"""Fine-scale identity + color-flip kernel for FRACTURED WILDS.

SPB-WILDS, tick 2 (2026-08-23).  Owner verdict: "Too much redundancy way too
similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping
stuff."  Baseline across BLOOM+PETRI: nearest-neighbour appearance similarity
median/max 70.55/79.17, angle-flip proxy median/min 10.56/7.05, and weakest
M/R/Cc tier occupancy 7/6/4.  This kernel replaces the shared broad-domain look
with six independently tiered mark families whose complete primitive boxes are
8-32 px at 2048.  Final movement is recorded beside each category install.

The kernel is intentionally category-local.  It does not change the shared
``fractured_catlib_2026`` contract used by the other FRACTURED collections.
"""

from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib


# SPB-WILDS, tick 3 (2026-08-23). Owner verdict: "WAY more spec
# coloring/shades of colors in the spec maps."  All three channels retain eight
# materially occupied, independent shades and broad 150-170 point spans, while
# avoiding a physically incoherent all-channel full-scale swing: the accepted
# fine paint reads at catalog busy-rank ~0.46-0.54, whereas the former
# 238/220/226 spans put every spec channel at a combined 0.843 lively-rank.
# Final audited M5/M7 movement is recorded beside the category installs.
_M_LEVELS = np.asarray([18, 42, 66, 90, 114, 138, 162, 188], np.float32)
_R_LEVELS = np.asarray([24, 44, 64, 84, 104, 126, 150, 174], np.float32)
_C_LEVELS = np.asarray([18, 42, 66, 90, 114, 140, 164, 188], np.float32)

_OPPONENT_OFFSETS = (
    (0.50, 0.33, 0.67), (0.42, 0.58, 0.17), (0.61, 0.28, 0.78),
    (0.47, 0.21, 0.72), (0.55, 0.36, 0.83), (0.39, 0.64, 0.14),
    (0.52, 0.25, 0.75), (0.44, 0.69, 0.19), (0.57, 0.31, 0.81),
    (0.49, 0.16, 0.66), (0.63, 0.38, 0.88), (0.41, 0.56, 0.06),
    (0.54, 0.29, 0.71), (0.46, 0.62, 0.12), (0.59, 0.34, 0.84),
    (0.51, 0.23, 0.73), (0.43, 0.67, 0.17), (0.56, 0.37, 0.87),
    (0.48, 0.18, 0.68), (0.62, 0.27, 0.77),
)

# Recipe-order topology maps.  BLOOM prioritises whorls/vines/pollen/flowers;
# PETRI prioritises membranes/cells/diatoms/chains.  Each is a permutation, so
# no category member gets the same silhouette as a sibling.
_BLOOM_TOPOLOGY = (3, 16, 13, 11, 2, 10, 18, 19, 6, 7,
                   5, 14, 17, 9, 1, 15, 12, 8, 4, 0)
_PETRI_TOPOLOGY = (11, 8, 2, 1, 13, 7, 10, 6, 18, 4,
                   14, 5, 12, 15, 9, 19, 0, 16, 17, 3)

# Owner-eye scale gate for the equal-density role router.  A visible continuous
# lead/counter zone counts as a feature even though it contains only micro
# glyphs.  These per-topology multipliers bring native-2048 p95 zone thickness
# from 38.4px median / 79.3px max to <=32px without shrinking any glyph box.
# Only failing families are accelerated; already-fine target/diamond/halo
# families retain their readable local organization (SPB-WILDS 2026-08-23).
_TOPOLOGY_FINE_MULTIPLIER = (
    2.20, 1.00, 1.45, 1.00, 2.40, 1.55, 2.40, 1.00, 1.75, 1.30,
    1.45, 1.40, 1.75, 1.00, 1.30, 2.20, 1.30, 1.50, 1.00, 2.50,
)

