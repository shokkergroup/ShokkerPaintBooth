"""Peacock Scale Furnace I2 — dense roof-scale furnace rosettes.

SPB-105 / owner 2026-09-01, Finish Identity correction.  I1 clipped its
otherwise useful rosettes into broad diagonal corridors, creating a strong
paint-silhouette collision with Tiger Beetle and reusing the category's macro
spec waves.  I2 is a new carrier: complete jittered 8–32px peacock-eye
territories made from six scale-ring materials, joined by furnace seams over a
separate 8–12px roof-scale lattice.  Every M/R/Cc transition follows anatomy.
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
    a = np.clip(mask * pm * .96, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(col, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    # P4 identity rewrite.  Random Voronoi territories made P1-P3 read as a
    # bubble carpet even after coarse gating.  These 12x11 generator-pixel
    # territories become 32x29 native pixels and are placed by a hand-authored
    # seven-row peacock-fan grammar.  The fan is a composition of legal fine
    # primitives; there is no macro mask and no palette-only identity.
    pitch_x, pitch_y = 12.0, 11.0
    row = np.floor(y / pitch_y)
    stagger = np.mod(row, 2.0) * (pitch_x * .5)
    col = np.floor((x + stagger) / pitch_x)
    cx = (col + .5) * pitch_x - stagger
    cy = (row + .5) * pitch_y
    dx, dy = x - cx, y - cy
    fid = row * 1031.0 + col * 17.0
    state = n01(np.sin(fid * 1.673 + .8) + .57 * np.cos(fid * .523 - 1.2))
    metal_state = np.mod(np.sin(fid * 17.913 + .31) * 31415.9265, 1.0)
    rough_state = np.mod(np.sin(fid * 41.177 - .73) * 27182.8183, 1.0)
    coat_state = np.mod(np.sin(fid * 67.731 + 1.17) * 16180.3399, 1.0)
    stretch_x = .94 + .12 * n01(np.sin(fid * .83))
    stretch_y = 1.08 - .10 * n01(np.cos(fid * .71))
    rr = np.sqrt((dx / stretch_x) ** 2 + (dy / stretch_y) ** 2)
    th = np.arctan2(dy, dx)

    lr, lc = np.mod(row, 7.0), np.mod(col, 7.0)
    crown = ((lr == 0) & ((lc == 0) | (lc == 3) | (lc == 6)))
    shoulder = ((lr == 1) & ((lc == 1) | (lc == 3) | (lc == 5)))
    inner = ((lr == 2) & ((lc == 2) | (lc == 3) | (lc == 4)))
    throat = ((lr == 3) & ((lc == 2) | (lc == 3) | (lc == 4)))
    collar = ((lr == 4) & ((lc == 2) | (lc == 3) | (lc == 4)))
    stem = ((lr >= 5) & (lc == 3))
    gate = (crown | shoulder | inner | throat | collar | stem).astype(np.float32)
    # Alternate furnace blocks reverse the internal spectral order without
    # changing the fan silhouette.
    block_flip = np.mod(np.floor(row / 7.0) + np.floor(col / 7.0), 2.0)

    # Complete but naturally broken scale-cell rings.  Each eyelet remains at
    # or below 32 native pixels and earns a named material tier.
    break0 = .40 + .60 * np.clip((np.cos(th * 3.0 + state * 5.1) + .30) * 1.65, 0, 1)
    break1 = .35 + .65 * np.clip((np.sin(th * 5.0 - state * 4.2) + .20) * 1.72, 0, 1)
    copper = np.clip(1 - np.abs(rr - (5.05 - .18 * block_flip)) / .72, 0, 1) * break0 * gate
    gold = np.clip(1 - np.abs(rr - (4.22 + .15 * block_flip)) / .66, 0, 1) * break1 * gate
    emerald = np.clip(1 - np.abs(rr - 3.42) / .70, 0, 1) * (.45 + .55 * np.maximum(break0, break1)) * gate
    blue = np.clip(1 - np.abs(rr - (2.60 - .14 * block_flip)) / .70, 0, 1) * gate
    black_disc = np.clip(1 - np.abs(rr - 1.70) / .58, 0, 1) * gate
    pearl = np.clip(1 - rr / .86, 0, 1) ** 1.35 * np.clip((state - .18) * 2.25, 0, 1) * gate
    spoke = np.clip((np.cos(th * 7.0 + state * 4.6) - .58) * 2.45, 0, 1)
    spoke *= np.clip((5.55 - rr) / 4.0, 0, 1) * gate

    # 8-12px crossed roof-scale ribs live inside the eyelets.  The refractory
    # voids stay calm so the seven-row feather fans survive picker reduction.
    scale_state = n01(np.sin(fid * 1.917) + .51 * np.cos(fid * .687 + 1.4))
    q0 = np.abs(np.mod(x + y + scale_state * 1.7, 3.5) - 1.75)
    q1 = np.abs(np.mod(x - y + scale_state * 1.3, 4.1) - 2.05)
    scale_ridge = np.clip((.30 - q0) / .30, 0, 1) * gate
    scale_cross = np.clip((.28 - q1) / .28, 0, 1) * gate
    scale_edge = np.maximum(scale_ridge, scale_cross)
    scale_face = np.clip(gate - scale_edge * .55, 0, 1)
    trabecula = np.clip(scale_ridge * scale_cross * 1.45, 0, 1)

    seam = np.clip(1 - np.abs(rr - 5.48) / .30, 0, 1) * gate
    seam *= np.clip((np.cos(th * 5.0 + state * 3.0) + .18) * 1.58, 0, 1)
    scar = np.clip(1 - np.abs(rr - (4.10 + .44 * np.sin(th * 2 + state * 3))) / .36, 0, 1)
    scar *= np.clip((np.cos(th * 4.0 - metal_state * 4.0) + .22) * 1.55, 0, 1) * gate
    abrasion = np.maximum(scar, seam * .72)
    return tuple(np.asarray(a, np.float32) for a in (
        copper, gold, emerald, blue, black_disc, pearl, spoke, abrasion, seam,
        scale_edge, scale_face, scale_ridge, scale_cross, trabecula,
        state, scale_state, metal_state, rough_state, coat_state,
    ))


def paint_butterfly_peacock_i2(paint, shape, mask, seed, pm, bb):
    copper, gold, emerald, blue, black_disc, pearl, spoke, abrasion, seam, scale_edge, scale_face, scale_ridge, scale_cross, trabecula, state, scale_state, metal_state, rough_state, coat_state = _surface(seed + 36187)
    ultra = np.array([.001, .001, .002], np.float32)
    indigo = np.array([.012, .022, .24], np.float32)
    cobalt = np.array([.018, .23, .84], np.float32)
    green = np.array([.010, .66, .28], np.float32)
    bronze = np.array([.62, .12, .018], np.float32)
    old_gold = np.array([.98, .57, .045], np.float32)
    white = np.array([.94, .97, 1.00], np.float32)

    col = ultra[None, None, :] + scale_face[..., None] * indigo[None, None, :] * (.23 + .18 * scale_state[..., None])
    col += copper[..., None] * bronze[None, None, :] * (.60 + .22 * metal_state[..., None])
    col += gold[..., None] * old_gold[None, None, :] * (.60 + .19 * coat_state[..., None])
    col += emerald[..., None] * green[None, None, :] * (.56 + .20 * rough_state[..., None])
    col += blue[..., None] * cobalt[None, None, :] * (.64 + .18 * state[..., None])
    col *= 1 - black_disc[..., None] * .96
    col += spoke[..., None] * np.array([.24, .045, .32], np.float32)
    col += abrasion[..., None] * old_gold[None, None, :] * (.24 + .34 * scale_state[..., None])
    col += seam[..., None] * np.array([.16, .055, .018], np.float32)
    col += scale_edge[..., None] * np.array([.028, .050, .070], np.float32)
    col += scale_ridge[..., None] * np.array([.045, .12, .30], np.float32) * (.21 + .30 * coat_state[..., None])
    col += trabecula[..., None] * np.array([.13, .035, .018], np.float32)
    col += pearl[..., None] * white[None, None, :] * .96
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_butterfly_peacock_i2(shape, seed, sm, base_m, base_r):
    copper, gold, emerald, blue, black_disc, pearl, spoke, abrasion, seam, scale_edge, scale_face, scale_ridge, scale_cross, trabecula, state, scale_state, metal_state, rough_state, coat_state = _surface(seed + 36187)

    m = 105 + copper * (88 + 42 * metal_state) + gold * (116 + 36 * state)
    m += scale_ridge * (62 + 38 * scale_state) + abrasion * 48 - black_disc * 72

    r = 114 + black_disc * (118 + 34 * rough_state) + spoke * (88 + 36 * state)
    r += scale_cross * (68 + 32 * scale_state) + trabecula * 45 - gold * 48 - pearl * 38

    cc = 101 + blue * (104 + 38 * coat_state) + pearl * (138 + 42 * state)
    cc += emerald * (62 + 34 * scale_state) + scale_edge * 54 + seam * 38 - black_disc * 58
    return (
        _resize(np.clip(m * sm, 0, 250), shape),
        _resize(np.clip(r, 4, 248), shape),
        _resize(np.clip(cc, 0, 255), shape),
    )
