# -*- coding: utf-8 -*-
"""Paint Technique bases.

These are not material fantasies; they are painterly application marks. The
base color should remain recognizable while the paint and spec maps carry the
brush, drip, roller, spray, sponge, or splatter evidence.
"""

import numpy as np

from engine.core import get_mgrid, multi_scale_noise
from engine.paint_v2 import ensure_bb_2d


_FIELD_CACHE: dict[tuple[str, tuple[int, int], int], object] = {}
_MIST_CACHE: dict[tuple[tuple[int, int], int, float, float], np.ndarray] = {}


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
    wh, ww = _working_shape((h, w), 768)
    y, x = get_mgrid((wh, ww))
    warp = multi_scale_noise((wh, ww), [6, 14, 32], [0.45, 0.35, 0.20], seed)
    coord = np.cos(angle) * x + np.sin(angle) * y
    field = np.sin(coord * freq + warp * warp_gain * max(wh, ww))
    return _resize_field(field.astype(np.float32), (h, w))


def _mist(shape, seed, density, strength=1.0):
    h, w = _shape2(shape)
    key = ((int(h), int(w)), int(seed), round(float(density), 6), round(float(strength), 4))
    cached = _MIST_CACHE.get(key)
    if cached is not None:
        return cached.copy()
    work_h, work_w = _working_shape((h, w), 768)
    rng = np.random.default_rng(seed)
    n = min(int(work_h * work_w * density), 90000)
    canvas = np.zeros((work_h, work_w), dtype=np.float32)
    if n > 0:
        yy = rng.integers(0, work_h, n)
        xx = rng.integers(0, work_w, n)
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
    out = np.clip(bloom * strength, 0, 1).astype(np.float32)
    out = _resize_field(out, (h, w))
    if len(_MIST_CACHE) > 48:
        _MIST_CACHE.clear()
    _MIST_CACHE[key] = out.copy()
    return out


def _micro_grain(shape, seed):
    h, w = _shape2(shape)
    work_h, work_w = _working_shape((h, w), 768)
    grain = _norm01(multi_scale_noise((work_h, work_w), [1, 2, 4, 8], [0.34, 0.30, 0.22, 0.14], seed))
    return _resize_field(grain, (h, w))


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


def _working_shape(shape, max_dim=640):
    h, w = _shape2(shape)
    max_side = max(h, w)
    if max_side <= max_dim:
        return h, w
    scale = float(max_dim) / float(max_side)
    return max(64, int(round(h * scale))), max(64, int(round(w * scale)))


def _resize_field(field, shape):
    h, w = _shape2(shape)
    if field.shape == (h, w):
        return field.astype(np.float32)
    try:
        import cv2

        return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    except Exception:
        from PIL import Image

        img = Image.fromarray((np.clip(field, 0, 1) * 255).astype(np.uint8), mode="L")
        img = img.resize((w, h), Image.BILINEAR)
        return (np.asarray(img).astype(np.float32) / 255.0).astype(np.float32)


def _drip_field(shape, seed):
    h, w = _shape2(shape)
    key = ("drip", (int(h), int(w)), int(seed))
    cached = _FIELD_CACHE.get(key)
    if cached is not None:
        return cached.copy()
    work_h, work_w = _working_shape((h, w), 384)
    y, x = get_mgrid((work_h, work_w))
    rng = np.random.default_rng(seed + 4101)

    src_cols = rng.integers(0, work_w, max(24, int(work_w * 0.040)))
    drips = np.zeros((work_h, work_w), dtype=np.float32)
    yn = y / max(work_h - 1, 1)
    width_scale = max(work_w / 640.0, 0.75)
    for col in src_cols:
        width = rng.uniform(1.2, 3.4) * width_scale
        start = rng.uniform(0.02, 0.42)
        length = rng.uniform(0.20, 0.90)
        phase = rng.uniform(0, 6.28)
        wander = np.sin(yn * rng.uniform(7.0, 17.0) + phase) * rng.uniform(1.5, 5.8) * width_scale
        dist = np.abs(x - (col + wander))
        trail = np.exp(-(dist ** 2) / (2.0 * width ** 2))
        gravity = np.clip((yn - start) / max(length, 1e-4), 0, 1)
        trail *= (gravity > 0).astype(np.float32) * np.exp(-gravity * rng.uniform(1.1, 2.2))
        bead_y = np.clip(start + length * rng.uniform(0.55, 1.04), 0, 1)
        bead = np.exp(-((yn - bead_y) ** 2) / (2.0 * 0.0018)) * np.exp(
            -(dist ** 2) / (2.0 * (width * 2.5) ** 2)
        )
        drips += trail * 0.82 + bead * 1.10

    curtain = _norm01(_line_field((work_h, work_w), seed + 4102, np.pi / 2.0, 0.052, 0.10))
    mist = _mist((work_h, work_w), seed + 4103, 0.010, 0.36)
    low_field = np.clip(_norm01(drips) * 0.78 + curtain * 0.14 + mist * 0.32, 0, 1)
    out = _resize_field(low_field, (h, w))
    if len(_FIELD_CACHE) > 32:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[key] = out.copy()
    return out


