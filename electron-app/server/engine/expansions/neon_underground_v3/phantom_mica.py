"""Isolated Phantom Mica pilot for the Neon Underground material reset.

SPB-105 / Neon reset expansion tick #6 / 2026-08-27 owner authorization:
continue the Oil-Slick-derived causal material rebuild beyond the first five.
This unwired pilot owns a smoked-clear stack of asymmetric translucent mica
overlaps.  It deliberately avoids fish/scale silhouettes, closed flake outlines,
rows, macro shards, generic noise, and an unrelated material underlay.

Metric movement: no accepted legacy material -> isolated native evidence.  The
exact M/R/Cc movement and timing are written by ``main`` after every evidence
render; official M7 remains unavailable until an owner keep permits wiring.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import time

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


FINISH_ID = "neon2_phantom_mica"
DISPLAY_NAME = "Phantom Mica"
DEFAULT_SEED = 0xF4A7_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)


def _polyline(mask: np.ndarray, points: list[tuple[float, float]], width: int, value: float) -> None:
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(mask, [pts], False, float(value), int(width), cv2.LINE_AA)


def _filled_polygon(mask: np.ndarray, points: list[tuple[float, float]], value: float) -> None:
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    cv2.fillConvexPoly(mask, pts, float(value), cv2.LINE_AA)


def _ellipse(
    mask: np.ndarray,
    center: tuple[float, float],
    axes: tuple[int, int],
    angle_degrees: float,
    value: float,
) -> None:
    cv2.ellipse(
        mask,
        (int(round(center[0])), int(round(center[1]))),
        (max(1, int(axes[0])), max(1, int(axes[1]))),
        float(angle_degrees),
        0.0,
        360.0,
        float(value),
        -1,
        cv2.LINE_AA,
    )


def _point(origin: tuple[float, float], distance: float, angle: float) -> tuple[float, float]:
    return origin[0] + math.cos(angle) * distance, origin[1] + math.sin(angle) * distance


def _mica_quad(
    center: tuple[float, float],
    half_major: float,
    half_minor: float,
    angle: float,
    asymmetry: float,
) -> list[tuple[float, float]]:
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    cx, cy = center
    return [
        (cx - ux * half_major - vx * half_minor, cy - uy * half_major - vy * half_minor),
        (
            cx + ux * half_major - vx * half_minor * (0.72 + asymmetry),
            cy + uy * half_major - vy * half_minor * (0.72 + asymmetry),
        ),
        (cx + ux * half_major * 0.82 + vx * half_minor, cy + uy * half_major * 0.82 + vy * half_minor),
        (
            cx - ux * half_major * (0.76 - 0.30 * asymmetry) + vx * half_minor * 0.78,
            cy - uy * half_major * (0.76 - 0.30 * asymmetry) + vy * half_minor * 0.78,
        ),
    ]


def _accumulate_overlap(
    body: np.ndarray,
    depth: np.ndarray,
    phase: np.ndarray,
    energy: np.ndarray,
    points: list[tuple[float, float]],
    opacity: float,
    phase_value: float,
    energy_value: float,
) -> None:
    """Alpha-stack one small facet in a bounded ROI and count its overlap."""
    h, w = body.shape
    p = np.rint(np.asarray(points, np.float32)).astype(np.int32)
    x0 = max(0, int(p[:, 0].min()) - 2)
    x1 = min(w, int(p[:, 0].max()) + 3)
    y0 = max(0, int(p[:, 1].min()) - 2)
    y1 = min(h, int(p[:, 1].max()) + 3)
    if x0 >= x1 or y0 >= y1:
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


def _phase_palette(phase: np.ndarray) -> np.ndarray:
    """Orientation/optical-order palette; never a global hue rotation."""
    anchors = np.asarray(
        (
            (0.22, 0.72, 0.95),  # spectral cyan
            (0.63, 0.31, 0.92),  # buried violet
            (0.96, 0.67, 0.37),  # champagne flash
            (0.70, 0.90, 1.00),  # cold pearl
            (0.22, 0.72, 0.95),
        ),
        np.float32,
    )
    p = np.mod(np.asarray(phase, np.float32), 1.0) * 4.0
    index = np.floor(p).astype(np.int32)
    fraction = p - index
    return anchors[index] * (1.0 - fraction[..., None]) + anchors[index + 1] * fraction[..., None]


def _compose_paint(
    body: np.ndarray,
    body_phase: np.ndarray,
    body_energy: np.ndarray,
    leading_lips: np.ndarray,
    lip_phase: np.ndarray,
    ghost_tails: np.ndarray,
    cleavage_steps: np.ndarray,
    occlusion_shadows: np.ndarray,
    fractured_corners: np.ndarray,
    buried_flashes: np.ndarray,
    attached_debris: np.ndarray,
) -> np.ndarray:
    h, w = body.shape
    paint = np.zeros((h, w, 3), np.float32)
    paint[:] = np.asarray((0.010, 0.012, 0.020), np.float32)

    # Dense bodies merge into one smoked-clear film.  Their closed construction
    # shapes remain invisible; only translucency, phase, and overlap are read.
    body_color = _phase_palette(body_phase)
    body_soft = blur(body, 12.0, h)
    body_strength = body * (0.055 + 0.115 * body_energy)
    raw_body = body_color * body_strength[..., None]
    soft_body = np.stack(tuple(blur(raw_body[..., i], 15.0, h) for i in range(3)), axis=2)
    paint += 1.46 * soft_body
    paint += body_soft[..., None] * np.asarray((0.027, 0.033, 0.052), np.float32)

    # Every high-energy accent is physically attached to the overlap stack.
    lip_color = _phase_palette(lip_phase)
    paint += lip_color * (0.46 * leading_lips + 0.56 * np.power(leading_lips, 2.2))[..., None]
    buried_raw = _phase_palette(body_phase + 0.10) * buried_flashes[..., None]
    buried_soft = np.stack(tuple(blur(buried_raw[..., i], 8.0, h) for i in range(3)), axis=2)
    paint += 0.48 * buried_soft
    paint += _phase_palette(body_phase + 0.18) * (0.12 * ghost_tails)[..., None]
    paint += cleavage_steps[..., None] * np.asarray((0.22, 0.25, 0.38), np.float32)
    paint += fractured_corners[..., None] * np.asarray((0.38, 0.20, 0.48), np.float32)
    paint += attached_debris[..., None] * np.asarray((0.18, 0.44, 0.58), np.float32)

    # Trailing occlusion lives under the next translucent plate; it is not a
    # black outline around a polygon.
    paint *= (1.0 - 0.38 * occlusion_shadows[..., None])
    paint += occlusion_shadows[..., None] * np.asarray((0.006, 0.009, 0.018), np.float32)
    # SPB-105 / Neon reset continuation / 2026-08-27 owner verdict: preserve
    # the smoked-clear body but let the physically authored optical phases read
    # as Neon rather than neutral pearl. Isolated M7 before this calibration:
    # 71.7 (M6 saturation miss); post-calibration movement is audited below.
    hsv = cv2.cvtColor(np.clip(paint, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.60, 0.0, 1.0)
    paint = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return np.clip(paint, 0.0, 1.0)


def build_phantom_mica(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build the deterministic Phantom Mica paint and causal M/R/Cc maps."""
    if int(size) < 256:
        raise ValueError("Phantom Mica requires a work raster of at least 256px")
    rng = seeded(seed)
    h = w = int(size)
    shape = (h, w)
    scale = float(size) / float(WORK)

    mica_bodies = np.zeros(shape, np.float32)
    overlap_depth = np.zeros(shape, np.float32)
    body_phase = np.zeros(shape, np.float32)
    body_energy = np.zeros(shape, np.float32)
    leading_lips = np.zeros(shape, np.float32)
    lip_phase = np.zeros(shape, np.float32)
    ghost_tails = np.zeros(shape, np.float32)
    cleavage_steps = np.zeros(shape, np.float32)
    occlusion_shadows = np.zeros(shape, np.float32)
    fractured_corners = np.zeros(shape, np.float32)
    attached_debris = np.zeros(shape, np.float32)

    body_count = 0
    lip_count = 0
    tail_count = 0
    cleavage_count = 0
    shadow_count = 0
    fracture_count = 0
    debris_count = 0

    cell = max(14, int(round(22.0 * scale)))
    for gy, y0 in enumerate(range(-cell, h + cell, cell)):
        for gx, x0 in enumerate(range(-cell, w + cell, cell)):
            if rng.random() < 0.035:
                continue
            cx = float(x0 + rng.uniform(-0.44, 0.44) * cell)
            cy = float(y0 + rng.uniform(-0.44, 0.44) * cell)
            block_x, block_y = gx // 4, gy // 4
            block_hash = (
                (block_x * 0x9E3779B1)
                ^ (block_y * 0x85EBCA77)
                ^ ((2 * block_x - block_y) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            base_angle = (block_hash % 18) * (math.pi / 18.0) + float(rng.uniform(-0.34, 0.34))
            base_phase = float(((block_hash % 127) / 127.0 + rng.uniform(-0.05, 0.05)) % 1.0)
            grammar = int(rng.integers(0, 5))
            stack_total = int(rng.integers(5, 10))
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
                if grammar == 0:  # offset deck
                    major_shift = t * 5.0 * scale
                    minor_shift = t * 10.0 * scale
                    angle += t * 0.12
                elif grammar == 1:  # asymmetric fan
                    major_shift = t * 5.5 * scale
                    minor_shift = abs(t) * 3.0 * scale
                    angle += t * 0.88
                elif grammar == 2:  # crossed burial stack
                    major_shift = t * 7.0 * scale
                    minor_shift = t * 4.0 * scale
                    angle += (-0.48 if stack_index % 2 else 0.38) + t * 0.16
                elif grammar == 3:  # staggered relay
                    major_shift = t * 12.0 * scale
                    minor_shift = math.sin(stack_index * 1.73) * 3.2 * scale
                    angle += float(rng.uniform(-0.22, 0.22))
                else:  # shallow fold packet
                    major_shift = t * 7.0 * scale
                    minor_shift = t * 8.0 * scale
                    angle += (0.24 if stack_index % 2 else -0.18) + t * 0.24

                ux, uy = math.cos(base_angle), math.sin(base_angle)
                vx, vy = -uy, ux
                center = (
                    cx + ux * major_shift + vx * minor_shift + rng.uniform(-1.4, 1.4) * scale,
                    cy + uy * major_shift + vy * minor_shift + rng.uniform(-1.4, 1.4) * scale,
                )
                half_major = float(rng.uniform(4.3, 8.0) * scale)
                half_minor = float(rng.uniform(3.0, 5.0) * scale)
                tier_index = int(rng.integers(0, len(EVENT_TIERS)))
                tier = float(EVENT_TIERS[tier_index])
                optical_phase = float((base_phase + t * 0.11 + tier_index * 0.012) % 1.0)
                quad = _mica_quad(
                    center,
                    half_major,
                    half_minor,
                    angle,
                    float(rng.uniform(-0.22, 0.22)),
                )
                _accumulate_overlap(
                    mica_bodies,
                    overlap_depth,
                    body_phase,
                    body_energy,
                    quad,
                    0.26 + 0.42 * tier,
                    optical_phase,
                    tier,
                )
                stack.append((quad, center, angle, half_major, half_minor, tier, optical_phase))
                body_count += 1

            # Only top-stack and occasional buried-mid plates expose an edge.
            visible_indices = {stack_total - 1}
            if rng.random() < 0.42:
                visible_indices.add(int(rng.integers(1, max(2, stack_total - 1))))
            for visible_index in sorted(visible_indices):
                quad, center, angle, half_major, half_minor, tier, optical_phase = stack[visible_index]
                lead_index = 0 if (visible_index + grammar) % 2 == 0 else 2
                lead = [quad[lead_index], quad[(lead_index + 1) % 4]]
                trail_index = (lead_index + 2) % 4
                trail = [quad[trail_index], quad[(trail_index + 1) % 4]]

                # A bright lip never exists as a freestanding sparkle: the
                # same exposed edge also authors its buried tail and occlusion.
                # Shadow-only edges remain possible deeper in the stack.
                edge_exposed = rng.random() < 0.78
                if edge_exposed:
                    lip_w = max(4, int(round(rng.uniform(4.0, 5.2) * scale)))
                    _polyline(leading_lips, lead, lip_w, tier)
                    _polyline(lip_phase, lead, lip_w, 0.08 + 0.84 * optical_phase)
                    lip_count += 1

                if edge_exposed:
                    ux, uy = math.cos(angle), math.sin(angle)
                    tail_shift = float(rng.uniform(2.8, 5.2) * scale)
                    ghost = [(x - ux * tail_shift, y - uy * tail_shift) for x, y in trail]
                    tail_w = max(4, int(round(rng.uniform(4.0, 5.5) * scale)))
                    _polyline(ghost_tails, ghost, tail_w, 0.24 + 0.64 * tier)
                    tail_count += 1

                if edge_exposed or rng.random() < 0.48:
                    shadow_w = max(4, int(round(rng.uniform(4.0, 5.5) * scale)))
                    _polyline(occlusion_shadows, trail, shadow_w, 0.22 + 0.62 * tier)
                    shadow_count += 1

            # One or two internal cleavage steps belong to the complete stack,
            # rather than being repeated on every microscopic body.
            if rng.random() < 0.74:
                step_total = 1 + int(rng.random() < 0.28)
                source_index = int(rng.integers(max(0, stack_total - 3), stack_total))
                _, center, angle, half_major, half_minor, _, _ = stack[source_index]
                ux, uy = math.cos(angle), math.sin(angle)
                vx, vy = -uy, ux
                for _ in range(step_total):
                    along = float(rng.uniform(-0.40, 0.40) * half_major)
                    step_center = (center[0] + ux * along, center[1] + uy * along)
                    step_half = float(rng.uniform(2.1, 4.0) * scale)
                    p0 = (step_center[0] - vx * step_half, step_center[1] - vy * step_half)
                    p1 = (step_center[0] + vx * step_half, step_center[1] + vy * step_half)
                    step_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                    step_tier = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
                    _polyline(cleavage_steps, [p0, step_center, p1], step_w, step_tier)
                    cleavage_count += 1

            # Fracture/debris affects only a minority of stack-leading corners.
            if rng.random() < 0.25:
                quad, center, angle, _, _, _, _ = stack[-1]
                corner_index = int(rng.integers(0, 4))
                corner = quad[corner_index]
                prev_corner = quad[(corner_index - 1) % 4]
                next_corner = quad[(corner_index + 1) % 4]
                frac = float(rng.uniform(0.28, 0.48))
                triangle = [
                    corner,
                    (
                        corner[0] + (prev_corner[0] - corner[0]) * frac,
                        corner[1] + (prev_corner[1] - corner[1]) * frac,
                    ),
                    (
                        corner[0] + (next_corner[0] - corner[0]) * frac,
                        corner[1] + (next_corner[1] - corner[1]) * frac,
                    ),
                ]
                fracture_tier = float(EVENT_TIERS[int(rng.integers(1, len(EVENT_TIERS)))])
                _filled_polygon(fractured_corners, triangle, fracture_tier)
                fracture_count += 1

                debris_total = 1 + int(rng.random() < 0.42)
                radial_angle = math.atan2(corner[1] - center[1], corner[0] - center[0])
                for _ in range(debris_total):
                    debris_center = _point(
                        corner,
                        float(rng.uniform(3.5, 6.5) * scale),
                        radial_angle + rng.uniform(-0.38, 0.38),
                    )
                    radius_x = max(2, int(round(rng.uniform(2.0, 3.2) * scale)))
                    radius_y = max(2, int(round(rng.uniform(2.0, 3.8) * scale)))
                    debris_tier = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
                    _ellipse(
                        attached_debris,
                        debris_center,
                        (radius_x, radius_y),
                        math.degrees(angle),
                        debris_tier,
                    )
                    debris_count += 1

    # Overlap flashes are intersections of authored mica bodies.  No random
    # sparkle field is introduced after the geometry.
    buried_overlap_flashes = smoothstep(1.4, 3.8, overlap_depth) * mica_bodies
    buried_overlap_flashes *= 0.42 + 0.58 * body_energy

    paint = _compose_paint(
        mica_bodies,
        body_phase,
        body_energy,
        leading_lips,
        lip_phase,
        ghost_tails,
        cleavage_steps,
        occlusion_shadows,
        fractured_corners,
        buried_overlap_flashes,
        attached_debris,
    )

    # Three independent physical responses share the exact authored stack.
    overlap_reach = blur(buried_overlap_flashes, 15.0, size)
    fracture_reach = blur(
        np.maximum.reduce((fractured_corners, cleavage_steps, attached_debris)),
        13.0,
        size,
    )
    tail_reach = blur(ghost_tails, 17.0, size)
    m_score = (
        2.42 * leading_lips
        + 1.86 * buried_overlap_flashes
        + 1.34 * fractured_corners
        + 0.82 * cleavage_steps
        + 0.28 * overlap_reach
        - 0.44 * occlusion_shadows
        - 0.24 * mica_bodies
    )
    r_score = (
        2.05 * fractured_corners
        + 1.68 * cleavage_steps
        + 1.46 * attached_debris
        + 1.10 * occlusion_shadows
        + 0.42 * fracture_reach
        + 0.24 * ghost_tails
        - 1.12 * leading_lips
        - 0.62 * mica_bodies
    )
    c_score = (
        1.52 * mica_bodies
        + 1.38 * ghost_tails
        + 0.72 * buried_overlap_flashes
        + 0.34 * tail_reach
        - 1.94 * fractured_corners
        - 1.42 * cleavage_steps
        - 1.02 * attached_debris
        - 0.48 * occlusion_shadows
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "translucent_mica_overlaps": mica_bodies,
        "asymmetric_leading_lips": leading_lips,
        "ghost_tails": ghost_tails,
        "cleavage_steps": cleavage_steps,
        "occlusion_shadows": occlusion_shadows,
        "fractured_corners": fractured_corners,
        "buried_overlap_flashes": buried_overlap_flashes,
        "attached_mica_debris": attached_debris,
    }
    geometry = (
        GeometryMark("translucent_mica_overlaps", 14.0, body_count),
        GeometryMark("asymmetric_leading_lips", 9.0, lip_count),
        GeometryMark("ghost_tails", 10.0, tail_count),
        GeometryMark("cleavage_steps", 9.0, cleavage_count),
        GeometryMark("occlusion_shadows", 10.0, shadow_count),
        GeometryMark("fractured_corners", 9.0, fracture_count),
        GeometryMark("buried_overlap_flashes", 12.0, body_count),
        GeometryMark("attached_mica_debris", 10.0, debris_count),
    )
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "exposed mica leading lips, fractured tips, cleavage exposure, and buried reflective overlaps",
            "R": "fractured trailing corners, cleavage steps, attached debris, and occluded overlap edges",
            "Cc": "intact transparent mica bodies and healed ghost tails, reduced sharply at every break",
        },
        carrier="smoked dark clear densely loaded with asymmetric translucent 8-32px mica overlap stacks",
        vetoes=(
            "no fish or scale silhouette",
            "no closed polygon/confetti wallpaper",
            "no rows or repeated tiles",
            "no macro shards",
            "no unrelated noise/spec underlay",
        ),
    )


def _write_audit(result: PilotResult, output: Path) -> dict[str, object]:
    repeat_times: list[float] = []
    repeats: list[PilotResult] = []
    for _ in range(3):
        start = time.perf_counter()
        repeat = build_phantom_mica()
        repeat_times.append(time.perf_counter() - start)
        repeats.append(repeat)

    paint_hashes = [hashlib.sha256(r.paint.tobytes()).hexdigest() for r in (result, *repeats)]
    spec_hashes = [hashlib.sha256(r.spec.tobytes()).hexdigest() for r in (result, *repeats)]
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
            "paint_128.png",
            "paint_64.png",
        ],
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    project_root = Path(__file__).resolve().parents[3]
    output = project_root / "_neon_oil_slick_reset_work" / "phantom_mica"
    result = timed_result(build_phantom_mica)
    manifest = render_evidence(result, output)
    audit = _write_audit(result, output)
    print(json.dumps({"manifest": manifest, "audit": audit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
