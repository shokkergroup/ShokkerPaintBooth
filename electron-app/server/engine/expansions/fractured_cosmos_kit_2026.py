# -*- coding: utf-8 -*-
"""FRACTURED COSMOS kit (2026-08-31) — off-planet field primitives.

Owner: the Fractured categories must be *unique, cool, and live up to what they
say they do*. COSMOS says off-planet, space, UFO. What was there was three
unrelated blocks: 20 genuinely on-theme, then **20 colour-name recolours**
(Cyan Drift / Cyan Dust Lane / Cyan Shockwave / Cyan Spiral, then the same four
in gilded, magenta, teal and violet — a 5x4 colour grid), then **20 iridescent
and holographic finishes with nothing to do with space at all** (Oil-Slick
Prism Shatter, Rainbow Truchet, Spectral Marble Flow…).

This kit supplies the things you can only see off Earth. Everything else —
cells, curl, filaments, dendrites, cracks, plates — is imported from the FLAMES
kit rather than rewritten, because a good primitive is a good primitive.
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

_TAU = 6.283185307179586


# ════════════════════════════════════════════════════════════════════════════
# THINGS YOU CAN ONLY SEE OFF EARTH
# ════════════════════════════════════════════════════════════════════════════

def starfield(shape, seed, n=2600, mag=2.2, spikes=0.06, glow=1.4):
    """Point sources drawn from a magnitude power law, a few with diffraction
    spikes. Real star fields are dominated by faint stars — a uniform-brightness
    scatter reads as noise, which is why the exponent matters more than the
    count."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = rng(seed)
    xs = r.integers(0, w, int(n))
    ys = r.integers(0, h, int(n))
    # power-law magnitudes: many faint, a handful bright
    b = (r.random(int(n)).astype(np.float32) ** float(mag))
    np.add.at(out, (ys, xs), b)
    if cv2 is None:
        return pct(out)
    out = cv2.GaussianBlur(out, (0, 0), float(glow) * 0.5)
    if spikes > 0:
        k = max(2, int(n * float(spikes)))
        sel = np.argsort(-b)[:k]
        sp = np.zeros((h, w), np.float32)
        for i in sel:
            x, y, v = int(xs[i]), int(ys[i]), float(b[i])
            L = max(3, int(6 + 26 * v))
            sp[max(0, y - L):y + L, x] += v
            sp[y, max(0, x - L):x + L] += v
        out = out + cv2.GaussianBlur(sp, (0, 0), 0.9) * 0.7
    return pct(out)


