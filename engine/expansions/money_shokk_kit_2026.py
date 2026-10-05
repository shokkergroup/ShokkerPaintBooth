# -*- coding: utf-8 -*-
"""💵 MONEY SHOKK kit (2026-08-31) — the machinery of wealth.

Owner: *"Forty themed exotic engines about wealth in every form — mint foil,
vault steel, counterfeit gold, burn-a-stack green. Flexes harder than chrome.
Right now we are falling WELL SHORT of it doing what it's supposed to. Needs a
total rework."*

The old shelf was a colour × creature grid — Canary Coffin, Magenta Widow,
Cerulean Cobra, Lime Scorpion, Seafoam Piranha — with a money name on the box.
Nothing in it was about money.

This kit is. Currency is the most over-engineered printed object on earth and
almost all of that engineering is ANTI-COUNTERFEITING TEXTURE at exactly the
scale a car wants: intaglio you can feel with a thumbnail, guilloche rosettes cut
on a rose engine, microtext too small to photocopy, a security thread windowed
through the paper, optically variable ink. The owner's own phrase for these is
"exotic engines" — a guilloche lathe is literally called a rose engine, and
`guilloche()` below is that machine.

Everything else — cells, curl, filaments, dendrites, cracks, plates, craters —
is imported from the FLAMES kit rather than rewritten.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

from engine.expansions.fractured_flames_kit_2026 import (      # noqa: F401
    GEN, WORK, fbm, n01, pct, rng, upscale, cell_mean, worley, curl, filaments,
    dla, percolate, spall, anneal_crack, kh_braid, rt_fingers, sparks, eden,
    wrinkle, _h1,
)

# craters lives in the COSMOS kit; a keyhole and a meteorite pit are the same
# maths, so import it rather than writing a second one.
from engine.expansions.fractured_cosmos_kit_2026 import craters   # noqa: E402,F401

_TAU = 6.283185307179586


# ════════════════════════════════════════════════════════════════════════════
# THE PRINTING WORKS
# ════════════════════════════════════════════════════════════════════════════

def guilloche(shape, seed, period=96.0, ring=13.0, teeth=(5, 8, 11), amp=0.34,
              warp=26.0, spin=0.0, sharp=1.0):
    """Rose-engine lathe work, as an implicit field rather than drawn curves.

    A guilloche machine cuts r(theta) = R(1 + a cos(n theta)) over and over with
    the phase creeping, so what you actually see is a family of nested rosette
    contours a fixed distance apart. Writing that as a field —

        rho / (1 + a cos(n phi))  ->  sin(2 pi * that / ring)

    — gives the same contours, vectorised, and puts the LINE SPACING under
    direct control at `ring` px. That matters: drawn as polylines the pattern
    scored 0.19-0.28 on the car-band, because a few big rosettes put all their
    energy in the petal envelope (below the window) and the hairlines put the
    rest above it. As a field the spacing IS the frequency.

    Two tooth counts are beaten together, which is what the second eccentric on
    a real rose engine does, and a slow warp keeps it off a perfect lattice.
    """
    h, w = int(shape[0]), int(shape[1])
    sc = w / 2048.0
    P = max(8.0, float(period) * sc)
    R = max(2.0, float(ring) * sc)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if warp:
        wx = (fbm((h, w), seed + 21, octaves=(4, 8, 16), weights=(1.0, .55, .3)) - 0.5)
        wy = (fbm((h, w), seed + 29, octaves=(4, 8, 16), weights=(1.0, .55, .3)) - 0.5)
        xx = xx + wx * float(warp) * sc
        yy = yy + wy * float(warp) * sc
    row = np.floor(yy / P)
    dx = np.mod(xx + row * P * 0.5, P) - P * 0.5      # brick-offset lattice
    dy = np.mod(yy, P) - P * 0.5
    rho = np.hypot(dx, dy)
    phi = np.arctan2(dy, dx)
    out = None
    for k, n in enumerate(teeth):
        cell = (row.astype(np.int64) * 8191
                + np.floor((xx + row * P * 0.5) / P).astype(np.int64))
        ph = float(spin) + k * 1.1 + _h1(cell, 401 + k) * _TAU
        petal = 1.0 + float(amp) * np.cos(float(n) * phi + ph)
        f = 0.5 + 0.5 * np.sin(_TAU * (rho / np.maximum(petal, 0.25)) / R)
        out = f if out is None else np.minimum(out, f)
    return np.clip(np.power(out, float(sharp)), 0, 1).astype(np.float32)


def intaglio(shape, seed, field=None, lpi=120.0, angle=28.0, warp=26.0,
             cross=0.0, depth=1.0):
    """Line engraving: parallel burin lines whose WIDTH carries the tone.

    Measured sweep at 2048: lpi 90-150 scores 0.70-0.78 on the car band,
    lpi 210 scores 0.58 and lpi 250 only 0.36 — a square grating puts its
    fundamental at r = lpi and every harmonic ABOVE the window, so pushing the
    lines finer walks the whole pattern out of sight. Default 120.

    An engraver does not shade with grey, they shade by swelling and thinning a
    line. So the duty cycle of the grating is driven by the field rather than
    its brightness — which is why a banknote portrait still reads at arm's
    length and still shows individual lines at 100mm.
    """
    h, w = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if field is None:
        field = fbm((h, w), seed + 5, octaves=(16, 32, 64, 128, 256),
                    weights=(1.0, .85, .7, .5, .35))
    f = pct(np.asarray(field, np.float32))
    wob = (fbm((h, w), seed + 11, octaves=(16, 32, 64), weights=(1.0, .6, .35)) - 0.5) * warp

    def grating(deg):
        a = np.deg2rad(deg)
        u = (xx * np.cos(a) + yy * np.sin(a)) + wob
        ph = np.mod(u * (lpi / max(w, 1)) * _TAU, _TAU) / _TAU        # 0..1 across a line
        duty = np.clip(0.16 + 0.62 * (1.0 - f) * float(depth), 0.04, 0.92)
        return (np.abs(ph - 0.5) < duty * 0.5).astype(np.float32)

    out = grating(angle)
    if cross > 0:
        out = np.maximum(out, grating(angle + 62.0) * float(cross))
    return np.clip(out * 0.95 + f * 0.05, 0, 1).astype(np.float32)


def microtext(shape, seed, rows=110, density=0.62, height=7.0, jitter=0.35):
    """Rows of text too small to photocopy — resolved as glyph-weight blocks.

    Real microtext on a note is 0.2mm tall. Scaled onto a 2048 canvas over a
    whole car it lands at 6-10px, which is dead centre of the visible window,
    and it reads as a woven band of language rather than as noise.
    """
    h, w = int(shape[0]), int(shape[1])
    if cv2 is None:
        return np.zeros((h, w), np.float32)
    r = rng(seed)
    out = np.zeros((h, w), np.float32)
    gap = h / float(max(rows, 1))
    hh = max(2.0, height * (h / 2048.0))
    for i in range(int(rows)):
        y = i * gap + r.uniform(-jitter, jitter) * gap
        x = r.uniform(-40, 0)
        base = r.uniform(0.55, 1.0)
        while x < w:
            gw = r.uniform(1.6, 4.2) * (w / 2048.0)
            if r.random() < density:
                y0, y1 = int(y), int(y + hh)
                x0, x1 = int(x), int(x + gw)
                if y1 > y0 and x1 > x0:
                    out[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = \
                        base * r.uniform(0.75, 1.0)
            x += gw + r.uniform(0.8, 2.4) * (w / 2048.0)
    return np.clip(out, 0, 1)


def threads(shape, seed, stripes=13, window=0.42, fibres=1800, tilt=7.0):
    """The security thread: an embedded metal stripe that surfaces through
    windows in the paper, plus the loose UV fibres scattered in the pulp.

    One stripe across a car is a poster. A bank note is 155mm wide and a car is
    4.5m, so at true relative scale a note's single thread becomes a rank of
    them — which is what this draws.
    """
    h, w = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.deg2rad(tilt)
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    period = w / float(max(stripes, 1))
    band = np.abs(np.mod(u, period) - period * 0.5) < (period * 0.055)
    win = (np.mod(v, period * 0.34) < (period * 0.34 * window)).astype(np.float32)
    out = band.astype(np.float32) * (0.42 + 0.58 * win)
    if fibres:
        out = np.maximum(out, filaments((h, w), seed + 3, n=int(fibres),
                                        length=int(9 * w / 2048.0) + 4,
                                        wander=0.85, width=1.0) * 0.8)
    return np.clip(out, 0, 1)


def moire(shape, seed, lpi=210.0, beat=1.045, angle=11.0, sharp=1.6, depth=0.70):
    """What a scanner does to a note. Two near-identical gratings at a small
    relative angle: the LINES stay fine (in the visible window) while their
    interference walks a slow beat across the panel. This is the tell of a
    reproduction, and it is the signature of the COUNTERFEIT chapter."""
    h, w = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a1 = np.deg2rad(angle)
    a2 = np.deg2rad(angle + 2.6)
    k = (lpi / max(w, 1)) * _TAU
    g1 = np.sin((xx * np.cos(a1) + yy * np.sin(a1)) * k)
    g2 = np.sin((xx * np.cos(a2) + yy * np.sin(a2)) * k * float(beat))
    env = 0.5 + 0.5 * (g1 * g2)          # the slow beat, on its own
    m = (0.5 + 0.5 * g1) * ((1.0 - float(depth)) + float(depth) * env)
    return np.clip(np.power(m, float(sharp)), 0, 1).astype(np.float32)


def knurl(shape, seed, pitch=26.0, angle=34.0, relief=1.0, wobble=0.35):
    """Diamond knurl: the grip cut into a coin edge, a safe dial, a bullion
    press. Two crossed square waves with a little runout so it is machined
    rather than printed."""
    h, w = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    wob = (fbm((h, w), seed + 13, octaves=(8, 16, 32), weights=(1.0, .5, .3)) - 0.5) * wobble * pitch
    k = _TAU / (pitch * (w / 2048.0))
    a = np.deg2rad(angle)
    u = (xx * np.cos(a) + yy * np.sin(a)) + wob
    v = (-xx * np.sin(a) + yy * np.cos(a)) + wob
    d = np.abs(np.sin(u * k)) * np.abs(np.sin(v * k))
    return np.clip(np.power(d, 0.55) * float(relief), 0, 1).astype(np.float32)


def facets(shape, seed, stones=190, table=0.34, brilliance=1.5):
    """Brilliant-cut facets: flat planes meeting at hard edges, each throwing
    light in its own direction. Cells give the stones, a per-cell constant gives
    the flat plane, and the cell boundary gives the girdle."""
    h, w = int(shape[0]), int(shape[1])
    d, lab = worley((h, w), seed, cells=int(stones), kind="f1")
    lab = np.asarray(lab)
    plane = _h1(lab, 331)
    tab = (d < float(table)).astype(np.float32)
    out = plane * (0.55 + 0.45 * tab) + (1.0 - pct(d)) * 0.22
    if cv2 is not None:
        gy, gx = np.gradient(cv2.GaussianBlur(pct(d), (0, 0), 1.0))
        out = out + np.clip(np.hypot(gx, gy) * 40.0, 0, 1) * 0.5 * float(brilliance)
    return pct(out), lab


def bricks(shape, seed, rows=34, cols=6, bind=0.22, lean=0.5, offset=1.0):
    """Banded stacks — currency straps, bullion bars, cash bricks.

    `offset` is the difference between a STACK and a SHEET: bars and cash
    bricks are laid course over course out of register (offset 1), while a
    sheet of uncut notes is printed in perfect register (offset 0) and reads
    as masonry if you jitter it.
    """
    h, w = int(shape[0]), int(shape[1])
    r = rng(seed)
    out = np.zeros((h, w), np.float32)
    rh = h / float(max(rows, 1))
    for i in range(int(rows)):
        y0 = i * rh
        off = r.uniform(0, 1) * (w / float(cols)) * float(offset)
        for j in range(int(cols) + 2):
            x0 = j * (w / float(cols)) - off
            x1 = x0 + (w / float(cols)) * r.uniform(0.86, 0.98)
            y1 = y0 + rh * r.uniform(0.80, 0.94)
            sh = r.uniform(0.35, 0.95)
            xa, xb = int(max(0, x0)), int(min(w, x1))
            ya, yb = int(max(0, y0)), int(min(h, y1))
            if xb > xa and yb > ya:
                out[ya:yb, xa:xb] = sh
                bh = max(1, int((yb - ya) * bind))
                mid = ya + (yb - ya) // 2
                out[max(ya, mid - bh // 2):min(yb, mid + bh // 2), xa:xb] = 1.0
    if lean and cv2 is not None:
        out = cv2.warpAffine(out, np.float32([[1, float(lean) * 0.06, 0], [0, 1, 0]]), (w, h),
                             borderMode=cv2.BORDER_WRAP)
    return np.clip(out, 0, 1)


def shred(shape, seed, strips=150, curl_amt=26.0, gap=0.30):
    """Cross-cut shredder output: strips that have lost their register and
    started to curl. The BURN chapter's counterpart to bricks."""
    h, w = int(shape[0]), int(shape[1])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    wob = (fbm((h, w), seed + 17, octaves=(4, 8, 16, 64), weights=(1.0, .8, .5, .25)) - 0.5) * curl_amt
    period = w / float(max(strips, 1))
    u = np.mod(xx + wob, period) / period
    strip = (u > gap * 0.5) & (u < 1.0 - gap * 0.5)
    cut = (np.mod(yy + wob * 1.7, period * 3.4) > period * 3.4 * 0.22)
    tone = _h1(np.floor((xx + wob) / period).astype(np.int64)
               + 977 * np.floor((yy + wob * 1.7) / (period * 3.4)).astype(np.int64), 613)
    return np.clip((strip & cut).astype(np.float32) * (0.45 + 0.55 * tone), 0, 1)


