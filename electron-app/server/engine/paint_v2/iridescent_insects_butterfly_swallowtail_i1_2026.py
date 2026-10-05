"""Swallowtail Prism I1 — fork-tailed Papilio scale tapestry.

SPB-105 / owner 2026-09-01: hand-authored 8-32px native detail, dense rather
than large, with many pattern-bound material states.  Papilio xuthus research
shows thin-film lower laminae, pigment-loaded ridges/crossribs, melanin-black
scales and structurally distinct blue scales; Papilio palinurus/crino adds
blue+yellow colour mixing from modulated or concave retroreflective layers.
This carrier combines those mechanisms without reusing another insect field.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

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
    # Each 1024 working pixel becomes two native pixels.  The 12x14.5 working
    # shingle therefore remains a 24x29px whole-car primitive.
    warp = 2.0 * np.sin(x / 61.0) + 1.25 * np.sin((x + y) / 117.0)
    row = np.floor((y + warp) / 12.0)
    row_shift = 2.05 * np.sin(row * 1.618) + 1.10 * np.cos(row * .713)
    stagger = np.mod(row, 2.0) * 7.25 + row_shift
    grid_x = x + stagger + 1.4 * np.sin(y / 47.0)
    u = np.mod(grid_x, 14.5) - 7.25
    v = np.mod(y + warp, 12.0) - 6.0

    col_id = np.floor(grid_x / 14.5)
    tile_state = n01(np.sin(col_id * 1.731 + row * .619) +
                     .57 * np.cos(col_id * .487 - row * 1.113))

    # Rounded, tapered overlapping body with paired swallowtail forks.
    taper = 6.15 + .72 * tile_state - .22 * (v + 1.2)
    side = np.clip((taper - np.abs(u)) / .72, 0, 1)
    top = np.clip((v + 5.75) / 1.10, 0, 1)
    bottom = np.clip((5.65 - v) / 1.15, 0, 1)
    body = side * top * bottom
    fork_sep = 2.05 + .62 * tile_state
    fork_l = np.clip(1 - np.sqrt(((u + fork_sep) / (1.28 + .32 * tile_state)) ** 2 + ((v - 4.80) / (1.52 + .30 * tile_state)) ** 2), 0, 1)
    fork_r = np.clip(1 - np.sqrt(((u - fork_sep) / (1.28 + .32 * tile_state)) ** 2 + ((v - 4.80) / (1.52 + .30 * tile_state)) ** 2), 0, 1)
    fork = np.maximum(fork_l, fork_r) * body
    notch = np.clip(1 - np.sqrt((u / 1.25) ** 2 + ((v - 5.10) / 1.36) ** 2), 0, 1)
    body *= 1 - notch * .92

    lip = np.clip(1 - np.abs(v + 4.72) / .52, 0, 1) * body
    rim = np.clip(1 - np.minimum(np.abs(np.abs(u) - taper + .45), np.abs(v - 5.0)) / .54, 0, 1) * body
    ridge = np.clip((np.cos((u + .16 * v + .72 * tile_state) * np.pi / (1.60 + .24 * tile_state)) - .52) * 2.25, 0, 1) * body
    cross = np.clip((np.cos((v - .10 * u + .48 * tile_state) * np.pi / (1.82 + .25 * tile_state)) - .60) * 2.55, 0, 1) * body
    window = np.clip(ridge * cross * 1.35, 0, 1)

    # Tiny concave retroreflector wells sit inside selected scale windows; the
    # double crescent produces Papilio-like blue/yellow mixing under motion.
    wu = np.mod(u + 7.25, 4.55) - 2.275
    wv = np.mod(v + 6.0, 4.15) - 2.075
    wr = np.sqrt((wu / 1.70) ** 2 + (wv / 1.45) ** 2)
    well = np.clip(1 - np.abs(wr - .72) / .23, 0, 1) * body
    well_core = np.clip(1 - wr / .58, 0, 1) * body

    # Per-tile optical families follow continuous wing-like sweeps, so a car
    # sees coherent bands composed of many fine scales rather than macro paint.
    cx = x - u
    cy = y - v
    f0 = n01(np.sin((cx + .42 * cy) / 73.0) + .66 * np.cos((cx - .58 * cy) / 129.0))
    f1 = n01(np.cos((cx - .31 * cy) / 91.0) + .54 * np.sin((cx + .71 * cy) / 151.0))
    f2 = n01(np.sin((cx + .77 * cy) / 53.0) + .48 * np.cos((cx - .21 * cy) / 173.0))
    melanin = np.clip((.30 - f0) * 4.4, 0, 1)
    lemon = np.clip((f0 - .36) * 2.2, 0, 1) * (1 - np.clip((f1 - .70) * 4.0, 0, 1))
    teal = np.clip((f1 - .42) * 2.4, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        body, fork, lip, rim, ridge, cross, window, well, well_core,
        melanin, lemon, teal, f0, f1, f2
    ))


def paint_butterfly_swallowtail_i1(paint, shape, mask, seed, pm, bb):
    body, fork, lip, rim, ridge, cross, window, well, well_core, melanin, lemon, teal, f0, f1, f2 = _surface(seed + 18041)
    black = np.array([.003, .004, .008], np.float32)
    ink = np.array([.010, .020, .050], np.float32)
    blue = np.array([.015, .19, .61], np.float32)
    cyan = np.array([.015, .76, .69], np.float32)
    yellow = np.array([.94, .79, .055], np.float32)
    amber = np.array([.94, .31, .025], np.float32)
    gold = np.array([1.00, .63, .08], np.float32)
    pearl = np.array([.88, .96, 1.00], np.float32)

    family = blue[None, None, :] * (1 - teal[..., None]) + cyan[None, None, :] * teal[..., None]
    family = family * (1 - lemon[..., None]) + yellow[None, None, :] * lemon[..., None]
    family = family * (1 - melanin[..., None]) + black[None, None, :] * melanin[..., None]
    col = ink[None, None, :] * (1 - body[..., None]) + family * body[..., None] * (.56 + .34 * f2[..., None])
    col += lip[..., None] * pearl[None, None, :] * (.22 + .23 * f1[..., None])
    col += rim[..., None] * gold[None, None, :] * (.43 + .34 * lemon[..., None])
    col += ridge[..., None] * cyan[None, None, :] * (.14 + .24 * teal[..., None])
    col += cross[..., None] * amber[None, None, :] * (.09 + .21 * lemon[..., None])
    col += window[..., None] * np.array([.08, .20, .46], np.float32)
    col += well[..., None] * (cyan[None, None, :] * (.34 + .28 * f0[..., None]) + yellow[None, None, :] * (.18 + .25 * f1[..., None]))
    col += well_core[..., None] * pearl[None, None, :] * (.34 + .46 * f2[..., None])
    col += fork[..., None] * gold[None, None, :] * (.12 + .18 * lemon[..., None])
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_butterfly_swallowtail_i1(shape, seed, sm, base_m, base_r):
    body, fork, lip, rim, ridge, cross, window, well, well_core, melanin, lemon, teal, f0, f1, f2 = _surface(seed + 18041)
    m_mix = (.16 * f0 + .13 * f2 + .15 * lip + .14 * well + .10 * rim +
             .09 * teal + .08 * ridge + .06 * fork + .05 * well_core +
             .04 * cross)
    r_mix = (.18 * f1 + .18 * melanin + .13 * cross + .12 * window +
             .10 * (1 - f2) + .08 * body + .07 * fork + .06 * rim +
             .05 * ridge + .03 * well_core)
    cc_mix = (.17 * f2 + .16 * lip + .14 * well_core + .12 * body +
              .10 * well + .09 * rim + .07 * lemon + .06 * ridge +
              .05 * window + .04 * (1 - melanin))
    m = 10 + 234 * m_mix + well * 18 - melanin * 30
    r = 15 + 225 * r_mix + melanin * 24 - lip * 18
    cc = 4 + 249 * cc_mix + well_core * 22 - melanin * 25
    m = np.mean(m) + 1.32 * (m - np.mean(m))
    r = np.mean(r) + 1.32 * (r - np.mean(r))
    cc = np.mean(cc) + 1.32 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 8, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
