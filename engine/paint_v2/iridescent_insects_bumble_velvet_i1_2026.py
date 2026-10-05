"""Bumble Velvet I1 — directional Bombus pile over glimpsed black chitin.

IRIDESCENT INSECTS tick 28 / owner identity law 2026-09-01.
Identity contract: the carrier is built from thousands of individually drawn,
socketed 8–24px native setae gathered into locally coherent nap packets.  Each
shaft has a tapered highlight and selected hairs carry forked/pectinate barbs;
comb fringes, exposed chitin slits, pollen hooks and burnished nap changes add
four further named mark families.  Ochre and black emerge from interlocking
hair populations, never from broad stripes.  Honeycomb, dots, scale wallpaper,
random fur noise and palette-only variants are prohibited.  M/R/Cc are bound
to shaft pigment, barb density, chitin exposure, sockets and pollen attachment.

Research: Lopez-Uribe et al., PeerJ 2022, "The diversity, evolution, and
development of setal morphologies in bumble bees" documents socketed,
single-celled branched setae, body-region-specific simple/branched/pectinate
forms and base-to-tip darkening; Thorp's pollen-capture model links branching
to increased collection area.  The polished corbicular plate and inward-curved
fringe inspire the sparse chitin slits and attached comb fans.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

GEN = 720


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape)
    a = np.asarray(a, np.float32)
    if a.shape[:2] == (h, w):
        return a
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .97, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(colour, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


def _stroke(dst, points, value=1.0, width=1):
    cv2.polylines(dst, [np.asarray(points, np.int32)], False, float(value), width, cv2.LINE_AA)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0xB00B1E)
    h = w = GEN
    under = np.zeros((h, w), np.float32)
    ochre = np.zeros_like(under)
    sable = np.zeros_like(under)
    shaft = np.zeros_like(under)
    tip = np.zeros_like(under)
    barb = np.zeros_like(under)
    comb = np.zeros_like(under)
    chitin = np.zeros_like(under)
    socket = np.zeros_like(under)
    pollen = np.zeros_like(under)
    burnish = np.zeros_like(under)

    # Fine, coherent nap packets.  A hidden low-frequency field chooses local
    # setal population and direction but is never itself rendered as wallpaper.
    step = 6.1
    for gy, y0 in enumerate(np.arange(-3.0, h + 4.0, step)):
        for x0 in np.arange(-3.0, w + 4.0, step):
            x = float(x0 + rng.uniform(-2.0, 2.0))
            y = float(y0 + rng.uniform(-2.0, 2.0))
            flow = (.54 * np.sin(x / 71.0 + .43 * np.sin(y / 113.0)) +
                    .31 * np.cos(y / 89.0 - x / 137.0) +
                    .15 * np.sin((x + 1.7 * y) / 53.0))
            theta = -.34 + .72 * flow + rng.normal(0, .16)
            pop = np.sin(x / 119.0 + y / 167.0) + .62 * np.cos(y / 83.0 - x / 151.0)
            is_ochre = pop + rng.normal(0, .48) > .08
            length = rng.uniform(3.2, 7.6)  # 9–22px after 2048² expansion.
            curve = rng.normal(0, .65)
            x1, y1 = x - .46 * length * np.cos(theta), y - .46 * length * np.sin(theta)
            x3, y3 = x + .54 * length * np.cos(theta), y + .54 * length * np.sin(theta)
            nx, ny = -np.sin(theta), np.cos(theta)
            x2, y2 = (x1 + x3) * .5 + nx * curve, (y1 + y3) * .5 + ny * curve
            pts = [(round(x1), round(y1)), (round(x2), round(y2)), (round(x3), round(y3))]
            strength = rng.uniform(.40, 1.0)
            _stroke(under, pts, .48 + .32 * strength, 1)
            _stroke(ochre if is_ochre else sable, pts, strength, 1)

            # Each hair receives a short off-axis sheen, not a global texture.
            hx = x2 + .18 * length * np.cos(theta)
            hy = y2 + .18 * length * np.sin(theta)
            _stroke(shaft, [(round(x2), round(y2)), (round(hx), round(hy))],
                    rng.uniform(.35, 1.0), 1)
            if rng.random() < .31:
                cv2.circle(tip, (int(round(x3)), int(round(y3))), 1,
                           float(rng.uniform(.32, .92)), -1, cv2.LINE_AA)

            # Branched/pectinate setae: barbs stay physically attached to a
            # shaft and remain 8–16px native, never floating confetti.
            if rng.random() < .24:
                side = -1 if rng.random() < .5 else 1
                for frac in (.43, .68):
                    bx = x1 + frac * (x3 - x1)
                    by = y1 + frac * (y3 - y1)
                    bl = rng.uniform(2.8, 4.9)
                    ba = theta + side * rng.uniform(.72, 1.12)
                    _stroke(barb, [(round(bx), round(by)),
                                   (round(bx + bl * np.cos(ba)), round(by + bl * np.sin(ba)))],
                            rng.uniform(.42, 1.0), 1)
                    side *= -1

    # Polished, elongated chitin exposures interrupt the pile.  They are
    # slits/plates rather than dots or a second honeycomb architecture.
    for _ in range(86):
        cx, cy = rng.integers(10, w - 10), rng.integers(10, h - 10)
        angle = rng.uniform(-.9, .9)
        length = rng.uniform(8.0, 15.0)
        p1 = (round(cx - length * np.cos(angle)), round(cy - length * np.sin(angle)))
        p2 = (round(cx + length * np.cos(angle)), round(cy + length * np.sin(angle)))
        _stroke(chitin, [p1, (cx, cy), p2], rng.uniform(.55, 1.0), rng.choice([1, 2]))
        # Socket collars remain short crescents attached to plate lips.
        cv2.ellipse(socket, (int(cx), int(cy)), (rng.integers(2, 5), rng.integers(1, 3)),
                    np.degrees(angle), 205, 338, float(rng.uniform(.45, .95)), 1, cv2.LINE_AA)

    # Sparse inward-curving comb fringes, assembled from individual attached
    # hairs.  These produce readable biological accents without macro bands.
    for _ in range(48):
        cx, cy = rng.integers(12, w - 12), rng.integers(12, h - 12)
        angle = rng.uniform(-np.pi, np.pi)
        for j in range(rng.integers(3, 7)):
            off = (j - 2.5) * 2.2
            nx, ny = -np.sin(angle), np.cos(angle)
            sx, sy = cx + off * nx, cy + off * ny
            length = rng.uniform(5.5, 10.0)
            ex, ey = sx + length * np.cos(angle), sy + length * np.sin(angle)
            mx, my = (sx + ex) / 2 + 1.4 * nx, (sy + ey) / 2 + 1.4 * ny
            _stroke(comb, [(round(sx), round(sy)), (round(mx), round(my)),
                           (round(ex), round(ey))], rng.uniform(.45, 1.0), 1)

    # Pollen appears only at hooked/branched pile intersections.
    intersections = np.argwhere((barb > .28) & (under > .24))
    if len(intersections):
        pick = intersections[rng.choice(len(intersections), min(190, len(intersections)), replace=False)]
        for py, px in pick:
            rr = int(rng.integers(1, 3))
            cv2.ellipse(pollen, (int(px), int(py)), (rr + 1, rr), rng.uniform(0, 180),
                        0, 360, float(rng.uniform(.38, 1.0)), -1, cv2.LINE_AA)

    # Short burnished nap changes align with, and selectively compress, pile.
    for _ in range(150):
        cx, cy = rng.integers(5, w - 5), rng.integers(5, h - 5)
        angle = -.2 + .65 * np.sin(cx / 83.0 + cy / 121.0)
        ln = rng.uniform(4.0, 9.0)
        _stroke(burnish, [(round(cx - ln * np.cos(angle)), round(cy - ln * np.sin(angle))),
                          (round(cx + ln * np.cos(angle)), round(cy + ln * np.sin(angle)))],
                rng.uniform(.30, .85), 1)

    arrays = (under, ochre, sable, shaft, tip, barb, comb, chitin, socket, pollen, burnish)
    # P3 preserves the accepted P2 construction while retaining a crisper
    # 8–16px native barb/shaft edge for whole-car readability.
    return tuple(cv2.GaussianBlur(a, (0, 0), .15).astype(np.float32) for a in arrays)


def paint_bumble_velvet_i1(paint, shape, mask, seed, pm, bb):
    under, ochre, sable, shaft, tip, barb, comb, chitin, socket, pollen, burnish = _surface(seed + 28117)
    col = np.zeros((*under.shape, 3), np.float32)
    col[:] = np.array([.020, .014, .020], np.float32)
    # P2 increases shaft-to-underfur contrast so the fine pile remains legible
    # on a whole-car carrier; density and native scale are unchanged.
    col += under[..., None] * np.array([.12, .075, .045], np.float32) * .76
    col += sable[..., None] * np.array([.11, .065, .15], np.float32) * .90
    col += ochre[..., None] * np.array([.89, .46, .045], np.float32) * .98
    col += shaft[..., None] * np.array([1.00, .82, .34], np.float32) * .48
    col += tip[..., None] * np.array([1.00, .94, .69], np.float32) * .52
    col += barb[..., None] * np.array([.38, .21, .07], np.float32) * .52
    col += comb[..., None] * np.array([.78, .48, .12], np.float32) * .70
    col += chitin[..., None] * np.array([.02, .18, .25], np.float32) * .98
    col += socket[..., None] * np.array([.30, .48, .54], np.float32) * .85
    col += pollen[..., None] * np.array([1.00, .79, .08], np.float32) * .94
    col += burnish[..., None] * np.array([.22, .12, .055], np.float32) * .34
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_bumble_velvet_i1(shape, seed, sm, base_m, base_r):
    under, ochre, sable, shaft, tip, barb, comb, chitin, socket, pollen, burnish = _surface(seed + 28117)
    # P2 separates material ownership: metallic belongs to exposed chitin and
    # ochre pigment; roughness to underfur/barbs/pollen; clearcoat to shaft
    # tips, burnished nap and comb fringes.  Shared silhouettes are subordinate.
    m = 8 + 238 * (.39 * chitin + .25 * socket + .20 * ochre +
                   .10 * pollen + .06 * shaft)
    r = 15 + 225 * (.36 * under + .25 * barb + .18 * sable +
                    .13 * pollen + .08 * comb)
    cc = 5 + 244 * (.34 * tip + .27 * shaft + .19 * burnish +
                    .13 * comb + .07 * chitin)
    m += chitin * 42 + socket * 29 - barb * 19 - under * 12
    r += barb * 34 + pollen * 27 - chitin * 31 - tip * 18
    cc += tip * 39 + shaft * 26 + burnish * 21 - sable * 17 - pollen * 11

    def spread(a, lo, hi):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        return np.clip(lo + (a - p1) * ((hi - lo) / max(float(p99 - p1), 1e-5)), lo, hi)

    # P4 keeps a near-full channel span while avoiding artificial 0/255 clipping
    # that made the material response louder than its already-dense paint pile.
    return (np.clip(_resize(spread(m, 3, 250) * sm, shape), 3, 250),
            np.clip(_resize(spread(r, 5, 248), shape), 5, 248),
            np.clip(_resize(spread(cc, 1, 252), shape), 1, 252))
