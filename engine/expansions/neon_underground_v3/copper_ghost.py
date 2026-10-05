"""Isolated Copper Ghost owner-review pilot for ``neon2_circuit_city``.

SPB-105 | 2026-08-27 | owner verdict: "don't overthink: one solid
candidate, one obvious repair maximum."  The rejected circuit/city treatment
is replaced by one causal black oxidized laminate with buried copper remnants.
Exact movement from no accepted pilot to the generated M/R/Cc and timing
measurements is written to this isolated candidate's manifest and audit.

This module is intentionally unwired.  It imports only shared material-core
utilities and owns its carrier, organic packet grammar, paint composition, and
causal maps.  It contains no unrelated noise, trace grid, or spec underlay.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import gc
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


FINISH_ID = "neon2_circuit_city"
DISPLAY_NAME = "Copper Ghost"
DEFAULT_SEED = 0xC099E257
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.80, 0.94), np.float32)
_FOIL_LOCAL = np.asarray(
    ((-1.00, -0.18), (-0.40, -1.00), (0.65, -0.78), (1.00, 0.16), (0.28, 1.00), (-0.78, 0.66)),
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


def _foil_polygon(
    center: tuple[float, float],
    half_major: float,
    half_minor: float,
    angle: float,
    rng: np.random.Generator,
) -> list[tuple[float, float]]:
    """Six unequal facets make a torn foil remnant, never a board chip."""
    jitter = rng.uniform((-0.12, -0.13), (0.12, 0.13), size=(6, 2)).astype(np.float32)
    local = (_FOIL_LOCAL + jitter) * np.asarray((half_major, half_minor), np.float32)
    ca, sa = math.cos(angle), math.sin(angle)
    rotation = np.asarray(((ca, -sa), (sa, ca)), np.float32)
    world = local @ rotation.T
    world += np.asarray(center, np.float32)
    return [(float(x), float(y)) for x, y in world]


def _accumulate_foil(
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
    mins = np.min(p, axis=0)
    maxs = np.max(p, axis=0)
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


def _palette(values: np.ndarray, anchors: tuple[tuple[float, float, float], ...]) -> np.ndarray:
    palette = np.asarray(anchors, np.float32)
    period = len(anchors) - 1
    p = np.mod(np.asarray(values, np.float32), 1.0) * period
    index = np.floor(p).astype(np.int32)
    fraction = p - index
    return palette[index] * (1.0 - fraction[..., None]) + palette[index + 1] * fraction[..., None]


def _laminate_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.08, 0.19, 0.18),
            (0.22, 0.12, 0.18),
            (0.20, 0.16, 0.09),
            (0.08, 0.18, 0.22),
            (0.08, 0.19, 0.18),
        ),
    )


def _copper_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.58, 0.25, 0.12),
            (0.94, 0.47, 0.18),
            (0.74, 0.24, 0.22),
            (1.00, 0.68, 0.34),
            (0.52, 0.22, 0.14),
            (0.58, 0.25, 0.12),
        ),
    )


def _verdigris_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.08, 0.58, 0.56),
            (0.18, 0.90, 0.72),
            (0.12, 0.62, 0.90),
            (0.36, 0.82, 0.70),
            (0.08, 0.58, 0.56),
        ),
    )


def _dielectric_palette(values: np.ndarray) -> np.ndarray:
    return _palette(
        values,
        (
            (0.54, 0.14, 0.54),
            (0.92, 0.24, 0.72),
            (0.58, 0.30, 0.96),
            (0.88, 0.38, 0.60),
            (0.54, 0.14, 0.54),
        ),
    )


def _compose_paint(
    foil_body: np.ndarray,
    foil_phase: np.ndarray,
    foil_energy: np.ndarray,
    copper_ledges: np.ndarray,
    copper_phase: np.ndarray,
    verdigris_margins: np.ndarray,
    verdigris_phase: np.ndarray,
    dielectric_ghosts: np.ndarray,
    dielectric_phase: np.ndarray,
    copper_pinpoints: np.ndarray,
    trace_stubs: np.ndarray,
    blister_lips: np.ndarray,
    underfilm_shadows: np.ndarray,
    solder_beads: np.ndarray,
    etched_gaps: np.ndarray,
    buried_overlap: np.ndarray,
) -> np.ndarray:
    h, w = foil_body.shape
    paint = np.zeros((h, w, 3), np.float32)
    paint[:] = np.asarray((0.010, 0.014, 0.016), np.float32)

    laminate_color = _laminate_palette(foil_phase)
    film_raw = laminate_color * (foil_body * (0.140 + 0.20 * foil_energy))[..., None]
    film_soft = np.stack(tuple(blur(film_raw[..., i], 11.0, h) for i in range(3)), axis=2)
    paint += 1.52 * film_soft
    paint += laminate_color * (foil_body * (0.050 + 0.065 * foil_energy))[..., None]
    paint += blur(foil_body, 14.0, h)[..., None] * np.asarray((0.034, 0.044, 0.050), np.float32)

    copper_color = _copper_palette(copper_phase)
    verdigris_color = _verdigris_palette(verdigris_phase)
    dielectric_color = _dielectric_palette(dielectric_phase)
    paint += copper_color * (0.31 * copper_ledges + 0.36 * np.power(copper_ledges, 2.0))[..., None]
    paint += verdigris_color * (0.22 * verdigris_margins + 0.22 * np.power(verdigris_margins, 2.0))[..., None]
    paint += dielectric_color * (0.15 * dielectric_ghosts + 0.14 * np.power(dielectric_ghosts, 2.0))[..., None]

    # Secondary events inherit the phase of their parent remnant.
    paint += copper_color * (0.36 * copper_pinpoints + 0.26 * trace_stubs)[..., None]
    paint += dielectric_color * (0.20 * blister_lips)[..., None]
    paint += (0.52 * copper_color + 0.48) * (0.24 * solder_beads)[..., None]
    paint += (0.55 * copper_color + 0.45 * verdigris_color) * (0.20 * buried_overlap)[..., None]

    paint *= 1.0 - 0.35 * underfilm_shadows[..., None]
    paint *= 1.0 - 0.48 * etched_gaps[..., None]
    paint += underfilm_shadows[..., None] * np.asarray((0.003, 0.006, 0.007), np.float32)
    paint += etched_gaps[..., None] * np.asarray((0.002, 0.003, 0.004), np.float32)
    # SPB-105 / 2026-08-27 owner verdict: the oxidized copper phases must stay
    # chromatic at picker scale without widening their 8–32px anatomy. Official
    # isolated M7 before calibration: 71.1 (M6 saturation miss); rerun below.
    hsv = cv2.cvtColor(np.clip(paint, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.80, 0.0, 1.0)
    paint = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return np.clip(paint, 0.0, 1.0)


def build_copper_ghost(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build deterministic oxidized laminate and causal M/R/Cc maps."""
    if int(size) < 256:
        raise ValueError("Copper Ghost requires a work raster of at least 256px")
    rng = seeded(seed)
    h = w = int(size)
    shape = (h, w)
    scale = float(size) / float(WORK)

    foil_body = np.zeros(shape, np.float32)
    foil_depth = np.zeros(shape, np.float32)
    foil_phase = np.zeros(shape, np.float32)
    foil_energy = np.zeros(shape, np.float32)
    copper_ledges = np.zeros(shape, np.float32)
    copper_phase = np.zeros(shape, np.float32)
    verdigris_margins = np.zeros(shape, np.float32)
    verdigris_phase = np.zeros(shape, np.float32)
    dielectric_ghosts = np.zeros(shape, np.float32)
    dielectric_phase = np.zeros(shape, np.float32)
    copper_pinpoints = np.zeros(shape, np.float32)
    trace_stubs = np.zeros(shape, np.float32)
    blister_lips = np.zeros(shape, np.float32)
    underfilm_shadows = np.zeros(shape, np.float32)
    solder_beads = np.zeros(shape, np.float32)
    etched_gaps = np.zeros(shape, np.float32)

    counts = {
        "buried_copper_remnants": 0,
        "short_torn_foil_ledges": 0,
        "cyan_verdigris_margins": 0,
        "magenta_dielectric_ghosts": 0,
        "exposed_copper_pinpoints": 0,
        "clipped_trace_stubs": 0,
        "blister_lips": 0,
        "underfilm_shadows": 0,
        "fractured_solder_beads": 0,
        "dark_etched_gaps": 0,
    }

    cell = max(15, int(round(22.0 * scale)))
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
                ^ ((block_x - 2 * block_y) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_angle = (block_hash % 26) * (math.pi / 26.0) + float(rng.uniform(-0.42, 0.42))
            base_phase = float(((block_hash % 181) / 181.0 + rng.uniform(-0.07, 0.07)) % 1.0)
            grammar = int(rng.integers(0, 4))
            stack_total = int(rng.integers(3, 7))
            stack: list[
                tuple[
                    list[tuple[float, float]],
                    tuple[float, float],
                    float,
                    float,
                    float,
                    float,
                    float,
                ]
            ] = []

            for stack_index in range(stack_total):
                t = (stack_index - 0.5 * (stack_total - 1)) / max(stack_total - 1, 1)
                angle = base_angle
                major_shift = 0.0
                minor_shift = 0.0
                if grammar == 0:  # peeled packet
                    major_shift = t * 8.0 * scale
                    minor_shift = t * 5.0 * scale
                    angle += t * 0.24
                elif grammar == 1:  # oxidation fan
                    major_shift = t * 5.0 * scale
                    minor_shift = abs(t) * 5.5 * scale
                    angle += t * 0.82
                elif grammar == 2:  # staggered underfilm pocket
                    major_shift = t * 11.0 * scale
                    minor_shift = math.sin(stack_index * 1.61) * 2.8 * scale
                    angle += float(rng.uniform(-0.24, 0.24))
                else:  # folded remnant
                    major_shift = t * 7.0 * scale
                    minor_shift = t * 8.0 * scale
                    angle += (0.28 if stack_index % 2 else -0.22) + t * 0.18

                foil_center = _local_point(
                    center,
                    base_angle,
                    major_shift + rng.uniform(-1.4, 1.4) * scale,
                    minor_shift + rng.uniform(-1.4, 1.4) * scale,
                )
                half_major = float(rng.uniform(4.2, 7.0) * scale)
                half_minor = float(rng.uniform(3.1, 5.1) * scale)
                tier_index = int(rng.integers(0, 8))
                tier = float(EVENT_TIERS[tier_index])
                optical_phase = float((base_phase + 0.09 * t + 0.014 * tier_index) % 1.0)
                polygon = _foil_polygon(foil_center, half_major, half_minor, angle, rng)
                _accumulate_foil(
                    foil_body,
                    foil_depth,
                    foil_phase,
                    foil_energy,
                    polygon,
                    0.23 + 0.40 * tier,
                    optical_phase,
                    tier,
                )
                stack.append((polygon, foil_center, angle, half_major, half_minor, tier, optical_phase))
                counts["buried_copper_remnants"] += 1

            visible_indices = {stack_total - 1}
            if rng.random() < 0.36:
                visible_indices.add(int(rng.integers(1, max(2, stack_total - 1))))
            for visible_index in sorted(visible_indices):
                polygon, foil_center, angle, half_major, half_minor, tier, optical_phase = stack[visible_index]
                lead_index = 0 if (visible_index + grammar) % 2 == 0 else 3
                if lead_index == 0:
                    ledge = [polygon[5], polygon[0], polygon[1], polygon[2]]
                    trail = [polygon[2], polygon[3], polygon[4]]
                else:
                    ledge = [polygon[2], polygon[3], polygon[4], polygon[5]]
                    trail = [polygon[5], polygon[0], polygon[1]]
                ledge_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                copper_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                _stroke(copper_ledges, ledge, ledge_w, copper_tier)
                _stroke(copper_phase, ledge, ledge_w, 0.07 + 0.86 * optical_phase)
                counts["short_torn_foil_ledges"] += 1

                margin_shift = float(rng.uniform(1.8, 3.0) * scale)
                margin = _offset_path(ledge, angle, margin_shift)
                margin_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                verdigris_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                _stroke(verdigris_margins, margin, margin_w, verdigris_tier)
                _stroke(verdigris_phase, margin, margin_w, 0.07 + 0.86 * ((optical_phase + 0.23) % 1.0))
                counts["cyan_verdigris_margins"] += 1

                ghost_shift = float(rng.uniform(2.2, 4.0) * scale)
                ghost = _offset_path(trail, angle, -ghost_shift)
                ghost_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                ghost_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                _stroke(dielectric_ghosts, ghost, ghost_w, 0.18 + 0.60 * ghost_tier)
                _stroke(dielectric_phase, ghost, ghost_w, 0.07 + 0.86 * ((optical_phase + 0.47) % 1.0))
                counts["magenta_dielectric_ghosts"] += 1

                shadow_w = max(4, int(round(rng.uniform(4.0, 5.2) * scale)))
                _stroke(underfilm_shadows, trail, shadow_w, 0.22 + 0.62 * tier)
                counts["underfilm_shadows"] += 1

                if rng.random() < 0.62:
                    along = float(rng.uniform(-0.28, 0.28) * half_major)
                    across = float(rng.uniform(-0.20, 0.20) * half_minor)
                    blister_center = _local_point(foil_center, angle, along, across)
                    blister_half = float(rng.uniform(2.2, 4.2) * scale)
                    b0 = _local_point(blister_center, angle, -blister_half, 0.0)
                    bk = _local_point(blister_center, angle, 0.0, rng.uniform(1.2, 2.4) * scale)
                    b1 = _local_point(blister_center, angle, blister_half, 0.0)
                    blister_w = max(4, int(round(rng.uniform(4.0, 4.8) * scale)))
                    _stroke(blister_lips, [b0, bk, b1], blister_w, float(EVENT_TIERS[int(rng.integers(0, 8))]))
                    counts["blister_lips"] += 1

            # The following events attach to the top torn ledge only.
            polygon, foil_center, angle, half_major, half_minor, tier, optical_phase = stack[-1]
            lead_corner = polygon[0 if grammar % 2 == 0 else 3]
            if rng.random() < 0.58:
                stub_angle = angle + rng.uniform(-0.62, 0.62)
                stub_length = float(rng.uniform(4.0, 7.5) * scale)
                stub_mid = _local_point(lead_corner, stub_angle, 0.48 * stub_length, rng.uniform(-1.0, 1.0) * scale)
                stub_end = _local_point(lead_corner, stub_angle, stub_length, rng.uniform(-1.2, 1.2) * scale)
                stub_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                stub_tier = float(EVENT_TIERS[int(rng.integers(0, 8))])
                _stroke(trace_stubs, [lead_corner, stub_mid, stub_end], stub_w, stub_tier)
                counts["clipped_trace_stubs"] += 1

            if rng.random() < 0.54:
                pinpoint_center = _local_point(
                    lead_corner,
                    angle,
                    rng.uniform(1.0, 2.8) * scale,
                    rng.uniform(-1.3, 1.3) * scale,
                )
                radius = max(2, int(round(rng.uniform(2.0, 2.8) * scale)))
                _disc(copper_pinpoints, pinpoint_center, radius, float(EVENT_TIERS[int(rng.integers(1, 8))]))
                counts["exposed_copper_pinpoints"] += 1

            if rng.random() < 0.38:
                bead_center = _local_point(
                    lead_corner,
                    angle + rng.uniform(-0.48, 0.48),
                    rng.uniform(2.8, 5.8) * scale,
                    rng.uniform(-1.4, 1.4) * scale,
                )
                axes = (
                    max(2, int(round(rng.uniform(2.0, 3.0) * scale))),
                    max(2, int(round(rng.uniform(2.0, 3.6) * scale))),
                )
                _ellipse(
                    solder_beads,
                    bead_center,
                    axes,
                    math.degrees(angle + rng.uniform(-0.35, 0.35)),
                    float(EVENT_TIERS[int(rng.integers(0, 8))]),
                )
                counts["fractured_solder_beads"] += 1

            if rng.random() < 0.82:
                gap_center = _local_point(
                    foil_center,
                    angle,
                    rng.uniform(-0.22, 0.22) * half_major,
                    rng.uniform(-0.20, 0.20) * half_minor,
                )
                gap_angle = angle + math.pi * 0.5 + rng.uniform(-0.32, 0.32)
                gap_half = float(rng.uniform(2.2, 4.2) * scale)
                g0 = _local_point(gap_center, gap_angle, -gap_half, 0.0)
                gk = _local_point(gap_center, gap_angle, 0.0, rng.uniform(-1.0, 1.0) * scale)
                g1 = _local_point(gap_center, gap_angle, gap_half, 0.0)
                gap_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                _stroke(etched_gaps, [g0, gk, g1], gap_w, 0.22 + 0.64 * tier)
                counts["dark_etched_gaps"] += 1

    buried_overlap = smoothstep(1.45, 3.20, foil_depth) * foil_body
    buried_overlap *= 0.42 + 0.58 * foil_energy

    paint = _compose_paint(
        foil_body,
        foil_phase,
        foil_energy,
        copper_ledges,
        copper_phase,
        verdigris_margins,
        verdigris_phase,
        dielectric_ghosts,
        dielectric_phase,
        copper_pinpoints,
        trace_stubs,
        blister_lips,
        underfilm_shadows,
        solder_beads,
        etched_gaps,
        buried_overlap,
    )

    metal_reach = blur(np.maximum.reduce((copper_ledges, copper_pinpoints, trace_stubs, solder_beads)), 17.0, size)
    rough_reach = blur(np.maximum.reduce((verdigris_margins, etched_gaps, solder_beads)), 15.0, size)
    coat_reach = blur(np.maximum.reduce((foil_body, dielectric_ghosts, blister_lips)), 15.0, size)
    m_score = (
        2.32 * copper_ledges
        + 2.06 * copper_pinpoints
        + 1.54 * trace_stubs
        + 1.32 * solder_beads
        + 0.92 * buried_overlap
        + 0.38 * metal_reach
        - 0.74 * etched_gaps
        - 0.32 * foil_body
    )
    r_score = (
        2.16 * verdigris_margins
        + 1.92 * etched_gaps
        + 1.48 * solder_beads
        + 1.04 * underfilm_shadows
        + 0.42 * rough_reach
        + 0.28 * trace_stubs
        - 1.10 * copper_ledges
        - 0.62 * foil_body
    )
    c_score = (
        1.62 * foil_body
        + 1.42 * dielectric_ghosts
        + 1.24 * blister_lips
        + 0.68 * buried_overlap
        + 0.34 * coat_reach
        + 0.22 * verdigris_margins
        - 1.82 * copper_pinpoints
        - 1.52 * etched_gaps
        - 1.14 * copper_ledges
        - 0.84 * solder_beads
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "buried_copper_remnants": foil_body,
        "short_torn_foil_ledges": copper_ledges,
        "cyan_verdigris_margins": verdigris_margins,
        "magenta_dielectric_ghosts": dielectric_ghosts,
        "exposed_copper_pinpoints": copper_pinpoints,
        "clipped_trace_stubs": trace_stubs,
        "blister_lips": blister_lips,
        "underfilm_shadows": underfilm_shadows,
        "fractured_solder_beads": solder_beads,
        "dark_etched_gaps": etched_gaps,
    }
    geometry = (
        GeometryMark("buried_copper_remnants", 28.0, counts["buried_copper_remnants"]),
        GeometryMark("short_torn_foil_ledges", 10.0, counts["short_torn_foil_ledges"]),
        GeometryMark("cyan_verdigris_margins", 10.0, counts["cyan_verdigris_margins"]),
        GeometryMark("magenta_dielectric_ghosts", 10.0, counts["magenta_dielectric_ghosts"]),
        GeometryMark("exposed_copper_pinpoints", 9.0, counts["exposed_copper_pinpoints"]),
        GeometryMark("clipped_trace_stubs", 9.0, counts["clipped_trace_stubs"]),
        GeometryMark("blister_lips", 9.0, counts["blister_lips"]),
        GeometryMark("underfilm_shadows", 10.0, counts["underfilm_shadows"]),
        GeometryMark("fractured_solder_beads", 10.0, counts["fractured_solder_beads"]),
        GeometryMark("dark_etched_gaps", 9.0, counts["dark_etched_gaps"]),
    )
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "torn copper ledges, exposed pinpoints, clipped foil stubs, solder remnants, and buried overlap",
            "R": "cyan verdigris margins, etched gaps, fractured solder, and underfilm shadow damage",
            "Cc": "intact oxidized laminate, magenta dielectric ghosts, blister lips, and buried copper; low at exposure",
        },
        carrier="black oxidized laminate densely loaded with overlapping organic 8-32px buried copper remnants",
        vetoes=(
            "no circuit boards, chips, or straight long traces",
            "no city or skyline imagery",
            "no grids, rows, maps, or barcodes",
            "no random confetti",
            "no unrelated noise/spec underlay",
        ),
    )


