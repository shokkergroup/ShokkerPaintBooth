"""Glasswing Lattice I1 — Greta oto anti-reflective membrane glass.

SPB-105 / owner 2026-09-01: original 8-32px native carrier with pattern-bound
M/R/Cc, no macro panes or random-noise rescue.  Greta oto research identifies
thin exposed membrane, irregular wax nanopillars over chitin nipples, sparse
piliform scales, low haze and omnidirectional anti-reflection.  Those structures
become fine membrane cells, double vein rims, pillar fields and vein-bound dew.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

GEN = 1024


def _hw(shape): return shape[:2] if len(shape) > 2 else shape


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


def _surface(seed):
    y, x = coords(GEN)
    dx, dy, d1, fid, d2 = _cells(GEN, 15.2, int(seed) % 7919 + 19457,
                                  jit=.96, taps=13, need2=True)
    gap = d2 - d1
    vein = np.clip(1 - gap / 1.03, 0, 1) ** 1.28
    outer = np.clip(1 - np.abs(gap - 1.68) / .64, 0, 1)
    face = np.clip((gap - .54) / 2.55, 0, 1)
    centre = np.clip(1 - d1 / 3.45, 0, 1)

    cx, cy = x - dx, y - dy
    f0 = n01(np.sin((cx + .28 * cy) / 67.0) + .59 * np.cos((cx - .72 * cy) / 121.0))
    f1 = n01(np.cos((cx - .43 * cy) / 83.0) + .53 * np.sin((cx + .61 * cy) / 149.0))
    f2 = n01(np.sin((cx + .76 * cy) / 49.0) + .47 * np.cos((cx - .19 * cy) / 167.0))
    state = n01(np.sin(fid * 1.913 + .4) + .49 * np.cos(fid * .611 - 1.3))

    # A second 8-12px native cellular system models the quasi-random two-layer
    # wax-pillar/chitin-nipple anti-reflective surface inside each membrane cell.
    pdx, pdy, pd1, pfid, pd2 = _cells(GEN, 5.15, int(seed) % 6151 + 22571,
                                      jit=.99, taps=9, need2=True)
    pr = np.sqrt((pdx / (1.0 + .18 * f0)) ** 2 + (pdy / (1.0 - .12 * f1)) ** 2)
    nipple = np.clip(1 - pr / 1.82, 0, 1) ** 1.25 * face
    pillar = np.clip(1 - np.abs(pr - (1.76 + .38 * n01(np.sin(pfid * 1.37)))) / .54, 0, 1) * face

    # Fine curved piliform-scale traces run through several membrane cells;
    # pearl condensates are anchored at selected cell centres, never scattered.
    bristle_phase = x + .26 * y + 4.1 * np.sin(y / 73.0) + 2.0 * np.sin((x + y) / 109.0)
    bristle = np.clip((np.cos(bristle_phase * np.pi / 25.0) - .91) * 10.5, 0, 1)
    bristle *= np.clip((np.cos((x - .18 * y) / 89.0) + .35) * 1.1, 0, 1)
    dew_gate = np.clip((state - .70) * 4.3, 0, 1)
    dew = np.clip(1 - np.abs(d1 - 2.15) / .72, 0, 1) * dew_gate
    dew_core = np.clip(1 - d1 / 1.18, 0, 1) * dew_gate
    return tuple(np.asarray(a, np.float32) for a in (
        vein, outer, face, centre, nipple, pillar, bristle, dew, dew_core,
        state, f0, f1, f2
    ))


def paint_butterfly_glasswing_i1(paint, shape, mask, seed, pm, bb):
    vein, outer, face, centre, nipple, pillar, bristle, dew, dew_core, state, f0, f1, f2 = _surface(seed + 19661)
    smoke = np.array([.055, .075, .090], np.float32)
    glass = np.array([.24, .36, .40], np.float32)
    cyan = np.array([.10, .68, .79], np.float32)
    violet = np.array([.37, .18, .55], np.float32)
    silver = np.array([.70, .79, .84], np.float32)
    pearl = np.array([.91, .97, 1.00], np.float32)
    amber = np.array([.68, .31, .09], np.float32)

    tint = cyan[None, None, :] * (1 - f1[..., None]) + violet[None, None, :] * f1[..., None]
    clarity = np.clip((state - .24) * 1.55, 0, 1)
    warm = np.clip((f0 - .57) * 2.75, 0, 1) * np.clip((state - .34) * 2.2, 0, 1)
    membrane = (glass[None, None, :] * (.38 + .24 * f0[..., None]) +
                tint * (.12 + .17 * f2[..., None]) +
                pearl[None, None, :] * (.035 + .105 * clarity[..., None]) +
                amber[None, None, :] * (.08 * warm[..., None]))
    col = smoke[None, None, :] * (1 - face[..., None] * .48) + face[..., None] * membrane
    col += outer[..., None] * cyan[None, None, :] * (.18 + .27 * f0[..., None])
    col += vein[..., None] * silver[None, None, :] * (.40 + .34 * state[..., None])
    col += centre[..., None] * violet[None, None, :] * (.05 + .12 * f2[..., None])
    col += nipple[..., None] * np.array([.10, .21, .24], np.float32) * (.18 + .24 * f1[..., None])
    col += pillar[..., None] * np.array([.12, .30, .35], np.float32) * (.15 + .21 * f0[..., None])
    col += bristle[..., None] * amber[None, None, :] * (.13 + .22 * f2[..., None])
    col += dew[..., None] * cyan[None, None, :] * (.30 + .23 * f1[..., None])
    col += dew_core[..., None] * pearl[None, None, :] * (.62 + .28 * f2[..., None])
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_butterfly_glasswing_i1(shape, seed, sm, base_m, base_r):
    vein, outer, face, centre, nipple, pillar, bristle, dew, dew_core, state, f0, f1, f2 = _surface(seed + 19661)
    m_mix = (.18 * f0 + .15 * vein + .13 * dew + .12 * state + .10 * outer +
             .09 * bristle + .08 * pillar + .06 * centre + .05 * dew_core +
             .04 * nipple)
    r_mix = (.19 * f1 + .17 * nipple + .14 * pillar + .12 * (1 - face) +
             .10 * state + .09 * bristle + .07 * outer + .05 * dew +
             .04 * vein + .03 * centre)
    cc_mix = (.18 * f2 + .17 * face + .15 * dew_core + .12 * pillar +
              .10 * outer + .09 * centre + .07 * dew + .05 * nipple +
              .04 * vein + .03 * (1 - state))
    m = 7 + 237 * m_mix + vein * 18 - face * 10
    r = 12 + 231 * r_mix + nipple * 14 - dew_core * 22
    cc = 3 + 251 * cc_mix + dew_core * 24 - bristle * 12
    m = np.mean(m) + 1.38 * (m - np.mean(m))
    r = np.mean(r) + 1.38 * (r - np.mean(r))
    cc = np.mean(cc) + 1.38 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 7, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
