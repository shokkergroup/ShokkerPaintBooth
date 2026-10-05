# -*- coding: utf-8 -*-
"""🌌 FRACTURED COSMOS — the 2026-08-31 rebuild. 60 → 60, all of them off-planet.

Owner: the Fractured categories must be *unique, cool, and live up to what they
say they do*. COSMOS says off-planet, space, UFO.

WHAT WAS THERE (all 60 names read off the shipped catalog):

  * **20 genuinely on-theme** — Abduction Shafts, Alien Circuit, Crop Circle,
    Saucer Alloy, Tractor Beam, Wormhole…
  * **20 that are a COLOUR GRID** — Cyan Drift / Cyan Dust Lane / Cyan
    Shockwave / Cyan Spiral, then the same four structures again in gilded,
    magenta, teal and violet. Five colours by four structures. This is the
    pattern the owner has rejected by name: a recolor is not a finish.
  * **20 with nothing to do with space at all** — Holographic Foil, Oil-Slick
    Prism Shatter, Rainbow Truchet, Kaleidoscope Tiles, Spectral Marble Flow,
    Dichroic Bands. Iridescence is a lovely effect and it is not outer space.

So two thirds of the category did not live up to its name.

THE REBUILD: five chapters of twelve, each a different KIND of off-planet thing,
so the arc runs from the craft that visits us out to the physics that would kill
us and back to the hardware we actually send up.

  🛸 CONTACT    the craft and its makers — hull, glyphs, beams, crop geometry
  🪐 WORLDS     surfaces you could stand on — regolith, ice, dunes, gas bands
  ✦ DEEP FIELD  what the telescope sees — nebulae, clusters, dust lanes
  ☄ EVENT       violent physics — horizons, lensing, jets, remnants
  ⬡ VESSEL      what we build to survive it — shields, foil, sails, radiators

No colour grid: every finish names its own palette drawn from what that object
actually is, and no two share a structure stack.
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

ID_PREFIX = "cos_"
GROUP = "🌌 FRACTURED COSMOS"
GEN = 1024
WORK = 1152

CHAPTERS = {"contact": "🛸 CONTACT", "worlds": "🪐 WORLDS",
            "deep": "✦ DEEP FIELD", "event": "☄ EVENT", "vessel": "⬡ VESSEL"}

# Each chapter has its own material grammar, from the Spec Guide deck: what a
# craft is made of is not what a nebula is made of.
CHAPTER_SPEC = {
    # machined alien alloy: metal ground, mirror seams, carrier where it powers up
    "contact": dict(bands=(("gloss_carbon", 0.22), ("gunmetal", 0.44),
                           ("brushed_ti", 0.64), ("satin_chrome", 0.82),
                           ("carrier_mid", 0.94), ("chrome", 1.01)),
                    edge="chrome", edge_max=0.06, r_spread=24.0),
    # planetary surface: dust, rock, ice, with mineral glints
    "worlds":  dict(bands=(("void", 0.24), ("ceramic_matte", 0.46),
                           ("bead_blast", 0.66), ("patina", 0.84),
                           ("frozen_metal", 0.95), ("satin_chrome", 1.01)),
                    edge="dark_chrome", edge_max=0.05, r_spread=34.0),
    # gas and light: almost no metal, and the coat carries the glow
    "deep":    dict(bands=(("void", 0.30), ("flat_black", 0.52),
                           ("satin", 0.70), ("semi_gloss", 0.85),
                           ("pearl", 0.95), ("candy_chrome", 1.01)),
                    edge="carrier_mid", edge_max=0.05, r_spread=22.0),
    # violent physics: the carrier rail belongs here, with mirror at the shock
    "event":   dict(bands=(("void", 0.26), ("gloss_carbon", 0.46),
                           ("carrier_low", 0.64), ("carrier_mid", 0.80),
                           ("carrier_high", 0.92), ("mercury", 1.01)),
                    edge="chrome", edge_max=0.07, r_spread=18.0, cc_offset=5),
    # spacecraft hardware: foil, ceramic, honeycomb, gold mirror
    "vessel":  dict(bands=(("gloss_carbon", 0.20), ("ceramic_matte", 0.42),
                           ("milk_glass", 0.60), ("spectraflame", 0.78),
                           ("dark_chrome", 0.92), ("mercury", 1.01)),
                    edge="chrome", edge_max=0.06, r_spread=26.0),
}

_STRUCTS = {
    "starfield": lambda sh, sd, k: (CK.starfield(sh, sd, **k), None),
    "craters":   lambda sh, sd, k: (CK.craters(sh, sd, **k), None),
    "bands":     lambda sh, sd, k: (CK.bands(sh, sd, **k), None),
    "lens":      lambda sh, sd, k: (CK.lens(sh, sd, **k), None),
    "rings":     lambda sh, sd, k: (CK.rings(sh, sd, **k), None),
    "crinkle":   lambda sh, sd, k: (CK.crinkle(sh, sd, **k), None),
    "honeycomb": lambda sh, sd, k: CK.honeycomb(sh, sd, **k),
    "jet":       lambda sh, sd, k: (CK.jet(sh, sd, **k), None),
    "shock":     lambda sh, sd, k: (CK.shockshell(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (CK.dunes(sh, sd, **k), None),
    "polygons":  lambda sh, sd, k: CK.polygons(sh, sd, **k),
    "glyphs":    lambda sh, sd, k: (CK.glyphs(sh, sd, **k), None),
    "hull":      lambda sh, sd, k: CK.hull(sh, sd, **k),
    # borrowed, because a good primitive is a good primitive
    "cells":     lambda sh, sd, k: CK.worley(sh, sd, **k),
    "curl":      lambda sh, sd, k: (CK.curl(sh, sd, **k), None),
    "filaments": lambda sh, sd, k: (CK.filaments(sh, sd, **k), None),
    "dendrite":  lambda sh, sd, k: (CK.dla(sh, sd, **k), None),
    "percolate": lambda sh, sd, k: CK.percolate(sh, sd, **k),
    "spall":     lambda sh, sd, k: CK.spall(sh, sd, **k),
    "crack":     lambda sh, sd, k: CK.anneal_crack(sh, sd, **k),
    "braid":     lambda sh, sd, k: (CK.kh_braid(sh, sd, **k), None),
    "fingers":   lambda sh, sd, k: (CK.rt_fingers(sh, sd, **k), None),
    "sparks":    lambda sh, sd, k: (CK.sparks(sh, sd, **k), None),
    "wrinkle":   lambda sh, sd, k: (CK.wrinkle(sh, sd, **k), None),
}


def build(stack, shape, seed, mix="sum"):
    acc, lab, wsum = None, None, 0.0
    for i, (name, wgt, kw) in enumerate(stack):
        f, l = _STRUCTS[name](shape, seed + 101 * i, dict(kw))
        if l is not None and lab is None:
            lab = l
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


def R(name, chapter, palette, seed, stack, mix="sum", tiers=8, gamma=1.0,
      spec=None, desc=""):
    """One finish: what it IS (chapter), what colour it is (palette drawn from
    the real object), and the geometry that makes it."""
    return dict(name=name, chapter=chapter, palette=palette, seed=seed,
                stack=stack, mix=mix, tiers=tiers, gamma=gamma,
                spec=spec or {}, desc=desc)


# palettes are named after the thing, never after a colour
P = {
    "hull_alloy":  ((0.14, 0.16, 0.19), (0.34, 0.38, 0.42), (0.58, 0.63, 0.68), (0.80, 0.84, 0.88)),
    "abduct":      ((0.03, 0.07, 0.05), (0.10, 0.36, 0.20), (0.35, 0.85, 0.45), (0.78, 1.00, 0.82)),
    "xeno_violet": ((0.06, 0.03, 0.10), (0.28, 0.12, 0.44), (0.55, 0.30, 0.85), (0.85, 0.70, 1.00)),
    "reactor":     ((0.04, 0.05, 0.09), (0.10, 0.30, 0.50), (0.25, 0.65, 0.95), (0.80, 0.95, 1.00)),
    "regolith":    ((0.10, 0.09, 0.08), (0.28, 0.26, 0.24), (0.46, 0.43, 0.40), (0.66, 0.63, 0.59)),
    "mars":        ((0.12, 0.06, 0.04), (0.38, 0.18, 0.10), (0.62, 0.33, 0.20), (0.82, 0.58, 0.42)),
    "europa":      ((0.16, 0.20, 0.26), (0.46, 0.56, 0.66), (0.72, 0.82, 0.90), (0.92, 0.97, 1.00)),
    "io":          ((0.14, 0.11, 0.04), (0.55, 0.42, 0.08), (0.86, 0.72, 0.18), (0.98, 0.92, 0.62)),
    "jupiter":     ((0.16, 0.11, 0.08), (0.48, 0.34, 0.24), (0.74, 0.58, 0.42), (0.92, 0.84, 0.72)),
    "titan":       ((0.08, 0.06, 0.04), (0.30, 0.22, 0.10), (0.55, 0.42, 0.18), (0.78, 0.64, 0.32)),
    "salt":        ((0.20, 0.20, 0.22), (0.52, 0.52, 0.54), (0.76, 0.76, 0.78), (0.95, 0.95, 0.96)),
    "basalt":      ((0.06, 0.06, 0.07), (0.18, 0.18, 0.20), (0.32, 0.32, 0.35), (0.50, 0.50, 0.54)),
    "emission":    ((0.05, 0.02, 0.06), (0.40, 0.08, 0.22), (0.85, 0.25, 0.40), (1.00, 0.70, 0.72)),
    "reflection":  ((0.03, 0.05, 0.12), (0.10, 0.24, 0.52), (0.30, 0.52, 0.88), (0.75, 0.88, 1.00)),
    "dust_lane":   ((0.04, 0.03, 0.03), (0.18, 0.13, 0.10), (0.42, 0.32, 0.24), (0.70, 0.58, 0.44)),
    "cluster":     ((0.03, 0.03, 0.06), (0.24, 0.24, 0.34), (0.62, 0.62, 0.72), (0.98, 0.96, 0.90)),
    "planetary":   ((0.03, 0.06, 0.07), (0.08, 0.36, 0.38), (0.30, 0.78, 0.72), (0.85, 1.00, 0.94)),
    "horizon":     ((0.01, 0.01, 0.02), (0.22, 0.12, 0.04), (0.72, 0.42, 0.08), (1.00, 0.86, 0.55)),
    "magnetar":    ((0.04, 0.02, 0.08), (0.30, 0.08, 0.40), (0.72, 0.24, 0.78), (1.00, 0.78, 0.98)),
    "shock":       ((0.03, 0.05, 0.06), (0.16, 0.34, 0.42), (0.50, 0.78, 0.86), (0.94, 0.98, 1.00)),
    "kilonova":    ((0.06, 0.03, 0.03), (0.36, 0.14, 0.08), (0.78, 0.46, 0.16), (1.00, 0.88, 0.62)),
    "mli_gold":    ((0.12, 0.08, 0.02), (0.52, 0.36, 0.08), (0.86, 0.66, 0.20), (1.00, 0.92, 0.66)),
    "shield_char": ((0.05, 0.04, 0.04), (0.20, 0.16, 0.14), (0.42, 0.32, 0.26), (0.66, 0.52, 0.40)),
    "radiator":    ((0.24, 0.25, 0.27), (0.58, 0.60, 0.63), (0.82, 0.84, 0.87), (0.97, 0.98, 1.00)),
    "sail":        ((0.16, 0.17, 0.20), (0.48, 0.52, 0.58), (0.78, 0.82, 0.88), (0.96, 0.98, 1.00)),
    "cryo":        ((0.14, 0.18, 0.22), (0.42, 0.54, 0.64), (0.70, 0.82, 0.90), (0.94, 0.98, 1.00)),
}

_ROWS = [
    # ───────────────────────── 🛸 CONTACT (12) ──────────────────────────────
    R("Saucer Alloy", "contact", "hull_alloy", 3101,
      [("hull", 1.0, dict(panels=84, seam=1.3)), ("braid", 0.5, dict(layers=96, shear=1.4))],
      desc="Spun machined hull: concentric turn-rings still on the alloy from the lathe that made it."),
    R("Hull Plating", "contact", "hull_alloy", 3102,
      [("hull", 1.0, dict(panels=70, rivets=0.8)), ("spall", 0.5, dict(cells=100))],
      desc="Irregular alien plates, recessed seams, fastener rows, and no two panels polished alike."),
    R("Glyph Script", "contact", "xeno_violet", 3103,
      [("glyphs", 1.0, dict(n=640, size=14.0)), ("cells", 0.5, dict(cells=150))],
      desc="Angular xeno writing — strokes cluster into words, so it reads as language, not scatter."),
    R("Crop Geometry", "contact", "abduct", 3104,
      [("rings", 0.55, dict(systems=170, n=5)), ("dunes", 1.0, dict(n=40)),
       ("cells", 1.9, dict(cells=150))],
      desc="Flattened agroglyph rings laid across a standing crop that all leans one way."),
    R("Abduction Column", "contact", "abduct", 3105,
      [("jet", 1.0, dict(n=280, spread=0.008)), ("sparks", 1.0, dict(n=2200, life=30)),
       ("cells", 1.0, dict(cells=160))],
      mix="max", desc="A leaning forest of light columns with the dust caught turning inside them."),
    R("Tractor Well", "contact", "abduct", 3106,
      [("rings", 0.55, dict(systems=150, n=6, tilt=0.7)), ("curl", 1.0, dict(scale=64)),
       ("cells", 1.9, dict(cells=150))],
      desc="Beam wells pulsing tight concentric pull-rings into whatever is underneath."),
    R("Bio-Mech Chitin", "contact", "xeno_violet", 3107,
      [("cells", 1.0, dict(cells=104)), ("filaments", 0.7, dict(n=380, length=40))],
      desc="Interlocking chitin plate and the vein bundles running between them. Grown, not built."),
    R("Reactor Lattice", "contact", "reactor", 3108,
      [("honeycomb", 1.0, dict(cells=92)), ("sparks", 0.55, dict(n=2400, life=24))],
      mix="max", desc="An isometric strut scaffold with the containment charge running the struts."),
    R("Beacon Array", "contact", "reactor", 3109,
      [("cells", 1.0, dict(cells=120)), ("sparks", 0.7, dict(n=2600, life=26))],
      mix="max", desc="Emitter grid mid-broadcast: every cell on its own phase of the same signal."),
    R("Cloaking Field", "contact", "hull_alloy", 3110,
      [("curl", 1.0, dict(scale=42, steps=16)), ("crinkle", 0.6, dict(scale=140))],
      desc="The hull half-there: a refractive skin that bends the background instead of hiding it."),
    R("Probe Skin", "contact", "hull_alloy", 3111,
      [("craters", 1.0, dict(n=2200, rmax=7.0)), ("hull", 0.6, dict(panels=90))],
      desc="Sensor pits and apertures sunk flush into a plated skin that has been out there a while."),
    R("Signal Bloom", "contact", "reactor", 3112,
      [("shock", 0.55, dict(n=320)), ("filaments", 1.0, dict(n=300, length=36)),
       ("cells", 1.9, dict(cells=155))],
      desc="A transmission leaving: expanding wavefronts stacked over the antenna that threw them."),

    # ───────────────────────── 🪐 WORLDS (12) ───────────────────────────────
    R("Regolith", "worlds", "regolith", 3201,
      [("craters", 1.0, dict(n=2800)), ("dendrite", 0.5, dict(seeds=900))],
      desc="Four billion years of impact gardening: dust turned over so often it has no bedrock left."),
    R("Crater Field", "worlds", "regolith", 3202,
      [("craters", 1.0, dict(n=1500, rmax=12.0, rim=0.8)), ("spall", 0.55, dict(cells=90))],
      desc="Big enough to have rims and ejecta blankets, and each one has been hit again since."),
    R("Ice Moon", "worlds", "europa", 3203,
      [("crack", 1.0, dict(cells=96, width=1.6)), ("filaments", 0.6, dict(n=340, length=52))],
      desc="A shell of ice cracked and re-frozen so many times the lines cross their own history."),
    R("Sulfur Volcanics", "worlds", "io", 3204,
      [("percolate", 1.0, dict(cells=160, p=0.44)), ("curl", 0.6, dict(scale=60))],
      desc="Sulfur flows in every allotrope colour, laid down and buried on a world that never stops."),
    R("Gas Giant Bands", "worlds", "jupiter", 3205,
      [("bands", 1.0, dict(n=62, vortex=40)), ("curl", 0.5, dict(scale=56))],
      desc="Zonal flow: belts running the opposite way to their neighbours, with storms caught between."),
    R("Storm Oval", "worlds", "jupiter", 3206,
      [("bands", 1.0, dict(n=48, vortex=64)), ("fingers", 0.6, dict(n=120))],
      desc="An anticyclone that has outlived every telescope pointed at it, kept fed by the shear."),
    R("Dune Sea", "worlds", "mars", 3207,
      [("dunes", 1.0, dict(n=40)), ("craters", 0.5, dict(n=1600, rmax=6.0))],
      desc="Barchan dunes all marching the same way because one wind has had the whole planet to itself."),
    R("Salt Flat", "worlds", "salt", 3208,
      [("polygons", 1.0, dict(cells=76)), ("crack", 0.5, dict(cells=110, width=1.4))],
      desc="Evaporite polygons: the floor of a sea that left, cracked into plates as it dried."),
    R("Basalt Plain", "worlds", "basalt", 3209,
      [("polygons", 1.0, dict(cells=62, relief=0.7)), ("wrinkle", 0.6, dict(k=0.9, steps=12))],
      desc="Flood basalt with wrinkle ridges — a lava ocean that cooled and then shrugged."),
    R("Methane Lake", "worlds", "titan", 3210,
      [("curl", 1.0, dict(scale=52, steps=18)), ("filaments", 0.55, dict(n=280, length=48))],
      desc="Dark hydrocarbon under an orange haze, with a shoreline that rain keeps redrawing."),
    R("Ring Shadow", "worlds", "jupiter", 3211,
      [("bands", 1.0, dict(n=70)), ("rings", 0.6, dict(systems=120, n=6))],
      desc="The ring system printing its own gaps onto the cloud deck below it."),
    R("Terminator", "worlds", "regolith", 3212,
      [("craters", 1.0, dict(n=2400, rim=0.9)), ("dunes", 0.5, dict(n=28))],
      desc="The line where the sun is setting: every crater rim throwing a shadow the length of itself."),

    # ──────────────────────── ✦ DEEP FIELD (12) ────────────────────────────
    R("Star Nursery", "deep", "emission", 3301,
      [("fingers", 1.0, dict(n=120, gain=1.7)), ("starfield", 0.6, dict(n=2400))],
      mix="max", desc="Pillars being eaten from the outside by the stars they just finished making."),
    R("Emission Nebula", "deep", "emission", 3302,
      [("curl", 1.0, dict(scale=48, steps=18)), ("starfield", 0.5, dict(n=2000))],
      mix="max", desc="Hydrogen ionised by everything young and hot inside it, glowing at one wavelength."),
    R("Dark Nebula", "deep", "dust_lane", 3303,
      [("dendrite", 1.0, dict(seeds=700, walkers=20000)), ("starfield", 0.6, dict(n=3000)),
       ("cells", 0.8, dict(cells=150))],
      desc="Not empty — full. Cold dust thick enough to delete the stars behind it."),
    R("Globular Cluster", "deep", "cluster", 3304,
      [("starfield", 1.0, dict(n=6000, mag=1.6, spikes=0.10)), ("cells", 0.45, dict(cells=130))],
      desc="A hundred thousand old stars packed so tightly the sky there never gets dark."),
    R("Spiral Arm", "deep", "reflection", 3305,
      [("curl", 1.0, dict(scale=38, steps=22)), ("starfield", 0.55, dict(n=2600))],
      mix="max", desc="A density wave, not a structure — the arm stays put while the stars pass through."),
    R("Dust Lane", "deep", "dust_lane", 3306,
      [("filaments", 1.0, dict(n=420, length=54)), ("starfield", 0.5, dict(n=2200))],
      desc="The dark band across a galaxy's face, edge-on and absolutely opaque."),
    R("Deep Field", "deep", "cluster", 3307,
      [("starfield", 1.0, dict(n=7000, mag=2.6, spikes=0.03)), ("lens", 0.5, dict(masses=36))],
      desc="Point the telescope at nothing for eleven days and this is what nothing turns out to be."),
    R("Reflection Nebula", "deep", "reflection", 3308,
      [("curl", 1.0, dict(scale=56, steps=16)), ("crinkle", 0.5, dict(scale=130))],
      desc="Dust that is not glowing at all — only scattering blue light from a star out of frame."),
    R("Planetary Nebula", "deep", "planetary", 3309,
      [("shock", 0.8, dict(n=340, thick=0.07)), ("rings", 0.45, dict(systems=180, n=4)),
       ("starfield", 1.9, dict(n=4200))],
      desc="A dying star's outer shell thrown off in stages, lit from inside by the core it left."),
    R("Filament Web", "deep", "reflection", 3310,
      [("filaments", 1.0, dict(n=480, length=60, wander=0.5)), ("cells", 0.5, dict(cells=110))],
      desc="Large-scale structure: galaxies strung on filaments around voids the size of nothing else."),
    R("Zodiacal Light", "deep", "dust_lane", 3311,
      [("dunes", 1.0, dict(n=26, crest=1.4)), ("starfield", 0.55, dict(n=2800))],
      mix="max", desc="Sunlight scattered off the dust in our own plane — the faintest thing you can see."),
    R("Molecular Cloud", "deep", "emission", 3312,
      [("percolate", 1.0, dict(cells=150, p=0.46)), ("dendrite", 0.55, dict(seeds=800))],
      desc="Cold, clumpy, and barely holding together — every clump a star that has not decided yet."),

    # ────────────────────────── ☄ EVENT (12) ───────────────────────────────
    R("Event Horizon", "event", "horizon", 3401,
      [("rings", 0.55, dict(systems=130, n=8, tilt=0.85)), ("lens", 1.0, dict(masses=40)),
       ("starfield", 1.9, dict(n=3400))],
      desc="The photon ring: light that went round more than once before it got out."),
    R("Accretion Disc", "event", "horizon", 3402,
      [("bands", 1.0, dict(n=66, vortex=30)), ("curl", 0.6, dict(scale=44, steps=20))],
      desc="Gas shearing against itself on the way in, and getting hot enough to be the brightest thing here."),
    R("Gravitational Lens", "event", "reflection", 3403,
      [("lens", 1.0, dict(masses=60, strength=34.0)), ("starfield", 0.5, dict(n=3000))],
      desc="Arcs and rings — the same galaxy, imaged four times by the mass in front of it."),
    R("Wormhole Throat", "event", "magnetar", 3404,
      [("rings", 0.55, dict(systems=120, n=9)), ("curl", 1.0, dict(scale=40, steps=22)),
       ("cells", 1.9, dict(cells=150))],
      desc="Nested funnels where the geometry stops agreeing with the distance."),
    R("Supernova Remnant", "event", "shock", 3405,
      [("shock", 0.55, dict(n=300, rag=0.8)), ("filaments", 1.0, dict(n=380, length=44)),
       ("starfield", 1.9, dict(n=2800))],
      desc="Ragged filament shells still expanding into whatever the star's wind cleared out first."),
    R("Pulsar Beam", "event", "magnetar", 3406,
      [("jet", 1.0, dict(n=300, knots=7)), ("rings", 0.5, dict(systems=110, n=5))],
      desc="A lighthouse turning thirty times a second, and you only exist when the beam is on you."),
    R("Magnetar Flare", "event", "magnetar", 3407,
      [("filaments", 1.0, dict(n=440, length=50, wander=0.42)), ("sparks", 0.6, dict(n=2600))],
      mix="max", desc="Field lines snapping and reconnecting on a crust that just cracked."),
    R("Relativistic Jet", "event", "reactor", 3408,
      [("jet", 0.55, dict(n=340, knots=11)), ("shock", 1.0, dict(n=220)),
       ("sparks", 1.9, dict(n=2400, life=24))],
      desc="Collimated, knotted, and moving at a speed that makes the far side of it invisible."),
    R("Bow Shock", "event", "shock", 3409,
      [("shock", 1.0, dict(n=340, thick=0.08)), ("braid", 0.55, dict(layers=96, shear=4.0))],
      desc="Where something moving fast meets something already there, and the medium piles up."),
    R("Tidal Stream", "event", "cluster", 3410,
      [("curl", 1.0, dict(scale=34, steps=24)), ("starfield", 0.6, dict(n=3400))],
      mix="max", desc="A companion galaxy pulled into a thread and wound round its own host."),
    R("Kilonova", "event", "kilonova", 3411,
      [("shock", 1.0, dict(n=300, thick=0.12)), ("dendrite", 1.0, dict(seeds=1000)),
       ("sparks", 1.0, dict(n=2600, life=22))],
      desc="Two neutron stars finished. Every heavy element in your body was made in one of these."),
    R("Frame Drag", "event", "horizon", 3412,
      [("curl", 0.8, dict(scale=24, steps=20)), ("rings", 0.45, dict(systems=180, n=4)),
       ("cells", 1.9, dict(cells=190))],
      desc="Spacetime itself wound up by the rotation, so standing still is no longer available."),

    # ────────────────────────── ⬡ VESSEL (12) ──────────────────────────────
    R("Heat Shield", "vessel", "shield_char", 3501,
      [("crack", 1.0, dict(cells=88, width=2.0)), ("craters", 0.55, dict(n=1800, rmax=6.0))],
      desc="Ablative char: the shield works by being destroyed at a rate somebody calculated exactly."),
    R("MLI Foil", "vessel", "mli_gold", 3502,
      [("crinkle", 1.0, dict(scale=130)), ("hull", 0.5, dict(panels=70))],
      desc="Multi-layer insulation, crumpled gold — the crinkles are the point, not damage."),
    R("Solar Sail", "vessel", "sail", 3503,
      [("crinkle", 1.0, dict(scale=100, folds=4)), ("braid", 0.5, dict(layers=96, shear=1.8))],
      desc="A membrane thinner than a bin bag and the size of a football pitch, pushed by light."),
    R("Radiator Panel", "vessel", "radiator", 3504,
      [("honeycomb", 1.0, dict(cells=100)), ("hull", 0.5, dict(panels=80))],
      desc="White honeycomb whose whole job is to be cold, facing the direction with nothing in it."),
    R("Whipple Shield", "vessel", "sail", 3505,
      [("craters", 1.0, dict(n=2600, rmax=6.5)), ("honeycomb", 0.55, dict(cells=94))],
      desc="Sacrificial outer layer, pitted by grains travelling at ten kilometres a second."),
    R("Thermal Blanket", "vessel", "mli_gold", 3506,
      [("polygons", 1.0, dict(cells=68, width=2.6)), ("crinkle", 0.6, dict(scale=120))],
      desc="Quilted kapton, stitched into cells so a puncture stays a puncture and not a tear."),
    R("Sun Shade", "vessel", "sail", 3507,
      [("crinkle", 1.0, dict(scale=110, sharp=3.0)), ("rings", 0.5, dict(systems=120, n=5))],
      desc="Five layers, each one colder than the last, holding a mirror at forty kelvin."),
    R("Mirror Segment", "vessel", "mli_gold", 3508,
      [("honeycomb", 1.0, dict(cells=76, wall=0.10)), ("crinkle", 0.45, dict(scale=150))],
      desc="Gold on beryllium, eighteen hexagons aligned to a fraction of the light they collect."),
    R("Docking Ring", "vessel", "radiator", 3509,
      [("rings", 0.55, dict(systems=140, n=7, tilt=0.8)), ("hull", 1.0, dict(panels=88)),
       ("cells", 1.9, dict(cells=148))],
      desc="A machined collar built so two things moving at eight kilometres a second can touch gently."),
    R("Ablation Streak", "vessel", "shield_char", 3510,
      [("dunes", 1.0, dict(n=44, drift=0.6)), ("jet", 0.5, dict(n=260))],
      desc="Re-entry flow written onto the shield: every streak is where the plasma went."),
    R("Cryo Tank", "vessel", "cryo",  3511,
      [("dendrite", 1.0, dict(seeds=1200)), ("crack", 0.55, dict(cells=104, width=1.5))],
      desc="Frost creeping over insulation, because the thing inside is colder than the sky."),
    R("Beacon Strobe", "vessel", "reactor", 3512,
      [("sparks", 1.0, dict(n=2800, life=22)), ("honeycomb", 1.0, dict(cells=88)),
       ("cells", 1.0, dict(cells=150))],
      mix="max", desc="Anti-collision strobe on a hull that nothing is close enough to collide with."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_")


COSMOS = {_fid(r["name"]): r for r in _ROWS}


# ════════════════════════════════════════════════════════════════════════════
# RENDER
# ════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=8)
def _field(fid):
    d = COSMOS[fid]
    f, lab = build(d["stack"], (GEN, GEN), d["seed"], mix=d.get("mix", "sum"))
    if lab is None:
        _dd, lab = CK.worley((GEN, GEN), d["seed"] + 7, cells=168)
    return f, lab


@lru_cache(maxsize=6)
def _art(fid):
    d = COSMOS[fid]
    f, lab = _field(fid)
    f = CK.upscale(f, WORK)
    lab = CK.upscale(lab, WORK)
    pal = np.asarray(P[d["palette"]], np.float32)
    tiers = int(d.get("tiers", 8))

    # per-CELL tier so the palette lands as coherent 8-32px patches, then the
    # field itself shades within them
    fc = CK.cell_mean(f, lab)
    t = np.clip(fc ** float(d.get("gamma", 1.0)), 0, 1)
    idx = np.clip((t * (len(pal) - 1)).astype(np.int32), 0, len(pal) - 2)
    frac = np.clip(t * (len(pal) - 1) - idx, 0, 1)[..., None]
    art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
    art = art * (0.70 + 0.60 * f)[..., None]

    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(art, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + (CK._h1(lab, 97) - 0.5) * 22.0, 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.86 + 0.28 * CK._h1(lab, 149)), 0, 1)
        art = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        g = CK.fbm((WORK, WORK), d["seed"] + 3, octaves=(128, 256, 512),
                   weights=(0.6, 1.0, 0.75)) - 0.5
        art = art * (1.0 + g * 0.22)[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    d = COSMOS[fid]
    chap = dict(CHAPTER_SPEC[d["chapter"]])
    chap.update(d.get("spec", {}))
    f, lab = _field(fid)
    f = CK.upscale(f, res)
    lab = CK.upscale(lab, res)
    fc = CK.cell_mean(f, lab)

    bands_ = chap["bands"]
    edges = np.asarray([u for _n, u in bands_], np.float32)
    deck = np.asarray([SC.CARDS[n] for n, _u in bands_], np.float32)
    qs = np.maximum.accumulate(np.asarray(
        np.percentile(fc[::4, ::4], np.clip(edges * 100.0, 0, 100)), np.float32))
    bi = np.clip(np.searchsorted(qs, fc.ravel(), side="left"), 0, len(bands_) - 1)
    out = deck[bi].reshape(res, res, 3)

    if cv2 is not None:
        hs = max(512, res // 2)
        hh = cv2.resize(f, (hs, hs), interpolation=cv2.INTER_AREA) if hs != res else f
        gy, gx = np.gradient(cv2.GaussianBlur(hh, (0, 0), 1.2))
        grad = np.hypot(gx, gy)
        gsub = grad[::2, ::2].ravel()
        lip = (grad > float(np.percentile(gsub, 97.4))).astype(np.float32)
        for q in (99.0, 99.5):
            if lip.mean() <= float(chap.get("edge_max", 0.06)):
                break
            lip = (grad > float(np.percentile(gsub, q))).astype(np.float32)
        k = int(max(2, res / 700.0 * hs / float(res)))
        lip = cv2.dilate(lip, np.ones((k, k), np.float32))
        if hs != res:
            lip = cv2.resize(lip, (res, res), interpolation=cv2.INTER_NEAREST)
        out[lip > 0] = SC.card(chap.get("edge", "chrome"))

    frac2 = float(chap.get("r_spread", 26.0)) / 255.0
    out[..., 1] = np.clip(out[..., 1] * (1.0 + (CK._h1(lab, 173) - 0.5) * 2.0 * frac2), 0, 255)
    out[..., 0] = np.clip(out[..., 0] * (0.93 + 0.14 * CK._h1(lab, 211)), 0, 255)
    off = int(chap.get("cc_offset", max(2, res // 420)))
    out[..., 2] = np.roll(np.roll(out[..., 2], off, 0), -off, 1)
    return SC.iron_safe(out)


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
    for fid in COSMOS:
        entry = _mk(fid)
        for reg in regs:
            try:
                reg[fid] = entry
            except Exception:
                pass
    return "%d off-planet finishes across %d chapters" % (len(COSMOS), len(CHAPTERS))
