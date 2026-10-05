"""Tiger Moth Ember I1 — aposematic scale-barb rivers over soot velvet.

SPB-105 / owner 2026-09-01: hand-authored 8-32px native anatomy, no macro
stripe wallpaper and no scattered confetti.  Arctiinae warning colours commonly
place red/orange/yellow or green-blue scale populations against dark melanin;
each lepidopteran scale retains longitudinal ridges, microribs and crossribs.
Micropterix work also shows simple fused scale films changing gold, bronze and
purple with thickness while melanin supplies absorption.  Here, thousands of
tilted keratin-like scale hairs build broken warning rivers from the inside.
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
    dx, dy, d1, fid, d2 = _cells(GEN, 9.4, int(seed) % 7919 + 43261,
                                  jit=.96, taps=11, need2=True)
    f0 = n01(np.sin((x + .34 * y) / 67.0) + .62 * np.cos((x - .58 * y) / 131.0))
    f1 = n01(np.cos((x - .49 * y) / 83.0) + .55 * np.sin((x + .73 * y) / 157.0))
    f2 = n01(np.sin((x + .81 * y) / 47.0) + .49 * np.cos((x - .21 * y) / 179.0))
    state = n01(np.sin(fid * 1.741 + .3) + .57 * np.cos(fid * .519 - 1.4))

    # Aperiodic warning currents classify individual scales; the broad rhythm
    # never draws a stripe directly, so its edges stay made of fine anatomy.
    current = np.sin((x + .23 * y) / 14.8 + 1.16 * np.sin(y / 71.0))
    current += .54 * np.cos((x - .61 * y) / 23.5 - .72 * np.sin(x / 103.0))
    ember_zone = np.clip((current + .38) * 1.45, 0, 1)
    ivory_zone = np.clip((-current - .56) * 2.65, 0, 1)
    soot_zone = np.clip(1 - ember_zone * .82 - ivory_zone * .92, 0, 1)

    angle = -.82 + 1.48 * f0 + .26 * (state - .5)
    ca, sa = np.cos(angle), np.sin(angle)
    rx, ry = dx * ca + dy * sa, -dx * sa + dy * ca
    half_len = 4.25 + 1.05 * state
    half_wid = 1.85 + .42 * (1 - state)
    taper = np.clip(1 - .27 * (rx / np.maximum(half_len, .1)), .61, 1.34)
    er = np.sqrt((rx / half_len) ** 2 + (ry / (half_wid * taper)) ** 2)
    hair = np.clip(1 - (er - .70) / .30, 0, 1)
    lip = np.clip(1 - np.abs(er - .87) / .13, 0, 1) * hair
    shaft = np.clip(1 - np.abs(ry) / .52, 0, 1) * hair

    # Alternating barb fans and crossrib windows stay inside each scale hair.
    fan_phase = (rx + 1.28 * np.sign(ry) * np.abs(ry) + state) * np.pi / 1.34
    fan = np.clip((np.cos(fan_phase) - .48) * 2.1, 0, 1) * hair * (1 - shaft * .62)
    cross = np.clip((np.cos((ry - .15 * rx) * np.pi / 1.18) - .57) * 2.34, 0, 1) * hair
    window = np.clip(fan * cross * 1.52, 0, 1)

    # Gold keratin filaments connect scale tips along only selected current
    # contours, preventing isolated glitter or random dot rescue.
    contour = np.clip(1 - np.abs(np.sin(current * 1.73 + .35 * f2)) / .115, 0, 1)
    filament = contour * np.clip((np.cos((x - .18 * y) * np.pi / 8.7) - .72) * 3.55, 0, 1)
    tip = np.clip(1 - np.sqrt(((rx - half_len + .45) / 1.08) ** 2 + (ry / 1.26) ** 2), 0, 1) * hair
    interstice = np.clip(1 - (d2 - d1) / .82, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        hair, lip, shaft, fan, cross, window, filament, tip, interstice,
        ember_zone, ivory_zone, soot_zone, state, f0, f1, f2
    ))


def paint_moth_tiger_i1(paint, shape, mask, seed, pm, bb):
    hair, lip, shaft, fan, cross, window, filament, tip, interstice, ember_zone, ivory_zone, soot_zone, state, f0, f1, f2 = _surface(seed + 18827)
    soot = np.array([.006, .007, .009], np.float32)
    coal = np.array([.055, .020, .014], np.float32)
    ember = np.array([.96, .105, .008], np.float32)
    vermilion = np.array([.58, .018, .006], np.float32)
    ivory = np.array([.91, .78, .55], np.float32)
    gold = np.array([1.00, .48, .045], np.float32)
    violet = np.array([.25, .035, .31], np.float32)

    ember_family = vermilion[None, None, :] * (1 - state[..., None]) + ember[None, None, :] * state[..., None]
    body_family = (ember_family * ember_zone[..., None] +
                   ivory[None, None, :] * ivory_zone[..., None] +
                   coal[None, None, :] * soot_zone[..., None])
    col = soot[None, None, :] * (1 - hair[..., None] * .72) + hair[..., None] * body_family * (.68 + .28 * f0[..., None])
    col += lip[..., None] * (gold[None, None, :] * ember_zone[..., None] + ivory[None, None, :] * ivory_zone[..., None]) * (.12 + .24 * f1[..., None])
    col += shaft[..., None] * gold[None, None, :] * (.07 + .17 * ember_zone[..., None])
    col += fan[..., None] * violet[None, None, :] * (.14 + .22 * f2[..., None])
    col += window[..., None] * np.array([.03, .12, .15], np.float32) * (.18 + .24 * f1[..., None])
    col += filament[..., None] * gold[None, None, :] * (.31 + .34 * f2[..., None])
    col += tip[..., None] * ivory[None, None, :] * (.08 + .20 * ivory_zone[..., None])
    col *= 1 - interstice[..., None] * .49
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_moth_tiger_i1(shape, seed, sm, base_m, base_r):
    hair, lip, shaft, fan, cross, window, filament, tip, interstice, ember_zone, ivory_zone, soot_zone, state, f0, f1, f2 = _surface(seed + 18827)
    m = 7 + 242 * (.16 * f0 + .15 * ember_zone + .13 * lip + .12 * filament +
                   .10 * state + .09 * shaft + .08 * fan + .07 * tip +
                   .06 * window + .04 * hair)
    r = 12 + 232 * (.17 * f1 + .15 * soot_zone + .13 * interstice + .12 * cross +
                    .10 * (1 - state) + .09 * fan + .08 * ivory_zone +
                    .07 * hair + .05 * tip + .04 * filament)
    cc = 4 + 249 * (.17 * f2 + .15 * hair + .14 * lip + .12 * ember_zone +
                    .10 * filament + .09 * shaft + .08 * tip + .06 * window +
                    .05 * state + .04 * (1 - interstice))
    m -= interstice * 28 + soot_zone * 13
    r += interstice * 18 - filament * 17
    cc += filament * 24 - soot_zone * 12
    m = np.mean(m) + 1.28 * (m - np.mean(m))
    r = np.mean(r) + 1.25 * (r - np.mean(r))
    cc = np.mean(cc) + 1.28 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 7, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
