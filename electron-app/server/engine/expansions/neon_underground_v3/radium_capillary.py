"""Radium Capillary — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset tick RC-P2 / owner directive 2026-08-27: replace the
rejected lazy Neon field with one dense automotive material whose paint and
three spec channels share causal fine anatomy. Radium Capillary is mineral
seepage through black porous ceramic, never slime, a drip/vein network,
lightning, biological worms, circuit traces, or generic green noise. It remains
unwired pending owner review. Owner-eye repair verdict: RC-P1's mechanically
rich but near-uniform quadrilaterals collapsed into green confetti; RC-P2 makes
graphite facets, teal salt beds, tapered deposits, bright pressure lips,
faceted menisci, and angular rupture visibly separate. Movement RC-P1 -> RC-P2:
ceramic coverage 0.177341 -> 0.329187, 64px luma std 0.072824 -> 0.082347,
and maximum absolute M/R/Cc correlation 0.528839 -> 0.445264.
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


FINISH_ID = "neon_toxic_green"
DISPLAY_NAME = "Radium Capillary"
DEFAULT_SEED = 0xA4D1_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
PROVENANCE = {
    "ticket": "SPB-105",
    "date": "2026-08-27",
    "tick": "RC-P2",
    "verdict": (
        "RC-P1's mechanically rich but near-uniform quadrilaterals collapsed into green confetti; "
        "RC-P2 separates the ceramic, salt, capillary, meniscus, crust, and rupture silhouettes."
    ),
    "metric_movement": {
        "ceramic_mask_coverage": [0.177341, 0.329187],
        "picker_64_luma_std": [0.072824, 0.082347],
        "max_abs_material_correlation": [0.528839, 0.445264],
    },
}


Layer = tuple[np.ndarray, np.ndarray, np.ndarray]


def _layer(size: int) -> Layer:
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


def _poly(
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
    return _poly(
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


def _draw(
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


CERAMIC_PALETTE = np.asarray(
    (
        (4, 11, 9),
        (6, 17, 13),
        (8, 24, 17),
        (11, 32, 21),
        (15, 41, 27),
        (20, 51, 32),
        (27, 63, 39),
        (36, 76, 47),
    ),
    np.uint8,
)
CAPILLARY_PALETTE = np.asarray(
    (
        (7, 41, 14),
        (9, 61, 18),
        (11, 83, 22),
        (14, 108, 26),
        (21, 136, 30),
        (37, 168, 37),
        (72, 204, 50),
        (133, 244, 76),
    ),
    np.uint8,
)
LIP_PALETTE = np.asarray(
    (
        (24, 83, 20),
        (37, 108, 22),
        (54, 135, 25),
        (76, 163, 29),
        (103, 190, 35),
        (137, 214, 45),
        (177, 235, 63),
        (222, 251, 102),
    ),
    np.uint8,
)
MENISCUS_PALETTE = np.asarray(
    (
        (65, 106, 23),
        (83, 133, 27),
        (105, 160, 31),
        (132, 187, 37),
        (162, 211, 47),
        (193, 232, 65),
        (222, 246, 95),
        (246, 255, 151),
    ),
    np.uint8,
)
ACID_PALETTE = np.asarray(
    (
        (75, 78, 6),
        (99, 104, 7),
        (126, 131, 8),
        (154, 158, 10),
        (181, 184, 13),
        (207, 207, 18),
        (231, 228, 29),
        (250, 246, 57),
    ),
    np.uint8,
)
SALT_PALETTE = np.asarray(
    (
        (3, 43, 40),
        (4, 58, 55),
        (5, 75, 70),
        (7, 94, 87),
        (10, 114, 103),
        (15, 137, 121),
        (24, 161, 140),
        (40, 188, 161),
    ),
    np.uint8,
)


def build_radium_capillary(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic radium-mineral seep laminate."""
    if int(size) != WORK:
        raise ValueError(f"Radium Capillary is authored at WORK={WORK}, got {size}")
    rng = seeded(seed)
    layers: dict[str, Layer] = {
        "porous ceramic facets": _layer(size),
        "shadow salts": _layer(size),
        "broken porous pockets": _layer(size),
        "short capillaries": _layer(size),
        "mineral lips": _layer(size),
        "meniscus beads": _layer(size),
        "acid crust": _layer(size),
        "branch stubs": _layer(size),
        "dry gaps": _layer(size),
        "occlusion pits": _layer(size),
    }
    geometry: Counter[tuple[str, float]] = Counter()

    # Continuous black-green ceramic platelets provide material density without
    # generic noise, grids, or a repeated hex/cell grammar.
    ceramic_cell = max(5, int(round(25.0 * size / NATIVE)))
    for gy, y0 in enumerate(range(-ceramic_cell, size + ceramic_cell, ceramic_cell)):
        for gx, x0 in enumerate(range(-ceramic_cell, size + ceramic_cell, ceramic_cell)):
            if rng.random() < 0.07:
                continue
            center = np.asarray(
                (
                    x0 + rng.uniform(-0.47, 0.47) * ceramic_cell,
                    y0 + rng.uniform(-0.47, 0.47) * ceramic_cell,
                ),
                np.float32,
            )
            theta = float(rng.uniform(-math.pi, math.pi))
            length = float(rng.uniform(14.0, 27.0))
            width = float(rng.uniform(9.0, 18.0))
            half_l, half_w = length * 0.5, width * 0.5
            variant = int(rng.integers(0, 3))
            if variant == 0:
                offsets = (
                    (-half_l, -half_w * 0.22),
                    (-half_l * 0.30, -half_w),
                    (half_l, -half_w * 0.34),
                    (half_l * 0.54, half_w),
                    (-half_l * 0.62, half_w * 0.58),
                )
            elif variant == 1:
                offsets = (
                    (-half_l, -half_w * 0.58),
                    (half_l * 0.44, -half_w),
                    (half_l, half_w * 0.14),
                    (half_l * 0.08, half_w),
                    (-half_l * 0.72, half_w * 0.48),
                )
            else:
                offsets = (
                    (-half_l, -half_w * 0.08),
                    (-half_l * 0.14, -half_w),
                    (half_l, -half_w * 0.10),
                    (half_l * 0.32, half_w),
                    (-half_l * 0.76, half_w * 0.45),
                )
            color, tier = _tiered(rng, CERAMIC_PALETTE)
            _draw(layers["porous ceramic facets"], _poly(center, theta, offsets, size), color, int(rng.integers(103, 181)), tier)
            _mark(geometry, "black porous ceramic facets", length)

    # Seep colonies gather short deposits into local mineral histories; no
    # authored segment is long enough to become a drip, vein, or circuit trace.
    seep_cell = max(12, int(round(94.0 * size / NATIVE)))
    margin = int(round(32.0 * size / NATIVE))
    for gy, base_y in enumerate(range(-seep_cell // 2, size + seep_cell, seep_cell)):
        for gx, base_x in enumerate(range(-seep_cell // 2, size + seep_cell, seep_cell)):
            center = np.asarray(
                (
                    base_x + rng.uniform(-0.44, 0.44) * seep_cell,
                    base_y + rng.uniform(-0.44, 0.44) * seep_cell,
                ),
                np.float32,
            )
            if center[0] < -margin or center[1] < -margin or center[0] > size + margin or center[1] > size + margin:
                continue
            domain_x, domain_y = gx // 4, gy // 4
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 5 + domain_y * 3) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -math.pi + (domain_hash % 1013) / 1012.0 * math.tau
            colony_theta = float(domain_theta + rng.normal(0.0, 0.31))

            if rng.random() < 0.88:
                salt_length = float(rng.uniform(24.0, 32.0))
                salt_width = float(rng.uniform(13.0, 22.0))
                salt_center = _point(center, colony_theta, rng.uniform(-7.0, 7.0), rng.uniform(-9.0, 9.0), size)
                salt_poly = _poly(
                    salt_center,
                    colony_theta + rng.uniform(-0.32, 0.32),
                    (
                        (-salt_length * 0.50, -salt_width * 0.18),
                        (-salt_length * 0.12, -salt_width * 0.50),
                        (salt_length * 0.50, -salt_width * 0.24),
                        (salt_length * 0.34, salt_width * 0.50),
                        (-salt_length * 0.42, salt_width * 0.38),
                    ),
                    size,
                )
                color, tier = _tiered(rng, SALT_PALETTE)
                _draw(layers["shadow salts"], salt_poly, color, int(rng.integers(132, 205)), tier)
                _mark(geometry, "blue-green shadow salts", salt_length)

            if rng.random() < 0.72:
                pocket_length = float(rng.uniform(20.0, 30.0))
                pocket_width = float(rng.uniform(12.0, 21.0))
                pocket_center = _point(center, colony_theta, rng.uniform(-10.0, 10.0), rng.uniform(-10.0, 10.0), size)
                pocket_poly = _poly(
                    pocket_center,
                    colony_theta + rng.uniform(-0.8, 0.8),
                    (
                        (-pocket_length * 0.50, -pocket_width * 0.08),
                        (-pocket_length * 0.18, -pocket_width * 0.50),
                        (pocket_length * 0.44, -pocket_width * 0.35),
                        (pocket_length * 0.50, pocket_width * 0.18),
                        (pocket_length * 0.04, pocket_width * 0.50),
                        (-pocket_length * 0.42, pocket_width * 0.34),
                    ),
                    size,
                )
                pocket_color = (int(rng.integers(2, 15)), int(rng.integers(9, 29)), int(rng.integers(8, 25)))
                pocket_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                _draw(layers["broken porous pockets"], pocket_poly, pocket_color, int(rng.integers(201, 250)), pocket_tier)
                _mark(geometry, "broken porous pockets", pocket_length)

            segment_count = int(rng.integers(5, 10))
            for segment_index in range(segment_count):
                theta = float(colony_theta + rng.normal(0.0, 0.42))
                cap_center = _point(
                    center,
                    colony_theta,
                    rng.uniform(-29.0, 29.0),
                    rng.uniform(-24.0, 24.0),
                    size,
                )
                length = float(rng.uniform(14.0, 29.0))
                width = float(rng.uniform(8.0, 11.5))
                color, tier = _weighted_tier(
                    rng,
                    CAPILLARY_PALETTE,
                    (0.15, 0.18, 0.20, 0.18, 0.14, 0.09, 0.045, 0.015),
                )
                capillary_poly = _poly(
                    cap_center,
                    theta,
                    (
                        (-length * 0.50, -width * 0.12),
                        (-length * 0.25, -width * 0.50),
                        (length * 0.18, -width * 0.36),
                        (length * 0.50, -width * 0.08),
                        (length * 0.31, width * 0.50),
                        (-length * 0.39, width * 0.34),
                    ),
                    size,
                )
                _draw(
                    layers["short capillaries"],
                    capillary_poly,
                    color,
                    int(rng.integers(123, 201)),
                    tier,
                )
                _mark(geometry, "short capillary deposits", length)

                # Only a minority forms a two-leg kink; there is no recoverable
                # long path and no repeated worm/vein silhouette.
                if segment_index == 0 and rng.random() < 0.36:
                    second_length = float(rng.uniform(9.0, 16.0))
                    side = -1.0 if rng.random() < 0.5 else 1.0
                    joint = _point(cap_center, theta, length * 0.44, 0.0, size)
                    turn_theta = theta + side * rng.uniform(0.48, 1.08)
                    second_center = _point(joint, turn_theta, second_length * 0.50, 0.0, size)
                    color_2, tier_2 = _tiered(rng, CAPILLARY_PALETTE)
                    second_width = float(rng.uniform(8.0, 9.5))
                    second_poly = _poly(
                        second_center,
                        turn_theta,
                        (
                            (-second_length * 0.50, -second_width * 0.14),
                            (-second_length * 0.16, -second_width * 0.50),
                            (second_length * 0.50, -second_width * 0.18),
                            (second_length * 0.30, second_width * 0.50),
                            (-second_length * 0.40, second_width * 0.32),
                        ),
                        size,
                    )
                    _draw(
                        layers["short capillaries"],
                        second_poly,
                        color_2,
                        int(rng.integers(132, 207)),
                        tier_2,
                    )
                    _mark(geometry, "short kinked capillary legs", second_length)

                side = -1.0 if rng.random() < 0.5 else 1.0
                if rng.random() < 0.43:
                    lip_length = float(rng.uniform(12.0, 22.0))
                    lip_center = _point(
                        cap_center,
                        theta,
                        rng.uniform(-length * 0.34, length * 0.34),
                        side * width * rng.uniform(0.30, 0.58),
                        size,
                    )
                    lip_color, lip_tier = _tiered(rng, LIP_PALETTE)
                    lip_width = float(rng.uniform(8.0, 9.5))
                    lip_poly = _poly(
                        lip_center,
                        theta + rng.uniform(-0.18, 0.18),
                        (
                            (-lip_length * 0.50, lip_width * 0.18),
                            (-lip_length * 0.18, -lip_width * 0.50),
                            (lip_length * 0.50, -lip_width * 0.12),
                            (lip_length * 0.24, lip_width * 0.50),
                        ),
                        size,
                    )
                    _draw(
                        layers["mineral lips"],
                        lip_poly,
                        lip_color,
                        int(rng.integers(171, 239)),
                        lip_tier,
                    )
                    _mark(geometry, "mineral lips", lip_length)

                if rng.random() < 0.30:
                    bead_diameter = float(rng.uniform(12.0, 18.0))
                    bead_center = _point(
                        cap_center,
                        theta,
                        (-1.0 if rng.random() < 0.5 else 1.0) * length * rng.uniform(0.34, 0.48),
                        rng.uniform(-width * 0.25, width * 0.25),
                        size,
                    )
                    bead_poly = _poly(
                        bead_center,
                        theta + rng.uniform(-0.9, 0.9),
                        (
                            (-bead_diameter * 0.50, -bead_diameter * 0.06),
                            (-bead_diameter * 0.16, -bead_diameter * 0.48),
                            (bead_diameter * 0.42, -bead_diameter * 0.34),
                            (bead_diameter * 0.50, bead_diameter * 0.14),
                            (bead_diameter * 0.08, bead_diameter * 0.48),
                            (-bead_diameter * 0.42, bead_diameter * 0.32),
                        ),
                        size,
                    )
                    bead_color, bead_tier = _tiered(rng, MENISCUS_PALETTE)
                    _draw(layers["meniscus beads"], bead_poly, bead_color, int(rng.integers(185, 246)), bead_tier)
                    _mark(geometry, "bright meniscus beads", bead_diameter)

                if rng.random() < 0.31:
                    stub_length = float(rng.uniform(9.0, 16.0))
                    stub_joint = _point(cap_center, theta, rng.uniform(-length * 0.30, length * 0.30), 0.0, size)
                    stub_theta = theta + side * rng.uniform(0.58, 1.12)
                    stub_center = _point(stub_joint, stub_theta, stub_length * 0.50, 0.0, size)
                    stub_color, stub_tier = _tiered(rng, SALT_PALETTE)
                    _draw(
                        layers["branch stubs"],
                        _strip(stub_center, stub_theta, stub_length, 8.0, size, rng.uniform(-0.18, 0.18)),
                        stub_color,
                        int(rng.integers(137, 207)),
                        stub_tier,
                    )
                    _mark(geometry, "finite branch stubs", stub_length)

                if rng.random() < 0.34:
                    crust_count = int(rng.integers(1, 3))
                    for _ in range(crust_count):
                        crust_length = float(rng.uniform(8.0, 14.0))
                        crust_width = float(rng.uniform(8.0, min(11.0, crust_length)))
                        crust_center = _point(
                            cap_center,
                            theta,
                            rng.uniform(-length * 0.46, length * 0.46),
                            -side * rng.uniform(width * 0.18, width + 3.0),
                            size,
                        )
                        crust_poly = _poly(
                            crust_center,
                            theta + rng.uniform(-1.0, 1.0),
                            (
                                (-crust_length * 0.50, -crust_width * 0.08),
                                (-crust_length * 0.10, -crust_width * 0.50),
                                (crust_length * 0.50, -crust_width * 0.18),
                                (crust_length * 0.22, crust_width * 0.50),
                                (-crust_length * 0.42, crust_width * 0.34),
                            ),
                            size,
                        )
                        crust_color, crust_tier = _tiered(rng, ACID_PALETTE)
                        _draw(layers["acid crust"], crust_poly, crust_color, int(rng.integers(153, 222)), crust_tier)
                        _mark(geometry, "acid-yellow crust flakes", crust_length)

                if rng.random() < 0.23:
                    gap_length = float(rng.uniform(8.0, 13.0))
                    gap_center = _point(cap_center, theta, rng.uniform(-length * 0.28, length * 0.28), 0.0, size)
                    gap_color = (int(rng.integers(2, 12)), int(rng.integers(8, 23)), int(rng.integers(5, 17)))
                    gap_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(
                        layers["dry gaps"],
                        _strip(gap_center, theta + rng.uniform(-0.35, 0.35), gap_length, 8.0, size, rng.uniform(-0.25, 0.25)),
                        gap_color,
                        int(rng.integers(194, 248)),
                        gap_tier,
                    )
                    _mark(geometry, "dry mineral gaps", gap_length)

                if rng.random() < 0.24:
                    pit_diameter = float(rng.uniform(8.0, 14.0))
                    pit_center = _point(
                        cap_center,
                        theta,
                        rng.uniform(-length * 0.48, length * 0.48),
                        rng.uniform(-width * 0.85, width * 0.85),
                        size,
                    )
                    pit_poly = _poly(
                        pit_center,
                        theta + rng.uniform(-1.1, 1.1),
                        (
                            (-pit_diameter * 0.50, -pit_diameter * 0.06),
                            (-pit_diameter * 0.12, -pit_diameter * 0.48),
                            (pit_diameter * 0.46, -pit_diameter * 0.28),
                            (pit_diameter * 0.50, pit_diameter * 0.16),
                            (pit_diameter * 0.04, pit_diameter * 0.48),
                            (-pit_diameter * 0.42, pit_diameter * 0.30),
                        ),
                        size,
                    )
                    pit_color = (int(rng.integers(0, 8)), int(rng.integers(3, 15)), int(rng.integers(3, 12)))
                    pit_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(layers["occlusion pits"], pit_poly, pit_color, int(rng.integers(215, 256)), pit_tier)
                    _mark(geometry, "dark occlusion pits", pit_diameter)

    masks = {name: layer[2] for name, layer in layers.items()}
    ceramic = masks["porous ceramic facets"]
    salts = masks["shadow salts"]
    pockets = masks["broken porous pockets"]
    capillaries = masks["short capillaries"]
    lips = masks["mineral lips"]
    meniscus = masks["meniscus beads"]
    crust = masks["acid crust"]
    stubs = masks["branch stubs"]
    gaps = masks["dry gaps"]
    pits = masks["occlusion pits"]

    seep_history = np.clip(blur(0.84 * capillaries + 0.70 * lips + 0.52 * meniscus, 25.0, size), 0.0, 1.0)
    salt_haze = np.clip(blur(0.88 * salts + 0.46 * crust, 19.0, size), 0.0, 1.0)
    ceramic_depth = np.clip(blur(ceramic, 28.0, size), 0.0, 1.0)
    rupture_shadow = np.clip(blur(0.78 * pockets + 0.74 * gaps + 0.88 * pits, 16.0, size), 0.0, 1.0)

    yy = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    studio_falloff = 0.91 + 0.09 * (1.0 - np.abs(yy - 0.47) * 2.0)
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = (0.011 + 0.020 * ceramic_depth + 0.038 * seep_history + 0.010 * salt_haze) * studio_falloff
    paint[..., 1] = (0.024 + 0.054 * ceramic_depth + 0.182 * seep_history + 0.099 * salt_haze - 0.012 * rupture_shadow) * studio_falloff
    paint[..., 2] = (0.017 + 0.038 * ceramic_depth + 0.052 * seep_history + 0.112 * salt_haze - 0.010 * rupture_shadow) * studio_falloff

    for family, strength in (
        ("porous ceramic facets", 0.78),
        ("shadow salts", 0.88),
        ("broken porous pockets", 0.95),
        ("short capillaries", 0.96),
        ("mineral lips", 0.97),
        ("branch stubs", 0.89),
        ("acid crust", 0.94),
        ("meniscus beads", 1.00),
        ("dry gaps", 0.98),
        ("occlusion pits", 1.00),
    ):
        _composite(paint, layers[family], strength)

    paint += blur(lips + meniscus, 10.0, size)[..., None] * np.asarray((0.055, 0.160, 0.030), np.float32)
    paint += blur(salts, 14.0, size)[..., None] * np.asarray((0.000, 0.065, 0.073), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    rupture = np.maximum.reduce((pockets, crust, gaps, pits))
    wet_pool = np.clip(
        blur(capillaries + 0.72 * lips + 0.58 * meniscus + 0.42 * salts, 12.0, size)
        - 0.62 * blur(gaps + pits, 8.0, size),
        0.0,
        1.0,
    )
    intact_ceramic = np.clip(
        blur(ceramic, 13.0, size)
        + 0.52 * blur(salts, 12.0, size)
        + 0.42 * wet_pool
        - 0.80 * blur(rupture, 8.0, size),
        0.0,
        1.0,
    )

    m_score = (
        0.08
        + 1.39 * lips
        + 1.25 * meniscus
        + 0.83 * crust
        + 0.36 * capillaries
        + 0.28 * salts
        - 0.58 * pockets
        - 0.46 * pits
        + 0.22 * blur(lips + meniscus + crust, 14.0, size)
    )
    r_score = (
        0.15
        + 1.23 * pockets
        + 1.10 * crust
        + 1.05 * gaps
        + 0.88 * pits
        + 0.38 * stubs
        + 0.24 * salts
        - 0.61 * meniscus
        - 0.37 * capillaries
        + 0.21 * blur(rupture + stubs, 16.0, size)
    )
    c_score = (
        0.17
        + 1.12 * intact_ceramic
        + 0.82 * wet_pool
        + 0.74 * salts
        + 0.46 * meniscus
        + 0.22 * capillaries
        - 0.77 * pits
        - 0.68 * gaps
        - 0.50 * crust
        - 0.39 * pockets
        + 0.16 * blur(ceramic + salts, 22.0, size)
    )
    spec = pack_material(m_score, r_score, c_score)

    evidence_masks = {
        "black porous ceramic facets": ceramic,
        "short kinked capillary deposits": capillaries,
        "mineral lips": lips,
        "bright meniscus beads": meniscus,
        "broken porous pockets": pockets,
        "acid-yellow crust": crust,
        "blue-green shadow salts": salts,
        "finite branch stubs": stubs,
        "dry mineral gaps": gaps,
        "dark occlusion pits": pits,
        "wet mineral pools": wet_pool,
        "intact ceramic/salt pools": intact_ceramic,
    }
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=evidence_masks,
        geometry=_geometry(geometry),
        carrier="black porous ceramic with dense radium-green capillary mineral deposits",
        material_story={
            "M": "mineral lips, bright meniscus beads, and acid crust expose the strongest radium deposit",
            "R": "broken porous pockets, dry gaps, acid crust, pits, and branch damage raise roughness",
            "Cc": "intact ceramic, wet mineral pools, blue-green salts, and meniscus deposits retain coat while rupture loses it",
        },
        vetoes=(
            "slime or drips",
            "veins",
            "lightning",
            "long lines",
            "biological worms",
            "circuit traces",
            "hexes or grids",
            "generic green noise",
            "macro voids",
        ),
    )


def _determinism_audit(seed: int, first: PilotResult) -> dict[str, object]:
    start = time.perf_counter()
    second = build_radium_capillary(seed=seed, size=first.paint.shape[0])
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
    dark_fraction = float(np.mean(edge_luma < 0.010))
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
        size_pass = bool(luma_std >= 0.025 and chroma_std >= 0.030 and contrast_span >= 0.070)
        sizes[str(picker_size)] = {
            "luma_std": round(luma_std, 6),
            "chroma_std": round(chroma_std, 6),
            "luma_p95_minus_p05": round(contrast_span, 6),
            "pass": size_pass,
        }
        passed = passed and size_pass
    return {"sizes": sizes, "pass": bool(passed)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render isolated Radium Capillary owner-review evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_neon_oil_slick_reset_work/radium_capillary"),
        help="isolated evidence directory",
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args()

    result = timed_result(build_radium_capillary, seed=args.seed)
    manifest = render_evidence(result, args.output, native_size=NATIVE)
    manifest["provenance"] = PROVENANCE
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    working_material = material_stats(result.spec)
    geometry = manifest["geometry_stats"]
    coverage = manifest["causal_mask_coverage"]
    correlations = working_material["correlation"]
    unique_mrc_triples = int(np.unique(result.spec.reshape(-1, 3), axis=0).shape[0])
    edge_continuity = _edge_continuity_audit(result.paint)
    picker_survival = _picker_audit(result.paint)
    visible_family_coverage_count = sum(
        value >= 0.005
        for name, value in coverage.items()
        if name not in {"wet mineral pools", "intact ceramic/salt pools"}
    )
    mechanical_gates = {
        "eight_plus_anatomy_families": bool(geometry["family_count"] >= 8),
        "eight_plus_family_masks_above_half_percent": bool(visible_family_coverage_count >= 8),
        "all_geometry_8_to_32_native": bool(geometry["fine_8_32_fraction"] == 1.0),
        "eight_tiers_each": bool(all(value == 8 for value in working_material["tier_count"].values())),
        "material_std_at_least_30": bool(all(value >= 30.0 for value in working_material["std"].values())),
        "all_abs_correlations_under_0_80": bool(all(abs(value) < 0.80 for value in correlations.values())),
        "many_material_triples": bool(unique_mrc_triples >= 128),
        "edge_continuity": bool(edge_continuity["pass"]),
        "picker_survival_128_and_64": bool(picker_survival["pass"]),
    }
    audit = {
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "display_name": DISPLAY_NAME,
        "provenance": PROVENANCE,
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
