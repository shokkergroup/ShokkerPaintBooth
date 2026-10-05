"""Probe: render real registered SPB finishes through the Spec Sculpt catalog path.

Proves whether reusing existing finish spec functions gives real diversity, and
whether the Viva pre/post pass is what introduces the grid-flash artifact.

Writes two contact sheets: catalog specs WITHOUT the VM pass (raw _resolve_finish_spec)
and WITH it (current catalog branch behavior), plus a diversity metric for each.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.spec_sculpt.catalog_blend import blend_registered_specs_float  # noqa: E402
from engine.spec_sculpt.core import load_paint_rgb_float01  # noqa: E402
from engine.spec_sculpt.generate import scratch_spec_from_any_paint  # noqa: E402

FINISHES = [
    "aniso_circular_chrome", "brushed_metal_fine", "carbon_weave", "multiscale_carbon_micro",
    "liquid_metal", "mercury_pool", "cs_candypaint", "gradient_pearl_chrome",
    "holographic_wrap", "cs_oilslick", "galaxy", "velvet",
    "multiscale_matte_silk", "aniso_herringbone_gold", "chameleon_copper", "grad_titanium_fire",
    "cs_gunmetal_gold", "pp_marble_flow_pearl", "fine_silver_flake", "quilt_diamond_shimmer",
    "ember_glow", "stealth", "aniso_crosshatch_steel", "prizm_holographic",
]
SIZE = 256
SEED = 9101


def _comp(spec):
    return np.stack([spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]], 2).astype(np.uint8)


def _diversity(comps):
    feats = [np.asarray(Image.fromarray(c).resize((16, 16)), np.float32).reshape(-1) for c in comps]
    feats = np.stack(feats)
    d = []
    for i in range(len(feats)):
        for j in range(i + 1, len(feats)):
            d.append(float(np.sqrt(np.mean((feats[i] - feats[j]) ** 2))))
    return float(np.mean(d)), float(np.min(d))


def _sheet(comps, labels, out, cols=6):
    n = len(comps)
    rows = (n + cols - 1) // cols
    tile, labh, pad = SIZE, 20, 6
    cw, ch = tile + pad, tile + labh + pad
    sheet = Image.new("RGB", (cols * cw + pad, rows * ch + pad), (16, 18, 24))
    d = ImageDraw.Draw(sheet)
    for i, (c, lab) in enumerate(zip(comps, labels)):
        r, cc = divmod(i, cols)
        x, y = pad + cc * cw, pad + r * ch
        sheet.paste(Image.fromarray(c).resize((tile, tile), Image.BILINEAR), (x, y))
        d.text((x + 3, y + tile + 4), lab[:30], fill=(220, 225, 235))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print("wrote", out)


def main():
    tex, _, _ = load_paint_rgb_float01(
        os.path.join(ROOT, "docs/hardmode_proof/dualshift_sunset_paint.png"), target_size=SIZE)
    m = np.ones((SIZE, SIZE), np.float32)

    raw_comps, vm_comps, labels = [], [], []
    for fid in FINISHES:
        try:
            spec_raw = blend_registered_specs_float((SIZE, SIZE), m, seed=SEED, sm=1.0, stack=[(fid, 1.0)])
            raw_comps.append(_comp(spec_raw))
            spec_vm = scratch_spec_from_any_paint(tex, seed=SEED, catalog_stack=[(fid, 1.0)])
            vm_comps.append(_comp(spec_vm))
            labels.append(fid)
        except Exception as e:
            print("FAIL", fid, e)

    rmean, rmin = _diversity(raw_comps)
    vmean, vmin = _diversity(vm_comps)
    print(f"RAW catalog (no VM)  diversity mean={rmean:.1f} min={rmin:.1f}")
    print(f"WITH VM pass         diversity mean={vmean:.1f} min={vmin:.1f}")
    _sheet(raw_comps, labels, os.path.join(ROOT, "_perf/spec_diversity/catalog_raw_noVM.png"))
    _sheet(vm_comps, labels, os.path.join(ROOT, "_perf/spec_diversity/catalog_withVM.png"))


if __name__ == "__main__":
    main()
