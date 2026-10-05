# -*- coding: utf-8 -*-
"""🌃 DARK CITY — 50 dark finishes with bright cutting through.

Owner 2026-09-01:

    "I want EXTREME & EXPERIMENTAL expanded to 50 finishes and the whole
     category renamed to DARK CITY ... where everything is based around very
     dark finishes (black, deep/dark blues reds greens golds etc) with STREAKS
     of bright coming through in the patterns. And specs that trace hot edges so
     they EXPLODE in glistening color against the dark backgrounds. Some darks
     can be flat/matte, some should be more glossy, some should be chalky, etc.
     MIX AND MATCH"

THE MECHANISM, stated so it is testable
---------------------------------------
Every finish here is built the same way and no two are built from the same
geometry:

1. **A dark ground.** The palette's first three stops sit at luma 0.02-0.22.
   Which KIND of dark is authored per finish — flat, chalky, glossy, wet.
2. **Streaks of bright coming through.** The top palette stop is the only bright
   one and it is reached by the top few percent of the field, so the bright
   arrives as streaks and edges rather than as a wash. `bright_at` sets how
   narrow that band is.
3. **A spec that traces the hot edges.** The `edge` card is laid in a lip on the
   region boundaries — where the bright already is — so the spec's sharpest
   material and the paint's brightest colour land on the same lines. That is
   what makes them explode rather than merely sit there.

Each finish names its own construction from the shared form libraries, so the
shelf has fifty geometries rather than one recoloured fifty times.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

import engine.expansions.fractured_flames_kit_2026 as FK
import engine.expansions.nightshift_forms_2026 as NF
from engine.paint_v2 import spec_cards as SC
from engine.paint_v2 import spec_story as ST

ID_PREFIX = "dkc_"
GROUP = "🌃 DARK CITY"
GEN = 1024
WORK = 1152


# ── the darks. First three stops are the ground, the last is the ONLY bright ──
P = {
    "asphalt":    ((0.04, 0.04, 0.05), (0.10, 0.10, 0.12), (0.19, 0.20, 0.23), (0.86, 0.90, 0.98)),
    "oil":        ((0.03, 0.04, 0.06), (0.08, 0.11, 0.16), (0.16, 0.13, 0.24), (0.72, 0.94, 0.86)),
    "tar":        ((0.02, 0.02, 0.02), (0.07, 0.07, 0.07), (0.15, 0.14, 0.13), (0.94, 0.78, 0.42)),
    "soot_blue":  ((0.03, 0.04, 0.07), (0.08, 0.10, 0.17), (0.15, 0.19, 0.29), (0.66, 0.86, 1.00)),
    "obsidian":   ((0.02, 0.02, 0.03), (0.06, 0.06, 0.09), (0.13, 0.13, 0.18), (0.80, 0.82, 0.95)),
    "hematite":   ((0.04, 0.03, 0.03), (0.11, 0.09, 0.09), (0.21, 0.18, 0.18), (0.92, 0.86, 0.80)),
    "jet":        ((0.02, 0.02, 0.02), (0.06, 0.06, 0.07), (0.12, 0.12, 0.14), (0.72, 0.74, 0.80)),
    "galena":     ((0.05, 0.05, 0.06), (0.12, 0.12, 0.14), (0.22, 0.23, 0.26), (0.88, 0.90, 0.94)),
    "abyss":      ((0.02, 0.04, 0.07), (0.05, 0.10, 0.18), (0.09, 0.19, 0.31), (0.52, 0.86, 1.00)),
    "prussian":   ((0.02, 0.04, 0.08), (0.04, 0.09, 0.19), (0.08, 0.17, 0.33), (0.62, 0.80, 0.98)),
    "pine":       ((0.02, 0.05, 0.04), (0.05, 0.12, 0.09), (0.09, 0.22, 0.16), (0.58, 0.98, 0.74)),
    "bottle":     ((0.02, 0.05, 0.03), (0.04, 0.13, 0.08), (0.08, 0.23, 0.14), (0.74, 1.00, 0.62)),
    "indigo":     ((0.04, 0.03, 0.09), (0.09, 0.07, 0.19), (0.16, 0.13, 0.32), (0.72, 0.62, 1.00)),
    "oxblood":    ((0.07, 0.02, 0.03), (0.16, 0.04, 0.06), (0.28, 0.08, 0.11), (1.00, 0.52, 0.42)),
    "garnet":     ((0.06, 0.02, 0.04), (0.14, 0.04, 0.08), (0.25, 0.07, 0.14), (1.00, 0.46, 0.62)),
    "burgundy":   ((0.06, 0.02, 0.04), (0.13, 0.05, 0.08), (0.22, 0.09, 0.13), (0.94, 0.62, 0.54)),
    "brass_night": ((0.06, 0.05, 0.02), (0.14, 0.11, 0.04), (0.25, 0.20, 0.08), (1.00, 0.86, 0.44)),
    "copper_dark": ((0.07, 0.04, 0.02), (0.16, 0.08, 0.04), (0.27, 0.15, 0.08), (1.00, 0.72, 0.40)),
    "amber_vault": ((0.05, 0.04, 0.02), (0.12, 0.09, 0.03), (0.21, 0.16, 0.06), (1.00, 0.80, 0.34)),
    "arc":        ((0.02, 0.02, 0.03), (0.05, 0.06, 0.09), (0.11, 0.13, 0.19), (0.90, 0.98, 1.00)),
    "neon_scar":  ((0.03, 0.02, 0.04), (0.08, 0.05, 0.11), (0.14, 0.09, 0.20), (1.00, 0.44, 0.86)),
    "tracer":     ((0.02, 0.03, 0.02), (0.06, 0.09, 0.06), (0.11, 0.17, 0.11), (0.86, 1.00, 0.46)),
}


def _luma(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _floor_dark(pal, targets=(0.085, 0.14, 0.21)):
    """A dark ground is not a void.

    Coverage scan 2026-09-02: eleven finishes here measured 0.75-0.99 of the
    canvas below luma 0.06 - a black car with three lines on it, not "very dark
    finishes with STREAKS of bright coming through". Their palettes started at
    luma 0.02-0.04. Lifting the three ground stops to 0.085 / 0.14 / 0.21
    (hue preserved) keeps every one of them well inside the dark-ground check
    (first three stops <= 0.30) and makes the ground read as deep colour, so
    the streak is a streak ON something.
    """
    out = []
    for i, c in enumerate(pal):
        l = _luma(c)
        if i < 3 and l < targets[i]:
            if l < 0.01:
                c = (targets[i], targets[i], targets[i] * 1.08)
            else:
                k = targets[i] / l
                c = tuple(min(1.0, float(v) * k) for v in c)
        out.append(tuple(float(v) for v in c))
    return tuple(out)


def _ground_scale(name):
    # deterministic, per palette: 0.85..1.15 so fifty floored grounds are not
    # one identical luma (the twin advisory hit 1.000 between vein finishes
    # when they were). str hash is randomised per process, so not that.
    h = sum(ord(c) * (i + 1) for i, c in enumerate(name)) * 2654435761 % 1000
    return 0.85 + 0.30 * (h / 999.0)


P = {k: _floor_dark(v, tuple(t * _ground_scale(k) for t in (0.085, 0.14, 0.21)))
     for k, v in P.items()}


def R(name, palette, form, params, deck, edge, seed, *, grain="grain", gamt=0.20,
      bright_at=0.86, tiers=0, gamma=1.0, desc="", **kw):
    """One dark finish.

    `bright_at` is the quantile where the ONE bright palette stop starts. High
    values keep the bright to streaks and edges, which is the brief; drop it
    only for a finish that is meant to read as lit rather than as dark.
    """
    return dict(name=name, palette=palette, form=form, params=params, deck=deck,
                edge=edge, seed=seed, grain=grain, gamt=gamt, bright_at=bright_at,
                tiers=tiers, gamma=gamma, desc=desc, **kw)


ROWS = [
    # ── ⬛ ASPHALT — street level, wet and worn ────────────────────────────
    R("Wet Asphalt", "asphalt", "erosion", dict(iters=22), ("void", "matte", "satin_carbon", "wet", "liquid_glaze"), "mercury", 3101,
      grain="grain", gamt=0.16, desc="Road after rain, holding every light in the street in a thin film."),
    R("Oil Slick", "oil", "ek:holo", dict(rings=220.0, orders=3.0), ("gloss_carbon", "gloss", "liquid_glaze", "spectraflame", "candy_chrome", "pearl", "mirror_deep"), "spectraflame", 3102,
      grain="flake", gamt=0.14, bright_at=0.74, desc="A film one wavelength thick on black water, and every colour in it."),
    R("Manhole Steam", "soot_blue", "fk:drift", dict(scale=150, steps=30), ("flat_black", "matte", "ceramic_matte", "milk_glass", "soft_gloss"), "satin_chrome", 3103,
      grain="grain", gamt=0.22, bright_at=0.74, desc="Vapour off a grate at 3am, lit from one side and gone by morning."),
    R("Tyre Black", "jet", "ek:knurl", dict(pitch=30.0, angle=0.0, wobble=0.15), ("void", "flat_black", "matte", "vinyl", "satin_carbon", "gunmetal", "semi_gloss"), "gunmetal", 3104,
      grain="stipple", gamt=0.24, bright_at=0.74, desc="Moulded tread in the deadest black there is, with the mould line still on it."),
    R("Tar Seam", "tar", "fk:crack", dict(cells=30, width=3.4), ("void", "matte", "satin_carbon", "bronze_raw", "spectraflame", "gloss", "liquid_glaze"), "spectraflame", 3105,
      grain="ridge", gamt=0.18, desc="Poured hot into the joint, gone hard and glossy where it pooled."),
    R("Gutter Chrome", "asphalt", "ek:topo", dict(lines=90.0, width=2.2), ("flat_black", "satin_carbon", "gunmetal", "satin_chrome", "chrome"), "chrome", 3106,
      grain="fibre", gamt=0.16, desc="Water finding the low line, and the low line turning out to be polished."),
    R("Night Rain", "soot_blue", "ek:rt_fingers", dict(n=70), ("void", "wet", "sea_glass", "liquid_glaze", "mirror_deep"), "mercury", 3107,
      grain="spark", gamt=0.20, bright_at=0.74, desc="Vertical water against a dark building, each drop its own lens."),
    R("Kerb Grit", "galena", "ek:craters", dict(n=4000, rmin=1.2, rmax=4.5, rim=0.4), ("matte", "ceramic_matte", "bead_blast", "powder", "galvanized"), "brushed_ti", 3108,
      grain="crackle", gamt=0.26, bright_at=0.90, desc="Swept into the edge and left there — the chalkiest dark on the shelf."),
    R("Storm Drain", "abyss", "maze", dict(cells=96), ("void", "flat_black", "gunmetal", "wet", "satin_chrome"), "steel_dark", 3109,
      grain="ridge", gamt=0.18, desc="Routed underneath everything, and the only light is what falls in."),
    R("Blacktop Heat", "tar", "ek:glitch", dict(slices=60, shift=18.0, tear=0.1, block=0.0), ("flat_black", "matte", "semi_gloss", "candy", "candy_chrome"), "candy_chrome", 3110,
      grain="grain", gamt=0.20, bright_at=0.82, desc="Fresh laid and still soft, shimmering where the sun is still on it."),

    # ── 🌑 OBSIDIAN — mineral darks ───────────────────────────────────────
    R("Obsidian Chill", "obsidian", "shatter", dict(impacts=3, radials=30), ("void", "gloss_carbon", "gloss", "liquid_glaze", "mirror_deep", "sea_glass", "chrome_veil"), "mercury", 3111,
      grain="ridge", gamt=0.14, bright_at=0.62, desc="Cooled too fast to crystallise. Conchoidal, and sharper than surgical steel."),
    R("Basalt Glass", "obsidian", "ek:polygons", dict(cells=60, width=2.5), ("flat_black", "matte", "ceramic_matte", "gloss_carbon", "semi_gloss", "sea_glass", "mirror_deep"), "gunmetal", 3112,
      grain="crackle", gamt=0.22, desc="Columns cracked by their own cooling, with a glassy skin on every face."),
    R("Hematite", "hematite", "ek:scales", dict(cell=18.0, keel=0.6), ("satin_carbon", "gunmetal", "brushed_ti", "steel_dark", "mirror_deep", "chrome_veil", "pewter_metal"), "mercury", 3113,
      grain="fibre", gamt=0.16, bright_at=0.62, desc="Iron oxide polished until it turns into a mirror that is somehow still red."),
    R("Tourmaline Black", "indigo", "quasicrystal", dict(waves=7, freq=240.0), ("void", "gloss_carbon", "sea_glass", "liquid_glaze", "spectraflame", "candy", "pearl"), "spectraflame", 3114,
      grain="flake", gamt=0.15, bright_at=0.82, desc="Schorl: black until you turn it, and then it is not black at all."),
    R("Onyx Band", "jet", "moire_beat", dict(a=104.0, b=112.0), ("void", "flat_black", "gloss_carbon", "ceramic_gloss", "liquid_glaze", "pearl", "mirror_deep"), "mercury", 3115,
      grain="grain", gamt=0.14, bright_at=0.62, desc="Banded chalcedony cut across the layers so the bands read as stripes."),
    R("Magnetite", "galena", "rosensweig", dict(pitch=26.0), ("matte", "satin_carbon", "gunmetal", "brushed_ti", "satin_chrome", "steel_dark", "mirror_deep"), "steel_dark", 3116,
      grain="spark", gamt=0.22, bright_at=0.62, desc="Lodestone in a field, standing up into spikes because it can."),
    R("Jet Carve", "jet", "tooled" if False else "fk:crease", dict(k=1.4, steps=30), ("void", "flat_black", "matte", "semi_gloss", "gloss"), "razor", 3117,
      grain="ridge", gamt=0.18, bright_at=0.62, desc="Fossil wood cut and polished for mourning jewellery, warm to the touch."),
    R("Shungite", "obsidian", "fk:percolate" if False else "fk:bed", dict(cells=52, p=0.44), ("void", "matte", "satin_carbon", "bead_blast", "gloss_carbon"), "gunmetal", 3118,
      grain="crackle", gamt=0.24, bright_at=0.90, desc="Carbon that predates multicellular life, and conducts like it knows it."),
    R("Anthracite", "galena", "fk:spall" if False else "fk:plate", dict(cells=24, lift=0.85), ("flat_black", "satin_carbon", "matte", "gloss_carbon", "gunmetal"), "steel_dark", 3119,
      grain="ridge", gamt=0.20, desc="Hard coal with a vitreous fracture — the cleanest burn and the brightest break."),
    R("Galena Cube", "galena", "truchet", dict(tiles=40, style="cross"), ("matte", "gunmetal", "brushed_ti", "satin_chrome", "mirror_deep"), "mercury", 3120,
      grain="stipple", gamt=0.18, desc="Lead sulphide cleaving into perfect cubes, each face a small dull mirror."),

    # ── 🔵 DEEP — dark blues and greens ───────────────────────────────────
    R("Abyss Blue", "abyss", "ek:camo", dict(patches=6, blob=140.0, roughness=1.4), ("void", "gloss_carbon", "sea_glass", "wet", "liquid_glaze"), "mercury", 3121,
      grain="grain", gamt=0.14, desc="Below the last light. Whatever is down there makes its own."),
    R("Midnight Teal", "pine", "caustics", dict(scale=6.0, octaves=4), ("gloss_carbon", "semi_gloss", "sea_glass", "gloss", "liquid_glaze", "wet", "candy"), "sea_glass", 3122,
      grain="flake", gamt=0.16, bright_at=0.62, desc="A pool lit from under the water, at the hour the party thins out."),
    R("Ink Well", "indigo", "metaball", dict(blobs=2200, radius=0.0080), ("void", "flat_black", "wet", "gloss", "mirror_deep", "liquid_glaze", "sea_glass"), "mercury", 3123,
      grain="grain", gamt=0.12, bright_at=0.62, desc="Iron gall ink pooling in the bottom of the well, thick enough to stand a nib in."),
    R("Prussian", "prussian", "ek:fbm", dict(octaves=(96, 192, 384, 768)), ("flat_black", "matte", "semi_gloss", "gloss", "ceramic_gloss"), "razor", 3124,
      grain="ridge", gamt=0.18, desc="The first modern synthetic blue, and still the deepest one in the box."),
    R("Deep Pine", "pine", "ek:filaments", dict(n=700, length=60, width=1.6, wander=0.35), ("void", "matte", "ceramic_matte", "vinyl", "semi_gloss", "sea_glass", "soft_gloss"), "patina", 3125,
      grain="fibre", gamt=0.22, bright_at=0.62, desc="Closed canopy at dusk, where the green has gone almost to black."),
    R("Bottle Green", "bottle", "phyllotaxis", dict(n=44000, spread=0.70), ("satin", "sea_glass", "gloss", "ceramic_gloss", "milk_glass", "liquid_glaze", "wet"), "sea_glass", 3126,
      grain="flake", gamt=0.15, bright_at=0.62, desc="Thick cast glass — black on edge, green through the face, and full of bubbles."),
    R("Nocturne", "indigo", "ek:moire", dict(), ("void", "gloss_carbon", "satin", "gloss", "pearl"), "satin_chrome", 3127,
      grain="fibre", gamt=0.16, desc="Written to be played quietly, in a room with one lamp on."),
    R("Cobalt Night", "prussian", "ek:worley", dict(cells=80), ("flat_black", "ceramic_matte", "semi_gloss", "ceramic_gloss", "liquid_glaze"), "chrome", 3128,
      grain="crackle", gamt=0.20, desc="Cobalt on a dark body, fired so the pigment sinks into the glaze."),
    R("Viridian Dark", "bottle", "ek:facets", dict(stones=320, table=0.30), ("void", "matte", "vinyl", "semi_gloss", "gloss"), "patina", 3129,
      grain="grain", gamt=0.22, bright_at=0.88, desc="Hydrated chromium oxide: a green so deep it argues with black."),
    R("Indigo Vault", "indigo", "ek:ikat", dict(), ("void", "flat_black", "matte", "satin", "milk_glass"), "pearl", 3130,
      grain="stipple", gamt=0.20, bright_at=0.74, desc="Twelve dips and a day in the air between each, until it stops being blue."),

    # ── 🔴 EMBER — dark reds and golds ────────────────────────────────────
    R("Oxblood", "oxblood", "ek:intaglio", dict(), ("void", "matte", "semi_gloss", "gloss", "ceramic_gloss"), "candy_chrome", 3131,
      grain="fibre", gamt=0.18, desc="Boot polish built up over years, worn back at the toe to something darker."),
    R("Garnet Dark", "garnet", "apollonian", dict(rmax=0.062), ("satin_carbon", "ceramic_gloss", "candy", "mirror_deep", "chrome_veil"), "candy_chrome", 3132,
      grain="flake", gamt=0.15, desc="Almandine: opaque in the hand and full of fire the moment it is lit."),
    R("Ember Gold", "amber_vault", "ek:stars", dict(), ("void", "flat_black", "matte", "bronze_raw", "spectraflame"), "spectraflame", 3133,
      grain="spark", gamt=0.22, bright_at=0.84, desc="A bed with no flame left on it, and more heat than it looks like."),
    R("Burgundy", "burgundy", "ek:tooled", dict(cell=70.0, petals=6, stamp=0.7, bevel=1.0), ("matte", "vinyl", "satin", "semi_gloss", "gloss"), "candy_chrome", 3134,
      grain="grain", gamt=0.18, bright_at=0.88, desc="In the bottle it is black; against a candle it is not."),
    R("Dried Rose", "burgundy", "ek:resist", dict(), ("clear_matte", "ceramic_matte", "vinyl", "satin", "soft_gloss"), "pearl", 3135,
      grain="stipple", gamt=0.24, bright_at=0.90, desc="Kept in a book for a decade, gone to paper and holding the colour anyway."),
    R("Brass Night", "brass_night", "damascus", dict(layers=190, twist=3.4), ("satin_carbon", "bronze_raw", "antique_chrome", "spectraflame", "candy_chrome"), "spectraflame", 3136,
      grain="fibre", gamt=0.16, desc="Unlacquered and left alone, so it darkens everywhere a hand does not go."),
    R("Molten Seam", "copper_dark", "ek:squiggle", dict(n=500, length=200.0, amp=20.0, confetti=0.1, width=4.0), ("void", "flat_black", "satin_carbon", "candy", "carrier_high", "liquid_glaze", "candy_chrome"), "chrome", 3137,
      grain="ridge", gamt=0.18, bright_at=0.62, desc="Cold plate with something still liquid running in the joint."),
    R("Copper Dark", "copper_dark", "ek:crinkle", dict(scale=90, sharp=2.2, folds=2), ("matte", "patina", "bronze_raw", "antique_chrome", "spectraflame"), "bronze_raw", 3138,
      grain="crackle", gamt=0.22, desc="Roofing copper eight winters in, before the green arrives and after the shine goes."),
    R("Rust Noir", "hematite", "fk:front", dict(seeds=300, steps=20), ("void", "matte", "patina", "bead_blast", "bronze_raw", "antique_chrome", "candy"), "steel_dark", 3139,
      grain="crackle", gamt=0.26, bright_at=0.90, desc="Oxide advancing across a dark panel, and winning, slowly."),
    R("Amber Vault", "amber_vault", "ek:dunes", dict(n=30, crest=1.8), ("satin", "gloss", "liquid_glaze", "spectraflame", "bronze_raw"), "spectraflame", 3140,
      grain="flake", gamt=0.14, desc="Resin with something in it, forty million years into a very slow set."),

    # ── ⚡ ARC — bright cutting the black ─────────────────────────────────
    R("Arc Weld", "arc", "imbricate", dict(rows=60, overlap=0.5), ("void", "gunmetal", "steel_dark", "chrome_dry", "chrome", "mirror_deep", "spectraflame"), "chrome", 3141,
      grain="spark", gamt=0.20, bright_at=0.62, desc="Strike an arc without a helmet once and you remember it for a week."),
    R("Lightning Black", "arc", "ek:dla", dict(seeds=8, walkers=48000, steps=320), ("void", "gloss_carbon", "satin_carbon", "carrier_mid", "carrier_high"), "chrome", 3142,
      grain="spark", gamt=0.18, bright_at=0.74, desc="One channel out of a thousand attempts, and it lasts thirty microseconds."),
    R("Filament", "amber_vault", "ridge_flow", dict(ridges=210, cores=4), ("void", "flat_black", "satin_carbon", "spectraflame", "carrier_high"), "spectraflame", 3143,
      grain="fibre", gamt=0.16, bright_at=0.88, desc="Coiled tungsten at 2800K, which is most of the way to giving up."),
    R("Neon Scar", "neon_scar", "ek:guilloche", dict(), ("void", "gloss_carbon", "semi_gloss", "carrier_mid", "carrier_high"), "chrome", 3144,
      grain="ridge", gamt=0.16, bright_at=0.74, desc="Bent glass on a black wall, and the wall is only there to hold it."),
    R("Laser Cut", "arc", "chladni", dict(modes=((47, 63), (71, 39), (89, 77), (107, 95), (119, 109))), ("flat_black", "satin_carbon", "gunmetal", "spectraflame", "chrome"), "razor", 3145,
      grain="ridge", gamt=0.14, bright_at=0.90, desc="A kerf a quarter of a millimetre wide, with the heat colour still on the edge."),
    R("Plasma Seam", "neon_scar", "ek:kh_braid", dict(layers=34, shear=4.0), ("void", "flat_black", "gloss_carbon", "carrier_low", "carrier_high"), "mercury", 3146,
      grain="grain", gamt=0.18, bright_at=0.74, desc="Where the ionised column touches metal, and the metal notices."),
    R("Spark Trail", "tracer", "fk:spark", dict(n=380, life=140), ("void", "matte", "satin_carbon", "spectraflame", "carrier_high", "gunmetal", "chrome"), "chrome", 3147,
      grain="spark", gamt=0.22, bright_at=0.62, desc="Grinding wheel on mild steel: each spark a burning particle with a lifetime."),
    R("Hot Wire", "amber_vault", "ek:sett", dict(pitch=30.0, twill=1.0), ("void", "flat_black", "matte", "bronze_raw", "carrier_high"), "spectraflame", 3148,
      grain="fibre", gamt=0.16, bright_at=0.88, desc="Nichrome through foam, glowing exactly as much as the current says."),
    R("Tracer", "tracer", "ek:filaments", dict(n=90, length=420, width=1.6, wander=0.02), ("void", "gunmetal", "matte", "candy", "carrier_high", "spectraflame", "chrome_dry"), "chrome", 3149,
      grain="spark", gamt=0.18, bright_at=0.62, desc="Every fifth round burning, which is how you learn where the others went."),
    R("Flashover", "arc", "gray_scott", dict(feed=0.026, kill=0.051), ("void", "flat_black", "gloss_carbon", "candy", "carrier_high", "candy_chrome", "mirror_deep"), "chrome", 3150,
      grain="grain", gamt=0.20, bright_at=0.62, desc="Every surface in the room reaching ignition temperature at the same moment."),
]


def _fid(name):
    return ID_PREFIX + "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


DARK_CITY = {_fid(r["name"]): r for r in ROWS}

# ── fixes from the first full gate run (42/50) ────────────────────────────
# THREE SCALE failures, all on the coarsest macro constructions (a basalt
# column field and two Gray-Scott regimes): they need a stronger keyed fine
# layer to carry the car window, since their own geometry is all above it.
for _f, _amt in (("dkc_blacktop_heat", 0.80), ("dkc_ink_well", 0.70), ("dkc_obsidian_chill", 0.62), ("dkc_hematite", 0.60), ("dkc_onyx_band", 0.60), ("dkc_magnetite", 0.60), ("dkc_jet_carve", 0.62), ("dkc_midnight_teal", 0.62), ("dkc_ink_well", 0.60), ("dkc_bottle_green", 0.60), ("dkc_molten_seam", 0.62), ("dkc_arc_weld", 0.62), ("dkc_spark_trail", 0.62), ("dkc_tracer", 0.62), ("dkc_flashover", 0.85), ("dkc_deep_pine", 0.75), ("dkc_basalt_glass", 0.78), ("dkc_ember_gold", 0.86),
                 ("dkc_flashover", 0.80)):
    DARK_CITY[_f]["detail"] = _amt

# FIVE FOLLOW failures, all on area-FILLING constructions (curl drift, caustics,
# phyllotaxis packing, ridge flow, a routed maze). Linear-by-value banding is
# right for this shelf's streak finishes and wrong for these: where the artwork
# covers the canvas evenly, equal-population bands track it better.
# Quantile bands were tried first and made all five WORSE (abyss_blue 0.344 ->
# 0.166); raising the keyed detail was tried second and was worse again
# (bottle_green 0.265 -> 0.134). Swept properly, the direction is the opposite
# of both guesses: LESS grain and a WIDER bright band. On an area-filling
# construction the grain dilutes the envelope rather than shaping it, and a
# narrow bright band leaves too little amplitude for the spec to track.
# Measured on bottle_green: 0.13 -> 0.67.
for _f in ("dkc_abyss_blue", "dkc_midnight_teal", "dkc_bottle_green",
           "dkc_nocturne", "dkc_neon_scar"):
    DARK_CITY[_f]["detail"] = 0.10
    DARK_CITY[_f]["bright_at"] = 0.70

# Ember Gold's Gray-Scott mitosis regime is the coarsest construction on the
# shelf and could not carry the car window at any detail amount (fine 0.048 even
# at 0.86). An ember bed is scale-free anyway — coals of every size — so it gets
# the Apollonian packing instead, which is the right shape for it.
# (2026-09-02: the apollonian override was removed; ember_gold is ek:sparks now,
#  its own construction. garnet_dark keeps apollonian.)
DARK_CITY["dkc_ember_gold"]["detail"] = 0.55


_ALIAS = {"fk:vein": "filaments", "fk:drift": "curl", "fk:dendrite": "dla", "fk:bed": "percolate",
          "fk:plate": "spall", "fk:crack": "anneal_crack", "fk:front": "eden", "fk:crease": "wrinkle",
          "fk:finger": "rt_fingers", "fk:spark": "sparks", "fk:braid": "kh_braid"}


# a shared algorithm in two visibly different regimes is two designs; each
# allowance names its reason (owner 2026-09-02 variant sheets)
_SAME_OK = {("dkc_deep_pine", "dkc_tracer"): "filaments: 700 short wandering needles vs 260 long straight rounds"}


def _canonical(form):
    if form in _ALIAS:
        return _ALIAS[form]
    return form[3:] if form.startswith(("ek:", "fk:")) else form


def check():
    """Fifty finishes, fifty geometries, fifty material stories, all dark."""
    # The flames kit aliases era-kit algorithms under other names. Owner
    # 2026-09-02: "Rust Noir ... EXACTLY like Hematite. HOW are we still
    # repeating?" (fk:front IS eden). Compare the ALGORITHM, not the label.
    _forms = [_canonical(d.get("form")) for d in DARK_CITY.values()] if "DARK_CITY" in globals() else []
    if _forms and len(set(_forms)) != len(_forms):
        _d = sorted({f for f in _forms if _forms.count(f) > 1})
        for f in list(_d):
            ids = tuple(sorted(k for k, d in DARK_CITY.items() if _canonical(d.get("form")) == f))
            if _SAME_OK.get(ids):
                _d.remove(f)
        if _d:
            raise ValueError("DARK CITY reuses constructions (by algorithm): %s" % _d)
    seen_form, seen_deck = {}, {}
    for fid, d in DARK_CITY.items():
        seen_form.setdefault((d["form"], tuple(sorted(d["params"].items()))), []).append(fid)
        seen_deck.setdefault(frozenset(d["deck"]), []).append(fid)
    for label, tbl in (("construction+params", seen_form), ("material story", seen_deck)):
        clash = {k: v for k, v in tbl.items() if len(v) > 1}
        if clash:
            raise ValueError("DARK CITY duplicate %s: %s" % (
                label, "; ".join(", ".join(sorted(v)) for v in clash.values())))
    # the brief: every ground must actually be dark
    for fid, d in DARK_CITY.items():
        stops = P[d["palette"]]
        lum = [0.2126 * s[0] + 0.7152 * s[1] + 0.0722 * s[2] for s in stops[:3]]
        if max(lum) > 0.30:
            raise ValueError("%s: ground is not dark (max luma %.2f)" % (fid, max(lum)))
        bright = stops[-1]
        if 0.2126 * bright[0] + 0.7152 * bright[1] + 0.0722 * bright[2] < 0.45:
            raise ValueError("%s: no bright to come through" % fid)
    return len(DARK_CITY)


def _form_field(d, shape, seed):
    form, params = d["form"], d["params"]
    if form.startswith("fk:"):
        key = form[3:]
        fn = {
            "cell": lambda: FK.worley(shape, seed, cells=params.get("cells", 26)),
            "vein": lambda: (FK.filaments(shape, seed, n=params.get("n", 70),
                                          length=params.get("length", 150)), None),
            "braid": lambda: (FK.kh_braid(shape, seed, layers=params.get("layers", 26),
                                          shear=params.get("shear", 4.2)), None),
            "drift": lambda: (FK.curl(shape, seed, scale=params.get("scale", 150),
                                      steps=params.get("steps", 30)), None),
            "dendrite": lambda: (FK.dla(shape, seed, seeds=params.get("seeds", 120)), None),
            "bed": lambda: FK.percolate(shape, seed, cells=params.get("cells", 44),
                                        p=params.get("p", 0.47)),
            "plate": lambda: FK.spall(shape, seed, cells=params.get("cells", 24),
                                      lift=params.get("lift", 0.85)),
            "crack": lambda: FK.anneal_crack(shape, seed, cells=params.get("cells", 30),
                                             width=params.get("width", 3.4), gen=1),
            "front": lambda: (FK.eden(shape, seed, seeds=params.get("seeds", 340),
                                      steps=params.get("steps", 18)), None),
            "crease": lambda: (FK.wrinkle(shape, seed, k=params.get("k", 2.1),
                                          steps=params.get("steps", 26)), None),
            "finger": lambda: (FK.rt_fingers(shape, seed, n=params.get("n", 30)), None),
            "spark": lambda: (FK.sparks(shape, seed, n=params.get("n", 260),
                                        life=params.get("life", 110)), None),
        }[key]
        out = fn()
    elif form.startswith("ek:"):
        # 2026-09-02: the shelf was built from the flames kit and the nightshift
        # forms only (30 constructions for 50 finishes). The era kit is the
        # third source of constructions and the zero-reuse rebuild draws on it.
        from engine.paint_v2 import era_kit_2026 as EK
        out = getattr(EK, form[3:])(shape, seed, **params)
    else:
        out = getattr(NF, form)(shape, seed, **params)
    f, lab = out if isinstance(out, tuple) else (out, None)
    return np.asarray(f, np.float32), lab



# ── FINE STRUCTURE — a second, smaller construction nested in the first ──────
# Owner 2026-09-02, holding DARK CITY next to IRIDESCENT INSECTS: "LOOK at how
# intricate some of those designs are. Then compare to what you have here." One
# construction plus a grain is one scale. Intricacy is structure INSIDE structure:
# weld ripples inside the spatter, siping inside the tread block, pinholes in the
# glaze, hammer dents inside the folds. Each entry is (form, params, weight) and is
# chosen from what that finish is; the fine field is keyed to the macro's edges so
# it lives on the design rather than over it.
FINE = {
    "dkc_arc_weld":      ("ek:scanline",     dict(lines=260.0, triad=1.0, bloom=0.4, roll=0.0, jitter=0.6), 0.30),  # bead ripple
    "dkc_basalt_glass":  ("ek:anneal_crack", dict(cells=80, width=1.2), 0.30),  # 180 cells 3.9s, 120 cells 4.0s                                    # glass craze
    "dkc_bottle_green":  ("ek:holo",         dict(rings=420.0, orders=2.0, sharp=1.6), 0.25),                       # thin-glass interference
    "dkc_burgundy":      ("ek:knurl",        dict(pitch=12.0, angle=0.3, wobble=0.6), 0.30),                       # leather grain
    "dkc_cobalt_night":  ("ek:craters",      dict(n=6000, rmin=1.0, rmax=3.0, rim=0.5), 0.30),                     # glaze pinholes
    "dkc_copper_dark":   ("ek:discs",        dict(n=8000, radius=4.0), 0.30),                                      # fine hammer dents
    "dkc_deep_pine":     ("ek:threads",      dict(), 0.30),                                                        # needles
    "dkc_dried_rose":    ("ek:crinkle",      dict(scale=400, sharp=2.0, folds=1), 0.30),                           # petal veining
    "dkc_ember_gold":    ("ek:worley",       dict(cells=220), 0.30),                                               # ash cells between embers
    "dkc_hematite":      ("ek:facets",       dict(stones=1500, table=0.4), 0.30),                                  # micro-facets on the lumps
    "dkc_hot_wire":      ("ek:sparks",       dict(), 0.30),                                                        # spitting at the wire
    "dkc_laser_cut":     ("ek:pixels",       dict(cell=6.0, levels=4, dither=0.2), 0.25),                          # kerf raster
    "dkc_rust_noir":     ("ek:splatter",     dict(blobs=3000, rmax=4.0, drips=0.0, spatter=1.2), 0.30),            # rust pitting
    "dkc_oxblood":       ("ek:scales",       dict(cell=9.0, keel=0.3), 0.30),                                      # leather grain
    "dkc_tyre_black":    ("ek:sett",         dict(pitch=10.0, twill=1.0), 0.30),                                   # siping in the tread block
    "dkc_wet_asphalt": ("ek:craters", dict(n=5000, rmin=1.0, rmax=2.5, rim=0.5), 0.30),  # aggregate pits under the film
    "dkc_manhole_steam": ("ek:fbm", dict(octaves=(256, 512, 1024)), 0.25),  # vapour grain
    "dkc_tar_seam": ("ek:worley", dict(cells=240), 0.25),  # cooled tar skin
    "dkc_gutter_chrome": ("ek:scanline", dict(lines=300.0, triad=1.0, bloom=0.3, roll=0.0, jitter=0.5), 0.25),  # ripple lines on the water
    "dkc_night_rain": ("ek:stars", dict(), 0.30),  # droplets
    "dkc_kerb_grit": ("ek:splatter", dict(blobs=4000, rmax=3.0, drips=0.0, spatter=1.0), 0.30),  # grit grains
    "dkc_storm_drain": ("ek:knurl", dict(pitch=10.0, angle=0.0, wobble=0.1), 0.30),  # grate mesh
    "dkc_obsidian_chill": ("ek:anneal_crack", dict(cells=220, width=1.0), 0.30),  # conchoidal ripples
    "dkc_tourmaline_black": ("ek:facets", dict(stones=1200, table=0.3), 0.30),  # crystal faces
    "dkc_onyx_band": ("ek:fbm", dict(octaves=(512, 1024)), 0.20),  # chalcedony grain
    "dkc_magnetite": ("ek:pixels", dict(cell=7.0, levels=3, dither=0.3), 0.25),  # octahedral cubes
    "dkc_jet_carve": ("ek:filaments", dict(n=500, length=60, width=1.0, wander=0.1), 0.30),  # carving strokes
    "dkc_shungite": ("ek:scales", dict(cell=8.0, keel=0.2), 0.25),  # carbon flakes
    "dkc_anthracite": ("ek:sett", dict(pitch=9.0, twill=1.0), 0.25),  # cleavage lines
    "dkc_galena_cube": ("ek:knurl", dict(pitch=14.0, angle=0.785, wobble=0.0), 0.25),  # cubic cleavage
    "dkc_midnight_teal": ("ek:holo", dict(rings=500.0, orders=1.0, sharp=1.5), 0.25),  # underwater shimmer
    "dkc_abyss_blue": ("ek:stars", dict(), 0.25),  # bioluminescent points
    "dkc_prussian": ("ek:craters", dict(n=7000, rmin=0.8, rmax=2.0, rim=0.4), 0.25),  # pigment grain
    "dkc_nocturne": ("ek:threads", dict(), 0.25),  # velvet
    "dkc_viridian_dark": ("ek:anneal_crack", dict(cells=260, width=1.0), 0.25),  # pigment craze
    "dkc_indigo_vault": ("ek:sett", dict(pitch=11.0, twill=2.0), 0.30),  # the cloth itself
    "dkc_garnet_dark": ("ek:facets", dict(stones=1600, table=0.5), 0.30),  # faces on the crystals
    "dkc_molten_seam": ("ek:worley", dict(cells=200), 0.25),  # cooled skin
    "dkc_amber_vault": ("ek:stars", dict(), 0.20),  # inclusions
    "dkc_lightning_black": ("ek:sparks", dict(), 0.25),  # branch sparks
    "dkc_filament": ("ek:scanline", dict(lines=400.0, triad=1.0, bloom=0.5, roll=0.0, jitter=0.2), 0.30),  # coil turns
    "dkc_plasma_seam": ("ek:fbm", dict(octaves=(256, 512)), 0.20),  # ionised haze
    "dkc_spark_trail": ("ek:splatter", dict(blobs=2000, rmax=3.0, drips=0.6, spatter=1.0), 0.25),  # burn marks
    "dkc_neon_scar": ("ek:holo", dict(rings=300.0, orders=1.0, sharp=1.2), 0.25),  # glass-tube sheen
    "dkc_tracer": ("ek:sparks", dict(), 0.25),  # burning particles
    "dkc_flashover": ("ek:anneal_crack", dict(cells=200, width=1.4), 0.35),  # char craze (SCALE 0.17)
}


@lru_cache(maxsize=4)
def _field(fid):
    d = DARK_CITY[fid]
    f, lab = _form_field(d, (GEN, GEN), d["seed"])
    f = NF.compose_form(f, d["seed"], kind=d["grain"],
                        amount=float(d.get("detail", 0.42)), res=GEN)
    # PLACES: busy zones and calm zones, as every gold standard has (paint-envelope
    # variation 0.19-0.30). A texture equally busy everywhere gives the FOLLOW axis
    # nothing to locate (nocturne -0.21, neon_scar 0.03, amber_vault 0.15). A slow
    # field varies the construction's CONTRAST across the car, never its geometry.
    slow = np.asarray(FK.fbm((GEN, GEN), d["seed"] + 7, octaves=(5, 10, 20),
                             weights=(1.0, 0.6, 0.35)), np.float32)
    slow = (slow - float(slow.min())) / max(float(slow.max() - slow.min()), 1e-6)
    _m = float(f.mean())
    f = np.clip(_m + (f - _m) * (0.50 + 1.0 * slow), 0, 1).astype(np.float32)
    fine = FINE.get(fid)
    if fine is not None:
        form2, params2, w = fine
        f2, _l2 = _form_field({"form": form2, "params": params2}, (GEN, GEN), d["seed"] + 41)
        f2 = np.asarray(f2, np.float32)
        f2 = (f2 - float(f2.min())) / max(float(f2.max() - f2.min()), 1e-6)
        # keyed to the macro's own edges: structure inside the structure
        gy, gx = np.gradient(f)
        key = np.hypot(gx, gy)
        key = key / max(float(np.percentile(key, 98)), 1e-6)
        key = 0.45 + 0.55 * np.clip(key, 0, 1)
        f = np.clip(f * (1.0 - w) + f2 * w * key + f * w * (1.0 - key), 0, 1).astype(np.float32)
    if lab is None:
        lab = NF._labels_from_field(f, d["seed"], 150) if hasattr(NF, "_labels_from_field") else None
    return f, lab


@lru_cache(maxsize=4)
def _art(fid):
    d = DARK_CITY[fid]
    f, lab = _field(fid)
    f = FK.upscale(f, WORK)
    pal = np.asarray(P[d["palette"]], np.float32)

    # THE BRIGHT ARRIVES AS STREAKS, NOT AS A WASH.
    # The first three stops are the dark ground and are spread over the bottom
    # `bright_at` of the field; the single bright stop takes only what is left.
    # That is the owner's "STREAKS of bright coming through the patterns" made
    # into a number rather than a hope.
    t = FK.pct(f)
    b = float(d.get("bright_at", 0.86))
    lowt = np.clip(t / max(b, 1e-3), 0.0, 1.0) * (len(pal) - 2)
    hit = np.clip((t - b) / max(1.0 - b, 1e-3), 0.0, 1.0)
    idx = np.clip(lowt.astype(np.int32), 0, len(pal) - 3)
    frac = np.clip(lowt - idx, 0, 1)[..., None]
    art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
    art = art * (1.0 - hit[..., None]) + pal[-1] * hit[..., None]

    if cv2 is not None:
        g, _k = NF.detail(f, d["seed"] + 3, kind=d["grain"], amount=1.0, res=WORK)
        art = art * (1.0 + (g - 0.5) * 2.0 * float(d["gamt"]))[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    """Dark body, hot edge.

    `edge_max` is deliberately a little wider here than elsewhere: on this shelf
    the lip IS the effect. It is laid on the region boundaries, which are the
    level sets of the artwork, which is exactly where the bright streaks already
    are — so the sharpest material and the brightest colour land on the same
    lines and the finish reads as glistening rather than merely dark.
    """
    d = DARK_CITY[fid]
    f, lab = _field(fid)
    f = FK.upscale(f, res)
    lab = FK.upscale(lab, res) if lab is not None else None
    art = _art(fid)
    if cv2 is not None and art.shape[0] != res:
        art = cv2.resize(np.asarray(art, np.float32), (res, res),
                         interpolation=cv2.INTER_LINEAR)
    # LINEAR bands, by value, not by population.
    #
    # This shelf is value-skewed BY DESIGN: bright_at keeps the bright to the
    # top ten-odd percent of the field, so the paint's detail is concentrated in
    # narrow streaks. Equal-population bands would spend five cards evenly over
    # a canvas that is mostly one dark tone, and the spec would have structure
    # where the paint has none. Cutting by value instead gives the dark ground
    # its own card and hands the rest of the ladder to the streaks — which is
    # where the hot edge belongs. Measured: FOLLOW 0.06-0.35 -> see below.
    kw = dict(bands="linear")
    kw.update(d.get("spec_kw", {}))
    return ST.compose(f, d["deck"], seed=d["seed"], res=res, lab=lab,
                      edge=d["edge"], art=art,
                      edge_max=float(d.get("edge_max", 0.10)), **kw)


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
        return (np.asarray(spec, np.float32) * mm).clip(0, 255).astype(np.uint8)

    paint_fn.__name__ = "paint_" + fid
    spec_fn.__name__ = "spec_" + fid
    return spec_fn, paint_fn



def install_into_engine(mono_reg, base_reg=None):
    n = 0
    for fid in DARK_CITY:
        mono_reg[fid] = _mk(fid)
        n += 1
    return "%d DARK CITY finishes installed" % n


# ── BANDING, CHOSEN PER FINISH ON MEASUREMENT ─────────────────────────────
# Two of the owner's requirements pull against each other here and neither is
# negotiable: the spec must be DIVERSE (quantile bands give every card real
# area — measured 13 distinct materials against 4 for linear) and it must FOLLOW
# the paint (linear bands track this shelf's value-skewed darks far better).
#
# So the mode is not a shelf-wide default. Each finish is measured both ways and
# takes QUANTILE if quantile still passes FOLLOW, LINEAR only where it cannot.
# Result: quantile for 15 of 50, 48/50 passing.
# Per-finish spec composition, MEASURED 2026-09-02 (bands x chips sweep at 1024,
# table in _rebuild/dkc_speckw.json), after the zero-reuse construction pass.
# Owner 2026-09-02: "the damn specs are not interesting enough" — re-swept
# RICHNESS-FIRST: the richest spec (effective materials by area) among the
# settings that still follow the paint (FOLLOW >= 0.35, SCALE >= 0.20).
_DKC_SPECKW = {
    "dkc_wet_asphalt": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_oil_slick": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_manhole_steam": {"bands": "quantile", "chips": 0.34, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_tyre_black": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_tar_seam": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_gutter_chrome": {"bands": "linear", "chips": 0.34, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_night_rain": {"bands": "linear", "chips": 0.34, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_kerb_grit": {"bands": "quantile", "chips": 0.34, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_storm_drain": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_blacktop_heat": {"bands": "linear", "chips": 0.50, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_obsidian_chill": {"bands": "linear", "chips": 0.34, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_basalt_glass": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_hematite": {"bands": "linear", "chips": 0.50, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_tourmaline_black": {"bands": "linear", "chips": 0.34, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_onyx_band": {"bands": "linear", "chips": 0.00, "edge_max": 0.18},
    "dkc_magnetite": {"bands": "linear", "chips": 0.50, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_jet_carve": {"bands": "quantile", "chips": 0.00, "edge_max": 0.18},
    "dkc_shungite": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_anthracite": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_galena_cube": {"bands": "quantile", "chips": 0.50, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_abyss_blue": {"bands": "quantile", "chips": 0.00, "edge_max": 0.10},
    "dkc_midnight_teal": {"bands": "linear", "chips": 0.50, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_ink_well": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_prussian": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_deep_pine": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_bottle_green": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_nocturne": {"bands": "linear", "chips": 0.00, "edge_max": 0.18},
    "dkc_cobalt_night": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_viridian_dark": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_indigo_vault": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_oxblood": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_garnet_dark": {"bands": "linear", "chips": 0.00, "edge_max": 0.10},
    "dkc_ember_gold": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_burgundy": {"bands": "linear", "chips": 0.50, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_dried_rose": {"bands": "quantile", "chips": 0.34, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_brass_night": {"bands": "quantile", "chips": 0.34, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_molten_seam": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_copper_dark": {"bands": "quantile", "chips": 0.34, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_rust_noir": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_amber_vault": {"bands": "linear", "chips": 0.00, "edge_max": 0.18},
    "dkc_arc_weld": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_lightning_black": {"bands": "linear", "chips": 0.00, "edge_max": 0.18},
    "dkc_filament": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_neon_scar": {"bands": "linear", "chips": 0.00, "edge_max": 0.18},
    "dkc_laser_cut": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_plasma_seam": {"bands": "quantile", "chips": 0.34, "edge_max": 0.10, "env_floor": 0.30},
    "dkc_spark_trail": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_hot_wire": {"bands": "quantile", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_tracer": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
    "dkc_flashover": {"bands": "linear", "chips": 0.50, "edge_max": 0.18, "env_floor": 0.30},
}
for _f, _kw in _DKC_SPECKW.items():
    if _f in DARK_CITY:
        _kw = dict(_kw)
        DARK_CITY[_f]["edge_max"] = _kw.pop("edge_max", DARK_CITY[_f].get("edge_max", 0.10))
        DARK_CITY[_f].setdefault("spec_kw", {}).update(_kw)
