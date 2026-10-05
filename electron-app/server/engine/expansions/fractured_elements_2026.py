# -*- coding: utf-8 -*-
"""🌊 FRACTURED ELEMENTS — the 2026-08-31 rebuild. 60 finishes, all weather.

Owner: *"FRACTURED ELEMENTS (weather - water, rain, sleet, snow, ice, tornadoes,
hurricanes, tsunamis, sandstorms - anything but fire since we already have fire
in it's own category). We have a category under SHOKKER called ATMOSPHERE which
you could take some of the ideas in there and bring them to FRACTURED ELEMENTS
and ditch the ATMOSPHERE category there altogether."*

WHAT WAS THERE. Three shelves stapled together by the 2026-08-01 merge:

  * **20 deep-sea creatures** — Anglerfish, Cephalopod, Kraken Ink, Glass Squid,
    Siphonophore, Whale Fall. Marine biology, not weather.
  * **20 storm cards that are a COLOUR GRID** — Slate Billows / Slate Hailfield
    / Slate Squall / Slate Vortex, then the same structures again in steel,
    violet and green.
  * **20 ice cards, also a colour grid** — Cyan Fissure / Cyan Frond / Cyan
    Frostbloom / Cyan Veil, then violet, silver and white.

So two thirds of it was a recolour matrix and a third was the wrong subject.

THE REBUILD: five chapters of twelve, one per kind of weather, absorbing the
good ideas from SHOKKER ▸ ATMOSPHERE (which is retired) — Acid Rain, Black Ice,
Blizzard, Dust Storm, Fog Bank, Hail Damage, Monsoon, Permafrost, Tornado Alley
all reappear here as authored finishes rather than as a separate shelf.

  🌧 RAIN     falling and landed water
  ❄ FROZEN   every way water goes solid
  🌀 STORM    rotation and violence in the air
  🌊 WATER    water with a surface — surf, flood, swell
  🏜 DRY      when the air carries dust instead

Fire is deliberately absent: it has its own category.
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

ID_PREFIX = "elm_"
GROUP = "🌊 FRACTURED ELEMENTS"
GEN = 1024
WORK = 1152
_TAU = 6.283185307179586

CHAPTERS = {"rain": "🌧 RAIN", "frozen": "❄ FROZEN", "storm": "🌀 STORM",
            "water": "🌊 WATER", "dry": "🏜 DRY"}


# ════════════════════════════════════════════════════════════════════════════
# WEATHER-SPECIFIC PRIMITIVES (everything else is imported)
# ════════════════════════════════════════════════════════════════════════════


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

def raindrops(shape, seed, n=1100, rmax=12.0, ripples=3, streak=0.0, sharp=0.055):
    """Impact rings on a wet surface. Each drop is a short train of expanding
    ripples, and the rings OCCLUDE rather than sum — overlapping rain rings that
    add just average into a smooth wash."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = CK.rng(seed)
    for _ in range(int(n)):
        cx, cy = r.random() * w, r.random() * h
        R = rmax * (0.30 + 0.85 * r.random())
        rad = int(R + 3)
        x0, x1 = int(max(0, cx - rad)), int(min(w, cx + rad))
        y0, y1 = int(max(0, cy - rad)), int(min(h, cy + rad))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(lx - cx, ly - cy) / R
        rip = np.zeros_like(d)
        for k in range(int(ripples)):
            rip = np.maximum(rip, np.exp(-((d - (0.35 + 0.30 * k)) / float(sharp)) ** 2) * (0.75 ** k))
        np.maximum(out[y0:y1, x0:x1], rip, out=out[y0:y1, x0:x1])
    if streak > 0 and cv2 is not None:
        st = CK.filaments(shape, seed + 7, n=int(420 * streak), length=44, wander=0.05, width=0.9)
        out = np.maximum(out, st * float(streak))
    return CK.pct(out)


def snowflakes(shape, seed, n=850, size=12.0, arms=6, branch=3):
    """Six-fold dendritic crystals. Not dots: a snowflake's whole identity is
    that it branches, and at 8-32px on a car the branching is what you see."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    if cv2 is None:
        return out
    r = CK.rng(seed)
    for _ in range(int(n)):
        cx, cy = r.random() * w, r.random() * h
        S = size * (0.45 + 0.9 * r.random())
        rot = r.random() * _TAU
        for a in range(int(arms)):
            th = rot + a * _TAU / arms
            x1, y1 = cx + np.cos(th) * S, cy + np.sin(th) * S
            cv2.line(out, (int(cx) % w, int(cy) % h), (int(x1) % w, int(y1) % h), 0.9, 1)
            for b in range(1, int(branch) + 1):
                t = b / (branch + 1.0)
                bx, by = cx + np.cos(th) * S * t, cy + np.sin(th) * S * t
                bl = S * 0.34 * (1.0 - t)
                for sgn in (-1, 1):
                    ph = th + sgn * 1.05
                    cv2.line(out, (int(bx) % w, int(by) % h),
                             (int(bx + np.cos(ph) * bl) % w, int(by + np.sin(ph) * bl) % h), 0.7, 1)
    return CK.pct(cv2.GaussianBlur(out, (0, 0), 0.7))


def funnels(shape, seed, n=110, twist=3.0, taper=2.2):
    """Rotating columns — tornado, waterspout, dust devil. Many small ones, so
    the car carries a field of rotation rather than one poster funnel."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = CK.rng(seed)
    for _ in range(int(n)):
        cx, cy = r.random() * w, r.random() * h
        R = (0.018 + 0.032 * r.random()) * min(h, w)
        rad = int(R * 1.8 + 3)
        x0, x1 = int(max(0, cx - rad)), int(min(w, cx + rad))
        y0, y1 = int(max(0, cy - rad)), int(min(h, cy + rad))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = lx - cx, ly - cy
        d = np.hypot(dx, dy) / R
        a = np.arctan2(dy, dx)
        spiral = 0.5 + 0.5 * np.sin(a * 2.0 + d * float(twist) * _TAU)
        env = np.clip(1.0 - d ** float(taper), 0, 1)
        np.maximum(out[y0:y1, x0:x1], spiral * env, out=out[y0:y1, x0:x1])
    return CK.pct(out)