def _roller_field(shape, seed):
    h, w = _shape2(shape)
    key = ("roller", (int(h), int(w)), int(seed))
    cached = _FIELD_CACHE.get(key)
    if cached is not None:
        return tuple(part.copy() for part in cached)
    work_h, work_w = _working_shape((h, w), 512)
    y, x = get_mgrid((work_h, work_w))
    lap = np.sin(x * 0.018 + multi_scale_noise((work_h, work_w), [18, 42], [0.55, 0.45], seed + 4401) * 2.1) * 0.5 + 0.5
    fiber = np.sin(x * 0.92 + y * 0.018 + multi_scale_noise((work_h, work_w), [3, 7], [0.7, 0.3], seed + 4402) * 3.0) * 0.5 + 0.5
    dry_edges = np.clip(1.0 - np.abs(lap - 0.52) * 4.0, 0, 1)
    streak = np.clip(lap * 0.34 + fiber * 0.44 + dry_edges * 0.28, 0, 1)
    out = (_resize_field(lap, (h, w)), _resize_field(fiber, (h, w)), _resize_field(streak, (h, w)))
    if len(_FIELD_CACHE) > 32:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[key] = tuple(part.copy() for part in out)
    return out


def _brush_fields(shape, seed):
    h, w = _shape2(shape)
    key = ("brush", (int(h), int(w)), int(seed))
    cached = _FIELD_CACHE.get(key)
    if cached is not None:
        return tuple(part.copy() for part in cached)
    work_h, work_w = _working_shape((h, w), 640)
    y, x = get_mgrid((work_h, work_w))
    angle = -0.12
    across = -np.sin(angle) * x + np.cos(angle) * y
    warp = multi_scale_noise((work_h, work_w), [36, 84, 168], [0.42, 0.36, 0.22], seed + 4601)
    stroke_width = max(42.0, min(160.0, max(h, w) * 0.070)) * (max(work_h, work_w) / max(h, w))
    bands = np.sin((across + warp * stroke_width * 0.95) * (2.0 * np.pi / stroke_width))
    bands = np.clip((bands + 0.58) * 0.64, 0, 1)
    taper = _norm01(multi_scale_noise((work_h, work_w), [90, 190, 360], [0.45, 0.35, 0.20], seed + 4602))
    bands = np.clip(bands * (0.58 + taper * 0.55), 0, 1)
    load = _norm01(multi_scale_noise((work_h, work_w), [120, 240, 420], [0.45, 0.35, 0.20], seed + 4603))
    bristle = (
        np.sin((across + warp * 7.0) * 0.92 + load * 2.4)
        + np.sin((across - warp * 4.0) * 1.85 + load * 1.4) * 0.38
        + np.sin((across + warp * 2.0) * 3.20) * 0.12
    )
    bristle = _norm01(bristle)
    ridges = bands * np.clip((bristle - 0.54) * 3.8, 0, 1)
    troughs = bands * np.clip((0.47 - bristle) * 3.5, 0, 1)
    dry_drag = bands * np.clip((0.42 - taper) * 2.2, 0, 1) * (0.55 + load * 0.45)
    stroke = np.clip(bands * 0.44 + ridges * 0.48 - troughs * 0.18, 0, 1)
    out = tuple(_resize_field(part, (h, w)) for part in (bands, ridges, troughs, dry_drag, stroke))
    if len(_FIELD_CACHE) > 32:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[key] = tuple(part.copy() for part in out)
    return out


def paint_drip_gravity(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    field = _drip_field((h, w), seed)

    dark = _base_tint(base, crush=0.35)
    wet = np.clip(base * (1.03 + field[:, :, None] * 0.22), 0, 1)
    tint = np.array([1.18, 0.74, 0.46], dtype=np.float32)
    cool_shadow = np.array([0.46, 0.58, 0.92], dtype=np.float32)
    lacquer = np.array([0.42, 0.18, 0.08], dtype=np.float32)
    effect = np.clip(
        dark * (1 - field[:, :, None] * 0.55)
        + wet * field[:, :, None] * 0.56
        + base * tint * field[:, :, None] * 0.24
        + lacquer * field[:, :, None] * 0.22
        + base * cool_shadow * (1.0 - field[:, :, None]) * 0.08,
        0,
        1,
    )
    effect = _add_paint_micro(effect, (h, w), seed + 4104, 0.25, field)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    out = np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.12 * blend, 0, 1)
    return out.astype(np.float32)


