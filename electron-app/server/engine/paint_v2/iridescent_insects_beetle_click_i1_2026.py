"""Click Beetle Plasma I1 — Elaterid superblack eyes and living lanterns.

SPB-105 / owner 2026-09-01.  Elaterids combine fine longitudinal elytral
striae/punctures with near-total-absorption eyespots built from vertical
microtubules; Pyrophorini add yellow-green/orange bioluminescent organs.  The
motifs repeat as 8-30px native structures so they distribute across a car.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

# Shared by the I2 identity-correction wrapper.  The original 1024² solve
# missed the real 2048² cold-render budget; all geometry below is scaled by
# .75 so the native 8–30px anatomy is preserved at a 768² solve.
GEN = 768


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
    ex, ey, e1, eid, e2 = _cells(GEN, 12.0, int(seed) % 6151 + 8719,
                                  jit=.93, taps=13, need2=True)
    state = n01(np.sin(eid * 1.414 + .8) + .47 * np.cos(eid * .618 + 1.7))
    angle = (state - .5) * 1.05
    ca, sa = np.cos(angle), np.sin(angle)
    sx = ex * ca + ey * sa
    sy = -ex * sa + ey * ca
    half_x = 3.675 + .9375 * state
    half_y = 2.4375 + .54 * (1 - state)
    rr = np.sqrt((sx / half_x) ** 2 + (sy / half_y) ** 2)
    eye = np.clip(1 - (rr - .72) / .22, 0, 1)
    iris = np.clip(1 - np.abs(rr - .83) / .15, 0, 1)
    pupil = np.clip(1 - rr / .56, 0, 1) ** 1.35
    corona = np.clip(1 - np.abs(rr - 1.00) / .12, 0, 1)
    center_x, center_y = x - ex, y - ey
    center_route = (np.sin((center_x + .36 * center_y) / 13.5) +
                    .53 * np.sin((center_x - .61 * center_y) / 23.25) +
                    .23 * np.cos(center_y / 8.25))
    lane = np.clip((.24 - np.abs(center_route)) / .13, 0, 1)
    pixel_route = (np.sin((x + .36 * y) / 13.5) +
                   .53 * np.sin((x - .61 * y) / 23.25) +
                   .23 * np.cos(y / 8.25))
    track = np.clip((.115 - np.abs(pixel_route)) / .070, 0, 1)
    eye *= lane
    iris *= lane
    pupil *= lane
    corona *= lane

    # Vertically aligned absorptive tubes inside every false eye.
    tube_x = np.mod(sx + 4.275, 1.7625) - .88125
    tube_y = np.mod(sy + 2.8875, 1.7625) - .88125
    tubes = np.clip(1 - (tube_x / .54) ** 2 - (tube_y / .54) ** 2, 0, 1) * pupil

    # Fine longitudinal elytral striae and uniform punctures outside eyes.
    bend = 1.125 * np.sin(y / 30.75) + .6 * np.cos((x + y) / 69.75)
    stria = np.clip((np.cos((x + .12 * y + bend) * np.pi / 1.7625) - .72) * 3.6, 0, 1)
    dx, dy, d1, fid, d2 = _cells(GEN, 3.45, int(seed) % 7919 + 5059,
                                  jit=.76, taps=11, need2=True)
    puncture = np.clip(1 - (dx / .72) ** 2 - (dy / .72) ** 2, 0, 1) ** 1.7
    shell = 1 - np.clip(eye + corona, 0, 1)
    stria *= shell
    puncture *= shell

    f0 = n01(np.sin((x + .34 * y) / 44.25) + .56 * np.cos((x - .66 * y) / 80.25))
    f1 = n01(np.cos((x - .31 * y) / 60.75) + .51 * np.sin((x + .59 * y) / 104.25))
    f2 = n01(np.sin((x + .79 * y) / 33.75) + .47 * np.cos((x - .18 * y) / 113.25))
    return tuple(np.asarray(a, np.float32) for a in (
        eye, iris, pupil, corona, tubes, stria, puncture, shell, track,
        state, f0, f1, f2
    ))


def paint_beetle_click_i1(paint, shape, mask, seed, pm, bb):
    eye, iris, pupil, corona, tubes, stria, puncture, shell, track, state, f0, f1, f2 = _surface(seed + 15101)
    black = np.array([.001, .001, .002], np.float32)
    graphite = np.array([.020, .029, .042], np.float32)
    blue = np.array([.015, .080, .235], np.float32)
    lime = np.array([.45, 1.00, .020], np.float32)
    amber = np.array([1.00, .29, .008], np.float32)
    sulfur = np.array([.88, 1.00, .045], np.float32)

    glow_rgb = lime[None, None, :] * (1 - state[..., None]) + amber[None, None, :] * state[..., None]
    col = graphite[None, None, :] * (.62 + .25 * f0[..., None]) + blue[None, None, :] * shell[..., None] * (.14 + .20 * f1[..., None])
    col += stria[..., None] * np.array([.065, .18, .24], np.float32)
    col += puncture[..., None] * np.array([.14, .24, .24], np.float32)
    col += track[..., None] * shell[..., None] * np.array([.018, .21, .23], np.float32)
    col = col * (1 - eye[..., None] * .92) + black[None, None, :] * eye[..., None] * .96
    col += iris[..., None] * glow_rgb * (.76 + .22 * f2[..., None])
    col += corona[..., None] * sulfur[None, None, :] * (.24 + .22 * f0[..., None])
    col += tubes[..., None] * np.array([.012, .025, .018], np.float32)
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_beetle_click_i1(shape, seed, sm, base_m, base_r):
    eye, iris, pupil, corona, tubes, stria, puncture, shell, track, state, f0, f1, f2 = _surface(seed + 15101)
    # Superblack tubes stay nonmetal/rough/uncoated; luminous organs, corona,
    # striae, punctures and shell domains each own independent spec states.
    m = 8 + 237 * (.23 * f0 + .17 * state + .15 * stria + .13 * iris + .11 * puncture + .08 * corona + .07 * shell + .06 * track)
    r = 14 + 226 * (.23 * f1 + .20 * pupil + .14 * tubes + .13 * puncture + .10 * (1 - state) + .08 * stria + .06 * corona + .06 * track)
    cc = 3 + 252 * (.22 * f2 + .18 * iris + .15 * corona + .13 * shell + .10 * stria + .08 * puncture + .07 * state + .07 * track)
    m -= pupil * 40
    r += tubes * 24 - iris * 28
    cc -= pupil * 46
    return (_resize(np.clip(m * sm, 0, 246), shape),
            _resize(np.clip(r, 10, 245), shape),
            _resize(np.clip(cc, 0, 255), shape))
