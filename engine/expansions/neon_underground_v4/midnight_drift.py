"""Midnight Drift — curved tire-light, backlit smoke, and ember wake.

SPB-105 / NU-V4 tick 3 / 2026-08-27. Replaces the rejected v3 dark
microtexture with a coherent drift event. Fine grooves, smoke wisps, hot lips,
rubber tears and sparks are all attached to the same curved pressure history.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, edge, finish, normal_light, pack_physical,
    palette_cycle, ridge, smooth, soft_noise, unit, warp_vortices,
)


ID = "neon2_splatter"
NAME = "Midnight Drift"
DRIFT_A = ((2, 3, 10), (15, 8, 39), (73, 17, 121), (255, 23, 139),
           (255, 102, 54), (255, 225, 173), (0, 205, 255), (4, 25, 54))
DRIFT_B = ((2, 4, 9), (0, 45, 73), (0, 220, 255), (217, 250, 255),
           (255, 55, 190), (151, 21, 255), (255, 90, 32), (22, 6, 30))


def build(seed: int = 4203, size: int = WORK):
    started = begin()
    x, y = coords(size)
    qx, qy = warp_vortices(x, y, (
        (-0.88, 0.08, 1.12, 0.63), (0.56, -0.18, 0.84, -0.74),
        (0.23, 0.73, 0.58, 0.54),
    ))
    r1 = np.sqrt((qx + 0.72) ** 2 + (qy - 0.05) ** 2)
    a1 = np.arctan2(qy - 0.05, qx + 0.72)
    r2 = np.sqrt((qx - 0.62) ** 2 + (qy + 0.18) ** 2)
    a2 = np.arctan2(qy + 0.18, qx - 0.62)
    arc1 = np.exp(-((r1 - (0.74 + 0.055 * np.sin(2.7 * a1))) / 0.105) ** 2)
    arc2 = np.exp(-((r2 - (0.69 + 0.043 * np.sin(3.2 * a2))) / 0.082) ** 2)
    track = np.clip(arc1 + 0.85 * arc2, 0.0, 1.0)

    # SPB-105 / NU-V4 tick 3R / owner 2048 whole-car contact 2026-08-27:
    # the hero arcs remain, while the entire road film now carries banked
    # pressure combs and crossing airflow. Both are analytic continuations of
    # the same two drift centres—not random grit, particles or distress filler.
    banked_comb_a = ridge(
        r1 * 61.0 + 0.82 * np.sin(3.4 * a1) + 0.22 * a1, 0.058,
    )
    banked_comb_b = ridge(
        r2 * 73.0 - 0.67 * np.sin(3.1 * a2) - 0.19 * a2, 0.055,
    )
    road_comb = np.clip(0.62 * banked_comb_a + 0.50 * banked_comb_b, 0.0, 1.0)
    airflow = ridge(
        qx * 67.0 + qy * 21.0 + 1.15 * np.sin(2.8 * a1 - 1.9 * a2), 0.052,
    )
    smoke_source = blur(track, size * 0.045)
    smoke_noise = soft_noise(seed + 11, size, size * 0.075, size * 0.005)
    smoke = unit(0.68 * smoke_source + 0.23 * smoke_noise
                 + 0.10 * np.sin(3.4 * qx - 2.1 * qy))
    smoke *= smooth(0.08, 0.75, blur(track, size * 0.095))
    hot_lip = np.clip(
        np.exp(-((np.abs(r1 - 0.74) - 0.085) / 0.018) ** 2)
        + np.exp(-((np.abs(r2 - 0.69) - 0.065) / 0.016) ** 2), 0.0, 1.0,
    )
    groove = np.clip(ridge((r1 - 0.74) * 92.0 + 0.8 * np.sin(4.0 * a1), 0.070) * arc1
                     + ridge((r2 - 0.69) * 106.0 - 0.7 * np.sin(3.0 * a2), 0.065) * arc2, 0.0, 1.0)
    turbulence = unit(smoke + 0.21 * np.sin(8.1 * qx + 4.3 * qy)
                      + 0.10 * np.sin(17.0 * qy - 6.2 * qx))
    wisp = ridge(turbulence * 5.8 + 0.18 * a1, 0.073) * smoke
    rubber_tear = smooth(0.63, 0.86, edge(track + 0.17 * groove)) * track
    spark_field = soft_noise(seed + 31, size, size * 0.014, size * 0.0042)
    sparks = smooth(0.77, 0.91, spark_field) * smooth(0.16, 0.75, track + 0.65 * hot_lip)
    thickness = unit(0.18 + 0.46 * smoke + 0.29 * track + 0.12 * np.sin(3.0 * a1)
                     - 0.14 * hot_lip + 0.08 * wisp
                     + 0.045 * road_comb - 0.035 * airflow)
    strain = edge(thickness)
    spectral = np.mod(2.15 * thickness + 0.19 * turbulence + 0.13 * groove, 1.0)
    order_jump = ridge(spectral, 0.050) * (0.25 + 0.75 * (smoke + track).clip(0, 1))

    def render(angle_b: bool) -> np.ndarray:
        light = normal_light(thickness + 0.16 * groove + 0.045 * road_comb - 0.035 * airflow,
                             (-0.61, 0.28, 0.75) if angle_b else (0.48, -0.51, 0.71))
        color = palette_cycle(spectral + (0.33 if angle_b else 0.0), DRIFT_B if angle_b else DRIFT_A)
        base = np.stack((0.012 + 0.035 * smoke, 0.010 + 0.018 * smoke,
                         0.026 + 0.072 * smoke), axis=2)
        base += np.stack((0.035 * road_comb + 0.024 * airflow,
                          0.012 * road_comb + 0.025 * airflow,
                          0.052 * road_comb + 0.070 * airflow), axis=2)
        energy = np.clip(0.10 + 0.34 * smoke + 0.58 * track + 0.35 * hot_lip
                         + 0.16 * groove + 0.18 * wisp + 0.40 * sparks
                         + 0.085 * road_comb + 0.075 * airflow
                         + 0.19 * order_jump + 0.15 * np.maximum(light, 0.0), 0.0, 1.18)
        return np.clip(base + color * energy[..., None], 0.0, 1.0)

    metal = unit(0.42 * (1.0 - thickness) * track + 0.30 * hot_lip + 0.19 * rubber_tear
                 + 0.16 * sparks + 0.12 * order_jump
                 + 0.10 * road_comb + 0.08 * airflow)
    rough = unit(0.31 * smoke + 0.25 * strain + 0.22 * groove + 0.18 * rubber_tear
                 + 0.15 * wisp + 0.12 * sparks + 0.18 * road_comb + 0.14 * airflow)
    coat = unit(0.38 * np.exp(-((thickness - 0.57) / 0.23) ** 2)
                + 0.32 * order_jump + 0.18 * track + 0.16 * hot_lip
                + 0.10 * airflow - 0.14 * road_comb - 0.23 * rubber_tear)
    return finish(started, ID, NAME, render(False), render(True), pack_physical(metal, rough, coat),
                  "two interacting drift arcs continuing through a full-field banked road and airflow history",
                  {"M": "exposed rubber, heat lips, tears and embedded sparks",
                   "R": "smoke density, radial grooves, wisps and strain",
                   "Cc": "wet track film and optical shoulders interrupted by tears"})
