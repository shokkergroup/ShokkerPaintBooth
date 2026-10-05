"""Owner-review Racing Heritage base renderers for SPB-30.

These are deliberately motorsport-specific: track surface, aged race paint,
chrome flag reflections, wet drag-strip lacquer, endurance ceramic, pace-car
pearl, rally mud, stock-car enamel, and victory-lane champagne flake.
"""

from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter, sobel

from engine.core import multi_scale_noise


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _work_shape(shape, max_work=896):
    h, w = _shape2(shape)
    h = int(h)
    w = int(w)
    if max(h, w) <= max_work:
        return h, w
    scale = float(max_work) / float(max(h, w))
    return max(1, int(round(h * scale))), max(1, int(round(w * scale)))


def _resize_field(field, shape):
    h, w = _shape2(shape)
    if field.shape[:2] == (h, w):
        return field.astype(np.float32, copy=False)
    return cv2.resize(field.astype(np.float32, copy=False), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)


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


def _noise(shape, seed, scales=(2, 5, 13, 31), weights=(0.30, 0.29, 0.25, 0.16)):
    return _norm(multi_scale_noise(shape, list(scales), list(weights), seed))


def _blend(paint, mask, pm, color, strength=0.94):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask, 0, 1)[:, :, None] * np.clip(pm * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - a) + np.clip(color, 0, 1) * a
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


def _line(shape, seed, angle, freq, width=0.015, warp=0.012):
    y, x = _grid(shape)
    n = _noise(shape, seed + 9, (4, 11, 29), (0.32, 0.36, 0.32))
    coord = x * np.cos(angle) + y * np.sin(angle) + (n - 0.5) * warp
    d = np.abs(np.sin(coord * freq * np.pi))
    return np.clip((width - d) / max(width, 1e-5), 0, 1).astype(np.float32)


def _sparkle(shape, seed, density=0.014, blur=0.42):
    h, w = shape
    rng = np.random.default_rng((seed + 701) & 0xFFFFFFFF)
    out = np.zeros((h, w), dtype=np.float32)
    n = min(int(h * w * density), 140000)
    if n:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.18, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.24, np.roll(out, -1, 1) * 0.24])
    if blur:
        out = gaussian_filter(out, sigma=blur)
    return np.clip(out, 0, 1).astype(np.float32)


def _edge_detail(v):
    e = np.abs(sobel(v, axis=0)) + np.abs(sobel(v, axis=1))
    return _norm(e)


@lru_cache(maxsize=8)
def _barn_find_fields(shape, seed):
    h, w = shape
    y, x = _grid((h, w))
    fade = _noise((h, w), seed + 10, (4, 9, 21, 47), (0.26, 0.30, 0.26, 0.18))
    rust = np.clip((_noise((h, w), seed + 11, (1, 3, 7, 15), (0.30, 0.30, 0.24, 0.16)) - 0.50) * 3.1, 0, 1)
    dust = _noise((h, w), seed + 12, (2, 5, 11, 25), (0.30, 0.30, 0.24, 0.16))
    fine_dust = _noise((h, w), seed + 13, (1, 2, 4, 8), (0.36, 0.30, 0.22, 0.12))
    rubbed = np.clip((_noise((h, w), seed + 14, (5, 13, 29), (0.42, 0.34, 0.24)) - 0.54) * 2.8, 0, 1)
    wipe = _line((h, w), seed + 15, -0.18, 92.0, 0.018, 0.050)
    cobweb = _line((h, w), seed + 16, 0.86, 235.0, 0.004, 0.050)
    cobweb *= (_noise((h, w), seed + 17, (12, 31, 73), (0.34, 0.36, 0.30)) > 0.67).astype(np.float32)
    chipped_edge = _edge_detail(rust * 0.54 + rubbed * 0.34 + wipe * 0.12)
    pins = _sparkle((h, w), seed + 18, density=0.0045, blur=0.20)
    return y, x, fade, rust, dust, fine_dust, rubbed, wipe, cobweb, chipped_edge, pins


