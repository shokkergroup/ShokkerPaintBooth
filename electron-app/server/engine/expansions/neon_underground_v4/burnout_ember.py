"""Burnout Ember -- tire-heat crescents feeding an underlit smoke wake."""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, edge, finish, normal_light, pack_physical,
    palette_cycle, palette_ramp, ridge, smooth, soft_noise, unit,
)


# SPB-105 / NU-V4-BURNOUT-EMBER, 2026-08-27. Owner verdict: v3 lacked
# Oil Slick's coherent SPEC behavior and did not read as neon/Tokyo Drift.
# Two unequal curved tire-heat tracks own the hero silhouette inside one
# full-field banked rubber/heat/smoke sheet. Tread cuts, molten shoulders, bank
# combs, smoke laminae, rubber tears, heat ripples and soot fissures remain
# subordinate 8-32px anatomy; no sparks or damage are added to fill darkness.
# Whole-car correction: util >.08 38.3% -> 76.2%; dead <.06 57.4% -> 14.0%;
# paint A/B mean delta .0498 -> .0942; 2048 build+resize 1.99s.
FINISH_ID = "neon_orange_hazard"
DISPLAY_NAME = "Burnout Ember"


def build(seed: int = 74531, size: int = WORK):
    started = begin()
    x, y = coords(size)
    char = soft_noise(seed + 7, size, max(42.0, size / 16.0), max(5.0, size / 175.0))

    ux, uy = x + 0.44, 1.18 * (y - 0.08)
    radius = np.sqrt(ux * ux + uy * uy)
    theta = np.arctan2(uy, ux)
    gate = smooth(-2.85, -2.30, theta) * (1.0 - smooth(1.82, 2.42, theta))
    track_a_axis = radius - (0.58 + 0.055 * np.sin(3.0 * theta))
    track_b_axis = radius - (1.02 + 0.070 * np.sin(2.0 * theta + 0.8))
    track_a = np.exp(-((track_a_axis / 0.095) ** 4)) * gate
    track_b = np.exp(-((track_b_axis / 0.082) ** 4)) * gate
    tracks = np.clip(track_a + track_b, 0.0, 1.0)
    core_a = np.exp(-((track_a_axis / 0.020) ** 2)) * gate
    core_b = np.exp(-((track_b_axis / 0.017) ** 2)) * gate
    shoulders = np.clip(blur(tracks, max(9.0, size / 100.0)) - 0.34 * tracks, 0.0, 1.0)

    wake_axis = y - (0.24 * np.sin(1.55 * x - 0.45) + 0.28 * x - 0.15)
    wake = np.exp(-((wake_axis / 0.28) ** 4)) * smooth(-0.98, 0.70, x)
    smoke = np.clip(0.68 * wake + 0.56 * blur(tracks, max(24.0, size / 38.0)), 0.0, 1.0)
    smoke *= 0.72 + 0.28 * char

    tread = ridge(44.0 * theta + 3.0 * radius + 1.8 * char, 0.060) * tracks
    rubber_tears = ridge(61.0 * (radius + 0.09 * np.sin(5.0 * theta)) + 1.3 * char, 0.045)
    rubber_tears *= tracks * smooth(0.60, 0.87, char)
    ember = ridge(73.0 * (0.68 * x - 0.73 * y) + 2.2 * char, 0.035)
    ember *= smooth(0.35, 0.82, smoke) * smooth(0.73, 0.92, char)
    heat_ripple = ridge(25.0 * (y + 0.18 * np.sin(5.0 * x)) + 1.4 * char, 0.055) * smoke
    soot_fissure = ridge(52.0 * (x + 0.24 * y) - 1.8 * char, 0.040) * tracks * smooth(0.66, 0.90, char)

    # The same track radii and smoke axis continue through the surrounding
    # elastomer as banked heat history. Broad panels provide full-field material
    # ownership; 9-26px native comb/lamination lips expose their physical flow.
    track_transport = np.maximum(
        np.exp(-((track_a_axis / 0.58) ** 2)),
        np.exp(-((track_b_axis / 0.62) ** 2)),
    ) * (0.58 + 0.42 * gate)
    smoke_sheet = np.exp(-((wake_axis / 0.72) ** 4))
    full_energy = np.clip(0.62 * track_transport + 0.54 * smoke_sheet, 0.0, 1.0)
    bank_phase = radius / 0.31 - 0.34 * theta + 0.11 * np.sin(2.5 * theta)
    bank_panels = smooth(-0.46, 0.68, np.sin(2.0 * np.pi * bank_phase))
    bank_comb = ridge(radius / 0.052 - 0.22 * theta, 0.15) * (0.30 + 0.70 * full_energy)
    smoke_lamina = ridge(21.0 * wake_axis + 0.58 * np.sin(3.0 * x), 0.095)
    smoke_lamina *= 0.28 + 0.72 * smoke_sheet

    ground = palette_ramp(0.60 * char + 0.16 * y, (
        (0.012, 0.009, 0.012), (0.040, 0.025, 0.028),
        (0.085, 0.040, 0.035), (0.13, 0.055, 0.045),
    ))
    heat_phase = np.mod(0.58 * tracks + 0.20 * shoulders + 0.18 * theta / np.pi + 0.12 * char, 1.0)
    heat_color = palette_cycle(heat_phase, (
        (0.92, 0.045, 0.015), (1.00, 0.25, 0.015), (1.00, 0.72, 0.08),
        (0.98, 0.05, 0.19), (0.66, 0.02, 0.28),
    ))
    smoke_color = palette_ramp(smoke, ((0.10, 0.025, 0.035), (0.42, 0.035, 0.075), (0.76, 0.09, 0.055), (0.95, 0.26, 0.08)))
    bank_color = palette_ramp(0.56 * bank_panels + 0.28 * full_energy, (
        (0.045, 0.020, 0.024), (0.12, 0.032, 0.030),
        (0.24, 0.055, 0.035), (0.38, 0.10, 0.045),
    ))
    paint = ground * (1.0 - 0.48 * smoke[..., None]) + smoke_color * smoke[..., None] * 0.60
    paint += bank_color * full_energy[..., None] * (0.56 + 0.24 * bank_panels[..., None])
    paint += bank_panels[..., None] * np.asarray((0.055, 0.035, 0.040), np.float32)
    paint += bank_comb[..., None] * np.asarray((0.15, 0.065, 0.035), np.float32) * (0.36 + 0.64 * full_energy[..., None])
    paint += smoke_lamina[..., None] * np.asarray((0.075, 0.038, 0.055), np.float32) * (0.34 + 0.66 * smoke_sheet[..., None])
    paint = paint * (1.0 - 0.77 * tracks[..., None]) + heat_color * tracks[..., None] * 0.96
    paint += (core_a + core_b)[..., None] * np.asarray((0.62, 0.52, 0.32), np.float32)
    paint += shoulders[..., None] * np.asarray((0.30, 0.06, 0.04), np.float32)
    paint += tread[..., None] * np.asarray((0.27, 0.15, 0.06), np.float32)
    paint += ember[..., None] * np.asarray((0.88, 0.58, 0.18), np.float32)
    paint += heat_ripple[..., None] * np.asarray((0.13, 0.035, 0.06), np.float32)
    paint -= (rubber_tears + soot_fissure)[..., None] * np.asarray((0.15, 0.08, 0.07), np.float32)

    height = (
        0.50 * tracks + 0.20 * shoulders + 0.15 * smoke + 0.12 * heat_ripple
        + 0.19 * full_energy + 0.15 * bank_panels + 0.11 * smoke_lamina
    )
    view = smooth(-0.15, 0.62, normal_light(height, (-0.55, 0.35, 0.76)))
    heat_b = palette_cycle(np.mod(heat_phase + 0.21 * view + 0.08 * tread, 1.0), (
        (1.00, 0.60, 0.08), (0.98, 0.13, 0.04), (0.77, 0.02, 0.30),
        (0.98, 0.04, 0.13), (1.00, 0.35, 0.03),
    ))
    paint_b = ground * (1.0 - 0.46 * smoke[..., None]) + smoke_color * smoke[..., None] * (0.42 + 0.34 * view[..., None])
    bank_b = palette_ramp(np.clip(0.43 * bank_panels + 0.30 * full_energy + 0.27 * view, 0.0, 1.0), (
        (0.055, 0.018, 0.034), (0.18, 0.032, 0.065),
        (0.34, 0.070, 0.038), (0.52, 0.20, 0.045),
    ))
    paint_b += bank_b * full_energy[..., None] * (0.50 + 0.34 * view[..., None])
    paint_b += bank_panels[..., None] * np.asarray((0.065, 0.030, 0.055), np.float32)
    paint_b += bank_comb[..., None] * np.asarray((0.18, 0.085, 0.035), np.float32) * (0.32 + 0.66 * view[..., None])
    paint_b += smoke_lamina[..., None] * np.asarray((0.085, 0.032, 0.075), np.float32) * (0.30 + 0.66 * view[..., None])
    paint_b = paint_b * (1.0 - 0.76 * tracks[..., None]) + heat_b * tracks[..., None] * (0.68 + 0.40 * view[..., None])
    paint_b += (core_a + core_b + 0.55 * ember)[..., None] * np.asarray((0.67, 0.56, 0.34), np.float32)
    paint_b += (shoulders + 0.54 * tread + 0.48 * heat_ripple)[..., None] * np.asarray((0.20, 0.055, 0.055), np.float32)
    paint_b -= (rubber_tears + soot_fissure)[..., None] * np.asarray((0.13, 0.07, 0.06), np.float32)

    metal = np.clip(
        0.04 + 0.66 * (core_a + core_b) + 0.34 * ember + 0.23 * tread
        + 0.28 * bank_comb + 0.17 * shoulders,
        0.0, 1.0,
    )
    rough = np.clip(
        0.32 + 0.39 * smoke + 0.30 * smoke_sheet + 0.33 * rubber_tears
        + 0.31 * soot_fissure + 0.22 * tread + 0.24 * smoke_lamina
        + 0.18 * (1.0 - bank_panels) - 0.38 * tracks - 0.18 * full_energy,
        0.0, 1.0,
    )
    coat = np.clip(
        0.12 + 0.48 * shoulders + 0.39 * tracks + 0.30 * full_energy
        + 0.24 * bank_panels + 0.19 * heat_ripple - 0.37 * bank_comb
        - 0.44 * rubber_tears - 0.29 * ember,
        0.0, 1.0,
    )
    spec = pack_physical(metal, rough, coat)

    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one full-field banked elastomer sheet carrying twin tire-heat crescents through a connected smoke wake",
        {
            "M": "white-hot track cores, bank-comb lips, fused tread and incandescent ember fragments",
            "R": "smoke sheets, laminae, torn rubber, soot fissures and tread cuts remain rough",
            "Cc": "heat-glazed bank panels, track bodies and molten shoulders retain clear",
        },
    )
