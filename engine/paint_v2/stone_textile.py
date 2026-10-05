# -*- coding: utf-8 -*-
"""Native renderers for Stone & Mineral and Textile-Inspired base finishes.

These replace the generic shipping fallback for categories where the owner
called out repeated/rotated DNA. Each ID keeps a different surface topology.

.. warning::

   **ORPHANED AT RUNTIME — see SPB-87.**

   This module is imported by ``shokker_engine_v2._spb_wire_regular_base_v2_overrides``
   (line 13018), and the resulting ``TEXTILE_STONE_OVERRIDES`` dict is collected
   into the overrides bag. But all 12 IDs below are reported as
   ``[Regular Base V2] Missing ids skipped`` at boot — the IDs don't yet exist
   in ``BASE_REGISTRY`` when the wire step runs.

   A LATER boot step (``[Regular Base Quality] Added 12 missing shipping base
   renderer(s)``) then registers the IDs with placeholder
   ``_spb_missing_base_paint_*`` / ``_spb_missing_base_spec_*`` shims from
   ``shokker_engine_v2.py``, NOT the dedicated functions in this file.

   The SPB-82 textile-inspired rebuild (tick 28) confirmed this: it landed
   by patching the shim in ``shokker_engine_v2._spb_make_shipping_base_paint``
   directly, not these renderers.

   **Until SPB-87 is resolved, do not assume edits here affect runtime
   output.** Test by checking ``BASE_REGISTRY[id]['paint_fn'].__module__`` —
   if it reads ``shokker_engine_v2`` instead of
   ``engine.paint_v2.stone_textile`` your edits are not running.

   Repro::

       python -c "import sys; sys.path.insert(0, '.')
       from engine.paint_v2.stone_textile import TEXTILE_STONE_OVERRIDES
       import shokker_engine_v2 as eng
       exp_paint, _ = TEXTILE_STONE_OVERRIDES['stone_slate_matte']
       print('matches:', eng.BASE_REGISTRY['stone_slate_matte']['paint_fn'] is exp_paint)"
       # prints: matches: False
"""

import numpy as np

from engine.core import get_mgrid, multi_scale_noise
from engine.paint_v2 import ensure_bb_2d


def _shape(shape):
    return shape[:2] if len(shape) > 2 else shape


