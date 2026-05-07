#!/usr/bin/env python3
"""Render SPB catalog items into an inspectable visual workbench.

This is a developer/operator audit tool, not production UI. It renders bases,
monolithics, regular patterns, and spec-pattern overlays at a real canvas size
(2048 by default), writes full paint/spec images, useful zoom crops, metrics,
contact sheets, and a static HTML index.

Examples:
  python scripts/spb_visual_workbench.py --ids candy_apple,copper,green_flake --size 2048
  python scripts/spb_visual_workbench.py --group "Tech & Circuit" --group-type pattern --limit 12
  python scripts/spb_visual_workbench.py --group Optical --group-type spec --size 1024
"""

from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import math
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


for _stream in (sys.stdout, sys.stderr):
    with contextlib.suppress(Exception):
        _stream.reconfigure(encoding="utf-8", errors="replace")


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


@dataclass
class WorkbenchRow:
    id: str
    kind: str
    status: str
    render_ms: float = 0.0
    paint_mean: list[float] | None = None
    paint_luma_std: float = 0.0
    paint_luma_span: float = 0.0
    fine_energy: float = 0.0
    residual_energy: float = 0.0
    block_energy: float = 0.0
    macro_energy: float = 0.0
    micro_macro_ratio: float = 0.0
    color_population: int = 0
    spec_m_range: float = 0.0
    spec_r_range: float = 0.0
    spec_cc_range: float = 0.0
    flags: list[str] | None = None
    error: str | None = None
    files: dict[str, str] | None = None


def _quiet_engine():
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as eng

        eng._ensure_expansions_loaded()
    return eng


