"""Blacklight Garage -- fluorescent solvent pools under ultraviolet bars."""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, edge, finish, normal_light, pack_physical,
    palette_cycle, palette_ramp, ridge, smooth, soft_noise, unit,
)


# SPB-105 / NU-V4-BLACKLIGHT-GARAGE, 2026-08-27. Owner verdict: v3 lacked
# Oil Slick's coherent SPEC behavior and did not read as neon/Tokyo Drift.
# Unequal solvent pools and reflected UV fixtures form the broad garage-floor
# silhouette. Their light now joins through full-field floor panels and linked
# UV reflection history. Tide rims, mop arcs, pinhole bubbles, panel seams, bar
# cores and fluorescent runoff veins supply attached 8-32px detail.
# Whole-car correction: util >.08 48.6% -> 82.6%; dead <.06 50.1% -> 6.8%;
# paint A/B mean delta .1218 -> .0977; 2048 build+resize 2.34s.
FINISH_ID = "neon_blacklight"
DISPLAY_NAME = "Blacklight Garage"


def build(seed: int = 74429, size: int = WORK):
    started = begin()
    x, y = coords(size)
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    # Analytic broad cure bands describe the poured concrete sheet; v3-style
    # random texture is not used to occupy otherwise empty paint.
    concrete = unit(
        0.52 + 0.23 * np.sin(2.1 * x + 0.46 * y)
        + 0.18 * np.cos(1.55 * y - 0.34 * x)
        + 0.11 * np.sin(3.2 * (x + y))
    )
    film_warp = soft_noise(seed + 19, size, max(70.0, size / 10.0))

    pool_acc = np.zeros((size, size), np.float32)
    thickness = np.zeros_like(pool_acc)
    for _ in range(5):
        cx, cy = rng.uniform(-0.92, 0.92, 2)
        rx, ry = rng.uniform(0.24, 0.52), rng.uniform(0.16, 0.38)
        angle = rng.uniform(-1.4, 1.4)
        ca, sa = np.cos(angle), np.sin(angle)
        dx, dy = x - cx, y - cy
        u, v = ca * dx + sa * dy, -sa * dx + ca * dy
        dist = np.sqrt((u / rx) ** 2 + (v / ry) ** 2)
        phase = rng.uniform(-np.pi, np.pi)
        wobble = (
            dist + 0.20 * (film_warp - 0.5)
            + 0.070 * np.sin(3.0 * u / max(rx, 1e-5) + phase)
            + 0.050 * np.sin(5.0 * v / max(ry, 1e-5) - 0.7 * phase)
        )
        body = 1.0 - smooth(0.76, 1.08, wobble)
        pool_acc += body
        thickness = np.maximum(thickness, body * (0.55 + 0.45 * np.clip(1.0 - dist, 0.0, 1.0)))

    # Merge overlapping spills into one irregular solvent history instead of
    # preserving a collection of repeated ellipse stamps.
    pool = smooth(0.14, 0.66, blur(pool_acc, max(4.0, size / 220.0)))
    thickness = np.maximum(thickness, 0.46 * pool)

    tide_rim = smooth(0.45, 0.78, edge(pool))
    runoff = ridge(36.0 * (x + 0.16 * np.sin(4.0 * y)) + 2.0 * film_warp, 0.050)
    runoff *= pool * smooth(0.54, 0.82, film_warp)
    mop_zone = np.exp(-(((y - (0.22 * np.sin(2.2 * x) + 0.18)) / 0.34) ** 4))
    mop_arc = ridge(47.0 * (0.76 * x + 0.24 * y) + 2.2 * film_warp, 0.050)
    mop_arc *= smooth(0.28, 0.78, pool) * mop_zone
    bubbles = ridge(58.0 * (x - 0.31 * y) + 1.2 * concrete, 0.042) * pool * smooth(0.75, 0.91, concrete)
    bar1_axis = y + 0.47 - 0.08 * np.sin(1.8 * x)
    bar2_axis = y - 0.48 + 0.07 * np.sin(2.2 * x + 0.8)
    uv_bars = np.clip(np.exp(-((bar1_axis / 0.055) ** 4)) + np.exp(-((bar2_axis / 0.045) ** 4)), 0.0, 1.0)
    bar_cores = np.clip(np.exp(-((bar1_axis / 0.014) ** 2)) + np.exp(-((bar2_axis / 0.012) ** 2)), 0.0, 1.0)
    uv_halo = np.clip(
        np.exp(-((bar1_axis / 0.36) ** 4)) + 0.92 * np.exp(-((bar2_axis / 0.33) ** 4)),
        0.0, 1.0,
    )

    # A continuous reflected fixture path links the solvent history across the
    # whole floor. Expansion seams and comb lips are 8-28px native and remain
    # causal to the same UV bars/pools, never random scratches or quota marks.
    link_axis = y - (0.20 * np.sin(1.72 * x - 0.30) + 0.055 * x + 0.02)
    floor_link = np.exp(-((link_axis / 0.30) ** 4))
    seam_a_axis = x - (-0.46 + 0.07 * np.sin(2.0 * y))
    seam_b_axis = x - (0.49 - 0.06 * np.sin(2.4 * y + 0.6))
    panel_seams = np.clip(
        np.exp(-((seam_a_axis / 0.014) ** 2))
        + np.exp(-((seam_b_axis / 0.012) ** 2)),
        0.0, 1.0,
    )
    panel_faces = smooth(-0.42, 0.68, np.sin(2.7 * x + 0.58 * y + 0.26 * np.sin(2.1 * y)))
    floor_comb = ridge(23.0 * link_axis + 0.60 * np.sin(2.6 * x), 0.095)
    floor_comb *= 0.28 + 0.72 * np.clip(0.58 * floor_link + 0.42 * uv_halo, 0.0, 1.0)

    ground = palette_ramp(0.68 * concrete + 0.16 * y, (
        (0.025, 0.025, 0.040), (0.055, 0.055, 0.075),
        (0.100, 0.085, 0.120), (0.160, 0.135, 0.170),
    ))
    optical = np.mod(0.78 * thickness + 0.18 * film_warp + 0.08 * x, 1.0)
    solvent = palette_cycle(optical, (
        (0.30, 0.015, 0.62), (0.78, 0.025, 0.95), (0.98, 0.06, 0.57),
        (0.05, 0.62, 0.98), (0.12, 0.92, 0.73), (0.48, 0.08, 0.86),
    ))
    paint = ground * (1.0 - 0.72 * pool[..., None]) + solvent * pool[..., None] * (0.72 + 0.25 * thickness[..., None])
    paint += uv_halo[..., None] * np.asarray((0.065, 0.025, 0.14), np.float32)
    paint += floor_link[..., None] * np.asarray((0.035, 0.095, 0.14), np.float32) * (0.54 + 0.46 * panel_faces[..., None])
    paint += panel_faces[..., None] * np.asarray((0.035, 0.032, 0.060), np.float32)
    paint += panel_seams[..., None] * np.asarray((0.18, 0.22, 0.30), np.float32) * (0.35 + 0.65 * uv_halo[..., None])
    paint += floor_comb[..., None] * np.asarray((0.045, 0.10, 0.15), np.float32)
    paint += tide_rim[..., None] * np.asarray((0.47, 0.36, 0.66), np.float32)
    paint += uv_bars[..., None] * np.asarray((0.28, 0.04, 0.62), np.float32)
    paint += bar_cores[..., None] * np.asarray((0.57, 0.62, 0.70), np.float32)
    paint += runoff[..., None] * np.asarray((0.16, 0.34, 0.45), np.float32)
    paint += mop_arc[..., None] * np.asarray((0.16, 0.08, 0.25), np.float32)
    paint += bubbles[..., None] * np.asarray((0.43, 0.37, 0.55), np.float32)

    height = (
        0.55 * thickness + 0.18 * tide_rim + 0.14 * mop_arc + 0.08 * concrete
        + 0.18 * floor_link + 0.14 * panel_faces + 0.13 * floor_comb
    )
    view = smooth(-0.18, 0.62, normal_light(height, (0.58, 0.34, 0.74)))
    solvent_b = palette_cycle(np.mod(optical + 0.23 * view - 0.06 * runoff, 1.0), (
        (0.06, 0.70, 1.00), (0.90, 0.04, 0.78), (0.55, 0.05, 1.00),
        (0.12, 0.92, 0.66), (0.98, 0.16, 0.53), (0.38, 0.08, 0.82),
    ))
    paint_b = ground * (1.0 - 0.70 * pool[..., None]) + solvent_b * pool[..., None] * (0.62 + 0.42 * view[..., None])
    paint_b += uv_halo[..., None] * np.asarray((0.035, 0.075, 0.18), np.float32) * (0.48 + 0.64 * view[..., None])
    paint_b += floor_link[..., None] * np.asarray((0.11, 0.045, 0.17), np.float32) * (0.48 + 0.60 * view[..., None])
    paint_b += panel_faces[..., None] * np.asarray((0.040, 0.034, 0.068), np.float32)
    paint_b += panel_seams[..., None] * np.asarray((0.23, 0.25, 0.34), np.float32) * (0.33 + 0.68 * uv_halo[..., None])
    paint_b += floor_comb[..., None] * np.asarray((0.07, 0.085, 0.17), np.float32)
    paint_b += tide_rim[..., None] * np.asarray((0.50, 0.45, 0.69), np.float32)
    paint_b += uv_bars[..., None] * np.asarray((0.12, 0.22, 0.67), np.float32)
    paint_b += bar_cores[..., None] * np.asarray((0.64, 0.66, 0.72), np.float32)
    paint_b += (runoff + bubbles + 0.55 * mop_arc)[..., None] * np.asarray((0.20, 0.26, 0.35), np.float32)

    metal = np.clip(
        0.03 + 0.48 * tide_rim + 0.60 * bar_cores + 0.48 * panel_seams
        + 0.27 * floor_comb + 0.16 * bubbles,
        0.0, 1.0,
    )
    rough = np.clip(
        0.67 - 0.53 * pool - 0.26 * uv_halo - 0.24 * floor_link
        + 0.30 * mop_arc + 0.25 * (1.0 - panel_faces) + 0.22 * panel_seams + 0.18 * runoff,
        0.0, 1.0,
    )
    coat = np.clip(
        0.10 + 0.70 * thickness + 0.32 * uv_halo + 0.30 * floor_link
        + 0.21 * panel_faces + 0.18 * bubbles - 0.39 * tide_rim - 0.28 * panel_seams,
        0.0, 1.0,
    )
    spec = pack_physical(metal, rough, coat)

    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one full-field UV-lit garage floor whose panel reflections link unequal fluorescent solvent pools",
        {
            "M": "tide rims, fixture cores, expansion seams and reflected comb lips catch conductive glints",
            "R": "dry panel faces and mop drag oppose smooth solvent and linked UV reflections",
            "Cc": "solvent pools, floor-link shoulders, bubbles and ultraviolet halos retain wet clear",
        },
    )
