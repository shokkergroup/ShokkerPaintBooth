"""Carbon Voltage -- broad charged seams crossing edge-lit carbon resin."""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, finish, normal_light, pack_physical,
    palette_ramp, ridge, smooth, soft_noise, unit,
)


# SPB-105 / NU-V4-CARBON-VOLTAGE, 2026-08-27. Owner verdict: v3 lacked
# Oil Slick's coherent SPEC behavior and did not read as neon/Tokyo Drift.
# Two broad conductive fault seams own the silhouette; 8-32px warp tows,
# weft tows, crossover lips, resin valleys, delamination sparks and edge bloom
# are attached detail rather than the carrier itself.
FINISH_ID = "neon2_honeycomb"
DISPLAY_NAME = "Carbon Voltage"


def build(seed: int = 74203, size: int = WORK):
    started = begin()
    x, y = coords(size)
    resin = soft_noise(seed + 9, size, max(42.0, size / 16.0), max(4.0, size / 180.0))

    # Fine physical weave remains quiet until a light direction exposes it.
    weave_count = 86.0 * size / 1024.0
    warp = ridge(weave_count * (0.71 * x + 0.71 * y) + 0.75 * resin, 0.19)
    weft = ridge(weave_count * (0.71 * x - 0.71 * y) - 0.62 * resin + 0.5, 0.19)
    crossover = warp * weft
    tow_height = 0.55 * warp + 0.45 * weft + 0.30 * crossover

    seam_a_axis = y - (0.40 * np.sin(1.78 * x + 0.32) - 0.18 * x)
    seam_b_axis = x - (-0.47 * np.sin(1.42 * y - 0.86) + 0.24 * y + 0.20)
    seam_a = np.exp(-((seam_a_axis / 0.155) ** 4))
    seam_b = np.exp(-((seam_b_axis / 0.135) ** 4))
    charge = np.clip(seam_a + 0.92 * seam_b, 0.0, 1.0)
    core_a = np.exp(-((seam_a_axis / 0.018) ** 2))
    core_b = np.exp(-((seam_b_axis / 0.016) ** 2))
    bloom = np.clip(blur(charge, max(7.0, size / 120.0)) - 0.35 * charge, 0.0, 1.0)
    valley = np.clip((1.0 - warp) * (1.0 - weft), 0.0, 1.0)
    spark_gate = ridge(74.0 * (x - 0.28 * y) + 2.1 * resin, 0.050)
    delam_sparks = spark_gate * smooth(0.42, 0.82, charge) * smooth(0.60, 0.88, resin)

    base = palette_ramp(0.54 * resin + 0.24 * tow_height, (
        (0.010, 0.014, 0.026), (0.035, 0.050, 0.070),
        (0.075, 0.105, 0.125), (0.14, 0.16, 0.19),
    ))
    paint = base
    paint += (0.72 * warp + 0.35 * crossover)[..., None] * np.asarray((0.025, 0.075, 0.095), np.float32)
    paint += (0.62 * weft + 0.25 * crossover)[..., None] * np.asarray((0.055, 0.025, 0.095), np.float32)
    paint += seam_a[..., None] * np.asarray((0.018, 0.67, 0.83), np.float32)
    paint += seam_b[..., None] * np.asarray((0.58, 0.03, 0.84), np.float32)
    paint += (core_a + core_b)[..., None] * np.asarray((0.58, 0.73, 0.72), np.float32)
    paint += bloom[..., None] * np.asarray((0.08, 0.19, 0.36), np.float32)
    paint += delam_sparks[..., None] * np.asarray((0.70, 0.68, 0.36), np.float32)

    height = 0.30 * tow_height + 0.64 * charge + 0.14 * resin
    lit_cyan = smooth(-0.16, 0.62, normal_light(height, (-0.68, -0.12, 0.72)))
    lit_violet = smooth(-0.16, 0.62, normal_light(height, (0.62, 0.25, 0.74)))
    paint_b = palette_ramp(0.44 * resin + 0.34 * tow_height, (
        (0.009, 0.013, 0.025), (0.025, 0.052, 0.070),
        (0.082, 0.070, 0.13), (0.13, 0.15, 0.18),
    ))
    paint_b += warp[..., None] * np.asarray((0.025, 0.13, 0.16), np.float32) * (0.40 + 0.72 * lit_cyan[..., None])
    paint_b += weft[..., None] * np.asarray((0.13, 0.025, 0.18), np.float32) * (0.40 + 0.72 * lit_violet[..., None])
    paint_b += seam_a[..., None] * np.asarray((0.035, 0.55, 0.93), np.float32) * (0.48 + 0.72 * lit_cyan[..., None])
    paint_b += seam_b[..., None] * np.asarray((0.78, 0.05, 0.66), np.float32) * (0.48 + 0.70 * lit_violet[..., None])
    paint_b += (core_a + core_b + 0.55 * delam_sparks)[..., None] * np.asarray((0.55, 0.70, 0.70), np.float32)

    metal = np.clip(0.07 + 0.66 * (core_a + core_b) + 0.33 * charge + 0.22 * delam_sparks + 0.11 * crossover, 0.0, 1.0)
    rough = np.clip(0.27 + 0.48 * tow_height + 0.38 * valley + 0.31 * delam_sparks - 0.54 * charge, 0.0, 1.0)
    coat = np.clip(0.25 + 0.56 * resin + 0.27 * valley + 0.24 * charge - 0.42 * delam_sparks - 0.18 * crossover, 0.0, 1.0)
    spec = pack_physical(metal, rough, coat)

    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one edge-lit carbon-resin skin split by crossing cyan and violet conductive faults",
        {
            "M": "conductive fault cores, charged intersections and exposed tow crossovers",
            "R": "dry tow crowns, resin valleys and delamination sparks oppose polished seams",
            "Cc": "intact smoked resin spans broad weave territories but breaks at exposed fibers",
        },
    )