def _write_audit(result: PilotResult, output: Path) -> dict[str, object]:
    repeat_times: list[float] = []
    paint_hashes = [hashlib.sha256(result.paint.tobytes()).hexdigest()]
    spec_hashes = [hashlib.sha256(result.spec.tobytes()).hexdigest()]
    for _ in range(3):
        # Evidence rendering temporarily allocates several native-size arrays.
        # Release them before timing, and hash each repeat immediately so audit
        # verification does not retain three complete 10-mask pilot results.
        gc.collect()
        start = time.perf_counter()
        repeat = build_copper_ghost()
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
        "max_abs_material_correlation": round(
            float(
                max(
                    abs(np.corrcoef(result.spec[..., 0].ravel(), result.spec[..., 1].ravel())[0, 1]),
                    abs(np.corrcoef(result.spec[..., 0].ravel(), result.spec[..., 2].ravel())[0, 1]),
                    abs(np.corrcoef(result.spec[..., 1].ravel(), result.spec[..., 2].ravel())[0, 1]),
                )
            ),
            6,
        ),
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
    output = project_root / "_neon_oil_slick_reset_work" / "copper_ghost"
    result = timed_result(build_copper_ghost)
    manifest = render_evidence(result, output)
    audit = _write_audit(result, output)
    print(json.dumps({"manifest": manifest, "audit": audit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
