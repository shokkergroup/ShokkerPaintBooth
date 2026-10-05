"""Turbo Heat — anodized titanium heat zones and moving weld glints."""
from __future__ import annotations

import numpy as np

from .core import FinishResult, WORK, begin, blur, coords, finish, normal_light, pack_physical, palette_ramp, resize_result, ridge, smooth, soft_noise, unit


FINISH_ID = "neon2_emberwake_delam"
DISPLAY_NAME = "Turbo Heat"
DEFAULT_SEED = 0x7A280

# SPB-105 / NU-V4-TH-1 / 2026-08-27 — owner verdict: v3 lacked Oil
# Slick mechanics, neon, and Tokyo Drift identity.  Broad turbo-temper zones
# own this metal sheet; weld ripples and heat checks are subordinate anatomy.


def _mix(paint: np.ndarray, color: np.ndarray, amount: np.ndarray) -> np.ndarray:
    a = np.clip(amount, 0.0, 1.0)[..., None]
    return paint * (1.0 - a) + color * a


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    started = begin()
    size = int(size)
    if size < 256:
        raise ValueError("Turbo Heat requires size >= 256")
    if size > WORK:
        source = build(seed=seed, size=WORK)
        paint_a, paint_b, spec = resize_result(source, size)
        return finish(started, FINISH_ID, DISPLAY_NAME, paint_a, paint_b, spec, source.carrier, source.material_story)
    x, y = coords(size)

    rows = (
        (-0.54, 0.28, 0.12, 0.2),
        (0.02, -0.22, -0.10, 2.0),
        (0.56, 0.24, 0.14, 4.1),
    )
    nearest = np.ones_like(x) * 4.0
    seam_core = np.zeros_like(x)
    seam_halo = np.zeros_like(x)
    signed_near = np.zeros_like(x)
    along = np.zeros_like(x)
    for i, (offset, slope, curve, phase) in enumerate(rows):
        center = offset + slope * x + curve * (x * x - 0.42) + 0.052 * np.sin(2.2 * x + phase)
        d = y - center
        ad = np.abs(d)
        choose = ad < nearest
        signed_near = np.where(choose, d, signed_near)
        nearest = np.minimum(nearest, ad)
        seam_core = np.maximum(seam_core, np.exp(-((d / 0.0068) ** 2)).astype(np.float32))
        seam_halo = np.maximum(seam_halo, np.exp(-((d / 0.070) ** 2)).astype(np.float32))
        along = np.maximum(along, np.exp(-((d / 0.19) ** 2)).astype(np.float32) * np.mod(0.48 * x + 0.21 * i, 1.0))

    heat_zone = np.exp(-((nearest / 0.205) ** 2)).astype(np.float32)
    temper_lip = np.exp(-(((nearest - 0.085) / 0.026) ** 2)).astype(np.float32)
    cooling_zone = np.exp(-(((nearest - 0.175) / 0.075) ** 2)).astype(np.float32)
    heat_order = unit(0.52 * heat_zone + 0.30 * temper_lip + 0.18 * along)
    oxide_color = palette_ramp(
        heat_order,
        ((0.10, 0.16, 0.25), (0.10, 0.44, 0.86), (0.48, 0.12, 0.88), (1.00, 0.18, 0.45), (1.00, 0.58, 0.08), (0.78, 0.94, 1.00)),
    )

    # Six native-fine histories attached to three broad weld/temper zones.
    weld_ripples = ridge(51.0 * x + 5.0 * np.sin(3.0 * y), 0.080) * seam_halo
    brushed_strokes = ridge(79.0 * (x + 0.075 * np.sin(2.5 * y)), 0.050) * (0.24 + 0.76 * heat_zone)
    cooling_ticks = ridge(58.0 * x - 17.0 * y, 0.052) * ridge(13.0 * y, 0.17) * cooling_zone
    heat_checks = ridge(43.0 * (x + y + 0.04 * np.sin(5.0 * x)), 0.055) * temper_lip
    spatter_beads = smooth(0.80, 0.945, soft_noise(seed + 23, size, 14.0, 2.1)) * seam_halo
    weld_pits = smooth(0.78, 0.93, soft_noise(seed + 53, size, 19.0, 2.5)) * seam_core

    sheet_height = (
        0.22 * np.sin(1.7 * x - 1.1 * y)
        + 0.16 * np.cos(2.1 * y + 0.5 * x)
        + 0.58 * heat_zone
        + 0.84 * seam_core
        + 0.24 * weld_ripples
    ).astype(np.float32)
    height = blur(sheet_height, 1.4)
    light_a = smooth(-0.16, 0.72, normal_light(height, (0.63, -0.32, 0.71)))
    light_b = smooth(-0.16, 0.72, normal_light(height, (-0.55, 0.45, 0.71)))
    # Thin-oxide order reverses across the weld shoulders under the opposing
    # view.  Signed distance and light jointly transfer palette ownership.
    heat_order_b = unit(
        0.40 * heat_zone
        + 0.26 * (1.0 - along)
        + 0.22 * light_b
        + 0.12 * smooth(-0.18, 0.18, signed_near)
    )
    oxide_color_b = palette_ramp(
        heat_order_b,
        ((0.08, 0.20, 0.38), (0.04, 0.72, 0.94), (0.40, 0.12, 1.00), (1.00, 0.08, 0.62), (1.00, 0.42, 0.06), (1.00, 0.94, 0.70)),
    )

    metal_ground = np.empty((size, size, 3), np.float32)
    metal_ground[:] = (0.045, 0.060, 0.082)
    metal_ground += (0.08 * smooth(-1.0, 1.0, 0.75 * x - 0.25 * y))[..., None] * np.asarray((0.58, 0.63, 0.70), np.float32)
    paint_a = _mix(metal_ground, oxide_color, np.clip(0.20 * cooling_zone + 0.82 * heat_zone * (0.42 + 0.64 * light_a), 0.0, 0.94))
    paint_b = _mix(
        metal_ground,
        oxide_color_b,
        np.clip(0.16 * cooling_zone + 0.92 * heat_zone * (0.24 + 0.92 * light_b) + 0.24 * temper_lip, 0.0, 0.96),
    )
    hot = np.clip(seam_core + 0.58 * weld_ripples + 0.52 * spatter_beads + 0.40 * cooling_ticks, 0.0, 1.0)
    white = np.ones_like(paint_a) * np.asarray((1.0, 0.90, 0.78), np.float32)
    paint_a = _mix(paint_a, white, 0.78 * hot * (0.34 + 0.66 * light_a))
    cool_white = np.ones_like(paint_b) * np.asarray((0.82, 0.94, 1.00), np.float32)
    paint_b = _mix(paint_b, cool_white, 0.86 * hot * smooth(0.16, 0.78, light_b))

    base_grade = smooth(-1.0, 1.0, 0.62 * x - 0.38 * y)
    metal = unit(0.32 + 0.34 * base_grade + 0.46 * seam_core + 0.30 * weld_ripples + 0.36 * spatter_beads - 0.20 * heat_checks)
    rough = unit(0.10 + 0.54 * weld_ripples + 0.62 * heat_checks + 0.48 * weld_pits + 0.26 * brushed_strokes + 0.16 * cooling_zone)
    coat = unit(0.08 + 0.62 * heat_zone + 0.52 * temper_lip + 0.30 * cooling_zone - 0.55 * weld_pits - 0.44 * heat_checks)
    spec = pack_physical(
        metal,
        rough,
        coat,
        m_cuts=(0.07, 0.15, 0.24, 0.34, 0.45, 0.57, 0.69, 0.81, 0.92),
        r_cuts=(0.065, 0.13, 0.21, 0.31, 0.42, 0.54, 0.67, 0.81, 0.93),
        c_cuts=(0.055, 0.12, 0.21, 0.32, 0.44, 0.57, 0.70, 0.83, 0.94),
    )
    return finish(
        started,
        FINISH_ID,
        DISPLAY_NAME,
        paint_a,
        paint_b,
        spec,
        "one curved titanium body sheet carrying three broad turbo-temper zones, anodized oxidation order, and hot weld seams",
        {
            "M": "the titanium body remains conductive, strongest at weld cores, solidified ripples, and spatter beads",
            "R": "weld pits, heat checks, cooling ticks, and brushed damage roughen the oxide sheet",
            "Cc": "smooth anodized heat zones and temper lips retain optical clear while pits and fractured welds break it",
        },
    )
