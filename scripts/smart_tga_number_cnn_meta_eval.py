"""Evaluate a Smart TGA race-number CNN with proposal/context metadata.

This is offline Smart TGA tooling. Cycle 70 showed that image-only crops still
confuse sponsor text, stripes, logos, and template pieces with race numbers.
This evaluator keeps the same held-out protocol as ``smart_tga_number_cnn_eval``
but adds numeric proposal/crop features to test whether context helps before
any Auto-build integration.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
import cv2
from PIL import Image, ImageDraw
from torch import nn
from torch.utils.data import DataLoader, Dataset

from smart_tga_number_cnn_eval import (
    FOLD_STRATEGY,
    IMG_SIZE,
    TinyNumberCNN,
    _load_manifest,
    _make_folds,
    _pil_to_tensor,
)
from smart_tga_template_prior_probe import (
    DEFAULT_INTEL,
    _as_xyxy as _template_as_xyxy,
    _center_value as _template_center_value,
    _effective_template_prior,
    _raw_template_prior,
    _region_stats as _template_region_stats,
    _resolved_slug,
    _source_slug,
)


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle70_ranker_unmatched_corpus_strict_v1/manifest.json")
USE_PROPOSAL_CONTEXT_META = os.environ.get("SPB_SMART_TGA_PROPOSAL_CONTEXT_META", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
USE_STROKE_TOPOLOGY_META = os.environ.get("SPB_SMART_TGA_STROKE_META", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
USE_REGION_CONTEXT_META = os.environ.get("SPB_SMART_TGA_REGION_CONTEXT_META", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
BOX_META_DIM = 6
PROPOSAL_BASE_META_DIM = 7
PROPOSAL_CONTEXT_META_DIM = 12 if USE_PROPOSAL_CONTEXT_META else 0
CROP_META_DIM = 11
REGION_CONTEXT_META_DIM = 14 if USE_REGION_CONTEXT_META else 0
STROKE_META_DIM = 12 if USE_STROKE_TOPOLOGY_META else 0
TEMPLATE_META_DIM = 10
META_DIM = (
    BOX_META_DIM
    + PROPOSAL_BASE_META_DIM
    + PROPOSAL_CONTEXT_META_DIM
    + CROP_META_DIM
    + REGION_CONTEXT_META_DIM
    + STROKE_META_DIM
    + TEMPLATE_META_DIM
)
_TEMPLATE_CACHE: dict[str, tuple[np.ndarray | None, np.ndarray | None]] = {}
_SOURCE_RGB_CACHE: dict[str, np.ndarray] = {}
PROPOSAL_FAMILY_GROUPS = (
    "component_default",
    "edge_component",
    "window",
    "focused_window",
    "side_panel",
    "expanded",
    "unknown",
)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _box_features(rec: dict[str, Any]) -> list[float]:
    box = rec.get("raw_box") or rec.get("box") or [0, 0, 0, 0]
    if len(box) != 4:
        box = [0, 0, 0, 0]
    if rec.get("raw_box"):
        x, y, w, h = [_num(v) for v in box]
    else:
        x0, y0, x1, y1 = [_num(v) for v in box]
        x, y, w, h = x0, y0, max(0.0, x1 - x0), max(0.0, y1 - y0)
    area = w * h
    aspect = w / max(1.0, h)
    return [
        w / 1024.0,
        h / 1024.0,
        area / float(1024 * 1024),
        np.log2(max(0.125, min(8.0, aspect))) / 3.0,
        (x + w * 0.5) / 1024.0,
        (y + h * 0.5) / 1024.0,
    ]


def _proposal_features(rec: dict[str, Any]) -> list[float]:
    def pick(*names: str, default: float = -1.0) -> float:
        for name in names:
            if rec.get(name) is not None:
                return _num(rec.get(name), default)
        return default

    area = pick("area", "candidate_area", default=-1.0)
    base = [
        1.0 if rec.get("raw_box") or rec.get("candidate_area") or rec.get("area") else 0.0,
        min(1.0, max(-1.0, area / 40000.0 if area >= 0 else -1.0)),
        pick("fill", "candidate_fill"),
        pick("edge_density", "candidate_edge_density"),
        pick("soft_edge_density", "candidate_edge_density"),
        pick("sat_density", "candidate_sat_density"),
        np.log2(max(0.125, min(8.0, pick("aspect", "candidate_aspect", default=1.0)))) / 3.0,
    ]
    index_raw = rec.get("proposal_index")
    has_index = index_raw is not None
    proposal_index = max(0.0, _num(index_raw, 0.0)) if has_index else 0.0
    family = _proposal_family_group(rec)
    family_flags = [1.0 if family == name else 0.0 for name in PROPOSAL_FAMILY_GROUPS]
    if not USE_PROPOSAL_CONTEXT_META:
        return base
    context = [
        1.0 if has_index else 0.0,
        min(1.0, proposal_index / 240.0),
        min(1.0, proposal_index / 480.0),
        1.0 / (1.0 + proposal_index) if has_index else 0.0,
        *family_flags,
        1.0 if family in {"side_panel", "focused_window"} else 0.0,
    ]
    if len(context) != PROPOSAL_CONTEXT_META_DIM:
        raise ValueError(f"proposal context dimension drifted: {len(context)} != {PROPOSAL_CONTEXT_META_DIM}")
    return base + context


def _proposal_family_group(rec: dict[str, Any]) -> str:
    raw = str(rec.get("proposal_variant") or rec.get("candidate_variant") or "").strip()
    if not raw:
        if rec.get("raw_box") or rec.get("candidate_area") or rec.get("area"):
            return "component_default"
        return "unknown"
    if raw == "window":
        return "window"
    if raw == "focused_window":
        return "focused_window"
    if raw.startswith("side_panel"):
        return "side_panel"
    if raw.startswith("expanded_"):
        return "expanded"
    if raw in {
        "default_shape",
        "tight_strokes",
        "wide_wordlike",
        "tall_digits",
        "soft_default",
        "soft_tall",
        "component_default",
    }:
        return "edge_component" if raw != "component_default" else "component_default"
    return "unknown"


def _crop_stats(path: Path) -> list[float]:
    arr = np.asarray(Image.open(path).convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)).astype(np.float32) / 255.0
    luma = arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0.0)
    gx = np.abs(np.diff(luma, axis=1))
    gy = np.abs(np.diff(luma, axis=0))
    edge_mean = float((gx.mean() + gy.mean()) * 0.5)
    edge_frac = float(((gx[:-1, :] + gy[:, :-1]) > 0.14).mean()) if gx.shape[0] > 1 and gy.shape[1] > 1 else 0.0
    nonblack = (arr.max(axis=2) > 0.035).astype(np.float32)
    color_std = arr.std(axis=(0, 1))
    return [
        float(luma.mean()),
        float(luma.std()),
        float(sat.mean()),
        float(sat.std()),
        edge_mean,
        edge_frac,
        float(nonblack.mean()),
        float((luma > 0.85).mean()),
        float((luma < 0.12).mean()),
        float(color_std.mean()),
        float(np.max(color_std)),
    ]


def _stroke_topology_stats_from_array(arr: np.ndarray) -> list[float]:
    luma = arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114
    nonblack = arr.max(axis=2) > 0.035
    border = np.concatenate([arr[0, :, :], arr[-1, :, :], arr[:, 0, :], arr[:, -1, :]], axis=0)
    border_rgb = np.median(border, axis=0)
    border_dist = np.linalg.norm(arr - border_rgb.reshape(1, 1, 3), axis=2)
    salient = (border_dist > 0.18) & nonblack
    if salient.mean() < 0.01:
        salient = (np.abs(luma - float(np.median(luma[nonblack]))) > 0.18) & nonblack if nonblack.any() else salient
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(salient.astype(np.uint8), 8)
    component_areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float32) if count > 1 else np.asarray([], dtype=np.float32)
    large_components = component_areas[component_areas >= 6.0]
    largest = float(component_areas.max()) if component_areas.size else 0.0
    if salient.any():
        ys, xs = np.where(salient)
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        bbox_area = float(max(1, (x1 - x0) * (y1 - y0)))
        bbox_fill = float(salient.sum() / bbox_area)
        bbox_area_frac = bbox_area / float(64 * 64)
    else:
        bbox_fill = 0.0
        bbox_area_frac = 0.0
    gx = np.abs(np.diff(luma, axis=1))
    gy = np.abs(np.diff(luma, axis=0))
    gx_mean = float(gx.mean())
    gy_mean = float(gy.mean())
    edge_total = gx_mean + gy_mean + 1e-6
    border_nonblack = float(
        np.concatenate([nonblack[0, :], nonblack[-1, :], nonblack[:, 0], nonblack[:, -1]]).mean()
    )
    quantized = np.floor(arr * 7.0).astype(np.int16)
    unique_colors = len({tuple(row) for row in quantized.reshape(-1, 3).tolist()})
    color_blockiness = 1.0 - min(1.0, unique_colors / 96.0)
    return [
        float(salient.mean()),
        bbox_area_frac,
        bbox_fill,
        min(1.0, float(len(large_components)) / 16.0),
        largest / max(1.0, float(salient.sum())),
        border_nonblack,
        gx_mean / edge_total,
        gy_mean / edge_total,
        float(((gx[:-1, :] > 0.16) & (gy[:, :-1] > 0.16)).mean()) if gx.shape[0] > 1 else 0.0,
        float(border_dist.mean()),
        float(border_dist.std()),
        color_blockiness,
    ]


def _stroke_topology_stats(path: Path) -> list[float]:
    arr = np.asarray(Image.open(path).convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)).astype(np.float32) / 255.0
    return _stroke_topology_stats_from_array(arr)


def _record_source_path(rec: dict[str, Any]) -> Path | None:
    for key in ("paint", "car_num", "car"):
        value = rec.get(key)
        if not value:
            continue
        path = Path(str(value))
        if path.is_file():
            return path
    return None


def _source_rgb(path: Path) -> np.ndarray:
    key = str(path.resolve())
    if key not in _SOURCE_RGB_CACHE:
        _SOURCE_RGB_CACHE[key] = np.asarray(Image.open(path).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS))
    return _SOURCE_RGB_CACHE[key]


def _clip_region_box(box: list[int] | tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = [int(round(float(v))) for v in box]
    x0 = max(0, min(1024, x0))
    y0 = max(0, min(1024, y0))
    x1 = max(0, min(1024, x1))
    y1 = max(0, min(1024, y1))
    if x1 <= x0 or y1 <= y0:
        return 0, 0, 0, 0
    return x0, y0, x1, y1


def _masked_mean(values: np.ndarray, mask: np.ndarray) -> float:
    if values.size == 0 or not mask.any():
        return 0.0
    return float(values[mask].mean())


def _masked_std(values: np.ndarray, mask: np.ndarray) -> float:
    if values.size == 0 or not mask.any():
        return 0.0
    return float(values[mask].std())


def _masked_color_complexity(region: np.ndarray, mask: np.ndarray) -> float:
    if region.size == 0 or not mask.any():
        return 0.0
    pixels = region[mask]
    if len(pixels) > 4096:
        step = max(1, len(pixels) // 4096)
        pixels = pixels[::step]
    quantized = np.floor(pixels.astype(np.float32) / 32.0).astype(np.int16)
    unique = len({tuple(row) for row in quantized.tolist()})
    return min(1.0, unique / 128.0)


def _component_counts(edge: np.ndarray, inside_mask: np.ndarray, ring_mask: np.ndarray) -> tuple[float, float]:
    n, _labels, stats, centroids = cv2.connectedComponentsWithStats(edge.astype(np.uint8), 8)
    inside_count = 0
    ring_count = 0
    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < 3 or area > 120:
            continue
        cx, cy = centroids[idx]
        x = int(round(cx))
        y = int(round(cy))
        if y < 0 or y >= edge.shape[0] or x < 0 or x >= edge.shape[1]:
            continue
        if inside_mask[y, x]:
            inside_count += 1
        elif ring_mask[y, x]:
            ring_count += 1
    return min(1.0, inside_count / 24.0), min(1.0, ring_count / 24.0)


def _region_context_stats_from_rgb(rgb: np.ndarray, box: list[int] | tuple[int, int, int, int]) -> list[float]:
    x0, y0, x1, y1 = _clip_region_box(box)
    if x1 <= x0 or y1 <= y0:
        return [0.0] * 14
    w = x1 - x0
    h = y1 - y0
    pad_x = max(18, int(round(w * 0.72)))
    pad_y = max(18, int(round(h * 0.72)))
    ex0 = max(0, x0 - pad_x)
    ey0 = max(0, y0 - pad_y)
    ex1 = min(1024, x1 + pad_x)
    ey1 = min(1024, y1 + pad_y)
    region = rgb[ey0:ey1, ex0:ex1]
    if region.size == 0:
        return [0.0] * 14
    lx0, ly0 = x0 - ex0, y0 - ey0
    lx1, ly1 = x1 - ex0, y1 - ey0
    inside_mask = np.zeros(region.shape[:2], dtype=bool)
    inside_mask[ly0:ly1, lx0:lx1] = True
    ring_mask = ~inside_mask
    gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)
    edge = cv2.Canny(gray, 35, 130) > 0
    sat = hsv[:, :, 1].astype(np.float32) / 255.0
    luma = gray.astype(np.float32) / 255.0
    inside_edge = _masked_mean(edge.astype(np.float32), inside_mask)
    ring_edge = _masked_mean(edge.astype(np.float32), ring_mask)
    inside_sat = _masked_mean(sat, inside_mask)
    ring_sat = _masked_mean(sat, ring_mask)
    edge_ratio = min(1.0, inside_edge / max(0.0005, ring_edge) / 2.0)
    sat_ratio = min(1.0, inside_sat / max(0.0005, ring_sat) / 2.0)
    inside_small, ring_small = _component_counts(edge, inside_mask, ring_mask)
    border_mask = np.zeros_like(inside_mask)
    strip = max(2, int(round(min(w, h) * 0.055)))
    border_mask[ly0:min(ly1, ly0 + strip), lx0:lx1] = True
    border_mask[max(ly0, ly1 - strip):ly1, lx0:lx1] = True
    border_mask[ly0:ly1, lx0:min(lx1, lx0 + strip)] = True
    border_mask[ly0:ly1, max(lx0, lx1 - strip):lx1] = True
    border_edge = _masked_mean(edge.astype(np.float32), border_mask)
    ring_clutter = min(1.0, ring_edge * 3.4 + ring_sat * 0.35 + ring_small * 0.65)
    return [
        inside_edge,
        ring_edge,
        edge_ratio,
        inside_sat,
        ring_sat,
        sat_ratio,
        _masked_std(luma, inside_mask),
        _masked_std(luma, ring_mask),
        _masked_color_complexity(region, inside_mask),
        _masked_color_complexity(region, ring_mask),
        inside_small,
        ring_small,
        border_edge,
        ring_clutter,
    ]


def _region_context_features(rec: dict[str, Any]) -> list[float]:
    source = _record_source_path(rec)
    if source is None:
        return [0.0] * REGION_CONTEXT_META_DIM
    try:
        return _region_context_stats_from_rgb(_source_rgb(source), _template_as_xyxy(rec, prefer_raw=False))
    except Exception:
        return [0.0] * REGION_CONTEXT_META_DIM


def _template_pair(rec: dict[str, Any]) -> tuple[np.ndarray | None, np.ndarray | None]:
    source_slug = _source_slug(rec)
    resolved = _resolved_slug(source_slug, DEFAULT_INTEL)
    cache_key = resolved or ""
    if cache_key not in _TEMPLATE_CACHE:
        if resolved:
            _TEMPLATE_CACHE[cache_key] = (
                _effective_template_prior(resolved, DEFAULT_INTEL),
                _raw_template_prior(resolved, DEFAULT_INTEL),
            )
        else:
            _TEMPLATE_CACHE[cache_key] = (None, None)
    return _TEMPLATE_CACHE[cache_key]


def _template_features(rec: dict[str, Any]) -> list[float]:
    """Context features from learned car intel masks.

    These are intentionally metadata-only and safe to zero-fill if the source
    car folder cannot be resolved. The raw learned mask is broad, so it is used
    as a soft feature; the runtime-style effective prior is the conservative
    grille/glass/light signal.
    """
    effective, raw = _template_pair(rec)
    box = _template_as_xyxy(rec, prefer_raw=False)
    raw_box = _template_as_xyxy(rec, prefer_raw=True)
    effective_box = _template_region_stats(effective, box)
    effective_raw = _template_region_stats(effective, raw_box)
    raw_box_stats = _template_region_stats(raw, box)
    return [
        1.0 if effective is not None else 0.0,
        effective_box["mean"],
        effective_box["frac_025"],
        effective_raw["mean"],
        effective_raw["frac_025"],
        effective_raw["max"],
        raw_box_stats["mean"],
        raw_box_stats["frac_050"],
        _template_center_value(effective, raw_box),
        effective_raw["area_frac"],
    ]


def _meta_vector(rec: dict[str, Any]) -> np.ndarray:
    crop_path = Path(rec["file"])
    values = (
        _box_features(rec)
        + _proposal_features(rec)
        + _crop_stats(crop_path)
        + (_region_context_features(rec) if USE_REGION_CONTEXT_META else [])
        + (_stroke_topology_stats(crop_path) if USE_STROKE_TOPOLOGY_META else [])
        + _template_features(rec)
    )
    if len(values) != META_DIM:
        raise ValueError(f"metadata dimension drifted: {len(values)} != {META_DIM}")
    return np.asarray(values, dtype=np.float32)


class MetaCropDataset(Dataset):
    def __init__(
        self,
        records: list[dict[str, Any]],
        indexes: list[int],
        meta: np.ndarray,
        mean: np.ndarray,
        std: np.ndarray,
        augment: bool,
        seed: int,
    ):
        self.records = records
        self.indexes = indexes
        self.meta = meta
        self.mean = mean
        self.std = std
        self.augment = augment
        self.seed = seed

    def __len__(self) -> int:
        return len(self.indexes)

    def __getitem__(self, item: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        idx = self.indexes[item]
        rec = self.records[idx]
        rng = random.Random(self.seed + idx * 1009 + item)
        img = Image.open(rec["file"])
        tensor = _pil_to_tensor(img, self.augment, rng)
        meta = torch.from_numpy((self.meta[idx] - self.mean) / self.std).float()
        label = torch.tensor(float(rec["truth"]), dtype=torch.float32)
        return tensor, meta, label


class TinyNumberCNNMeta(nn.Module):
    def __init__(self, meta_dim: int = META_DIM) -> None:
        super().__init__()
        self.image_features = TinyNumberCNN().features
        self.meta_features = nn.Sequential(
            nn.Linear(meta_dim, 32),
            nn.ReLU(inplace=True),
            nn.Dropout(0.15),
            nn.Linear(32, 24),
            nn.ReLU(inplace=True),
        )
        self.head = nn.Sequential(
            nn.Dropout(0.25),
            nn.Linear(96 + 24, 48),
            nn.ReLU(inplace=True),
            nn.Dropout(0.20),
            nn.Linear(48, 1),
        )

    def forward(self, x: torch.Tensor, meta: torch.Tensor) -> torch.Tensor:
        img = self.image_features(x).flatten(1)
        ctx = self.meta_features(meta)
        return self.head(torch.cat([img, ctx], dim=1)).squeeze(1)


def _predict(model: TinyNumberCNNMeta, loader: DataLoader, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    probs: list[np.ndarray] = []
    truths: list[np.ndarray] = []
    with torch.no_grad():
        for x, meta, y in loader:
            logits = model(x.to(device), meta.to(device))
            probs.append(torch.sigmoid(logits).cpu().numpy())
            truths.append(y.numpy())
    return np.concatenate(probs), np.concatenate(truths).astype(np.int32)


def _train_fold(
    records: list[dict[str, Any]],
    meta: np.ndarray,
    train_idx: list[int],
    test_idx: list[int],
    args: argparse.Namespace,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    train_meta = meta[train_idx]
    mean = train_meta.mean(axis=0).astype(np.float32)
    std = np.maximum(train_meta.std(axis=0).astype(np.float32), 1e-4)
    train_ds = MetaCropDataset(records, train_idx, meta, mean, std, augment=True, seed=seed)
    test_ds = MetaCropDataset(records, test_idx, meta, mean, std, augment=False, seed=seed + 17)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = TinyNumberCNNMeta(meta.shape[1]).to(device)
    pos = sum(records[idx]["truth"] for idx in train_idx)
    neg = len(train_idx) - pos
    pos_weight = torch.tensor([max(1.0, neg / max(1.0, float(pos))) * args.pos_weight_scale], device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _epoch in range(args.epochs):
        model.train()
        for x, meta_batch, y in train_loader:
            opt.zero_grad(set_to_none=True)
            logits = model(x.to(device), meta_batch.to(device))
            target = y.to(device)
            if args.loss == "focal":
                bce = nn.functional.binary_cross_entropy_with_logits(
                    logits,
                    target,
                    pos_weight=pos_weight,
                    reduction="none",
                )
                prob = torch.sigmoid(logits)
                pt = torch.where(target > 0.5, prob, 1.0 - prob).clamp(1e-4, 1.0 - 1e-4)
                loss = (((1.0 - pt) ** args.focal_gamma) * bce).mean()
            else:
                loss = loss_fn(logits, target)
            loss.backward()
            opt.step()
    return _predict(model, test_loader, device)


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 6
    cell = 190
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        img = Image.open(rec["file"]).convert("RGB").resize((156, 156), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 17, y + 24))
        draw.text((x + 6, y + 5), f"truth {rec['truth']} pred {rec['pred']} p {rec['prob']:.2f}", fill=(255, 220, 120))
        draw.text((x + 6, y + 176), str(rec.get("group", ""))[:27], fill=(220, 220, 220))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    draw.text((8, 8), title, fill=(255, 255, 255))
    sheet.save(out_path)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    records = _load_manifest(args.manifest, args.holdout_mode)
    meta = np.stack([_meta_vector(rec) for rec in records]).astype(np.float32)
    folds = _make_folds(records, args.folds, args.seed)
    if args.max_folds:
        folds = folds[:args.max_folds]
    fold_results: list[dict[str, Any]] = []
    mistakes: list[dict[str, Any]] = []
    fold_prob_cache: list[dict[str, Any]] = []
    for fold_no, test_idx in enumerate(folds):
        train_idx = [idx for idx in range(len(records)) if idx not in test_idx]
        probs, truth = _train_fold(records, meta, train_idx, test_idx, args, args.seed + fold_no * 31)
        fold_prob_cache.append({"fold": fold_no, "test_idx": test_idx, "probs": probs.tolist(), "truth": truth.tolist()})
        pred = (probs >= args.threshold).astype(np.int32)
        fold_mistakes: list[dict[str, Any]] = []
        for local_idx, p, t, prob in zip(test_idx, pred, truth, probs):
            if int(p) == int(t):
                continue
            rec = records[local_idx]
            mistake = {
                "file": rec["file"],
                "truth": int(t),
                "pred": int(p),
                "prob": round(float(prob), 4),
                "label": rec["label"],
                "group": rec["group"],
                "fold": fold_no,
            }
            fold_mistakes.append(mistake)
            mistakes.append(mistake)
        fold_results.append({
            "fold": fold_no,
            "train": len(train_idx),
            "test": len(test_idx),
            "test_groups": sorted({records[idx]["group"] for idx in test_idx}),
            "accuracy": round(float((pred == truth).mean()), 4),
            "false_positive": int(((pred == 1) & (truth == 0)).sum()),
            "false_negative": int(((pred == 0) & (truth == 1)).sum()),
            "mistakes": fold_mistakes,
        })
    threshold_sweep: list[dict[str, Any]] = []
    for threshold in [round(v, 2) for v in np.linspace(0.15, 0.85, 15)]:
        fold_acc: list[float] = []
        fp_total = 0
        fn_total = 0
        fp_files: set[str] = set()
        fn_files: set[str] = set()
        for cache in fold_prob_cache:
            probs = np.asarray(cache["probs"], dtype=np.float32)
            truth = np.asarray(cache["truth"], dtype=np.int32)
            pred = (probs >= threshold).astype(np.int32)
            fold_acc.append(float((pred == truth).mean()))
            for idx, p, t in zip(cache["test_idx"], pred, truth):
                if int(p) == int(t):
                    continue
                rec = records[idx]
                if int(t) == 0 and int(p) == 1:
                    fp_total += 1
                    fp_files.add(rec["file"])
                elif int(t) == 1 and int(p) == 0:
                    fn_total += 1
                    fn_files.add(rec["file"])
        threshold_sweep.append({
            "threshold": threshold,
            "mean_accuracy": round(float(np.mean(fold_acc)), 4) if fold_acc else 0.0,
            "min_accuracy": round(float(np.min(fold_acc)), 4) if fold_acc else 0.0,
            "total_false_positive": fp_total,
            "total_false_negative": fn_total,
            "unique_false_positive_files": len(fp_files),
            "unique_false_negative_files": len(fn_files),
        })
    best_threshold = max(threshold_sweep, key=lambda r: (r["mean_accuracy"], r["min_accuracy"])) if threshold_sweep else None
    best_min_threshold = max(threshold_sweep, key=lambda r: (r["min_accuracy"], r["mean_accuracy"])) if threshold_sweep else None
    accuracies = [f["accuracy"] for f in fold_results]
    model_parts = ["tiny_cnn_meta_template_prior"]
    if USE_PROPOSAL_CONTEXT_META:
        model_parts.append("proposal_context")
    if USE_REGION_CONTEXT_META:
        model_parts.append("region_context")
    if USE_STROKE_TOPOLOGY_META:
        model_parts.append("stroke")
    model_name = "_".join(model_parts) + "_v1"
    summary = {
        "manifest": str(args.manifest),
        "holdout_mode": args.holdout_mode,
        "model": model_name,
        "fold_strategy": FOLD_STRATEGY,
        "meta_dim": int(meta.shape[1]),
        "proposal_context_meta_enabled": USE_PROPOSAL_CONTEXT_META,
        "region_context_meta_enabled": USE_REGION_CONTEXT_META,
        "stroke_topology_meta_enabled": USE_STROKE_TOPOLOGY_META,
        "box_meta_dim": BOX_META_DIM,
        "proposal_base_meta_dim": PROPOSAL_BASE_META_DIM,
        "proposal_context_meta_dim": PROPOSAL_CONTEXT_META_DIM,
        "crop_meta_dim": CROP_META_DIM,
        "region_context_meta_dim": REGION_CONTEXT_META_DIM,
        "stroke_meta_dim": STROKE_META_DIM,
        "template_meta_dim": TEMPLATE_META_DIM,
        "samples": len(records),
        "positive_samples": sum(1 for r in records if r["truth"] == 1),
        "hard_negative_samples": sum(1 for r in records if r["truth"] == 0),
        "folds": len(fold_results),
        "epochs": args.epochs,
        "loss": args.loss,
        "focal_gamma": args.focal_gamma if args.loss == "focal" else None,
        "pos_weight_scale": args.pos_weight_scale,
        "threshold": args.threshold,
        "mean_accuracy": round(float(np.mean(accuracies)), 4) if accuracies else 0.0,
        "min_accuracy": round(float(np.min(accuracies)), 4) if accuracies else 0.0,
        "total_false_positive": sum(f["false_positive"] for f in fold_results),
        "total_false_negative": sum(f["false_negative"] for f in fold_results),
        "unique_false_positive_files": len({m["file"] for m in mistakes if m["truth"] == 0 and m["pred"] == 1}),
        "unique_false_negative_files": len({m["file"] for m in mistakes if m["truth"] == 1 and m["pred"] == 0}),
        "threshold_sweep": threshold_sweep,
        "best_threshold_by_mean": best_threshold,
        "best_threshold_by_min": best_min_threshold,
        "fold_results": fold_results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "cnn_meta_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    mistake_records: list[dict[str, Any]] = []
    by_file = {rec["file"]: rec for rec in records}
    for mistake in mistakes[:36]:
        rec = dict(by_file[mistake["file"]])
        rec.update(mistake)
        mistake_records.append(rec)
    _contact_sheet(mistake_records, args.output / "mistakes_contact_sheet.png", "Smart TGA CNN+metadata mistakes")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=Path("_smart_tga_runs/smart_tga_number_cnn_meta_eval"))
    parser.add_argument("--holdout-mode", choices=["source", "paint"], default="source")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=28)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.0012)
    parser.add_argument("--weight-decay", type=float, default=0.0008)
    parser.add_argument("--loss", choices=["bce", "focal"], default="focal")
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--pos-weight-scale", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


def main() -> None:
    summary = evaluate(parse_args())
    brief = {k: v for k, v in summary.items() if k != "fold_results"}
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
