"""Boost Spool: compressor pressure winding into turbine heat.

SPB-105 / NU-V4-2 / 2026-08-27. Owner verdict: v3 lacked Oil Slick's
coherent SPEC mechanics and did not read as neon, Tokyo Drift, or Fast &
Furious. This is one continuous turbo-pressure carrier with a physical
alternate view, never a carpet of repeated fragments.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, FinishResult, begin, blur, coords, edge, finish, normal_light,
    pack_physical, palette_cycle, ridge, smooth, soft_noise, unit,
    warp_vortices,
)


FINISH_ID = "neon2_plasma_tubes"
DISPLAY_NAME = "Boost Spool"
DEFAULT_SEED = 0xB0057A40


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    """Build a broad compressor scroll and heat-cured turbine material."""
    started = begin()
    size = int(size)
    x, y = coords(size)
    scale = size / float(WORK)
    qx, qy = warp_vortices(
        x, y,
        ((-0.30, 0.02, 0.78, 1.12), (0.25, -0.10, 0.62, -0.58)),
    )
    dx, dy = qx + 0.28, qy - 0.01
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)

    scroll_radius = 0.39 + 0.075 * np.sin(theta - 0.35) + 0.035 * np.sin(3.0 * theta)
    compressor_scroll = np.exp(-(((radius - scroll_radius) / 0.145) ** 2))
    compressor_scroll *= 1.0 - smooth(0.88, 1.10, radius)
    inner_bowl = np.exp(-((radius / 0.31) ** 2))
    turbine_heat = np.exp(-(((radius - 0.24) / 0.115) ** 2)) * smooth(-0.15, 0.62, qx)

    tongue_center = -0.08 + 0.16 * np.sin(2.1 * (qx + 0.82))
    tongue_width = 0.10 + 0.09 * smooth(-1.0, 0.42, qx)
    intake_tongue = np.exp(-(((qy - tongue_center) / tongue_width) ** 2))
    intake_tongue *= 1.0 - smooth(0.35, 0.72, qx)
    pressure = np.clip(0.72 * compressor_scroll + 0.64 * intake_tongue + 0.28 * inner_bowl, 0.0, 1.0)

    texture = soft_noise(seed ^ 0x77D1, size, 48.0 * scale, 7.0 * scale)
    compression_lip = np.clip(edge(pressure) * (0.55 + 0.45 * pressure), 0.0, 1.0)
    blade_ripples = ridge(63.0 * radius + 4.5 * theta / np.pi + 0.8 * texture, 0.095) * inner_bowl
    scroll_strain = ridge(48.0 * radius + 2.2 * theta / np.pi, 0.10) * compressor_scroll
    clamp_ribs = ridge(58.0 * qx - 6.0 * qy + 0.5 * texture, 0.09) * intake_tongue
    oxide_scale = ridge(51.0 * (qx + 0.30 * qy) + 1.1 * texture, 0.105) * turbine_heat
    bov_wake_center = 0.23 - 0.62 * (qx - 0.12)
    bov_wake = np.exp(-(((qy - bov_wake_center) / 0.085) ** 2)) * smooth(0.06, 0.30, qx) * (1.0 - smooth(0.72, 1.0, qx))

    # SPB-105 / NU-V4-2F / owner whole-car verdict: retain the turbine-scroll
    # hero, but continue its compression and heat history through the 2048 car
    # sheet.  The outer scroll, intake vanes and wake shear below are attached
    # analytic flow—not random particles, scratches or brightness filler—and
    # their subordinate ridges resolve at 8-32 native px.
    # WORK build + 2048 delivery median: 1.76s.  Native >.04 utilization /
    # worst 256px cell / border: .424/.000/.130 -> 1.000/1.000/1.000;
    # A/B .0516 -> .0696; M/R/Cc std 70.68/52.12/62.08, tiers 10/10/9.
    pressure_atmosphere = np.exp(-0.62 * radius)
    spiral_radius = 0.50 + 0.18 * np.mod(theta + np.pi, 2.0 * np.pi) / (2.0 * np.pi)
    outer_scroll = np.exp(-(((radius - spiral_radius) / 0.34) ** 2))
    outer_scroll = np.clip(0.52 * outer_scroll + 0.48 * pressure_atmosphere, 0.0, 1.0)
    outer_scroll_ribs = ridge(
        67.0 * radius + 3.8 * theta / np.pi + 0.32 * texture, 0.078
    ) * smooth(0.12, 0.84, outer_scroll) * (1.0 - 0.58 * compressor_scroll)
    intake_field_center = -0.08 + 0.16 * np.sin(2.1 * (qx + 0.82))
    intake_field_width = 0.22 + 0.24 * smooth(-0.95, 1.0, qx)
    intake_field = np.exp(-(((qy - intake_field_center) / intake_field_width) ** 2))
    intake_field = np.clip(0.70 * intake_field + 0.30 * pressure_atmosphere, 0.0, 1.0)
    intake_vanes = ridge(
        58.0 * qx - 8.5 * qy + 0.42 * texture, 0.078
    ) * smooth(0.14, 0.82, intake_field) * (1.0 - 0.50 * inner_bowl)
    heat_wake_center = 0.06 + 0.20 * np.sin(1.75 * (qx + 0.12))
    heat_wake_width = 0.16 + 0.30 * smooth(-0.24, 1.02, qx)
    heat_wake = np.exp(-(((qy - heat_wake_center) / heat_wake_width) ** 2))
    heat_wake *= smooth(-0.34, 0.10, qx)
    heat_wake_shear = ridge(
        61.0 * qx + 7.0 * qy + 0.52 * texture, 0.082
    ) * heat_wake
    wake_pressure = np.clip(
        0.56 * pressure_atmosphere + 0.38 * intake_field + 0.32 * heat_wake,
        0.0, 1.0,
    )
    height = unit(
        0.55 * pressure + 0.38 * turbine_heat + 0.24 * compression_lip
        + 0.14 * blade_ripples + 0.10 * bov_wake + 0.10 * outer_scroll_ribs
        + 0.08 * intake_vanes + 0.08 * heat_wake_shear + 0.05 * wake_pressure
    )

    def paint_view(travel: float, light_vec: tuple[float, float, float]) -> np.ndarray:
        light = normal_light(height, light_vec)
        exposure = np.clip((light + 0.55) / 1.55, 0.0, 1.0)
        optical = np.mod(
            1.35 * pressure + 1.65 * turbine_heat + 0.18 * scroll_strain
            + 0.08 * theta / np.pi + 0.40 * wake_pressure
            + 0.18 * outer_scroll_ribs + 0.12 * heat_wake_shear
            + travel * (0.50 + 0.50 * exposure),
            1.0,
        )
        shift = palette_cycle(
            optical,
            ((0.00, 0.32, 0.63), (0.00, 0.96, 1.00), (0.82, 0.98, 1.00),
             (1.00, 0.34, 0.04), (1.00, 0.08, 0.38), (0.20, 0.16, 0.72)),
        )
        paint = np.zeros((size, size, 3), np.float32)
        paint[:] = (0.004, 0.009, 0.020)
        paint += pressure_atmosphere[..., None] * np.asarray((0.010, 0.052, 0.112), np.float32)
        field_return = wake_pressure * (0.026 + 0.060 * exposure)
        paint += shift * field_return[..., None]
        paint += blur(pressure, 11.0 * scale)[..., None] * np.asarray((0.00, 0.11, 0.17), np.float32)
        paint += shift * (pressure * (0.22 + 0.48 * exposure))[..., None]
        paint += np.asarray((1.00, 0.24, 0.025), np.float32) * (
            turbine_heat * (0.24 + 0.43 * exposure)
        )[..., None]
        paint += np.asarray((0.10, 0.88, 1.00), np.float32) * (0.34 * compression_lip + 0.22 * bov_wake)[..., None]
        paint += np.asarray((1.00, 0.74, 0.20), np.float32) * (0.27 * blade_ripples + 0.20 * oxide_scale)[..., None]
        paint += np.asarray((0.58, 0.18, 0.96), np.float32) * (0.20 * scroll_strain)[..., None]
        paint += np.asarray((0.85, 0.98, 1.00), np.float32) * (0.23 * clamp_ribs)[..., None]
        paint += np.asarray((0.02, 0.62, 0.96), np.float32) * (
            0.090 * outer_scroll_ribs + 0.070 * intake_vanes
        )[..., None]
        paint += np.asarray((1.00, 0.20, 0.055), np.float32) * (
            0.080 * heat_wake + 0.095 * heat_wake_shear
        )[..., None]
        return np.clip(paint, 0.0, 1.0)

    paint = paint_view(0.00, (0.50, -0.43, 0.75))
    paint_b = paint_view(0.28, (-0.61, 0.24, 0.75))

    metal = np.clip(
        0.08 + 0.70 * compressor_scroll + 0.78 * turbine_heat + 0.50 * blade_ripples
        + 0.32 * compression_lip + 0.25 * clamp_ribs + 0.24 * outer_scroll_ribs
        + 0.18 * intake_vanes + 0.16 * heat_wake_shear
        + 0.10 * pressure_atmosphere - 0.30 * bov_wake,
        0.0, 1.0,
    )
    # SPB-105 / NU-V4-2R / owner verdict: keep Oil Slick-grade material spread.
    # The first fixed-threshold pass left almost the whole untouched void in
    # one roughness tier. Pressure cure now supplies a broad physical ramp,
    # while oxide and strain still own the high tail; no quantiles are used.
    # Native R movement: std/tier 16.39/9 -> 41.78/10.
    rough = np.clip(
        0.025 + 0.40 * pressure + 0.68 * oxide_scale + 0.56 * scroll_strain
        + 0.42 * clamp_ribs + 0.32 * texture * turbine_heat
        + 0.28 * compression_lip + 0.32 * outer_scroll_ribs
        + 0.28 * heat_wake_shear + 0.18 * intake_vanes
        + 0.10 * wake_pressure - 0.30 * inner_bowl,
        0.0, 1.0,
    )
    coat = np.clip(
        0.14 + 0.68 * intake_tongue + 0.52 * inner_bowl + 0.34 * bov_wake
        + 0.24 * compressor_scroll + 0.38 * intake_field
        + 0.24 * pressure_atmosphere - 0.64 * oxide_scale
        - 0.36 * blade_ripples - 0.28 * heat_wake_shear
        - 0.20 * outer_scroll_ribs,
        0.0, 1.0,
    )
    spec = pack_physical(
        metal, rough, coat,
        m_cuts=(0.09, 0.18, 0.28, 0.38, 0.49, 0.60, 0.71, 0.82, 0.92),
        r_cuts=(0.08, 0.17, 0.27, 0.38, 0.49, 0.60, 0.71, 0.82, 0.92),
        c_cuts=(0.06, 0.14, 0.23, 0.33, 0.44, 0.56, 0.68, 0.80, 0.91),
    )
    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "continuous cyan intake pressure winding through a full-sheet compressor scroll into orange turbine heat, outer pressure ribs, intake vanes and wake shear",
        {
            "M": "compressor scroll, hot turbine metal, blade ripples, outer pressure ribs, intake vanes and clamp faces",
            "R": "heat oxide scale, strained scroll ribs, wake shear, vanes and compressed metal shoulders",
            "Cc": "smooth intake pressure and compressor atmosphere across the sheet, reduced at hot scale and rib shear",
        },
    )
