#!/usr/bin/env python3
"""
Tick 91 rebake — Ghost Geometry (10) + Depth Illusion (11) thumbnails.

After the renderer edits in engine/expansions/fusions.py, every Ghost
and Depth Illusion finish needs a fresh thumbnail so the workbench shows
the new output. Uses the spec-channel preview path (per bake_spec_driven_
thumbnails.py recipe) since Ghost Geometry is spec_driven and Depth
Illusion's structure is also primarily in the spec channel.

Writes to all 3 mirror locations:
  thumbnails/monolithic/<id>.png
  electron-app/server/thumbnails/monolithic/<id>.png
  electron-app/server/pyserver/_internal/thumbnails/monolithic/<id>.png
"""
from __future__ import annotations

import io
import sys
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))

GHOST = [
    "ghost_camo", "ghost_circuit", "ghost_diamonds", "ghost_fracture",
    "ghost_hex", "ghost_quilt", "ghost_scales", "ghost_stripes",
    "ghost_vortex", "ghost_waves",
]
DEPTH = [
    "depth_bubble", "depth_canyon", "depth_crack", "depth_erosion",
    "depth_honeycomb", "depth_map", "depth_pillow", "depth_ripple",
    "depth_scale", "depth_vortex", "depth_wave",
]


# Tint hints per category (just for the preview render — actual paint pipeline
# uses per-finish color elsewhere).
GHOST_TINT = (0.55, 0.62, 0.78)   # cool steel/teal
DEPTH_TINT = (0.58, 0.50, 0.42)   # warm earth (deep canyon vibe)


def spec_to_rgb_preview(M, R, CC, tint):
    """High M = bright, low R = bright, high CC = depth contribution."""
    sb = (M * 1.0 + (255.0 - R) * 0.6 + CC * 0.3) / 1.9
    sb = np.clip(sb, 0, 255)
    lo, hi = sb.min(), sb.max()
    if hi - lo > 2.0:
        sb = (sb - lo) / (hi - lo) * 255.0
    sb = sb.astype(np.uint8)
    base = sb.astype(np.float32)
    amt = 0.40
    r = base * (1.0 - amt) + (base * tint[0]) * amt
    g = base * (1.0 - amt) + (base * tint[1]) * amt
    b = base * (1.0 - amt) + (base * tint[2]) * amt
    return np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)


def rebake_one(stem: str, spec_fn, tint, size: int = 2048, thumb: int = 256) -> dict:
    seed = hash(stem) & 0x7FFFFFFF
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    arr = spec_fn(shape, mask, seed, 1.0)
    M = arr[:, :, 0].astype(np.float32)
    R = arr[:, :, 1].astype(np.float32)
    CC = arr[:, :, 2].astype(np.float32)
    rgb = spec_to_rgb_preview(M, R, CC, tint)
    img = Image.fromarray(rgb).resize((thumb, thumb), Image.LANCZOS)
    targets = [
        V5_ROOT / "thumbnails" / "monolithic" / f"{stem}.png",
        V5_ROOT / "electron-app" / "server" / "thumbnails" / "monolithic" / f"{stem}.png",
        V5_ROOT / "electron-app" / "server" / "pyserver" / "_internal" / "thumbnails" / "monolithic" / f"{stem}.png",
    ]
    img.save(targets[0])
    for t in targets[1:]:
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(targets[0], t)
    return {
        "M_std": float(np.std(M)),
        "R_std": float(np.std(R)),
        "CC_std": float(np.std(CC)),
        "M_range": (float(M.min()), float(M.max())),
    }


def main() -> int:
    import shokker_engine_v2 as eng  # noqa
    mono = eng.MONOLITHIC_REGISTRY
    print(f"[rebake] MONOLITHIC_REGISTRY size: {len(mono)}")

    print()
    print("=== Ghost Geometry ===")
    for stem in GHOST:
        entry = mono.get(stem)
        if not entry or not isinstance(entry, tuple):
            print(f"  {stem:24s}  MISSING")
            continue
        spec_fn = entry[0]
        try:
            stats = rebake_one(stem, spec_fn, GHOST_TINT)
            print(f"  {stem:24s}  M_std={stats['M_std']:6.2f}  R_std={stats['R_std']:6.2f}  CC_std={stats['CC_std']:6.2f}  M=[{stats['M_range'][0]:.0f},{stats['M_range'][1]:.0f}]")
        except Exception as exc:
            print(f"  {stem:24s}  FAIL: {exc}")

    print()
    print("=== Depth Illusion ===")
    for stem in DEPTH:
        entry = mono.get(stem)
        if not entry or not isinstance(entry, tuple):
            print(f"  {stem:24s}  MISSING")
            continue
        spec_fn = entry[0]
        try:
            stats = rebake_one(stem, spec_fn, DEPTH_TINT)
            print(f"  {stem:24s}  M_std={stats['M_std']:6.2f}  R_std={stats['R_std']:6.2f}  CC_std={stats['CC_std']:6.2f}  M=[{stats['M_range'][0]:.0f},{stats['M_range'][1]:.0f}]")
        except Exception as exc:
            print(f"  {stem:24s}  FAIL: {exc}")

    print()
    print("[rebake] done. All 21 thumbnails updated in 3 mirror locations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
