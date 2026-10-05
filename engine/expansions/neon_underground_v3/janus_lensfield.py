"""Isolated Janus Lensfield owner-review pilot.

SPB-105 | 2026-08-27 | owner verdict: "don't overthink: one solid
candidate and at most one obvious visual repair."  This module replaces the
unaccepted legacy ``neon_dual_glow`` appearance with one causal optical-resin
material.  Exact timing and M/R/Cc movement from no accepted pilot to this
candidate are written to its isolated manifest/audit on every evidence run.

The pilot is intentionally unwired: no registry, catalog, or packaged mirror
imports it.  All visible paint and material response originates in the same
authored microlens anatomy below; there is no noise/spec underlay.
"""

from __future__ import annotations

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


FINISH_ID = "neon_dual_glow"
DISPLAY_NAME = "Janus Lensfield"
DEFAULT_SEED = 0x1A2B5EED
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.80, 0.94), np.float32)


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


def _disc(
    mask: np.ndarray,
    center: tuple[float, float],
    radius: int,
    value: float,
) -> None:
    cv2.circle(
        mask,
        (int(round(center[0])), int(round(center[1]))),
        int(radius),
        float(value),
        -1,
        cv2.LINE_AA,
    )


def _lens_polygon(
    center: tuple[float, float],
    half_major: float,
    half_minor: float,
    angle: float,
    rng: np.random.Generator,
) -> list[tuple[float, float]]:
    """Eight unequal facets form an irregular lens, never a circle/capsule."""
    local = (
        (-1.00, -0.04),
        (-0.58, -0.72),
        (0.04, -1.00),
        (0.78, -0.55),
        (1.00, 0.10),
        (0.48, 0.88),
        (-0.20, 1.00),
        (-0.82, 0.48),
    )
    ca, sa = math.cos(angle), math.sin(angle)
    result: list[tuple[float, float]] = []
    for lx, ly in local:
        x = (lx + float(rng.uniform(-0.07, 0.07))) * half_major
        y = (ly + float(rng.uniform(-0.09, 0.09))) * half_minor
        result.append((center[0] + ca * x - sa * y, center[1] + sa * x + ca * y))
    return result


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


def _accumulate_body(
    body: np.ndarray,
    depth: np.ndarray,
    phase: np.ndarray,
    energy: np.ndarray,
    polygon: list[tuple[float, float]],
    opacity: float,
    phase_value: float,
    energy_value: float,
) -> None:
    """Alpha-compose one polygon inside a bounded ROI for predictable speed."""
    h, w = body.shape
    p = np.rint(np.asarray(polygon, np.float32)).astype(np.int32)
    x0 = max(0, int(np.min(p[:, 0])) - 2)
    y0 = max(0, int(np.min(p[:, 1])) - 2)
    x1 = min(w, int(np.max(p[:, 0])) + 3)
    y1 = min(h, int(np.max(p[:, 1])) + 3)
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


def _palette(values: np.ndarray, anchors: tuple[tuple[float, float, float], ...]) -> np.ndarray:
    palette = np.asarray(anchors, np.float32)
    period = len(anchors) - 1
    p = np.mod(np.asarray(values, np.float32), 1.0) * period
    index = np.floor(p).astype(np.int32)
    fraction = p - index
    return palette[index] * (1.0 - fraction[..., None]) + palette[index + 1] * fraction[..., None]


def _body_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.08, 0.28, 0.42),
            (0.32, 0.12, 0.48),
            (0.46, 0.08, 0.31),
            (0.10, 0.34, 0.44),
            (0.08, 0.28, 0.42),
        ),
    )


def _cyan_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.18, 0.82, 1.00),
            (0.32, 1.00, 0.88),
            (0.54, 0.68, 1.00),
            (0.10, 0.62, 0.96),
            (0.18, 0.82, 1.00),
        ),
    )


def _magenta_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (1.00, 0.26, 0.72),
            (0.80, 0.34, 1.00),
            (1.00, 0.48, 0.58),
            (0.72, 0.22, 0.94),
            (1.00, 0.26, 0.72),
        ),
    )