def char(shape, seed, fronts=7, bite=1.5, ember=0.25):
    """A burning edge eating into paper: the scorch corona ahead of the front,
    the black crumble behind it."""
    h, w = int(shape[0]), int(shape[1])
    f = fbm((h, w), seed, octaves=(6, 12, 24, 48, 96, 192),
            weights=(1.0, .85, .7, .55, .4, .3))
    lvl = np.percentile(f, np.linspace(12, 88, int(fronts)))
    out = np.zeros((h, w), np.float32)
    for i, L in enumerate(lvl):
        d = np.abs(f - float(L))
        out = np.maximum(out, np.exp(-d * (60.0 * float(bite))) * (0.5 + 0.5 * (i / max(len(lvl) - 1, 1))))
    if ember:
        out = np.maximum(out, sparks((h, w), seed + 7, n=int(2200 * ember / 0.25),
                                     life=26, g=0.2, spread=1.2) * 0.85)
    return pct(out)


def watermark(shape, seed, scale=7.0, depth=0.68, laid=170.0, fibre=1.0):
    """Paper, not print: the pulp is thinner where the dandy roll pressed it, so
    a watermark is a THICKNESS field, and the laid lines of the mould run
    through everything on top of it."""
    h, w = int(shape[0]), int(shape[1])
    yy, _xx = np.mgrid[0:h, 0:w].astype(np.float32)
    _xx = _xx.astype(np.float32)
    base = fbm((h, w), seed,
               octaves=(int(scale), int(scale * 2), int(scale * 4),
                        int(scale * 10), int(scale * 22), int(scale * 44)),
               weights=(1.0, .6, .4, .5, .42, .3))
    lines = 0.5 + 0.5 * np.sin(yy * (_TAU * laid / max(h, 1)))
    chain = 0.5 + 0.5 * np.sin(_xx * (_TAU * (laid / 7.0) / max(w, 1)))
    lines = np.maximum(lines, chain * 0.75)
    out = pct(base) * (1.0 - depth) + lines * depth
    # THE FIBRE. Currency stock is cotton and linen rag, not wood pulp, and
    # you can see the individual fibres against a light. It also rescues the
    # card mechanically: cell_mean averages inside ~6px cells, which is the
    # laid-line period, so the mould lines alone get wiped before they reach
    # the spec. Fibre is shorter than a cell and survives.
    if fibre > 0:
        out = np.maximum(out, filaments((h, w), seed + 41, n=int(2600 * fibre),
                                        length=int(11 * w / 2048.0) + 4,
                                        wander=0.85, width=1.0) * 0.72)
    return np.clip(out, 0, 1).astype(np.float32)
