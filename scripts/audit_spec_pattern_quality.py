#!/usr/bin/env python3
"""Grade shipping Spec Pattern Overlay thumbnails and rank rebuild candidates.

This script renders every UI-shipping SPEC_PATTERNS id, scores it on a
100-point rubric, and writes ranked thumbnails plus JSON/Markdown reports.

Score components:
  - intent: category/name-specific behavior fit
  - originality: inverse structural similarity against other visible overlays
  - wow: contrast, entropy, edges, highlight structure
  - detail: pixel-scale and near-pixel residual structure
  - coverage: how much of the 2048-style canvas is materially affected
  - physics: weakest M/R/CC range/std plus channel independence

SPB-105 / owner overnight overhaul Round 1 (2026-07-13): modernized this
auditor for native (H,W,3) M/R/CC overlays. Owner verdict: "WIDE diversity in
spec pattern LOOKS... gloss, flat, chrome, FRACTURED... FIVE ROUNDS."
Baseline movement: stale 3-channel rejection -> full visible-catalog grading.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.spb_pattern_gate import _whiten, struct_sig


@dataclass
class SpecPatternGrade:
    id: str
    name: str
    category: str
    score: float
    intent: float
    originality: float
    wow: float
    detail: float
    coverage: float
    physics: float
    active_fraction: float
    fine_energy: float
    residual_energy: float
    entropy: float
    dynamic_range: float
    edge_density: float
    largest_region_ratio: float
    largest_region_detail: float
    max_abs_correlation: float
    nearest_id: str
    channel_stds: list[float]
    channel_spans: list[float]
    min_channel_std: float
    min_channel_span: float
    max_channel_correlation: float
    render_ms: float
    material_family: str
    flags: list[str]
    rebuild_required: bool
    error: str | None = None


def _load_ui_spec_patterns() -> tuple[list[dict[str, Any]], dict[str, str]]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
for (const file of ['js/spec-overlays/catalog-data.js', 'js/spec-overlays/catalog-install.js']) {
  vm.runInContext(fs.readFileSync(file, 'utf8'), ctx, { filename: file, timeout: 5000 });
}
const specs = vm.runInContext('SPEC_PATTERNS', ctx);
const groups = vm.runInContext('SPEC_PATTERN_GROUPS', ctx);
const groupById = {};
for (const [group, ids] of Object.entries(groups)) {
  for (const id of ids) if (!groupById[id]) groupById[id] = group;
}
console.log(JSON.stringify({ specs, groupById }));
"""
    out = subprocess.check_output(["node", "-e", script], cwd=REPO, text=True, encoding="utf-8")
    payload = json.loads(out)
    return payload["specs"], payload["groupById"]


def _quiet_catalog():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from engine.spec_patterns import PATTERN_CATALOG
    return PATTERN_CATALOG


