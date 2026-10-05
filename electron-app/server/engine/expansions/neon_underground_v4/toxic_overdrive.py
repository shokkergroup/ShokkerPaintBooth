"""Toxic Overdrive — broad acid-current pools under moving pressure light."""
from __future__ import annotations

import numpy as np

from .core import (
    FinishResult,
    WORK,
    begin,
    blur,
    coords,
    finish,
    normal_light,
    pack_physical,
    resize_result,
    ridge,
    smooth,
    soft_noise,
    unit,
    warp_vortices,
)


FINISH_ID = "neon_toxic_green"
DISPLAY_NAME = "Toxic Overdrive"
DEFAULT_SEED = 0x70A1C

# SPB-105 / NU-V4-TO-1 / 2026-08-27 — owner verdict: v3 lacked Oil
# Slick mechanics, visible neon, and Tokyo Drift identity.  One broad acid
# pressure sheet now owns the paint; fine deposits only describe its history.


def _mix(paint: np.ndarray, color: tuple[float, float, float], amount: np.ndarray) -> np.ndarray:
    a = np.clip(amount, 0.0, 1.0)[..., None]
    c = np.asarray(color, np.float32)
    return paint * (1.0 - a) + c * a


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    started = begin()
    size = int(size)
    if size < 256:
        raise ValueError("Toxic Overdrive requires size >= 256")
    if size > WORK:
        source = build(seed=seed, size=WORK)
        paint_a, paint_b, spec = resize_result(source, size)
        return finish(started, FINISH_ID, DISPLAY_NAME, paint_a, paint_b, spec, source.carrier, source.material_story)
    x, y = coords(size)
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    jitter = rng.uniform(-0.035, 0.035, 6).astype(np.float32)
    qx, qy = warp_vortices(
        x,
        y,
        (
            (-0.55 + jitter[0], -0.20 + jitter[1], 0.74, 0.34),
            (0.48 + jitter[2], 0.10 + jitter[3], 0.67, -0.29),
            (-0.06 + jitter[4], 0.68 + jitter[5], 0.58, 0.23),
        ),
    )

    # A coherent warped pressure sheet forms a few large current pools and
    # black sink territories—never a tiled cellular or dark-noise carpet.
    drive = (
        0.50
        + 0.21 * np.sin(3.05 * qx + 1.18 * qy)
        + 0.16 * np.cos(3.35 * qy - 0.82 * qx)
        + 0.09 * np.sin(4.85 * qx - 1.55 * qy)
        + 0.10 * (0.68 * qx - 0.32 * qy)
    ).astype(np.float32)
    field = unit(drive)
    pools = smooth(0.52, 0.76, field)
    deep_current = smooth(0.68, 0.91, field)
    pressure_lips = np.exp(-(((field - 0.57) / 0.040) ** 2)).astype(np.float32)
    wet_shoulders = np.exp(-(((field - 0.49) / 0.115) ** 2)).astype(np.float32)
    black_sink = smooth(0.33, 0.55, 1.0 - field)

    # Six causal 8–32px detail families attached to the pressure anatomy.
    capillary_forks = np.maximum(
        ridge(39.0 * (qx + 0.12 * np.sin(3.2 * qy)) + 7.0 * qy, 0.070),
        ridge(34.0 * (qx + qy + 0.05 * np.sin(5.0 * qx)), 0.060),
    ) * pools
    precipitate_dashes = ridge(57.0 * qx - 18.0 * qy, 0.065) * ridge(14.0 * qy + 3.0 * qx, 0.17) * wet_shoulders
    pressure_ticks = ridge(63.0 * (qx - 0.27 * qy), 0.055) * pressure_lips
    bubble_pinpoints = smooth(0.80, 0.945, soft_noise(seed + 19, size, 13.0, 2.0)) * deep_current
    abrasion_streaks = ridge(46.0 * qx + 22.0 * qy, 0.060) * black_sink * wet_shoulders
    dry_pits = smooth(0.79, 0.94, soft_noise(seed + 47, size, 17.0, 2.4)) * black_sink

    height = blur(0.66 * pools + 0.74 * pressure_lips + 0.24 * wet_shoulders + 0.15 * capillary_forks, 1.5)
    light_a = smooth(-0.14, 0.72, normal_light(height, (0.61, -0.34, 0.72)))
    light_b = smooth(-0.14, 0.72, normal_light(height, (-0.57, 0.42, 0.71)))

    ground = np.empty((size, size, 3), np.float32)
    ground[:] = (0.005, 0.012, 0.003)
    ground += (0.028 * smooth(-1.0, 1.0, 0.7 * x - 0.3 * y))[..., None] * np.asarray((0.10, 0.20, 0.03), np.float32)
    neon_a = np.clip(0.47 * pools * (0.36 + 0.74 * light_a) + 0.66 * wet_shoulders + 0.68 * pressure_lips, 0.0, 1.0)
    neon_b = np.clip(0.47 * pools * (0.36 + 0.74 * light_b) + 0.66 * wet_shoulders + 0.68 * pressure_lips, 0.0, 1.0)
    paint_a = _mix(ground, (0.08, 0.96, 0.02), neon_a)
    # Opposing light reveals a different interference order across the same
    # acid pools: emerald sinks turn cyan-green while compressed shoulders
    # retain lime.  The ownership is field/light driven, not a global tint.
    b_order = smooth(0.18, 0.82, np.clip(0.46 * field + 0.54 * light_b, 0.0, 1.0))
    toxic_b_color = (
        np.asarray((0.02, 0.82, 0.18), np.float32)[None, None, :] * (1.0 - b_order[..., None])
        + np.asarray((0.05, 1.00, 0.72), np.float32)[None, None, :] * b_order[..., None]
    )
    neon_b_view = np.clip(neon_b * (0.62 + 0.48 * light_b) + 0.30 * deep_current * smooth(0.34, 0.82, light_b), 0.0, 1.0)
    paint_b = _mix(ground, toxic_b_color, neon_b_view)
    yellow_hot = np.clip(pressure_lips + 0.58 * pressure_ticks + 0.55 * bubble_pinpoints + 0.38 * precipitate_dashes, 0.0, 1.0)
    paint_a = _mix(paint_a, (1.00, 0.94, 0.06), 0.78 * yellow_hot * (0.36 + 0.64 * light_a))
    paint_b = _mix(paint_b, (0.58, 1.00, 0.18), 0.66 * yellow_hot * smooth(0.20, 0.78, light_b))
    paint_a = _mix(paint_a, (0.72, 1.00, 0.80), 0.48 * capillary_forks * light_a)
    paint_b = _mix(paint_b, (0.52, 0.96, 1.00), 0.64 * capillary_forks * smooth(0.18, 0.76, light_b))
    # The opposite view exchanges exposed pressure cuts for pooled-deposit
    # glints, creating a genuine optical-state change on the same sheet.
    paint_a = _mix(paint_a, (0.92, 1.00, 0.38), 0.42 * np.clip(pressure_ticks + abrasion_streaks, 0.0, 1.0) * light_a)
    paint_b = _mix(paint_b, (0.42, 0.92, 1.00), 0.68 * np.clip(precipitate_dashes + bubble_pinpoints, 0.0, 1.0) * smooth(0.16, 0.74, light_b))

    metal = unit(0.05 + 0.52 * pressure_lips + 0.66 * bubble_pinpoints + 0.48 * abrasion_streaks + 0.30 * pressure_ticks + 0.16 * field)
    rough = unit(0.08 + 0.70 * dry_pits + 0.56 * abrasion_streaks + 0.44 * precipitate_dashes + 0.24 * black_sink)
    coat = unit(0.08 + 0.72 * pools + 0.66 * wet_shoulders + 0.30 * pressure_lips - 0.58 * dry_pits - 0.44 * abrasion_streaks)
    spec = pack_physical(
        metal,
        rough,
        coat,
        m_cuts=(0.055, 0.11, 0.19, 0.29, 0.41, 0.54, 0.68, 0.82, 0.93),
        r_cuts=(0.07, 0.14, 0.23, 0.33, 0.44, 0.56, 0.69, 0.82, 0.93),
        c_cuts=(0.05, 0.12, 0.21, 0.32, 0.44, 0.57, 0.71, 0.84, 0.94),
    )
    return finish(
        started,
        FINISH_ID,
        DISPLAY_NAME,
        paint_a,
        paint_b,
        spec,
        "one warped acid-current clearcoat sheet forming broad green pressure pools, yellow lips, and deep black overdrive sinks",
        {
            "M": "pressure lips, burst pinpoints, abrasion streaks, and overdriven ticks expose conductive substrate",
            "R": "dry pits, scraped sinks, precipitate dashes, and capillary damage roughen the current path",
            "Cc": "wet current pools and smooth pressure shoulders retain clear while dry sinks and abrasion remove it",
        },
    )