def _prep(paint, shape, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = _shape(shape)
    return paint.copy(), ensure_bb_2d(bb, shape), h, w


def _mix(paint, effect, mask, pm, bb, bb_gain=0.08):
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    out = paint * (1.0 - blend) + effect * blend
    return np.clip(out + bb[:, :, None] * bb_gain * pm * mask[:, :, None], 0, 1).astype(np.float32)


def _fine(shape, seed, amount=1.0):
    h, w = _shape(shape)
    a = multi_scale_noise((h, w), [2, 4, 8], [0.48, 0.34, 0.18], seed)
    b = multi_scale_noise((h, w), [1, 3, 6], [0.40, 0.36, 0.24], seed + 17)
    return np.clip((a * 0.62 + b * 0.38) * amount, -1, 1).astype(np.float32)


def _fiber(shape, seed, angle, freq, warp=0.0):
    h, w = _shape(shape)
    y, x = get_mgrid((h, w))
    noise = multi_scale_noise((h, w), [8, 16, 32], [0.45, 0.35, 0.20], seed)
    coord = x * np.cos(angle) + y * np.sin(angle) + noise * warp
    return (np.sin(coord * freq) * 0.5 + 0.5).astype(np.float32)


def _textile_weave_macro(shape, seed):
    """Macro-band weave grain (SPB-82, tick 28).

    Returns a (H,W) float32 in roughly [-0.5, 0.5]. The textile paint_fns
    add this to their `body` modulation BEFORE the dstack to RGB. Without
    it the textiles have only fine/mid noise that washes out at 32px
    block-mean scale (M8 reads them as flat: macro_std32 ~ 1-2).

    Octaves 32/64/128 produce 16-64 pixel weave-cluster features at 2048
    canvas — visible at thumbnail scale AND reads as fabric weave on the
    actual car body. Companion to the tick-27 weather fix and tick-25
    quilt fix. Codified in docs/METRICS.md section A.1.
    """
    h, w = _shape(shape)
    return (multi_scale_noise((h, w), [32, 64, 128], [0.40, 0.35, 0.25], seed)
            - 0.5).astype(np.float32)


def paint_stone_slate_matte(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    y, x = get_mgrid((h, w))
    layers = _fiber((h, w), seed + 10, 0.18, 0.42, 7.0)
    cleavage = _fiber((h, w), seed + 11, -0.92, 0.09, 18.0)
    chips = np.clip(_fine((h, w), seed + 12, 1.3) * 2.0 - 0.55, 0, 1)
    mineral = multi_scale_noise((h, w), [1, 3, 7, 17], [0.34, 0.30, 0.22, 0.14], seed + 15)
    green = np.clip((mineral - 0.63) * 4.4, 0, 1)
    iron = np.clip((0.27 - mineral) * 4.0, 0, 1)
    quartz = np.clip((np.abs(_fine((h, w), seed + 16, 1.1)) - 0.62) * 3.0, 0, 1)
    slab = 0.18 + layers * 0.055 + cleavage * 0.030 - chips * 0.035
    effect = np.dstack([
        slab * 0.78 + iron * 0.070 + quartz * 0.018,
        slab * 0.88 + green * 0.095 + iron * 0.022 + quartz * 0.030,
        slab * 0.93 + green * 0.050 + quartz * 0.070,
    ])
    return _mix(paint, effect, mask, pm, bb, 0.04)


def spec_stone_slate_matte(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    grain = _fine((h, w), seed + 13, 1.0)
    cleavage = _fiber((h, w), seed + 14, -0.92, 0.09, 18.0)
    mineral = multi_scale_noise((h, w), [1, 3, 7, 17], [0.34, 0.30, 0.22, 0.14], seed + 15)
    M = np.clip(9.0 + np.abs(grain) * 22.0 * sm + mineral * 12.0, 0, 255).astype(np.float32)
    R = np.clip(168.0 + cleavage * 48.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(156.0 + np.abs(grain) * 42.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_stone_marble_polished(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    y, x = get_mgrid((h, w))
    flow = multi_scale_noise((h, w), [12, 24, 48], [0.45, 0.35, 0.20], seed + 20)
    vein_field = np.sin(x * 0.035 + y * 0.012 + flow * 5.2)
    veins = np.clip(np.abs(vein_field) ** 10.0, 0, 1)
    gold = np.clip(np.sin(x * 0.017 - y * 0.031 + flow * 3.0) ** 16, 0, 1)
    body = 0.72 + _fine((h, w), seed + 21, 0.22)
    effect = np.dstack([
        body + veins * 0.10 + gold * 0.08,
        body * 0.96 + veins * 0.07 + gold * 0.045,
        body * 0.88 + veins * 0.03,
    ])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.18)


def spec_stone_marble_polished(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    polish = multi_scale_noise((h, w), [6, 18, 48], [0.45, 0.35, 0.20], seed + 22)
    vein = np.abs(_fiber((h, w), seed + 23, 0.42, 0.12, 18.0))
    M = np.clip(48.0 + vein * 42.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + (1.0 - polish) * 28.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(24.0 + vein * 24.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_stone_granite_speckled(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    rng = np.random.RandomState(seed + 30)
    pepper = rng.rand(h, w).astype(np.float32)
    salt = rng.rand(h, w).astype(np.float32)
    mica = rng.rand(h, w).astype(np.float32)
    base = 0.34 + _fine((h, w), seed + 31, 0.08)
    flecks = (pepper > 0.72) * -0.13 + (salt > 0.78) * 0.18 + (mica > 0.965) * 0.34
    effect = np.dstack([
        base + flecks * 0.95,
        base * 0.95 + flecks * 0.88,
        base * 0.90 + flecks * 0.72,
    ])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.05)


def spec_stone_granite_speckled(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    rng = np.random.RandomState(seed + 32)
    mica = (rng.rand(h, w) > 0.968).astype(np.float32)
    grain = np.abs(_fine((h, w), seed + 33, 1.0))
    M = np.clip(54.0 + mica * 130.0 * sm + grain * 20.0, 0, 255).astype(np.float32)
    R = np.clip(62.0 + grain * 70.0 * sm - mica * 30.0, 15, 255).astype(np.float32)
    CC = np.clip(46.0 + grain * 56.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_stone_sandstone_warm(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    y, x = get_mgrid((h, w))
    strata = _fiber((h, w), seed + 40, 0.03, 0.075, 22.0)
    grit = np.abs(_fine((h, w), seed + 41, 0.9))
    pores = np.clip(_fine((h, w), seed + 42, 1.2) - 0.52, 0, 1)
    body = 0.49 + strata * 0.12 + grit * 0.075 - pores * 0.10
    effect = np.dstack([body * 1.08, body * 0.84, body * 0.55])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.035)


def spec_stone_sandstone_warm(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    grit = np.abs(_fine((h, w), seed + 43, 1.0))
    strata = _fiber((h, w), seed + 40, 0.03, 0.075, 22.0)
    M = np.clip(5.0 + grit * 12.0 * sm + strata * 5.0, 0, 255).astype(np.float32)
    R = np.clip(182.0 + grit * 48.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(174.0 + grit * 52.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_stone_obsidian_mirror(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    y, x = get_mgrid((h, w))
    smoke = multi_scale_noise((h, w), [10, 24, 64], [0.45, 0.35, 0.20], seed + 50)
    shell = multi_scale_noise((h, w), [5, 11, 23, 53], [0.30, 0.30, 0.24, 0.16], seed + 51)
    shard_a = np.clip(np.abs(np.sin((x * 0.030 - y * 0.018 + shell * 4.8))) ** 20, 0, 1)
    shard_b = np.clip(np.abs(np.sin((x * 0.012 + y * 0.034 + smoke * 5.4))) ** 24, 0, 1)
    fracture = np.clip(shard_a * 0.70 + shard_b * 0.58 + np.abs(np.gradient(shell, axis=0)) * 2.2, 0, 1)
    base = 0.020 + smoke * 0.030 + fracture * 0.17
    blue_flash = np.clip(np.sin(x * 0.010 + y * 0.006 + shell * 5.0), 0, 1) * fracture
    effect = np.dstack([base * 0.74 + fracture * 0.015, base * 0.84 + blue_flash * 0.015, base * 1.10 + blue_flash * 0.045])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.28)


def spec_stone_obsidian_mirror(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    y, x = get_mgrid((h, w))
    shell = multi_scale_noise((h, w), [5, 11, 23, 53], [0.30, 0.30, 0.24, 0.16], seed + 51)
    smoke = multi_scale_noise((h, w), [10, 24, 64], [0.45, 0.35, 0.20], seed + 50)
    shard_a = np.clip(np.abs(np.sin((x * 0.030 - y * 0.018 + shell * 4.8))) ** 20, 0, 1)
    shard_b = np.clip(np.abs(np.sin((x * 0.012 + y * 0.034 + smoke * 5.4))) ** 24, 0, 1)
    fracture = np.clip(shard_a * 0.70 + shard_b * 0.58 + np.abs(np.gradient(shell, axis=0)) * 2.2, 0, 1)
    M = np.clip(190.0 + fracture * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(4.0 + (1.0 - fracture) * 24.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(16.0 + fracture * 12.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_stone_travertine_cream(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    strata = _fiber((h, w), seed + 60, 0.02, 0.055, 20.0)
    pore_noise = _fine((h, w), seed + 61, 1.25)
    pores = np.clip((pore_noise - 0.42) * 2.4, 0, 1)
    body = 0.63 + strata * 0.13 - pores * 0.19
    effect = np.dstack([body * 1.08, body * 0.96, body * 0.74])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.04)


def spec_stone_travertine_cream(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    pores = np.clip((_fine((h, w), seed + 62, 1.2) - 0.35) * 2.1, 0, 1)
    M = np.clip(8.0 + pores * 8.0, 0, 255).astype(np.float32)
    R = np.clip(112.0 + pores * 88.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(96.0 + pores * 82.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_textile_denim_weave(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    warp = _fiber((h, w), seed + 100, 0.0, 1.35, 2.0)
    weft = _fiber((h, w), seed + 101, np.pi / 2, 0.92, 2.0)
    twill = _fiber((h, w), seed + 102, np.pi / 4, 0.55, 5.0)
    slub = _fine((h, w), seed + 103, 0.25)
    macro = _textile_weave_macro((h, w), seed + 105)
    indigo = 0.16 + warp * 0.05 + weft * 0.03 + twill * 0.04 + slub + macro * 0.09
    effect = np.dstack([indigo * 0.42, indigo * 0.58, indigo * 1.18])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.025)


def spec_textile_denim_weave(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    weave = _fiber((h, w), seed + 104, np.pi / 4, 0.60, 4.0)
    M = np.clip(4.0 + weave * 8.0, 0, 255).astype(np.float32)
    R = np.clip(172.0 + weave * 50.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(185.0 + weave * 48.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_textile_canvas_rough(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    warp = _fiber((h, w), seed + 110, 0.0, 0.82, 4.0)
    weft = _fiber((h, w), seed + 111, np.pi / 2, 0.74, 4.0)
    knots = np.clip(_fine((h, w), seed + 112, 1.0) - 0.55, 0, 1)
    macro = _textile_weave_macro((h, w), seed + 115)
    body = 0.44 + warp * 0.10 + weft * 0.09 + knots * 0.16 + macro * 0.10
    effect = np.dstack([body * 1.06, body * 0.92, body * 0.68])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.025)


def spec_textile_canvas_rough(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    weave = _fiber((h, w), seed + 113, 0.0, 0.82, 4.0) * _fiber((h, w), seed + 114, np.pi / 2, 0.74, 4.0)
    knots = np.clip(_fine((h, w), seed + 112, 1.0) - 0.55, 0, 1)
    M = np.clip(3.0 + weave * 9.0 + knots * 8.0, 0, 255).astype(np.float32)
    R = np.clip(194.0 + weave * 46.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(198.0 + weave * 46.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_textile_silk_sheen(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    y, x = get_mgrid((h, w))
    strands = _fiber((h, w), seed + 120, 0.08, 1.70, 6.0)
    moire = np.sin(x * 0.030 + y * 0.055 + multi_scale_noise((h, w), [12, 24, 48], [0.45, 0.35, 0.20], seed + 121) * 4.0)
    # Silk should still feel smooth — lower amplitude than coarse textiles.
    macro = _textile_weave_macro((h, w), seed + 125)
    shimmer = 0.46 + strands * 0.11 + moire * 0.08 + macro * 0.06
    effect = np.dstack([shimmer * 0.86, shimmer * 0.78, shimmer * 1.18])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.12)


def spec_textile_silk_sheen(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    strands = _fiber((h, w), seed + 122, 0.08, 1.70, 6.0)
    M = np.clip(18.0 + strands * 38.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(26.0 + (1.0 - strands) * 42.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(42.0 + strands * 28.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_textile_velvet_crush(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    nap = multi_scale_noise((h, w), [10, 22, 46], [0.45, 0.35, 0.20], seed + 130)
    pile = _fiber((h, w), seed + 131, -0.35, 1.10, 8.0)
    macro = _textile_weave_macro((h, w), seed + 135)
    crushed = np.clip(0.30 + nap * 0.13 + pile * 0.07 + macro * 0.11, 0, 1)
    effect = np.dstack([crushed * 0.85, crushed * 0.30, crushed * 1.08])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.02)


def spec_textile_velvet_crush(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    nap = multi_scale_noise((h, w), [10, 22, 46], [0.45, 0.35, 0.20], seed + 132)
    pile = _fiber((h, w), seed + 131, -0.35, 1.10, 8.0)
    M = np.clip(2.0 + np.maximum(nap, 0) * 11.0 + pile * 8.0, 0, 255).astype(np.float32)
    R = np.clip(150.0 + (1.0 - nap) * 38.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(178.0 + np.maximum(nap, 0) * 40.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_textile_burlap_coarse(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    warp = _fiber((h, w), seed + 140, 0.0, 0.44, 10.0)
    weft = _fiber((h, w), seed + 141, np.pi / 2, 0.38, 10.0)
    stray = np.clip(_fine((h, w), seed + 142, 1.2), 0, 1)
    macro = _textile_weave_macro((h, w), seed + 145)
    body = 0.36 + warp * 0.13 + weft * 0.12 + stray * 0.10 + macro * 0.12
    effect = np.dstack([body * 1.16, body * 0.92, body * 0.58])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.02)


def spec_textile_burlap_coarse(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    coarse = _fiber((h, w), seed + 143, 0.0, 0.44, 10.0) + _fiber((h, w), seed + 144, np.pi / 2, 0.38, 10.0)
    stray = np.clip(_fine((h, w), seed + 142, 1.2), 0, 1)
    M = np.clip(1.0 + coarse * 5.0 + stray * 7.0, 0, 255).astype(np.float32)
    R = np.clip(205.0 + coarse * 24.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(210.0 + coarse * 24.0, 16, 255).astype(np.float32)
    return M, R, CC


def paint_textile_suede_soft(paint, shape, mask, seed, pm, bb):
    paint, bb, h, w = _prep(paint, shape, bb)
    nap = multi_scale_noise((h, w), [6, 14, 32], [0.45, 0.35, 0.20], seed + 150)
    fibers = _fiber((h, w), seed + 151, 0.55, 1.28, 5.0)
    macro = _textile_weave_macro((h, w), seed + 155)
    body = 0.30 + nap * 0.09 + fibers * 0.055 + macro * 0.10
    effect = np.dstack([body * 1.10, body * 0.88, body * 0.70])
    return _mix(paint, np.clip(effect, 0, 1), mask, pm, bb, 0.018)


def spec_textile_suede_soft(shape, seed, sm, base_m, base_r):
    h, w = _shape(shape)
    nap = multi_scale_noise((h, w), [6, 14, 32], [0.45, 0.35, 0.20], seed + 152)
    fibers = _fiber((h, w), seed + 151, 0.55, 1.28, 5.0)
    M = np.clip(2.0 + np.abs(nap) * 8.0 + fibers * 8.0, 0, 255).astype(np.float32)
    R = np.clip(186.0 + np.abs(nap) * 50.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(198.0 + np.abs(nap) * 38.0, 16, 255).astype(np.float32)
    return M, R, CC


TEXTILE_STONE_OVERRIDES = {
    "stone_slate_matte": (paint_stone_slate_matte, spec_stone_slate_matte),
    "stone_marble_polished": (paint_stone_marble_polished, spec_stone_marble_polished),
    "stone_granite_speckled": (paint_stone_granite_speckled, spec_stone_granite_speckled),
    "stone_sandstone_warm": (paint_stone_sandstone_warm, spec_stone_sandstone_warm),
    "stone_obsidian_mirror": (paint_stone_obsidian_mirror, spec_stone_obsidian_mirror),
    "stone_travertine_cream": (paint_stone_travertine_cream, spec_stone_travertine_cream),
    "textile_denim_weave": (paint_textile_denim_weave, spec_textile_denim_weave),
    "textile_canvas_rough": (paint_textile_canvas_rough, spec_textile_canvas_rough),
    "textile_silk_sheen": (paint_textile_silk_sheen, spec_textile_silk_sheen),
    "textile_velvet_crush": (paint_textile_velvet_crush, spec_textile_velvet_crush),
    "textile_burlap_coarse": (paint_textile_burlap_coarse, spec_textile_burlap_coarse),
    "textile_suede_soft": (paint_textile_suede_soft, spec_textile_suede_soft),
}