def craters(shape, seed, n=2600, rmin=1.6, rmax=8.5, rim=0.55, power=2.6):
    """Impact gardening: overlapping bowls with raised rims and ejecta, sizes
    drawn from a power law so small craters vastly outnumber large ones — the
    thing that makes a real regolith surface read as bombarded rather than
    dotted."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sizes = rmin + (rmax - rmin) * (r.random(int(n)).astype(np.float32) ** float(power))
    order = np.argsort(sizes)                                  # big ones first, small on top
    cx = r.random(int(n)).astype(np.float32) * w
    cy = r.random(int(n)).astype(np.float32) * h
    for i in order[::-1]:
        R = float(sizes[i])
        x0, x1 = int(max(0, cx[i] - 2.2 * R)), int(min(w, cx[i] + 2.2 * R))
        y0, y1 = int(max(0, cy[i] - 2.2 * R)), int(min(h, cy[i] + 2.2 * R))
        if x1 <= x0 or y1 <= y0:
            continue
        d = np.hypot(xx[y0:y1, x0:x1] - cx[i], yy[y0:y1, x0:x1] - cy[i]) / R
        bowl = -np.clip(1.0 - d * d, 0, 1) ** 0.6
        ring = np.exp(-((d - 1.0) * 3.2) ** 2) * float(rim)
        out[y0:y1, x0:x1] += bowl + ring
    return pct(out)


def bands(shape, seed, n=58, shear=2.6, vortex=34, turb=0.60):
    """Gas-giant zonal flow: alternating belts driven into each other by
    differential rotation, with vortices caught in the shear between them."""
    h, w = shape[0], shape[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = fbm((h, w), seed, octaves=(4, 8, 16, 32), weights=(1.0, 0.8, 0.55, 0.3))
    lat = yy / float(h) + (warp - 0.5) * 0.12
    belt = np.sin(lat * _TAU * float(n))
    # the shear itself drags the belts sideways
    drag = np.cumsum(np.sin(lat * _TAU * n * 0.5) * 0.02, axis=1)
    fine = fbm((h, w), seed + 11, octaves=(48, 96, 192, 384), weights=(0.5, 0.85, 1.0, 0.7))
    out = belt * 0.6 + np.sin(drag * shear + fine * _TAU) * 0.35
    if vortex and cv2 is not None:
        r = rng(seed + 3)
        v = np.zeros((h, w), np.float32)
        for _ in range(int(vortex)):
            R = 10.0 + 30.0 * r.random()
            cx_, cy_ = r.random() * w, r.random() * h
            rad = int(R * 2.6 + 3)                    # bounded, like every
            x0, x1 = int(max(0, cx_ - rad)), int(min(w, cx_ + rad))
            y0, y1 = int(max(0, cy_ - rad)), int(min(h, cy_ + rad))
            if x1 - x0 < 4 or y1 - y0 < 4:
                continue
            ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            d = np.hypot(lx - cx_, ly - cy_) / R
            a = np.arctan2(ly - cy_, lx - cx_)
            v[y0:y1, x0:x1] += np.exp(-d * d) * np.sin(a * 2.0 + d * 5.0)
        out = out + v * 0.5
    return pct(out * (1.0 - turb) + fine * turb)


def lens(shape, seed, masses=48, strength=26.0, background=None):
    """Gravitational lensing: a background field pulled into arcs and rings
    around a scatter of masses. The deflection falls off as 1/r, which is what
    makes the arcs tangential rather than radial."""
    h, w = shape[0], shape[1]
    bg = starfield((h, w), seed + 7, n=3200) if background is None else np.asarray(background, np.float32)
    r = rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = np.zeros((h, w), np.float32)
    dy = np.zeros((h, w), np.float32)
    for _ in range(int(masses)):
        cx_, cy_ = r.random() * w, r.random() * h
        m = float(strength) * (0.35 + 0.65 * r.random())
        ex, ey = xx - cx_, yy - cy_
        d2 = ex * ex + ey * ey + 36.0
        dx -= m * ex / d2 * 60.0
        dy -= m * ey / d2 * 60.0
    sx = np.clip(xx + dx, 0, w - 1).astype(np.int32)
    sy = np.clip(yy + dy, 0, h - 1).astype(np.int32)
    return pct(bg[sy, sx])


def rings(shape, seed, n=5, gaps=2, tilt=0.34, warp=0.05, systems=150):
    """Ring systems: fine ringlets with resonance gaps cut through them (the
    Cassini division is a gap, not a colour change).

    A FIELD of small systems, each evaluated only inside its own footprint. One
    centred ring set on a 2048 canvas is a single bullseye on a whole car —
    measured car-band 0.263 at 44% coverage — and evaluating each system over
    the entire canvas cost 4.9s, which is what kept the count low enough to be
    a poster in the first place."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = rng(seed)
    wob = (fbm((h, w), seed, octaves=(16, 32, 64)) - 0.5) * float(warp)
    for _ in range(int(systems)):
        cx_, cy_ = r.random() * w, r.random() * h
        R = (0.030 + 0.060 * r.random()) * min(h, w)
        x0, x1 = int(max(0, cx_ - 1.3 * R)), int(min(w, cx_ + 1.3 * R))
        y0, y1 = int(max(0, cy_ - 1.3 * R)), int(min(h, cy_ + 1.3 * R))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        ti = float(tilt) * (0.6 + 0.9 * r.random())
        a = r.random() * _TAU
        ex = ((lx - cx_) * np.cos(a) + (ly - cy_) * np.sin(a)) / R
        ey = (-(lx - cx_) * np.sin(a) + (ly - cy_) * np.cos(a)) / (R * max(ti, 0.05))
        d = np.hypot(ex, ey) + wob[y0:y1, x0:x1]
        rl = 0.5 + 0.5 * np.sin(d * _TAU * float(n))
        for _g in range(int(gaps)):
            g = 0.2 + 0.75 * r.random()
            rl = rl * (1.0 - np.exp(-((d - g) / (0.02 + 0.03 * r.random())) ** 2))
        np.maximum(out[y0:y1, x0:x1], rl * np.clip(1.15 - d, 0, 1),
                   out=out[y0:y1, x0:x1])
    return pct(out)


