"""Isolated Blue Breakdown pilot for the Neon Underground material reset.

SPB-105 / Neon reset pilot tick #1 / 2026-08-27 owner verdict:
"Claude's rebuild has failed miserably."
This is a clean-sheet, unwired owner-review pilot.  It replaces literal neon
motifs with short dielectric micro-fuse packets in a dark ceramic lacquer.
Metric movement: rejected/unmeasured legacy material -> isolated M/R/Cc std
82.790/83.299/83.261; official M7 remains unavailable until owner keep because
this pilot is intentionally absent from every live registry.
"""
from __future__ import annotations

import json
import math
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


FINISH_ID = "neon_electric_blue"
DISPLAY_NAME = "Blue Breakdown"
DEFAULT_SEED = 0xB10E_2026

# Eight brightness populations are chosen per authored event.  These values
# alter paint and all three causal responses together; they are not a noise or
# post-hoc spec field.
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)


def _polyline(mask: np.ndarray, points: list[tuple[float, float]], width: int, value: float) -> None:
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(mask, [pts], False, float(value), int(width), cv2.LINE_AA)


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


def _facet(
    mask: np.ndarray,
    center: tuple[float, float],
    half_major: float,
    half_minor: float,
    angle: float,
    skew: float,
    value: float,
) -> list[tuple[float, float]]:
    """Draw one irregular sintered ceramic platelet and return its corners."""
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    cx, cy = center
    points = [
        (cx - ux * half_major - vx * half_minor, cy - uy * half_major - vy * half_minor),
        (
            cx + ux * half_major - vx * half_minor * (0.82 + skew),
            cy + uy * half_major - vy * half_minor * (0.82 + skew),
        ),
        (cx + ux * half_major + vx * half_minor, cy + uy * half_major + vy * half_minor),
        (
            cx - ux * half_major + vx * half_minor * (0.86 - skew),
            cy - uy * half_major + vy * half_minor * (0.86 - skew),
        ),
    ]
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    cv2.fillConvexPoly(mask, pts, float(value), cv2.LINE_AA)
    return points


def _point(origin: tuple[float, float], distance: float, angle: float) -> tuple[float, float]:
    return origin[0] + math.cos(angle) * distance, origin[1] + math.sin(angle) * distance


def _compose_paint(
    ceramic_facets: np.ndarray,
    vitrified_edges: np.ndarray,
    primary: np.ndarray,
    secondary: np.ndarray,
    lips: np.ndarray,
    channels: np.ndarray,
    shoulders: np.ndarray,
    beads: np.ndarray,
    bridges: np.ndarray,
    residue: np.ndarray,
    nodes: np.ndarray,
    intact: np.ndarray,
) -> np.ndarray:
    """Compose the carrier only from the authored dielectric history."""
    h, w = primary.shape
    paint = np.zeros((h, w, 3), np.float32)

    # Deep ceramic rather than pure black: intact clear carries a restrained
    # blue-violet body, while every brighter mark remains rupture-attached.
    paint[:] = np.asarray((0.007, 0.014, 0.035), np.float32)
    paint += ceramic_facets[..., None] * np.asarray((0.012, 0.034, 0.095), np.float32)
    paint += np.power(ceramic_facets, 2.0)[..., None] * np.asarray((0.006, 0.018, 0.052), np.float32)
    paint += vitrified_edges[..., None] * np.asarray((0.010, 0.052, 0.16), np.float32)
    paint += intact[..., None] * np.asarray((0.008, 0.014, 0.030), np.float32)
    electrical_haze = blur(np.maximum(primary, secondary), 27.0, h)
    thermal_haze = blur(np.maximum(shoulders, residue), 19.0, h)
    paint += electrical_haze[..., None] * np.asarray((0.006, 0.052, 0.15), np.float32)
    paint += thermal_haze[..., None] * np.asarray((0.050, 0.004, 0.095), np.float32)
    paint += shoulders[..., None] * np.asarray((0.20, 0.020, 0.50), np.float32)
    paint += residue[..., None] * np.asarray((0.13, 0.012, 0.23), np.float32)

    # A fused lip has a cobalt body, an electric-blue leading face, and a small
    # white-blue exposure peak.  The tiered event value varies each packet.
    paint += primary[..., None] * np.asarray((0.008, 0.052, 0.18), np.float32)
    paint += lips[..., None] * np.asarray((0.035, 0.31, 0.82), np.float32)
    paint += np.power(lips, 2.55)[..., None] * np.asarray((0.31, 0.58, 0.72), np.float32)
    paint += secondary[..., None] * np.asarray((0.010, 0.070, 0.21), np.float32)
    paint += beads[..., None] * np.asarray((0.38, 0.68, 1.02), np.float32)
    paint += nodes[..., None] * np.asarray((0.55, 0.66, 0.84), np.float32)
    paint += bridges[..., None] * np.asarray((0.06, 0.40, 0.68), np.float32)
    paint += np.power(bridges, 2.2)[..., None] * np.asarray((0.15, 0.25, 0.30), np.float32)

    # Quenched ceramic is a blue-black trough, not a black line pasted over a
    # glow.  Its cobalt floor preserves microstructure in native and picker views.
    trough = np.clip(channels * (1.0 - 0.72 * bridges), 0.0, 1.0)
    paint *= (1.0 - 0.88 * trough[..., None])
    paint += trough[..., None] * np.asarray((0.004, 0.015, 0.050), np.float32)
    return np.clip(paint, 0.0, 1.0)


