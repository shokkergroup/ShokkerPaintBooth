"""Arcade Afterhours — broad CRT sweeps and phosphor trails after closing."""
from __future__ import annotations

import numpy as np

from .core import FinishResult, WORK, begin, blur, coords, finish, normal_light, pack_physical, resize_result, ridge, smooth, soft_noise, unit


FINISH_ID = "neon2_synthwave_sun"
DISPLAY_NAME = "Arcade Afterhours"
DEFAULT_SEED = 0xA2CA4E

# SPB-105 / NU-V4-AA-1 / 2026-08-27 — owner verdict: v3 lacked Oil
# Slick mechanics, real neon, and Tokyo Drift identity.  These broad phosphor
# sweeps read at picker scale; fine scan anatomy never becomes the carrier.


def _mix(paint: np.ndarray, color: tuple[float, float, float], amount: np.ndarray) -> np.ndarray:
    a = np.clip(amount, 0.0, 1.0)[..., None]
    c = np.asarray(color, np.float32)
    return paint * (1.0 - a) + c * a


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    started = begin()
    size = int(size)
    if size < 256:
        raise ValueError("Arcade Afterhours requires size >= 256")
    if size > WORK:
        source = build(seed=seed, size=WORK)
        paint_a, paint_b, spec = resize_result(source, size)
        return finish(started, FINISH_ID, DISPLAY_NAME, paint_a, paint_b, spec, source.carrier, source.material_story)
    x, y = coords(size)

    # Five unequal CRT/vector sweeps produce one broad diagonal game-floor
    # current.  None repeats as a tile or isolated glyph.
    sweeps = (
        (-0.78, 0.18, 0.15, 0.0),
        (-0.39, -0.14, -0.10, 1.1),
        (0.02, 0.22, 0.08, 2.2),
        (0.43, -0.18, -0.13, 3.4),
        (0.80, 0.12, 0.11, 4.6),
    )
    magenta = np.zeros_like(x)
    cyan = np.zeros_like(x)
    violet = np.zeros_like(x)
    cores = np.zeros_like(x)
    afterglow = np.zeros_like(x)
    leading = np.zeros_like(x)
    trailing = np.zeros_like(x)
    for i, (offset, slope, curve, phase) in enumerate(sweeps):
        center = offset + slope * x + curve * (x * x - 0.45) + 0.055 * np.sin(2.2 * x + phase)
        d = y - center
        envelope = np.exp(-((d / 0.095) ** 2)).astype(np.float32)
        core = np.exp(-((d / 0.0075) ** 2)).astype(np.float32)
        ghost = np.exp(-(((d - 0.045) / 0.055) ** 2)).astype(np.float32)
        lead = np.exp(-(((d + 0.022) / 0.014) ** 2)).astype(np.float32)
        trail = np.exp(-(((d - 0.030) / 0.020) ** 2)).astype(np.float32)
        cores = np.maximum(cores, core)
        afterglow = np.maximum(afterglow, ghost)
        leading = np.maximum(leading, lead)
        trailing = np.maximum(trailing, trail)
        if i % 3 == 0:
            magenta = np.maximum(magenta, envelope)
        elif i % 3 == 1:
            cyan = np.maximum(cyan, envelope)
        else:
            violet = np.maximum(violet, envelope)

    # Attached 8–32px families: scan combs, vector rails, phosphor beads,
    # retrace gaps, burn notches, and white raster intersections.
    scan_combs = ridge(82.0 * y + 5.0 * np.sin(3.0 * x), 0.075) * np.clip(magenta + cyan + violet, 0.0, 1.0)
    vector_rails = ridge(49.0 * (x + 0.11 * np.sin(2.6 * y)) - 9.0 * y, 0.072) * afterglow
    phosphor_beads = smooth(0.78, 0.935, soft_noise(seed + 7, size, 12.0, 2.2)) * blur(cores, 2.4)
    retrace_gaps = ridge(31.0 * x + 13.0 * y, 0.060) * leading
    burn_notches = smooth(0.76, 0.925, soft_noise(seed + 41, size, 20.0, 2.7)) * trailing
    raster_hits = ridge(65.0 * x - 21.0 * y, 0.050) * scan_combs * blur(cores, 1.8)

    carrier = np.clip(0.58 * (magenta + cyan + violet) + 0.52 * afterglow, 0.0, 1.0)
    height = blur(0.52 * carrier + 0.78 * cores + 0.32 * leading + 0.18 * scan_combs, 1.45)
    light_a = smooth(-0.15, 0.70, normal_light(height, (0.58, -0.39, 0.72)))
    light_b = smooth(-0.15, 0.70, normal_light(height, (-0.49, 0.51, 0.71)))

    ground = np.empty((size, size, 3), np.float32)
    ground[:] = (0.010, 0.004, 0.028)
    ground += (0.026 * smooth(-1.0, 1.0, x + 0.3 * y))[..., None] * np.asarray((0.24, 0.05, 0.34), np.float32)
    paint_a = _mix(ground, (1.00, 0.025, 0.72), magenta * (0.28 + 0.76 * light_a))
    paint_a = _mix(paint_a, (0.02, 0.92, 1.00), cyan * (0.27 + 0.74 * light_a))
    paint_a = _mix(paint_a, (0.48, 0.08, 1.00), violet * (0.26 + 0.72 * light_a))
    paint_b = _mix(ground, (1.00, 0.025, 0.72), magenta * (0.28 + 0.76 * light_b))
    paint_b = _mix(paint_b, (0.02, 0.92, 1.00), cyan * (0.27 + 0.74 * light_b))
    paint_b = _mix(paint_b, (0.48, 0.08, 1.00), violet * (0.26 + 0.72 * light_b))

    # A exposes the current raster's leading faces; B exposes its true
    # trailing phosphor state, changing lit geometry rather than only hue.
    live_a = np.clip(0.76 * leading + 0.64 * cores + 0.38 * scan_combs + phosphor_beads, 0.0, 1.0)
    live_b = np.clip(0.76 * trailing + 0.58 * afterglow + 0.42 * vector_rails + phosphor_beads, 0.0, 1.0)
    paint_a = _mix(paint_a, (1.0, 0.93, 1.0), 0.70 * live_a * (0.38 + 0.62 * light_a))
    paint_b = _mix(paint_b, (0.85, 0.96, 1.0), 0.70 * live_b * (0.38 + 0.62 * light_b))

    backplane_grade = smooth(-1.0, 1.0, 0.58 * x + 0.42 * y)
    metal = unit(0.04 + 0.26 * backplane_grade + 0.20 * carrier + 0.62 * raster_hits + 0.56 * phosphor_beads + 0.40 * cores + 0.18 * vector_rails)
    rough = unit(0.08 + 0.68 * burn_notches + 0.55 * retrace_gaps + 0.38 * scan_combs + 0.26 * (1.0 - carrier))
    coat = unit(0.10 + 0.76 * carrier + 0.50 * afterglow + 0.34 * leading - 0.58 * burn_notches - 0.42 * retrace_gaps)
    spec = pack_physical(
        metal,
        rough,
        coat,
        m_cuts=(0.05, 0.10, 0.17, 0.27, 0.39, 0.53, 0.67, 0.81, 0.93),
        r_cuts=(0.07, 0.14, 0.22, 0.32, 0.43, 0.55, 0.68, 0.82, 0.93),
        c_cuts=(0.055, 0.12, 0.21, 0.32, 0.44, 0.57, 0.70, 0.83, 0.94),
    )
    return finish(
        started,
        FINISH_ID,
        DISPLAY_NAME,
        paint_a,
        paint_b,
        spec,
        "deep black-violet arcade glass carrying five broad after-hours CRT sweeps and their fading phosphor memory",
        {
            "M": "raster intersections, phosphor bead electrodes, vector rails, and exposed sweep cores carry conductivity",
            "R": "burn-in notches, retrace gaps, dead scan combs, and unlit glass interrupt the smooth phosphor face",
            "Cc": "intact sweep glass and broad afterglow shoulders keep clear while burns and retrace cuts remove it",
        },
    )
