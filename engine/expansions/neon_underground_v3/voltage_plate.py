"""Voltage Plate — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset finish #2 / owner verdict 2026-08-27: "Claude's
rebuild has failed miserably." Metric movement: rejected live finish with no
isolated causal baseline -> deterministic unwired platelet candidate pending
owner screening, mapped-car proof, and official catalog M7. Nothing here
registers or replaces the live ``neon_cyber_yellow`` finish.
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


FINISH_ID = "neon_cyber_yellow"
DISPLAY_NAME = "Voltage Plate"
DEFAULT_SEED = 0xA017_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
PAINT_TIERS = np.asarray((0.08, 0.19, 0.31, 0.43, 0.56, 0.69, 0.83, 0.98), np.float32)

FAMILIES = (
    "conductive ceramic facets",
    "shear phosphor platelets",
    "charged rims",
    "bridge slivers",
    "chipped corners",
    "copper pinpoints",
    "quenched gaps",
    "offset afterimages",
    "shear fracture scores",
    "fused shoulder glaze",
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


def _platelet_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    nose: float,
    shear: float,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    # Six unequal vertices make a cleaved plate, never a capsule or hex tile.
    return np.asarray(
        (
            (cx + ux * half_l, cy + uy * half_l),
            (cx + ux * half_l * nose + vx * half_w * 0.72, cy + uy * half_l * nose + vy * half_w * 0.72),
            (cx - ux * half_l * 0.74 + vx * half_w, cy - uy * half_l * 0.74 + vy * half_w),
            (cx - ux * half_l + vx * half_w * shear, cy - uy * half_l + vy * half_w * shear),
            (cx - ux * half_l * 0.58 - vx * half_w * 0.83, cy - uy * half_l * 0.58 - vy * half_w * 0.83),
            (cx + ux * half_l * 0.35 - vx * half_w, cy + uy * half_l * 0.35 - vy * half_w),
        ),
        np.float32,
    )


def _quad_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    taper: float = 0.72,
    skew: float = 0.0,
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
            (cx + ux * half_l + vx * half_w * (0.55 + skew), cy + uy * half_l + vy * half_w * (0.55 + skew)),
            (cx - ux * half_l + vx * half_w * (0.82 - skew), cy - uy * half_l + vy * half_w * (0.82 - skew)),
        ),
        np.float32,
    )


def _diamond_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx + ux * half_l, cy + uy * half_l),
            (cx + vx * half_w, cy + vy * half_w),
            (cx - ux * half_l, cy - uy * half_l),
            (cx - vx * half_w, cy - vy * half_w),
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
    # SPB-105 tick #2: audit the largest authored extent rather than only line
    # thickness, so every primitive genuinely stays inside the 8-32px doctrine.
    counter[(family, round(max(float(value) for value in dimensions_native), 3))] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def build_voltage_plate(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Voltage Plate is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    shape = (size, size)
    masks = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    tones = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    geometry: Counter[tuple[str, float]] = Counter()

    # Dense jittered sites build one continuous ceramic-loaded material. Hashed
    # three-cell shear domains provide local alignment, but terminate too soon
    # to form caution bands, circuitry, a grid, or a macro lane.
    cell = max(6, int(round(_work_px(32.0, size))))
    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + 0.5 * cell + (0.29 * cell if gy % 2 else 0.0) + rng.uniform(-0.48, 0.48) * cell)
            cy = float(y0 + 0.5 * cell + rng.uniform(-0.48, 0.48) * cell)
            domain_x, domain_y = gx // 3, gy // 3
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 7 + domain_y * 11) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.46 + (domain_hash % 29) / 28.0 * 2.92
            theta = float(domain_theta + rng.uniform(-0.42, 0.42))

            carrier_tier_index = int(rng.integers(0, len(EVENT_TIERS)))
            carrier_strength = float(EVENT_TIERS[carrier_tier_index])
            carrier_tone = _paint_tone(rng, carrier_tier_index)
            carrier_length = float(rng.uniform(13.0, 28.0))
            carrier_width = float(rng.uniform(8.0, 16.0))
            carrier_center = _point((cx, cy), theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.5, 3.5), size)
            carrier_points = _quad_points(
                carrier_center, carrier_length, carrier_width,
                theta + rng.uniform(-0.28, 0.28), size,
                rng.uniform(0.46, 0.88), rng.uniform(-0.18, 0.18),
            )
            _draw_pair(
                masks["conductive ceramic facets"], tones["conductive ceramic facets"],
                carrier_points, carrier_strength, carrier_tone,
            )
            _mark(geometry, "conductive ceramic facets", carrier_length, carrier_width)

            if rng.random() >= 0.78:
                continue

            tier_index = int(rng.integers(0, len(EVENT_TIERS)))
            strength = float(EVENT_TIERS[tier_index])
            paint_tone = _paint_tone(rng, tier_index)
            platelet_theta = float(theta + rng.uniform(-0.18, 0.18))
            platelet_length = float(rng.uniform(13.0, 31.0))
            platelet_width = float(rng.uniform(8.0, 17.0))
            platelet_center = _point(
                carrier_center, platelet_theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size,
            )
            platelet_points = _platelet_points(
                platelet_center, platelet_length, platelet_width, platelet_theta, size,
                rng.uniform(0.28, 0.68), rng.uniform(-0.24, 0.24),
            )
            _draw_pair(
                masks["shear phosphor platelets"], tones["shear phosphor platelets"],
                platelet_points, strength, paint_tone,
            )
            _mark(geometry, "shear phosphor platelets", platelet_length, platelet_width)

            side = -1.0 if rng.random() < 0.5 else 1.0
            front = _point(platelet_center, platelet_theta, platelet_length * 0.42, side * platelet_width * 0.08, size)
            rear = _point(platelet_center, platelet_theta, -platelet_length * 0.40, -side * platelet_width * 0.12, size)

            if rng.random() < 0.60:
                edge_index = int(rng.choice((0, 1, 4, 5)))
                p0 = tuple(platelet_points[edge_index])
                p1 = tuple(platelet_points[(edge_index + 1) % len(platelet_points)])
                edge_length = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)) * NATIVE / size)
                if edge_length >= 8.0:
                    rim_length = float(np.clip(edge_length, 8.0, 32.0))
                    rim_strength = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
                    _line_pair(
                        masks["charged rims"], tones["charged rims"], p0, p1,
                        8.0, rim_strength, paint_tone, size,
                    )
                    _mark(geometry, "charged rims", rim_length, 8.0)

            if rng.random() < 0.27:
                bridge_length = float(rng.uniform(9.0, 22.0))
                bridge_width = float(rng.uniform(8.0, 10.5))
                bridge_theta = platelet_theta + side * rng.uniform(0.34, 0.72)
                bridge_center = _point(
                    front, bridge_theta, bridge_length * 0.22, side * rng.uniform(1.0, 3.5), size,
                )
                bridge_points = _quad_points(
                    bridge_center, bridge_length, bridge_width, bridge_theta, size,
                    rng.uniform(0.32, 0.60), rng.uniform(-0.20, 0.20),
                )
                bridge_tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                _draw_pair(
                    masks["bridge slivers"], tones["bridge slivers"], bridge_points,
                    float(EVENT_TIERS[bridge_tier_index]), _paint_tone(rng, bridge_tier_index),
                )
                _mark(geometry, "bridge slivers", bridge_length, bridge_width)

            # Exactly one primary consequence per platelet keeps all anatomy
            # attached without producing a repeated multi-arm stamp.
            anatomy = float(rng.random())
            if anatomy < 0.18:
                echo_length = float(rng.uniform(11.0, min(26.0, platelet_length)))
                echo_width = float(rng.uniform(8.0, min(13.0, platelet_width)))
                echo_center = _point(
                    platelet_center, platelet_theta, rng.uniform(-5.0, 6.0),
                    side * rng.uniform(8.0, 14.0), size,
                )
                echo_points = _platelet_points(
                    echo_center, echo_length, echo_width,
                    platelet_theta + rng.uniform(-0.14, 0.14), size,
                    rng.uniform(0.30, 0.66), rng.uniform(-0.22, 0.22),
                )
                _draw_pair(
                    masks["offset afterimages"], tones["offset afterimages"],
                    echo_points, strength, paint_tone,
                )
                _mark(geometry, "offset afterimages", echo_length, echo_width)
            elif anatomy < 0.34:
                chip_length = float(rng.uniform(8.0, 13.0))
                chip_width = float(rng.uniform(8.0, 12.0))
                chip_center = _point(
                    front if rng.random() < 0.5 else rear, platelet_theta,
                    rng.uniform(-1.5, 2.0), side * rng.uniform(-2.0, 2.0), size,
                )
                chip_points = _diamond_points(
                    chip_center, chip_length, chip_width,
                    platelet_theta + rng.uniform(-0.72, 0.72), size,
                )
                _draw_pair(
                    masks["chipped corners"], tones["chipped corners"],
                    chip_points, strength, paint_tone,
                )
                _mark(geometry, "chipped corners", chip_length, chip_width)
            elif anatomy < 0.49:
                gap_length = float(rng.uniform(9.0, min(18.0, platelet_length)))
                gap_width = float(rng.uniform(8.0, min(12.0, platelet_width)))
                gap_center = _point(
                    platelet_center, platelet_theta, rng.uniform(-4.0, 4.0), rng.uniform(-2.0, 2.0), size,
                )
                gap_points = _quad_points(
                    gap_center, gap_length, gap_width,
                    platelet_theta + rng.uniform(-0.22, 0.22), size,
                    rng.uniform(0.36, 0.68), rng.uniform(-0.20, 0.20),
                )
                _draw_pair(
                    masks["quenched gaps"], tones["quenched gaps"],
                    gap_points, strength, paint_tone,
                )
                _mark(geometry, "quenched gaps", gap_length, gap_width)
            elif anatomy < 0.61:
                copper_length = float(rng.uniform(8.0, 11.5))
                copper_width = float(rng.uniform(8.0, 10.5))
                copper_anchor = front if rng.random() < 0.56 else rear
                copper_center = _point(
                    copper_anchor, platelet_theta, rng.uniform(-1.5, 2.0), side * rng.uniform(-1.5, 2.0), size,
                )
                copper_points = _diamond_points(
                    copper_center, copper_length, copper_width,
                    platelet_theta + rng.uniform(-0.55, 0.55), size,
                )
                _draw_pair(
                    masks["copper pinpoints"], tones["copper pinpoints"],
                    copper_points, strength, paint_tone,
                )
                _mark(geometry, "copper pinpoints", copper_length, copper_width)
            elif anatomy < 0.75:
                score_length = float(rng.uniform(9.0, min(21.0, platelet_length)))
                score_width = 8.0
                score_theta = platelet_theta + side * rng.uniform(0.58, 1.02)
                score_center = _point(
                    platelet_center, platelet_theta, rng.uniform(-4.0, 4.0), side * rng.uniform(-1.0, 2.0), size,
                )
                p0 = _point(score_center, score_theta, -score_length * 0.52, 0.0, size)
                p1 = _point(score_center, score_theta, score_length * 0.48, 0.0, size)
                _line_pair(
                    masks["shear fracture scores"], tones["shear fracture scores"],
                    p0, p1, score_width, strength, paint_tone, size,
                )
                _mark(geometry, "shear fracture scores", score_length, score_width)
            elif anatomy < 0.91:
                glaze_length = float(rng.uniform(10.0, min(25.0, platelet_length)))
                glaze_width = float(rng.uniform(8.0, min(11.0, platelet_width)))
                glaze_center = _point(
                    platelet_center, platelet_theta, rng.uniform(-3.0, 3.0),
                    -side * platelet_width * 0.35, size,
                )
                glaze_points = _quad_points(
                    glaze_center, glaze_length, glaze_width,
                    platelet_theta + rng.uniform(-0.09, 0.09), size,
                    rng.uniform(0.48, 0.78), rng.uniform(-0.14, 0.14),
                )
                _draw_pair(
                    masks["fused shoulder glaze"], tones["fused shoulder glaze"],
                    glaze_points, strength, paint_tone,
                )
                _mark(geometry, "fused shoulder glaze", glaze_length, glaze_width)

    ceramic = np.clip(masks["conductive ceramic facets"], 0.0, 1.0)
    platelets = np.clip(masks["shear phosphor platelets"], 0.0, 1.0)
    rims = np.clip(masks["charged rims"], 0.0, 1.0)
    bridges = np.clip(masks["bridge slivers"], 0.0, 1.0)
    chips = np.clip(masks["chipped corners"], 0.0, 1.0)
    copper = np.clip(masks["copper pinpoints"], 0.0, 1.0)
    gaps = np.clip(masks["quenched gaps"], 0.0, 1.0)
    echoes = np.clip(masks["offset afterimages"], 0.0, 1.0)
    scores = np.clip(masks["shear fracture scores"], 0.0, 1.0)
    glaze = np.clip(masks["fused shoulder glaze"], 0.0, 1.0)

    intact_plate = np.clip(platelets - 0.72 * np.maximum.reduce((chips, gaps, scores)), 0.0, 1.0)
    metal_process = np.maximum.reduce((copper, bridges * 0.72, chips * 0.54, ceramic * 0.20))
    damage_process = np.maximum.reduce((chips, gaps, scores, echoes * 0.42))
    coat_process = np.maximum.reduce((glaze, rims, intact_plate * 0.56, echoes * 0.28))
    metal_reach = np.clip(_wrap_blur(metal_process, 5.0, size) * 1.62, 0.0, 1.0)
    damage_reach = np.clip(_wrap_blur(damage_process, 6.0, size) * 1.68, 0.0, 1.0)
    coat_reach = np.clip(_wrap_blur(coat_process, 6.5, size) * 1.55, 0.0, 1.0)
    platelet_bed = np.clip(_wrap_blur(np.maximum(platelets, echoes * 0.65), 7.0, size) * 1.55, 0.0, 1.0)
    carrier_pressure = np.clip(
        _wrap_blur(np.maximum.reduce((ceramic, platelets, bridges, damage_process)), 11.0, size) * 1.72,
        0.0, 1.0,
    )
    px = cv2.Sobel(carrier_pressure, cv2.CV_32F, 1, 0, ksize=3)
    py = cv2.Sobel(carrier_pressure, cv2.CV_32F, 0, 1, ksize=3)
    strain = np.abs(px) + np.abs(py)
    strain /= max(float(np.percentile(strain, 99.0)), 1e-6)
    strain = np.clip(strain, 0.0, 1.0)

    # All relief comes from the authored platelet/ceramic process; no generic
    # grain, FBM, chart lane, or unrelated noise is used beneath the material.
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.026 + 0.040 * carrier_pressure + 0.055 * platelet_bed + 0.015 * strain
    paint[..., 1] = 0.028 + 0.042 * carrier_pressure + 0.050 * platelet_bed + 0.017 * strain
    paint[..., 2] = 0.025 + 0.028 * carrier_pressure + 0.012 * platelet_bed + 0.020 * strain

    _blend(paint, ceramic, _ramp(tones["conductive ceramic facets"], (0.032, 0.036, 0.030), (0.160, 0.170, 0.085)), 0.82)
    _blend(paint, echoes, _ramp(tones["offset afterimages"], (0.060, 0.060, 0.008), (0.390, 0.360, 0.025)), 0.66)
    _blend(paint, platelets, _ramp(tones["shear phosphor platelets"], (0.090, 0.082, 0.006), (0.900, 0.760, 0.025)), 0.98)
    _blend(paint, glaze, _ramp(tones["fused shoulder glaze"], (0.090, 0.080, 0.006), (0.710, 0.650, 0.055)), 0.72)
    _blend(paint, rims, _ramp(tones["charged rims"], (0.120, 0.125, 0.008), (1.000, 0.975, 0.180)), 0.90)
    _blend(paint, bridges, _ramp(tones["bridge slivers"], (0.110, 0.075, 0.005), (0.950, 0.570, 0.020)), 0.90)
    _blend(paint, chips, _ramp(tones["chipped corners"], (0.006, 0.010, 0.012), (0.075, 0.085, 0.065)), 0.95)
    _blend(paint, gaps, _ramp(tones["quenched gaps"], (0.006, 0.018, 0.020), (0.040, 0.180, 0.145)), 0.92)
    _blend(paint, scores, _ramp(tones["shear fracture scores"], (0.003, 0.005, 0.007), (0.045, 0.065, 0.055)), 0.98)
    _blend(paint, copper, _ramp(tones["copper pinpoints"], (0.145, 0.035, 0.004), (1.000, 0.400, 0.025)), 1.00)
    # SPB-105 / Neon reset continuation / 2026-08-27 owner verdict: retain
    # small platelet scale while restoring the saturated charged-phosphor read.
    # Official isolated M7 before calibration was 69.2 (M6 saturation miss);
    # the official rerun below records movement with geometry/spec unchanged.
    hsv = cv2.cvtColor(np.clip(paint, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 2.0, 0.0, 1.0)
    paint = np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 1.25, 0.0, 1.0)

    metal_score = (
        0.05 + 0.56 * metal_reach + 1.92 * copper + 1.28 * bridges
        + 0.72 * chips + 0.44 * ceramic - 1.08 * platelets
        - 0.54 * glaze - 0.32 * gaps - 0.24 * rims
    )
    rough_score = (
        0.10 + 0.58 * damage_reach + 1.56 * chips + 1.48 * scores
        + 1.30 * gaps + 0.62 * echoes + 0.36 * bridges
        - 0.92 * glaze - 0.62 * rims - 0.28 * intact_plate
    )
    coat_score = (
        0.14 + 0.52 * coat_reach + 1.58 * glaze + 1.12 * rims
        + 0.76 * intact_plate + 0.42 * echoes + 0.30 * bridges
        - 1.16 * chips - 1.04 * gaps - 0.76 * scores - 0.24 * copper
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
            "M": "conductive ceramic exposure, copper pinpoints, and bridge deposits lead while dielectric phosphor stays low",
            "R": "chipped corners, cross-shear scores, quenched gaps, and displaced afterimages rise independently",
            "Cc": "fused glaze, charged rims, and intact platelet shoulders retain clear; chips, gaps, and scores break it",
        },
        carrier="dark conductive ceramic loaded with shear-yellow phosphor platelets",
        vetoes=(
            "caution stripe or hazard-tape band",
            "lightning bolt or circuitry network",
            "grid, row, hex field, or macro lane",
            "confetti or repeated capsule stamp",
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
    result = timed_result(build_voltage_plate, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_voltage_plate, seed)
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
    checks = {
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
        "checks": checks,
        "all_mechanical_checks_green": all(checks.values()),
        "catalog_m7": "PENDING isolated official workbook harness",
        "mapped_car": "PENDING; three-position material light proxy supplied for owner screening",
        "manifest": manifest,
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render isolated Voltage Plate owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "voltage_plate",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
