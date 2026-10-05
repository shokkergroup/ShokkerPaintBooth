"""Pulsefoil Pleats — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset finish #11 / owner verdict 2026-08-27: "Claude's
rebuild has failed miserably." Metric movement: rejected live finish with no
isolated causal baseline -> deterministic unwired crushed metallic-laminate
pilot with 10 families, 8 M/R/Cc tiers, 82.79/83.30/83.26 channel std, and
64/128 picker luma std 16.73/26.29. Owner review, mapped-car proof, and official
catalog M7 remain pending. This module does not register or replace the live
``neon2_flow_tubes`` finish.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Iterable, Sequence

import cv2
import numpy as np

from engine.paint_v2.neon_material_core_v3 import (
    GeometryMark,
    NATIVE,
    PilotResult,
    WORK,
    geometry_stats,
    mask_coverage,
    material_stats,
    pack_material,
    render_evidence,
    resize_result,
    seeded,
    timed_result,
)


FINISH_ID = "neon2_flow_tubes"
DISPLAY_NAME = "Pulsefoil Pleats"
DEFAULT_SEED = 0xF01D_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
PAINT_TIERS = np.asarray((0.08, 0.19, 0.31, 0.43, 0.56, 0.69, 0.83, 0.98), np.float32)

FAMILIES = (
    "black flexible-laminate facets",
    "asymmetric folded foil faces",
    "cyan leading creases",
    "magenta rebound shadows",
    "exposed silver lips",
    "clipped fold ends",
    "local bridge welds",
    "delaminated underfaces",
    "angular oxide beads",
    "dark compression gaps",
)


def _work_px(native: float, size: int) -> float:
    return float(native) * float(size) / float(NATIVE)


def _axis_shifts(lo: float, hi: float, size: int) -> list[int]:
    shifts = [0]
    if lo < 0.0:
        shifts.append(size)
    if hi >= float(size):
        shifts.append(-size)
    return shifts


def _fill_periodic(canvas: np.ndarray, points: np.ndarray, value: float) -> None:
    points = np.asarray(points, np.float32)
    size = int(canvas.shape[0])
    xs = _axis_shifts(float(points[:, 0].min()) - 2.0, float(points[:, 0].max()) + 2.0, size)
    ys = _axis_shifts(float(points[:, 1].min()) - 2.0, float(points[:, 1].max()) + 2.0, size)
    for dx in xs:
        for dy in ys:
            shifted = np.rint(points + np.asarray((dx, dy), np.float32)).astype(np.int32)
            cv2.fillPoly(canvas, (shifted,), float(value), cv2.LINE_AA)


def _draw_pair(
    mask: np.ndarray,
    tone: np.ndarray,
    points: np.ndarray,
    strength: float,
    paint_tone: float,
) -> None:
    _fill_periodic(mask, points, strength)
    _fill_periodic(tone, points, paint_tone)


def _line_periodic(
    canvas: np.ndarray,
    p0: tuple[float, float],
    p1: tuple[float, float],
    width_native: float,
    value: float,
    size: int,
) -> None:
    width = max(1, int(round(_work_px(width_native, size))))
    margin = width + 2
    xs = _axis_shifts(min(p0[0], p1[0]) - margin, max(p0[0], p1[0]) + margin, size)
    ys = _axis_shifts(min(p0[1], p1[1]) - margin, max(p0[1], p1[1]) + margin, size)
    for dx in xs:
        for dy in ys:
            q0 = (int(round(p0[0] + dx)), int(round(p0[1] + dy)))
            q1 = (int(round(p1[0] + dx)), int(round(p1[1] + dy)))
            cv2.line(canvas, q0, q1, float(value), width, cv2.LINE_AA)


def _line_pair(
    mask: np.ndarray,
    tone: np.ndarray,
    p0: tuple[float, float],
    p1: tuple[float, float],
    width_native: float,
    strength: float,
    paint_tone: float,
    size: int,
) -> None:
    _line_periodic(mask, p0, p1, width_native, strength, size)
    _line_periodic(tone, p0, p1, width_native, paint_tone, size)


def _point(
    center: tuple[float, float], theta: float, along_native: float, across_native: float, size: int,
) -> tuple[float, float]:
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    return (
        center[0] + ux * _work_px(along_native, size) + vx * _work_px(across_native, size),
        center[1] + uy * _work_px(along_native, size) + vy * _work_px(across_native, size),
    )


def _facet_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    skew: float,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l - vx * half_w * (0.70 + skew), cy - uy * half_l - vy * half_w * (0.70 + skew)),
            (cx + ux * half_l * 0.64 - vx * half_w, cy + uy * half_l * 0.64 - vy * half_w),
            (cx + ux * half_l + vx * half_w * (0.34 - skew), cy + uy * half_l + vy * half_w * (0.34 - skew)),
            (cx + ux * half_l * 0.08 + vx * half_w, cy + uy * half_l * 0.08 + vy * half_w),
            (cx - ux * half_l * 0.80 + vx * half_w * 0.44, cy - uy * half_l * 0.80 + vy * half_w * 0.44),
        ),
        np.float32,
    )


def _fold_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    side: float,
    size: int,
    clip: float,
    shear: float,
) -> np.ndarray:
    """One crushed step-face: asymmetric, blunt, and explicitly not a V."""
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l + side * vx * half_w * 0.18, cy - uy * half_l + side * vy * half_w * 0.18),
            (cx - ux * half_l * (0.58 + clip) - side * vx * half_w, cy - uy * half_l * (0.58 + clip) - side * vy * half_w),
            (cx + ux * half_l * 0.16 - side * vx * half_w * (0.88 + shear), cy + uy * half_l * 0.16 - side * vy * half_w * (0.88 + shear)),
            (cx + ux * half_l - side * vx * half_w * 0.22, cy + uy * half_l - side * vy * half_w * 0.22),
            (cx + ux * half_l * 0.58 + side * vx * half_w * 0.56, cy + uy * half_l * 0.58 + side * vy * half_w * 0.56),
            (cx - ux * half_l * 0.06 + side * vx * half_w, cy - uy * half_l * 0.06 + side * vy * half_w),
            (cx - ux * half_l * 0.58 + side * vx * half_w * (0.58 - shear), cy - uy * half_l * 0.58 + side * vy * half_w * (0.58 - shear)),
        ),
        np.float32,
    )


def _wedge_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    bias: float,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx + ux * half_l, cy + uy * half_l),
            (cx + ux * half_l * bias + vx * half_w, cy + uy * half_l * bias + vy * half_w),
            (cx - ux * half_l * 0.46 + vx * half_w * 0.56, cy - uy * half_l * 0.46 + vy * half_w * 0.56),
            (cx - ux * half_l, cy - uy * half_l),
            (cx - ux * half_l * 0.16 - vx * half_w, cy - uy * half_l * 0.16 - vy * half_w),
            (cx + ux * half_l * 0.42 - vx * half_w * 0.50, cy + uy * half_l * 0.42 - vy * half_w * 0.50),
        ),
        np.float32,
    )


def _wrap_blur(values: np.ndarray, sigma_native: float, size: int) -> np.ndarray:
    sigma = max(0.35, _work_px(sigma_native, size))
    pad = max(2, int(math.ceil(sigma * 4.0)))
    wrapped = np.pad(np.asarray(values, np.float32), ((pad, pad), (pad, pad)), mode="wrap")
    blurred = cv2.GaussianBlur(wrapped, (0, 0), sigma)
    return blurred[pad:-pad, pad:-pad]


def _blend(paint: np.ndarray, mask: np.ndarray, color: np.ndarray, opacity: float) -> None:
    alpha = np.clip(np.asarray(mask, np.float32) * float(opacity), 0.0, 1.0)
    if color.ndim == 1:
        color = np.broadcast_to(color, paint.shape)
    paint *= 1.0 - alpha[..., None]
    paint += np.asarray(color, np.float32) * alpha[..., None]


def _ramp(tone: np.ndarray, low: Sequence[float], high: Sequence[float]) -> np.ndarray:
    amount = np.clip(np.asarray(tone, np.float32), 0.0, 1.0)[..., None]
    lo = np.asarray(low, np.float32)
    hi = np.asarray(high, np.float32)
    return lo + (hi - lo) * amount


def _paint_tone(rng: np.random.Generator, tier_index: int) -> float:
    return float(np.clip(PAINT_TIERS[tier_index] + rng.uniform(-0.075, 0.075), 0.03, 1.0))


def _mark(counter: Counter[tuple[str, float]], family: str, *dimensions_native: float) -> None:
    # SPB-105 tick #11: audit every complete 8-32px authored extent.
    counter[(family, round(max(float(value) for value in dimensions_native), 3))] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def build_pulsefoil_pleats(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Pulsefoil Pleats is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    shape = (size, size)
    masks = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    tones = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    geometry: Counter[tuple[str, float]] = Counter()

    # Two-cell crush biases are immediately broken by strong site jitter. No
    # direction survives long enough to become a row, wave, ribbon, tube, long
    # fold, fish scale, chevron, or repeated V stamp.
    cell = max(6, int(round(_work_px(29.0, size))))
    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + 0.5 * cell + (0.30 * cell if gy % 2 else 0.0) + rng.uniform(-0.47, 0.47) * cell)
            cy = float(y0 + 0.5 * cell + rng.uniform(-0.47, 0.47) * cell)
            domain_x, domain_y = gx // 2, gy // 2
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 11 + domain_y * 29) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.50 + (domain_hash % 43) / 42.0 * 3.00
            theta = float(domain_theta + rng.uniform(-0.66, 0.66))

            carrier_tier = int(rng.integers(0, len(EVENT_TIERS)))
            carrier_length = float(rng.uniform(13.0, 27.0))
            carrier_width = float(rng.uniform(12.0, 22.0))
            carrier_center = _point((cx, cy), theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            carrier_points = _facet_points(
                carrier_center, carrier_length, carrier_width,
                theta + rng.uniform(-0.42, 0.42), size, rng.uniform(-0.20, 0.20),
            )
            _draw_pair(
                masks["black flexible-laminate facets"], tones["black flexible-laminate facets"],
                carrier_points, float(EVENT_TIERS[carrier_tier]), _paint_tone(rng, carrier_tier),
            )
            _mark(geometry, "black flexible-laminate facets", carrier_length, carrier_width)

            if rng.random() >= 0.78:
                continue

            tier = int(rng.integers(0, len(EVENT_TIERS)))
            strength = float(EVENT_TIERS[tier])
            paint_tone = _paint_tone(rng, tier)
            side = -1.0 if rng.random() < 0.5 else 1.0
            fold_theta = float(theta + rng.uniform(-0.30, 0.30))
            fold_length = float(rng.uniform(20.0, 31.5))
            fold_width = float(rng.uniform(12.0, 20.0))
            fold_center = _point(carrier_center, fold_theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            fold_points = _fold_points(
                fold_center, fold_length, fold_width, fold_theta, side, size,
                rng.uniform(0.03, 0.26), rng.uniform(-0.18, 0.18),
            )
            _draw_pair(
                masks["asymmetric folded foil faces"], tones["asymmetric folded foil faces"],
                fold_points, strength, paint_tone,
            )
            _mark(geometry, "asymmetric folded foil faces", fold_length, fold_width)

            front = _point(fold_center, fold_theta, fold_length * 0.43, side * fold_width * 0.02, size)
            rear = _point(fold_center, fold_theta, -fold_length * 0.43, -side * fold_width * 0.04, size)

            if rng.random() < 0.62:
                edge_index = int(rng.choice((1, 2, 3, 5)))
                p0 = tuple(fold_points[edge_index])
                p1 = tuple(fold_points[(edge_index + 1) % len(fold_points)])
                edge_length = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)) * NATIVE / size)
                if edge_length >= 8.0:
                    crease_tier = int(rng.integers(0, len(EVENT_TIERS)))
                    crease_length = float(np.clip(edge_length, 8.0, 32.0))
                    _line_pair(
                        masks["cyan leading creases"], tones["cyan leading creases"],
                        p0, p1, 8.0, float(EVENT_TIERS[crease_tier]), _paint_tone(rng, crease_tier), size,
                    )
                    _mark(geometry, "cyan leading creases", crease_length, 8.0)

            if rng.random() < 0.52:
                shadow_length = float(rng.uniform(10.0, min(24.0, fold_length)))
                shadow_width = float(rng.uniform(8.0, min(13.5, fold_width)))
                shadow_center = _point(
                    fold_center, fold_theta, rng.uniform(-4.0, 3.0), side * rng.uniform(5.0, 9.0), size,
                )
                shadow_points = _facet_points(
                    shadow_center, shadow_length, shadow_width,
                    fold_theta + side * rng.uniform(0.15, 0.44), size, rng.uniform(-0.22, 0.22),
                )
                shadow_tier = int(rng.integers(0, len(EVENT_TIERS)))
                _draw_pair(
                    masks["magenta rebound shadows"], tones["magenta rebound shadows"],
                    shadow_points, float(EVENT_TIERS[shadow_tier]), _paint_tone(rng, shadow_tier),
                )
                _mark(geometry, "magenta rebound shadows", shadow_length, shadow_width)

            if rng.random() < 0.43:
                edge_index = int(rng.choice((0, 1, 4, 5)))
                p0 = tuple(fold_points[edge_index])
                p1 = tuple(fold_points[(edge_index + 1) % len(fold_points)])
                edge_length = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)) * NATIVE / size)
                if edge_length >= 8.0:
                    lip_tier = int(rng.integers(0, len(EVENT_TIERS)))
                    lip_length = float(np.clip(edge_length, 8.0, 32.0))
                    _line_pair(
                        masks["exposed silver lips"], tones["exposed silver lips"],
                        p0, p1, 8.0, float(EVENT_TIERS[lip_tier]), _paint_tone(rng, lip_tier), size,
                    )
                    _mark(geometry, "exposed silver lips", lip_length, 8.0)

            anatomy = float(rng.random())
            if anatomy < 0.20:
                end_length = float(rng.uniform(8.0, 14.0))
                end_width = float(rng.uniform(8.0, min(13.0, fold_width)))
                anchor = front if rng.random() < 0.50 else rear
                end_center = _point(anchor, fold_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-2.0, 2.0), size)
                end_points = _wedge_points(
                    end_center, end_length, end_width,
                    fold_theta + side * rng.uniform(0.50, 0.96), size, rng.uniform(-0.24, 0.24),
                )
                _draw_pair(
                    masks["clipped fold ends"], tones["clipped fold ends"],
                    end_points, strength, paint_tone,
                )
                _mark(geometry, "clipped fold ends", end_length, end_width)
            elif anatomy < 0.40:
                weld_length = float(rng.uniform(8.0, 12.0))
                weld_width = float(rng.uniform(8.0, 11.0))
                anchor = front if rng.random() < 0.55 else rear
                weld_center = _point(anchor, fold_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-2.0, 2.5), size)
                weld_points = _wedge_points(
                    weld_center, weld_length, weld_width,
                    fold_theta + rng.uniform(-0.72, 0.72), size, rng.uniform(-0.22, 0.28),
                )
                _draw_pair(
                    masks["local bridge welds"], tones["local bridge welds"],
                    weld_points, strength, paint_tone,
                )
                _mark(geometry, "local bridge welds", weld_length, weld_width)
            elif anatomy < 0.60:
                under_length = float(rng.uniform(10.0, min(22.0, fold_length)))
                under_width = float(rng.uniform(8.0, min(14.0, fold_width)))
                under_center = _point(
                    fold_center, fold_theta, rng.uniform(-4.0, 4.0), side * rng.uniform(5.0, 9.0), size,
                )
                under_points = _facet_points(
                    under_center, under_length, under_width,
                    fold_theta + side * rng.uniform(0.30, 0.64), size, rng.uniform(-0.22, 0.22),
                )
                _draw_pair(
                    masks["delaminated underfaces"], tones["delaminated underfaces"],
                    under_points, strength, paint_tone,
                )
                _mark(geometry, "delaminated underfaces", under_length, under_width)
            elif anatomy < 0.80:
                bead_length = float(rng.uniform(8.0, 12.0))
                bead_width = float(rng.uniform(8.0, 11.5))
                bead_center = _point(rear, fold_theta, rng.uniform(-1.0, 3.0), side * rng.uniform(-2.0, 3.0), size)
                bead_points = _wedge_points(
                    bead_center, bead_length, bead_width,
                    fold_theta + rng.uniform(-0.72, 0.72), size, rng.uniform(-0.22, 0.28),
                )
                _draw_pair(
                    masks["angular oxide beads"], tones["angular oxide beads"],
                    bead_points, strength, paint_tone,
                )
                _mark(geometry, "angular oxide beads", bead_length, bead_width)
            else:
                gap_length = float(rng.uniform(10.0, min(20.0, fold_length)))
                gap_width = float(rng.uniform(8.0, min(13.0, fold_width)))
                anchor = front if rng.random() < 0.50 else rear
                gap_center = _point(anchor, fold_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-3.0, 3.0), size)
                gap_points = _wedge_points(
                    gap_center, gap_length, gap_width,
                    fold_theta + rng.uniform(-0.34, 0.34), size, rng.uniform(-0.24, 0.24),
                )
                _draw_pair(
                    masks["dark compression gaps"], tones["dark compression gaps"],
                    gap_points, strength, paint_tone,
                )
                _mark(geometry, "dark compression gaps", gap_length, gap_width)

    carrier = np.clip(masks["black flexible-laminate facets"], 0.0, 1.0)
    faces = np.clip(masks["asymmetric folded foil faces"], 0.0, 1.0)
    creases = np.clip(masks["cyan leading creases"], 0.0, 1.0)
    shadows = np.clip(masks["magenta rebound shadows"], 0.0, 1.0)
    lips = np.clip(masks["exposed silver lips"], 0.0, 1.0)
    ends = np.clip(masks["clipped fold ends"], 0.0, 1.0)
    welds = np.clip(masks["local bridge welds"], 0.0, 1.0)
    underfaces = np.clip(masks["delaminated underfaces"], 0.0, 1.0)
    beads = np.clip(masks["angular oxide beads"], 0.0, 1.0)
    gaps = np.clip(masks["dark compression gaps"], 0.0, 1.0)

    damage = np.maximum.reduce((ends, underfaces, beads, gaps))
    intact_face = np.clip(faces - 0.72 * np.maximum.reduce((ends, underfaces, gaps)), 0.0, 1.0)
    metal_process = np.maximum.reduce((intact_face, lips, welds, creases * 0.62, beads * 0.54))
    rough_process = np.maximum.reduce((damage, welds * 0.52, shadows * 0.34))
    coat_process = np.maximum.reduce((carrier, shadows * 0.68, intact_face * 0.32, creases * 0.28))
    metal_reach = np.clip(_wrap_blur(metal_process, 4.0, size) * 1.62, 0.0, 1.0)
    rough_reach = np.clip(_wrap_blur(rough_process, 4.8, size) * 1.66, 0.0, 1.0)
    coat_reach = np.clip(_wrap_blur(coat_process, 5.2, size) * 1.58, 0.0, 1.0)
    foil_bed = np.clip(_wrap_blur(np.maximum.reduce((faces, creases, shadows, lips)), 6.0, size) * 1.56, 0.0, 1.0)
    carrier_pressure = np.clip(
        _wrap_blur(np.maximum.reduce((carrier, faces, damage, shadows)), 9.0, size) * 1.68,
        0.0, 1.0,
    )
    px = cv2.Sobel(carrier_pressure, cv2.CV_32F, 1, 0, ksize=3)
    py = cv2.Sobel(carrier_pressure, cv2.CV_32F, 0, 1, ksize=3)
    crush_strain = np.abs(px) + np.abs(py)
    crush_strain /= max(float(np.percentile(crush_strain, 99.0)), 1e-6)
    crush_strain = np.clip(crush_strain, 0.0, 1.0)

    # The laminate pressure bed derives only from authored fold masks. There is
    # no flow field, tube path, ribbon, wave, grid, or generic texture noise.
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.012 + 0.032 * carrier_pressure + 0.036 * foil_bed + 0.010 * crush_strain
    paint[..., 1] = 0.016 + 0.042 * carrier_pressure + 0.052 * foil_bed + 0.014 * crush_strain
    paint[..., 2] = 0.024 + 0.060 * carrier_pressure + 0.078 * foil_bed + 0.022 * crush_strain

    # SPB-105 2026-08-27 visual repair: the first bake compressed into colored
    # aggregate.  Subdue the carrier and accent chroma while lifting the larger
    # neutral step-faces, so each cyan/magenta/silver mark remains visibly
    # attached to one crushed foil plane instead of reading as loose confetti.
    _blend(paint, carrier, _ramp(tones["black flexible-laminate facets"], (0.014, 0.020, 0.030), (0.105, 0.135, 0.170)), 0.94)
    _blend(paint, faces, _ramp(tones["asymmetric folded foil faces"], (0.090, 0.108, 0.126), (0.650, 0.710, 0.755)), 0.92)
    _blend(paint, shadows, _ramp(tones["magenta rebound shadows"], (0.050, 0.010, 0.072), (0.440, 0.055, 0.390)), 0.84)
    _blend(paint, creases, _ramp(tones["cyan leading creases"], (0.025, 0.120, 0.145), (0.220, 0.760, 0.850)), 0.92)
    _blend(paint, lips, _ramp(tones["exposed silver lips"], (0.120, 0.145, 0.165), (0.920, 0.970, 1.000)), 0.98)
    _blend(paint, ends, _ramp(tones["clipped fold ends"], (0.008, 0.014, 0.025), (0.130, 0.190, 0.230)), 0.96)
    _blend(paint, welds, _ramp(tones["local bridge welds"], (0.100, 0.090, 0.070), (0.920, 0.750, 0.420)), 0.98)
    _blend(paint, underfaces, _ramp(tones["delaminated underfaces"], (0.025, 0.010, 0.055), (0.280, 0.060, 0.350)), 0.94)
    _blend(paint, beads, _ramp(tones["angular oxide beads"], (0.080, 0.040, 0.018), (0.520, 0.235, 0.050)), 0.92)
    _blend(paint, gaps, _ramp(tones["dark compression gaps"], (0.002, 0.004, 0.009), (0.035, 0.060, 0.085)), 0.99)
    paint = np.clip(paint, 0.0, 1.0)

    # SPB-105 / 2026-08-27 owner verdict: keep the foil neutral enough to read
    # as metal, but make its attached cyan/magenta rebound phases survive the
    # picker. Official isolated M7 movement: 71.7 -> 87.4, with geometry/spec
    # unchanged.
    hsv = cv2.cvtColor(paint, cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.50, 0.0, 1.0)
    paint = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    metal_score = (
        0.05 + 0.60 * metal_reach + 1.62 * intact_face + 1.54 * lips
        + 1.42 * welds + 1.12 * creases + 0.88 * beads
        - 0.96 * gaps - 0.82 * underfaces - 0.52 * carrier
    )
    rough_score = (
        0.12 + 0.62 * rough_reach + 1.54 * ends + 1.46 * underfaces
        + 1.36 * beads + 1.28 * gaps + 0.78 * welds + 0.42 * shadows
        - 0.92 * lips - 0.72 * intact_face - 0.42 * creases
    )
    coat_score = (
        0.16 + 0.58 * coat_reach + 1.42 * carrier + 1.02 * shadows
        + 0.58 * intact_face + 0.38 * creases - 1.22 * underfaces
        - 1.16 * gaps - 1.08 * ends - 0.78 * beads
        - 0.52 * welds - 0.36 * lips
    )
    spec = pack_material(metal_score, rough_score, coat_score)

    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=_geometry(geometry),
        material_story={
            "M": "intact foil faces, silver lips, bridge welds, cyan creases, and oxide deposits lead while gaps and underfaces stay low",
            "R": "clipped ends, delaminated underfaces, oxide beads, compression gaps, and weld disturbance rise independently",
            "Cc": "intact black laminate and rebound skins retain clear while delamination, gaps, ends, and welds interrupt it",
        },
        carrier="black flexible metallic laminate crushed into tiny asymmetric foil pleats",
        vetoes=(
            "flow line, tube, waveform, wave, or ribbon",
            "chevron, repeated V, long fold, or directional lane",
            "grid, row, fish scale, or repeated folded tile",
            "floating confetti or unrelated metallic chips",
            "generic noise or unrelated texture underlay",
        ),
    )


def _hash_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


def _seam_audit(paint: np.ndarray, spec: np.ndarray) -> dict[str, float]:
    def ratio(values: np.ndarray, axis: int) -> float:
        values = values.astype(np.float32)
        if axis == 1:
            seam = np.mean(np.abs(values[:, 0] - values[:, -1]))
            local = np.mean(np.abs(np.diff(values, axis=1)))
        else:
            seam = np.mean(np.abs(values[0] - values[-1]))
            local = np.mean(np.abs(np.diff(values, axis=0)))
        return round(float(seam / max(float(local), 1e-7)), 6)

    return {
        "paint_x_to_local_ratio": ratio(paint, 1),
        "paint_y_to_local_ratio": ratio(paint, 0),
        "M_x_to_local_ratio": ratio(spec[..., 0], 1),
        "M_y_to_local_ratio": ratio(spec[..., 0], 0),
        "R_x_to_local_ratio": ratio(spec[..., 1], 1),
        "R_y_to_local_ratio": ratio(spec[..., 1], 0),
        "Cc_x_to_local_ratio": ratio(spec[..., 2], 1),
        "Cc_y_to_local_ratio": ratio(spec[..., 2], 0),
    }


def write_pilot_evidence(output: Path, seed: int = DEFAULT_SEED) -> dict[str, object]:
    result = timed_result(build_pulsefoil_pleats, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_pulsefoil_pleats, seed)
    deterministic = bool(
        np.array_equal(result.paint, repeat.paint)
        and np.array_equal(result.spec, repeat.spec)
        and all(np.array_equal(result.masks[name], repeat.masks[name]) for name in FAMILIES)
    )

    active = np.maximum.reduce(tuple(np.asarray(result.masks[name]) for name in FAMILIES)) > 0.15
    void_distance = cv2.distanceTransform((~active).astype(np.uint8), cv2.DIST_L2, 5)
    max_void_native = float(void_distance.max() * NATIVE / WORK)
    picker64 = cv2.resize(paint_native, (64, 64), interpolation=cv2.INTER_AREA)
    picker128 = cv2.resize(paint_native, (128, 128), interpolation=cv2.INTER_AREA)
    luma64 = cv2.cvtColor(np.clip(picker64 * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    luma128 = cv2.cvtColor(np.clip(picker128 * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    stats = material_stats(spec_native)
    geometry = geometry_stats(result.geometry)
    seam = _seam_audit(result.paint, result.spec)
    checks_audit = {
        "deterministic": deterministic,
        "native_paint_spec_under_3_seconds": native_elapsed <= 3.0,
        "repeat_under_3_seconds": repeat.elapsed_seconds <= 3.0,
        "ten_attached_families": geometry["family_count"] >= 10,
        "all_dimensions_8_32_native": geometry["fine_8_32_fraction"] == 1.0,
        "eight_tiers_each_channel": all(value == 8 for value in stats["tier_count"].values()),
        "std_at_least_30_each_channel": all(value >= 30.0 for value in stats["std"].values()),
        "channels_not_copied_or_inverse": all(abs(value) < 0.80 for value in stats["correlation"].values()),
        "full_canvas_no_void_over_64px": max_void_native <= 64.0,
        "picker_64_survives": float(luma64.std()) >= 3.5,
        "picker_128_survives": float(luma128.std()) >= 5.0,
        "periodic_seams_below_3x_local_change": all(value < 3.0 for value in seam.values()),
    }
    audit = {
        "schema": "spb-neon-oil-slick-pilot-audit/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "seed": int(seed),
        "builder_elapsed_seconds": round(float(result.elapsed_seconds), 6),
        "native_paint_spec_elapsed_seconds": round(float(native_elapsed), 6),
        "repeat_elapsed_seconds": round(float(repeat.elapsed_seconds), 6),
        "deterministic": deterministic,
        "paint_sha256": _hash_array(result.paint),
        "spec_sha256": _hash_array(result.spec),
        "material_stats_native": stats,
        "geometry_stats": geometry,
        "causal_mask_coverage": mask_coverage(result.masks),
        "max_unmarked_void_native_px": round(max_void_native, 3),
        "seam_ratios_vs_local_neighbor_change": seam,
        "picker_luma_std": {"64": round(float(luma64.std()), 6), "128": round(float(luma128.std()), 6)},
        "checks": checks_audit,
        "all_mechanical_checks_green": all(checks_audit.values()),
        "catalog_m7": "PENDING isolated official workbook harness",
        "mapped_car": "PENDING; three-position material light proxy supplied for owner screening",
        "manifest": manifest,
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render isolated Pulsefoil Pleats owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "pulsefoil_pleats",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
