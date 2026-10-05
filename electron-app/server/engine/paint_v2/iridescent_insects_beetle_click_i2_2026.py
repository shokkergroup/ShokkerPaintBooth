"""Click Beetle Plasma I2 — anatomy-bound material correction.

SPB-105 / owner 2026-09-01, Finish Identity correction.  The accepted I1
paint already has unique Elaterid nerve routes, microtube eyes, lantern rings,
striae and punctures.  Its spec, however, was dominated by the same broad
f0/f1/f2 fields used elsewhere in IRIDESCENT INSECTS.  I2 preserves that good
paint and replaces only M/R/Cc with a name-true feature circuit: every material
transition is caused by a visible eye, tube, iris, corona, route, stria or pore.
"""
from __future__ import annotations

import numpy as np

from engine.paint_v2.iridescent_insects_beetle_click_i1_2026 import (
    _resize,
    _surface,
    paint_beetle_click_i1,
)


paint_beetle_click_i2 = paint_beetle_click_i1


def spec_beetle_click_i2(shape, seed, sm, base_m, base_r):
    eye, iris, pupil, corona, tubes, stria, puncture, shell, track, state, f0, f1, f2 = _surface(seed + 15101)

    # Shell graphite is the quiet substrate.  Each visible piece of the click
    # beetle construction owns a different response; broad fields may only
    # vary the feature they are clipped into and can never form a free wave.
    # Orthogonal feature ownership prevents the same eye/track mask from
    # driving all three channels.  Red/metal follows shell striae and lantern
    # irises; green/roughness follows pores and absorptive tubes; blue/coat
    # follows nerve routes and coronas.
    m = 112 + stria * (96 + 42 * f0) + iris * (112 + 38 * (1 - state))
    m += corona * (28 + 26 * state) - pupil * 74 - tubes * 24

    r = 114 + puncture * (114 + 50 * f1) + pupil * 112 + tubes * 53
    r += shell * 8 - iris * 22 - track * 18

    cc = 108 + track * (124 + 48 * f2) + corona * (132 + 42 * (1 - state))
    cc += iris * (42 + 38 * state) - puncture * 34 - tubes * 18
    return (
        _resize(np.clip(m * sm, 0, 250), shape),
        _resize(np.clip(r, 4, 248), shape),
        _resize(np.clip(cc, 0, 255), shape),
    )
