"""Wet Apex: a luminous racing line through rain-dark pavement.

SPB-105 / NU-V4-2 / 2026-08-27. Owner verdict: v3 lacked Oil Slick's
coherent SPEC mechanics and did not read as neon, Tokyo Drift, or Fast &
Furious. This broad S-curve owns its water depth, reflection and alternate
view; fine rain anatomy is subordinate rather than a tiled carrier.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, FinishResult, begin, blur, coords, edge, finish, normal_light,
    pack_physical, palette_cycle, ridge, smooth, soft_noise, unit, warp_vortices,
)


FINISH_ID = "neon2_torque_scar"
DISPLAY_NAME = "Wet Apex"
DEFAULT_SEED = 0xA9E55EED


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    """Build a continuous wet racing-line carrier with physical view change."""
    started = begin()
    size = int(size)
    x, y = coords(size)
    scale = size / float(WORK)
    texture = soft_noise(seed ^ 0xC0A57, size, 58.0 * scale, 8.0 * scale)

    curve = 0.34 * np.sin(2.20 * y + 0.30) + 0.075 * np.sin(5.7 * y - 0.25)
    d = x - curve
    lane = np.exp(-((d / 0.46) ** 6))
    racing_line = np.exp(-((d / 0.058) ** 2))
    underglow = np.exp(-((d / 0.24) ** 2))
    inside_edge = np.exp(-(((d + 0.27) / 0.050) ** 2))
    outside_edge = np.exp(-(((d - 0.31) / 0.060) ** 2))

    water_depth = unit(
        0.48 + 0.24 * np.sin(2.0 * y - 1.35 * x)
        + 0.14 * np.sin(5.2 * y + 0.72 * x) + 0.22 * texture
    )
    puddle = smooth(0.50, 0.82, water_depth) * (0.38 + 0.62 * lane)
    reflection_smear = blur(underglow * (0.48 + 0.52 * puddle), 13.0 * scale)
    spray_wake = np.exp(-(((d + 0.12 * np.sin(3.0 * y)) / 0.17) ** 2))
    spray_wake *= ridge(34.0 * y - 8.0 * x + 0.6 * texture, 0.11)
    rain_filaments = ridge(67.0 * (0.22 * x + y) + 0.9 * texture, 0.075) * puddle
    tire_shear = ridge(55.0 * y + 6.0 * d + 0.7 * texture, 0.09) * lane * (1.0 - racing_line)
    curb_blocks = ridge(42.0 * y + 2.0 * np.sin(5.0 * y), 0.16) * np.maximum(inside_edge, outside_edge)
    apex_flash = np.maximum(
        np.exp(-(((y + 0.42) / 0.20) ** 2)) * inside_edge,
        np.exp(-(((y - 0.42) / 0.20) ** 2)) * outside_edge,
    )
    water_lip = np.clip(edge(puddle) * (0.45 + 0.55 * underglow), 0.0, 1.0)

    # SPB-105 / NU-V4-2F / owner whole-car verdict: retain the luminous apex
    # hero while making the entire sheet a smart wet-asphalt material. The
    # added combs/rills are carrier-derived 8-32px drainage anatomy, not grit.
    drainage_depth = smooth(0.28, 0.78, water_depth)
    asphalt_flow = ridge(49.0 * (0.78 * x + 0.20 * y) + 0.50 * texture, 0.13)
    drainage_comb = ridge(63.0 * (0.18 * x + y) + 0.65 * texture, 0.075)
    drainage_comb *= 0.24 + 0.76 * drainage_depth
    water_rills = np.clip(edge(water_depth) * (0.42 + 0.58 * drainage_depth), 0.0, 1.0)
    ghost_curve_a = curve + 0.43 - 0.10 * np.sin(2.8 * y + 0.4)
    ghost_curve_b = curve - 0.56 + 0.08 * np.sin(3.1 * y - 0.2)
    reflected_lines = np.clip(
        np.exp(-(((x - ghost_curve_a) / 0.095) ** 2))
        + 0.68 * np.exp(-(((x - ghost_curve_b) / 0.11) ** 2)),
        0.0, 1.0,
    )
    reflected_line_smear = blur(reflected_lines * (0.30 + 0.70 * drainage_depth), 10.0 * scale)
    # NU-V4-TILE-1 / SPB-105, 2026-08-28. Owner: the live tile retains the
    # hero curve but loses the expensive wet-coating read at picker scale.
    # This is one deformed water-film history within the asphalt—not a second
    # graphic. Its lamellae, order lips and mid-depth pools all originate from
    # the same rain-fed sheet and therefore earn their M/R/Cc differences.
    film_x, film_y = warp_vortices(x, y, (
        (-0.58, -0.38, 0.58, 0.42), (0.36, -0.06, 0.66, -0.37),
        (-0.22, 0.58, 0.54, 0.31),
    ))
    racing_film = unit(
        0.50 + 0.12 * film_x - 0.08 * film_y
        + 0.10 * np.sin(7.6 * film_x + 2.1 * film_y)
        + 0.064 * np.sin(13.4 * film_y - 3.7 * film_x)
        + 0.040 * np.sin(24.0 * film_x + 15.6 * film_y)
        + 0.18 * puddle
    )
    film_slope = edge(racing_film)
    film_fold = ridge(
        film_x * (45.0 + 12.0 * film_slope) + film_y * (16.0 - 5.0 * film_slope),
        0.14,
    ) * (0.28 + 0.72 * drainage_depth)
    film_order = np.mod(2.84 * racing_film + 0.22 * water_depth + 0.11 * underglow, 1.0)
    order_lip = np.exp(-np.minimum(film_order, 1.0 - film_order) / 0.037)
    order_lip *= 0.28 + 0.72 * (puddle + 0.38 * lane)
    film_pool = np.exp(-((racing_film - 0.56) / 0.18) ** 2) * (1.0 - 0.46 * film_slope)
    height = unit(
        0.52 * puddle + 0.38 * reflection_smear + 0.26 * racing_line
        + 0.16 * water_lip + 0.10 * apex_flash + 0.12 * drainage_depth
        + 0.10 * water_rills + 0.09 * reflected_line_smear + 0.13 * film_pool
        + 0.10 * order_lip + 0.07 * film_fold
    )

    def paint_view(
        travel: float,
        light_vec: tuple[float, float, float],
        grazing: float = 0.0,
    ) -> np.ndarray:
        light = normal_light(height, light_vec)
        exposure = np.clip((light + 0.55) / 1.55, 0.0, 1.0)
        optical = np.mod(
            1.52 * water_depth + 0.32 * water_lip + 0.12 * tire_shear
            + 0.16 * reflected_line_smear + 0.10 * drainage_comb
            + 0.26 * racing_film + 0.14 * order_lip
            + travel * (0.54 + 0.46 * exposure),
            1.0,
        )
        wet_color = palette_cycle(
            optical,
            ((0.00, 0.26, 0.40), (0.00, 0.92, 0.78), (0.10, 0.78, 1.00),
             (0.82, 0.24, 1.00), (1.00, 0.18, 0.60), (0.02, 0.38, 0.50)),
        )
        paint = np.zeros((size, size, 3), np.float32)
        paint[:] = (0.005, 0.008, 0.012)
        asphalt = 0.060 + 0.105 * texture
        paint += asphalt[..., None] * np.asarray((0.16, 0.22, 0.31), np.float32)
        # A wet clearcoat does not disappear away from the racing line.  The
        # deformed film gives every tile a low, colored lacquer bed; only its
        # physically pooled/order-lip areas rise to the bright return.
        paint += wet_color * (0.028 + 0.060 * racing_film + 0.046 * film_pool + 0.022 * film_fold)[..., None]
        paint += wet_color * (
            drainage_depth * (0.060 + 0.035 * exposure + 0.060 * float(grazing))
        )[..., None]
        wet_gain = 0.20 + 0.45 * exposure + float(grazing) * (0.48 + 0.46 * water_lip)
        paint += wet_color * (reflection_smear * wet_gain)[..., None]
        paint += wet_color * (
            float(grazing) * 0.66 * blur(puddle + 0.55 * water_lip, 8.0 * scale)
        )[..., None]
        paint += np.asarray((0.00, 1.00, 0.75), np.float32) * (0.62 * racing_line + 0.24 * underglow)[..., None]
        paint += np.asarray((0.92, 0.98, 1.00), np.float32) * (0.32 * apex_flash + 0.18 * water_lip)[..., None]
        paint += np.asarray((0.12, 0.72, 1.00), np.float32) * (0.24 * spray_wake + 0.18 * rain_filaments)[..., None]
        paint += np.asarray((1.00, 0.12, 0.58), np.float32) * (0.20 * curb_blocks + 0.13 * outside_edge)[..., None]
        paint += np.asarray((0.02, 0.42, 0.55), np.float32) * (0.14 * tire_shear)[..., None]
        # Asphalt flow remains a low directional tooth in the lacquer; the
        # single rain/drainage comb is the readable line family. Keeping their
        # paint weights unequal prevents a synthetic cross-hatch/grid read.
        paint += np.asarray((0.05, 0.30, 0.48), np.float32) * (0.035 * asphalt_flow + 0.085 * drainage_comb)[..., None]
        paint += np.asarray((0.18, 0.66, 0.88), np.float32) * (0.13 * water_rills)[..., None]
        # The two displaced reflections are the same apex light transported
        # through separate water-depth lanes.  Giving them enough return keeps
        # an off-curve tile from collapsing into empty asphalt at 128px.
        paint += wet_color * (0.38 * reflected_line_smear + 0.22 * reflected_lines)[..., None]
        paint += wet_color * (0.11 * film_pool + 0.075 * film_fold)[..., None]
        paint += np.asarray((0.82, 0.92, 1.00), np.float32) * (0.10 * order_lip)[..., None]
        return np.clip(paint, 0.0, 1.0)

    paint = paint_view(0.00, (0.50, -0.45, 0.74))
    # SPB-105 / NU-V4-2R / owner verdict: v3 omitted the Oil Slick witness.
    # Water-owned grazing interference moves native A/B delta 0.0274 -> 0.0668.
    paint_b = paint_view(0.52, (-0.74, 0.08, 0.67), 0.75)

    metal = np.clip(
        0.03 + 0.62 * racing_line + 0.48 * apex_flash + 0.32 * curb_blocks
        + 0.25 * water_lip + 0.18 * reflection_smear + 0.22 * reflected_lines
        + 0.16 * water_rills + 0.18 * order_lip + 0.12 * film_fold - 0.24 * texture,
        0.0, 1.0,
    )
    rough = np.clip(
        0.18 + 0.48 * texture + 0.46 * tire_shear + 0.38 * curb_blocks
        + 0.34 * asphalt_flow + 0.32 * drainage_comb + 0.30 * rain_filaments
        + 0.20 * film_slope + 0.18 * film_fold - 0.68 * puddle - 0.34 * racing_line,
        0.0, 1.0,
    )
    coat = np.clip(
        0.10 + 0.72 * puddle + 0.58 * reflection_smear + 0.34 * racing_line
        + 0.36 * drainage_depth + 0.30 * reflected_line_smear + 0.22 * water_lip
        + 0.22 * film_pool + 0.18 * order_lip - 0.48 * tire_shear - 0.32 * curb_blocks
        - 0.20 * asphalt_flow - 0.12 * film_fold,
        0.0, 1.0,
    )
    spec = pack_physical(
        metal, rough, coat,
        m_cuts=(0.07, 0.15, 0.24, 0.34, 0.45, 0.57, 0.69, 0.81, 0.91),
        r_cuts=(0.08, 0.17, 0.27, 0.38, 0.49, 0.60, 0.71, 0.82, 0.92),
        c_cuts=(0.08, 0.17, 0.27, 0.37, 0.48, 0.59, 0.70, 0.81, 0.91),
    )
    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "broad luminous S-curve over full-field smart wet asphalt with puddle depth, one deformed racing-film, order lips, drainage combs/rills, reflected racing lines, spray wake, tire shear and apex curb flashes",
        {
            "M": "hero and reflected racing-line pigment, order lips, apex flashes, curb faces and thin water rills",
            "R": "directional asphalt flow, strained film folds, tire shear, drainage combs, curb blocks and rain-cut microstructure",
            "Cc": "mid-depth racing-film pools, continuous puddle/drainage depth and racing-line smear, reduced where tires and curbs break water",
        },
    )
