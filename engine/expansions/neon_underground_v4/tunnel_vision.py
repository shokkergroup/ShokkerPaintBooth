"""Tunnel Vision: vanishing light wedges over a wet midnight tunnel.

SPB-105 / NU-V4-2 / 2026-08-27. Owner verdict: v3 lacked Oil Slick's
coherent SPEC mechanics and did not read as neon, Tokyo Drift, or Fast &
Furious. This finish restores a single perspective carrier and true
light/normal-dependent optical travel instead of a repeated micro-carpet.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, FinishResult, begin, blur, coords, edge, finish, normal_light,
    pack_physical, palette_cycle, ridge, smooth, soft_noise, unit,
)


FINISH_ID = "neon_cyber_yellow"
DISPLAY_NAME = "Tunnel Vision"
DEFAULT_SEED = 0x7A11E120


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    """Build coherent perspective walls, road clear and speed-light anatomy."""
    started = begin()
    size = int(size)
    x, y = coords(size)
    scale = size / float(WORK)

    depth = np.clip((y + 0.58) / 1.58, 0.0, 1.0)
    spread = 0.10 + 0.92 * np.power(depth, 0.82)
    u = (x - 0.035) / spread
    active = smooth(-0.56, -0.30, y)

    road = np.exp(-((u / 0.74) ** 6)) * active
    wall_band = np.exp(-(((np.abs(u) - 0.95) / 0.26) ** 2)) * active
    outer_wall = np.exp(-(((np.abs(u) - 1.34) / 0.34) ** 2)) * active
    horizon_core = np.exp(-(((x - 0.035) / 0.085) ** 2 + ((y + 0.52) / 0.075) ** 2))
    texture = soft_noise(seed ^ 0xA512, size, 54.0 * scale, 9.0 * scale)

    # Perspective seams compress toward the vanishing point. Fine filament
    # bundles remain subordinate inside the few broad wall-light territories.
    perspective_phase = 15.0 * np.log2(0.12 + depth) + 0.55 * texture
    expansion_seams = ridge(perspective_phase, 0.105) * (wall_band + 0.42 * road)
    yellow_wedges = wall_band * smooth(-0.20, 0.18, u)
    cyan_wedges = wall_band * (1.0 - smooth(-0.18, 0.16, u))
    white_lips = np.clip(edge(wall_band) * (0.65 + 0.35 * expansion_seams), 0.0, 1.0)
    road_reflection = blur((0.70 * yellow_wedges + 0.88 * cyan_wedges) * smooth(0.12, 0.96, depth), 12.0 * scale) * road
    lane_filaments = ridge(70.0 * u + 5.5 * perspective_phase, 0.08) * road * smooth(0.22, 0.95, depth)
    ceiling_flicker = ridge(61.0 * x + 8.0 * y + texture, 0.09) * outer_wall
    speed_shear = ridge(54.0 * depth + 3.0 * u, 0.075) * wall_band

    # SPB-105 / NU-V4-2F / owner whole-car verdict: the yellow/cyan wedges stay
    # the hero, while the same tunnel pressure now continues through the road,
    # crown and side shell. All added ribs/combs are coherent 8-32px anatomy.
    side_shell = smooth(0.46, 0.88, np.abs(x)) * active
    side_ribs = ridge(perspective_phase + 0.30 * np.abs(u), 0.10) * side_shell
    side_vents = ridge(62.0 * (0.20 * x + y) + 0.45 * texture, 0.075) * side_shell
    crown_depth = np.clip((-y - 0.39) / 0.61, 0.0, 1.0)
    crown_spread = 0.085 + 0.94 * np.power(crown_depth, 0.84)
    crown_u = (x - 0.035) / crown_spread
    crown = 1.0 - smooth(-0.62, -0.39, y)
    crown_phase = 13.5 * np.log2(0.11 + crown_depth) + 0.20 * np.sin(3.2 * crown_u)
    crown_ribs = ridge(crown_phase, 0.09) * crown
    crown_stringers = ridge(5.2 * crown_u, 0.070) * crown
    lane_seams = ridge(4.6 * u + 0.14 * np.sin(3.0 * y), 0.070) * road
    drainage_comb = ridge(60.0 * depth + 2.8 * u + 0.45 * texture, 0.075) * road
    vanishing_pressure = np.exp(-((u / 0.56) ** 2)) * np.exp(-(((y + 0.40) / 0.30) ** 2))
    structural_field = np.clip(
        np.maximum.reduce((wall_band, 0.72 * side_shell, 0.68 * crown, 0.62 * road)),
        0.0, 1.0,
    )
    height = unit(
        0.52 * wall_band + 0.30 * road_reflection + 0.22 * white_lips
        + 0.14 * expansion_seams + 0.10 * horizon_core + 0.12 * side_ribs
        + 0.10 * crown_ribs + 0.09 * lane_seams + 0.08 * vanishing_pressure
    )

    def paint_view(
        travel: float,
        light_vec: tuple[float, float, float],
        grazing: float = 0.0,
    ) -> np.ndarray:
        light = normal_light(height, light_vec)
        exposure = np.clip((light + 0.55) / 1.55, 0.0, 1.0)
        optical = np.mod(
            0.78 * depth + 0.28 * crown_depth + 0.33 * road_reflection
            + 0.18 * expansion_seams + 0.12 * structural_field
            + travel * (0.48 + 0.52 * exposure),
            1.0,
        )
        reflected_color = palette_cycle(
            optical,
            ((0.00, 0.40, 0.65), (0.00, 0.95, 1.00), (0.90, 1.00, 1.00),
             (1.00, 0.84, 0.02), (1.00, 0.32, 0.04), (0.18, 0.15, 0.58)),
        )
        paint = np.zeros((size, size, 3), np.float32)
        paint[:] = (0.004, 0.006, 0.012)
        paint += structural_field[..., None] * np.asarray((0.014, 0.025, 0.046), np.float32)
        paint += road[..., None] * np.asarray((0.010, 0.024, 0.039), np.float32) * (0.55 + 0.45 * texture[..., None])
        # Wall faces keep their yellow/cyan identity, but more than half of
        # their returned color comes from the local optical order. The B state
        # therefore exposes different attached faces instead of recoloring the
        # complete image after composition.
        yellow_color = 0.43 * np.asarray((0.92, 0.67, 0.00), np.float32) + 0.57 * reflected_color
        cyan_color = 0.43 * np.asarray((0.00, 0.67, 0.94), np.float32) + 0.57 * reflected_color
        wall_gain = float(grazing) * (0.32 + 0.34 * white_lips)
        paint += yellow_color * (yellow_wedges * (0.30 + 0.42 * exposure + wall_gain))[..., None]
        paint += cyan_color * (cyan_wedges * (0.28 + 0.43 * exposure + wall_gain))[..., None]
        paint += reflected_color * (road_reflection * (0.24 + 0.45 * exposure))[..., None]
        paint += reflected_color * (
            float(grazing) * 0.28 * blur(structural_field + road_reflection, 8.0 * scale)
        )[..., None]
        paint += np.asarray((0.88, 0.98, 1.00), np.float32) * (0.32 * white_lips + 0.48 * horizon_core)[..., None]
        paint += np.asarray((1.00, 0.74, 0.06), np.float32) * (0.24 * expansion_seams + 0.18 * speed_shear)[..., None]
        paint += np.asarray((0.05, 0.78, 1.00), np.float32) * (0.24 * lane_filaments + 0.18 * ceiling_flicker)[..., None]
        paint += np.asarray((0.08, 0.34, 0.66), np.float32) * (0.18 * side_ribs + 0.13 * side_vents)[..., None]
        paint += np.asarray((0.30, 0.22, 0.72), np.float32) * (0.15 * crown_ribs + 0.13 * crown_stringers)[..., None]
        paint += np.asarray((0.04, 0.42, 0.62), np.float32) * (0.16 * lane_seams + 0.12 * drainage_comb)[..., None]
        paint += reflected_color * (0.16 * vanishing_pressure)[..., None]
        return np.clip(paint, 0.0, 1.0)

    paint = paint_view(0.00, (0.54, -0.40, 0.74))
    # SPB-105 / NU-V4-2R / owner verdict: v3 omitted the Oil Slick witness.
    # Wall-owned optical return moves native A/B delta 0.0332 -> 0.0665.
    paint_b = paint_view(0.58, (-0.70, 0.12, 0.70), 0.42)

    panel = np.clip(wall_band + 0.52 * outer_wall + 0.38 * side_shell + 0.32 * crown, 0.0, 1.0)
    metal = np.clip(
        0.05 + 0.66 * panel + 0.58 * white_lips + 0.34 * expansion_seams
        + 0.25 * ceiling_flicker + 0.30 * side_ribs + 0.24 * crown_stringers
        + 0.18 * lane_seams - 0.30 * road,
        0.0, 1.0,
    )
    rough = np.clip(
        0.11 + 0.58 * road * (1.0 - road_reflection) + 0.48 * expansion_seams
        + 0.34 * speed_shear + 0.30 * drainage_comb + 0.26 * side_vents
        + 0.22 * texture * structural_field - 0.42 * white_lips,
        0.0, 1.0,
    )
    coat = np.clip(
        0.12 + 0.78 * road_reflection + 0.50 * road + 0.38 * horizon_core
        + 0.24 * wall_band + 0.24 * crown + 0.20 * vanishing_pressure
        - 0.50 * expansion_seams - 0.28 * lane_filaments - 0.20 * drainage_comb,
        0.0, 1.0,
    )
    spec = pack_physical(
        metal, rough, coat,
        m_cuts=(0.08, 0.17, 0.27, 0.38, 0.49, 0.60, 0.71, 0.82, 0.92),
        r_cuts=(0.09, 0.18, 0.28, 0.39, 0.50, 0.61, 0.72, 0.83, 0.93),
        # SPB-105 / NU-V4-2R: fixed physical coat spread 57.55/7 -> 68.83/8.
        c_cuts=(0.06, 0.13, 0.21, 0.30, 0.40, 0.50, 0.60, 0.72, 0.85),
    )
    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one full-field vanishing tunnel carrier with yellow/cyan wall wedges, crown and side ribs, road/lane pressure, wet reflections and fine speed filaments",
        {
            "M": "wall/crown panels, exposed light lips, side ribs, lane hardware and attached reflectors",
            "R": "rain-dark pavement, drainage combs, expansion seams, side vents and tunnel wear",
            "Cc": "wet road and vanishing reflection with smooth crown/wall clear, interrupted by seams",
        },
    )
