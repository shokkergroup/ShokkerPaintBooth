"""Afterburn Chrome: heat-shifted chrome with physical optical-order travel.

SPB-105 / NU-V4-2 / 2026-08-27. Owner verdict: v3 lacked Oil Slick's
coherent SPEC mechanics and did not read as neon, Tokyo Drift, or Fast &
Furious. This finish transfers Oil Slick's causal lesson into a directional
chrome/heat carrier, with its own topology and a true alternate view.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, FinishResult, begin, blur, coords, edge, finish, normal_light,
    pack_physical, palette_cycle, ridge, smooth, soft_noise, unit,
)


FINISH_ID = "neon_rainbow_tube"
DISPLAY_NAME = "Afterburn Chrome"
DEFAULT_SEED = 0xA67E2B4E


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    """Build one heat-worked chrome sheet with angle-dependent oxidation."""
    started = begin()
    size = int(size)
    x, y = coords(size)
    scale = size / float(WORK)
    texture = soft_noise(seed ^ 0xC4A0, size, 62.0 * scale, 7.5 * scale)

    # Directional heat advection creates broad flame-shaped chrome territories;
    # no independent marks are pasted over a neutral background.
    qx = x + 0.105 * np.sin(2.7 * y + 0.45 * np.sin(3.1 * x))
    qy = y + 0.070 * np.sin(3.4 * x - 0.35 * np.sin(2.3 * y))
    thickness = (
        0.49 + 0.15 * qx - 0.08 * qy
        + 0.15 * np.sin(4.6 * qx + 1.5 * qy)
        + 0.085 * np.sin(8.7 * qy - 2.6 * qx)
        + 0.035 * np.sin(18.0 * qx + 11.0 * qy)
    )
    film = unit(thickness)
    gy, gx = np.gradient(thickness)
    compression = unit(np.sqrt(gx * gx + gy * gy))
    shock = np.clip(edge(compression) * smooth(0.25, 0.80, compression), 0.0, 1.0)
    cool_chrome = 1.0 - smooth(0.35, 0.63, film)
    heat_zone = smooth(0.28, 0.78, film) * (1.0 - smooth(0.88, 1.0, film))
    afterburn = smooth(0.66, 0.92, film)
    thermal_lip = np.clip(edge(film) * (0.45 + 0.55 * compression), 0.0, 1.0)
    oxide_shoulders = ridge(7.5 * film + 0.42 * compression, 0.15) * heat_zone

    # SPB-105 / NU-V4-2G / owner single-gate verdict: preserve the broad
    # heat-chrome territories and their Oil Slick A/B witness, but give the
    # same advected film enough car-readable fine paint anatomy.  Calm chrome,
    # order edges and compressed shear receive mutually weighted line families
    # derived from film/compression; this is one worked sheet, not crosshatch,
    # noise, grain, particles or a second carrier.  Each ridge is 8-32px native.
    # Direct native movement: fine/residual .003910/.002737 -> .004418/.003093;
    # saturation .439744 -> .543740; A/B .145061 -> .193150.  WORK build +
    # 2048 delivery median 1.77s; M/R/Cc std 69.81/40.47/49.46, tiers 10/10/10.
    compression_gate = smooth(0.38, 0.64, compression)
    order_gate = smooth(0.16, 0.52, blur(thermal_lip, 6.0 * scale))
    brushed_lamellae = smooth(0.28, 0.54, ridge(
        44.0 * (qx + 0.12 * qy + 0.075 * film) + 0.24 * compression,
        0.25,
    ))
    brushed_lamellae *= (1.0 - compression_gate) * (1.0 - order_gate)
    order_edge_striations = smooth(0.28, 0.54, ridge(
        50.0 * (qx - 0.08 * qy + 0.105 * film) + 0.18 * compression,
        0.25,
    ))
    order_edge_striations *= order_gate * (1.0 - compression_gate)
    shear_hairs = smooth(0.28, 0.54, ridge(
        46.0 * (qy - 0.18 * qx + 0.090 * film) - 0.16 * compression,
        0.25,
    ))
    shear_hairs *= compression_gate
    weld_ripples = ridge(43.0 * (qy - 0.16 * qx) + 0.55 * texture, 0.10) * thermal_lip
    heat_fissures = ridge(57.0 * (qx - 0.28 * qy) + 1.2 * texture, 0.075) * shock
    oxide_pits = (
        ridge(61.0 * qx + 5.0 * qy, 0.085)
        * ridge(53.0 * qy - 4.0 * qx, 0.095)
        * afterburn * compression
    )
    height = unit(
        0.52 * film + 0.30 * compression + 0.18 * thermal_lip
        + 0.12 * oxide_shoulders + 0.08 * weld_ripples
        + 0.018 * brushed_lamellae + 0.022 * order_edge_striations
        + 0.026 * shear_hairs
    )

    def paint_view(travel: float, light_vec: tuple[float, float, float]) -> np.ndarray:
        light = normal_light(height, light_vec)
        exposure = np.clip((light + 0.55) / 1.55, 0.0, 1.0)
        optical = np.mod(
            2.55 * film + 0.20 * compression + 0.10 * oxide_shoulders
            + 0.030 * order_edge_striations + 0.025 * shear_hairs
            + travel * (0.46 + 0.54 * exposure),
            1.0,
        )
        spectral = palette_cycle(
            optical,
            ((0.04, 0.08, 0.15), (0.05, 0.36, 0.86), (0.38, 0.16, 0.92),
             (0.96, 0.12, 0.62), (1.00, 0.34, 0.04), (1.00, 0.78, 0.12),
             (0.18, 0.84, 0.88)),
        )
        paint = np.zeros((size, size, 3), np.float32)
        paint[:] = (0.010, 0.012, 0.018)
        chrome = np.asarray((0.48, 0.56, 0.66), np.float32)
        paint += chrome * (0.20 * cool_chrome * (0.48 + 0.52 * exposure))[..., None]
        paint += spectral * (heat_zone * (0.34 + 0.52 * exposure))[..., None]
        paint += np.asarray((1.00, 0.28, 0.03), np.float32) * (0.30 * afterburn)[..., None]
        paint += np.asarray((0.92, 0.98, 1.00), np.float32) * (0.28 * thermal_lip + 0.18 * weld_ripples)[..., None]
        paint += np.asarray((0.28, 0.62, 1.00), np.float32) * (0.15 * oxide_shoulders)[..., None]
        paint += np.asarray((0.64, 0.74, 0.88), np.float32) * (0.18 * brushed_lamellae)[..., None]
        paint += spectral * (0.17 * order_edge_striations * (0.36 + 0.64 * heat_zone))[..., None]
        paint += np.asarray((0.20, 0.74, 1.00), np.float32) * (
            0.14 * shear_hairs * (0.40 + 0.60 * cool_chrome)
        )[..., None]
        paint += np.asarray((1.00, 0.25, 0.055), np.float32) * (
            0.13 * shear_hairs * heat_zone
        )[..., None]
        paint *= 1.0 - 0.38 * heat_fissures[..., None] - 0.22 * oxide_pits[..., None]
        paint += blur(thermal_lip, 7.0 * scale)[..., None] * np.asarray((0.10, 0.04, 0.12), np.float32)
        neutral = (
            0.299 * paint[..., 0] + 0.587 * paint[..., 1] + 0.114 * paint[..., 2]
        )
        chroma_gain = 1.36 + 0.16 * heat_zone
        paint = neutral[..., None] + (paint - neutral[..., None]) * chroma_gain[..., None]
        return np.clip(paint, 0.0, 1.0)

    paint = paint_view(0.00, (0.51, -0.44, 0.74))
    paint_b = paint_view(0.34, (-0.60, 0.26, 0.75))

    # SPB-105 / NU-V4-2R / owner verdict: keep Oil Slick-grade material spread.
    # Chrome remains broadly conductive, but burnt pits and fissures now reach
    # genuinely exposed/oxidized low-metal states instead of compressing the
    # fixed physical ladder into its upper seven tiers. Native M movement:
    # std/tier 61.17/7 -> 70.69/10.
    metal = np.clip(
        0.24 + 0.62 * cool_chrome + 0.48 * thermal_lip + 0.36 * weld_ripples
        + 0.25 * afterburn - 0.74 * oxide_pits - 0.56 * heat_fissures
        + 0.07 * brushed_lamellae + 0.09 * order_edge_striations
        - 0.08 * shear_hairs - 0.18 * shock * heat_zone,
        0.0, 1.0,
    )
    rough = np.clip(
        0.08 + 0.20 * brushed_lamellae + 0.18 * order_edge_striations
        + 0.24 * shear_hairs + 0.58 * oxide_pits + 0.50 * heat_fissures
        + 0.36 * compression + 0.22 * shock - 0.30 * cool_chrome,
        0.0, 1.0,
    )
    coat = np.clip(
        0.18 + 0.62 * cool_chrome + 0.52 * oxide_shoulders + 0.30 * heat_zone
        + 0.06 * brushed_lamellae - 0.10 * order_edge_striations
        - 0.14 * shear_hairs - 0.66 * heat_fissures
        - 0.50 * oxide_pits - 0.24 * afterburn,
        0.0, 1.0,
    )
    spec = pack_physical(
        metal, rough, coat,
        m_cuts=(0.10, 0.20, 0.30, 0.41, 0.52, 0.63, 0.74, 0.84, 0.93),
        r_cuts=(0.07, 0.15, 0.24, 0.34, 0.45, 0.57, 0.69, 0.81, 0.91),
        c_cuts=(0.08, 0.17, 0.27, 0.38, 0.49, 0.60, 0.71, 0.82, 0.92),
    )
    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "directionally heat-worked chrome with broad oxidation territories, afterburn zones, thermal lips, 8-32px brushed lamellae, order-edge striations, shear hairs, weld ripples, heat fissures and oxide pits",
        {
            "M": "cool chrome, brushed lamellae, exposed order lips, weld faces and hot conductive substrate",
            "R": "worked lamellae, order-edge striations, shear hairs, oxide pits, heat fissures and shock",
            "Cc": "cool polished chrome and smooth optical shoulders, interrupted by order shear, burnt and fractured zones",
        },
    )
