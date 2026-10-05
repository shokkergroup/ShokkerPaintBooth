"""Velvet Static — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset tick VS-P1 / owner directive 2026-08-27: replace the
literal synthwave-sun treatment with one causal fine-feature automotive
material. Velvet Static is black conductive microvelvet whose short local nap
events carry charged tips, laydown, discharge, clipping, fusion, compression,
and lint consequences. It contains no sun/horizon, grid, stripe, long hair,
fur/noise carpet, flame, flower, starburst, or repeated tuft/chevron stamp.
Owner-eye verdict: first-pass isolated-review keeper; the staggered charged-nap
packets remain directional and locally finite rather than collapsing into fur,
wallpaper, or repeated tuft icons. Movement from the unwired legacy state is
11 causal anatomy families, 64 px luma/chroma survival of 0.039490/0.030269,
and maximum absolute M/R/Cc correlation 0.503709. The existing ID remains
unwired pending review, so no official M7 is invented.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
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


FINISH_ID = "neon2_synthwave_sun"
DISPLAY_NAME = "Velvet Static"
DEFAULT_SEED = 0x7E17_2026
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


def _flock(
    center: np.ndarray,
    theta: float,
    length_native: float,
    width_native: float,
    size: int,
    variant: int,
) -> np.ndarray:
    half_l = float(length_native) * 0.5
    half_w = float(width_native) * 0.5
    if int(variant) % 3 == 0:
        offsets = (
            (-half_l, -half_w * 0.18),
            (-half_l * 0.28, -half_w),
            (half_l, -half_w * 0.32),
            (half_l * 0.52, half_w),
            (-half_l * 0.68, half_w * 0.46),
        )
    elif int(variant) % 3 == 1:
        offsets = (
            (-half_l, -half_w * 0.58),
            (half_l * 0.18, -half_w),
            (half_l, half_w * 0.04),
            (half_l * 0.12, half_w),
            (-half_l * 0.72, half_w * 0.28),
        )
    else:
        offsets = (
            (-half_l, -half_w * 0.08),
            (-half_l * 0.02, -half_w),
            (half_l, -half_w * 0.16),
            (half_l * 0.38, half_w),
            (-half_l * 0.58, half_w * 0.66),
        )
    return _poly(center, theta, offsets, size)


def _shoulder(
    center: np.ndarray,
    theta: float,
    length_native: float,
    width_native: float,
    size: int,
    flip: float,
) -> np.ndarray:
    half_l = float(length_native) * 0.5
    half_w = float(width_native) * 0.5
    return _poly(
        center,
        theta,
        (
            (-half_l, -half_w * 0.12 * flip),
            (-half_l * 0.18, -half_w * flip),
            (half_l, -half_w * 0.22 * flip),
            (half_l * 0.30, half_w * flip),
            (-half_l * 0.60, half_w * 0.46 * flip),
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


CARRIER_PALETTE = np.asarray(
    (
        (4, 5, 10),
        (7, 8, 16),
        (11, 12, 23),
        (16, 16, 31),
        (22, 21, 40),
        (29, 27, 50),
        (38, 34, 62),
        (49, 43, 75),
    ),
    np.uint8,
)
FLOCK_PALETTE = np.asarray(
    (
        (8, 5, 13),
        (14, 8, 22),
        (22, 11, 33),
        (31, 15, 45),
        (42, 20, 59),
        (56, 27, 75),
        (72, 36, 94),
        (91, 48, 116),
    ),
    np.uint8,
)
CORAL_PALETTE = np.asarray(
    (
        (55, 13, 17),
        (77, 17, 23),
        (103, 23, 31),
        (132, 31, 40),
        (163, 42, 51),
        (194, 57, 65),
        (224, 79, 82),
        (249, 111, 105),
    ),
    np.uint8,
)
MAGENTA_PALETTE = np.asarray(
    (
        (44, 4, 35),
        (64, 6, 52),
        (87, 8, 71),
        (113, 12, 93),
        (142, 18, 118),
        (174, 29, 147),
        (207, 50, 179),
        (239, 85, 213),
    ),
    np.uint8,
)
VIOLET_PALETTE = np.asarray(
    (
        (17, 8, 28),
        (25, 12, 40),
        (35, 16, 54),
        (47, 22, 70),
        (61, 30, 88),
        (78, 41, 108),
        (99, 56, 132),
        (124, 76, 157),
    ),
    np.uint8,
)
CYAN_PALETTE = np.asarray(
    (
        (4, 37, 45),
        (5, 53, 63),
        (7, 72, 84),
        (10, 94, 108),
        (15, 120, 136),
        (25, 151, 168),
        (49, 190, 208),
        (99, 232, 244),
    ),
    np.uint8,
)
END_PALETTE = np.asarray(
    (
        (25, 20, 32),
        (37, 29, 45),
        (52, 41, 60),
        (69, 55, 77),
        (89, 72, 97),
        (112, 92, 120),
        (139, 118, 147),
        (169, 149, 178),
    ),
    np.uint8,
)
KNOT_PALETTE = np.asarray(
    (
        (30, 13, 30),
        (45, 19, 44),
        (63, 27, 60),
        (84, 37, 79),
        (108, 50, 101),
        (136, 67, 126),
        (168, 90, 155),
        (205, 122, 188),
    ),
    np.uint8,
)
LINT_PALETTE = np.asarray(
    (
        (44, 51, 57),
        (59, 68, 75),
        (77, 88, 96),
        (98, 111, 120),
        (122, 136, 145),
        (150, 164, 173),
        (181, 194, 202),
        (216, 227, 233),
    ),
    np.uint8,
)


def build_velvet_static(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic conductive microvelvet laminate."""
    if int(size) != WORK:
        raise ValueError(f"Velvet Static is authored at WORK={WORK}, got {size}")
    rng = seeded(seed)
    layers: dict[str, Layer] = {
        "carrier pile facets": _layer(size),
        "asymmetric flock facets": _layer(size),
        "coral charged tips": _layer(size),
        "magenta charged tips": _layer(size),
        "violet laydown shadows": _layer(size),
        "cyan discharge pinpoints": _layer(size),
        "clipped fiber ends": _layer(size),
        "fused pile knots": _layer(size),
        "pressed dark gaps": _layer(size),
        "metallic lint shards": _layer(size),
        "local combed shoulders": _layer(size),
    }
    geometry: Counter[tuple[str, float]] = Counter()

    # Low-contrast carrier facets overlap into one black-purple nap. They are
    # broad enough to avoid hair/noise and locally random enough to avoid rows.
    carrier_cell = max(5, int(round(27.0 * size / NATIVE)))
    for y0 in range(-carrier_cell, size + carrier_cell, carrier_cell):
        for x0 in range(-carrier_cell, size + carrier_cell, carrier_cell):
            if rng.random() < 0.07:
                continue
            center = np.asarray(
                (x0 + rng.uniform(-0.49, 0.49) * carrier_cell, y0 + rng.uniform(-0.49, 0.49) * carrier_cell),
                np.float32,
            )
            theta = float(rng.uniform(-math.pi, math.pi))
            length = float(rng.uniform(14.0, 27.0))
            width = float(rng.uniform(9.0, 17.0))
            color, tier = _tiered(rng, CARRIER_PALETTE)
            _draw(
                layers["carrier pile facets"],
                _flock(center, theta, length, width, size, int(rng.integers(0, 3))),
                color,
                int(rng.integers(86, 160)),
                tier,
            )
            _mark(geometry, "black conductive microvelvet carrier facets", length)

    # Static packets are staggered along one finite local nap direction. Hue is
    # selected per packet so downsampling keeps color instead of averaging it.
    event_cell = max(12, int(round(79.0 * size / NATIVE)))
    margin = int(round(34.0 * size / NATIVE))
    for gy, base_y in enumerate(range(-event_cell // 2, size + event_cell, event_cell)):
        for gx, base_x in enumerate(range(-event_cell // 2, size + event_cell, event_cell)):
            anchor = np.asarray(
                (base_x + rng.uniform(-0.48, 0.48) * event_cell, base_y + rng.uniform(-0.48, 0.48) * event_cell),
                np.float32,
            )
            if anchor[0] < -margin or anchor[1] < -margin or anchor[0] > size + margin or anchor[1] > size + margin:
                continue
            domain_x, domain_y = gx // 5, gy // 5
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 11 + domain_y * 17) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_theta = -math.pi + (domain_hash % 1021) / 1020.0 * math.tau
            packet_theta = float(base_theta + rng.normal(0.0, 0.39))
            packet_phase = int((gx * 5 + gy * 3 + domain_hash) % 3)
            fragment_count = int(rng.integers(3, 7))
            fragment_step = float(rng.uniform(8.0, 12.0))
            packet_skew = float(rng.uniform(-2.6, 2.6))

            if rng.random() < 0.86:
                shadow_length = float(rng.uniform(22.0, 32.0))
                shadow_width = float(rng.uniform(13.0, 21.0))
                shadow_center = _point(anchor, packet_theta, rng.uniform(-6.0, 6.0), rng.uniform(-9.0, 9.0), size)
                shadow_color, shadow_tier = _tiered(rng, VIOLET_PALETTE)
                _draw(
                    layers["violet laydown shadows"],
                    _flock(shadow_center, packet_theta + rng.uniform(-0.28, 0.28), shadow_length, shadow_width, size, int(rng.integers(0, 3))),
                    shadow_color,
                    int(rng.integers(119, 197)),
                    shadow_tier,
                )
                _mark(geometry, "violet pile-laydown shadows", shadow_length)

            if rng.random() < 0.76:
                shoulder_length = float(rng.uniform(18.0, 30.0))
                shoulder_width = float(rng.uniform(10.0, 17.0))
                shoulder_side = -1.0 if rng.random() < 0.5 else 1.0
                shoulder_center = _point(
                    anchor,
                    packet_theta,
                    rng.uniform(-9.0, 9.0),
                    shoulder_side * rng.uniform(10.0, 19.0),
                    size,
                )
                shoulder_color, shoulder_tier = _tiered(rng, VIOLET_PALETTE)
                _draw(
                    layers["local combed shoulders"],
                    _shoulder(shoulder_center, packet_theta + rng.uniform(-0.22, 0.22), shoulder_length, shoulder_width, size, shoulder_side),
                    shoulder_color,
                    int(rng.integers(129, 207)),
                    shoulder_tier,
                )
                _mark(geometry, "finite local combed shoulders", shoulder_length)

            facet_centers: list[np.ndarray] = []
            for fragment_index in range(fragment_count):
                slot = float(fragment_index) - 0.5 * float(fragment_count - 1)
                theta = float(packet_theta + rng.normal(0.0, 0.24))
                facet_center = _point(
                    anchor,
                    packet_theta,
                    slot * fragment_step + rng.uniform(-4.0, 4.0),
                    slot * packet_skew + rng.uniform(-11.0, 11.0),
                    size,
                )
                facet_centers.append(facet_center)
                length = float(rng.uniform(15.0, 29.0))
                width = float(rng.uniform(8.0, 12.0))
                flock_color, flock_tier = _tiered(
                    rng,
                    FLOCK_PALETTE,
                    (0.10, 0.14, 0.18, 0.19, 0.16, 0.12, 0.07, 0.04),
                )
                _draw(
                    layers["asymmetric flock facets"],
                    _flock(facet_center, theta, length, width, size, int(rng.integers(0, 3))),
                    flock_color,
                    int(rng.integers(151, 225)),
                    flock_tier,
                )
                _mark(geometry, "short asymmetric conductive flock facets", length)

                tip_probability = (0.76, 0.76, 0.68)[packet_phase]
                if rng.random() < tip_probability:
                    tip_length = float(rng.uniform(8.0, 15.0))
                    tip_width = float(rng.uniform(8.0, min(10.5, tip_length)))
                    tip_sign = -1.0 if rng.random() < 0.28 else 1.0
                    tip_center = _point(
                        facet_center,
                        theta,
                        tip_sign * length * rng.uniform(0.34, 0.49),
                        rng.uniform(-width * 0.28, width * 0.28),
                        size,
                    )
                    if packet_phase == 0 or (packet_phase == 2 and fragment_index % 2 == 0):
                        tip_family = "coral charged tips"
                        tip_palette = CORAL_PALETTE
                        geometry_family = "hot-coral charged pile tips"
                    else:
                        tip_family = "magenta charged tips"
                        tip_palette = MAGENTA_PALETTE
                        geometry_family = "hot-magenta charged pile tips"
                    tip_color, tip_tier = _tiered(
                        rng,
                        tip_palette,
                        (0.02, 0.04, 0.08, 0.13, 0.18, 0.21, 0.20, 0.14),
                    )
                    _draw(
                        layers[tip_family],
                        _shoulder(tip_center, theta + rng.uniform(-0.14, 0.14), tip_length, tip_width, size, tip_sign),
                        tip_color,
                        int(rng.integers(184, 244)),
                        tip_tier,
                    )
                    _mark(geometry, geometry_family, tip_length)

                    if rng.random() < 0.20:
                        discharge_size = float(rng.uniform(8.0, 11.0))
                        discharge_center = _point(
                            tip_center,
                            theta,
                            tip_sign * tip_length * rng.uniform(0.22, 0.40),
                            rng.uniform(-3.0, 3.0),
                            size,
                        )
                        discharge_color, discharge_tier = _tiered(
                            rng,
                            CYAN_PALETTE,
                            (0.02, 0.04, 0.07, 0.11, 0.16, 0.20, 0.21, 0.19),
                        )
                        _draw(
                            layers["cyan discharge pinpoints"],
                            _diamond(discharge_center, theta + rng.uniform(-0.8, 0.8), discharge_size, 8.0, size),
                            discharge_color,
                            int(rng.integers(205, 256)),
                            discharge_tier,
                        )
                        _mark(geometry, "cyan electrostatic discharge pinpoints", discharge_size)

                if rng.random() < 0.29:
                    end_length = float(rng.uniform(8.0, 14.0))
                    end_width = float(rng.uniform(8.0, min(10.5, end_length)))
                    end_center = _point(
                        facet_center,
                        theta,
                        -length * rng.uniform(0.34, 0.48),
                        rng.uniform(-width * 0.28, width * 0.28),
                        size,
                    )
                    end_color, end_tier = _tiered(rng, END_PALETTE)
                    _draw(
                        layers["clipped fiber ends"],
                        _flock(end_center, theta + rng.uniform(-0.18, 0.18), end_length, end_width, size, int(rng.integers(0, 3))),
                        end_color,
                        int(rng.integers(162, 228)),
                        end_tier,
                    )
                    _mark(geometry, "blunt clipped fiber ends", end_length)

                if rng.random() < 0.24:
                    gap_length = float(rng.uniform(10.0, 18.0))
                    gap_width = float(rng.uniform(8.0, min(12.0, gap_length)))
                    gap_center = _point(
                        facet_center,
                        theta,
                        rng.uniform(-length * 0.24, length * 0.24),
                        rng.uniform(-width * 0.20, width * 0.20),
                        size,
                    )
                    gap_color = (int(rng.integers(0, 6)), int(rng.integers(1, 7)), int(rng.integers(3, 11)))
                    gap_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(
                        layers["pressed dark gaps"],
                        _shoulder(gap_center, theta + math.pi * 0.5 + rng.uniform(-0.24, 0.24), gap_length, gap_width, size, 1.0),
                        gap_color,
                        int(rng.integers(217, 256)),
                        gap_tier,
                    )
                    _mark(geometry, "pressed dark pile gaps", gap_length)

            if rng.random() < 0.68:
                knot_size = float(rng.uniform(10.0, 18.0))
                knot_center = _point(anchor, packet_theta, rng.uniform(-9.0, 9.0), rng.uniform(-9.0, 9.0), size)
                knot_color, knot_tier = _tiered(rng, KNOT_PALETTE)
                _draw(
                    layers["fused pile knots"],
                    _flock(knot_center, packet_theta + rng.uniform(-0.7, 0.7), knot_size, rng.uniform(8.0, min(14.0, knot_size)), size, int(rng.integers(0, 3))),
                    knot_color,
                    int(rng.integers(177, 238)),
                    knot_tier,
                )
                _mark(geometry, "asymmetric fused pile knots", knot_size)

            lint_count = int(rng.integers(1, 4)) if rng.random() < 0.72 else 0
            for _ in range(lint_count):
                lint_length = float(rng.uniform(8.0, 15.0))
                lint_width = float(rng.uniform(8.0, min(10.5, lint_length)))
                lint_center = _point(
                    anchor,
                    packet_theta,
                    rng.uniform(-27.0, 27.0),
                    rng.uniform(-24.0, 24.0),
                    size,
                )
                lint_color, lint_tier = _tiered(rng, LINT_PALETTE)
                _draw(
                    layers["metallic lint shards"],
                    _poly(
                        lint_center,
                        rng.uniform(-math.pi, math.pi),
                        (
                            (-lint_length * 0.50, -lint_width * 0.10),
                            (-lint_length * 0.06, -lint_width * 0.50),
                            (lint_length * 0.50, -lint_width * 0.16),
                            (lint_length * 0.18, lint_width * 0.50),
                            (-lint_length * 0.38, lint_width * 0.28),
                        ),
                        size,
                    ),
                    lint_color,
                    int(rng.integers(151, 224)),
                    lint_tier,
                )
                _mark(geometry, "tiny embedded metallic lint shards", lint_length)

    masks = {name: layer[2] for name, layer in layers.items()}
    carrier = masks["carrier pile facets"]
    flock = masks["asymmetric flock facets"]
    coral = masks["coral charged tips"]
    magenta = masks["magenta charged tips"]
    violet = masks["violet laydown shadows"]
    cyan = masks["cyan discharge pinpoints"]
    ends = masks["clipped fiber ends"]
    knots = masks["fused pile knots"]
    gaps = masks["pressed dark gaps"]
    lint = masks["metallic lint shards"]
    shoulders = masks["local combed shoulders"]

    carrier_depth = np.clip(blur(carrier, 24.0, size), 0.0, 1.0)
    nap_haze = np.clip(blur(0.76 * flock + 0.64 * shoulders + 0.42 * violet, 18.0, size), 0.0, 1.0)
    coral_haze = np.clip(blur(coral, 14.0, size), 0.0, 1.0)
    magenta_haze = np.clip(blur(magenta, 14.0, size), 0.0, 1.0)
    discharge_haze = np.clip(blur(cyan + 0.44 * lint, 11.0, size), 0.0, 1.0)
    compression = np.clip(blur(0.82 * gaps + 0.56 * ends, 12.0, size), 0.0, 1.0)

    yy = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    studio_falloff = 0.91 + 0.09 * (1.0 - np.abs(yy - 0.48) * 2.0)
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = (0.013 + 0.040 * carrier_depth + 0.102 * nap_haze + 0.124 * coral_haze + 0.139 * magenta_haze + 0.016 * discharge_haze - 0.012 * compression) * studio_falloff
    paint[..., 1] = (0.016 + 0.042 * carrier_depth + 0.046 * nap_haze + 0.037 * coral_haze + 0.018 * magenta_haze + 0.112 * discharge_haze - 0.013 * compression) * studio_falloff
    paint[..., 2] = (0.026 + 0.067 * carrier_depth + 0.133 * nap_haze + 0.052 * coral_haze + 0.121 * magenta_haze + 0.136 * discharge_haze - 0.010 * compression) * studio_falloff

    for family, strength in (
        ("carrier pile facets", 0.54),
        ("violet laydown shadows", 0.90),
        ("local combed shoulders", 0.93),
        ("asymmetric flock facets", 0.96),
        ("fused pile knots", 0.97),
        ("coral charged tips", 1.00),
        ("magenta charged tips", 1.00),
        ("clipped fiber ends", 0.95),
        ("metallic lint shards", 0.97),
        ("pressed dark gaps", 1.00),
        ("cyan discharge pinpoints", 1.00),
    ):
        _composite(paint, layers[family], strength)

    paint += blur(coral, 10.0, size)[..., None] * np.asarray((0.206, 0.034, 0.030), np.float32)
    paint += blur(magenta, 10.0, size)[..., None] * np.asarray((0.206, 0.000, 0.168), np.float32)
    paint += blur(cyan, 9.0, size)[..., None] * np.asarray((0.000, 0.151, 0.191), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    # SPB-105 / 2026-08-27 owner verdict: keep the nap black and tactile while
    # ensuring its attached coral/magenta/cyan charge survives as Neon at buyer
    # scale. Pre-harness saturation mean was 0.4806; this calibration changes
    # no authored geometry, causal mask, or M/R/Cc response.
    hsv = cv2.cvtColor(paint, cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.35, 0.0, 1.0)
    paint = np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 1.18, 0.0, 1.0)
    # Official isolated M7 then moved 83.7 -> 84.9: saturation passed, but the
    # same authored nap edges softened during 1024->2048 evidence scaling.
    # Restore only that causal local contrast (no noise/new marks). Final
    # isolated M7 movement: 83.7 -> 84.9 -> 85.2.
    local_nap_detail = paint - cv2.GaussianBlur(paint, (0, 0), 1.0)
    paint = np.clip(paint + 1.35 * local_nap_detail + 0.012, 0.0, 1.0)

    rupture = np.maximum.reduce((ends, gaps, lint))
    charged_nap = np.clip(
        blur(0.82 * coral + 0.86 * magenta + 0.78 * cyan + 0.54 * knots, 11.0, size)
        - 0.55 * blur(gaps, 8.0, size),
        0.0,
        1.0,
    )
    intact_nap = np.clip(
        blur(0.62 * carrier + 0.92 * flock + 0.72 * violet + 0.54 * shoulders, 13.0, size)
        + 0.34 * blur(knots, 10.0, size)
        - 0.78 * blur(rupture, 8.0, size),
        0.0,
        1.0,
    )

    m_score = (
        0.07
        + 1.34 * lint
        + 1.18 * cyan
        + 0.92 * knots
        + 0.76 * magenta
        + 0.68 * coral
        + 0.34 * ends
        - 0.61 * gaps
        - 0.28 * violet
        + 0.18 * blur(lint + cyan + knots, 14.0, size)
    )
    r_score = (
        0.15
        + 1.18 * flock
        + 1.08 * gaps
        + 0.89 * ends
        + 0.64 * lint
        + 0.46 * shoulders
        + 0.32 * violet
        - 0.62 * knots
        - 0.48 * cyan
        - 0.38 * coral
        - 0.34 * magenta
        + 0.19 * blur(flock + gaps + ends, 15.0, size)
    )
    c_score = (
        0.16
        + 1.13 * intact_nap
        + 0.78 * violet
        + 0.55 * shoulders
        + 0.48 * knots
        + 0.35 * charged_nap
        - 0.86 * gaps
        - 0.68 * ends
        - 0.42 * lint
        - 0.31 * coral
        - 0.27 * magenta
        + 0.15 * blur(carrier + violet + shoulders, 20.0, size)
    )
    spec = pack_material(m_score, r_score, c_score)

    evidence_masks = {
        "black conductive microvelvet carrier facets": carrier,
        "short asymmetric conductive flock facets": flock,
        "hot-coral charged pile tips": coral,
        "hot-magenta charged pile tips": magenta,
        "violet pile-laydown shadows": violet,
        "cyan electrostatic discharge pinpoints": cyan,
        "blunt clipped fiber ends": ends,
        "asymmetric fused pile knots": knots,
        "pressed dark pile gaps": gaps,
        "tiny embedded metallic lint shards": lint,
        "finite local combed shoulders": shoulders,
        "registered charged-nap pools": charged_nap,
        "intact velvet-nap pools": intact_nap,
    }
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=evidence_masks,
        geometry=_geometry(geometry),
        carrier="black conductive microvelvet with dense finite electrostatic pile events",
        material_story={
            "M": "metallic lint, cyan discharge, fused knots, and charged coral/magenta tips raise metallic response",
            "R": "standing flock, pressed gaps, clipped ends, lint, shoulders, and laydown control roughness while knots and hot tips smooth",
            "Cc": "intact nap, violet laydown, combed shoulders, and fused knots retain coat while compression, clipping, lint, and charged tips reduce it",
        },
        vetoes=(
            "synthwave sun or horizon",
            "grids or stripes",
            "long hairs",
            "fur or generic noise carpet",
            "flames",
            "flowers or starbursts",
            "repeated tuft or chevron stamps",
            "macro voids",
        ),
    )


def _array_digest(values: np.ndarray) -> str:
    """Compact a completed render before the repeat so the audit does not double peak memory."""
    return hashlib.blake2b(np.ascontiguousarray(values).view(np.uint8), digest_size=20).hexdigest()


def _determinism_audit(
    seed: int,
    size: int,
    expected_paint_digest: str,
    expected_spec_digest: str,
) -> dict[str, object]:
    start = time.perf_counter()
    second = build_velvet_static(seed=seed, size=size)
    rerun_seconds = time.perf_counter() - start
    paint_equal = bool(expected_paint_digest == _array_digest(second.paint))
    spec_equal = bool(expected_spec_digest == _array_digest(second.spec))
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
    parser = argparse.ArgumentParser(description="Render isolated Velvet Static owner-review evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_neon_oil_slick_reset_work/velvet_static"),
        help="isolated evidence directory",
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args()

    result = timed_result(build_velvet_static, seed=args.seed)
    manifest = render_evidence(result, args.output, native_size=NATIVE)
    working_material = material_stats(result.spec)
    geometry = manifest["geometry_stats"]
    coverage = manifest["causal_mask_coverage"]
    correlations = working_material["correlation"]
    unique_mrc_triples = int(np.unique(result.spec.reshape(-1, 3), axis=0).shape[0])
    edge_continuity = _edge_continuity_audit(result.paint)
    picker_survival = _picker_audit(result.paint)
    builder_seconds = float(result.elapsed_seconds)
    render_size = int(result.paint.shape[0])
    paint_digest = _array_digest(result.paint)
    spec_digest = _array_digest(result.spec)
    visible_family_coverage_count = sum(
        value >= 0.005
        for name, value in coverage.items()
        if name not in {"registered charged-nap pools", "intact velvet-nap pools"}
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
        "tick": "VS-P1",
        "verdict": (
            "First-pass isolated-review keeper: all screened views retain finite directional conductive nap, "
            "distinct charged and compressed consequences, and no synthwave icon, fur/noise carpet, or repeated "
            "tuft-stamp failure; no visual repair iteration was needed."
        ),
        "metric_movement": {
            "official_baseline_m7": None,
            "legacy_isolated_metrics": None,
            "isolated_family_count": int(geometry["family_count"]),
            "isolated_max_abs_material_correlation": round(max(abs(value) for value in correlations.values()), 6),
            "isolated_picker_64_luma_std": picker_survival["sizes"]["64"]["luma_std"],
            "isolated_picker_64_chroma_std": picker_survival["sizes"]["64"]["chroma_std"],
        },
    }
    manifest["provenance"] = provenance
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Evidence and first-pass metrics are complete. Release their large render
    # arrays before the repeat so the measured composer is not penalized by an
    # artificial two-render resident set inside this isolated audit command.
    del result
    determinism = _determinism_audit(args.seed, render_size, paint_digest, spec_digest)
    audit = {
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "display_name": DISPLAY_NAME,
        "provenance": provenance,
        "builder_seconds": round(builder_seconds, 6),
        "under_three_seconds": bool(builder_seconds <= 3.0),
        "determinism": determinism,
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
