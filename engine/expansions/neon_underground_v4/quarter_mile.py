"""Quarter Mile — staging pulses feeding a perspective launch corridor.

SPB-105 / NU-V4 tick 6 / 2026-08-27. The v3 group had no tuner-racing
read. This finish builds one wet launch history from staging pools, lane lips,
fine traction checks, rubber stitches, spray beads and optical-order breaks.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, edge, finish, normal_light, pack_physical,
    palette_ramp, ridge, smooth, soft_noise, unit,
)


ID = "neon2_quarter_mile_weave"
NAME = "Quarter Mile"
STRIP_A = ((2, 4, 10), (15, 18, 24), (100, 43, 3), (255, 130, 4),
           (255, 225, 57), (130, 255, 38), (224, 255, 213))
STRIP_B = ((2, 4, 11), (8, 27, 40), (0, 121, 127), (0, 244, 215),
           (225, 255, 52), (255, 109, 12), (255, 232, 206))


def build(seed: int = 4513, size: int = WORK):
    started = begin()
    x, y = coords(size)
    depth = np.clip((y + 1.0) * 0.5, 0.0, 1.0)
    lane_curve = -0.04 + 0.12 * np.sin(2.05 * y - 0.5) * (0.28 + 0.72 * depth)
    lane_width = 0.12 + 0.53 * depth
    lane_d = np.abs(x - lane_curve) / lane_width
    corridor = 1.0 - smooth(0.72, 1.04, lane_d)
    shoulder = np.exp(-((lane_d - 0.88) / 0.095) ** 2)
    center_charge = np.exp(-((lane_d / 0.62) ** 2)) * corridor

    # SPB-105 / NU-V4 tick 6R / owner 2048 whole-car contact 2026-08-27:
    # the launch corridor had a strong hero but left the shoulders functionally
    # empty. These are coherent strip-surface histories, not filler particles:
    # perspective grooves, transverse traction cuts and runoff drainage remain
    # addressable anywhere a car UV samples the material.
    perspective_x = (x - lane_curve) / (0.24 + 0.76 * depth)
    surface_groove = ridge(
        perspective_x * 58.0 + y * 4.2 + 0.55 * np.sin(5.1 * y), 0.060,
    )
    traction_cut = ridge(
        y * (78.0 - 24.0 * depth) + 0.65 * np.sin(8.0 * perspective_x), 0.052,
    )
    strip_lamella = np.clip(0.72 * surface_groove + 0.46 * traction_cut, 0.0, 1.0)
    drainage = ridge(
        lane_d * (17.0 + 5.0 * depth) + y * 2.7, 0.068,
    ) * smooth(0.72, 1.55, lane_d)
    runoff_wash = smooth(0.74, 1.62, lane_d) * (
        0.54 + 0.46 * (0.5 + 0.5 * np.sin(3.3 * y - 1.6 * x))
    )

    # Unequal stage pulses accelerate toward the foreground; they are physical
    # energy pools, not a literal traffic-light illustration.
    pulses = np.zeros_like(x)
    for cy, amp, spread in ((-0.67, 0.62, 0.12), (-0.39, 0.78, 0.14),
                            (-0.07, 0.92, 0.17), (0.31, 1.00, 0.22), (0.72, 0.73, 0.29)):
        local_width = 0.18 + 0.28 * ((cy + 1.0) * 0.5)
        pulses += amp * np.exp(-(((y - cy) / spread) ** 2 + ((x - lane_curve) / local_width) ** 2))
    pulses = unit(pulses)
    launch_flow = unit(0.44 * corridor + 0.39 * pulses + 0.22 * depth
                       + 0.08 * np.sin(7.3 * y + 2.4 * x))
    lane_lip = shoulder * (0.45 + 0.55 * pulses)
    traction_checks = (ridge((x / lane_width) * 62.0 + 0.4 * np.sin(6.0 * y), 0.075)
                       * ridge(y * 54.0 + 0.3 * np.sin(8.0 * x), 0.085))
    check_gate = smooth(0.50, 0.79, soft_noise(seed + 3, size, size * 0.026, size * 0.0044))
    traction_checks *= corridor * check_gate
    rubber_stitch = ridge(y * (91.0 - 18.0 * depth) + x * 9.0, 0.055) * center_charge
    spray_field = soft_noise(seed + 21, size, size * 0.013, size * 0.0040)
    spray_bead = smooth(0.75, 0.91, spray_field) * (0.25 + 0.75 * corridor)
    launch_tear = smooth(0.55, 0.82, edge(launch_flow + 0.13 * traction_checks)) * corridor
    thickness = unit(0.19 + 0.52 * launch_flow + 0.17 * pulses + 0.10 * center_charge
                     - 0.09 * traction_checks + 0.06 * spray_bead
                     + 0.055 * strip_lamella - 0.045 * drainage)
    spectral = np.mod(1.71 * thickness + 0.22 * depth + 0.18 * pulses, 1.0)
    order_jump = ridge(spectral, 0.050) * corridor

    def render(angle_b: bool) -> np.ndarray:
        light = normal_light(thickness + 0.14 * lane_lip - 0.07 * traction_checks
                             + 0.045 * strip_lamella - 0.035 * drainage,
                             (-0.54, 0.34, 0.76) if angle_b else (0.48, -0.44, 0.75))
        energy_order = np.clip(0.53 * launch_flow + 0.39 * pulses + 0.28 * depth
                               + 0.15 * order_jump + (0.08 * light if angle_b else 0.0), 0, 1)
        color = palette_ramp(energy_order, STRIP_B if angle_b else STRIP_A)
        wet_black = np.stack((0.009 + 0.032 * launch_flow,
                              0.012 + 0.025 * launch_flow,
                              0.020 + 0.040 * launch_flow), axis=2)
        surface_tint = np.stack((0.025 * drainage + 0.010 * strip_lamella + 0.018 * runoff_wash,
                                 0.030 * strip_lamella + 0.018 * drainage + 0.028 * runoff_wash,
                                 0.070 * strip_lamella + 0.045 * drainage + 0.074 * runoff_wash), axis=2)
        emission = np.clip(0.10 + 0.48 * corridor + 0.44 * pulses + 0.28 * lane_lip
                           + 0.17 * traction_checks + 0.16 * rubber_stitch
                           + 0.24 * spray_bead + 0.14 * launch_tear + 0.17 * order_jump
                           + 0.075 * strip_lamella + 0.065 * drainage
                           + 0.12 * np.maximum(light, 0.0), 0.0, 1.13)
        return np.clip(wet_black + surface_tint + color * emission[..., None], 0.0, 1.0)

    metal = unit(0.41 * (1.0 - thickness) * corridor + 0.27 * lane_lip
                 + 0.20 * traction_checks + 0.15 * launch_tear + 0.12 * spray_bead
                 + 0.10 * drainage + 0.07 * strip_lamella + 0.06 * runoff_wash)
    rough = unit(0.29 * edge(thickness) + 0.24 * traction_checks + 0.21 * rubber_stitch
                 + 0.18 * launch_tear + 0.15 * spray_bead
                 + 0.19 * strip_lamella + 0.15 * drainage + 0.08 * runoff_wash)
    coat = unit(0.38 * launch_flow + 0.28 * pulses + 0.27 * order_jump
                + 0.17 * center_charge + 0.11 * drainage + 0.09 * runoff_wash
                - 0.16 * strip_lamella - 0.22 * traction_checks - 0.14 * launch_tear)
    # The strip is mostly mirror-wet, so its physically meaningful roughness
    # transitions occupy the low end. Fixed low-range cuts expose them without
    # equalizing populations or inventing a second texture carrier.
    spec = pack_physical(
        metal, rough, coat,
        r_cuts=(0.012, 0.027, 0.047, 0.075, 0.115, 0.175, 0.26, 0.40, 0.61),
    )
    return finish(started, ID, NAME, render(False), render(True), spec,
                  "staging-energy pools merging into a full-field wet perspective strip with traction and drainage history",
                  {"M": "exposed strip, charged lane lips and traction fragments",
                   "R": "micro-checks, rubber stitches, spray and launch tears",
                   "Cc": "wet launch flow and optical shoulders around pulse pools"})
