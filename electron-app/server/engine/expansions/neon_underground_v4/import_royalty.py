"""Import Royalty -- layered razor-cut tuner vinyl with prismatic lips."""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, blur, coords, edge, finish, normal_light, pack_physical,
    palette_cycle, palette_ramp, ridge, smooth, soft_noise, unit,
)


# SPB-105 / NU-V4-IMPORT-ROYALTY, 2026-08-27. Owner verdict: v3 lacked
# Oil Slick's coherent SPEC behavior and did not read as neon/Tokyo Drift.
# Broad overlapping razor-vinyl slashes own this thumbnail silhouette. Attached
# 8-32px anatomy comprises prism lips, cut seams, squeegee ribs, trapped bubbles,
# adhesive shadows and chipped foil tips.
FINISH_ID = "neon_pink_blaze"
DISPLAY_NAME = "Import Royalty"


def _slash(u: np.ndarray, v: np.ndarray, center: float, width: float, lo: float, hi: float) -> np.ndarray:
    body = np.exp(-(((u - center) / width) ** 8))
    gate = smooth(lo - 0.16, lo + 0.04, v) * (1.0 - smooth(hi - 0.04, hi + 0.16, v))
    return body * gate


def build(seed: int = 74317, size: int = WORK):
    started = begin()
    x, y = coords(size)
    film = soft_noise(seed + 13, size, max(46.0, size / 15.0), max(5.0, size / 175.0))

    u = 0.79 * x + 0.61 * y + 0.075 * np.sin(3.6 * y)
    v = -0.61 * x + 0.79 * y
    p1 = _slash(u, v, -0.58, 0.22, -1.35, 0.34)
    p2 = _slash(u, v, -0.05, 0.29, -0.74, 1.32)
    p3 = _slash(u, v, 0.55, 0.19, -1.30, 0.76)
    # Counter-slash prevents a stripe-sheet read and creates one layered wrap.
    cu = 0.91 * x - 0.42 * y
    cv = 0.42 * x + 0.91 * y
    p4 = _slash(cu, cv, 0.08, 0.16, -0.98, 0.98) * (1.0 - 0.55 * p2)
    panels = np.clip(p1 + p2 + p3 + p4, 0.0, 1.0)

    lip1, lip2, lip3, lip4 = edge(p1), edge(p2), edge(p3), edge(p4)
    lips = np.clip(lip1 + lip2 + lip3 + lip4, 0.0, 1.0)
    seam_shadow = np.clip(blur(lips, max(5.0, size / 190.0)) - 0.45 * lips, 0.0, 1.0)
    squeegee = ridge(54.0 * v + 2.4 * film, 0.060) * panels * smooth(0.42, 0.84, film)
    bubble_field = ridge(29.0 * (u + 0.13 * np.sin(5.0 * v)) + 1.1 * film, 0.045)
    bubbles = bubble_field * panels * smooth(0.72, 0.91, film)
    chip = ridge(67.0 * (u - 0.21 * v) + 0.5, 0.040) * lips * smooth(0.55, 0.84, film)

    ground = palette_ramp(film, (
        (0.012, 0.008, 0.030), (0.055, 0.010, 0.082),
        (0.105, 0.018, 0.13), (0.17, 0.025, 0.15),
    ))
    phase = np.mod(0.34 * u + 0.17 * v + 0.24 * film, 1.0)
    wrap = palette_cycle(phase, (
        (0.98, 0.04, 0.55), (0.72, 0.03, 0.98), (0.08, 0.60, 0.96),
        (0.98, 0.18, 0.69), (1.00, 0.48, 0.18),
    ))
    paint = ground * (1.0 - 0.63 * panels[..., None]) + wrap * panels[..., None] * (0.80 + 0.20 * film[..., None])
    paint += lips[..., None] * np.asarray((0.64, 0.72, 0.66), np.float32)
    paint += squeegee[..., None] * np.asarray((0.20, 0.045, 0.25), np.float32)
    paint += bubbles[..., None] * np.asarray((0.26, 0.22, 0.32), np.float32)
    paint += chip[..., None] * np.asarray((0.74, 0.48, 0.22), np.float32)
    paint -= seam_shadow[..., None] * np.asarray((0.12, 0.08, 0.14), np.float32)

    height = 0.44 * panels + 0.23 * film + 0.18 * squeegee + 0.30 * bubbles
    view = smooth(-0.18, 0.62, normal_light(height, (0.64, -0.25, 0.72)))
    phase_b = np.mod(phase + 0.20 * view - 0.08 * panels, 1.0)
    wrap_b = palette_cycle(phase_b, (
        (0.08, 0.68, 1.00), (0.96, 0.08, 0.70), (0.80, 0.06, 1.00),
        (1.00, 0.50, 0.16), (0.98, 0.16, 0.48),
    ))
    paint_b = ground * (1.0 - 0.62 * panels[..., None]) + wrap_b * panels[..., None] * (0.68 + 0.42 * view[..., None])
    paint_b += lips[..., None] * np.asarray((0.70, 0.78, 0.70), np.float32) * (0.62 + 0.45 * view[..., None])
    paint_b += (0.68 * squeegee + bubbles)[..., None] * np.asarray((0.17, 0.10, 0.24), np.float32)
    paint_b += chip[..., None] * np.asarray((0.60, 0.55, 0.30), np.float32)
    paint_b -= seam_shadow[..., None] * np.asarray((0.11, 0.07, 0.13), np.float32)

    metal = np.clip(0.06 + 0.72 * lips + 0.51 * chip + 0.18 * panels + 0.12 * bubbles, 0.0, 1.0)
    rough = np.clip(0.29 + 0.16 * film + 0.42 * seam_shadow + 0.35 * squeegee + 0.28 * chip - 0.31 * panels - 0.22 * bubbles, 0.0, 1.0)
    coat = np.clip(0.20 + 0.64 * panels + 0.30 * bubbles - 0.50 * lips - 0.32 * chip + 0.10 * film, 0.0, 1.0)
    # Vinyl roughness lives in a narrower physical envelope than metal/coat;
    # fixed cuts expose adhesive, panel, squeegee and chip states without the
    # equal-population quantile packing that collapsed v3 into spec confetti.
    spec = pack_physical(
        metal, rough, coat,
        r_cuts=(0.05, 0.12, 0.20, 0.29, 0.39, 0.50, 0.62, 0.75, 0.87),
    )

    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one layered tuner-wrap skin built from four unequal razor-cut vinyl slashes",
        {
            "M": "prismatic cut lips, chipped foil tips and compressed bubble crowns",
            "R": "adhesive seams, squeegee ribs and chipped edges interrupt polished vinyl",
            "Cc": "intact broad vinyl panels and trapped-bubble domes hold glossy clear",
        },
    )
