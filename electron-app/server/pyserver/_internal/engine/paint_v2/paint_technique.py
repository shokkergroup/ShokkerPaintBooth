# -*- coding: utf-8 -*-
"""Paint Technique bases.

These are not material fantasies; they are painterly application marks. The
base color should remain recognizable while the paint and spec maps carry the
brush, drip, roller, spray, sponge, or splatter evidence.
"""

import numpy as np

from engine.core import get_mgrid, multi_scale_noise
from engine.paint_v2 import ensure_bb_2d


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _as_rgb(paint):
    return paint[:, :, :3].copy() if paint.ndim == 3 and paint.shape[2] > 3 else paint.copy()


def _mask3(mask):
    return mask[:, :, np.newaxis].astype(np.float32)


def _norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _base_tint(base, lift=0.0, crush=0.0):
    gray = base.mean(axis=2, keepdims=True)
    return np.clip(base * (1.0 - crush) + gray * crush + lift, 0, 1)


def _line_field(shape, seed, angle, freq, warp_gain=0.16):
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    warp = multi_scale_noise((h, w), [6, 14, 32], [0.45, 0.35, 0.20], seed)
    coord = np.cos(angle) * x + np.sin(angle) * y
    return np.sin(coord * freq + warp * warp_gain * max(h, w))


def _mist(shape, seed, density, strength=1.0):
    h, w = _shape2(shape)
    rng = np.random.default_rng(seed)
    n = min(int(h * w * density), 140000)
    canvas = np.zeros((h, w), dtype=np.float32)
    if n > 0:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.15, 1.0, n).astype(np.float32)
        np.maximum.at(canvas, (yy, xx), vals)
    bloom = canvas
    if n > 0:
        # tiny nearest-neighbor growth without a blur dependency: enough to make
        # paint droplets read in-game without creating blocky square chunks.
        bloom = np.maximum.reduce([
            canvas,
            np.roll(canvas, 1, axis=0) * 0.55,
            np.roll(canvas, -1, axis=0) * 0.55,
            np.roll(canvas, 1, axis=1) * 0.55,
            np.roll(canvas, -1, axis=1) * 0.55,
        ])
    return np.clip(bloom * strength, 0, 1).astype(np.float32)


def _micro_grain(shape, seed):
    h, w = _shape2(shape)
    return _norm01(multi_scale_noise((h, w), [1, 2, 4, 8], [0.34, 0.30, 0.22, 0.14], seed))


def _add_paint_micro(effect, shape, seed, strength=0.08, weight=None):
    h, w = _shape2(shape)
    grain = _micro_grain((h, w), seed)
    if weight is None:
        gate = np.ones((h, w), dtype=np.float32)
    else:
        gate = 0.35 + np.clip(weight, 0, 1) * 0.65
    chroma = np.stack([
        (grain - 0.50) * 0.95,
        (0.50 - grain) * 0.36,
        (0.52 - grain) * 0.72,
    ], axis=2).astype(np.float32)
    lift = (grain - 0.5)[:, :, None] * 0.42
    return np.clip(effect + (chroma + lift) * float(strength) * gate[:, :, None], 0, 1)


def paint_drip_gravity(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    rng = np.random.default_rng(seed + 4101)

    src_cols = rng.integers(0, w, max(28, int(w * 0.055)))
    drips = np.zeros((h, w), dtype=np.float32)
    yn = y / max(h - 1, 1)
    for col in src_cols:
        width = rng.uniform(1.4, 4.8) * max(w / 2048.0, 0.45)
        start = rng.uniform(0.02, 0.42)
        length = rng.uniform(0.18, 0.92)
        wander = np.sin(yn * rng.uniform(9.0, 23.0) + rng.uniform(0, 6.28)) * rng.uniform(2.0, 10.0)
        dist = np.abs(x - (col + wander))
        trail = np.exp(-(dist ** 2) / (2.0 * width ** 2))
        gravity = np.clip((yn - start) / max(length, 1e-4), 0, 1)
        trail *= (gravity > 0).astype(np.float32) * np.exp(-gravity * 1.45)
        bead_y = np.clip(start + length * rng.uniform(0.55, 1.05), 0, 1)
        bead = np.exp(-((yn - bead_y) ** 2) / (2.0 * 0.0018)) * np.exp(-(dist ** 2) / (2.0 * (width * 2.3) ** 2))
        drips += trail * 0.72 + bead * 1.15
    curtain = _norm01(_line_field((h, w), seed + 4102, np.pi / 2.0, 0.035, 0.10))
    mist = _mist((h, w), seed + 4103, 0.012, 0.38)
    field = np.clip(_norm01(drips) * 0.72 + curtain * 0.18 + mist * 0.35, 0, 1)

    dark = _base_tint(base, crush=0.35)
    wet = np.clip(base * (1.03 + field[:, :, None] * 0.22), 0, 1)
    effect = np.clip(dark * (1 - field[:, :, None] * 0.55) + wet * field[:, :, None] * 0.85, 0, 1)
    effect = _add_paint_micro(effect, (h, w), seed + 4104, 0.25, field)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    out = np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.12 * blend, 0, 1)
    return out.astype(np.float32)


