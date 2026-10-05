"""Glasswing Lattice I2 — clear panes, doubled veins and anti-reflective pillars.

SPB-105 / Finish Identity Law / owner 2026-09-01: Glasswing was named among
cards with nearly identical spec maps.  I1 buried its real anatomy beneath broad
f0/f1/f2 haze.  I2 follows Greta oto research: a thin exposed membrane, sparse
piliform scales, a lower nipple layer and irregular wax nanopillars that create
omnidirectional anti-reflection (Siddique et al. 2015; Pomerantz et al. 2021).
Every material state is bound to a visible pane, vein, pillar, bristle or dew
feature.  No full-frame wave or palette-swap carrier remains.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

GEN = 768


def _hw(shape): return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape)
    a = np.asarray(a, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, col):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .96, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(col, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    dx, dy, d1, fid, d2 = _cells(
        GEN, 11.25, int(seed) % 7919 + 38461, jit=.96, taps=13, need2=True,
    )
    gap = d2 - d1
    state = n01(np.sin(fid * 1.913 + .4) + .49 * np.cos(fid * .611 - 1.3))
    metal_state = np.mod(np.sin(fid * 19.331 + .71) * 31415.9265, 1.0)
    rough_state = np.mod(np.sin(fid * 43.117 - .39) * 27182.8183, 1.0)
    coat_state = np.mod(np.sin(fid * 71.713 + 1.17) * 16180.3399, 1.0)

    # Three separately readable 8-18px native vein layers surround 20-32px
    # clear panes.  They are materially different rather than one fuzzy edge.
    vein_core = np.clip(1 - gap / .62, 0, 1) ** 1.18
    vein_inner = np.clip(1 - np.abs(gap - .88) / .34, 0, 1)
    vein_outer = np.clip(1 - np.abs(gap - 1.52) / .42, 0, 1)
    pane = np.clip((gap - .38) / 1.92, 0, 1)
    pane_core = np.clip((gap - 1.10) / 1.60, 0, 1)

    # Regular chitin nipples plus irregular wax pillars, restricted to panes.
    pdx, pdy, pd1, pfid, pd2 = _cells(
        GEN, 3.65, int(seed) % 6151 + 40127, jit=.96, taps=9, need2=True,
    )
    pstate = n01(np.sin(pfid * 1.377 + .2) + .55 * np.cos(pfid * .477 - .9))
    stretch_x = .92 + .28 * pstate
    stretch_y = 1.16 - .24 * pstate
    pr = np.sqrt((pdx / stretch_x) ** 2 + (pdy / stretch_y) ** 2)
    nipple = np.clip(1 - pr / 1.30, 0, 1) ** 1.2 * pane
    pillar_radius = 1.20 + .48 * pstate
    pillar = np.clip(1 - np.abs(pr - pillar_radius) / .38, 0, 1) * pane
    pedestal = np.clip(1 - pr / 2.05, 0, 1) * pane * (1 - nipple * .65)

    # Sparse 24-31px piliform scales are oriented per pane and anchored to its
    # centre.  No line crosses unrelated panes and no broad bristle wave exists.
    theta = state * np.pi * 1.7 - .35
    bu = dx * np.cos(theta) + dy * np.sin(theta)
    bv = -dx * np.sin(theta) + dy * np.cos(theta)
    bristle_gate = np.clip((state - .76) * 5.2, 0, 1)
    bristle = np.clip((.38 - np.abs(bv)) / .38, 0, 1)
    bristle *= np.clip((5.2 - np.abs(bu)) / 1.05, 0, 1) * bristle_gate * pane
    fork = np.maximum(
        np.clip((.34 - np.abs(bv - .25 * (bu - 3.4))) / .34, 0, 1),
        np.clip((.34 - np.abs(bv + .25 * (bu - 3.4))) / .34, 0, 1),
    )
    fork *= np.clip((bu - 2.4) / .8, 0, 1) * np.clip((5.1 - bu) / .8, 0, 1) * bristle_gate * pane

    # Rare condensate rings are cell-centred and therefore part of the lattice.
    dew_gate = np.clip((coat_state - .84) * 7.0, 0, 1)
    dew = np.clip(1 - np.abs(d1 - 2.05) / .46, 0, 1) * dew_gate * pane
    dew_core = np.clip(1 - d1 / 1.10, 0, 1) * dew_gate * pane
    return tuple(np.asarray(a, np.float32) for a in (
        vein_core, vein_inner, vein_outer, pane, pane_core, nipple, pillar,
        pedestal, bristle, fork, dew, dew_core, state, pstate, metal_state,
        rough_state, coat_state,
    ))


def paint_butterfly_glasswing_i2(paint, shape, mask, seed, pm, bb):
    vc, vi, vo, pane, pc, nipple, pillar, pedestal, bristle, fork, dew, dew_core, state, pstate, metal_state, rough_state, coat_state = _surface(seed + 41777)
    carbon = np.array([.008, .012, .018], np.float32)
    smoke = np.array([.070, .105, .118], np.float32)
    glass = np.array([.31, .43, .46], np.float32)
    cyan = np.array([.055, .62, .74], np.float32)
    violet = np.array([.32, .13, .48], np.float32)
    silver = np.array([.78, .87, .91], np.float32)
    amber = np.array([.62, .27, .065], np.float32)
    pearl = np.array([.94, .98, 1.00], np.float32)

    pane_tint = glass[None, None, :] * (.52 + .18 * coat_state[..., None])
    pane_tint += cyan[None, None, :] * (.10 + .12 * (1 - state[..., None]))
    pane_tint += violet[None, None, :] * (.035 + .075 * state[..., None])
    col = carbon[None, None, :] + pane[..., None] * pane_tint
    col += pc[..., None] * smoke[None, None, :] * (.18 + .17 * rough_state[..., None])
    col += vo[..., None] * cyan[None, None, :] * (.23 + .22 * coat_state[..., None])
    col += vi[..., None] * np.array([.11, .28, .34], np.float32) * (.40 + .26 * metal_state[..., None])
    col += vc[..., None] * silver[None, None, :] * (.58 + .29 * metal_state[..., None])
    col += nipple[..., None] * np.array([.10, .16, .18], np.float32) * (.24 + .18 * pstate[..., None])
    col += pillar[..., None] * cyan[None, None, :] * (.10 + .14 * pstate[..., None])
    col += pedestal[..., None] * np.array([.055, .11, .13], np.float32) * .18
    col += bristle[..., None] * amber[None, None, :] * (.44 + .30 * rough_state[..., None])
    col += fork[..., None] * silver[None, None, :] * .46
    col += dew[..., None] * cyan[None, None, :] * (.36 + .24 * coat_state[..., None])
    col += dew_core[..., None] * pearl[None, None, :] * .92
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_butterfly_glasswing_i2(shape, seed, sm, base_m, base_r):
    vc, vi, vo, pane, pc, nipple, pillar, pedestal, bristle, fork, dew, dew_core, state, pstate, metal_state, rough_state, coat_state = _surface(seed + 41777)
    # Metallic traces the silver vein skeleton/bristles; roughness traces the
    # wax/nipple anti-reflective relief; clearcoat traces clear pane faces/dew.
    # P2 population split.  P1 gave every pane both rough pillar relief and a
    # full blue clearcoat face, collapsing the combined map to one silhouette.
    # Independent per-pane gates retain anatomy while separating ownership.
    rough_gate = np.clip((rough_state - .34) * 1.90, 0, 1)
    coat_gate = np.clip((coat_state - .38) * 1.85, 0, 1)
    m = 8 + vc * (176 + 58 * metal_state) + vi * (64 + 36 * state)
    m += bristle * (116 + 52 * metal_state) + fork * 82 + dew * 24 - pc * 6
    r = 14 + nipple * rough_gate * (132 + 56 * rough_state)
    r += pillar * rough_gate * (146 + 52 * pstate)
    r += pedestal * (24 + 32 * rough_gate) + bristle * 38 + vo * 16 - dew_core * 14
    cc = 10 + pc * coat_gate * (128 + 72 * coat_state)
    cc += pane * (12 + 18 * coat_state) + dew * (92 + 38 * coat_gate)
    cc += dew_core * 146 + fork * 28 - vc * 18 - pillar * 10
    return (
        np.clip(_resize(np.clip(m * sm, 6, 232), shape), 6, 232),
        np.clip(_resize(np.clip(r, 10, 228), shape), 10, 228),
        np.clip(_resize(np.clip(cc, 6, 236), shape), 6, 236),
    )
