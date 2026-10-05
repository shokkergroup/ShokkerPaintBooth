# -*- coding: utf-8 -*-
"""
engine/paint_v2/metallic_standard_2026.py — ★ METALLIC STANDARD (rebuild 2026-06-14)

Owner: the old 22 were "all just versions of metallic." This replaces them with 22
WILDLY different metallic bangers — liquid metals, heat-tinted copper, anodized
titanium oil-slick, holographic rainbow chrome-flake, hammered gold-leaf, brushed
graphite, damascus steel, black w/ rainbow micro-flake, + 7 vivid candy-over-flake
colors. Through-line = real metal + FINE flake (full-res sparkle); diversity = color +
metal type (liquid/brushed/hammered/anodize/damascus/flake).

Contracts: paint_x(paint,shape,mask,seed,pm,bb)->HxWx3 ; spec_x(shape,seed,sm,bm,br)->(M,R,CC).
High M (metal); M rides flake, R rides independent grain (decorrelated); R floor 15,
M<=255, CC=16 wet clear. FINE detail (full-res flake/brush/hammer). <3s @2048.
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array
from engine.color_science import candy_absorb, interference_palette

_MS_CACHE = {}


def _cache(key, fn):
    v = _MS_CACHE.get(key)
    if v is None:
        if len(_MS_CACHE) > 160:
            _MS_CACHE.clear()
        v = fn()
        _MS_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, scales, weights, seed, cap=0):
    h, w = shape[:2]
    key = ("n", h, w, tuple(scales), tuple(weights), int(seed), int(cap))

    def build():
        if cap and min(h, w) > cap:
            sh = max(64, int(round(h * cap / max(h, w))))
            sw = max(64, int(round(w * cap / max(h, w))))
            f = multi_scale_noise((sh, sw), scales, weights, seed)
            return _resize_array(np.asarray(f, np.float32), h, w)
        return np.asarray(multi_scale_noise((h, w), scales, weights, seed), np.float32)

    return _cache(key, build)


def _grain(shape, seed):
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x4AD7) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        return ((n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) * 0.333).astype(np.float32)

    return _cache(key, build)


def _flake(shape, seed, density, lo=0.35):
    h, w = shape[:2]
    key = ("fl", h, w, int(seed), float(density), float(lo))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x9E37) & 0xFFFFFFFF)
        n = min(int(h * w * float(density)), 170000)
        out = np.zeros((h, w), np.float32)
        if n > 0:
            yy = rng.integers(0, h, n); xx = rng.integers(0, w, n)
            out[yy, xx] = rng.uniform(lo, 1.0, n).astype(np.float32)
            out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.45, np.roll(out, 1, 1) * 0.45])
        return out.astype(np.float32)

    return _cache(key, build)


def _rot(shape, deg):
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    a = np.deg2rad(deg); ca, sa = np.cos(a), np.sin(a)
    return (x * ca + y * sa).astype(np.float32), (-x * sa + y * ca).astype(np.float32)


# ---------- metal core: bright metal body + FINE flake glints ----------

def _metal(paint, shape, mask, seed, pm, bb, base_rgb, tint=None, depth=0.5,
           flake_density=0.022, flake_rgb=None, sparkle=0.8, grain_amt=0.14):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    g = _grain((h, w), seed + 3)
    body = np.empty((h, w, 3), np.float32); body[:] = np.asarray(base_rgb, np.float32)
    body = body * (1.0 + grain_amt * (g[:, :, None] - 0.5) * 2.0)
    if tint is not None:
        d = np.maximum(depth * (1.0 + 0.4 * (g - 0.5)), 0.0).astype(np.float32)
        body = candy_absorb(np.clip(body, 0, 1), np.asarray(tint, np.float32), d, 1.0)
    fl = _flake((h, w), seed, flake_density)
    if flake_rgb is None:
        flake_rgb = np.clip(np.sqrt(np.clip(np.asarray(base_rgb, np.float32), 0, 1)) * 1.1, 0.1, 1)
    out = np.clip(body + fl[:, :, None] * float(sparkle) * np.asarray(flake_rgb, np.float32), 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return out * m + paint * (1 - m)


def _metal_spec(shape, seed, sm, base_m, base_r, m_body=200.0, m_flake=252.0,
                r_base=24.0, r_amp=16.0, flake_density=0.022, cc=16.0, aniso=None):
    h, w = shape[:2]
    fl = np.clip(_flake((h, w), seed, flake_density), 0, 1)
    g = _grain((h, w), seed + 3)
    M = np.clip(m_body + (m_flake - m_body) * fl * sm, 0, 255)
    R = r_base + r_amp * (g - 0.5) * 2.0 * sm
    if aniso is not None:                              # brushed: lower R along grain dir
        u, _v = _rot((h, w), aniso)
        R = R - 18.0 * (0.5 + 0.5 * np.cos(u * 1.2)) * sm
    R = np.clip(R, 15, 255)
    return (M.astype(np.float32), R.astype(np.float32), np.full((h, w), float(cc), np.float32))


def _brush(shape, seed, deg, freq=1.2):
    u, _v = _rot(shape, deg)
    n = _norm01(_noise(shape, [1, 2, 3], [0.5, 0.3, 0.2], seed, cap=1024))
    return (0.5 + 0.5 * np.sin(u * freq + n * 8.0)).astype(np.float32)


def _hammer(shape, seed, period):
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    jx = _noise((h, w), [period], [1.0], seed, cap=512) * period * 0.3
    jy = _noise((h, w), [period], [1.0], seed + 1, cap=512) * period * 0.3
    fx = ((x + jx) / period) % 1.0 - 0.5; fy = ((y + jy) / period) % 1.0 - 0.5
    d = np.sqrt(fx * fx + fy * fy)
    return np.clip(1.0 - d * 2.3, 0, 1).astype(np.float32)


# =====================================================================
# THE 22 — wildly diverse metallic bangers
# =====================================================================
# ---- SILVERS / WHITE METALS ----
def paint_liquid_silver(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    flow = _norm01(np.sin(_noise((h, w), [10, 22], [0.6, 0.4], seed) * 6.0 + _noise((h, w), [20, 40], [0.5, 0.5], seed + 1) * 4.0))
    base = np.empty((h, w, 3), np.float32); base[:] = (0.72, 0.74, 0.78)
    col = np.clip(base * (0.7 + 0.55 * flow[:, :, None]), 0, 1)
    fl = _flake((h, w), seed, 0.014, lo=0.5)
    col = np.clip(col + fl[:, :, None] * 0.6, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_liquid_silver(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=235, m_flake=255, r_base=14, r_amp=8, flake_density=0.014)

def paint_platinum_mirror(paint, shape, mask, seed, pm, bb):
    return _metal(paint, shape, mask, seed, pm, bb, (0.80, 0.80, 0.83), flake_density=0.018, sparkle=0.55, grain_amt=0.06)
def spec_platinum_mirror(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=245, m_flake=255, r_base=12, r_amp=6, flake_density=0.018)

def paint_silver_frost(paint, shape, mask, seed, pm, bb):
    return _metal(paint, shape, mask, seed, pm, bb, (0.70, 0.74, 0.80), flake_density=0.030, sparkle=0.85,
                  flake_rgb=(0.85, 0.92, 1.0))
def spec_silver_frost(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=210, m_flake=252, r_base=34, r_amp=18, flake_density=0.030)

# ---- GOLDS ----
def paint_molten_gold(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    flow = _norm01(np.sin(_noise((h, w), [9, 20], [0.6, 0.4], seed) * 6.5))
    base = np.empty((h, w, 3), np.float32); base[:] = (0.92, 0.70, 0.20)
    col = np.clip(base * (0.6 + 0.6 * flow[:, :, None]), 0, 1)
    fl = _flake((h, w), seed, 0.016, lo=0.5)
    col = np.clip(col + fl[:, :, None] * np.array([1.0, 0.92, 0.6], np.float32) * 0.6, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_molten_gold(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=235, m_flake=255, r_base=16, r_amp=9, flake_density=0.016)

def paint_gold_leaf_hammered(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    dome = _hammer((h, w), seed, 20)
    base = np.empty((h, w, 3), np.float32); base[:] = (0.86, 0.66, 0.22)
    col = np.clip(base * (0.72 + 0.5 * dome[:, :, None]), 0, 1)
    fl = _flake((h, w), seed + 4, 0.012, lo=0.5)
    col = np.clip(col + fl[:, :, None] * np.array([1.0, 0.9, 0.6], np.float32) * 0.5, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_gold_leaf_hammered(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    dome = _hammer((h, w), seed, 20)
    g = _grain((h, w), seed + 3)
    M = np.clip(210 + 40 * dome * sm, 0, 255)
    R = np.clip(28 + 22 * (g - 0.5) * 2.0 * sm - 10 * dome * sm, 15, 255)
    return (M.astype(np.float32), R.astype(np.float32), np.full((h, w), 16.0, np.float32))

def paint_champagne_diamond(paint, shape, mask, seed, pm, bb):
    return _metal(paint, shape, mask, seed, pm, bb, (0.84, 0.78, 0.62), flake_density=0.034, sparkle=0.9,
                  flake_rgb=(1.0, 0.98, 0.9))
def spec_champagne_diamond(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=255, r_base=30, r_amp=16, flake_density=0.034)

# ---- COPPER / BRONZE / ROSE ----
def paint_copper_fire(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    heat = _norm01(_noise((h, w), [14, 30], [0.6, 0.4], seed))
    film = np.asarray(interference_palette(heat * 0.5 + 0.2, orders=2.2, quantize=0.5, brightness=1.0), np.float32)
    copper = np.array([0.80, 0.40, 0.18], np.float32)
    col = np.clip(copper[None, None, :] * 0.6 + film * 0.4, 0, 1)
    fl = _flake((h, w), seed, 0.020, lo=0.45)
    col = np.clip(col + fl[:, :, None] * np.array([1.0, 0.7, 0.45], np.float32) * 0.55, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_copper_fire(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=200, m_flake=252, r_base=22, r_amp=14, flake_density=0.020)

def paint_bronze_age(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    mot = _norm01(_noise((h, w), [8, 18, 38], [0.4, 0.35, 0.25], seed))
    base = np.array([0.52, 0.38, 0.20], np.float32)
    dark = np.array([0.26, 0.20, 0.12], np.float32)
    col = base[None, None, :] * (0.5 + 0.5 * mot[:, :, None]) + dark[None, None, :] * (1 - mot[:, :, None]) * 0.5
    fl = _flake((h, w), seed, 0.016, lo=0.4)
    col = np.clip(col + fl[:, :, None] * np.array([0.85, 0.65, 0.4], np.float32) * 0.4, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_bronze_age(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=170, m_flake=240, r_base=40, r_amp=22, flake_density=0.016)

def paint_rose_gold_flake(paint, shape, mask, seed, pm, bb):
    return _metal(paint, shape, mask, seed, pm, bb, (0.86, 0.62, 0.56), flake_density=0.026, sparkle=0.85,
                  flake_rgb=(1.0, 0.85, 0.82))
def spec_rose_gold_flake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=253, r_base=26, r_amp=15, flake_density=0.026)

# ---- DARK METALS ----
def paint_gunmetal_storm(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    storm = _norm01(_noise((h, w), [10, 22, 46], [0.4, 0.35, 0.25], seed))
    base = np.array([0.30, 0.32, 0.36], np.float32)
    col = base[None, None, :] * (0.55 + 0.55 * storm[:, :, None])
    fl = _flake((h, w), seed, 0.024, lo=0.45)
    col = np.clip(col + fl[:, :, None] * np.array([0.8, 0.85, 0.95], np.float32) * 0.55, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_gunmetal_storm(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=190, m_flake=250, r_base=34, r_amp=20, flake_density=0.024)

def paint_graphite_brushed(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    br = _brush((h, w), seed, 28.0, freq=1.4)
    base = np.array([0.26, 0.27, 0.30], np.float32)
    col = np.clip(base[None, None, :] * (0.7 + 0.6 * br[:, :, None]), 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_graphite_brushed(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=235, r_base=50, r_amp=18, flake_density=0.004, aniso=28.0)

def paint_black_diamond_flake(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32); base[:] = (0.07, 0.07, 0.09)
    fl = np.clip(_flake((h, w), seed, 0.03, lo=0.4), 0, 1)
    rainbow = np.asarray(interference_palette(_grain((h, w), seed + 8), orders=3.5, quantize=0.4), np.float32)
    col = np.clip(base + (fl[:, :, None]) * rainbow * 0.9, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_black_diamond_flake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=120, m_flake=255, r_base=28, r_amp=16, flake_density=0.03)

def paint_steel_damascus(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    u, v = _rot((h, w), 16.0)
    warp = _noise((h, w), [12, 26], [0.6, 0.4], seed) * 5.0
    band = 0.5 + 0.5 * np.sin(v * 0.10 + warp)
    light = np.array([0.62, 0.64, 0.68], np.float32); dark = np.array([0.20, 0.21, 0.24], np.float32)
    col = dark[None, None, :] + (light - dark)[None, None, :] * band[:, :, None]
    fl = _flake((h, w), seed + 4, 0.010, lo=0.4)
    col = np.clip(col + fl[:, :, None] * 0.4, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_steel_damascus(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    u, v = _rot((h, w), 16.0)
    warp = _noise((h, w), [12, 26], [0.6, 0.4], seed) * 5.0
    band = 0.5 + 0.5 * np.sin(v * 0.10 + warp)
    g = _grain((h, w), seed + 3)
    M = np.clip(180 + 60 * band * sm, 0, 255)
    R = np.clip(30 + 22 * (g - 0.5) * 2.0 * sm, 15, 255)
    return (M.astype(np.float32), R.astype(np.float32), np.full((h, w), 16.0, np.float32))

# ---- VIVID CANDY-OVER-FLAKE COLORS ----
def _colorflake(paint, shape, mask, seed, base_rgb, tint, flake_rgb, depth=0.7, fd=0.024):
    return _metal(paint, shape, mask, seed, 1.0, None, base_rgb, tint=tint, depth=depth,
                  flake_density=fd, flake_rgb=flake_rgb, sparkle=0.85, grain_amt=0.10)

def paint_emerald_metalflake(paint, shape, mask, seed, pm, bb):
    return _colorflake(paint, shape, mask, seed, (0.78, 0.82, 0.5), (0.05, 0.55, 0.2), (0.4, 1.0, 0.5))
def spec_emerald_metalflake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=200, m_flake=253, r_base=20, r_amp=14, flake_density=0.024)

def paint_sapphire_metalflake(paint, shape, mask, seed, pm, bb):
    return _colorflake(paint, shape, mask, seed, (0.55, 0.65, 0.9), (0.05, 0.15, 0.7), (0.4, 0.6, 1.0))
def spec_sapphire_metalflake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=253, r_base=20, r_amp=14, flake_density=0.024)

def paint_ruby_metalflake(paint, shape, mask, seed, pm, bb):
    return _colorflake(paint, shape, mask, seed, (0.9, 0.55, 0.55), (0.7, 0.04, 0.1), (1.0, 0.5, 0.5))
def spec_ruby_metalflake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=253, r_base=20, r_amp=14, flake_density=0.024)

def paint_violet_metalflake(paint, shape, mask, seed, pm, bb):
    return _colorflake(paint, shape, mask, seed, (0.74, 0.62, 0.9), (0.4, 0.08, 0.75), (0.8, 0.5, 1.0))
def spec_violet_metalflake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=253, r_base=20, r_amp=14, flake_density=0.024)

def paint_teal_metalflake(paint, shape, mask, seed, pm, bb):
    return _colorflake(paint, shape, mask, seed, (0.5, 0.85, 0.85), (0.02, 0.55, 0.55), (0.4, 1.0, 1.0))
def spec_teal_metalflake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=253, r_base=20, r_amp=14, flake_density=0.024)

def paint_magenta_metalflake(paint, shape, mask, seed, pm, bb):
    return _colorflake(paint, shape, mask, seed, (0.92, 0.55, 0.8), (0.78, 0.05, 0.5), (1.0, 0.5, 0.85))
def spec_magenta_metalflake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=253, r_base=20, r_amp=14, flake_density=0.024)

def paint_burnt_orange_metal(paint, shape, mask, seed, pm, bb):
    return _colorflake(paint, shape, mask, seed, (0.92, 0.62, 0.3), (0.85, 0.32, 0.04), (1.0, 0.7, 0.4), depth=0.6)
def spec_burnt_orange_metal(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=205, m_flake=253, r_base=22, r_amp=14, flake_density=0.024)

# ---- EXOTIC SHIFT ----
def paint_titanium_anodize(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    t = _norm01(_noise((h, w), [16, 34, 70], [0.4, 0.35, 0.25], seed))
    film = np.asarray(interference_palette(t, orders=3.0, quantize=0.45, brightness=1.05), np.float32)
    ti = np.array([0.55, 0.56, 0.60], np.float32)
    col = np.clip(film * 0.65 + ti[None, None, :] * 0.35, 0, 1)
    fl = _flake((h, w), seed, 0.012, lo=0.45)
    col = np.clip(col + fl[:, :, None] * 0.4, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_titanium_anodize(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=210, m_flake=250, r_base=20, r_amp=12, flake_density=0.012)

def paint_chrome_rainbow_flake(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32); base[:] = (0.74, 0.76, 0.80)   # chrome body
    fl = np.clip(_flake((h, w), seed, 0.03, lo=0.4), 0, 1)
    rainbow = np.asarray(interference_palette(_grain((h, w), seed + 8), orders=4.0, quantize=0.35, brightness=1.2), np.float32)
    col = np.clip(base * (1 - fl[:, :, None]) + rainbow * fl[:, :, None], 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_chrome_rainbow_flake(shape, seed, sm, base_m, base_r):
    return _metal_spec(shape, seed, sm, base_m, base_r, m_body=235, m_flake=255, r_base=16, r_amp=10, flake_density=0.03)
