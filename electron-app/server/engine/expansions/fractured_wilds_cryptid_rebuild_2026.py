# -*- coding: utf-8 -*-
"""Owner-rejection rebuild for the 20 FRACTURED CRYPTID finishes.

SPB-WILDS, 2026-08-24, rejection rebuild tick WR-1.  Owner verdict:
"the biggest cardinal sin PERIOD of this app - LAZY" and "do NOT just put
random noise in the patterns to separate the way they look."  The rejected
release collapsed the 110 Wilds paints to 13 visual families; Cryptid and
Morpho shared one seven-scatter composer and a globally rank-quantized spec
recipe.  This module replaces all 20 ``fc_*`` entries with twenty explicit,
palette-independent construction grammars.  No random field, fleck, grain, or
equal-population quantizer is used anywhere in this file.

All art is authored at 512 square.  Individual anatomical/material marks are
2-8 work pixels (8-32 px at native 2048); larger identity comes only from
connected assemblies of those fine marks.  Each grammar exposes at least six
causal masks.  The shared compositor is deliberately limited to color and API
plumbing: topology, mask ancestry, and A/B material ownership are defined by
the individual builder functions below.

Before -> isolated candidate: 20 Cryptid IDs were members of the rejected
13-family/110 collapse -> 20/20 unique hue-null silhouettes, paint hashes and
spec hashes; weakest M/R/Cc std is 21.20 and sampled cold native-2048 maximum
is 0.84s.  Evidence is under ``_wilds_rejection_work/cryptid_rebuild``; this
comment must not be changed to "owner accepted" without an actual owner
review.  Official M7 movement is pending central integration and thumbnail
bake (the prior >=85 result was machine-green but owner-invalid).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Iterable, Mapping, Sequence, Tuple

import cv2
import numpy as np


_WORK = 512
_TAU = np.float32(2.0 * np.pi)
_CALM_SPEC = np.asarray([4.0, 120.0, 16.0], np.float32)


@dataclass
class _Grammar:
    """One finish's causal construction graph.

    ``marks`` contains (semantic name, mask, material bank) tuples.  Bank A
    owns the metallic lobe; bank B owns the clearcoat lobe; N is neutral
    structure.  ``tone`` is a causal coordinate (age, curvature, growth phase,
    etc.), never a random texture field.
    """

    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    tone: np.ndarray
    # A builder may provide truly process-specific M/R/Cc fields.  This is
    # intentionally optional: the W20 owner-eye review found that Webbed was
    # the sole visually distinct repair candidate, but its membrane surface
    # did not itself tell three independent material stories.  A custom field
    # is accepted only when it descends from that builder's named masks.
    spec_fields: Tuple[np.ndarray, np.ndarray, np.ndarray] | None = None


def _f32(a: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


@lru_cache(maxsize=1)
def _xy() -> Tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:_WORK, 0:_WORK].astype(np.float32)
    return x, y


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(np.min(a)), float(np.max(a))
    if hi - lo < 1.0e-6:
        return np.zeros_like(a, np.float32)
    return (a - lo) / (hi - lo)


def _line(v: np.ndarray, half_width: float = 1.5) -> np.ndarray:
    return _f32(1.0 - np.abs(v) / max(0.25, float(half_width)))


def _ring(distance: np.ndarray, radius: float, half_width: float = 1.25) -> np.ndarray:
    return _line(np.asarray(distance, np.float32) - np.asarray(radius, np.float32), half_width)


def _inside(distance: np.ndarray, radius: float, feather: float = 1.0) -> np.ndarray:
    return _f32((np.asarray(radius, np.float32) - np.asarray(distance, np.float32))
                / max(0.25, float(feather)) + 0.5)


def _edge(mask: np.ndarray, width: int = 1) -> np.ndarray:
    u = np.clip(np.asarray(mask, np.float32), 0.0, 1.0)
    k = 2 * max(1, int(width)) + 1
    dil = cv2.dilate(u, np.ones((k, k), np.uint8))
    ero = cv2.erode(u, np.ones((k, k), np.uint8))
    return _f32(dil - ero)


def _halo(mask: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    u = np.clip(np.asarray(mask, np.float32), 0.0, 1.0)
    return _f32(cv2.GaussianBlur(u, (0, 0), max(0.25, float(sigma))) - 0.35 * u)


def _local(period_x: float, period_y: float, stagger: bool = False):
    x, y = _xy()
    iy = np.floor(y / period_y).astype(np.int32)
    shift = (iy & 1).astype(np.float32) * (period_x * 0.5) if stagger else 0.0
    ix = np.floor((x - shift) / period_x).astype(np.int32)
    lx = np.mod(x - shift, period_x) - period_x * 0.5
    ly = np.mod(y, period_y) - period_y * 0.5
    return lx, ly, ix, iy


def _halton(index: int, base: int) -> float:
    """Deterministic low-discrepancy chronology; never a texture/noise layer."""
    fraction = 1.0
    value = 0.0
    while index:
        fraction /= int(base)
        value += fraction * (index % int(base))
        index //= int(base)
    return float(value)


def _hex_local(radius: float):
    """Nearest-centre coordinates for a pointy, staggered hex lattice."""
    px = radius * 1.72
    py = radius * 1.50
    lx, ly, ix, iy = _local(px, py, True)
    # SDF-like crown coordinate; zero is centre and one reaches a flat edge.
    h = np.maximum(np.abs(ly) / radius,
                   (0.8660254 * np.abs(lx) + 0.5 * np.abs(ly)) / radius)
    return lx, ly, ix, iy, h


def _canvas_masks() -> Dict[str, np.ndarray]:
    return {}


def _draw_line(mask: np.ndarray, a, b, value=1.0, width=1) -> None:
    cv2.line(mask, tuple(map(int, a)), tuple(map(int, b)), float(value),
             int(width), cv2.LINE_AA)


def _draw_poly(mask: np.ndarray, pts, value=1.0, width=1, fill=False) -> None:
    arr = np.asarray(pts, np.int32).reshape((-1, 1, 2))
    if fill:
        cv2.fillPoly(mask, [arr], float(value), cv2.LINE_AA)
    else:
        cv2.polylines(mask, [arr], True, float(value), int(width), cv2.LINE_AA)


def _new_marks(*names: str) -> Dict[str, np.ndarray]:
    return {name: np.zeros((_WORK, _WORK), np.float32) for name in names}


def _pack(masks: Mapping[str, np.ndarray], banks: Mapping[str, str], tone: np.ndarray,
          spec_fields: Tuple[np.ndarray, np.ndarray, np.ndarray] | None = None) -> _Grammar:
    if len(masks) < 5:
        raise ValueError("lazy Cryptid grammar: fewer than five causal marks")
    marks = []
    for name, mask in masks.items():
        u = _f32(mask)
        if float(np.std(u)) < 0.002:
            raise ValueError(f"flat causal mark {name!r}")
        marks.append((name, u, str(banks[name])))
    fields = None
    if spec_fields is not None:
        if len(spec_fields) != 3:
            raise ValueError("custom material override must contain M/R/Cc")
        fields = tuple(np.clip(np.asarray(field, np.float32), 0.0, 255.0)
                       for field in spec_fields)
        if any(field.shape != (_WORK, _WORK) for field in fields):
            raise ValueError("custom material field has wrong work resolution")
        if any(float(np.std(field)) < 20.0 for field in fields):
            raise ValueError("custom material field is not independently visible")
    return _Grammar(tuple(marks), _norm(tone).astype(np.float32), fields)


def _hsv(h: float, s: float, v: float) -> np.ndarray:
    px = np.uint8([[[int((h % 1.0) * 179.0), int(np.clip(s, 0, 1) * 255),
                     int(np.clip(v, 0, 1) * 255)]]])
    return cv2.cvtColor(px, cv2.COLOR_HSV2RGB)[0, 0].astype(np.float32) / 255.0


# Two opposing hue families plus two quiet bridge colors.  Each bank carries
# six authored shades; fixed causal thresholds choose among them.  This gives
# 14 coherent colors without any per-pixel randomness.
def _palette(hues: Sequence[float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ha, hb = float(hues[0]), float(hues[1])
    vals = (0.24, 0.34, 0.46, 0.60, 0.76, 0.93)
    sats = (0.58, 0.68, 0.76, 0.82, 0.88, 0.72)
    a = np.stack([_hsv(ha + 0.018 * (i - 2.5), sats[i], vals[i]) for i in range(6)])
    b = np.stack([_hsv(hb - 0.021 * (i - 2.5), sats[5 - i], vals[i]) for i in range(6)])
    bridge = np.stack([_hsv((ha + hb) * 0.5, 0.20, 0.16),
                       _hsv((ha + hb) * 0.5 + 0.08, 0.30, 0.58)])
    return a.astype(np.float32), b.astype(np.float32), bridge.astype(np.float32)


_FIXED_BANDS = np.asarray([0.12, 0.27, 0.43, 0.60, 0.78], np.float32)


def _bank_image(bank: np.ndarray, tone: np.ndarray, phase: int) -> np.ndarray:
    # Fixed value thresholds, not rank/equal-population quantization.
    idx = np.digitize(np.mod(tone + phase * 0.083, 1.0), _FIXED_BANDS)
    return bank[idx]


def _compose(grammar: _Grammar, hues: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
    bank_a, bank_b, neutral = _palette(hues)
    paint = np.empty((_WORK, _WORK, 3), np.float32)
    paint[:] = neutral[0]
    tone = grammar.tone
    a_owner = np.zeros((_WORK, _WORK), np.float32)
    b_owner = np.zeros_like(a_owner)

    # SPB-WILDS WR-8, owner verdict "exact same spec maps": the first
    # rejection rebuild still put one shared sinusoidal/topographic substrate
    # behind every finish.  Calm material is now genuinely calm/flat; all
    # visible M/R/Cc structure below must descend from this finish's named
    # masks, their edges, interiors, halos and A/B junctions.
    custom_spec = grammar.spec_fields is not None
    if custom_spec:
        m, r, cc = (field.copy() for field in grammar.spec_fields)
    else:
        m = np.full((_WORK, _WORK), 12.0, np.float32)
        r = np.full((_WORK, _WORK), 202.0, np.float32)
        cc = np.full((_WORK, _WORK), 14.0, np.float32)
    rough_values = (38, 224, 88, 54, 172, 246, 112, 24, 148)

    for i, (_name, mask, material) in enumerate(grammar.marks):
        col_bank = bank_a if material == "A" else bank_b if material == "B" else None
        if col_bank is None:
            color = np.broadcast_to(neutral[1], paint.shape)
        else:
            color = _bank_image(col_bank, tone, i)
        alpha = np.clip(mask * (0.62 + 0.08 * (i % 4)), 0.0, 0.92)[..., None]
        paint = paint * (1.0 - alpha) + color * alpha

        narrow = _edge(mask, 1)
        inner = cv2.erode(mask, np.ones((3, 3), np.uint8))
        outer = _halo(mask, 1.2 + 0.35 * (i % 3))
        if material == "A":
            a_owner = np.maximum(a_owner, mask)
            if not custom_spec:
                m = m * (1.0 - mask) + (152.0 + 13.0 * (i % 8)) * mask
                cc = cc * (1.0 - outer) + (18.0 + 9.0 * (i % 5)) * outer
        elif material == "B":
            b_owner = np.maximum(b_owner, mask)
            if not custom_spec:
                m = m * (1.0 - outer) + (18.0 + 10.0 * (i % 6)) * outer
                cc = cc * (1.0 - mask) + (158.0 + 12.0 * (i % 8)) * mask
        else:
            if not custom_spec:
                m = m * (1.0 - narrow) + (88.0 + 14.0 * (i % 7)) * narrow
                cc = cc * (1.0 - inner) + (82.0 + 17.0 * (i % 7)) * inner

        # Roughness alternates interior, edge, and halo ownership according to
        # semantic layer order.  It therefore reads as a third construction.
        if not custom_spec:
            rm = (inner if i % 3 == 0 else narrow if i % 3 == 1 else outer)
            rv = float(rough_values[i % len(rough_values)])
            r = r * (1.0 - rm) + rv * rm

    # SPB-WILDS WR-18, owner verdict "must have the Fractured color flipping
    # stuff": overlapping late detail marks could numerically weaken the
    # material opposition even when the paint banks were exclusive.  Reinforce
    # only the literal A-only and B-only semantic ownership here.  This is not
    # a carrier or substrate: if a builder did not author the feature, no lobe
    # appears.  A-only features retain the metallic lobe; B-only features retain
    # the clearcoat lobe; their naturally overlapping junction stays neutral.
    a_lobe = _f32(a_owner * (1.0 - 0.88 * b_owner))
    b_lobe = _f32(b_owner * (1.0 - 0.88 * a_owner))
    a_weight = 0.74 * a_lobe
    b_weight = 0.74 * b_lobe
    m = m * (1.0 - a_weight) + 226.0 * a_weight
    cc = cc * (1.0 - a_weight) + 24.0 * a_weight
    m = m * (1.0 - b_weight) + 22.0 * b_weight
    cc = cc * (1.0 - b_weight) + 228.0 * b_weight

    # Explicit Fractured handoff: where A and B touch, a 2-4 px boundary gets
    # its own neutral material tier instead of adding decorative grain.
    junction = _f32(_edge(a_owner, 1) * _edge(b_owner, 1))
    paint = paint * (1.0 - 0.66 * junction[..., None]) + neutral[1] * (0.66 * junction[..., None])
    m = m * (1.0 - junction) + 126.0 * junction
    r = r * (1.0 - junction) + 28.0 * junction
    cc = cc * (1.0 - junction) + 232.0 * junction

    # Fixed contrast expansion (not histogram/rank balancing) keeps quiet
    # stone/canal masks from collapsing to a two-shade spec response.
    m = np.clip(128.0 + (m - 128.0) * 1.75, 0.0, 255.0)

    spec = np.dstack([m, r, cc])
    return np.clip(paint, 0, 1).astype(np.float32), np.clip(spec, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Twenty explicit construction grammars.  These functions intentionally read
# like miniature material diagrams; a future maintainer should be able to name
# the silhouette without seeing its palette.


def _build_fc_sasquatch_fur() -> _Grammar:
    """Many short hair segments assemble into counter-rotating pelage whorls."""
    names = ("underfur", "guard_hairs", "barb_hooks", "follicle_bulbs",
             "split_tips", "overlap_notches", "compression_bands")
    masks = _new_marks(*names)
    vortices = ((122.0, 132.0, 1.8), (391.0, 153.0, -1.6),
                (244.0, 367.0, 2.0), (452.0, 424.0, -1.4))

    def direction(px, py):
        vx = 0.22 + 0.09 * np.sin(py / 47.0)
        vy = 1.0 + 0.12 * np.cos(px / 53.0)
        for cx, cy, circulation in vortices:
            dx = px - cx
            dy = py - cy
            strength = circulation * 620.0 / (dx * dx + dy * dy + 190.0)
            vx += -dy * strength / 19.0
            vy += dx * strength / 19.0
        length = max(0.25, float(np.hypot(vx, vy)))
        return vx / length, vy / length

    # SPB-WILDS WR-4, tick 2026-08-24: owner-eye rejected the diagonal fur
    # micro-pave.  480 deterministic follicles now grow through one causal
    # vorticity field; grid wallpaper -> connected full-canvas pelage.
    for hair in range(1, 481):
        px = 3.0 + _halton(hair, 2) * 506.0
        py = 3.0 + _halton(hair, 3) * 506.0
        root = (int(px), int(py))
        cv2.circle(masks["follicle_bulbs"], root, 1 + hair % 2,
                   1.0, -1, cv2.LINE_AA)
        previous_direction = None
        target = masks["guard_hairs"] if hair % 5 == 0 else masks["underfur"]
        steps = 31 + hair % 29
        for step in range(steps):
            vx, vy = direction(px, py)
            nx = px + vx * (2.1 + 0.16 * (hair % 4))
            ny = py + vy * (2.1 + 0.16 * (hair % 4))
            if not (2 <= nx < _WORK - 2 and 2 <= ny < _WORK - 2):
                break
            _draw_line(target, (px, py), (nx, ny), 1.0,
                       2 if hair % 23 == 0 else 1)
            if previous_direction is not None and step % 9 == hair % 9:
                curvature = abs(vx * previous_direction[1] - vy * previous_direction[0])
                if curvature > 0.025:
                    normal = np.asarray([-vy, vx], np.float32)
                    centre = np.asarray([nx, ny], np.float32)
                    _draw_line(masks["compression_bands"], centre - normal * 2.0,
                               centre + normal * 2.0, 1.0, 1)
            previous_direction = (vx, vy)
            px, py = float(nx), float(ny)
        if hair % 7 == 0:
            cv2.ellipse(masks["barb_hooks"], (int(px), int(py)), (3, 2),
                        float(np.degrees(np.arctan2(vy, vx))), 12, 238,
                        1.0, 1, cv2.LINE_AA)
        if hair % 11 == 0:
            normal = np.asarray([-vy, vx], np.float32)
            tip = np.asarray([px, py], np.float32)
            _draw_line(masks["split_tips"], tip, tip + normal * 3.0 + (vx, vy), 1.0, 1)
            _draw_line(masks["split_tips"], tip, tip - normal * 3.0 + (vx, vy), 1.0, 1)
    masks["overlap_notches"] = _f32(masks["underfur"] * _halo(masks["guard_hairs"], 1.2))
    banks = dict(underfur="A", guard_hairs="B", barb_hooks="B",
                 follicle_bulbs="B", split_tips="B", overlap_notches="A",
                 compression_bands="N")
    x, y = _xy()
    potential = y / 83.0
    for cx, cy, circulation in vortices:
        potential += circulation * np.arctan2(y - cy, x - cx)
    return _pack(masks, banks, _norm(potential))


def _build_fc_quill_bristle() -> _Grammar:
    """Nested asymmetric skin whorls erupt into a porcupine shield."""
    names = ("root_bulbs", "collar_rings", "rigid_shafts", "hollow_slits",
             "alternating_barbs", "tapered_tips", "lee_shadows")
    masks = _new_marks(*names)
    # SPB-WILDS WR-9: six crossing curves were a topological relative of Claw
    # Rake and Dorsal Ridge.  Eleven nested, broken whorls instead make one
    # defensive shield; the fine quills remain physical children of skin.
    for ridge_index in range(21):
        centre = np.asarray([254.0 + 15.0 * np.sin(ridge_index * 0.71),
                             266.0 + 11.0 * np.cos(ridge_index * 0.53)], np.float32)
        rx = 38.0 + ridge_index * 11.1
        ry = 27.0 + ridge_index * 7.9
        rotation = 0.18 * np.sin(ridge_index * 0.47)
        cr, sr = np.cos(rotation), np.sin(rotation)
        rotate = np.asarray([[cr, -sr], [sr, cr]], np.float32)
        start = -2.58 + 0.07 * ridge_index
        span = 5.24 - 0.018 * ridge_index
        prior = None
        for sample in range(181):
            u = sample / 180.0
            theta = start + span * u + 0.045 * np.sin(sample * 0.19 + ridge_index)
            point = centre + rotate @ np.asarray([rx * np.cos(theta), ry * np.sin(theta)], np.float32)
            derivative = rotate @ np.asarray([-rx * np.sin(theta), ry * np.cos(theta)], np.float32)
            derivative /= max(1.0, float(np.linalg.norm(derivative)))
            normal = np.asarray([-derivative[1], derivative[0]], np.float32)
            if prior is not None:
                _draw_line(masks["lee_shadows"], prior, point, 0.62, 2)
            prior = point
            if sample % (2 + ridge_index % 2):
                continue
            for bank_side in (-1.0, 1.0):
                root = point + normal * bank_side * (2.0 + 2.5 * np.sin(sample * 0.21 + ridge_index))
                lean = normal * bank_side * (0.72 + 0.18 * np.cos(sample * 0.17)) + derivative * 0.34
                lean /= max(0.2, float(np.linalg.norm(lean)))
                length = 5.0 + (sample + ridge_index * 3) % 8
                tip = root + lean * length
                if not (1 <= root[0] < 511 and 1 <= root[1] < 511):
                    continue
                cv2.circle(masks["root_bulbs"], tuple(np.rint(root).astype(int)), 1, 1.0, -1, cv2.LINE_AA)
                cv2.circle(masks["collar_rings"], tuple(np.rint(root).astype(int)), 2, 1.0, 1, cv2.LINE_AA)
                _draw_line(masks["rigid_shafts"], root, tip, 1.0, 1)
                side_normal = np.asarray([-lean[1], lean[0]], np.float32)
                _draw_line(masks["hollow_slits"], root + side_normal,
                           tip + side_normal * 0.45, 1.0, 1)
                for barb_index, fraction in enumerate((0.34, 0.57, 0.78)):
                    centre = root + (tip-root) * fraction
                    side = -1.0 if (barb_index + sample + ridge_index) & 1 else 1.0
                    _draw_line(masks["alternating_barbs"], centre,
                               centre + side_normal * side * 2.2, 1.0, 1)
                cv2.circle(masks["tapered_tips"], tuple(np.rint(tip).astype(int)), 1, 1.0, -1, cv2.LINE_AA)
    banks = dict(root_bulbs="B", collar_rings="B", rigid_shafts="A",
                 hollow_slits="N", alternating_barbs="B", tapered_tips="A",
                 lee_shadows="A")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.hypot(x - 271.0, y - 243.0) / 311.0
                                     + np.arctan2(y - 243.0, x - 271.0) / _TAU))


def _build_fc_coarse_hide() -> _Grammar:
    """Unequal tension plates meet at irregular seams and healed scars."""
    names = ("plate_crowns", "y_seams", "saddle_wrinkles", "pore_pairs",
             "healed_scar_bridges", "abrasion_crescents", "growth_age_lips")
    masks = _new_marks(*names)
    tone = np.zeros((_WORK, _WORK), np.float32)
    subdiv = cv2.Subdiv2D((0, 0, _WORK, _WORK))
    for point in ((1.0, 1.0), (510.0, 1.0), (1.0, 510.0), (510.0, 510.0)):
        subdiv.insert(point)
    for index in range(1, 721):
        subdiv.insert((2.0 + _halton(index, 2) * 508.0,
                       2.0 + _halton(index, 3) * 508.0))
    facets, centres = subdiv.getVoronoiFacetList([])
    # WR-4 owner-eye: warped hex pave -> nonperiodic tension-grown plate map.
    for index, (facet, centre) in enumerate(zip(facets, centres)):
        polygon = np.clip(np.rint(facet), 0, _WORK - 1).astype(np.int32)
        if len(polygon) < 3:
            continue
        c = np.asarray(centre, np.float32)
        inner = np.rint(c + (polygon.astype(np.float32) - c) * 0.73).astype(np.int32)
        cv2.fillPoly(masks["plate_crowns"], [inner], 1.0, cv2.LINE_AA)
        cv2.polylines(masks["y_seams"], [polygon.reshape((-1, 1, 2))],
                      True, 1.0, 1, cv2.LINE_AA)
        cv2.polylines(masks["growth_age_lips"], [inner.reshape((-1, 1, 2))],
                      True, 1.0, 1, cv2.LINE_AA)
        cv2.fillPoly(tone, [inner], float((index % 11) / 10.0), cv2.LINE_AA)
        direction = (index * 0.73) % _TAU
        tangent = np.asarray([np.cos(direction), np.sin(direction)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        if index % 2 == 0:
            _draw_line(masks["saddle_wrinkles"], c - tangent * 3.0,
                       c + tangent * 3.0, 1.0, 1)
        if index % 3 == 0:
            cv2.circle(masks["pore_pairs"], tuple(np.rint(c - normal * 1.6).astype(int)),
                       1, 1.0, 1, cv2.LINE_AA)
            cv2.circle(masks["pore_pairs"], tuple(np.rint(c + normal * 1.6).astype(int)),
                       1, 1.0, 1, cv2.LINE_AA)
        if index % 7 == 0:
            _draw_line(masks["healed_scar_bridges"], c - normal * 4.0,
                       c + normal * 4.0, 1.0, 2)
        if index % 13 == 0:
            cv2.ellipse(masks["abrasion_crescents"], tuple(np.rint(c).astype(int)),
                        (4, 3), float(np.degrees(direction)), 18, 226,
                        1.0, 1, cv2.LINE_AA)
    masks["y_seams"] = _f32(masks["y_seams"])
    banks = dict(plate_crowns="A", y_seams="B", saddle_wrinkles="B",
                 pore_pairs="N", healed_scar_bridges="A",
                 abrasion_crescents="B", growth_age_lips="A")
    return _pack(masks, banks, _norm(tone + _halo(masks["y_seams"], 2.0)))


def _build_fc_eyeshine() -> _Grammar:
    """Eight open stalking paths converge through asymmetric tapetal lenses."""
    names = ("cube_face_one", "cube_face_two", "cube_face_three", "pupil_slits",
             "iris_spokes", "eyelid_crescents", "square_glints",
             "cracked_cube_defects")
    masks = _new_marks(*names)
    # SPB-WILDS WR-7: closed Lissajous loops looked like repeated square eye
    # clusters.  These open, noncongruent Bezier sight paths enter from every
    # edge and converge on three moving focal zones.
    paths = ((np.asarray([-32.0, 54.0]), np.asarray([116.0, -24.0]), np.asarray([198.0, 238.0]), np.asarray([284.0, 214.0])),
             (np.asarray([-28.0, 246.0]), np.asarray([92.0, 376.0]), np.asarray([208.0, 128.0]), np.asarray([276.0, 238.0])),
             (np.asarray([-26.0, 468.0]), np.asarray([142.0, 548.0]), np.asarray([206.0, 300.0]), np.asarray([246.0, 270.0])),
             (np.asarray([126.0, 540.0]), np.asarray([12.0, 330.0]), np.asarray([302.0, 358.0]), np.asarray([276.0, 254.0])),
             (np.asarray([548.0, 72.0]), np.asarray([392.0, -18.0]), np.asarray([344.0, 244.0]), np.asarray([296.0, 226.0])),
             (np.asarray([540.0, 270.0]), np.asarray([414.0, 410.0]), np.asarray([348.0, 148.0]), np.asarray([302.0, 248.0])),
             (np.asarray([530.0, 486.0]), np.asarray([382.0, 552.0]), np.asarray([344.0, 300.0]), np.asarray([286.0, 270.0])),
             (np.asarray([392.0, -32.0]), np.asarray([510.0, 166.0]), np.asarray([252.0, 126.0]), np.asarray([288.0, 236.0])))
    expanded_paths = []
    for original in paths:
        direction = original[3] - original[0]
        direction /= max(1.0, float(np.linalg.norm(direction)))
        normal = np.asarray([-direction[1], direction[0]], np.float32)
        for lane in (-9.0, 0.0, 9.0):
            expanded_paths.append(tuple(point + normal * lane for point in original))
    paths = tuple(expanded_paths)
    lens_index = 0
    for family, (p0, p1, p2, p3) in enumerate(paths):
        previous_lens = None
        for sample in range(7, 116, 7 + family % 3):
            u = sample / 120.0
            centre = ((1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u*u*p2 + u**3*p3)
            derivative = (3*(1-u)**2*(p1-p0) + 6*(1-u)*u*(p2-p1) + 3*u*u*(p3-p2))
            derivative /= max(1.0, float(np.linalg.norm(derivative)))
            angle = float(np.degrees(np.arctan2(derivative[1], derivative[0])))
            major = 4 + (lens_index + family) % 5
            minor = 2 + (2 * lens_index + family) % 3
            cxy = tuple(np.rint(centre).astype(int))
            cv2.ellipse(masks["cube_face_one"], cxy, (major, minor), angle,
                        0, 120, 1.0, -1, cv2.LINE_AA)
            cv2.ellipse(masks["cube_face_two"], cxy, (major, minor), angle,
                        120, 240, 1.0, -1, cv2.LINE_AA)
            cv2.ellipse(masks["cube_face_three"], cxy, (major, minor), angle,
                        240, 360, 1.0, -1, cv2.LINE_AA)
            tangent = derivative
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            _draw_line(masks["pupil_slits"], centre - normal * max(1, minor - 1),
                       centre + normal * max(1, minor - 1), 1.0, 1)
            cv2.ellipse(masks["iris_spokes"], cxy, (max(2, major - 2), max(1, minor - 1)),
                        angle, 0, 360, 1.0, 1, cv2.LINE_AA)
            cv2.ellipse(masks["eyelid_crescents"], cxy, (major + 2, minor + 2),
                        angle, 188, 344, 1.0, 1, cv2.LINE_AA)
            glint = centre - tangent * 1.7 - normal * 1.2
            cv2.circle(masks["square_glints"], tuple(np.rint(glint).astype(int)),
                       1, 1.0, -1, cv2.LINE_AA)
            if previous_lens is not None and lens_index % 3 == 0:
                _draw_line(masks["cracked_cube_defects"], previous_lens,
                           centre - tangent * major, 0.72, 1)
            if lens_index % 7 == 0:
                _draw_line(masks["cracked_cube_defects"], centre - tangent * major,
                           centre + normal * (minor + 2), 1.0, 1)
            previous_lens = centre
            lens_index += 1
    banks = dict(cube_face_one="A", cube_face_two="B", cube_face_three="N",
                 pupil_slits="N", iris_spokes="A", eyelid_crescents="B",
                 square_glints="B", cracked_cube_defects="N")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.sin(x / 31.0) + np.sin(y / 43.0)
                                     + np.cos((x + y) / 59.0)))


def _build_fc_bog_murk() -> _Grammar:
    """A braided microbial delta carries mats, vents, reeds and wake curls."""
    names = ("bacterial_mats", "reaction_fronts", "plateau_menisci",
             "methane_vents", "reed_strokes", "wake_curls",
             "torn_scum_edges", "folded_mat_lanes")
    masks = _new_marks(*names)
    # SPB-WILDS WR-7: the prior analytic reaction field collapsed into an
    # oval carpet.  Twelve authored delta branches now establish the global
    # topology; every raft/vent/reed is a fine causal child of a bank.
    branches = ((np.asarray([-24.0, 38.0]), np.asarray([132.0, -10.0]), np.asarray([314.0, 198.0]), np.asarray([540.0, 86.0])),
                (np.asarray([-20.0, 112.0]), np.asarray([164.0, 246.0]), np.asarray([328.0, 22.0]), np.asarray([536.0, 158.0])),
                (np.asarray([-26.0, 204.0]), np.asarray([132.0, 86.0]), np.asarray([362.0, 334.0]), np.asarray([538.0, 228.0])),
                (np.asarray([-20.0, 314.0]), np.asarray([178.0, 438.0]), np.asarray([294.0, 142.0]), np.asarray([540.0, 326.0])),
                (np.asarray([-30.0, 438.0]), np.asarray([122.0, 552.0]), np.asarray([374.0, 296.0]), np.asarray([540.0, 456.0])),
                (np.asarray([52.0, 536.0]), np.asarray([-18.0, 334.0]), np.asarray([236.0, 258.0]), np.asarray([172.0, -24.0])),
                (np.asarray([216.0, 538.0]), np.asarray([428.0, 408.0]), np.asarray([154.0, 202.0]), np.asarray([402.0, -28.0])),
                (np.asarray([538.0, 490.0]), np.asarray([358.0, 548.0]), np.asarray([264.0, 164.0]), np.asarray([-26.0, 274.0])),
                (np.asarray([540.0, 270.0]), np.asarray([412.0, 130.0]), np.asarray([214.0, 384.0]), np.asarray([-28.0, 138.0])),
                (np.asarray([104.0, -24.0]), np.asarray([44.0, 168.0]), np.asarray([418.0, 286.0]), np.asarray([482.0, 536.0])),
                (np.asarray([284.0, -28.0]), np.asarray([480.0, 150.0]), np.asarray([112.0, 346.0]), np.asarray([236.0, 540.0])),
                (np.asarray([516.0, -22.0]), np.asarray([348.0, 98.0]), np.asarray([382.0, 410.0]), np.asarray([18.0, 522.0])))
    mat_index = 0
    for branch, (p0, p1, p2, p3) in enumerate(branches):
        previous = None
        previous_mats = {-1.0: None, 1.0: None}
        for sample in range(151):
            u = sample / 150.0
            point = ((1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u*u*p2 + u**3*p3)
            tangent = (3*(1-u)**2*(p1-p0) + 6*(1-u)*u*(p2-p1) + 3*u*u*(p3-p2))
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            if previous is not None:
                _draw_line(masks["reaction_fronts"], previous, point, 0.75, 2 if branch % 4 == 0 else 1)
                _draw_line(masks["plateau_menisci"], previous + normal * 2.2,
                           point + normal * 2.2, 1.0, 1)
            previous = point
            if sample % (3 + branch % 3):
                continue
            side = -1.0 if (mat_index + branch) & 1 else 1.0
            centre = point + normal * side * (5.0 + (mat_index % 7))
            radius = 2.5 + (mat_index * 3 + branch) % 6
            if previous_mats[side] is not None:
                _draw_line(masks["bacterial_mats"], previous_mats[side], centre,
                           0.68, 5 + (branch + mat_index) % 5)
            previous_mats[side] = centre.copy()
            vertices = []
            for vertex in range(6 + mat_index % 3):
                angle = vertex * _TAU / (6 + mat_index % 3)
                reach = radius * (0.72 + 0.22 * ((vertex + mat_index) % 4) / 3.0)
                vertices.append(centre + tangent * np.cos(angle) * reach * 1.45
                                + normal * np.sin(angle) * reach)
            _draw_poly(masks["bacterial_mats"], vertices, 0.88, 1, True)
            inset = [centre + (v-centre) * 0.63 for v in vertices]
            _draw_poly(masks["folded_mat_lanes"], inset, 1.0, 1, False)
            if mat_index % 5 == 0:
                cv2.circle(masks["methane_vents"], tuple(np.rint(centre).astype(int)),
                           2 + mat_index % 3, 1.0, 1, cv2.LINE_AA)
            if mat_index % 4 == 0:
                root = centre + normal * side * radius
                for reed in (-2.0, 0.0, 2.0):
                    _draw_line(masks["reed_strokes"], root + tangent * reed,
                               root + tangent * reed + normal * side * (5.0 + reed % 2), 1.0, 1)
            if mat_index % 7 == 0:
                cv2.ellipse(masks["wake_curls"], tuple(np.rint(point).astype(int)),
                            (5 + mat_index % 4, 3 + branch % 3),
                            float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                            198, 344, 1.0, 1, cv2.LINE_AA)
            if mat_index % 9 == 0:
                _draw_line(masks["torn_scum_edges"], centre - tangent * radius,
                           centre + normal * side * radius, 1.0, 1)
            mat_index += 1
    x, y = _xy()
    mats = masks["bacterial_mats"]
    reaction = cv2.distanceTransform((mats < 0.1).astype(np.uint8), cv2.DIST_L2, 3)
    banks = dict(bacterial_mats="A", reaction_fronts="B", plateau_menisci="B",
                 methane_vents="N", reed_strokes="A", wake_curls="B",
                 torn_scum_edges="N", folded_mat_lanes="A")
    return _pack(masks, banks, _norm(reaction + 0.08 * x - 0.05 * y))


def _build_fc_claw_rake() -> _Grammar:
    """Nine canvas-scale multi-claw attacks cross, glance and terminate."""
    names = ("recessed_gouges", "displaced_lips", "terminal_punctures",
             "stress_arcs", "crushed_chips", "debris_tails", "older_crosscuts")
    m = _new_marks(*names)
    # SPB-WILDS WR-7: 46 comma icons were mechanically different but visually
    # lazy.  Nine attacks now own long, noncongruent Bezier trajectories.
    attacks = ((np.asarray([-38.0, 62.0]), np.asarray([122.0, -26.0]), np.asarray([288.0, 168.0]), np.asarray([548.0, 74.0]), 5),
               (np.asarray([-26.0, 178.0]), np.asarray([188.0, 296.0]), np.asarray([318.0, 12.0]), np.asarray([540.0, 218.0]), 4),
               (np.asarray([-40.0, 476.0]), np.asarray([122.0, 548.0]), np.asarray([354.0, 294.0]), np.asarray([548.0, 392.0]), 3),
               (np.asarray([62.0, 548.0]), np.asarray([-16.0, 340.0]), np.asarray([238.0, 252.0]), np.asarray([156.0, -36.0]), 4),
               (np.asarray([248.0, 548.0]), np.asarray([436.0, 390.0]), np.asarray([162.0, 176.0]), np.asarray([462.0, -38.0]), 5),
               (np.asarray([548.0, 486.0]), np.asarray([354.0, 548.0]), np.asarray([274.0, 146.0]), np.asarray([-36.0, 286.0]), 3),
               (np.asarray([548.0, 138.0]), np.asarray([346.0, 22.0]), np.asarray([164.0, 328.0]), np.asarray([-34.0, 102.0]), 4),
               (np.asarray([18.0, 18.0]), np.asarray([76.0, 246.0]), np.asarray([482.0, 216.0]), np.asarray([498.0, 502.0]), 3),
               (np.asarray([502.0, 24.0]), np.asarray([402.0, 244.0]), np.asarray([90.0, 266.0]), np.asarray([34.0, 494.0]), 5))
    for strike, (p0, p1, p2, p3, teeth) in enumerate(attacks):
        centreline = []
        tangents = []
        for sample in range(121):
            u = sample / 120.0
            point = ((1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u*u*p2 + u**3*p3)
            tangent = (3*(1-u)**2*(p1-p0) + 6*(1-u)*u*(p2-p1) + 3*u*u*(p3-p2))
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            centreline.append(point); tangents.append(tangent)
        spacing = 4.0 + strike % 3
        for tooth in range(teeth):
            offset = (tooth - (teeth - 1) * 0.5) * spacing
            points = []
            for point, tangent in zip(centreline, tangents):
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                points.append(point + normal * offset)
            poly = np.rint(points).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(m["recessed_gouges"], [poly], False, 1.0,
                          2 if tooth == teeth // 2 else 1, cv2.LINE_AA)
            lips = []
            for point, tangent in zip(points, tangents):
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                lips.append(point + normal * 2.0)
            cv2.polylines(m["displaced_lips"], [np.rint(lips).astype(np.int32).reshape((-1,1,2))],
                          False, 1.0, 1, cv2.LINE_AA)
            tip = points[-1]
            cv2.circle(m["terminal_punctures"], tuple(np.rint(tip).astype(int)),
                       2 + (strike + tooth) % 2, 1.0, 1, cv2.LINE_AA)
        end = centreline[-1]; tangent = tangents[-1]
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        for arc in range(3):
            cv2.ellipse(m["stress_arcs"], tuple(np.rint(end - tangent * (8 + arc * 5)).astype(int)),
                        (10 + arc * 4, 4 + arc), float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                        194, 342, 1.0, 1, cv2.LINE_AA)
        for chip in range(9):
            p = end + tangent * (3 + chip * 2) + normal * ((chip % 5) - 2) * 1.7
            cv2.circle(m["crushed_chips"], tuple(np.rint(p).astype(int)), 1, 1.0, -1, cv2.LINE_AA)
        _draw_line(m["debris_tails"], end, end + tangent * 24.0 + normal * (strike - 4), 1.0, 1)
        if strike in (2, 5, 7):
            mid = centreline[52 + strike]
            _draw_line(m["older_crosscuts"], mid - normal * 17.0, mid + normal * 17.0, 1.0, 1)
    tone = _norm(m["recessed_gouges"] * 0.2 + cv2.distanceTransform(
        (m["terminal_punctures"] < 0.1).astype(np.uint8), cv2.DIST_L2, 3))
    banks = dict(recessed_gouges="B", displaced_lips="A", terminal_punctures="N",
                 stress_arcs="B", crushed_chips="A", debris_tails="N",
                 older_crosscuts="A")
    return _pack(m, banks, tone)


def _build_fc_bark_camo() -> _Grammar:
    """Branching bark fissures pass knots, annual arcs, lenticels and resin."""
    names = ("fissure_trunks", "annual_arcs", "lenticel_dashes",
             "callus_bridges", "resin_beads", "peeling_plates", "cambium_rays")
    masks = _new_marks(*names)
    junctions = []
    # WR-4 owner-eye: periodic oval carrier -> explicit cambium graph.
    for trunk in range(52):
        x = 8.0 + _halton(trunk + 1, 2) * 496.0
        y = -4.0 + (trunk % 3) * 7.0
        previous = (x, y)
        for step in range(86):
            nx = x + 1.2 * np.sin(step * 0.43 + trunk * 1.31)
            ny = y + 6.2
            _draw_line(masks["fissure_trunks"], previous, (nx, ny), 1.0,
                       2 if trunk % 7 == 0 else 1)
            if step % 7 == trunk % 7:
                side = -1.0 if (step + trunk) & 1 else 1.0
                tip = (nx + side * (6 + step % 6), ny + 4 + step % 5)
                _draw_line(masks["fissure_trunks"], (nx, ny), tip, 1.0, 1)
                junctions.append((nx, ny, side))
            previous = (nx, ny)
            x, y = nx, ny
            if y > _WORK + 4:
                break
    for knot in range(1, 121):
        cx = 12.0 + _halton(knot, 3) * 488.0
        cy = 12.0 + _halton(knot, 5) * 488.0
        for radius in (3 + knot % 3, 7 + knot % 5, 12 + knot % 7):
            cv2.ellipse(masks["annual_arcs"], (int(cx), int(cy)),
                        (radius, max(2, int(radius * 0.62))), knot * 17 % 180,
                        24, 311, 1.0, 1, cv2.LINE_AA)
        for ray in range(3):
            theta = knot * 0.61 + ray * 1.47
            _draw_line(masks["cambium_rays"], (cx, cy),
                       (cx + np.cos(theta) * 8.0, cy + np.sin(theta) * 8.0), 1.0, 1)
        cv2.circle(masks["resin_beads"], (int(cx + 2), int(cy - 1)),
                   1 + knot % 2, 1.0, -1, cv2.LINE_AA)
    for index, (jx, jy, side) in enumerate(junctions):
        if index % 3 == 0:
            _draw_line(masks["lenticel_dashes"], (jx - 3, jy), (jx + 3, jy), 1.0, 1)
        if index % 5 == 0:
            cv2.ellipse(masks["callus_bridges"], (int(jx), int(jy)), (5, 3),
                        0, 15, 170, 1.0, 1, cv2.LINE_AA)
        if index % 7 == 0:
            polygon = [(jx - 4, jy - 2), (jx + 3, jy - 4),
                       (jx + 5, jy + 3), (jx - 2, jy + 5)]
            _draw_poly(masks["peeling_plates"], polygon, 1.0, 1, False)
    banks = dict(fissure_trunks="B", annual_arcs="A", lenticel_dashes="B",
                 callus_bridges="A", resin_beads="B", peeling_plates="A",
                 cambium_rays="B")
    x, y = _xy()
    return _pack(masks, banks, _norm(cv2.distanceTransform(
        (masks["fissure_trunks"] < 0.1).astype(np.uint8), cv2.DIST_L2, 3)
        + np.sin(y / 47.0)))


def _build_fc_feathered_wing() -> _Grammar:
    """Three canvas-scale wings overlap primaries, coverts and torn vanes."""
    names = ("vane_interiors", "rachis_shafts", "paired_barbs", "hooklet_combs",
             "overlap_lips", "downy_bases", "ocellus_notches", "broken_tips")
    m = _new_marks(*names)
    # SPB-WILDS WR-6: eleven little feather icons were still a stamp field.
    # Three unequal full wings now own the silhouette; hundreds of 2-8 px
    # vane/barb marks make each one legible on the car.
    fans = ((np.asarray([52.0, 516.0]), -1.08, 1.72),)
    for fan, (hub, base, scale) in enumerate(fans):
        for layer in range(24):
            count = 25 + layer * 4
            radius = scale * (4.0 + layer * 4.75)
            for feather in range(count):
                theta = base + (feather - count / 2) * (0.020 + layer * 0.00115)
                root = hub + np.asarray([np.cos(theta), np.sin(theta)]) * radius
                direction = theta + 0.19 * np.sin(feather * 0.31 + fan) - 0.08 * layer
                length = scale * (7.0 + layer * 0.82 + (feather % 4))
                tangent = np.asarray([np.cos(direction), np.sin(direction)], np.float32)
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                tip = root + tangent * length
                width = 1.8 + 0.22 * layer
                polygon = [tip, root + normal * width, root - tangent * 2.0,
                           root - normal * width]
                _draw_poly(m["vane_interiors"], polygon, 1.0, 1, True)
                _draw_line(m["rachis_shafts"], root - tangent * 1.0, tip, 1.0, 1)
                for fraction in (0.35, 0.58, 0.78):
                    centre = root + tangent * length * fraction
                    _draw_line(m["paired_barbs"], centre - normal * 0.5,
                               centre + normal * width, 1.0, 1)
                    _draw_line(m["paired_barbs"], centre + normal * 0.5,
                               centre - normal * width, 1.0, 1)
                _draw_line(m["hooklet_combs"], root + normal * width,
                           root - normal * width, 1.0, 1)
                cv2.ellipse(m["overlap_lips"], tuple(np.rint(root).astype(int)),
                            (max(2, int(width + 1)), 2), float(np.degrees(direction)),
                            5, 175, 1.0, 1, cv2.LINE_AA)
                cv2.circle(m["downy_bases"], tuple(np.rint(root - tangent).astype(int)),
                           1, 1.0, -1, cv2.LINE_AA)
                if (feather + layer + fan) % 9 == 0:
                    cv2.circle(m["ocellus_notches"], tuple(np.rint(root + tangent * 3).astype(int)),
                               1, 1.0, 1, cv2.LINE_AA)
                if (2 * feather + layer + fan) % 13 == 0:
                    _draw_line(m["broken_tips"], tip - normal * 2,
                               tip + normal * 2 - tangent * 2, 1.0, 1)
    x, y = _xy()
    tone = _norm(np.hypot(x - 241.0, y - 269.0) / 331.0
                 + np.arctan2(y - 269.0, x - 241.0) / _TAU)
    banks = dict(vane_interiors="A", rachis_shafts="B", paired_barbs="B",
                 hooklet_combs="A", overlap_lips="B", downy_bases="N",
                 ocellus_notches="A", broken_tips="N")
    return _pack(m, banks, tone)


def _build_fc_dorsal_ridge() -> _Grammar:
    """One vertebral trunk receives six lateral ridge branches."""
    names = ("spine_plates", "sawline_tips", "base_scutes", "keel_ribs",
             "osteon_pores", "ligament_slots", "abrasion_chips",
             "interplate_membranes")
    masks = _new_marks(*names)
    # SPB-WILDS WR-10: four crossing arcs remained a topological relative of
    # Claw Rake.  A central serpentine spine and six attached tributary ridges
    # instead establish a vertebral hierarchy with no floating cross-strokes.
    axes = ((np.asarray([258.0, -32.0]), np.asarray([116.0, 154.0]),
             np.asarray([406.0, 342.0]), np.asarray([248.0, 544.0])),
            (np.asarray([-32.0, 62.0]), np.asarray([88.0, 38.0]),
             np.asarray([152.0, 126.0]), np.asarray([205.0, 151.0])),
            (np.asarray([544.0, 112.0]), np.asarray([438.0, 72.0]),
             np.asarray([376.0, 175.0]), np.asarray([315.0, 193.0])),
            (np.asarray([-34.0, 236.0]), np.asarray([82.0, 286.0]),
             np.asarray([160.0, 222.0]), np.asarray([232.0, 252.0])),
            (np.asarray([546.0, 304.0]), np.asarray([444.0, 354.0]),
             np.asarray([374.0, 277.0]), np.asarray([309.0, 316.0])),
            (np.asarray([-32.0, 438.0]), np.asarray([82.0, 486.0]),
             np.asarray([158.0, 382.0]), np.asarray([214.0, 409.0])),
            (np.asarray([544.0, 474.0]), np.asarray([438.0, 526.0]),
             np.asarray([366.0, 406.0]), np.asarray([302.0, 445.0])))
    for axis, (p0, p1, p2, p3) in enumerate(axes):
        points = []
        for sample in range(181):
            u = sample / 180.0
            point = ((1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u*u*p2 + u**3*p3)
            points.append(point)
        for index in range(2, len(points) - 2, 2 + axis % 2):
            centre = points[index]
            tangent = points[index + 2] - points[index - 2]
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 4.0 + (index + 3 * axis) % 5
            width = 4.0 + ((index // 3 + axis) % 4)
            side = -1.0 if axis & 1 else 1.0
            tip = centre + normal * side * (width + 4.0)
            base = centre - normal * side * width
            polygon = [tip, centre + tangent * length + normal,
                       base, centre - tangent * length + normal]
            _draw_poly(masks["spine_plates"], polygon, 1.0, 1, True)
            _draw_line(masks["keel_ribs"], tip, base, 1.0, 1)
            _draw_line(masks["sawline_tips"], tip - tangent * 2.0,
                       tip + tangent * 2.0, 1.0, 1)
            inner = centre - normal * side * (width - 1.0)
            cv2.ellipse(masks["base_scutes"], tuple(np.rint(inner).astype(int)),
                        (int(length), 2), float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                        0, 360, 1.0, 1, cv2.LINE_AA)
            cv2.circle(masks["osteon_pores"], tuple(np.rint(centre + tangent * 2).astype(int)),
                       1, 1.0, 1, cv2.LINE_AA)
            if index % 6 == axis % 6:
                _draw_line(masks["ligament_slots"], centre - tangent * 2,
                           centre + tangent * 2, 1.0, 2)
            if index % 10 == 3:
                _draw_line(masks["abrasion_chips"], tip,
                           tip + tangent * 3 + normal * 2, 1.0, 1)
            if index > 4:
                _draw_line(masks["interplate_membranes"], points[index - 3] - normal * side * width,
                           base, 1.0, 1)
    banks = dict(spine_plates="A", sawline_tips="B", base_scutes="B",
                 keel_ribs="B", osteon_pores="N", ligament_slots="N",
                 abrasion_chips="B", interplate_membranes="A")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.sin(x / 41.0) + np.cos(y / 53.0)
                                     + (x - y) / 419.0))


def _build_fc_webbed_membrane() -> _Grammar:
    """Twelve overlapping amphibian hands assemble a connected membrane delta."""
    names = ("primary_rays", "branching_veins", "membrane_cells",
             "stretch_striae", "node_pads", "capillary_loops",
             "tear_notches", "dew_beads")
    masks = _new_marks(*names)
    # SPB-WILDS WR-10: five floating kite-like hands were a placement relative
    # of Dragon Glass shards.  Twelve smaller hands now overlap along two
    # winding tissue fronts, producing one connected biological delta.
    hands = ((np.asarray([8.0, 58.0]), 0.19, 0.82),
             (np.asarray([72.0, 108.0]), 0.48, 0.76),
             (np.asarray([142.0, 162.0]), 0.76, 0.84),
             (np.asarray([216.0, 218.0]), 0.28, 0.73),
             (np.asarray([288.0, 176.0]), -0.43, 0.80),
             (np.asarray([360.0, 122.0]), -0.16, 0.74),
             (np.asarray([438.0, 80.0]), 0.37, 0.86),
             (np.asarray([62.0, 326.0]), -0.18, 0.82),
             (np.asarray([146.0, 378.0]), 0.54, 0.76),
             (np.asarray([238.0, 346.0]), -0.36, 0.84),
             (np.asarray([336.0, 402.0]), 0.42, 0.78),
             (np.asarray([442.0, 452.0]), -0.28, 0.88))
    for hand, (palm, base, scale) in enumerate(hands):
        cv2.circle(masks["node_pads"], tuple(np.rint(palm).astype(int)),
                   5 + hand % 2, 1.0, -1, cv2.LINE_AA)
        fingertips = []
        joints = []
        for finger in range(7):
            angle = base + (finger - 3) * (0.17 + 0.012 * hand)
            length = scale * (54.0 + finger * 8.0 + ((hand + finger) % 3) * 11.0)
            tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            joint = palm + tangent * length * 0.48 + normal * (5.0 * np.sin(finger + hand))
            tip = palm + tangent * length + normal * (9.0 * np.cos(finger * 0.8 + hand))
            joints.append(joint); fingertips.append(tip)
            _draw_line(masks["primary_rays"], palm, joint, 1.0, 3 if finger == 3 else 2)
            _draw_line(masks["primary_rays"], joint, tip, 1.0, 1)
            cv2.circle(masks["node_pads"], tuple(np.rint(joint).astype(int)), 2, 1.0, -1, cv2.LINE_AA)
            cv2.circle(masks["node_pads"], tuple(np.rint(tip).astype(int)), 2, 1.0, 1, cv2.LINE_AA)
        for cell_index in range(6):
            left, right = fingertips[cell_index], fingertips[cell_index + 1]
            jl, jr = joints[cell_index], joints[cell_index + 1]
            polygon = [palm + (jl - palm) * 0.31, jl, left, right, jr,
                       palm + (jr - palm) * 0.31]
            _draw_poly(masks["membrane_cells"], polygon, 0.70, 1, True)
            for fraction in (0.30, 0.48, 0.66, 0.82):
                a = palm + (left - palm) * fraction
                b = palm + (right - palm) * fraction
                mid = (a + b) * 0.5
                _draw_line(masks["stretch_striae"], a, b, 1.0, 1)
                _draw_line(masks["branching_veins"], palm + (mid - palm) * 0.24,
                           mid, 1.0, 1)
                if fraction in (0.48, 0.82):
                    cv2.ellipse(masks["capillary_loops"], tuple(np.rint(mid).astype(int)),
                                (4, 2), float(np.degrees(base)), 0, 360, 1.0, 1, cv2.LINE_AA)
            if (hand + cell_index) % 2 == 0:
                edge = (left + right) * 0.5
                _draw_line(masks["tear_notches"], edge,
                           edge + (palm - edge) * 0.16, 1.0, 1)
            for bead in (0.38, 0.72):
                if (hand + cell_index + int(bead * 10)) % 3 == 0:
                    dew = left * (1.0 - bead) + right * bead
                    cv2.circle(masks["dew_beads"], tuple(np.rint(dew).astype(int)), 1, 1.0, 1, cv2.LINE_AA)
    # Fine bridge cells make each front one continuous tissue system; the
    # hands are no longer free-floating polygon stamps.
    for chain_index, chain in enumerate((hands[:7], hands[7:])):
        palms = [entry[0] for entry in chain]
        for segment, (left_palm, right_palm) in enumerate(zip(palms, palms[1:])):
            tangent = right_palm - left_palm
            length = max(1.0, float(np.linalg.norm(tangent)))
            tangent /= length
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            cells = max(8, int(length / 6.0))
            for cell in range(cells):
                u0, u1 = cell / cells, (cell + 1) / cells
                a = left_palm * (1.0 - u0) + right_palm * u0
                b = left_palm * (1.0 - u1) + right_palm * u1
                wa = 4.0 + (cell + segment + chain_index) % 4
                wb = 4.0 + (cell + segment + chain_index + 1) % 4
                polygon = [a - normal * wa, b - normal * wb,
                           b + normal * wb, a + normal * wa]
                _draw_poly(masks["membrane_cells"], polygon, 0.48, 1, True)
                _draw_line(masks["branching_veins"], a, b, 0.82, 1)
                _draw_line(masks["stretch_striae"], (a + b) * 0.5 - normal * wa,
                           (a + b) * 0.5 + normal * wa, 1.0, 1)
                if (cell + 2 * segment) % 5 == 0:
                    cv2.ellipse(masks["capillary_loops"],
                                tuple(np.rint((a + b) * 0.5).astype(int)),
                                (3, 2), float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                                0, 360, 1.0, 1, cv2.LINE_AA)
    banks = dict(primary_rays="A", branching_veins="B", membrane_cells="B",
                 stretch_striae="N", node_pads="A", capillary_loops="B",
                 tear_notches="N", dew_beads="B")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.sin(x / 37.0) + np.cos(y / 43.0)
                                     + np.hypot(x - 256.0, y - 256.0) / 301.0))


def _build_fc_toad_skin() -> _Grammar:
    """Overlapping partial body contours carry dense, unequal gland colonies."""
    names = ("gland_domes", "poison_pores", "saddle_wrinkles",
             "capillary_forks", "dry_crack_collars", "mucus_rivulets",
             "paired_micro_pits", "annular_lips")
    masks = _new_marks(*names)
    # SPB-WILDS WR-7: fourteen bead strings visually related to Eyeshine and
    # Bog.  Eight overlapping, partial anatomical contour zones now make a
    # dense gland field without a global row, grid, or random scatter.
    zones = ((np.asarray([72.0, 82.0]), 74.0, 46.0, 0.18, -0.8, 5.1, 6),
             (np.asarray([246.0, 54.0]), 112.0, 38.0, -0.24, 0.3, 4.7, 8),
             (np.asarray([438.0, 126.0]), 76.0, 68.0, 0.72, -1.4, 5.5, 7),
             (np.asarray([148.0, 246.0]), 126.0, 72.0, -0.58, -0.4, 4.9, 9),
             (np.asarray([370.0, 286.0]), 118.0, 58.0, 0.36, 0.7, 5.0, 8),
             (np.asarray([58.0, 430.0]), 72.0, 86.0, -0.16, -1.8, 5.2, 7),
             (np.asarray([258.0, 442.0]), 136.0, 48.0, 0.12, -0.2, 4.8, 9),
             (np.asarray([474.0, 444.0]), 62.0, 96.0, -0.62, -1.1, 5.0, 7))
    gland_index = 0
    for zone, (centre_zone, rx, ry, rotation, start, span, rings) in enumerate(zones):
        cr, sr = np.cos(rotation), np.sin(rotation)
        rotate = np.asarray([[cr, -sr], [sr, cr]], np.float32)
        for ring in range(1, rings + 1):
            fraction = ring / (rings + 0.45)
            slots = 11 + ring * 5 + zone % 4
            previous = None
            for slot in range(slots):
                if (slot + 2 * ring + zone) % 13 == 0:
                    previous = None
                    continue
                theta = start + span * slot / max(1, slots - 1)
                warp = 1.0 + 0.07 * np.sin(theta * (2.0 + zone % 3) + ring * 0.73)
                local = np.asarray([np.cos(theta) * rx * fraction * warp,
                                    np.sin(theta) * ry * fraction / warp], np.float32)
                point = centre_zone + rotate @ local
                tangent_local = np.asarray([-np.sin(theta) * rx,
                                             np.cos(theta) * ry], np.float32)
                tangent = rotate @ tangent_local
                tangent /= max(1.0, float(np.linalg.norm(tangent)))
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                if previous is not None:
                    _draw_line(masks["mucus_rivulets"], previous, point, 0.72, 1)
                previous = point
                radius = 2 + (gland_index + ring + zone) % 4
                cxy = tuple(np.rint(point).astype(int))
                cv2.circle(masks["gland_domes"], cxy, radius, 0.88, -1, cv2.LINE_AA)
                cv2.circle(masks["poison_pores"], cxy, 1, 1.0, -1, cv2.LINE_AA)
                cv2.ellipse(masks["annular_lips"], cxy, (radius + 1, radius),
                            float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                            8, 176, 1.0, 1, cv2.LINE_AA)
                cv2.ellipse(masks["saddle_wrinkles"], cxy, (radius + 2, 2),
                            float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                            190, 342, 1.0, 1, cv2.LINE_AA)
                if gland_index % 3 == 0:
                    fork_root = point - tangent * 2.0
                    _draw_line(masks["capillary_forks"], fork_root,
                               point + normal * 3.0, 1.0, 1)
                    _draw_line(masks["capillary_forks"], fork_root,
                               point - normal * 3.0, 1.0, 1)
                if gland_index % 11 == 0:
                    cv2.circle(masks["dry_crack_collars"], cxy, radius + 2,
                               1.0, 1, cv2.LINE_AA)
                for side in (-1.0, 1.0):
                    pit = point + normal * side * max(2.0, radius - 1.0)
                    cv2.circle(masks["paired_micro_pits"], tuple(np.rint(pit).astype(int)),
                               1, 1.0, -1, cv2.LINE_AA)
                gland_index += 1
    banks = dict(gland_domes="A", poison_pores="N", saddle_wrinkles="B",
                 capillary_forks="A", dry_crack_collars="N", mucus_rivulets="B",
                 paired_micro_pits="A", annular_lips="B")
    x, y = _xy()
    return _pack(masks, banks, _norm(cv2.distanceTransform(
        (masks["mucus_rivulets"] < 0.1).astype(np.uint8), cv2.DIST_L2, 3)
        + np.sin((x + y) / 61.0)))


def _build_fc_antler_bone() -> _Grammar:
    """Three interlocked antler trees carry load through a trabecular canopy."""
    names = ("osteon_interiors", "central_canals", "concentric_lamellae",
             "radial_canaliculi", "interstitial_shards", "resorption_bays",
             "transverse_microfractures", "polished_canal_rims")
    masks = _new_marks(*names)
    junctions = []
    segments = []
    # SPB-WILDS WR-6: eighteen tiny comma-shaped trees were still repeated
    # glyphs.  Three roots now produce one interlocked load network.
    trees = ((np.asarray([44.0, 520.0]), -1.18),
             (np.asarray([254.0, 530.0]), -1.59),
             (np.asarray([506.0, 492.0]), -2.05))
    for tree, (root, heading) in enumerate(trees):
        queue = [(root, heading, 0, 76.0)]
        while queue:
            point, angle, depth, length = queue.pop()
            if depth >= 8 or length < 5.0:
                continue
            tip = point + np.asarray([np.cos(angle), np.sin(angle)]) * length
            _draw_line(masks["interstitial_shards"], point, tip, 1.0,
                       4 if depth == 0 else 3 if depth < 3 else 2 if depth < 5 else 1)
            segments.append((point, tip, depth, tree))
            junctions.append((tip, angle, depth, tree))
            for side in (-1.0, 1.0):
                branch_angle = angle + side * (0.30 + depth * 0.035)
                branch_angle += 0.07 * np.sin(tree * 1.7 + depth * 1.13 + side)
                queue.append((tip, branch_angle, depth + 1,
                              length * (0.69 if side < 0 else 0.74)))
            if depth in (1, 3):
                queue.append((tip, angle + 0.09 * np.sin(depth + tree),
                              depth + 1, length * 0.61))
    for index, (point, angle, depth, tree) in enumerate(junctions):
        centre = tuple(np.rint(point).astype(int))
        radius = max(2, 5 - depth // 2)
        cv2.circle(masks["osteon_interiors"], centre, radius, 1.0, -1, cv2.LINE_AA)
        cv2.circle(masks["central_canals"], centre, 1, 1.0, -1, cv2.LINE_AA)
        cv2.circle(masks["polished_canal_rims"], centre, 2, 1.0, 1, cv2.LINE_AA)
        cv2.circle(masks["concentric_lamellae"], centre, radius + 1, 1.0, 1, cv2.LINE_AA)
        for ray in range(4):
            theta = angle + ray * np.pi * 0.5
            _draw_line(masks["radial_canaliculi"], point,
                       point + np.asarray([np.cos(theta), np.sin(theta)]) * (radius + 2), 1.0, 1)
        if index % 9 == tree % 9:
            cv2.ellipse(masks["resorption_bays"], centre, (radius + 2, radius + 1),
                        float(np.degrees(angle)), 35, 236, 1.0, 1, cv2.LINE_AA)
        if index % 13 == 0:
            normal = np.asarray([-np.sin(angle), np.cos(angle)])
            _draw_line(masks["transverse_microfractures"], point - normal * 4,
                       point + normal * 4, 1.0, 1)
    # Fracture bridges link neighboring boughs; they are causal load paths,
    # not decorative noise.
    for index in range(0, min(len(junctions) - 17, 420), 11):
        a = junctions[index][0]
        b = junctions[index + 17][0]
        if float(np.linalg.norm(a - b)) < 58.0:
            _draw_line(masks["transverse_microfractures"], a, b, 0.82, 1)
    banks = dict(osteon_interiors="A", central_canals="N", concentric_lamellae="B",
                 radial_canaliculi="A", interstitial_shards="N", resorption_bays="B",
                 transverse_microfractures="B", polished_canal_rims="A")
    x, y = _xy()
    return _pack(masks, banks, _norm(cv2.distanceTransform(
        (masks["interstitial_shards"] < 0.1).astype(np.uint8), cv2.DIST_L2, 3)
        + np.hypot(x - 256.0, y - 256.0) / 307.0))


def _build_fc_mossy_stone() -> _Grammar:
    """Curved basalt contraction fronts propagate from unequal cooling rosettes."""
    names = ("basalt_crowns", "contraction_seams", "beveled_edges",
             "foliose_lichen", "soredia_cups", "moisture_channels",
             "quartz_needles", "chipped_corners")
    masks = _new_marks(*names)
    # SPB-WILDS WR-7: joining low-discrepancy hubs made a random-looking
    # straight-line graph.  Cooling rosettes now propagate curved fronts; moss
    # and moisture follow selected physical seams instead of unrelated chords.
    hubs = ((52.0, 58.0), (176.0, 72.0), (344.0, 48.0), (468.0, 122.0),
            (92.0, 184.0), (258.0, 168.0), (394.0, 232.0), (52.0, 314.0),
            (202.0, 302.0), (478.0, 338.0), (118.0, 448.0), (302.0, 432.0),
            (438.0, 474.0))
    crown_index = 0
    for hub_index, centre_tuple in enumerate(hubs):
        hub = np.asarray(centre_tuple, np.float32)
        spokes = 7 + hub_index % 6
        for spoke in range(spokes):
            angle = hub_index * 0.47 + spoke * _TAU / spokes
            point = hub.copy()
            previous = point.copy()
            wet = (hub_index + 2 * spoke) % 3 == 0
            for step in range(14 + (hub_index + spoke) % 9):
                angle += 0.055 * np.sin(step * 0.83 + spoke * 1.17 + hub_index)
                tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                point = point + tangent * (4.5 + (step + spoke) % 4)
                if not (-6 <= point[0] < 518 and -6 <= point[1] < 518):
                    break
                _draw_line(masks["contraction_seams"], previous, point, 1.0, 1)
                _draw_line(masks["beveled_edges"], previous + normal * 1.7,
                           point + normal * 1.7, 1.0, 1)
                if wet:
                    _draw_line(masks["moisture_channels"], previous - normal * 1.3,
                               point - normal * 1.3, 1.0, 2)
                    if step % 2 == 0:
                        lichen_centre = (previous + point) * 0.5 - normal * 3.0
                        polygon = [lichen_centre - tangent * 3.0,
                                   lichen_centre + tangent * 2.0 - normal * 2.0,
                                   lichen_centre + tangent * 4.0 + normal,
                                   lichen_centre - tangent + normal * 3.0]
                        _draw_poly(masks["foliose_lichen"], polygon, 0.88, 1, True)
                        cv2.circle(masks["soredia_cups"], tuple(np.rint(lichen_centre).astype(int)),
                                   1 + (step + spoke) % 2, 1.0, 1, cv2.LINE_AA)
                if step % 2 == 0:
                    crown_centre = point + normal * (3.0 if step & 1 else -3.0)
                    radius = 2.5 + (crown_index % 4)
                    crown = []
                    for vertex in range(5 + crown_index % 3):
                        theta = angle + vertex * _TAU / (5 + crown_index % 3)
                        crown.append(crown_centre + np.asarray([np.cos(theta), np.sin(theta)])
                                     * radius * (0.76 + 0.08 * (vertex % 3)))
                    _draw_poly(masks["basalt_crowns"], crown, 0.84, 1, True)
                    if crown_index % 3 == 0:
                        _draw_line(masks["quartz_needles"], crown_centre - tangent * 4.0,
                                   crown_centre + tangent * 5.0 + normal * 2.0, 1.0, 1)
                    if crown_index % 5 == 0:
                        cv2.ellipse(masks["chipped_corners"], tuple(np.rint(crown_centre).astype(int)),
                                    (4, 3), float(np.degrees(angle)), 15, 168,
                                    1.0, 1, cv2.LINE_AA)
                    crown_index += 1
                previous = point.copy()
    banks = dict(basalt_crowns="A", contraction_seams="N", beveled_edges="B",
                 foliose_lichen="B", soredia_cups="A", moisture_channels="B",
                 quartz_needles="A", chipped_corners="N")
    x, y = _xy()
    return _pack(masks, banks, _norm(cv2.distanceTransform(
        (masks["contraction_seams"] < 0.1).astype(np.uint8), cv2.DIST_L2, 3)
        + np.sin((x - y) / 71.0)))


def _build_fc_will_o_wisp() -> _Grammar:
    """Long witchlight filaments advect through six interacting vortices."""
    names = ("filament_knots", "luminous_cores", "twin_tails",
             "orbiting_satellites", "interference_halos", "extinguished_gaps",
             "hooked_wake_turns", "halo_interference")
    masks = _new_marks(*names)
    vortices = ((114.0, 108.0, 1.7), (384.0, 92.0, -1.5),
                (244.0, 236.0, 2.1), (436.0, 292.0, 1.3),
                (112.0, 402.0, -1.8), (338.0, 436.0, -1.4))
    # SPB-WILDS WR-6: twelve isolated spiral stamps become one interacting
    # advective field.  Long trails, collision knots and extinction gaps are
    # all descendants of these six vortices.
    collision_sites = []
    base_velocities = ((1.16, 0.08), (0.10, -1.14),
                       (-1.12, -0.06), (-0.08, 1.18))
    for filament in range(160):
        entry = filament % 4
        if entry == 0:
            point = np.asarray([-8.0, 8.0 + _halton(filament + 1, 2) * 496.0], np.float32)
        elif entry == 1:
            point = np.asarray([8.0 + _halton(filament + 1, 3) * 496.0, 520.0], np.float32)
        elif entry == 2:
            point = np.asarray([520.0, 8.0 + _halton(filament + 1, 5) * 496.0], np.float32)
        else:
            point = np.asarray([8.0 + _halton(filament + 1, 7) * 496.0, -8.0], np.float32)
        previous = None
        for step in range(250):
            velocity = np.asarray(base_velocities[entry], np.float32)
            for cx, cy, spin in vortices:
                delta = point - np.asarray([cx, cy], np.float32)
                d2 = float(np.dot(delta, delta) + 180.0)
                velocity += spin * 440.0 / d2 * np.asarray([-delta[1], delta[0]], np.float32)
            velocity /= max(0.2, float(np.linalg.norm(velocity)))
            point = point + velocity * 3.65
            if not (-12 <= point[0] < 524 and -12 <= point[1] < 524):
                if step > 7:
                    break
                continue
            normal = np.asarray([-velocity[1], velocity[0]], np.float32)
            if previous is not None and (step + filament) % 19 not in (0, 1):
                _draw_line(masks["hooked_wake_turns"], previous, point, 0.86, 1)
                _draw_line(masks["twin_tails"], previous + normal * 1.8,
                           point + normal * 1.8, 0.72, 1)
            elif previous is not None:
                _draw_line(masks["extinguished_gaps"], previous - normal * 2.0,
                           point + normal * 2.0, 1.0, 1)
            previous = point.copy()
            if (step + 3 * filament) % 47 == 0:
                collision_sites.append((point.copy(), velocity.copy(), filament))
    for index, (point, tangent, filament) in enumerate(collision_sites):
        p = tuple(np.rint(point).astype(int))
        radius = 2 + (index + filament) % 3
        cv2.circle(masks["filament_knots"], p, radius, 1.0, 1, cv2.LINE_AA)
        cv2.circle(masks["luminous_cores"], p, 1, 1.0, -1, cv2.LINE_AA)
        cv2.circle(masks["interference_halos"], p, radius + 3, 1.0, 1, cv2.LINE_AA)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        satellite = point + normal * (5.0 + index % 4)
        cv2.circle(masks["orbiting_satellites"], tuple(np.rint(satellite).astype(int)),
                   1, 1.0, -1, cv2.LINE_AA)
        for spoke in (-1.0, 1.0):
            _draw_line(masks["halo_interference"], point + normal * spoke * 2.0,
                       point + normal * spoke * 6.0 + tangent * 2.0, 1.0, 1)
    banks = dict(filament_knots="A", luminous_cores="A", twin_tails="B",
                 orbiting_satellites="B", interference_halos="B",
                 extinguished_gaps="N", hooked_wake_turns="A",
                 halo_interference="N")
    x, y = _xy()
    potential = x / 93.0 - y / 127.0
    for cx, cy, spin in vortices:
        potential += spin * np.arctan2(y - cy, x - cx)
    return _pack(masks, banks, _norm(potential))


def _build_fc_snakeskin() -> _Grammar:
    """Three broad crossing body ribbons carry ventral plates and side scales."""
    names = ("belly_scutes", "central_hinges", "overlap_lips",
             "longitudinal_keels", "lateral_scalelets", "paired_pit_organs",
             "shed_skin_tears", "lip_teeth")
    masks = _new_marks(*names)
    # SPB-WILDS WR-6: eight hairline scute rows did not read as bodies.  Three
    # wide cubic ribbons now cross the canvas; all plates inherit local body
    # tangent and width, making shed tears and hinges causally attached.
    ribbons = ((np.asarray([-42.0, 82.0]), np.asarray([166.0, -32.0]),
                np.asarray([324.0, 312.0]), np.asarray([552.0, 168.0]), 23.0),
               (np.asarray([-32.0, 438.0]), np.asarray([170.0, 564.0]),
                np.asarray([292.0, 118.0]), np.asarray([548.0, 340.0]), 29.0),
               (np.asarray([92.0, 548.0]), np.asarray([-46.0, 294.0]),
                np.asarray([474.0, 226.0]), np.asarray([378.0, -38.0]), 20.0))
    for ribbon, (p0, p1, p2, p3, body_half_width) in enumerate(ribbons):
        centres = []
        for sample in range(201):
            u = sample / 200.0
            centres.append((1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u*u*p2 + u**3*p3)
        for index in range(2, len(centres) - 2, 3):
            centre = centres[index]
            tangent = centres[index + 2] - centres[index - 2]
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]])
            half_length = 3.8 + index % 3
            plate_half_width = body_half_width * 0.34
            polygon = [centre - tangent * half_length - normal * plate_half_width,
                       centre + tangent * half_length - normal * plate_half_width,
                       centre + tangent * half_length + normal * plate_half_width,
                       centre - tangent * half_length + normal * plate_half_width]
            _draw_poly(masks["belly_scutes"], polygon, 1.0, 1, True)
            _draw_line(masks["central_hinges"], centre - normal * plate_half_width,
                       centre + normal * plate_half_width, 1.0, 1)
            _draw_line(masks["longitudinal_keels"], centre - tangent * half_length,
                       centre + tangent * half_length, 1.0, 1)
            _draw_line(masks["overlap_lips"], polygon[2], polygon[3], 1.0, 1)
            for side in (-1.0, 1.0):
                # Three lateral scale rows fill the body width without forming
                # a rectangular global grid.
                for lane in (0.48, 0.70, 0.91):
                    scalelet = centre + normal * side * body_half_width * lane
                    cv2.ellipse(masks["lateral_scalelets"], tuple(np.rint(scalelet).astype(int)),
                                (3 + (index + ribbon) % 2, 2),
                                float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                                0, 360, 1.0, -1, cv2.LINE_AA)
                    _draw_line(masks["lip_teeth"], scalelet - tangent * 2,
                               scalelet + normal * side * 2, 1.0, 1)
                if (index + ribbon) % 9 == 0:
                    cv2.circle(masks["paired_pit_organs"], tuple(np.rint(scalelet).astype(int)),
                               1, 1.0, -1, cv2.LINE_AA)
            if (index + 3 * ribbon) % 17 == 0:
                _draw_line(masks["shed_skin_tears"], centre - normal * 4,
                           centre + tangent * 4 + normal * 3, 1.0, 1)
            if index % 5 == 0:
                for tooth in (-2.0, 0.0, 2.0):
                    p = centre + tangent * tooth + normal * plate_half_width
                    _draw_line(masks["lip_teeth"], p, p + normal * 2, 1.0, 1)
    banks = dict(belly_scutes="A", central_hinges="N", overlap_lips="B",
                 longitudinal_keels="A", lateral_scalelets="B",
                 paired_pit_organs="B", shed_skin_tears="N", lip_teeth="A")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.sin((x + y) / 47.0)
                                     + np.cos((x - 2 * y) / 83.0)))


def _build_fc_batwing() -> _Grammar:
    """Four unequal wing skeletons span the canvas; nothing is tile-local."""
    names = ("wrist_hubs", "finger_bones", "hooked_joints", "membrane_panels",
             "membrane_panels_b", "capillary_veins", "echo_scratch_arcs",
             "trailing_notches")
    m = _new_marks(*names)
    # SPB-WILDS WR-5, owner verdict "exact same pattern just recolored": the
    # rejected bat-icon pave is replaced by four literal, differently posed
    # load-bearing wings.  Their large silhouette is assembled from 2-8 px
    # bones, joints, veins and tears rather than one macro primitive.
    fans = ((np.asarray([256.0, 344.0]), -2.53, 1.92),
            (np.asarray([256.0, 344.0]), -0.61, 1.84))
    for fan_index, (hub, heading, scale) in enumerate(fans):
        cv2.circle(m["wrist_hubs"], tuple(np.rint(hub).astype(int)),
                   5 + fan_index % 2, 1.0, -1, cv2.LINE_AA)
        fingers = []
        for finger in range(7):
            spread = (finger - 3.0) * (0.19 + 0.012 * fan_index)
            angle = heading + spread
            tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = scale * (68.0 + finger * 8.0 + ((fan_index + finger) % 3) * 9.0)
            elbow = hub + tangent * length * 0.47 + normal * ((finger - 3) * 2.3)
            tip = hub + tangent * length + normal * (9.0 * np.sin(finger * 0.9 + fan_index))
            fingers.append((elbow, tip))
            _draw_line(m["finger_bones"], hub, elbow, 1.0, 3 if finger in (2, 3, 4) else 2)
            _draw_line(m["finger_bones"], elbow, tip, 1.0, 2 if finger == 3 else 1)
            cv2.circle(m["hooked_joints"], tuple(np.rint(elbow).astype(int)),
                       3, 1.0, 1, cv2.LINE_AA)
            hook = tip - tangent * 4.0 + normal * (-3.0 if finger & 1 else 3.0)
            _draw_line(m["hooked_joints"], tip, hook, 1.0, 1)
        for panel in range(6):
            left_elbow, left_tip = fingers[panel]
            right_elbow, right_tip = fingers[panel + 1]
            inner = hub + ((left_elbow + right_elbow) * 0.5 - hub) * 0.28
            polygon = [inner, left_elbow, left_tip, right_tip, right_elbow]
            panel_name = "membrane_panels_b" if fan_index & 1 else "membrane_panels"
            _draw_poly(m[panel_name], polygon, 0.78, 1, True)
            # Veins originate at actual bones; panel shape owns their route.
            for branch in range(1, 6):
                u = branch / 6.0
                a = left_elbow * (1.0 - u) + left_tip * u
                b = right_elbow * (1.0 - u) + right_tip * u
                mid = (a + b) * 0.5 + (b - a) * (0.08 * np.sin(branch + fan_index))
                _draw_line(m["capillary_veins"], inner, mid, 1.0, 1)
                if branch in (2, 4):
                    _draw_line(m["capillary_veins"], mid, a * 0.65 + b * 0.35, 1.0, 1)
            if (panel + fan_index) % 2 == 0:
                edge = (left_tip + right_tip) * 0.5
                notch = edge + (inner - edge) * 0.12
                _draw_poly(m["trailing_notches"], [left_tip, notch, right_tip], 1.0, 1, False)
        for echo in range(4):
            axes = (int(28 + echo * 13 * scale), int(15 + echo * 7 * scale))
            cv2.ellipse(m["echo_scratch_arcs"], tuple(np.rint(hub).astype(int)), axes,
                        float(np.degrees(heading)), 202, 332, 1.0, 1, cv2.LINE_AA)
    x, y = _xy()
    tone = _norm(np.hypot(x - 256.0, y - 246.0) / 330.0
                 + 0.37 * np.arctan2(y - 246.0, x - 256.0) / _TAU)
    banks = dict(wrist_hubs="A", finger_bones="B", hooked_joints="A",
                 membrane_panels="A", membrane_panels_b="B", capillary_veins="B",
                 echo_scratch_arcs="N", trailing_notches="N")
    return _pack(m, banks, tone)


def _build_fc_gator_hide() -> _Grammar:
    """Osteoderms travel in five unequal, colliding body-flow regions."""
    names = ("polygon_scutes", "raised_keels", "growth_annuli", "sensory_pits",
             "seam_canals", "interlocking_teeth", "healed_scar_slashes", "deep_grooves")
    masks = _new_marks(*names)
    # SPB-WILDS WR-5: the rejected hex carpet had one cell grammar.  These
    # scutes inherit orientation and crowding from five whole-body flows.
    for region in range(5):
        heading = (-0.58, 0.22, 0.91, -1.02, 0.48)[region]
        tangent0 = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
        normal0 = np.asarray([-tangent0[1], tangent0[0]], np.float32)
        origin = np.asarray(((42, 70), (25, 245), (185, -15), (470, 35), (95, 505))[region], np.float32)
        for lane in range(-3, 4):
            previous_back = None
            for step in range(42):
                u = step / 41.0
                bend = 34.0 * np.sin(u * _TAU * (0.62 + region * 0.08) + region * 0.73)
                centre = origin + tangent0 * (u * 610.0) + normal0 * (lane * 9.0 + bend)
                if not (-12 <= centre[0] < _WORK + 12 and -12 <= centre[1] < _WORK + 12):
                    continue
                local_angle = heading + 0.24 * np.cos(u * _TAU * (0.62 + region * 0.08) + region * 0.73)
                tangent = np.asarray([np.cos(local_angle), np.sin(local_angle)], np.float32)
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                half_length = 4.0 + ((step + 2 * region + lane) % 4)
                half_width = 2.5 + ((2 * step + region - lane) % 3)
                shear = ((step + lane + region) % 5 - 2) * 0.65
                polygon = [centre - tangent * half_length - normal * half_width,
                           centre + tangent * (half_length + shear) - normal * half_width,
                           centre + tangent * half_length + normal * half_width,
                           centre - tangent * (half_length - shear) + normal * half_width]
                _draw_poly(masks["polygon_scutes"], polygon, 1.0, 1, True)
                _draw_poly(masks["deep_grooves"], polygon, 1.0, 1, False)
                inset = [centre + (p - centre) * 0.62 for p in polygon]
                _draw_poly(masks["growth_annuli"], inset, 1.0, 1, False)
                _draw_line(masks["raised_keels"], centre - tangent * (half_length - 1),
                           centre + tangent * (half_length - 1), 1.0, 2)
                pit = centre + tangent * 1.5 - normal * 1.2
                cv2.circle(masks["sensory_pits"], tuple(np.rint(pit).astype(int)),
                           1, 1.0, -1, cv2.LINE_AA)
                back = centre - tangent * half_length
                if previous_back is not None:
                    _draw_line(masks["seam_canals"], previous_back, back, 1.0, 1)
                previous_back = centre + tangent * half_length
                if (step + lane + region) % 7 == 0:
                    for tooth in (-2.0, 0.0, 2.0):
                        p = centre + tangent * tooth + normal * half_width
                        _draw_line(masks["interlocking_teeth"], p, p + normal * 2.0, 1.0, 1)
                if (3 * step + lane - region) % 19 == 0:
                    _draw_line(masks["healed_scar_slashes"], centre - normal * 4.0,
                               centre + tangent * 3.0 + normal * 4.0, 1.0, 1)
    banks = dict(polygon_scutes="A", raised_keels="B", growth_annuli="A",
                 sensory_pits="B", seam_canals="N", interlocking_teeth="B",
                 healed_scar_slashes="N", deep_grooves="A")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.sin((x + 0.7 * y) / 61.0)
                                     + np.cos((x - 1.4 * y) / 97.0)))


def _build_fc_hide_scale_glass() -> _Grammar:
    """Lenticular scale streams split and collide around body contours."""
    names = ("lens_bodies", "rim_bevels", "focal_caustics", "stress_veins",
             "micropore_pairs", "scuff_arcs", "occlusion_shadows", "overlap_lips")
    masks = _new_marks(*names)
    obstacles = ((144.0, 128.0, 1.45), (372.0, 162.0, -1.22),
                 (250.0, 342.0, 1.61), (430.0, 430.0, -1.08))
    # SPB-WILDS WR-5: scale position is inherited from deterministic stream
    # integration, never a row/stagger/grid and never random texture.
    seeds = []
    for index in range(58):
        if index % 3 == 0:
            seeds.append(np.asarray([-8.0, 6.0 + _halton(index + 1, 2) * 500.0], np.float32))
        elif index % 3 == 1:
            seeds.append(np.asarray([6.0 + _halton(index + 1, 3) * 500.0, -8.0], np.float32))
        else:
            seeds.append(np.asarray([520.0, 6.0 + _halton(index + 1, 5) * 500.0], np.float32))
    scale_index = 0
    for seed_index, seed in enumerate(seeds):
        point = seed.copy()
        previous = None
        for step in range(210):
            velocity = np.asarray([1.0 if seed_index % 3 != 2 else -1.0,
                                   0.36 * np.sin(point[0] / 71.0 + seed_index * 0.41)], np.float32)
            if seed_index % 3 == 1:
                velocity += np.asarray([0.18, 0.82], np.float32)
            for cx, cy, spin in obstacles:
                delta = point - np.asarray([cx, cy], np.float32)
                d2 = float(np.dot(delta, delta) + 280.0)
                velocity += spin * 660.0 / d2 * np.asarray([-delta[1], delta[0]], np.float32)
                velocity += 520.0 / d2 * delta / max(1.0, float(np.sqrt(d2)))
            velocity /= max(0.2, float(np.linalg.norm(velocity)))
            point = point + velocity * 3.8
            if not (-10 <= point[0] < _WORK + 10 and -10 <= point[1] < _WORK + 10):
                if step > 5:
                    break
                continue
            if previous is not None:
                _draw_line(masks["stress_veins"], previous, point, 0.55, 1)
            previous = point.copy()
            if step % (3 + seed_index % 3) != 0:
                continue
            tangent = velocity
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            half_length = 4.0 + scale_index % 4
            half_width = 2.1 + (scale_index * 2) % 3
            centre = point.copy()
            polygon = [centre - tangent * half_length,
                       centre - normal * half_width,
                       centre + tangent * half_length,
                       centre + normal * half_width]
            _draw_poly(masks["lens_bodies"], polygon, 0.86, 1, True)
            _draw_poly(masks["rim_bevels"], polygon, 1.0, 1, False)
            _draw_line(masks["focal_caustics"], centre - tangent * (half_length - 1) - normal,
                       centre + tangent * (half_length - 1) - normal, 1.0, 1)
            _draw_line(masks["overlap_lips"], polygon[2], polygon[3], 1.0, 1)
            cv2.circle(masks["micropore_pairs"], tuple(np.rint(centre - tangent * 2).astype(int)),
                       1, 1.0, -1, cv2.LINE_AA)
            cv2.circle(masks["micropore_pairs"], tuple(np.rint(centre + tangent * 2).astype(int)),
                       1, 1.0, -1, cv2.LINE_AA)
            _draw_line(masks["occlusion_shadows"], centre + normal * half_width,
                       centre + normal * half_width - tangent * 3.0, 1.0, 2)
            if scale_index % 13 == 0:
                cv2.ellipse(masks["scuff_arcs"], tuple(np.rint(centre).astype(int)),
                            (int(half_length), int(half_width + 1)),
                            float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                            195, 338, 1.0, 1, cv2.LINE_AA)
            scale_index += 1
    banks = dict(lens_bodies="A", rim_bevels="B", focal_caustics="B",
                 stress_veins="N", micropore_pairs="A", scuff_arcs="A",
                 occlusion_shadows="N", overlap_lips="B")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.sin(x / 49.0) + np.cos(y / 67.0)
                                     + np.sin((x + y) / 113.0)))


def _build_fc_dragon_hex_glass() -> _Grammar:
    """Seven noncongruent glass shards own local triangulation and fold polarity."""
    names = ("kagome_straps", "mountain_folds", "valley_folds", "hex_voids",
             "node_bosses", "triangular_faces", "refracted_faces",
             "scale_edge_teeth", "chipped_runes")
    masks = _new_marks(*names)
    # SPB-WILDS WR-5: a uniform infinite Kagome lattice was still wallpaper.
    # These localized origami domains have unrelated boundaries, axes and
    # triangulations; the empty negative space is part of the design.
    domains = ((np.asarray([82.0, 92.0]), 58.0, 7, 0.13),
               (np.asarray([250.0, 72.0]), 74.0, 9, 1.04),
               (np.asarray([431.0, 138.0]), 66.0, 8, 2.12),
               (np.asarray([146.0, 279.0]), 91.0, 10, -0.42),
               (np.asarray([363.0, 292.0]), 78.0, 7, 0.67),
               (np.asarray([77.0, 447.0]), 61.0, 8, 2.69),
               (np.asarray([334.0, 438.0]), 88.0, 11, -1.23))
    for domain_index, (centre, radius, sides, phase) in enumerate(domains):
        boundary = []
        inner = []
        for vertex in range(sides):
            angle = phase + vertex * _TAU / sides
            reach = radius * (0.76 + 0.20 * ((vertex * 3 + domain_index) % 5) / 4.0)
            point = centre + np.asarray([np.cos(angle), np.sin(angle)]) * reach
            boundary.append(point)
            inner.append(centre + (point - centre) * (0.42 + 0.05 * ((vertex + domain_index) % 3)))
            cv2.circle(masks["node_bosses"], tuple(np.rint(point).astype(int)),
                       2 + vertex % 2, 1.0, -1, cv2.LINE_AA)
        for vertex in range(sides):
            nxt = (vertex + 1) % sides
            tri = [centre, boundary[vertex], boundary[nxt]]
            face_name = "refracted_faces" if (vertex + domain_index) & 1 else "triangular_faces"
            _draw_poly(masks[face_name], tri,
                       0.58 + 0.07 * ((vertex + domain_index) % 4), 1, True)
            target = inner[(vertex + 2 + domain_index) % sides]
            if (vertex + domain_index) & 1:
                _draw_line(masks["mountain_folds"], boundary[vertex], target, 1.0, 2)
            else:
                _draw_line(masks["valley_folds"], boundary[vertex], target, 1.0, 2)
            _draw_line(masks["kagome_straps"], inner[vertex], inner[nxt], 1.0, 2)
            aperture = centre * 0.38 + (boundary[vertex] + boundary[nxt]) * 0.31
            cv2.circle(masks["hex_voids"], tuple(np.rint(aperture).astype(int)),
                       3 + (vertex + domain_index) % 3, 1.0, 1, cv2.LINE_AA)
            edge_mid = (boundary[vertex] + boundary[nxt]) * 0.5
            tangent = boundary[nxt] - boundary[vertex]
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            for tooth in (-5.0, 0.0, 5.0):
                p = edge_mid + tangent * tooth
                _draw_line(masks["scale_edge_teeth"], p, p + normal * 3.0, 1.0, 1)
            if (vertex + 2 * domain_index) % 4 == 0:
                rune = inner[vertex]
                _draw_line(masks["chipped_runes"], rune - (3, 3), rune + (3, 3), 1.0, 1)
                _draw_line(masks["chipped_runes"], rune - (3, -3), rune + (3, -3), 1.0, 1)
    banks = dict(kagome_straps="A", mountain_folds="A", valley_folds="B",
                 hex_voids="N", node_bosses="B", triangular_faces="A",
                 refracted_faces="B", scale_edge_teeth="B", chipped_runes="N")
    x, y = _xy()
    return _pack(masks, banks, _norm(np.hypot(x - 252.0, y - 261.0)
                                     + 37.0 * np.sin(np.arctan2(y - 261.0, x - 252.0) * 7.0)))


def _build_fc_crackle_eyeshine_glass() -> _Grammar:
    """Newton-basin tapetum; basin ancestry drives every optical component."""
    lx, ly, ix, iy = _local(38.0, 38.0, True)
    phase = ((ix + 2 * iy) % 6).astype(np.float32) * (np.pi / 9.0)
    z = (lx / 9.0 + 1j * ly / 9.0) * np.exp(1j * phase)
    iterations = np.zeros((_WORK, _WORK), np.float32)
    for step in range(9):
        denom = 3.0 * z * z
        denom = np.where(np.abs(denom) < 1.0e-5, 1.0e-5 + 0j, denom)
        z = z - (z * z * z - 1.0) / denom
        iterations += (np.abs(z * z * z - 1.0) > 0.015).astype(np.float32)
    roots = np.asarray([1.0 + 0j, np.exp(2j * np.pi / 3), np.exp(4j * np.pi / 3)])
    dist = np.stack([np.abs(z - root) for root in roots], axis=0)
    label = np.argmin(dist, axis=0).astype(np.uint8)
    boundaries = _f32(_edge(label.astype(np.float32) / 2.0, 1))
    pupil_axis = np.where(label == 0, lx,
                          np.where(label == 1, 0.5 * lx + 0.866 * ly,
                                   -0.5 * lx + 0.866 * ly))
    pupils = _line(pupil_axis, 0.72) * (np.hypot(lx, ly) < 10.0)
    iris = _line(np.sin(np.hypot(lx, ly) * 1.4 + label * 1.7), 0.16) * (np.hypot(lx, ly) < 11.0)
    cat_caustic = _line(ly - 0.065 * lx * lx + 2.5, 0.62) * (np.hypot(lx, ly) < 12.0)
    bevel = cv2.dilate(boundaries, np.ones((5, 5), np.uint8)) - boundaries
    relay = _line(lx + 0.42 * ly, 0.58) * boundaries
    glint = _inside(np.maximum(np.abs(lx + 4.0), np.abs(ly + 4.0)), 1.15, 0.45)
    backing = _f32((pupil_axis - 2.0) / 3.0) * (np.hypot(lx, ly) < 10.0)
    masks = dict(newton_basin_faces=_f32(1.0 - boundaries), oriented_pupils=pupils,
                 iris_bands=iris, cat_eye_caustics=cat_caustic, bevel_rims=bevel,
                 relay_cracks=relay, square_glints=glint, dark_backing_wedges=backing)
    banks = dict(newton_basin_faces="A", oriented_pupils="N", iris_bands="A",
                 cat_eye_caustics="B", bevel_rims="B", relay_cracks="N",
                 square_glints="B", dark_backing_wedges="A")
    return _pack(masks, banks, _norm(iterations / 9.0 + label * 0.21))


# ---------------------------------------------------------------------------
# WR-11 owner-eye replacements.  The first mechanical-green candidate still
# contained four unmistakable lazy silhouettes: one macro quill fan, lens
# beads on sparse paths, repeated frog-hand stamps, and a tiled Newton-eye
# square.  These replacements share no placement generator.  Each establishes
# a different global causal system before any fine 2-8 work-pixel material
# children are drawn.


def _build_fc_quill_bristle_w12() -> _Grammar:
    """A warped defensive mantle erupts along unequal full-canvas skin folds."""
    names = ("root_bulbs", "collar_rings", "rigid_shafts", "hollow_slits",
             "alternating_barbs", "tapered_tips", "lee_shadows",
             "strain_crosscuts")
    masks = _new_marks(*names)

    # SPB-WILDS WR-11, owner verdict "LAZY": the previous twenty-one nested
    # arcs were one giant fan.  Thirty-one independent skin folds now advect
    # through a non-radial strain field.  Short quills are physical children
    # of those folds; no fold shares a hub or a translated curve template.
    fold_index = 0
    quill_index = 0
    for entry in range(31):
        point = np.asarray([-10.0,
                            9.0 + entry * 16.35
                            + 8.0 * np.sin(entry * 1.37)], np.float32)
        previous = None
        for step in range(178):
            px, py = float(point[0]), float(point[1])
            vx = 1.0 + 0.11 * np.sin(py / 39.0 + entry * 0.23)
            vy = (0.44 * np.sin(px / (47.0 + entry % 5 * 3.0) + entry * 0.61)
                  + 0.27 * np.cos((px + py) / 71.0 - entry * 0.29)
                  + 0.0015 * (px - 256.0) * np.sin(entry * 0.73))
            tangent = np.asarray([vx, vy], np.float32)
            tangent /= max(0.2, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            next_point = point + tangent * (3.25 + 0.18 * (entry % 4))
            if previous is not None:
                _draw_line(masks["lee_shadows"], previous, point, 0.70,
                           2 if entry % 7 == 0 else 1)
            if step % (2 + entry % 2) == 0 and 1.0 <= px < 511.0 and 1.0 <= py < 511.0:
                for side in (-1.0, 1.0):
                    root = point + normal * side * (2.0 + (quill_index % 4))
                    lean = normal * side + tangent * (0.22 + 0.07 * (entry % 3))
                    lean /= max(0.2, float(np.linalg.norm(lean)))
                    length = 3.5 + (quill_index * 5 + entry) % 6
                    tip = root + lean * length
                    cv2.circle(masks["root_bulbs"], tuple(np.rint(root).astype(int)),
                               1 + quill_index % 2, 1.0, -1, cv2.LINE_AA)
                    cv2.circle(masks["collar_rings"], tuple(np.rint(root).astype(int)),
                               2 + quill_index % 2, 1.0, 1, cv2.LINE_AA)
                    _draw_line(masks["rigid_shafts"], root, tip, 1.0, 1)
                    slit_a = root + lean * (1.4 + quill_index % 2)
                    slit_b = tip - lean * 1.2
                    _draw_line(masks["hollow_slits"], slit_a, slit_b, 1.0, 1)
                    barb_normal = np.asarray([-lean[1], lean[0]], np.float32)
                    for fraction in (0.42, 0.68):
                        barb_root = root + lean * length * fraction
                        barb_side = -1.0 if (quill_index + int(fraction * 10)) & 1 else 1.0
                        _draw_line(masks["alternating_barbs"], barb_root,
                                   barb_root - lean * 1.5 + barb_normal * barb_side * 2.1,
                                   1.0, 1)
                    _draw_line(masks["tapered_tips"], tip - barb_normal * 1.5,
                               tip + barb_normal * 1.5 - lean, 1.0, 1)
                    if quill_index % 9 == 0:
                        _draw_line(masks["strain_crosscuts"], root - tangent * 3.0,
                                   root + tangent * 3.0, 1.0, 1)
                    quill_index += 1
            previous = point.copy()
            point = next_point
            if point[0] > 522.0:
                break
        fold_index += 1
    banks = dict(root_bulbs="B", collar_rings="A", rigid_shafts="A",
                 hollow_slits="N", alternating_barbs="B", tapered_tips="B",
                 lee_shadows="A", strain_crosscuts="N")
    x, y = _xy()
    tone = _norm(y / 61.0 + 0.41 * np.sin(x / 47.0)
                 + 0.23 * np.cos((x + y) / 73.0))
    return _pack(masks, banks, tone)


def _build_fc_eyeshine_w12() -> _Grammar:
    """Unequal cropped tapetal basins fracture one continuous nocturnal eye field."""
    names = ("tapetal_basin_a", "tapetal_basin_b", "basin_faults",
             "curved_pupil_slits", "iris_isophotes", "caustic_cusps",
             "lid_shadows", "fracture_relays", "square_glints")
    masks = _new_marks(*names)
    x, y = _xy()
    centres = ((-52.0, 72.0, 1.20, 0.63, 0.18),
               (158.0, -46.0, 0.74, 1.28, -0.51),
               (374.0, 48.0, 1.31, 0.72, 0.77),
               (558.0, 176.0, 0.82, 1.18, -0.94),
               (72.0, 286.0, 1.05, 0.86, 1.17),
               (274.0, 236.0, 0.71, 1.34, -0.16),
               (462.0, 354.0, 1.27, 0.69, 0.43),
               (138.0, 532.0, 0.88, 1.17, -0.73),
               (356.0, 548.0, 1.18, 0.79, 0.96))
    distances = []
    locals_xy = []
    for index, (cx, cy, sx, sy, angle) in enumerate(centres):
        ca, sa = np.cos(angle), np.sin(angle)
        dx, dy = x - cx, y - cy
        u = (ca * dx + sa * dy) / (sx * (106.0 + 7.0 * (index % 3)))
        v = (-sa * dx + ca * dy) / (sy * (96.0 + 9.0 * ((index + 1) % 4)))
        warp = (0.14 * np.sin((dx + 0.7 * dy) / (45.0 + 3.0 * index))
                + 0.08 * np.cos((dy - 0.4 * dx) / (61.0 + 2.0 * index)))
        distances.append(u * u + v * v + warp + index * 0.006)
        locals_xy.append((u, v))
    distance_stack = np.stack(distances, axis=0)
    label = np.argmin(distance_stack, axis=0).astype(np.uint8)
    best = np.take_along_axis(distance_stack, label[None, ...], axis=0)[0]
    second = np.partition(distance_stack, 1, axis=0)[1]
    confidence = _norm(second - best)
    masks["tapetal_basin_a"] = _f32(((label % 2) == 0).astype(np.float32)
                                     * (0.70 + 0.30 * confidence))
    masks["tapetal_basin_b"] = _f32(((label % 2) == 1).astype(np.float32)
                                     * (0.70 + 0.30 * confidence))
    masks["basin_faults"] = _edge(label.astype(np.float32) / max(1, len(centres) - 1), 1)
    for index, (u, v) in enumerate(locals_xy):
        region = (label == index).astype(np.float32)
        rho = np.hypot(u, v)
        pupil_curve = v - (0.055 + 0.008 * index) * u * u + 0.08 * np.sin(u * (3.1 + index * 0.13))
        masks["curved_pupil_slits"] = np.maximum(
            masks["curved_pupil_slits"], _line(pupil_curve, 0.014) * region)
        iris_phase = np.mod(rho * (7.2 + 0.31 * index) + index * 0.19, 1.0)
        iris = _f32(1.0 - np.abs(iris_phase - 0.5) / 0.12) * region
        masks["iris_isophotes"] = np.maximum(masks["iris_isophotes"], iris)
        cusp = _line(v * v - (0.19 + 0.015 * index) * (u + 0.54), 0.018) * region
        masks["caustic_cusps"] = np.maximum(masks["caustic_cusps"], cusp)
        lid = _line(v + 0.43 + 0.11 * np.sin(u * 2.4 + index), 0.021) * region
        masks["lid_shadows"] = np.maximum(masks["lid_shadows"], lid)
        relay = _line(u - v * (0.38 + 0.04 * (index % 3))
                      - 0.31 * np.sin(v * 4.0 + index), 0.015) * region
        masks["fracture_relays"] = np.maximum(masks["fracture_relays"], relay)
        # One glint location per unequal basin, frequently cropped by the
        # basin fault.  It is not a repeated lens chain.
        gx = -0.31 + 0.06 * (index % 4)
        gy = -0.27 + 0.05 * ((2 * index) % 5)
        glint = _inside(np.maximum(np.abs(u - gx), np.abs(v - gy)),
                        0.022 + 0.004 * (index % 3), 0.008) * region
        masks["square_glints"] = np.maximum(masks["square_glints"], glint)
    banks = dict(tapetal_basin_a="A", tapetal_basin_b="B", basin_faults="N",
                 curved_pupil_slits="N", iris_isophotes="A",
                 caustic_cusps="B", lid_shadows="B", fracture_relays="N",
                 square_glints="B")
    tone = _norm(confidence + label.astype(np.float32) * 0.17
                 + 0.11 * np.sin((x - y) / 79.0))
    return _pack(masks, banks, tone)


def _build_fc_webbed_membrane_w12() -> _Grammar:
    """Edge-fed arteries grow one continuous amphibian tension membrane."""
    names = ("arterial_trunks", "branching_veins", "membrane_tissue",
             "stretch_striae", "junction_pads", "capillary_loops",
             "tear_notches", "dew_beads", "venous_shadows")
    masks = _new_marks(*names)
    trunks = ((np.asarray([-24.0, 38.0]), np.asarray([96.0, 18.0]), np.asarray([302.0, 212.0]), np.asarray([538.0, 84.0])),
              (np.asarray([-22.0, 138.0]), np.asarray([144.0, 296.0]), np.asarray([328.0, 30.0]), np.asarray([540.0, 178.0])),
              (np.asarray([-28.0, 286.0]), np.asarray([152.0, 172.0]), np.asarray([352.0, 432.0]), np.asarray([542.0, 304.0])),
              (np.asarray([-24.0, 462.0]), np.asarray([118.0, 554.0]), np.asarray([382.0, 306.0]), np.asarray([540.0, 446.0])),
              (np.asarray([72.0, -24.0]), np.asarray([18.0, 142.0]), np.asarray([278.0, 284.0]), np.asarray([198.0, 540.0])),
              (np.asarray([316.0, -24.0]), np.asarray([510.0, 118.0]), np.asarray([198.0, 336.0]), np.asarray([402.0, 540.0])),
              (np.asarray([538.0, 42.0]), np.asarray([394.0, 136.0]), np.asarray([128.0, 352.0]), np.asarray([-24.0, 392.0])),
              (np.asarray([112.0, -26.0]), np.asarray([246.0, 92.0]), np.asarray([-8.0, 348.0]), np.asarray([126.0, 540.0])),
              (np.asarray([492.0, -28.0]), np.asarray([334.0, 154.0]), np.asarray([554.0, 326.0]), np.asarray([462.0, 540.0])),
              (np.asarray([-26.0, 218.0]), np.asarray([196.0, 18.0]), np.asarray([304.0, 498.0]), np.asarray([540.0, 246.0])),
              (np.asarray([22.0, 540.0]), np.asarray([44.0, 298.0]), np.asarray([430.0, 166.0]), np.asarray([538.0, 18.0])),
              (np.asarray([540.0, 516.0]), np.asarray([308.0, 562.0]), np.asarray([206.0, 54.0]), np.asarray([-24.0, 18.0])))
    branch_counter = 0
    for trunk_index, (p0, p1, p2, p3) in enumerate(trunks):
        points = []
        tangents = []
        previous = None
        for sample in range(161):
            u = sample / 160.0
            point = ((1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u*u*p2 + u**3*p3)
            tangent = (3*(1-u)**2*(p1-p0) + 6*(1-u)*u*(p2-p1) + 3*u*u*(p3-p2))
            tangent /= max(1.0, float(np.linalg.norm(tangent)))
            points.append(point); tangents.append(tangent)
            if previous is not None:
                _draw_line(masks["arterial_trunks"], previous, point, 1.0,
                           3 if trunk_index % 3 == 0 else 2)
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                _draw_line(masks["venous_shadows"], previous + normal * 2.3,
                           point + normal * 2.3, 0.82, 1)
            previous = point
        for anchor_index in range(8 + trunk_index % 4, 154, 9 + trunk_index % 5):
            anchor = points[anchor_index]
            tangent = tangents[anchor_index]
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            side = -1.0 if (anchor_index + trunk_index) & 1 else 1.0
            reach = 20.0 + (branch_counter * 7 + trunk_index) % 24
            elbow = anchor + normal * side * reach * 0.54 + tangent * (3.0 * np.sin(branch_counter))
            tip = anchor + normal * side * reach + tangent * (7.0 * np.cos(branch_counter * 0.71))
            _draw_line(masks["branching_veins"], anchor, elbow, 1.0, 1)
            _draw_line(masks["branching_veins"], elbow, tip, 1.0, 1)
            cv2.circle(masks["junction_pads"], tuple(np.rint(anchor).astype(int)),
                       2 + branch_counter % 2, 1.0, -1, cv2.LINE_AA)
            for fork_side in (-1.0, 1.0):
                fork_tip = tip + normal * side * (5.0 + branch_counter % 5)
                fork_tip += tangent * fork_side * (5.0 + (branch_counter * 3) % 7)
                _draw_line(masks["branching_veins"], elbow, fork_tip, 0.92, 1)
                loop_mid = (tip + fork_tip) * 0.5
                cv2.ellipse(masks["capillary_loops"], tuple(np.rint(loop_mid).astype(int)),
                            (3 + branch_counter % 3, 2 + (branch_counter + 1) % 2),
                            float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                            0, 360, 1.0, 1, cv2.LINE_AA)
            _draw_line(masks["stretch_striae"], anchor - tangent * 4.0,
                       anchor + tangent * 4.0, 1.0, 1)
            if branch_counter % 5 == 0:
                _draw_line(masks["tear_notches"], tip - tangent * 3.0,
                           tip + normal * side * 4.0, 1.0, 1)
            if branch_counter % 4 == 0:
                cv2.circle(masks["dew_beads"], tuple(np.rint(tip).astype(int)),
                           1 + branch_counter % 2, 1.0, 1, cv2.LINE_AA)
            branch_counter += 1
    vessel = np.maximum(masks["arterial_trunks"], masks["branching_veins"])
    # Tissue is the causal close-range envelope of the vascular tree.  The
    # 2-8 work-pixel width respects the 8-32 native-pixel feature doctrine.
    near = cv2.GaussianBlur(vessel, (0, 0), 3.2)
    wide = cv2.GaussianBlur(vessel, (0, 0), 7.2)
    masks["membrane_tissue"] = _f32(near * 2.4 + wide * 0.72)
    banks = dict(arterial_trunks="A", branching_veins="B", membrane_tissue="B",
                 stretch_striae="N", junction_pads="A", capillary_loops="B",
                 tear_notches="N", dew_beads="B", venous_shadows="A")
    x, y = _xy()
    tone = _norm(cv2.distanceTransform((vessel < 0.08).astype(np.uint8),
                                       cv2.DIST_L2, 3)
                 + 0.09 * x - 0.06 * y)
    return _pack(masks, banks, tone)


def _build_fc_toad_skin_w12() -> _Grammar:
    """A deterministic reaction front grows one contiguous glandular dermis."""
    names = ("gland_domes", "poison_pores", "saddle_wrinkles",
             "capillary_forks", "dry_crack_collars", "mucus_rivulets",
             "paired_micro_pits", "annular_lips")
    x, y = _xy()
    u = np.ones((_WORK, _WORK), np.float32)
    v = np.zeros_like(u)
    seed = np.zeros_like(u)

    # SPB-WILDS WR-11, owner verdict "LAZY": eight paisley colonies were
    # repeated closed icons.  Authored chemical fronts below only initialize
    # one global Gray-Scott dermis; no random/noise field enters the solve.
    seed_curves = (((-20, 64), (124, 18), (238, 188), (536, 96)),
                   ((-18, 208), (152, 338), (344, 46), (538, 246)),
                   ((-22, 424), (126, 548), (356, 266), (538, 456)),
                   ((64, -18), (4, 164), (294, 286), (176, 536)),
                   ((326, -22), (526, 122), (172, 374), (426, 536)))
    for curve_index, control in enumerate(seed_curves):
        p0, p1, p2, p3 = [np.asarray(point, np.float32) for point in control]
        previous = None
        for sample in range(121):
            t = sample / 120.0
            point = ((1-t)**3*p0 + 3*(1-t)**2*t*p1
                     + 3*(1-t)*t*t*p2 + t**3*p3)
            if previous is not None:
                _draw_line(seed, previous, point, 0.76,
                           3 + (curve_index + sample // 19) % 4)
            previous = point
    for index, (cx, cy, rx, ry, angle) in enumerate(
            ((72, 104, 24, 11, 17), (208, 68, 18, 29, -33),
             (414, 128, 31, 14, 61), (118, 286, 27, 18, -52),
             (304, 244, 17, 34, 28), (468, 316, 29, 13, -18),
             (64, 452, 21, 32, 73), (266, 438, 35, 16, -41),
             (446, 482, 23, 27, 12))):
        cv2.ellipse(seed, (cx, cy), (rx, ry), angle, 0, 360,
                    0.64 + 0.04 * (index % 4), -1, cv2.LINE_AA)
    # A continuous, deterministic concentration field starts chemistry in the
    # spaces between the authored fronts as well.  This is part of the Turing
    # solve—not a rendered grain/noise layer—and is never composited directly.
    interference = np.tanh(
        1.35 * (np.sin(x / 18.7 + 0.34 * np.sin(y / 41.0))
                + np.cos(y / 23.9 - 0.29 * np.sin(x / 53.0))
                + 0.48 * np.sin((x + 1.37 * y) / 31.0)))
    concentration = 0.035 + 0.055 * (interference + 1.0) * 0.5
    v[:] = np.clip(concentration + seed * 0.72, 0.0, 0.96)
    u[:] = np.clip(1.0 - v * 0.58, 0.0, 1.0)
    kernel = np.asarray([[0.05, 0.20, 0.05],
                         [0.20, -1.0, 0.20],
                         [0.05, 0.20, 0.05]], np.float32)
    feed = 0.0315 + 0.0075 * (x / 511.0) + 0.0025 * np.sin(y / 83.0)
    kill = 0.0590 + 0.0042 * (y / 511.0) + 0.0018 * np.cos((x + y) / 97.0)
    for _step in range(260):
        lap_u = cv2.filter2D(u, -1, kernel, borderType=cv2.BORDER_REFLECT)
        lap_v = cv2.filter2D(v, -1, kernel, borderType=cv2.BORDER_REFLECT)
        reaction = u * v * v
        u += 0.18 * lap_u - reaction + feed * (1.0 - u)
        v += 0.09 * lap_v + reaction - (feed + kill) * v
        np.clip(u, 0.0, 1.0, out=u)
        np.clip(v, 0.0, 1.0, out=v)
    chemistry = _norm(v)
    dome = _f32((chemistry - 0.13) / 0.42)
    high = _f32((chemistry - 0.46) / 0.22)
    local_max = _f32((chemistry >= cv2.dilate(chemistry, np.ones((5, 5), np.uint8))).astype(np.float32)
                     * high)
    poison = cv2.dilate(local_max, np.ones((3, 3), np.uint8))
    wrinkle = np.maximum(_line(chemistry - 0.30, 0.025),
                         _line(chemistry - 0.56, 0.022))
    collars = _edge(_f32((chemistry > 0.50).astype(np.float32)), 1)
    lips = _edge(_f32((chemistry > 0.27).astype(np.float32)), 1)
    mucus = (_line(chemistry - (0.18 + 0.025 * np.sin((x - y) / 53.0)), 0.018)
             * _f32((chemistry - 0.08) / 0.18))
    gradient_x = cv2.Sobel(chemistry, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(chemistry, cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gradient_x, gradient_y))
    capillaries = _f32(gradient * (1.0 - high) * 1.65)
    paired = np.maximum(np.roll(poison, 2, axis=0), np.roll(poison, -2, axis=1))
    masks = dict(gland_domes=dome, poison_pores=poison,
                 saddle_wrinkles=wrinkle, capillary_forks=capillaries,
                 dry_crack_collars=collars, mucus_rivulets=mucus,
                 paired_micro_pits=paired, annular_lips=lips)
    banks = dict(gland_domes="A", poison_pores="N", saddle_wrinkles="B",
                 capillary_forks="A", dry_crack_collars="N",
                 mucus_rivulets="B", paired_micro_pits="A",
                 annular_lips="B")
    return _pack(masks, banks, _norm(chemistry + 0.29 * u + 0.08 * x / 511.0))


def _build_fc_mossy_stone_w12() -> _Grammar:
    """Curved contraction faults partition a continuous lichen-fed basalt skin."""
    names = ("basalt_crowns", "contraction_seams", "beveled_edges",
             "foliose_lichen", "soredia_cups", "moisture_channels",
             "quartz_needles", "chipped_corners")
    masks = _new_marks(*names)

    # SPB-WILDS WR-11: thirteen repeated radial stars are gone.  Thirty-six
    # faults enter from unrelated edges and propagate through one anisotropic
    # contraction field.  Lichen and quartz are children of wet seams and
    # high-curvature corners, never independent flecks.
    fault_counter = 0
    lichen_counter = 0
    for fault in range(36):
        edge = fault % 4
        along = 8.0 + ((fault * fault * 37 + fault * 19) % 497)
        if edge == 0:
            point = np.asarray([-8.0, along], np.float32); angle = -0.16 + 0.023 * fault
        elif edge == 1:
            point = np.asarray([along, -8.0], np.float32); angle = 1.31 + 0.019 * fault
        elif edge == 2:
            point = np.asarray([520.0, along], np.float32); angle = np.pi - 0.24 - 0.017 * fault
        else:
            point = np.asarray([along, 520.0], np.float32); angle = -1.42 + 0.021 * fault
        previous = None
        for step in range(190):
            px, py = float(point[0]), float(point[1])
            angle += (0.021 * np.sin(px / 43.0 + fault * 0.73)
                      - 0.017 * np.cos(py / 57.0 - fault * 0.41)
                      + 0.011 * np.sin((px - py) / 79.0))
            tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            next_point = point + tangent * (3.1 + 0.16 * (fault % 5))
            if previous is not None:
                _draw_line(masks["contraction_seams"], previous, point, 1.0,
                           2 if fault % 11 == 0 else 1)
                _draw_line(masks["beveled_edges"], previous + normal * 1.8,
                           point + normal * 1.8, 0.92, 1)
                if fault % 3 == 0 or (fault + step) % 13 == 0:
                    _draw_line(masks["moisture_channels"], previous - normal * 1.6,
                               point - normal * 1.6, 1.0, 2)
            if step % (3 + fault % 3) == 0 and 1.0 <= px < 511.0 and 1.0 <= py < 511.0:
                if fault % 3 == 0:
                    centre = point - normal * (3.0 + lichen_counter % 4)
                    reach = 2.5 + lichen_counter % 4
                    polygon = [centre - tangent * reach,
                               centre + tangent * (reach + 1.0) - normal * 1.8,
                               centre + tangent * (reach + 2.0) + normal * 1.2,
                               centre - tangent * 0.7 + normal * (2.4 + lichen_counter % 2)]
                    _draw_poly(masks["foliose_lichen"], polygon, 0.86, 1, True)
                    cv2.circle(masks["soredia_cups"], tuple(np.rint(centre).astype(int)),
                               1 + lichen_counter % 2, 1.0, 1, cv2.LINE_AA)
                    lichen_counter += 1
                if (fault + step) % 9 == 0:
                    base = point + normal * 2.0
                    _draw_line(masks["quartz_needles"], base,
                               base + normal * (4.0 + fault % 5) + tangent * 2.0,
                               1.0, 1)
                    _draw_line(masks["quartz_needles"], base,
                               base + normal * (3.0 + step % 4) - tangent * 2.0,
                               1.0, 1)
                if (fault + 2 * step) % 17 == 0:
                    chip = point + normal * (2.0 if fault & 1 else -2.0)
                    _draw_poly(masks["chipped_corners"],
                               [chip, chip + tangent * 3.0 + normal * 2.0,
                                chip + tangent * 5.0 - normal], 1.0, 1, False)
            previous = point.copy()
            point = next_point
            if not (-12.0 <= point[0] <= 524.0 and -12.0 <= point[1] <= 524.0):
                break
        fault_counter += 1
    seam_binary = (masks["contraction_seams"] < 0.08).astype(np.uint8)
    distance = cv2.distanceTransform(seam_binary, cv2.DIST_L2, 3)
    # Plate crowns fill the stone between seams but preserve fine distance
    # relief; no texture field or histogram balancing is introduced.
    crown = _f32(0.38 + 0.62 * _norm(np.minimum(distance, 13.0)))
    masks["basalt_crowns"] = crown
    banks = dict(basalt_crowns="A", contraction_seams="N", beveled_edges="B",
                 foliose_lichen="B", soredia_cups="A", moisture_channels="B",
                 quartz_needles="A", chipped_corners="N")
    x, y = _xy()
    tone = _norm(distance + 0.17 * x - 0.11 * y
                 + 1.7 * masks["moisture_channels"])
    return _pack(masks, banks, tone)


def _build_fc_dragon_hex_glass_w12() -> _Grammar:
    """One nonperiodic stressed-glass continent fractures into fine fold facets."""
    names = ("mountain_folds", "valley_folds", "plate_faces_a",
             "plate_faces_b", "fold_voids", "node_bosses",
             "refracted_seams", "scale_edge_teeth", "chipped_runes")
    masks = _new_marks(*names)
    facet_tone = np.zeros((_WORK, _WORK), np.float32)

    # SPB-WILDS WR-11: seven radial origami icons were repeated stamps.  The
    # node set below is the literal global fracture structure, not an added
    # random/noise separator.  A low-discrepancy chronology is smoothly
    # displaced by one anisotropic stress field and triangulated once across
    # the whole canvas; there are no domains, hubs, tiles, or repeated shards.
    subdivision = cv2.Subdiv2D((0, 0, _WORK, _WORK))
    for index in range(1, 3001):
        px = _halton(index, 2) * 511.0
        py = _halton(index, 3) * 511.0
        wx = (7.8 * np.sin(py / 43.0 + px / 89.0)
              + 3.4 * np.sin((px - py) / 31.0))
        wy = (6.6 * np.cos(px / 47.0 - py / 97.0)
              + 3.1 * np.sin((px + py) / 37.0))
        point = (float(np.clip(px + wx, 0.25, 511.74)),
                 float(np.clip(py + wy, 0.25, 511.74)))
        try:
            subdivision.insert(point)
        except cv2.error:
            # Exact duplicate coordinates can occur only after float clipping;
            # skipping them does not add entropy or alter any other point.
            continue
    triangles = subdivision.getTriangleList().reshape((-1, 3, 2))
    facet_counter = 0
    for triangle in triangles:
        if np.any(triangle < 0.0) or np.any(triangle >= float(_WORK)):
            continue
        edge_one = triangle[1] - triangle[0]
        edge_two = triangle[2] - triangle[0]
        area = abs(float(edge_one[0] * edge_two[1]
                         - edge_one[1] * edge_two[0])) * 0.5
        # W12's 126-pixel cutoff silently discarded the larger bridging
        # triangles and left repeated dark holes.  All valid local folds now
        # participate in the one connected fault continent.
        if area < 1.0 or area > 520.0:
            continue
        centre = triangle.mean(axis=0)
        edge_three = triangle[2] - triangle[1]
        candidate_edges = (edge_one, edge_two, edge_three)
        long_edge = max(candidate_edges, key=lambda value: float(np.dot(value, value)))
        edge_angle = float(np.arctan2(long_edge[1], long_edge[0]))
        theta_field = (0.37 * np.arctan2(centre[1] - 236.0,
                                         centre[0] - 278.0)
                       + 0.29 * np.sin((centre[0] + centre[1]) / 91.0))
        # Material ownership follows whether the facet's longest fold aligns
        # with the local anisotropic stress tensor.  This removes W12's broad
        # diagonal recolor stripes without adding a random separator.
        stress = (np.cos(2.0 * (edge_angle - theta_field))
                  + 0.23 * np.sin(area * 0.19 + edge_angle * 3.0))
        face_name = "plate_faces_a" if stress >= 0.0 else "plate_faces_b"
        _draw_poly(masks[face_name], triangle, 0.72 + 0.06 * (facet_counter % 4),
                   1, True)
        _draw_poly(facet_tone, triangle,
                   float(np.mod(edge_angle / np.pi + area * 0.013, 1.0)),
                   1, True)
        inner = centre + (triangle - centre) * (0.44 + 0.03 * (facet_counter % 3))
        for edge_index in range(3):
            a = triangle[edge_index]
            b = triangle[(edge_index + 1) % 3]
            vector = b - a
            length = max(0.2, float(np.linalg.norm(vector)))
            tangent = vector / length
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            fold_name = "mountain_folds" if (stress + tangent[0] * tangent[1]) >= 0.0 else "valley_folds"
            _draw_line(masks[fold_name], a, b, 1.0, 1)
            _draw_line(masks["refracted_seams"], inner[edge_index], centre,
                       0.82, 1)
            if facet_counter % 4 == edge_index:
                midpoint = (a + b) * 0.5
                _draw_line(masks["scale_edge_teeth"], midpoint - tangent * 1.5,
                           midpoint + normal * (2.0 + facet_counter % 3),
                           1.0, 1)
        if facet_counter % 17 == 0:
            cv2.circle(masks["fold_voids"], tuple(np.rint(centre).astype(int)),
                       1 + facet_counter % 3, 1.0, 1, cv2.LINE_AA)
        if facet_counter % 11 == 0:
            vertex = triangle[facet_counter % 3]
            cv2.circle(masks["node_bosses"], tuple(np.rint(vertex).astype(int)),
                       1 + (facet_counter // 11) % 2, 1.0, -1, cv2.LINE_AA)
        if facet_counter % 29 == 0:
            _draw_line(masks["chipped_runes"], centre - (2.5, 2.5),
                       centre + (2.5, 2.5), 1.0, 1)
            _draw_line(masks["chipped_runes"], centre - (2.5, -2.5),
                       centre + (2.5, -2.5), 1.0, 1)
        facet_counter += 1
    banks = dict(mountain_folds="A", valley_folds="B", plate_faces_a="A",
                 plate_faces_b="B", fold_voids="N", node_bosses="B",
                 refracted_seams="A", scale_edge_teeth="B", chipped_runes="N")
    tone = _norm(facet_tone + 0.17 * masks["mountain_folds"]
                 - 0.13 * masks["valley_folds"])
    return _pack(masks, banks, tone)


def _build_fc_crackle_eyeshine_glass_w12() -> _Grammar:
    """One global five-attractor Newton tapetum replaces the repeated tile."""
    names = ("basin_faces_a", "basin_faces_b", "tapetal_cracks",
             "oriented_pupils", "iris_bands", "cat_eye_caustics",
             "bevel_rims", "relay_fractures", "square_glints")
    x, y = _xy()
    # SPB-WILDS WR-11, owner verdict "exact same pattern": `_local(38, 38)`
    # made a square Newton-eye wallpaper.  This solve spans the whole canvas;
    # its five unequal attractors include cropped/off-axis domains and never
    # repeat, translate, or tile.
    zx = (x - 256.0) / 153.0
    zy = (y - 248.0) / 149.0
    z = (zx + 0.13 * np.sin(zy * 2.1)
         + 1j * (zy + 0.10 * np.sin(zx * 2.7))).astype(np.complex64)
    seed_z = z.copy()
    roots = np.asarray([-1.31 + 0.24j, -0.27 + 1.18j, 0.96 + 0.78j,
                        1.23 - 0.61j, -0.36 - 1.12j], np.complex64)
    iterations = np.zeros((_WORK, _WORK), np.float32)
    for step in range(13):
        offsets = [z - root for root in roots]
        polynomial = np.ones_like(z)
        for offset in offsets:
            polynomial *= offset
        derivative = np.zeros_like(z)
        for omit in range(len(roots)):
            term = np.ones_like(z)
            for index, offset in enumerate(offsets):
                if index != omit:
                    term *= offset
            derivative += term
        safe = np.where(np.abs(derivative) < 1.0e-5,
                        np.complex64(1.0e-5 + 0j), derivative)
        z = z - polynomial / safe
        residual = np.min(np.stack([np.abs(z - root) for root in roots]), axis=0)
        iterations += (residual > 0.012).astype(np.float32)
        # Bounded clipping prevents singular flight without introducing any
        # texture or stochastic perturbation.
        magnitude = np.abs(z)
        z = np.where(magnitude > 9.0, z / np.maximum(magnitude, 1.0) * 9.0, z)
    distance = np.stack([np.abs(z - root) for root in roots], axis=0)
    label = np.argmin(distance, axis=0).astype(np.uint8)
    confidence = _norm(np.partition(distance, 1, axis=0)[1]
                       - np.min(distance, axis=0))
    cracks = _edge(label.astype(np.float32) / 4.0, 1)
    faces_a = _f32(((label == 0) | (label == 2) | (label == 4)).astype(np.float32)
                   * (0.68 + 0.32 * confidence))
    faces_b = _f32(((label == 1) | (label == 3)).astype(np.float32)
                   * (0.68 + 0.32 * confidence))
    root_map = roots[label]
    # Optical anatomy uses each pixel's original position inside its basin,
    # not the converged Newton value (which collapses almost every pixel onto
    # a root and would turn the glint/spec bank into a near-solid fill).
    local = (seed_z - root_map) * np.exp(1j * (0.42 + label * 0.57))
    lu, lv = local.real.astype(np.float32), local.imag.astype(np.float32)
    pupils = _line(lv - 0.18 * lu * lu + 0.025 * (label - 2.0), 0.010)
    radial = np.hypot(lu, lv)
    iris_phase = np.mod(radial * (18.0 + label * 1.7)
                        + iterations * 0.071, 1.0)
    iris = _f32(1.0 - np.abs(iris_phase - 0.5) / 0.11)
    caustic = _line(lv * lv - (0.23 + 0.025 * label) * (lu + 0.21), 0.012)
    bevel = _f32(cv2.dilate(cracks, np.ones((5, 5), np.uint8)) - cracks)
    relay = cracks * _f32(cv2.Laplacian(confidence, cv2.CV_32F) * 3.0 + 0.5)
    glint = _inside(np.maximum(np.abs(lu + 0.055), np.abs(lv + 0.048)),
                    0.016, 0.006)
    masks = dict(basin_faces_a=faces_a, basin_faces_b=faces_b,
                 tapetal_cracks=cracks, oriented_pupils=pupils,
                 iris_bands=iris, cat_eye_caustics=caustic,
                 bevel_rims=bevel, relay_fractures=relay,
                 square_glints=glint)
    banks = dict(basin_faces_a="A", basin_faces_b="B", tapetal_cracks="N",
                 oriented_pupils="N", iris_bands="A", cat_eye_caustics="B",
                 bevel_rims="B", relay_fractures="N", square_glints="B")
    tone = _norm(iterations / 13.0 + label.astype(np.float32) * 0.17
                 + confidence * 0.31)
    return _pack(masks, banks, tone)


# ---------------------------------------------------------------------------
# W13 owner-eye replacements.
#
# SPB-WILDS WR-13, 2026-08-24.  Owner verdict: "LAZY" / "exact same
# pattern just recolored" and "do NOT just put random noise in the patterns
# to separate the way they look."  The W12 mechanical pass was green, but its
# contact sheet still exposed lanes, macro icons, sparse loop traces and
# repeated optical basins.  These builders replace the placement equations
# themselves.  Metric movement is recorded in the isolated W13 report after
# the contact-sheet rejection loop; none of this is production-wired.


def _w13_contours(field: np.ndarray, levels: Sequence[float]) -> Tuple[np.ndarray, ...]:
    """Extract deterministic material fronts from an authored scalar field."""
    lo, hi = float(np.min(field)), float(np.max(field))
    scale = 255.0 / max(1.0e-6, hi - lo)
    u8 = np.clip((field - lo) * scale, 0, 255).astype(np.uint8)
    result = []
    for level in levels:
        threshold = int(np.clip((float(level) - lo) * scale, 0, 255))
        found, _hierarchy = cv2.findContours(
            (u8 >= threshold).astype(np.uint8), cv2.RETR_LIST,
            cv2.CHAIN_APPROX_NONE)
        result.extend(contour[:, 0, :].astype(np.float32)
                      for contour in found if len(contour) >= 18)
    return tuple(result)


def _w13_bezier(control: Sequence[Sequence[float]], samples: int = 181) -> np.ndarray:
    p0, p1, p2, p3 = [np.asarray(point, np.float32) for point in control]
    t = np.linspace(0.0, 1.0, int(samples), dtype=np.float32)[:, None]
    return ((1.0 - t) ** 3 * p0 + 3.0 * (1.0 - t) ** 2 * t * p1
            + 3.0 * (1.0 - t) * t * t * p2 + t ** 3 * p3)


def _build_fc_quill_bristle_w13() -> _Grammar:
    """Quills erupt from a branching stress labyrinth, never parallel lanes."""
    names = ("crease_ridges", "crease_lee", "root_bulbs", "collar_rings",
             "rigid_shafts", "hollow_slits", "alternating_barbs",
             "tapered_tips", "strain_crosscuts")
    masks = _new_marks(*names)
    x, y = _xy()
    # The incommensurate stress waves are a literal compressed-skin solve.
    # Only their material fronts render; there is no random/noise layer.
    stress = (0.92 * np.sin((x + 0.37 * y) / 29.0
                            + 0.72 * np.sin(y / 71.0))
              + 0.74 * np.cos((y - 0.21 * x) / 37.0
                              - 0.55 * np.sin(x / 83.0))
              + 0.51 * np.sin((1.31 * x - 0.77 * y) / 53.0)
              + 0.33 * np.cos(np.hypot(x + 76.0, y - 294.0) / 24.0))
    contours = _w13_contours(stress, (-1.18, -0.72, -0.26, 0.21, 0.68, 1.13))
    qindex = 0
    for cindex, contour in enumerate(contours):
        closed = np.vstack([contour, contour[:1]])
        cv2.polylines(masks["crease_ridges"],
                      [np.rint(closed).astype(np.int32).reshape((-1, 1, 2))],
                      False, 0.86, 1 + (cindex % 11 == 0), cv2.LINE_AA)
        stride = 5 + cindex % 4
        for index in range(2, len(contour) - 2, stride):
            root = contour[index]
            tangent = contour[index + 2] - contour[index - 2]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            # Stress sign, not a shared row index, determines eruption side.
            ix = int(np.clip(round(root[0]), 0, 511))
            iy = int(np.clip(round(root[1]), 0, 511))
            side = 1.0 if stress[iy, ix] >= 0.0 else -1.0
            root = root + normal * side * (1.0 + qindex % 3)
            length = 4.0 + ((qindex * 7 + cindex * 3) % 7)
            lean = normal * side + tangent * (0.16 + 0.08 * np.sin(qindex * 0.73))
            lean /= max(0.25, float(np.linalg.norm(lean)))
            tip = root + lean * length
            cv2.circle(masks["root_bulbs"], tuple(np.rint(root).astype(int)),
                       1 + qindex % 2, 1.0, -1, cv2.LINE_AA)
            cv2.circle(masks["collar_rings"], tuple(np.rint(root).astype(int)),
                       2 + qindex % 2, 1.0, 1, cv2.LINE_AA)
            _draw_line(masks["rigid_shafts"], root, tip, 1.0, 1)
            _draw_line(masks["hollow_slits"], root + lean * 1.5,
                       tip - lean * 1.0, 1.0, 1)
            barb_normal = np.asarray([-lean[1], lean[0]], np.float32)
            for fraction in (0.38, 0.63, 0.79):
                anchor = root + lean * length * fraction
                barb_side = -1.0 if (qindex + int(fraction * 100)) & 1 else 1.0
                _draw_line(masks["alternating_barbs"], anchor,
                           anchor - lean * 1.4 + barb_normal * barb_side * 2.2,
                           1.0, 1)
            _draw_line(masks["tapered_tips"], tip - barb_normal * 1.5,
                       tip + barb_normal * 1.5 - lean, 1.0, 1)
            if qindex % 7 == 0:
                _draw_line(masks["strain_crosscuts"], root - tangent * 4.0,
                           root + tangent * 4.0, 1.0, 1)
            qindex += 1
    masks["crease_lee"] = _f32(cv2.GaussianBlur(masks["crease_ridges"],
                                                 (0, 0), 2.8) * 2.4)
    banks = dict(crease_ridges="A", crease_lee="B", root_bulbs="B",
                 collar_rings="A", rigid_shafts="A", hollow_slits="N",
                 alternating_barbs="B", tapered_tips="B",
                 strain_crosscuts="N")
    return _pack(masks, banks, _norm(stress))


def _build_fc_toad_skin_w13() -> _Grammar:
    """Merging reaction watersheds form contiguous dermis, not sparse loops."""
    names = ("gland_territories_a", "gland_territories_b", "mucus_ravines",
             "poison_pores", "capillary_forks", "dry_collars",
             "micro_pit_pairs", "annular_lips", "saddle_wrinkles")
    x, y = _xy()
    u = np.ones((_WORK, _WORK), np.float32)
    v = np.zeros_like(u)
    seed = np.zeros_like(u)
    seed_controls = (((-18, 42), (114, 4), (242, 194), (534, 86)),
                     ((-22, 178), (186, 334), (302, 18), (538, 226)),
                     ((-26, 354), (128, 548), (370, 252), (538, 442)),
                     ((42, -22), (-6, 190), (330, 276), (188, 538)),
                     ((306, -24), (536, 118), (148, 382), (430, 540)),
                     ((534, 8), (388, 174), (72, 254), (-20, 494)))
    for index, control in enumerate(seed_controls):
        points = _w13_bezier(control, 151)
        cv2.polylines(seed, [np.rint(points).astype(np.int32).reshape((-1, 1, 2))],
                      False, 0.66 + 0.05 * (index % 4), 4 + index % 4,
                      cv2.LINE_AA)
    # Unequal seed lobes merge into the same chemical terrain; they never
    # survive as repeated rendered islands.
    for index in range(1, 39):
        cx = int(8 + _halton(index, 2) * 496)
        cy = int(8 + _halton(index, 3) * 496)
        ax = 5 + (index * 7) % 16
        ay = 4 + (index * 11) % 13
        cv2.ellipse(seed, (cx, cy), (ax, ay), (index * 37) % 180,
                    0, 360, 0.46 + 0.05 * (index % 5), -1, cv2.LINE_AA)
    v[:] = np.clip(0.035 + 0.76 * seed, 0.0, 0.94)
    u[:] = np.clip(1.0 - 0.61 * v, 0.0, 1.0)
    kernel = np.asarray([[0.05, 0.20, 0.05], [0.20, -1.0, 0.20],
                         [0.05, 0.20, 0.05]], np.float32)
    feed = 0.0215 + 0.0025 * x / 511.0 + 0.0008 * np.sin(y / 89.0)
    kill = 0.0505 + 0.0020 * y / 511.0 + 0.0006 * np.cos(x / 73.0)
    # The worm-forming feed/kill range preserves a contiguous living dermis.
    # W12 used a higher-kill state that extinguished almost the whole field.
    for _step in range(400):
        lap_u = cv2.filter2D(u, -1, kernel, borderType=cv2.BORDER_REFLECT)
        lap_v = cv2.filter2D(v, -1, kernel, borderType=cv2.BORDER_REFLECT)
        reaction = u * v * v
        u += 0.18 * lap_u - reaction + feed * (1.0 - u)
        v += 0.09 * lap_v + reaction - (feed + kill) * v
        np.clip(u, 0.0, 1.0, out=u)
        np.clip(v, 0.0, 1.0, out=v)
    chem = _norm(v + 0.34 * (1.0 - u))
    smooth = cv2.GaussianBlur(chem, (0, 0), 2.2)
    # Two interlocking chemical ownership lobes cover the dermis.  The
    # thresholds are causal concentration states, not equal-population ranks.
    territory_a = _f32(0.24 + 0.86 * (smooth - 0.06) / 0.52)
    territory_b = _f32(0.22 + 0.84 * (0.72 - smooth) / 0.54)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gx, gy))
    local_max = ((smooth >= cv2.dilate(smooth, np.ones((5, 5), np.uint8)))
                 .astype(np.float32) * _f32((smooth - 0.22) / 0.45))
    pores = cv2.dilate(local_max, np.ones((3, 3), np.uint8))
    ravines = (0.30 * np.maximum(_line(smooth - 0.22, 0.014),
                                 _line(smooth - 0.47, 0.013))
               * _f32((gradient - 0.31) / 0.55))
    collars = (0.34 * _edge((smooth > 0.61).astype(np.float32), 1)
               * _f32((gradient - 0.42) / 0.46))
    lips = (0.28 * _edge((smooth > 0.34).astype(np.float32), 1)
            * _f32((gradient - 0.50) / 0.40))
    capillaries = _f32(gradient * (1.0 - _f32((smooth - 0.70) / 0.18)) * 1.9)
    paired = np.maximum(np.roll(pores, 3, axis=0), np.roll(pores, -3, axis=1))
    wrinkles = _f32(np.maximum(_line(gx + 0.55 * gy, 0.025),
                                _line(gy - 0.42 * gx, 0.025)) * gradient)
    masks = dict(gland_territories_a=territory_a,
                 gland_territories_b=territory_b, mucus_ravines=ravines,
                 poison_pores=pores, capillary_forks=capillaries,
                 dry_collars=collars, micro_pit_pairs=paired,
                 annular_lips=lips, saddle_wrinkles=wrinkles)
    banks = dict(gland_territories_a="A", gland_territories_b="B",
                 mucus_ravines="B", poison_pores="N", capillary_forks="A",
                 dry_collars="N", micro_pit_pairs="A", annular_lips="B",
                 saddle_wrinkles="B")
    return _pack(masks, banks, _norm(chem + 0.21 * gradient))


def _build_fc_antler_bone_w13() -> _Grammar:
    """Anisotropic trabecular load paths fill the canvas without tree recursion."""
    names = ("trabecular_beams_a", "trabecular_beams_b", "marrow_bays",
             "lamellar_rims", "central_canals", "radial_canaliculi",
             "resorption_notches", "fracture_bridges", "osteon_nodes")
    x, y = _xy()
    # This quasiperiodic load solution is deterministic structural math.  Its
    # thresholded ridges are rendered bone beams, not a noise separator.
    load = (np.sin((x + 0.34 * y) / 12.7 + 0.58 * np.sin(y / 63.0))
            + 0.88 * np.sin((y - 0.29 * x) / 16.9
                            - 0.47 * np.sin(x / 71.0))
            + 0.52 * np.cos((1.37 * x + 0.81 * y) / 27.3)
            + 0.31 * np.sin(np.hypot(x - 548.0, y + 94.0) / 19.1))
    ridge = np.abs(np.sin(load * 2.15))
    beam = _f32((ridge - 0.57) / 0.26)
    # Split ownership by signed load; both banks are literal parts of the
    # same connected trabecular system rather than palette-only variants.
    beams_a = beam * _f32((load + 0.42) / 0.72)
    beams_b = beam * _f32((0.58 - load) / 0.78)
    binary = (beam > 0.26).astype(np.uint8)
    cavity_distance = cv2.distanceTransform(1 - binary, cv2.DIST_L2, 3)
    beam_distance = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    marrow = _f32((cavity_distance - 1.5) / 6.5)
    lamellae = np.maximum(_line(np.mod(beam_distance, 4.4), 0.80),
                          _line(np.mod(beam_distance + 2.2, 6.7), 0.72)) * binary
    central = _f32((cavity_distance < 2.1).astype(np.float32)
                   * (1.0 - binary) * _edge(binary.astype(np.float32), 1))
    gx = cv2.Sobel(load.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(load.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    canal = _f32(_line(np.sin((x * gy - y * gx) / 29.0), 0.16) * beam)
    notches = _f32(_edge(binary.astype(np.float32), 1)
                   * _line(np.cos((x - 1.7 * y) / 31.0), 0.18))
    bridges = _f32(_line(np.sin((x + y) / 23.0 + load), 0.12)
                   * _f32((cavity_distance - 1.0) / 5.0))
    curvature = np.abs(cv2.Laplacian(load.astype(np.float32), cv2.CV_32F))
    nodes = _f32((curvature - 0.05) / 0.16) * beam
    masks = dict(trabecular_beams_a=beams_a, trabecular_beams_b=beams_b,
                 marrow_bays=marrow, lamellar_rims=lamellae,
                 central_canals=central, radial_canaliculi=canal,
                 resorption_notches=notches, fracture_bridges=bridges,
                 osteon_nodes=nodes)
    banks = dict(trabecular_beams_a="A", trabecular_beams_b="B",
                 marrow_bays="B", lamellar_rims="A", central_canals="N",
                 radial_canaliculi="A", resorption_notches="B",
                 fracture_bridges="N", osteon_nodes="A")
    return _pack(masks, banks, _norm(load + 0.19 * beam_distance))


def _build_fc_crackle_eyeshine_glass_w13() -> _Grammar:
    """A single brittle optical potential makes nonrepeating crack domains."""
    names = ("compressive_faces_a", "tensile_faces_b", "tapetal_cracks",
             "pupil_shears", "iris_relays", "cusp_caustics",
             "bevel_splinters", "relay_bridges", "glint_chips")
    x, y = _xy()
    z = ((x - 248.0) / 158.0 + 1j * (y - 266.0) / 151.0).astype(np.complex64)
    # A global rational stress potential replaces W12's five repeated Newton
    # eye basins.  Poles are unequal and mostly cropped/off-canvas.
    poles = ((-3.42 + 0.48j, 1.18 - 0.42j),
             (0.31 + 3.16j, -0.86 + 0.77j),
             (3.28 - 1.84j, 0.69 + 1.09j),
             (-2.77 - 2.91j, -1.21 - 0.38j))
    potential = np.zeros_like(z)
    for pole, weight in poles:
        potential += np.complex64(weight) / (z - np.complex64(pole) + 0.075j)
    # Keep the optical polynomial zero-free inside the canvas.  W13's roots
    # created visible pinwheel hubs even after its rational poles were moved.
    potential += np.complex64(3.4 + 0.2j) + 0.46 * z + 0.075 * z * z
    phase = np.angle(potential).astype(np.float32)
    magnitude = np.log1p(np.abs(potential)).astype(np.float32)
    real = potential.real.astype(np.float32)
    imag = potential.imag.astype(np.float32)
    crack_phase = np.mod((phase + np.pi) / (2.0 * np.pi) * 17.0
                         + magnitude * 2.7, 1.0)
    cracks = _f32(1.0 - np.abs(crack_phase - 0.5) / 0.085)
    shear_phase = np.mod((real - 0.37 * imag) * 2.9 + phase * 0.7, 1.0)
    shears = _f32(1.0 - np.abs(shear_phase - 0.5) / 0.09)
    strain = np.sin(phase * 11.0 + magnitude * 3.7)
    faces_a = _f32((strain + 0.14) / 0.72) * (1.0 - 0.68 * cracks)
    faces_b = _f32((0.14 - strain) / 0.72) * (1.0 - 0.68 * cracks)
    relays = _f32(cracks * _line(np.sin(magnitude * 13.0 - phase * 3.0), 0.16))
    pupils = _f32(shears
                  * _line(np.sin(phase * 5.3 - magnitude * 2.1), 0.14))
    caustics = _f32(_line(np.cos(phase * 4.1)
                                + 0.37 * np.sin(magnitude * 6.7) - 0.18,
                                0.085)
                    * (1.0 - cracks))
    bevels = _f32(cv2.dilate(cracks, np.ones((5, 5), np.uint8)) - 0.62 * cracks)
    bridges = _f32(_line(np.sin((x + 0.61 * y) / 13.0 + phase * 2.0), 0.11)
                   * cracks)
    glints = _f32(_line(np.cos(real * 11.0 + imag * 7.0), 0.075)
                   * _line(np.sin(real * 6.0 - imag * 9.0), 0.075))
    masks = dict(compressive_faces_a=faces_a, tensile_faces_b=faces_b,
                 tapetal_cracks=cracks, pupil_shears=pupils,
                 iris_relays=relays, cusp_caustics=caustics,
                 bevel_splinters=bevels, relay_bridges=bridges,
                 glint_chips=glints)
    banks = dict(compressive_faces_a="A", tensile_faces_b="B",
                 tapetal_cracks="N", pupil_shears="N", iris_relays="A",
                 cusp_caustics="B", bevel_splinters="B",
                 relay_bridges="N", glint_chips="A")
    return _pack(masks, banks, _norm(phase + 0.57 * magnitude))


def _build_fc_claw_rake_w13() -> _Grammar:
    """Many unequal local impacts assemble one fractured rake event."""
    names = ("impact_bruises", "impact_rebound", "recessed_gouges", "displaced_lips",
             "terminal_punctures", "stress_crescents", "crushed_chips",
             "debris_tails", "older_crosscuts", "delamination_edges")
    masks = _new_marks(*names)
    # Four collision fronts locate the damage, but their macro paths never
    # render.  Only short 2-8 work-pixel gouges and their causal children do.
    paths = (((-28, 72), (116, -26), (334, 218), (544, 126)),
             ((-24, 408), (168, 560), (338, 216), (544, 382)),
             ((86, -24), (-8, 182), (382, 308), (278, 542)),
             ((516, -28), (362, 142), (116, 326), (-26, 478)))
    impact_index = 0
    all_damage = np.zeros((_WORK, _WORK), np.float32)
    for path_index, control in enumerate(paths):
        points = _w13_bezier(control, 193)
        for anchor_index in range(10 + path_index * 5, 184,
                                  17 + 2 * (path_index % 3)):
            anchor = points[anchor_index]
            tangent = points[anchor_index + 3] - points[anchor_index - 3]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            count = 2 + ((impact_index * 5 + path_index) % 5)
            spread = 2.4 + (impact_index % 4)
            for tooth in range(count):
                side_offset = (tooth - (count - 1) * 0.5) * spread
                root = anchor + normal * side_offset + tangent * (
                    1.8 * np.sin((tooth + 1) * (impact_index + 2)))
                direction = tangent + normal * (0.22 * np.sin(
                    impact_index * 0.91 + tooth * 1.7))
                direction /= max(0.25, float(np.linalg.norm(direction)))
                length = 5.0 + ((impact_index * 11 + tooth * 7) % 13)
                elbow = root + direction * length * 0.58 + normal * (
                    1.5 * np.sin(tooth + impact_index * 0.37))
                tip = root + direction * length
                _draw_line(masks["recessed_gouges"], root, elbow, 1.0,
                           2 if (impact_index + tooth) % 5 == 0 else 1)
                _draw_line(masks["recessed_gouges"], elbow, tip, 1.0, 1)
                lip_normal = np.asarray([-direction[1], direction[0]], np.float32)
                _draw_line(masks["displaced_lips"], root + lip_normal * 1.8,
                           elbow + lip_normal * 1.8, 1.0, 1)
                _draw_line(masks["delamination_edges"], elbow - lip_normal * 2.0,
                           tip - lip_normal * 1.2, 0.88, 1)
                cv2.circle(masks["terminal_punctures"],
                           tuple(np.rint(tip).astype(int)), 1 + tooth % 2,
                           1.0, 1, cv2.LINE_AA)
                if (impact_index + tooth) % 3 == 0:
                    centre = tip - direction * 2.0
                    cv2.ellipse(masks["stress_crescents"],
                                tuple(np.rint(centre).astype(int)),
                                (3 + impact_index % 4, 2 + tooth % 2),
                                float(np.degrees(np.arctan2(direction[1], direction[0]))),
                                185, 345, 1.0, 1, cv2.LINE_AA)
                for chip in range(1 + (impact_index + tooth) % 4):
                    chip_point = tip + direction * (2.0 + chip * 2.1)
                    chip_point += lip_normal * ((chip % 3) - 1) * 1.7
                    cv2.circle(masks["crushed_chips"],
                               tuple(np.rint(chip_point).astype(int)), 1,
                               1.0, -1, cv2.LINE_AA)
                if tooth == count - 1:
                    _draw_line(masks["debris_tails"], tip,
                               tip + direction * (7.0 + impact_index % 6)
                               + lip_normal * (impact_index % 5 - 2), 1.0, 1)
            cv2.circle(all_damage, tuple(np.rint(anchor).astype(int)),
                       3 + impact_index % 3, 1.0, -1, cv2.LINE_AA)
            if impact_index % 6 == 0:
                cross = normal * (5.0 + impact_index % 8)
                _draw_line(masks["older_crosscuts"], anchor - cross,
                           anchor + cross + tangent * 3.0, 1.0, 1)
            impact_index += 1
    all_damage = np.maximum(all_damage, masks["recessed_gouges"])
    masks["impact_bruises"] = _f32(cv2.GaussianBlur(all_damage, (0, 0), 2.7) * 3.2)
    masks["impact_rebound"] = _f32(
        cv2.GaussianBlur(all_damage, (0, 0), 5.4) * 2.7
        - 0.34 * masks["impact_bruises"])
    banks = dict(impact_bruises="B", impact_rebound="A",
                 recessed_gouges="B", displaced_lips="A",
                 terminal_punctures="N", stress_crescents="A",
                 crushed_chips="A", debris_tails="N", older_crosscuts="A",
                 delamination_edges="B")
    distance = cv2.distanceTransform((all_damage < 0.08).astype(np.uint8),
                                     cv2.DIST_L2, 3)
    return _pack(masks, banks, _norm(distance + masks["impact_bruises"] * 5.0))


def _build_fc_bark_camo_w13() -> _Grammar:
    """Cross-loading splits one full-canvas cambium sheet around live knots."""
    names = ("cambium_shoulders_a", "cambium_shoulders_b", "fissure_trunks",
             "branch_splits", "annual_arcs", "lenticel_dashes",
             "callus_bridges", "resin_trails", "peeling_lips")
    masks = _new_marks(*names)
    x, y = _xy()
    # Twelve off-axis knots warp the cambium coordinate so fissures bend,
    # split and reconnect rather than forming the rejected vertical curtain.
    warp_x = x + 18.0 * np.sin(y / 41.0) + 8.0 * np.sin((x + y) / 67.0)
    warp_y = y + 14.0 * np.sin(x / 53.0) - 7.0 * np.cos((x - y) / 79.0)
    knot_data = ((58, 78, 1.0), (206, 44, -0.8), (402, 92, 1.2),
                 (118, 184, -1.1), (314, 166, 0.9), (492, 226, -1.0),
                 (42, 314, 1.1), (236, 286, -1.3), (422, 342, 0.8),
                 (142, 430, 1.0), (336, 456, -0.9), (522, 438, 1.2))
    for cx, cy, spin in knot_data:
        dx, dy = x - cx, y - cy
        r2 = dx * dx + dy * dy + 180.0
        influence = np.exp(-r2 / 2400.0)
        warp_x += spin * influence * dy * 0.38
        warp_y -= spin * influence * dx * 0.24
    growth = (warp_x / 18.0 + 0.62 * np.sin(warp_y / 27.0)
              + 0.31 * np.sin((warp_x - 0.7 * warp_y) / 43.0))
    phase = np.mod(growth, 1.0)
    fissure = _f32(1.0 - np.minimum(phase, 1.0 - phase) / 0.085)
    shoulders = _f32(1.0 - np.abs(phase - 0.28) / 0.17)
    shoulders_b = _f32(1.0 - np.abs(phase - 0.72) / 0.17)
    # Cross-load contours are sparse physical branch splits, not decoration.
    cross = np.mod(warp_y / 31.0 + 0.42 * np.sin(warp_x / 47.0), 1.0)
    branch = _f32(1.0 - np.minimum(cross, 1.0 - cross) / 0.075) * _f32(fissure * 1.6)
    masks["fissure_trunks"] = fissure
    masks["branch_splits"] = branch
    masks["cambium_shoulders_a"] = shoulders * (1.0 - 0.70 * fissure)
    masks["cambium_shoulders_b"] = shoulders_b * (1.0 - 0.70 * fissure)
    for index, (cx, cy, spin) in enumerate(knot_data):
        angle = int((index * 31 + spin * 17) % 180)
        for radius in (5 + index % 3, 10 + (index * 3) % 6,
                       17 + (index * 5) % 8):
            cv2.ellipse(masks["annual_arcs"], (cx, cy),
                        (radius, max(3, int(radius * (0.52 + 0.05 * (index % 4))))),
                        angle, 18 + index % 5 * 7, 326 - index % 4 * 9,
                        1.0, 1, cv2.LINE_AA)
        for ray in range(3 + index % 4):
            theta = index * 0.77 + ray * (0.83 + 0.07 * (index % 3))
            start = np.asarray([cx, cy], np.float32)
            end = start + np.asarray([np.cos(theta), np.sin(theta)]) * (
                7.0 + (index * 3 + ray * 5) % 15)
            _draw_line(masks["callus_bridges"], start, end, 1.0, 1)
        resin_end = np.asarray([cx + spin * (8 + index % 5),
                                cy + 13 + (index * 7) % 18])
        _draw_line(masks["resin_trails"], (cx + 2, cy + 1), resin_end, 1.0,
                   2 if index % 4 == 0 else 1)
    # Lenticels and peel lips are selected intersections of the two living
    # growth coordinates, so they remain attached to cambium anatomy.
    masks["lenticel_dashes"] = _f32(
        _line(np.sin(warp_y / 9.0 + growth * 0.7), 0.12) * shoulders_b)
    masks["peeling_lips"] = _f32(
        _line(np.cos(warp_y / 17.0 - growth * 0.9), 0.13) * shoulders)
    banks = dict(cambium_shoulders_a="A", cambium_shoulders_b="B",
                 fissure_trunks="B", branch_splits="N", annual_arcs="A",
                 lenticel_dashes="B", callus_bridges="A",
                 resin_trails="B", peeling_lips="A")
    return _pack(masks, banks, _norm(growth + 0.23 * cross))


def _build_fc_feathered_wing_w13() -> _Grammar:
    """A canvas-filling molt front advects unequal feather packets around tears."""
    names = ("vane_packets_a", "vane_packets_b", "rachis_shafts",
             "paired_barbs", "hooklet_combs", "downy_wakes",
             "ocellus_notches", "broken_tips", "overlap_lips")
    masks = _new_marks(*names)
    tears = ((104.0, 126.0, 1.3), (382.0, 92.0, -1.1),
             (262.0, 284.0, 1.5), (458.0, 398.0, -1.2),
             (82.0, 442.0, 0.9))
    # Low-discrepancy chronology only places biological packets; all visible
    # direction and curvature comes from the aerodynamic pressure field.
    for index in range(1, 421):
        root = np.asarray([6.0 + _halton(index, 2) * 500.0,
                           6.0 + _halton(index, 3) * 500.0], np.float32)
        velocity = np.asarray([0.93, 0.22 * np.sin(root[0] / 63.0)], np.float32)
        for cx, cy, spin in tears:
            delta = root - np.asarray([cx, cy], np.float32)
            d2 = float(np.dot(delta, delta) + 260.0)
            velocity += spin * 560.0 / d2 * np.asarray([-delta[1], delta[0]], np.float32)
        velocity /= max(0.25, float(np.linalg.norm(velocity)))
        normal = np.asarray([-velocity[1], velocity[0]], np.float32)
        length = 13.0 + (index * 11) % 23
        bend = normal * (2.0 + (index * 7) % 7) * np.sin(index * 0.83)
        mid = root + velocity * length * 0.54 + bend
        tip = root + velocity * length + bend * 0.42
        width = 2.5 + (index * 5) % 5
        polygon = [root - normal * width * 0.72,
                   mid - normal * width, tip,
                   mid + normal * width, root + normal * width * 0.72]
        vane_name = "vane_packets_a" if index % 5 in (0, 1, 4) else "vane_packets_b"
        _draw_poly(masks[vane_name], polygon, 0.72 + 0.06 * (index % 4), 1, True)
        _draw_line(masks["rachis_shafts"], root - velocity * 2.0, mid, 1.0, 1)
        _draw_line(masks["rachis_shafts"], mid, tip, 1.0, 1)
        for fraction in (0.22, 0.38, 0.55, 0.70, 0.84):
            centre = ((1.0 - fraction) * root + fraction * tip
                      + bend * np.sin(np.pi * fraction) * 0.6)
            local_width = width * (1.0 - fraction * 0.72)
            _draw_line(masks["paired_barbs"], centre,
                       centre + normal * local_width - velocity * 1.6, 1.0, 1)
            _draw_line(masks["paired_barbs"], centre,
                       centre - normal * local_width - velocity * 1.6, 1.0, 1)
        _draw_line(masks["hooklet_combs"], mid - normal * width,
                   mid + normal * width, 1.0, 1)
        cv2.ellipse(masks["overlap_lips"], tuple(np.rint(root).astype(int)),
                    (max(2, int(width)), 2),
                    float(np.degrees(np.arctan2(velocity[1], velocity[0]))),
                    8, 172, 1.0, 1, cv2.LINE_AA)
        cv2.circle(masks["downy_wakes"], tuple(np.rint(root - velocity * 2).astype(int)),
                   1 + index % 2, 1.0, 1, cv2.LINE_AA)
        if index % 9 == 0:
            cv2.circle(masks["ocellus_notches"], tuple(np.rint(mid).astype(int)),
                       1 + index % 2, 1.0, 1, cv2.LINE_AA)
        if index % 13 == 0:
            _draw_line(masks["broken_tips"], tip - normal * 2.4,
                       tip + normal * 2.4 - velocity * 2.1, 1.0, 1)
    x, y = _xy()
    pressure = 0.002 * x - 0.001 * y
    for cx, cy, spin in tears:
        pressure += spin * np.arctan2(y - cy, x - cx)
    banks = dict(vane_packets_a="A", vane_packets_b="B",
                 rachis_shafts="B", paired_barbs="B", hooklet_combs="A",
                 downy_wakes="N", ocellus_notches="A", broken_tips="N",
                 overlap_lips="B")
    return _pack(masks, banks, _norm(pressure))


def _build_fc_dorsal_ridge_w13() -> _Grammar:
    """Colliding armored fronts carry dense local scutes and saw keels."""
    names = ("base_membranes_a", "base_membranes_b", "spine_plates",
             "sawline_tips", "keel_ribs", "osteon_pores",
             "ligament_slots", "abrasion_chips", "collision_sutures")
    masks = _new_marks(*names)
    fronts = (((-24, 46), (122, -12), (326, 184), (542, 94)),
              ((-26, 156), (176, 312), (344, 8), (540, 202)),
              ((-24, 286), (116, 158), (374, 416), (540, 300)),
              ((-24, 446), (142, 554), (354, 286), (540, 454)),
              ((58, -26), (-18, 142), (316, 294), (168, 540)),
              ((226, -26), (442, 118), (126, 382), (364, 540)),
              ((512, -22), (352, 138), (564, 344), (432, 540)),
              ((540, 70), (398, 170), (138, 356), (-24, 486)))
    front_union = np.zeros((_WORK, _WORK), np.float32)
    plate_index = 0
    for front_index, control in enumerate(fronts):
        points = _w13_bezier(control, 201)
        polyline = np.rint(points).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(front_union, [polyline], False, 1.0,
                      3 + front_index % 3, cv2.LINE_AA)
        for idx in range(4, 196, 5 + front_index % 3):
            centre = points[idx]
            tangent = points[idx + 3] - points[idx - 3]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            side = -1.0 if (front_index + idx // 7) & 1 else 1.0
            length = 3.5 + (plate_index * 7) % 6
            height = 5.0 + (plate_index * 11) % 8
            base = centre - normal * side * 2.5
            tip = centre + normal * side * height
            polygon = [base - tangent * length, base + tangent * length,
                       tip + tangent * 1.2, tip - tangent * 1.2]
            _draw_poly(masks["spine_plates"], polygon,
                       0.78 + 0.05 * (plate_index % 4), 1, True)
            _draw_line(masks["keel_ribs"], base, tip, 1.0, 1)
            _draw_line(masks["sawline_tips"], tip - tangent * 2.0,
                       tip + tangent * 2.0 - normal * side, 1.0, 1)
            cv2.circle(masks["osteon_pores"], tuple(np.rint(centre).astype(int)),
                       1, 1.0, 1, cv2.LINE_AA)
            _draw_line(masks["ligament_slots"], base - tangent * 2.0,
                       base + tangent * 2.0, 1.0, 1)
            if plate_index % 9 == 0:
                _draw_line(masks["abrasion_chips"], tip,
                           tip + tangent * 3.0 - normal * side * 2.0, 1.0, 1)
            plate_index += 1
    near = cv2.GaussianBlur(front_union, (0, 0), 5.5)
    masks["base_membranes_a"] = _f32(near * 2.2
                                      * (0.60 + 0.40 * (np.sin((_xy()[0] + _xy()[1]) / 37.0) > 0)))
    masks["base_membranes_b"] = _f32(near * 2.2
                                      * (0.60 + 0.40 * (np.sin((_xy()[0] + _xy()[1]) / 37.0) <= 0)))
    masks["collision_sutures"] = _f32(_edge((near > 0.19).astype(np.float32), 1)
                                       * cv2.dilate(front_union, np.ones((5, 5), np.uint8)))
    x, y = _xy()
    banks = dict(base_membranes_a="A", base_membranes_b="B",
                 spine_plates="A", sawline_tips="B", keel_ribs="B",
                 osteon_pores="N", ligament_slots="N", abrasion_chips="B",
                 collision_sutures="A")
    return _pack(masks, banks, _norm(near + 0.18 * x - 0.13 * y))


def _build_fc_snakeskin_w13() -> _Grammar:
    """Ten open body currents interlock fine scutes without macro loops."""
    names = ("belly_scutes_a", "dorsal_scutes_b", "hinge_seams",
             "overlap_lips", "longitudinal_keels", "pit_organs",
             "molt_tears", "lip_teeth", "shed_membranes")
    masks = _new_marks(*names)
    bodies = (((-26, 48), (132, -28), (326, 198), (538, 94), 18),
              ((-24, 112), (166, 262), (340, 12), (538, 166), 21),
              ((-28, 208), (118, 92), (382, 338), (540, 230), 16),
              ((-24, 302), (178, 446), (314, 118), (540, 326), 23),
              ((-26, 422), (112, 550), (372, 282), (538, 456), 19),
              ((42, -26), (-18, 156), (286, 312), (146, 540), 17),
              ((178, -24), (428, 116), (102, 376), (338, 540), 22),
              ((492, -26), (332, 174), (558, 344), (432, 540), 18),
              ((538, 64), (402, 148), (98, 382), (-26, 468), 20),
              ((526, 496), (342, 566), (196, 38), (4, -24), 16))
    body_union = np.zeros((_WORK, _WORK), np.float32)
    scale_index = 0
    for body_index, (*control, half_width) in enumerate(bodies):
        points = _w13_bezier(control, 241)
        cv2.polylines(body_union,
                      [np.rint(points).astype(np.int32).reshape((-1, 1, 2))],
                      False, 1.0, int(half_width * 2), cv2.LINE_AA)
        for idx in range(4, 236, 4 + body_index % 3):
            centre = points[idx]
            tangent = points[idx + 3] - points[idx - 3]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            # Every sample builds a small cross-body assembly.  No wide body
            # primitive is composited; body_union only computes shed tissue.
            length = 3.0 + scale_index % 3
            for lane in range(-3, 4):
                lane_fraction = lane / 3.4
                p = centre + normal * half_width * lane_fraction
                width = 2.0 + ((scale_index + lane + body_index) % 3)
                if abs(lane) <= 1:
                    polygon = [p - tangent * length - normal * width,
                               p + tangent * length - normal * width,
                               p + tangent * length + normal * width,
                               p - tangent * length + normal * width]
                    _draw_poly(masks["belly_scutes_a"], polygon,
                               0.76 + 0.05 * ((scale_index + lane) % 4), 1, True)
                else:
                    cv2.ellipse(masks["dorsal_scutes_b"],
                                tuple(np.rint(p).astype(int)),
                                (int(length), int(width)),
                                float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                                0, 360, 0.82, -1, cv2.LINE_AA)
                _draw_line(masks["overlap_lips"], p - normal * width,
                           p + tangent * length + normal * width, 1.0, 1)
                if lane == 0:
                    _draw_line(masks["longitudinal_keels"],
                               p - tangent * length, p + tangent * length,
                               1.0, 1)
                    _draw_line(masks["hinge_seams"], p - normal * width,
                               p + normal * width, 1.0, 1)
                if abs(lane) == 3 and scale_index % 7 == 0:
                    cv2.circle(masks["pit_organs"],
                               tuple(np.rint(p + tangent).astype(int)), 1,
                               1.0, -1, cv2.LINE_AA)
                if (scale_index + lane * 3) % 11 == 0:
                    _draw_line(masks["lip_teeth"], p + normal * width,
                               p + normal * (width + 2) - tangent, 1.0, 1)
            if scale_index % 17 == 0:
                _draw_line(masks["molt_tears"], centre - normal * 5.0,
                           centre + normal * 5.0 + tangent * 4.0, 1.0, 1)
            scale_index += 1
    # A narrow causal envelope under overlapped scutes is shed membrane, not
    # a broad painted ribbon; it closes tiny gaps between fine assemblies.
    masks["shed_membranes"] = _f32(cv2.GaussianBlur(body_union, (0, 0), 1.8) * 0.52)
    banks = dict(belly_scutes_a="A", dorsal_scutes_b="B", hinge_seams="N",
                 overlap_lips="B", longitudinal_keels="A", pit_organs="B",
                 molt_tears="N", lip_teeth="A", shed_membranes="B")
    x, y = _xy()
    return _pack(masks, banks, _norm(0.19 * x - 0.14 * y + body_union))


def _build_fc_batwing_w13() -> _Grammar:
    """Cropped bones enter every edge and tension one continuous membrane."""
    names = ("membrane_stress_a", "membrane_stress_b", "cropped_bones",
             "hooked_joints", "capillary_trees", "tension_striae",
             "echo_scratches", "trailing_tears", "dew_notches")
    masks = _new_marks(*names)
    bones = (((-28, 26), (108, -12), (214, 198), (536, 86)),
             ((-24, 132), (182, 44), (266, 354), (540, 176)),
             ((-28, 286), (122, 198), (380, 478), (540, 304)),
             ((-22, 474), (156, 550), (334, 308), (540, 452)),
             ((46, -24), (-18, 172), (332, 214), (158, 540)),
             ((196, -28), (436, 114), (88, 372), (344, 540)),
             ((486, -24), (326, 156), (550, 356), (436, 540)),
             ((540, 46), (394, 156), (142, 332), (-24, 458)),
             ((512, 520), (294, 548), (224, 14), (10, -20)))
    skeleton = np.zeros((_WORK, _WORK), np.float32)
    joint_index = 0
    for bone_index, control in enumerate(bones):
        points = _w13_bezier(control, 181)
        poly = np.rint(points).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(masks["cropped_bones"], [poly], False, 1.0,
                      3 if bone_index % 3 == 0 else 2, cv2.LINE_AA)
        cv2.polylines(skeleton, [poly], False, 1.0, 2, cv2.LINE_AA)
        for idx in range(12 + bone_index % 5, 174, 17 + bone_index % 4):
            joint = points[idx]
            tangent = points[idx + 3] - points[idx - 3]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            cv2.circle(masks["hooked_joints"], tuple(np.rint(joint).astype(int)),
                       2 + joint_index % 3, 1.0, 1, cv2.LINE_AA)
            side = -1.0 if (joint_index + bone_index) & 1 else 1.0
            branch = joint + normal * side * (8.0 + joint_index % 11)
            _draw_line(masks["capillary_trees"], joint, branch, 1.0, 1)
            for fork in (-1.0, 1.0):
                tip = branch + normal * side * (5.0 + (joint_index * 3) % 6)
                tip += tangent * fork * (4.0 + (joint_index + bone_index) % 7)
                _draw_line(masks["capillary_trees"], branch, tip, 1.0, 1)
            _draw_line(masks["tension_striae"], joint - tangent * 4.0,
                       joint + tangent * 4.0, 1.0, 1)
            if joint_index % 5 == 0:
                _draw_line(masks["trailing_tears"], branch,
                           branch + tangent * 5.0 + normal * side * 4.0,
                           1.0, 1)
            if joint_index % 4 == 0:
                cv2.circle(masks["dew_notches"], tuple(np.rint(branch).astype(int)),
                           1, 1.0, -1, cv2.LINE_AA)
            joint_index += 1
    distance = cv2.distanceTransform((skeleton < 0.08).astype(np.uint8),
                                     cv2.DIST_L2, 3)
    # Interleaved 4-8 work-pixel stress lamellae fill space between bones.
    stress_phase = np.mod(distance / 7.2
                          + 0.13 * np.sin((_xy()[0] - _xy()[1]) / 61.0), 1.0)
    envelope = _f32((24.0 - distance) / 12.0)
    masks["membrane_stress_a"] = _f32(
        (1.0 - np.abs(stress_phase - 0.24) / 0.23) * envelope)
    masks["membrane_stress_b"] = _f32(
        (1.0 - np.abs(stress_phase - 0.72) / 0.23) * envelope)
    masks["echo_scratches"] = _f32(
        _line(np.sin((_xy()[0] + 1.4 * _xy()[1]) / 17.0 + distance / 9.0),
              0.11) * envelope)
    banks = dict(membrane_stress_a="A", membrane_stress_b="B",
                 cropped_bones="B", hooked_joints="A", capillary_trees="B",
                 tension_striae="A", echo_scratches="N",
                 trailing_tears="N", dew_notches="B")
    return _pack(masks, banks, _norm(distance + skeleton * 7.0))


def _build_fc_gator_hide_w13() -> _Grammar:
    """Six colliding armor rafts fill the canvas with unequal osteoderms."""
    names = ("osteoderm_faces_a", "osteoderm_faces_b", "raised_keels",
             "growth_annuli", "sensory_pits", "seam_canals",
             "interlocking_teeth", "scar_slashes", "collision_grooves")
    masks = _new_marks(*names)
    rafts = (((-28, 54), (148, -22), (326, 210), (542, 114), 34),
             ((-26, 178), (194, 344), (324, 24), (542, 238), 39),
             ((-26, 348), (118, 220), (386, 488), (540, 366), 33),
             ((44, -28), (-14, 178), (316, 286), (166, 542), 36),
             ((274, -28), (522, 136), (126, 378), (414, 542), 41),
             ((540, 72), (384, 166), (108, 354), (-28, 472), 35))
    scute_index = 0
    for raft_index, (*control, raft_width) in enumerate(rafts):
        points = _w13_bezier(control, 231)
        for idx in range(5, 225, 6 + raft_index % 2):
            centre = points[idx]
            tangent = points[idx + 4] - points[idx - 4]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            for lane in range(-3, 4):
                p = centre + normal * lane * (raft_width / 7.2)
                half_l = 3.0 + (scute_index * 7 + lane) % 5
                half_w = 2.5 + (scute_index * 11 - lane) % 4
                shear = ((scute_index + lane * 3) % 5 - 2) * 0.65
                polygon = [p - tangent * half_l - normal * half_w,
                           p + tangent * (half_l + shear) - normal * half_w,
                           p + tangent * half_l + normal * half_w,
                           p - tangent * (half_l - shear) + normal * half_w]
                face = "osteoderm_faces_a" if (lane + raft_index) % 3 else "osteoderm_faces_b"
                _draw_poly(masks[face], polygon,
                           0.76 + 0.05 * (scute_index % 4), 1, True)
                _draw_line(masks["raised_keels"], p - tangent * (half_l - 1),
                           p + tangent * (half_l - 1), 1.0, 1)
                inset = [p + (vertex - p) * 0.61 for vertex in polygon]
                _draw_poly(masks["growth_annuli"], inset, 1.0, 1, False)
                _draw_line(masks["seam_canals"], polygon[0], polygon[1], 1.0, 1)
                if scute_index % 5 == 0:
                    cv2.circle(masks["sensory_pits"],
                               tuple(np.rint(p + tangent * 1.4).astype(int)),
                               1, 1.0, -1, cv2.LINE_AA)
                if scute_index % 9 == 0:
                    _draw_line(masks["interlocking_teeth"],
                               p + normal * half_w,
                               p + normal * (half_w + 2.5) - tangent, 1.0, 1)
                if scute_index % 17 == 0:
                    _draw_line(masks["scar_slashes"], p - normal * 4.0,
                               p + normal * 4.0 + tangent * 3.0, 1.0, 1)
                scute_index += 1
    total_faces = np.maximum(masks["osteoderm_faces_a"],
                             masks["osteoderm_faces_b"])
    masks["collision_grooves"] = _f32(_edge(total_faces, 1)
                                       * cv2.GaussianBlur(total_faces, (0, 0), 2.4))
    x, y = _xy()
    banks = dict(osteoderm_faces_a="A", osteoderm_faces_b="B",
                 raised_keels="B", growth_annuli="A", sensory_pits="B",
                 seam_canals="N", interlocking_teeth="B", scar_slashes="N",
                 collision_grooves="A")
    return _pack(masks, banks, _norm(0.17 * x + 0.11 * y + total_faces))


def _build_fc_hide_scale_glass_w13() -> _Grammar:
    """Nonparallel refractive streams split into a dense lenticular hide."""
    names = ("lens_bodies_a", "lens_bodies_b", "rim_bevels",
             "focal_caustics", "stress_veins", "micropore_pairs",
             "scuff_arcs", "occlusion_lips", "collision_prisms")
    masks = _new_marks(*names)
    lens_index = 0
    for stream in range(1, 43):
        edge = stream % 4
        a = 12.0 + _halton(stream, 2) * 488.0
        b = 12.0 + _halton(stream, 3) * 488.0
        c = 12.0 + _halton(stream, 5) * 488.0
        d = 12.0 + _halton(stream, 7) * 488.0
        if edge == 0:
            control = ((-18, a), (b, c), (d, 512 - b), (530, c))
        elif edge == 1:
            control = ((a, -18), (c, b), (512 - d, c), (b, 530))
        elif edge == 2:
            control = ((530, a), (512 - b, d), (c, b), (-18, 512 - c))
        else:
            control = ((a, 530), (d, 512 - b), (b, c), (512 - a, -18))
        points = _w13_bezier(control, 171)
        for idx in range(5 + stream % 4, 166, 5 + stream % 3):
            centre = points[idx]
            if not (1 <= centre[0] < 511 and 1 <= centre[1] < 511):
                continue
            tangent = points[idx + 3] - points[idx - 3]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            major = 3.0 + (lens_index * 7) % 5
            minor = 2.0 + (lens_index * 11) % 3
            polygon = [centre - tangent * major,
                       centre - normal * minor + tangent,
                       centre + tangent * major,
                       centre + normal * minor - tangent]
            body = "lens_bodies_a" if (stream + lens_index) % 4 in (0, 1) else "lens_bodies_b"
            _draw_poly(masks[body], polygon,
                       0.74 + 0.06 * (lens_index % 4), 1, True)
            _draw_poly(masks["rim_bevels"], polygon, 1.0, 1, False)
            _draw_line(masks["focal_caustics"], centre - tangent * (major - 1),
                       centre + tangent * (major - 1), 1.0, 1)
            _draw_line(masks["stress_veins"], centre - normal * minor,
                       centre + normal * minor, 1.0, 1)
            for side in (-1.0, 1.0):
                pore = centre + normal * side * max(1.0, minor - 1.0)
                cv2.circle(masks["micropore_pairs"],
                           tuple(np.rint(pore).astype(int)), 1, 1.0, 1,
                           cv2.LINE_AA)
            if lens_index % 8 == 0:
                cv2.ellipse(masks["scuff_arcs"],
                            tuple(np.rint(centre).astype(int)),
                            (int(major + 2), int(minor + 2)),
                            float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                            190, 330, 1.0, 1, cv2.LINE_AA)
            _draw_line(masks["occlusion_lips"], polygon[2], polygon[3], 1.0, 1)
            if lens_index % 13 == 0:
                _draw_line(masks["collision_prisms"], centre - tangent * 2.0,
                           centre + normal * 3.0, 1.0, 1)
                _draw_line(masks["collision_prisms"], centre + tangent * 2.0,
                           centre - normal * 3.0, 1.0, 1)
            lens_index += 1
    x, y = _xy()
    banks = dict(lens_bodies_a="A", lens_bodies_b="B", rim_bevels="B",
                 focal_caustics="B", stress_veins="N", micropore_pairs="A",
                 scuff_arcs="A", occlusion_lips="N", collision_prisms="B")
    return _pack(masks, banks, _norm(np.sin(x / 43.0 + y / 67.0)
                                     + np.cos((x - 1.3 * y) / 79.0)))


def _build_fc_quill_bristle_w14() -> _Grammar:
    """Open cross-loaded skin creases carry dense, locally varied quills."""
    names = ("crease_shoulders_a", "crease_shoulders_b", "root_bulbs",
             "collar_rings", "rigid_shafts", "hollow_slits",
             "alternating_barbs", "tapered_tips", "strain_crosscuts")
    masks = _new_marks(*names)
    # W13's scalar contours closed into repeated giant islands.  These 28
    # cross-loaded creases all enter and leave the canvas, use every edge
    # pairing, and have no shared hub or translated curve template.
    qindex = 0
    crease_union = np.zeros((_WORK, _WORK), np.float32)
    for crease in range(1, 29):
        pairing = crease % 6
        a = 6.0 + _halton(crease, 2) * 500.0
        b = 6.0 + _halton(crease, 3) * 500.0
        c = 6.0 + _halton(crease, 5) * 500.0
        d = 6.0 + _halton(crease, 7) * 500.0
        if pairing == 0:
            control = ((-18, a), (c, -24), (d, 542), (530, b))
        elif pairing == 1:
            control = ((a, -18), (-26, c), (542, d), (b, 530))
        elif pairing == 2:
            control = ((-18, a), (c, d), (b, 512 - c), (d, 530))
        elif pairing == 3:
            control = ((a, -18), (d, b), (512 - c, a), (530, d))
        elif pairing == 4:
            control = ((530, a), (512 - b, d), (c, b), (-18, 512 - d))
        else:
            control = ((a, 530), (c, 512 - b), (d, b), (512 - a, -18))
        points = _w13_bezier(control, 191)
        poly = np.rint(points).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(crease_union, [poly], False, 1.0,
                      2 if crease % 7 == 0 else 1, cv2.LINE_AA)
        for idx in range(4 + crease % 4, 186, 4 + crease % 3):
            root = points[idx]
            if not (0 <= root[0] < 512 and 0 <= root[1] < 512):
                continue
            tangent = points[idx + 3] - points[idx - 3]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            side = -1.0 if (qindex + crease) & 1 else 1.0
            root = root + normal * side * (1.5 + qindex % 3)
            lean = normal * side + tangent * (0.13 + 0.07 * np.sin(qindex * 0.77))
            lean /= max(0.25, float(np.linalg.norm(lean)))
            length = 4.0 + (qindex * 11 + crease * 3) % 7
            tip = root + lean * length
            cv2.circle(masks["root_bulbs"], tuple(np.rint(root).astype(int)),
                       1 + qindex % 2, 1.0, -1, cv2.LINE_AA)
            cv2.circle(masks["collar_rings"], tuple(np.rint(root).astype(int)),
                       2 + qindex % 2, 1.0, 1, cv2.LINE_AA)
            _draw_line(masks["rigid_shafts"], root, tip, 1.0, 1)
            _draw_line(masks["hollow_slits"], root + lean * 1.4,
                       tip - lean * 1.1, 1.0, 1)
            barb_normal = np.asarray([-lean[1], lean[0]], np.float32)
            for fraction in (0.39, 0.66):
                anchor = root + lean * length * fraction
                barb_side = -1.0 if (qindex + int(fraction * 10)) & 1 else 1.0
                _draw_line(masks["alternating_barbs"], anchor,
                           anchor - lean * 1.4 + barb_normal * barb_side * 2.0,
                           1.0, 1)
            _draw_line(masks["tapered_tips"], tip - barb_normal * 1.4,
                       tip + barb_normal * 1.4 - lean, 1.0, 1)
            if qindex % 8 == 0:
                _draw_line(masks["strain_crosscuts"], root - tangent * 3.5,
                           root + tangent * 3.5, 1.0, 1)
            qindex += 1
    masks["crease_shoulders_a"] = _f32(
        cv2.GaussianBlur(crease_union, (0, 0), 2.6) * 2.4)
    masks["crease_shoulders_b"] = _f32(
        cv2.GaussianBlur(crease_union, (0, 0), 5.1) * 1.7
        - 0.32 * masks["crease_shoulders_a"])
    x, y = _xy()
    banks = dict(crease_shoulders_a="A", crease_shoulders_b="B",
                 root_bulbs="B", collar_rings="A", rigid_shafts="A",
                 hollow_slits="N", alternating_barbs="B",
                 tapered_tips="B", strain_crosscuts="N")
    return _pack(masks, banks, _norm(0.19 * x - 0.13 * y + crease_union * 4.0))


def _build_fc_bark_camo_w14() -> _Grammar:
    """A continuous cambium growth field delaminates into non-lane camo plates."""
    names = ("cambium_islands_a", "cork_islands_b", "fissure_boundaries",
             "peeling_lips", "annual_arcs", "lenticel_dashes",
             "callus_rays", "resin_trails", "abrasion_notches")
    x, y = _xy()
    growth = (0.93 * np.sin(x / 17.0 + 0.71 * np.sin(y / 43.0))
              + 0.78 * np.sin((x + 1.13 * y) / 27.0
                              - 0.49 * np.cos(x / 51.0))
              + 0.59 * np.cos((x - 1.47 * y) / 35.0)
              + 0.34 * np.sin(np.hypot(x + 84.0, y - 322.0) / 19.0))
    smooth = cv2.GaussianBlur(growth.astype(np.float32), (0, 0), 2.1)
    island_a = _f32((smooth + 0.48) / 0.78)
    island_b = _f32((0.42 - smooth) / 0.76)
    boundary = np.maximum(_line(smooth + 0.36, 0.055),
                          _line(smooth - 0.24, 0.050))
    peel = np.maximum(_line(smooth + 0.08, 0.045),
                      _line(smooth - 0.61, 0.042))
    masks = dict(cambium_islands_a=island_a, cork_islands_b=island_b,
                 fissure_boundaries=boundary, peeling_lips=peel,
                 annual_arcs=np.zeros_like(x), lenticel_dashes=np.zeros_like(x),
                 callus_rays=np.zeros_like(x), resin_trails=np.zeros_like(x),
                 abrasion_notches=np.zeros_like(x))
    knots = ((54, 72, 18, 9, 17), (226, 48, 13, 21, -31),
             (412, 108, 24, 12, 58), (118, 232, 21, 14, -47),
             (314, 204, 12, 25, 29), (480, 278, 22, 11, -18),
             (62, 388, 15, 24, 69), (252, 354, 26, 13, -38),
             (430, 458, 18, 22, 11), (166, 502, 23, 10, 42))
    for index, (cx, cy, rx, ry, angle) in enumerate(knots):
        for inset in (0, 4, 8):
            cv2.ellipse(masks["annual_arcs"], (cx, cy),
                        (max(3, rx - inset), max(3, ry - inset // 2)),
                        angle, 18 + index % 4 * 7, 326 - index % 3 * 11,
                        1.0, 1, cv2.LINE_AA)
        for ray in range(2 + index % 4):
            theta = index * 0.79 + ray * 1.13
            start = np.asarray([cx, cy], np.float32)
            end = start + np.asarray([np.cos(theta), np.sin(theta)]) * (
                7.0 + (index * 5 + ray * 3) % 13)
            _draw_line(masks["callus_rays"], start, end, 1.0, 1)
        _draw_line(masks["resin_trails"], (cx + 2, cy + 1),
                   (cx + 3 + index % 5, cy + 9 + (index * 7) % 15),
                   1.0, 1 + (index % 4 == 0))
    # Lenticels and abrasion are intersections of the live plate interiors
    # with fine growth-age phases; they do not form a global row or grid.
    masks["lenticel_dashes"] = _f32(
        _line(np.sin((0.81 * x + 1.37 * y) / 8.7 + smooth * 1.9), 0.115)
        * island_b)
    masks["abrasion_notches"] = _f32(
        _line(np.cos((1.29 * x - 0.73 * y) / 11.3 - smooth * 1.4), 0.105)
        * peel)
    banks = dict(cambium_islands_a="A", cork_islands_b="B",
                 fissure_boundaries="B", peeling_lips="A", annual_arcs="A",
                 lenticel_dashes="B", callus_rays="A", resin_trails="B",
                 abrasion_notches="N")
    return _pack(masks, banks, _norm(smooth))


def _build_fc_dorsal_ridge_w14() -> _Grammar:
    """Three off-canvas pressure systems collide into a dense armored drift."""
    names = ("compressed_scutes_a", "rebound_scutes_b", "keel_network",
             "saw_tip_edges", "base_membranes", "osteon_pores",
             "ligament_slots", "abrasion_chips", "collision_sutures")
    x, y = _xy()
    # All pressure origins are cropped away, so the visible result has no hub,
    # fan, lane or repeated icon.  Different wavelengths make a genuine
    # collision field rather than translated rings.
    u1 = 0.91 * (x + 182.0) + 0.42 * (y - 92.0)
    v1 = -0.42 * (x + 182.0) + 0.91 * (y - 92.0)
    u2 = 0.71 * (x - 714.0) - 0.70 * (y - 366.0)
    v2 = 0.70 * (x - 714.0) + 0.71 * (y - 366.0)
    u3 = 0.53 * (x - 268.0) + 0.85 * (y + 344.0)
    v3 = -0.85 * (x - 268.0) + 0.53 * (y + 344.0)
    d1 = np.hypot(u1 * 0.83, v1 * 1.21)
    d2 = np.hypot(u2 * 1.17, v2 * 0.78)
    d3 = np.hypot(u3 * 0.92, v3 * 1.14)
    w1 = np.sin(d1 / 11.3 + 0.24 * np.sin(y / 49.0))
    w2 = np.sin(d2 / 14.9 - 0.31 * np.cos(x / 57.0))
    w3 = np.sin(d3 / 18.7 + 0.27 * np.sin((x - y) / 73.0))
    pressure = w1 + 0.88 * w2 + 0.73 * w3
    compressed = _f32((pressure - 0.18) / 0.92)
    rebound = _f32((-pressure - 0.16) / 0.88)
    # Fine keels are loci where different pressure waves disagree; they are
    # 1-3 work pixels even though their connected drift spans the canvas.
    disagreement = np.minimum.reduce((np.abs(w1 - w2), np.abs(w2 - w3),
                                      np.abs(w3 - w1)))
    keels = _f32((0.19 - disagreement) / 0.13)
    plate_boundary = _edge((pressure > 0.0).astype(np.float32), 1)
    saw = _f32(plate_boundary
               * _line(np.sin((x + 1.7 * y) / 5.7 + pressure * 1.8), 0.14))
    membrane = _f32(cv2.GaussianBlur(plate_boundary, (0, 0), 3.4) * 2.1
                    - 0.42 * plate_boundary)
    gx = cv2.Sobel(pressure.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(pressure.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gx, gy))
    pores = _f32(_line(np.sin(d1 / 4.9 + d2 / 7.1), 0.095)
                   * _line(np.cos(d3 / 5.3 - d2 / 8.2), 0.095)
                   * (compressed + rebound))
    slots = _f32(_line(np.sin((gx * y - gy * x) / 17.0), 0.12)
                   * gradient * (compressed + rebound))
    chips = _f32(saw * _line(np.cos((x - 1.2 * y) / 9.1), 0.11))
    sutures = _f32(keels * plate_boundary)
    masks = dict(compressed_scutes_a=compressed, rebound_scutes_b=rebound,
                 keel_network=keels, saw_tip_edges=saw,
                 base_membranes=membrane, osteon_pores=pores,
                 ligament_slots=slots, abrasion_chips=chips,
                 collision_sutures=sutures)
    banks = dict(compressed_scutes_a="A", rebound_scutes_b="B",
                 keel_network="B", saw_tip_edges="B", base_membranes="A",
                 osteon_pores="N", ligament_slots="N", abrasion_chips="B",
                 collision_sutures="A")
    return _pack(masks, banks, _norm(pressure + 0.17 * gradient))


def _build_fc_mossy_stone_w13() -> _Grammar:
    """Irregular basalt slabs grow moss only from a finite propagating fault set."""
    names = ("basalt_slabs_a", "wet_slabs_b", "contraction_faults",
             "beveled_edges", "moisture_tributaries", "foliose_lichen",
             "soredia_cups", "quartz_needles", "chipped_corners")
    masks = _new_marks(*names)
    faults = (((-20, 38), (118, -16), (286, 174), (532, 88)),
              ((-22, 146), (176, 318), (348, 18), (534, 192)),
              ((-20, 302), (116, 186), (398, 472), (534, 338)),
              ((-22, 454), (154, 548), (336, 304), (532, 468)),
              ((34, -20), (-12, 158), (304, 286), (154, 532)),
              ((176, -22), (428, 96), (96, 394), (352, 534)),
              ((472, -20), (326, 146), (544, 342), (426, 534)),
              ((532, 52), (394, 138), (122, 374), (-20, 492)),
              ((526, 488), (332, 552), (206, 24), (8, -18)),
              ((-18, 226), (124, 18), (402, 494), (530, 256)),
              ((104, 532), (48, 306), (470, 164), (512, -18)),
              ((-18, 506), (172, 362), (264, 64), (532, 22)))
    fault_mask = np.zeros((_WORK, _WORK), np.float32)
    wet_mask = np.zeros_like(fault_mask)
    child_index = 0
    fault_controls = list(faults)
    for extra in range(1, 13):
        a = 8.0 + _halton(extra, 2) * 496.0
        b = 8.0 + _halton(extra, 3) * 496.0
        c = 8.0 + _halton(extra, 5) * 496.0
        d = 8.0 + _halton(extra, 7) * 496.0
        if extra % 4 == 0:
            fault_controls.append(((-18, a), (b, c), (d, 512 - b), (530, c)))
        elif extra % 4 == 1:
            fault_controls.append(((a, -18), (c, b), (512 - d, c), (b, 530)))
        elif extra % 4 == 2:
            fault_controls.append(((530, a), (512 - b, d), (c, b), (-18, 512 - c)))
        else:
            fault_controls.append(((a, 530), (d, 512 - b), (b, c), (512 - a, -18)))
    for index, control in enumerate(fault_controls):
        points = _w13_bezier(control, 221)
        poly = np.rint(points).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(fault_mask, [poly], False, 1.0,
                      2 if index % 5 == 0 else 1, cv2.LINE_AA)
        if index % 3 == 0:
            cv2.polylines(wet_mask, [poly], False, 1.0, 3, cv2.LINE_AA)
        for idx in range(11 + index % 5, 214, 17 + index % 4):
            point = points[idx]
            tangent = points[idx + 4] - points[idx - 4]
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            side = -1.0 if (index + child_index) & 1 else 1.0
            reach = 6.0 + (child_index * 7) % 12
            tip = point + normal * side * reach + tangent * (
                2.0 * np.sin(child_index * 0.71))
            _draw_line(masks["moisture_tributaries"], point, tip, 1.0, 1)
            if index % 3 == 0:
                centre = point + normal * side * (3.0 + child_index % 4)
                polygon = [centre - tangent * (3.0 + child_index % 3),
                           centre + tangent * 4.0 - normal * 1.5,
                           centre + tangent * 2.0 + normal * 3.0,
                           centre - tangent * 1.0 + normal * 2.5]
                _draw_poly(masks["foliose_lichen"], polygon, 0.88, 1, True)
                cv2.circle(masks["soredia_cups"],
                           tuple(np.rint(centre).astype(int)),
                           1 + child_index % 2, 1.0, 1, cv2.LINE_AA)
            if child_index % 5 == 0:
                _draw_line(masks["quartz_needles"], point - tangent * 2.0,
                           point + normal * side * 5.0 + tangent * 2.0,
                           1.0, 1)
            if child_index % 7 == 0:
                _draw_line(masks["chipped_corners"], point - normal * 2.0,
                           point + tangent * 3.0 + normal * 2.0, 1.0, 1)
            child_index += 1
    faults_binary = cv2.dilate(fault_mask, np.ones((3, 3), np.uint8))
    open_stone = (faults_binary < 0.08).astype(np.uint8)
    _count, labels = cv2.connectedComponents(open_stone, 8)
    # Connected fault-bounded slabs get physical wet/dry ownership; labels
    # are causal components, never equal-population rank bins.
    slab_a = ((labels % 3) != 1).astype(np.float32) * open_stone
    slab_b = ((labels % 3) == 1).astype(np.float32) * open_stone
    wet_halo = _f32(cv2.GaussianBlur(np.maximum(wet_mask,
                                                masks["moisture_tributaries"]),
                                     (0, 0), 5.2) * 2.5)
    masks["basalt_slabs_a"] = _f32(0.28 * open_stone + 0.62 * slab_a)
    masks["wet_slabs_b"] = _f32(0.21 * open_stone + 0.66 * slab_b
                                 + 0.44 * wet_halo)
    masks["contraction_faults"] = fault_mask
    masks["beveled_edges"] = _f32(cv2.dilate(fault_mask,
                                              np.ones((5, 5), np.uint8))
                                   - 0.72 * fault_mask)
    banks = dict(basalt_slabs_a="A", wet_slabs_b="B",
                 contraction_faults="N", beveled_edges="B",
                 moisture_tributaries="B", foliose_lichen="B",
                 soredia_cups="A", quartz_needles="A", chipped_corners="N")
    distance = cv2.distanceTransform(open_stone, cv2.DIST_L2, 3)
    return _pack(masks, banks, _norm(distance + labels.astype(np.float32) * 0.17))


def _build_fc_batwing_w14() -> _Grammar:
    """Three off-canvas wrists sweep cropped bones through layered membrane."""
    names = ("membrane_lamellae_a", "membrane_lamellae_b", "finger_bones",
             "hooked_joints", "capillary_forks", "tension_striae",
             "echo_scratches", "trailing_tears", "dew_notches")
    masks = _new_marks(*names)
    skeleton = np.zeros((_WORK, _WORK), np.float32)
    fans = ((np.asarray([-92.0, 238.0]), -0.54, 1.0),
            (np.asarray([318.0, -104.0]), 1.17, -1.0),
            (np.asarray([618.0, 474.0]), -2.63, 1.0))
    joint_index = 0
    for fan_index, (hub, heading, bend_sign) in enumerate(fans):
        for finger in range(7 + fan_index):
            angle = heading + (finger - (3.0 + fan_index * 0.5)) * (
                0.105 + fan_index * 0.012)
            direction = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            normal = np.asarray([-direction[1], direction[0]], np.float32)
            length = 520.0 + finger * 17.0 + fan_index * 23.0
            p0 = hub
            p1 = hub + direction * length * 0.28 + normal * bend_sign * (
                34.0 + finger * 5.0)
            p2 = hub + direction * length * 0.69 - normal * bend_sign * (
                24.0 + (finger * 11) % 39)
            p3 = hub + direction * length
            points = _w13_bezier((p0, p1, p2, p3), 211)
            poly = np.rint(points).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(masks["finger_bones"], [poly], False, 1.0,
                          3 if finger % 4 == 0 else 2, cv2.LINE_AA)
            cv2.polylines(skeleton, [poly], False, 1.0, 2, cv2.LINE_AA)
            for idx in range(26 + finger % 7, 202, 31 + fan_index * 3):
                point = points[idx]
                if not (0 <= point[0] < 512 and 0 <= point[1] < 512):
                    continue
                tangent = points[idx + 3] - points[idx - 3]
                tangent /= max(0.25, float(np.linalg.norm(tangent)))
                local_normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                cv2.circle(masks["hooked_joints"],
                           tuple(np.rint(point).astype(int)),
                           2 + joint_index % 2, 1.0, 1, cv2.LINE_AA)
                side = -1.0 if (joint_index + finger) & 1 else 1.0
                fork = point + local_normal * side * (8.0 + joint_index % 9)
                _draw_line(masks["capillary_forks"], point, fork, 1.0, 1)
                _draw_line(masks["capillary_forks"], fork,
                           fork + local_normal * side * 5.0 + tangent * 4.0,
                           1.0, 1)
                _draw_line(masks["capillary_forks"], fork,
                           fork + local_normal * side * 4.0 - tangent * 5.0,
                           1.0, 1)
                _draw_line(masks["tension_striae"], point - tangent * 4.0,
                           point + tangent * 4.0, 1.0, 1)
                if joint_index % 4 == 0:
                    _draw_line(masks["trailing_tears"], fork,
                               fork + tangent * 5.0 + local_normal * side * 3.0,
                               1.0, 1)
                if joint_index % 5 == 0:
                    cv2.circle(masks["dew_notches"],
                               tuple(np.rint(fork).astype(int)), 1, 1.0, -1,
                               cv2.LINE_AA)
                joint_index += 1
    distance = cv2.distanceTransform((skeleton < 0.08).astype(np.uint8),
                                     cv2.DIST_L2, 3)
    phase = np.mod(distance / 6.4 + 0.08 * np.sin((_xy()[0] + _xy()[1]) / 67.0),
                   1.0)
    envelope = _f32((31.0 - distance) / 15.0)
    masks["membrane_lamellae_a"] = _f32(
        (1.0 - np.abs(phase - 0.23) / 0.21) * envelope)
    masks["membrane_lamellae_b"] = _f32(
        (1.0 - np.abs(phase - 0.72) / 0.21) * envelope)
    masks["echo_scratches"] = _f32(
        _line(np.sin((_xy()[0] - 1.6 * _xy()[1]) / 14.0 + distance / 8.0),
              0.10) * envelope)
    banks = dict(membrane_lamellae_a="A", membrane_lamellae_b="B",
                 finger_bones="B", hooked_joints="A", capillary_forks="B",
                 tension_striae="A", echo_scratches="N",
                 trailing_tears="N", dew_notches="B")
    return _pack(masks, banks, _norm(distance + skeleton * 6.0))


def _build_fc_hide_scale_glass_w14() -> _Grammar:
    """Edge-fed refractive currents weave dense lenses without one convergence."""
    names = ("lens_bodies_a", "lens_bodies_b", "rim_bevels",
             "focal_caustics", "stress_veins", "micropore_pairs",
             "scuff_arcs", "occlusion_lips", "collision_prisms")
    masks = _new_marks(*names)
    obstacles = ((96.0, 118.0, 0.72), (402.0, 86.0, -0.61),
                 (226.0, 286.0, 0.83), (446.0, 352.0, -0.76),
                 (92.0, 438.0, 0.57), (332.0, 486.0, -0.68))
    base_velocities = ((1.0, 0.08), (0.12, 1.0), (-1.0, -0.11),
                       (-0.09, -1.0))
    lens_index = 0
    for stream in range(96):
        entry = stream % 4
        along = 5.0 + _halton(stream + 1, (2, 3, 5, 7)[entry]) * 502.0
        if entry == 0:
            point = np.asarray([-8.0, along], np.float32)
        elif entry == 1:
            point = np.asarray([along, -8.0], np.float32)
        elif entry == 2:
            point = np.asarray([520.0, along], np.float32)
        else:
            point = np.asarray([along, 520.0], np.float32)
        for step in range(176):
            velocity = np.asarray(base_velocities[entry], np.float32)
            velocity += np.asarray([
                0.22 * np.sin(point[1] / (41.0 + stream % 7)
                              + stream * 0.37),
                0.24 * np.cos(point[0] / (47.0 + stream % 5)
                              - stream * 0.29)], np.float32)
            for cx, cy, spin in obstacles:
                delta = point - np.asarray([cx, cy], np.float32)
                d2 = float(np.dot(delta, delta) + 420.0)
                velocity += spin * 28.0 / d2 * np.asarray(
                    [-delta[1], delta[0]], np.float32)
            velocity /= max(0.25, float(np.linalg.norm(velocity)))
            point = point + velocity * 3.4
            if not (-10 <= point[0] < 522 and -10 <= point[1] < 522):
                if step > 9:
                    break
                continue
            if step % (4 + stream % 3) != 0:
                continue
            normal = np.asarray([-velocity[1], velocity[0]], np.float32)
            major = 3.0 + (lens_index * 7 + stream) % 5
            minor = 2.0 + (lens_index * 5 + step) % 3
            centre = point.copy()
            polygon = [centre - velocity * major,
                       centre - normal * minor + velocity,
                       centre + velocity * major,
                       centre + normal * minor - velocity]
            body = "lens_bodies_a" if (stream + lens_index) % 5 in (0, 1, 4) else "lens_bodies_b"
            _draw_poly(masks[body], polygon,
                       0.74 + 0.06 * (lens_index % 4), 1, True)
            _draw_poly(masks["rim_bevels"], polygon, 1.0, 1, False)
            _draw_line(masks["focal_caustics"], centre - velocity * (major - 1),
                       centre + velocity * (major - 1), 1.0, 1)
            _draw_line(masks["stress_veins"], centre - normal * minor,
                       centre + normal * minor, 1.0, 1)
            for side in (-1.0, 1.0):
                pore = centre + normal * side * max(1.0, minor - 1.0)
                cv2.circle(masks["micropore_pairs"],
                           tuple(np.rint(pore).astype(int)), 1, 1.0, 1,
                           cv2.LINE_AA)
            if lens_index % 11 == 0:
                cv2.ellipse(masks["scuff_arcs"],
                            tuple(np.rint(centre).astype(int)),
                            (int(major + 2), int(minor + 2)),
                            float(np.degrees(np.arctan2(velocity[1], velocity[0]))),
                            190, 330, 1.0, 1, cv2.LINE_AA)
            _draw_line(masks["occlusion_lips"], polygon[2], polygon[3], 1.0, 1)
            if lens_index % 17 == 0:
                _draw_line(masks["collision_prisms"], centre - velocity * 2.0,
                           centre + normal * 3.0, 1.0, 1)
                _draw_line(masks["collision_prisms"], centre + velocity * 2.0,
                           centre - normal * 3.0, 1.0, 1)
            lens_index += 1
    x, y = _xy()
    potential = (0.002 * x - 0.0017 * y
                 + 0.31 * np.sin(y / 67.0)
                 - 0.27 * np.cos(x / 73.0)
                 + 0.19 * np.sin((x - y) / 91.0))
    banks = dict(lens_bodies_a="A", lens_bodies_b="B", rim_bevels="B",
                 focal_caustics="B", stress_veins="N", micropore_pairs="A",
                 scuff_arcs="A", occlusion_lips="N", collision_prisms="B")
    return _pack(masks, banks, _norm(potential))


def _build_fc_gator_hide_w14() -> _Grammar:
    """A continuous osteoderm relief replaces repeated armored tracks."""
    names = ("crown_relief_a", "saddle_relief_b", "raised_keels",
             "growth_annuli", "sensory_pits", "seam_canals",
             "interlocking_teeth", "scar_slashes", "deep_grooves")
    x, y = _xy()
    # Three anisotropic dermal loads buckle one sheet.  Their absolute folded
    # envelope makes craggy osteoderm mountains without cells, rows or paves.
    f1 = np.sin((x + 0.28 * y) / 15.7 + 0.63 * np.sin(y / 67.0))
    f2 = np.sin((y - 0.41 * x) / 20.9 - 0.54 * np.cos(x / 79.0))
    f3 = np.cos((1.23 * x + 0.77 * y) / 29.3
                + 0.37 * np.sin((x - y) / 91.0))
    relief = np.abs(0.54 * f1 + 0.37 * f2 + 0.29 * f3
                    + 0.24 * f1 * f2 - 0.18 * f2 * f3)
    crown = _f32((relief - 0.67) / 0.29)
    saddle = _f32((0.43 - relief) / 0.32)
    keels = np.maximum(_line(relief - 0.72, 0.050),
                       _line(relief - 0.89, 0.042))
    annuli = np.maximum(_line(relief - 0.56, 0.037),
                        _line(relief - 0.78, 0.034))
    gx = cv2.Sobel(relief.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(relief.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gx, gy))
    local_max = ((relief >= cv2.dilate(relief.astype(np.float32),
                                       np.ones((5, 5), np.uint8)))
                 .astype(np.float32) * _f32((relief - 0.67) / 0.27))
    pits = cv2.dilate(local_max, np.ones((3, 3), np.uint8))
    canals = _f32(_line(f1 - f2, 0.075) * gradient)
    teeth = _f32(keels * _line(np.sin((x + 1.6 * y) / 5.9), 0.13))
    scars = _f32(_line(np.sin((1.7 * x - 0.6 * y) / 13.1 + relief * 2.3),
                       0.085) * saddle)
    grooves = _f32(_line(relief - 0.34, 0.040)
                   + _line(relief - 0.96, 0.034))
    masks = dict(crown_relief_a=crown, saddle_relief_b=saddle,
                 raised_keels=keels, growth_annuli=annuli,
                 sensory_pits=pits, seam_canals=canals,
                 interlocking_teeth=teeth, scar_slashes=scars,
                 deep_grooves=grooves)
    banks = dict(crown_relief_a="A", saddle_relief_b="B",
                 raised_keels="B", growth_annuli="A", sensory_pits="B",
                 seam_canals="N", interlocking_teeth="B", scar_slashes="N",
                 deep_grooves="A")
    return _pack(masks, banks, _norm(relief + 0.16 * gradient))


def _build_fc_quill_bristle_w15() -> _Grammar:
    """A full defensive mantle orients every quill by one continuous stress tensor."""
    names = ("root_dermis_a", "lee_dermis_b", "root_bulbs",
             "collar_rings", "rigid_shafts", "hollow_slits",
             "alternating_barbs", "tapered_tips", "strain_crosscuts")
    masks = _new_marks(*names)
    x, y = _xy()
    # Low-discrepancy chronology prevents rows but never renders as noise:
    # every point is a literal quill with causal anatomy, and its angle comes
    # from the same smoothly varying defensive stress tensor.
    root_field = np.zeros((_WORK, _WORK), np.float32)
    lee_field = np.zeros_like(root_field)
    for index in range(1, 1851):
        root = np.asarray([4.0 + _halton(index, 2) * 504.0,
                           4.0 + _halton(index, 3) * 504.0], np.float32)
        rx, ry = float(root[0]), float(root[1])
        angle = (0.83 * np.sin(rx / 71.0) - 0.69 * np.cos(ry / 83.0)
                 + 0.41 * np.sin((rx - ry) / 109.0)
                 + 0.22 * np.cos((rx + 1.3 * ry) / 57.0))
        lean = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-lean[1], lean[0]], np.float32)
        length = 3.5 + (index * 11) % 7
        tip = root + lean * length
        cv2.circle(masks["root_bulbs"], tuple(np.rint(root).astype(int)),
                   1 + index % 2, 1.0, -1, cv2.LINE_AA)
        cv2.circle(masks["collar_rings"], tuple(np.rint(root).astype(int)),
                   2 + index % 2, 1.0, 1, cv2.LINE_AA)
        _draw_line(masks["rigid_shafts"], root, tip, 1.0, 1)
        _draw_line(masks["hollow_slits"], root + lean * 1.3,
                   tip - lean * 1.0, 1.0, 1)
        for fraction in (0.41, 0.68):
            anchor = root + lean * length * fraction
            side = -1.0 if (index + int(fraction * 10)) & 1 else 1.0
            _draw_line(masks["alternating_barbs"], anchor,
                       anchor - lean * 1.2 + normal * side * 1.8, 1.0, 1)
        _draw_line(masks["tapered_tips"], tip - normal * 1.3,
                   tip + normal * 1.3 - lean, 1.0, 1)
        if index % 9 == 0:
            _draw_line(masks["strain_crosscuts"], root - normal * 2.8,
                       root + normal * 2.8, 1.0, 1)
        cv2.circle(root_field, tuple(np.rint(root).astype(int)),
                   2 + index % 2, 1.0, -1, cv2.LINE_AA)
        _draw_line(lee_field, root - normal * 2.2, tip - normal * 2.2,
                   1.0, 1)
    masks["root_dermis_a"] = _f32(cv2.GaussianBlur(root_field, (0, 0), 2.0) * 1.9)
    masks["lee_dermis_b"] = _f32(cv2.GaussianBlur(lee_field, (0, 0), 2.7) * 2.1)
    tone = _norm(np.sin(x / 71.0) - np.cos(y / 83.0)
                 + 0.44 * np.sin((x - y) / 109.0))
    banks = dict(root_dermis_a="A", lee_dermis_b="B", root_bulbs="B",
                 collar_rings="A", rigid_shafts="A", hollow_slits="N",
                 alternating_barbs="B", tapered_tips="B",
                 strain_crosscuts="N")
    return _pack(masks, banks, tone)


def _build_fc_claw_rake_w15() -> _Grammar:
    """Thirty noncongruent pressure-fracture strike bundles cover the plane."""
    names = ("impact_rebound_a", "impact_bruises_b", "recessed_gouges",
             "displaced_lips", "terminal_punctures", "stress_crescents",
             "crushed_chips", "debris_tails", "older_crosscuts")
    masks = _new_marks(*names)
    rebound = np.zeros((_WORK, _WORK), np.float32)
    bruise = np.zeros_like(rebound)
    for strike in range(1, 73):
        centre = np.asarray([8.0 + _halton(strike, 2) * 496.0,
                             8.0 + _halton(strike, 3) * 496.0], np.float32)
        angle = (1.17 * np.sin(centre[0] / 83.0)
                 + 0.91 * np.cos(centre[1] / 71.0)
                 + 0.37 * np.sin((centre[0] + centre[1]) / 113.0)
                 + strike * 0.071)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        teeth = 2 + (strike * 5) % 6
        spread = 1.8 + (strike * 7) % 5
        for tooth in range(teeth):
            root = centre + normal * (tooth - (teeth - 1) * 0.5) * spread
            direction = tangent + normal * (0.18 * np.sin(strike + tooth * 1.9))
            direction /= max(0.25, float(np.linalg.norm(direction)))
            length = 4.0 + (strike * 11 + tooth * 7) % 8
            elbow = root + direction * length * 0.56 + normal * (
                1.4 * np.sin(strike * 0.63 + tooth))
            tip = root + direction * length
            _draw_line(masks["recessed_gouges"], root, elbow, 1.0,
                       2 if (strike + tooth) % 7 == 0 else 1)
            _draw_line(masks["recessed_gouges"], elbow, tip, 1.0, 1)
            lip_normal = np.asarray([-direction[1], direction[0]], np.float32)
            _draw_line(masks["displaced_lips"], root + lip_normal * 1.6,
                       tip + lip_normal * 1.2, 1.0, 1)
            cv2.circle(masks["terminal_punctures"],
                       tuple(np.rint(tip).astype(int)), 1 + tooth % 2,
                       1.0, 1, cv2.LINE_AA)
            if (strike + tooth) % 3 == 0:
                cv2.ellipse(masks["stress_crescents"],
                            tuple(np.rint(tip - direction * 2.0).astype(int)),
                            (3 + strike % 3, 2 + tooth % 2),
                            float(np.degrees(np.arctan2(direction[1], direction[0]))),
                            188, 342, 1.0, 1, cv2.LINE_AA)
            if (strike + 2 * tooth) % 4 == 0:
                chip = tip + direction * 2.0 + lip_normal * (
                    -1.8 if tooth & 1 else 1.8)
                cv2.circle(masks["crushed_chips"],
                           tuple(np.rint(chip).astype(int)), 1, 1.0, -1,
                           cv2.LINE_AA)
        end = centre + tangent * (7.0 + strike % 5)
        _draw_line(masks["debris_tails"], end,
                   end + tangent * (5.0 + strike % 7)
                   + normal * (strike % 5 - 2), 1.0, 1)
        if strike % 6 == 0:
            _draw_line(masks["older_crosscuts"], centre - normal * 7.0,
                       centre + normal * 7.0 + tangent * 3.0, 1.0, 1)
        cv2.circle(bruise, tuple(np.rint(centre).astype(int)),
                   4 + strike % 4, 1.0, -1, cv2.LINE_AA)
        cv2.circle(rebound, tuple(np.rint(centre - normal * 3.0).astype(int)),
                   6 + strike % 5, 1.0, 1, cv2.LINE_AA)
    masks["impact_bruises_b"] = _f32(cv2.GaussianBlur(bruise, (0, 0), 2.3) * 2.8)
    masks["impact_rebound_a"] = _f32(cv2.GaussianBlur(rebound, (0, 0), 3.8) * 2.3
                                      - 0.27 * masks["impact_bruises_b"])
    banks = dict(impact_rebound_a="A", impact_bruises_b="B",
                 recessed_gouges="B", displaced_lips="A",
                 terminal_punctures="N", stress_crescents="B",
                 crushed_chips="A", debris_tails="N", older_crosscuts="A")
    x, y = _xy()
    return _pack(masks, banks, _norm(0.16 * x - 0.12 * y + bruise * 4.0))


def _build_fc_dorsal_ridge_w15() -> _Grammar:
    """Deformed Chladni nodes become a connected full-canvas osteoderm sawline."""
    names = ("compression_plates_a", "rebound_plates_b", "nodal_keels",
             "saw_tip_teeth", "base_membranes", "osteon_pores",
             "ligament_slots", "abrasion_chips", "collision_sutures")
    x, y = _xy()
    px = (x - 256.0) / 512.0 * np.pi * 2.0
    py = (y - 256.0) / 512.0 * np.pi * 2.0
    u = px + 0.39 * np.sin(1.7 * py) + 0.17 * np.sin(px - py)
    v = py - 0.31 * np.sin(1.3 * px) + 0.14 * np.cos(px + 0.7 * py)
    field = (np.sin(5.0 * u) * np.sin(8.0 * v)
             - np.sin(8.0 * u) * np.sin(5.0 * v)
             + 0.34 * (np.sin(3.0 * u) * np.sin(11.0 * v)
                       - np.sin(11.0 * u) * np.sin(3.0 * v)))
    compression = _f32((field - 0.15) / 0.72)
    rebound = _f32((-field - 0.13) / 0.70)
    keels = _line(field, 0.075)
    membrane = _f32(cv2.GaussianBlur(keels, (0, 0), 3.0) * 2.2
                    - 0.36 * keels)
    # A triangular traveling phase chops each continuous nodal keel into
    # locally alternating saw faces without changing its global connectivity.
    tooth_phase = np.mod((1.31 * x + 0.73 * y) / 7.0
                         + 0.44 * np.sin((x - y) / 43.0), 1.0)
    teeth = _f32(keels * (1.0 - np.abs(tooth_phase - 0.5) / 0.18))
    gx = cv2.Sobel(field.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(field.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gx, gy))
    pores = _f32(keels
                 * _line(np.sin(2.2 * x / 7.0 + 1.7 * y / 9.0), 0.10)
                 * _line(np.cos(1.3 * x / 11.0 - 2.1 * y / 8.0), 0.10))
    slots = _f32(keels * _line(np.sin((gx * y - gy * x) / 15.0), 0.12))
    chips = _f32(teeth * _line(np.cos((x + 1.6 * y) / 9.0), 0.11))
    sutures = _f32(keels * _f32((gradient - 0.43) / 0.45))
    masks = dict(compression_plates_a=compression, rebound_plates_b=rebound,
                 nodal_keels=keels, saw_tip_teeth=teeth,
                 base_membranes=membrane, osteon_pores=pores,
                 ligament_slots=slots, abrasion_chips=chips,
                 collision_sutures=sutures)
    banks = dict(compression_plates_a="A", rebound_plates_b="B",
                 nodal_keels="B", saw_tip_teeth="B", base_membranes="A",
                 osteon_pores="N", ligament_slots="N", abrasion_chips="B",
                 collision_sutures="A")
    return _pack(masks, banks, _norm(field + 0.18 * gradient))


def _build_fc_gator_hide_w15() -> _Grammar:
    """A warped gyroid slice forms one continuous craggy osteoderm labyrinth."""
    names = ("crown_ridges_a", "saddle_ridges_b", "zero_keels",
             "growth_annuli", "sensory_pits", "seam_canals",
             "interlocking_teeth", "scar_slashes", "deep_grooves")
    x, y = _xy()
    u = x / 15.7 + 0.62 * np.sin(y / 61.0) + 0.18 * np.sin((x-y) / 37.0)
    v = y / 18.9 - 0.55 * np.cos(x / 73.0) + 0.21 * np.cos((x+y) / 49.0)
    w = (0.71 * x - 1.13 * y) / 24.3 + 0.43 * np.sin(x / 83.0)
    gyroid = (np.sin(u) * np.cos(v) + np.sin(v) * np.cos(w)
              + np.sin(w) * np.cos(u))
    crown = _f32((gyroid - 0.18) / 0.92)
    saddle = _f32((-gyroid - 0.16) / 0.90)
    keels = _line(gyroid, 0.095)
    annuli = np.maximum(_line(gyroid - 0.48, 0.060),
                        _line(gyroid + 0.53, 0.058))
    local_max = ((gyroid >= cv2.dilate(gyroid.astype(np.float32),
                                       np.ones((5, 5), np.uint8)))
                 .astype(np.float32) * _f32((gyroid - 0.35) / 0.75))
    pits = cv2.dilate(local_max, np.ones((3, 3), np.uint8))
    gx = cv2.Sobel(gyroid.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gyroid.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gx, gy))
    canals = _f32(keels * _f32((gradient - 0.31) / 0.55))
    teeth = _f32(keels * _line(np.sin((1.7 * x + 0.9 * y) / 5.3), 0.13))
    scars = _f32(_line(np.sin((1.4 * x - 0.8 * y) / 11.7 + gyroid), 0.09)
                 * (crown + saddle))
    grooves = np.maximum(_line(gyroid - 0.91, 0.050),
                          _line(gyroid + 0.87, 0.052))
    masks = dict(crown_ridges_a=crown, saddle_ridges_b=saddle,
                 zero_keels=keels, growth_annuli=annuli,
                 sensory_pits=pits, seam_canals=canals,
                 interlocking_teeth=teeth, scar_slashes=scars,
                 deep_grooves=grooves)
    banks = dict(crown_ridges_a="A", saddle_ridges_b="B", zero_keels="B",
                 growth_annuli="A", sensory_pits="B", seam_canals="N",
                 interlocking_teeth="B", scar_slashes="N", deep_grooves="A")
    return _pack(masks, banks, _norm(gyroid + 0.16 * gradient))


def _build_fc_hide_scale_glass_w15() -> _Grammar:
    """A deterministic Clifford attractor carries one nonrepeating lens shoal."""
    names = ("lens_bodies_a", "lens_bodies_b", "rim_bevels",
             "focal_caustics", "stress_veins", "micropore_pairs",
             "scuff_arcs", "occlusion_lips", "collision_prisms")
    masks = _new_marks(*names)
    count = 92000
    xs = np.empty(count, np.float32)
    ys = np.empty(count, np.float32)
    ax, ay = np.float32(0.11), np.float32(-0.17)
    a, b, c, d = -1.73, 1.82, 0.94, 1.21
    for index in range(count + 180):
        nx = np.sin(a * ay) + c * np.cos(a * ax)
        ny = np.sin(b * ax) + d * np.cos(b * ay)
        ax, ay = np.float32(nx), np.float32(ny)
        if index >= 180:
            xs[index - 180] = ax
            ys[index - 180] = ay
    # Fixed affine crop spreads the one connected strange attractor through
    # the canvas.  No random jitter, tile, path family or carrier is added.
    px = 5.0 + _norm(xs) * 502.0
    py = 5.0 + _norm(ys) * 502.0
    lens_index = 0
    for index in range(8, count - 8, 19):
        centre = np.asarray([px[index], py[index]], np.float32)
        tangent = np.asarray([px[index + 3] - px[index - 3],
                              py[index + 3] - py[index - 3]], np.float32)
        tangent /= max(0.25, float(np.linalg.norm(tangent)))
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        curvature = float((px[index + 6] - 2 * px[index] + px[index - 6])
                          * normal[0]
                          + (py[index + 6] - 2 * py[index] + py[index - 6])
                          * normal[1])
        major = 2.5 + (lens_index * 7) % 5
        minor = 1.8 + (lens_index * 11) % 3
        polygon = [centre - tangent * major,
                   centre - normal * minor + tangent,
                   centre + tangent * major,
                   centre + normal * minor - tangent]
        body = "lens_bodies_a" if curvature >= 0.0 else "lens_bodies_b"
        _draw_poly(masks[body], polygon,
                   0.74 + 0.06 * (lens_index % 4), 1, True)
        _draw_poly(masks["rim_bevels"], polygon, 1.0, 1, False)
        _draw_line(masks["focal_caustics"], centre - tangent * (major - 0.8),
                   centre + tangent * (major - 0.8), 1.0, 1)
        _draw_line(masks["stress_veins"], centre - normal * minor,
                   centre + normal * minor, 1.0, 1)
        for side in (-1.0, 1.0):
            pore = centre + normal * side * max(1.0, minor - 0.7)
            cv2.circle(masks["micropore_pairs"],
                       tuple(np.rint(pore).astype(int)), 1, 1.0, 1,
                       cv2.LINE_AA)
        if lens_index % 11 == 0:
            cv2.ellipse(masks["scuff_arcs"], tuple(np.rint(centre).astype(int)),
                        (int(major + 2), int(minor + 2)),
                        float(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                        190, 330, 1.0, 1, cv2.LINE_AA)
        _draw_line(masks["occlusion_lips"], polygon[2], polygon[3], 1.0, 1)
        if lens_index % 17 == 0:
            _draw_line(masks["collision_prisms"], centre - tangent * 2.0,
                       centre + normal * 3.0, 1.0, 1)
            _draw_line(masks["collision_prisms"], centre + tangent * 2.0,
                       centre - normal * 3.0, 1.0, 1)
        lens_index += 1
    # Visit chronology is the physical polish age, not a random texture.
    age = np.zeros((_WORK, _WORK), np.float32)
    ix = np.clip(np.rint(px).astype(np.int32), 0, 511)
    iy = np.clip(np.rint(py).astype(np.int32), 0, 511)
    np.maximum.at(age, (iy, ix), np.linspace(0.0, 1.0, count,
                                            dtype=np.float32))
    age = cv2.GaussianBlur(age, (0, 0), 1.1)
    banks = dict(lens_bodies_a="A", lens_bodies_b="B", rim_bevels="B",
                 focal_caustics="B", stress_veins="N", micropore_pairs="A",
                 scuff_arcs="A", occlusion_lips="N", collision_prisms="B")
    return _pack(masks, banks, _norm(age))


def _build_fc_crackle_eyeshine_glass_w15() -> _Grammar:
    """An asymmetric Phoenix basin forms global tapetal cracks without tiles or hubs."""
    names = ("escaped_faces_a", "retained_faces_b", "tapetal_cracks",
             "pupil_shears", "iris_relays", "cusp_caustics",
             "bevel_splinters", "relay_bridges", "glint_chips")
    x, y = _xy()
    # The crop intentionally excludes the Phoenix set's symmetric body.  Only
    # one asymmetric boundary coast crosses the canvas, so no radial centre,
    # repeated basin, tile or random perturbation can appear.
    z = ((-1.92 + x / 511.0 * 2.74)
         + 1j * (-1.34 + y / 511.0 * 2.91)).astype(np.complex64)
    previous = np.zeros_like(z)
    c = np.complex64(-0.48 + 0.63j)
    p = np.complex64(-0.36 + 0.04j)
    escape = np.zeros((_WORK, _WORK), np.float32)
    active = np.ones((_WORK, _WORK), bool)
    for step in range(1, 29):
        next_z = z * z + c + p * previous
        previous, z = z, next_z
        newly = active & (np.abs(z) > 5.0)
        escape[newly] = float(step)
        active &= ~newly
        # Bounded values preserve derivatives after escape; there is no
        # stochastic orbit reset.
        mag = np.abs(z)
        z = np.where(mag > 8.0, z / np.maximum(mag, 1.0) * 8.0, z)
    escape[active] = 29.0
    e = _norm(escape)
    phase = np.angle(z).astype(np.float32)
    gx = cv2.Sobel(e, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(e, cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gx, gy))
    faces_a = _f32((0.72 - e) / 0.55) * (1.0 - 0.58 * gradient)
    faces_b = _f32((e - 0.28) / 0.56) * (1.0 - 0.58 * gradient)
    cracks = _f32((gradient - 0.18) / 0.55)
    pupil = _f32(_line(np.sin(phase * 3.7 + e * 8.0), 0.13)
                 * (1.0 - cracks))
    iris = _f32(_line(np.sin(e * 27.0 + phase * 1.8), 0.14))
    caustic = _f32(_line(np.cos(phase * 2.9 - e * 13.0) - 0.16, 0.085)
                    * (1.0 - 0.62 * cracks))
    bevel = _f32(cv2.dilate(cracks, np.ones((5, 5), np.uint8))
                  - 0.56 * cracks)
    relay = _f32(cracks * _line(np.sin((x + 0.73 * y) / 9.7 + phase),
                                 0.11))
    glint = _f32(_line(np.sin(e * 41.0 + phase * 5.0), 0.075)
                  * _line(np.cos(e * 23.0 - phase * 7.0), 0.075))
    masks = dict(escaped_faces_a=faces_a, retained_faces_b=faces_b,
                 tapetal_cracks=cracks, pupil_shears=pupil,
                 iris_relays=iris, cusp_caustics=caustic,
                 bevel_splinters=bevel, relay_bridges=relay,
                 glint_chips=glint)
    banks = dict(escaped_faces_a="A", retained_faces_b="B",
                 tapetal_cracks="N", pupil_shears="N", iris_relays="A",
                 cusp_caustics="B", bevel_splinters="B",
                 relay_bridges="N", glint_chips="A")
    return _pack(masks, banks, _norm(e + 0.23 * phase + 0.17 * gradient))


# ---------------------------------------------------------------------------
# W16 owner-eye topology rebuild.
#
# SPB-WILDS WR-16, 2026-08-24.  Owner verdict: "LAZY" / "exact same
# pattern just recolored".  The W15 contact board was mechanically clean but
# visually failed 0 KEEP / 2 REPAIR / 18 REBUILD: mathematical labels did not
# rescue pavers, macro contours, repeated icons, hubs, lanes or sparse cards.
# These builders start from visible material mechanics.  Low-discrepancy
# chronology is used only to place literal authored features; it is never
# rendered as a noise layer.  The frozen rejection and metric movement live in
# OWNER_EYE_REJECTION_W15.md and the eventual W16 owner-eye report.


def _w16_segment(mask: np.ndarray, centre: Sequence[float], angle: float,
                 length: float, value: float = 1.0, width: int = 1,
                 bend: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Draw one short causal segment and return root/mid/tip coordinates."""
    c = np.asarray(centre, np.float32)
    tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
    normal = np.asarray([-tangent[1], tangent[0]], np.float32)
    root = c - tangent * (0.5 * length)
    tip = c + tangent * (0.5 * length)
    middle = c + normal * bend
    pts = np.rint(np.stack([root, middle, tip])).astype(np.int32)
    cv2.polylines(mask, [pts.reshape((-1, 1, 2))], False, float(value),
                  int(width), cv2.LINE_AA)
    return root, middle, tip


def _w16_disc(mask: np.ndarray, centre: Sequence[float], radius: int,
              value: float = 1.0, filled: bool = True) -> None:
    cv2.circle(mask, tuple(np.rint(centre).astype(int)), int(radius),
               float(value), -1 if filled else 1, cv2.LINE_AA)


def _build_fc_sasquatch_fur_w16() -> _Grammar:
    """Dense hooked pelage: no card-length streamline survives the repair."""
    names = ("warm_underfur_a", "cool_underfur_b", "guard_hairs",
             "hooked_kinks", "follicle_roots", "split_tips",
             "matted_crosshairs", "silvered_notches", "shed_fuzz")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 3001):
        c = np.asarray([2.0 + 508.0 * _halton(index, 2),
                        2.0 + 508.0 * _halton(index, 3)], np.float32)
        angle = (0.42 * np.sin(c[0] / 57.0) - 0.53 * np.cos(c[1] / 69.0)
                 + 0.31 * np.sin((c[0] + c[1]) / 41.0)
                 + 0.17 * np.cos((2.0 * c[0] - c[1]) / 83.0))
        length = 3.0 + (index * 13) % 7
        bend = 0.35 * ((index * 7) % 7 - 3)
        under = "warm_underfur_a" if ((index * 5) % 11) < 6 else "cool_underfur_b"
        root, middle, tip = _w16_segment(masks[under], c, angle,
                                          length + 1.0, 0.66, 2, bend)
        _w16_segment(masks["guard_hairs"], c, angle + 0.05 * np.sin(index),
                     length, 1.0, 1, bend)
        if index % 3 == 0:
            _w16_disc(masks["follicle_roots"], root, 1, 1.0, True)
        if index % 4 == 0:
            normal_angle = angle + np.pi * 0.5
            _w16_segment(masks["hooked_kinks"], middle, normal_angle,
                         2.0 + index % 3, 1.0, 1,
                         0.35 * (-1 if index & 1 else 1))
        if index % 5 == 0:
            _w16_segment(masks["split_tips"], tip, angle + 0.55, 2.6,
                         1.0, 1, 0.25)
            _w16_segment(masks["split_tips"], tip, angle - 0.48, 2.2,
                         1.0, 1, -0.25)
        if index % 7 == 0:
            _w16_segment(masks["matted_crosshairs"], c, angle + 1.35,
                         3.0 + index % 5, 1.0, 1, 0.4)
        if index % 9 == 0:
            _w16_segment(masks["silvered_notches"], middle,
                         angle + np.pi * 0.5, 2.2, 1.0, 1)
        if index % 11 == 0:
            _w16_disc(masks["shed_fuzz"], c + np.asarray([1.5, -1.0]),
                      1 + index % 2, 0.85, False)
    tone = _norm(0.33 * np.sin(x / 43.0) + 0.29 * np.cos(y / 61.0)
                 + 0.26 * np.sin((x - y) / 37.0) + 0.0017 * x)
    banks = dict(warm_underfur_a="A", cool_underfur_b="B",
                 guard_hairs="N", hooked_kinks="B", follicle_roots="A",
                 split_tips="B", matted_crosshairs="A",
                 silvered_notches="N", shed_fuzz="B")
    return _pack(masks, banks, tone)


def _build_fc_quill_bristle_w16() -> _Grammar:
    """A varied broken-quill mat; sockets no longer form repeated icons."""
    names = ("amber_quill_faces_a", "violet_quill_faces_b", "hard_spines",
             "cuticle_ticks", "offset_barbs", "split_nibs",
             "buried_roots", "crossed_needles", "broken_fragments")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 2451):
        c = np.asarray([2.0 + 508.0 * _halton(index, 2),
                        2.0 + 508.0 * _halton(index, 5)], np.float32)
        angle = (0.79 * np.sin(c[1] / 81.0) + 0.37 * np.cos(c[0] / 53.0)
                 + 0.24 * np.sin((c[0] - 1.7 * c[1]) / 47.0)
                 + ((index * 17) % 9 - 4) * 0.045)
        length = 4.0 + (index * 19) % 8
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        root = c - tangent * length * 0.45
        tip = c + tangent * length * 0.55
        half = 0.75 + 0.25 * (index % 3)
        face = [root - normal * half, root + normal * half,
                tip + normal * 0.12]
        bank = "amber_quill_faces_a" if (index * 7) % 13 < 7 else "violet_quill_faces_b"
        _draw_poly(masks[bank], face, 0.72 + 0.07 * (index % 4), 1, True)
        _draw_line(masks["hard_spines"], root, tip, 1.0, 1)
        if index % 2 == 0:
            anchor = root + tangent * length * (0.28 + 0.08 * (index % 4))
            _draw_line(masks["cuticle_ticks"], anchor - normal * 1.2,
                       anchor + normal * 1.2, 1.0, 1)
        if index % 3 == 0:
            anchor = root + tangent * length * 0.62
            side = -1.0 if index & 1 else 1.0
            _draw_line(masks["offset_barbs"], anchor,
                       anchor - tangent * 1.2 + normal * side * (1.5 + index % 3),
                       1.0, 1)
        if index % 5 == 0:
            _draw_line(masks["split_nibs"], tip - tangent * 1.2,
                       tip + normal * 1.6, 1.0, 1)
            _draw_line(masks["split_nibs"], tip - tangent * 1.2,
                       tip - normal * 1.3, 1.0, 1)
        if index % 7 == 0:
            _draw_line(masks["buried_roots"], root - normal * 1.5,
                       root + normal * 1.5, 1.0, 2)
        if index % 11 == 0:
            _w16_segment(masks["crossed_needles"], c, angle + 1.05,
                         4.0 + index % 5, 1.0, 1, 0.2)
        if index % 13 == 0:
            frag_c = c + normal * (2.5 + index % 4)
            _w16_segment(masks["broken_fragments"], frag_c,
                         angle + 0.3 * np.sin(index), 2.0 + index % 4,
                         1.0, 1, 0.4)
    tone = _norm(0.39 * np.sin(x / 59.0) - 0.31 * np.cos(y / 73.0)
                 + 0.27 * np.sin((x + y) / 31.0) + 0.0009 * y)
    banks = dict(amber_quill_faces_a="A", violet_quill_faces_b="B",
                 hard_spines="N", cuticle_ticks="A", offset_barbs="B",
                 split_nibs="B", buried_roots="A", crossed_needles="N",
                 broken_fragments="B")
    return _pack(masks, banks, tone)


def _build_fc_coarse_hide_w16() -> _Grammar:
    """Rucked hide from overlapping pressure folds, never closed cells."""
    names = ("compressed_fold_a", "released_fold_b", "fold_crests",
             "crease_shadows", "short_wrinkles", "scar_staples",
             "sweat_pores", "abraded_flecks", "crossgrain_nicks")
    x, y = _xy()
    # Twenty-one fixed anisotropic pressure events create a rumpled sheet.
    pressure = np.zeros((_WORK, _WORK), np.float32)
    shear = np.zeros_like(pressure)
    for event in range(1, 22):
        cx = -35.0 + 580.0 * _halton(event, 2)
        cy = -30.0 + 570.0 * _halton(event, 3)
        angle = 0.31 * event + 0.7 * np.sin(event * 1.9)
        ca, sa = np.cos(angle), np.sin(angle)
        dx, dy = x - cx, y - cy
        u = ca * dx + sa * dy
        v = -sa * dx + ca * dy
        major = 42.0 + (event * 17) % 57
        minor = 11.0 + (event * 13) % 19
        event_field = np.exp(-(u * u / (major * major)
                               + v * v / (minor * minor))).astype(np.float32)
        pressure += event_field * (0.65 + 0.08 * (event % 5))
        shear += event_field * np.sin(u / (4.3 + event % 4))
    pressure = _norm(pressure)
    gx = cv2.Sobel(pressure, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(pressure, cv2.CV_32F, 0, 1, ksize=3)
    slope = _norm(np.hypot(gx, gy))
    crests = _f32((slope - 0.20) / 0.48)
    compressed = _f32((pressure - 0.43) / 0.42) * (1.0 - 0.42 * crests)
    released = _f32((0.61 - pressure) / 0.48) * (0.24 + 0.76 * slope)
    shadows = _f32(cv2.GaussianBlur(crests, (0, 0), 2.2) - 0.32 * crests)
    wrinkle_phase = np.sin((1.7 * x + 0.9 * y) / 4.8 + shear * 4.3)
    dash = _f32((np.cos((0.6 * x - 1.4 * y) / 7.1) - 0.15) / 0.85)
    wrinkles = _f32(_line(wrinkle_phase, 0.11) * (0.25 + 0.75 * crests) * dash)
    staples = _f32(wrinkles * _line(np.sin((x - y) / 9.3 + pressure * 5.0), 0.12))
    pores = ((pressure > cv2.dilate(pressure, np.ones((5, 5), np.uint8)) - 1e-5)
             .astype(np.float32) * _f32((pressure - 0.42) / 0.45))
    pores = cv2.dilate(pores, np.ones((3, 3), np.uint8))
    flecks = _f32(crests * _line(np.sin((2.2 * x - y) / 6.7), 0.09)
                  * _line(np.cos((x + 1.9 * y) / 5.9), 0.11))
    nicks = _f32(_line(np.sin((x + 2.1 * y) / 8.7 + shear * 2.0), 0.08)
                 * _f32((slope - 0.37) / 0.45))
    masks = dict(compressed_fold_a=compressed, released_fold_b=released,
                 fold_crests=crests, crease_shadows=shadows,
                 short_wrinkles=wrinkles, scar_staples=staples,
                 sweat_pores=pores, abraded_flecks=flecks,
                 crossgrain_nicks=nicks)
    banks = dict(compressed_fold_a="A", released_fold_b="B",
                 fold_crests="B", crease_shadows="A", short_wrinkles="N",
                 scar_staples="A", sweat_pores="B", abraded_flecks="N",
                 crossgrain_nicks="B")
    return _pack(masks, banks, _norm(pressure + 0.17 * shear))


def _build_fc_eyeshine_w16() -> _Grammar:
    """One fine tapetal interference cloth, with no repeated eye basin."""
    names = ("gold_polarity_a", "violet_polarity_b", "tapetal_needles",
             "crossed_relays", "pupil_dashes", "caustic_combs",
             "glint_pairs", "dark_adaptation", "relay_splinters")
    x, y = _xy()
    u = x + 8.0 * np.sin(y / 47.0) + 4.0 * np.sin((x - y) / 71.0)
    v = y - 7.0 * np.cos(x / 59.0) + 3.0 * np.cos((x + y) / 83.0)
    p = np.sin(u / 3.7 + v / 19.0) + 0.58 * np.sin(v / 4.9 - u / 23.0)
    q = np.cos(v / 3.3 - u / 17.0) + 0.52 * np.sin((u + v) / 5.7)
    dash_a = _f32((np.cos((0.71 * u - 0.36 * v) / 6.1) - 0.05) / 0.95)
    dash_b = _f32((np.sin((0.43 * u + 0.82 * v) / 7.3) + 0.07) / 0.93)
    polarity_a = _f32((p - 0.05) / 1.18) * dash_a
    polarity_b = _f32((-p - 0.03) / 1.14) * dash_b
    needles = _f32(_line(p, 0.11) * (0.32 + 0.68 * dash_b))
    relays = _f32(_line(q, 0.10) * (0.28 + 0.72 * dash_a))
    pupil = _f32(_line(np.sin(u / 2.5 + q), 0.075)
                 * _f32((np.cos(v / 8.3) - 0.22) / 0.78))
    combs = _f32(_line(np.sin(v / 2.9 - p * 1.7), 0.075)
                 * _f32((np.sin(u / 9.1) - 0.08) / 0.92))
    glints = _f32(needles * relays * 2.5)
    dark = _f32((0.32 - np.abs(p)) / 0.32) * (1.0 - 0.65 * glints)
    splinters = _f32(_line(np.sin((u - v) / 2.3 + p * q), 0.065)
                      * _f32((np.cos((u + v) / 11.0) - 0.35) / 0.65))
    masks = dict(gold_polarity_a=polarity_a, violet_polarity_b=polarity_b,
                 tapetal_needles=needles, crossed_relays=relays,
                 pupil_dashes=pupil, caustic_combs=combs,
                 glint_pairs=glints, dark_adaptation=dark,
                 relay_splinters=splinters)
    banks = dict(gold_polarity_a="A", violet_polarity_b="B",
                 tapetal_needles="A", crossed_relays="B", pupil_dashes="N",
                 caustic_combs="B", glint_pairs="A", dark_adaptation="N",
                 relay_splinters="B")
    return _pack(masks, banks, _norm(p + 0.31 * q))


def _build_fc_bog_murk_w16() -> _Grammar:
    """Dense peat-film microbiology replaces the sparse trunk skeleton."""
    names = ("peat_clots_a", "oil_films_b", "microbial_rods",
             "spore_crescents", "gas_pores", "root_hairs",
             "wet_halves", "silt_flecks", "decay_bridges")
    masks = _new_marks(*names)
    x, y = _xy()
    clot = np.zeros((_WORK, _WORK), np.float32)
    film = np.zeros_like(clot)
    for colony in range(1, 281):
        c = np.asarray([_halton(colony, 2) * 512.0,
                        _halton(colony, 3) * 512.0], np.float32)
        angle = (1.9 * np.sin(c[0] / 91.0) - 1.3 * np.cos(c[1] / 77.0)
                 + 0.17 * colony)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        extent = 5.0 + (colony * 7) % 10
        wet_side = -1.0 if colony & 1 else 1.0
        _w16_disc(clot, c - normal * 1.5, 2 + colony % 4, 0.8, True)
        _w16_disc(film, c + normal * 2.0, 3 + colony % 5, 0.7, True)
        for branch in range(1, 4 + colony % 4):
            origin = c + tangent * ((branch - 2.5) * 1.2)
            theta = angle + wet_side * (0.25 + 0.19 * branch)
            _, _, tip = _w16_segment(masks["microbial_rods"], origin,
                                      theta, 3.0 + (colony + branch) % 6,
                                      1.0, 1, 0.5 * np.sin(colony + branch))
            if (colony + branch) % 3 == 0:
                cv2.ellipse(masks["spore_crescents"],
                            tuple(np.rint(tip).astype(int)),
                            (2 + branch % 2, 1 + colony % 2),
                            float(np.degrees(theta)), 20, 255, 1.0, 1,
                            cv2.LINE_AA)
            if (colony + branch) % 4 == 0:
                _w16_segment(masks["root_hairs"], origin,
                             theta + wet_side * 0.9, 2.0 + branch,
                             1.0, 1, -0.35)
        if colony % 2 == 0:
            _w16_disc(masks["gas_pores"], c + tangent * 2.0, 1 + colony % 3,
                      1.0, False)
        if colony % 3 == 0:
            _w16_segment(masks["wet_halves"], c + normal * wet_side * 2.0,
                         angle, 4.0 + colony % 6, 1.0, 2, 0.7)
        if colony % 5 == 0:
            for fleck in range(3):
                p = c + normal * (fleck - 1) * 2.1 + tangent * (fleck - 0.5)
                _w16_disc(masks["silt_flecks"], p, 1, 1.0, True)
        if colony % 7 == 0:
            _w16_segment(masks["decay_bridges"], c - tangent * extent * 0.35,
                         angle + 0.45, 5.0 + colony % 7, 1.0, 1, 1.0)
    masks["peat_clots_a"] = _f32(cv2.GaussianBlur(clot, (0, 0), 2.0) * 1.9)
    masks["oil_films_b"] = _f32(cv2.GaussianBlur(film, (0, 0), 2.8) * 1.7
                                  - 0.22 * masks["peat_clots_a"])
    banks = dict(peat_clots_a="A", oil_films_b="B", microbial_rods="B",
                 spore_crescents="A", gas_pores="N", root_hairs="B",
                 wet_halves="A", silt_flecks="N", decay_bridges="B")
    tone = _norm(0.36 * np.sin(x / 67.0) + 0.28 * np.cos(y / 79.0)
                 + 0.25 * np.sin((x + 1.7 * y) / 43.0) + clot - film)
    return _pack(masks, banks, tone)


def _build_fc_claw_rake_w16() -> _Grammar:
    """Crossing short gouge swarms replace reusable strike-bundle stamps."""
    names = ("fresh_gouges_a", "old_gouges_b", "raised_lips",
             "hook_tears", "terminal_chips", "pressure_smears",
             "crosscut_scars", "bone_dust", "healed_notches")
    masks = _new_marks(*names)
    x, y = _xy()
    smear_a = np.zeros((_WORK, _WORK), np.float32)
    smear_b = np.zeros_like(smear_a)
    for index in range(1, 1751):
        c = np.asarray([2.0 + 508.0 * _halton(index, 2),
                        2.0 + 508.0 * _halton(index, 7)], np.float32)
        family = (index * 11) % 5
        angle = ((-1.04, -0.43, 0.18, 0.71, 1.27)[family]
                 + 0.24 * np.sin(c[0] / 67.0)
                 - 0.19 * np.cos(c[1] / 71.0)
                 + 0.08 * np.sin(index * 1.7))
        length = 3.0 + (index * 17) % 8
        bend = ((index * 5) % 7 - 3) * 0.28
        bank = "fresh_gouges_a" if (index * 3) % 10 < 6 else "old_gouges_b"
        root, middle, tip = _w16_segment(masks[bank], c, angle, length,
                                          1.0, 1 + (index % 17 == 0), bend)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        side = -1.0 if index & 1 else 1.0
        _draw_line(masks["raised_lips"], root + normal * side * 1.3,
                   tip + normal * side * 1.1, 0.9, 1)
        if index % 3 == 0:
            _w16_segment(masks["hook_tears"], tip - tangent * 1.0,
                         angle + side * (0.68 + 0.08 * (index % 4)),
                         2.0 + index % 4, 1.0, 1, side * 0.5)
        if index % 4 == 0:
            _w16_disc(masks["terminal_chips"], tip + normal * side,
                      1, 1.0, True)
        if index % 6 == 0:
            _w16_segment(masks["crosscut_scars"], middle,
                         angle + 1.0 + 0.17 * family,
                         2.0 + index % 5, 1.0, 1, -bend)
        if index % 8 == 0:
            for offset in (-1.4, 0.0, 1.4):
                _w16_disc(masks["bone_dust"], tip + normal * offset,
                          1, 0.8, True)
        if index % 13 == 0:
            cv2.ellipse(masks["healed_notches"],
                        tuple(np.rint(root).astype(int)),
                        (2 + index % 3, 1 + index % 2),
                        float(np.degrees(angle)), 20, 175, 1.0, 1,
                        cv2.LINE_AA)
        target = smear_a if bank.endswith("_a") else smear_b
        _draw_line(target, root - tangent * 1.0, tip + tangent * 1.0,
                   0.7, 3)
    masks["pressure_smears"] = _f32(
        cv2.GaussianBlur(smear_a + smear_b, (0, 0), 2.4) * 1.35
        - 0.34 * (smear_a + smear_b))
    banks = dict(fresh_gouges_a="A", old_gouges_b="B", raised_lips="B",
                 hook_tears="A", terminal_chips="B", pressure_smears="N",
                 crosscut_scars="A", bone_dust="N", healed_notches="B")
    tone = _norm(0.31 * np.sin(x / 53.0) - 0.27 * np.cos(y / 61.0)
                 + 0.22 * np.sin((2.0 * x - y) / 47.0))
    return _pack(masks, banks, tone)


def _build_fc_bark_camo_w16() -> _Grammar:
    """Overlapping shag-bark splinters replace coarse camo islands."""
    names = ("sunward_splinters_a", "shadow_splinters_b", "cambium_slits",
             "peel_lips", "lenticel_dashes", "resin_tears",
             "fungal_pinholes", "weather_checks", "charred_edges")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1451):
        c = np.asarray([2.0 + 508.0 * _halton(index, 3),
                        2.0 + 508.0 * _halton(index, 5)], np.float32)
        angle = (1.44 + 0.34 * np.sin(c[0] / 63.0)
                 + 0.22 * np.cos(c[1] / 71.0)
                 + ((index * 7) % 9 - 4) * 0.055)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 4.0 + (index * 13) % 8
        half = 1.1 + 0.35 * (index % 4)
        root = c - tangent * length * 0.48
        tip = c + tangent * length * 0.52
        shoulder = root + tangent * length * (0.32 + 0.05 * (index % 3))
        polygon = [root - normal * half * 0.55,
                   shoulder - normal * half,
                   tip - normal * half * 0.22,
                   tip + normal * half * 0.40,
                   shoulder + normal * half * 0.74,
                   root + normal * half * 0.32]
        body = "sunward_splinters_a" if (index * 5) % 12 < 7 else "shadow_splinters_b"
        _draw_poly(masks[body], polygon, 0.67 + 0.08 * (index % 4), 1, True)
        _draw_line(masks["cambium_slits"], root + tangent,
                   tip - tangent, 1.0, 1)
        _draw_line(masks["peel_lips"], polygon[1], polygon[2], 1.0, 1)
        if index % 3 == 0:
            _w16_segment(masks["lenticel_dashes"], c,
                         angle + np.pi * 0.5, 2.0 + index % 4, 1.0, 1)
        if index % 5 == 0:
            tear = tip + normal * (-1.0 if index & 1 else 1.0)
            _w16_disc(masks["resin_tears"], tear, 1 + index % 2,
                      0.9, True)
            _w16_segment(masks["resin_tears"], tear, angle,
                         2.0 + index % 3, 0.9, 1, 0.4)
        if index % 7 == 0:
            _w16_disc(masks["fungal_pinholes"], c - normal * half,
                      1, 1.0, False)
        if index % 9 == 0:
            _w16_segment(masks["weather_checks"], c, angle + 0.78,
                         3.0 + index % 5, 1.0, 1, -0.5)
        if index % 11 == 0:
            _draw_line(masks["charred_edges"], polygon[4], polygon[5],
                       1.0, 2)
    banks = dict(sunward_splinters_a="A", shadow_splinters_b="B",
                 cambium_slits="N", peel_lips="B", lenticel_dashes="A",
                 resin_tears="B", fungal_pinholes="N", weather_checks="A",
                 charred_edges="B")
    tone = _norm(0.42 * np.sin(y / 43.0) + 0.21 * np.cos(x / 71.0)
                 + 0.18 * np.sin((x + y) / 29.0) + 0.0012 * y)
    return _pack(masks, banks, tone)


def _build_fc_feathered_wing_w16() -> _Grammar:
    """Overlapping barbule lace; no complete feather packet or vortex hub."""
    names = ("violet_vanes_a", "cyan_vanes_b", "micro_rachis",
             "left_barbules", "right_barbules", "hooklet_nodes",
             "cross_vane_bridges", "down_fuzz", "iridescent_nicks")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 2451):
        c = np.asarray([2.0 + 508.0 * _halton(index, 2),
                        2.0 + 508.0 * _halton(index, 11)], np.float32)
        flow = (0.18 + 0.55 * np.sin(c[0] / 83.0)
                - 0.37 * np.cos(c[1] / 67.0)
                + 0.21 * np.sin((c[0] - c[1]) / 47.0))
        family = -1.0 if (index * 5) % 9 < 4 else 1.0
        angle = flow + family * (0.46 + 0.05 * (index % 4))
        length = 3.0 + (index * 17) % 7
        body = "violet_vanes_a" if family < 0 else "cyan_vanes_b"
        root, middle, tip = _w16_segment(masks[body], c, angle,
                                          length + 1.0, 0.74, 2,
                                          family * 0.45)
        _w16_segment(masks["micro_rachis"], c, flow, length,
                     1.0, 1, 0.2 * np.sin(index))
        barb_name = "left_barbules" if family < 0 else "right_barbules"
        if index % 2 == 0:
            _w16_segment(masks[barb_name], middle, flow + family * 1.02,
                         2.0 + index % 4, 1.0, 1, family * 0.3)
        if index % 3 == 0:
            _w16_disc(masks["hooklet_nodes"], tip, 1, 1.0, True)
        if index % 5 == 0:
            _w16_segment(masks["cross_vane_bridges"], c, flow + 1.48,
                         2.0 + index % 5, 1.0, 1, -family * 0.35)
        if index % 7 == 0:
            for offset in (-1.4, 1.4):
                _w16_segment(masks["down_fuzz"], root + np.asarray([offset, 0.0]),
                             flow + offset * 0.24, 2.0 + index % 3,
                             0.85, 1, 0.5)
        if index % 11 == 0:
            _w16_segment(masks["iridescent_nicks"], middle,
                         flow + family * 0.72, 2.0, 1.0, 1)
    banks = dict(violet_vanes_a="A", cyan_vanes_b="B", micro_rachis="N",
                 left_barbules="A", right_barbules="B", hooklet_nodes="B",
                 cross_vane_bridges="N", down_fuzz="A",
                 iridescent_nicks="B")
    tone = _norm(0.35 * np.sin(x / 73.0) - 0.31 * np.cos(y / 59.0)
                 + 0.24 * np.sin((x - 1.4 * y) / 41.0))
    return _pack(masks, banks, tone)


def _build_fc_dorsal_ridge_w16() -> _Grammar:
    """Broken scalene osteoderms replace the Chladni contour paver."""
    names = ("compression_scutes_a", "rebound_scutes_b", "dorsal_keels",
             "saw_notches", "osteon_pores", "ligament_tabs",
             "abrasion_chips", "collision_sutures", "shed_slivers")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1001):
        c = np.asarray([2.0 + 508.0 * _halton(index, 5),
                        2.0 + 508.0 * _halton(index, 7)], np.float32)
        angle = (0.55 * np.sin(c[0] / 79.0)
                 + 0.46 * np.cos(c[1] / 61.0)
                 + 0.25 * np.sin((c[0] + c[1]) / 37.0)
                 + ((index * 13) % 11 - 5) * 0.06)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 3.0 + (index * 11) % 8
        width = 1.4 + 0.45 * (index % 5)
        root = c - tangent * length * 0.45
        tip = c + tangent * length * 0.55
        # Six unequal scalene silhouettes prevent a stamp field.
        shoulder_shift = ((index * 7) % 5 - 2) * 0.35
        polygon = [root - normal * width * 0.45,
                   c - tangent * 0.7 - normal * (width + shoulder_shift),
                   tip + normal * (0.15 + 0.1 * (index % 3)),
                   c + tangent * 0.5 + normal * (width * 0.62),
                   root + normal * width * 0.28]
        body = "compression_scutes_a" if (index * 3) % 10 < 6 else "rebound_scutes_b"
        _draw_poly(masks[body], polygon, 0.67 + 0.08 * (index % 4), 1, True)
        _draw_line(masks["dorsal_keels"], root, tip, 1.0, 1)
        if index % 2 == 0:
            _w16_segment(masks["saw_notches"], tip - tangent,
                         angle + (0.72 if index & 2 else -0.63),
                         2.0 + index % 4, 1.0, 1, 0.3)
        if index % 3 == 0:
            _w16_disc(masks["osteon_pores"], c - tangent * 0.5,
                      1, 1.0, False)
        if index % 5 == 0:
            _w16_segment(masks["ligament_tabs"], root,
                         angle + np.pi * 0.5, 2.0 + index % 3,
                         1.0, 1)
        if index % 7 == 0:
            _w16_disc(masks["abrasion_chips"], tip + normal,
                      1, 1.0, True)
        if index % 9 == 0:
            _w16_segment(masks["collision_sutures"], c,
                         angle + 1.1, 3.0 + index % 4,
                         1.0, 1, -0.5)
        if index % 13 == 0:
            _w16_segment(masks["shed_slivers"], c + normal * 3.0,
                         angle - 0.24, 2.0 + index % 5,
                         1.0, 1, 0.4)
    banks = dict(compression_scutes_a="A", rebound_scutes_b="B",
                 dorsal_keels="B", saw_notches="A", osteon_pores="N",
                 ligament_tabs="B", abrasion_chips="N",
                 collision_sutures="A", shed_slivers="B")
    tone = _norm(0.38 * np.sin(x / 83.0) + 0.29 * np.cos(y / 71.0)
                 + 0.21 * np.sin((1.6 * x - y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_webbed_membrane_w16() -> _Grammar:
    """Fine stretched tissue, capillary deltas and local wrinkles—no rib fan."""
    names = ("taut_membrane_a", "slack_membrane_b", "tension_wrinkles",
             "capillary_stems", "capillary_forks", "dew_nodes",
             "scar_windows", "elastic_crosslinks", "edge_frays")
    x, y = _xy()
    tension = np.zeros((_WORK, _WORK), np.float32)
    skew = np.zeros_like(tension)
    # Cropped external pulls deform the sheet but never draw their anchors.
    for anchor in range(1, 14):
        side = anchor % 4
        if side == 0:
            cx, cy = -70.0, _halton(anchor, 3) * 512.0
        elif side == 1:
            cx, cy = 582.0, _halton(anchor, 5) * 512.0
        elif side == 2:
            cx, cy = _halton(anchor, 2) * 512.0, -65.0
        else:
            cx, cy = _halton(anchor, 7) * 512.0, 577.0
        dx, dy = x - cx, y - cy
        radius = 95.0 + (anchor * 19) % 71
        pull = np.exp(-(dx * dx + dy * dy) / (radius * radius)).astype(np.float32)
        tension += pull * (0.7 + 0.05 * anchor)
        skew += pull * np.sin((0.6 * dx - 0.8 * dy) / (19.0 + anchor))
    tension = _norm(tension)
    taut = _f32((tension - 0.38) / 0.47)
    slack = _f32((0.66 - tension) / 0.51)
    phase = (1.7 * x + 0.8 * y) / 4.3 + skew * 3.2
    breaks = _f32((np.cos((0.5 * x - 1.3 * y) / 7.7) - 0.08) / 0.92)
    wrinkles = _f32(_line(np.sin(phase), 0.10) * breaks)
    stems = np.zeros((_WORK, _WORK), np.float32)
    forks = np.zeros_like(stems)
    dew = np.zeros_like(stems)
    windows = np.zeros_like(stems)
    cross = np.zeros_like(stems)
    frays = np.zeros_like(stems)
    for index in range(1, 701):
        c = np.asarray([2.0 + 508.0 * _halton(index, 3),
                        2.0 + 508.0 * _halton(index, 11)], np.float32)
        angle = (0.34 * np.sin(c[0] / 71.0) - 0.42 * np.cos(c[1] / 83.0)
                 + 0.19 * np.sin((c[0] + c[1]) / 53.0))
        root, middle, tip = _w16_segment(stems, c, angle,
                                          3.0 + (index * 7) % 7,
                                          1.0, 1, 0.5 * np.sin(index))
        if index % 2 == 0:
            side = -1.0 if index & 2 else 1.0
            _w16_segment(forks, tip, angle + side * (0.55 + 0.08 * (index % 4)),
                         2.0 + index % 4, 1.0, 1, side * 0.3)
        if index % 4 == 0:
            _w16_disc(dew, tip, 1 + index % 2, 1.0, True)
        if index % 7 == 0:
            cv2.ellipse(windows, tuple(np.rint(c).astype(int)),
                        (2 + index % 4, 1 + index % 3),
                        float(np.degrees(angle)), 25, 305, 1.0, 1,
                        cv2.LINE_AA)
        if index % 9 == 0:
            _w16_segment(cross, middle, angle + 1.2,
                         2.0 + index % 5, 1.0, 1, -0.5)
        if index % 13 == 0:
            _w16_segment(frays, root, angle - 0.7,
                         2.0 + index % 4, 1.0, 1, 0.7)
    masks = dict(taut_membrane_a=taut, slack_membrane_b=slack,
                 tension_wrinkles=wrinkles, capillary_stems=stems,
                 capillary_forks=forks, dew_nodes=dew,
                 scar_windows=windows, elastic_crosslinks=cross,
                 edge_frays=frays)
    banks = dict(taut_membrane_a="A", slack_membrane_b="B",
                 tension_wrinkles="N", capillary_stems="B",
                 capillary_forks="A", dew_nodes="B", scar_windows="N",
                 elastic_crosslinks="A", edge_frays="B")
    return _pack(masks, banks, _norm(tension + 0.21 * skew))


def _build_fc_toad_skin_w16() -> _Grammar:
    """Seven interleaved gland anatomies replace reaction-loop contours."""
    names = ("olive_glands_a", "warning_glands_b", "wart_crowns",
             "wet_collars", "pore_clusters", "thorn_nubs",
             "seam_crescents", "capillary_notches", "shed_peels")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1251):
        c = np.asarray([2.0 + 508.0 * _halton(index, 2),
                        2.0 + 508.0 * _halton(index, 13)], np.float32)
        radius = 1.8 + 0.55 * ((index * 7) % 7)
        lobes = 3 + (index * 5) % 5
        rotation = 0.37 * index + 0.42 * np.sin(c[0] / 67.0)
        pts = []
        for vertex in range(lobes * 2):
            theta = rotation + _TAU * vertex / float(lobes * 2)
            alternating = 1.0 if vertex % 2 == 0 else 0.53 + 0.07 * (index % 4)
            local_r = radius * alternating * (0.86 + 0.12 * np.sin(index + vertex * 1.7))
            pts.append(c + np.asarray([np.cos(theta), np.sin(theta)], np.float32)
                       * local_r)
        body = "olive_glands_a" if (index * 11) % 17 < 9 else "warning_glands_b"
        _draw_poly(masks[body], pts, 0.66 + 0.08 * (index % 4), 1, True)
        if index % 2 == 0:
            cv2.ellipse(masks["wart_crowns"], tuple(np.rint(c).astype(int)),
                        (max(1, int(radius)), max(1, int(radius * 0.62))),
                        float(np.degrees(rotation)), 195, 345, 1.0, 1,
                        cv2.LINE_AA)
        if index % 3 == 0:
            cv2.ellipse(masks["wet_collars"], tuple(np.rint(c).astype(int)),
                        (max(2, int(radius + 1)), max(1, int(radius * 0.75 + 1))),
                        float(np.degrees(rotation)), 12, 168, 1.0, 1,
                        cv2.LINE_AA)
        if index % 4 == 0:
            for pore in range(1 + index % 3):
                theta = rotation + pore * 2.1
                p = c + np.asarray([np.cos(theta), np.sin(theta)], np.float32)
                _w16_disc(masks["pore_clusters"], p, 1, 1.0, True)
        if index % 5 == 0:
            theta = rotation + (index % lobes) * _TAU / lobes
            tip = c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * radius
            _w16_segment(masks["thorn_nubs"], tip, theta,
                         2.0 + index % 3, 1.0, 1, 0.25)
        if index % 7 == 0:
            cv2.ellipse(masks["seam_crescents"], tuple(np.rint(c).astype(int)),
                        (2 + index % 4, 1 + index % 2),
                        float(np.degrees(rotation)), 40, 258, 1.0, 1,
                        cv2.LINE_AA)
        if index % 9 == 0:
            _w16_segment(masks["capillary_notches"], c,
                         rotation + 1.2, 2.0 + index % 5,
                         1.0, 1, -0.4)
        if index % 11 == 0:
            _w16_segment(masks["shed_peels"], c + np.asarray([radius, 0.0]),
                         rotation - 0.7, 3.0 + index % 4,
                         1.0, 1, 0.8)
    banks = dict(olive_glands_a="A", warning_glands_b="B", wart_crowns="B",
                 wet_collars="A", pore_clusters="N", thorn_nubs="B",
                 seam_crescents="A", capillary_notches="N", shed_peels="B")
    tone = _norm(0.32 * np.sin(x / 71.0) + 0.27 * np.cos(y / 53.0)
                 + 0.24 * np.sin((x + y) / 37.0))
    return _pack(masks, banks, tone)


def _build_fc_antler_bone_w16() -> _Grammar:
    """Directional trabecular splinters replace nested oval osteon paving."""
    names = ("dense_marrow_a", "open_marrow_b", "trabecular_beams",
             "mineral_forks", "lamella_ticks", "canal_pores",
             "osteoclast_bays", "calcified_bridges", "weathered_splinters")
    masks = _new_marks(*names)
    x, y = _xy()
    marrow_a = np.zeros((_WORK, _WORK), np.float32)
    marrow_b = np.zeros_like(marrow_a)
    for index in range(1, 1151):
        c = np.asarray([2.0 + 508.0 * _halton(index, 3),
                        2.0 + 508.0 * _halton(index, 7)], np.float32)
        angle = (0.17 + 0.62 * np.sin(c[1] / 79.0)
                 + 0.28 * np.cos(c[0] / 67.0)
                 + ((index * 11) % 9 - 4) * 0.07)
        length = 3.0 + (index * 13) % 8
        root, middle, tip = _w16_segment(masks["trabecular_beams"], c,
                                          angle, length, 1.0,
                                          2 if index % 19 == 0 else 1,
                                          0.45 * np.sin(index * 0.7))
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        target = marrow_a if (index * 5) % 12 < 7 else marrow_b
        _draw_line(target, root, tip, 0.8, 3)
        if index % 2 == 0:
            side = -1.0 if index & 2 else 1.0
            _w16_segment(masks["mineral_forks"], tip - tangent,
                         angle + side * (0.58 + 0.07 * (index % 5)),
                         2.0 + index % 5, 1.0, 1, side * 0.4)
        if index % 3 == 0:
            _w16_segment(masks["lamella_ticks"], middle,
                         angle + np.pi * 0.5, 2.0 + index % 4,
                         1.0, 1)
        if index % 5 == 0:
            _w16_disc(masks["canal_pores"], root + normal * 1.3,
                      1, 1.0, False)
        if index % 7 == 0:
            cv2.ellipse(masks["osteoclast_bays"],
                        tuple(np.rint(c + normal * 2.0).astype(int)),
                        (2 + index % 3, 1 + index % 2),
                        float(np.degrees(angle)), 40, 250, 1.0, 1,
                        cv2.LINE_AA)
        if index % 11 == 0:
            _w16_segment(masks["calcified_bridges"], middle,
                         angle + 1.15, 3.0 + index % 5,
                         1.0, 1, -0.5)
        if index % 13 == 0:
            _w16_segment(masks["weathered_splinters"], tip + normal * 2.0,
                         angle - 0.32, 2.0 + index % 6,
                         1.0, 1, 0.5)
    masks["dense_marrow_a"] = _f32(cv2.GaussianBlur(marrow_a, (0, 0), 2.0) * 1.8)
    masks["open_marrow_b"] = _f32(cv2.GaussianBlur(marrow_b, (0, 0), 2.7) * 2.0
                                    - 0.2 * masks["dense_marrow_a"])
    banks = dict(dense_marrow_a="A", open_marrow_b="B",
                 trabecular_beams="N", mineral_forks="B",
                 lamella_ticks="A", canal_pores="N", osteoclast_bays="B",
                 calcified_bridges="A", weathered_splinters="B")
    tone = _norm(0.38 * np.sin(x / 89.0) - 0.25 * np.cos(y / 61.0)
                 + 0.2 * np.sin((x - y) / 43.0) + marrow_a - marrow_b)
    return _pack(masks, banks, tone)


def _build_fc_mossy_stone_w16() -> _Grammar:
    """Edge-cropped microfault chips and lichen colonies, never a central fan."""
    names = ("dry_basalt_a", "wet_basalt_b", "microfaults",
             "fault_lips", "lichen_tufts", "quartz_nicks",
             "moisture_beads", "spalled_chips", "moss_filaments")
    masks = _new_marks(*names)
    x, y = _xy()
    # Independent roots enter from all four edges and walk only a short span;
    # there is no shared target, radial centre, or full-card lane.
    for fault in range(1, 97):
        side = fault % 4
        if side == 0:
            point = np.asarray([0.0, _halton(fault, 3) * 512.0], np.float32)
            heading = -0.48 + 0.16 * (fault % 7)
        elif side == 1:
            point = np.asarray([511.0, _halton(fault, 5) * 512.0], np.float32)
            heading = np.pi - 0.5 + 0.15 * (fault % 8)
        elif side == 2:
            point = np.asarray([_halton(fault, 2) * 512.0, 0.0], np.float32)
            heading = 1.08 + 0.14 * (fault % 7)
        else:
            point = np.asarray([_halton(fault, 7) * 512.0, 511.0], np.float32)
            heading = -1.94 + 0.13 * (fault % 9)
        steps = 5 + (fault * 7) % 9
        previous = point.copy()
        for step in range(steps):
            heading += 0.16 * np.sin(fault * 1.3 + step * 1.9)
            length = 3.0 + (fault + step * 5) % 6
            point = previous + np.asarray([np.cos(heading), np.sin(heading)], np.float32) * length
            _draw_line(masks["microfaults"], previous, point, 1.0, 1)
            normal = np.asarray([-np.sin(heading), np.cos(heading)], np.float32)
            _draw_line(masks["fault_lips"], previous + normal * 1.4,
                       point + normal * 1.2, 0.9, 1)
            if (fault + step) % 3 == 0:
                _w16_disc(masks["quartz_nicks"], point, 1, 1.0, True)
            previous = point
    for chip in range(1, 1051):
        c = np.asarray([2.0 + 508.0 * _halton(chip, 11),
                        2.0 + 508.0 * _halton(chip, 13)], np.float32)
        angle = 0.43 * chip + 0.3 * np.sin(c[0] / 79.0)
        radius = 1.7 + 0.45 * ((chip * 7) % 7)
        vertices = 3 + chip % 4
        pts = []
        for k in range(vertices):
            theta = angle + _TAU * k / vertices
            rr = radius * (0.72 + 0.23 * np.sin(chip + k * 1.7))
            pts.append(c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * rr)
        body = "dry_basalt_a" if (chip * 5) % 13 < 7 else "wet_basalt_b"
        _draw_poly(masks[body], pts, 0.62 + 0.09 * (chip % 4), 1, True)
        if chip % 3 == 0:
            _w16_disc(masks["lichen_tufts"], c + np.asarray([1.2, -0.8]),
                      1 + chip % 3, 0.9, False)
        if chip % 5 == 0:
            _w16_disc(masks["moisture_beads"], c, 1, 1.0, True)
        if chip % 7 == 0:
            _w16_segment(masks["spalled_chips"], c, angle,
                         2.0 + chip % 5, 1.0, 1, 0.5)
        if chip % 11 == 0:
            for branch in (-1.0, 1.0):
                _w16_segment(masks["moss_filaments"], c,
                             angle + branch * 0.7, 2.0 + chip % 4,
                             1.0, 1, branch * 0.4)
    banks = dict(dry_basalt_a="A", wet_basalt_b="B", microfaults="N",
                 fault_lips="B", lichen_tufts="A", quartz_nicks="N",
                 moisture_beads="B", spalled_chips="A", moss_filaments="B")
    tone = _norm(0.31 * np.sin(x / 61.0) + 0.33 * np.cos(y / 83.0)
                 + 0.21 * np.sin((x + 1.4 * y) / 47.0))
    return _pack(masks, banks, tone)


def _build_fc_will_o_wisp_w16() -> _Grammar:
    """A dense field of detached plasma commas and sparks, without void hubs."""
    names = ("cold_plasma_a", "hot_plasma_b", "luminous_cores",
             "forked_tongues", "afterglow_halves", "detached_sparks",
             "ion_notches", "quenched_ends", "crossing_arcs")
    masks = _new_marks(*names)
    x, y = _xy()
    glow_a = np.zeros((_WORK, _WORK), np.float32)
    glow_b = np.zeros_like(glow_a)
    for index in range(1, 2051):
        c = np.asarray([2.0 + 508.0 * _halton(index, 2),
                        2.0 + 508.0 * _halton(index, 17)], np.float32)
        angle = (0.9 * np.sin(c[0] / 73.0) + 0.74 * np.cos(c[1] / 89.0)
                 + 0.31 * np.sin((c[0] - c[1]) / 43.0)
                 + ((index * 7) % 11 - 5) * 0.045)
        length = 3.0 + (index * 13) % 7
        bank_mask = glow_a if (index * 5) % 12 < 7 else glow_b
        root, middle, tip = _w16_segment(bank_mask, c, angle,
                                          length + 1.0, 0.8, 2,
                                          0.8 * np.sin(index * 0.9))
        _w16_segment(masks["luminous_cores"], c, angle, length,
                     1.0, 1, 0.65 * np.sin(index * 0.9))
        if index % 2 == 0:
            side = -1.0 if index & 2 else 1.0
            _w16_segment(masks["forked_tongues"], tip,
                         angle + side * (0.6 + 0.08 * (index % 4)),
                         2.0 + index % 4, 1.0, 1, side * 0.5)
        if index % 3 == 0:
            _w16_segment(masks["afterglow_halves"], middle,
                         angle + 0.22, length * 0.55, 0.9, 2, -0.4)
        if index % 4 == 0:
            _w16_disc(masks["detached_sparks"], tip + np.asarray([1.4, -1.2]),
                      1, 1.0, True)
        if index % 7 == 0:
            _w16_segment(masks["ion_notches"], middle,
                         angle + np.pi * 0.5, 2.0, 1.0, 1)
        if index % 9 == 0:
            _w16_disc(masks["quenched_ends"], root, 1 + index % 2,
                      1.0, False)
        if index % 13 == 0:
            _w16_segment(masks["crossing_arcs"], c,
                         angle + 1.18, 3.0 + index % 5,
                         1.0, 1, -0.8)
    masks["cold_plasma_a"] = _f32(cv2.GaussianBlur(glow_a, (0, 0), 1.9) * 1.8)
    masks["hot_plasma_b"] = _f32(cv2.GaussianBlur(glow_b, (0, 0), 2.7) * 1.9
                                   - 0.18 * masks["cold_plasma_a"])
    banks = dict(cold_plasma_a="A", hot_plasma_b="B", luminous_cores="N",
                 forked_tongues="B", afterglow_halves="A",
                 detached_sparks="B", ion_notches="N", quenched_ends="A",
                 crossing_arcs="B")
    tone = _norm(0.34 * np.sin(x / 83.0) - 0.29 * np.cos(y / 71.0)
                 + 0.27 * np.sin((x + y) / 39.0) + glow_b - glow_a)
    return _pack(masks, banks, tone)


def _build_fc_snakeskin_w16() -> _Grammar:
    """Open, overlapping shed fragments replace broad scute ribbons."""
    names = ("belly_fragments_a", "keel_fragments_b", "open_chevrons",
             "shed_crescents", "keel_nicks", "friction_scratches",
             "chromatophore_dots", "hinge_threads", "weathered_tips")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1551):
        c = np.asarray([2.0 + 508.0 * _halton(index, 5),
                        2.0 + 508.0 * _halton(index, 11)], np.float32)
        angle = (0.18 + 0.27 * np.sin(c[1] / 69.0)
                 + 0.18 * np.cos(c[0] / 83.0)
                 + ((index * 7) % 9 - 4) * 0.055)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        span = 2.4 + 0.55 * ((index * 13) % 8)
        root = c - tangent * span * 0.55
        tip = c + tangent * span * 0.55
        apex = c + normal * ((-1.0 if index & 1 else 1.0)
                             * (1.2 + 0.35 * (index % 5)))
        body = "belly_fragments_a" if (index * 3) % 10 < 6 else "keel_fragments_b"
        _draw_poly(masks[body], [root, apex, tip],
                   0.64 + 0.08 * (index % 4), 1, True)
        # Open chevrons deliberately omit the root-to-tip closing edge.
        _draw_line(masks["open_chevrons"], root, apex, 1.0, 1)
        _draw_line(masks["open_chevrons"], apex, tip, 1.0, 1)
        if index % 2 == 0:
            cv2.ellipse(masks["shed_crescents"], tuple(np.rint(c).astype(int)),
                        (max(2, int(span)), 1 + index % 2),
                        float(np.degrees(angle)), 205, 338, 1.0, 1,
                        cv2.LINE_AA)
        if index % 3 == 0:
            _w16_segment(masks["keel_nicks"], apex,
                         angle + np.pi * 0.5, 2.0 + index % 4,
                         1.0, 1)
        if index % 5 == 0:
            _w16_segment(masks["friction_scratches"], c,
                         angle + 0.34, 3.0 + index % 5,
                         1.0, 1, 0.35)
        if index % 7 == 0:
            _w16_disc(masks["chromatophore_dots"], c - normal,
                      1, 1.0, True)
        if index % 9 == 0:
            _w16_segment(masks["hinge_threads"], root,
                         angle + 1.15, 2.0 + index % 4,
                         1.0, 1, -0.4)
        if index % 11 == 0:
            _w16_disc(masks["weathered_tips"], tip, 1, 1.0, False)
    banks = dict(belly_fragments_a="A", keel_fragments_b="B",
                 open_chevrons="N", shed_crescents="B", keel_nicks="A",
                 friction_scratches="N", chromatophore_dots="B",
                 hinge_threads="A", weathered_tips="B")
    tone = _norm(0.37 * np.sin(x / 67.0) + 0.25 * np.cos(y / 89.0)
                 + 0.21 * np.sin((x - 1.3 * y) / 41.0))
    return _pack(masks, banks, tone)


def _build_fc_batwing_w16() -> _Grammar:
    """Crumpled micro-pleats and local capillaries, with no wrist/rib fan."""
    names = ("mountain_pleats_a", "valley_pleats_b", "crease_spines",
             "kawasaki_crossfolds", "capillary_threads", "scar_slits",
             "membrane_pinholes", "frayed_hinges", "echo_notches")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1651):
        c = np.asarray([2.0 + 508.0 * _halton(index, 7),
                        2.0 + 508.0 * _halton(index, 13)], np.float32)
        angle = (0.72 * np.sin(c[0] / 91.0)
                 - 0.51 * np.cos(c[1] / 73.0)
                 + 0.19 * np.sin((c[0] + c[1]) / 43.0)
                 + ((index * 17) % 13 - 6) * 0.045)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        span = 3.0 + (index * 11) % 8
        root = c - tangent * span * 0.5
        tip = c + tangent * span * 0.5
        apex = c + normal * ((-1.0 if index & 1 else 1.0)
                             * (0.8 + 0.3 * (index % 5)))
        pleat = "mountain_pleats_a" if (index * 5) % 11 < 6 else "valley_pleats_b"
        _draw_poly(masks[pleat], [root - normal * 0.8, apex, tip + normal * 0.5,
                                  c - normal * 0.5],
                   0.61 + 0.09 * (index % 4), 1, True)
        _draw_line(masks["crease_spines"], root, apex, 1.0, 1)
        _draw_line(masks["crease_spines"], apex, tip, 1.0, 1)
        if index % 2 == 0:
            _w16_segment(masks["kawasaki_crossfolds"], apex,
                         angle + np.pi * 0.5,
                         2.0 + index % 5, 1.0, 1, 0.35)
        if index % 3 == 0:
            _w16_segment(masks["capillary_threads"], c + normal * 1.4,
                         angle + 0.21, 3.0 + index % 5,
                         1.0, 1, -0.6)
        if index % 5 == 0:
            _w16_segment(masks["scar_slits"], c,
                         angle + 0.83, 2.0 + index % 6,
                         1.0, 1, 0.5)
        if index % 7 == 0:
            _w16_disc(masks["membrane_pinholes"], c - normal,
                      1, 1.0, False)
        if index % 11 == 0:
            _w16_segment(masks["frayed_hinges"], root,
                         angle - 0.64, 2.0 + index % 4,
                         1.0, 1, -0.7)
        if index % 13 == 0:
            _w16_segment(masks["echo_notches"], tip,
                         angle + 1.22, 2.0 + index % 4,
                         1.0, 1)
    banks = dict(mountain_pleats_a="A", valley_pleats_b="B",
                 crease_spines="N", kawasaki_crossfolds="B",
                 capillary_threads="A", scar_slits="N",
                 membrane_pinholes="B", frayed_hinges="A",
                 echo_notches="B")
    tone = _norm(0.36 * np.sin(x / 79.0) - 0.31 * np.cos(y / 97.0)
                 + 0.23 * np.sin((x + 1.5 * y) / 47.0))
    return _pack(masks, banks, tone)


def _build_fc_gator_hide_w16() -> _Grammar:
    """Overlapping eroded osteoderm crescents replace the gyroid paver."""
    names = ("sun_scours_a", "mud_scours_b", "erosion_crescents",
             "pressure_pits", "interlocking_teeth", "seam_scrapes",
             "scar_staples", "silt_notches", "shed_rind")
    masks = _new_marks(*names)
    x, y = _xy()
    scour_a = np.zeros((_WORK, _WORK), np.float32)
    scour_b = np.zeros_like(scour_a)
    for index in range(1, 1451):
        c = np.asarray([2.0 + 508.0 * _halton(index, 3),
                        2.0 + 508.0 * _halton(index, 17)], np.float32)
        angle = (0.42 * np.sin(c[1] / 83.0)
                 + 0.26 * np.cos(c[0] / 61.0)
                 + ((index * 7) % 15 - 7) * 0.07)
        major = 2 + (index * 11) % 6
        minor = 1 + (index * 5) % 4
        start = 15 + (index * 37) % 130
        sweep = 95 + (index * 29) % 155
        target = "sun_scours_a" if (index * 5) % 13 < 7 else "mud_scours_b"
        cv2.ellipse(masks[target], tuple(np.rint(c).astype(int)),
                    (major, minor), float(np.degrees(angle)),
                    start, start + sweep, 0.84, 2, cv2.LINE_AA)
        cv2.ellipse(masks["erosion_crescents"], tuple(np.rint(c).astype(int)),
                    (major + 1, minor + 1), float(np.degrees(angle)),
                    start + 7, start + sweep - 9, 1.0, 1, cv2.LINE_AA)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        ground = scour_a if target.endswith("_a") else scour_b
        _draw_line(ground, c - tangent * major, c + tangent * major,
                   0.68, 3)
        if index % 2 == 0:
            _w16_disc(masks["pressure_pits"], c + normal * 0.6,
                      1, 1.0, False)
        if index % 3 == 0:
            _w16_segment(masks["interlocking_teeth"], c + tangent * major,
                         angle + (0.8 if index & 2 else -0.7),
                         2.0 + index % 4, 1.0, 1, 0.35)
        if index % 5 == 0:
            _w16_segment(masks["seam_scrapes"], c,
                         angle + 0.28, 3.0 + index % 6,
                         1.0, 1, -0.5)
        if index % 7 == 0:
            _w16_segment(masks["scar_staples"], c,
                         angle + np.pi * 0.5, 2.0 + index % 5,
                         1.0, 1)
        if index % 11 == 0:
            _w16_disc(masks["silt_notches"], c - tangent * 2.0,
                      1, 1.0, True)
        if index % 13 == 0:
            _w16_segment(masks["shed_rind"], c + normal * 2.5,
                         angle - 0.45, 2.0 + index % 5,
                         1.0, 1, 0.6)
    masks["sun_scours_a"] = np.maximum(masks["sun_scours_a"],
                                        _f32(cv2.GaussianBlur(scour_a, (0, 0), 1.8) * 1.5))
    masks["mud_scours_b"] = np.maximum(masks["mud_scours_b"],
                                        _f32(cv2.GaussianBlur(scour_b, (0, 0), 2.3) * 1.6))
    banks = dict(sun_scours_a="A", mud_scours_b="B",
                 erosion_crescents="N", pressure_pits="B",
                 interlocking_teeth="A", seam_scrapes="N",
                 scar_staples="B", silt_notches="A", shed_rind="B")
    tone = _norm(0.37 * np.sin(x / 71.0) + 0.3 * np.cos(y / 89.0)
                 + 0.2 * np.sin((x - y) / 41.0) + scour_a - scour_b)
    return _pack(masks, banks, tone)


def _build_fc_hide_scale_glass_w16() -> _Grammar:
    """Full-card Fresnel sliver weave replaces the Clifford shoal emblem."""
    names = ("amber_lenses_a", "green_lenses_b", "fresnel_bevels",
             "focal_threads", "stress_splits", "pore_pairs",
             "occlusion_lips", "scuff_notches", "collision_glints")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1701):
        c = np.asarray([2.0 + 508.0 * _halton(index, 5),
                        2.0 + 508.0 * _halton(index, 19)], np.float32)
        angle = (0.53 * np.sin(c[0] / 73.0) - 0.47 * np.cos(c[1] / 97.0)
                 + 0.23 * np.sin((c[0] + c[1]) / 43.0)
                 + ((index * 11) % 9 - 4) * 0.06)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 3.0 + (index * 13) % 8
        width = 0.9 + 0.32 * (index % 5)
        root = c - tangent * length * 0.52
        tip = c + tangent * length * 0.48
        curve = normal * (0.5 * np.sin(index * 1.3))
        polygon = [root - normal * width * 0.5,
                   c - normal * width + curve,
                   tip - normal * width * 0.15,
                   tip + normal * width * 0.45,
                   c + normal * width * 0.72 + curve,
                   root + normal * width * 0.22]
        body = "amber_lenses_a" if (index * 7) % 15 < 8 else "green_lenses_b"
        _draw_poly(masks[body], polygon, 0.58 + 0.1 * (index % 4), 1, True)
        _draw_line(masks["fresnel_bevels"], polygon[0], polygon[1], 1.0, 1)
        _draw_line(masks["fresnel_bevels"], polygon[1], polygon[2], 1.0, 1)
        _draw_line(masks["focal_threads"], root + tangent,
                   tip - tangent, 1.0, 1)
        if index % 2 == 0:
            _w16_segment(masks["stress_splits"], c,
                         angle + np.pi * 0.5, 2.0 + index % 5,
                         1.0, 1, 0.4)
        if index % 3 == 0:
            _w16_disc(masks["pore_pairs"], c - normal * width,
                      1, 1.0, False)
            _w16_disc(masks["pore_pairs"], c + normal * width,
                      1, 1.0, False)
        if index % 5 == 0:
            _draw_line(masks["occlusion_lips"], polygon[3], polygon[4],
                       1.0, 1)
        if index % 7 == 0:
            _w16_segment(masks["scuff_notches"], c + normal * 1.5,
                         angle + 0.73, 2.0 + index % 4,
                         1.0, 1, -0.3)
        if index % 11 == 0:
            _w16_disc(masks["collision_glints"], tip, 1, 1.0, True)
    banks = dict(amber_lenses_a="A", green_lenses_b="B",
                 fresnel_bevels="B", focal_threads="N", stress_splits="A",
                 pore_pairs="N", occlusion_lips="B", scuff_notches="A",
                 collision_glints="B")
    tone = _norm(0.41 * np.sin(x / 83.0) - 0.28 * np.cos(y / 67.0)
                 + 0.22 * np.sin((1.2 * x + y) / 37.0))
    return _pack(masks, banks, tone)


def _build_fc_dragon_hex_glass_w16() -> _Grammar:
    """Crossing ballistic shard flights replace full-canvas triangulation."""
    names = ("emerald_shards_a", "ember_shards_b", "bevel_fragments",
             "stress_needles", "scale_remnants", "prism_slashes",
             "impact_chips", "flight_shadows", "collision_sparks")
    masks = _new_marks(*names)
    x, y = _xy()
    shard_index = 0
    # Thirty-two cropped ballistic events cross at unrelated angles.  Sources
    # remain off-card and no trajectory line is drawn; only physical shards
    # and their local descendants are visible.
    for flight in range(1, 33):
        side = flight % 4
        if side == 0:
            origin = np.asarray([-35.0, _halton(flight, 3) * 512.0], np.float32)
            velocity = np.asarray([12.0 + flight % 7, -3.0 + flight % 9], np.float32)
        elif side == 1:
            origin = np.asarray([547.0, _halton(flight, 5) * 512.0], np.float32)
            velocity = np.asarray([-13.0 - flight % 6, -4.0 + flight % 8], np.float32)
        elif side == 2:
            origin = np.asarray([_halton(flight, 7) * 512.0, -38.0], np.float32)
            velocity = np.asarray([-4.0 + flight % 9, 12.0 + flight % 6], np.float32)
        else:
            origin = np.asarray([_halton(flight, 11) * 512.0, 550.0], np.float32)
            velocity = np.asarray([-3.0 + flight % 8, -13.0 - flight % 7], np.float32)
        gravity = np.asarray([0.11 * ((flight % 5) - 2),
                              0.08 * ((flight % 7) - 3)], np.float32)
        for step in range(4, 40):
            t = step * 0.72
            c = origin + velocity * t + gravity * (t * t)
            if c[0] < -8 or c[0] > 520 or c[1] < -8 or c[1] > 520:
                continue
            tangent = velocity + 2.0 * gravity * t
            angle = float(np.arctan2(tangent[1], tangent[0]))
            tangent /= max(0.25, float(np.linalg.norm(tangent)))
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 2.5 + (shard_index * 13) % 7
            width = 1.0 + 0.35 * (shard_index % 5)
            polygon = [c - tangent * length * 0.55,
                       c - normal * width + tangent * 0.2,
                       c + tangent * length * 0.48,
                       c + normal * width * (0.55 + 0.1 * (shard_index % 3))]
            body = "emerald_shards_a" if (flight + step) % 5 < 3 else "ember_shards_b"
            _draw_poly(masks[body], polygon, 0.58 + 0.1 * (shard_index % 4), 1, True)
            _draw_poly(masks["bevel_fragments"], polygon, 1.0, 1, False)
            _draw_line(masks["stress_needles"], polygon[0], polygon[2], 1.0, 1)
            if shard_index % 2 == 0:
                _w16_segment(masks["scale_remnants"], c,
                             angle + 0.69, 2.0 + shard_index % 5,
                             1.0, 1, 0.4)
            if shard_index % 3 == 0:
                _w16_segment(masks["prism_slashes"], c + normal,
                             angle - 0.35, 3.0 + shard_index % 4,
                             1.0, 1, -0.5)
            if shard_index % 5 == 0:
                _w16_disc(masks["impact_chips"], c + tangent * length * 0.5,
                          1, 1.0, True)
            if shard_index % 7 == 0:
                _draw_line(masks["flight_shadows"], polygon[1] - normal,
                           polygon[3] - normal, 1.0, 2)
            if shard_index % 11 == 0:
                _w16_disc(masks["collision_sparks"], c - normal * 1.5,
                          1, 1.0, False)
            shard_index += 1
    banks = dict(emerald_shards_a="A", ember_shards_b="B",
                 bevel_fragments="B", stress_needles="N",
                 scale_remnants="A", prism_slashes="B", impact_chips="N",
                 flight_shadows="A", collision_sparks="B")
    tone = _norm(0.34 * np.sin(x / 59.0) + 0.29 * np.cos(y / 71.0)
                 + 0.24 * np.sin((x - 1.5 * y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_crackle_eyeshine_glass_w16() -> _Grammar:
    """Dense shear-driven branch cracks replace the Phoenix blob/noise field."""
    names = ("metal_lips_a", "clear_lips_b", "crack_cores",
             "branch_splinters", "pupil_shears", "tapetal_bridges",
             "bevel_chips", "relay_glints", "quenched_tips")
    masks = _new_marks(*names)
    x, y = _xy()
    for crack in range(1, 501):
        point = np.asarray([3.0 + 506.0 * _halton(crack, 2),
                            3.0 + 506.0 * _halton(crack, 23)], np.float32)
        heading = (0.62 * np.sin(point[0] / 83.0)
                   - 0.57 * np.cos(point[1] / 71.0)
                   + ((crack * 17) % 15 - 7) * 0.09)
        previous = point.copy()
        steps = 3 + (crack * 7) % 8
        for step in range(steps):
            heading += 0.23 * np.sin(crack * 1.7 + step * 2.1)
            length = 2.0 + (crack * 5 + step * 7) % 7
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            point = previous + tangent * length
            _draw_line(masks["crack_cores"], previous, point, 1.0, 1)
            lip_name = "metal_lips_a" if (crack + step) % 3 else "clear_lips_b"
            side = -1.0 if (crack + step) & 1 else 1.0
            _draw_line(masks[lip_name], previous + normal * side * 1.4,
                       point + normal * side * 1.2, 0.86, 2)
            if (crack + step) % 2 == 0:
                branch_angle = heading + side * (0.58 + 0.08 * ((crack + step) % 5))
                _, _, branch_tip = _w16_segment(masks["branch_splinters"],
                                                 point - tangent,
                                                 branch_angle,
                                                 2.0 + (crack + step) % 5,
                                                 1.0, 1, side * 0.4)
                if (crack + step) % 4 == 0:
                    _w16_disc(masks["bevel_chips"], branch_tip,
                              1, 1.0, True)
            if (crack + step) % 3 == 0:
                _w16_segment(masks["pupil_shears"], point,
                             heading + 1.2, 2.0 + step % 5,
                             1.0, 1, -0.4)
            if (crack + step) % 5 == 0:
                _w16_segment(masks["tapetal_bridges"], previous,
                             heading - 0.72, 3.0 + crack % 4,
                             1.0, 1, 0.6)
            if (crack + step) % 7 == 0:
                _w16_disc(masks["relay_glints"], point + normal,
                          1, 1.0, False)
            previous = point
        _w16_disc(masks["quenched_tips"], previous, 1 + crack % 2,
                  1.0, False)
    banks = dict(metal_lips_a="A", clear_lips_b="B", crack_cores="N",
                 branch_splinters="B", pupil_shears="A",
                 tapetal_bridges="B", bevel_chips="N", relay_glints="A",
                 quenched_tips="B")
    tone = _norm(0.39 * np.sin(x / 73.0) - 0.33 * np.cos(y / 89.0)
                 + 0.23 * np.sin((1.3 * x + y) / 47.0))
    return _pack(masks, banks, tone)


# W17 is the first cross-family correction after the W16 all-fine pass.  W16
# fixed scale but let several independent grammars converge into similar short
# stroke clouds.  W17 changes their primary process and visible silhouette;
# no seed/palette/crop substitution is considered a repair.


def _build_fc_quill_bristle_w17() -> _Grammar:
    """Magnetic dipole-grown armour of visibly faceted, noncongruent quills."""
    names = ("umber_quill_faces_a", "violet_quill_faces_b", "flux_spines",
             "collar_cuts", "asymmetric_barbs", "hollow_channels",
             "broken_nibs", "crossed_splinters", "root_scars")
    masks = _new_marks(*names)
    x, y = _xy()
    poles = ((-40.0, 90.0, 1.0), (118.0, -36.0, -0.8),
             (284.0, 548.0, 1.2), (552.0, 208.0, -1.1),
             (430.0, -44.0, 0.75), (-52.0, 412.0, -0.95),
             (592.0, 520.0, 0.62))
    for index in range(1, 2301):
        c = np.asarray([2.0 + 508.0 * _halton(index, 2),
                        2.0 + 508.0 * _halton(index, 5)], np.float32)
        vx = 0.0
        vy = 0.0
        for px, py, strength in poles:
            dx, dy = float(c[0] - px), float(c[1] - py)
            inv = strength / max(144.0, dx * dx + dy * dy)
            vx += inv * (dx * dx - dy * dy)
            vy += inv * (2.0 * dx * dy)
        flux_angle = float(np.arctan2(vy, vx))
        angle = (round(flux_angle / (np.pi / 4.0)) * (np.pi / 4.0)
                 + ((index * 7) % 7 - 3) * 0.035)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 4.0 + (index * 11) % 5
        half = 2.1 + 0.58 * (index % 4)
        root = c - tangent * length * 0.48
        tip = c + tangent * length * 0.52
        shoulder = c - tangent * (0.4 + 0.15 * (index % 3))
        if index % 3 == 0:
            polygon = [root - normal * half * 0.45,
                       shoulder - normal * half,
                       tip, shoulder + normal * half * 0.63,
                       root + normal * half * 0.25]
        elif index % 3 == 1:
            polygon = [root - normal * half * 0.75,
                       c - normal * half * 0.68,
                       tip, c + normal * half,
                       root + normal * half * 0.32]
        else:
            polygon = [root - normal * half * 0.5,
                       c - normal * half,
                       tip - normal * 0.2,
                       tip + normal * 0.35,
                       c + normal * half * 0.58,
                       root + normal * half * 0.2]
        body = "umber_quill_faces_a" if (index * 5) % 12 < 7 else "violet_quill_faces_b"
        _draw_poly(masks[body], polygon, 0.78 + 0.06 * (index % 4), 1, True)
        _draw_line(masks["flux_spines"], root, tip, 1.0, 1)
        _draw_line(masks["collar_cuts"], root - normal * half * 0.7,
                   root + normal * half * 0.65, 1.0, 1)
        if index % 2 == 0:
            anchor = c + tangent * length * 0.12
            side = -1.0 if index & 2 else 1.0
            _draw_line(masks["asymmetric_barbs"], anchor,
                       anchor - tangent * 1.0 + normal * side * (1.8 + index % 3),
                       1.0, 1)
        if index % 3 == 0:
            _draw_line(masks["hollow_channels"], root + tangent,
                       tip - tangent, 1.0, 1)
        if index % 5 == 0:
            _draw_line(masks["broken_nibs"], tip - tangent,
                       tip + normal * 1.4, 1.0, 1)
        if index % 7 == 0:
            _w16_segment(masks["crossed_splinters"], c + normal * 2.0,
                         angle + 1.08, 2.0 + index % 5, 1.0, 1, 0.4)
        if index % 11 == 0:
            cv2.ellipse(masks["root_scars"], tuple(np.rint(root).astype(int)),
                        (2 + index % 2, 1), float(np.degrees(angle)),
                        15, 175, 1.0, 1, cv2.LINE_AA)
    banks = dict(umber_quill_faces_a="A", violet_quill_faces_b="B",
                 flux_spines="N", collar_cuts="A", asymmetric_barbs="B",
                 hollow_channels="N", broken_nibs="B",
                 crossed_splinters="A", root_scars="B")
    tone = _norm(0.33 * np.sin(x / 73.0) - 0.3 * np.cos(y / 91.0)
                 + 0.26 * np.sin((x + y) / 47.0))
    return _pack(masks, banks, tone)


def _build_fc_coarse_hide_w17() -> _Grammar:
    """Fine elastic buckling from many local pressure contacts, not macro bars."""
    names = ("compression_rims_a", "release_rims_b", "buckling_crests",
             "saddle_shadows", "wrinkle_fingers", "scar_bridges",
             "sweat_ducts", "rubbed_cusps", "crossgrain_checks")
    x, y = _xy()
    # Solve the contact field on a bounded causal grid, then derive every
    # visible 2-8 work-pixel mark at 512.  The former 900 x 512² event loop
    # took ~11.6 s cold and violated the native preview budget.
    low = 192
    ly, lx = np.mgrid[0:low, 0:low].astype(np.float32)
    pressure_low = np.zeros((low, low), np.float32)
    shear_low = np.zeros_like(pressure_low)
    scale = low / float(_WORK)
    for event in range(1, 901):
        cx = (-12.0 + 536.0 * _halton(event, 2)) * scale
        cy = (-12.0 + 536.0 * _halton(event, 3)) * scale
        angle = 0.61 * event + 0.7 * np.sin(event * 1.3)
        ca, sa = np.cos(angle), np.sin(angle)
        dx, dy = lx - cx, ly - cy
        u = ca * dx + sa * dy
        v = -sa * dx + ca * dy
        major = (5.0 + (event * 13) % 6) * scale
        minor = (2.3 + (event * 7) % 4) * scale
        contact = np.exp(-(u * u / (major * major)
                           + v * v / (minor * minor))).astype(np.float32)
        pressure_low += contact * (0.52 + 0.06 * (event % 7))
        shear_low += contact * np.sin(u / ((2.2 + event % 3) * scale))
    pressure = cv2.resize(_norm(pressure_low), (_WORK, _WORK),
                          interpolation=cv2.INTER_CUBIC)
    shear = cv2.resize(shear_low, (_WORK, _WORK),
                       interpolation=cv2.INTER_CUBIC)
    pressure = _norm(pressure)
    lap = cv2.Laplacian(pressure, cv2.CV_32F, ksize=3)
    gx = cv2.Sobel(pressure, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(pressure, cv2.CV_32F, 0, 1, ksize=3)
    slope = _norm(np.hypot(gx, gy))
    pos = _f32((lap - 0.018) / 0.21)
    neg = _f32((-lap - 0.018) / 0.21)
    crests = _f32((slope - 0.18) / 0.52)
    shadow = _f32(cv2.GaussianBlur(crests, (0, 0), 1.7) - 0.31 * crests)
    fingers = _f32(crests * _line(np.sin((1.8 * x - 0.7 * y) / 3.1
                                         + shear * 2.7), 0.10))
    bridges = _f32(pos * _line(np.sin((x + 1.4 * y) / 5.3), 0.11))
    ducts = ((pressure >= cv2.dilate(pressure, np.ones((3, 3), np.uint8)) - 1e-5)
             .astype(np.float32) * _f32((pressure - 0.38) / 0.46))
    cusps = _f32(neg * _line(np.cos((2.1 * x + y) / 4.7), 0.095))
    checks = _f32(_line(np.sin((x - 2.0 * y) / 4.1 + lap * 3.0), 0.075)
                  * _f32((slope - 0.34) / 0.43))
    masks = dict(compression_rims_a=pos, release_rims_b=neg,
                 buckling_crests=crests, saddle_shadows=shadow,
                 wrinkle_fingers=fingers, scar_bridges=bridges,
                 sweat_ducts=ducts, rubbed_cusps=cusps,
                 crossgrain_checks=checks)
    banks = dict(compression_rims_a="A", release_rims_b="B",
                 buckling_crests="B", saddle_shadows="A",
                 wrinkle_fingers="N", scar_bridges="A", sweat_ducts="B",
                 rubbed_cusps="N", crossgrain_checks="B")
    return _pack(masks, banks, _norm(pressure + 0.2 * shear))


def _build_fc_eyeshine_w17() -> _Grammar:
    """Aperiodic, individually damaged corner-cube retroreflector cups."""
    names = ("gold_cube_faces_a", "violet_cube_faces_b", "third_cube_faces",
             "pupil_slits", "iris_ticks", "eyelid_crescents",
             "square_glints", "lash_combs", "cracked_corners")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1801):
        c = np.asarray([3.0 + 506.0 * _halton(index, 3),
                        3.0 + 506.0 * _halton(index, 7)], np.float32)
        rotation = (0.41 * np.sin(c[0] / 71.0)
                    - 0.33 * np.cos(c[1] / 83.0)
                    + index * 0.173)
        radius = 2.7 + 0.45 * ((index * 11) % 8)
        directions = [rotation,
                      rotation + _TAU / 3.0 + 0.09 * ((index * 7) % 7 - 3),
                      rotation + 2.0 * _TAU / 3.0
                      + 0.07 * ((index * 11) % 9 - 4)]
        rim = []
        for k, theta in enumerate(directions):
            rr = radius * (0.62 + 0.11 * ((index + k * 5) % 6))
            rim.append(c + np.asarray([np.cos(theta), np.sin(theta)],
                                      np.float32) * rr)
        centre_shift = c + np.asarray([np.cos(rotation + 0.61),
                                       np.sin(rotation + 0.61)], np.float32) \
            * (0.25 + 0.12 * (index % 5))
        _draw_poly(masks["gold_cube_faces_a"], [centre_shift, rim[0], rim[1]],
                   0.74 + 0.06 * (index % 4), 1, True)
        if index % 5 != 0:
            _draw_poly(masks["violet_cube_faces_b"],
                       [centre_shift, rim[1], rim[2]],
                       0.7 + 0.07 * ((index + 1) % 4), 1, True)
        if index % 3 != 0:
            _draw_poly(masks["third_cube_faces"],
                       [centre_shift, rim[2], rim[0]], 0.82, 1, True)
        slit_angle = rotation + (0.47 if index & 1 else -0.39)
        _w16_segment(masks["pupil_slits"], centre_shift, slit_angle,
                     2.0 + index % 5, 1.0, 1)
        if index % 2 == 0:
            for tick in (-1.0, 1.0):
                p = centre_shift + np.asarray([np.cos(rotation), np.sin(rotation)],
                                              np.float32) * tick * 1.4
                _w16_segment(masks["iris_ticks"], p, rotation + np.pi * 0.5,
                             2.0, 1.0, 1)
        if index % 3 == 0:
            cv2.ellipse(masks["eyelid_crescents"],
                        tuple(np.rint(c).astype(int)),
                        (max(2, int(radius)), max(1, int(radius * 0.55))),
                        float(np.degrees(rotation)), 195, 338, 1.0, 1,
                        cv2.LINE_AA)
        if index % 4 == 0:
            p = np.rint(centre_shift + np.asarray([1.1, -0.8])).astype(int)
            cv2.rectangle(masks["square_glints"], tuple(p - 1), tuple(p + 1),
                          1.0, -1, cv2.LINE_AA)
        if index % 7 == 0:
            for lash in range(3):
                anchor = rim[0] + (rim[1] - rim[0]) * (0.2 + lash * 0.27)
                _w16_segment(masks["lash_combs"], anchor,
                             rotation - 1.0, 2.0 + lash, 1.0, 1)
        if index % 11 == 0:
            _draw_line(masks["cracked_corners"], rim[1], centre_shift,
                       1.0, 1)
            _w16_segment(masks["cracked_corners"], rim[1],
                         rotation + 0.9, 2.0 + index % 4, 1.0, 1)
    banks = dict(gold_cube_faces_a="A", violet_cube_faces_b="B",
                 third_cube_faces="N", pupil_slits="N", iris_ticks="A",
                 eyelid_crescents="B", square_glints="A", lash_combs="B",
                 cracked_corners="N")
    tone = _norm(0.37 * np.sin(x / 61.0) + 0.29 * np.cos(y / 79.0)
                 + 0.23 * np.sin((x - y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_bog_murk_w17() -> _Grammar:
    """Overlapping torn scum rafts with attached vents, reeds and menisci."""
    names = ("peat_rafts_a", "oil_rafts_b", "plateau_menisci",
             "methane_mouths", "bacterial_folds", "reed_strokes",
             "wake_curls", "torn_edges", "silt_cups")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1601):
        c = np.asarray([2.0 + 508.0 * _halton(index, 5),
                        2.0 + 508.0 * _halton(index, 11)], np.float32)
        rotation = 0.39 * index + 0.32 * np.sin(c[0] / 73.0)
        radius = 2.7 + 0.22 * ((index * 13) % 7)
        vertices = 5 + index % 5
        pts = []
        for vertex in range(vertices):
            theta = rotation + _TAU * vertex / vertices
            rr = radius * (0.62 + 0.29 * np.sin(index * 1.7 + vertex * 2.3))
            pts.append(c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * rr)
        body = "peat_rafts_a" if (index * 7) % 15 < 8 else "oil_rafts_b"
        _draw_poly(masks[body], pts, 0.62 + 0.08 * (index % 5), 1, True)
        if index % 2 == 0:
            _draw_poly(masks["plateau_menisci"], pts, 1.0, 1, False)
        if index % 3 == 0:
            _w16_disc(masks["methane_mouths"], c,
                      1 + index % 2, 1.0, False)
        if index % 4 == 0:
            _w16_segment(masks["bacterial_folds"], c,
                         rotation + 0.28, 3.0 + index % 5,
                         1.0, 1, 0.75)
        if index % 5 == 0:
            _w16_segment(masks["reed_strokes"], c + np.asarray([1.5, 0.0]),
                         rotation + 1.12, 3.0 + index % 5,
                         1.0, 1, -0.45)
        if index % 7 == 0:
            cv2.ellipse(masks["wake_curls"], tuple(np.rint(c).astype(int)),
                        (2 + index % 4, 1 + index % 3),
                        float(np.degrees(rotation)), 45, 270, 1.0, 1,
                        cv2.LINE_AA)
        if index % 9 == 0:
            _w16_segment(masks["torn_edges"], pts[index % vertices],
                         rotation - 0.72, 2.0 + index % 5,
                         1.0, 1, 0.55)
        if index % 11 == 0:
            _w16_disc(masks["silt_cups"], c + np.asarray([-1.4, 1.1]),
                      1, 1.0, True)
    banks = dict(peat_rafts_a="A", oil_rafts_b="B", plateau_menisci="N",
                 methane_mouths="B", bacterial_folds="A", reed_strokes="N",
                 wake_curls="B", torn_edges="A", silt_cups="B")
    tone = _norm(0.33 * np.sin(x / 83.0) - 0.3 * np.cos(y / 67.0)
                 + 0.22 * np.sin((x + 1.2 * y) / 41.0))
    return _pack(masks, banks, tone)


def _build_fc_bark_camo_w17() -> _Grammar:
    """Chunky cambium splinters, lenticels and resin—not another hair field."""
    names = ("cork_sheets_a", "cambium_sheets_b", "deep_slits",
             "lifted_peel_lips", "lenticel_bars", "resin_drops",
             "fungal_bites", "weathered_checks", "char_flakes")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1401):
        c = np.asarray([3.0 + 506.0 * _halton(index, 7),
                        3.0 + 506.0 * _halton(index, 13)], np.float32)
        angle = (1.48 + 0.21 * np.sin(c[0] / 61.0)
                 + 0.17 * np.cos(c[1] / 79.0)
                 + ((index * 11) % 9 - 4) * 0.045)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 4.0 + (index * 7) % 5
        width = 2.8 + 0.52 * (index % 5)
        root = c - tangent * length * 0.5
        tip = c + tangent * length * 0.5
        polygon = [root - normal * width * 0.44,
                   c - tangent + normal * (-width + 0.3 * (index % 3)),
                   tip - normal * width * 0.26,
                   tip + normal * width * 0.38,
                   c + tangent + normal * width * 0.72,
                   root + normal * width * 0.24]
        body = "cork_sheets_a" if (index * 3) % 10 < 6 else "cambium_sheets_b"
        _draw_poly(masks[body], polygon, 0.74 + 0.06 * (index % 4), 1, True)
        _draw_line(masks["deep_slits"], root + tangent,
                   tip - tangent, 1.0, 1)
        _draw_line(masks["lifted_peel_lips"], polygon[1], polygon[2],
                   1.0, 1)
        if index % 2 == 0:
            _w16_segment(masks["lenticel_bars"], c,
                         angle + np.pi * 0.5, 2.0 + index % 5,
                         1.0, 1)
        if index % 3 == 0:
            _w16_disc(masks["resin_drops"], tip + normal,
                      1 + index % 2, 1.0, True)
        if index % 5 == 0:
            cv2.ellipse(masks["fungal_bites"], tuple(np.rint(c).astype(int)),
                        (2 + index % 3, 1 + index % 2),
                        float(np.degrees(angle)), 25, 190, 1.0, 1,
                        cv2.LINE_AA)
        if index % 7 == 0:
            _w16_segment(masks["weathered_checks"], c,
                         angle + 0.73, 3.0 + index % 5,
                         1.0, 1, -0.45)
        if index % 11 == 0:
            _w16_disc(masks["char_flakes"], root - normal,
                      1, 1.0, True)
    banks = dict(cork_sheets_a="A", cambium_sheets_b="B", deep_slits="N",
                 lifted_peel_lips="B", lenticel_bars="A", resin_drops="B",
                 fungal_bites="N", weathered_checks="A", char_flakes="B")
    tone = _norm(0.41 * np.sin(y / 47.0) + 0.23 * np.cos(x / 73.0)
                 + 0.18 * np.sin((x + y) / 31.0))
    return _pack(masks, banks, tone)


def _build_fc_feathered_wing_w17() -> _Grammar:
    """Overlapping asymmetric micro-vanes grown segment-by-segment."""
    names = ("violet_vane_faces_a", "cyan_vane_faces_b", "broken_rachises",
             "left_barb_trees", "right_barb_trees", "hooklet_crossbars",
             "downy_bases", "ocellus_notches", "snapped_tips")
    masks = _new_marks(*names)
    x, y = _xy()
    for vane in range(1, 431):
        point = np.asarray([3.0 + 506.0 * _halton(vane, 3),
                            3.0 + 506.0 * _halton(vane, 17)], np.float32)
        heading = (0.43 * np.sin(point[0] / 83.0)
                   - 0.37 * np.cos(point[1] / 71.0)
                   + ((vane * 11) % 13 - 6) * 0.07)
        steps = 3 + (vane * 5) % 5
        root = point.copy()
        previous = point.copy()
        for step in range(steps):
            heading += 0.11 * np.sin(vane * 1.3 + step * 2.1)
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 3.0 + (vane + step * 7) % 4
            point = previous + tangent * length
            _draw_line(masks["broken_rachises"], previous, point, 1.0, 1)
            left_tip = previous + tangent * (0.45 * length) + normal * (
                2.0 + (vane + step) % 4)
            right_tip = previous + tangent * (0.62 * length) - normal * (
                1.6 + (vane + 2 * step) % 4)
            _draw_line(masks["left_barb_trees"], previous, left_tip, 1.0, 1)
            _draw_line(masks["right_barb_trees"], previous, right_tip, 1.0, 1)
            face = "violet_vane_faces_a" if (vane + step) % 3 else "cyan_vane_faces_b"
            _draw_poly(masks[face], [previous, left_tip, point, right_tip],
                       0.52 + 0.1 * ((vane + step) % 4), 1, True)
            if (vane + step) % 2 == 0:
                _draw_line(masks["hooklet_crossbars"],
                           left_tip - normal * 1.2,
                           right_tip + normal * 1.0, 1.0, 1)
            if (vane + step) % 5 == 0:
                _w16_disc(masks["ocellus_notches"], previous + tangent * 1.5,
                          1, 1.0, False)
            previous = point
        if vane % 2 == 0:
            for fuzz in (-1.0, 0.0, 1.0):
                _w16_segment(masks["downy_bases"], root + np.asarray([fuzz, 0.0]),
                             heading + fuzz * 0.45, 2.0 + vane % 3,
                             1.0, 1, fuzz * 0.3)
        if vane % 3 == 0:
            _w16_segment(masks["snapped_tips"], point,
                         heading + (0.75 if vane & 1 else -0.68),
                         2.0 + vane % 4, 1.0, 1, 0.4)
    banks = dict(violet_vane_faces_a="A", cyan_vane_faces_b="B",
                 broken_rachises="N", left_barb_trees="A",
                 right_barb_trees="B", hooklet_crossbars="N",
                 downy_bases="A", ocellus_notches="B", snapped_tips="B")
    tone = _norm(0.34 * np.sin(x / 79.0) - 0.3 * np.cos(y / 67.0)
                 + 0.23 * np.sin((x - 1.2 * y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_dorsal_ridge_w17() -> _Grammar:
    """Many cropped osteoderm sawlines; each plate descends from a load chain."""
    names = ("bone_plate_faces_a", "ember_plate_faces_b", "load_spines",
             "alternating_saw_teeth", "osteon_pores", "ligament_slots",
             "abrasion_chips", "collision_crossbars", "shed_scute_tips")
    masks = _new_marks(*names)
    x, y = _xy()
    for chain in range(1, 501):
        point = np.asarray([3.0 + 506.0 * _halton(chain, 5),
                            3.0 + 506.0 * _halton(chain, 19)], np.float32)
        heading = (0.16 + 0.48 * np.sin(point[1] / 89.0)
                   + ((chain * 7) % 11 - 5) * 0.11)
        steps = 7 + (chain * 11) % 9
        previous = point.copy()
        for step in range(steps):
            heading += 0.13 * np.sin(chain * 0.9 + step * 1.7)
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 3.0 + (chain + step * 5) % 4
            point = previous + tangent * length
            side = -1.0 if (chain + step) & 1 else 1.0
            apex = (previous + point) * 0.5 + normal * side * (
                1.4 + 0.35 * ((chain + step) % 5))
            face = "bone_plate_faces_a" if (chain + 2 * step) % 5 < 3 else "ember_plate_faces_b"
            _draw_poly(masks[face], [previous - normal * 0.8, apex,
                                     point + normal * 0.55, (previous + point) * 0.5],
                       0.64 + 0.08 * ((chain + step) % 4), 1, True)
            _draw_line(masks["load_spines"], previous, point, 1.0, 1)
            _draw_line(masks["alternating_saw_teeth"], apex,
                       point - tangent * 0.7, 1.0, 1)
            if (chain + step) % 3 == 0:
                _w16_disc(masks["osteon_pores"], (previous + point) * 0.5,
                          1, 1.0, False)
            if (chain + step) % 4 == 0:
                _w16_segment(masks["ligament_slots"], previous,
                             heading + np.pi * 0.5, 2.0 + step % 4,
                             1.0, 1)
            if (chain + step) % 6 == 0:
                _w16_disc(masks["abrasion_chips"], apex, 1, 1.0, True)
            if (chain + step) % 9 == 0:
                _w16_segment(masks["collision_crossbars"], (previous + point) * 0.5,
                             heading + 1.08, 2.0 + chain % 5,
                             1.0, 1, -0.4)
            previous = point
        if chain % 3 == 0:
            _w16_segment(masks["shed_scute_tips"], point,
                         heading - 0.52, 2.0 + chain % 5,
                         1.0, 1, 0.5)
    banks = dict(bone_plate_faces_a="A", ember_plate_faces_b="B",
                 load_spines="N", alternating_saw_teeth="B",
                 osteon_pores="N", ligament_slots="A", abrasion_chips="B",
                 collision_crossbars="A", shed_scute_tips="B")
    tone = _norm(0.35 * np.sin(x / 71.0) + 0.27 * np.cos(y / 83.0)
                 + 0.22 * np.sin((x + 1.3 * y) / 41.0))
    return _pack(masks, banks, tone)


def _build_fc_webbed_membrane_w17() -> _Grammar:
    """Broken Airy-stress striae and local vascular forks, no macro lobes."""
    names = ("tensile_striae_a", "compressive_striae_b", "membrane_wrinkles",
             "capillary_stems", "capillary_forks", "node_pads",
             "tear_windows", "elastic_bridges", "dew_beads")
    x, y = _xy()
    airy = (np.sin(x / 19.0 + 0.31 * np.sin(y / 47.0))
            + 0.72 * np.cos(y / 23.0 - 0.27 * np.cos(x / 53.0))
            + 0.31 * np.sin((x - y) / 31.0))
    gx = cv2.Sobel(airy.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(airy.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    dash_a = _f32((np.cos((0.8 * x - 1.2 * y) / 5.1) - 0.1) / 0.9)
    dash_b = _f32((np.sin((1.3 * x + 0.6 * y) / 6.3) + 0.08) / 0.92)
    tensile = _f32(_line(airy - 0.42, 0.12) * dash_a
                   + _line(airy + 0.88, 0.10) * dash_b)
    compressive = _f32(_line(airy + 0.37, 0.12) * dash_b
                       + _line(airy - 0.93, 0.10) * dash_a)
    wrinkles = _f32(_line(np.sin((gx * y - gy * x) / 7.1), 0.095)
                     * _f32((np.hypot(gx, gy) - 0.02) / 0.15))
    stems = np.zeros((_WORK, _WORK), np.float32)
    forks = np.zeros_like(stems)
    pads = np.zeros_like(stems)
    windows = np.zeros_like(stems)
    bridges = np.zeros_like(stems)
    dew = np.zeros_like(stems)
    for index in range(1, 851):
        c = np.asarray([2.0 + 508.0 * _halton(index, 7),
                        2.0 + 508.0 * _halton(index, 11)], np.float32)
        angle = (0.51 * np.sin(c[0] / 73.0) - 0.44 * np.cos(c[1] / 89.0)
                 + ((index * 5) % 7 - 3) * 0.07)
        root, middle, tip = _w16_segment(stems, c, angle,
                                          3.0 + index % 5, 1.0, 1,
                                          0.45 * np.sin(index))
        if index % 2 == 0:
            side = -1.0 if index & 2 else 1.0
            _w16_segment(forks, tip, angle + side * 0.68,
                         2.0 + index % 4, 1.0, 1, side * 0.35)
        if index % 3 == 0:
            _w16_disc(pads, root, 1, 1.0, True)
        if index % 5 == 0:
            cv2.ellipse(windows, tuple(np.rint(c).astype(int)),
                        (2 + index % 4, 1 + index % 2),
                        float(np.degrees(angle)), 35, 280, 1.0, 1,
                        cv2.LINE_AA)
        if index % 7 == 0:
            _w16_segment(bridges, middle, angle + 1.14,
                         2.0 + index % 5, 1.0, 1, -0.5)
        if index % 11 == 0:
            _w16_disc(dew, tip + np.asarray([1.0, -1.0]),
                      1, 1.0, False)
    masks = dict(tensile_striae_a=tensile, compressive_striae_b=compressive,
                 membrane_wrinkles=wrinkles, capillary_stems=stems,
                 capillary_forks=forks, node_pads=pads,
                 tear_windows=windows, elastic_bridges=bridges,
                 dew_beads=dew)
    banks = dict(tensile_striae_a="A", compressive_striae_b="B",
                 membrane_wrinkles="N", capillary_stems="B",
                 capillary_forks="A", node_pads="B", tear_windows="N",
                 elastic_bridges="A", dew_beads="B")
    return _pack(masks, banks, _norm(airy + 0.2 * gx - 0.17 * gy))


def _build_fc_toad_skin_w17() -> _Grammar:
    """Edge-to-edge mixed poison glands with seven noncongruent anatomies."""
    names = ("olive_gland_bodies_a", "warning_gland_bodies_b", "poison_pores",
             "mucus_crescents", "thorn_warts", "capillary_forks",
             "dry_collar_checks", "paired_micro_pits", "shed_lobes")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 2451):
        u = np.mod(index * 1.4142135623730951
                   + 0.23 * np.sin(index * 1.7320508075688772), 1.0)
        v = np.mod(index * 2.23606797749979
                   + 0.19 * np.sin(index * 2.6457513110645907 + 0.31), 1.0)
        c = np.asarray([2.0 + 508.0 * u, 2.0 + 508.0 * v], np.float32)
        radius = 1.45 + 0.4 * ((index * 11) % 8)
        lobes = 3 + (index * 7) % 6
        rotation = index * 0.293 + 0.27 * np.sin(c[0] / 71.0)
        pts = []
        for vertex in range(lobes * 2):
            theta = rotation + _TAU * vertex / (lobes * 2.0)
            rr = radius * (1.0 if vertex % 2 == 0 else
                           0.48 + 0.08 * ((index + vertex) % 4))
            pts.append(c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * rr)
        body = "olive_gland_bodies_a" if (index * 5) % 13 < 7 else "warning_gland_bodies_b"
        _draw_poly(masks[body], pts, 0.72 + 0.07 * (index % 4), 1, True)
        if index % 2 == 0:
            _w16_disc(masks["poison_pores"], c, 1, 1.0, False)
        if index % 3 == 0:
            cv2.ellipse(masks["mucus_crescents"], tuple(np.rint(c).astype(int)),
                        (max(2, int(radius + 1)), max(1, int(radius * 0.65 + 1))),
                        float(np.degrees(rotation)), 190, 345, 1.0, 1,
                        cv2.LINE_AA)
        if index % 4 == 0:
            theta = rotation + (index % lobes) * _TAU / lobes
            tip = c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * radius
            _w16_segment(masks["thorn_warts"], tip, theta,
                         2.0 + index % 3, 1.0, 1, 0.3)
        if index % 5 == 0:
            _w16_segment(masks["capillary_forks"], c,
                         rotation + 0.8, 2.0 + index % 5,
                         1.0, 1, -0.45)
        if index % 7 == 0:
            _w16_segment(masks["dry_collar_checks"], c,
                         rotation + 1.3, 3.0 + index % 4,
                         1.0, 1, 0.5)
        if index % 9 == 0:
            for side in (-1.0, 1.0):
                _w16_disc(masks["paired_micro_pits"],
                          c + np.asarray([side * 1.2, 0.0]),
                          1, 1.0, True)
        if index % 13 == 0:
            _w16_segment(masks["shed_lobes"], pts[index % len(pts)],
                         rotation - 0.6, 2.0 + index % 5,
                         1.0, 1, 0.7)
    banks = dict(olive_gland_bodies_a="A", warning_gland_bodies_b="B",
                 poison_pores="N", mucus_crescents="B", thorn_warts="A",
                 capillary_forks="N", dry_collar_checks="A",
                 paired_micro_pits="B", shed_lobes="B")
    tone = _norm(0.31 * np.sin(x / 67.0) + 0.28 * np.cos(y / 83.0)
                 + 0.24 * np.sin((x + y) / 41.0))
    return _pack(masks, banks, tone)


def _build_fc_antler_bone_w17() -> _Grammar:
    """Connected load-path trabeculae replace independent blurred bone rods."""
    names = ("dense_load_lips_a", "open_load_lips_b", "trabecular_trunks",
             "mineral_branches", "lamella_crossbars", "marrow_canals",
             "resorption_bays", "calcified_junctions", "weathered_ends")
    masks = _new_marks(*names)
    x, y = _xy()
    for tree in range(1, 361):
        point = np.asarray([2.0 + 508.0 * _halton(tree, 3),
                            2.0 + 508.0 * _halton(tree, 23)], np.float32)
        heading = (0.35 * np.sin(point[1] / 83.0)
                   + 0.28 * np.cos(point[0] / 71.0)
                   + ((tree * 13) % 11 - 5) * 0.12)
        previous = point.copy()
        steps = 6 + (tree * 7) % 9
        for step in range(steps):
            heading += 0.15 * np.sin(tree * 1.1 + step * 1.9)
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 3.0 + (tree + step * 5) % 4
            point = previous + tangent * length
            _draw_line(masks["trabecular_trunks"], previous, point, 1.0,
                       2 if (tree + step) % 17 == 0 else 1)
            lip = "dense_load_lips_a" if (tree + step) % 4 < 3 else "open_load_lips_b"
            side = -1.0 if (tree + step) & 1 else 1.0
            _draw_line(masks[lip], previous + normal * side * 1.3,
                       point + normal * side * 1.1, 0.86, 2)
            if (tree + step) % 2 == 0:
                branch_heading = heading + side * (0.55 + 0.08 * ((tree + step) % 5))
                _w16_segment(masks["mineral_branches"], point - tangent,
                             branch_heading, 2.0 + (tree + step) % 5,
                             1.0, 1, side * 0.35)
            if (tree + step) % 3 == 0:
                _w16_segment(masks["lamella_crossbars"], (previous + point) * 0.5,
                             heading + np.pi * 0.5, 2.0 + step % 4,
                             1.0, 1)
            if (tree + step) % 5 == 0:
                _w16_disc(masks["marrow_canals"], previous + normal,
                          1, 1.0, False)
            if (tree + step) % 7 == 0:
                cv2.ellipse(masks["resorption_bays"],
                            tuple(np.rint(point + normal * 1.5).astype(int)),
                            (2 + step % 3, 1 + tree % 2),
                            float(np.degrees(heading)), 30, 235, 1.0, 1,
                            cv2.LINE_AA)
            if (tree + step) % 11 == 0:
                _w16_disc(masks["calcified_junctions"], point,
                          1 + tree % 2, 1.0, True)
            previous = point
        if tree % 3 == 0:
            _w16_segment(masks["weathered_ends"], point,
                         heading - 0.72, 2.0 + tree % 5,
                         1.0, 1, 0.55)
    banks = dict(dense_load_lips_a="A", open_load_lips_b="B",
                 trabecular_trunks="N", mineral_branches="B",
                 lamella_crossbars="A", marrow_canals="N",
                 resorption_bays="B", calcified_junctions="A",
                 weathered_ends="B")
    tone = _norm(0.36 * np.sin(x / 89.0) - 0.29 * np.cos(y / 73.0)
                 + 0.21 * np.sin((x - y) / 47.0))
    return _pack(masks, banks, tone)


def _build_fc_mossy_stone_w17() -> _Grammar:
    """Distributed collision chips with foliose lichen attachment—no fault hub."""
    names = ("slate_chips_a", "wet_chips_b", "collision_seams",
             "bevel_cusps", "foliose_lichen", "soredia_cups",
             "moisture_threads", "quartz_needles", "moss_rhizoids")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 2101):
        c = np.asarray([2.0 + 508.0 * _halton(index, 11),
                        2.0 + 508.0 * _halton(index, 17)], np.float32)
        rotation = 0.47 * index + 0.29 * np.sin(c[1] / 83.0)
        radius = 2.45 + 0.22 * ((index * 7) % 8)
        vertices = 3 + (index * 5) % 5
        pts = []
        for vertex in range(vertices):
            theta = rotation + _TAU * vertex / vertices
            rr = radius * (0.58 + 0.35 * np.sin(index * 1.1 + vertex * 2.7))
            pts.append(c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * rr)
        body = "slate_chips_a" if (index * 5) % 13 < 7 else "wet_chips_b"
        _draw_poly(masks[body], pts, 0.66 + 0.08 * (index % 4), 1, True)
        if index % 2 == 0:
            _draw_line(masks["collision_seams"], pts[0], pts[vertices // 2],
                       1.0, 1)
        if index % 3 == 0:
            _draw_line(masks["bevel_cusps"], pts[1], pts[2 % vertices],
                       1.0, 1)
        if index % 4 == 0:
            side = -1.0 if index & 1 else 1.0
            cv2.ellipse(masks["foliose_lichen"],
                        tuple(np.rint(c + np.asarray([side, -side])).astype(int)),
                        (2 + index % 4, 1 + index % 3),
                        float(np.degrees(rotation)), 20, 285, 1.0, 2,
                        cv2.LINE_AA)
        if index % 5 == 0:
            _w16_disc(masks["soredia_cups"], c, 1, 1.0, False)
        if index % 7 == 0:
            _w16_segment(masks["moisture_threads"], c,
                         rotation + 0.62, 3.0 + index % 5,
                         1.0, 1, 0.65)
        if index % 9 == 0:
            _w16_segment(masks["quartz_needles"], pts[-1],
                         rotation - 0.38, 2.0 + index % 5,
                         1.0, 1)
        if index % 11 == 0:
            for branch in (-1.0, 1.0):
                _w16_segment(masks["moss_rhizoids"], c,
                             rotation + branch * 0.9,
                             2.0 + index % 4, 1.0, 1, branch * 0.45)
    banks = dict(slate_chips_a="A", wet_chips_b="B", collision_seams="N",
                 bevel_cusps="B", foliose_lichen="A", soredia_cups="B",
                 moisture_threads="A", quartz_needles="N", moss_rhizoids="B")
    tone = _norm(0.34 * np.sin(x / 71.0) + 0.29 * np.cos(y / 91.0)
                 + 0.22 * np.sin((x + 1.4 * y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_snakeskin_w17() -> _Grammar:
    """Overlapping broken zipper chains carry belly, keel and shed anatomy."""
    names = ("belly_faces_a", "keel_faces_b", "hinge_seams",
             "alternating_chevrons", "pit_organs", "overlap_lips",
             "shed_tears", "friction_files", "weathered_points")
    masks = _new_marks(*names)
    x, y = _xy()
    for chain in range(1, 1601):
        u = np.mod(chain * 1.4142135623730951
                   + 0.19 * np.sin(chain * 2.2360679775), 1.0)
        v = np.mod(chain * 1.7320508075688772
                   + 0.17 * np.sin(chain * 2.4494897428 + 0.37), 1.0)
        point = np.asarray([2.0 + 508.0 * u, 2.0 + 508.0 * v], np.float32)
        heading = (0.12 + 0.92 * np.sin(chain * 0.7548776662)
                   + 0.24 * np.sin(point[1] / 73.0)
                   + 0.16 * np.cos(point[0] / 89.0)
                   + ((chain * 11) % 9 - 4) * 0.055)
        steps = 1 + int(_halton(chain, 13) * 3.0)
        previous = point.copy()
        for step in range(steps):
            heading += 0.08 * np.sin(chain * 1.3 + step * 1.7)
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 3.0 + (chain + step * 7) % 4
            point = previous + tangent * length
            side = -1.0 if (chain + step) & 1 else 1.0
            apex = (previous + point) * 0.5 + normal * side * (
                1.5 + 0.3 * ((chain + step) % 5))
            body = "belly_faces_a" if (chain + step) % 5 < 3 else "keel_faces_b"
            _draw_poly(masks[body], [previous, apex, point,
                                     (previous + point) * 0.5 - normal * side * 0.5],
                       0.65 + 0.08 * ((chain + step) % 4), 1, True)
            _draw_line(masks["hinge_seams"], previous, point, 1.0, 1)
            _draw_line(masks["alternating_chevrons"], previous, apex, 1.0, 1)
            _draw_line(masks["alternating_chevrons"], apex, point, 1.0, 1)
            if (chain + step) % 3 == 0:
                _w16_disc(masks["pit_organs"], apex, 1, 1.0, False)
            if (chain + step) % 4 == 0:
                _draw_line(masks["overlap_lips"], apex,
                           point - tangent * 0.7, 1.0, 2)
            if (chain + step) % 5 == 0:
                _w16_segment(masks["shed_tears"], apex,
                             heading + side * 0.82,
                             2.0 + step % 5, 1.0, 1, side * 0.4)
            if (chain + step) % 7 == 0:
                _w16_segment(masks["friction_files"], (previous + point) * 0.5,
                             heading + np.pi * 0.5, 2.0 + chain % 4,
                             1.0, 1)
            previous = point
        if chain % 3 == 0:
            _w16_disc(masks["weathered_points"], point,
                      1, 1.0, True)
    banks = dict(belly_faces_a="A", keel_faces_b="B", hinge_seams="N",
                 alternating_chevrons="B", pit_organs="N", overlap_lips="A",
                 shed_tears="B", friction_files="A", weathered_points="B")
    tone = _norm(0.37 * np.sin(x / 83.0) + 0.25 * np.cos(y / 67.0)
                 + 0.21 * np.sin((x - 1.2 * y) / 41.0))
    return _pack(masks, banks, tone)


def _build_fc_batwing_w17() -> _Grammar:
    """Aperiodic kirigami slit folds replace another short-stroke flow field."""
    names = ("mountain_flaps_a", "valley_flaps_b", "kirigami_slits",
             "hinge_bars", "capillary_arcs", "echo_scratches",
             "membrane_pores", "torn_corners", "crease_glints")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 2601):
        c = np.asarray([3.0 + 506.0 * _halton(index, 13),
                        3.0 + 506.0 * _halton(index, 19)], np.float32)
        raw_angle = (0.64 * np.sin(c[0] / 97.0)
                     - 0.49 * np.cos(c[1] / 79.0))
        angle = (round(raw_angle / (np.pi / 3.0)) * (np.pi / 3.0)
                 + ((index * 7) % 13 - 6) * 0.035)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 4.0 + (index * 11) % 5
        half = 2.4 + 0.48 * (index % 4)
        root = c - tangent * length * 0.5
        tip = c + tangent * length * 0.5
        fold = c + normal * ((-1.0 if index & 1 else 1.0) * half)
        body = "mountain_flaps_a" if (index * 5) % 11 < 6 else "valley_flaps_b"
        _draw_poly(masks[body], [root - normal * 0.5, fold,
                                 tip + normal * 0.35, c - normal * 0.6],
                   0.7 + 0.07 * (index % 4), 1, True)
        _draw_poly(masks["crease_glints"], [root, fold, tip],
                   0.46 + 0.05 * (index % 3), 1, True)
        _draw_line(masks["kirigami_slits"], root, tip, 1.0, 1)
        _draw_line(masks["hinge_bars"], root - normal * 1.2,
                   root + normal * 1.2, 1.0, 1)
        if index % 2 == 0:
            cv2.ellipse(masks["capillary_arcs"], tuple(np.rint(c).astype(int)),
                        (2 + index % 4, 1 + index % 2),
                        float(np.degrees(angle)), 25, 210, 1.0, 1,
                        cv2.LINE_AA)
        if index % 3 == 0:
            _w16_segment(masks["echo_scratches"], fold,
                         angle + 0.92, 2.0 + index % 5,
                         1.0, 1, -0.45)
        if index % 5 == 0:
            _w16_disc(masks["membrane_pores"], c - normal,
                      1, 1.0, False)
        if index % 7 == 0:
            _w16_segment(masks["torn_corners"], tip,
                         angle - 0.68, 2.0 + index % 4,
                         1.0, 1, 0.65)
        if index % 11 == 0:
            _w16_disc(masks["crease_glints"], fold,
                      1, 1.0, True)
    banks = dict(mountain_flaps_a="A", valley_flaps_b="B",
                 kirigami_slits="N", hinge_bars="A", capillary_arcs="B",
                 echo_scratches="N", membrane_pores="B", torn_corners="A",
                 crease_glints="N")
    tone = _norm(0.35 * np.sin(x / 91.0) - 0.31 * np.cos(y / 73.0)
                 + 0.22 * np.sin((x + y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_hide_scale_glass_w17() -> _Grammar:
    """Broad enough biconvex Fresnel splinters to read as lenses, not hair."""
    names = ("amber_lens_backs_a", "green_lens_fronts_b", "convex_rims",
             "focal_caustics", "stress_veins", "dermal_pores",
             "occlusion_shadows", "scuff_crescents", "prism_glints")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 1501):
        c = np.asarray([3.0 + 506.0 * _halton(index, 5),
                        3.0 + 506.0 * _halton(index, 37)], np.float32)
        angle = (0.46 * np.sin(c[0] / 83.0) - 0.42 * np.cos(c[1] / 71.0)
                 + ((index * 11) % 9 - 4) * 0.08)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 4.0 + (index * 13) % 5
        width = 2.6 + 0.38 * (index % 5)
        root = c - tangent * length * 0.5
        tip = c + tangent * length * 0.5
        polygon = [root,
                   c - normal * width + tangent * 0.4,
                   tip,
                   c + normal * width * (0.72 + 0.08 * (index % 3))]
        body = "amber_lens_backs_a" if (index * 7) % 15 < 8 else "green_lens_fronts_b"
        _draw_poly(masks[body], polygon, 0.72 + 0.06 * (index % 4), 1, True)
        _draw_poly(masks["convex_rims"], polygon, 1.0, 1, False)
        _draw_line(masks["focal_caustics"], root + tangent,
                   tip - tangent, 1.0, 1)
        if index % 2 == 0:
            _w16_segment(masks["stress_veins"], c,
                         angle + np.pi * 0.5, 2.0 + index % 5,
                         1.0, 1, 0.45)
        if index % 3 == 0:
            _w16_disc(masks["dermal_pores"], c - normal * 0.8,
                      1, 1.0, False)
        if index % 5 == 0:
            _draw_line(masks["occlusion_shadows"], polygon[2], polygon[3],
                       1.0, 2)
        if index % 7 == 0:
            cv2.ellipse(masks["scuff_crescents"], tuple(np.rint(c).astype(int)),
                        (max(2, int(length * 0.5)), max(1, int(width * 0.55))),
                        float(np.degrees(angle)), 200, 330, 1.0, 1,
                        cv2.LINE_AA)
        if index % 11 == 0:
            _w16_disc(masks["prism_glints"], tip, 1, 1.0, True)
    banks = dict(amber_lens_backs_a="A", green_lens_fronts_b="B",
                 convex_rims="B", focal_caustics="N", stress_veins="A",
                 dermal_pores="N", occlusion_shadows="B",
                 scuff_crescents="A", prism_glints="B")
    tone = _norm(0.4 * np.sin(x / 79.0) - 0.3 * np.cos(y / 89.0)
                 + 0.22 * np.sin((x + 1.3 * y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_dragon_hex_glass_w17() -> _Grammar:
    """Distributed collision-born scale shards; no exposed ballistic tracks."""
    names = ("emerald_scale_shards_a", "ember_scale_shards_b", "glass_bevels",
             "mountain_folds", "valley_folds", "stress_needles",
             "scale_teeth", "impact_cusps", "caustic_sparks")
    masks = _new_marks(*names)
    x, y = _xy()
    for index in range(1, 3001):
        # Each sample is one independently timed collision fragment.  The
        # ballistic state determines orientation/asymmetry, but no shared
        # source path or trajectory is rendered.
        c = np.asarray([3.0 + 506.0 * _halton(index, 2),
                        3.0 + 506.0 * _halton(index, 41)], np.float32)
        vx = -1.0 + 2.0 * _halton(index, 5)
        vy = -1.0 + 2.0 * _halton(index, 7)
        time = 0.35 + 1.3 * _halton(index, 11)
        angle = float(np.arctan2(vy + 0.27 * time, vx - 0.19 * time))
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        length = 3.0 + (index * 13) % 6
        width = 2.2 + 0.42 * (index % 5)
        spin = (-1.0 if index & 1 else 1.0) * (0.4 + 0.2 * (index % 4))
        polygon = [c - tangent * length * 0.55,
                   c - normal * width + tangent * spin,
                   c + tangent * length * 0.48,
                   c + normal * width * 0.72 - tangent * spin * 0.4]
        body = "emerald_scale_shards_a" if (index * 5) % 12 < 7 else "ember_scale_shards_b"
        _draw_poly(masks[body], polygon, 0.68 + 0.07 * (index % 4), 1, True)
        _draw_poly(masks["glass_bevels"], polygon, 1.0, 1, False)
        _draw_line(masks["mountain_folds"], polygon[0], polygon[2], 1.0, 1)
        _draw_line(masks["valley_folds"], polygon[1], polygon[3], 1.0, 1)
        if index % 2 == 0:
            _w16_segment(masks["stress_needles"], c,
                         angle + 0.67, 2.0 + index % 5,
                         1.0, 1, 0.45)
        if index % 3 == 0:
            _w16_segment(masks["scale_teeth"], polygon[2],
                         angle + (0.82 if index & 2 else -0.74),
                         2.0 + index % 4, 1.0, 1, 0.35)
        if index % 5 == 0:
            _w16_disc(masks["impact_cusps"], polygon[0],
                      1, 1.0, True)
        if index % 7 == 0:
            _w16_disc(masks["caustic_sparks"], c + normal,
                      1, 1.0, False)
    banks = dict(emerald_scale_shards_a="A", ember_scale_shards_b="B",
                 glass_bevels="N", mountain_folds="A", valley_folds="N",
                 stress_needles="B", scale_teeth="A", impact_cusps="N",
                 caustic_sparks="B")
    tone = _norm(0.36 * np.sin(x / 73.0) + 0.28 * np.cos(y / 83.0)
                 + 0.23 * np.sin((x - 1.4 * y) / 41.0))
    return _pack(masks, banks, tone)


def _build_fc_bog_murk_w18() -> _Grammar:
    """Short advected scum-raft chains replace another uniform dot carpet."""
    names = ("peat_raft_faces_a", "oil_raft_faces_b", "meniscus_edges",
             "methane_vents", "bacterial_wrinkles", "reed_splinters",
             "wake_crescents", "torn_scum_lips", "silt_pockets")
    masks = _new_marks(*names)
    x, y = _xy()
    for chain in range(1, 3001):
        u = np.mod(chain * 1.4142135623730951
                   + 0.21 * np.sin(chain * 2.6457513111), 1.0)
        v = np.mod(chain * 2.23606797749979
                   + 0.18 * np.sin(chain * 1.7320508076 + 0.29), 1.0)
        point = np.asarray([3.0 + 506.0 * u, 3.0 + 506.0 * v], np.float32)
        heading = (0.51 * np.sin(point[0] / 83.0)
                   - 0.46 * np.cos(point[1] / 71.0)
                   + ((chain * 7) % 11 - 5) * 0.08)
        steps = 1
        for step in range(steps):
            heading += 0.17 * np.sin(chain * 1.3 + step * 1.9)
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            point = point + tangent * (3.0 + (chain + step) % 4)
            radius = 2.0 + 0.32 * ((chain + step * 5) % 6)
            vertices = 5 + (chain + step) % 4
            pts = []
            for vertex in range(vertices):
                theta = heading + _TAU * vertex / vertices
                rr = radius * (0.58 + 0.32 * np.sin(chain + step * 1.7
                                                    + vertex * 2.1))
                pts.append(point + np.asarray([np.cos(theta), np.sin(theta)],
                                              np.float32) * rr)
            body = "peat_raft_faces_a" if (chain + 2 * step) % 5 < 3 else "oil_raft_faces_b"
            _draw_poly(masks[body], pts,
                       0.68 + 0.08 * ((chain + step) % 4), 1, True)
            _draw_poly(masks["meniscus_edges"], pts, 1.0, 1, False)
            if (chain + step) % 2 == 0:
                _w16_disc(masks["methane_vents"], point,
                          1, 1.0, False)
            if (chain + step) % 3 == 0:
                _w16_segment(masks["bacterial_wrinkles"], point,
                             heading + 0.31, 2.0 + step % 5,
                             1.0, 1, 0.6)
            if (chain + step) % 4 == 0:
                _w16_segment(masks["reed_splinters"], point + normal,
                             heading + 1.07, 2.0 + chain % 5,
                             1.0, 1, -0.4)
            if (chain + step) % 5 == 0:
                cv2.ellipse(masks["wake_crescents"],
                            tuple(np.rint(point - tangent * 1.5).astype(int)),
                            (2 + step % 3, 1 + chain % 2),
                            float(np.degrees(heading)), 35, 265, 1.0, 1,
                            cv2.LINE_AA)
            if (chain + step) % 7 == 0:
                _w16_segment(masks["torn_scum_lips"], pts[-1],
                             heading - 0.74, 2.0 + step % 4,
                             1.0, 1, 0.55)
            if (chain + step) % 11 == 0:
                _w16_disc(masks["silt_pockets"], point - normal,
                          1, 1.0, True)
    banks = dict(peat_raft_faces_a="A", oil_raft_faces_b="B",
                 meniscus_edges="N", methane_vents="B",
                 bacterial_wrinkles="A", reed_splinters="N",
                 wake_crescents="B", torn_scum_lips="A", silt_pockets="B")
    tone = _norm(0.34 * np.sin(x / 79.0) - 0.29 * np.cos(y / 67.0)
                 + 0.23 * np.sin((x + 1.3 * y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_bark_camo_w18() -> _Grammar:
    """Broken local peel chains create bark streaks without card-length lanes."""
    names = ("cork_peels_a", "cambium_peels_b", "grain_slits",
             "lifted_lips", "lenticel_crossbars", "resin_beads",
             "fungal_bites", "weather_checks", "charred_tips")
    masks = _new_marks(*names)
    x, y = _xy()
    for chain in range(1, 1301):
        point = np.asarray([3.0 + 506.0 * _halton(chain, 2),
                            3.0 + 506.0 * _halton(chain, 3)], np.float32)
        heading = (1.48 + 0.52 * np.sin(point[0] / 23.0)
                   + 0.31 * np.cos(point[1] / 29.0)
                   + ((chain * 11) % 9 - 4) * 0.045)
        steps = 1 + int(_halton(chain, 11) * 3.0)
        for step in range(steps):
            heading += 0.08 * np.sin(chain * 1.1 + step * 1.7)
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 4.0 + (chain + step * 7) % 5
            width = 2.0 + 0.35 * ((chain + step) % 5)
            centre = point + tangent * length * 0.52
            root = point
            tip = point + tangent * length
            polygon = [root - normal * width * 0.32,
                       centre - normal * width,
                       tip - normal * width * 0.18,
                       tip + normal * width * 0.44,
                       centre + normal * width * 0.68,
                       root + normal * width * 0.22]
            body = "cork_peels_a" if (chain + step) % 5 < 3 else "cambium_peels_b"
            _draw_poly(masks[body], polygon,
                       0.71 + 0.07 * ((chain + step) % 4), 1, True)
            _draw_line(masks["grain_slits"], root + tangent,
                       tip - tangent, 1.0, 1)
            _draw_line(masks["lifted_lips"], polygon[1], polygon[2], 1.0, 1)
            if (chain + step) % 2 == 0:
                _w16_segment(masks["lenticel_crossbars"], centre,
                             heading + np.pi * 0.5, 2.0 + step % 4,
                             1.0, 1)
            if (chain + step) % 3 == 0:
                _w16_disc(masks["resin_beads"], tip + normal,
                          1, 1.0, True)
            if (chain + step) % 5 == 0:
                cv2.ellipse(masks["fungal_bites"],
                            tuple(np.rint(centre).astype(int)),
                            (2 + step % 3, 1 + chain % 2),
                            float(np.degrees(heading)), 30, 210, 1.0, 1,
                            cv2.LINE_AA)
            if (chain + step) % 7 == 0:
                _w16_segment(masks["weather_checks"], centre,
                             heading + 0.82, 2.0 + step % 5,
                             1.0, 1, -0.45)
            if (chain + step) % 11 == 0:
                _w16_disc(masks["charred_tips"], root - normal,
                          1, 1.0, True)
            point = tip
    banks = dict(cork_peels_a="A", cambium_peels_b="B", grain_slits="N",
                 lifted_lips="B", lenticel_crossbars="A", resin_beads="B",
                 fungal_bites="N", weather_checks="A", charred_tips="B")
    tone = _norm(0.42 * np.sin(y / 53.0) + 0.21 * np.cos(x / 79.0)
                 + 0.18 * np.sin((x + y) / 37.0))
    return _pack(masks, banks, tone)


def _build_fc_mossy_stone_w18() -> _Grammar:
    """Noncongruent foliose lichen colonies attach to small basalt hosts."""
    names = ("slate_hosts_a", "wet_hosts_b", "basalt_bevels",
             "foliose_lobes", "soredia_cups", "moisture_channels",
             "quartz_needles", "moss_rhizoids", "spalled_corners")
    masks = _new_marks(*names)
    x, y = _xy()
    for colony in range(1, 1801):
        u = np.mod(colony * 0.7548776662466927, 1.0)
        v = np.mod(colony * 0.5698402909980532
                   + 0.17 * np.sin(colony * 0.61803398875), 1.0)
        c = np.asarray([3.0 + 506.0 * u, 3.0 + 506.0 * v], np.float32)
        rotation = (0.58 * np.sin(c[0] / 37.0)
                    - 0.43 * np.cos(c[1] / 41.0)
                    + 0.21 * np.sin((c[0] + c[1]) / 53.0))
        radius = 2.2 + 0.35 * ((colony * 7) % 6)
        vertices = 3 + colony % 4
        host = []
        for vertex in range(vertices):
            theta = rotation + _TAU * vertex / vertices
            rr = radius * (0.67 + 0.24 * np.sin(colony + vertex * 2.3))
            host.append(c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * rr)
        body = "slate_hosts_a" if (colony * 5) % 13 < 7 else "wet_hosts_b"
        _draw_poly(masks[body], host,
                   0.65 + 0.08 * (colony % 4), 1, True)
        _draw_poly(masks["basalt_bevels"], host, 1.0, 1, False)
        lobe_count = 2 + (colony * 11) % 5
        for lobe in range(lobe_count):
            theta = (rotation + lobe * 2.399963229728653
                     + 0.31 * np.sin(colony * 0.7 + lobe * 1.9))
            centre = c + np.asarray([np.cos(theta), np.sin(theta)], np.float32) * (
                0.8 + 0.27 * ((colony + lobe * 3) % 6))
            cv2.ellipse(masks["foliose_lobes"],
                        tuple(np.rint(centre).astype(int)),
                        (1 + (colony + lobe) % 3, 1 + (colony + 2 * lobe) % 2),
                        float(np.degrees(theta)),
                        18 + (colony + lobe) % 47,
                        235 + (colony * 3 + lobe * 11) % 92, 1.0, 1,
                        cv2.LINE_AA)
        if colony % 2 == 0:
            _w16_disc(masks["soredia_cups"], c, 1, 1.0, False)
        if colony % 3 == 0:
            _w16_segment(masks["moisture_channels"], c,
                         rotation + 0.68, 3.0 + colony % 5,
                         1.0, 1, 0.6)
        if colony % 5 == 0:
            _w16_segment(masks["quartz_needles"], host[-1],
                         rotation - 0.42, 2.0 + colony % 5,
                         1.0, 1)
        if colony % 7 == 0:
            for side in (-1.0, 1.0):
                _w16_segment(masks["moss_rhizoids"], c,
                             rotation + side * 0.91,
                             2.0 + colony % 4, 1.0, 1, side * 0.45)
        if colony % 11 == 0:
            _w16_disc(masks["spalled_corners"], host[0],
                      1, 1.0, True)
    banks = dict(slate_hosts_a="A", wet_hosts_b="B", basalt_bevels="N",
                 foliose_lobes="N", soredia_cups="B", moisture_channels="B",
                 quartz_needles="N", moss_rhizoids="A", spalled_corners="B")
    tone = _norm(0.33 * np.sin(x / 73.0) + 0.29 * np.cos(y / 89.0)
                 + 0.23 * np.sin((x + 1.5 * y) / 47.0))
    return _pack(masks, banks, tone)


def _build_fc_hide_scale_glass_w18() -> _Grammar:
    """Short curling shoals of overlapping biconvex lenses, not dot scatter."""
    names = ("amber_lens_backs_a", "green_lens_fronts_b", "convex_rims",
             "focal_caustics", "stress_veins", "dermal_pores",
             "occlusion_shadows", "scuff_crescents", "prism_glints")
    masks = _new_marks(*names)
    x, y = _xy()
    for shoal in range(1, 281):
        point = np.asarray([3.0 + 506.0 * _halton(shoal, 5),
                            3.0 + 506.0 * _halton(shoal, 59)], np.float32)
        heading = (0.44 * np.sin(point[0] / 79.0)
                   - 0.39 * np.cos(point[1] / 91.0)
                   + ((shoal * 7) % 13 - 6) * 0.07)
        steps = 10 + (shoal * 11) % 11
        for step in range(steps):
            heading += 0.14 * np.sin(shoal * 1.1 + step * 1.7)
            tangent = np.asarray([np.cos(heading), np.sin(heading)], np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            length = 4.0 + (shoal + step * 7) % 5
            width = 2.0 + 0.38 * ((shoal + step) % 5)
            centre = point + tangent * length * 0.58
            tip = point + tangent * length
            polygon = [point, centre - normal * width,
                       tip, centre + normal * width * (
                           0.72 + 0.08 * ((shoal + step) % 3))]
            body = "amber_lens_backs_a" if (shoal + step) % 5 < 3 else "green_lens_fronts_b"
            _draw_poly(masks[body], polygon,
                       0.7 + 0.07 * ((shoal + step) % 4), 1, True)
            _draw_poly(masks["convex_rims"], polygon, 1.0, 1, False)
            _draw_line(masks["focal_caustics"], point + tangent,
                       tip - tangent, 1.0, 1)
            if (shoal + step) % 2 == 0:
                _w16_segment(masks["stress_veins"], centre,
                             heading + np.pi * 0.5,
                             2.0 + step % 5, 1.0, 1, 0.4)
            if (shoal + step) % 3 == 0:
                _w16_disc(masks["dermal_pores"], centre - normal,
                          1, 1.0, False)
            if (shoal + step) % 5 == 0:
                _draw_line(masks["occlusion_shadows"], polygon[2], polygon[3],
                           1.0, 2)
            if (shoal + step) % 7 == 0:
                cv2.ellipse(masks["scuff_crescents"],
                            tuple(np.rint(centre).astype(int)),
                            (2 + step % 3, 1 + shoal % 2),
                            float(np.degrees(heading)), 200, 330, 1.0, 1,
                            cv2.LINE_AA)
            if (shoal + step) % 11 == 0:
                _w16_disc(masks["prism_glints"], tip,
                          1, 1.0, True)
            point = point + tangent * (2.7 + 0.25 * (step % 4))
    banks = dict(amber_lens_backs_a="A", green_lens_fronts_b="B",
                 convex_rims="N", focal_caustics="N", stress_veins="A",
                 dermal_pores="N", occlusion_shadows="B",
                 scuff_crescents="A", prism_glints="B")
    tone = _norm(0.4 * np.sin(x / 83.0) - 0.31 * np.cos(y / 71.0)
                 + 0.22 * np.sin((x + 1.2 * y) / 43.0))
    return _pack(masks, banks, tone)


def _build_fc_eyeshine_w19() -> _Grammar:
    """Nonlinear tapetal ray-fold density: no cube stamp or tiled basin."""
    names = ("positive_fold_faces_a", "negative_fold_faces_b", "caustic_ridges",
             "pupil_shears", "iris_relays", "cusp_glints",
             "lash_breaks", "dark_adaptation_notches", "cracked_wavefronts")
    # A deterministic ray bundle is the physical primary process.  The input
    # samples are never rendered.  Their nonlinear lens map folds phase space;
    # only output photon density, fold sign and descendants become features.
    ray_res = 720
    rv, ru = np.mgrid[-1.0:1.0:complex(ray_res),
                      -1.0:1.0:complex(ray_res)].astype(np.float32)
    base_x = (ru + 1.0) * 255.5
    base_y = (rv + 1.0) * 255.5
    out_x = (base_x + 7.2 * np.sin(59.0 * rv + 1.7 * ru * ru)
             + 4.8 * np.sin(97.0 * (ru + rv))
             + 3.0 * (ru * ru - rv * rv))
    out_y = (base_y + 6.8 * np.sin(67.0 * ru - 1.4 * rv * rv)
             + 4.5 * np.cos(89.0 * (ru - rv))
             + 3.2 * (2.0 * ru * rv))
    # Signed Jacobian classifies the two opposed retroreflector faces.
    duy, dux = np.gradient(out_x)
    dvy, dvx = np.gradient(out_y)
    determinant = dux * dvy - duy * dvx
    px = np.mod(np.rint(out_x).astype(np.int32), 512)
    py = np.mod(np.rint(out_y).astype(np.int32), 512)
    density = np.zeros((_WORK, _WORK), np.float32)
    positive = np.zeros_like(density)
    negative = np.zeros_like(density)
    np.add.at(density, (py.ravel(), px.ravel()), 1.0)
    np.add.at(positive, (py.ravel(), px.ravel()),
              (determinant > 0.0).astype(np.float32).ravel())
    np.add.at(negative, (py.ravel(), px.ravel()),
              (determinant <= 0.0).astype(np.float32).ravel())
    density = np.power(_norm(cv2.GaussianBlur(density, (0, 0), 1.45)),
                       0.46).astype(np.float32)
    positive = np.power(_norm(cv2.GaussianBlur(positive, (0, 0), 1.65)),
                        0.49).astype(np.float32)
    negative = np.power(_norm(cv2.GaussianBlur(negative, (0, 0), 1.65)),
                        0.49).astype(np.float32)
    x, y = _xy()
    gx = cv2.Sobel(density, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(density, cv2.CV_32F, 0, 1, ksize=3)
    gradient = _norm(np.hypot(gx, gy))
    direction = np.arctan2(gy, gx)
    fold_carrier = _f32((density - 0.08) / 0.72)
    polarization = np.sin(2.3 * direction + 4.1 * density)
    face_a = _f32(fold_carrier * _f32((polarization - 0.04) / 0.82))
    face_b = _f32(fold_carrier * _f32((-polarization - 0.04) / 0.82))
    ridges = _f32((gradient - 0.08) / 0.62)
    pupil = _f32(ridges * _line(np.sin(direction * 3.0 + density * 7.0), 0.11))
    iris = _f32(_line(np.sin(density * 29.0 + direction * 1.7), 0.10)
                * _f32((density - 0.13) / 0.65))
    local_max = (density >= cv2.dilate(density, np.ones((5, 5), np.uint8)) - 1e-6)
    glints = local_max.astype(np.float32) * _f32((density - 0.31) / 0.54)
    lash = _f32(ridges * _line(np.sin((1.3 * x - 0.7 * y) / 4.9
                                     + direction), 0.085))
    dark = _f32((0.38 - density) / 0.38) * _f32((gradient - 0.05) / 0.35)
    cracked = _f32(ridges * _line(np.cos((x + 1.6 * y) / 6.7
                                         - direction * 1.4), 0.075))
    masks = dict(positive_fold_faces_a=face_a, negative_fold_faces_b=face_b,
                 caustic_ridges=ridges, pupil_shears=pupil,
                 iris_relays=iris, cusp_glints=glints,
                 lash_breaks=lash, dark_adaptation_notches=dark,
                 cracked_wavefronts=cracked)
    banks = dict(positive_fold_faces_a="A", negative_fold_faces_b="B",
                 caustic_ridges="N", pupil_shears="A", iris_relays="B",
                 cusp_glints="B", lash_breaks="N",
                 dark_adaptation_notches="N", cracked_wavefronts="B")
    return _pack(masks, banks, _norm(density + 0.19 * direction))


def _build_fc_webbed_membrane_w21() -> _Grammar:
    """Hierarchical finite-tension membrane with closed, deformed panels.

    SPB-WILDS WR-21, 2026-08-24.  Owner-eye W20 verdict: Webbed was the sole
    visually distinct REPAIR-CANDIDATE, but its paint was still a collection
    of analytic arcs and its M/R/Cc contacts did not prove that the membrane
    surface owned the Fractured handoff.  This is an empty-topology repair:
    two deterministic finite-element site levels form nested closed panels,
    one smooth load displacement deforms the graph, and all secondary marks
    descend from edge distance, principal stress, junction degree, or local
    strain.  No glyph scatter, random/noise layer, grid, rank quantizer, hub,
    or repeated fan is present.  Every drawn component is 2-8 work pixels.
    """
    x, y = _xy()

    def site_labels(count: int, bases: Tuple[int, int], phase: float
                    ) -> Tuple[np.ndarray, np.ndarray]:
        # Low-discrepancy sites are finite-element nodes, not decorative
        # scatter.  Every visible pixel below descends from their adjacency.
        source = np.ones((_WORK, _WORK), np.uint8)
        occupied = set()
        for index in range(1, count + 1):
            u = _halton(index, bases[0])
            v = _halton(index, bases[1])
            # A bounded load displacement prevents rows and repeated cell
            # silhouettes before the full graph is warped below.
            px = 5.0 + 502.0 * u + 8.0 * np.sin(_TAU * v + phase)
            py = 5.0 + 502.0 * v + 7.0 * np.sin(_TAU * u * 1.37 - phase)
            point = (int(np.clip(round(px), 1, _WORK - 2)),
                     int(np.clip(round(py), 1, _WORK - 2)))
            # Deterministic collision walk; it preserves one node per label.
            while point in occupied:
                point = ((point[0] + 3) % (_WORK - 2) + 1,
                         (point[1] + 5) % (_WORK - 2) + 1)
            occupied.add(point)
            source[point[1], point[0]] = 0
        distance_to_site, labels = cv2.distanceTransformWithLabels(
            source, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        return distance_to_site.astype(np.float32), labels.astype(np.float32)

    # Two-level nested membrane: 82 load panels and 1180 capillary panels.
    # Each broad load panel contains many fine closed cells, so the coarse
    # graph reads as hierarchy rather than a single-size cellular paver.
    coarse_distance, coarse_labels = site_labels(82, (2, 3), 0.41)
    fine_distance, fine_labels = site_labels(1180, (5, 7), 1.13)

    # Smooth finite-tension displacement from unequal boundary loads.  It is
    # not rendered as a scalar carrier; it only moves the cell adjacency.
    dx = (16.0 * np.sin(y / 67.0 + 0.31 * np.sin(x / 113.0))
          + 8.5 * np.sin((x + 1.7 * y) / 149.0))
    dy = (-14.0 * np.cos(x / 79.0 - 0.27 * np.cos(y / 127.0))
          + 7.5 * np.sin((1.4 * x - y) / 137.0))
    map_x = (x + dx).astype(np.float32)
    map_y = (y + dy).astype(np.float32)
    coarse_labels = cv2.remap(coarse_labels, map_x, map_y,
                              cv2.INTER_NEAREST, borderMode=cv2.BORDER_REFLECT_101)
    fine_labels = cv2.remap(fine_labels, map_x, map_y,
                            cv2.INTER_NEAREST, borderMode=cv2.BORDER_REFLECT_101)
    coarse_distance = cv2.remap(coarse_distance, map_x, map_y,
                                cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    fine_distance = cv2.remap(fine_distance, map_x, map_y,
                              cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    def boundaries(labels: np.ndarray) -> np.ndarray:
        edge = np.zeros((_WORK, _WORK), np.uint8)
        edge[:, 1:] |= labels[:, 1:] != labels[:, :-1]
        edge[1:, :] |= labels[1:, :] != labels[:-1, :]
        edge[:, :-1] |= labels[:, :-1] != labels[:, 1:]
        edge[:-1, :] |= labels[:-1, :] != labels[1:, :]
        return edge.astype(np.float32)

    coarse_edge = boundaries(coarse_labels)
    fine_edge = boundaries(fine_labels)
    # Fine panels terminate at the primary load frame instead of crossing it.
    primary = cv2.dilate(coarse_edge, np.ones((3, 3), np.uint8))
    fine_only = fine_edge * (1.0 - cv2.dilate(coarse_edge,
                                                np.ones((5, 5), np.uint8)))
    # The boundary extractor already marks both pixels adjacent to an edge,
    # giving a true two-work-pixel secondary vein without thickening it into
    # a cellular paver.
    secondary = fine_only
    full_frame = _f32(np.maximum(primary, secondary))

    # Principal stress direction and magnitude come from the same displacement
    # used above.  Opposite 2-6 px sides of each cell wall are literal
    # tension/compression membrane faces, not decorative outline colors.
    ux = cv2.Sobel(dx.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    uy = cv2.Sobel(dx.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    vx = cv2.Sobel(dy.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    vy = cv2.Sobel(dy.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    strain = _norm(np.hypot(ux + vy, uy + vx))
    theta = 0.5 * np.arctan2(uy + vx, ux - vy + 1.0e-5)
    distance = cv2.distanceTransform((full_frame < 0.18).astype(np.uint8),
                                     cv2.DIST_L2, 5)
    # The gradient of distance-to-node gives a stable local coordinate inside
    # every deformed fine panel.  Dotting it with principal stress partitions
    # the actual membrane face into unequal contiguous tensile/compressive
    # halves.  At the 15 px mean cell diameter each face is 2-8 work px wide.
    fdx = cv2.Sobel(fine_distance, cv2.CV_32F, 1, 0, ksize=3)
    fdy = cv2.Sobel(fine_distance, cv2.CV_32F, 0, 1, ksize=3)
    local_theta = theta + 0.58 * np.sin(coarse_labels * 1.61803398875 + 0.37)
    face_side = fdx * np.cos(local_theta) + fdy * np.sin(local_theta)
    interior = _f32(1.0 - cv2.GaussianBlur(full_frame, (0, 0), 0.72))
    # Only the 2-6 px load-bearing sleeve adjacent to a cell wall is colored;
    # broad cell interiors stay translucent.  Opposite perimeter arcs are the
    # two membrane faces, avoiding both a filled mosaic and floating dashes.
    face_sleeve = (_f32((distance - 0.7) / 1.1)
                   * _f32((6.2 - distance) / 1.35) * interior)
    membrane_a = _f32(face_sleeve * _f32((face_side - 0.12) / 1.05))
    membrane_b = _f32(face_sleeve * _f32((-face_side - 0.12) / 1.05))

    # The neutral line between those two load states is a physical stretch
    # crease crossing each cell, not a floating directional-stroke layer.
    striae = _f32(interior * _f32(1.0 - np.abs(face_side) / 1.25)
                   * _f32((distance - 0.8) / 1.2))

    # Capillaries are the high-shear subset of the *existing* secondary graph;
    # they never float as free lines.  Primary/fine intersections form load
    # bridges and graph degree creates node pads.
    capillaries = _f32(secondary * _f32((strain - 0.37) / 0.36))
    bridges = _f32(secondary * cv2.dilate(primary, np.ones((5, 5), np.uint8)))
    def label_junctions(labels: np.ndarray) -> np.ndarray:
        # Three-or-more distinct cell labels in one 2x2 neighbourhood is a
        # true finite-element junction.  Counting thick edge pixels instead
        # would incorrectly turn the whole vein graph into a "node pad".
        p = labels[:-1, :-1]
        r = labels[:-1, 1:]
        d = labels[1:, :-1]
        q = labels[1:, 1:]
        j = (((p != r) & (p != d) & (r != d))
             | ((p != r) & (p != q) & (r != q))
             | ((p != d) & (p != q) & (d != q))
             | ((r != d) & (r != q) & (d != q)))
        out = np.zeros((_WORK, _WORK), np.uint8)
        out[:-1, :-1] = j.astype(np.uint8)
        return out

    nodes = np.maximum(label_junctions(coarse_labels),
                       label_junctions(fine_labels))
    nodes = cv2.dilate(nodes, np.ones((3, 3), np.uint8)).astype(np.float32)

    # Tears occur only where strain exceeds the membrane's local capacity.
    # Their two-pixel lips are cut from the membrane distance field rather
    # than stamped as ellipses or random holes.
    rupture = (_f32((strain - 0.68) / 0.18)
               * _f32((distance - 2.2) / 1.8)
               * _f32((fine_distance - 2.0) / 2.5))
    rupture = cv2.morphologyEx((rupture > 0.44).astype(np.uint8),
                               cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    tear_lips = _f32(_edge(rupture.astype(np.float32), 1) *
                     _f32((10.0 - distance) / 3.0))

    masks = dict(
        primary_tension_rays=primary,
        secondary_panel_veins=secondary,
        membrane_tension_faces_a=membrane_a,
        membrane_compression_faces_b=membrane_b,
        stretch_striae=striae,
        capillary_loops=capillaries,
        load_node_pads=nodes,
        elastic_bridges=bridges,
        tear_lips=tear_lips,
    )
    banks = dict(
        primary_tension_rays="N",
        secondary_panel_veins="N",
        membrane_tension_faces_a="A",
        membrane_compression_faces_b="B",
        stretch_striae="A",
        capillary_loops="B",
        load_node_pads="A",
        elastic_bridges="N",
        tear_lips="B",
    )

    # Process-specific material proof.  M is the load frame + tensile face;
    # R is the cell strain/tear story; Cc is the compressed face + capillary
    # film.  All three are assembled only from the named membrane masks.
    m_field = (10.0 + 202.0 * membrane_a + 188.0 * primary
               + 82.0 * secondary + 43.0 * striae + 228.0 * nodes)
    r_field = (222.0 - 146.0 * striae - 112.0 * bridges
               - 74.0 * membrane_a + 26.0 * tear_lips
               - 38.0 * _f32(strain * interior))
    cc_field = (12.0 + 210.0 * membrane_b + 224.0 * capillaries
                + 104.0 * secondary + 168.0 * tear_lips
                + 52.0 * bridges)
    tone = _norm(0.30 * distance + 0.23 * fine_distance + 0.26 * strain
                 + 0.13 * np.cos(2.0 * theta) + 0.08 * coarse_labels / 82.0)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_webbed_membrane_w22() -> _Grammar:
    """Domain-local W21 membrane with heterogeneous visible anatomy.

    SPB-WILDS WR-22, 2026-08-24.  Independent W21 verdict: strong repair,
    but the two face hatches still occupied the whole card and resolved as one
    elongated-cell paver.  W22 preserves W21's finite-tension adjacency and
    process fields exactly.  It localizes the two face states to mutually
    exclusive load domains, then gives capillaries, bridges, true graph nodes,
    and strain tears their own visible membrane regions.  This is a material
    routing repair, not a hue, seed, density, crop, or glyph change.
    """
    source = _build_fc_webbed_membrane_w21()
    original = {name: mask for name, mask, _bank in source.marks}

    face_a = original["membrane_tension_faces_a"]
    face_b = original["membrane_compression_faces_b"]
    support = cv2.GaussianBlur(face_a + face_b, (0, 0), 17.0)
    signed_load = cv2.GaussianBlur(face_a - face_b, (0, 0), 23.0)
    signed_load = signed_load / (support + 0.035)

    # Fixed physical dead-band creates mutually exclusive tensile and
    # compressive domains.  The broad masks are never painted themselves;
    # they only decide where W21 membrane facets are allowed to remain.
    tension_domain = (signed_load > 0.055).astype(np.uint8)
    compression_domain = (signed_load < -0.055).astype(np.uint8)
    domain_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    tension_domain = cv2.morphologyEx(tension_domain, cv2.MORPH_OPEN, domain_kernel)
    compression_domain = cv2.morphologyEx(compression_domain, cv2.MORPH_OPEN,
                                          domain_kernel)
    localized_a = _f32(face_a * tension_domain)
    localized_b = _f32(face_b * compression_domain)
    occupied_domain = np.maximum(tension_domain, compression_domain).astype(np.float32)
    release_domain = 1.0 - occupied_domain

    # Anatomy in the released membrane is feature-descended from W21.  The
    # masks are widened only to 2-5 work pixels; no new placement carrier is
    # introduced.  This makes the shelf visibly heterogeneous rather than
    # filling empty domains with a third hatch.
    capillary_core = original["capillary_loops"]
    capillary_loops = _f32(capillary_core * (0.42 + 0.58 * release_domain))

    bridge_core = original["elastic_bridges"]
    elastic_bridges = cv2.dilate(bridge_core, np.ones((3, 3), np.uint8))
    elastic_bridges = _f32(elastic_bridges * (0.36 + 0.64 * release_domain))
    bridge_flexure_lips = _f32(_halo(bridge_core, 1.25)
                               * (0.35 + 0.65 * release_domain))

    pad = original["load_node_pads"]
    pad_core = cv2.erode((pad > 0.12).astype(np.uint8),
                         np.ones((3, 3), np.uint8)).astype(np.float32)
    pad_rim = _f32(_edge(pad_core, 1) * (0.30 + 0.70 * release_domain))

    cross3 = np.asarray([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.uint8)
    tear_shape = cv2.dilate(original["tear_lips"], cross3)
    tear_lips = _f32(tear_shape * (0.28 + 0.72 * release_domain))
    recoil_shell = cv2.dilate(tear_shape, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (5, 5))).astype(np.float32)
    tear_recoil = _f32(_edge(recoil_shell, 1) * (1.0 - tear_shape)
                       * (0.32 + 0.68 * release_domain))

    release_seams = _f32(original["stretch_striae"] * release_domain)

    masks = dict(
        primary_tension_rays=original["primary_tension_rays"],
        secondary_panel_veins=original["secondary_panel_veins"],
        localized_tension_facets_a=localized_a,
        localized_compression_folds_b=localized_b,
        capillary_loops=capillary_loops,
        elastic_bridges=elastic_bridges,
        bridge_flexure_lips=bridge_flexure_lips,
        load_node_cores=pad_core,
        load_node_rims=pad_rim,
        strain_release_seams=release_seams,
        tear_lips=tear_lips,
        tear_recoil_arcs=tear_recoil,
    )
    banks = dict(
        primary_tension_rays="N",
        secondary_panel_veins="N",
        localized_tension_facets_a="A",
        localized_compression_folds_b="B",
        capillary_loops="B",
        elastic_bridges="A",
        bridge_flexure_lips="A",
        load_node_cores="A",
        load_node_rims="B",
        strain_release_seams="N",
        tear_lips="B",
        tear_recoil_arcs="A",
    )

    primary = masks["primary_tension_rays"]
    secondary = masks["secondary_panel_veins"]
    m_field = (12.0 + 210.0 * localized_a + 172.0 * primary
               + 68.0 * secondary + 206.0 * elastic_bridges
               + 138.0 * bridge_flexure_lips + 236.0 * pad_core
               + 96.0 * tear_recoil)
    r_field = (220.0 - 158.0 * release_seams - 126.0 * elastic_bridges
               - 82.0 * bridge_flexure_lips - 56.0 * localized_a
               + 28.0 * tear_lips - 38.0 * pad_rim)
    cc_field = (14.0 + 214.0 * localized_b + 222.0 * capillary_loops
                + 174.0 * pad_rim + 232.0 * tear_lips
                + 46.0 * secondary)
    tone = _norm(source.tone + 0.14 * tension_domain
                 - 0.11 * compression_domain + 0.09 * release_domain)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w23() -> _Grammar:
    """Asymmetric catastrophe-optics progression, rendered as ray envelopes.

    SPB-WILDS WR-23, 2026-08-24.  W20 rejected W19 as optical fuzz; earlier
    variants were macro basins, corner-cube stamps, and tiled triangular cups.
    This reset draws the envelopes of twelve unequal fold/cusp/swallowtail ray
    events.  Every auxiliary mark is attached to envelope curvature, optical
    order, or a phase discontinuity.  There is no density image, random/noise
    ground, basin crop, eye glyph, cell mesh, hub, grid, or repeated stamp.
    """
    names = (
        "positive_fold_faces_a", "negative_relay_faces_b",
        "caustic_envelope_cores", "positive_diffraction_orders_a",
        "negative_diffraction_orders_b", "pupil_phase_shears",
        "cusp_glint_discontinuities", "eyelid_occlusion_lips",
        "lash_phase_breaks", "cracked_wavefront_relays",
    )
    masks = _new_marks(*names)
    phase_field = np.zeros((_WORK, _WORK), np.float32)
    shear_cut = np.zeros((_WORK, _WORK), np.float32)

    # Each row is one successive catastrophe state in a single asymmetric
    # optical progression.  The events overlap/crop at the card boundaries;
    # none is displayed as an isolated atlas icon.
    events = (
        (0, -42.0, 94.0, 214.0, 136.0, -0.17, 0.23),
        (1, 126.0, -34.0, 178.0, 164.0, 0.81, 0.61),
        (2, 306.0, 44.0, 192.0, 151.0, -0.72, 1.07),
        (3, 515.0, 119.0, 226.0, 128.0, 0.19, 1.43),
        (4, 458.0, 278.0, 171.0, 193.0, 1.08, 1.89),
        (0, 523.0, 464.0, 214.0, 143.0, -1.24, 2.31),
        (2, 332.0, 526.0, 203.0, 171.0, 0.54, 2.77),
        (1, 134.0, 548.0, 183.0, 142.0, -0.42, 3.19),
        (4, -27.0, 423.0, 226.0, 168.0, 0.91, 3.61),
        (3, 43.0, 268.0, 194.0, 181.0, -0.96, 4.03),
        (2, 235.0, 251.0, 167.0, 127.0, 0.37, 4.47),
        (1, 399.0, 361.0, 181.0, 137.0, -0.31, 4.91),
    )

    def draw_path(mask: np.ndarray, points: np.ndarray, value: float,
                  width: int) -> None:
        finite = np.isfinite(points).all(axis=1)
        # Split at numerical/crop jumps so OpenCV cannot bridge unrelated
        # envelope branches across the card.
        start = 0
        for index in range(1, len(points) + 1):
            jump = (index == len(points) or not finite[index - 1]
                    or (index < len(points)
                        and float(np.linalg.norm(points[index] - points[index - 1])) > 24.0))
            if jump:
                segment = points[start:index][finite[start:index]]
                if len(segment) >= 2:
                    cv2.polylines(mask, [np.rint(segment).astype(np.int32)],
                                  False, float(value), int(width), cv2.LINE_AA)
                start = index

    for event_index, (kind, cx, cy, sx, sy, rotation, phase) in enumerate(events):
        q = np.linspace(-1.34, 1.34, 641, dtype=np.float32)
        # Canonical fold -> cusp -> swallowtail -> butterfly progression.
        if kind == 0:
            u = q
            v = 0.60 * q ** 3 - 0.54 * q + 0.10 * q ** 5
        elif kind == 1:
            u = q ** 2 - 0.47 + 0.10 * q
            v = 0.76 * q ** 3 - 0.48 * q
        elif kind == 2:
            u = q ** 3 - 0.83 * q
            v = 0.48 * q ** 4 - 0.67 * q ** 2 + 0.16 * q
        elif kind == 3:
            u = q ** 4 - 0.96 * q ** 2 + 0.08 * q
            v = 0.43 * q ** 5 - 0.78 * q ** 3 + 0.31 * q
        else:
            u = q + 0.21 * q ** 3
            v = 0.39 * q ** 5 - 0.71 * q ** 3 + 0.42 * q

        # A small phase-dependent perturbation represents unequal tapetal
        # refractive order.  It alters the ray envelope, not the background.
        u = u + 0.055 * np.sin((2.0 + 0.13 * event_index) * q + phase)
        v = v + 0.047 * np.sin((3.0 + 0.17 * kind) * q - phase)
        cr, sr = float(np.cos(rotation)), float(np.sin(rotation))
        px = cx + sx * (cr * u - sr * v)
        py = cy + sy * (sr * u + cr * v)
        points = np.column_stack([px, py]).astype(np.float32)

        tangent = np.gradient(points, axis=0)
        speed = np.maximum(np.linalg.norm(tangent, axis=1), 1.0e-4)
        normal = np.column_stack([-tangent[:, 1] / speed,
                                  tangent[:, 0] / speed]).astype(np.float32)
        second = np.gradient(tangent, axis=0)
        curvature = np.abs(tangent[:, 0] * second[:, 1]
                           - tangent[:, 1] * second[:, 0]) / (speed ** 3 + 1.0e-5)
        curvature /= max(float(np.percentile(curvature, 96)), 1.0e-5)
        curvature = np.clip(curvature, 0.0, 1.0)

        sleeve = 3.1 + 0.55 * np.sin(q * 1.7 + phase)
        positive = points + normal * sleeve[:, None]
        negative = points - normal * sleeve[:, None]
        fringe_gap = 7.0 + 0.65 * np.cos(q * 1.3 - phase)
        positive_fringe = points + normal * fringe_gap[:, None]
        negative_fringe = points - normal * fringe_gap[:, None]

        draw_path(masks["positive_fold_faces_a"], positive, 1.0, 4)
        draw_path(masks["negative_relay_faces_b"], negative, 1.0, 4)
        draw_path(masks["caustic_envelope_cores"], points, 0.92, 2)

        # Optical orders are deliberately discontinuous across alternating
        # canonical states; they cannot become uniform parallel rails.
        order_gate = ((np.arange(len(q)) // (31 + 2 * kind)
                       + event_index) % 3 != 1)
        pf = positive_fringe.copy()
        nf = negative_fringe.copy()
        pf[~order_gate] = np.nan
        nf[np.roll(~order_gate, 11 + kind)] = np.nan
        draw_path(masks["positive_diffraction_orders_a"], pf, 0.88, 2)
        draw_path(masks["negative_diffraction_orders_b"], nf, 0.88, 2)

        # Phase shears cut all ray-envelope bands at physically indexed
        # discontinuities.  Lash breaks and glints attach to those cuts or to
        # true high-curvature cusp samples; nothing is freely scattered.
        shear_indices = (91 + event_index * 7, 287 + kind * 11,
                         493 - event_index * 5)
        for shear_index in shear_indices:
            idx = int(np.clip(shear_index, 8, len(points) - 9))
            centre = points[idx]
            n = normal[idx]
            a = centre - n * (5.0 + event_index % 3)
            b = centre + n * (5.0 + event_index % 3)
            _draw_line(shear_cut, a, b, 1.0, 5)
            _draw_line(masks["pupil_phase_shears"], a, b, 1.0, 3)
            tangent_unit = tangent[idx] / speed[idx]
            _draw_line(masks["lash_phase_breaks"],
                       a - tangent_unit * 2.0, a + tangent_unit * 3.0, 1.0, 2)
            _draw_line(masks["lash_phase_breaks"],
                       b - tangent_unit * 3.0, b + tangent_unit * 2.0, 1.0, 2)

        candidate_indices = np.where(curvature > 0.72)[0]
        prior = -30
        for idx in candidate_indices:
            if idx - prior < 28:
                continue
            prior = int(idx)
            centre = points[idx]
            tangent_unit = tangent[idx] / speed[idx]
            # A glint is a broken 3-7 px reflecting face, never a dot.
            _draw_line(masks["cusp_glint_discontinuities"],
                       centre - tangent_unit * 2.0,
                       centre + tangent_unit * (3.0 + event_index % 3),
                       1.0, 3)

        # A cropped path interval becomes an eyelid lip.  Its location varies
        # with catastrophe state and crosses the caustic rather than enclosing
        # an eye symbol.
        lo = 178 + (event_index * 23) % 141
        hi = min(len(points), lo + 72 + 7 * kind)
        draw_path(masks["eyelid_occlusion_lips"],
                  points[lo:hi] - normal[lo:hi] * 1.8, 0.96, 5)

        # Short relay fractures join an envelope only to its own diffraction
        # order.  They are causal cross-links, not a generic crack substrate.
        for idx in range(63 + event_index % 9, len(points) - 30, 97 + 3 * kind):
            if ((idx // 17) + event_index) % 2:
                _draw_line(masks["cracked_wavefront_relays"],
                           negative[idx], negative_fringe[idx], 1.0, 2)

        draw_path(phase_field, points,
                  0.12 + 0.073 * event_index, 5)

    # Make every phase shear a literal discontinuity in the optical faces.
    cut = _f32(cv2.GaussianBlur(shear_cut, (0, 0), 0.55))
    for name in ("positive_fold_faces_a", "negative_relay_faces_b",
                 "caustic_envelope_cores", "positive_diffraction_orders_a",
                 "negative_diffraction_orders_b"):
        masks[name] = _f32(masks[name] * (1.0 - cut))

    banks = dict(
        positive_fold_faces_a="A",
        negative_relay_faces_b="B",
        caustic_envelope_cores="N",
        positive_diffraction_orders_a="A",
        negative_diffraction_orders_b="B",
        pupil_phase_shears="N",
        cusp_glint_discontinuities="A",
        eyelid_occlusion_lips="B",
        lash_phase_breaks="N",
        cracked_wavefront_relays="B",
    )

    fold = masks["positive_fold_faces_a"]
    relay = masks["negative_relay_faces_b"]
    core = masks["caustic_envelope_cores"]
    pa = masks["positive_diffraction_orders_a"]
    pb = masks["negative_diffraction_orders_b"]
    shear = masks["pupil_phase_shears"]
    glint = masks["cusp_glint_discontinuities"]
    eyelid = masks["eyelid_occlusion_lips"]
    lash = masks["lash_phase_breaks"]
    cracks = masks["cracked_wavefront_relays"]
    m_field = (10.0 + 208.0 * fold + 142.0 * core + 176.0 * pa
               + 236.0 * glint + 62.0 * eyelid)
    r_field = (214.0 - 162.0 * shear - 116.0 * lash - 84.0 * core
               + 32.0 * cracks - 46.0 * eyelid)
    cc_field = (12.0 + 212.0 * relay + 182.0 * pb + 226.0 * eyelid
                + 154.0 * cracks + 54.0 * core)
    x, y = _xy()
    tone = _norm(0.62 * cv2.GaussianBlur(phase_field, (0, 0), 3.2)
                 + 0.21 * x / _WORK + 0.17 * y / _WORK)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w24() -> _Grammar:
    """Tapetal ray sheet folded by an asymmetric symplectic twist map.

    SPB-WILDS WR-24, 2026-08-24.  W23 was self-rejected before root review:
    twelve vector envelopes became sparse macro rails with repeated eye loops.
    W24 restarts from a two-dimensional optical sheet.  Four smooth canonical
    ray-transfer kicks stretch and fold two ancestral tapetal bands across the
    frame.  All visible features descend from band ancestry, a fold crest, or
    a true phase-wrap discontinuity.  No line scatter, noise/density image,
    basin, cell mesh, central pupil, repeated icon, or scalar contour paver is
    added after the transport.
    """
    x, y = _xy()
    u = (x + 0.5) / _WORK
    v = (y + 0.5) / _WORK
    wrap_events = np.zeros((_WORK, _WORK), np.float32)

    # Area-preserving ray-transfer kicks.  The coefficients are one optical
    # prescription, not per-feature seeds.  Four iterations remain coherent;
    # deeper iteration would deliberately be rejected as chaotic fuzz.
    kicks = (
        (0.137, 0.109, 0.17, 0.61),
        (-0.118, 0.151, 1.03, 0.29),
        (0.164, -0.126, 0.47, 1.37),
        (-0.103, 0.143, 1.71, 0.83),
    )
    for vertical_kick, horizontal_kick, phase_u, phase_v in kicks:
        next_v_raw = (v + vertical_kick * np.sin(_TAU * (u + phase_u))
                      + 0.031 * np.sin(_TAU * (2.0 * u - v + phase_v)))
        next_v = np.mod(next_v_raw, 1.0)
        wrap_events = np.maximum(wrap_events,
                                 (np.abs(next_v_raw - next_v) > 0.42).astype(np.float32))
        next_u_raw = (u + horizontal_kick * np.sin(_TAU * (next_v + phase_v))
                      + 0.027 * np.sin(_TAU * (u + 2.0 * next_v - phase_u)))
        next_u = np.mod(next_u_raw, 1.0)
        wrap_events = np.maximum(wrap_events,
                                 (np.abs(next_u_raw - next_u) > 0.42).astype(np.float32))
        u, v = next_u.astype(np.float32), next_v.astype(np.float32)

    def periodic_band(phase: np.ndarray, centre: float,
                      half_width: float, feather: float) -> np.ndarray:
        distance = np.abs(np.mod(phase - centre + 0.5, 1.0) - 0.5)
        return _f32((half_width - distance) / max(0.005, feather) + 0.5)

    # Ancestral source bands are 2-8 work pixels after the four ray folds.
    phase_a = np.mod(10.0 * u + 0.41 * v, 1.0)
    phase_b = np.mod(8.0 * v - 0.37 * u + 0.09, 1.0)
    sheet_a = periodic_band(phase_a, 0.16, 0.052, 0.020)
    sheet_b_raw = periodic_band(phase_b, 0.61, 0.054, 0.021)
    # A/B sheets cross optically but the visible paint ownership remains
    # substantial and exclusive at their junctions.
    sheet_b = _f32(sheet_b_raw * (1.0 - 0.78 * sheet_a))

    crest_a = periodic_band(phase_a, 0.082, 0.018, 0.012)
    crest_b = periodic_band(phase_b, 0.526, 0.018, 0.012)
    wrap_boundary = _edge(wrap_events.astype(np.float32), 1)
    fold_crests = _f32(np.maximum(crest_a, crest_b)
                       * (1.0 - cv2.dilate((wrap_boundary > 0.08).astype(np.uint8),
                                           np.ones((3, 3), np.uint8))))
    order_a = periodic_band(phase_a, 0.295, 0.020, 0.012)
    order_b = periodic_band(phase_b, 0.746, 0.021, 0.012)

    # True map discontinuities are the pupil phase shears.  Their lips and
    # lash breaks are derived morphologically from that same feature; they are
    # not free glyphs.
    pupil_shears = wrap_boundary
    shear_shell = cv2.dilate(pupil_shears.astype(np.uint8),
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    eyelid_lips = _f32(_edge(shear_shell.astype(np.float32), 1)
                       * (1.0 - pupil_shears))

    # Curvature is evaluated on the transported sheet in a wrap-safe complex
    # embedding.  Glints stay on real fold crests; relays stay where a fold
    # actually meets a pupil shear.
    embed_a = np.sin(_TAU * phase_a).astype(np.float32)
    lap_a = np.abs(cv2.Laplacian(embed_a, cv2.CV_32F, ksize=3))
    curvature = _norm(cv2.GaussianBlur(lap_a, (0, 0), 0.85))
    glint_gate = periodic_band(np.mod(3.0 * u - 2.0 * v, 1.0),
                               0.43, 0.062, 0.025)
    cusp_glints = _f32(fold_crests * np.maximum(
        _f32((curvature - 0.16) / 0.42), glint_gate))
    cracked_relays = _f32(cv2.dilate(fold_crests, np.ones((3, 3), np.uint8))
                          * cv2.dilate(pupil_shears,
                                       np.ones((5, 5), np.uint8)))
    cracked_relays = _f32(_edge(cracked_relays, 1))

    shear_dx = np.abs(cv2.Sobel(u.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3))
    shear_dy = np.abs(cv2.Sobel(v.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3))
    direction_gate = _f32((shear_dx - shear_dy + 0.12) / 0.52)
    lash_breaks = _f32(pupil_shears * direction_gate
                       * periodic_band(np.mod(7.0 * u + 5.0 * v, 1.0),
                                       0.31, 0.055, 0.022))

    # Phase cuts are literal gaps in the transported tapetal sheets.
    cut = _f32(cv2.GaussianBlur(pupil_shears, (0, 0), 0.55))
    sheet_a = _f32(sheet_a * (1.0 - cut))
    sheet_b = _f32(sheet_b * (1.0 - cut))
    order_a = _f32(order_a * (1.0 - cut))
    order_b = _f32(order_b * (1.0 - cut))

    masks = dict(
        transported_positive_sheet_a=sheet_a,
        transported_negative_sheet_b=sheet_b,
        fold_caustic_crests=fold_crests,
        positive_diffraction_orders_a=order_a,
        negative_diffraction_orders_b=order_b,
        pupil_phase_shears=pupil_shears,
        cusp_glint_discontinuities=cusp_glints,
        eyelid_occlusion_lips=eyelid_lips,
        lash_phase_breaks=lash_breaks,
        cracked_wavefront_relays=cracked_relays,
    )
    banks = dict(
        transported_positive_sheet_a="A",
        transported_negative_sheet_b="B",
        fold_caustic_crests="N",
        positive_diffraction_orders_a="A",
        negative_diffraction_orders_b="B",
        pupil_phase_shears="N",
        cusp_glint_discontinuities="A",
        eyelid_occlusion_lips="B",
        lash_phase_breaks="N",
        cracked_wavefront_relays="B",
    )

    m_field = (10.0 + 206.0 * sheet_a + 154.0 * fold_crests
               + 186.0 * order_a + 232.0 * cusp_glints
               + 64.0 * cracked_relays)
    r_field = (216.0 - 156.0 * pupil_shears - 118.0 * lash_breaks
               - 92.0 * fold_crests + 28.0 * cracked_relays
               - 44.0 * eyelid_lips)
    cc_field = (12.0 + 210.0 * sheet_b + 184.0 * order_b
                + 226.0 * eyelid_lips + 168.0 * cracked_relays
                + 48.0 * fold_crests)
    tone = _norm(0.36 * u + 0.29 * v + 0.21 * curvature
                 + 0.14 * cv2.GaussianBlur(wrap_events, (0, 0), 2.2))
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w25() -> _Grammar:
    """Critical ray envelopes of one asymmetric refracting tapetal sheet.

    SPB-WILDS WR-25, 2026-08-24.  W24 was self-rejected because its transported
    source bands read as scalar marbling/flow fill and collided with reserved
    Morpho/Petri processes.  W25 renders only the true Jacobian-zero critical
    set of a smooth refracting sheet, its two local fold sides, and optics that
    physically attach to that set.  There is no visible height field, flow
    band, density image, cell graph, basin, random/noise layer, eye icon, or
    repeated local stamp.
    """
    x, y = _xy()
    u = (x + 0.5) / _WORK * 2.0 - 1.0
    v = (y + 0.5) / _WORK * 2.0 - 1.0

    # One chirped, nonperiodic tapetal height prescription.  The height is
    # never painted; it only refracts parallel rays to the observation plane.
    p1 = _TAU * (2.31 * u + 1.47 * v + 0.73 * u * v
                 + 0.28 * v * v - 0.17 * u * u)
    p2 = _TAU * (-1.19 * u + 3.07 * v - 0.61 * u * v
                 + 0.22 * u ** 3 + 0.11 * v * v)
    p3 = _TAU * (3.83 * u - 2.17 * v + 0.37 * u * v
                 - 0.19 * v ** 3 + 0.14 * u * u)
    p4 = _TAU * (1.63 * u + 4.11 * v + 0.33 * u * u
                 - 0.29 * v * v + 0.09 * u * v * v)
    height = (0.47 * np.sin(p1) + 0.31 * np.sin(p2 + 0.41)
              + 0.19 * np.sin(p3 - 0.73) + 0.11 * np.sin(p4 + 1.19))
    height = height.astype(np.float32)

    spacing = 2.0 / _WORK
    grad_v, grad_u = np.gradient(height, spacing, spacing)
    # Fermat ray transfer: screen position = source + focal distance * slope.
    map_x = x + 1.34 * grad_u
    map_y = y + 1.18 * grad_v
    dxx = np.gradient(map_x, axis=1)
    dxy = np.gradient(map_x, axis=0)
    dyx = np.gradient(map_y, axis=1)
    dyy = np.gradient(map_y, axis=0)
    determinant = (dxx * dyy - dxy * dyx).astype(np.float32)
    det_scale = max(float(np.percentile(np.abs(determinant), 97.5)), 1.0e-5)
    det = np.clip(determinant / det_scale, -1.0, 1.0).astype(np.float32)

    # det(J)=0 is the literal fold caustic.  Its two sign sides are the
    # opposing ray-sheet faces; distance bands stay 2-8 work pixels.
    core = _f32(1.0 - np.abs(det) / 0.052)
    core_binary = (core > 0.12).astype(np.uint8)
    distance = cv2.distanceTransform(1 - core_binary, cv2.DIST_L2, 5)
    fold_sleeve = (_f32((distance - 0.8) / 1.0)
                   * _f32((5.9 - distance) / 1.25))
    positive_face = _f32(fold_sleeve * (det > 0.0))
    negative_face = _f32(fold_sleeve * (det < 0.0))
    positive_order = (_f32(1.0 - np.abs(distance - 7.4) / 1.15)
                      * (det > 0.0).astype(np.float32))
    negative_order = (_f32(1.0 - np.abs(distance - 7.7) / 1.15)
                      * (det < 0.0).astype(np.float32))

    # High-slope tapetal zones are physically occluded at the pupil.  Only the
    # boundary is rendered as a shear; the filled scalar zone stays invisible.
    slope = _norm(np.hypot(grad_u, grad_v))
    occluded = (slope > 0.705).astype(np.float32)
    pupil_shear = _f32(_edge(occluded, 1))
    shear_cut = cv2.dilate((pupil_shear > 0.10).astype(np.uint8),
                           np.ones((3, 3), np.uint8)).astype(np.float32)
    positive_face = _f32(positive_face * (1.0 - shear_cut))
    negative_face = _f32(negative_face * (1.0 - shear_cut))
    positive_order = _f32(positive_order * (1.0 - shear_cut))
    negative_order = _f32(negative_order * (1.0 - shear_cut))
    core = _f32(core * (1.0 - 0.82 * shear_cut))

    eyelid_lips = _f32(_halo(pupil_shear, 1.35) * (1.0 - pupil_shear))
    det_dx = cv2.Sobel(det, cv2.CV_32F, 1, 0, ksize=3)
    det_dy = cv2.Sobel(det, cv2.CV_32F, 0, 1, ksize=3)
    critical_speed = _norm(np.hypot(det_dx, det_dy))
    # Cusp glints occur where the critical curve slows and reverses.  A fixed
    # phase gate merely separates adjacent pieces of the same envelope; it is
    # never visible away from a caustic core.
    phase_gate = _f32((np.sin(p1 - p3) - 0.06) / 0.78)
    cusp_glints = _f32(core * _f32((0.43 - critical_speed) / 0.27)
                       * phase_gate)
    intersection = (cv2.dilate(core_binary, np.ones((5, 5), np.uint8))
                    * cv2.dilate((pupil_shear > 0.08).astype(np.uint8),
                                 np.ones((5, 5), np.uint8))).astype(np.float32)
    lash_breaks = _f32(_edge(intersection, 1))
    order_union = np.maximum(positive_order, negative_order)
    cracked_relays = _f32(order_union * cv2.dilate(
        (pupil_shear > 0.08).astype(np.uint8), np.ones((7, 7), np.uint8)))
    cracked_relays = _f32(_edge(cracked_relays, 1))

    masks = dict(
        positive_fold_faces_a=positive_face,
        negative_fold_faces_b=negative_face,
        ray_envelope_cores=core,
        positive_diffraction_orders_a=positive_order,
        negative_diffraction_orders_b=negative_order,
        pupil_phase_shears=pupil_shear,
        cusp_glint_discontinuities=cusp_glints,
        eyelid_occlusion_lips=eyelid_lips,
        lash_phase_breaks=lash_breaks,
        cracked_wavefront_relays=cracked_relays,
    )
    banks = dict(
        positive_fold_faces_a="A",
        negative_fold_faces_b="B",
        ray_envelope_cores="N",
        positive_diffraction_orders_a="A",
        negative_diffraction_orders_b="B",
        pupil_phase_shears="N",
        cusp_glint_discontinuities="A",
        eyelid_occlusion_lips="B",
        lash_phase_breaks="N",
        cracked_wavefront_relays="B",
    )

    m_field = (10.0 + 210.0 * positive_face + 142.0 * core
               + 184.0 * positive_order + 234.0 * cusp_glints
               + 58.0 * lash_breaks)
    r_field = (218.0 - 158.0 * pupil_shear - 122.0 * lash_breaks
               - 86.0 * core + 30.0 * cracked_relays
               - 48.0 * eyelid_lips)
    cc_field = (12.0 + 212.0 * negative_face + 188.0 * negative_order
                + 228.0 * eyelid_lips + 174.0 * cracked_relays
                + 46.0 * core)
    tone = _norm(0.39 * height + 0.27 * slope + 0.22 * np.abs(det)
                 + 0.12 * cv2.GaussianBlur(pupil_shear, (0, 0), 2.0))
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w26() -> _Grammar:
    """Open, edge-cropped astigmatic caustic sheet with no closed cells.

    SPB-WILDS WR-26, 2026-08-24.  W25's periodic refractor produced closed
    bean-like critical cells and was self-rejected as a scalar paver.  W26
    uses fourteen unequal open ray envelopes from one chirped astigmatic
    aperture.  Every envelope enters and exits the card; no path closes, fans
    from a common point, or displays an isolated eye/cusp specimen.  Paired
    fold faces, phase cuts, diffraction relays and glints stay attached to the
    ray history.  There is no height-field fill, marbling, mesh, density/fuzz,
    basin or random/noise ground.
    """
    names = (
        "positive_fold_faces_a", "negative_fold_faces_b",
        "ray_envelope_cores", "positive_diffraction_orders_a",
        "negative_diffraction_orders_b", "pupil_phase_shears",
        "cusp_glint_discontinuities", "eyelid_occlusion_lips",
        "lash_phase_breaks", "cracked_wavefront_relays",
    )
    masks = _new_marks(*names)
    shear_cut = np.zeros((_WORK, _WORK), np.float32)
    phase_tone = np.zeros((_WORK, _WORK), np.float32)

    def draw_open(mask: np.ndarray, points: np.ndarray, value: float,
                  width: int) -> None:
        cv2.polylines(mask, [np.rint(points).astype(np.int32)], False,
                      float(value), int(width), cv2.LINE_AA)

    for order in range(14):
        q = np.linspace(-1.72, 1.72, 921, dtype=np.float32)
        # One aperture chronology: curvature and astigmatism drift smoothly
        # with order, so these are unequal ray envelopes rather than copied
        # Bezier/glyph stamps.
        a = 0.16 * np.sin(0.73 * order + 0.21)
        b = 0.23 * np.cos(0.47 * order - 0.38)
        c = 0.09 * np.sin(1.19 * order + 0.77)
        u = q
        v = a * q ** 3 + b * q ** 2 + c * q
        v += 0.038 * np.sin((1.35 + 0.07 * order) * q
                            + 0.41 * order) * (1.0 - 0.11 * q * q)
        rotation = -1.04 + np.mod(order * 1.117, 2.08)
        cr, sr = float(np.cos(rotation)), float(np.sin(rotation))
        sx = 286.0 + 17.0 * np.sin(order * 0.61)
        sy = 152.0 + 21.0 * np.cos(order * 0.83)
        cx = 256.0 + 73.0 * np.sin(order * 1.41421356237 + 0.19)
        cy = 256.0 + 66.0 * np.cos(order * 1.73205080757 - 0.31)
        px = cx + sx * (cr * u - sr * v)
        py = cy + sy * (sr * u + cr * v)
        points = np.column_stack([px, py]).astype(np.float32)
        tangent = np.gradient(points, axis=0)
        speed = np.maximum(np.linalg.norm(tangent, axis=1), 1.0e-4)
        normal = np.column_stack([-tangent[:, 1] / speed,
                                  tangent[:, 0] / speed]).astype(np.float32)
        second = np.gradient(tangent, axis=0)
        curvature = np.abs(tangent[:, 0] * second[:, 1]
                           - tangent[:, 1] * second[:, 0]) / (speed ** 3 + 1.0e-5)
        curvature /= max(float(np.percentile(curvature, 95)), 1.0e-5)

        side = 3.1 + 0.45 * np.sin(q * 1.23 + order * 0.37)
        pos = points + normal * side[:, None]
        neg = points - normal * side[:, None]
        order_gap = 7.2 + 0.55 * np.cos(q * 1.41 - order * 0.29)
        pos_order = points + normal * order_gap[:, None]
        neg_order = points - normal * order_gap[:, None]
        draw_open(masks["positive_fold_faces_a"], pos, 1.0, 4)
        draw_open(masks["negative_fold_faces_b"], neg, 1.0, 4)
        draw_open(masks["ray_envelope_cores"], points, 0.94, 2)

        # Each diffraction order has different aperture stops, breaking any
        # chance of a uniform parallel-rail wallpaper.
        gate = ((np.arange(len(q)) // (53 + 3 * (order % 4))
                 + order) % 4 != 1)
        p_order = pos_order.copy()
        n_order = neg_order.copy()
        p_order[~gate] = np.nan
        n_order[np.roll(~gate, 17 + order % 5)] = np.nan
        # Split NaN-gated order paths into contiguous pieces.
        for target, data in ((masks["positive_diffraction_orders_a"], p_order),
                             (masks["negative_diffraction_orders_b"], n_order)):
            finite = np.isfinite(data).all(axis=1)
            starts = np.where(finite & ~np.r_[False, finite[:-1]])[0]
            ends = np.where(finite & ~np.r_[finite[1:], False])[0] + 1
            for start, end in zip(starts, ends):
                if end - start > 2:
                    draw_open(target, data[start:end], 0.90, 2)

        shear_indices = (181 + 9 * order, 462 - 7 * (order % 6),
                         701 - 5 * order)
        for idx in shear_indices:
            idx = int(np.clip(idx, 8, len(points) - 9))
            centre = points[idx]
            n = normal[idx]
            a_pt = centre - n * (5.0 + order % 3)
            b_pt = centre + n * (5.0 + order % 3)
            _draw_line(shear_cut, a_pt, b_pt, 1.0, 5)
            _draw_line(masks["pupil_phase_shears"], a_pt, b_pt, 1.0, 3)
            tangent_unit = tangent[idx] / speed[idx]
            _draw_line(masks["lash_phase_breaks"],
                       a_pt - tangent_unit * 2.0,
                       a_pt + tangent_unit * 3.0, 1.0, 2)
            _draw_line(masks["lash_phase_breaks"],
                       b_pt - tangent_unit * 3.0,
                       b_pt + tangent_unit * 2.0, 1.0, 2)

        # One true curvature maximum per open envelope becomes a broken glint
        # face, not a dot or repeated eye highlight.
        idx = int(np.argmax(curvature[70:-70]) + 70)
        tangent_unit = tangent[idx] / speed[idx]
        _draw_line(masks["cusp_glint_discontinuities"],
                   points[idx] - tangent_unit * 3.0,
                   points[idx] + tangent_unit * (3.0 + order % 3), 1.0, 3)

        lip_start = 287 + (order * 37) % 219
        lip_end = min(len(points), lip_start + 58 + 4 * (order % 5))
        draw_open(masks["eyelid_occlusion_lips"],
                  points[lip_start:lip_end] - normal[lip_start:lip_end] * 1.7,
                  0.96, 5)
        for idx in range(97 + order % 11, len(points) - 40, 137 + order % 9):
            if (idx // 13 + order) % 3 == 0:
                _draw_line(masks["cracked_wavefront_relays"],
                           neg[idx], neg_order[idx], 1.0, 2)
        draw_open(phase_tone, points, 0.09 + 0.061 * order, 5)

    cut = _f32(cv2.GaussianBlur(shear_cut, (0, 0), 0.55))
    for name in ("positive_fold_faces_a", "negative_fold_faces_b",
                 "ray_envelope_cores", "positive_diffraction_orders_a",
                 "negative_diffraction_orders_b"):
        masks[name] = _f32(masks[name] * (1.0 - cut))

    banks = dict(
        positive_fold_faces_a="A", negative_fold_faces_b="B",
        ray_envelope_cores="N", positive_diffraction_orders_a="A",
        negative_diffraction_orders_b="B", pupil_phase_shears="N",
        cusp_glint_discontinuities="A", eyelid_occlusion_lips="B",
        lash_phase_breaks="N", cracked_wavefront_relays="B",
    )
    pa = masks["positive_fold_faces_a"]
    pb = masks["negative_fold_faces_b"]
    core = masks["ray_envelope_cores"]
    oa = masks["positive_diffraction_orders_a"]
    ob = masks["negative_diffraction_orders_b"]
    shear = masks["pupil_phase_shears"]
    glint = masks["cusp_glint_discontinuities"]
    eyelid = masks["eyelid_occlusion_lips"]
    lash = masks["lash_phase_breaks"]
    cracks = masks["cracked_wavefront_relays"]
    m_field = (10.0 + 208.0 * pa + 144.0 * core + 182.0 * oa
               + 236.0 * glint + 58.0 * lash)
    r_field = (216.0 - 158.0 * shear - 118.0 * lash - 86.0 * core
               + 32.0 * cracks - 46.0 * eyelid)
    cc_field = (12.0 + 210.0 * pb + 186.0 * ob + 228.0 * eyelid
                + 172.0 * cracks + 48.0 * core)
    x, y = _xy()
    tone = _norm(0.61 * cv2.GaussianBlur(phase_tone, (0, 0), 3.0)
                 + 0.22 * x / _WORK + 0.17 * y / _WORK)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w27() -> _Grammar:
    """Distributed fold→cusp→occlusion→relay catastrophe event ledger.

    SPB-WILDS WR-27, 2026-08-24.  W26 was self-rejected because unchanged open
    envelopes crossed at one shared focus and became a hub/fan.  W27 has no
    card-spanning carrier.  Nine unequal ray genealogies enter from different
    boundaries; each fold collapses into a cusp, is physically severed by a
    pupil occlusion, relays through a different optical order, and terminates
    in a clipped return.  Every visible auxiliary mark is a state transition
    of that genealogy.  No mesh/cell, paver, hub, closed loop, flow fill,
    scalar marble, density/fuzz, random line scatter, or eye glyph is present.
    """
    names = (
        "positive_fold_faces_a", "negative_fold_faces_b",
        "ray_envelope_cores", "positive_diffraction_orders_a",
        "negative_diffraction_orders_b", "pupil_phase_shears",
        "cusp_glint_discontinuities", "eyelid_occlusion_lips",
        "lash_phase_breaks", "cracked_wavefront_relays",
    )
    masks = _new_marks(*names)
    phase_tone = np.zeros((_WORK, _WORK), np.float32)

    # Explicit boundary-to-boundary histories.  They are one optical event
    # ledger, not sampled placements: anchor changes mark real aberration and
    # occlusion transitions, and no two chains share an entry, focus, or exit.
    histories = (
        ((-38, 62), (64, 34), (139, 128), (246, 91), (356, 144), (538, 113)),
        ((74, -42), (37, 76), (121, 183), (71, 302), (154, 405), (118, 548)),
        ((545, 39), (449, 83), (398, 177), (454, 272), (383, 386), (432, 548)),
        ((-43, 252), (58, 221), (151, 286), (232, 239), (323, 318), (547, 276)),
        ((210, -39), (252, 62), (344, 116), (307, 214), (409, 249), (548, 218)),
        ((-39, 467), (64, 426), (152, 481), (243, 415), (345, 482), (523, 549)),
        ((443, -43), (397, 49), (302, 102), (344, 190), (244, 270), (-37, 181)),
        ((545, 441), (457, 398), (424, 314), (332, 344), (247, 286), (172, 548)),
        ((-44, 354), (48, 372), (103, 319), (182, 363), (238, 490), (356, 548)),
    )

    def catmull(points: Sequence[Tuple[float, float]], samples: int = 90
                ) -> np.ndarray:
        p = np.asarray(points, np.float32)
        padded = np.vstack([p[0], p, p[-1]])
        out = []
        for segment in range(1, len(padded) - 2):
            p0, p1, p2, p3 = padded[segment - 1:segment + 3]
            t = np.linspace(0.0, 1.0, samples, endpoint=False,
                            dtype=np.float32)[:, None]
            curve = 0.5 * ((2.0 * p1)
                           + (-p0 + p2) * t
                           + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
                           + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t * t * t)
            out.append(curve)
        out.append(p[-1][None, :])
        return np.vstack(out).astype(np.float32)

    def draw_range(mask: np.ndarray, points: np.ndarray, start: float,
                   end: float, value: float, width: int) -> None:
        lo = int(np.clip(round(start * (len(points) - 1)), 0, len(points) - 2))
        hi = int(np.clip(round(end * (len(points) - 1)), lo + 2, len(points)))
        cv2.polylines(mask, [np.rint(points[lo:hi]).astype(np.int32)], False,
                      float(value), int(width), cv2.LINE_AA)

    for history_index, anchors in enumerate(histories):
        points = catmull(anchors, 94 + 3 * (history_index % 4))
        tangent = np.gradient(points, axis=0)
        speed = np.maximum(np.linalg.norm(tangent, axis=1), 1.0e-4)
        normal = np.column_stack([-tangent[:, 1] / speed,
                                  tangent[:, 0] / speed]).astype(np.float32)
        s = np.linspace(0.0, 1.0, len(points), dtype=np.float32)

        # At the first cusp the two fold faces collapse, cross, and reopen.
        cusp_coordinate = np.abs(s - 0.285) / 0.095
        side = 3.0 + 0.45 * np.sin(s * 8.0 + history_index * 0.51)
        side *= np.clip(cusp_coordinate, 0.0, 1.0)
        sign = np.where(s < 0.285, 1.0, -1.0).astype(np.float32)
        positive = points + normal * (side * sign)[:, None]
        negative = points - normal * (side * sign)[:, None]

        # Fold and clipped-return intervals are separated by a genuine pupil
        # gap and a relay-only interval.  No core/face can be traced unchanged
        # across the card.
        for start, end in ((0.00, 0.405), (0.705, 0.925)):
            draw_range(masks["positive_fold_faces_a"], positive,
                       start, end, 1.0, 4)
            draw_range(masks["negative_fold_faces_b"], negative,
                       start, end, 1.0, 4)
            draw_range(masks["ray_envelope_cores"], points,
                       start, end, 0.94, 2)

        # The relay interval changes optical order and follows unequal sides;
        # its fragments are stopped twice by aperture breaks.
        gap = 7.0 + 0.45 * np.cos(s * 6.0 - history_index * 0.37)
        pos_order = points + normal * gap[:, None]
        neg_order = points - normal * gap[:, None]
        for start, end in ((0.505, 0.585), (0.615, 0.695)):
            draw_range(masks["positive_diffraction_orders_a"], pos_order,
                       start, end, 0.90, 2)
            draw_range(masks["negative_diffraction_orders_b"], neg_order,
                       start + 0.008, end - 0.006, 0.90, 2)

        # Pupil shears are the two severed ends of the main fold.  Their lash
        # breaks and eyelid lips attach locally instead of forming a new field.
        for cut_s in (0.425, 0.485, 0.715, 0.945):
            idx = int(round(cut_s * (len(points) - 1)))
            centre = points[idx]
            n = normal[idx]
            tangent_unit = tangent[idx] / speed[idx]
            a_pt = centre - n * (5.0 + history_index % 3)
            b_pt = centre + n * (5.0 + history_index % 3)
            _draw_line(masks["pupil_phase_shears"], a_pt, b_pt, 1.0, 3)
            _draw_line(masks["lash_phase_breaks"],
                       a_pt - tangent_unit * 2.0,
                       a_pt + tangent_unit * 3.0, 1.0, 2)
            _draw_line(masks["lash_phase_breaks"],
                       b_pt - tangent_unit * 3.0,
                       b_pt + tangent_unit * 2.0, 1.0, 2)

        # One curvature event and one clipped return per genealogy.  They vary
        # in length, orientation and age but are never repeated eye/glint dots.
        cusp_idx = int(round(0.285 * (len(points) - 1)))
        tangent_unit = tangent[cusp_idx] / speed[cusp_idx]
        _draw_line(masks["cusp_glint_discontinuities"],
                   points[cusp_idx] - tangent_unit * 2.0,
                   points[cusp_idx] + tangent_unit * (4.0 + history_index % 3),
                   1.0, 3)
        draw_range(masks["eyelid_occlusion_lips"],
                   points - normal * 1.8, 0.925,
                   0.985, 0.96, 5)

        # A short cracked relay attaches the two separated optical orders at
        # the second aperture stop.  It is never a free crack substrate.
        relay_idx = int(round(0.603 * (len(points) - 1)))
        _draw_line(masks["cracked_wavefront_relays"],
                   neg_order[relay_idx], pos_order[relay_idx], 1.0, 2)
        draw_range(phase_tone, points, 0.0, 0.405,
                   0.13 + 0.083 * history_index, 5)
        draw_range(phase_tone, points, 0.705, 0.985,
                   0.19 + 0.079 * history_index, 5)

    banks = dict(
        positive_fold_faces_a="A", negative_fold_faces_b="B",
        ray_envelope_cores="N", positive_diffraction_orders_a="A",
        negative_diffraction_orders_b="B", pupil_phase_shears="N",
        cusp_glint_discontinuities="A", eyelid_occlusion_lips="B",
        lash_phase_breaks="N", cracked_wavefront_relays="B",
    )
    pa = masks["positive_fold_faces_a"]
    pb = masks["negative_fold_faces_b"]
    core = masks["ray_envelope_cores"]
    oa = masks["positive_diffraction_orders_a"]
    ob = masks["negative_diffraction_orders_b"]
    shear = masks["pupil_phase_shears"]
    glint = masks["cusp_glint_discontinuities"]
    eyelid = masks["eyelid_occlusion_lips"]
    lash = masks["lash_phase_breaks"]
    cracks = masks["cracked_wavefront_relays"]
    m_field = (10.0 + 208.0 * pa + 146.0 * core + 184.0 * oa
               + 236.0 * glint + 58.0 * lash)
    r_field = (216.0 - 158.0 * shear - 118.0 * lash - 88.0 * core
               + 34.0 * cracks - 48.0 * eyelid)
    cc_field = (12.0 + 210.0 * pb + 188.0 * ob + 228.0 * eyelid
                + 174.0 * cracks + 48.0 * core)
    x, y = _xy()
    tone = _norm(0.63 * cv2.GaussianBlur(phase_tone, (0, 0), 3.0)
                 + 0.20 * x / _WORK + 0.17 * y / _WORK)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w28() -> _Grammar:
    """Aperture-split butterfly diffraction critical-event field.

    SPB-WILDS WR-28, 2026-08-24.  W27 was self-rejected: its nine explicit
    genealogies still read as sparse card-spanning rails.  W28 resets from an
    empty topology and evaluates one non-periodic sixth-order catastrophe
    integral over a curved 2-D control-plane slice.  The positive and negative
    halves of the same physical aperture are accumulated separately.  Their
    fold crests, destructive shears, cusp glints, occlusion lips, and coherent
    relays are different states of that one wavefront; no independent texture
    is added to disguise a carrier.  Only diffraction-local high-pass anatomy
    is painted -- never the broad scalar power field.
    """
    names = (
        "positive_aperture_fold_faces_a",
        "negative_aperture_fold_faces_b",
        "combined_ray_envelope_cores",
        "constructive_diffraction_orders_a",
        "destructive_diffraction_orders_b",
        "pupil_phase_shears",
        "cusp_glint_discontinuities",
        "aperture_occlusion_lips",
        "wavefront_branch_relays",
    )
    masks = _new_marks(*names)

    # Curved control-plane slice through one butterfly potential.  These are
    # low-order control terms, not a noise/seed warp, repeating lattice, or
    # collection of placed specimens.
    x_px, y_px = _xy()
    x = (x_px / (_WORK - 1.0) - 0.5) * 2.0
    y = (y_px / (_WORK - 1.0) - 0.5) * 2.0
    a = -2.32 - 0.31 * x + 0.27 * y
    b = (0.34 - 0.68 * x + 0.91 * y + 1.08 * x * y)
    c = (-0.28 + 2.18 * x + 0.72 * y
         - 0.93 * (x * x - 0.72 * y * y))
    d = (0.17 - 0.82 * x + 2.73 * y
         + 1.19 * (x * x * y - 0.48 * y * y * y))

    positive = np.zeros((_WORK, _WORK), np.complex64)
    negative = np.zeros_like(positive)
    states = np.linspace(-2.72, 2.72, 112, dtype=np.float32)
    wave = np.float32(15.2)
    for state in states:
        t = np.float32(state)
        phase = (t ** 6 / 6.0 + a * (t ** 4 / 4.0)
                 + b * (t ** 3 / 3.0) + c * (t * t / 2.0) + d * t)
        sample = (np.exp((1j * wave * phase).astype(np.complex64))
                  * np.float32(np.exp(-0.12 * float(t * t))))
        if t >= 0.0:
            positive += sample
        else:
            negative += sample

    total = positive + negative

    def robust(field: np.ndarray, lo: float = 4.0,
               hi: float = 99.6) -> np.ndarray:
        u = np.asarray(field, np.float32)
        low, high = np.percentile(u, (lo, hi))
        return _f32((u - float(low)) / max(float(high - low), 1.0e-6))

    def crest(field: np.ndarray, sigma: float = 1.55,
              floor: float = 0.50, feather: float = 0.14) -> np.ndarray:
        # Oscillatory diffraction maxima are finite-width physical orders.
        # Subtracting the local envelope suppresses the forbidden broad scalar
        # field and retains only the sharp folds and their attached fringes.
        u = robust(np.log1p(np.maximum(field, 0.0)))
        local = cv2.GaussianBlur(u, (0, 0), sigma)
        high = robust(np.maximum(u - local, 0.0), 1.0, 99.0)
        return _f32((high - floor) / max(feather, 0.02))

    p_power = np.abs(positive).astype(np.float32) ** 2
    n_power = np.abs(negative).astype(np.float32) ** 2
    t_power = np.abs(total).astype(np.float32) ** 2
    p_amp = np.sqrt(p_power + 1.0e-5)
    n_amp = np.sqrt(n_power + 1.0e-5)
    balance = (p_amp - n_amp) / np.maximum(p_amp + n_amp, 1.0e-5)
    cross = positive * np.conj(negative)
    relative_phase = np.angle(cross).astype(np.float32)
    coherence = np.cos(relative_phase).astype(np.float32)
    quadrature = np.sin(relative_phase).astype(np.float32)

    p_crest = crest(p_power, 1.35, 0.46, 0.13)
    n_crest = crest(n_power, 1.35, 0.46, 0.13)
    t_crest = crest(t_power, 1.65, 0.58, 0.12)
    constructive = crest(t_power / np.maximum(p_amp + n_amp, 0.1),
                         1.25, 0.48, 0.13)
    cancellation = crest((p_amp + n_amp) / np.maximum(np.sqrt(t_power), 0.2),
                         1.15, 0.53, 0.12)

    p_domain = _f32((balance + 0.24) / 0.32)
    n_domain = _f32((-balance + 0.24) / 0.32)
    coherent = _f32((coherence - 0.10) / 0.48)
    opposed = _f32((-coherence - 0.05) / 0.46)
    both = robust(np.minimum(p_amp, n_amp), 8.0, 97.5)

    masks["positive_aperture_fold_faces_a"] = _f32(p_crest * p_domain)
    masks["negative_aperture_fold_faces_b"] = _f32(n_crest * n_domain)
    masks["combined_ray_envelope_cores"] = _f32(t_crest * (0.35 + 0.65 * both))
    masks["constructive_diffraction_orders_a"] = _f32(
        constructive * coherent * (0.28 + 0.72 * both))
    masks["destructive_diffraction_orders_b"] = _f32(
        cancellation * opposed * (0.28 + 0.72 * both))

    # Phase shear is a derivative event, not another threshold contour.
    gx = cv2.Sobel(relative_phase, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(relative_phase, cv2.CV_32F, 0, 1, ksize=3)
    phase_jump = robust(np.hypot(gx, gy), 30.0, 99.2)
    masks["pupil_phase_shears"] = _f32(
        phase_jump * opposed * (0.18 + 0.82 * both) * t_crest)

    # Curvature concentrates at fold/cusp transitions.  Glints remain short
    # pieces of an envelope rather than detached dots or repeated eye icons.
    power_u = robust(np.log1p(t_power))
    lap = np.abs(cv2.Laplacian(power_u, cv2.CV_32F, ksize=3))
    curvature = robust(lap, 45.0, 99.4)
    masks["cusp_glint_discontinuities"] = _f32(
        curvature * t_crest * coherent * both)

    # Dominance changes are physical aperture occlusions.  Restrict them to
    # active orders so no macro balance contour survives across the card.
    dominance_grad = np.hypot(
        cv2.Sobel(balance, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(balance, cv2.CV_32F, 0, 1, ksize=3))
    occlusion = robust(dominance_grad, 35.0, 99.0)
    masks["aperture_occlusion_lips"] = _f32(
        occlusion * (0.52 * p_crest + 0.48 * n_crest) * opposed)

    # Quadrature is where one aperture branch relays into the other.  Again,
    # it is painted only at existing finite diffraction orders.
    relay_phase = _f32((np.abs(quadrature) - 0.48) / 0.34)
    masks["wavefront_branch_relays"] = _f32(
        relay_phase * both * np.maximum(constructive, cancellation))

    banks = dict(
        positive_aperture_fold_faces_a="A",
        negative_aperture_fold_faces_b="B",
        combined_ray_envelope_cores="N",
        constructive_diffraction_orders_a="A",
        destructive_diffraction_orders_b="B",
        pupil_phase_shears="N",
        cusp_glint_discontinuities="A",
        aperture_occlusion_lips="B",
        wavefront_branch_relays="N",
    )
    pa = masks["positive_aperture_fold_faces_a"]
    nb = masks["negative_aperture_fold_faces_b"]
    core = masks["combined_ray_envelope_cores"]
    ca = masks["constructive_diffraction_orders_a"]
    db = masks["destructive_diffraction_orders_b"]
    shear = masks["pupil_phase_shears"]
    glint = masks["cusp_glint_discontinuities"]
    lip = masks["aperture_occlusion_lips"]
    relay = masks["wavefront_branch_relays"]
    m_field = (8.0 + 214.0 * pa + 172.0 * ca + 96.0 * core
               + 232.0 * glint + 54.0 * relay)
    r_field = (240.0 - 205.0 * shear - 165.0 * core - 109.0 * ca
               + 53.0 * relay - 73.0 * lip)
    cc_field = (10.0 + 216.0 * nb + 188.0 * db + 154.0 * lip
                + 82.0 * shear + 46.0 * relay)
    tone = _norm(0.44 * power_u
                 + 0.24 * (relative_phase / (2.0 * np.pi) + 0.5)
                 + 0.18 * (balance * 0.5 + 0.5)
                 + 0.14 * curvature)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w29() -> _Grammar:
    """Non-cellular directed cusp/fold DAG with event-local optical anatomy.

    SPB-WILDS WR-29, 2026-08-24.  W28 was self-rejected because every mask
    collapsed to the same directional diffraction-filament shelf.  W29 keeps
    the reserved catastrophe-optics process but discards the scalar field.
    Eleven unequal propagation epochs create a directed, degree-limited ray
    genealogy.  Critical edges are cropped to short ancestry stubs; the paint
    is carried by fold wedges, cusp fins, occlusion lips, transverse order
    returns, phase notches, relay scars and order-swap blocks whose geometry
    comes from each event's actual in/out degree and turning angle.  There is
    no closed face, cell, common focus, full-card rail, random placement field,
    scalar marble, filled flow band, or repeated junction stamp.
    """
    names = (
        "positive_fold_wedges_a", "negative_fold_wedges_b",
        "cropped_critical_ancestry", "cusp_glint_fins",
        "occlusion_recoil_lips", "positive_order_returns_a",
        "negative_order_returns_b", "phase_shear_notches",
        "relay_scar_bridges", "order_swap_blocks",
    )
    masks = _new_marks(*names)
    phase_tone = np.zeros((_WORK, _WORK), np.float32)

    # Propagation epochs are one evolving ray sheet, not a placement grid.
    # Count changes are the fold births/deaths; irrational phase progression
    # keeps events unequal without a seed, noise field, or rank quantizer.
    counts = (13, 17, 14, 18, 15, 19, 14, 18, 16, 17, 13)
    golden = np.float32(0.6180339887498948)
    epochs = []
    for epoch_index, count in enumerate(counts):
        tau = epoch_index / float(len(counts) - 1)
        points = []
        for local_index in range(count):
            orbit = np.mod((local_index + 0.5) * golden
                           + 0.173 * epoch_index
                           + 0.031 * epoch_index * epoch_index, 1.0)
            raw_y = 9.0 + 494.0 * orbit
            raw_x = -18.0 + 548.0 * tau
            # Low-order refractive displacement is part of the event history;
            # it is never rendered as a texture or used as a novelty overlay.
            px = (raw_x + 17.0 * np.sin(raw_y / 73.0 + epoch_index * 0.43)
                  + 7.0 * np.sin((raw_y + raw_x) / 119.0))
            py = (raw_y + 13.0 * np.sin(raw_x / 83.0 - orbit * 2.7)
                  + 6.0 * np.cos((1.4 * raw_x - raw_y) / 137.0))
            points.append(np.asarray([px, py], np.float32))
        # Rank along the local wavefront defines ancestry without producing
        # visible rows; x displacement above is already event-dependent.
        epochs.append(sorted(points, key=lambda point: float(point[1])))

    nodes = []
    node_epoch = []
    epoch_ids = []
    for epoch_index, points in enumerate(epochs):
        ids = []
        for point in points:
            ids.append(len(nodes))
            nodes.append(point)
            node_epoch.append(epoch_index)
        epoch_ids.append(ids)

    # Quantile-preserving transitions produce only 1↔1, 1↔2 and 2↔1
    # events.  Extra coverage edges ensure every ray has ancestry/descendants;
    # no node can become a common hub.
    edge_set = set()
    for epoch_index in range(len(epoch_ids) - 1):
        source_ids = epoch_ids[epoch_index]
        target_ids = epoch_ids[epoch_index + 1]
        ns, nt = len(source_ids), len(target_ids)
        for target_rank, target_id in enumerate(target_ids):
            q = (target_rank + 0.5) / nt
            source_rank = int(np.clip(round(q * ns - 0.5), 0, ns - 1))
            edge_set.add((source_ids[source_rank], target_id))
        for source_rank, source_id in enumerate(source_ids):
            q = (source_rank + 0.5) / ns
            target_rank = int(np.clip(round(q * nt - 0.5), 0, nt - 1))
            edge_set.add((source_id, target_ids[target_rank]))

    incoming = [[] for _ in nodes]
    outgoing = [[] for _ in nodes]
    for left, right in sorted(edge_set):
        outgoing[left].append(right)
        incoming[right].append(left)

    def unit(vector: np.ndarray) -> np.ndarray:
        length = float(np.linalg.norm(vector))
        if length < 1.0e-5:
            return np.asarray([1.0, 0.0], np.float32)
        return (vector / length).astype(np.float32)

    def quad(mask: np.ndarray, centre: np.ndarray, tangent: np.ndarray,
             length: float, width: float, value: float = 1.0,
             skew: float = 0.0) -> None:
        t = unit(tangent)
        n = np.asarray([-t[1], t[0]], np.float32)
        half_l = 0.5 * float(length)
        half_w = 0.5 * float(width)
        pts = np.asarray([
            centre - t * half_l - n * (half_w * (0.76 + skew)),
            centre + t * half_l - n * (half_w * (1.18 - skew)),
            centre + t * half_l + n * (half_w * (0.72 + skew)),
            centre - t * half_l + n * (half_w * (1.12 - skew)),
        ], np.int32)
        cv2.fillConvexPoly(mask, pts, float(value), cv2.LINE_AA)

    def wedge(mask: np.ndarray, root: np.ndarray, tangent: np.ndarray,
              length: float, width: float, flip: float,
              value: float = 1.0) -> None:
        t = unit(tangent)
        n = np.asarray([-t[1], t[0]], np.float32) * float(flip)
        tip = root + t * float(length)
        pts = np.asarray([
            root - t * 1.0 - n * width * 0.32,
            root + n * width * 0.64,
            tip + n * width * 0.16,
            tip - n * width * 0.24,
        ], np.int32)
        cv2.fillConvexPoly(mask, pts, float(value), cv2.LINE_AA)

    # Crop every critical edge to unequal entry/exit stubs.  The graph remains
    # auditable in isolation but can never become the dominant paint carrier.
    for edge_index, (left, right) in enumerate(sorted(edge_set)):
        a = nodes[left]
        b = nodes[right]
        delta = b - a
        normal = np.asarray([-delta[1], delta[0]], np.float32)
        normal = unit(normal)
        bend = normal * (3.0 + 2.0 * ((left + 2 * right) % 5)) \
            * (-1.0 if edge_index & 1 else 1.0)
        control = 0.5 * (a + b) + bend
        t = np.linspace(0.0, 1.0, 36, dtype=np.float32)[:, None]
        curve = ((1.0 - t) ** 2 * a + 2.0 * (1.0 - t) * t * control
                 + t * t * b)
        entry_end = 5 + (edge_index % 4)
        exit_start = 27 - (edge_index % 5)
        cv2.polylines(masks["cropped_critical_ancestry"],
                      [np.rint(curve[:entry_end]).astype(np.int32)], False,
                      0.74, 2, cv2.LINE_AA)
        cv2.polylines(masks["cropped_critical_ancestry"],
                      [np.rint(curve[exit_start:]).astype(np.int32)], False,
                      0.90, 2, cv2.LINE_AA)

    for node_index, point in enumerate(nodes):
        prev_dirs = [unit(point - nodes[parent]) for parent in incoming[node_index]]
        next_dirs = [unit(nodes[child] - point) for child in outgoing[node_index]]
        vectors = prev_dirs + next_dirs
        tangent = unit(np.sum(vectors, axis=0)) if vectors else np.asarray(
            [1.0, 0.0], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        in_degree = len(prev_dirs)
        out_degree = len(next_dirs)
        event_epoch = node_epoch[node_index]
        event_code = (node_index * 7 + event_epoch * 11) % 13
        turn = 0.0
        if prev_dirs and next_dirs:
            turn = float(np.cross(prev_dirs[0], next_dirs[-1]))

        # 1→2 births and 2→1 annihilations own genuinely different wedge
        # geometry.  Through-events use asymmetric paired fold-side plates.
        if out_degree == 2:
            for branch_index, direction in enumerate(next_dirs):
                target = (masks["positive_fold_wedges_a"]
                          if branch_index == 0 else
                          masks["negative_fold_wedges_b"])
                wedge(target, point + direction * 1.0, direction,
                      8.0 + (event_code % 6), 4.0 + (event_code % 4),
                      -1.0 if branch_index == 0 else 1.0,
                      0.76 + 0.04 * (event_code % 5))
        elif in_degree == 2:
            for branch_index, direction in enumerate(prev_dirs):
                target = (masks["negative_fold_wedges_b"]
                          if branch_index == 0 else
                          masks["positive_fold_wedges_a"])
                wedge(target, point - direction * 1.0, -direction,
                      7.0 + ((event_code + branch_index) % 7),
                      4.0 + ((event_code + 2 * branch_index) % 4),
                      1.0 if branch_index == 0 else -1.0,
                      0.78 + 0.04 * ((event_code + branch_index) % 4))
        else:
            length = 9.0 + (event_code % 8)
            width = 4.0 + (event_code % 5)
            wedge(masks["positive_fold_wedges_a"],
                  point - normal * (1.3 + event_code % 3), tangent,
                  length, width, -1.0, 0.78 + 0.04 * (event_code % 5))
            wedge(masks["negative_fold_wedges_b"],
                  point + normal * (1.6 + (event_code + 1) % 3), tangent,
                  length * (0.72 + 0.05 * (event_code % 4)),
                  width * (0.78 + 0.04 * ((event_code + 2) % 4)),
                  1.0, 0.78 + 0.04 * ((event_code + 3) % 5))

        # True cusp events receive a triangular fin whose long axis is the
        # unequal in/out bisector.  Turn magnitude changes its silhouette.
        if in_degree != out_degree or abs(turn) > 0.26:
            fin_length = 5.0 + (event_code % 4)
            fin_width = 3.0 + ((event_code + 1) % 4)
            wedge(masks["cusp_glint_fins"],
                  point + tangent * 1.5, tangent + normal * turn,
                  fin_length, fin_width, -1.0 if turn < 0.0 else 1.0, 1.0)

        # Occlusion lips sit across annihilations or every fourth high-shear
        # through-event.  Their skew comes from actual local turn, so they are
        # not a repeated bracket glyph.
        if in_degree > out_degree or (event_code % 4 == 0 and in_degree):
            quad(masks["occlusion_recoil_lips"],
                 point - tangent * (2.0 + event_code % 3), normal + tangent * turn,
                 7.0 + (event_code % 6), 4.0 + ((event_code + 2) % 4),
                 0.84 + 0.04 * (event_code % 4),
                 np.clip(turn, -0.35, 0.35))

        # Diffraction returns are transverse finite plates, not parallel
        # carrier lines.  Positive and negative orders occupy different sides
        # and exchange order at every third event.
        order_swap = (event_code % 3 == 0)
        for order in range(1 + (event_code % 3)):
            offset = tangent * (5.0 + order * (3.5 + 0.3 * (event_code % 4)))
            side = normal * (2.0 + 1.4 * order)
            a_centre = point + offset + (-side if order_swap else side)
            b_centre = point + offset + (side if order_swap else -side)
            bar_direction = normal + tangent * (0.18 * (order - 1) + 0.22 * turn)
            quad(masks["positive_order_returns_a"], a_centre,
                 bar_direction, 5.0 + ((event_code + order) % 5),
                 2.0 + ((event_code + order) % 3), 0.82)
            quad(masks["negative_order_returns_b"], b_centre,
                 bar_direction - tangent * 0.16,
                 4.0 + ((event_code + 2 * order) % 6),
                 2.0 + ((event_code + order + 1) % 3), 0.82)

        # Every event has one causal phase notch cut across a named fold face.
        notch_centre = point - tangent * (2.0 + event_code % 4)
        quad(masks["phase_shear_notches"], notch_centre,
             normal + tangent * turn, 4.0 + (event_code % 4),
             2.0 + ((event_code + 1) % 3), 0.88)

        # Split/merge relays are short bent scars linking the local branch
        # sides; no relay is free-floating or spans between unrelated events.
        if in_degree + out_degree >= 3:
            relay = np.asarray([
                point - tangent * 4.0 - normal * (2.0 + abs(turn) * 3.0),
                point - tangent * 0.5 + normal * (1.0 + turn * 2.0),
                point + tangent * (3.5 + event_code % 3)
                + normal * (-1.5 + turn * 2.5),
            ], np.float32)
            cv2.polylines(masks["relay_scar_bridges"],
                          [np.rint(relay).astype(np.int32)], False,
                          0.94, 2 + (event_code % 2), cv2.LINE_AA)

        # Order swaps are quadrilateral phase blocks at only one third of
        # events.  Their aspect/axis derives from local turning and epoch age.
        if order_swap:
            quad(masks["order_swap_blocks"],
                 point + tangent * (1.5 + event_code % 3),
                 tangent + normal * (0.32 + turn),
                 4.0 + (event_code % 5), 3.0 + ((event_code + 2) % 4),
                 0.76 + 0.04 * (event_code % 5),
                 np.clip(-turn, -0.3, 0.3))

        # Tone is event age painted only through the event footprint.
        cv2.circle(phase_tone, tuple(np.rint(point).astype(int)),
                   6 + (event_code % 5),
                   float(0.08 + 0.083 * event_epoch + 0.011 * event_code),
                   -1, cv2.LINE_AA)

    banks = dict(
        positive_fold_wedges_a="A", negative_fold_wedges_b="B",
        cropped_critical_ancestry="N", cusp_glint_fins="A",
        occlusion_recoil_lips="B", positive_order_returns_a="A",
        negative_order_returns_b="B", phase_shear_notches="N",
        relay_scar_bridges="N", order_swap_blocks="B",
    )
    pa = masks["positive_fold_wedges_a"]
    nb = masks["negative_fold_wedges_b"]
    ancestry = masks["cropped_critical_ancestry"]
    cusp = masks["cusp_glint_fins"]
    lip = masks["occlusion_recoil_lips"]
    oa = masks["positive_order_returns_a"]
    ob = masks["negative_order_returns_b"]
    shear = masks["phase_shear_notches"]
    relay = masks["relay_scar_bridges"]
    swap = masks["order_swap_blocks"]
    m_field = (8.0 + 196.0 * pa + 176.0 * oa + 232.0 * cusp
               + 84.0 * ancestry + 54.0 * relay)
    r_field = (238.0 - 162.0 * shear - 116.0 * ancestry
               - 86.0 * relay + 34.0 * swap - 48.0 * lip)
    cc_field = (10.0 + 204.0 * nb + 182.0 * ob + 218.0 * lip
                + 164.0 * swap + 48.0 * relay)
    x_px, y_px = _xy()
    tone = _norm(0.66 * cv2.GaussianBlur(phase_tone, (0, 0), 2.0)
                 + 0.19 * x_px / _WORK + 0.15 * y_px / _WORK)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w30() -> _Grammar:
    """Directed fold sheet whose unequal event regions replace one another.

    SPB-WILDS WR-30, 2026-08-24.  W29 was self-rejected as a sparse repeated
    junction-stamp field.  W30 removes node glyphs entirely.  A dense directed
    ray genealogy progresses through five spatially coherent catastrophe
    regimes.  Paired fold sides terminate into cusp wedges; compressed spans
    disappear behind occlusion lips; stretched spans become transverse
    diffraction returns; high-shear spans become relay scars; order-swap spans
    exchange A/B plates.  No edge retains one mark language from entry to exit
    and no second carrier is added.  The ancestry core is visible only inside
    fold and cusp regimes, never as a full-card graph.
    """
    names = (
        "paired_positive_fold_sides_a", "paired_negative_fold_sides_b",
        "finite_envelope_cores", "true_cusp_wedges",
        "occlusion_recoil_lips", "positive_transverse_returns_a",
        "negative_transverse_returns_b", "phase_shear_notches",
        "relay_scar_zigzags", "order_swap_facets",
    )
    masks = _new_marks(*names)
    phase_tone = np.zeros((_WORK, _WORK), np.float32)

    counts = (21, 25, 22, 27, 23, 26, 21, 28, 24, 26, 22, 20)
    irrational = np.float32(0.6180339887498948)
    epochs = []
    for epoch_index, count in enumerate(counts):
        tau = epoch_index / float(len(counts) - 1)
        wavefront = []
        for rank in range(count):
            orbit = np.mod((rank + 0.5) * irrational
                           + 0.113 * epoch_index
                           + 0.019 * epoch_index * epoch_index, 1.0)
            y0 = 4.0 + 504.0 * orbit
            x0 = -24.0 + 560.0 * tau
            x1 = (x0 + 15.0 * np.sin(y0 / 68.0 + epoch_index * 0.39)
                  + 6.0 * np.sin((x0 + 1.3 * y0) / 127.0))
            y1 = (y0 + 15.0 * np.sin(x0 / 76.0 - orbit * 2.3)
                  + 8.0 * np.cos((1.5 * x0 - y0) / 143.0))
            wavefront.append(np.asarray([x1, y1], np.float32))
        epochs.append(sorted(wavefront, key=lambda p: float(p[1])))

    nodes = []
    epoch_ids = []
    ranks = []
    for epoch_index, points in enumerate(epochs):
        ids = []
        for rank, point in enumerate(points):
            ids.append(len(nodes))
            nodes.append(point)
            ranks.append((epoch_index, rank))
        epoch_ids.append(ids)

    edges = set()
    for epoch_index in range(len(epoch_ids) - 1):
        source_ids = epoch_ids[epoch_index]
        target_ids = epoch_ids[epoch_index + 1]
        ns, nt = len(source_ids), len(target_ids)
        for target_rank, target_id in enumerate(target_ids):
            source_rank = int(np.clip(
                round((target_rank + 0.5) * ns / nt - 0.5), 0, ns - 1))
            edges.add((source_ids[source_rank], target_id))
        for source_rank, source_id in enumerate(source_ids):
            target_rank = int(np.clip(
                round((source_rank + 0.5) * nt / ns - 0.5), 0, nt - 1))
            edges.add((source_id, target_ids[target_rank]))

    incoming = [[] for _ in nodes]
    outgoing = [[] for _ in nodes]
    for left, right in sorted(edges):
        outgoing[left].append(right)
        incoming[right].append(left)

    def unit(vector: np.ndarray) -> np.ndarray:
        magnitude = float(np.linalg.norm(vector))
        if magnitude < 1.0e-5:
            return np.asarray([1.0, 0.0], np.float32)
        return (vector / magnitude).astype(np.float32)

    def quad(mask: np.ndarray, centre: np.ndarray, direction: np.ndarray,
             length: float, width: float, value: float = 1.0,
             skew: float = 0.0) -> None:
        t = unit(direction)
        n = np.asarray([-t[1], t[0]], np.float32)
        hl, hw = 0.5 * float(length), 0.5 * float(width)
        polygon = np.asarray([
            centre - t * hl - n * hw * (0.72 + skew),
            centre + t * hl - n * hw * (1.18 - skew),
            centre + t * hl + n * hw * (0.78 + skew),
            centre - t * hl + n * hw * (1.10 - skew),
        ], np.int32)
        cv2.fillConvexPoly(mask, polygon, float(value), cv2.LINE_AA)

    def wedge(mask: np.ndarray, root: np.ndarray, direction: np.ndarray,
              length: float, width: float, side: float,
              value: float = 1.0) -> None:
        t = unit(direction)
        n = np.asarray([-t[1], t[0]], np.float32) * float(side)
        tip = root + t * float(length)
        polygon = np.asarray([
            root - t * 1.2 - n * width * 0.24,
            root + n * width * 0.68,
            tip + n * width * 0.13,
            tip - n * width * 0.22,
        ], np.int32)
        cv2.fillConvexPoly(mask, polygon, float(value), cv2.LINE_AA)

    def section(mask: np.ndarray, curve: np.ndarray, lo: float, hi: float,
                value: float, width: int, offset: float = 0.0) -> None:
        start = int(np.clip(round(lo * (len(curve) - 1)), 0, len(curve) - 2))
        stop = int(np.clip(round(hi * (len(curve) - 1)), start + 2, len(curve)))
        points = curve.copy()
        if abs(offset) > 1.0e-5:
            tangent = np.gradient(points, axis=0)
            speed = np.maximum(np.linalg.norm(tangent, axis=1), 1.0e-5)
            normal = np.column_stack([-tangent[:, 1] / speed,
                                      tangent[:, 0] / speed])
            points = points + normal * float(offset)
        cv2.polylines(mask,
                      [np.rint(points[start:stop]).astype(np.int32)], False,
                      float(value), int(width), cv2.LINE_AA)

    for edge_index, (left, right) in enumerate(sorted(edges)):
        a, b = nodes[left], nodes[right]
        epoch_index, source_rank = ranks[left]
        delta = b - a
        tangent = unit(delta)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        # Actual genealogy curvature, compression and branching affect the
        # event silhouette.  The five regimes travel diagonally through the
        # wavefront; they are not rectangular screen partitions.
        source_count = counts[epoch_index]
        q = source_rank / max(source_count - 1, 1)
        event_class = int(np.floor(np.mod(
            1.35 * epoch_index + 4.7 * q + 0.11 * epoch_index * q, 5.0)))
        if len(outgoing[left]) > 1 or len(incoming[right]) > 1:
            event_class = 1  # true cusp birth/annihilation
        length = float(np.linalg.norm(delta))
        if length < 45.0 and event_class not in (1, 4):
            event_class = 2  # compressed/occluded
        bend_sign = -1.0 if ((edge_index + source_rank) & 1) else 1.0
        bend = normal * bend_sign * (4.0 + (edge_index % 5))
        control = 0.5 * (a + b) + bend
        u = np.linspace(0.0, 1.0, 54, dtype=np.float32)[:, None]
        curve = ((1.0 - u) ** 2 * a + 2.0 * (1.0 - u) * u * control
                 + u * u * b)
        curve_tangent = np.gradient(curve, axis=0)
        mid = len(curve) // 2
        mid_t = unit(curve_tangent[mid])
        mid_n = np.asarray([-mid_t[1], mid_t[0]], np.float32)
        code = (edge_index * 7 + source_rank * 3 + epoch_index * 5) % 17
        paint_value = 0.74 + 0.04 * (code % 6)

        if event_class == 0:
            # Paired fold regime.  Each side terminates before the node and
            # changes lateral order once, preventing a traceable rail.
            split = 0.44 + 0.04 * ((code % 5) - 2)
            section(masks["paired_positive_fold_sides_a"], curve,
                    0.04, split, paint_value, 4 + (code % 3), 3.0)
            section(masks["paired_negative_fold_sides_b"], curve,
                    0.08, split - 0.02, paint_value, 3 + ((code + 1) % 3), -3.0)
            section(masks["paired_positive_fold_sides_a"], curve,
                    split + 0.12, 0.94, paint_value, 3 + ((code + 2) % 3), -2.6)
            section(masks["paired_negative_fold_sides_b"], curve,
                    split + 0.15, 0.91, paint_value, 4 + ((code + 1) % 2), 2.6)
            section(masks["finite_envelope_cores"], curve,
                    0.08, split - 0.03, 0.82, 2)
            section(masks["finite_envelope_cores"], curve,
                    split + 0.16, 0.88, 0.68, 2)
            # Phase shear physically occupies the missing interval.
            shear_centre = curve[int(split * (len(curve) - 1))]
            quad(masks["phase_shear_notches"], shear_centre,
                 mid_n + mid_t * 0.24, 6.0 + code % 5,
                 2.0 + (code % 3), 0.92)

        elif event_class == 1:
            # Cusp regime: a tapering A/B wedge pair replaces the longitudinal
            # fold, and unequal fins/relay scars carry the junction.
            wedge(masks["paired_positive_fold_sides_a"], curve[5], mid_t,
                  13.0 + code % 8, 5.0 + code % 4, -1.0, paint_value)
            wedge(masks["paired_negative_fold_sides_b"], curve[-6], -mid_t,
                  9.0 + (code * 3) % 9, 4.0 + (code + 2) % 5,
                  1.0, paint_value)
            cusp_centre = curve[mid]
            wedge(masks["true_cusp_wedges"], cusp_centre - mid_t * 2.0,
                  mid_t + mid_n * (0.26 * bend_sign),
                  7.0 + code % 6, 4.0 + (code + 1) % 4,
                  bend_sign, 1.0)
            relay = np.asarray([
                cusp_centre - mid_t * 7.0 - mid_n * 3.0,
                cusp_centre - mid_t * 1.0 + mid_n * (1.0 + bend_sign * 2.0),
                cusp_centre + mid_t * (5.0 + code % 4) - mid_n * 2.0,
            ], np.float32)
            cv2.polylines(masks["relay_scar_zigzags"],
                          [np.rint(relay).astype(np.int32)], False,
                          0.94, 2 + code % 3, cv2.LINE_AA)

        elif event_class == 2:
            # Occlusion regime: the envelope is absent.  Two recoil lips and
            # a short rebound wedge make the interruption literal.
            for fraction, side in ((0.24, -1.0), (0.72, 1.0)):
                idx = int(fraction * (len(curve) - 1))
                local_t = unit(curve_tangent[idx])
                local_n = np.asarray([-local_t[1], local_t[0]], np.float32)
                quad(masks["occlusion_recoil_lips"], curve[idx],
                     local_n + local_t * (0.22 * bend_sign),
                     8.0 + (code + idx) % 6, 4.0 + (code + idx) % 4,
                     0.82 + 0.04 * (code % 5), 0.24 * side)
            wedge(masks["paired_positive_fold_sides_a"], curve[36],
                  unit(curve_tangent[36]), 8.0 + code % 7,
                  4.0 + code % 4, -bend_sign, paint_value)
            quad(masks["phase_shear_notches"], curve[27], mid_n,
                 6.0 + code % 5, 2.0 + code % 3, 0.9)

        elif event_class == 3:
            # Diffraction regime: only transverse finite returns remain.  They
            # vary in count, aspect and curvature side and cannot read as a
            # parallel full-card line family.
            return_count = 3 + code % 5
            for order in range(return_count):
                fraction = (order + 1.0) / (return_count + 1.0)
                idx = int(fraction * (len(curve) - 1))
                local_t = unit(curve_tangent[idx])
                local_n = np.asarray([-local_t[1], local_t[0]], np.float32)
                side = -1.0 if order & 1 else 1.0
                target = (masks["positive_transverse_returns_a"]
                          if (order + code) & 1 else
                          masks["negative_transverse_returns_b"])
                quad(target, curve[idx] + local_n * side * (1.0 + order % 3),
                     local_n + local_t * (0.12 * (order - 2)),
                     5.0 + (code + order * 2) % 7,
                     2.0 + (code + order) % 4,
                     0.76 + 0.04 * ((code + order) % 6),
                     0.12 * side)
            quad(masks["phase_shear_notches"], curve[mid], mid_t,
                 5.0 + code % 5, 3.0 + code % 3, 0.88)

        else:
            # Relay/order-swap regime.  A bent scar is the only continuous
            # piece; A/B facets exchange sides along it and end in a lip.
            picks = (4, 17, 31, 47)
            zig = curve[list(picks)].copy()
            zig[1] += mid_n * (3.0 + code % 4)
            zig[2] -= mid_n * (2.0 + (code + 1) % 4)
            cv2.polylines(masks["relay_scar_zigzags"],
                          [np.rint(zig).astype(np.int32)], False,
                          0.88, 2 + code % 3, cv2.LINE_AA)
            for swap_index, idx in enumerate((10, 24, 39)):
                local_t = unit(curve_tangent[idx])
                local_n = np.asarray([-local_t[1], local_t[0]], np.float32)
                centre = curve[idx] + local_n * (-2.5 if swap_index & 1 else 2.5)
                quad(masks["order_swap_facets"], centre,
                     local_t + local_n * (0.2 * (swap_index - 1)),
                     6.0 + (code + swap_index) % 7,
                     4.0 + (code + 2 * swap_index) % 4,
                     0.78 + 0.04 * ((code + swap_index) % 5),
                     0.18 * (swap_index - 1))
                target = (masks["positive_transverse_returns_a"]
                          if swap_index != 1 else
                          masks["negative_transverse_returns_b"])
                quad(target, centre + local_n * (3.0 - swap_index),
                     local_n, 5.0 + (code + swap_index) % 5,
                     2.0 + swap_index % 3, 0.84)
            quad(masks["occlusion_recoil_lips"], curve[-8], mid_n,
                 7.0 + code % 6, 4.0 + code % 4, 0.9)

        # Paint event age through the same edge footprint.  It changes shade
        # within named anatomy but is never rendered as a background field.
        section(phase_tone, curve, 0.02, 0.97,
                0.08 + 0.071 * epoch_index + 0.023 * event_class, 7)

    banks = dict(
        paired_positive_fold_sides_a="A", paired_negative_fold_sides_b="B",
        finite_envelope_cores="N", true_cusp_wedges="A",
        occlusion_recoil_lips="B", positive_transverse_returns_a="A",
        negative_transverse_returns_b="B", phase_shear_notches="N",
        relay_scar_zigzags="N", order_swap_facets="B",
    )
    pa = masks["paired_positive_fold_sides_a"]
    nb = masks["paired_negative_fold_sides_b"]
    core = masks["finite_envelope_cores"]
    cusp = masks["true_cusp_wedges"]
    lip = masks["occlusion_recoil_lips"]
    oa = masks["positive_transverse_returns_a"]
    ob = masks["negative_transverse_returns_b"]
    shear = masks["phase_shear_notches"]
    relay = masks["relay_scar_zigzags"]
    swap = masks["order_swap_facets"]
    m_field = (8.0 + 202.0 * pa + 178.0 * oa + 228.0 * cusp
               + 76.0 * core + 48.0 * relay)
    r_field = (240.0 - 166.0 * shear - 112.0 * core
               - 94.0 * relay + 38.0 * swap - 58.0 * lip)
    cc_field = (10.0 + 206.0 * nb + 184.0 * ob + 218.0 * lip
                + 174.0 * swap + 48.0 * relay)
    x_px, y_px = _xy()
    tone = _norm(0.70 * cv2.GaussianBlur(phase_tone, (0, 0), 2.4)
                 + 0.17 * x_px / _WORK + 0.13 * y_px / _WORK)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_eyeshine_w31() -> _Grammar:
    """Unequal connected fold/cusp assemblies on one directed genealogy.

    SPB-WILDS WR-31, 2026-08-24.  W30 was self-rejected as a dense dash and
    chevron lane field.  W31 abandons per-edge microplates.  Forty-seven
    degree-limited events form one edge-cropped asymmetric ray genealogy, but
    every event is a connected assembly sized by its own adjacent spans and
    turning angle: through-folds exchange paired sides, births unfold into
    cusp fans, mergers end in beak annihilation lips, high turns become order
    swaps, and compressed spans vanish behind occlusion/recoil anatomy.  Fine
    2-8 px primitives build the larger event identity; no event is stamped
    from a shared glyph and no full critical edge survives unchanged.
    """
    names = (
        "positive_fold_faces_a", "negative_fold_faces_b",
        "cropped_envelope_ancestry", "cusp_unfolding_fans",
        "beak_annihilation_lips", "positive_diffraction_returns_a",
        "negative_diffraction_returns_b", "phase_occlusion_notches",
        "relay_scar_paths", "order_swap_facets",
    )
    masks = _new_marks(*names)
    phase_tone = np.zeros((_WORK, _WORK), np.float32)

    counts = (4, 6, 5, 7, 4, 6, 5, 4, 6)
    golden = np.float32(0.6180339887498948)
    epochs = []
    for epoch_index, count in enumerate(counts):
        tau = epoch_index / float(len(counts) - 1)
        wavefront = []
        for rank in range(count):
            orbit = np.mod((rank + 0.5) * golden
                           + 0.137 * epoch_index
                           + 0.027 * epoch_index * epoch_index, 1.0)
            base_x = -42.0 + 596.0 * tau
            base_y = 12.0 + 488.0 * orbit
            point = np.asarray([
                base_x + 31.0 * np.sin(base_y / 91.0 + epoch_index * 0.57)
                + 12.0 * np.sin((base_x + base_y) / 157.0),
                base_y + 26.0 * np.sin(base_x / 107.0 - orbit * 2.8)
                + 13.0 * np.cos((1.6 * base_x - base_y) / 173.0),
            ], np.float32)
            wavefront.append(point)
        epochs.append(sorted(wavefront, key=lambda p: float(p[1])))

    nodes = []
    epoch_ids = []
    ranks = []
    for epoch_index, points in enumerate(epochs):
        ids = []
        for rank, point in enumerate(points):
            ids.append(len(nodes))
            nodes.append(point)
            ranks.append((epoch_index, rank))
        epoch_ids.append(ids)

    edges = set()
    for epoch_index in range(len(epoch_ids) - 1):
        source_ids = epoch_ids[epoch_index]
        target_ids = epoch_ids[epoch_index + 1]
        ns, nt = len(source_ids), len(target_ids)
        for target_rank, target_id in enumerate(target_ids):
            source_rank = int(np.clip(
                round((target_rank + 0.5) * ns / nt - 0.5), 0, ns - 1))
            edges.add((source_ids[source_rank], target_id))
        for source_rank, source_id in enumerate(source_ids):
            target_rank = int(np.clip(
                round((source_rank + 0.5) * nt / ns - 0.5), 0, nt - 1))
            edges.add((source_id, target_ids[target_rank]))

    incoming = [[] for _ in nodes]
    outgoing = [[] for _ in nodes]
    for left, right in sorted(edges):
        outgoing[left].append(right)
        incoming[right].append(left)

    def unit(vector: np.ndarray) -> np.ndarray:
        magnitude = float(np.linalg.norm(vector))
        if magnitude < 1.0e-5:
            return np.asarray([1.0, 0.0], np.float32)
        return (vector / magnitude).astype(np.float32)

    def bezier(start: np.ndarray, control: np.ndarray, end: np.ndarray,
               samples: int = 72) -> np.ndarray:
        t = np.linspace(0.0, 1.0, samples, dtype=np.float32)[:, None]
        return ((1.0 - t) ** 2 * start + 2.0 * (1.0 - t) * t * control
                + t * t * end).astype(np.float32)

    def geometry(curve: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        tangent = np.gradient(curve, axis=0)
        speed = np.maximum(np.linalg.norm(tangent, axis=1), 1.0e-5)
        normal = np.column_stack([-tangent[:, 1] / speed,
                                  tangent[:, 0] / speed]).astype(np.float32)
        return tangent, normal

    def draw_curve(mask: np.ndarray, curve: np.ndarray, width: int,
                   value: float = 1.0, offset: float = 0.0,
                   lo: float = 0.0, hi: float = 1.0) -> None:
        points = curve.copy()
        if abs(offset) > 1.0e-5:
            _tangent, normal = geometry(points)
            points = points + normal * float(offset)
        start = int(np.clip(round(lo * (len(points) - 1)), 0, len(points) - 2))
        stop = int(np.clip(round(hi * (len(points) - 1)), start + 2, len(points)))
        cv2.polylines(mask, [np.rint(points[start:stop]).astype(np.int32)],
                      False, float(value), int(width), cv2.LINE_AA)

    def quad(mask: np.ndarray, centre: np.ndarray, direction: np.ndarray,
             length: float, width: float, value: float = 1.0,
             skew: float = 0.0) -> None:
        t = unit(direction)
        n = np.asarray([-t[1], t[0]], np.float32)
        hl, hw = 0.5 * float(length), 0.5 * float(width)
        polygon = np.asarray([
            centre - t * hl - n * hw * (0.70 + skew),
            centre + t * hl - n * hw * (1.20 - skew),
            centre + t * hl + n * hw * (0.76 + skew),
            centre - t * hl + n * hw * (1.12 - skew),
        ], np.int32)
        cv2.fillConvexPoly(mask, polygon, float(value), cv2.LINE_AA)

    def wedge(mask: np.ndarray, root: np.ndarray, direction: np.ndarray,
              length: float, width: float, side: float,
              value: float = 1.0) -> None:
        t = unit(direction)
        n = np.asarray([-t[1], t[0]], np.float32) * float(side)
        tip = root + t * float(length)
        polygon = np.asarray([
            root - t * 1.5 - n * width * 0.22,
            root + n * width * 0.70,
            tip + n * width * 0.12,
            tip - n * width * 0.20,
        ], np.int32)
        cv2.fillConvexPoly(mask, polygon, float(value), cv2.LINE_AA)

    # Edge ancestry is drawn only through its middle third.  Node assemblies
    # own both ends and transform it before another edge can be followed.
    for edge_index, (left, right) in enumerate(sorted(edges)):
        a, b = nodes[left], nodes[right]
        direction = b - a
        normal = np.asarray([-direction[1], direction[0]], np.float32)
        normal = unit(normal)
        control = 0.5 * (a + b) + normal * (
            (-1.0 if edge_index & 1 else 1.0) * (5.0 + edge_index % 7))
        curve = bezier(a, control, b, 66)
        draw_curve(masks["cropped_envelope_ancestry"], curve,
                   2 + edge_index % 2, 0.72, 0.0, 0.36, 0.64)

    for node_index, point in enumerate(nodes):
        epoch_index, rank = ranks[node_index]
        prev_points = [nodes[parent] for parent in incoming[node_index]]
        next_points = [nodes[child] for child in outgoing[node_index]]
        prev_dirs = [unit(point - parent) for parent in prev_points]
        next_dirs = [unit(child - point) for child in next_points]
        in_degree, out_degree = len(prev_dirs), len(next_dirs)
        in_dir = unit(np.sum(prev_dirs, axis=0)) if prev_dirs else (
            next_dirs[0] if next_dirs else np.asarray([1.0, 0.0], np.float32))
        out_dir = unit(np.sum(next_dirs, axis=0)) if next_dirs else in_dir
        tangent = unit(in_dir + out_dir)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        turn = float(in_dir[0] * out_dir[1] - in_dir[1] * out_dir[0])
        incoming_span = min([float(np.linalg.norm(point - parent))
                             for parent in prev_points] or [84.0])
        outgoing_span = min([float(np.linalg.norm(child - point))
                             for child in next_points] or [84.0])
        local_span = np.clip(0.31 * min(incoming_span, outgoing_span),
                             18.0, 46.0)
        code = (node_index * 11 + epoch_index * 7 + rank * 3) % 19
        value = 0.74 + 0.04 * (code % 6)

        start = point - in_dir * local_span
        end = point + out_dir * local_span
        control = point + normal * turn * (8.0 + code % 7)
        through = bezier(start, control, end, 86)
        tt, nn = geometry(through)

        if in_degree <= 1 and out_degree <= 1:
            # One-to-one fold: two continuous faces collapse, swap sides and
            # re-open.  The central occlusion gap is owned by a shear notch.
            s = np.linspace(0.0, 1.0, len(through), dtype=np.float32)
            collapse = np.clip(np.abs(s - 0.49) / (0.11 + 0.01 * (code % 4)),
                               0.0, 1.0)
            side = (3.0 + 0.35 * (code % 5)) * collapse
            sign = np.where(s < 0.49, 1.0, -1.0)
            positive = through + nn * (side * sign)[:, None]
            negative = through - nn * (side * sign)[:, None]
            draw_curve(masks["positive_fold_faces_a"], positive,
                       4 + code % 4, value, 0.0, 0.02, 0.42)
            draw_curve(masks["negative_fold_faces_b"], negative,
                       4 + (code + 2) % 4, value, 0.0, 0.04, 0.40)
            draw_curve(masks["positive_fold_faces_a"], positive,
                       3 + (code + 1) % 4, value, 0.0, 0.59, 0.97)
            draw_curve(masks["negative_fold_faces_b"], negative,
                       4 + (code + 3) % 4, value, 0.0, 0.61, 0.94)
            draw_curve(masks["cropped_envelope_ancestry"], through,
                       2, 0.82, 0.0, 0.08, 0.38)
            draw_curve(masks["cropped_envelope_ancestry"], through,
                       2, 0.68, 0.0, 0.64, 0.91)
            quad(masks["phase_occlusion_notches"], point,
                 normal + tangent * (0.28 * turn),
                 8.0 + code % 9, 3.0 + code % 4, 0.96, 0.22 * turn)

            # High turns become a genuine three-facet order exchange instead
            # of another copy of the through-fold silhouette.
            if abs(turn) > 0.22 or code % 4 == 0:
                for facet_index, fraction in enumerate((0.36, 0.50, 0.65)):
                    idx = int(fraction * (len(through) - 1))
                    local_t = unit(tt[idx])
                    local_n = nn[idx]
                    quad(masks["order_swap_facets"],
                         through[idx] + local_n * (facet_index - 1) * 2.6,
                         local_t + local_n * (0.22 * (facet_index - 1)),
                         8.0 + (code + 3 * facet_index) % 11,
                         4.0 + (code + facet_index) % 5,
                         0.78 + 0.05 * facet_index,
                         0.14 * (facet_index - 1))

        elif out_degree > in_degree:
            # Birth: the entering fold terminates at a true cusp fan.  Every
            # outgoing direction gets a different-length wedge and curved
            # diffraction return; no common fan template is reused.
            draw_curve(masks["positive_fold_faces_a"], through,
                       5 + code % 3, value, 2.8, 0.02, 0.43)
            draw_curve(masks["negative_fold_faces_b"], through,
                       4 + (code + 1) % 4, value, -2.8, 0.04, 0.39)
            for branch_index, direction in enumerate(next_dirs):
                branch_span = np.clip(0.34 * float(np.linalg.norm(
                    next_points[branch_index] - point)), 16.0, 42.0)
                side = -1.0 if branch_index == 0 else 1.0
                wedge(masks["cusp_unfolding_fans"], point,
                      direction + normal * (0.14 * side),
                      branch_span * (0.58 + 0.11 * branch_index),
                      5.0 + (code + 2 * branch_index) % 4,
                      side, 0.94)
                branch_end = point + direction * branch_span
                branch_control = 0.5 * (point + branch_end) + normal * side * (
                    5.0 + (code + branch_index) % 6)
                order_curve = bezier(point + direction * 4.0,
                                     branch_control, branch_end, 64)
                target = (masks["positive_diffraction_returns_a"]
                          if branch_index == 0 else
                          masks["negative_diffraction_returns_b"])
                draw_curve(target, order_curve,
                           3 + (code + branch_index) % 4,
                           0.82 + 0.06 * branch_index,
                           side * (4.0 + branch_index), 0.16, 0.88)
            quad(masks["phase_occlusion_notches"], point - in_dir * 3.0,
                 normal, 7.0 + code % 7, 3.0 + code % 4, 0.92)

        else:
            # Merger/annihilation: incoming fold faces terminate against one
            # skew beak lip.  The exit is a relay scar with an order handoff.
            for branch_index, direction in enumerate(prev_dirs):
                branch_start = point - direction * local_span
                branch_control = 0.5 * (branch_start + point) + normal * (
                    (-1.0 if branch_index == 0 else 1.0)
                    * (5.0 + (code + branch_index) % 7))
                branch_curve = bezier(branch_start, branch_control, point, 68)
                target = (masks["positive_fold_faces_a"]
                          if branch_index == 0 else
                          masks["negative_fold_faces_b"])
                draw_curve(target, branch_curve,
                           4 + (code + branch_index) % 4,
                           value, (-3.0 if branch_index == 0 else 3.0),
                           0.03, 0.84)
            quad(masks["beak_annihilation_lips"], point - out_dir * 1.5,
                 normal + out_dir * (0.24 * turn),
                 14.0 + code % 13, 5.0 + code % 4,
                 0.88, np.clip(turn, -0.3, 0.3))
            relay_end = point + out_dir * local_span
            relay = np.asarray([
                point + out_dir * 3.0 - normal * (4.0 + abs(turn) * 5.0),
                point + out_dir * (0.34 * local_span) + normal * (3.0 + code % 5),
                point + out_dir * (0.68 * local_span) - normal * (2.0 + code % 4),
                relay_end,
            ], np.float32)
            cv2.polylines(masks["relay_scar_paths"],
                          [np.rint(relay).astype(np.int32)], False,
                          0.90, 3 + code % 4, cv2.LINE_AA)
            quad(masks["order_swap_facets"],
                 point + out_dir * (0.58 * local_span),
                 out_dir + normal * (0.32 * turn),
                 10.0 + code % 11, 4.0 + code % 5, 0.86)
            target = (masks["positive_diffraction_returns_a"]
                      if turn >= 0.0 else
                      masks["negative_diffraction_returns_b"])
            quad(target, point + out_dir * (0.78 * local_span), normal,
                 10.0 + (code * 3) % 13, 3.0 + code % 4, 0.90)

        cv2.circle(phase_tone, tuple(np.rint(point).astype(int)),
                   int(np.clip(local_span * 0.62, 10, 27)),
                   float(0.08 + 0.105 * epoch_index + 0.009 * code),
                   -1, cv2.LINE_AA)

    banks = dict(
        positive_fold_faces_a="A", negative_fold_faces_b="B",
        cropped_envelope_ancestry="N", cusp_unfolding_fans="A",
        beak_annihilation_lips="B", positive_diffraction_returns_a="A",
        negative_diffraction_returns_b="B", phase_occlusion_notches="N",
        relay_scar_paths="N", order_swap_facets="B",
    )
    pa = masks["positive_fold_faces_a"]
    nb = masks["negative_fold_faces_b"]
    ancestry = masks["cropped_envelope_ancestry"]
    cusp = masks["cusp_unfolding_fans"]
    lip = masks["beak_annihilation_lips"]
    oa = masks["positive_diffraction_returns_a"]
    ob = masks["negative_diffraction_returns_b"]
    shear = masks["phase_occlusion_notches"]
    relay = masks["relay_scar_paths"]
    swap = masks["order_swap_facets"]
    m_field = (8.0 + 204.0 * pa + 184.0 * oa + 228.0 * cusp
               + 74.0 * ancestry + 52.0 * relay)
    r_field = (246.0 - 214.0 * shear - 146.0 * ancestry
               - 120.0 * relay + 47.0 * swap - 81.0 * lip)
    cc_field = (10.0 + 208.0 * nb + 188.0 * ob + 222.0 * lip
                + 178.0 * swap + 48.0 * relay)
    x_px, y_px = _xy()
    tone = _norm(0.71 * cv2.GaussianBlur(phase_tone, (0, 0), 3.2)
                 + 0.16 * x_px / _WORK + 0.13 * y_px / _WORK)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_mossy_stone_w32() -> _Grammar:
    """Cooling-column crowns causally colonized by attached foliose lichen.

    SPB-WILDS WR-32, 2026-08-24.  The W20 Mossy Stone contact was rejected as
    detached dot/pebble scatter with no two-material construction.  W32 grows
    one fine basalt cooling front, derives crown facets and contraction seams
    from its column adjacency, selects downhill wet seam chains, and grows
    foliose lichen only outward from those chains.  Soredia cups live inside
    lichen; quartz needles and chipped corners live on exposed mineral crowns.
    No detached moss dots, bare basalt paver, random/noise layer, broad scalar
    continent, Webbed membrane, or Foam film is rendered.
    """
    names = (
        "dry_column_crown_facets_a", "foliose_lichen_lobes_b",
        "fine_contraction_seams", "crown_bevel_faces",
        "wet_seam_channels_b", "soredia_cup_rims_b",
        "lichen_rhizine_veins", "quartz_needles_a",
        "chipped_crown_edges_a",
    )
    masks = _new_marks(*names)
    x, y = _xy()

    # Advancing cooling-front nucleation.  The stagger and smooth displacement
    # are deterministic physical front timing, never a seed/noise texture.
    source = np.ones((_WORK, _WORK), np.uint8)
    sites = []
    occupied = set()
    spacing_x = 6.65
    spacing_y = 6.35
    row_count = int(np.ceil(_WORK / spacing_y)) + 2
    column_count = int(np.ceil(_WORK / spacing_x)) + 2
    for row in range(-1, row_count):
        raw_y = row * spacing_y + 2.4
        for column in range(-1, column_count):
            raw_x = (column * spacing_x + 2.1
                     + (0.48 * spacing_x if row & 1 else 0.0))
            px = (raw_x + 1.45 * np.sin(raw_y / 18.7 + raw_x / 43.0)
                  + 0.72 * np.sin((1.4 * raw_x - raw_y) / 27.0))
            py = (raw_y + 1.18 * np.cos(raw_x / 21.0 - raw_y / 39.0)
                  + 0.64 * np.sin((raw_x + 1.7 * raw_y) / 31.0))
            ix, iy = int(round(px)), int(round(py))
            if not (1 <= ix < _WORK - 1 and 1 <= iy < _WORK - 1):
                continue
            while (ix, iy) in occupied and ix < _WORK - 2:
                ix += 1
            if (ix, iy) in occupied:
                continue
            occupied.add((ix, iy))
            source[iy, ix] = 0
            sites.append((ix, iy, row, column))

    _distance_to_site, labels = cv2.distanceTransformWithLabels(
        source, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    labels = labels.astype(np.int32)

    # Fine contraction adjacency.  Unlike Webbed, the visual material is the
    # filled prismatic crown relief and its colonized face, not a wall mesh.
    edge = np.zeros((_WORK, _WORK), np.uint8)
    edge[:, 1:] |= labels[:, 1:] != labels[:, :-1]
    edge[1:, :] |= labels[1:, :] != labels[:-1, :]
    edge[:, :-1] |= labels[:, :-1] != labels[:, 1:]
    edge[:-1, :] |= labels[:-1, :] != labels[1:, :]
    edge_f = edge.astype(np.float32)
    interior = (edge == 0).astype(np.uint8)
    crown_depth = cv2.distanceTransform(interior, cv2.DIST_L2, 5)
    crown_depth_u = _f32(crown_depth / 4.2)
    gx = cv2.Sobel(crown_depth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(crown_depth, cv2.CV_32F, 0, 1, ksize=3)
    slope = np.hypot(gx, gy)
    facet_normal = (0.78 * gx - 0.42 * gy) / np.maximum(slope, 0.35)
    lit_facet = _f32((facet_normal + 0.62) / 1.18)

    # A low-order downhill wetness potential selects connected seam chains.
    # It is only a causal selector; no scalar field is painted.
    moisture = (0.46 * np.sin((x + 0.42 * y) / 74.0)
                + 0.31 * np.cos((1.3 * x - y) / 103.0)
                + 0.17 * np.sin((x + 1.8 * y) / 139.0)
                + 0.18 * y / _WORK)
    moisture_gate = _f32((moisture + 0.18) / 0.48)
    seam_slope = cv2.Sobel(moisture.astype(np.float32), cv2.CV_32F,
                           0, 1, ksize=3)
    downhill_gate = _f32((seam_slope + 0.055) / 0.12)
    wet_seam = _f32(edge_f * moisture_gate * (0.44 + 0.56 * downhill_gate))
    wet_binary = (wet_seam > 0.28).astype(np.uint8)
    distance_to_wet = cv2.distanceTransform(1 - wet_binary,
                                             cv2.DIST_L2, 5)

    # Lichen has a bounded 2-7 px foliose reach and grows into one mineral
    # face, not symmetrically around every cell wall.  Lobe scalloping follows
    # crown normal and colonization age, never an independent noise texture.
    colonization_age = _norm(0.58 * moisture + 0.27 * x / _WORK
                             - 0.15 * y / _WORK)
    reach = 2.4 + 3.1 * colonization_age
    growth_side = _f32((-facet_normal + 0.72) / 1.30)
    lichen_body = _f32((reach - distance_to_wet) / 1.05) * growth_side
    lichen_body *= _f32((distance_to_wet - 0.35) / 0.85)
    lobe_phase = (0.5 + 0.5 * np.sin(
        2.5 * np.arctan2(gy, gx) + 1.15 * crown_depth
        + 0.23 * labels.astype(np.float32)))
    foliose = _f32(lichen_body * (0.58 + 0.42 * lobe_phase))

    # Dry stone is explicitly excluded from colonized/wet anatomy, giving the
    # Fractured A/B handoff substantial literal material ownership.
    wet_halo = _f32((3.2 - distance_to_wet) / 1.4)
    dry_exclusion = _f32(1.0 - np.maximum(foliose, wet_halo * 0.82))
    masks["dry_column_crown_facets_a"] = _f32(
        interior.astype(np.float32) * dry_exclusion
        * (0.54 + 0.46 * lit_facet) * (0.48 + 0.52 * crown_depth_u))
    masks["foliose_lichen_lobes_b"] = foliose
    masks["fine_contraction_seams"] = _f32(edge_f * (1.0 - 0.58 * wet_halo))
    masks["crown_bevel_faces"] = _f32(
        (cv2.dilate(edge_f, np.ones((3, 3), np.uint8)) - edge_f)
        * dry_exclusion * (0.42 + 0.58 * lit_facet))
    masks["wet_seam_channels_b"] = wet_seam

    # Rhizines are the inner lichen/seam contact, never free hair or moss
    # scatter.  Soredia cup rims occur only at colonized crown maxima.
    lichen_edge = _edge(foliose > 0.42, 1)
    masks["lichen_rhizine_veins"] = _f32(
        wet_halo * foliose * (0.36 + 0.64 * edge_f))
    crown_max = (crown_depth >= cv2.dilate(
        crown_depth, np.ones((5, 5), np.uint8)) - 1.0e-6)
    cup_sites = (crown_max & (foliose > 0.34)
                 & ((labels % 11) == 3)).astype(np.uint8)
    cup_outer = cv2.dilate(cup_sites, np.ones((3, 3), np.uint8))
    masks["soredia_cup_rims_b"] = _f32(
        (cup_outer.astype(np.float32) - cup_sites.astype(np.float32))
        * foliose + 0.34 * cup_sites.astype(np.float32) * foliose)

    # Quartz and chips share the same exposed mineral event.  Each needle is
    # rooted on one dry crown and terminates at its chipped bevel.
    for site_index, (ix, iy, row, column) in enumerate(sites):
        if ((row * 7 + column * 11 + site_index * 3) % 37) != 5:
            continue
        if foliose[iy, ix] > 0.16 or wet_halo[iy, ix] > 0.32:
            continue
        angle = (0.43 * np.sin(ix / 37.0) - 0.38 * np.cos(iy / 41.0)
                 + 0.17 * np.sin((ix + iy) / 29.0))
        direction = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-direction[1], direction[0]], np.float32)
        centre = np.asarray([ix, iy], np.float32)
        length = 3.0 + ((site_index * 5) % 6)
        root = centre - direction * 1.5
        tip = centre + direction * length
        _draw_line(masks["quartz_needles_a"], root, tip, 1.0, 2)
        chip = np.asarray([
            tip - direction * 2.0 - normal * 2.0,
            tip + direction * 1.0,
            tip - direction * 1.0 + normal * 2.2,
        ], np.float32)
        _draw_poly(masks["chipped_crown_edges_a"], chip,
                   0.82 + 0.04 * (site_index % 5), 1, False)

    # The lobe edge modulates the body and makes foliose attachment nameable
    # without adding another free contour carrier.
    masks["foliose_lichen_lobes_b"] = _f32(
        masks["foliose_lichen_lobes_b"] + 0.28 * lichen_edge * lichen_body)

    banks = dict(
        dry_column_crown_facets_a="A", foliose_lichen_lobes_b="B",
        fine_contraction_seams="N", crown_bevel_faces="N",
        wet_seam_channels_b="B", soredia_cup_rims_b="B",
        lichen_rhizine_veins="N", quartz_needles_a="A",
        chipped_crown_edges_a="A",
    )
    dry = masks["dry_column_crown_facets_a"]
    lichen = masks["foliose_lichen_lobes_b"]
    seams = masks["fine_contraction_seams"]
    bevel = masks["crown_bevel_faces"]
    wet = masks["wet_seam_channels_b"]
    cups = masks["soredia_cup_rims_b"]
    rhizine = masks["lichen_rhizine_veins"]
    quartz = masks["quartz_needles_a"]
    chips = masks["chipped_crown_edges_a"]
    m_field = (12.0 + 178.0 * dry + 224.0 * quartz + 196.0 * chips
               + 84.0 * bevel + 42.0 * seams)
    r_field = (224.0 - 152.0 * wet - 118.0 * lichen - 76.0 * rhizine
               + 52.0 * dry - 34.0 * cups)
    cc_field = (10.0 + 212.0 * lichen + 226.0 * wet + 184.0 * cups
                + 118.0 * rhizine + 42.0 * bevel)
    tone = _norm(0.34 * crown_depth_u + 0.28 * colonization_age
                 + 0.22 * lit_facet + 0.16 * moisture_gate)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_mossy_stone_w33() -> _Grammar:
    """Lichen-mediated exfoliation of one continuous weathered stone fabric.

    SPB-WILDS WR-33, 2026-08-24.  W32 was rejected even with strong metrics:
    its cooling-site lattice visibly became a micro-paver inside three scalar
    continents.  W33 starts over with no lattice, territory selector, filled
    background field, detached dot, or repeated colony stamp.  Edge-cropped
    weathering fronts expose unequal stone spalls; foliose thallus blades grow
    directly from their damp contact lips, then rhizines, soralia, dissolution
    bays, quartz sutures, and chips cross-cut or occlude that same interface.
    The support trajectory is never painted as a full-card carrier.
    """
    names = (
        "stone_exfoliation_faces_a", "mineral_cleavage_steps_a",
        "foliose_thallus_blades_b", "recurved_thallus_lips_b",
        "wet_attachment_channels_b", "soralia_broken_crescents_b",
        "rhizine_anchor_combs", "dissolution_contact_bays",
        "healed_fracture_sutures", "quartz_suture_teeth_a",
        "chipped_spall_returns_a",
    )
    masks = _new_marks(*names)

    # Fourteen roots enter from all four crop edges.  Each carries one
    # weathering interface, but its local event schedule repeatedly changes
    # anatomy; no root survives as a uniform painted rail.  First-generation
    # children inherit a real contact point and terminate quickly.
    fronts = []
    roots_per_edge = 4
    for root_index in range(roots_per_edge * 4):
        edge = root_index % 4
        slot = root_index // 4
        fraction = (slot + 0.42
                    + 0.19 * np.sin(1.37 * root_index + 0.6)) / roots_per_edge
        fraction = float(np.clip(fraction, 0.05, 0.95))
        lean = 0.46 * np.sin(root_index * 1.91 + 0.3)
        if edge == 0:
            start = np.asarray([-3.0, fraction * _WORK], np.float32)
            angle = lean
        elif edge == 1:
            start = np.asarray([_WORK + 3.0, fraction * _WORK], np.float32)
            angle = np.pi + lean
        elif edge == 2:
            start = np.asarray([fraction * _WORK, -3.0], np.float32)
            angle = np.pi * 0.5 + lean
        else:
            start = np.asarray([fraction * _WORK, _WORK + 3.0], np.float32)
            angle = -np.pi * 0.5 + lean
        fronts.append((start, float(angle), 108 + (root_index * 17) % 39,
                       root_index, 0))

    front_cursor = 0
    while front_cursor < len(fronts):
        start, angle, steps, family, generation = fronts[front_cursor]
        front_cursor += 1
        point = start.copy()
        previous = None
        spawned = 0
        side = -1.0 if family & 1 else 1.0

        for step in range(int(steps)):
            # A deterministic weathering tensor turns fronts through the rock.
            # It is only a force law; none of these scalar terms is painted.
            px, py = float(point[0]), float(point[1])
            turn = (0.075 * np.sin(px / 31.0 + py / 47.0 + family * 0.61)
                    + 0.052 * np.cos(px / 73.0 - py / 29.0 - family * 0.37)
                    + 0.034 * np.sin((px + 1.7 * py) / 91.0 + step * 0.23))
            angle += float(turn)
            travel = 2.55 + 0.28 * np.sin(step * 0.43 + family)
            tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            next_point = point + tangent * travel

            # Reflective mineral resistance prevents a common focus and lets
            # roots cross-cut at unrelated angles instead of forming lanes.
            if next_point[0] < -5.0 or next_point[0] > _WORK + 5.0:
                angle = float(np.pi - angle + 0.31 * np.sin(family + step))
                tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
                next_point = point + tangent * travel
            if next_point[1] < -5.0 or next_point[1] > _WORK + 5.0:
                angle = float(-angle + 0.27 * np.cos(family - step))
                tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
                next_point = point + tangent * travel

            if previous is None:
                previous = point.copy()
                point = next_point
                continue

            segment = next_point - point
            length = max(0.25, float(np.linalg.norm(segment)))
            tangent = segment / length
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            mid = 0.5 * (point + next_point)
            event = (step + 3 * family + 5 * generation) % 17
            if event in (0, 6, 12):
                side *= -1.0

            # Unequal foliose blades share their base with the damp fracture
            # contact.  Their free edge is scalloped or forked, never a disc,
            # closed rosette, region fill, or repeated glyph.
            if event in (0, 1, 2, 7, 8, 13, 14):
                reach = 4.2 + ((step * 5 + family * 3) % 7)
                half_tip = 1.35 + 0.42 * ((step + family) % 4)
                skew = (0.9 * np.sin(step * 0.77 + family * 0.39))
                tip = mid + normal * side * reach + tangent * skew
                shoulder_a = tip - tangent * half_tip
                shoulder_b = tip + tangent * half_tip
                base_a = point + normal * side * 0.55
                base_b = next_point + normal * side * 0.55
                blade = np.asarray([base_a, base_b, shoulder_b, tip + normal * side,
                                    shoulder_a], np.float32)
                _draw_poly(masks["foliose_thallus_blades_b"], blade,
                           0.78 + 0.04 * ((family + step) % 5), 1, True)
                _draw_line(masks["recurved_thallus_lips_b"], shoulder_a,
                           tip + normal * side * 0.45, 0.94, 1)
                _draw_line(masks["recurved_thallus_lips_b"],
                           tip + normal * side * 0.45, shoulder_b, 0.94, 1)
                _draw_line(masks["wet_attachment_channels_b"], point,
                           next_point, 0.78 + 0.06 * (event % 3),
                           2 if event in (1, 8) else 1)

                # Rhizines are paired hooks rooted beneath selected blades.
                if event in (1, 7, 13):
                    for offset in (-0.82, 0.58):
                        root = mid + tangent * offset
                        elbow = root - normal * side * (2.2 + 0.35 * event % 2)
                        hook = elbow - tangent * (1.4 if offset < 0 else -1.4)
                        _draw_line(masks["rhizine_anchor_combs"], root, elbow,
                                   0.88, 1)
                        _draw_line(masks["rhizine_anchor_combs"], elbow, hook,
                                   0.88, 1)

                # Soralia are open, broken crescents embedded in a free lobe
                # lip.  No cup dot or detached fruiting-body scatter survives.
                if event in (2, 8, 14):
                    inner = tip - normal * side * 1.55
                    arc = np.asarray([
                        inner - tangent * (half_tip * 0.68),
                        inner - normal * side * 0.85,
                        inner + tangent * (half_tip * 0.68),
                    ], np.int32).reshape((-1, 1, 2))
                    cv2.polylines(masks["soralia_broken_crescents_b"], [arc],
                                  False, 1.0, 1, cv2.LINE_AA)

            # Angular stone spalls occupy the dry side of other interface
            # reaches.  They intentionally vary triangle/quad/stepped
            # anatomy so the result cannot become a repeated scale or paver.
            if event in (3, 4, 5, 9, 10, 15, 16):
                dry_side = -side
                depth = 3.4 + ((family * 7 + step * 3) % 6)
                taper = 0.75 + 0.24 * ((step + 2 * family) % 5)
                outer_a = point + normal * dry_side * depth - tangent * taper
                outer_b = next_point + normal * dry_side * (0.62 * depth) + tangent * taper
                if event in (4, 10, 16):
                    kink = mid + normal * dry_side * (depth + 1.5)
                    face = np.asarray([point, next_point, outer_b, kink,
                                       outer_a], np.float32)
                else:
                    face = np.asarray([point, next_point, outer_b, outer_a],
                                      np.float32)
                _draw_poly(masks["stone_exfoliation_faces_a"], face,
                           0.72 + 0.05 * ((step + family) % 6), 1, True)

                # A cleavage step is inside and attached to this exact spall.
                step_a = mid + normal * dry_side * (1.15 + 0.18 * depth)
                step_b = mid + normal * dry_side * (depth - 0.8)
                _draw_line(masks["mineral_cleavage_steps_a"], step_a, step_b,
                           0.84, 1)

                # Chipped returns are asymmetric angular edge losses, not
                # loose chips or debris dots.
                if event in (5, 10, 16):
                    notch_tip = outer_b - tangent * 1.3
                    notch = np.asarray([
                        outer_b,
                        notch_tip + normal * dry_side * 1.8,
                        notch_tip - tangent * 2.2,
                    ], np.float32)
                    _draw_poly(masks["chipped_spall_returns_a"], notch,
                               0.92, 1, False)

            # A healed interval is drawn only where neither material has just
            # occupied the interface.  It therefore cannot reveal every
            # hidden support path as one common carrier.
            if event in (5, 6, 11, 12, 16):
                jog = normal * (0.65 * np.sin(step + family))
                _draw_line(masks["healed_fracture_sutures"], point + jog,
                           next_point - jog, 0.72, 1)

            # Quartz is a short sutured zipper grown through a healed local
            # interval.  Its teeth share endpoints with the fracture and
            # stone face; no detached needle/dot field is placed.
            if event in (6, 12):
                qmid = mid - normal * side * 0.8
                _draw_line(masks["quartz_suture_teeth_a"], point, qmid,
                           0.94, 2)
                _draw_line(masks["quartz_suture_teeth_a"], qmid, next_point,
                           0.94, 1)
                tooth_tip = qmid - normal * side * (3.2 + 0.5 * (family % 3))
                _draw_line(masks["quartz_suture_teeth_a"], qmid, tooth_tip,
                           1.0, 1)
                _draw_line(masks["quartz_suture_teeth_a"], tooth_tip,
                           tooth_tip + tangent * 2.2, 0.86, 1)

            # Dissolution bays are open U-shaped bites exactly at wet/dry
            # contacts.  They will physically cut both material masks below.
            if event in (4, 11, 15):
                bay_side = side if event == 11 else -side
                p0 = mid - tangent * 2.1
                p1 = mid + normal * bay_side * 2.5
                p2 = mid + tangent * 2.1
                bay = np.asarray([p0, p1, p2], np.int32).reshape((-1, 1, 2))
                cv2.polylines(masks["dissolution_contact_bays"], [bay],
                              False, 0.92, 2, cv2.LINE_AA)

            # Two short-lived child fronts inherit a real contact point.  The
            # parent changes event class at the fork, so no repeated Y stamp
            # or globally traceable branch skeleton remains.
            if (generation == 0 and spawned < 2
                    and step in (37 + family % 9, 79 + family % 11)):
                child_angle = angle + (0.86 if spawned == 0 else -1.04)
                child_angle += 0.18 * np.sin(family * 0.63 + step)
                fronts.append((mid.copy(), float(child_angle),
                               31 + (family * 11 + step) % 24,
                               37 + family * 3 + spawned, 1))
                spawned += 1

            previous = point.copy()
            point = next_point

    # Physical cross-cut order.  Dissolution removes material at the contact;
    # thallus and wet anatomy occlude exposed mineral; quartz then heals only
    # the surviving dry interface.  This is a coupled fabric, not stacked
    # decorative textures.
    bay = _f32(masks["dissolution_contact_bays"])
    lichen = _f32(masks["foliose_thallus_blades_b"])
    wet = _f32(masks["wet_attachment_channels_b"])
    b_cover = np.maximum(lichen, wet)
    masks["stone_exfoliation_faces_a"] = _f32(
        masks["stone_exfoliation_faces_a"]
        * (1.0 - 0.88 * b_cover) * (1.0 - 0.82 * bay))
    masks["mineral_cleavage_steps_a"] = _f32(
        masks["mineral_cleavage_steps_a"]
        * (1.0 - 0.92 * b_cover) * (1.0 - 0.72 * bay))
    masks["quartz_suture_teeth_a"] = _f32(
        masks["quartz_suture_teeth_a"] * (1.0 - 0.76 * b_cover))
    masks["chipped_spall_returns_a"] = _f32(
        masks["chipped_spall_returns_a"] * (1.0 - 0.84 * b_cover))
    masks["foliose_thallus_blades_b"] = _f32(
        lichen * (1.0 - 0.72 * bay))
    masks["recurved_thallus_lips_b"] = _f32(
        masks["recurved_thallus_lips_b"] * (1.0 - 0.62 * bay))
    masks["healed_fracture_sutures"] = _f32(
        masks["healed_fracture_sutures"]
        * (1.0 - 0.88 * np.maximum(b_cover, bay)))
    masks["rhizine_anchor_combs"] = _f32(
        masks["rhizine_anchor_combs"] * cv2.dilate(
            (masks["foliose_thallus_blades_b"] > 0.12).astype(np.float32),
            np.ones((5, 5), np.uint8)))
    masks["soralia_broken_crescents_b"] = _f32(
        masks["soralia_broken_crescents_b"] * cv2.dilate(
            (masks["foliose_thallus_blades_b"] > 0.12).astype(np.float32),
            np.ones((3, 3), np.uint8)))

    banks = dict(
        stone_exfoliation_faces_a="A", mineral_cleavage_steps_a="A",
        foliose_thallus_blades_b="B", recurved_thallus_lips_b="B",
        wet_attachment_channels_b="B", soralia_broken_crescents_b="B",
        rhizine_anchor_combs="N", dissolution_contact_bays="N",
        healed_fracture_sutures="N", quartz_suture_teeth_a="A",
        chipped_spall_returns_a="A",
    )
    stone = masks["stone_exfoliation_faces_a"]
    cleavage = masks["mineral_cleavage_steps_a"]
    lichen = masks["foliose_thallus_blades_b"]
    lips = masks["recurved_thallus_lips_b"]
    wet = masks["wet_attachment_channels_b"]
    soralia = masks["soralia_broken_crescents_b"]
    rhizine = masks["rhizine_anchor_combs"]
    healed = masks["healed_fracture_sutures"]
    quartz = masks["quartz_suture_teeth_a"]
    chips = masks["chipped_spall_returns_a"]

    # Three independently nameable material stories: reflective exfoliation
    # and quartz; matte dry faces versus slick wet channels; clear organic
    # thallus lips/soralia with mineral chips left quiet.
    m_field = (10.0 + 178.0 * stone + 116.0 * cleavage + 226.0 * quartz
               + 202.0 * chips + 68.0 * healed - 54.0 * lichen)
    r_field = (176.0 + 62.0 * lichen + 42.0 * rhizine
               - 142.0 * wet - 104.0 * quartz - 76.0 * lips
               + 36.0 * bay + 28.0 * stone)
    cc_field = (12.0 + 134.0 * lichen + 214.0 * lips + 230.0 * wet
                + 196.0 * soralia + 112.0 * rhizine
                + 72.0 * healed - 46.0 * stone)
    x, y = _xy()
    age = (0.31 * x / _WORK + 0.24 * y / _WORK
           + 0.25 * np.sin((x + 1.3 * y) / 57.0)
           + 0.20 * np.cos((1.7 * x - y) / 83.0))
    return _pack(masks, banks, age, (m_field, r_field, cc_field))


def _build_fc_dragon_hex_glass_w34() -> _Grammar:
    """Defect-rich Kagome kirigami armor with topological fold frustration.

    SPB-WILDS WR-34, 2026-08-24.  W20/W17 Dragon was a directional shard
    swarm and earlier versions were triangle pavers.  W34 is this lane's one
    reserved armor lattice: a triangular mineral net is locally displaced by
    paired Volterra cores; its Voronoi dual acquires real five/seven-sided
    adjacency defects; and edge-midpoint construction produces the exact
    triangle/hex Kagome sheet between them.  Alternating mountain/valley folds
    cannot close around odd faces, so the 5/7 defects physically rewrite fold
    ownership, cuts, teeth, bosses, runes, and M/R/Cc response.  No shard,
    confetti, macro sail, or plain lattice recolor is added.
    """
    names = (
        "mountain_fold_ribs_a", "valley_fold_ribs_b",
        "fivefold_disclination_closures_a",
        "sevenfold_disclination_closures_b",
        "kirigami_cut_mouths", "node_boss_trihedra_a",
        "tooth_seam_zippers_b", "micro_rune_cuts",
        "caustic_fold_lips_b", "arrested_fold_returns",
        "clipped_void_rims",
    )
    masks = _new_marks(*names)

    spacing = 13.2
    row_step = spacing * np.sqrt(3.0) * 0.5
    sites = []
    for row in range(-2, int(_WORK / row_step) + 3):
        for column in range(-2, int(_WORK / spacing) + 3):
            point = np.asarray([
                column * spacing + (0.5 * spacing if row & 1 else 0.0),
                row * row_step,
            ], np.float32)
            # Fine sheet prestress changes edge length without defining a
            # visible scalar carrier.  Actual topology changes below.
            point[0] += (0.75 * np.sin(point[1] / 39.0)
                         + 0.36 * np.sin((point[0] + point[1]) / 71.0))
            point[1] += (0.62 * np.cos(point[0] / 47.0)
                         - 0.31 * np.sin((1.3 * point[0] - point[1]) / 83.0))
            if 1.0 < point[0] < _WORK - 1.0 and 1.0 < point[1] < _WORK - 1.0:
                sites.append(point)

    # Thirty aperiodically placed Volterra cores displace opposing sides of a
    # local cut.  Delaunay bond flips create 42 actual 5/7 facet pairs in the
    # focused W34 geometry, not colored labels on unchanged honeycomb cells.
    defects = tuple(
        (24.0 + 464.0 * _halton(index, 2),
         24.0 + 464.0 * _halton(index, 3),
         -1.45 + 2.9 * _halton(index, 5))
        for index in range(1, 31)
    )
    for defect_index, (cx, cy, angle) in enumerate(defects):
        centre = np.asarray([cx, cy], np.float32)
        tangent = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
        normal = np.asarray([-tangent[1], tangent[0]], np.float32)
        ranked = sorted(
            range(len(sites)),
            key=lambda site_index: float(np.linalg.norm(
                sites[site_index] - centre)),
        )[:8]
        for rank, site_index in enumerate(ranked):
            delta = sites[site_index] - centre
            along = float(np.dot(delta, tangent))
            across = float(np.dot(delta, normal))
            strength = ((5.2 - 0.48 * rank)
                        * np.exp(-float(np.dot(delta, delta)) / 520.0))
            sites[site_index] += tangent * strength * (
                1.0 if across >= 0.0 else -1.0)
            sites[site_index] += (
                normal * 0.22 * strength
                * np.sin(along / 5.0 + rank + defect_index * 0.17))

    subdiv = cv2.Subdiv2D((0, 0, _WORK, _WORK))
    for point in sites:
        clipped = (float(np.clip(point[0], 1.1, _WORK - 1.1)),
                   float(np.clip(point[1], 1.1, _WORK - 1.1)))
        try:
            subdiv.insert(clipped)
        except cv2.error:
            # A deformed duplicate is an arrested insertion, never replaced
            # with a random point or jitter texture.
            continue
    facets, centres = subdiv.getVoronoiFacetList([])

    # Render exact midpoint polygons.  In a honeycomb dual, each cell's edge
    # midpoints form a hex void and the three midpoints around each Voronoi
    # vertex form a triangle: this is the Kagome adjacency, not a triangle
    # glyph stamped over a hex background.
    cell_tone = np.zeros((_WORK, _WORK), np.float32)
    defect_distance = np.full((_WORK, _WORK), 999.0, np.float32)
    actual_five = 0
    actual_seven = 0
    for cell_index, (facet, centre_tuple) in enumerate(zip(facets, centres)):
        centre = np.asarray(centre_tuple, np.float32)
        if not (10.0 <= centre[0] < _WORK - 10.0
                and 10.0 <= centre[1] < _WORK - 10.0):
            continue
        polygon = np.asarray(facet, np.float32)
        sides = int(len(polygon))
        if sides < 5 or sides > 7:
            continue
        mids = 0.5 * (polygon + np.roll(polygon, -1, axis=0))
        distances = np.asarray([
            np.hypot(float(centre[0]) - cx, float(centre[1]) - cy)
            for cx, cy, _angle in defects
        ], np.float32)
        nearest = int(np.argmin(distances))
        near = float(distances[nearest])
        _cx, _cy, defect_angle = defects[nearest]
        local_strain = float(np.clip((35.0 - near) / 27.0, 0.0, 1.0))
        lattice_row = int(np.floor(centre[1] / row_step + 0.5))
        lattice_column = int(np.floor(
            (centre[0] - (0.5 * spacing if lattice_row & 1 else 0.0))
            / spacing + 0.5))
        phase = (lattice_column + 2 * lattice_row + nearest) & 1
        if sides == 5:
            actual_five += 1
        elif sides == 7:
            actual_seven += 1

        # Discrete cell age only colors marks physically owned by this cell;
        # no filled cell or background territory is painted.
        tone_value = (0.13 + 0.17 * ((lattice_column - lattice_row) % 5)
                      + 0.19 * local_strain + 0.11 * (sides - 5))
        cv2.fillPoly(cell_tone, [np.rint(mids).astype(np.int32)],
                     float(np.mod(tone_value, 1.0)), cv2.LINE_AA)

        closure_index = (nearest + lattice_column - lattice_row) % sides
        cut_index = (closure_index + 2 + (nearest % 3)) % sides
        secondary_cut = (cut_index + 1 + (cell_index & 1)) % sides
        for edge_index in range(sides):
            start = mids[edge_index]
            end = mids[(edge_index + 1) % sides]
            edge = end - start
            edge_length = max(0.25, float(np.linalg.norm(edge)))
            tangent = edge / edge_length
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            if float(np.dot(normal, centre - 0.5 * (start + end))) < 0.0:
                normal *= -1.0

            # Odd polygons cannot alternate mountain/valley folds through a
            # full circuit.  The closure is a real adjacent same-sign pair,
            # and its local cut is physically absent from the base ribs.
            is_closure = sides in (5, 7) and edge_index == closure_index
            is_cut = (local_strain > 0.34
                      and edge_index in (cut_index, secondary_cut)
                      and ((cell_index + nearest + edge_index) % 4 == 0))
            mountain = ((edge_index + phase) & 1) == 0
            if is_closure:
                mountain = sides == 5

            if not is_cut:
                target = (masks["mountain_fold_ribs_a"] if mountain
                          else masks["valley_fold_ribs_b"])
                width = 3 if local_strain > 0.22 or is_closure else 2
                _draw_line(target, start, end,
                           0.72 + 0.08 * ((edge_index + nearest) % 4),
                           width)
            else:
                # The two short lips terminate at the missing fold segment.
                mouth_mid = 0.5 * (start + end)
                lip_a = start + 0.38 * (mouth_mid - start)
                lip_b = end + 0.38 * (mouth_mid - end)
                _draw_line(masks["kirigami_cut_mouths"], start,
                           lip_a + normal * 1.6, 0.96, 2)
                _draw_line(masks["kirigami_cut_mouths"], end,
                           lip_b + normal * 1.6, 0.96, 2)
                _draw_line(masks["arrested_fold_returns"],
                           lip_a + normal * 1.6,
                           lip_a - tangent * 1.8 + normal * 2.7, 0.88, 1)
                _draw_line(masks["arrested_fold_returns"],
                           lip_b + normal * 1.6,
                           lip_b + tangent * 1.8 + normal * 2.7, 0.88, 1)

            if is_closure:
                closure_name = ("fivefold_disclination_closures_a"
                                if sides == 5 else
                                "sevenfold_disclination_closures_b")
                _draw_line(masks[closure_name], start, end, 1.0, 3)
                # Two unequal teeth terminate in the adjacent fold faces.
                for fraction, tooth_height in ((0.34, 2.1), (0.68, 3.0)):
                    root = start + edge * fraction
                    tooth = root + normal * tooth_height
                    _draw_line(masks["tooth_seam_zippers_b"], root, tooth,
                               0.94, 1)
                    _draw_line(masks["tooth_seam_zippers_b"], tooth,
                               tooth + tangent * (1.2 if fraction < 0.5 else -1.4),
                               0.94, 1)

            # Caustic lips descend only from compressed mountain folds near a
            # topological core; they bend/terminate with the edited edge.
            if mountain and local_strain > 0.18 and not is_cut \
                    and ((edge_index + cell_index + nearest) % 3 == 0):
                _draw_line(masks["caustic_fold_lips_b"],
                           start + normal * 1.55, end + normal * 1.55,
                           0.88 + 0.04 * (nearest % 3), 1)

        # An actual 5/7 void gets a complete defect collar.  Regular void
        # rims appear only where a kirigami cut clipped their adjacency, so a
        # uniform honeycomb outline cannot survive as a neutral carrier.
        if sides == 5:
            _draw_poly(masks["fivefold_disclination_closures_a"], mids,
                       0.92, 2, False)
        elif sides == 7:
            _draw_poly(masks["sevenfold_disclination_closures_b"], mids,
                       0.92, 2, False)
        elif local_strain > 0.34 and ((cell_index + nearest) % 4 == 0):
            open_rim = np.rint(np.delete(mids, cut_index, axis=0)).astype(np.int32)
            cv2.polylines(masks["clipped_void_rims"], [open_rim], False,
                          0.78, 1, cv2.LINE_AA)

        # Trihedral bosses are literal Kagome triangle wedges at defect
        # vertices.  Rune cuts begin on that void rim and terminate inside it;
        # neither is a detached dot, triangle confetti, or free stamp.
        if local_strain > 0.27:
            boss_index = (closure_index + nearest) % sides
            vertex = polygon[(boss_index + 1) % sides]
            boss = np.asarray([
                vertex,
                mids[boss_index],
                mids[(boss_index + 1) % sides],
            ], np.float32)
            centroid = np.mean(boss, axis=0)
            boss = centroid + 0.72 * (boss - centroid)
            _draw_poly(masks["node_boss_trihedra_a"], boss,
                       0.82 + 0.05 * (nearest % 4), 1, True)
        if local_strain > 0.40 and ((cell_index + 2 * nearest) % 3 == 0):
            rune_start = mids[(cut_index + 2) % sides]
            radial = centre - rune_start
            elbow = rune_start + 0.47 * radial
            ortho = np.asarray([-radial[1], radial[0]], np.float32)
            ortho /= max(0.25, float(np.linalg.norm(ortho)))
            rune_end = elbow + ortho * (2.0 + 0.35 * (nearest % 5))
            _draw_line(masks["micro_rune_cuts"], rune_start, elbow, 0.96, 1)
            _draw_line(masks["micro_rune_cuts"], elbow, rune_end, 0.96, 1)

    # The focused geometry is expected to contain matched 5/7 pairs.  A
    # topology regression must fail loudly rather than render a regular grid.
    if actual_five < 24 or actual_seven < 24:
        raise ValueError(
            f"Dragon Kagome lost defect richness: 5={actual_five}, 7={actual_seven}")

    banks = dict(
        mountain_fold_ribs_a="A", valley_fold_ribs_b="B",
        fivefold_disclination_closures_a="A",
        sevenfold_disclination_closures_b="B",
        kirigami_cut_mouths="N", node_boss_trihedra_a="A",
        tooth_seam_zippers_b="B", micro_rune_cuts="N",
        caustic_fold_lips_b="B", arrested_fold_returns="N",
        clipped_void_rims="N",
    )
    mountain = masks["mountain_fold_ribs_a"]
    valley = masks["valley_fold_ribs_b"]
    five = masks["fivefold_disclination_closures_a"]
    seven = masks["sevenfold_disclination_closures_b"]
    cuts = masks["kirigami_cut_mouths"]
    bosses = masks["node_boss_trihedra_a"]
    teeth = masks["tooth_seam_zippers_b"]
    runes = masks["micro_rune_cuts"]
    caustic = masks["caustic_fold_lips_b"]
    returns = masks["arrested_fold_returns"]
    rims = masks["clipped_void_rims"]

    # Independent material topology is derived from fold polarity and actual
    # adjacency edits.  M highlights mountain/boss/five-fold armor; R separates
    # compressed cuts from polished mountains; Cc follows valley/seven-fold
    # caustic lips and clipped voids.
    m_field = (10.0 + 158.0 * mountain + 224.0 * five + 196.0 * bosses
               + 112.0 * teeth + 74.0 * returns - 46.0 * valley)
    r_field = (208.0 - 142.0 * mountain + 38.0 * valley
               - 126.0 * caustic + 32.0 * cuts + 74.0 * runes
               + 48.0 * rims - 86.0 * bosses)
    cc_field = (8.0 + 146.0 * valley + 224.0 * seven + 218.0 * caustic
                + 172.0 * rims + 126.0 * runes + 92.0 * cuts
                - 42.0 * mountain)
    tone = _norm(cell_tone + 0.24 * five + 0.37 * seven
                 + 0.18 * caustic + 0.11 * bosses)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


def _build_fc_batwing_w35() -> _Grammar:
    """Edge-injected time-of-flight echoes refracted by bat-wing bone shadow.

    SPB-WILDS WR-35, 2026-08-24.  W20/W17 Batwing was dot/short-mark scatter;
    earlier versions exposed a wrist hub and radial fan.  W35 injects eight
    unequal ray bundles from the crop edges.  Their fine arrival fronts are
    painted only where an attached bone/cartilage chain bends, splits,
    occludes, or delays neighboring rays.  Early fronts and hard bone shadow
    own A; late refracted returns and capillary doubles own B.  No circular
    emitter, membrane mesh, scalar contour fill, parallel-wave wallpaper, or
    decorative spec field exists.
    """
    names = (
        "bone_shadow_segments_a", "cartilage_refraction_joints_b",
        "early_arrival_fronts_a", "late_refracted_returns_b",
        "phase_dislocation_cusps", "scratch_harmonic_combs",
        "torn_trailing_notches_a", "capillary_echo_doubles_b",
        "dead_acoustic_gap_edges", "order_swap_relays_b",
    )
    masks = _new_marks(*names)

    # An irregular field of attached short phalange/bone-shadow segments.  A
    # chain owns its cartilage joints, but no chain shares a wrist hub and no
    # full-card membrane graph is drawn.
    bone_binary = np.zeros((_WORK, _WORK), np.uint8)
    cartilage_binary = np.zeros_like(bone_binary)
    tangent_x = np.zeros((_WORK, _WORK), np.float32)
    tangent_y = np.zeros_like(tangent_x)
    tangent_weight = np.zeros_like(tangent_x)
    chain_terminals = []
    for chain in range(1, 57):
        if chain <= 16:
            edge = (chain - 1) % 4
            slot = (chain - 1) // 4
            fraction = (slot + 0.34 + 0.17 * np.sin(chain * 1.73)) / 4.0
            if edge == 0:
                point = np.asarray([-2.0, fraction * _WORK], np.float32)
                angle = 0.18 * np.sin(chain)
            elif edge == 1:
                point = np.asarray([_WORK + 2.0, fraction * _WORK], np.float32)
                angle = np.pi + 0.18 * np.cos(chain)
            elif edge == 2:
                point = np.asarray([fraction * _WORK, -2.0], np.float32)
                angle = np.pi * 0.5 + 0.19 * np.sin(chain * 0.7)
            else:
                point = np.asarray([fraction * _WORK, _WORK + 2.0], np.float32)
                angle = -np.pi * 0.5 + 0.19 * np.cos(chain * 0.9)
        else:
            point = np.asarray([
                8.0 + 496.0 * _halton(chain - 16, 2),
                8.0 + 496.0 * _halton(chain - 16, 3),
            ], np.float32)
            angle = (-np.pi + 2.0 * np.pi * _halton(chain - 16, 5)
                     + 0.28 * np.sin(chain * 0.63))
        segments = 6 + (chain * 7) % 9
        previous_direction = None
        for segment_index in range(segments):
            angle += (0.20 * np.sin(point[0] / 43.0 + chain * 0.37)
                      - 0.16 * np.cos(point[1] / 37.0 - segment_index * 0.51)
                      + 0.08 * np.sin((point[0] + point[1]) / 61.0))
            direction = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
            length = 4.8 + ((chain * 11 + segment_index * 5) % 7) * 0.48
            next_point = point + direction * length
            if next_point[0] < -3.0 or next_point[0] > _WORK + 3.0:
                angle = float(np.pi - angle + 0.21 * np.sin(chain + segment_index))
                direction = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
                next_point = point + direction * length
            if next_point[1] < -3.0 or next_point[1] > _WORK + 3.0:
                angle = float(-angle + 0.19 * np.cos(chain - segment_index))
                direction = np.asarray([np.cos(angle), np.sin(angle)], np.float32)
                next_point = point + direction * length
            width = 3 if (chain + segment_index) % 7 == 0 else 2
            _draw_line(masks["bone_shadow_segments_a"], point, next_point,
                       0.76 + 0.06 * ((chain + segment_index) % 4), width)
            cv2.line(bone_binary, tuple(np.rint(point).astype(int)),
                     tuple(np.rint(next_point).astype(int)), 1, width,
                     cv2.LINE_AA)
            cv2.line(tangent_x, tuple(np.rint(point).astype(int)),
                     tuple(np.rint(next_point).astype(int)),
                     float(direction[0]), width + 2, cv2.LINE_AA)
            cv2.line(tangent_y, tuple(np.rint(point).astype(int)),
                     tuple(np.rint(next_point).astype(int)),
                     float(direction[1]), width + 2, cv2.LINE_AA)
            cv2.line(tangent_weight, tuple(np.rint(point).astype(int)),
                     tuple(np.rint(next_point).astype(int)), 1.0,
                     width + 2, cv2.LINE_AA)

            # Cartilage is an asymmetric attached trihedron at an actual bend,
            # never a free joint dot.
            if previous_direction is not None:
                bend = float(previous_direction[0] * direction[1]
                             - previous_direction[1] * direction[0])
                normal = np.asarray([-direction[1], direction[0]], np.float32)
                pad = np.asarray([
                    point - previous_direction * 2.0,
                    point + direction * 2.4,
                    point + normal * (2.1 if bend >= 0.0 else -2.1),
                ], np.float32)
                _draw_poly(masks["cartilage_refraction_joints_b"], pad,
                           0.78 + 0.05 * ((chain + segment_index) % 5),
                           1, True)
                cv2.fillPoly(cartilage_binary,
                             [np.rint(pad).astype(np.int32)], 1,
                             cv2.LINE_AA)
            previous_direction = direction.copy()
            point = next_point
        chain_terminals.append((point.copy(), direction.copy(), chain))

    free = (bone_binary == 0).astype(np.uint8)
    distance_to_bone = cv2.distanceTransform(free, cv2.DIST_L2, 5)
    free_cartilage = (cartilage_binary == 0).astype(np.uint8)
    distance_to_cartilage = cv2.distanceTransform(
        free_cartilage, cv2.DIST_L2, 5)
    grad_x = cv2.Sobel(distance_to_bone, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(distance_to_bone, cv2.CV_32F, 0, 1, ksize=3)
    smooth_weight = cv2.GaussianBlur(tangent_weight, (0, 0), 4.0)
    smooth_tx = cv2.GaussianBlur(tangent_x, (0, 0), 4.0)
    smooth_ty = cv2.GaussianBlur(tangent_y, (0, 0), 4.0)
    smooth_tx /= np.maximum(smooth_weight, 1.0e-3)
    smooth_ty /= np.maximum(smooth_weight, 1.0e-3)

    injections = (
        ("left", 0.16, 3), ("right", np.pi - 0.38, 11),
        ("top", np.pi * 0.5 + 0.47, 17),
        ("bottom", -np.pi * 0.5 - 0.21, 23),
        ("left", -0.56, 29), ("right", np.pi + 0.52, 31),
        ("top", np.pi * 0.5 - 0.61, 37),
        ("bottom", -np.pi * 0.5 + 0.43, 41),
    )
    rays = 58
    for source_index, (edge, base_angle, phase_key) in enumerate(injections):
        coordinate = (np.arange(rays, dtype=np.float32) + 0.5) / rays
        coordinate += 0.012 * np.sin(
            np.arange(rays, dtype=np.float32) * 0.71 + phase_key)
        coordinate = np.clip(coordinate, 0.004, 0.996)
        positions = np.zeros((rays, 2), np.float32)
        if edge == "left":
            positions[:, 0] = -2.0
            positions[:, 1] = coordinate * _WORK
        elif edge == "right":
            positions[:, 0] = _WORK + 2.0
            positions[:, 1] = coordinate * _WORK
        elif edge == "top":
            positions[:, 0] = coordinate * _WORK
            positions[:, 1] = -2.0
        else:
            positions[:, 0] = coordinate * _WORK
            positions[:, 1] = _WORK + 2.0

        ray_angles = (base_angle
                      + 0.17 * np.sin(np.arange(rays) * 0.37 + phase_key)
                      + 0.06 * np.sin(np.arange(rays) * 1.13
                                      + source_index)).astype(np.float32)
        directions = np.column_stack(
            [np.cos(ray_angles), np.sin(ray_angles)]).astype(np.float32)
        encounters = np.zeros(rays, np.int16)
        near_previous = np.zeros(rays, bool)
        attenuation = np.ones(rays, np.float32)
        occlusion_age = np.zeros(rays, np.int16)

        for time_index in range(118):
            ix = np.clip(np.rint(positions[:, 0]).astype(np.int32),
                         0, _WORK - 1)
            iy = np.clip(np.rint(positions[:, 1]).astype(np.int32),
                         0, _WORK - 1)
            distance = distance_to_bone[iy, ix]
            cartilage_distance = distance_to_cartilage[iy, ix]
            near_now = distance < 5.2
            newly_occluded = near_now & ~near_previous
            encounters[newly_occluded] += 1
            occlusion_age = np.maximum(occlusion_age - 1, 0)
            occlusion_age[newly_occluded] = (
                4 + ((np.flatnonzero(newly_occluded) + phase_key) % 6))
            attenuation[newly_occluded] *= 0.72

            # Refraction follows the attached bone tangent; a small outward
            # term prevents rays from tunneling through the obstacle.  The
            # ray ancestry, not a scalar contour field, authors every front.
            local_tangent = np.column_stack(
                [smooth_tx[iy, ix], smooth_ty[iy, ix]]).astype(np.float32)
            tangent_length = np.linalg.norm(local_tangent, axis=1)
            valid_tangent = tangent_length > 0.08
            local_tangent[valid_tangent] /= tangent_length[valid_tangent, None]
            reverse = np.sum(local_tangent * directions, axis=1) < 0.0
            local_tangent[reverse] *= -1.0
            outward = np.column_stack(
                [grad_x[iy, ix], grad_y[iy, ix]]).astype(np.float32)
            outward_length = np.linalg.norm(outward, axis=1)
            valid_outward = outward_length > 0.08
            outward[valid_outward] /= outward_length[valid_outward, None]
            refraction = np.clip((8.2 - distance) / 7.0, 0.0, 0.68)
            directions = (directions * (1.0 - refraction[:, None])
                          + local_tangent * (0.78 * refraction[:, None])
                          + outward * (0.34 * refraction[:, None]))
            direction_length = np.linalg.norm(directions, axis=1)
            directions /= np.maximum(direction_length[:, None], 0.1)
            positions += directions * (2.35 + 0.18 * np.sin(
                time_index * 0.39 + source_index))

            in_bounds = ((positions[:, 0] >= 1.0)
                         & (positions[:, 0] < _WORK - 1.0)
                         & (positions[:, 1] >= 1.0)
                         & (positions[:, 1] < _WORK - 1.0))
            if time_index < 7 or time_index % 3:
                near_previous = near_now
                continue

            # Connect neighboring rays at equal flight time only around a
            # causal obstacle/refraction event.  Undisturbed plane-wave rails
            # are deliberately absent.
            for ray_index in range(rays - 1):
                if not (in_bounds[ray_index] and in_bounds[ray_index + 1]):
                    continue
                start = positions[ray_index]
                end = positions[ray_index + 1]
                front = end - start
                front_length = float(np.linalg.norm(front))
                if not (2.0 <= front_length <= 10.5):
                    continue
                local_near = min(float(distance[ray_index]),
                                 float(distance[ray_index + 1]))
                curvature = abs(float(
                    directions[ray_index, 0] * directions[ray_index + 1, 1]
                    - directions[ray_index, 1] * directions[ray_index + 1, 0]))
                shadow_jump = abs(float(distance[ray_index]
                                        - distance[ray_index + 1]))
                event_strength = (local_near < 13.0 and
                                  (curvature > 0.012
                                   or shadow_jump > 0.44
                                   or occlusion_age[ray_index] > 0
                                   or occlusion_age[ray_index + 1] > 0))
                if not event_strength:
                    continue
                order_left = int(encounters[ray_index])
                order_right = int(encounters[ray_index + 1])
                late = max(order_left, order_right) > 0
                target = (masks["late_refracted_returns_b"] if late else
                          masks["early_arrival_fronts_a"])
                _draw_line(target, start, end,
                           0.74 + 0.06 * ((time_index + ray_index
                                           + source_index) % 4),
                           2 if curvature > 0.055 else 1)

                tangent = front / max(front_length, 0.25)
                normal = np.asarray([-tangent[1], tangent[0]], np.float32)
                midpoint = 0.5 * (start + end)
                if curvature > 0.045:
                    cusp = midpoint + normal * (
                        2.0 + 1.2 * np.sign(order_right - order_left + 0.2))
                    _draw_line(masks["phase_dislocation_cusps"], start,
                               cusp, 0.92, 1)
                    _draw_line(masks["phase_dislocation_cusps"], cusp,
                               end, 0.92, 1)
                if late and min(float(cartilage_distance[ray_index]),
                                float(cartilage_distance[ray_index + 1])) < 8.5:
                    offset = 2.1 + 0.35 * ((ray_index + phase_key) % 4)
                    _draw_line(masks["capillary_echo_doubles_b"],
                               start + normal * offset,
                               end + normal * offset, 0.96, 1)
                    _draw_line(masks["capillary_echo_doubles_b"],
                               start + normal * (offset + 1.5),
                               end + normal * (offset + 1.5), 0.68, 1)
                if curvature > 0.026 and ((ray_index + time_index
                                           + phase_key) % 5 == 0):
                    for offset in (-1.6, 0.0, 1.7):
                        root = midpoint + tangent * offset
                        _draw_line(masks["scratch_harmonic_combs"],
                                   root - normal * 1.4,
                                   root + normal * 1.9, 0.88, 1)
                if order_left != order_right:
                    relay = midpoint + normal * (
                        3.0 if order_right > order_left else -3.0)
                    _draw_line(masks["order_swap_relays_b"], start,
                               relay, 0.90, 1)
                    _draw_line(masks["order_swap_relays_b"], relay,
                               end, 0.90, 1)
                    # The early front terminates in a torn notch; the late
                    # path opens a dead acoustic gap behind the same event.
                    notch_base = start if order_left < order_right else end
                    notch_tip = notch_base - tangent * 2.7 + normal * 2.1
                    _draw_line(masks["torn_trailing_notches_a"],
                               notch_base, notch_tip, 0.96, 1)
                    _draw_line(masks["torn_trailing_notches_a"], notch_tip,
                               notch_tip - normal * 3.3, 0.96, 1)
                    _draw_line(masks["dead_acoustic_gap_edges"],
                               notch_tip - normal * 3.3,
                               notch_tip - normal * 5.6 + tangent * 1.5,
                               0.86, 2)
            near_previous = near_now

    # Terminal bone shadows own one final clipped notch, anchoring the time
    # field to anatomy instead of leaving a decorative wave-only texture.
    for point, direction, chain in chain_terminals:
        normal = np.asarray([-direction[1], direction[0]], np.float32)
        if not (-2.0 <= point[0] <= _WORK + 2.0
                and -2.0 <= point[1] <= _WORK + 2.0):
            continue
        tip = point + direction * (3.0 + chain % 4)
        _draw_line(masks["dead_acoustic_gap_edges"], point,
                   tip + normal * 2.0, 0.72, 1)
        _draw_line(masks["dead_acoustic_gap_edges"], point,
                   tip - normal * 2.0, 0.72, 1)

    banks = dict(
        bone_shadow_segments_a="A", cartilage_refraction_joints_b="B",
        early_arrival_fronts_a="A", late_refracted_returns_b="B",
        phase_dislocation_cusps="N", scratch_harmonic_combs="N",
        torn_trailing_notches_a="A", capillary_echo_doubles_b="B",
        dead_acoustic_gap_edges="N", order_swap_relays_b="B",
    )
    bone = masks["bone_shadow_segments_a"]
    cartilage = masks["cartilage_refraction_joints_b"]
    early = masks["early_arrival_fronts_a"]
    late = masks["late_refracted_returns_b"]
    cusp = masks["phase_dislocation_cusps"]
    scratches = masks["scratch_harmonic_combs"]
    notches = masks["torn_trailing_notches_a"]
    doubles = masks["capillary_echo_doubles_b"]
    dead = masks["dead_acoustic_gap_edges"]
    relays = masks["order_swap_relays_b"]

    # Early echoes and bone are metallic while late/cartilage/capillary echoes
    # reverse into clearcoat.  Roughness separately names dead gaps, scratch
    # combs and compliant cartilage, so no channel is a decorative recolor.
    m_field = (10.0 + 206.0 * bone + 178.0 * early + 194.0 * notches
               + 86.0 * cusp - 62.0 * late - 44.0 * doubles)
    r_field = (196.0 - 118.0 * bone - 104.0 * early + 54.0 * cartilage
               + 48.0 * scratches + 42.0 * dead - 126.0 * doubles
               + 38.0 * relays)
    cc_field = (8.0 + 202.0 * cartilage + 176.0 * late
                + 230.0 * doubles + 154.0 * relays + 112.0 * cusp
                - 46.0 * early - 38.0 * bone)
    tone = _norm(0.22 * bone + 0.34 * cartilage + 0.43 * early
                 + 0.71 * late + 0.86 * doubles + 0.58 * relays)
    return _pack(masks, banks, tone, (m_field, r_field, cc_field))


_BUILDERS: Mapping[str, Callable[[], _Grammar]] = {
    "fc_sasquatch_fur": _build_fc_sasquatch_fur_w16,
    "fc_quill_bristle": _build_fc_quill_bristle_w17,
    "fc_coarse_hide": _build_fc_coarse_hide_w17,
    "fc_eyeshine": _build_fc_eyeshine_w31,
    "fc_bog_murk": _build_fc_bog_murk_w18,
    "fc_claw_rake": _build_fc_claw_rake_w16,
    "fc_bark_camo": _build_fc_bark_camo_w18,
    "fc_feathered_wing": _build_fc_feathered_wing_w16,
    "fc_dorsal_ridge": _build_fc_dorsal_ridge_w17,
    "fc_webbed_membrane": _build_fc_webbed_membrane_w22,
    "fc_toad_skin": _build_fc_toad_skin_w17,
    "fc_antler_bone": _build_fc_antler_bone_w17,
    "fc_mossy_stone": _build_fc_mossy_stone_w33,
    "fc_will_o_wisp": _build_fc_will_o_wisp_w16,
    "fc_snakeskin": _build_fc_snakeskin_w17,
    "fc_batwing": _build_fc_batwing_w35,
    "fc_gator_hide": _build_fc_gator_hide_w16,
    "fc_hide_scale_glass": _build_fc_hide_scale_glass_w18,
    "fc_dragon_hex_glass": _build_fc_dragon_hex_glass_w34,
    "fc_crackle_eyeshine_glass": _build_fc_crackle_eyeshine_glass_w16,
}


# Semantically paired A/B hue families.  These pairs are intentionally far
# enough apart that the opposing M/Cc ownership produces a literal color
# handoff as the reflection lobe changes, while the topology remains legible
# on hue-null evidence.
_HUES: Mapping[str, Tuple[float, float]] = {
    "fc_sasquatch_fur": (0.075, 0.48),       # chestnut / moss-cyan
    "fc_quill_bristle": (0.105, 0.75),       # umber / violet
    "fc_coarse_hide": (0.025, 0.50),         # warm hide / scar teal
    "fc_eyeshine": (0.125, 0.78),            # gold / magenta-cyan optical
    "fc_bog_murk": (0.30, 0.79),             # peat-green / violet oil
    "fc_claw_rake": (0.035, 0.64),           # blood-bone / blue-violet
    "fc_bark_camo": (0.085, 0.30),           # cork / green-gold cambium
    "fc_feathered_wing": (0.73, 0.49),       # dark vane / blue-green barb
    "fc_dorsal_ridge": (0.19, 0.02),         # bone-olive / ember
    "fc_webbed_membrane": (0.79, 0.49),       # smoke-purple / electric teal
    "fc_toad_skin": (0.24, 0.91),            # olive / warning violet-orange
    "fc_antler_bone": (0.115, 0.52),         # ivory / mineral cyan
    "fc_mossy_stone": (0.65, 0.18),          # blue-slate / wet yellow-lime
    "fc_will_o_wisp": (0.48, 0.86),          # cyan / violet-ember
    "fc_snakeskin": (0.22, 0.96),            # olive / copper-violet
    "fc_batwing": (0.77, 0.49),               # black-violet / cyan-red bone
    "fc_gator_hide": (0.22, 0.54),            # mud-olive / teal-copper
    "fc_hide_scale_glass": (0.075, 0.52),      # amber hide / cyan-green lens
    "fc_dragon_hex_glass": (0.39, 0.02),       # emerald / ember-violet folds
    "fc_crackle_eyeshine_glass": (0.135, 0.67),# gold-green / blue-magenta
}

CRYPTID_IDS: Tuple[str, ...] = tuple(_BUILDERS)


@lru_cache(maxsize=8)
def _authored(fid: str) -> Tuple[np.ndarray, np.ndarray]:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    grammar = _BUILDERS[fid]()
    return _compose(grammar, _HUES[fid])


def clear_cache() -> None:
    """Bounded test/audit hook."""
    _authored.cache_clear()
    _xy.cache_clear()


def debug_grammar(fid: str) -> _Grammar:
    """Return a fresh construction graph for palette-free evidence only."""
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _BUILDERS[fid]()


def debug_hue_null(fid: str) -> np.ndarray:
    """Palette-free topology proof; colors cannot hide repeated silhouettes."""
    grammar = debug_grammar(fid)
    out = 0.08 + 0.14 * grammar.tone
    levels = (0.30, 0.70, 0.44, 0.88, 0.56, 0.96, 0.38, 0.79, 0.63)
    for i, (_name, mask, _bank) in enumerate(grammar.marks):
        value = levels[i % len(levels)]
        out = out * (1.0 - mask) + value * mask
    return np.repeat(np.clip(out[..., None], 0, 1), 3, axis=2).astype(np.float32)


def debug_angle_pair(fid: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Controlled two-lobe material proof, not an app renderer replacement.

    Angle A weights the metallic ownership; angle B weights the opposing
    clearcoat ownership.  Paint is unchanged between the two images.  A large
    attached difference therefore proves material-driven Fractured behavior,
    not a second recolored paint asset.
    """
    paint, spec = _authored(fid)
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - 0.55 * rough, 0.22, 1.0)
    gain_a = np.clip(0.18 + 0.98 * metal * aperture, 0.12, 1.18)
    gain_b = np.clip(0.18 + 0.98 * coat * aperture, 0.12, 1.18)
    warm = np.asarray([0.16, 0.08, 0.025], np.float32)
    cool = np.asarray([0.025, 0.095, 0.18], np.float32)
    a = np.clip(paint * gain_a[..., None] + warm * (metal * aperture)[..., None], 0, 1)
    b = np.clip(paint * gain_b[..., None] + cool * (coat * aperture)[..., None], 0, 1)
    diff = np.abs(a - b)
    return a.astype(np.float32), b.astype(np.float32), diff.astype(np.float32)


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
        authored, _ = _authored(fid)
        authored = cv2.resize(authored, (fw, fh), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(m2 * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
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

    spec_fn.__name__ = f"spec_{fid}_rejection_rebuild"
    paint_fn.__name__ = f"paint_{fid}_rejection_rebuild"
    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the twenty current ``fc_*`` monolithic entries."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    eng = _sys.modules.get("shokker_engine_v2")
    if eng is not None and hasattr(eng, "FUSION_REGISTRY"):
        regs.append(eng.FUSION_REGISTRY)
    unique_regs = []
    for reg in regs:
        if all(reg is not other for other in unique_regs):
            unique_regs.append(reg)
    for fid in CRYPTID_IDS:
        entry = _entry(fid)
        for reg in unique_regs:
            reg[fid] = entry
    return f"fractured-wilds-cryptid-rejection-rebuild: {len(CRYPTID_IDS)} explicit grammars live"


if len(CRYPTID_IDS) != 20 or set(CRYPTID_IDS) != set(_HUES):
    raise AssertionError("Cryptid rejection rebuild must own exactly 20 configured IDs")
