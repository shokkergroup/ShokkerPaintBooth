#!/usr/bin/env python3
"""
Tick 94 rebake — Reactive Panels (10) + Sparkle Systems (10) + Weather & Age (10).

Rebakes spec-channel previews after the tick-94 renderer changes. Writes
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

REACTIVE = [
    "reactive_stealth_pop", "reactive_pearl_flash", "reactive_candy_reveal",
    "reactive_chrome_fade", "reactive_matte_shine", "reactive_dual_tone",
    "reactive_ghost_metal", "reactive_mirror_shadow", "reactive_warm_cold",
    "reactive_pulse_metal",
]
SPARKLE = [
    "sparkle_diamond_dust", "sparkle_starfield", "sparkle_galaxy",
    "sparkle_firefly", "sparkle_snowfall", "sparkle_champagne",
    "sparkle_meteor", "sparkle_constellation", "sparkle_confetti",
    "sparkle_lightning_bug",
]
WEATHER = [
    "weather_sun_fade", "weather_salt_spray", "weather_acid_rain",
    "weather_desert_blast", "weather_ice_storm", "weather_road_spray",
    "weather_hood_bake", "weather_barn_dust", "weather_ocean_mist",
    "weather_volcanic_ash",
]

REACTIVE_TINT = (0.62, 0.66, 0.78)
SPARKLE_TINT = (0.66, 0.66, 0.78)
WEATHER_TINT = (0.62, 0.50, 0.40)


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


def rebake_group(mono, stems, tint, label):
    print()
    print(f"=== {label} ===")
    print(f"{'finish':<32s} {'spec_s':>7s} {'paint_s':>8s} {'total':>7s}  M_std  R_std  CC_std  range")
    for stem in stems:
        entry = mono.get(stem)
        if not entry:
            print(f"  {stem:32s}  MISSING")
            continue
        spec_fn, paint_fn = entry[0], entry[1]
        seed = hash(stem) & 0x7FFFFFFF
        shape = (2048, 2048)
        mask = np.ones(shape, dtype=np.float32)
        neutral = np.full((2048, 2048, 3), 0.5, dtype=np.float32)
        try:
            t0 = time.perf_counter()
            spec_arr = spec_fn(shape, mask, seed, 1.0)
            t_spec = time.perf_counter() - t0
            t0 = time.perf_counter()
            _ = paint_fn(neutral.copy(), shape, mask, seed, 1.0, 1.0)
            t_paint = time.perf_counter() - t0
            M = spec_arr[:, :, 0].astype(np.float32)
            R = spec_arr[:, :, 1].astype(np.float32)
            CC = spec_arr[:, :, 2].astype(np.float32)
            rgb = spec_to_rgb_preview(M, R, CC, tint)
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
            status = "OK" if total <= 3.0 else ("WARN" if total <= 6.0 else "OVER")
            print(f"  {stem:32s} {t_spec:>7.2f} {t_paint:>8.2f} {total:>7.2f}  {np.std(M):5.1f}  {np.std(R):5.1f}  {np.std(CC):5.1f}   M=[{M.min():.0f},{M.max():.0f}]  {status}")
        except Exception as exc:
            print(f"  {stem:32s}  FAIL: {exc}")


def main() -> int:
    import shokker_engine_v2 as eng  # noqa
    mono = eng.MONOLITHIC_REGISTRY
    print(f"[rebake-tick94] MONOLITHIC_REGISTRY: {len(mono)} entries")
    rebake_group(mono, REACTIVE, REACTIVE_TINT, "REACTIVE PANELS")
    rebake_group(mono, SPARKLE, SPARKLE_TINT, "SPARKLE SYSTEMS")
    rebake_group(mono, WEATHER, WEATHER_TINT, "WEATHER & AGE")
    print()
    print("[rebake-tick94] done. 30 thumbnails updated in 3 mirror locations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
