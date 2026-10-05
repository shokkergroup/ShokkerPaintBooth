#!/usr/bin/env python3
"""
Tick 93 rebake — Directional Grain (10 aniso_* finishes).

Rebakes each spec preview after the _aniso_grain_field rewrite. Writes
to all 3 mirror locations.
"""
from __future__ import annotations

import io
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))

ANISO = [
    "aniso_horizontal_chrome", "aniso_vertical_pearl", "aniso_diagonal_candy",
    "aniso_radial_metallic", "aniso_circular_chrome", "aniso_crosshatch_steel",
    "aniso_spiral_mercury", "aniso_wave_titanium", "aniso_herringbone_gold",
    "aniso_turbulence_metal",
]

# Brushed-steel tint that lets the spec channel structure read clearly
TINT = (0.56, 0.60, 0.66)


def spec_to_rgb_preview(M, R, CC, tint):
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


def main() -> int:
    import shokker_engine_v2 as eng  # noqa
    mono = eng.MONOLITHIC_REGISTRY
    print(f"[rebake-aniso] MONOLITHIC_REGISTRY: {len(mono)} entries")
    print()
    print(f"{'finish':<30s} {'spec_s':>7s} {'paint_s':>8s} {'total':>7s}  M_std  R_std  CC_std  range")
    for stem in ANISO:
        entry = mono.get(stem)
        if not entry:
            print(f"  {stem:30s}  MISSING from registry")
            continue
        spec_fn, paint_fn = entry[0], entry[1]
        seed = hash(stem) & 0x7FFFFFFF
        shape = (2048, 2048)
        mask = np.ones(shape, dtype=np.float32)
        neutral = np.full((2048, 2048, 3), 0.5, dtype=np.float32)
        t0 = time.perf_counter()
        spec_arr = spec_fn(shape, mask, seed, 1.0)
        t_spec = time.perf_counter() - t0
        t0 = time.perf_counter()
        _ = paint_fn(neutral.copy(), shape, mask, seed, 1.0, 1.0)
        t_paint = time.perf_counter() - t0
        M = spec_arr[:, :, 0].astype(np.float32)
        R = spec_arr[:, :, 1].astype(np.float32)
        CC = spec_arr[:, :, 2].astype(np.float32)
        rgb = spec_to_rgb_preview(M, R, CC, TINT)
        img = Image.fromarray(rgb).resize((256, 256), Image.LANCZOS)
        targets = [
            V5_ROOT / "thumbnails" / "monolithic" / f"{stem}.png",
            V5_ROOT / "electron-app" / "server" / "thumbnails" / "monolithic" / f"{stem}.png",
            V5_ROOT / "electron-app" / "server" / "pyserver" / "_internal" / "thumbnails" / "monolithic" / f"{stem}.png",
        ]
        img.save(targets[0])
        for t in targets[1:]:
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(targets[0], t)
        total = t_spec + t_paint
        print(f"  {stem:<30s} {t_spec:>7.2f} {t_paint:>8.2f} {total:>7.2f}  {np.std(M):5.1f}  {np.std(R):5.1f}  {np.std(CC):5.1f}   M=[{M.min():.0f},{M.max():.0f}]")
    print()
    print("[rebake-aniso] done. 10 thumbnails updated in 3 mirror locations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
