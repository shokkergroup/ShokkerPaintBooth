"""Mayfly Silverstream I1 — alternating corrugation veins and flex bullae.

IRIDESCENT INSECTS tick 26 / owner identity law 2026-09-01.
Identity contract: alternating convex/concave longitudinal veins, intercalary
forks, numerous minute cross-veins and aligned oval bullae must be legible in
grayscale.  The carrier cannot be Cicada's wandering ladders, Lacewing's
diagonal fan, or a generic pinstripe.  M/R/Cc follow crest, trough, tie, fork,
bulla, rim and membrane facets.  Source: Staniczek et al. 2023 documents fully
corrugated Ephemeroptera wings, alternating positive/negative veins, numerous
cross-veins, intercalary veins, and desclerotized bullae on concave veins.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

GEN = 576


def _hw(shape): return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape); a = np.asarray(a, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, col):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    a = np.clip(mask * pm * .96, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(col, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


@lru_cache(maxsize=2)
def _surface(seed):
    s = GEN / 1024.0
    rng = np.random.default_rng(int(seed) ^ 0xE0F1A)
    crest = np.zeros((GEN, GEN), np.float32)
    crest_core = np.zeros_like(crest)
    trough = np.zeros_like(crest)
    tie = np.zeros_like(crest)
    fork = np.zeros_like(crest)
    bulla = np.zeros_like(crest)
    bulla_rim = np.zeros_like(crest)
    facet = np.zeros_like(crest)

    def pt(xv, yv): return int(round(xv * s)), int(round(yv * s))

    tracks = []
    y0 = -30.0; index = 0
    while y0 < 1060:
        xs = np.arange(-40.0, 1064.0, 9.0)
        phase = rng.uniform(0, np.pi * 2)
        slope = rng.uniform(-.045, .055)
        ys = y0 + slope * xs + rng.uniform(1.2, 3.6) * np.sin(xs / rng.uniform(24, 51) + phase)
        ys += rng.uniform(.5, 1.7) * np.sin(xs / rng.uniform(8, 16) - phase * .37)
        pts = np.array([pt(a, b) for a, b in zip(xs, ys)], np.int32)
        positive = index % 2 == 0
        target = crest if positive else trough
        cv2.polylines(target, [pts], False, rng.uniform(.62, .96),
                      max(1, int(round((2.7 if positive else 2.0) * s))), cv2.LINE_AA)
        if positive:
            cv2.polylines(crest_core, [pts], False, 1.0,
                          max(1, int(round(.82 * s))), cv2.LINE_AA)
        tracks.append((xs, ys, positive))
        y0 += rng.uniform(10.5, 16.8)
        index += 1

    # Irregular cross-veins and retained intercalary forks break any textile
    # cadence.  Every segment is 8–30px native and terminates on a named vein.
    for i in range(len(tracks) - 1):
        xs, ys, positive = tracks[i]; xs2, ys2, _ = tracks[i + 1]
        xv = rng.uniform(-10, 18)
        while xv < 1040:
            j = int(np.argmin(np.abs(xs - xv)))
            if rng.random() > .72:
                xa, ya = float(xs[j]), float(ys[j]); yb = float(ys2[j])
                lean = rng.uniform(-3.5, 3.5)
                path = np.array([pt(xa, ya), pt(xa + lean, (ya + yb) * .5), pt(xa, yb)], np.int32)
                cv2.polylines(tie, [path], False, rng.uniform(.45, .88),
                              max(1, int(round(1.15 * s))), cv2.LINE_AA)
                if positive and rng.random() > .72:
                    length = rng.uniform(6.0, 14.0)
                    v = np.array([pt(xa, ya), pt(xa + length, ya - rng.uniform(5, 10)),
                                  pt(xa + length, ya + rng.uniform(5, 10))], np.int32)
                    cv2.polylines(fork, [v], False, 1.0, max(1, int(round(1.3 * s))), cv2.LINE_AA)
            xv += rng.uniform(11.0, 22.0)

    # Flexible bullae align across selected concave veins in several broken,
    # oblique flex rows.  They interrupt trough material rather than float.
    for row_x in (rng.uniform(120, 230), rng.uniform(470, 610), rng.uniform(790, 910)):
        for i, (xs, ys, positive) in enumerate(tracks):
            if positive or i % 3 == 0: continue
            xv = row_x + i * rng.uniform(.45, 1.10) + rng.uniform(-4, 4)
            j = int(np.argmin(np.abs(xs - xv))); yv = float(ys[j])
            axes = (max(1, int(round(rng.uniform(3.0, 5.2) * s))),
                    max(1, int(round(rng.uniform(1.6, 2.8) * s))))
            cv2.ellipse(bulla, pt(xv, yv), axes, rng.uniform(-12, 12), 0, 360, 1.0, -1, cv2.LINE_AA)
            cv2.ellipse(bulla_rim, pt(xv, yv), axes, rng.uniform(-12, 12), 0, 360, 1.0, 1, cv2.LINE_AA)

    # Fine alternating corrugation facets hug crest/trough relief.
    y, x = coords(GEN); x, y = x / s, y / s
    micro = n01(np.sin((x + .18 * y) / 4.6) + .52 * np.cos((.31 * x - y) / 7.8))
    relief = np.clip(crest + trough, 0, 1)
    facet = np.clip((micro - .43) * 1.75, 0, 1) * cv2.GaussianBlur(relief, (0, 0), 1.8)
    crest = cv2.GaussianBlur(crest, (0, 0), .36); crest_core = cv2.GaussianBlur(crest_core, (0, 0), .25)
    trough = cv2.GaussianBlur(trough, (0, 0), .34); tie = cv2.GaussianBlur(tie, (0, 0), .28)
    fork = cv2.GaussianBlur(fork, (0, 0), .26); bulla = cv2.GaussianBlur(bulla, (0, 0), .30)
    bulla_rim = cv2.GaussianBlur(bulla_rim, (0, 0), .24)

    # Quiet, nonperiodic membrane thickness—subordinate to corrugation anatomy.
    raw = cv2.resize(rng.random((84, 84), dtype=np.float32), (GEN, GEN), interpolation=cv2.INTER_CUBIC)
    membrane = cv2.GaussianBlur(raw, (0, 0), 3.0)
    return tuple(np.asarray(a, np.float32) for a in
                 (crest, crest_core, trough, tie, fork, bulla, bulla_rim, facet, membrane))


def paint_mayfly_silver_i1(paint, shape, mask, seed, pm, bb):
    crest, core, trough, tie, fork, bulla, brim, facet, membrane = _surface(seed + 62003)
    col = np.zeros((*crest.shape, 3), np.float32)
    col[:] = np.array([.07, .105, .13], np.float32)
    col += membrane[..., None] * np.array([.22, .32, .40], np.float32) * .56
    # P3 breaks the crest highlight into attached corrugation facets.  The
    # underlying vein stays continuous but no longer reads as textile thread.
    col += crest[..., None] * np.array([.20, .34, .48], np.float32) * .32
    col += (crest * facet)[..., None] * np.array([.66, .76, .81], np.float32) * .78
    col += core[..., None] * np.array([.43, .60, .69], np.float32) * .24
    col += (core * (.25 + .75 * facet))[..., None] * np.array([.84, .91, .92], np.float32) * .50
    col += trough[..., None] * np.array([.08, .16, .28], np.float32) * .58
    col += tie[..., None] * np.array([.25, .48, .69], np.float32) * .54
    col += fork[..., None] * np.array([.72, .47, .16], np.float32) * .82
    col += bulla[..., None] * np.array([.12, .36, .51], np.float32) * .56
    col += brim[..., None] * np.array([.68, .90, .94], np.float32) * .88
    col += facet[..., None] * np.array([.36, .56, .66], np.float32) * .34
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_mayfly_silver_i1(shape, seed, sm, base_m, base_r):
    crest, core, trough, tie, fork, bulla, brim, facet, membrane = _surface(seed + 62003)
    m = 18 + 220 * (.28 * crest + .22 * core + .15 * fork + .11 * brim +
                    .09 * facet + .08 * tie + .07 * membrane)
    r = 16 + 216 * (.27 * trough + .20 * tie + .17 * bulla + .13 * (1 - membrane) +
                    .10 * facet + .08 * fork + .05 * (1 - core))
    cc = 14 + 230 * (.25 * membrane + .22 * brim + .16 * core + .13 * bulla +
                     .10 * tie + .08 * crest + .06 * facet)
    m += core * 26 + fork * 18 - bulla * 15
    r += trough * 24 + bulla * 18 - brim * 21
    cc += brim * 28 + bulla * 17 - trough * 12
    for a, target in ((m, 28.0), (r, 25.0), (cc, 29.0)):
        a[:] = np.mean(a) + target / max(float(np.std(a)), 1e-5) * (a - np.mean(a))
    return (_resize(np.clip(m * sm, 0, 252), shape),
            _resize(np.clip(r, 3, 249), shape),
            _resize(np.clip(cc, 0, 255), shape))
