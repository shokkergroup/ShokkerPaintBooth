"""Buprestid Furnace I1 — thermosensitive nested valley multilayers.

SPB-105 / owner 2026-09-01.  Jewel-beetle elytra combine 10um surface cells,
roughly 50um sculpted valleys, chitin/melanin multilayers and irregular air
gaps.  Heating can drive green cuticle toward blue or red.  This surface uses
fine nested furnace valleys in a cellular sea, not a recycled shell tile.
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
    a = np.clip(mask * pm * .94, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(col, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    # A sea of 8-16px native cells, interrupted by separate 18-32px sculpted
    # reflector valleys.  Both populations follow broad heat-flow phases.
    sdx, sdy, sd1, sfid, sd2 = _cells(GEN, 6.4, int(seed) % 7919 + 2129,
                                      jit=.48, taps=9, need2=True)
    sq = (sdx / 2.75) ** 2 + (sdy / 2.35) ** 2
    cell = np.clip(1 - sq, 0, 1) ** .55
    cell_rim = np.clip((cell - .04) * 4.4, 0, 1) * np.clip(1 - (cell - .67) * 4.5, 0, 1)
    cell_core = np.clip((cell - .50) * 2.15, 0, 1)

    vdx, vdy, vd1, vfid, vd2 = _cells(GEN, 17.2, int(seed) % 6841 + 3251,
                                      jit=.72, taps=11, need2=True)
    ang = .7 * np.sin((x - vdx) / 97.0) + .35 * np.cos((y - vdy) / 73.0)
    vu = vdx * np.cos(ang) + vdy * np.sin(ang)
    vv = -vdx * np.sin(ang) + vdy * np.cos(ang)
    radius = np.sqrt((vu / 8.2) ** 2 + (vv / 6.6) ** 2)
    valley = np.clip(1 - radius, 0, 1) ** .46
    wall = np.clip((valley - .04) * 3.9, 0, 1) * np.clip(1 - (valley - .74) * 4.2, 0, 1)
    floor = np.clip((valley - .48) * 2.0, 0, 1)

    f0 = n01(np.sin((x + .52 * y) / 69.0) + .61 * np.cos((x - .31 * y) / 113.0))
    f1 = n01(np.cos((x - .74 * y) / 87.0) + .53 * np.sin((x + .28 * y) / 151.0))
    f2 = n01(np.sin((x + .17 * y) / 43.0) + .49 * np.cos((x - .81 * y) / 131.0))

    layer_phase = radius * 12.5 + f0 * 4.2 + np.sin(ang * 2.0) * .7
    lamella = np.clip((np.cos(layer_phase * np.pi) - .32) * 2.1, 0, 1) * valley
    air_gap = np.clip((np.sin(layer_phase * np.pi * .73 + 1.2) - .52) * 2.8, 0, 1) * valley
    mica = np.clip((np.sin((vu - vv) * np.pi / 3.8 + f2 * 3.0) - .70) * 3.4, 0, 1) * wall
    heat = n01(np.sin((x + .61 * y) / 19.0) +
               .58 * np.cos((x - .47 * y) / 27.0) +
               .34 * np.sin((x + y) / 13.0))
    return tuple(np.asarray(a, np.float32) for a in (
        cell, cell_rim, cell_core, valley, wall, floor, lamella, air_gap, mica,
        f0, f1, f2, heat
    ))


def paint_beetle_buprestid_i1(paint, shape, mask, seed, pm, bb):
    cell, cr, cc, valley, wall, floor, lamella, air, mica, f0, f1, f2, heat = _surface(seed + 9451)
    charcoal = np.array([.018, .008, .018], np.float32)
    green = np.array([.01, .34, .13], np.float32)
    copper = np.array([.72, .17, .025], np.float32)
    ember = np.array([.98, .45, .035], np.float32)
    violet = np.array([.23, .018, .38], np.float32)
    brass = np.array([.95, .72, .12], np.float32)
    cobalt = np.array([.015, .12, .48], np.float32)

    sea = charcoal[None, None, :] * (.18 + .12 * (1 - f2[..., None])) + green[None, None, :] * (.74 + .18 * f2[..., None])
    hot = copper[None, None, :] * (1 - f0[..., None]) + ember[None, None, :] * f0[..., None]
    cool = violet[None, None, :] * (1 - f1[..., None]) + cobalt[None, None, :] * f1[..., None]
    furnace = cool * (1 - heat[..., None]) + hot * heat[..., None]
    heat_s = heat * heat * (3 - 2 * heat)
    thermal = sea * (1 - heat_s[..., None]) + hot * heat_s[..., None]
    cool_phase = np.clip((f1 - .52) * 1.65, 0, .58)
    thermal = thermal * (1 - cool_phase[..., None]) + cool * cool_phase[..., None]
    col = thermal
    col += cell[..., None] * np.array([.004, .010, .006], np.float32)
    col += lamella[..., None] * brass[None, None, :] * (.035 + .052 * f2[..., None])
    col *= 1 - air[..., None] * .105
    col += wall[..., None] * np.array([.028, .024, .013], np.float32)
    col += mica[..., None] * np.array([.060, .085, .045], np.float32)
    col -= floor[..., None] * np.array([.010, .008, .006], np.float32)
    hi = _resize(np.clip(col, 0, 1), shape)
    return _blend(paint, mask, pm, hi)


def spec_beetle_buprestid_i1(shape, seed, sm, base_m, base_r):
    cell, cr, cc, valley, wall, floor, lamella, air, mica, f0, f1, f2, heat = _surface(seed + 9451)
    # Smooth cells, light-spreading walls, hot multilayer floors, irregular air
    # gaps and mica seams each have separate material ownership.
    m = 28 + 202 * (.40 * f0 + .20 * floor + .16 * lamella + .14 * cr + .10 * mica) - air * 24
    r = 24 + 185 * (.45 * f1 + .24 * wall + .14 * air + .10 * cc + .07 * heat) - floor * 30
    coat = 10 + 240 * (.42 * f2 + .20 * cell + .16 * lamella + .13 * mica + .09 * floor) - wall * 25
    m += heat * valley * 31
    r += (1 - heat) * valley * 19
    coat += cr * 22
    m = np.clip(m * sm, 0, 244)
    r = np.clip(r, 14, 226)
    coat = np.clip(coat, 0, 255)
    return _resize(m, shape), _resize(r, shape), _resize(coat, shape)
