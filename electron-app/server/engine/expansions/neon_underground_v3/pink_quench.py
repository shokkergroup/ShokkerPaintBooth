"""Pink Quench — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset finish #7 / owner verdict 2026-08-27: "Claude's
rebuild has failed miserably." Metric movement: rejected live finish with no
isolated causal baseline -> deterministic unwired thermal-shock glass pilot
pending owner review, mapped-car proof, and official catalog M7. This module
does not register or replace the live ``neon_pink_blaze`` finish.
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


FINISH_ID = "neon_pink_blaze"
DISPLAY_NAME = "Pink Quench"
DEFAULT_SEED = 0x91A0_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
PAINT_TIERS = np.asarray((0.08, 0.19, 0.31, 0.43, 0.56, 0.69, 0.83, 0.98), np.float32)

FAMILIES = (
    "black ceramic shock facets",
    "magenta glass splinters",
    "pale temper lips",
    "violet cooling shadows",
    "cyan stress pinpoints",
    "broken glass ends",
    "short branching checks",
    "quenched glass beads",
    "oxide crumbs",
    "dark quenched pits",
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
            cv2.fillConvexPoly(canvas, shifted, float(value), cv2.LINE_AA)


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


def _splinter_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    cleave: float,
    skew: float,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    # Six unequal vertices form one blunt cleaved shard. The two-ended fracture
    # profile avoids the pointed bilateral leaf/petal silhouette entirely.
    return np.asarray(
        (
            (cx + ux * half_l + vx * half_w * 0.18, cy + uy * half_l + vy * half_w * 0.18),
            (cx + ux * half_l * 0.12 + vx * half_w, cy + uy * half_l * 0.12 + vy * half_w),
            (cx - ux * half_l * cleave + vx * half_w * (0.64 + skew), cy - uy * half_l * cleave + vy * half_w * (0.64 + skew)),
            (cx - ux * half_l - vx * half_w * 0.12, cy - uy * half_l - vy * half_w * 0.12),
            (cx - ux * half_l * 0.34 - vx * half_w, cy - uy * half_l * 0.34 - vy * half_w),
            (cx + ux * half_l * 0.76 - vx * half_w * (0.52 - skew), cy + uy * half_l * 0.76 - vy * half_w * (0.52 - skew)),
        ),
        np.float32,
    )


def _facet_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    taper: float,
    skew: float,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l - vx * half_w, cy - uy * half_l - vy * half_w),
            (cx + ux * half_l - vx * half_w * taper, cy + uy * half_l - vy * half_w * taper),
            (cx + ux * half_l + vx * half_w * (0.52 + skew), cy + uy * half_l + vy * half_w * (0.52 + skew)),
            (cx - ux * half_l + vx * half_w * (0.80 - skew), cy - uy * half_l + vy * half_w * (0.80 - skew)),
        ),
        np.float32,
    )


def _nugget_points(
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
            (cx - ux * half_l * 0.72 + vx * half_w * 0.50, cy - uy * half_l * 0.72 + vy * half_w * 0.50),
            (cx - ux * half_l, cy - uy * half_l),
            (cx - vx * half_w * 0.78, cy - vy * half_w * 0.78),
        ),
        np.float32,
    )


def _point(
    center: tuple[float, float], theta: float, along_native: float, across_native: float, size: int,
) -> tuple[float, float]:
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    return (
        center[0] + ux * _work_px(along_native, size) + vx * _work_px(across_native, size),
        center[1] + uy * _work_px(along_native, size) + vy * _work_px(across_native, size),
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
    # SPB-105 tick #7: record the largest authored extent, not merely stroke
    # thickness, so the owner's complete 8-32px doctrine is auditable.
    counter[(family, round(max(float(value) for value in dimensions_native), 3))] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def build_pink_quench(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Pink Quench is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    shape = (size, size)
    masks = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    tones = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    geometry: Counter[tuple[str, float]] = Counter()

    # Jittered ceramic cells carry two-cell thermal domains. Direction changes
    # before a tiger stripe, ribbon, long crack, grid, or recoverable motif can
    # form, while neighboring splinters still share a credible quench history.
    cell = max(6, int(round(_work_px(30.0, size))))
    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + 0.5 * cell + (0.33 * cell if gy % 2 else 0.0) + rng.uniform(-0.48, 0.48) * cell)
            cy = float(y0 + 0.5 * cell + rng.uniform(-0.48, 0.48) * cell)
            domain_x, domain_y = gx // 2, gy // 2
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 13 - domain_y * 5) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.48 + (domain_hash % 31) / 30.0 * 2.96
            theta = float(domain_theta + rng.uniform(-0.50, 0.50))

            carrier_tier_index = int(rng.integers(0, len(EVENT_TIERS)))
            carrier_strength = float(EVENT_TIERS[carrier_tier_index])
            carrier_tone = _paint_tone(rng, carrier_tier_index)
            carrier_length = float(rng.uniform(13.0, 28.0))
            carrier_width = float(rng.uniform(8.0, 17.0))
            carrier_center = _point((cx, cy), theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.5, 3.5), size)
            carrier_points = _facet_points(
                carrier_center, carrier_length, carrier_width,
                theta + rng.uniform(-0.28, 0.28), size,
                rng.uniform(0.46, 0.86), rng.uniform(-0.18, 0.18),
            )
            _draw_pair(
                masks["black ceramic shock facets"], tones["black ceramic shock facets"],
                carrier_points, carrier_strength, carrier_tone,
            )
            _mark(geometry, "black ceramic shock facets", carrier_length, carrier_width)

            if rng.random() >= 0.76:
                continue

            tier_index = int(rng.integers(0, len(EVENT_TIERS)))
            strength = float(EVENT_TIERS[tier_index])
            paint_tone = _paint_tone(rng, tier_index)
            splinter_theta = float(theta + rng.uniform(-0.18, 0.18))
            splinter_length = float(rng.uniform(16.0, 31.5))
            splinter_width = float(rng.uniform(8.0, 12.5))
            splinter_center = _point(
                carrier_center, splinter_theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size,
            )
            splinter_points = _splinter_points(
                splinter_center, splinter_length, splinter_width, splinter_theta, size,
                rng.uniform(0.50, 0.90), rng.uniform(-0.20, 0.20),
            )
            _draw_pair(
                masks["magenta glass splinters"], tones["magenta glass splinters"],
                splinter_points, strength, paint_tone,
            )
            _mark(geometry, "magenta glass splinters", splinter_length, splinter_width)

            side = -1.0 if rng.random() < 0.5 else 1.0
            front = _point(splinter_center, splinter_theta, splinter_length * 0.43, side * splinter_width * 0.06, size)
            rear = _point(splinter_center, splinter_theta, -splinter_length * 0.42, -side * splinter_width * 0.10, size)

            if rng.random() < 0.52:
                shadow_length = float(rng.uniform(11.0, min(26.0, splinter_length)))
                shadow_width = float(rng.uniform(8.0, min(12.0, splinter_width)))
                shadow_center = _point(
                    splinter_center, splinter_theta, rng.uniform(-4.0, 5.0),
                    side * rng.uniform(6.0, 10.0), size,
                )
                shadow_points = _splinter_points(
                    shadow_center, shadow_length, shadow_width,
                    splinter_theta + rng.uniform(-0.13, 0.13), size,
                    rng.uniform(0.52, 0.86), rng.uniform(-0.18, 0.18),
                )
                shadow_tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                _draw_pair(
                    masks["violet cooling shadows"], tones["violet cooling shadows"],
                    shadow_points, float(EVENT_TIERS[shadow_tier_index]),
                    _paint_tone(rng, shadow_tier_index),
                )
                _mark(geometry, "violet cooling shadows", shadow_length, shadow_width)

            if rng.random() < 0.58:
                edge_index = int(rng.choice((0, 1, 3, 4)))
                p0 = tuple(splinter_points[edge_index])
                p1 = tuple(splinter_points[(edge_index + 1) % len(splinter_points)])
                edge_length = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)) * NATIVE / size)
                if edge_length >= 8.0:
                    lip_length = float(np.clip(edge_length, 8.0, 32.0))
                    lip_tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                    _line_pair(
                        masks["pale temper lips"], tones["pale temper lips"], p0, p1,
                        8.0, float(EVENT_TIERS[lip_tier_index]),
                        _paint_tone(rng, lip_tier_index), size,
                    )
                    _mark(geometry, "pale temper lips", lip_length, 8.0)

            # One primary consequence per shard prevents hearts, radial petals,
            # flower stamps, and repeated multi-arm quench glyphs.
            anatomy = float(rng.random())
            if anatomy < 0.12:
                pinpoint_length = float(rng.uniform(8.0, 10.5))
                pinpoint_width = float(rng.uniform(8.0, 10.0))
                pinpoint_anchor = front if rng.random() < 0.64 else rear
                pinpoint_center = _point(
                    pinpoint_anchor, splinter_theta, rng.uniform(-1.0, 2.0),
                    side * rng.uniform(-1.5, 2.0), size,
                )
                pinpoint_points = _nugget_points(
                    pinpoint_center, pinpoint_length, pinpoint_width,
                    splinter_theta + rng.uniform(-0.60, 0.60), size, rng.uniform(-0.18, 0.25),
                )
                _draw_pair(
                    masks["cyan stress pinpoints"], tones["cyan stress pinpoints"],
                    pinpoint_points, strength, paint_tone,
                )
                _mark(geometry, "cyan stress pinpoints", pinpoint_length, pinpoint_width)
            elif anatomy < 0.28:
                break_length = float(rng.uniform(8.0, 14.0))
                break_width = float(rng.uniform(8.0, 12.0))
                break_anchor = front if rng.random() < 0.46 else rear
                break_center = _point(
                    break_anchor, splinter_theta, rng.uniform(-1.5, 2.0),
                    side * rng.uniform(-2.0, 2.0), size,
                )
                break_points = _facet_points(
                    break_center, break_length, break_width,
                    splinter_theta + side * rng.uniform(0.48, 0.92), size,
                    rng.uniform(0.34, 0.64), rng.uniform(-0.24, 0.24),
                )
                _draw_pair(
                    masks["broken glass ends"], tones["broken glass ends"],
                    break_points, strength, paint_tone,
                )
                _mark(geometry, "broken glass ends", break_length, break_width)
            elif anatomy < 0.42:
                trunk_length = float(rng.uniform(10.0, 18.0))
                trunk_theta = splinter_theta + side * rng.uniform(0.48, 0.82)
                trunk_start = front if rng.random() < 0.54 else rear
                trunk_end = _point(trunk_start, trunk_theta, trunk_length, 0.0, size)
                branch_length = float(rng.uniform(8.0, 12.0))
                junction = _point(trunk_start, trunk_theta, trunk_length * rng.uniform(0.46, 0.68), 0.0, size)
                branch_theta = trunk_theta - side * rng.uniform(0.42, 0.70)
                branch_end = _point(junction, branch_theta, branch_length, 0.0, size)
                _line_pair(
                    masks["short branching checks"], tones["short branching checks"],
                    trunk_start, trunk_end, 8.0, strength, paint_tone, size,
                )
                _line_pair(
                    masks["short branching checks"], tones["short branching checks"],
                    junction, branch_end, 8.0, strength * 0.82, paint_tone * 0.88, size,
                )
                _mark(geometry, "short branching checks", trunk_length, 8.0)
                _mark(geometry, "short branching checks", branch_length, 8.0)
            elif anatomy < 0.54:
                bead_length = float(rng.uniform(8.0, 12.0))
                bead_width = float(rng.uniform(8.0, 11.0))
                bead_anchor = front if rng.random() < 0.55 else rear
                bead_center = _point(
                    bead_anchor, splinter_theta, rng.uniform(-1.0, 2.5),
                    side * rng.uniform(-1.5, 2.5), size,
                )
                bead_points = _nugget_points(
                    bead_center, bead_length, bead_width,
                    splinter_theta + rng.uniform(-0.70, 0.70), size, rng.uniform(-0.20, 0.30),
                )
                _draw_pair(
                    masks["quenched glass beads"], tones["quenched glass beads"],
                    bead_points, strength, paint_tone,
                )
                _mark(geometry, "quenched glass beads", bead_length, bead_width)
            elif anatomy < 0.70:
                crumb_count = 1 + int(rng.random() < 0.36)
                for crumb_index in range(crumb_count):
                    crumb_length = float(rng.uniform(8.0, 11.0))
                    crumb_width = float(rng.uniform(8.0, 10.0))
                    crumb_center = _point(
                        rear, splinter_theta,
                        -rng.uniform(2.0 + 4.0 * crumb_index, 5.0 + 5.0 * crumb_index),
                        side * rng.uniform(-3.0, 4.0), size,
                    )
                    crumb_points = _nugget_points(
                        crumb_center, crumb_length, crumb_width,
                        splinter_theta + rng.uniform(-0.65, 0.65), size, rng.uniform(-0.20, 0.26),
                    )
                    crumb_tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                    _draw_pair(
                        masks["oxide crumbs"], tones["oxide crumbs"], crumb_points,
                        float(EVENT_TIERS[crumb_tier_index]), _paint_tone(rng, crumb_tier_index),
                    )
                    _mark(geometry, "oxide crumbs", crumb_length, crumb_width)
            elif anatomy < 0.86:
                pit_length = float(rng.uniform(8.0, min(15.0, splinter_length)))
                pit_width = float(rng.uniform(8.0, min(11.5, splinter_width)))
                pit_center = _point(
                    splinter_center, splinter_theta, rng.uniform(-4.0, 4.0), rng.uniform(-2.0, 2.0), size,
                )
                pit_points = _nugget_points(
                    pit_center, pit_length, pit_width,
                    splinter_theta + rng.uniform(-0.35, 0.35), size, rng.uniform(-0.18, 0.26),
                )
                _draw_pair(
                    masks["dark quenched pits"], tones["dark quenched pits"],
                    pit_points, strength, paint_tone,
                )
                _mark(geometry, "dark quenched pits", pit_length, pit_width)

    ceramic = np.clip(masks["black ceramic shock facets"], 0.0, 1.0)
    glass = np.clip(masks["magenta glass splinters"], 0.0, 1.0)
    lips = np.clip(masks["pale temper lips"], 0.0, 1.0)
    shadows = np.clip(masks["violet cooling shadows"], 0.0, 1.0)
    pinpoints = np.clip(masks["cyan stress pinpoints"], 0.0, 1.0)
    broken = np.clip(masks["broken glass ends"], 0.0, 1.0)
    checks = np.clip(masks["short branching checks"], 0.0, 1.0)
    beads = np.clip(masks["quenched glass beads"], 0.0, 1.0)
    crumbs = np.clip(masks["oxide crumbs"], 0.0, 1.0)
    pits = np.clip(masks["dark quenched pits"], 0.0, 1.0)

    damage = np.maximum.reduce((broken, checks, crumbs, pits))
    intact_glass = np.clip(glass - 0.72 * np.maximum.reduce((broken, checks, pits)), 0.0, 1.0)
    metal_process = np.maximum.reduce((pinpoints, crumbs * 0.76, broken * 0.52, ceramic * 0.20))
    coat_process = np.maximum.reduce((intact_glass, lips, beads, shadows * 0.36))
    metal_reach = np.clip(_wrap_blur(metal_process, 5.0, size) * 1.65, 0.0, 1.0)
    damage_reach = np.clip(_wrap_blur(damage, 6.0, size) * 1.72, 0.0, 1.0)
    coat_reach = np.clip(_wrap_blur(coat_process, 6.5, size) * 1.58, 0.0, 1.0)
    glass_bed = np.clip(_wrap_blur(np.maximum(glass, shadows * 0.72), 7.5, size) * 1.56, 0.0, 1.0)
    carrier_pressure = np.clip(
        _wrap_blur(np.maximum.reduce((ceramic, glass, shadows, damage)), 11.0, size) * 1.74,
        0.0, 1.0,
    )
    px = cv2.Sobel(carrier_pressure, cv2.CV_32F, 1, 0, ksize=3)
    py = cv2.Sobel(carrier_pressure, cv2.CV_32F, 0, 1, ksize=3)
    strain = np.abs(px) + np.abs(py)
    strain /= max(float(np.percentile(strain, 99.0)), 1e-6)
    strain = np.clip(strain, 0.0, 1.0)

    # The black-ceramic relief and ruby heat bed derive only from the authored
    # quench masks. There is no generic grain, flame field, ribbon, or FBM.
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.028 + 0.045 * carrier_pressure + 0.065 * glass_bed + 0.016 * strain
    paint[..., 1] = 0.017 + 0.018 * carrier_pressure + 0.008 * glass_bed + 0.011 * strain
    paint[..., 2] = 0.038 + 0.052 * carrier_pressure + 0.060 * glass_bed + 0.023 * strain

    _blend(paint, ceramic, _ramp(tones["black ceramic shock facets"], (0.035, 0.022, 0.050), (0.180, 0.055, 0.150)), 0.86)
    _blend(paint, shadows, _ramp(tones["violet cooling shadows"], (0.050, 0.010, 0.090), (0.380, 0.055, 0.520)), 0.72)
    _blend(paint, glass, _ramp(tones["magenta glass splinters"], (0.110, 0.007, 0.070), (0.840, 0.030, 0.430)), 0.98)
    _blend(paint, lips, _ramp(tones["pale temper lips"], (0.170, 0.035, 0.120), (1.000, 0.650, 0.840)), 0.92)
    _blend(paint, broken, _ramp(tones["broken glass ends"], (0.012, 0.004, 0.014), (0.180, 0.020, 0.070)), 0.96)
    _blend(paint, checks, _ramp(tones["short branching checks"], (0.008, 0.012, 0.025), (0.070, 0.130, 0.190)), 0.94)
    _blend(paint, pits, _ramp(tones["dark quenched pits"], (0.005, 0.010, 0.016), (0.045, 0.145, 0.155)), 0.96)
    _blend(paint, crumbs, _ramp(tones["oxide crumbs"], (0.110, 0.012, 0.030), (0.820, 0.115, 0.055)), 0.96)
    _blend(paint, beads, _ramp(tones["quenched glass beads"], (0.190, 0.065, 0.145), (1.000, 0.770, 0.910)), 0.98)
    _blend(paint, pinpoints, _ramp(tones["cyan stress pinpoints"], (0.025, 0.120, 0.150), (0.380, 0.930, 1.000)), 1.00)
    # SPB-105 / Neon reset continuation / 2026-08-27 owner verdict: increase
    # visibility by exposure, never by enlarging the 8–32px glass anatomy.
    # Official isolated M7 moved from an initial 84.3 after this calibration;
    # the next workbook run records the final composite below.
    paint = np.clip(paint * 1.16, 0.0, 1.0)

    metal_score = (
        0.05 + 0.58 * metal_reach + 1.88 * pinpoints + 1.42 * crumbs
        + 0.76 * broken + 0.42 * ceramic - 0.92 * glass
        - 0.42 * lips - 0.34 * beads - 0.22 * shadows
    )
    rough_score = (
        0.10 + 0.58 * damage_reach + 1.54 * broken + 1.48 * checks
        + 1.30 * crumbs + 1.18 * pits + 0.52 * shadows
        - 0.86 * lips - 0.72 * beads - 0.30 * intact_glass
    )
    coat_score = (
        0.14 + 0.52 * coat_reach + 1.28 * intact_glass + 1.54 * lips
        + 1.42 * beads + 0.46 * shadows - 1.16 * broken
        - 1.08 * checks - 1.02 * pits - 0.62 * crumbs - 0.24 * pinpoints
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
            "M": "conductive ceramic exposure, cyan stress pinpoints, oxide crumbs, and broken substrate lead while glass stays low",
            "R": "broken ends, short checks, oxide crumbs, quenched pits, and cooling shadows rise independently",
            "Cc": "intact magenta glass, pale temper lips, and quenched beads retain clear; breaks, checks, and pits interrupt it",
        },
        carrier="black ceramic coating loaded with thermally quenched ruby fluorescent glass splinters",
        vetoes=(
            "flame, ribbon, tiger stripe, or long crack",
            "heart, flower, petal, or radial stamp",
            "floating confetti or generic flake recolor",
            "Blue Breakdown, Redline Shear, or Emberwake recolor",
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
    result = timed_result(build_pink_quench, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_pink_quench, seed)
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
    parser = argparse.ArgumentParser(description="Render isolated Pink Quench owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "pink_quench",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
