"""IRIDESCENT INSECTS 2026 — hand-authored structural surface replacements.

SPB-105 / owner verdict 2026-09-01: 2048² car canvases need dense,
purposeful 8–32px detail, not broad color fields, macro symbols, generic
noise, or palette-only recolors.  Each exported pair below owns a different
biological optical grammar and independently phased M/R/Cc material states.
The small shared functions only provide coordinates/compositing; they never
choose a card's carrier or palette.
"""
from __future__ import annotations

import numpy as np


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _xy(shape):
    h, w = _hw(shape)
    y, x = np.mgrid[0:h, 0:w]
    return y.astype(np.float32), x.astype(np.float32)


def _apply(paint, mask, pm, colour, strength=0.93):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    amt = np.clip(mask * pm * strength, 0.0, 1.0)[:, :, None]
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - amt) + colour * amt
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _mix(stops, t):
    """Interpolate a deliberately authored palette across a scalar carrier."""
    s = np.asarray(stops, dtype=np.float32)
    p = np.clip(t, 0.0, 0.99999) * (len(s) - 1)
    lo = p.astype(np.int32)
    hi = np.minimum(lo + 1, len(s) - 1)
    f = (p - lo)[:, :, None]
    return s[lo] * (1.0 - f) + s[hi] * f


def _state(values, key):
    """Use hand-selected material states, not one global channel multiplier."""
    table = np.asarray(values, dtype=np.float32)
    return table[np.clip(key.astype(np.int32), 0, len(table) - 1)]


def _micro_warp(x, y, seed):
    return (
        np.sin((x * 0.117 + y * 0.043 + seed) * 0.73)
        + 0.55 * np.sin((x * 0.041 - y * 0.091 + seed * 1.7) * 1.19)
        + 0.25 * np.cos((x * 0.203 + y * 0.157 + seed * 0.3))
    ).astype(np.float32)


# 01 — CHRYSINA JEWEL: nested 10–24px elytral lozenges / wax pits / seam lips.
def _jewel(shape, seed):
    y, x = _xy(shape)
    flow = _micro_warp(x, y, seed + 101) * 2.8
    qx = (x + flow) / 14.0
    qy = (y - flow * 0.55 + (np.floor(qx) % 2) * 8.0) / 18.0
    fx, fy = qx - np.floor(qx), qy - np.floor(qy)
    diamond = np.abs(fx - 0.5) * 1.08 + np.abs(fy - 0.5)
    lip = np.clip((0.53 - diamond) * 10.0, 0.0, 1.0)
    core = np.clip((0.30 - diamond) * 12.0, 0.0, 1.0)
    pit = np.clip((diamond - 0.43) * 9.0, 0.0, 1.0)
    phase = (np.sin(np.floor(qx) * 1.73 + np.floor(qy) * 2.41 + seed) * 0.5 + 0.5)
    striae = np.clip(np.sin((x * 0.82 + y * 0.21 + flow) * np.pi / 10.0) * 0.5 + 0.5, 0, 1)
    key = np.clip((phase * 4.0 + core * 2.2 + lip * 1.5 + striae * 1.2).astype(np.int32), 0, 8)
    return key, lip, core, pit, striae


def paint_beetle_jewel(paint, shape, mask, seed, pm, bb):
    key, lip, core, pit, striae = _jewel(shape, seed)
    colour = _mix([
        (0.012, 0.050, 0.031), (0.016, 0.125, 0.070), (0.025, 0.255, 0.115),
        (0.060, 0.410, 0.165), (0.145, 0.555, 0.190), (0.365, 0.630, 0.105),
        (0.660, 0.690, 0.095), (0.790, 0.610, 0.055), (0.930, 0.790, 0.280)
    ], key / 8.0)
    colour = colour * (0.76 + 0.22 * core[:, :, None] + 0.10 * lip[:, :, None])
    colour += striae[:, :, None] * np.array([0.018, 0.030, 0.008], dtype=np.float32)
    colour *= (1.0 - pit[:, :, None] * 0.38)
    return _apply(paint, mask, pm, np.clip(colour, 0, 1))


