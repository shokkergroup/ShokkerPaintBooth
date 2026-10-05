"""Split Underglow -- opposed cyan and magenta ground-light basins."""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, edge, finish, normal_light, pack_physical,
    palette_ramp, ridge, smooth, soft_noise, unit, warp_vortices,
)


# SPB-105 / NU-V4-SPLIT-UNDERGLOW, 2026-08-27. Owner verdict: v3 lacked
# Oil Slick's coherent SPEC behavior and did not read as neon/Tokyo Drift.
# Opposed cyan/magenta ground-light basins and a smoked central body are the
# broad silhouette. Full-field light-fed body panels, fold shoulders, emitter
# rails, diffuser ribs, road echoes, overlap lips, condensation streaks and
# housing chips provide attached 8-32px anatomy without filler texture.
FINISH_ID = "neon_dual_glow"
DISPLAY_NAME = "Split Underglow"


def build(seed: int = 74653, size: int = WORK):
    started = begin()
    x, y = coords(size)
    road = soft_noise(seed + 5, size, max(44.0, size / 15.0), max(5.0, size / 180.0))

    cyan_d = ((x + 0.53) / 0.72) ** 2 + ((y - 0.40) / 0.55) ** 2
    magenta_d = ((x - 0.53) / 0.72) ** 2 + ((y - 0.40) / 0.55) ** 2
    cyan_source = np.exp(-(cyan_d ** 1.45)) * (0.84 + 0.16 * road)
    magenta_source = np.exp(-(magenta_d ** 1.45)) * (0.84 + 0.16 * (1.0 - road))

    body_axis = y - (-0.15 + 0.13 * np.cos(2.2 * x) - 0.055 * x)
    smoked_body = np.exp(-((body_axis / 0.245) ** 6))
    body_edge = smooth(0.52, 0.82, edge(smoked_body))
    under_mask = smooth(-0.08, 0.30, body_axis)
    cyan = cyan_source.copy()
    magenta = magenta_source.copy()
    cyan *= 0.30 + 0.70 * under_mask
    magenta *= 0.30 + 0.70 * under_mask
    overlap = np.minimum(cyan, magenta)

    # The ground emitters illuminate the entire smoked body, not just the lower
    # half of the canvas. These two wider transport lobes share the exact source
    # centers and colors of the hero underglow, then decay upward through the
    # panel stack. No unrelated noise or brightness quota participates.
    vertical_transport = np.exp(-(((y - 0.30) / 1.26) ** 2))
    cyan_cast = np.exp(-(((x + 0.53) / 0.98) ** 2)) * vertical_transport
    magenta_cast = np.exp(-(((x - 0.53) / 0.98) ** 2)) * vertical_transport
    cast_overlap = np.minimum(cyan_cast, magenta_cast)
    cast_energy = np.clip(cyan_cast + magenta_cast, 0.0, 1.0)
    upper_weight = np.clip(1.0 - 0.38 * under_mask, 0.62, 1.0)

    # Three unequal stamped-panel folds span the UV field. Broad shoulders own
    # the material hierarchy; their 10-28px native lips and ribs are subordinate.
    fold_a_axis = y - (-0.70 + 0.095 * np.sin(2.30 * x + 0.35))
    fold_b_axis = y - (-0.38 - 0.075 * np.sin(2.75 * x - 0.70))
    fold_c_axis = x - (0.22 + 0.28 * np.sin(1.55 * y + 0.45))
    fold_a = np.exp(-((fold_a_axis / 0.115) ** 4))
    fold_b = np.exp(-((fold_b_axis / 0.105) ** 4))
    fold_c = np.exp(-((fold_c_axis / 0.125) ** 4))
    fold_body = np.clip(fold_a + 0.90 * fold_b + 0.72 * fold_c, 0.0, 1.0)
    fold_lip = np.clip(
        np.exp(-((fold_a_axis / 0.014) ** 2))
        + np.exp(-((fold_b_axis / 0.012) ** 2))
        + 0.82 * np.exp(-((fold_c_axis / 0.013) ** 2)),
        0.0, 1.0,
    )
    panel_height = np.clip(0.34 + 0.36 * fold_body + 0.18 * smoked_body + 0.12 * cast_energy, 0.0, 1.0)
    panel_ribs = ridge(38.0 * (x + 0.13 * y) + 0.65 * np.sin(3.0 * y), 0.14)
    panel_ribs *= fold_body * upper_weight
    upper_reflection = ridge(20.0 * y + 0.82 * np.sin(2.7 * x), 0.090)
    upper_reflection *= cast_energy * (1.0 - 0.52 * under_mask)

    # SPB-105 / NU-V4-TILE-1, 2026-08-28. Owner: the card-scale split reads
    # as a generic cyan/magenta gradient.  This is a single deformed smoked
    # clear film carried by the same opposing light basins—not rainbow noise
    # or pasted decoration. Its order lips make the panel surface legible in
    # every tile and feed three different physical responses below.
    film_x, film_y = warp_vortices(x, y, (
        (-0.63, -0.35, 0.62, 0.37), (0.42, -0.12, 0.56, -0.31),
        (-0.20, 0.59, 0.68, 0.28),
    ))
    smoked_film = unit(
        0.50 + 0.12 * film_x - 0.07 * film_y
        + 0.094 * np.sin(7.5 * film_x + 2.4 * film_y)
        + 0.061 * np.sin(13.7 * film_y - 4.1 * film_x)
        + 0.037 * np.sin(25.0 * film_x + 14.0 * film_y)
        + 0.16 * cast_energy + 0.11 * fold_body
    )
    film_slope = edge(smoked_film)
    film_lamella = ridge(
        film_x * (43.0 + 11.0 * film_slope) + film_y * (17.0 - 5.0 * film_slope),
        0.14,
    ) * (0.26 + 0.74 * cast_energy)
    film_order = np.mod(2.62 * smoked_film + 0.18 * cast_overlap + 0.10 * fold_body, 1.0)
    film_lip = np.exp(-np.minimum(film_order, 1.0 - film_order) / 0.038)
    film_lip *= 0.20 + 0.80 * (cast_energy + 0.34 * fold_body)
    film_pool = np.exp(-((smoked_film - 0.55) / 0.18) ** 2) * (1.0 - 0.48 * film_slope)

    cyan_rail = np.exp(-(((y - (0.27 + 0.035 * np.sin(3.0 * x))) / 0.018) ** 2)) * smooth(-0.96, -0.02, x)
    magenta_rail = np.exp(-(((y - (0.27 - 0.035 * np.sin(3.0 * x))) / 0.018) ** 2)) * smooth(0.02, 0.96, x)
    diffusion = ridge(37.0 * (x + 0.11 * np.sin(4.0 * y)) + 1.8 * road, 0.055)
    diffusion *= np.clip(cyan + magenta, 0.0, 1.0) * under_mask
    road_echo = ridge(25.0 * y + 1.4 * np.sin(3.1 * x) + 1.2 * road, 0.060)
    road_echo *= smooth(0.18, 0.72, cyan + magenta) * smooth(0.22, 0.90, y)
    condensation = ridge(61.0 * (0.19 * x + y) + 2.0 * road, 0.042)
    condensation *= smoked_body * smooth(0.66, 0.90, road)
    chips = ridge(69.0 * (x - 0.24 * y) + 0.8, 0.037) * body_edge * smooth(0.57, 0.86, road)

    ground = palette_ramp(0.66 * road + 0.13 * y, (
        (0.008, 0.012, 0.022), (0.022, 0.036, 0.055),
        (0.055, 0.067, 0.085), (0.10, 0.105, 0.12),
    ))
    paint = ground.copy()
    paint += cyan[..., None] * np.asarray((0.005, 0.62, 0.84), np.float32)
    paint += magenta[..., None] * np.asarray((0.78, 0.015, 0.59), np.float32)
    paint += overlap[..., None] * np.asarray((0.34, 0.03, 0.56), np.float32)
    paint *= (1.0 - 0.64 * smoked_body[..., None])
    paint += smoked_body[..., None] * np.asarray((0.028, 0.037, 0.065), np.float32)
    panel_color = (
        cyan_cast[..., None] * np.asarray((0.018, 0.28, 0.39), np.float32)
        + magenta_cast[..., None] * np.asarray((0.35, 0.018, 0.27), np.float32)
        + cast_overlap[..., None] * np.asarray((0.18, 0.035, 0.30), np.float32)
    )
    paint += panel_color * (0.40 + 0.28 * panel_height[..., None]) * upper_weight[..., None]
    paint += fold_body[..., None] * panel_color * 0.34
    film_color = (
        cyan_cast[..., None] * np.asarray((0.020, 0.36, 0.52), np.float32)
        + magenta_cast[..., None] * np.asarray((0.52, 0.020, 0.37), np.float32)
        + cast_overlap[..., None] * np.asarray((0.35, 0.08, 0.52), np.float32)
    )
    paint += film_color * (0.085 * smoked_film + 0.13 * film_pool + 0.060 * film_lamella)[..., None]
    paint += np.asarray((0.78, 0.90, 1.00), np.float32) * (0.105 * film_lip)[..., None]
    paint += fold_lip[..., None] * np.asarray((0.20, 0.33, 0.44), np.float32) * (
        0.36 + 0.64 * cast_energy[..., None]
    )
    paint += panel_ribs[..., None] * panel_color * 0.26
    paint += upper_reflection[..., None] * (
        cyan_cast[..., None] * np.asarray((0.035, 0.18, 0.25), np.float32)
        + magenta_cast[..., None] * np.asarray((0.22, 0.025, 0.17), np.float32)
    )
    paint += body_edge[..., None] * (
        np.asarray((0.08, 0.26, 0.35), np.float32) * cyan[..., None]
        + np.asarray((0.33, 0.05, 0.27), np.float32) * magenta[..., None]
    )
    paint += (cyan_rail + magenta_rail)[..., None] * np.asarray((0.66, 0.73, 0.70), np.float32)
    paint += diffusion[..., None] * (
        cyan[..., None] * np.asarray((0.02, 0.20, 0.25), np.float32)
        + magenta[..., None] * np.asarray((0.22, 0.02, 0.18), np.float32)
    )
    paint += road_echo[..., None] * np.asarray((0.06, 0.10, 0.14), np.float32)
    paint += condensation[..., None] * np.asarray((0.07, 0.10, 0.14), np.float32)
    paint += chips[..., None] * np.asarray((0.44, 0.35, 0.48), np.float32)

    height = (
        0.34 * smoked_body + 0.24 * (cyan + magenta) + 0.18 * body_edge
        + 0.18 * panel_height + 0.20 * fold_body + 0.11 * road_echo
        + 0.08 * upper_reflection + 0.13 * film_pool + 0.10 * film_lip
        + 0.07 * film_lamella
    )
    left_light = smooth(-0.18, 0.62, normal_light(height, (-0.70, 0.04, 0.71)))
    right_light = smooth(-0.18, 0.62, normal_light(height, (0.70, 0.04, 0.71)))
    paint_b = ground.copy()
    paint_b += cyan[..., None] * np.asarray((0.015, 0.47, 0.95), np.float32) * (0.46 + 0.78 * left_light[..., None])
    paint_b += magenta[..., None] * np.asarray((0.94, 0.025, 0.42), np.float32) * (0.46 + 0.78 * right_light[..., None])
    paint_b += overlap[..., None] * np.asarray((0.46, 0.08, 0.68), np.float32)
    paint_b *= (1.0 - 0.62 * smoked_body[..., None])
    paint_b += smoked_body[..., None] * np.asarray((0.035, 0.045, 0.073), np.float32)
    panel_color_b = (
        cyan_cast[..., None] * np.asarray((0.025, 0.22, 0.54), np.float32) * (0.38 + 0.76 * left_light[..., None])
        + magenta_cast[..., None] * np.asarray((0.54, 0.025, 0.20), np.float32) * (0.38 + 0.76 * right_light[..., None])
        + cast_overlap[..., None] * np.asarray((0.26, 0.055, 0.38), np.float32)
    )
    paint_b += panel_color_b * (0.38 + 0.29 * panel_height[..., None]) * upper_weight[..., None]
    paint_b += fold_body[..., None] * panel_color_b * 0.36
    film_color_b = (
        cyan_cast[..., None] * np.asarray((0.025, 0.29, 0.63), np.float32)
        + magenta_cast[..., None] * np.asarray((0.63, 0.025, 0.27), np.float32)
        + cast_overlap[..., None] * np.asarray((0.43, 0.10, 0.62), np.float32)
    )
    paint_b += film_color_b * (0.095 * smoked_film + 0.15 * film_pool + 0.055 * film_lamella)[..., None]
    paint_b += np.asarray((0.86, 0.92, 1.00), np.float32) * (0.095 * film_lip)[..., None]
    paint_b += fold_lip[..., None] * np.asarray((0.30, 0.39, 0.52), np.float32) * (
        0.30 + 0.42 * (left_light + right_light)[..., None]
    )
    paint_b += panel_ribs[..., None] * panel_color_b * 0.27
    paint_b += upper_reflection[..., None] * (
        cyan_cast[..., None] * np.asarray((0.035, 0.14, 0.32), np.float32)
        + magenta_cast[..., None] * np.asarray((0.31, 0.028, 0.13), np.float32)
    )
    paint_b += body_edge[..., None] * np.asarray((0.23, 0.23, 0.34), np.float32) * (0.52 + 0.52 * (left_light + right_light)[..., None])
    paint_b += (cyan_rail + magenta_rail + 0.55 * chips)[..., None] * np.asarray((0.62, 0.70, 0.72), np.float32)
    paint_b += (0.55 * diffusion + road_echo + 0.65 * condensation)[..., None] * np.asarray((0.07, 0.11, 0.15), np.float32)

    metal = np.clip(
        0.04 + 0.71 * (cyan_rail + magenta_rail) + 0.43 * body_edge
        + 0.48 * fold_lip + 0.31 * upper_reflection + 0.24 * panel_ribs
        + 0.36 * chips + 0.10 * diffusion + 0.18 * film_lip + 0.12 * film_lamella,
        0.0, 1.0,
    )
    rough = np.clip(
        0.52 - 0.39 * (cyan + magenta) - 0.20 * cast_energy
        + 0.28 * (1.0 - panel_height) + 0.32 * panel_ribs + 0.27 * fold_lip
        + 0.31 * road_echo + 0.36 * condensation + 0.25 * chips + 0.12 * road
        + 0.20 * film_slope + 0.16 * film_lamella,
        0.0, 1.0,
    )
    coat = np.clip(
        0.15 + 0.46 * smoked_body + 0.45 * (cyan + magenta) + 0.24 * overlap
        + 0.37 * cast_energy + 0.28 * panel_height + 0.19 * fold_body
        + 0.22 * film_pool + 0.18 * film_lip - 0.36 * fold_lip - 0.35 * chips
        - 0.27 * condensation - 0.12 * film_lamella,
        0.0, 1.0,
    )
    # Smoked optical clear lives high in the physical coat envelope. Fixed
    # high-clear thresholds retain its panel/fold distinctions without forcing
    # equal populations or introducing an unrelated variance field.
    spec = pack_physical(
        metal, rough, coat,
        c_cuts=(0.36, 0.42, 0.48, 0.54, 0.61, 0.68, 0.75, 0.82, 0.90),
    )

    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one full-field smoked panel skin carrying opposed cyan and magenta ground-light basins through folds, a deformed optical clear film and wet reflections",
        {
            "M": "emitter housings, body lips, panel-fold lips, film order lips and reflection rails expose conductive edges",
            "R": "strained film lamellae, panel ribs, wet-road echoes, condensation and damaged housing chips interrupt smooth cast light",
            "Cc": "full-field smoked panels, mid-depth film pools, fold shoulders and broad underglow basins hold clear between ruptures",
        },
    )
