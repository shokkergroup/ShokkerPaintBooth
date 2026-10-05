"""Lacewing Aurora I1 — fanned Neuropteran gradates and thin-film panes.

IRIDESCENT INSECTS tick 25 / owner identity law 2026-09-01.
Identity contract: this must read in grayscale as a branching lacewing wing:
sigmoid pseudomedial rails, convergent radial branches, staggered inner/outer
gradates, oval tension joints, fine vein setae and pebbled thin-film panes.
It may not resemble Glasswing's irregular closed polygons, Cicada's dense
longitudinal tension ladders, or any palette-swapped diagonal wave.  Paint and
M/R/Cc are bound to those named features.  Sources: Shevtsova et al. PNAS 2011
(membrane thickness, corrugation, venation and hair placement define WIPs) and
Breitkreuz et al. ZooKeys 2015 (variable 5–7 inner and 6–8 outer gradates,
continuous Psm, branch/crossvein markings).
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

GEN = 640


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


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
    s = GEN / 1024.0
    rng = np.random.default_rng(int(seed) ^ 0x1ACEA0)
    primary = np.zeros((GEN, GEN), np.float32)
    primary_core = np.zeros_like(primary)
    branch = np.zeros_like(primary)
    gradate = np.zeros_like(primary)
    joint = np.zeros_like(primary)
    hair = np.zeros_like(primary)

    def pt(xv, yv):
        return int(round(xv * s)), int(round(yv * s))

    # Independent sigmoid pseudomedial rails.  Each rail owns a different
    # curvature, lean and branch schedule; there is no shared periodic field.
    rails = []
    x0 = -240.0
    rail_index = 0
    while x0 < 1130:
        ys = np.arange(-90.0, 1110.0, 12.0)
        phase = rng.uniform(0, np.pi * 2)
        lean = rng.uniform(.38, .70)
        bend = rng.uniform(7.0, 17.0)
        xs = x0 + lean * ys + bend * np.sin(ys / rng.uniform(78, 142) + phase)
        xs += rng.uniform(1.2, 3.8) * np.sin(ys / rng.uniform(18, 34) - phase * .41)
        points = np.array([pt(a, b) for a, b in zip(xs, ys)], np.int32)
        thick = rail_index % 4 == 0
        cv2.polylines(primary, [points], False, .92 if thick else .58,
                      max(1, int(round((3.2 if thick else 2.1) * s))), cv2.LINE_AA)
        cv2.polylines(primary_core, [points], False, 1.0 if thick else .68,
                      max(1, int(round((1.05 if thick else .70) * s))), cv2.LINE_AA)
        rails.append((ys, xs, thick))
        x0 += rng.uniform(34.0, 55.0)
        rail_index += 1

    # Convergent radial branches leave one rail and terminate toward the next.
    # Short 8–30px-native pieces, rather than a full repeated crossbar, build
    # the characteristic lace fan and keep the carrier scalable on a car.
    for i, (ys, xs, thick) in enumerate(rails[:-1]):
        ys2, xs2, _ = rails[i + 1]
        yv = rng.uniform(-20, 20)
        while yv < 1040:
            j = int(np.argmin(np.abs(ys - yv)))
            xa, xb = float(xs[j]), float(xs2[j])
            gap = xb - xa
            if 12 < gap < 70 and rng.random() > .12:
                count = int(rng.integers(2, 5))
                for arm in range(count):
                    t0 = .10 + arm * (.68 / max(count - 1, 1))
                    start = xa + gap * t0
                    length = min(gap * rng.uniform(.30, .56), rng.uniform(7.0, 15.0))
                    rise = rng.uniform(5.0, 14.0) * (-1 if (arm + i) % 2 else 1)
                    path = np.array([
                        pt(start, yv),
                        pt(start + length * .48, yv + rise * .42),
                        pt(start + length, yv + rise),
                    ], np.int32)
                    cv2.polylines(branch, [path], False, rng.uniform(.58, .94),
                                  max(1, int(round(1.45 * s))), cv2.LINE_AA)
                    if rng.random() > .60:
                        # Pedicellate setae follow, and remain attached to, a vein.
                        hp = np.array([pt(start + length * .42, yv + rise * .38),
                                       pt(start + length * .42 + rng.uniform(-4, 4),
                                          yv + rise * .38 + rng.uniform(4, 8))], np.int32)
                        cv2.polylines(hair, [hp], False, 1.0, 1, cv2.LINE_AA)
                # Staggered inner/outer gradates occupy only selected gaps.
                if rng.random() > .30:
                    ga = xa + gap * rng.uniform(.18, .35)
                    gb = xa + gap * rng.uniform(.65, .84)
                    gy = yv + rng.uniform(-3, 3)
                    arc = np.array([pt(ga, gy), pt((ga + gb) * .5, gy + rng.uniform(-4, 4)),
                                    pt(gb, gy + rng.uniform(-2, 2))], np.int32)
                    cv2.polylines(gradate, [arc], False, rng.uniform(.54, .90),
                                  max(1, int(round(1.35 * s))), cv2.LINE_AA)
                    if rng.random() > .74:
                        center = pt((ga + gb) * .5, gy)
                        cv2.ellipse(joint, center,
                                    (max(1, int(round(2.7 * s))), max(1, int(round(1.6 * s)))),
                                    rng.uniform(-35, 35), 0, 360, 1.0, 1, cv2.LINE_AA)
            yv += rng.uniform(17.0, 29.0)

    primary = cv2.GaussianBlur(primary, (0, 0), .40)
    primary_core = cv2.GaussianBlur(primary_core, (0, 0), .26)
    branch = cv2.GaussianBlur(branch, (0, 0), .32)
    gradate = cv2.GaussianBlur(gradate, (0, 0), .30)
    joint = cv2.GaussianBlur(joint, (0, 0), .28)
    hair = cv2.GaussianBlur(hair, (0, 0), .24)
    vein = np.clip(primary + branch + gradate, 0, 1)

    y, x = coords(GEN)
    x, y = x / s, y / s
    # P1's trigonometric thickness field passed M7 88.2 but was rejected as a
    # repeated diagonal-oval wallpaper.  P2 uses nonperiodic, spatially smooth
    # thickness populations at a 10–28px native scale; the authored venation
    # remains the only long-range carrier.
    thick_a = cv2.resize(rng.random((76, 76), dtype=np.float32), (GEN, GEN),
                         interpolation=cv2.INTER_CUBIC)
    thick_b = cv2.resize(rng.random((128, 128), dtype=np.float32), (GEN, GEN),
                         interpolation=cv2.INTER_CUBIC)
    thick_a = cv2.GaussianBlur(thick_a, (0, 0), 3.6)
    thick_b = cv2.GaussianBlur(thick_b, (0, 0), 2.0)
    vein_halo = cv2.GaussianBlur(vein, (0, 0), 3.4)
    pebble = np.clip(.64 * thick_a + .24 * thick_b + .12 * vein_halo, 0, 1)
    pane = (1 - np.clip(vein * 1.2, 0, 1))
    pearl = np.clip((pebble - .20) * 1.28, 0, 1) * pane
    rose = np.clip(1 - np.abs(pebble - .60) / .17, 0, 1) * pane
    green = np.clip(1 - np.abs(pebble - .37) / .15, 0, 1) * pane
    blue = np.clip((pebble - .80) * 4.1, 0, 1) * pane

    # Minute wax pores sit within pane material; lips and tips are separate
    # named mark types and receive different material tiers.
    px = x + 1.0 * np.sin(y / 27.0)
    py = y + .8 * np.sin(x / 33.0)
    gx = np.mod(px + 3.15, 6.3) - 3.15
    gy = np.mod(py + 2.95, 5.9) - 2.95
    pd = np.sqrt(gx * gx + gy * gy)
    pore = cv2.GaussianBlur(np.clip(1 - pd / 1.75, 0, 1), (0, 0), .28) * pane
    pore_lip = cv2.GaussianBlur(np.clip(1 - np.abs(pd - 1.85) / .42, 0, 1), (0, 0), .27) * pane
    return tuple(np.asarray(a, np.float32) for a in (
        primary, primary_core, branch, gradate, joint, hair, pebble,
        pearl, rose, green, blue, pore, pore_lip,
    ))


def paint_lacewing_aurora_i1(paint, shape, mask, seed, pm, bb):
    (primary, core, branch, gradate, joint, hair, pebble,
     pearl, rose, green, blue, pore, pore_lip) = _surface(seed + 77101)
    col = np.zeros((*primary.shape, 3), np.float32)
    col[:] = np.array([.11, .17, .145], np.float32)
    col += pearl[..., None] * np.array([.38, .49, .43], np.float32) * .30
    col += green[..., None] * np.array([.13, .50, .27], np.float32) * .34
    col += rose[..., None] * np.array([.61, .16, .39], np.float32) * .32
    col += blue[..., None] * np.array([.14, .31, .68], np.float32) * .30
    col += primary[..., None] * np.array([.50, .33, .11], np.float32) * .70
    col += core[..., None] * np.array([.88, .72, .31], np.float32) * .62
    col += branch[..., None] * np.array([.18, .65, .37], np.float32) * .92
    col += gradate[..., None] * np.array([.78, .51, .24], np.float32) * .88
    col += joint[..., None] * np.array([.92, .82, .55], np.float32) * .70
    col += hair[..., None] * np.array([.69, .88, .72], np.float32) * .46
    col += pore[..., None] * np.array([.10, .23, .18], np.float32) * .18
    col += pore_lip[..., None] * np.array([.50, .73, .61], np.float32) * .28
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_lacewing_aurora_i1(shape, seed, sm, base_m, base_r):
    (primary, core, branch, gradate, joint, hair, pebble,
     pearl, rose, green, blue, pore, pore_lip) = _surface(seed + 77101)
    m = 18 + 216 * (.24 * primary + .18 * core + .14 * gradate + .12 * joint +
                    .10 * rose + .08 * blue + .08 * pore_lip + .06 * branch)
    r = 20 + 208 * (.22 * hair + .19 * pore + .16 * green + .13 * (1 - pearl) +
                    .11 * branch + .08 * (1 - pebble) + .06 * gradate + .05 * joint)
    cc = 14 + 228 * (.24 * pearl + .18 * rose + .15 * blue + .13 * pore_lip +
                     .10 * joint + .08 * core + .07 * green + .05 * hair)
    m += core * 24 + joint * 21 - pore * 13
    r += hair * 24 + pore * 18 - joint * 20
    cc += pore_lip * 24 + pearl * 19 - primary * 10
    for a, target in ((m, 27.0), (r, 24.0), (cc, 29.0)):
        a[:] = np.mean(a) + target / max(float(np.std(a)), 1e-5) * (a - np.mean(a))
    return (_resize(np.clip(m * sm, 0, 252), shape),
            _resize(np.clip(r, 4, 249), shape),
            _resize(np.clip(cc, 0, 255), shape))
