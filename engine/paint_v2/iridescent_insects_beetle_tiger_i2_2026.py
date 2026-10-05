"""Tiger Beetle Velocity I2 — feature-owned puncta/maculation material map.

SPB-105 / Finish Identity Law / owner 2026-09-01: Tiger Beetle was explicitly
named among cards with near-identical spec maps.  Its I1 copper/ivory velocity
paint is distinctive and remains the accepted carrier; only the generic
f0/f1/f2-dominated M/R/Cc is replaced.  Metallic now belongs to puncta lips and
compression teeth, roughness to pit cores/seams and ivory maculation, and
clearcoat to puncta bowls/maculation edges.  No screen-space color wave is used.
"""
from __future__ import annotations

import numpy as np

from engine.paint_v2.iridescent_insects_beetle_tiger_i1_2026 import (
    _resize,
    _surface,
    paint_beetle_tiger_i1 as paint_beetle_tiger_i2,
)


def spec_beetle_tiger_i2(shape, seed, sm, base_m, base_r):
    pit, lip, core, seam, _f0, _f1, _f2, macula, macula_edge, teeth = _surface(seed + 9423)
    # Separate biological/process owners.  Values intentionally span many tiers
    # through mask intersections instead of one field recolored into RGB.
    lip_teeth = np.clip(lip * (.58 + .62 * teeth), 0, 1)
    pit_floor = np.clip(core * (1 - lip * .42), 0, 1)
    ivory_body = np.clip(macula * (1 - macula_edge * .52), 0, 1)
    ivory_lip = np.clip(macula_edge * (1 - macula * .28), 0, 1)
    compression = np.clip(teeth * (1 - macula) * (.45 + .55 * seam), 0, 1)

    m = 54 + lip * 92 + lip_teeth * 62 + compression * 74 + core * 34
    m += seam * 22 - ivory_body * 86 - ivory_lip * 28
    r = 42 + pit_floor * 104 + seam * 92 + ivory_body * 74
    r += macula_edge * 38 + compression * 44 - lip * 32 - teeth * 18
    cc = 24 + pit * 92 + ivory_lip * 118 + teeth * 64
    cc += lip * 42 + macula * 34 - seam * 28 - core * 18
    return (
        np.clip(_resize(np.clip(m * sm, 8, 236), shape), 8, 236),
        np.clip(_resize(np.clip(r, 12, 232), shape), 12, 232),
        np.clip(_resize(np.clip(cc, 6, 240), shape), 6, 240),
    )
