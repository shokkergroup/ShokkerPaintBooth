#!/usr/bin/env python3
"""
Bake spec-aware preview thumbnails for Enhanced Foundation Exotic (efx_*).

The standard rebuild_thumbnails.py renders the PAINT channel of a finish
into thumbnails/base/<id>.png. For spec-driven finishes (Foundation,
Enhanced Foundation, Enhanced Foundation Exotic) paint is intentionally
flat, so every paint-only thumbnail is the same gray — useless in the
picker.

This script renders the SPEC channel directly as a grayscale image so
the picker can show what each efx_* finish actually contributes. It
calls each entry's base_spec_fn(), gets the M/R/CC arrays, and produces
a luminance preview that emphasizes the SPEC CHARACTER (where M is
high → bright; where R is low → polished/bright; combined into a
single visual that captures the pattern).

Output: thumbnails/base/<id>.png  (overwrites the flat-gray bake)
        thumbnails/base_spec_preview/<id>.png  (also kept here as a
        canonical "spec-only" preview the picker can use)
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from PIL import Image

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))

OUT_BASE = V5_ROOT / "thumbnails" / "base"
OUT_PREV = V5_ROOT / "thumbnails" / "base_spec_preview"
OUT_PREV.mkdir(parents=True, exist_ok=True)


def spec_to_rgb_preview(M: np.ndarray, R: np.ndarray, CC: np.ndarray, swatch_hex: str) -> np.ndarray:
    """Compose a single RGB preview from M/R/CC that reads as a 'spec sample'.

    Strategy:
      - Luminance comes from the spec response:
          spec_brightness = (M*1.0 + (255-R)*0.6 + CC*0.3) / (1.0+0.6+0.3)
        Where high M = metallic flash, low R = polished gloss, high CC = clearcoat depth.
      - Color tint comes from the entry's swatch hex (mild tint, ~20-30% strength)
        so different finishes read as visually different even when their
        spec triplet means are similar.
      - Final image is 256x256 uint8 RGB.
    """
    H, W = M.shape
    sb = (M * 1.0 + (255.0 - R) * 0.6 + CC * 0.3) / 1.9
    sb = np.clip(sb, 0, 255)
    # Normalize against the per-image dynamic range so dim finishes still show
    # their structure (don't blow out by a global mean).
    lo, hi = sb.min(), sb.max()
    if hi - lo > 2.0:
        sb = (sb - lo) / (hi - lo) * 255.0
    sb = np.clip(sb, 0, 255).astype(np.uint8)

    # Parse swatch hex tint
    s = swatch_hex.lstrip('#')
    if len(s) == 6:
        tr, tg, tb = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    else:
        tr = tg = tb = 128
    # Apply tint: 70% spec luminance + 30% tinted version of that luminance
    tint_strength = 0.30
    base_gray = sb.astype(np.float32)
    r = base_gray * (1.0 - tint_strength) + (base_gray * (tr / 255.0)) * tint_strength
    g = base_gray * (1.0 - tint_strength) + (base_gray * (tg / 255.0)) * tint_strength
    b = base_gray * (1.0 - tint_strength) + (base_gray * (tb / 255.0)) * tint_strength
    rgb = np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)
    return rgb


def main() -> int:
    import shokker_engine_v2 as eng   # noqa: F401 — triggers BASE_REGISTRY build
    base = eng.BASE_REGISTRY
    # Pull swatches from finish-data via the in-app JS file (lightweight regex parse).
    import re
    fd_text = (V5_ROOT / "paint-booth-0-finish-data.js").read_text(encoding="utf-8")
    swatches = {}
    for m in re.finditer(r'\{\s*id:\s*"(efx_[a-z_]+)"[^}]*?swatch:\s*"(#[0-9a-fA-F]{6})"', fd_text):
        swatches[m.group(1)] = m.group(2)

    efx_ids = sorted(k for k in base if k.startswith("efx_"))
    print(f"[efx-preview] rendering {len(efx_ids)} spec-aware previews")
    # CRITICAL (owner brief 2026-05-15): render at 2048 (real car-body size)
    # then downsample to 256 for the preview. Rendering directly at 256
    # bypasses the fine-frequency bands (octaves 512/1024/2048 collapse to
    # sub-pixel detail at small renders) — the preview would lie about what
    # the painter sees on the car. Downsampling 2048→256 preserves the
    # texture envelope while keeping the file lightweight.
    RENDER = 2048
    THUMB = 256
    import time
    for fid in efx_ids:
        entry = base[fid]
        spec_fn = entry.get("base_spec_fn")
        if not callable(spec_fn):
            print(f"  SKIP {fid} (no base_spec_fn)")
            continue
        seed = hash(fid) & 0x7FFFFFFF
        t0 = time.time()
        M, R, CC = spec_fn((RENDER, RENDER), seed, 1.0, entry.get("M", 128), entry.get("R", 80))
        rgb_full = spec_to_rgb_preview(M, R, CC, swatches.get(fid, "#808080"))
        # Downsample 2048 → 256 via LANCZOS (preserves high-frequency detail).
        img = Image.fromarray(rgb_full).resize((THUMB, THUMB), Image.LANCZOS)
        img.save(OUT_BASE / f"{fid}.png")
        img.save(OUT_PREV / f"{fid}.png")
        dt = time.time() - t0
        print(f"  {dt:4.1f}s  {fid:32s} M=({M.mean():.0f}±{M.std():.0f}) R=({R.mean():.0f}±{R.std():.0f}) CC=({CC.mean():.0f}±{CC.std():.0f})")
    print(f"[efx-preview] done. PNGs in {OUT_BASE} and {OUT_PREV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
