"""Emperor Eyelet I2 — ocellus-bound material correction.

SPB-105 / owner 2026-09-01, Finish Identity correction.  I1's braided broken
ocelli and purple-emperor scale paint are preserved.  Its combined spec shared
the category's generic f0/f1/f2 wave silhouette.  I2 gives separate material
ownership to bronze/gold rings and ridges, dark/spoke/roof scales, and
iris/pearl/lip features so the spec unmistakably traces an eyelet.
"""
from __future__ import annotations

import numpy as np

from engine.paint_v2.iridescent_insects_butterfly_emperor_i1_2026 import (
    _resize,
    _surface,
    paint_butterfly_emperor_i1,
)


paint_butterfly_emperor_i2 = paint_butterfly_emperor_i1


def spec_butterfly_emperor_i2(shape, seed, sm, base_m, base_r):
    outer, gold, iris, dark, pupil, spoke, scale, scale_lip, ridge, state, stream, cadence, f0, f1, f2 = _surface(seed + 16561)

    m = 106 + outer * (88 + 34 * state) + gold * (122 + 34 * f0)
    m += ridge * (72 + 42 * cadence) + scale * 14 - dark * 78

    r = 116 + dark * (112 + 36 * f1) + spoke * (86 + 42 * state)
    r += scale * (28 + 34 * cadence) - gold * 51 - pupil * 43
    r = 116 + 1.06 * (r - 116)

    cc = 102 + pupil * (136 + 44 * f2) + iris * (94 + 38 * cadence)
    cc += scale_lip * (76 + 36 * state) + outer * 24 - dark * 64 - spoke * 18
    return (
        _resize(np.clip(m * sm, 0, 250), shape),
        _resize(np.clip(r, 4, 248), shape),
        _resize(np.clip(cc, 0, 255), shape),
    )