def spec_drip_gravity(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    y, _ = get_mgrid((h, w))
    curtain = _norm01(_line_field((h, w), seed + 4102, np.pi / 2.0, 0.035, 0.10))
    bead = _mist((h, w), seed + 4103, 0.012, 0.75)
    gravity = y / max(h - 1, 1)
    wet = np.clip(curtain * 0.45 + bead * 0.85 + gravity * 0.25, 0, 1)
    M = np.clip(base_m * 0.25 + wet * 70.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(20.0 + (1 - wet) * 95.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + (1 - wet) * 65.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_splatter_loose(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    fine = _mist((h, w), seed + 4201, 0.055, 0.98)
    medium = _mist((h, w), seed + 4202, 0.007, 1.0)
    medium = np.maximum.reduce([medium, np.roll(medium, 1, 0), np.roll(medium, -1, 1)]) * 0.65
    direction = _norm01(_line_field((h, w), seed + 4203, 0.25, 0.055, 0.08))
    splatter = np.clip(fine * 0.68 + medium * 0.52 + np.clip(direction - 0.72, 0, 1) * 0.32, 0, 1)
    ink = np.clip(base * 0.45 + np.array([0.08, 0.075, 0.09], dtype=np.float32), 0, 1)
    highlight = np.clip(base + 0.14, 0, 1)
    effect = np.clip(base * (1 - splatter[:, :, None] * 0.42) + ink * splatter[:, :, None] * 0.55 + highlight * fine[:, :, None] * 0.20, 0, 1)
    effect = _add_paint_micro(effect, (h, w), seed + 4204, 0.11, splatter)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.08 * blend, 0, 1).astype(np.float32)


def spec_splatter_loose(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    splatter = np.clip(_mist((h, w), seed + 4201, 0.035, 0.85) + _mist((h, w), seed + 4202, 0.007, 1.0), 0, 1)
    M = np.clip(base_m * 0.18 + splatter * 95.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(36.0 + (1 - splatter) * 115.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(22.0 + (1 - splatter) * 90.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_sponge_stipple(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    pores = multi_scale_noise((h, w), [1, 2, 5, 11], [0.36, 0.28, 0.22, 0.14], seed + 4301)
    pores = _norm01(pores)
    holes = np.clip((0.42 - pores) * 3.6, 0, 1)
    raised = np.clip((pores - 0.58) * 3.0, 0, 1)
    mottled = multi_scale_noise((h, w), [6, 14, 28], [0.45, 0.35, 0.20], seed + 4302)
    field = np.clip(raised * 0.62 - holes * 0.34 + _norm01(mottled) * 0.28, 0, 1)
    warm = np.clip(base * np.array([1.08, 1.02, 0.92], dtype=np.float32), 0, 1)
    cool_shadow = np.clip(base * np.array([0.72, 0.78, 0.86], dtype=np.float32), 0, 1)
    effect = np.clip(base * 0.55 + warm * field[:, :, None] * 0.55 + cool_shadow * holes[:, :, None] * 0.35, 0, 1)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.06 * blend, 0, 1).astype(np.float32)


def spec_sponge_stipple(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    pores = _norm01(multi_scale_noise((h, w), [1, 2, 5, 11], [0.36, 0.28, 0.22, 0.14], seed + 4301))
    micro = np.clip(np.abs(pores - 0.5) * 2.0, 0, 1)
    M = np.clip(base_m * 0.12 + micro * 62.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(78.0 + micro * 92.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(70.0 + micro * 105.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_roller_streak(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    lap = np.sin(x * 0.018 + multi_scale_noise((h, w), [18, 42], [0.55, 0.45], seed + 4401) * 2.1) * 0.5 + 0.5
    fiber = np.sin(x * 0.92 + y * 0.018 + multi_scale_noise((h, w), [3, 7], [0.7, 0.3], seed + 4402) * 3.0) * 0.5 + 0.5
    dry_edges = np.clip(1.0 - np.abs(lap - 0.52) * 4.0, 0, 1)
    streak = np.clip(lap * 0.34 + fiber * 0.44 + dry_edges * 0.28, 0, 1)
    effect = np.clip(base * (0.86 + streak[:, :, None] * 0.28), 0, 1)
    effect = _add_paint_micro(effect, (h, w), seed + 4404, 0.20, streak)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.07 * blend, 0, 1).astype(np.float32)


def spec_roller_streak(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    fiber = np.sin(x * 0.92 + y * 0.018 + multi_scale_noise((h, w), [3, 7], [0.7, 0.3], seed + 4402) * 3.0) * 0.5 + 0.5
    lap = np.sin(x * 0.018 + multi_scale_noise((h, w), [18, 42], [0.55, 0.45], seed + 4401) * 2.1) * 0.5 + 0.5
    M = np.clip(base_m * 0.10 + fiber * 66.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(58.0 + lap * 92.0 * sm + fiber * 28.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(44.0 + (1 - fiber) * 115.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_spray_fade(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    yn = y / max(h - 1, 1)
    xn = x / max(w - 1, 1)
    fade = np.clip((xn * 0.65 + yn * 0.35 - 0.08) / 0.84, 0, 1)
    fade = fade + (multi_scale_noise((h, w), [10, 22, 48], [0.45, 0.35, 0.20], seed + 4501) - 0.5) * 0.13
    fade = np.clip(fade, 0, 1)
    atom = _mist((h, w), seed + 4502, 0.075, 0.92) * (0.25 + fade * 0.75)
    target = np.clip(base * 1.18 + np.array([0.04, 0.025, 0.015], dtype=np.float32), 0, 1)
    effect = np.clip(base * (1 - fade[:, :, None] * 0.58) + target * fade[:, :, None] * 0.68 + atom[:, :, None] * 0.16, 0, 1)
    effect = _add_paint_micro(effect, (h, w), seed + 4504, 0.11, np.maximum(atom, fade))
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.09 * blend, 0, 1).astype(np.float32)


def spec_spray_fade(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    fade = np.clip(((x / max(w - 1, 1)) * 0.65 + (y / max(h - 1, 1)) * 0.35 - 0.08) / 0.84, 0, 1)
    atom = _mist((h, w), seed + 4502, 0.05, 0.65)
    field = np.clip(fade * 0.65 + atom * 0.45, 0, 1)
    M = np.clip(base_m * 0.18 + field * 62.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(30.0 + (1 - fade) * 116.0 * sm + atom * 24.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + (1 - field) * 105.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_brush_stroke(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    warp = multi_scale_noise((h, w), [8, 18, 36], [0.45, 0.35, 0.20], seed + 4601)
    bristle = (
        np.sin((x + warp * 18.0) * 0.37 + y * 0.026)
        + np.sin((x + warp * 10.0) * 0.91 + y * 0.014) * 0.45
        + np.sin((x - warp * 6.0) * 1.77) * 0.18
    )
    bristle = _norm01(bristle)
    ridges = np.clip((bristle - 0.56) * 3.2, 0, 1)
    troughs = np.clip((0.43 - bristle) * 3.0, 0, 1)
    load = _norm01(multi_scale_noise((h, w), [22, 48, 96], [0.42, 0.36, 0.22], seed + 4602))
    stroke = np.clip(ridges * 0.62 + load * 0.34 - troughs * 0.20, 0, 1)
    rich = np.clip(base * (0.82 + load[:, :, None] * 0.28), 0, 1)
    effect = np.clip(rich + ridges[:, :, None] * 0.16 - troughs[:, :, None] * 0.12, 0, 1)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.10 * blend * stroke[:, :, None], 0, 1).astype(np.float32)


def spec_brush_stroke(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    y, x = get_mgrid((h, w))
    warp = multi_scale_noise((h, w), [8, 18, 36], [0.45, 0.35, 0.20], seed + 4601)
    bristle = _norm01(np.sin((x + warp * 18.0) * 0.37 + y * 0.026) + np.sin((x + warp * 10.0) * 0.91 + y * 0.014) * 0.45)
    ridges = np.clip((bristle - 0.56) * 3.2, 0, 1)
    troughs = np.clip((0.43 - bristle) * 3.0, 0, 1)
    M = np.clip(base_m * 0.12 + ridges * 70.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(42.0 + troughs * 112.0 * sm + ridges * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(22.0 + troughs * 128.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC
