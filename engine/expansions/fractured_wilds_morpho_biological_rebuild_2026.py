# -*- coding: utf-8 -*-
"""Literal biological/optical rebuild for 25 Fractured Morpho finishes.

SPB-WILDS, 2026-08-24, rejection rebuild lane WR-MORPHO-BIO-1.  Owner
verdict: "how many have the EXACT SAME pattern just recolored or exact same
spec maps" and "do NOT just put random noise in the patterns to separate the
way they look".

This module replaces only the first 25 current ``fmo_*`` IDs, Morpho Blue
through Duck Speculum.  Each ID owns an explicit builder function that draws
literal anatomy or optics and returns at least seven causal masks.  There is
no RNG, noise field, exotic-source wrapper, shared field router, rank
quantizer, or rotate/seed/palette variant mechanism here.  Larger identity is
assembled from 2--8 px authored primitives at the 512 work size (8--32 px at
native 2048).

Every builder explicitly assigns each named mark to material bank A, B, or N
and supplies its own M/R/Cc targets.  Shared code is limited to low-level SDF
helpers, fixed 14-shade color plumbing, mask compositing, API adaptation, and
evidence rendering.  No owner acceptance is claimed.  Official M7 results are
pending central integration and thumbnail baking.

Audit movement, 2026-08-24: the rejected 50-ID release collapsed into one
seven-scatter/eight-carrier composer plus a shared diagonal/rank spec family.
W1/W2 rendered oval cards, W3 rendered row/grid/pave families, and the later
W9 candidate was independently rejected 0 KEEP / 5 REPAIR / 20 REBUILD.  W10
implemented that rejection matrix literally, then its own full contact sheet
rejected seven residual families.  W11 replaced those; W12 rejected a hubbed
fault layout and two ambiguous card-scale identities; active W13 contains the
resulting 25 canvas-scale constructions.  Every active builder owns its
feature-attached M/R/Cc construction, bypassing the old bright shared M/Cc
halo and widened roughness shoulder.  W14 then split four still-correlated
material roles; its maximum absolute within-finish M/R/Cc correlation is
0.7434.  Fresh W14 evidence reports 25 unique
paint/hue-null/spec hashes, minimum causal-union coverage 0.708, minimum
M/R/Cc standard deviations 63.841/25.046/33.676, minimum A/B mean absolute
response 25.722, and maximum cold 512 construction 0.3436 s.  Evidence is
under ``_wilds_rejection_work/morpho_rebuild/biological_w14``; no result there
inherits the superseded W9 KEEP labels or claims owner acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


_WORK = 512
_CALM_SPEC = np.asarray([4.0, 120.0, 16.0], np.float32)


@dataclass(frozen=True)
class _Mark:
    name: str
    mask: np.ndarray
    bank: str
    metal: float
    rough: float
    coat: float


@dataclass(frozen=True)
class _Grammar:
    marks: Tuple[_Mark, ...]
    tone: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray] | None = None


def _f32(a: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(np.min(a)), float(np.max(a))
    if hi - lo < 1.0e-7:
        return np.zeros_like(a, np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


@lru_cache(maxsize=1)
def _xy() -> Tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:_WORK, 0:_WORK].astype(np.float32)
    return x, y


def _line(v: np.ndarray, half_width: float = 1.25) -> np.ndarray:
    return _f32(1.0 - np.abs(np.asarray(v, np.float32)) / max(.15, float(half_width)))


def _ring(distance: np.ndarray, radius, half_width: float = 1.25) -> np.ndarray:
    return _line(np.asarray(distance, np.float32) - np.asarray(radius, np.float32), half_width)


def _inside(distance: np.ndarray, radius, feather: float = .9) -> np.ndarray:
    return _f32((np.asarray(radius, np.float32) - np.asarray(distance, np.float32))
                / max(.2, float(feather)) + .5)


def _edge(mask: np.ndarray, width: int = 1) -> np.ndarray:
    u = _f32(mask)
    k = max(1, int(width)) * 2 + 1
    kernel = np.ones((k, k), np.uint8)
    return _f32(cv2.dilate(u, kernel) - cv2.erode(u, kernel))


def _halo(mask: np.ndarray, sigma: float = 1.6) -> np.ndarray:
    u = _f32(mask)
    return _f32(cv2.GaussianBlur(u, (0, 0), max(.25, float(sigma))) - .28 * u)


def _local(period_x: float, period_y: float, stagger: bool = False):
    x, y = _xy()
    iy = np.floor(y / period_y).astype(np.int32)
    shift = (iy & 1).astype(np.float32) * period_x * .5 if stagger else 0.0
    ix = np.floor((x - shift) / period_x).astype(np.int32)
    lx = np.mod(x - shift, period_x) - period_x * .5
    ly = np.mod(y, period_y) - period_y * .5
    return lx, ly, ix, iy


def _ellipse(lx: np.ndarray, ly: np.ndarray, rx: float, ry: float) -> np.ndarray:
    return np.sqrt((lx / rx) ** 2 + (ly / ry) ** 2)


def _hex_local(radius: float):
    px, py = radius * 1.72, radius * 1.50
    lx, ly, ix, iy = _local(px, py, True)
    h = np.maximum(np.abs(ly) / radius,
                   (0.8660254 * np.abs(lx) + .5 * np.abs(ly)) / radius)
    return lx, ly, ix, iy, h


def _rect_sdf(lx: np.ndarray, ly: np.ndarray, hx: float, hy: float) -> np.ndarray:
    return np.maximum(np.abs(lx) / hx, np.abs(ly) / hy)


def _periodic_line(z: np.ndarray, period: float, width: float = .16, phase: float = 0.0) -> np.ndarray:
    return _line(np.sin((np.asarray(z, np.float32) / period + phase) * 2.0 * np.pi), width)


def _paths(path_groups, width: int = 2, closed: bool = False) -> np.ndarray:
    """Rasterize builder-owned canvas paths; this is only low-level plumbing."""
    canvas = np.zeros((_WORK, _WORK), np.uint8)
    for points in path_groups:
        pts = np.asarray(points, np.float32)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        pts = np.rint(pts).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(canvas, [pts], bool(closed), 255, max(1, int(width)), cv2.LINE_AA)
    return canvas.astype(np.float32) / 255.0


def _circles(circle_specs, width: int = 2) -> np.ndarray:
    """Rasterize explicit builder-owned circles ``(x, y, r)``."""
    canvas = np.zeros((_WORK, _WORK), np.uint8)
    for cx, cy, radius in circle_specs:
        cv2.circle(canvas, (int(round(cx)), int(round(cy))), max(1, int(round(radius))),
                   255, int(width), cv2.LINE_AA)
    return canvas.astype(np.float32) / 255.0


def _pack(
    masks: Mapping[str, np.ndarray],
    ownership: Mapping[str, Tuple[str, float, float, float]],
    tone: np.ndarray,
) -> _Grammar:
    if len(masks) < 7:
        raise ValueError("lazy Morpho grammar: fewer than seven causal masks")
    if set(masks) != set(ownership):
        raise ValueError("mask/ownership topology mismatch")
    marks = []
    for name, mask in masks.items():
        u = _f32(mask)
        if float(np.std(u)) < .002:
            raise ValueError(f"flat causal mask {name!r}")
        bank, metal, rough, coat = ownership[name]
        if bank not in {"A", "B", "N"}:
            raise ValueError(f"bad material bank for {name!r}")
        marks.append(_Mark(name, u, bank, float(metal), float(rough), float(coat)))
    return _Grammar(tuple(marks), _norm(tone))


def _blend_field(base: float, components) -> np.ndarray:
    """Blend builder-selected named masks into one explicit material channel."""
    out = np.full((_WORK, _WORK), float(base), np.float32)
    for mask, target in components:
        u = _f32(mask)
        out = out * (1.0 - u) + float(target) * u
    return np.clip(out, 0, 255).astype(np.float32)


def _pack10(
    masks: Mapping[str, np.ndarray],
    ownership: Mapping[str, Tuple[str, float, float, float]],
    tone: np.ndarray,
    metal_components,
    rough_components,
    coat_components,
) -> _Grammar:
    """W10 contract: every builder constructs its own visible M/R/Cc fields."""
    grammar = _pack(masks, ownership, tone)
    spec = (
        _blend_field(float(_CALM_SPEC[0]), metal_components),
        _blend_field(float(_CALM_SPEC[1]), rough_components),
        _blend_field(float(_CALM_SPEC[2]), coat_components),
    )
    return _Grammar(grammar.marks, grammar.tone, spec)


def _hsv(h: float, s: float, v: float) -> np.ndarray:
    px = np.uint8([[[int((h % 1.0) * 179.0), int(np.clip(s, 0, 1) * 255),
                     int(np.clip(v, 0, 1) * 255)]]])
    return cv2.cvtColor(px, cv2.COLOR_HSV2RGB)[0, 0].astype(np.float32) / 255.0


def _palette(hues: Sequence[float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Six A shades + six B shades + two bridges: 14 purposeful colors."""
    ha, hb = float(hues[0]), float(hues[1])
    vals = (.22, .32, .44, .58, .74, .94)
    sats = (.62, .72, .82, .90, .96, .76)
    a = np.stack([_hsv(ha + .020 * (i - 2.5), sats[i], vals[i]) for i in range(6)])
    b = np.stack([_hsv(hb - .023 * (i - 2.5), sats[5 - i], vals[i]) for i in range(6)])
    bridge = np.stack([_hsv((ha + hb) * .5, .18, .13),
                       _hsv((ha + hb) * .5 + .09, .32, .62)])
    return a.astype(np.float32), b.astype(np.float32), bridge.astype(np.float32)


_FIXED_BANDS = np.asarray([.12, .27, .43, .60, .78], np.float32)


def _bank_image(bank: np.ndarray, tone: np.ndarray, phase: int) -> np.ndarray:
    idx = np.digitize(np.mod(tone + phase * .079, 1.0), _FIXED_BANDS)
    return bank[idx]


