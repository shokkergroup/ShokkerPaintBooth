"""Damselfly Cobalt I1 — melanin/chitin wing laminations and needle ripples.

SPB-105 / IRIDESCENT INSECTS tick 23 / owner 2026-09-01: every visible
primitive stays 8-32px at 2048².  Neurobasis hindwings obtain high-contrast
green-blue colour from distinct membrane-cuticle laminations over two strongly
absorbing ventral layers; Calopteryx males add melanin/chitin multilayers in
blue-reflecting veins.  This card translates that stack into densely articulated
paired needle lamellae—not Dragonfly Resilin's lattice or Emerald Skimmer's
nanosphere clouds.  Iteration metrics are recorded in the rebuild ledger.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, n01

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
    y, x = coords(GEN)
    x, y = x / s, y / s
    seed = int(seed)
    dx, dy, d1, fid, d2 = _cells(GEN, 9.8 * s, seed % 8191 + 196613,
                                  jit=.91, taps=11, need2=True)
    dx, dy, d1, d2 = dx / s, dy / s, d1 / s, d2 / s
    cx, cy = x - dx, y - dy

    # Each jittered cell owns a compact 14-30px native lamellar needle.  The
    # orientation follows a continuous field, while a small ID perturbation
    # prevents the array from becoming woven or mechanically periodic.
    flow = n01(np.sin((cx + .27 * cy) / 47.0) + .63 * np.cos((cx - .74 * cy) / 83.0))
    jitter = n01(np.sin(fid * 1.731 + .4) + .52 * np.cos(fid * .619 - 1.3))
    state = np.clip(.76 * flow + .24 * jitter, 0, 1)
    angle = -.58 + 1.16 * flow + .22 * (jitter - .5)
    ca, sa = np.cos(angle), np.sin(angle)
    rx, ry = dx * ca + dy * sa, -dx * sa + dy * ca
    length = 6.7 + 1.0 * state
    width = 3.25 + .48 * (1 - state)
    er = np.sqrt((rx / length) ** 2 + (ry / width) ** 2)
    body = np.clip(1 - (er - .73) / .27, 0, 1)
    body_core = np.clip(1 - er / .76, 0, 1)
    rim = np.clip(1 - np.abs(er - .82) / .14, 0, 1) * body

    # Two short reflective laminations and a dark central capillary are bound
    # inside every needle.  End sutures and crossed ripple teeth add the other
    # fine mark families without introducing free grit.
    lam_a = np.clip(1 - np.abs(ry - 1.30) / .92, 0, 1) * body
    lam_b = np.clip(1 - np.abs(ry + 1.30) / .92, 0, 1) * body
    pair = np.maximum(lam_a, lam_b)
    capillary = np.clip(1 - np.abs(ry) / .68, 0, 1) * body
    tip = np.clip(1 - np.abs(np.abs(rx) - length * .72) / .82, 0, 1) * body
    ripple_phase = (rx + .31 * ry + .9 * state) * np.pi / 2.25
    ripple = np.clip((np.cos(ripple_phase) - .55) * 2.23, 0, 1) * body * (1 - capillary * .62)
    cross = np.clip((np.cos((ry - .17 * rx) * np.pi / 1.95) - .58) * 2.38, 0, 1) * body
    window = np.clip(ripple * cross * 1.38, 0, 1)

    # The optical stack: dorsal colour layer, dark ventral absorber, and a
    # narrow wet seam where the two laminated halves meet.
    dorsal = body * np.clip((state - .17) * 1.24, 0, 1)
    ventral = body * np.clip((.62 - state) * 1.55, 0, 1)
    violet = body * np.clip(1 - np.abs(state - .50) / .19, 0, 1)
    steel = body * np.clip((state - .69) * 2.55, 0, 1)
    wet_seam = capillary * np.clip((state - .38) * 1.65, 0, 1)
    gap = np.clip((d2 - d1 - .24) / 1.04, 0, 1)

    # Continuous hindwing laminations replace the local needles as the visual
    # hierarchy.  Paired 8-28px native ribbons survive unevenly along their
    # course; short cross-sutures are physically attached to those ribbons.
    warp = 8.2 * np.sin(y / 37.0 + .7 * np.sin(x / 121.0))
    warp += 3.6 * np.sin((x + y) / 79.0) + 2.1 * np.sin((x - 2 * y) / 137.0)
    u = x + .23 * y + warp
    v = y - .10 * x + 4.2 * np.sin(x / 53.0)
    q = np.mod(u + 8.6, 17.2) - 8.6
    laminate = np.clip(1 - np.abs(np.abs(q) - 3.55) / 1.82, 0, 1)
    laminate_core = np.clip(1 - np.abs(np.abs(q) - 3.55) / .70, 0, 1)
    trough = np.clip(1 - np.abs(q) / 1.66, 0, 1)
    band = np.floor((u + 8.6) / 17.2)
    survival = n01(np.sin(band * 1.713 + np.floor(v / 16.4) * .731) +
                   .49 * np.cos(band * .619 - np.floor(v / 16.4) * 1.127))
    survive_gate = np.clip((survival - .27) * 1.52, 0, 1)
    laminate *= survive_gate
    laminate_core *= survive_gate
    cross_phase = np.mod(v + band * 3.9 + 8.6, 17.2) - 8.6
    suture = np.clip(1 - np.abs(cross_phase) / 1.45, 0, 1) * np.clip(laminate * 1.72, 0, 1)
    suture_core = np.clip(1 - np.abs(cross_phase) / .58, 0, 1) * laminate_core

    # Sparse oblique laminations appear only inside one continuous optical
    # population so they behave like vein forks, never a full crosshatch.
    ub = x - .54 * y + 5.1 * np.sin((x + .4 * y) / 61.0)
    qb = np.mod(ub + 9.1, 18.2) - 9.1
    branch_gate = np.clip((flow - .72) * 4.05, 0, 1)
    branch = np.clip(1 - np.abs(np.abs(qb) - 3.7) / 1.62, 0, 1) * branch_gate
    branch_core = np.clip(1 - np.abs(np.abs(qb) - 3.7) / .62, 0, 1) * branch_gate
    needle_accent = body * np.clip((.49 - survival) * 2.20, 0, 1)
    needle_glint = pair * needle_accent
    return tuple(np.asarray(a, np.float32) for a in (
        body, body_core, rim, pair, capillary, tip, ripple, cross, window,
        dorsal, ventral, violet, steel, wet_seam, gap, state, flow,
        laminate, laminate_core, trough, suture, suture_core, branch, branch_core,
        needle_accent, needle_glint,
    ))


def paint_damselfly_cobalt_i1(paint, shape, mask, seed, pm, bb):
    (body, body_core, rim, pair, capillary, tip, ripple, cross, window,
     dorsal, ventral, violet, steel, wet_seam, gap, state, flow,
     laminate, laminate_core, trough, suture, suture_core, branch, branch_core,
     needle_accent, needle_glint) = _surface(seed + 50261)
    ink = np.array([.008, .012, .030], np.float32)
    cobalt = np.array([.025, .18, .78], np.float32)
    electric = np.array([.05, .46, 1.0], np.float32)
    purple = np.array([.31, .055, .64], np.float32)
    steel_col = np.array([.56, .73, .86], np.float32)
    cyan = np.array([.02, .70, .82], np.float32)

    col = ink[None, None, :] * (.72 + .15 * (1 - flow[..., None]))
    col += cobalt[None, None, :] * (.14 + .29 * flow[..., None])
    col += purple[None, None, :] * (.035 + .15 * (1 - flow[..., None]))
    col *= 1 - trough[..., None] * .38
    col += laminate[..., None] * cobalt[None, None, :] * (.54 + .30 * flow[..., None])
    col += laminate_core[..., None] * electric[None, None, :] * .72
    col += branch[..., None] * purple[None, None, :] * .55
    col += branch_core[..., None] * cyan[None, None, :] * .52
    col += suture[..., None] * steel_col[None, None, :] * .57
    col += suture_core[..., None] * np.array([.64, .82, 1.0], np.float32) * .68
    col += needle_accent[..., None] * cobalt[None, None, :] * .27
    col += needle_glint[..., None] * electric[None, None, :] * .45
    col += window[..., None] * purple[None, None, :] * np.clip(needle_accent * .14, 0, 1)[..., None]
    col *= 1 - gap[..., None] * .075
    return _blend(paint, mask, pm, _resize(np.clip(col, 0, 1), shape))


def spec_damselfly_cobalt_i1(shape, seed, sm, base_m, base_r):
    (body, body_core, rim, pair, capillary, tip, ripple, cross, window,
     dorsal, ventral, violet, steel, wet_seam, gap, state, flow,
     laminate, laminate_core, trough, suture, suture_core, branch, branch_core,
     needle_accent, needle_glint) = _surface(seed + 50261)
    m = 30 + 190 * (.34 * laminate + .23 * branch_core + .17 * steel +
                    .12 * flow + .09 * laminate_core + .05 * tip)
    r = 22 + 198 * (.31 * trough + .24 * gap + .18 * ventral + .13 * capillary +
                    .09 * (1 - state) + .05 * needle_accent)
    cc = 20 + 205 * (.29 * suture_core + .22 * wet_seam + .17 * window +
                     .13 * rim + .11 * needle_glint + .08 * state)
    m += branch_core * 20 - ventral * 15
    r += capillary * 17 - suture_core * 20
    cc += suture_core * 24 + needle_glint * 17 - trough * 12
    m = np.mean(m) + 24.0 / max(float(np.std(m)), 1e-5) * (m - np.mean(m))
    r = np.mean(r) + 22.0 / max(float(np.std(r)), 1e-5) * (r - np.mean(r))
    cc = np.mean(cc) + 25.0 / max(float(np.std(cc)), 1e-5) * (cc - np.mean(cc))
    return (_resize(np.clip(m * sm, 0, 250), shape),
            _resize(np.clip(r, 5, 249), shape),
            _resize(np.clip(cc, 0, 255), shape))