def spec_beetle_jewel(shape, seed, sm, base_m, base_r):
    key, lip, core, pit, striae = _jewel(shape, seed)
    m = _state([42, 76, 106, 136, 165, 194, 221, 246, 255], key)
    r = _state([122, 96, 73, 54, 39, 28, 20, 15, 8], key)
    c = _state([174, 132, 94, 68, 44, 27, 18, 12, 5], key)
    m = np.clip(m + lip * 25 + core * 14 - pit * 40 + striae * 9, 0, 255) * sm
    r = np.clip(r - lip * 15 + pit * 53 + (1 - striae) * 8, 15, 255)
    c = np.clip(c - core * 20 + pit * 66 + lip * 6, 0, 255)
    return m.astype(np.float32), r.astype(np.float32), c.astype(np.float32)


# 02 — CHRYSOCHROA RIBBON: 8–20px oblique photonic ribbons with separate cuticle phases.
def _ribbon(shape, seed):
    y, x = _xy(shape)
    bend = 10.0 * np.sin(y / 43.0 + seed * 0.07) + 4.0 * np.sin((x + y) / 71.0)
    lane = (x * 0.72 + y * 0.41 + bend) / 13.0
    f = lane - np.floor(lane)
    ridge = np.clip(1.0 - np.abs(f - 0.50) * 6.0, 0, 1)
    shoulder = np.clip(1.0 - np.abs(f - 0.22) * 8.0, 0, 1) + np.clip(1.0 - np.abs(f - 0.78) * 8.0, 0, 1)
    cross = np.clip(np.sin((x * 0.18 - y * 0.33 + bend) * np.pi / 17.0) * 0.5 + 0.5, 0, 1)
    microcut = np.clip(np.sin((x * 0.77 + y * 0.31) * np.pi / 9.0) * 0.5 + 0.5, 0, 1)
    phase = np.mod(np.floor(lane) * 0.173 + cross * 0.73 + microcut * 0.41, 1.0)
    key = np.clip((phase * 9.0 + ridge * 1.4).astype(np.int32), 0, 10)
    return key, ridge, shoulder, cross, microcut


def paint_beetle_rainbow(paint, shape, mask, seed, pm, bb):
    key, ridge, shoulder, cross, microcut = _ribbon(shape, seed)
    colour = _mix([
        (0.030, 0.015, 0.080), (0.065, 0.025, 0.180), (0.040, 0.145, 0.390),
        (0.020, 0.390, 0.450), (0.030, 0.590, 0.245), (0.330, 0.660, 0.060),
        (0.760, 0.600, 0.045), (0.900, 0.235, 0.060), (0.730, 0.045, 0.250),
        (0.410, 0.030, 0.390), (0.170, 0.065, 0.340)
    ], key / 10.0)
    sheen = 0.66 + ridge * 0.28 + shoulder * 0.09 + microcut * 0.05
    colour = colour * sheen[:, :, None] + cross[:, :, None] * np.array([0.010, 0.018, 0.028], dtype=np.float32)
    return _apply(paint, mask, pm, np.clip(colour, 0, 1), 0.94)


def spec_beetle_rainbow(shape, seed, sm, base_m, base_r):
    key, ridge, shoulder, cross, microcut = _ribbon(shape, seed)
    m = _state([224, 244, 187, 228, 157, 202, 250, 214, 242, 174, 230], key)
    r = _state([26, 10, 54, 23, 72, 42, 8, 34, 16, 66, 29], key)
    c = _state([22, 4, 81, 16, 114, 48, 2, 33, 11, 99, 27], key)
    m = np.clip(m + ridge * 22 - shoulder * 18 + cross * 11, 0, 255) * sm
    r = np.clip(r - ridge * 13 + shoulder * 29 + microcut * 9, 15, 255)
    c = np.clip(c - ridge * 18 + shoulder * 26 + (1 - cross) * 12, 0, 255)
    return m.astype(np.float32), r.astype(np.float32), c.astype(np.float32)