def _compose(grammar: _Grammar, hues: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
    """Low-level color/material plumbing; builders own every target and mask."""
    bank_a, bank_b, neutral = _palette(hues)
    tone = grammar.tone
    paint = np.broadcast_to(neutral[0], (_WORK, _WORK, 3)).copy()
    # The substrate is intentionally calm.  W4 rejected the earlier shared
    # sinusoidal substrate because sparse anatomy could inherit an unrelated
    # spec texture even when its causal marks were honest.  All visible M/R/Cc
    # structure now comes only from builder-owned named marks and junctions.
    if grammar.explicit_spec is None:
        m = np.full((_WORK, _WORK), _CALM_SPEC[0], np.float32)
        r = np.full((_WORK, _WORK), _CALM_SPEC[1], np.float32)
        cc = np.full((_WORK, _WORK), _CALM_SPEC[2], np.float32)
    else:
        m, r, cc = (np.asarray(ch, np.float32).copy() for ch in grammar.explicit_spec)
    owner_a = np.zeros((_WORK, _WORK), np.float32)
    owner_b = np.zeros_like(owner_a)

    for i, mark in enumerate(grammar.marks):
        if mark.bank == "A":
            color = _bank_image(bank_a, tone, i)
            owner_a = np.maximum(owner_a, mark.mask)
        elif mark.bank == "B":
            color = _bank_image(bank_b, tone, i)
            owner_b = np.maximum(owner_b, mark.mask)
        else:
            color = np.broadcast_to(neutral[1], paint.shape)
        coverage = float(np.mean(mark.mask))
        # Large anatomy masks establish a quiet body; fine causal marks carry
        # the identity.  Without this coverage-aware low-level opacity, W1
        # honestly rendered too many different builders as colored oval cards.
        paint_gain = (.38 if coverage > .34 else .60) + .045 * (i % 5)
        alpha = np.clip(mark.mask * paint_gain, 0.0, .86)[..., None]
        paint = paint * (1.0 - alpha) + color * alpha
        if grammar.explicit_spec is None:
            # Legacy W1-W9 behavior retained only for auditable rejected
            # builders.  Active W10 builders bypass it with explicit fields.
            core = np.clip(mark.mask * (1.08 + .04 * (i % 3)), 0.0, .98)
            md = abs(mark.metal - float(_CALM_SPEC[0])) / 251.0
            rd = abs(mark.rough - float(_CALM_SPEC[1])) / 188.0
            cd = abs(mark.coat - float(_CALM_SPEC[2])) / 237.0
            um = np.maximum(core, _halo(mark.mask, .85 + 2.2 * md) * (.32 + .42 * md))
            rk = 5 + 2 * int(np.clip(np.floor(rd * 3.0), 0, 2))
            rough_shoulder = cv2.dilate(mark.mask, np.ones((rk, rk), np.uint8))
            ur = np.maximum(core, rough_shoulder * (.72 + .25 * rd))
            uc = np.maximum(core, _halo(mark.mask, .85 + 2.2 * cd) * (.32 + .42 * cd))
            m = m * (1.0 - um) + mark.metal * um
            r = r * (1.0 - ur) + mark.rough * ur
            cc = cc * (1.0 - uc) + mark.coat * uc

    # This 2--4 px A/B contact seam is derived from the builder's ownership;
    # it does not introduce an independent texture.
    junction = _f32(_edge(owner_a, 1) * _edge(owner_b, 1))
    paint = paint * (1.0 - .62 * junction[..., None]) + neutral[1] * (.62 * junction[..., None])
    if grammar.explicit_spec is None:
        m = m * (1.0 - junction) + 126.0 * junction
        r = r * (1.0 - junction) + 26.0 * junction
        cc = cc * (1.0 - junction) + 234.0 * junction

    spec = np.dstack([np.clip(m, 0, 255), np.clip(r, 0, 255), np.clip(cc, 0, 255)])
    return np.clip(paint, 0, 1).astype(np.float32), spec.astype(np.uint8)


# ---------------------------------------------------------------------------
# Twenty-five literal biological/optical construction graphs.


def _build_fmo_morpho_blue() -> _Grammar:
    """Continuous Christmas-tree lamellae: no enclosing scale-card silhouette."""
    x, y = _xy()
    bend = x + 1.15 * np.sin(y / 21.0) + .35 * np.sin(y / 5.2)
    lane = np.mod(bend, 9.0) - 4.5
    row = np.mod(y + .18 * bend, 5.0) - 2.5
    trunks = _line(lane, .66)
    left_shelves = _line(row + .70 * lane, .48) * (lane < -.15) * (lane > -4.0)
    right_shelves = _line(row - .70 * lane, .48) * (lane > .15) * (lane < 4.0)
    shelf_lips = _line(np.abs(row) - 1.28, .35) * (np.abs(lane) < 3.7)
    christmas_forks = _line(np.abs(lane) - (1.15 + .72 * np.abs(row)), .44) * (np.abs(row) < 1.9)
    bridge_ribs = _periodic_line(y + .24 * x, 13.0, .12) * (np.abs(lane) > 2.7)
    pores = _ring(np.hypot(lane - 2.75, np.mod(y, 10.0) - 5.0), .82, .38)
    tooth_train = _periodic_line(y, 2.55, .16) * (np.abs(lane) < 1.1)
    dislocation = _line(lane - .48 * row, .43) * (((np.floor(y / 20.0).astype(np.int32)
                                                    + np.floor(x / 27.0).astype(np.int32)) % 7) == 0)
    masks = dict(nanoridge_trunks=trunks, left_lamellar_shelves=left_shelves,
                 right_lamellar_shelves=right_shelves, shelf_edge_lips=shelf_lips,
                 christmas_tree_forks=christmas_forks, interscale_bridge_ribs=bridge_ribs,
                 ordered_perforation_pores=pores, tooth_trains_and_dislocations=np.maximum(tooth_train, dislocation))
    own = dict(nanoridge_trunks=("A", 242, 30, 22), left_lamellar_shelves=("A", 214, 48, 38),
               right_lamellar_shelves=("B", 48, 74, 246), shelf_edge_lips=("B", 82, 44, 252),
               christmas_tree_forks=("A", 188, 92, 54), interscale_bridge_ribs=("B", 68, 158, 222),
               ordered_perforation_pores=("N", 24, 236, 58), tooth_trains_and_dislocations=("N", 112, 206, 84))
    return _pack(masks, own, _norm(.46 * np.sin(bend / 9.0) + y / 71.0 + .18 * shelf_lips))


def _build_fmo_sunset_moth() -> _Grammar:
    """Connected scallop venation with branching sunset bands and free fringe."""
    x, y = _xy()
    sweep = x + .24 * y + 5.0 * np.sin(y / 29.0)
    vein_lane = np.mod(sweep, 31.0) - 15.5
    lobe_y = np.mod(y + 3.0 * np.sin(x / 33.0), 24.0) - 12.0
    primary = _line(vein_lane, .92)
    costal = _line(lobe_y - .052 * vein_lane * vein_lane + 7.0, .68)
    upper_branch = _periodic_line(y - .58 * np.abs(vein_lane) + 2.0, 13.0, .13) * (vein_lane > -14)
    lower_branch = _periodic_line(y + .43 * np.abs(vein_lane) - 1.0, 17.0, .13) * (vein_lane < 14)
    scale_rakes = _periodic_line(y + .20 * x, 3.25, .17) * (np.abs(vein_lane) > 2.2)
    scallop_rims = _line(lobe_y - 2.5 * np.cos(vein_lane / 4.5), .58)
    crescent_bands = _line(np.hypot(vein_lane + 8.0, lobe_y - 1.0) - 4.4, .58) * (lobe_y > -1.0)
    false_eye_wedges = _inside(np.maximum(np.abs(vein_lane - 8.8) / 1.8,
                                          np.abs(lobe_y + 2.0) / 3.0), 1.0, .22)
    fringe = _periodic_line(x, 2.75, .18) * (np.abs(lobe_y - 9.0) < 1.0)
    masks = dict(primary_costal_veins=primary, scalloped_lobe_seams=costal,
                 upper_venation_forks=upper_branch, lower_venation_forks=lower_branch,
                 directional_scale_rakes=scale_rakes, chained_crescent_bands=crescent_bands,
                 false_eye_wedges=false_eye_wedges, free_fringe_and_rims=np.maximum(fringe, scallop_rims))
    own = dict(primary_costal_veins=("A", 240, 34, 30), scalloped_lobe_seams=("N", 108, 74, 96),
               upper_venation_forks=("A", 202, 52, 46), lower_venation_forks=("B", 66, 122, 232),
               directional_scale_rakes=("B", 92, 166, 214), chained_crescent_bands=("B", 44, 48, 252),
               false_eye_wedges=("A", 220, 186, 34), free_fringe_and_rims=("N", 24, 238, 58))
    return _pack(masks, own, _norm(sweep / 68.0 + .31 * np.sin(lobe_y / 5.0) + .16 * crescent_bands))


def _build_fmo_monarch_vein() -> _Grammar:
    """Fine hex wing-cell graph crossed by genuinely wider Murray-law trunks."""
    x, y = _xy()
    lx, ly, ix, iy, h = _hex_local(5.4)
    cell_border = _line(h - .94, .07)
    inner_margin = _line(h - .70, .08)
    primary = _periodic_line(x + .17 * y + 2.5 * np.sin(y / 37.0), 47.0, .055)
    secondary_a = _periodic_line(y - .58 * x, 53.0, .055)
    secondary_b = _periodic_line(y + .36 * x + 5.0 * np.sin(x / 61.0), 71.0, .055)
    tertiary = _line(np.abs(lx) - (.34 * np.abs(ly) + 2.05), .42) * (h < .9)
    scale_bricks = _periodic_line(ly + .16 * lx, 2.35, .19) * (h < .70)
    white_insets = _inside(np.hypot(lx - 2.6, ly + 2.1), .72, .26) * (((ix + 2 * iy) % 9) == 0)
    nodes = _ring(np.hypot(lx, ly), .78, .36) * (((2 * ix - iy) % 7) == 0)
    masks = dict(closed_hex_wing_cells=cell_border, black_inner_margins=inner_margin,
                 murray_primary_veins=primary, ordered_secondary_branches=np.maximum(secondary_a, secondary_b),
                 tertiary_cell_forks=tertiary, orange_scale_bricks=scale_bricks,
                 white_spot_insets=white_insets, cross_vein_nodes=nodes)
    own = dict(closed_hex_wing_cells=("N", 26, 236, 28), black_inner_margins=("A", 202, 62, 42),
               murray_primary_veins=("A", 242, 30, 26), ordered_secondary_branches=("B", 58, 70, 248),
               tertiary_cell_forks=("B", 94, 112, 230), orange_scale_bricks=("A", 180, 138, 54),
               white_spot_insets=("N", 72, 188, 112), cross_vein_nodes=("B", 122, 44, 242))
    return _pack(masks, own, _norm(.42 * h + .31 * np.sin((x + y) / 17.0) + .20 * primary))


def _build_fmo_atlas_wing() -> _Grammar:
    """Interlocked costal S-hooks: the snake mimic is drawn by veins, not blobs."""
    x, y = _xy()
    lx = np.mod(x + 3.4 * np.sin(y / 15.0), 21.0) - 10.5
    ly = np.mod(y, 18.0) - 9.0
    row = np.floor(y / 18.0).astype(np.int32)
    s_curve = lx - 3.5 * np.sin((ly + 1.0) / 3.4)
    hooked_costal = _line(s_curve, .76)
    jaw = _line(ly - .52 * s_curve - 1.2, .56) * (np.abs(s_curve) < 6.2)
    brow = _line(ly + .075 * (s_curve - 1.4) ** 2 - 4.8, .55) * (np.abs(s_curve) < 6.8)
    pupil = _inside(_ellipse(s_curve + 2.2, ly + 3.3, .95, 1.45), 1.0, .22)
    neck_scales = _periodic_line(ly + .45 * s_curve, 2.8, .18) * (np.abs(s_curve) < 5.8) * (ly > -4.0)
    cross_veins = _periodic_line(s_curve - .22 * ly, 3.1, .17) * (np.abs(s_curve) < 6.8)
    antennae = _line(np.abs(s_curve) - (3.2 + .25 * (ly + 8.0)), .48) * (ly < -3.5)
    bite_notches = _ring(np.hypot(s_curve - 5.0, ly - 1.2), 1.2, .42) * (((row + np.floor(x / 21).astype(np.int32)) % 4) == 0)
    masks = dict(hooked_costal_spines=hooked_costal, articulated_jaw_bands=jaw,
                 false_eye_brows=brow, false_pupil_slits=pupil, neck_scale_rakes=neck_scales,
                 membrane_cross_veins=cross_veins, forked_antennae=antennae, bite_notch_crescents=bite_notches)
    own = dict(hooked_costal_spines=("A", 240, 32, 28), articulated_jaw_bands=("B", 68, 78, 244),
               false_eye_brows=("A", 206, 52, 42), false_pupil_slits=("N", 18, 242, 20),
               neck_scale_rakes=("B", 102, 152, 220), membrane_cross_veins=("N", 118, 186, 88),
               forked_antennae=("B", 54, 54, 252), bite_notch_crescents=("A", 194, 178, 36))
    return _pack(masks, own, _norm(.34 * np.sin(s_curve / 4.0) + y / 63.0 + .22 * brow))


def _build_fmo_luna_dust() -> _Grammar:
    """Chladni plate where dust accumulates only on deterministic nodal curves."""
    x, y = _xy()
    ch = np.sin(x * np.pi / 13.0) * np.sin(y * np.pi / 17.0) - .64 * np.sin(x * np.pi / 19.0) * np.sin(y * np.pi / 11.0)
    nodes = _line(ch, .105)
    beads = nodes * _periodic_line(x + .37 * y, 4.2, .19)
    antinodes = _f32((np.abs(ch) - .62) / .16)
    lx, ly, ix, iy = _local(29.0, 29.0, True)
    rr = np.hypot(lx, ly)
    craters = _ring(rr, 3.4, .72) * (((ix + iy) % 4) == 0)
    ejecta = _ring(np.hypot(lx + 2.5, ly), 6.0, .66) * (lx > -2.0) * (((ix - iy) % 3) == 0)
    spokes = _line(np.sin(np.arctan2(ly, lx) * 6.0), .16) * (rr > 3.0) * (rr < 9.0)
    flakes = _inside(np.maximum(np.abs(lx - 6.0), np.abs(ly + 5.0)), 1.25, .35)
    clearings = _inside(rr, 7.8, .8) * antinodes
    masks = dict(chladni_nodal_curves=nodes, compressed_bead_chains=beads,
                 cleared_antinode_islands=clearings, crater_cups=craters,
                 crescent_ejecta=ejecta, radial_spoke_cracks=spokes,
                 moon_scale_flakes=flakes, compressed_dust_ridges=_edge(nodes, 1))
    own = dict(chladni_nodal_curves=("A", 220, 58, 44), compressed_bead_chains=("A", 248, 32, 22),
               cleared_antinode_islands=("N", 26, 236, 74), crater_cups=("B", 68, 94, 236),
               crescent_ejecta=("B", 104, 166, 212), radial_spoke_cracks=("N", 44, 218, 58),
               moon_scale_flakes=("B", 142, 72, 246), compressed_dust_ridges=("A", 188, 112, 36))
    return _pack(masks, own, _norm(ch + .18 * rr / 15.0))


def _build_fmo_swallowtail() -> _Grammar:
    """A dense fork-and-tail arrow lattice, with no enclosing oval vanes."""
    x, y = _xy()
    lx = np.mod(x + .18 * y, 15.0) - 7.5
    ly = np.mod(y, 17.0) - 8.5
    ix = np.floor((x + .18 * y) / 15.0).astype(np.int32)
    iy = np.floor(y / 17.0).astype(np.int32)
    shaft = _line(lx, .64)
    upper_forks = np.maximum(_line(lx - .62 * (ly + 1.0) - 1.0, .48),
                             _line(lx + .62 * (ly + 1.0) + 1.0, .48)) * (ly < 2.5)
    tail_prongs = np.maximum(_line(lx - .86 * (ly - 2.0), .46),
                             _line(lx + .86 * (ly - 2.0), .46)) * (ly > 1.5)
    tail_notch = _line(np.abs(lx) - (.32 * (ly - 1.0) + 1.1), .40) * (ly > 1.0)
    flash_windows = _inside(_rect_sdf(lx - 3.6, ly + 1.2, 1.15, 2.4), 1.0, .20)
    scale_rakes = _periodic_line(ly + .27 * lx, 2.7, .18) * (np.abs(lx) > 1.0)
    marginal_eyes = _ring(np.hypot(lx + 4.7, ly - 4.5), .82, .37) * (((ix - iy) % 3) == 0)
    hinge_teeth = _periodic_line(x, 2.45, .19) * (np.abs(ly - 6.7) < .75)
    masks = dict(central_vane_shafts=shaft, upper_forked_veins=upper_forks,
                 elongated_tail_prongs=tail_prongs, swallowtail_v_notches=tail_notch,
                 rectangular_flash_windows=flash_windows, directional_scale_rakes=scale_rakes,
                 marginal_micro_eyes=marginal_eyes, articulated_hinge_teeth=hinge_teeth)
    own = dict(central_vane_shafts=("N", 32, 232, 32), upper_forked_veins=("A", 232, 38, 34),
               elongated_tail_prongs=("A", 196, 64, 48), swallowtail_v_notches=("B", 54, 58, 250),
               rectangular_flash_windows=("B", 96, 114, 232), directional_scale_rakes=("B", 78, 156, 218),
               marginal_micro_eyes=("A", 214, 188, 30), articulated_hinge_teeth=("N", 108, 198, 76))
    return _pack(masks, own, _norm(.31 * lx / 7.5 + .48 * ly / 8.5 + .20 * upper_forks))


def _build_fmo_ulysses_flash() -> _Grammar:
    """Tilted nanoridge parquet with per-domain diffraction order."""
    lx, ly, ix, iy = _local(22.0, 20.0, True)
    angle_code = ((ix + 2 * iy) % 4).astype(np.float32)
    ca = np.cos(angle_code * np.pi / 4.0); sa = np.sin(angle_code * np.pi / 4.0)
    u, v = ca * lx - sa * ly, sa * lx + ca * ly
    walls = _line(_rect_sdf(lx, ly, 10.2, 9.1) - .96, .07)
    combs = _periodic_line(u, 2.45, .18) * (_rect_sdf(lx, ly, 9.2, 8.2) < 1)
    crossbars = _periodic_line(v, 5.1, .15) * (np.abs(u) < 8.5)
    joints = _inside(np.maximum(np.abs(lx - 8.2), np.abs(ly - 7.0)), 1.15, .35)
    ticks = _periodic_line(v, 3.2, .19) * (np.abs(u - 7.5) < 1.1)
    hinge = _line(v + 6.6, .68) * (np.abs(u) < 7.5)
    forks = np.maximum(_line(u - .48 * v - 1.5, .58), _line(u + .48 * v + 1.5, .58)) * (np.abs(v) < 3.0)
    order_front = _line(np.sin(u * .43 + v * .21 + angle_code), .18)
    masks = dict(parquet_domain_walls=walls, oriented_diffraction_combs=combs,
                 domain_crossbars=crossbars, overlap_joints=joints,
                 diffraction_order_ticks=ticks, hinge_gaps=hinge,
                 dislocation_forks=forks, moving_order_fronts=order_front)
    own = dict(parquet_domain_walls=("N", 96, 196, 80), oriented_diffraction_combs=("A", 240, 36, 28),
               domain_crossbars=("B", 56, 72, 244), overlap_joints=("A", 182, 118, 52),
               diffraction_order_ticks=("B", 98, 46, 250), hinge_gaps=("N", 22, 238, 24),
               dislocation_forks=("A", 214, 154, 38), moving_order_fronts=("B", 72, 104, 230))
    return _pack(masks, own, _norm(angle_code / 4.0 + .22 * u / 22.0 + .12 * v / 20.0))


def _build_fmo_owl_eye() -> _Grammar:
    """Paired owl facial discs: brows and beak chevrons dominate tiny pupils."""
    x, y = _xy()
    lx, ly, ix, iy = _local(22.0, 18.0, True)
    left_r = np.hypot(lx + 3.8, ly + .8)
    right_r = np.hypot(lx - 3.8, ly + .8)
    facial_discs = np.maximum(_ring(left_r, 4.7, .48), _ring(right_r, 4.7, .48))
    pupils = np.maximum(_inside(left_r, 1.05, .27), _inside(right_r, 1.05, .27))
    iris_bars = np.maximum(_periodic_line(np.arctan2(ly + .8, lx + 3.8), .50, .17) * (left_r > 2.0) * (left_r < 4.5),
                           _periodic_line(np.arctan2(ly + .8, lx - 3.8), .50, .17) * (right_r > 2.0) * (right_r < 4.5))
    horn_brows = np.maximum(_line(ly + .58 * np.abs(lx) - 5.1, .52),
                             _line(ly - .22 * np.abs(lx) + 3.5, .46)) * (np.abs(lx) < 9.0)
    beak_chevron = _line(np.abs(lx) + .72 * ly - 3.1, .46) * (ly > -1.5)
    feather_combs = _periodic_line(ly + .24 * lx, 2.65, .18) * (np.minimum(left_r, right_r) > 4.6)
    square_glints = np.maximum(_inside(_rect_sdf(lx + 4.2, ly + .1, .62, .55), 1.0, .20),
                               _inside(_rect_sdf(lx - 3.4, ly + .1, .62, .55), 1.0, .20))
    ear_tufts = _line(np.abs(lx) - (5.0 + .58 * (ly + 6.5)), .44) * (ly < -3.0)
    masks = dict(paired_facial_disc_rims=facial_discs, paired_dark_pupils=pupils,
                 broken_radial_iris_bars=iris_bars, horned_brow_chevrons=horn_brows,
                 central_beak_chevrons=beak_chevron, surrounding_feather_combs=feather_combs,
                 offset_square_glints=square_glints, pointed_ear_tufts=ear_tufts)
    own = dict(paired_facial_disc_rims=("A", 222, 44, 40), paired_dark_pupils=("N", 18, 244, 18),
               broken_radial_iris_bars=("B", 72, 112, 238), horned_brow_chevrons=("A", 192, 78, 52),
               central_beak_chevrons=("B", 106, 58, 246), surrounding_feather_combs=("B", 84, 164, 216),
               offset_square_glints=("N", 104, 194, 104), pointed_ear_tufts=("A", 210, 184, 32))
    return _pack(masks, own, _norm(.36 * left_r / 6.0 + .28 * right_r / 6.0 + .25 * horn_brows))


def _build_fmo_glasswing() -> _Grammar:
    """Transparent membrane truss with panes, capillaries and stress notches."""
    x, y = _xy()
    lx, ly, ix, iy = _local(34.0, 22.0, True)
    pane = _inside(_rect_sdf(lx, ly, 15.0, 9.2), 1.0, .10)
    primary = _line(lx + .22 * ly, 1.10)
    secondary = np.maximum(_line(ly - .42 * lx, .76), _line(ly + .42 * lx, .76))
    caustic = _periodic_line(ly + 2.4 * np.sin((lx + ix) / 5.2), 3.3, .17) * pane
    border_scales = _periodic_line(lx, 2.6, .19) * (np.abs(ly) > 7.5) * pane
    trichia = _periodic_line(lx + .3 * ly, 2.2, .15) * pane * (np.abs(ly) < 6.8)
    nodes = _inside(np.hypot(lx - 13.6, ly - 8.0), 1.35, .40)
    stress = _line(lx - .72 * ly - 6.0, .58) * pane * (((ix + iy) % 4) == 0)
    capillary = _ring(_ellipse(lx + 5.5, ly, 4.0, 2.8), .82, .10) * pane
    masks = dict(transparent_membrane_panes=pane, primary_veins=primary,
                 secondary_trusses=secondary, newton_caustic_wrinkles=caustic,
                 sparse_border_scales=border_scales, microtrichia_combs=trichia,
                 node_pads_and_stress_notches=np.maximum(nodes, stress), capillary_loops=capillary)
    own = dict(transparent_membrane_panes=("B", 48, 72, 242), primary_veins=("A", 226, 38, 42),
               secondary_trusses=("A", 188, 58, 64), newton_caustic_wrinkles=("B", 74, 116, 250),
               sparse_border_scales=("N", 104, 206, 78), microtrichia_combs=("N", 28, 236, 46),
               node_pads_and_stress_notches=("A", 242, 152, 26), capillary_loops=("B", 118, 46, 222))
    return _pack(masks, own, _norm((x + 2.0 * y) / 93.0 + .18 * caustic))


def _build_fmo_emperor_scale() -> _Grammar:
    """Open five-ray crown fans articulated on a staggered hinge lattice."""
    lx, ly, ix, iy = _local(13.0, 12.0, True)
    rr = np.hypot(lx, ly + 4.1)
    th = np.arctan2(ly + 4.1, lx)
    fan_envelope = (rr > 1.2) * (rr < 8.2) * (ly < 3.8)
    crown_rays = _periodic_line(th, .43, .16) * fan_envelope
    ray_crossbars = _periodic_line(rr, 2.35, .18) * crown_rays
    basal_hinges = _ring(rr, 1.8, .42)
    crown_arc = _ring(rr, 7.0, .48) * (ly < 3.3)
    tip_beads = _ring(rr, 6.25, .36) * _periodic_line(th, .43, .20)
    overlap_lips = _line(ly - 3.0 + .045 * lx * lx, .52)
    edge_teeth = _periodic_line(lx, 2.15, .18) * (np.abs(ly - 3.0) < .85)
    missing_ray = crown_rays * (((2 * ix + iy) % 7) == 0) * (th > .25) * (th < .72)
    masks = dict(open_crown_rays=crown_rays, ray_crossbar_ladders=ray_crossbars,
                 circular_basal_hinges=basal_hinges, scalloped_crown_arcs=crown_arc,
                 terminal_diffraction_beads=tip_beads, overlap_hinge_lips=overlap_lips,
                 serrated_edge_teeth=edge_teeth, deterministic_missing_rays=missing_ray)
    own = dict(open_crown_rays=("A", 234, 36, 34), ray_crossbar_ladders=("B", 66, 92, 242),
               circular_basal_hinges=("N", 30, 234, 38), scalloped_crown_arcs=("A", 192, 74, 50),
               terminal_diffraction_beads=("B", 42, 50, 252), overlap_hinge_lips=("B", 106, 142, 226),
               serrated_edge_teeth=("A", 208, 178, 34), deterministic_missing_rays=("N", 18, 244, 20))
    return _pack(masks, own, _norm(th / np.pi + .29 * rr / 8.0 + .18 * ray_crossbars))


def _build_fmo_jewel_scarab() -> _Grammar:
    """A continuous paired-elytron rail system with triangular scutella."""
    x, y = _xy()
    carrier = x + 1.8 * np.sin(y / 31.0)
    pair_lx = np.mod(carrier, 34.0) - 17.0
    pair_ix = np.floor(carrier / 34.0).astype(np.int32)
    suture = _line(pair_lx, .80)
    paired_costae = _periodic_line(np.abs(pair_lx) + .12 * y, 4.15, .16)
    costa_lips = _periodic_line(np.abs(pair_lx) + .12 * y, 4.15, .16, .5)
    scutellum = _line(np.abs(pair_lx) + .58 * (np.mod(y, 17.0) - 8.5) - 3.4, .48) * (np.mod(y, 17.0) < 8.5)
    punctures = _ring(np.hypot(np.mod(np.abs(pair_lx), 4.15) - 2.08,
                                     np.mod(y + 2.0 * (pair_ix & 1), 5.1) - 2.55), .64, .34)
    hex_phase = (np.sin(x * .91) + np.sin((.5 * x + .866 * y) * .91)
                 + np.sin((.5 * x - .866 * y) * .91))
    microcells = _line(hex_phase + .12, .20)
    file_teeth = _periodic_line(y, 2.3, .20) * (np.abs(pair_lx) < 1.45)
    schiller = _line(np.sin((y + .44 * x) / 2.45) + .24 * np.sin(x / 7.0), .18)
    masks = dict(central_elytral_sutures=suture, paired_longitudinal_costae=paired_costae,
                 raised_costa_lips=costa_lips, repeated_scutellum_triangles=scutellum,
                 ordered_puncture_files=punctures, cuticular_hex_microcells=microcells,
                 stridulatory_suture_teeth=file_teeth, migrating_schiller_bands=schiller)
    own = dict(central_elytral_sutures=("N", 26, 238, 28), paired_longitudinal_costae=("A", 238, 34, 32),
               raised_costa_lips=("A", 188, 82, 52), repeated_scutellum_triangles=("B", 60, 52, 250),
               ordered_puncture_files=("N", 38, 220, 72), cuticular_hex_microcells=("A", 206, 148, 42),
               stridulatory_suture_teeth=("B", 104, 176, 218), migrating_schiller_bands=("B", 44, 62, 252))
    return _pack(masks, own, _norm(.29 * pair_lx / 17.0 + y / 61.0 + .25 * schiller))


def _build_fmo_tiger_beetle() -> _Grammar:
    """Branching cream maculation traverses continuous corrugated armor."""
    x, y = _xy()
    corr = x + 2.0 * np.sin(y / 10.0) + .7 * np.sin(y / 3.2)
    furrows = _periodic_line(corr, 5.2, .16)
    ridges = _periodic_line(corr, 5.2, .16, .5)
    trunk = y - 8.0 * np.sin(x / 17.0) - 3.0 * np.sin(x / 5.7)
    branch_a = trunk - .55 * np.mod(x, 27.0) + 7.0
    branch_b = trunk + .48 * np.mod(x + 9.0, 31.0) - 8.0
    maculation_trunks = _periodic_line(trunk, 43.0, .065)
    cream_forks = np.maximum(_periodic_line(branch_a, 43.0, .075),
                             _periodic_line(branch_b, 43.0, .075))
    ribbon_lips = np.maximum(_periodic_line(trunk + 2.2, 43.0, .060),
                             _periodic_line(trunk - 2.2, 43.0, .060))
    puncta = _ring(np.hypot(np.mod(corr, 5.2) - 2.6,
                                  np.mod(y + .2 * x, 6.2) - 3.1), .58, .30)
    suture_ladders = _periodic_line(y, 2.9, .20) * _periodic_line(x + .12 * y, 47.0, .055)
    shoulder_calluses = _line(np.sin((x - .34 * y) / 5.2), .17) * (cream_forks > .18)
    masks = dict(longitudinal_corrugation_furrows=furrows, raised_interstrial_ridges=ridges,
                 branching_maculation_trunks=maculation_trunks, bifurcated_cream_forks=cream_forks,
                 double_maculation_ribbon_lips=ribbon_lips, ordered_puncture_files=puncta,
                 sparse_suture_ladders=suture_ladders, crystalline_shoulder_calluses=shoulder_calluses)
    own = dict(longitudinal_corrugation_furrows=("N", 24, 240, 30), raised_interstrial_ridges=("A", 236, 36, 38),
               branching_maculation_trunks=("B", 48, 60, 252), bifurcated_cream_forks=("B", 88, 102, 238),
               double_maculation_ribbon_lips=("A", 204, 82, 50), ordered_puncture_files=("N", 42, 218, 72),
               sparse_suture_ladders=("A", 190, 180, 32), crystalline_shoulder_calluses=("B", 108, 148, 222))
    return _pack(masks, own, _norm(.38 * np.sin(trunk / 13.0) + corr / 47.0 + .20 * cream_forks))


def _build_fmo_stag_carapace() -> _Grammar:
    """Shield plates with antler channels, keels, pore bosses and repairs."""
    lx, ly, ix, iy, h = _hex_local(10.5)
    plate = _f32((.93 - h) / .10)
    gutters = _line(h - .96, .065)
    keel = _line(lx + .20 * ly, .85) * plate
    horn_arc = _ring(_ellipse(lx - 2.0, ly + 1.0, 5.6, 4.0), .78, .12) * plate * (lx > -4)
    bosses = _ring(np.hypot(lx + 4.2, ly - 2.2), 1.25, .55) * plate
    bevels = _edge(plate, 1)
    repairs = np.maximum(_line(lx - .62 * ly - 1.5, .55),
                         _line(lx + .42 * ly + 2.0, .55)) * plate * (((ix - iy) % 6) == 0)
    rasp = _periodic_line(ly + .18 * lx, 2.7, .18) * plate
    shoulder = _inside(np.hypot(lx - 6.0, ly + 5.0), 1.8, .45) * plate
    masks = dict(shield_plates=plate, joint_gutters=gutters, raised_keels=keel,
                 antler_channels=horn_arc, puncture_bosses=bosses, rim_bevels=bevels,
                 split_repairs_and_shoulder_spikes=np.maximum(repairs, shoulder), rasp_rows=rasp)
    own = dict(shield_plates=("A", 158, 112, 62), joint_gutters=("N", 22, 242, 24),
               raised_keels=("A", 238, 34, 36), antler_channels=("B", 64, 82, 244),
               puncture_bosses=("N", 42, 222, 66), rim_bevels=("B", 102, 54, 226),
               split_repairs_and_shoulder_spikes=("A", 204, 184, 32), rasp_rows=("B", 82, 138, 216))
    return _pack(masks, own, _norm(h + .16 * (ix % 5) + .11 * rasp))


def _build_fmo_chrysina_gold() -> _Grammar:
    """Chirped Bragg lamellae nested inside crystalline reflector tiles."""
    lx, ly, ix, iy = _local(24.0, 24.0, True)
    u = (lx + ly) * .7071; v = (ly - lx) * .7071
    tile_sdf = _rect_sdf(u, v, 10.5, 10.5)
    tile = _inside(tile_sdf, 1.0, .08)
    seams = _line(tile_sdf - .96, .055)
    radial = np.hypot(u + 1.4 * np.sin(iy), v)
    lamellae = _periodic_line(radial + .018 * radial * radial, 2.55, .18) * tile
    cross_ribs = _periodic_line(np.arctan2(v, u), .52, .17) * tile * (radial > 2.5)
    dislocation = _line(u - .46 * v, .58) * tile * (((ix + iy) % 5) == 0)
    pinholes = _ring(np.hypot(u - 5.0, v + 4.0), .85, .43) * tile
    crack_arrest = _ring(np.hypot(u + 5.0, v - 2.0), 3.0, .62) * (v > -2) * tile
    order_front = _line(np.sin(radial * .82 + .42 * np.arctan2(v, u)), .18) * tile
    masks = dict(crystalline_tiles=tile, rim_seams=seams, curved_bragg_lamellae=lamellae,
                 lamellar_cross_ribs=cross_ribs, layer_dislocations=dislocation,
                 pinhole_defects=pinholes, crack_arrest_crescents=crack_arrest,
                 local_diffraction_order_fronts=order_front)
    own = dict(crystalline_tiles=("A", 186, 88, 72), rim_seams=("N", 38, 228, 42),
               curved_bragg_lamellae=("B", 56, 66, 250), lamellar_cross_ribs=("A", 238, 38, 34),
               layer_dislocations=("N", 26, 242, 28), pinhole_defects=("N", 18, 224, 76),
               crack_arrest_crescents=("A", 208, 168, 40), local_diffraction_order_fronts=("B", 94, 104, 232))
    return _pack(masks, own, _norm(radial / 15.0 + .17 * (ix % 6) + .10 * order_front))


def _build_fmo_oil_beetle() -> _Grammar:
    """Continuous oily phase labyrinth with gland ducts and branch cuts."""
    x, y = _xy()
    phase = (np.sin(x / 5.4 + 1.15 * np.sin(y / 13.0))
             + .82 * np.sin(y / 7.1 - .58 * np.sin(x / 11.0)))
    zero_order = _line(phase, .16)
    positive_order = _line(phase - .78, .16)
    negative_order = _line(phase + .78, .16)
    ducts = _line(np.sin(y / 2.65 + 1.7 * np.sin(x / 9.0)), .16)
    gland_pores = _ring(np.hypot(np.mod(x + 2.0 * np.sin(y / 11.0), 8.0) - 4.0,
                                      np.mod(y, 7.0) - 3.5), .76, .35) * (np.abs(phase) > .7)
    branch_cuts = _periodic_line(x - .64 * y + 3.0 * np.sin(y / 19.0), 67.0, .055)
    caustic_tongues = _line(np.sin((x + .31 * y) / 3.1) + .44 * np.sin(y / 2.3), .15) * (phase > .25)
    cusp_calluses = _ring(np.hypot(np.mod(x, 23.0) - 11.5,
                                    np.mod(y + 5.0, 19.0) - 9.5), 2.6, .48) * (phase < -.45)
    masks = dict(zero_order_labyrinths=zero_order, positive_phase_lips=positive_order,
                 negative_phase_lips=negative_order, meandering_oil_gland_ducts=ducts,
                 phase_attached_gland_pores=gland_pores, crystallographic_branch_cuts=branch_cuts,
                 moving_caustic_tongues=caustic_tongues, cusp_callus_crescents=cusp_calluses)
    own = dict(zero_order_labyrinths=("A", 230, 38, 36), positive_phase_lips=("B", 42, 52, 252),
               negative_phase_lips=("B", 92, 104, 238), meandering_oil_gland_ducts=("A", 198, 72, 50),
               phase_attached_gland_pores=("N", 30, 228, 70), crystallographic_branch_cuts=("N", 104, 198, 78),
               moving_caustic_tongues=("B", 118, 64, 244), cusp_callus_crescents=("A", 210, 176, 34))
    return _pack(masks, own, _norm(phase + .22 * np.sin((x - y) / 17.0)))


def _build_fmo_firefly_shell() -> _Grammar:
    """Articulated lantern abdomen with windows, spiracles and pulse bars."""
    lx, ly, ix, iy = _local(30.0, 20.0, True)
    plate = _inside(_rect_sdf(lx, ly, 13.5, 8.2), 1.0, .10)
    joints = _line(np.abs(ly) - 8.0, .78) * (np.abs(lx) < 13.0)
    windows = _inside(_rect_sdf(lx, ly, 7.2, 4.3), 1.0, .12) * plate
    spiracles = np.maximum(_ring(np.hypot(lx - 10.0, ly), 1.15, .52),
                            _ring(np.hypot(lx + 10.0, ly), 1.15, .52)) * plate
    bristles = _periodic_line(lx, 2.7, .18) * (np.abs(ly) > 6.0) * plate
    diffraction = _periodic_line(ly + .18 * lx, 2.5, .18) * windows
    pulse = _inside(_rect_sdf(np.mod(lx + 9.0, 6.0) - 3.0, ly, 1.6, 2.0), 1.0, .16) * windows
    cap = _inside(_rect_sdf(lx, ly - 6.6, 11.2, 1.3), 1.0, .16) * (((iy + ix) % 5) == 0)
    bevel = _edge(plate, 1)
    masks = dict(abdominal_plates=plate, cuticle_joints=joints, luminous_windows=windows,
                 paired_spiracles=spiracles, bristle_rows=bristles,
                 window_diffraction_ribs=diffraction, morse_pulse_bars=pulse,
                 terminal_caps_and_bevels=np.maximum(cap, bevel))
    own = dict(abdominal_plates=("A", 172, 96, 64), cuticle_joints=("N", 24, 242, 24),
               luminous_windows=("B", 46, 42, 252), paired_spiracles=("N", 38, 224, 70),
               bristle_rows=("A", 216, 188, 34), window_diffraction_ribs=("B", 88, 82, 238),
               morse_pulse_bars=("B", 122, 36, 248), terminal_caps_and_bevels=("A", 198, 136, 46))
    return _pack(masks, own, _norm(ly / 20.0 + .21 * (iy % 7) + .15 * pulse))


def _build_fmo_weevil_pit() -> _Grammar:
    """Unbroken weevil striae carrying pit files, leaf scales and setae."""
    x, y = _xy()
    strial_x = x + 1.15 * np.sin(y / 11.0) + .42 * np.sin(y / 3.7)
    lane = np.mod(strial_x, 7.0) - 3.5
    furrows = _line(lane, .58)
    raised_interstriae = _line(np.abs(lane) - 2.35, .46)
    pit_rows = _ring(np.hypot(lane, np.mod(y + .45 * strial_x, 6.0) - 3.0), .69, .31)
    leaf_x = np.mod(strial_x + 3.5, 7.0) - 3.5
    leaf_y = np.mod(y + .3 * strial_x, 8.0) - 4.0
    leaf_scales = _ring(_ellipse(leaf_x, leaf_y, 1.25, 2.2), .70, .17)
    leaf_midveins = _line(leaf_x + .18 * leaf_y, .34) * (_ellipse(leaf_x, leaf_y, 1.25, 2.2) < 1)
    ordered_setae = _line(leaf_x - .42 * leaf_y, .34) * (np.abs(leaf_y) < 2.4) * (np.abs(leaf_x) < 1.7)
    central_sutures = _periodic_line(x + .05 * y, 43.0, .050)
    wear_breaks = _periodic_line(y + .61 * x, 73.0, .050) * (np.abs(lane) < 1.0)
    masks = dict(continuous_strial_furrows=furrows, raised_interstrial_rails=raised_interstriae,
                 offset_pit_files=pit_rows, overlapping_leaf_scales=leaf_scales,
                 leaf_scale_midveins=leaf_midveins, ordered_backward_setae=ordered_setae,
                 sparse_elytral_sutures=central_sutures, diagonal_wear_breaks=wear_breaks)
    own = dict(continuous_strial_furrows=("N", 22, 242, 26), raised_interstrial_rails=("A", 234, 36, 38),
               offset_pit_files=("N", 38, 220, 70), overlapping_leaf_scales=("B", 62, 138, 234),
               leaf_scale_midveins=("B", 104, 186, 214), ordered_backward_setae=("A", 198, 88, 48),
               sparse_elytral_sutures=("A", 216, 162, 38), diagonal_wear_breaks=("N", 82, 204, 76))
    return _pack(masks, own, _norm(strial_x / 39.0 + .28 * np.sin(y / 13.0) + .18 * leaf_scales))


def _build_fmo_ground_beetle() -> _Grammar:
    """Cross-braced carabid armor with serrated rails and square punctures."""
    lx, ly, ix, iy = _local(30.0, 24.0, True)
    plate = _inside(_rect_sdf(lx, ly, 13.5, 10.2), 1.0, .10)
    costae_a = _periodic_line(lx + .42 * ly, 4.0, .18) * plate
    costae_b = _periodic_line(lx - .42 * ly, 4.0, .18) * plate
    serration = _periodic_line(ly, 2.7, .19) * costae_a
    punctures = _ring(np.maximum(np.abs(np.mod(lx + 15.0, 6.0) - 3.0),
                                 np.abs(np.mod(ly + 12.0, 6.0) - 3.0)), 1.2, .42) * plate
    carina = _line(lx, 1.0) * plate
    shoulder_hooks = _ring(_ellipse(lx - 9.0, ly + 7.0, 3.0, 2.0), .78, .13) * plate
    cross_ridges = _periodic_line(ly, 5.0, .17) * plate
    ventral_seams = _line(_rect_sdf(lx, ly, 13.5, 10.2) - .95, .06)
    wear = _inside(np.hypot(lx + 7.0, ly - 6.0), 1.8, .45) * plate * (((ix - iy) % 5) == 0)
    masks = dict(carabid_armor_plates=plate, crossed_costae=np.maximum(costae_a, costae_b),
                 serrated_interstriae=serration, square_punctures=punctures,
                 central_carinae=carina, shoulder_hooks=shoulder_hooks,
                 cross_ridges_and_ventral_seams=np.maximum(cross_ridges, ventral_seams), wear_gaps=wear)
    own = dict(carabid_armor_plates=("A", 164, 106, 58), crossed_costae=("A", 232, 38, 40),
               serrated_interstriae=("B", 82, 142, 226), square_punctures=("N", 26, 236, 52),
               central_carinae=("B", 54, 62, 250), shoulder_hooks=("A", 206, 174, 36),
               cross_ridges_and_ventral_seams=("N", 104, 202, 78), wear_gaps=("N", 18, 244, 22))
    return _pack(masks, own, _norm((ix % 8) / 8.0 + .27 * lx / 30.0 + .13 * serration))


def _build_fmo_scarab_horn() -> _Grammar:
    """Three-arm Clelie horn bouquets with collars, forks and pore beads."""
    lx, ly, ix, iy = _local(44.0, 44.0, True)
    rr = np.hypot(lx, ly); th = np.arctan2(ly, lx)
    arm_phase = np.sin(3.0 * th + rr * .34 + .3 * ((ix + iy) % 3))
    horn = _line(arm_phase, .31) * (rr > 4.0) * (rr < 18.5)
    growth = _periodic_line(rr + 2.2 * th, 3.0, .19) * horn
    collars = _ring(rr, 4.8, .72)
    fork_a = _line(np.sin(3.0 * th + rr * .34 + .62), .24) * (rr > 15.0) * (rr < 20.0)
    fork_b = _line(np.sin(3.0 * th + rr * .34 - .62), .24) * (rr > 15.0) * (rr < 20.0)
    struts = _periodic_line(th, .70, .18) * horn * (rr > 7.0)
    pores = _ring(np.hypot(np.mod(lx + 22.0, 7.0) - 3.5,
                             np.mod(ly + 22.0, 7.0) - 3.5), .75, .40) * horn
    abrasion = _line(ly - .24 * lx - 3.0, .72) * horn
    sockets = _inside(rr, 2.2, .55)
    masks = dict(tapered_horn_arms=horn, growth_ridges=growth, basal_collars=collars,
                 forked_tips=np.maximum(fork_a, fork_b), cross_struts=struts,
                 ordered_pore_beads=pores, abrasion_flats=abrasion, root_sockets=sockets)
    own = dict(tapered_horn_arms=("A", 182, 88, 64), growth_ridges=("B", 74, 92, 238),
               basal_collars=("A", 236, 34, 38), forked_tips=("B", 48, 54, 252),
               cross_struts=("N", 106, 204, 76), ordered_pore_beads=("N", 24, 232, 54),
               abrasion_flats=("A", 204, 182, 34), root_sockets=("B", 92, 68, 228))
    return _pack(masks, own, _norm(rr / 22.0 + .14 * th + .12 * growth))


def _build_fmo_ladybird_dome() -> _Grammar:
    """Flowing dome sutures carry asymmetric macula constellations and glints."""
    x, y = _xy()
    dome_phase = x + .28 * y + 4.4 * np.sin(y / 25.0)
    lane = np.mod(dome_phase, 37.0) - 18.5
    row = np.mod(y + 2.8 * np.sin(x / 29.0), 31.0) - 15.5
    sutures = _line(lane, .82)
    rim_arc_a = _line(row + .050 * lane * lane - 9.0, .56)
    rim_arc_b = _line(row - .038 * lane * lane + 8.0, .56)
    macula_a = _inside(np.hypot(lane - 6.0, row + 4.0), 2.0, .42)
    macula_b = _inside(np.hypot(lane + 7.0, row - 2.0), 1.55, .38)
    macula_c = _inside(_ellipse(lane - 10.5, row - 8.0, 1.2, 2.4), 1.0, .22)
    crown_glints = _line(row + .30 * lane + 5.0, .46) * (lane > 2.0) * (lane < 13.0)
    pore_collars = _ring(np.hypot(np.mod(dome_phase, 5.0) - 2.5,
                                  np.mod(y + .2 * x, 5.5) - 2.75), .52, .28) * (np.abs(lane) > 3.0)
    scalloped_heads = _periodic_line(x, 2.45, .18) * (np.abs(row + 12.3) < .72)
    masks = dict(flowing_central_sutures=sutures, upper_dome_rim_arcs=rim_arc_a,
                 lower_dome_rim_arcs=rim_arc_b, large_offset_maculae=macula_a,
                 small_counter_maculae=macula_b, elongated_head_maculae=macula_c,
                 comet_crown_glints=crown_glints, pore_collars_and_head_scallops=np.maximum(pore_collars, scalloped_heads))
    own = dict(flowing_central_sutures=("N", 22, 242, 24), upper_dome_rim_arcs=("A", 222, 42, 38),
               lower_dome_rim_arcs=("B", 72, 92, 240), large_offset_maculae=("N", 32, 216, 72),
               small_counter_maculae=("A", 188, 88, 52), elongated_head_maculae=("B", 106, 58, 244),
               comet_crown_glints=("B", 42, 32, 252), pore_collars_and_head_scallops=("A", 208, 174, 34))
    return _pack(masks, own, _norm(.31 * lane / 18.5 + .26 * row / 15.5 + .22 * crown_glints))


def _build_fmo_hummingbird_gorget() -> _Grammar:
    """Triangular gorget platelets fan by domain; no semicircular feather cards."""
    lx, ly, ix, iy = _local(11.0, 10.0, True)
    domain = ((ix + 2 * iy) % 6).astype(np.float32)
    angle = (domain - 2.5) * .16
    ca, sa = np.cos(angle), np.sin(angle)
    u, v = ca * lx - sa * ly, sa * lx + ca * ly
    shaft = _line(u, .48) * (v > -3.8) * (v < 4.4)
    arrow_wings = _line(np.abs(u) + .78 * v - 2.8, .42) * (v < 2.8) * (v > -3.2)
    tip_caps = _line(v - 2.9 + .30 * np.abs(u), .40) * (np.abs(u) < 2.7)
    barb_ridges = _periodic_line(v + .35 * u, 2.25, .18) * (np.abs(u) < 3.4)
    basal_pockets = _inside(_ellipse(u, v + 3.4, 1.2, .75), 1.0, .22)
    overlap_lips = _line(v + 1.4 - .18 * u * u, .42) * (np.abs(u) < 3.6)
    tip_notches = _inside(np.hypot(u, v - 3.4), .62, .25) * (((ix - iy) % 5) == 0)
    orientation_glints = _line(np.sin(u * .78 + v * .28 + domain), .16) * arrow_wings
    masks = dict(rotating_feather_shafts=shaft, triangular_arrow_wings=arrow_wings,
                 bevelled_platelet_tip_caps=tip_caps, internal_barb_ridges=barb_ridges,
                 dark_basal_pockets=basal_pockets, parabolic_overlap_lips=overlap_lips,
                 deterministic_tip_notches=tip_notches, orientation_glint_lines=orientation_glints)
    own = dict(rotating_feather_shafts=("N", 34, 232, 48), triangular_arrow_wings=("A", 242, 30, 24),
               bevelled_platelet_tip_caps=("A", 206, 54, 42), internal_barb_ridges=("B", 58, 92, 246),
               dark_basal_pockets=("N", 18, 244, 18), parabolic_overlap_lips=("B", 104, 72, 234),
               deterministic_tip_notches=("A", 188, 176, 34), orientation_glint_lines=("B", 42, 34, 252))
    return _pack(masks, own, _norm(domain / 6.0 + .28 * u / 5.5 + .16 * orientation_glints))


def _build_fmo_peacock_eye() -> _Grammar:
    """Fine teardrop ocelli grow from long stems and a many-ray barb corona."""
    lx, ly, ix, iy = _local(18.0, 22.0, True)
    ox, oy = lx + .7, ly - 3.0
    rr = _ellipse(ox, oy, 5.5, 6.8)
    th = np.arctan2(oy, ox)
    outer_teardrop = _ring(rr + .055 * oy, .88, .060)
    eccentric_pupil = _inside(_ellipse(ox + 1.1, oy + .3, 1.0, 1.65), 1.0, .22)
    iris_petals = _line(np.sin(th * 7.0 + rr * 5.4), .18) * (rr > .24) * (rr < .61)
    double_corona = np.maximum(_ring(rr, .61, .050), _ring(rr, .74, .050))
    radial_barbs = _periodic_line(th, .44, .17) * (rr > .72) * (rr < 1.04)
    eyelid = _line(oy + .12 * ox * ox - 2.4, .45) * (rr < .9)
    glint_bead = _inside(np.hypot(ox + 1.8, oy + 1.6), .55, .22)
    stem = _line(lx + .18 * ly, .58) * (ly > 2.0)
    masks = dict(teardrop_ocellus_rims=outer_teardrop, eccentric_dark_pupils=eccentric_pupil,
                 seven_petal_irises=iris_petals, double_gold_coronae=double_corona,
                 radial_tail_barbs=radial_barbs, broken_parabolic_eyelids=eyelid,
                 single_offset_glint_beads=glint_bead, long_feather_stems=stem)
    own = dict(teardrop_ocellus_rims=("A", 198, 60, 46), eccentric_dark_pupils=("N", 18, 244, 18),
               seven_petal_irises=("B", 52, 56, 252), double_gold_coronae=("A", 238, 32, 28),
               radial_tail_barbs=("B", 88, 132, 230), broken_parabolic_eyelids=("N", 46, 214, 72),
               single_offset_glint_beads=("B", 40, 30, 254), long_feather_stems=("A", 206, 174, 34))
    return _pack(masks, own, _norm(rr + .21 * th + .16 * stem))


def _build_fmo_starling_sheen() -> _Grammar:
    """Continuous hooked barbule textile with looping rachis lanes."""
    x, y = _xy()
    rachis_field = x + .32 * y + 2.4 * np.sin(y / 18.0)
    lane = np.mod(rachis_field, 17.0) - 8.5
    cross = np.mod(y - .18 * x, 8.0) - 4.0
    rachis = _line(lane, .66)
    barb_a = _line(cross - .58 * lane, .42) * (np.abs(lane) < 7.6)
    barb_b = _line(cross + .58 * lane, .42) * (np.abs(lane) < 7.6)
    hook_curls = _ring(np.hypot(np.mod(lane + 8.5, 4.2) - 2.1,
                                    np.mod(cross + 4.0, 4.0) - 2.0), .78, .30)
    cross_nodes = _inside(np.hypot(lane, cross), .58, .24)
    platelet_ladders = _periodic_line(y, 2.35, .20) * (np.abs(lane) < 1.1)
    overlap_pockets = _inside(_ellipse(lane - 5.2, cross + 1.8, 1.25, .72), 1.0, .20)
    tip_combs = _periodic_line(x, 2.25, .18) * (np.abs(lane - 7.2) < .72)
    missing_gaps = _periodic_line(x - .62 * y, 79.0, .045) * np.maximum(barb_a, barb_b)
    masks = dict(looping_rachis_lanes=rachis, forward_barbule_family=barb_a,
                 backward_barbule_family=barb_b, hooked_barbicel_curls=hook_curls,
                 barbule_crosslink_nodes=cross_nodes, platelet_ladders=platelet_ladders,
                 overlap_pockets_and_tip_combs=np.maximum(overlap_pockets, tip_combs), sparse_missing_barb_gaps=missing_gaps)
    own = dict(looping_rachis_lanes=("A", 232, 36, 34), forward_barbule_family=("B", 62, 108, 242),
               backward_barbule_family=("B", 104, 72, 236), hooked_barbicel_curls=("A", 196, 86, 48),
               barbule_crosslink_nodes=("N", 88, 202, 74), platelet_ladders=("A", 210, 162, 38),
               overlap_pockets_and_tip_combs=("B", 44, 44, 252), sparse_missing_barb_gaps=("N", 18, 244, 20))
    return _pack(masks, own, _norm(.34 * lane / 8.5 + .27 * cross / 4.0 + .22 * hook_curls))


def _build_fmo_magpie_wing() -> _Grammar:
    """Eight-fold vane parquet with white bars, black pockets and hook nodes."""
    x, y = _xy()
    p0 = np.sin((x + y) * np.pi / 7.0)
    p1 = np.sin((x - y) * np.pi / 9.0)
    p2 = np.sin((.4142 * x + y) * np.pi / 8.0)
    p3 = np.sin((x - .4142 * y) * np.pi / 10.0)
    vane = _line(p0 + .55 * p2, .24)
    white_bars = _line(p1 + .48 * p3, .22)
    black_pockets = _f32((np.abs(p0) - .72) / .18) * _f32((np.abs(p1) - .70) / .18)
    barbules = _line(np.sin(x / 2.5 + 1.2 * np.sin(y / 7.0)), .18) * vane
    nodes = _inside(np.hypot(np.mod(x, 18.0) - 9.0, np.mod(y, 18.0) - 9.0), 1.25, .42)
    rachis = _periodic_line(x + .35 * y, 13.0, .16)
    teeth = _periodic_line(x - y, 3.0, .18) * (white_bars > .2)
    seams = _line(p2 - p3, .22)
    masks = dict(eightfold_vane_parquet=vane, silver_white_bars=white_bars,
                 black_overlap_pockets=black_pockets, hooked_barbules=barbules,
                 diamond_cross_nodes=nodes, rachis_seams=rachis,
                 edge_teeth=teeth, interference_order_seams=seams)
    own = dict(eightfold_vane_parquet=("A", 168, 102, 58), silver_white_bars=("B", 54, 46, 250),
               black_overlap_pockets=("N", 18, 242, 20), hooked_barbules=("A", 228, 42, 40),
               diamond_cross_nodes=("B", 98, 66, 238), rachis_seams=("N", 92, 198, 78),
               edge_teeth=("A", 204, 176, 36), interference_order_seams=("B", 74, 104, 228))
    return _pack(masks, own, _norm(p0 + .73 * p1 + .41 * p2 + .18 * p3))


def _build_fmo_duck_speculum() -> _Grammar:
    """Rectangular speculum windows bounded by white bars and crossed barbules."""
    lx, ly, ix, iy = _local(38.0, 28.0, True)
    window = _inside(_rect_sdf(lx, ly, 16.5, 11.5), 1.0, .10)
    white_bars = np.maximum(_line(np.abs(ly) - 10.0, .82),
                            _line(np.abs(lx) - 15.0, .82)) * window
    barb_a = _periodic_line(lx + .42 * ly, 3.2, .18) * window
    barb_b = _periodic_line(lx - .42 * ly, 3.2, .18) * window
    rachis = _line(ly + .16 * lx, .95) * window
    hook_nodes = _ring(np.hypot(np.mod(lx + 19.0, 6.0) - 3.0,
                                  np.mod(ly + 14.0, 6.0) - 3.0), .8, .40) * window
    overlap_lip = _ring(_rect_sdf(lx, ly, 16.5, 11.5), .90, .055)
    pinions = _periodic_line(lx, 2.5, .19) * (ly > 9.0) * window
    hinge = _line(ly + 10.5 - .025 * lx * lx, .72) * window
    flash_order = _line(np.sin((lx + .28 * ly) / 2.1), .19) * window
    masks = dict(speculum_windows=window, white_border_bars=white_bars,
                 crossed_barbule_families=np.maximum(barb_a, barb_b), rachis_rails=rachis,
                 hook_nodes=hook_nodes, overlap_lips=overlap_lip,
                 edge_pinions_and_dark_hinges=np.maximum(pinions, hinge), moving_flash_order=flash_order)
    own = dict(speculum_windows=("B", 52, 58, 250), white_border_bars=("N", 112, 184, 94),
               crossed_barbule_families=("A", 224, 42, 40), rachis_rails=("A", 192, 76, 54),
               hook_nodes=("B", 98, 92, 232), overlap_lips=("N", 34, 226, 66),
               edge_pinions_and_dark_hinges=("N", 18, 242, 22), moving_flash_order=("B", 78, 38, 252))
    return _pack(masks, own, _norm(lx / 38.0 + .31 * ly / 28.0 + .14 * flash_order))


# ---------------------------------------------------------------------------
# W4 canvas-scale biological rebuild.
#
# W3 is intentionally left above as auditable rejected work: its builders had
# real named masks but too often arranged them as uniform rows/pave.  The W4
# builders below own one canvas-scale anatomical construction apiece.  Dense
# fine paths, teeth, pores, lamellae and barbules attach to that construction;
# no repeated local tile is used as the dominant silhouette.


def _w4_morpho_blue() -> _Grammar:
    """A single opening Morpho ridge fan with attached Christmas-tree shelves."""
    x, y = _xy(); t = np.linspace(0.0, 1.0, 240, dtype=np.float32)
    ridges_a, ridges_b, shelves, teeth, forks, pores = [], [], [], [], [], []
    for k in range(-16, 17):
        px = 8.0 + 510.0 * t
        py = 256.0 + k * (2.2 + 14.7 * t) + 18.0 * np.sin(np.pi * t + .31 * k)
        (ridges_a if k % 2 == 0 else ridges_b).append(np.c_[px, py])
        for j in range(8, 230, 11):
            qx, qy = float(px[j]), float(py[j]); span = 3.0 + 1.8 * ((j + k) % 3)
            shelves.append([(qx - span, qy - 1.8), (qx, qy), (qx + span, qy + 1.8)])
        for j in range(12, 230, 17):
            qx, qy = float(px[j]), float(py[j])
            teeth.append([(qx - 2.2, qy - 2.0), (qx, qy), (qx + 2.2, qy - 2.0)])
        if k in {-12, -5, 4, 11}:
            forks.append(np.c_[px[150:], py[150:] + (k % 3 - 1) * 7.0 * (t[150:] - t[150])])
        if k % 4 == 1:
            for j in range(20, 225, 29): pores.append((float(px[j] + 3.2), float(py[j]), 1.2))
    bridges = []
    for q in (.18, .36, .57, .79):
        pts = []
        for k in range(-16, 17):
            px = 8.0 + 510.0 * q
            py = 256.0 + k * (2.2 + 14.7 * q) + 18.0 * np.sin(np.pi * q + .31 * k)
            pts.append((px, py))
        bridges.append(pts)
    lip = [[(18, 250), (92, 238), (176, 211), (278, 167), (394, 104), (510, 22)]]
    masks = dict(even_nanoridge_fan=_paths(ridges_a, 2), odd_nanoridge_fan=_paths(ridges_b, 2),
                 attached_lamellar_shelves=_paths(shelves, 1), christmas_tree_teeth=_paths(teeth, 1),
                 ordered_perforation_pores=_circles(pores, 1), cross_ridge_bridge_arcs=_paths(bridges, 1),
                 terminal_fork_dislocations=_paths(forks, 2), leading_overlap_lip=_paths(lip, 2))
    own = dict(even_nanoridge_fan=("A", 242, 30, 22), odd_nanoridge_fan=("B", 46, 72, 248),
               attached_lamellar_shelves=("A", 206, 54, 38), christmas_tree_teeth=("B", 98, 44, 252),
               ordered_perforation_pores=("N", 24, 238, 56), cross_ridge_bridge_arcs=("B", 72, 158, 222),
               terminal_fork_dislocations=("N", 118, 198, 82), leading_overlap_lip=("A", 186, 104, 48))
    tone = np.arctan2(y - 256.0, x + 26.0) + .0037 * np.hypot(x + 26.0, y - 256.0)
    return _pack(masks, own, _norm(tone))


def _w4_sunset_moth() -> _Grammar:
    """One scalloped moth wing radiating from a basal hinge."""
    x, y = _xy(); t = np.linspace(0.0, 1.0, 180, dtype=np.float32)
    primary, upper, lower, rakes = [], [], [], []
    endpoints = [(94, 22), (165, 10), (242, 22), (318, 54), (390, 104),
                 (454, 170), (492, 250), (505, 334), (486, 421), (440, 492)]
    veins = []
    for i, (ex, ey) in enumerate(endpoints):
        px = 22.0 + (ex - 22.0) * t + 18.0 * np.sin(np.pi * t) * np.sin(.57 * i)
        py = 438.0 + (ey - 438.0) * t - 15.0 * np.sin(np.pi * t) * np.cos(.43 * i)
        veins.append(np.c_[px, py]); primary.append(np.c_[px, py])
        for j in range(25, 165, 18):
            qx, qy = float(px[j]), float(py[j]); side = -1.0 if (i + j) % 2 else 1.0
            branch = [(qx, qy), (qx + 8.0, qy + side * 7.0), (qx + 17.0, qy + side * 10.0)]
            (upper if side < 0 else lower).append(branch)
        for j in range(18, 168, 9):
            qx, qy = float(px[j]), float(py[j]); rakes.append([(qx - 3, qy + 2), (qx + 4, qy - 2)])
    cross = []
    for q in (.22, .39, .58, .76, .90):
        cross.append([(float(v[int(q * 179), 0]), float(v[int(q * 179), 1])) for v in veins])
    rim_t = np.linspace(-.08, 1.05, 220)
    rim = np.c_[260 + 252 * np.cos(1.43 * np.pi * rim_t),
                270 - 248 * np.sin(1.43 * np.pi * rim_t) + 12 * np.sin(13 * np.pi * rim_t)]
    crescents = [(402, 152, 16), (466, 247, 12), (457, 365, 10)]
    eyes = [(414, 154, 4), (469, 248, 3), (459, 366, 3)]
    masks = dict(radial_costal_veins=_paths(primary, 2), upper_vein_forks=_paths(upper, 1),
                 lower_vein_forks=_paths(lower, 1), curved_cross_veins=_paths(cross, 1),
                 attached_scale_rakes=_paths(rakes, 1), scalloped_outer_fringe=_paths([rim], 2),
                 sunset_crescent_bands=_circles(crescents, 2), false_eye_wedges=_circles(eyes, -1))
    own = dict(radial_costal_veins=("A", 238, 34, 30), upper_vein_forks=("A", 198, 56, 42),
               lower_vein_forks=("B", 62, 118, 236), curved_cross_veins=("N", 108, 76, 96),
               attached_scale_rakes=("B", 88, 164, 216), scalloped_outer_fringe=("N", 22, 240, 54),
               sunset_crescent_bands=("B", 42, 46, 252), false_eye_wedges=("A", 218, 186, 30))
    return _pack(masks, own, _norm(np.arctan2(y - 438, x - 22) + .0022 * np.hypot(x - 22, y - 438)))


def _w4_monarch_vein() -> _Grammar:
    """A single polygonal Monarch wing-cell graph with hierarchical vein widths."""
    x, y = _xy(); root = np.array([38.0, 454.0]); t = np.linspace(0, 1, 150, dtype=np.float32)
    tips = np.asarray([(58, 52), (128, 20), (205, 16), (286, 38), (360, 82),
                       (426, 146), (476, 226), (492, 320), (462, 420)], np.float32)
    primaries = []
    for i, tip in enumerate(tips):
        px = root[0] + (tip[0] - root[0]) * t + (i - 4) * 3.2 * np.sin(np.pi * t)
        py = root[1] + (tip[1] - root[1]) * t - 22 * np.sin(np.pi * t) * np.sin(.44 * i)
        primaries.append(np.c_[px, py])
    cross, tertiary, bricks = [], [], []
    levels = (.18, .31, .47, .64, .79, .91)
    for li, q in enumerate(levels):
        pts = []
        j = int(q * (len(t) - 1))
        for i, vein in enumerate(primaries):
            px, py = vein[j]; pts.append((float(px), float(py)))
            if i < len(primaries) - 1:
                nx, ny = primaries[i + 1][j]
                mx, my = (px + nx) / 2, (py + ny) / 2
                tertiary.append([(px, py), (mx + 4 * np.sin(i + li), my), (nx, ny)])
                for s in (.30, .55, .78):
                    bx, by = px * (1 - s) + nx * s, py * (1 - s) + ny * s
                    bricks.append([(bx - 3, by + 1.5), (bx + 3, by - 1.5)])
        cross.append(pts)
    spots = [(93, 47, 4), (151, 28, 3), (228, 30, 4), (310, 58, 3),
             (383, 106, 4), (442, 172, 3), (477, 253, 4), (477, 344, 3)]
    nodes = [(float(v[55, 0]), float(v[55, 1]), 2.0) for v in primaries]
    margin = [[(58, 52), (128, 20), (205, 16), (286, 38), (360, 82), (426, 146),
               (476, 226), (492, 320), (462, 420), (38, 454)]]
    masks = dict(murray_primary_veins=_paths(primaries, 3), polygonal_cross_veins=_paths(cross, 2),
                 tertiary_cell_forks=_paths(tertiary, 1), orange_scale_bricks=_paths(bricks, 1),
                 white_margin_spots=_circles(spots, 2), cross_vein_nodes=_circles(nodes, 1),
                 black_outer_margin=_paths(margin, 3), fine_margin_fringe=_paths([margin[0][:-1]], 1))
    own = dict(murray_primary_veins=("N", 24, 242, 24), polygonal_cross_veins=("A", 226, 42, 34),
               tertiary_cell_forks=("B", 64, 76, 246), orange_scale_bricks=("A", 184, 136, 50),
               white_margin_spots=("N", 88, 174, 118), cross_vein_nodes=("B", 112, 52, 242),
               black_outer_margin=("A", 204, 62, 40), fine_margin_fringe=("B", 46, 160, 220))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .0018 * np.hypot(x - root[0], y - root[1])))


