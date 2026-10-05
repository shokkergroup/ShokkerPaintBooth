"""Laser Lane — decisive bundled beam corridors over wet graphite."""
from __future__ import annotations

import numpy as np

from .core import FinishResult, WORK, begin, blur, coords, finish, normal_light, pack_physical, resize_result, ridge, smooth, unit


FINISH_ID = "neon2_laser_web"
DISPLAY_NAME = "Laser Lane"
DEFAULT_SEED = 0x1A5E71

# SPB-105 / NU-V4-LL-1 / 2026-08-27 — owner verdict: v3 lacked Oil
# Slick mechanics, neon, and Tokyo Drift identity.  Four broad laser lanes now
# own the sheet; their 8–32px beam anatomy is detail, not a microtexture carpet.
# NU-V4 whole-car correction: lane-owned haze and interference planes now
# carry the dark graphite between hero beams; no dust or spark quota is used.


def _mix(paint: np.ndarray, color: tuple[float, float, float], amount: np.ndarray) -> np.ndarray:
    a = np.clip(amount, 0.0, 1.0)[..., None]
    c = np.asarray(color, np.float32)
    return paint * (1.0 - a) + c * a


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    started = begin()
    size = int(size)
    if size < 256:
        raise ValueError("Laser Lane requires size >= 256")
    if size > WORK:
        source = build(seed=seed, size=WORK)
        paint_a, paint_b, spec = resize_result(source, size)
        return finish(started, FINISH_ID, DISPLAY_NAME, paint_a, paint_b, spec, source.carrier, source.material_story)
    x, y = coords(size)

    # A few asymmetric corridors establish readable high-speed direction.
    rows = (
        (-0.68, 0.52, 0.12, 0.3, (1.00, 0.04, 0.24)),
        (-0.19, -0.33, -0.08, 1.6, (1.00, 0.10, 0.62)),
        (0.31, 0.41, 0.09, 3.0, (0.14, 0.94, 1.00)),
        (0.72, -0.48, -0.11, 4.4, (0.52, 0.20, 1.00)),
    )
    halo = np.zeros_like(x)
    cores = np.zeros_like(x)
    satellites = np.zeros_like(x)
    reflections = np.zeros_like(x)
    active_a = np.zeros_like(x)
    active_b = np.zeros_like(x)
    red = np.zeros_like(x)
    cyan = np.zeros_like(x)
    red_volume = np.zeros_like(x)
    cyan_volume = np.zeros_like(x)
    interference_plane = np.zeros_like(x)
    plane_lips = np.zeros_like(x)
    along = np.zeros_like(x)
    for i, (offset, slope, curve, phase, _color) in enumerate(rows):
        center = offset + slope * x + curve * (x * x - 0.38) + 0.035 * np.sin(2.8 * x + phase)
        d = y - center
        gate = 0.36 + 0.64 * smooth(-0.35, 0.72, np.sin(16.0 * x + 1.7 * phase))
        lane_halo = np.exp(-((d / 0.086) ** 2)).astype(np.float32)
        core = np.exp(-((d / 0.0062) ** 2)).astype(np.float32) * gate
        satellite = (
            np.exp(-(((d - 0.014) / 0.0046) ** 2))
            + np.exp(-(((d + 0.014) / 0.0046) ** 2))
        ).astype(np.float32) * gate
        reflection = np.exp(-(((d - 0.085) / 0.050) ** 2)).astype(np.float32) * (0.28 + 0.72 * gate)
        volume = np.exp(-((d / 0.30) ** 2)).astype(np.float32) * (0.36 + 0.64 * gate)
        plane_offset = 0.18 if i % 2 == 0 else -0.18
        plane = np.exp(-(((d - plane_offset) / 0.115) ** 2)).astype(np.float32)
        lips = np.maximum(
            np.exp(-(((d - plane_offset - 0.055) / 0.012) ** 2)),
            np.exp(-(((d - plane_offset + 0.055) / 0.012) ** 2)),
        ).astype(np.float32)
        halo = np.maximum(halo, lane_halo)
        cores = np.maximum(cores, core)
        satellites = np.maximum(satellites, np.clip(satellite, 0.0, 1.0))
        reflections = np.maximum(reflections, reflection)
        interference_plane = np.maximum(interference_plane, plane * (0.34 + 0.66 * gate))
        plane_lips = np.maximum(plane_lips, lips * (0.30 + 0.70 * gate))
        along = np.maximum(along, lane_halo * np.mod(0.5 * x + 0.19 * i, 1.0))
        if i < 2:
            red = np.maximum(red, lane_halo)
            red_volume = np.maximum(red_volume, volume)
        else:
            cyan = np.maximum(cyan, lane_halo)
            cyan_volume = np.maximum(cyan_volume, volume)
        active_a = np.maximum(active_a, lane_halo * (0.96 if i in (0, 2) else 0.45))
        active_b = np.maximum(active_b, lane_halo * (0.96 if i in (1, 3) else 0.45))

    # Deterministic beam anatomy: pulse bands, plane lips, lane-volume
    # lamellae, overlap fringes and rain-sliced wet reflections.
    anchors = ridge(31.0 * x + 4.5 * y, 0.16) * blur(cores, 2.0)
    lane_volume = np.clip(np.maximum(red_volume, cyan_volume), 0.0, 1.0)
    overlap_volume = smooth(0.08, 0.42, red_volume * cyan_volume)
    haze_lamellae = ridge(46.0 * (y - 0.12 * x + 0.022 * np.sin(4.8 * x))
                           + 0.62 * lane_volume, 0.15)
    haze_lamellae *= 0.22 + 0.78 * lane_volume
    interference_fringes = ridge(58.0 * (y - 0.12 * x + 0.018 * np.sin(4.8 * x))
                                  + 0.62 * lane_volume
                                  + 0.36 * (red_volume - cyan_volume) + 0.29, 0.11)
    interference_fringes *= np.maximum(interference_plane, overlap_volume)
    rain_cuts = ridge(61.0 * y + 9.0 * x, 0.055) * reflections
    pulse_knots = ridge(42.0 * x + 4.0 * np.sin(3.0 * y), 0.075) * cores

    wet_height = blur(0.56 * halo + 0.86 * cores + 0.24 * reflections
                      + 0.18 * interference_plane, 1.5)
    light_a = smooth(-0.14, 0.72, normal_light(wet_height, (0.66, -0.24, 0.72)))
    light_b = smooth(-0.14, 0.72, normal_light(wet_height, (-0.62, 0.34, 0.72)))
    ground = np.empty((size, size, 3), np.float32)
    ground[:] = (0.007, 0.009, 0.016)
    ground += (0.028 * smooth(-1.0, 1.0, x))[..., None] * np.asarray((0.12, 0.18, 0.25), np.float32)

    ground_a = _mix(ground, (0.24, 0.006, 0.055),
                    0.13 * red_volume * (0.30 + 0.70 * light_a))
    ground_a = _mix(ground_a, (0.006, 0.17, 0.22),
                    0.13 * cyan_volume * (0.30 + 0.70 * light_a))
    ground_b = _mix(ground, (0.25, 0.008, 0.18),
                    0.14 * red_volume * (0.30 + 0.70 * light_b))
    ground_b = _mix(ground_b, (0.06, 0.10, 0.28),
                    0.14 * cyan_volume * (0.30 + 0.70 * light_b))

    red_energy_a = np.clip(red * (0.48 + 0.66 * light_a) + 0.24 * active_a + 0.55 * cores + 0.32 * reflections, 0.0, 1.0)
    red_energy_b = np.clip(red * (0.24 + 0.94 * light_b) + 0.48 * active_b + 0.44 * cores + 0.48 * reflections, 0.0, 1.0)
    cyan_energy_a = np.clip(cyan * (0.46 + 0.66 * light_a) + 0.24 * active_a + 0.55 * satellites, 0.0, 1.0)
    cyan_energy_b = np.clip(cyan * (0.22 + 0.96 * light_b) + 0.48 * active_b + 0.44 * satellites, 0.0, 1.0)
    b_order = smooth(0.18, 0.82, np.mod(along + 0.34 * light_b + 0.17, 1.0))
    red_b_color = (
        np.asarray((1.00, 0.015, 0.20), np.float32)[None, None, :] * (1.0 - b_order[..., None])
        + np.asarray((1.00, 0.12, 0.78), np.float32)[None, None, :] * b_order[..., None]
    )
    cyan_b_color = (
        np.asarray((0.02, 0.98, 1.00), np.float32)[None, None, :] * (1.0 - b_order[..., None])
        + np.asarray((0.48, 0.10, 1.00), np.float32)[None, None, :] * b_order[..., None]
    )
    paint_a = _mix(ground_a, (1.00, 0.025, 0.34), red_energy_a)
    paint_a = _mix(paint_a, (0.08, 0.92, 1.00), cyan_energy_a)
    paint_b = _mix(ground_b, red_b_color, red_energy_b)
    paint_b = _mix(paint_b, cyan_b_color, cyan_energy_b)
    fine_hot = np.clip(cores + 0.70 * satellites + anchors + 0.45 * pulse_knots, 0.0, 1.0)
    paint_a = _mix(paint_a, (1.0, 0.94, 0.92), 0.72 * fine_hot * (0.42 + 0.58 * light_a))
    b_live = np.clip(0.72 * satellites + 0.68 * anchors + 0.56 * reflections + 0.44 * pulse_knots, 0.0, 1.0)
    paint_b = _mix(paint_b, (0.90, 0.94, 1.00), 0.82 * b_live * smooth(0.16, 0.78, light_b))
    plane_anatomy = np.clip(0.50 * haze_lamellae + 0.58 * interference_fringes
                            + 0.54 * plane_lips + 0.34 * rain_cuts, 0.0, 1.0)
    paint_a = _mix(paint_a, (0.40, 0.62, 0.72),
                   0.14 * plane_anatomy * (0.28 + 0.72 * light_a))
    paint_b = _mix(paint_b, (0.64, 0.34, 0.86),
                   0.15 * plane_anatomy * (0.28 + 0.72 * light_b))

    road_grade = smooth(-1.0, 1.0, 0.63 * x - 0.37 * y)
    metal = unit(0.04 + 0.24 * road_grade + 0.18 * lane_volume + 0.22 * halo
                 + 0.62 * cores + 0.54 * anchors + 0.34 * plane_lips
                 + 0.24 * interference_fringes + 0.16 * satellites)
    rough = unit(0.09 + 0.22 * (1.0 - road_grade) + 0.18 * halo
                 + 0.50 * haze_lamellae + 0.48 * interference_fringes
                 + 0.42 * rain_cuts + 0.24 * pulse_knots - 0.20 * interference_plane)
    coat = unit(0.10 + 0.48 * lane_volume + 0.62 * interference_plane
                + 0.70 * reflections + 0.48 * halo + 0.28 * satellites
                - 0.38 * haze_lamellae - 0.34 * rain_cuts - 0.24 * plane_lips)
    spec = pack_physical(
        metal,
        rough,
        coat,
        m_cuts=(0.045, 0.09, 0.16, 0.25, 0.37, 0.51, 0.66, 0.81, 0.93),
        r_cuts=(0.07, 0.14, 0.22, 0.32, 0.44, 0.57, 0.70, 0.83, 0.93),
        c_cuts=(0.06, 0.13, 0.22, 0.33, 0.45, 0.58, 0.71, 0.84, 0.94),
    )
    return finish(
        started,
        FINISH_ID,
        DISPLAY_NAME,
        paint_a,
        paint_b,
        spec,
        "rain-dark graphite clear crossed by four unequal bundled laser corridors and their wet optical echoes",
        {
            "M": "beam cores, pulse anchors, satellite electrodes, plane lips, and overlap fringes reveal conductive return",
            "R": "lane-volume lamellae, interference fringes, rain cuts, and pulse knots shear the wet lane surface",
            "Cc": "broad beam volume, interference planes, halos, and offset wet reflections retain deep clear",
        },
    )