# Explicit semantic identity ledger, recipe order == ``wild_variant``.  Each
# row selects six different bounded glyphs from `_semantic_glyph_bank` plus a
# topology compositor.  This is deliberately 40 named mechanisms rather than
# 40 rotations of one dot/ring kernel (owner-eye rejection, 2026-08-23).
# Glyph indices: disc, ring, crescent, arc, spoke, star, slash, capsule,
# needle, curl, chevron, cross, fork, leaf, petal, quadpetal, comb,
# ribbed-pill, beadchain, trellis, cell-wall, crack, dust, pore.
_SEMANTIC_RECIPES = (
    # BLOOM — 20 botanical mechanisms.
    ("rosette",       (15, 14, 1, 3, 4, 9), 0),
    ("trellis",       (19, 13, 18, 12, 3, 22), 1),
    ("echinate",      (5, 4, 0, 23, 8, 22), 2),
    ("lamina",        (14, 16, 13, 3, 8, 22), 3),
    ("foam",          (20, 1, 23, 0, 2, 22), 4),
    ("platemosaic",   (20, 15, 19, 0, 21, 22), 5),
    ("threaddrift",   (9, 6, 7, 18, 3, 22), 6),
    ("billow",        (9, 2, 3, 14, 0, 22), 7),
    ("needlefelt",    (8, 11, 22, 7, 12, 0), 1),
    ("rdlab",         (15, 20, 9, 1, 23, 22), 4),
    ("stemmesh",      (12, 7, 19, 13, 18, 22), 2),
    ("starlat",       (5, 11, 4, 18, 0, 22), 0),
    ("petalcells",    (15, 20, 14, 0, 1, 3), 5),
    ("pleat",         (10, 16, 6, 19, 18, 22), 3),
    ("dustclump",     (22, 0, 23, 1, 18, 2), 6),
    ("fringe",        (16, 8, 6, 7, 3, 22), 7),
    ("imbric",        (2, 17, 15, 14, 1, 22), 2),
    ("beadcurtain",   (18, 7, 19, 8, 22, 0), 1),
    ("pinwheel",      (4, 9, 3, 5, 0, 22), 0),
    ("porate",        (23, 1, 0, 20, 21, 22), 4),
    # PETRI — 20 microbial/culture mechanisms.
    ("droplets",      (0, 1, 23, 2, 3, 22), 6),
    ("ripples",       (1, 3, 2, 9, 0, 22), 3),
    ("streaks",       (6, 9, 7, 8, 18, 22), 7),
    ("crackle",       (21, 20, 11, 12, 23, 22), 5),
    ("dendrite",      (12, 13, 8, 5, 18, 22), 1),
    ("pills",         (17, 7, 8, 23, 18, 22), 2),
    ("stainplates",   (20, 15, 23, 0, 21, 22), 5),
    ("spineball",     (5, 4, 8, 23, 1, 22), 0),
    ("ringspots",     (1, 0, 23, 2, 18, 22), 4),
    ("loopnet",       (18, 1, 19, 11, 7, 22), 2),
    ("satellite",     (0, 4, 1, 23, 18, 22), 6),
    ("sporedust",     (22, 23, 0, 1, 2, 18), 7),
    ("raphe",         (17, 8, 7, 23, 1, 22), 3),
    ("hexmesh",       (20, 19, 4, 18, 11, 22), 5),
    ("hyphae",        (12, 9, 18, 0, 8, 22), 1),
    ("ribbons",       (9, 16, 6, 7, 3, 22), 7),
    ("memfoam",       (20, 1, 23, 2, 0, 22), 4),
    ("beadchains",    (18, 7, 19, 0, 8, 22), 2),
    ("discs",         (17, 1, 23, 8, 4, 22), 3),
    ("swirlspecks",   (9, 3, 22, 0, 4, 1), 6),
)


def _n01(a):
    x = np.asarray(a, np.float32)
    lo, hi = float(np.percentile(x, 1.0)), float(np.percentile(x, 99.0))
    return np.clip((x - lo) / max(hi - lo, 1e-6), 0.0, 1.0).astype(np.float32)


def _rank_eight(a):
    """Eight deterministic, broadly occupied tiers from one authored field."""
    x = np.asarray(a, np.float32)
    cuts = np.percentile(x, (12.5, 25.0, 37.5, 50.0, 62.5, 75.0, 87.5))
    return np.searchsorted(cuts, x, side="right").astype(np.int32)


def _recipe_hue_tint(variant):
    """Small frozen tint keeps same-color recipes from becoming recolors.

    Violet garden/chain are deliberately separated within the still-violet
    family: their accepted fork/leaf versus beadchain topology survived owner
    eye, but hue-only NN was 72.209 before this material routing adjustment.
    """
    q = int(variant)
    tint = 0.022 * np.sin((q + 1) * 2.399963)
    if q == 24:       # fpe_violet_garden: cooler violet
        tint -= 0.014
    elif q == 29:     # fpe_violet_chains: warmer violet
        tint += 0.014
    return tint


def _hash(ix, iy, salt):
    return catlib.h2(ix, iy, int(salt)).astype(np.float32)


def _grid(xx, yy, pitch, angle, seed, salt):
    """Jittered local coordinates; every primitive stays inside one fine cell."""
    ca, sa = np.cos(angle), np.sin(angle)
    xr = xx * ca + yy * sa
    yr = -xx * sa + yy * ca
    ix = np.floor(xr / pitch)
    iy = np.floor(yr / pitch)
    jx = (_hash(ix, iy, seed + salt) - 0.5) * pitch * 0.28
    jy = (_hash(ix, iy, seed + salt + 37) - 0.5) * pitch * 0.28
    u = (xr - (ix + 0.5) * pitch) - jx
    v = (yr - (iy + 0.5) * pitch) - jy
    tier = np.floor(_hash(ix, iy, seed + salt + 79) * 8.0) / 7.0
    return u.astype(np.float32), v.astype(np.float32), tier.astype(np.float32), ix, iy


def _identity_pattern(fam, profile):
    """Twenty topologies from six alphabets; all remain cell-bounded."""
    a, b, c, d, e, f = fam
    modes = (
        a, b, c, d, e, f,
        np.maximum(a, b), np.maximum(c, d), np.abs(a - b), np.abs(c - f),
        a * d, b * e, np.maximum(a * 0.82, f), np.clip(b + c - 0.42, 0, 1),
        np.clip(d + e - 0.34, 0, 1), np.abs(e - f),
        np.clip(np.maximum(a, c) - b * 0.32, 0, 1), np.sqrt(np.clip(b * f, 0, 1)),
        np.clip(a + d + e - 0.72, 0, 1), np.clip(b + c + f - 0.82, 0, 1),
    )
    x = _n01(modes[int(profile) % 20])
    gamma = (0.72, 0.88, 1.04, 1.20)[int(profile) % 4]
    return np.clip(x ** gamma, 0, 1).astype(np.float32)


def _semantic_identity(fam, mode):
    """Compose six selected glyphs with lead/counter density parity.

    Both dominant roles carry a named primitive. Giving only the lead luma
    weight turned its organization into a macro dark/bright band; near-parity
    lets topology read as glyph substitution at constant visual density.
    """
    a, b, c, d, e, f = fam
    accents = (
        np.maximum(b, c), b * d, np.abs(b - c), np.clip(b + c - 0.38, 0, 1),
        np.maximum(c, d), np.sqrt(np.clip(b * e, 0, 1)),
        np.abs(c - f), np.maximum(b * 0.82, f),
    )
    base = 0.43 * a + 0.31 * b + 0.09 * c + 0.07 * d + 0.06 * e + 0.04 * f
    return _n01(base + 0.10 * accents[int(mode) % len(accents)])