def _w4_atlas_wing() -> _Grammar:
    """Seven interlocking snake-head costal hooks, each a continuous anatomy path."""
    x, y = _xy(); tt = np.linspace(0, 1, 220, dtype=np.float32)
    spines, jaws, brows, scales, crossveins, antennae = [], [], [], [], [], []
    bases = [34, 91, 158, 236, 329, 418, 486]
    for i, base in enumerate(bases):
        px = 10 + 502 * tt
        py = base + (26 + 4 * i) * np.sin(2.2 * np.pi * tt + .63 * i) + 8 * np.sin(5.1 * np.pi * tt)
        spines.append(np.c_[px, py])
        for j in range(22, 205, 19):
            qx, qy = float(px[j]), float(py[j]); side = -1 if (i + j) % 2 else 1
            jaws.append([(qx, qy), (qx + 8, qy + side * 7), (qx + 17, qy + side * 4)])
            brows.append([(qx - 5, qy - 5), (qx + 1, qy - 8), (qx + 8, qy - 5)])
        for j in range(14, 210, 10):
            qx, qy = float(px[j]), float(py[j]); scales.append([(qx - 3, qy - 2), (qx + 3, qy + 2)])
        for j in range(35, 195, 31):
            qx, qy = float(px[j]), float(py[j]); crossveins.append([(qx, qy - 7), (qx, qy + 7)])
        antennae.append([(px[-35], py[-35]), (px[-18], py[-18] - 13), (px[-1], py[-1] - 5)])
    pupils = [(82, bases[0] + 18, 3), (221, bases[2] - 18, 3), (352, bases[4] + 15, 3), (471, bases[6] - 10, 3)]
    notches = [(128, 78, 5), (286, 250, 5), (438, 421, 5)]
    masks = dict(serpentine_costal_spines=_paths(spines, 2), articulated_jaw_forks=_paths(jaws, 2),
                 false_eye_brows=_paths(brows, 1), sparse_false_pupils=_circles(pupils, -1),
                 attached_neck_scale_rakes=_paths(scales, 1), membrane_cross_veins=_paths(crossveins, 1),
                 terminal_antenna_hooks=_paths(antennae, 2), bite_notch_crescents=_circles(notches, 2))
    own = dict(serpentine_costal_spines=("A", 240, 32, 28), articulated_jaw_forks=("B", 66, 80, 244),
               false_eye_brows=("A", 202, 56, 40), sparse_false_pupils=("N", 18, 244, 18),
               attached_neck_scale_rakes=("B", 102, 152, 218), membrane_cross_veins=("N", 112, 188, 86),
               terminal_antenna_hooks=("B", 46, 50, 252), bite_notch_crescents=("A", 194, 176, 34))
    return _pack(masks, own, _norm(.38 * np.sin(x / 37.0 + y / 91.0) + y / 512.0))


def _w4_luna_dust() -> _Grammar:
    """One whole Chladni plate with authored craters attached to its nodes."""
    x, y = _xy()
    ch = (np.sin(np.pi * x / 83.0) * np.sin(np.pi * y / 119.0)
          - .71 * np.sin(np.pi * (x + .19 * y) / 137.0) * np.sin(np.pi * (y - .13 * x) / 71.0))
    nodes = _line(ch, .075)
    inner_nodes = _line(ch - .42, .075); outer_nodes = _line(ch + .42, .075)
    beads = nodes * _periodic_line(x + .37 * y, 4.1, .19)
    crater_specs = [(72, 82, 11), (181, 149, 8), (326, 83, 14), (439, 174, 9),
                    (113, 328, 13), (267, 276, 10), (409, 398, 15), (221, 445, 7)]
    craters = _circles(crater_specs, 2)
    ejecta_paths = []
    for cx, cy, r0 in crater_specs[::2]:
        a = np.linspace(-.7, .9, 70); ejecta_paths.append(np.c_[cx + (r0 + 7) * np.cos(a), cy + (r0 + 4) * np.sin(a)])
    spokes = []
    for cx, cy, r0 in crater_specs[1::2]:
        for a in (.2, 1.4, 2.7, 4.1): spokes.append([(cx, cy), (cx + (r0 + 12) * np.cos(a), cy + (r0 + 12) * np.sin(a))])
    flakes = _circles([(48, 227, 2), (156, 252, 2), (298, 183, 2), (372, 308, 2), (477, 276, 2)], -1)
    masks = dict(primary_chladni_nodes=nodes, positive_order_nodes=inner_nodes,
                 negative_order_nodes=outer_nodes, compressed_dust_bead_chains=beads,
                 authored_crater_cups=craters, crescent_ejecta_arcs=_paths(ejecta_paths, 2),
                 radial_crater_spokes=_paths(spokes, 1), isolated_moon_scale_flakes=flakes)
    own = dict(primary_chladni_nodes=("A", 222, 54, 40), positive_order_nodes=("B", 58, 86, 246),
               negative_order_nodes=("B", 106, 152, 224), compressed_dust_bead_chains=("A", 246, 30, 22),
               authored_crater_cups=("N", 32, 232, 68), crescent_ejecta_arcs=("B", 122, 68, 236),
               radial_crater_spokes=("N", 82, 204, 76), isolated_moon_scale_flakes=("A", 190, 162, 36))
    return _pack(masks, own, _norm(ch + .18 * np.hypot(x - 260, y - 244) / 360.0))


def _w4_swallowtail() -> _Grammar:
    """One bifurcating swallowtail wing opens from a shared thoracic root."""
    x, y = _xy(); t = np.linspace(0, 1, 190, dtype=np.float32); root = (44.0, 266.0)
    shafts, forks_a, forks_b, prongs, rakes = [], [], [], [], []
    angles = np.linspace(-1.18, 1.12, 17)
    for i, ang in enumerate(angles):
        length = 440 - 7 * abs(i - 8)
        px = root[0] + length * t * np.cos(ang * .52) + 18 * np.sin(np.pi * t) * np.sin(ang * 2)
        py = root[1] + length * t * np.sin(ang * .52) + 15 * np.sin(np.pi * t) * np.cos(ang * 3)
        shafts.append(np.c_[px, py])
        j = 112 + (i % 4) * 7; qx, qy = float(px[j]), float(py[j])
        forks_a.append([(qx, qy), (qx + 45, qy - 18 - 2 * i), (qx + 86, qy - 30 - 2 * i)])
        forks_b.append([(qx, qy), (qx + 42, qy + 15 + 2 * i), (qx + 82, qy + 26 + 2 * i)])
        if i in {1, 2, 14, 15}: prongs.append(np.c_[px[120:], py[120:] + (i - 8) * 2.8 * t[120:]])
        for j2 in range(20, 176, 10):
            rakes.append([(float(px[j2] - 3), float(py[j2] + 2)), (float(px[j2] + 4), float(py[j2] - 2))])
    hinge_arcs = []
    for r0 in (18, 31, 46):
        a = np.linspace(-1.25, 1.25, 90); hinge_arcs.append(np.c_[root[0] + r0 * np.cos(a), root[1] + r0 * np.sin(a)])
    windows = [(294, 153, 6), (369, 190, 5), (398, 324, 6), (310, 390, 5)]
    eyes = [(432, 113, 4), (457, 393, 4)]
    masks = dict(radial_vane_shafts=_paths(shafts, 2), upper_vein_bifurcations=_paths(forks_a, 1),
                 lower_vein_bifurcations=_paths(forks_b, 1), elongated_tail_prongs=_paths(prongs, 3),
                 attached_directional_scale_rakes=_paths(rakes, 1), articulated_basal_hinges=_paths(hinge_arcs, 2),
                 flash_window_collars=_circles(windows, 2), marginal_eye_cups=_circles(eyes, 2))
    own = dict(radial_vane_shafts=("N", 30, 234, 30), upper_vein_bifurcations=("A", 232, 36, 32),
               lower_vein_bifurcations=("A", 192, 64, 46), elongated_tail_prongs=("B", 48, 56, 252),
               attached_directional_scale_rakes=("B", 84, 154, 220), articulated_basal_hinges=("A", 206, 178, 34),
               flash_window_collars=("B", 112, 86, 238), marginal_eye_cups=("N", 20, 242, 58))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .0025 * np.hypot(x - root[0], y - root[1])))


def _w4_ulysses_flash() -> _Grammar:
    """Seven non-repeating diffraction domains separated by sweeping faults."""
    x, y = _xy()
    b1 = y - (86 + .16 * x + 24 * np.sin(x / 73.0))
    b2 = y - (207 - .10 * x + 31 * np.sin((x + 40) / 91.0))
    b3 = y - (339 + .08 * x - 27 * np.sin(x / 61.0))
    d0, d1, d2, d3 = b1 < 0, (b1 >= 0) & (b2 < 0), (b2 >= 0) & (b3 < 0), b3 >= 0
    walls = np.maximum.reduce([_line(b1, 1.8), _line(b2, 1.8), _line(b3, 1.8)])
    comb_a = _periodic_line(x + .18 * y + 2 * np.sin(y / 37), 5.1, .16) * d0
    comb_b = _periodic_line(y - .43 * x + 3 * np.sin(x / 49), 4.4, .17) * d1
    comb_c = _periodic_line(x + .67 * y + 4 * np.sin(y / 53), 5.8, .16) * d2
    comb_d = _periodic_line(y + .12 * x + 3 * np.sin(x / 31), 4.7, .17) * d3
    crossbars = (_periodic_line(y, 13.0, .12) * d0 + _periodic_line(x, 17.0, .10) * d2)
    joints = _circles([(18, 90, 3), (131, 129, 3), (252, 117, 3), (379, 144, 3),
                       (78, 217, 3), (312, 292, 3), (453, 349, 3)], 2)
    ticks = _periodic_line(x - y, 3.1, .18) * walls
    fronts = np.maximum(_line(np.sin(x / 17.0 + y / 29.0), .14),
                        _line(np.cos(x / 31.0 - y / 19.0), .14) * d3)
    masks = dict(sweeping_domain_faults=walls, domain_a_diffraction_combs=comb_a,
                 domain_b_diffraction_combs=comb_b, domain_c_diffraction_combs=comb_c,
                 domain_d_diffraction_combs=comb_d, fault_crossbars_and_joints=np.maximum(crossbars, joints),
                 diffraction_order_ticks=ticks, migrating_order_fronts=fronts)
    own = dict(sweeping_domain_faults=("N", 102, 194, 82), domain_a_diffraction_combs=("A", 242, 30, 24),
               domain_b_diffraction_combs=("B", 46, 66, 252), domain_c_diffraction_combs=("A", 196, 72, 46),
               domain_d_diffraction_combs=("B", 104, 112, 236), fault_crossbars_and_joints=("N", 34, 230, 56),
               diffraction_order_ticks=("A", 210, 166, 34), migrating_order_fronts=("B", 72, 44, 248))
    return _pack(masks, own, _norm(.31 * np.sin(x / 73.0) + .37 * np.cos(y / 91.0) + .22 * walls))


def _w4_owl_eye() -> _Grammar:
    """One paired owl face assembled from fine concentric feather anatomy."""
    x, y = _xy(); centers = ((145.0, 263.0), (367.0, 251.0))
    discs, irises, pupils, radial, brows, glints = [], [], [], [], [], []
    for ci, (cx, cy) in enumerate(centers):
        for r0 in range(30, 155, 8):
            a = np.linspace(0, 2 * np.pi, 180); wobble = 2.5 * np.sin(5 * a + ci)
            discs.append(np.c_[cx + (r0 + wobble) * np.cos(a), cy + .88 * (r0 + wobble) * np.sin(a)])
        for r0 in (17, 24):
            a = np.linspace(0, 2 * np.pi, 100); irises.append(np.c_[cx + r0 * np.cos(a), cy + 1.1 * r0 * np.sin(a)])
        pupils.append((cx + (4 if ci else -4), cy + 2, 7))
        for a0 in np.linspace(0, 2 * np.pi, 28, endpoint=False):
            radial.append([(cx + 27 * np.cos(a0), cy + 23 * np.sin(a0)),
                           (cx + 146 * np.cos(a0), cy + 128 * np.sin(a0))])
        brows.append([(cx - 108, cy - 54), (cx - 20, cy - 104), (cx + 91, cy - 55)])
        glints.append((cx - 4, cy - 5, 2))
    beak = [[(256, 188), (229, 278), (256, 353), (285, 277), (256, 188)]]
    ear_tufts = [[(42, 187), (91, 20), (185, 132)], [(327, 127), (428, 18), (474, 188)]]
    masks = dict(concentric_facial_feather_discs=_paths(discs, 1), double_iris_rings=_paths(irises, 2),
                 paired_pupil_cups=_circles(pupils, -1), radial_facial_feather_combs=_paths(radial, 1),
                 horned_brow_chevrons=_paths(brows, 3), central_beak_chevrons=_paths(beak, 2),
                 offset_square_glints=_circles(glints, -1), pointed_ear_tufts=_paths(ear_tufts, 3))
    own = dict(concentric_facial_feather_discs=("B", 82, 152, 222), double_iris_rings=("A", 232, 38, 34),
               paired_pupil_cups=("N", 18, 244, 18), radial_facial_feather_combs=("B", 112, 88, 238),
               horned_brow_chevrons=("A", 194, 72, 48), central_beak_chevrons=("A", 214, 164, 34),
               offset_square_glints=("N", 108, 188, 112), pointed_ear_tufts=("B", 48, 48, 252))
    tone = .55 * np.hypot(x - centers[0][0], (y - centers[0][1]) / .88) + .45 * np.hypot(x - centers[1][0], (y - centers[1][1]) / .88)
    return _pack(masks, own, _norm(tone))


def _w4_glasswing() -> _Grammar:
    """A single transparent wing membrane triangulated from one basal node."""
    x, y = _xy(); root = (22.0, 421.0); t = np.linspace(0, 1, 160, dtype=np.float32)
    tips = [(58, 40), (132, 18), (214, 25), (301, 55), (382, 108), (448, 180), (489, 269), (472, 370)]
    primary = []
    for i, (ex, ey) in enumerate(tips):
        px = root[0] + (ex - root[0]) * t + 10 * np.sin(np.pi * t) * np.sin(i)
        py = root[1] + (ey - root[1]) * t - 12 * np.sin(np.pi * t) * np.cos(.7 * i)
        primary.append(np.c_[px, py])
    trusses, caustics, trichia = [], [], []
    for q in (.18, .34, .52, .69, .84):
        j = int(q * 159); pts = [(float(v[j, 0]), float(v[j, 1])) for v in primary]; trusses.append(pts)
        if q in (.34, .69): caustics.append([(px, py + 5 * np.sin(px / 13.0)) for px, py in pts])
    for i, v in enumerate(primary):
        for j in range(15, 150, 9):
            px, py = v[j]; trichia.append([(px - 2, py + 2), (px + 3, py - 2)])
    border = [[*tips, root]]
    nodes = [(float(v[52, 0]), float(v[52, 1]), 3) for v in primary]
    stress = [[(96, 344), (177, 280), (228, 205)], [(292, 291), (356, 221), (416, 153)]]
    capillaries = [(142, 166, 18), (327, 128, 14), (398, 285, 16)]
    masks = dict(primary_membrane_veins=_paths(primary, 3), triangular_secondary_trusses=_paths(trusses, 2),
                 newton_caustic_wrinkles=_paths(caustics, 1), sparse_border_scales=_paths(border, 3),
                 attached_microtrichia_combs=_paths(trichia, 1), node_pads=_circles(nodes, 2),
                 stress_notch_paths=_paths(stress, 2), capillary_loops=_circles(capillaries, 2))
    own = dict(primary_membrane_veins=("A", 228, 38, 38), triangular_secondary_trusses=("A", 188, 62, 56),
               newton_caustic_wrinkles=("B", 72, 112, 250), sparse_border_scales=("N", 104, 202, 78),
               attached_microtrichia_combs=("N", 26, 238, 44), node_pads=("A", 242, 154, 24),
               stress_notch_paths=("B", 104, 72, 234), capillary_loops=("B", 48, 52, 252))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .002 * np.hypot(x - root[0], y - root[1])))


def _w4_emperor_scale() -> _Grammar:
    """One imperial crown fan with ray-attached ribs, eyes and terminal teeth."""
    x, y = _xy(); root = (256.0, 486.0); t = np.linspace(0, 1, 210, dtype=np.float32)
    rays, crossbars, eyes, teeth, pores = [], [], [], [], []
    angles = np.linspace(-2.58, -.56, 31)
    for i, a in enumerate(angles):
        length = 430 + 42 * np.cos(i * .71)
        px = root[0] + length * t * np.cos(a) + 15 * np.sin(np.pi * t) * np.sin(i * .3)
        py = root[1] + length * t * np.sin(a) - 11 * np.sin(np.pi * t) * np.cos(i * .23)
        rays.append(np.c_[px, py])
        for j in range(25, 195, 18):
            qx, qy = float(px[j]), float(py[j]); crossbars.append([(qx - 3, qy - 2), (qx + 3, qy + 2)])
        if i % 4 == 1: eyes.append((float(px[142]), float(py[142]), 3))
        teeth.append([(float(px[-8] - 3), float(py[-8] + 2)), (float(px[-1]), float(py[-1])), (float(px[-8] + 3), float(py[-8] + 2))])
        if i % 5 == 2: pores.append((float(px[95]), float(py[95]), 1.5))
    arcs = []
    for r0 in (34, 68, 112, 164, 226, 302, 378):
        a = np.linspace(-2.58, -.56, 180); arcs.append(np.c_[root[0] + r0 * np.cos(a), root[1] + r0 * np.sin(a)])
    hinges = _circles([(256, 486, 15), (256, 486, 28)], 2)
    missing = [rays[i][145:] for i in (4, 13, 24)]
    masks = dict(open_crown_rays=_paths(rays, 2), ray_crossbar_ladders=_paths(crossbars, 1),
                 concentric_overlap_lips=_paths(arcs, 2), circular_basal_hinges=hinges,
                 crown_eye_cups=_circles(eyes, 2), terminal_serration_teeth=_paths(teeth, 1),
                 ray_attached_pores=_circles(pores, 1), missing_ray_dislocations=_paths(missing, 3))
    own = dict(open_crown_rays=("A", 234, 34, 32), ray_crossbar_ladders=("B", 62, 92, 244),
               concentric_overlap_lips=("A", 190, 76, 48), circular_basal_hinges=("N", 28, 234, 40),
               crown_eye_cups=("B", 42, 48, 252), terminal_serration_teeth=("A", 208, 174, 32),
               ray_attached_pores=("N", 96, 204, 76), missing_ray_dislocations=("B", 108, 66, 238))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .0026 * np.hypot(x - root[0], y - root[1])))


def _w4_jewel_scarab() -> _Grammar:
    """One paired jewel-scarab carapace with longitudinal anatomical ownership."""
    x, y = _xy(); yy = np.linspace(22, 500, 220, dtype=np.float32)
    suture = [[(256 + 4 * np.sin(v / 43), v) for v in yy]]
    outlines, costae, lips, punctures = [], [], [], []
    a = np.linspace(-1.52, 1.52, 220)
    outlines.append(np.c_[256 - 218 * np.cos(a), 260 + 238 * np.sin(a)])
    outlines.append(np.c_[256 + 218 * np.cos(a), 260 + 238 * np.sin(a)])
    offsets = [-188, -154, -119, -82, -43, 43, 82, 119, 154, 188]
    for i, off in enumerate(offsets):
        px = 256 + off * (1 - .000008 * (yy - 260) ** 2) + 7 * np.sin(yy / (31 + i))
        costae.append(np.c_[px, yy])
        lips.append(np.c_[px + np.sign(off) * 3.2, yy])
        for j in range(8 + i % 5, 210, 13 + i % 3): punctures.append((float(px[j]), float(yy[j]), 1.5))
    tri = [[(222, 62), (256, 20), (291, 64), (256, 96), (222, 62)]]
    files = []
    for v in range(104, 474, 9): files.append([(250, v), (262, v)])
    micro = _line(np.sin(x / 3.1) + np.sin((.51 * x + .86 * y) / 3.1) + np.sin((.51 * x - .86 * y) / 3.1), .18)
    schiller = _line(np.sin((y + .39 * x) / 4.6) + .28 * np.sin(x / 17.0), .15)
    masks = dict(paired_elytral_outlines=_paths(outlines, 3), central_suture=_paths(suture, 3),
                 longitudinal_costae=_paths(costae, 2), raised_costa_lips=_paths(lips, 1),
                 ordered_puncture_files=_circles(punctures, 1), scutellum_diamond=_paths(tri, 2),
                 stridulatory_suture_file=_paths(files, 1), attached_hex_microcells=np.minimum(micro, _halo(_paths(costae, 3), 3.0)))
    own = dict(paired_elytral_outlines=("A", 176, 94, 62), central_suture=("N", 24, 242, 24),
               longitudinal_costae=("A", 238, 34, 30), raised_costa_lips=("B", 62, 72, 250),
               ordered_puncture_files=("N", 38, 220, 72), scutellum_diamond=("B", 108, 48, 244),
               stridulatory_suture_file=("A", 204, 164, 38), attached_hex_microcells=("B", 48, 138, 224))
    return _pack(masks, own, _norm(.36 * np.sin((x - 256) / 71.0) + y / 512.0 + .19 * schiller))


def _w4_tiger_beetle() -> _Grammar:
    """A canvas-spanning maculation tree laid across curved elytral corrugations."""
    x, y = _xy(); t = np.linspace(0, 1, 170, dtype=np.float32)
    trunk = np.c_[22 + 486 * t, 264 + 74 * np.sin(2.2 * np.pi * t) + 29 * np.sin(5.1 * np.pi * t)]
    forks_a, forks_b, lips, corrugations = [], [], [], []
    for j in (22, 43, 66, 91, 116, 140):
        qx, qy = trunk[j]; span = 82 + (j % 4) * 13
        forks_a.append([(qx, qy), (qx + span * .45, qy - 48), (qx + span, qy - 82 - j % 23)])
        forks_b.append([(qx, qy), (qx + span * .42, qy + 43), (qx + span, qy + 76 + j % 17)])
        lips.append([(qx, qy - 4), (qx + span * .45, qy - 52), (qx + span, qy - 86 - j % 23)])
    for k in range(-18, 19):
        px = np.linspace(0, 512, 240); py = 256 + k * 13 + 18 * np.sin(px / 47.0 + .29 * k)
        corrugations.append(np.c_[px, py])
    punctures = []
    for k, path in enumerate(corrugations[::3]):
        for j in range(10 + k, 230, 19): punctures.append((float(path[j, 0]), float(path[j, 1]), 1.4))
    suture = [[(256 + 11 * np.sin(v / 83), v) for v in np.linspace(8, 504, 180)]]
    spines = [[(20 + 18 * i, 26 + 3 * (i % 4)), (24 + 18 * i, 17)] for i in range(27)]
    calluses = [(85, 210, 9), (212, 346, 7), (371, 179, 10), (458, 319, 8)]
    masks = dict(branching_maculation_trunk=_paths([trunk], 4), upper_cream_maculation_forks=_paths(forks_a, 3),
                 lower_cream_maculation_forks=_paths(forks_b, 3), double_ribbon_lips=_paths(lips, 1),
                 curved_elytral_corrugations=_paths(corrugations, 1), attached_puncture_files=_circles(punctures, 1),
                 central_suture_and_edge_spines=np.maximum(_paths(suture, 2), _paths(spines, 1)),
                 crystalline_shoulder_calluses=_circles(calluses, 2))
    own = dict(branching_maculation_trunk=("B", 44, 54, 252), upper_cream_maculation_forks=("B", 84, 86, 242),
               lower_cream_maculation_forks=("A", 216, 48, 38), double_ribbon_lips=("A", 184, 84, 50),
               curved_elytral_corrugations=("N", 28, 236, 34), attached_puncture_files=("N", 44, 216, 72),
               central_suture_and_edge_spines=("A", 198, 178, 32), crystalline_shoulder_calluses=("B", 112, 142, 224))
    return _pack(masks, own, _norm(.35 * np.sin(x / 71.0) + .32 * np.sin(y / 83.0) + .24 * _paths([trunk], 5)))


def _w4_stag_carapace() -> _Grammar:
    """A single antler-channel bouquet grows through irregular shield armor."""
    x, y = _xy(); root = (256.0, 492.0); t = np.linspace(0, 1, 180, dtype=np.float32)
    horns, branches, growth, pores = [], [], [], []
    angles = [-2.74, -2.55, -2.33, -2.09, -1.84, -1.58, -1.33, -1.07, -.82, -.60, -.43]
    for i, a in enumerate(angles):
        length = 390 + 35 * np.sin(i * 1.7)
        px = root[0] + length * t * np.cos(a) + 26 * np.sin(np.pi * t) * np.sin(i)
        py = root[1] + length * t * np.sin(a) - 18 * np.sin(np.pi * t) * np.cos(i)
        horns.append(np.c_[px, py])
        for j in (52, 87, 121, 149):
            qx, qy = float(px[j]), float(py[j]); side = -1 if (i + j) % 2 else 1
            branches.append([(qx, qy), (qx + side * 27, qy - 30), (qx + side * 48, qy - 55)])
        for j in range(18, 165, 13):
            qx, qy = float(px[j]), float(py[j]); growth.append([(qx - 3, qy - 2), (qx + 3, qy + 2)])
        if i % 2 == 0:
            for j in (35, 72, 110, 145): pores.append((float(px[j]), float(py[j]), 1.5))
    plate_seams = [[(8, 58), (76, 91), (143, 64), (218, 104), (294, 68), (373, 99), (505, 53)],
                   [(20, 126), (112, 76), (206, 112), (274, 58), (361, 91), (490, 44)],
                   [(7, 191), (79, 161), (157, 198), (235, 153), (324, 187), (410, 142), (509, 173)],
                   [(11, 258), (104, 216), (188, 249), (268, 197), (352, 228), (505, 183)],
                   [(8, 323), (91, 292), (177, 329), (259, 286), (350, 318), (438, 276), (510, 303)],
                   [(18, 387), (132, 340), (218, 379), (311, 329), (411, 364), (501, 314)],
                   [(4, 452), (86, 421), (173, 461), (257, 414), (349, 450), (441, 409), (510, 438)]]
    bosses = [(112, 76, 7), (274, 58, 6), (188, 249, 7), (352, 228, 6), (218, 379, 7), (411, 364, 6)]
    repairs = [[(73, 151), (119, 176), (151, 210)], [(346, 265), (388, 290), (417, 327)]]
    sockets = [(256, 492, 15), (256, 492, 28)]
    masks = dict(primary_antler_channels=_paths(horns, 4), forked_antler_tines=_paths(branches, 2),
                 attached_growth_ridges=_paths(growth, 1), irregular_shield_plate_seams=_paths(plate_seams, 2),
                 plate_junction_bosses=_circles(bosses, 2), horn_pore_beads=_circles(pores, 1),
                 split_repair_paths=_paths(repairs, 2), basal_root_sockets=_circles(sockets, 2))
    own = dict(primary_antler_channels=("A", 230, 36, 34), forked_antler_tines=("B", 58, 76, 248),
               attached_growth_ridges=("B", 108, 136, 226), irregular_shield_plate_seams=("N", 26, 240, 28),
               plate_junction_bosses=("A", 196, 166, 36), horn_pore_beads=("N", 44, 218, 70),
               split_repair_paths=("A", 180, 92, 50), basal_root_sockets=("B", 94, 54, 242))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .002 * np.hypot(x - root[0], y - root[1])))


def _w4_chrysina_gold() -> _Grammar:
    """Chirped Bragg lamellae wrap two non-equivalent reflector foci."""
    x, y = _xy()
    r1 = np.hypot((x - 166) * 1.08, (y - 300) * .82)
    r2 = np.hypot((x - 392) * .86, (y - 183) * 1.12)
    phi = r1 + .34 * r2 + 9 * np.sin(np.arctan2(y - 300, x - 166) * 3)
    lamellae = _periodic_line(phi + .0035 * phi * phi, 6.4, .16)
    counter = _periodic_line(r2 + .004 * r2 * r2, 7.1, .16) * (x > 248)
    cross_ribs = _periodic_line(np.arctan2(y - 300, x - 166), .24, .16) * (r1 > 38)
    boundary = _line(r1 - .72 * r2 - 35, 1.7)
    dislocations = _paths([[(31, 425), (129, 347), (205, 272), (293, 198), (468, 103)],
                           [(82, 57), (171, 126), (258, 175), (346, 232), (493, 308)]], 2)
    pinholes = _circles([(74, 383, 2), (146, 318, 2), (241, 251, 2), (329, 203, 2),
                        (407, 162, 2), (470, 122, 2), (351, 371, 2)], 1)
    arrest = _circles([(205, 272, 18), (346, 232, 15), (351, 371, 22)], 2)
    order_front = _line(np.sin(phi / 11.0 + np.arctan2(y - 183, x - 392)), .15)
    masks = dict(chirped_primary_bragg_lamellae=lamellae, counterfocus_lamellae=counter,
                 radial_lamellar_cross_ribs=cross_ribs, crystalline_focus_boundary=boundary,
                 layer_dislocation_paths=dislocations, pinhole_defects=pinholes,
                 crack_arrest_crescents=arrest, migrating_diffraction_order_front=order_front)
    own = dict(chirped_primary_bragg_lamellae=("B", 48, 62, 252), counterfocus_lamellae=("A", 238, 32, 28),
               radial_lamellar_cross_ribs=("A", 198, 66, 44), crystalline_focus_boundary=("N", 38, 228, 42),
               layer_dislocation_paths=("N", 24, 242, 28), pinhole_defects=("N", 18, 226, 76),
               crack_arrest_crescents=("A", 208, 168, 38), migrating_diffraction_order_front=("B", 94, 102, 234))
    return _pack(masks, own, _norm(phi + .21 * order_front))


