"""Render family survey sheets of REAL registry finishes (no-VM catalog path)
so we can curate the best-of set for Spec Sculpt.

Writes one labelled contact sheet per bucket to _perf/spec_diversity/curate/ and
prints the finish ids in each bucket (so picks can be referenced by id).
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

SIZE = 200
SEED = 9101
PER_BUCKET = 30

# Buckets: (name, [keywords]). A finish lands in the FIRST bucket it matches.
BUCKETS = [
    ("metals_chrome_brushed", ["chrome", "mirror", "mercury", "liquid_metal", "aniso_", "brushed",
                                "machined", "crosshatch", "herringbone", "steel", "billet", "knurl", "titanium"]),
    ("carbon_matte_velvet", ["carbon", "weave", "kevlar", "honeycomb", "fiber", "matte", "velvet",
                              "satin", "suede", "stealth", "cerakote"]),
    ("candy_pearl_gloss", ["candy", "pearl", "opal", "ghost", "gloss", "wet", "lacquer", "glass", "anodiz"]),
    ("flake_diamond_sparkle", ["flake", "glitter", "diamond", "sparkle", "quilt", "metalflake", "shimmer"]),
    ("holo_prism_shift", ["holo", "prism", "oilslick", "oil_slick", "chameleon", "colorshift", "flip",
                           "spectral", "iridesc", "microshift", "hyperflip"]),
    ("exotic_gold_glow", ["galaxy", "nebula", "plasma", "fire", "molten", "aurora", "cosmic", "gold",
                           "copper", "bronze", "brass", "rose_gold", "marble", "glow", "neon", "ember", "toxic"]),
]


def _comp(spec):
    return np.stack([spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]], 2).astype(np.uint8)


def _sheet(items, out, cols=6):
    n = len(items)
    rows = (n + cols - 1) // cols
    tile, labh, pad = SIZE, 22, 6
    cw, ch = tile + pad, tile + labh + pad
    sheet = Image.new("RGB", (cols * cw + pad, rows * ch + pad), (16, 18, 24))
    d = ImageDraw.Draw(sheet)
    for i, (comp, lab) in enumerate(items):
        r, cc = divmod(i, cols)
        x, y = pad + cc * cw, pad + r * ch
        sheet.paste(Image.fromarray(comp).resize((tile, tile), Image.BILINEAR), (x, y))
        d.text((x + 3, y + tile + 4), lab[:32], fill=(220, 225, 235))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)


def main():
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY
    keys = sorted(set(BASE_REGISTRY.keys()) | set(MONOLITHIC_REGISTRY.keys()))
    m = np.ones((SIZE, SIZE), np.float32)

    assigned = set()
    for bname, kws in BUCKETS:
        picks = []
        for k in keys:
            if k in assigned:
                continue
            kl = k.lower()
            if any(kw in kl for kw in kws):
                picks.append(k)
        # spread picks across the matches (not just alphabetical front)
        if len(picks) > PER_BUCKET:
            step = len(picks) / PER_BUCKET
            picks = [picks[int(i * step)] for i in range(PER_BUCKET)]
        items = []
        for fid in picks:
            assigned.add(fid)
            try:
                spec = blend_registered_specs_float((SIZE, SIZE), m, seed=SEED, sm=1.0, stack=[(fid, 1.0)])
                items.append((_comp(spec), fid))
            except Exception as e:
                print("FAIL", fid, e)
        out = os.path.join(ROOT, "_perf/spec_diversity/curate", f"{bname}.png")
        _sheet(items, out)
        print(f"=== {bname} ({len(items)}) -> {out}")
        print("   " + ", ".join(fid for _, fid in items))


if __name__ == "__main__":
    main()
