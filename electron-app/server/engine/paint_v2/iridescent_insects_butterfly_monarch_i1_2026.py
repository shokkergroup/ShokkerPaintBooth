"""Monarch Mosaic I1 — fine Danaus scale windows and vein-black lattice.

SPB-105 / owner 2026-09-01.  Monarch orange is pigment-dominant, but the
overlapping tiled scales, upper-lamina ridges/crossribs and absorptive black
scale structure produce the material character.  This compresses that biology
into repeat-safe 8-32px native windows instead of one giant butterfly wing.
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
    dx, dy, d1, fid, d2 = _cells(GEN, 13.0, int(seed) % 7919 + 3469,
                                  jit=.91, taps=11, need2=True)
    vein = np.clip(1 - (d2 - d1) / 1.55, 0, 1) ** 1.15
    inner = np.clip((d2 - d1 - .45) / 2.7, 0, 1)
    rim = np.clip(1 - np.abs((d2 - d1) - 1.95) / .62, 0, 1)

    # Scale-over-scale roof tiles live inside every vein-bounded window.
    row = np.floor((y + 2.2 * np.sin(x / 37.0)) / 5.4)
    sx = np.mod(x + np.mod(row, 2) * 3.2, 7.4) - 3.7
    sy = np.mod(y + 2.2 * np.sin(x / 37.0), 5.4) - 2.7
    tile = np.clip(1 - (sx / 3.25) ** 2 - ((sy + .55) / 2.35) ** 2, 0, 1)
    tile_lip = np.clip(1 - np.abs(np.sqrt((sx / 3.25) ** 2 + ((sy + .55) / 2.35) ** 2) - .83) / .17, 0, 1)
    tile *= inner
    tile_lip *= inner

    # Fine upper-lamina ridges and crossribs remain subordinate to the scales.
    ridge = np.clip((np.cos((x + .10 * y) * np.pi / 2.7) - .72) * 3.6, 0, 1) * inner
    cross = np.clip((np.cos((y - .08 * x) * np.pi / 4.4) - .82) * 5.0, 0, 1) * ridge

    # White marginal spots are bound to selected vein junctions—not random
    # confetti.  Many small spots guarantee distribution across a whole car.
    rr = np.sqrt(dx * dx + dy * dy)
    spot_gate = (n01(np.sin(fid * 1.732 + 1.1) + .48 * np.cos(fid * .613)) > .88).astype(np.float32)
    pearl = np.clip(1 - rr / 4.05, 0, 1) ** 1.15 * spot_gate * np.clip(inner * 1.45, 0, 1)

    cell_tone = n01(np.sin(fid * 2.236 + .4) + .55 * np.cos(fid * .414 + 2.0))
    f0 = n01(np.sin((x + .35 * y) / 61.0) + .54 * np.cos((x - .70 * y) / 103.0))
    f1 = n01(np.cos((x - .27 * y) / 79.0) + .51 * np.sin((x + .63 * y) / 137.0))
    f2 = n01(np.sin((x + .82 * y) / 43.0) + .45 * np.cos((x - .16 * y) / 149.0))
    return tuple(np.asarray(a, np.float32) for a in (
        vein, inner, rim, tile, tile_lip, ridge, cross, pearl,
        cell_tone, f0, f1, f2
    ))


def paint_butterfly_monarch_i1(paint, shape, mask, seed, pm, bb):
    vein, inner, rim, tile, tile_lip, ridge, cross, pearl, cell_tone, f0, f1, f2 = _surface(seed + 12491)
    black = np.array([.002, .002, .003], np.float32)
    orange = np.array([.95, .135, .008], np.float32)
    vermilion = np.array([.55, .018, .006], np.float32)
    amber = np.array([1.00, .43, .020], np.float32)
    cream = np.array([.92, .86, .70], np.float32)

    cell_rgb = (vermilion[None, None, :] * (1 - cell_tone[..., None]) +
                amber[None, None, :] * cell_tone[..., None])
    col = black[None, None, :] + inner[..., None] * cell_rgb * (.67 + .24 * f0[..., None])
    col += tile[..., None] * orange[None, None, :] * (.16 + .18 * f1[..., None])
    col += tile_lip[..., None] * amber[None, None, :] * .42
    col += rim[..., None] * np.array([.34, .045, .006], np.float32)
    col *= 1 - vein[..., None] * .94
    col += ridge[..., None] * np.array([.22, .064, .012], np.float32)
    col += cross[..., None] * np.array([.39, .14, .022], np.float32)
    col += pearl[..., None] * cream[None, None, :] * (.82 + .18 * f2[..., None])
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_butterfly_monarch_i1(shape, seed, sm, base_m, base_r):
    vein, inner, rim, tile, tile_lip, ridge, cross, pearl, cell_tone, f0, f1, f2 = _surface(seed + 12491)
    # Pigment orange stays satin; black nanostructure is ultra-absorptive;
    # tile lips, ridges, crossribs, veins and white pearls each carry their own
    # response. Per-window state prevents a two-value posterized spec map.
    m = 12 + 220 * (.25 * f0 + .18 * cell_tone + .17 * rim + .14 * tile_lip + .11 * ridge + .09 * pearl + .06 * inner)
    r = 26 + 218 * (.27 * f1 + .18 * vein + .15 * (1 - cell_tone) + .13 * cross + .11 * tile + .09 * pearl + .07 * rim)
    cc = 5 + 250 * (.25 * f2 + .20 * inner + .15 * tile_lip + .13 * pearl + .11 * ridge + .09 * rim + .07 * cross) - vein * 40
    m -= vein * 28
    r += vein * 22 - pearl * 20
    cc += pearl * 28
    return (_resize(np.clip(m * sm, 0, 244), shape),
            _resize(np.clip(r, 12, 242), shape),
            _resize(np.clip(cc, 0, 255), shape))
