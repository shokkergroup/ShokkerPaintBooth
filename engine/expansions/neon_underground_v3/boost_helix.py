"""Isolated Boost Helix owner-review pilot for ``neon2_plasma_tubes``.

SPB-105 | 2026-08-27 | owner verdict: "don't overthink: one solid
candidate, one obvious repair maximum."  The rejected tube treatment moves
from no accepted pilot to a causal pressure-cured ceramic whose short paired
facet remnants carry independent eight-tier M/R/Cc.  The audited movement is
M/R/Cc std 82.790/83.299/83.261, maximum absolute correlation 0.461, and
2.935 s maximum across four builds; the isolated manifest and audit retain
the full-precision measurements.

This module is intentionally unwired.  It imports only shared material-core
utilities and owns its carrier, packet grammar, paint composition, and causal
maps.  No continuous tube, coil, spiral, flow line, or unrelated spec field is
authored.
"""

from __future__ import annotations

import gc
import hashlib
import json
import math
import time
from pathlib import Path

import cv2
import numpy as np

from engine.paint_v2.neon_material_core_v3 import (
    GeometryMark,
    PilotResult,
    WORK,
    blur,
    pack_material,
    render_evidence,
    seeded,
    smoothstep,
    timed_result,
)


FINISH_ID = "neon2_plasma_tubes"
DISPLAY_NAME = "Boost Helix"
DEFAULT_SEED = 0xB0057E11
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.80, 0.94), np.float32)
_FACET_LOCAL = np.asarray(
    ((-1.00, -0.38), (-0.58, -1.00), (0.62, -0.78), (1.00, 0.18), (0.42, 1.00), (-0.80, 0.64)),
    np.float32,
)
_LEADING_LOCAL = np.asarray(
    ((-1.00, -0.42), (-0.52, -1.00), (0.76, -0.64), (1.00, 0.12), (0.34, 0.92), (-0.72, 0.54)),
    np.float32,
)
_COUNTER_LOCAL = np.asarray(
    ((-1.00, 0.08), (-0.38, -0.90), (0.72, -0.66), (1.00, 0.38), (0.12, 1.00), (-0.74, 0.66)),
    np.float32,
)


def _points(points: list[tuple[float, float]] | np.ndarray) -> np.ndarray:
    return np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))


def _stroke(
    mask: np.ndarray,
    points: list[tuple[float, float]],
    width: int,
    value: float,
    closed: bool = False,
) -> None:
    if len(points) >= 2:
        cv2.polylines(mask, [_points(points)], closed, float(value), int(width), cv2.LINE_AA)


def _fill(mask: np.ndarray, points: list[tuple[float, float]] | np.ndarray, value: float) -> None:
    if len(points) >= 3:
        cv2.fillConvexPoly(mask, _points(points), float(value), cv2.LINE_AA)


def _ellipse(
    mask: np.ndarray,
    center: tuple[float, float],
    axes: tuple[int, int],
    angle: float,
    value: float,
) -> None:
    cv2.ellipse(
        mask,
        (int(round(center[0])), int(round(center[1]))),
        (int(axes[0]), int(axes[1])),
        float(angle),
        0.0,
        360.0,
        float(value),
        -1,
        cv2.LINE_AA,
    )


def _local_point(
    center: tuple[float, float],
    angle: float,
    along: float,
    across: float,
) -> tuple[float, float]:
    ca, sa = math.cos(angle), math.sin(angle)
    return (
        center[0] + ca * along - sa * across,
        center[1] + sa * along + ca * across,
    )


def _offset_path(
    points: list[tuple[float, float]],
    angle: float,
    distance: float,
) -> list[tuple[float, float]]:
    nx, ny = -math.sin(angle), math.cos(angle)
    return [(x + nx * distance, y + ny * distance) for x, y in points]


def _facet_polygon(
    center: tuple[float, float],
    half_length: float,
    half_width: float,
    angle: float,
    rng: np.random.Generator,
    template: np.ndarray = _FACET_LOCAL,
) -> np.ndarray:
    jitter = rng.uniform((-0.10, -0.12), (0.10, 0.12), size=(6, 2)).astype(np.float32)
    local = (template + jitter) * np.asarray((half_length, half_width), np.float32)
    ca, sa = math.cos(angle), math.sin(angle)
    rotation = np.asarray(((ca, -sa), (sa, ca)), np.float32)
    world = local @ rotation.T
    world += np.asarray(center, np.float32)
    return np.rint(world).astype(np.int32)


