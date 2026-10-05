"""Isolated Live Mesh Delam owner-review pilot for ``neon2_wireframe``.

SPB-105 | 2026-08-27 | owner verdict: "don't overthink: one solid
candidate, one obvious repair maximum."  The rejected wireframe treatment is
replaced by one causal black conductive laminate containing clipped, locally
delaminated interlace remnants.  Exact movement from no accepted pilot to the
candidate is M/R/Cc std 82.790/83.299/83.261, max absolute correlation 0.382,
and 2.547 s maximum across four audited builds.  The generated manifest and
audit retain the full-precision measurements.

This module is intentionally unwired.  It imports only shared material-core
utilities and owns its carrier, packet grammar, paint composition, and causal
maps.  No continuous net, grid, hue noise, or unrelated spec underlay exists.
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


FINISH_ID = "neon2_wireframe"
DISPLAY_NAME = "Live Mesh Delam"
DEFAULT_SEED = 0x1A7E5EED
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.80, 0.94), np.float32)
_RIBBON_LOCAL = np.asarray(
    ((-1.00, -0.36), (-0.72, -1.00), (0.62, -0.86), (1.00, 0.22), (0.54, 1.00), (-0.82, 0.70)),
    np.float32,
)


def _points(points: list[tuple[float, float]]) -> np.ndarray:
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


def _fill(mask: np.ndarray, points: list[tuple[float, float]], value: float) -> None:
    if len(points) >= 3:
        cv2.fillConvexPoly(mask, _points(points), float(value), cv2.LINE_AA)


def _disc(mask: np.ndarray, center: tuple[float, float], radius: int, value: float) -> None:
    cv2.circle(
        mask,
        (int(round(center[0])), int(round(center[1]))),
        int(radius),
        float(value),
        -1,
        cv2.LINE_AA,
    )


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


def _ribbon_polygon(
    center: tuple[float, float],
    half_length: float,
    half_width: float,
    angle: float,
    rng: np.random.Generator,
) -> np.ndarray:
    jitter = rng.uniform((-0.11, -0.13), (0.11, 0.13), size=(6, 2)).astype(np.float32)
    local = (_RIBBON_LOCAL + jitter) * np.asarray((half_length, half_width), np.float32)
    ca, sa = math.cos(angle), math.sin(angle)
    rotation = np.asarray(((ca, -sa), (sa, ca)), np.float32)
    world = local @ rotation.T
    world += np.asarray(center, np.float32)
    return np.rint(world).astype(np.int32)


def _accumulate_fragment(
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
    p = polygon
    mins = p.min(axis=0)
    maxs = p.max(axis=0)
    x0 = max(0, int(mins[0]) - 2)
    y0 = max(0, int(mins[1]) - 2)
    x1 = min(w, int(maxs[0]) + 3)
    y1 = min(h, int(maxs[1]) + 3)
    if x1 <= x0 or y1 <= y0:
        return
    local = np.zeros((y1 - y0, x1 - x0), np.uint8)
    shifted = p.copy()
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
    period = len(anchors) - 1
    active = np.asarray(support, bool)
    selected = np.asarray(values, np.float32)[active]
    p = np.mod(selected, 1.0) * period
    index = np.floor(p).astype(np.int32)
    fraction = p - index
    result = np.zeros((*values.shape, 3), np.float32)
    result[active] = palette[index] * (1.0 - fraction[:, None]) + palette[index + 1] * fraction[:, None]
    return result


def _laminate_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.07, 0.18, 0.22),
            (0.18, 0.10, 0.24),
            (0.22, 0.14, 0.09),
            (0.08, 0.23, 0.20),
            (0.07, 0.18, 0.22),
        ),
        support,
    )


def _mesh_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.18, 0.42, 0.48),
            (0.34, 0.56, 0.64),
            (0.48, 0.32, 0.56),
            (0.54, 0.40, 0.24),
            (0.18, 0.42, 0.48),
        ),
        support,
    )


def _cyan_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.10, 0.68, 0.92),
            (0.24, 0.96, 0.76),
            (0.34, 0.72, 1.00),
            (0.18, 0.82, 0.86),
            (0.10, 0.68, 0.92),
        ),
        support,
    )


def _magenta_palette(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.60, 0.16, 0.68),
            (0.94, 0.28, 0.72),
            (0.62, 0.32, 0.98),
            (0.86, 0.40, 0.60),
            (0.60, 0.16, 0.68),
        ),
        support,
    )


def _compose_paint(
    fragment_body: np.ndarray,
    fragment_phase: np.ndarray,
    fragment_energy: np.ndarray,
    interlace_strips: np.ndarray,
    strip_phase: np.ndarray,
    cyan_crossings: np.ndarray,
    cyan_phase: np.ndarray,
    underfilm_ghosts: np.ndarray,
    ghost_phase: np.ndarray,
    copper_lips: np.ndarray,
    strand_ends: np.ndarray,
    junction_beads: np.ndarray,
    torn_windows: np.ndarray,
    blister_shadows: np.ndarray,
    adhesive_gaps: np.ndarray,
    buried_overlap: np.ndarray,
) -> np.ndarray:
    h, w = fragment_body.shape
    paint = np.zeros((h, w, 3), np.float32)
    paint[:] = np.asarray((0.012, 0.016, 0.020), np.float32)

    laminate_color = _laminate_palette(fragment_phase, fragment_body > 0.0)
    body_raw = laminate_color * (fragment_body * (0.170 + 0.22 * fragment_energy))[..., None]
    body_soft = np.stack(tuple(blur(body_raw[..., i], 11.0, h) for i in range(3)), axis=2)
    paint += 1.55 * body_soft
    paint += laminate_color * (fragment_body * (0.060 + 0.075 * fragment_energy))[..., None]
    paint += blur(fragment_body, 14.0, h)[..., None] * np.asarray((0.040, 0.050, 0.060), np.float32)

    mesh_support = (
        (interlace_strips > 0.0)
        | (copper_lips > 0.0)
        | (strand_ends > 0.0)
        | (junction_beads > 0.0)
        | (buried_overlap > 0.0)
    )
    magenta_support = (underfilm_ghosts > 0.0) | (buried_overlap > 0.0)
    mesh_color = _mesh_palette(strip_phase, mesh_support)
    cyan_color = _cyan_palette(cyan_phase, cyan_crossings > 0.0)
    magenta_color = _magenta_palette(ghost_phase, magenta_support)
    copper_color = np.clip(
        0.48 * mesh_color + np.asarray((0.48, 0.19, 0.065), np.float32),
        0.0,
        1.0,
    )
    paint += mesh_color * (0.28 * interlace_strips + 0.26 * np.power(interlace_strips, 2.0))[..., None]
    paint += cyan_color * (0.22 * cyan_crossings + 0.24 * np.power(cyan_crossings, 2.0))[..., None]
    paint += magenta_color * (0.13 * underfilm_ghosts + 0.12 * np.power(underfilm_ghosts, 2.0))[..., None]
    paint += copper_color * (0.26 * copper_lips + 0.18 * strand_ends)[..., None]
    paint += (0.44 * copper_color + 0.56) * (0.22 * junction_beads)[..., None]
    paint += (0.48 * mesh_color + 0.52 * magenta_color) * (0.16 * buried_overlap)[..., None]

    # Damage is internal to a packet; no dark line can connect into a net.
    paint *= 1.0 - 0.35 * torn_windows[..., None]
    paint *= 1.0 - 0.30 * blister_shadows[..., None]
    paint *= 1.0 - 0.44 * adhesive_gaps[..., None]
    paint += torn_windows[..., None] * np.asarray((0.004, 0.006, 0.010), np.float32)
    paint += blister_shadows[..., None] * np.asarray((0.003, 0.006, 0.010), np.float32)
    paint += adhesive_gaps[..., None] * np.asarray((0.002, 0.003, 0.005), np.float32)
    return np.clip(paint, 0.0, 1.0)


def build_live_mesh_delam(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build deterministic delaminated micro-interlace and causal M/R/Cc."""
    if int(size) < 256:
        raise ValueError("Live Mesh Delam requires a work raster of at least 256px")
    rng = seeded(seed)
    h = w = int(size)
    shape = (h, w)
    scale = float(size) / float(WORK)

    fragment_body = np.zeros(shape, np.float32)
    fragment_depth = np.zeros(shape, np.float32)
    fragment_phase = np.zeros(shape, np.float32)
    fragment_energy = np.zeros(shape, np.float32)
    interlace_strips = np.zeros(shape, np.float32)
    strip_phase = np.zeros(shape, np.float32)
    cyan_crossings = np.zeros(shape, np.float32)
    cyan_phase = np.zeros(shape, np.float32)
    underfilm_ghosts = np.zeros(shape, np.float32)
    ghost_phase = np.zeros(shape, np.float32)
    copper_lips = np.zeros(shape, np.float32)
    strand_ends = np.zeros(shape, np.float32)
    junction_beads = np.zeros(shape, np.float32)
    torn_windows = np.zeros(shape, np.float32)
    blister_shadows = np.zeros(shape, np.float32)
    adhesive_gaps = np.zeros(shape, np.float32)

    counts = {
        "delaminated_mesh_fragments": 0,
        "short_broken_interlace_strips": 0,
        "cyan_exposed_crossings": 0,
        "magenta_underfilm_ghosts": 0,
        "lifted_copper_lips": 0,
        "clipped_strand_ends": 0,
        "fused_junction_beads": 0,
        "torn_windows": 0,
        "blister_shadows": 0,
        "dark_adhesive_gaps": 0,
    }

    cell = max(14, int(round(20.0 * scale)))
    for gy, y0 in enumerate(range(-cell, h + cell, cell)):
        for gx, x0 in enumerate(range(-cell, w + cell, cell)):
            if rng.random() < 0.025:
                continue
            center = (
                float(x0 + rng.uniform(-0.46, 0.46) * cell),
                float(y0 + rng.uniform(-0.46, 0.46) * cell),
            )
            block_x, block_y = gx // 3, gy // 3
            block_hash = (
                (block_x * 0x9E3779B1)
                ^ (block_y * 0x85EBCA77)
                ^ ((2 * block_x + block_y) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_angle = (block_hash % 30) * (math.pi / 30.0) + float(rng.uniform(-0.48, 0.48))
            base_phase = float(((block_hash % 197) / 197.0 + rng.uniform(-0.07, 0.07)) % 1.0)
            grammar = int(rng.integers(0, 4))

            fragment_total = int(rng.integers(2, 6))
            for fragment_index in range(fragment_total):
                t = (fragment_index - 0.5 * (fragment_total - 1)) / max(fragment_total - 1, 1)
                fragment_angle = base_angle + float(rng.uniform(-0.44, 0.44))
                if grammar == 1:
                    fragment_angle += t * 0.72
                elif grammar == 2:
                    fragment_angle += (0.30 if fragment_index % 2 else -0.22)
                fragment_center = _local_point(
                    center,
                    base_angle,
                    t * rng.uniform(8.0, 13.0) * scale,
                    rng.uniform(-4.2, 4.2) * scale,
                )
                half_length = float(rng.uniform(4.3, 7.4) * scale)
                half_width = float(rng.uniform(3.0, 4.9) * scale)
                tier_index = int(rng.integers(0, 8))
                tier = float(EVENT_TIERS[tier_index])
                optical_phase = float((base_phase + 0.08 * t + 0.014 * tier_index) % 1.0)
                polygon = _ribbon_polygon(fragment_center, half_length, half_width, fragment_angle, rng)
                _accumulate_fragment(
                    fragment_body,
                    fragment_depth,
                    fragment_phase,
                    fragment_energy,
                    polygon,
                    0.23 + 0.39 * tier,
                    optical_phase,
                    tier,
                )
                counts["delaminated_mesh_fragments"] += 1

            primary_angle = base_angle + float(rng.uniform(-0.24, 0.24))
            secondary_delta = (
                rng.uniform(0.52, 0.84)
                if grammar == 0
                else rng.uniform(0.24, 0.46)
                if grammar == 1
                else -rng.uniform(0.62, 1.02)
                if grammar == 2
                else rng.uniform(0.94, 1.30)
            )
            secondary_angle = primary_angle + float(secondary_delta)
            crossing = _local_point(
                center,
                primary_angle,
                rng.uniform(-2.2, 2.2) * scale,
                rng.uniform(-2.0, 2.0) * scale,
            )
            primary_half = float(rng.uniform(5.0, 7.8) * scale)
            secondary_half = float(rng.uniform(4.2, 6.8) * scale)
            p0 = _local_point(crossing, primary_angle, -primary_half, rng.uniform(-0.8, 0.8) * scale)
            pk = _local_point(crossing, primary_angle, rng.uniform(-0.8, 0.8) * scale, rng.uniform(-1.4, 1.4) * scale)
            p1 = _local_point(crossing, primary_angle, primary_half, rng.uniform(-0.8, 0.8) * scale)
            q0 = _local_point(crossing, secondary_angle, -secondary_half, rng.uniform(-0.7, 0.7) * scale)
            qk = _local_point(crossing, secondary_angle, rng.uniform(-0.7, 0.7) * scale, rng.uniform(-1.1, 1.1) * scale)
            q1 = _local_point(crossing, secondary_angle, secondary_half, rng.uniform(-0.7, 0.7) * scale)
            primary_path = [p0, pk, p1]
            secondary_path = [q0, qk, q1]

            strip_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
            primary_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            secondary_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            _stroke(interlace_strips, primary_path, strip_w, primary_tier)
            _stroke(strip_phase, primary_path, strip_w, 0.07 + 0.86 * base_phase)
            _stroke(interlace_strips, secondary_path, strip_w, secondary_tier)
            _stroke(strip_phase, secondary_path, strip_w, 0.07 + 0.86 * ((base_phase + 0.19) % 1.0))
            counts["short_broken_interlace_strips"] += 2

            cross_half = float(rng.uniform(3.0, 5.0) * scale)
            c0 = _local_point(crossing, primary_angle, -cross_half, 0.0)
            ck = _local_point(crossing, primary_angle, 0.0, rng.uniform(-1.2, 1.2) * scale)
            c1 = _local_point(crossing, primary_angle, cross_half, 0.0)
            cross_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
            cross_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
            _stroke(cyan_crossings, [c0, ck, c1], cross_w, cross_tier)
            _stroke(cyan_phase, [c0, ck, c1], cross_w, 0.07 + 0.86 * ((base_phase + 0.36) % 1.0))
            counts["cyan_exposed_crossings"] += 1

            ghost_shift = float(rng.uniform(2.4, 4.2) * scale)
            ghost_path = _offset_path(secondary_path, secondary_angle, ghost_shift)
            ghost_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
            ghost_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            _stroke(underfilm_ghosts, ghost_path, ghost_w, 0.18 + 0.60 * ghost_tier)
            _stroke(ghost_phase, ghost_path, ghost_w, 0.07 + 0.86 * ((base_phase + 0.49) % 1.0))
            counts["magenta_underfilm_ghosts"] += 1

            lip_shift = float(rng.uniform(1.8, 2.8) * scale)
            lip_path = _offset_path([p0, pk], primary_angle, lip_shift)
            lip_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
            _stroke(copper_lips, lip_path, lip_w, float(EVENT_TIERS[int(rng.integers(0, 8))]))
            counts["lifted_copper_lips"] += 1

            end_point = p1 if rng.random() < 0.5 else q0
            end_angle = primary_angle if end_point is p1 else secondary_angle
            end_half = float(rng.uniform(2.0, 3.6) * scale)
            e0 = _local_point(end_point, end_angle + math.pi * 0.5, -end_half, 0.0)
            e1 = _local_point(end_point, end_angle + math.pi * 0.5, end_half, 0.0)
            end_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
            _stroke(strand_ends, [e0, end_point, e1], end_w, float(EVENT_TIERS[int(rng.integers(0, 8))]))
            counts["clipped_strand_ends"] += 1

            if rng.random() < 0.54:
                axes = (
                    max(2, int(round(rng.uniform(2.0, 3.0) * scale))),
                    max(2, int(round(rng.uniform(2.0, 3.6) * scale))),
                )
                _ellipse(
                    junction_beads,
                    crossing,
                    axes,
                    math.degrees(primary_angle + rng.uniform(-0.5, 0.5)),
                    float(EVENT_TIERS[int(rng.integers(0, 8))]),
                )
                counts["fused_junction_beads"] += 1

            if rng.random() < 0.56:
                window_center = _local_point(
                    center,
                    base_angle,
                    rng.uniform(-3.2, 3.2) * scale,
                    rng.uniform(-3.0, 3.0) * scale,
                )
                window_half_x = float(rng.uniform(2.4, 4.2) * scale)
                window_half_y = float(rng.uniform(2.2, 3.8) * scale)
                window = [
                    _local_point(window_center, base_angle, -window_half_x, -0.45 * window_half_y),
                    _local_point(window_center, base_angle, -0.18 * window_half_x, -window_half_y),
                    _local_point(window_center, base_angle, window_half_x, 0.28 * window_half_y),
                    _local_point(window_center, base_angle, 0.14 * window_half_x, window_half_y),
                ]
                _fill(torn_windows, window, float(EVENT_TIERS[int(rng.integers(0, 8))]))
                counts["torn_windows"] += 1

            if rng.random() < 0.76:
                blister_center = _local_point(
                    center,
                    base_angle,
                    rng.uniform(-3.0, 3.0) * scale,
                    rng.uniform(-3.0, 3.0) * scale,
                )
                blister_half = float(rng.uniform(2.5, 4.4) * scale)
                b0 = _local_point(blister_center, base_angle, -blister_half, 0.0)
                bk = _local_point(blister_center, base_angle, 0.0, rng.uniform(1.2, 2.4) * scale)
                b1 = _local_point(blister_center, base_angle, blister_half, 0.0)
                blister_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                _stroke(blister_shadows, [b0, bk, b1], blister_w, 0.22 + 0.62 * primary_tier)
                counts["blister_shadows"] += 1

            gap_angle = primary_angle + math.pi * 0.5 + rng.uniform(-0.30, 0.30)
            gap_half = float(rng.uniform(2.1, 3.9) * scale)
            g0 = _local_point(pk, gap_angle, -gap_half, 0.0)
            gk = _local_point(pk, gap_angle, 0.0, rng.uniform(-1.0, 1.0) * scale)
            g1 = _local_point(pk, gap_angle, gap_half, 0.0)
            gap_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
            _stroke(adhesive_gaps, [g0, gk, g1], gap_w, 0.22 + 0.64 * secondary_tier)
            counts["dark_adhesive_gaps"] += 1

    buried_overlap = smoothstep(1.45, 3.10, fragment_depth) * fragment_body
    buried_overlap *= 0.42 + 0.58 * fragment_energy

    paint = _compose_paint(
        fragment_body,
        fragment_phase,
        fragment_energy,
        interlace_strips,
        strip_phase,
        cyan_crossings,
        cyan_phase,
        underfilm_ghosts,
        ghost_phase,
        copper_lips,
        strand_ends,
        junction_beads,
        torn_windows,
        blister_shadows,
        adhesive_gaps,
        buried_overlap,
    )

    # SPB-105 / 2026-08-27 owner verdict: keep every interlace remnant fine,
    # but let its authored cyan/copper/magenta phases survive as Neon on-car.
    # Official isolated M7 movement: 70.7 -> 85.6, with geometry/spec unchanged.
    hsv = cv2.cvtColor(np.clip(paint, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 2.00, 0.0, 1.0)
    paint = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    metal_reach = blur(np.maximum.reduce((cyan_crossings, copper_lips, strand_ends, junction_beads)), 17.0, size)
    rough_reach = blur(np.maximum.reduce((torn_windows, blister_shadows, adhesive_gaps)), 15.0, size)
    coat_reach = blur(np.maximum.reduce((fragment_body, underfilm_ghosts, interlace_strips)), 15.0, size)
    m_score = (
        2.28 * cyan_crossings
        + 1.94 * copper_lips
        + 1.52 * junction_beads
        + 1.20 * strand_ends
        + 0.88 * buried_overlap
        + 0.38 * metal_reach
        + 0.24 * interlace_strips
        - 0.72 * adhesive_gaps
        - 0.30 * fragment_body
    )
    r_score = (
        2.14 * torn_windows
        + 1.92 * adhesive_gaps
        + 1.46 * strand_ends
        + 1.16 * blister_shadows
        + 0.42 * rough_reach
        + 0.30 * junction_beads
        - 1.08 * cyan_crossings
        - 0.62 * fragment_body
    )
    c_score = (
        1.60 * fragment_body
        + 1.40 * underfilm_ghosts
        + 1.08 * interlace_strips
        + 0.70 * buried_overlap
        + 0.34 * coat_reach
        + 0.22 * copper_lips
        - 1.82 * torn_windows
        - 1.46 * adhesive_gaps
        - 1.18 * strand_ends
        - 0.92 * cyan_crossings
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "delaminated_mesh_fragments": fragment_body,
        "short_broken_interlace_strips": interlace_strips,
        "cyan_exposed_crossings": cyan_crossings,
        "magenta_underfilm_ghosts": underfilm_ghosts,
        "lifted_copper_lips": copper_lips,
        "clipped_strand_ends": strand_ends,
        "fused_junction_beads": junction_beads,
        "torn_windows": torn_windows,
        "blister_shadows": blister_shadows,
        "dark_adhesive_gaps": adhesive_gaps,
    }
    geometry = (
        GeometryMark("delaminated_mesh_fragments", 28.0, counts["delaminated_mesh_fragments"]),
        GeometryMark("short_broken_interlace_strips", 10.0, counts["short_broken_interlace_strips"]),
        GeometryMark("cyan_exposed_crossings", 8.0, counts["cyan_exposed_crossings"]),
        GeometryMark("magenta_underfilm_ghosts", 10.0, counts["magenta_underfilm_ghosts"]),
        GeometryMark("lifted_copper_lips", 10.0, counts["lifted_copper_lips"]),
        GeometryMark("clipped_strand_ends", 8.0, counts["clipped_strand_ends"]),
        GeometryMark("fused_junction_beads", 9.0, counts["fused_junction_beads"]),
        GeometryMark("torn_windows", 10.0, counts["torn_windows"]),
        GeometryMark("blister_shadows", 9.0, counts["blister_shadows"]),
        GeometryMark("dark_adhesive_gaps", 8.0, counts["dark_adhesive_gaps"]),
    )
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "cyan exposed crossings, lifted copper lips, clipped conductive ends, fused beads, and buried overlap",
            "R": "torn windows, dark adhesive gaps, clipped ends, blister shadows, and fractured junctions",
            "Cc": "intact conductive laminate, magenta underfilm ghosts, buried strips, and overlaps; low at tears",
        },
        carrier="black conductive laminate densely loaded with clipped organic 8-32px delaminated interlace packets",
        vetoes=(
            "no literal wireframes, grids, rows, nets, or webs",
            "no long wires or circuit diagrams",
            "no triangles or repeated X stamps",
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
        repeat = build_live_mesh_delam()
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
    output = project_root / "_neon_oil_slick_reset_work" / "live_mesh_delam"
    result = timed_result(build_live_mesh_delam)
    manifest = render_evidence(result, output)
    audit = _write_audit(result, output)
    print(json.dumps({"manifest": manifest, "audit": audit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