def crests(shape, seed, n=74, foam=0.55, steep=2.4):
    """Breaking wave crests: a train of rollers with foam thrown off the lip."""
    h, w = shape[0], shape[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ph = CK.fbm((h, w), seed, octaves=(8, 16, 32, 64), weights=(1.0, 0.8, 0.55, 0.3))
    u = yy / float(h) * float(n) + ph * 1.6
    s = u - np.floor(u)
    roll = np.clip(1.0 - np.abs(s * 2.0 - 0.75) ** float(steep), 0, 1)
    fine = CK.fbm((h, w), seed + 5, octaves=(128, 256, 512), weights=(0.6, 1.0, 0.75))
    lip = np.clip((roll - 0.72) * 6.0, 0, 1)
    return CK.pct(roll * 0.7 + fine * 0.4 + lip * fine * float(foam) * 2.2)


def veil(shape, seed, layers=5, drift=0.5, grain=0.55):
    """Suspended particulate — fog, dust haze, spindrift. Stacked translucent
    sheets, each drifting slightly differently, which is what gives haze depth
    instead of being a flat wash."""
    h, w = shape[0], shape[1]
    acc = np.zeros((h, w), np.float32)
    # The octave stack has to REACH the car band: a haze built only from
    # octaves 12-96 is a smooth gradient with no 8-32px content at all, which
    # is what a fog bank looks like from a mile away and not from a metre.
    for i in range(int(layers)):
        f = CK.fbm((h, w), seed + i * 211,
                   octaves=(48 + i * 32, 128 + i * 64, 256 + i * 96, 512),
                   weights=(0.6, 1.0, 0.9, 0.6))
        acc += f * (0.82 ** i)
    fine = CK.fbm((h, w), seed + 77, octaves=(128, 256, 512), weights=(0.55, 1.0, 0.8))
    return CK.pct(acc * (1.0 - grain) + fine * grain + CK.pct(acc) * float(drift) * 0.3)


_STRUCTS = {
    "drops":     lambda sh, sd, k: (raindrops(sh, sd, **k), None),
    "flakes":    lambda sh, sd, k: (snowflakes(sh, sd, **k), None),
    "funnel":    lambda sh, sd, k: (funnels(sh, sd, **k), None),
    "crest":     lambda sh, sd, k: (crests(sh, sd, **k), None),
    "veil":      lambda sh, sd, k: (veil(sh, sd, **k), None),
    "streak":    lambda sh, sd, k: (CK.filaments(sh, sd, **k), None),
    "cells":     lambda sh, sd, k: CK.worley(sh, sd, **k),
    "curl":      lambda sh, sd, k: (CK.curl(sh, sd, **k), None),
    "dendrite":  lambda sh, sd, k: (CK.dla(sh, sd, **k), None),
    "percolate": lambda sh, sd, k: CK.percolate(sh, sd, **k),
    "crack":     lambda sh, sd, k: CK.anneal_crack(sh, sd, **k),
    "polygons":  lambda sh, sd, k: CK.polygons(sh, sd, **k),
    "braid":     lambda sh, sd, k: (CK.kh_braid(sh, sd, **k), None),
    "fingers":   lambda sh, sd, k: (CK.rt_fingers(sh, sd, **k), None),
    "sparks":    lambda sh, sd, k: (CK.sparks(sh, sd, **k), None),
    "craters":   lambda sh, sd, k: (CK.craters(sh, sd, **k), None),
    "dunes":     lambda sh, sd, k: (CK.dunes(sh, sd, **k), None),
    "spall":     lambda sh, sd, k: CK.spall(sh, sd, **k),
    "wrinkle":   lambda sh, sd, k: (CK.wrinkle(sh, sd, **k), None),
    "rings":     lambda sh, sd, k: (CK.rings(sh, sd, **k), None),
}

# What weather DOES to a surface, per chapter.
CHAPTER_SPEC = {
    # wet: the wettest states in the deck, with a dry matte ground to contrast
    "rain":   dict(bands=(("matte", 0.24), ("semi_gloss", 0.46), ("gloss", 0.66),
                          ("wet", 0.84), ("liquid_glaze", 0.94), ("chrome", 1.01)),
                   edge="chrome", edge_max=0.06, r_spread=28.0),
    # frozen: milk glass, rime and hard clear ice over a dead ground
    "frozen": dict(bands=(("ceramic_matte", 0.26), ("milk_glass", 0.48),
                          ("frozen_metal", 0.66), ("sea_glass", 0.82),
                          ("liquid_glaze", 0.93), ("mercury", 1.01)),
                   edge="satin_chrome", edge_max=0.05, r_spread=30.0),
    # storm: dark, charged, with the carrier where the lightning is
    "storm":  dict(bands=(("void", 0.26), ("flat_black", 0.46), ("satin_carbon", 0.64),
                          ("gunmetal", 0.80), ("carrier_mid", 0.93), ("chrome", 1.01)),
                   edge="chrome", edge_max=0.07, r_spread=22.0, cc_offset=5),
    # water with a surface: glass, foam and the metal of a wave face
    "water":  dict(bands=(("gloss_carbon", 0.24), ("sea_glass", 0.46),
                          ("gloss", 0.64), ("wet", 0.80), ("milk_glass", 0.92),
                          ("mercury", 1.01)),
                   edge="chrome", edge_max=0.06, r_spread=26.0),
    # dry: everything matte and mineral, with the odd mica glint
    "dry":    dict(bands=(("void", 0.26), ("ceramic_matte", 0.48), ("powder", 0.66),
                          ("bead_blast", 0.82), ("patina", 0.93), ("satin_chrome", 1.01)),
                   edge="dark_chrome", edge_max=0.05, r_spread=36.0),
}

P = {
    "storm_slate": ((0.09, 0.10, 0.12), (0.24, 0.27, 0.31), (0.44, 0.48, 0.54), (0.68, 0.72, 0.78)),
    "rain_night":  ((0.05, 0.07, 0.10), (0.14, 0.20, 0.28), (0.30, 0.40, 0.52), (0.60, 0.72, 0.84)),
    "acid":        ((0.06, 0.09, 0.05), (0.22, 0.34, 0.14), (0.46, 0.64, 0.24), (0.76, 0.90, 0.52)),
    "petrichor":   ((0.08, 0.07, 0.06), (0.26, 0.22, 0.18), (0.46, 0.42, 0.36), (0.72, 0.70, 0.64)),
    "snow":        ((0.30, 0.34, 0.40), (0.60, 0.66, 0.74), (0.82, 0.87, 0.93), (0.97, 0.99, 1.00)),
    "ice_blue":    ((0.10, 0.18, 0.24), (0.30, 0.50, 0.62), (0.58, 0.78, 0.88), (0.88, 0.96, 1.00)),
    "black_ice":   ((0.04, 0.05, 0.07), (0.12, 0.16, 0.22), (0.28, 0.36, 0.46), (0.62, 0.72, 0.82)),
    "rime":        ((0.22, 0.26, 0.28), (0.50, 0.56, 0.60), (0.76, 0.82, 0.86), (0.95, 0.98, 1.00)),
    "supercell":   ((0.06, 0.06, 0.08), (0.20, 0.20, 0.26), (0.42, 0.40, 0.34), (0.72, 0.66, 0.46)),
    "hail_green":  ((0.06, 0.09, 0.08), (0.18, 0.30, 0.26), (0.38, 0.56, 0.46), (0.70, 0.84, 0.72)),
    "bolt":        ((0.04, 0.04, 0.08), (0.16, 0.16, 0.34), (0.44, 0.46, 0.78), (0.88, 0.90, 1.00)),
    "surf":        ((0.05, 0.14, 0.16), (0.10, 0.36, 0.40), (0.32, 0.64, 0.68), (0.82, 0.94, 0.96)),
    "deep_swell":  ((0.03, 0.08, 0.12), (0.08, 0.22, 0.34), (0.20, 0.44, 0.60), (0.62, 0.82, 0.92)),
    "flood":       ((0.08, 0.08, 0.06), (0.24, 0.22, 0.16), (0.44, 0.40, 0.28), (0.70, 0.66, 0.52)),
    "sand":        ((0.14, 0.11, 0.07), (0.42, 0.33, 0.20), (0.68, 0.56, 0.36), (0.90, 0.82, 0.62)),
    "haboob":      ((0.12, 0.08, 0.05), (0.38, 0.24, 0.12), (0.66, 0.46, 0.24), (0.90, 0.74, 0.48)),
    "salt_haze":   ((0.22, 0.22, 0.24), (0.52, 0.52, 0.54), (0.76, 0.76, 0.77), (0.95, 0.95, 0.96)),
    "drought":     ((0.12, 0.10, 0.08), (0.34, 0.29, 0.22), (0.56, 0.49, 0.38), (0.80, 0.74, 0.62)),
    "fog":         ((0.20, 0.22, 0.24), (0.44, 0.48, 0.52), (0.68, 0.72, 0.76), (0.90, 0.93, 0.95)),
}


def R(name, chapter, palette, seed, stack, mix="sum", tiers=8, gamma=1.0,
      spec=None, desc=""):
    return dict(name=name, chapter=chapter, palette=palette, seed=seed,
                stack=stack, mix=mix, tiers=tiers, gamma=gamma,
                spec=spec or {}, desc=desc)


_ROWS = [
    # ───────────────────────────── 🌧 RAIN (12) ─────────────────────────────
    R("Downpour", "rain", "rain_night", 4101,
      [("streak", 1.0, dict(n=560, length=52, wander=0.04, width=0.9)),
       ("drops", 0.8, dict(n=900))],
      desc="Rain hard enough to be a surface of its own, and the road answering it."),
    R("Cloudburst", "rain", "rain_night", 4102,
      [("drops", 0.75, dict(n=1500, rmax=10.0, ripples=4)), ("cells", 0.7, dict(cells=150)),
       ("cells", 1.7, dict(cells=178))],
      desc="Every drop lands at once — a whole sheet of overlapping impact rings."),
    R("Drizzle", "rain", "fog", 4103,
      [("veil", 1.0, dict(layers=5)), ("drops", 0.8, dict(n=1800, rmax=5.0, ripples=2))],
      desc="Too fine to hear, wet enough to soak you. Rain you only see against a light."),
    R("Sheet Rain", "rain", "storm_slate", 4104,
      [("streak", 1.0, dict(n=700, length=64, wander=0.02, width=0.8)),
       ("cells", 0.7, dict(cells=160))],
      desc="Wind-driven and near-horizontal, arriving in visible sheets across the tarmac."),
    R("Monsoon", "rain", "acid", 4105,
      [("streak", 1.0, dict(n=520, length=58, wander=0.08)), ("veil", 0.75, dict(layers=4))],
      desc="A season, not a shower — warm rain with the whole sky committed to it."),
    R("Acid Rain", "rain", "acid", 4106,
      [("drops", 1.0, dict(n=1100, rmax=9.0)), ("spall", 0.75, dict(cells=100))],
      desc="Rain that leaves a mark: etched pits where each drop sat and worked."),
    R("Puddle Skin", "rain", "petrichor", 4107,
      [("drops", 0.75, dict(n=800, rmax=15.0, ripples=4)), ("curl", 0.7, dict(scale=64)),
       ("cells", 1.7, dict(cells=172))],
      desc="Standing water with the wind fretting it and oil-film drifting on top."),
    R("Dew Field", "rain", "fog", 4108,
      [("cells", 1.0, dict(cells=175)), ("drops", 0.7, dict(n=2000, rmax=5.0, ripples=1))],
      desc="Condensation beaded on cold paint, each bead its own tiny lens."),
    R("Petrichor", "rain", "petrichor", 4109,
      [("veil", 1.0, dict(layers=4, grain=0.7)), ("percolate", 0.75, dict(cells=155))],
      desc="Dry ground taking the first rain — dark patches spreading and joining."),
    R("Gutter Race", "rain", "rain_night", 4110,
      [("curl", 1.0, dict(scale=44, steps=18)), ("drops", 0.75, dict(n=900, rmax=8.0))],
      desc="Water finding the low line and running it faster than anything else on the road."),
    R("Windscreen", "rain", "black_ice", 4111,
      [("drops", 0.75, dict(n=1300, rmax=11.0, ripples=3, streak=0.6)),
       ("cells", 0.7, dict(cells=165)),
       ("cells", 1.5, dict(cells=180))],
      desc="Beads shearing sideways and joining into rivulets the moment you move."),
    R("Virga", "rain", "fog", 4112,
      [("veil", 1.0, dict(layers=6, drift=0.7)), ("streak", 0.8, dict(n=380, length=48))],
      desc="Rain that never lands — it evaporates on the way down and hangs there instead."),

    # ──────────────────────────── ❄ FROZEN (12) ────────────────────────────
    R("Blizzard", "frozen", "snow", 4201,
      [("flakes", 0.75, dict(n=700)), ("veil", 0.8, dict(layers=5, drift=0.8)),
       ("cells", 1.4, dict(cells=176))],
      desc="Snow moving sideways fast enough that the ground and the sky stop being different."),
    R("Snowdrift", "frozen", "snow", 4202,
      [("dunes", 1.0, dict(n=36)), ("flakes", 0.75, dict(n=520, size=9.0))],
      desc="Wind sculpting snow the same way it sculpts sand, and just as sharply."),
    R("Sleet", "frozen", "ice_blue", 4203,
      [("drops", 0.75, dict(n=1400, rmax=7.0, ripples=2)), ("flakes", 0.75, dict(n=420)),
       ("cells", 1.4, dict(cells=174))],
      desc="Half rain, half ice, and unpleasant in a way neither of them manages alone."),
    R("Hail Damage", "frozen", "rime", 4204,
      [("craters", 1.0, dict(n=1600, rmax=9.0, rim=0.8)), ("crack", 0.7, dict(cells=104))],
      desc="Dents you can feel through the paint, each one a stone that fell out of a cloud."),
    R("Hoarfrost", "frozen", "rime", 4205,
      [("dendrite", 1.0, dict(seeds=900, walkers=18000)), ("flakes", 0.75, dict(n=480))],
      desc="Water going straight from vapour to crystal, feathering out on every cold edge."),
    R("Rime Ice", "frozen", "rime", 4206,
      [("dendrite", 1.0, dict(seeds=1300)), ("dunes", 0.7, dict(n=30))],
      desc="Freezing fog building into the wind, so the ice grows toward the weather."),
    R("Black Ice", "frozen", "black_ice", 4207,
      [("crack", 1.0, dict(cells=120, width=1.4)), ("curl", 0.7, dict(scale=60))],
      desc="Invisible until it is far too late — clear ice over dark tarmac."),
    R("Frost Fern", "frozen", "ice_blue", 4208,
      [("dendrite", 1.0, dict(seeds=600, walkers=22000, steps=54)), ("cells", 0.7, dict(cells=160))],
      desc="Window frost: ferns that grow along scratches you never knew the glass had."),
    R("Diamond Dust", "frozen", "snow", 4209,
      [("sparks", 1.0, dict(n=2800, life=20, width=0.7)), ("veil", 0.7, dict(layers=4))],
      desc="Ice crystals falling out of a clear sky, each one catching the sun on its way."),
    R("Permafrost", "frozen", "ice_blue", 4210,
      [("polygons", 1.0, dict(cells=70)), ("crack", 0.7, dict(cells=112, width=1.6))],
      desc="Ground that has not thawed in ten thousand years, cracked into contraction polygons."),
    R("Serac Field", "frozen", "ice_blue", 4211,
      [("spall", 1.0, dict(cells=84, lift=0.68)), ("crack", 0.75, dict(cells=100))],
      desc="A glacier breaking over a step: blocks the size of houses, none of them stable."),
    R("Graupel", "frozen", "snow", 4212,
      [("cells", 1.0, dict(cells=140)), ("flakes", 0.75, dict(n=560, size=8.0))],
      desc="Soft hail — snowflakes that fell through supercooled cloud and came out rimed."),

    # ───────────────────────────── 🌀 STORM (12) ────────────────────────────
    R("Tornado Alley", "storm", "supercell", 4301,
      [("funnel", 0.75, dict(n=34)), ("curl", 0.8, dict(scale=40, steps=20)),
       ("cells", 1.7, dict(cells=170))],
      desc="Rotation you can see. The field turns before the funnel ever touches down."),
    R("Supercell", "storm", "supercell", 4302,
      [("curl", 1.0, dict(scale=34, steps=24)), ("fingers", 0.8, dict(n=120))],
      desc="One storm with its own rotating updraught, which is why it lasts all afternoon."),
    R("Hurricane Eye", "storm", "storm_slate", 4303,
      [("funnel", 1.0, dict(n=22, twist=3.0, taper=1.6)), ("crest", 0.8, dict(n=34))],
      desc="Bands wrapped tight enough to leave a hole in the middle where it is completely calm."),
    R("Squall Line", "storm", "storm_slate", 4304,
      [("braid", 1.0, dict(layers=96, shear=4.2)), ("streak", 0.8, dict(n=520, length=50))],
      desc="A wall of weather a hundred miles long arriving all at once."),
    R("Gust Front", "storm", "haboob", 4305,
      [("fingers", 1.0, dict(n=130, gain=1.7)), ("veil", 0.8, dict(layers=4))],
      desc="The cold air a storm pushes ahead of itself, rolling and picking up everything loose."),
    R("Mammatus", "storm", "supercell", 4306,
      [("cells", 1.0, dict(cells=88)), ("fingers", 0.8, dict(n=110, gain=1.5))],
      desc="Pouches hanging under the anvil — sinking air, and a sky that looks upside down."),
    R("Wall Cloud", "storm", "supercell", 4307,
      [("curl", 0.75, dict(scale=38, steps=22)), ("funnel", 0.75, dict(n=18)),
       ("cells", 1.6, dict(cells=172))],
      desc="The lowered base under the updraught. If anything is going to happen, it happens here."),
    R("Lightning Strike", "storm", "bolt", 4308,
      [("dendrite", 1.0, dict(seeds=420, walkers=24000, steps=56)), ("sparks", 0.8, dict(n=2400))],
      mix="max", desc="One channel out of a thousand attempts, and it lasts about thirty microseconds."),
    R("Thunderhead", "storm", "storm_slate", 4309,
      [("fingers", 1.0, dict(n=120)), ("veil", 0.8, dict(layers=5))],
      desc="Twelve kilometres of vertical development, flattened at the top where it hit the stratosphere."),
    R("Microburst", "storm", "hail_green", 4310,
      [("funnel", 0.75, dict(n=30, twist=2.0, taper=3.0)), ("crest", 0.75, dict(n=30)),
       ("cells", 1.7, dict(cells=176))],
      desc="Air falling out of a cloud fast enough to spread sideways when it lands."),
    R("Waterspout", "storm", "surf", 4311,
      [("funnel", 0.75, dict(n=28, twist=6.0)), ("crest", 0.8, dict(n=32)),
       ("cells", 1.6, dict(cells=174))],
      desc="A tornado that found the sea and started lifting it."),
    R("Derecho", "storm", "storm_slate", 4312,
      [("braid", 1.0, dict(layers=96, shear=5.0)), ("fingers", 0.75, dict(n=120))],
      desc="Straight-line wind that keeps going for six hundred miles without rotating once."),

    # ───────────────────────────── 🌊 WATER (12) ────────────────────────────
    R("Tsunami", "water", "deep_swell", 4401,
      [("crest", 0.75, dict(n=22, steep=3.0)), ("curl", 0.8, dict(scale=44, steps=20)),
       ("cells", 1.7, dict(cells=168))],
      desc="Not a wave — a change in sea level that happens to be moving at jet speed."),
    R("Breaker", "water", "surf", 4402,
      [("crest", 1.0, dict(n=32, foam=0.8)), ("percolate", 0.8, dict(cells=150))],
      desc="The moment the wave face outruns its own base and the top has nowhere to go."),
    R("Whitewater", "water", "surf", 4403,
      [("percolate", 1.0, dict(cells=170, p=0.48)), ("crest", 0.8, dict(n=38))],
      desc="Air beaten into water until it stops being either one."),
    R("Tide Race", "water", "deep_swell", 4404,
      [("curl", 1.0, dict(scale=36, steps=24)), ("braid", 0.8, dict(layers=96, shear=3.6))],
      desc="A whole ocean forced through a gap, and the seams where the flows shear past each other."),
    R("Storm Surge", "water", "flood", 4405,
      [("crest", 0.75, dict(n=26)), ("veil", 0.8, dict(layers=4, grain=0.65)),
       ("cells", 1.7, dict(cells=172))],
      desc="The sea arriving somewhere it does not belong, pushed by a low-pressure centre."),
    R("Riptide", "water", "surf", 4406,
      [("curl", 1.0, dict(scale=32, steps=26)), ("crest", 0.75, dict(n=36))],
      desc="A narrow river running out through the surf, and the reason you swim sideways."),
    R("Spindrift", "water", "salt_haze", 4407,
      [("veil", 1.0, dict(layers=5, drift=0.75)), ("streak", 0.8, dict(n=480, length=46))],
      desc="Spray torn off the wave tops and carried until it is more air than water."),
    R("Whirlpool", "water", "deep_swell", 4408,
      [("funnel", 0.75, dict(n=30, twist=7.0)), ("curl", 0.8, dict(scale=40, steps=20)),
       ("cells", 1.8, dict(cells=176))],
      desc="Two tides meeting on a shelf and neither of them giving way."),
    R("Chop", "water", "surf", 4409,
      [("crest", 1.0, dict(n=48, steep=1.8)), ("cells", 0.75, dict(cells=155))],
      desc="Short, steep, confused water — the wind arguing with the swell underneath it."),
    R("Glassy Swell", "water", "deep_swell", 4410,
      [("curl", 0.75, dict(scale=52, steps=16)), ("crest", 0.7, dict(n=18, steep=1.4)),
       ("cells", 1.7, dict(cells=170))],
      desc="Long-period energy from a storm a thousand miles away, arriving in perfect order."),
    R("Flood Line", "water", "flood", 4411,
      [("dunes", 1.0, dict(n=32, crest=1.6)), ("percolate", 0.8, dict(cells=160))],
      desc="Silt and debris marking exactly how high it got, all the way along."),
    R("Foam Lace", "water", "salt_haze", 4412,
      [("percolate", 1.0, dict(cells=180, p=0.42)), ("cells", 0.8, dict(cells=150))],
      desc="What is left on the sand after the wave goes back — a lace of bubbles, briefly."),

    # ────────────────────────────── 🏜 DRY (12) ─────────────────────────────
    R("Sandstorm", "dry", "sand", 4501,
      [("veil", 1.0, dict(layers=5, drift=0.8)), ("streak", 0.8, dict(n=520, length=54, wander=0.06))],
      desc="Visibility measured in metres, and the sound of your own paint being taken off."),
    R("Haboob", "dry", "haboob", 4502,
      [("fingers", 1.0, dict(n=120, gain=1.8)), ("veil", 0.85, dict(layers=5))],
      desc="A wall of dust a mile high rolling ahead of a collapsing thunderstorm."),
    R("Dust Devil", "dry", "sand", 4503,
      [("funnel", 0.75, dict(n=34, twist=6.5)), ("dunes", 0.75, dict(n=34)),
       ("cells", 1.6, dict(cells=178))],
      desc="Ground heated until the air above it has to leave, spinning as it goes."),
    R("Heat Shimmer", "dry", "salt_haze", 4504,
      [("curl", 1.0, dict(scale=48, steps=18)), ("veil", 0.8, dict(layers=4, grain=0.7))],
      desc="Air of two different densities in the same place, and the road bending because of it."),
    R("Drought Crack", "dry", "drought", 4505,
      [("polygons", 1.0, dict(cells=72, width=2.4)), ("crack", 0.8, dict(cells=110))],
      desc="Clay that has given up all its water and shrunk away from itself."),
    R("Mirage", "dry", "salt_haze", 4506,
      [("braid", 1.0, dict(layers=96, shear=2.2)), ("veil", 0.8, dict(layers=5))],
      desc="An inverted image of the sky lying on the road, and it stays exactly as far away."),
    R("Dust Veil", "dry", "haboob", 4507,
      [("veil", 1.0, dict(layers=6, drift=0.6)), ("cells", 0.75, dict(cells=165))],
      desc="Fine enough to stay up for weeks and to make the sunsets worth watching."),
    R("Salt Haze", "dry", "salt_haze", 4508,
      [("polygons", 1.0, dict(cells=80, relief=0.6)), ("veil", 0.8, dict(layers=4))],
      desc="A dry lake giving its crust back to the wind one flake at a time."),
    R("Harmattan", "dry", "sand", 4509,
      [("dunes", 1.0, dict(n=42, drift=0.55)), ("veil", 0.8, dict(layers=5))],
      desc="A trade wind carrying the Sahara west until it reaches the sea and beyond."),
    R("Sirocco", "dry", "haboob", 4510,
      [("curl", 1.0, dict(scale=38, steps=22)), ("dunes", 0.8, dict(n=38))],
      desc="Desert air pulled north across the Mediterranean, arriving hot and full of grit."),
    R("Loess", "dry", "drought", 4511,
      [("dunes", 1.0, dict(n=30, crest=1.8)), ("percolate", 0.75, dict(cells=160))],
      desc="Windblown silt laid down in beds deep enough to farm and soft enough to carve."),
    R("Brownout", "dry", "haboob", 4512,
      [("veil", 1.0, dict(layers=6, drift=0.9, grain=0.65)), ("funnel", 0.75, dict(n=26))],
      desc="Rotor wash lifting the whole surface at once, and the ground disappearing from under you."),
]


def _fid(name):
    return ID_PREFIX + name.lower().replace(" ", "_").replace("-", "_")


ELEMENTS = {_fid(r["name"]): r for r in _ROWS}


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


_LAB_OWN = {}


@lru_cache(maxsize=8)
def _field(fid):
    """The finish's OWN construction (elements_construction_2026), chosen from the
    weather it is. SPB-105 / owner 2026-09-01: finishes first, spec to the finishes.
    The recipe's `stack` stays for provenance only."""
    from engine.expansions import elements_construction_2026 as EC
    from engine.expansions import nightshift_forms_2026 as NF
    from engine.paint_v2 import era_kit_2026 as EK

    d = ELEMENTS[fid]
    form, params, kind = EC.form_for(fid)
    fn = getattr(EK, form[3:]) if form.startswith("ek:") else getattr(NF, form)
    out = fn((GEN, GEN), d["seed"], **params)
    f, lab = out if isinstance(out, tuple) else (out, None)
    f = np.asarray(f, np.float32)
    f = NF.compose_form(f, d["seed"], kind=kind,
                        amount=float(d.get("detail", EC.DETAIL.get(EC.stem(fid), 0.40))), res=GEN)
    slow = np.asarray(CK.fbm((GEN, GEN), d["seed"] + 7, octaves=(5, 10, 20),
                             weights=(1.0, 0.6, 0.35)), np.float32)
    slow = (slow - float(slow.min())) / max(float(slow.max() - slow.min()), 1e-6)
    mm = float(f.mean())
    f = np.clip(mm + (f - mm) * (0.50 + 1.0 * slow), 0, 1).astype(np.float32)
    fine = EC.FINE.get(EC.stem(fid))
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
        lab = _labels_from_field(f, 170, CK)
    return f, lab


@lru_cache(maxsize=6)
def _art(fid):
    d = ELEMENTS[fid]
    f, lab = _field(fid)
    f = CK.upscale(f, WORK)
    lab = CK.upscale(lab, WORK)
    pal = np.asarray(P[d["palette"]], np.float32)
    # cell means only when the construction drew the cells (the 12px-mosaic bug)
    fc = CK.cell_mean(f, lab) if _LAB_OWN.get(fid, True) else f
    t = np.clip(CK.pct(fc) ** float(d.get("gamma", 1.0)), 0, 1)
    idx = np.clip((t * (len(pal) - 1)).astype(np.int32), 0, len(pal) - 2)
    frac = np.clip(t * (len(pal) - 1) - idx, 0, 1)[..., None]
    art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
    from engine.expansions import elements_construction_2026 as _EC
    relief = float(d.get("relief", _EC.RELIEF.get(_EC.stem(fid), 0.56)))
    art = art * ((1.0 - relief / 2.0) + relief * f)[..., None]
    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(art, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + (CK._h1(lab, 97) - 0.5) * 20.0, 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.86 + 0.28 * CK._h1(lab, 149)), 0, 1)
        art = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        # KEYED fine detail, not an independent grain layer.
        #
        # This used to be a plain fbm sprayed at constant amplitude over the
        # whole canvas. That is what made the paint's band-limited detail
        # envelope FLAT, and a flat envelope is one no spec can follow: measured
        # elm_monsoon FOLLOW 0.052 with a perfectly reasonable spec, because
        # there was nothing in the paint for the spec to correlate with. The
        # detail now rides the finish's own field, so it concentrates where the
        # artwork has structure — which is both physically right and what makes
        # the FOLLOW axis reachable at all.
        from engine.expansions import nightshift_forms_2026 as NF
        gk, _key = NF.detail(fc, d["seed"] + 3, kind=d.get("grain", "grain"),
                             amount=1.0, res=WORK)
        art = art * (1.0 + (gk - 0.5) * 2.0 * float(d.get("gamt", 0.30)))[..., None]
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    """The finish's own hand-authored material story, laid on its own artwork.

    SPB-105 / owner 2026-08-31: *"the damn finishes and spec maps for MANY of
    them are repeats, totally the same just slightly recolored. The specs are
    EXACTLY the same."*

    He was right and the cause was structural: this function used to read
    CHAPTER_SPEC, so all twelve rain finishes shared one band list, all twelve
    frozen ones another, and so on — five decks for sixty finishes, with zero
    per-finish overrides. Measured story_ratio 0.30 and 60/60 law failures.

    Now each finish names its own deck in elements_design_2026 (chosen from its
    own description — standing water gets liquid glaze and mercury, a dry lake
    crust gets ceramic and bead-blast, hail damage gets dented galvanised metal)
    and the layout comes from spec_story.compose against the RENDERED PAINT, so
    the material boundaries sit on the artwork's own tonal boundaries instead of
    being dealt over an unrelated noise field. That second part is what the
    owner meant by "follow the pattern of the base paint and MAKE SENSE".
    """
    from engine.paint_v2 import spec_story as ST
    from engine.expansions import elements_design_2026 as ED

    d = ELEMENTS[fid]
    deck, edge, kw = ED.DECKS[fid]
    kw = dict(kw)
    kw.update(_ELM_SPECKW.get(fid, {}))   # richness-first sweep (_rebuild/rich_sweep.py elements)
    f, lab = _field(fid)
    f = CK.upscale(f, res)
    lab = CK.upscale(lab, res) if lab is not None else None
    art = _art(fid)
    if art.shape[0] != res and cv2 is not None:
        art = cv2.resize(np.asarray(art, np.float32), (res, res),
                         interpolation=cv2.INTER_LINEAR)
    return ST.compose(f, deck, seed=d["seed"], res=res, lab=lab,
                      edge=edge, art=art, **kw)


