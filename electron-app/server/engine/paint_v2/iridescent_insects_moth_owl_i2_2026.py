"""Owl Moth Sable I2 — braided broken ocelli over order-disorder sable nap.

SPB-105 / Finish Identity Law / owner 2026-09-01: Owl Moth was explicitly
identified as sharing the generic spec carrier.  I1 hid its ocelli beneath broad
f0/f1/f2 haze.  I2 uses deliberate crossing braids of incomplete 20-31px Caligo
ocelli over 8-12px ordered ridges and disordered crossribs.  Melanin discs,
bronze/gold rings, pearl pupil scars, nap, bristles and abrasion own separate
material states; no giant eyes, random target field or screen-space wave.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

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
    px, py = 10.8, 8.8
    row = np.floor(y / py)
    stagger = np.mod(row, 2.0) * px * .5
    col = np.floor((x + stagger) / px)
    cx = (col + .5) * px - stagger
    cy = (row + .5) * py
    u, v = x - cx, y - cy
    fid = row * 1069.0 + col * 31.0 + (int(seed) % 1871)
    state = n01(np.sin(fid * 1.673 + .2) + .63 * np.cos(fid * .541 - 1.0))
    metal_state = np.mod(np.sin(fid * 17.731 + .61) * 31415.9265, 1.0)
    rough_state = np.mod(np.sin(fid * 39.337 - .43) * 27182.8183, 1.0)
    coat_state = np.mod(np.sin(fid * 67.117 + 1.21) * 16180.3399, 1.0)

    # P3: sparse paired ocelli.  P1 scattered; P2 became bead lattice.  Each
    # three-row/six-column repeat now contains one unmistakable two-eye pair,
    # staggered between bands so the whole-car field stays borderless.
    band = np.mod(row, 3.0) == 1.0
    pair_phase = np.mod(col + np.floor(row / 3.0) * 3.0, 6.0)
    active = (band & ((pair_phase == 1.0) | (pair_phase == 2.0))).astype(np.float32)

    angle = -.62 + 1.24 * state
    ca, sa = np.cos(angle), np.sin(angle)
    rx, ry = u * ca + v * sa, -u * sa + v * ca
    ax = 4.72 + .36 * state
    ay = 3.42 + .26 * (1 - state)
    er = np.sqrt((rx / ax) ** 2 + (ry / ay) ** 2)
    th = np.arctan2(ry / ay, rx / ax)
    arc0 = .28 + .72 * np.clip((np.cos(th - state * 4.8) + .36) * 1.42, 0, 1)
    arc1 = .24 + .76 * np.clip((np.sin(th * 2.0 + metal_state * 5.1) + .30) * 1.48, 0, 1)
    bronze = np.clip(1 - np.abs(er - .88) / .19, 0, 1) * arc0 * active
    gold = np.clip(1 - np.abs(er - .64) / .18, 0, 1) * arc1 * active
    oxblood = np.clip(1 - np.abs(er - .46) / .16, 0, 1) * np.maximum(arc0, arc1) * active
    black_disc = np.clip(1 - er / .48, 0, 1) * active
    pupil = np.clip(1 - np.sqrt(((rx - .58 * (state - .5)) / 1.25) ** 2 +
                                ((ry + .42 * (state - .5)) / .94) ** 2), 0, 1) * active

    # Every territory is a sable roof scale; only selected paired scales receive
    # the bright ocellus rings.  This gives P4 a complete moth surface instead
    # of P3's eyes floating over an underbuilt dark field.
    roof = np.clip((.96 - er) / .22, 0, 1)
    ridge = np.clip((np.cos((rx + .16 * ry) * np.pi / 3.25 + state * 1.7) - .54) * 2.25, 0, 1) * roof
    cross = np.clip((np.cos((ry - .18 * rx) * np.pi / 2.75 + rough_state * 1.9) - .60) * 2.50, 0, 1) * roof
    window = np.clip(ridge * cross * 1.55, 0, 1)

    # A short horizontal brow/pair link terminates within each 31px territory.
    thread = np.clip((.44 - np.abs(v + .18)) / .44, 0, 1) * active
    thread *= np.clip((5.05 - np.abs(u)) / .72, 0, 1)

    # Calm sable substrate: two fine woven mark types, never a random grain.
    q0 = np.abs(np.mod(x - .43 * y + state * .7, 3.7) - 1.85)
    q1 = np.abs(np.mod(x + .21 * y + rough_state * .5, 4.3) - 2.15)
    nap_ridge = np.clip((.25 - q0) / .25, 0, 1)
    nap_cross = np.clip((.22 - q1) / .22, 0, 1)
    nap_knot = np.clip(nap_ridge * nap_cross * 1.65, 0, 1)

    # Pane-local long bristle and abrasion: attached to ocelli, not global flow.
    bristle = np.clip((.34 - np.abs(ry - .34 * rx)) / .34, 0, 1)
    bristle *= np.clip((5.0 - np.abs(rx)) / .9, 0, 1) * active
    abrasion = np.clip(1 - np.abs(er - (.74 + .06 * np.sin(th * 3.0))) / .075, 0, 1)
    abrasion *= np.clip((np.cos(th * 5.0 + coat_state * 4.0) + .30) * 1.45, 0, 1) * active
    return tuple(np.asarray(a, np.float32) for a in (
        bronze, gold, oxblood, black_disc, pupil, roof, ridge, cross, window,
        nap_ridge, nap_cross, nap_knot, thread, bristle, abrasion, state, metal_state,
        rough_state, coat_state,
    ))


def paint_moth_owl_i2(paint, shape, mask, seed, pm, bb):
    bronze, gold, oxblood, black_disc, pupil, roof, ridge, cross, window, nap_ridge, nap_cross, nap_knot, thread, bristle, abrasion, state, metal_state, rough_state, coat_state = _surface(seed + 44939)
    sable = np.array([.004, .003, .006], np.float32)
    smoke = np.array([.080, .055, .066], np.float32)
    bronze_c = np.array([.60, .23, .050], np.float32)
    gold_c = np.array([.91, .55, .11], np.float32)
    oxblood_c = np.array([.31, .012, .025], np.float32)
    cool = np.array([.075, .17, .27], np.float32)
    pearl = np.array([.90, .87, .73], np.float32)

    col = sable[None, None, :] + smoke[None, None, :] * (.42 + .18 * rough_state[..., None])
    col += nap_ridge[..., None] * np.array([.052, .035, .048], np.float32) * (.50 + .24 * state[..., None])
    col += nap_cross[..., None] * cool[None, None, :] * (.15 + .14 * coat_state[..., None])
    col += nap_knot[..., None] * bronze_c[None, None, :] * .13
    col += thread[..., None] * bronze_c[None, None, :] * (.42 + .24 * metal_state[..., None])
    col += bronze[..., None] * bronze_c[None, None, :] * (.68 + .28 * metal_state[..., None])
    col += gold[..., None] * gold_c[None, None, :] * (.74 + .24 * coat_state[..., None])
    col += oxblood[..., None] * oxblood_c[None, None, :] * (.65 + .24 * state[..., None])
    col *= 1 - black_disc[..., None] * (.78 + .16 * rough_state[..., None])
    col += ridge[..., None] * cool[None, None, :] * (.26 + .24 * coat_state[..., None])
    col += window[..., None] * oxblood_c[None, None, :] * .34
    col += bristle[..., None] * pearl[None, None, :] * (.19 + .20 * metal_state[..., None])
    col += abrasion[..., None] * bronze_c[None, None, :] * (.28 + .22 * rough_state[..., None])
    col += pupil[..., None] * pearl[None, None, :] * (.82 + .16 * coat_state[..., None])
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_moth_owl_i2(shape, seed, sm, base_m, base_r):
    bronze, gold, oxblood, black_disc, pupil, roof, ridge, cross, window, nap_ridge, nap_cross, nap_knot, thread, bristle, abrasion, state, metal_state, rough_state, coat_state = _surface(seed + 44939)
    m = 10 + bronze * (112 + 56 * metal_state) + gold * (142 + 48 * state)
    m += abrasion * (72 + 46 * rough_state) + thread * (72 + 42 * metal_state)
    m += bristle * 78 + nap_knot * 34 - black_disc * 12
    r = 24 + black_disc * (146 + 62 * rough_state) + cross * (96 + 48 * rough_state)
    r += nap_ridge * (52 + 36 * state) + oxblood * 58 + window * 44 - pupil * 18
    cc = 12 + pupil * (164 + 62 * coat_state) + ridge * (112 + 46 * coat_state)
    cc += gold * 54 + window * 72 + nap_cross * 34 - black_disc * 16 - abrasion * 10
    return (
        np.clip(_resize(np.clip(m * sm, 6, 236), shape), 6, 236),
        np.clip(_resize(np.clip(r, 10, 234), shape), 10, 234),
        np.clip(_resize(np.clip(cc, 6, 240), shape), 6, 240),
    )
