"""Hoverfly Mirror I1 — syrphid mirror tergites under false-vein glass.

IRIDESCENT INSECTS tick 30 / owner identity law 2026-09-01.
Identity contract: compact 8–28px native rhomboid tergite mirrors assemble into
interrupted abdominal maculae; transparent wing-film lanes, paired true/spurious
vein rails, bare membrane windows, microtrichia combs, pollinose frost, vein
nodes and articulation scuffs add seven named mark families.  Mimetic dark/gold
colour comes from shiny cuticle plates and dusted maculae, not Bumble pile or
Wasp Signal's chevron network.  It may not resemble a vein-web card, generic
stripes, chrome tiles, confetti or a palette variant.  M/R/Cc ownership follows
mirror plate, pollinose dust, membrane, rail, microtrichium and node anatomy.

Research: Syrphidae use glossy cuticular abdominal pigment rather than bee-like
hair pigment; pollinose maculae and punctate shiny terga are diagnostic in many
taxa.  Betasyrphus wing studies use patchy microtrichia distributions and
thin-film wing interference patterns; the family hallmark is a vena spuria
running parallel to a longitudinal vein.  Brachyceran flexible membranes also
carry bare microplates and microplates with single or grouped microtrichia.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

GEN = 680


def _hw(shape): return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape); a = np.asarray(a, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    a = np.clip(mask * pm * .97, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(colour, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0x480F1E)
    h = w = GEN
    mirror = np.zeros((h, w), np.float32)
    dark = np.zeros_like(mirror)
    gold = np.zeros_like(mirror)
    membrane = np.zeros_like(mirror)
    true_rail = np.zeros_like(mirror)
    false_rail = np.zeros_like(mirror)
    frost = np.zeros_like(mirror)
    trichia = np.zeros_like(mirror)
    node = np.zeros_like(mirror)
    scuff = np.zeros_like(mirror)
    bare = np.zeros_like(mirror)

    # P2 replaces P1's sinusoidal macula bands (metric pass but owner-eye
    # reject) with anatomically paired, irregular pollinose macula islands.
    # The invisible mask only selects individual 9–28px sclerites.
    macula_mask = np.zeros((h, w), np.uint8)
    for _ in range(158):
        cx, cy = float(rng.integers(-20, w + 20)), float(rng.integers(-20, h + 20))
        angle = rng.uniform(-np.pi, np.pi); sep = rng.uniform(11.0, 27.0)
        ux, uy = np.cos(angle), np.sin(angle)
        for side in (-1, 1):
            px, py = cx + side * sep * ux, cy + side * sep * uy
            axes = (int(rng.integers(11, 27)), int(rng.integers(5, 12)))
            cv2.ellipse(macula_mask, (round(px), round(py)), axes,
                        np.degrees(angle) + rng.uniform(-18, 18), 0, 360, 255, -1, cv2.LINE_AA)
    macula_mask = cv2.GaussianBlur(macula_mask, (0, 0), 2.2)

    # Compact rhomboid sclerites cover the complete carrier; only their
    # material population changes inside paired maculae.
    sx, sy = 7.2, 7.0
    for row, y0 in enumerate(np.arange(-4, h + 5, sy)):
        for x0 in np.arange(-4, w + 5, sx):
            cx = float(x0 + rng.uniform(-1.8, 1.8)); cy = float(y0 + rng.uniform(-1.7, 1.7))
            ix, iy = int(np.clip(round(cx), 0, w - 1)), int(np.clip(round(cy), 0, h - 1))
            angle = (-.30 if row % 2 else .26) + rng.uniform(-.12, .12)
            ux, uy = np.cos(angle), np.sin(angle); nx, ny = -uy, ux
            ln = rng.uniform(2.8, 5.4); hh = rng.uniform(1.25, 2.25)
            pts = np.asarray([
                (round(cx - ln * ux), round(cy - ln * uy)),
                (round(cx + hh * nx), round(cy + hh * ny)),
                (round(cx + ln * ux), round(cy + ln * uy)),
                (round(cx - hh * nx), round(cy - hh * ny)),
            ], np.int32)
            strength = float(rng.uniform(.38, 1.0))
            if macula_mask[iy, ix] + rng.normal(0, 32) > 105:
                target = gold if rng.random() < .43 else mirror
            else:
                target = dark
            cv2.fillConvexPoly(target, pts, strength, cv2.LINE_AA)
            # Pollinose frost is made from attached 8–14px comb scratches, not dots.
            if target is mirror and rng.random() < .30:
                for j in range(rng.integers(2, 5)):
                    off = (j - 1.5) * .9
                    p1 = (round(cx - 1.9 * ux + off * nx), round(cy - 1.9 * uy + off * ny))
                    p2 = (round(cx + 1.9 * ux + off * nx), round(cy + 1.9 * uy + off * ny))
                    cv2.line(frost, p1, p2, float(rng.uniform(.32, .86)), 1, cv2.LINE_AA)

    # Sparse transparent wing-film lanes cross the sclerites without forming a
    # full vein web.  Each lane has a true rail and a parallel, broken vena spuria.
    for k in range(12):
        y0 = rng.uniform(-20, h + 20); slope = rng.uniform(-.34, .34)
        pts = []
        for x in np.arange(-10, w + 11, 9):
            yy = y0 + slope * x + 4.5 * np.sin(x / rng.uniform(71, 126) + k * .71)
            pts.append((round(x), round(yy)))
        arr = np.asarray(pts, np.int32)
        cv2.polylines(membrane, [arr], False, float(rng.uniform(.20, .55)), int(rng.integers(4, 8)), cv2.LINE_AA)
        cv2.polylines(true_rail, [arr], False, float(rng.uniform(.45, 1.0)), 1, cv2.LINE_AA)
        offset = rng.choice([-1, 1]) * rng.uniform(5.0, 9.0)
        shifted = arr.copy(); shifted[:, 1] += round(offset)
        # False rail is interrupted into finite diagnostic packets.
        for start in range(rng.integers(0, 4), len(shifted) - 2, rng.integers(4, 8)):
            end = min(len(shifted), start + rng.integers(2, 5))
            cv2.polylines(false_rail, [shifted[start:end]], False,
                          float(rng.uniform(.42, .96)), 1, cv2.LINE_AA)

    # Microtrichia occur in bounded islands alongside rails; bare windows are
    # elongated clear patches, separating this from uniformly hairy wings.
    rail_points = np.argwhere((true_rail + false_rail) > .22)
    if len(rail_points):
        pick = rail_points[rng.choice(len(rail_points), min(1100, len(rail_points)), replace=False)]
        for py, px in pick:
            if rng.random() < .58: continue
            angle = rng.uniform(-1.35, 1.35); ln = rng.uniform(2.5, 5.0)
            cv2.line(trichia, (int(px), int(py)),
                     (round(px + ln * np.cos(angle)), round(py + ln * np.sin(angle))),
                     float(rng.uniform(.30, .86)), 1, cv2.LINE_AA)
    for _ in range(95):
        cx, cy = int(rng.integers(8, w - 8)), int(rng.integers(8, h - 8))
        cv2.ellipse(bare, (cx, cy), (int(rng.integers(4, 9)), int(rng.integers(2, 5))),
                    rng.uniform(0, 180), 0, 360, float(rng.uniform(.26, .74)), 1, cv2.LINE_AA)

    # Articulation nodes and mirror scuffs stay attached to plate/rail material.
    candidates = np.argwhere((mirror > .28) & ((true_rail + false_rail) > .12))
    if len(candidates):
        pick = candidates[rng.choice(len(candidates), min(180, len(candidates)), replace=False)]
        for py, px in pick:
            cv2.ellipse(node, (int(px), int(py)), (2, 1), rng.uniform(0, 180), 0, 360,
                        float(rng.uniform(.40, 1.0)), 1, cv2.LINE_AA)
    mirror_pts = np.argwhere(mirror > .38)
    if len(mirror_pts):
        pick = mirror_pts[rng.choice(len(mirror_pts), min(320, len(mirror_pts)), replace=False)]
        for py, px in pick:
            angle = rng.uniform(-.7, .7); ln = rng.uniform(2.8, 5.8)
            cv2.line(scuff, (int(px), int(py)),
                     (round(px + ln * np.cos(angle)), round(py + ln * np.sin(angle))),
                     float(rng.uniform(.25, .75)), 1, cv2.LINE_AA)

    arrays = (mirror, dark, gold, membrane, true_rail, false_rail, frost, trichia, node, scuff, bare)
    return tuple(cv2.GaussianBlur(a, (0, 0), .18).astype(np.float32) for a in arrays)


def paint_hoverfly_mirror_i1(paint, shape, mask, seed, pm, bb):
    mirror, dark, gold, membrane, true_rail, false_rail, frost, trichia, node, scuff, bare = _surface(seed + 30107)
    col = np.zeros((*mirror.shape, 3), np.float32)
    col[:] = np.array([.022, .031, .030], np.float32)
    col += dark[..., None] * np.array([.09, .17, .22], np.float32) * .98
    col += mirror[..., None] * np.array([.56, .76, .73], np.float32) * .98
    col += gold[..., None] * np.array([.82, .57, .10], np.float32) * .96
    col += membrane[..., None] * np.array([.06, .29, .36], np.float32) * .43
    col += true_rail[..., None] * np.array([.78, .89, .80], np.float32) * .66
    col += false_rail[..., None] * np.array([.30, .82, .70], np.float32) * .64
    col += frost[..., None] * np.array([.85, .90, .70], np.float32) * .54
    col += trichia[..., None] * np.array([.32, .49, .36], np.float32) * .46
    col += node[..., None] * np.array([.94, .72, .28], np.float32) * .76
    col += scuff[..., None] * np.array([.75, .84, .79], np.float32) * .42
    col += bare[..., None] * np.array([.08, .15, .17], np.float32) * .38
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_hoverfly_mirror_i1(shape, seed, sm, base_m, base_r):
    mirror, dark, gold, membrane, true_rail, false_rail, frost, trichia, node, scuff, bare = _surface(seed + 30107)
    m = 8 + 238 * (.31 * mirror + .23 * gold + .17 * node +
                   .13 * scuff + .09 * true_rail + .07 * frost)
    r = 15 + 222 * (.28 * frost + .22 * trichia + .18 * dark +
                    .14 * scuff + .10 * false_rail + .08 * bare)
    cc = 5 + 244 * (.29 * membrane + .23 * bare + .18 * true_rail +
                    .13 * false_rail + .10 * node + .07 * mirror)
    m += mirror * 34 + gold * 25 - membrane * 18
    r += frost * 31 + trichia * 24 - mirror * 27 - node * 14
    cc += membrane * 35 + bare * 28 + true_rail * 20 - frost * 17

    def spread(a, lo, hi):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        return np.clip(lo + (a - p1) * ((hi - lo) / max(float(p99 - p1), 1e-5)), lo, hi)

    return (np.clip(_resize(spread(m, 4, 250) * sm, shape), 4, 250),
            np.clip(_resize(spread(r, 7, 247), shape), 7, 247),
            np.clip(_resize(spread(cc, 2, 252), shape), 2, 252))
