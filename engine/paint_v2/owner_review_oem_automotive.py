"""Owner-review OEM Automotive base renderers for SPB-30.

OEM paints should read like believable vehicle finishes, not generic noisy tiles.
These renderers use paint-shop cues: orange peel, pearl mica, spray passes,
fleet/service color standards, clearcoat depth, and aged taxi chalking.
"""

from __future__ import annotations

from collections import OrderedDict

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from engine.core import hsv_to_rgb_vec, multi_scale_noise


_NOISE_CACHE: dict[tuple[tuple[int, int], int, tuple[float, ...], tuple[float, ...]], np.ndarray] = {}
_GRID_CACHE = OrderedDict()
_LINE_CACHE = OrderedDict()
_OEM_CACHE_MAX = 32


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
    key = (int(h), int(w))
    cached = _GRID_CACHE.get(key)
    if cached is not None:
        _GRID_CACHE.move_to_end(key)
        return cached
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    out = (yy / max(h - 1, 1), xx / max(w - 1, 1))
    _GRID_CACHE[key] = out
    _GRID_CACHE.move_to_end(key)
    while len(_GRID_CACHE) > 4:
        _GRID_CACHE.popitem(last=False)
    return out


def _norm(v):
    v = np.asarray(v, dtype=np.float32)
    lo = float(v.min())
    hi = float(v.max())
    if hi - lo < 1e-6:
        return np.zeros_like(v, dtype=np.float32)
    return ((v - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, seed, scales=(2, 6, 17, 43), weights=(0.28, 0.28, 0.25, 0.19)):
    h, w = shape
    key = ((int(h), int(w)), int(seed), tuple(float(v) for v in scales), tuple(float(v) for v in weights))
    cached = _NOISE_CACHE.get(key)
    if cached is not None:
        return cached
    out = _norm(multi_scale_noise(shape, list(scales), list(weights), seed))
    if len(_NOISE_CACHE) > 96:
        _NOISE_CACHE.clear()
    # SPB paint-finish perf loop tick 2026-05-31 09:53; owner: "Speed is king in this app."
    # Exact normalized-noise reuse only: fire_engine 5336.3 -> 4616.4 ms; paint/spec std drift 0.
    _NOISE_CACHE[key] = out
    return out


def _blend(paint, mask, pm, color, strength=0.93):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask, 0, 1)[:, :, None] * np.clip(pm * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - a) + np.clip(color, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _orange_peel(shape, seed, amount=1.0):
    n1 = _noise(shape, seed + 11, (4, 9, 21, 53), (0.18, 0.25, 0.32, 0.25))
    n2 = _noise(shape, seed + 12, (1, 2, 4), (0.48, 0.32, 0.20))
    pits = gaussian_filter((n1 > 0.72).astype(np.float32), sigma=max(0.45, shape[0] / 1800.0))
    return np.clip((n1 - 0.5) * 0.030 * amount + (n2 - 0.5) * 0.014 * amount + pits * 0.020 * amount, -0.08, 0.08)


def _spray_pass(shape, seed, horizontal=True):
    y, x = _grid(shape)
    axis = y if horizontal else x
    spacing = 17.0 + (seed % 7)
    phase = np.sin((axis * spacing + _noise(shape, seed + 21) * 0.05) * np.pi * 2.0)
    pass_band = phase * 0.018 + np.sin((axis * spacing * 0.5) * np.pi * 2.0) * 0.010
    atom = _noise(shape, seed + 22, (1, 3, 8), (0.44, 0.34, 0.22)) - 0.5
    return (pass_band + atom * 0.025).astype(np.float32)


def _mica(shape, seed, density=0.018, size=0.7):
    raw = _noise(shape, seed + 31, (1, 2, 5), (0.48, 0.34, 0.18))
    flecks = np.clip((raw - (1.0 - density)) / max(density, 1e-4), 0, 1)
    if size > 0:
        flecks = gaussian_filter(flecks, sigma=size)
    orient = _noise(shape, seed + 32, (3, 7, 19), (0.28, 0.36, 0.36))
    return np.clip(flecks * (0.55 + orient * 0.65), 0, 1).astype(np.float32)


def _fine_shop_texture(shape, seed, strength=1.0):
    y, x = _grid(shape)
    atom = _noise(shape, seed + 201, (1, 2, 4, 9), (0.40, 0.30, 0.20, 0.10)) - 0.5
    buff = np.sin((x * (95.0 + seed % 11) + y * (17.0 + seed % 5)) * np.pi * 2.0)
    wipe = np.sin((x * (18.0 + seed % 7) - y * (41.0 + seed % 13)) * np.pi * 2.0)
    scratches = np.clip((buff * 0.55 + wipe * 0.45) - 0.88, 0, 1)
    return (atom * 0.040 + scratches * 0.060) * strength


def _thin_reflection_lines(shape, seed, axis="x", density=34.0, width=0.010):
    y, x = _grid(shape)
    coord = x if axis == "x" else y
    warp = (_noise(shape, seed + 211, (5, 17, 53), (0.25, 0.35, 0.40)) - 0.5) * 0.04
    line = np.abs(np.sin((coord * density + warp) * np.pi))
    return np.clip((width - line) / max(width, 1e-4), 0, 1).astype(np.float32)


def _hash01(shape, seed):
    y, x = _grid(shape)
    raw = np.sin((x * 127.1 + y * 311.7 + float(seed) * 0.173) * 43758.5453)
    return (raw - np.floor(raw)).astype(np.float32)


def _simple_lines(shape, seed, axis="x", density=36.0, width=0.012, warp=0.02):
    key = (
        int(shape[0]), int(shape[1]), int(seed), str(axis),
        round(float(density), 6), round(float(width), 6), round(float(warp), 6),
    )
    cached = _LINE_CACHE.get(key)
    if cached is not None:
        _LINE_CACHE.move_to_end(key)
        return cached
    y, x = _grid(shape)
    coord = x if axis == "x" else y
    bend = np.sin((x * (7.0 + seed % 5) + y * (11.0 + seed % 7)) * np.pi * 2.0) * warp
    line = np.abs(np.sin((coord * density + bend + seed * 0.0017) * np.pi))
    out = np.clip((width - line) / max(width, 1e-4), 0, 1).astype(np.float32)
    # SPB paint-finish perf loop tick 2026-05-31 07:23; owner: "Speed is king in this app."
    # Exact OEM grid/line reuse avoids rebuilding dealer-pearl 2048² normalized grids and pearl lanes;
    # dealer_pearl 5905.7 -> 4485.0 ms, paint/spec std drift 0.
    _LINE_CACHE[key] = out
    _LINE_CACHE.move_to_end(key)
    while len(_LINE_CACHE) > _OEM_CACHE_MAX:
        _LINE_CACHE.popitem(last=False)
    return out


def _hsv(h, s, v):
    h, s, v = np.broadcast_arrays(h, s, v)
    h = np.mod(h, 1.0).astype(np.float32)
    s = np.clip(s, 0, 1).astype(np.float32)
    v = np.clip(v, 0, 1).astype(np.float32)
    r, g, b = hsv_to_rgb_vec(h, s, v)
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def _paint_solid(shape, color, seed, peel=1.0, pass_axis=True, pearl=None):
    h, w = shape
    y, x = _grid(shape)
    peel_field = _orange_peel(shape, seed, peel)
    pass_field = _spray_pass(shape, seed + 60, pass_axis)
    clear_wave = _noise(shape, seed + 61, (17, 37, 89), (0.25, 0.36, 0.39)) - 0.5
    atomized = _noise(shape, seed + 62, (1, 2, 5), (0.46, 0.34, 0.20)) - 0.5
    color = np.asarray(color, dtype=np.float32)
    out = color[None, None, :] * (
        1.0
        + peel_field[:, :, None]
        + pass_field[:, :, None]
        + clear_wave[:, :, None] * 0.018
        + atomized[:, :, None] * 0.040
    )
    if pearl is not None:
        mica = _mica(shape, seed + 70, pearl[0], pearl[1])
        pearl_rgb = _hsv(pearl[2] + x * pearl[3] + y * pearl[4], pearl[5], pearl[6])
        out = out + pearl_rgb * mica[:, :, None] * pearl[7]
    return np.clip(out, 0, 1).astype(np.float32)


def _spec_from_paint(shape, seed, kind="gloss", metallic=0.0, pearl=0.0):
    peel = _orange_peel(shape, seed, 1.0)
    pass_field = _spray_pass(shape, seed + 60)
    mica = _mica(shape, seed + 70, 0.025, 0.7) if pearl or metallic else np.zeros(shape, dtype=np.float32)
    if kind == "flat":
        M = 2 + _noise(shape, seed + 80, (1, 3, 9, 27), (0.35, 0.30, 0.22, 0.13)) * 10 + mica * 8
        R = 60 + _noise(shape, seed + 81) * 44 - peel * 50
        CC = 16 + _noise(shape, seed + 82) * 8
    elif kind == "clear":
        M = 18 + metallic * 80 + mica * (70 + pearl * 50)
        R = 15 + np.clip(peel * 160 + pass_field * 60, -8, 28)
        CC = 34 + _noise(shape, seed + 83) * 18 + pearl * 18
    else:
        M = 4 + metallic * 82 + mica * (52 + pearl * 72)
        R = 20 + np.clip(peel * 170 + pass_field * 64, -10, 34)
        CC = 18 + _noise(shape, seed + 84) * 12 + pearl * 14
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32)


