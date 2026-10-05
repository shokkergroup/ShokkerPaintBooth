# -*- coding: utf-8 -*-
"""🌍 WORLD OF COLOR — the 2026-08-31 rebuild of COLORSHOXX. 77 → 100.

Owner: *"COLORSHOXX and its 77 finishes was originally designed to try to do
something unique with color flipping. It's outdated and very repetitive now.
I'm thinking of taking that from 77 finishes to 100 and repurposing this to
WORLD OF COLOR which will take colors/styles from various COUNTRIES and making
something out of it. Irish, Scottish, Japanese, African, Jamaican, Australian,
etc."*

WHAT WAS THERE. 77 `cx_*` ids in three generations — `cx_{colour}` singles,
`cx_{a}_{b}` duos, then `cx_hyperflip_{a}_{b}`. Measured, the specs were the
tell: **median 2 distinct material cards over 2 families**, roughness sigma
**7.0** and clearcoat sigma **2.5** — the spec channel was two flat cards, so
every card's "flip" was the paint doing it alone, 77 times, from the same
handful of engines.

THE IDEA. Twenty places, five finishes each, and each finish is a MATERIAL OR
PROCESS that place actually makes colour with. Not a flag, not a stereotype — a
tartan sett, an indigo vat, a celadon glaze, an ochre bed, a salt terrace.

That scope is drawn deliberately. SPB already has five CULTURAL shelves built on
flags and iconography (RISING SUN, UNION JACKED, VIVA MEXICO, FORBIDDEN DRAGON,
LET FREEDOM RING). Coming at the world through CRAFT instead means this shelf
cannot become a second copy of those, and where the two touch the same country
they are looking at different things — Rising Sun has the flag; here Japan is an
indigo vat, an urushi table and a raku kiln.

Everything is drawn from commercially made textiles, ceramics, minerals and
landscape. Sacred and ceremonial designs are not source material for car paint
and none are used.

  🌍 EUROPE    Ireland · Scotland · Portugal · Norway
  🌏 ASIA      Japan · India · Türkiye · Korea
  🌍 AFRICA    Morocco · Mali · Egypt · Ethiopia
  🌎 AMERICAS  Jamaica · Brazil · Peru · Cuba
  🌏 OCEANIA   Australia · Aotearoa · Indonesia · Philippines
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

import engine.expansions.world_of_color_kit_2026 as WK
from engine.paint_v2 import spec_cards as SC

ID_PREFIX = "woc_"
GROUP = "🌍 WORLD OF COLOR"
GEN = 1024
WORK = 1152

CHAPTERS = {"europe": "🌍 EUROPE", "asia": "🌏 ASIA", "africa": "🌍 AFRICA",
            "americas": "🌎 AMERICAS", "oceania": "🌏 OCEANIA"}

_STRUCTS = {
    "sett":      lambda sh, sd, k: (WK.sett(sh, sd, **k), None),
    "stars":     lambda sh, sd, k: (WK.stars(sh, sd, **k), None),
    "ikat":      lambda sh, sd, k: (WK.ikat(sh, sd, **k), None),
    "resist":    lambda sh, sd, k: WK.resist(sh, sd, **k),
    "cells":     lambda sh, sd, k: WK.worley(sh, sd, **k),
    "braid":     lambda sh, sd, k: (WK.kh_braid(sh, sd, **k), None),
    "filaments": lambda sh, sd, k: (WK.filaments(sh, sd, **k), None),
    "dendrite":  lambda sh, sd, k: (WK.dla(sh, sd, **k), None),
    "curl":      lambda sh, sd, k: (WK.curl(sh, sd, **k), None),
    "percolate": lambda sh, sd, k: WK.percolate(sh, sd, **k),
    "spall":     lambda sh, sd, k: WK.spall(sh, sd, **k),
    "crack":     lambda sh, sd, k: WK.anneal_crack(sh, sd, **k),
    "craters":   lambda sh, sd, k: (WK.craters(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (WK.dunes(sh, sd, **k), None),
    "polygons":  lambda sh, sd, k: WK.polygons(sh, sd, **k),
    "honeycomb": lambda sh, sd, k: WK.honeycomb(sh, sd, **k),
    "bands":     lambda sh, sd, k: (WK.bands(sh, sd, **k), None),
    "wrinkle":   lambda sh, sd, k: (WK.wrinkle(sh, sd, **k), None),
    "sparks":    lambda sh, sd, k: (WK.sparks(sh, sd, **k), None),
    "eden":      lambda sh, sd, k: (WK.eden(sh, sd, **k), None),
    "crinkle":   lambda sh, sd, k: (WK.crinkle(sh, sd, **k), None),
}

# ── palettes, one per finish family, taken from the real material ───────────
P = {
    # EUROPE
    "aran":       ((0.42, 0.40, 0.35), (0.68, 0.66, 0.59), (0.86, 0.84, 0.78), (0.98, 0.97, 0.94)),
    "peat":       ((0.09, 0.06, 0.04), (0.26, 0.18, 0.11), (0.46, 0.34, 0.21), (0.70, 0.58, 0.40)),
    "connemara":  ((0.06, 0.13, 0.08), (0.20, 0.36, 0.24), (0.42, 0.58, 0.42), (0.74, 0.84, 0.70)),
    "stout":      ((0.05, 0.03, 0.02), (0.16, 0.10, 0.06), (0.60, 0.50, 0.36), (0.95, 0.90, 0.78)),
    "burren":     ((0.28, 0.30, 0.28), (0.52, 0.55, 0.52), (0.74, 0.77, 0.74), (0.93, 0.95, 0.93)),
    "tartan":     ((0.06, 0.09, 0.16), (0.36, 0.08, 0.10), (0.16, 0.32, 0.22), (0.86, 0.76, 0.44)),
    "tweed":      ((0.16, 0.15, 0.12), (0.38, 0.34, 0.26), (0.58, 0.54, 0.44), (0.80, 0.78, 0.68)),
    "cairngorm":  ((0.14, 0.12, 0.13), (0.36, 0.32, 0.34), (0.60, 0.55, 0.56), (0.86, 0.83, 0.84)),
    "heather":    ((0.10, 0.08, 0.14), (0.30, 0.20, 0.38), (0.54, 0.38, 0.60), (0.82, 0.70, 0.86)),
    "cask":       ((0.10, 0.05, 0.02), (0.32, 0.16, 0.05), (0.60, 0.36, 0.12), (0.88, 0.68, 0.34)),
    "azulejo":    ((0.06, 0.10, 0.24), (0.14, 0.26, 0.54), (0.40, 0.56, 0.80), (0.90, 0.94, 0.98)),
    "cork_bark":  ((0.18, 0.13, 0.08), (0.44, 0.34, 0.20), (0.68, 0.56, 0.38), (0.90, 0.82, 0.62)),
    "calcada":    ((0.10, 0.10, 0.11), (0.34, 0.34, 0.34), (0.66, 0.66, 0.65), (0.94, 0.94, 0.92)),
    "sardine":    ((0.14, 0.16, 0.18), (0.38, 0.42, 0.46), (0.64, 0.68, 0.72), (0.90, 0.92, 0.95)),
    "douro":      ((0.12, 0.10, 0.10), (0.30, 0.26, 0.24), (0.52, 0.44, 0.38), (0.78, 0.70, 0.60)),
    "rosemaling": ((0.08, 0.06, 0.10), (0.34, 0.10, 0.14), (0.20, 0.40, 0.34), (0.92, 0.84, 0.62)),
    "fjord":      ((0.05, 0.10, 0.12), (0.12, 0.28, 0.34), (0.32, 0.54, 0.60), (0.72, 0.88, 0.92)),
    "birch":      ((0.20, 0.19, 0.17), (0.52, 0.50, 0.46), (0.80, 0.78, 0.74), (0.98, 0.97, 0.95)),
    "arctic":     ((0.10, 0.13, 0.20), (0.26, 0.36, 0.52), (0.52, 0.66, 0.80), (0.88, 0.94, 0.99)),
    "nor_slate":  ((0.11, 0.12, 0.13), (0.28, 0.30, 0.32), (0.48, 0.51, 0.54), (0.74, 0.77, 0.80)),
    # ASIA
    "aizome":     ((0.03, 0.06, 0.13), (0.08, 0.16, 0.34), (0.20, 0.34, 0.58), (0.62, 0.74, 0.88)),
    "urushi":     ((0.05, 0.02, 0.02), (0.24, 0.05, 0.05), (0.52, 0.14, 0.12), (0.84, 0.46, 0.36)),
    "raku":       ((0.06, 0.06, 0.07), (0.22, 0.22, 0.24), (0.48, 0.46, 0.44), (0.82, 0.78, 0.72)),
    "kintsugi":   ((0.10, 0.10, 0.12), (0.30, 0.30, 0.33), (0.72, 0.58, 0.22), (0.98, 0.88, 0.52)),
    "washi":      ((0.32, 0.30, 0.26), (0.60, 0.58, 0.52), (0.82, 0.80, 0.74), (0.97, 0.96, 0.92)),
    "blockprint": ((0.10, 0.06, 0.06), (0.42, 0.14, 0.14), (0.70, 0.36, 0.26), (0.95, 0.80, 0.60)),
    "madras":     ((0.08, 0.12, 0.10), (0.42, 0.18, 0.12), (0.20, 0.44, 0.34), (0.92, 0.86, 0.50)),
    "marigold":   ((0.20, 0.09, 0.02), (0.56, 0.26, 0.03), (0.84, 0.50, 0.08), (0.99, 0.80, 0.34)),
    "shisha":     ((0.14, 0.06, 0.14), (0.42, 0.14, 0.38), (0.68, 0.36, 0.60), (0.94, 0.78, 0.90)),
    "jali":       ((0.24, 0.18, 0.14), (0.52, 0.42, 0.32), (0.76, 0.66, 0.54), (0.95, 0.90, 0.80)),
    "iznik":      ((0.05, 0.08, 0.18), (0.10, 0.30, 0.44), (0.36, 0.62, 0.68), (0.92, 0.95, 0.96)),
    "kilim":      ((0.12, 0.05, 0.06), (0.44, 0.14, 0.12), (0.24, 0.34, 0.30), (0.90, 0.76, 0.44)),
    "meerschaum": ((0.34, 0.31, 0.26), (0.62, 0.58, 0.50), (0.84, 0.80, 0.70), (0.98, 0.96, 0.90)),
    "copper_ham": ((0.16, 0.08, 0.04), (0.46, 0.24, 0.10), (0.74, 0.44, 0.22), (0.96, 0.72, 0.46)),
    "nazar":      ((0.03, 0.07, 0.18), (0.08, 0.24, 0.52), (0.34, 0.58, 0.84), (0.92, 0.96, 0.99)),
    "celadon":    ((0.14, 0.22, 0.20), (0.34, 0.50, 0.44), (0.58, 0.74, 0.66), (0.88, 0.96, 0.90)),
    "bojagi":     ((0.14, 0.10, 0.16), (0.44, 0.20, 0.28), (0.30, 0.48, 0.56), (0.94, 0.90, 0.72)),
    "dancheong":  ((0.06, 0.10, 0.12), (0.16, 0.34, 0.36), (0.52, 0.16, 0.16), (0.94, 0.86, 0.52)),
    "hanji":      ((0.34, 0.32, 0.27), (0.62, 0.60, 0.53), (0.84, 0.82, 0.75), (0.98, 0.97, 0.93)),
    "najeon":     ((0.05, 0.05, 0.07), (0.20, 0.22, 0.28), (0.56, 0.66, 0.72), (0.92, 0.95, 0.98)),
    # AFRICA
    "zellij":     ((0.05, 0.09, 0.12), (0.12, 0.30, 0.34), (0.60, 0.26, 0.16), (0.94, 0.92, 0.86)),
    "tadelakt":   ((0.24, 0.18, 0.14), (0.52, 0.40, 0.32), (0.76, 0.64, 0.54), (0.95, 0.89, 0.82)),
    "saffron":    ((0.24, 0.11, 0.02), (0.60, 0.30, 0.04), (0.86, 0.54, 0.10), (0.99, 0.82, 0.38)),
    "tannery":    ((0.14, 0.09, 0.04), (0.44, 0.30, 0.10), (0.72, 0.56, 0.22), (0.96, 0.86, 0.50)),
    "cedar":      ((0.12, 0.09, 0.05), (0.34, 0.24, 0.13), (0.56, 0.42, 0.24), (0.82, 0.70, 0.48)),
    "bogolan":    ((0.09, 0.07, 0.05), (0.28, 0.22, 0.16), (0.62, 0.56, 0.46), (0.94, 0.92, 0.86)),
    "kente":      ((0.10, 0.08, 0.04), (0.46, 0.12, 0.10), (0.16, 0.36, 0.26), (0.96, 0.80, 0.16)),
    "indigo_w":   ((0.04, 0.06, 0.12), (0.10, 0.18, 0.34), (0.26, 0.38, 0.58), (0.72, 0.82, 0.92)),
    "brass_cast": ((0.14, 0.10, 0.03), (0.42, 0.31, 0.09), (0.70, 0.56, 0.20), (0.94, 0.85, 0.50)),
    "laterite":   ((0.16, 0.07, 0.04), (0.46, 0.20, 0.10), (0.72, 0.40, 0.22), (0.94, 0.68, 0.44)),
    "faience":    ((0.04, 0.14, 0.18), (0.10, 0.36, 0.44), (0.32, 0.64, 0.70), (0.86, 0.95, 0.96)),
    "lapis":      ((0.03, 0.05, 0.18), (0.08, 0.14, 0.44), (0.22, 0.32, 0.70), (0.72, 0.80, 0.96)),
    "alabaster":  ((0.36, 0.33, 0.27), (0.66, 0.62, 0.53), (0.86, 0.83, 0.74), (0.99, 0.98, 0.93)),
    "papyrus":    ((0.26, 0.20, 0.11), (0.56, 0.46, 0.27), (0.80, 0.71, 0.50), (0.97, 0.92, 0.76)),
    "desertglass":((0.16, 0.18, 0.12), (0.44, 0.48, 0.32), (0.72, 0.76, 0.56), (0.95, 0.97, 0.84)),
    "coffee":     ((0.08, 0.05, 0.03), (0.26, 0.15, 0.08), (0.50, 0.32, 0.18), (0.78, 0.60, 0.40)),
    "basalt_hi":  ((0.08, 0.09, 0.10), (0.22, 0.24, 0.26), (0.42, 0.45, 0.48), (0.68, 0.72, 0.76)),
    "shamma":     ((0.36, 0.35, 0.32), (0.64, 0.63, 0.58), (0.86, 0.85, 0.80), (0.98, 0.97, 0.94)),
    "lalibela":   ((0.14, 0.08, 0.05), (0.40, 0.24, 0.14), (0.66, 0.46, 0.30), (0.90, 0.76, 0.58)),
    "saltflat":   ((0.30, 0.31, 0.32), (0.60, 0.62, 0.64), (0.84, 0.86, 0.88), (0.99, 1.00, 1.00)),
    # AMERICAS
    "soundsys":   ((0.05, 0.05, 0.06), (0.20, 0.18, 0.16), (0.44, 0.40, 0.34), (0.76, 0.72, 0.62)),
    "rasta":      ((0.08, 0.10, 0.06), (0.14, 0.36, 0.16), (0.78, 0.62, 0.06), (0.72, 0.12, 0.10)),
    "bluemtn":    ((0.05, 0.09, 0.12), (0.14, 0.28, 0.32), (0.34, 0.52, 0.50), (0.72, 0.86, 0.84)),
    "seaglass":   ((0.14, 0.24, 0.24), (0.36, 0.56, 0.54), (0.62, 0.80, 0.76), (0.92, 0.98, 0.96)),
    "allspice":   ((0.10, 0.07, 0.04), (0.30, 0.20, 0.11), (0.54, 0.40, 0.24), (0.82, 0.68, 0.48)),
    "carnival":   ((0.10, 0.05, 0.14), (0.52, 0.10, 0.34), (0.14, 0.52, 0.42), (0.98, 0.84, 0.20)),
    "amazon":     ((0.03, 0.09, 0.05), (0.10, 0.28, 0.14), (0.26, 0.50, 0.26), (0.62, 0.80, 0.48)),
    "tourmaline": ((0.06, 0.12, 0.10), (0.16, 0.36, 0.28), (0.52, 0.24, 0.34), (0.90, 0.76, 0.82)),
    "calcadao":   ((0.12, 0.12, 0.13), (0.36, 0.36, 0.36), (0.68, 0.68, 0.67), (0.95, 0.95, 0.94)),
    "cocoa":      ((0.09, 0.05, 0.03), (0.28, 0.16, 0.09), (0.52, 0.34, 0.20), (0.80, 0.62, 0.42)),
    "alpaca":     ((0.20, 0.17, 0.14), (0.46, 0.40, 0.34), (0.70, 0.65, 0.58), (0.92, 0.90, 0.85)),
    "andes":      ((0.14, 0.11, 0.10), (0.40, 0.28, 0.22), (0.66, 0.52, 0.40), (0.90, 0.82, 0.70)),
    "cusco":      ((0.10, 0.06, 0.08), (0.44, 0.12, 0.16), (0.18, 0.36, 0.44), (0.96, 0.82, 0.34)),
    "chicha":     ((0.16, 0.06, 0.06), (0.48, 0.16, 0.14), (0.76, 0.40, 0.26), (0.96, 0.76, 0.48)),
    "salt_ter":   ((0.28, 0.26, 0.24), (0.58, 0.56, 0.52), (0.82, 0.80, 0.76), (0.99, 0.98, 0.96)),
    "havana":     ((0.10, 0.14, 0.16), (0.28, 0.44, 0.46), (0.72, 0.52, 0.30), (0.96, 0.90, 0.74)),
    "tobacco":    ((0.11, 0.07, 0.04), (0.32, 0.22, 0.12), (0.56, 0.42, 0.24), (0.84, 0.70, 0.48)),
    "malecon":    ((0.10, 0.13, 0.14), (0.30, 0.38, 0.38), (0.56, 0.64, 0.62), (0.86, 0.92, 0.90)),
    "vintagelac": ((0.06, 0.08, 0.14), (0.16, 0.28, 0.48), (0.40, 0.56, 0.76), (0.84, 0.92, 0.98)),
    "sugar":      ((0.30, 0.28, 0.24), (0.60, 0.56, 0.48), (0.84, 0.80, 0.72), (0.99, 0.97, 0.92)),
    # OCEANIA
    "ochre":      ((0.16, 0.07, 0.03), (0.46, 0.22, 0.08), (0.74, 0.44, 0.18), (0.95, 0.72, 0.40)),
    "varnish":    ((0.10, 0.07, 0.05), (0.28, 0.18, 0.12), (0.48, 0.34, 0.24), (0.72, 0.58, 0.44)),
    "opal":       ((0.06, 0.08, 0.12), (0.18, 0.34, 0.36), (0.56, 0.30, 0.48), (0.92, 0.90, 0.66)),
    "saltpan":    ((0.32, 0.30, 0.28), (0.62, 0.60, 0.56), (0.85, 0.84, 0.80), (0.99, 0.99, 0.97)),
    "eucalypt":   ((0.14, 0.14, 0.11), (0.36, 0.38, 0.30), (0.62, 0.62, 0.52), (0.88, 0.88, 0.78)),
    "greenstone": ((0.04, 0.10, 0.07), (0.12, 0.30, 0.20), (0.30, 0.52, 0.38), (0.66, 0.82, 0.68)),
    "blacksand":  ((0.05, 0.05, 0.06), (0.18, 0.18, 0.20), (0.38, 0.38, 0.40), (0.66, 0.66, 0.68)),
    "kauri":      ((0.18, 0.11, 0.03), (0.50, 0.32, 0.08), (0.78, 0.56, 0.20), (0.98, 0.84, 0.48)),
    "fern":       ((0.05, 0.11, 0.06), (0.16, 0.32, 0.16), (0.36, 0.56, 0.32), (0.72, 0.86, 0.58)),
    "geothermal": ((0.12, 0.10, 0.06), (0.38, 0.30, 0.12), (0.66, 0.56, 0.24), (0.92, 0.88, 0.56)),
    "batik":      ((0.08, 0.06, 0.04), (0.28, 0.18, 0.08), (0.56, 0.42, 0.20), (0.88, 0.80, 0.56)),
    "ikat_ind":   ((0.10, 0.05, 0.05), (0.38, 0.12, 0.12), (0.24, 0.30, 0.42), (0.92, 0.84, 0.62)),
    "volcanic":   ((0.06, 0.06, 0.07), (0.20, 0.20, 0.22), (0.40, 0.40, 0.42), (0.70, 0.68, 0.68)),
    "teak":       ((0.14, 0.10, 0.05), (0.38, 0.28, 0.14), (0.62, 0.48, 0.26), (0.88, 0.76, 0.50)),
    "spice":      ((0.18, 0.08, 0.03), (0.50, 0.24, 0.06), (0.78, 0.48, 0.14), (0.97, 0.78, 0.40)),
    "capiz":      ((0.30, 0.31, 0.30), (0.60, 0.62, 0.60), (0.82, 0.85, 0.84), (0.98, 0.99, 0.99)),
    "abaca":      ((0.24, 0.21, 0.15), (0.52, 0.47, 0.36), (0.76, 0.71, 0.58), (0.95, 0.92, 0.82)),
    "jeepney":    ((0.08, 0.06, 0.12), (0.44, 0.10, 0.28), (0.16, 0.40, 0.52), (0.96, 0.84, 0.24)),
    "terraces":   ((0.08, 0.12, 0.07), (0.22, 0.36, 0.18), (0.46, 0.60, 0.36), (0.80, 0.88, 0.64)),
    "mayon":      ((0.07, 0.07, 0.08), (0.22, 0.22, 0.24), (0.44, 0.42, 0.42), (0.74, 0.70, 0.66)),
}


def _floor_ground(pal, lo):
    """Coverage 2026-09-02: lapis (starfield on a 0.06 ground) measured 0.66 of
    the canvas near-black, najeon 0.53. A dark ground still has to read as a
    colour on the car; lift only the darkest stop, hue preserved."""
    c = pal[0]
    l = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    if l >= lo:
        return pal
    k = lo / max(l, 1e-3)
    return (tuple(min(1.0, float(v) * k) for v in c),) + tuple(pal[1:])


for _k, _lo in (("lapis", 0.10), ("najeon", 0.09), ("urushi", 0.08)):
    if _k in P:
        P[_k] = _floor_ground(P[_k], _lo)

# ── material decks, by what the thing is made of ────────────────────────────
D_CLOTH  = (("clear_matte", 0.28), ("frozen_metal", 0.50), ("vinyl", 0.68),
            ("pearl", 0.84), ("gloss_carbon", 0.95), ("spectraflame", 1.01))
D_GLAZE  = (("ceramic_matte", 0.26), ("sea_glass", 0.48), ("milk_glass", 0.66),
            ("ceramic_gloss", 0.82), ("liquid_glaze", 0.94), ("chrome", 1.01))
D_STONE  = (("ceramic_matte", 0.26), ("bead_blast", 0.48), ("satin_carbon", 0.66),
            ("brushed_ti", 0.83), ("gloss_carbon", 0.94), ("dark_chrome", 1.01))
D_METAL  = (("patina", 0.26), ("satin_carbon", 0.48), ("brushed_ti", 0.66),
            ("galvanized", 0.83), ("candy", 0.94), ("mercury", 1.01))
D_LACQUER= (("eggshell", 0.26), ("powder", 0.48), ("soft_gloss", 0.66),
            ("candy", 0.83), ("candy_chrome", 0.94), ("chrome", 1.01))
D_WATER  = (("frozen_film", 0.26), ("sea_glass", 0.48), ("gloss", 0.66),
            ("wet", 0.83), ("liquid_glaze", 0.94), ("mercury", 1.01))
D_EARTH  = (("void", 0.28), ("ceramic_matte", 0.50), ("patina", 0.68),
            ("satin_carbon", 0.84), ("metallic", 0.95), ("antique_chrome", 1.01))
D_SHELL  = (("clear_matte", 0.26), ("frozen_film", 0.48), ("milk_glass", 0.66),
            ("pearl", 0.83), ("spectraflame", 0.94), ("candy_chrome", 1.01))
D_WOOD   = (("matte", 0.28), ("powder", 0.50), ("satin_carbon", 0.68),
            ("metallic", 0.84), ("soft_gloss", 0.95), ("dark_chrome", 1.01))
D_FIRE   = (("flat_black", 0.28), ("ceramic_matte", 0.50), ("patina", 0.68),
            ("carrier_low", 0.84), ("carrier_mid", 0.95), ("carrier_high", 1.01))



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

def R(name, chapter, nation, palette, deck, seed, stack, mix="sum", edge="chrome",
      r_spread=26.0, gamma=1.0, dither=0.15, desc=""):
    return dict(name=name, chapter=chapter, nation=nation, palette=palette,
                bands=deck, seed=seed, stack=stack, mix=mix, edge=edge,
                r_spread=r_spread, gamma=gamma, dither=dither, desc=desc)


_ROWS = [
    # ══════════════════════ 🌍 EUROPE ══════════════════════════════════════
    # ── Ireland
    R("Aran Cable", "europe", "Ireland", "aran", D_CLOTH, 8101,
      [("braid", 1.0, dict(layers=104, shear=1.6)), ("filaments", 0.7, dict(n=2000, length=15, wander=0.7))],
      desc="Honeycomb and cable worked in undyed bainin wool, every stitch countable."),
    R("Peat Cut", "europe", "Ireland", "peat", D_EARTH, 8102,
      [("bands", 1.0, dict(n=84, shear=1.2, vortex=6, turb=0.32)), ("percolate", 0.6, dict(cells=170))],
      desc="A turf bank sliced open — ten thousand years of bog laid down in readable courses."),
    R("Connemara Marble", "europe", "Ireland", "connemara", D_STONE, 8103,
      [("curl", 1.0, dict(scale=54, steps=20)), ("crack", 0.55, dict(cells=118, gen=1))],
      desc="Serpentine marble from the west — green banding folded by four hundred million years."),
    R("Stout Head", "europe", "Ireland", "stout", D_WATER, 8104,
      [("percolate", 1.0, dict(cells=196, p=0.5)), ("craters", 0.6, dict(n=3000, rmax=4.5))],
      desc="Nitrogen cascade settling into a cream head over black. The surge is the whole point."),
    R("Burren Pavement", "europe", "Ireland", "burren", D_STONE, 8105,
      [("crack", 1.0, dict(cells=96, width=3.2, gen=1)), ("craters", 0.55, dict(n=2200, rmax=5.5))],
      desc="Limestone pavement scored into clints and grykes by rain that took its time."),
    # ── Scotland
    R("Tartan Sett", "europe", "Scotland", "tartan", D_CLOTH, 8111,
      [("sett", 1.0, dict(pitch=48, stripes=(0.32, 0.08, 0.06, 0.20, 0.06, 0.10)))],
      desc="One sequence of threads, reflected about its pivots and run both ways. Order you can wear."),
    R("Harris Tweed", "europe", "Scotland", "tweed", D_CLOTH, 8112,
      [("braid", 1.0, dict(layers=118, shear=2.2)), ("cells", 0.7, dict(cells=150))],
      desc="Handwoven in the Outer Hebrides from dyed-in-the-wool yarn, so the colour is IN the fibre."),
    R("Cairngorm Granite", "europe", "Scotland", "cairngorm", D_STONE, 8113,
      [("cells", 1.0, dict(cells=132)), ("sparks", 0.6, dict(n=2600, life=20))],
      desc="Coarse pink granite with smoky quartz in it, every crystal a different mind."),
    R("Heather Moor", "europe", "Scotland", "heather", D_EARTH, 8114,
      [("filaments", 1.0, dict(n=3000, length=11, wander=0.9)),
       ("eden", 0.7, dict(seeds=2000, steps=9)), ("cells", 0.5, dict(cells=166))],
      desc="Ling in full flower over peat — purple to the horizon and knee-deep in it."),
    R("Cask Char", "europe", "Scotland", "cask", D_FIRE, 8115,
      [("crack", 1.0, dict(cells=124, width=2.4, gen=1)), ("craters", 0.6, dict(n=2600, rmax=5.5))],
      desc="Level four char on American oak. The alligator skin inside is what makes the whisky."),
    # ── Portugal
    R("Azulejo Blue", "europe", "Portugal", "azulejo", D_GLAZE, 8121,
      [("stars", 1.0, dict(cell=138, points=8)), ("crack", 0.5, dict(cells=130, width=1.8, gen=1))],
      desc="Cobalt on tin glaze, tile after tile up a whole façade, crazed by two centuries of weather."),
    R("Cork Bark", "europe", "Portugal", "cork_bark", D_WOOD, 8122,
      [("percolate", 1.0, dict(cells=182, p=0.5)), ("bands", 0.6, dict(n=70, vortex=9, turb=0.4))],
      desc="Stripped every nine years and it grows back. Nothing else on earth does this."),
    R("Calçada Wave", "europe", "Portugal", "calcada", D_STONE, 8123,
      [("polygons", 1.0, dict(cells=118, relief=0.62)), ("curl", 0.55, dict(scale=58, steps=16))],
      desc="Black and white limestone cubes set by hand into a rolling wave, a pavement you notice."),
    R("Sardine Tin", "europe", "Portugal", "sardine", D_METAL, 8124,
      [("ikat", 1.0, dict(rows=44, motifs=980, blur=5, sharp=1.6)),
       ("cells", 0.6, dict(cells=158))],
      desc="Packed nose to tail in oil, under a lithographed lid brighter than the fish."),
    R("Douro Schist", "europe", "Portugal", "douro", D_STONE, 8125,
      [("spall", 1.0, dict(cells=112, lift=0.6)), ("bands", 0.6, dict(n=76, vortex=8))],
      desc="Terraces cut into schist so the vines can find water. The rock is the terroir."),
    # ── Norway
    R("Rosemaling", "europe", "Norway", "rosemaling", D_LACQUER, 8131,
      [("curl", 1.0, dict(scale=26, steps=20)),
       ("filaments", 0.75, dict(n=1500, length=34, wander=0.75)),
       ("cells", 0.45, dict(cells=162))],
      desc="Rose painting on a dowry chest — C-scrolls and cross-hatched flowers, freehand, no pencil."),
    R("Fjord Water", "europe", "Norway", "fjord", D_WATER, 8132,
      [("curl", 1.0, dict(scale=62, steps=18)), ("crinkle", 0.6, dict(scale=140, sharp=2.2))],
      desc="Meltwater over a drowned glacial valley, cold enough to change the colour of the light."),
    R("Birch Bark", "europe", "Norway", "birch", D_WOOD, 8133,
      [("bands", 1.0, dict(n=110, shear=0.8, vortex=3, turb=0.28)), ("filaments", 0.6, dict(n=1800, length=20))],
      desc="Paper birch peeling in horizontal ribbons, each lenticel a dark dash across the white."),
    R("Arctic Light", "europe", "Norway", "arctic", D_WATER, 8134,
      [("curl", 1.0, dict(scale=72, steps=24)), ("filaments", 0.55, dict(n=1500, length=34, wander=0.5))],
      desc="Two hours of blue dusk that never becomes day, in the week either side of solstice."),
    R("Slate Roof", "europe", "Norway", "nor_slate", D_STONE, 8135,
      [("spall", 1.0, dict(cells=98, lift=0.68)), ("crack", 0.55, dict(cells=116, gen=1))],
      desc="Riven slate hung in courses, thick at the eave and thin at the ridge, good for four hundred years."),

    # ══════════════════════ 🌏 ASIA ═════════════════════════════════════════
    # ── Japan
    R("Aizome Vat", "asia", "Japan", "aizome", D_CLOTH, 8201,
      [("resist", 1.0, dict(cells=158, crackle=0.9)), ("braid", 0.6, dict(layers=110, shear=1.4))],
      desc="Fermented indigo. The cloth comes out green and turns blue in the air while you watch."),
    R("Urushi Lacquer", "asia", "Japan", "urushi", D_LACQUER, 8202,
      [("curl", 1.0, dict(scale=40, steps=24)), ("cells", 0.55, dict(cells=176))],
      desc="Forty coats of tree sap, each cured in a damp box and polished back with charcoal."),
    R("Raku Crackle", "asia", "Japan", "raku", D_GLAZE, 8203,
      [("crack", 1.0, dict(cells=142, width=2.0, gen=1)), ("percolate", 0.6, dict(cells=170))],
      desc="Pulled from the kiln red hot and thrown into sawdust. The crazing is the record of the shock."),
    R("Kintsugi Seam", "asia", "Japan", "kintsugi", D_METAL, 8204,
      [("crack", 1.0, dict(cells=88, width=3.6, gen=1)), ("cells", 0.6, dict(cells=150))],
      desc="The break repaired in gold rather than hidden, so the history is the most valuable part."),
    R("Washi Fibre", "asia", "Japan", "washi", D_CLOTH, 8205,
      [("filaments", 1.0, dict(n=2800, length=16, wander=0.85)), ("cells", 0.6, dict(cells=168))],
      desc="Kozo bark beaten and floated — long fibres locked into a sheet strong enough to be a wall."),
    # ── India
    R("Block Print", "asia", "India", "blockprint", D_CLOTH, 8211,
      [("stars", 1.0, dict(cell=112, points=6, ring=0.3)), ("resist", 0.55, dict(cells=164, crackle=0.6))],
      desc="Hand-cut teak blocks, one per colour, walked across the cloth by eye and never quite in register."),
    R("Madras Check", "asia", "India", "madras", D_CLOTH, 8212,
      [("sett", 1.0, dict(pitch=42, stripes=(0.26, 0.14, 0.08, 0.24, 0.10, 0.18), twill=5))],
      desc="Handloom cotton in vegetable dye, made to bleed — the fading is a feature you pay for."),
    R("Marigold Mound", "asia", "India", "marigold", D_EARTH, 8213,
      [("craters", 1.0, dict(n=4600, rmax=8.0, rim=0.75, power=1.8)),
       ("cells", 0.85, dict(cells=146)), ("eden", 0.5, dict(seeds=2200, steps=8))],
      desc="Genda strung by the kilometre and heaped at the flower market, orange past the point of sense."),
    R("Mirror Work", "asia", "India", "shisha", D_SHELL, 8214,
      [("craters", 1.0, dict(n=4200, rmax=9.0, rim=1.0, power=1.6)),
       ("braid", 0.8, dict(layers=98, shear=1.8)), ("cells", 0.4, dict(cells=170))],
      desc="Shisha discs caught under a ring of chain stitch, so a whole skirt throws light back at you."),
    R("Sandstone Jali", "asia", "India", "jali", D_STONE, 8215,
      [("stars", 1.0, dict(cell=126, points=12, interlace=1.0)), ("cells", 0.5, dict(cells=160))],
      desc="A screen carved from one slab, cutting the sun into geometry and letting the wind through."),
    # ── Türkiye
    R("Iznik Tile", "asia", "Türkiye", "iznik", D_GLAZE, 8221,
      [("stars", 1.0, dict(cell=134, points=10)), ("crack", 0.5, dict(cells=136, width=1.6, gen=1))],
      desc="Quartz-bodied tile under a clear glaze — cobalt, turquoise, and the red that took a century to get."),
    R("Kilim Weave", "asia", "Türkiye", "kilim", D_CLOTH, 8222,
      [("ikat", 1.0, dict(rows=52, motifs=1150, blur=3, sharp=1.9)),
       ("braid", 0.9, dict(layers=112, shear=1.2))],
      desc="Slit-woven flatweave — no pile, so the pattern is the structure and it reads both sides."),
    R("Meerschaum", "asia", "Türkiye", "meerschaum", D_STONE, 8223,
      [("percolate", 1.0, dict(cells=188, p=0.48)), ("craters", 0.55, dict(n=2600, rmax=5.0))],
      desc="Sepiolite carved wet and soft, then smoked for thirty years until it goes amber from the inside."),
    R("Hammered Copper", "asia", "Türkiye", "copper_ham", D_METAL, 8224,
      [("craters", 1.0, dict(n=2000, rmax=9.0, rim=0.7)), ("cells", 0.6, dict(cells=146))],
      desc="Planished by hand in the coppersmiths' bazaar, every facet a hammer blow you can count."),
    R("Nazar Glass", "asia", "Türkiye", "nazar", D_GLAZE, 8225,
      [("craters", 1.0, dict(n=2400, rmax=7.5, rim=0.9)), ("curl", 0.5, dict(scale=50, steps=16))],
      desc="Cobalt glass rings, wound hot on the rod and hung anywhere luck is needed."),
    # ── Korea
    R("Celadon Glaze", "asia", "Korea", "celadon", D_GLAZE, 8231,
      [("crack", 1.0, dict(cells=150, width=1.7, gen=1)), ("curl", 0.55, dict(scale=64, steps=14))],
      desc="Goryeo green — iron reduced in a starved kiln until it goes the colour of shallow water."),
    R("Bojagi Patch", "asia", "Korea", "bojagi", D_CLOTH, 8232,
      [("polygons", 1.0, dict(cells=104, relief=0.4)), ("filaments", 0.6, dict(n=2000, length=14))],
      desc="Wrapping cloth pieced from offcuts, seams flat-felled so it reads from either side."),
    R("Dancheong", "asia", "Korea", "dancheong", D_LACQUER, 8233,
      [("stars", 1.0, dict(cell=120, points=6, interlace=0.8)), ("bands", 0.55, dict(n=88, vortex=6))],
      desc="Mineral pigment on temple timber — it is decoration, and it is also what stops the wood rotting."),
    R("Hanji Sheet", "asia", "Korea", "hanji", D_CLOTH, 8234,
      [("filaments", 1.0, dict(n=2600, length=15, wander=0.8)), ("wrinkle", 0.55, dict(k=1.0, steps=14))],
      desc="Mulberry paper couched a hundred times. Strong enough to floor a room and be walked on."),
    R("Najeon Inlay", "asia", "Korea", "najeon", D_SHELL, 8235,
      [("spall", 1.0, dict(cells=132, lift=0.55)), ("craters", 0.55, dict(n=2400, rmax=5.5))],
      desc="Abalone cut into hairlines and laid into black lacquer, so the light moves when you do."),

    # ══════════════════════ 🌍 AFRICA ═══════════════════════════════════════
    # ── Morocco
    R("Zellij Star", "africa", "Morocco", "zellij", D_GLAZE, 8301,
      [("stars", 1.0, dict(cell=128, points=8, interlace=1.0)), ("crack", 0.45, dict(cells=140, gen=1))],
      desc="Every piece chipped to shape by hand from a fired tile and set face-down into the bed."),
    R("Tadelakt", "africa", "Morocco", "tadelakt", D_STONE, 8302,
      [("curl", 1.0, dict(scale=56, steps=18)), ("cells", 0.6, dict(cells=164))],
      desc="Lime plaster burnished with a river stone and sealed with black soap until it holds water."),
    R("Saffron Souk", "africa", "Morocco", "saffron", D_EARTH, 8303,
      [("cells", 1.0, dict(cells=148)), ("dunes", 0.6, dict(n=46))],
      desc="Cones of ground spice built by hand and rebuilt every morning after the wind gets at them."),
    R("Tannery Vats", "africa", "Morocco", "tannery", D_EARTH, 8304,
      [("honeycomb", 1.0, dict(cells=118)), ("percolate", 0.6, dict(cells=172))],
      desc="Stone wells of dye and pigeon lime in Fez, worked exactly as they were in the eleventh century."),
    R("Atlas Cedar", "africa", "Morocco", "cedar", D_WOOD, 8305,
      [("bands", 1.0, dict(n=92, shear=1.4, vortex=8, turb=0.34)), ("stars", 0.5, dict(cell=150, points=8, interlace=0.5))],
      desc="Carved cedar ceilings, cut from trees that were old when the city was founded."),
    # ── Mali
    R("Bogolan Mud", "africa", "Mali", "bogolan", D_CLOTH, 8311,
      [("resist", 1.0, dict(cells=142, crackle=1.1)), ("braid", 0.6, dict(layers=100, shear=1.5))],
      desc="Cloth soaked in leaf tannin, then painted with fermented river mud — the iron fixes the black."),
    R("Kente Strip", "africa", "Mali", "kente", D_CLOTH, 8312,
      [("sett", 1.0, dict(pitch=52, stripes=(0.34, 0.06, 0.16, 0.06, 0.28, 0.10), ratio=2.4))],
      desc="Woven in narrow strips on a men's loom, then sewn edge to edge so the pattern steps."),
    R("Indigo Resist", "africa", "Mali", "indigo_w", D_CLOTH, 8313,
      [("resist", 1.0, dict(cells=176, crackle=0.7, bleed=0.6)), ("filaments", 0.55, dict(n=1900, length=16))],
      desc="Tied, stitched and dipped a dozen times. Each dip is darker and the resist never quite holds."),
    R("Brass Casting", "africa", "Mali", "brass_cast", D_METAL, 8314,
      [("craters", 1.0, dict(n=2200, rmax=7.0)), ("cells", 0.6, dict(cells=152))],
      desc="Lost wax: the model is destroyed to make the object, so every casting is the only one."),
    R("Laterite Road", "africa", "Mali", "laterite", D_EARTH, 8315,
      [("dunes", 1.0, dict(n=44)), ("craters", 0.6, dict(n=2800, rmax=5.0))],
      desc="Iron-rich soil that sets like brick in the sun and turns the whole country red in the dry."),
    # ── Egypt
    R("Faience Blue", "africa", "Egypt", "faience", D_GLAZE, 8321,
      [("crack", 1.0, dict(cells=146, width=1.8, gen=1)), ("craters", 0.6, dict(n=2600, rmax=5.0))],
      desc="Not clay at all — ground quartz that brings its own glaze to the surface as it dries."),
    R("Lapis Ground", "africa", "Egypt", "lapis", D_STONE, 8322,
      [("cells", 1.0, dict(cells=126)), ("sparks", 0.6, dict(n=2400, life=18))],
      desc="Lazurite with pyrite through it, carried two thousand miles from Badakhshan to be ground up."),
    R("Alabaster", "africa", "Egypt", "alabaster", D_STONE, 8323,
      [("bands", 1.0, dict(n=78, shear=1.6, vortex=11, turb=0.42)), ("curl", 0.5, dict(scale=60, steps=14))],
      desc="Calcite banded by dripping water, cut thin enough that a lamp inside shows through the wall."),
    R("Papyrus Weave", "africa", "Egypt", "papyrus", D_CLOTH, 8324,
      [("braid", 1.0, dict(layers=92, shear=1.0)), ("filaments", 0.6, dict(n=2100, length=18))],
      desc="Pith sliced, laid at right angles and beaten until its own sap glues it into a sheet."),
    R("Desert Glass", "africa", "Egypt", "desertglass", D_GLAZE, 8325,
      [("spall", 1.0, dict(cells=124, lift=0.62)), ("craters", 0.55, dict(n=2600, rmax=6.0))],
      desc="Libyan silica glass — sand fused by something that came out of the sky 29 million years ago."),
    # ── Ethiopia
    R("Coffee Bed", "africa", "Ethiopia", "coffee", D_EARTH, 8331,
      [("cells", 1.0, dict(cells=138)), ("percolate", 0.6, dict(cells=170))],
      desc="Cherries drying on raised beds, raked by hand every hour so the ferment stays even."),
    R("Basalt Highland", "africa", "Ethiopia", "basalt_hi", D_STONE, 8332,
      [("polygons", 1.0, dict(cells=110, relief=0.7)), ("crack", 0.55, dict(cells=124, gen=1))],
      desc="Flood basalt stacked three kilometres deep, then split open by the rift underneath it."),
    R("Shamma Cotton", "africa", "Ethiopia", "shamma", D_CLOTH, 8333,
      [("braid", 1.0, dict(layers=124, shear=1.1)), ("filaments", 0.6, dict(n=2300, length=14))],
      desc="Handspun gauze worn as a shawl, so fine that the border stripe is the only weight in it."),
    R("Lalibela Stone", "africa", "Ethiopia", "lalibela", D_STONE, 8334,
      [("spall", 1.0, dict(cells=104, lift=0.66)), ("craters", 0.6, dict(n=2400, rmax=6.5))],
      desc="Churches cut DOWN into the rock, roof first, out of one piece of the mountain."),
    R("Danakil Salt", "africa", "Ethiopia", "saltflat", D_STONE, 8335,
      [("polygons", 1.0, dict(cells=126, relief=0.5)), ("craters", 0.5, dict(n=2400, rmax=4.5))],
      desc="Salt pans a hundred metres below the sea, cut into slabs and carried out by camel."),

    # ══════════════════════ 🌎 AMERICAS ═════════════════════════════════════
    # ── Jamaica
    R("Sound System", "americas", "Jamaica", "soundsys", D_WOOD, 8401,
      [("honeycomb", 1.0, dict(cells=124)), ("cells", 0.6, dict(cells=156)),
       ("filaments", 0.4, dict(n=1500, length=18))], dither=0.05,
      desc="Scoops and tweeter boxes stacked to the ceiling, built by the crew that runs them."),
    R("Rasta Weave", "americas", "Jamaica", "rasta", D_CLOTH, 8402,
      [("sett", 1.0, dict(pitch=44, stripes=(0.30, 0.10, 0.26, 0.10, 0.14, 0.10), ratio=3.0))],
      desc="Knitted bands in red, gold and green, worn as a tam and stretched by what is under it."),
    R("Blue Mountain", "americas", "Jamaica", "bluemtn", D_WATER, 8403,
      [("curl", 1.0, dict(scale=44, steps=16)), ("eden", 0.5, dict(seeds=1800, steps=9)),
       ("cells", 0.6, dict(cells=172))],
      desc="Cloud forest above 1500 metres, where the mist is what makes the coffee worth the price."),
    R("Sea Glass", "americas", "Jamaica", "seaglass", D_GLAZE, 8404,
      [("spall", 1.0, dict(cells=134, lift=0.5)), ("craters", 0.6, dict(n=2800, rmax=5.5))],
      desc="Bottle glass rolled by surf until the edges go and the surface frosts right through."),
    R("Allspice Bark", "americas", "Jamaica", "allspice", D_WOOD, 8405,
      [("bands", 1.0, dict(n=88, shear=1.3, vortex=7)), ("percolate", 0.55, dict(cells=168))],
      desc="Pimento — one tree that tastes like four spices, and the wood smokes the jerk pit."),
    # ── Brazil
    R("Carnival Block", "americas", "Brazil", "carnival", D_LACQUER, 8411,
      [("stars", 1.0, dict(cell=116, points=12, interlace=0.7)), ("sparks", 0.6, dict(n=3000, life=24))],
      desc="Sequin, feather and float paint at four in the morning, all of it built to last one night."),
    R("Amazon Canopy", "americas", "Brazil", "amazon", D_EARTH, 8412,
      [("eden", 1.0, dict(seeds=2400, steps=10)),
       ("dendrite", 1.0, dict(seeds=1300)), ("cells", 0.55, dict(cells=168))],
      desc="Closed canopy from above — a single surface made of ten thousand competing crowns."),
    R("Tourmaline", "americas", "Brazil", "tourmaline", D_STONE, 8413,
      [("bands", 1.0, dict(n=82, shear=1.8, vortex=12)), ("cells", 0.55, dict(cells=148))],
      desc="Watermelon crystal: green rind, white ring, pink core, all grown in one go."),
    R("Calçadão", "americas", "Brazil", "calcadao", D_STONE, 8414,
      [("curl", 1.0, dict(scale=48, steps=20)), ("polygons", 0.6, dict(cells=120, relief=0.5))],
      desc="Copacabana's black and white wave, laid stone by stone the length of the beach."),
    R("Cocoa Pod", "americas", "Brazil", "cocoa", D_WOOD, 8415,
      [("bands", 1.0, dict(n=74, shear=2.0, vortex=14)), ("craters", 0.55, dict(n=2400, rmax=6.0))],
      desc="Ridged pods cut from the trunk itself, then fermented in banana leaf for a week."),
    # ── Peru
    R("Alpaca Weave", "americas", "Peru", "alpaca", D_CLOTH, 8421,
      [("braid", 1.0, dict(layers=116, shear=1.4)), ("filaments", 0.65, dict(n=2400, length=14, wander=0.8))],
      desc="Hollow fibre, warmer than wool and no lanolin in it, spun on a drop spindle while walking."),
    R("Andes Strata", "americas", "Peru", "andes", D_STONE, 8422,
      [("bands", 1.0, dict(n=88, shear=2.4, vortex=18, turb=0.5)), ("spall", 0.55, dict(cells=108))],
      desc="Rainbow Mountain: marine sediment, iron and copper folded upright and then stripped bare."),
    R("Cusco Textile", "americas", "Peru", "cusco", D_CLOTH, 8423,
      [("ikat", 1.0, dict(rows=62, motifs=1050, blur=7)), ("sett", 0.5, dict(pitch=54, ratio=1.6))],
      desc="Backstrap loom, warp-faced, so the pattern lives entirely in threads you never see cross."),
    R("Chicha Morada", "americas", "Peru", "chicha", D_WATER, 8424,
      [("curl", 1.0, dict(scale=52, steps=18)), ("percolate", 0.55, dict(cells=176))],
      desc="Purple corn boiled with pineapple rind and clove until the colour is frankly unreasonable."),
    R("Salt Terrace", "americas", "Peru", "salt_ter", D_STONE, 8425,
      [("polygons", 1.0, dict(cells=132, relief=0.45)), ("bands", 0.55, dict(n=80, vortex=10))],
      desc="Maras: three thousand evaporation ponds fed by one warm spring, worked since before the Inca."),
    # ── Cuba
    R("Havana Facade", "americas", "Cuba", "havana", D_LACQUER, 8431,
      [("spall", 1.0, dict(cells=116, lift=0.58)), ("percolate", 0.6, dict(cells=166))],
      desc="Colonial paint sixteen layers deep, each one failing to a different colour underneath."),
    R("Tobacco Leaf", "americas", "Cuba", "tobacco", D_WOOD, 8432,
      [("filaments", 1.0, dict(n=1600, length=42, wander=0.35)), ("cells", 0.6, dict(cells=152))],
      desc="Vuelta Abajo wrapper, cured in a barn for fifty days until the veins go the colour of the leaf."),
    R("Malecón Spray", "americas", "Cuba", "malecon", D_WATER, 8433,
      [("craters", 1.0, dict(n=3000, rmax=6.5)), ("curl", 0.6, dict(scale=58, steps=18))],
      desc="Eight kilometres of sea wall and the Atlantic coming straight over it onto the road."),
    R("Vintage Lacquer", "americas", "Cuba", "vintagelac", D_LACQUER, 8434,
      [("curl", 1.0, dict(scale=46, steps=15)), ("craters", 0.5, dict(n=2200, rmax=5.0))],
      desc="A '55 Bel Air kept alive for seventy years on house paint, marine varnish and stubbornness."),
    R("Sugar Crystal", "americas", "Cuba", "sugar", D_GLAZE, 8435,
      [("polygons", 1.0, dict(cells=140, relief=0.6)), ("sparks", 0.55, dict(n=2800, life=20))],
      desc="Raw crystals off the centrifuge, still warm, still smelling of the cane field."),

    # ══════════════════════ 🌏 OCEANIA ══════════════════════════════════════
    # ── Australia
    R("Ochre Bed", "oceania", "Australia", "ochre", D_EARTH, 8501,
      [("bands", 1.0, dict(n=86, shear=1.6, vortex=10, turb=0.44)), ("cells", 0.6, dict(cells=154))],
      desc="Iron oxide laid down in bands and quarried for forty thousand years as pigment."),
    R("Desert Varnish", "oceania", "Australia", "varnish", D_STONE, 8502,
      [("percolate", 1.0, dict(cells=180, p=0.46)), ("dendrite", 0.6, dict(seeds=1000))],
      desc="Manganese and clay laid on rock by microbes at a micron a millennium, and it shines."),
    R("Opal Seam", "oceania", "Australia", "opal", D_SHELL, 8503,
      [("spall", 1.0, dict(cells=126, lift=0.55)), ("craters", 0.6, dict(n=2600, rmax=6.0))],
      desc="Silica spheres stacked regularly enough to diffract — the fire is structure, not pigment."),
    R("Salt Pan", "oceania", "Australia", "saltpan", D_STONE, 8504,
      [("polygons", 1.0, dict(cells=136, relief=0.42)), ("crack", 0.55, dict(cells=128, gen=1))],
      desc="Lake Eyre dry: a crust that polygonises as it shrinks and floods once a decade."),
    R("Eucalypt Bark", "oceania", "Australia", "eucalypt", D_WOOD, 8505,
      [("bands", 1.0, dict(n=98, shear=1.2, vortex=6)), ("spall", 0.6, dict(cells=118, lift=0.6))],
      desc="Ribbon gum shedding in long strips, leaving fresh green-grey skin underneath."),
    # ── Aotearoa
    R("Greenstone", "oceania", "Aotearoa", "greenstone", D_STONE, 8511,
      [("curl", 1.0, dict(scale=58, steps=20)), ("cells", 0.55, dict(cells=158))],
      desc="Nephrite from the West Coast rivers, tougher than steel and worked only by abrasion."),
    R("Black Sand", "oceania", "Aotearoa", "blacksand", D_EARTH, 8512,
      [("dunes", 1.0, dict(n=48)), ("cells", 0.6, dict(cells=170))],
      desc="Titanomagnetite off the volcanoes, hot enough to burn your feet on a cloudy day."),
    R("Kauri Gum", "oceania", "Aotearoa", "kauri", D_SHELL, 8513,
      [("curl", 1.0, dict(scale=44, steps=22)), ("craters", 0.55, dict(n=2200, rmax=6.5))],
      desc="Resin buried in swamp for thirty thousand years and dug out again with a spear."),
    R("Silver Fern", "oceania", "Aotearoa", "fern", D_CLOTH, 8514,
      [("dendrite", 1.0, dict(seeds=520, walkers=26000, steps=58)),
       ("cells", 0.85, dict(cells=164)), ("filaments", 0.5, dict(n=1800, length=16))],
      desc="Ponga frond, white underneath, laid face-down to mark a track you can follow by moonlight."),
    R("Geothermal", "oceania", "Aotearoa", "geothermal", D_EARTH, 8515,
      [("percolate", 1.0, dict(cells=172, p=0.5)), ("craters", 0.6, dict(n=2800, rmax=7.0))],
      desc="Silica terraces and mud pots at Rotorua, rebuilt daily by water coming up too hot to touch."),
    # ── Indonesia
    R("Batik Wax", "oceania", "Indonesia", "batik", D_CLOTH, 8521,
      [("resist", 1.0, dict(cells=150, crackle=1.2)), ("stars", 0.5, dict(cell=132, points=8, interlace=0.6))],
      desc="Drawn in hot wax with a canting, dyed, boiled off, and drawn again for the next colour."),
    R("Ikat Warp", "oceania", "Indonesia", "ikat_ind", D_CLOTH, 8522,
      [("ikat", 1.0, dict(rows=66, motifs=1150, blur=12)), ("braid", 0.5, dict(layers=104, shear=1.0))],
      desc="The thread is dyed before it is woven, so the design arrives already blurred. That IS the craft."),
    R("Volcanic Sand", "oceania", "Indonesia", "volcanic", D_EARTH, 8523,
      [("dunes", 1.0, dict(n=52)), ("craters", 0.6, dict(n=3000, rmax=5.0))],
      desc="Ash from a caldera that emptied itself, farmed within a decade because nothing grows better."),
    R("Teak Grain", "oceania", "Indonesia", "teak", D_WOOD, 8524,
      [("bands", 1.0, dict(n=100, shear=1.5, vortex=8, turb=0.36)), ("filaments", 0.6, dict(n=1700, length=26, wander=0.2))],
      desc="Oil in the grain itself, which is why a teak deck survives what it survives."),
    R("Spice Heap", "oceania", "Indonesia", "spice", D_EARTH, 8525,
      [("cells", 1.0, dict(cells=144)), ("dunes", 0.6, dict(n=42))],
      desc="Nutmeg and mace from islands the world fought a war over. Two spices, one seed."),
    # ── Philippines
    R("Capiz Shell", "oceania", "Philippines", "capiz", D_SHELL, 8531,
      [("spall", 1.0, dict(cells=120, lift=0.48)), ("polygons", 0.6, dict(cells=124, relief=0.4))],
      desc="Windowpane oyster cut into squares and set in wooden lattice, translucent and cool."),
    R("Abaca Fibre", "oceania", "Philippines", "abaca", D_CLOTH, 8532,
      [("filaments", 1.0, dict(n=2200, length=30, wander=0.4)), ("braid", 0.6, dict(layers=96, shear=1.2))],
      desc="Banana-family fibre strong enough to have rigged the world's ships, woven here into cloth."),
    R("Jeepney Chrome", "oceania", "Philippines", "jeepney", D_METAL, 8533,
      [("stars", 1.0, dict(cell=110, points=10, interlace=0.9)), ("sparks", 0.6, dict(n=2600, life=22))],
      desc="Stainless bodywork, hand-cut trim and more paint than the mechanicals are worth."),
    R("Rice Terrace", "oceania", "Philippines", "terraces", D_WATER, 8534,
      [("bands", 1.0, dict(n=92, shear=2.6, vortex=20, turb=0.5)), ("curl", 0.55, dict(scale=54, steps=16))],
      desc="Two thousand years of contour walls at Banaue, still fed by the same irrigation."),
    R("Mayon Ash", "oceania", "Philippines", "mayon", D_FIRE, 8535,
      [("dunes", 1.0, dict(n=46)), ("percolate", 0.6, dict(cells=174))],
      desc="The most perfect cone on earth, and the ash fall that keeps it that shape."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_") \
        .replace("ç", "c").replace("ã", "a").replace("é", "e").replace("ó", "o")


WORLD = {_fid(r["name"]): r for r in _ROWS}


def title(fid):
    d = WORLD[fid]
    return "%s: %s" % (d["nation"], d["name"])


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
    return WK.pct(acc), lab


_LAB_OWN = {}


@lru_cache(maxsize=8)
def _field(fid):
    """The finish's OWN construction, chosen from what it is (woc_design_2026).

    SPB-105 / owner 2026-09-01: "YOU BUILD THE FINISHES FIRST THEN SPEC TO THE
    FINISHES." The shelf had 66 stack recipes for 100 finishes (spall+craters
    served five crafts on three continents; one `sett` was tartan, madras, kente
    and a rasta tam). The recipe's `stack` is kept for provenance only.
    """
    from engine.expansions import woc_design_2026 as WDS
    from engine.expansions import nightshift_forms_2026 as NF
    from engine.paint_v2 import era_kit_2026 as EK

    d = WORLD[fid]
    form, params, kind = WDS.form_for(fid)
    fn = getattr(EK, form[3:]) if form.startswith("ek:") else getattr(NF, form)
    out = fn((GEN, GEN), d["seed"], **params)
    f, lab = out if isinstance(out, tuple) else (out, None)
    f = np.asarray(f, np.float32)
    f = NF.compose_form(f, d["seed"], kind=kind,
                        amount=float(d.get("detail", WDS.DETAIL.get(WDS.stem(fid), 0.40))),
                        res=GEN)
    # PLACES: busy zones and calm zones, as every gold standard has (see paradigm_2026)
    slow = np.asarray(WK.fbm((GEN, GEN), d["seed"] + 7, octaves=(5, 10, 20),
                             weights=(1.0, 0.6, 0.35)), np.float32)
    slow = (slow - float(slow.min())) / max(float(slow.max() - slow.min()), 1e-6)
    m = float(f.mean())
    f = np.clip(m + (f - m) * (0.50 + 1.0 * slow), 0, 1).astype(np.float32)
    # FINE: a second, smaller construction nested inside the first (intricacy;
    # owner 2026-09-02). Keyed to the macro's edges so it sits on the design.
    fine = WDS.FINE.get(WDS.stem(fid))
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
    _LAB_OWN[fid] = lab is not None
    if lab is None:
        lab = _labels_from_field(f, 166, WK)
    return f, lab


@lru_cache(maxsize=6)
def _art(fid):
    d = WORLD[fid]
    f, lab = _field(fid)
    f = WK.upscale(f, WORK)
    lab = WK.upscale(lab, WORK)
    pal = np.asarray(P[d["palette"]], np.float32)
    # cell means only when the construction drew the cells; over an invented
    # label grid they turn every f-only construction into one 12px mosaic
    # (paradigm_2026, 2026-09-02: bark FOLLOW 0.02 with every lever dead).
    fc = WK.cell_mean(f, lab) if _LAB_OWN.get(fid, True) else f
    t = np.clip(WK.pct(fc) ** float(d.get("gamma", 1.0)), 0, 1)
    idx = np.clip((t * (len(pal) - 1)).astype(np.int32), 0, len(pal) - 2)
    frac = np.clip(t * (len(pal) - 1) - idx, 0, 1)[..., None]
    art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
    from engine.expansions import woc_design_2026 as WDS
    relief = float(d.get("relief", WDS.RELIEF.get(WDS.stem(fid), 0.52)))
    art = art * ((1.0 - relief / 2.0) + relief * f)[..., None]
    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(art, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + (WK._h1(lab, 97) - 0.5) * 13.0, 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.88 + 0.24 * WK._h1(lab, 149)), 0, 1)
        art = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        g = WK.fbm((WORK, WORK), d["seed"] + 3, octaves=(128, 256, 512),
                   weights=(0.6, 1.0, 0.8)) - 0.5
        art = art * (1.0 + g * 0.22)[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


# Per-finish spec composition, MEASURED 2026-09-02 (bands x chips sweep at 1024;
# table in _rebuild/woc_speckw.json) on the woc_design constructions.
_WOC_SPECKW = {
    "woc_aran_cable": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_peat_cut": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_connemara_marble": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_stout_head": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_burren_pavement": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_tartan_sett": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "woc_harris_tweed": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_cairngorm_granite": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_heather_moor": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_cask_char": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_azulejo_blue": {"bands": "linear", "chips": 0.34, "edge_max": 0.07},
    "woc_cork_bark": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_calcada_wave": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "woc_sardine_tin": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "woc_douro_schist": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_rosemaling": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_fjord_water": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_birch_bark": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_arctic_light": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_slate_roof": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_aizome_vat": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_urushi_lacquer": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_raku_crackle": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_kintsugi_seam": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "woc_washi_fibre": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "woc_block_print": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_madras_check": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_marigold_mound": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_mirror_work": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_sandstone_jali": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "woc_iznik_tile": {"bands": "linear", "chips": 0.34, "edge_max": 0.07},
    "woc_kilim_weave": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_meerschaum": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_hammered_copper": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_nazar_glass": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_celadon_glaze": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_bojagi_patch": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "woc_dancheong": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_hanji_sheet": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_najeon_inlay": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "woc_zellij_star": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_tadelakt": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_saffron_souk": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_tannery_vats": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_atlas_cedar": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_bogolan_mud": {"bands": "linear", "chips": 0.34, "edge_max": 0.07},
    "woc_kente_strip": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "woc_indigo_resist": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_brass_casting": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_laterite_road": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_faience_blue": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "woc_lapis_ground": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_alabaster": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_papyrus_weave": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_desert_glass": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_coffee_bed": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_basalt_highland": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "woc_shamma_cotton": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_lalibela_stone": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_danakil_salt": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_sound_system": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_rasta_weave": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_blue_mountain": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_sea_glass": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_allspice_bark": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_carnival_block": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_amazon_canopy": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_tourmaline": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_calcadao": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_cocoa_pod": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_alpaca_weave": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "woc_andes_strata": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_cusco_textile": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_chicha_morada": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "woc_salt_terrace": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "woc_havana_facade": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_tobacco_leaf": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_malecon_spray": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_vintage_lacquer": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_sugar_crystal": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_ochre_bed": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_desert_varnish": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_opal_seam": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_salt_pan": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_eucalypt_bark": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_greenstone": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "woc_black_sand": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_kauri_gum": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "woc_silver_fern": {"bands": "linear", "chips": 0.34, "edge_max": 0.07},
    "woc_geothermal": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_batik_wax": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_ikat_warp": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_volcanic_sand": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "woc_teak_grain": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "woc_spice_heap": {"bands": "quantile", "chips": 0.50, "edge_max": 0.07},
    "woc_capiz_shell": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "woc_abaca_fibre": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "woc_jeepney_chrome": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "woc_rice_terrace": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "woc_mayon_ash": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
}


def _spec_at(fid, res):
    """The finish's own craft, as a material story, laid on its own artwork.

    SPB-105 / owner 2026-09-01. Measured before this: **10 distinct band tuples
    across 100 finishes**, the largest shared by twenty-two — the decks were
    written per continental chapter, so twenty different crafts from four
    countries dealt the same cards.

    Every finish on this shelf IS a specific named craft, which makes the deck a
    matter of reading rather than inventing: urushi is forty coats of lacquer,
    raku is crackled glaze off a red-hot kiln, capiz is windowpane oyster shell.
    woc_decks_2026 authors all hundred. Layout is composed against the RENDERED
    PAINT so material boundaries land on the artwork's own boundaries.
    """
    from engine.paint_v2 import spec_story as ST
    from engine.expansions import woc_decks_2026 as WD

    d = WORLD[fid] if "WORLD" in globals() else _RECIPES[fid]
    entry = WD.CARDS.get(fid)
    f, lab = _field(fid)
    f = WK.upscale(f, res)
    lab = WK.upscale(lab, res) if lab is not None else None
    art = _art(fid)
    if cv2 is not None and art.shape[0] != res:
        art = cv2.resize(np.asarray(art, np.float32), (res, res),
                         interpolation=cv2.INTER_LINEAR)
    cards, edge, kw = entry
    kw = dict(kw)
    kw.update(_WOC_SPECKW.get(fid, {}))
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
    for fid in WORLD:
        entry = _mk(fid)
        for reg in regs:
            try:
                reg[fid] = entry
            except Exception:
                pass
    return "%d finishes from %d places" % (len(WORLD), len({r["nation"] for r in _ROWS}))
