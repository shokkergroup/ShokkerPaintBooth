#!/usr/bin/env python3
"""
SPB-86 tick 51 — generate per-finish preview PNGs at 2048² showing the
new micro-signature output. Owner reviews these to decide whether the
direction is right before we expand to all 30 enh_* finishes.

Six families covered (one representative finish each):
* enh_chrome (mirror with rare micro-streaks)
* enh_brushed (anisotropic 1D grain)
* enh_carbon_fiber (orthogonal weave)
* enh_pearl (soft hue zones)
* enh_metallic (lognormal flakes)
* enh_frozen (frost ridges)

Saves PNGs to _workbook_metrics/spb86_micro_preview/ at 1024² (downsampled
from 2048 render for file size).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))


PROBE_FINISHES = [
    "enh_chrome",
    "enh_brushed",
    "enh_carbon_fiber",
    "enh_pearl",
    "enh_metallic",
    "enh_frozen",
]


def spec_to_rgb_preview(M, R, CC, swatch_hex: str = "#808080") -> np.ndarray:
    sb = (M * 1.0 + (255.0 - R) * 0.6 + CC * 0.3) / 1.9
    sb = np.clip(sb, 0, 255)
    lo, hi = sb.min(), sb.max()
    if hi - lo > 2.0:
        sb = (sb - lo) / (hi - lo) * 255.0
    sb = np.clip(sb, 0, 255).astype(np.uint8)
    s = swatch_hex.lstrip("#")
    if len(s) == 6:
        tr, tg, tb = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    else:
        tr = tg = tb = 128
    tint = 0.30
    base = sb.astype(np.float32)
    r = base * (1.0 - tint) + (base * (tr / 255.0)) * tint
    g = base * (1.0 - tint) + (base * (tg / 255.0)) * tint
    b = base * (1.0 - tint) + (base * (tb / 255.0)) * tint
    return np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)


def main() -> int:
    import shokker_engine_v2 as eng  # noqa: F401
    out_dir = V5_ROOT / "_workbook_metrics" / "spb86_micro_preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[spb86-preview] saving to {out_dir}")
    for stem in PROBE_FINISHES:
        e = eng.BASE_REGISTRY.get(stem)
        if not e:
            print(f"  MISSING {stem}"); continue
        seed = hash(stem) & 0x7FFFFFFF
        M, R, CC = e["base_spec_fn"]((2048, 2048), seed, 1.0,
                                       e.get("M", 128), e.get("R", 80))
        # Save a 1024² preview (downsampled from 2048 render for size)
        rgb = spec_to_rgb_preview(M, R, CC, "#808080")
        img = Image.fromarray(rgb).resize((1024, 1024), Image.LANCZOS)
        out = out_dir / f"{stem}.png"
        img.save(out)
        print(f"  {stem:18s}  M mean={M.mean():6.1f} std={M.std():5.2f}  saved -> {out.name}")

    # Build a single 3x2 grid summary sheet
    cell = 384
    sheet = Image.new("RGB", (cell * 3, cell * 2), (16, 18, 24))
    for i, stem in enumerate(PROBE_FINISHES):
        src = Image.open(out_dir / f"{stem}.png").resize((cell, cell), Image.LANCZOS)
        col, row = i % 3, i // 3
        sheet.paste(src, (col * cell, row * cell))
    sheet_path = out_dir / "comparison_sheet.png"
    sheet.save(sheet_path)
    print(f"[spb86-preview] comparison sheet at {sheet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
