"""Emberwake Delam — isolated Neon Underground v3 owner-review pilot.

SPB-105 / Neon reset tick ED-P2 / owner screen 2026-08-27: the first pass read
as "near-identical sparse orange/purple caterpillar packets on blank black."
Audit movement: repeated packet field -> dense independent foil-scale anatomy,
16 geometry families, 26.2% foil coverage before eight attached rupture masks,
deterministic ~1.7s builder, and causal 8-tier M/R/Cc.  Emberwake is one
heat-delaminated foil skin beneath smoked black clear, never a flame graphic or
floating ribbon.  No registry/catalog wiring is permitted before owner review.
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


FINISH_ID = "neon2_emberwake_delam"
DISPLAY_NAME = "Emberwake Delam"
DEFAULT_SEED = 0xE8BE_2026
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


def _points(
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
    return _points(
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
    blend = (alpha.astype(np.float32) / 255.0 * float(strength))[..., None]
    paint *= 1.0 - blend
    paint += rgb.astype(np.float32) / 255.0 * blend


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


FOIL_PALETTE = np.asarray(
    (
        (61, 4, 2),
        (86, 6, 2),
        (114, 10, 2),
        (146, 16, 3),
        (179, 26, 4),
        (213, 42, 6),
        (241, 66, 9),
        (255, 97, 14),
    ),
    np.uint8,
)
SHOULDER_PALETTE = np.asarray(
    (
        (29, 0, 43),
        (45, 0, 68),
        (65, 2, 91),
        (89, 3, 114),
        (117, 5, 136),
        (145, 7, 151),
        (177, 10, 164),
        (211, 18, 181),
    ),
    np.uint8,
)
ADHESIVE_PALETTE = np.asarray(
    (
        (43, 10, 2),
        (60, 15, 2),
        (82, 22, 2),
        (108, 31, 3),
        (139, 44, 4),
        (173, 62, 6),
        (207, 86, 9),
        (238, 119, 17),
    ),
    np.uint8,
)
PEEL_PALETTE = np.asarray(
    (
        (178, 25, 3),
        (207, 39, 4),
        (229, 56, 7),
        (244, 77, 12),
        (255, 105, 22),
        (255, 143, 52),
        (255, 190, 105),
        (255, 237, 196),
    ),
    np.uint8,
)
OXIDE_PALETTE = np.asarray(
    (
        (78, 16, 3),
        (105, 25, 4),
        (137, 37, 5),
        (172, 54, 7),
        (204, 76, 13),
        (222, 104, 29),
        (104, 139, 126),
        (151, 185, 161),
    ),
    np.uint8,
)
NICK_PALETTE = np.asarray(
    (
        (84, 72, 73),
        (106, 94, 96),
        (130, 119, 121),
        (154, 145, 145),
        (179, 171, 168),
        (204, 198, 190),
        (229, 224, 211),
        (255, 248, 227),
    ),
    np.uint8,
)


def build_emberwake_delam(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Compose one deterministic sheet of heat-delaminated fluorescent foil."""
    if int(size) != WORK:
        raise ValueError(f"Emberwake Delam is authored at WORK={WORK}, got {size}")
    rng = seeded(seed)
    layers: dict[str, Layer] = {
        "cooled shoulders": _layer(size),
        "adhesive blisters": _layer(size),
        "fluorescent foil": _layer(size),
        "broken peel lips": _layer(size),
        "snap-back scars": _layer(size),
        "soot fissures": _layer(size),
        "oxide shards": _layer(size),
        "char microflakes": _layer(size),
        "exposed foil nicks": _layer(size),
    }
    geometry: Counter[tuple[str, float]] = Counter()

    # A dense, low-contrast foil skin prevents the damage colonies from reading
    # as floating caterpillar stamps.  Each site authors one isolated foil scale
    # plus at most one independently positioned material consequence.  Shapes,
    # roles, angles, and tiers all vary; there is no single repeated packet.
    micro_cell = max(5, int(round(28.0 * size / NATIVE)))
    for micro_y, y0 in enumerate(range(-micro_cell, size + micro_cell, micro_cell)):
        for micro_x, x0 in enumerate(range(-micro_cell, size + micro_cell, micro_cell)):
            if rng.random() < 0.10:
                continue
            center = np.asarray(
                (
                    x0 + rng.uniform(-0.46, 0.46) * micro_cell,
                    y0 + rng.uniform(-0.46, 0.46) * micro_cell,
                ),
                np.float32,
            )
            theta = float(rng.uniform(-math.pi, math.pi))
            scale_length = float(rng.uniform(12.0, 24.0))
            scale_width = float(rng.uniform(8.0, 14.0))
            half_scale_l = scale_length * 0.5
            half_scale_w = scale_width * 0.5
            variant = int(rng.integers(0, 3))
            if variant == 0:
                scale_offsets = (
                    (-half_scale_l, -half_scale_w * 0.18),
                    (-half_scale_l * 0.34, -half_scale_w),
                    (half_scale_l, -half_scale_w * 0.32),
                    (half_scale_l * 0.58, half_scale_w),
                    (-half_scale_l * 0.52, half_scale_w * 0.64),
                )
            elif variant == 1:
                scale_offsets = (
                    (-half_scale_l, -half_scale_w * 0.56),
                    (half_scale_l * 0.52, -half_scale_w),
                    (half_scale_l, half_scale_w * 0.20),
                    (half_scale_l * 0.12, half_scale_w),
                    (-half_scale_l * 0.74, half_scale_w * 0.48),
                )
            else:
                scale_offsets = (
                    (-half_scale_l, -half_scale_w * 0.12),
                    (-half_scale_l * 0.16, -half_scale_w),
                    (half_scale_l, -half_scale_w * 0.08),
                    (half_scale_l * 0.38, half_scale_w),
                    (-half_scale_l * 0.72, half_scale_w * 0.54),
                )
            scale_color, scale_tier = _tiered(rng, FOIL_PALETTE, low=0, high=5)
            _draw(
                layers["fluorescent foil"],
                _points(center, theta, scale_offsets, size),
                scale_color,
                int(rng.integers(106, 177)),
                scale_tier,
            )
            _mark(geometry, "isolated foil scales", scale_length)

            if rng.random() >= 0.74:
                continue
            role = int((micro_x * 5 + micro_y * 7 + int(rng.integers(0, 13))) % 6)
            offset_theta = float(theta + rng.uniform(-math.pi, math.pi))
            event_center = _point(center, offset_theta, rng.uniform(10.0, 25.0), 0.0, size)

            if role == 0:
                # Faceted quench freckle: a violet diamond, never a dot/circle.
                diameter = float(rng.uniform(8.0, 13.0))
                freckle = _points(
                    event_center,
                    theta + rng.uniform(-1.0, 1.0),
                    ((-diameter * 0.50, 0.0), (0.0, -diameter * 0.43), (diameter * 0.50, 0.0), (0.0, diameter * 0.43)),
                    size,
                )
                freckle_color, freckle_tier = _tiered(rng, SHOULDER_PALETTE, low=2)
                _draw(layers["cooled shoulders"], freckle, freckle_color, int(rng.integers(155, 226)), freckle_tier)
                _mark(geometry, "quench freckles", diameter)
            elif role == 1:
                fissure_length = float(rng.uniform(12.0, 24.0))
                fissure_color = (int(rng.integers(2, 24)), int(rng.integers(0, 8)), int(rng.integers(2, 20)))
                fissure_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                _draw(
                    layers["soot fissures"],
                    _strip(event_center, theta + rng.uniform(-1.2, 1.2), fissure_length, 8.0, size, rng.uniform(-0.24, 0.24)),
                    fissure_color,
                    int(rng.integers(195, 249)),
                    fissure_tier,
                )
                _mark(geometry, "soot fissure shards", fissure_length)
            elif role == 2:
                chip_length = float(rng.uniform(10.0, 18.0))
                chip_width = float(rng.uniform(8.0, 10.0))
                chip_color, chip_tier = _weighted_tier(
                    rng,
                    NICK_PALETTE,
                    (0.08, 0.14, 0.21, 0.23, 0.18, 0.10, 0.05, 0.01),
                )
                _draw(
                    layers["exposed foil nicks"],
                    _strip(event_center, theta + rng.uniform(-0.7, 0.7), chip_length, chip_width, size, rng.uniform(-0.30, 0.30)),
                    chip_color,
                    int(rng.integers(163, 225)),
                    chip_tier,
                )
                _mark(geometry, "torn edge chips", chip_length)
            elif role == 3:
                scar_a = float(rng.uniform(8.0, 14.0))
                scar_b = float(rng.uniform(8.0, 14.0))
                scar_theta = float(theta + rng.uniform(-1.0, 1.0))
                turn_theta = float(scar_theta + (-1.0 if rng.random() < 0.5 else 1.0) * rng.uniform(0.55, 1.0))
                first_center = _point(event_center, scar_theta, -scar_a * 0.50, 0.0, size)
                second_center = _point(event_center, turn_theta, scar_b * 0.50, 0.0, size)
                scar_color = (int(rng.integers(20, 59)), int(rng.integers(0, 8)), int(rng.integers(54, 119)))
                scar_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                _draw(layers["snap-back scars"], _strip(first_center, scar_theta, scar_a, 8.0, size, -0.18), scar_color, 215, scar_tier)
                _draw(layers["snap-back scars"], _strip(second_center, turn_theta, scar_b, 8.0, size, 0.18), scar_color, 223, scar_tier)
                _mark(geometry, "isolated snap-back scars", scar_a)
                _mark(geometry, "isolated snap-back scars", scar_b)
            elif role == 4:
                lip_length = float(rng.uniform(12.0, 24.0))
                lip_color, lip_tier = _weighted_tier(
                    rng,
                    PEEL_PALETTE,
                    (0.0, 0.06, 0.20, 0.25, 0.22, 0.16, 0.08, 0.03),
                )
                _draw(
                    layers["broken peel lips"],
                    _strip(event_center, theta + rng.uniform(-0.8, 0.8), lip_length, 8.0, size, rng.uniform(-0.30, 0.30)),
                    lip_color,
                    int(rng.integers(174, 235)),
                    lip_tier,
                )
                _mark(geometry, "broken peel bevels", lip_length)
            else:
                oxide_diameter = float(rng.uniform(8.0, 13.0))
                oxide = _points(
                    event_center,
                    theta + rng.uniform(-1.2, 1.2),
                    (
                        (-oxide_diameter * 0.50, 0.0),
                        (-oxide_diameter * 0.05, -oxide_diameter * 0.42),
                        (oxide_diameter * 0.50, -oxide_diameter * 0.08),
                        (oxide_diameter * 0.10, oxide_diameter * 0.44),
                    ),
                    size,
                )
                oxide_color, oxide_tier = _tiered(rng, OXIDE_PALETTE)
                _draw(layers["oxide shards"], oxide, oxide_color, int(rng.integers(154, 218)), oxide_tier)
                _mark(geometry, "isolated oxide shards", oxide_diameter)

    # Local clusters survive small pickers, while every individual authoring
    # operation remains 8-32px.  Coarse orientation domains share only heat
    # history; their boundaries are never painted as panels or waves.
    cell = max(16, int(round(76.0 * size / NATIVE)))
    margin = int(round(32.0 * size / NATIVE))
    for gy, base_y in enumerate(range(-cell // 2, size + cell, cell)):
        for gx, base_x in enumerate(range(-cell // 2, size + cell, cell)):
            cluster_center = np.asarray(
                (
                    base_x + rng.uniform(-0.42, 0.42) * cell,
                    base_y + rng.uniform(-0.42, 0.42) * cell,
                ),
                np.float32,
            )
            if (
                cluster_center[0] < -margin
                or cluster_center[1] < -margin
                or cluster_center[0] > size + margin
                or cluster_center[1] > size + margin
            ):
                continue
            domain_x, domain_y = gx // 3, gy // 3
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x + domain_y * 5) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            local_index = (gx % 3) + 3 * (gy % 3)
            active_bit = bool(
                ((domain_hash >> (local_index + 4)) & 1)
                and ((domain_hash >> ((local_index + 15) % 27)) & 1)
            )
            forced_anchor = local_index == int(domain_hash % 9)
            if not (active_bit or forced_anchor):
                continue
            domain_theta = -math.pi + (domain_hash % 1009) / 1008.0 * math.tau
            cluster_theta = float(domain_theta + rng.normal(0.0, 0.34))
            shard_count = int(rng.integers(6, 10))
            along_slots = rng.uniform(-28.0, 28.0, size=shard_count).astype(np.float32)

            for shard_slot, along_slot in enumerate(along_slots):
                theta = float(cluster_theta + rng.normal(0.0, 0.22))
                shard_center = _point(
                    cluster_center,
                    cluster_theta,
                    float(along_slot + rng.uniform(-4.0, 4.0)),
                    float(rng.uniform(-24.0, 24.0)),
                    size,
                )
                foil_length = float(rng.uniform(18.0, 32.0))
                foil_width = float(rng.uniform(8.0, 16.0))
                half_l = foil_length * 0.5
                half_w = foil_width * 0.5
                side = -1.0 if rng.random() < 0.5 else 1.0

                # Cooled magenta/violet foil remains physically tucked beneath
                # one edge of its hot plate, never floating as a ribbon.
                if rng.random() < 0.42:
                    shoulder_length = float(rng.uniform(14.0, 28.0))
                    shoulder_width = float(rng.uniform(8.0, 14.0))
                    shoulder_center = _point(
                        shard_center,
                        theta,
                        rng.uniform(-4.0, 2.0),
                        -side * (foil_width * 0.35 + shoulder_width * 0.18),
                        size,
                    )
                    shoulder_poly = _points(
                        shoulder_center,
                        theta + rng.uniform(-0.12, 0.12),
                        (
                            (-shoulder_length * 0.50, -shoulder_width * 0.22),
                            (-shoulder_length * 0.12, -shoulder_width * 0.50),
                            (shoulder_length * 0.50, -shoulder_width * 0.28),
                            (shoulder_length * 0.38, shoulder_width * 0.44),
                            (-shoulder_length * 0.42, shoulder_width * 0.50),
                        ),
                        size,
                    )
                    color, tier = _tiered(rng, SHOULDER_PALETTE)
                    _draw(layers["cooled shoulders"], shoulder_poly, color, int(rng.integers(151, 224)), tier)
                    _mark(geometry, "cooled magenta/violet shoulders", shoulder_length)

                # Adhesive blisters are irregular faceted pockets.  No circle,
                # ellipse, or annular highlight is used anywhere in this file.
                if rng.random() < 0.28:
                    blister_length = float(rng.uniform(10.0, 22.0))
                    blister_width = float(rng.uniform(8.0, 16.0))
                    blister_center = _point(
                        shard_center,
                        theta,
                        rng.uniform(-6.0, 5.0),
                        side * rng.uniform(-foil_width * 0.20, foil_width * 0.28),
                        size,
                    )
                    blister_poly = _points(
                        blister_center,
                        theta + rng.uniform(-0.35, 0.35),
                        (
                            (-blister_length * 0.50, -blister_width * 0.10),
                            (-blister_length * 0.18, -blister_width * 0.50),
                            (blister_length * 0.43, -blister_width * 0.36),
                            (blister_length * 0.50, blister_width * 0.18),
                            (blister_length * 0.05, blister_width * 0.50),
                            (-blister_length * 0.42, blister_width * 0.34),
                        ),
                        size,
                    )
                    color, tier = _tiered(rng, ADHESIVE_PALETTE)
                    _draw(layers["adhesive blisters"], blister_poly, color, int(rng.integers(137, 211)), tier)
                    _mark(geometry, "faceted adhesive blisters", blister_length)

                foil_poly = _points(
                    shard_center,
                    theta,
                    (
                        (-half_l, -half_w * 0.18),
                        (-half_l * 0.48, -half_w),
                        (half_l * 0.28, -half_w * 0.82),
                        (half_l, -half_w * 0.18),
                        (half_l * 0.72, half_w * 0.76),
                        (-half_l * 0.22, half_w),
                        (-half_l * 0.86, half_w * 0.46),
                    ),
                    size,
                )
                color, foil_tier = _tiered(rng, FOIL_PALETTE)
                _draw(layers["fluorescent foil"], foil_poly, color, int(rng.integers(162, 235)), foil_tier)
                _mark(geometry, "fluorescent foil plates", foil_length)

                # Selected colony plates lift one broken bevel at an edge.  The
                # single finite trapezoid avoids a repeated literal hook glyph.
                had_peel = rng.random() < 0.18
                if had_peel:
                    lip_length = float(rng.uniform(10.0, 24.0))
                    lip_center = _point(
                        shard_center,
                        theta,
                        rng.uniform(-half_l * 0.15, half_l * 0.58),
                        side * half_w * rng.uniform(0.58, 0.92),
                        size,
                    )
                    peel_color, peel_tier = _weighted_tier(
                        rng,
                        PEEL_PALETTE,
                        (0.0, 0.0, 0.20, 0.23, 0.22, 0.17, 0.12, 0.06),
                    )
                    _draw(
                        layers["broken peel lips"],
                        _strip(
                            lip_center,
                            theta + side * rng.uniform(0.10, 0.48),
                            lip_length,
                            rng.uniform(8.0, 9.2),
                            size,
                            rng.uniform(-0.26, 0.26),
                        ),
                        peel_color,
                        int(rng.integers(184, 245)),
                        peel_tier,
                    )
                    _mark(geometry, "broken colony peel bevels", lip_length)

                # Snap-back damage begins at the same lifted edge and recoils
                # as a short angular scar, never a large arc.
                if (had_peel and rng.random() < 0.55) or (not had_peel and rng.random() < 0.08):
                    scar_a = float(rng.uniform(8.0, 17.0))
                    scar_b = float(rng.uniform(8.0, 15.0))
                    scar_joint = _point(
                        shard_center,
                        theta,
                        rng.uniform(-half_l * 0.42, half_l * 0.30),
                        -side * rng.uniform(0.0, half_w * 0.58),
                        size,
                    )
                    scar_theta = theta + rng.uniform(-0.30, 0.30)
                    recoil_theta = scar_theta - side * rng.uniform(0.58, 1.02)
                    scar_center_a = _point(scar_joint, scar_theta, -scar_a * 0.50, 0.0, size)
                    scar_center_b = _point(scar_joint, recoil_theta, scar_b * 0.50, 0.0, size)
                    scar_color = (
                        int(rng.integers(16, 52)),
                        int(rng.integers(0, 7)),
                        int(rng.integers(38, 99)),
                    )
                    scar_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _draw(layers["snap-back scars"], _strip(scar_center_a, scar_theta, scar_a, 8.0, size, -0.18), scar_color, 226, scar_tier)
                    _draw(layers["snap-back scars"], _strip(scar_center_b, recoil_theta, scar_b, 8.0, size, 0.20), scar_color, 238, scar_tier)
                    _mark(geometry, "snap-back scars", scar_a)
                    _mark(geometry, "snap-back scars", scar_b)

                # Soot fissures cut through real foil plates.  The optional
                # branch is another finite segment, not generated crack noise.
                had_fissure = rng.random() < 0.30
                if had_fissure:
                    fissure_length = float(rng.uniform(12.0, 28.0))
                    fissure_theta = theta + rng.uniform(-0.72, 0.72)
                    fissure_center = _point(
                        shard_center,
                        theta,
                        rng.uniform(-half_l * 0.28, half_l * 0.28),
                        rng.uniform(-half_w * 0.38, half_w * 0.38),
                        size,
                    )
                    soot_color = (
                        int(rng.integers(1, 19)),
                        int(rng.integers(0, 7)),
                        int(rng.integers(2, 18)),
                    )
                    soot_tier = float(EVENT_TIERS[int(rng.integers(2, 8))])
                    _draw(
                        layers["soot fissures"],
                        _strip(fissure_center, fissure_theta, fissure_length, 8.0, size, rng.uniform(-0.22, 0.22)),
                        soot_color,
                        int(rng.integers(214, 256)),
                        soot_tier,
                    )
                    _mark(geometry, "soot fissures", fissure_length)
                    if rng.random() < 0.36:
                        branch_length = float(rng.uniform(8.0, 16.0))
                        branch_theta = fissure_theta + (-1.0 if rng.random() < 0.5 else 1.0) * rng.uniform(0.55, 1.08)
                        branch_origin = _point(fissure_center, fissure_theta, rng.uniform(-3.0, 4.0), 0.0, size)
                        branch_center = _point(branch_origin, branch_theta, branch_length * 0.50, 0.0, size)
                        _draw(
                            layers["soot fissures"],
                            _strip(branch_center, branch_theta, branch_length, 8.0, size, rng.uniform(-0.18, 0.18)),
                            soot_color,
                            int(rng.integers(203, 248)),
                            float(EVENT_TIERS[int(rng.integers(1, 8))]),
                        )
                        _mark(geometry, "soot fissures", branch_length)

                # Oxide beads are faceted diamonds/shards only—never circles.
                has_oxide = (
                    (had_peel and rng.random() < 0.58)
                    or (had_fissure and rng.random() < 0.42)
                    or rng.random() < 0.07
                )
                if has_oxide:
                    oxide_count = int(rng.integers(1, 3))
                    for _ in range(oxide_count):
                        oxide_diameter = float(rng.uniform(8.0, 13.0))
                        oxide_center = _point(
                            shard_center,
                            theta,
                            rng.uniform(-half_l * 0.72, half_l * 0.72),
                            side * rng.uniform(half_w * 0.05, half_w * 0.86),
                            size,
                        )
                        oxide_theta = theta + rng.uniform(-math.pi, math.pi)
                        oxide_poly = _points(
                            oxide_center,
                            oxide_theta,
                            (
                                (-oxide_diameter * 0.50, 0.0),
                                (-oxide_diameter * 0.08, -oxide_diameter * 0.42),
                                (oxide_diameter * 0.50, -oxide_diameter * 0.08),
                                (oxide_diameter * 0.12, oxide_diameter * 0.44),
                            ),
                            size,
                        )
                        oxide_color, oxide_tier = _tiered(rng, OXIDE_PALETTE)
                        _draw(layers["oxide shards"], oxide_poly, oxide_color, int(rng.integers(174, 241)), oxide_tier)
                        _mark(geometry, "oxide beads/shards", oxide_diameter)

                # Char remains attached to rupture history as angular flakes.
                if (had_fissure or had_peel) and rng.random() < 0.62:
                    flake_count = int(rng.integers(1, 3))
                    for _ in range(flake_count):
                        flake_length = float(rng.uniform(8.0, 15.0))
                        flake_width = float(rng.uniform(8.0, min(12.0, flake_length)))
                        flake_center = _point(
                            shard_center,
                            theta,
                            rng.uniform(-half_l * 0.74, half_l * 0.66),
                            rng.uniform(-half_w * 0.78, half_w * 0.78),
                            size,
                        )
                        flake_poly = _points(
                            flake_center,
                            theta + rng.uniform(-1.0, 1.0),
                            (
                                (-flake_length * 0.50, -flake_width * 0.12),
                                (-flake_length * 0.10, -flake_width * 0.50),
                                (flake_length * 0.50, -flake_width * 0.22),
                                (flake_length * 0.24, flake_width * 0.50),
                                (-flake_length * 0.42, flake_width * 0.36),
                            ),
                            size,
                        )
                        char_color = (
                            int(rng.integers(3, 30)),
                            int(rng.integers(1, 12)),
                            int(rng.integers(1, 17)),
                        )
                        char_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                        _draw(layers["char microflakes"], flake_poly, char_color, int(rng.integers(184, 247)), char_tier)
                        _mark(geometry, "char microflakes", flake_length)

                # Small pale nicks expose clean foil along damaged plate edges.
                if rng.random() < 0.15:
                    nick_length = float(rng.uniform(10.0, 20.0))
                    nick_width = float(rng.uniform(8.0, 10.0))
                    nick_center = _point(
                        shard_center,
                        theta,
                        rng.uniform(-half_l * 0.42, half_l * 0.60),
                        -side * half_w * rng.uniform(0.42, 0.88),
                        size,
                    )
                    nick_poly = _strip(
                        nick_center,
                        theta + rng.uniform(-0.22, 0.22),
                        nick_length,
                        nick_width,
                        size,
                        rng.uniform(-0.28, 0.28),
                    )
                    nick_color, nick_tier = _weighted_tier(
                        rng,
                        NICK_PALETTE,
                        (0.03, 0.07, 0.14, 0.20, 0.22, 0.19, 0.11, 0.04),
                    )
                    _draw(layers["exposed foil nicks"], nick_poly, nick_color, int(rng.integers(201, 256)), nick_tier)
                    _mark(geometry, "exposed foil nicks", nick_length)

    masks = {name: layer[2] for name, layer in layers.items()}
    foil = masks["fluorescent foil"]
    shoulders = masks["cooled shoulders"]
    adhesive = masks["adhesive blisters"]
    peel = masks["broken peel lips"]
    snap = masks["snap-back scars"]
    soot = masks["soot fissures"]
    oxide = masks["oxide shards"]
    char = masks["char microflakes"]
    nicks = masks["exposed foil nicks"]

    rupture = np.maximum.reduce((peel, snap, soot, char, nicks))
    heat_history = np.clip(blur(1.06 * foil + 0.94 * peel + 0.56 * oxide, 32.0, size), 0.0, 1.0)
    cooled_history = np.clip(blur(shoulders, 24.0, size), 0.0, 1.0)
    soot_shadow = np.clip(blur(0.78 * soot + 0.61 * char + 0.42 * snap, 20.0, size), 0.0, 1.0)

    yy = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    studio_falloff = 0.91 + 0.09 * (1.0 - np.abs(yy - 0.46) * 2.0)
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = (0.034 + 0.285 * heat_history + 0.074 * cooled_history - 0.009 * soot_shadow) * studio_falloff
    paint[..., 1] = (0.008 + 0.027 * heat_history - 0.002 * soot_shadow) * studio_falloff
    paint[..., 2] = (0.014 + 0.088 * cooled_history + 0.009 * soot_shadow) * studio_falloff

    for family, strength in (
        ("cooled shoulders", 0.92),
        ("adhesive blisters", 0.84),
        ("fluorescent foil", 0.96),
        ("broken peel lips", 1.00),
        ("snap-back scars", 0.97),
        ("soot fissures", 0.99),
        ("oxide shards", 0.96),
        ("char microflakes", 0.98),
        ("exposed foil nicks", 1.00),
    ):
        _composite(paint, layers[family], strength)

    # All glow is registered to real peel/oxide/shoulder anatomy.
    paint += blur(peel, 12.0, size)[..., None] * np.asarray((0.24, 0.040, 0.004), np.float32)
    paint += blur(shoulders, 17.0, size)[..., None] * np.asarray((0.075, 0.000, 0.105), np.float32)
    paint += blur(oxide, 9.0, size)[..., None] * np.asarray((0.055, 0.016, 0.003), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    intact_foil = np.clip(
        blur(foil, 10.0, size)
        + 0.48 * blur(adhesive, 12.0, size)
        + 0.38 * blur(shoulders, 14.0, size)
        - 0.91 * blur(rupture, 8.0, size),
        0.0,
        1.0,
    )
    adhesive_pockets = np.clip(
        blur(adhesive * (1.0 - np.clip(rupture, 0.0, 1.0)), 11.0, size)
        + 0.30 * blur(shoulders, 13.0, size),
        0.0,
        1.0,
    )

    # Three independent physical questions over the same registered anatomy.
    m_score = (
        0.08
        + 1.52 * nicks
        + 1.31 * peel
        + 0.69 * oxide
        + 0.31 * foil
        - 0.63 * soot
        - 0.48 * char
        - 0.20 * adhesive
        + 0.23 * blur(peel + nicks, 13.0, size)
    )
    r_score = (
        0.16
        + 1.32 * soot
        + 1.18 * char
        + 1.03 * snap
        + 0.58 * oxide
        + 0.29 * adhesive
        - 0.79 * nicks
        - 0.69 * peel
        - 0.46 * intact_foil
        + 0.25 * blur(soot + char + snap, 16.0, size)
    )
    c_score = (
        0.14
        + 1.24 * intact_foil
        + 0.91 * adhesive_pockets
        + 0.72 * blur(shoulders, 11.0, size)
        + 0.24 * foil
        - 1.17 * soot
        - 1.04 * char
        - 0.91 * snap
        - 0.72 * peel
        - 0.48 * nicks
    )
    spec = pack_material(m_score, r_score, c_score)

    evidence_masks = {
        "fluorescent foil plates": foil,
        "broken peel lips": peel,
        "snap-back scars": snap,
        "soot fissures": soot,
        "faceted adhesive blisters": adhesive,
        "oxide beads/shards": oxide,
        "char microflakes": char,
        "exposed foil nicks": nicks,
        "cooled magenta/violet shoulders": shoulders,
        "intact foil/adhesive pockets": intact_foil,
    }
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=evidence_masks,
        geometry=_geometry(geometry),
        carrier="heat-delaminated fluorescent foil in smoked black clear",
        material_story={
            "M": "exposed clean foil nicks and the hottest lifted peel lips rise above oxidized foil",
            "R": "soot fissures, char microflakes, and snap-back damage rise while clean hot foil falls",
            "Cc": "intact foil, faceted adhesive pockets, and cooled shoulders retain coat while rupture loses it",
        },
        vetoes=(
            "flames",
            "fire icons",
            "waves",
            "floating ribbons",
            "repeated hook wallpaper",
            "macro panels",
            "circles or adhesive bubble rings",
            "generic noise underlays",
        ),
    )


def _determinism_audit(seed: int, first: PilotResult) -> dict[str, object]:
    start = time.perf_counter()
    second = build_emberwake_delam(seed=seed, size=first.paint.shape[0])
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
    dark_fraction = float(np.mean(edge_luma < 0.008))
    return {
        "edge_to_global_gradient_ratio": round(ratio, 6),
        "edge_dark_void_fraction": round(dark_fraction, 6),
        "pass": bool(0.45 <= ratio <= 1.55 and dark_fraction < 0.08),
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
    parser = argparse.ArgumentParser(description="Render isolated Emberwake Delam owner-review evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_neon_oil_slick_reset_work/emberwake_delam"),
        help="isolated evidence directory",
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args()

    result = timed_result(build_emberwake_delam, seed=args.seed)
    manifest = render_evidence(result, args.output, native_size=NATIVE)
    working_material = material_stats(result.spec)
    geometry = manifest["geometry_stats"]
    coverage = manifest["causal_mask_coverage"]
    correlations = working_material["correlation"]
    unique_mrc_triples = int(np.unique(result.spec.reshape(-1, 3), axis=0).shape[0])
    edge_continuity = _edge_continuity_audit(result.paint)
    picker_survival = _picker_audit(result.paint)
    visible_family_coverage_count = sum(
        value >= 0.005 for name, value in coverage.items() if name != "intact foil/adhesive pockets"
    )
    mechanical_gates = {
        "five_plus_anatomy_families": bool(geometry["family_count"] >= 5),
        "five_plus_family_masks_above_half_percent": bool(visible_family_coverage_count >= 5),
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
