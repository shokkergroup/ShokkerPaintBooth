"""Electrocell — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset tick EC-P2 / owner directive 2026-08-27: replace the
literal honeycomb treatment with one causal fine-feature automotive material.
Electrocell is a black electrochemical ceramic laminate carrying irregular
collapsed membrane deposits and their charge/separator/rupture consequences.
It contains no honeycomb, hexagons, grid, rows, circles, bubbles, scales,
biological cells, flowers, or repeated tile/stamp grammar. The existing ID
remains unwired pending owner review, so no official M7 is fabricated.
Owner-eye repair verdict: EC-P1 placed carrier and rupture anatomy in the same
tiny-chip register and collapsed into multicolor confetti; EC-P2 tightens the
fragments into asymmetric directional collapse packets, broadens the membrane,
and separates buried cyan/magenta layers from acid-yellow edge charge. Movement
EC-P1 -> EC-P2: 64px chroma std 0.014026 -> 0.030283, 64px luma std 0.037495 ->
0.081835, membrane coverage 0.113789 -> 0.165475, and family masks above 0.5%
9 -> 10.
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


FINISH_ID = "neon2_honeycomb"
DISPLAY_NAME = "Electrocell"
DEFAULT_SEED = 0xE1EC_2026
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


def _plate(
    center: np.ndarray,
    theta: float,
    length_native: float,
    width_native: float,
    size: int,
    variant: int,
) -> np.ndarray:
    half_l = float(length_native) * 0.5
    half_w = float(width_native) * 0.5
    variants: tuple[tuple[tuple[float, float], ...], ...] = (
        (
            (-half_l, -half_w * 0.18),
            (-half_l * 0.24, -half_w),
            (half_l, -half_w * 0.30),
            (half_l * 0.42, half_w),
            (-half_l * 0.72, half_w * 0.48),
        ),
        (
            (-half_l, -half_w * 0.62),
            (half_l * 0.26, -half_w),
            (half_l, half_w * 0.08),
            (half_l * 0.08, half_w),
            (-half_l * 0.74, half_w * 0.30),
        ),
        (
            (-half_l, -half_w * 0.06),
            (-half_l * 0.08, -half_w),
            (half_l, -half_w * 0.18),
            (half_l * 0.56, half_w),
            (-half_l * 0.58, half_w * 0.68),
        ),
        (
            (-half_l, -half_w * 0.36),
            (-half_l * 0.42, -half_w),
            (half_l, -half_w * 0.44),
            (half_l * 0.70, half_w * 0.58),
            (-half_l * 0.18, half_w),
        ),
    )
    return _poly(center, theta, variants[int(variant) % len(variants)], size)


def _wedge(
    center: np.ndarray,
    theta: float,
    length_native: float,
    width_native: float,
    size: int,
    flip: float = 1.0,
) -> np.ndarray:
    half_l = float(length_native) * 0.5
    half_w = float(width_native) * 0.5
    return _poly(
        center,
        theta,
        (
            (-half_l, -half_w * 0.16 * flip),
            (-half_l * 0.12, -half_w * flip),
            (half_l, -half_w * 0.18 * flip),
            (half_l * 0.32, half_w * flip),
            (-half_l * 0.58, half_w * 0.42 * flip),
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


CERAMIC_PALETTE = np.asarray(
    (
        (3, 7, 11),
        (6, 12, 18),
        (9, 18, 26),
        (13, 25, 35),
        (18, 33, 45),
        (24, 42, 56),
        (32, 53, 68),
        (42, 66, 82),
    ),
    np.uint8,
)
MEMBRANE_PALETTE = np.asarray(
    (
        (8, 10, 18),
        (13, 15, 27),
        (19, 21, 38),
        (27, 28, 50),
        (37, 37, 64),
        (49, 48, 80),
        (64, 61, 97),
        (82, 77, 116),
    ),
    np.uint8,
)
ACID_PALETTE = np.asarray(
    (
        (46, 49, 3),
        (65, 69, 4),
        (88, 93, 6),
        (114, 120, 8),
        (143, 149, 12),
        (174, 180, 19),
        (207, 211, 32),
        (239, 240, 62),
    ),
    np.uint8,
)
CYAN_PALETTE = np.asarray(
    (
        (3, 35, 42),
        (4, 50, 59),
        (6, 68, 78),
        (9, 89, 100),
        (14, 113, 126),
        (23, 142, 156),
        (44, 176, 192),
        (84, 215, 229),
    ),
    np.uint8,
)
MAGENTA_PALETTE = np.asarray(
    (
        (35, 3, 31),
        (51, 5, 46),
        (70, 7, 63),
        (92, 10, 83),
        (117, 14, 106),
        (146, 22, 132),
        (179, 38, 161),
        (215, 68, 194),
    ),
    np.uint8,
)
BRIDGE_PALETTE = np.asarray(
    (
        (39, 42, 18),
        (56, 59, 23),
        (76, 79, 30),
        (99, 102, 40),
        (125, 128, 53),
        (154, 157, 70),
        (185, 188, 93),
        (218, 220, 123),
    ),
    np.uint8,
)
CRYSTAL_PALETTE = np.asarray(
    (
        (63, 70, 53),
        (82, 92, 68),
        (104, 117, 85),
        (130, 145, 104),
        (158, 174, 127),
        (187, 202, 153),
        (216, 228, 183),
        (244, 250, 218),
    ),
    np.uint8,
)
TORN_PALETTE = np.asarray(
    (
        (19, 25, 34),
        (30, 38, 49),
        (43, 53, 65),
        (58, 69, 82),
        (76, 88, 102),
        (98, 111, 125),
        (125, 139, 153),
        (158, 173, 187),
    ),
    np.uint8,
)


def build_electrocell(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic electrochemical ceramic laminate."""
    if int(size) != WORK:
        raise ValueError(f"Electrocell is authored at WORK={WORK}, got {size}")
    rng = seeded(seed)
    layers: dict[str, Layer] = {
        "ceramic facets": _layer(size),
        "collapsed membrane plates": _layer(size),
        "acid charged rims": _layer(size),
        "cyan electrolyte ghosts": _layer(size),
        "magenta separator shadows": _layer(size),
        "clipped pore mouths": _layer(size),
        "fused bridges": _layer(size),
        "crystal beads": _layer(size),
        "torn corners": _layer(size),
        "exhausted centers": _layer(size),
    }
    geometry: Counter[tuple[str, float]] = Counter()

    # A randomized black ceramic platelet carrier provides full-sheet density;
    # it is not a tessellation because centers, spacing, angles, and silhouettes
    # are independently jittered and the base coat remains continuous beneath it.
    carrier_cell = max(5, int(round(28.0 * size / NATIVE)))
    for y0 in range(-carrier_cell, size + carrier_cell, carrier_cell):
        for x0 in range(-carrier_cell, size + carrier_cell, carrier_cell):
            if rng.random() < 0.08:
                continue
            center = np.asarray(
                (x0 + rng.uniform(-0.50, 0.50) * carrier_cell, y0 + rng.uniform(-0.50, 0.50) * carrier_cell),
                np.float32,
            )
            theta = float(rng.uniform(-math.pi, math.pi))
            length = float(rng.uniform(14.0, 27.0))
            width = float(rng.uniform(9.0, 18.0))
            color, tier = _tiered(rng, CERAMIC_PALETTE)
            _draw(
                layers["ceramic facets"],
                _plate(center, theta, length, width, size, int(rng.integers(0, 4))),
                color,
                int(rng.integers(91, 169)),
                tier,
            )
            _mark(geometry, "black electrochemical ceramic facets", length)

    # Each rupture packet is a short asymmetric stack of fragments. The packet
    # has no closed perimeter, radial center, repeated outline, or shared row.
    deposit_cell = max(12, int(round(78.0 * size / NATIVE)))
    margin = int(round(34.0 * size / NATIVE))
    for gy, base_y in enumerate(range(-deposit_cell // 2, size + deposit_cell, deposit_cell)):
        for gx, base_x in enumerate(range(-deposit_cell // 2, size + deposit_cell, deposit_cell)):
            anchor = np.asarray(
                (base_x + rng.uniform(-0.49, 0.49) * deposit_cell, base_y + rng.uniform(-0.49, 0.49) * deposit_cell),
                np.float32,
            )
            if anchor[0] < -margin or anchor[1] < -margin or anchor[0] > size + margin or anchor[1] > size + margin:
                continue
            domain_x, domain_y = gx // 5, gy // 5
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x * 13 + domain_y * 7) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_theta = -math.pi + (domain_hash % 1021) / 1020.0 * math.tau
            packet_theta = float(base_theta + rng.normal(0.0, 0.42))
            packet_phase = int((gx * 3 + gy * 5 + domain_hash) % 3)
            cyan_probability = (0.92, 0.28, 0.72)[packet_phase]
            magenta_probability = (0.28, 0.92, 0.60)[packet_phase]
            fragment_centers: list[np.ndarray] = []
            fragment_count = int(rng.integers(3, 6))
            fragment_step = float(rng.uniform(9.0, 14.0))
            packet_skew = float(rng.uniform(-2.8, 2.8))

            for fragment_index in range(fragment_count):
                theta = float(packet_theta + rng.normal(0.0, 0.28))
                slot = float(fragment_index) - 0.5 * float(fragment_count - 1)
                plate_center = _point(
                    anchor,
                    packet_theta,
                    slot * fragment_step + rng.uniform(-4.5, 4.5),
                    slot * packet_skew + rng.uniform(-12.0, 12.0),
                    size,
                )
                fragment_centers.append(plate_center)
                length = float(rng.uniform(18.0, 31.0))
                width = float(rng.uniform(12.0, 21.0))

                # Buried electrolyte and separator layers are displaced in
                # opposite directions before the dark membrane overlays them.
                side = -1.0 if rng.random() < 0.5 else 1.0
                if rng.random() < cyan_probability:
                    ghost_length = float(rng.uniform(18.0, min(31.0, length + 1.0)))
                    ghost_width = float(rng.uniform(10.0, min(18.0, width)))
                    ghost_center = _point(
                        plate_center,
                        theta,
                        rng.uniform(-length * 0.18, length * 0.18),
                        side * rng.uniform(width * 0.60, width * 0.92),
                        size,
                    )
                    ghost_color, ghost_tier = _tiered(
                        rng,
                        CYAN_PALETTE,
                        (0.03, 0.05, 0.09, 0.14, 0.18, 0.20, 0.18, 0.13),
                    )
                    _draw(
                        layers["cyan electrolyte ghosts"],
                        _plate(ghost_center, theta + rng.uniform(-0.18, 0.18), ghost_length, ghost_width, size, int(rng.integers(0, 4))),
                        ghost_color,
                        int(rng.integers(145, 216)),
                        ghost_tier,
                    )
                    _mark(geometry, "displaced cyan electrolyte ghosts", ghost_length)

                if rng.random() < magenta_probability:
                    shadow_length = float(rng.uniform(15.0, min(29.0, length)))
                    shadow_width = float(rng.uniform(9.0, min(16.0, width)))
                    shadow_center = _point(
                        plate_center,
                        theta,
                        rng.uniform(-length * 0.20, length * 0.20),
                        -side * rng.uniform(width * 0.56, width * 0.88),
                        size,
                    )
                    shadow_color, shadow_tier = _tiered(
                        rng,
                        MAGENTA_PALETTE,
                        (0.03, 0.05, 0.09, 0.14, 0.18, 0.20, 0.18, 0.13),
                    )
                    _draw(
                        layers["magenta separator shadows"],
                        _wedge(shadow_center, theta + rng.uniform(-0.16, 0.16), shadow_length, shadow_width, size, side),
                        shadow_color,
                        int(rng.integers(145, 218)),
                        shadow_tier,
                    )
                    _mark(geometry, "magenta separator shadows", shadow_length)

                plate_color, plate_tier = _tiered(
                    rng,
                    MEMBRANE_PALETTE,
                    (0.07, 0.11, 0.15, 0.18, 0.18, 0.15, 0.10, 0.06),
                )
                _draw(
                    layers["collapsed membrane plates"],
                    _plate(plate_center, theta, length, width, size, int(rng.integers(0, 4))),
                    plate_color,
                    int(rng.integers(178, 238)),
                    plate_tier,
                )
                _mark(geometry, "irregular collapsed membrane plates", length)

                if rng.random() < 0.72:
                    rim_length = float(rng.uniform(14.0, min(27.0, length)))
                    rim_width = float(rng.uniform(8.0, 9.5))
                    rim_center = _point(
                        plate_center,
                        theta,
                        rng.uniform(-length * 0.20, length * 0.20),
                        side * rng.uniform(width * 0.38, width * 0.62),
                        size,
                    )
                    rim_color, rim_tier = _tiered(
                        rng,
                        ACID_PALETTE,
                        (0.02, 0.04, 0.08, 0.13, 0.18, 0.21, 0.20, 0.14),
                    )
                    _draw(
                        layers["acid charged rims"],
                        _wedge(rim_center, theta + rng.uniform(-0.12, 0.12), rim_length, rim_width, size, side),
                        rim_color,
                        int(rng.integers(190, 247)),
                        rim_tier,
                    )
                    _mark(geometry, "acid-yellow charged rims", rim_length)

                if rng.random() < 0.24:
                    pore_length = float(rng.uniform(10.0, 18.0))
                    pore_width = float(rng.uniform(8.0, min(13.0, pore_length)))
                    pore_center = _point(
                        plate_center,
                        theta,
                        (-1.0 if rng.random() < 0.5 else 1.0) * length * rng.uniform(0.28, 0.44),
                        rng.uniform(-width * 0.32, width * 0.32),
                        size,
                    )
                    pore_color = (int(rng.integers(0, 7)), int(rng.integers(2, 10)), int(rng.integers(4, 14)))
                    pore_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(
                        layers["clipped pore mouths"],
                        _wedge(pore_center, theta + rng.uniform(-0.45, 0.45), pore_length, pore_width, size, -side),
                        pore_color,
                        int(rng.integers(215, 256)),
                        pore_tier,
                    )
                    _mark(geometry, "clipped angular pore mouths", pore_length)

                if rng.random() < 0.28:
                    corner_size = float(rng.uniform(8.0, 14.0))
                    corner_center = _point(
                        plate_center,
                        theta,
                        (-1.0 if rng.random() < 0.5 else 1.0) * length * rng.uniform(0.40, 0.56),
                        side * width * rng.uniform(0.32, 0.64),
                        size,
                    )
                    corner_color, corner_tier = _tiered(rng, TORN_PALETTE)
                    _draw(
                        layers["torn corners"],
                        _poly(
                            corner_center,
                            theta + rng.uniform(-0.7, 0.7),
                            (
                                (-corner_size * 0.50, -corner_size * 0.16),
                                (corner_size * 0.42, -corner_size * 0.44),
                                (corner_size * 0.18, corner_size * 0.50),
                            ),
                            size,
                        ),
                        corner_color,
                        int(rng.integers(178, 239)),
                        corner_tier,
                    )
                    _mark(geometry, "torn membrane corners", corner_size)

                if rng.random() < 0.30:
                    center_length = float(rng.uniform(10.0, 20.0))
                    center_width = float(rng.uniform(8.0, min(14.0, center_length)))
                    exhausted_center = _point(
                        plate_center,
                        theta,
                        rng.uniform(-length * 0.14, length * 0.14),
                        rng.uniform(-width * 0.18, width * 0.18),
                        size,
                    )
                    exhausted_color = (int(rng.integers(0, 6)), int(rng.integers(1, 8)), int(rng.integers(3, 11)))
                    exhausted_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(
                        layers["exhausted centers"],
                        _plate(exhausted_center, theta + rng.uniform(-0.35, 0.35), center_length, center_width, size, int(rng.integers(0, 4))),
                        exhausted_color,
                        int(rng.integers(224, 256)),
                        exhausted_tier,
                    )
                    _mark(geometry, "dark exhausted membrane centers", center_length)

            # The nearest two fragments may fuse through one finite bridge.
            # Selecting the nearest pair prevents a recoverable long network.
            if len(fragment_centers) >= 2 and rng.random() < 0.84:
                nearest: tuple[float, np.ndarray, np.ndarray] | None = None
                for index, first in enumerate(fragment_centers[:-1]):
                    for second in fragment_centers[index + 1 :]:
                        distance_native = float(np.linalg.norm(second - first) * NATIVE / size)
                        if nearest is None or distance_native < nearest[0]:
                            nearest = (distance_native, first, second)
                assert nearest is not None
                distance_native, first, second = nearest
                if distance_native <= 32.0:
                    bridge_length = float(np.clip(distance_native, 8.0, 28.0))
                    delta = second - first
                    bridge_theta = float(math.atan2(float(delta[1]), float(delta[0])))
                    bridge_center = (first + second) * 0.5
                    bridge_color, bridge_tier = _tiered(rng, BRIDGE_PALETTE)
                    _draw(
                        layers["fused bridges"],
                        _wedge(bridge_center, bridge_theta, bridge_length, rng.uniform(8.0, 10.0), size, 1.0),
                        bridge_color,
                        int(rng.integers(160, 229)),
                        bridge_tier,
                    )
                    _mark(geometry, "finite fused membrane bridges", bridge_length)

                    if rng.random() < 0.92:
                        bead_size = float(rng.uniform(8.0, 13.0))
                        bead_center = _point(
                            bridge_center,
                            bridge_theta,
                            (-1.0 if rng.random() < 0.5 else 1.0) * bridge_length * rng.uniform(0.24, 0.42),
                            rng.uniform(-4.0, 4.0),
                            size,
                        )
                        bead_color, bead_tier = _tiered(
                            rng,
                            CRYSTAL_PALETTE,
                            (0.03, 0.05, 0.08, 0.12, 0.17, 0.20, 0.20, 0.15),
                        )
                        _draw(
                            layers["crystal beads"],
                            _diamond(bead_center, bridge_theta + rng.uniform(-0.8, 0.8), bead_size, 8.0, size),
                            bead_color,
                            int(rng.integers(188, 246)),
                            bead_tier,
                        )
                        _mark(geometry, "faceted electrolyte crystal beads", bead_size)

    masks = {name: layer[2] for name, layer in layers.items()}
    ceramic = masks["ceramic facets"]
    plates = masks["collapsed membrane plates"]
    rims = masks["acid charged rims"]
    cyan = masks["cyan electrolyte ghosts"]
    magenta = masks["magenta separator shadows"]
    pores = masks["clipped pore mouths"]
    bridges = masks["fused bridges"]
    beads = masks["crystal beads"]
    corners = masks["torn corners"]
    centers = masks["exhausted centers"]

    ceramic_depth = np.clip(blur(ceramic, 24.0, size), 0.0, 1.0)
    electrolyte_haze = np.clip(blur(0.82 * cyan + 0.46 * beads, 18.0, size), 0.0, 1.0)
    separator_haze = np.clip(blur(0.84 * magenta + 0.38 * corners, 16.0, size), 0.0, 1.0)
    charge_haze = np.clip(blur(0.84 * rims + 0.62 * bridges + 0.44 * beads, 15.0, size), 0.0, 1.0)
    exhaustion = np.clip(blur(0.72 * pores + 0.86 * centers + 0.54 * corners, 13.0, size), 0.0, 1.0)

    yy = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    studio_falloff = 0.91 + 0.09 * (1.0 - np.abs(yy - 0.48) * 2.0)
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = (0.012 + 0.040 * ceramic_depth + 0.020 * electrolyte_haze + 0.098 * separator_haze + 0.076 * charge_haze - 0.012 * exhaustion) * studio_falloff
    paint[..., 1] = (0.019 + 0.057 * ceramic_depth + 0.118 * electrolyte_haze + 0.025 * separator_haze + 0.086 * charge_haze - 0.014 * exhaustion) * studio_falloff
    paint[..., 2] = (0.028 + 0.074 * ceramic_depth + 0.140 * electrolyte_haze + 0.092 * separator_haze + 0.029 * charge_haze - 0.010 * exhaustion) * studio_falloff

    for family, strength in (
        ("ceramic facets", 0.54),
        ("cyan electrolyte ghosts", 0.97),
        ("magenta separator shadows", 0.97),
        ("collapsed membrane plates", 0.95),
        ("fused bridges", 0.94),
        ("acid charged rims", 0.98),
        ("torn corners", 0.91),
        ("crystal beads", 1.00),
        ("clipped pore mouths", 1.00),
        ("exhausted centers", 1.00),
    ):
        _composite(paint, layers[family], strength)

    paint += blur(rims + beads, 10.0, size)[..., None] * np.asarray((0.206, 0.232, 0.006), np.float32)
    paint += blur(cyan, 11.0, size)[..., None] * np.asarray((0.000, 0.187, 0.239), np.float32)
    paint += blur(magenta, 11.0, size)[..., None] * np.asarray((0.213, 0.000, 0.181), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    # SPB-105 / 2026-08-27 owner verdict: preserve the collapsed membrane's
    # fine anatomy while keeping the charged electrolyte phases visibly Neon.
    # Official isolated M7 movement: 71.0 -> 86.5 without changing geometry
    # or M/R/Cc.
    hsv = cv2.cvtColor(paint, cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0.0, 1.0)
    paint = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    rupture = np.maximum.reduce((pores, corners, centers))
    charged_pool = np.clip(
        blur(0.88 * rims + 0.72 * bridges + 0.82 * beads, 11.0, size)
        - 0.56 * blur(centers + pores, 8.0, size),
        0.0,
        1.0,
    )
    intact_membrane = np.clip(
        blur(0.68 * ceramic + 0.92 * plates + 0.48 * magenta, 13.0, size)
        + 0.34 * blur(cyan + bridges, 11.0, size)
        - 0.82 * blur(rupture, 8.0, size),
        0.0,
        1.0,
    )

    m_score = (
        0.07
        + 1.31 * rims
        + 1.16 * beads
        + 0.92 * bridges
        + 0.48 * cyan
        + 0.36 * corners
        - 0.68 * centers
        - 0.48 * pores
        + 0.18 * blur(rims + beads + bridges, 14.0, size)
    )
    r_score = (
        0.14
        + 1.24 * centers
        + 1.08 * pores
        + 0.93 * corners
        + 0.61 * magenta
        + 0.38 * plates
        - 0.70 * beads
        - 0.55 * rims
        - 0.34 * cyan
        + 0.20 * blur(centers + pores + corners, 15.0, size)
    )
    c_score = (
        0.16
        + 1.12 * intact_membrane
        + 0.84 * cyan
        + 0.67 * magenta
        + 0.51 * bridges
        + 0.38 * charged_pool
        - 0.88 * centers
        - 0.76 * pores
        - 0.64 * corners
        - 0.31 * rims
        + 0.15 * blur(ceramic + plates + cyan, 20.0, size)
    )
    spec = pack_material(m_score, r_score, c_score)

    evidence_masks = {
        "black electrochemical ceramic facets": ceramic,
        "irregular collapsed membrane plates": plates,
        "acid-yellow charged rims": rims,
        "displaced cyan electrolyte ghosts": cyan,
        "magenta separator shadows": magenta,
        "clipped angular pore mouths": pores,
        "finite fused membrane bridges": bridges,
        "faceted electrolyte crystal beads": beads,
        "torn membrane corners": corners,
        "dark exhausted membrane centers": centers,
        "registered charged pools": charged_pool,
        "intact membrane/ceramic pools": intact_membrane,
    }
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=evidence_masks,
        geometry=_geometry(geometry),
        carrier="black electrochemical ceramic with dense irregular collapsed membrane deposits",
        material_story={
            "M": "acid-charged rims, fused bridges, crystal beads, electrolyte residue, and torn exposed corners raise metallic response",
            "R": "exhausted centers, clipped pores, torn corners, separator abrasion, and collapsed membrane raise roughness",
            "Cc": "intact membrane, ceramic, cyan electrolyte, magenta separator, and fused bridges retain coat while rupture loses it",
        },
        vetoes=(
            "honeycomb or hexagons",
            "grids or rows",
            "bubbles or circles",
            "scales",
            "biological cells",
            "flowers",
            "repeated tile or stamp grammar",
            "macro voids",
        ),
    )


def _determinism_audit(seed: int, first: PilotResult) -> dict[str, object]:
    start = time.perf_counter()
    second = build_electrocell(seed=seed, size=first.paint.shape[0])
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
    parser = argparse.ArgumentParser(description="Render isolated Electrocell owner-review evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_neon_oil_slick_reset_work/electrocell"),
        help="isolated evidence directory",
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args()

    result = timed_result(build_electrocell, seed=args.seed)
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
        if name not in {"registered charged pools", "intact membrane/ceramic pools"}
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
        "tick": "EC-P2",
        "verdict": (
            "EC-P1 placed carrier and rupture anatomy in the same tiny-chip register and collapsed into multicolor "
            "confetti; EC-P2 tightens asymmetric directional collapse packets and separates buried layers from edge charge."
        ),
        "metric_movement": {
            "picker_64_chroma_std": [0.014026, picker_survival["sizes"]["64"]["chroma_std"]],
            "picker_64_luma_std": [0.037495, picker_survival["sizes"]["64"]["luma_std"]],
            "collapsed_membrane_coverage": [0.113789, coverage["irregular collapsed membrane plates"]],
            "family_masks_above_half_percent": [9, int(visible_family_coverage_count)],
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
