"""Dragonfly Resilin I1 — corrugated Odonata vein composite and blue joints.

SPB-105 / owner 2026-09-01: 8-32px native structure, borderless and scalable.
Dragonfly wings use corrugated raised/lowered longitudinal veins, thinner cross
veins, hollow multilayer cuticle, resilin-rich joints and membrane suspension,
plus nodus/pterostigma mass-control elements.  This is not another polygonal
glasswing lattice: staggered vein rails and elastic blue joints dominate, while
the membrane carries a separately phased thin-film interference response.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

GEN = 640


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


@lru_cache(maxsize=2)
def _surface(seed):
    s = GEN / 1024.0
    y, x = coords(GEN)
    y, x = y / s, x / s
    k = float((int(seed) % 997) / 997.0)
    cdx, cdy, cd1, cfid, cd2 = _cells(GEN, 11.6 * s, int(seed) % 6151 + 88411,
                                       jit=.96, taps=11, need2=True)
    cdx, cdy, cd1, cd2 = cdx / s, cdy / s, cd1 / s, cd2 / s

    # Fine, unequal longitudinal rails follow a shallow corrugated sweep.
    warp = 10.4 * np.sin(y / 39.0 + 1.7 * np.sin(x / 139.0) + k * 4.1)
    warp += 4.8 * np.sin((x + y) / 57.0) + 2.7 * np.sin((x - 2 * y) / 113.0)
    u = x + .21 * y + warp
    v = y - .08 * x + 5.7 * np.sin(x / 61.0 - k * 2.7)
    rail_phase = u * np.pi / 10.7 + .74 * np.sin(v / 27.0) + .31 * np.sin(u / 43.0)
    rail = np.clip((np.cos(rail_phase) - .69) * 3.32, 0, 1)
    rail_core = np.clip((np.cos(rail_phase) - .89) * 9.2, 0, 1)
    branch_phase = (u + .52 * v + 8.0 * np.sin(v / 53.0)) * np.pi / 14.3
    branch_gate = np.clip((np.sin((x - y) / 97.0 + k * 3.0) + .18) * 1.12, 0, 1)
    branch = np.clip((np.cos(branch_phase) - .82) * 5.55, 0, 1) * branch_gate
    rail = np.maximum(rail, branch * .88)
    rail_core = np.maximum(rail_core, np.clip(branch * 1.35 - .28, 0, 1))
    hill = np.clip((np.sin(rail_phase * .5) + .22) * .93, 0, 1)
    valley = np.clip((-np.sin(rail_phase * .5) + .18) * .91, 0, 1)

    # Cross veins follow irregular anisotropic cell boundaries. Primary rails
    # remain the corrugation skeleton; the small biological cells eliminate
    # any textile-like manufactured crossbar cadence.
    band = np.floor(rail_phase / (2 * np.pi))
    cell_edge = np.clip(1 - (cd2 - cd1) / 1.22, 0, 1)
    cell_state = n01(np.sin(cfid * 1.713 + .5) + .54 * np.cos(cfid * .617 - 1.2))
    cross = cell_edge * (.46 + .54 * cell_state) * (1 - rail_core * .58)

    # Resilin joints occur only where cross veins meet rail shoulders.
    shoulder = np.clip(1 - np.abs(np.cos(rail_phase) - .73) / .20, 0, 1)
    joint = shoulder * np.clip(cross * 1.55, 0, 1)
    joint_core = np.clip(joint * 1.75 - .34, 0, 1)

    # Corrugated membrane and its suspension zone at vein edges.
    corrugation = n01(np.sin(u / 5.6 + .45 * np.sin(v / 43.0)) + .48 * np.cos(v / 14.9 - u / 37.0))
    f0 = n01(np.sin((x + .57 * y) / 61.0) + .58 * np.cos((x - .71 * y) / 133.0))
    f1 = n01(np.cos((x - .33 * y) / 79.0) + .51 * np.sin((x + .66 * y) / 157.0))
    f2 = n01(np.sin((x + .84 * y) / 43.0) + .46 * np.cos((x - .16 * y) / 181.0))
    suspension = np.clip(1 - np.abs(np.cos(rail_phase) - .48) / .38, 0, 1) * (1 - rail_core)

    # Pterostigma-like mass bars are rail-bound elongated segments, repeated
    # finely enough to survive arbitrary car zoning without a single macro bar.
    segment = np.clip((np.cos((v + band * 3.7) * np.pi / 31.0) - .78) * 4.5, 0, 1)
    stigma_gate = (np.mod(band.astype(np.int32) * 7 + np.floor(v / 31.0).astype(np.int32), 11) == 0).astype(np.float32)
    stigma = rail * segment * stigma_gate
    spike = joint * np.clip((np.cos((u - v) * np.pi / 5.8) - .76) * 4.3, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        rail, rail_core, hill, valley, cross, joint, joint_core, corrugation,
        suspension, stigma, spike, f0, f1, f2
    ))


def paint_dragonfly_wing_i1(paint, shape, mask, seed, pm, bb):
    rail, rail_core, hill, valley, cross, joint, joint_core, corrugation, suspension, stigma, spike, f0, f1, f2 = _surface(seed + 40123)
    smoke = np.array([.025, .045, .055], np.float32)
    membrane = np.array([.27, .43, .48], np.float32)
    silver = np.array([.67, .78, .78], np.float32)
    graphite = np.array([.018, .025, .030], np.float32)
    resilin = np.array([.045, .43, .92], np.float32)
    violet = np.array([.38, .12, .57], np.float32)
    cyan = np.array([.10, .72, .78], np.float32)
    amber = np.array([.67, .32, .055], np.float32)

    film = membrane[None, None, :] * (.39 + .31 * corrugation[..., None])
    film += cyan[None, None, :] * (.07 + .15 * f0[..., None]) + violet[None, None, :] * (.055 + .12 * f1[..., None])
    col = smoke[None, None, :] * .34 + film * .66
    col += hill[..., None] * silver[None, None, :] * (.045 + .075 * f2[..., None])
    col += valley[..., None] * violet[None, None, :] * (.035 + .08 * f0[..., None])
    col = col * (1 - rail[..., None] * .34) + rail[..., None] * silver[None, None, :] * (.17 + .19 * f1[..., None])
    col *= 1 - rail_core[..., None] * .28
    col += cross[..., None] * np.array([.34, .53, .56], np.float32) * (.58 + .35 * f2[..., None])
    col += suspension[..., None] * cyan[None, None, :] * (.11 + .19 * f0[..., None])
    col += joint[..., None] * resilin[None, None, :] * (.72 + .34 * f2[..., None])
    col += joint_core[..., None] * np.array([.42, .78, 1.0], np.float32) * .64
    col += stigma[..., None] * amber[None, None, :] * (.58 + .26 * f1[..., None])
    col += spike[..., None] * graphite[None, None, :] * .78
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_dragonfly_wing_i1(shape, seed, sm, base_m, base_r):
    rail, rail_core, hill, valley, cross, joint, joint_core, corrugation, suspension, stigma, spike, f0, f1, f2 = _surface(seed + 40123)
    m = 7 + 242 * (.17 * cross + .14 * stigma + .13 * joint_core + .12 * corrugation +
                   .10 * f0 + .09 * spike + .08 * suspension + .07 * rail +
                   .05 * hill + .03 * f2 + .02 * valley)
    r = 10 + 235 * (.17 * f1 + .16 * cross + .14 * suspension + .12 * valley +
                    .11 * corrugation + .10 * joint + .07 * stigma +
                    .06 * spike + .04 * rail_core + .03 * (1 - hill))
    cc = 4 + 250 * (.17 * f2 + .16 * suspension + .15 * joint + .13 * cross +
                    .11 * corrugation + .09 * stigma + .07 * joint_core +
                    .05 * rail + .04 * hill + .03 * (1 - valley))
    m += stigma * 25 - joint * 17
    r += cross * 17 - joint_core * 20
    cc += joint * 27 + suspension * 14
    m = np.mean(m) + 1.62 * (m - np.mean(m))
    r = np.mean(r) + 1.02 * (r - np.mean(r))
    cc = np.mean(cc) + .98 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 7, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
