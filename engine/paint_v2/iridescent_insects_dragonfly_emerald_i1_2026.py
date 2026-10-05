"""Emerald Skimmer I1 — quasi-ordered nanosphere colour clouds in Odonata cuticle.

SPB-105 / IRIDESCENT INSECTS tick 22 / owner 2026-09-01: "FINE DETAILS"
at 8-32px native and many distinct spec shades.  Unlike Dragonfly Resilin's
structural vein lattice, this carrier is built around coherent-scattering
nanosphere populations under thin translucent cuticle, melanin stiffeners that
purify the colour, and wax-platelet bloom.  Metric movement is recorded after
each isolated adapter pass in the rebuild ledger before live promotion.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

GEN = 640


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape)
    a = np.asarray(a, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, col):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask * pm * .96, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(col, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


@lru_cache(maxsize=2)
def _surface(seed):
    # Solve at 640² but express all geometry in a virtual 1024² field.  The
    # final 2048² render therefore keeps every dot/rim/platelet in the owner's
    # required 8-32px native range without paying a 2048² construction cost.
    s = GEN / 1024.0
    y, x = coords(GEN)
    x, y = x / s, y / s
    seed = int(seed)
    k = (seed % 1009) / 1009.0

    # Closely packed but non-periodic epidermal nanosphere populations.  Their
    # colour does not come from isolated dots: several connected population
    # fields decide which entire bead clusters coherently scatter together.
    dx, dy, d1, fid, d2 = _cells(GEN, 5.9 * s, seed % 7919 + 171071,
                                  jit=.66, taps=9, need2=True)
    d1, d2 = d1 / s, d2 / s
    bead = cv2.GaussianBlur(np.clip(1 - d1 / 2.75, 0, 1), (0, 0), .38)
    bead_core = cv2.GaussianBlur(np.clip(1 - d1 / 1.25, 0, 1), (0, 0), .32)
    bead_rim = cv2.GaussianBlur(np.clip(1 - np.abs(d1 - 2.15) / .62, 0, 1), (0, 0), .42)
    interstice = np.clip((d2 - d1 - .42) / 1.12, 0, 1)

    u = x + 13.0 * np.sin(y / 67.0 + k * 3.7) + 5.0 * np.sin((x + y) / 127.0)
    v = y - 9.0 * np.sin(x / 83.0 - k * 2.1) + 3.8 * np.sin((x - 2 * y) / 91.0)
    cloud_a = n01(np.sin(u / 28.0) + .72 * np.cos(v / 44.0) + .34 * np.sin((u + v) / 73.0))
    cloud_b = n01(np.cos((u - .31 * v) / 37.0) + .61 * np.sin((v + .42 * u) / 55.0))
    cloud_c = n01(np.sin((u + .78 * v) / 61.0) + .49 * np.cos((u - v) / 93.0))
    emerald = bead * np.clip((cloud_a - .38) * 1.62, 0, 1)
    cyan = bead * np.clip((cloud_b - .56) * 2.18, 0, 1)
    cobalt = bead * np.clip((cloud_c - .66) * 2.94, 0, 1)
    shadow_bead = bead * np.clip((.47 - cloud_a) * 1.83, 0, 1)

    # Dark stiffeners are finite, branching cuticular seams.  A broad field
    # chooses their course; 8-18px attached beads make the anatomy articulate
    # instead of resolving as a second all-over vein grid.
    seam_a = np.clip(1 - np.abs(cloud_a - cloud_b - .055) / .032, 0, 1)
    seam_b = np.clip(1 - np.abs(cloud_b - cloud_c + .085) / .030, 0, 1)
    seam_gate = np.clip((cloud_c - .29) * 1.55, 0, 1)
    seam = np.maximum(seam_a * seam_gate, seam_b * np.clip((.76 - cloud_a) * 1.35, 0, 1))
    seam_core = np.clip(seam * 2.4 - .68, 0, 1)
    articulation = bead_rim * np.clip(seam * 1.65, 0, 1)

    # Pruinose wax platelets live on the lit shoulders of connected clouds.
    # Their two crossed orientations prevent a generic speckle/grain read.
    wax_a = np.clip((np.cos((x + .24 * y) * np.pi / 4.9) - .66) * 2.95, 0, 1)
    wax_b = np.clip((np.cos((y - .31 * x) * np.pi / 6.7) - .72) * 3.55, 0, 1)
    wax = np.maximum(wax_a * np.clip((cloud_b - .57) * 2.3, 0, 1),
                     wax_b * np.clip((cloud_c - .62) * 2.7, 0, 1))
    wax *= bead + bead_rim * .45

    # Quasi-ordered vertex flashes appear only where cloud boundaries meet a
    # seam shoulder; they are attached optical events, not free confetti.
    boundary = np.clip(1 - np.abs(cloud_a - cloud_b) / .16, 0, 1)
    vertex = bead_core * boundary * np.clip(articulation * 2.0 + seam * .7, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        bead, bead_core, bead_rim, interstice, cloud_a, cloud_b, cloud_c,
        emerald, cyan, cobalt, shadow_bead, seam, seam_core, articulation,
        wax, vertex,
    ))


def paint_dragonfly_emerald_i1(paint, shape, mask, seed, pm, bb):
    (bead, bead_core, bead_rim, interstice, cloud_a, cloud_b, cloud_c,
     emerald, cyan, cobalt, shadow_bead, seam, seam_core, articulation,
     wax, vertex) = _surface(seed + 46291)

    deep = np.array([.008, .022, .025], np.float32)
    green = np.array([.015, .58, .35], np.float32)
    jade = np.array([.03, .82, .54], np.float32)
    aqua = np.array([.04, .68, .78], np.float32)
    blue = np.array([.04, .22, .67], np.float32)
    violet = np.array([.24, .07, .39], np.float32)
    chrome = np.array([.72, .89, .84], np.float32)

    col = deep[None, None, :] * (.43 + .12 * cloud_c[..., None])
    col += green[None, None, :] * (.20 + .32 * cloud_a[..., None])
    col += aqua[None, None, :] * (.045 + .18 * cloud_b[..., None])
    col += violet[None, None, :] * (.025 + .105 * cloud_c[..., None])
    col += blue[None, None, :] * np.clip((cloud_c - .47) * .20, 0, 1)[..., None]
    col += np.array([.67, .29, .035], np.float32)[None, None, :] * np.clip((cloud_a - cloud_b - .26) * .24, 0, 1)[..., None]
    col += emerald[..., None] * green[None, None, :] * .48
    col += cyan[..., None] * aqua[None, None, :] * .43
    col += cobalt[..., None] * blue[None, None, :] * .38
    col += bead_rim[..., None] * aqua[None, None, :] * np.clip((cloud_b - .38) * .31, 0, 1)[..., None]
    col += bead_core[..., None] * violet[None, None, :] * (.035 + .095 * cloud_c[..., None])
    col *= 1 - shadow_bead[..., None] * .22
    col *= 1 - seam[..., None] * .31
    col += seam[..., None] * np.array([.015, .10, .075], np.float32)[None, None, :] * .19
    col += articulation[..., None] * np.array([.12, .52, .39], np.float32) * .38
    col += articulation[..., None] * np.array([.70, .34, .055], np.float32) * np.clip((cloud_c - .61) * .42, 0, 1)[..., None]
    col += wax[..., None] * chrome[None, None, :] * (.24 + .20 * cloud_c[..., None])
    col += vertex[..., None] * np.array([.72, 1.0, .90], np.float32) * .76
    col *= 1 - seam_core[..., None] * .24
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_dragonfly_emerald_i1(shape, seed, sm, base_m, base_r):
    (bead, bead_core, bead_rim, interstice, cloud_a, cloud_b, cloud_c,
     emerald, cyan, cobalt, shadow_bead, seam, seam_core, articulation,
     wax, vertex) = _surface(seed + 46291)
    # Eleven differently weighted, pattern-bound contributors per channel give
    # adjacent nanospheres genuinely different materials rather than a tinted
    # copy of the paint.  Melanin seams suppress stray reflection; wax and
    # vertex joints carry the hard flashes.
    m = 32 + 182 * (.29 * emerald + .21 * bead_core + .18 * articulation +
                    .14 * cloud_a + .10 * seam + .08 * wax)
    r = 25 + 196 * (.27 * shadow_bead + .22 * interstice + .18 * cloud_b +
                    .14 * bead_rim + .11 * seam_core + .08 * cobalt)
    cc = 24 + 203 * (.27 * wax + .22 * vertex + .17 * cyan + .14 * cloud_c +
                     .11 * cobalt + .09 * (1 - seam))
    m += vertex * 17 - seam_core * 24
    r += seam * 18 - wax * 23
    cc += wax * 26 + vertex * 18 - seam_core * 16
    m = np.mean(m) + 26.0 / max(float(np.std(m)), 1e-5) * (m - np.mean(m))
    r = np.mean(r) + 24.0 / max(float(np.std(r)), 1e-5) * (r - np.mean(r))
    cc = np.mean(cc) + 27.0 / max(float(np.std(cc)), 1e-5) * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 249), shape),
            _resize(np.clip(r, 6, 248), shape),
            _resize(np.clip(cc, 0, 255), shape))
