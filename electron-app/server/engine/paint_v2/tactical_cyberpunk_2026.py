# -*- coding: utf-8 -*-
"""
engine/paint_v2/tactical_cyberpunk_2026.py — ★ TACTICAL & CYBERPUNK (new 2026-06-14)

Reconception of "Industrial & Tactical". 20 finishes: 10 mil-spec CAMO + solids,
10 CYBERPUNK. SPB crushes finishes down and lives on MICRO detail — so every pattern
here is FINE (camo blobs ~10-30px, grids/traces ~10-16px at 2048) with ragged
fine-broken edges, NOT big shapes. Each cyberpunk finish is a DISTINCT design (routed
circuit vs grid vs gradient+grid vs pinstripe vs hex vs glyph-rain vs plasma) — no
recolored-and-flipped clones.

Contracts: paint_x(paint,shape,mask,seed,pm,bb)->HxWx3 ; spec_x(shape,seed,sm,bm,br)->(M,R,CC).
M mostly flat dielectric (trivially decorrelated); chrome rides its own field vs R-grain.
Patterns rotated/omnidirectional (UV-agnostic). <3s @2048.
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array
from engine.color_science import interference_palette

_TC_CACHE = {}


def _cache(key, fn):
    v = _TC_CACHE.get(key)
    if v is None:
        if len(_TC_CACHE) > 160:
            _TC_CACHE.clear()
        v = fn()
        _TC_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, scales, weights, seed, cap=0):
    """multi_scale_noise; scales = feature size in PIXELS (lower=finer). cap=0 => full-res
    so FINE features survive (no work-res blur)."""
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
        rng = np.random.default_rng((int(seed) ^ 0x1F3D) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        return ((n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) * 0.333).astype(np.float32)

    return _cache(key, build)


def _rot(shape, deg):
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    a = np.deg2rad(deg); ca, sa = np.cos(a), np.sin(a)
    return (x * ca + y * sa).astype(np.float32), (-x * sa + y * ca).astype(np.float32)


# ---------- CAMO (fine blobs + ragged micro edges) ----------

def _camo(paint, shape, mask, seed, palette, scale=12, pixel=0, angular=False, micro=0.05):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    coarse = _norm01(_noise((h, w), [scale, scale * 2, scale * 4], [0.5, 0.3, 0.2], seed))
    fine = _norm01(_noise((h, w), [max(2, scale // 3), max(3, scale // 2)], [0.5, 0.5], seed + 9))
    v = _norm01(coarse + 0.32 * fine)                 # ragged fine-broken blob edges
    if angular:
        v = np.abs((v * 3.0) % 1.0 - 0.5) * 2.0
    if pixel > 0:
        vs = v[::pixel, ::pixel]
        v = np.repeat(np.repeat(vs, pixel, 0), pixel, 1)[:h, :w]
    pal = np.asarray(palette, np.float32); nb = len(pal)
    band = np.clip((v * nb).astype(np.int32), 0, nb - 1)
    col = pal[band]
    g = _grain((h, w), seed + 3)[:, :, None]
    col = np.clip(col * (1.0 + micro * (g - 0.5) * 2.0), 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)


def _camo_spec(shape, seed, sm, r_base=170.0, r_amp=30.0, cc=120.0, m_flat=8.0):
    h, w = shape[:2]
    g = _grain((h, w), seed + 3)
    R = np.clip(r_base + r_amp * (g - 0.5) * 2.0 * sm, 15, 255)
    return (np.full((h, w), m_flat, np.float32), R.astype(np.float32), np.full((h, w), cc, np.float32))


def _solid(paint, shape, mask, seed, color, micro=0.06):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    g = _grain((h, w), seed + 3)[:, :, None]
    col = np.clip(np.asarray(color, np.float32)[None, None, :] * (1.0 + micro * (g - 0.5) * 2.0), 0, 1)
    m = mask[:, :, None]
    return (col * m + paint * (1 - m)).astype(np.float32)


# ---------- pattern fields (all FINE) ----------

def _stripes_field(shape, seed, period, deg, warp=2.6):
    """Wavy directional brush stripes (tiger). 0..1."""
    h, w = shape[:2]
    u, v = _rot((h, w), deg)
    wf = _norm01(_noise((h, w), [period, period * 2], [0.6, 0.4], seed + 5))
    s = np.sin((v / period + wf * warp) * np.pi * 2.0)
    return (np.clip(np.abs(s) * 1.6 - 0.4, 0, 1)).astype(np.float32)   # bold stripe masks


def _grid_field(shape, period, deg=24.0, width=0.05):
    u, v = _rot(shape, deg)
    fu = np.abs((u / period) % 1.0 - 0.5); fv = np.abs((v / period) % 1.0 - 0.5)
    return np.clip(1.0 - np.minimum(fu, fv) / width, 0, 1).astype(np.float32)


def _node_field(shape, period, deg=24.0):
    u, v = _rot(shape, deg)
    fu = np.abs((u / period) % 1.0 - 0.5); fv = np.abs((v / period) % 1.0 - 0.5)
    return np.clip(1.0 - np.sqrt(fu * fu + fv * fv) / 0.12, 0, 1).astype(np.float32)


def _circuit_field(shape, seed, period, deg=18.0):
    u, v = _rot(shape, deg)
    fu = np.abs((u / period) % 1.0 - 0.5); fv = np.abs((v / period) % 1.0 - 0.5)
    gu = _norm01(_noise(shape, [max(2, period)], [1.0], seed + 1, cap=640))
    gv = _norm01(_noise(shape, [max(2, period)], [1.0], seed + 2, cap=640))
    lx = (fv < 0.07).astype(np.float32) * (gu > 0.42)
    ly = (fu < 0.07).astype(np.float32) * (gv > 0.42)
    nodes = ((fu < 0.16) & (fv < 0.16)).astype(np.float32)
    return np.clip(np.maximum.reduce([lx, ly, nodes]), 0, 1).astype(np.float32)


def _hex_field(shape, period):
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    s = (2.0 * np.pi) / float(period)
    g = (np.cos(x * s) + np.cos((0.5 * x + 0.866 * y) * s) + np.cos((0.5 * x - 0.866 * y) * s)) / 3.0
    return np.clip(1.0 - np.abs(g) * 2.4, 0, 1).astype(np.float32)


def _pinstripe_field(shape, period, deg):
    u, v = _rot(shape, deg)
    return np.clip(1.0 - np.abs((u / period) % 1.0 - 0.5) / 0.18, 0, 1).astype(np.float32)


def _glow(paint, shape, mask, seed, base_rgb, glow_rgb, line, glow2_rgb=None, line2=None):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    col = np.empty((h, w, 3), np.float32); col[:] = np.asarray(base_rgb, np.float32)
    l = np.clip(line, 0, 1)[:, :, None]
    col = col * (1 - l) + np.asarray(glow_rgb, np.float32)[None, None, :] * l
    if glow2_rgb is not None and line2 is not None:
        l2 = np.clip(line2, 0, 1)[:, :, None]
        col = col * (1 - l2) + np.asarray(glow2_rgb, np.float32)[None, None, :] * l2
    col = np.clip(col, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)


def _glow_spec(shape, seed, sm, line, r_line=18.0, r_base=150.0, cc=40.0, m_flat=0.0):
    h, w = shape[:2]
    l = np.clip(np.asarray(line, np.float32), 0, 1)
    g = _grain((h, w), seed + 3)
    R = np.clip(r_base + 25.0 * (g - 0.5) * 2.0 * sm - (r_base - r_line) * l * sm, 15, 255)
    return (np.full((h, w), m_flat, np.float32), R.astype(np.float32), np.full((h, w), cc, np.float32))


# =====================================================================
# THE 20  (FINE scales throughout)
# =====================================================================
# ---- TACTICAL ----
_MULTICAM = [(0.62, 0.58, 0.42), (0.47, 0.49, 0.35), (0.40, 0.35, 0.25), (0.24, 0.26, 0.20), (0.55, 0.50, 0.40)]
def paint_multicam(paint, shape, mask, seed, pm, bb):
    return _camo(paint, shape, mask, seed, _MULTICAM, scale=13)
def spec_multicam(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=165, cc=115)

_MARPAT = [(0.20, 0.28, 0.18), (0.34, 0.28, 0.18), (0.55, 0.50, 0.36), (0.08, 0.09, 0.07)]
def paint_marpat_woodland(paint, shape, mask, seed, pm, bb):
    return _camo(paint, shape, mask, seed, _MARPAT, scale=10, pixel=4)
def spec_marpat_woodland(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=175, cc=125)

_TIGER_BASE = (0.34, 0.36, 0.23); _TIGER_TAN = (0.52, 0.47, 0.31)
def paint_tiger_stripe(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32); base[:] = _TIGER_TAN
    olive = _stripes_field((h, w), seed + 1, 42, 7.0)
    black = _stripes_field((h, w), seed + 2, 26, -5.0)
    col = base * (1 - olive[:, :, None]) + np.asarray(_TIGER_BASE, np.float32)[None, None, :] * olive[:, :, None]
    col = col * (1 - black[:, :, None] * 0.92)                  # dark tiger stripes
    g = _grain((h, w), seed + 3)[:, :, None]
    col = np.clip(col * (1 + 0.05 * (g - 0.5) * 2), 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_tiger_stripe(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=168, cc=118)

_KRYPTEK = [(0.20, 0.21, 0.23), (0.07, 0.07, 0.08), (0.34, 0.35, 0.37), (0.12, 0.13, 0.14)]
def paint_kryptek_typhon(paint, shape, mask, seed, pm, bb):
    return _camo(paint, shape, mask, seed, _KRYPTEK, scale=12, angular=True)
def spec_kryptek_typhon(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=160, cc=110)

_M81 = [(0.28, 0.34, 0.22), (0.38, 0.30, 0.18), (0.08, 0.08, 0.06), (0.52, 0.48, 0.34)]
def paint_m81_woodland(paint, shape, mask, seed, pm, bb):
    return _camo(paint, shape, mask, seed, _M81, scale=15)
def spec_m81_woodland(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=175, cc=125)

_DESERT = [(0.70, 0.62, 0.43), (0.44, 0.34, 0.20), (0.78, 0.71, 0.52), (0.55, 0.46, 0.30)]
def paint_desert_dpm(paint, shape, mask, seed, pm, bb):
    return _camo(paint, shape, mask, seed, _DESERT, scale=11)
def spec_desert_dpm(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=175, cc=125)

_URBAN = [(0.62, 0.63, 0.65), (0.40, 0.41, 0.43), (0.16, 0.17, 0.18), (0.80, 0.81, 0.82)]
def paint_urban_digital(paint, shape, mask, seed, pm, bb):
    return _camo(paint, shape, mask, seed, _URBAN, scale=9, pixel=4)
def spec_urban_digital(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=170, cc=120)

def paint_od_drab(paint, shape, mask, seed, pm, bb):
    return _solid(paint, shape, mask, seed, (0.30, 0.33, 0.20))
def spec_od_drab(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=185, r_amp=20, cc=140)

def paint_coyote_fde(paint, shape, mask, seed, pm, bb):
    return _solid(paint, shape, mask, seed, (0.55, 0.46, 0.33))
def spec_coyote_fde(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=185, r_amp=20, cc=140)

def paint_blackout_ops(paint, shape, mask, seed, pm, bb):
    return _solid(paint, shape, mask, seed, (0.06, 0.06, 0.07), micro=0.10)
def spec_blackout_ops(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=205, r_amp=25, cc=200, m_flat=4)

# ---- CYBERPUNK (each distinct, all fine) ----
def paint_neon_circuit(paint, shape, mask, seed, pm, bb):   # routed traces + nodes
    h, w = shape[:2]
    line = _circuit_field((h, w), seed, 17, deg=16.0)
    line2 = _circuit_field((h, w), seed + 50, 13, deg=-22.0) * 0.85
    return _glow(paint, shape, mask, seed, (0.03, 0.05, 0.08), (0.10, 0.95, 1.0), line,
                 glow2_rgb=(1.0, 0.12, 0.72), line2=line2)
def spec_neon_circuit(shape, seed, sm, base_m, base_r):
    return _glow_spec(shape, seed, sm, _circuit_field(shape, seed, 17, deg=16.0), r_line=16, r_base=120, cc=30)

def paint_tron_grid(paint, shape, mask, seed, pm, bb):      # fine grid + bright intersection nodes + depth fade
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    fade = _norm01(x * 0.5 + y * 0.7)                       # recession glow gradient
    line = _grid_field((h, w), 26, deg=24.0, width=0.10) * (0.50 + 0.50 * fade)
    nodes = _node_field((h, w), 26, deg=24.0)
    return _glow(paint, shape, mask, seed, (0.02, 0.03, 0.06), (0.10, 0.70, 1.0), line,
                 glow2_rgb=(0.7, 0.95, 1.0), line2=nodes)
def spec_tron_grid(shape, seed, sm, base_m, base_r):
    return _glow_spec(shape, seed, sm, _grid_field(shape, 26, deg=24.0, width=0.10), r_line=16, r_base=130, cc=30)

def paint_synthwave(paint, shape, mask, seed, pm, bb):      # magenta->cyan gradient + FINE grid + sun band
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    t = _norm01(x * 0.4 + y * 0.9)
    mag = np.array([0.92, 0.10, 0.62], np.float32); cyn = np.array([0.10, 0.62, 0.95], np.float32)
    grad = mag[None, None, :] * (1 - t[:, :, None]) + cyn[None, None, :] * t[:, :, None]
    sun = np.clip(1.0 - np.abs(t - 0.5) * 6.0, 0, 1)[:, :, None] * np.array([1.0, 0.65, 0.10], np.float32)[None, None, :]
    line = _grid_field((h, w), 22, deg=24.0, width=0.075)
    col = grad * 0.7 + sun * 0.35
    col = np.clip(col * (1 - line[:, :, None]) + np.array([0.85, 0.98, 1.0])[None, None, :] * line[:, :, None], 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_synthwave(shape, seed, sm, base_m, base_r):
    return _glow_spec(shape, seed, sm, _grid_field(shape, 22, deg=24.0, width=0.075), r_line=18, r_base=70, cc=24)

def paint_data_rain(paint, shape, mask, seed, pm, bb):      # fine matrix glyph rain
    h, w = shape[:2]
    u, v = _rot((h, w), 10.0)
    col_streak = _norm01(_noise((h, w), [2], [1.0], seed + 7))
    drip = (np.sin(v * 0.5 + col_streak * 40.0) * 0.5 + 0.5) ** 3
    lane = (np.abs((u / 5.0) % 1.0 - 0.5) < 0.28).astype(np.float32)
    line = np.clip(drip * lane * (col_streak > 0.42), 0, 1).astype(np.float32)
    return _glow(paint, shape, mask, seed, (0.02, 0.05, 0.03), (0.25, 1.0, 0.35), line)
def spec_data_rain(shape, seed, sm, base_m, base_r):
    u, v = _rot(shape, 10.0)
    col_streak = _norm01(_noise(shape, [2], [1.0], seed + 7))
    drip = (np.sin(v * 0.5 + col_streak * 40.0) * 0.5 + 0.5) ** 3
    lane = (np.abs((u / 5.0) % 1.0 - 0.5) < 0.28).astype(np.float32)
    return _glow_spec(shape, seed, sm, np.clip(drip * lane, 0, 1), r_line=20, r_base=160, cc=80)

def paint_glitch_rgb(paint, shape, mask, seed, pm, bb):     # fine scanline RGB shift + small blocks
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32); base[:] = (0.06, 0.06, 0.09)
    scan = _norm01(_noise((h, w), [2, 4], [0.6, 0.4], seed + 1))         # fine horizontal scan bands
    block = (_norm01(_noise((h, w), [5, 9], [0.5, 0.5], seed + 2)) > 0.55).astype(np.float32)
    rb = np.roll(block, 3, axis=1); bb_ = np.roll(block, -3, axis=1)     # channel offset = chromatic glitch
    base[:, :, 0] += rb * (scan > 0.55) * 0.9
    base[:, :, 1] += block * (scan < 0.45) * 0.8
    base[:, :, 2] += bb_ * (scan > 0.5) * 0.9
    col = np.clip(base, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_glitch_rgb(shape, seed, sm, base_m, base_r):
    block = (_norm01(_noise(shape, [5, 9], [0.5, 0.5], seed + 2)) > 0.55).astype(np.float32)
    return _glow_spec(shape, seed, sm, block, r_line=24, r_base=120, cc=40)

def paint_hex_tech(paint, shape, mask, seed, pm, bb):       # fine glowing hex panels
    h, w = shape[:2]
    return _glow(paint, shape, mask, seed, (0.04, 0.06, 0.09), (0.12, 0.85, 1.0), _hex_field((h, w), 11))
def spec_hex_tech(shape, seed, sm, base_m, base_r):
    return _glow_spec(shape, seed, sm, _hex_field(shape, 11), r_line=18, r_base=130, cc=30)

def paint_holo_vapor(paint, shape, mask, seed, pm, bb):     # fine holographic vapor
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    t = _norm01(_noise((h, w), [8, 18], [0.5, 0.5], seed))
    col = np.asarray(interference_palette(t, orders=4.0, quantize=0.35, brightness=1.15), np.float32)
    col = np.clip(col * 0.72 + 0.26, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_holo_vapor(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    return _glow_spec(shape, seed, sm, _norm01(_noise((h, w), [8, 18], [0.5, 0.5], seed)), r_line=20, r_base=40, cc=20)

def paint_chrome_neon(paint, shape, mask, seed, pm, bb):    # chrome + FINE diagonal neon pinstripes (distinct from grids)
    h, w = shape[:2]
    pin_m = _pinstripe_field((h, w), 17, deg=34.0)
    pin_c = _pinstripe_field((h, w), 25, deg=34.0)
    return _glow(paint, shape, mask, seed, (0.66, 0.69, 0.76), (1.0, 0.10, 0.66), pin_m,
                 glow2_rgb=(0.10, 0.95, 1.0), line2=pin_c)
def spec_chrome_neon(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    pin = np.clip(_pinstripe_field((h, w), 17, deg=34.0) + _pinstripe_field((h, w), 25, deg=34.0), 0, 1)
    g = _grain((h, w), seed + 3)
    M = np.clip(235.0 - pin * 210.0 * sm, 0, 255)           # chrome body high M, neon pins dielectric
    R = np.clip(20.0 + 30.0 * (g - 0.5) * 2.0 * sm, 15, 255)   # R on independent grain (decorrelated)
    return (M.astype(np.float32), R.astype(np.float32), np.full((h, w), 16.0, np.float32))

def paint_plasma_pulse(paint, shape, mask, seed, pm, bb):   # fine plasma filaments
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2]
    turb = _noise((h, w), [8, 18, 36], [0.4, 0.35, 0.25], seed)
    p = _norm01(np.sin(turb * 9.0) + turb * 2.0)
    blue = np.array([0.18, 0.30, 1.0], np.float32); purp = np.array([0.62, 0.10, 0.95], np.float32)
    col = blue[None, None, :] * (1 - p[:, :, None]) + purp[None, None, :] * p[:, :, None]
    arc = np.clip((np.sin(turb * 26.0) ** 8), 0, 1)[:, :, None]
    col = np.clip(col * (0.35 + 0.65 * p[:, :, None]) + arc * 0.7, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)
def spec_plasma_pulse(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    turb = _noise((h, w), [8, 18, 36], [0.4, 0.35, 0.25], seed)
    return _glow_spec(shape, seed, sm, np.clip((np.sin(turb * 26.0) ** 8), 0, 1), r_line=18, r_base=90, cc=24)

_CYBERCAMO = [(0.04, 0.05, 0.10), (0.10, 0.85, 1.0), (0.85, 0.10, 0.75), (0.45, 0.10, 0.90)]
def paint_cyber_camo(paint, shape, mask, seed, pm, bb):     # fine neon pixel camo
    return _camo(paint, shape, mask, seed, _CYBERCAMO, scale=9, pixel=4, micro=0.06)
def spec_cyber_camo(shape, seed, sm, base_m, base_r):
    return _camo_spec(shape, seed, sm, r_base=90, r_amp=30, cc=24, m_flat=0)
