# -*- coding: utf-8 -*-
"""◈ PARADIGM — the 2026-08-31 redesign. 34 → 50, with an idea of its own.

Owner: *"Under SHOKKER we have our original Shokker design system which now
feels ancient called PARADIGM. Redesign this entire category and expand it from
35 to 50. Give it it's OWN unique feel somehow. Come up with something unique
here to distinguish this category."*

WHAT WAS THERE. 34 finishes with no shared idea: some physics (Blackbody,
Quantum, Event Horizon), some weather (Category 5 Hypercane, Seismic
Faultline, Geomagnetic Storm), some materials (Living Chrome, Mercury Pool,
Glass Armor). After tonight it was also duplicating other categories — the
weather ones belong in ELEMENTS and the space ones in COSMOS.

THE IDEA: **a PARADIGM finish argues with itself.**

Every one of these shows you a substance you recognise instantly — hessian,
moss, corduroy, cracked concrete, kraft paper, rust — and then behaves like
something it absolutely is not. The weave is real and it is machined from solid
mercury. The moss is real and it is cut glass. The cardboard is real and it is
chrome.

This is the one thing SPB can do that a texture pack cannot: the paint and the
spec map are independent channels, so a surface can LOOK like one material and
BEHAVE like another under light. No other category here does that on purpose —
everywhere else the spec is the honest material of the thing depicted. Here the
geometry still follows the artwork exactly (a weave's spec still runs along the
weave) while the SUBSTANCE contradicts it.

So each row declares two things:

    implies   the material card that substance would really have
    spec      the material family it is given instead

and the gate measures both: FOLLOW (the spec tracks the paint's geometry, as
everywhere else) and CONTRADICT (the material it was given is a long way from
the one it implies, in the M/R/Cc cube). A finish that fails CONTRADICT is not
a PARADIGM finish — it is just a nice texture, and it belongs elsewhere.

  ⬢ WOVEN     textiles that behave like metal
  ⬣ GROWN     living surfaces that behave like glass and mirror
  ⬡ MINERAL   stone and concrete that behave like liquid
  ⬠ MADE      paper, card and timber that behave like chrome
  ⬟ RUINED    rust, ash and decay that behave like something pristine
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

import engine.expansions.fractured_cosmos_kit_2026 as CK
from engine.paint_v2 import spec_cards as SC

ID_PREFIX = "pdg_"
GROUP = "◈ PARADIGM"
GEN = 1024
WORK = 1152

CHAPTERS = {"woven": "⬢ WOVEN", "grown": "⬣ GROWN", "mineral": "⬡ MINERAL",
            "made": "⬠ MADE", "ruined": "⬟ RUINED"}

_STRUCTS = {
    "cells":     lambda sh, sd, k: CK.worley(sh, sd, **k),
    "braid":     lambda sh, sd, k: (CK.kh_braid(sh, sd, **k), None),
    "honeycomb": lambda sh, sd, k: CK.honeycomb(sh, sd, **k),
    "filaments": lambda sh, sd, k: (CK.filaments(sh, sd, **k), None),
    "dendrite":  lambda sh, sd, k: (CK.dla(sh, sd, **k), None),
    "curl":      lambda sh, sd, k: (CK.curl(sh, sd, **k), None),
    "percolate": lambda sh, sd, k: CK.percolate(sh, sd, **k),
    "spall":     lambda sh, sd, k: CK.spall(sh, sd, **k),
    "crack":     lambda sh, sd, k: CK.anneal_crack(sh, sd, **k),
    "polygons":  lambda sh, sd, k: CK.polygons(sh, sd, **k),
    "craters":   lambda sh, sd, k: (CK.craters(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (CK.dunes(sh, sd, **k), None),
    "wrinkle":   lambda sh, sd, k: (CK.wrinkle(sh, sd, **k), None),
    "fingers":   lambda sh, sd, k: (CK.rt_fingers(sh, sd, **k), None),
    "sparks":    lambda sh, sd, k: (CK.sparks(sh, sd, **k), None),
    "bands":     lambda sh, sd, k: (CK.bands(sh, sd, **k), None),
    "eden":      lambda sh, sd, k: (CK.eden(sh, sd, **k), None),
    "hull":      lambda sh, sd, k: CK.hull(sh, sd, **k),
}

# Substance palettes — deliberately ordinary. The shock is not the colour.
P = {
    "hessian":   ((0.16, 0.12, 0.07), (0.42, 0.33, 0.19), (0.66, 0.55, 0.35), (0.84, 0.76, 0.56)),
    "denim":     ((0.06, 0.09, 0.15), (0.16, 0.24, 0.38), (0.34, 0.46, 0.62), (0.62, 0.72, 0.84)),
    "wool":      ((0.14, 0.13, 0.12), (0.36, 0.34, 0.32), (0.58, 0.56, 0.53), (0.80, 0.78, 0.75)),
    "corduroy":  ((0.10, 0.07, 0.05), (0.30, 0.20, 0.12), (0.52, 0.37, 0.22), (0.74, 0.60, 0.42)),
    "felt":      ((0.10, 0.11, 0.10), (0.26, 0.30, 0.26), (0.44, 0.50, 0.44), (0.66, 0.72, 0.66)),
    "moss":      ((0.05, 0.09, 0.04), (0.16, 0.30, 0.12), (0.34, 0.52, 0.22), (0.60, 0.76, 0.42)),
    "lichen":    ((0.14, 0.16, 0.12), (0.38, 0.44, 0.32), (0.62, 0.70, 0.54), (0.85, 0.90, 0.76)),
    "bark":      ((0.09, 0.07, 0.05), (0.26, 0.20, 0.14), (0.44, 0.35, 0.25), (0.66, 0.56, 0.42)),
    "leaf":      ((0.05, 0.10, 0.05), (0.14, 0.32, 0.14), (0.30, 0.56, 0.26), (0.58, 0.80, 0.46)),
    "hide":      ((0.11, 0.08, 0.06), (0.32, 0.24, 0.17), (0.54, 0.42, 0.30), (0.76, 0.64, 0.48)),
    "concrete":  ((0.18, 0.18, 0.19), (0.40, 0.40, 0.41), (0.60, 0.60, 0.61), (0.80, 0.80, 0.81)),
    "granite":   ((0.14, 0.14, 0.16), (0.34, 0.34, 0.37), (0.56, 0.55, 0.58), (0.80, 0.79, 0.82)),
    "chalk":     ((0.34, 0.34, 0.32), (0.60, 0.60, 0.57), (0.80, 0.80, 0.77), (0.96, 0.96, 0.93)),
    "slate_rk":  ((0.09, 0.10, 0.12), (0.24, 0.26, 0.30), (0.42, 0.45, 0.50), (0.64, 0.68, 0.74)),
    "terracotta":((0.14, 0.07, 0.04), (0.42, 0.22, 0.12), (0.66, 0.40, 0.24), (0.86, 0.64, 0.46)),
    "kraft":     ((0.20, 0.14, 0.08), (0.48, 0.35, 0.20), (0.72, 0.58, 0.38), (0.90, 0.80, 0.60)),
    "newsprint": ((0.26, 0.25, 0.22), (0.52, 0.51, 0.47), (0.74, 0.73, 0.69), (0.92, 0.91, 0.87)),
    "plywood":   ((0.16, 0.11, 0.06), (0.44, 0.31, 0.16), (0.68, 0.52, 0.30), (0.88, 0.76, 0.52)),
    "cork":      ((0.15, 0.11, 0.07), (0.40, 0.30, 0.18), (0.63, 0.50, 0.32), (0.84, 0.74, 0.54)),
    "greyboard": ((0.19, 0.19, 0.18), (0.40, 0.40, 0.38), (0.58, 0.58, 0.55), (0.76, 0.76, 0.73)),
    "rust":      ((0.12, 0.06, 0.03), (0.38, 0.18, 0.08), (0.62, 0.34, 0.16), (0.84, 0.58, 0.34)),
    "verdigris": ((0.06, 0.12, 0.10), (0.16, 0.34, 0.29), (0.34, 0.58, 0.50), (0.62, 0.82, 0.74)),
    "ash_grey":  ((0.13, 0.13, 0.13), (0.32, 0.32, 0.32), (0.52, 0.52, 0.52), (0.74, 0.74, 0.74)),
    "soot_blk":  ((0.04, 0.04, 0.04), (0.14, 0.13, 0.13), (0.28, 0.27, 0.26), (0.48, 0.46, 0.44)),
    "mould":     ((0.08, 0.09, 0.06), (0.24, 0.26, 0.18), (0.44, 0.46, 0.34), (0.68, 0.70, 0.56)),
}



def _labels_from_field(f, cells, K):
    """Cells derived from the finish's OWN field.

    Audited 2026-09-01: five modules share the idiom `if lab is None:
    worley(seed+7, cells=150..170)`. The seed varies so the mosaic moves between
    finishes, but the generator and cell count do not — so every finish that
    reaches the fallback wears the same mosaic character, and because the palette
    index comes from the cell-meaned field, that mosaic IS the visible motif.
    243 of 585 finishes across the five shelves reached it.
    """
    import numpy as _np
    n = int(f.shape[0])
    q = _np.clip((K.pct(f) * 9.0).astype(_np.int64), 0, 8)
    step = max(2, int(round(n / max(_np.sqrt(max(cells, 1)), 1.0))))
    yy, xx = _np.mgrid[0:n, 0:n]
    warp = (_np.asarray(f, _np.float32) - 0.5) * step * 1.6
    gy = ((yy + warp) / step).astype(_np.int64)
    gx = ((xx - warp) / step).astype(_np.int64)
    return (q * _np.int64(1000003) + gy * _np.int64(7919) + gx).astype(_np.int32)

def R(name, chapter, palette, implies, bands, seed, stack, mix="sum",
      edge="chrome", r_spread=24.0, gamma=1.0, desc=""):
    """One paradox.

    `implies` is the material card that substance would really have — hessian is
    a rough dielectric, concrete is a rough dielectric, rust is a rough oxide.
    `bands` is what it is given instead. The gate checks that the two are a long
    way apart in the material cube, because that distance IS the finish.
    """
    return dict(name=name, chapter=chapter, palette=palette, implies=implies,
                bands=bands, seed=seed, stack=stack, mix=mix, edge=edge,
                r_spread=r_spread, gamma=gamma, desc=desc)


# Material sets a substance is given INSTEAD of its own. Each spans at least
# three material families, and each runs monotonically from rough to polished as
# the substance goes from shadow to highlight — so the spec still reads as the
# geometry of the thing, which is what makes the wrong material land as a shock
# rather than as noise.
B_MERCURY = (("frozen_metal", 0.22), ("sea_glass", 0.44), ("satin_chrome", 0.63),
             ("gloss_carbon", 0.81), ("mercury", 0.94), ("chrome", 1.01))
B_GLASS   = (("frozen_film", 0.22), ("galvanized", 0.44), ("sea_glass", 0.63),
             ("milk_glass", 0.79), ("gloss_carbon", 0.92), ("liquid_glaze", 1.01))
B_LIQUID  = (("anodized", 0.24), ("pearl", 0.46), ("gloss", 0.65),
             ("liquid_glaze", 0.82), ("candy", 0.94), ("candy_chrome", 1.01))
B_CARRIER = (("carrier_low", 0.22), ("milk_glass", 0.44), ("carrier_mid", 0.63),
             ("carrier_high", 0.81), ("razor", 0.93), ("mercury", 1.01))
B_PEARL   = (("frozen_film", 0.22), ("anodized", 0.44), ("milk_glass", 0.64),
             ("pearl", 0.82), ("spectraflame", 0.94), ("candy_chrome", 1.01))


_ROWS = [
    # ────────────────────────── ⬢ WOVEN (10) ───────────────────────────────
    R("Hessian Mercury", "woven", "hessian", "matte", B_MERCURY, 5101,
      [("braid", 1.0, dict(layers=96, shear=1.2)), ("cells", 0.8, dict(cells=168))],
      desc="Coarse jute sacking, thread for thread — machined out of a single block of mercury."),
    R("Denim Chrome", "woven", "denim", "vinyl", B_MERCURY, 5102,
      [("braid", 1.0, dict(layers=110, shear=2.0)), ("filaments", 0.8, dict(n=440, length=34))],
      desc="Twill you could count the picks on, and every one of them is a mirror."),
    R("Wool Glass", "woven", "wool", "clear_matte", B_GLASS, 5103,
      [("filaments", 1.0, dict(n=520, length=30, wander=0.5)), ("cells", 0.8, dict(cells=172))],
      desc="Carded wool with the surface tension of poured glass."),
    R("Corduroy Liquid", "woven", "corduroy", "matte", B_LIQUID, 5104,
      [("braid", 1.0, dict(layers=84, shear=0.9)), ("dunes", 0.8, dict(n=44))],
      desc="Wales running true down the panel, and each one is a standing wave of liquid."),
    R("Felt Carrier", "woven", "felt", "clear_matte", B_CARRIER, 5105,
      [("dendrite", 1.0, dict(seeds=1100)), ("cells", 0.85, dict(cells=176))],
      desc="Pressed fibre, no weave at all — and it thresholds under a floodlight like cut metal."),
    R("Canvas Pearl", "woven", "hessian", "matte", B_PEARL, 5106,
      [("honeycomb", 1.0, dict(cells=158)), ("filaments", 0.8, dict(n=1900, length=13, wander=0.7))],
      desc="Artist's canvas, sized and stretched, behaving like a tri-coat pearl."),
    R("Tweed Mirror", "woven", "wool", "eggshell", B_MERCURY, 5107,
      [("cells", 1.0, dict(cells=120)), ("braid", 0.85, dict(layers=96, shear=1.6))],
      desc="Flecked country cloth with the optics of a polished ingot."),
    R("Burlap Glaze", "woven", "hessian", "matte", B_GLASS, 5108,
      [("braid", 1.0, dict(layers=88, shear=1.0)), ("cells", 0.8, dict(cells=134))],
      desc="Open-weave sacking, glazed as though it had been through a kiln."),
    R("Knit Liquid", "woven", "denim", "matte", B_LIQUID, 5109,
      [("honeycomb", 1.0, dict(cells=150)), ("curl", 0.8, dict(scale=52, steps=16))],
      desc="Every loop of the knit intact, and the whole surface still moving."),
    R("Silk Carrier", "woven", "felt", "satin", B_CARRIER, 5110,
      [("curl", 1.0, dict(scale=46, steps=18)), ("cells", 0.85, dict(cells=174))],
      desc="Cloth caught mid-drape, made of a material that only exists after dark."),

    # ────────────────────────── ⬣ GROWN (10) ───────────────────────────────
    R("Moss Glass", "grown", "moss", "ceramic_matte", B_GLASS, 5201,
      [("dendrite", 1.0, dict(seeds=950)), ("cells", 0.85, dict(cells=170))],
      desc="Sphagnum, every frond resolved, cast in optical glass."),
    R("Lichen Mercury", "grown", "lichen", "clear_matte", B_MERCURY, 5202,
      [("percolate", 1.0, dict(cells=155, p=0.46)), ("dendrite", 0.85, dict(seeds=900))],
      desc="Crustose lichen spreading on rock, rendered as a liquid metal colony."),
    R("Bark Chrome", "grown", "bark", "matte", B_MERCURY, 5203,
      [("crack", 1.0, dict(cells=88, width=2.2)), ("dunes", 0.8, dict(n=36))],
      desc="Deep fissured bark you could put your fingers into, mirror-polished."),
    R("Leaf Liquid", "grown", "leaf", "ceramic_matte", B_LIQUID, 5204,
      [("dendrite", 1.0, dict(seeds=380, walkers=26000, steps=60)),
       ("cells", 0.85, dict(cells=166))],
      desc="Venation from midrib to margin, and the whole leaf is still pouring."),
    R("Hide Pearl", "grown", "hide", "eggshell", B_PEARL, 5205,
      [("cells", 1.0, dict(cells=110)), ("spall", 0.8, dict(cells=96))],
      desc="Full-grain leather with its pores intact, finished as a pearl coat."),
    R("Fur Carrier", "grown", "wool", "vinyl", B_CARRIER, 5206,
      [("filaments", 1.0, dict(n=620, length=26, wander=0.6)), ("cells", 0.85, dict(cells=178))],
      desc="Dense pelt lying one way, which under lights behaves like the Fractured rail."),
    R("Coral Glass", "grown", "verdigris", "ceramic_matte", B_GLASS, 5207,
      [("percolate", 1.0, dict(cells=150, p=0.44)), ("craters", 0.8, dict(n=1800, rmax=7.0))],
      desc="A calcified reef, still porous, and clear all the way through."),
    R("Root Mercury", "grown", "bark", "matte", B_MERCURY, 5208,
      [("dendrite", 1.0, dict(seeds=700, walkers=20000)), ("cells", 0.85, dict(cells=168))],
      desc="A root mat pulled out of the soil intact, every hair of it liquid metal."),
    R("Petal Liquid", "grown", "leaf", "ceramic_matte", B_LIQUID, 5209,
      [("curl", 1.0, dict(scale=48, steps=18)), ("cells", 0.85, dict(cells=160))],
      desc="Petal tissue with the light behaving as though the flower were poured."),
    R("Spore Pearl", "grown", "mould", "clear_matte", B_PEARL, 5210,
      [("cells", 1.0, dict(cells=140)), ("dendrite", 0.85, dict(seeds=1000))],
      desc="A fruiting mat gone velvet — and finished like a show car."),

    # ───────────────────────── ⬡ MINERAL (10) ──────────────────────────────
    R("Concrete Liquid", "mineral", "concrete", "matte", B_LIQUID, 5301,
      [("craters", 1.0, dict(n=2200, rmax=8.0)), ("cells", 0.85, dict(cells=165))],
      desc="Board-marked concrete with the aggregate showing, and it has not set."),
    R("Granite Mercury", "mineral", "granite", "ceramic_matte", B_MERCURY, 5302,
      [("cells", 1.0, dict(cells=120)), ("sparks", 0.8, dict(n=2400, life=22))],
      desc="Coarse-grained granite, every crystal visible, machined out of mercury."),
    R("Chalk Chrome", "mineral", "chalk", "ceramic_matte", B_MERCURY, 5303,
      [("spall", 1.0, dict(cells=142, lift=0.5)), ("craters", 0.8, dict(n=3200, rmax=4.0))],
      desc="Blackboard chalk — the most matte thing there is — polished to a mirror."),
    R("Slate Glass", "mineral", "slate_rk", "matte", B_GLASS, 5304,
      [("spall", 1.0, dict(cells=86, lift=0.66)), ("crack", 0.8, dict(cells=104, gen=1))],
      desc="Riven slate, split along its cleavage, and completely transparent."),
    R("Terracotta Carrier", "mineral", "terracotta", "ceramic_matte", B_CARRIER, 5305,
      [("polygons", 1.0, dict(cells=74)), ("craters", 0.8, dict(n=1900, rmax=7.0))],
      desc="Unglazed fired clay that ignites into the carrier the moment lights hit it."),
    R("Pumice Pearl", "mineral", "ash_grey", "void", B_PEARL, 5306,
      [("craters", 1.0, dict(n=2600, rmax=10.0)), ("craters", 0.7, dict(n=3400, rmax=4.0)),
       ("cells", 0.5, dict(cells=176))],
      desc="Volcanic foam, light enough to float, finished like a concours pearl."),
    R("Sandstone Liquid", "mineral", "kraft", "powder", B_LIQUID, 5307,
      [("bands", 1.0, dict(n=72, shear=2.3, vortex=17, turb=0.52)),
       ("craters", 0.8, dict(n=2600, rmax=4.5))],
      desc="Cross-bedded sandstone with every lamina readable, and it is flowing."),
    R("Basalt Mirror", "mineral", "slate_rk", "matte", B_MERCURY, 5308,
      [("polygons", 1.0, dict(cells=104, relief=0.7)), ("wrinkle", 0.8, dict(k=0.9, steps=12))],
      desc="Columnar basalt in plan view, each column a perfect mirror."),
    R("Gypsum Glass", "mineral", "chalk", "ceramic_matte", B_GLASS, 5309,
      [("filaments", 1.0, dict(n=420, length=48)), ("cells", 0.85, dict(cells=168))],
      desc="Fibrous gypsum — satin spar — taken all the way to optical clarity."),
    R("Grit Carrier", "mineral", "granite", "ceramic_matte", B_CARRIER, 5310,
      [("craters", 1.0, dict(n=2600, rmax=5.5)), ("cells", 0.85, dict(cells=175))],
      desc="Blasting grit at rest, which after dark stops behaving like a mineral at all."),

    # ────────────────────────── ⬠ MADE (10) ────────────────────────────────
    R("Kraft Chrome", "made", "kraft", "eggshell", B_MERCURY, 5401,
      [("filaments", 1.0, dict(n=2400, length=13, wander=0.75)), ("cells", 0.85, dict(cells=172))],
      desc="Unbleached kraft paper with the fibre lay visible, and it is solid chrome."),
    R("Corrugate Mercury", "made", "greyboard", "vinyl", B_MERCURY, 5402,
      [("braid", 1.0, dict(layers=72, shear=0.8)), ("cells", 0.85, dict(cells=166))],
      desc="Single-wall board with the flutes running true — poured, not folded."),
    R("Newsprint Glass", "made", "newsprint", "matte", B_GLASS, 5403,
      [("cells", 1.0, dict(cells=150)), ("filaments", 0.85, dict(n=2200, length=12, wander=0.7))],
      desc="Cheap paper stock, showing its screen, and clear as a lens."),
    R("Plywood Liquid", "made", "plywood", "matte", B_LIQUID, 5404,
      [("bands", 1.0, dict(n=104, shear=1.5, vortex=7, turb=0.34)),
       ("filaments", 0.7, dict(n=1500, length=26, wander=0.18))],
      desc="Rotary-cut veneer with the grain sweeping across it, and it has not stopped moving."),
    R("Cork Pearl", "made", "cork", "powder", B_PEARL, 5405,
      [("percolate", 1.0, dict(cells=205, p=0.52)), ("honeycomb", 0.7, dict(cells=170))],
      desc="Cellular cork, every cell open, finished as a three-stage pearl."),
    R("Greyboard Carrier", "made", "greyboard", "clear_matte", B_CARRIER, 5406,
      [("cells", 1.0, dict(cells=130)), ("dendrite", 0.85, dict(seeds=950))],
      desc="Book board. The dullest material in any workshop, and it fractures under light."),
    R("Sawdust Mirror", "made", "plywood", "matte", B_MERCURY, 5407,
      [("cells", 1.0, dict(cells=145)), ("sparks", 0.8, dict(n=2600, life=20))],
      desc="Swarf and dust from the saw, every particle a facet."),
    R("Blotter Glass", "made", "newsprint", "clear_matte", B_GLASS, 5408,
      [("filaments", 1.0, dict(n=2600, length=11, wander=0.8)), ("dendrite", 0.6, dict(seeds=1200))],
      desc="Absorbent blotting stock, which drinks light and somehow also transmits it."),
    R("Chipboard Liquid", "made", "cork", "powder", B_LIQUID, 5409,
      [("spall", 1.0, dict(cells=92)), ("cells", 0.85, dict(cells=168))],
      desc="Pressed chip and resin, every flake showing, in the middle of pouring."),
    R("Card Pearl", "made", "kraft", "vinyl", B_PEARL, 5410,
      [("wrinkle", 1.0, dict(k=1.15, steps=15, scale=150)),
       ("filaments", 0.8, dict(n=2000, length=12, wander=0.7))],
      desc="Folded card stock with the crease still crisp, sprayed like a show finish."),

    # ───────────────────────── ⬟ RUINED (10) ───────────────────────────────
    R("Rust Mirror", "ruined", "rust", "patina", B_MERCURY, 5501,
      [("percolate", 1.0, dict(cells=138, p=0.50)), ("spall", 0.85, dict(cells=94))],
      desc="Scaling iron oxide lifting off in plates, and every plate is a mirror."),
    R("Verdigris Glass", "ruined", "verdigris", "ceramic_matte", B_GLASS, 5502,
      [("dendrite", 1.0, dict(seeds=1000)), ("crack", 0.85, dict(cells=106))],
      desc="Copper carbonate crusting a roof, and you can see straight through it."),
    R("Ash Chrome", "ruined", "ash_grey", "void", B_MERCURY, 5503,
      [("dendrite", 1.0, dict(seeds=1300)), ("cells", 0.85, dict(cells=176))],
      desc="Cold wood ash. Nothing on earth reflects less, and this reflects everything."),
    R("Soot Pearl", "ruined", "soot_blk", "void", B_PEARL, 5504,
      [("dendrite", 1.0, dict(seeds=700, walkers=22000)), ("cells", 0.85, dict(cells=172))],
      desc="Carbon black, the deadest pigment there is, laid down as a pearl."),
    R("Mould Liquid", "ruined", "mould", "ceramic_matte", B_LIQUID, 5505,
      [("percolate", 1.0, dict(cells=162, p=0.44)), ("dendrite", 0.85, dict(seeds=1000))],
      desc="A colony spreading across a damp wall, and the whole wall is running."),
    R("Flake Carrier", "ruined", "rust", "patina", B_CARRIER, 5506,
      [("spall", 1.0, dict(cells=88, lift=0.7)), ("cells", 0.85, dict(cells=168))],
      desc="Failing paint curling off the substrate, each flake carrying the Fractured rail."),
    R("Corrosion Glass", "ruined", "verdigris", "ceramic_matte", B_GLASS, 5507,
      [("craters", 1.0, dict(n=2400, rmax=7.0)), ("percolate", 0.8, dict(cells=186, p=0.48))],
      desc="Pitting corrosion eating into the metal, and each pit is a lens."),
    R("Cinder Mirror", "ruined", "soot_blk", "void", B_MERCURY, 5508,
      [("spall", 1.0, dict(cells=104, lift=0.72)), ("percolate", 0.6, dict(cells=118, p=0.52))],
      desc="Burnt-out clinker from the bottom of a grate, polished like jewellery."),
    R("Decay Pearl", "ruined", "mould", "clear_matte", B_PEARL, 5509,
      [("dendrite", 1.0, dict(seeds=1150)), ("wrinkle", 0.75, dict(k=1.0, steps=13))],
      desc="Rot doing its work, finished to a standard the object never had when new."),
    R("Weathered Liquid", "ruined", "ash_grey", "clear_matte", B_LIQUID, 5510,
      [("bands", 1.0, dict(n=88, shear=1.1, vortex=5, turb=0.30)),
       ("filaments", 0.75, dict(n=1800, length=30, wander=0.14))],
      desc="Timber silvered by forty years of weather, and it is pouring off the panel."),
]


CHAP_WORD = {"woven": "Woven", "grown": "Grown", "mineral": "Mineral",
             "made": "Made", "ruined": "Ruined"}


def title(fid):
    """Picker label. Chapter-prefixed so the shelf sorts itself into the five
    arcs, per the owner's FLAMES instruction ("Cinder: Clinker Crust")."""
    d = PARADIGM[fid]
    return "%s: %s" % (CHAP_WORD[d["chapter"]], d["name"])


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_")