def _semantic_glyph_bank(u0, v0, p0, u1, v1, p1, u2, v2, p2,
                         spot, broken_ring, slash, arc, fleck, sweep,
                         selected):
    """Lazily build only one recipe's six bounded glyph primitives."""
    d0, d1, d2 = np.hypot(u0, v0), np.hypot(u1, v1), np.hypot(u2, v2)

    def build(idx):
        if idx == 0:   # disc
            return spot
        if idx == 1:   # ring
            return broken_ring
        if idx == 2:   # crescent
            outer = np.exp(-((d1 / (p1 * 0.45 + 1e-4)) ** 6))
            inner = np.exp(-((np.hypot(u1 - p1 * 0.16, v1) /
                                  (p1 * 0.36 + 1e-4)) ** 6))
            return np.clip(outer - inner * 0.88, 0, 1)
        if idx == 3:   # arc
            return arc
        if idx == 4:   # spoke
            ring = np.exp(-(((d2 - p2 * 0.34) / (p2 * 0.09 + 1e-4)) ** 2))
            ray = np.clip((np.cos(np.arctan2(v2, u2) * 6.0) - 0.58) * 2.4,
                          0, 1) * np.exp(-((d2 / (p2 * 0.45 + 1e-4)) ** 5))
            return np.maximum(ring, ray)
        if idx == 5:   # star
            rays = np.clip((np.cos(np.arctan2(v0, u0) * 5.0) - 0.22) * 1.8,
                           0, 1) ** 2
            return np.exp(-((d0 / (p0 * 0.49 + 1e-4)) ** 6)) * (0.24 + 0.76 * rays)
        if idx == 6:   # slash
            return slash
        if idx == 7:   # capsule
            return np.exp(-((u2 / (p2 * 0.47 + 1e-4)) ** 8) -
                          ((v2 / (p2 * 0.20 + 1e-4)) ** 4))
        if idx == 8:   # needle
            return np.exp(-((u1 / (p1 * 0.47 + 1e-4)) ** 8)) * \
                np.exp(-((v1 / (p1 * 0.075 + 1e-4)) ** 2))
        if idx == 9:   # curl
            return np.maximum(sweep, np.roll(arc, 1, axis=1) * 0.86)
        if idx == 10:  # chevron
            line = np.abs(v2 - np.abs(u2) * 0.62 + p2 * 0.05)
            return np.exp(-((line / (p2 * 0.095 + 1e-4)) ** 2)) * \
                np.exp(-((u2 / (p2 * 0.47 + 1e-4)) ** 8))
        if idx == 11:  # cross
            a = np.exp(-((v1 / (p1 * 0.10 + 1e-4)) ** 2)) * \
                np.exp(-((u1 / (p1 * 0.46 + 1e-4)) ** 8))
            b = np.exp(-((u1 / (p1 * 0.10 + 1e-4)) ** 2)) * \
                np.exp(-((v1 / (p1 * 0.46 + 1e-4)) ** 8))
            return np.maximum(a, b)
        if idx == 12:  # fork / dendrite
            trunk = np.exp(-((u2 / (p2 * 0.075 + 1e-4)) ** 2)) * \
                np.exp(-((v2 / (p2 * 0.47 + 1e-4)) ** 8))
            a = np.exp(-(((u2 - (v2 + p2 * 0.04) * 0.68) /
                           (p2 * 0.085 + 1e-4)) ** 2)) * (v2 < p2 * 0.08)
            b = np.exp(-(((u2 + (v2 + p2 * 0.04) * 0.68) /
                           (p2 * 0.085 + 1e-4)) ** 2)) * (v2 < p2 * 0.08)
            return np.maximum(trunk, np.maximum(a, b))
        if idx == 13:  # leaf with central vein
            body = np.exp(-((np.abs(u0) / (p0 * 0.24 + 1e-4)) ** 3) -
                          ((np.abs(v0) / (p0 * 0.48 + 1e-4)) ** 6))
            vein = np.exp(-((u0 / (p0 * 0.055 + 1e-4)) ** 2)) * body
            return np.maximum(body * 0.72, vein)
        if idx == 14:  # petal
            return np.exp(-((np.abs(u0) / (p0 * 0.32 + 1e-4)) ** 3) -
                          ((np.abs(v0) / (p0 * 0.48 + 1e-4)) ** 6))
        if idx == 15:  # four-lobe petal cell
            a = np.exp(-((u1 / (p1 * 0.18 + 1e-4)) ** 4) -
                       ((v1 / (p1 * 0.46 + 1e-4)) ** 6))
            b = np.exp(-((u1 / (p1 * 0.46 + 1e-4)) ** 6) -
                       ((v1 / (p1 * 0.18 + 1e-4)) ** 4))
            return np.maximum(a, b)
        if idx == 16:  # comb / lamina ribs
            box = np.exp(-((u1 / (p1 * 0.48 + 1e-4)) ** 8) -
                         ((v1 / (p1 * 0.48 + 1e-4)) ** 8))
            return box * (0.5 + 0.5 * np.cos(v1 * np.pi /
                                             (p1 * 0.17 + 1e-4))) ** 5
        if idx == 17:  # ribbed pill / diatom
            pill = np.exp(-((u0 / (p0 * 0.48 + 1e-4)) ** 8) -
                          ((v0 / (p0 * 0.25 + 1e-4)) ** 4))
            ribs = (0.5 + 0.5 * np.cos(u0 * np.pi /
                                       (p0 * 0.16 + 1e-4))) ** 5
            return pill * (0.28 + 0.72 * ribs)
        if idx == 18:  # bead chain
            return np.maximum(spot, slash * 0.62)
        if idx == 19:  # trellis with leaf-knot nodes
            a = np.exp(-(((u2 - v2) / (p2 * 0.095 + 1e-4)) ** 2))
            b = np.exp(-(((u2 + v2) / (p2 * 0.095 + 1e-4)) ** 2))
            gate = np.exp(-((u2 / (p2 * 0.49 + 1e-4)) ** 8) -
                          ((v2 / (p2 * 0.49 + 1e-4)) ** 8))
            return np.maximum((np.maximum(a, b) * gate), fleck * 0.72)
        if idx == 20:  # cell wall / foam plate
            square_r = np.maximum(np.abs(u0), np.abs(v0))
            return np.exp(-(((square_r - p0 * 0.40) /
                              (p0 * 0.075 + 1e-4)) ** 2))
        if idx == 21:  # crack junction
            fork = build(12)
            return np.maximum(fork, np.roll(fork, 1, axis=0) * 0.64)
        if idx == 22:  # localized dust / spores
            return np.clip(fleck * 0.58 + spot * 0.42, 0, 1)
        if idx == 23:  # pore with mouth rim
            return np.maximum(broken_ring, spot * 0.58)
        raise ValueError(f"Unknown semantic glyph {idx}")

    return np.stack([
        np.clip(build(int(idx)), 0, 1).astype(np.float32) for idx in selected
    ], axis=0)