def _compose_paint(
    body: np.ndarray,
    body_phase: np.ndarray,
    body_energy: np.ndarray,
    cyan_flanks: np.ndarray,
    cyan_phase: np.ndarray,
    magenta_flanks: np.ndarray,
    magenta_phase: np.ndarray,
    equators: np.ndarray,
    caustics: np.ndarray,
    chips: np.ndarray,
    necks: np.ndarray,
    ghosts: np.ndarray,
    occlusion: np.ndarray,
) -> np.ndarray:
    h, w = body.shape
    paint = np.zeros((h, w, 3), np.float32)
    paint[:] = np.asarray((0.008, 0.010, 0.018), np.float32)

    # The dense low-energy bodies merge into one black optical-resin carrier.
    body_color = _body_palette(body_phase)
    body_raw = body_color * (body * (0.105 + 0.18 * body_energy))[..., None]
    body_soft = np.stack(tuple(blur(body_raw[..., i], 9.0, h) for i in range(3)), axis=2)
    paint += 1.42 * body_soft
    paint += body_color * (body * (0.045 + 0.055 * body_energy))[..., None]
    paint += blur(body, 11.0, h)[..., None] * np.asarray((0.022, 0.029, 0.048), np.float32)

    cyan_color = _cyan_palette(cyan_phase)
    magenta_color = _magenta_palette(magenta_phase)
    paint += cyan_color * (0.29 * cyan_flanks + 0.34 * np.power(cyan_flanks, 2.1))[..., None]
    paint += magenta_color * (0.28 * magenta_flanks + 0.34 * np.power(magenta_flanks, 2.1))[..., None]

    # Remaining marks are attached optical events, never a free sparkle field.
    equator_color = 0.38 * cyan_color + 0.62 * magenta_color
    paint += equator_color * (0.17 * equators)[..., None]
    caustic_color = 0.55 * cyan_color + 0.45 * magenta_color
    paint += caustic_color * (0.22 * caustics + 0.43 * np.power(caustics, 2.0))[..., None]
    paint += magenta_color * (0.23 * chips)[..., None]
    paint += cyan_color * (0.27 * necks)[..., None]
    paint += body_color * (0.18 * ghosts)[..., None]

    # Occlusion cuts sit inside/under a lens; they never become black outlines.
    paint *= 1.0 - 0.50 * occlusion[..., None]
    paint += occlusion[..., None] * np.asarray((0.002, 0.004, 0.009), np.float32)
    return np.clip(paint, 0.0, 1.0)


