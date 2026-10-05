"""Cicada Window I1 — hydrophobic nanopillar glass and bronze wing ribs.

SPB-105 / IRIDESCENT INSECTS tick 24 / owner 2026-09-01: 8-32px native
features, no macro wallpaper or random grit.  Cicada wings use close-packed,
spherically capped conical protuberances under hydrophobic wax; the ordered
~200nm arrays provide anti-reflection, self-cleaning and exceptionally low
adhesion.  This renderer binds those pillar tips to compact elongated membrane
windows, bronze ribs, turquoise cross-ties and jumping-condensate rims.  It is
not Glasswing Lattice's irregular polygon carrier.  Iteration metrics are logged
before any live promotion.
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
    """Build a hand-authored cicada membrane, not a periodic stripe field.

    IRIDESCENT INSECTS tick 24 / pass 5 / owner identity law 2026-09-01:
    the long carrier is an unequal family of independently wandering veins.
    Every visible material event is a fine native feature: 6-12px vein lips,
    8-24px tension ties, 8-12px nanocones and 10-22px suture collars.
    P3 M7 94.4 was rejected as macro wave wallpaper; P4 M7 98.8 was
    rejected as pearl-chain clutter; P5 retains the vein anatomy at M7 98.9.
    """
    s = GEN / 1024.0
    rng = np.random.default_rng(int(seed) ^ 0xC1CA4A)
    rib = np.zeros((GEN, GEN), np.float32)
    rib_core = np.zeros_like(rib)
    cross = np.zeros_like(rib)
    cross_core = np.zeros_like(rib)
    suture = np.zeros_like(rib)
    fold = np.zeros_like(rib)

    def pt(xv, yv):
        return int(round(xv * s)), int(round(yv * s))

    # Unequal vein tracks.  Spacing, phase, walk and cross-tie cadence are all
    # independent; grayscale silhouette therefore cannot collapse to a recolor
    # or rotated copy of Glasswing's polygon lattice.
    tracks = []
    xv = -36.0
    idx = 0
    while xv < 1080.0:
        spacing = float(rng.uniform(12.0, 19.0))
        phase = float(rng.uniform(0, np.pi * 2))
        lean = float(rng.uniform(-.10, .22))
        amp1 = float(rng.uniform(1.8, 5.2))
        amp2 = float(rng.uniform(.8, 2.6))
        ys = np.arange(-32.0, 1064.0, 10.0)
        xs = xv + lean * ys + amp1 * np.sin(ys / rng.uniform(31.0, 58.0) + phase)
        xs += amp2 * np.sin(ys / rng.uniform(11.0, 21.0) - phase * .47)
        pts = np.array([pt(a, b) for a, b in zip(xs, ys)], np.int32)
        strong = (idx % 5 == 0) or (idx % 7 == 3)
        cv2.polylines(rib, [pts], False, .82 if strong else .48,
                      max(1, int(round((3.8 if strong else 2.4) * s))), cv2.LINE_AA)
        cv2.polylines(rib_core, [pts], False, 1.0 if strong else .58,
                      max(1, int(round((1.35 if strong else .85) * s))), cv2.LINE_AA)
        tracks.append((ys, xs, strong))
        xv += spacing
        idx += 1

    # Short arched tension ties connect only neighboring veins.  Cadence and
    # vertical offset vary per gap, breaking the old full-width wave wallpaper.
    for i in range(len(tracks) - 1):
        ys0, xs0, strong0 = tracks[i]
        ys1, xs1, strong1 = tracks[i + 1]
        yv = float(rng.uniform(-8, 12))
        step = float(rng.uniform(13.0, 24.0))
        while yv < 1034:
            j = int(np.argmin(np.abs(ys0 - yv)))
            xa, xb = float(xs0[j]), float(xs1[j])
            if xb - xa < 30 and rng.random() > .16:
                crown = yv + float(rng.uniform(-2.8, 2.8))
                arc = np.array([pt(xa, yv), pt((xa + xb) * .5, crown), pt(xb, yv + rng.uniform(-1.8, 1.8))], np.int32)
                power = .84 if (strong0 or strong1) else .56
                cv2.polylines(cross, [arc], False, power, max(1, int(round(2.1 * s))), cv2.LINE_AA)
                cv2.polylines(cross_core, [arc], False, power, max(1, int(round(.72 * s))), cv2.LINE_AA)
                if rng.random() > .92:
                    cv2.circle(suture, pt(xa, yv), max(1, int(round(rng.uniform(1.6, 2.6) * s))), 1.0, 1, cv2.LINE_AA)
                if rng.random() > .72:
                    # tiny flexible resilin fold beside the joint
                    stub = np.array([pt(xa + 2, yv + 1), pt(xa + rng.uniform(5, 10), yv + rng.uniform(3, 8))], np.int32)
                    cv2.polylines(fold, [stub], False, 1.0, max(1, int(round(1.2 * s))), cv2.LINE_AA)
            yv += step * float(rng.uniform(.82, 1.22))

    rib = cv2.GaussianBlur(rib, (0, 0), .42)
    rib_core = cv2.GaussianBlur(rib_core, (0, 0), .28)
    cross = cv2.GaussianBlur(cross, (0, 0), .38)
    cross_core = cv2.GaussianBlur(cross_core, (0, 0), .24)
    suture = cv2.GaussianBlur(suture, (0, 0), .36)
    fold = cv2.GaussianBlur(fold, (0, 0), .30)
    carrier = np.clip(rib + cross, 0, 1)

    y, x = coords(GEN)
    x, y = x / s, y / s
    # Fine membrane states remain subordinate to the authored vein silhouette.
    state = n01(np.sin((x * .73 + y * .29) / 9.1) +
                .61 * np.cos((x * .17 - y * .81) / 12.7) +
                .31 * np.sin((x + y) / 5.8))
    clear = np.clip((state - .30) * 1.45, 0, 1) * (1 - carrier)
    smoke = np.clip((.59 - state) * 1.55, 0, 1) * (1 - carrier)
    turquoise = np.clip(1 - np.abs(state - .64) / .16, 0, 1) * (1 - carrier)
    amber = np.clip((state - .82) * 4.2, 0, 1) * (1 - carrier)

    # Hydrophobic capped nanocones are attached to membrane panes.  At native
    # 2048 they resolve at roughly 8-12px and never become random confetti.
    px = x + 1.1 * np.sin(y / 23.0)
    py = y + .7 * np.sin(x / 31.0)
    row = np.floor(py / 4.6)
    hx = np.mod(px + np.mod(row, 2.0) * 2.65 + 2.65, 5.3) - 2.65
    hy = np.mod(py + 2.30, 4.6) - 2.30
    hd = np.sqrt(hx * hx + hy * hy)
    pillar = cv2.GaussianBlur(np.clip(1 - hd / 2.12, 0, 1), (0, 0), .31) * (1 - carrier)
    pillar_tip = cv2.GaussianBlur(np.clip(1 - hd / .78, 0, 1), (0, 0), .24) * clear
    pillar_rim = cv2.GaussianBlur(np.clip(1 - np.abs(hd - 1.58) / .42, 0, 1), (0, 0), .28) * (turquoise + .35 * smoke)

    # Sparse condensate belongs to sutures: dilated collars, never floating dots.
    drop = cv2.dilate(suture, np.ones((2, 2), np.uint8), iterations=1) * (.26 + .42 * clear)
    drop_rim = np.clip(cv2.dilate(suture, np.ones((3, 3), np.uint8), iterations=1) - drop * .72, 0, 1)
    return tuple(np.asarray(a, np.float32) for a in (
        rib, rib_core, cross, cross_core, suture, state, clear, smoke,
        turquoise, amber, pillar, pillar_tip, pillar_rim, drop, drop_rim, fold,
    ))


def paint_cicada_membrane_i1(paint, shape, mask, seed, pm, bb):
    (rib, rib_core, cross, cross_core, suture, state, clear, smoke,
     turquoise, amber, pillar, pillar_tip, pillar_rim, drop, drop_rim, fold) = _surface(seed + 54139)
    haze = np.array([.12, .18, .19], np.float32)
    clear_col = np.array([.41, .56, .57], np.float32)
    bronze = np.array([.58, .27, .065], np.float32)
    gold = np.array([.86, .54, .16], np.float32)
    teal = np.array([.025, .57, .64], np.float32)
    chrome = np.array([.77, .88, .86], np.float32)

    col = haze[None, None, :] * (.52 + .17 * smoke[..., None])
    col += clear[..., None] * clear_col[None, None, :] * .34
    col += turquoise[..., None] * teal[None, None, :] * .28
    col += amber[..., None] * np.array([.55, .22, .045], np.float32) * .25
    col += pillar[..., None] * np.array([.23, .38, .38], np.float32) * .15
    col += pillar_rim[..., None] * teal[None, None, :] * .18
    col += pillar_tip[..., None] * chrome[None, None, :] * .22
    col += rib[..., None] * bronze[None, None, :] * (.52 + .22 * state[..., None])
    col += rib_core[..., None] * gold[None, None, :] * .36
    col += cross[..., None] * teal[None, None, :] * .60
    col += cross_core[..., None] * chrome[None, None, :] * .44
    col += suture[..., None] * np.array([.92, .71, .30], np.float32) * .40
    col += drop[..., None] * np.array([.10, .35, .39], np.float32) * .19
    col += drop_rim[..., None] * chrome[None, None, :] * .24
    col += fold[..., None] * np.array([.23, .42, .77], np.float32) * .48
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_cicada_membrane_i1(shape, seed, sm, base_m, base_r):
    (rib, rib_core, cross, cross_core, suture, state, clear, smoke,
     turquoise, amber, pillar, pillar_tip, pillar_rim, drop, drop_rim, fold) = _surface(seed + 54139)
    m = 24 + 202 * (.24 * rib + .18 * rib_core + .16 * suture + .12 * amber +
                    .10 * pillar_tip + .08 * fold + .07 * state + .05 * cross_core)
    r = 18 + 210 * (.24 * smoke + .21 * pillar + .16 * cross + .12 * (1 - clear) +
                    .10 * drop + .08 * pillar_rim + .05 * (1 - state) + .04 * fold)
    cc = 16 + 220 * (.22 * clear + .19 * drop_rim + .16 * pillar_tip +
                     .13 * turquoise + .10 * cross_core + .09 * suture + .07 * fold + .04 * state)
    m += suture * 22 + rib_core * 17 - smoke * 15
    r += pillar * 18 - drop_rim * 23
    cc += drop_rim * 28 + pillar_tip * 18 - smoke * 12
    m = np.mean(m) + 25.0 / max(float(np.std(m)), 1e-5) * (m - np.mean(m))
    r = np.mean(r) + 23.0 / max(float(np.std(r)), 1e-5) * (r - np.mean(r))
    cc = np.mean(cc) + 27.0 / max(float(np.std(cc)), 1e-5) * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 250), shape),
            _resize(np.clip(r, 5, 249), shape),
            _resize(np.clip(cc, 0, 255), shape))
