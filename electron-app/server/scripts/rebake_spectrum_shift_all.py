#!/usr/bin/env python3
"""SPB-102 — rebake all 50 ★ Spectrum Shift thumbnails after v2 rewrite.

Renders the PAINT channel onto neutral substrate (so the chromatic
substrate is what you actually see), then writes to all 3 mirror
thumbnail locations.
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

PALETTES = ["oil_slick", "aurora", "sunset", "vapor", "holographic",
            "goldsmith", "phantom", "inferno", "mirage", "reptile"]
VARIANTS = ["classic", "macro", "micro", "shimmer", "wave"]


def rebake_paint_preview(stem: str, paint_fn, size: int = 2048) -> dict:
    """Render the paint channel onto a DARK base (luma 0.15) so the
    paint_fn's treat_mask fully engages and the iridescent substrate
    shows at its real visual intensity. Mirrors the actual app use case
    where spectrum_shift gets applied to dark body zones."""
    seed = hash(stem) & 0x7FFFFFFF
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    # Dark base so substrate fully replaces (treat_mask ≈ 1.0 at luma 0.15)
    dark_base = np.full((size, size, 3), 0.15, dtype=np.float32)
    t0 = time.perf_counter()
    painted = paint_fn(dark_base.copy(), shape, mask, seed, 1.0, 1.0)
    dt = time.perf_counter() - t0
    rgb = np.clip(painted * 255, 0, 255).astype(np.uint8)
    img = Image.fromarray(rgb).resize((256, 256), Image.LANCZOS)
    out_paths = [
        V5_ROOT / "thumbnails" / "monolithic" / f"{stem}.png",
        V5_ROOT / "electron-app" / "server" / "thumbnails" / "monolithic" / f"{stem}.png",
        V5_ROOT / "electron-app" / "server" / "pyserver" / "_internal" / "thumbnails" / "monolithic" / f"{stem}.png",
    ]
    img.save(out_paths[0])
    for p in out_paths[1:]:
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out_paths[0], p)
    return {
        "paint_s": round(dt, 2),
        "color_mean": rgb.mean(axis=(0, 1)).tolist(),
        "color_std": rgb.std(axis=(0, 1)).tolist(),
    }


def main() -> int:
    import shokker_engine_v2 as eng  # noqa
    mono = eng.MONOLITHIC_REGISTRY
    print(f"[rebake-spectrum-v2] MONOLITHIC_REGISTRY: {len(mono)}")
    ok = 0
    fail = 0
    for palette in PALETTES:
        for variant in VARIANTS:
            stem = f"spectrum_{palette}_{variant}"
            entry = mono.get(stem)
            if not entry:
                print(f"  MISSING: {stem}")
                fail += 1
                continue
            paint_fn = entry[1]
            try:
                stats = rebake_paint_preview(stem, paint_fn)
                ok += 1
                cmean = stats["color_mean"]
                cstd = stats["color_std"]
                print(f"  {stem:<36s}  {stats['paint_s']:.2f}s  "
                      f"R={cmean[0]:.0f}±{cstd[0]:.0f}  "
                      f"G={cmean[1]:.0f}±{cstd[1]:.0f}  "
                      f"B={cmean[2]:.0f}±{cstd[2]:.0f}")
            except Exception as exc:
                print(f"  FAIL {stem}: {exc}")
                fail += 1
    print()
    print(f"[rebake-spectrum-v2] done. {ok} ok, {fail} failed.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
