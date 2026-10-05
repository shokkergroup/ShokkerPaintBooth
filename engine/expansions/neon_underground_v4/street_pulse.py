"""Street Pulse -- crossing traffic-light rivers in wet midnight clear."""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, finish, normal_light, pack_physical,
    palette_ramp, ridge, smooth, soft_noise, unit,
)


# SPB-105 / NU-V4-STREET-PULSE, 2026-08-27. Owner verdict: v3 lacked
# Oil Slick's coherent SPEC behavior and did not read as neon/Tokyo Drift.
# This carrier is one full-field wet roadway sheet crossed by two continuous
# light rivers; lane combs and banked wet panels propagate their energy through
# every UV region. Fine rain ribs, emitter cores, broken tails, puddle lips and
# spray beads remain subordinate 8-32px anatomy, never filler texture.
# Whole-car correction: util >.08 45.9% -> 97.6%; dead <.06 18.3% -> 0.04%;
# paint A/B mean delta .0714 -> .0779; 2048 build+resize 1.40s.
FINISH_ID = "neon2_flow_tubes"
DISPLAY_NAME = "Street Pulse"


def build(seed: int = 74121, size: int = WORK):
    started = begin()
    x, y = coords(size)

    wet = soft_noise(seed + 11, size, max(34.0, size / 18.0), max(5.0, size / 150.0))
    camber = 0.52 + 0.25 * np.cos(1.45 * x - 0.65 * y) + 0.23 * wet

    red_axis = y - (0.37 * np.sin(2.05 * x + 0.42) - 0.18 * x - 0.20)
    cyan_axis = y - (-0.31 * np.sin(1.72 * x - 0.75) + 0.14 * x + 0.24)
    red_body = np.exp(-((red_axis / 0.165) ** 4))
    cyan_body = np.exp(-((cyan_axis / 0.155) ** 4))
    crossing = np.minimum(red_body, cyan_body)

    # 8-20px emitter/rain anatomy carried by the broad light rivers.
    fine_scale = max(34.0, 66.0 * 1024.0 / size)
    red_core = np.exp(-((red_axis / 0.020) ** 2))
    cyan_core = np.exp(-((cyan_axis / 0.018) ** 2))
    red_break = 0.48 + 0.52 * smooth(-0.25, 0.22, np.sin(fine_scale * x + 5.0 * wet))
    cyan_break = 0.50 + 0.50 * smooth(-0.18, 0.28, np.sin(fine_scale * (x + 0.17 * y) - 3.0 * wet))
    emitter_red = red_core * red_break
    emitter_cyan = cyan_core * cyan_break
    reflection_ribs = ridge(15.0 * y + 1.25 * np.sin(4.0 * x) + 0.8 * wet, 0.075)
    reflection_ribs *= np.clip(0.58 * red_body + 0.62 * cyan_body, 0.0, 1.0)
    rain = ridge(42.0 * (0.22 * x + y) + 1.5 * wet, 0.060)
    rain *= smooth(0.42, 0.78, wet) * np.clip(red_body + cyan_body + 0.24, 0.0, 1.0)
    puddle_lip = unit(np.abs(np.gradient(blur(wet, max(4.0, size / 180.0)), axis=0)))
    puddle_lip = smooth(0.62, 0.87, puddle_lip)

    # Parallel wet-lane histories continue around both traffic rivers. The
    # 9-24px native comb lips share the river axes, while their broad envelopes
    # merge into unequal road panels rather than ending in empty black paint.
    red_envelope = np.exp(-((red_axis / 0.86) ** 2))
    cyan_envelope = np.exp(-((cyan_axis / 0.82) ** 2))
    red_comb = ridge(red_axis / 0.052 + 0.42 * wet, 0.16) * (0.30 + 0.70 * red_envelope)
    cyan_comb = ridge(cyan_axis / 0.049 - 0.37 * wet, 0.16) * (0.30 + 0.70 * cyan_envelope)
    road_fold_phase = 0.72 * red_axis / 0.42 + 0.46 * cyan_axis / 0.55 + 0.16 * wet
    road_panels = smooth(-0.36, 0.72, np.sin(2.0 * np.pi * road_fold_phase))
    road_sheen = np.clip(0.42 * red_envelope + 0.45 * cyan_envelope + 0.26 * road_panels, 0.0, 1.0)

    road = palette_ramp(camber, ((0.008, 0.012, 0.030), (0.025, 0.045, 0.080), (0.075, 0.105, 0.145)))
    paint = road * (0.76 + 0.24 * wet[..., None])
    paint += road_sheen[..., None] * np.asarray((0.055, 0.075, 0.105), np.float32)
    paint += red_comb[..., None] * np.asarray((0.105, 0.018, 0.045), np.float32)
    paint += cyan_comb[..., None] * np.asarray((0.012, 0.075, 0.115), np.float32)
    paint += red_body[..., None] * np.asarray((0.70, 0.018, 0.13), np.float32)
    paint += cyan_body[..., None] * np.asarray((0.008, 0.50, 0.80), np.float32)
    paint += crossing[..., None] * np.asarray((0.39, 0.02, 0.63), np.float32)
    paint += emitter_red[..., None] * np.asarray((0.62, 0.42, 0.42), np.float32)
    paint += emitter_cyan[..., None] * np.asarray((0.50, 0.66, 0.62), np.float32)
    paint += reflection_ribs[..., None] * (
        red_body[..., None] * np.asarray((0.22, 0.025, 0.08), np.float32)
        + cyan_body[..., None] * np.asarray((0.01, 0.14, 0.24), np.float32)
    )
    paint += rain[..., None] * np.asarray((0.08, 0.16, 0.23), np.float32)
    paint += puddle_lip[..., None] * np.asarray((0.035, 0.075, 0.11), np.float32)

    height = (
        0.20 * camber + 0.44 * red_body + 0.41 * cyan_body
        + 0.12 * reflection_ribs + 0.14 * road_panels
        + 0.10 * red_comb + 0.09 * cyan_comb
    )
    light_a = normal_light(height, (-0.62, -0.20, 0.76))
    light_b = normal_light(height, (0.64, 0.12, 0.76))
    expose_a = smooth(-0.12, 0.58, light_a)
    expose_b = smooth(-0.12, 0.58, light_b)
    # Alternate view is owned by the two raised light rivers. Opposed normals
    # expose different interference-order shoulders, so red travels through
    # magenta/amber while cyan travels through teal/electric blue; the road is
    # not globally hue-rotated and the emitter topology remains fixed.
    red_order = np.clip(0.50 * expose_b + 0.30 * wet + 0.20 * reflection_ribs, 0.0, 1.0)
    cyan_order = np.clip(0.52 * expose_a + 0.28 * (1.0 - wet) + 0.20 * reflection_ribs, 0.0, 1.0)
    red_view = palette_ramp(red_order, (
        (0.42, 0.008, 0.25), (0.78, 0.018, 0.58),
        (1.00, 0.12, 0.42), (1.00, 0.50, 0.08),
    ))
    cyan_view = palette_ramp(cyan_order, (
        (0.005, 0.28, 0.60), (0.005, 0.72, 0.72),
        (0.10, 0.88, 1.00), (0.42, 0.32, 1.00),
    ))
    road_view = np.clip(0.62 + 0.24 * wet + 0.17 * smooth(-0.10, 0.62, light_b), 0.0, 1.0)
    paint_b = road * road_view[..., None]
    paint_b += road_sheen[..., None] * np.asarray((0.045, 0.080, 0.12), np.float32) * (
        0.52 + 0.62 * expose_b[..., None]
    )
    paint_b += red_comb[..., None] * np.asarray((0.13, 0.018, 0.075), np.float32) * (0.45 + 0.68 * expose_b[..., None])
    paint_b += cyan_comb[..., None] * np.asarray((0.012, 0.10, 0.14), np.float32) * (0.45 + 0.68 * expose_a[..., None])
    paint_b += red_body[..., None] * red_view * (0.58 + 0.62 * expose_b[..., None])
    paint_b += cyan_body[..., None] * cyan_view * (0.58 + 0.60 * expose_a[..., None])
    paint_b += crossing[..., None] * np.asarray((0.64, 0.10, 0.62), np.float32)
    paint_b += emitter_red[..., None] * np.asarray((0.72, 0.62, 0.59), np.float32)
    paint_b += emitter_cyan[..., None] * np.asarray((0.56, 0.72, 0.75), np.float32)
    paint_b += (reflection_ribs + 0.65 * rain)[..., None] * np.asarray((0.05, 0.13, 0.18), np.float32)

    metal = np.clip(
        0.04 + 0.72 * (emitter_red + emitter_cyan) + 0.25 * puddle_lip
        + 0.25 * (red_comb + cyan_comb) + 0.12 * rain,
        0.0, 1.0,
    )
    rough = np.clip(
        0.68 - 0.48 * wet - 0.38 * (red_body + cyan_body) - 0.21 * road_sheen
        + 0.29 * rain + 0.22 * puddle_lip + 0.18 * (red_comb + cyan_comb),
        0.0, 1.0,
    )
    coat = np.clip(
        0.14 + 0.58 * wet + 0.28 * (red_body + cyan_body) + 0.35 * road_sheen
        + 0.18 * road_panels - 0.28 * rain - 0.20 * (red_comb + cyan_comb) + 0.12 * crossing,
        0.0, 1.0,
    )
    spec = pack_physical(metal, rough, coat)

    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one full-field rain-wet roadway clear whose banked lane combs carry two opposed traffic-light rivers",
        {
            "M": "emitter cores, road-comb lips, puddle lips and rain-polished lane fragments",
            "R": "banked asphalt and rain cuts oppose the burnished rivers and wet panel sheen",
            "Cc": "wet road panels and continuous reflected-light rivers retain full-field clear",
        },
    )
