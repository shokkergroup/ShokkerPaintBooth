"""Longhorn Filament I1 — Cerambycid photonic sack-scales.

SPB-105 / owner 2026-09-01.  Sulawesiella and Anoplophora longhorns carry
elongated scales whose ordered chitin-air multilayers make yellow-green and
orange while disordered networks make turquoise/blue.  Here every staggered
scale is about 9x30px native and contains its own fine crystal crossbands.
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
    row = np.floor((y + 2.4 * np.sin(x / 91.0)) / 6.4)
    # Alternating overlap and gentle flow keep the elongated scales organic.
    flow = 2.2 * np.sin(y / 39.0) + 1.4 * np.sin((x + y) / 107.0)
    raw_sx = np.mod(x + .5 * row * 15.2 + flow, 15.2) - 7.6
    raw_sy = np.mod(y + 2.4 * np.sin(x / 91.0), 6.4) - 3.2
    sid = row * 131.0 + np.floor((x + .5 * row * 15.2 + flow) / 15.2)
    state = n01(np.sin(sid * 1.618 + .9) + .53 * np.cos(sid * .414 + 2.1))
    disorder = n01(np.sin(sid * 2.236 + 1.6) + .48 * np.cos(sid * .732 + .3))
    angle = (state - .5) * .48 + (disorder - .5) * .16
    ca, sa = np.cos(angle), np.sin(angle)
    sx = raw_sx * ca + raw_sy * sa
    sy = -raw_sx * sa + raw_sy * ca
    half_l = 5.8 + 1.35 * state
    half_w = 1.85 + .52 * disorder
    rr = np.sqrt((sx / half_l) ** 2 + (sy / half_w) ** 2)
    sack = np.clip(1 - (rr - .74) / .25, 0, 1)
    lip = np.clip(1 - np.abs(rr - .82) / .13, 0, 1)
    core = np.clip(1 - np.abs(sy) / .72, 0, 1) * sack

    # Ball-and-stick / layered interior rendered as tiny crossbands and paired
    # pore nodes, all clipped inside their biological scale carrier.
    crossband = np.clip((np.cos((sx + .25 * sy) * np.pi / 2.15) - .62) * 2.65, 0, 1) * sack
    node_x = np.mod(sx + 7.15, 4.05) - 2.025
    node = np.clip(1 - (node_x / .88) ** 2 - (sy / .82) ** 2, 0, 1) * sack

    # Per-scale identity gives ordered yellow/orange and disordered turquoise
    # domains.  The hash is indexed by the actual staggered biological scales.
    f0 = n01(np.sin((x + .33 * y) / 71.0) + .57 * np.cos((x - .65 * y) / 109.0))
    f1 = n01(np.cos((x - .39 * y) / 83.0) + .52 * np.sin((x + .55 * y) / 137.0))
    f2 = n01(np.sin((x + .78 * y) / 47.0) + .45 * np.cos((x - .21 * y) / 157.0))
    return tuple(np.asarray(a, np.float32) for a in (
        sack, lip, core, crossband, node, state, disorder, f0, f1, f2
    ))


def paint_beetle_longhorn_i1(paint, shape, mask, seed, pm, bb):
    sack, lip, core, crossband, node, state, disorder, f0, f1, f2 = _surface(seed + 13781)
    black = np.array([.003, .004, .006], np.float32)
    green = np.array([.12, .73, .15], np.float32)
    gold = np.array([.96, .54, .035], np.float32)
    orange = np.array([.88, .105, .010], np.float32)
    turquoise = np.array([.015, .66, .64], np.float32)
    indigo = np.array([.025, .040, .28], np.float32)

    ordered = green[None, None, :] * (1 - state[..., None]) + gold[None, None, :] * state[..., None]
    hot = orange[None, None, :] * (1 - f0[..., None]) + ordered * f0[..., None]
    disordered = turquoise[None, None, :] * (1 - disorder[..., None]) + indigo[None, None, :] * disorder[..., None]
    scale_rgb = hot * (1 - disorder[..., None] ** 2) + disordered * disorder[..., None] ** 2

    col = black[None, None, :] + sack[..., None] * scale_rgb * (.60 + .28 * f1[..., None])
    col += lip[..., None] * scale_rgb * .42
    col += core[..., None] * np.array([.30, .32, .16], np.float32) * (.35 + .45 * f2[..., None])
    col += crossband[..., None] * np.array([.18, .20, .12], np.float32)
    col += node[..., None] * np.array([.68, .78, .50], np.float32) * .36
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_beetle_longhorn_i1(shape, seed, sm, base_m, base_r):
    sack, lip, core, crossband, node, state, disorder, f0, f1, f2 = _surface(seed + 13781)
    # Ordered lamellae, disordered turquoise networks, cortex lips, inner
    # crystal bands, pore nodes and black interstices all respond separately.
    m = 10 + 235 * (.23 * f0 + .18 * state + .16 * sack + .14 * lip + .11 * crossband + .10 * node + .08 * disorder)
    r = 18 + 220 * (.25 * f1 + .19 * disorder + .16 * (1 - state) + .13 * core + .11 * node + .09 * lip + .07 * (1 - sack))
    cc = 4 + 251 * (.23 * f2 + .19 * sack + .16 * (1 - disorder) + .14 * lip + .11 * core + .10 * crossband + .07 * node)
    m += node * 14
    r += (1 - sack) * 20 - lip * 24
    cc += lip * 22 - disorder * 18
    return (_resize(np.clip(m * sm, 0, 246), shape),
            _resize(np.clip(r, 10, 242), shape),
            _resize(np.clip(cc, 0, 255), shape))