# 03 — MORPHO LAMELLA: 8–18px ridges, irregular buttresses, and scale seams.
def _morpho(shape, seed):
    y, x = _xy(shape)
    drift = 4.0 * np.sin(x / 59.0 + seed * 0.11) + 2.2 * np.sin(y / 47.0)
    ladder = (y + drift) / 9.5
    lf = ladder - np.floor(ladder)
    ridge = np.clip(1.0 - np.abs(lf - 0.50) * 5.2, 0, 1)
    butt = np.clip(np.sin((x + drift * 2.5) * np.pi / 23.0) * 0.5 + 0.5, 0, 1) * ridge
    broken = np.clip(np.sin((x * 0.43 - y * 0.19 + seed) * np.pi / 13.0) * 0.5 + 0.5, 0, 1)
    seam = np.clip(np.sin((x * 0.12 + y * 0.08) * np.pi / 31.0) * 0.5 + 0.5, 0, 1)
    key = np.clip((ridge * 3.2 + butt * 2.1 + broken * 2.0 + seam * 1.6).astype(np.int32), 0, 8)
    return key, ridge, butt, broken, seam


def paint_butterfly_morpho(paint, shape, mask, seed, pm, bb):
    key, ridge, butt, broken, seam = _morpho(shape, seed)
    colour = _mix([
        (0.004, 0.009, 0.042), (0.006, 0.025, 0.105), (0.010, 0.070, 0.245),
        (0.020, 0.185, 0.480), (0.035, 0.350, 0.760), (0.120, 0.475, 0.980),
        (0.320, 0.520, 1.000), (0.460, 0.380, 0.920), (0.680, 0.720, 1.000)
    ], key / 8.0)
    colour = colour * (0.74 + ridge[:, :, None] * 0.21 + butt[:, :, None] * 0.12)
    colour += broken[:, :, None] * ridge[:, :, None] * np.array([0.015, 0.020, 0.045], dtype=np.float32)
    colour *= 0.92 + seam[:, :, None] * 0.08
    return _apply(paint, mask, pm, np.clip(colour, 0, 1), 0.94)


def spec_butterfly_morpho(shape, seed, sm, base_m, base_r):
    key, ridge, butt, broken, seam = _morpho(shape, seed)
    m = _state([28, 57, 91, 132, 173, 215, 248, 236, 255], key)
    r = _state([140, 105, 82, 61, 43, 28, 12, 21, 6], key)
    c = _state([184, 139, 98, 62, 39, 20, 5, 16, 0], key)
    m = np.clip(m + ridge * 22 + butt * 18 - (1 - broken) * 12, 0, 255) * sm
    r = np.clip(r - ridge * 16 - butt * 10 + (1 - broken) * 21 + seam * 7, 15, 255)
    c = np.clip(c - ridge * 20 - butt * 13 + (1 - broken) * 30, 0, 255)
    return m.astype(np.float32), r.astype(np.float32), c.astype(np.float32)


# 04 — MONARCH SCALEWORK: micro-scale rows and hairline wing veins, no giant wing graphic.
def _monarch(shape, seed):
    y, x = _xy(shape)
    row = (y + 3.8 * np.sin(x / 47.0 + seed)) / 13.0
    col = (x + 5.5 * np.sin(y / 38.0 + seed * 0.4)) / 17.0
    rf, cf = row - np.floor(row), col - np.floor(col)
    scale = np.clip(1.0 - (((cf - 0.50) / 0.44) ** 2 + ((rf - 0.57) / 0.39) ** 2), 0, 1)
    vein = np.clip(np.sin((x * 0.18 - y * 0.24 + seed) * np.pi / 29.0) * 0.5 + 0.5, 0, 1)
    vein = np.clip((vein - 0.84) * 6.0, 0, 1)
    rim = np.clip(1.0 - scale * 2.2, 0, 1)
    freckle = np.clip(np.sin((x * 0.63 + y * 0.71) * np.pi / 11.0) * 0.5 + 0.5, 0, 1)
    key = np.clip((scale * 3.6 + (1 - vein) * 1.6 + freckle * 1.9).astype(np.int32), 0, 8)
    return key, scale, vein, rim, freckle


def paint_butterfly_monarch(paint, shape, mask, seed, pm, bb):
    key, scale, vein, rim, freckle = _monarch(shape, seed)
    colour = _mix([
        (0.012, 0.006, 0.004), (0.035, 0.012, 0.006), (0.125, 0.035, 0.008),
        (0.310, 0.090, 0.012), (0.610, 0.220, 0.020), (0.930, 0.440, 0.028),
        (1.000, 0.660, 0.120), (0.860, 0.500, 0.210), (0.550, 0.170, 0.100)
    ], key / 8.0)
    colour *= (1 - vein[:, :, None] * 0.87)
    colour = colour * (0.72 + scale[:, :, None] * 0.24 + freckle[:, :, None] * 0.06)
    colour += rim[:, :, None] * np.array([0.014, 0.007, 0.002], dtype=np.float32)
    return _apply(paint, mask, pm, np.clip(colour, 0, 1), 0.93)


