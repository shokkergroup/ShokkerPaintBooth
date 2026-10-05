#!/usr/bin/env python3
"""Render and score SPB finish/pattern categories.

Examples:
  python scripts/finish_visual_audit.py --category "★ COLORSHOXX" --limit 25
  python scripts/finish_visual_audit.py --category Ornamental --size 256
  python scripts/finish_visual_audit.py --ids cx_hyperflip_red_blue,cx_gold_green
  python scripts/finish_visual_audit.py --patterns decade_ --limit 20

Outputs are written under audit/finish_visual_audit/<timestamp>/ by default:
  contact_sheet.png  paint previews
  spec_sheet.png     M/R/CC previews where available
  report.json        machine-readable metrics
  report.md          human-readable triage summary
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _quiet_import_engine():
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as eng
        eng._ensure_expansions_loaded()
    return eng


def _load_js_special_groups() -> dict[str, list[str]]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
console.log(JSON.stringify(vm.runInContext('SPECIAL_GROUPS', ctx)));
"""
    out = subprocess.check_output(["node", "-e", script], cwd=REPO, text=True, encoding="utf-8")
    return json.loads(out)


def _norm01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _fine_energy(arr: np.ndarray) -> float:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    dx = np.abs(np.diff(arr, axis=1)).mean()
    dy = np.abs(np.diff(arr, axis=0)).mean()
    return float(dx + dy)


def _residual_energy(arr: np.ndarray, block: int = 8) -> float:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    h, w = arr.shape[:2]
    hh = h - h % block
    ww = w - w % block
    if hh < block or ww < block:
        return 0.0
    cropped = arr[:hh, :ww]
    coarse = cropped.reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
    up = np.repeat(np.repeat(coarse, block, axis=0), block, axis=1)
    return float(np.abs(cropped - up).mean())


def _large_blob_ratio(arr: np.ndarray, block: int = 32) -> float:
    arr = _norm01(arr.mean(axis=2) if arr.ndim == 3 else arr)
    h, w = arr.shape[:2]
    hh = h - h % block
    ww = w - w % block
    if hh < block or ww < block:
        return 0.0
    cropped = arr[:hh, :ww]
    coarse = cropped.reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
    return float(np.std(coarse) / (np.std(cropped) + 1e-6))


def _largest_region_detail(arr: np.ndarray, block: int = 16, levels: int = 6) -> tuple[float, float, float]:
    """Measure detail inside the largest connected low-frequency region."""
    arr = _norm01(arr.mean(axis=2) if arr.ndim == 3 else arr)
    if arr.size == 0:
        return 0.0, 0.0, 0.0
    smooth = cv2.GaussianBlur(arr, (0, 0), sigmaX=block * 0.55, sigmaY=block * 0.55)
    q = np.floor(_norm01(smooth) * levels).astype(np.uint8)
    q = np.clip(q, 0, levels - 1)
    best_area = 0
    best_mask = None
    for level in range(levels):
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats((q == level).astype(np.uint8), 8)
        if count <= 1:
            continue
        idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area > best_area:
            best_area = area
            best_mask = labels == idx
    if best_mask is None or best_area <= 0:
        return 0.0, 0.0, 0.0
    eroded = cv2.erode(best_mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1).astype(bool)
    sample = eroded if eroded.any() else best_mask
    blur = cv2.GaussianBlur(arr, (0, 0), sigmaX=3.0, sigmaY=3.0)
    highpass = float(np.abs(arr[sample] - blur[sample]).mean())
    dx = np.abs(np.diff(arr, axis=1))
    dy = np.abs(np.diff(arr, axis=0))
    xmask = best_mask[:, :-1] & best_mask[:, 1:]
    ymask = best_mask[:-1, :] & best_mask[1:, :]
    gradient = float((dx[xmask].mean() if xmask.any() else 0.0) + (dy[ymask].mean() if ymask.any() else 0.0))
    return float(best_area / arr.size), round(highpass, 6), round(gradient, 6)


