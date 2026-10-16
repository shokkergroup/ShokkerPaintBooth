"""Render one direct, staging-only split picker for H1-I32.

This is deliberately not the catalog picker writer and never promotes assets
or edits its manifest.  It uses I32's exact authored paint/spec functions at
1024² then area-downsamples to the native 48px split-card geometry, avoiding
the unrelated heavyweight server import while owner-eye staging continues.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.expansions.fractured_houdini_veiled_skull_i32_2026 import (  # noqa: E402
    paint_veiled_skull_i32,
    spec_veiled_skull_i32,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=48)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=ROOT / "_houdini_thumb_i32_p8_dev" / "houdini_veiled_skull_picker_split.png")
    args = parser.parse_args()
    out_size = max(32, min(256, int(args.size)))
    # Server snapshots render a 2048 source at preview_scale .5: mirror that
    # effective 1024² fidelity here, then collapse to the native split size.
    master = 1024
    source = np.full((master, master, 3), 132, np.uint8)
    mask = np.full((master, master), 255, np.uint8)
    paint = paint_veiled_skull_i32(source, (master, master), mask, int(args.seed), 1.0, None)
    spec = spec_veiled_skull_i32((master, master), int(args.seed), 1.0, 0, 0)
    paint_u8 = np.clip(paint * 255.0 if paint.max() <= 1.5 else paint, 0, 255).astype(np.uint8)
    paint_small = cv2.resize(paint_u8, (out_size, out_size), interpolation=cv2.INTER_AREA)
    spec_small = cv2.resize(spec, (out_size, out_size), interpolation=cv2.INTER_AREA)
    split = np.concatenate((paint_small, spec_small), axis=1)
    split[:, out_size - 1:out_size + 1] = (20, 20, 20)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # cv2 writes BGR while the renderer arrays are RGB.
    if not cv2.imwrite(str(args.output), cv2.cvtColor(split, cv2.COLOR_RGB2BGR)):
        raise RuntimeError(f"could not write {args.output}")
    print(args.output)
    print("paint_std=%.4f mrc_std=%.2f/%.2f/%.2f" % (paint.std(), spec[..., 0].std(), spec[..., 1].std(), spec[..., 2].std()))


if __name__ == "__main__":
    main()
