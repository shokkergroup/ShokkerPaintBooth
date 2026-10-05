# -*- coding: utf-8 -*-
"""Isolated explicit rejection rebuild for the 20 FRACTURED BLOOM finishes.

SPB-WILDS, 2026-08-24, rejection rebuild tick WR-B1.  Owner verdict:
"the biggest cardinal sin PERIOD of this app - LAZY" and "do NOT just put
random noise in the patterns to separate the way they look."  This candidate
therefore owns twenty literal botanical construction grammars.  The semantic
mark names below are executable masks, not labels attached after rendering.

All art is authored at 512 square.  Primitive strokes, lips, pores, anthers,
veins and seams are 2-8 work pixels (8-32 px at native 2048); recognizable
larger forms are connected assemblies of those fine marks.  There is no RNG,
sampled texture, wrapped source image, generic field-derivative router, grain,
fleck, or rank/equal-population quantizer in this module.  Biological density
comes from connected canvas-scale growth paths varied causally by branch,
node, growth age, handedness, or flow position.

The shared code is limited to palette, material, resize and registry plumbing.
Every builder defines at least seven causal masks plus explicit metallic-lobe
(A), clearcoat-lobe (B), or neutral (N) ownership.  M, R and Cc are composed
from different mask interiors, edges and halos, then snapped to fixed material
tiers.  Fourteen coherent authored colors are available to every finish.

This file is an unwired candidate.  Evidence lives under
``_wilds_rejection_work/bloom_explicit`` and must never be relabelled as owner
accepted without an actual owner review.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


_WORK = 512
_CALM_SPEC = np.asarray([4.0, 120.0, 16.0], np.float32)


@dataclass
class _Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    tone: np.ndarray


def _f32(a: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


@lru_cache(maxsize=1)
def _xy() -> Tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:_WORK, 0:_WORK].astype(np.float32)
    return x, y


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return np.zeros_like(a) if hi - lo < 1.0e-7 else (a - lo) / (hi - lo)


def _line(v: np.ndarray, half_width: float = 1.25) -> np.ndarray:
    return _f32(1.0 - np.abs(np.asarray(v, np.float32)) / max(0.25, float(half_width)))


def _ring(distance: np.ndarray, radius, half_width: float = 1.0) -> np.ndarray:
    return _line(np.asarray(distance, np.float32) - np.asarray(radius, np.float32), half_width)


def _inside(distance: np.ndarray, radius, feather: float = 0.8) -> np.ndarray:
    return _f32((np.asarray(radius, np.float32) - np.asarray(distance, np.float32))
                / max(0.2, float(feather)) + 0.5)


def _edge(mask: np.ndarray, width: int = 1) -> np.ndarray:
    u = _f32(mask)
    k = 2 * max(1, int(width)) + 1
    kernel = np.ones((k, k), np.uint8)
    return _f32(cv2.dilate(u, kernel) - cv2.erode(u, kernel))


def _halo(mask: np.ndarray, sigma: float = 1.6) -> np.ndarray:
    u = _f32(mask)
    return _f32(cv2.GaussianBlur(u, (0, 0), max(0.25, float(sigma))) - 0.32 * u)


def _new_marks(*names: str) -> Dict[str, np.ndarray]:
    return {name: np.zeros((_WORK, _WORK), np.float32) for name in names}


def _draw_line(mask: np.ndarray, a, b, value=1.0, width=1) -> None:
    cv2.line(mask, tuple(map(int, a)), tuple(map(int, b)), float(value),
             int(width), cv2.LINE_AA)


def _draw_circle(mask: np.ndarray, center, radius, value=1.0, width=1) -> None:
    cv2.circle(mask, tuple(map(int, center)), int(max(1, radius)), float(value),
               int(width), cv2.LINE_AA)


def _draw_poly(mask: np.ndarray, points, value=1.0, width=1, fill=False) -> None:
    pts = np.asarray(points, np.int32).reshape((-1, 1, 2))
    if fill:
        cv2.fillPoly(mask, [pts], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(mask, [pts], True, float(value), int(width), cv2.LINE_AA)


def _pack(masks: Mapping[str, np.ndarray], banks: Mapping[str, str], tone: np.ndarray) -> _Grammar:
    if len(masks) < 7:
        raise ValueError("lazy Bloom grammar: fewer than seven causal marks")
    marks = []
    for name, mask in masks.items():
        u = _f32(mask)
        # A two-work-pixel AA shoulder is the minimum car-scale feature.  This
        # is visibility plumbing, not a uniqueness perturbation: it preserves
        # the exact causal topology while preventing one-pixel hairlines.
        shoulder = cv2.dilate(u, np.ones((2, 2), np.uint8))
        u = np.maximum(u, 0.72 * shoulder)
        if float(u.std()) < 0.0015:
            raise ValueError(f"flat Bloom causal mark {name!r}")
        bank = str(banks[name])
        if bank not in {"A", "B", "N"}:
            raise ValueError(f"invalid material bank {bank!r}")
        marks.append((name, u, bank))
    if not ({"A", "B"} <= {bank for _name, _mask, bank in marks}):
        raise ValueError("Bloom grammar lacks explicit A/B ownership")
    return _Grammar(tuple(marks), _norm(tone).astype(np.float32))


def _hsv(h: float, s: float, v: float) -> np.ndarray:
    px = np.uint8([[[int((h % 1.0) * 179.0), int(np.clip(s, 0, 1) * 255),
                     int(np.clip(v, 0, 1) * 255)]]])
    return cv2.cvtColor(px, cv2.COLOR_HSV2RGB)[0, 0].astype(np.float32) / 255.0


def _palette(hues: Sequence[float], saturation: Sequence[float]):
    ha, hb = float(hues[0]), float(hues[1])
    sa, sb = float(saturation[0]), float(saturation[1])
    values = (0.20, 0.31, 0.43, 0.58, 0.75, 0.93)
    a = np.stack([_hsv(ha + 0.017 * (i - 2.5),
                       min(0.96, sa * (0.78 + i * 0.055)), values[i])
                  for i in range(6)])
    b = np.stack([_hsv(hb - 0.019 * (i - 2.5),
                       min(0.96, sb * (1.05 - i * 0.045)), values[i])
                  for i in range(6)])
    bridge = np.stack([_hsv((ha + hb) * 0.5 + 0.50, 0.18, 0.13),
                       _hsv((ha + hb) * 0.5 + 0.08, 0.28, 0.62)])
    return a.astype(np.float32), b.astype(np.float32), bridge.astype(np.float32)


_COLOR_BANDS = np.asarray([0.12, 0.27, 0.43, 0.60, 0.78], np.float32)
_M_TIERS = np.asarray([8, 36, 68, 104, 142, 180, 220, 252], np.uint8)
_R_TIERS = np.asarray([18, 46, 76, 108, 140, 172, 204, 232], np.uint8)
_C_TIERS = np.asarray([10, 40, 72, 106, 144, 184, 224, 252], np.uint8)
_SPEC_BANDS = np.asarray([28, 60, 92, 124, 156, 188, 220], np.float32)


def _bank_image(bank: np.ndarray, tone: np.ndarray, phase: int) -> np.ndarray:
    idx = np.digitize(np.mod(tone + phase * 0.091, 1.0), _COLOR_BANDS)
    return bank[idx]


def _fixed_tiers(channel: np.ndarray, tiers: np.ndarray) -> np.ndarray:
    return tiers[np.digitize(np.clip(channel, 0, 255), _SPEC_BANDS)]


def _compose(grammar: _Grammar, hues: Sequence[float], saturation=(0.92, 0.92)):
    bank_a, bank_b, neutral = _palette(hues, saturation)
    tone = grammar.tone
    ground = 0.76 * neutral[0] + 0.24 * bank_a[0]
    paint_num = np.broadcast_to(ground, (_WORK, _WORK, 3)).copy() * 0.18
    paint_den = np.full((_WORK, _WORK, 1), 0.18, np.float32)
    # A restrained lobe-A ground is actual coating material, not empty black
    # canvas.  Fine feature masks still own the visible topology and all spec
    # variation; the ground remains perfectly calm in M/R/Cc.
    a_owner = np.zeros((_WORK, _WORK), np.float32)
    b_owner = np.zeros_like(a_owner)

    # WR-B4 / owner verdict 2026-08-24: the previous three phase-band
    # substrates were mechanically different only because ``tone`` differed.
    # In a contact sheet they still read as the same spec recipe under twenty
    # silhouettes -- exactly the recolour/spec-map waste the owner rejected.
    # Start from genuinely calm material and let named physical anatomy own
    # every visible M/R/Cc variation.  This deliberately removes the shared
    # sinusoidal carrier instead of disguising it with noise. W4 additionally
    # replaces the universal insertion-order material recipe: every builder
    # now supplies literal feature-named M/R/Cc arrays, and the host only
    # consumes those authored channels.
    for i, (_name, mask, owner) in enumerate(grammar.marks):
        color = (_bank_image(bank_a, tone, i) if owner == "A" else
                 _bank_image(bank_b, tone, i) if owner == "B" else
                 np.broadcast_to(neutral[1], paint_num.shape))
        weight = np.clip(mask * (0.78 + 0.055 * (i % 4)), 0.0, 1.0)
        paint_num += color * weight[..., None]
        paint_den += weight[..., None]

        if owner == "A":
            a_owner = np.maximum(a_owner, mask)
        elif owner == "B":
            b_owner = np.maximum(b_owner, mask)

    paint = paint_num / np.maximum(paint_den, 1.0e-6)
    m, r, cc = (np.asarray(ch, np.float32).copy()
                for ch in grammar.explicit_spec)

    junction = _f32(_edge(a_owner, 1) * _edge(b_owner, 1))
    paint = paint * (1.0 - 0.68 * junction[..., None]) + neutral[1] * (0.68 * junction[..., None])
    m = m * (1.0 - junction) + 124.0 * junction
    r = r * (1.0 - junction) + 26.0 * junction
    cc = cc * (1.0 - junction) + 236.0 * junction

    spec = np.dstack([_fixed_tiers(m, _M_TIERS),
                      _fixed_tiers(r, _R_TIERS),
                      _fixed_tiers(cc, _C_TIERS)]).astype(np.uint8)
    return np.clip(paint, 0, 1).astype(np.float32), spec


# ---------------------------------------------------------------------------
# Twenty executable botanical grammars.  Each function is intentionally
# self-describing: the named anatomy is the actual mask ancestry.


def _build_fbl_magenta_whorl() -> _Grammar:
    """One asymmetric fiddlehead crozier with leaves owned by its coiled rachis."""
    m = _new_marks("coiled_rachis", "pinna_sweeps", "pinna_blades",
                   "vascular_forks", "sori_cups", "crozier_scales",
                   "torn_margins", "overlap_scars")
    tone = np.zeros((_WORK, _WORK), np.float32)
    t = np.linspace(0.0, 1.0, 401, dtype=np.float32)
    angle = -0.36 + 4.72 * np.pi * t + 0.21 * np.sin(t * 5.0 * np.pi)
    radius = 302.0 * (1.0 - t) ** 0.73 + 7.0
    sx = 286.0 + 0.86 * radius * np.cos(angle)
    sy = 253.0 + 0.74 * radius * np.sin(angle)
    cv2.polylines(m["coiled_rachis"],
                  [np.column_stack((sx, sy)).astype(np.int32)], False,
                  1.0, 4, cv2.LINE_AA)

    nodes = (7, 14, 24, 32, 44, 53, 64, 72, 85, 95, 103, 115,
             124, 135, 143, 156, 166, 174, 186, 195, 206, 214,
             227, 237, 245, 257, 266, 277, 285, 298, 308, 316,
             328, 337, 348, 356, 369, 379, 387, 396)
    previous_tip = None
    for n, k in enumerate(nodes):
        px, py = float(sx[k]), float(sy[k])
        tx = float(sx[min(k + 3, 400)] - sx[max(k - 3, 0)])
        ty = float(sy[min(k + 3, 400)] - sy[max(k - 3, 0)])
        tangent = np.arctan2(ty, tx)
        side = -1.0 if n % 2 else 1.0
        length = (24.0 + 56.0 * np.sin(np.pi * k / 400.0) ** 0.72
                  + 13.0 * np.sin(n * 1.73) ** 2)
        branch_angle = tangent + side * (0.91 + 0.22 * np.sin(n * 1.19))
        ex = px + length * np.cos(branch_angle)
        ey = py + length * np.sin(branch_angle)
        cx = px + length * 0.52 * np.cos(branch_angle - side * 0.31)
        cy = py + length * 0.52 * np.sin(branch_angle - side * 0.31)
        q = np.linspace(0.0, 1.0, 29, dtype=np.float32)
        bx = (1-q)**2*px + 2*(1-q)*q*cx + q*q*ex
        by = (1-q)**2*py + 2*(1-q)*q*cy + q*q*ey
        cv2.polylines(m["pinna_sweeps"],
                      [np.column_stack((bx, by)).astype(np.int32)], False,
                      1.0, 2, cv2.LINE_AA)
        cv2.ellipse(m["pinna_blades"], (int(ex), int(ey)),
                    (5 + n % 3, 2 + (n + 1) % 2), np.degrees(branch_angle),
                    0, 360, 1.0, -1, cv2.LINE_AA)
        _draw_line(m["vascular_forks"], (bx[14], by[14]),
                   (bx[14] + 9*np.cos(branch_angle + side*0.58),
                    by[14] + 9*np.sin(branch_angle + side*0.58)), width=1)
        _draw_circle(m["sori_cups"],
                     (ex - 3*np.cos(branch_angle), ey - 3*np.sin(branch_angle)),
                     2 + n % 2, width=1)
        cv2.ellipse(m["crozier_scales"], (int(px), int(py)),
                    (4 + n % 3, 2), np.degrees(tangent), 25, 305,
                    1.0, 1, cv2.LINE_AA)
        if n in (3, 8, 14, 19):
            _draw_line(m["torn_margins"],
                       (ex - 4*np.sin(branch_angle), ey + 4*np.cos(branch_angle)),
                       (ex + 5*np.sin(branch_angle), ey - 5*np.cos(branch_angle)), width=1)
        if previous_tip is not None and n in (6, 11, 16, 21):
            _draw_line(m["overlap_scars"], previous_tip, (bx[18], by[18]), width=1)
        previous_tip = (ex, ey)
        cv2.circle(tone, (int(px), int(py)), 7, (n % 11) / 10.0, -1)
    banks = dict(coiled_rachis="A", pinna_sweeps="B", pinna_blades="B",
                 vascular_forks="A", sori_cups="B", crozier_scales="N",
                 torn_margins="N", overlap_scars="A")
    ancestry = tone + 0.55*m["coiled_rachis"] + 0.41*m["pinna_sweeps"] + 0.27*m["pinna_blades"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.2))


def _build_fbl_leafvine_drape() -> _Grammar:
    """One canvas-spanning climbing graph with leaves owned by its branches."""
    m = _new_marks("climbing_stems", "branch_sweeps", "node_collars",
                   "alternating_leaf_pairs", "leaf_midribs", "tendril_loops",
                   "seed_pods", "underpasses")
    tone = np.zeros((_WORK, _WORK), np.float32)
    t = np.linspace(0.0, 1.0, 241, dtype=np.float32)
    trunk_x = 18.0 + 478.0 * t + 27.0 * np.sin(t * np.pi * 4.2) + 11.0 * np.sin(t * np.pi * 13.0)
    trunk_y = 500.0 - 480.0 * t + 49.0 * np.sin(t * np.pi * 3.1 + 0.35)
    trunk = np.column_stack((trunk_x, trunk_y)).astype(np.int32)
    cv2.polylines(m["climbing_stems"], [trunk], False, 1.0, 3, cv2.LINE_AA)
    node_t = (0.025, 0.061, 0.104, 0.151, 0.207, 0.263, 0.322, 0.378,
              0.441, 0.503, 0.566, 0.631, 0.694, 0.752, 0.814, 0.871,
              0.919, 0.958)
    previous_tendril = None
    for n, tn in enumerate(node_t):
        k = int(tn * (len(t) - 1))
        sx, sy = float(trunk_x[k]), float(trunk_y[k])
        dx = float(trunk_x[min(k + 2, len(t) - 1)] - trunk_x[max(k - 2, 0)])
        dy = float(trunk_y[min(k + 2, len(t) - 1)] - trunk_y[max(k - 2, 0)])
        tangent = np.arctan2(dy, dx)
        side = -1.0 if n % 2 else 1.0
        length = 102.0 + 104.0 * (0.5 + 0.5 * np.sin(n * 2.173))
        angle = tangent + side * (0.76 + 0.26 * np.sin(n * 1.31))
        ex, ey = sx + length * np.cos(angle), sy + length * np.sin(angle)
        cx = sx + length * 0.43 * np.cos(angle + side * 0.48)
        cy = sy + length * 0.43 * np.sin(angle + side * 0.48)
        q = np.linspace(0.0, 1.0, 39, dtype=np.float32)
        bx = (1-q)**2 * sx + 2*(1-q)*q*cx + q*q*ex
        by = (1-q)**2 * sy + 2*(1-q)*q*cy + q*q*ey
        branch = np.column_stack((bx, by)).astype(np.int32)
        cv2.polylines(m["branch_sweeps"], [branch], False, 1.0, 2, cv2.LINE_AA)
        for fork_j in (14, 27):
            fsx,fsy=float(bx[fork_j]),float(by[fork_j])
            fork_side=-side if fork_j==14 else side
            fa=angle+fork_side*(0.58+0.12*np.sin(n+fork_j))
            fl=42.0+31.0*(0.5+0.5*np.sin(n*1.89+fork_j))
            fex,fey=fsx+fl*np.cos(fa),fsy+fl*np.sin(fa)
            _draw_line(m["branch_sweeps"],(fsx,fsy),(fex,fey),width=1)
            cv2.ellipse(m["alternating_leaf_pairs"],(int(fex),int(fey)),(7,3),
                        np.degrees(fa),0,360,1.0,-1,cv2.LINE_AA)
            _draw_line(m["leaf_midribs"],(fex-5*np.cos(fa),fey-5*np.sin(fa)),(fex,fey),width=1)
        _draw_circle(m["node_collars"], (sx, sy), 3 + n % 2, width=1)
        for j in range(5, 37, 5):
            px, py = float(bx[j]), float(by[j])
            tx, ty = float(bx[min(j+1, 38)]-bx[max(j-1, 0)]), float(by[min(j+1, 38)]-by[max(j-1, 0)])
            leaf_side = -1.0 if (j // 5 + n) % 2 else 1.0
            leaf_ang = np.degrees(np.arctan2(ty, tx) + leaf_side * 1.02)
            lx = px + leaf_side * 4.2 * np.cos(np.radians(leaf_ang))
            ly = py + leaf_side * 4.2 * np.sin(np.radians(leaf_ang))
            cv2.ellipse(m["alternating_leaf_pairs"], (int(lx), int(ly)),
                        (6 + (n+j) % 3, 2 + (n % 2)), leaf_ang, 0, 360, 1.0, -1, cv2.LINE_AA)
            _draw_line(m["leaf_midribs"], (px, py), (lx, ly), width=1)
            cv2.circle(tone, (int(px), int(py)), 6, ((n * 5 + j) % 13) / 12.0, -1)
        _draw_circle(m["tendril_loops"], (ex, ey), 5 + (n % 4), width=1)
        cv2.ellipse(m["seed_pods"], (int(ex - side * 6), int(ey + side * 3)),
                    (7, 2 + (n % 2)), np.degrees(angle), 0, 360, 1.0, -1, cv2.LINE_AA)
        if previous_tendril is not None and n in (4, 7, 11, 15):
            _draw_line(m["underpasses"], previous_tendril, (ex, ey), width=1)
        previous_tendril = (ex, ey)
    banks = dict(climbing_stems="A", branch_sweeps="B", node_collars="N",
                 alternating_leaf_pairs="B", leaf_midribs="A", tendril_loops="B",
                 seed_pods="A", underpasses="N")
    ancestry=tone+0.62*m["climbing_stems"]+0.48*m["branch_sweeps"]+0.36*m["alternating_leaf_pairs"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 7.0))


def _build_fbl_butter_pollen() -> _Grammar:
    """One ruptured grain feeding a canvas-spanning germination tube."""
    m = _new_marks("exine_shell", "aperture_rim", "tube_walls",
                   "cytoplasmic_streams", "callose_plugs", "rupture_folds",
                   "tip_vesicle_crown", "stigma_contacts", "exine_ribs")
    tone = np.zeros((_WORK, _WORK), np.float32)
    center = (73.0, 355.0)
    aa = np.linspace(-0.22, 2.0*np.pi-0.22, 251, dtype=np.float32)
    rr = 78.0 + 9.0*np.sin(aa*5.0+0.4) + 5.0*np.sin(aa*11.0-0.7)
    gx = center[0] + rr*np.cos(aa)
    gy = center[1] + 0.91*rr*np.sin(aa)
    cv2.polylines(m["exine_shell"],
                  [np.column_stack((gx, gy)).astype(np.int32)], True,
                  1.0, 3, cv2.LINE_AA)
    for rib in range(25):
        a = -2.86 + rib*0.247 + 0.05*np.sin(rib*1.7)
        inner = (center[0]+17*np.cos(a), center[1]+15*np.sin(a))
        outer = (center[0]+(67+rib%6)*np.cos(a),
                 center[1]+0.91*(67+rib%6)*np.sin(a))
        _draw_line(m["exine_ribs"], inner, outer, width=1)

    t = np.linspace(0.0, 1.0, 321, dtype=np.float32)
    tx = 118.0 + 370.0*t + 28.0*np.sin(t*5.0*np.pi)
    ty = 365.0 - 250.0*t + 70.0*np.sin(t*3.2*np.pi+0.3) + 23.0*np.sin(t*9.0*np.pi)
    dx = np.gradient(tx); dy = np.gradient(ty); mag = np.maximum(1.0, np.hypot(dx, dy))
    nx, ny = -dy/mag, dx/mag
    for offset in (-11.0, -7.0, 7.0, 11.0):
        px, py = tx + offset*nx, ty + offset*ny
        cv2.polylines(m["tube_walls"],
                      [np.column_stack((px, py)).astype(np.int32)], False,
                      1.0, 2 if abs(offset) > 9 else 1, cv2.LINE_AA)
    for offset in (-4.0, 0.0, 4.0):
        wobble = 1.8*np.sin(t*17.0*np.pi + offset)
        px, py = tx + (offset+wobble)*nx, ty + (offset+wobble)*ny
        cv2.polylines(m["cytoplasmic_streams"],
                      [np.column_stack((px, py)).astype(np.int32)], False,
                      1.0, 1, cv2.LINE_AA)
    for k in (31, 49, 70, 91, 119, 151, 184, 214, 245, 274, 299):
        span = 8.0 + (k % 4)
        _draw_line(m["callose_plugs"], (tx[k]-span*nx[k], ty[k]-span*ny[k]),
                   (tx[k]+span*nx[k], ty[k]+span*ny[k]), width=2)
        cv2.circle(tone, (int(tx[k]), int(ty[k])), 9, (k % 19)/18.0, -1)
    cv2.ellipse(m["aperture_rim"], (112, 340), (13, 8), -18,
                0, 360, 1.0, 2, cv2.LINE_AA)
    for fold in range(11):
        a = -0.53 + fold*0.105
        _draw_line(m["rupture_folds"],
                   (104+fold%3, 340+fold-5),
                   (82+28*np.cos(a), 355+25*np.sin(a)), width=1)
    tip = (float(tx[-1]), float(ty[-1]))
    tip_angle = np.arctan2(dy[-1], dx[-1])
    for branch in range(13):
        a = tip_angle - 1.02 + branch*0.17 + 0.05*np.sin(branch*1.9)
        length = 21.0 + 6.0*np.sin(branch*1.3)**2
        end = (tip[0]+length*np.cos(a), tip[1]+length*np.sin(a))
        _draw_line(m["tip_vesicle_crown"], tip, end, width=1)
        cv2.ellipse(m["stigma_contacts"], (int(end[0]), int(end[1])),
                    (4+branch%3, 2), np.degrees(a), 0, 360,
                    1.0, 1, cv2.LINE_AA)
    banks = dict(exine_shell="A", aperture_rim="B", tube_walls="B",
                 cytoplasmic_streams="A", callose_plugs="N", rupture_folds="B",
                 tip_vesicle_crown="A", stigma_contacts="B", exine_ribs="N")
    ancestry = tone + 0.55*m["tube_walls"] + 0.43*m["cytoplasmic_streams"] + 0.35*m["exine_shell"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.0))


def _build_fbl_pink_rose() -> _Grammar:
    """A single rose topography of nested, non-crossing scalloped petals."""
    m=_new_marks("petal_shells","curled_margins","petal_midribs","sepals",
                 "stamen_arcs","dew_cups","inter_petal_slits","central_throats")
    tone=np.zeros((_WORK,_WORK),np.float32); center=(267.0,244.0)
    angles=np.linspace(0,2*np.pi,361,dtype=np.float32)
    for layer in range(1,42):
        base=5.0+layer*6.55
        count=3+min(7,layer//5)
        phase=layer*0.239+0.24*np.sin(layer*0.91)
        amp=1.6+0.21*layer
        rr=base+amp*np.sin(count*angles+phase)+1.8*np.sin((count+3)*angles-layer*0.11)
        px=center[0]+rr*np.cos(angles); py=center[1]+0.92*rr*np.sin(angles)
        key="curled_margins" if layer%4==0 else "petal_shells"
        cv2.polylines(m[key],[np.column_stack((px,py)).astype(np.int32)],True,1.0,
                      2 if layer%7==0 else 1,cv2.LINE_AA)
        if layer%3==1:
            cv2.circle(tone,(int(center[0]+base*np.cos(phase)),int(center[1]+0.92*base*np.sin(phase))),
                       8,(layer%17)/16.0,-1)
    for ray in range(13):
        a=ray*2*np.pi/13.0+0.12*np.sin(ray*1.77)
        rr=np.linspace(18,274,70); aa=a+0.16*np.sin(rr/49.0+ray)
        px=center[0]+rr*np.cos(aa); py=center[1]+0.92*rr*np.sin(aa)
        cv2.polylines(m["petal_midribs"],[np.column_stack((px,py)).astype(np.int32)],False,1.0,1,cv2.LINE_AA)
        if ray%3==0:
            _draw_line(m["inter_petal_slits"],(px[29],py[29]),(px[37],py[37]),width=2)
        if ray%4==0:
            _draw_circle(m["dew_cups"],(px[43],py[43]),2+ray%3,width=1)
    for ray in range(11):
        a=ray*2*np.pi/11.0+0.31
        cv2.ellipse(m["sepals"],(int(center[0]+254*np.cos(a)),int(center[1]+235*np.sin(a))),
                    (13,4),np.degrees(a),0,360,1.0,1,cv2.LINE_AA)
    for rr in (4,8,13,19,26,34): _draw_circle(m["stamen_arcs"],center,rr,width=1)
    _draw_circle(m["central_throats"],center,5,width=-1)
    masks=m
    banks = dict(petal_shells="A", curled_margins="B", petal_midribs="N",
                 sepals="B", stamen_arcs="A", dew_cups="B",
                 inter_petal_slits="N", central_throats="A")
    return _pack(masks, banks, cv2.GaussianBlur(tone+0.38*m["petal_shells"],(0,0),2.1))


def _build_fbl_coral_cluster() -> _Grammar:
    """One kidney-shaped coral atoll carrying inward and outward antler forks."""
    m=_new_marks("branch_trunks","fork_tips","axial_mouths","radial_septa",
                 "calices","growth_rings","living_polyps","bridge_scars")
    tone=np.zeros((_WORK,_WORK),np.float32)
    tt=np.linspace(0,2*np.pi,361,dtype=np.float32)
    reef_x=256.0+188.0*np.cos(tt)+31.0*np.cos(3*tt+0.4)
    reef_y=254.0+139.0*np.sin(tt)+27.0*np.sin(4*tt-0.5)
    reef=np.column_stack((reef_x,reef_y)).astype(np.int32)
    cv2.polylines(m["branch_trunks"],[reef],True,1.0,4,cv2.LINE_AA)
    terminals=[]
    for root in range(29):
        k=4+root*12
        sx,sy=float(reef_x[k]),float(reef_y[k])
        tx,ty=float(reef_x[k+2]-reef_x[k-2]),float(reef_y[k+2]-reef_y[k-2])
        tangent=np.arctan2(ty,tx); side=-1.0 if root%3==0 else 1.0
        initial=tangent+side*(np.pi/2+0.13*np.sin(root*1.7))
        stack=[(sx,sy,initial,57.0+33.0*(0.5+0.5*np.sin(root*1.29)),0,root+1)]
        while stack:
            px,py,angle,length,depth,identity=stack.pop()
            bend=0.14*np.sin(identity*1.41+depth)
            ex,ey=px+length*np.cos(angle+bend),py+length*np.sin(angle+bend)
            cx=px+length*0.48*np.cos(angle-bend*1.5)
            cy=py+length*0.48*np.sin(angle-bend*1.5)
            q=np.linspace(0,1,19,dtype=np.float32)
            bx=(1-q)**2*px+2*(1-q)*q*cx+q*q*ex
            by=(1-q)**2*py+2*(1-q)*q*cy+q*q*ey
            cv2.polylines(m["branch_trunks"],[np.column_stack((bx,by)).astype(np.int32)],False,
                          1.0,2 if depth<2 else 1,cv2.LINE_AA)
            _draw_circle(m["growth_rings"],(ex,ey),3+depth,width=1)
            cv2.circle(tone,(int(ex),int(ey)),6,((identity+depth*3)%17)/16.0,-1)
            if depth<3:
                _draw_circle(m["fork_tips"],(ex,ey),2,width=-1)
                spread=0.39+0.09*np.sin(identity*0.83)
                stack.append((ex,ey,angle-spread,length*0.61,depth+1,identity*2))
                stack.append((ex,ey,angle+spread*0.88,length*0.58,depth+1,identity*2+1))
            else:
                _draw_circle(m["calices"],(ex,ey),5+identity%3,width=1)
                _draw_circle(m["axial_mouths"],(ex,ey),2+identity%2,width=1)
                for ray in range(6):
                    a=ray*np.pi/3+identity*0.17
                    _draw_line(m["radial_septa"],(ex,ey),(ex+5*np.cos(a),ey+5*np.sin(a)),width=1)
                _draw_circle(m["living_polyps"],(ex+2*np.cos(identity),ey+2*np.sin(identity)),1,width=-1)
                terminals.append((ex,ey))
    for i in range(0,len(terminals)-9,17):
        _draw_line(m["bridge_scars"],terminals[i],terminals[i+9],width=1)
    banks = dict(branch_trunks="A", fork_tips="B", axial_mouths="N",
                 radial_septa="B", calices="A", growth_rings="N",
                 living_polyps="B", bridge_scars="A")
    return _pack(m, banks, cv2.GaussianBlur(tone + 0.45 * m["branch_trunks"], (0, 0), 2.0))


def _build_fbl_butter_mosaic() -> _Grammar:
    """One giant ginkgo marquetry divided by an organic branching vein tree."""
    x, y = _xy()
    lx, ly = x - 252.0, 548.0 - y
    radius = np.hypot(lx, ly)
    theta = np.arctan2(ly, lx)
    fan = _f32((theta-0.13)/0.055) * _f32((np.pi-0.13-theta)/0.055) * _f32((530.0-radius)/8.0)
    m=_new_marks("grout","florets","buttons","scars")
    origin=(252.0,548.0)
    for vein in range(27):
        u=vein/26.0
        a=0.15+(np.pi-0.30)*u+0.045*np.sin(vein*2.17)
        length=478.0+17.0*np.sin(vein*1.31)
        ex,ey=origin[0]+length*np.cos(a),origin[1]-length*np.sin(a)
        cx=origin[0]+length*0.53*np.cos(a+0.15*np.sin(vein*1.7))
        cy=origin[1]-length*0.53*np.sin(a+0.15*np.sin(vein*1.7))
        q=np.linspace(0.04,1.0,67,dtype=np.float32)
        bx=(1-q)**2*origin[0]+2*(1-q)*q*cx+q*q*ex
        by=(1-q)**2*origin[1]+2*(1-q)*q*cy+q*q*ey
        cv2.polylines(m["grout"],[np.column_stack((bx,by)).astype(np.int32)],False,1.0,
                      2 if vein%5==0 else 1,cv2.LINE_AA)
        for j in (18,31,45,57):
            side=-1.0 if (j//13+vein)%2 else 1.0
            tx,ty=bx[j+2]-bx[j-2],by[j+2]-by[j-2]; tangent=np.arctan2(ty,tx)
            branch_len=18.0+26.0*np.sin(np.pi*j/67.0)+7.0*np.sin(vein*j)
            ba=tangent+side*(0.62+0.17*np.sin(vein+j))
            px,py=bx[j]+branch_len*np.cos(ba),by[j]+branch_len*np.sin(ba)
            _draw_line(m["grout"],(bx[j],by[j]),(px,py),width=1)
            _draw_circle(m["florets"],(px,py),3+(vein+j)%3,width=1)
            if (vein+j)%7==0: _draw_line(m["scars"],(px-4,py+2),(px+5,py-2),width=1)
        if vein%3==0: _draw_circle(m["buttons"],(bx[11],by[11]),3+vein%4,width=1)
    grout=cv2.dilate(m["grout"],np.ones((5,5),np.uint8))*fan; faces=fan
    florets=m["florets"]*fan; buttons=m["buttons"]*fan; scars=m["scars"]*fan
    ray_petals = _ring(radius, 476.0 + 9.0*np.sin(theta*13.0), 0.80) * fan
    bevels = _halo(grout, 1.35) * fan
    overlap = np.maximum(_edge(fan, 1),_halo(faces*grout,2.0)*(1.0-grout))
    plate_lamina = _halo(grout, 3.2) * fan * (1.0-grout)
    masks = dict(plate_lamina=plate_lamina, grout_seams=grout, floret_stamps=florets,
                 ray_petals=ray_petals, button_centers=buttons,
                 bevel_lips=bevels, missing_tile_scars=scars,
                 floral_overlap_lips=overlap)
    banks = dict(plate_lamina="A", grout_seams="B", floret_stamps="B",
                 ray_petals="A", button_centers="B", bevel_lips="B",
                 missing_tile_scars="N", floral_overlap_lips="A")
    return _pack(masks, banks, _norm(radius/520.0+theta/np.pi+0.37*cv2.GaussianBlur(grout,(0,0),3.0)))


def _build_fbl_pink_pollen() -> _Grammar:
    """One fused pollinium whose four lobes share one irregular outer membrane."""
    x, y = _xy()
    m = _new_marks("tetrad_boundaries", "fusion_sutures", "exine_ridges",
                   "germ_apertures", "rupture_forks", "adhesion_necks",
                   "pressure_crescents", "callose_scars", "overlap_collars")
    tone = np.zeros((_WORK, _WORK), np.float32)
    specs = ((188.0, 198.0, 164.0, 116.0, 0.18, 0.2),
             (332.0, 132.0, 137.0, 78.0, -0.31, 1.1),
             (365.0, 326.0, 124.0, 148.0, 0.47, 2.0),
             (143.0, 374.0, 98.0, 114.0, -0.52, 2.8))
    lobes = []
    aa = np.linspace(0.0, 2.0*np.pi, 241, dtype=np.float32)
    for identity, (cx, cy, rx, ry, rotation, phase) in enumerate(specs):
        ca, sa = np.cos(rotation), np.sin(rotation)
        dx, dy = x-cx, y-cy
        ux, uy = ca*dx+sa*dy, -sa*dx+ca*dy
        angle = np.arctan2(uy/ry, ux/rx)
        distance = np.hypot(ux/rx, uy/ry)
        boundary = 1.0 + 0.09*np.sin(angle*(3+identity)+phase) + 0.05*np.sin(angle*(7+2*identity)-phase)
        lobes.append(_f32((boundary-distance)/0.018))
        radial = 1.0 + 0.09*np.sin(aa*(3+identity)+phase) + 0.05*np.sin(aa*(7+2*identity)-phase)
        px = cx + ca*(rx*radial*np.cos(aa)) - sa*(ry*radial*np.sin(aa))
        py = cy + sa*(rx*radial*np.cos(aa)) + ca*(ry*radial*np.sin(aa))
        cv2.polylines(m["tetrad_boundaries"],
                      [np.column_stack((px, py)).astype(np.int32)], True,
                      1.0, 3, cv2.LINE_AA)
    union = np.maximum.reduce(lobes)
    # The four developmental lobes are internal anatomy, not four stamped
    # glyphs.  Only the outer edge of their fused pollinium is visible.
    m["tetrad_boundaries"] = _edge(union, 1)

    # Lobe 0: a bent aperture fan.
    pore0 = (143.0, 173.0)
    cv2.ellipse(m["germ_apertures"], (143, 173), (18, 10), 24,
                0, 360, 1.0, 2, cv2.LINE_AA)
    for n, a in enumerate((-2.71, -2.42, -2.11, -1.77, -1.39, -0.98,
                           -0.55, -0.09, 0.38, 0.82, 1.21, 1.58, 1.92)):
        length = 73.0 + 29.0*np.sin(n*1.31)**2
        ex, ey = pore0[0]+length*np.cos(a), pore0[1]+length*np.sin(a)
        control = ((pore0[0]+ex)*0.5+17*np.cos(a+1.1),
                   (pore0[1]+ey)*0.5+13*np.sin(a+1.1))
        q = np.linspace(0.0, 1.0, 29, dtype=np.float32)
        bx = (1-q)**2*pore0[0]+2*(1-q)*q*control[0]+q*q*ex
        by = (1-q)**2*pore0[1]+2*(1-q)*q*control[1]+q*q*ey
        cv2.polylines(m["exine_ridges"], [np.column_stack((bx, by)).astype(np.int32)],
                      False, 1.0, 1, cv2.LINE_AA)
        if n in (2, 6, 10):
            _draw_line(m["rupture_forks"], (bx[18], by[18]),
                       (bx[18]+14*np.cos(a+0.63), by[18]+14*np.sin(a+0.63)), width=1)

    # Lobe 1: one crooked comb spine rather than a copied fan.
    q = np.linspace(0.0, 1.0, 151, dtype=np.float32)
    sx = 273.0 + 151.0*q + 13.0*np.sin(q*4.0*np.pi)
    sy = 102.0 + 72.0*q + 26.0*np.sin(q*2.3*np.pi+0.4)
    cv2.polylines(m["exine_ridges"], [np.column_stack((sx, sy)).astype(np.int32)],
                  False, 1.0, 3, cv2.LINE_AA)
    for n, k in enumerate((8, 17, 29, 42, 56, 71, 87, 104, 122, 139)):
        tx, ty = sx[min(k+2,150)]-sx[max(k-2,0)], sy[min(k+2,150)]-sy[max(k-2,0)]
        a = np.arctan2(ty, tx) + (-1.0 if n%2 else 1.0)*(0.83+0.07*n)
        length = 24.0 + 18.0*np.sin(n*1.7)**2
        _draw_line(m["rupture_forks"], (sx[k], sy[k]),
                   (sx[k]+length*np.cos(a), sy[k]+length*np.sin(a)), width=1)
    cv2.ellipse(m["germ_apertures"], (366, 123), (13, 21), -37,
                20, 342, 1.0, 2, cv2.LINE_AA)

    # Lobe 2: two crossing lamellae with asymmetric side veins.
    for branch_index, phase in enumerate((0.2, 1.1)):
        q = np.linspace(0.0, 1.0, 151, dtype=np.float32)
        sx = 244.0 + 212.0*q + 17.0*np.sin(q*3.0*np.pi+phase)
        sy = 391.0 - 112.0*q + (41.0 if branch_index == 0 else -37.0)*np.sin(q*np.pi)
        cv2.polylines(m["exine_ridges"], [np.column_stack((sx, sy)).astype(np.int32)],
                      False, 1.0, 2, cv2.LINE_AA)
        for n, k in enumerate((13, 31, 52, 76, 101, 127)):
            side = -1.0 if (n+branch_index)%2 else 1.0
            _draw_line(m["rupture_forks"], (sx[k], sy[k]),
                       (sx[k]+side*(18+n%4), sy[k]-(12+branch_index*6)), width=1)
    cv2.ellipse(m["germ_apertures"], (382, 354), (22, 11), 11,
                0, 360, 1.0, 2, cv2.LINE_AA)

    # Lobe 3: one off-centre spiral crack with attached, unequal fissures.
    tt = np.linspace(0.0, 1.0, 241, dtype=np.float32)
    angle = 0.3 + tt*4.4*np.pi
    radius = 5.0 + 88.0*tt
    sx = 139.0 + radius*np.cos(angle)
    sy = 361.0 + 0.84*radius*np.sin(angle)
    cv2.polylines(m["exine_ridges"], [np.column_stack((sx, sy)).astype(np.int32)],
                  False, 1.0, 2, cv2.LINE_AA)
    for n, k in enumerate((21, 39, 62, 88, 117, 149, 184, 218)):
        a = angle[k] + (-1.0 if n%2 else 1.0)*(0.62+0.05*n)
        length = 15.0 + 14.0*np.sin(n*1.2)**2
        _draw_line(m["rupture_forks"], (sx[k], sy[k]),
                   (sx[k]+length*np.cos(a), sy[k]+length*np.sin(a)), width=1)
    cv2.ellipse(m["germ_apertures"], (139, 361), (15, 12), -18,
                0, 360, 1.0, 2, cv2.LINE_AA)

    for a, b, bend in ((0, 1, (259.0, 91.0)), (1, 2, (441.0, 248.0)),
                       (2, 3, (260.0, 438.0)), (3, 0, (84.0, 254.0))):
        start = specs[a][:2]; end = specs[b][:2]
        q = np.linspace(0.0, 1.0, 43, dtype=np.float32)
        bx = (1-q)**2*start[0] + 2*(1-q)*q*bend[0] + q*q*end[0]
        by = (1-q)**2*start[1] + 2*(1-q)*q*bend[1] + q*q*end[1]
        cv2.polylines(m["fusion_sutures"], [np.column_stack((bx, by)).astype(np.int32)],
                      False, 1.0, 2, cv2.LINE_AA)
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        midpoint = ((specs[a][0]+specs[b][0])*0.5, (specs[a][1]+specs[b][1])*0.5)
        _draw_circle(m["adhesion_necks"], midpoint, 5+a%3, width=1)
    m["pressure_crescents"] = _halo(m["tetrad_boundaries"], 3.2)*(1.0-m["tetrad_boundaries"])
    m["overlap_collars"] = _halo(m["fusion_sutures"], 1.8)*(1.0-m["fusion_sutures"])
    for n, point in enumerate(((93, 112), (238, 77), (440, 191), (455, 384),
                               (283, 453), (75, 410), (48, 247))):
        cv2.ellipse(m["callose_scars"], point, (7+n%3, 3), n*17,
                    15, 335, 1.0, 1, cv2.LINE_AA)
        cv2.circle(tone, point, 9, (n%6)/5.0, -1)
    for key in ("exine_ridges", "germ_apertures", "rupture_forks", "callose_scars"):
        m[key] *= union
    m["exine_ridges"] = cv2.dilate(m["exine_ridges"], np.ones((3, 3), np.uint8))
    banks = dict(tetrad_boundaries="A", fusion_sutures="B", exine_ridges="B",
                 germ_apertures="A", rupture_forks="B", adhesion_necks="N",
                 pressure_crescents="B", callose_scars="A", overlap_collars="B")
    ancestry = tone + 0.52*m["tetrad_boundaries"] + 0.46*m["exine_ridges"] + 0.34*m["fusion_sutures"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.1))


def _build_fbl_white_whorl() -> _Grammar:
    """Five broad gardenia ribbons, each assembled from fine parallel folds."""
    m=_new_marks("gardenia_cups","overlap_lips","petal_cushions","central_throats",
                 "fold_saddles","dew_rims","torn_margins","fold_ribs")
    tone=np.zeros((_WORK,_WORK),np.float32); center=(231.0,278.0)
    arm_angles=(0.08,1.19,2.46,3.71,5.28)
    arm_turns=(1.31,-0.86,1.76,-1.22,0.59)
    arm_lengths=(347.0,281.0,329.0,247.0,306.0)
    arm_scales=(0.76,1.04,0.86,0.95,0.70)
    offset_sets=((-24,-16,-8,-2,5,13,22),(-19,-10,-3,5,12,18),
                 (-26,-18,-11,-4,2,9,17,25),(-16,-7,0,8,15),
                 (-23,-14,-5,3,11,19))
    for arm in range(5):
        t=np.linspace(0,1,181,dtype=np.float32)
        rr=6.0+arm_lengths[arm]*t
        aa=(arm_angles[arm]+arm_turns[arm]*t
            +(0.13+0.04*arm)*np.sin(t*(2.3+0.37*arm)*np.pi+arm))
        cx=center[0]+rr*np.cos(aa); cy=center[1]+arm_scales[arm]*rr*np.sin(aa)
        dx=np.gradient(cx); dy=np.gradient(cy); mag=np.maximum(1,np.hypot(dx,dy))
        nx=-dy/mag; ny=dx/mag
        for oi,offset in enumerate(offset_sets[arm]):
            px=cx+offset*nx; py=cy+offset*ny
            key="gardenia_cups" if (oi+2*arm)%3!=0 else "fold_ribs"
            cv2.polylines(m[key],[np.column_stack((px,py)).astype(np.int32)],False,1.0,
                          2 if abs(offset)<=2 else 1,cv2.LINE_AA)
        step=13+2*arm
        for k in range(14+arm,176,step):
            _draw_line(m["fold_saddles"],(cx[k]-8*nx[k],cy[k]-8*ny[k]),
                       (cx[k]+8*nx[k],cy[k]+8*ny[k]),width=1)
            cv2.ellipse(m["petal_cushions"],(int(cx[k]+4*nx[k]),int(cy[k]+4*ny[k])),
                        (5+(k+arm)%3,2+arm%2),np.degrees(aa[k]),0,360,1.0,-1,cv2.LINE_AA)
            if (k//step+arm)%3==0: _draw_circle(m["dew_rims"],(cx[k]-6*nx[k],cy[k]-6*ny[k]),2+arm%3,width=1)
            cv2.circle(tone,(int(cx[k]),int(cy[k])),7,((k//step+arm*3)%17)/16.0,-1)
        _draw_line(m["torn_margins"],(cx[-8]-8*nx[-8],cy[-8]-8*ny[-8]),
                   (cx[-1]+8*nx[-1],cy[-1]+8*ny[-1]),width=2)
    m["gardenia_cups"]=cv2.dilate(m["gardenia_cups"],np.ones((3,3),np.uint8))
    m["fold_ribs"]=cv2.dilate(m["fold_ribs"],np.ones((3,3),np.uint8))
    m["overlap_lips"]=_edge(m["gardenia_cups"],1)*_halo(m["fold_ribs"],1.3)
    # A gardenia overlap is a narrow laminar lip, not a zero-width crossing.
    # Give that B-owned anatomy a three-pixel body so its clearcoat interior
    # survives fixed-tier composition while remaining a fine car-scale mark.
    m["overlap_lips"]=cv2.dilate(m["overlap_lips"],np.ones((3,3),np.uint8))
    for rr in (4,8,13,19): _draw_circle(m["central_throats"],center,rr,width=1)
    masks=m
    banks = dict(gardenia_cups="A", overlap_lips="B", petal_cushions="A",
                 central_throats="N", fold_saddles="B", dew_rims="B",
                 torn_margins="N", fold_ribs="B")
    ancestry=tone+0.49*m["gardenia_cups"]+0.34*m["fold_ribs"]+0.29*m["petal_cushions"]
    return _pack(masks, banks, cv2.GaussianBlur(ancestry,(0,0),7.0))


def _build_fbl_coral_stamen() -> _Grammar:
    """One three-way braided stamen bundle, not a repeated radial fountain."""
    m = _new_marks("braided_filaments", "bilobed_anthers", "pollen_sacs",
                   "dehiscence_seams", "connective_knots", "stigma_curls",
                   "root_bracts", "missing_filaments", "braid_crossovers")
    tone = np.zeros((_WORK, _WORK), np.float32)
    root = np.asarray((47.0, 468.0), np.float32)
    endpoints = ((438.0, 55.0), (501.0, 264.0), (382.0, 487.0))
    controls = (((103.0, 233.0), (291.0, 32.0)),
                ((174.0, 414.0), (335.0, 185.0)),
                ((127.0, 548.0), (291.0, 416.0)))
    for bundle, endpoint in enumerate(endpoints):
        p1, p2 = controls[bundle]
        q = np.linspace(0.0, 1.0, 181, dtype=np.float32)
        bx = ((1-q)**3*root[0] + 3*(1-q)**2*q*p1[0]
              + 3*(1-q)*q*q*p2[0] + q**3*endpoint[0])
        by = ((1-q)**3*root[1] + 3*(1-q)**2*q*p1[1]
              + 3*(1-q)*q*q*p2[1] + q**3*endpoint[1])
        dx, dy = np.gradient(bx), np.gradient(by)
        mag = np.maximum(1.0, np.hypot(dx, dy)); nx, ny = -dy/mag, dx/mag
        for strand in range(7):
            phase = strand*0.91 + bundle*0.47
            envelope = (3.0+strand%3)*np.sin(q*(5.0+bundle*1.3)*np.pi+phase)*np.sin(np.pi*q)
            offset = (strand-3)*1.7 + envelope
            px, py = bx+offset*nx, by+offset*ny
            cv2.polylines(m["braided_filaments"],
                          [np.column_stack((px, py)).astype(np.int32)], False,
                          1.0, 1, cv2.LINE_AA)
        for n, k in enumerate((19, 43, 72, 104, 137, 163)):
            span = 8.0 + 3.0*np.sin(n*1.7+bundle)**2
            _draw_line(m["connective_knots"],
                       (bx[k]-span*nx[k], by[k]-span*ny[k]),
                       (bx[k]+span*nx[k], by[k]+span*ny[k]), width=2)
            if n in (1, 4):
                _draw_circle(m["braid_crossovers"], (bx[k], by[k]), 4+bundle, width=1)
            cv2.circle(tone, (int(bx[k]), int(by[k])), 8,
                       ((n+bundle*3)%8)/7.0, -1)
        for branch, k in enumerate((31, 58, 91, 125, 153)):
            side = -1.0 if (branch+bundle)%2 else 1.0
            tangent = np.arctan2(dy[k], dx[k])
            length = 46.0 + 49.0*np.sin((branch+1)*1.31+bundle)**2
            angle = tangent + side*(0.72+0.11*branch+0.06*bundle)
            start = (float(bx[k]), float(by[k]))
            end = (start[0]+length*np.cos(angle), start[1]+length*np.sin(angle))
            control = (start[0]+length*0.48*np.cos(angle-side*0.39),
                       start[1]+length*0.48*np.sin(angle-side*0.39))
            q2 = np.linspace(0.0, 1.0, 31, dtype=np.float32)
            fx = (1-q2)**2*start[0]+2*(1-q2)*q2*control[0]+q2*q2*end[0]
            fy = (1-q2)**2*start[1]+2*(1-q2)*q2*control[1]+q2*q2*end[1]
            for offset in (-2.0, 0.0, 2.0):
                fdx, fdy = np.gradient(fx), np.gradient(fy)
                fmag = np.maximum(1.0, np.hypot(fdx, fdy))
                px = fx-offset*fdy/fmag; py = fy+offset*fdx/fmag
                cv2.polylines(m["braided_filaments"],
                              [np.column_stack((px, py)).astype(np.int32)], False,
                              1.0, 1, cv2.LINE_AA)
            a_deg = np.degrees(np.arctan2(fy[-1]-fy[-3], fx[-1]-fx[-3]))
            cv2.ellipse(m["bilobed_anthers"], (int(end[0]), int(end[1])),
                        (6+branch%3, 2+bundle%2), a_deg, 0, 360,
                        1.0, -1, cv2.LINE_AA)
            cv2.ellipse(m["pollen_sacs"], (int(end[0]), int(end[1])),
                        (3, 1), a_deg+90, 0, 360, 1.0, 1, cv2.LINE_AA)
            _draw_line(m["dehiscence_seams"],
                       (end[0]-4*np.cos(angle), end[1]-4*np.sin(angle)),
                       (end[0]+4*np.cos(angle), end[1]+4*np.sin(angle)), width=1)
        tip_angle = np.arctan2(dy[-1], dx[-1])
        lobe_count = 9+bundle*2
        for lobe in range(lobe_count):
            a = tip_angle - 1.02 + lobe*(2.04/(lobe_count-1)) + 0.05*np.sin(lobe*1.8)
            length = 17.0 + 8.0*np.sin(lobe*1.37)**2
            sx, sy = endpoint
            ex, ey = sx+length*np.cos(a), sy+length*np.sin(a)
            _draw_line(m["braided_filaments"], (sx, sy), (ex, ey), width=1)
            cv2.ellipse(m["bilobed_anthers"], (int(ex), int(ey)),
                        (5+lobe%3, 2), np.degrees(a), 0, 360,
                        1.0, -1, cv2.LINE_AA)
            cv2.ellipse(m["pollen_sacs"], (int(ex), int(ey)), (3, 1),
                        np.degrees(a)+90, 0, 360, 1.0, 1, cv2.LINE_AA)
            _draw_line(m["dehiscence_seams"],
                       (ex-3*np.cos(a), ey-3*np.sin(a)),
                       (ex+3*np.cos(a), ey+3*np.sin(a)), width=1)
        if bundle == 1:
            _draw_circle(m["missing_filaments"], (bx[149], by[149]), 5, width=1)
    for n, a in enumerate((-2.73, -2.31, -1.88, -1.42, -0.96, -0.51, -0.08)):
        length = 22.0 + n%4*4.0
        _draw_line(m["root_bracts"], root,
                   (root[0]+length*np.cos(a), root[1]+length*np.sin(a)), width=2)
    for rr, rotation in ((10, -24), (18, 17), (27, -11), (37, 28)):
        cv2.ellipse(m["stigma_curls"], (55, 453), (rr, max(4, rr//3)),
                    rotation, 188, 351, 1.0, 1, cv2.LINE_AA)
    banks = dict(braided_filaments="A", bilobed_anthers="B", pollen_sacs="A",
                 dehiscence_seams="N", connective_knots="B", stigma_curls="B",
                 root_bracts="A", missing_filaments="N", braid_crossovers="B")
    ancestry = tone + 0.52*m["braided_filaments"] + 0.41*m["connective_knots"] + 0.29*m["bilobed_anthers"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.0))


def _build_fbl_lilac_rose() -> _Grammar:
    """One interlocking crown of nineteen unequal teardrop petal chambers."""
    m = _new_marks("reaction_walls", "petal_bays", "curl_tips",
                   "branch_saddles", "closed_chambers", "rupture_gaps",
                   "rim_fronts", "vein_relays")
    tone = np.zeros((_WORK, _WORK), np.float32); center=np.asarray((258.0,252.0))
    golden=np.pi*(3.0-np.sqrt(5.0))
    for n in range(19):
        angle=n*golden+0.19*np.sin(n*1.51)
        orbit=7.5*n+8.0*np.sin(n*0.73)
        base=center+orbit*np.asarray((np.cos(angle),0.91*np.sin(angle)))
        length=44.0+8.2*n+13.0*np.sin(n*1.17)
        width=19.0+3.1*n+7.0*np.sin(n*1.91)**2
        orient=angle+np.pi+0.31*np.sin(n*0.81)
        u=np.asarray((np.cos(orient),np.sin(orient))); v=np.asarray((-u[1],u[0]))
        q=np.linspace(0,1,81,dtype=np.float32)
        # Tapered closed teardrop; every point is on one petal's causal rim.
        axial=(q*2.0-1.0)*length*0.5
        breadth=np.clip(np.sin(np.pi*q),0.0,None)**0.72*width*(0.78+0.22*np.sin(q*np.pi+n))
        left=base[None,:]+axial[:,None]*u[None,:]+breadth[:,None]*v[None,:]
        right=base[None,:]+axial[::-1,None]*u[None,:]-breadth[::-1,None]*v[None,:]
        outline=np.vstack((left,right)).astype(np.int32)
        _draw_poly(m["reaction_walls"],outline,width=2)
        if n%3!=0: _draw_poly(m["petal_bays"],outline,fill=True)
        _draw_poly(m["rim_fronts"],outline,width=1)
        tip=base+u*length*0.5
        _draw_circle(m["curl_tips"],tip,3+n%4,width=1)
        _draw_line(m["vein_relays"],base-u*length*0.35,tip,width=1)
        for j in (24,40,56):
            p=left[j]; mirror=right[80-j]
            _draw_line(m["branch_saddles"],p,mirror,width=1)
        if n%2==0: _draw_circle(m["closed_chambers"],base,5+n%5,width=1)
        if n%4==1: _draw_line(m["rupture_gaps"],tip-v*4,tip+v*4,width=2)
        cv2.circle(tone,(int(base[0]),int(base[1])),11,(n%13)/12.0,-1)
    # Petal bays are narrow tissue lips following each chamber wall; the
    # earlier construction's filled teardrops read as macro stamps.
    m["petal_bays"]=_halo(m["reaction_walls"],2.5)*(1.0-m["reaction_walls"])
    masks = m
    banks = dict(reaction_walls="A", petal_bays="B", curl_tips="A",
                 branch_saddles="N", closed_chambers="A", rupture_gaps="N",
                 rim_fronts="B", vein_relays="B")
    return _pack(masks, banks, cv2.GaussianBlur(tone + 0.38*m["petal_bays"], (0, 0), 2.2))


def _build_fbl_coral_vine() -> _Grammar:
    """One rooted coral-vine crown: recursive Y growth, not vertical lanes."""
    m = _new_marks("primary_stems", "secondary_veins", "y_nodes", "bud_cups",
                   "thorn_tips", "leaf_sockets", "anastomosis_bridges", "vein_scars",
                   "leaf_blades")
    tone = np.zeros((_WORK, _WORK), np.float32)
    stack = [(256.0, 516.0, -2.31, 178.0, 0, 1),
             (256.0, 516.0, -1.57, 193.0, 0, 2),
             (256.0, 516.0, -0.82, 181.0, 0, 3)]
    terminal_by_depth = []
    while stack:
        sx, sy, angle, length, depth, identity = stack.pop()
        bend = 0.13*np.sin(identity*1.73+depth)
        ex = sx + length*np.cos(angle+bend)
        ey = sy + length*np.sin(angle+bend)
        cx = sx + length*0.52*np.cos(angle-bend*1.7)
        cy = sy + length*0.52*np.sin(angle-bend*1.7)
        q = np.linspace(0.0, 1.0, 27, dtype=np.float32)
        bx = (1-q)**2*sx + 2*(1-q)*q*cx + q*q*ex
        by = (1-q)**2*sy + 2*(1-q)*q*cy + q*q*ey
        cv2.polylines(m["primary_stems" if depth<3 else "secondary_veins"],
                      [np.column_stack((bx, by)).astype(np.int32)], False, 1.0,
                      3 if depth<2 else 1, cv2.LINE_AA)
        _draw_circle(m["y_nodes"], (ex, ey), 2+int(depth<2), width=1)
        _draw_circle(m["leaf_sockets"], (bx[17], by[17]), 2, width=1)
        side = -1.0 if identity%2 else 1.0
        cv2.ellipse(m["leaf_blades"], (int(bx[18]+side*4), int(by[18])),
                    (6, 2), np.degrees(angle)+side*38, 0, 360, 1.0, -1, cv2.LINE_AA)
        _draw_line(m["thorn_tips"], (bx[11], by[11]),
                   (bx[11]+5*np.cos(angle+side*1.2), by[11]+5*np.sin(angle+side*1.2)), width=1)
        cv2.circle(tone, (int(ex), int(ey)), 6, (identity%19)/18.0, -1)
        if depth < 8 and length > 8:
            spread = 0.34 + 0.10*np.sin(identity*0.93) + depth*0.018
            shrink = 0.69 + 0.025*np.sin(identity*1.17)
            stack.append((ex, ey, angle-spread, length*shrink, depth+1, identity*2))
            stack.append((ex, ey, angle+spread*0.91, length*(shrink-0.025), depth+1, identity*2+1))
        else:
            _draw_circle(m["bud_cups"], (ex, ey), 3+identity%3, width=1)
            terminal_by_depth.append((ex, ey))
        if identity%9 == 0:
            _draw_line(m["vein_scars"], (bx[8]-3, by[8]+2), (bx[8]+4, by[8]-2), width=1)
    for i in range(0, len(terminal_by_depth)-5, 11):
        a, b = terminal_by_depth[i], terminal_by_depth[i+5]
        _draw_line(m["anastomosis_bridges"], a, b, width=1)
    banks = dict(primary_stems="A", secondary_veins="B", y_nodes="N",
                 bud_cups="B", thorn_tips="A", leaf_sockets="N",
                 anastomosis_bridges="B", vein_scars="A", leaf_blades="B")
    return _pack(m, banks, cv2.GaussianBlur(tone + 0.42 * m["primary_stems"], (0, 0), 2.2))


def _build_fbl_lilac_stamen() -> _Grammar:
    """One side-view stamen ending in an asymmetric bilobed anther cutaway."""
    m = _new_marks("filament_spine", "filament_striations", "anther_lobes",
                   "connective_bridge", "dehiscence_suture", "endothecial_ribs",
                   "tapetum_frills", "pollen_chambers", "ruptured_tip")
    tone = np.zeros((_WORK, _WORK), np.float32)
    t = np.linspace(0.0, 1.0, 241, dtype=np.float32)
    sx = 8.0 + 326.0*t + 31.0*np.sin(t*2.7*np.pi+0.2)
    sy = 500.0 - 319.0*t + 54.0*np.sin(t*3.1*np.pi+0.6)
    dx = np.gradient(sx); dy = np.gradient(sy); mag = np.maximum(1.0, np.hypot(dx, dy))
    nx, ny = -dy/mag, dx/mag
    cv2.polylines(m["filament_spine"],
                  [np.column_stack((sx, sy)).astype(np.int32)], False,
                  1.0, 5, cv2.LINE_AA)
    for offset in (-5.0, -2.0, 2.0, 5.0):
        px, py = sx + offset*nx, sy + offset*ny
        cv2.polylines(m["filament_striations"],
                      [np.column_stack((px, py)).astype(np.int32)], False,
                      1.0, 1, cv2.LINE_AA)

    lobe_specs = ((351.0, 103.0, 147.0, 86.0, -19.0, 0.3),
                  (389.0, 258.0, 121.0, 103.0, 23.0, 1.1))
    boundaries = []
    aa = np.linspace(0.0, 2.0*np.pi, 241, dtype=np.float32)
    for li, (cx, cy, rx, ry, rotation, phase) in enumerate(lobe_specs):
        local_r = 1.0 + 0.10*np.sin(aa*3.0+phase) + 0.055*np.sin(aa*7.0-phase)
        ca, sa = np.cos(np.radians(rotation)), np.sin(np.radians(rotation))
        ux, uy = rx*local_r*np.cos(aa), ry*local_r*np.sin(aa)
        bx, by = cx + ca*ux - sa*uy, cy + sa*ux + ca*uy
        boundaries.append((bx, by))
        cv2.polylines(m["anther_lobes"],
                      [np.column_stack((bx, by)).astype(np.int32)], True,
                      1.0, 3, cv2.LINE_AA)
        for inset in (0.72, 0.48):
            ix, iy = cx + inset*(bx-cx), cy + inset*(by-cy)
            cv2.polylines(m["tapetum_frills"],
                          [np.column_stack((ix, iy)).astype(np.int32)], True,
                          1.0, 1, cv2.LINE_AA)
        rib_indices = ((4, 14, 27, 41, 57, 74, 93, 113, 134, 156, 179, 201, 222, 236)
                       if li == 0 else (7, 22, 38, 55, 73, 92, 112, 133, 155, 178, 199, 217, 231))
        root = (327.0+li*18.0, 174.0+li*17.0)
        for n, k in enumerate(rib_indices):
            ex, ey = float(bx[k]), float(by[k])
            control = ((root[0]+ex)*0.5 + (12+li*5)*np.sin(n*1.3),
                       (root[1]+ey)*0.5 + (10-li*3)*np.cos(n*1.7))
            q = np.linspace(0.0, 1.0, 27, dtype=np.float32)
            px = (1-q)**2*root[0] + 2*(1-q)*q*control[0] + q*q*ex
            py = (1-q)**2*root[1] + 2*(1-q)*q*control[1] + q*q*ey
            cv2.polylines(m["endothecial_ribs"],
                          [np.column_stack((px, py)).astype(np.int32)], False,
                          1.0, 1, cv2.LINE_AA)
            if n in (1, 4, 8):
                cv2.ellipse(m["pollen_chambers"],
                            (int(px[15]), int(py[15])), (6+n%3, 3),
                            np.degrees(np.arctan2(py[-1]-py[-4], px[-1]-px[-4])),
                            0, 360, 1.0, 1, cv2.LINE_AA)
            cv2.circle(tone, (int(px[13]), int(py[13])), 8,
                       ((n+li*5)%11)/10.0, -1)
    bridge_t = np.linspace(0.0, 1.0, 91, dtype=np.float32)
    bx = 311.0 + 92.0*bridge_t + 16.0*np.sin(bridge_t*np.pi)
    by = 180.0 + 11.0*np.sin(bridge_t*2.0*np.pi) + 24.0*bridge_t
    cv2.polylines(m["connective_bridge"],
                  [np.column_stack((bx, by)).astype(np.int32)], False,
                  1.0, 5, cv2.LINE_AA)
    sy2 = 318.0 + 109.0*bridge_t + 9.0*np.sin(bridge_t*4.0*np.pi)
    sx2 = 55.0 + 264.0*bridge_t + 21.0*np.sin(bridge_t*2.0*np.pi+0.4)
    cv2.polylines(m["dehiscence_suture"],
                  [np.column_stack((sy2, sx2)).astype(np.int32)], False,
                  1.0, 2, cv2.LINE_AA)
    cv2.ellipse(m["ruptured_tip"], (482, 292), (25, 9), 31,
                185, 358, 1.0, 2, cv2.LINE_AA)
    banks = dict(filament_spine="A", filament_striations="B", anther_lobes="A",
                 connective_bridge="N", dehiscence_suture="B", endothecial_ribs="B",
                 tapetum_frills="A", pollen_chambers="B", ruptured_tip="N")
    ancestry = tone + 0.51*m["anther_lobes"] + 0.43*m["endothecial_ribs"] + 0.33*m["filament_spine"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.2))


def _build_fbl_magenta_mosaic() -> _Grammar:
    """One four-lobed orchid rendered as irregular stained-glass marquetry."""
    x, y = _xy()
    lx, ly = x-250.0, y-263.0
    radius = np.hypot(lx, ly)
    theta = np.arctan2(ly, lx)
    boundary = 214.0 + 52.0*np.cos(theta*4.0+0.24*np.sin(theta*3.0)) + 17.0*np.sin(theta*9.0)
    florets = _f32((boundary-radius)/2.2)
    walls=np.zeros_like(radius); buttons=np.zeros_like(radius); midribs=np.zeros_like(radius)
    broken=np.zeros_like(radius)
    center=(250.0,263.0)
    for lobe in range(9):
        a=lobe*2*np.pi/9.0+0.12*np.sin(lobe*2.1)
        length=246.0+18.0*np.sin(lobe*1.37)
        ex,ey=center[0]+length*np.cos(a),center[1]+length*np.sin(a)
        cx,cy=center[0]+length*0.47*np.cos(a+0.31*np.sin(lobe+1)),center[1]+length*0.47*np.sin(a+0.31*np.sin(lobe+1))
        q=np.linspace(0,1,81,dtype=np.float32)
        bx=(1-q)**2*center[0]+2*(1-q)*q*cx+q*q*ex
        by=(1-q)**2*center[1]+2*(1-q)*q*cy+q*q*ey
        cv2.polylines(midribs,[np.column_stack((bx,by)).astype(np.int32)],False,1.0,3,cv2.LINE_AA)
        for j in range(10,76,7):
            tx,ty=bx[j+2]-bx[j-2],by[j+2]-by[j-2]; tangent=np.arctan2(ty,tx)
            for side in (-1.0,1.0):
                branch_len=(38.0+68.0*np.sin(np.pi*j/81.0))*(0.76+0.24*np.sin(j*lobe+1.2)**2)
                ba=tangent+side*(0.67+0.18*np.sin(j*0.91+lobe))
                px,py=bx[j]+branch_len*np.cos(ba),by[j]+branch_len*np.sin(ba)
                _draw_line(walls,(bx[j],by[j]),(px,py),width=2 if j%14==10 else 1)
                for fork in (-1.0,1.0):
                    fa=ba+fork*(0.42+0.08*np.sin(j+lobe))
                    fl=branch_len*(0.28+0.08*((j+lobe)%3))
                    _draw_line(walls,(px,py),(px+fl*np.cos(fa),py+fl*np.sin(fa)),width=1)
                if (j+lobe)%3==0: _draw_circle(buttons,(px,py),3+(j%4),width=1)
                if (j+2*lobe)%5==0: _draw_line(broken,(px-3,py+2),(px+4,py-2),width=1)
    walls*=florets; buttons*=florets; midribs*=florets; broken*=florets
    notches = _ring(radius, boundary-4.0+5.0*np.sin(theta*16.0), 0.68)
    lips = _ring(radius, boundary, 0.85)
    corner_pores = np.zeros_like(radius)
    for i in range(20):
        a = i*2*np.pi/20.0 + 0.08*np.sin(i*1.7)
        rr = 0.74*(214.0+52.0*np.cos(a*4.0+0.24*np.sin(a*3.0))+17.0*np.sin(a*9.0))
        corner_pores = np.maximum(corner_pores,
                                  _ring(np.hypot(lx-rr*np.cos(a), ly-rr*np.sin(a)), 2+i%2, 0.55))
    facet_lips = _halo(walls, 2.6) * florets * (1.0-walls)
    masks = dict(petal_facet_lips=facet_lips, cell_walls=walls, button_eyes=buttons,
                 petal_midribs=midribs, corner_notches=notches,
                 overlap_lips=lips, broken_cells=broken, corner_pores=corner_pores)
    banks = dict(petal_facet_lips="A", cell_walls="N", button_eyes="B",
                 petal_midribs="B", corner_notches="N", overlap_lips="B",
                 broken_cells="B", corner_pores="A")
    return _pack(masks, banks, _norm(radius/310.0+theta/(2*np.pi)+0.31*cv2.GaussianBlur(walls,(0,0),3.0)))


def _build_fbl_leaf_whorl() -> _Grammar:
    """One heteromorphic leaf whorl: tendril, blade, pitcher, fern and ribbon."""
    m = _new_marks("central_rachides", "leaflet_pleats", "chevron_ribs",
                   "serrated_margins", "node_bands", "over_under_seams",
                   "tip_hooks", "secondary_veins")
    tone = np.zeros((_WORK, _WORK), np.float32)
    root = np.asarray((252.0, 271.0), np.float32)

    # Crozier tendril to upper left.
    t = np.linspace(0.0, 1.0, 181, dtype=np.float32)
    angle = 0.4 + 3.8*np.pi*t
    radius = 142.0*(1.0-t)**0.74 + 5.0
    bx = 112.0 + radius*np.cos(angle); by = 132.0 + 0.82*radius*np.sin(angle)
    stem_x = np.concatenate((np.linspace(root[0], bx[0], 31), bx))
    stem_y = np.concatenate((np.linspace(root[1], by[0], 31), by))
    cv2.polylines(m["central_rachides"],
                  [np.column_stack((stem_x, stem_y)).astype(np.int32)], False,
                  1.0, 3, cv2.LINE_AA)
    for n, k in enumerate((18, 39, 65, 96, 131, 162)):
        _draw_circle(m["tip_hooks"], (bx[k], by[k]), 3+n%3, width=1)
        _draw_line(m["secondary_veins"], (bx[k], by[k]),
                   (bx[k]+(9+n)*np.cos(angle[k]+0.8), by[k]+(9+n)*np.sin(angle[k]+0.8)), width=1)

    # One long blade to upper right, outlined from a single causal midrib.
    q = np.linspace(0.0, 1.0, 121, dtype=np.float32)
    bx = (1-q)**2*root[0]+2*(1-q)*q*354.0+q*q*474.0
    by = (1-q)**2*root[1]+2*(1-q)*q*102.0+q*q*28.0
    dx, dy = np.gradient(bx), np.gradient(by); mag=np.maximum(1.0,np.hypot(dx,dy))
    nx,ny=-dy/mag,dx/mag
    half=36.0*np.clip(np.sin(np.pi*q),0.0,None)**0.76*(0.82+0.18*np.sin(q*5*np.pi+0.4)**2)
    outline=np.vstack((np.column_stack((bx+half*nx,by+half*ny)),
                       np.column_stack((bx-half*nx,by-half*ny))[::-1])).astype(np.int32)
    _draw_poly(m["leaflet_pleats"],outline,width=2)
    cv2.polylines(m["central_rachides"],[np.column_stack((bx,by)).astype(np.int32)],False,1.0,3,cv2.LINE_AA)
    for n,k in enumerate((17,31,48,67,89,107)):
        side=-1.0 if n%2 else 1.0
        _draw_line(m["chevron_ribs"],(bx[k],by[k]),
                   (bx[k]+side*0.86*half[k]*nx[k],by[k]+side*0.86*half[k]*ny[k]),width=1)
        _draw_line(m["serrated_margins"],
                   (bx[k]+side*half[k]*nx[k],by[k]+side*half[k]*ny[k]),
                   (bx[k]+side*(half[k]+6)*nx[k]+4*dx[k]/mag[k],
                    by[k]+side*(half[k]+6)*ny[k]+4*dy[k]/mag[k]),width=1)

    # A pitcher leaf to lower right with an open lip and internal ribs.
    q=np.linspace(0.0,1.0,91,dtype=np.float32)
    bx=(1-q)**2*root[0]+2*(1-q)*q*405.0+q*q*431.0
    by=(1-q)**2*root[1]+2*(1-q)*q*319.0+q*q*404.0
    cv2.polylines(m["central_rachides"],[np.column_stack((bx,by)).astype(np.int32)],False,1.0,3,cv2.LINE_AA)
    aa=np.linspace(0,2*np.pi,181,dtype=np.float32)
    rr=1.0+0.13*np.sin(aa*3.0+0.5)+0.06*np.sin(aa*7.0)
    px=423.0+54.0*rr*np.cos(aa); py=411.0+76.0*rr*np.sin(aa)
    cv2.polylines(m["leaflet_pleats"],[np.column_stack((px,py)).astype(np.int32)],True,1.0,2,cv2.LINE_AA)
    cv2.ellipse(m["over_under_seams"],(423,353),(48,13),-7,2,356,1.0,3,cv2.LINE_AA)
    for n,a in enumerate((-2.72,-2.18,-1.61,-1.03,-0.42,0.17,0.73)):
        _draw_line(m["chevron_ribs"],(423,404),(423+48*np.cos(a),404+61*np.sin(a)),width=1)
        if n in (1,4): _draw_circle(m["node_bands"],(423+31*np.cos(a),404+39*np.sin(a)),3+n%2,width=1)

    # One fern blade to lower left, with unequal pinnae on a bent rachis.
    q=np.linspace(0.0,1.0,121,dtype=np.float32)
    bx=(1-q)**2*root[0]+2*(1-q)*q*132.0+q*q*23.0
    by=(1-q)**2*root[1]+2*(1-q)*q*365.0+q*q*486.0
    cv2.polylines(m["central_rachides"],[np.column_stack((bx,by)).astype(np.int32)],False,1.0,3,cv2.LINE_AA)
    for n,k in enumerate((11,20,31,43,56,70,85,101,114)):
        tx,ty=bx[min(120,k+2)]-bx[max(0,k-2)],by[min(120,k+2)]-by[max(0,k-2)]
        tangent=np.arctan2(ty,tx); side=-1.0 if n%2 else 1.0
        length=22.0+29.0*np.sin(np.pi*k/120.0)+8.0*np.sin(n*1.6)**2
        a=tangent+side*(0.83+0.08*n)
        end=(bx[k]+length*np.cos(a),by[k]+length*np.sin(a))
        _draw_line(m["chevron_ribs"],(bx[k],by[k]),end,width=2 if n in (2,6) else 1)
        cv2.ellipse(m["leaflet_pleats"],(int(end[0]),int(end[1])),(7+n%4,3),np.degrees(a),0,360,1.0,1,cv2.LINE_AA)
        _draw_circle(m["tip_hooks"],end,2+n%3,width=1)

    # A narrow ribbon leaf rises through the centre and crosses the other organs.
    q=np.linspace(0.0,1.0,151,dtype=np.float32)
    bx=root[0]+31.0*np.sin(q*3.0*np.pi)+13.0*np.sin(q*8.0*np.pi)
    by=root[1]-294.0*q
    cv2.polylines(m["central_rachides"],[np.column_stack((bx,by)).astype(np.int32)],False,1.0,4,cv2.LINE_AA)
    for n,k in enumerate((13,29,48,70,95,121,143)):
        _draw_line(m["over_under_seams"],(bx[k]-11-n%3,by[k]),(bx[k]+11+n%3,by[k]),width=1)
        _draw_circle(m["node_bands"],(bx[k],by[k]),2+n%3,width=1)
        cv2.circle(tone,(int(bx[k]),int(by[k])),8,(n%6)/5.0,-1)
    for rr in (6,11,17,24): _draw_circle(m["over_under_seams"],root,rr,width=1)
    banks = dict(central_rachides="A", leaflet_pleats="B", chevron_ribs="A",
                 serrated_margins="B", node_bands="N", over_under_seams="N",
                 tip_hooks="B", secondary_veins="A")
    ancestry=tone+0.48*m["central_rachides"]+0.41*m["leaflet_pleats"]+0.34*m["chevron_ribs"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry,(0,0),2.1))


def _build_fbl_white_pollen() -> _Grammar:
    """One wind-stretched exine veil with branching shear anatomy."""
    m = _new_marks("source_exine", "veil_margins", "shear_folds",
                   "rupture_dendrites", "impact_cusps", "wake_sutures",
                   "germ_aperture", "lee_scars", "electrostatic_bridges")
    tone = np.zeros((_WORK, _WORK), np.float32)
    t = np.linspace(0.0, 1.0, 321, dtype=np.float32)
    cx = 18.0 + 501.0*t
    cy = 414.0 - 276.0*t + 55.0*np.sin(t*1.7*np.pi+0.16) + 21.0*np.sin(t*5.0*np.pi)
    dx = np.gradient(cx); dy = np.gradient(cy); mag = np.maximum(1.0, np.hypot(dx, dy))
    nx, ny = -dy/mag, dx/mag
    width = (9.0 + 116.0*np.clip(np.sin(np.pi*t), 0.0, None)**0.73
             *(0.84+0.16*np.sin(t*3.0*np.pi+0.5)**2))
    upper = np.column_stack((cx+width*nx, cy+width*ny))
    lower = np.column_stack((cx-width*nx, cy-width*ny))
    cv2.polylines(m["veil_margins"], [upper.astype(np.int32), lower.astype(np.int32)],
                  False, 1.0, 3, cv2.LINE_AA)

    cv2.polylines(m["shear_folds"],
                  [np.column_stack((cx, cy)).astype(np.int32)], False,
                  1.0, 3, cv2.LINE_AA)
    fold_nodes = (17, 31, 48, 67, 88, 111, 136, 163,
                  191, 218, 242, 264, 283, 299)
    for n, k in enumerate(fold_nodes):
        sides = (-1.0, 1.0) if n in (2, 6, 10, 13) else ((-1.0,) if n%2 else (1.0,))
        for side in sides:
            target_k = min(320, k+8+n%5)
            start = (cx[max(0,k-5)], cy[max(0,k-5)])
            end = (cx[target_k]+side*0.88*width[target_k]*nx[target_k],
                   cy[target_k]+side*0.88*width[target_k]*ny[target_k])
            control = ((start[0]+end[0])*0.5 + 13.0*np.cos(n*1.21+side),
                       (start[1]+end[1])*0.5 + 13.0*np.sin(n*1.21+side))
            q = np.linspace(0.0, 1.0, 31, dtype=np.float32)
            px = (1-q)**2*start[0]+2*(1-q)*q*control[0]+q*q*end[0]
            py = (1-q)**2*start[1]+2*(1-q)*q*control[1]+q*q*end[1]
            cv2.polylines(m["shear_folds"],
                          [np.column_stack((px, py)).astype(np.int32)], False,
                          1.0, 1 if n%3 else 2, cv2.LINE_AA)

    branch_nodes = (28, 43, 61, 78, 99, 117, 137, 159,
                    182, 207, 231, 252, 274, 291)
    for n, k in enumerate(branch_nodes):
        side = -1.0 if n % 2 else 1.0
        start = (cx[k] + side*0.12*width[k]*nx[k], cy[k] + side*0.12*width[k]*ny[k])
        end = (cx[k] + side*0.91*width[k]*nx[k], cy[k] + side*0.91*width[k]*ny[k])
        control = ((start[0]+end[0])*0.5 + 14.0*np.cos(n*1.4),
                   (start[1]+end[1])*0.5 + 14.0*np.sin(n*1.4))
        q = np.linspace(0.0, 1.0, 31, dtype=np.float32)
        bx = (1-q)**2*start[0] + 2*(1-q)*q*control[0] + q*q*end[0]
        by = (1-q)**2*start[1] + 2*(1-q)*q*control[1] + q*q*end[1]
        cv2.polylines(m["rupture_dendrites"],
                      [np.column_stack((bx, by)).astype(np.int32)], False,
                      1.0, 2, cv2.LINE_AA)
        fork_point = (bx[17], by[17])
        for fork in (-1.0, 1.0):
            a = np.arctan2(by[-1]-by[-3], bx[-1]-bx[-3]) + fork*(0.45+0.07*n)
            _draw_line(m["rupture_dendrites"], fork_point,
                       (fork_point[0]+(12+n%4)*np.cos(a),
                        fork_point[1]+(12+n%4)*np.sin(a)), width=1)
        cv2.ellipse(m["impact_cusps"], (int(end[0]), int(end[1])),
                    (5+n%3, 2), np.degrees(np.arctan2(dy[k], dx[k])),
                    25, 320, 1.0, 1, cv2.LINE_AA)
        cv2.circle(tone, (int(start[0]), int(start[1])), 9, (n%6)/5.0, -1)
    for n, k in enumerate((28, 64, 103, 145, 188, 233, 279, 307)):
        span = width[k]*(0.34+0.07*np.sin(n*1.8)**2)
        _draw_line(m["wake_sutures"],
                   (cx[k]-span*nx[k], cy[k]-span*ny[k]),
                   (cx[k]+span*nx[k], cy[k]+span*ny[k]), width=1)
        if n in (1, 4, 6):
            _draw_line(m["electrostatic_bridges"],
                       (cx[k]-0.7*span*nx[k], cy[k]-0.7*span*ny[k]),
                       (cx[min(k+21,320)]+0.6*span*nx[min(k+21,320)],
                        cy[min(k+21,320)]+0.6*span*ny[min(k+21,320)]), width=1)
    aa = np.linspace(0.0, 2.0*np.pi, 151, dtype=np.float32)
    rr = 31.0 + 5.0*np.sin(aa*5.0+0.7)
    ex, ey = 29.0+rr*np.cos(aa), 429.0+0.82*rr*np.sin(aa)
    cv2.polylines(m["source_exine"], [np.column_stack((ex, ey)).astype(np.int32)],
                  True, 1.0, 2, cv2.LINE_AA)
    cv2.ellipse(m["germ_aperture"], (48, 414), (10, 5), -27,
                0, 360, 1.0, 2, cv2.LINE_AA)
    for cut in range(9):
        k = 108 + cut*19
        _draw_line(m["lee_scars"],
                   (cx[k]+0.63*width[k]*nx[k], cy[k]+0.63*width[k]*ny[k]),
                   (cx[k]+(0.79+0.02*cut)*width[k]*nx[k],
                    cy[k]+(0.79+0.02*cut)*width[k]*ny[k]), width=1)
    m["veil_margins"] = cv2.dilate(m["veil_margins"], np.ones((5, 5), np.uint8))
    m["shear_folds"] = cv2.dilate(m["shear_folds"], np.ones((5, 5), np.uint8))
    banks = dict(source_exine="A", veil_margins="B", shear_folds="A",
                 rupture_dendrites="B", impact_cusps="B", wake_sutures="N",
                 germ_aperture="A", lee_scars="N", electrostatic_bridges="B")
    ancestry = tone + 0.50*m["veil_margins"] + 0.44*m["shear_folds"] + 0.37*m["rupture_dendrites"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.1))


def _build_fbl_pink_stamen() -> _Grammar:
    """One serpentine stamen spine carrying opposing comb bouquets."""
    m = _new_marks("filament_combs", "anther_tips", "base_rails", "cross_ties",
                   "bent_teeth", "missing_sockets", "pollen_beads", "dehiscence_seams")
    tone = np.zeros((_WORK, _WORK), np.float32)
    tt = np.linspace(-0.05, 1.05, 281, dtype=np.float32)
    sx = -16.0 + 544.0*tt + 21.0*np.sin(tt*11*np.pi)
    sy = 258.0 + 147.0*np.sin(tt*3.15*np.pi+0.35) + 39.0*np.sin(tt*9.0*np.pi)
    spine = np.column_stack((sx,sy)).astype(np.int32)
    cv2.polylines(m["base_rails"], [spine], False, 1.0, 3, cv2.LINE_AA)
    previous_tips = [None, None]
    nodes=(5,11,18,26,35,45,56,68,81,95,110,126,143,
           161,180,200,221,239,255,269,276)
    for node in nodes:
        px,py=float(sx[node]),float(sy[node])
        tx,ty=float(sx[node+2]-sx[node-2]),float(sy[node+2]-sy[node-2])
        tangent=np.arctan2(ty,tx)
        for side_index,side in enumerate((-1.0,1.0)):
            if (node,side_index) in ((56,0),(143,1),(239,0)):
                _draw_circle(m["missing_sockets"],(px,py),3,width=1)
                continue
            length=34.0+82.0*(0.5+0.5*np.sin(node*1.173+side_index))
            angle=tangent+side*(1.08+0.19*np.sin(node*0.71))
            bend=8.0*np.sin(node*1.91+side_index)
            ex=px+length*np.cos(angle)-bend*np.sin(angle)
            ey=py+length*np.sin(angle)+bend*np.cos(angle)
            control=(px+length*0.49*np.cos(angle)-1.7*bend*np.sin(angle),
                     py+length*0.49*np.sin(angle)+1.7*bend*np.cos(angle))
            q=np.linspace(0.0,1.0,31,dtype=np.float32)
            bx=(1-q)**2*px+2*(1-q)*q*control[0]+q*q*ex
            by=(1-q)**2*py+2*(1-q)*q*control[1]+q*q*ey
            bdx,bdy=np.gradient(bx),np.gradient(by); bmag=np.maximum(1.0,np.hypot(bdx,bdy))
            for offset in (-2.0,0.0,2.0):
                fx=bx-offset*bdy/bmag; fy=by+offset*bdx/bmag
                cv2.polylines(m["filament_combs"],[np.column_stack((fx,fy)).astype(np.int32)],
                              False,1.0,1,cv2.LINE_AA)
            cv2.ellipse(m["anther_tips"],(int(ex),int(ey)),(4+node%3,2),
                        np.degrees(angle),0,360,1.0,-1,cv2.LINE_AA)
            _draw_line(m["dehiscence_seams"],(ex-3*np.cos(angle),ey-3*np.sin(angle)),
                       (ex+3*np.cos(angle),ey+3*np.sin(angle)),width=1)
            _draw_line(m["bent_teeth"],(ex,ey),(ex+4*np.cos(angle+side*0.8),ey+4*np.sin(angle+side*0.8)),width=1)
            _draw_circle(m["pollen_beads"],(ex+3*np.cos(angle),ey+3*np.sin(angle)),1,width=-1)
            if previous_tips[side_index] is not None and (node//5+side_index)%4==0:
                _draw_line(m["cross_ties"],previous_tips[side_index],(ex,ey),width=1)
            previous_tips[side_index]=(ex,ey)
        cv2.circle(tone,(int(px),int(py)),6,(node%31)/30.0,-1)
    banks = dict(filament_combs="A", anther_tips="B", base_rails="N",
                 cross_ties="B", bent_teeth="A", missing_sockets="N",
                 pollen_beads="B", dehiscence_seams="A")
    return _pack(m, banks, cv2.GaussianBlur(tone + 0.4 * m["base_rails"], (0, 0), 1.8))


def _build_fbl_blush_rose() -> _Grammar:
    """One oblong rose-bud cross-section with an asymmetric fold network."""
    m = _new_marks("shingled_petals", "fan_ribs", "overlap_scallops",
                   "tip_notches", "basal_pockets", "curl_lips",
                   "vein_forks", "overlap_slits")
    x,y=_xy(); cx,cy=258.0,251.0; rotation=-0.57; ca,sa=np.cos(rotation),np.sin(rotation)
    dx,dy=x-cx,y-cy
    ux=ca*dx+sa*dy; uy=-sa*dx+ca*dy
    er=np.hypot(ux/1.13,uy/0.82); et=np.arctan2(uy/0.82,ux/1.13)
    boundary=205.0+22.0*np.sin(et*3.0+0.4)+13.0*np.sin(et*7.0-0.6)
    body=_f32((boundary-er)/2.0)
    m["curl_lips"]=_ring(er,boundary,0.82)
    def world(px,py):
        return (cx+ca*px-sa*py,cy+sa*px+ca*py)
    t=np.linspace(0,1,121,dtype=np.float32)
    spine_x=-188.0+379.0*t
    spine_y=28.0*np.sin(t*3.1*np.pi+0.3)+16.0*np.sin(t*7.0*np.pi)
    wx,wy=world(spine_x,spine_y)
    cv2.polylines(m["overlap_slits"],[np.column_stack((wx,wy)).astype(np.int32)],False,1.0,3,cv2.LINE_AA)
    tone=np.zeros((_WORK,_WORK),np.float32)
    for n,j in enumerate(range(5,117,3)):
        sx,sy=float(spine_x[j]),float(spine_y[j])
        tx,ty=float(spine_x[j+2]-spine_x[j-2]),float(spine_y[j+2]-spine_y[j-2])
        tangent=np.arctan2(ty,tx); side=-1.0 if n%2 else 1.0
        length=64.0+91.0*np.sin(np.pi*j/121.0)*(0.72+0.28*np.sin(n*1.83)**2)
        angle=tangent+side*(1.05+0.22*np.sin(n*1.21))
        ex,ey=sx+length*np.cos(angle),sy+length*np.sin(angle)
        q=np.linspace(0,1,33,dtype=np.float32)
        control=(sx+length*0.48*np.cos(angle-side*0.42),sy+length*0.48*np.sin(angle-side*0.42))
        bx=(1-q)**2*sx+2*(1-q)*q*control[0]+q*q*ex
        by=(1-q)**2*sy+2*(1-q)*q*control[1]+q*q*ey
        gx,gy=world(bx,by)
        cv2.polylines(m["fan_ribs"],[np.column_stack((gx,gy)).astype(np.int32)],False,1.0,1,cv2.LINE_AA)
        fork=world(bx[19]+10*np.cos(angle+side*0.7),by[19]+10*np.sin(angle+side*0.7))
        _draw_line(m["vein_forks"],world(bx[19],by[19]),fork,width=1)
        tip=world(ex,ey); _draw_circle(m["tip_notches"],tip,2+n%3,width=1)
        if n%3==0: _draw_circle(m["basal_pockets"],world(sx,sy),4+n%4,width=1)
        if n%4==0:
            cv2.ellipse(m["overlap_scallops"],(int(tip[0]),int(tip[1])),
                        (13+n%7,4),np.degrees(rotation+angle),175,355,1.0,2,cv2.LINE_AA)
        cv2.circle(tone,(int(world(sx,sy)[0]),int(world(sx,sy)[1])),9,(n%17)/16.0,-1)
    for offset in (-52.0,47.0):
        sx=-145.0+322.0*t; sy=offset+19*np.sin(t*4.0*np.pi+offset/31.0)
        gx,gy=world(sx,sy)
        cv2.polylines(m["overlap_slits"],[np.column_stack((gx,gy)).astype(np.int32)],False,1.0,1,cv2.LINE_AA)
    for key in ("fan_ribs","overlap_scallops","tip_notches","basal_pockets","vein_forks","overlap_slits"):
        m[key]*=body
    # The body only clips the cutaway.  Visible petal material remains a fine
    # laminar shoulder attached to the irregular rib network, never a macro fill.
    m["shingled_petals"]=(cv2.dilate(m["fan_ribs"],np.ones((7,7),np.uint8))
                           *body*(1.0-m["fan_ribs"]))
    masks=m
    banks = dict(shingled_petals="A", fan_ribs="B", overlap_scallops="B",
                 tip_notches="N", basal_pockets="A", curl_lips="B",
                 vein_forks="A", overlap_slits="N")
    return _pack(masks, banks, cv2.GaussianBlur(tone+0.41*m["shingled_petals"],(0,0),2.0))


def _build_fbl_lilac_vine() -> _Grammar:
    """One irregular wisteria canopy with curved, crossing raceme branches."""
    m = _new_marks("raceme_strands", "pea_blossoms", "node_collars", "tendril_knots",
                   "leaf_pairs", "seed_pods", "over_under_crossings", "canopy_stems")
    tone = np.zeros((_WORK, _WORK), np.float32)
    t=np.linspace(-0.04,1.04,251,dtype=np.float32)
    canopy_x=-18.0+548.0*t+19.0*np.sin(t*7*np.pi)
    canopy_y=58.0+93.0*t+48.0*np.sin(t*2.7*np.pi+0.6)+13.0*np.sin(t*11*np.pi)
    cv2.polylines(m["canopy_stems"],[np.column_stack((canopy_x,canopy_y)).astype(np.int32)],
                  False,1.0,3,cv2.LINE_AA)
    node_t=(0.018,0.049,0.087,0.126,0.169,0.216,0.267,0.319,0.374,
            0.431,0.489,0.548,0.606,0.663,0.719,0.772,0.821,0.866,
            0.905,0.938,0.966)
    previous_end=None
    for strand,tn in enumerate(node_t):
        k=int(tn*(len(t)-1)); sx,sy=float(canopy_x[k]),float(canopy_y[k])
        angle=0.43+2.05*(0.5+0.5*np.sin(strand*1.47))+0.18*np.sin(strand*2.9)
        length=142.0+186.0*(0.5+0.5*np.sin(strand*1.137+0.4))
        ex,ey=sx+length*np.cos(angle),sy+length*np.sin(angle)
        cx=sx+length*0.44*np.cos(angle-0.62*np.sin(strand*1.2))
        cy=sy+length*0.44*np.sin(angle-0.62*np.sin(strand*1.2))
        q=np.linspace(0,1,49,dtype=np.float32)
        bx=(1-q)**2*sx+2*(1-q)*q*cx+q*q*ex
        by=(1-q)**2*sy+2*(1-q)*q*cy+q*q*ey
        cv2.polylines(m["raceme_strands"],[np.column_stack((bx,by)).astype(np.int32)],
                      False,1.0,2,cv2.LINE_AA)
        for node in range(5,47,5):
            px,py=float(bx[node]),float(by[node]); side=-1 if (node//5+strand)%2 else 1
            _draw_circle(m["node_collars"],(px,py),2,width=1)
            cv2.ellipse(m["pea_blossoms"],(int(px+side*5),int(py+2)),(5,3),side*31,
                        0,360,1.0,-1,cv2.LINE_AA)
            _draw_line(m["leaf_pairs"],(px,py),(px-side*8,py-4),width=2)
            if node%10==5: _draw_circle(m["tendril_knots"],(px+side*8,py-4),3+strand%3,width=1)
            if (node+strand)%4==0:
                cv2.ellipse(m["seed_pods"],(int(px-side*6),int(py+6)),(5,2),side*27,
                            0,360,1.0,1,cv2.LINE_AA)
            cv2.circle(tone,(int(px),int(py)),6,((node+strand*3)%19)/18.0,-1)
        if previous_end is not None and strand in (4,8,13,18):
            _draw_line(m["over_under_crossings"],previous_end,(ex,ey),width=1)
        previous_end=(ex,ey)
    banks = dict(raceme_strands="A", pea_blossoms="B", node_collars="N",
                 tendril_knots="B", leaf_pairs="A", seed_pods="B",
                 over_under_crossings="N", canopy_stems="A")
    return _pack(m, banks, cv2.GaussianBlur(tone + 0.38 * m["raceme_strands"], (0, 0), 2.0))


def _build_fbl_butter_whorl() -> _Grammar:
    """One ascending corkscrew bud carrying irregular, overlapping bract whorls."""
    m = _new_marks("corkscrew_axis", "bract_outlines", "bract_midribs",
                   "serrated_lips", "node_collars", "vascular_forks",
                   "overlap_slits", "bud_cups", "apex_hooks")
    tone = np.zeros((_WORK, _WORK), np.float32)
    t = np.linspace(0.0, 1.0, 361, dtype=np.float32)
    sx = 257.0 + 82.0*np.sin(t*2.55*np.pi+0.2)*(0.34+0.66*np.sin(np.pi*t))
    sy = 526.0 - 548.0*t + 18.0*np.sin(t*7.0*np.pi)
    cv2.polylines(m["corkscrew_axis"],
                  [np.column_stack((sx, sy)).astype(np.int32)], False,
                  1.0, 5, cv2.LINE_AA)
    nodes = (19, 34, 52, 73, 91, 116, 139, 157, 184,
             205, 231, 249, 276, 297, 315, 338, 351)
    previous_edge = None
    for n, k in enumerate(nodes):
        px, py = float(sx[k]), float(sy[k])
        tx = float(sx[min(k+3,360)]-sx[max(k-3,0)])
        ty = float(sy[min(k+3,360)]-sy[max(k-3,0)])
        tangent = np.arctan2(ty, tx)
        side = -1.0 if n % 2 else 1.0
        length = 67.0 + 114.0*np.sin(np.pi*k/360.0)**0.78 + 17.0*np.sin(n*1.41)**2
        angle = tangent + side*(1.03+0.25*np.sin(n*1.13))
        ex, ey = px+length*np.cos(angle), py+length*np.sin(angle)
        control = (px+length*0.47*np.cos(angle-side*(0.35+0.06*n)),
                   py+length*0.47*np.sin(angle-side*(0.35+0.06*n)))
        q = np.linspace(0.0, 1.0, 61, dtype=np.float32)
        bx = (1-q)**2*px + 2*(1-q)*q*control[0] + q*q*ex
        by = (1-q)**2*py + 2*(1-q)*q*control[1] + q*q*ey
        bdx, bdy = np.gradient(bx), np.gradient(by)
        bmag = np.maximum(1.0, np.hypot(bdx, bdy)); bnx, bny = -bdy/bmag, bdx/bmag
        half = ((7.0+0.11*length)*np.clip(np.sin(np.pi*q), 0.0, None)**0.69
                *(0.83+0.17*np.sin(q*4.0*np.pi+n)**2))
        left = np.column_stack((bx+half*bnx, by+half*bny))
        right = np.column_stack((bx-half*bnx, by-half*bny))[::-1]
        outline = np.vstack((left, right)).astype(np.int32)
        _draw_poly(m["bract_outlines"], outline, width=2)
        cv2.polylines(m["bract_midribs"],
                      [np.column_stack((bx, by)).astype(np.int32)], False,
                      1.0, 2, cv2.LINE_AA)
        for j in (16, 29, 43):
            fork_side = -1.0 if (j+n)%2 else 1.0
            a = np.arctan2(bdy[j], bdx[j]) + fork_side*(0.62+0.09*n)
            _draw_line(m["vascular_forks"], (bx[j], by[j]),
                       (bx[j]+(10+j%7)*np.cos(a), by[j]+(10+j%7)*np.sin(a)), width=1)
        for j in (21, 37, 51):
            edge_x = bx[j]+side*half[j]*bnx[j]
            edge_y = by[j]+side*half[j]*bny[j]
            _draw_line(m["serrated_lips"], (edge_x, edge_y),
                       (edge_x+5*np.cos(angle+side*0.9), edge_y+5*np.sin(angle+side*0.9)), width=1)
        _draw_circle(m["node_collars"], (px, py), 3+n%3, width=1)
        if n in (2, 6, 10, 14):
            cv2.ellipse(m["bud_cups"], (int(ex), int(ey)), (7+n%4, 3),
                        np.degrees(angle), 0, 330, 1.0, 2, cv2.LINE_AA)
        _draw_line(m["apex_hooks"], (bx[-5], by[-5]),
                   (ex+7*np.cos(angle+side*0.72), ey+7*np.sin(angle+side*0.72)), width=1)
        if previous_edge is not None and n in (4, 8, 12, 16):
            _draw_line(m["overlap_slits"], previous_edge, (bx[34], by[34]), width=1)
        previous_edge = (ex, ey)
        cv2.circle(tone, (int(bx[28]), int(by[28])), 9, (n%9)/8.0, -1)
    banks = dict(corkscrew_axis="N", bract_outlines="A", bract_midribs="B",
                 serrated_lips="B", node_collars="N", vascular_forks="A",
                 overlap_slits="B", bud_cups="A", apex_hooks="B")
    ancestry = tone + 0.52*m["bract_outlines"] + 0.43*m["bract_midribs"] + 0.31*m["corkscrew_axis"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.2))


def _build_fbl_magenta_pollen() -> _Grammar:
    """One tri-porate grain whose three apertures grow unrelated fissure arbors."""
    x, y = _xy(); lx, ly = (x-257.0)/1.04, (y-253.0)/0.96
    radius = np.hypot(lx, ly); theta = np.arctan2(ly, lx)
    body_r = 232.0 + 12.0*np.sin(theta*7.0) + 7.0*np.sin(theta*13.0+0.4)
    inside = _f32((body_r-radius)/2.0)
    m = _new_marks("annular_rim", "germ_pores", "primary_fissures",
                   "secondary_forks", "aperture_collars", "inter_pore_bridges",
                   "exine_cushions", "contact_flats", "rupture_scars")
    m["annular_rim"] = _ring(radius, body_r, 0.88)
    pore_angles = (0.18, 2.31, 4.42)
    pore_points = [(257.0+139.0*np.cos(a), 253.0+0.96*139.0*np.sin(a))
                   for a in pore_angles]
    tone = np.zeros((_WORK, _WORK), np.float32)
    for identity, ((sx, sy), angle) in enumerate(zip(pore_points, pore_angles)):
        cv2.ellipse(m["germ_pores"], (int(sx), int(sy)),
                    (23+identity*2, 15+identity), np.degrees(angle),
                    0, 360, 1.0, 2, cv2.LINE_AA)
        cv2.ellipse(m["aperture_collars"], (int(sx), int(sy)),
                    (30+identity*2, 21+identity), np.degrees(angle),
                    12, 349, 1.0, 1, cv2.LINE_AA)
        for branch in range(15):
            a = (angle + np.pi - 1.12 + branch*(2.24/14.0)
                 + 0.07*np.sin(branch*1.7+identity))
            length = 124.0 + 76.0*np.sin((branch+1)*1.23+identity)**2
            ex = sx + length*np.cos(a)
            ey = sy + 0.96*length*np.sin(a)
            control = ((sx+ex)*0.5 + (18+identity*5)*np.cos(a+1.17),
                       (sy+ey)*0.5 + (15+branch%4)*np.sin(a+1.17))
            q = np.linspace(0.0, 1.0, 37, dtype=np.float32)
            bx = (1-q)**2*sx + 2*(1-q)*q*control[0] + q*q*ex
            by = (1-q)**2*sy + 2*(1-q)*q*control[1] + q*q*ey
            cv2.polylines(m["primary_fissures"],
                          [np.column_stack((bx, by)).astype(np.int32)], False,
                          1.0, 2 if branch in (2, 7) else 1, cv2.LINE_AA)
            for fork, j in zip((-1.0, 1.0), (21, 28)):
                tangent = np.arctan2(by[j]-by[j-2], bx[j]-bx[j-2])
                fa = tangent + fork*(0.47+0.06*((branch+identity)%3))
                fl = 16.0 + 9.0*np.sin(branch*1.41+fork)**2
                _draw_line(m["secondary_forks"], (bx[j], by[j]),
                           (bx[j]+fl*np.cos(fa), by[j]+fl*np.sin(fa)), width=1)
            if branch in (1, 5, 9, 13):
                _draw_line(m["rupture_scars"], (bx[-5]-4, by[-5]+2),
                           (bx[-1]+5, by[-1]-2), width=1)
            cv2.circle(tone, (int(bx[20]), int(by[20])), 8,
                       ((branch+identity*4)%10)/9.0, -1)
        for spur in range(7):
            a = angle - 0.73 + spur*0.24 + 0.05*np.sin(spur*1.9+identity)
            length = 73.0 + 29.0*np.sin(spur*1.43+identity)**2
            ex, ey = sx+length*np.cos(a), sy+0.96*length*np.sin(a)
            control = ((sx+ex)*0.5+12*np.cos(a-1.0),
                       (sy+ey)*0.5+12*np.sin(a-1.0))
            q = np.linspace(0.0, 1.0, 29, dtype=np.float32)
            bx = (1-q)**2*sx+2*(1-q)*q*control[0]+q*q*ex
            by = (1-q)**2*sy+2*(1-q)*q*control[1]+q*q*ey
            cv2.polylines(m["primary_fissures"],
                          [np.column_stack((bx, by)).astype(np.int32)], False,
                          1.0, 1, cv2.LINE_AA)
            fa = a + (-1.0 if spur%2 else 1.0)*(0.51+0.03*spur)
            _draw_line(m["secondary_forks"], (bx[18], by[18]),
                       (bx[18]+(13+spur%4)*np.cos(fa),
                        by[18]+(13+spur%4)*np.sin(fa)), width=1)
        other = pore_points[(identity+1)%3]
        control = (257.0+53.0*np.cos(angle+1.18), 253.0+49.0*np.sin(angle+1.18))
        q = np.linspace(0.0, 1.0, 61, dtype=np.float32)
        bx = (1-q)**2*sx + 2*(1-q)*q*control[0] + q*q*other[0]
        by = (1-q)**2*sy + 2*(1-q)*q*control[1] + q*q*other[1]
        cv2.polylines(m["inter_pore_bridges"],
                      [np.column_stack((bx, by)).astype(np.int32)], False,
                      1.0, 3, cv2.LINE_AA)
    for key in ("germ_pores", "primary_fissures", "secondary_forks",
                "aperture_collars", "inter_pore_bridges", "rupture_scars"):
        m[key] *= inside
    m["exine_cushions"] = (_halo(np.maximum(m["primary_fissures"], m["inter_pore_bridges"]), 2.2)
                           * inside * (1.0-m["primary_fissures"]))
    m["contact_flats"] = np.maximum(
        _line(lx-body_r+7.0, 0.62)*(np.abs(ly)<82.0),
        _line(-lx-body_r+8.0, 0.62)*(np.abs(ly)<63.0))
    banks = dict(annular_rim="A", germ_pores="B", primary_fissures="A",
                 secondary_forks="B", aperture_collars="B", inter_pore_bridges="N",
                 exine_cushions="B", contact_flats="N", rupture_scars="A")
    ancestry = tone + 0.49*m["primary_fissures"] + 0.41*m["secondary_forks"] + 0.35*m["annular_rim"]
    return _pack(m, banks, cv2.GaussianBlur(ancestry, (0, 0), 2.1))


# WR-B4 routes every active ID through the owner-eye topology module below.
# The WR-B1 constructors above remain only as auditable rejection history and
# are unreachable from `_authored`, evidence, or installation.
from engine.expansions.fractured_wilds_bloom_w4_topologies_2026 import (  # noqa: E402
    BUILDERS as _BUILDERS,
    owner_unions as _owner_unions,
)


_HUES: Mapping[str, Tuple[float, float]] = {
    "fbl_magenta_whorl": (0.91, 0.47),
    "fbl_leafvine_drape": (0.31, 0.78),
    "fbl_butter_pollen": (0.13, 0.64),
    "fbl_pink_rose": (0.95, 0.47),
    "fbl_coral_cluster": (0.025, 0.52),
    "fbl_butter_mosaic": (0.14, 0.72),
    "fbl_pink_pollen": (0.96, 0.42),
    "fbl_white_whorl": (0.11, 0.57),
    "fbl_coral_stamen": (0.02, 0.49),
    "fbl_lilac_rose": (0.78, 0.31),
    "fbl_coral_vine": (0.015, 0.34),
    "fbl_lilac_stamen": (0.76, 0.12),
    "fbl_magenta_mosaic": (0.89, 0.46),
    "fbl_leaf_whorl": (0.28, 0.83),
    "fbl_white_pollen": (0.10, 0.60),
    "fbl_pink_stamen": (0.94, 0.17),
    "fbl_blush_rose": (0.985, 0.48),
    "fbl_lilac_vine": (0.77, 0.32),
    "fbl_butter_whorl": (0.13, 0.68),
    "fbl_magenta_pollen": (0.91, 0.43),
}

_SATURATION: Mapping[str, Tuple[float, float]] = {
    fid: ((0.34, 0.72) if fid in {"fbl_white_whorl", "fbl_white_pollen"}
          else (0.90, 0.92))
    for fid in _BUILDERS
}

# Fine dark filaments can disappear after the 512->car reduction.  These
# topology-neutral display gammas expose their authored palette without making
# marks larger or adding a decorative carrier.
_DISPLAY_GAMMA: Mapping[str, float] = {
    "fbl_coral_stamen": 0.68,
    "fbl_lilac_stamen": 0.66,
    "fbl_leaf_whorl": 0.76,
    "fbl_pink_stamen": 0.76,
    "fbl_butter_whorl": 0.70,
}

BLOOM_IDS: Tuple[str, ...] = tuple(_BUILDERS)


@lru_cache(maxsize=8)
def _authored(fid: str):
    if fid not in _BUILDERS:
        raise KeyError(fid)
    paint, spec = _compose(_BUILDERS[fid](), _HUES[fid], _SATURATION[fid])
    paint = np.power(paint, float(_DISPLAY_GAMMA.get(fid, 1.0))).astype(np.float32)
    return paint, spec


def clear_cache() -> None:
    _authored.cache_clear()
    _xy.cache_clear()


def debug_grammar(fid: str) -> _Grammar:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _BUILDERS[fid]()


def debug_hue_null(fid: str) -> np.ndarray:
    grammar = debug_grammar(fid)
    out = 0.07 + 0.13 * grammar.tone
    levels = (0.30, 0.72, 0.44, 0.90, 0.56, 0.97, 0.38, 0.80, 0.64, 0.86)
    for i, (_name, mask, _owner) in enumerate(grammar.marks):
        out = out * (1.0 - mask) + levels[i % len(levels)] * mask
    return np.repeat(np.clip(out[..., None], 0, 1), 3, axis=2).astype(np.float32)


def debug_angle_pair(fid: str):
    """Ownership-backed PBR lobe visualization; not independent runtime proof."""
    paint, spec = _authored(fid)
    grammar = debug_grammar(fid)
    owner_a, owner_b = _owner_unions(grammar)
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - 0.58 * rough, 0.20, 1.0)
    hue_a, hue_b = _HUES[fid]
    env_a = _hsv(hue_a + 0.035, 0.88, 0.72)
    env_b = _hsv(hue_b - 0.035, 0.90, 0.76)
    lobe_a = np.clip(owner_a * (0.24 + 0.76 * metal) * aperture
                     + 0.08 * owner_b * coat, 0.0, 1.0)
    lobe_b = np.clip(owner_b * (0.24 + 0.76 * coat) * aperture
                     + 0.08 * owner_a * metal, 0.0, 1.0)
    ma = lobe_a[..., None]
    cb = lobe_b[..., None]
    a = np.clip(paint * (0.10 + 0.46 * ma) + env_a * (0.96 * ma), 0, 1)
    b = np.clip(paint * (0.10 + 0.46 * cb) + env_b * (0.96 * cb), 0, 1)
    diff = np.abs(a - b).astype(np.float32)  # absolute; never normalized per finish
    hsv_a = cv2.cvtColor(a.astype(np.float32), cv2.COLOR_RGB2HSV)
    hsv_b = cv2.cvtColor(b.astype(np.float32), cv2.COLOR_RGB2HSV)
    hd = np.abs(hsv_a[:, :, 0] - hsv_b[:, :, 0])
    hd = np.minimum(hd, 360.0 - hd) / 180.0
    # A lobe can intentionally desaturate while the opponent becomes vivid;
    # use the stronger saturation as reliability so that this real hue handoff
    # is not erased from evidence merely because one angle approaches neutral.
    weight = np.maximum(hsv_a[:, :, 1], hsv_b[:, :, 1]) * np.maximum(hsv_a[:, :, 2], hsv_b[:, :, 2])
    hue_delta = _f32(hd * weight)
    hue_view = np.dstack([hue_delta, np.sqrt(hue_delta), 1.0 - hue_delta]) * hue_delta[..., None]
    return a.astype(np.float32), b.astype(np.float32), diff, hue_view.astype(np.float32)


def _entry(fid: str):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)
        if src.ndim != 3 or src.shape[2] < 3:
            src = np.zeros((fh, fw, 3), np.float32)
        else:
            src = src[:, :, :3]
            if src.size and float(src.max()) > 1.5:
                src = src / 255.0
            if src.shape[:2] != (fh, fw):
                src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored, _ = _authored(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(m2 * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        _, authored = _authored(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(_CALM_SPEC + (authored - _CALM_SPEC) * max(0.0, float(sm)), 0, 255)
        mk = np.clip(m2, 0, 1)[..., None]
        rgb = active * mk + _CALM_SPEC * (1.0 - mk)
        out = np.empty((fh, fw, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    paint_fn.__name__ = f"paint_{fid}_explicit_rebuild"
    spec_fn.__name__ = f"spec_{fid}_explicit_rebuild"
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Install only into the supplied registry; this candidate is not wired."""
    for fid in BLOOM_IDS:
        mono_reg[fid] = _entry(fid)
    return f"fractured-wilds-bloom-explicit-candidate: {len(BLOOM_IDS)} grammars installed"


if len(BLOOM_IDS) != 20 or set(BLOOM_IDS) != set(_HUES) or set(BLOOM_IDS) != set(_SATURATION):
    raise AssertionError("Bloom explicit candidate must own exactly twenty configured IDs")


__all__ = ["BLOOM_IDS", "install_into_engine", "clear_cache", "debug_grammar",
           "debug_hue_null", "debug_angle_pair"]