def build_blue_breakdown(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic dark-ceramic dielectric breakdown sheet.

    The working raster is 1024 and the evidence contract performs the exact
    native 2048 enlargement.  Every drawn primitive therefore uses 4--16 work
    pixels, corresponding to the owner's required 8--32 native pixels.
    """
    if int(size) < 256:
        raise ValueError("Blue Breakdown requires a work raster of at least 256px")
    rng = seeded(seed)
    shape = (int(size), int(size))

    ceramic_facets = np.zeros(shape, np.float32)
    vitrified_edges = np.zeros(shape, np.float32)
    primary_path = np.zeros(shape, np.float32)
    fused_lip_lines = np.zeros(shape, np.float32)
    temper_shoulder_lines = np.zeros(shape, np.float32)
    secondary_path = np.zeros(shape, np.float32)
    secondary_lips = np.zeros(shape, np.float32)
    corona_beads = np.zeros(shape, np.float32)
    healed_bridges = np.zeros(shape, np.float32)
    residue_flecks = np.zeros(shape, np.float32)
    rupture_nodes = np.zeros(shape, np.float32)

    scale = float(size) / float(WORK)
    cell = max(22, int(round(34 * scale)))
    margin = max(10, int(round(13 * scale)))
    packet_count = 0
    fork_count = 0
    bead_count = 0
    bridge_count = 0
    residue_count = 0
    node_count = 0
    lip_count = 0
    shoulder_count = 0
    facet_count = 0
    facet_edge_count = 0

    # Full-surface carrier: overlapping anisotropic ceramic platelets are fired
    # into a continuous dielectric sheet.  These are authored 8--32px facets,
    # not FBM, grain, a Voronoi crackle, or an unrelated spec backdrop.
    facet_cell = max(7, int(round(10.0 * scale)))
    for fy, y0 in enumerate(range(-facet_cell, size + facet_cell, facet_cell)):
        for fx, x0 in enumerate(range(-facet_cell, size + facet_cell, facet_cell)):
            center = (
                float(x0 + rng.uniform(-0.42, 0.42) * facet_cell),
                float(y0 + rng.uniform(-0.42, 0.42) * facet_cell),
            )
            block_x, block_y = fx // 5, fy // 5
            block_hash = (
                (block_x * 0x45D9F3B) ^ (block_y * 0x119DE1F3) ^ ((block_x + block_y) * 0x27D4EB2D)
            ) & 0xFFFFFFFF
            block_angle = (block_hash % 12) * (math.pi / 12.0)
            facet_angle = block_angle + float(rng.uniform(-0.34, 0.34))
            half_major = float(rng.uniform(4.0, 8.0) * scale)
            half_minor = float(rng.uniform(2.1, 4.0) * scale)
            facet_energy = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
            corners = _facet(
                ceramic_facets,
                center,
                half_major,
                half_minor,
                facet_angle,
                float(rng.uniform(-0.18, 0.18)),
                facet_energy,
            )
            facet_count += 1

            # Only one platelet face is vitrified.  Avoiding closed outlines is
            # what keeps the carrier from becoming polygon/paver wallpaper.
            if rng.random() < 0.72:
                edge_index = int(rng.integers(0, 4))
                p0 = corners[edge_index]
                p1 = corners[(edge_index + 1) % 4]
                edge_energy = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
                edge_w = max(4, int(round(rng.uniform(4.0, 5.2) * scale)))
                _polyline(vitrified_edges, [p0, p1], edge_w, edge_energy)
                facet_edge_count += 1

    # Each jittered cell owns an irregular electrical-tree packet assembled
    # from several *separate* 8--32px events.  The cluster provides hierarchy;
    # no individual primitive is enlarged into a macro crack or icon.
    for gy, y0 in enumerate(range(-cell // 2, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell // 2, size + cell, cell)):
            if rng.random() < 0.055:
                continue
            cx = float(x0 + rng.uniform(-0.38, 0.38) * cell)
            cy = float(y0 + rng.uniform(-0.38, 0.38) * cell)
            if cx < -margin or cy < -margin or cx > size + margin or cy > size + margin:
                continue

            # Piecewise firing domains share orientation locally without the
            # continuous streamlines/contours that belong to Oil Slick.
            domain_x, domain_y = gx // 3, gy // 3
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x - domain_y) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain = (domain_hash % 12) * (math.pi / 6.0)
            root_theta = float(domain + rng.uniform(-0.27, 0.27))
            packet_energy = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])
            packet_grammar = int(rng.integers(0, 4))
            segment_total = int(rng.integers(2, 9))
            segments: list[
                tuple[
                    tuple[float, float],
                    tuple[float, float],
                    tuple[float, float],
                    float,
                    float,
                ]
            ] = []

            for segment_index in range(segment_total):
                if segment_index == 0:
                    theta = root_theta
                    length = float(rng.uniform(9.0, 15.5) * scale)
                    center = (cx, cy)
                    start = _point(center, -0.50 * length, theta)
                else:
                    # Four packet grammars break the repeated three-prong read:
                    # sharp tree, shallow delamination, counter-fan, and
                    # staggered discharge.  Parent depth stays bounded.
                    parent = segments[int(rng.integers(0, min(4, len(segments))))]
                    parent_anchor = parent[1] if rng.random() < 0.58 else parent[2]
                    side = -1.0 if rng.random() < 0.5 else 1.0
                    if packet_grammar == 0:
                        theta = parent[3] + side * float(rng.uniform(0.48, 1.22))
                    elif packet_grammar == 1:
                        theta = parent[3] + side * float(rng.uniform(0.14, 0.43))
                    elif packet_grammar == 2:
                        theta = root_theta + side * float(rng.uniform(0.82, 1.78))
                        parent_anchor = segments[0][1] if rng.random() < 0.62 else parent_anchor
                    else:
                        theta = domain + float(rng.uniform(-0.62, 0.62))
                    length = float(rng.uniform(5.0, 11.5) * scale)
                    gap = float(rng.uniform(1.4, 3.2) * scale)
                    start = _point(parent_anchor, gap, theta)

                bend = float(rng.uniform(-0.22, 0.22))
                middle = _point(start, 0.50 * length, theta + bend)
                end = _point(start, length, theta + 0.62 * bend)
                points = [start, middle, end]
                local_tier = int(
                    np.clip(
                        int(np.searchsorted(EVENT_TIERS, packet_energy)) + int(rng.integers(-2, 3)),
                        0,
                        len(EVENT_TIERS) - 1,
                    )
                )
                energy = float(EVENT_TIERS[local_tier])
                core_w = max(4, int(round(rng.uniform(4.0, 5.1) * scale)))
                if segment_index == 0:
                    _polyline(primary_path, points, core_w, 0.34 + 0.64 * energy)
                    packet_count += 1
                else:
                    _polyline(secondary_path, points, core_w, 0.36 + 0.62 * energy)
                    fork_count += 1

                # One-sided vitrification is drawn as an open rail.  Secondary
                # branch lips use a different target mask but the same parent.
                lip_side = -1.0 if rng.random() < 0.5 else 1.0
                nx, ny = -math.sin(theta), math.cos(theta)
                lip_offset = float(rng.uniform(3.2, 4.4) * scale) * lip_side
                lip_points = [(x + nx * lip_offset, y + ny * lip_offset) for x, y in points]
                lip_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                lip_target = fused_lip_lines if segment_index == 0 else secondary_lips
                _polyline(lip_target, lip_points, lip_w, energy)
                lip_count += 1

                # Temper shoulders occur on most, not all, segments.  Their
                # short outer-half rail gives the cluster thermal direction.
                if rng.random() < 0.76:
                    shoulder_offset = float(rng.uniform(6.0, 7.6) * scale) * lip_side
                    shoulder_points = [
                        (middle[0] + nx * shoulder_offset, middle[1] + ny * shoulder_offset),
                        (end[0] + nx * shoulder_offset, end[1] + ny * shoulder_offset),
                    ]
                    shoulder_w = max(4, int(round(rng.uniform(4.0, 5.2) * scale)))
                    _polyline(
                        temper_shoulder_lines,
                        shoulder_points,
                        shoulder_w,
                        0.20 + 0.66 * energy,
                    )
                    shoulder_count += 1

                # Rare counter-lip fragments expose a second response without
                # ever closing the path into a capsule.
                if rng.random() < 0.17:
                    counter = -lip_offset * rng.uniform(0.82, 1.04)
                    counter_points = [
                        (start[0] + nx * counter, start[1] + ny * counter),
                        (middle[0] + nx * counter, middle[1] + ny * counter),
                    ]
                    _polyline(lip_target, counter_points, lip_w, float(EVENT_TIERS[max(0, local_tier - 2)]))
                    lip_count += 1

                segments.append((start, middle, end, theta, energy))

            # Corona collects on a few terminal tips, tied to this packet's
            # branches rather than scattered over the carrier.
            terminal_count = int(rng.integers(1, min(4, len(segments)) + 1))
            terminal_indices = rng.choice(len(segments), size=terminal_count, replace=False)
            for terminal_index in np.atleast_1d(terminal_indices):
                segment = segments[int(terminal_index)]
                if rng.random() < 0.64:
                    endpoint = segment[2]
                    bead_theta = segment[3] + rng.choice((-1.0, 1.0)) * rng.uniform(0.58, 1.18)
                    bead_center = _point(endpoint, rng.uniform(3.4, 6.2) * scale, bead_theta)
                    radius = max(2, int(round(rng.uniform(2.0, 3.7) * scale)))
                    bead_energy = float(EVENT_TIERS[int(rng.integers(2, len(EVENT_TIERS)))])
                    _ellipse(corona_beads, bead_center, (radius, radius), 0.0, bead_energy)
                    bead_count += 1

            # Healed glass crosses one selected segment and therefore remains
            # physically attached even when the packet is viewed in isolation.
            if rng.random() < 0.69:
                segment = segments[int(rng.integers(0, len(segments)))]
                anchor = segment[1]
                bridge_theta = segment[3] + math.pi * 0.5 + rng.uniform(-0.17, 0.17)
                bridge_len = float(rng.uniform(5.0, 9.5) * scale)
                b0 = _point(anchor, -0.5 * bridge_len, bridge_theta)
                b1 = _point(anchor, 0.5 * bridge_len, bridge_theta)
                bridge_energy = float(EVENT_TIERS[int(rng.integers(1, len(EVENT_TIERS)))])
                bridge_w = max(4, int(round(rng.uniform(4.0, 5.6) * scale)))
                _polyline(healed_bridges, [b0, anchor, b1], bridge_w, bridge_energy)
                bridge_count += 1

            # Residue flecks are short heat-aligned slashes on packet flanks,
            # not isolated ellipses or generic grit.
            for _ in range(int(rng.integers(1, 4))):
                segment = segments[int(rng.integers(0, len(segments)))]
                side = -1.0 if rng.random() < 0.5 else 1.0
                residue_theta = segment[3] + side * math.pi * 0.5
                residue_center = _point(segment[1], rng.uniform(6.0, 9.0) * scale, residue_theta)
                slash_theta = segment[3] + rng.uniform(-0.38, 0.38)
                slash_len = float(rng.uniform(4.0, 7.5) * scale)
                s0 = _point(residue_center, -0.5 * slash_len, slash_theta)
                s1 = _point(residue_center, 0.5 * slash_len, slash_theta)
                residue_energy = float(EVENT_TIERS[int(rng.integers(0, 7))])
                residue_w = max(4, int(round(rng.uniform(4.0, 5.0) * scale)))
                _polyline(residue_flecks, [s0, residue_center, s1], residue_w, residue_energy)
                residue_count += 1

            # A fused root node is rare and requires a genuinely high packet.
            if packet_energy >= 0.67 and rng.random() < 0.32:
                radius = max(3, int(round(rng.uniform(3.0, 4.8) * scale)))
                _ellipse(rupture_nodes, (cx, cy), (radius, radius), 0.0, packet_energy)
                node_count += 1

    # These are independently authored open rails attached to their rupture,
    # not subtraction-generated rings or generic contour decoration.
    fused_lips = np.clip(np.maximum(fused_lip_lines, secondary_lips), 0.0, 1.0)
    violet_shoulders = np.clip(temper_shoulder_lines, 0.0, 1.0)
    secondary_forks = np.clip(secondary_path, 0.0, 1.0)
    quenched_channels = np.clip(
        np.maximum(primary_path, secondary_path) * (1.0 - 0.66 * healed_bridges),
        0.0,
        1.0,
    )

    damage = np.maximum.reduce(
        (
            primary_path,
            fused_lips,
            secondary_path,
            residue_flecks,
            rupture_nodes,
        )
    )
    damage_binary = (damage > 0.08).astype(np.uint8)
    distance_to_damage = cv2.distanceTransform(1 - damage_binary, cv2.DIST_L2, 5).astype(np.float32)
    intact = smoothstep(2.0 * scale, 14.0 * scale, distance_to_damage)

    paint = _compose_paint(
        ceramic_facets,
        vitrified_edges,
        primary_path,
        secondary_forks,
        fused_lips,
        quenched_channels,
        violet_shoulders,
        corona_beads,
        healed_bridges,
        residue_flecks,
        rupture_nodes,
        intact,
    )

    # Continuous material scores answer three different physical questions.
    # Their only full-field components are diffusion/distance from authored
    # damage; there is no unrelated FBM, grain, or generic spec underlay.
    electrical_reach = blur(
        np.maximum.reduce((primary_path, secondary_path, corona_beads, rupture_nodes)),
        22.0,
        size,
    )
    heat_reach = blur(
        np.maximum.reduce((fused_lips, violet_shoulders, residue_flecks)),
        17.0,
        size,
    )
    bridge_reach = blur(healed_bridges, 13.0, size)

    m_score = (
        2.55 * fused_lips
        + 2.05 * rupture_nodes
        + 1.48 * corona_beads
        + 1.18 * healed_bridges
        + 0.24 * electrical_reach
        + 0.10 * vitrified_edges
        - 0.12 * ceramic_facets
        - 1.10 * quenched_channels
        - 0.38 * residue_flecks
    )
    r_score = (
        2.38 * quenched_channels
        + 1.74 * residue_flecks
        + 1.26 * violet_shoulders
        + 0.88 * secondary_path
        + 0.31 * heat_reach
        + 0.72 * vitrified_edges
        + 0.36 * (1.0 - ceramic_facets)
        - 1.33 * fused_lips
        - 0.82 * healed_bridges
        - 0.52 * corona_beads
    )
    c_score = (
        0.74 * intact
        + 2.12 * healed_bridges
        + 1.08 * corona_beads
        + 0.82 * bridge_reach
        + 1.76 * violet_shoulders
        + 0.48 * heat_reach
        + 0.86 * ceramic_facets
        - 0.44 * vitrified_edges
        - 1.02 * quenched_channels
        - 0.64 * fused_lips
        - 0.72 * residue_flecks
        - 0.34 * rupture_nodes
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "sintered_ceramic_facets": ceramic_facets,
        "vitrified_facet_edges": vitrified_edges,
        "primary_fissures": primary_path,
        "secondary_forks": secondary_forks,
        "fused_lips": fused_lips,
        "quenched_channels": quenched_channels,
        "violet_temper_shoulders": violet_shoulders,
        "corona_beads": corona_beads,
        "healed_glass_bridges": healed_bridges,
        "residue_flecks": residue_flecks,
        "rupture_nodes": rupture_nodes,
    }
    geometry = (
        GeometryMark("sintered_ceramic_facets", 12.0, facet_count),
        GeometryMark("vitrified_facet_edges", 9.0, facet_edge_count),
        GeometryMark("primary_fissures", 9.0, packet_count),
        GeometryMark("secondary_forks", 9.0, fork_count),
        GeometryMark("fused_lips", 9.0, lip_count),
        GeometryMark("quenched_channels", 9.0, packet_count + fork_count),
        GeometryMark("violet_temper_shoulders", 9.0, shoulder_count),
        GeometryMark("corona_beads", 12.0, bead_count),
        GeometryMark("healed_glass_bridges", 10.0, bridge_count),
        GeometryMark("residue_flecks", 10.0, residue_count),
        GeometryMark("rupture_nodes", 16.0, node_count),
    )
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "fused substrate lips, rupture nodes, corona electrodes, and vitrified repair bridges",
            "R": "vitrified facet edges, quenched char, ceramic residue, temper shoulders, and secondary rupture texture",
            "Cc": "sintered facet faces, intact ceramic distance, and healed glass bridges, cut by rupture exposure",
        },
        carrier="full-surface sintered dark-ceramic facets carrying dense discontinuous 8-32px micro-fuse trees",
        vetoes=(
            "no lightning-bolt silhouette",
            "no connected Voronoi crackle",
            "no neon tube",
            "no Oil Slick flow contour",
            "no unrelated noise/spec underlay",
        ),
    )


def main() -> int:
    project_root = Path(__file__).resolve().parents[3]
    output = project_root / "_neon_oil_slick_reset_work" / "blue_breakdown"
    result = timed_result(build_blue_breakdown)
    manifest = render_evidence(result, output)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
