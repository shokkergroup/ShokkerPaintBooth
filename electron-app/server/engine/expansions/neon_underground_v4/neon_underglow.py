"""Neon Underglow — broad ground-light pressure moving through smoked paint.

SPB-105 / NU-V4 tick 2 / 2026-08-27. Owner verdict: v3 lacked Oil
Slick mechanics, neon presence, and Tokyo-Drift identity. This replacement
uses one advected film history for basin, lip, lamella, bead, order-jump and
shear anatomy; fixed physical thresholds drive its independent M/R/Cc maps.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, edge, finish, normal_light, pack_physical,
    palette_cycle, ridge, smooth, soft_noise, unit, warp_vortices,
)


ID = "neon_electric_blue"
NAME = "Neon Underglow"

PALETTE_A = ((1, 5, 18), (0, 58, 96), (0, 224, 255), (199, 255, 255),
             (255, 38, 206), (112, 17, 255), (1, 20, 53))
PALETTE_B = ((2, 3, 12), (65, 7, 112), (255, 32, 191), (255, 225, 249),
             (0, 239, 255), (0, 91, 153), (3, 14, 31))


def build(seed: int = 4101, size: int = WORK):
    started = begin()
    x, y = coords(size)
    qx, qy = warp_vortices(x, y, (
        (-0.72, -0.42, 0.72, 0.72), (0.05, -0.55, 0.52, -0.83),
        (0.64, -0.05, 0.66, 0.74), (-0.36, 0.37, 0.58, -0.69),
        (0.58, 0.69, 0.48, 0.64),
    ))
    qx = qx + 0.055 * np.sin(8.7 * qy + 1.4 * np.sin(3.1 * qx))
    qy = qy + 0.043 * np.sin(7.2 * qx - 1.1 * np.sin(4.7 * qy))

    center_a = -0.34 + 0.16 * np.sin(2.45 * qx + 0.5) + 0.055 * np.sin(7.2 * qx)
    center_b = 0.43 - 0.13 * np.sin(2.15 * qx - 0.8)
    da, db = qy - center_a, qy - center_b
    lower = np.exp(-((da / 0.25) ** 2))
    upper = np.exp(-((db / 0.16) ** 2))
    basin = np.clip(lower + 0.62 * upper, 0.0, 1.0)
    lip = np.clip(
        np.exp(-((np.abs(da) - 0.21) / 0.035) ** 2)
        + 0.72 * np.exp(-((np.abs(db) - 0.13) / 0.027) ** 2), 0.0, 1.0,
    )
    thickness = unit(
        0.48 + 0.20 * qx - 0.13 * qy + 0.22 * lower - 0.12 * upper
        + 0.075 * np.sin(7.4 * qx + 3.1 * qy)
        + 0.042 * np.sin(14.7 * qy - 5.3 * qx)
    )
    slope = edge(thickness)
    shoulder = smooth(0.30, 0.74, slope) * (0.35 + 0.65 * basin)
    lamella = ridge(qx * (72.0 + 15.0 * thickness) + qy * 23.0, 0.075) * basin
    condensation = soft_noise(seed + 7, size, size * 0.035, size * 0.0045)
    beads = smooth(0.73, 0.89, condensation) * smooth(0.18, 0.82, basin)
    shear = smooth(0.48, 0.78, edge(qx + 0.23 * np.sin(9.0 * qy))) * lip
    spectral = np.mod(2.75 * thickness + 0.16 * slope + 0.11 * lamella, 1.0)
    order_jump = ridge(spectral, 0.052) * (0.38 + 0.62 * basin)

    def render(angle_b: bool) -> np.ndarray:
        palette = PALETTE_B if angle_b else PALETTE_A
        travel = 0.29 if angle_b else 0.0
        light = normal_light(thickness + 0.18 * basin + 0.06 * lamella,
                             (-0.58, 0.34, 0.74) if angle_b else (0.53, -0.42, 0.72))
        color = palette_cycle(spectral + travel + (0.04 * light), palette)
        smoked = np.stack((0.008 + 0.016 * thickness,
                           0.012 + 0.030 * thickness,
                           0.026 + 0.055 * thickness), axis=2)
        emission = np.clip(0.13 + 0.64 * basin + 0.40 * lip + 0.20 * order_jump
                           + 0.14 * lamella + 0.18 * beads + 0.13 * shear
                           + 0.17 * np.maximum(light, 0.0), 0.0, 1.18)
        veil = smooth(0.02, 0.82, basin + 0.55 * lip)[..., None]
        return np.clip(smoked * (1.0 - 0.56 * veil) + color * emission[..., None], 0.0, 1.0)

    paint = render(False)
    paint_b = render(True)
    dry_exposure = np.clip(1.0 - thickness, 0.0, 1.0) * (0.35 + 0.65 * shoulder)
    pooled_coat = np.exp(-((thickness - 0.57) / 0.22) ** 2) * (1.0 - 0.55 * slope)
    metal = unit(0.45 * dry_exposure + 0.27 * lip + 0.18 * order_jump + 0.20 * shear + 0.12 * beads)
    rough = unit(0.34 * slope + 0.25 * lamella + 0.19 * shear + 0.18 * beads + 0.12 * dry_exposure)
    coat = unit(0.43 * pooled_coat + 0.32 * order_jump + 0.20 * basin + 0.16 * lip - 0.18 * shear)
    spec = pack_physical(metal, rough, coat)
    return finish(started, ID, NAME, paint, paint_b, spec,
                  "two coherent underbody light basins advected through one smoked interference sheet",
                  {"M": "dry substrate, charged lips, order ruptures and bead metal",
                   "R": "sheet strain, fine lamellae, shear and condensation",
                   "Cc": "mid-depth wet pools with optical-order shoulders"})

