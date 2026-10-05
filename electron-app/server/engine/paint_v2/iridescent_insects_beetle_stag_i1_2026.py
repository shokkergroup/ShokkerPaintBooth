"""Stag Carapace I1 — Lucanus layered armor, not generic iridescence.

SPB-105 / owner 2026-09-01.  Research anchors: three-layer stag elytra,
trabecular pillars with concentric spiral-woven substructure, pore canals,
longitudinal ribs and a glossy black-to-oxblood sclerotized shell.  All marks
resolve as 8-32px native detail on a 2048 car canvas.
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
    a = np.clip(mask * pm * .95, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(col, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    y, x = coords(GEN)
    # 8-22px native asymmetric sclerite field.
    dx, dy, d1, fid, d2 = _cells(GEN, 8.4, int(seed) % 7919 + 2017,
                                  jit=.76, taps=11, need2=True)
    seam = np.clip(1 - (d2 - d1) / 1.05, 0, 1) ** 1.45
    face = np.clip((d2 - d1 - .18) / 2.45, 0, 1)
    pore = np.clip(1 - (dx / .72) ** 2 - (dy / .72) ** 2, 0, 1) ** 2.2

    # Dense rib grain runs longitudinally but bends through the armor, avoiding
    # wallpaper-straight lines.  Broken crossbars expose the woven laminae.
    bend = 2.4 * np.sin(y / 43.0) + 1.3 * np.cos((x + y) / 79.0)
    rib = np.clip((np.cos((x + .22 * y + bend) * np.pi / 3.9) - .70) * 3.5, 0, 1)
    rib *= .35 + .65 * face
    crossbar = np.clip((np.cos((y + 1.8 * np.sin(x / 57.0)) * np.pi / 5.6) - .83) * 5.0, 0, 1)
    crossbar *= rib

    # Each 18-26px native trabecular node carries several tiny concentric
    # spiral-woven rings.  The rings are structural, not isolated polka dots.
    dx2, dy2, q1, qid, q2 = _cells(GEN, 12.6, int(seed) % 6151 + 7331,
                                    jit=.88, taps=11, need2=True)
    rr = np.sqrt(dx2 * dx2 + dy2 * dy2)
    theta = np.arctan2(dy2, dx2)
    spiral = np.clip((np.cos(rr * 3.45 - theta * 1.7) - .52) * 2.25, 0, 1)
    spiral *= np.clip((5.0 - rr) / 2.5, 0, 1)
    hub = np.clip(1 - rr / 1.05, 0, 1) ** 1.7
    pillar = np.clip(1 - rr / 4.7, 0, 1)

    # Deterministic per-sclerite and per-pillar material identities create
    # thousands of adjacent small color/spec states without random confetti.
    cell_tone = n01(np.sin(fid * 1.6180339 + .7) + .57 * np.cos(fid * .381966 + 1.9))
    pillar_tone = n01(np.sin(qid * 2.4142136 + .3) + .49 * np.cos(qid * .707107 + 2.2))

    # Minute sensory setae emerge from selected pore canals.
    setae = np.clip((.080 - np.abs(np.sin((x + .34 * y) / 5.3))) / .045, 0, 1)
    setae *= np.clip((pore - .25) * 1.5, 0, 1)

    f0 = n01(np.sin((x + .22 * y) / 67.0) + .58 * np.cos((x - .71 * y) / 101.0))
    f1 = n01(np.cos((x - .35 * y) / 83.0) + .52 * np.sin((x + .63 * y) / 139.0))
    f2 = n01(np.sin((x + .77 * y) / 47.0) + .49 * np.cos((x - .18 * y) / 151.0))
    return tuple(np.asarray(a, np.float32) for a in (
        seam, face, pore, rib, crossbar, spiral, hub, pillar, setae,
        cell_tone, pillar_tone, f0, f1, f2
    ))


def paint_beetle_stag_i1(paint, shape, mask, seed, pm, bb):
    seam, face, pore, rib, crossbar, spiral, hub, pillar, setae, cell_tone, pillar_tone, f0, f1, f2 = _surface(seed + 11003)
    black = np.array([.006, .004, .006], np.float32)
    oxblood = np.array([.235, .010, .018], np.float32)
    mahogany = np.array([.100, .018, .012], np.float32)
    copper = np.array([.54, .145, .035], np.float32)
    violet = np.array([.090, .018, .120], np.float32)
    cold_steel = np.array([.055, .155, .34], np.float32)

    cell_rgb = (oxblood[None, None, :] * (1 - cell_tone[..., None]) +
                np.array([.035, .020, .125], np.float32)[None, None, :] * cell_tone[..., None])
    col = black[None, None, :] + mahogany[None, None, :] * (.34 + .50 * f0[..., None])
    col += cell_rgb * (.31 + .47 * f1[..., None])
    col += violet[None, None, :] * f2[..., None] * .30
    col += face[..., None] * cell_rgb * .18
    col += seam[..., None] * copper[None, None, :] * (.32 + .28 * f2[..., None])
    col += rib[..., None] * np.array([.13, .040, .021], np.float32)
    col += crossbar[..., None] * np.array([.29, .090, .024], np.float32)
    ring_rgb = (copper[None, None, :] * (1 - pillar_tone[..., None]) +
                cold_steel[None, None, :] * pillar_tone[..., None])
    col += spiral[..., None] * ring_rgb * (.84 + .20 * f0[..., None])
    col += hub[..., None] * (np.array([.76, .30, .075], np.float32)[None, None, :] *
                             (1 - pillar_tone[..., None]) + cold_steel[None, None, :] * pillar_tone[..., None]) * .62
    col *= 1 - pore[..., None] * .70
    col += setae[..., None] * np.array([.28, .16, .07], np.float32)
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_beetle_stag_i1(shape, seed, sm, base_m, base_r):
    seam, face, pore, rib, crossbar, spiral, hub, pillar, setae, cell_tone, pillar_tone, f0, f1, f2 = _surface(seed + 11003)
    # Eight materially distinct states: black chrome faces, satin oxblood,
    # copper seams, dry pores, glossy ribs, hard spiral weave, mercury hubs,
    # and fibrous setae.  Slow fields are deliberately de-phased per channel.
    m = 26 + 202 * (.26 * f0 + .17 * cell_tone + .15 * face + .13 * seam + .12 * spiral + .09 * hub + .05 * rib + .03 * setae)
    r = 18 + 215 * (.29 * f1 + .17 * (1 - cell_tone) + .18 * pore + .11 * crossbar + .09 * setae + .09 * seam + .07 * pillar) - spiral * 35
    cc = 5 + 250 * (.26 * f2 + .17 * pillar_tone + .17 * face + .13 * rib + .10 * pillar + .08 * spiral + .05 * hub + .04 * seam) - pore * 38
    m += hub * 20 - pore * 28
    r += (1 - face) * 12
    cc += crossbar * 16 - setae * 24
    return (_resize(np.clip(m * sm, 0, 245), shape),
            _resize(np.clip(r, 10, 235), shape),
            _resize(np.clip(cc, 0, 255), shape))