def paint_ambulance_white(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    base = _paint_solid((h, w), [0.94, 0.935, 0.90], seed, 0.8, True)
    prism = _mica((h, w), seed + 101, 0.030, 0.55)
    strip = np.clip((0.018 - np.abs(np.sin((x * 28.0 + y * 2.0) * np.pi))) * 18.0, 0, 1)
    base = np.clip(base + prism[:, :, None] * [0.10, 0.12, 0.16] + strip[:, :, None] * [0.06, 0.05, 0.05], 0, 1)
    return _blend(paint, mask, pm, base, 0.94)


def spec_ambulance_white(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    bead = _mica((h, w), seed + 101, 0.035, 0.55)
    M = np.clip(3 + bead * 24 * sm, 0, 255)
    R = np.clip(28 - bead * 9 + _noise((h, w), seed + 102) * 10, 15, 255)
    CC = np.clip(18 + bead * 10, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_dealer_pearl(paint, shape, mask, seed, pm, bb):
    out_shape = _shape2(shape)
    h, w = _work_shape(out_shape)
    y, x = _grid((h, w))
    grain = _hash01((h, w), seed + 113)
    micro = np.sin((x * 211.0 + y * 137.0 + seed) * np.pi * 2.0) * 0.5 + 0.5
    pearl_lane = _simple_lines((h, w), seed + 115, "y", 58.0, 0.018, 0.018)
    side_flop = _simple_lines((h, w), seed + 117, "x", 27.0, 0.026, 0.030)
    lot_shadow = _simple_lines((h, w), seed + 118, "x", 13.0, 0.020, 0.016)
    pearl_pop = np.clip((grain - 0.925) / 0.075, 0, 1) * (0.55 + micro * 0.45)
    base = np.full((h, w, 3), [0.295, 0.300, 0.285], dtype=np.float32)
    flop = _hsv(0.56 + x * 0.075 - y * 0.055 + micro * 0.015, 0.34, 0.24)
    pearl_tint = _hsv(0.08 + x * 0.18 - y * 0.12 + grain * 0.025, 0.54, 0.68)
    warm = _hsv(0.095 + x * 0.040, 0.36, 0.42)
    cool = _hsv(0.58 - y * 0.055, 0.34, 0.38)
    shop = (micro - 0.5) * 0.026 + np.clip((grain - 0.985) / 0.015, 0, 1) * 0.08
    base = np.clip(
        base
        + flop * (grain[:, :, None] - 0.5) * 0.18
        + micro[:, :, None] * [0.022, 0.026, 0.034]
        + pearl_lane[:, :, None] * (warm * 0.14 + cool * 0.08)
        + side_flop[:, :, None] * (cool * 0.24 - warm * 0.045)
        + lot_shadow[:, :, None] * [-0.070, -0.060, -0.048]
        + pearl_pop[:, :, None] * pearl_tint * 0.55
        + shop[:, :, None] * [0.018, 0.020, 0.024],
        0,
        1,
    )
    if (h, w) != out_shape:
        # SPB paint-finish perf loop tick 2026-05-31 14:15; owner: "No base can be more than 4 seconds."
        # Dealer pearl keeps its lane/flop language, but solves expensive HSV/lane structure at CX/OEM work scale.
        # Measured dealer_pearl 4874.1 ms -> 1809.4 ms at 2048; M7 not rerun in perf-only heartbeat.
        base = _resize_field(base, out_shape)
        micro = (_hash01(out_shape, seed + 1193) - 0.5)[:, :, None]
        base = np.clip(base + micro * np.array([0.014, 0.017, 0.022], dtype=np.float32), 0, 1)
    return _blend(paint, mask, pm, base, 0.93)


def spec_dealer_pearl(shape, seed, sm, base_m, base_r):
    out_shape = _shape2(shape)
    h, w = _work_shape(out_shape)
    grain = _hash01((h, w), seed + 119)
    lane = _simple_lines((h, w), seed + 115, "y", 58.0, 0.018, 0.018)
    fleck = np.clip((grain - 0.925) / 0.075, 0, 1)
    M = 18 + fleck * 112 * sm + lane * 36
    R = 22 - lane * 7 - fleck * 5
    CC = 26 + lane * 26 + fleck * 20
    if (h, w) != out_shape:
        M = _resize_field(M, out_shape)
        R = _resize_field(R, out_shape)
        CC = _resize_field(CC, out_shape)
        micro = _hash01(out_shape, seed + 1197) - 0.5
        M = M + micro * 8.0 * sm
        R = R - micro * 4.0 * sm
        CC = CC + micro * 5.0 * sm
    return M.astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32)


def paint_factory_basecoat(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    bell = _spray_pass((h, w), seed + 121, True)
    silver = 0.38 + bell * 0.9 + (_noise((h, w), seed + 122) - 0.5) * 0.08
    tone = _hsv(0.57 + x * 0.025, 0.08, silver)
    robot_overlap = np.clip((0.045 - np.abs(np.sin((y * 11.0 + x * 0.4) * np.pi))) * 7.0, 0, 1)
    color = np.clip(tone + robot_overlap[:, :, None] * [0.035, 0.035, 0.030], 0, 1)
    return _blend(paint, mask, pm, color, 0.92)


def spec_factory_basecoat(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    band = np.abs(_spray_pass((h, w), seed + 121, True))
    flake = _mica((h, w), seed + 122, 0.050, 0.55)
    M = np.clip(82 + band * 80 + flake * 85 * sm, 0, 255)
    R = np.clip(34 - band * 12 - flake * 10, 15, 255)
    CC = np.clip(18 + band * 10, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_fire_engine(paint, shape, mask, seed, pm, bb):
    out_shape = _shape2(shape)
    h, w = _work_shape(out_shape)
    y, x = _grid((h, w))
    grain = _hash01((h, w), seed + 132)
    color = np.full((h, w, 3), [0.91, 0.020, 0.014], dtype=np.float32)
    clear_lines = _simple_lines((h, w), seed + 131, "y", 36.0, 0.020, 0.010)
    booth = _simple_lines((h, w), seed + 132, "x", 48.0, 0.014, 0.015)
    orange_edge = _simple_lines((h, w), seed + 133, "y", 70.0, 0.010, 0.010)
    panel_shadow = _simple_lines((h, w), seed + 135, "x", 17.0, 0.018, 0.012)
    shop = (np.sin((x * 157.0 - y * 41.0 + seed) * np.pi * 2.0) * 0.5 + 0.5 - 0.5) * 0.040
    ember = np.clip((grain - 0.982) / 0.018, 0, 1)
    color = np.clip(
        color
        + clear_lines[:, :, None] * [0.032, 0.006, 0.002]
        + booth[:, :, None] * [0.080, 0.018, 0.010]
        + orange_edge[:, :, None] * [0.050, 0.026, 0.004]
        + panel_shadow[:, :, None] * [-0.160, -0.018, -0.010]
        + shop[:, :, None] * [0.040, 0.006, 0.004]
        + ember[:, :, None] * [0.10, 0.035, 0.010],
        0,
        1,
    )
    if (h, w) != out_shape:
        # SPB paint-finish perf loop tick 2026-05-31 14:15; owner: "No base can be more than 4 seconds."
        # Fire Engine keeps clearcoat lanes/booth lines/ember pins, but renders their structure at work scale.
        # Measured fire_engine 5176.5 ms -> 2264.1 ms at 2048; M7 not rerun in perf-only heartbeat.
        color = _resize_field(color, out_shape)
        micro = (_hash01(out_shape, seed + 1329) - 0.5)[:, :, None]
        color = np.clip(color + micro * np.array([0.022, 0.004, 0.003], dtype=np.float32), 0, 1)
    return _blend(paint, mask, pm, color, 0.95)


def spec_fire_engine(shape, seed, sm, base_m, base_r):
    out_shape = _shape2(shape)
    work = _work_shape(out_shape)
    M, R, CC = _spec_from_paint(work, seed, "gloss", metallic=0.0, pearl=0.10)
    if work != out_shape:
        M = _resize_field(M, out_shape)
        R = _resize_field(R, out_shape)
        CC = _resize_field(CC, out_shape)
        micro = _hash01(out_shape, seed + 1331) - 0.5
        M = M + micro * 7.0 * sm
        R = R - micro * 4.0 * sm
        CC = CC + micro * 5.0 * sm
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32)


def paint_fleet_white(paint, shape, mask, seed, pm, bb):
    color = _paint_solid(_shape2(shape), [0.85, 0.85, 0.815], seed, 0.65, False)
    chalk = _noise(_shape2(shape), seed + 141, (8, 21, 55), (0.30, 0.34, 0.36))
    color = np.clip(color + (chalk[:, :, None] - 0.5) * 0.025, 0, 1)
    return _blend(paint, mask, pm, color, 0.92)


def spec_fleet_white(shape, seed, sm, base_m, base_r):
    return _spec_from_paint(_shape2(shape), seed, "flat", metallic=0.0, pearl=0.0)


def paint_police_black(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    peel = _orange_peel((h, w), seed, 0.8)
    carbon = _noise((h, w), seed + 151, (3, 8, 21, 55), (0.22, 0.28, 0.28, 0.22))
    clear = np.clip((0.035 - np.abs(np.sin((x * 18.0 + y * 4.0) * np.pi))) * 4.0, 0, 1)
    micro = _noise((h, w), seed + 152, (1, 2, 5), (0.44, 0.34, 0.22)) - 0.5
    blue_roof = _thin_reflection_lines((h, w), seed + 153, "x", 31.0, 0.018)
    white_bar = _thin_reflection_lines((h, w), seed + 155, "y", 47.0, 0.012)
    shop = _fine_shop_texture((h, w), seed + 154, 0.8)
    base = 0.022 + carbon * 0.052 + peel * 0.48 + clear * 0.040 + micro * 0.020 + shop * 0.32
    color = np.stack([base * 0.88, base * 0.96, base * 1.16], axis=-1)
    color = np.clip(
        color
        + blue_roof[:, :, None] * [0.030, 0.060, 0.160]
        + white_bar[:, :, None] * [0.150, 0.160, 0.185],
        0,
        1,
    )
    return _blend(paint, mask, pm, color, 0.95)


def spec_police_black(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    clear = _noise((h, w), seed + 151)
    M = np.clip(4 + clear * 10 * sm, 0, 255)
    R = np.clip(24 + clear * 22, 15, 255)
    CC = np.clip(18 + clear * 8, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_school_bus(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    grain = _hash01((h, w), seed + 162)
    color = np.full((h, w, 3), [0.96, 0.66, 0.040], dtype=np.float32)
    uv = np.sin((x * 9.0 + y * 23.0 + seed * 0.01) * np.pi * 2.0) * 0.5 + 0.5
    enamel = _simple_lines((h, w), seed + 163, "y", 44.0, 0.016, 0.014)
    warm_lane = _simple_lines((h, w), seed + 164, "x", 45.0, 0.013, 0.014)
    body_shadow = _simple_lines((h, w), seed + 165, "y", 22.0, 0.018, 0.014)
    speck = np.clip((grain - 0.975) / 0.025, 0, 1)
    color = np.clip(
        color
        + (uv[:, :, None] - 0.5) * [0.055, 0.038, 0.006]
        + enamel[:, :, None] * [0.028, 0.016, -0.002]
        + warm_lane[:, :, None] * [0.035, 0.018, 0.000]
        + body_shadow[:, :, None] * [-0.145, -0.095, -0.010],
        0,
        1,
    )
    color = np.clip(
        color + speck[:, :, None] * [0.055, 0.040, 0.010],
        0,
        1,
    )
    return _blend(paint, mask, pm, color, 0.95)


def spec_school_bus(shape, seed, sm, base_m, base_r):
    return _spec_from_paint(_shape2(shape), seed, "gloss", metallic=0.0, pearl=0.05)


def paint_showroom_clear(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    grain = _hash01((h, w), seed + 181)
    deep = np.full((h, w, 3), [0.115, 0.125, 0.140], dtype=np.float32)
    horizon = np.clip((0.055 - np.abs(np.sin((y * 4.0 + x * 0.7) * np.pi))) * 5.5, 0, 1)
    booth_panels = np.clip((0.026 - np.abs(np.sin((x * 13.0 - y * 1.2) * np.pi))) * 7.0, 0, 1)
    micro = (grain - 0.5) * 0.030 + np.clip((grain - 0.988) / 0.012, 0, 1) * 0.055
    glint = np.clip((grain - 0.985) / 0.015, 0, 1)
    white_tube = _simple_lines((h, w), seed + 175, "x", 39.0, 0.012, 0.018)
    blue_glass = _simple_lines((h, w), seed + 176, "y", 52.0, 0.010, 0.018)
    color = np.clip(
        deep
        + horizon[:, :, None] * [0.16, 0.16, 0.18]
        + booth_panels[:, :, None] * [0.05, 0.055, 0.065]
        + micro[:, :, None] * [0.014, 0.014, 0.016]
        + glint[:, :, None] * [0.18, 0.19, 0.22]
        + white_tube[:, :, None] * [0.18, 0.18, 0.19]
        + blue_glass[:, :, None] * [0.020, 0.040, 0.090],
        0,
        1,
    )
    return _blend(paint, mask, pm, color, 0.92)


def spec_showroom_clear(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    gloss = _mica((h, w), seed + 171, 0.012, 1.0)
    polish = _noise((h, w), seed + 173, (3, 9, 29, 71), (0.20, 0.30, 0.28, 0.22))
    M = np.clip(18 + polish * 12 + gloss * 45 + base_m * 0.25, 0, 255)
    R = np.clip(20 + _orange_peel((h, w), seed, 0.5) * 70 + polish * 10 - gloss * 7, 15, 255)
    CC = np.clip(38 + _noise((h, w), seed + 172) * 20, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_smoked(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    smoke = _noise((h, w), seed + 181, (9, 23, 61, 131), (0.22, 0.30, 0.30, 0.18))
    micro = _noise((h, w), seed + 182, (1, 3, 7), (0.42, 0.34, 0.24)) - 0.5
    film = 0.050 + smoke * 0.080 + y * 0.025
    color = np.stack([film * 0.83, film * 0.90, film], axis=-1)
    wipe = _thin_reflection_lines((h, w), seed + 183, "x", 68.0, 0.010)
    grit = _fine_shop_texture((h, w), seed + 184, 0.95)
    color = np.clip(
        color
        + micro[:, :, None] * [0.024, 0.028, 0.036]
        + wipe[:, :, None] * [0.018, 0.026, 0.045]
        + grit[:, :, None] * [0.016, 0.020, 0.030],
        0,
        1,
    )
    return _blend(paint, mask, pm, color, 0.90)


def spec_smoked(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    smoke = _noise((h, w), seed + 181, (9, 23, 61, 131), (0.22, 0.30, 0.30, 0.18))
    M = np.clip(12 + smoke * 24 * sm, 0, 255)
    R = np.clip(28 + smoke * 35, 15, 255)
    CC = np.clip(34 + smoke * 28, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_taxi_yellow(paint, shape, mask, seed, pm, bb):
    h, w = _shape2(shape)
    y, x = _grid((h, w))
    grain = _hash01((h, w), seed + 202)
    base = np.full((h, w, 3), [0.90, 0.66, 0.055], dtype=np.float32)
    fade = np.sin((x * 12.0 - y * 21.0 + seed * 0.02) * np.pi * 2.0) * 0.5 + 0.5
    grit = grain - 0.5
    checker_shadow = np.clip((0.020 - np.abs(np.sin((x * 24.0 + y * 2.0) * np.pi))) * 10.0, 0, 1) * (fade > 0.66)
    warm_wear = (np.sin((x * 173.0 + y * 47.0 + seed) * np.pi * 2.0) * 0.5 + 0.5 - 0.5) * 0.070
    amber_line = _simple_lines((h, w), seed + 194, "y", 44.0, 0.015, 0.018)
    door_shadow = _simple_lines((h, w), seed + 195, "x", 20.0, 0.022, 0.018)
    sun_bleach = np.clip((fade - 0.54) * 3.6, 0, 1)
    chips = np.clip((grain - 0.980) / 0.020, 0, 1)
    color = np.clip(
        base
        + sun_bleach[:, :, None] * [0.115, 0.055, -0.012]
        + fade[:, :, None] * [0.055, -0.022, -0.014]
        + grit[:, :, None] * [0.045, 0.028, 0.000]
        + checker_shadow[:, :, None] * [-0.12, -0.10, -0.025]
        + warm_wear[:, :, None] * [0.070, 0.044, 0.006]
        + amber_line[:, :, None] * [0.055, 0.030, 0.000]
        + door_shadow[:, :, None] * [-0.150, -0.090, -0.012],
        0,
        1,
    )
    color = np.clip(color - chips[:, :, None] * [0.12, 0.09, 0.035], 0, 1)
    return _blend(paint, mask, pm, color, 0.94)


def spec_taxi_yellow(shape, seed, sm, base_m, base_r):
    h, w = _shape2(shape)
    fade = _noise((h, w), seed + 191, (13, 37, 83), (0.28, 0.36, 0.36))
    M = np.clip(4 + fade * 8 * sm, 0, 255)
    R = np.clip(30 + fade * 48, 15, 255)
    CC = np.clip(18 + (1 - fade) * 10, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


OWNER_REVIEW_OEM_AUTOMOTIVE_OVERRIDES = {
    "ambulance_white": (paint_ambulance_white, spec_ambulance_white),
    "dealer_pearl": (paint_dealer_pearl, spec_dealer_pearl),
    "factory_basecoat": (paint_factory_basecoat, spec_factory_basecoat),
    "fire_engine": (paint_fire_engine, spec_fire_engine),
    "fleet_white": (paint_fleet_white, spec_fleet_white),
    "police_black": (paint_police_black, spec_police_black),
    "school_bus": (paint_school_bus, spec_school_bus),
    "showroom_clear": (paint_showroom_clear, spec_showroom_clear),
    "smoked": (paint_smoked, spec_smoked),
    "taxi_yellow": (paint_taxi_yellow, spec_taxi_yellow),
}