def _cell_pitches(profile):
    """Authoring-grid cell boxes for the three independent mark grids."""
    p = int(profile) % 20
    return (4.6 + (p % 5) * 1.13,
            5.0 + ((p * 3 + 1) % 5) * 1.07,
            5.4 + ((p * 7 + 2) % 5) * 1.01)


def _hue_composition(res, seed, variant):
    """Return one of forty fine-scale glyph-occupancy organizations.

    The first semantic rebuild proved that the named topologies were readable,
    but its single field-sized spirals/targets left 80-250 px density bands.
    This SPB-WILDS 2026-08-23 owner-eye repair repeats radial mechanisms across
    3-5 local centres and phase-compresses the remaining paths by 3.6-4.5x.
    The result is only a *probability router* for complete 8-32 px glyph boxes;
    it is never painted as RGB/value and never becomes a macro primitive.
    """
    q = int(variant) % 40
    slot = q % 20
    category = q // 20
    p = (_BLOOM_TOPOLOGY if category == 0 else _PETRI_TOPOLOGY)[slot]
    yy, xx = np.mgrid[:res, :res].astype(np.float32)
    u = (xx + 0.5) / float(res) - 0.5
    v = (yy + 0.5) / float(res) - 0.5
    # Seed motion keeps same-index BLOOM/PETRI members from being recolors.
    phase = ((int(seed) * 0.00061803398875) % 1.0) * np.pi * 2.0
    theta = phase * 0.17 + p * 0.239 + category * 0.41
    ca, sa = np.cos(theta), np.sin(theta)
    x = u * ca + v * sa
    y = -u * sa + v * ca
    if category:
        x0, y0 = x, y
        x = x0 + 0.105 * np.sin(y0 * (9.0 + (slot % 3) * 2.0) + phase)
        y = y0 + 0.085 * np.sin(x0 * (11.0 + (slot % 4)) - phase * 0.73)
    cx = 0.12 * np.sin(phase + p * 0.71)
    cy = 0.12 * np.cos(phase * 0.83 - p * 0.47)
    dx, dy = u - cx, v - cy
    rad = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)

    # Multiple smoothly repeating local centres retire the one giant
    # field-sized rosette/target/diamond.  Sine-warp coordinates are continuous
    # at motif boundaries, unlike a hard tiled modulo, so they do not introduce
    # a shared checker seam.  The centres move with recipe and seed.
    motif_count = 3.35 + 0.34 * (slot % 5) + category * 0.28
    mx = 0.50 * np.sin((x * motif_count + phase * 0.071) * np.pi * 2.0)
    my = 0.50 * np.sin((y * (motif_count + 0.37) - phase * 0.053) * np.pi * 2.0)
    mrad = np.hypot(mx, my)
    mang = np.arctan2(my, mx)
    local_radial = p in {1, 2, 3, 6, 7, 11, 13, 17, 18, 19}

    if p == 0:       # diagonal fault strata
        z = x * 4.4 + 0.23 * np.sin(y * 14.0 + phase)
    elif p == 1:     # many displaced target-ring colonies
        z = mrad * 8.4 + 0.25 * np.sin(mang * 3.0 + phase)
    elif p == 2:     # twin-source interference
        r2 = np.hypot(mx + 0.24, my - 0.18)
        z = (mrad - r2) * 12.0 + (mrad + r2) * 2.1
    elif p == 3:     # local coiled rosettes, not one macro spiral
        z = mrad * 7.6 + mang * (1.15 + category * 0.32) / np.pi
    elif p == 4:     # nested chevrons
        z = (np.abs(x) + y * (0.72 + category * 0.14)) * 6.1
    elif p == 5:     # meandering rivers
        z = x * 5.1 + 0.72 * np.sin(y * 7.0 + phase) + 0.18 * np.sin(y * 19.0)
    elif p == 6:     # local fractured sunburst sectors + close radial ribs
        z = mang * (3.0 + category) / np.pi + mrad * 5.4
    elif p == 7:     # local offset diamond lenses
        z = (np.abs(mx * 1.15) + np.abs(my * 0.84)) * 8.0 + mang * 0.18
    elif p == 8:     # sedimentary shelves
        z = y * 5.6 + 0.44 * np.sin(x * 8.0 + phase) + 0.15 * np.sin(x * 23.0)
    elif p == 9:     # mirrored botanical wings
        z = np.abs(x + 0.18 * np.sin(y * 10.0 + phase)) * 7.8 + y * 1.1
    elif p == 10:    # skewed tiled facets
        z = np.sin(x * 10.0 + phase) + np.cos(y * 12.0 - phase * 0.7) + x * 1.8
    elif p == 11:    # many local petal/bloom lobes
        z = mrad * 5.0 + np.cos(mang * (4.0 + category)) * (0.95 - np.clip(mrad, 0, 0.8))
    elif p == 12:    # hourglass pinch field
        z = (x * x * 1.9 - y * y) * 9.0 + x * 1.4 + np.sin(y * 8.0) * 0.22
    elif p == 13:    # paired local cellular halos
        r2 = np.hypot(mx - 0.27, my + 0.17)
        r3 = np.hypot(mx + 0.23, my - 0.21)
        z = np.minimum(r2, r3) * 9.0 + np.maximum(r2, r3) * 1.3
    elif p == 14:    # crossing fault fans
        z = np.sin((x + y) * 9.0 + phase) + 0.72 * np.sin((x - y) * 13.0 - phase)
    elif p == 15:    # lissajous current
        z = np.sin(x * 8.0 + np.sin(y * 6.0 + phase)) + np.cos(y * 10.0 + phase * 0.6)
    elif p == 16:    # S-flow ribbons
        z = (x + 0.34 * np.sin(y * 6.2 + phase) + 0.13 * np.sin(y * 15.0)) * 6.3
    elif p == 17:    # many nested square shock cells
        z = np.maximum(np.abs(mx), np.abs(my)) * 10.0 + np.minimum(np.abs(mx), np.abs(my)) * 1.4
    elif p == 18:    # local kaleidoscope wedges
        fold = np.abs(np.mod(mang + np.pi / 5.0, np.pi / 2.5) - np.pi / 5.0)
        z = fold * 3.2 + mrad * 6.2
    else:            # local counter-rotating twin spirals
        dx2, dy2 = mx + 0.23, my - 0.16
        r2, a2 = np.hypot(dx2, dy2), np.arctan2(dy2, dx2)
        # Keep opposite angular winding without letting the two radial slopes
        # cancel into a wide low-gradient plateau.
        z = mrad * 7.2 + mang / np.pi - r2 * 2.4 + a2 / np.pi

    if category:
        # PETRI's layouts are compound living currents; BLOOM keeps the
        # cleaner botanical/fault skeleton.  Both remain hue-only.
        z = z + 0.34 * np.sin((x * (5.0 + slot % 4) - y * (7.0 + slot % 3))
                              * np.pi + phase)
    # The compressed phase is retained only as a tiny spec/hue wobble. Local
    # radial mechanisms already gained 3-5x frequency from ``motif_count``;
    # continuous paths receive the same increase here. This frequency is never
    # a painted band: it only changes which complete micro-glyph cells occur.
    jitter = 0.09 * np.sin((x * 31.0 + y * 23.0) * np.pi + phase)
    organization_frequency = ((1.12 + 0.10 * (slot % 4)) if local_radial
                              else (3.60 + 0.30 * (slot % 4)))
    organization_frequency *= _TOPOLOGY_FINE_MULTIPLIER[p]
    routed_phase = (z + jitter * 0.34) * organization_frequency
    broad = np.mod(routed_phase + category * 0.37, 1.0).astype(np.float32)
    org_phase = 0.5 + 0.5 * np.cos((routed_phase + category * 0.23) * np.pi * 2.0)
    organization = cv2.GaussianBlur(org_phase.astype(np.float32), (0, 0),
                                    max(0.70, res / 820.0))
    return broad, _n01(organization)