def _w4_oil_beetle() -> _Grammar:
    """A non-tiled oily phase labyrinth with glands only at authored phase knots."""
    x, y = _xy()
    phase = (np.sin(x / 7.2 + 1.34 * np.sin(y / 31.0))
             + .79 * np.sin(y / 9.1 - .83 * np.sin(x / 43.0))
             + .28 * np.sin((x + y) / 17.0))
    zero = _line(phase, .13); pos = _line(phase - .72, .13); neg = _line(phase + .72, .13)
    ducts = _line(np.sin(y / 3.1 + 1.9 * np.sin(x / 23.0)) + .22 * np.sin(x / 5.0), .14)
    glands = _circles([(52, 91, 3), (119, 218, 2), (188, 137, 4), (273, 334, 3),
                       (337, 82, 2), (408, 246, 4), (468, 403, 3), (226, 457, 2)], 2)
    branch_cuts = _paths([[(14, 481), (104, 407), (179, 322), (259, 251), (361, 173), (501, 66)],
                          [(57, 18), (138, 96), (227, 156), (309, 237), (401, 307), (492, 389)]], 2)
    caustics = _line(np.sin((x + .29 * y) / 4.1) + .46 * np.sin(y / 3.3), .14) * (phase > .2)
    calluses = _circles([(119, 218, 14), (273, 334, 18), (408, 246, 13)], 2)
    masks = dict(zero_order_phase_labyrinth=zero, positive_phase_lips=pos, negative_phase_lips=neg,
                 meandering_oil_gland_ducts=ducts, authored_gland_knot_collars=glands,
                 crystallographic_branch_cuts=branch_cuts, moving_caustic_tongues=caustics,
                 cusp_callus_crescents=calluses)
    own = dict(zero_order_phase_labyrinth=("A", 230, 36, 34), positive_phase_lips=("B", 42, 50, 252),
               negative_phase_lips=("B", 94, 102, 238), meandering_oil_gland_ducts=("A", 198, 72, 48),
               authored_gland_knot_collars=("N", 32, 228, 70), crystallographic_branch_cuts=("N", 104, 196, 80),
               moving_caustic_tongues=("B", 118, 62, 244), cusp_callus_crescents=("A", 208, 176, 34))
    return _pack(masks, own, _norm(phase + .17 * np.sin((x - y) / 37.0)))


def _w4_firefly_shell() -> _Grammar:
    """One articulated luminous abdomen follows a curved body axis."""
    x, y = _xy(); t = np.linspace(0, 1, 240, dtype=np.float32)
    cx = 256 + 184 * np.sin(1.52 * np.pi * t - .73); cy = 505 - 498 * t + 10 * np.sin(3.0 * np.pi * t)
    dx = np.gradient(cx); dy = np.gradient(cy); mag = np.hypot(dx, dy); nx, ny = -dy / mag, dx / mag
    edge_a = np.c_[cx + 54 * nx, cy + 54 * ny]; edge_b = np.c_[cx - 54 * nx, cy - 54 * ny]
    joints, windows, spiracles, bristles, ribs, pulses = [], [], [], [], [], []
    segment_js = [22, 50, 81, 113, 148, 184, 216]
    for si, j in enumerate(segment_js):
        qx, qy = cx[j], cy[j]; nxx, nyy = nx[j], ny[j]; txx, tyy = dx[j] / mag[j], dy[j] / mag[j]
        joints.append([(qx - 43 * nxx, qy - 43 * nyy), (qx + 43 * nxx, qy + 43 * nyy)])
        hw, hh = 25 + 2 * (si % 3), 13 + (si % 2) * 3
        corners = [(qx - hw * txx - hh * nxx, qy - hw * tyy - hh * nyy),
                   (qx + hw * txx - hh * nxx, qy + hw * tyy - hh * nyy),
                   (qx + hw * txx + hh * nxx, qy + hw * tyy + hh * nyy),
                   (qx - hw * txx + hh * nxx, qy - hw * tyy + hh * nyy)]
        windows.append(corners)
        spiracles.extend([(qx + 34 * nxx, qy + 34 * nyy, 3), (qx - 34 * nxx, qy - 34 * nyy, 3)])
        for s in (-1, 1):
            for off in (-18, -6, 6, 18):
                bx, by = qx + off * txx + s * 43 * nxx, qy + off * tyy + s * 43 * nyy
                bristles.append([(bx, by), (bx + s * 8 * nxx, by + s * 8 * nyy)])
        for off in (-18, -9, 0, 9, 18):
            rx, ry = qx + off * txx, qy + off * tyy
            ribs.append([(rx - 12 * nxx, ry - 12 * nyy), (rx + 12 * nxx, ry + 12 * nyy)])
        for off in (-12, 4, 15):
            px, py = qx + off * txx, qy + off * tyy
            pulses.append([(px - 5 * nxx, py - 5 * nyy), (px + 5 * nxx, py + 5 * nyy)])
    caps = [edge_a[:20], edge_b[:20], edge_a[-20:], edge_b[-20:]]
    masks = dict(abdominal_edge_rails=_paths([edge_a, edge_b], 3), articulated_cuticle_joints=_paths(joints, 3),
                 luminous_window_outlines=_paths(windows, 2, True), paired_spiracle_collars=_circles(spiracles, 2),
                 joint_attached_bristles=_paths(bristles, 1), window_diffraction_ribs=_paths(ribs, 1),
                 morse_pulse_bars=_paths(pulses, 2), terminal_caps=_paths(caps, 2))
    own = dict(abdominal_edge_rails=("A", 178, 92, 60), articulated_cuticle_joints=("N", 24, 242, 24),
               luminous_window_outlines=("B", 44, 42, 252), paired_spiracle_collars=("N", 38, 224, 70),
               joint_attached_bristles=("A", 212, 184, 34), window_diffraction_ribs=("B", 86, 82, 238),
               morse_pulse_bars=("B", 122, 34, 248), terminal_caps=("A", 196, 134, 46))
    return _pack(masks, own, _norm(.38 * np.sin(x / 83.0) + .31 * np.cos(y / 71.0) + .19 * _paths(windows, 2, True)))


def _w4_weevil_pit() -> _Grammar:
    """Long weevil striae bend around two callus organs rather than tile."""
    x, y = _xy(); yy = np.linspace(0, 512, 260, dtype=np.float32)
    furrows, rails, pits, leaves, midveins, setae = [], [], [], [], [], []
    callus_centers = [(174, 188), (349, 336)]
    for i, base in enumerate(np.linspace(18, 494, 35)):
        warp = 11 * np.sin(yy / (53 + i % 7) + i * .37)
        for cx0, cy0 in callus_centers:
            warp += (base - cx0) * .11 * np.exp(-((yy - cy0) / 72) ** 2) * np.exp(-((base - cx0) / 95) ** 2)
        px = base + warp
        furrows.append(np.c_[px, yy])
        if i % 2 == 0: rails.append(np.c_[px + 4.2, yy])
        for j in range(12 + (i * 7) % 19, 250, 23 + i % 4):
            pits.append((float(px[j]), float(yy[j]), 1.3))
            if i % 3 == 1:
                cx1, cy1 = float(px[j] + 4), float(yy[j] + 3)
                a = np.linspace(0, 2 * np.pi, 30); leaves.append(np.c_[cx1 + 2.3 * np.cos(a), cy1 + 4.0 * np.sin(a)])
                midveins.append([(cx1, cy1 - 3), (cx1, cy1 + 3)])
                setae.append([(cx1 - 1, cy1), (cx1 + 5, cy1 - 4)])
    sutures = [[(256 + 7 * np.sin(v / 81), v) for v in yy]]
    calluses = _circles([(174, 188, 17), (349, 336, 21)], 2)
    wear = [[(61, 453), (142, 389), (233, 316)], [(302, 212), (385, 145), (471, 83)]]
    masks = dict(curved_longitudinal_striae=_paths(furrows, 2), raised_interstrial_rails=_paths(rails, 1),
                 stria_attached_pit_files=_circles(pits, 1), overlapping_leaf_scale_outlines=_paths(leaves, 1, True),
                 leaf_scale_midveins=_paths(midveins, 1), backward_ordered_setae=_paths(setae, 1),
                 central_suture_and_calluses=np.maximum(_paths(sutures, 3), calluses), diagonal_wear_breaks=_paths(wear, 2))
    own = dict(curved_longitudinal_striae=("N", 22, 242, 26), raised_interstrial_rails=("A", 234, 36, 36),
               stria_attached_pit_files=("N", 40, 220, 70), overlapping_leaf_scale_outlines=("B", 62, 136, 236),
               leaf_scale_midveins=("B", 104, 184, 214), backward_ordered_setae=("A", 196, 88, 48),
               central_suture_and_calluses=("A", 214, 158, 38), diagonal_wear_breaks=("N", 84, 202, 76))
    return _pack(masks, own, _norm(x / 512.0 + .27 * np.sin(y / 73.0) + .16 * calluses))


def _w4_ground_beetle() -> _Grammar:
    """A single carabid breastplate cross-braced around its central carina."""
    x, y = _xy(); carina = [[(256 + 9 * np.sin(v / 67), v) for v in np.linspace(12, 502, 210)]]
    costae_a, costae_b, braces, serrations = [], [], [], []
    for i, y0 in enumerate(np.linspace(38, 474, 18)):
        left = [(256, y0), (198 - 4 * i, y0 - 22), (116 - 2 * i, y0 - 42), (18, y0 - 64 + 5 * np.sin(i))]
        right = [(256, y0), (314 + 3 * i, y0 + 18), (392 + 2 * i, y0 + 36), (500, y0 + 53 - 4 * np.cos(i))]
        costae_a.append(left); costae_b.append(right)
        if i < 17:
            braces.append([(left[1][0], left[1][1]), (right[1][0], right[1][1])])
        for p in left[1:3] + right[1:3]: serrations.append([(p[0] - 3, p[1] - 2), (p[0] + 3, p[1] + 2)])
    punctures = [(72 + (i * 43) % 376, 64 + (i * 71) % 382, 3) for i in range(29)]
    hooks = [[(49, 111), (84, 75), (126, 91)], [(387, 418), (431, 448), (474, 421)]]
    seams = [[(22, 34), (88, 78), (155, 51), (226, 89)], [(286, 431), (365, 468), (442, 446), (501, 482)]]
    wear = _circles([(143, 298, 8), (364, 174, 7), (426, 352, 6)], 2)
    masks = dict(central_carina=_paths(carina, 4), left_radiating_costae=_paths(costae_a, 2),
                 right_radiating_costae=_paths(costae_b, 2), transverse_cross_braces=_paths(braces, 2),
                 costa_serration_teeth=_paths(serrations, 1), square_puncture_collars=_circles(punctures, 2),
                 shoulder_hooks_and_ventral_seams=np.maximum(_paths(hooks, 3), _paths(seams, 2)), wear_gaps=wear)
    own = dict(central_carina=("B", 50, 58, 252), left_radiating_costae=("A", 232, 36, 36),
               right_radiating_costae=("A", 194, 64, 46), transverse_cross_braces=("N", 102, 198, 80),
               costa_serration_teeth=("B", 84, 138, 228), square_puncture_collars=("N", 26, 236, 52),
               shoulder_hooks_and_ventral_seams=("A", 206, 174, 34), wear_gaps=("N", 18, 244, 20))
    return _pack(masks, own, _norm(.33 * np.sin(x / 89.0) + .29 * np.cos(y / 71.0) + .22 * _paths(carina, 5)))


def _w4_scarab_horn() -> _Grammar:
    """One Clelie horn bouquet with attached rings, forks and pore beads."""
    x, y = _xy(); root = (256.0, 493.0); t = np.linspace(0, 1, 210, dtype=np.float32)
    arms, growth, forks, struts, pores, abrasions = [], [], [], [], [], []
    for i, a0 in enumerate(np.linspace(-2.72, -.42, 9)):
        theta = a0 + (1.25 + .08 * i) * t + .12 * np.sin(3 * np.pi * t + i)
        radius = (62 + 340 * t) * (1 - .05 * np.sin(i * 1.4))
        px = root[0] + radius * np.cos(theta); py = root[1] + radius * np.sin(theta)
        arms.append(np.c_[px, py])
        for j in range(22, 190, 17):
            qx, qy = float(px[j]), float(py[j]); growth.append([(qx - 3, qy - 2), (qx + 3, qy + 2)])
        qx, qy = float(px[165]), float(py[165]); forks.extend([[(qx, qy), (qx + 28, qy - 35), (qx + 49, qy - 57)],
                                                               [(qx, qy), (qx - 24, qy - 32), (qx - 42, qy - 55)]])
        if i < 8: struts.append([(float(px[106]), float(py[106])), (float(px[122] + 8), float(py[122] - 5))])
        if i % 2 == 0:
            for j in (48, 94, 142): pores.append((float(px[j]), float(py[j]), 1.5))
        abrasions.append([(float(px[78] - 5), float(py[78] - 2)), (float(px[88] + 5), float(py[88] + 2))])
    collars = _circles([(256, 493, 24), (256, 493, 39), (256, 493, 54)], 2)
    sockets = _circles([(256, 493, 11), (256, 493, 18)], 2)
    masks = dict(spiralling_horn_arms=_paths(arms, 4), attached_growth_ridges=_paths(growth, 1),
                 bifurcated_horn_tips=_paths(forks, 2), cross_horn_struts=_paths(struts, 2),
                 basal_growth_collars=collars, ordered_pore_beads=_circles(pores, 1),
                 abrasion_flats=_paths(abrasions, 2), root_sockets=sockets)
    own = dict(spiralling_horn_arms=("A", 182, 86, 62), attached_growth_ridges=("B", 72, 90, 240),
               bifurcated_horn_tips=("B", 44, 50, 252), cross_horn_struts=("N", 104, 204, 76),
               basal_growth_collars=("A", 236, 32, 34), ordered_pore_beads=("N", 24, 232, 54),
               abrasion_flats=("A", 202, 180, 32), root_sockets=("B", 92, 66, 230))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .0027 * np.hypot(x - root[0], y - root[1])))


def _w4_ladybird_dome() -> _Grammar:
    """One asymmetric ladybird dome with authored maculae and rim anatomy."""
    x, y = _xy(); a = np.linspace(-.06, 2 * np.pi + .06, 260)
    outline = np.c_[256 + 223 * np.cos(a) * (1 + .04 * np.sin(3 * a)),
                    271 + 214 * np.sin(a) * (1 + .03 * np.cos(5 * a))]
    suture = [[(257 + 17 * np.sin(v / 91), v) for v in np.linspace(58, 484, 190)]]
    inner_rims = []
    for scale in (.72, .86): inner_rims.append(np.c_[256 + 223 * scale * np.cos(a), 271 + 214 * scale * np.sin(a)])
    maculae = [(129, 147, 24), (219, 112, 16), (349, 139, 29), (411, 241, 18),
               (327, 329, 23), (177, 354, 31), (104, 279, 14)]
    crowns = [[(103, 112), (159, 82), (223, 69)], [(293, 72), (354, 91), (397, 126)]]
    pores = []
    for i, (cx, cy, r0) in enumerate(maculae):
        for ang in np.linspace(0, 2 * np.pi, 9 + i % 4, endpoint=False):
            pores.append((cx + (r0 + 8) * np.cos(ang), cy + (r0 + 8) * np.sin(ang), 1.2))
    scallops = []
    for ang in np.linspace(.15, 2.95, 35):
        qx, qy = 256 + 223 * np.cos(ang), 271 + 214 * np.sin(ang)
        scallops.append([(qx - 3, qy - 2), (qx, qy + 4), (qx + 3, qy - 2)])
    head = [[(156, 90), (256, 47), (361, 93), (327, 121), (256, 107), (187, 123), (156, 90)]]
    masks = dict(asymmetric_dome_outline=_paths([outline], 4, True), flowing_central_suture=_paths(suture, 3),
                 nested_highlight_rims=_paths(inner_rims, 2), authored_black_maculae=_circles(maculae, 3),
                 crown_glint_comets=_paths(crowns, 3), macula_attached_pore_collars=_circles(pores, 1),
                 scalloped_outer_edge=_paths(scallops, 1), articulated_head_cap=_paths(head, 3, True))
    own = dict(asymmetric_dome_outline=("A", 174, 94, 60), flowing_central_suture=("N", 22, 242, 24),
               nested_highlight_rims=("B", 102, 70, 238), authored_black_maculae=("N", 28, 218, 70),
               crown_glint_comets=("B", 42, 30, 252), macula_attached_pore_collars=("A", 210, 158, 36),
               scalloped_outer_edge=("A", 196, 186, 30), articulated_head_cap=("B", 112, 52, 244))
    er = np.hypot((x - 256) / 223.0, (y - 271) / 214.0)
    return _pack(masks, own, _norm(er + .18 * np.sin(np.arctan2(y - 271, x - 256) * 3)))


def _w4_hummingbird_gorget() -> _Grammar:
    """One expanding gorget fan whose arrow platelets attach to curved feather rays."""
    x, y = _xy(); root = (256.0, 500.0); t = np.linspace(0, 1, 220, dtype=np.float32)
    lanes, rachises, arrows, barbs, pockets, lips, notches, glints = [], [], [], [], [], [], [], []
    for i, a in enumerate(np.linspace(-2.70, -.44, 37)):
        length = 418 + 38 * np.sin(i * .61)
        px = root[0] + length * t * np.cos(a) + 22 * np.sin(np.pi * t) * np.sin(i * .29)
        py = root[1] + length * t * np.sin(a) - 13 * np.sin(np.pi * t) * np.cos(i * .41)
        lanes.append(np.c_[px, py]); rachises.append(np.c_[px[::2], py[::2]])
        for j in range(24 + i % 5, 205, 14 + i % 3):
            qx, qy = float(px[j]), float(py[j]); span = 3 + (j + i) % 3
            arrows.append([(qx - span, qy + 3), (qx, qy - 3), (qx + span, qy + 3)])
            barbs.append([(qx - 4, qy - 1), (qx + 4, qy + 1)])
            lips.append([(qx - 3, qy + 5), (qx + 3, qy + 5)])
        if i % 5 == 1: pockets.append((float(px[46]), float(py[46]), 3))
        if i in {3, 12, 24, 33}: notches.append((float(px[-8]), float(py[-8]), 3))
        glints.append([(float(px[130] - 4), float(py[130])), (float(px[130] + 5), float(py[130]))])
    masks = dict(curved_feather_lanes=_paths(lanes, 1), central_rachises=_paths(rachises, 2),
                 attached_arrow_platelets=_paths(arrows, 1), transverse_barb_ridges=_paths(barbs, 1),
                 black_basal_pockets=_circles(pockets, -1), platelet_overlap_lips=_paths(lips, 1),
                 terminal_tip_notches=_circles(notches, 2), orientation_glint_lines=_paths(glints, 1))
    own = dict(curved_feather_lanes=("A", 212, 56, 44), central_rachises=("N", 38, 228, 50),
               attached_arrow_platelets=("A", 244, 30, 22), transverse_barb_ridges=("B", 58, 96, 246),
               black_basal_pockets=("N", 18, 244, 18), platelet_overlap_lips=("B", 100, 72, 232),
               terminal_tip_notches=("A", 188, 174, 32), orientation_glint_lines=("B", 40, 32, 252))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .003 * np.hypot(x - root[0], y - root[1])))


def _w4_peacock_eye() -> _Grammar:
    """A five-eye peacock plume, each ocellus authored on a shared branching stem."""
    x, y = _xy(); centers = [(120, 118, 34, 43), (267, 72, 29, 38), (405, 137, 37, 47),
                             (191, 305, 31, 41), (363, 342, 35, 45)]
    rims, pupils, petals, corona, barbs, eyelids, glints, stems = [], [], [], [], [], [], [], []
    stem_root = (256, 508)
    for i, (cx, cy, rx, ry) in enumerate(centers):
        a = np.linspace(0, 2 * np.pi, 160)
        rims.append(np.c_[cx + rx * np.cos(a), cy + ry * np.sin(a) * (1 + .08 * np.cos(a))])
        pupils.append((cx + (3 if i % 2 else -3), cy, 5))
        for phase in np.linspace(0, 2 * np.pi, 9, endpoint=False):
            aa = np.linspace(phase - .12, phase + .12, 14)
            petals.append(np.c_[cx + .48 * rx * np.cos(aa), cy + .48 * ry * np.sin(aa)])
        for scale in (.62, .76): corona.append(np.c_[cx + rx * scale * np.cos(a), cy + ry * scale * np.sin(a)])
        for phase in np.linspace(0, 2 * np.pi, 24, endpoint=False):
            barbs.append([(cx + .78 * rx * np.cos(phase), cy + .78 * ry * np.sin(phase)),
                          (cx + 1.06 * rx * np.cos(phase), cy + 1.06 * ry * np.sin(phase))])
        eyelids.append([(cx - .72 * rx, cy - .12 * ry), (cx, cy - .34 * ry), (cx + .72 * rx, cy - .10 * ry)])
        glints.append((cx - 5, cy - 7, 2))
        stems.append([stem_root, ((stem_root[0] + cx) / 2 + 30 * np.sin(i), (stem_root[1] + cy) / 2), (cx, cy + ry)])
    masks = dict(authored_teardrop_ocellus_rims=_paths(rims, 3, True), eccentric_dark_pupils=_circles(pupils, -1),
                 nine_petal_iris_segments=_paths(petals, 2), double_gold_coronae=_paths(corona, 2),
                 radial_tail_barbs=_paths(barbs, 1), parabolic_eyelids=_paths(eyelids, 2),
                 offset_glint_beads=_circles(glints, -1), branching_feather_stems=_paths(stems, 3))
    own = dict(authored_teardrop_ocellus_rims=("A", 198, 58, 44), eccentric_dark_pupils=("N", 18, 244, 18),
               nine_petal_iris_segments=("B", 50, 54, 252), double_gold_coronae=("A", 238, 30, 26),
               radial_tail_barbs=("B", 86, 130, 232), parabolic_eyelids=("N", 46, 214, 72),
               offset_glint_beads=("B", 38, 28, 254), branching_feather_stems=("A", 204, 172, 34))
    tone = np.minimum.reduce([np.hypot((x - cx) / rx, (y - cy) / ry) for cx, cy, rx, ry in centers])
    return _pack(masks, own, _norm(tone + .15 * np.arctan2(y - 508, x - 256)))


def _w4_starling_sheen() -> _Grammar:
    """Nine sweeping rachises carry nonuniform hooked barbule families."""
    x, y = _xy(); t = np.linspace(0, 1, 220, dtype=np.float32)
    rachises, forward, backward, hooks, nodes, ladders, pockets, gaps = [], [], [], [], [], [], [], []
    starts = [(18, 44), (27, 101), (15, 174), (34, 236), (12, 301), (31, 361), (18, 420), (42, 474), (102, 505)]
    for i, (sx, sy) in enumerate(starts):
        px = sx + (500 - sx) * t
        py = sy + (i - 4) * 7 * t + (22 + 3 * i) * np.sin(1.2 * np.pi * t + .39 * i)
        rachises.append(np.c_[px, py])
        for j in range(20, 205, 15 + i % 4):
            qx, qy = float(px[j]), float(py[j]); span = 9 + (j + i) % 8
            forward.append([(qx, qy), (qx + span, qy - 7 - i % 3)])
            backward.append([(qx, qy), (qx + span - 2, qy + 6 + i % 4)])
            a = np.linspace(.15, 1.45 * np.pi, 22)
            hooks.append(np.c_[qx + span + 2.3 * np.cos(a), qy - 3 + 2.3 * np.sin(a)])
            nodes.append((qx, qy, 1.5))
        for j in range(28, 196, 34):
            qx, qy = float(px[j]), float(py[j]); ladders.extend([[(qx - 3, qy - 4), (qx + 3, qy - 4)],
                                                                  [(qx - 3, qy + 4), (qx + 3, qy + 4)]])
        pockets.append((float(px[47]), float(py[47]), 4))
        if i in {1, 4, 7}: gaps.append(np.c_[px[115:132], py[115:132] + 3])
    masks = dict(sweeping_rachis_paths=_paths(rachises, 3), forward_barbule_branches=_paths(forward, 1),
                 backward_barbule_branches=_paths(backward, 1), terminal_barbicel_hooks=_paths(hooks, 1),
                 barbule_crosslink_nodes=_circles(nodes, 1), platelet_ladder_rungs=_paths(ladders, 1),
                 overlap_pockets=_circles(pockets, 2), authored_missing_barb_gaps=_paths(gaps, 3))
    own = dict(sweeping_rachis_paths=("A", 232, 34, 32), forward_barbule_branches=("B", 60, 106, 244),
               backward_barbule_branches=("B", 102, 70, 238), terminal_barbicel_hooks=("A", 196, 84, 46),
               barbule_crosslink_nodes=("N", 88, 202, 74), platelet_ladder_rungs=("A", 208, 160, 36),
               overlap_pockets=("B", 42, 42, 252), authored_missing_barb_gaps=("N", 18, 244, 20))
    return _pack(masks, own, _norm(.37 * np.sin((x + .31 * y) / 67.0) + y / 512.0))


def _w4_magpie_wing() -> _Grammar:
    """One magpie wing fan with white bars crossing its black vane anatomy."""
    x, y = _xy(); root = (24.0, 468.0); t = np.linspace(0, 1, 210, dtype=np.float32)
    vanes, rachises, barbs, hooks, nodes, teeth = [], [], [], [], [], []
    for i, a in enumerate(np.linspace(-1.22, .12, 21)):
        length = 470 - 7 * abs(i - 11)
        px = root[0] + length * t * np.cos(a) + 14 * np.sin(np.pi * t) * np.sin(.4 * i)
        py = root[1] + length * t * np.sin(a) - 11 * np.sin(np.pi * t) * np.cos(.3 * i)
        vanes.append(np.c_[px, py]); rachises.append(np.c_[px[::2], py[::2]])
        for j in range(20, 192, 13 + i % 3):
            qx, qy = float(px[j]), float(py[j]); barbs.append([(qx - 2, qy + 5), (qx + 7, qy - 5)])
            if j % 2: hooks.append((qx + 7, qy - 5, 1.4))
        nodes.append((float(px[91]), float(py[91]), 2))
        teeth.append([(float(px[-10] - 3), float(py[-10] + 2)), (float(px[-1]), float(py[-1])), (float(px[-10] + 3), float(py[-10] + 2))])
    bars = [[(44, 344), (151, 305), (273, 278), (399, 269), (505, 285)],
            [(31, 389), (143, 359), (272, 348), (401, 359), (508, 394)]]
    pockets = _paths([[(78, 424), (156, 390), (244, 371)], [(336, 327), (412, 315), (487, 328)]], 5)
    fronts = _paths([[(86, 118), (177, 158), (269, 187), (369, 201), (481, 197)]], 2)
    masks = dict(radiating_black_vanes=_paths(vanes, 2), central_rachis_rails=_paths(rachises, 3),
                 silver_white_crossbars=_paths(bars, 5), attached_hooked_barbules=_paths(barbs, 1),
                 barbule_hook_nodes=_circles(hooks, 1), black_overlap_pockets=pockets,
                 terminal_edge_teeth=_paths(teeth, 1), interference_order_front=fronts)
    own = dict(radiating_black_vanes=("A", 166, 100, 58), central_rachis_rails=("N", 90, 196, 78),
               silver_white_crossbars=("B", 50, 44, 252), attached_hooked_barbules=("A", 228, 40, 38),
               barbule_hook_nodes=("B", 98, 64, 238), black_overlap_pockets=("N", 18, 244, 18),
               terminal_edge_teeth=("A", 202, 174, 34), interference_order_front=("B", 72, 102, 230))
    return _pack(masks, own, _norm(np.arctan2(y - root[1], x - root[0]) + .0022 * np.hypot(x - root[0], y - root[1])))


def _w4_duck_speculum() -> _Grammar:
    """One contiguous duck speculum band assembled from unequal feather panels."""
    x, y = _xy(); centers = [(61, 287), (102, 275), (146, 263), (193, 252), (242, 246),
                             (292, 244), (342, 249), (390, 260), (434, 276), (474, 296)]
    panels, white_bars, rachises, barbs_a, barbs_b, hooks, lips, pinions = [], [], [], [], [], [], [], []
    for i, (cx, cy) in enumerate(centers):
        hw = 18 + i % 4; hh = 108 + (i * 9) % 28; slant = (i - 4.5) * 1.8
        poly = [(cx - hw, cy - hh + slant), (cx + hw, cy - hh - slant),
                (cx + hw + 5, cy + hh - slant), (cx - hw - 4, cy + hh + slant)]
        panels.append(poly)
        rachises.append([(cx - 2, cy - hh + 6), (cx + 2, cy + hh - 6)])
        white_bars.extend([[(cx - hw, cy - hh + 9), (cx + hw, cy - hh + 6)],
                           [(cx - hw - 2, cy + hh - 9), (cx + hw + 3, cy + hh - 12)]])
        for off in range(-hh + 14, hh - 12, 12 + i % 3):
            barbs_a.append([(cx, cy + off), (cx + hw - 3, cy + off - 7)])
            barbs_b.append([(cx, cy + off + 4), (cx - hw + 3, cy + off + 10)])
            if (off + i) % 2: hooks.append((cx + hw - 4, cy + off - 6, 1.3))
        lips.append([(cx - hw - 2, cy + hh - 3), (cx + hw + 4, cy + hh - 6)])
        pinions.append([(cx - 4, cy - hh + 3), (cx, cy - hh - 5), (cx + 4, cy - hh + 2)])
    flash = _paths([[(25, 218), (119, 202), (227, 199), (342, 208), (487, 249)],
                    [(32, 329), (132, 343), (250, 350), (375, 342), (493, 317)]], 2)
    masks = dict(unequal_speculum_feather_panels=_paths(panels, 2, True), white_border_bars=_paths(white_bars, 4),
                 individual_rachis_rails=_paths(rachises, 2), forward_barbule_families=_paths(barbs_a, 1),
                 backward_barbule_families=_paths(barbs_b, 1), attached_hook_nodes=_circles(hooks, 1),
                 feather_overlap_lips=_paths(lips, 2), pinion_teeth_and_flash_fronts=np.maximum(_paths(pinions, 1), flash))
    own = dict(unequal_speculum_feather_panels=("B", 50, 56, 252), white_border_bars=("N", 112, 182, 94),
               individual_rachis_rails=("A", 222, 40, 38), forward_barbule_families=("A", 188, 74, 54),
               backward_barbule_families=("B", 98, 90, 234), attached_hook_nodes=("N", 34, 226, 66),
               feather_overlap_lips=("B", 72, 42, 250), pinion_teeth_and_flash_fronts=("A", 202, 168, 34))
    band = y - (258 + 34 * np.sin((x - 62) / 143.0))
    return _pack(masks, own, _norm(.37 * x / 512.0 + .29 * band / 180.0 + .18 * flash))


def _w5_sunset_moth() -> _Grammar:
    """A bilateral sunset moth: two scalloped wings attach to one body spine."""
    x, y = _xy(); body_y = np.linspace(62, 461, 180, dtype=np.float32)
    body = [[(256 + 7 * np.sin(v / 51), v) for v in body_y]]
    left_tips = [(29, 73), (8, 137), (17, 211), (4, 292), (25, 371), (72, 443)]
    right_tips = [(483, 58), (507, 126), (493, 205), (509, 281), (486, 365), (435, 451)]
    primaries, upper, lower, rakes = [], [], [], []
    t = np.linspace(0, 1, 150, dtype=np.float32)
    for side, tips in ((-1, left_tips), (1, right_tips)):
        for i, (ex, ey) in enumerate(tips):
            root_y = 144 + i * 48
            px = 256 + (ex - 256) * t + side * 14 * np.sin(np.pi * t) * np.sin(i + .4)
            py = root_y + (ey - root_y) * t - 12 * np.sin(np.pi * t) * np.cos(i * .7)
            primaries.append(np.c_[px, py])
            for j in range(24, 138, 18):
                qx, qy = float(px[j]), float(py[j]); rise = -1 if (i + j) % 2 else 1
                branch = [(qx, qy), (qx + side * 12, qy + rise * 8), (qx + side * 24, qy + rise * 11)]
                (upper if rise < 0 else lower).append(branch)
            for j in range(16, 140, 9):
                qx, qy = float(px[j]), float(py[j]); rakes.append([(qx - 3, qy + 2), (qx + 3, qy - 2)])
    left_rim = [(256, 110), *left_tips, (256, 431)]; right_rim = [(256, 105), *right_tips, (256, 435)]
    crescents = [(61, 160, 12), (48, 290, 15), (92, 397, 10), (452, 143, 11), (468, 278, 14), (428, 402, 9)]
    eyes = [(61, 160, 3), (48, 290, 4), (452, 143, 3), (468, 278, 4)]
    antennae = [[(252, 67), (218, 27), (184, 14)], [(260, 67), (296, 25), (331, 12)]]
    masks = dict(central_body_spine=_paths(body, 4), bilateral_costal_veins=_paths(primaries, 2),
                 upper_venation_forks=_paths(upper, 1), lower_venation_forks=_paths(lower, 1),
                 attached_scale_rakes=_paths(rakes, 1), asymmetrical_scalloped_rims=_paths([left_rim, right_rim], 3),
                 sunset_crescent_bands=_circles(crescents, 2), false_eye_cups_and_antennae=np.maximum(_circles(eyes, -1), _paths(antennae, 2)))
    own = dict(central_body_spine=("N", 24, 238, 48), bilateral_costal_veins=("A", 238, 34, 30),
               upper_venation_forks=("A", 198, 56, 42), lower_venation_forks=("B", 62, 118, 236),
               attached_scale_rakes=("B", 88, 164, 216), asymmetrical_scalloped_rims=("N", 22, 240, 54),
               sunset_crescent_bands=("B", 42, 46, 252), false_eye_cups_and_antennae=("A", 218, 186, 30))
    return _pack(masks, own, _norm(.38 * np.sin((x - 256) / 83.0) + y / 512.0 + .18 * _paths(body, 5)))