PARADIGM = {_fid(r["name"]): r for r in _ROWS}

# ── BANDING, CHOSEN PER FINISH ON MEASUREMENT (2026-09-01) ────────────────
# Quantile bands give every card real area (median 9 distinct spec materials
# on this shelf); linear tracks a value-skewed field better. Both are owner
# requirements, so each finish is measured both ways and takes quantile unless
# quantile cannot follow the paint. Quantile wins for 35 of 50.
# Per-finish spec composition, MEASURED 2026-09-02 (bands x chips sweep at
# 1024, table in _rebuild/pdg_speckw.json). Quantile banding is preferred (every
# card gets real area) and chips are preferred (a real second material at
# 8-32px); each is given up only where it cannot follow the paint. Dense
# textures needed chips=0: 14px confetti of the neighbour card decorrelates a
# texture that is busy everywhere (canvas FOLLOW 0.12 -> 0.54, corrugate
# 0.12 -> 0.29 from chips alone).
_PDG_SPECKW = {
    "pdg_hessian_mercury": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "pdg_denim_chrome": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "pdg_wool_glass": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "pdg_corduroy_liquid": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_felt_carrier": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_canvas_pearl": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_tweed_mirror": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "pdg_burlap_glaze": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_knit_liquid": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_silk_carrier": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_moss_glass": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_lichen_mercury": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_bark_chrome": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "pdg_leaf_liquid": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_hide_pearl": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_fur_carrier": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_coral_glass": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "pdg_root_mercury": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "pdg_petal_liquid": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "pdg_spore_pearl": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "pdg_concrete_liquid": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_granite_mercury": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "pdg_chalk_chrome": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "pdg_slate_glass": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_terracotta_carrier": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "pdg_pumice_pearl": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "pdg_sandstone_liquid": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_basalt_mirror": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "pdg_gypsum_glass": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "pdg_grit_carrier": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "pdg_kraft_chrome": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_corrugate_mercury": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "pdg_newsprint_glass": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_plywood_liquid": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_cork_pearl": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_greyboard_carrier": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "pdg_sawdust_mirror": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "pdg_blotter_glass": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "pdg_chipboard_liquid": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "pdg_card_pearl": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "pdg_rust_mirror": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_verdigris_glass": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "pdg_ash_chrome": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "pdg_soot_pearl": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_mould_liquid": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_flake_carrier": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_corrosion_glass": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "pdg_cinder_mirror": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "pdg_decay_pearl": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "pdg_weathered_liquid": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
}
for _f, _kw in _PDG_SPECKW.items():
    if _f in PARADIGM:
        PARADIGM[_f].setdefault("spec_kw", {}).update(_kw)


