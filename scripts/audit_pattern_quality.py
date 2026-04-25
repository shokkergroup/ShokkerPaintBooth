#!/usr/bin/env python3
"""Grade shipping regular Pattern categories and rank rebuild candidates.

Unlike Spec Pattern overlays, regular Patterns are painter-visible color/shape
surfaces. This audit grades the actual grouped UI catalog, renders thumbnails,
and scores each pattern on a 100-point Alpha-quality rubric:

  - intent: does it look like the named/category concept?
  - originality: is it visually distinct from sibling patterns?
  - wow: contrast, edges, hierarchy, visual punch
  - detail: pixel/near-pixel detail for a 2048 canvas
  - coverage: how much of the canvas is materially engaged

Image-backed user assets are graded and ranked, but not automatically marked
for source rebuild because their source artwork is intentionally user-curated.
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


def _safe_console(text: str) -> str:
    return str(text).encode("ascii", "replace").decode("ascii")


@dataclass
class PatternGrade:
    id: str
    name: str
    category: str
    renderer: str
    score: float
    intent: float
    originality: float
    wow: float
    detail: float
    coverage: float
    active_fraction: float
    fine_energy: float
    residual_energy: float
    entropy: float
    dynamic_range: float
    edge_density: float
    color_population: float
    largest_region_ratio: float
    largest_region_detail: float
    max_abs_correlation: float
    flags: list[str]
    rebuild_required: bool
    error: str | None = None


def _load_ui_patterns() -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, str]]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
const patterns = vm.runInContext('PATTERNS', ctx);
const groups = vm.runInContext('PATTERN_GROUPS', ctx);
const groupById = {};
for (const [group, ids] of Object.entries(groups)) {
  for (const id of ids) if (!groupById[id]) groupById[id] = group;
}
console.log(JSON.stringify({ patterns, groups, groupById }));
"""
    out = subprocess.check_output(["node", "-e", script], cwd=REPO, text=True, encoding="utf-8")
    payload = json.loads(out)
    return payload["patterns"], payload["groups"], payload["groupById"]


def _quiet_engine():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import shokker_engine_v2 as eng
        eng._ensure_expansions_loaded()
    return eng


def _norm01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _score_clip(value: float, target: float, floor: float = 0.0) -> float:
    return float(np.clip((value - floor) / max(target - floor, 1e-6) * 100.0, 0.0, 100.0))


def _fine_energy(arr: np.ndarray) -> float:
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    dx = np.abs(np.diff(gray, axis=1)).mean()
    dy = np.abs(np.diff(gray, axis=0)).mean()
    return float(dx + dy)


def _residual_energy(arr: np.ndarray, block: int = 8) -> float:
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    h, w = gray.shape[:2]
    hh = h - h % block
    ww = w - w % block
    if hh < block or ww < block:
        return 0.0
    cropped = gray[:hh, :ww]
    coarse = cropped.reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
    up = np.repeat(np.repeat(coarse, block, axis=0), block, axis=1)
    return float(np.abs(cropped - up).mean())


def _entropy(arr: np.ndarray) -> float:
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    hist, _ = np.histogram(np.clip(gray, 0, 1), bins=32, range=(0, 1))
    p = hist.astype(np.float64)
    p = p[p > 0] / max(p.sum(), 1.0)
    if p.size == 0:
        return 0.0
    return float(-(p * np.log2(p)).sum() / math.log2(32))


def _edge_density(arr: np.ndarray) -> float:
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    u8 = np.clip(gray * 255, 0, 255).astype(np.uint8)
    edges = cv2.Canny(u8, 36, 96)
    return float((edges > 0).mean())


def _color_population(rgb: np.ndarray) -> float:
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        return 0.0
    bins = np.floor(np.clip(rgb[:, :, :3], 0, 0.999) * 8).astype(np.int16)
    packed = bins[:, :, 0] * 64 + bins[:, :, 1] * 8 + bins[:, :, 2]
    counts = np.bincount(packed.ravel(), minlength=512).astype(np.float32)
    return float((counts > (rgb.shape[0] * rgb.shape[1] * 0.0015)).sum())


