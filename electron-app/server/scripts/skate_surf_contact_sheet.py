#!/usr/bin/env python3
"""Build a single PNG contact sheet for ``PATTERN_GROUPS["Skate & Surf"]``.

Each cell: top = pattern mask (what SPB uses as the modulation field), bottom =
gloss base + pattern at intensity 1.0 (quick read of “on car” feel).

Run from repo root:
  python scripts/skate_surf_contact_sheet.py
  python scripts/skate_surf_contact_sheet.py --out audit/my_sheet.png --columns 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pattern_inventory import FINISH_JS, _parse_pattern_groups


def _norm_gray(arr: np.ndarray) -> Image.Image:
    a = np.asarray(arr, dtype=np.float32)
    if a.size == 0:
        return Image.new("RGB", (1, 1), (40, 44, 52))
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < 1e-8:
        u8 = np.zeros_like(a, dtype=np.uint8)
    else:
        u8 = (np.clip((a - lo) / (hi - lo), 0.0, 1.0) * 255.0).astype(np.uint8)
    return Image.fromarray(u8, "L").convert("RGB")


def _write_sheet(
    path: Path,
    tiles: list[tuple[str, Image.Image]],
    columns: int,
    cell: int,
    label_h: int,
) -> None:
    if not tiles:
        return
    cols = max(1, columns)
    rows = int(np.ceil(len(tiles) / cols))
    w = cols * cell
    h = rows * (cell + label_h)
    sheet = Image.new("RGB", (w, h), (14, 16, 20))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    for i, (label, img) in enumerate(tiles):
        cx, cy = i % cols, i // cols
        x, y = cx * cell, cy * (cell + label_h)
        sheet.paste(img.resize((cell, cell), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle((x, y + cell, x + cell, y + cell + label_h), fill=(8, 10, 14))
        draw.text((x + 6, y + cell + 6), label[:42], fill=(230, 234, 240), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=93)
    print(f"Wrote {path} ({len(tiles)} patterns, {cols} columns, cell={cell}px)")


def _cell_image(
    mask_rgb: Image.Image,
    paint_rgb: Image.Image | None,
    cell: int,
    label_h: int,
) -> Image.Image:
    inner = cell
    if paint_rgb is None:
        return mask_rgb.resize((inner, inner), Image.Resampling.LANCZOS)
    mask_h = inner // 2
    paint_h = inner - mask_h
    out = Image.new("RGB", (inner, inner), (20, 22, 28))
    out.paste(mask_rgb.resize((inner, mask_h), Image.Resampling.LANCZOS), (0, 0))
    out.paste(paint_rgb.resize((inner, paint_h), Image.Resampling.LANCZOS), (0, mask_h))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Skate & Surf pattern contact sheet")
    ap.add_argument(
        "--category",
        default="Skate & Surf",
        help='PATTERN_GROUPS key (default: "Skate & Surf")',
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "audit" / "skate_surf_contact_sheet.png",
        help="Output PNG path",
    )
    ap.add_argument("--columns", type=int, default=4, help="Grid columns")
    ap.add_argument("--cell", type=int, default=280, help="Square cell size in pixels")
    ap.add_argument("--label-h", type=int, default=30, dest="label_h", help="Label strip height")
    ap.add_argument("--size", type=int, default=512, help="Internal render resolution (square)")
    ap.add_argument("--seed", type=int, default=1, help="Deterministic pattern seed")
    args = ap.parse_args()

    if not FINISH_JS.is_file():
        print(f"Missing {FINISH_JS}", file=sys.stderr)
        return 1
    js = FINISH_JS.read_text(encoding="utf-8", errors="replace")
    groups = _parse_pattern_groups(js)
    ids = groups.get(args.category)
    if not ids:
        print(
            f"Unknown category {args.category!r}. Keys: {sorted(groups.keys())}",
            file=sys.stderr,
        )
        return 1

    from engine.compose import _get_pattern_mask, compose_paint_mod

    shape = (int(args.size), int(args.size))
    mask = np.ones(shape, dtype=np.float32)
    base = np.full((shape[0], shape[1], 3), 0.42, dtype=np.float32)

    tiles: list[tuple[str, Image.Image]] = []
    for pid in ids:
        err: str | None = None
        try:
            pm = _get_pattern_mask(pid, shape, mask, int(args.seed), 1.0, scale=1.0)
            if pm is None:
                err = "no mask"
                m_img = Image.new("RGB", (64, 64), (90, 30, 30))
            else:
                pm = np.clip(np.asarray(pm, dtype=np.float32), 0.0, 1.0)
                m_img = _norm_gray(pm)
            if err is None:
                paint = compose_paint_mod(
                    "gloss",
                    pid,
                    base.copy(),
                    shape,
                    mask,
                    int(args.seed),
                    1.0,
                    1.0,
                    scale=1.0,
                )
                paint = np.asarray(paint, dtype=np.float32)[:, :, :3]
                p_img = Image.fromarray(
                    (np.clip(paint, 0.0, 1.0) * 255.0).astype(np.uint8), "RGB"
                )
            else:
                p_img = None
        except Exception as exc:
            err = str(exc)[:80]
            m_img = Image.new("RGB", (64, 64), (90, 30, 30))
            p_img = None
        cell_img = _cell_image(m_img, p_img, args.cell, args.label_h)
        label = pid if err is None else f"{pid}  [{err}]"
        tiles.append((label, cell_img))

    _write_sheet(args.out.resolve(), tiles, args.columns, args.cell, args.label_h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