def _accumulate_facet(
    body: np.ndarray,
    depth: np.ndarray,
    phase: np.ndarray,
    energy: np.ndarray,
    polygon: np.ndarray,
    opacity: float,
    phase_value: float,
    energy_value: float,
) -> None:
    h, w = body.shape
    mins = polygon.min(axis=0)
    maxs = polygon.max(axis=0)
    x0 = max(0, int(mins[0]) - 2)
    y0 = max(0, int(mins[1]) - 2)
    x1 = min(w, int(maxs[0]) + 3)
    y1 = min(h, int(maxs[1]) + 3)
    if x1 <= x0 or y1 <= y0:
        return
    local = np.zeros((y1 - y0, x1 - x0), np.uint8)
    shifted = polygon.copy()
    shifted[:, 0] -= x0
    shifted[:, 1] -= y0
    cv2.fillConvexPoly(local, shifted.reshape((-1, 1, 2)), 255, cv2.LINE_AA)
    alpha = local.astype(np.float32) / 255.0
    effective = alpha * float(opacity)
    body_roi = body[y0:y1, x0:x1]
    body_roi[:] = 1.0 - (1.0 - body_roi) * (1.0 - effective)
    depth[y0:y1, x0:x1] += (alpha > 0.20).astype(np.float32)
    phase_roi = phase[y0:y1, x0:x1]
    energy_roi = energy[y0:y1, x0:x1]
    phase_roi[:] = phase_roi * (1.0 - effective) + float(phase_value) * effective
    energy_roi[:] = energy_roi * (1.0 - effective) + float(energy_value) * effective


def _palette(
    values: np.ndarray,
    anchors: tuple[tuple[float, float, float], ...],
    support: np.ndarray,
) -> np.ndarray:
    palette = np.asarray(anchors, np.float32)
    active = np.asarray(support, bool)
    selected = np.asarray(values, np.float32)[active]
    p = np.mod(selected, 1.0) * (len(anchors) - 1)
    index = np.floor(p).astype(np.int32)
    fraction = p - index
    result = np.zeros((*values.shape, 3), np.float32)
    result[active] = palette[index] * (1.0 - fraction[:, None]) + palette[index + 1] * fraction[:, None]
    return result


def _ceramic_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.06, 0.15, 0.20),
            (0.16, 0.09, 0.22),
            (0.20, 0.14, 0.09),
            (0.07, 0.21, 0.18),
            (0.06, 0.15, 0.20),
        ),
        support,
    )


def _cyan_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.08, 0.58, 0.88),
            (0.18, 0.92, 0.76),
            (0.28, 0.66, 1.00),
            (0.12, 0.78, 0.82),
            (0.08, 0.58, 0.88),
        ),
        support,
    )


def _magenta_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.54, 0.12, 0.66),
            (0.92, 0.22, 0.68),
            (0.58, 0.28, 0.96),
            (0.82, 0.34, 0.56),
            (0.54, 0.12, 0.66),
        ),
        support,
    )


def _oxide_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.66, 0.30, 0.10),
            (0.26, 0.66, 0.50),
            (0.82, 0.48, 0.16),
            (0.34, 0.50, 0.62),
            (0.66, 0.30, 0.10),
        ),
        support,
    )


