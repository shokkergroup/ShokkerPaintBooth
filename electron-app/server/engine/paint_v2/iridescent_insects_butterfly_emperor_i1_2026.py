"""Emperor Eyelet I1 — scale-cell ocelli over purple-emperor optics.

SPB-105 / owner 2026-09-01.  Butterfly eyespots are concentric colour rings
assembled from one-colour scale cells, while Sasakia emperor blue gains power
from ridged scales over melanin-black or white backgrounds.  This uses broken
8-28px native eyelet rings inside a dense overlapping scale lattice—never one
giant eye printed across a car.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

# Shared by the I2 identity wrapper.  896² plus a 14px solve pitch keeps the
# eyelet-cell cadence at 32px native and meets the real cold-render budget.
GEN = 896


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
    dx, dy, d1, fid, d2 = _cells(GEN, 14.0, int(seed) % 7919 + 10357,
                                  jit=.90, taps=13, need2=True)
    state = n01(np.sin(fid * 1.732 + .6) + .51 * np.cos(fid * .517 + 1.9))
    # Evaluate the long-wave carrier at each Voronoi centre so whole eyelets
    # gather into flowing, interlocked ribbons instead of reading as dot noise.
    cx, cy = x - dx, y - dy
    stream = n01(np.sin((cx + .37 * cy) / 46.0) +
                 .62 * np.cos((cx - .71 * cy) / 83.0) +
                 .31 * np.sin((cx + .12 * cy) / 137.0))
    # Only selected scale cells become ocelli.  The selector follows a second
    # oblique cadence, producing braided chains rather than a filled dot field.
    cadence = n01(np.sin((cx + .62 * cy) / 24.0 + .72 * np.sin(cy / 91.0)) +
                  .45 * np.cos((cx - .18 * cy) / 51.0))
    eyelet = np.clip((stream - .40) * 3.4, 0, 1) * np.clip((cadence - .48) * 4.2, 0, 1)
    angle = (state - .5) * .62
    ca, sa = np.cos(angle), np.sin(angle)
    rx, ry = dx * ca + dy * sa, -dx * sa + dy * ca
    rr = np.sqrt((rx / (1.0 + .18 * state)) ** 2 + (ry / (1.0 - .10 * state)) ** 2)
    theta = np.arctan2(ry, rx)
    break_a = np.clip((np.sin(theta * 3.0 + state * 5.2) + .20) * 2.1, 0, 1)
    break_b = np.clip((np.cos(theta * 4.0 - state * 4.3) + .05) * 1.8, 0, 1)
    outer = np.clip(1 - np.abs(rr - 6.15) / 1.08, 0, 1) * break_a * eyelet
    gold = np.clip(1 - np.abs(rr - 4.35) / .96, 0, 1) * break_b * eyelet
    iris = np.clip(1 - np.abs(rr - 3.48) / 1.28, 0, 1) * eyelet
    dark = np.clip(1 - np.abs(rr - 2.85) / .82, 0, 1) * eyelet
    pupil_gate = np.clip((state - .31) * 2.7, 0, 1) * eyelet
    pupil = np.clip(1 - rr / 1.62, 0, 1) ** 1.35 * pupil_gate
    spoke = np.clip((np.cos(theta * 7.0 + state * 3.2) - .72) * 3.6, 0, 1)
    spoke *= np.clip((6.8 - rr) / 3.8, 0, 1) * eyelet

    # Overlapping roof-tile scale matrix remains visible through and between
    # eyelets, carrying the dense ridges that make emperor blue flash.
    row = np.floor((y + 1.8 * np.sin(x / 53.0)) / 5.4)
    sx = np.mod(x + np.mod(row, 2) * 3.3, 7.1) - 3.55
    sy = np.mod(y + 1.8 * np.sin(x / 53.0), 5.4) - 2.7
    scale = np.clip(1 - (sx / 3.15) ** 2 - ((sy + .50) / 2.30) ** 2, 0, 1)
    scale_lip = np.clip(1 - np.abs(np.sqrt((sx / 3.15) ** 2 + ((sy + .50) / 2.30) ** 2) - .82) / .16, 0, 1)
    ridge = np.clip((np.cos((x + .12 * y) * np.pi / 2.55) - .72) * 3.7, 0, 1) * scale

    f0 = n01(np.sin((x + .31 * y) / 63.0) + .56 * np.cos((x - .68 * y) / 109.0))
    f1 = n01(np.cos((x - .36 * y) / 79.0) + .52 * np.sin((x + .57 * y) / 137.0))
    f2 = n01(np.sin((x + .81 * y) / 43.0) + .46 * np.cos((x - .17 * y) / 151.0))
    return tuple(np.asarray(a, np.float32) for a in (
        outer, gold, iris, dark, pupil, spoke, scale, scale_lip, ridge, state, stream, cadence, f0, f1, f2
    ))


def paint_butterfly_emperor_i1(paint, shape, mask, seed, pm, bb):
    outer, gold_ring, iris, dark, pupil, spoke, scale, scale_lip, ridge, state, stream, cadence, f0, f1, f2 = _surface(seed + 16561)
    midnight = np.array([.004, .003, .012], np.float32)
    indigo = np.array([.020, .035, .34], np.float32)
    violet = np.array([.20, .018, .38], np.float32)
    bronze = np.array([.62, .19, .035], np.float32)
    old_gold = np.array([.92, .55, .075], np.float32)
    pearl = np.array([.82, .90, 1.00], np.float32)

    blue = indigo[None, None, :] * (1 - f0[..., None]) + violet[None, None, :] * f0[..., None]
    # A continuous purple-emperor blue ground keeps the non-ocellus regions
    # luxurious; the scale lattice becomes relief, not the whole visual idea.
    col = midnight[None, None, :] + blue * (.18 + .27 * f0[..., None])
    col += scale[..., None] * blue * (.18 + .16 * f1[..., None])
    col += scale_lip[..., None] * np.array([.025, .075, .24], np.float32)
    col += ridge[..., None] * np.array([.040, .15, .39], np.float32)
    col += outer[..., None] * bronze[None, None, :] * (1.02 + .15 * state[..., None])
    col += gold_ring[..., None] * old_gold[None, None, :] * (1.02 + .10 * f2[..., None])
    col += iris[..., None] * np.array([.12, .08, .68], np.float32) * (.70 + .28 * cadence[..., None])
    col *= 1 - dark[..., None] * .93
    col += spoke[..., None] * np.array([.31, .070, .42], np.float32)
    col += pupil[..., None] * pearl[None, None, :] * .98
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_butterfly_emperor_i1(shape, seed, sm, base_m, base_r):
    outer, gold_ring, iris, dark, pupil, spoke, scale, scale_lip, ridge, state, stream, cadence, f0, f1, f2 = _surface(seed + 16561)
    # Expand independent, pattern-bound mixtures around their own means.  The
    # controlled 1.4x spread preserves thousands of adjacent material colours
    # without the harsh full-range normalization rejected in Emperor P4.
    m_mix = (.17 * f0 + .12 * state + .16 * outer + .16 * gold_ring + .10 * iris +
             .10 * ridge + .08 * pupil + .05 * scale_lip + .03 * spoke +
             .02 * stream + .01 * cadence)
    r_mix = (.19 * f1 + .18 * dark + .12 * (1 - state) + .12 * spoke + .09 * iris +
             .08 * scale + .09 * outer + .07 * pupil + .04 * ridge +
             .02 * (1 - stream))
    cc_mix = (.17 * f2 + .14 * scale + .15 * pupil + .11 * scale_lip +
              .13 * gold_ring + .10 * iris + .08 * ridge + .07 * outer +
              .03 * spoke + .02 * stream)
    m = 12 + 232 * m_mix
    r = 18 + 222 * r_mix
    cc = 4 + 251 * cc_mix - dark * 38
    m = np.mean(m) + 1.40 * (m - np.mean(m))
    r = np.mean(r) + 1.40 * (r - np.mean(r))
    cc = np.mean(cc) + 1.40 * (cc - np.mean(cc))
    m += gold_ring * 18 - dark * 28
    r += dark * 22 - pupil * 20
    cc += pupil * 25
    return (_resize(np.clip(m * sm, 0, 246), shape),
            _resize(np.clip(r, 10, 244), shape),
            _resize(np.clip(cc, 0, 255), shape))