def spec_drip_gravity(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    field = _drip_field((h, w), seed)
    bead = _mist(_working_shape((h, w), 384), seed + 4103, 0.010, 0.75)
    bead = _resize_field(bead, (h, w))
    gravity = np.arange(h, dtype=np.float32)[:, None] / max(h - 1, 1)
    wet = np.clip(field * 0.82 + bead * 0.48 + gravity * 0.18, 0, 1)
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
    droplet_chroma = np.stack([
        fine * 0.16 + medium * 0.08,
        direction * 0.07,
        (1.0 - direction) * fine * 0.13,
    ], axis=2).astype(np.float32)
    effect = np.clip(
        base * (1 - splatter[:, :, None] * 0.42)
        + ink * splatter[:, :, None] * 0.55
        + highlight * fine[:, :, None] * 0.20
        + droplet_chroma * splatter[:, :, None],
        0,
        1,
    )
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
    wh, ww = _working_shape((h, w), 768)
    pores = _resize_field(multi_scale_noise((wh, ww), [1, 2, 5, 11], [0.36, 0.28, 0.22, 0.14], seed + 4301), (h, w))
    pores = _norm01(pores)
    holes = np.clip((0.42 - pores) * 3.6, 0, 1)
    raised = np.clip((pores - 0.58) * 3.0, 0, 1)
    mottled = _resize_field(multi_scale_noise((wh, ww), [6, 14, 28], [0.45, 0.35, 0.20], seed + 4302), (h, w))
    field = np.clip(raised * 0.62 - holes * 0.34 + _norm01(mottled) * 0.28, 0, 1)
    warm = np.clip(base * np.array([1.08, 1.02, 0.92], dtype=np.float32), 0, 1)
    cool_shadow = np.clip(base * np.array([0.72, 0.78, 0.86], dtype=np.float32), 0, 1)
    effect = np.clip(base * 0.55 + warm * field[:, :, None] * 0.55 + cool_shadow * holes[:, :, None] * 0.35, 0, 1)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.06 * blend, 0, 1).astype(np.float32)


def spec_sponge_stipple(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    wh, ww = _working_shape((h, w), 768)
    pores = _norm01(_resize_field(multi_scale_noise((wh, ww), [1, 2, 5, 11], [0.36, 0.28, 0.22, 0.14], seed + 4301), (h, w)))
    micro = np.clip(np.abs(pores - 0.5) * 2.0, 0, 1)
    M = np.clip(base_m * 0.12 + micro * 62.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(78.0 + micro * 92.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(70.0 + micro * 105.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_roller_streak(paint, shape, mask, seed, pm, bb):
    base = _as_rgb(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _shape2(shape)
    lap, fiber, streak = _roller_field((h, w), seed)
    warm = np.array([1.08, 0.98, 0.84], dtype=np.float32)
    cool = np.array([0.78, 0.88, 1.06], dtype=np.float32)
    effect = np.clip(base * (0.84 + streak[:, :, None] * 0.24) + base * warm * lap[:, :, None] * 0.12 + base * cool * fiber[:, :, None] * 0.10, 0, 1)
    effect = _add_paint_micro(effect, (h, w), seed + 4404, 0.20, streak)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.07 * blend, 0, 1).astype(np.float32)


def spec_roller_streak(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    lap, fiber, _streak = _roller_field((h, w), seed)
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
    wh, ww = _working_shape((h, w), 768)
    fade_noise = _resize_field(multi_scale_noise((wh, ww), [10, 22, 48], [0.45, 0.35, 0.20], seed + 4501), (h, w))
    fade = fade + (fade_noise - 0.5) * 0.13
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
    bands, ridges, troughs, dry_drag, stroke = _brush_fields((h, w), seed)
    rich = np.clip(base * (0.82 + bands[:, :, None] * 0.30 + stroke[:, :, None] * 0.08), 0, 1)
    warm_ridge = np.array([1.10, 1.03, 0.92], dtype=np.float32)
    cool_trough = np.array([0.72, 0.80, 0.90], dtype=np.float32)
    effect = np.clip(
        rich * (1 - troughs[:, :, None] * 0.28)
        + base * warm_ridge * ridges[:, :, None] * 0.18
        + base * cool_trough * dry_drag[:, :, None] * 0.14
        - troughs[:, :, None] * 0.08,
        0,
        1,
    )
    effect = _add_paint_micro(effect, (h, w), seed + 4604, 0.10, stroke)
    blend = np.clip(pm, 0, 1) * _mask3(mask)
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.10 * blend * stroke[:, :, None], 0, 1).astype(np.float32)


def spec_brush_stroke(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    bands, ridges, troughs, _dry_drag, _stroke = _brush_fields((h, w), seed)
    M = np.clip(base_m * 0.12 + ridges * 70.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(40.0 + troughs * 122.0 * sm + bands * 28.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + troughs * 134.0 * sm + (1 - bands) * 12.0, 16, 255).astype(np.float32)
    return M, R, CC
