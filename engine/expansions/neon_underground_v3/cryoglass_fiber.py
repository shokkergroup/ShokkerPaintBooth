"""Cryoglass Fiber — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset tick CF-P2 / owner directive 2026-08-27: avoid "a generic
white-noise carpet."  Visual movement: pale repeated C-shaped bead packets ->
larger irregular short-fibre sheaves over continuous graphite facets; 64px
chroma 0.023994 -> 0.028120 (pass).  Final audit: deterministic ~1.9s builder,
nine visible anatomy families, 20.3% fractured-fibre coverage, 8-tier causal
M/R/Cc, and every authored dimension 8-32px.  It remains unwired pending owner
review.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time
from typing import Sequence

import cv2
import numpy as np

from engine.paint_v2.neon_material_core_v3 import (
    GeometryMark,
    NATIVE,
    PilotResult,
    WORK,
    blur,
    material_stats,
    pack_material,
    render_evidence,
    seeded,
    timed_result,
)


FINISH_ID = "neon_ice_white"
DISPLAY_NAME = "Cryoglass Fiber"
DEFAULT_SEED = 0xC8A0_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)


Layer = tuple[np.ndarray, np.ndarray, np.ndarray]


def _new_layer(size: int) -> Layer:
    return (
        np.zeros((size, size, 3), np.uint8),
        np.zeros((size, size), np.uint8),
        np.zeros((size, size), np.float32),
    )


def _basis(theta: float) -> tuple[np.ndarray, np.ndarray]:
    tangent = np.asarray((math.cos(theta), math.sin(theta)), np.float32)
    normal = np.asarray((-tangent[1], tangent[0]), np.float32)
    return tangent, normal


def _point(
    center: np.ndarray,
    theta: float,
    along_native: float,
    across_native: float,
    size: int,
) -> np.ndarray:
    tangent, normal = _basis(theta)
    scale = float(size) / float(NATIVE)
    return center + tangent * (float(along_native) * scale) + normal * (float(across_native) * scale)


def _polygon(
    center: np.ndarray,
    theta: float,
    offsets_native: Sequence[tuple[float, float]],
    size: int,
) -> np.ndarray:
    tangent, normal = _basis(theta)
    scale = float(size) / float(NATIVE)
    points = [
        center + tangent * (along * scale) + normal * (across * scale)
        for along, across in offsets_native
    ]
    return np.rint(points).astype(np.int32)


def _strip(
    center: np.ndarray,
    theta: float,
    length_native: float,
    width_native: float,
    size: int,
    skew: float = 0.0,
) -> np.ndarray:
    half_l = float(length_native) * 0.5
    half_w = float(width_native) * 0.5
    return _polygon(
        center,
        theta,
        (
            (-half_l, -half_w),
            (half_l, -half_w * (1.0 - skew)),
            (half_l, half_w),
            (-half_l, half_w * (1.0 + skew)),
        ),
        size,
    )


def _paint_mark(
    layer: Layer,
    polygon: np.ndarray,
    color: Sequence[int],
    opacity: int,
    tier: float,
) -> None:
    rgb, alpha, causal = layer
    cv2.fillConvexPoly(rgb, polygon, tuple(int(value) for value in color), cv2.LINE_AA)
    cv2.fillConvexPoly(alpha, polygon, int(opacity), cv2.LINE_AA)
    cv2.fillConvexPoly(causal, polygon, float(tier), cv2.LINE_AA)


def _composite(paint: np.ndarray, layer: Layer, strength: float = 1.0) -> None:
    rgb, alpha, _ = layer
    weight = (alpha.astype(np.float32) / 255.0 * float(strength))[..., None]
    paint *= 1.0 - weight
    paint += rgb.astype(np.float32) / 255.0 * weight


def _tiered(
    rng: np.random.Generator,
    palette: np.ndarray,
    low: int = 0,
    high: int = 8,
) -> tuple[tuple[int, int, int], float]:
    index = int(rng.integers(low, high))
    return tuple(int(value) for value in palette[index]), float(EVENT_TIERS[index])


def _weighted_tier(
    rng: np.random.Generator,
    palette: np.ndarray,
    weights: Sequence[float],
) -> tuple[tuple[int, int, int], float]:
    probabilities = np.asarray(weights, np.float64)
    probabilities /= probabilities.sum()
    index = int(rng.choice(len(palette), p=probabilities))
    return tuple(int(value) for value in palette[index]), float(EVENT_TIERS[index])


def _mark(counter: Counter[tuple[str, float]], family: str, dimension_native: float) -> None:
    dimension = round(float(dimension_native), 3)
    if not 8.0 <= dimension <= 32.0:
        raise ValueError(f"{family} authored outside 8-32px: {dimension}")
    counter[(family, dimension)] += 1


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


RESIN_PALETTE = np.asarray(
    (
        (6, 11, 19),
        (8, 16, 27),
        (11, 22, 36),
        (14, 29, 47),
        (18, 37, 58),
        (23, 47, 71),
        (31, 59, 85),
        (42, 73, 101),
    ),
    np.uint8,
)
FIBER_PALETTE = np.asarray(
    (
        (43, 57, 75),
        (63, 80, 100),
        (86, 106, 127),
        (113, 136, 157),
        (143, 167, 186),
        (175, 200, 217),
        (209, 228, 241),
        (244, 251, 255),
    ),
    np.uint8,
)
PRISM_PALETTE = np.asarray(
    (
        (40, 71, 107),
        (50, 94, 137),
        (58, 119, 164),
        (72, 148, 190),
        (99, 174, 211),
        (137, 194, 226),
        (177, 216, 241),
        (222, 242, 255),
    ),
    np.uint8,
)
FROST_PALETTE = np.asarray(
    (
        (81, 103, 126),
        (105, 129, 151),
        (130, 155, 176),
        (156, 181, 201),
        (182, 207, 224),
        (205, 227, 241),
        (228, 243, 251),
        (249, 254, 255),
    ),
    np.uint8,
)
WELD_PALETTE = np.asarray(
    (
        (63, 89, 116),
        (80, 112, 139),
        (99, 137, 163),
        (121, 160, 184),
        (147, 184, 205),
        (176, 207, 224),
        (207, 230, 242),
        (241, 251, 255),
    ),
    np.uint8,
)


def build_cryoglass_fiber(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic short-fibre cryoglass/resin laminate."""
    if int(size) != WORK:
        raise ValueError(f"Cryoglass Fiber is authored at WORK={WORK}, got {size}")
    rng = seeded(seed)
    layers: dict[str, Layer] = {
        "graphite resin facets": _new_layer(size),
        "translucent fiber cores": _new_layer(size),
        "prismatic splinters": _new_layer(size),
        "frost collars": _new_layer(size),
        "clipped fiber ends": _new_layer(size),
        "faceted air beads": _new_layer(size),
        "crossing welds": _new_layer(size),
        "delamination notches": _new_layer(size),
        "black occlusion cuts": _new_layer(size),
    }
    geometry: Counter[tuple[str, float]] = Counter()

    # Dark graphite facets form a continuous resin carrier without independent
    # noise.  Three silhouette variants and strong jitter suppress wallpaper.
    resin_cell = max(5, int(round(30.0 * size / NATIVE)))
    for gy, y0 in enumerate(range(-resin_cell, size + resin_cell, resin_cell)):
        for gx, x0 in enumerate(range(-resin_cell, size + resin_cell, resin_cell)):
            if rng.random() < 0.08:
                continue
            center = np.asarray(
                (
                    x0 + rng.uniform(-0.46, 0.46) * resin_cell,
                    y0 + rng.uniform(-0.46, 0.46) * resin_cell,
                ),
                np.float32,
            )
            theta = float(rng.uniform(-math.pi, math.pi))
            length = float(rng.uniform(12.0, 24.0))
            width = float(rng.uniform(8.0, 16.0))
            half_l, half_w = length * 0.5, width * 0.5
            variant = int(rng.integers(0, 3))
            if variant == 0:
                offsets = (
                    (-half_l, -half_w * 0.22),
                    (-half_l * 0.30, -half_w),
                    (half_l, -half_w * 0.34),
                    (half_l * 0.56, half_w),
                    (-half_l * 0.64, half_w * 0.58),
                )
            elif variant == 1:
                offsets = (
                    (-half_l, -half_w * 0.62),
                    (half_l * 0.42, -half_w),
                    (half_l, half_w * 0.12),
                    (half_l * 0.08, half_w),
                    (-half_l * 0.70, half_w * 0.52),
                )
            else:
                offsets = (
                    (-half_l, -half_w * 0.10),
                    (-half_l * 0.12, -half_w),
                    (half_l, -half_w * 0.08),
                    (half_l * 0.34, half_w),
                    (-half_l * 0.76, half_w * 0.46),
                )
            color, tier = _tiered(rng, RESIN_PALETTE)
            _paint_mark(
                layers["graphite resin facets"],
                _polygon(center, theta, offsets, size),
                color,
                int(rng.integers(72, 144)),
                tier,
            )
            _mark(geometry, "graphite resin facets", length)

    # Fibre bundles are short local packets, not continuous hairs or webs.
    bundle_cell = max(12, int(round(96.0 * size / NATIVE)))
    margin = int(round(32.0 * size / NATIVE))
    for gy, base_y in enumerate(range(-bundle_cell // 2, size + bundle_cell, bundle_cell)):
        for gx, base_x in enumerate(range(-bundle_cell // 2, size + bundle_cell, bundle_cell)):
            bundle_center = np.asarray(
                (
                    base_x + rng.uniform(-0.44, 0.44) * bundle_cell,
                    base_y + rng.uniform(-0.44, 0.44) * bundle_cell,
                ),
                np.float32,
            )
            if (
                bundle_center[0] < -margin
                or bundle_center[1] < -margin
                or bundle_center[0] > size + margin
                or bundle_center[1] > size + margin
            ):
                continue
            domain_x, domain_y = gx // 4, gy // 4
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 3 + domain_y * 7) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -math.pi + (domain_hash % 1021) / 1020.0 * math.tau
            bundle_theta = float(domain_theta + rng.normal(0.0, 0.28))
            fiber_count = int(rng.integers(7, 13))
            across_slots = np.linspace(-24.0, 24.0, fiber_count, dtype=np.float32)
            across_slots += rng.uniform(-3.5, 3.5, size=fiber_count).astype(np.float32)

            for fiber_index in range(fiber_count):
                theta = float(bundle_theta + rng.normal(0.0, 0.13))
                center = _point(
                    bundle_center,
                    bundle_theta,
                    rng.uniform(-28.0, 28.0),
                    float(across_slots[fiber_index]),
                    size,
                )
                length = float(rng.uniform(22.0, 32.0))
                width = float(rng.uniform(8.0, 10.5))
                half_l, half_w = length * 0.5, width * 0.5
                fiber_poly = _polygon(
                    center,
                    theta,
                    (
                        (-half_l, -half_w * 0.20),
                        (-half_l * 0.72, -half_w),
                        (half_l * 0.62, -half_w * 0.78),
                        (half_l, -half_w * 0.08),
                        (half_l * 0.66, half_w * 0.82),
                        (-half_l * 0.56, half_w),
                    ),
                    size,
                )
                fiber_color, fiber_tier = _weighted_tier(
                    rng,
                    FIBER_PALETTE,
                    (0.06, 0.11, 0.17, 0.21, 0.20, 0.14, 0.08, 0.03),
                )
                _paint_mark(
                    layers["translucent fiber cores"],
                    fiber_poly,
                    fiber_color,
                    int(rng.integers(124, 216)),
                    fiber_tier,
                )
                _mark(geometry, "fractured translucent fibers", length)

                side = -1.0 if rng.random() < 0.5 else 1.0
                if rng.random() < 0.28:
                    splinter_length = float(rng.uniform(10.0, 24.0))
                    splinter_width = float(rng.uniform(8.0, 10.0))
                    splinter_center = _point(
                        center,
                        theta,
                        rng.uniform(-half_l * 0.46, half_l * 0.48),
                        side * rng.uniform(half_w * 0.35, half_w * 0.88),
                        size,
                    )
                    splinter_poly = _polygon(
                        splinter_center,
                        theta + side * rng.uniform(0.12, 0.48),
                        (
                            (-splinter_length * 0.50, 0.0),
                            (splinter_length * 0.34, -splinter_width * 0.50),
                            (splinter_length * 0.50, splinter_width * 0.08),
                            (-splinter_length * 0.30, splinter_width * 0.50),
                        ),
                        size,
                    )
                    color, tier = _tiered(rng, PRISM_PALETTE)
                    _paint_mark(layers["prismatic splinters"], splinter_poly, color, int(rng.integers(154, 229)), tier)
                    _mark(geometry, "prismatic splinters", splinter_length)

                if rng.random() < 0.17:
                    collar_length = float(rng.uniform(8.0, 13.0))
                    collar_width = float(rng.uniform(10.0, 18.0))
                    collar_center = _point(
                        center,
                        theta,
                        (-1.0 if rng.random() < 0.5 else 1.0) * half_l * rng.uniform(0.62, 0.90),
                        rng.uniform(-half_w * 0.25, half_w * 0.25),
                        size,
                    )
                    collar_poly = _polygon(
                        collar_center,
                        theta,
                        (
                            (-collar_length * 0.50, -collar_width * 0.34),
                            (collar_length * 0.42, -collar_width * 0.50),
                            (collar_length * 0.50, collar_width * 0.26),
                            (-collar_length * 0.36, collar_width * 0.50),
                        ),
                        size,
                    )
                    color, tier = _weighted_tier(
                        rng,
                        FROST_PALETTE,
                        (0.08, 0.14, 0.20, 0.22, 0.18, 0.11, 0.05, 0.02),
                    )
                    _paint_mark(layers["frost collars"], collar_poly, color, int(rng.integers(128, 191)), tier)
                    _mark(geometry, "frost collars", max(collar_length, collar_width))

                if rng.random() < 0.15:
                    end_length = float(rng.uniform(8.0, 13.0))
                    end_width = float(rng.uniform(8.0, 11.0))
                    end_center = _point(
                        center,
                        theta,
                        (-1.0 if rng.random() < 0.5 else 1.0) * half_l * rng.uniform(0.72, 0.94),
                        rng.uniform(-half_w * 0.30, half_w * 0.30),
                        size,
                    )
                    color, tier = _weighted_tier(
                        rng,
                        FROST_PALETTE,
                        (0.02, 0.04, 0.08, 0.13, 0.19, 0.22, 0.20, 0.12),
                    )
                    _paint_mark(
                        layers["clipped fiber ends"],
                        _strip(end_center, theta + rng.uniform(-0.30, 0.30), end_length, end_width, size, rng.uniform(-0.24, 0.24)),
                        color,
                        int(rng.integers(164, 226)),
                        tier,
                    )
                    _mark(geometry, "clipped fiber ends", max(end_length, end_width))

                if rng.random() < 0.16:
                    bead_diameter = float(rng.uniform(8.0, 14.0))
                    bead_center = _point(
                        center,
                        theta,
                        rng.uniform(-half_l * 0.55, half_l * 0.55),
                        side * rng.uniform(half_w * 0.65, half_w + 5.0),
                        size,
                    )
                    bead_poly = _polygon(
                        bead_center,
                        theta + rng.uniform(-1.0, 1.0),
                        (
                            (-bead_diameter * 0.50, -bead_diameter * 0.08),
                            (-bead_diameter * 0.18, -bead_diameter * 0.48),
                            (bead_diameter * 0.38, -bead_diameter * 0.36),
                            (bead_diameter * 0.50, bead_diameter * 0.12),
                            (bead_diameter * 0.10, bead_diameter * 0.48),
                            (-bead_diameter * 0.42, bead_diameter * 0.34),
                        ),
                        size,
                    )
                    color, tier = _tiered(rng, PRISM_PALETTE, low=1)
                    _paint_mark(layers["faceted air beads"], bead_poly, color, int(rng.integers(107, 181)), tier)
                    _mark(geometry, "faceted trapped-air beads", bead_diameter)

                if rng.random() < 0.23:
                    notch_length = float(rng.uniform(8.0, 15.0))
                    notch_width = float(rng.uniform(8.0, min(12.0, notch_length)))
                    notch_center = _point(
                        center,
                        theta,
                        rng.uniform(-half_l * 0.46, half_l * 0.46),
                        -side * rng.uniform(0.0, half_w * 0.52),
                        size,
                    )
                    notch_poly = _polygon(
                        notch_center,
                        theta + side * rng.uniform(0.18, 0.62),
                        (
                            (-notch_length * 0.50, -notch_width * 0.12),
                            (notch_length * 0.18, -notch_width * 0.50),
                            (notch_length * 0.50, notch_width * 0.08),
                            (-notch_length * 0.12, notch_width * 0.50),
                        ),
                        size,
                    )
                    notch_color = (int(rng.integers(4, 18)), int(rng.integers(8, 24)), int(rng.integers(16, 38)))
                    notch_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _paint_mark(layers["delamination notches"], notch_poly, notch_color, int(rng.integers(186, 246)), notch_tier)
                    _mark(geometry, "delamination notches", notch_length)

                if rng.random() < 0.22:
                    cut_length = float(rng.uniform(10.0, 24.0))
                    cut_center = _point(
                        center,
                        theta,
                        rng.uniform(-half_l * 0.42, half_l * 0.42),
                        rng.uniform(-half_w * 0.40, half_w * 0.40),
                        size,
                    )
                    cut_theta = theta + side * rng.uniform(0.54, 1.16)
                    cut_color = (int(rng.integers(1, 10)), int(rng.integers(3, 15)), int(rng.integers(8, 25)))
                    cut_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _paint_mark(
                        layers["black occlusion cuts"],
                        _strip(cut_center, cut_theta, cut_length, 8.0, size, rng.uniform(-0.20, 0.20)),
                        cut_color,
                        int(rng.integers(205, 256)),
                        cut_tier,
                    )
                    _mark(geometry, "black occlusion cuts", cut_length)

            # A weld is a compact irregular bridge between nearby short fibers,
            # not a repeated X or a radial/star node.
            if rng.random() < 0.36:
                weld_length = float(rng.uniform(9.0, 16.0))
                weld_width = float(rng.uniform(8.0, 14.0))
                weld_center = _point(
                    bundle_center,
                    bundle_theta,
                    rng.uniform(-14.0, 14.0),
                    rng.uniform(-12.0, 12.0),
                    size,
                )
                weld_poly = _polygon(
                    weld_center,
                    bundle_theta + rng.uniform(-0.65, 0.65),
                    (
                        (-weld_length * 0.50, -weld_width * 0.12),
                        (-weld_length * 0.18, -weld_width * 0.50),
                        (weld_length * 0.46, -weld_width * 0.34),
                        (weld_length * 0.50, weld_width * 0.18),
                        (weld_length * 0.02, weld_width * 0.50),
                        (-weld_length * 0.42, weld_width * 0.34),
                    ),
                    size,
                )
                color, tier = _tiered(rng, WELD_PALETTE)
                _paint_mark(layers["crossing welds"], weld_poly, color, int(rng.integers(155, 228)), tier)
                _mark(geometry, "crossing welds", max(weld_length, weld_width))

    masks = {name: layer[2] for name, layer in layers.items()}
    resin = masks["graphite resin facets"]
    fibers = masks["translucent fiber cores"]
    prisms = masks["prismatic splinters"]
    frost = masks["frost collars"]
    ends = masks["clipped fiber ends"]
    air = masks["faceted air beads"]
    welds = masks["crossing welds"]
    notches = masks["delamination notches"]
    cuts = masks["black occlusion cuts"]

    fiber_halo = np.clip(blur(0.88 * fibers + 0.72 * prisms + 0.46 * welds, 24.0, size), 0.0, 1.0)
    frost_haze = np.clip(blur(0.84 * frost + 0.52 * air + 0.35 * ends, 18.0, size), 0.0, 1.0)
    resin_depth = np.clip(blur(resin, 28.0, size), 0.0, 1.0)
    occlusion_shadow = np.clip(blur(0.82 * cuts + 0.66 * notches, 16.0, size), 0.0, 1.0)

    yy = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    studio_falloff = 0.91 + 0.09 * (1.0 - np.abs(yy - 0.48) * 2.0)
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = (0.014 + 0.022 * resin_depth + 0.056 * fiber_halo + 0.022 * frost_haze) * studio_falloff
    paint[..., 1] = (0.023 + 0.045 * resin_depth + 0.114 * fiber_halo + 0.071 * frost_haze) * studio_falloff
    paint[..., 2] = (0.044 + 0.086 * resin_depth + 0.205 * fiber_halo + 0.146 * frost_haze - 0.018 * occlusion_shadow) * studio_falloff

    for family, strength in (
        ("graphite resin facets", 0.76),
        ("translucent fiber cores", 0.95),
        ("prismatic splinters", 0.96),
        ("frost collars", 0.90),
        ("faceted air beads", 0.82),
        ("crossing welds", 0.94),
        ("delamination notches", 0.96),
        ("black occlusion cuts", 0.99),
        ("clipped fiber ends", 1.00),
    ):
        _composite(paint, layers[family], strength)

    paint += blur(prisms + welds, 11.0, size)[..., None] * np.asarray((0.026, 0.076, 0.120), np.float32)
    paint += blur(frost + ends, 9.0, size)[..., None] * np.asarray((0.055, 0.071, 0.086), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    rupture = np.maximum.reduce((frost, ends, notches, cuts))
    intact_resin = np.clip(
        blur(resin, 13.0, size)
        + 0.52 * blur(fibers, 12.0, size)
        + 0.68 * blur(welds, 10.0, size)
        + 0.42 * blur(air, 11.0, size)
        - 0.92 * blur(rupture, 8.0, size),
        0.0,
        1.0,
    )

    m_score = (
        0.09
        + 1.43 * prisms
        + 1.29 * ends
        + 1.12 * welds
        + 0.42 * fibers
        - 0.61 * frost
        - 0.58 * cuts
        - 0.42 * notches
        + 0.22 * blur(prisms + ends + welds, 14.0, size)
    )
    r_score = (
        0.15
        + 1.31 * frost
        + 1.22 * notches
        + 1.16 * cuts
        + 0.72 * ends
        + 0.46 * air
        - 0.78 * welds
        - 0.58 * fibers
        - 0.34 * intact_resin
        + 0.24 * blur(frost + notches + cuts, 16.0, size)
    )
    c_score = (
        0.17
        # SPB-105 / 2026-08-27 owner verdict: keep Cc independently causal,
        # not a mechanical inverse of roughness. Clear survives in intact resin,
        # crossing welds, trapped-air skins, and fibre faces; breaks only reduce
        # it locally. R/Cc correlation moved -0.868094 -> -0.625230.
        + 1.40 * intact_resin
        + 1.20 * welds
        + 0.90 * air
        + 0.80 * fibers
        + 0.40 * prisms
        + 0.20 * ends
        - 0.30 * cuts
        - 0.20 * notches
        + 0.15 * frost
        + 0.20 * blur(resin + welds + air, 22.0, size)
    )
    spec = pack_material(m_score, r_score, c_score)

    evidence_masks = {
        "graphite/blue-black resin facets": resin,
        "fractured translucent fibers": fibers,
        "prismatic splinters": prisms,
        "frost collars": frost,
        "clipped fiber ends": ends,
        "faceted trapped-air beads": air,
        "crossing welds": welds,
        "delamination notches": notches,
        "black occlusion cuts": cuts,
        "intact resin/fiber pools": intact_resin,
    }
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=evidence_masks,
        geometry=_geometry(geometry),
        carrier="deep graphite/blue-black resin packed with fractured translucent white and ice-blue microfibers",
        material_story={
            "M": "prismatic splinters, clipped clean ends, and compact crossing welds expose the brightest glass",
            "R": "frost collars, delamination notches, black occlusion cuts, and clipped damage raise roughness",
            "Cc": "intact resin/fiber pools, compact welds, and faceted trapped-air pockets retain coat while rupture loses it",
        },
        vetoes=(
            "snowflakes",
            "icicles",
            "long hairs or scratches",
            "webs",
            "starbursts",
            "confetti",
            "repeated X marks",
            "generic white-noise carpet",
            "macro voids",
        ),
    )


def _determinism_audit(seed: int, first: PilotResult) -> dict[str, object]:
    start = time.perf_counter()
    second = build_cryoglass_fiber(seed=seed, size=first.paint.shape[0])
    rerun_seconds = time.perf_counter() - start
    paint_equal = bool(np.array_equal(first.paint, second.paint))
    spec_equal = bool(np.array_equal(first.spec, second.spec))
    return {
        "paint_byte_identical": paint_equal,
        "spec_byte_identical": spec_equal,
        "rerun_seconds": round(float(rerun_seconds), 6),
        "pass": bool(paint_equal and spec_equal and rerun_seconds <= 3.0),
    }


def _edge_continuity_audit(paint: np.ndarray) -> dict[str, object]:
    rgb = np.clip(np.asarray(paint, np.float32), 0.0, 1.0)
    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    gx = np.pad(np.abs(np.diff(luma, axis=1)), ((0, 0), (0, 1)))
    gy = np.pad(np.abs(np.diff(luma, axis=0)), ((0, 1), (0, 0)))
    gradient = np.hypot(gx, gy)
    band = max(4, luma.shape[0] // 64)
    edge_gradient = np.concatenate(
        (gradient[:band].ravel(), gradient[-band:].ravel(), gradient[:, :band].ravel(), gradient[:, -band:].ravel())
    )
    edge_luma = np.concatenate((luma[:band].ravel(), luma[-band:].ravel(), luma[:, :band].ravel(), luma[:, -band:].ravel()))
    ratio = float(edge_gradient.mean() / max(float(gradient.mean()), 1e-7))
    dark_fraction = float(np.mean(edge_luma < 0.012))
    return {
        "edge_to_global_gradient_ratio": round(ratio, 6),
        "edge_dark_void_fraction": round(dark_fraction, 6),
        "pass": bool(0.45 <= ratio <= 1.55 and dark_fraction < 0.05),
    }


def _picker_audit(paint: np.ndarray) -> dict[str, object]:
    rgb = np.clip(np.asarray(paint, np.float32), 0.0, 1.0)
    sizes: dict[str, dict[str, object]] = {}
    passed = True
    for picker_size in (128, 64):
        picker = cv2.resize(rgb, (picker_size, picker_size), interpolation=cv2.INTER_AREA)
        luma = picker[..., 0] * 0.2126 + picker[..., 1] * 0.7152 + picker[..., 2] * 0.0722
        chroma = np.max(picker, axis=2) - np.min(picker, axis=2)
        luma_std = float(luma.std())
        chroma_std = float(chroma.std())
        contrast_span = float(np.quantile(luma, 0.95) - np.quantile(luma, 0.05))
        size_pass = bool(luma_std >= 0.025 and chroma_std >= 0.025 and contrast_span >= 0.070)
        sizes[str(picker_size)] = {
            "luma_std": round(luma_std, 6),
            "chroma_std": round(chroma_std, 6),
            "luma_p95_minus_p05": round(contrast_span, 6),
            "pass": size_pass,
        }
        passed = passed and size_pass
    return {"sizes": sizes, "pass": bool(passed)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render isolated Cryoglass Fiber owner-review evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_neon_oil_slick_reset_work/cryoglass_fiber"),
        help="isolated evidence directory",
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args()

    result = timed_result(build_cryoglass_fiber, seed=args.seed)
    manifest = render_evidence(result, args.output, native_size=NATIVE)
    working_material = material_stats(result.spec)
    geometry = manifest["geometry_stats"]
    coverage = manifest["causal_mask_coverage"]
    correlations = working_material["correlation"]
    unique_mrc_triples = int(np.unique(result.spec.reshape(-1, 3), axis=0).shape[0])
    edge_continuity = _edge_continuity_audit(result.paint)
    picker_survival = _picker_audit(result.paint)
    visible_family_coverage_count = sum(
        value >= 0.005 for name, value in coverage.items() if name != "intact resin/fiber pools"
    )
    mechanical_gates = {
        "eight_plus_anatomy_families": bool(geometry["family_count"] >= 8),
        "eight_plus_family_masks_above_half_percent": bool(visible_family_coverage_count >= 8),
        "all_geometry_8_to_32_native": bool(geometry["fine_8_32_fraction"] == 1.0),
        "eight_tiers_each": bool(all(value == 8 for value in working_material["tier_count"].values())),
        "material_std_at_least_30": bool(all(value >= 30.0 for value in working_material["std"].values())),
        "channels_not_copied_or_inverse": bool(all(abs(value) < 0.90 for value in correlations.values())),
        "many_material_triples": bool(unique_mrc_triples >= 128),
        "edge_continuity": bool(edge_continuity["pass"]),
        "picker_survival_128_and_64": bool(picker_survival["pass"]),
    }
    audit = {
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "display_name": DISPLAY_NAME,
        "builder_seconds": round(float(result.elapsed_seconds), 6),
        "under_three_seconds": bool(result.elapsed_seconds <= 3.0),
        "determinism": _determinism_audit(args.seed, result),
        "material_stats_working": working_material,
        "unique_mrc_triples": unique_mrc_triples,
        "geometry": geometry,
        "causal_mask_coverage": coverage,
        "visible_family_coverage_count": int(visible_family_coverage_count),
        "edge_continuity": edge_continuity,
        "picker_survival": picker_survival,
        "mechanical_gates": mechanical_gates,
        "mechanical_gates_pass": bool(all(mechanical_gates.values())),
        "official_m7": None,
        "official_m7_note": "Unwired isolated pilot; no registry/workbook record exists, so no composite is fabricated.",
    }
    (args.output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0 if audit["under_three_seconds"] and audit["determinism"]["pass"] and audit["mechanical_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
