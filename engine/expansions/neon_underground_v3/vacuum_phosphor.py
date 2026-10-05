"""Vacuum Phosphor — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset finish #8 / owner verdict 2026-08-27: "Claude's
rebuild has failed miserably." Metric movement: rejected live finish with no
isolated causal baseline -> deterministic unwired evacuated-glass/phosphor
pilot pending owner review, mapped-car proof, and official catalog M7. This
module does not register or replace the live ``neon2_sign_tubes`` finish.
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


FINISH_ID = "neon2_sign_tubes"
DISPLAY_NAME = "Vacuum Phosphor"
DEFAULT_SEED = 0x7AC0_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
PAINT_TIERS = np.asarray((0.08, 0.19, 0.31, 0.43, 0.56, 0.69, 0.83, 0.98), np.float32)

FAMILIES = (
    "black evacuated wall facets",
    "fractured glass-wall slivers",
    "white-blue excitation lips",
    "cyan phosphor deposits",
    "magenta getter stains",
    "clipped channel ends",
    "collapsed neck shards",
    "dark vacuum pockets",
    "sputter freckles",
    "local electrode beads",
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


def _wall_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    size: int,
    head_cut: float,
    tail_cut: float,
    shear: float,
) -> np.ndarray:
    """One notched, incomplete wall chip; never a tube, dash, or capsule."""
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l + vx * half_w * (0.58 - tail_cut), cy - uy * half_l + vy * half_w * (0.58 - tail_cut)),
            (cx - ux * half_l * (0.62 + tail_cut) - vx * half_w, cy - uy * half_l * (0.62 + tail_cut) - vy * half_w),
            (cx + ux * half_l * 0.22 - vx * half_w * (0.92 + shear), cy + uy * half_l * 0.22 - vy * half_w * (0.92 + shear)),
            (cx + ux * half_l - vx * half_w * (0.30 + head_cut), cy + uy * half_l - vy * half_w * (0.30 + head_cut)),
            (cx + ux * half_l * (0.67 - head_cut) + vx * half_w, cy + uy * half_l * (0.67 - head_cut) + vy * half_w),
            (cx + ux * half_l * 0.18 + vx * half_w * (0.66 - shear), cy + uy * half_l * 0.18 + vy * half_w * (0.66 - shear)),
            (cx - ux * half_l * 0.02 + vx * half_w * 0.08, cy - uy * half_l * 0.02 + vy * half_w * 0.08),
            (cx - ux * half_l * 0.48 + vx * half_w * 0.72, cy - uy * half_l * 0.48 + vy * half_w * 0.72),
        ),
        np.float32,
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
            (cx - ux * half_l - vx * half_w * (0.78 + skew), cy - uy * half_l - vy * half_w * (0.78 + skew)),
            (cx + ux * half_l * 0.70 - vx * half_w, cy + uy * half_l * 0.70 - vy * half_w),
            (cx + ux * half_l + vx * half_w * (0.42 - skew), cy + uy * half_l + vy * half_w * (0.42 - skew)),
            (cx + ux * half_l * 0.05 + vx * half_w, cy + uy * half_l * 0.05 + vy * half_w),
            (cx - ux * half_l * 0.82 + vx * half_w * 0.46, cy - uy * half_l * 0.82 + vy * half_w * 0.46),
        ),
        np.float32,
    )


def _deposit_points(
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
            (cx - ux * half_l * 0.32 + vx * half_w * 0.68, cy - uy * half_l * 0.32 + vy * half_w * 0.68),
            (cx - ux * half_l, cy - uy * half_l),
            (cx - ux * half_l * 0.28 - vx * half_w, cy - uy * half_l * 0.28 - vy * half_w),
            (cx + ux * half_l * 0.44 - vx * half_w * 0.54, cy + uy * half_l * 0.44 - vy * half_w * 0.54),
        ),
        np.float32,
    )


def _neck_points(
    anchor: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    side: float,
    size: int,
) -> np.ndarray:
    """Asymmetric collapsed throat with a clipped, non-rounded termination."""
    p0 = _point(anchor, theta, 0.0, -side * width_native * 0.38, size)
    p1 = _point(anchor, theta, length_native * 0.34, -side * width_native * 0.50, size)
    p2 = _point(anchor, theta, length_native, -side * width_native * 0.12, size)
    p3 = _point(anchor, theta, length_native * 0.62, side * width_native * 0.24, size)
    p4 = _point(anchor, theta, length_native * 0.18, side * width_native * 0.48, size)
    return np.asarray((p0, p1, p2, p3, p4), np.float32)


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
    # SPB-105 tick #8: audit the full authored extent for every mark.
    counter[(family, round(max(float(value) for value in dimensions_native), 3))] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def build_vacuum_phosphor(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Vacuum Phosphor is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    shape = (size, size)
    masks = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    tones = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    geometry: Counter[tuple[str, float]] = Counter()

    # Heavily jittered sites share only a two-cell deposition bias. Directions
    # change locally before any row, grid, long curve, worm, or recoverable tube
    # can form. Every secondary feature is physically attached to its wall chip.
    cell = max(6, int(round(_work_px(29.0, size))))
    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + 0.5 * cell + (0.29 * cell if gy % 2 else 0.0) + rng.uniform(-0.46, 0.46) * cell)
            cy = float(y0 + 0.5 * cell + rng.uniform(-0.46, 0.46) * cell)
            domain_x, domain_y = gx // 2, gy // 2
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 7 + domain_y * 19) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.52 + (domain_hash % 37) / 36.0 * 3.04
            theta = float(domain_theta + rng.uniform(-0.60, 0.60))

            carrier_tier = int(rng.integers(0, len(EVENT_TIERS)))
            carrier_length = float(rng.uniform(13.0, 26.0))
            carrier_width = float(rng.uniform(12.0, 22.0))
            carrier_center = _point((cx, cy), theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            carrier_points = _facet_points(
                carrier_center, carrier_length, carrier_width,
                theta + rng.uniform(-0.38, 0.38), size, rng.uniform(-0.20, 0.20),
            )
            _draw_pair(
                masks["black evacuated wall facets"], tones["black evacuated wall facets"],
                carrier_points, float(EVENT_TIERS[carrier_tier]), _paint_tone(rng, carrier_tier),
            )
            _mark(geometry, "black evacuated wall facets", carrier_length, carrier_width)

            if rng.random() >= 0.70:
                continue

            tier = int(rng.integers(0, len(EVENT_TIERS)))
            strength = float(EVENT_TIERS[tier])
            paint_tone = _paint_tone(rng, tier)
            wall_theta = float(theta + rng.uniform(-0.28, 0.28))
            wall_length = float(rng.uniform(15.0, 29.5))
            wall_width = float(rng.uniform(10.0, 17.5))
            wall_center = _point(carrier_center, wall_theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            wall_points = _wall_points(
                wall_center, wall_length, wall_width, wall_theta, size,
                rng.uniform(0.06, 0.34), rng.uniform(0.04, 0.28), rng.uniform(-0.18, 0.18),
            )
            _draw_pair(
                masks["fractured glass-wall slivers"], tones["fractured glass-wall slivers"],
                wall_points, strength, paint_tone,
            )
            _mark(geometry, "fractured glass-wall slivers", wall_length, wall_width)

            side = -1.0 if rng.random() < 0.5 else 1.0
            front = _point(wall_center, wall_theta, wall_length * 0.43, side * wall_width * 0.03, size)
            rear = _point(wall_center, wall_theta, -wall_length * 0.43, -side * wall_width * 0.04, size)

            # Only one irregular wall shoulder glows: paired rails would imply a
            # literal tube. Edge selection changes per fragment.
            if rng.random() < 0.46:
                edge_index = int(rng.choice((0, 1, 2, 4)))
                lip_p0 = tuple(wall_points[edge_index])
                lip_p1 = tuple(wall_points[(edge_index + 1) % len(wall_points)])
                edge_length = float(np.linalg.norm(np.asarray(lip_p1) - np.asarray(lip_p0)) * NATIVE / size)
                if edge_length >= 8.0:
                    lip_tier = int(rng.integers(0, len(EVENT_TIERS)))
                    lip_length = float(np.clip(edge_length, 8.0, 32.0))
                    _line_pair(
                        masks["white-blue excitation lips"], tones["white-blue excitation lips"],
                        lip_p0, lip_p1, 8.0, float(EVENT_TIERS[lip_tier]),
                        _paint_tone(rng, lip_tier), size,
                    )
                    _mark(geometry, "white-blue excitation lips", lip_length, 8.0)

            anatomy = float(rng.random())
            if anatomy < 0.17:
                deposit_length = float(rng.uniform(9.0, min(21.0, wall_length)))
                deposit_width = float(rng.uniform(8.0, min(12.5, wall_width)))
                deposit_center = _point(
                    wall_center, wall_theta, rng.uniform(-4.0, 5.0), side * rng.uniform(-2.0, 2.0), size,
                )
                deposit_points = _deposit_points(
                    deposit_center, deposit_length, deposit_width,
                    wall_theta + rng.uniform(-0.24, 0.24), size, rng.uniform(-0.22, 0.30),
                )
                _draw_pair(
                    masks["cyan phosphor deposits"], tones["cyan phosphor deposits"],
                    deposit_points, strength, paint_tone,
                )
                _mark(geometry, "cyan phosphor deposits", deposit_length, deposit_width)
            elif anatomy < 0.34:
                stain_length = float(rng.uniform(10.0, min(23.0, wall_length)))
                stain_width = float(rng.uniform(8.0, 14.0))
                stain_center = _point(
                    wall_center, wall_theta, rng.uniform(-5.0, 4.0), side * rng.uniform(5.0, 9.0), size,
                )
                stain_points = _facet_points(
                    stain_center, stain_length, stain_width,
                    wall_theta + side * rng.uniform(0.22, 0.58), size, rng.uniform(-0.22, 0.22),
                )
                stain_tier = int(rng.integers(0, len(EVENT_TIERS)))
                _draw_pair(
                    masks["magenta getter stains"], tones["magenta getter stains"],
                    stain_points, float(EVENT_TIERS[stain_tier]), _paint_tone(rng, stain_tier),
                )
                _mark(geometry, "magenta getter stains", stain_length, stain_width)
            elif anatomy < 0.50:
                end_length = float(rng.uniform(8.0, 14.0))
                end_width = float(rng.uniform(8.0, min(13.0, wall_width)))
                anchor = front if rng.random() < 0.52 else rear
                end_center = _point(anchor, wall_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-1.5, 1.5), size)
                end_points = _deposit_points(
                    end_center, end_length, end_width,
                    wall_theta + side * rng.uniform(0.52, 0.98), size, rng.uniform(-0.25, 0.20),
                )
                _draw_pair(
                    masks["clipped channel ends"], tones["clipped channel ends"],
                    end_points, strength, paint_tone,
                )
                _mark(geometry, "clipped channel ends", end_length, end_width)
            elif anatomy < 0.65:
                neck_length = float(rng.uniform(9.0, 17.0))
                neck_width = float(rng.uniform(8.0, 12.5))
                anchor = front if rng.random() < 0.48 else rear
                neck_theta = wall_theta + side * rng.uniform(0.22, 0.55)
                neck_points = _neck_points(anchor, neck_length, neck_width, neck_theta, side, size)
                _draw_pair(
                    masks["collapsed neck shards"], tones["collapsed neck shards"],
                    neck_points, strength, paint_tone,
                )
                _mark(geometry, "collapsed neck shards", neck_length, neck_width)
            elif anatomy < 0.80:
                pocket_length = float(rng.uniform(10.0, min(22.0, wall_length)))
                pocket_width = float(rng.uniform(8.0, min(12.5, wall_width)))
                pocket_center = _point(
                    wall_center, wall_theta, rng.uniform(-4.0, 4.0), rng.uniform(-2.0, 2.0), size,
                )
                pocket_points = _deposit_points(
                    pocket_center, pocket_length, pocket_width,
                    wall_theta + rng.uniform(-0.35, 0.35), size, rng.uniform(-0.28, 0.25),
                )
                _draw_pair(
                    masks["dark vacuum pockets"], tones["dark vacuum pockets"],
                    pocket_points, strength, paint_tone,
                )
                _mark(geometry, "dark vacuum pockets", pocket_length, pocket_width)
            elif anatomy < 0.91:
                freckle_count = 1 + int(rng.random() < 0.42)
                for index in range(freckle_count):
                    freckle_length = float(rng.uniform(8.0, 10.5))
                    freckle_width = float(rng.uniform(8.0, 10.0))
                    freckle_center = _point(
                        rear, wall_theta, -rng.uniform(2.0 + index * 4.0, 5.0 + index * 5.0),
                        side * rng.uniform(-4.0, 5.0), size,
                    )
                    freckle_points = _facet_points(
                        freckle_center, freckle_length, freckle_width,
                        wall_theta + rng.uniform(-0.85, 0.85), size, rng.uniform(-0.26, 0.26),
                    )
                    freckle_tier = int(rng.integers(0, len(EVENT_TIERS)))
                    _draw_pair(
                        masks["sputter freckles"], tones["sputter freckles"],
                        freckle_points, float(EVENT_TIERS[freckle_tier]), _paint_tone(rng, freckle_tier),
                    )
                    _mark(geometry, "sputter freckles", freckle_length, freckle_width)
            else:
                bead_length = float(rng.uniform(8.0, 12.0))
                bead_width = float(rng.uniform(8.0, 11.5))
                anchor = front if rng.random() < 0.55 else rear
                bead_center = _point(anchor, wall_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-2.0, 2.0), size)
                bead_points = _deposit_points(
                    bead_center, bead_length, bead_width,
                    wall_theta + rng.uniform(-0.72, 0.72), size, rng.uniform(-0.20, 0.28),
                )
                _draw_pair(
                    masks["local electrode beads"], tones["local electrode beads"],
                    bead_points, strength, paint_tone,
                )
                _mark(geometry, "local electrode beads", bead_length, bead_width)

    carrier = np.clip(masks["black evacuated wall facets"], 0.0, 1.0)
    walls = np.clip(masks["fractured glass-wall slivers"], 0.0, 1.0)
    lips = np.clip(masks["white-blue excitation lips"], 0.0, 1.0)
    deposits = np.clip(masks["cyan phosphor deposits"], 0.0, 1.0)
    getter = np.clip(masks["magenta getter stains"], 0.0, 1.0)
    ends = np.clip(masks["clipped channel ends"], 0.0, 1.0)
    necks = np.clip(masks["collapsed neck shards"], 0.0, 1.0)
    pockets = np.clip(masks["dark vacuum pockets"], 0.0, 1.0)
    sputter = np.clip(masks["sputter freckles"], 0.0, 1.0)
    electrodes = np.clip(masks["local electrode beads"], 0.0, 1.0)

    damage = np.maximum.reduce((ends, necks, pockets, sputter))
    intact_wall = np.clip(walls - 0.72 * np.maximum.reduce((ends, necks, pockets)), 0.0, 1.0)
    excitation = np.maximum.reduce((lips, deposits, electrodes))
    metal_process = np.maximum.reduce((electrodes, sputter * 0.82, deposits * 0.56, getter * 0.34))
    rough_process = np.maximum.reduce((damage, getter * 0.64, deposits * 0.32))
    coat_process = np.maximum.reduce((intact_wall, lips, deposits * 0.60, carrier * 0.20))
    metal_reach = np.clip(_wrap_blur(metal_process, 5.0, size) * 1.72, 0.0, 1.0)
    rough_reach = np.clip(_wrap_blur(rough_process, 6.0, size) * 1.70, 0.0, 1.0)
    coat_reach = np.clip(_wrap_blur(coat_process, 6.5, size) * 1.62, 0.0, 1.0)
    glow_bed = np.clip(_wrap_blur(np.maximum(excitation, getter * 0.48), 7.0, size) * 1.58, 0.0, 1.0)
    carrier_pressure = np.clip(
        _wrap_blur(np.maximum.reduce((carrier, walls, damage, getter)), 10.5, size) * 1.72,
        0.0, 1.0,
    )
    px = cv2.Sobel(carrier_pressure, cv2.CV_32F, 1, 0, ksize=3)
    py = cv2.Sobel(carrier_pressure, cv2.CV_32F, 0, 1, ksize=3)
    wall_strain = np.abs(px) + np.abs(py)
    wall_strain /= max(float(np.percentile(wall_strain, 99.0)), 1e-6)
    wall_strain = np.clip(wall_strain, 0.0, 1.0)

    # The black evacuated carrier is derived from wall/damage masks only. No
    # waveform, sign, tube path, circuitry, lane field, or generic grain exists.
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.010 + 0.026 * carrier_pressure + 0.025 * glow_bed + 0.010 * wall_strain
    paint[..., 1] = 0.015 + 0.035 * carrier_pressure + 0.060 * glow_bed + 0.014 * wall_strain
    paint[..., 2] = 0.026 + 0.060 * carrier_pressure + 0.095 * glow_bed + 0.026 * wall_strain

    # 2026-08-27 visual repair: broaden the visible ceramic/glass carrier and
    # subordinate the wall bodies so the surface cannot collapse to blue dash
    # wallpaper. Bright excitation remains an attached, one-shoulder event.
    _blend(paint, carrier, _ramp(tones["black evacuated wall facets"], (0.012, 0.025, 0.045), (0.115, 0.205, 0.310)), 0.94)
    _blend(paint, walls, _ramp(tones["fractured glass-wall slivers"], (0.022, 0.050, 0.090), (0.235, 0.430, 0.575)), 0.74)
    _blend(paint, getter, _ramp(tones["magenta getter stains"], (0.090, 0.010, 0.115), (0.720, 0.080, 0.590)), 0.90)
    _blend(paint, deposits, _ramp(tones["cyan phosphor deposits"], (0.015, 0.130, 0.150), (0.180, 0.945, 1.000)), 0.98)
    _blend(paint, lips, _ramp(tones["white-blue excitation lips"], (0.080, 0.170, 0.235), (0.760, 0.945, 1.000)), 0.94)
    _blend(paint, ends, _ramp(tones["clipped channel ends"], (0.008, 0.020, 0.040), (0.160, 0.300, 0.390)), 0.96)
    _blend(paint, necks, _ramp(tones["collapsed neck shards"], (0.025, 0.040, 0.080), (0.390, 0.430, 0.610)), 0.94)
    _blend(paint, pockets, _ramp(tones["dark vacuum pockets"], (0.003, 0.006, 0.012), (0.025, 0.055, 0.100)), 0.98)
    _blend(paint, sputter, _ramp(tones["sputter freckles"], (0.080, 0.025, 0.070), (0.710, 0.300, 0.525)), 0.95)
    _blend(paint, electrodes, _ramp(tones["local electrode beads"], (0.115, 0.075, 0.045), (1.000, 0.790, 0.405)), 0.99)
    paint = np.clip(paint, 0.0, 1.0)

    metal_score = (
        0.04 + 0.62 * metal_reach + 1.78 * electrodes + 1.42 * sputter
        + 1.02 * deposits + 0.48 * getter - 0.92 * intact_wall
        - 0.52 * lips - 0.34 * carrier - 0.28 * pockets
    )
    rough_score = (
        0.12 + 0.62 * rough_reach + 1.58 * ends + 1.48 * necks
        + 1.38 * pockets + 1.24 * sputter + 0.72 * getter
        - 0.86 * lips - 0.62 * intact_wall - 0.36 * deposits
    )
    coat_score = (
        0.16 + 0.56 * coat_reach + 1.46 * intact_wall + 1.54 * lips
        + 0.82 * deposits + 0.38 * carrier - 1.22 * ends
        - 1.12 * necks - 1.04 * pockets - 0.68 * sputter - 0.42 * getter
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
            "M": "local electrode beads, sputter freckles, cyan phosphor deposits, and getter residue lead while intact glass stays low",
            "R": "clipped ends, collapsed necks, vacuum pockets, sputter, and getter damage rise independently",
            "Cc": "intact wall slivers, excitation lips, and phosphor shoulders retain clear while breaks and vacuum pockets interrupt it",
        },
        carrier="black evacuated glass/ceramic composite carrying broken phosphor-channel wall fragments",
        vetoes=(
            "literal tube, sign, text, waveform, or music UI",
            "long curve, loop, worm, paired rail, or repeated capsule",
            "circuitry, macro lane, row, grid, or barcode",
            "floating confetti or generic glow flakes",
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
    result = timed_result(build_vacuum_phosphor, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_vacuum_phosphor, seed)
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
    parser = argparse.ArgumentParser(description="Render isolated Vacuum Phosphor owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "vacuum_phosphor",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
