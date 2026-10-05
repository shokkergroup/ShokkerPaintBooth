"""Rose Chafer Velvet I1 — polarized scallop-bowl cuticle.

SPB-105 / owner 2026-09-01.  Cetonia aurata carries a twisted chiral layered
reflector with dominant metallic green, circular-polarization selectivity and
bowl/dish reflector anatomy.  Dense staggered velvet bowls, fan striae and
pollen dimples provide the whole-car carrier at native 8-32px detail.
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
    a = np.clip(mask * pm * .94, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(col, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    # Warped staggered rows: 10-22px full-resolution scallops.  Row staggering
    # and two independent warps prevent a rigid wallpaper read.
    yw = (y + 9.2 * np.sin(x / 57.0) + 4.8 * np.sin((x + y) / 89.0) +
          2.6 * np.sin((x - 2.0 * y) / 143.0))
    row = np.floor(yw / 7.6)
    xw = (x + 7.6 * np.sin(y / 41.0) + 3.9 * np.cos((x - y) / 73.0) +
          2.1 * np.sin((2.0 * x + y) / 127.0))
    offset = np.mod(row, 2.0) * 5.15
    u = np.mod(xw + offset + 5.15, 10.3) - 5.15
    v = np.mod(yw + 3.8, 7.6) - 3.8

    # Each piece is a convex bowl with an open lower scallop, raised rim,
    # velvet crown, radial fan striae and one recessed pollen dimple.
    q = (u / 5.15) ** 2 + ((v + .72) / 4.55) ** 2
    bowl = np.clip(1 - q, 0, 1) ** .42
    lower_cut = np.clip((v + 3.2) / 1.25, 0, 1)
    bowl *= lower_cut
    crown = np.clip((bowl - .24) * 1.55, 0, 1)
    rim = np.clip((bowl - .04) * 4.6, 0, 1) * np.clip(1 - (bowl - .72) * 4.3, 0, 1)
    valley = np.clip(1 - bowl * 1.8, 0, 1)
    theta = np.arctan2(v + .5, u)
    radius = np.sqrt((u / 5.15) ** 2 + ((v + .6) / 4.55) ** 2)
    fan = np.clip((np.cos(theta * 7.0 + radius * 5.4) - .60) * 3.0, 0, 1) * bowl * (1 - crown * .42)
    dimple = np.clip(1 - (u / 1.10) ** 2 - ((v + 1.55) / .78) ** 2, 0, 1) ** 1.7
    lip_glint = np.clip((np.sin(theta * 3.0 - radius * 8.0) - .70) * 3.4, 0, 1) * rim

    # Chiral-layer phases occupy broad coherent regions while the local bowl
    # phase turns them into hundreds of distinct, adjacent material states.
    f0 = n01(np.sin((x + .28 * y) / 61.0) + .61 * np.cos((x - .73 * y) / 107.0))
    f1 = n01(np.cos((x - .46 * y) / 79.0) + .55 * np.sin((x + .64 * y) / 139.0))
    f2 = n01(np.sin((x + .91 * y) / 47.0) + .48 * np.cos((x - .19 * y) / 127.0))
    twist = n01(np.sin(theta * 2.0 + f0 * 4.8) + .62 * np.cos(radius * 10.0 - f1 * 3.2))
    return tuple(np.asarray(a, np.float32) for a in (
        bowl, crown, rim, valley, fan, dimple, lip_glint, f0, f1, f2, twist
    ))


def paint_beetle_rose_chafer_i1(paint, shape, mask, seed, pm, bb):
    bowl, crown, rim, valley, fan, dimple, glint, f0, f1, f2, twist = _surface(seed + 9437)
    deep = np.array([.006, .075, .030], np.float32)
    grass = np.array([.018, .52, .115], np.float32)
    chartreuse = np.array([.52, .88, .045], np.float32)
    gold = np.array([.93, .62, .075], np.float32)
    copper = np.array([.48, .065, .025], np.float32)
    violet = np.array([.18, .018, .31], np.float32)

    green = grass[None, None, :] * (1 - f0[..., None]) + chartreuse[None, None, :] * f0[..., None]
    polarized = copper[None, None, :] * (1 - f1[..., None]) + violet[None, None, :] * f1[..., None]
    polarized = polarized * (1 - twist[..., None]) + green * twist[..., None]
    col = deep[None, None, :] * (1 - bowl[..., None] * .90) + polarized * bowl[..., None] * .98
    col += crown[..., None] * np.array([.055, .12, .030], np.float32)
    col += fan[..., None] * np.array([.055, .095, .018], np.float32)
    col += rim[..., None] * gold[None, None, :] * (.10 + .12 * f2[..., None])
    col += glint[..., None] * np.array([.30, .34, .10], np.float32)
    col *= 1 - dimple[..., None] * .56
    col += dimple[..., None] * np.array([.30, .17, .018], np.float32)
    hi = _resize(np.clip(col, 0, 1), shape)
    return _blend(paint, mask, pm, hi)


def spec_beetle_rose_chafer_i1(shape, seed, sm, base_m, base_r):
    bowl, crown, rim, valley, fan, dimple, glint, f0, f1, f2, twist = _surface(seed + 9437)
    # Chiral green pearl, chartreuse metal, velvet valleys, clear pollen wells,
    # gold edge flash and satin fan striae all remain independently phased.
    m = 22 + 196 * (.43 * f0 + .20 * twist + .17 * rim + .12 * fan + .08 * glint) - valley * 18
    r = 26 + 174 * (.48 * f1 + .22 * valley + .14 * fan + .10 * dimple + .06 * crown) - rim * 25
    cc = 8 + 245 * (.45 * f2 + .22 * crown + .15 * glint + .10 * dimple + .08 * rim) - valley * 28
    m += dimple * 22
    r += (1 - twist) * bowl * 18
    cc += twist * bowl * 24
    m = np.clip(m * sm, 0, 241)
    r = np.clip(r, 14, 224)
    cc = np.clip(cc, 0, 255)
    return _resize(m, shape), _resize(r, shape), _resize(cc, shape)