def build(stack, shape, seed, mix="sum"):
    acc, lab, lab_w, wsum = None, None, -1.0, 0.0
    for i, (name, wgt, kw) in enumerate(stack):
        f, l = _STRUCTS[name](shape, seed + 101 * i, dict(kw))
        if l is not None and float(wgt) > lab_w:
            lab, lab_w = l, float(wgt)
        if acc is None:
            acc, wsum = f * float(wgt), float(wgt)
        elif mix == "max":
            acc = np.maximum(acc, f * float(wgt))
        else:
            acc = acc + f * float(wgt)
            wsum += float(wgt)
    if mix == "sum" and wsum > 0:
        acc = acc / wsum
    return CK.pct(acc), lab


@lru_cache(maxsize=8)
def _field(fid):
    """The finish's OWN construction, chosen from its substance.

    SPB-105 / owner 2026-09-01: "YOU BUILD THE FINISHES FIRST THEN SPEC TO THE
    FINISHES." This shelf had 27 constructions for 50 finishes (one used eight
    times), and the previous pass authored fifty distinct spec decks on top of
    that duplicated paint — which is the wrong order. paradigm_design_2026 now
    names one construction per SUBSTANCE, zero reuse (hessian is a crosshatch
    weave, denim a 3/1 twill, leaf venation is flow accumulation, terracotta an
    annealing crack, basalt columnar jointing), and the deck in paradigm_decks
    follows THAT.

    The recipe's old `stack` is left in place for provenance but is no longer
    what the paint is built from.
    """
    from engine.expansions import paradigm_design_2026 as PDS
    from engine.expansions import nightshift_forms_2026 as NF
    from engine.paint_v2 import era_kit_2026 as EK

    d = PARADIGM[fid]
    form, params, kind = PDS.form_for(fid)
    fn = getattr(EK, form[3:]) if form.startswith("ek:") else getattr(NF, form)
    out = fn((GEN, GEN), d["seed"], **params)
    f, lab = out if isinstance(out, tuple) else (out, None)
    f = np.asarray(f, np.float32)
    # keyed fine detail rides the construction; never a uniform grain layer
    f = NF.compose_form(f, d["seed"], kind=kind,
                        amount=float(d.get("detail", PDS.DETAIL.get(PDS.substance(fid), 0.40))),
                        res=GEN)
    # PLACES. Every gold standard has zones where the texture is busy and zones
    # where it is calm (paint-envelope variation 0.19-0.30 across the canvas).
    # A texture equally busy everywhere measured 0.09-0.12 here, and FOLLOW
    # could not be judged on it at all (bark -0.13, canvas 0.00, corrugate 0.07)
    # because the spec's detail has nowhere in particular to be. Real bark, real
    # canvas, real corrugate have worn zones and intact zones too. A slow field
    # varies the construction's CONTRAST across the car; never its geometry.
    slow = np.asarray(CK.fbm((GEN, GEN), d["seed"] + 7, octaves=(5, 10, 20),
                             weights=(1.0, 0.6, 0.35)), np.float32)
    slow = (slow - float(slow.min())) / max(float(slow.max() - slow.min()), 1e-6)
    m = float(f.mean())
    f = np.clip(m + (f - m) * (0.50 + 1.0 * slow), 0, 1).astype(np.float32)
    # MACRO damage authored per substance in paradigm_design_2026.MACRO.
    if PDS.MACRO.get(PDS.substance(fid)) == "crush":
        cr = np.asarray(CK.fbm((GEN, GEN), d["seed"] + 11, octaves=(4, 8, 16),
                               weights=(1.0, 0.5, 0.25)), np.float32)
        cr = (cr - float(cr.min())) / max(float(cr.max() - cr.min()), 1e-6)
        cr = np.clip((cr - 0.42) / 0.25, 0, 1)          # ~half the sheet crushed, soft edges (0.55: FOLLOW 0.184)
        flat = (cv2.GaussianBlur(f, (0, 0), GEN / 2048.0 * 6.0) if cv2 is not None
                else np.full_like(f, float(f.mean())))
        f = (f * (1.0 - 0.95 * cr) + flat * 0.95 * cr).astype(np.float32)
    # FINE: a second, smaller construction nested inside the first (intricacy;
    # owner 2026-09-02). Keyed to the macro's edges so it sits on the design.
    fine = PDS.FINE.get(PDS.substance(fid))
    if fine is not None:
        form2, params2, w = fine
        fn2 = getattr(EK, form2[3:]) if form2.startswith("ek:") else getattr(NF, form2)
        out2 = fn2((GEN, GEN), d["seed"] + 41, **params2)
        f2 = np.asarray(out2[0] if isinstance(out2, tuple) else out2, np.float32)
        f2 = (f2 - float(f2.min())) / max(float(f2.max() - f2.min()), 1e-6)
        gy, gx = np.gradient(f)
        key = np.hypot(gx, gy)
        key = key / max(float(np.percentile(key, 98)), 1e-6)
        key = 0.45 + 0.55 * np.clip(key, 0, 1)
        f = np.clip(f * (1.0 - w) + f2 * w * key + f * w * (1.0 - key), 0, 1).astype(np.float32)
    # Whether the construction supplied its own regions (bricks, columns,
    # plates, cells) or we had to invent a label grid for the spec's chips.
    _LAB_OWN[fid] = lab is not None
    if lab is None:
        lab = _labels_from_field(f, 170, CK)
    return f, lab


