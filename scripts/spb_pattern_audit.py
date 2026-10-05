#!/usr/bin/env python3
"""Audit visible SPB patterns across primary paint, scale, and Harden masks.

This is the pattern-specific companion to ``spb_visual_workbench.py``. It is
meant for exactly the failure class where a picker pattern exists but does not
show up, scales oddly, or disappears when Base Overlay Pattern Pop/Harden uses
it as a mask.
"""

from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import spb_visual_workbench as wb


@dataclass
class PatternAuditRow:
    id: str
    status: str
    groups: list[str]
    render_ms: float
    mask_std: float
    mask_span: float
    mask_coverage: float
    scale_delta: float
    harden_coverage: float
    harden_span: float
    paint_delta: float
    flags: list[str]
    error: str | None = None
    files: dict[str, str] | None = None


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "pattern"


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _gray_image(arr: np.ndarray) -> Image.Image:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.size == 0:
        return Image.new("L", (1, 1), 0).convert("RGB")
    span = float(arr.max() - arr.min())
    if span > 1e-7:
        arr = (arr - float(arr.min())) / span
    else:
        arr = np.zeros_like(arr, dtype=np.float32)
    return Image.fromarray((np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8), "L").convert("RGB")


def _rgb_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(arr[:, :, :3], 0.0, 1.0) * 255).astype(np.uint8), "RGB")


def _visible_pattern_ids() -> tuple[list[str], dict[str, list[str]], dict[str, Any]]:
    picker = wb._load_picker_groups()
    ids: list[str] = []
    groups_by_id: dict[str, list[str]] = {}
    for group_name, group_ids in (picker.get("pattern", {}) or {}).items():
        if not isinstance(group_ids, list):
            continue
        for item_id in group_ids:
            if not item_id:
                continue
            if item_id not in groups_by_id:
                ids.append(item_id)
                groups_by_id[item_id] = []
            groups_by_id[item_id].append(group_name)
    return ids, groups_by_id, picker.get("meta", {})


def _pattern_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(a, dtype=np.float32) - np.asarray(b, dtype=np.float32))))


