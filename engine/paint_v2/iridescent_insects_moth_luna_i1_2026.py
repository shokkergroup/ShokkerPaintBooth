"""Luna Silk I1 — feather-scale satin with curled-tip reverse diffraction.

SPB-105 / owner 2026-09-01: irregular 8-22px native elements, many adjacent
material states, no printed moons or textile wallpaper.  Lepidopteran scales
overlap cover/ground layers and carry ridge lamellae, crossribs and thin-film
lower laminae; curled scale tips can orient crossrib gratings vertically and
reverse their colour order at grazing light.  Actias luna supplies celadon.
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
    dx, dy, d1, fid, d2 = _cells(GEN, 10.6, int(seed) % 7919 + 28793,
                                  jit=.98, taps=11, need2=True)
    state = n01(np.sin(fid * 1.811 + .7) + .55 * np.cos(fid * .593 - 1.1))
    cx, cy = x - dx, y - dy
    f0 = n01(np.sin((cx + .34 * cy) / 61.0) + .61 * np.cos((cx - .70 * cy) / 119.0))
    f1 = n01(np.cos((cx - .41 * cy) / 79.0) + .52 * np.sin((cx + .64 * cy) / 143.0))
    f2 = n01(np.sin((cx + .76 * cy) / 43.0) + .47 * np.cos((cx - .18 * cy) / 169.0))

    angle = -.62 + 1.24 * f0 + .22 * (state - .5)
    ca, sa = np.cos(angle), np.sin(angle)
    rx, ry = dx * ca + dy * sa, -dx * sa + dy * ca
    length = 5.10 + .58 * state
    width = 3.72 + .58 * (1 - state)
    er = np.sqrt((rx / length) ** 2 + (ry / width) ** 2)
    body = np.clip(1 - (er - .72) / .28, 0, 1)
    edge = np.clip(1 - np.abs(er - .90) / .10, 0, 1) * body
    shaft = np.clip(1 - np.abs(ry) / .48, 0, 1) * np.clip((length - np.abs(rx)) / 1.1, 0, 1) * body
    barb_phase = (rx + np.sign(ry) * 1.34 * np.abs(ry) + .65 * state) * np.pi / 1.46
    barb = np.clip((np.cos(barb_phase) - .54) * 2.30, 0, 1) * body * (1 - shaft * .55)
    cross = np.clip((np.cos((ry - .10 * rx) * np.pi / 1.22) - .62) * 2.60, 0, 1) * body
    window = np.clip(barb * cross * 1.45, 0, 1)

    # Distal curled tip: paired scallops plus a tight vertical crossrib grating.
    tip_x = rx - (length - .65)
    lobe_l = np.clip(1 - np.sqrt((tip_x / .92) ** 2 + ((ry + .70) / .78) ** 2), 0, 1)
    lobe_r = np.clip(1 - np.sqrt((tip_x / .92) ** 2 + ((ry - .70) / .78) ** 2), 0, 1)
    tip = np.maximum(lobe_l, lobe_r) * body
    tip_grating = np.clip((np.cos(ry * np.pi / .68 + state * 2.8) - .48) * 2.10, 0, 1) * tip
    interstice = np.clip(1 - (d2 - d1) / .95, 0, 1)

    # Fine silk filaments follow the scale field's prevailing comb direction.
    filament_phase = x - .31 * y + 5.0 * np.sin(y / 67.0) + 2.4 * np.sin((x + y) / 111.0)
    filament = np.clip((np.cos(filament_phase * np.pi / 19.0) - .92) * 10.0, 0, 1)
    filament *= np.clip((np.cos((x + .14 * y) / 83.0) + .28) * 1.15, 0, 1)
    # Broad but non-geometric silk currents organize the micro-scales into
    # coherent plumes.  They are an underlayer, never a macro printed motif.
    plume = n01(np.sin((x + .28 * y) / 104.0 + 1.15 * np.sin(y / 181.0)) +
                .63 * np.cos((x - .51 * y) / 157.0 - .74 * np.sin(x / 227.0)))
    glint = np.clip((plume - .42) * 2.15, 0, 1) * np.clip((.76 - plume) * 3.15, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        body, edge, shaft, barb, cross, window, tip, tip_grating,
        interstice, filament, state, f0, f1, f2, plume, glint
    ))


def paint_moth_luna_i1(paint, shape, mask, seed, pm, bb):
    body, edge, shaft, barb, cross, window, tip, tip_grating, interstice, filament, state, f0, f1, f2, plume, glint = _surface(seed + 29123)
    charcoal = np.array([.008, .012, .015], np.float32)
    celadon = np.array([.42, .82, .57], np.float32)
    jade = np.array([.045, .47, .29], np.float32)
    lilac = np.array([.52, .25, .67], np.float32)
    silver = np.array([.69, .79, .76], np.float32)
    moon = np.array([.91, .96, .82], np.float32)
    cyan = np.array([.10, .70, .77], np.float32)

    under = jade[None, None, :] * (1 - plume[..., None]) + lilac[None, None, :] * plume[..., None]
    under = under * (.18 + .19 * f2[..., None]) + celadon[None, None, :] * (.06 + .12 * glint[..., None])
    family = celadon[None, None, :] * (1 - f1[..., None]) + lilac[None, None, :] * f1[..., None]
    family = family * (.39 + .35 * f2[..., None]) + jade[None, None, :] * (.09 + .13 * (1 - f0[..., None]))
    col = charcoal[None, None, :] * .45 + under * .55
    col = col * (1 - body[..., None] * .78) + body[..., None] * family
    selected = np.clip((state - .38) * 2.45, 0, 1)
    col += edge[..., None] * silver[None, None, :] * (.045 + .085 * state[..., None])
    col += shaft[..., None] * moon[None, None, :] * (.055 + .115 * f0[..., None]) * (.35 + .65 * selected[..., None])
    col += barb[..., None] * np.array([.16, .31, .21], np.float32) * (.10 + .13 * f2[..., None])
    col += window[..., None] * np.array([.10, .05, .16], np.float32)
    col += tip[..., None] * lilac[None, None, :] * (.08 + .13 * f1[..., None])
    col += tip_grating[..., None] * selected[..., None] * (cyan[None, None, :] * (.15 + .16 * f0[..., None]) + moon[None, None, :] * (.05 + .09 * f2[..., None]))
    col *= 1 - interstice[..., None] * .23
    col += filament[..., None] * silver[None, None, :] * (.035 + .075 * f1[..., None])
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_moth_luna_i1(shape, seed, sm, base_m, base_r):
    body, edge, shaft, barb, cross, window, tip, tip_grating, interstice, filament, state, f0, f1, f2, plume, glint = _surface(seed + 29123)
    m_mix = (.14 * f0 + .13 * edge + .11 * shaft + .11 * tip_grating +
             .10 * state + .08 * filament + .08 * barb + .07 * tip +
             .06 * window + .05 * body + .04 * plume + .03 * glint)
    r_mix = (.18 * f1 + .17 * interstice + .13 * cross + .12 * window +
             .10 * (1 - state) + .09 * barb + .07 * body + .06 * tip +
             .05 * filament + .03 * shaft + .04 * (1 - plume))
    cc_mix = (.17 * f2 + .15 * body + .14 * tip_grating + .12 * edge +
              .10 * shaft + .08 * tip + .07 * filament + .06 * barb +
              .06 * (1 - interstice) + .05 * state + .04 * glint)
    m = 8 + 238 * m_mix + tip_grating * 17 - interstice * 24
    r = 14 + 228 * r_mix + interstice * 18 - shaft * 14
    cc = 3 + 251 * cc_mix + tip_grating * 20 - window * 15
    m = np.mean(m) + 1.36 * (m - np.mean(m))
    r = np.mean(r) + 1.36 * (r - np.mean(r))
    cc = np.mean(cc) + 1.36 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 7, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
