"""Ground Beetle Obsidian I2 — engraved-armor material correction.

SPB-105 / owner 2026-09-01, Finish Identity correction.  I1's oil-black
Carabid paint already has a unique polygon mesh, diffraction bars, pits,
continuous abrasion and buried crosses.  I2 preserves it and removes generic
macro waves from M/R/Cc.  Metal follows plates/gratings/crosses, roughness
follows pits/abrasion, and clearcoat follows mesh/mercury lips.
"""
from __future__ import annotations

import numpy as np

from engine.paint_v2.iridescent_insects_beetle_ground_i1_2026 import (
    _resize,
    _surface,
    paint_beetle_ground_i1,
)


paint_beetle_ground_i2 = paint_beetle_ground_i1


def spec_beetle_ground_i2(shape, seed, sm, base_m, base_r):
    mesh, plate, pit, pit_lip, transverse, scrape, cross, f0, f1, f2 = _surface(seed + 9463)

    m = 104 + plate * (72 + 46 * f0) + transverse * (92 + 36 * f2)
    m += cross * (116 + 34 * f1) + pit_lip * 26 - pit * 82

    r = 112 + pit * (116 + 42 * f1) + scrape * (104 + 48 * f0)
    r += cross * 24 - transverse * 31 - pit_lip * 18

    cc = 98 + mesh * (108 + 44 * f2) + pit_lip * (126 + 38 * f0)
    cc += plate * 19 - scrape * 68 - pit * 24
    # Ground Beetle paint is deliberately oil-black and quiet.  Keep the
    # feature separation but match its energy hierarchy instead of letting the
    # diagnostic spec map shout three times louder than the visible armor.
    m = 104 + .42 * (m - 104)
    r = 112 + .94 * (r - 112)
    cc = 98 + .50 * (cc - 98)
    return (
        _resize(np.clip(m * sm, 0, 250), shape),
        _resize(np.clip(r, 4, 248), shape),
        _resize(np.clip(cc, 0, 255), shape),
    )