def _write_contact_sheet(path: Path, tiles: list[tuple[str, Image.Image]], columns: int, tile: int) -> None:
    if not tiles:
        return
    rows = int(np.ceil(len(tiles) / max(columns, 1)))
    label_h = 26
    sheet = Image.new("RGB", (columns * tile, rows * (tile + label_h)), (16, 17, 22))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, image) in enumerate(tiles):
        x = (index % columns) * tile
        y = (index // columns) * (tile + label_h)
        sheet.paste(image.resize((tile, tile), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle((x, y + tile, x + tile, y + tile + label_h), fill=(8, 10, 14))
        draw.text((x + 4, y + tile + 8), label[:34], fill=(235, 238, 242), font=font)
    sheet.save(path, quality=90)


def _audit_one(eng, item_id: str, groups: list[str], out_dir: Path, size: int, seed: int, scales: list[float]) -> PatternAuditRow:
    from engine.compose import _get_pattern_mask, _harden_overlay_pattern_mask, compose_paint_mod

    item_dir = out_dir / "items" / _safe_name(item_id)
    item_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    start = time.perf_counter()
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    base = np.full((size, size, 3), 0.45, dtype=np.float32)
    try:
        if item_id not in getattr(eng, "PATTERN_REGISTRY", {}):
            raise KeyError("visible picker pattern is missing from engine registry")

        masks: dict[float, np.ndarray] = {}
        for scale in scales:
            pm = _get_pattern_mask(item_id, shape, mask, seed, 1.0, scale=scale)
            if pm is None:
                raise RuntimeError(f"_get_pattern_mask returned None at scale {scale}")
            masks[scale] = np.clip(np.asarray(pm, dtype=np.float32), 0.0, 1.0)
            path = item_dir / f"mask_scale_{str(scale).replace('.', '_')}.jpg"
            _gray_image(masks[scale]).resize((420, 420), Image.Resampling.LANCZOS).save(path, quality=88)
            files[f"mask_{scale:g}"] = _rel(path, out_dir)

        primary_scale = scales[0]
        smallest_scale = scales[-1]
        primary_mask = masks[primary_scale]
        scaled_mask = masks[smallest_scale]
        hard = _harden_overlay_pattern_mask(scaled_mask)
        if hard is None:
            raise RuntimeError("Harden mask returned None")
        hard = np.clip(np.asarray(hard, dtype=np.float32), 0.0, 1.0)

        hard_path = item_dir / "harden_mask.jpg"
        _gray_image(hard).resize((420, 420), Image.Resampling.LANCZOS).save(hard_path, quality=88)
        files["harden_mask"] = _rel(hard_path, out_dir)

        paint = compose_paint_mod("gloss", item_id, base.copy(), shape, mask, seed, 1.0, 1.0, scale=primary_scale)
        paint = np.asarray(paint, dtype=np.float32)[:, :, :3]
        paint_path = item_dir / "primary_paint.jpg"
        _rgb_image(paint).resize((420, 420), Image.Resampling.LANCZOS).save(paint_path, quality=88)
        files["primary_paint"] = _rel(paint_path, out_dir)

        scale_delta = _pattern_diff(primary_mask, scaled_mask)
        paint_delta = _pattern_diff(paint, base)
        mask_span = float(primary_mask.max() - primary_mask.min())
        mask_std = float(primary_mask.std())
        mask_coverage = float((primary_mask > 0.05).mean())
        harden_coverage = float((hard > 0.05).mean())
        harden_span = float(hard.max() - hard.min())

        flags: list[str] = []
        if mask_span < 0.05 or mask_std < 0.01:
            flags.append("raw mask nearly flat")
        if mask_coverage < 0.01:
            flags.append("raw mask nearly empty")
        if scale_delta < 0.01 and abs(primary_scale - smallest_scale) > 0.05:
            flags.append("scale change barely affects mask")
        if harden_span < 0.05 or harden_coverage < 0.01:
            flags.append("Harden mask nearly empty")
        if paint_delta < 0.01:
            flags.append("primary paint nearly invisible")

        return PatternAuditRow(
            id=item_id,
            status="WARN" if flags else "OK",
            groups=groups,
            render_ms=round((time.perf_counter() - start) * 1000.0, 2),
            mask_std=round(mask_std, 6),
            mask_span=round(mask_span, 6),
            mask_coverage=round(mask_coverage, 6),
            scale_delta=round(scale_delta, 6),
            harden_coverage=round(harden_coverage, 6),
            harden_span=round(harden_span, 6),
            paint_delta=round(paint_delta, 6),
            flags=flags,
            files=files,
        )
    except Exception as exc:
        return PatternAuditRow(
            id=item_id,
            status="BROKEN",
            groups=groups,
            render_ms=round((time.perf_counter() - start) * 1000.0, 2),
            mask_std=0.0,
            mask_span=0.0,
            mask_coverage=0.0,
            scale_delta=0.0,
            harden_coverage=0.0,
            harden_span=0.0,
            paint_delta=0.0,
            flags=["pattern audit error"],
            error=f"{type(exc).__name__}: {exc}",
            files=files,
        )


def _render_html(out_dir: Path, rows: list[PatternAuditRow], meta: dict[str, Any], title: str) -> None:
    cards: list[str] = []
    for row in rows:
        item_meta = meta.get(row.id, {}) or {}
        name = html.escape(str(item_meta.get("name", row.id)))
        desc = html.escape(str(item_meta.get("desc", "")))
        flags = ", ".join(row.flags) or "none"
        files = row.files or {}
        figures = []
        for key, label in (
            ("primary_paint", "Primary Paint"),
            ("mask_1", "Mask 1.0"),
            ("mask_0.5", "Mask 0.5"),
            ("mask_0.25", "Mask 0.25"),
            ("harden_mask", "Harden 0.25"),
        ):
            if key in files:
                figures.append(
                    f'<figure><a href="{html.escape(files[key])}"><img src="{html.escape(files[key])}" alt="{html.escape(label)}"></a>'
                    f"<figcaption>{html.escape(label)}</figcaption></figure>"
                )
        cards.append(
            f"""
<article class="card status-{html.escape(row.status.lower())}">
  <h2>{html.escape(row.id)} <span>{html.escape(row.status)}</span></h2>
  <p class="name">{name}</p>
  <p class="desc">{desc}</p>
  <p class="groups">{html.escape(', '.join(row.groups))}</p>
  <p class="metrics">mask std {row.mask_std:.4f} | span {row.mask_span:.4f} | coverage {row.mask_coverage:.3f} | scale delta {row.scale_delta:.4f} | Harden coverage {row.harden_coverage:.3f} | paint delta {row.paint_delta:.4f} | {html.escape(flags)}</p>
  {f'<p class="error">{html.escape(row.error or "")}</p>' if row.error else ''}
  {''.join(figures)}
</article>
"""
        )

    css = """
body { margin: 0; font-family: system-ui, Segoe UI, sans-serif; background: #111318; color: #eef1f4; }
header { position: sticky; top: 0; z-index: 2; background: #171a21; padding: 14px 18px; border-bottom: 1px solid #303743; }
h1 { margin: 0; font-size: 18px; }
.summary { color: #c7d2df; font-size: 12px; margin-top: 6px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 14px; padding: 14px; }
.card { background: #1a1f28; border: 1px solid #333b48; border-radius: 6px; padding: 12px; }
.status-warn { border-color: #947534; }
.status-broken { border-color: #9b403a; }
h2 { margin: 0 0 6px; font-size: 15px; }
h2 span { color: #9aa7b6; font-size: 12px; margin-left: 8px; }
.name { margin: 0 0 5px; font-weight: 650; }
.desc, .groups, .metrics, .error { margin: 0 0 9px; color: #cbd5e1; font-size: 12px; line-height: 1.4; }
.error { color: #ffb3aa; }
figure { display: inline-block; width: 18.8%; margin: 0 1% 10px 0; vertical-align: top; }
figure img { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; background: #07090d; border: 1px solid #303743; }
figcaption { color: #aeb8c5; font-size: 10px; margin-top: 4px; }
a { color: inherit; }
"""
    counts = {
        "ok": sum(1 for row in rows if row.status == "OK"),
        "warn": sum(1 for row in rows if row.status == "WARN"),
        "broken": sum(1 for row in rows if row.status == "BROKEN"),
    }
    doc = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{css}</style></head><body>"
        f"<header><h1>{html.escape(title)}</h1>"
        f"<div class=\"summary\">OK {counts['ok']} | WARN {counts['warn']} | BROKEN {counts['broken']} | total {len(rows)}</div></header>"
        f"<main class=\"grid\">{''.join(cards)}</main></body></html>"
    )
    (out_dir / "index.html").write_text(doc, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", help="Comma-separated pattern IDs. Defaults to all visible picker patterns.")
    parser.add_argument("--size", type=int, default=192)
    parser.add_argument("--seed", type=int, default=7301)
    parser.add_argument("--scales", default="1,0.5,0.25")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--columns", type=int, default=6)
    parser.add_argument("--out-dir")
    args = parser.parse_args(argv)

    if args.size < 32:
        raise SystemExit("--size must be at least 32.")
    scales = [float(x.strip()) for x in args.scales.split(",") if x.strip()]
    if not scales:
        raise SystemExit("--scales must contain at least one numeric scale.")

    visible_ids, groups_by_id, meta = _visible_pattern_ids()
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] if args.ids else visible_ids
    if args.limit > 0:
        ids = ids[: args.limit]

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else REPO / "audit" / "spb_pattern_audit" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    with contextlib.redirect_stdout(io.StringIO()):
        eng = wb._quiet_engine()

    rows = [
        _audit_one(eng, item_id, groups_by_id.get(item_id, []), out_dir, args.size, args.seed, scales)
        for item_id in ids
    ]

    tiles: list[tuple[str, Image.Image]] = []
    for row in rows:
        if row.files and "primary_paint" in row.files:
            with contextlib.suppress(Exception):
                tiles.append((row.id, Image.open(out_dir / row.files["primary_paint"]).convert("RGB")))
    _write_contact_sheet(out_dir / "pattern_paint_contact_sheet.jpg", tiles, args.columns, 180)

    payload = {
        "generated_at": stamp,
        "size": args.size,
        "seed": args.seed,
        "scales": scales,
        "count": len(rows),
        "rows": [asdict(row) for row in rows],
        "metadata": {item_id: meta.get(item_id, {}) for item_id in ids},
    }
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _render_html(out_dir, rows, payload["metadata"], f"SPB Pattern Audit ({args.size}px)")

    broken = [row for row in rows if row.status == "BROKEN"]
    warnings = [row for row in rows if row.status == "WARN"]
    print(f"Pattern audit: {len(rows)} patterns at {args.size}x{args.size}")
    print(f"Warnings: {len(warnings)}")
    print(f"Broken: {len(broken)}")
    print(f"HTML: {out_dir / 'index.html'}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
