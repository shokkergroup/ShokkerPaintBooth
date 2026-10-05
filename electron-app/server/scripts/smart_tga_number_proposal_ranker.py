"""Rank full-image Smart TGA number proposals with the focal CNN.

This is offline Smart TGA tooling. It answers a practical question before any
Auto-build integration: when hybrid proposals are generated from the whole TGA,
does a held-out CNN rank the true race-number boxes near the top?
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw
from torch import nn
from torch.utils.data import DataLoader

from smart_tga_number_candidate_miner import _box_iou, _crop_square, _read_rgb
from smart_tga_number_cnn_eval import FOLD_STRATEGY, CropDataset, TinyNumberCNN, _load_manifest, _make_folds, _pil_to_tensor
from smart_tga_number_cnn_meta_eval import (
    META_DIM,
    REGION_CONTEXT_META_DIM,
    MetaCropDataset,
    TinyNumberCNNMeta,
    USE_REGION_CONTEXT_META,
    USE_STROKE_TOPOLOGY_META,
    _box_features,
    _meta_vector,
    _proposal_features,
    _region_context_stats_from_rgb,
    _stroke_topology_stats_from_array,
    _template_features,
)
from smart_tga_number_proposal_eval import _as_xyxy, _proposal_boxes, _raw_xywh_to_xyxy, _source_bucket, _source_path


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle67_arcachevy_window_hardneg_corpus_v1/manifest.json")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_number_proposal_ranker")
TOP_K = (1, 3, 5, 10, 20, 40)
SCORE_SWEEP_MODES = ("image", "meta", "image_meta_blend", "image_meta_product", "image_meta_veto")


def _candidate_xyxy(candidate: dict[str, Any]) -> list[int]:
    raw = candidate.get("raw_box")
    if isinstance(raw, list) and len(raw) == 4:
        return _raw_xywh_to_xyxy([int(v) for v in raw])
    return [int(v) for v in candidate.get("box", [0, 0, 0, 0])]


def _record_xyxy(record: dict[str, Any]) -> list[int]:
    box = _as_xyxy(record)
    if box:
        return [int(v) for v in box]
    return _candidate_xyxy(record)


def _context_crop_from_rgb(
    rgb: np.ndarray,
    box: list[int],
    pad_scale: float,
    mark_box: bool = True,
) -> Image.Image:
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = [int(v) for v in box]
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    box_w = max(1, x1 - x0)
    box_h = max(1, y1 - y0)
    pad = max(8, int(max(box_w, box_h) * max(0.0, float(pad_scale))))
    cx0 = max(0, x0 - pad)
    cy0 = max(0, y0 - pad)
    cx1 = min(width, x1 + pad)
    cy1 = min(height, y1 + pad)
    img = Image.fromarray(rgb[cy0:cy1, cx0:cx1]).convert("RGB")
    if mark_box:
        local = [x0 - cx0, y0 - cy0, x1 - cx0, y1 - cy0]
        draw = ImageDraw.Draw(img)
        stroke = max(1, int(min(img.size) * 0.018))
        draw.rectangle(local, outline=(255, 225, 40), width=stroke)
    return img


def _positive_records(records: list[dict[str, Any]], indexes: list[int]) -> list[dict[str, Any]]:
    positives: list[dict[str, Any]] = []
    for idx in indexes:
        rec = records[idx]
        if rec.get("truth") != 1:
            continue
        gt = _as_xyxy(rec)
        source = _source_path(rec)
        if not gt or not source:
            continue
        positives.append(
            {
                "manifest_index": idx,
                "source_path": str(source.resolve()),
                "folder": rec.get("folder") or source.parent.name,
                "source_bucket": _source_bucket(rec),
                "group": rec.get("group"),
                "gt_box": gt,
                "record_file": rec.get("file"),
            }
        )
    return positives


def _hard_negative_records(records: list[dict[str, Any]], indexes: list[int]) -> list[dict[str, Any]]:
    negatives: list[dict[str, Any]] = []
    for idx in indexes:
        rec = records[idx]
        if rec.get("truth") == 1:
            continue
        box = _as_xyxy(rec)
        source = _source_path(rec)
        if not box or not source:
            continue
        negatives.append(
            {
                "manifest_index": idx,
                "source_path": str(source.resolve()),
                "folder": rec.get("folder") or source.parent.name,
                "source_bucket": _source_bucket(rec),
                "group": rec.get("group"),
                "gt_box": box,
                "record_file": rec.get("file"),
                "negative_label": rec.get("label"),
                "source_kind": rec.get("source_kind"),
                "candidate_label": rec.get("candidate_label"),
                "probe_label": rec.get("probe_label"),
            }
        )
    return negatives


def _training_weight(record: dict[str, Any], args: argparse.Namespace) -> float:
    if record.get("truth") == 1:
        return 1.0
    weight = max(0.05, float(args.hard_negative_weight))
    if record.get("source_kind") == "reviewed_candidate_queue":
        weight *= max(0.05, float(args.reviewed_hard_negative_weight))
    return weight


def _is_confuser_record(record: dict[str, Any], target: str) -> bool:
    if record.get("truth") == 1:
        return False
    if target == "reviewed":
        return record.get("source_kind") == "reviewed_candidate_queue"
    return True


def _confuser_records(records: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    confuser_records: list[dict[str, Any]] = []
    for record in records:
        out = dict(record)
        out["truth"] = 1 if _is_confuser_record(record, target) else 0
        confuser_records.append(out)
    return confuser_records


def _confuser_training_args(args: argparse.Namespace) -> argparse.Namespace:
    cloned = argparse.Namespace(**vars(args))
    cloned.hard_negative_weight = 1.0
    cloned.reviewed_hard_negative_weight = 1.0
    return cloned


class _WeightedCropDataset:
    def __init__(self, records: list[dict[str, Any]], indexes: list[int], args: argparse.Namespace, augment: bool, seed: int):
        self.records = records
        self.indexes = indexes
        self.args = args
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
        label = torch.tensor(float(rec["truth"]), dtype=torch.float32)
        weight = torch.tensor(_training_weight(rec, self.args), dtype=torch.float32)
        return tensor, label, weight


class _WeightedContextCropDataset:
    def __init__(self, records: list[dict[str, Any]], indexes: list[int], args: argparse.Namespace, augment: bool, seed: int):
        self.records = records
        self.indexes = indexes
        self.args = args
        self.augment = augment
        self.seed = seed
        self.rgb_cache: dict[str, np.ndarray] = {}
        self.image_cache: dict[int, Image.Image] = {}

    def __len__(self) -> int:
        return len(self.indexes)

    def _source_rgb(self, record: dict[str, Any]) -> np.ndarray:
        source = _source_path(record)
        if source is None:
            raise ValueError(f"context confuser record has no source paint: {record.get('file')}")
        key = str(source.resolve())
        if key not in self.rgb_cache:
            self.rgb_cache[key] = _read_rgb(source)
        return self.rgb_cache[key]

    def _context_image(self, idx: int) -> Image.Image:
        if idx not in self.image_cache:
            rec = self.records[idx]
            rgb = self._source_rgb(rec)
            self.image_cache[idx] = _context_crop_from_rgb(
                rgb,
                _record_xyxy(rec),
                self.args.context_confuser_pad_scale,
                mark_box=True,
            )
        return self.image_cache[idx]

    def __getitem__(self, item: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        idx = self.indexes[item]
        rec = self.records[idx]
        rng = random.Random(self.seed + idx * 1009 + item)
        tensor = _pil_to_tensor(self._context_image(idx), self.augment, rng)
        label = torch.tensor(float(rec["truth"]), dtype=torch.float32)
        weight = torch.tensor(_training_weight(rec, self.args), dtype=torch.float32)
        return tensor, label, weight


class _WeightedMetaCropDataset:
    def __init__(
        self,
        records: list[dict[str, Any]],
        indexes: list[int],
        meta: np.ndarray,
        mean: np.ndarray,
        std: np.ndarray,
        args: argparse.Namespace,
        augment: bool,
        seed: int,
    ):
        self.records = records
        self.indexes = indexes
        self.meta = meta
        self.mean = mean
        self.std = std
        self.args = args
        self.augment = augment
        self.seed = seed

    def __len__(self) -> int:
        return len(self.indexes)

    def __getitem__(self, item: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        idx = self.indexes[item]
        rec = self.records[idx]
        rng = random.Random(self.seed + idx * 1009 + item)
        img = Image.open(rec["file"])
        tensor = _pil_to_tensor(img, self.augment, rng)
        meta = torch.from_numpy((self.meta[idx] - self.mean) / self.std).float()
        label = torch.tensor(float(rec["truth"]), dtype=torch.float32)
        weight = torch.tensor(_training_weight(rec, self.args), dtype=torch.float32)
        return tensor, meta, label, weight


def _train_loop(
    model: nn.Module,
    loader: DataLoader,
    records: list[dict[str, Any]],
    train_idx: list[int],
    args: argparse.Namespace,
    device: torch.device,
    meta_model: bool,
) -> None:
    pos = sum(records[idx]["truth"] for idx in train_idx)
    neg = len(train_idx) - pos
    pos_weight = torch.tensor([max(1.0, neg / max(1.0, float(pos))) * args.pos_weight_scale], device=device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _epoch in range(args.epochs):
        model.train()
        for batch in loader:
            opt.zero_grad(set_to_none=True)
            if meta_model:
                x, meta_batch, y, sample_weight = batch
                logits = model(x.to(device), meta_batch.to(device))
            else:
                x, y, sample_weight = batch
                logits = model(x.to(device))
            target = y.to(device)
            sample_weight = sample_weight.to(device)
            bce = nn.functional.binary_cross_entropy_with_logits(
                logits,
                target,
                pos_weight=pos_weight,
                reduction="none",
            )
            if args.loss == "focal":
                prob = torch.sigmoid(logits)
                pt = torch.where(target > 0.5, prob, 1.0 - prob).clamp(1e-4, 1.0 - 1e-4)
                loss_terms = ((1.0 - pt) ** args.focal_gamma) * bce
            else:
                loss_terms = bce
            loss = (loss_terms * sample_weight).sum() / sample_weight.sum().clamp_min(1e-4)
            loss.backward()
            opt.step()


def _train_image_model(records: list[dict[str, Any]], train_idx: list[int], args: argparse.Namespace, seed: int) -> nn.Module:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    dataset = _WeightedCropDataset(records, train_idx, args, augment=True, seed=seed)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = TinyNumberCNN().to(device)
    _train_loop(model, loader, records, train_idx, args, device, meta_model=False)
    return model


def _train_context_image_model(records: list[dict[str, Any]], train_idx: list[int], args: argparse.Namespace, seed: int) -> nn.Module:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    dataset = _WeightedContextCropDataset(records, train_idx, args, augment=True, seed=seed)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = TinyNumberCNN().to(device)
    _train_loop(model, loader, records, train_idx, args, device, meta_model=False)
    return model


def _train_meta_model(
    records: list[dict[str, Any]],
    train_idx: list[int],
    args: argparse.Namespace,
    seed: int,
) -> tuple[nn.Module, np.ndarray, np.ndarray]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    meta = np.stack([_meta_vector(rec) for rec in records]).astype(np.float32)
    if meta.shape[1] != META_DIM:
        raise ValueError(f"unexpected metadata dimension: {meta.shape[1]} != {META_DIM}")
    train_meta = meta[train_idx]
    mean = train_meta.mean(axis=0).astype(np.float32)
    std = np.maximum(train_meta.std(axis=0).astype(np.float32), 1e-4)
    dataset = _WeightedMetaCropDataset(records, train_idx, meta, mean, std, args, augment=True, seed=seed)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = TinyNumberCNNMeta(meta.shape[1]).to(device)
    _train_loop(model, loader, records, train_idx, args, device, meta_model=True)
    return model, mean, std


def _train_scorer(records: list[dict[str, Any]], train_idx: list[int], args: argparse.Namespace, seed: int) -> dict[str, Any]:
    scorer: dict[str, Any] = {"rank_model": args.rank_model}
    if args.rank_model in {"image", "image_meta_veto", "image_meta_blend", "image_meta_product"}:
        scorer["image_model"] = _train_image_model(records, train_idx, args, seed)
    if args.rank_model in {"meta", "image_meta_veto", "image_meta_blend", "image_meta_product"}:
        meta_model, mean, std = _train_meta_model(records, train_idx, args, seed + 11)
        scorer["meta_model"] = meta_model
        scorer["meta_mean"] = mean
        scorer["meta_std"] = std
    if args.confuser_penalty_weight > 0:
        confuser_records = _confuser_records(records, args.confuser_target)
        confuser_train_count = sum(int(confuser_records[idx]["truth"]) for idx in train_idx)
        scorer["confuser_target"] = args.confuser_target
        scorer["confuser_train_positive_records"] = confuser_train_count
        if confuser_train_count > 0:
            confuser_args = _confuser_training_args(args)
            if "image_model" in scorer:
                scorer["confuser_image_model"] = _train_image_model(confuser_records, train_idx, confuser_args, seed + 101)
            if "meta_model" in scorer:
                meta_model, mean, std = _train_meta_model(confuser_records, train_idx, confuser_args, seed + 113)
                scorer["confuser_meta_model"] = meta_model
                scorer["confuser_meta_mean"] = mean
                scorer["confuser_meta_std"] = std
    if _context_confuser_enabled(args):
        context_confuser_records = _confuser_records(records, args.context_confuser_target)
        context_train_count = sum(int(context_confuser_records[idx]["truth"]) for idx in train_idx)
        scorer["context_confuser_target"] = args.context_confuser_target
        scorer["context_confuser_train_positive_records"] = context_train_count
        if context_train_count > 0:
            context_args = _confuser_training_args(args)
            scorer["context_confuser_model"] = _train_context_image_model(context_confuser_records, train_idx, context_args, seed + 151)
    return scorer


def _crop_stats_from_image(img: Image.Image) -> list[float]:
    arr = np.asarray(img.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)).astype(np.float32) / 255.0
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


def _stroke_topology_stats_from_image(img: Image.Image) -> list[float]:
    arr = np.asarray(img.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)).astype(np.float32) / 255.0
    return _stroke_topology_stats_from_array(arr)


def _candidate_meta_vector(candidate: dict[str, Any], crop: Image.Image, rgb: np.ndarray) -> np.ndarray:
    values = (
        _box_features(candidate)
        + _proposal_features(candidate)
        + _crop_stats_from_image(crop)
        + (_region_context_stats_from_rgb(rgb, _candidate_xyxy(candidate)) if USE_REGION_CONTEXT_META else [])
        + (_stroke_topology_stats_from_image(crop) if USE_STROKE_TOPOLOGY_META else [])
        + _template_features(candidate)
    )
    if len(values) != META_DIM:
        raise ValueError(f"metadata dimension drifted: {len(values)} != {META_DIM}")
    return np.asarray(values, dtype=np.float32)


def _predict_image_probs(model: nn.Module, tensors: list[torch.Tensor], args: argparse.Namespace) -> list[float]:
    device = next(model.parameters()).device
    model.eval()
    probs: list[float] = []
    with torch.no_grad():
        for start in range(0, len(tensors), args.batch_size):
            batch = torch.stack(tensors[start:start + args.batch_size]).to(device)
            logits = model(batch)
            probs.extend([float(v) for v in torch.sigmoid(logits).cpu().numpy()])
    return probs


def _predict_meta_probs(
    model: nn.Module,
    tensors: list[torch.Tensor],
    meta: list[np.ndarray],
    mean: np.ndarray,
    std: np.ndarray,
    args: argparse.Namespace,
) -> list[float]:
    device = next(model.parameters()).device
    model.eval()
    probs: list[float] = []
    normalized = [((row - mean) / std).astype(np.float32) for row in meta]
    with torch.no_grad():
        for start in range(0, len(tensors), args.batch_size):
            batch = torch.stack(tensors[start:start + args.batch_size]).to(device)
            meta_batch = torch.from_numpy(np.stack(normalized[start:start + args.batch_size])).float().to(device)
            logits = model(batch, meta_batch)
            probs.extend([float(v) for v in torch.sigmoid(logits).cpu().numpy()])
    return probs


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _mean_mask(values: np.ndarray, mask: np.ndarray) -> float:
    if values.size == 0 or mask.size == 0 or not bool(mask.any()):
        return 0.0
    return float(values[mask].mean())


def _panelness_score_from_rgb(rgb: np.ndarray, box: list[int]) -> float:
    """Heuristic score for sponsor/template/contingency panel-like false positives."""
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = [int(v) for v in box]
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    box_w = max(1, x1 - x0)
    box_h = max(1, y1 - y0)
    box_area = float(box_w * box_h)
    pad = max(8, min(72, int(max(box_w, box_h) * 0.45)))
    wx0 = max(0, x0 - pad)
    wy0 = max(0, y0 - pad)
    wx1 = min(width, x1 + pad)
    wy1 = min(height, y1 + pad)
    crop = rgb[wy0:wy1, wx0:wx1]
    if crop.size == 0:
        return 0.0

    local = [x0 - wx0, y0 - wy0, x1 - wx0, y1 - wy0]
    ch, cw = crop.shape[:2]
    inside = np.zeros((ch, cw), dtype=bool)
    inside[local[1]:local[3], local[0]:local[2]] = True
    expanded = np.ones((ch, cw), dtype=bool)
    ring = expanded & ~inside
    border = np.zeros((ch, cw), dtype=bool)
    band = max(2, min(10, int(min(box_w, box_h) * 0.12)))
    bx0, by0, bx1, by1 = local
    border[by0:min(by1, by0 + band), bx0:bx1] = True
    border[max(by0, by1 - band):by1, bx0:bx1] = True
    border[by0:by1, bx0:min(bx1, bx0 + band)] = True
    border[by0:by1, max(bx0, bx1 - band):bx1] = True

    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1].astype(np.float32) / 255.0
    luma = gray.astype(np.float32) / 255.0
    edges = cv2.Canny(gray, 35, 130) > 0
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.abs(grad_x) + np.abs(grad_y)
    axis_strength = np.abs(np.abs(grad_x) - np.abs(grad_y)) / np.maximum(1.0, grad_mag)

    inside_edge = _mean_mask(edges.astype(np.float32), inside)
    border_edge = _mean_mask(edges.astype(np.float32), border)
    ring_edge = _mean_mask(edges.astype(np.float32), ring)
    edge_axis = _mean_mask(axis_strength, edges & (grad_mag > 18))
    sat_mean = _mean_mask(sat, inside)
    sat_ring = _mean_mask(sat, ring)
    contrast = float(np.percentile(luma[inside], 92) - np.percentile(luma[inside], 8)) if inside.any() else 0.0

    inside_pixels = crop[inside]
    if inside_pixels.size:
        quantized = np.unique((inside_pixels // 32).reshape(-1, 3), axis=0)
        color_complexity = _clamp01((len(quantized) - 4) / 26.0)
    else:
        color_complexity = 0.0

    salient = ((sat > 0.24) | (luma < 0.16) | (luma > 0.84) | edges).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(salient, 8)
    small_components = 0
    enclosing_score = 0.0
    for comp in range(1, count):
        cx, cy, cw_stat, ch_stat, area = [int(v) for v in stats[comp]]
        if area < 4:
            continue
        comp_mask = labels == comp
        overlap = float((comp_mask & inside).sum()) / max(1.0, box_area)
        if 5 <= area <= max(420, box_area * 0.32) and overlap > 0.02:
            small_components += 1
        comp_x1 = cx + cw_stat
        comp_y1 = cy + ch_stat
        contains_center = cx <= (bx0 + bx1) * 0.5 <= comp_x1 and cy <= (by0 + by1) * 0.5 <= comp_y1
        wraps_box = cx <= bx0 + band and cy <= by0 + band and comp_x1 >= bx1 - band and comp_y1 >= by1 - band
        if overlap > 0.32 and (contains_center or wraps_box):
            area_ratio = min(1.0, area / max(1.0, box_area * 2.8))
            bbox_ratio = min(1.0, (cw_stat * ch_stat) / max(1.0, box_area * 2.6))
            enclosing_score = max(enclosing_score, 0.55 * area_ratio + 0.45 * bbox_ratio)

    small_component_score = _clamp01((small_components - 3) / 18.0)
    border_score = _clamp01((border_edge - max(0.04, inside_edge * 0.55)) / 0.24)
    ring_score = _clamp01((ring_edge - 0.045) / 0.18)
    axis_score = _clamp01((edge_axis - 0.46) / 0.32)
    saturation_panel = _clamp01(((sat_mean + sat_ring) * 0.5 - 0.22) / 0.45)
    contrast_score = _clamp01((contrast - 0.38) / 0.45)

    score = (
        0.20 * border_score
        + 0.17 * ring_score
        + 0.18 * small_component_score
        + 0.16 * color_complexity
        + 0.17 * enclosing_score
        + 0.07 * axis_score
        + 0.03 * saturation_panel
        + 0.02 * contrast_score
    )
    if small_components <= 3 and color_complexity < 0.22 and ring_edge < 0.08:
        score *= 0.72
    return _clamp01(score)


def _combined_score(
    rank_model: str,
    image_prob: float | None,
    meta_prob: float | None,
    image_blend_weight: float,
    meta_veto_threshold: float,
    meta_veto_penalty: float,
) -> float:
    if rank_model == "meta":
        return float(meta_prob if meta_prob is not None else 0.0)
    if rank_model == "image_meta_veto":
        if image_prob is None or meta_prob is None:
            raise ValueError("image_meta_veto requires both image and metadata scores")
        return image_prob if meta_prob >= meta_veto_threshold else image_prob * meta_veto_penalty
    if rank_model == "image_meta_blend":
        if image_prob is None or meta_prob is None:
            raise ValueError("image_meta_blend requires both image and metadata scores")
        w = _clamp01(image_blend_weight)
        return image_prob * w + meta_prob * (1.0 - w)
    if rank_model == "image_meta_product":
        if image_prob is None or meta_prob is None:
            raise ValueError("image_meta_product requires both image and metadata scores")
        w = _clamp01(image_blend_weight)
        return float(np.exp(w * np.log(max(1e-6, image_prob)) + (1.0 - w) * np.log(max(1e-6, meta_prob))))
    return float(image_prob if image_prob is not None else 0.0)


def _blend_optional_scores(image_prob: float | None, meta_prob: float | None, image_blend_weight: float) -> float | None:
    if image_prob is None and meta_prob is None:
        return None
    if image_prob is None:
        return float(meta_prob)
    if meta_prob is None:
        return float(image_prob)
    w = _clamp01(image_blend_weight)
    return float(image_prob) * w + float(meta_prob) * (1.0 - w)


def _apply_confuser_penalty(score: float, confuser_prob: float | None, args: argparse.Namespace) -> float:
    penalty_weight = max(0.0, float(args.confuser_penalty_weight))
    if penalty_weight <= 0.0 or confuser_prob is None:
        return float(score)
    return float(score) * max(0.0, 1.0 - penalty_weight * _clamp01(confuser_prob))


def _apply_context_confuser_penalty(score: float, confuser_prob: float | None, args: argparse.Namespace) -> float:
    penalty_weight = max(0.0, float(args.context_confuser_penalty_weight))
    if penalty_weight <= 0.0 or confuser_prob is None:
        return float(score)
    return float(score) * max(0.0, 1.0 - penalty_weight * _clamp01(confuser_prob))


def _context_confuser_enabled(args: argparse.Namespace) -> bool:
    return bool(args.context_confuser_penalty_weight > 0 or getattr(args, "context_frontier", False))


def _sibling_boost_enabled(args: argparse.Namespace) -> bool:
    return bool(float(getattr(args, "sibling_boost_weight", 0.0)) > 0.0)


def _sibling_digit_gate_enabled(args: argparse.Namespace) -> bool:
    return bool(_sibling_boost_enabled(args) and getattr(args, "sibling_digit_gate", False))


def _apply_panel_penalty(score: float, panel_score: float | None, args: argparse.Namespace) -> float:
    penalty_weight = max(0.0, float(args.panel_penalty_weight))
    if penalty_weight <= 0.0 or panel_score is None:
        return float(score)
    return float(score) * max(0.0, 1.0 - penalty_weight * _clamp01(panel_score))


def _parse_float_csv(raw: str) -> list[float]:
    values: list[float] = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        values.append(_clamp01(float(text)))
    if not values:
        raise ValueError("score sweep needs at least one weight")
    return values


def _parse_mode_csv(raw: str) -> list[str]:
    modes: list[str] = []
    for part in raw.split(","):
        mode = part.strip()
        if not mode:
            continue
        if mode not in SCORE_SWEEP_MODES:
            raise ValueError(f"unsupported score sweep mode: {mode}")
        if mode not in modes:
            modes.append(mode)
    if not modes:
        raise ValueError("score sweep needs at least one mode")
    return modes


def _score_sweep_specs(args: argparse.Namespace) -> list[dict[str, Any]]:
    if not args.score_sweep:
        return []
    modes = _parse_mode_csv(args.score_sweep_modes)
    weights = _parse_float_csv(args.score_sweep_weights)
    specs: list[dict[str, Any]] = []
    for mode in modes:
        if mode in {"image", "meta", "image_meta_veto"}:
            if mode == "image_meta_veto":
                key = f"{mode}_t{args.meta_veto_threshold:.3f}_p{args.meta_veto_penalty:.3f}"
            else:
                key = mode
            specs.append({"key": key, "mode": mode, "image_blend_weight": None})
            continue
        for weight in weights:
            specs.append({
                "key": f"{mode}_w{weight:.2f}",
                "mode": mode,
                "image_blend_weight": weight,
            })
    return specs


def _context_frontier_specs(
    args: argparse.Namespace,
    sweep_specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not getattr(args, "context_frontier", False):
        return []
    thresholds: list[float] = []
    for threshold in _parse_float_csv(args.context_frontier_thresholds):
        if threshold not in thresholds:
            thresholds.append(threshold)
    specs: list[dict[str, Any]] = []
    for spec in sweep_specs:
        for threshold in thresholds:
            threshold_key = f"ctxlte{threshold:.2f}"
            specs.append({
                "key": f"{spec['key']}__{threshold_key}",
                "base_key": spec["key"],
                "mode": spec["mode"],
                "image_blend_weight": spec["image_blend_weight"],
                "context_confuser_threshold": threshold,
            })
    return specs


def _context_frontier_scored(scored: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for candidate in scored:
        context_score = candidate.get("context_confuser_score")
        if context_score is not None and float(context_score) > threshold:
            continue
        out = dict(candidate)
        out["context_frontier_threshold"] = round(float(threshold), 4)
        filtered.append(out)
    for rank, candidate in enumerate(filtered, start=1):
        candidate["rank"] = rank
    return filtered


def _sibling_signature_from_crop(crop: Image.Image) -> np.ndarray:
    arr = np.asarray(crop.convert("L").resize((48, 48), Image.Resampling.LANCZOS)).astype(np.float32) / 255.0
    grad_x = cv2.Sobel(arr, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(arr, cv2.CV_32F, 0, 1, ksize=3)
    edge = np.abs(grad_x) + np.abs(grad_y)
    edge = cv2.resize(edge, (8, 8), interpolation=cv2.INTER_AREA).astype(np.float32)
    edge -= float(edge.mean())
    denom = float(edge.std())
    if denom > 1e-4:
        edge /= denom
    return edge


def _digit_mask_quality(mask: np.ndarray, valid: np.ndarray) -> dict[str, float]:
    mask = (mask > 0) & valid
    total = int(mask.sum())
    valid_count = max(1, int(valid.sum()))
    if total <= 8:
        return {"score": 0.0}
    labels_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    components: list[tuple[int, int, int, int, int]] = []
    small_count = 0
    for comp in range(1, labels_count):
        x, y, w, h, area = [int(v) for v in stats[comp]]
        if area < 5:
            continue
        touches_border = x <= 1 or y <= 1 or x + w >= mask.shape[1] - 1 or y + h >= mask.shape[0] - 1
        if touches_border and area > valid_count * 0.28:
            continue
        if area < 80:
            small_count += 1
        components.append((x, y, w, h, area))
    if not components:
        return {"score": 0.0}
    components.sort(key=lambda item: item[4], reverse=True)
    large_components = [item for item in components if item[4] >= max(80, valid_count * 0.012)]
    if not large_components:
        return {"score": 0.0}

    top_area = sum(item[4] for item in components[:3])
    total_area = sum(item[4] for item in components)
    x0 = min(item[0] for item in large_components)
    y0 = min(item[1] for item in large_components)
    x1 = max(item[0] + item[2] for item in large_components)
    y1 = max(item[1] + item[3] for item in large_components)
    span_x = (x1 - x0) / float(mask.shape[1])
    span_y = (y1 - y0) / float(mask.shape[0])
    fill = total_area / float(valid_count)
    top_share = top_area / max(1.0, float(total_area))
    large_count = len(large_components)

    fill_score = max(0.0, 1.0 - abs(fill - 0.26) / 0.30)
    span_score = _clamp01((max(span_x, span_y) - 0.28) / 0.40)
    top_share_score = _clamp01((top_share - 0.42) / 0.42)
    large_count_score = _clamp01(1.0 - abs(large_count - 3.0) / 7.0)
    clutter_penalty = _clamp01((small_count - 14) / 34.0)
    extreme_penalty = 0.0
    if fill < 0.035 or fill > 0.72:
        extreme_penalty += 0.22
    if span_x < 0.14 and span_y < 0.14:
        extreme_penalty += 0.22

    score = (
        0.30 * fill_score
        + 0.26 * span_score
        + 0.24 * top_share_score
        + 0.20 * large_count_score
    )
    score *= max(0.0, 1.0 - 0.65 * clutter_penalty - extreme_penalty)
    return {
        "score": _clamp01(score),
        "fill": round(fill, 6),
        "span_x": round(span_x, 6),
        "span_y": round(span_y, 6),
        "top_share": round(top_share, 6),
        "large_count": float(large_count),
        "small_count": float(small_count),
    }


def _number_stroke_score_from_crop(crop: Image.Image) -> dict[str, float]:
    arr = np.asarray(crop.convert("RGB").resize((96, 96), Image.Resampling.LANCZOS))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    valid = arr.max(axis=2) > 5
    if int(valid.sum()) < 64:
        valid = np.ones(gray.shape, dtype=bool)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _thr, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = (otsu == 0)
    bright = (otsu > 0)
    edges = cv2.Canny(gray, 35, 130) > 0
    edge_stroke = cv2.dilate(edges.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1) > 0
    sat_stroke = (sat > 80) & edge_stroke

    candidates = [
        _digit_mask_quality(dark, valid),
        _digit_mask_quality(bright, valid),
        _digit_mask_quality(edge_stroke, valid),
        _digit_mask_quality(sat_stroke | edge_stroke, valid),
    ]
    best = max(candidates, key=lambda row: row.get("score", 0.0))
    return best


def _sibling_similarity(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None:
        return 0.0
    av = a.reshape(-1).astype(np.float32)
    candidates = [b, np.fliplr(b)]
    best = 0.0
    denom_a = float(np.linalg.norm(av))
    if denom_a <= 1e-6:
        return 0.0
    for variant in candidates:
        bv = variant.reshape(-1).astype(np.float32)
        denom_b = float(np.linalg.norm(bv))
        if denom_b <= 1e-6:
            continue
        best = max(best, float(np.dot(av, bv) / (denom_a * denom_b)))
    return _clamp01((best + 1.0) * 0.5)


def _candidate_area(candidate: dict[str, Any]) -> float:
    box = candidate.get("xyxy") or _candidate_xyxy(candidate)
    return float(max(1, int(box[2]) - int(box[0])) * max(1, int(box[3]) - int(box[1])))


def _candidate_aspect(candidate: dict[str, Any]) -> float:
    box = candidate.get("xyxy") or _candidate_xyxy(candidate)
    return float(max(1, int(box[2]) - int(box[0]))) / float(max(1, int(box[3]) - int(box[1])))


def _sibling_size_similarity(candidate: dict[str, Any], seed: dict[str, Any], args: argparse.Namespace) -> float:
    area_a = _candidate_area(candidate)
    area_b = _candidate_area(seed)
    aspect_a = _candidate_aspect(candidate)
    aspect_b = _candidate_aspect(seed)
    area_ratio = max(area_a, area_b) / max(1.0, min(area_a, area_b))
    aspect_ratio = max(aspect_a, aspect_b) / max(0.001, min(aspect_a, aspect_b))
    area_score = max(0.0, 1.0 - (area_ratio - 1.0) / max(0.01, float(args.sibling_boost_area_ratio)))
    aspect_score = max(0.0, 1.0 - (aspect_ratio - 1.0) / max(0.01, float(args.sibling_boost_aspect_ratio)))
    return _clamp01(0.58 * area_score + 0.42 * aspect_score)


def _apply_sibling_boost(scored: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    if not _sibling_boost_enabled(args):
        return scored
    weight = max(0.0, float(args.sibling_boost_weight))
    seed_rank = max(1, int(args.sibling_boost_seed_rank))
    seed_min = float(args.sibling_boost_seed_min)
    sim_min = float(args.sibling_boost_similarity)
    ordered = sorted(scored, key=lambda c: float(c["score"]), reverse=True)
    for rank, candidate in enumerate(ordered, start=1):
        candidate["rank"] = rank
    digit_min = float(getattr(args, "sibling_digit_min", 0.0))
    digit_gate = _sibling_digit_gate_enabled(args)
    seeds = []
    for candidate in ordered[:seed_rank]:
        if float(candidate["score"]) < seed_min or candidate.get("_sibling_signature") is None:
            continue
        if digit_gate and float(candidate.get("number_stroke_score", 0.0)) < digit_min:
            continue
        seeds.append(candidate)
    if not seeds:
        for rank, candidate in enumerate(sorted(scored, key=lambda c: float(c["score"]), reverse=True), start=1):
            candidate["rank"] = rank
        return scored

    boosted: list[dict[str, Any]] = []
    for candidate in scored:
        out = dict(candidate)
        original_score = float(candidate["score"])
        best_boost = 0.0
        best_seed: dict[str, Any] | None = None
        best_similarity = 0.0
        best_size_similarity = 0.0
        for seed in seeds:
            if seed is candidate or _box_iou(candidate.get("xyxy") or _candidate_xyxy(candidate), seed.get("xyxy") or _candidate_xyxy(seed)) > 0.22:
                continue
            if digit_gate and float(candidate.get("number_stroke_score", 0.0)) < digit_min:
                continue
            visual_similarity = _sibling_similarity(candidate.get("_sibling_signature"), seed.get("_sibling_signature"))
            size_similarity = _sibling_size_similarity(candidate, seed, args)
            similarity = visual_similarity * size_similarity
            if similarity < sim_min:
                continue
            seed_score = float(seed["score"])
            if seed_score <= original_score:
                continue
            boost = weight * similarity * (seed_score - original_score)
            if boost > best_boost:
                best_boost = boost
                best_seed = seed
                best_similarity = visual_similarity
                best_size_similarity = size_similarity
        if best_seed is not None and best_boost > 0.0:
            out["pre_sibling_score"] = round(original_score, 6)
            out["sibling_score_delta"] = round(best_boost, 6)
            out["sibling_similarity"] = round(best_similarity, 6)
            out["sibling_size_similarity"] = round(best_size_similarity, 6)
            out["sibling_seed_score"] = round(float(best_seed["score"]), 6)
            out["sibling_seed_rank"] = int(best_seed.get("rank") or 0)
            out["sibling_seed_proposal_index"] = best_seed.get("proposal_index")
            out["score"] = round(min(0.999999, original_score + best_boost), 6)
        boosted.append(out)
    boosted.sort(key=lambda c: c["score"], reverse=True)
    for rank, candidate in enumerate(boosted, start=1):
        candidate["rank"] = rank
    return boosted


def _json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _json_clean(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [_json_clean(item) for item in value]
    if isinstance(value, tuple):
        return [_json_clean(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _rescore_scored_candidates(
    scored: list[dict[str, Any]],
    spec: dict[str, Any],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    rescored: list[dict[str, Any]] = []
    weight = args.image_blend_weight if spec["image_blend_weight"] is None else float(spec["image_blend_weight"])
    for candidate in scored:
        image_prob = candidate.get("image_score")
        meta_prob = candidate.get("meta_score")
        prob = _combined_score(
            spec["mode"],
            float(image_prob) if image_prob is not None else None,
            float(meta_prob) if meta_prob is not None else None,
            weight,
            args.meta_veto_threshold,
            args.meta_veto_penalty,
        )
        pre_confuser_prob = prob
        confuser_prob = candidate.get("confuser_score")
        prob = _apply_confuser_penalty(
            pre_confuser_prob,
            float(confuser_prob) if confuser_prob is not None else None,
            args,
        )
        pre_context_confuser_prob = prob
        context_confuser_prob = candidate.get("context_confuser_score")
        prob = _apply_context_confuser_penalty(
            pre_context_confuser_prob,
            float(context_confuser_prob) if context_confuser_prob is not None else None,
            args,
        )
        pre_panel_prob = prob
        panel_score = candidate.get("panel_score")
        prob = _apply_panel_penalty(
            pre_panel_prob,
            float(panel_score) if panel_score is not None else None,
            args,
        )
        out = dict(candidate)
        if confuser_prob is not None and args.confuser_penalty_weight > 0:
            out["pre_confuser_score"] = round(pre_confuser_prob, 6)
        if context_confuser_prob is not None and _context_confuser_enabled(args):
            if args.context_confuser_penalty_weight > 0:
                out["pre_context_confuser_score"] = round(pre_context_confuser_prob, 6)
            out["context_confuser_score"] = round(float(context_confuser_prob), 6)
        if panel_score is not None and args.panel_penalty_weight > 0:
            out["pre_panel_score"] = round(pre_panel_prob, 6)
        out["score"] = round(prob, 6)
        out["score_sweep_key"] = spec["key"]
        out["score_sweep_mode"] = spec["mode"]
        if spec["image_blend_weight"] is not None:
            out["image_blend_weight"] = round(weight, 4)
        if spec["mode"] == "image_meta_veto":
            out["meta_vetoed"] = bool(meta_prob is not None and float(meta_prob) < args.meta_veto_threshold)
        rescored.append(out)
    rescored = _apply_sibling_boost(rescored, args)
    rescored.sort(key=lambda c: c["score"], reverse=True)
    for rank, candidate in enumerate(rescored, start=1):
        candidate["rank"] = rank
    return rescored


def _score_candidates(
    scorer: dict[str, Any],
    rgb: np.ndarray,
    candidates: list[dict[str, Any]],
    args: argparse.Namespace,
    source_path: Path | None = None,
) -> list[dict[str, Any]]:
    tensors: list[torch.Tensor] = []
    context_tensors: list[torch.Tensor] = []
    sibling_signatures: list[np.ndarray] = []
    number_stroke_details: list[dict[str, float]] = []
    meta_rows: list[np.ndarray] = []
    needs_meta = (
        args.rank_model in {"meta", "image_meta_veto", "image_meta_blend", "image_meta_product"}
        or "confuser_meta_model" in scorer
    )
    needs_context_confuser = "context_confuser_model" in scorer
    source_folder = source_path.parent.name if source_path else None
    source_value = str(source_path) if source_path else None
    for index, candidate in enumerate(candidates):
        candidate["proposal_index"] = index
        if source_value:
            candidate.setdefault("paint", source_value)
            candidate.setdefault("folder", source_folder)
        crop = _crop_square(rgb, tuple(candidate["box"]))
        tensors.append(_pil_to_tensor(crop, augment=False, rng=random.Random(0)))
        if _sibling_boost_enabled(args):
            sibling_signatures.append(_sibling_signature_from_crop(crop))
            number_stroke_details.append(_number_stroke_score_from_crop(crop))
        if needs_meta:
            meta_rows.append(_candidate_meta_vector(candidate, crop, rgb))
        if needs_context_confuser:
            context_tensors.append(
                _pil_to_tensor(
                    _context_crop_from_rgb(
                        rgb,
                        _candidate_xyxy(candidate),
                        args.context_confuser_pad_scale,
                        mark_box=True,
                    ),
                    augment=False,
                    rng=random.Random(0),
                )
            )
    if not tensors:
        return []
    image_probs: list[float] | None = None
    meta_probs: list[float] | None = None
    confuser_image_probs: list[float] | None = None
    confuser_meta_probs: list[float] | None = None
    context_confuser_probs: list[float] | None = None
    panel_scores: list[float] | None = None
    if "image_model" in scorer:
        image_probs = _predict_image_probs(scorer["image_model"], tensors, args)
    if "meta_model" in scorer:
        meta_probs = _predict_meta_probs(
            scorer["meta_model"],
            tensors,
            meta_rows,
            scorer["meta_mean"],
            scorer["meta_std"],
            args,
        )
    if "confuser_image_model" in scorer:
        confuser_image_probs = _predict_image_probs(scorer["confuser_image_model"], tensors, args)
    if "confuser_meta_model" in scorer:
        confuser_meta_probs = _predict_meta_probs(
            scorer["confuser_meta_model"],
            tensors,
            meta_rows,
            scorer["confuser_meta_mean"],
            scorer["confuser_meta_std"],
            args,
        )
    if "context_confuser_model" in scorer:
        context_confuser_probs = _predict_image_probs(scorer["context_confuser_model"], context_tensors, args)
    if args.panel_penalty_weight > 0:
        panel_scores = [_panelness_score_from_rgb(rgb, _candidate_xyxy(candidate)) for candidate in candidates]
    scored: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        image_prob = image_probs[index] if image_probs is not None else None
        meta_prob = meta_probs[index] if meta_probs is not None else None
        pre_confuser_prob = _combined_score(
            args.rank_model,
            image_prob,
            meta_prob,
            args.image_blend_weight,
            args.meta_veto_threshold,
            args.meta_veto_penalty,
        )
        confuser_image_prob = confuser_image_probs[index] if confuser_image_probs is not None else None
        confuser_meta_prob = confuser_meta_probs[index] if confuser_meta_probs is not None else None
        confuser_prob = _blend_optional_scores(
            confuser_image_prob,
            confuser_meta_prob,
            args.confuser_image_blend_weight,
        )
        prob = _apply_confuser_penalty(pre_confuser_prob, confuser_prob, args)
        pre_context_confuser_prob = prob
        context_confuser_prob = context_confuser_probs[index] if context_confuser_probs is not None else None
        prob = _apply_context_confuser_penalty(pre_context_confuser_prob, context_confuser_prob, args)
        pre_panel_prob = prob
        panel_score = panel_scores[index] if panel_scores is not None else None
        prob = _apply_panel_penalty(pre_panel_prob, panel_score, args)
        out = dict(candidate)
        out["proposal_index"] = index
        out["score"] = round(prob, 6)
        if image_prob is not None:
            out["image_score"] = round(float(image_prob), 6)
        if meta_prob is not None:
            out["meta_score"] = round(float(meta_prob), 6)
            out["meta_vetoed"] = bool(args.rank_model == "image_meta_veto" and meta_prob < args.meta_veto_threshold)
        if args.rank_model in {"image_meta_blend", "image_meta_product"}:
            out["image_blend_weight"] = round(float(args.image_blend_weight), 4)
        if confuser_prob is not None and args.confuser_penalty_weight > 0:
            out["pre_confuser_score"] = round(pre_confuser_prob, 6)
            out["confuser_score"] = round(float(confuser_prob), 6)
            if confuser_image_prob is not None:
                out["confuser_image_score"] = round(float(confuser_image_prob), 6)
            if confuser_meta_prob is not None:
                out["confuser_meta_score"] = round(float(confuser_meta_prob), 6)
        if context_confuser_prob is not None and _context_confuser_enabled(args):
            if args.context_confuser_penalty_weight > 0:
                out["pre_context_confuser_score"] = round(pre_context_confuser_prob, 6)
            out["context_confuser_score"] = round(float(context_confuser_prob), 6)
        if panel_score is not None and args.panel_penalty_weight > 0:
            out["pre_panel_score"] = round(pre_panel_prob, 6)
            out["panel_score"] = round(float(panel_score), 6)
        out["xyxy"] = _candidate_xyxy(candidate)
        if _sibling_boost_enabled(args):
            out["_sibling_signature"] = sibling_signatures[index]
            stroke_detail = number_stroke_details[index]
            out["_number_stroke_detail"] = stroke_detail
            out["number_stroke_score"] = round(float(stroke_detail.get("score", 0.0)), 6)
        scored.append(out)
    scored = _apply_sibling_boost(scored, args)
    scored.sort(key=lambda c: c["score"], reverse=True)
    for rank, candidate in enumerate(scored, start=1):
        candidate["rank"] = rank
    return scored


def _source_groups(positives: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in positives:
        groups.setdefault(rec["source_path"], []).append(rec)
    return groups


def _assign_ranks(
    positives: list[dict[str, Any]],
    scored_by_source: dict[str, list[dict[str, Any]]],
    iou_threshold: float,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for rec in positives:
        scored = scored_by_source.get(rec["source_path"], [])
        best_iou = 0.0
        best_rank: int | None = None
        best_score = 0.0
        best_candidate: dict[str, Any] | None = None
        for candidate in scored:
            iou = _box_iou(rec["gt_box"], candidate["xyxy"])
            if iou > best_iou:
                best_iou = iou
                best_candidate = candidate
                best_score = float(candidate["score"])
            if iou >= iou_threshold and (best_rank is None or int(candidate["rank"]) < best_rank):
                best_rank = int(candidate["rank"])
        out = dict(rec)
        out["best_iou"] = round(best_iou, 6)
        out["best_rank"] = best_rank
        out["best_score"] = round(best_score, 6)
        out["best_candidate"] = best_candidate
        ranked.append(out)
    return ranked


def _assign_hard_negative_pressure(
    negatives: list[dict[str, Any]],
    scored_by_source: dict[str, list[dict[str, Any]]],
    iou_threshold: float,
) -> list[dict[str, Any]]:
    pressured: list[dict[str, Any]] = []
    for rec in negatives:
        scored = scored_by_source.get(rec["source_path"], [])
        best_iou = 0.0
        best_iou_score = 0.0
        best_iou_candidate: dict[str, Any] | None = None
        best_rank: int | None = None
        best_score = 0.0
        best_rank_candidate: dict[str, Any] | None = None
        for candidate in scored:
            iou = _box_iou(rec["gt_box"], candidate["xyxy"])
            if iou > best_iou:
                best_iou = iou
                best_iou_candidate = candidate
                best_iou_score = float(candidate["score"])
            if iou >= iou_threshold and (best_rank is None or int(candidate["rank"]) < best_rank):
                best_rank = int(candidate["rank"])
                best_score = float(candidate["score"])
                best_rank_candidate = candidate
        out = dict(rec)
        out["best_iou"] = round(best_iou, 6)
        out["best_iou_score"] = round(best_iou_score, 6)
        out["best_iou_candidate"] = best_iou_candidate
        out["best_rank"] = best_rank
        out["best_score"] = round(best_score if best_rank_candidate is not None else best_iou_score, 6)
        out["best_candidate"] = best_rank_candidate or best_iou_candidate
        pressured.append(out)
    return pressured


def _top_unmatched(
    source_path: str,
    scored: list[dict[str, Any]],
    positives: list[dict[str, Any]],
    iou_threshold: float,
    limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in scored:
        if any(_box_iou(pos["gt_box"], candidate["xyxy"]) >= iou_threshold for pos in positives):
            continue
        row = dict(candidate)
        row["source_path"] = source_path
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def _aggregate_ranked(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "samples": len(records),
        "mean_best_iou": round(float(np.mean([r["best_iou"] for r in records])) if records else 0.0, 6),
        "median_best_iou": round(float(np.median([r["best_iou"] for r in records])) if records else 0.0, 6),
        "covered_by_proposals": sum(1 for r in records if r["best_iou"] >= 0.25),
    }
    for top_k in TOP_K:
        covered = sum(1 for r in records if r["best_rank"] is not None and int(r["best_rank"]) <= top_k)
        summary[f"top_{top_k}_recall"] = round(covered / max(1, len(records)), 6)
        summary[f"top_{top_k}_covered"] = covered
    ranks = [int(r["best_rank"]) for r in records if r["best_rank"] is not None]
    summary["median_matched_rank"] = round(float(np.median(ranks)) if ranks else 0.0, 3)
    return summary


def _aggregate_by(records: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        groups.setdefault(str(rec.get(field) or "unknown"), []).append(rec)
    return {name: _aggregate_ranked(group) for name, group in sorted(groups.items())}


def _aggregate_hard_negative_pressure(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "samples": len(records),
        "mean_best_iou": round(float(np.mean([r["best_iou"] for r in records])) if records else 0.0, 6),
        "median_best_iou": round(float(np.median([r["best_iou"] for r in records])) if records else 0.0, 6),
        "matched_by_proposals": sum(1 for r in records if r["best_iou"] >= 0.25),
    }
    for top_k in TOP_K:
        exposed = sum(1 for r in records if r["best_rank"] is not None and int(r["best_rank"]) <= top_k)
        summary[f"top_{top_k}_exposed"] = exposed
        summary[f"top_{top_k}_exposure_rate"] = round(exposed / max(1, len(records)), 6)
    ranks = [int(r["best_rank"]) for r in records if r["best_rank"] is not None]
    summary["median_exposed_rank"] = round(float(np.median(ranks)) if ranks else 0.0, 3)
    return summary


def _aggregate_hard_negative_by(records: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        groups.setdefault(str(rec.get(field) or "unknown"), []).append(rec)
    return {name: _aggregate_hard_negative_pressure(group) for name, group in sorted(groups.items())}


def _candidate_quality(
    scored_by_source: dict[str, list[dict[str, Any]]],
    positives_by_source: dict[str, list[dict[str, Any]]],
    iou_threshold: float,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for top_k in TOP_K:
        candidate_slots = 0
        known_positive_candidates = 0
        unmatched_candidates = 0
        known_positive_boxes = 0
        known_positive_boxes_covered = 0
        for source, scored in scored_by_source.items():
            positives = positives_by_source.get(source, [])
            top = scored[:top_k]
            candidate_slots += len(top)
            known_positive_boxes += len(positives)
            for candidate in top:
                if any(_box_iou(pos["gt_box"], candidate["xyxy"]) >= iou_threshold for pos in positives):
                    known_positive_candidates += 1
                else:
                    unmatched_candidates += 1
            for pos in positives:
                if any(_box_iou(pos["gt_box"], candidate["xyxy"]) >= iou_threshold for candidate in top):
                    known_positive_boxes_covered += 1
        rows[f"top_{top_k}"] = {
            "candidate_slots": candidate_slots,
            "known_positive_candidates": known_positive_candidates,
            "unmatched_candidates": unmatched_candidates,
            "known_positive_boxes": known_positive_boxes,
            "known_positive_boxes_covered": known_positive_boxes_covered,
            "known_positive_box_recall": round(known_positive_boxes_covered / max(1, known_positive_boxes), 6),
            "known_precision_floor": round(known_positive_candidates / max(1, candidate_slots), 6),
        }
    return rows


def _merge_candidate_quality(rows: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for top_k in TOP_K:
        key = f"top_{top_k}"
        totals = {
            "candidate_slots": 0,
            "known_positive_candidates": 0,
            "unmatched_candidates": 0,
            "known_positive_boxes": 0,
            "known_positive_boxes_covered": 0,
        }
        for row in rows:
            data = row.get(key, {})
            for field in totals:
                totals[field] += int(data.get(field, 0))
        totals["known_positive_box_recall"] = round(
            totals["known_positive_boxes_covered"] / max(1, totals["known_positive_boxes"]),
            6,
        )
        totals["known_precision_floor"] = round(
            totals["known_positive_candidates"] / max(1, totals["candidate_slots"]),
            6,
        )
        merged[key] = totals
    return merged


def _safe_filename_key(key: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in key)


def _sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 5
    cell = 220
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    rgb_cache: dict[str, np.ndarray] = {}
    for idx, rec in enumerate(records):
        source = rec["source_path"]
        if source not in rgb_cache:
            rgb_cache[source] = _read_rgb(Path(source))
        rgb = rgb_cache[source]
        candidate = rec.get("best_candidate") or rec
        box = candidate.get("xyxy") or _candidate_xyxy(candidate)
        x0 = max(0, min(rec.get("gt_box", box)[0], box[0]) - 34)
        y0 = max(0, min(rec.get("gt_box", box)[1], box[1]) - 34)
        x1 = min(rgb.shape[1], max(rec.get("gt_box", box)[2], box[2]) + 34)
        y1 = min(rgb.shape[0], max(rec.get("gt_box", box)[3], box[3]) + 34)
        crop = Image.fromarray(rgb[y0:y1, x0:x1]).convert("RGB")
        local = [box[0] - x0, box[1] - y0, box[2] - x0, box[3] - y0]
        cdraw = ImageDraw.Draw(crop)
        cdraw.rectangle(local, outline=(255, 225, 50), width=3)
        if "gt_box" in rec:
            gt = rec["gt_box"]
            cdraw.rectangle([gt[0] - x0, gt[1] - y0, gt[2] - x0, gt[3] - y0], outline=(255, 80, 80), width=4)
        crop.thumbnail((194, 154), Image.Resampling.LANCZOS)
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        sheet.paste(crop, (x + 12, y + 28))
        rank = rec.get("best_rank", rec.get("rank", "?"))
        score = rec.get("best_score", rec.get("score", 0.0))
        draw.text((x + 6, y + 6), f"rank {rank} p {float(score):.2f} iou {float(rec.get('best_iou', 0.0)):.2f}", fill=(255, 230, 130))
        extras: list[str] = []
        panel_score = candidate.get("panel_score", rec.get("panel_score"))
        confuser_score = candidate.get("confuser_score", rec.get("confuser_score"))
        context_confuser_score = candidate.get("context_confuser_score", rec.get("context_confuser_score"))
        number_stroke_score = candidate.get("number_stroke_score", rec.get("number_stroke_score"))
        if panel_score is not None:
            extras.append(f"panel {float(panel_score):.2f}")
        if confuser_score is not None:
            extras.append(f"conf {float(confuser_score):.2f}")
        if context_confuser_score is not None:
            extras.append(f"ctx {float(context_confuser_score):.2f}")
        if number_stroke_score is not None:
            extras.append(f"num {float(number_stroke_score):.2f}")
        sibling_delta = candidate.get("sibling_score_delta", rec.get("sibling_score_delta"))
        sibling_similarity = candidate.get("sibling_similarity", rec.get("sibling_similarity"))
        if sibling_delta is not None:
            suffix = f" sim {float(sibling_similarity):.2f}" if sibling_similarity is not None else ""
            extras.append(f"sib +{float(sibling_delta):.2f}{suffix}")
        if extras:
            draw.text((x + 6, y + 18), " ".join(extras)[:32], fill=(170, 220, 255))
        draw.text((x + 6, y + 198), str(Path(source).parent.name)[:30], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    records = _load_manifest(args.manifest, args.holdout_mode)
    folds = _make_folds(records, args.folds, args.seed)
    if args.max_folds:
        folds = folds[:args.max_folds]
    sweep_specs = _score_sweep_specs(args)
    if sweep_specs and args.rank_model not in {"image_meta_veto", "image_meta_blend", "image_meta_product"}:
        raise ValueError("--score-sweep requires a rank model that trains both image and metadata scorers")
    if args.context_frontier and not sweep_specs:
        raise ValueError("--context-frontier requires --score-sweep so thresholds can be compared against replayed score variants")
    frontier_specs = _context_frontier_specs(args, sweep_specs)
    frontier_specs_by_base: dict[str, list[dict[str, Any]]] = {}
    for spec in frontier_specs:
        frontier_specs_by_base.setdefault(spec["base_key"], []).append(spec)
    args.output.mkdir(parents=True, exist_ok=True)
    all_ranked: list[dict[str, Any]] = []
    all_unmatched: list[dict[str, Any]] = []
    all_hard_negative_pressure: list[dict[str, Any]] = []
    all_candidate_quality: list[dict[str, dict[str, Any]]] = []
    fold_summaries: list[dict[str, Any]] = []
    sweep_ranked: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in sweep_specs}
    sweep_hard_negative_pressure: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in sweep_specs}
    sweep_candidate_quality: dict[str, list[dict[str, dict[str, Any]]]] = {spec["key"]: [] for spec in sweep_specs}
    sweep_fold_summaries: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in sweep_specs}
    sweep_unmatched: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in sweep_specs}
    sweep_specs_by_key = {spec["key"]: spec for spec in sweep_specs}
    frontier_ranked: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in frontier_specs}
    frontier_hard_negative_pressure: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in frontier_specs}
    frontier_candidate_quality: dict[str, list[dict[str, dict[str, Any]]]] = {spec["key"]: [] for spec in frontier_specs}
    frontier_fold_summaries: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in frontier_specs}
    frontier_unmatched: dict[str, list[dict[str, Any]]] = {spec["key"]: [] for spec in frontier_specs}
    frontier_specs_by_key = {spec["key"]: spec for spec in frontier_specs}
    for fold_no, test_idx in enumerate(folds):
        train_idx = [idx for idx in range(len(records)) if idx not in test_idx]
        positives = _positive_records(records, test_idx)
        if not positives:
            continue
        negatives = _hard_negative_records(records, test_idx)
        scorer = _train_scorer(records, train_idx, args, args.seed + fold_no * 37)
        positives_by_source = _source_groups(positives)
        negatives_by_source = _source_groups(negatives)
        scored_by_source: dict[str, list[dict[str, Any]]] = {}
        source_keys = sorted(set(positives_by_source) | set(negatives_by_source))
        for source in source_keys:
            source_path = Path(source)
            rgb = _read_rgb(source_path)
            proposals = _proposal_boxes(rgb, args.max_boxes, args.variant)
            scored = _score_candidates(scorer, rgb, proposals, args, source_path)
            scored_by_source[source] = scored
        positive_scored_by_source = {source: scored_by_source[source] for source in positives_by_source if source in scored_by_source}
        for source, source_positives in positives_by_source.items():
            scored = scored_by_source.get(source, [])
            all_unmatched.extend(_top_unmatched(source, scored, source_positives, args.iou_threshold, args.unmatched_per_source))
        hard_negative_pressure = _assign_hard_negative_pressure(negatives, scored_by_source, args.iou_threshold)
        for rec in hard_negative_pressure:
            rec["fold"] = fold_no
        all_hard_negative_pressure.extend(hard_negative_pressure)
        for spec in sweep_specs:
            rescored_by_source = {
                source: _rescore_scored_candidates(scored, spec, args)
                for source, scored in scored_by_source.items()
            }
            positive_rescored_by_source = {
                source: rescored_by_source[source]
                for source in positives_by_source
                if source in rescored_by_source
            }
            sweep_quality = _candidate_quality(positive_rescored_by_source, positives_by_source, args.iou_threshold)
            sweep_candidate_quality[spec["key"]].append(sweep_quality)
            for source, scored in rescored_by_source.items():
                if source not in positives_by_source:
                    continue
                sweep_unmatched[spec["key"]].extend(
                    _top_unmatched(source, scored, positives_by_source.get(source, []), args.iou_threshold, args.unmatched_per_source)
                )
            sweep_records = _assign_ranks(positives, rescored_by_source, args.iou_threshold)
            for rec in sweep_records:
                rec["fold"] = fold_no
                rec["score_sweep_key"] = spec["key"]
            sweep_ranked[spec["key"]].extend(sweep_records)
            sweep_negatives = _assign_hard_negative_pressure(negatives, rescored_by_source, args.iou_threshold)
            for rec in sweep_negatives:
                rec["fold"] = fold_no
                rec["score_sweep_key"] = spec["key"]
            sweep_hard_negative_pressure[spec["key"]].extend(sweep_negatives)
            sweep_fold_summaries[spec["key"]].append({
                "fold": fold_no,
                "ranked": _aggregate_ranked(sweep_records),
                "hard_negative_pressure": _aggregate_hard_negative_pressure(sweep_negatives),
                "candidate_quality": sweep_quality,
            })
            for frontier_spec in frontier_specs_by_base.get(spec["key"], []):
                threshold = float(frontier_spec["context_confuser_threshold"])
                frontier_by_source = {
                    source: _context_frontier_scored(scored, threshold)
                    for source, scored in rescored_by_source.items()
                }
                positive_frontier_by_source = {
                    source: frontier_by_source[source]
                    for source in positives_by_source
                    if source in frontier_by_source
                }
                frontier_quality = _candidate_quality(positive_frontier_by_source, positives_by_source, args.iou_threshold)
                frontier_candidate_quality[frontier_spec["key"]].append(frontier_quality)
                for source, scored in frontier_by_source.items():
                    if source not in positives_by_source:
                        continue
                    frontier_unmatched[frontier_spec["key"]].extend(
                        _top_unmatched(
                            source,
                            scored,
                            positives_by_source.get(source, []),
                            args.iou_threshold,
                            args.unmatched_per_source,
                        )
                    )
                frontier_records = _assign_ranks(positives, frontier_by_source, args.iou_threshold)
                for rec in frontier_records:
                    rec["fold"] = fold_no
                    rec["score_sweep_key"] = spec["key"]
                    rec["context_frontier_key"] = frontier_spec["key"]
                    rec["context_confuser_threshold"] = round(threshold, 4)
                frontier_ranked[frontier_spec["key"]].extend(frontier_records)
                frontier_negatives = _assign_hard_negative_pressure(negatives, frontier_by_source, args.iou_threshold)
                for rec in frontier_negatives:
                    rec["fold"] = fold_no
                    rec["score_sweep_key"] = spec["key"]
                    rec["context_frontier_key"] = frontier_spec["key"]
                    rec["context_confuser_threshold"] = round(threshold, 4)
                frontier_hard_negative_pressure[frontier_spec["key"]].extend(frontier_negatives)
                frontier_fold_summaries[frontier_spec["key"]].append({
                    "fold": fold_no,
                    "ranked": _aggregate_ranked(frontier_records),
                    "hard_negative_pressure": _aggregate_hard_negative_pressure(frontier_negatives),
                    "candidate_quality": frontier_quality,
                })
        candidate_quality = _candidate_quality(positive_scored_by_source, positives_by_source, args.iou_threshold)
        all_candidate_quality.append(candidate_quality)
        ranked = _assign_ranks(positives, scored_by_source, args.iou_threshold)
        for rec in ranked:
            rec["fold"] = fold_no
        all_ranked.extend(ranked)
        fold_summaries.append({
            "fold": fold_no,
            "train": len(train_idx),
            "test": len(test_idx),
            "positive_boxes": len(ranked),
            "hard_negative_boxes": len(hard_negative_pressure),
            "groups": sorted({records[idx]["group"] for idx in test_idx}),
            "ranked": _aggregate_ranked(ranked),
            "hard_negative_pressure": _aggregate_hard_negative_pressure(hard_negative_pressure),
            "candidate_quality": candidate_quality,
        })

    ranked_sorted = sorted(all_ranked, key=lambda r: (r["best_rank"] is None, r["best_rank"] or 99999, -r["best_iou"]))
    misses = [r for r in all_ranked if r["best_rank"] is None or int(r["best_rank"]) > args.miss_top_k]
    misses = sorted(misses, key=lambda r: (r["best_rank"] is not None, r["best_rank"] or 99999, -r["best_iou"]))
    unmatched_sorted = sorted(all_unmatched, key=lambda r: float(r["score"]), reverse=True)
    negative_pressure_sorted = sorted(
        all_hard_negative_pressure,
        key=lambda r: (r["best_rank"] is None, r["best_rank"] or 99999, -float(r["best_score"])),
    )
    _sheet(ranked_sorted[: args.sheet_items], args.output / "top_ranked_matches.png", "Held-out true number proposal ranks")
    _sheet(misses[: args.sheet_items], args.output / f"misses_top{args.miss_top_k}.png", f"True numbers not in top {args.miss_top_k}")
    _sheet(unmatched_sorted[: args.sheet_items], args.output / "top_unmatched_candidates.png", "High-score unmatched candidates")
    _sheet(
        [r for r in negative_pressure_sorted if r.get("best_candidate")][: args.sheet_items],
        args.output / "hard_negative_pressure.png",
        "Held-out hard negatives still ranked as number candidates",
    )

    score_sweep_summary: dict[str, Any] = {}
    for key, records_for_key in sweep_ranked.items():
        spec = sweep_specs_by_key[key]
        score_sweep_summary[key] = {
            "mode": spec["mode"],
            "image_blend_weight": spec["image_blend_weight"],
            "overall": _aggregate_ranked(records_for_key),
            "hard_negative_pressure": _aggregate_hard_negative_pressure(sweep_hard_negative_pressure[key]),
            "hard_negative_by_source_bucket": _aggregate_hard_negative_by(sweep_hard_negative_pressure[key], "source_bucket"),
            "candidate_quality": _merge_candidate_quality(sweep_candidate_quality[key]),
            "by_source_bucket": _aggregate_by(records_for_key, "source_bucket"),
            "fold_results": sweep_fold_summaries[key],
        }
    score_sweep_best: list[dict[str, Any]] = []
    score_sweep_best_safe_overlay: list[dict[str, Any]] = []
    score_sweep_best_low_pressure: list[dict[str, Any]] = []
    if score_sweep_summary:
        for key, data in score_sweep_summary.items():
            overall = data["overall"]
            safe_overlay = data.get("by_source_bucket", {}).get("safe_car_num_delta", {})
            hard_negative = data.get("hard_negative_pressure", {})
            reviewed_negative = data.get("hard_negative_by_source_bucket", {}).get("reviewed_candidate_queue", {})
            top20_quality = data.get("candidate_quality", {}).get("top_20", {})
            row = {
                "key": key,
                "mode": data["mode"],
                "image_blend_weight": data["image_blend_weight"],
                "top_20_covered": overall.get("top_20_covered", 0),
                "top_40_covered": overall.get("top_40_covered", 0),
                "top_10_covered": overall.get("top_10_covered", 0),
                "safe_overlay_top_20_covered": safe_overlay.get("top_20_covered", 0),
                "safe_overlay_top_40_covered": safe_overlay.get("top_40_covered", 0),
                "hard_negative_top_5_exposed": hard_negative.get("top_5_exposed", 0),
                "hard_negative_top_20_exposed": hard_negative.get("top_20_exposed", 0),
                "reviewed_hard_negative_top_5_exposed": reviewed_negative.get("top_5_exposed", 0),
                "reviewed_hard_negative_top_20_exposed": reviewed_negative.get("top_20_exposed", 0),
                "top_20_known_precision_floor": top20_quality.get("known_precision_floor", 0.0),
                "median_matched_rank": overall.get("median_matched_rank", 0.0),
            }
            score_sweep_best.append(row)
            score_sweep_best_safe_overlay.append(dict(row))
            score_sweep_best_low_pressure.append(dict(row))
        score_sweep_best.sort(
            key=lambda r: (
                int(r["top_20_covered"]),
                int(r["top_40_covered"]),
                int(r["top_10_covered"]),
                -float(r["median_matched_rank"]),
            ),
            reverse=True,
        )
        score_sweep_best_safe_overlay.sort(
            key=lambda r: (
                int(r["safe_overlay_top_20_covered"]),
                int(r["safe_overlay_top_40_covered"]),
                int(r["top_20_covered"]),
                int(r["top_40_covered"]),
                float(r["top_20_known_precision_floor"]),
            ),
            reverse=True,
        )
        score_sweep_best_low_pressure.sort(
            key=lambda r: (
                int(r["top_20_covered"]),
                int(r["top_40_covered"]),
                -int(r["reviewed_hard_negative_top_20_exposed"]),
                -int(r["hard_negative_top_20_exposed"]),
                -int(r["reviewed_hard_negative_top_5_exposed"]),
                -int(r["hard_negative_top_5_exposed"]),
                float(r["top_20_known_precision_floor"]),
            ),
            reverse=True,
        )
        sheet_key = args.score_sweep_sheet_key
        if sheet_key == "best":
            sheet_key = score_sweep_best[0]["key"]
        if sheet_key:
            if sheet_key not in score_sweep_summary:
                raise ValueError(f"unknown score sweep sheet key: {sheet_key}")
            safe_key = _safe_filename_key(sheet_key)
            sweep_ranked_sorted = sorted(
                sweep_ranked[sheet_key],
                key=lambda r: (r["best_rank"] is None, r["best_rank"] or 99999, -r["best_iou"]),
            )
            sweep_misses = [
                r for r in sweep_ranked[sheet_key]
                if r["best_rank"] is None or int(r["best_rank"]) > args.miss_top_k
            ]
            sweep_misses = sorted(
                sweep_misses,
                key=lambda r: (r["best_rank"] is not None, r["best_rank"] or 99999, -r["best_iou"]),
            )
            sweep_unmatched_sorted = sorted(sweep_unmatched[sheet_key], key=lambda r: float(r["score"]), reverse=True)
            sweep_paths = {
                "ranked_records": str((args.output / f"score_sweep_{safe_key}_ranked_records.json").resolve()),
                "top_ranked_sheet": str((args.output / f"score_sweep_{safe_key}_top_ranked_matches.png").resolve()),
                "misses_sheet": str((args.output / f"score_sweep_{safe_key}_misses_top{args.miss_top_k}.png").resolve()),
                "top_unmatched_sheet": str((args.output / f"score_sweep_{safe_key}_top_unmatched_candidates.png").resolve()),
            }
            (args.output / f"score_sweep_{safe_key}_ranked_records.json").write_text(
                json.dumps(_json_clean(sweep_ranked[sheet_key]), indent=2),
                encoding="utf-8",
            )
            _sheet(
                sweep_ranked_sorted[: args.sheet_items],
                args.output / f"score_sweep_{safe_key}_top_ranked_matches.png",
                f"{sheet_key} held-out true number ranks",
            )
            _sheet(
                sweep_misses[: args.sheet_items],
                args.output / f"score_sweep_{safe_key}_misses_top{args.miss_top_k}.png",
                f"{sheet_key} true numbers not in top {args.miss_top_k}",
            )
            _sheet(
                sweep_unmatched_sorted[: args.sheet_items],
                args.output / f"score_sweep_{safe_key}_top_unmatched_candidates.png",
                f"{sheet_key} high-score unmatched candidates",
            )
            score_sweep_summary[sheet_key]["sheets"] = sweep_paths

    context_frontier_summary: dict[str, Any] = {}
    for key, records_for_key in frontier_ranked.items():
        spec = frontier_specs_by_key[key]
        context_frontier_summary[key] = {
            "base_key": spec["base_key"],
            "mode": spec["mode"],
            "image_blend_weight": spec["image_blend_weight"],
            "context_confuser_threshold": spec["context_confuser_threshold"],
            "overall": _aggregate_ranked(records_for_key),
            "hard_negative_pressure": _aggregate_hard_negative_pressure(frontier_hard_negative_pressure[key]),
            "hard_negative_by_source_bucket": _aggregate_hard_negative_by(
                frontier_hard_negative_pressure[key],
                "source_bucket",
            ),
            "candidate_quality": _merge_candidate_quality(frontier_candidate_quality[key]),
            "by_source_bucket": _aggregate_by(records_for_key, "source_bucket"),
            "fold_results": frontier_fold_summaries[key],
        }
    context_frontier_best: list[dict[str, Any]] = []
    context_frontier_best_low_pressure: list[dict[str, Any]] = []
    if context_frontier_summary:
        for key, data in context_frontier_summary.items():
            overall = data["overall"]
            safe_overlay = data.get("by_source_bucket", {}).get("safe_car_num_delta", {})
            hard_negative = data.get("hard_negative_pressure", {})
            reviewed_negative = data.get("hard_negative_by_source_bucket", {}).get("reviewed_candidate_queue", {})
            top20_quality = data.get("candidate_quality", {}).get("top_20", {})
            row = {
                "key": key,
                "base_key": data["base_key"],
                "mode": data["mode"],
                "image_blend_weight": data["image_blend_weight"],
                "context_confuser_threshold": data["context_confuser_threshold"],
                "top_20_covered": overall.get("top_20_covered", 0),
                "top_40_covered": overall.get("top_40_covered", 0),
                "top_10_covered": overall.get("top_10_covered", 0),
                "safe_overlay_top_20_covered": safe_overlay.get("top_20_covered", 0),
                "safe_overlay_top_40_covered": safe_overlay.get("top_40_covered", 0),
                "hard_negative_top_5_exposed": hard_negative.get("top_5_exposed", 0),
                "hard_negative_top_20_exposed": hard_negative.get("top_20_exposed", 0),
                "reviewed_hard_negative_top_5_exposed": reviewed_negative.get("top_5_exposed", 0),
                "reviewed_hard_negative_top_20_exposed": reviewed_negative.get("top_20_exposed", 0),
                "top_20_known_precision_floor": top20_quality.get("known_precision_floor", 0.0),
                "median_matched_rank": overall.get("median_matched_rank", 0.0),
            }
            context_frontier_best.append(row)
            context_frontier_best_low_pressure.append(dict(row))
        context_frontier_best.sort(
            key=lambda r: (
                int(r["top_20_covered"]),
                int(r["top_40_covered"]),
                int(r["top_10_covered"]),
                -int(r["reviewed_hard_negative_top_20_exposed"]),
                -int(r["hard_negative_top_20_exposed"]),
                float(r["top_20_known_precision_floor"]),
                -float(r["median_matched_rank"]),
            ),
            reverse=True,
        )
        context_frontier_best_low_pressure.sort(
            key=lambda r: (
                -int(r["reviewed_hard_negative_top_20_exposed"]),
                -int(r["hard_negative_top_20_exposed"]),
                -int(r["reviewed_hard_negative_top_5_exposed"]),
                -int(r["hard_negative_top_5_exposed"]),
                int(r["top_20_covered"]),
                int(r["top_40_covered"]),
                float(r["top_20_known_precision_floor"]),
            ),
            reverse=True,
        )
        frontier_sheet_key = args.context_frontier_sheet_key
        if frontier_sheet_key == "best":
            frontier_sheet_key = context_frontier_best[0]["key"]
        if frontier_sheet_key:
            if frontier_sheet_key not in context_frontier_summary:
                raise ValueError(f"unknown context frontier sheet key: {frontier_sheet_key}")
            safe_key = _safe_filename_key(frontier_sheet_key)
            frontier_ranked_sorted = sorted(
                frontier_ranked[frontier_sheet_key],
                key=lambda r: (r["best_rank"] is None, r["best_rank"] or 99999, -r["best_iou"]),
            )
            frontier_misses = [
                r for r in frontier_ranked[frontier_sheet_key]
                if r["best_rank"] is None or int(r["best_rank"]) > args.miss_top_k
            ]
            frontier_misses = sorted(
                frontier_misses,
                key=lambda r: (r["best_rank"] is not None, r["best_rank"] or 99999, -r["best_iou"]),
            )
            frontier_unmatched_sorted = sorted(
                frontier_unmatched[frontier_sheet_key],
                key=lambda r: float(r["score"]),
                reverse=True,
            )
            frontier_negative_sorted = sorted(
                frontier_hard_negative_pressure[frontier_sheet_key],
                key=lambda r: (r["best_rank"] is None, r["best_rank"] or 99999, -float(r["best_score"])),
            )
            frontier_paths = {
                "ranked_records": str((args.output / f"context_frontier_{safe_key}_ranked_records.json").resolve()),
                "top_ranked_sheet": str((args.output / f"context_frontier_{safe_key}_top_ranked_matches.png").resolve()),
                "misses_sheet": str((args.output / f"context_frontier_{safe_key}_misses_top{args.miss_top_k}.png").resolve()),
                "top_unmatched_sheet": str((args.output / f"context_frontier_{safe_key}_top_unmatched_candidates.png").resolve()),
                "hard_negative_sheet": str((args.output / f"context_frontier_{safe_key}_hard_negative_pressure.png").resolve()),
            }
            (args.output / f"context_frontier_{safe_key}_ranked_records.json").write_text(
                json.dumps(_json_clean(frontier_ranked[frontier_sheet_key]), indent=2),
                encoding="utf-8",
            )
            _sheet(
                frontier_ranked_sorted[: args.sheet_items],
                args.output / f"context_frontier_{safe_key}_top_ranked_matches.png",
                f"{frontier_sheet_key} held-out true number ranks",
            )
            _sheet(
                frontier_misses[: args.sheet_items],
                args.output / f"context_frontier_{safe_key}_misses_top{args.miss_top_k}.png",
                f"{frontier_sheet_key} true numbers not in top {args.miss_top_k}",
            )
            _sheet(
                frontier_unmatched_sorted[: args.sheet_items],
                args.output / f"context_frontier_{safe_key}_top_unmatched_candidates.png",
                f"{frontier_sheet_key} high-score unmatched candidates",
            )
            _sheet(
                [r for r in frontier_negative_sorted if r.get("best_candidate")][: args.sheet_items],
                args.output / f"context_frontier_{safe_key}_hard_negative_pressure.png",
                f"{frontier_sheet_key} hard negatives still ranked",
            )
            context_frontier_summary[frontier_sheet_key]["sheets"] = frontier_paths

    summary = {
        "manifest": str(args.manifest),
        "output": str(args.output.resolve()),
        "holdout_mode": args.holdout_mode,
        "fold_strategy": FOLD_STRATEGY,
        "variant": args.variant,
        "rank_model": args.rank_model,
        "meta_dim": META_DIM,
        "region_context_meta_enabled": USE_REGION_CONTEXT_META,
        "region_context_meta_dim": REGION_CONTEXT_META_DIM,
        "stroke_topology_meta_enabled": USE_STROKE_TOPOLOGY_META,
        "meta_veto_threshold": args.meta_veto_threshold if args.rank_model == "image_meta_veto" else None,
        "meta_veto_penalty": args.meta_veto_penalty if args.rank_model == "image_meta_veto" else None,
        "image_blend_weight": args.image_blend_weight if args.rank_model in {"image_meta_blend", "image_meta_product"} else None,
        "max_boxes": args.max_boxes,
        "iou_threshold": args.iou_threshold,
        "folds": len(fold_summaries),
        "epochs": args.epochs,
        "loss": args.loss,
        "focal_gamma": args.focal_gamma if args.loss == "focal" else None,
        "hard_negative_weight": args.hard_negative_weight,
        "reviewed_hard_negative_weight": args.reviewed_hard_negative_weight,
        "confuser_penalty_weight": args.confuser_penalty_weight,
        "confuser_target": args.confuser_target if args.confuser_penalty_weight > 0 else None,
        "confuser_image_blend_weight": args.confuser_image_blend_weight if args.confuser_penalty_weight > 0 else None,
        "context_confuser_penalty_weight": args.context_confuser_penalty_weight,
        "context_confuser_target": args.context_confuser_target if _context_confuser_enabled(args) else None,
        "context_confuser_pad_scale": args.context_confuser_pad_scale if _context_confuser_enabled(args) else None,
        "context_frontier": args.context_frontier,
        "context_frontier_thresholds": _parse_float_csv(args.context_frontier_thresholds) if args.context_frontier else [],
        "sibling_boost_weight": args.sibling_boost_weight,
        "sibling_boost_seed_rank": args.sibling_boost_seed_rank if _sibling_boost_enabled(args) else None,
        "sibling_boost_seed_min": args.sibling_boost_seed_min if _sibling_boost_enabled(args) else None,
        "sibling_boost_similarity": args.sibling_boost_similarity if _sibling_boost_enabled(args) else None,
        "sibling_boost_area_ratio": args.sibling_boost_area_ratio if _sibling_boost_enabled(args) else None,
        "sibling_boost_aspect_ratio": args.sibling_boost_aspect_ratio if _sibling_boost_enabled(args) else None,
        "sibling_digit_gate": bool(args.sibling_digit_gate) if _sibling_boost_enabled(args) else False,
        "sibling_digit_min": args.sibling_digit_min if _sibling_digit_gate_enabled(args) else None,
        "panel_penalty_weight": args.panel_penalty_weight,
        "positive_boxes": len(all_ranked),
        "overall": _aggregate_ranked(all_ranked),
        "hard_negative_pressure": _aggregate_hard_negative_pressure(all_hard_negative_pressure),
        "hard_negative_by_source_bucket": _aggregate_hard_negative_by(all_hard_negative_pressure, "source_bucket"),
        "candidate_quality": _merge_candidate_quality(all_candidate_quality),
        "by_source_bucket": _aggregate_by(all_ranked, "source_bucket"),
        "by_folder": _aggregate_by(all_ranked, "folder"),
        "fold_results": fold_summaries,
        "score_sweep_keys": [spec["key"] for spec in sweep_specs],
        "score_sweep_best": score_sweep_best,
        "score_sweep_best_safe_overlay": score_sweep_best_safe_overlay,
        "score_sweep_best_low_pressure": score_sweep_best_low_pressure,
        "context_frontier_keys": [spec["key"] for spec in frontier_specs],
        "context_frontier_best": context_frontier_best,
        "context_frontier_best_low_pressure": context_frontier_best_low_pressure,
        "top_unmatched_count": len(all_unmatched),
        "hard_negative_pressure_count": len(all_hard_negative_pressure),
        "hard_negative_pressure_sheet": str((args.output / "hard_negative_pressure.png").resolve()) if all_hard_negative_pressure else None,
        "top_unmatched_sheet": str((args.output / "top_unmatched_candidates.png").resolve()) if all_unmatched else None,
        "misses_sheet": str((args.output / f"misses_top{args.miss_top_k}.png").resolve()) if misses else None,
    }
    (args.output / "ranker_eval.json").write_text(json.dumps(_json_clean(summary), indent=2), encoding="utf-8")
    if score_sweep_summary:
        (args.output / "score_sweep.json").write_text(json.dumps(_json_clean(score_sweep_summary), indent=2), encoding="utf-8")
    if context_frontier_summary:
        (args.output / "context_frontier.json").write_text(json.dumps(_json_clean(context_frontier_summary), indent=2), encoding="utf-8")
    (args.output / "ranked_records.json").write_text(json.dumps(_json_clean(all_ranked), indent=2), encoding="utf-8")
    (args.output / "hard_negative_pressure_records.json").write_text(
        json.dumps(_json_clean(negative_pressure_sorted), indent=2),
        encoding="utf-8",
    )
    (args.output / "top_unmatched_candidates.json").write_text(json.dumps(_json_clean(unmatched_sorted), indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--holdout-mode", choices=["source", "paint"], default="source")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument(
        "--variant",
        choices=[
            "default",
            "multi",
            "multi_soft",
            "window",
            "hybrid",
            "hybrid_expand",
            "hybrid_focus",
            "hybrid_side_panel",
        ],
        default="hybrid",
    )
    parser.add_argument(
        "--rank-model",
        choices=["image", "meta", "image_meta_veto", "image_meta_blend", "image_meta_product"],
        default="image",
    )
    parser.add_argument("--meta-veto-threshold", type=float, default=0.95)
    parser.add_argument("--meta-veto-penalty", type=float, default=0.05)
    parser.add_argument("--image-blend-weight", type=float, default=0.7)
    parser.add_argument(
        "--confuser-penalty-weight",
        type=float,
        default=0.0,
        help="Optional score penalty from a second head trained to recognize known false-positive crops. Default 0 disables it.",
    )
    parser.add_argument(
        "--confuser-target",
        choices=["reviewed", "all"],
        default="reviewed",
        help="False-positive class used for the optional confuser penalty head.",
    )
    parser.add_argument(
        "--confuser-image-blend-weight",
        type=float,
        default=0.5,
        help="Image-vs-metadata blend for the optional confuser penalty score.",
    )
    parser.add_argument(
        "--context-confuser-penalty-weight",
        type=float,
        default=0.0,
        help="Optional score penalty from a context crop CNN trained on full-TGA false-positive regions. Default 0 disables it.",
    )
    parser.add_argument(
        "--context-confuser-target",
        choices=["reviewed", "all"],
        default="reviewed",
        help="False-positive class used for the optional context crop confuser head.",
    )
    parser.add_argument(
        "--context-confuser-pad-scale",
        type=float,
        default=0.65,
        help="Padding scale around each proposal for the optional context crop confuser head.",
    )
    parser.add_argument(
        "--context-frontier",
        action="store_true",
        help="Offline diagnostic: replay score-sweep variants after dropping candidates above context confuser thresholds.",
    )
    parser.add_argument(
        "--context-frontier-thresholds",
        default="0.60,0.65,0.70,0.75,0.80,0.85",
        help="Comma-separated context confuser score ceilings for --context-frontier.",
    )
    parser.add_argument(
        "--context-frontier-sheet-key",
        default="best",
        help="Context-frontier key to render contact sheets for, or 'best'. Empty disables frontier sheets.",
    )
    parser.add_argument(
        "--panel-penalty-weight",
        type=float,
        default=0.0,
        help="Optional score penalty from a full-TGA panelness heuristic for sponsor/template false positives. Default 0 disables it.",
    )
    parser.add_argument(
        "--sibling-boost-weight",
        type=float,
        default=0.0,
        help="Optional same-TGA visual sibling boost for repeated number-like candidates. Default 0 disables it.",
    )
    parser.add_argument(
        "--sibling-boost-seed-rank",
        type=int,
        default=5,
        help="Top-N candidates per TGA that can seed the optional sibling boost.",
    )
    parser.add_argument(
        "--sibling-boost-seed-min",
        type=float,
        default=0.50,
        help="Minimum seed score for the optional sibling boost.",
    )
    parser.add_argument(
        "--sibling-boost-similarity",
        type=float,
        default=0.70,
        help="Minimum visual-size similarity for sibling boost propagation.",
    )
    parser.add_argument(
        "--sibling-boost-area-ratio",
        type=float,
        default=2.4,
        help="Area-ratio tolerance for sibling boost size matching.",
    )
    parser.add_argument(
        "--sibling-boost-aspect-ratio",
        type=float,
        default=1.35,
        help="Aspect-ratio tolerance for sibling boost size matching.",
    )
    parser.add_argument(
        "--sibling-digit-gate",
        action="store_true",
        help="Offline diagnostic: only allow sibling boost between crops with number-like stroke topology.",
    )
    parser.add_argument(
        "--sibling-digit-min",
        type=float,
        default=0.55,
        help="Minimum number-stroke score required by --sibling-digit-gate.",
    )
    parser.add_argument("--score-sweep", action="store_true")
    parser.add_argument(
        "--score-sweep-modes",
        default="image,meta,image_meta_blend,image_meta_product",
        help="Comma-separated replay modes for already-scored candidates.",
    )
    parser.add_argument(
        "--score-sweep-weights",
        default="0.30,0.40,0.50,0.55,0.60,0.70,0.80",
        help="Comma-separated image weights used for blend/product replay modes.",
    )
    parser.add_argument(
        "--score-sweep-sheet-key",
        default="best",
        help="Score-sweep key to render contact sheets for, or 'best'. Empty disables sweep sheets.",
    )
    parser.add_argument("--max-boxes", type=int, default=240)
    parser.add_argument("--iou-threshold", type=float, default=0.25)
    parser.add_argument("--miss-top-k", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=18)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.0012)
    parser.add_argument("--weight-decay", type=float, default=0.0008)
    parser.add_argument("--loss", choices=["bce", "focal"], default="focal")
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--pos-weight-scale", type=float, default=1.0)
    parser.add_argument(
        "--hard-negative-weight",
        type=float,
        default=1.0,
        help="Training loss multiplier for all non-number crops. Default 1.0 preserves baseline behavior.",
    )
    parser.add_argument(
        "--reviewed-hard-negative-weight",
        type=float,
        default=1.0,
        help="Additional loss multiplier for reviewed candidate-queue hard negatives.",
    )
    parser.add_argument("--unmatched-per-source", type=int, default=3)
    parser.add_argument("--sheet-items", type=int, default=40)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


def main() -> None:
    summary = evaluate(parse_args())
    brief = {k: v for k, v in summary.items() if k not in {"fold_results", "by_folder"}}
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
