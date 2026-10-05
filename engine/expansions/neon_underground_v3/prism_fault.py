"""Isolated Prism Fault owner-review pilot for ``neon_rainbow_tube``.

SPB-105 | 2026-08-27 | owner verdict: "don't overthink: one solid
candidate, one obvious repair maximum."  The rejected tube/rainbow treatment
is replaced by one causal black laminated optical film.  Exact movement from
no accepted pilot to the generated M/R/Cc and timing measurements is written
to this candidate's isolated manifest and audit on every evidence run.

This module is intentionally unwired.  It imports shared material utilities,
but owns its carrier, fracture grammar, paint composition, and causal maps.
There is no hue-noise or unrelated spec underlay.
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


FINISH_ID = "neon_rainbow_tube"
DISPLAY_NAME = "Prism Fault"
DEFAULT_SEED = 0xFA0175ED
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


def _disc(mask: np.ndarray, center: tuple[float, float], radius: int, value: float) -> None:
    cv2.circle(
        mask,
        (int(round(center[0])), int(round(center[1]))),
        int(radius),
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


def _plate_polygon(
    center: tuple[float, float],
    half_major: float,
    half_minor: float,
    angle: float,
    rng: np.random.Generator,
) -> list[tuple[float, float]]:
    """Asymmetric six-facet platelet; no repeated shard template or scale."""
    local = (
        (-1.00, -0.28),
        (-0.34, -1.00),
        (0.72, -0.76),
        (1.00, 0.20),
        (0.30, 1.00),
        (-0.82, 0.68),
    )
    ca, sa = math.cos(angle), math.sin(angle)
    result: list[tuple[float, float]] = []
    for lx, ly in local:
        px = (lx + float(rng.uniform(-0.10, 0.10))) * half_major
        py = (ly + float(rng.uniform(-0.11, 0.11))) * half_minor
        result.append((center[0] + ca * px - sa * py, center[1] + sa * px + ca * py))
    return result


def _accumulate_plate(
    body: np.ndarray,
    depth: np.ndarray,
    phase: np.ndarray,
    energy: np.ndarray,
    polygon: list[tuple[float, float]],
    opacity: float,
    phase_value: float,
    energy_value: float,
) -> None:
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


def _film_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.08, 0.20, 0.29),
            (0.29, 0.10, 0.34),
            (0.34, 0.12, 0.18),
            (0.10, 0.28, 0.29),
            (0.08, 0.20, 0.29),
        ),
    )


def _spectral_palette(values: np.ndarray) -> np.ndarray:
    # Each authored fault samples a short part of this cycle; the canvas never
    # receives a global rainbow gradient or free hue field.
    return _palette(
        values,
        (
            (1.00, 0.24, 0.20),
            (1.00, 0.62, 0.18),
            (0.97, 0.24, 0.76),
            (0.56, 0.28, 1.00),
            (0.13, 0.70, 1.00),
            (0.20, 0.98, 0.72),
            (1.00, 0.24, 0.20),
        ),
    )


def _compose_paint(
    plate_body: np.ndarray,
    plate_phase: np.ndarray,
    plate_energy: np.ndarray,
    spectral_edges: np.ndarray,
    edge_phase: np.ndarray,
    color_ghosts: np.ndarray,
    ghost_phase: np.ndarray,
    chipped_corners: np.ndarray,
    clear_seams: np.ndarray,
    absorption_notches: np.ndarray,
    white_caustics: np.ndarray,
    buried_overlaps: np.ndarray,
    chromatic_dust: np.ndarray,
) -> np.ndarray:
    h, w = plate_body.shape
    paint = np.zeros((h, w, 3), np.float32)
    paint[:] = np.asarray((0.010, 0.012, 0.019), np.float32)

    film_color = _film_palette(plate_phase)
    film_raw = film_color * (plate_body * (0.115 + 0.17 * plate_energy))[..., None]
    film_soft = np.stack(tuple(blur(film_raw[..., i], 10.0, h) for i in range(3)), axis=2)
    paint += 1.48 * film_soft
    paint += film_color * (plate_body * (0.040 + 0.052 * plate_energy))[..., None]
    paint += blur(plate_body, 13.0, h)[..., None] * np.asarray((0.026, 0.034, 0.052), np.float32)

    edge_color = _spectral_palette(edge_phase)
    ghost_color = _spectral_palette(ghost_phase)
    paint += edge_color * (0.26 * spectral_edges + 0.30 * np.power(spectral_edges, 2.0))[..., None]
    paint += ghost_color * (0.13 * color_ghosts + 0.14 * np.power(color_ghosts, 2.0))[..., None]

    # All secondary events remain attached to an authored break or overlap.
    paint += edge_color * (0.24 * chipped_corners)[..., None]
    paint += (0.42 * edge_color + 0.58) * (0.12 * clear_seams)[..., None]
    paint += (0.50 * edge_color + 0.50 * ghost_color) * (0.18 * buried_overlaps)[..., None]
    paint += ghost_color * (0.18 * chromatic_dust)[..., None]
    paint += white_caustics[..., None] * np.asarray((0.48, 0.57, 0.66), np.float32)

    # Absorption notches cut through the spectral edge inside the laminate.
    paint *= 1.0 - 0.52 * absorption_notches[..., None]
    paint += absorption_notches[..., None] * np.asarray((0.002, 0.003, 0.006), np.float32)
    # SPB-105 / Neon reset continuation / 2026-08-27 owner verdict: keep the
    # spectral edges visibly chromatic without widening a single fault. Official
    # isolated M7 before calibration: 71.7 (M6 saturation miss); rerun below.
    hsv = cv2.cvtColor(np.clip(paint, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.15, 0.0, 1.0)
    paint = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return np.clip(paint, 0.0, 1.0)


def build_prism_fault(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build deterministic fractured diffraction film and causal M/R/Cc."""
    if int(size) < 256:
        raise ValueError("Prism Fault requires a work raster of at least 256px")
    rng = seeded(seed)
    h = w = int(size)
    shape = (h, w)
    scale = float(size) / float(WORK)

    plate_body = np.zeros(shape, np.float32)
    plate_depth = np.zeros(shape, np.float32)
    plate_phase = np.zeros(shape, np.float32)
    plate_energy = np.zeros(shape, np.float32)
    spectral_edges = np.zeros(shape, np.float32)
    edge_phase = np.zeros(shape, np.float32)
    color_ghosts = np.zeros(shape, np.float32)
    ghost_phase = np.zeros(shape, np.float32)
    chipped_corners = np.zeros(shape, np.float32)
    clear_seams = np.zeros(shape, np.float32)
    absorption_notches = np.zeros(shape, np.float32)
    white_caustics = np.zeros(shape, np.float32)
    chromatic_dust = np.zeros(shape, np.float32)

    counts = {
        "fractured_diffraction_platelets": 0,
        "asymmetric_spectral_edge_splits": 0,
        "displaced_color_ghosts": 0,
        "chipped_prism_corners": 0,
        "narrow_clear_seams": 0,
        "dark_absorption_notches": 0,
        "tiny_white_caustics": 0,
        "buried_plate_overlaps": 0,
        "chromatic_dust_at_breaks": 0,
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
                ^ ((2 * block_x - block_y) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_angle = (block_hash % 28) * (math.pi / 28.0) + float(rng.uniform(-0.46, 0.46))
            base_phase = float(((block_hash % 211) / 211.0 + rng.uniform(-0.07, 0.07)) % 1.0)

            fault_length = float(rng.uniform(11.0, 16.0) * scale)
            kink_across = float(rng.uniform(-2.2, 2.2) * scale)
            p0 = _local_point(center, base_angle, -0.50 * fault_length, rng.uniform(-0.8, 0.8) * scale)
            kink = _local_point(center, base_angle, rng.uniform(-0.12, 0.12) * fault_length, kink_across)
            p1 = _local_point(center, base_angle, 0.50 * fault_length, rng.uniform(-0.8, 0.8) * scale)
            master_path = [p0, kink, p1]

            plate_total = int(rng.integers(3, 6))
            for plate_index in range(plate_total):
                t = (plate_index - 0.5 * (plate_total - 1)) / max(plate_total - 1, 1)
                plate_center = _local_point(
                    center,
                    base_angle,
                    t * fault_length * rng.uniform(0.58, 0.88),
                    float(rng.uniform(-3.2, 3.2) * scale),
                )
                plate_angle = base_angle + float(rng.uniform(-0.42, 0.42)) + t * 0.18
                half_major = float(rng.uniform(4.4, 7.0) * scale)
                half_minor = float(rng.uniform(3.1, 5.2) * scale)
                tier_index = int(rng.integers(0, 8))
                tier = float(EVENT_TIERS[tier_index])
                optical_phase = float((base_phase + 0.065 * t + 0.013 * tier_index) % 1.0)
                polygon = _plate_polygon(plate_center, half_major, half_minor, plate_angle, rng)
                _accumulate_plate(
                    plate_body,
                    plate_depth,
                    plate_phase,
                    plate_energy,
                    polygon,
                    0.23 + 0.39 * tier,
                    optical_phase,
                    tier,
                )
                counts["fractured_diffraction_platelets"] += 1

            # Two incomplete, displaced halves create a microscopic spectral
            # split.  They share one fracture and never become a rainbow band.
            edge_tier_a = float(EVENT_TIERS[int(rng.integers(1, 8))])
            edge_tier_b = float(EVENT_TIERS[int(rng.integers(0, 8))])
            split_offset = float(rng.uniform(1.2, 2.2) * scale)
            p1a = (
                kink[0] + 0.56 * (p1[0] - kink[0]),
                kink[1] + 0.56 * (p1[1] - kink[1]),
            )
            p0b = (
                p0[0] + 0.44 * (kink[0] - p0[0]),
                p0[1] + 0.44 * (kink[1] - p0[1]),
            )
            split_a = _offset_path([p0, kink, p1a], base_angle, -split_offset)
            split_b = _offset_path([p0b, kink, p1], base_angle, 0.72 * split_offset)
            edge_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
            _stroke(spectral_edges, split_a, edge_w, edge_tier_a)
            _stroke(edge_phase, split_a, edge_w, 0.07 + 0.86 * base_phase)
            _stroke(spectral_edges, split_b, edge_w, edge_tier_b)
            _stroke(edge_phase, split_b, edge_w, 0.07 + 0.86 * ((base_phase + 0.17) % 1.0))
            counts["asymmetric_spectral_edge_splits"] += 2

            ghost_shift = float(rng.uniform(2.4, 4.4) * scale)
            ghost_path = _offset_path(master_path, base_angle, ghost_shift)
            ghost_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
            ghost_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            _stroke(color_ghosts, ghost_path, ghost_w, 0.18 + 0.60 * ghost_tier)
            _stroke(ghost_phase, ghost_path, ghost_w, 0.07 + 0.86 * ((base_phase + 0.31) % 1.0))
            counts["displaced_color_ghosts"] += 1

            seam_w = max(4, int(round(rng.uniform(4.0, 4.7) * scale)))
            seam_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
            _stroke(clear_seams, master_path, seam_w, 0.16 + 0.70 * seam_tier)
            counts["narrow_clear_seams"] += 1

            if rng.random() < 0.58:
                branch_angle = base_angle + float(rng.choice((-1.0, 1.0))) * rng.uniform(0.48, 0.86)
                branch_length = float(rng.uniform(4.2, 7.5) * scale)
                branch_end = _local_point(kink, branch_angle, branch_length, rng.uniform(-0.7, 0.7) * scale)
                branch_mid = _local_point(kink, branch_angle, 0.48 * branch_length, rng.uniform(-1.0, 1.0) * scale)
                branch_path = [kink, branch_mid, branch_end]
                branch_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                _stroke(spectral_edges, branch_path, edge_w, branch_tier)
                _stroke(edge_phase, branch_path, edge_w, 0.07 + 0.86 * ((base_phase + 0.43) % 1.0))
                counts["asymmetric_spectral_edge_splits"] += 1

            chip_corner = p0 if rng.random() < 0.5 else p1
            if rng.random() < 0.48:
                chip_size = float(rng.uniform(3.8, 5.2) * scale)
                chip = [
                    chip_corner,
                    _local_point(chip_corner, base_angle, chip_size, 0.35 * chip_size),
                    _local_point(chip_corner, base_angle, 0.18 * chip_size, chip_size),
                ]
                chip_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                _fill(chipped_corners, chip, chip_tier)
                counts["chipped_prism_corners"] += 1

                dust_total = 1 + int(rng.random() < 0.42)
                for _ in range(dust_total):
                    dust_center = _local_point(
                        chip_corner,
                        base_angle + rng.uniform(-0.55, 0.55),
                        float(rng.uniform(4.0, 7.0) * scale),
                        float(rng.uniform(-1.5, 1.5) * scale),
                    )
                    dust_radius = max(2, int(round(rng.uniform(2.0, 2.7) * scale)))
                    dust_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                    _disc(chromatic_dust, dust_center, dust_radius, dust_tier)
                    counts["chromatic_dust_at_breaks"] += 1

            if rng.random() < 0.78:
                notch_center = _local_point(
                    kink,
                    base_angle,
                    rng.uniform(-0.18, 0.18) * fault_length,
                    rng.uniform(-0.8, 0.8) * scale,
                )
                notch_half = float(rng.uniform(2.0, 3.8) * scale)
                n0 = _local_point(notch_center, base_angle + math.pi * 0.5, -notch_half, 0.0)
                n1 = _local_point(notch_center, base_angle + math.pi * 0.5, notch_half, 0.0)
                notch_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
                _stroke(absorption_notches, [n0, n1], notch_w, 0.22 + 0.64 * seam_tier)
                counts["dark_absorption_notches"] += 1

            if rng.random() < 0.54:
                caustic_center = _local_point(
                    kink,
                    base_angle,
                    rng.uniform(-1.2, 1.2) * scale,
                    rng.uniform(-1.2, 1.2) * scale,
                )
                caustic_radius = max(2, int(round(rng.uniform(2.0, 2.8) * scale)))
                caustic_tier = float(EVENT_TIERS[int(rng.integers(1, 8))])
                _disc(white_caustics, caustic_center, caustic_radius, caustic_tier)
                counts["tiny_white_caustics"] += 1

    buried_overlaps = smoothstep(1.45, 3.25, plate_depth) * plate_body
    buried_overlaps *= 0.42 + 0.58 * plate_energy
    counts["buried_plate_overlaps"] = counts["fractured_diffraction_platelets"]

    paint = _compose_paint(
        plate_body,
        plate_phase,
        plate_energy,
        spectral_edges,
        edge_phase,
        color_ghosts,
        ghost_phase,
        chipped_corners,
        clear_seams,
        absorption_notches,
        white_caustics,
        buried_overlaps,
        chromatic_dust,
    )

    # Three independent physical answers share the exact authored fractures.
    metal_reach = blur(np.maximum.reduce((spectral_edges, white_caustics, buried_overlaps)), 17.0, size)
    break_reach = blur(np.maximum.reduce((chipped_corners, absorption_notches, chromatic_dust)), 15.0, size)
    coat_reach = blur(np.maximum.reduce((plate_body, clear_seams, color_ghosts)), 15.0, size)
    m_score = (
        2.34 * spectral_edges
        + 2.04 * white_caustics
        + 1.38 * buried_overlaps
        + 0.92 * chipped_corners
        + 0.38 * metal_reach
        + 0.24 * color_ghosts
        - 0.70 * absorption_notches
        - 0.28 * plate_body
    )
    r_score = (
        2.24 * chipped_corners
        + 1.94 * absorption_notches
        + 1.52 * chromatic_dust
        + 0.82 * color_ghosts
        + 0.42 * break_reach
        - 1.12 * spectral_edges
        - 0.74 * clear_seams
        - 0.48 * plate_body
    )
    c_score = (
        1.62 * plate_body
        + 1.48 * clear_seams
        + 1.20 * color_ghosts
        + 0.74 * buried_overlaps
        + 0.34 * coat_reach
        + 0.22 * spectral_edges
        - 1.82 * chipped_corners
        - 1.52 * absorption_notches
        - 1.24 * chromatic_dust
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "fractured_diffraction_platelets": plate_body,
        "asymmetric_spectral_edge_splits": spectral_edges,
        "displaced_color_ghosts": color_ghosts,
        "chipped_prism_corners": chipped_corners,
        "narrow_clear_seams": clear_seams,
        "dark_absorption_notches": absorption_notches,
        "tiny_white_caustics": white_caustics,
        "buried_plate_overlaps": buried_overlaps,
        "chromatic_dust_at_breaks": chromatic_dust,
    }
    geometry = (
        GeometryMark("fractured_diffraction_platelets", 26.0, counts["fractured_diffraction_platelets"]),
        GeometryMark("asymmetric_spectral_edge_splits", 9.0, counts["asymmetric_spectral_edge_splits"]),
        GeometryMark("displaced_color_ghosts", 10.0, counts["displaced_color_ghosts"]),
        GeometryMark("chipped_prism_corners", 9.0, counts["chipped_prism_corners"]),
        GeometryMark("narrow_clear_seams", 8.0, counts["narrow_clear_seams"]),
        GeometryMark("dark_absorption_notches", 8.0, counts["dark_absorption_notches"]),
        GeometryMark("tiny_white_caustics", 9.0, counts["tiny_white_caustics"]),
        GeometryMark("buried_plate_overlaps", 12.0, counts["buried_plate_overlaps"]),
        GeometryMark("chromatic_dust_at_breaks", 8.0, counts["chromatic_dust_at_breaks"]),
    )
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "spectral edge splits, white caustics, exposed chips, and buried reflective plate overlaps",
            "R": "chipped corners, absorption notches, displaced ghosts, and break-attached chromatic dust",
            "Cc": "intact laminate platelets, narrow clear seams, color ghosts, and buried overlaps; low at breaks",
        },
        carrier="black laminated optical film densely fractured into overlapping 8-32px diffraction platelet packets",
        vetoes=(
            "no rainbow stripes or bands",
            "no literal tubes or smooth gradients",
            "no confetti, repeating shards, or fish scales",
            "no simple hue noise",
            "no unrelated noise/spec underlay",
        ),
    )


def _write_audit(result: PilotResult, output: Path) -> dict[str, object]:
    repeat_times: list[float] = []
    repeats: list[PilotResult] = []
    for _ in range(3):
        start = time.perf_counter()
        repeat = build_prism_fault()
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
    output = project_root / "_neon_oil_slick_reset_work" / "prism_fault"
    result = timed_result(build_prism_fault)
    manifest = render_evidence(result, output)
    audit = _write_audit(result, output)
    print(json.dumps({"manifest": manifest, "audit": audit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