def _norm01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _structure_and_channels(arr: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    """Return a perceptual material-structure field plus authored channels.

    Modern SPB spec overlays are M/R/CC stacks.  Roughness is inverted for the
    structure view because low-R pixels are the glossy/highlight response.  The
    shared structure remains tied to the authored material marks while channel
    statistics are measured from the untouched data.
    """
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 2:
        return np.clip(arr, 0.0, 1.0), [np.clip(arr, 0.0, 1.0)]
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(f"expected (H,W) or (H,W,3+), got {arr.shape}")
    channels = [np.clip(arr[:, :, idx], 0.0, 1.0) for idx in range(3)]
    m, r, cc = (_norm01(ch) for ch in channels)
    structure = np.clip(m * 0.40 + (1.0 - r) * 0.30 + cc * 0.30, 0.0, 1.0)
    return structure.astype(np.float32), channels


def _channel_metrics(channels: list[np.ndarray]) -> tuple[list[float], list[float], float]:
    stds = [float(ch.std()) for ch in channels]
    spans = [float(ch.max() - ch.min()) for ch in channels]
    max_corr = 0.0
    if len(channels) >= 3 and all(std > 1e-7 for std in stds[:3]):
        corr = np.corrcoef(np.stack([ch.ravel() for ch in channels[:3]]))
        off_diag = np.abs(corr - np.eye(3, dtype=np.float64))
        max_corr = float(np.nanmax(off_diag))
    return stds, spans, max_corr


def _score_clip(value: float, target: float, floor: float = 0.0) -> float:
    if target <= 0:
        return 0.0
    return float(np.clip((value - floor) / max(target - floor, 1e-6) * 100.0, 0.0, 100.0))


def _fine_energy(arr: np.ndarray) -> float:
    dx = np.abs(np.diff(arr, axis=1)).mean()
    dy = np.abs(np.diff(arr, axis=0)).mean()
    return float(dx + dy)


def _residual_energy(arr: np.ndarray, block: int = 8) -> float:
    h, w = arr.shape[:2]
    hh = h - h % block
    ww = w - w % block
    if hh < block or ww < block:
        return 0.0
    cropped = arr[:hh, :ww]
    coarse = cropped.reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
    up = np.repeat(np.repeat(coarse, block, axis=0), block, axis=1)
    return float(np.abs(cropped - up).mean())


def _entropy(arr: np.ndarray) -> float:
    hist, _ = np.histogram(np.clip(arr, 0, 1), bins=32, range=(0, 1))
    p = hist.astype(np.float64)
    p = p[p > 0] / max(p.sum(), 1.0)
    if p.size == 0:
        return 0.0
    return float(-(p * np.log2(p)).sum() / math.log2(32))


def _edge_density(arr: np.ndarray) -> float:
    u8 = np.clip(arr * 255, 0, 255).astype(np.uint8)
    edges = cv2.Canny(u8, 32, 88)
    return float((edges > 0).mean())


def _largest_region_detail(arr: np.ndarray, levels: int = 6) -> tuple[float, float]:
    smooth = cv2.GaussianBlur(arr, (0, 0), sigmaX=8.0, sigmaY=8.0)
    q = np.floor(_norm01(smooth) * levels).astype(np.uint8)
    q = np.clip(q, 0, levels - 1)
    best_area = 0
    best_mask = None
    for level in range(levels):
        count, labels, stats, _ = cv2.connectedComponentsWithStats((q == level).astype(np.uint8), 8)
        if count <= 1:
            continue
        idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area > best_area:
            best_area = area
            best_mask = labels == idx
    if best_mask is None:
        return 0.0, 0.0
    blur = cv2.GaussianBlur(arr, (0, 0), sigmaX=2.5, sigmaY=2.5)
    return float(best_area / arr.size), float(np.abs(arr[best_mask] - blur[best_mask]).mean())


def _family(pid: str, name: str, category: str) -> str:
    s = f"{pid} {name} {category}".lower()
    if any(t in s for t in ("sparkle", "flake", "dust", "glass", "shimmer", "prismatic", "gold")):
        return "sparkle"
    if any(t in s for t in ("brushed", "grain", "lathe", "wire", "polish", "mill", "machined", "grating")):
        return "directional"
    if any(t in s for t in ("carbon", "weave", "mesh", "kevlar", "dyneema", "chainlink", "knurl")):
        return "weave"
    if any(t in s for t in ("rust", "mud", "dust", "grime", "wear", "scuff", "patina", "chip", "scorch", "corrosion")):
        return "weather"
    if any(t in s for t in ("hex", "grid", "lattice", "diamond", "circuit", "panel", "brick", "rivet", "faceted")):
        return "geometric"
    if any(t in s for t in ("wet", "clear", "drip", "pool", "ripple", "oil", "caustic", "fish", "bubble")):
        return "coating"
    if any(t in s for t in ("sponsor", "tape", "vinyl", "decal", "ghost", "emboss", "deboss", "confetti", "race_number")):
        return "graphic_surface"
    if any(t in s for t in ("electric", "branch", "dendrite", "discharge", "lightning")):
        return "branching"
    if any(t in s for t in ("abstract", "brush", "crayon", "airbrush", "spray", "halftone", "op art", "bauhaus")):
        return "artistic"
    return "general"


def _intent_score(family: str, active: float, fine: float, residual: float, entropy: float,
                  edge: float, dyn: float, region_ratio: float, region_detail: float) -> float:
    coverage_base = _score_clip(active, 0.48)
    detail_base = _score_clip(residual, 0.055)
    edge_base = _score_clip(edge, 0.18)
    dyn_base = _score_clip(dyn, 0.78)
    entropy_base = _score_clip(entropy, 0.82)
    anti_blob = float(np.clip((1.0 - region_ratio) / 0.72 * 100.0, 0, 100))
    inside = _score_clip(region_detail, 0.025)
    if family == "sparkle":
        return 0.28 * detail_base + 0.25 * coverage_base + 0.22 * dyn_base + 0.15 * edge_base + 0.10 * inside
    if family == "directional":
        return 0.30 * detail_base + 0.28 * edge_base + 0.20 * coverage_base + 0.12 * entropy_base + 0.10 * inside
    if family == "weave":
        return 0.25 * edge_base + 0.24 * detail_base + 0.23 * coverage_base + 0.18 * entropy_base + 0.10 * inside
    if family == "weather":
        return 0.27 * coverage_base + 0.22 * entropy_base + 0.20 * detail_base + 0.16 * anti_blob + 0.15 * inside
    if family == "geometric":
        return 0.30 * edge_base + 0.24 * coverage_base + 0.18 * detail_base + 0.16 * dyn_base + 0.12 * inside
    if family == "coating":
        return 0.26 * coverage_base + 0.22 * entropy_base + 0.20 * detail_base + 0.17 * dyn_base + 0.15 * inside
    if family == "artistic":
        return 0.26 * coverage_base + 0.24 * entropy_base + 0.20 * dyn_base + 0.18 * edge_base + 0.12 * detail_base
    if family == "graphic_surface":
        return 0.30 * edge_base + 0.25 * coverage_base + 0.22 * detail_base + 0.13 * entropy_base + 0.10 * inside
    if family == "branching":
        return 0.34 * edge_base + 0.24 * detail_base + 0.18 * dyn_base + 0.14 * coverage_base + 0.10 * inside
    return 0.24 * coverage_base + 0.23 * detail_base + 0.20 * entropy_base + 0.18 * dyn_base + 0.15 * inside


def _grade(pid: str, meta: dict[str, Any], arr: np.ndarray, max_corr: float,
           nearest_id: str, channel_stds: list[float], channel_spans: list[float],
           max_channel_corr: float, render_ms: float, threshold: float) -> SpecPatternGrade:
    name = str(meta.get("name") or pid)
    category = str(meta.get("group") or meta.get("category") or "Ungrouped")
    norm = _norm01(arr)
    active = float((np.abs(norm - 0.5) > 0.055).mean())
    fine = _fine_energy(norm)
    residual = _residual_energy(norm)
    ent = _entropy(norm)
    dyn = float(np.quantile(norm, 0.98) - np.quantile(norm, 0.02))
    edge = _edge_density(norm)
    region_ratio, region_detail = _largest_region_detail(norm)
    fam = _family(pid, name, category)
    intent = _intent_score(fam, active, fine, residual, ent, edge, dyn, region_ratio, region_detail)
    originality = float(np.clip((1.0 - max_corr) / 0.38 * 100.0, 0, 100))
    if fam == "graphic_surface":
        wow = (
            0.34 * _score_clip(edge, 0.20)
            + 0.26 * _score_clip(residual, 0.060)
            + 0.18 * _score_clip(ent, 0.86)
            + 0.12 * _score_clip(region_detail, 0.025)
            + 0.10 * _score_clip(dyn, 0.82)
        )
    elif fam == "branching":
        wow = (
            0.34 * _score_clip(edge, 0.20)
            + 0.24 * _score_clip(dyn, 0.82)
            + 0.20 * _score_clip(residual, 0.060)
            + 0.12 * _score_clip(ent, 0.86)
            + 0.10 * _score_clip(region_detail, 0.025)
        )
    else:
        wow = (
            0.30 * _score_clip(dyn, 0.82)
            + 0.24 * _score_clip(ent, 0.86)
            + 0.22 * _score_clip(edge, 0.20)
            + 0.14 * _score_clip(residual, 0.060)
            + 0.10 * _score_clip(region_detail, 0.025)
        )
    detail = 0.56 * _score_clip(residual, 0.058) + 0.24 * _score_clip(fine, 0.16) + 0.20 * _score_clip(region_detail, 0.026)
    coverage = _score_clip(active, 0.50)
    min_std = min(channel_stds) if channel_stds else 0.0
    min_span = min(channel_spans) if channel_spans else 0.0
    std_score = _score_clip(min_std, 20.0 / 255.0)
    span_score = _score_clip(min_span, 0.70)
    independence = float(np.clip((0.98 - max_channel_corr) / (0.98 - 0.55) * 100.0, 0.0, 100.0))
    physics = 0.38 * std_score + 0.34 * span_score + 0.28 * independence
    score = (
        0.20 * intent + 0.16 * originality + 0.16 * wow
        + 0.18 * detail + 0.12 * coverage + 0.18 * physics
    )
    flags: list[str] = []
    if coverage < 70:
        flags.append("LOW_COVERAGE")
    if detail < 70:
        flags.append("LOW_DETAIL")
    if intent < 70:
        flags.append("LOW_INTENT")
    if wow < 65:
        flags.append("LOW_WOW")
    if max_corr >= 0.80:
        flags.append("NEAR_DUPLICATE")
    if min_std < 20.0 / 255.0:
        flags.append("WEAK_CHANNEL_STD")
    if min_span < 0.70:
        flags.append("NARROW_CHANNEL_RANGE")
    if len(channel_stds) >= 3 and max_channel_corr >= 0.85:
        flags.append("CHANNEL_COUPLED")
    if region_ratio > 0.72 and region_detail < 0.022:
        flags.append("BLOB_OR_FLAT_REGION")
    rebuild = score < threshold or bool({
        "LOW_COVERAGE", "LOW_DETAIL", "LOW_INTENT", "BLOB_OR_FLAT_REGION",
        "NEAR_DUPLICATE", "WEAK_CHANNEL_STD", "NARROW_CHANNEL_RANGE", "CHANNEL_COUPLED",
    } & set(flags))
    return SpecPatternGrade(
        id=pid,
        name=name,
        category=category,
        score=round(score, 2),
        intent=round(intent, 2),
        originality=round(originality, 2),
        wow=round(wow, 2),
        detail=round(detail, 2),
        coverage=round(coverage, 2),
        physics=round(physics, 2),
        active_fraction=round(active, 5),
        fine_energy=round(fine, 6),
        residual_energy=round(residual, 6),
        entropy=round(ent, 5),
        dynamic_range=round(dyn, 5),
        edge_density=round(edge, 5),
        largest_region_ratio=round(region_ratio, 5),
        largest_region_detail=round(region_detail, 6),
        max_abs_correlation=round(max_corr, 5),
        nearest_id=nearest_id,
        channel_stds=[round(value, 6) for value in channel_stds],
        channel_spans=[round(value, 6) for value in channel_spans],
        min_channel_std=round(min_std, 6),
        min_channel_span=round(min_span, 6),
        max_channel_correlation=round(max_channel_corr, 6),
        render_ms=round(render_ms, 3),
        material_family=fam,
        flags=flags,
        rebuild_required=rebuild,
    )


def _thumb(arr: np.ndarray, tile: int) -> Image.Image:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        # Material-response view: red=metallic, green=gloss (inverse roughness),
        # blue=clearcoat. Preserve authored values instead of normalizing away
        # weak channels; the sheet must make narrow palettes visibly obvious.
        rgb = np.dstack([arr[:, :, 0], 1.0 - arr[:, :, 1], arr[:, :, 2]])
        rgb = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    else:
        u8 = np.clip(_norm01(arr) * 255, 0, 255).astype(np.uint8)
        rgb = np.dstack([u8, 255 - u8 // 2, np.clip(50 + u8, 0, 255).astype(np.uint8)])
    return Image.fromarray(rgb.astype(np.uint8), "RGB").resize((tile, tile), Image.Resampling.LANCZOS)


def _write_sheet(path: Path, rows: list[SpecPatternGrade], renders: dict[str, np.ndarray], columns: int, tile: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        sheet = Image.new("RGB", (max(tile * columns, tile), tile), (18, 18, 22))
        draw = ImageDraw.Draw(sheet)
        draw.text((12, 12), "No rebuild-required patterns at this threshold.", fill=(235, 235, 235), font=ImageFont.load_default())
        sheet.save(path)
        return
    label_h = 48
    rows_n = math.ceil(len(rows) / columns)
    sheet = Image.new("RGB", (columns * tile, rows_n * (tile + label_h)), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, row in enumerate(rows):
        x = (idx % columns) * tile
        y = (idx // columns) * (tile + label_h)
        render = renders.get(row.id)
        if render is not None:
            sheet.paste(_thumb(render, tile), (x, y))
        else:
            # Broken/missing renderer (pattern mid-rebuild, purged, or threw): draw a
            # placeholder tile instead of KeyError-crashing the whole contact sheet.
            draw.rectangle((x, y, x + tile, y + tile), fill=(40, 20, 20))
            draw.text((x + 6, y + tile // 2 - 8), "NO RENDER", fill=(220, 120, 120), font=font)
        color = (34, 100, 46) if row.score >= 82 else (120, 90, 28) if row.score >= 72 else (116, 34, 34)
        draw.rectangle((x, y + tile, x + tile, y + tile + label_h), fill=color)
        draw.text((x + 4, y + tile + 4), f"{row.score:05.2f} {row.id[:22]}", fill=(245, 245, 245), font=font)
        draw.text((x + 4, y + tile + 22), ",".join(row.flags[:2])[:28], fill=(245, 220, 180), font=font)
    sheet.save(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", type=int, default=192)
    ap.add_argument("--seed", type=int, default=7301)
    ap.add_argument("--threshold", type=float, default=96.0)
    ap.add_argument("--columns", type=int, default=6)
    ap.add_argument("--ids", default="", help="Optional comma-separated picker ids for focused visual review")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--fail-on-rebuild", action="store_true")
    args = ap.parse_args(argv)

    specs, group_by_id = _load_ui_spec_patterns()
    if args.ids:
        selected = {value.strip() for value in args.ids.split(",") if value.strip()}
        specs = [meta for meta in specs if str(meta.get("id") or "") in selected]
    catalog = _quiet_catalog()
    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "spec_pattern_quality" / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    metas: dict[str, dict[str, Any]] = {}
    renders: dict[str, np.ndarray] = {}
    structures: dict[str, np.ndarray] = {}
    vectors: dict[str, np.ndarray] = {}
    channel_stats: dict[str, tuple[list[float], list[float], float]] = {}
    render_times: dict[str, float] = {}
    broken: list[SpecPatternGrade] = []

    for meta in specs:
        pid = str(meta.get("id") or "")
        if not pid:
            continue
        merged = dict(meta)
        merged["group"] = group_by_id.get(pid, merged.get("category", "Ungrouped"))
        metas[pid] = merged
        fn = catalog.get(pid)
        if fn is None:
            broken.append(SpecPatternGrade(
                id=pid, name=str(merged.get("name") or pid), category=str(merged.get("group")),
                score=0.0, intent=0.0, originality=0.0, wow=0.0, detail=0.0, coverage=0.0,
                physics=0.0,
                active_fraction=0.0, fine_energy=0.0, residual_energy=0.0, entropy=0.0,
                dynamic_range=0.0, edge_density=0.0, largest_region_ratio=0.0,
                largest_region_detail=0.0, max_abs_correlation=1.0,
                nearest_id="", channel_stds=[], channel_spans=[], min_channel_std=0.0,
                min_channel_span=0.0, max_channel_correlation=1.0, render_ms=0.0,
                material_family=_family(pid, str(merged.get("name") or pid), str(merged.get("group"))),
                flags=["BROKEN_MISSING_RENDERER"], rebuild_required=True,
                error="id missing from engine.spec_patterns.PATTERN_CATALOG",
            ))
            continue
        try:
            started = time.perf_counter()
            arr = np.asarray(fn((args.size, args.size), args.seed, 1.0), dtype=np.float32)
            arr = np.clip(arr, 0, 1).astype(np.float32)
            render_times[pid] = (time.perf_counter() - started) * 1000.0
            structure, channels = _structure_and_channels(arr)
        except Exception as exc:
            broken.append(SpecPatternGrade(
                id=pid, name=str(merged.get("name") or pid), category=str(merged.get("group")),
                score=0.0, intent=0.0, originality=0.0, wow=0.0, detail=0.0, coverage=0.0,
                physics=0.0,
                active_fraction=0.0, fine_energy=0.0, residual_energy=0.0, entropy=0.0,
                dynamic_range=0.0, edge_density=0.0, largest_region_ratio=0.0,
                largest_region_detail=0.0, max_abs_correlation=1.0,
                nearest_id="", channel_stds=[], channel_spans=[], min_channel_std=0.0,
                min_channel_span=0.0, max_channel_correlation=1.0, render_ms=0.0,
                material_family=_family(pid, str(merged.get("name") or pid), str(merged.get("group"))),
                flags=["BROKEN_EXCEPTION"], rebuild_required=True,
                error=f"{type(exc).__name__}: {exc}",
            ))
            continue
        renders[pid] = arr
        structures[pid] = structure
        vectors[pid] = struct_sig(structure)
        channel_stats[pid] = _channel_metrics(channels)

    max_corr: dict[str, float] = {pid: 0.0 for pid in vectors}
    nearest: dict[str, str] = {pid: "" for pid in vectors}
    ids = list(vectors)
    if ids:
        signature_matrix = _whiten(np.asarray([vectors[pid] for pid in ids], dtype=np.float32))
        similarity = signature_matrix @ signature_matrix.T
        np.fill_diagonal(similarity, -1.0)
        for idx, pid in enumerate(ids):
            match_idx = int(np.argmax(similarity[idx]))
            max_corr[pid] = float(similarity[idx, match_idx])
            nearest[pid] = ids[match_idx]

    rows = []
    for pid in renders:
        stds, spans, channel_corr = channel_stats[pid]
        rows.append(_grade(
            pid, metas[pid], structures[pid], max_corr.get(pid, 0.0), nearest.get(pid, ""),
            stds, spans, channel_corr, render_times.get(pid, 0.0), args.threshold,
        ))
    rows.extend(broken)
    ranked = sorted(rows, key=lambda r: (r.score, r.id))
    by_best = sorted(rows, key=lambda r: (-r.score, r.id))
    rebuild = [r for r in ranked if r.rebuild_required]

    _write_sheet(out_dir / "ranked_worst_first.png", ranked, renders, args.columns, args.size)
    _write_sheet(out_dir / "ranked_best_first.png", by_best, renders, args.columns, args.size)
    _write_sheet(out_dir / "rebuild_required.png", rebuild, renders, args.columns, args.size)

    payload = {
        "size": args.size,
        "seed": args.seed,
        "threshold": args.threshold,
        "count": len(rows),
        "rebuild_required_count": len(rebuild),
        "weak_channel_std_count": sum("WEAK_CHANNEL_STD" in row.flags for row in rows),
        "narrow_channel_range_count": sum("NARROW_CHANNEL_RANGE" in row.flags for row in rows),
        "channel_coupled_count": sum("CHANNEL_COUPLED" in row.flags for row in rows),
        "near_duplicate_count": sum("NEAR_DUPLICATE" in row.flags for row in rows),
        "rows": [asdict(r) for r in ranked],
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Spec Pattern Quality Audit",
        "",
        f"- Count: {len(rows)}",
        f"- Threshold: {args.threshold:.1f}",
        f"- Rebuild required: {len(rebuild)}",
        f"- Weakest channel std below 20/255: {payload['weak_channel_std_count']}",
        f"- Weakest channel span below 0.70: {payload['narrow_channel_range_count']}",
        f"- M/R/CC max |correlation| at or above 0.85: {payload['channel_coupled_count']}",
        f"- Structural nearest-neighbor similarity at or above 0.80: {payload['near_duplicate_count']}",
        f"- Worst-first sheet: `ranked_worst_first.png`",
        f"- Rebuild sheet: `rebuild_required.png`",
        "",
        "## Rubric",
        "",
        "- Total = intent 20%, originality 16%, wow 16%, detail 18%, coverage 12%, M/R/CC physics 18%.",
        "- Physics grades weakest-channel std/range plus M/R/CC independence; hard gates use std 20/255, span 0.70, and max |corr| 0.85.",
        "- Structural nearest-neighbor similarity at or above 0.80 is a hard review flag; owner-eye review adjudicates frequency-signature false positives.",
        "",
        "## Rebuild Required",
        "",
    ]
    if rebuild:
        lines.append("| Rank | ID | Name | Group | Score | Nearest | Similarity | Min std | Min span | Corr | Flags |")
        lines.append("|---:|---|---|---|---:|---|---:|---:|---:|---:|---|")
        for idx, row in enumerate(rebuild, 1):
            lines.append(
                f"| {idx} | `{row.id}` | {row.name} | {row.category} | {row.score:.2f} | "
                f"`{row.nearest_id}` | {row.max_abs_correlation:.3f} | {row.min_channel_std:.4f} | "
                f"{row.min_channel_span:.3f} | {row.max_channel_correlation:.3f} | {', '.join(row.flags)} |"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Top 25", "", "| Rank | ID | Name | Group | Score |", "|---:|---|---|---|---:|"])
    for idx, row in enumerate(by_best[:25], 1):
        lines.append(f"| {idx} | `{row.id}` | {row.name} | {row.category} | {row.score:.2f} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Spec patterns graded: {len(rows)}")
    print(f"Rebuild required: {len(rebuild)}")
    print(f"Output: {out_dir}")
    if rebuild:
        print("Worst 20:")
        for row in rebuild[:20]:
            print(f"  {row.score:6.2f} {row.id} [{', '.join(row.flags)}]")
    return 1 if args.fail_on_rebuild and rebuild else 0


if __name__ == "__main__":
    raise SystemExit(main())