def _compose_paint(
    ceramic_body: np.ndarray,
    ceramic_phase: np.ndarray,
    ceramic_energy: np.ndarray,
    cyan_faces: np.ndarray,
    cyan_phase: np.ndarray,
    magenta_faces: np.ndarray,
    magenta_phase: np.ndarray,
    compression_nodes: np.ndarray,
    clipped_ends: np.ndarray,
    collapsed_necks: np.ndarray,
    sheath_ghosts: np.ndarray,
    sheath_phase: np.ndarray,
    oxide_chips: np.ndarray,
    oxide_phase: np.ndarray,
    pressure_gaps: np.ndarray,
    buried_flashes: np.ndarray,
) -> np.ndarray:
    h, w = ceramic_body.shape
    paint = np.zeros((h, w, 3), np.float32)
    paint[:] = np.asarray((0.010, 0.013, 0.018), np.float32)

    ceramic_color = _ceramic_palette(ceramic_phase, ceramic_body > 0.0)
    body_raw = ceramic_color * (ceramic_body * (0.16 + 0.21 * ceramic_energy))[..., None]
    body_soft = np.stack(tuple(blur(body_raw[..., i], 11.0, h) for i in range(3)), axis=2)
    paint += 1.45 * body_soft
    paint += ceramic_color * (ceramic_body * (0.060 + 0.080 * ceramic_energy))[..., None]
    paint += blur(ceramic_body, 14.0, h)[..., None] * np.asarray((0.034, 0.041, 0.052), np.float32)

    cyan_color = _cyan_palette(cyan_phase, cyan_faces > 0.0)
    magenta_support = (magenta_faces > 0.0) | (buried_flashes > 0.0)
    magenta_color = _magenta_palette(magenta_phase, magenta_support)
    sheath_color = _magenta_palette(sheath_phase, sheath_ghosts > 0.0)
    oxide_color = _oxide_palette(oxide_phase, oxide_chips > 0.0)
    paint += cyan_color * (0.25 * cyan_faces + 0.24 * np.power(cyan_faces, 2.0))[..., None]
    paint += magenta_color * (0.22 * magenta_faces + 0.21 * np.power(magenta_faces, 2.0))[..., None]
    paint += sheath_color * (0.14 * sheath_ghosts + 0.10 * np.power(sheath_ghosts, 2.0))[..., None]
    paint += oxide_color * (0.26 * oxide_chips + 0.18 * np.power(oxide_chips, 2.0))[..., None]
    paint += (0.72 + 0.28 * cyan_color) * (0.34 * compression_nodes)[..., None]
    paint += (0.42 * cyan_color + 0.30 * magenta_color + 0.28) * (0.19 * clipped_ends)[..., None]
    paint += (0.46 * ceramic_color + 0.54 * magenta_color) * (0.15 * buried_flashes)[..., None]

    paint *= 1.0 - 0.38 * collapsed_necks[..., None]
    paint *= 1.0 - 0.46 * pressure_gaps[..., None]
    paint += collapsed_necks[..., None] * np.asarray((0.003, 0.005, 0.010), np.float32)
    paint += pressure_gaps[..., None] * np.asarray((0.002, 0.003, 0.006), np.float32)
    return np.clip(paint, 0.0, 1.0)


