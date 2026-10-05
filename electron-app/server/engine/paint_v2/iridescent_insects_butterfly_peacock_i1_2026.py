"""Peacock Scale Furnace I1 — micro-rosette thin-film scale mosaic.

SPB-105 / owner 2026-09-01: every native mark stays 8-32px and receives a
pattern-bound material role.  Inachis io blue eyespot scales are pigmentless
thin-film cover scales over black ground scales; nymphalid eyespots are mosaics
of one-colour roof tiles, while ultra-black scales deepen contrast through steep
ridges and expanded trabeculae.  These become fragmented 26px furnace rosettes,
not giant eyes and not Emperor Eyelet's braided single-cell ocelli.
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
    # 30px-native rosette territory, built from separate 9-12px scale cells.
    dx, dy, d1, fid, d2 = _cells(GEN, 17.0, int(seed) % 7919 + 24281,
                                  jit=.96, taps=13, need2=True)
    state = n01(np.sin(fid * 1.673 + .8) + .57 * np.cos(fid * .523 - 1.2))
    rr = np.sqrt((dx / (1.0 + .15 * n01(np.sin(fid)))) ** 2 +
                 (dy / (1.0 - .12 * n01(np.cos(fid * .71)))) ** 2)
    th = np.arctan2(dy, dx)
    cx, cy = x - dx, y - dy
    route = n01(np.sin((cx + .37 * cy) / 59.0) +
                .61 * np.cos((cx - .68 * cy) / 113.0) +
                .28 * np.sin((cx + .11 * cy) / 173.0))
    active = np.clip((route - .44) * 3.55, 0, 1)
    break0 = np.clip((np.cos(th * 3.0 + state * 5.1) + .28) * 1.65, 0, 1)
    break1 = np.clip((np.sin(th * 5.0 - state * 4.2) + .18) * 1.72, 0, 1)
    copper = np.clip(1 - np.abs(rr - 7.10) / 1.28, 0, 1) * (.34 + .66 * break0) * active
    gold = np.clip(1 - np.abs(rr - 5.78) / 1.02, 0, 1) * (.28 + .72 * break1) * active
    emerald = np.clip(1 - np.abs(rr - 4.48) / 1.18, 0, 1) * (.42 + .58 * np.maximum(break0, break1 * .68)) * active
    blue = np.clip(1 - np.abs(rr - 3.10) / 1.16, 0, 1) * active
    black_disc = np.clip(1 - np.abs(rr - 1.98) / .88, 0, 1) * active
    pearl = np.clip(1 - rr / 1.05, 0, 1) ** 1.35 * active * np.clip((state - .28) * 2.2, 0, 1)
    spoke = np.clip((np.cos(th * 7.0 + state * 4.6) - .60) * 2.55, 0, 1)
    spoke *= np.clip((7.8 - rr) / 5.4, 0, 1) * active

    sdx, sdy, sd1, sfid, sd2 = _cells(GEN, 4.75, int(seed) % 6151 + 27109,
                                       jit=.92, taps=9, need2=True)
    sgap = sd2 - sd1
    scale_edge = np.clip(1 - sgap / .62, 0, 1)
    scale_face = np.clip((sgap - .18) / 1.14, 0, 1)
    scale_state = n01(np.sin(sfid * 1.917) + .51 * np.cos(sfid * .687 + 1.4))
    scale_ridge = np.clip((np.cos((sdx + .19 * sdy + scale_state) * np.pi / 1.42) - .54) * 2.35, 0, 1) * scale_face
    scale_cross = np.clip((np.cos((sdy - .15 * sdx) * np.pi / 1.66) - .61) * 2.55, 0, 1) * scale_face
    trabecula = np.clip(scale_ridge * scale_cross * 1.45, 0, 1)

    f0 = n01(np.sin((cx + .39 * cy) / 71.0) + .58 * np.cos((cx - .66 * cy) / 127.0))
    f1 = n01(np.cos((cx - .28 * cy) / 89.0) + .52 * np.sin((cx + .73 * cy) / 157.0))
    f2 = n01(np.sin((cx + .81 * cy) / 47.0) + .45 * np.cos((cx - .17 * cy) / 181.0))
    ring_scar = np.clip(1 - np.abs(rr - (5.05 + .62 * np.sin(th * 2 + state * 3))) / .48, 0, 1)
    ring_scar *= np.clip((np.cos(th * 4.0 - f0 * 4.0) + .22) * 1.55, 0, 1) * active
    furnace_seam = np.clip(1 - (d2 - d1) / .84, 0, 1) * active
    furnace_seam *= np.clip((np.cos((x - .31 * y) / 14.0 + state * 3.0) + .20) * 1.55, 0, 1)
    abrasion = np.maximum(ring_scar, furnace_seam * .72)
    return tuple(np.asarray(a, np.float32) for a in (
        copper, gold, emerald, blue, black_disc, pearl, spoke, abrasion, active,
        scale_edge, scale_face, scale_ridge, scale_cross, trabecula,
        state, scale_state, f0, f1, f2
    ))


def paint_butterfly_peacock_i1(paint, shape, mask, seed, pm, bb):
    copper, gold_ring, emerald, blue, black_disc, pearl, spoke, abrasion, active, scale_edge, scale_face, scale_ridge, scale_cross, trabecula, state, scale_state, f0, f1, f2 = _surface(seed + 24317)
    ultra = np.array([.001, .001, .002], np.float32)
    indigo = np.array([.015, .025, .31], np.float32)
    cobalt = np.array([.025, .25, .82], np.float32)
    green = np.array([.015, .63, .30], np.float32)
    bronze = np.array([.58, .14, .025], np.float32)
    old_gold = np.array([.96, .55, .055], np.float32)
    white = np.array([.92, .95, 1.00], np.float32)

    col = ultra[None, None, :] + scale_face[..., None] * indigo[None, None, :] * (.31 + .28 * f1[..., None])
    corridor = green[None, None, :] * (1 - f0[..., None]) + cobalt[None, None, :] * f0[..., None]
    corridor = corridor * (1 - .28 * f2[..., None]) + bronze[None, None, :] * (.28 * f2[..., None])
    col += active[..., None] * corridor * (.22 + .24 * scale_face[..., None])
    col += copper[..., None] * bronze[None, None, :] * (.57 + .18 * state[..., None])
    col += gold_ring[..., None] * old_gold[None, None, :] * (.56 + .16 * f2[..., None])
    col += emerald[..., None] * green[None, None, :] * (.50 + .22 * f0[..., None])
    col += blue[..., None] * cobalt[None, None, :] * (.60 + .12 * f1[..., None])
    col *= 1 - black_disc[..., None] * .94
    col += spoke[..., None] * np.array([.20, .05, .29], np.float32)
    col += abrasion[..., None] * old_gold[None, None, :] * (.28 + .35 * scale_state[..., None])
    col += scale_edge[..., None] * np.array([.035, .055, .075], np.float32)
    col += scale_ridge[..., None] * np.array([.05, .12, .28], np.float32) * (.22 + .32 * f2[..., None])
    col += trabecula[..., None] * np.array([.12, .04, .025], np.float32)
    col += pearl[..., None] * white[None, None, :] * .94
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_butterfly_peacock_i1(shape, seed, sm, base_m, base_r):
    copper, gold_ring, emerald, blue, black_disc, pearl, spoke, abrasion, active, scale_edge, scale_face, scale_ridge, scale_cross, trabecula, state, scale_state, f0, f1, f2 = _surface(seed + 24317)
    m_mix = (.15 * f0 + .14 * copper + .13 * gold_ring + .12 * blue +
             .10 * emerald + .09 * abrasion + .08 * state + .07 * scale_ridge +
             .06 * pearl + .04 * scale_edge + .02 * spoke)
    r_mix = (.17 * f1 + .18 * black_disc + .12 * scale_cross + .11 * trabecula +
             .10 * (1 - state) + .09 * spoke + .08 * copper + .06 * emerald +
             .05 * scale_face + .04 * pearl)
    cc_mix = (.16 * f2 + .15 * blue + .14 * pearl + .11 * gold_ring +
              .10 * scale_face + .09 * abrasion + .08 * emerald +
              .07 * scale_edge + .06 * scale_ridge + .04 * (1 - black_disc))
    m = 8 + 238 * m_mix + gold_ring * 16 - black_disc * 28
    r = 13 + 229 * r_mix + black_disc * 22 - pearl * 18
    cc = 3 + 251 * cc_mix + pearl * 24 - trabecula * 18 + active * 7
    m = np.mean(m) + 1.35 * (m - np.mean(m))
    r = np.mean(r) + 1.35 * (r - np.mean(r))
    cc = np.mean(cc) + 1.40 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 7, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
