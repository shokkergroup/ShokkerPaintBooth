#!/usr/bin/env python3
"""Direct native evidence for the IRIDESCENT INSECTS 2026 rebuild.

This is deliberately a small owner-eye probe, not a production thumbnail
writer. It renders a plain 2048² paint carrier plus literal RGB=M/Rough/Cc
proof, then makes a contact sheet with 256px picker-scale cards.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.paint_v2 import iridescent_insects as insects


WAVE_1 = (
    "beetle_jewel", "beetle_rainbow", "butterfly_morpho",
    "butterfly_monarch", "dragonfly_wing",
    "beetle_tortoise", "beetle_tiger", "beetle_rose_chafer",
    "beetle_buprestid", "beetle_ground",
)


def _rgb(values: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(values * 255.0, 0, 255).astype(np.uint8), "RGB")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", type=int, default=2048)
    ap.add_argument("--thumb", type=int, default=256)
    ap.add_argument("--out", type=Path, default=Path("_iridescent_insects_2026/wave1_native"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    n = args.render
    mask = np.ones((n, n), dtype=np.float32)
    cards = []
    for index, name in enumerate(WAVE_1):
        pfn = getattr(insects, f"paint_{name}")
        sfn = getattr(insects, f"spec_{name}")
        start = time.perf_counter()
        paint = pfn(np.zeros((n, n, 3), np.float32), (n, n), mask, 42, 1.0, None)
        metal, rough, coat = sfn((n, n), 42, 1.0, 0, 0)
        elapsed = time.perf_counter() - start
        spec = np.dstack((metal, rough, coat)).astype(np.float32) / 255.0
        paint_img, spec_img = _rgb(paint), _rgb(spec)
        paint_img.save(args.out / f"{name}_paint_2048.png")
        spec_img.save(args.out / f"{name}_mrc_2048.png")
        left = paint_img.resize((args.thumb, args.thumb), Image.Resampling.LANCZOS)
        right = spec_img.resize((args.thumb, args.thumb), Image.Resampling.LANCZOS)
        split = Image.new("RGB", (args.thumb * 2, args.thumb))
        split.paste(left, (0, 0)); split.paste(right, (args.thumb, 0))
        split.save(args.out / f"{name}_picker_split.png")
        cards.append((name, split, elapsed, (metal.std(), rough.std(), coat.std())))
    card_w, card_h = args.thumb * 2, args.thumb + 44
    sheet = Image.new("RGB", (card_w, card_h * len(cards)), (12, 15, 22))
    draw = ImageDraw.Draw(sheet)
    for row, (name, split, elapsed, spread) in enumerate(cards):
        y = row * card_h
        sheet.paste(split, (0, y))
        draw.text((8, y + args.thumb + 5), f"{name}  {elapsed:.2f}s  M/R/Cc sigma {spread[0]:.1f}/{spread[1]:.1f}/{spread[2]:.1f}", fill=(230, 235, 245))
    sheet.save(args.out / "wave1_contact_sheet.png")
    print(f"[insects-2026] wrote {len(cards)} cards -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
