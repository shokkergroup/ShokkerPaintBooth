"""Ground Beetle Obsidian I1 — engraved Carabid diffraction armor.

SPB-105 / owner 2026-09-01.  Carabid elytra use polygonal microsculpture,
dense transverse diffraction gratings, sculpted green/cyan multilayers and in
some species subsurface Maltese-cross arrays.  This is oil-black asymmetric
armor with engraved mesh and scrape tracks, never a bright jewel-beetle clone.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

# Shared by the I2 identity wrapper.  At 704² the 10.8/11px plate and cross
# pitches resolve to 31–32px on the 2048² car canvas—the lowest safe solve
# before the carrier would violate the owner's native-detail ceiling.
GEN = 704


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
    dx, dy, d1, fid, d2 = _cells(GEN, 10.8, int(seed) % 7919 + 4363,
                                  jit=.81, taps=11, need2=True)
    mesh = np.clip(1 - (d2 - d1) / 1.30, 0, 1)
    plate = np.clip((d2 - d1 - .30) / 2.8, 0, 1)
    pit = np.clip(1 - (dx / 1.28) ** 2 - (dy / 1.02) ** 2, 0, 1) ** 1.8
    pit_lip = np.clip(1 - ((np.sqrt(dx * dx + dy * dy) - 1.65) / .72) ** 2, 0, 1)

    warp = 3.2 * np.sin(x / 71.0) + 2.0 * np.sin((x - y) / 113.0)
    transverse = np.clip((np.cos((y + warp) * np.pi / 4.6) - .75) * 4.0, 0, 1)
    transverse *= np.clip((plate + mesh * .45), 0, 1)

    # Diagonal abrasion/scrape routes are continuous fine contours, not random
    # scratches.  A second shorter family creates hooked intersections.
    scrape_field = (np.sin((x + .63 * y) / 14.0) +
                    .55 * np.sin((x - .24 * y) / 23.0) +
                    .30 * np.cos(y / 9.0))
    scrape = np.clip((.085 - np.abs(scrape_field)) / .042, 0, 1)
    scrape_gate = .22 + .78 * n01(np.sin(x / 83.0 - y / 61.0) +
                                  .52 * np.cos(x / 127.0 + y / 47.0))
    scrape *= scrape_gate

    # Tiny subsurface cross arms; strong in spec, nearly hidden in paint.
    cx = np.mod(x + 5.5, 11.0) - 5.5
    cy = np.mod(y + 5.5, 11.0) - 5.5
    arm_h = np.clip(1 - np.abs(cy) / .75, 0, 1) * np.clip(1 - np.abs(cx) / 3.4, 0, 1)
    arm_v = np.clip(1 - np.abs(cx) / .75, 0, 1) * np.clip(1 - np.abs(cy) / 3.4, 0, 1)
    cross = np.clip(arm_h + arm_v, 0, 1) * np.clip((plate - .2) * 1.4, 0, 1)

    f0 = n01(np.sin((x + .33 * y) / 59.0) + .60 * np.cos((x - .71 * y) / 103.0))
    f1 = n01(np.cos((x - .42 * y) / 77.0) + .53 * np.sin((x + .58 * y) / 137.0))
    f2 = n01(np.sin((x + .81 * y) / 41.0) + .47 * np.cos((x - .16 * y) / 149.0))
    return tuple(np.asarray(a, np.float32) for a in (
        mesh, plate, pit, pit_lip, transverse, scrape, cross, f0, f1, f2
    ))


def paint_beetle_ground_i1(paint, shape, mask, seed, pm, bb):
    mesh, plate, pit, pit_lip, transverse, scrape, cross, f0, f1, f2 = _surface(seed + 9463)
    obsidian = np.array([.004, .005, .009], np.float32)
    graphite = np.array([.055, .065, .082], np.float32)
    petrol = np.array([.010, .205, .175], np.float32)
    cobalt = np.array([.018, .080, .38], np.float32)
    mercury = np.array([.48, .60, .66], np.float32)

    oil = petrol[None, None, :] * (1 - f0[..., None]) + cobalt[None, None, :] * f0[..., None]
    col = obsidian[None, None, :] * (.48 + .16 * (1 - f2[..., None])) + graphite[None, None, :] * .30
    col += oil * (.56 + .40 * f1[..., None])
    col += plate[..., None] * np.array([.018, .030, .044], np.float32)
    col += mesh[..., None] * np.array([.060, .135, .125], np.float32)
    col += transverse[..., None] * np.array([.045, .125, .165], np.float32)
    col += scrape[..., None] * np.array([.18, .245, .285], np.float32)
    col += pit_lip[..., None] * mercury[None, None, :] * .14
    col *= 1 - pit[..., None] * .72
    col += cross[..., None] * np.array([.010, .018, .022], np.float32)
    hi = _resize(np.clip(col, 0, 1), shape)
    return _blend(paint, mask, pm, hi)


def spec_beetle_ground_i1(shape, seed, sm, base_m, base_r):
    mesh, plate, pit, pit_lip, transverse, scrape, cross, f0, f1, f2 = _surface(seed + 9463)
    # Black chrome plates, blue pearl gratings, wet mesh, dry abrasion, mercury
    # pit lips and buried cross arrays all separate across M/R/Cc.
    m = 38 + 196 * (.43 * f0 + .18 * plate + .15 * transverse + .13 * pit_lip + .11 * cross) - pit * 30
    r = 24 + 190 * (.46 * f1 + .23 * scrape + .14 * pit + .10 * mesh + .07 * cross) - transverse * 24
    cc = 8 + 246 * (.44 * f2 + .21 * mesh + .14 * plate + .12 * pit_lip + .09 * transverse) - scrape * 38
    m += scrape * 16
    r += (1 - plate) * 14
    cc += cross * 25
    m = np.clip(m * sm, 0, 242)
    r = np.clip(r, 12, 228)
    cc = np.clip(cc, 0, 255)
    return _resize(m, shape), _resize(r, shape), _resize(cc, shape)
