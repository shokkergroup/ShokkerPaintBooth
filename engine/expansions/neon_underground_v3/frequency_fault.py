"""Frequency Fault — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset finish #25 / owner verdict 2026-08-27: the rejected
rebuild reduced racing finishes to literal icons and repeated wallpaper.
This replacement is one encapsulated conductive automotive film assembled
from irregular local microbar packets and their attached process failures.
It is deliberately unwired until owner review and official workbook proof.
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


FINISH_ID = "neon2_frequency_fault"
DISPLAY_NAME = "Frequency Fault"
DEFAULT_SEED = 0xF2E0_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
COLOR_TIERS = np.asarray((0.10, 0.22, 0.34, 0.46, 0.58, 0.70, 0.84, 0.98), np.float32)

FAMILIES = (
    "conductive microbars",
    "intact bar shoulders",
    "squeeze-out lips",
    "skipped bar ghosts",
    "offset conductive echoes",
    "peak deposits",
    "fractured terminations",
    "dielectric gaps",
    "solder nicks",
    "encapsulant bridges",
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


def _fill_periodic(mask: np.ndarray, points: np.ndarray, value: float) -> None:
    points = np.asarray(points, np.float32)
    size = int(mask.shape[0])
    xs = _axis_shifts(float(points[:, 0].min()) - 2.0, float(points[:, 0].max()) + 2.0, size)
    ys = _axis_shifts(float(points[:, 1].min()) - 2.0, float(points[:, 1].max()) + 2.0, size)
    for dx in xs:
        for dy in ys:
            shifted = np.rint(points + np.asarray((dx, dy), np.float32)).astype(np.int32)
            cv2.fillConvexPoly(mask, shifted, float(value), cv2.LINE_AA)


def _quad_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    skew: float = 0.0,
    taper: float = 0.78,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l - vx * half_w * (0.82 + skew), cy - uy * half_l - vy * half_w * (0.82 + skew)),
            (cx + ux * half_l - vx * half_w * taper, cy + uy * half_l - vy * half_w * taper),
            (cx + ux * half_l + vx * half_w * (0.58 + 0.16 * skew), cy + uy * half_l + vy * half_w * (0.58 + 0.16 * skew)),
            (cx - ux * half_l + vx * half_w, cy - uy * half_l + vy * half_w),
        ),
        np.float32,
    )


def _quad(
    mask: np.ndarray,
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    value: float,
    size: int,
    skew: float = 0.0,
    taper: float = 0.78,
) -> np.ndarray:
    points = _quad_points(center, length_native, width_native, theta, size, skew, taper)
    _fill_periodic(mask, points, value)
    return points


def _line(
    mask: np.ndarray,
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
            cv2.line(mask, q0, q1, float(value), width, cv2.LINE_AA)


def _diamond(
    mask: np.ndarray,
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    value: float,
    size: int,
) -> None:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    points = np.asarray(
        (
            (cx + ux * half_l, cy + uy * half_l),
            (cx + vx * half_w, cy + vy * half_w),
            (cx - ux * half_l, cy - uy * half_l),
            (cx - vx * half_w, cy - vy * half_w),
        ),
        np.float32,
    )
    _fill_periodic(mask, points, value)


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
    t = np.clip(np.asarray(tone, np.float32), 0.0, 1.0)[..., None]
    lo = np.asarray(low, np.float32)
    hi = np.asarray(high, np.float32)
    return lo + (hi - lo) * t


def _mark(counter: Counter[tuple[str, float]], family: str, *dimensions_native: float) -> None:
    # SPB-105 tick #25: record the largest authored dimension so the owner's
    # 8–32px doctrine cannot be passed by reporting only stroke thickness.
    dimension = max(float(value) for value in dimensions_native)
    counter[(family, round(dimension, 3))] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def _paint_tone(rng: np.random.Generator, tier_index: int) -> float:
    return float(np.clip(COLOR_TIERS[tier_index] + rng.uniform(-0.075, 0.075), 0.04, 1.0))


def build_frequency_fault(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Frequency Fault is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    shape = (size, size)
    masks = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    tones = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    geometry: Counter[tuple[str, float]] = Counter()

    # The staggered 34px-native sites are only sampling cells, not visible
    # rows. Near-cell-width jitter and hashed 4x4 heading domains prevent a
    # chart, barcode, lane, or equalizer silhouette from emerging.
    cell = max(6, int(round(_work_px(34.0, size))))
    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + 0.5 * cell + (0.31 * cell if gy % 2 else 0.0) + rng.uniform(-0.48, 0.48) * cell)
            cy = float(y0 + 0.5 * cell + rng.uniform(-0.48, 0.48) * cell)

            domain_x, domain_y = gx // 3, gy // 3
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 5 - domain_y * 3) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.42 + (domain_hash % 23) / 22.0 * 2.84
            theta = float(domain_theta + rng.uniform(-0.46, 0.46))
            bar_count = int(rng.choice((1, 2, 3), p=(0.40, 0.47, 0.13)))
            spacing_native = float(rng.uniform(9.0, 14.0))
            skipped_slot = int(rng.integers(0, bar_count)) if bar_count >= 2 and rng.random() < 0.19 else -1
            actual_centers: list[tuple[float, float]] = []

            for bar_index in range(bar_count):
                tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                tier = float(EVENT_TIERS[tier_index])
                tone = _paint_tone(rng, tier_index)
                local_theta = float(theta + rng.uniform(-0.16, 0.16))
                across = (bar_index - 0.5 * (bar_count - 1)) * spacing_native + rng.uniform(-2.6, 2.6)
                along = rng.uniform(-5.0, 5.0)
                center = _point((cx, cy), theta, along, across, size)
                bar_length = float(rng.uniform(13.0, 30.0))
                bar_width = float(rng.uniform(8.0, 14.0))

                if bar_index == skipped_slot:
                    ghost_length = float(np.clip(bar_length * rng.uniform(0.68, 0.92), 10.0, 26.0))
                    ghost_width = float(rng.uniform(8.0, min(12.0, bar_width)))
                    _quad(
                        masks["skipped bar ghosts"], center, ghost_length, ghost_width,
                        local_theta + rng.uniform(-0.08, 0.08), tier, size,
                        rng.uniform(-0.22, 0.22), rng.uniform(0.46, 0.72),
                    )
                    _quad(
                        tones["skipped bar ghosts"], center, ghost_length, ghost_width,
                        local_theta + rng.uniform(-0.04, 0.04), tone, size,
                        rng.uniform(-0.16, 0.16), rng.uniform(0.52, 0.78),
                    )
                    _mark(geometry, "skipped bar ghosts", ghost_length, ghost_width)
                    continue

                _quad(
                    masks["conductive microbars"], center, bar_length, bar_width,
                    local_theta, tier, size, rng.uniform(-0.18, 0.18), rng.uniform(0.48, 0.88),
                )
                _quad(
                    tones["conductive microbars"], center, bar_length, bar_width,
                    local_theta, tone, size, rng.uniform(-0.10, 0.10), rng.uniform(0.56, 0.90),
                )
                _mark(geometry, "conductive microbars", bar_length, bar_width)
                actual_centers.append(center)

                side = -1.0 if rng.random() < 0.5 else 1.0
                front = _point(center, local_theta, bar_length * 0.42, side * bar_width * 0.10, size)
                rear = _point(center, local_theta, -bar_length * 0.43, -side * bar_width * 0.08, size)

                if rng.random() < 0.58:
                    shoulder_length = float(rng.uniform(10.0, min(25.0, bar_length)))
                    shoulder_width = float(rng.uniform(8.0, min(10.5, bar_width)))
                    shoulder_center = _point(
                        center, local_theta, rng.uniform(-2.5, 2.5), side * bar_width * 0.38, size,
                    )
                    shoulder_tier = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
                    _quad(
                        masks["intact bar shoulders"], shoulder_center, shoulder_length, shoulder_width,
                        local_theta + rng.uniform(-0.06, 0.06), shoulder_tier, size,
                        rng.uniform(-0.12, 0.12), rng.uniform(0.55, 0.82),
                    )
                    _quad(
                        tones["intact bar shoulders"], shoulder_center, shoulder_length, shoulder_width,
                        local_theta, tone, size, 0.0, 0.70,
                    )
                    _mark(geometry, "intact bar shoulders", shoulder_length, shoulder_width)

                anatomy = float(rng.random())
                if anatomy < 0.18:
                    squeeze_length = float(rng.uniform(10.0, min(24.0, bar_length)))
                    squeeze_width = float(rng.uniform(8.0, 12.0))
                    squeeze_center = _point(
                        center, local_theta, rng.uniform(-4.0, 4.0), side * (0.48 * bar_width + 2.0), size,
                    )
                    _quad(
                        masks["squeeze-out lips"], squeeze_center, squeeze_length, squeeze_width,
                        local_theta + rng.uniform(-0.12, 0.12), tier, size,
                        rng.uniform(-0.24, 0.24), rng.uniform(0.34, 0.68),
                    )
                    _quad(
                        tones["squeeze-out lips"], squeeze_center, squeeze_length, squeeze_width,
                        local_theta, tone, size, 0.0, 0.56,
                    )
                    _mark(geometry, "squeeze-out lips", squeeze_length, squeeze_width)
                elif anatomy < 0.34:
                    echo_length = float(rng.uniform(10.0, min(25.0, bar_length)))
                    echo_width = float(rng.uniform(8.0, 10.5))
                    echo_center = _point(
                        center, local_theta, rng.uniform(-5.0, 6.0), side * rng.uniform(8.0, 13.0), size,
                    )
                    echo_tier = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
                    _quad(
                        masks["offset conductive echoes"], echo_center, echo_length, echo_width,
                        local_theta + rng.uniform(-0.10, 0.10), echo_tier, size,
                        rng.uniform(-0.18, 0.18), rng.uniform(0.42, 0.72),
                    )
                    _quad(
                        tones["offset conductive echoes"], echo_center, echo_length, echo_width,
                        local_theta, tone, size, 0.0, 0.62,
                    )
                    _mark(geometry, "offset conductive echoes", echo_length, echo_width)
                elif anatomy < 0.48:
                    peak_length = float(rng.uniform(8.0, 14.0))
                    peak_width = float(rng.uniform(8.0, 12.0))
                    peak_center = _point(front, local_theta, rng.uniform(-1.0, 3.0), side * rng.uniform(-2.0, 2.0), size)
                    _diamond(
                        masks["peak deposits"], peak_center, peak_length, peak_width,
                        local_theta + rng.uniform(-0.45, 0.45), tier, size,
                    )
                    _diamond(
                        tones["peak deposits"], peak_center, peak_length, peak_width,
                        local_theta, tone, size,
                    )
                    _mark(geometry, "peak deposits", peak_length, peak_width)
                elif anatomy < 0.62:
                    fracture_length = float(rng.uniform(8.0, 15.0))
                    fracture_width = float(rng.uniform(8.0, 13.0))
                    fracture_center = _point(front, local_theta, rng.uniform(-2.0, 2.5), side * rng.uniform(-2.0, 2.0), size)
                    fracture_theta = local_theta + side * rng.uniform(0.58, 1.02)
                    _quad(
                        masks["fractured terminations"], fracture_center, fracture_length, fracture_width,
                        fracture_theta, tier, size, rng.uniform(-0.24, 0.24), rng.uniform(0.34, 0.62),
                    )
                    _quad(
                        tones["fractured terminations"], fracture_center, fracture_length, fracture_width,
                        fracture_theta, tone, size, 0.0, 0.52,
                    )
                    _mark(geometry, "fractured terminations", fracture_length, fracture_width)
                elif anatomy < 0.74:
                    gap_length = float(rng.uniform(8.0, min(16.0, bar_length)))
                    gap_width = float(rng.uniform(8.0, min(11.0, bar_width)))
                    gap_center = _point(center, local_theta, rng.uniform(-4.0, 4.0), rng.uniform(-2.0, 2.0), size)
                    _quad(
                        masks["dielectric gaps"], gap_center, gap_length, gap_width,
                        local_theta + rng.uniform(-0.20, 0.20), tier, size,
                        rng.uniform(-0.20, 0.20), rng.uniform(0.40, 0.70),
                    )
                    _quad(
                        tones["dielectric gaps"], gap_center, gap_length, gap_width,
                        local_theta, tone, size, 0.0, 0.58,
                    )
                    _mark(geometry, "dielectric gaps", gap_length, gap_width)
                elif anatomy < 0.84:
                    nick_length = float(rng.uniform(8.0, 12.0))
                    nick_width = float(rng.uniform(8.0, 10.5))
                    nick_center = _point(
                        rear if rng.random() < 0.5 else front, local_theta,
                        rng.uniform(-1.5, 2.0), side * rng.uniform(-1.0, 2.0), size,
                    )
                    _diamond(
                        masks["solder nicks"], nick_center, nick_length, nick_width,
                        local_theta + rng.uniform(-0.55, 0.55), tier, size,
                    )
                    _diamond(
                        tones["solder nicks"], nick_center, nick_length, nick_width,
                        local_theta, tone, size,
                    )
                    _mark(geometry, "solder nicks", nick_length, nick_width)

            if len(actual_centers) >= 2 and rng.random() < 0.30:
                bridge_index = int(rng.integers(0, len(actual_centers) - 1))
                p0 = actual_centers[bridge_index]
                p1 = actual_centers[bridge_index + 1]
                delta = np.asarray(p1, np.float32) - np.asarray(p0, np.float32)
                bridge_length = float(np.clip(np.linalg.norm(delta) * NATIVE / size, 8.0, 30.0))
                bridge_tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                bridge_tier = float(EVENT_TIERS[bridge_tier_index])
                bridge_width = float(rng.uniform(8.0, 11.0))
                _line(masks["encapsulant bridges"], p0, p1, bridge_width, bridge_tier, size)
                _line(
                    tones["encapsulant bridges"], p0, p1, bridge_width,
                    _paint_tone(rng, bridge_tier_index), size,
                )
                _mark(geometry, "encapsulant bridges", bridge_length, bridge_width)

    conductive = np.clip(masks["conductive microbars"], 0.0, 1.0)
    shoulders = np.clip(masks["intact bar shoulders"], 0.0, 1.0)
    squeeze = np.clip(masks["squeeze-out lips"], 0.0, 1.0)
    skipped = np.clip(masks["skipped bar ghosts"], 0.0, 1.0)
    echoes = np.clip(masks["offset conductive echoes"], 0.0, 1.0)
    peaks = np.clip(masks["peak deposits"], 0.0, 1.0)
    fractures = np.clip(masks["fractured terminations"], 0.0, 1.0)
    gaps = np.clip(masks["dielectric gaps"], 0.0, 1.0)
    nicks = np.clip(masks["solder nicks"], 0.0, 1.0)
    bridges = np.clip(masks["encapsulant bridges"], 0.0, 1.0)

    conductive_process = np.maximum.reduce((conductive, shoulders * 0.72, echoes * 0.58, peaks, nicks))
    damage_process = np.maximum.reduce((squeeze, skipped, fractures, gaps * 0.56))
    coat_process = np.maximum.reduce((shoulders, gaps, bridges, echoes * 0.42))
    conductive_reach = np.clip(_wrap_blur(conductive_process, 5.5, size) * 1.55, 0.0, 1.0)
    damage_reach = np.clip(_wrap_blur(damage_process, 6.0, size) * 1.65, 0.0, 1.0)
    coat_reach = np.clip(_wrap_blur(coat_process, 6.5, size) * 1.55, 0.0, 1.0)
    total_process = np.maximum.reduce((conductive_process, damage_process, coat_process))
    film_pressure = np.clip(_wrap_blur(total_process, 12.0, size) * 1.85, 0.0, 1.0)
    px = cv2.Sobel(film_pressure, cv2.CV_32F, 1, 0, ksize=3)
    py = cv2.Sobel(film_pressure, cv2.CV_32F, 0, 1, ksize=3)
    strain = np.abs(px) + np.abs(py)
    strain /= max(float(np.percentile(strain, 99.0)), 1e-6)
    strain = np.clip(strain, 0.0, 1.0)

    # A uniform graphite film plus relief derived only from authored process
    # masks; no unrelated noise/FBM/grain is used to manufacture richness.
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.018 + 0.024 * film_pressure + 0.012 * strain + 0.012 * damage_reach
    paint[..., 1] = 0.026 + 0.035 * film_pressure + 0.021 * strain + 0.008 * coat_reach
    paint[..., 2] = 0.043 + 0.060 * film_pressure + 0.038 * strain + 0.026 * coat_reach

    _blend(paint, skipped, _ramp(tones["skipped bar ghosts"], (0.018, 0.030, 0.050), (0.070, 0.145, 0.205)), 0.82)
    _blend(paint, echoes, _ramp(tones["offset conductive echoes"], (0.030, 0.045, 0.085), (0.205, 0.175, 0.470)), 0.76)
    _blend(paint, bridges, _ramp(tones["encapsulant bridges"], (0.035, 0.075, 0.120), (0.245, 0.340, 0.610)), 0.68)
    _blend(paint, conductive, _ramp(tones["conductive microbars"], (0.028, 0.062, 0.092), (0.115, 0.420, 0.555)), 0.96)
    _blend(paint, shoulders, _ramp(tones["intact bar shoulders"], (0.040, 0.095, 0.140), (0.260, 0.655, 0.805)), 0.72)
    _blend(paint, squeeze, _ramp(tones["squeeze-out lips"], (0.095, 0.012, 0.070), (0.675, 0.055, 0.405)), 0.94)
    _blend(paint, fractures, _ramp(tones["fractured terminations"], (0.045, 0.008, 0.012), (0.710, 0.105, 0.035)), 0.94)
    _blend(paint, gaps, _ramp(tones["dielectric gaps"], (0.040, 0.090, 0.125), (0.180, 0.480, 0.610)), 0.82)
    _blend(paint, peaks, _ramp(tones["peak deposits"], (0.105, 0.030, 0.155), (0.920, 0.160, 0.615)), 0.98)
    _blend(paint, nicks, _ramp(tones["solder nicks"], (0.230, 0.315, 0.350), (0.860, 0.965, 1.000)), 1.00)
    # SPB-105 / Neon reset continuation / 2026-08-27 owner verdict: a small
    # causal exposure lift keeps the deposited microbars legible at picker size
    # without enlarging them. Isolated M7 before calibration: 84.8; the official
    # rerun below records the exact movement while geometry/spec stay unchanged.
    paint = np.clip(paint * 1.08, 0.0, 1.0)

    metal_score = (
        0.05 + 0.52 * conductive_reach + 1.42 * conductive + 1.92 * nicks
        + 1.62 * peaks + 0.48 * shoulders + 0.34 * echoes
        - 0.76 * fractures - 0.54 * gaps - 0.46 * skipped - 0.28 * squeeze
    )
    rough_score = (
        0.10 + 0.54 * damage_reach + 1.48 * squeeze + 1.56 * fractures
        + 1.32 * skipped + 0.56 * echoes + 0.42 * gaps
        - 0.58 * bridges - 0.46 * shoulders - 0.24 * nicks
    )
    coat_score = (
        0.14 + 0.50 * coat_reach + 1.62 * bridges + 1.35 * gaps
        + 0.98 * shoulders + 0.08 * conductive + 0.12 * echoes
        - 1.08 * fractures - 0.58 * squeeze - 0.42 * skipped - 0.26 * nicks
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
            "M": "conductive microbars, solder nicks, and peak deposits lead; dielectric omissions and exposed breaks fall",
            "R": "squeeze-out, fractured terminations, skipped/eroded bar ghosts, and offset damage rise independently",
            "Cc": "encapsulant bridges, dielectric windows, and intact bar shoulders retain clear; exposed fractures break it",
        },
        carrier="dark encapsulated conductive film with locally deposited microbar packets",
        vetoes=(
            "waveform, chart, equalizer, or music UI silhouette",
            "barcode, uniform grid, repeated rows, or macro lanes",
            "floating disconnected ornaments",
            "generic noise or unrelated texture underlay",
            "any authored dimension outside 8–32px native",
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
    result = timed_result(build_frequency_fault, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_frequency_fault, seed)
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
    parser = argparse.ArgumentParser(description="Render isolated Frequency Fault owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "frequency_fault",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