def _w5_swallowtail() -> _Grammar:
    """A sharp bilateral X-wing with two dominant swallowtail prongs."""
    x, y = _xy(); thorax = [[(256, 102), (249, 193), (257, 284), (251, 374)]]
    roots = [(253, 188), (256, 273)]
    left_tips = [(24, 24), (4, 91), (18, 164), (38, 238)]
    right_tips = [(487, 31), (509, 102), (493, 174), (474, 244)]
    shafts, forks, rakes = [], [], []
    t = np.linspace(0, 1, 145, dtype=np.float32)
    for side, tips in ((-1, left_tips), (1, right_tips)):
        for i, tip in enumerate(tips):
            root = roots[i % 2]
            px = root[0] + (tip[0] - root[0]) * t + side * 9 * np.sin(np.pi * t)
            py = root[1] + (tip[1] - root[1]) * t + 7 * np.sin(np.pi * t) * np.sin(i)
            shafts.append(np.c_[px, py])
            qx, qy = float(px[82]), float(py[82])
            forks.extend([[(qx, qy), (qx + side * 31, qy - 18), (qx + side * 58, qy - 27)],
                          [(qx, qy), (qx + side * 28, qy + 15), (qx + side * 55, qy + 24)]])
            for j in range(18, 134, 9): rakes.append([(float(px[j] - 3), float(py[j] + 2)), (float(px[j] + 3), float(py[j] - 2))])
    tails = [[(243, 303), (186, 371), (102, 504)], [(269, 303), (332, 374), (422, 506)],
             [(237, 310), (198, 382), (154, 486)], [(275, 309), (315, 386), (365, 488)]]
    notch = [[(217, 318), (256, 354), (296, 317)]]
    hinges = []
    for r0 in (16, 29, 43):
        a = np.linspace(-2.7, -.45, 70); hinges.append(np.c_[256 + r0 * np.cos(a), 275 + r0 * np.sin(a)])
    windows = [(112, 123, 6), (397, 132, 6), (178, 238, 5), (334, 241, 5)]
    eyes = [(72, 73, 4), (441, 81, 4)]
    masks = dict(central_thorax_rail=_paths(thorax, 4), sharp_radial_vane_shafts=_paths(shafts, 2),
                 paired_bifurcation_forks=_paths(forks, 2), four_long_tail_prongs=_paths(tails, 4),
                 swallowtail_v_notch=_paths(notch, 3), attached_directional_scale_rakes=_paths(rakes, 1),
                 articulated_hinges_and_flash_windows=np.maximum(_paths(hinges, 2), _circles(windows, 2)),
                 marginal_eye_cups=_circles(eyes, 2))
    own = dict(central_thorax_rail=("N", 30, 234, 30), sharp_radial_vane_shafts=("A", 232, 36, 32),
               paired_bifurcation_forks=("A", 192, 64, 46), four_long_tail_prongs=("B", 48, 56, 252),
               swallowtail_v_notch=("N", 18, 244, 20), attached_directional_scale_rakes=("B", 84, 154, 220),
               articulated_hinges_and_flash_windows=("A", 206, 178, 34), marginal_eye_cups=("B", 112, 86, 238))
    return _pack(masks, own, _norm(.36 * np.abs(x - 256) / 256.0 + .31 * y / 512.0 + .2 * _paths(tails, 5)))


def _w5_glasswing() -> _Grammar:
    """A whole transparent membrane is an irregular graph, not a radial fan."""
    x, y = _xy()
    nodes = [(36, 61), (154, 28), (291, 54), (451, 32), (493, 151), (468, 312),
             (501, 463), (356, 489), (205, 461), (47, 492), (19, 332), (72, 213),
             (171, 154), (302, 167), (407, 229), (334, 342), (181, 334), (258, 258)]
    edges = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),(9,10),(10,11),(11,0),
             (0,12),(1,12),(2,13),(3,13),(4,14),(5,14),(6,15),(7,15),(8,16),(9,16),(10,16),(11,12),
             (12,13),(13,14),(14,15),(15,16),(16,12),(12,17),(13,17),(14,17),(15,17),(16,17)]
    primary = [[nodes[a], nodes[b]] for a,b in edges[:12]]
    trusses = [[nodes[a], nodes[b]] for a,b in edges[12:]]
    caustics = []
    for k, y0 in enumerate((97, 187, 279, 371, 438)):
        xx = np.linspace(34, 486, 150); yy = y0 + (9 + 2*k) * np.sin(xx / (31 + 3*k) + .7*k)
        caustics.append(np.c_[xx, yy])
    border_scales = []
    boundary = nodes[:12] + [nodes[0]]
    for i in range(len(boundary)-1):
        ax, ay = boundary[i]; bx, by = boundary[i+1]
        for q in np.linspace(.12,.88,6):
            px, py = ax*(1-q)+bx*q, ay*(1-q)+by*q; border_scales.append([(px-2,py-2),(px+2,py+2)])
    trichia = []
    for a,b in edges[12:]:
        ax, ay = nodes[a]; bx, by = nodes[b]
        for q in (.25,.5,.75):
            px, py = ax*(1-q)+bx*q, ay*(1-q)+by*q; trichia.append([(px-2,py+2),(px+2,py-2)])
    node_pads = [(px,py,3) for px,py in nodes[12:]]
    stress = [[(68, 214),(135,246),(181,334)],[(302,167),(348,244),(334,342)],[(407,229),(451,318),(468,412)]]
    capillaries = [(118,105,12),(237,113,9),(380,104,13),(421,390,11),(117,397,10)]
    masks = dict(outer_membrane_veins=_paths(primary, 4), irregular_internal_trusses=_paths(trusses, 2),
                 newton_caustic_wrinkles=_paths(caustics, 1), sparse_border_scale_teeth=_paths(border_scales, 1),
                 truss_attached_microtrichia=_paths(trichia, 1), internal_node_pads=_circles(node_pads, 2),
                 stress_notch_paths=_paths(stress, 2), capillary_loops=_circles(capillaries, 2))
    own = dict(outer_membrane_veins=("A", 228, 38, 38), irregular_internal_trusses=("A", 188, 62, 56),
               newton_caustic_wrinkles=("B", 72, 112, 250), sparse_border_scale_teeth=("N", 104, 202, 78),
               truss_attached_microtrichia=("N", 26, 238, 44), internal_node_pads=("A", 242, 154, 24),
               stress_notch_paths=("B", 104, 72, 234), capillary_loops=("B", 48, 52, 252))
    return _pack(masks, own, _norm(.32*np.sin(x/97.0)+.29*np.cos(y/83.0)+.21*_paths(trusses,3)))


def _w5_magpie_wing() -> _Grammar:
    """One diagonal magpie rachis carries a full field of parallel vanes and white bars."""
    x, y = _xy(); t = np.linspace(0,1,220,dtype=np.float32)
    main = np.c_[18+480*t, 463-417*t+23*np.sin(2*np.pi*t)]
    vanes, barbs, hooks, nodes, teeth = [], [], [], [], []
    for i, q in enumerate(np.linspace(.05,.95,25)):
        j=int(q*219); qx,qy=main[j]
        span=94+43*np.sin(i*.63); side=-1 if i%2 else 1
        path=[(qx,qy),(qx+side*26,qy+side*34),(qx+side*span,qy+side*(66+8*np.cos(i)))]
        vanes.append(path)
        for s in np.linspace(.15,.85,7):
            ax,ay=path[0]; bx,by=path[-1]; px,py=ax*(1-s)+bx*s,ay*(1-s)+by*s
            barbs.append([(px-4,py+2),(px+5,py-2)])
            if (i+int(s*10))%3==0: hooks.append((px+4,py-2,1.4))
        nodes.append((qx,qy,2)); teeth.append([(path[-1][0]-4,path[-1][1]+2),path[-1],(path[-1][0]+4,path[-1][1]+2)])
    white_bars=[[(12,150),(132,187),(254,213),(376,223),(503,211)],[(17,296),(139,319),(263,331),(389,326),(507,301)]]
    pockets=[[(91,405),(143,359),(197,313)],[(301,191),(354,147),(410,102)]]
    fronts=[[(38,92),(148,117),(262,129),(381,118),(487,83)]]
    masks=dict(diagonal_main_rachis=_paths([main],4), alternating_parallel_vanes=_paths(vanes,2),
               silver_white_crossbars=_paths(white_bars,5), vane_attached_barbules=_paths(barbs,1),
               barbule_hook_nodes=_circles(hooks,1), black_overlap_pockets=_paths(pockets,5),
               terminal_edge_teeth=_paths(teeth,1), interference_order_front=_paths(fronts,2))
    own=dict(diagonal_main_rachis=("N",90,196,78),alternating_parallel_vanes=("A",166,100,58),
             silver_white_crossbars=("B",50,44,252),vane_attached_barbules=("A",228,40,38),
             barbule_hook_nodes=("B",98,64,238),black_overlap_pockets=("N",18,244,18),
             terminal_edge_teeth=("A",202,174,34),interference_order_front=("B",72,102,230))
    return _pack(masks,own,_norm(.35*np.sin((x+y)/89.0)+.29*(x-y)/512.0+.18*_paths([main],5)))


def _distance_from(mask: np.ndarray) -> np.ndarray:
    """Pixel distance from a builder-owned path or feature mask."""
    binary = (_f32(mask) < .16).astype(np.uint8)
    return cv2.distanceTransform(binary, cv2.DIST_L2, 5).astype(np.float32)


def _mark_union(masks: Mapping[str, np.ndarray]) -> np.ndarray:
    return np.maximum.reduce([_f32(mask) for mask in masks.values()])


def _w10_morpho_blue() -> _Grammar:
    """Six irregular branching/merging ridge trunks form dense lamellar shoals."""
    x, y = _xy(); t = np.linspace(0, 1, 260, dtype=np.float32)
    hinge = [[(-8, 268), (18, 258), (43, 262)]]
    trunks, forks, mergers, teeth = [], [], [], []
    offsets = [-116, -67, -21, 28, 76, 124]
    for i, off in enumerate(offsets):
        px = 12 + 512 * t
        py = 258 + off * (t ** (.72 + .06 * i)) + 31 * np.sin((1.2 + .11 * i) * np.pi * t + .7 * i) * t
        py += 13 * np.sin(5 * np.pi * t + i) * t * (1 - t)
        trunks.append(np.c_[px, py])
        for j in range(24 + i, 246, 13 + i % 3):
            qx, qy = float(px[j]), float(py[j]); teeth.append([(qx - 3, qy - 2), (qx, qy + 2), (qx + 4, qy - 1)])
        if i in (1, 3, 4):
            j = 118 + i * 9; qx, qy = float(px[j]), float(py[j])
            forks.append([(qx, qy), (qx + 55, qy - 22 - 5 * i), (qx + 108, qy - 31 - 7 * i)])
        if i in (0, 2, 5):
            j = 168 - i * 6; qx, qy = float(px[j]), float(py[j])
            mergers.append([(qx, qy), (qx + 48, qy + 17 - 3 * i), (qx + 96, qy + 23 - 4 * i)])
    trunk_mask = _paths(trunks, 3); d = _distance_from(trunk_mask)
    chirp = d * (1.0 + .0015 * x) + 2.7 * np.sin((x + .32 * y) / 43.0)
    ridge_faces_a = _periodic_line(chirp, 6.2, .56)
    ridge_faces_b = _periodic_line(chirp, 6.2, .56, .25)
    shelf_lips = _periodic_line(chirp + .22 * y, 11.0, .34) * np.maximum(ridge_faces_a, ridge_faces_b)
    pores = _circles([(68,252,2),(117,222,2),(174,292,2),(233,185,2),(301,338,2),(365,146,2),(432,374,2),(486,92,2)], 1)
    junctions = np.maximum(_paths(forks, 3), _paths(mergers, 3))
    tooth_m = _paths(teeth, 1)
    masks = dict(branching_nanoridge_trunks=trunk_mask, alternating_ridge_faces_a=ridge_faces_a,
                 alternating_ridge_faces_b=ridge_faces_b, lamellar_overlap_lips=shelf_lips,
                 christmas_tree_teeth=tooth_m, ordered_perforation_pores=pores,
                 fork_and_merge_junctions=junctions, surviving_left_hinge=_paths(hinge, 4))
    own = dict(branching_nanoridge_trunks=("A",220,72,52), alternating_ridge_faces_a=("A",242,44,30),
               alternating_ridge_faces_b=("B",52,112,242), lamellar_overlap_lips=("B",106,66,250),
               christmas_tree_teeth=("A",188,142,80), ordered_perforation_pores=("N",24,236,42),
               fork_and_merge_junctions=("N",96,206,94), surviving_left_hinge=("B",72,156,214))
    return _pack10(masks, own, chirp,
                   [(ridge_faces_a,242),(ridge_faces_b,64),(trunk_mask,198),(tooth_m,154)],
                   [(ridge_faces_a,206),(ridge_faces_b,72),(pores,238),(junctions,34),(shelf_lips,92),(trunk_mask,58)],
                   [(shelf_lips,248),(ridge_faces_b,214),(tooth_m,132),(pores,44)])


def _w10_sunset_moth() -> _Grammar:
    """A diagonally cropped unequal bilateral moth fills and exits the frame."""
    x, y = _xy(); t = np.linspace(-.12, 1.12, 260, dtype=np.float32)
    body = np.c_[-42 + 590 * t, 514 - 552 * t + 18 * np.sin(2 * np.pi * t)]
    body_mask = _paths([body], 4)
    roots = [42, 76, 113, 153, 194, 226]
    veins_l, veins_r, branches, rakes = [], [], [], []
    for i, j in enumerate(roots):
        bx, by = body[j]
        for side in (-1, 1):
            unequal = 1.0 + .16 * np.sin(i * 1.7 + side)
            ex = bx + side * (250 + 27 * i) * unequal
            ey = by + side * (116 - 13 * i) + 28 * np.sin(i + side)
            q = np.linspace(0, 1, 130)
            px = bx + (ex - bx) * q + side * 22 * np.sin(np.pi * q) * np.cos(i)
            py = by + (ey - by) * q + 18 * np.sin(np.pi * q) * np.sin(i + .6 * side)
            (veins_l if side < 0 else veins_r).append(np.c_[px, py])
            for k in range(18, 121, 13):
                qx, qy = float(px[k]), float(py[k]); bend = side * (8 + (k % 4))
                branches.append([(qx,qy),(qx+bend,qy-7),(qx+2*bend,qy-9)])
                rakes.append([(qx-3*side,qy-2),(qx+4*side,qy+2)])
    veins = np.maximum(_paths(veins_l,3), _paths(veins_r,2)); d = _distance_from(np.maximum(veins,body_mask))
    scale_phase = d + .017 * (x - y) * (1 + .18 * np.sin((x + y) / 87.0))
    scales_a = _periodic_line(scale_phase, 5.7, .76)
    scales_b = _periodic_line(scale_phase + .008 * x * np.sin(y / 79.0), 7.1, .73, .25)
    rim_t = np.linspace(-.3,1.3,280); rim = np.c_[-30+570*rim_t, 498-525*rim_t+86*np.sin(3*np.pi*rim_t)+19*np.sin(11*np.pi*rim_t)]
    cres_a = np.linspace(-.55,1.05,120); cres = np.c_[352+94*np.cos(cres_a), 173+61*np.sin(cres_a)]
    masks = dict(diagonal_body_spine=body_mask, unequal_left_wing_tree=_paths(veins_l,3),
                 unequal_right_wing_tree=_paths(veins_r,2), dense_curvature_scale_rakes_a=scales_a,
                 dense_curvature_scale_rakes_b=scales_b, secondary_vein_forks=_paths(branches,1),
                 frame_crossing_scalloped_rim=_paths([rim],3), single_nested_crescent=_paths([cres],3))
    own = dict(diagonal_body_spine=("N",34,226,70), unequal_left_wing_tree=("A",236,46,38),
               unequal_right_wing_tree=("B",72,118,238), dense_curvature_scale_rakes_a=("A",202,136,64),
               dense_curvature_scale_rakes_b=("B",58,172,224), secondary_vein_forks=("A",178,82,52),
               frame_crossing_scalloped_rim=("N",24,240,44), single_nested_crescent=("B",108,54,250))
    cres_m = _paths([cres],3); branch_m = _paths(branches,1); rim_m = _paths([rim],3)
    return _pack10(masks,own,scale_phase,
                   [(scales_a,216),(veins,244),(cres_m,86),(scales_b,142)],
                   [(scales_b,226),(body_mask,42),(branch_m,92),(rim_m,188)],
                   [(cres_m,250),(scales_b,214),(rim_m,82),(veins,166)])


def _w10_monarch_vein() -> _Grammar:
    """A recursive asymmetric Murray tree creates herringbone territories."""
    x, y = _xy(); branches=[]
    def grow(p0, angle, length, depth, skew):
        q=np.linspace(0,1,70); px=p0[0]+length*q*np.cos(angle)+skew*9*np.sin(np.pi*q); py=p0[1]+length*q*np.sin(angle)-skew*7*np.sin(np.pi*q)
        branches.append(np.c_[px,py])
        if depth:
            end=(float(px[-1]),float(py[-1])); grow(end,angle-.48+skew*.04,length*.69,depth-1,-skew); grow(end,angle+.36+skew*.03,length*.62,depth-1,skew)
    grow((-28,472),-.63,248,4,1.0)
    tree=_paths(branches,3); d=_distance_from(tree)
    territory=np.sin((x+.37*y)/83.0)+.72*np.sin((y-.21*x)/117.0)
    theta=.55+1.05*_norm(territory)+.17*np.sin(d/19.0)
    u=x*np.cos(theta)+y*np.sin(theta); v=-x*np.sin(theta)+y*np.cos(theta)
    herr_a=_periodic_line(u+.42*np.abs(np.mod(v,15.0)-7.5),7.0,.69)
    herr_b=_periodic_line(u-.51*np.abs(np.mod(v+4.0,17.0)-8.5),8.3,.67,.25)
    cross=_periodic_line(d+.08*u,13.0,.38)*_f32((12-d)/5.0)
    nodes=_circles([(float(p[-1,0]),float(p[-1,1]),2) for p in branches if 0<p[-1,0]<512 and 0<p[-1,1]<512],1)
    margins=_periodic_line(d,21.0,.32)
    spot=_circles([(73,401,3),(142,338,2),(236,259,3),(319,192,2),(421,102,3),(486,49,2)],2)
    masks=dict(murray_recursive_tree=tree, territory_herringbones_a=herr_a, territory_herringbones_b=herr_b,
               branch_attached_cross_veins=cross, recursive_branch_nodes=nodes, territory_margin_contours=margins,
               asymmetric_white_insets=spot, fine_scale_tip_notches=np.minimum(herr_a,_periodic_line(v,4.1,.42)))
    own=dict(murray_recursive_tree=("N",28,236,34),territory_herringbones_a=("A",226,92,52),
             territory_herringbones_b=("B",62,154,230),branch_attached_cross_veins=("A",188,54,44),
             recursive_branch_nodes=("B",112,48,244),territory_margin_contours=("N",72,206,84),
             asymmetric_white_insets=("B",46,86,250),fine_scale_tip_notches=("A",204,176,38))
    tips=masks['fine_scale_tip_notches']
    return _pack10(masks,own,theta+d/31.0,
                   [(tree,242),(herr_a,196),(nodes,104),(tips,224)],
                   [(margins,216),(herr_b,72),(tree,36),(spot,164)],
                   [(herr_b,238),(cross,186),(spot,248),(tips,98)])


def _w10_atlas_wing() -> _Grammar:
    """One serpent costal ribbon hooks around a negative-space false eye."""
    x,y=_xy(); q=np.linspace(-.08,1.08,330)
    cx=-26+566*q; cy=254+106*np.sin(1.35*np.pi*q)+38*np.sin(3.8*np.pi*q)
    spine=_paths([np.c_[cx,cy]],5); d=_distance_from(spine)
    eye=np.hypot((x-367)/58.0,(y-223)/43.0); eye_gap=_inside(eye,1.0,.08)
    ribbon_a=_periodic_line(d+2*np.sin(x/59.0),6.1,.75)*(1-eye_gap)
    ribbon_b=_periodic_line(d+.018*y*np.sin(x/83.0),7.7,.72,.25)*(1-eye_gap)
    jaw=np.maximum(_ring(eye,.92,.035),_ring(eye,.68,.04)); pupil=_inside(np.hypot((x-382)/13.0,(y-226)/22.0),1,.12)
    ribs=[]; scales=[]
    for j in range(18,315,13):
        px,py=float(cx[j]),float(cy[j]); ribs.append([(px,py-15-(j%9)),(px+9,py),(px,py+15+(j%7))])
        for off in (-7,7): scales.append([(px-4,py+off-2),(px+4,py+off+2)])
    rib_m=_paths(ribs,1); pack_m=_paths(scales,1)
    antenna=[[(-8,164),(74,102),(143,119)],[(425,330),(488,398),(528,455)]]
    masks=dict(costal_serpent_spine=spine,outer_lamellar_ribbon=ribbon_a,inner_lamellar_ribbon=ribbon_b,
               hooked_false_jaw=jaw,matte_negative_space_pupil=pupil,branching_membrane_ribs=rib_m,
               curvature_following_scale_packs=pack_m,terminal_antenna_hooks=_paths(antenna,3))
    own=dict(costal_serpent_spine=("A",236,48,36),outer_lamellar_ribbon=("A",202,112,58),
             inner_lamellar_ribbon=("B",58,166,226),hooked_false_jaw=("B",112,64,248),
             matte_negative_space_pupil=("N",18,244,18),branching_membrane_ribs=("A",174,76,48),
             curvature_following_scale_packs=("B",84,198,210),terminal_antenna_hooks=("N",102,216,72))
    ant=_paths(antenna,3)
    return _pack10(masks,own,d+.19*np.arctan2(y-223,x-367),
                   [(spine,244),(ribbon_a,206),(rib_m,154),(pupil,12)],
                   [(ribbon_a,208),(ribbon_b,66),(pupil,242),(pack_m,214),(jaw,42)],
                   [(jaw,250),(ribbon_b,222),(ant,96),(rib_m,176)])


def _w10_luna_dust() -> _Grammar:
    """Dense high-frequency nodal dust chains deformed by authored craters."""
    x,y=_xy(); ch=(np.sin(np.pi*x/31.0)*np.sin(np.pi*y/43.0)-.73*np.sin(np.pi*(x+.17*y)/57.0)*np.sin(np.pi*(y-.11*x)/37.0))
    craters=[(72,91,18,12),(188,164,25,17),(337,87,16,24),(439,211,27,15),(126,347,21,28),(294,304,30,19),(414,421,23,26)]
    crater_inside=np.zeros((_WORK,_WORK),np.float32); rims=[]; ejecta=[]
    for i,(cx,cy,rx,ry) in enumerate(craters):
        er=np.hypot((x-cx)/rx,(y-cy)/ry); crater_inside=np.maximum(crater_inside,_inside(er,1,.08)); rims.append(_ring(er,.88,.045))
        a=np.linspace(-.8,.95,80); ejecta.append(np.c_[cx+(rx+9)*np.cos(a+i*.2),cy+(ry+6)*np.sin(a+i*.2)])
    deform=ch+.42*crater_inside*np.sin((x+y)/13.0)
    grooves=_line(deform,.10)*(1-.78*crater_inside); pos=_line(deform-.48,.11); neg=_line(deform+.48,.11)
    dust=np.maximum(grooves*_periodic_line(x+.43*y,4.0,.62),_periodic_line(deform*17+x/7.0,5.1,.48))
    basin_a=_periodic_line(11*deform+x/9.0,6.3,.56); basin_b=_periodic_line(13*deform-y/8.0,7.2,.54,.25)
    rim_m=np.maximum.reduce(rims); eject_m=_paths(ejecta,2); spokes=[]
    for i,(cx,cy,rx,ry) in enumerate(craters):
        for a in (.3+i*.2,1.7+i*.1,3.1+i*.17,4.6+i*.09): spokes.append([(cx,cy),(cx+(rx+14)*np.cos(a),cy+(ry+14)*np.sin(a))])
    spoke_m=_paths(spokes,1)
    masks=dict(deformed_primary_nodal_grooves=grooves,positive_basin_dust=basin_a,negative_basin_dust=basin_b,
               compressed_dust_chains=dust,elliptic_crater_rims=rim_m,crescent_ejecta_chains=eject_m,
               crater_radial_spokes=spoke_m,interrupted_order_nodes=np.maximum(pos,neg))
    own=dict(deformed_primary_nodal_grooves=("N",42,68,88),positive_basin_dust=("A",218,146,54),
             negative_basin_dust=("B",66,202,222),compressed_dust_chains=("A",242,112,34),
             elliptic_crater_rims=("B",104,54,246),crescent_ejecta_chains=("B",142,174,214),
             crater_radial_spokes=("N",28,226,62),interrupted_order_nodes=("A",184,82,46))
    return _pack10(masks,own,deform,
                   [(grooves,198),(basin_a,226),(rim_m,82),(spoke_m,146)],
                   [(dust,218),(grooves,58),(crater_inside,232),(eject_m,126)],
                   [(basin_b,238),(rim_m,248),(grooves,94),(eject_m,196)])


def _w10_swallowtail() -> _Grammar:
    """Four split tail streamers weave diagonally and exit unrelated edges."""
    x,y=_xy(); q=np.linspace(-.12,1.12,320)
    streamers=[]; splits=[]; crossings=[]; teeth=[]
    specs=[(-68,96,1.08,34),(38,214,.83,-42),(141,336,1.31,47),(249,455,.67,-31)]
    for i,(sx,sy,freq,amp) in enumerate(specs):
        px=sx+572*q; py=sy+310*q+amp*np.sin((freq*2.2)*np.pi*q+i*.8)+17*np.sin(6*np.pi*q+i)
        streamers.append(np.c_[px,py])
        for j in (92+i*7,176-i*5,246+i*3):
            bx,by=float(px[j]),float(py[j]); side=-1 if (i+j)%2 else 1
            splits.append([(bx,by),(bx+42,by+side*27),(bx+91,by+side*48)])
        for j in range(25,300,12+i):
            bx,by=float(px[j]),float(py[j]); teeth.append([(bx-3,by-2),(bx,by+3),(bx+4,by-1)])
    stream_m=_paths(streamers,4); split_m=_paths(splits,2); d=_distance_from(np.maximum(stream_m,split_m))
    flow=x*.21-y*.13+7*np.sin((x+y)/79.0)
    shingles_a=_periodic_line(d+.11*flow,6.0,.76)
    shingles_b=_periodic_line(d-.08*flow,7.4,.74,.25)
    overlap=_periodic_line(d+.19*x,12.0,.44)*np.maximum(shingles_a,shingles_b)
    crossing_mask=_inside(d,2.4,.8)*_periodic_line(x+y,31.0,.35)
    eyelets=_circles([(91,147,3),(188,271,2),(311,329,3),(438,441,2)],2)
    masks=dict(four_interlocking_streamers=stream_m,authored_streamer_splits=split_m,
               dense_shingles_a=shingles_a,dense_shingles_b=shingles_b,shingle_overlap_lips=overlap,
               crossing_knot_collars=crossing_mask,terminal_serration_teeth=_paths(teeth,1),sparse_flash_eyelets=eyelets)
    own=dict(four_interlocking_streamers=("A",228,52,38),authored_streamer_splits=("B",62,86,246),
             dense_shingles_a=("A",198,154,58),dense_shingles_b=("B",74,188,224),shingle_overlap_lips=("B",112,72,250),
             crossing_knot_collars=("N",34,226,72),terminal_serration_teeth=("A",214,176,34),sparse_flash_eyelets=("N",20,242,42))
    tooth_m=_paths(teeth,1)
    return _pack10(masks,own,d+.12*flow,
                   [(stream_m,242),(shingles_a,206),(split_m,136),(eyelets,72)],
                   [(crossing_mask,42),(shingles_b,218),(overlap,96),(tooth_m,164)],
                   [(overlap,248),(split_m,218),(eyelets,244),(tooth_m,126),(stream_m,168)])


def _w10_ulysses_flash() -> _Grammar:
    """Curved fault basins own chirped normal combs that terminate at walls."""
    x,y=_xy()
    f1=82+.21*x+31*np.sin(x/71.0); f2=198-.08*x+42*np.sin((x+37)/93.0); f3=335+.12*x-36*np.sin((x-51)/67.0); f4=448-.19*x+24*np.sin(x/49.0)
    walls=np.maximum.reduce([_line(y-f1,2.0),_line(y-f2,2.0),_line(y-f3,2.0),_line(y-f4,2.0)])
    regions=[y<f1,(y>=f1)&(y<f2),(y>=f2)&(y<f3),(y>=f3)&(y<f4),y>=f4]
    wall_fields=[y-f1,y-f2,y-f3,y-f4]
    combs=[]; cross=[]
    phases=[x+.18*y+6*np.sin(y/43.0), y-.37*x+7*np.sin(x/57.0), x+.61*y+9*np.sin(y/69.0), y+.22*x+8*np.sin(x/37.0), x-.53*y+5*np.sin((x+y)/61.0)]
    for i,(reg,ph) in enumerate(zip(regions,phases)):
        chirp=ph*(1+.0007*(x+37*i))+.006*ph*ph*np.sign(np.sin((x+y)/113.0))
        combs.append(_periodic_line(chirp,5.0+1.1*i,.72-.018*i)*reg)
        cross.append(_periodic_line(chirp+.31*(x-y),13+2*i,.37)*reg)
    comb_a=np.maximum.reduce(combs[::2]); comb_b=np.maximum.reduce(combs[1::2]); cross_m=np.maximum.reduce(cross)
    terminations=np.minimum(np.maximum(comb_a,comb_b),cv2.dilate(walls,np.ones((7,7),np.uint8)))
    pores=_circles([(45,89,2),(128,181,2),(231,309,2),(336,221,2),(412,421,2),(488,344,2)],1)
    fronts=_line(np.sin((x+.27*y)/17.0)+.43*np.sin(y/11.0),.16)*np.maximum(comb_a,comb_b)
    masks=dict(curved_fault_walls=walls,alternating_basin_combs_a=comb_a,alternating_basin_combs_b=comb_b,
               basin_cross_ties=cross_m,comb_termination_crowns=terminations,fault_pore_nodes=pores,
               moving_order_fronts=fronts,wall_normal_lips=_periodic_line(np.minimum.reduce([np.abs(v) for v in wall_fields]),7.1,.54))
    own=dict(curved_fault_walls=("N",46,216,82),alternating_basin_combs_a=("A",238,82,42),
             alternating_basin_combs_b=("B",54,168,232),basin_cross_ties=("A",176,132,62),
             comb_termination_crowns=("B",112,58,250),fault_pore_nodes=("N",24,238,54),
             moving_order_fronts=("B",86,112,242),wall_normal_lips=("A",202,46,34))
    lips=masks['wall_normal_lips']
    return _pack10(masks,own,.2*sum(phases)+walls,
                   [(comb_a,242),(walls,174),(terminations,92),(cross_m,212)],
                   [(comb_a,68),(comb_b,224),(walls,38),(pores,238),(cross_m,116)],
                   [(comb_b,246),(lips,208),(fronts,118),(terminations,238)])


def _w10_owl_eye() -> _Grammar:
    """Two unequal cropped eyes sit beneath overlapping crescent feather plates."""
    x,y=_xy(); eyes=[(119,275,128,153),(397,222,156,119)]
    iris=[]; pupils=np.zeros((_WORK,_WORK),np.float32); cres_a=np.zeros_like(pupils); cres_b=np.zeros_like(pupils); eyelids=[]
    for i,(cx,cy,rx,ry) in enumerate(eyes):
        er=np.hypot((x-cx)/rx,(y-cy)/ry); pupils=np.maximum(pupils,_inside(np.hypot((x-cx-(9 if i else -11))/22,(y-cy)/31),1,.12))
        iris.append(np.maximum(_ring(er,.28,.028),_ring(er,.43,.026)))
        theta=np.arctan2((y-cy)/ry,(x-cx)/rx)
        plates=np.maximum(_periodic_line(er*rx*.86+10*np.sin(3*theta+i),7.0+i,.82),
                          _periodic_line(er*rx*.61-8*np.sin(2*theta-i),10.3+i,.58,.25))*(er>.18)*(er<1.82)
        if i==0: cres_a=np.maximum(cres_a,plates)
        else: cres_b=np.maximum(cres_b,plates)
        eyelids.extend([[(cx-rx*.9,cy-ry*.13),(cx-20,cy-ry*.55),(cx+rx*.83,cy-ry*.18)],
                        [(cx-rx*.78,cy+ry*.12),(cx+12,cy+ry*.40),(cx+rx*.74,cy+ry*.09)]])
    iris_m=np.maximum.reduce(iris); lid_m=_paths(eyelids,4)
    plate_lips=np.minimum(np.maximum(cres_a,cres_b),_periodic_line(x-.31*y,9.0,.50))
    chevrons=_line(np.abs(x-258)+.72*(y-264)-124,2.0)
    glints=_circles([(93,244,4),(424,192,3)],-1)
    rough_tiers=_periodic_line(np.minimum(np.hypot((x-119)/128,(y-275)/153),np.hypot((x-397)/156,(y-222)/119))*91,10.0,.56)
    masks=dict(unequal_cropped_iris_rings=iris_m,matte_offset_pupils=pupils,left_crescent_feather_plates=cres_a,
               right_crescent_feather_plates=cres_b,layered_eyelid_chevrons=lid_m,plate_overlap_lips=plate_lips,
               central_beak_chevron=chevrons,offset_glints_and_plate_tiers=np.maximum(glints,rough_tiers))
    own=dict(unequal_cropped_iris_rings=("B",112,54,250),matte_offset_pupils=("N",18,244,18),
             left_crescent_feather_plates=("A",214,148,54),right_crescent_feather_plates=("B",66,182,226),
             layered_eyelid_chevrons=("A",232,46,36),plate_overlap_lips=("B",92,88,244),
             central_beak_chevron=("N",104,204,76),offset_glints_and_plate_tiers=("A",184,122,112))
    gltier=np.maximum(glints,rough_tiers)
    return _pack10(masks,own,.4*np.hypot(x-119,y-275)+.6*np.hypot(x-397,y-222),
                   [(iris_m,238),(lid_m,198),(cres_a,142),(pupils,8)],
                   [(pupils,242),(cres_b,214),(rough_tiers,72),(lid_m,118)],
                   [(iris_m,250),(plate_lips,226),(cres_b,156),(glints,244)])


def _w10_glasswing() -> _Grammar:
    """Four unequal edge loads bend a dense tensile membrane and capillary trees."""
    x,y=_xy(); loads=[(-42,88,1.2),(182,-37,.8),(551,197,1.35),(344,559,1.0)]
    potential=np.zeros((_WORK,_WORK),np.float32); angle=np.zeros_like(potential)
    for lx,ly,w in loads:
        rr=np.hypot(x-lx,y-ly)+9; potential+=w*np.log(rr); angle+=w*np.arctan2(y-ly,x-lx)
    truss_a=_periodic_line(17*potential+2.2*angle,6.0,.58)
    truss_b=_periodic_line(13*potential-2.9*angle,7.4,.56,.25)
    stress=_line(np.sin(9*potential)+.51*np.sin(5*angle),.18)
    caustic=_periodic_line(11*potential+x/17.0-y/23.0,8.3,.50)
    capillary=[]
    seeds=[(21,103),(176,18),(493,193),(353,491)]
    for i,(sx,sy) in enumerate(seeds):
        for branch in range(5):
            q=np.linspace(0,1,100); ex=256+105*np.cos(i+branch*.7); ey=258+92*np.sin(i+branch*.9)
            px=sx+(ex-sx)*q+18*np.sin(np.pi*q)*(branch-2); py=sy+(ey-sy)*q+15*np.sin(2*np.pi*q+i)
            capillary.append(np.c_[px,py])
    cap_m=_paths(capillary,2); nodes=_circles([(256,258,4),(177,181,3),(347,184,3),(321,344,3),(142,322,3)],2)
    micro=_periodic_line(potential*21+.23*x,5.3,.58)*np.maximum(truss_a,truss_b)
    borders=_paths([[(-8,31),(182,-9),(383,22),(522,116)],[(523,116),(492,329),(389,520)],[(389,520),(163,496),(-9,421)]],3)
    masks=dict(load_curved_primary_trusses=truss_a,bifurcating_counter_trusses=truss_b,tensile_stress_seams=stress,
               dense_caustic_wrinkles=caustic,authored_capillary_trees=cap_m,capillary_junction_pads=nodes,
               membrane_microtrichia=micro,loaded_outer_membrane_edges=borders)
    own=dict(load_curved_primary_trusses=("A",232,58,42),bifurcating_counter_trusses=("B",58,168,232),
             tensile_stress_seams=("A",182,98,52),dense_caustic_wrinkles=("B",102,192,244),
             authored_capillary_trees=("A",214,72,46),capillary_junction_pads=("N",38,226,70),
             membrane_microtrichia=("N",92,206,88),loaded_outer_membrane_edges=("B",74,54,250))
    return _pack10(masks,own,potential+.11*angle,
                   [(truss_a,238),(cap_m,202),(nodes,86),(micro,158)],
                   [(truss_b,218),(stress,48),(micro,174),(borders,104)],
                   [(caustic,246),(truss_b,184),(nodes,232),(borders,82)])


