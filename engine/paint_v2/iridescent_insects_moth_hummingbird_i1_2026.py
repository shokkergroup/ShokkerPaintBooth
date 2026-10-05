"""Hummingbird Blur I1 — Hemaris shed-scale membrane in wingbeat motion.

SPB-105 / owner 2026-09-01: native 8-32px anatomy, no speed-line wallpaper,
confetti or macro wing drawing.  Hemaris clearwings shed scales after eclosion,
leaving transparent membrane, reddish-brown marginal scale remnants and veins.
Clearwing transparency also depends on reduced/altered scales and anti-reflective
surface nanostructure.  This material distributes those mechanisms through a
whole-car field: tilted bristle scales, empty sockets, ragged copper remnants,
clear membrane wakes and contour-bound pollen all follow one wingbeat flow.
"""
from __future__ import annotations

import cv2
import numpy as np
from functools import lru_cache

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

GEN = 640


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


@lru_cache(maxsize=2)
def _surface(seed):
    # Solve on a smaller grid while expressing all geometry in the original
    # virtual 1024-space.  This preserves native mark scale after the final
    # resize and keeps the standard 2048 render inside the 2-3 second budget.
    s = GEN / 1024.0
    y, x = coords(GEN)
    y, x = y / s, x / s
    dx, dy, d1, fid, d2 = _cells(GEN, 8.4 * s, int(seed) % 7919 + 52711,
                                  jit=.98, taps=11, need2=True)
    dx, dy, d1, d2 = dx / s, dy / s, d1 / s, d2 / s
    vdx, vdy, vd1, vfid, vd2 = _cells(GEN, 34.0 * s, int(seed) % 6151 + 69317,
                                       jit=.88, taps=11, need2=True)
    vdx, vdy, vd1, vd2 = vdx / s, vdy / s, vd1 / s, vd2 / s
    vr = np.sqrt(vdx * vdx + vdy * vdy)
    vt = np.arctan2(vdy, vdx)
    vstate = n01(np.sin(vfid * 1.317 + .7) + .62 * np.cos(vfid * .371 - 1.2))
    f0 = n01(np.sin(vr / 5.2 + 1.25 * vt + .9 * vstate) + .58 * np.cos(vr / 9.1 - 2.1 * vt))
    f1 = n01(np.cos(vr / 7.1 - 1.6 * vt + .7 * vstate) + .51 * np.sin(vr / 11.8 + 2.7 * vt))
    f2 = n01(np.sin(vr / 4.1 + 2.3 * vt - .8 * vstate) + .46 * np.cos(vr / 10.4 - 1.1 * vt))
    state = n01(np.sin(fid * 1.927 + .9) + .58 * np.cos(fid * .487 - .6))

    # Each 30-110px organizational vortex is a local wingbeat, not a printed
    # motif.  Fine scale fragments circulate around it; adjacent vortices flip
    # handedness and material family so the field never becomes speed stripes.
    clockwise = np.clip((vstate - .34) * 1.52, 0, 1)
    downstroke = np.clip((.66 - vstate) * 1.52, 0, 1)
    orbit = np.sin(vr / 3.05 + 2.15 * vt * (clockwise - downstroke) + vstate * 2.4)
    clear_ring = np.clip((orbit - .02) * 1.58, 0, 1)
    core = np.clip(1 - vr / (6.3 + 3.3 * vstate), 0, 1)
    shed = np.clip(.58 * clear_ring + .76 * core + .24 * f1 - .32, 0, 1)

    angle = vt + np.pi * .5 + .42 * np.sin(vr / 5.1 + state * 2.1)
    ca, sa = np.cos(angle), np.sin(angle)
    rx, ry = dx * ca + dy * sa, -dx * sa + dy * ca
    half_len = 3.75 + .72 * state
    half_wid = 1.92 + .30 * (1 - state)
    er = np.sqrt((rx / half_len) ** 2 + (ry / half_wid) ** 2)
    scale = np.clip(1 - (er - .71) / .29, 0, 1)
    bristle = np.clip(1 - np.abs(ry) / .48, 0, 1) * np.clip((half_len - np.abs(rx)) / 1.08, 0, 1) * scale
    fork_a = np.clip(1 - np.sqrt(((rx - half_len + .82) / 1.34) ** 2 + ((ry - .62) / .66) ** 2), 0, 1)
    fork_b = np.clip(1 - np.sqrt(((rx - half_len + .82) / 1.34) ** 2 + ((ry + .62) / .66) ** 2), 0, 1)
    fork = np.maximum(fork_a, fork_b) * scale
    lip = np.clip(1 - np.abs(er - .88) / .12, 0, 1) * scale
    cross = np.clip((np.cos((ry - .13 * rx) * np.pi / 1.13) - .59) * 2.44, 0, 1) * scale

    # Detached scales leave material socket halos; retained bristles and empty
    # sockets are mutually exclusive, creating clear membrane without erasure.
    keep = np.clip(1 - shed * 1.18, 0, 1)
    retained = scale * keep
    retained_bristle = bristle * keep
    retained_fork = fork * keep
    retained_lip = lip * keep
    rr = np.sqrt(dx * dx + dy * dy)
    socket = np.clip(1 - np.abs(rr - 2.65) / .72, 0, 1) * np.clip(shed * 1.55, 0, 1)

    # Anti-reflective membrane relief is an offset hex/pillar mesh, visible as
    # glass sheen rather than a printed grid.
    hx = np.mod(x + np.mod(np.floor(y / 5.8), 2) * 3.1, 6.2) - 3.1
    hy = np.mod(y, 5.8) - 2.9
    pillar = np.clip(1 - np.sqrt((hx / 1.55) ** 2 + (hy / 1.55) ** 2), 0, 1) * shed
    membrane_ripple = n01(np.sin((x - .22 * y) / 11.7 + .74 * np.sin(y / 53.0))) * shed

    # Pollen adheres only to fine orbital lips and retained fork tips.
    beat_contour = np.clip(1 - np.abs(np.sin(vr / 3.45 + 2.4 * vt + vstate * 3.1)) / .15, 0, 1)
    pollen = retained_fork * beat_contour * np.clip((state - .53) * 3.2, 0, 1)
    wake = beat_contour * np.clip((np.cos(vr * np.pi / 3.3 + vt * 1.7) - .76) * 4.15, 0, 1)
    interstice = np.clip(1 - (d2 - d1) / .88, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        retained, retained_bristle, retained_fork, retained_lip, cross,
        socket, pillar, membrane_ripple, pollen, wake, interstice,
        clockwise, downstroke, shed, state, f0, f1, f2
    ))