def _signature_fields(res, seed, profile, engine_field=None):
    """Return value/hue maps + six full-box 8-32 px mark families.

    ``res`` is the 640 authoring grid.  Cell pitches are 4.6-9.6 authoring
    pixels, which become 14.7-30.7 pixels on a 2048 canvas.  Spot/ring/segment
    widths are bounded to at least 0.55 cell, so no dominant one-pixel dust is
    being used to game a fineness score.
    """
    variant = int(profile) % 40
    p = variant % 20
    broad_hue, organization = _hue_composition(res, seed, variant)
    yy, xx = np.mgrid[:res, :res].astype(np.float32)
    a0 = (p * 0.38196601125 + 0.11) * np.pi
    p0, p1, p2 = _cell_pitches(p)

    u0, v0, t0, i0, j0 = _grid(xx, yy, p0, a0, seed, 101)
    u1, v1, t1, i1, j1 = _grid(xx, yy, p1, a0 + 1.047, seed, 211)
    u2, v2, t2, i2, j2 = _grid(xx, yy, p2, a0 - 0.733, seed, 307)

    d0 = np.hypot(u0, v0)
    d1 = np.hypot(u1, v1)
    d2 = np.hypot(u2, v2)

    # Six visual alphabets: domed spots, broken rings, bounded slashes,
    # clipped arcs, rounded flecks and curved capsules.  All six are present
    # in every finish; profile-specific weights decide which two lead.
    spot = np.exp(-((d0 / (p0 * 0.31 + 1e-4)) ** 4))
    ring = np.exp(-(((d1 - p1 * 0.33) / (p1 * 0.13 + 1e-4)) ** 2))
    gate = np.clip((np.cos(np.arctan2(v1, u1) - t1 * np.pi * 2.0) - 0.05) * 2.5, 0, 1)
    broken_ring = ring * (0.28 + 0.72 * gate)
    slash = np.exp(-((v2 / (p2 * 0.28 + 1e-4)) ** 4)) * \
            np.exp(-((u2 / (p2 * 0.47 + 1e-4)) ** 8))
    arc = np.exp(-(((d0 - p0 * 0.36) / (p0 * 0.15 + 1e-4)) ** 2)) * \
          np.clip((np.sin(np.arctan2(v0, u0) * (2 + p % 3) + t0 * 6.0) + 0.35) * 1.1, 0, 1)
    fleck = np.exp(-((u1 / (p1 * 0.31 + 1e-4)) ** 6) -
                   ((v1 / (p1 * 0.27 + 1e-4)) ** 6))
    bend = (0.18 + 0.07 * (p % 4)) / max(p2, 1e-3)
    curve_v = v2 - bend * (u2 * u2 - p2 * p2 * 0.12)
    sweep = np.exp(-((curve_v / (p2 * 0.28 + 1e-4)) ** 4)) * \
            np.exp(-((u2 / (p2 * 0.48 + 1e-4)) ** 8))

    recipe_name, selected, mode = _SEMANTIC_RECIPES[variant]
    glyph_bank = _semantic_glyph_bank(
        u0, v0, p0, u1, v1, p1, u2, v2, p2,
        spot, broken_ring, slash, arc, fleck, sweep, selected,
    )
    # Topology performs complementary lead<->counter glyph substitution at
    # nearly constant density. It never creates an empty/dark broad band. The
    # fine phase-compressed router means every visible run/gap is 8-32 px at
    # native 2048; the remaining four roles stay sparse supporting accents.
    organization2 = np.roll(organization, res // 7, axis=1)
    routing = np.clip((organization - 0.24) / 0.52, 0.0, 1.0)
    routing = routing * routing * (3.0 - 2.0 * routing)
    tertiary_pick = (_hash(i2, j2, seed + 661) < (0.22 + 0.42 * organization2))
    lead_org = 0.16 + 0.84 * routing
    counter_org = 0.16 + 0.84 * (1.0 - routing)
    gates = np.stack([
        lead_org,
        (0.18 + 0.82 * (t1 > 0.18)) * counter_org,
        (0.14 + 0.86 * tertiary_pick.astype(np.float32)) * (0.18 + 0.82 * (t2 > 0.32)),
        (0.12 + 0.88 * (t0 > 0.56)),
        (0.10 + 0.90 * (t1 > 0.68)),
        (0.08 + 0.92 * (t2 > 0.78)),
    ], axis=0).astype(np.float32)
    fam = (glyph_bank * gates).astype(np.float32)
    identity = _semantic_identity(fam, mode)
    # The recipe order itself carries meaning: lead, counter, tertiary, then
    # three supports. Small per-recipe shifts vary prominence without turning
    # the table into rotations of one shared alphabet.
    weights = np.asarray([0.39, 0.28, 0.12, 0.09, 0.07, 0.05], np.float32)
    weights[3 + (variant % 3)] += 0.018
    weights[(mode + 1) % 3] += 0.012
    weights /= float(weights.sum())
    marks = np.tensordot(weights, fam, axes=(0, 0)).astype(np.float32)

    if engine_field is None:
        raw_structural = structural = marks
    else:
        raw_structural = cv2.resize(_n01(engine_field), (res, res), interpolation=cv2.INTER_LINEAR)
        # Remove the old global silhouette while retaining the finish's own
        # fine ridges/edges as a seventh, name-specific structural signal.
        slow = cv2.GaussianBlur(raw_structural, (0, 0), 2.8)
        structural = _n01(np.abs(raw_structural - slow))

    primary = fam[0]
    secondary = fam[1]
    value = _n01(0.36 * identity + 0.20 * marks + 0.18 * structural +
                 0.13 * primary * t0 + 0.13 * secondary * (1.0 - t1))
    hue = np.mod(0.31 * structural + 0.27 * t0 + 0.19 * (1.0 - t1) +
                 0.14 * t2 + 0.31 * primary + variant * 0.071, 1.0).astype(np.float32)
    return (value.astype(np.float32), hue, fam, t0, t1, t2,
            raw_structural.astype(np.float32), identity, broad_hue,
            weights.astype(np.float32))


class FineFractureKit(catlib.CategoryKit):
    """CategoryKit with micro-only identity maps and true three-channel phases."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signature_cached = lru_cache(maxsize=8)(self._signature_fid)

    def _signature_fid(self, fid):
        d = self.ALL[fid]
        # A 256 probe is enough to recover the old generator's name-specific
        # ridges.  It is high-passed before use, so no macro flower/cell island
        # can re-enter the new paint.
        probe = np.asarray(self.engines[d["engine"]](256, int(d["seed"]),
                                                     **d.get("eargs", {})), np.float32)
        variant = int(d.get("wild_variant", d["wild_profile"]))
        return _signature_fields(self.GEN, int(d["seed"]), variant, probe)

    def macro_maps(self, d):
        value, hue, _, _, _, _, raw, identity, _, _ = self.signature_cached(d["id"])
        # The old generator remains the name-specific lead.  Six auxiliary
        # families enrich it; they do not flatten twenty designs into one
        # shared micro-noise skin.
        return _n01(0.76 * identity + 0.24 * raw), \
            np.mod(0.72 * identity + 0.28 * raw, 1.0).astype(np.float32)

    def art_work(self, fid):
        value, local_hue, fam, t0, t1, t2, raw, identity, broad_hue, weights = \
            self.signature_cached(fid)
        d = self.ALL[fid]
        profile = int(d["wild_profile"])
        variant = int(d.get("wild_variant", profile))

        # Do not let the old category generators remain the hidden lead.  Their
        # twenty functions converged on the same broad cell skin.  Only their
        # high-passed, name-specific ridge signal survives as one of seven fine
        # inputs to this new painter.
        raw_hi = _n01(np.abs(raw - cv2.GaussianBlur(raw, (0, 0), 2.6)))
        detail = _n01(np.tensordot(weights, fam, axes=(0, 0)))
        lead = fam[0]
        counter = fam[1]
        tertiary = fam[2]
        fine_luma = _n01(0.44 * lead + 0.30 * counter + 0.10 * detail +
                         0.03 * raw_hi + 0.08 * value + 0.05 * tertiary)
        # SPB-WILDS 2026-08-23 owner-eye repair.  The rejected candidate used
        # ``broad_hue * 4 mod 1`` as visible paint and collapsed into the same
        # zebra/checker grammar.  Luma is now eight discrete shades cut only
        # from the finish's own six glyph families and name-specific old-engine
        # ridges.  Narrow soft contour bands + localized tier stipple raise
        # fine energy without adding full-field noise or enlarging a mark.
        contour_bank = []
        for k, field in enumerate(fam):
            level = 0.28 + 0.055 * ((profile + k * 3) % 5)
            width = 0.070 + 0.010 * ((profile + k) % 3)
            band = np.exp(-(((field - level) / width) ** 2))
            gx = cv2.Sobel(field, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(field, cv2.CV_32F, 0, 1, ksize=3)
            ridge = _n01(np.hypot(gx, gy))
            contour_bank.append(np.clip(0.70 * band + 0.30 * ridge, 0, 1))
        contours = np.stack(contour_bank, axis=0).astype(np.float32)
        contour_weights = np.asarray([0.42, 0.31, 0.11, 0.07, 0.05, 0.04],
                                     np.float32)
        contour_detail = _n01(np.tensordot(contour_weights, contours, axes=(0, 0)))
        localized_stipple = np.clip(
            lead * (0.55 * t0 + 0.25 * (1.0 - t1)) +
            counter * 0.20 * t2, 0, 1)
        semantic_relief = _n01(0.34 * lead + 0.28 * counter +
                               0.18 * contour_detail + 0.10 * fine_luma +
                               0.04 * tertiary + 0.03 * localized_stipple +
                               0.03 * raw_hi)
        luma_levels = np.asarray(
            [0.18, 0.27, 0.36, 0.46, 0.57, 0.68, 0.80, 0.93], np.float32)
        li = np.clip((semantic_relief * 8.0).astype(np.int32), 0, 7)
        target_luma = luma_levels[li]
        # A sub-pixel authoring-grid antialias softens contour stair steps;
        # complete glyph boxes remain 8-32px at native 2048.
        target_luma = cv2.GaussianBlur(target_luma, (3, 3), 0.42)

        hs = list(d.get("hues", ()))
        hero = (float(hs[0]) if hs else 0.82) + _recipe_hue_tint(variant)
        hero %= 1.0
        offsets = _OPPONENT_OFFSETS[profile % 20]
        opponents = tuple((hero + x) % 1.0 for x in offsets)
        bias = 0.035 if variant >= 20 else 0.0
        # Calm hero/counter body; the frozen opponent hue is applied to the
        # lead glyph *last*, so overlaps cannot wash it back toward a generic
        # mixed color. Broad topology is completely absent from visible hue.
        # This preserves iter6 paint geometry while making the Fractured travel
        # an unambiguous hero<->opponent handoff on actual named marks.
        hcur = np.mod(hero + (local_hue - 0.5) * 0.018, 1.0)
        for field, target, amount in (
                (counter, hero, 0.90),
                (tertiary, opponents[2], 0.06),
                (contour_detail, opponents[(profile + 1) % 3], 0.03),
                (lead, (opponents[0] + bias) % 1.0, 0.98)):
            mk = np.clip((field - 0.18) * 1.62, 0.0, 1.0) * amount
            dh = ((target - hcur + 0.5) % 1.0) - 0.5
            hcur = np.mod(hcur + dh * mk, 1.0)
        sat = np.clip(0.52 + 0.12 * detail + 0.355 * lead +
                      0.04 * counter - 0.02 * tertiary +
                      float(d.get("kw", {}).get("gray", 0.0)) * -0.22,
                      0.42, 0.94)
        hsv = np.stack([hcur * 179.0, sat * 255.0,
                        np.clip(0.60 + 0.38 * fine_luma, 0, 1) * 255.0], axis=2)
        rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0
        # Hue must not smuggle broad value shapes into the finish.  Restore the
        # fine-only target luma exactly after the HSV conversion.
        actual_luma = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        rgb = np.clip(rgb * (target_luma / np.maximum(actual_luma, 1e-3))[..., None], 0, 1)
        rgb = cv2.resize(rgb, (self.WORK, self.WORK), interpolation=cv2.INTER_CUBIC)
        aa = cv2.GaussianBlur(rgb, (3, 3), 0.38)
        slow = cv2.GaussianBlur(aa, (0, 0), 0.92)
        return np.clip(aa + (aa - slow) * 0.34, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def _mask(mask, h, w):
        m = np.asarray(mask, np.float32)
        if m.ndim == 3:
            m = m[:, :, 0]
        if m.shape[:2] != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
        return np.clip(m, 0.0, 1.0)

    def mk(self, fid):
        # Paint uses CategoryKit's canonical linear resize + mask/pm contract.
        # Spec is rebuilt here because the old shared M/R/Cc formula was the
        # cross-category collapse.
        _, paint_fn = super().mk(fid)
        work = int(self.WORK)

        def spec_fn(shape, mask, seed, sm):
            fh, fw = int(shape[0]), int(shape[1])
            art = self.art_work_cached(fid)
            value, hue, fam, t0, t1, t2, raw, identity, broad_hue, _ = \
                self.signature_cached(fid)
            value = cv2.resize(value, (work, work), interpolation=cv2.INTER_LINEAR)
            hue = cv2.resize(hue, (work, work), interpolation=cv2.INTER_LINEAR)
            fam = np.stack([cv2.resize(x, (work, work), interpolation=cv2.INTER_LINEAR)
                            for x in fam], axis=0)
            t0 = cv2.resize(t0, (work, work), interpolation=cv2.INTER_NEAREST)
            t1 = cv2.resize(t1, (work, work), interpolation=cv2.INTER_NEAREST)
            t2 = cv2.resize(t2, (work, work), interpolation=cv2.INTER_NEAREST)
            raw = cv2.resize(raw, (work, work), interpolation=cv2.INTER_LINEAR)
            identity = cv2.resize(identity, (work, work), interpolation=cv2.INTER_LINEAR)
            broad_hue = cv2.resize(broad_hue, (work, work), interpolation=cv2.INTER_NEAREST)

            lum = _n01(0.299 * art[:, :, 0] + 0.587 * art[:, :, 1] + 0.114 * art[:, :, 2])
            profile = int(self.ALL[fid]["wild_profile"])
            f0 = fam[0]
            f1 = fam[1]
            f2 = fam[2]

            # Three genuinely independent phase fields.  M follows the
            # colored paint relief; Cc is half a cycle away on a different
            # mark family, so the tinted metal and white environment lobes
            # trade dominance as the real car highlight sweeps.  R is a third
            # eight-step aperture ladder, not a copy of either power channel.
            base_pm = np.mod((0.30 * lum + 0.24 * hue + 0.22 * f0 +
                              0.16 * t0 + 0.08 * raw) * 3.15 + profile * 0.061, 1.0)
            # Saturation-weighted circular distance from the hero is the
            # authoritative opponent gate. It is itself produced by the lead
            # semantic glyph, so metal/clear angle phases follow the feature;
            # a white highlight has zero saturation and cannot enter the gate.
            art8 = np.clip(art * 255.0, 0, 255).astype(np.uint8)
            paint_hsv = cv2.cvtColor(art8, cv2.COLOR_RGB2HSV).astype(np.float32)
            paint_hue = paint_hsv[:, :, 0] / 179.0
            paint_sat = paint_hsv[:, :, 1] / 255.0
            hs = list(self.ALL[fid].get("hues", ()))
            variant = int(self.ALL[fid].get("wild_variant", profile))
            hero = (float(hs[0]) if hs else 0.82) + _recipe_hue_tint(variant)
            hero %= 1.0
            bias = 0.035 if variant >= 20 else 0.0
            opponent = (hero + _OPPONENT_OFFSETS[profile % 20][0] + bias) % 1.0
            hero_distance = np.abs(((paint_hue - hero + 0.5) % 1.0) - 0.5) * 2.0
            opponent_distance = np.abs(((paint_hue - opponent + 0.5) % 1.0) - 0.5) * 2.0
            opponent_affinity = (hero_distance - opponent_distance) * paint_sat
            opponent_gate = _n01(0.84 * opponent_affinity + 0.16 * f0)
            pm_score = 0.62 * opponent_gate + 0.38 * base_pm
            pr = np.mod((0.24 * (1.0 - lum) + 0.22 * f1 + 0.24 * t1 +
                         0.18 * value + 0.12 * (1.0 - raw)) * 3.55 +
                        profile * 0.113, 1.0)
            # Cc shares only the semantic opponent gate with M. Its actual
            # phase is independently built from tertiary/support glyphs and a
            # third tier grid; this preserves color handoff without the old
            # near-copy correlation.
            pc_base = np.mod((0.22 * (1.0 - lum) + 0.26 * f2 + 0.22 * t2 +
                              0.18 * fam[5] + 0.12 * hue) * 3.35 +
                             profile * 0.173, 1.0)
            pc_score = 0.50 * opponent_gate + 0.39 * pc_base + \
                       0.11 * (1.0 - base_pm)
            # Rank tiers guarantee all eight wide shades are materially
            # occupied instead of merely declared in a palette. M/R/Cc use
            # different phase fields; only M/Cc cooperate on opponent glyphs.
            mi = _rank_eight(pm_score)
            ri = _rank_eight(pr)
            ci = _rank_eight(pc_score)
            metal = _M_LEVELS[mi]
            rough = _R_LEVELS[ri]
            clear = _C_LEVELS[ci]

            mk = self._mask(mask, work, work)
            strength = np.clip(float(sm), 0.0, 1.0) * mk
            neutral = np.float32([4.0, 120.0, 16.0])
            dyn = np.stack([metal, rough, clear], axis=2)
            out3 = neutral[None, None, :] + (dyn - neutral[None, None, :]) * strength[..., None]
            out = np.empty((work, work, 4), np.uint8)
            out[:, :, :3] = np.clip(out3, 0, 255).astype(np.uint8)
            out[:, :, 3] = 255
            if (fh, fw) != (work, work):
                out = cv2.resize(out, (fw, fh), interpolation=cv2.INTER_LINEAR)
            return out

        return spec_fn, paint_fn
