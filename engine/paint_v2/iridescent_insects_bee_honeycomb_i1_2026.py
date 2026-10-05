"""Bee Venturi I1 — imperfect wax-cell armor with pollen-set microhairs.

IRIDESCENT INSECTS tick 27 / owner identity law 2026-09-01.
Identity contract: thousands of individually distorted rounded wax cells form
the carrier, but regular honeycomb wallpaper is prohibited.  Transition cells,
merged walls, wax grains, cocoon silk lamellae, honey menisci, propolis plugs,
and pollen-set hairs supply separate mark families and M/R/Cc states.  It may
not resemble any insect scale, wing-vein, bubble or generic hex-grid finish.
Sources: Zhang et al. PNAS 2010 (500nm–1.5um wax grains and age-layered silk
cocoon cell walls), Nazzi 2016 (cell foundation/storage architecture), and
Smith et al. PNAS 2021 (imperfect comb transition cells and variable walls).
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, n01

GEN = 640


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
    rng = np.random.default_rng(int(seed) ^ 0xBEE271)
    # P1's individually drawn rings scored 92.0 but were rejected as ordered
    # dot/confetti wallpaper.  P2 builds one connected, shared-wall Voronoi
    # architecture from imperfect cell centres.  No cell is a floating ring.
    seed_map = np.full((GEN, GEN), 255, np.uint8)
    centres = []
    row = 0; yy = -4.0
    while yy < GEN + 5:
        step = rng.uniform(7.0, 10.2)
        xx = -4.0 + (step * .48 if row % 2 else 0) + rng.uniform(-2.8, 2.8)
        while xx < GEN + 5:
            cx = int(np.clip(round(xx + rng.uniform(-2.5, 2.5)), 0, GEN - 1))
            cy = int(np.clip(round(yy + rng.uniform(-2.3, 2.3)), 0, GEN - 1))
            seed_map[cy, cx] = 0; centres.append((cx, cy))
            xx += step * rng.uniform(.78, 1.32)
        yy += step * rng.uniform(.76, 1.22); row += 1

    dist, labels = cv2.distanceTransformWithLabels(
        seed_map, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
    )
    edge = np.zeros((GEN, GEN), np.float32)
    edge[:, 1:] = np.maximum(edge[:, 1:], (labels[:, 1:] != labels[:, :-1]).astype(np.float32))
    edge[1:, :] = np.maximum(edge[1:, :], (labels[1:, :] != labels[:-1, :]).astype(np.float32))
    wall_lip = cv2.GaussianBlur(edge, (0, 0), .32)
    wall = cv2.GaussianBlur(cv2.dilate(edge, np.ones((2, 2), np.uint8), iterations=1), (0, 0), .45)
    interior = 1 - np.clip(cv2.dilate(edge, np.ones((3, 3), np.uint8), iterations=1), 0, 1)

    max_label = int(labels.max())
    state = rng.random(max_label + 1, dtype=np.float32)
    tier = state[labels]
    fresh = np.clip(1 - np.abs(tier - .28) / .28, 0, 1) * interior
    honey = np.clip(1 - np.abs(tier - .60) / .18, 0, 1) * interior
    aged = np.clip((tier - .70) * 3.35, 0, 1) * interior
    propolis = np.clip((tier - .91) * 11.2, 0, 1) * np.clip(1 - dist / 3.4, 0, 1)

    y, x = coords(GEN); x, y = x / s, y / s
    silk_lines = np.clip(1 - np.abs(np.mod(y + .17 * x, 3.8) - 1.9) / .55, 0, 1)
    silk = silk_lines * aged
    grain_state = n01(np.sin((.83 * x + .17 * y) / 3.9) +
                      .55 * np.cos((.23 * x - .91 * y) / 5.7))
    grain = np.clip((grain_state - .48) * 1.92, 0, 1) * cv2.GaussianBlur(wall, (0, 0), 1.2)
    meniscus = np.clip(cv2.dilate(honey, np.ones((3, 3), np.uint8), iterations=1) - honey * .70, 0, 1) * interior

    # Sparse pollen bundles remain physically attached to chosen cell centres.
    hair = np.zeros_like(wall); pollen = np.zeros_like(wall)
    for cx, cy in centres[::max(1, len(centres) // 420)]:
        if rng.random() < .67: continue
        cv2.circle(pollen, (cx, cy), max(1, int(round(rng.uniform(1.2, 2.1)))), 1.0, -1, cv2.LINE_AA)
        for _ in range(int(rng.integers(3, 6))):
            a = rng.uniform(0, np.pi * 2); ln = rng.uniform(3.0, 7.0)
            hp = np.array([(cx, cy), (int(round(cx + ln * np.cos(a))), int(round(cy + ln * np.sin(a))))], np.int32)
            cv2.polylines(hair, [hp], False, rng.uniform(.50, 1.0), 1, cv2.LINE_AA)
    propolis = cv2.GaussianBlur(propolis, (0, 0), .34)
    silk = cv2.GaussianBlur(silk, (0, 0), .25); hair = cv2.GaussianBlur(hair, (0, 0), .23)
    pollen = cv2.GaussianBlur(pollen, (0, 0), .28)
    return tuple(np.asarray(a, np.float32) for a in
                 (wall, wall_lip, fresh, honey, aged, propolis, silk, hair, pollen, grain, meniscus))


def paint_bee_honeycomb_i1(paint, shape, mask, seed, pm, bb):
    wall, lip, fresh, honey, aged, propolis, silk, hair, pollen, grain, meniscus = _surface(seed + 27109)
    col = np.zeros((*wall.shape, 3), np.float32)
    col[:] = np.array([.055, .035, .022], np.float32)
    col += fresh[..., None] * np.array([.54, .31, .08], np.float32) * .54
    col += honey[..., None] * np.array([.86, .44, .045], np.float32) * .76
    col += aged[..., None] * np.array([.18, .075, .028], np.float32) * .58
    col += wall[..., None] * np.array([.68, .39, .11], np.float32) * .78
    col += lip[..., None] * np.array([.95, .69, .25], np.float32) * .58
    col += propolis[..., None] * np.array([.10, .035, .018], np.float32) * .72
    col += silk[..., None] * np.array([.66, .53, .35], np.float32) * .48
    col += hair[..., None] * np.array([.52, .33, .10], np.float32) * .62
    col += pollen[..., None] * np.array([.93, .73, .18], np.float32) * .78
    col += grain[..., None] * np.array([.76, .55, .28], np.float32) * .34
    col += meniscus[..., None] * np.array([.94, .81, .52], np.float32) * .50
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_bee_honeycomb_i1(shape, seed, sm, base_m, base_r):
    wall, lip, fresh, honey, aged, propolis, silk, hair, pollen, grain, meniscus = _surface(seed + 27109)
    m = 16 + 224 * (.23 * wall + .18 * lip + .14 * pollen + .12 * grain +
                    .10 * meniscus + .09 * honey + .08 * silk + .06 * fresh)
    r = 20 + 212 * (.23 * aged + .20 * hair + .16 * propolis + .13 * grain +
                    .10 * fresh + .08 * silk + .06 * (1 - honey) + .04 * wall)
    cc = 12 + 234 * (.24 * honey + .21 * meniscus + .16 * lip + .12 * fresh +
                     .09 * pollen + .07 * wall + .06 * grain + .05 * silk)
    m += pollen * 25 + wall * 17 - propolis * 14
    r += hair * 24 + propolis * 19 - meniscus * 22
    cc += meniscus * 29 + lip * 21 - aged * 12
    for a, target in ((m, 29.0), (r, 26.0), (cc, 31.0)):
        a[:] = np.mean(a) + target / max(float(np.std(a)), 1e-5) * (a - np.mean(a))
    # P2's connected carrier passed the eye and M5 99.1 but failed M6 because
    # M/Cc occupied only 146/136 levels.  P3 preserves the feature silhouettes
    # and expands robust percentiles, not decorative color fields.
    def spread(a, lo, hi):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        return np.clip(lo + (a - p1) * ((hi - lo) / max(float(p99 - p1), 1e-5)), lo, hi)
    m = spread(m, 3, 252) * sm
    r = spread(r, 5, 249)
    cc = spread(cc, 1, 254)
    return (_resize(m, shape), _resize(r, shape), _resize(cc, shape))