def _norm01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _safe_name(item_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", item_id).strip("_") or "item"


def _rgb_image(rgb: np.ndarray) -> Image.Image:
    arr = np.clip(rgb[:, :, :3], 0, 1)
    return Image.fromarray((arr * 255).astype(np.uint8), "RGB")


def _gray_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray((_norm01(arr) * 255).astype(np.uint8), "L").convert("RGB")


def _spec_array(spec: Any, shape: tuple[int, int]) -> np.ndarray | None:
    if spec is None:
        return None
    if isinstance(spec, tuple):
        chans = [np.asarray(c, dtype=np.float32) for c in spec[:3]]
        while len(chans) < 3:
            chans.append(np.zeros(shape, dtype=np.float32))
        arr = np.stack(chans[:3], axis=2)
    else:
        arr = np.asarray(spec, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.repeat(arr[:, :, None], 3, axis=2)
        elif arr.ndim == 3:
            arr = arr[:, :, :3]
        else:
            return None
    return np.clip(arr, 0, 255).astype(np.uint8)


_PATTERN_ASSET_INDEX: dict[str, Path] | None = None


def _asset_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _pattern_asset_index() -> dict[str, Path]:
    global _PATTERN_ASSET_INDEX
    if _PATTERN_ASSET_INDEX is not None:
        return _PATTERN_ASSET_INDEX

    index: dict[str, Path] = {}
    roots = [
        REPO / "assets" / "patterns",
        REPO / "basespatterns_examples" / "patternexamples",
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                index.setdefault(path.name.lower(), path)
                index.setdefault(path.stem.lower(), path)
                index.setdefault(_asset_key(path.name), path)
                index.setdefault(_asset_key(path.stem), path)
    _PATTERN_ASSET_INDEX = index
    return index


def _resolve_pattern_asset(item_id: str, meta: dict[str, Any] | None) -> Path | None:
    meta = meta or {}
    swatch_image = str(meta.get("swatch_image") or "").strip()
    if swatch_image:
        candidate = REPO / swatch_image.lstrip("/\\")
        if candidate.exists():
            return candidate

    index = _pattern_asset_index()
    lowered = item_id.lower()
    name = str(meta.get("name") or "").strip()
    candidates = [
        lowered,
        lowered.replace("-", "_"),
        lowered.replace("_", "-"),
        _asset_key(item_id),
    ]
    if name:
        candidates.extend([name.lower(), _asset_key(name)])
    for key in candidates:
        if key in index:
            return index[key]
        for suffix in (".png", ".jpg", ".jpeg", ".webp"):
            if f"{key}{suffix}" in index:
                return index[f"{key}{suffix}"]
    return None


def _render_image_pattern_asset(path: Path, size: int) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    image = ImageOps.exif_transpose(image)
    image = ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    return np.asarray(image, dtype=np.float32) / 255.0


def _call_mono_spec(spec_fn, shape: tuple[int, int], mask: np.ndarray, seed: int):
    try:
        return spec_fn(shape, mask, seed, 1.0)
    except TypeError:
        return spec_fn(shape, seed, 1.0, 120, 80)


def _render_item(eng, item_id: str, kind: str, size: int, seed: int, meta: dict[str, Any] | None = None):
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((size, size, 3), 0.18, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    if kind in {"auto", "base"} and item_id in eng.BASE_REGISTRY:
        entry = eng.BASE_REGISTRY[item_id]
        rgb = paint.copy()
        if entry.get("paint_fn"):
            rgb = entry["paint_fn"](rgb, shape, mask, seed, 1.0, bb)
        spec = None
        if entry.get("base_spec_fn"):
            spec = entry["base_spec_fn"](shape, seed, 1.0, float(entry.get("M", 120)), float(entry.get("R", 80)))
        return np.clip(rgb[:, :, :3], 0, 1), _spec_array(spec, shape), "base"

    if kind in {"auto", "monolithic", "special"} and item_id in eng.MONOLITHIC_REGISTRY:
        entry = eng.MONOLITHIC_REGISTRY[item_id]
        spec_fn, paint_fn = entry[:2]
        rgb = paint_fn(paint.copy(), shape, mask, seed, 1.0, bb)
        spec = _call_mono_spec(spec_fn, shape, mask, seed)
        return np.clip(rgb[:, :, :3], 0, 1), _spec_array(spec, shape), "monolithic"

    if kind in {"auto", "monolithic", "special"} and item_id.startswith(("grad_", "gradm_", "grad3_", "ghostg_", "mc_")):
        meta = meta or {}
        c1 = meta.get("swatch")
        c2 = meta.get("swatch2")
        c3 = meta.get("swatch3")
        if c1 and c2:
            from engine.render import render_generic_finish

            zone = {"finish_colors": {"c1": c1, "c2": c2, "c3": c3, "ghost": meta.get("ghost")}}
            spec, rgb = render_generic_finish(item_id, zone, paint.copy(), shape, mask, seed, 1.0, 1.0, bb, rotation=0)
            return np.clip(rgb[:, :, :3], 0, 1), _spec_array(spec, shape), "runtime_generic_monolithic"

    if kind in {"auto", "pattern"} and item_id in eng.PATTERN_REGISTRY:
        entry = eng.PATTERN_REGISTRY[item_id]
        asset = _resolve_pattern_asset(item_id, meta)
        if asset is not None:
            rgb = _render_image_pattern_asset(asset, size)
            pv = _norm01(rgb.mean(axis=2))
            spec = np.dstack([
                np.clip(pv * 255, 0, 255),
                np.clip((1.0 - pv) * 180 + 15, 15, 255),
                np.clip(16 + pv * 140, 16, 255),
            ]).astype(np.uint8)
            return rgb, spec, "image_pattern"
        tex_fn = entry.get("texture_fn")
        if tex_fn is None:
            raise ValueError("pattern has no texture_fn and no image asset")
        tex = tex_fn(shape, mask, seed, 1.0)
        pv = _norm01(tex["pattern_val"])
        rgb = np.dstack([pv, pv, pv]).astype(np.float32)
        spec = np.dstack([
            np.clip(pv * 255, 0, 255),
            np.clip((1.0 - pv) * 180 + 15, 15, 255),
            np.clip(16 + pv * 140, 16, 255),
        ]).astype(np.uint8)
        return rgb, spec, "pattern"

    if kind in {"auto", "spec", "spec-pattern", "spec_pattern"}:
        from engine.spec_patterns import PATTERN_CATALOG

        if item_id in PATTERN_CATALOG:
            pv = _norm01(PATTERN_CATALOG[item_id](shape, seed, 1.0))
            rgb = np.dstack([pv, pv, pv]).astype(np.float32)
            spec = np.dstack([
                np.clip(pv * 255, 0, 255),
                np.clip((1.0 - pv) * 180 + 15, 15, 255),
                np.clip(16 + pv * 140, 16, 255),
            ]).astype(np.uint8)
            return rgb, spec, "spec_pattern"

    raise KeyError(f"{item_id!r} not found for kind {kind!r}")


def _fine_energy(luma: np.ndarray) -> float:
    dx = float(np.abs(np.diff(luma, axis=1)).mean()) if luma.shape[1] > 1 else 0.0
    dy = float(np.abs(np.diff(luma, axis=0)).mean()) if luma.shape[0] > 1 else 0.0
    return dx + dy


def _residual_energy(luma: np.ndarray, block: int = 8) -> float:
    h, w = luma.shape
    hh = h - h % block
    ww = w - w % block
    if hh < block or ww < block:
        return 0.0
    cropped = luma[:hh, :ww]
    coarse = cropped.reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
    up = np.repeat(np.repeat(coarse, block, axis=0), block, axis=1)
    return float(np.abs(cropped - up).mean())


def _block_energy(luma: np.ndarray, block: int = 16) -> float:
    h, w = luma.shape
    hh = h - h % block
    ww = w - w % block
    if hh < block * 2 or ww < block * 2:
        return 0.0
    cropped = luma[:hh, :ww]
    coarse = cropped.reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
    edge_x = np.abs(np.diff(coarse, axis=1)).mean() if coarse.shape[1] > 1 else 0.0
    edge_y = np.abs(np.diff(coarse, axis=0)).mean() if coarse.shape[0] > 1 else 0.0
    return float(edge_x + edge_y)


def _macro_energy(luma: np.ndarray) -> float:
    """How much of the finish is carried by large 2048-scale forms."""
    if luma.size == 0:
        return 0.0
    h, w = luma.shape
    sigma = max(10.0, min(h, w) / 42.0)
    macro = cv2.GaussianBlur(luma.astype(np.float32), (0, 0), sigmaX=sigma, sigmaY=sigma)
    return float(macro.std())


def _micro_macro_ratio(residual: float, macro: float) -> float:
    """Low values mean big forms dominate and fine detail is not carrying enough."""
    return float(residual / max(macro, 1e-6))


def _color_population(rgb: np.ndarray) -> int:
    bins = np.floor(np.clip(rgb[:, :, :3], 0, 0.999) * 8).astype(np.int16)
    packed = bins[:, :, 0] * 64 + bins[:, :, 1] * 8 + bins[:, :, 2]
    counts = np.bincount(packed.ravel(), minlength=512)
    return int((counts > (rgb.shape[0] * rgb.shape[1] * 0.002)).sum())


def _best_detail_box(luma: np.ndarray, crop: int) -> tuple[int, int, int, int]:
    h, w = luma.shape
    crop = min(crop, h, w)
    if crop <= 0:
        return (0, 0, w, h)
    blur = cv2.GaussianBlur(luma.astype(np.float32), (0, 0), sigmaX=3.0, sigmaY=3.0)
    detail = np.abs(luma - blur)
    stride = max(1, crop // 3)
    best = (0.0, 0, 0)
    for y in range(0, h - crop + 1, stride):
        for x in range(0, w - crop + 1, stride):
            score = float(detail[y : y + crop, x : x + crop].mean())
            if score > best[0]:
                best = (score, x, y)
    _, x, y = best
    return (x, y, x + crop, y + crop)


def _write_contact_sheet(path: Path, tiles: list[tuple[str, Image.Image]], columns: int, tile: int) -> None:
    if not tiles:
        return
    label_h = 28
    rows = math.ceil(len(tiles) / columns)
    sheet = Image.new("RGB", (columns * tile, rows * (tile + label_h)), (16, 16, 20))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, (label, image) in enumerate(tiles):
        x = (idx % columns) * tile
        y = (idx // columns) * (tile + label_h)
        sheet.paste(image.resize((tile, tile), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle((x, y + tile, x + tile, y + tile + label_h), fill=(8, 8, 12))
        draw.text((x + 4, y + tile + 8), label[:32], fill=(235, 235, 235), font=font)
    sheet.save(path)


def _load_picker_groups() -> dict[str, Any]:
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
function meta(arrName) {
  return Object.fromEntries((vm.runInContext(arrName, ctx) || []).filter(x => x && x.id).map(x => [x.id, x]));
}
console.log(JSON.stringify({
  base: vm.runInContext('BASE_GROUPS', ctx) || {},
  pattern: vm.runInContext('PATTERN_GROUPS', ctx) || {},
  special: vm.runInContext('SPECIAL_GROUPS', ctx) || {},
  spec: vm.runInContext('SPEC_PATTERN_GROUPS', ctx) || {},
  meta: Object.assign({}, meta('BASES'), meta('PATTERNS'), meta('MONOLITHICS'), meta('SPEC_PATTERNS'))
}));
"""
    out = subprocess.check_output(["node", "-e", script], cwd=REPO, text=True, encoding="utf-8")
    return json.loads(out)


def _resolve_ids(args: argparse.Namespace) -> tuple[list[str], dict[str, Any], str, str]:
    picker = _load_picker_groups()
    if args.ids:
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        return ids, picker.get("meta", {}), "explicit", args.kind
    groups = picker.get(args.group_type, {})
    if args.group not in groups:
        needle = args.group.lower()
        matches = [name for name in groups if needle in name.lower()]
        if len(matches) == 1:
            args.group = matches[0]
        else:
            known = ", ".join(sorted(groups)[:20])
            raise SystemExit(f"Unknown {args.group_type} group {args.group!r}. First known groups: {known}")
    kind = args.kind if args.kind != "auto" else args.group_type
    if kind == "special":
        kind = "monolithic"
    if kind == "spec":
        kind = "spec-pattern"
    return list(groups[args.group]), picker.get("meta", {}), args.group, kind


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _render_html(out_dir: Path, title: str, rows: list[WorkbenchRow], metadata: dict[str, Any] | None = None) -> None:
    metadata = metadata or {}
    cards = []
    for row in rows:
        files = row.files or {}
        flags = ", ".join(row.flags or []) or "none"
        desc = html.escape(str(row.error or ""))
        item_meta = metadata.get(row.id, {}) or {}
        name = html.escape(str(item_meta.get("name", row.id)))
        expected = html.escape(str(item_meta.get("desc", "")))
        card = [
            f'<article class="card status-{html.escape(row.status.lower())}" '
            f'data-id="{html.escape(row.id)}" data-kind="{html.escape(row.kind)}" '
            f'data-name="{name}">'
        ]
        card.append(f"<h2>{html.escape(row.id)} <span>{html.escape(row.kind)}</span></h2>")
        if name and name != html.escape(row.id):
            card.append(f'<p class="name">{name}</p>')
        if expected:
            card.append(f'<p class="expected"><strong>Supposed to look like:</strong> {expected}</p>')
        card.append(
            "<p class=\"metrics\">"
            f"render {row.render_ms:.1f}ms | luma std {row.paint_luma_std:.4f} | "
            f"fine {row.fine_energy:.4f} | residual {row.residual_energy:.4f} | "
            f"block {row.block_energy:.4f} | macro {row.macro_energy:.4f} | "
            f"micro/macro {row.micro_macro_ratio:.3f} | colors {row.color_population} | "
            f"M range {row.spec_m_range:.1f} | flags {html.escape(flags)}"
            "</p>"
        )
        if desc:
            card.append(f'<p class="error">{desc}</p>')
        card.append(
            f"""
<section class="review" data-review-for="{html.escape(row.id)}">
  <div class="review-row">
    <label><input type="radio" name="decision-{html.escape(row.id)}" value="pass"> PASS</label>
    <label><input type="radio" name="decision-{html.escape(row.id)}" value="fail"> FAIL</label>
    <button type="button" class="review-clear">Clear</button>
  </div>
  <div class="fail-tags">
    <label><input type="checkbox" value="wrong-description"> wrong description</label>
    <label><input type="checkbox" value="not-unique"> not unique/repeats</label>
    <label><input type="checkbox" value="too-blobby"> too blobby</label>
    <label><input type="checkbox" value="too-coarse"> too coarse/big</label>
    <label><input type="checkbox" value="too-flat"> too flat</label>
    <label><input type="checkbox" value="paint-wrong"> paint wrong</label>
    <label><input type="checkbox" value="spec-wrong"> spec wrong</label>
    <label><input type="checkbox" value="spec-repeats"> spec repeats</label>
    <label><input type="checkbox" value="broken-render"> broken/render issue</label>
    <label><input type="checkbox" value="render-time-too-long"> render time too long</label>
    <label><input type="checkbox" value="too-busy"> too busy</label>
    <label><input type="checkbox" value="needs-finer-detail"> needs finer detail</label>
    <label><input type="checkbox" value="color-issue"> color issue</label>
  </div>
  <textarea class="review-note" placeholder="PASS notes: what works / why you like it. FAIL notes: what is wrong and what it should do instead."></textarea>
</section>
"""
        )
        for key, label in (
            ("paint_preview", "Paint"),
            ("spec_preview", "Spec"),
            ("detail_crop", "Detail Crop"),
            ("center_crop", "Center Crop"),
            ("luma_preview", "Luma"),
        ):
            if key in files:
                full_key = "paint_full" if key == "paint_preview" else "spec_full" if key == "spec_preview" else key
                href = files.get(full_key, files[key])
                card.append(
                    f'<figure><a href="{html.escape(href)}"><img src="{html.escape(files[key])}" alt="{html.escape(label)}"></a>'
                    f"<figcaption>{html.escape(label)}</figcaption></figure>"
                )
        card.append("</article>")
        cards.append("\n".join(card))

    css = """
body { margin: 0; font-family: system-ui, Segoe UI, sans-serif; background: #111318; color: #eef1f4; }
header { position: sticky; top: 0; z-index: 2; background: #171a21; padding: 14px 18px; border-bottom: 1px solid #303743; }
h1 { margin: 0; font-size: 18px; font-weight: 700; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; padding: 14px; }
.card { background: #1a1f28; border: 1px solid #333b48; border-radius: 6px; padding: 12px; }
.card h2 { margin: 0 0 8px; font-size: 15px; }
.card h2 span { color: #9aa7b6; font-size: 12px; font-weight: 500; margin-left: 8px; }
.name { margin: -4px 0 7px; color: #eef1f4; font-size: 13px; font-weight: 650; }
.expected { margin: 0 0 10px; color: #d5dee8; font-size: 12px; line-height: 1.45; }
.metrics { margin: 0 0 10px; color: #c6d0dc; font-size: 12px; line-height: 1.45; }
.error { color: #ffb3aa; font-size: 12px; }
figure { display: inline-block; width: 31%; margin: 0 1% 10px 0; vertical-align: top; }
figure img { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; background: #08090c; border: 1px solid #303743; }
figcaption { color: #aeb8c5; font-size: 11px; margin-top: 4px; }
.status-warn { border-color: #826b28; }
.status-broken { border-color: #8b3a34; }
.review { margin: 10px 0 12px; padding: 10px; border: 1px solid #344052; border-radius: 6px; background: #131821; }
.review-row { display: flex; gap: 12px; align-items: center; margin-bottom: 8px; color: #e7eef7; font-size: 12px; font-weight: 700; }
.review-row label { display: inline-flex; align-items: center; gap: 5px; }
.review-clear, .review-toolbar button { background: #253044; color: #eef3f8; border: 1px solid #43506a; border-radius: 4px; padding: 5px 8px; cursor: pointer; }
.review-clear:hover, .review-toolbar button:hover { background: #31405a; }
.fail-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.fail-tags label { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: #c8d3df; border: 1px solid #334052; border-radius: 4px; padding: 4px 6px; background: #10151d; }
.fail-tags.is-disabled { opacity: 0.45; }
.review-note { width: 100%; min-height: 64px; box-sizing: border-box; background: #0e1218; color: #edf2f7; border: 1px solid #3a4658; border-radius: 4px; padding: 8px; resize: vertical; }
.review-toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 10px 18px; border-top: 1px solid #27303d; background: #141922; }
.review-summary { color: #c7d2df; font-size: 12px; margin-left: auto; }
.review-export { width: calc(100% - 36px); min-height: 110px; margin: 0 18px 14px; box-sizing: border-box; background: #0e1218; color: #edf2f7; border: 1px solid #3a4658; border-radius: 4px; padding: 8px; }
a { color: inherit; }
"""
    js = """
const REVIEW_VERSION = 1;
const reviewKey = "spb-workbench-review:" + location.pathname;
const cards = Array.from(document.querySelectorAll(".card"));
const exportBox = document.getElementById("review-export");
const summary = document.getElementById("review-summary");

function emptyState() {
  return { version: REVIEW_VERSION, updatedAt: null, source: location.href, items: {} };
}

function loadState() {
  try {
    return Object.assign(emptyState(), JSON.parse(localStorage.getItem(reviewKey) || "{}"));
  } catch (_) {
    return emptyState();
  }
}

let state = loadState();

function itemState(id) {
  if (!state.items[id]) state.items[id] = { decision: "", reasons: [], comment: "" };
  return state.items[id];
}

function saveState() {
  state.updatedAt = new Date().toISOString();
  localStorage.setItem(reviewKey, JSON.stringify(state));
  updateSummary();
}

function setFailTagsEnabled(card, enabled) {
  const wrap = card.querySelector(".fail-tags");
  if (!wrap) return;
  wrap.classList.toggle("is-disabled", !enabled);
  wrap.querySelectorAll("input").forEach((input) => { input.disabled = !enabled; });
}

function applyStateToCard(card) {
  const id = card.dataset.id;
  const current = itemState(id);
  card.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.checked = input.value === current.decision;
  });
  card.querySelectorAll('.fail-tags input[type="checkbox"]').forEach((input) => {
    input.checked = current.reasons.includes(input.value);
  });
  const note = card.querySelector(".review-note");
  if (note) note.value = current.comment || "";
  setFailTagsEnabled(card, current.decision === "fail");
}

function collect() {
  const items = cards.map((card, index) => {
    const id = card.dataset.id;
    const current = itemState(id);
    return {
      index: index + 1,
      id,
      name: card.dataset.name || id,
      kind: card.dataset.kind || "",
      decision: current.decision || "",
      failReasons: current.decision === "fail" ? current.reasons : [],
      comment: current.comment || ""
    };
  });
  return {
    version: REVIEW_VERSION,
    source: location.href,
    title: document.title,
    exportedAt: new Date().toISOString(),
    counts: {
      total: items.length,
      pass: items.filter((item) => item.decision === "pass").length,
      fail: items.filter((item) => item.decision === "fail").length,
      unset: items.filter((item) => !item.decision).length,
      commented: items.filter((item) => item.comment.trim()).length
    },
    items
  };
}

function toMarkdown(payload) {
  const lines = [
    "# " + payload.title,
    "",
    "- Source: " + payload.source,
    "- Exported: " + payload.exportedAt,
    "- Total: " + payload.counts.total,
    "- PASS: " + payload.counts.pass,
    "- FAIL: " + payload.counts.fail,
    "- Unset: " + payload.counts.unset,
    "- Commented: " + payload.counts.commented,
    ""
  ];
  payload.items.forEach((item) => {
    if (!item.decision && !item.comment.trim()) return;
    lines.push("## " + item.index + ". " + item.id);
    lines.push("");
    lines.push("- Name: " + item.name);
    lines.push("- Kind: " + item.kind);
    lines.push("- Decision: " + (item.decision || "unset"));
    if (item.failReasons.length) lines.push("- Fail reasons: " + item.failReasons.join(", "));
    if (item.comment.trim()) lines.push("- Comment: " + item.comment.trim().replace(/\\n/g, "\\n  "));
    lines.push("");
  });
  return lines.join("\\n");
}

function showExport(format) {
  const payload = collect();
  exportBox.value = format === "md" ? toMarkdown(payload) : JSON.stringify(payload, null, 2);
  exportBox.focus();
  exportBox.select();
}

function download(filename, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function updateSummary() {
  const payload = collect();
  summary.textContent = `PASS ${payload.counts.pass} | FAIL ${payload.counts.fail} | unset ${payload.counts.unset} | comments ${payload.counts.commented}`;
}

cards.forEach((card) => {
  const id = card.dataset.id;
  applyStateToCard(card);
  card.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.addEventListener("change", () => {
      const current = itemState(id);
      current.decision = input.value;
      if (input.value !== "fail") current.reasons = [];
      applyStateToCard(card);
      saveState();
    });
  });
  card.querySelectorAll('.fail-tags input[type="checkbox"]').forEach((input) => {
    input.addEventListener("change", () => {
      const current = itemState(id);
      const reasons = new Set(current.reasons || []);
      if (input.checked) reasons.add(input.value);
      else reasons.delete(input.value);
      current.reasons = Array.from(reasons).sort();
      saveState();
    });
  });
  const note = card.querySelector(".review-note");
  if (note) {
    note.addEventListener("input", () => {
      itemState(id).comment = note.value;
      saveState();
    });
  }
  const clear = card.querySelector(".review-clear");
  if (clear) {
    clear.addEventListener("click", () => {
      state.items[id] = { decision: "", reasons: [], comment: "" };
      applyStateToCard(card);
      saveState();
    });
  }
});

document.getElementById("review-show-json").addEventListener("click", () => showExport("json"));
document.getElementById("review-show-md").addEventListener("click", () => showExport("md"));
document.getElementById("review-copy-json").addEventListener("click", async () => {
  showExport("json");
  try { await navigator.clipboard.writeText(exportBox.value); } catch (_) {}
});
document.getElementById("review-download-json").addEventListener("click", () => {
  const payload = collect();
  download("owner_review_decisions.json", JSON.stringify(payload, null, 2), "application/json");
});
document.getElementById("review-download-md").addEventListener("click", () => {
  download("owner_review_decisions.md", toMarkdown(collect()), "text/markdown");
});
document.getElementById("review-mark-unset-pass").addEventListener("click", () => {
  cards.forEach((card) => {
    const id = card.dataset.id;
    const current = itemState(id);
    if (!current.decision) current.decision = "pass";
    applyStateToCard(card);
  });
  saveState();
});
document.getElementById("review-clear-all").addEventListener("click", () => {
  if (!confirm("Clear all PASS/FAIL decisions and comments for this page?")) return;
  state = emptyState();
  localStorage.removeItem(reviewKey);
  cards.forEach(applyStateToCard);
  saveState();
});
updateSummary();
"""
    html_doc = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{css}</style></head><body>"
        f"<header><h1>{html.escape(title)}</h1></header>"
        "<section class=\"review-toolbar\">"
        "<button type=\"button\" id=\"review-show-json\">Show JSON</button>"
        "<button type=\"button\" id=\"review-show-md\">Show Markdown</button>"
        "<button type=\"button\" id=\"review-copy-json\">Copy JSON</button>"
        "<button type=\"button\" id=\"review-download-json\">Download JSON</button>"
        "<button type=\"button\" id=\"review-download-md\">Download Markdown</button>"
        "<button type=\"button\" id=\"review-mark-unset-pass\">Mark Unset PASS</button>"
        "<button type=\"button\" id=\"review-clear-all\">Clear All</button>"
        "<span class=\"review-summary\" id=\"review-summary\"></span>"
        "</section>"
        "<textarea id=\"review-export\" class=\"review-export\" placeholder=\"Review export appears here when you click Show JSON or Show Markdown.\" readonly></textarea>"
        f"<main class=\"grid\">{''.join(cards)}</main><script>{js}</script></body></html>"
    )
    (out_dir / "index.html").write_text(html_doc, encoding="utf-8")


def _process_item(
    eng,
    item_id: str,
    kind: str,
    size: int,
    seed: int,
    out_dir: Path,
    meta: dict[str, Any] | None = None,
) -> WorkbenchRow:
    item_dir = out_dir / "items" / _safe_name(item_id)
    item_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    flags: list[str] = []
    start = time.perf_counter()
    try:
        rgb, spec, actual_kind = _render_item(eng, item_id, kind, size, seed, meta)
        render_ms = (time.perf_counter() - start) * 1000.0
        luma = rgb[:, :, :3].mean(axis=2).astype(np.float32)

        paint_full = item_dir / "paint_full.png"
        paint_preview = item_dir / "paint_preview.jpg"
        luma_preview = item_dir / "luma_preview.jpg"
        center_crop = item_dir / "center_crop.png"
        detail_crop = item_dir / "detail_crop.png"
        paint_img = _rgb_image(rgb)
        paint_img.save(paint_full)
        paint_img.resize((420, 420), Image.Resampling.LANCZOS).save(paint_preview, quality=88)
        _gray_image(luma).resize((420, 420), Image.Resampling.LANCZOS).save(luma_preview, quality=88)

        crop = min(512, size)
        cx = max(0, (size - crop) // 2)
        cy = max(0, (size - crop) // 2)
        paint_img.crop((cx, cy, cx + crop, cy + crop)).save(center_crop)
        paint_img.crop(_best_detail_box(luma, crop)).save(detail_crop)

        files.update({
            "paint_full": _relative(paint_full, out_dir),
            "paint_preview": _relative(paint_preview, out_dir),
            "luma_preview": _relative(luma_preview, out_dir),
            "center_crop": _relative(center_crop, out_dir),
            "detail_crop": _relative(detail_crop, out_dir),
        })
        if actual_kind == "image_pattern":
            asset = _resolve_pattern_asset(item_id, meta)
            if asset is not None:
                files["source_asset"] = _relative(asset, REPO)

        spec_m_range = spec_r_range = spec_cc_range = 0.0
        if spec is not None:
            spec_img = Image.fromarray(spec[:, :, :3], "RGB")
            spec_full = item_dir / "spec_full.png"
            spec_preview = item_dir / "spec_preview.jpg"
            spec_img.save(spec_full)
            spec_img.resize((420, 420), Image.Resampling.LANCZOS).save(spec_preview, quality=88)
            files["spec_full"] = _relative(spec_full, out_dir)
            files["spec_preview"] = _relative(spec_preview, out_dir)
            spec_m_range = float(spec[:, :, 0].max() - spec[:, :, 0].min())
            spec_r_range = float(spec[:, :, 1].max() - spec[:, :, 1].min())
            spec_cc_range = float(spec[:, :, 2].max() - spec[:, :, 2].min())

        fine = _fine_energy(luma)
        residual = _residual_energy(luma)
        block = _block_energy(luma)
        macro = _macro_energy(luma)
        micro_macro = _micro_macro_ratio(residual, macro)
        luma_span = float(np.percentile(luma, 99) - np.percentile(luma, 1))
        color_pop = _color_population(rgb)
        if fine < 0.004 and residual < 0.003:
            flags.append("low detail")
        if residual < 0.012 and actual_kind not in {"image_pattern"}:
            flags.append("needs 2048 micro-detail")
        if macro > 0.045 and micro_macro < 0.36 and actual_kind not in {"image_pattern"}:
            flags.append("macro-dominated/too-large")
        if block > 0.20 and residual < 0.030:
            flags.append("blocky/coarse field")
        if color_pop < 2:
            flags.append("low color population")
        if spec is not None and spec_m_range < 8:
            flags.append("flat metallic channel")

        return WorkbenchRow(
            id=item_id,
            kind=actual_kind,
            status="WARN" if flags else "OK",
            render_ms=round(render_ms, 2),
            paint_mean=[round(float(x), 4) for x in rgb.reshape(-1, 3).mean(axis=0)],
            paint_luma_std=round(float(luma.std()), 6),
            paint_luma_span=round(luma_span, 6),
            fine_energy=round(fine, 6),
            residual_energy=round(residual, 6),
            block_energy=round(block, 6),
            macro_energy=round(macro, 6),
            micro_macro_ratio=round(micro_macro, 6),
            color_population=color_pop,
            spec_m_range=round(spec_m_range, 3),
            spec_r_range=round(spec_r_range, 3),
            spec_cc_range=round(spec_cc_range, 3),
            flags=flags,
            files=files,
        )
    except Exception as ex:
        return WorkbenchRow(
            id=item_id,
            kind=kind,
            status="BROKEN",
            render_ms=round((time.perf_counter() - start) * 1000.0, 2),
            flags=["render error"],
            error=f"{type(ex).__name__}: {ex}",
            files=files,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", help="Comma-separated item IDs. Use --kind to disambiguate collisions.")
    parser.add_argument("--kind", default="auto", choices=["auto", "base", "monolithic", "special", "pattern", "spec", "spec-pattern", "spec_pattern"])
    parser.add_argument("--group", help="Picker group name, e.g. Metallic Standard, Tech & Circuit, Optical.")
    parser.add_argument("--group-type", default="base", choices=["base", "pattern", "special", "spec"])
    parser.add_argument("--size", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=7301)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out-dir")
    parser.add_argument("--columns", type=int, default=4)
    args = parser.parse_args(argv)

    if not args.ids and not args.group:
        raise SystemExit("Provide --ids or --group.")
    if args.size < 32:
        raise SystemExit("--size must be at least 32.")

    ids, meta, label, render_kind = _resolve_ids(args)
    if args.limit > 0:
        ids = ids[: args.limit]

    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe_label = _safe_name(label)
    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "spb_visual_workbench" / f"{stamp}-{safe_label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    eng = _quiet_engine()
    rows: list[WorkbenchRow] = []
    paint_tiles: list[tuple[str, Image.Image]] = []
    spec_tiles: list[tuple[str, Image.Image]] = []
    for item_id in ids:
        row = _process_item(eng, item_id, render_kind, args.size, args.seed, out_dir, meta.get(item_id, {}))
        rows.append(row)
        if row.files and "paint_preview" in row.files:
            paint_tiles.append((item_id, Image.open(out_dir / row.files["paint_preview"]).convert("RGB")))
        if row.files and "spec_preview" in row.files:
            spec_tiles.append((item_id, Image.open(out_dir / row.files["spec_preview"]).convert("RGB")))

    sheet_tile = 240
    _write_contact_sheet(out_dir / "paint_contact_sheet.jpg", paint_tiles, args.columns, sheet_tile)
    _write_contact_sheet(out_dir / "spec_contact_sheet.jpg", spec_tiles, args.columns, sheet_tile)

    payload = {
        "label": label,
        "kind": render_kind,
        "size": args.size,
        "seed": args.seed,
        "count": len(rows),
        "generated_at": stamp,
        "rows": [asdict(row) for row in rows],
        "metadata": {item_id: meta.get(item_id, {}) for item_id in ids},
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _render_html(out_dir, f"SPB Visual Workbench: {label} ({args.size}px)", rows, payload["metadata"])

    broken = [row for row in rows if row.status == "BROKEN"]
    warnings = [row for row in rows if row.status == "WARN"]
    print(f"Visual workbench: {label}")
    print(f"Rendered: {len(rows)} at {args.size}x{args.size}")
    print(f"Warnings: {len(warnings)}")
    print(f"Broken: {len(broken)}")
    print(f"HTML: {out_dir / 'index.html'}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
