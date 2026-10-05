"""Owl Moth Sable I1 — broken micro-ocelli woven into absorptive scale nap.

SPB-105 / owner 2026-09-01: native 8-32px features, no giant eye decals and no
uniform dot field.  Caligo eyespot blackness combines melanin with disordered
ridges and crossribs; Io moth eyespots layer short wide white scales with long
thin bristle scales over black/yellow regions.  This whole-car translation uses
eccentric, incomplete micro-ocelli braided into sable nap, with each ring,
bristle layer, pupil scar and ordered/disordered rib family owning material.
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
    dx, dy, d1, fid, d2 = _cells(GEN, 13.1 * s, int(seed) % 7919 + 73471,
                                  jit=.99, taps=11, need2=True)
    dx, dy, d1, d2 = dx / s, dy / s, d1 / s, d2 / s
    state = n01(np.sin(fid * 1.673 + .2) + .63 * np.cos(fid * .541 - 1.0))
    f0 = n01(np.sin((x + .37 * y) / 57.0) + .59 * np.cos((x - .69 * y) / 123.0))
    f1 = n01(np.cos((x - .44 * y) / 81.0) + .52 * np.sin((x + .71 * y) / 151.0))
    f2 = n01(np.sin((x + .83 * y) / 45.0) + .47 * np.cos((x - .17 * y) / 177.0))

    angle = -.92 + 1.72 * f0 + .34 * (state - .5)
    ca, sa = np.cos(angle), np.sin(angle)
    rx, ry = dx * ca + dy * sa, -dx * sa + dy * ca
    ax = 5.05 + 1.32 * state
    ay = 3.18 + .76 * (1 - state)
    er = np.sqrt((rx / ax) ** 2 + (ry / ay) ** 2)
    theta = np.arctan2(ry / ay, rx / ax)

    # Eccentric incomplete rings: every ocellus loses a different angular
    # sector and shifts its pupil, preventing coins, dots, or perfect targets.
    arc_gate = np.clip((np.cos(theta - state * 4.7 + .85 * np.sin(fid * .31)) + .48) * 1.35, 0, 1)
    outer = np.clip(1 - np.abs(er - .86) / .27, 0, 1) * (.38 + .62 * arc_gate)
    gold_ring = np.clip(1 - np.abs(er - .59) / .235, 0, 1) * (.30 + .70 * np.roll(arc_gate, 1, axis=1))
    black_disc = np.clip(1 - er / .56, 0, 1)
    pupil = np.clip(1 - np.sqrt(((rx - .72 * (state - .5)) / 1.30) ** 2 +
                                ((ry + .48 * (state - .5)) / 1.02) ** 2), 0, 1) * black_disc

    # Two scale layers: short broad roof scales and longer bristles sweeping
    # across adjacent ocelli, as in Io moth surface layering.
    roof = np.clip(1 - (er - .72) / .28, 0, 1)
    ridge = np.clip((np.cos((rx + .14 * ry) * np.pi / 1.26 + state * 2.1) - .55) * 2.25, 0, 1) * roof
    cross = np.clip((np.cos((ry - .17 * rx) * np.pi / 1.02 + f2 * 1.7) - .61) * 2.56, 0, 1) * roof
    rib_window = np.clip(ridge * cross * 1.47, 0, 1)

    # Long sable bristles form coherent nap across, rather than around, the
    # rosettes; their broken cadence gives the black order-disorder response.
    nap_phase = x - .43 * y + 6.2 * np.sin(y / 61.0) + 3.1 * np.sin((x + y) / 109.0)
    bristle = np.clip((np.cos(nap_phase * np.pi / 10.8) - .80) * 4.7, 0, 1)
    bristle *= np.clip((np.cos((x + .19 * y) / 47.0 + f1 * 1.5) + .45) * 1.12, 0, 1)
    abrasion = np.clip(1 - np.abs(np.sin(er * 11.5 + theta * 1.7 + state * 3.2)) / .20, 0, 1) * roof
    interstice = np.clip(1 - (d2 - d1) / .91, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        outer, gold_ring, black_disc, pupil, roof, ridge, cross, rib_window,
        bristle, abrasion, interstice, state, f0, f1, f2
    ))


def paint_moth_owl_i1(paint, shape, mask, seed, pm, bb):
    outer, gold_ring, black_disc, pupil, roof, ridge, cross, window, bristle, abrasion, interstice, state, f0, f1, f2 = _surface(seed + 31169)
    sable = np.array([.008, .006, .008], np.float32)
    smoke = np.array([.095, .078, .090], np.float32)
    bronze = np.array([.52, .255, .070], np.float32)
    old_gold = np.array([.78, .50, .14], np.float32)
    pearl = np.array([.78, .76, .68], np.float32)
    cool = np.array([.13, .20, .27], np.float32)
    oxblood = np.array([.24, .025, .035], np.float32)

    under = smoke[None, None, :] * (.40 + .38 * f0[..., None]) + oxblood[None, None, :] * (.18 + .23 * f1[..., None])
    col = sable[None, None, :] * .42 + under * .58
    col += roof[..., None] * smoke[None, None, :] * (.22 + .24 * state[..., None])
    col += outer[..., None] * bronze[None, None, :] * (.67 + .38 * f0[..., None])
    col += gold_ring[..., None] * old_gold[None, None, :] * (.72 + .43 * f1[..., None])
    col *= 1 - black_disc[..., None] * .64
    col += pupil[..., None] * pearl[None, None, :] * (.69 + .30 * f2[..., None])
    col += ridge[..., None] * cool[None, None, :] * (.22 + .27 * f2[..., None])
    col += window[..., None] * oxblood[None, None, :] * (.28 + .29 * f1[..., None])
    col += bristle[..., None] * pearl[None, None, :] * (.07 + .14 * f0[..., None])
    col += abrasion[..., None] * bronze[None, None, :] * (.14 + .21 * f2[..., None])
    col *= 1 - interstice[..., None] * .37
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_moth_owl_i1(shape, seed, sm, base_m, base_r):
    outer, gold_ring, black_disc, pupil, roof, ridge, cross, window, bristle, abrasion, interstice, state, f0, f1, f2 = _surface(seed + 31169)
    m = 6 + 242 * (.15 * f0 + .14 * gold_ring + .12 * outer + .11 * abrasion +
                   .10 * state + .09 * bristle + .08 * pupil + .07 * ridge +
                   .06 * window + .05 * roof + .03 * cross)
    r = 13 + 231 * (.17 * f1 + .16 * black_disc + .13 * interstice + .11 * cross +
                    .10 * (1 - state) + .09 * window + .07 * roof + .06 * bristle +
                    .06 * abrasion + .05 * outer)
    cc = 3 + 251 * (.16 * f2 + .14 * pupil + .13 * gold_ring + .12 * ridge +
                    .10 * outer + .09 * abrasion + .08 * bristle + .07 * roof +
                    .06 * window + .05 * (1 - interstice))
    m -= black_disc * 31 + interstice * 19
    r += black_disc * 23 + interstice * 14 - pupil * 18
    cc += pupil * 29 - black_disc * 13
    m = np.mean(m) + 1.34 * (m - np.mean(m))
    r = np.mean(r) + 1.31 * (r - np.mean(r))
    cc = np.mean(cc) + 1.34 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 7, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