def build_boost_helix(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build deterministic paired facet remnants and causal M/R/Cc."""
    if int(size) < 256:
        raise ValueError("Boost Helix requires a work raster of at least 256px")
    rng = seeded(seed)
    h = w = int(size)
    shape = (h, w)
    scale = float(size) / float(WORK)

    ceramic_body = np.zeros(shape, np.float32)
    ceramic_depth = np.zeros(shape, np.float32)
    ceramic_phase = np.zeros(shape, np.float32)
    ceramic_energy = np.zeros(shape, np.float32)
    cyan_faces = np.zeros(shape, np.float32)
    cyan_phase = np.zeros(shape, np.float32)
    magenta_faces = np.zeros(shape, np.float32)
    magenta_phase = np.zeros(shape, np.float32)
    compression_nodes = np.zeros(shape, np.float32)
    clipped_ends = np.zeros(shape, np.float32)
    collapsed_necks = np.zeros(shape, np.float32)
    sheath_ghosts = np.zeros(shape, np.float32)
    sheath_phase = np.zeros(shape, np.float32)
    oxide_chips = np.zeros(shape, np.float32)
    oxide_phase = np.zeros(shape, np.float32)
    pressure_gaps = np.zeros(shape, np.float32)

    counts = {
        "pressure_cured_ceramic_facets": 0,
        "cyan_leading_faces": 0,
        "magenta_counterfaces": 0,
        "white_compression_nodes": 0,
        "clipped_filament_ends": 0,
        "collapsed_necks": 0,
        "violet_sheath_ghosts": 0,
        "oxide_chips": 0,
        "dark_pressure_gaps": 0,
    }

    cell = max(14, int(round(20.0 * scale)))
    for gy, y0 in enumerate(range(-cell, h + cell, cell)):
        for gx, x0 in enumerate(range(-cell, w + cell, cell)):
            if rng.random() < 0.025:
                continue
            center = (
                float(x0 + rng.uniform(-0.47, 0.47) * cell),
                float(y0 + rng.uniform(-0.47, 0.47) * cell),
            )
            block_x, block_y = gx // 3, gy // 3
            block_hash = (
                (block_x * 0x9E3779B1)
                ^ (block_y * 0x85EBCA77)
                ^ ((block_x + 3 * block_y) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_angle = (block_hash % 37) * (math.pi / 37.0) + float(rng.uniform(-0.62, 0.62))
            base_phase = float(((block_hash % 211) / 211.0 + rng.uniform(-0.08, 0.08)) % 1.0)
            grammar = int(rng.integers(0, 5))

            facet_total = int(rng.integers(2, 6))
            for facet_index in range(facet_total):
                t = (facet_index - 0.5 * (facet_total - 1)) / max(facet_total - 1, 1)
                facet_angle = base_angle + float(rng.uniform(-0.52, 0.52))
                if grammar == 1:
                    facet_angle += t * 0.58
                elif grammar == 2:
                    facet_angle += 0.26 if facet_index % 2 else -0.31
                elif grammar == 4:
                    facet_angle -= t * 0.46
                facet_center = _local_point(
                    center,
                    base_angle,
                    t * rng.uniform(7.5, 12.5) * scale,
                    rng.uniform(-4.3, 4.3) * scale,
                )
                half_length = float(rng.uniform(4.1, 7.2) * scale)
                half_width = float(rng.uniform(2.8, 4.8) * scale)
                tier_index = int(rng.integers(0, 8))
                tier = float(EVENT_TIERS[tier_index])
                optical_phase = float((base_phase + 0.09 * t + 0.017 * tier_index) % 1.0)
                polygon = _facet_polygon(facet_center, half_length, half_width, facet_angle, rng)
                _accumulate_facet(
                    ceramic_body,
                    ceramic_depth,
                    ceramic_phase,
                    ceramic_energy,
                    polygon,
                    0.22 + 0.38 * tier,
                    optical_phase,
                    tier,
                )
                counts["pressure_cured_ceramic_facets"] += 1

            sliver_angle = base_angle + float(rng.uniform(-0.34, 0.34))
            handed = -1.0 if grammar in (1, 4) else 1.0
            along_shift = float(rng.uniform(-2.5, 2.5) * scale)
            across = float(rng.uniform(2.3, 4.2) * scale)
            cyan_center = _local_point(center, sliver_angle, along_shift - rng.uniform(0.6, 2.2) * scale, -across)
            magenta_center = _local_point(
                center,
                sliver_angle,
                along_shift + handed * rng.uniform(1.7, 4.0) * scale,
                across * rng.uniform(0.72, 1.18),
            )
            cyan_angle = sliver_angle + float(rng.uniform(-0.20, 0.18))
            magenta_angle = sliver_angle + handed * float(rng.uniform(0.14, 0.42))
            cyan_half_l = float(rng.uniform(4.2, 7.0) * scale)
            magenta_half_l = float(rng.uniform(3.8, 6.7) * scale)
            cyan_half_w = float(rng.uniform(2.2, 3.5) * scale)
            magenta_half_w = float(rng.uniform(2.1, 3.4) * scale)
            cyan_poly = _facet_polygon(
                cyan_center, cyan_half_l, cyan_half_w, cyan_angle, rng, _LEADING_LOCAL
            )
            magenta_poly = _facet_polygon(
                magenta_center, magenta_half_l, magenta_half_w, magenta_angle, rng, _COUNTER_LOCAL
            )
            cyan_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            magenta_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            _fill(cyan_faces, cyan_poly, 0.18 + 0.70 * cyan_tier)
            _fill(cyan_phase, cyan_poly, 0.07 + 0.86 * ((base_phase + 0.22) % 1.0))
            _fill(magenta_faces, magenta_poly, 0.18 + 0.70 * magenta_tier)
            _fill(magenta_phase, magenta_poly, 0.07 + 0.86 * ((base_phase + 0.54) % 1.0))
            counts["cyan_leading_faces"] += 1
            counts["magenta_counterfaces"] += 1

            bridge_angle = sliver_angle + handed * float(rng.uniform(0.04, 0.18))
            bridge_half = float(rng.uniform(2.4, 4.2) * scale)
            bridge_center = _local_point(center, sliver_angle, along_shift, rng.uniform(-1.0, 1.0) * scale)
            b0 = _local_point(bridge_center, bridge_angle, -bridge_half, 0.0)
            bk = _local_point(bridge_center, bridge_angle, 0.0, handed * rng.uniform(0.8, 1.8) * scale)
            b1 = _local_point(bridge_center, bridge_angle, bridge_half, 0.0)

            if rng.random() < 0.62:
                axes = (
                    max(2, int(round(rng.uniform(2.0, 3.1) * scale))),
                    max(2, int(round(rng.uniform(2.0, 3.5) * scale))),
                )
                _ellipse(
                    compression_nodes,
                    bridge_center,
                    axes,
                    math.degrees(bridge_angle + rng.uniform(-0.45, 0.45)),
                    float(EVENT_TIERS[int(rng.integers(1, 8))]),
                )
                counts["white_compression_nodes"] += 1

            end_source = cyan_center if rng.random() < 0.5 else magenta_center
            end_angle = cyan_angle if end_source is cyan_center else magenta_angle
            end_point = _local_point(end_source, end_angle, rng.choice((-1.0, 1.0)) * rng.uniform(3.2, 5.2) * scale, 0.0)
            end_half = float(rng.uniform(2.1, 3.7) * scale)
            e0 = _local_point(end_point, end_angle + math.pi * 0.5, -end_half, 0.0)
            e1 = _local_point(end_point, end_angle + math.pi * 0.5, end_half, 0.0)
            end_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
            _stroke(clipped_ends, [e0, end_point, e1], end_w, float(EVENT_TIERS[int(rng.integers(0, 8))]))
            counts["clipped_filament_ends"] += 1

            neck_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
            _stroke(collapsed_necks, [b0, bk, b1], neck_w, 0.20 + 0.66 * magenta_tier)
            counts["collapsed_necks"] += 1

            ghost_shift = handed * float(rng.uniform(2.7, 4.6) * scale)
            ghost_half = float(rng.uniform(3.8, 6.2) * scale)
            g0 = _local_point(bridge_center, sliver_angle, -ghost_half, ghost_shift)
            gk = _local_point(
                bridge_center,
                sliver_angle,
                rng.uniform(-0.8, 0.8) * scale,
                ghost_shift + rng.uniform(-1.2, 1.2) * scale,
            )
            g1 = _local_point(bridge_center, sliver_angle, ghost_half, ghost_shift * 0.72)
            ghost_path = [g0, gk, g1]
            ghost_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
            ghost_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            _stroke(sheath_ghosts, ghost_path, ghost_w, 0.16 + 0.60 * ghost_tier)
            _stroke(sheath_phase, ghost_path, ghost_w, 0.07 + 0.86 * ((base_phase + 0.70) % 1.0))
            counts["violet_sheath_ghosts"] += 1

            if rng.random() < 0.74:
                chip_center = _local_point(
                    end_point,
                    end_angle,
                    rng.uniform(-1.8, 1.8) * scale,
                    rng.uniform(-2.2, 2.2) * scale,
                )
                chip_l = float(rng.uniform(2.2, 3.8) * scale)
                chip_w = float(rng.uniform(2.1, 3.5) * scale)
                chip = _facet_polygon(chip_center, chip_l, chip_w, end_angle + rng.uniform(-0.7, 0.7), rng)
                chip_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                _fill(oxide_chips, chip, 0.18 + 0.68 * chip_tier)
                _fill(oxide_phase, chip, 0.07 + 0.86 * ((base_phase + 0.84) % 1.0))
                counts["oxide_chips"] += 1

            gap_angle = sliver_angle + math.pi * 0.5 + rng.uniform(-0.36, 0.36)
            gap_half = float(rng.uniform(2.2, 4.0) * scale)
            gap_center = _local_point(center, sliver_angle, rng.uniform(-2.5, 2.5) * scale, rng.uniform(-1.8, 1.8) * scale)
            p0 = _local_point(gap_center, gap_angle, -gap_half, 0.0)
            pk = _local_point(gap_center, gap_angle, 0.0, rng.uniform(-1.1, 1.1) * scale)
            p1 = _local_point(gap_center, gap_angle, gap_half, 0.0)
            gap_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
            _stroke(pressure_gaps, [p0, pk, p1], gap_w, 0.20 + 0.66 * cyan_tier)
            counts["dark_pressure_gaps"] += 1

    buried_flashes = smoothstep(1.45, 3.10, ceramic_depth) * ceramic_body
    buried_flashes *= 0.40 + 0.60 * ceramic_energy

    paint = _compose_paint(
        ceramic_body,
        ceramic_phase,
        ceramic_energy,
        cyan_faces,
        cyan_phase,
        magenta_faces,
        magenta_phase,
        compression_nodes,
        clipped_ends,
        collapsed_necks,
        sheath_ghosts,
        sheath_phase,
        oxide_chips,
        oxide_phase,
        pressure_gaps,
        buried_flashes,
    )

    # SPB-105 / 2026-08-27 owner verdict: retain the clipped 8-32px pressure
    # anatomy while restoring a decisive cyan/magenta Neon read. Official
    # isolated M7 before calibration: 68.8 (M6 saturation miss); the rerun
    # reached 83.4 after saturation passed but exposed weak picker luminance.
    # This final exposure lift targets that owner-eye/M5 weakness with causal
    # masks, feature scale, and material maps intact. Movement: 68.8 -> 83.4
    # -> 85.6.
    hsv = cv2.cvtColor(np.clip(paint, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.65, 0.0, 1.0)
    paint = np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 1.45, 0.0, 1.0)

    metal_reach = blur(np.maximum.reduce((cyan_faces, compression_nodes, oxide_chips, clipped_ends)), 17.0, size)
    rough_reach = blur(np.maximum.reduce((collapsed_necks, oxide_chips, pressure_gaps)), 15.0, size)
    coat_reach = blur(np.maximum.reduce((ceramic_body, magenta_faces, sheath_ghosts)), 15.0, size)
    m_score = (
        2.18 * compression_nodes
        + 1.94 * cyan_faces
        + 1.54 * oxide_chips
        + 1.20 * clipped_ends
        + 0.82 * buried_flashes
        + 0.38 * metal_reach
        + 0.22 * magenta_faces
        - 0.74 * pressure_gaps
        - 0.34 * ceramic_body
    )
    r_score = (
        2.12 * pressure_gaps
        + 1.86 * oxide_chips
        + 1.48 * clipped_ends
        + 1.24 * collapsed_necks
        + 0.42 * rough_reach
        + 0.26 * compression_nodes
        - 1.02 * cyan_faces
        - 0.58 * ceramic_body
    )
    c_score = (
        1.66 * ceramic_body
        + 1.38 * sheath_ghosts
        + 1.14 * magenta_faces
        + 0.72 * buried_flashes
        + 0.34 * coat_reach
        + 0.18 * cyan_faces
        - 1.76 * pressure_gaps
        - 1.42 * collapsed_necks
        - 1.18 * clipped_ends
        - 0.84 * compression_nodes
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "pressure_cured_ceramic_facets": ceramic_body,
        "cyan_leading_faces": cyan_faces,
        "magenta_counterfaces": magenta_faces,
        "white_compression_nodes": compression_nodes,
        "clipped_filament_ends": clipped_ends,
        "collapsed_necks": collapsed_necks,
        "violet_sheath_ghosts": sheath_ghosts,
        "oxide_chips": oxide_chips,
        "dark_pressure_gaps": pressure_gaps,
        "buried_overlap_flashes": buried_flashes,
    }
    geometry = (
        GeometryMark("pressure_cured_ceramic_facets", 28.0, counts["pressure_cured_ceramic_facets"]),
        GeometryMark("cyan_leading_faces", 26.0, counts["cyan_leading_faces"]),
        GeometryMark("magenta_counterfaces", 24.0, counts["magenta_counterfaces"]),
        GeometryMark("white_compression_nodes", 10.0, counts["white_compression_nodes"]),
        GeometryMark("clipped_filament_ends", 12.0, counts["clipped_filament_ends"]),
        GeometryMark("collapsed_necks", 10.0, counts["collapsed_necks"]),
        GeometryMark("violet_sheath_ghosts", 22.0, counts["violet_sheath_ghosts"]),
        GeometryMark("oxide_chips", 12.0, counts["oxide_chips"]),
        GeometryMark("dark_pressure_gaps", 10.0, counts["dark_pressure_gaps"]),
        GeometryMark("buried_overlap_flashes", 18.0, counts["pressure_cured_ceramic_facets"]),
    )
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "white compression nodes, cyan leading faces, oxide chips, clipped conductive ends, and buried overlap",
            "R": "dark pressure gaps, oxide fractures, clipped ends, collapsed necks, and compressed junctions",
            "Cc": "intact pressure-cured ceramic, violet sheath ghosts, magenta counterfaces, and buried overlaps; low at collapse",
        },
        carrier="black pressure-cured ceramic densely loaded with clipped organic 8-32px paired plasma-facet remnants",
        vetoes=(
            "no tubes, long coils, spirals, springs, worms, or flow lines",
            "no DNA icons, rows, grids, or repeated S/X stamps",
            "no unrelated noise/spec underlay",
        ),
    )


def _write_audit(result: PilotResult, output: Path) -> dict[str, object]:
    repeat_times: list[float] = []
    paint_hashes = [hashlib.sha256(result.paint.tobytes()).hexdigest()]
    spec_hashes = [hashlib.sha256(result.spec.tobytes()).hexdigest()]
    for _ in range(3):
        gc.collect()
        start = time.perf_counter()
        repeat = build_boost_helix()
        repeat_times.append(time.perf_counter() - start)
        paint_hashes.append(hashlib.sha256(repeat.paint.tobytes()).hexdigest())
        spec_hashes.append(hashlib.sha256(repeat.spec.tobytes()).hexdigest())
        del repeat

    union = np.maximum.reduce(tuple(np.asarray(mask, np.float32) for mask in result.masks.values()))
    border = np.zeros(union.shape, bool)
    border[:16, :] = True
    border[-16:, :] = True
    border[:, :16] = True
    border[:, -16:] = True
    correlations = (
        float(np.corrcoef(result.spec[..., 0].ravel(), result.spec[..., 1].ravel())[0, 1]),
        float(np.corrcoef(result.spec[..., 0].ravel(), result.spec[..., 2].ravel())[0, 1]),
        float(np.corrcoef(result.spec[..., 1].ravel(), result.spec[..., 2].ravel())[0, 1]),
    )
    audit = {
        "schema": "spb-neon-oil-slick-pilot-audit/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": result.finish_id,
        "deterministic_4_of_4": len(set(paint_hashes)) == 1 and len(set(spec_hashes)) == 1,
        "paint_sha256": paint_hashes[0],
        "spec_sha256": spec_hashes[0],
        "builder_timings_seconds": [round(float(result.elapsed_seconds), 6)]
        + [round(float(value), 6) for value in repeat_times],
        "builder_max_seconds": round(float(max([result.elapsed_seconds, *repeat_times])), 6),
        "all_causal_union_coverage": round(float(np.mean(union > 0.15)), 6),
        "edge_union_coverage": round(float(np.mean(union[border] > 0.15)), 6),
        "interior_union_coverage": round(float(np.mean(union[~border] > 0.15)), 6),
        "max_abs_material_correlation": round(max(abs(value) for value in correlations), 6),
        "official_m7": "UNAVAILABLE_WHILE_ISOLATED_AND_UNREGISTERED",
        "visual_contacts": [
            "paint_2048.png",
            "detail_1to1_1024.png",
            "material_contact.png",
            "light_sweep_contact.png",
            "causal_masks_contact.png",
            "paint_128.png",
            "paint_64.png",
        ],
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    project_root = Path(__file__).resolve().parents[3]
    output = project_root / "_neon_oil_slick_reset_work" / "boost_helix"
    result = timed_result(build_boost_helix)
    manifest = render_evidence(result, output)
    audit = _write_audit(result, output)
    print(json.dumps({"manifest": manifest, "audit": audit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
