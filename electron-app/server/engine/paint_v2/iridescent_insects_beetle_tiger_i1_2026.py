"""Tiger Beetle Velocity I1 — Cicindelinae punctae and racing maculation.

SPB-105 / owner 2026-09-01.  Tiger-beetle structural colour is an additive
mixture: tightly packed epicuticular punctae reflect shorter wavelengths than
their copper/green surroundings, while unmelanized white maculations scatter
broadband light.  This card turns that biology into fine elytral velocity
lanes, never random confetti or a generic dot carrier.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

GEN = 384


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


@lru_cache(maxsize=2)
def _surface(seed):
    # I2 performance correction, owner 2026-09-01: the former 1024² field was
    # solved independently for paint and spec and cold-baked in 25.71s.  Solve
    # at 512², retain the original virtual 1024-coordinate geometry, and cache
    # the immutable feature tuple so paint/spec share one solve.
    s = GEN / 1024.0
    y, x = coords(GEN)
    y, x = y / s, x / s

    # Closely packed 8-18px full-resolution punctae.  Colour follows broad
    # optical lanes; cell identity never chooses an arbitrary random colour.
    dx, dy, d1, fid, d2 = _cells(GEN, 8.2 * s, int(seed) % 7919 + 1009,
                                  jit=.52, taps=5, need2=True)
    dx, dy, d1, d2 = dx / s, dy / s, d1 / s, d2 / s
    ang = .42 * np.sin((x - dx) / 83.0) + .18 * np.sin((y - dy) / 47.0)
    u = dx * np.cos(ang) + dy * np.sin(ang)
    v = -dx * np.sin(ang) + dy * np.cos(ang)
    q = (u / 3.25) ** 2 + (v / 2.55) ** 2
    pit = np.clip(1 - q, 0, 1) ** .68
    lip = np.clip((pit - .05) * 4.1, 0, 1) * np.clip(1 - (pit - .60) * 4.1, 0, 1)
    core = np.clip((pit - .48) * 2.15, 0, 1)
    seam = np.clip(1 - (d2 - d1) / 1.22, 0, 1)

    # Continuous copper/green/violet optical routes mimic the pointillistic
    # mixing seen at distance while retaining fine puncta under magnification.
    flow0 = n01(np.sin((x + .31 * y) / 57.0) + .58 * np.cos((x - .63 * y) / 93.0))
    flow1 = n01(np.cos((x - .24 * y) / 71.0) + .55 * np.sin((x + .81 * y) / 121.0))
    flow2 = n01(np.sin((x + .68 * y) / 39.0) + .46 * np.cos((x - .17 * y) / 149.0))

    # P2: compact, irregular knee/foot fragments.  Interfering flow families
    # remove the P1 wallpaper cadence while keeping every mark native-fine.
    wave_a = (np.sin((x + .78 * y) / 17.5) +
              .61 * np.sin((x - .29 * y) / 29.0) +
              .36 * np.cos((y + .18 * x) / 11.5))
    wave_b = (np.sin((x - .56 * y) / 21.0 + 1.3) +
              .57 * np.cos((x + .43 * y) / 33.0) +
              .31 * np.sin((y - .11 * x) / 13.0))
    # Zero-contours form connected maculation ribbons; maxima formed the
    # rejected P2 isolated "rice" marks.
    knee_a = np.clip((.098 - np.abs(wave_a)) / .046, 0, 1)
    knee_b = np.clip((.086 - np.abs(wave_b)) / .042, 0, 1)
    family = np.clip((n01(np.sin(x / 91.0 - y / 73.0) +
                              .57 * np.cos(x / 137.0 + y / 59.0)) - .34) * 3.2, 0, 1)
    fragment = np.clip((n01(np.sin(x / 47.0 + y / 61.0) +
                                .54 * np.cos(x / 83.0 - y / 37.0)) - .23) * 2.6, 0, 1)
    macula = np.clip(knee_a * (.48 + .52 * fragment) +
                     knee_b * (1 - family) * fragment * .30, 0, 1)
    macula_edge = np.clip((macula - .05) * 3.5, 0, 1) * np.clip(1 - (macula - .70) * 4.0, 0, 1)

    # Aligned microscopic scratch/compression teeth support the sense of speed.
    teeth = np.clip((np.sin((x * .91 - y * .41) * np.pi / 5.4) - .72) * 3.6, 0, 1)
    teeth *= np.clip((lip + seam) * .75, 0, 1) * (1 - macula)
    return tuple(np.asarray(a, np.float32) for a in (
        pit, lip, core, seam, flow0, flow1, flow2, macula, macula_edge, teeth
    ))


def paint_beetle_tiger_i1(paint, shape, mask, seed, pm, bb):
    pit, lip, core, seam, f0, f1, f2, macula, macula_edge, teeth = _surface(seed + 9423)
    copper = np.array([.58, .145, .025], np.float32)
    brass = np.array([.92, .54, .075], np.float32)
    green = np.array([.015, .50, .255], np.float32)
    violet = np.array([.075, .025, .31], np.float32)
    blue = np.array([.015, .20, .57], np.float32)
    ivory = np.array([.96, .94, .76], np.float32)

    ground = copper[None, None, :] * (1 - f0[..., None]) + brass[None, None, :] * f0[..., None]
    short = violet[None, None, :] * (1 - f1[..., None]) + blue[None, None, :] * f1[..., None]
    short = short * (1 - f2[..., None] * .48) + green[None, None, :] * f2[..., None] * .55
    col = ground * (1 - pit[..., None] * .20) + short * pit[..., None] * .31
    col += lip[..., None] * np.array([.032, .048, .020], np.float32)
    col -= core[..., None] * np.array([.035, .015, .005], np.float32)
    col += teeth[..., None] * np.array([.09, .16, .11], np.float32)
    col = col * (1 - macula[..., None] * .96) + ivory[None, None, :] * macula[..., None]
    col += macula_edge[..., None] * np.array([.035, .05, .07], np.float32)
    hi = _resize(np.clip(col, 0, 1), shape)
    return _blend(paint, mask, pm, hi)


def spec_beetle_tiger_i1(shape, seed, sm, base_m, base_r):
    pit, lip, core, seam, f0, f1, f2, macula, macula_edge, teeth = _surface(seed + 9423)
    # Independent structural-layer periods: blue puncta, green lips, copper
    # ground, broadband white maculation, compression teeth and seams all own
    # materially distinct response rather than sharing a single grayscale mask.
    m = 35 + 180 * (.50 * f0 + .23 * lip + .17 * core + .10 * teeth) - macula * 82
    r = 28 + 164 * (.53 * f1 + .19 * seam + .16 * macula + .12 * core) - lip * 30
    cc = 14 + 238 * (.49 * f2 + .22 * pit + .16 * macula_edge + .13 * teeth) - macula * 34
    m += pit * 27 - seam * 15
    r += macula_edge * 22
    cc += lip * 24
    m = np.clip(m * sm, 0, 238)
    r = np.clip(r, 16, 224)
    cc = np.clip(cc, 0, 255)
    return _resize(m, shape), _resize(r, shape), _resize(cc, shape)
