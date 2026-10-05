"""Rose Chafer Velvet I2 — chiral scallop bowls with local material identity.

SPB-105 / owner 2026-09-01, Finish Identity correction.  The I1 bowl anatomy
was useful, but broad generic f0/f1/f2 fields dominated both paint and spec and
made the live card converge with Emperor, Ground, Click and Owl.  I2 assigns
color and eight-tier M/R/Cc to each 8-22px native bowl, then binds rims, fan
striae, velvet crowns, pollen wells and lip glints to separate responses.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

# 768² solve keeps the warped bowl anatomy at roughly 10–30px after native
# upscale while holding the real 2048² standard render inside the 2–3s budget.
GEN = 768


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
    yw = (y + 9.2 * np.sin(x / 57.0) + 4.8 * np.sin((x + y) / 89.0) +
          2.6 * np.sin((x - 2.0 * y) / 143.0))
    row = np.floor(yw / 7.6)
    xw = (x + 7.6 * np.sin(y / 41.0) + 3.9 * np.cos((x - y) / 73.0) +
          2.1 * np.sin((2.0 * x + y) / 127.0))
    offset = np.mod(row, 2.0) * 5.15
    shifted = xw + offset + 5.15
    u = np.mod(shifted, 10.3) - 5.15
    v = np.mod(yw + 3.8, 7.6) - 3.8
    sid = row * 1601.0 + np.floor(shifted / 10.3)
    phase = float(int(seed) % 8191) * .00171

    q = (u / 5.15) ** 2 + ((v + .72) / 4.55) ** 2
    bowl = np.clip(1 - q, 0, 1) ** .42
    bowl *= np.clip((v + 3.2) / 1.25, 0, 1)
    crown = np.clip((bowl - .24) * 1.55, 0, 1)
    rim = np.clip((bowl - .04) * 4.6, 0, 1) * np.clip(1 - (bowl - .72) * 4.3, 0, 1)
    valley = np.clip(1 - bowl * 1.8, 0, 1)
    theta = np.arctan2(v + .5, u)
    radius = np.sqrt((u / 5.15) ** 2 + ((v + .6) / 4.55) ** 2)
    fan = np.clip((np.cos(theta * 7.0 + radius * 5.4) - .60) * 3.0, 0, 1) * bowl * (1 - crown * .42)
    dimple = np.clip(1 - (u / 1.10) ** 2 - ((v + 1.55) / .78) ** 2, 0, 1) ** 1.7
    glint = np.clip((np.sin(theta * 3.0 - radius * 8.0) - .70) * 3.4, 0, 1) * rim

    # Per-bowl chiral phase replaces I1's screen-space macro waves.
    # Hashes are constant inside each bowl and intentionally non-periodic in
    # screen space.  Their role is subordinate material variation; the visible
    # identity remains the bowl/rim/fan/well anatomy.
    hue = np.mod(np.sin(sid * 12.9898 + phase) * 43758.5453, 1.0)
    metal = np.mod(np.sin(sid * 39.3467 + 1.2 + phase) * 24634.6345, 1.0)
    rough = np.mod(np.sin(sid * 73.1569 - .8 - phase) * 15731.7431, 1.0)
    coat = np.mod(np.sin(sid * 19.9131 + .6 + phase) * 9513.1487, 1.0)
    twist = n01(np.sin(theta * 2.0 + hue * 5.3) + .62 * np.cos(radius * 10.0 - metal * 3.6))
    return tuple(np.asarray(a, np.float32) for a in (
        bowl, crown, rim, valley, fan, dimple, glint, hue, metal, rough, coat, twist,
    ))


def paint_beetle_rose_chafer_i2(paint, shape, mask, seed, pm, bb):
    bowl, crown, rim, valley, fan, dimple, glint, hue, metal, rough, coat, twist = _surface(seed + 31469)
    deep = np.array([.004, .048, .018], np.float32)
    jade = np.array([.012, .43, .085], np.float32)
    grass = np.array([.025, .68, .13], np.float32)
    chartreuse = np.array([.58, .91, .035], np.float32)
    gold = np.array([.96, .61, .055], np.float32)
    copper = np.array([.52, .055, .018], np.float32)
    violet = np.array([.20, .012, .34], np.float32)

    # Rose chafers read metallic green first.  Chiral twist moves locally from
    # jade through grass to chartreuse; copper/violet are limited polarization
    # accents instead of full-card bands.
    green = jade[None, None, :] * (1 - twist[..., None]) + grass[None, None, :] * twist[..., None]
    green = green * (1 - .28 * hue[..., None]) + chartreuse[None, None, :] * (.28 * hue[..., None])
    polarized = copper[None, None, :] * (1 - coat[..., None]) + violet[None, None, :] * coat[..., None]
    local = green * (.66 + .26 * metal[..., None]) + polarized * (.06 + .08 * rough[..., None])

    col = deep[None, None, :] * (1 - bowl[..., None] * .88) + local * bowl[..., None]
    col += crown[..., None] * np.array([.055, .13, .026], np.float32) * (.28 + .34 * coat[..., None])
    col += fan[..., None] * np.array([.12, .16, .025], np.float32) * (.22 + .36 * rough[..., None])
    col += rim[..., None] * gold[None, None, :] * (.12 + .22 * metal[..., None])
    col += glint[..., None] * np.array([.34, .39, .11], np.float32)
    col *= 1 - dimple[..., None] * .58
    col += dimple[..., None] * np.array([.33, .15, .012], np.float32) * (.66 + .22 * metal[..., None])
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_beetle_rose_chafer_i2(shape, seed, sm, base_m, base_r):
    bowl, crown, rim, valley, fan, dimple, glint, hue, metal, rough, coat, twist = _surface(seed + 31469)
    mt = np.floor(np.clip(metal, 0, .999) * 8.0) / 7.0
    rt = np.floor(np.clip(rough, 0, .999) * 8.0) / 7.0
    ct = np.floor(np.clip(coat, 0, .999) * 8.0) / 7.0

    # Neutral valleys plus independent bowl states make the combined map read
    # as scallop anatomy, not another category-wide rainbow wave.
    m = 118 + bowl * ((mt - .5) * 162) + rim * (31 + 31 * twist)
    m += fan * (15 + 24 * hue) - crown * 24 + dimple * 28
    r = 128 + bowl * ((rt - .5) * 174) + crown * (24 + 31 * hue)
    r += fan * (31 + 24 * metal) + dimple * 38 - rim * 53
    cc = 120 + bowl * ((ct - .5) * 182) + crown * (20 + 31 * twist)
    cc += glint * 52 + rim * (25 + 29 * coat) - dimple * 47 - fan * 20
    return (
        _resize(np.clip(m * sm, 0, 250), shape),
        _resize(np.clip(r, 4, 248), shape),
        _resize(np.clip(cc, 0, 255), shape),
    )