def _w10_emperor_scale() -> _Grammar:
    """Three offset crown-lamella braids sweep as one S-shaped construction."""
    x,y=_xy(); q=np.linspace(-.08,1.08,330); braids=[]; lips=[]; teeth=[]; pores=[]
    for i,(off,amp,freq) in enumerate(((-92,71,1.05),(0,96,.83),(88,63,1.27))):
        px=-28+568*q; py=252+off+amp*np.sin(freq*2*np.pi*q+i*.9)+24*np.sin(4*np.pi*q+i)
        braids.append(np.c_[px,py]); lips.append(np.c_[px,py+(-1 if i%2 else 1)*(7+2*i)])
        schedule=11+i*4
        for j in range(18+i*5,315,schedule):
            if (j//schedule+i)%7==0: continue
            bx,by=float(px[j]),float(py[j]); teeth.append([(bx-3,by-3),(bx,by+3),(bx+4,by-2)])
        for j in range(31+i*7,300,37-i*3): pores.append((float(px[j]),float(py[j]),1.7))
    braid_m=_paths(braids,5); lip_m=_paths(lips,2); d=_distance_from(braid_m)
    lam_a=_periodic_line(d+.013*x*np.sin(y/79.0),5.8,.77)
    lam_b=_periodic_line(d-.017*y*np.sin(x/67.0),7.2,.75,.25)
    crossings=np.minimum(cv2.dilate(braid_m,np.ones((9,9),np.uint8)),_periodic_line(x+y,29.0,.40))
    missing=_line(np.sin((x-2*y)/31.0)+.44*np.sin(y/13.0),.17)*lam_a
    masks=dict(three_sweeping_braid_spines=braid_m,offset_crossing_lips=lip_m,dense_crown_lamellae_a=lam_a,
               dense_crown_lamellae_b=lam_b,distinct_serration_schedules=_paths(teeth,1),authored_missing_teeth=missing,
               braid_attached_pores=_circles(pores,1),crossing_knot_fields=crossings)
    own=dict(three_sweeping_braid_spines=("A",232,54,38),offset_crossing_lips=("B",84,92,246),
             dense_crown_lamellae_a=("A",204,146,56),dense_crown_lamellae_b=("B",62,186,228),
             distinct_serration_schedules=("A",218,82,42),authored_missing_teeth=("N",24,238,34),
             braid_attached_pores=("N",102,218,76),crossing_knot_fields=("B",118,58,250))
    tooth_m=_paths(teeth,1); pore_m=_circles(pores,1)
    return _pack10(masks,own,d+.15*np.sin((x+y)/53.0),
                   [(braid_m,242),(lam_a,206),(tooth_m,166),(missing,52)],
                   [(pore_m,232),(crossings,46),(lam_b,216),(lip_m,104)],
                   [(lip_m,250),(tooth_m,226),(missing,182),(pore_m,86),(crossings,138)])


def _w10_jewel_scarab() -> _Grammar:
    """A cropped split elytron diverts its costae around five puncture constellations."""
    x,y=_xy(); seam_x=258+27*np.sin(y/73.0)+13*np.sin(y/29.0)-.00042*(y-256)**2
    seam=_line(x-seam_x,2.7); left=x<seam_x; right=~left
    const=[(83,97,19,13),(174,337,26,17),(326,144,18,25),(426,286,29,18),(368,446,21,28)]
    deflections=np.zeros((_WORK,_WORK),np.float32); punctures=np.zeros_like(deflections); shadows=np.zeros_like(deflections)
    satellites=[]; arrest=[]
    for i,(cx,cy,rx,ry) in enumerate(const):
        er=np.hypot((x-cx)/rx,(y-cy)/ry); th=np.arctan2((y-cy)/ry,(x-cx)/rx)
        deflections+=(9+2*i)*np.exp(-2.3*er)*np.sin(th*(2+i%2)+.8*i)
        punctures=np.maximum(punctures,np.maximum(_ring(er,.72,.055),_ring(er,1.0,.04)))
        shadows=np.maximum(shadows,_inside(er,.46,.12))
        for a in (.25+i*.31,1.9+i*.17,3.7-i*.11,5.2+i*.09):
            satellites.append((cx+(rx+5)*np.cos(a),cy+(ry+4)*np.sin(a),1.6))
        arrest.append([(cx-rx-9,cy+ry*.15),(cx-rx+3,cy+ry*.34)])
    base=np.where(left,seam_x-x,x-seam_x)
    phase=base+deflections+.013*y*np.where(left,1.0,-1.0)
    costa_l=np.maximum(_periodic_line(phase+4*np.sin(y/47.0),6.3,.78),
                       _periodic_line(phase-.19*y,10.1,.61,.25))*left
    costa_r=np.maximum(_periodic_line(phase-3*np.sin(y/59.0),7.7,.76,.25),
                       _periodic_line(phase+.23*y,11.3,.59))*right
    cross_lips=_periodic_line(phase+.31*y,13.0,.49)*np.maximum(costa_l,costa_r)
    sat_m=_circles(satellites,1); arrest_m=_paths(arrest,2)
    wandering=_periodic_line(y+8*np.sin((x-seam_x)/17.0),9.0,.55)*_inside(np.abs(x-seam_x),19,5)
    masks=dict(wandering_split_suture=seam,left_diverting_costae=costa_l,right_diverting_costae=costa_r,
               five_puncture_constellations=punctures,puncture_shadow_floors=shadows,
               constellation_satellite_pores=sat_m,costal_arrest_marks=arrest_m,suture_overlap_stitches=wandering,
               costa_cross_lips=cross_lips)
    own=dict(wandering_split_suture=("N",38,220,76),left_diverting_costae=("A",236,66,40),
             right_diverting_costae=("B",58,174,232),five_puncture_constellations=("B",112,48,250),
             puncture_shadow_floors=("N",18,242,22),constellation_satellite_pores=("A",188,198,54),
             costal_arrest_marks=("N",82,210,92),suture_overlap_stitches=("B",88,94,240),
             costa_cross_lips=("A",210,126,62))
    return _pack10(masks,own,phase+.19*y,
                   [(costa_l,242),(costa_r,84),(seam,194),(sat_m,126),(shadows,22)],
                   [(costa_l,74),(costa_r,218),(punctures,38),(arrest_m,174),(wandering,106)],
                   [(punctures,250),(cross_lips,212),(costa_r,166),(sat_m,88),(seam,228)])


def _w10_tiger_beetle() -> _Grammar:
    """A maculation tree controls local corrugation vortices and punctured tips."""
    x,y=_xy(); limbs=[]; nodes=[]
    def branch(p0,ang,length,depth,bias):
        q=np.linspace(0,1,72); px=p0[0]+length*q*np.cos(ang)+bias*14*np.sin(np.pi*q); py=p0[1]+length*q*np.sin(ang)+9*np.sin(2*np.pi*q+depth)
        limbs.append(np.c_[px,py]); nodes.append((float(px[-1]),float(py[-1])))
        if depth:
            branch(nodes[-1],ang-.53+bias*.05,length*.66,depth-1,-bias)
            if depth>1 or bias>0: branch(nodes[-1],ang+.39+bias*.04,length*.59,depth-1,bias)
    branch((-34,454),-.64,276,4,1.0)
    tree=_paths(limbs,4); d=_distance_from(tree)
    vort=np.zeros((_WORK,_WORK),np.float32); swell=np.zeros_like(vort)
    for i,(cx,cy) in enumerate(nodes[2::2]):
        rr=np.hypot(x-cx,y-cy)+5; vort+=(1 if i%2 else -1)*np.arctan2(y-cy,x-cx)*(.35+19/rr)
        swell+=np.exp(-rr/46.0)*np.sin(rr/(4.8+.3*(i%3)))
    corr_phase=d+5.5*vort+7*swell+.008*x*y/32.0
    corr_a=_periodic_line(corr_phase,6.1,.77)
    corr_b=_periodic_line(corr_phase+.27*np.sin((x+y)/33.0)*d,8.2,.74,.25)
    branch_vortices=_periodic_line(vort*8+d*.13,10.0,.53)*_inside(d,31,9)
    tips=_circles([(cx,cy,2.2) for cx,cy in nodes if -4<cx<516 and -4<cy<516],1)
    macula=_inside(d,5.2,2.4); collars=_periodic_line(d,10.7,.48)*_inside(d,35,8)
    hooks=[]
    for i,(cx,cy) in enumerate(nodes[1::3]): hooks.append([(cx-8,cy+4),(cx,cy-5),(cx+10,cy+2)])
    hook_m=_paths(hooks,2)
    masks=dict(asymmetric_maculation_tree=tree,tree_body_macula=macula,local_corrugation_vortices=branch_vortices,
               positive_vortex_corrugations=corr_a,negative_vortex_corrugations=corr_b,
               punctured_branch_tips=tips,branch_distance_collars=collars,terminal_cusp_hooks=hook_m)
    own=dict(asymmetric_maculation_tree=("N",28,230,48),tree_body_macula=("A",222,82,44),
             local_corrugation_vortices=("B",84,162,238),positive_vortex_corrugations=("A",238,54,36),
             negative_vortex_corrugations=("B",56,192,226),punctured_branch_tips=("N",18,244,20),
             branch_distance_collars=("A",178,128,66),terminal_cusp_hooks=("B",124,72,248))
    return _pack10(masks,own,corr_phase+vort,
                   [(corr_a,242),(tree,186),(tips,58),(branch_vortices,212)],
                   [(corr_b,224),(macula,48),(collars,154),(tips,238)],
                   [(tree,246),(branch_vortices,224),(hook_m,188),(tips,96),(macula,138)])


def _w10_stag_carapace() -> _Grammar:
    """Opposing antler channels occlude seven irregular armor plates."""
    x,y=_xy(); left=[]; right=[]; t=np.linspace(0,1,170)
    for side in (-1,1):
        for k in range(3):
            sx=247+side*(19+12*k); sy=542
            px=sx+side*(58+23*k)*np.sin(np.pi*t)+side*(36+17*k)*t
            py=542-590*t+35*np.sin((2.1+k*.4)*np.pi*t+k)
            (left if side<0 else right).append(np.c_[px,py])
    ant_l=_paths(left,5); ant_r=_paths(right,4); ant=np.maximum(ant_l,ant_r)
    plate_specs=[(72,93,86,60,.18),(195,112,96,70,-.24),(339,83,105,59,.12),(452,164,90,76,-.2),
                 (112,306,111,84,-.1),(286,297,123,91,.22),(421,409,127,98,-.15)]
    plate_a=np.zeros((_WORK,_WORK),np.float32); plate_b=np.zeros_like(plate_a); seams=np.zeros_like(plate_a); bosses=[]
    plate_phase=np.zeros_like(plate_a)
    for i,(cx,cy,rx,ry,sk) in enumerate(plate_specs):
        dx=(x-cx)+sk*(y-cy); dy=(y-cy)-.35*sk*(x-cx); er=np.hypot(dx/rx,dy/ry)
        inside=_inside(er,1,.06); rim=_ring(er,.96,.025)
        if i%2: plate_b=np.maximum(plate_b,inside)
        else: plate_a=np.maximum(plate_a,inside)
        seams=np.maximum(seams,rim); plate_phase+=inside*(er*rx+8*np.sin(3*np.arctan2(dy,dx)+i))
        bosses.append((cx+rx*.17*np.cos(i),cy+ry*.14*np.sin(i),3.0))
    visible_a=plate_a*(1-.78*ant); visible_b=plate_b*(1-.78*ant)
    collars_a=_periodic_line(plate_phase+3*np.sin(y/41.0),6.4,.78)*visible_a
    collars_b=_periodic_line(plate_phase-4*np.sin(x/53.0),7.9,.75,.25)*visible_b
    trab=_periodic_line(7*np.arctan2(y-256,x-256)+plate_phase*.15,10.0,.46)*np.maximum(visible_a,visible_b)
    boss_m=_circles(bosses,2); hooks=[]
    for paths in (left,right):
        for p in paths: hooks.append([(p[-18,0],p[-18,1]),(p[-5,0]+(7 if p[-1,0]>256 else -7),p[-5,1]-9),(p[-1,0],p[-1,1])])
    hook_m=_paths(hooks,2)
    masks=dict(left_antler_channels=ant_l,right_antler_channels=ant_r,occluded_armor_plates_a=visible_a,
               occluded_armor_plates_b=visible_b,irregular_plate_seams=seams,dense_plate_collars=np.maximum(collars_a,collars_b),
               plate_trabecular_ribs=trab,plate_boss_rings=boss_m,terminal_antler_hooks=hook_m)
    own=dict(left_antler_channels=("A",232,62,42),right_antler_channels=("B",68,178,236),
             occluded_armor_plates_a=("A",188,118,52),occluded_armor_plates_b=("B",86,146,220),
             irregular_plate_seams=("N",34,226,78),dense_plate_collars=("A",216,84,56),
             plate_trabecular_ribs=("B",116,68,248),plate_boss_rings=("N",22,240,32),terminal_antler_hooks=("B",148,92,238))
    collar=np.maximum(collars_a,collars_b)
    return _pack10(masks,own,plate_phase+.31*_distance_from(ant),
                   [(ant_l,242),(visible_a,174),(collar,214),(boss_m,84)],
                   [(ant_r,218),(visible_b,66),(seams,188),(trab,132)],
                   [(seams,246),(ant_r,188),(hook_m,232),(collar,116)])


def _w10_chrysina_gold() -> _Grammar:
    """Elliptic and teardrop foci meet along a broken Bragg front."""
    x,y=_xy(); e1=np.hypot((x-156)/132,(y-274)/186)
    dx=(x-378)/102; dy=(y-226)/154; theta=np.arctan2(dy,dx); rad=np.hypot(dx,dy)
    teardrop=rad*(1+.34*np.cos(theta))
    focus_phase=71*e1-64*teardrop+9*np.sin(3*theta)+.012*x*y/48.0
    front=_line(focus_phase,2.2)
    gaps=((np.sin((x+y)/37.0)>.18)&(np.cos((x-2*y)/61.0)>-.52)).astype(np.float32)
    broken=front*gaps
    lam_e=np.maximum(_periodic_line(82*e1+4*np.sin(theta*4),6.0,.78),
                     _periodic_line(67*e1-5*np.sin(theta*3),9.3,.62,.25))*(focus_phase<0)
    lam_c=np.maximum(_periodic_line(76*teardrop+5*np.sin(e1*7),7.4,.76,.25),
                     _periodic_line(59*teardrop-6*np.sin(e1*5),10.7,.60))*(focus_phase>=0)
    disloc=_line(np.sin(focus_phase/11.0)+.58*np.sin(theta*5+e1*3),.18)
    arrest=_periodic_line(np.abs(focus_phase)+.23*y,12.0,.50)*_inside(np.abs(focus_phase),35,9)
    pinholes=_circles([(57,418,2),(119,92,2),(224,371,2),(306,96,2),(417,181,2),(469,354,2)],1)
    cuspline=_line((dy*dy)-(.62*np.maximum(-dx,0))**3,.028)
    lips=_periodic_line(focus_phase+.35*x,9.0,.53)*np.maximum(lam_e,lam_c)
    masks=dict(elliptic_focus_lamellae=lam_e,teardrop_cusp_lamellae=lam_c,joined_broken_bragg_front=broken,
               cusp_caustic_spine=cuspline,front_dislocation_scars=disloc,bragg_arrest_bands=arrest,
               authored_focus_pinholes=pinholes,lamellar_overlap_lips=lips)
    own=dict(elliptic_focus_lamellae=("A",240,66,38),teardrop_cusp_lamellae=("B",72,184,232),
             joined_broken_bragg_front=("N",42,214,88),cusp_caustic_spine=("B",124,48,252),
             front_dislocation_scars=("A",194,132,62),bragg_arrest_bands=("B",98,96,238),
             authored_focus_pinholes=("N",18,242,26),lamellar_overlap_lips=("A",218,82,54))
    return _pack10(masks,own,focus_phase+theta,
                   [(lam_e,244),(lam_c,92),(broken,204),(pinholes,48)],
                   [(lam_e,72),(lam_c,220),(disloc,44),(arrest,172)],
                   [(cuspline,252),(lips,224),(lam_c,178),(broken,106)])


def _w10_oil_beetle() -> _Grammar:
    """Deterministically integrated flowlines merge around glands, vortices, and saddles."""
    x,y=_xy(); centers=[(118,121,1.0),(389,107,-.9),(176,381,-1.15),(421,344,.82)]
    saddles=[(255,211,.75),(292,407,-.62)]
    def velocity(px,py):
        vx=1.45+.34*np.sin(py/71.0); vy=.18*np.sin(px/63.0)
        for cx,cy,w in centers:
            dx=px-cx; dy=py-cy; den=dx*dx+dy*dy+310.0; vx+=-w*dy*38/den; vy+=w*dx*38/den
        for cx,cy,w in saddles:
            dx=px-cx; dy=py-cy; den=np.hypot(dx,dy)+23; vx+=w*dx/den; vy-=w*dy/den
        mag=max(.2,float(np.hypot(vx,vy))); return vx/mag,vy/mag
    flows=[]
    for i,sy in enumerate(np.linspace(-18,530,43)):
        px=-18.0; py=float(sy+13*np.sin(i*.73)); pts=[]
        for step in range(330):
            if step%2==0: pts.append((px,py))
            vx,vy=velocity(px,py); px+=vx*2.05; py+=vy*2.05
            if px>530 or py<-30 or py>542: break
        flows.append(pts)
    flow_m=_paths(flows,2); d=_distance_from(flow_m)
    stream_a=_periodic_line(d+.014*x*np.sin(y/47.0),6.0,.78)
    stream_b=_periodic_line(d-.017*y*np.sin(x/61.0),7.8,.75,.25)
    glands=np.zeros((_WORK,_WORK),np.float32); gland_lips=np.zeros_like(glands)
    for i,(cx,cy,w) in enumerate(centers):
        rr=np.hypot((x-cx)/(19+3*i),(y-cy)/(13+2*(i%2))); glands=np.maximum(glands,_inside(rr,1,.10)); gland_lips=np.maximum(gland_lips,_ring(rr,.87,.055))
    saddle_cusps=np.zeros_like(glands)
    for cx,cy,w in saddles: saddle_cusps=np.maximum(saddle_cusps,_line(((x-cx)/29)**2-((y-cy)/23)**2,.14))
    mergers=np.minimum(cv2.dilate(flow_m,np.ones((7,7),np.uint8)),_periodic_line(x+1.7*y,23,.38))
    caustic=_periodic_line(d+.41*np.sin((x+y)/29.0)*d,11.0,.51)*np.maximum(stream_a,stream_b)
    ducts=_paths([[(118,121),(187,164),(255,211)],[(389,107),(331,162),(255,211)],[(176,381),(241,411),(292,407)],[(421,344),(365,387),(292,407)]],3)
    masks=dict(integrated_primary_streamlines=flow_m,positive_oil_stream_bands=stream_a,negative_oil_stream_bands=stream_b,
               four_gland_vortices=glands,gland_lip_rings=gland_lips,two_saddle_cusps=saddle_cusps,
               authored_duct_mergers=np.maximum(mergers,ducts),flow_attached_caustics=caustic)
    own=dict(integrated_primary_streamlines=("A",232,58,40),positive_oil_stream_bands=("A",202,138,56),
             negative_oil_stream_bands=("B",62,194,226),four_gland_vortices=("N",24,240,28),
             gland_lip_rings=("B",128,46,250),two_saddle_cusps=("A",186,108,64),
             authored_duct_mergers=("N",78,216,86),flow_attached_caustics=("B",96,82,244))
    return _pack10(masks,own,d+.17*x+2*np.sin(y/39.0),
                   [(stream_a,242),(flow_m,188),(gland_lips,88),(ducts,214)],
                   [(stream_b,222),(glands,42),(saddle_cusps,178),(mergers,106)],
                   [(caustic,250),(stream_b,184),(gland_lips,232),(ducts,128)])


def _w10_firefly_shell() -> _Grammar:
    """A full-frame curved abdomen carries unequal articulated lantern chambers."""
    x,y=_xy(); center=248+71*np.sin((y-38)/181.0)+23*np.sin(y/57.0); lateral=x-center
    width=214-38*np.cos(y/157.0)+16*np.sin(y/43.0); body=_inside(np.abs(lateral),width,8)
    joints_y=[-18,61,137,224,303,397,526]; joints=[]
    for i,jy in enumerate(joints_y):
        curve=jy+11*np.sin((x-center)/71.0+i*.8)+.0007*(x-center)**2*(-1 if i%2 else 1)
        joints.append(_line(y-curve,2.4)*body)
    joint_m=np.maximum.reduce(joints)
    seg_idx=np.zeros((_WORK,_WORK),np.float32)
    for j in joints_y[1:-1]: seg_idx+=(y>j).astype(np.float32)
    window_phase=np.abs(lateral)*(1+.07*np.sin(y/47.0))+seg_idx*9+5*np.sin((y+seg_idx*23)/31.0)
    window_a=_periodic_line(window_phase,6.2,.78)*body
    window_b=_periodic_line(window_phase+.29*y+7*np.sin(lateral/53.0),8.1,.74,.25)*body
    pulses=_periodic_line(y+13*np.sin(lateral/67.0)+seg_idx*17,19.0+1.6*seg_idx,.48)*np.maximum(window_a,window_b)
    lateral_ribs=_periodic_line(lateral+.15*y*np.sin(y/91.0),12.0,.52)*body
    lumen=_inside(np.abs(lateral),38+8*np.sin(y/83.0),5)*body
    spiracles=[]
    for i,jy in enumerate((37,99,179,263,352,451)):
        center_j=248+71*np.sin((jy-38)/181.0)+23*np.sin(jy/57.0)
        width_j=214-38*np.cos(jy/157.0)+16*np.sin(jy/43.0)
        for side in (-1,1): spiracles.append((float(center_j+side*(width_j-18)),jy,2.2))
    spiracle_m=_circles(spiracles,1); edge=_edge(body,2)
    masks=dict(full_frame_abdomen_body=body,unequal_articulation_joints=joint_m,positive_nested_lantern_windows=window_a,
               negative_nested_lantern_windows=window_b,nonperiodic_segment_pulses=pulses,curved_lateral_ribs=lateral_ribs,
               central_lantern_lumen=lumen,paired_segment_spiracles=spiracle_m,scalloped_abdomen_edge=edge)
    own=dict(full_frame_abdomen_body=("N",32,214,70),unequal_articulation_joints=("A",224,66,44),
             positive_nested_lantern_windows=("A",242,104,38),negative_nested_lantern_windows=("B",62,188,232),
             nonperiodic_segment_pulses=("B",118,72,250),curved_lateral_ribs=("A",188,146,58),
             central_lantern_lumen=("N",18,238,26),paired_segment_spiracles=("B",86,48,246),
             scalloped_abdomen_edge=("N",102,224,84))
    return _pack10(masks,own,window_phase+seg_idx*.13,
                   [(window_a,244),(joint_m,192),(spiracle_m,72),(pulses,216)],
                   [(window_b,224),(lumen,42),(lateral_ribs,158),(edge,98)],
                   [(pulses,250),(window_b,184),(joint_m,226),(spiracle_m,116)])


def _w10_weevil_pit() -> _Grammar:
    """Three unequal whorled strial basins feed a tapered rostrum throat."""
    x,y=_xy(); basins=[(126,142,104,81,1.0),(351,195,137,103,-.8),(226,391,151,98,1.15)]
    phases=[]; domains=[]; calluses=[]
    for i,(cx,cy,rx,ry,w) in enumerate(basins):
        dx=(x-cx)/rx; dy=(y-cy)/ry; rr=np.hypot(dx,dy); th=np.arctan2(dy,dx)
        phases.append(rr*76+w*17*th+6*np.sin((i+2)*th)); domains.append(np.exp(-1.9*rr))
        calluses.append(_inside(rr,.24,.06))
    stack=np.stack(domains); owner=np.argmax(stack,axis=0)
    stria_parts=[]; counter_parts=[]
    for i,ph in enumerate(phases):
        dom=owner==i; stria_parts.append(_periodic_line(ph,6.1+i*.8,.78,.13*i)*dom)
        counter_parts.append(_periodic_line(ph+.33*(x-y),10.7+i,.54,.25)*dom)
    stria_a=np.maximum.reduce(stria_parts); cross=np.maximum.reduce(counter_parts); callus=np.maximum.reduce(calluses)
    throat_center=271+34*np.sin((y-274)/91.0); throat_width=np.clip(116-.31*(y-238),26,116)
    throat=_inside(np.abs(x-throat_center),throat_width,5)*(y>220)
    throat_striae=_periodic_line(np.abs(x-throat_center)+.16*y,7.0,.76)*throat
    bifurcations=_line(np.sin((phases[0]-phases[1])/13.0)+.43*np.sin(phases[2]/9.0),.16)*np.maximum(stria_a,throat_striae)
    boundaries=np.zeros((_WORK,_WORK),np.float32)
    for i in range(3): boundaries=np.maximum(boundaries,_edge((owner==i).astype(np.float32),1))
    leaf_scales=_periodic_line(x+.47*y+8*np.sin(y/41.0),8.7,.58)*cv2.dilate(boundaries,np.ones((17,17),np.uint8))
    term=np.minimum(stria_a,cv2.dilate(callus,np.ones((9,9),np.uint8)))
    masks=dict(three_whorled_strial_basins=stria_a,basin_counter_striae=cross,raised_callus_islands=callus,
               tapered_rostrum_throat=throat,rostrum_longitudinal_striae=throat_striae,
               strial_bifurcation_scars=bifurcations,boundary_only_leaf_scales=leaf_scales,callus_stria_terminations=term)
    own=dict(three_whorled_strial_basins=("A",236,68,42),basin_counter_striae=("B",66,184,230),
             raised_callus_islands=("N",26,238,30),tapered_rostrum_throat=("A",178,112,58),
             rostrum_longitudinal_striae=("B",92,156,242),strial_bifurcation_scars=("N",82,218,88),
             boundary_only_leaf_scales=("A",214,138,52),callus_stria_terminations=("B",128,52,250))
    total_phase=np.choose(owner,phases)
    return _pack10(masks,own,total_phase+.14*y,
                   [(stria_a,242),(throat_striae,184),(callus,62),(bifurcations,212)],
                   [(cross,222),(throat,54),(leaf_scales,168),(term,238)],
                   [(boundaries,248),(leaf_scales,218),(callus,224),(bifurcations,92),(cross,166)])


def _w10_ground_beetle() -> _Grammar:
    """One asymmetric branching keel carries merging ribs and shoulder hooks."""
    x,y=_xy(); q=np.linspace(-.08,1.08,300)
    cx=256+49*np.sin(1.45*np.pi*q)+21*np.sin(5*np.pi*q); cy=-24+558*q
    main=np.c_[cx,cy]; branches=[main]; forks=[]
    for i,j in enumerate((62,108,167,219)):
        bx,by=float(cx[j]),float(cy[j]); side=-1 if i in (0,3) else 1
        tq=np.linspace(0,1,110); px=bx+side*(151-13*i)*tq+side*17*np.sin(np.pi*tq); py=by+(62+8*i)*tq+12*np.sin(2*np.pi*tq+i)
        branches.append(np.c_[px,py]); forks.append([(bx,by),(px[18],py[18]),(px[39],py[39])])
    carina=_paths(branches,5); d=_distance_from(carina)
    ribs=[]; hooks=[]
    for i,j in enumerate(range(15,286,9)):
        bx,by=float(cx[j]),float(cy[j]); slope=(cx[min(j+2,299)]-cx[max(j-2,0)])/(cy[min(j+2,299)]-cy[max(j-2,0)]+1e-4)
        side=-1 if i%3 else 1; reach=118+31*np.sin(i*.73)
        ex=bx+side*reach; ey=by-side*slope*reach+14*np.sin(i*.91)
        ribs.append([(bx,by),(bx+side*reach*.53,by-side*slope*reach*.43+9*np.sin(i)),(ex,ey)])
        if i%4==1: hooks.append([(ex-7*side,ey-5),(ex,ey),(ex-11*side,ey+11)])
    rib_m=_paths(ribs,2); hook_m=_paths(hooks,2)
    collars_a=_periodic_line(d+4*np.sin(y/43.0),6.2,.78)
    collars_b=_periodic_line(d-.21*x+5*np.sin(y/71.0),8.4,.73,.25)
    serr=_periodic_line(x+.37*y,5.1,.57)*cv2.dilate(rib_m,np.ones((9,9),np.uint8))
    merge=np.maximum(_paths(forks,3),np.minimum(rib_m,cv2.dilate(carina,np.ones((11,11),np.uint8))))
    shoulder=_periodic_line(d+.43*y,14.0,.47)*_inside(d,61,14)
    masks=dict(asymmetric_branching_carina=carina,irregular_curved_ribs=rib_m,positive_keel_collars=collars_a,
               negative_keel_collars=collars_b,rib_serration_teeth=serr,rib_merge_junctions=merge,
               terminal_shoulder_hooks=hook_m,carina_shoulder_bands=shoulder)
    own=dict(asymmetric_branching_carina=("N",42,218,76),irregular_curved_ribs=("A",228,64,42),
             positive_keel_collars=("A",202,142,56),negative_keel_collars=("B",62,188,232),
             rib_serration_teeth=("B",108,86,244),rib_merge_junctions=("N",24,238,36),
             terminal_shoulder_hooks=("A",188,118,62),carina_shoulder_bands=("B",132,54,250))
    return _pack10(masks,own,d+.12*x+np.sin(y/31.0),
                   [(collars_a,242),(carina,192),(serr,116),(merge,216)],
                   [(collars_b,222),(rib_m,58),(shoulder,168),(hook_m,238)],
                   [(rib_m,246),(collars_b,178),(hook_m,226),(merge,96)])


def _w10_scarab_horn() -> _Grammar:
    """A cropped logarithmic horn crosses the canvas and bifurcates twice."""
    x,y=_xy(); q=np.linspace(-.12,1.15,340)
    px=-31+574*q; py=472-117*np.log1p(np.maximum(q+.14,.01)*7.4)+54*np.sin(1.7*np.pi*q)
    trunk=np.c_[px,py]; forks=[trunk]
    for j,side,reach in ((137,-1,176),(225,1,143)):
        bx,by=float(px[j]),float(py[j]); tq=np.linspace(0,1,140)
        fx=bx+reach*tq; fy=by+side*(109*tq+43*np.sin(np.pi*tq))+18*np.sin(3*np.pi*tq)
        forks.append(np.c_[fx,fy])
    horn_core=_paths(forks,7); d=_distance_from(horn_core)
    cortex=_inside(d,31+5*np.sin((x+y)/67.0),7)
    inner=_inside(d,17+3*np.sin(y/41.0),5)
    collars_a=_periodic_line(d+2*np.sin(x/43.0),5.9,.79)
    collars_b=_periodic_line(d-.17*y+3*np.sin(x/71.0),7.7,.75,.25)
    trab=[]
    for path in forks:
        for j in range(18,len(path)-18,13):
            bx,by=path[j]; dx=path[j+2,0]-path[j-2,0]; dy=path[j+2,1]-path[j-2,1]; mag=np.hypot(dx,dy)+1e-4
            nx,ny=-dy/mag,dx/mag; span=13+(j%17)
            trab.append([(bx-nx*span,by-ny*span),(bx,by),(bx+nx*span,by+ny*span)])
    trab_m=_paths(trab,1); cortex_lip=_edge(cortex,2); marrow=_periodic_line(d+.39*x,11.2,.52)*inner
    bif_nodes=_circles([(px[137],py[137],4),(px[225],py[225],4)],2)
    hook=_paths([[(px[267],py[267]),(px[286]+12,py[286]-17),(px[303],py[303])]],3)
    masks=dict(logarithmic_cross_frame_horn=horn_core,variable_width_cortex=cortex,inner_marrow_channel=inner,
               positive_cortex_collars=collars_a,negative_cortex_collars=collars_b,dense_trabecular_microbranches=trab_m,
               cortex_boundary_lip=cortex_lip,bifurcation_node_rings=bif_nodes,terminal_horn_hook=hook,
               marrow_cross_ties=marrow)
    own=dict(logarithmic_cross_frame_horn=("A",238,58,40),variable_width_cortex=("A",174,126,54),
             inner_marrow_channel=("N",22,238,28),positive_cortex_collars=("A",216,84,48),
             negative_cortex_collars=("B",64,194,230),dense_trabecular_microbranches=("B",104,102,244),
             cortex_boundary_lip=("N",86,220,92),bifurcation_node_rings=("B",132,46,250),
             terminal_horn_hook=("A",198,68,58),marrow_cross_ties=("B",92,164,226))
    return _pack10(masks,own,d+.16*x-2*np.sin(y/43.0),
                   [(collars_a,244),(horn_core,196),(trab_m,126),(bif_nodes,74)],
                   [(collars_b,222),(inner,48),(cortex_lip,174),(marrow,112)],
                   [(cortex_lip,248),(collars_b,182),(hook,232),(trab_m,98)])


def _w10_ladybird_dome() -> _Grammar:
    """A cropped ellipsoidal elytron carries distorted maculae and curved pore chains."""
    x,y=_xy(); cx,cy=284,271; dx=(x-cx)/337; dy=(y-cy)/286; er=np.hypot(dx+.11*dy,dy-.07*dx)
    dome=_inside(er,1.0,.05); seam_x=259+24*np.sin((y-36)/83.0)+.00022*(y-276)**2
    seam=_line(x-seam_x,3.0)*dome
    mac_specs=[(42,78,58,43,.25),(173,142,51,67,-.18),(392,91,72,47,.12),(476,254,69,83,-.2),
               (109,361,77,55,.17),(329,402,63,79,-.14)]
    mac=np.zeros((_WORK,_WORK),np.float32); scallop=np.zeros_like(mac); glints=np.zeros_like(mac)
    for i,(mx,my,rx,ry,sk) in enumerate(mac_specs):
        ddx=(x-mx)+sk*(y-my); ddy=(y-my)-.3*sk*(x-mx); mr=np.hypot(ddx/rx,ddy/ry)
        boundary=1+.08*np.sin(3*np.arctan2(ddy,ddx)+i)+.05*np.sin(5*np.arctan2(ddy,ddx)-i)
        mi=_inside(mr,boundary,.06)*dome; mac=np.maximum(mac,mi); scallop=np.maximum(scallop,_ring(mr,boundary,.035)*dome)
        glints=np.maximum(glints,_ring(mr,.62,.025)*mi)
    theta=np.arctan2(dy,dx); pore_phase=er*211+17*theta+8*np.sin(4*theta)+6*np.sin(er*19)
    pore_chains_a=_periodic_line(pore_phase,6.1,.76)*dome
    pore_chains_b=_periodic_line(pore_phase+.31*x-5*np.sin(theta*7),8.3,.72,.25)*dome
    pores=np.minimum(np.maximum(pore_chains_a,pore_chains_b),_periodic_line(theta*97+er*23,5.0,.55))
    dome_glint=_periodic_line(er*121+theta*11,13.0,.42)*dome*(1-mac)
    shadow=_edge(dome,3); suture_stitch=_periodic_line(y+6*np.sin(x/31.0),8.0,.52)*_inside(np.abs(x-seam_x),15,4)
    masks=dict(cropped_ellipsoidal_elytron=dome,off_axis_wandering_suture=seam,distorted_cropped_maculae=mac,
               scalloped_macula_shadows=scallop,positive_curved_pore_chains=pore_chains_a,negative_curved_pore_chains=pore_chains_b,
               ordered_pore_intersections=pores,macula_attached_glints=glints,elytron_edge_shadow=shadow,suture_microstitches=suture_stitch)
    own=dict(cropped_ellipsoidal_elytron=("A",178,118,52),off_axis_wandering_suture=("N",42,218,78),
             distorted_cropped_maculae=("N",18,242,22),scalloped_macula_shadows=("B",92,48,248),
             positive_curved_pore_chains=("A",238,72,40),negative_curved_pore_chains=("B",64,184,232),
             ordered_pore_intersections=("A",206,146,58),macula_attached_glints=("B",126,62,250),
             elytron_edge_shadow=("N",86,226,92),suture_microstitches=("B",108,104,242))
    return _pack10(masks,own,pore_phase+.21*y,
                   [(pore_chains_a,244),(seam,186),(glints,82),(mac,24)],
                   [(pore_chains_b,220),(mac,44),(scallop,184),(shadow,108)],
                   [(glints,250),(pore_chains_b,178),(suture_stitch,226),(scallop,116)])


def _w10_hummingbird_gorget() -> _Grammar:
    """An asymmetric C-shaped throat shock separates three platelet-flow domains."""
    x,y=_xy(); dx=(x-319)/228; dy=(y-271)/196; rr=np.hypot(dx,dy); th=np.arctan2(dy,dx)
    c_gate=_inside(np.abs(th-.12),2.58,.18); shock=_ring(rr,.83+.07*np.sin(2*th)+.035*np.sin(5*th),.025)*c_gate
    domain0=(rr<.79)&(th<.72); domain1=((rr>=.72)&(th>-1.95)); domain2=~(domain0|domain1)
    # Each phase changes orientation continuously; none points to a shared root.
    ph0=x*np.cos(.24+.47*np.sin(y/127.0))+y*np.sin(.24+.47*np.sin(y/127.0))+8*np.sin((x-y)/53.0)
    ph1=x*np.cos(1.37+.36*np.sin(x/109.0))+y*np.sin(1.37+.36*np.sin(x/109.0))+7*np.sin((x+y)/61.0)
    ph2=x*np.cos(-.71+.42*np.sin((x+y)/151.0))+y*np.sin(-.71+.42*np.sin((x+y)/151.0))+9*np.sin(y/47.0)
    plates_a=np.maximum.reduce([_periodic_line(ph0,6.0,.78)*domain0,_periodic_line(ph1,7.1,.76,.25)*domain1,
                                _periodic_line(ph2,8.2,.74)*domain2])
    plates_b=np.maximum.reduce([_periodic_line(ph0+.31*y,9.2,.61,.25)*domain0,
                                _periodic_line(ph1-.27*x,10.4,.59)*domain1,
                                _periodic_line(ph2+.19*(x-y),11.3,.57,.25)*domain2])
    rachises=[]; barbs=[]
    for i,(sx,sy,ang) in enumerate(((22,84,.19),(73,421,-.43),(246,522,-1.24),(512,377,2.77),(474,19,2.13))):
        q=np.linspace(0,1,130); px=sx+186*q*np.cos(ang)+23*np.sin(np.pi*q+i); py=sy+176*q*np.sin(ang)+18*np.sin(2*np.pi*q+i)
        rachises.append(np.c_[px,py])
        for j in range(12,121,13+i%3):
            bx,by=float(px[j]),float(py[j]); barbs.append([(bx-5*np.sin(ang),by+5*np.cos(ang)),(bx+7*np.sin(ang),by-7*np.cos(ang))])
    rach_m=_paths(rachises,3); barb_m=_paths(barbs,1)
    shock_lips=_periodic_line((rr-.83)*147+8*np.sin(th*4),8.0,.54)*_inside(np.abs(rr-.83),.15,.04)*c_gate
    dislocations=_line(np.sin((ph0-ph1)/19.0)+.5*np.sin((ph2-ph0)/23.0),.17)*np.maximum(plates_a,plates_b)
    masks=dict(asymmetric_c_throat_shock=shock,three_domain_primary_platelets=plates_a,three_domain_counter_platelets=plates_b,
               independent_curved_rachises=rach_m,rachis_attached_barbs=barb_m,shockwave_overlap_lips=shock_lips,
               orientation_domain_dislocations=dislocations,c_gate_terminal_cusps=_circles([(99,92,3),(112,445,3)],2))
    own=dict(asymmetric_c_throat_shock=("N",40,216,84),three_domain_primary_platelets=("A",242,62,38),
             three_domain_counter_platelets=("B",62,192,232),independent_curved_rachises=("A",194,112,54),
             rachis_attached_barbs=("B",112,86,246),shockwave_overlap_lips=("B",136,48,250),
             orientation_domain_dislocations=("N",24,238,34),c_gate_terminal_cusps=("A",218,146,58))
    cusp=masks['c_gate_terminal_cusps']
    return _pack10(masks,own,np.where(domain0,ph0,np.where(domain1,ph1,ph2)),
                   [(plates_a,244),(rach_m,188),(shock,212),(cusp,74)],
                   [(plates_b,222),(dislocations,42),(barb_m,168),(shock_lips,104)],
                   [(shock_lips,250),(plates_b,182),(rach_m,226),(cusp,116)])


def _w10_peacock_eye() -> _Grammar:
    """One immense cropped ocellus and two unlike eyes interrupt a branching plume."""
    x,y=_xy(); dx=(x+61)/334; dy=(y-258)/267; th=np.arctan2(dy,dx); giant=np.hypot(dx,dy)
    giant_boundary=.86+.10*np.sin(2*th)+.055*np.sin(5*th)
    giant_rim=_ring(giant,giant_boundary,.018); giant_cres=_ring(giant,.58+.08*np.cos(th-.4),.023)*(th>-.95)
    giant_pupil=_inside(np.hypot((x-41)/57,(y-276)/89),1,.10)
    e2=np.hypot((x-376)/71,(y-106)/49); eye2=np.maximum(_ring(e2,.92+.08*np.sin(np.arctan2(y-106,x-376)*3),.035),_inside(e2,.31,.07))
    e3=np.hypot((x-417)/94,(y-405)/61); eye3=np.maximum(_ring(e3,.82+.11*np.sin(np.arctan2(y-405,x-417)*2+.7),.04),_ring(e3,.43,.04))
    stems=[]; twigs=[]
    roots=[(-18,35),(-24,151),(-11,362),(47,529),(198,529),(523,253)]
    for i,(sx,sy) in enumerate(roots):
        q=np.linspace(0,1,150); ex=241+67*np.cos(i*.81); ey=257+93*np.sin(i*.67)
        px=sx+(ex-sx)*q+31*np.sin(np.pi*q+i*.4); py=sy+(ey-sy)*q+24*np.sin(2*np.pi*q+i)
        stems.append(np.c_[px,py])
        for j in range(18,142,15+i%3):
            bx,by=float(px[j]),float(py[j]); side=-1 if (i+j)%2 else 1
            twigs.append([(bx,by),(bx+side*(18+j%9),by-9+side*4),(bx+side*(33+j%13),by-14+side*7)])
    stem_m=_paths(stems,3); twig_m=_paths(twigs,1); d=_distance_from(np.maximum(stem_m,twig_m))
    plume_a=_periodic_line(d+4*np.sin((x+y)/43.0),6.1,.78)
    plume_b=_periodic_line(d-.21*x+5*np.sin(y/59.0),8.4,.73,.25)
    plume_hooks=np.minimum(plume_a,_periodic_line(x-.63*y,5.2,.54))*cv2.dilate(twig_m,np.ones((13,13),np.uint8))
    ocellus=np.maximum.reduce([giant_rim,giant_cres,giant_pupil]); eyes=np.maximum(eye2,eye3)
    masks=dict(immense_off_canvas_ocellus=ocellus,irregular_giant_ocellus_rim=giant_rim,two_nonmatching_secondary_eyes=eyes,
               branching_plume_stems=stem_m,plume_bifurcation_twigs=twig_m,positive_plume_lamellae=plume_a,
               negative_plume_lamellae=plume_b,twig_attached_barb_hooks=plume_hooks)
    own=dict(immense_off_canvas_ocellus=("B",122,48,250),irregular_giant_ocellus_rim=("A",224,78,42),
             two_nonmatching_secondary_eyes=("N",30,236,36),branching_plume_stems=("A",192,116,58),
             plume_bifurcation_twigs=("B",84,156,240),positive_plume_lamellae=("A",240,64,40),
             negative_plume_lamellae=("B",64,194,230),twig_attached_barb_hooks=("N",102,218,86))
    return _pack10(masks,own,d+th*9,
                   [(plume_a,244),(stem_m,188),(giant_rim,212),(giant_pupil,44)],
                   [(plume_b,222),(eyes,52),(twig_m,168),(plume_hooks,104)],
                   [(ocellus,250),(plume_b,178),(eye2,226),(eye3,116)])


def _w10_starling_sheen() -> _Grammar:
    """Two crossing feather-vortex sheets braid only at authored collisions."""
    x,y=_xy(); sheet_a=[]; sheet_b=[]
    for i in range(9):
        q=np.linspace(-.08,1.08,220); px=-25+567*q; py=61+i*46+41*np.sin(1.45*np.pi*q+i*.34)+13*np.sin(5*np.pi*q+i)
        sheet_a.append(np.c_[px,py])
    for i in range(8):
        q=np.linspace(-.08,1.08,220); py=-24+559*q; px=54+i*57+47*np.sin(1.25*np.pi*q+i*.47)-16*np.sin(4*np.pi*q+i)
        sheet_b.append(np.c_[px,py])
    rach_a=_paths(sheet_a,3); rach_b=_paths(sheet_b,3); da=_distance_from(rach_a); db=_distance_from(rach_b)
    vane_a=_periodic_line(da+.19*x+5*np.sin(y/43.0),6.2,.78)
    vane_b=_periodic_line(db-.17*y+6*np.sin(x/57.0),7.7,.75,.25)
    crossings=np.minimum(cv2.dilate(rach_a,np.ones((13,13),np.uint8)),cv2.dilate(rach_b,np.ones((13,13),np.uint8)))
    pockets=_inside(crossings,.35,.12)*_line(np.sin((x+y)/13.0)+.4*np.sin((x-y)/9.0),.19)
    braid=np.maximum(rach_a*(1-.72*cv2.dilate(rach_b,np.ones((7,7),np.uint8))),
                     rach_b*(1-.72*cv2.dilate(rach_a,np.ones((7,7),np.uint8))))
    hooks=np.minimum(np.maximum(vane_a,vane_b),_periodic_line(x+y+7*np.sin(x/31.0),5.1,.55))*cv2.dilate(crossings,np.ones((19,19),np.uint8))
    branchlets=[]
    for i,p in enumerate(sheet_a[::2]+sheet_b[1::2]):
        for j in (51+i%7,112+i%9,174-i%11):
            bx,by=p[j]; branchlets.append([(bx,by),(bx+17*np.cos(i),by+17*np.sin(i)),(bx+31*np.cos(i+.3),by+31*np.sin(i+.3))])
    branch_m=_paths(branchlets,1); lips=np.minimum(vane_a,vane_b)
    masks=dict(first_curved_feather_sheet=rach_a,second_crossing_feather_sheet=rach_b,first_sheet_vanes=vane_a,
               second_sheet_vanes=vane_b,authored_crossing_pockets=pockets,alternating_braid_occlusion=braid,
               collision_only_barb_hooks=hooks,rachis_bifurcation_branchlets=branch_m,crossing_overlap_lips=lips)
    own=dict(first_curved_feather_sheet=("A",232,64,42),second_crossing_feather_sheet=("B",66,184,232),
             first_sheet_vanes=("A",242,94,38),second_sheet_vanes=("B",58,198,228),
             authored_crossing_pockets=("N",22,240,28),alternating_braid_occlusion=("A",184,126,56),
             collision_only_barb_hooks=("B",112,72,248),rachis_bifurcation_branchlets=("N",88,218,86),
             crossing_overlap_lips=("B",134,48,250))
    return _pack10(masks,own,da-db+.13*x,
                   [(vane_a,244),(rach_a,188),(branch_m,112),(pockets,54)],
                   [(vane_b,222),(rach_b,62),(hooks,172),(crossings,104)],
                   [(lips,250),(vane_b,178),(braid,226),(pockets,116)])


def _w10_magpie_wing() -> _Grammar:
    """Seven unequal diagonal shear blades overlap as a multi-edge staircase."""
    x,y=_xy(); blade_a=np.zeros((_WORK,_WORK),np.float32); blade_b=np.zeros_like(blade_a); edges=np.zeros_like(blade_a)
    barbs=np.zeros_like(blade_a); overlaps=np.zeros_like(blade_a); prior=np.zeros_like(blade_a)
    specs=[(-84,92,.63,37),(16,32,.78,52),(84,117,.56,44),(169,69,.91,61),(236,146,.68,49),(323,98,.83,57),(401,173,.59,46)]
    for i,(anchor,base,slope,half) in enumerate(specs):
        center=base+slope*(x-anchor)+19*np.sin((x+31*i)/(61+5*i))+8*np.sin(x/(19+2*i))
        half_eff=half*1.34
        extent=((x>anchor-112)&(x<anchor+424)).astype(np.float32)
        blade=_inside(np.abs(y-center),half_eff,5)*extent
        edge=_line(np.abs(y-center)-half_eff,2.0)*extent
        local=_periodic_line((y-center)*(1+.0016*x)+.23*x,5.7+.45*i,.77,.25*(i%2))*blade
        overlaps=np.maximum(overlaps,np.minimum(prior,blade)); prior=np.maximum(prior,blade)
        edges=np.maximum(edges,edge); barbs=np.maximum(barbs,local)
        if i%2: blade_b=np.maximum(blade_b,blade)
        else: blade_a=np.maximum(blade_a,blade)
    deformed_bars=_periodic_line(y-.71*x+17*np.sin(x/47.0)+11*np.sin(y/71.0),11.0,.55)*np.maximum(blade_a,blade_b)
    hooks=np.minimum(barbs,_periodic_line(x+1.7*y,5.0,.53))*cv2.dilate(edges,np.ones((11,11),np.uint8))
    anchors=_circles([(0,92,3),(16,44,3),(84,164,3),(169,131,3),(236,209,3),(323,163,3),(506,481,3)],2)
    shear=_line(np.sin((y-.66*x)/17.0)+.47*np.sin((x+y)/29.0),.18)*overlaps
    edge_distance=_distance_from(edges)
    wakes=_periodic_line(edge_distance+.19*x-.11*y+5*np.sin((x+y)/47.0),7.1,.74)*_inside(edge_distance,83,15)
    masks=dict(alternating_shear_blades_a=blade_a,alternating_shear_blades_b=blade_b,unequal_blade_edges=edges,
               dense_blade_attached_barbs=barbs,deformed_silver_crossbars=deformed_bars,overlap_shadow_pockets=overlaps,
               edge_only_barb_hooks=hooks,multiple_edge_anchor_nodes=anchors,collision_shear_scars=shear,
               blade_edge_shear_wakes=wakes)
    own=dict(alternating_shear_blades_a=("A",214,116,54),alternating_shear_blades_b=("B",82,158,236),
             unequal_blade_edges=("N",44,216,84),dense_blade_attached_barbs=("A",242,64,38),
             deformed_silver_crossbars=("B",136,92,244),overlap_shadow_pockets=("N",22,240,26),
             edge_only_barb_hooks=("B",112,52,250),multiple_edge_anchor_nodes=("A",188,142,62),
             collision_shear_scars=("N",94,224,88),blade_edge_shear_wakes=("A",204,132,64))
    return _pack10(masks,own,barbs+.17*x-.11*y,
                   [(barbs,244),(wakes,172),(blade_a,164),(edges,198),(anchors,72)],
                   [(blade_b,218),(wakes,86),(overlaps,42),(deformed_bars,174),(hooks,106)],
                   [(edges,248),(wakes,198),(deformed_bars,188),(hooks,226),(shear,116)])


def _w10_duck_speculum() -> _Grammar:
    """A continuous curved speculum ribbon merges four tapered flow lobes."""
    x,y=_xy(); center=260+67*np.sin((x-22)/137.0)+29*np.sin(x/47.0); width=177+25*np.sin(x/89.0)+16*np.sin(x/31.0)
    signed=y-center; ribbon=_inside(np.abs(signed),width,7)
    lobes=np.zeros((_WORK,_WORK),np.float32); lobe_edges=np.zeros_like(lobes)
    lobe_specs=[(64,184,151,89,-.18),(183,266,174,102,.14),(337,236,164,111,-.11),(475,326,151,96,.19)]
    for i,(cx,cy,rx,ry,sk) in enumerate(lobe_specs):
        dx=(x-cx)+sk*(y-cy); dy=(y-cy)-.3*sk*(x-cx); lr=np.hypot(dx/rx,dy/ry)
        taper=1-.18*np.cos(np.arctan2(dy,dx)+i); li=_inside(lr,taper,.06)*ribbon
        lobes=np.maximum(lobes,li); lobe_edges=np.maximum(lobe_edges,_ring(lr,taper,.032)*ribbon)
    flow=signed*(1+.0012*x)+9*np.sin(x/43.0)+5*np.sin((x+y)/71.0)
    rach_a=_periodic_line(flow,6.1,.79)*ribbon
    rach_b=_periodic_line(flow+.27*x-8*np.sin(y/53.0),8.0,.75,.25)*ribbon
    bars_top=_line(signed+width-13-8*np.sin(x/37.0),2.3)
    bars_bottom=_line(signed-width+15+7*np.sin(x/43.0),2.3)
    white_bars=np.maximum(bars_top,bars_bottom)
    merge_lips=np.minimum(lobes,_periodic_line(flow+.43*y,12.0,.52))
    hooks=np.minimum(np.maximum(rach_a,rach_b),_periodic_line(x-.57*y+7*np.sin(x/29.0),5.0,.55))*ribbon
    terminal=[]
    for i,(cx,cy,rx,ry,sk) in enumerate(lobe_specs): terminal.append([(cx+rx*.62,cy-ry*.18),(cx+rx*.76,cy),(cx+rx*.61,cy+ry*.21)])
    terminal_m=_paths(terminal,2); edge=_edge(ribbon,2)
    masks=dict(continuous_curved_speculum_ribbon=ribbon,four_merging_tapered_lobes=lobes,irregular_white_boundary_bars=white_bars,
               positive_flow_rachises=rach_a,negative_flow_rachises=rach_b,lobe_merge_overlap_lips=merge_lips,
               flow_following_barb_hooks=hooks,tapered_lobe_terminal_hooks=terminal_m,scalloped_ribbon_edge=edge,
               individual_lobe_edges=lobe_edges)
    own=dict(continuous_curved_speculum_ribbon=("A",184,122,54),four_merging_tapered_lobes=("B",86,148,232),
             irregular_white_boundary_bars=("N",48,208,96),positive_flow_rachises=("A",242,62,38),
             negative_flow_rachises=("B",62,194,230),lobe_merge_overlap_lips=("B",128,50,250),
             flow_following_barb_hooks=("A",206,146,58),tapered_lobe_terminal_hooks=("N",24,238,32),
             scalloped_ribbon_edge=("B",104,82,244),individual_lobe_edges=("A",218,102,64))
    return _pack10(masks,own,flow+.15*x,
                   [(rach_a,244),(lobes,168),(white_bars,198),(terminal_m,72)],
                   [(rach_b,222),(ribbon,64),(hooks,174),(edge,104)],
                   [(white_bars,250),(rach_b,182),(merge_lips,226),(lobe_edges,116)])


def _w11_luna_dust() -> _Grammar:
    """W11: interrupted dendritic dust chains replace W10's rejected cell pave."""
    x,y=_xy(); craters=[(69,88,22,15),(184,151,31,21),(349,73,19,28),(455,214,33,18),(111,369,25,34),(286,323,37,23),(414,439,27,31)]
    crater=np.zeros((_WORK,_WORK),np.float32); rims=np.zeros_like(crater); crescents=[]; ejecta=[]
    for i,(cx,cy,rx,ry) in enumerate(craters):
        er=np.hypot((x-cx)/rx,(y-cy)/ry); crater=np.maximum(crater,_inside(er,1,.08)); rims=np.maximum(rims,_ring(er,.91,.045))
        a=np.linspace(-1.15+.21*i,.72+.17*i,70); crescents.append(np.c_[cx+(rx+4)*np.cos(a),cy+(ry+3)*np.sin(a)])
        for k,a0 in enumerate((-.72,.18,1.07,2.18,3.51,4.64)):
            length=36+9*((i+k)%4); q=np.linspace(0,1,45); ang=a0+.23*i+.11*k
            px=cx+(rx+3)*np.cos(ang)+length*q*np.cos(ang)+7*np.sin(np.pi*q+k)
            py=cy+(ry+3)*np.sin(ang)+length*q*np.sin(ang)+5*np.sin(2*np.pi*q+i)
            ejecta.append(np.c_[px,py])
    # Explicit branching chains cross the canvas at unrelated slopes and are
    # cut out by the seven authored crater basins.
    chains=[]; forks=[]
    for i in range(17):
        q=np.linspace(-.08,1.08,230); sx=-24+19*(i%3); sy=21+31*i
        px=sx+556*q+28*np.sin((1.1+.07*i)*np.pi*q+i*.49)+12*np.sin(5*np.pi*q+i)
        py=sy+(53*np.sin(i*.67)-31)*q+21*np.sin((2.3+.11*(i%4))*np.pi*q+i*.31)
        chains.append(np.c_[px,py])
        for j in (73+i%11,148-i%9):
            bx,by=float(px[j]),float(py[j]); side=-1 if (i+j)%2 else 1
            forks.append([(bx,by),(bx+31,by+side*19),(bx+68,by+side*31)])
    chain_raw=_paths(chains,2); fork_raw=_paths(forks,2)
    chain=chain_raw*(1-.94*crater); fork_m=fork_raw*(1-.94*crater)
    skeleton=np.maximum(chain,fork_m); d=_distance_from(skeleton)
    dust_a=_periodic_line(d+3*np.sin((x+y)/41.0),6.0,.77)*(1-.85*crater)
    dust_b=_periodic_line(d-.19*x+5*np.sin(y/53.0),8.3,.73,.25)*(1-.85*crater)
    nodes=np.minimum(np.maximum(dust_a,dust_b),_periodic_line(x+1.37*y+9*np.sin(x/37.0),5.1,.57))
    cres_m=_paths(crescents,2); eject_m=_paths(ejecta,1)
    masks=dict(interrupted_dendritic_dust_chains=chain,authored_chain_forks=fork_m,positive_crater_basin_dust=dust_a,
               negative_crater_basin_dust=dust_b,seven_elliptic_crater_rims=rims,crescent_ejecta_fronts=cres_m,
               directional_ejecta_filaments=eject_m,dust_chain_order_nodes=nodes,matte_crater_floors=crater)
    own=dict(interrupted_dendritic_dust_chains=("N",38,218,76),authored_chain_forks=("A",188,128,58),
             positive_crater_basin_dust=("A",238,72,40),negative_crater_basin_dust=("B",64,192,230),
             seven_elliptic_crater_rims=("B",116,48,250),crescent_ejecta_fronts=("A",214,146,54),
             directional_ejecta_filaments=("N",88,224,86),dust_chain_order_nodes=("B",96,92,244),
             matte_crater_floors=("N",18,242,24))
    return _pack10(masks,own,d+.13*x-.09*y,
                   [(dust_a,244),(chain,188),(rims,108),(nodes,216)],
                   [(dust_b,222),(crater,44),(eject_m,172),(fork_m,104)],
                   [(rims,250),(dust_b,182),(cres_m,226),(nodes,116)])


def _w11_ulysses_flash() -> _Grammar:
    """W11: five irregular fault territories replace the rejected global comb."""
    x,y=_xy(); left=x < 119+38*np.sin(y/79.0)+13*np.sin(y/31.0)
    top=(y < 127+43*np.sin((x+17)/91.0)+11*np.sin(x/37.0)) & ~left
    right=(x > 381+34*np.sin((y+31)/67.0)-12*np.sin(y/29.0)) & ~left & ~top
    bottom=(y > 382+39*np.sin((x-41)/83.0)-10*np.sin(x/33.0)) & ~left & ~top & ~right
    owner=np.full((_WORK,_WORK),4,np.int32); owner[left]=0; owner[top]=1; owner[right]=2; owner[bottom]=3
    walls=np.zeros((_WORK,_WORK),np.float32)
    for i in range(5): walls=np.maximum(walls,_edge((owner==i).astype(np.float32),2))
    phases=[x+.41*y+9*np.sin(y/47.0), y-.63*x+7*np.sin(x/59.0), x-.22*y+11*np.sin((x+y)/67.0),
            y+.78*x+8*np.sin((x-y)/43.0), x+.13*y+6*np.sin(y/31.0)+.0007*x*y]
    comb_parts=[]; cross_parts=[]
    for i,ph in enumerate(phases):
        dom=owner==i; chirp=ph*(1+.0008*(x+31*i))+.004*(i-2)*ph*ph/64.0
        comb_parts.append(_periodic_line(chirp,5.7+.7*i,.84-.018*i,.25*(i%2))*dom)
        cross_parts.append(_periodic_line(chirp+.29*(x-y),11.0+1.4*i,.47)*dom)
    comb_a=np.maximum.reduce([comb_parts[0],comb_parts[2],comb_parts[4]])
    comb_b=np.maximum.reduce([comb_parts[1],comb_parts[3]])
    cross=np.maximum.reduce(cross_parts)
    term=np.minimum(np.maximum(comb_a,comb_b),cv2.dilate(walls,np.ones((11,11),np.uint8)))
    fault_lips=_periodic_line(_distance_from(walls)+.17*x,7.3,.58)*_inside(_distance_from(walls),21,6)
    pores=_circles([(45,92,2),(156,202,2),(278,83,2),(394,286,2),(229,414,2),(472,452,2)],1)
    arrest=_line(np.sin((phases[0]-phases[3])/17.0)+.47*np.sin((phases[2]-phases[4])/21.0),.17)*term
    masks=dict(five_irregular_fault_territories=np.maximum(comb_a,comb_b),territory_comb_family_a=comb_a,
               territory_comb_family_b=comb_b,curved_fault_walls=walls,wall_normal_cross_ties=cross,
               comb_termination_crowns=term,fault_distance_overlap_lips=fault_lips,authored_fault_pores=pores,
               basin_arrest_scars=arrest)
    own=dict(five_irregular_fault_territories=("N",78,206,88),territory_comb_family_a=("A",242,62,38),
             territory_comb_family_b=("B",62,194,230),curved_fault_walls=("N",34,224,72),
             wall_normal_cross_ties=("A",188,136,56),comb_termination_crowns=("B",116,48,250),
             fault_distance_overlap_lips=("A",216,92,62),authored_fault_pores=("N",18,242,28),
             basin_arrest_scars=("B",94,102,242))
    tone=np.choose(owner,phases)
    return _pack10(masks,own,tone,
                   [(comb_a,244),(walls,188),(term,92),(cross,214)],
                   [(comb_b,222),(walls,46),(fault_lips,172),(pores,238)],
                   [(term,250),(comb_b,182),(fault_lips,226),(arrest,116)])


def _w11_owl_eye() -> _Grammar:
    """W11: open parabolic feather crescents replace W10's bullseye rings."""
    x,y=_xy(); eyes=[(-18,298,81,111),(391,205,103,76)]
    pupil=np.zeros((_WORK,_WORK),np.float32); iris=np.zeros_like(pupil); glints=[]
    for i,(cx,cy,rx,ry) in enumerate(eyes):
        er=np.hypot((x-cx)/rx,(y-cy)/ry); iris=np.maximum(iris,_ring(er,.78+.06*np.sin(3*np.arctan2(y-cy,x-cx)+i),.035))
        pupil=np.maximum(pupil,_inside(np.hypot((x-cx-(8 if i else -7))/19,(y-cy)/27),1,.10)); glints.append((cx+9,cy-12,3))
    # Opposing open parabolas read as overlapping crescent plates, not eyes.
    left_phase=(x+22)+.0038*(y-299)**2+8*np.sin((y-299)/53.0)
    right_phase=(510-x)+.0047*(y-203)**2+7*np.sin((y-203)/47.0)
    left_dom=(x<307+31*np.sin(y/89.0)); right_dom=~(x<216+24*np.sin(y/73.0))
    plates_l=np.maximum(_periodic_line(left_phase,7.0,.77),_periodic_line(left_phase+.31*y,10.4,.58,.25))*left_dom
    plates_r=np.maximum(_periodic_line(right_phase,8.1,.75,.25),_periodic_line(right_phase-.27*y,11.3,.56))*right_dom
    lids=_paths([[(-12,263),(57,218),(139,255),(221,329)],[(286,205),(377,157),(472,176),(526,231)],
                 [(-9,343),(69,379),(151,342)],[(303,245),(395,277),(503,248)]],4)
    eyelid_chev=_periodic_line(x-.62*y+7*np.sin(y/43.0),9.0,.52)*cv2.dilate(lids,np.ones((15,15),np.uint8))
    overlap=np.minimum(plates_l,plates_r); beak=_paths([[(216,287),(259,246),(302,291)],[(231,315),(259,339),(289,312)]],3)
    glint_m=_circles(glints,2); cres_lips=np.maximum(_edge(plates_l,1),_edge(plates_r,1))*_periodic_line(y,13.0,.44)
    masks=dict(two_unequal_cropped_irises=iris,matte_offset_pupils=pupil,left_open_feather_crescents=plates_l,
               right_open_feather_crescents=plates_r,layered_eyelid_paths=lids,eyelid_attached_chevrons=eyelid_chev,
               crescent_plate_overlap=overlap,central_beak_chevrons=beak,offset_eye_glints=glint_m,
               feather_crescent_lips=cres_lips)
    own=dict(two_unequal_cropped_irises=("B",124,48,250),matte_offset_pupils=("N",18,242,22),
             left_open_feather_crescents=("A",238,72,40),right_open_feather_crescents=("B",64,192,230),
             layered_eyelid_paths=("A",198,118,58),eyelid_attached_chevrons=("B",108,92,244),
             crescent_plate_overlap=("N",34,224,78),central_beak_chevrons=("A",218,144,54),
             offset_eye_glints=("N",88,210,92),feather_crescent_lips=("B",142,66,246))
    return _pack10(masks,own,left_phase-right_phase,
                   [(plates_l,244),(iris,188),(lids,112),(pupil,18)],
                   [(plates_r,222),(pupil,44),(eyelid_chev,172),(overlap,102)],
                   [(iris,250),(plates_r,182),(cres_lips,226),(glint_m,116)])


def _w11_stag_carapace() -> _Grammar:
    """W11: seven contiguous irregular armor territories replace floating ovals."""
    x,y=_xy(); polys=[
        [(-20,-20),(172,-20),(209,78),(174,185),(-20,207)],
        [(154,-20),(337,-20),(371,91),(316,192),(174,164),(207,73)],
        [(326,-20),(532,-20),(532,177),(437,215),(351,151),(370,82)],
        [(-20,184),(174,155),(257,237),(213,361),(-20,337)],
        [(170,157),(348,176),(421,274),(333,382),(211,353),(253,236)],
        [(345,162),(532,159),(532,353),(441,397),(337,365),(420,273)],
        [(-20,330),(207,348),(332,374),(532,345),(532,532),(-20,532)]
    ]
    plate_masks=[]; seams=np.zeros((_WORK,_WORK),np.float32); collar_a=np.zeros_like(seams); collar_b=np.zeros_like(seams)
    for i,poly in enumerate(polys):
        canvas=np.zeros((_WORK,_WORK),np.uint8); pts=np.asarray(poly,np.int32).reshape((-1,1,2)); cv2.fillPoly(canvas,[pts],255,cv2.LINE_AA)
        pm=canvas.astype(np.float32)/255.0; plate_masks.append(pm); seams=np.maximum(seams,_paths([poly+[poly[0]]],3))
        inner=cv2.distanceTransform((canvas>127).astype(np.uint8),cv2.DIST_L2,5).astype(np.float32)
        collars=_periodic_line(inner+4*np.sin((x+y)/(43+5*i)+i),6.1+.45*i,.76,.25*(i%2))*pm
        if i%2: collar_b=np.maximum(collar_b,collars)
        else: collar_a=np.maximum(collar_a,collars)
    antlers=[]
    for side in (-1,1):
        q=np.linspace(-.08,1.08,220); px=256+side*(283*q+28*np.sin(2*np.pi*q)); py=271-143*np.sin(np.pi*q)+side*26*np.sin(3*np.pi*q)
        antlers.append(np.c_[px,py])
        for j in (51,93,139,177):
            bx,by=float(px[j]),float(py[j]); antlers.append([(bx,by),(bx+side*39,by-37-(j%17)),(bx+side*74,by-55+(j%13))])
    ant_l=_paths(antlers[:5],5); ant_r=_paths(antlers[5:],4); ant=np.maximum(ant_l,ant_r)
    visible_a=np.maximum.reduce([plate_masks[i]*(1-.84*ant) for i in (0,2,4,6)])
    visible_b=np.maximum.reduce([plate_masks[i]*(1-.84*ant) for i in (1,3,5)])
    bosses=_circles([(91,81,3),(259,72,3),(434,83,3),(98,262,3),(298,267,3),(455,272,3),(273,441,3)],2)
    trab=_periodic_line(x+.71*y+11*np.sin((x-y)/57.0),8.0,.57)*cv2.dilate(ant,np.ones((19,19),np.uint8))
    hooks=_paths([[(-3,252),(29,230),(54,247)],[(516,275),(487,246),(461,262)],[(245,126),(256,102),(269,127)]],2)
    masks=dict(contiguous_armor_plates_a=visible_a,contiguous_armor_plates_b=visible_b,seven_irregular_plate_seams=seams,
               left_occluding_antler=ant_l,right_occluding_antler=ant_r,positive_plate_collars=collar_a,
               negative_plate_collars=collar_b,plate_boss_rings=bosses,antler_trabecular_branches=trab,terminal_antler_hooks=hooks)
    own=dict(contiguous_armor_plates_a=("A",184,124,54),contiguous_armor_plates_b=("B",84,154,232),
             seven_irregular_plate_seams=("N",42,216,84),left_occluding_antler=("A",238,62,40),
             right_occluding_antler=("B",62,194,230),positive_plate_collars=("A",216,94,52),
             negative_plate_collars=("B",116,74,246),plate_boss_rings=("N",20,242,28),
             antler_trabecular_branches=("A",198,142,62),terminal_antler_hooks=("N",96,224,88))
    return _pack10(masks,own,collar_a-collar_b+.11*x,
                   [(collar_a,244),(ant_l,188),(seams,112),(bosses,72)],
                   [(collar_b,222),(visible_b,62),(trab,172),(hooks,106)],
                   [(seams,250),(ant_r,182),(collar_b,226),(bosses,116)])


def _w11_firefly_shell() -> _Grammar:
    """W11: the articulated abdomen is cropped full-frame, never a ribbon icon."""
    x,y=_xy(); center=254+47*np.sin((y-18)/173.0)+19*np.sin(y/61.0); width=296+29*np.sin(y/89.0)+13*np.sin(y/37.0)
    lateral=x-center; body=_inside(np.abs(lateral),width,8)
    bounds=[-29,58,132,215,301,394,533]; joints=[]; seg_owner=np.zeros((_WORK,_WORK),np.int32)
    for i,jy in enumerate(bounds[1:-1]):
        curve=jy+14*np.sin((x-center)/(57+4*i)+i*.7)+.0009*(x-center)**2*(-1 if i%2 else 1)
        joints.append(_line(y-curve,2.5)*body); seg_owner+=(y>curve).astype(np.int32)
    joint=np.maximum.reduce(joints)
    chamber_a=np.zeros((_WORK,_WORK),np.float32); chamber_b=np.zeros_like(chamber_a); ribs=np.zeros_like(chamber_a)
    phase_total=np.zeros_like(chamber_a)
    for i in range(6):
        dom=(seg_owner==i); angle=(-.42+.19*i)+.21*np.sin((x+y)/(83+7*i))
        phase=(x*np.cos(angle)+y*np.sin(angle))*(1+.0007*(x+23*i))+7*np.sin((x-y)/(47+3*i)+i)
        bands=np.maximum(_periodic_line(phase,5.8+.45*i,.77,.25*(i%2)),
                         _periodic_line(phase+.29*lateral,9.7+.5*i,.56))*dom*body
        if i%2: chamber_b=np.maximum(chamber_b,bands)
        else: chamber_a=np.maximum(chamber_a,bands)
        ribs=np.maximum(ribs,_periodic_line(lateral+.17*y+5*np.sin(y/(41+2*i)),12.0+i,.48)*dom*body)
        phase_total+=phase*dom
    lumen_width=61+11*np.sin(y/71.0); lumen_region=_inside(np.abs(lateral),lumen_width,5)*body
    lumen=_periodic_line(lateral+6*np.sin(y/43.0),9.1,.59)*lumen_region
    pulses=_periodic_line(y+15*np.sin(lateral/79.0)+17*seg_owner,17.0+1.1*seg_owner,.49)*np.maximum(chamber_a,chamber_b)
    edge=_edge(body,2); spiracles=[]
    for i,jy in enumerate((34,95,171,255,347,455)):
        cj=254+47*np.sin((jy-18)/173.0)+19*np.sin(jy/61.0); wj=296+29*np.sin(jy/89.0)+13*np.sin(jy/37.0)
        for side in (-1,1): spiracles.append((cj+side*(wj-17),jy,2.2))
    spiracle=_circles(spiracles,1)
    masks=dict(full_frame_cropped_abdomen=body,unequal_curved_articulation_joints=joint,alternating_lantern_chambers_a=chamber_a,
               alternating_lantern_chambers_b=chamber_b,segment_specific_longitudinal_ribs=ribs,central_lantern_lumen=lumen,
               nonperiodic_segment_pulses=pulses,paired_segment_spiracles=spiracle,scalloped_abdomen_edge=edge)
    own=dict(full_frame_cropped_abdomen=("N",40,210,82),unequal_curved_articulation_joints=("A",226,68,42),
             alternating_lantern_chambers_a=("A",242,72,38),alternating_lantern_chambers_b=("B",62,194,230),
             segment_specific_longitudinal_ribs=("A",188,138,58),central_lantern_lumen=("N",18,242,24),
             nonperiodic_segment_pulses=("B",118,52,250),paired_segment_spiracles=("N",94,224,88),
             scalloped_abdomen_edge=("B",104,96,244))
    return _pack10(masks,own,phase_total+.13*lateral,
                   [(chamber_a,244),(joint,188),(spiracle,82),(pulses,216)],
                   [(chamber_b,222),(lumen,44),(ribs,172),(edge,106)],
                   [(pulses,250),(chamber_b,182),(joint,226),(spiracle,116)])


def _w11_ground_beetle() -> _Grammar:
    """W11: a diagonal asymmetric keel replaces the rejected central rail."""
    x,y=_xy(); q=np.linspace(-.08,1.08,280)
    px=-29+569*q+18*np.sin(3*np.pi*q); py=474-407*q+47*np.sin(1.55*np.pi*q)+16*np.sin(5*np.pi*q)
    paths=[np.c_[px,py]]; forks=[]
    branch_specs=[(57,-1,167,-113),(103,1,139,126),(154,-1,183,-97),(207,1,155,111)]
    for i,(j,side,reach,rise) in enumerate(branch_specs):
        bx,by=float(px[j]),float(py[j]); tq=np.linspace(0,1,120)
        fx=bx+reach*tq+17*np.sin(np.pi*tq+i); fy=by+rise*tq+side*31*np.sin(np.pi*tq)+12*np.sin(3*np.pi*tq+i)
        paths.append(np.c_[fx,fy]); forks.append([(bx,by),(fx[24],fy[24]),(fx[49],fy[49])])
    carina=_paths(paths,5); d=_distance_from(carina)
    ribs=[]; hooks=[]
    schedules=[(paths[0],range(14,266,11)),(paths[1],range(16,108,14)),(paths[2],range(19,111,17)),
               (paths[3],range(13,109,13)),(paths[4],range(21,110,18))]
    for pi,(path,schedule) in enumerate(schedules):
        for n,j in enumerate(schedule):
            bx,by=path[j]; dx=path[min(j+2,len(path)-1),0]-path[max(j-2,0),0]; dy=path[min(j+2,len(path)-1),1]-path[max(j-2,0),1]; mag=np.hypot(dx,dy)+1e-4
            nx,ny=-dy/mag,dx/mag; side=-1 if (n+pi)%3 else 1; reach=31+7*((n+2*pi)%6)
            ex,ey=bx+side*nx*reach,by+side*ny*reach
            ribs.append([(bx,by),(bx+side*nx*reach*.52+dx/mag*6,by+side*ny*reach*.52+dy/mag*6),(ex,ey)])
            if (n+pi)%5==2: hooks.append([(ex-side*nx*7,ey-side*ny*7),(ex,ey),(ex+side*nx*9-dx/mag*6,ey+side*ny*9-dy/mag*6)])
    rib_m=_paths(ribs,2); hook_m=_paths(hooks,2); fork_m=_paths(forks,3)
    collars_a=_periodic_line(d+4*np.sin((x+y)/43.0),6.1,.77)
    collars_b=_periodic_line(d-.17*x+.11*y+5*np.sin(y/61.0),8.3,.73,.25)
    serr=np.minimum(_periodic_line(x+.83*y,5.0,.56),cv2.dilate(rib_m,np.ones((11,11),np.uint8)))
    merge=np.maximum(fork_m,np.minimum(rib_m,cv2.dilate(carina,np.ones((13,13),np.uint8))))
    shoulder=_periodic_line(d+.37*y,13.0,.49)*_inside(d,57,13)
    masks=dict(diagonal_branching_carina=carina,irregular_terminating_ribs=rib_m,positive_keel_collars=collars_a,
               negative_keel_collars=collars_b,rib_attached_serrations=serr,authored_rib_merge_junctions=merge,
               irregular_shoulder_hooks=hook_m,branch_distance_shoulder_bands=shoulder)
    own=dict(diagonal_branching_carina=("N",40,216,82),irregular_terminating_ribs=("A",226,66,42),
             positive_keel_collars=("A",242,78,38),negative_keel_collars=("B",62,194,230),
             rib_attached_serrations=("B",108,92,244),authored_rib_merge_junctions=("N",22,240,30),
             irregular_shoulder_hooks=("A",194,138,58),branch_distance_shoulder_bands=("B",126,52,250))
    return _pack10(masks,own,d+.14*x-.09*y,
                   [(collars_a,244),(carina,188),(serr,112),(merge,216)],
                   [(collars_b,222),(rib_m,58),(shoulder,172),(hook_m,238)],
                   [(rib_m,250),(collars_b,182),(hook_m,226),(merge,106)])


def _w11_starling_sheen() -> _Grammar:
    """W11: two non-grid vortex sheets cross through one braided collision zone."""
    x,y=_xy(); ra=np.hypot((x-101)/1.12,(y-217)/.88)+7; aa=np.arctan2(y-217,x-101)
    rb=np.hypot((x-423)/.91,(y-309)/1.17)+7; ab=np.arctan2(y-309,x-423)
    boundary=x+y-506-39*np.sin((x-y)/83.0); dom_a=_inside(boundary,34,13); dom_b=_inside(-boundary,58,15)
    ph_a=ra+22*aa+7*np.sin(3*aa)+.012*x*y/48.0
    ph_b=rb-19*ab+8*np.sin(2*ab)-.011*x*y/51.0
    vane_a=np.maximum(_periodic_line(ph_a,6.0,.77),_periodic_line(ph_a+.27*y,10.1,.58,.25))*dom_a
    vane_b=np.maximum(_periodic_line(ph_b,7.2,.75,.25),_periodic_line(ph_b-.23*x,11.3,.56))*dom_b
    rach_a=[]; rach_b=[]
    for i,(r0,a0,span) in enumerate(((53,-1.1,2.5),(97,-.8,2.2),(142,-.45,1.9))):
        q=np.linspace(0,1,150); a=a0+span*q; r=r0+104*q+13*np.sin(2*np.pi*q+i)
        rach_a.append(np.c_[101+r*np.cos(a),217+.78*r*np.sin(a)])
    for i,(r0,a0,span) in enumerate(((61,2.0,-2.2),(112,2.35,-1.9),(158,2.7,-1.65))):
        q=np.linspace(0,1,150); a=a0+span*q; r=r0+91*q+11*np.sin(3*np.pi*q+i)
        rach_b.append(np.c_[423+.91*r*np.cos(a),309+r*np.sin(a)])
    rach_ma=_paths(rach_a,3); rach_mb=_paths(rach_b,3)
    branchlets=[]
    for i,p in enumerate(rach_a+rach_b):
        for j in (43+i*3,91-i*2,129-i):
            bx,by=p[j]; ang=.37*i+.8; branchlets.append([(bx,by),(bx+19*np.cos(ang),by+19*np.sin(ang)),(bx+37*np.cos(ang+.3),by+37*np.sin(ang+.3))])
    branch_m=_paths(branchlets,1)
    collision=np.minimum(dom_a,dom_b); pockets=_line(np.sin((ph_a-ph_b)/11.0)+.43*np.sin((x+y)/17.0),.18)*collision
    braid=np.maximum(rach_ma*(1-.72*cv2.dilate(rach_mb,np.ones((7,7),np.uint8))),rach_mb*(1-.72*cv2.dilate(rach_ma,np.ones((7,7),np.uint8))))
    hooks=np.minimum(np.maximum(vane_a,vane_b),_periodic_line(x+1.43*y,5.0,.55))*cv2.dilate(pockets,np.ones((13,13),np.uint8))
    overlap_lips=_periodic_line(ph_a-ph_b,9.0,.52)*collision
    masks=dict(first_feather_vortex_sheet=vane_a,second_crossing_vortex_sheet=vane_b,first_sheet_curved_rachises=rach_ma,
               second_sheet_curved_rachises=rach_mb,rachis_bifurcation_branchlets=branch_m,authored_collision_pockets=pockets,
               alternating_collision_braid=braid,pocket_only_barb_hooks=hooks,crossing_overlap_lips=overlap_lips)
    own=dict(first_feather_vortex_sheet=("A",242,68,38),second_crossing_vortex_sheet=("B",62,194,230),
             first_sheet_curved_rachises=("A",188,124,54),second_sheet_curved_rachises=("B",94,146,240),
             rachis_bifurcation_branchlets=("N",86,220,86),authored_collision_pockets=("N",20,242,26),
             alternating_collision_braid=("A",214,96,58),pocket_only_barb_hooks=("B",118,52,250),
             crossing_overlap_lips=("N",102,212,92))
    return _pack10(masks,own,ph_a-ph_b,
                   [(vane_a,244),(rach_ma,188),(branch_m,112),(pockets,54)],
                   [(vane_b,222),(rach_mb,62),(hooks,172),(collision,106)],
                   [(overlap_lips,250),(vane_b,182),(braid,226),(pockets,116)])


def _w13_sunset_moth() -> _Grammar:
    """W13: two unequal cropped wing bodies replace the ambiguous long-ray read."""
    x,y=_xy(); inv=np.float32(1/np.sqrt(2.0)); along=(x-y)*inv; normal=(x+y-478)*inv
    width_l=151+39*np.sin((along+83)/127.0)+17*np.sin(along/43.0)
    width_r=209+31*np.sin((along-41)/151.0)-23*np.sin(along/57.0)
    wing_l=((normal<0)&(normal>-width_l)).astype(np.float32)
    wing_r=((normal>=0)&(normal<width_r)).astype(np.float32)
    body=_line(normal,3.6); rim_l=_line(normal+width_l,2.4); rim_r=_line(normal-width_r,2.4); rim=np.maximum(rim_l,rim_r)
    veins_l=[]; veins_r=[]; forks=[]
    roots=[(-92,1.0),(-21,.82),(57,1.16),(139,.73),(214,1.29)]
    for i,(a0,bend) in enumerate(roots):
        bx=(a0*inv+478/2); by=(-a0*inv+478/2)
        for side in (-1,1):
            reach=(132+19*i)*(1.0+(.14 if side>0 and i%2 else -.07))
            q=np.linspace(0,1,125); nx=inv*side; ny=inv*side
            tx=inv; ty=-inv
            px=bx+nx*reach*q+tx*side*(21+7*i)*np.sin(np.pi*q)*bend
            py=by+ny*reach*q+ty*side*(21+7*i)*np.sin(np.pi*q)*bend+9*np.sin(2*np.pi*q+i)
            (veins_l if side<0 else veins_r).append(np.c_[px,py])
            for j in (44+i%7,83-i%5):
                vx,vy=float(px[j]),float(py[j]); forks.append([(vx,vy),(vx+side*24,vy-side*9),(vx+side*51,vy-side*14)])
    vein_l=_paths(veins_l,3)*wing_l; vein_r=_paths(veins_r,2)*wing_r; fork_m=_paths(forks,1)*np.maximum(wing_l,wing_r)
    phase_l=along+.0062*normal**2+8*np.sin((along+normal)/59.0)
    phase_r=.43*along-.0041*normal**2+11*np.sin((along-normal)/71.0)
    scale_l=np.maximum(_periodic_line(phase_l,6.0,.78),_periodic_line(phase_l+.31*normal,10.1,.57,.25))*wing_l
    scale_r=np.maximum(_periodic_line(phase_r,7.3,.75,.25),_periodic_line(phase_r-.27*normal,11.4,.55))*wing_r
    scale_rakes=np.minimum(np.maximum(scale_l,scale_r),_periodic_line(along+1.17*normal,5.0,.54))
    cres_t=np.linspace(-.72,.91,100); cres=np.c_[366+71*np.cos(cres_t),126+47*np.sin(cres_t)]; cres_m=_paths([cres],3)*wing_r
    scallop=_periodic_line(along+9*np.sin(along/37.0),13.0,.47)*cv2.dilate(rim,np.ones((13,13),np.uint8))
    masks=dict(diagonal_cropped_body_spine=body,unequal_left_wing_body=wing_l,unequal_right_wing_body=wing_r,
               left_branching_vein_tree=vein_l,right_branching_vein_tree=vein_r,secondary_vein_forks=fork_m,
               left_curvature_scale_field=scale_l,right_curvature_scale_field=scale_r,scale_rake_intersections=scale_rakes,
               frame_crossing_scalloped_rim=np.maximum(rim,scallop),single_nested_crescent=cres_m)
    own=dict(diagonal_cropped_body_spine=("N",36,222,74),unequal_left_wing_body=("A",168,132,58),
             unequal_right_wing_body=("B",82,158,232),left_branching_vein_tree=("A",238,64,40),
             right_branching_vein_tree=("B",62,194,230),secondary_vein_forks=("N",94,218,88),
             left_curvature_scale_field=("A",218,92,54),right_curvature_scale_field=("B",116,72,246),
             scale_rake_intersections=("A",192,148,62),frame_crossing_scalloped_rim=("N",24,240,30),
             single_nested_crescent=("B",142,48,250))
    return _pack10(masks,own,phase_l-phase_r,
                   [(scale_l,244),(vein_l,188),(body,216),(cres_m,84)],
                   [(scale_r,222),(wing_l,62),(fork_m,172),(scallop,106)],
                   [(cres_m,250),(scale_r,182),(rim,226),(scale_rakes,116)])


def _w13_peacock_eye() -> _Grammar:
    """W13: a dominant open off-canvas ocellus sits over an irregular branch plume."""
    x,y=_xy(); dx=(x+104)/367; dy=(y-281)/294; th=np.arctan2(dy,dx); gr=np.hypot(dx,dy)
    boundary=.94+.11*np.sin(2*th-.3)+.06*np.sin(5*th+.4)
    gate=_inside(np.abs(th-.03),2.38,.16)
    giant_outer=_ring(gr,boundary,.024)*gate
    giant_mantle=_inside(np.abs(gr-(boundary-.13)),.085,.025)*gate
    giant_pupil=_inside(np.hypot((x-29)/74,(y-294)/111),1,.10)
    # The two secondary eyes intentionally use unlike equations and broken fronts.
    t2=np.arctan2(y-116,x-388); e2=np.hypot((x-388)/82,(y-116)/55)
    tear_boundary=.87-.18*np.cos(t2)+.07*np.sin(3*t2); eye2=_ring(e2,tear_boundary,.04)*(np.sin(t2*2+.7)>.0)
    e2_pupil=_inside(np.hypot((x-404)/16,(y-121)/23),1,.10)
    t3=np.arctan2(y-405,x-423); e3=np.hypot((x-423)/107,(y-405)/72)
    eye3=_ring(e3,.76+.12*np.sin(2*t3+.9),.045)*(t3>-2.45)*(t3<1.37)
    eye3_cres=_inside(np.abs(e3-.41),.075,.025)*(t3>-.8)
    stems=[]; twigs=[]
    roots=[(-17,18),(-22,121),(-18,238),(-9,369),(53,529),(189,528),(323,526),(529,318),(526,158)]
    for i,(sx,sy) in enumerate(roots):
        q=np.linspace(0,1,155); ex=252+83*np.cos(i*.61+.4); ey=273+109*np.sin(i*.73-.2)
        px=sx+(ex-sx)*q+27*np.sin(np.pi*q+i*.37)+9*np.sin(4*np.pi*q+i)
        py=sy+(ey-sy)*q+23*np.sin(2*np.pi*q+i*.51)
        stems.append(np.c_[px,py])
        for j in range(19+i%5,148,17+i%4):
            bx,by=float(px[j]),float(py[j]); side=-1 if (i+j)%2 else 1
            twigs.append([(bx,by),(bx+side*(17+j%8),by-8+side*5),(bx+side*(34+j%11),by-13+side*9)])
    stem_m=_paths(stems,3); twig_m=_paths(twigs,1); d=_distance_from(np.maximum(stem_m,twig_m))
    plume_a=_periodic_line(d+4*np.sin((x+y)/41.0),6.0,.78)
    plume_b=_periodic_line(d-.19*x+5*np.sin(y/57.0),8.2,.73,.25)
    hooks=np.minimum(np.maximum(plume_a,plume_b),_periodic_line(x-.61*y,5.0,.55))*cv2.dilate(twig_m,np.ones((13,13),np.uint8))
    giant=np.maximum.reduce([giant_outer,giant_mantle,giant_pupil]); secondary=np.maximum.reduce([eye2,e2_pupil,eye3,eye3_cres])
    masks=dict(dominant_open_off_canvas_ocellus=giant,irregular_giant_ocellus_front=giant_outer,giant_ocellus_mantle=giant_mantle,
               broken_teardrop_secondary_eye=np.maximum(eye2,e2_pupil),open_crescent_secondary_eye=np.maximum(eye3,eye3_cres),
               dense_branching_plume_stems=stem_m,plume_bifurcation_twigs=twig_m,positive_plume_lamellae=plume_a,
               negative_plume_lamellae=plume_b,twig_attached_barb_hooks=hooks)
    own=dict(dominant_open_off_canvas_ocellus=("B",126,48,250),irregular_giant_ocellus_front=("A",232,72,42),
             giant_ocellus_mantle=("A",198,128,58),broken_teardrop_secondary_eye=("N",26,240,30),
             open_crescent_secondary_eye=("B",98,84,244),dense_branching_plume_stems=("A",188,138,56),
             plume_bifurcation_twigs=("N",88,220,86),positive_plume_lamellae=("A",242,64,38),
             negative_plume_lamellae=("B",62,194,230),twig_attached_barb_hooks=("B",112,102,246))
    return _pack10(masks,own,d+th*11,
                   [(plume_a,244),(giant_outer,214),(stem_m,188),(giant_pupil,42)],
                   [(plume_b,222),(secondary,54),(twig_m,172),(hooks,106)],
                   [(giant,250),(plume_b,182),(eye2,226),(eye3_cres,116)])


_BUILDERS: Mapping[str, Callable[[], _Grammar]] = {
    "fmo_morpho_blue": _w10_morpho_blue,
    "fmo_sunset_moth": _w13_sunset_moth,
    "fmo_monarch_vein": _w10_monarch_vein,
    "fmo_atlas_wing": _w10_atlas_wing,
    "fmo_luna_dust": _w11_luna_dust,
    "fmo_swallowtail": _w10_swallowtail,
    "fmo_ulysses_flash": _w11_ulysses_flash,
    "fmo_owl_eye": _w11_owl_eye,
    "fmo_glasswing": _w10_glasswing,
    "fmo_emperor_scale": _w10_emperor_scale,
    "fmo_jewel_scarab": _w10_jewel_scarab,
    "fmo_tiger_beetle": _w10_tiger_beetle,
    "fmo_stag_carapace": _w11_stag_carapace,
    "fmo_chrysina_gold": _w10_chrysina_gold,
    "fmo_oil_beetle": _w10_oil_beetle,
    "fmo_firefly_shell": _w11_firefly_shell,
    "fmo_weevil_pit": _w10_weevil_pit,
    "fmo_ground_beetle": _w11_ground_beetle,
    "fmo_scarab_horn": _w10_scarab_horn,
    "fmo_ladybird_dome": _w10_ladybird_dome,
    "fmo_hummingbird_gorget": _w10_hummingbird_gorget,
    "fmo_peacock_eye": _w13_peacock_eye,
    "fmo_starling_sheen": _w11_starling_sheen,
    "fmo_magpie_wing": _w10_magpie_wing,
    "fmo_duck_speculum": _w10_duck_speculum,
}


_HUES: Mapping[str, Tuple[float, float]] = {
    "fmo_morpho_blue": (.60, .84),          # cobalt / violet-cyan order
    "fmo_sunset_moth": (.055, .77),         # sunset orange / violet-teal
    "fmo_monarch_vein": (.075, .50),        # monarch orange / cool flash
    "fmo_atlas_wing": (.095, .43),          # rust-brown / green-violet mimic
    "fmo_luna_dust": (.29, .73),            # moon green / violet silver
    "fmo_swallowtail": (.58, .12),          # blue / yellow-red eyes
    "fmo_ulysses_flash": (.60, .88),        # cobalt / magenta-cyan order
    "fmo_owl_eye": (.105, .62),             # owl gold / blue-violet glint
    "fmo_glasswing": (.53, .115),           # smoke cyan / gold vein edge
    "fmo_emperor_scale": (.73, .12),        # royal violet / amber crown
    "fmo_jewel_scarab": (.38, .98),         # emerald / ruby-violet suture
    "fmo_tiger_beetle": (.45, .085),        # green metal / cream-magenta
    "fmo_stag_carapace": (.055, .31),       # horn umber / moss green
    "fmo_chrysina_gold": (.115, .43),       # gold / green-magenta Bragg
    "fmo_oil_beetle": (.68, .49),           # blue violet / teal oil
    "fmo_firefly_shell": (.12, .34),         # amber / lime-cyan lantern
    "fmo_weevil_pit": (.29, .67),           # shell green / violet pit rim
    "fmo_ground_beetle": (.69, .085),        # black-blue / copper-gold rail
    "fmo_scarab_horn": (.09, .36),           # horn gold / emerald edge
    "fmo_ladybird_dome": (.015, .125),       # red-orange / golden crown
    "fmo_hummingbird_gorget": (.95, .36),    # ruby / emerald-cyan normal
    "fmo_peacock_eye": (.58, .32),           # peacock blue / green-gold
    "fmo_starling_sheen": (.70, .36),        # violet / green sheen
    "fmo_magpie_wing": (.59, .13),           # blue-black / silver-gold bar
    "fmo_duck_speculum": (.52, .69),         # teal / violet-blue flash
}


MORPHO_BIO_IDS: Tuple[str, ...] = tuple(_BUILDERS)

if len(MORPHO_BIO_IDS) != 25 or set(MORPHO_BIO_IDS) != set(_HUES):
    raise AssertionError("Morpho biological rebuild must own exactly 25 configured IDs")


@lru_cache(maxsize=8)
def _authored(fid: str) -> Tuple[np.ndarray, np.ndarray]:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _compose(_BUILDERS[fid](), _HUES[fid])


def clear_cache() -> None:
    _authored.cache_clear()
    _xy.cache_clear()


def debug_grammar(fid: str) -> _Grammar:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _BUILDERS[fid]()


def debug_hue_null(fid: str) -> np.ndarray:
    """Palette-free proof using named masks, not paint luminance."""
    grammar = debug_grammar(fid)
    out = .06 + .12 * grammar.tone
    levels = (.28, .72, .42, .90, .54, .96, .36, .82, .64, .22)
    for i, mark in enumerate(grammar.marks):
        value = levels[i % len(levels)]
        alpha = mark.mask * (.34 if float(np.mean(mark.mask)) > .34 else 1.0)
        out = out * (1.0 - alpha) + value * alpha
    return np.repeat(np.clip(out[..., None], 0, 1), 3, axis=2).astype(np.float32)


def debug_angle_pair(fid: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A/B material-lobe proof; paint remains identical between the views."""
    paint, spec = _authored(fid)
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .36 * rough, .30, 1.0)
    gain_a = np.clip(.16 + 1.02 * metal * aperture, .10, 1.18)
    gain_b = np.clip(.16 + 1.02 * coat * aperture, .10, 1.18)
    warm = np.asarray([.45, .19, .05], np.float32)
    cool = np.asarray([.05, .24, .48], np.float32)
    a = np.clip(paint * gain_a[..., None] + warm * (metal * aperture)[..., None], 0, 1)
    b = np.clip(paint * gain_b[..., None] + cool * (coat * aperture)[..., None], 0, 1)
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


def _entry(fid: str):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)
        if src.ndim != 3 or src.shape[2] < 3:
            src = np.zeros((fh, fw, 3), np.float32)
        else:
            src = src[:, :, :3]
            if src.size and float(np.max(src)) > 1.5:
                src = src / 255.0
            if src.shape[:2] != (fh, fw):
                src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored = cv2.resize(_authored(fid)[0], (fw, fh), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(m2 * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        authored = cv2.resize(_authored(fid)[1], (fw, fh), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(_CALM_SPEC + (authored - _CALM_SPEC) * max(0.0, float(sm)), 0, 255)
        mk = np.clip(m2, 0, 1)[..., None]
        rgb = active * mk + _CALM_SPEC * (1.0 - mk)
        out = np.empty((fh, fw, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    spec_fn.__name__ = f"spec_{fid}_biological_rebuild"
    paint_fn.__name__ = f"paint_{fid}_biological_rebuild"
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the first twenty-five current ``fmo_*`` entries."""
    regs = [mono_reg]
    if base_reg is not None and base_reg is not mono_reg:
        regs.append(base_reg)
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys
    eng = sys.modules.get("shokker_engine_v2")
    if eng is not None and hasattr(eng, "FUSION_REGISTRY"):
        regs.append(eng.FUSION_REGISTRY)
    unique_regs = []
    for reg in regs:
        if all(reg is not other for other in unique_regs):
            unique_regs.append(reg)
    for fid in MORPHO_BIO_IDS:
        entry = _entry(fid)
        for reg in unique_regs:
            reg[fid] = entry
    return f"fractured-wilds-morpho-biological-rebuild: {len(MORPHO_BIO_IDS)} explicit grammars live"


def _tile_contact(images: Sequence[np.ndarray], labels: Sequence[str], cols: int = 5, cell: int = 256) -> np.ndarray:
    rows = (len(images) + cols - 1) // cols
    head = 32
    sheet = np.full((rows * (cell + head), cols * cell, 3), 18, np.uint8)
    for i, (im, label) in enumerate(zip(images, labels)):
        row, col = divmod(i, cols)
        tile = cv2.resize(im, (cell, cell), interpolation=cv2.INTER_AREA)
        if tile.ndim == 2:
            tile = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
        sheet[row * (cell + head) + head:(row + 1) * (cell + head), col * cell:(col + 1) * cell] = tile
        cv2.putText(sheet, label.replace("fmo_", "")[:28],
                    (col * cell + 5, row * (cell + head) + 21),
                    cv2.FONT_HERSHEY_SIMPLEX, .47, (236, 236, 236), 1, cv2.LINE_AA)
    return sheet


def _nearest_pair(images: Sequence[np.ndarray], labels: Sequence[str]) -> Mapping[str, object]:
    vectors = []
    for im in images:
        a = np.asarray(im)
        if a.ndim == 3:
            a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
        a = cv2.resize(a, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
        a -= float(a.mean())
        a /= max(float(np.linalg.norm(a)), 1.0e-7)
        vectors.append(a)
    best = (-2.0, "", "")
    vals = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            corr = float(np.dot(vectors[i], vectors[j]))
            vals.append(corr)
            if corr > best[0]:
                best = (corr, labels[i], labels[j])
    return {"max_correlation": round(best[0], 5),
            "nearest_pair": [best[1], best[2]],
            "mean_correlation": round(float(np.mean(vals)), 5),
            "pair_count": len(vals)}


def _audit(output: Path) -> Mapping[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    ids = list(MORPHO_BIO_IDS)
    paints, nulls, metals, roughs, coats = ([] for _ in range(5))
    views_a, views_b, diffs = ([] for _ in range(3))
    rows = []
    t_all = time.perf_counter()
    for i, fid in enumerate(ids, 1):
        clear_cache()
        t0 = time.perf_counter()
        grammar = debug_grammar(fid)
        paint, spec = _compose(grammar, _HUES[fid])
        elapsed = time.perf_counter() - t0
        null = debug_hue_null(fid)
        va, vb, diff = debug_angle_pair(fid)
        p8 = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
        n8 = (np.clip(null, 0, 1) * 255).astype(np.uint8)
        paints.append(cv2.cvtColor(p8, cv2.COLOR_RGB2BGR))
        nulls.append(cv2.cvtColor(n8, cv2.COLOR_RGB2BGR))
        metals.append(spec[:, :, 0])
        roughs.append(spec[:, :, 1])
        coats.append(spec[:, :, 2])
        views_a.append(cv2.cvtColor((va * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
        views_b.append(cv2.cvtColor((vb * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
        diffs.append((np.mean(diff, axis=2) * 255).astype(np.uint8))
        channels = [spec[:, :, j].astype(np.float32).ravel() for j in range(3)]
        channel_corr = [float(np.corrcoef(channels[a], channels[b])[0, 1])
                        for a, b in ((0, 1), (0, 2), (1, 2))]
        causal_union = _mark_union({mark.name: mark.mask for mark in grammar.marks})
        rows.append({
            "id": fid,
            "builder": _BUILDERS[fid].__name__,
            "causal_mask_count": len(grammar.marks),
            "causal_masks": [mark.name for mark in grammar.marks],
            "causal_union_coverage": round(float(np.mean(causal_union > .08)), 4),
            "material_banks": {mark.name: mark.bank for mark in grammar.marks},
            "spec_targets": {mark.name: [mark.metal, mark.rough, mark.coat] for mark in grammar.marks},
            "seconds_512_cold": round(elapsed, 4),
            "paint_sha256": hashlib.sha256(p8.tobytes()).hexdigest(),
            "hue_null_sha256": hashlib.sha256(n8.tobytes()).hexdigest(),
            "spec_sha256": hashlib.sha256(spec.tobytes()).hexdigest(),
            "m_std": round(float(spec[:, :, 0].std()), 3),
            "r_std": round(float(spec[:, :, 1].std()), 3),
            "cc_std": round(float(spec[:, :, 2].std()), 3),
            "spec_channel_correlations_mr_mc_rc": [round(x, 5) for x in channel_corr],
            "ab_mean_abs": round(float(np.mean(diff) * 255), 3),
        })
        print(f"[{i:02d}/25] {fid}: {elapsed:.3f}s", flush=True)

    contacts = {
        "paint_contact.png": paints,
        "hue_null_contact.png": nulls,
        "metal_contact.png": metals,
        "roughness_contact.png": roughs,
        "clearcoat_contact.png": coats,
        "angle_a_contact.png": views_a,
        "angle_b_contact.png": views_b,
        "ab_difference_contact.png": diffs,
    }
    for filename, images in contacts.items():
        cv2.imwrite(str(output / filename), _tile_contact(images, ids))

    spec_silhouettes = []
    for m, r, c in zip(metals, roughs, coats):
        chans = []
        for ch in (m, r, c):
            z = cv2.resize(ch, (64, 64), interpolation=cv2.INTER_AREA)
            chans.append((_norm(z) * 255).astype(np.uint8))
        spec_silhouettes.append(np.concatenate(chans, axis=1))

    api_rows = []
    for fid in ids[::5]:
        spec_fn, paint_fn = _entry(fid)
        shape = (2048, 2048)
        mask = np.ones(shape, np.float32)
        base = np.zeros((2048, 2048, 3), np.float32)
        _authored(fid)
        t0 = time.perf_counter(); pout = paint_fn(base, shape, mask, 1, 1.0, None); tp = time.perf_counter() - t0
        t0 = time.perf_counter(); sout = spec_fn(shape, mask, 1, 1.0); ts = time.perf_counter() - t0
        api_rows.append({"id": fid, "paint_2048_hot_s": round(tp, 4),
                         "spec_2048_hot_s": round(ts, 4),
                         "paint_shape": list(pout.shape), "spec_shape": list(sout.shape)})

    registry = {}
    status = install_into_engine(registry)
    report = {
        "schema": 1,
        "ticket": "SPB-WILDS-REJECTION-2026-08-24 WR-MORPHO-BIO-1",
        "owner_acceptance_claimed": False,
        "old_measured_state": "50 Morpho IDs shared one seven-scatter composer and common rank/carrier spec family",
        "candidate_scope": "first 25 current Morpho IDs only",
        "independent_rejection_basis": "biological_w9/INDEPENDENT_OWNER_EYE_REJECTION.md (0 KEEP / 5 REPAIR / 20 REBUILD)",
        "finish_count": len(ids),
        "explicit_builder_count": len({fn.__name__ for fn in _BUILDERS.values()}),
        "all_builders_have_7_plus_masks": all(r["causal_mask_count"] >= 7 for r in rows),
        "minimum_causal_masks": min(r["causal_mask_count"] for r in rows),
        "minimum_causal_union_coverage": min(r["causal_union_coverage"] for r in rows),
        "all_causal_union_coverage_at_least_0_70": all(r["causal_union_coverage"] >= .70 for r in rows),
        "explicit_feature_attached_spec_builder_count": sum(debug_grammar(fid).explicit_spec is not None for fid in ids),
        "shared_visible_spec_substrate_used": False,
        "rng_or_noise_uniqueness_used": False,
        "wrapped_source_fields_used": False,
        "shared_topology_router_used": False,
        "rank_quantisation_used": False,
        "unique_paint_hashes": len({r["paint_sha256"] for r in rows}),
        "unique_hue_null_hashes": len({r["hue_null_sha256"] for r in rows}),
        "unique_spec_hashes": len({r["spec_sha256"] for r in rows}),
        "hue_null_structural_nn": _nearest_pair(nulls, ids),
        "spec_structural_nn": _nearest_pair(spec_silhouettes, ids),
        "min_spec_std": {"M": min(r["m_std"] for r in rows),
                         "R": min(r["r_std"] for r in rows),
                         "Cc": min(r["cc_std"] for r in rows)},
        "max_abs_within_finish_spec_correlation": max(
            abs(v) for r in rows for v in r["spec_channel_correlations_mr_mc_rc"]),
        "min_ab_mean_abs": min(r["ab_mean_abs"] for r in rows),
        "max_cold_512_s": max(r["seconds_512_cold"] for r in rows),
        "api_2048_samples": api_rows,
        "registry_count": len(registry),
        "registry_ids_exact": set(registry) == set(ids),
        "install_status": status,
        "seconds_total": round(time.perf_counter() - t_all, 3),
        "finishes": rows,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _main() -> int:
    parser = argparse.ArgumentParser(description="Audit explicit biological Morpho builders")
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    report = _audit(args.audit)
    keys = ("finish_count", "explicit_builder_count", "minimum_causal_masks",
            "minimum_causal_union_coverage", "all_causal_union_coverage_at_least_0_70",
            "unique_paint_hashes", "unique_hue_null_hashes", "unique_spec_hashes",
            "hue_null_structural_nn", "spec_structural_nn", "min_spec_std",
            "min_ab_mean_abs", "max_cold_512_s", "registry_count", "registry_ids_exact")
    print(json.dumps({k: report[k] for k in keys}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