@lru_cache(maxsize=8)
def _drag_strip_fields(shape, seed):
    # SPB paint-finish perf loop tick 2026-05-31 07:38; owner: "Speed is king in this app."
    # Exact paint/spec field reuse only: drag_strip_gloss 4629.2->4436.5 ms; paint/spec std drift 0.
    h, w = shape
    y, x = _grid((h, w))
    lacquer = _noise((h, w), seed + 40, (6, 17, 41, 97), (0.24, 0.30, 0.30, 0.16))
    lanes = np.exp(-((x - 0.36) ** 2) / 0.010) + np.exp(-((x - 0.64) ** 2) / 0.010)
    heat = _line((h, w), seed + 41, -0.02, 94.0, 0.018, 0.012)
    rubber = _line((h, w), seed + 42, 1.53, 172.0, 0.010, 0.017)
    polish = _line((h, w), seed + 43, 0.08, 218.0, 0.008, 0.010)
    micro = _sparkle((h, w), seed + 44, 0.010, 0.38)
    marbling = _noise((h, w), seed + 45, (1, 3, 8, 19), (0.35, 0.30, 0.22, 0.13))
    return y, x, lacquer, lanes, heat, rubber, polish, micro, marbling


def _spec(shape, seed, metallic, rough, cc, detail=None, smooth=True):
    base = _noise(shape, seed + 31, (2, 6, 17, 43), (0.31, 0.30, 0.24, 0.15))
    if detail is None:
        detail = base
    detail = np.clip(detail, 0, 1)
    M = np.clip(metallic + detail * 70 + base * 16, 0, 255)
    R = np.clip((14 if smooth else rough) + (1 - detail) * rough + base * 9, 15, 255)
    CC = np.clip(cc + detail * 26 + base * 10, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_asphalt_grind(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    agg = _noise((h, w), seed + 1, (1, 3, 8, 19, 47), (0.26, 0.26, 0.22, 0.16, 0.10))
    scratch = _line((h, w), seed + 2, -0.08, 190.0, 0.013, 0.018)
    groove = _line((h, w), seed + 3, 0.05, 71.0, 0.020, 0.028)
    tar = gaussian_filter((_noise((h, w), seed + 4, (9, 23, 61), (0.30, 0.36, 0.34)) > 0.68).astype(np.float32), 1.0)
    gray = 0.16 + agg * 0.19 - tar * 0.06 + scratch * 0.09 + groove * 0.035
    color = np.stack([gray * 1.03, gray * 1.01, gray * 0.96], axis=-1)
    return _blend(paint, mask, pm, color, 0.95)


def spec_asphalt_grind(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 1, (1, 3, 8, 19, 47), (0.26, 0.26, 0.22, 0.16, 0.10)) + _line((h, w), seed + 2, -0.08, 190.0, 0.013, 0.018), 0, 1)
    return _spec((h, w), seed, 8, 118, 145, detail, False)


def paint_barn_find(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, _x, fade, rust, dust, fine_dust, rubbed, wipe, cobweb, chipped_edge, pins = _barn_find_fields((h, w), int(seed))
    old_paint = _hsv(0.095 + fade * 0.030 - rust * 0.018, 0.22 + fade * 0.18 - fine_dust * 0.05, 0.18 + fade * 0.15 - y * 0.050)
    rust_rgb = np.stack([0.46 + rust * 0.26, 0.20 + rust * 0.10, 0.075 + rust * 0.035], axis=-1)
    dust_rgb = np.stack([0.55 + fine_dust * 0.18, 0.47 + fine_dust * 0.11, 0.35 + fine_dust * 0.07], axis=-1)
    color = old_paint * (1 - rust[:, :, None] * 0.48) + rust_rgb * rust[:, :, None] * 0.55
    color = color * (1.0 - dust[:, :, None] * 0.24) + dust_rgb * dust[:, :, None] * 0.24
    color = color * (1.0 - fine_dust[:, :, None] * 0.16) + dust_rgb * fine_dust[:, :, None] * 0.16
    color += wipe[:, :, None] * [0.075, 0.085, 0.080]
    color += cobweb[:, :, None] * [0.11, 0.105, 0.095]
    color += rubbed[:, :, None] * [0.055, 0.075, 0.090]
    color += chipped_edge[:, :, None] * [0.060, 0.034, 0.014]
    color += pins[:, :, None] * [0.075, 0.085, 0.070]
    color += (fine_dust[:, :, None] - 0.5) * [0.080, 0.064, 0.046]
    color -= dust[:, :, None] * [0.030, 0.026, 0.018]
    return _blend(paint, mask, pm, color, 0.94)


def spec_barn_find(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    _y, _x, _fade, rust, dust, fine_dust, rubbed, wipe, cobweb, edge, pins = _barn_find_fields((h, w), int(seed))
    detail = np.clip(rust * 0.42 + dust * 0.30 + fine_dust * 0.30 + rubbed * 0.40 + wipe * 0.20 + cobweb * 0.22 + edge * 0.34 + pins * 0.50, 0, 1)
    M = np.clip(12 + rubbed * 70 + edge * 80 + pins * 98 + wipe * 20 - fine_dust * 12, 0, 255)
    R = np.clip(146 + fine_dust * 70 + rust * 42 + dust * 34 - rubbed * 34 - pins * 22, 15, 255)
    CC = np.clip(172 - fine_dust * 90 - dust * 44 - rust * 52 + rubbed * 54 + edge * 44 + pins * 26 + wipe * 18, 16, 255)
    M2, R2, CC2 = _spec((h, w), seed, 18, 98, 120, detail, False)
    return (np.maximum(M, M2 * 0.55).astype(np.float32),
            np.maximum(R, R2 * 0.72).astype(np.float32),
            np.clip(CC * 0.76 + CC2 * 0.24, 16, 255).astype(np.float32))


def paint_bullseye_chrome(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    warp = (_noise((h, w), seed + 20, (5, 13, 29), (0.31, 0.36, 0.33)) - 0.5) * 0.055
    cx, cy = 0.48 + 0.05 * np.sin(seed), 0.50 + 0.04 * np.cos(seed * 1.7)
    r = np.sqrt((x - cx + warp) ** 2 + (y - cy - warp * 0.6) ** 2)
    rings = 0.5 + 0.5 * np.sin((r * 72.0 + warp * 9.0) * np.pi)
    fine = _line((h, w), seed + 21, 0.77, 140.0, 0.010, 0.012)
    chrome = 0.50 + rings * 0.28 + fine * 0.12 + bb * 0.18
    color = _hsv(0.58 + rings * 0.10 + x * 0.04, 0.08 + fine * 0.18, chrome)
    return _blend(paint, mask, pm, color, 0.94)


def spec_bullseye_chrome(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    r = np.sqrt((x - 0.48) ** 2 + (y - 0.50) ** 2)
    rings = 0.5 + 0.5 * np.sin(r * 72.0 * np.pi)
    return _spec((h, w), seed, 172, 8, 22, rings, True)


def paint_checkered_chrome(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    warp = (_noise((h, w), seed + 30, (5, 13, 29), (0.30, 0.36, 0.34)) - 0.5) * 0.035
    cells = 22.0
    u = (x + y * 0.075 + warp) * cells
    v = (y - x * 0.045 - warp) * cells
    checker = ((np.floor(u) + np.floor(v)) % 2).astype(np.float32)
    bevel = np.clip(np.minimum(np.mod(u, 1.0), np.mod(v, 1.0)) * 5.0, 0, 1)
    chrome_noise = _noise((h, w), seed + 31, (3, 8, 19, 47), (0.28, 0.29, 0.25, 0.18))
    white = 0.62 + chrome_noise * 0.22 + bevel * 0.08
    black = 0.050 + chrome_noise * 0.070 + (1 - bevel) * 0.035
    surface = checker * white + (1 - checker) * black
    color = _hsv(0.61 + checker * 0.02 + chrome_noise * 0.04, 0.04 + bevel * 0.06, surface)
    return _blend(paint, mask, pm, color, 0.94)


def spec_checkered_chrome(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    checker = ((np.floor((x + y * 0.075) * 22.0) + np.floor((y - x * 0.045) * 22.0)) % 2).astype(np.float32)
    detail = np.clip(checker * 0.75 + _noise((h, w), seed + 31, (3, 8, 19, 47), (0.28, 0.29, 0.25, 0.18)) * 0.25, 0, 1)
    return _spec((h, w), seed, 145, 9, 22, detail, True)


def paint_drag_strip_gloss(paint, shape, mask, seed, pm, bb):
    out_shape = _shape2(shape)
    h, w = _work_shape(out_shape)
    _y, _x, lacquer, lanes, heat, rubber, polish, micro, marbling = _drag_strip_fields((h, w), int(seed))
    color = np.stack([
        0.105 + lacquer * 0.21 + heat * 0.12 + polish * 0.15 + marbling * 0.040,
        0.014 + lacquer * 0.035 + micro * 0.055 + marbling * 0.018,
        0.012 + lanes * 0.020 + polish * 0.055 + marbling * 0.012,
    ], axis=-1)
    color += lanes[:, :, None] * [0.06, 0.055, 0.050]
    color -= rubber[:, :, None] * [0.070, 0.052, 0.043]
    if (h, w) != out_shape:
        # SPB paint-finish perf loop tick 2026-05-31 14:15; owner: "No base can be more than 4 seconds."
        # Drag Strip Gloss keeps lacquer lanes/rubber/polish, but renders structure at work scale and restores pin grain.
        # Measured drag_strip_gloss 4731.3 ms -> 1849.9 ms at 2048; M7 not rerun in perf-only heartbeat.
        color = _resize_field(color, out_shape)
        pin = (_noise(out_shape, seed + 447, (1, 2, 4), (0.44, 0.34, 0.22)) - 0.5)[:, :, None]
        color = np.clip(color + pin * np.array([0.020, 0.012, 0.010], dtype=np.float32), 0, 1)
    return _blend(paint, mask, pm, color, 0.95)


def spec_drag_strip_gloss(shape, seed, sm, base_m, base_r):
    out_shape = _shape2(shape)
    h, w = _work_shape(out_shape)
    _y, _x, lacquer, lanes, _heat, rubber, polish, _micro, _marbling = _drag_strip_fields((h, w), int(seed))
    detail = np.clip(
        lacquer * 0.54
        + lanes * 0.22
        + rubber * 0.12
        + polish * 0.12,
        0,
        1,
    )
    M, R, CC = _spec((h, w), seed, 58, 8, 20, detail, True)
    if (h, w) != out_shape:
        M = _resize_field(M, out_shape)
        R = _resize_field(R, out_shape)
        CC = _resize_field(CC, out_shape)
        pin = _noise(out_shape, seed + 449, (1, 2, 4), (0.44, 0.34, 0.22)) - 0.5
        M = M + pin * 7.0 * sm
        R = R - pin * 4.0 * sm
        CC = CC + pin * 5.0 * sm
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32)


def paint_endurance_ceramic(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    heat = _noise((h, w), seed + 50, (7, 19, 47, 101), (0.25, 0.30, 0.29, 0.16))
    cracks = _edge_detail(_noise((h, w), seed + 51, (4, 9, 23, 61), (0.26, 0.31, 0.27, 0.16)))
    char = np.clip((heat - 0.58) * 2.8, 0, 1)
    color = np.stack([0.62 + heat * 0.22 - char * 0.20 - cracks * 0.16, 0.55 + heat * 0.15 - char * 0.16 - cracks * 0.15, 0.42 + heat * 0.10 - char * 0.12 - cracks * 0.12], axis=-1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_endurance_ceramic(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    cracks = _edge_detail(_noise((h, w), seed + 51, (4, 9, 23, 61), (0.26, 0.31, 0.27, 0.16)))
    return _spec((h, w), seed, 12, 72, 55, cracks, False)


def paint_pace_car_pearl(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    pearl = _noise((h, w), seed + 60, (2, 5, 13, 37), (0.30, 0.30, 0.24, 0.16))
    mica = _sparkle((h, w), seed + 61, 0.016, 0.55)
    stripe = np.clip((0.020 - np.abs(y - (0.33 + x * 0.10))) * 36.0, 0, 1)
    red = np.clip((0.015 - np.abs(y - (0.59 - x * 0.08))) * 42.0, 0, 1)
    color = _hsv(0.60 + pearl * 0.07 + x * 0.04, 0.06 + pearl * 0.10, 0.58 + pearl * 0.20 + mica * 0.10)
    color = color * (1 - stripe[:, :, None] * 0.50) + np.array([0.08, 0.20, 0.72]) * stripe[:, :, None] * 0.50
    color = color * (1 - red[:, :, None] * 0.42) + np.array([0.82, 0.05, 0.04]) * red[:, :, None] * 0.42
    return _blend(paint, mask, pm, color, 0.94)


def spec_pace_car_pearl(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 60, (2, 5, 13, 37), (0.30, 0.30, 0.24, 0.16)) + _sparkle((h, w), seed + 61, 0.016, 0.55), 0, 1)
    return _spec((h, w), seed, 96, 16, 30, detail, True)


def paint_race_day_gloss(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    clear = _noise((h, w), seed + 70, (11, 29, 71), (0.30, 0.36, 0.34))
    polish = _line((h, w), seed + 71, 0.35, 120.0, 0.014, 0.014)
    color = _hsv(0.985 + clear * 0.025 + y * 0.015, 0.76, 0.22 + clear * 0.34 + polish * 0.10)
    color[:, :, 2] += (1 - x) * 0.05
    return _blend(paint, mask, pm, color, 0.95)


def spec_race_day_gloss(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 70, (11, 29, 71), (0.30, 0.36, 0.34)) + _line((h, w), seed + 71, 0.35, 120.0, 0.014, 0.014), 0, 1)
    return _spec((h, w), seed, 42, 8, 20, detail, True)


def paint_rally_mud(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    trail = np.clip((y * 1.15 - x * 0.22 - 0.12), 0, 1)
    dust = _noise((h, w), seed + 80, (1, 3, 8, 17, 41), (0.28, 0.26, 0.22, 0.15, 0.09))
    splat = np.clip((dust - (0.50 + trail * 0.16)) * 3.4, 0, 1)
    streak = _line((h, w), seed + 81, -0.65, 155.0, 0.017, 0.030)
    base = np.stack([0.18 + dust * 0.17, 0.18 + dust * 0.15, 0.17 + dust * 0.12], axis=-1)
    mud = np.stack([0.36 + dust * 0.12, 0.27 + dust * 0.09, 0.15 + dust * 0.05], axis=-1)
    color = base * (1 - splat[:, :, None] * 0.74) + mud * splat[:, :, None] * 0.74
    color -= streak[:, :, None] * [0.045, 0.035, 0.025]
    return _blend(paint, mask, pm, color, 0.95)


def spec_rally_mud(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    dust = _noise((h, w), seed + 80, (1, 3, 8, 17, 41), (0.28, 0.26, 0.22, 0.15, 0.09))
    splat = np.clip((dust - 0.48) * 3.4, 0, 1)
    return _spec((h, w), seed, 12, 104, 76, splat, False)


def paint_stock_car_enamel(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    peel = _noise((h, w), seed + 90, (2, 5, 11, 27), (0.30, 0.30, 0.24, 0.16))
    pass_band = _line((h, w), seed + 91, 0.01, 92.0, 0.015, 0.008)
    ghost = np.clip((0.035 - np.abs(x - 0.52)) * 16.0, 0, 1)
    color = _hsv(0.565 + peel * 0.025, 0.58 + pass_band * 0.12, 0.30 + peel * 0.26 + pass_band * 0.06)
    color = color * (1 - ghost[:, :, None] * 0.28) + np.array([0.92, 0.91, 0.82]) * ghost[:, :, None] * 0.28
    return _blend(paint, mask, pm, color, 0.94)


def spec_stock_car_enamel(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 90, (2, 5, 11, 27), (0.30, 0.30, 0.24, 0.16)) + _line((h, w), seed + 91, 0.01, 92.0, 0.015, 0.008), 0, 1)
    return _spec((h, w), seed, 12, 16, 24, detail, True)


def paint_victory_lane(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    champagne = _noise((h, w), seed + 100, (3, 7, 17, 43), (0.29, 0.30, 0.25, 0.16))
    confetti = _sparkle((h, w), seed + 101, 0.026, 0.36)
    streamers = _line((h, w), seed + 102, -0.42, 78.0, 0.010, 0.030)
    color = _hsv(0.105 + champagne * 0.045 + x * 0.015, 0.42 + confetti * 0.12, 0.34 + champagne * 0.26 + confetti * 0.20)
    color[:, :, 0] += streamers * 0.08
    color[:, :, 1] += streamers * 0.06
    return _blend(paint, mask, pm, color, 0.94)


def spec_victory_lane(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    detail = np.clip(_noise((h, w), seed + 100, (3, 7, 17, 43), (0.29, 0.30, 0.25, 0.16)) + _sparkle((h, w), seed + 101, 0.026, 0.36), 0, 1)
    return _spec((h, w), seed, 126, 14, 26, detail, True)


OWNER_REVIEW_RACING_HERITAGE_OVERRIDES = {
    "asphalt_grind": (paint_asphalt_grind, spec_asphalt_grind),
    "barn_find": (paint_barn_find, spec_barn_find),
    "bullseye_chrome": (paint_bullseye_chrome, spec_bullseye_chrome),
    "checkered_chrome": (paint_checkered_chrome, spec_checkered_chrome),
    "drag_strip_gloss": (paint_drag_strip_gloss, spec_drag_strip_gloss),
    "endurance_ceramic": (paint_endurance_ceramic, spec_endurance_ceramic),
    "pace_car_pearl": (paint_pace_car_pearl, spec_pace_car_pearl),
    "race_day_gloss": (paint_race_day_gloss, spec_race_day_gloss),
    "rally_mud": (paint_rally_mud, spec_rally_mud),
    "stock_car_enamel": (paint_stock_car_enamel, spec_stock_car_enamel),
    "victory_lane": (paint_victory_lane, spec_victory_lane),
}