def build_janus_lensfield(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build deterministic black resin with causally authored Janus lenses."""
    if int(size) < 256:
        raise ValueError("Janus Lensfield requires a work raster of at least 256px")
    rng = seeded(seed)
    h = w = int(size)
    shape = (h, w)
    scale = float(size) / float(WORK)

    bodies = np.zeros(shape, np.float32)
    depth = np.zeros(shape, np.float32)
    body_phase = np.zeros(shape, np.float32)
    body_energy = np.zeros(shape, np.float32)
    cyan_flanks = np.zeros(shape, np.float32)
    cyan_phase = np.zeros(shape, np.float32)
    magenta_flanks = np.zeros(shape, np.float32)
    magenta_phase = np.zeros(shape, np.float32)
    clipped_equators = np.zeros(shape, np.float32)
    caustic_pinpoints = np.zeros(shape, np.float32)
    chipped_edges = np.zeros(shape, np.float32)
    lens_necks = np.zeros(shape, np.float32)
    buried_ghosts = np.zeros(shape, np.float32)
    occlusion_cuts = np.zeros(shape, np.float32)

    counts = {
        "irregular_lens_bodies": 0,
        "opposing_cyan_flanks": 0,
        "opposing_magenta_flanks": 0,
        "clipped_equators": 0,
        "caustic_pinpoints": 0,
        "chipped_edges": 0,
        "short_lens_neck_overlaps": 0,
        "buried_ghost_lenses": 0,
        "black_occlusion_cuts": 0,
    }

    cell = max(12, int(round(16.0 * scale)))
    for gy, y0 in enumerate(range(-cell, h + cell, cell)):
        for gx, x0 in enumerate(range(-cell, w + cell, cell)):
            if rng.random() < 0.025:
                continue
            packet_center = (
                float(x0 + rng.uniform(-0.46, 0.46) * cell),
                float(y0 + rng.uniform(-0.46, 0.46) * cell),
            )
            block_x, block_y = gx // 3, gy // 3
            block_hash = (
                (block_x * 0x9E3779B1)
                ^ (block_y * 0x85EBCA77)
                ^ ((block_x + 2 * block_y) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_angle = (block_hash % 24) * (math.pi / 24.0) + float(rng.uniform(-0.52, 0.52))
            base_phase = float(((block_hash % 193) / 193.0 + rng.uniform(-0.08, 0.08)) % 1.0)
            packet_total = 1 + int(rng.random() < 0.40) + int(rng.random() < 0.065)
            previous_center: tuple[float, float] | None = None

            for packet_index in range(packet_total):
                t = packet_index - 0.5 * (packet_total - 1)
                angle = base_angle + t * float(rng.uniform(0.28, 0.68)) + float(rng.uniform(-0.18, 0.18))
                center = _local_point(
                    packet_center,
                    base_angle,
                    t * float(rng.uniform(5.0, 8.0)) * scale,
                    float(rng.uniform(-3.0, 3.0)) * scale,
                )
                half_major = float(rng.uniform(4.7, 7.5) * scale)
                half_minor = float(rng.uniform(3.5, 5.8) * scale)
                polygon = _lens_polygon(center, half_major, half_minor, angle, rng)
                tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                tier = float(EVENT_TIERS[tier_index])
                handed = bool((block_hash + packet_index + int(rng.integers(0, 3))) % 2)
                cyan_index = int(np.clip(tier_index + (2 if handed else -1), 0, 7))
                magenta_index = int(np.clip(tier_index + (-1 if handed else 2), 0, 7))
                cyan_tier = float(EVENT_TIERS[cyan_index])
                magenta_tier = float(EVENT_TIERS[magenta_index])
                optical_phase = float((base_phase + 0.11 * t + 0.017 * tier_index) % 1.0)

                _accumulate_body(
                    bodies,
                    depth,
                    body_phase,
                    body_energy,
                    polygon,
                    0.22 + 0.40 * tier,
                    optical_phase,
                    tier,
                )
                counts["irregular_lens_bodies"] += 1

                # Unequal, incomplete end facets supply Janus opposition
                # without ever outlining an eye, circle, or capsule.
                cyan_path = [polygon[7], polygon[0], polygon[1]]
                magenta_path = [polygon[3], polygon[4], polygon[5]]
                flank_w = max(4, int(round(rng.uniform(4.0, 5.2) * scale)))
                _stroke(cyan_flanks, cyan_path, flank_w, cyan_tier)
                _stroke(cyan_phase, cyan_path, flank_w, 0.08 + 0.84 * optical_phase)
                _stroke(magenta_flanks, magenta_path, flank_w, magenta_tier)
                _stroke(magenta_phase, magenta_path, flank_w, 0.08 + 0.84 * ((optical_phase + 0.46) % 1.0))
                counts["opposing_cyan_flanks"] += 1
                counts["opposing_magenta_flanks"] += 1

                equator_anchor = center
                if rng.random() < 0.78:
                    across = float(rng.uniform(-0.20, 0.20) * half_minor)
                    equator_half = float(rng.uniform(0.24, 0.44) * half_major)
                    p0 = _local_point(center, angle, -equator_half, across)
                    kink = _local_point(center, angle, rng.uniform(-0.08, 0.08) * half_major, across * 0.45)
                    p1 = _local_point(center, angle, equator_half * rng.uniform(0.65, 1.0), -across * 0.30)
                    equator_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
                    equator_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                    _stroke(clipped_equators, [p0, kink, p1], equator_w, equator_tier)
                    equator_anchor = kink
                    counts["clipped_equators"] += 1

                if rng.random() < 0.70:
                    caustic_center = _local_point(
                        equator_anchor,
                        angle,
                        float(rng.uniform(-0.18, 0.18) * half_major),
                        float(rng.uniform(-0.16, 0.16) * half_minor),
                    )
                    radius = max(2, int(round(rng.uniform(2.0, 2.8) * scale)))
                    caustic_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                    _disc(caustic_pinpoints, caustic_center, radius, caustic_tier)
                    counts["caustic_pinpoints"] += 1

                if rng.random() < 0.31:
                    corner_index = 0 if rng.random() < 0.5 else 4
                    corner = polygon[corner_index]
                    prev_corner = polygon[(corner_index - 1) % 8]
                    next_corner = polygon[(corner_index + 1) % 8]
                    fraction = float(rng.uniform(0.25, 0.43))
                    chip = [
                        corner,
                        (
                            corner[0] + (prev_corner[0] - corner[0]) * fraction,
                            corner[1] + (prev_corner[1] - corner[1]) * fraction,
                        ),
                        (
                            corner[0] + (next_corner[0] - corner[0]) * fraction,
                            corner[1] + (next_corner[1] - corner[1]) * fraction,
                        ),
                    ]
                    _fill(chipped_edges, chip, float(EVENT_TIERS[int(rng.integers(1, 8))]))
                    counts["chipped_edges"] += 1

                if rng.random() < 0.48:
                    ghost_shift = float(rng.uniform(2.2, 4.2) * scale)
                    shifted = [
                        _local_point(point, angle, -ghost_shift, 0.35 * ghost_shift)
                        for point in (polygon[5], polygon[6], polygon[7])
                    ]
                    ghost_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                    _stroke(
                        buried_ghosts,
                        shifted,
                        ghost_w,
                        0.18 + 0.58 * float(EVENT_TIERS[int(rng.integers(0, 8))]),
                    )
                    counts["buried_ghost_lenses"] += 1

                if rng.random() < 0.83:
                    cut_along = float(rng.uniform(-0.18, 0.24) * half_major)
                    cut_half = float(rng.uniform(0.26, 0.48) * half_minor)
                    p0 = _local_point(center, angle, cut_along, -cut_half)
                    p1 = _local_point(center, angle, cut_along * 0.35, cut_half)
                    cut_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                    _stroke(occlusion_cuts, [p0, p1], cut_w, 0.22 + 0.62 * tier)
                    counts["black_occlusion_cuts"] += 1

                if previous_center is not None:
                    neck_mid = (
                        0.52 * previous_center[0] + 0.48 * center[0],
                        0.52 * previous_center[1] + 0.48 * center[1],
                    )
                    neck_points = [
                        (
                            0.72 * previous_center[0] + 0.28 * center[0],
                            0.72 * previous_center[1] + 0.28 * center[1],
                        ),
                        _local_point(neck_mid, base_angle, 0.0, rng.uniform(-1.3, 1.3) * scale),
                        (
                            0.28 * previous_center[0] + 0.72 * center[0],
                            0.28 * previous_center[1] + 0.72 * center[1],
                        ),
                    ]
                    neck_w = max(4, int(round(rng.uniform(4.0, 5.2) * scale)))
                    _stroke(lens_necks, neck_points, neck_w, 0.20 + 0.68 * tier)
                    counts["short_lens_neck_overlaps"] += 1
                previous_center = center

    # Buried optical energy is an overlap of authored bodies, not extra noise.
    buried_overlap = smoothstep(1.35, 2.85, depth) * bodies
    body_energy[:] = np.maximum(body_energy, 0.44 * buried_overlap)

    paint = _compose_paint(
        bodies,
        body_phase,
        body_energy,
        cyan_flanks,
        cyan_phase,
        magenta_flanks,
        magenta_phase,
        clipped_equators,
        caustic_pinpoints,
        chipped_edges,
        lens_necks,
        buried_ghosts,
        occlusion_cuts,
    )

    # Independent material roles share the same lens anatomy.  Exposed cyan
    # facets/caustics drive M; broken equators/chips/cuts drive R; intact body,
    # magenta flank and ghosts drive Cc.  Tiered masks make local dominance
    # exchange as the moving proxy crosses differently handed packets.
    metal_reach = blur(np.maximum.reduce((cyan_flanks, caustic_pinpoints, lens_necks)), 17.0, size)
    break_reach = blur(np.maximum.reduce((chipped_edges, clipped_equators, occlusion_cuts)), 13.0, size)
    ghost_reach = blur(np.maximum(buried_ghosts, lens_necks), 15.0, size)
    m_score = (
        2.30 * cyan_flanks
        + 1.92 * caustic_pinpoints
        + 1.34 * lens_necks
        + 0.88 * chipped_edges
        + 0.52 * buried_overlap
        + 0.36 * metal_reach
        + 0.26 * magenta_flanks
        - 0.72 * occlusion_cuts
        - 0.30 * bodies
    )
    r_score = (
        2.16 * chipped_edges
        + 1.78 * clipped_equators
        + 1.58 * occlusion_cuts
        + 0.52 * break_reach
        + 0.38 * magenta_flanks
        - 1.16 * cyan_flanks
        - 0.74 * caustic_pinpoints
        - 0.48 * bodies
    )
    c_score = (
        1.56 * bodies
        + 1.42 * magenta_flanks
        + 1.20 * buried_ghosts
        + 0.76 * lens_necks
        + 0.34 * ghost_reach
        + 0.26 * cyan_flanks
        - 1.72 * chipped_edges
        - 1.34 * clipped_equators
        - 1.08 * occlusion_cuts
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "irregular_lens_bodies": bodies,
        "opposing_cyan_flanks": cyan_flanks,
        "opposing_magenta_flanks": magenta_flanks,
        "clipped_equators": clipped_equators,
        "caustic_pinpoints": caustic_pinpoints,
        "chipped_edges": chipped_edges,
        "short_lens_neck_overlaps": lens_necks,
        "buried_ghost_lenses": buried_ghosts,
        "black_occlusion_cuts": occlusion_cuts,
    }
    geometry = (
        GeometryMark("irregular_lens_bodies", 28.0, counts["irregular_lens_bodies"]),
        GeometryMark("opposing_cyan_flanks", 9.0, counts["opposing_cyan_flanks"]),
        GeometryMark("opposing_magenta_flanks", 9.0, counts["opposing_magenta_flanks"]),
        GeometryMark("clipped_equators", 8.0, counts["clipped_equators"]),
        GeometryMark("caustic_pinpoints", 9.0, counts["caustic_pinpoints"]),
        GeometryMark("chipped_edges", 8.0, counts["chipped_edges"]),
        GeometryMark("short_lens_neck_overlaps", 10.0, counts["short_lens_neck_overlaps"]),
        GeometryMark("buried_ghost_lenses", 18.0, counts["buried_ghost_lenses"]),
        GeometryMark("black_occlusion_cuts", 9.0, counts["black_occlusion_cuts"]),
    )
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "exposed cyan flanks, caustic pinpoints, reflective neck overlaps, and chipped exposure",
            "R": "clipped equators, chipped edges, and black occlusion cuts with fractured reach",
            "Cc": "intact resin lens bodies, opposing magenta flanks, buried ghosts, and healed necks",
        },
        carrier="black optical resin densely filled with irregular opposing-flank birefringent microlens packets",
        vetoes=(
            "no yin-yang or eye icons",
            "no bubbles, polka dots, fish scales, or confetti",
            "no repeated capsules",
            "no grids or rows",
            "no simple two-color split wallpaper",
            "no unrelated noise/spec underlay",
        ),
    )


def _write_audit(result: PilotResult, output: Path) -> dict[str, object]:
    repeat_times: list[float] = []
    repeats: list[PilotResult] = []
    for _ in range(3):
        start = time.perf_counter()
        repeat = build_janus_lensfield()
        repeat_times.append(time.perf_counter() - start)
        repeats.append(repeat)

    paint_hashes = [hashlib.sha256(item.paint.tobytes()).hexdigest() for item in (result, *repeats)]
    spec_hashes = [hashlib.sha256(item.spec.tobytes()).hexdigest() for item in (result, *repeats)]
    union = np.maximum.reduce(tuple(np.asarray(mask, np.float32) for mask in result.masks.values()))
    border = np.zeros(union.shape, bool)
    border[:16, :] = True
    border[-16:, :] = True
    border[:, :16] = True
    border[:, -16:] = True
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
    output = project_root / "_neon_oil_slick_reset_work" / "janus_lensfield"
    result = timed_result(build_janus_lensfield)
    manifest = render_evidence(result, output)
    audit = _write_audit(result, output)
    print(json.dumps({"manifest": manifest, "audit": audit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
