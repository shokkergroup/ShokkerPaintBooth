"""Fresnel Rain-Skin — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset finish #9 / owner verdict 2026-08-27: "Claude's
rebuild has failed miserably." Metric movement: rejected live finish with no
isolated causal baseline -> deterministic unwired hydrophobic optical-film
pilot pending owner review, mapped-car proof, and official catalog M7. This
module does not register or replace the live ``neon2_rain`` finish.
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


FINISH_ID = "neon2_rain"
DISPLAY_NAME = "Fresnel Rain-Skin"
DEFAULT_SEED = 0xF2E5_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
PAINT_TIERS = np.asarray((0.08, 0.19, 0.31, 0.43, 0.56, 0.69, 0.83, 0.98), np.float32)

FAMILIES = (
    "black optical-clear facets",
    "clipped Fresnel lens skins",
    "cyan leading ridges",
    "violet trailing skins",
    "ruptured menisci",
    "trapped angular microbeads",
    "dry notches",
    "overlapping lens seams",
    "white caustic chips",
    "dark dewetting pits",
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
            (cx - ux * half_l - vx * half_w * (0.72 + skew), cy - uy * half_l - vy * half_w * (0.72 + skew)),
            (cx + ux * half_l * 0.62 - vx * half_w, cy + uy * half_l * 0.62 - vy * half_w),
            (cx + ux * half_l + vx * half_w * (0.32 - skew), cy + uy * half_l + vy * half_w * (0.32 - skew)),
            (cx + ux * half_l * 0.10 + vx * half_w, cy + uy * half_l * 0.10 + vy * half_w),
            (cx - ux * half_l * 0.78 + vx * half_w * 0.45, cy - uy * half_l * 0.78 + vy * half_w * 0.45),
        ),
        np.float32,
    )


def _lens_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    side: float,
    size: int,
    clip: float,
    bend: float,
) -> np.ndarray:
    """A broad clipped film pane, never a closed drop, ring, or scale."""
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l + side * vx * half_w * 0.10, cy - uy * half_l + side * vy * half_w * 0.10),
            (cx - ux * half_l * (0.56 + clip) - side * vx * half_w * 0.82, cy - uy * half_l * (0.56 + clip) - side * vy * half_w * 0.82),
            (cx - ux * half_l * 0.05 - side * vx * half_w, cy - uy * half_l * 0.05 - side * vy * half_w),
            (cx + ux * half_l * 0.58 - side * vx * half_w * (0.74 + bend), cy + uy * half_l * 0.58 - side * vy * half_w * (0.74 + bend)),
            (cx + ux * half_l - side * vx * half_w * 0.06, cy + uy * half_l - side * vy * half_w * 0.06),
            (cx + ux * half_l * 0.48 + side * vx * half_w * 0.58, cy + uy * half_l * 0.48 + side * vy * half_w * 0.58),
            # Keep the inner shoulder shallow. The original deep notch read as
            # thousands of C/U rings; this remains a clipped pane whose Fresnel
            # identity comes from one-sided ridges rather than a closed outline.
            (cx + ux * half_l * 0.02 + side * vx * half_w * 0.46, cy + uy * half_l * 0.02 + side * vy * half_w * 0.46),
            (cx - ux * half_l * 0.48 + side * vx * half_w * (0.68 - bend), cy - uy * half_l * 0.48 + side * vy * half_w * (0.68 - bend)),
        ),
        np.float32,
    )


def _skin_points(
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    side: float,
    size: int,
    taper: float,
) -> np.ndarray:
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    return np.asarray(
        (
            (cx - ux * half_l - side * vx * half_w * 0.72, cy - uy * half_l - side * vy * half_w * 0.72),
            (cx + ux * half_l * taper - side * vx * half_w, cy + uy * half_l * taper - side * vy * half_w),
            (cx + ux * half_l + side * vx * half_w * 0.18, cy + uy * half_l + side * vy * half_w * 0.18),
            (cx + ux * half_l * 0.08 + side * vx * half_w, cy + uy * half_l * 0.08 + side * vy * half_w),
            (cx - ux * half_l * 0.74 + side * vx * half_w * 0.36, cy - uy * half_l * 0.74 + side * vy * half_w * 0.36),
        ),
        np.float32,
    )


def _chip_points(
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
            (cx - ux * half_l * 0.42 + vx * half_w * 0.58, cy - uy * half_l * 0.42 + vy * half_w * 0.58),
            (cx - ux * half_l, cy - uy * half_l),
            (cx - ux * half_l * 0.18 - vx * half_w, cy - uy * half_l * 0.18 - vy * half_w),
            (cx + ux * half_l * 0.46 - vx * half_w * 0.48, cy + uy * half_l * 0.46 - vy * half_w * 0.48),
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
    # SPB-105 tick #9: audit each complete authored extent, not line width alone.
    counter[(family, round(max(float(value) for value in dimensions_native), 3))] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def build_fresnel_rain_skin(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Fresnel Rain-Skin is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    shape = (size, size)
    masks = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    tones = {family: np.zeros(shape, np.float32) for family in FAMILIES}
    geometry: Counter[tuple[str, float]] = Counter()

    # Jittered optical sites share only a tiny two-cell shear bias. Orientation
    # changes before rows, falling lines, scales, ripples, or waves can emerge.
    # All anatomy remains attached to one collapsed film remnant.
    cell = max(6, int(round(_work_px(29.0, size))))
    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + 0.5 * cell + (0.31 * cell if gy % 2 else 0.0) + rng.uniform(-0.47, 0.47) * cell)
            cy = float(y0 + 0.5 * cell + rng.uniform(-0.47, 0.47) * cell)
            domain_x, domain_y = gx // 2, gy // 2
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 17 - domain_y * 11) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.50 + (domain_hash % 41) / 40.0 * 3.00
            theta = float(domain_theta + rng.uniform(-0.62, 0.62))

            carrier_tier = int(rng.integers(0, len(EVENT_TIERS)))
            carrier_length = float(rng.uniform(13.0, 27.0))
            carrier_width = float(rng.uniform(11.0, 22.0))
            carrier_center = _point((cx, cy), theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            carrier_points = _facet_points(
                carrier_center, carrier_length, carrier_width,
                theta + rng.uniform(-0.40, 0.40), size, rng.uniform(-0.20, 0.20),
            )
            _draw_pair(
                masks["black optical-clear facets"], tones["black optical-clear facets"],
                carrier_points, float(EVENT_TIERS[carrier_tier]), _paint_tone(rng, carrier_tier),
            )
            _mark(geometry, "black optical-clear facets", carrier_length, carrier_width)

            if rng.random() >= 0.70:
                continue

            tier = int(rng.integers(0, len(EVENT_TIERS)))
            strength = float(EVENT_TIERS[tier])
            paint_tone = _paint_tone(rng, tier)
            side = -1.0 if rng.random() < 0.5 else 1.0
            lens_theta = float(theta + rng.uniform(-0.30, 0.30))
            lens_length = float(rng.uniform(15.0, 30.0))
            lens_width = float(rng.uniform(11.0, 19.0))
            lens_center = _point(carrier_center, lens_theta, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), size)
            lens_points = _lens_points(
                lens_center, lens_length, lens_width, lens_theta, side, size,
                rng.uniform(0.03, 0.26), rng.uniform(-0.16, 0.16),
            )
            _draw_pair(
                masks["clipped Fresnel lens skins"], tones["clipped Fresnel lens skins"],
                lens_points, strength, paint_tone,
            )
            _mark(geometry, "clipped Fresnel lens skins", lens_length, lens_width)

            front = _point(lens_center, lens_theta, lens_length * 0.43, side * lens_width * 0.02, size)
            rear = _point(lens_center, lens_theta, -lens_length * 0.43, -side * lens_width * 0.04, size)

            if rng.random() < 0.60:
                edge_index = int(rng.choice((1, 2, 3, 5)))
                p0 = tuple(lens_points[edge_index])
                p1 = tuple(lens_points[(edge_index + 1) % len(lens_points)])
                edge_length = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)) * NATIVE / size)
                if edge_length >= 8.0:
                    ridge_tier = int(rng.integers(0, len(EVENT_TIERS)))
                    ridge_length = float(np.clip(edge_length, 8.0, 32.0))
                    _line_pair(
                        masks["cyan leading ridges"], tones["cyan leading ridges"],
                        p0, p1, 8.0, float(EVENT_TIERS[ridge_tier]),
                        _paint_tone(rng, ridge_tier), size,
                    )
                    _mark(geometry, "cyan leading ridges", ridge_length, 8.0)

            if rng.random() < 0.46:
                skin_length = float(rng.uniform(10.0, min(24.0, lens_length)))
                skin_width = float(rng.uniform(8.0, min(13.5, lens_width)))
                skin_center = _point(
                    lens_center, lens_theta, rng.uniform(-4.0, 3.0), side * rng.uniform(5.0, 9.0), size,
                )
                skin_points = _skin_points(
                    skin_center, skin_length, skin_width,
                    lens_theta + side * rng.uniform(0.14, 0.42), side, size, rng.uniform(0.48, 0.86),
                )
                skin_tier = int(rng.integers(0, len(EVENT_TIERS)))
                _draw_pair(
                    masks["violet trailing skins"], tones["violet trailing skins"],
                    skin_points, float(EVENT_TIERS[skin_tier]), _paint_tone(rng, skin_tier),
                )
                _mark(geometry, "violet trailing skins", skin_length, skin_width)

            anatomy = float(rng.random())
            if anatomy < 0.17:
                segment_a = float(rng.uniform(8.0, 14.0))
                segment_b = float(rng.uniform(8.0, 13.0))
                start = front if rng.random() < 0.52 else rear
                kink_theta = lens_theta + side * rng.uniform(0.38, 0.72)
                junction = _point(start, kink_theta, segment_a, 0.0, size)
                end = _point(junction, kink_theta - side * rng.uniform(0.34, 0.62), segment_b, 0.0, size)
                _line_pair(
                    masks["ruptured menisci"], tones["ruptured menisci"],
                    start, junction, 8.0, strength, paint_tone, size,
                )
                _line_pair(
                    masks["ruptured menisci"], tones["ruptured menisci"],
                    junction, end, 8.0, strength * 0.84, paint_tone * 0.90, size,
                )
                _mark(geometry, "ruptured menisci", segment_a, 8.0)
                _mark(geometry, "ruptured menisci", segment_b, 8.0)
            elif anatomy < 0.34:
                bead_length = float(rng.uniform(8.0, 12.0))
                bead_width = float(rng.uniform(8.0, 11.5))
                bead_center = _point(
                    rear, lens_theta, rng.uniform(-1.0, 3.0), side * rng.uniform(-2.0, 3.0), size,
                )
                bead_points = _chip_points(
                    bead_center, bead_length, bead_width,
                    lens_theta + rng.uniform(-0.75, 0.75), size, rng.uniform(-0.22, 0.28),
                )
                _draw_pair(
                    masks["trapped angular microbeads"], tones["trapped angular microbeads"],
                    bead_points, strength, paint_tone,
                )
                _mark(geometry, "trapped angular microbeads", bead_length, bead_width)
            elif anatomy < 0.51:
                notch_length = float(rng.uniform(8.0, 14.0))
                notch_width = float(rng.uniform(8.0, min(13.0, lens_width)))
                anchor = front if rng.random() < 0.50 else rear
                notch_center = _point(anchor, lens_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-2.0, 2.0), size)
                notch_points = _chip_points(
                    notch_center, notch_length, notch_width,
                    lens_theta + side * rng.uniform(0.50, 0.95), size, rng.uniform(-0.22, 0.22),
                )
                _draw_pair(
                    masks["dry notches"], tones["dry notches"],
                    notch_points, strength, paint_tone,
                )
                _mark(geometry, "dry notches", notch_length, notch_width)
            elif anatomy < 0.68:
                seam_length = float(rng.uniform(9.0, 18.0))
                seam_theta = lens_theta + side * rng.uniform(0.52, 0.94)
                seam_start = _point(lens_center, lens_theta, rng.uniform(-4.0, 4.0), -side * lens_width * 0.36, size)
                seam_end = _point(seam_start, seam_theta, seam_length, 0.0, size)
                _line_pair(
                    masks["overlapping lens seams"], tones["overlapping lens seams"],
                    seam_start, seam_end, 8.0, strength, paint_tone, size,
                )
                _mark(geometry, "overlapping lens seams", seam_length, 8.0)
            elif anatomy < 0.84:
                chip_length = float(rng.uniform(8.0, 12.5))
                chip_width = float(rng.uniform(8.0, 11.5))
                anchor = front if rng.random() < 0.58 else rear
                chip_center = _point(anchor, lens_theta, rng.uniform(-1.0, 2.0), side * rng.uniform(-2.0, 2.5), size)
                chip_points = _chip_points(
                    chip_center, chip_length, chip_width,
                    lens_theta + rng.uniform(-0.78, 0.78), size, rng.uniform(-0.20, 0.28),
                )
                _draw_pair(
                    masks["white caustic chips"], tones["white caustic chips"],
                    chip_points, strength, paint_tone,
                )
                _mark(geometry, "white caustic chips", chip_length, chip_width)
            else:
                pit_length = float(rng.uniform(10.0, min(20.0, lens_length)))
                pit_width = float(rng.uniform(8.0, min(13.0, lens_width)))
                pit_center = _point(
                    lens_center, lens_theta, rng.uniform(-4.0, 4.0), rng.uniform(-2.0, 2.0), size,
                )
                pit_points = _chip_points(
                    pit_center, pit_length, pit_width,
                    lens_theta + rng.uniform(-0.35, 0.35), size, rng.uniform(-0.25, 0.25),
                )
                _draw_pair(
                    masks["dark dewetting pits"], tones["dark dewetting pits"],
                    pit_points, strength, paint_tone,
                )
                _mark(geometry, "dark dewetting pits", pit_length, pit_width)

    carrier = np.clip(masks["black optical-clear facets"], 0.0, 1.0)
    lenses = np.clip(masks["clipped Fresnel lens skins"], 0.0, 1.0)
    ridges = np.clip(masks["cyan leading ridges"], 0.0, 1.0)
    skins = np.clip(masks["violet trailing skins"], 0.0, 1.0)
    ruptures = np.clip(masks["ruptured menisci"], 0.0, 1.0)
    beads = np.clip(masks["trapped angular microbeads"], 0.0, 1.0)
    notches = np.clip(masks["dry notches"], 0.0, 1.0)
    seams = np.clip(masks["overlapping lens seams"], 0.0, 1.0)
    caustics = np.clip(masks["white caustic chips"], 0.0, 1.0)
    pits = np.clip(masks["dark dewetting pits"], 0.0, 1.0)

    damage = np.maximum.reduce((ruptures, notches, seams, pits))
    intact_lens = np.clip(lenses - 0.72 * np.maximum.reduce((ruptures, notches, pits)), 0.0, 1.0)
    substrate_process = np.maximum.reduce((notches, pits * 0.84, ruptures * 0.62, caustics * 0.48))
    rough_process = np.maximum.reduce((damage, caustics * 0.58, skins * 0.28))
    clear_process = np.maximum.reduce((intact_lens, ridges, skins * 0.72, beads * 0.64))
    substrate_reach = np.clip(_wrap_blur(substrate_process, 5.0, size) * 1.70, 0.0, 1.0)
    rough_reach = np.clip(_wrap_blur(rough_process, 6.0, size) * 1.68, 0.0, 1.0)
    clear_reach = np.clip(_wrap_blur(clear_process, 6.5, size) * 1.62, 0.0, 1.0)
    optic_bed = np.clip(_wrap_blur(np.maximum.reduce((lenses, ridges, skins, caustics)), 7.0, size) * 1.60, 0.0, 1.0)
    carrier_pressure = np.clip(
        _wrap_blur(np.maximum.reduce((carrier, lenses, damage, skins)), 10.5, size) * 1.72,
        0.0, 1.0,
    )
    px = cv2.Sobel(carrier_pressure, cv2.CV_32F, 1, 0, ksize=3)
    py = cv2.Sobel(carrier_pressure, cv2.CV_32F, 0, 1, ksize=3)
    film_strain = np.abs(px) + np.abs(py)
    film_strain /= max(float(np.percentile(film_strain, 99.0)), 1e-6)
    film_strain = np.clip(film_strain, 0.0, 1.0)

    # The optical carrier derives only from lens and failure masks. There are no
    # rain strokes, falling marks, drops, rings, waves, or generic wet noise.
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.010 + 0.024 * carrier_pressure + 0.022 * optic_bed + 0.009 * film_strain
    paint[..., 1] = 0.018 + 0.044 * carrier_pressure + 0.054 * optic_bed + 0.014 * film_strain
    paint[..., 2] = 0.032 + 0.076 * carrier_pressure + 0.092 * optic_bed + 0.028 * film_strain

    # 2026-08-27 visual repair: visible broad carrier panes replace the first
    # pass's repeated C/U silhouettes while preserving dense optical response.
    _blend(paint, carrier, _ramp(tones["black optical-clear facets"], (0.012, 0.032, 0.055), (0.125, 0.235, 0.350)), 0.96)
    _blend(paint, lenses, _ramp(tones["clipped Fresnel lens skins"], (0.018, 0.050, 0.085), (0.205, 0.430, 0.570)), 0.72)
    _blend(paint, skins, _ramp(tones["violet trailing skins"], (0.040, 0.015, 0.095), (0.430, 0.140, 0.680)), 0.88)
    _blend(paint, ridges, _ramp(tones["cyan leading ridges"], (0.020, 0.150, 0.185), (0.280, 0.925, 1.000)), 0.96)
    _blend(paint, ruptures, _ramp(tones["ruptured menisci"], (0.010, 0.025, 0.050), (0.170, 0.330, 0.440)), 0.94)
    _blend(paint, beads, _ramp(tones["trapped angular microbeads"], (0.080, 0.120, 0.165), (0.610, 0.850, 0.960)), 0.94)
    _blend(paint, notches, _ramp(tones["dry notches"], (0.003, 0.007, 0.014), (0.035, 0.075, 0.115)), 0.98)
    _blend(paint, seams, _ramp(tones["overlapping lens seams"], (0.025, 0.045, 0.090), (0.310, 0.360, 0.620)), 0.90)
    _blend(paint, pits, _ramp(tones["dark dewetting pits"], (0.002, 0.004, 0.009), (0.020, 0.045, 0.075)), 0.99)
    _blend(paint, caustics, _ramp(tones["white caustic chips"], (0.100, 0.165, 0.210), (0.880, 0.970, 1.000)), 0.99)
    # SPB-105 / 2026-08-27 owner verdict: increase pane visibility through
    # exposure, never larger Fresnel anatomy. Official isolated M7 before this
    # calibration: 84.2; final movement is recorded by the rerun below.
    paint = np.clip(paint * 1.40, 0.0, 1.0)

    metal_score = (
        0.04 + 0.62 * substrate_reach + 1.54 * notches + 1.42 * pits
        + 1.16 * caustics + 0.72 * ruptures - 0.88 * intact_lens
        - 0.56 * ridges - 0.38 * beads - 0.28 * skins
    )
    rough_score = (
        0.10 + 0.64 * rough_reach + 1.58 * ruptures + 1.48 * notches
        + 1.36 * seams + 1.28 * pits + 0.82 * caustics
        - 0.92 * ridges - 0.76 * intact_lens - 0.46 * beads
    )
    coat_score = (
        0.16 + 0.58 * clear_reach + 1.52 * intact_lens + 1.46 * ridges
        + 1.12 * skins + 0.88 * beads + 0.36 * carrier
        - 1.22 * ruptures - 1.16 * notches - 1.08 * pits
        - 0.72 * seams - 0.38 * caustics
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
            "M": "dry notches, dewetting pits, caustic substrate chips, and ruptured film expose the dark base while intact optics stay low",
            "R": "ruptured menisci, dry notches, overlapping seams, pits, and caustic fracture rise independently",
            "Cc": "intact Fresnel film, cyan leading ridges, violet trailing skins, and trapped beads retain optical clear",
        },
        carrier="black hydrophobic optical clear carrying collapsed angular water-film lenses",
        vetoes=(
            "rain line, falling drop, teardrop, or weather illustration",
            "bubble, polka dot, round bead, scale, or repeated tile",
            "ripple, ring, loop, wave, or long curve",
            "row, grid, lane, or directional rain field",
            "generic wet noise or unrelated texture underlay",
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
    result = timed_result(build_fresnel_rain_skin, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_fresnel_rain_skin, seed)
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
    parser = argparse.ArgumentParser(description="Render isolated Fresnel Rain-Skin owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "fresnel_rain_skin",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
