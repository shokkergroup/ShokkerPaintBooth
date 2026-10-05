"""Redline Rush — escalating heat corridors and speed-pressure anatomy.

SPB-105 / NU-V4 tick 5 / 2026-08-27. This is not a palette swap of the v3
carrier: it owns broad acceleration wedges, hot lips, fine turbine lamellae,
pressure dashes, carbon pores and order-jump glints.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, coords, edge, finish, normal_light, pack_physical,
    palette_ramp, ridge, smooth, soft_noise, unit, warp_vortices,
)


ID = "neon_red_alert"
NAME = "Redline Rush"
RED_A = ((4, 2, 8), (35, 2, 14), (105, 3, 23), (235, 9, 41),
         (255, 62, 23), (255, 169, 50), (255, 246, 209))
RED_B = ((3, 2, 9), (22, 4, 59), (104, 5, 135), (255, 12, 164),
         (255, 80, 59), (66, 226, 255), (229, 253, 255))


def build(seed: int = 4409, size: int = WORK):
    started = begin()
    x, y = coords(size)
    qx, qy = warp_vortices(x, y, (
        (-0.73, -0.55, 0.74, 0.55), (0.02, -0.06, 0.82, -0.51),
        (0.68, 0.51, 0.72, 0.47),
    ))
    sweep = qy - (0.25 * np.sin(2.35 * qx - 0.4) + 0.22 * qx - 0.08)
    sweep2 = qy + 0.52 - (0.17 * np.sin(2.8 * qx + 0.9) - 0.10 * qx)
    corridor = np.exp(-((sweep / 0.23) ** 2))
    return_band = 0.72 * np.exp(-((sweep2 / 0.13) ** 2))
    surge = np.clip(corridor + return_band, 0.0, 1.0)
    progression = smooth(-0.88, 0.88, qx + 0.10 * np.sin(3.4 * qy))

    # SPB-105 / NU-V4 tick 5R / owner 2048 whole-car contact 2026-08-27:
    # retain the redline hero, but make the entire substrate intentional. The
    # cross-ply and compression echoes share the same warped acceleration frame;
    # they are continuous engineered carbon anatomy, never confetti/noise filler.
    carbon_warp = ridge(
        qx * 76.0 + qy * 29.0 + 0.72 * np.sin(4.2 * sweep), 0.058,
    )
    carbon_weft = ridge(
        qx * 71.0 - qy * 34.0 - 0.63 * np.sin(3.7 * sweep2), 0.058,
    )
    cross_ply = np.clip(0.62 * carbon_warp + 0.54 * carbon_weft, 0.0, 1.0)
    compression_echo = ridge(
        sweep * 8.6 + 0.32 * progression + 0.16 * np.sin(5.0 * qx), 0.078,
    ) * (0.30 + 0.70 * (1.0 - surge))
    heat = unit(0.11 + 0.55 * surge + 0.38 * progression * corridor
                + 0.11 * np.sin(6.4 * qx + 3.2 * qy)
                + 0.045 * cross_ply + 0.055 * compression_echo)
    lip = np.clip(np.exp(-((np.abs(sweep) - 0.205) / 0.026) ** 2)
                  + 0.70 * np.exp(-((np.abs(sweep2) - 0.115) / 0.020) ** 2), 0.0, 1.0)
    turbine_lamella = ridge(qx * (78.0 + 18.0 * progression) + qy * 17.0
                            + 1.4 * np.sin(5.0 * qy), 0.060) * surge
    dash_gate = smooth(0.54, 0.82, soft_noise(seed + 17, size, size * 0.022, size * 0.0043))
    pressure_dash = ridge(qx * 53.0 - qy * 7.0, 0.055) * dash_gate * (0.35 + 0.65 * surge)
    pore_field = soft_noise(seed + 23, size, size * 0.010, size * 0.0042)
    carbon_pore = smooth(0.76, 0.92, pore_field) * (1.0 - 0.70 * surge)
    fracture = smooth(0.56, 0.82, edge(heat + 0.14 * turbine_lamella)) * (0.3 + 0.7 * surge)
    spectral = np.mod(1.64 * heat + 0.22 * progression + 0.10 * turbine_lamella, 1.0)
    order_jump = ridge(spectral, 0.050) * surge

    def render(angle_b: bool) -> np.ndarray:
        height = heat + 0.12 * turbine_lamella + 0.08 * lip
        height += 0.045 * cross_ply + 0.050 * compression_echo
        light = normal_light(height, (-0.58, 0.32, 0.75) if angle_b else (0.55, -0.37, 0.74))
        exposure = np.clip(0.68 * heat + 0.36 * progression * surge
                           + 0.24 * lip + 0.14 * order_jump + 0.12 * np.maximum(light, 0), 0, 1)
        color = palette_ramp(np.clip(exposure + (0.08 * light if angle_b else 0.0), 0, 1),
                             RED_B if angle_b else RED_A)
        carbon = np.stack((0.013 + 0.045 * heat, 0.006 + 0.012 * heat,
                           0.014 + 0.024 * heat), axis=2)
        carbon += np.stack((0.050 * compression_echo + 0.024 * cross_ply,
                            0.006 * cross_ply,
                            0.031 * cross_ply + 0.022 * compression_echo), axis=2)
        energy = np.clip(0.13 + 0.70 * surge + 0.31 * lip + 0.15 * turbine_lamella
                         + 0.18 * pressure_dash + 0.13 * fracture + 0.17 * order_jump
                         + 0.085 * cross_ply + 0.115 * compression_echo
                         - 0.24 * carbon_pore, 0.0, 1.12)
        return np.clip(carbon + color * energy[..., None], 0.0, 1.0)

    metal = unit(0.39 * (1.0 - heat) + 0.28 * lip + 0.19 * fracture
                 + 0.16 * pressure_dash + 0.11 * carbon_pore
                 + 0.11 * cross_ply + 0.09 * compression_echo)
    rough = unit(0.28 * edge(heat) + 0.24 * turbine_lamella + 0.22 * fracture
                 + 0.18 * carbon_pore + 0.15 * pressure_dash
                 + 0.21 * cross_ply + 0.13 * compression_echo)
    coat = unit(0.41 * np.exp(-((heat - 0.60) / 0.24) ** 2)
                + 0.31 * order_jump + 0.21 * surge + 0.15 * lip
                + 0.12 * compression_echo - 0.16 * cross_ply - 0.21 * fracture)
    return finish(started, ID, NAME, render(False), render(True), pack_physical(metal, rough, coat),
                  "two acceleration corridors over a full-field warped carbon and compression-pressure sheet",
                  {"M": "cool substrate, hot lips, fractures and dash inclusions",
                   "R": "turbine lamellae, carbon pores and acceleration strain",
                   "Cc": "mid-heat varnish pools and optical-order glints"})
