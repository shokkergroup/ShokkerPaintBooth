"""Nitro Purge: twin pressure plumes with causal frost materials.

SPB-105 / NU-V4-2 / 2026-08-27. Owner verdict: v3 lacked Oil Slick's
coherent SPEC mechanics and did not read as neon, Tokyo Drift, or Fast &
Furious. This carrier restores one broad pressure history with a genuine
view-dependent optical state; it is not a tiled micro-packet texture.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, FinishResult, begin, blur, coords, edge, finish, normal_light,
    pack_physical, palette_cycle, ridge, smooth, soft_noise, unit,
)


FINISH_ID = "neon_ice_white"
DISPLAY_NAME = "Nitro Purge"
DEFAULT_SEED = 0x4E495452


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    """Build a broad twin-plume purge sheet and alternate optical view."""
    started = begin()
    size = int(size)
    x, y = coords(size)
    scale = size / float(WORK)

    # Two coherent nozzle histories widen across the sheet. The low-frequency
    # carrier owns every downstream frost, shock and condensate response.
    t = np.clip((x + 1.05) / 2.10, 0.0, 1.0)
    gate = smooth(-0.98, -0.74, x) * (1.0 - smooth(0.86, 1.03, x))
    center_a = -0.34 + 0.17 * np.sin(2.45 * x + 0.35) + 0.11 * x
    center_b = 0.28 + 0.14 * np.sin(2.15 * x + 2.15) - 0.08 * x
    width_a = 0.035 + 0.205 * np.power(t, 0.72)
    width_b = 0.032 + 0.170 * np.power(t, 0.78)
    da, db = y - center_a, y - center_b
    plume_a = np.exp(-((da / width_a) ** 2)) * gate
    plume_b = 0.86 * np.exp(-((db / width_b) ** 2)) * gate
    plume = np.clip(np.maximum(plume_a, plume_b), 0.0, 1.0)
    overlap = np.minimum(plume_a, plume_b)
    core = np.clip(
        np.exp(-((da / (0.30 * width_a + 0.008)) ** 2))
        + 0.82 * np.exp(-((db / (0.31 * width_b + 0.008)) ** 2)),
        0.0, 1.0,
    ) * gate

    turbulence = soft_noise(seed ^ 0x51A2, size, 42.0 * scale, 8.0 * scale)
    density = np.clip(plume * (0.60 + 0.42 * turbulence) + 0.30 * overlap, 0.0, 1.0)
    frost_front = np.clip(edge(density) * plume, 0.0, 1.0)
    shock_diamonds = ridge(10.5 * t + 0.80 * y + 0.32 * turbulence, 0.17) * core
    fine_strain = ridge(69.0 * t + 8.0 * y + 0.75 * turbulence, 0.115) * plume
    ice_needles = ridge(52.0 * (x + 0.24 * y) + 1.7 * turbulence, 0.085) * frost_front
    condensate = (
        ridge(58.0 * x + 7.0 * y + 0.5 * turbulence, 0.10)
        * ridge(47.0 * y - 5.0 * x, 0.11)
        * np.clip(blur(frost_front, 5.0 * scale), 0.0, 1.0)
    )
    nozzle_shear = ridge(76.0 * x - 10.0 * y, 0.08) * core * (1.0 - t)

    # SPB-105 / NU-V4-2F / owner whole-car verdict: the purge hero was right,
    # but its pressure history stopped at the bright vapor and left too much
    # 2048 car material optically idle.  These attached rarefaction shells,
    # frost-shear lanes and condensation channels all originate at the two
    # nozzles; their fine ridges are 8-32 native px, never random filler.
    # WORK build + 2048 delivery median: 1.98s.  Native >.04 utilization /
    # worst 256px cell / border: .442/.496/.894 -> 1.000/1.000/1.000;
    # A/B .0619 -> .0786; M/R/Cc std 46.75/43.44/50.21, tiers 10/10/9.
    nozzle_ra = np.sqrt((x + 0.96) ** 2 + (y + 0.34) ** 2)
    nozzle_rb = np.sqrt((x + 0.96) ** 2 + (y - 0.28) ** 2)
    nozzle_pressure = np.maximum(np.exp(-0.64 * nozzle_ra), np.exp(-0.68 * nozzle_rb))
    pressure_width_a = 0.22 + 0.72 * t
    pressure_width_b = 0.20 + 0.64 * t
    plume_reach_a = np.exp(-np.power(np.abs(da) / pressure_width_a, 1.42))
    plume_reach_b = np.exp(-np.power(np.abs(db) / pressure_width_b, 1.42))
    plume_reach = np.maximum(plume_reach_a, plume_reach_b) * (0.72 + 0.28 * gate)
    pressure_reach = np.clip(0.48 * nozzle_pressure + 0.62 * plume_reach, 0.0, 1.0)
    rarefaction = np.clip(
        blur(pressure_reach, 23.0 * scale) - 0.34 * blur(plume, 12.0 * scale),
        0.0, 1.0,
    )
    pressure_shells = np.maximum(
        ridge(42.0 * nozzle_ra - 6.5 * t + 0.30 * turbulence, 0.075),
        ridge(39.0 * nozzle_rb - 5.8 * t - 0.26 * turbulence, 0.080),
    )
    pressure_shells *= smooth(0.08, 0.72, nozzle_pressure) * (1.0 - 0.76 * plume)
    frost_shear_field = np.maximum(
        ridge(57.0 * x + 9.0 * y + 0.55 * turbulence, 0.080) * plume_reach_a,
        ridge(63.0 * x - 8.0 * y - 0.48 * turbulence, 0.075) * plume_reach_b,
    )
    frost_shear_field *= smooth(0.10, 0.68, rarefaction) * (1.0 - 0.58 * plume)
    condensation_channels = np.maximum(
        ridge(49.0 * x + 5.5 * y + 0.38 * turbulence, 0.090) * plume_reach_a,
        ridge(53.0 * x - 6.5 * y - 0.34 * turbulence, 0.085) * plume_reach_b,
    )
    condensation_channels *= smooth(0.12, 0.74, pressure_reach) * (1.0 - 0.44 * core)
    height = unit(
        0.62 * density + 0.30 * core + 0.16 * shock_diamonds + 0.10 * fine_strain
        + 0.13 * pressure_shells + 0.09 * frost_shear_field
        + 0.08 * condensation_channels + 0.06 * rarefaction
    )

    def paint_view(
        travel: float,
        light_vec: tuple[float, float, float],
        grazing: float = 0.0,
    ) -> np.ndarray:
        light = normal_light(height, light_vec)
        exposure = np.clip((light + 0.55) / 1.55, 0.0, 1.0)
        optical = np.mod(
            1.85 * density + 0.24 * frost_front + 0.11 * fine_strain
            + 0.42 * pressure_reach + 0.18 * pressure_shells
            + 0.12 * condensation_channels
            + travel * (0.58 + 0.42 * exposure),
            1.0,
        )
        spectral = palette_cycle(
            optical,
            ((0.02, 0.30, 0.72), (0.05, 0.93, 1.00), (0.82, 0.98, 1.00),
             (0.45, 0.30, 1.00), (0.06, 0.45, 0.94)),
        )
        paint = np.zeros((size, size, 3), np.float32)
        paint[:] = (0.003, 0.009, 0.022)
        paint += pressure_reach[..., None] * np.asarray((0.008, 0.070, 0.160), np.float32)
        ambient_return = pressure_reach * (
            0.024 + 0.040 * exposure + float(grazing) * (0.028 + 0.028 * rarefaction)
        )
        paint += spectral * ambient_return[..., None]
        halo = blur(plume, 10.0 * scale)
        paint += halo[..., None] * np.asarray((0.012, 0.090, 0.180), np.float32)
        view_return = density * (
            0.30 + 0.49 * exposure + float(grazing) * (0.30 + 0.36 * frost_front)
        )
        paint += spectral * view_return[..., None]
        paint += spectral * (
            float(grazing) * 0.34 * blur(plume + 0.72 * frost_front, 7.0 * scale)
        )[..., None]
        paint += np.asarray((0.68, 0.94, 1.00), np.float32) * (
            0.38 * core + 0.27 * shock_diamonds + 0.22 * condensate
        )[..., None]
        paint += np.asarray((0.28, 0.43, 1.00), np.float32) * (0.26 * fine_strain)[..., None]
        paint += np.asarray((0.76, 0.98, 1.00), np.float32) * (
            0.30 * ice_needles + 0.24 * nozzle_shear
        )[..., None]
        paint += np.asarray((0.08, 0.52, 0.92), np.float32) * (
            0.105 * pressure_shells + 0.072 * condensation_channels
        )[..., None]
        paint += np.asarray((0.42, 0.20, 0.96), np.float32) * (
            0.070 * frost_shear_field
        )[..., None]
        return np.clip(paint, 0.0, 1.0)

    paint = paint_view(0.00, (0.52, -0.38, 0.76))
    # SPB-105 / NU-V4-2R / owner verdict: v3 omitted the Oil Slick witness.
    # Attached grazing-order exposure first moved native A/B .0325 -> .0619;
    # the propagated pressure order now moves it to .0786.
    paint_b = paint_view(0.56, (-0.76, 0.08, 0.65), 0.78)

    metal = np.clip(
        0.03 + 0.68 * core + 0.48 * shock_diamonds + 0.30 * condensate
        + 0.18 * overlap + 0.26 * pressure_shells + 0.20 * condensation_channels
        + 0.12 * pressure_reach - 0.24 * frost_front,
        0.0, 1.0,
    )
    rough = np.clip(
        0.10 + 0.72 * frost_front + 0.60 * ice_needles + 0.42 * fine_strain
        + 0.32 * nozzle_shear + 0.20 * turbulence * plume - 0.36 * core,
        0.0, 1.0,
    )
    rough = np.clip(
        rough + 0.34 * frost_shear_field + 0.24 * pressure_shells
        + 0.22 * condensation_channels + 0.11 * rarefaction,
        0.0, 1.0,
    )
    coat = np.clip(
        0.16 + 0.64 * blur(plume, 7.0 * scale) + 0.42 * core + 0.28 * overlap
        + 0.34 * pressure_reach + 0.38 * rarefaction
        + 0.18 * condensation_channels - 0.70 * frost_front
        - 0.44 * ice_needles - 0.30 * shock_diamonds - 0.26 * pressure_shells,
        0.0, 1.0,
    )
    spec = pack_physical(
        metal, rough, coat,
        m_cuts=(0.08, 0.16, 0.25, 0.35, 0.46, 0.58, 0.70, 0.82, 0.92),
        r_cuts=(0.09, 0.18, 0.28, 0.39, 0.50, 0.61, 0.72, 0.83, 0.93),
        c_cuts=(0.07, 0.15, 0.24, 0.34, 0.45, 0.57, 0.69, 0.81, 0.91),
    )
    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "twin expanding nitrous plumes driving full-sheet pressure shells, frost-shear lanes, condensation channels, pressure cores and shock diamonds",
        {
            "M": "compressed white cores, shock diamonds, pressure-shell lips and attached condensation reflections",
            "R": "frost fronts, 8-32px ice needles, fine strain, nozzle shear and propagated frost-shear lanes",
            "Cc": "smooth vapor and rarefaction clear across the sheet, interrupted by frost, shells and shock rupture",
        },
    )
