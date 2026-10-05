"""Wasp Signal I2 — aposematic duplex-lamella signal cuticle.

IRIDESCENT INSECTS tick 29 / owner identity law 2026-09-01.
Identity contract: yellow/black warning structure must emerge from thousands of
individually tapered 8–24px native duplex cuticle lamellae, not broad painted
stripes.  The compact lamella packets follow broken, branching signal fronts;
packed pigment granules, serrated segment lips, pentagonal rosettes with central
pores, attached setae and rare tracheal slits add six named mark families.
It may not resemble Bumble Velvet's directional hairs, Bee Venturi's cells,
Tiger Moth's scale rivers, a checker/chevron wallpaper, or a recolor.  M/R/Cc
trace yellow granules, black endocuticle, lamella lips, pores and setae.

Research: Ishay et al. 2000 describe Oriental-hornet gastral cuticle as duplex
chitin/protein lamellae perforated by photoreceptor pores, tracheal tubules and
nerve fibres.  Garcia et al. 2020 report pentagonal/hexagonal epicuticle
rosettes, central pores and pore-borne setae in micro-wasps, with pigment
concentrated near the epicuticle.  Polistes/Vespula microscopy distinguishes
packed yellow hypocuticle granules from parallel black endocuticle layers.
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
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .97, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(colour, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


def _poly(dst, pts, value):
    cv2.fillConvexPoly(dst, np.asarray(pts, np.int32), float(value), cv2.LINE_AA)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0xA90519)
    h = w = GEN
    yellow = np.zeros((h, w), np.float32)
    black = np.zeros_like(yellow)
    outer = np.zeros_like(yellow)
    inner = np.zeros_like(yellow)
    lip = np.zeros_like(yellow)
    granule = np.zeros_like(yellow)
    rosette = np.zeros_like(yellow)
    pore = np.zeros_like(yellow)
    seta = np.zeros_like(yellow)
    trachea = np.zeros_like(yellow)
    bruise = np.zeros_like(yellow)

    # P3 discards both earlier stripe fields.  A small number of connected,
    # angular aposematic graphs now route the yellow population; the graph is
    # invisible and only selects individual duplex plates.  Thus the visible
    # construction is a field of 10–28px armor tiles, never a macro stroke.
    signal = np.zeros((h, w), np.uint8)
    # P4 replaces P3's wandering graph (unique but visually arbitrary) with
    # connected chains of nested tergite chevrons: unmistakable warning grammar
    # built from abdominal-segment silhouettes rather than decorative zigzags.
    for _ in range(38):
        cx, cy = float(rng.integers(-20, w + 20)), float(rng.integers(-20, h + 20))
        travel = rng.choice(np.array([-.70, -.18, .18, .70, 1.40, -1.40]))
        for j in range(rng.integers(5, 10)):
            facing = travel + rng.choice([-1, 1]) * rng.uniform(.72, 1.02)
            size = rng.uniform(9.0, 18.0)
            ux, uy = np.cos(facing), np.sin(facing)
            nx, ny = -uy, ux
            apex = (round(cx + size * ux), round(cy + size * uy))
            left = (round(cx - .45 * size * ux + .82 * size * nx),
                    round(cy - .45 * size * uy + .82 * size * ny))
            right = (round(cx - .45 * size * ux - .82 * size * nx),
                     round(cy - .45 * size * uy - .82 * size * ny))
            cv2.polylines(signal, [np.asarray([left, apex, right], np.int32)], False,
                          255, int(rng.integers(8, 14)), cv2.LINE_AA)
            if j % 3 == 1:
                # A short inner duplex wall makes a two-tier signal shield.
                inner_pts = np.asarray([
                    (round(cx - .05 * size * ux + .38 * size * nx),
                     round(cy - .05 * size * uy + .38 * size * ny)),
                    (round(cx + .48 * size * ux), round(cy + .48 * size * uy)),
                    (round(cx - .05 * size * ux - .38 * size * nx),
                     round(cy - .05 * size * uy - .38 * size * ny)),
                ], np.int32)
                cv2.polylines(signal, [inner_pts], False, 255, int(rng.integers(5, 9)), cv2.LINE_AA)
            stride = rng.uniform(17.0, 28.0)
            cx += stride * np.cos(travel); cy += stride * np.sin(travel)
            travel += rng.uniform(-.12, .12)
    edge = cv2.morphologyEx(signal, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))

    step_x, step_y = 8.0, 7.4
    for row, y0 in enumerate(np.arange(-4.0, h + 5.0, step_y)):
        for x0 in np.arange(-4.0, w + 5.0, step_x):
            cx = float(x0 + rng.uniform(-1.7, 1.7))
            cy = float(y0 + rng.uniform(-1.5, 1.5))
            ix, iy = int(np.clip(round(cx), 0, w - 1)), int(np.clip(round(cy), 0, h - 1))
            is_yellow = signal[iy, ix] > 40
            angle = (-.21 if (row + int(cx // 53)) % 2 else .17) + rng.uniform(-.13, .13)
            ln = rng.uniform(3.1, 5.0)
            half = rng.uniform(1.55, 2.45)
            ux, uy = np.cos(angle), np.sin(angle)
            nx, ny = -uy, ux
            taper = rng.uniform(.62, .90)
            pts = [
                (round(cx - ln * ux - half * nx), round(cy - ln * uy - half * ny)),
                (round(cx + ln * ux - half * taper * nx), round(cy + ln * uy - half * taper * ny)),
                (round(cx + ln * ux + half * taper * nx), round(cy + ln * uy + half * taper * ny)),
                (round(cx - ln * ux + half * nx), round(cy - ln * uy + half * ny)),
            ]
            strength = rng.uniform(.42, 1.0)
            target = yellow if is_yellow else black
            _poly(target, pts, strength)
            # Duplex wall: outer and inner walls occupy opposite tile edges.
            p1 = (round(cx - ln * ux - half * nx), round(cy - ln * uy - half * ny))
            p2 = (round(cx + ln * ux - half * taper * nx), round(cy + ln * uy - half * taper * ny))
            p3 = (round(cx - ln * ux + half * nx), round(cy - ln * uy + half * ny))
            p4 = (round(cx + ln * ux + half * taper * nx), round(cy + ln * uy + half * taper * ny))
            cv2.line(outer, p1, p2, float(rng.uniform(.34, .95)), 1, cv2.LINE_AA)
            cv2.line(inner, p3, p4, float(rng.uniform(.28, .88)), 1, cv2.LINE_AA)
            if edge[iy, ix] > 40:
                cv2.line(lip, p1, p2, float(rng.uniform(.48, 1.0)), 1, cv2.LINE_AA)
            if is_yellow and rng.random() < .42:
                # Pigment granules are short attached chains, not loose dots.
                gx = cx - .35 * ln * ux
                for g in range(rng.integers(2, 5)):
                    px = round(gx + g * 1.55 * ux + rng.uniform(-.4, .4) * nx)
                    py = round(cy + g * 1.55 * uy + rng.uniform(-.4, .4) * ny)
                    cv2.ellipse(granule, (px, py), (1, 1), 0, 0, 360,
                                float(rng.uniform(.38, .92)), -1, cv2.LINE_AA)

    # Sparse epicuticle rosettes are pentagonal and tied to a pore/seta; their
    # rarity keeps them anatomical punctuation rather than bubble wallpaper.
    for _ in range(210):
        cx, cy = int(rng.integers(6, w - 6)), int(rng.integers(6, h - 6))
        radius = rng.uniform(2.0, 3.8)
        rot = rng.uniform(0, np.pi * 2)
        pts = [(round(cx + radius * np.cos(rot + k * 2 * np.pi / 5)),
                round(cy + radius * np.sin(rot + k * 2 * np.pi / 5))) for k in range(5)]
        cv2.polylines(rosette, [np.asarray(pts, np.int32)], True,
                      float(rng.uniform(.38, .92)), 1, cv2.LINE_AA)
        cv2.circle(pore, (cx, cy), 1, float(rng.uniform(.45, 1.0)), -1, cv2.LINE_AA)
        if rng.random() < .42:
            angle = rng.uniform(-np.pi, np.pi); ln = rng.uniform(3.2, 6.8)
            cv2.line(seta, (cx, cy), (round(cx + ln * np.cos(angle)), round(cy + ln * np.sin(angle))),
                     float(rng.uniform(.35, .92)), 1, cv2.LINE_AA)

    # Rare tracheal slits and bruised pigment packets remain elongated.
    for _ in range(92):
        cx, cy = int(rng.integers(8, w - 8)), int(rng.integers(8, h - 8))
        angle = rng.uniform(-.7, .7); ln = rng.uniform(3.0, 7.0)
        cv2.ellipse(trachea, (cx, cy), (round(ln), 1), np.degrees(angle), 0, 360,
                    float(rng.uniform(.35, .95)), 1, cv2.LINE_AA)
        if rng.random() < .58:
            cv2.line(bruise, (round(cx - ln * np.cos(angle)), round(cy - ln * np.sin(angle))),
                     (round(cx + ln * np.cos(angle)), round(cy + ln * np.sin(angle))),
                     float(rng.uniform(.28, .75)), 1, cv2.LINE_AA)

    arrays = (yellow, black, outer, inner, lip, granule, rosette, pore, seta, trachea, bruise)
    return tuple(cv2.GaussianBlur(a, (0, 0), .18).astype(np.float32) for a in arrays)


def paint_wasp_warning_i2(paint, shape, mask, seed, pm, bb):
    yellow, black, outer, inner, lip, granule, rosette, pore, seta, trachea, bruise = _surface(seed + 29021)
    col = np.zeros((*yellow.shape, 3), np.float32)
    col[:] = np.array([.018, .014, .012], np.float32)
    col += black[..., None] * np.array([.055, .075, .095], np.float32) * .86
    col += yellow[..., None] * np.array([.98, .60, .025], np.float32) * .96
    col += outer[..., None] * np.array([.96, .78, .24], np.float32) * .22
    col += inner[..., None] * np.array([.22, .12, .035], np.float32) * .27
    col += lip[..., None] * np.array([1.00, .82, .30], np.float32) * .73
    col += granule[..., None] * np.array([1.00, .91, .44], np.float32) * .64
    col += rosette[..., None] * np.array([.30, .15, .035], np.float32) * .71
    col += pore[..., None] * np.array([.015, .025, .035], np.float32) * .96
    col += seta[..., None] * np.array([.76, .54, .18], np.float32) * .63
    col += trachea[..., None] * np.array([.05, .34, .42], np.float32) * .76
    col += bruise[..., None] * np.array([.47, .07, .028], np.float32) * .53
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_wasp_warning_i2(shape, seed, sm, base_m, base_r):
    yellow, black, outer, inner, lip, granule, rosette, pore, seta, trachea, bruise = _surface(seed + 29021)
    m = 7 + 238 * (.34 * outer + .24 * lip + .16 * trachea +
                   .12 * granule + .08 * yellow + .06 * rosette)
    r = 14 + 224 * (.31 * black + .22 * inner + .17 * pore +
                    .13 * seta + .10 * bruise + .07 * rosette)
    cc = 5 + 244 * (.30 * yellow + .23 * granule + .18 * lip +
                    .13 * outer + .09 * trachea + .07 * seta)
    m += outer * 32 + trachea * 27 - pore * 24 - black * 12
    r += pore * 33 + inner * 24 + seta * 19 - lip * 28
    cc += granule * 31 + lip * 25 - bruise * 18 - black * 11

    def spread(a, lo, hi):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        return np.clip(lo + (a - p1) * ((hi - lo) / max(float(p99 - p1), 1e-5)), lo, hi)

    # P5 keeps broad but not artificially clipped spans so the material signal
    # remains proportionate to the compact paint plates.
    # P6 retains 231/181/171 distinct channel levels but avoids making the
    # roughness and clearcoat maps louder than the compact signal-plate paint.
    return (np.clip(_resize(spread(m, 12, 242) * sm, shape), 12, 242),
            np.clip(_resize(spread(r, 37, 217), shape), 37, 217),
            np.clip(_resize(spread(cc, 42, 212), shape), 42, 212))