def crinkle(shape, seed, scale=120, sharp=2.6, folds=3):
    """Crumpled reflective foil — multi-layer insulation, a solar sail. The
    creases are the *ridges* of a folded surface, so the field is the absolute
    value of a signed height, taken a few times at different scales."""
    h, w = shape[0], shape[1]
    acc = np.zeros((h, w), np.float32)
    for i in range(int(folds)):
        f = fbm((h, w), seed + i * 131, octaves=(scale // 2 or 1, scale, scale * 2, scale * 4),
                weights=(0.5, 1.0, 0.75, 0.5)) - 0.5
        acc += (1.0 - np.abs(f) * 2.0) ** float(sharp) * (0.7 ** i)
    return pct(acc)


def honeycomb(shape, seed, cells=96, wall=0.16, jitter=0.06):
    """Hex cells — radiator panel, mirror segment array, whipple shield."""
    h, w = shape[0], shape[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s = float(w) / float(cells)
    q = (xx * (2.0 / 3.0)) / s
    rr = (-xx / 3.0 + (np.sqrt(3.0) / 3.0) * yy) / s
    j = (fbm((h, w), seed, octaves=(8, 16, 32)) - 0.5) * float(jitter) * 6.0
    q, rr = q + j, rr - j
    cq, cr = np.round(q), np.round(rr)
    cs = np.round(-q - rr)
    dq, dr, ds = np.abs(cq - q), np.abs(cr - rr), np.abs(cs + q + rr)
    edge = np.maximum(np.maximum(dq, dr), ds)
    # Hex axial coordinates are SIGNED, so a raw combination of them produces
    # negative labels — and every consumer of a label field (cell_mean, the
    # per-cell hashes) assumes labels index from zero. Fold to a positive range.
    # Hex axial coordinates are SIGNED, so a raw combination of them produces
    # negative labels, and every consumer of a label field assumes labels index
    # from zero. Return a DENSE range rather than a hash: sparse labels make
    # bincount allocate by the maximum value instead of the count.
    qi = (cq - cq.min()).astype(np.int64)
    ri = (cr - cr.min()).astype(np.int64)
    lab = ri * (int(qi.max()) + 1) + qi
    return pct(np.clip((edge - (0.5 - float(wall))) / max(wall, 1e-3), 0, 1)), lab


def jet(shape, seed, n=320, knots=9, spread=0.006, length=0.075):
    """Relativistic jets: collimated, knotty, terminating in a hot spot. Many
    small ones, each drawn only inside its own footprint — a handful of long
    jets is a poster (measured car-band 0.003 at 44% coverage)."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = rng(seed)
    for _ in range(int(n)):
        cx_, cy_ = r.random() * w, r.random() * h
        a = r.random() * _TAU
        ux, uy = np.cos(a), np.sin(a)
        L = float(length) * min(h, w) * (0.5 + r.random())
        rad = int(L + 6)
        x0, x1 = int(max(0, cx_ - rad)), int(min(w, cx_ + rad))
        y0, y1 = int(max(0, cy_ - rad)), int(min(h, cy_ + rad))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        t = (lx - cx_) * ux + (ly - cy_) * uy
        p = np.abs(-(lx - cx_) * uy + (ly - cy_) * ux)
        wid = float(spread) * min(h, w) * (0.35 + np.clip(t, 0, None) / max(L, 1))
        core = np.exp(-(p / np.maximum(wid, 0.7)) ** 2)
        core = np.where((t > 0) & (t < L), core, 0.0)
        kn = 0.55 + 0.65 * np.sin(t / max(L, 1) * _TAU * knots + r.random() * _TAU)
        np.maximum(out[y0:y1, x0:x1], core * kn, out=out[y0:y1, x0:x1])
    return pct(out)


def shockshell(shape, seed, n=260, thick=0.11, rag=0.7):
    """Expanding supernova shells: thin filamentary rims, ragged where the blast
    met denser gas. Many small remnants, each bounded — big shells put all the
    energy below the car band (measured 0.036)."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    r = rng(seed)
    warp = fbm((h, w), seed + 9, octaves=(32, 64, 128, 256)) - 0.5
    for _ in range(int(n)):
        cx_, cy_ = r.random() * w, r.random() * h
        R = (0.020 + 0.030 * r.random()) * min(h, w)
        rad = int(R * 1.6 + 3)
        x0, x1 = int(max(0, cx_ - rad)), int(min(w, cx_ + rad))
        y0, y1 = int(max(0, cy_ - rad)), int(min(h, cy_ + rad))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(lx - cx_, ly - cy_) / R + warp[y0:y1, x0:x1] * float(rag)
        np.maximum(out[y0:y1, x0:x1], np.exp(-((d - 1.0) / float(thick)) ** 2),
                   out=out[y0:y1, x0:x1])
    return pct(out)


def dunes(shape, seed, n=34, drift=0.42, crest=2.2):
    """Barchan dune fields: asymmetric ridges with a sharp slip face, all
    marching the same way because one wind made them."""
    h, w = shape[0], shape[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ph = fbm((h, w), seed, octaves=(6, 12, 24, 48), weights=(1.0, 0.8, 0.5, 0.3))
    u = xx / float(w) * float(n) + ph * float(drift) * n
    s = u - np.floor(u)
    ridge = np.clip(1.0 - np.abs(s * 2.0 - 0.7) ** float(crest), 0, 1)
    fine = fbm((h, w), seed + 5, octaves=(128, 256, 512), weights=(0.6, 1.0, 0.7))
    return pct(ridge * 0.8 + fine * 0.45)


def polygons(shape, seed, cells=70, width=2.0, relief=0.5):
    """Desiccation / thermal-contraction polygons — salt flats, permafrost,
    the floor of a dry lake on any world."""
    d, lab = worley(shape, seed, cells=cells, kind="f2f1")
    seam = np.exp(-(d * cells / 11.0) ** 2 / max(width, 0.2))
    body = (1.0 - d) * float(relief) + _h1(lab, 17) * 0.5
    return pct(seam * 0.9 + body * 0.6), lab


def glyphs(shape, seed, n=520, stroke=2.0, size=16.0):
    """Angular xeno script: short straight strokes, arcs and pips on a jittered
    baseline. Written, not scattered — strokes cluster into words."""
    h, w = shape[0], shape[1]
    out = np.zeros((h, w), np.float32)
    if cv2 is None:
        return out
    r = rng(seed)
    for _ in range(int(n)):
        bx, by = r.random() * w, r.random() * h
        for _s in range(int(2 + 4 * r.random())):
            L = size * (0.4 + 0.9 * r.random())
            a = (np.pi / 4.0) * r.integers(0, 8)
            x0, y0 = bx + r.random() * size, by + r.random() * size * 0.6
            x1, y1 = x0 + np.cos(a) * L, y0 + np.sin(a) * L
            cv2.line(out, (int(x0) % w, int(y0) % h), (int(x1) % w, int(y1) % h),
                     float(0.5 + 0.5 * r.random()), int(max(1, stroke)))
        if r.random() < 0.4:
            cv2.circle(out, (int(bx + size) % w, int(by) % h),
                       int(max(1, size * 0.16)), float(0.7), -1)
    return pct(cv2.GaussianBlur(out, (0, 0), 0.7))


def hull(shape, seed, panels=76, seam=1.4, rivets=0.55, wear=0.35):
    """Machined ship plating: irregular panels, recessed seams, fastener rows
    and the polish differences between neighbouring plates."""
    d, lab = worley(shape, seed, cells=panels, kind="f2f1")
    seams = np.exp(-(d * panels / 9.0) ** 2 / max(seam, 0.2))
    plate = _h1(lab, 23) * float(wear)
    grain = fbm(shape, seed + 3, octaves=(96, 192, 384), weights=(0.6, 1.0, 0.7)) * 0.35
    out = (1.0 - seams) * (0.55 + plate) + grain
    if rivets > 0 and cv2 is not None:
        r = rng(seed + 5)
        h, w = shape[0], shape[1]
        pts = np.zeros((h, w), np.float32)
        step = max(6, int(min(h, w) / (panels * 1.6)))
        for y in range(0, h, step * 3):
            for x in range(0, w, step):
                if r.random() < 0.5:
                    pts[y % h, x % w] = 1.0
        out = out + cv2.GaussianBlur(pts, (0, 0), 1.1) * float(rivets) * (1.0 - seams)
    return pct(out), lab
