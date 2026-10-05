# -*- coding: utf-8 -*-
"""🎩 FRACTURED HOUDINI — the 2026-09-02 rebuild. Thirty hidden designs.

Owner: "the whole concept was to HIDE designs like SKULLS, GLYPH SIGNALS, UFOs,
GHOSTS, Flames, WHATEVER - hiding features IN the paint that ONLY show up when it
FRACTURES. Cleverly hidden otherwise."

THE MECHANISM (measured with engine/paint_v2/daynight.py before a single card):
a dielectric pixel shows its paint diffusely and its highlight is white; a
chrome-tier metallic pixel shows almost no diffuse and its reflection is tinted
by its own paint. Under a broad soft sky both look the same. Under a lamp or
direct sun the chrome pixel is the brightest thing on the car. So:

    paint  the carrier texture, IDENTICAL inside and outside the design
    spec   the carrier's own matte/satin dielectric quilt, with the design as a
           chrome-tier HALFTONE laid only on the carrier's fine cells — at 1:1
           the spec is still that texture; the shape resolves at car scale

Five pairings were measured on three carriers (engine/expansions/houdini_reveal_2026):
matte dielectric body -> chrome secret at mid-luma paint hides under overcast
(0.01) and reveals under a lamp (0.20). Gloss-vs-matte in one material shows in
daylight; a matte hole in a metal body shows everywhere. This is the one.

WHY THE FIRST TWENTY FAILED (wiki 2026-08-31): secrets fragmented into scattered
marks so nothing was legible; generic dark carriers; proofs with no engine basis;
no number for hidden-vs-revealed. Here: fifteen legible silhouettes, each in two
forms (a few large / a field of small), thirty distinct carriers, and a gate:
hidden <= 0.03 under overcast, reveal >= 0.15 under a lamp
(_rebuild/houdini_gate.py). FOLLOW is deliberately exempt for this shelf — the
spec follows the HIDDEN design, not the paint; that is the finish.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from engine.paint_v2 import era_kit_2026 as EK
from engine.expansions import nightshift_forms_2026 as NF
from engine.expansions import fractured_flames_kit_2026 as FK
from engine.expansions import houdini_reveal_2026 as HR

GROUP = "🎩 FRACTURED HOUDINI"
GEN = 1024
WORK = 1152


# ───────────────────────── more silhouettes ─────────────────────────────────
def _g(h, w, cx, cy, s, rot):
    return HR._grid(h, w, cx, cy, s, rot)


def bat(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    body = (X / 0.16) ** 2 + (Y / 0.30) ** 2 < 1.0
    head = (X / 0.14) ** 2 + ((Y + 0.30) / 0.13) ** 2 < 1.0
    ear_l = (np.abs(X + 0.09) < 0.05 * np.clip(1 - (-Y - 0.36) / 0.16, 0, 1)) & (Y < -0.36) & (Y > -0.52)
    ear_r = (np.abs(X - 0.09) < 0.05 * np.clip(1 - (-Y - 0.36) / 0.16, 0, 1)) & (Y < -0.36) & (Y > -0.52)
    wing = np.zeros_like(X, bool)
    for sgn in (-1.0, 1.0):
        Xw = sgn * X
        upper = (Xw > 0.10) & (Xw < 1.0) & (Y > -0.32 + 0.22 * (Xw - 0.1)) & (Y < 0.34)
        scallop = np.zeros_like(X, bool)
        for k in range(3):
            scx = 0.28 + 0.30 * k
            scallop |= ((Xw - scx) / 0.17) ** 2 + ((Y - 0.42) / 0.20) ** 2 < 1.0
        wing |= upper & ~scallop
    return (body | head | ear_l | ear_r | wing).astype(np.float32)


def spider(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    abdomen = (X / 0.30) ** 2 + ((Y - 0.18) / 0.36) ** 2 < 1.0
    thorax = (X / 0.18) ** 2 + ((Y + 0.24) / 0.18) ** 2 < 1.0
    legs = np.zeros_like(X, bool)
    for sgn in (-1.0, 1.0):
        for k, (a0, a1) in enumerate(((-0.55, -0.9), (-0.25, -0.5), (0.05, 0.05), (0.35, 0.55))):
            x0, y0 = sgn * 0.14, -0.22 + 0.12 * k
            x1, y1 = sgn * 0.62, y0 + a0 * 0.7
            x2, y2 = sgn * 0.98, y1 + a1 * 0.4 + 0.25
            for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2)):
                dx, dy = bx - ax, by - ay
                t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy + 1e-6), 0, 1)
                legs |= np.hypot(X - (ax + t * dx), Y - (ay + t * dy)) < 0.045
    return (abdomen | thorax | legs).astype(np.float32)


def crescent(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    outer = X ** 2 + Y ** 2 < 0.9 ** 2
    inner = (X - 0.32) ** 2 + (Y - 0.10) ** 2 < 0.78 ** 2
    return (outer & ~inner).astype(np.float32)


def bolt(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    seg1 = (Y > -1.0) & (Y < -0.2) & (np.abs(X - (0.10 + 0.55 * (Y + 1.0) / 0.8)) < 0.18)
    seg2 = (Y > -0.30) & (Y < 0.30) & (np.abs(X - (0.60 - 0.85 * (Y + 0.30) / 0.6)) < 0.20)
    seg3 = (Y > 0.20) & (Y < 1.0) & (np.abs(X - (-0.20 + 0.55 * (Y - 0.2) / 0.8)) < 0.16 * np.clip(1.2 - (Y - 0.2), 0.2, 1))
    return (seg1 | seg2 | seg3).astype(np.float32)


def dagger(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    blade = (Y > -1.0) & (Y < 0.30) & (np.abs(X) < 0.16 * np.clip((Y + 1.0) / 0.5, 0, 1))
    guard = (np.abs(X) < 0.48) & (Y > 0.28) & (Y < 0.40)
    grip = (np.abs(X) < 0.09) & (Y > 0.40) & (Y < 0.82)
    pommel = X ** 2 + (Y - 0.88) ** 2 < 0.11 ** 2
    return (blade | guard | grip | pommel).astype(np.float32)


def crown(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    band = (np.abs(X) < 0.80) & (Y > 0.25) & (Y < 0.55)
    points = np.zeros_like(X, bool)
    for px in (-0.64, -0.32, 0.0, 0.32, 0.64):
        hgt = 0.65 if px == 0.0 else 0.50
        points |= (Y < 0.25) & (Y > 0.25 - hgt) & (np.abs(X - px) < 0.14 * np.clip((Y - (0.25 - hgt)) / hgt, 0, 1))
        points |= (X - px) ** 2 + (Y - (0.25 - hgt)) ** 2 < 0.06 ** 2
    return (band | points).astype(np.float32)


def key(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    ring = (X ** 2 + (Y + 0.55) ** 2 < 0.34 ** 2) & ~(X ** 2 + (Y + 0.55) ** 2 < 0.17 ** 2)
    shaft = (np.abs(X) < 0.08) & (Y > -0.25) & (Y < 0.85)
    tooth1 = (X > 0.08) & (X < 0.36) & (Y > 0.55) & (Y < 0.66)
    tooth2 = (X > 0.08) & (X < 0.28) & (Y > 0.75) & (Y < 0.85)
    return (ring | shaft | tooth1 | tooth2).astype(np.float32)


def hourglass(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    top = (Y > -0.80) & (Y < 0.0) & (np.abs(X) < 0.55 * np.clip((-Y) / 0.8, 0.06, 1))
    bot = (Y < 0.80) & (Y > 0.0) & (np.abs(X) < 0.55 * np.clip((Y) / 0.8, 0.06, 1))
    frame = (np.abs(X) < 0.62) & ((np.abs(Y + 0.86) < 0.06) | (np.abs(Y - 0.86) < 0.06))
    posts = (np.abs(np.abs(X) - 0.60) < 0.04) & (np.abs(Y) < 0.86)
    sand = (Y < 0.80) & (Y > 0.45) & (np.abs(X) < 0.55 * np.clip((Y) / 0.8, 0.06, 1))
    return ((top | bot | frame | posts) & ~(bot & ~sand & (Y > 0.12))).astype(np.float32)


def serpent(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    path = 0.35 * np.sin(Y * 4.2)
    body = (np.abs(X - path) < 0.13 * np.clip(1.0 - np.abs(Y) / 1.05, 0.15, 1)) & (np.abs(Y) < 1.0)
    head = ((X - 0.35 * np.sin(-1.0 * 4.2)) / 0.22) ** 2 + ((Y + 1.02) / 0.16) ** 2 < 1.0
    return (body | head).astype(np.float32)


HR.SHAPES.update({"bat": bat, "spider": spider, "crescent": crescent, "bolt": bolt, "dagger": dagger,
                  "crown": crown, "key": key, "hourglass": hourglass, "serpent": serpent})

# bolder saucer than the proof: thicker hull, no beam rays
def ufo2(h, w, cx, cy, s, rot=0.0):
    X, Y = _g(h, w, cx, cy, s, rot)
    saucer = (X / 1.0) ** 2 + (Y / 0.30) ** 2 < 1.0
    dome = ((X / 0.46) ** 2 + ((Y + 0.20) / 0.40) ** 2 < 1.0) & (Y < 0.0)
    ports = np.zeros_like(X, bool)
    for px in (-0.62, -0.31, 0.0, 0.31, 0.62):
        ports |= ((X - px) / 0.08) ** 2 + ((Y - 0.08) / 0.07) ** 2 < 1.0
    return ((saucer & ~ports) | dome).astype(np.float32)


HR.SHAPES["ufo"] = ufo2


# ───────────────────────── the thirty ────────────────────────────────────────
# id: (name, design, layout, carrier form, params, palette (4 stops, mid-luma), body cards, desc)
# layout: "few" = sparse (14 small silhouettes); "field" = dense (36 smaller) — sizes in _field
MATTE = ((0, 214, 214), (0, 196, 200), (0, 176, 184))          # dead, chalk, eggshell — dielectric, dark under a lamp
MATTE2 = ((0, 222, 222), (0, 206, 210), (0, 190, 198))          # a second matte family (satin bodies measured NOT hidden: 0.04-0.12 overcast)
SECRET = (255, 8, 70)                                          # chrome-tier smooth: the flash
SECRET_VEIL = (252, 30, 120)                                   # a softer chrome for the field forms

# fraction of carrier cells lit inside the design (default 0.45; thin silhouettes 0.35).
# Lower on the carriers that leaked under overcast in the first gate.
CELL_FRAC = {"hou_cold_flame": 0.46, "hou_belfry": 0.46, "hou_widows_web": 0.48, "hou_lunar_tide": 0.52,
             "hou_haunting": 0.62, "hou_sands": 0.62, "hou_ossuary": 0.72, "hou_locksmith": 0.74, "hou_nightwing": 0.62,
             "hou_usurper": 0.55, "hou_sigil": 0.54, "hou_serpentine": 0.58, "hou_nest": 0.50}   # each measured: too high leaks under overcast, too low is a weak reveal

HOUDINI = {
    "hou_veiled_skull":    ("Veiled Skull", "skull", "few", "ek:crinkle", dict(scale=130, sharp=2.6, folds=2),
                            ((0.12, 0.10, 0.16), (0.22, 0.19, 0.28), (0.34, 0.30, 0.42), (0.50, 0.44, 0.58)), MATTE,
                            "Plum lacquer with a fine crease. Nothing in it until a light crosses the panel, and then there is."),
    "hou_ossuary":         ("Ossuary", "skull", "field", "ek:worley", dict(cells=150),
                            ((0.20, 0.19, 0.17), (0.32, 0.30, 0.27), (0.44, 0.42, 0.38), (0.58, 0.55, 0.50)), MATTE,
                            "Bone-grey cells. Under the pit lamps every cell that was ever a skull remembers it."),
    "hou_phantom_choir":   ("Phantom Choir", "ghost", "few", "damascus", dict(layers=120, folds=3, twist=2.0, warp=0.3),
                            ((0.13, 0.10, 0.19), (0.24, 0.18, 0.32), (0.36, 0.28, 0.46), (0.52, 0.42, 0.62)), MATTE,
                            "Lilac folds with nobody in them. Headlights fill the seats."),
    "hou_haunting":        ("Haunting", "ghost", "field", "ek:threads", dict(),
                            ((0.16, 0.19, 0.18), (0.26, 0.30, 0.29), (0.38, 0.42, 0.40), (0.52, 0.56, 0.54)), MATTE2,
                            "Mist-green fibre, and a dozen small shapes in it that only the sun can see."),
    "hou_close_encounter": ("Close Encounter", "ufo", "few", "ek:kh_braid", dict(layers=26, shear=3.0),
                            ((0.08, 0.12, 0.22), (0.14, 0.22, 0.36), (0.22, 0.34, 0.50), (0.34, 0.48, 0.64)), MATTE,
                            "Night-blue turbulence. Three saucers, lights on, that the daytime denies."),
    "hou_saucer_swarm":    ("Saucer Swarm", "ufo", "field", "ek:percolate", dict(cells=90, p=0.5),
                            ((0.08, 0.20, 0.22), (0.14, 0.32, 0.34), (0.22, 0.44, 0.46), (0.34, 0.58, 0.60)), MATTE,
                            "Teal clusters. A whole fleet in formation, visible from the grandstand at dusk."),
    "hou_cold_flame":      ("Cold Flame", "flame", "few", "ek:curl", dict(scale=120, steps=26),
                            ((0.16, 0.08, 0.06), (0.30, 0.14, 0.08), (0.46, 0.22, 0.10), (0.64, 0.34, 0.14)), MATTE,
                            "Ember-brown swirl that is not on fire. Under a lamp it is."),
    "hou_wildfire":        ("Wildfire", "flame", "field", "ridge_flow", dict(ridges=120, cores=4),
                            ((0.18, 0.06, 0.06), (0.34, 0.12, 0.08), (0.52, 0.20, 0.10), (0.70, 0.32, 0.14)), MATTE2,
                            "Red ridge lines. The fire is everywhere, and only the light knows."),
    "hou_rune_wall":       ("Rune Wall", "glyph", "field", "ek:knurl", dict(pitch=14.0, angle=0.785, wobble=0.3),
                            ((0.10, 0.12, 0.10), (0.20, 0.24, 0.20), (0.32, 0.38, 0.32), (0.48, 0.54, 0.46)), MATTE,
                            "Moss-green weave. The wall was written on before it was painted."),
    "hou_sigil":           ("Sigil", "glyph", "few", "ek:bricks", dict(rows=26, cols=6, bind=0.14),
                            ((0.14, 0.15, 0.18), (0.24, 0.26, 0.30), (0.36, 0.38, 0.44), (0.50, 0.52, 0.58)), MATTE2,
                            "Slate courses, and four large marks laid into them that a torch reads."),
    "hou_watchers":        ("Watchers", "eye", "few", "ek:scales", dict(cell=22.0, keel=0.4),
                            ((0.16, 0.10, 0.12), (0.30, 0.18, 0.22), (0.44, 0.28, 0.34), (0.60, 0.42, 0.50)), MATTE,
                            "Wine scales. In the shade you are alone. In the light you are not."),
    "hou_thousand_eyes":   ("Thousand Eyes", "eye", "field", "ek:honeycomb", dict(),
                            ((0.22, 0.16, 0.08), (0.36, 0.27, 0.12), (0.50, 0.38, 0.16), (0.66, 0.52, 0.22)), MATTE2,
                            "Amber cells, and every cell has an eye it only opens for the sun."),
    "hou_belfry":          ("Belfry", "bat", "field", "ek:wrinkle", dict(k=1.8, steps=14),   # 22 steps measured 3.3s
                            ((0.12, 0.10, 0.16), (0.20, 0.17, 0.26), (0.30, 0.26, 0.38), (0.42, 0.37, 0.52)), MATTE,
                            "Charcoal-violet folds. The bats are up there; wait for the lights."),
    "hou_nightwing":       ("Nightwing", "bat", "few", "ek:intaglio", dict(),   # moire cells turned the bats into blocks on the sheet; a fine engraved tone keeps the wings
                            ((0.08, 0.10, 0.20), (0.14, 0.18, 0.32), (0.22, 0.28, 0.46), (0.32, 0.40, 0.60)), MATTE,
                            "Ink-blue interference. Three wingspans across the door, when the sun says so."),
    "hou_widows_web":      ("Widow's Web", "spider", "few", "ek:polygons", dict(cells=40, width=2.0),   # anneal_crack 5.6s; polygons 60 3.9s
                            ((0.14, 0.08, 0.09), (0.26, 0.14, 0.15), (0.38, 0.20, 0.22), (0.52, 0.28, 0.30)), MATTE,
                            "Black-red crazing. What is sitting in it shows under a lamp."),
    "hou_brood":           ("Brood", "spider", "field", "ek:craters", dict(n=900, rmin=2.5, rmax=7.0, rim=0.6),   # 3000 4.4s, 1600 3.7s
                            ((0.16, 0.12, 0.09), (0.28, 0.22, 0.16), (0.40, 0.32, 0.24), (0.54, 0.44, 0.34)), MATTE2,
                            "Brown pitted ground. A dozen small spiders, lit."),
    "hou_moonshadow":      ("Moonshadow", "crescent", "few", "ek:dunes", dict(n=28, crest=1.8),
                            ((0.10, 0.10, 0.22), (0.18, 0.18, 0.36), (0.28, 0.28, 0.50), (0.40, 0.40, 0.64)), MATTE,
                            "Indigo drifts. Three moons come up when the lights do."),
    "hou_lunar_tide":      ("Lunar Tide", "crescent", "field", "caustics", dict(scale=9.0, octaves=3),
                            ((0.12, 0.14, 0.18), (0.20, 0.23, 0.28), (0.30, 0.34, 0.40), (0.42, 0.47, 0.53)), MATTE2,
                            "Silver-blue water light, and a sky full of crescents behind it."),
    "hou_storm_sigil":     ("Storm Sigil", "bolt", "few", "ek:facets", dict(stones=260, table=0.4),
                            ((0.14, 0.16, 0.20), (0.24, 0.27, 0.32), (0.36, 0.40, 0.46), (0.50, 0.54, 0.60)), MATTE,
                            "Steel facets. The bolts are in the metal; a headlight sets them off."),
    "hou_static_field":    ("Static Field", "bolt", "field", "ek:fbm", dict(octaves=(96, 192, 384, 768)),
                            ((0.12, 0.13, 0.16), (0.22, 0.24, 0.28), (0.34, 0.36, 0.42), (0.48, 0.50, 0.56)), MATTE2,
                            "Storm-grey grain with lightning all through it, waiting for a lamp."),
    "hou_assassins_hand":  ("Assassin's Hand", "dagger", "few", "ek:spall", dict(cells=50, lift=0.7),
                            ((0.12, 0.13, 0.15), (0.22, 0.23, 0.26), (0.34, 0.36, 0.40), (0.48, 0.50, 0.54)), MATTE,
                            "Gunmetal plates. Four blades, drawn only in the light."),
    "hou_armory":          ("Armory", "dagger", "field", "ek:bands", dict(n=60, shear=0.1, turb=0.1),
                            ((0.14, 0.16, 0.20), (0.24, 0.27, 0.32), (0.36, 0.40, 0.46), (0.50, 0.54, 0.60)), MATTE2,
                            "Cold steel bands and a rack of small knives that the sun inventories."),
    "hou_usurper":         ("Usurper", "crown", "few", "ek:guilloche", dict(),
                            ((0.20, 0.14, 0.06), (0.34, 0.24, 0.10), (0.48, 0.36, 0.16), (0.64, 0.50, 0.24)), MATTE,
                            "Gold-brown engraving. Somebody's crowns are in it, and the lights crown them."),
    "hou_court":           ("Court", "crown", "field", "ek:sett", dict(pitch=22.0, twill=2.0),
                            ((0.16, 0.10, 0.22), (0.28, 0.18, 0.36), (0.40, 0.28, 0.50), (0.54, 0.40, 0.64)), MATTE2,
                            "Royal purple twill, a court of small crowns held for the sun."),
    "hou_skeleton_key":    ("Skeleton Key", "key", "few", "ek:topo", dict(lines=110.0, width=2.4),
                            ((0.20, 0.16, 0.08), (0.34, 0.28, 0.14), (0.48, 0.40, 0.20), (0.62, 0.54, 0.28)), MATTE,
                            "Brass contours. The keys are cut into the map; a torch finds the locks."),
    "hou_locksmith":       ("Locksmith", "key", "field", "imbricate", dict(rows=48, overlap=0.5),
                            ((0.10, 0.20, 0.18), (0.18, 0.32, 0.30), (0.28, 0.44, 0.42), (0.40, 0.58, 0.56)), MATTE2,
                            "Verdigris scales with a ring of keys hidden in them."),
    "hou_borrowed_time":   ("Borrowed Time", "hourglass", "few", "ek:shag", dict(strands=8000, length=24, splay=1.2),
                            ((0.22, 0.18, 0.12), (0.36, 0.30, 0.20), (0.50, 0.42, 0.30), (0.64, 0.56, 0.42)), MATTE,
                            "Sand-coloured nap. The hourglasses are running; you only see them under a lamp."),
    "hou_sands":           ("Sands", "hourglass", "field", "ek:discs", dict(n=2600, radius=11.0),
                            ((0.24, 0.18, 0.08), (0.38, 0.30, 0.14), (0.52, 0.42, 0.20), (0.66, 0.56, 0.28)), MATTE2,
                            "Ochre discs, and a field of small hourglasses that the sun turns over."),
    "hou_serpentine":      ("Serpentine", "serpent", "few", "gray_scott", dict(feed=0.030, kill=0.062),
                            ((0.08, 0.16, 0.10), (0.14, 0.28, 0.18), (0.22, 0.40, 0.26), (0.34, 0.54, 0.36)), MATTE,
                            "Green cells. Three snakes in the grass, lit from the pit wall."),
    "hou_nest":            ("Nest", "serpent", "field", "ek:filaments", dict(n=300, length=200, width=2.0, wander=0.15),
                            ((0.14, 0.16, 0.08), (0.26, 0.28, 0.14), (0.38, 0.40, 0.20), (0.52, 0.54, 0.28)), MATTE2,
                            "Olive fibre, and the nest underneath it that daylight refuses to show."),
}


def check():
    forms = [v[3] for v in HOUDINI.values()]
    if len(set(forms)) != len(forms):
        raise ValueError("HOUDINI reuses carriers: %s" % sorted({f for f in forms if forms.count(f) > 1}))
    designs = {}
    for fid, v in HOUDINI.items():
        designs.setdefault((v[1], v[2]), []).append(fid)
    dup = {k: v for k, v in designs.items() if len(v) > 1}
    if dup:
        raise ValueError("HOUDINI repeats a design+layout: %s" % dup)
    return len(HOUDINI)


def _seed(fid):
    import zlib
    return zlib.crc32(fid.encode()) % 100000


@lru_cache(maxsize=8)
def _field(fid):
    """Carrier field at GEN, plus the design mask at GEN."""
    name, design, layout, form, params, pal, body, desc = HOUDINI[fid]
    seed = _seed(fid)
    fn = getattr(EK, form[3:]) if form.startswith("ek:") else getattr(NF, form)
    out = fn((GEN, GEN), seed, **params)
    f = np.asarray(out[0] if isinstance(out, tuple) else out, np.float32)
    f = NF.compose_form(f, seed, kind="grain", amount=0.40, res=GEN)
    f = (f - float(f.min())) / max(float(f.max() - f.min()), 1e-6)
    # Owner 2026-09-02: the first cut placed 4 silhouettes at 17-30% of the canvas (350-600 px
    # on the car: MASSIVE) all upright (the UV islands point every way). Now: many small ones,
    # every instance at its own full-circle rotation + mirror (HR.field full_rot), masks at GEN.
    #   "few"   = sparse : 14 at 6-11%  of the canvas (120-225 px on the 2048 car)
    #   "field" = dense  : 36 at 3.5-6.5%             (70-130 px on the car)
    if layout == "few":
        count, size = 14, (0.06, 0.11)
    else:
        count, size = 36, (0.035, 0.065)
    mask = HR.field((GEN, GEN), seed + 7, design, count=count, size=size)
    return f, mask


@lru_cache(maxsize=6)
def _art(fid):
    name, design, layout, form, params, pal, body, desc = HOUDINI[fid]
    f, _mask = _field(fid)
    f = FK.upscale(f, WORK)
    pal = np.asarray(pal, np.float32)
    t = np.clip(f, 0, 1) * (len(pal) - 1)
    idx = np.clip(t.astype(np.int32), 0, len(pal) - 2)
    fr = (t - idx)[..., None]
    art = pal[idx] * (1.0 - fr) + pal[idx + 1] * fr
    art = art * (0.85 + 0.30 * f)[..., None]
    if cv2 is not None:
        g, _k = NF.detail(f, _seed(fid) + 3, kind="grain", amount=1.0, res=WORK)
        art = art * (1.0 + (g - 0.5) * 2.0 * 0.16)[..., None]
    # THE PAINT NEVER CARRIES THE DESIGN. That is the whole point.
    return np.clip(art, 0, 1).astype(np.float32)


def _spec_at(fid, res):
    name, design, layout, form, params, pal, body, desc = HOUDINI[fid]
    f0, mask0 = _field(fid)
    q1, q2 = np.quantile(f0[::4, ::4], [0.36, 0.72])   # at GEN: np.quantile on 4M pixels cost ~1.5s per render
    f = cv2.resize(f0, (res, res), interpolation=cv2.INTER_LINEAR) if cv2 is not None else FK.upscale(f0, res)
    mask = cv2.resize(mask0, (res, res), interpolation=cv2.INTER_LINEAR) if cv2 is not None else FK.upscale(mask0, res)
    # body: three dielectric cards by carrier quantile, so the map is a quilt, not a wash
    spec = np.empty((res, res, 3), np.float32)
    spec[...] = np.asarray(body[0], np.float32)
    spec[f > q1] = np.asarray(body[1], np.float32)
    spec[f > q2] = np.asarray(body[2], np.float32)
    # the secret: chrome-tier on the carrier's own fine cells inside the silhouette
    secret = np.asarray(SECRET, np.float32)          # the veil card measured half the reveal; full chrome everywhere
    # thin silhouettes (wings, shafts, strokes) need more of their cells lit to read
    thin = design in ("bat", "key", "serpent", "crown", "bolt", "dagger", "glyph", "spider", "hourglass", "ufo")
    # adaptive: a fixed 0.40 lit 8% of some carriers and 70% of others (WEAK REVEAL on
    # threads/discs/imbricate, leaks under overcast on caustics/wrinkle). Light a set
    # FRACTION of the carrier's cells: more for thin silhouettes, fewer where the
    # carrier leaks under a soft sky.
    frac = CELL_FRAC.get(fid, 0.72 if thin else 0.62)   # 0.45 lit too few cells: reveal fell to ~0.12 across the shelf
    thr = float(np.quantile(f0[::4, ::4], 1.0 - frac))
    cells = f > thr
    on = (mask > 0.5) & cells
    spec[on] = secret
    rim = (mask > 0.15) & (mask <= 0.5) & cells
    spec[rim] = 0.5 * spec[rim] + 0.5 * secret
    return np.clip(spec, 0, 255)


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
        if cv2 is not None and art.shape[:2] != (fh, fw):
            art = cv2.resize(art, (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        s = _spec_at(fid, fw)
        if s.shape[0] != fh and cv2 is not None:
            s = cv2.resize(s, (fw, fh), interpolation=cv2.INTER_NEAREST)
        return s

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    n = 0
    for fid in HOUDINI:
        mono_reg[fid] = _mk(fid)
        n += 1
    return "%d FRACTURED HOUDINI finishes installed" % n
