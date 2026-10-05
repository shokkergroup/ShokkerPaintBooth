"""Pulse Ablation — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset tick PA-P2 / owner directive 2026-08-27: replace the
rejected literal/lazy Neon treatment with one causal, fine-feature automotive
material. Pulse Ablation is black coated metal carrying dense, finite laser
ablation strike histories. It is never a web, ray field, starburst, lightning,
grid, crosshair, beam illustration, or generic scratch noise. The existing ID
remains unwired pending owner review; therefore no official M7 is fabricated.
Owner-eye repair verdict: PA-P1's low-energy shoulders collapsed toward dark
platelets and scattered sequins; PA-P2 visibly separates cyan and magenta heat
displacement across each dark finite trench while reducing detached clutter.
Movement PA-P1 -> PA-P2: 64px chroma std 0.020037 -> 0.037266, 64px luma std
0.039386 -> 0.056653, and maximum absolute M/R/Cc correlation 0.691005 ->
0.629949.
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


FINISH_ID = "neon2_laser_web"
DISPLAY_NAME = "Pulse Ablation"
DEFAULT_SEED = 0xAB1A_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)


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
    points = [center + tangent * (along * scale) + normal * (across * scale) for along, across in offsets_native]
    return np.rint(points).astype(np.int32)


def _tapered(
    center: np.ndarray,
    theta: float,
    length_native: float,
    width_native: float,
    size: int,
    bite: float = 0.0,
) -> np.ndarray:
    half_l = float(length_native) * 0.5
    half_w = float(width_native) * 0.5
    return _poly(
        center,
        theta,
        (
            (-half_l, -half_w * (0.28 + bite)),
            (-half_l * 0.30, -half_w),
            (half_l * 0.44, -half_w * 0.60),
            (half_l, -half_w * 0.06),
            (half_l * 0.34, half_w * 0.48),
            (-half_l * 0.58, half_w),
        ),
        size,
    )


def _diamond(
    center: np.ndarray,
    theta: float,
    length_native: float,
    width_native: float,
    size: int,
) -> np.ndarray:
    half_l = float(length_native) * 0.5
    half_w = float(width_native) * 0.5
    return _poly(
        center,
        theta,
        ((-half_l, 0.0), (0.0, -half_w), (half_l, 0.0), (0.0, half_w)),
        size,
    )


def _draw(layer: Layer, polygon: np.ndarray, color: Sequence[int], opacity: int, tier: float) -> None:
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
    weights: Sequence[float] | None = None,
) -> tuple[tuple[int, int, int], float]:
    if weights is None:
        index = int(rng.integers(0, 8))
    else:
        probabilities = np.asarray(weights, np.float64)
        probabilities /= probabilities.sum()
        index = int(rng.choice(8, p=probabilities))
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


COATING_PALETTE = np.asarray(
    (
        (4, 7, 11),
        (7, 11, 17),
        (10, 16, 24),
        (14, 22, 32),
        (19, 29, 41),
        (25, 37, 50),
        (33, 47, 61),
        (43, 59, 73),
    ),
    np.uint8,
)
TRENCH_PALETTE = np.asarray(
    (
        (10, 5, 10),
        (18, 7, 17),
        (28, 10, 25),
        (40, 13, 34),
        (55, 17, 44),
        (72, 22, 55),
        (94, 29, 68),
        (120, 39, 84),
    ),
    np.uint8,
)
CYAN_PALETTE = np.asarray(
    (
        (3, 36, 45),
        (4, 52, 64),
        (6, 71, 85),
        (9, 93, 109),
        (14, 119, 137),
        (24, 150, 169),
        (49, 190, 210),
        (101, 235, 247),
    ),
    np.uint8,
)
MAGENTA_PALETTE = np.asarray(
    (
        (38, 4, 32),
        (57, 6, 48),
        (79, 8, 66),
        (105, 11, 87),
        (135, 16, 111),
        (169, 26, 139),
        (207, 48, 173),
        (243, 91, 211),
    ),
    np.uint8,
)
BEAD_PALETTE = np.asarray(
    (
        (30, 19, 29),
        (48, 27, 44),
        (69, 38, 61),
        (94, 51, 79),
        (122, 68, 99),
        (154, 89, 122),
        (190, 118, 151),
        (228, 158, 191),
    ),
    np.uint8,
)
OXIDE_PALETTE = np.asarray(
    (
        (17, 23, 27),
        (25, 34, 39),
        (35, 47, 52),
        (49, 61, 65),
        (67, 76, 78),
        (89, 94, 89),
        (115, 115, 101),
        (145, 140, 116),
    ),
    np.uint8,
)
HOT_PALETTE = np.asarray(
    (
        (72, 79, 86),
        (91, 102, 111),
        (113, 128, 138),
        (138, 157, 167),
        (166, 188, 197),
        (195, 216, 223),
        (223, 238, 243),
        (247, 253, 255),
    ),
    np.uint8,
)


def build_pulse_ablation(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic coated-metal ablation laminate."""
    if int(size) != WORK:
        raise ValueError(f"Pulse Ablation is authored at WORK={WORK}, got {size}")
    rng = seeded(seed)
    layers: dict[str, Layer] = {
        "coated metal facets": _layer(size),
        "scorched microtrenches": _layer(size),
        "cyan displaced rims": _layer(size),
        "magenta displaced rims": _layer(size),
        "re-solidified beads": _layer(size),
        "clipped crater mouths": _layer(size),
        "oxide freckles": _layer(size),
        "ejecta chips": _layer(size),
        "interrupted pulse gaps": _layer(size),
        "white-hot pinpoints": _layer(size),
        "carbonized pits": _layer(size),
    }
    geometry: Counter[tuple[str, float]] = Counter()

    # The coating is a continuous jittered platelet sheet. Individual facets
    # remain fine and irregular, so density does not become a grid or noise map.
    coating_cell = max(5, int(round(27.0 * size / NATIVE)))
    for y0 in range(-coating_cell, size + coating_cell, coating_cell):
        for x0 in range(-coating_cell, size + coating_cell, coating_cell):
            if rng.random() < 0.055:
                continue
            center = np.asarray(
                (x0 + rng.uniform(-0.47, 0.47) * coating_cell, y0 + rng.uniform(-0.47, 0.47) * coating_cell),
                np.float32,
            )
            theta = float(rng.uniform(-math.pi, math.pi))
            length = float(rng.uniform(14.0, 27.0))
            width = float(rng.uniform(9.0, 18.0))
            half_l, half_w = length * 0.5, width * 0.5
            offsets = (
                (-half_l, -half_w * rng.uniform(0.12, 0.42)),
                (-half_l * rng.uniform(0.18, 0.42), -half_w),
                (half_l, -half_w * rng.uniform(0.18, 0.48)),
                (half_l * rng.uniform(0.38, 0.70), half_w),
                (-half_l * rng.uniform(0.52, 0.82), half_w * rng.uniform(0.42, 0.72)),
            )
            color, tier = _tiered(rng, COATING_PALETTE)
            _draw(layers["coated metal facets"], _poly(center, theta, offsets, size), color, int(rng.integers(101, 179)), tier)
            _mark(geometry, "black coated-metal facets", length)

    # Each strike colony is finite and locally disordered. No segment exceeds
    # 30px, and adjacent cells use unrelated directions so no web/ray survives.
    strike_cell = max(12, int(round(96.0 * size / NATIVE)))
    margin = int(round(32.0 * size / NATIVE))
    for gy, base_y in enumerate(range(-strike_cell // 2, size + strike_cell, strike_cell)):
        for gx, base_x in enumerate(range(-strike_cell // 2, size + strike_cell, strike_cell)):
            anchor = np.asarray(
                (base_x + rng.uniform(-0.43, 0.43) * strike_cell, base_y + rng.uniform(-0.43, 0.43) * strike_cell),
                np.float32,
            )
            if anchor[0] < -margin or anchor[1] < -margin or anchor[0] > size + margin or anchor[1] > size + margin:
                continue
            domain_x, domain_y = gx // 4, gy // 4
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 7 + domain_y * 11) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_theta = -math.pi + (domain_hash % 1019) / 1018.0 * math.tau
            strike_theta = float(base_theta + rng.normal(0.0, 0.46))

            # A clipped angular cavity gives the packet a physical origin
            # without creating a repeated circular crater grammar.
            if rng.random() < 0.68:
                mouth_length = float(rng.uniform(18.0, 30.0))
                mouth_width = float(rng.uniform(12.0, 21.0))
                mouth_center = _point(anchor, strike_theta, rng.uniform(-6.0, 6.0), rng.uniform(-7.0, 7.0), size)
                half_l, half_w = mouth_length * 0.5, mouth_width * 0.5
                mouth_poly = _poly(
                    mouth_center,
                    strike_theta + rng.uniform(-0.55, 0.55),
                    (
                        (-half_l, -half_w * 0.12),
                        (-half_l * 0.30, -half_w),
                        (half_l * 0.48, -half_w * 0.54),
                        (half_l, half_w * 0.05),
                        (half_l * 0.24, half_w),
                        (-half_l * 0.66, half_w * 0.48),
                    ),
                    size,
                )
                mouth_color = (int(rng.integers(1, 10)), int(rng.integers(3, 13)), int(rng.integers(7, 19)))
                mouth_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                _draw(layers["clipped crater mouths"], mouth_poly, mouth_color, int(rng.integers(204, 252)), mouth_tier)
                _mark(geometry, "clipped angular crater mouths", mouth_length)

            trench_count = int(rng.integers(4, 8))
            for trench_index in range(trench_count):
                theta = float(strike_theta + rng.normal(0.0, 0.28))
                trench_center = _point(
                    anchor,
                    strike_theta,
                    rng.uniform(-28.0, 28.0),
                    rng.uniform(-24.0, 24.0),
                    size,
                )
                length = float(rng.uniform(14.0, 30.0))
                width = float(rng.uniform(8.0, 11.5))
                trench_color, trench_tier = _tiered(
                    rng,
                    TRENCH_PALETTE,
                    (0.05, 0.09, 0.14, 0.18, 0.19, 0.16, 0.12, 0.07),
                )
                _draw(
                    layers["scorched microtrenches"],
                    _tapered(trench_center, theta, length, width, size, rng.uniform(-0.08, 0.16)),
                    trench_color,
                    int(rng.integers(178, 239)),
                    trench_tier,
                )
                _mark(geometry, "short scorched microtrenches", length)

                # Heat moves to opposite trench shoulders. The two chroma
                # families are separate wedges rather than an outlined tube.
                side = -1.0 if rng.random() < 0.5 else 1.0
                if rng.random() < 0.88:
                    rim_length = float(rng.uniform(14.0, min(29.0, length + 1.0)))
                    rim_width = float(rng.uniform(8.0, 9.5))
                    rim_center = _point(
                        trench_center,
                        theta,
                        rng.uniform(-length * 0.22, length * 0.22),
                        side * rng.uniform(width * 0.78, width * 1.08),
                        size,
                    )
                    rim_color, rim_tier = _tiered(
                        rng,
                        CYAN_PALETTE,
                        (0.02, 0.04, 0.08, 0.13, 0.18, 0.21, 0.20, 0.14),
                    )
                    _draw(
                        layers["cyan displaced rims"],
                        _tapered(rim_center, theta + rng.uniform(-0.14, 0.14), rim_length, rim_width, size, 0.08),
                        rim_color,
                        int(rng.integers(178, 241)),
                        rim_tier,
                    )
                    _mark(geometry, "displaced cyan heat rims", rim_length)

                if rng.random() < 0.86:
                    rim_length = float(rng.uniform(14.0, min(29.0, length + 1.0)))
                    rim_width = float(rng.uniform(8.0, 9.5))
                    rim_center = _point(
                        trench_center,
                        theta,
                        rng.uniform(-length * 0.22, length * 0.22),
                        -side * rng.uniform(width * 0.78, width * 1.10),
                        size,
                    )
                    rim_color, rim_tier = _tiered(
                        rng,
                        MAGENTA_PALETTE,
                        (0.02, 0.04, 0.08, 0.13, 0.18, 0.21, 0.20, 0.14),
                    )
                    _draw(
                        layers["magenta displaced rims"],
                        _tapered(rim_center, theta + rng.uniform(-0.14, 0.14), rim_length, rim_width, size, -0.02),
                        rim_color,
                        int(rng.integers(179, 242)),
                        rim_tier,
                    )
                    _mark(geometry, "displaced magenta heat rims", rim_length)

                if rng.random() < 0.34:
                    bead_length = float(rng.uniform(10.0, 17.0))
                    bead_width = float(rng.uniform(8.0, min(13.0, bead_length)))
                    bead_center = _point(
                        trench_center,
                        theta,
                        (-1.0 if rng.random() < 0.5 else 1.0) * length * rng.uniform(0.34, 0.48),
                        rng.uniform(-width * 0.45, width * 0.45),
                        size,
                    )
                    bead_color, bead_tier = _tiered(rng, BEAD_PALETTE)
                    _draw(
                        layers["re-solidified beads"],
                        _diamond(bead_center, theta + rng.uniform(-0.8, 0.8), bead_length, bead_width, size),
                        bead_color,
                        int(rng.integers(177, 240)),
                        bead_tier,
                    )
                    _mark(geometry, "faceted re-solidified beads", bead_length)

                if rng.random() < 0.24:
                    gap_length = float(rng.uniform(8.0, 14.0))
                    gap_center = _point(trench_center, theta, rng.uniform(-length * 0.28, length * 0.28), 0.0, size)
                    gap_color = (int(rng.integers(1, 9)), int(rng.integers(2, 10)), int(rng.integers(4, 14)))
                    gap_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(
                        layers["interrupted pulse gaps"],
                        _tapered(gap_center, theta + math.pi * 0.5 + rng.uniform(-0.22, 0.22), gap_length, 8.0, size, 0.12),
                        gap_color,
                        int(rng.integers(211, 255)),
                        gap_tier,
                    )
                    _mark(geometry, "interrupted pulse gaps", gap_length)

                if rng.random() < 0.15:
                    hot_size = float(rng.uniform(8.0, 11.0))
                    hot_center = _point(
                        trench_center,
                        theta,
                        (-1.0 if rng.random() < 0.5 else 1.0) * length * rng.uniform(0.36, 0.48),
                        rng.uniform(-width * 0.30, width * 0.30),
                        size,
                    )
                    hot_color, hot_tier = _tiered(rng, HOT_PALETTE, (0.02, 0.04, 0.07, 0.11, 0.16, 0.20, 0.20, 0.20))
                    _draw(
                        layers["white-hot pinpoints"],
                        _diamond(hot_center, theta + rng.uniform(-1.0, 1.0), hot_size, 8.0, size),
                        hot_color,
                        int(rng.integers(211, 256)),
                        hot_tier,
                    )
                    _mark(geometry, "white-hot terminal pinpoints", hot_size)

                if rng.random() < 0.20:
                    pit_size = float(rng.uniform(9.0, 16.0))
                    pit_center = _point(
                        trench_center,
                        theta,
                        rng.uniform(-length * 0.46, length * 0.46),
                        rng.uniform(-width * 0.90, width * 0.90),
                        size,
                    )
                    pit_color = (int(rng.integers(0, 7)), int(rng.integers(1, 8)), int(rng.integers(2, 10)))
                    pit_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(
                        layers["carbonized pits"],
                        _poly(
                            pit_center,
                            theta + rng.uniform(-1.0, 1.0),
                            (
                                (-pit_size * 0.50, -pit_size * 0.08),
                                (-pit_size * 0.16, -pit_size * 0.46),
                                (pit_size * 0.46, -pit_size * 0.28),
                                (pit_size * 0.50, pit_size * 0.14),
                                (pit_size * 0.06, pit_size * 0.48),
                                (-pit_size * 0.42, pit_size * 0.30),
                            ),
                            size,
                        ),
                        pit_color,
                        int(rng.integers(220, 256)),
                        pit_tier,
                    )
                    _mark(geometry, "dark carbonized pits", pit_size)

            # Oxide freckles and ejecta are local to the strike but do not all
            # nest into the trench silhouette, preventing a repeated stamp.
            oxide_count = int(rng.integers(1, 4))
            for _ in range(oxide_count):
                oxide_size = float(rng.uniform(8.0, 12.0))
                oxide_center = _point(
                    anchor,
                    strike_theta,
                    rng.uniform(-31.0, 31.0),
                    rng.uniform(-28.0, 28.0),
                    size,
                )
                oxide_color, oxide_tier = _tiered(rng, OXIDE_PALETTE)
                _draw(
                    layers["oxide freckles"],
                    _diamond(oxide_center, rng.uniform(-math.pi, math.pi), oxide_size, 8.0, size),
                    oxide_color,
                    int(rng.integers(133, 207)),
                    oxide_tier,
                )
                _mark(geometry, "oxide microfreckles", oxide_size)

            ejecta_count = int(rng.integers(1, 3))
            for ejecta_index in range(ejecta_count):
                ejecta_length = float(rng.uniform(8.0, 15.0))
                ejecta_width = float(rng.uniform(8.0, min(11.0, ejecta_length)))
                ejecta_center = _point(
                    anchor,
                    strike_theta,
                    rng.uniform(-34.0, 34.0),
                    rng.uniform(-31.0, 31.0),
                    size,
                )
                palette = CYAN_PALETTE if (ejecta_index + gx + gy) % 2 == 0 else MAGENTA_PALETTE
                ejecta_color, ejecta_tier = _tiered(rng, palette)
                _draw(
                    layers["ejecta chips"],
                    _poly(
                        ejecta_center,
                        rng.uniform(-math.pi, math.pi),
                        (
                            (-ejecta_length * 0.50, -ejecta_width * 0.10),
                            (-ejecta_length * 0.06, -ejecta_width * 0.50),
                            (ejecta_length * 0.50, -ejecta_width * 0.18),
                            (ejecta_length * 0.22, ejecta_width * 0.50),
                            (-ejecta_length * 0.38, ejecta_width * 0.30),
                        ),
                        size,
                    ),
                    ejecta_color,
                    int(rng.integers(146, 220)),
                    ejecta_tier,
                )
                _mark(geometry, "angular ejecta chips", ejecta_length)

    masks = {name: layer[2] for name, layer in layers.items()}
    coating = masks["coated metal facets"]
    trenches = masks["scorched microtrenches"]
    cyan = masks["cyan displaced rims"]
    magenta = masks["magenta displaced rims"]
    beads = masks["re-solidified beads"]
    craters = masks["clipped crater mouths"]
    oxide = masks["oxide freckles"]
    ejecta = masks["ejecta chips"]
    gaps = masks["interrupted pulse gaps"]
    hot = masks["white-hot pinpoints"]
    pits = masks["carbonized pits"]

    strike_heat = np.clip(blur(0.78 * cyan + 0.78 * magenta + 0.52 * hot, 22.0, size), 0.0, 1.0)
    carbon_haze = np.clip(blur(0.74 * trenches + 0.62 * craters + 0.86 * pits, 17.0, size), 0.0, 1.0)
    coating_depth = np.clip(blur(coating, 24.0, size), 0.0, 1.0)
    ejecta_haze = np.clip(blur(0.62 * oxide + 0.54 * ejecta, 13.0, size), 0.0, 1.0)

    yy = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    studio_falloff = 0.91 + 0.09 * (1.0 - np.abs(yy - 0.48) * 2.0)
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = (0.014 + 0.050 * coating_depth + 0.083 * strike_heat + 0.035 * ejecta_haze - 0.012 * carbon_haze) * studio_falloff
    paint[..., 1] = (0.019 + 0.061 * coating_depth + 0.066 * strike_heat + 0.043 * ejecta_haze - 0.013 * carbon_haze) * studio_falloff
    paint[..., 2] = (0.027 + 0.078 * coating_depth + 0.109 * strike_heat + 0.055 * ejecta_haze - 0.010 * carbon_haze) * studio_falloff

    for family, strength in (
        ("coated metal facets", 0.62),
        ("clipped crater mouths", 0.97),
        ("scorched microtrenches", 0.96),
        ("cyan displaced rims", 1.00),
        ("magenta displaced rims", 1.00),
        ("oxide freckles", 0.79),
        ("ejecta chips", 0.91),
        ("re-solidified beads", 0.98),
        ("interrupted pulse gaps", 1.00),
        ("white-hot pinpoints", 1.00),
        ("carbonized pits", 1.00),
    ):
        _composite(paint, layers[family], strength)

    paint += blur(cyan, 10.0, size)[..., None] * np.asarray((0.000, 0.110, 0.142), np.float32)
    paint += blur(magenta, 10.0, size)[..., None] * np.asarray((0.142, 0.000, 0.108), np.float32)
    paint += blur(hot, 8.0, size)[..., None] * np.asarray((0.090, 0.105, 0.116), np.float32)
    # SPB-105 / 2026-08-27 owner verdict: preserve finite strike scale while
    # restoring saturated heat displacement and picker contrast. Official
    # isolated M7 before calibration: 69.8 (M6 saturation miss); rerun below.
    hsv = cv2.cvtColor(np.clip(paint, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.10, 0.0, 1.0)
    paint = np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 1.15, 0.0, 1.0)

    rupture = np.maximum.reduce((trenches, craters, gaps, pits))
    heat_reflow = np.clip(
        blur(0.76 * cyan + 0.72 * magenta + 0.84 * beads + 0.54 * hot, 11.0, size)
        - 0.58 * blur(gaps + pits, 8.0, size),
        0.0,
        1.0,
    )
    intact_coat = np.clip(
        blur(coating, 13.0, size)
        + 0.43 * blur(cyan + magenta, 11.0, size)
        + 0.38 * heat_reflow
        - 0.82 * blur(rupture, 8.0, size),
        0.0,
        1.0,
    )

    m_score = (
        0.07
        + 1.26 * craters
        + 1.02 * trenches
        + 0.88 * ejecta
        + 0.73 * beads
        + 1.18 * hot
        + 0.30 * cyan
        - 0.66 * pits
        - 0.30 * gaps
        + 0.19 * blur(craters + trenches + ejecta, 14.0, size)
    )
    r_score = (
        0.14
        + 1.29 * pits
        + 1.08 * trenches
        + 0.96 * oxide
        + 0.92 * gaps
        + 0.49 * ejecta
        + 0.33 * craters
        - 0.67 * beads
        - 0.58 * hot
        - 0.30 * magenta
        + 0.20 * blur(pits + oxide + gaps, 15.0, size)
    )
    c_score = (
        0.16
        + 1.12 * intact_coat
        + 0.88 * heat_reflow
        + 0.68 * cyan
        + 0.54 * magenta
        + 0.48 * beads
        - 0.86 * craters
        - 0.74 * trenches
        - 0.70 * gaps
        - 0.62 * pits
        - 0.27 * oxide
        + 0.15 * blur(coating + cyan + magenta, 20.0, size)
    )
    spec = pack_material(m_score, r_score, c_score)

    evidence_masks = {
        "black coated-metal facets": coating,
        "short scorched microtrenches": trenches,
        "displaced cyan heat rims": cyan,
        "displaced magenta heat rims": magenta,
        "faceted re-solidified beads": beads,
        "clipped angular crater mouths": craters,
        "oxide microfreckles": oxide,
        "angular ejecta chips": ejecta,
        "interrupted pulse gaps": gaps,
        "white-hot terminal pinpoints": hot,
        "dark carbonized pits": pits,
        "registered heat-reflow pools": heat_reflow,
        "intact coated-metal pools": intact_coat,
    }
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=evidence_masks,
        geometry=_geometry(geometry),
        carrier="black coated metal packed with finite cyan/magenta pulse-ablation strike histories",
        material_story={
            "M": "ablated crater mouths and trenches expose metal while ejecta, re-solidified beads, and pinpoints retain metallic response",
            "R": "carbonized pits, scorched trenches, oxide freckles, and interrupted gaps raise roughness while reflow beads and pinpoints smooth it",
            "Cc": "intact coating and registered heat reflow retain clearcoat while crater, trench, gap, pit, and oxide rupture remove it",
        },
        vetoes=(
            "webs or spiderwebs",
            "long rays or lines",
            "starbursts",
            "lightning",
            "grids",
            "crosshairs",
            "laser-beam imagery",
            "generic scratch noise",
            "macro voids",
        ),
    )


def _determinism_audit(seed: int, first: PilotResult) -> dict[str, object]:
    start = time.perf_counter()
    second = build_pulse_ablation(seed=seed, size=first.paint.shape[0])
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
    parser = argparse.ArgumentParser(description="Render isolated Pulse Ablation owner-review evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_neon_oil_slick_reset_work/pulse_ablation"),
        help="isolated evidence directory",
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args()

    result = timed_result(build_pulse_ablation, seed=args.seed)
    manifest = render_evidence(result, args.output, native_size=NATIVE)
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
        if name not in {"registered heat-reflow pools", "intact coated-metal pools"}
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
    provenance = {
        "ticket": "SPB-105",
        "date": "2026-08-27",
        "tick": "PA-P2",
        "verdict": (
            "PA-P1's low-energy shoulders collapsed toward dark platelets and scattered sequins; PA-P2 visibly "
            "separates cyan and magenta heat displacement across each finite trench while reducing detached clutter."
        ),
        "metric_movement": {
            "picker_64_chroma_std": [0.020037, picker_survival["sizes"]["64"]["chroma_std"]],
            "picker_64_luma_std": [0.039386, picker_survival["sizes"]["64"]["luma_std"]],
            "max_abs_material_correlation": [
                0.691005,
                round(max(abs(value) for value in correlations.values()), 6),
            ],
        },
    }
    manifest["provenance"] = provenance
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    audit = {
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "display_name": DISPLAY_NAME,
        "provenance": provenance,
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