def spec_butterfly_monarch(shape, seed, sm, base_m, base_r):
    key, scale, vein, rim, freckle = _monarch(shape, seed)
    m = _state([6, 18, 49, 88, 132, 176, 221, 166, 103], key)
    r = _state([202, 168, 122, 78, 55, 34, 18, 48, 85], key)
    c = _state([211, 173, 129, 83, 48, 22, 8, 36, 74], key)
    m = np.clip(m + scale * 26 - vein * 75 + freckle * 10, 0, 255) * sm
    r = np.clip(r - scale * 23 + vein * 50 + rim * 11, 15, 255)
    c = np.clip(c - scale * 29 + vein * 86 + (1 - freckle) * 7, 0, 255)
    return m.astype(np.float32), r.astype(np.float32), c.astype(np.float32)


# 05 — DRAGONFLY RESILIN: membrane panels, branching cross-veins, and elastic node beads.
def _dragonfly(shape, seed):
    y, x = _xy(shape)
    a = x * 0.19 + y * 0.09 + 7.0 * np.sin(y / 73.0 + seed)
    b = x * -0.08 + y * 0.23 + 5.0 * np.sin(x / 61.0 + seed * 0.3)
    la = np.abs(np.sin(a * np.pi / 24.0))
    lb = np.abs(np.sin(b * np.pi / 19.0))
    vein_a = np.clip((la - 0.91) * 12.0, 0, 1)
    vein_b = np.clip((lb - 0.92) * 13.0, 0, 1)
    vein = np.maximum(vein_a, vein_b)
    cell = np.clip((1 - la) * (1 - lb), 0, 1)
    node = np.clip(vein_a * vein_b * 3.0, 0, 1)
    ripple = np.clip(np.sin((x * 0.33 + y * 0.27 + seed) * np.pi / 14.0) * 0.5 + 0.5, 0, 1)
    key = np.clip((cell * 3.0 + ripple * 2.2 + node * 3.4).astype(np.int32), 0, 8)
    return key, vein, cell, node, ripple


def paint_dragonfly_wing(paint, shape, mask, seed, pm, bb):
    key, vein, cell, node, ripple = _dragonfly(shape, seed)
    colour = _mix([
        (0.030, 0.060, 0.080), (0.070, 0.130, 0.180), (0.105, 0.235, 0.280),
        (0.110, 0.390, 0.395), (0.135, 0.535, 0.450), (0.300, 0.650, 0.510),
        (0.500, 0.710, 0.700), (0.570, 0.500, 0.800), (0.750, 0.820, 0.940)
    ], key / 8.0)
    vein_col = np.array([0.015, 0.022, 0.035], dtype=np.float32)
    colour = colour * (0.70 + cell[:, :, None] * 0.17 + ripple[:, :, None] * 0.08)
    colour = colour * (1 - vein[:, :, None]) + vein_col * vein[:, :, None]
    colour += node[:, :, None] * np.array([0.11, 0.16, 0.20], dtype=np.float32)
    return _apply(paint, mask, pm, np.clip(colour, 0, 1), 0.89)


def spec_dragonfly_wing(shape, seed, sm, base_m, base_r):
    key, vein, cell, node, ripple = _dragonfly(shape, seed)
    m = _state([45, 75, 110, 145, 174, 204, 225, 165, 238], key)
    r = _state([118, 91, 64, 46, 31, 20, 15, 58, 10], key)
    c = _state([172, 122, 84, 55, 33, 18, 7, 69, 0], key)
    m = np.clip(m - vein * 62 + node * 78 + ripple * 11, 0, 255) * sm
    r = np.clip(r + vein * 113 - node * 40 + (1 - cell) * 10, 15, 255)
    c = np.clip(c + vein * 99 - node * 35 + (1 - ripple) * 14, 0, 255)
    return m.astype(np.float32), r.astype(np.float32), c.astype(np.float32)