def paint_moth_hummingbird_i1(paint, shape, mask, seed, pm, bb):
    retained, bristle, fork, lip, cross, socket, pillar, ripple, pollen, wake, interstice, upstroke, downstroke, shed, state, f0, f1, f2 = _surface(seed + 21617)
    smoke = np.array([.018, .030, .031], np.float32)
    glass = np.array([.16, .34, .33], np.float32)
    olive = np.array([.24, .38, .12], np.float32)
    copper = np.array([.72, .155, .035], np.float32)
    bronze = np.array([.49, .24, .055], np.float32)
    pearl = np.array([.72, .82, .72], np.float32)
    cyan = np.array([.065, .52, .58], np.float32)
    pollen_gold = np.array([1.00, .58, .035], np.float32)

    membrane = smoke[None, None, :] * (1 - shed[..., None] * .62) + glass[None, None, :] * shed[..., None] * (.45 + .28 * f0[..., None])
    family = olive[None, None, :] * upstroke[..., None] + copper[None, None, :] * downstroke[..., None]
    family = family / np.maximum((upstroke + downstroke)[..., None], .65)
    col = membrane * (1 - retained[..., None] * .72) + retained[..., None] * family * (.52 + .31 * state[..., None])
    col += bristle[..., None] * pearl[None, None, :] * (.07 + .16 * f1[..., None])
    col += lip[..., None] * bronze[None, None, :] * (.15 + .24 * upstroke[..., None])
    col += fork[..., None] * copper[None, None, :] * (.11 + .20 * downstroke[..., None])
    col += cross[..., None] * np.array([.06, .13, .08], np.float32) * (.13 + .18 * f2[..., None])
    col += socket[..., None] * bronze[None, None, :] * (.21 + .25 * f1[..., None])
    col += pillar[..., None] * cyan[None, None, :] * (.11 + .20 * f2[..., None])
    col += ripple[..., None] * pearl[None, None, :] * (.025 + .075 * f0[..., None])
    col += pollen[..., None] * pollen_gold[None, None, :] * .88
    col += wake[..., None] * cyan[None, None, :] * (.06 + .11 * shed[..., None])
    col *= 1 - interstice[..., None] * .30
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_moth_hummingbird_i1(shape, seed, sm, base_m, base_r):
    retained, bristle, fork, lip, cross, socket, pillar, ripple, pollen, wake, interstice, upstroke, downstroke, shed, state, f0, f1, f2 = _surface(seed + 21617)
    m = 6 + 243 * (.15 * f0 + .14 * retained + .12 * lip + .11 * downstroke +
                   .10 * pollen + .09 * bristle + .08 * socket + .07 * wake +
                   .06 * state + .05 * fork + .03 * pillar)
    r = 10 + 235 * (.16 * f1 + .15 * shed + .13 * interstice + .11 * ripple +
                    .10 * cross + .09 * upstroke + .08 * socket + .07 * pillar +
                    .06 * (1 - state) + .05 * retained)
    cc = 4 + 250 * (.17 * f2 + .16 * shed + .13 * pillar + .11 * ripple +
                    .10 * lip + .09 * pollen + .08 * wake + .06 * fork +
                    .05 * (1 - interstice) + .05 * state)
    m += pollen * 27 - shed * 17
    r += interstice * 16 - pollen * 19
    cc += shed * 24 + pollen * 18
    m = np.mean(m) + 1.31 * (m - np.mean(m))
    r = np.mean(r) + 1.28 * (r - np.mean(r))
    cc = np.mean(cc) + 1.30 * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 248), shape),
            _resize(np.clip(r, 7, 246), shape),
            _resize(np.clip(cc, 0, 255), shape))
