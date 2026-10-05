"""Burner Impact — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset finish #10 / owner verdict 2026-08-27: "Claude's
rebuild has failed miserably." Metric movement: rejected live finish with no
isolated causal baseline -> deterministic unwired hot-metal/thermal-ceramic
pilot pending owner review, mapped-car proof, and official catalog M7. This
module does not register or replace the live ``neon2_splatter`` finish.
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


FINISH_ID = "neon2_splatter"
DISPLAY_NAME = "Burner Impact"
DEFAULT_SEED = 0xB017_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
PAINT_TIERS = np.asarray((0.08, 0.19, 0.31, 0.43, 0.56, 0.69, 0.83, 0.98), np.float32)

FAMILIES = (
    "black thermal-ceramic facets",
    "flattened hot-metal impact plates",
    "orange molten lips",
    "magenta recoil shadows",
    "cyan temper pinpoints",
    "chipped attached ejecta",
    "collapsed crater wedges",
    "angular oxide beads",
    "quenched impact centers",
    "single short fracture stubs",
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


def _impact_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    side: float,
    size: int,
    head_clip: float,
    shear: float,
) -> np.ndarray:
    """One flattened cleaved plate, with no radial or circular symmetry."""
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l + side * vx * half_w * 0.20, cy - uy * half_l + side * vy * half_w * 0.20),
            (cx - ux * half_l * 0.62 - side * vx * half_w, cy - uy * half_l * 0.62 - side * vy * half_w),
            (cx + ux * half_l * 0.18 - side * vx * half_w * (0.88 + shear), cy + uy * half_l * 0.18 - side * vy * half_w * (0.88 + shear)),
            (cx + ux * half_l - side * vx * half_w * (0.30 + head_clip), cy + uy * half_l - side * vy * half_w * (0.30 + head_clip)),
            (cx + ux * half_l * (0.72 - head_clip) + side * vx * half_w, cy + uy * half_l * (0.72 - head_clip) + side * vy * half_w),
            (cx + ux * half_l * 0.06 + side * vx * half_w * (0.72 - shear), cy + uy * half_l * 0.06 + side * vy * half_w * (0.72 - shear)),
            (cx - ux * half_l * 0.56 + side * vx * half_w * 0.60, cy - uy * half_l * 0.56 + side * vy * half_w * 0.60),
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
    # SPB-105 tick #10: record full authored extents for the owner's 8-32px rule.
    counter[(family, round(max(float(value) for value in dimensions_native), 3))] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def build_burner_impact(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Burner Impact is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    shape = (size, size)
    masks = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    tones = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    geometry: Counter[tuple[str, float]] = Counter()

    # Jittered sites carry two-cell blast biases. Each impact has one primary
    # consequence and at most one fracture direction, so no star, flower,
    # bullet-hole icon, ray field, row, or splatter silhouette can emerge.
    cell = max(6, int(round(_work_px(29.0, size))))
    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + 0.5 * cell + (0.30 * cell if gy % 2 else 0.0) + rng.uniform(-0.47, 0.47) * cell)
            cy = float(y0 + 0.5 * cell + rng.uniform(-0.47, 0.47) * cell)
            domain_x, domain_y = gx // 2, gy // 2
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 23 + domain_y * 7) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.50 + (domain_hash % 43) / 42.0 * 3.00
            theta = float(domain_theta + rng.uniform(-0.64, 0.64))

            carrier_tier = int(rng.integers(0, len(EVENT_TIERS)))
            carrier_length = float(rng.uniform(13.0, 27.0))
            carrier_width = float(rng.uniform(11.0, 22.0))
            carrier_center = _point((cx, cy), theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            carrier_points = _facet_points(
                carrier_center, carrier_length, carrier_width,
                theta + rng.uniform(-0.40, 0.40), size, rng.uniform(-0.20, 0.20),
            )
            _draw_pair(
                masks["black thermal-ceramic facets"], tones["black thermal-ceramic facets"],
                carrier_points, float(EVENT_TIERS[carrier_tier]), _paint_tone(rng, carrier_tier),
            )
            _mark(geometry, "black thermal-ceramic facets", carrier_length, carrier_width)

            if rng.random() >= 0.70:
                continue

            tier = int(rng.integers(0, len(EVENT_TIERS)))
            strength = float(EVENT_TIERS[tier])
            paint_tone = _paint_tone(rng, tier)
            side = -1.0 if rng.random() < 0.5 else 1.0
            impact_theta = float(theta + rng.uniform(-0.30, 0.30))
            plate_length = float(rng.uniform(15.0, 29.0))
            plate_width = float(rng.uniform(11.5, 19.5))
            plate_center = _point(carrier_center, impact_theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            plate_points = _impact_points(
                plate_center, plate_length, plate_width, impact_theta, side, size,
                rng.uniform(0.04, 0.28), rng.uniform(-0.18, 0.18),
            )
            _draw_pair(
                masks["flattened hot-metal impact plates"], tones["flattened hot-metal impact plates"],
                plate_points, strength, paint_tone,
            )
            _mark(geometry, "flattened hot-metal impact plates", plate_length, plate_width)

            front = _point(plate_center, impact_theta, plate_length * 0.43, side * plate_width * 0.02, size)
            rear = _point(plate_center, impact_theta, -plate_length * 0.43, -side * plate_width * 0.04, size)

            if rng.random() < 0.40:
                edge_index = int(rng.choice((1, 2, 3, 5)))
                p0 = tuple(plate_points[edge_index])
                p1 = tuple(plate_points[(edge_index + 1) % len(plate_points)])
                edge_length = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)) * NATIVE / size)
                if edge_length >= 8.0:
                    lip_tier = int(rng.integers(0, len(EVENT_TIERS)))
                    lip_length = float(np.clip(edge_length, 8.0, 32.0))
                    _line_pair(
                        masks["orange molten lips"], tones["orange molten lips"],
                        p0, p1, 8.0, float(EVENT_TIERS[lip_tier]), _paint_tone(rng, lip_tier), size,
                    )
                    _mark(geometry, "orange molten lips", lip_length, 8.0)

            if rng.random() < 0.50:
                shadow_length = float(rng.uniform(10.0, min(24.0, plate_length)))
                shadow_width = float(rng.uniform(8.0, min(13.5, plate_width)))
                shadow_center = _point(
                    plate_center, impact_theta, rng.uniform(-4.0, 3.0), side * rng.uniform(5.0, 9.0), size,
                )
                shadow_points = _facet_points(
                    shadow_center, shadow_length, shadow_width,
                    impact_theta + side * rng.uniform(0.16, 0.44), size, rng.uniform(-0.22, 0.22),
                )
                shadow_tier = int(rng.integers(0, len(EVENT_TIERS)))
                _draw_pair(
                    masks["magenta recoil shadows"], tones["magenta recoil shadows"],
                    shadow_points, float(EVENT_TIERS[shadow_tier]), _paint_tone(rng, shadow_tier),
                )
                _mark(geometry, "magenta recoil shadows", shadow_length, shadow_width)

            anatomy = float(rng.random())
            if anatomy < 0.14:
                pin_length = float(rng.uniform(8.0, 10.5))
                pin_width = float(rng.uniform(8.0, 10.0))
                anchor = front if rng.random() < 0.62 else rear
                pin_center = _point(anchor, impact_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-2.0, 2.0), size)
                pin_points = _wedge_points(
                    pin_center, pin_length, pin_width,
                    impact_theta + rng.uniform(-0.80, 0.80), size, rng.uniform(-0.22, 0.28),
                )
                _draw_pair(
                    masks["cyan temper pinpoints"], tones["cyan temper pinpoints"],
                    pin_points, strength, paint_tone,
                )
                _mark(geometry, "cyan temper pinpoints", pin_length, pin_width)
            elif anatomy < 0.31:
                ejecta_count = 1 + int(rng.random() < 0.38)
                for index in range(ejecta_count):
                    chip_length = float(rng.uniform(8.0, 11.0))
                    chip_width = float(rng.uniform(8.0, 10.0))
                    chip_center = _point(
                        rear, impact_theta, -rng.uniform(2.0 + index * 4.0, 5.0 + index * 5.0),
                        side * rng.uniform(-4.0, 5.0), size,
                    )
                    chip_points = _wedge_points(
                        chip_center, chip_length, chip_width,
                        impact_theta + rng.uniform(-0.85, 0.85), size, rng.uniform(-0.24, 0.28),
                    )
                    chip_tier = int(rng.integers(0, len(EVENT_TIERS)))
                    _draw_pair(
                        masks["chipped attached ejecta"], tones["chipped attached ejecta"],
                        chip_points, float(EVENT_TIERS[chip_tier]), _paint_tone(rng, chip_tier),
                    )
                    _mark(geometry, "chipped attached ejecta", chip_length, chip_width)
            elif anatomy < 0.47:
                wedge_length = float(rng.uniform(9.0, 16.0))
                wedge_width = float(rng.uniform(8.0, min(13.0, plate_width)))
                anchor = front if rng.random() < 0.50 else rear
                wedge_center = _point(anchor, impact_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-2.0, 2.0), size)
                wedge_points = _wedge_points(
                    wedge_center, wedge_length, wedge_width,
                    impact_theta + side * rng.uniform(0.50, 0.98), size, rng.uniform(-0.24, 0.24),
                )
                _draw_pair(
                    masks["collapsed crater wedges"], tones["collapsed crater wedges"],
                    wedge_points, strength, paint_tone,
                )
                _mark(geometry, "collapsed crater wedges", wedge_length, wedge_width)
            elif anatomy < 0.63:
                bead_length = float(rng.uniform(8.0, 12.0))
                bead_width = float(rng.uniform(8.0, 11.5))
                bead_center = _point(rear, impact_theta, rng.uniform(-1.0, 3.0), side * rng.uniform(-2.0, 3.0), size)
                bead_points = _wedge_points(
                    bead_center, bead_length, bead_width,
                    impact_theta + rng.uniform(-0.72, 0.72), size, rng.uniform(-0.22, 0.28),
                )
                _draw_pair(
                    masks["angular oxide beads"], tones["angular oxide beads"],
                    bead_points, strength, paint_tone,
                )
                _mark(geometry, "angular oxide beads", bead_length, bead_width)
            elif anatomy < 0.80:
                center_length = float(rng.uniform(10.0, min(20.0, plate_length)))
                center_width = float(rng.uniform(8.0, min(13.0, plate_width)))
                # Bias quench collapse to one fractured end. A centered dark
                # insert plus molten lip formed a bullet-hole/bullseye in the
                # first screen even though no circle primitive existed.
                anchor = front if rng.random() < 0.50 else rear
                center_anchor = _point(
                    anchor, impact_theta, rng.uniform(-1.0, 2.0),
                    side * rng.uniform(-3.0, 3.5), size,
                )
                center_points = _wedge_points(
                    center_anchor, center_length, center_width,
                    impact_theta + rng.uniform(-0.34, 0.34), size, rng.uniform(-0.24, 0.24),
                )
                _draw_pair(
                    masks["quenched impact centers"], tones["quenched impact centers"],
                    center_points, strength, paint_tone,
                )
                _mark(geometry, "quenched impact centers", center_length, center_width)
            else:
                stub_length = float(rng.uniform(8.0, 15.0))
                stub_theta = impact_theta + side * rng.uniform(0.50, 1.04)
                anchor = front if rng.random() < 0.50 else rear
                stub_end = _point(anchor, stub_theta, stub_length, 0.0, size)
                _line_pair(
                    masks["single short fracture stubs"], tones["single short fracture stubs"],
                    anchor, stub_end, 8.0, strength, paint_tone, size,
                )
                _mark(geometry, "single short fracture stubs", stub_length, 8.0)

    carrier = np.clip(masks["black thermal-ceramic facets"], 0.0, 1.0)
    plates = np.clip(masks["flattened hot-metal impact plates"], 0.0, 1.0)
    lips = np.clip(masks["orange molten lips"], 0.0, 1.0)
    shadows = np.clip(masks["magenta recoil shadows"], 0.0, 1.0)
    pins = np.clip(masks["cyan temper pinpoints"], 0.0, 1.0)
    ejecta = np.clip(masks["chipped attached ejecta"], 0.0, 1.0)
    craters = np.clip(masks["collapsed crater wedges"], 0.0, 1.0)
    beads = np.clip(masks["angular oxide beads"], 0.0, 1.0)
    centers = np.clip(masks["quenched impact centers"], 0.0, 1.0)
    stubs = np.clip(masks["single short fracture stubs"], 0.0, 1.0)

    damage = np.maximum.reduce((ejecta, craters, centers, stubs))
    intact_plate = np.clip(plates - 0.72 * np.maximum.reduce((craters, centers, stubs)), 0.0, 1.0)
    metal_process = np.maximum.reduce((intact_plate, lips, pins, beads * 0.74))
    rough_process = np.maximum.reduce((damage, beads * 0.68, shadows * 0.30))
    coat_process = np.maximum.reduce((carrier, centers * 0.52, shadows * 0.42, intact_plate * 0.26))
    metal_reach = np.clip(_wrap_blur(metal_process, 4.0, size) * 1.62, 0.0, 1.0)
    rough_reach = np.clip(_wrap_blur(rough_process, 4.8, size) * 1.66, 0.0, 1.0)
    coat_reach = np.clip(_wrap_blur(coat_process, 5.2, size) * 1.58, 0.0, 1.0)
    heat_bed = np.clip(_wrap_blur(np.maximum.reduce((plates, lips, shadows, pins)), 6.0, size) * 1.56, 0.0, 1.0)
    carrier_pressure = np.clip(
        _wrap_blur(np.maximum.reduce((carrier, plates, damage, shadows)), 9.0, size) * 1.68,
        0.0, 1.0,
    )
    px = cv2.Sobel(carrier_pressure, cv2.CV_32F, 1, 0, ksize=3)
    py = cv2.Sobel(carrier_pressure, cv2.CV_32F, 0, 1, ksize=3)
    thermal_strain = np.abs(px) + np.abs(py)
    thermal_strain /= max(float(np.percentile(thermal_strain, 99.0)), 1e-6)
    thermal_strain = np.clip(thermal_strain, 0.0, 1.0)

    # The carrier and heat bed derive from impact masks only. There is no paint
    # splatter, droplet field, blob noise, radial burst, or unrelated texture.
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.018 + 0.052 * carrier_pressure + 0.072 * heat_bed + 0.014 * thermal_strain
    paint[..., 1] = 0.011 + 0.026 * carrier_pressure + 0.020 * heat_bed + 0.010 * thermal_strain
    paint[..., 2] = 0.020 + 0.052 * carrier_pressure + 0.034 * heat_bed + 0.020 * thermal_strain

    # 2026-08-27 visual repair: a broader visible ceramic/iron bed replaces the
    # first pass's repeated orange-chip cadence; molten orange stays localized.
    _blend(paint, carrier, _ramp(tones["black thermal-ceramic facets"], (0.030, 0.018, 0.030), (0.220, 0.075, 0.125)), 0.96)
    _blend(paint, plates, _ramp(tones["flattened hot-metal impact plates"], (0.075, 0.016, 0.012), (0.610, 0.150, 0.030)), 0.80)
    _blend(paint, shadows, _ramp(tones["magenta recoil shadows"], (0.070, 0.008, 0.070), (0.650, 0.055, 0.500)), 0.88)
    _blend(paint, lips, _ramp(tones["orange molten lips"], (0.180, 0.025, 0.005), (1.000, 0.560, 0.055)), 0.98)
    _blend(paint, pins, _ramp(tones["cyan temper pinpoints"], (0.020, 0.130, 0.160), (0.350, 0.930, 1.000)), 0.99)
    _blend(paint, ejecta, _ramp(tones["chipped attached ejecta"], (0.075, 0.016, 0.010), (0.570, 0.120, 0.030)), 0.90)
    _blend(paint, craters, _ramp(tones["collapsed crater wedges"], (0.004, 0.006, 0.010), (0.075, 0.045, 0.060)), 0.98)
    _blend(paint, beads, _ramp(tones["angular oxide beads"], (0.110, 0.055, 0.018), (0.880, 0.430, 0.065)), 0.97)
    _blend(paint, centers, _ramp(tones["quenched impact centers"], (0.003, 0.005, 0.010), (0.120, 0.025, 0.085)), 0.98)
    _blend(paint, stubs, _ramp(tones["single short fracture stubs"], (0.035, 0.012, 0.022), (0.360, 0.095, 0.110)), 0.92)
    # SPB-105 / 2026-08-27 owner verdict: lift the causal impact anatomy rather
    # than enlarge it. Official isolated M7 before calibration: 83.3; final
    # movement is recorded by the next private workbook run.
    paint = np.clip(paint * 1.60, 0.0, 1.0)

    metal_score = (
        0.05 + 0.60 * metal_reach + 1.58 * intact_plate + 1.52 * lips
        + 1.44 * pins + 1.18 * beads + 0.46 * ejecta
        - 0.92 * craters - 0.84 * centers - 0.54 * carrier
    )
    rough_score = (
        0.12 + 0.62 * rough_reach + 1.56 * ejecta + 1.48 * craters
        + 1.38 * stubs + 1.22 * beads + 1.08 * centers + 0.44 * shadows
        - 0.90 * lips - 0.66 * intact_plate - 0.42 * pins
    )
    coat_score = (
        0.16 + 0.58 * coat_reach + 1.42 * carrier + 1.04 * centers
        + 0.62 * shadows + 0.42 * intact_plate - 1.22 * lips
        - 1.16 * craters - 1.10 * ejecta - 0.92 * stubs
        - 0.58 * beads - 0.34 * pins
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
            "M": "intact hot-metal plates, molten lips, cyan temper points, and oxide beads lead while crater collapse stays low",
            "R": "attached ejecta, collapsed wedges, single fracture stubs, oxide beads, and quenched centers rise independently",
            "Cc": "intact black ceramic and quenched centers retain clear while molten and fractured impact anatomy interrupts it",
        },
        carrier="black thermal ceramic struck by flattened hot-metal impact plates",
        vetoes=(
            "paint splatter, blob, droplet, or liquid-spill illustration",
            "star, starburst, flower, radial packet, or bullet-hole icon",
            "long ray, spoke field, repeated circle, or ring",
            "floating confetti or unrelated colored chips",
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
    result = timed_result(build_burner_impact, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_burner_impact, seed)
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
    parser = argparse.ArgumentParser(description="Render isolated Burner Impact owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "burner_impact",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