# Per-finish spec composition (baked by _rebuild/rich_sweep.py elements)
_ELM_SPECKW = {
    "elm_downpour": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_cloudburst": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_drizzle": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_sheet_rain": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "elm_monsoon": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "elm_acid_rain": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "elm_puddle_skin": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_dew_field": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_petrichor": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "elm_gutter_race": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_windscreen": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_virga": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_blizzard": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "elm_snowdrift": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "elm_sleet": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "elm_hail_damage": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "elm_hoarfrost": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "elm_rime_ice": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_black_ice": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "elm_frost_fern": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "elm_diamond_dust": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_permafrost": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_serac_field": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_graupel": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "elm_tornado_alley": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_supercell": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_hurricane_eye": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_squall_line": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "elm_gust_front": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "elm_mammatus": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_wall_cloud": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "elm_lightning_strike": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_thunderhead": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "elm_microburst": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_waterspout": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_derecho": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "elm_tsunami": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_breaker": {"bands": "quantile", "chips": 0.00, "edge_max": 0.07},
    "elm_whitewater": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_tide_race": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "elm_storm_surge": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_riptide": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_spindrift": {"bands": "linear", "chips": 0.34, "edge_max": 0.14},
    "elm_whirlpool": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "elm_chop": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "elm_glassy_swell": {"bands": "quantile", "chips": 0.00, "edge_max": 0.14},
    "elm_flood_line": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "elm_foam_lace": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "elm_sandstorm": {"bands": "quantile", "chips": 0.34, "edge_max": 0.14},
    "elm_haboob": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "elm_dust_devil": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_heat_shimmer": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_drought_crack": {"bands": "linear", "chips": 0.50, "edge_max": 0.07},
    "elm_mirage": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_dust_veil": {"bands": "quantile", "chips": 0.34, "edge_max": 0.07},
    "elm_salt_haze": {"bands": "linear", "chips": 0.00, "edge_max": 0.14},
    "elm_harmattan": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
    "elm_sirocco": {"bands": "linear", "chips": 0.50, "edge_max": 0.14},
    "elm_loess": {"bands": "quantile", "chips": 0.50, "edge_max": 0.14},
    "elm_brownout": {"bands": "linear", "chips": 0.00, "edge_max": 0.07},
}


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
    for fid in ELEMENTS:
        entry = _mk(fid)
        for reg in regs:
            try:
                reg[fid] = entry
            except Exception:
                pass
    return "%d weather finishes across %d chapters" % (len(ELEMENTS), len(CHAPTERS))