def _largest_region_detail(arr: np.ndarray, levels: int = 6) -> tuple[float, float]:
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    gray = _norm01(gray)
    smooth = cv2.GaussianBlur(gray, (0, 0), sigmaX=8.0, sigmaY=8.0)
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
    blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.5, sigmaY=2.5)
    return float(best_area / gray.size), float(np.abs(gray[best_mask] - blur[best_mask]).mean())


def _resolve_asset(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    p = str(path_text).replace("\\", "/")
    if p.startswith("/"):
        p = p[1:]
    path = REPO / p
    return path if path.exists() else None


def _load_image_pattern(meta: dict[str, Any], size: int, entry: dict[str, Any] | None = None) -> tuple[np.ndarray | None, str | None]:
    path_text = None
    if isinstance(entry, dict):
        path_text = entry.get("image_path") or entry.get("swatch_image")
    path_text = path_text or meta.get("swatch_image") or meta.get("image_path")
    path = _resolve_asset(path_text)
    if path is None:
        return None, "image asset missing"
    try:
        img = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
        return np.asarray(img, dtype=np.float32) / 255.0, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _render_pattern(eng, meta: dict[str, Any], size: int, seed: int) -> tuple[np.ndarray | None, np.ndarray | None, str, str | None]:
    pid = str(meta.get("id") or "")
    entry = eng.PATTERN_REGISTRY.get(pid)
    if not isinstance(entry, dict):
        img, err = _load_image_pattern(meta, size)
        return img, img, "image" if img is not None else "missing", err or "missing PATTERN_REGISTRY entry"
    if callable(entry.get("texture_fn")):
        mask = np.ones((size, size), dtype=np.float32)
        tex = entry["texture_fn"]((size, size), mask, seed, 1.0)
        pv = _norm01(np.asarray(tex.get("pattern_val"), dtype=np.float32))
        try:
            base = np.full((size, size, 3), 0.18, dtype=np.float32)
            bb = np.zeros((size, size), dtype=np.float32)
            rgb = eng.overlay_pattern_paint(base, pid, (size, size), mask, seed, 1.0, bb, scale=1.0, opacity=1.0, rotation=0, spec_mult=1.0)
            rgb = np.clip(rgb[:, :, :3], 0, 1).astype(np.float32)
        except Exception:
            rgb = np.dstack([pv, pv, pv]).astype(np.float32)
        return pv, rgb, "procedural", None
    img, err = _load_image_pattern(meta, size, entry)
    if img is not None:
        return img.mean(axis=2), img, "image", None
    return None, None, "missing", err or "no texture_fn and no image asset"


def _family(pid: str, name: str, category: str) -> str:
    s = f"{pid} {name} {category}".lower()
    if any(t in s for t in ("tech", "circuit", "pcb", "graphene", "gear", "fiber", "sonar", "waveform", "data", "matrix", "cyber")):
        return "tech"
    if any(t in s for t in ("surface accent", "accent", "frost", "wax", "scratch", "clearcoat", "chrome_delete", "flip")):
        return "surface"
    if any(t in s for t in ("world geometry", "tribal", "cultural", "calendar", "knot", "fret", "medallion", "interlace")):
        return "world"
    if any(t in s for t in ("natural", "nature", "marble", "wood", "bark", "leaf", "water", "fern", "cloud", "flame", "dragonfly", "coral", "geode", "snake")):
        return "natural"
    if any(t in s for t in ("art deco", "textile", "geometric", "advanced", "op-art", "visual illusion", "moire", "checker", "rings", "hypnotic")):
        return "geometry"
    if any(t in s for t in ("decade", "50s", "60s", "70s", "80s", "90s")):
        return "decade"
    if any(t in s for t in ("abstract", "experimental", "biomechanical", "fractal", "stardust", "illusion")):
        return "abstract"
    return "general"


def _intent_score(family: str, active: float, fine: float, residual: float, entropy: float,
                  edge: float, dyn: float, color_pop: float, region_ratio: float, region_detail: float) -> float:
    coverage_base = _score_clip(active, 0.52)
    detail_base = _score_clip(residual, 0.065)
    fine_base = _score_clip(fine, 0.18)
    edge_base = _score_clip(edge, 0.20)
    dyn_base = _score_clip(dyn, 0.82)
    entropy_base = _score_clip(entropy, 0.88)
    color_base = _score_clip(color_pop, 14.0)
    inside = _score_clip(region_detail, 0.028)
    anti_blob = float(np.clip((1.0 - region_ratio) / 0.76 * 100.0, 0, 100))
    if family == "tech":
        return 0.28 * edge_base + 0.24 * detail_base + 0.20 * coverage_base + 0.13 * entropy_base + 0.10 * dyn_base + 0.05 * inside
    if family == "surface":
        return 0.27 * detail_base + 0.24 * coverage_base + 0.18 * edge_base + 0.16 * entropy_base + 0.10 * dyn_base + 0.05 * inside
    if family == "world":
        return 0.26 * edge_base + 0.23 * coverage_base + 0.21 * detail_base + 0.16 * dyn_base + 0.09 * entropy_base + 0.05 * inside
    if family == "natural":
        return 0.24 * coverage_base + 0.22 * entropy_base + 0.20 * detail_base + 0.16 * anti_blob + 0.11 * dyn_base + 0.07 * inside
    if family == "geometry":
        return 0.28 * edge_base + 0.23 * coverage_base + 0.20 * detail_base + 0.15 * dyn_base + 0.09 * entropy_base + 0.05 * inside
    if family == "decade":
        return 0.24 * color_base + 0.22 * edge_base + 0.20 * coverage_base + 0.16 * detail_base + 0.12 * entropy_base + 0.06 * dyn_base
    if family == "abstract":
        return 0.24 * entropy_base + 0.22 * dyn_base + 0.20 * detail_base + 0.18 * coverage_base + 0.10 * color_base + 0.06 * edge_base
    return 0.23 * coverage_base + 0.22 * detail_base + 0.19 * entropy_base + 0.18 * dyn_base + 0.10 * edge_base + 0.08 * color_base


def _grade(meta: dict[str, Any], category: str, renderer: str, scalar: np.ndarray, rgb: np.ndarray,
           max_corr: float, threshold: float) -> PatternGrade:
    pid = str(meta.get("id") or "")
    name = str(meta.get("name") or pid)
    arr = _norm01(scalar)
    rgb = np.clip(rgb if rgb.ndim == 3 else np.dstack([arr, arr, arr]), 0, 1).astype(np.float32)
    gray = _norm01(rgb.mean(axis=2) * 0.50 + arr * 0.50)
    active = float((np.abs(gray - 0.5) > 0.055).mean())
    fine = _fine_energy(gray)
    residual = _residual_energy(gray)
    ent = _entropy(gray)
    dyn = float(np.quantile(gray, 0.98) - np.quantile(gray, 0.02))
    edge = _edge_density(gray)
    color_pop = _color_population(rgb)
    region_ratio, region_detail = _largest_region_detail(gray)
    fam = _family(pid, name, category)
    intent = _intent_score(fam, active, fine, residual, ent, edge, dyn, color_pop, region_ratio, region_detail)
    originality = float(np.clip((1.0 - max_corr) / 0.42 * 100.0, 0, 100))
    if fam in {"tech", "geometry", "world"}:
        wow = 0.30 * _score_clip(edge, 0.20) + 0.22 * _score_clip(dyn, 0.82) + 0.20 * _score_clip(residual, 0.065) + 0.16 * _score_clip(ent, 0.88) + 0.12 * _score_clip(region_detail, 0.028)
    elif fam in {"natural", "surface"}:
        wow = 0.24 * _score_clip(ent, 0.88) + 0.23 * _score_clip(residual, 0.065) + 0.20 * _score_clip(dyn, 0.82) + 0.18 * _score_clip(edge, 0.20) + 0.15 * _score_clip(region_detail, 0.028)
    else:
        wow = 0.25 * _score_clip(dyn, 0.82) + 0.22 * _score_clip(ent, 0.88) + 0.21 * _score_clip(edge, 0.20) + 0.19 * _score_clip(residual, 0.065) + 0.13 * _score_clip(color_pop, 14.0)
    detail = 0.52 * _score_clip(residual, 0.065) + 0.26 * _score_clip(fine, 0.18) + 0.22 * _score_clip(region_detail, 0.028)
    coverage = _score_clip(active, 0.52)
    score = 0.24 * intent + 0.14 * originality + 0.20 * wow + 0.26 * detail + 0.16 * coverage
    flags: list[str] = []
    if coverage < 76:
        flags.append("LOW_COVERAGE")
    if detail < 78:
        flags.append("LOW_DETAIL")
    if intent < 78:
        flags.append("LOW_INTENT")
    if wow < 74:
        flags.append("LOW_WOW")
    if originality < 42:
        flags.append("NEAR_DUPLICATE")
    if region_ratio > 0.74 and region_detail < 0.024:
        flags.append("BLOB_OR_FLAT_REGION")
    if color_pop < 3 and fam in {"decade", "abstract"}:
        flags.append("LOW_COLOR_POPULATION")
    auto_rebuildable = renderer == "procedural"
    rebuild = auto_rebuildable and (score < threshold or bool({"LOW_COVERAGE", "LOW_DETAIL", "LOW_INTENT", "BLOB_OR_FLAT_REGION"} & set(flags)))
    if renderer == "image" and score < threshold:
        flags.append("IMAGE_REVIEW_ONLY")
    return PatternGrade(
        id=pid,
        name=name,
        category=category,
        renderer=renderer,
        score=round(score, 2),
        intent=round(intent, 2),
        originality=round(originality, 2),
        wow=round(wow, 2),
        detail=round(detail, 2),
        coverage=round(coverage, 2),
        active_fraction=round(active, 5),
        fine_energy=round(fine, 6),
        residual_energy=round(residual, 6),
        entropy=round(ent, 5),
        dynamic_range=round(dyn, 5),
        edge_density=round(edge, 5),
        color_population=round(color_pop, 2),
        largest_region_ratio=round(region_ratio, 5),
        largest_region_detail=round(region_detail, 6),
        max_abs_correlation=round(max_corr, 5),
        flags=flags,
        rebuild_required=rebuild,
    )


def _thumb(rgb: np.ndarray, tile: int) -> Image.Image:
    arr = np.clip(rgb[:, :, :3] * 255, 0, 255).astype(np.uint8) if rgb.ndim == 3 else np.clip(np.dstack([rgb, rgb, rgb]) * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").resize((tile, tile), Image.Resampling.LANCZOS)


def _write_sheet(path: Path, rows: list[PatternGrade], previews: dict[str, np.ndarray], columns: int, tile: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        sheet = Image.new("RGB", (columns * tile, tile), (18, 18, 22))
        ImageDraw.Draw(sheet).text((12, 12), "No patterns in this sheet.", fill=(235, 235, 235), font=ImageFont.load_default())
        sheet.save(path)
        return
    label_h = 52
    rows_n = math.ceil(len(rows) / columns)
    sheet = Image.new("RGB", (columns * tile, rows_n * (tile + label_h)), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, row in enumerate(rows):
        x = (idx % columns) * tile
        y = (idx // columns) * (tile + label_h)
        sheet.paste(_thumb(previews[row.id], tile), (x, y))
        fill = (34, 100, 46) if row.score >= 90 else (120, 90, 28) if row.score >= 82 else (116, 34, 34)
        draw.rectangle((x, y + tile, x + tile, y + tile + label_h), fill=fill)
        draw.text((x + 4, y + tile + 4), f"{row.score:05.2f} {row.id[:22]}", fill=(245, 245, 245), font=font)
        draw.text((x + 4, y + tile + 22), row.category[:24], fill=(220, 235, 245), font=font)
        draw.text((x + 4, y + tile + 38), ",".join(row.flags[:2])[:28], fill=(245, 220, 180), font=font)
    sheet.save(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", type=int, default=192)
    ap.add_argument("--seed", type=int, default=8301)
    ap.add_argument("--threshold", type=float, default=88.0)
    ap.add_argument("--columns", type=int, default=6)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--fail-on-rebuild", action="store_true")
    args = ap.parse_args(argv)

    patterns, groups, group_by_id = _load_ui_patterns()
    eng = _quiet_engine()
    meta_by_id = {str(p.get("id")): dict(p) for p in patterns if p.get("id")}
    grouped_ids = []
    for ids in groups.values():
        for pid in ids:
            if pid not in grouped_ids:
                grouped_ids.append(pid)

    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "pattern_quality" / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    scalars: dict[str, np.ndarray] = {}
    previews: dict[str, np.ndarray] = {}
    renderers: dict[str, str] = {}
    errors: dict[str, str] = {}
    vectors: dict[str, np.ndarray] = {}

    for pid in grouped_ids:
        meta = meta_by_id.get(pid, {"id": pid, "name": pid})
        scalar, rgb, renderer, err = _render_pattern(eng, meta, args.size, args.seed)
        if scalar is None or rgb is None:
            errors[pid] = err or "render failed"
            scalars[pid] = np.zeros((args.size, args.size), dtype=np.float32)
            previews[pid] = np.zeros((args.size, args.size, 3), dtype=np.float32)
            renderers[pid] = renderer
            vectors[pid] = np.zeros(args.size * args.size, dtype=np.float32)
            continue
        scalars[pid] = _norm01(scalar)
        previews[pid] = np.clip(rgb if rgb.ndim == 3 else np.dstack([scalar, scalar, scalar]), 0, 1).astype(np.float32)
        renderers[pid] = renderer
        vectors[pid] = _norm01(previews[pid].mean(axis=2) * 0.5 + scalars[pid] * 0.5).ravel()

    max_corr: dict[str, float] = {pid: 0.0 for pid in vectors}
    ids = list(vectors)
    for i, a in enumerate(ids):
        va = vectors[a]
        sa = float(np.std(va))
        if sa < 1e-6:
            max_corr[a] = 1.0
            continue
        for b in ids[i + 1:]:
            vb = vectors[b]
            sb = float(np.std(vb))
            if sb < 1e-6:
                continue
            corr = abs(float(np.corrcoef(va, vb)[0, 1]))
            max_corr[a] = max(max_corr[a], corr)
            max_corr[b] = max(max_corr[b], corr)

    rows: list[PatternGrade] = []
    for pid in grouped_ids:
        meta = meta_by_id.get(pid, {"id": pid, "name": pid})
        category = str(group_by_id.get(pid, meta.get("category") or "Ungrouped"))
        if pid in errors:
            rows.append(PatternGrade(
                id=pid, name=str(meta.get("name") or pid), category=category, renderer=renderers.get(pid, "missing"),
                score=0.0, intent=0.0, originality=0.0, wow=0.0, detail=0.0, coverage=0.0,
                active_fraction=0.0, fine_energy=0.0, residual_energy=0.0, entropy=0.0, dynamic_range=0.0,
                edge_density=0.0, color_population=0.0, largest_region_ratio=0.0, largest_region_detail=0.0,
                max_abs_correlation=1.0, flags=["BROKEN_RENDER"], rebuild_required=renderers.get(pid) == "procedural",
                error=errors[pid],
            ))
            continue
        rows.append(_grade(meta, category, renderers[pid], scalars[pid], previews[pid], max_corr.get(pid, 0.0), args.threshold))

    ranked = sorted(rows, key=lambda r: (r.score, r.id))
    best = sorted(rows, key=lambda r: (-r.score, r.id))
    rebuild = [r for r in ranked if r.rebuild_required]
    review = [r for r in ranked if "IMAGE_REVIEW_ONLY" in r.flags]

    _write_sheet(out_dir / "ranked_worst_first.png", ranked, previews, args.columns, args.size)
    _write_sheet(out_dir / "ranked_best_first.png", best, previews, args.columns, args.size)
    _write_sheet(out_dir / "rebuild_required.png", rebuild, previews, args.columns, args.size)
    _write_sheet(out_dir / "image_review_only.png", review, previews, args.columns, args.size)

    category_summary = []
    for group, ids_in_group in groups.items():
        subset = [r for r in rows if r.id in ids_in_group]
        if not subset:
            continue
        category_summary.append({
            "category": group,
            "count": len(subset),
            "average_score": round(float(np.mean([r.score for r in subset])), 2),
            "min_score": round(float(min(r.score for r in subset)), 2),
            "rebuild_required": sum(1 for r in subset if r.rebuild_required),
            "image_review_only": sum(1 for r in subset if "IMAGE_REVIEW_ONLY" in r.flags),
        })
    category_summary.sort(key=lambda x: (x["average_score"], x["category"]))

    payload = {
        "size": args.size,
        "seed": args.seed,
        "threshold": args.threshold,
        "count": len(rows),
        "rebuild_required_count": len(rebuild),
        "image_review_only_count": len(review),
        "category_summary": category_summary,
        "rows": [asdict(r) for r in ranked],
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Regular Pattern Quality Audit",
        "",
        f"- Count: {len(rows)}",
        f"- Threshold: {args.threshold:.1f}",
        f"- Rebuild required: {len(rebuild)}",
        f"- Image review only: {len(review)}",
        "",
        "## Rubric",
        "",
        "- Total = intent 24%, originality 14%, wow factor 20%, detail 26%, canvas coverage 16%.",
        "- Procedural patterns hard-rebuild on low coverage, low detail, low intent, or blob/flat largest-region flags.",
        "- Image-backed/user-art patterns are graded but marked review-only instead of auto-rebuilt.",
        "",
        "## Weakest Categories",
        "",
        "| Category | Count | Avg | Min | Rebuild | Image Review |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in category_summary[:20]:
        lines.append(f"| {row['category']} | {row['count']} | {row['average_score']:.2f} | {row['min_score']:.2f} | {row['rebuild_required']} | {row['image_review_only']} |")
    lines.extend(["", "## Rebuild Required", ""])
    if rebuild:
        lines.append("| Rank | ID | Name | Category | Score | Flags |")
        lines.append("|---:|---|---|---|---:|---|")
        for idx, row in enumerate(rebuild, 1):
            lines.append(f"| {idx} | `{row.id}` | {row.name} | {row.category} | {row.score:.2f} | {', '.join(row.flags)} |")
    else:
        lines.append("- None")
    lines.extend(["", "## Top 25", "", "| Rank | ID | Name | Category | Score |", "|---:|---|---|---|---:|"])
    for idx, row in enumerate(best[:25], 1):
        lines.append(f"| {idx} | `{row.id}` | {row.name} | {row.category} | {row.score:.2f} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Patterns graded: {len(rows)}")
    print(f"Rebuild required: {len(rebuild)}")
    print(f"Image review only: {len(review)}")
    print(f"Output: {out_dir}")
    if category_summary:
        print("Weakest categories:")
        for row in category_summary[:10]:
            print(_safe_console(f"  {row['average_score']:6.2f} {row['category']} rebuild={row['rebuild_required']}"))
    if rebuild:
        print("Worst rebuild candidates:")
        for row in rebuild[:30]:
            print(_safe_console(f"  {row.score:6.2f} {row.id} [{', '.join(row.flags)}]"))
    return 1 if args.fail_on_rebuild and rebuild else 0


if __name__ == "__main__":
    raise SystemExit(main())