def _color_population(rgb: np.ndarray) -> float:
    rgb = np.asarray(rgb, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        return 0.0
    # Approximate how many distinct color zones are materially present.
    bins = np.floor(np.clip(rgb[:, :, :3], 0, 0.999) * 8).astype(np.int16)
    packed = bins[:, :, 0] * 64 + bins[:, :, 1] * 8 + bins[:, :, 2]
    counts = np.bincount(packed.ravel(), minlength=512).astype(np.float32)
    return float((counts > (rgb.shape[0] * rgb.shape[1] * 0.002)).sum())


def _spec_to_rgba(spec: Any, shape: tuple[int, int]) -> np.ndarray | None:
    if spec is None:
        return None
    if isinstance(spec, tuple):
        chans = [np.asarray(c, dtype=np.float32) for c in spec[:3]]
        while len(chans) < 3:
            chans.append(np.zeros(shape, dtype=np.float32))
        arr = np.stack(chans[:3], axis=2)
    else:
        arr = np.asarray(spec)
        if arr.ndim == 2:
            arr = np.repeat(arr[:, :, None], 3, axis=2)
        elif arr.ndim == 3:
            arr = arr[:, :, :3]
        else:
            return None
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    alpha = np.full((shape[0], shape[1], 1), 255, dtype=np.uint8)
    return np.concatenate([arr, alpha], axis=2)


def _m_channel(spec: Any) -> np.ndarray | None:
    if spec is None:
        return None
    if isinstance(spec, tuple):
        return np.asarray(spec[0], dtype=np.float32)
    arr = np.asarray(spec)
    if arr.ndim == 3:
        return arr[:, :, 0].astype(np.float32)
    if arr.ndim == 2:
        return arr.astype(np.float32)
    return None


def _call_mono_spec(spec_fn, shape, mask, seed):
    try:
        return spec_fn(shape, mask, seed, 1.0)
    except TypeError:
        return spec_fn(shape, seed, 1.0, 120, 80)


def _render_item(eng, item_id: str, size: int, seed: int) -> tuple[np.ndarray | None, np.ndarray | None, str, str | None]:
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((size, size, 3), 0.18, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    if item_id in eng.MONOLITHIC_REGISTRY:
        spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[item_id]
        rgb = paint_fn(paint.copy(), shape, mask, seed, 1.0, bb)
        spec = _call_mono_spec(spec_fn, shape, mask, seed)
        return np.clip(rgb[:, :, :3], 0, 1), _spec_to_rgba(spec, shape), "monolithic", None

    if item_id in eng.BASE_REGISTRY:
        entry = eng.BASE_REGISTRY[item_id]
        rgb = paint.copy()
        if entry.get("paint_fn"):
            rgb = entry["paint_fn"](rgb, shape, mask, seed, 1.0, bb)
        spec = None
        if entry.get("base_spec_fn"):
            spec = entry["base_spec_fn"](shape, seed, 1.0, float(entry.get("M", 120)), float(entry.get("R", 80)))
        return np.clip(rgb[:, :, :3], 0, 1), _spec_to_rgba(spec, shape), "base", None

    if item_id in eng.PATTERN_REGISTRY:
        entry = eng.PATTERN_REGISTRY[item_id]
        tex_fn = entry.get("texture_fn")
        if tex_fn is None:
            return None, None, "pattern", "pattern has no texture_fn"
        tex = tex_fn(shape, mask, seed, 1.0)
        pv = _norm01(tex["pattern_val"])
        rgb = np.stack([pv, pv, pv], axis=2)
        spec = np.dstack([
            np.clip(pv * 255, 0, 255),
            np.clip((1 - pv) * 180 + 15, 15, 255),
            np.clip(16 + pv * 140, 16, 255),
            np.full(shape, 255, dtype=np.float32),
        ]).astype(np.uint8)
        return rgb, spec, "pattern", None

    try:
        from engine.spec_patterns import PATTERN_CATALOG
        if item_id in PATTERN_CATALOG:
            pv = PATTERN_CATALOG[item_id](shape, seed, 1.0)
            pv = _norm01(pv)
            rgb = np.stack([pv, pv, pv], axis=2)
            spec = np.dstack([pv * 255, (1 - pv) * 180 + 15, 16 + pv * 140, np.full(shape, 255)]).astype(np.uint8)
            return rgb, spec, "spec_pattern", None
    except Exception:
        pass

    return None, None, "missing", "id not found in base/monolithic/pattern/spec-pattern registries"


@dataclass
class AuditRow:
    id: str
    kind: str
    status: str
    fine_energy: float = 0.0
    residual_energy: float = 0.0
    large_blob_ratio: float = 0.0
    largest_region_ratio: float = 0.0
    largest_region_detail: float = 0.0
    largest_region_gradient: float = 0.0
    spec_largest_region_detail: float = 0.0
    color_population: float = 0.0
    spec_range: float = 0.0
    paint_spec_corr: float | None = None
    flags: list[str] | None = None
    error: str | None = None


def _score(item_id: str, kind: str, rgb: np.ndarray | None, spec: np.ndarray | None, err: str | None) -> AuditRow:
    flags: list[str] = []
    if rgb is None:
        return AuditRow(id=item_id, kind=kind, status="BROKEN", flags=["BROKEN"], error=err)
    lum = rgb[:, :, :3].mean(axis=2)
    fine = _fine_energy(lum)
    residual = _residual_energy(lum)
    blob = _large_blob_ratio(lum)
    region_ratio, region_detail, region_gradient = _largest_region_detail(lum)
    pop = _color_population(rgb)
    spec_range = 0.0
    spec_region_detail = 0.0
    corr = None
    if spec is not None:
        m = spec[:, :, 0].astype(np.float32)
        spec_range = float(m.max() - m.min())
        _spec_region_ratio, spec_region_detail, _spec_region_gradient = _largest_region_detail(m)
        if float(np.std(m)) > 1e-5 and float(np.std(lum)) > 1e-5:
            corr = float(np.corrcoef(_norm01(lum).ravel(), _norm01(m).ravel())[0, 1])
    if fine < 0.010:
        flags.append("LOW_FINE_DETAIL")
    if residual < 0.006:
        flags.append("LOW_PIXEL_RESIDUAL")
    if blob > 0.78 and residual < 0.020:
        flags.append("BLOB_DOMINANT")
    if blob > 0.78 and max(region_detail, spec_region_detail) < 0.040:
        flags.append("INTERNAL_FLAT_REGION")
    if kind in {"monolithic", "base"} and spec is not None and spec_range < 45:
        flags.append("LOW_SPEC_RANGE")
    if pop < 2:
        flags.append("LOW_COLOR_POPULATION")
    return AuditRow(
        id=item_id,
        kind=kind,
        status="WARN" if flags else "OK",
        fine_energy=round(fine, 6),
        residual_energy=round(residual, 6),
        large_blob_ratio=round(blob, 6),
        largest_region_ratio=round(region_ratio, 6),
        largest_region_detail=region_detail,
        largest_region_gradient=region_gradient,
        spec_largest_region_detail=spec_region_detail,
        color_population=round(pop, 2),
        spec_range=round(spec_range, 2),
        paint_spec_corr=None if corr is None else round(corr, 4),
        flags=flags,
        error=err,
    )


def _thumbnail(rgb: np.ndarray | None, size: int) -> Image.Image:
    if rgb is None:
        return Image.new("RGB", (size, size), (32, 0, 0))
    arr = np.clip(rgb[:, :, :3] * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").resize((size, size), Image.Resampling.LANCZOS)


def _spec_thumb(spec: np.ndarray | None, size: int) -> Image.Image:
    if spec is None:
        return Image.new("RGB", (size, size), (12, 12, 12))
    return Image.fromarray(spec[:, :, :3].astype(np.uint8), "RGB").resize((size, size), Image.Resampling.LANCZOS)


def _write_sheet(path: Path, tiles: list[tuple[str, Image.Image]], columns: int = 5, tile: int = 160) -> None:
    if not tiles:
        return
    label_h = 30
    rows = math.ceil(len(tiles) / columns)
    sheet = Image.new("RGB", (columns * tile, rows * (tile + label_h)), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, (label, img) in enumerate(tiles):
        x = (idx % columns) * tile
        y = (idx // columns) * (tile + label_h)
        sheet.paste(img.resize((tile, tile)), (x, y))
        short = label[:26]
        draw.rectangle((x, y + tile, x + tile, y + tile + label_h), fill=(12, 12, 16))
        draw.text((x + 4, y + tile + 8), short, fill=(230, 230, 230), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def _resolve_ids(args, eng) -> tuple[str, list[str]]:
    if args.ids:
        return "explicit", [x.strip() for x in args.ids.split(",") if x.strip()]
    if args.patterns is not None:
        prefix = args.patterns
        ids = [pid for pid in eng.PATTERN_REGISTRY if pid.startswith(prefix)]
        try:
            from engine.spec_patterns import PATTERN_CATALOG
            ids += [pid for pid in PATTERN_CATALOG if pid.startswith(prefix)]
        except Exception:
            pass
        return f"patterns:{prefix}", sorted(set(ids))
    groups = _load_js_special_groups()
    if args.category not in groups:
        lowered = args.category.lower()
        matches = [name for name in groups if lowered in name.lower()]
        if len(matches) == 1:
            return matches[0], list(groups[matches[0]])
        known = ", ".join(sorted(groups)[:20])
        raise SystemExit(f"Unknown category {args.category!r}. First known categories: {known}")
    return args.category, list(groups[args.category])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--category", default="★ COLORSHOXX", help="SPECIAL_GROUPS category name")
    ap.add_argument("--ids", help="Comma-separated explicit ids")
    ap.add_argument("--patterns", nargs="?", const="", help="Audit PATTERN_REGISTRY/spec-pattern ids by prefix")
    ap.add_argument("--size", type=int, default=192)
    ap.add_argument("--seed", type=int, default=7301)
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--columns", type=int, default=5)
    ap.add_argument("--fail-on-warn", action="store_true")
    args = ap.parse_args(argv)

    eng = _quiet_import_engine()
    category, ids = _resolve_ids(args, eng)
    if args.limit and args.limit > 0:
        ids = ids[: args.limit]

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "finish_visual_audit" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[AuditRow] = []
    paint_tiles: list[tuple[str, Image.Image]] = []
    spec_tiles: list[tuple[str, Image.Image]] = []
    vectors: dict[str, np.ndarray] = {}

    for item_id in ids:
        try:
            rgb, spec, kind, err = _render_item(eng, item_id, args.size, args.seed)
        except Exception as ex:
            rgb, spec, kind, err = None, None, "broken", f"{type(ex).__name__}: {ex}"
        row = _score(item_id, kind, rgb, spec, err)
        rows.append(row)
        paint_tiles.append((item_id, _thumbnail(rgb, args.size)))
        spec_tiles.append((item_id, _spec_thumb(spec, args.size)))
        if rgb is not None:
            vectors[item_id] = _norm01(rgb.mean(axis=2)).ravel()

    near_duplicates = []
    keys = list(vectors)
    for i, a_id in enumerate(keys):
        for b_id in keys[i + 1:]:
            a = vectors[a_id]
            b = vectors[b_id]
            if float(np.std(a)) < 1e-6 or float(np.std(b)) < 1e-6:
                continue
            corr = float(np.corrcoef(a, b)[0, 1])
            if abs(corr) > 0.985:
                near_duplicates.append({"a": a_id, "b": b_id, "corr": round(corr, 5)})

    _write_sheet(out_dir / "contact_sheet.png", paint_tiles, columns=args.columns, tile=args.size)
    _write_sheet(out_dir / "spec_sheet.png", spec_tiles, columns=args.columns, tile=args.size)

    payload = {
        "category": category,
        "size": args.size,
        "seed": args.seed,
        "count": len(rows),
        "generated_at": stamp,
        "rows": [asdict(r) for r in rows],
        "near_duplicates": near_duplicates,
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    warn_rows = [r for r in rows if r.flags]
    lines = [
        f"# Finish Visual Audit: {category}",
        "",
        f"- Count: {len(rows)}",
        f"- Warnings: {len(warn_rows)}",
        f"- Near duplicates: {len(near_duplicates)}",
        f"- Contact sheet: `contact_sheet.png`",
        f"- Spec sheet: `spec_sheet.png`",
        "",
        "## Warnings",
        "",
    ]
    for r in warn_rows[:80]:
        lines.append(f"- `{r.id}` ({r.kind}): {', '.join(r.flags or [])}")
    if not warn_rows:
        lines.append("- None")
    if near_duplicates:
        lines += ["", "## Near Duplicates", ""]
        for dup in near_duplicates[:80]:
            lines.append(f"- `{dup['a']}` vs `{dup['b']}` corr={dup['corr']}")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Audit category: {category}")
    print(f"Rendered: {len(rows)}")
    print(f"Warnings: {len(warn_rows)}")
    print(f"Near duplicates: {len(near_duplicates)}")
    print(f"Output: {out_dir}")
    return 1 if args.fail_on_warn and (warn_rows or near_duplicates) else 0


if __name__ == "__main__":
    raise SystemExit(main())
