# -*- coding: utf-8 -*-
"""🌍 WORLD OF COLOR kit (2026-08-31) — how the world actually makes colour.

Owner: *"COLORSHOXX and its 77 finishes was originally designed to try to do
something unique with color flipping. It's outdated and very repetitive now.
I'm thinking of taking that from 77 finishes to 100 and repurposing this to
WORLD OF COLOR which will take colors/styles from various COUNTRIES and making
something out of it. Irish, Scottish, Japanese, African, Jamaican, Australian,
etc."*

SCOPE, deliberately drawn. SPB already has five CULTURAL shelves built on flags
and iconography — RISING SUN, UNION JACKED, VIVA MEXICO, FORBIDDEN DRAGON, LET
FREEDOM RING. WORLD OF COLOR is a different axis on purpose: it is about the
MATERIALS AND CRAFT PROCESSES a place makes colour with. Not Japan's flag —
Japan's indigo vat, its urushi lacquer, its raku kiln. That keeps this shelf
from duplicating a category that already exists, and it is the more interesting
question anyway.

It also keeps the work honest. Everything here is drawn from commercially made
textiles, ceramics, minerals and landscape — tartan setts, azulejo, celadon,
ochre, salt pans. Sacred and ceremonial designs are not source material for car
paint, and none are used.

Four processes the rest of the catalog has no way to draw:

    sett     woven bands crossing at right angles with real over/under
    stars    the n-pointed star-and-rosette tiling of zellij and iznik
    ikat     warp-resist: dye applied to the thread, so the pattern arrives
             blurred along one axis only, and the blur IS the signature
    resist   wax or mud applied before the dye, then cracked
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

from engine.expansions.fractured_flames_kit_2026 import (      # noqa: F401
    GEN, WORK, fbm, n01, pct, rng, upscale, cell_mean, worley, curl, filaments,
    dla, percolate, spall, anneal_crack, kh_braid, rt_fingers, sparks, eden,
    wrinkle, _h1,
)
from engine.expansions.fractured_cosmos_kit_2026 import (      # noqa: F401
    craters, dunes, polygons, honeycomb, bands, crinkle,
)

_TAU = 6.283185307179586


def sett(shape, seed, pitch=46.0, stripes=(0.30, 0.10, 0.06, 0.18, 0.06, 0.10),
         twill=7.0, weave=1.0, ratio=1.0):
    """A tartan sett: one sequence of coloured bands, repeated and reflected,
    run in BOTH directions, with the twill visible where they cross.

    The sett is the repeating unit and it is symmetric about its pivots, which
    is why tartan reads as ordered rather than striped. Where warp crosses weft
    the colours do not blend — one thread is simply on top — so this returns the
    over/under as a real alternation rather than a multiply.
    """
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    P = max(16.0, float(pitch) * sc)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    band = np.asarray(stripes, np.float32)
    band = band / max(band.sum(), 1e-6)
    edges = np.concatenate([[0.0], np.cumsum(band)])
    # reflect the sequence so the sett has pivots, like a real one
    full = np.concatenate([edges[:-1] * 0.5, 0.5 + (1.0 - edges[::-1][:-1]) * 0.5])
    levels = np.linspace(0.08, 1.0, len(band))
    levels = np.concatenate([levels, levels[::-1]])

    def run(u):
        t = np.mod(u / P, 1.0)
        idx = np.clip(np.searchsorted(full, t, side="right") - 1, 0, len(levels) - 1)
        return levels[idx]

    warp = run(xx)
    weft = run(yy * float(ratio))
    # twill: a 2/2 diagonal decides which thread shows at each crossing
    tw = np.mod((xx + yy) / max(twill * sc, 1.0), 2.0) < 1.0
    over = np.where(tw, warp, weft)
    under = np.where(tw, weft, warp)
    out = over * (0.62 + 0.38 * float(weave)) + under * (0.38 * (1.0 - 0.4 * float(weave)))
    # thread grain, so it is cloth and not printed stripes
    g = fbm((h, w), seed + 5, octaves=(256, 512), weights=(1.0, 0.6)) - 0.5
    return pct(np.clip(out + g * 0.10, 0, None))


def stars(shape, seed, cell=150.0, points=8, ring=0.34, interlace=1.0, warp=10.0):
    """Star-and-rosette tiling — zellij, iznik, azulejo, jali.

    An n-pointed star is |cos(n*phi/2)| in polar form, so the whole tiling can be
    written as a field: fold to a cell, take the star radius, band it. The
    interlace term is what makes it read as strapwork rather than wallpaper —
    the bands cross over and under each other.
    """
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    C = max(12.0, float(cell) * sc)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if warp:
        xx = xx + (fbm((h, w), seed + 11, octaves=(4, 8, 16), weights=(1.0, .5, .3)) - 0.5) * warp * sc
        yy = yy + (fbm((h, w), seed + 17, octaves=(4, 8, 16), weights=(1.0, .5, .3)) - 0.5) * warp * sc
    row = np.floor(yy / C)
    dx = np.mod(xx + row * C * 0.5, C) - C * 0.5
    dy = np.mod(yy, C) - C * 0.5
    rho = np.hypot(dx, dy) / (C * 0.5)
    phi = np.arctan2(dy, dx)
    star = np.abs(np.cos(float(points) * phi * 0.5)) ** 0.6
    d = rho / np.maximum(star * 0.85 + 0.15, 0.12)
    outline = np.exp(-((d - 1.0) ** 2) / (2.0 * (float(ring) * 0.35) ** 2))
    fill = np.clip(1.0 - d, 0, 1) ** 0.7
    out = np.maximum(fill * 0.72, outline)
    if interlace:
        strap = 0.5 + 0.5 * np.sin(_TAU * (rho * 3.0 + phi * float(points) / _TAU))
        out = np.clip(out * (0.72 + 0.28 * strap * float(interlace)), 0, 1)
    return pct(out)


def ikat(shape, seed, motifs=1100, blur=10.0, axis=0, sharp=1.3, rows=64):
    """Warp-resist weaving. The yarn is tied and dyed BEFORE it goes on the loom,
    so the design arrives smeared along the warp and crisp across it. That
    one-axis blur is the whole signature of an ikat and no symmetric filter can
    fake it."""
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    r = rng(seed)
    out = np.zeros((h, w), np.float32)
    rh = h / float(max(rows, 1))
    for i in range(int(motifs)):
        row = i % int(rows)
        cy = (row + 0.5) * rh + r.uniform(-0.12, 0.12) * rh
        cx = r.uniform(0, w)
        rad = r.uniform(0.32, 0.55) * rh
        y0, y1 = int(max(0, cy - rad * 2)), int(min(h, cy + rad * 2))
        x0, x1 = int(max(0, cx - rad * 2)), int(min(w, cx + rad * 2))
        if y1 <= y0 or x1 <= x0:
            continue
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot((gx - cx) / rad, (gy - cy) / rad)
        lobes = 1.0 + 0.42 * np.cos(float(r.integers(4, 9)) * np.arctan2(gy - cy, gx - cx))
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1],
                                       np.clip(1.0 - d / np.maximum(lobes, 0.2), 0, 1) ** sharp)
    if cv2 is not None and blur > 0:
        k = int(max(3, round(blur * sc)) | 1)
        kern = np.ones((1, k), np.float32) / k if axis == 0 else np.ones((k, 1), np.float32) / k
        out = cv2.filter2D(out, -1, kern)
        # the weave itself stays crisp across the smear
        yy = np.mgrid[0:h, 0:w][0].astype(np.float32)
        out = out * (0.80 + 0.20 * (0.5 + 0.5 * np.sin(yy * _TAU / max(3.0 * sc, 1.0))))
    return pct(out)


def resist(shape, seed, patches=120, crackle=1.0, cells=150, bleed=0.4):
    """Wax or mud resist, then dye, then crack. Batik and bogolan both work this
    way: the resist keeps the dye off, and the value of the thing is in the
    crazing that lets a little through anyway."""
    h, w = int(shape[0]), int(shape[1])
    covered, lab = percolate((h, w), seed, cells=int(cells), p=0.46)
    # The crackle runs along the EDGES OF THE RESIST ITSELF — wax cracks where
    # it is thin, which is at the boundary of each patch. Taking those boundaries
    # from the percolate labels we already have is physically right and costs
    # nothing; the annealing crack simulation it replaces was 0.73s, more than
    # half this primitive's whole budget.
    lab_i = np.asarray(lab, np.int64)
    edge = np.zeros((h, w), np.float32)
    edge[:, :-1] += (lab_i[:, :-1] != lab_i[:, 1:])
    edge[:-1, :] += (lab_i[:-1, :] != lab_i[1:, :])
    if cv2 is not None:
        edge = cv2.dilate(np.clip(edge, 0, 1), np.ones((2, 2), np.float32))
        edge = cv2.GaussianBlur(edge, (0, 0), max(0.7, w / 2048.0))
    cr = pct(edge) * (0.55 + 0.45 * fbm((h, w), seed + 23, octaves=(64, 128, 256),
                                        weights=(1.0, .7, .45)))
    dye = np.clip(1.0 - covered + cr * float(crackle) * 0.85, 0, 1)
    if bleed and cv2 is not None:
        dye = cv2.GaussianBlur(dye, (0, 0), max(0.6, float(bleed) * w / 2048.0 * 2.0))
    return pct(dye), lab
