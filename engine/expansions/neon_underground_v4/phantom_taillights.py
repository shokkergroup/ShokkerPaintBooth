"""Phantom Taillights — red afterimage ribbons crossing midnight blue."""
from __future__ import annotations

import numpy as np

from .core import FinishResult, WORK, begin, blur, coords, finish, normal_light, pack_physical, resize_result, ridge, smooth, unit


FINISH_ID = "neon2_phantom_mica"
DISPLAY_NAME = "Phantom Taillights"
DEFAULT_SEED = 0x7A11A17

# SPB-105 / NU-V4-PT-1 / 2026-08-27 — owner verdict: v3 lacked Oil
# Slick mechanics, neon, and Tokyo Drift identity.  Directional taillight
# afterimages now dominate; LEDs and rain cuts remain fine attached evidence.
# NU-V4 whole-car correction: the owner found the hero promising but the dark
# body too poster-like, so every new 8-32px mark follows taillight diffusion,
# wet-body drainage, or an optical echo rather than freestanding particles.


def _mix(paint: np.ndarray, color: tuple[float, float, float], amount: np.ndarray) -> np.ndarray:
    a = np.clip(amount, 0.0, 1.0)[..., None]
    c = np.asarray(color, np.float32)
    return paint * (1.0 - a) + c * a


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    started = begin()
    size = int(size)
    if size < 256:
        raise ValueError("Phantom Taillights requires size >= 256")
    if size > WORK:
        source = build(seed=seed, size=WORK)
        paint_a, paint_b, spec = resize_result(source, size)
        return finish(started, FINISH_ID, DISPLAY_NAME, paint_a, paint_b, spec, source.carrier, source.material_story)
    x, y = coords(size)

    # Four long unequal trajectories create an unmistakable lateral night
    # carrier without drawing literal lamps or repeating vehicle silhouettes.
    rows = (
        (-0.58, 0.17, 0.13, 0.1),
        (-0.20, -0.12, -0.08, 1.5),
        (0.25, 0.21, 0.10, 2.9),
        (0.65, -0.16, -0.12, 4.2),
    )
    ribbon = np.zeros_like(x)
    cores = np.zeros_like(x)
    leading = np.zeros_like(x)
    trailing = np.zeros_like(x)
    reflection = np.zeros_like(x)
    diffusion = np.zeros_like(x)
    wet_body = np.zeros_like(x)
    diffusion_lips = np.zeros_like(x)
    red_ribbon = np.zeros_like(x)
    pink_ribbon = np.zeros_like(x)
    for i, (offset, slope, curve, phase) in enumerate(rows):
        center = offset + slope * x + curve * (x * x - 0.42) + 0.048 * np.sin(2.5 * x + phase)
        d = y - center
        taper = smooth(-0.95, 0.82, x + 0.08 * np.sin(2.0 * y + phase))
        broad = np.exp(-((d / 0.112) ** 2)).astype(np.float32) * (0.42 + 0.58 * taper)
        core = np.exp(-((d / 0.0070) ** 2)).astype(np.float32)
        lead = np.exp(-(((d + 0.021) / 0.014) ** 2)).astype(np.float32)
        trail = np.exp(-(((d - 0.038) / 0.030) ** 2)).astype(np.float32) * taper
        echo = np.exp(-(((d - 0.105) / 0.050) ** 2)).astype(np.float32) * (0.20 + 0.80 * taper)
        fog = np.exp(-((d / 0.285) ** 2)).astype(np.float32) * (0.34 + 0.66 * taper)
        body_echo = np.exp(-(((d - 0.17 - 0.025 * np.sin(2.0 * x + phase)) / 0.19) ** 2)).astype(np.float32)
        body_echo *= 0.30 + 0.70 * taper
        echo_lips = np.maximum(
            np.exp(-(((d - 0.145) / 0.012) ** 2)),
            np.exp(-(((d - 0.205) / 0.012) ** 2)),
        ).astype(np.float32) * (0.28 + 0.72 * taper)
        ribbon = np.maximum(ribbon, broad)
        cores = np.maximum(cores, core)
        leading = np.maximum(leading, lead)
        trailing = np.maximum(trailing, trail)
        reflection = np.maximum(reflection, echo)
        diffusion = np.maximum(diffusion, fog)
        wet_body = np.maximum(wet_body, body_echo)
        diffusion_lips = np.maximum(diffusion_lips, echo_lips)
        if i % 2:
            pink_ribbon = np.maximum(pink_ribbon, broad)
        else:
            red_ribbon = np.maximum(red_ribbon, broad)

    # Seven deterministic native-fine families. None is a random bead, chip or
    # scratch: pulse bands stay on the live lens, shear follows the wet body,
    # and reflection ticks/lips remain inside the afterimage history.
    led_dashes = ridge(48.0 * x + 6.0 * y, 0.085) * ridge(12.0 * y - 2.0 * x, 0.20) * blur(cores, 2.0)
    brake_pulses = ridge(29.0 * x + 3.4 * y, 0.16) * blur(cores, 3.0)
    taper_striae = ridge(62.0 * (x + 0.08 * np.sin(3.0 * y)), 0.055) * trailing
    rain_shear = ridge(46.0 * (y - 0.14 * x + 0.018 * np.sin(5.2 * x))
                       + 0.72 * diffusion, 0.15)
    rain_shear *= 0.24 + 0.76 * np.maximum(diffusion, wet_body)
    reflection_ticks = ridge(43.0 * x - 17.0 * y, 0.060) * reflection
    lens_facets = ridge(54.0 * x + 8.0 * y, 0.14) * leading
    body_striae = ridge(58.0 * (y - 0.14 * x + 0.016 * np.sin(5.2 * x))
                        + 0.72 * diffusion + 0.31, 0.11) * wet_body

    height = blur(0.50 * ribbon + 0.84 * cores + 0.36 * leading
                  + 0.24 * reflection + 0.16 * wet_body, 1.5)
    light_a = smooth(-0.14, 0.72, normal_light(height, (0.65, -0.24, 0.72)))
    light_b = smooth(-0.14, 0.72, normal_light(height, (-0.58, 0.39, 0.72)))
    ground = np.empty((size, size, 3), np.float32)
    ground[:] = (0.004, 0.008, 0.030)
    ground += (0.034 * smooth(-1.0, 1.0, x - 0.2 * y))[..., None] * np.asarray((0.08, 0.16, 0.48), np.float32)

    ground_a = _mix(ground, (0.24, 0.006, 0.075),
                    0.16 * diffusion * (0.32 + 0.68 * light_a))
    ground_a = _mix(ground_a, (0.13, 0.018, 0.20),
                    0.11 * wet_body * (0.42 + 0.58 * light_a))
    ground_b = _mix(ground, (0.18, 0.008, 0.15),
                    0.15 * diffusion * (0.32 + 0.68 * light_b))
    ground_b = _mix(ground_b, (0.26, 0.018, 0.12),
                    0.12 * wet_body * (0.42 + 0.58 * light_b))

    red_a = red_ribbon * (0.52 + 0.64 * light_a)
    red_b = red_ribbon * (0.52 + 0.64 * light_b)
    pink_a = pink_ribbon * (0.52 + 0.64 * light_a)
    pink_b = pink_ribbon * (0.52 + 0.64 * light_b)
    paint_a = _mix(ground_a, (1.00, 0.025, 0.22), red_a)
    paint_a = _mix(paint_a, (1.00, 0.045, 0.68), pink_a)
    paint_b = _mix(ground_b, (1.00, 0.025, 0.22), red_b)
    paint_b = _mix(paint_b, (1.00, 0.045, 0.68), pink_b)

    # A catches the live leading lens; B catches the fading trailing image and
    # lower wet echo, so the light state changes spatial ownership.
    live_a = np.clip(0.84 * leading + 0.72 * cores + brake_pulses + 0.45 * led_dashes, 0.0, 1.0)
    live_b = np.clip(0.78 * trailing + 0.62 * reflection + 0.52 * taper_striae + 0.36 * reflection_ticks, 0.0, 1.0)
    paint_a = _mix(paint_a, (1.0, 0.88, 0.90), 0.72 * live_a * (0.38 + 0.62 * light_a))
    paint_b = _mix(paint_b, (0.85, 0.86, 1.0), 0.72 * live_b * (0.38 + 0.62 * light_b))
    wet_anatomy = np.clip(0.62 * rain_shear + 0.48 * body_striae
                          + 0.44 * reflection_ticks + 0.52 * diffusion_lips, 0.0, 1.0)
    paint_a = _mix(paint_a, (0.82, 0.16, 0.34),
                   0.15 * wet_anatomy * (0.28 + 0.72 * light_a))
    paint_b = _mix(paint_b, (0.74, 0.14, 0.52),
                   0.16 * wet_anatomy * (0.28 + 0.72 * light_b))

    midnight_grade = smooth(-1.0, 1.0, 0.68 * x - 0.32 * y)
    metal = unit(0.05 + 0.22 * midnight_grade + 0.18 * diffusion
                 + 0.20 * ribbon + 0.56 * cores + 0.58 * brake_pulses
                 + 0.38 * lens_facets + 0.28 * led_dashes + 0.20 * diffusion_lips)
    rough = unit(0.08 + 0.58 * rain_shear + 0.48 * taper_striae
                 + 0.36 * body_striae + 0.28 * reflection_ticks
                 + 0.18 * (1.0 - np.maximum(diffusion, wet_body)))
    coat = unit(0.08 + 0.48 * diffusion + 0.64 * wet_body + 0.68 * ribbon
                + 0.54 * reflection + 0.38 * leading
                - 0.42 * rain_shear - 0.30 * body_striae - 0.24 * diffusion_lips)
    spec = pack_physical(
        metal,
        rough,
        coat,
        m_cuts=(0.05, 0.10, 0.18, 0.28, 0.40, 0.53, 0.67, 0.81, 0.93),
        r_cuts=(0.07, 0.14, 0.23, 0.33, 0.45, 0.57, 0.69, 0.82, 0.93),
        c_cuts=(0.055, 0.12, 0.21, 0.32, 0.44, 0.57, 0.70, 0.83, 0.94),
    )
    return finish(
        started,
        FINISH_ID,
        DISPLAY_NAME,
        paint_a,
        paint_b,
        spec,
        "midnight-blue wet candy carrying four red and magenta taillight afterimage trajectories with fading optical echoes",
        {
            "M": "live lens cores, LED dashes, pulse bands, lens facets, and afterimage lips expose reflective backing",
            "R": "whole-body rain shear, fading striae, and reflection ticks create directional wet drag",
            "Cc": "diffused taillight volume, broad wet-body echoes, and intact ribbons retain deep clear",
        },
    )
