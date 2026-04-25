#!/usr/bin/env python3
"""Grade shipping Spec Pattern Overlay thumbnails and rank rebuild candidates.

This script renders every UI-shipping SPEC_PATTERNS id, scores it on a
100-point rubric, and writes ranked thumbnails plus JSON/Markdown reports.

Score components:
  - intent: category/name-specific behavior fit
  - originality: inverse visual correlation against other patterns
  - wow: contrast, entropy, edges, highlight structure
  - detail: pixel-scale and near-pixel residual structure
  - coverage: how much of the 2048-style canvas is materially affected
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
    active_fraction: float
    fine_energy: float
    residual_energy: float
    entropy: float
    dynamic_range: float
    edge_density: float
    largest_region_ratio: float
    largest_region_detail: float
    max_abs_correlation: float
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


def _grade(pid: str, meta: dict[str, Any], arr: np.ndarray, max_corr: float, threshold: float) -> SpecPatternGrade:
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
    score = 0.24 * intent + 0.16 * originality + 0.20 * wow + 0.24 * detail + 0.16 * coverage
    flags: list[str] = []
    if coverage < 70:
        flags.append("LOW_COVERAGE")
    if detail < 70:
        flags.append("LOW_DETAIL")
    if intent < 70:
        flags.append("LOW_INTENT")
    if wow < 65:
        flags.append("LOW_WOW")
    if originality < 45:
        flags.append("NEAR_DUPLICATE")
    if region_ratio > 0.72 and region_detail < 0.022:
        flags.append("BLOB_OR_FLAT_REGION")
    rebuild = score < threshold or bool({"LOW_COVERAGE", "LOW_DETAIL", "LOW_INTENT", "BLOB_OR_FLAT_REGION"} & set(flags))
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
        active_fraction=round(active, 5),
        fine_energy=round(fine, 6),
        residual_energy=round(residual, 6),
        entropy=round(ent, 5),
        dynamic_range=round(dyn, 5),
        edge_density=round(edge, 5),
        largest_region_ratio=round(region_ratio, 5),
        largest_region_detail=round(region_detail, 6),
        max_abs_correlation=round(max_corr, 5),
        flags=flags,
        rebuild_required=rebuild,
    )


def _thumb(arr: np.ndarray, tile: int) -> Image.Image:
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
        sheet.paste(_thumb(renders[row.id], tile), (x, y))
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
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--fail-on-rebuild", action="store_true")
    args = ap.parse_args(argv)

    specs, group_by_id = _load_ui_spec_patterns()
    catalog = _quiet_catalog()
    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "spec_pattern_quality" / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    metas: dict[str, dict[str, Any]] = {}
    renders: dict[str, np.ndarray] = {}
    vectors: dict[str, np.ndarray] = {}
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
                active_fraction=0.0, fine_energy=0.0, residual_energy=0.0, entropy=0.0,
                dynamic_range=0.0, edge_density=0.0, largest_region_ratio=0.0,
                largest_region_detail=0.0, max_abs_correlation=1.0,
                flags=["BROKEN_MISSING_RENDERER"], rebuild_required=True,
                error="id missing from engine.spec_patterns.PATTERN_CATALOG",
            ))
            continue
        try:
            arr = np.asarray(fn((args.size, args.size), args.seed, 1.0), dtype=np.float32)
            if arr.ndim != 2:
                raise ValueError(f"expected 2D array, got {arr.shape}")
            arr = np.clip(arr, 0, 1).astype(np.float32)
        except Exception as exc:
            broken.append(SpecPatternGrade(
                id=pid, name=str(merged.get("name") or pid), category=str(merged.get("group")),
                score=0.0, intent=0.0, originality=0.0, wow=0.0, detail=0.0, coverage=0.0,
                active_fraction=0.0, fine_energy=0.0, residual_energy=0.0, entropy=0.0,
                dynamic_range=0.0, edge_density=0.0, largest_region_ratio=0.0,
                largest_region_detail=0.0, max_abs_correlation=1.0,
                flags=["BROKEN_EXCEPTION"], rebuild_required=True,
                error=f"{type(exc).__name__}: {exc}",
            ))
            continue
        renders[pid] = arr
        vectors[pid] = _norm01(arr).ravel()

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
            if corr > max_corr[a]:
                max_corr[a] = corr
            if corr > max_corr[b]:
                max_corr[b] = corr

    rows = [_grade(pid, metas[pid], renders[pid], max_corr.get(pid, 0.0), args.threshold) for pid in renders]
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
        "rows": [asdict(r) for r in ranked],
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Spec Pattern Quality Audit",
        "",
        f"- Count: {len(rows)}",
        f"- Threshold: {args.threshold:.1f}",
        f"- Rebuild required: {len(rebuild)}",
        f"- Worst-first sheet: `ranked_worst_first.png`",
        f"- Rebuild sheet: `rebuild_required.png`",
        "",
        "## Rubric",
        "",
        "- Total = intent 24%, originality 16%, wow factor 20%, detail 24%, canvas coverage 16%.",
        "- Hard rebuild also triggers on low coverage, low detail, low intent, or blob/flat largest-region flags.",
        "",
        "## Rebuild Required",
        "",
    ]
    if rebuild:
        lines.append("| Rank | ID | Name | Group | Score | Flags |")
        lines.append("|---:|---|---|---|---:|---|")
        for idx, row in enumerate(rebuild, 1):
            lines.append(f"| {idx} | `{row.id}` | {row.name} | {row.category} | {row.score:.2f} | {', '.join(row.flags)} |")
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
