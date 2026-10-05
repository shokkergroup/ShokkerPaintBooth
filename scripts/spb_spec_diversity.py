"""Spec Sculpt diversity harness.

Renders all SPEC_SCULPT_WORLD_RECIPES (or every preset) from one sample paint,
builds a labelled contact sheet, and prints a diversity metric so we can prove
whether the 'Shokk the World' looks are actually distinct.

Usage:
  python scripts/spb_spec_diversity.py --paint docs/color-change-breakthrough-reference/pic01-paint-preview-a.png \
      --out _perf/spec_diversity/before.png --size 224 --mode world
  python scripts/spb_spec_diversity.py --mode presets   # every preset, not just world recipes
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.spec_sculpt.core import load_paint_rgb_float01  # noqa: E402
from engine.spec_sculpt.generate import scratch_spec_from_any_paint  # noqa: E402
from engine.spec_sculpt.presets import SPEC_SCULPT_PRESETS, normalize_preset_stack  # noqa: E402


def _world_recipes():
    """Mirror server.py SPEC_SCULPT_WORLD_RECIPES so the harness needs no Flask import."""
    return [
        ("Mirror Chrome", [["mirror_chrome", 1.0]]),
        ("Mercury Flow", [["mercury_flow", 1.0]]),
        ("Radial Machined", [["radial_machined", 1.0]]),
        ("Brushed Titanium", [["brushed_titanium", 1.0]]),
        ("Obsidian Mirror", [["obsidian_mirror", 1.0]]),
        ("Forged Carbon", [["forged_carbon", 1.0]]),
        ("Carbon Fiber", [["carbon_fiber", 1.0]]),
        ("Bakeneko Velvet", [["bakeneko_velvet", 1.0]]),
        ("Matte Silk", [["matte_silk", 1.0]]),
        ("Candy Poison", [["candy_poison", 1.0]]),
        ("Cotton Candy", [["cotton_candy", 1.0]]),
        ("Pearl Chaser", [["pearl_chaser", 1.0]]),
        ("Ghost Scales", [["ghost_scales", 1.0]]),
        ("Chaos Flake", [["chaos_flake", 1.0]]),
        ("Hex Flake", [["hex_flake", 1.0]]),
        ("Galaxy Sparkle", [["galaxy_sparkle", 1.0]]),
        ("Metal Flake", [["metal_flake", 1.0]]),
        ("Holographic", [["holographic", 1.0]]),
        ("Arctic Chameleon", [["arctic_chameleon", 1.0]]),
        ("Oil Slick Wave", [["oil_slick_wave", 1.0]]),
        ("Spectral Rings", [["spectral_rings", 1.0]]),
        ("Copper Flame", [["copper_flame", 1.0]]),
        ("Marble Pearl", [["marble_pearl", 1.0]]),
        ("Rose Gold", [["rose_gold", 1.0]]),
    ]


def _composite(spec_u8: np.ndarray) -> np.ndarray:
    return np.stack([spec_u8[:, :, 0], spec_u8[:, :, 1], spec_u8[:, :, 2]], axis=2).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paint", default="docs/color-change-breakthrough-reference/pic01-paint-preview-a.png")
    ap.add_argument("--out", default="_perf/spec_diversity/before.png")
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--mode", choices=["world", "presets"], default="world")
    ap.add_argument("--seed", type=int, default=9101)
    ap.add_argument("--cols", type=int, default=6)
    args = ap.parse_args()

    paint_path = os.path.join(ROOT, args.paint) if not os.path.isabs(args.paint) else args.paint
    tex, orig_hw, _ = load_paint_rgb_float01(paint_path, target_size=args.size)
    print(f"paint={os.path.basename(paint_path)} orig={orig_hw} work={tex.shape[:2]}")

    if args.mode == "world":
        items = _world_recipes()
        seeds = [args.seed + i * 17 for i in range(len(items))]
    else:
        items = [(str(p["label"]), [[str(p["id"]), 1.0]]) for p in SPEC_SCULPT_PRESETS]
        seeds = [args.seed + i * 17 for i in range(len(items))]

    comps = []
    labels = []
    for (label, presets), sd in zip(items, seeds):
        ps = normalize_preset_stack(presets)
        spec = scratch_spec_from_any_paint(tex, seed=sd, chromatic_shift=True, preset_stack=ps)
        comps.append(_composite(spec))
        labels.append(label)

    # --- diversity metric: pairwise L2 over 16x16 downsamples, normalized 0..255 ---
    feats = []
    for c in comps:
        small = np.asarray(Image.fromarray(c).resize((16, 16), Image.BILINEAR), dtype=np.float32)
        feats.append(small.reshape(-1))
    feats = np.stack(feats)
    n = len(feats)
    dists = []
    for i in range(n):
        for j in range(i + 1, n):
            dists.append(float(np.sqrt(np.mean((feats[i] - feats[j]) ** 2))))
    dists = np.array(dists)
    chan_means = np.stack([c.reshape(-1, 3).mean(0) for c in comps])  # per-look mean M,R,Cc
    print(f"DIVERSITY mode={args.mode} n={n}")
    print(f"  mean pairwise RMS dist : {dists.mean():.2f}  (min {dists.min():.2f}  max {dists.max():.2f})")
    print(f"  std of per-look mean M  : {chan_means[:,0].std():.2f}")
    print(f"  std of per-look mean R  : {chan_means[:,1].std():.2f}")
    print(f"  std of per-look mean Cc : {chan_means[:,2].std():.2f}")

    # --- contact sheet ---
    cols = args.cols
    rows = (n + cols - 1) // cols
    tile = args.size
    lab_h = 22
    pad = 6
    cw = tile + pad
    ch = tile + lab_h + pad
    sheet = Image.new("RGB", (cols * cw + pad, rows * ch + pad), (16, 18, 24))
    draw = ImageDraw.Draw(sheet)
    for idx, (c, label) in enumerate(zip(comps, labels)):
        rr, cc = divmod(idx, cols)
        x = pad + cc * cw
        y = pad + rr * ch
        sheet.paste(Image.fromarray(c).resize((tile, tile), Image.BILINEAR), (x, y))
        draw.text((x + 3, y + tile + 4), label, fill=(220, 225, 235))
    out_path = os.path.join(ROOT, args.out) if not os.path.isabs(args.out) else args.out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path)
    print(f"wrote {out_path}  ({sheet.size[0]}x{sheet.size[1]})")


if __name__ == "__main__":
    main()
