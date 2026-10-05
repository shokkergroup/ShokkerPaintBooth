"""Owner-review Premium Luxury base renderers for SPB-30."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, sobel

from engine.core import multi_scale_noise


_PL_PAIR_FIELD_CACHE = {}
# SPB paint-finish perf loop tick 2026-05-31 06:53; owner: "Speed is king in this app."
# Exact paired-field reuse for targeted luxury paint/spec renders; preserves finish detail while avoiding duplicate 2048² recipe fields.
# Lamborghini Verde 2016.4->1960.9 ms with paint/spec std drift 0.


def _pair_cache_put(key, value):
    if len(_PL_PAIR_FIELD_CACHE) > 48:
        _PL_PAIR_FIELD_CACHE.clear()
    _PL_PAIR_FIELD_CACHE[key] = value
    return value


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _grid(shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy / max(h - 1, 1), xx / max(w - 1, 1)


def _norm(v):
    v = np.asarray(v, dtype=np.float32)
    lo = float(v.min())
    hi = float(v.max())
    if hi - lo < 1e-6:
        return np.zeros_like(v, dtype=np.float32)
    return ((v - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, seed, scales=(2, 5, 13, 31), weights=(0.28, 0.30, 0.25, 0.17)):
    return _norm(multi_scale_noise(shape, list(scales), list(weights), seed))


def _blend(paint, mask, pm, color, strength=0.94):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask, 0, 1)[:, :, None] * np.clip(pm * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1 - a) + np.clip(color, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _hsv(h, s, v):
    h, s, v = np.broadcast_arrays(h, s, v)
    h = np.mod(h, 1.0).astype(np.float32)
    s = np.clip(s, 0, 1).astype(np.float32)
    v = np.clip(v, 0, 1).astype(np.float32)
    i = np.floor(h * 6.0).astype(np.int32) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    rgb = np.empty(h.shape + (3,), dtype=np.float32)
    cases = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))
    for idx, vals in enumerate(cases):
        m = i == idx
        for c in range(3):
            rgb[..., c][m] = vals[c][m]
    return rgb


def _sparkle(shape, seed, density=0.020, blur=0.45):
    h, w = shape
    rng = np.random.default_rng((seed + 211) & 0xFFFFFFFF)
    out = np.zeros((h, w), dtype=np.float32)
    n = min(int(h * w * density), 160000)
    if n:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.2, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.25, np.roll(out, -1, 1) * 0.25])
    if blur:
        out = gaussian_filter(out, sigma=blur)
    return np.clip(out, 0, 1).astype(np.float32)


def _line(shape, seed, angle, freq, width=0.018, warp=0.016):
    y, x = _grid(shape)
    n = _noise(shape, seed + 3, (5, 13, 29), (0.32, 0.36, 0.32))
    coord = x * np.cos(angle) + y * np.sin(angle) + (n - 0.5) * warp
    d = np.abs(np.sin(coord * freq * np.pi))
    return np.clip((width - d) / max(width, 1e-5), 0, 1).astype(np.float32)


def _spec(shape, seed, metallic=100, rough=22, cc=26, detail=None, smooth=True):
    base = _noise(shape, seed + 31, (2, 6, 15, 39), (0.30, 0.30, 0.24, 0.16))
    if detail is None:
        detail = base
    detail = np.clip(detail, 0, 1)
    M = np.clip(metallic + detail * 70 + base * 18, 0, 255)
    R = np.clip((14 if smooth else rough) + (1 - detail) * rough + base * 8, 15, 255)
    CC = np.clip(cc + detail * 24 + base * 9, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def _lamborghini_verde_fields(shape, seed):
    h, w = shape
    key = ("lamborghini_verde", int(h), int(w), int(seed))
    cached = _PL_PAIR_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    _y, x = _grid((h, w))
    pearl = _noise((h, w), seed + 40, (4, 11, 27, 63), (0.28, 0.30, 0.26, 0.16))
    flake = _sparkle((h, w), seed + 41, 0.018, 0.48)
    return _pair_cache_put(key, (x, pearl, flake))


def paint_bentley_silver(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    grain = _line((h, w), seed, 0.03, 118.0, 0.024, 0.010)
    flake = _sparkle((h, w), seed + 1, 0.018, 0.42)
    cloud = _noise((h, w), seed + 2, (7, 19, 47), (0.30, 0.36, 0.34))
    silver = 0.56 + cloud * 0.12 + grain * 0.08 + flake * 0.16
    color = np.stack([silver * 1.02, silver, silver * 0.96], axis=-1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_bentley_silver(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_line((h, w), seed, 0.03, 118.0, 0.024, 0.010) + _sparkle((h, w), seed + 1, 0.018, 0.42), 0, 1)
    return _spec((h, w), seed, 176, 18, 32, detail, True)


def paint_bugatti_blue(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    depth = _noise((h, w), seed + 10, (6, 15, 37, 83), (0.25, 0.31, 0.28, 0.16))
    pearl = _sparkle((h, w), seed + 11, 0.012, 0.55)
    micro = _noise((h, w), seed + 12, (1, 2, 5, 11), (0.38, 0.30, 0.21, 0.11))
    woven = _line((h, w), seed + 13, -0.72, 164.0, 0.014, 0.014)
    cross = _line((h, w), seed + 14, 0.50, 211.0, 0.010, 0.010)
    enamel = np.clip(depth * 0.62 + micro * 0.20 + woven * 0.10 + cross * 0.08, 0, 1)
    color = _hsv(
        0.612 + x * 0.040 + depth * 0.055 + woven * 0.020,
        0.76 + cross * 0.10,
        0.18 + enamel * 0.29 + pearl * 0.14,
    )
    color[:, :, 0] *= 0.46
    color[:, :, 1] *= 0.68 + woven * 0.05
    color[:, :, 2] += cross * 0.055
    return _blend(paint, mask, pm, color, 0.94)


def spec_bugatti_blue(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(
        _noise((h, w), seed + 10, (6, 15, 37, 83), (0.25, 0.31, 0.28, 0.16)) * 0.70
        + _line((h, w), seed + 13, -0.72, 164.0, 0.014, 0.014) * 0.18
        + _line((h, w), seed + 14, 0.50, 211.0, 0.010, 0.010) * 0.12,
        0,
        1,
    )
    return _spec((h, w), seed, 92, 18, 36, detail, True)


def paint_ferrari_rosso(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    depth = _noise((h, w), seed + 20, (5, 13, 29, 71), (0.24, 0.30, 0.30, 0.16))
    metallic = _sparkle((h, w), seed + 21, 0.018, 0.48)
    red = 0.52 + depth * 0.38 + metallic * 0.14
    color = np.stack([red, 0.025 + depth * 0.035, 0.018 + depth * 0.020], axis=-1)
    return _blend(paint, mask, pm, color, 0.95)


def spec_ferrari_rosso(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 20, (5, 13, 29, 71), (0.24, 0.30, 0.30, 0.16)) + _sparkle((h, w), seed + 21, 0.018, 0.48), 0, 1)
    return _spec((h, w), seed, 116, 16, 42, detail, True)


def _carbon_twill(shape, seed, scale=98.0):
    y, x = _grid(shape)
    n = _noise(shape, seed + 30, (3, 9, 21), (0.32, 0.34, 0.34))
    u = (x + y * 1.18 + (n - 0.5) * 0.026) * scale
    v = (x * 0.88 - y + (n - 0.5) * 0.026) * scale
    a = np.clip((0.42 - np.abs(np.sin(u * np.pi))) * 3.2, 0, 1)
    b = np.clip((0.42 - np.abs(np.sin(v * np.pi))) * 3.2, 0, 1)
    over = ((np.floor(u / 2) + np.floor(v / 2)) % 2).astype(np.float32)
    return np.clip(a * over + b * (1 - over), 0, 1).astype(np.float32), n


def paint_koenigsegg_clear(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    weave, n = _carbon_twill((h, w), seed, 112.0)
    clear = _noise((h, w), seed + 32, (8, 23, 61), (0.28, 0.36, 0.36))
    base = 0.055 + weave * 0.105 + n * 0.035
    color = np.stack([base * 1.28 + clear * 0.035, base * 0.92, base * 0.58], axis=-1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_koenigsegg_clear(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    weave, n = _carbon_twill((h, w), seed, 112.0)
    return _spec((h, w), seed, 68, 20, 42, np.clip(weave * 0.8 + n * 0.25, 0, 1), True)


def paint_lamborghini_verde(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    x, pearl, flake = _lamborghini_verde_fields((h, w), seed)
    color = _hsv(0.29 + x * 0.06 + pearl * 0.11, 0.88, 0.40 + pearl * 0.36 + flake * 0.18)
    color[:, :, 0] += flake * 0.16
    return _blend(paint, mask, pm, np.clip(color, 0, 1), 0.95)


def spec_lamborghini_verde(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    _x, pearl, flake = _lamborghini_verde_fields((h, w), seed)
    detail = np.clip(pearl + flake, 0, 1)
    return _spec((h, w), seed, 112, 18, 34, detail, True)


def paint_maybach_two_tone(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    wave = (_noise((h, w), seed + 50, (23, 71), (0.55, 0.45)) - 0.5) * 0.018
    split = 1.0 / (1.0 + np.exp(-115.0 * (y - 0.49 - wave)))
    upper = _noise((h, w), seed + 51, (8, 23, 59), (0.28, 0.36, 0.36))
    lower = _noise((h, w), seed + 52, (4, 13, 37), (0.28, 0.34, 0.38))
    lacquer = _noise((h, w), seed + 53, (1, 3, 7, 17), (0.34, 0.30, 0.22, 0.14))
    brushed = _line((h, w), seed + 54, 0.015, 168.0, 0.012, 0.006)
    pin = _line((h, w), seed + 55, 0.00, 118.0, 0.007, 0.003)
    coach = np.clip((0.010 - np.abs(y - 0.49 - wave)) * 80.0, 0, 1)
    top = np.stack([
        0.030 + upper * 0.065 + lacquer * 0.020,
        0.028 + upper * 0.052 + lacquer * 0.016,
        0.034 + upper * 0.050 + brushed * 0.030,
    ], axis=-1)
    bottom = np.stack([
        0.55 + lower * 0.15 + brushed * 0.055,
        0.50 + lower * 0.12 + lacquer * 0.030,
        0.42 + lower * 0.10 + pin * 0.035,
    ], axis=-1)
    color = top * (1 - split[:, :, None]) + bottom * split[:, :, None] + coach[:, :, None] * [0.38, 0.34, 0.22]
    return _blend(paint, mask, pm, color, 0.94)


def spec_maybach_two_tone(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    y, _ = _grid((h, w))
    split = 1.0 / (1.0 + np.exp(-115.0 * (y - 0.49)))
    detail = np.clip(
        split * 0.46
        + _noise((h, w), seed + 52, (4, 13, 37), (0.28, 0.34, 0.38)) * 0.27
        + _noise((h, w), seed + 53, (1, 3, 7, 17), (0.34, 0.30, 0.22, 0.14)) * 0.17
        + _line((h, w), seed + 54, 0.015, 168.0, 0.012, 0.006) * 0.10,
        0,
        1,
    )
    return _spec((h, w), seed, 84, 18, 38, detail, True)


def paint_mclaren_orange(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    glow = _noise((h, w), seed + 60, (5, 15, 41, 97), (0.24, 0.30, 0.30, 0.16))
    flake = _sparkle((h, w), seed + 61, 0.018, 0.45)
    color = np.stack([0.86 + glow * 0.14, 0.33 + glow * 0.18 + flake * 0.08, 0.025 + flake * 0.04], axis=-1)
    return _blend(paint, mask, pm, color, 0.95)


def spec_mclaren_orange(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 60, (5, 15, 41, 97), (0.24, 0.30, 0.30, 0.16)) + _sparkle((h, w), seed + 61, 0.018, 0.45), 0, 1)
    return _spec((h, w), seed, 96, 17, 34, detail, True)


def paint_pagani_tricolore(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    angle = np.clip(x * 0.42 + y * 0.24 + _noise((h, w), seed + 70, (7, 19, 47), (0.30, 0.36, 0.34)) * 0.36, 0, 1)
    c1 = np.array([0.08, 0.11, 0.34], dtype=np.float32)
    c2 = np.array([0.82, 0.72, 0.45], dtype=np.float32)
    c3 = np.array([0.48, 0.04, 0.10], dtype=np.float32)
    w1 = np.clip(1 - np.abs(angle - 0.18) * 3.2, 0, 1)
    w2 = np.clip(1 - np.abs(angle - 0.50) * 3.0, 0, 1)
    w3 = np.clip(1 - np.abs(angle - 0.82) * 3.2, 0, 1)
    denom = w1 + w2 + w3 + 1e-5
    color = (c1 * w1[:, :, None] + c2 * w2[:, :, None] + c3 * w3[:, :, None]) / denom[:, :, None]
    color += _sparkle((h, w), seed + 71, 0.014, 0.50)[:, :, None] * [0.12, 0.10, 0.08]
    return _blend(paint, mask, pm, color, 0.94)


def spec_pagani_tricolore(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = _noise((h, w), seed + 70, (7, 19, 47), (0.30, 0.36, 0.34))
    return _spec((h, w), seed, 126, 18, 36, detail, True)


def paint_porsche_pts(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    peel = _noise((h, w), seed + 80, (1, 2, 5, 13), (0.34, 0.30, 0.22, 0.14))
    flow = _noise((h, w), seed + 81, (17, 41, 91), (0.30, 0.36, 0.34))
    pearl = _sparkle((h, w), seed + 82, 0.014, 0.52)
    ribbon = _line((h, w), seed + 83, -0.24, 92.0, 0.018, 0.020)
    flop = _norm(np.sin((x * 1.25 + y * 0.42 + flow * 0.18) * np.pi))
    hue = 0.710 + flow * 0.050 + ribbon * 0.030 + flop * 0.025
    color = _hsv(hue, 0.31 + flow * 0.14 + ribbon * 0.10, 0.20 + peel * 0.090 + flow * 0.070 + pearl * 0.050)
    color[:, :, 0] += ribbon * 0.035
    color[:, :, 1] += flop * 0.025
    color[:, :, 2] += pearl * 0.070
    return _blend(paint, mask, pm, color, 0.94)


def spec_porsche_pts(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(
        _noise((h, w), seed + 80, (1, 2, 5, 13), (0.34, 0.30, 0.22, 0.14)) * 0.60
        + _sparkle((h, w), seed + 82, 0.014, 0.52) * 0.20
        + _line((h, w), seed + 83, -0.24, 92.0, 0.018, 0.020) * 0.20,
        0,
        1,
    )
    return _spec((h, w), seed, 8, 22, 40, detail, True)


def paint_satin_gold(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    grain = _line((h, w), seed + 90, -0.06, 116.0, 0.022, 0.010)
    satin = _noise((h, w), seed + 91, (4, 11, 31, 73), (0.26, 0.31, 0.27, 0.16))
    color = _hsv(0.112 + satin * 0.025, 0.48 + grain * 0.12, 0.34 + satin * 0.18 + grain * 0.09)
    return _blend(paint, mask, pm, color, 0.94)


def spec_satin_gold(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    grain = _line((h, w), seed + 90, -0.06, 116.0, 0.022, 0.010)
    return _spec((h, w), seed, 132, 44, 26, grain, False)


OWNER_REVIEW_PREMIUM_LUXURY_OVERRIDES = {
    "bentley_silver": (paint_bentley_silver, spec_bentley_silver),
    "bugatti_blue": (paint_bugatti_blue, spec_bugatti_blue),
    "ferrari_rosso": (paint_ferrari_rosso, spec_ferrari_rosso),
    "koenigsegg_clear": (paint_koenigsegg_clear, spec_koenigsegg_clear),
    "lamborghini_verde": (paint_lamborghini_verde, spec_lamborghini_verde),
    "maybach_two_tone": (paint_maybach_two_tone, spec_maybach_two_tone),
    "mclaren_orange": (paint_mclaren_orange, spec_mclaren_orange),
    "pagani_tricolore": (paint_pagani_tricolore, spec_pagani_tricolore),
    "porsche_pts": (paint_porsche_pts, spec_porsche_pts),
    "satin_gold": (paint_satin_gold, spec_satin_gold),
}