_LAB_OWN = {}


@lru_cache(maxsize=6)
def _art(fid):
    d = PARADIGM[fid]
    f, lab = _field(fid)
    f = CK.upscale(f, WORK)
    lab = CK.upscale(lab, WORK)
    pal = np.asarray(P[d["palette"]], np.float32)
    # cell_mean over an INVENTED 170-cell label grid turns every f-only
    # construction (crinkle, moire, scanline, moire_beat, rosensweig...) into
    # the same 12px mosaic: fine detail averaged away inside cells, car-band
    # energy coming from cell edges that are everywhere at once. Measured
    # 2026-09-02: bark FOLLOW 0.018 and NO compose lever moved it (13 tried,
    # -0.03..0.07), because the artwork the spec was following was the grid,
    # not the bark. Cell means are only meaningful when the construction
    # itself drew the cells (bricks, basalt columns, spall plates).
    fc = CK.cell_mean(f, lab) if _LAB_OWN.get(fid, True) else f
    t = np.clip(CK.pct(fc) ** float(d.get("gamma", 1.0)), 0, 1)
    idx = np.clip((t * (len(pal) - 1)).astype(np.int32), 0, len(pal) - 2)
    frac = np.clip(t * (len(pal) - 1) - idx, 0, 1)[..., None]
    art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
    # relief = how much of the construction's own fine field survives on top
    # of the cell tone. 0.52 is the historic default; columnar/plated forms
    # whose cell_mean flattens their ridge detail can ask for more.
    from engine.expansions import paradigm_design_2026 as PDS
    relief = float(d.get("relief", PDS.RELIEF.get(PDS.substance(fid), 0.52)))
    art = art * ((1.0 - relief / 2.0) + relief * f)[..., None]
    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(art, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        # deliberately restrained: the substance has to stay believable, because
        # the paradox only lands if you accept the material first
        hsv[..., 0] = np.mod(hsv[..., 0] + (CK._h1(lab, 97) - 0.5) * 12.0, 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.88 + 0.22 * CK._h1(lab, 149)), 0, 1)
        art = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        g = CK.fbm((WORK, WORK), d["seed"] + 3, octaves=(128, 256, 512),
                   weights=(0.6, 1.0, 0.8)) - 0.5
        art = art * (1.0 + g * 0.24)[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    """The finish's own material story, laid on its own artwork.

    SPB-105 / owner 2026-09-01: *"If it says MINERAL: CHALK CHROME then by GOD
    it should make you instantly feel like this finish IS chalk chrome."*

    pdg_chalk_chrome was inside a group of ELEVEN finishes dealing an identical
    material set — the deck came from `d["bands"]`, which was written per
    IMPOSED MATERIAL, so every *_mercury, *_chrome and *_mirror card shared one
    band list. Measured story_ratio 0.38 with 41/50 failing the law.

    The deck now comes from BOTH halves of the name (paradigm_decks_2026): the
    substance's honest materials at the rough end, the imposed material at the
    sharp end. That is the shelf's whole concept — a finish arguing with itself
    — and it makes all fifty distinct. Layout is composed against the RENDERED
    PAINT so the material boundaries sit on the artwork's tonal boundaries.
    """
    from engine.paint_v2 import spec_story as ST
    from engine.expansions import paradigm_decks_2026 as PD

    d = PARADIGM[fid]
    cards, edge = PD.deck_for(fid)
    f, lab = _field(fid)
    f = CK.upscale(f, res)
    lab = CK.upscale(lab, res) if lab is not None else None
    art = _art(fid)
    if cv2 is not None and art.shape[0] != res:
        art = cv2.resize(np.asarray(art, np.float32), (res, res),
                         interpolation=cv2.INTER_LINEAR)
    # spec_story's micro="paint" (spec fine layer = paint's own car-band
    # detail) was wired here 2026-09-02 and MEASURED: law failures 9 -> 16, bark
    # FOLLOW 0.02 -> -0.13. On a texture equally busy everywhere the envelope
    # axis has nothing to correlate, and riding the paint's bandpass only
    # exposes the roughness card's anti-correlation with paint brightness. So
    # the default micro stays; the finish gets "places" in _field instead.
    kw = dict()
    kw.update(d.get("spec_kw", {}))
    return ST.compose(f, cards, seed=d["seed"], res=res, lab=lab,
                      edge=edge, art=art, **kw)


def _mk(fid):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw) and cv2 is not None:
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = _art(fid)
        if cv2 is not None:
            art = cv2.resize(art, (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw) and cv2 is not None:
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        spec = _spec_at(fid, fw)
        mm = np.clip(m2, 0.0, 1.0)[..., None]
        return (spec.astype(np.float32) * mm).clip(0, 255).astype(np.uint8)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    for fid in PARADIGM:
        entry = _mk(fid)
        for reg in regs:
            try:
                reg[fid] = entry
            except Exception:
                pass
    return "%d paradoxes across %d chapters" % (len(PARADIGM), len(CHAPTERS))
