"""Signglass Shatter -- broad broken phosphor-glass territories."""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, finish, normal_light, pack_physical,
    palette_cycle, palette_ramp, ridge, smooth, soft_noise, unit,
)


# SPB-105 / NU-V4-SIGNGLASS-SHATTER, 2026-08-27. Owner verdict: v3 lacked
# Oil Slick's coherent SPEC behavior and did not read as neon/Tokyo Drift.
# Eighteen unequal sign-glass territories establish a thumbnail-readable broken
# sheet. White phosphor rims, silver backing lips, dying interiors, getter soot,
# fork cracks and trapped gas beads provide attached 8-32px anatomy.
FINISH_ID = "neon2_sign_tubes"
DISPLAY_NAME = "Signglass Shatter"


def build(seed: int = 74777, size: int = WORK):
    started = begin()
    x, y = coords(size)
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    glass_noise = soft_noise(seed + 21, size, max(48.0, size / 14.0), max(5.0, size / 180.0))

    centers = rng.uniform(-1.08, 1.08, (18, 2)).astype(np.float32)
    centers[:4] = np.asarray(((-0.82, -0.70), (0.82, -0.72), (-0.78, 0.73), (0.80, 0.72)), np.float32)
    d1 = np.full((size, size), np.inf, np.float32)
    d2 = np.full_like(d1, np.inf)
    owner = np.zeros((size, size), np.int16)
    for index, (cx, cy) in enumerate(centers):
        anis = 0.82 + 0.35 * ((index * 0.61803398875) % 1.0)
        d = (x - cx) ** 2 + anis * (y - cy) ** 2
        take = d < d1
        d2 = np.where(take, d1, np.minimum(d2, d))
        d1 = np.where(take, d, d1)
        owner = np.where(take, index, owner)

    gap = np.maximum(np.sqrt(d2) - np.sqrt(d1), 0.0)
    rim = np.exp(-((gap / 0.026) ** 2))
    hot_rim = np.exp(-((gap / 0.010) ** 2))
    interior = smooth(0.020, 0.115, gap)

    alive_lut = np.ones(18, np.float32)
    alive_lut[rng.choice(18, 4, replace=False)] = 0.0
    alive = alive_lut[owner]
    phase_lut = rng.uniform(0.0, 1.0, 18).astype(np.float32)
    fade_lut = rng.uniform(0.46, 1.0, 18).astype(np.float32)
    phase = np.mod(phase_lut[owner] + 0.14 * glass_noise + 0.035 * x, 1.0)
    fade = fade_lut[owner] * (0.72 + 0.28 * glass_noise)
    live_interior = interior * alive
    dead = interior * (1.0 - alive)

    fork = ridge(43.0 * (0.72 * x + 0.69 * y) + 2.1 * glass_noise + owner * 0.17, 0.050)
    fork *= rim * smooth(0.52, 0.84, glass_noise)
    getter = ridge(31.0 * (x - 0.23 * y) + owner * 0.31, 0.060)
    getter *= live_interior * smooth(0.63, 0.88, glass_noise)
    gas_beads = ridge(67.0 * (x + 0.17 * y) + 1.4 * glass_noise, 0.038)
    gas_beads *= live_interior * smooth(0.77, 0.92, glass_noise)
    silver_lip = rim * smooth(0.30, 0.72, np.mod(owner * 0.37 + glass_noise, 1.0))

    ground = palette_ramp(glass_noise, (
        (0.008, 0.008, 0.017), (0.026, 0.018, 0.038),
        (0.055, 0.026, 0.065), (0.09, 0.04, 0.085),
    ))
    phosphor = palette_cycle(phase, (
        (1.00, 0.035, 0.30), (1.00, 0.08, 0.70), (0.62, 0.04, 1.00),
        (0.08, 0.62, 1.00), (0.04, 0.95, 0.75), (1.00, 0.18, 0.46),
    ))
    paint = ground * (1.0 - 0.78 * live_interior[..., None]) + phosphor * (live_interior * fade)[..., None] * 0.92
    paint += dead[..., None] * np.asarray((0.018, 0.022, 0.038), np.float32)
    paint += rim[..., None] * phosphor * np.asarray((0.34, 0.34, 0.40), np.float32)
    paint += hot_rim[..., None] * np.asarray((0.66, 0.70, 0.66), np.float32)
    paint += silver_lip[..., None] * np.asarray((0.37, 0.45, 0.48), np.float32)
    paint += gas_beads[..., None] * np.asarray((0.43, 0.46, 0.43), np.float32)
    paint -= (getter + 0.60 * fork)[..., None] * np.asarray((0.17, 0.09, 0.14), np.float32)

    height = 0.45 * live_interior + 0.32 * rim + 0.17 * gas_beads + 0.11 * phase
    view = smooth(-0.20, 0.64, normal_light(height, (0.64, -0.28, 0.72)))
    phosphor_b = palette_cycle(np.mod(phase + 0.20 * view - 0.07 * getter, 1.0), (
        (0.10, 0.70, 1.00), (0.85, 0.04, 0.95), (1.00, 0.05, 0.48),
        (1.00, 0.34, 0.08), (0.08, 0.90, 0.72), (0.75, 0.04, 0.77),
    ))
    paint_b = ground * (1.0 - 0.76 * live_interior[..., None]) + phosphor_b * live_interior[..., None] * fade[..., None] * (0.58 + 0.48 * view[..., None])
    paint_b += dead[..., None] * np.asarray((0.018, 0.023, 0.040), np.float32)
    paint_b += rim[..., None] * phosphor_b * 0.34
    paint_b += hot_rim[..., None] * np.asarray((0.70, 0.72, 0.68), np.float32)
    paint_b += (silver_lip + 0.62 * gas_beads)[..., None] * np.asarray((0.39, 0.48, 0.49), np.float32)
    paint_b -= (getter + 0.55 * fork)[..., None] * np.asarray((0.16, 0.08, 0.13), np.float32)

    metal = np.clip(0.05 + 0.72 * silver_lip + 0.47 * hot_rim + 0.26 * fork + 0.18 * gas_beads, 0.0, 1.0)
    rough = np.clip(0.22 + 0.56 * dead + 0.45 * fork + 0.38 * getter + 0.24 * rim - 0.25 * live_interior, 0.0, 1.0)
    coat = np.clip(0.08 + 0.77 * live_interior + 0.32 * gas_beads - 0.51 * rim - 0.35 * fork - 0.28 * getter, 0.0, 1.0)
    spec = pack_physical(metal, rough, coat)

    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one broken sign-glass sheet of eighteen unequal phosphor territories and four dead shards",
        {
            "M": "silver backing lips, white fracture rims and exposed gas-bead electrodes",
            "R": "missing glass, fork cracks and getter soot contrast intact polished interiors",
            "Cc": "live sign-glass territories and trapped gas domes retain clear away from rims",
        },
    )
