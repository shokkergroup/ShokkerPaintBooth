# -*- coding: utf-8 -*-
"""
Candy Special Paint Functions — v5 engine
13 unique candy + pearlescent + iridescent effects with physics-based optics.
Each function implements specific optical phenomena:
- Beer-Lambert absorption (single & multi-pass)
- Fresnel reflection + color filtering
- Diffraction grating & adularescence
- Plateau-Rayleigh instability patterns
"""

import numpy as np
from scipy.spatial import cKDTree
from engine.core import _resize_array, multi_scale_noise, get_mgrid, hsv_to_rgb_vec
from engine.paint_v2 import ensure_bb_2d
from engine.color_science import candy_absorb


_CANDY_FIELD_CACHE = {}
# SPB paint-finish perf loop tick 2026-05-31 05:23; owner: "Speed is king in this app."
# Exact shared-field reuse only: candy_emerald 5692.5->4836.7 ms, candy_burgundy 5211.4->4803.5 ms, candy_apple 5323.1->5069.8 ms; std drift 0.
# SPB paint-finish perf loop tick 2026-05-31 06:38; owner: "Speed is king in this app."
# Hypershift Spectral keeps the same fine-flake recipe but reuses float32 coordinate/warp fields and full-mask blend output: 7947.7->6068.1 ms; paint std drift -0.000005, spec std drift +0.006676.
# SPB paint-finish perf loop tick 2026-05-31 07:23; owner: "Speed is king in this app."
# Moonstone keeps its cabochon/adularescence recipe while reusing geometry/noise fields and full-mask paint output: 7459.5->5972.4 ms; paint std drift 0, spec std drift +0.000084.
_CANDY_HYPERSHIFT_ANCHORS = np.array([0.02, 0.12, 0.28, 0.52, 0.72, 0.88], dtype=np.float32)


def _candy_cache_put(key, value):
    if len(_CANDY_FIELD_CACHE) > 96:
        _CANDY_FIELD_CACHE.clear()
    _CANDY_FIELD_CACHE[key] = value
    return value


def _candy_noise(shape, scales, weights, seed, cap=768):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("noise", int(h), int(w), tuple(scales), tuple(weights), int(seed), int(cap))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(int(cap), int(h), int(w))
    if work < min(h, w):
        sh = max(64, int(round(h * work / max(h, w))))
        sw = max(64, int(round(w * work / max(h, w))))
        field = multi_scale_noise((sh, sw), scales, weights, seed)
        field = _resize_array(np.asarray(field, dtype=np.float32), h, w)
    else:
        field = multi_scale_noise((h, w), scales, weights, seed)
    return _candy_cache_put(key, np.asarray(field, dtype=np.float32))


def _candy_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _candy_edge01(arr):
    gy, gx = np.gradient(np.asarray(arr, dtype=np.float32))
    return _candy_norm01(np.sqrt(gx * gx + gy * gy))


def _candy_pinfield(shape, seed, density=0.006):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("pins", int(h), int(w), int(seed), float(density))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    n = min(int(h * w * density), 90000)
    out = np.zeros((h, w), dtype=np.float32)
    if n > 0:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.20, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    return _candy_cache_put(key, np.maximum.reduce([
        out,
        np.roll(out, 1, axis=0) * 0.34,
        np.roll(out, -1, axis=1) * 0.34,
    ]).astype(np.float32))


def _candy_burgundy_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("burgundy_fields", int(h), int(w), int(seed))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    body = _candy_norm01(_candy_noise((h, w), [5, 13, 31], [0.40, 0.36, 0.24], seed + 1602))
    fine = _candy_norm01(_candy_noise((h, w), [1, 2, 4], [0.42, 0.34, 0.24], seed + 1603))
    clot = np.clip((body - 0.46) * 2.4, 0, 1)
    skin = _candy_edge01(body * 0.66 + fine * 0.34)
    serum = np.clip((fine - 0.63) * 2.7 + skin * 0.32, 0, 1)
    pins = _candy_pinfield((h, w), seed + 1604, 0.011)
    return _candy_cache_put(key, (body, fine, clot, skin, serum, pins))


def _candy_apple_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("apple_fields", int(h), int(w), int(seed))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    y, x = get_mgrid((h, w))
    body = _candy_norm01(_candy_noise((h, w), [4, 10, 24], [0.40, 0.36, 0.24], seed + 1645, cap=640))
    lacquer = _candy_norm01(_candy_noise((h, w), [1, 2, 4], [0.45, 0.34, 0.21], seed + 1646, cap=640))
    flow = np.exp(-np.abs(np.sin((x * 0.028 + y * 0.011 + body * 1.8) * np.pi)) * 8.0).astype(np.float32)
    pins = _candy_pinfield((h, w), seed + 1647, 0.032)
    edge = _candy_edge01(body * 0.50 + lacquer * 0.38 + flow * 0.12)
    return _candy_cache_put(key, (body, lacquer, flow, pins, edge))


def _candy_emerald_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("emerald_fields", int(h), int(w), int(seed))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    body = _candy_norm01(_candy_noise((h, w), [6, 15, 34], [0.40, 0.35, 0.25], seed + 1608))
    fine = _candy_norm01(_candy_noise((h, w), [1, 3, 6], [0.4, 0.3, 0.3], seed + 1609))
    bubble = np.clip((body - 0.56) * 2.2, 0, 1)
    glass_edge = _candy_edge01(body * 0.58 + fine * 0.42)
    phosphor = _candy_pinfield((h, w), seed + 1699, 0.010)
    return _candy_cache_put(key, (body, fine, bubble, glass_edge, phosphor))


def _candy_hypershift_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("hypershift_fields", int(h), int(w), int(seed))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    y, x = get_mgrid((h, w))
    xn = (x.astype(np.float32, copy=False) / np.float32(max(w - 1, 1))).astype(np.float32, copy=False)
    yn = (y.astype(np.float32, copy=False) / np.float32(max(h - 1, 1))).astype(np.float32, copy=False)
    warp = _candy_norm01(_candy_noise((h, w), [8, 18, 48], [0.44, 0.34, 0.22], seed + 1780, cap=720))
    return _candy_cache_put(key, (xn, yn, warp))


def _candy_moonstone_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("moonstone_fields", int(h), int(w), int(seed))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    y, x = get_mgrid((h, w))
    xn = (x.astype(np.float32, copy=False) / np.float32(max(w - 1, 1))).astype(np.float32, copy=False)
    yn = (y.astype(np.float32, copy=False) / np.float32(max(h - 1, 1))).astype(np.float32, copy=False)
    cx = np.float32(0.48 + (seed % 17) / 200.0)
    cy = np.float32(0.44 + (seed % 13) / 200.0)
    r = np.sqrt((xn - cx) ** 2 + (yn - cy) ** 2).astype(np.float32)
    r_norm = np.clip(r / np.float32(0.62), 0.0, 1.0).astype(np.float32)
    core = np.exp(-r * r * np.float32(14.0)).astype(np.float32)
    wave = np.sin(xn * 18.0 + yn * 11.0 + seed * 0.002).astype(np.float32)
    moon_noise = _candy_noise((h, w), [8, 16, 32], [0.42, 0.34, 0.24], seed + 1617, cap=720)
    mica = _candy_pinfield((h, w), seed + 1618, 0.022)
    return _candy_cache_put(key, (xn, yn, r, r_norm, core, wave, moon_noise, mica))


def _candy_deep_pearl_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("deep_pearl_fields", int(h), int(w), int(seed))
    cached = _CANDY_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    y, x = get_mgrid((h, w))
    xn = (x.astype(np.float32, copy=False) / np.float32(max(w - 1, 1))).astype(np.float32, copy=False)
    yn = (y.astype(np.float32, copy=False) / np.float32(max(h - 1, 1))).astype(np.float32, copy=False)
    nacre = _candy_norm01(_candy_noise((h, w), [7, 17, 37], [0.42, 0.35, 0.23], seed + 1730, cap=720))
    cloud = _candy_norm01(_candy_noise((h, w), [2, 5, 11], [0.45, 0.34, 0.21], seed + 1731, cap=720))
    veil = np.exp(-np.abs(np.sin((xn * 13.0 - yn * 7.0 + nacre * 2.2) * np.pi)) * 7.5).astype(np.float32)
    mica = _candy_pinfield((h, w), seed + 1732, 0.025)
    hair = _candy_norm01(np.sin(x * 0.41 + y * 0.19 + cloud * 3.2) + np.sin(x * -0.27 + y * 0.58) * 0.55)
    edge = _candy_edge01(nacre * 0.45 + cloud * 0.35 + veil * 0.20)
    # SPB perf loop 2026-05-31; owner hard ceiling: no base over 4s. Shared nacre/mica field, same detail recipe.
    return _candy_cache_put(key, (xn, yn, nacre, cloud, veil, mica, hair, edge))


def paint_candy_v2(paint, shape, mask, seed, pm, bb):
    """
    Generic candy coat — Beer-Lambert per-channel absorption.
    FIX: was hardcoded red → now tints toward base paint's dominant hue.
    Added micro-sparkle for candy depth.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Generate variation — married to spec
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1600)

    # TRUE Beer–Lambert absorption (engine/color_science 2026-06-09): candy is
    # the lit basecoat seen THROUGH tinted clear. Transmission tint = the base's
    # own hue saturated (channels below the dominant absorb harder); coat depth
    # varies with the noise, so thick pools go darker AND more saturated instead
    # of the old lerp's chalky flattening.
    dom = np.clip(base[:, :, :3].max(axis=2, keepdims=True), 0.08, 1.0)
    tint = np.clip(base[:, :, :3] / dom, 0.02, 1.0) ** 1.8
    depth = (0.55 + noise * 0.55) * 1.15
    metal = np.clip(base[:, :, :3] * 1.18 + 0.05, 0.0, 1.0)
    effect = base.copy()
    effect[:, :, :3] = candy_absorb(metal, tint, depth)

    # Micro-sparkle: 0.3% of pixels get bright candy highlights
    rng = np.random.RandomState(seed + 1600)
    sparkle_mask = (rng.random((h, w)) > 0.997).astype(np.float32)
    sparkle = sparkle_mask * 0.25 * pm
    effect[:, :, :3] = np.clip(effect[:, :, :3] + sparkle[:, :, np.newaxis], 0, 1)

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.20 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy(shape, seed, sm, base_m, base_r):
    """Generic candy spec: wet clear depth plus embedded flake, not flat chrome."""
    h, w = shape[:2] if len(shape) > 2 else shape
    body = _candy_norm01(_candy_noise((h, w), [3, 7, 15], [0.40, 0.34, 0.26], seed + 1600))
    resin = _candy_norm01(_candy_noise((h, w), [1, 2, 4], [0.42, 0.34, 0.24], seed + 1601))
    edge = _candy_edge01(body * 0.60 + resin * 0.40)
    pins = _candy_pinfield((h, w), seed + 1602, 0.010)
    M = np.clip(base_m * 0.72 + edge * 54.0 * sm + pins * 78.0 * sm + resin * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(max(base_r * 0.58, 15.0) + (1.0 - body) * 24.0 * sm + resin * 18.0 * sm - pins * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(22.0 + body * 46.0 * sm + edge * 34.0 * sm + pins * 30.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_candy_burgundy_v2(paint, shape, mask, seed, pm, bb):
    """
    Deep burgundy candy with wine-red absorption profile.
    Multi-scale absorption creates depth with warm undertones.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise_coarse, noise_fine, clot, skin, serum, pins = _candy_burgundy_fields((h, w), seed)
    
    # Wine-red Beer–Lambert absorption (engine/color_science 2026-06-09):
    # transmission tint chosen so a mid (0.6) basecoat at depth 1.0 lands on the
    # classic burgundy target; thicker zones deepen toward black-cherry
    # physically instead of lerping to a flat opaque red.
    burgundy_t = np.array([0.63, 0.042, 0.117], dtype=np.float32)  # transmission @ depth 1
    fresh_edge = np.array([0.72, 0.030, 0.095], dtype=np.float32)
    depth = (0.40 + (noise_coarse * 0.18 + noise_fine * 0.13)) * 2.0
    metal = np.clip(base * 0.85 + 0.18, 0.0, 1.0)                  # lit basecoat under the clear
    effect = candy_absorb(metal, burgundy_t, depth)
    effect = np.clip(
        effect * (1.0 - clot[:, :, None] * 0.16)
        + fresh_edge[None, None, :] * (skin[:, :, None] * 0.12 + serum[:, :, None] * 0.10)
        + pins[:, :, None] * np.array([0.30, 0.062, 0.090], dtype=np.float32),
        0,
        1,
    )

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    # (The old post-hoc blue-suppression line is gone: Beer–Lambert absorption
    # with burgundy_t's tiny blue transmission now suppresses short wavelengths
    # in thick-coat zones physically — WEAK-CANDY-001 is solved at the source.)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_burgundy(shape, seed, sm, base_m, base_r):
    """
    Burgundy spec — muted highlight with wine-stained appearance.
    G channel clamped to minimum 15 (iRacing GGX requires non-zero roughness for candy).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_candy_burgundy_v2: seed+1602 [4,8], seed+1603 [1,2]
    noise_coarse = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1602)
    noise_fine = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 1603)
    # base_m/base_r arrive as 0-255 from registry — work in native space
    M = np.full((h, w), base_m * 0.85, dtype=np.float32) + noise_coarse * 25.0 * sm
    R = np.full((h, w), max(base_r * 0.6, 15.0), dtype=np.float32) + noise_fine * 15.0 * sm
    CC = np.clip(16.0 + noise_coarse * 8.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            CC)


def spec_candy_burgundy(shape, seed, sm, base_m, base_r):
    """Coagulated Blood spec: rough clot islands, glossy serum pockets, hot skin edges."""
    h, w = shape[:2] if len(shape) > 2 else shape
    body, fine, clot, skin, serum, pins = _candy_burgundy_fields((h, w), seed)
    M = np.clip(base_m * 0.52 + skin * 74.0 * sm + serum * 46.0 * sm + pins * 82.0 * sm - clot * 18.0, 0, 255)
    R = np.clip(max(base_r * 0.72, 15.0) + clot * 64.0 * sm + fine * 26.0 * sm - serum * 24.0 * sm - pins * 10.0, 15, 255)
    CC = np.clip(18.0 + serum * 76.0 * sm + skin * 44.0 * sm + pins * 28.0 * sm - clot * 10.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_candy_chrome_v2(paint, shape, mask, seed, pm, bb):
    """
    Candy over chrome base — maximum reflection + color filter.
    Fresnel effect with strong directional highlights over reflective substrate.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Fresnel approximation: more reflection at grazing angles
    grid = get_mgrid((h, w))
    fresnel = 0.3 + 0.4 * np.abs(np.sin(grid[1] * np.pi))  # View angle simulation
    
    noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 1606)
    
    # Chrome candy via Beer–Lambert (engine/color_science 2026-06-09): a bright
    # reflective substrate seen through orange-red tinted clear; where the
    # fresnel reflection is strong the optical path is longer, so the filter
    # deepens instead of washing toward an opaque overlay color.
    candy_filter_t = np.array([0.92, 0.34, 0.12], dtype=np.float32)  # transmission @ depth 1
    reflection = fresnel * (0.8 + noise * 0.15)
    metal = np.clip(base * 0.45 + 0.50, 0.0, 1.0)                    # chrome substrate stays lit
    depth = 0.35 + reflection * 1.05
    effect = candy_absorb(metal, candy_filter_t, depth)
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_chrome(shape, seed, sm, base_m, base_r):
    """
    Chrome candy spec — strong metallic highlight with sharp edges.
    G channel clamped to minimum 15 (iRacing GGX requires non-zero roughness for candy).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    grid = get_mgrid((h, w))
    fresnel_spec = 0.5 + 0.3 * np.abs(np.sin(grid[1] * np.pi))
    # base_m/base_r in 0-255 — candy chrome is near-max metallic
    M = np.full((h, w), base_m * 0.95, dtype=np.float32) + fresnel_spec * 12.0 * sm
    fine_noise = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1607)
    R = np.full((h, w), max(base_r * 0.5, 15.0), dtype=np.float32) + fine_noise * 10.0 * sm
    CC = np.clip(16.0 + fine_noise * 4.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            CC)

def paint_candy_emerald_v2(paint, shape, mask, seed, pm, bb):
    """
    Green candy with copper phthalocyanine pigment absorption.
    Deep green with subtle blue shift — wavelength-dependent penetration.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise_primary = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1608)
    noise_secondary = multi_scale_noise((h, w), [1, 3, 6], [0.4, 0.3, 0.3], seed + 1609)
    
    # Emerald Beer–Lambert absorption (engine/color_science 2026-06-09): CuPc
    # transmission tint — deep green with blue undertone that deepens physically
    # with coat thickness instead of lerping to a flat opaque green.
    emerald_t = np.array([0.17, 0.83, 0.50], dtype=np.float32)       # transmission @ depth 1
    depth = (0.42 + (noise_primary * 0.15 + noise_secondary * 0.08)) * 2.0
    metal = np.clip(base * 0.88 + 0.14, 0.0, 1.0)
    effect = candy_absorb(metal, emerald_t, depth)

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    # Copper phthalocyanine micro-crystalline fleck sparkle — WEAK-CANDY-001 FIX
    # CuPc pigments have angular crystal facets that produce bright micro-specular points
    rng = np.random.RandomState(seed + 1699)
    sparkle = (rng.random((h, w)) < 0.003).astype(np.float32) * pm * 0.4 * mask
    # WARN-CANDY-001 FIX: green-yellow tint matches CuPc spectral output (not white)
    result = np.clip(result + sparkle[:,:,np.newaxis] * np.array([0.8, 1.0, 0.3], dtype=np.float32), 0, 1).astype(np.float32)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_emerald(shape, seed, sm, base_m, base_r):
    """
    Emerald spec — cool green reflection with moderate sparkle.
    G channel clamped to minimum 15 (iRacing GGX requires non-zero roughness for candy).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_candy_emerald_v2: seed+1608 [2,4], seed+1609 [1,3,6]
    noise_primary = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1608)
    noise_secondary = multi_scale_noise((h, w), [1, 3, 6], [0.4, 0.3, 0.3], seed + 1609)
    # base_m/base_r in 0-255 — emerald candy, moderate metallic
    M = np.full((h, w), base_m * 0.8, dtype=np.float32) + noise_primary * 20.0 * sm
    R = np.full((h, w), max(base_r * 0.6, 15.0), dtype=np.float32) + noise_secondary * 15.0 * sm
    CC = np.clip(16.0 + noise_primary * 8.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            CC)


def paint_hydrographic_v2(paint, shape, mask, seed, pm, bb):
    """
    Water transfer film with Plateau-Rayleigh instability pattern.
    Thin film creates ripple-like surface waves with color shifts.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    grid = get_mgrid((h, w))
    # Plateau-Rayleigh instability: sinusoidal ripple pattern
    ripples = 0.5 + 0.3 * np.sin(grid[0] * 8 + seed) * np.cos(grid[1] * 6 + seed * 1.3)
    
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1612)
    
    # Water film effect: subtle color shift with ripple modulation
    hydrographic = np.array([0.3, 0.6, 0.7])
    effect = base * 0.5 + hydrographic[np.newaxis, np.newaxis, :] * (ripples[:,:,np.newaxis] * 0.4 + noise[:,:,np.newaxis] * 0.1)
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_hydrographic(shape, seed, sm, base_m, base_r):
    """
    Hydrographic spec — water-surface pattern with variable specularity.
    """
    h, w = shape
    grid = get_mgrid((h, w))
    ripple_pattern = 0.5 + 0.3 * np.sin(grid[0] * 8) * np.cos(grid[1] * 6)
    # base_m/base_r in 0-255 — hydrographic has moderate metallic
    M = np.full((h, w), base_m * 0.7, dtype=np.float32) + ripple_pattern * 30.0 * sm
    noise_cc = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1613)
    R = np.full((h, w), max(base_r * 0.5, 15.0), dtype=np.float32) + noise_cc * 20.0 * sm
    CC = np.clip(16.0 + noise_cc * 8.0 * sm, 16, 32).astype(np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            CC)


def _legacy_paint_jelly_pearl_v2_pre_micro_detail(paint, shape, mask, seed, pm, bb):
    """
    Translucent jelly pearl: BASE COLOR SHOWS THROUGH with pearlescent wash.
    Pearl particles create shimmer highlights that shift. No fixed jelly color.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Pearl particle distribution (scattered bright shimmer spots)
    particle_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1614)
    particles = np.clip((particle_noise - 0.3) * 2.0, 0, 1)

    # Pearlescent angle-shift simulation
    angle_noise = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1615)
    pearl_shift = angle_noise * 0.5 + 0.5  # 0-1 "viewing angle"

    # Translucent LIGHTEN of base paint (not replacement)
    # Jelly effect: lift the base color toward white with pearl iridescence
    lighten_amount = 0.25  # how much to lighten
    lightened = np.clip(base + lighten_amount, 0, 1)

    # Pearl shimmer highlights that shift color based on "angle"
    shimmer_r = particles * (0.6 + 0.4 * np.sin(pearl_shift * np.pi * 2.0))
    shimmer_g = particles * (0.6 + 0.4 * np.sin(pearl_shift * np.pi * 2.0 + 2.1))
    shimmer_b = particles * (0.6 + 0.4 * np.sin(pearl_shift * np.pi * 2.0 + 4.2))

    # Effect: lightened base + pearl shimmer overlay (base color shows through)
    effect = np.stack([
        np.clip(lightened[:,:,0] + shimmer_r * 0.2, 0, 1),
        np.clip(lightened[:,:,1] + shimmer_g * 0.15, 0, 1),
        np.clip(lightened[:,:,2] + shimmer_b * 0.2, 0, 1),
    ], axis=-1)

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.20 * pm * mask_3d, 0, 1).astype(np.float32)


def _legacy_spec_jelly_pearl_pre_micro_detail(shape, seed, sm, base_m, base_r):
    """
    Jelly pearl spec: pearlescent shimmer with scattered highlight particles.
    Moderate metallic from mica particles, low roughness for gloss, good clearcoat.
    """
    h, w = shape
    # MARRIED to _legacy_paint_jelly_pearl_v2_pre_micro_detail:
    # seed+1614 [4,8,16], seed+1615 [16,32]
    particle_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1614)
    particles = np.clip((particle_noise - 0.3) * 2.0, 0, 1)
    angle = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1615)
    # M: pearl zones = high metallic (mica shimmer), non-pearl = moderate
    M = np.clip(80.0 + particles * 140.0 * sm + angle * 30.0 * sm, 0, 255).astype(np.float32)
    # R: pearl zones = glossy (LOW R), non-pearl = slightly rougher
    # particles HIGH → R low (glossy pearl shimmer). particles LOW → R higher (matte jelly)
    R = np.clip(15.0 + (1.0 - particles) * 20.0 * sm + angle * 5.0 * sm, 15, 255).astype(np.float32)
    # CC: pearl zones = pearlescent (HIGHER CC), non-pearl = less
    CC = np.clip(16.0 + particles * 14.0 * sm + (1.0 - particles) * 4.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC

def paint_moonstone_v2(paint, shape, mask, seed, pm, bb):
    """
    Adularescence light scattering from orthoclase feldspar layers.
    Moving light shimmer effect — glow travels across surface.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    grid = get_mgrid((h, w))
    # WARN-CANDY-003 FIX: seed-derived center avoids every moonstone instance sharing same peak position
    cy = 0.35 + (seed % 31) / 100.0
    cx = 0.35 + (seed % 29) / 100.0
    # Adularescence: light ray traveling across surface
    shimmer = 0.5 + 0.4 * np.sin((grid[0] + grid[1]) * 3 + seed) * np.exp(-((grid[0] - cy)**2 + (grid[1] - cx)**2) * 3)
    
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1617)
    
    # Moonstone: silvery-white with blue adularescence
    moonstone = np.array([0.75, 0.7, 0.8])
    effect = base * 0.6 + moonstone[np.newaxis, np.newaxis, :] * (0.3 + shimmer[:,:,np.newaxis] * 0.3) + noise[:,:,np.newaxis] * 0.1
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.28 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_moonstone(shape, seed, sm, base_m, base_r):
    """
    Moonstone spec — traveling adularescence with directional glow.
    FLAT-FIX: base_m/base_r are 0-255 scale, not 0-1. Fixed math.
    """
    h, w = shape
    grid = get_mgrid((h, w))
    # MARRIED to paint_moonstone_v2: same grid shimmer + Gaussian envelope
    cy = 0.35 + (seed % 31) / 100.0
    cx = 0.35 + (seed % 29) / 100.0
    shimmer = 0.5 + 0.4 * np.sin((grid[0] + grid[1]) * 3 + seed) * np.exp(-((grid[0] - cy)**2 + (grid[1] - cx)**2) * 3)
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1617)
    # base_m, base_r are in 0-255 range — work in that range directly
    M = np.clip(base_m + (shimmer - 0.5) * 40.0 * sm + noise * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + (noise - 0.5) * 25.0 * sm + shimmer * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + shimmer * 12.0 * sm + noise * 6.0 * sm, 16, 255).astype(np.float32)  # CC≥16 always
    return (M, R, CC)


def paint_chameleon_dual_shift_v2(paint, shape, mask, seed, pm, bb):
    """Dual-Shift chameleon with a real teal-to-purple flip and fine flop grain."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)

    flow = _cs_norm01(np.sin(x * 0.021 + y * 0.047 + seed * 0.013) + np.cos(x * -0.036 + y * 0.018) * 0.55)
    grain = _cs_norm01(np.sin(x * 0.19 + y * 0.43 + seed * 0.011) + np.sin(x * -0.37 + y * 0.11) * 0.55)
    angle = np.clip(bb * 0.54 + xn * 0.34 + (1.0 - yn) * 0.22 + flow * 0.24, 0, 1)
    flip = angle * angle * (3.0 - 2.0 * angle)

    teal = np.array([0.015, 0.46, 0.38], dtype=np.float32)
    violet = np.array([0.48, 0.045, 0.76], dtype=np.float32)
    magenta_edge = np.array([0.92, 0.12, 0.78], dtype=np.float32)
    color = teal[None, None, :] * (1.0 - flip[:, :, None]) + violet[None, None, :] * flip[:, :, None]

    flip_line = np.exp(-np.abs(np.sin((xn * 9.0 - yn * 5.5 + flow * 1.9) * np.pi)) * 5.2)
    edge = np.clip((angle - 0.68) * 3.1, 0, 1)
    color = np.clip(color + magenta_edge[None, None, :] * edge[:, :, None] * 0.34, 0, 1)
    color = np.clip(color + flip_line[:, :, None] * np.array([0.12, 0.03, 0.20], dtype=np.float32), 0, 1)

    micro = _cs_micro((h, w), seed + 1712, 0.014)
    carrier = np.clip(base * 0.16 + color * 0.92 + grain[:, :, None] * 0.035, 0, 1)
    carrier = np.clip(carrier + micro[:, :, None] * np.array([0.16, 0.08, 0.24], dtype=np.float32), 0, 1)

    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + carrier * blend + bb[:, :, None] * 0.16 * blend, 0, 1).astype(np.float32)


def spec_chameleon_dual_shift(shape, seed, sm, base_m, base_r):
    """Dual-Shift spec: smooth flop zones plus fine metallic pigment."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    flow = _cs_norm01(np.sin(x * 0.021 + y * 0.047 + seed * 0.013) + np.cos(x * -0.036 + y * 0.018) * 0.55)
    micro = _cs_micro((h, w), seed + 1712, 0.014)
    flip_line = np.exp(-np.abs(np.sin((xn * 9.0 - yn * 5.5 + flow * 1.9) * np.pi)) * 5.2)
    angle = np.clip(xn * 0.42 + (1.0 - yn) * 0.28 + flow * 0.30, 0, 1)
    M = np.clip(142.0 + angle * 68.0 * sm + flip_line * 34.0 * sm + micro * 42.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(17.0 + (1.0 - angle) * 22.0 * sm + (1.0 - micro) * 14.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + flip_line * 15.0 * sm + micro * 11.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_bifrost_iridescent_v2(paint, shape, mask, seed, pm, bb):
    """Bifrost Crystal: prismatic shard fields with rainbow travel, not soft waves."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    seam, glint, micro, hue = _cs_bifrost_fields((h, w), seed)
    sat = np.clip(0.56 + seam * 0.20 + micro * 0.12, 0, 1)
    val = np.clip(0.38 + seam * 0.18 + glint * 0.12 + micro * 0.10 + bb * 0.10, 0, 1)
    rr, gg, bbv = hsv_to_rgb_vec(hue, sat, val)
    prism = np.stack([rr, gg, bbv], axis=-1).astype(np.float32)
    carrier = np.clip(base * 0.30 + prism * 0.78, 0, 1)
    carrier = np.clip(carrier + seam[:, :, None] * np.array([0.10, 0.12, 0.16], dtype=np.float32), 0, 1)

    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + carrier * blend + bb[:, :, None] * 0.13 * blend, 0, 1).astype(np.float32)


def spec_bifrost_iridescent(shape, seed, sm, base_m, base_r):
    """Bifrost Crystal spec: aligned crystalline seams and prismatic micrograin."""
    h, w = shape[:2] if len(shape) > 2 else shape
    seam, glint, micro, _hue = _cs_bifrost_fields((h, w), seed)
    M = np.clip(116.0 + seam * 58.0 * sm + glint * 38.0 * sm + micro * 32.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(16.0 + (1.0 - seam) * 18.0 * sm + (1.0 - micro) * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + seam * 14.0 * sm + glint * 8.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_opal_v2(paint, shape, mask, seed, pm, bb):
    """
    Dragon's Pearl Scale: iridescent overlapping hexagonal scale pattern
    with pearlescent shimmer at each scale edge. Not a diffraction grating.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Generate hexagonal/fish-scale pattern using Voronoi-like cells
    rng = np.random.RandomState(seed + 1619)
    n_scales = 720  # smaller scales for 2048; owner said the v3 pattern was too large
    # Hexagonal-ish grid with jitter for organic look
    grid_n = int(np.sqrt(n_scales))
    cy_pts = []
    cx_pts = []
    for gy in range(grid_n + 2):
        for gx in range(grid_n + 2):
            base_y = (gy + 0.5) / (grid_n + 1) * h
            base_x = (gx + 0.5 + (gy % 2) * 0.5) / (grid_n + 1) * w
            cy_pts.append(base_y + rng.randn() * h / (grid_n * 3))
            cx_pts.append(base_x + rng.randn() * w / (grid_n * 3))
    pts = np.stack([cy_pts, cx_pts], axis=1)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.stack([yy.ravel(), xx.ravel()], axis=1).astype(np.float64)
    dists, indices = tree.query(coords, k=2)
    labels = indices[:, 0].reshape(h, w)
    d0 = dists[:, 0].reshape(h, w).astype(np.float32)
    d1 = dists[:, 1].reshape(h, w).astype(np.float32)
    cell_scale = np.percentile(d0, 92) + 1e-8

    # Bright seams come from nearest/second-nearest proximity. The old distance
    # field lit cell centers, which read as dots instead of dragon scales.
    seam = np.clip((d1 - d0) / cell_scale, 0, 1)
    edge_glow = np.exp(-(seam * 4.8) ** 2).astype(np.float32)
    scale_interior = np.clip(d0 / cell_scale, 0, 1)

    # Per-scale hue — COHERENT dragon scale gradient (gold → green → teal)
    # Instead of random hue per cell, use spatial position + gentle noise
    # so adjacent scales shift smoothly like real iridescent reptile scales
    n_pts = len(cy_pts)
    pts_arr = np.array(pts)
    # Spatial gradient: diagonal flow from gold (top-left) to teal (bottom-right)
    spatial_t = (pts_arr[:, 0] / (h + 1e-8) * 0.5 +
                 pts_arr[:, 1] / (w + 1e-8) * 0.5)
    spatial_t = np.clip(spatial_t, 0, 1).astype(np.float32)
    # Add per-scale jitter — small, keeping neighbors coherent
    jitter = rng.uniform(-0.14, 0.14, size=n_pts).astype(np.float32)
    scale_t = np.clip(spatial_t + jitter, 0, 1)
    t_map = scale_t[labels]

    # Angle-shift simulation: noise shifts position along the gradient
    angle_noise = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1620)
    shifted_t = np.clip(t_map + angle_noise * 0.18, 0, 1)

    # Dragon scale color palette: warm gold → olive green → emerald → teal
    # 4-stop gradient mapped to t=0..1
    # t=0.0: warm gold     [0.82, 0.65, 0.18]
    # t=0.33: olive-bronze  [0.55, 0.62, 0.15]
    # t=0.66: emerald green [0.12, 0.58, 0.30]
    # t=1.0: deep teal      [0.08, 0.45, 0.42]
    c0 = np.array([0.88, 0.70, 0.20], dtype=np.float32)
    c1 = np.array([0.20, 0.72, 0.42], dtype=np.float32)
    c2 = np.array([0.08, 0.55, 0.82], dtype=np.float32)
    c3 = np.array([0.58, 0.25, 0.82], dtype=np.float32)
    c4 = np.array([0.92, 0.36, 0.64], dtype=np.float32)

    # Piecewise linear interpolation through the 4 stops
    t3 = shifted_t * 4.0  # scale to 0-4 for 4 segments
    seg = np.clip(np.floor(t3).astype(int), 0, 3)
    frac = np.clip(t3 - seg, 0, 1)

    colors_lut = np.stack([c0, c1, c2, c3, c4])  # (5, 3)
    r_ch = colors_lut[seg, 0] * (1 - frac) + colors_lut[np.minimum(seg + 1, 4), 0] * frac
    g_ch = colors_lut[seg, 1] * (1 - frac) + colors_lut[np.minimum(seg + 1, 4), 1] * frac
    b_ch = colors_lut[seg, 2] * (1 - frac) + colors_lut[np.minimum(seg + 1, 4), 2] * frac

    # Pearl shimmer at scale edges — boosted from 0.3 to 0.5 for visible sparkle
    arc = np.exp(-np.abs(np.sin(scale_interior * np.pi * 3.2 + shifted_t * 2.4)) * 5.0)
    edge_shimmer = np.clip(edge_glow * 0.58 + arc * 0.16, 0, 1)
    r_ch = np.clip(r_ch + edge_shimmer * 0.8, 0, 1)
    g_ch = np.clip(g_ch + edge_shimmer * 0.7, 0, 1)
    b_ch = np.clip(b_ch + edge_shimmer * 0.9, 0, 1)

    # Per-scale brightness: gold brighter, teal darker (adds dimension)
    scale_bright = np.clip(1.0 - shifted_t * 0.3, 0.7, 1.0)
    r_ch = np.clip(r_ch * scale_bright, 0, 1)
    g_ch = np.clip(g_ch * scale_bright, 0, 1)
    b_ch = np.clip(b_ch * scale_bright, 0, 1)

    shade = 0.78 + scale_interior * 0.18 + edge_glow * 0.18
    effect = np.stack([r_ch * shade, g_ch * shade, b_ch * shade], axis=2)
    # FIX: stronger scale overlay (was 0.35/0.65 → 0.15/0.85) so dragon scales dominate
    effect = base * 0.15 + effect * 0.85

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_opal(shape, seed, sm, base_m, base_r):
    """
    Dragon's Pearl Scale spec: hexagonal scale pattern with metallic edges (M=200+),
    smooth glossy interior (M=80-120), pearlescent clearcoat variation per scale.

    Uses the SAME Voronoi cell structure as paint_opal_v2 (cKDTree, seed+1619)
    so spec edges align perfectly with paint edges.
    """
    h, w = shape
    rng = np.random.RandomState(seed + 1619)
    n_scales = 720
    grid_n = int(np.sqrt(n_scales))
    cy_pts, cx_pts = [], []
    for gy in range(grid_n + 2):
        for gx in range(grid_n + 2):
            base_y = (gy + 0.5) / (grid_n + 1) * h
            base_x = (gx + 0.5 + (gy % 2) * 0.5) / (grid_n + 1) * w
            cy_pts.append(base_y + rng.randn() * h / (grid_n * 3))
            cx_pts.append(base_x + rng.randn() * w / (grid_n * 3))
    pts = np.stack([cy_pts, cx_pts], axis=1)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.stack([yy.ravel(), xx.ravel()], axis=1).astype(np.float64)
    dists, _indices = tree.query(coords, k=2)
    d0 = dists[:, 0].reshape(h, w).astype(np.float32)
    d1 = dists[:, 1].reshape(h, w).astype(np.float32)
    cell_scale = np.percentile(d0, 92) + 1e-8
    seam = np.clip((d1 - d0) / cell_scale, 0, 1)

    edge_mask = np.exp(-(seam * 4.8) ** 2).astype(np.float32)
    interior_mask = np.clip(d0 / cell_scale, 0, 1)

    # Per-scale clearcoat variation — MARRIED to paint via same rng sequence
    n_pts = len(cy_pts)
    angle_noise = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1620)
    cc_map = np.clip(angle_noise * 0.5 + 0.5, 0, 1).astype(np.float32)

    # M: edges highly metallic (pearl shimmer), interior moderate
    M = np.clip(92.0 + edge_mask * 150.0 * sm + interior_mask * 20.0 * sm, 0, 255).astype(np.float32)

    # R: GLOSSY INTERIORS (low R), rougher edges (higher R) — FIX: was inverted
    R = np.clip(15.0 + edge_mask * 35.0 * sm, 15, 255).astype(np.float32)

    # CC: pearlescent at edges, moderate variation via angle noise
    CC = np.clip(16.0 + edge_mask * 18.0 * sm + cc_map * 10.0 * sm, 16, 255).astype(np.float32)

    return M, R, CC


def paint_opal_v2(paint, shape, mask, seed, pm, bb):
    """Dragon's Pearl Scale: fine micro-scales calibrated for full-car wrap scale."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    edge_glow, scale_arc, mica, shifted_t = _cs_opal_fields((h, w), seed)

    hue = np.mod(0.10 + shifted_t * 0.72 + edge_glow * 0.05 + mica * 0.035, 1.0)
    sat = np.clip(0.55 + edge_glow * 0.18 + mica * 0.10, 0, 1)
    val = np.clip(0.42 + edge_glow * 0.24 + scale_arc * 0.12 + mica * 0.10, 0, 1)
    r_ch, g_ch, b_ch = hsv_to_rgb_vec(hue, sat, val)

    pearl_flash = np.clip(edge_glow * 0.55 + scale_arc * 0.18 + mica * 0.08, 0, 1)
    r_ch = np.clip(r_ch + pearl_flash * 0.36, 0, 1)
    g_ch = np.clip(g_ch + pearl_flash * 0.32, 0, 1)
    b_ch = np.clip(b_ch + pearl_flash * 0.42, 0, 1)

    shade = 0.78 + edge_glow * 0.12 + scale_arc * 0.05
    effect = np.stack([r_ch * shade, g_ch * shade, b_ch * shade], axis=2)
    effect = base * 0.22 + effect * 0.80
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + effect * blend + bb[:, :, None] * 0.24 * blend, 0, 1).astype(np.float32)


def spec_opal(shape, seed, sm, base_m, base_r):
    """Dragon's Pearl Scale spec aligned to the fast micro-scale paint field."""
    h, w = shape
    edge_mask, scale_arc, mica, _shifted_t = _cs_opal_fields((h, w), seed)

    M = np.clip(92.0 + edge_mask * 112.0 * sm + scale_arc * 28.0 * sm + mica * 30.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + edge_mask * 24.0 * sm + (1.0 - mica) * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + edge_mask * 15.0 * sm + scale_arc * 8.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_smoked_v2(paint, shape, mask, seed, pm, bb):
    """
    Smoke tint darkening via Beer-Lambert gray absorption.
    Translucent smoke effect — darkens underlying color uniformly.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 1621)
    
    # Smoke absorption: uniform gray darkening with variation
    smoke_strength = 0.65 + noise * 0.15
    effect = base * (1.0 - smoke_strength[:,:,np.newaxis]) + np.array([0.15, 0.15, 0.15])[np.newaxis, np.newaxis, :] * smoke_strength[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_smoked(shape, seed, sm, base_m, base_r):
    """
    Smoked spec — muted highlight with smoke veil darkening.
    """
    h, w = shape
    # MARRIED to paint_smoked_v2: seed+1621, scales [2,4,8]
    noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 1621)
    # base_m/base_r in 0-255 — smoked = muted, lower metallic
    M = np.full((h, w), base_m * 0.65, dtype=np.float32) + noise * 15.0 * sm
    R = np.full((h, w), max(base_r * 0.5, 15.0), dtype=np.float32) + noise * 12.0 * sm
    CC = np.clip(16.0 + noise * 10.0 * sm, 16, 34).astype(np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            CC)

def paint_spectraflame_v2(paint, shape, mask, seed, pm, bb):
    """
    Sentient Polycarbonate: color-shifting clear optical polymer.
    Shifts hue based on noise topology (simulating viewing angle).
    Like looking through an optical crystal that bends light differently at each point.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Viewing angle topology simulation (noise = surface angle variation)
    topo = _cs_noise((h, w), [7, 15, 31], [0.44, 0.36, 0.20], seed + 1624, cap=512)
    fine = _cs_noise((h, w), [28, 64, 128], [0.42, 0.36, 0.22], seed + 1625, cap=512)
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    ribbon = np.exp(-np.abs(np.sin((xn * 19.0 + yn * 11.0 + topo * 2.7) * np.pi)) * 6.8)
    hair = _cs_norm01(np.sin(x * 0.62 + y * 0.18 + topo * 4.0) + np.sin(x * -0.37 + y * 0.51) * 0.65)
    cells = _cs_micro((h, w), seed + 1626, 0.045)

    # Convert base paint to grayscale luminance for hue-shift reference
    lum = base[:,:,0] * 0.299 + base[:,:,1] * 0.587 + base[:,:,2] * 0.114

    # Hue shift amount driven by noise topology (simulates angle-dependent refraction)
    hue_shift = topo * 0.55 + fine * 0.20 + ribbon * 0.06 + hair * 0.04

    # Apply hue rotation to the base paint color
    # Convert RGB to approximate hue, shift it, convert back
    # Simplified: rotate RGB channels based on topology
    cos_shift = np.cos(hue_shift * np.pi * 2.0)
    sin_shift = np.sin(hue_shift * np.pi * 2.0)

    # Rodrigues hue rotation around (1,1,1) luminance axis — corrected coefficients
    c, s = cos_shift, sin_shift
    r_out = base[:,:,0] * (0.333 + 0.667 * c) + base[:,:,1] * (0.333 - 0.333 * c - 0.577 * s) + base[:,:,2] * (0.333 - 0.333 * c + 0.577 * s)
    g_out = base[:,:,0] * (0.333 - 0.333 * c + 0.577 * s) + base[:,:,1] * (0.333 + 0.667 * c) + base[:,:,2] * (0.333 - 0.333 * c - 0.577 * s)
    b_out = base[:,:,0] * (0.333 - 0.333 * c - 0.577 * s) + base[:,:,1] * (0.333 - 0.333 * c + 0.577 * s) + base[:,:,2] * (0.333 + 0.667 * c)

    # Polycarbonate clear crystal shimmer — boosted from 0.08 to 0.14 for visible sparkle
    crystal_shimmer = np.clip((topo - 0.3) * 2.0, 0, 1) * 0.12 + ribbon * 0.15 + cells * 0.10
    r_out = np.clip(r_out + crystal_shimmer + hair * 0.045, 0, 1)
    g_out = np.clip(g_out + crystal_shimmer * 0.85 + ribbon * 0.05, 0, 1)
    b_out = np.clip(b_out + crystal_shimmer * 1.12 + hair * 0.06, 0, 1)

    flame_hue = np.mod(0.02 + topo * 0.12 + ribbon * 0.06 + hair * 0.04, 1.0)
    flame_sat = np.clip(0.78 + ribbon * 0.12 + cells * 0.08, 0, 1)
    flame_val = np.clip(0.42 + ribbon * 0.22 + hair * 0.12 + cells * 0.12 + bb * 0.10, 0, 1)
    fr, fg, fb = hsv_to_rgb_vec(flame_hue, flame_sat, flame_val)
    flame = np.stack([fr, fg, fb], axis=2).astype(np.float32)
    effect = np.clip(base * 0.12 + np.stack([r_out, g_out, b_out], axis=2) * 0.42 + flame * 0.76, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_spectraflame(shape, seed, sm, base_m, base_r):
    """
    Sentient Polycarbonate spec: glassy low roughness with subtle
    interference-like variation. Clear optical polymer surface.
    """
    h, w = shape
    # MARRIED to paint_spectraflame_v2: seed+1624 [8,16,32], seed+1625 [2,4,8]
    topo = _cs_noise((h, w), [7, 15, 31], [0.44, 0.36, 0.20], seed + 1624, cap=512)
    fine = _cs_noise((h, w), [28, 64, 128], [0.42, 0.36, 0.22], seed + 1625, cap=512)
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    ribbon = np.exp(-np.abs(np.sin((xn * 19.0 + yn * 11.0 + topo * 2.7) * np.pi)) * 6.8)
    cells = _cs_micro((h, w), seed + 1626, 0.045)
    # M: moderate metallic with interference variation
    M = np.clip(118.0 + topo * 58.0 * sm + ribbon * 58.0 * sm + cells * 46.0 * sm, 0, 255).astype(np.float32)
    # R: glassy smooth with ACTUAL variation above GGX floor (was 3-13, all clamped to 15)
    R = np.clip(15.0 + (1.0 - ribbon) * 18.0 * sm + fine * 12.0 * sm, 15, 255).astype(np.float32)
    # CC: optical grade polymer, variation follows topology
    CC = np.clip(16.0 + ribbon * 16.0 * sm + cells * 9.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_tinted_clear_v2(paint, shape, mask, seed, pm, bb):
    """
    Colored clearcoat with uniform Beer-Lambert tint.
    Subtle color shift — nearly transparent with consistent hue.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    depth = multi_scale_noise((h, w), [5, 13, 29], [0.45, 0.35, 0.20], seed + 1629)
    flow = np.sin((xn * 15.0 - yn * 8.0 + depth * 2.4) * np.pi) * 0.5 + 0.5
    meniscus = np.exp(-np.abs(np.sin((xn * 5.0 + yn * 4.0 + depth) * np.pi)) * 5.4)

    amber = np.array([0.96, 0.58, 0.20], dtype=np.float32)
    smoke = np.array([0.18, 0.24, 0.31], dtype=np.float32)
    clear_tint = amber[None, None, :] * (0.62 + flow[:, :, None] * 0.18) + smoke[None, None, :] * (0.20 + depth[:, :, None] * 0.12)
    tint_strength = np.clip(0.32 + depth * 0.16 + meniscus * 0.10, 0, 0.68)
    effect = base * (1.0 - tint_strength[:, :, np.newaxis]) + clear_tint * tint_strength[:, :, np.newaxis]
    effect = np.clip(effect + meniscus[:, :, None] * np.array([0.11, 0.08, 0.04], dtype=np.float32), 0, 1)
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.2 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_tinted_clear(shape, seed, sm, base_m, base_r):
    """
    Tinted clear spec — uniform transparent highlight.
    """
    h, w = shape
    # MARRIED to paint_tinted_clear_v2: seed+1629, scales [1,2,4]
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    noise = multi_scale_noise((h, w), [5, 13, 29], [0.45, 0.35, 0.20], seed + 1629)
    meniscus = np.exp(-np.abs(np.sin((xn * 5.0 + yn * 4.0 + noise) * np.pi)) * 5.4)
    # base_m/base_r in 0-255 — tinted clear preserves most of base
    M = np.full((h, w), base_m * 0.82, dtype=np.float32) + meniscus * 32.0 * sm + noise * 12.0 * sm
    R = np.full((h, w), max(base_r * 0.58, 15.0), dtype=np.float32) + (1.0 - meniscus) * 18.0 * sm
    CC = np.clip(16.0 + meniscus * 16.0 * sm + noise * 5.0 * sm, 16, 40).astype(np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            CC)


def paint_tinted_lacquer_v2(paint, shape, mask, seed, pm, bb):
    """
    Nitrocellulose lacquer with dissolved dye molecules.
    Glossy finish with slight orange-peel texture from drying patterns.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Orange-peel texture pattern
    texture = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 1632)
    
    noise = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 1633)
    
    # Lacquer with dye: deep red with high gloss
    lacquer_dye = np.array([0.75, 0.2, 0.15])
    dye_strength = 0.55 + texture * 0.15
    effect = base * (1.0 - dye_strength[:,:,np.newaxis]) + lacquer_dye[np.newaxis, np.newaxis, :] * dye_strength[:,:,np.newaxis] + noise[:,:,np.newaxis] * 0.08
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.3 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_tinted_lacquer(shape, seed, sm, base_m, base_r):
    """
    Tinted lacquer spec — glossy highlight with orange-peel microtexture.
    """
    h, w = shape
    texture = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.3, 0.3], seed + 1634)
    # base_m/base_r in 0-255 — lacquer = glossy, moderate metallic
    M = np.full((h, w), base_m * 0.85, dtype=np.float32) + texture * 18.0 * sm
    noise_r = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1635)
    R = np.full((h, w), max(base_r * 0.6, 15.0), dtype=np.float32) + noise_r * 15.0 * sm
    CC = np.clip(16.0 + noise_r * 7.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            CC)


def paint_tri_coat_pearl_v2(paint, shape, mask, seed, pm, bb):
    """
    Three-layer pearl with ZONE-WEIGHTED color mixing.
    Each zone has a dominant coat color — not flat averaging.
    FIX: was /3.0 equal blend → now zone-weighted like spec's w1/w2/w3.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Three independent pearl layers — same seeds as spec for marriage
    layer1 = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1636)
    layer2 = multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 1637)
    layer3 = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1638)
    y, x = get_mgrid((h, w))
    platelet = multi_scale_noise((h, w), [2, 4, 8], [0.42, 0.35, 0.23], seed + 1639)
    nacre = np.sin(x * 0.16 + y * 0.052 + layer2 * 3.5) * 0.5 + 0.5
    platelet_flash = np.clip((platelet - 0.08) * 1.8, 0, 1)

    # Normalize to 0-1 range for zone weighting
    l1 = np.clip(layer1 * 0.5 + 0.5, 0.01, 1.0)
    l2 = np.clip(layer2 * 0.5 + 0.5, 0.01, 1.0)
    l3 = np.clip(layer3 * 0.5 + 0.5, 0.01, 1.0)

    # Zone weights — whichever layer is strongest DOMINATES (matches spec's w1/w2/w3)
    total = l1 + l2 + l3 + 1e-8
    w1 = (l1 / total)[:, :, np.newaxis]
    w2 = (l2 / total)[:, :, np.newaxis]
    w3 = (l3 / total)[:, :, np.newaxis]

    color1 = np.array([0.95, 0.4, 0.3])   # Red pearl (coat 1)
    color2 = np.array([0.3, 0.7, 0.95])   # Blue pearl (coat 2)
    color3 = np.array([0.4, 0.95, 0.5])   # Green pearl (coat 3)

    # Zone-weighted mix: dominant coat shows its color clearly
    effect = w1 * color1 + w2 * color2 + w3 * color3
    effect[:, :, 0] = np.clip(effect[:, :, 0] + platelet_flash * 0.130 + nacre * 0.055, 0, 1)
    effect[:, :, 1] = np.clip(effect[:, :, 1] + platelet_flash * 0.104 + (1.0 - nacre) * 0.044, 0, 1)
    effect[:, :, 2] = np.clip(effect[:, :, 2] + platelet_flash * 0.158 + nacre * 0.066, 0, 1)
    effect = np.clip(effect, 0, 1)

    # Stronger overlay — 0.35 base + 0.65 tri-coat (was 0.5/0.5)
    effect = base * 0.35 + effect * 0.65

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.3 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_tri_coat_pearl(shape, seed, sm, base_m, base_r):
    """
    Tri-coat pearl spec: THREE DISTINCT ZONES with different metallic/roughness
    creating visible color-shift regions. Each coat is distinguishable.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_tri_coat_pearl_v2: same seeds AND scales
    layer1 = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 1636)
    layer2 = multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 1637)
    layer3 = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1638)
    platelet = multi_scale_noise((h, w), [2, 4, 8], [0.42, 0.35, 0.23], seed + 1639)
    platelet01 = np.clip((platelet + 1.0) * 0.5, 0, 1)

    # Create three DOMINANT zones (each layer claims territory)
    l1 = np.clip(layer1 * 0.5 + 0.5, 0, 1)
    l2 = np.clip(layer2 * 0.5 + 0.5, 0, 1)
    l3 = np.clip(layer3 * 0.5 + 0.5, 0, 1)

    # Determine which "coat" dominates at each pixel
    total = l1 + l2 + l3 + 1e-8
    w1 = l1 / total  # coat 1 weight
    w2 = l2 / total  # coat 2 weight
    w3 = l3 / total  # coat 3 weight

    # Coat 1: High metallic, very smooth (chrome pearl)
    # Coat 2: Medium metallic, moderate roughness (satin pearl)
    # Coat 3: Low metallic, smooth (gloss pearl)
    M = np.clip((w1 * 210.0 + w2 * 132.0 + w3 * 58.0) * sm + platelet01 * 36.0 * sm + 30.0 * (1.0 - sm), 0, 255).astype(np.float32)
    R = np.clip(w1 * 4.0 + w2 * 23.0 + w3 * 8.0 + 3.0 + (1.0 - platelet01) * 18.0 * sm, 15, 255).astype(np.float32)

    # CC varies by coat zone for visible shift
    CC = np.clip(16.0 + w1 * 5.0 + w2 * 18.0 * sm + w3 * 10.0 * sm + platelet01 * 12.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


# ============================================================================
# CANDY APPLE — Deep crimson Beer-Lambert, shadow-crush absorption
# ============================================================================

def paint_candy_apple_v2(paint, shape, mask, seed, pm, bb):
    """
    Candy apple — deeply saturated crimson candy, Beer-Lambert single-pass.
    High base absorption (0.82+) vs generic candy (0.70+) creates a characteristic
    'shadow crush': mid-tones go almost black, only bright specular zones show vivid
    crimson. Distinct from candy_v2 [0.8,0.1,0.1] (lighter red) and candy_burgundy
    [0.4,0.05,0.08] (wine-brown). Candy apple = near-monochromatic crimson, green+blue
    both suppressed hard.
    WEAK-036 FIX: replaces paint_smoked_darken (15% gray darkener, zero red physics).
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Two-scale noise for organic depth variation
    noise_coarse = multi_scale_noise((h, w), [16, 32], [0.55, 0.45], seed + 1645)
    noise_fine   = multi_scale_noise((h, w), [1, 2], [0.60, 0.40], seed + 1646)

    # Deep crimson — more saturated than generic candy, near-monochromatic red
    candy_color = np.array([0.72, 0.02, 0.02], dtype=np.float32)

    # High base absorption for "shadow crush" — mid-tones crushed toward black
    absorption = np.float32(0.82) + (noise_coarse * np.float32(0.10) + noise_fine * np.float32(0.05))
    absorption = np.clip(absorption, np.float32(0.72), np.float32(0.97))

    effect = (base * (np.float32(1.0) - absorption[:, :, np.newaxis])
              + candy_color[np.newaxis, np.newaxis, :] * absorption[:, :, np.newaxis])

    blend   = np.float32(np.clip(pm, 0.0, 1.0))
    mask_3d = mask[:, :, np.newaxis]
    result  = np.clip(base * (np.float32(1.0) - mask_3d * blend)
                      + effect * (mask_3d * blend), 0, 1)
    # Green + blue suppression in candy zones (short-wavelength absorption)
    result[..., 1] = np.clip(result[..., 1] * (np.float32(1.0) - absorption * np.float32(0.12) * mask), 0, 1)
    result[..., 2] = np.clip(result[..., 2] * (np.float32(1.0) - absorption * np.float32(0.18) * mask), 0, 1)
    # Higher bb boost (0.20) — bright specular pops hard against crushed shadow
    return np.clip(result + bb[:, :, np.newaxis] * np.float32(0.20) * pm * mask_3d, 0, 1).astype(np.float32)


# ============================================================================
# 2026-04-24 regular-base rebuild overrides. These are the canonical active
# definitions imported by the registry; the old jelly-pearl implementation is
# retained above under legacy names so import behavior is explicit.
# ============================================================================

def _cs_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


_CS_FIELD_CACHE = {}


def _cs_cache_put(key, value):
    if len(_CS_FIELD_CACHE) > 128:
        _CS_FIELD_CACHE.clear()
    _CS_FIELD_CACHE[key] = value
    return value


def _cs_noise(shape, scales, weights, seed, cap=1024):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("noise", int(h), int(w), tuple(scales), tuple(weights), int(seed), int(cap))
    cached = _CS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(int(cap), int(h), int(w))
    if work < min(h, w):
        sh = max(8, int(round(h * work / max(h, w))))
        sw = max(8, int(round(w * work / max(h, w))))
        field = multi_scale_noise((sh, sw), scales, weights, seed)
        field = _resize_array(np.asarray(field, dtype=np.float32), h, w)
    else:
        field = multi_scale_noise((h, w), scales, weights, seed)
    return _cs_cache_put(key, np.asarray(field, dtype=np.float32))


def _cs_micro(shape, seed, density):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("micro", int(h), int(w), int(seed), float(density))
    cached = _CS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    rng = np.random.default_rng(seed)
    n = min(int(h * w * density), 160000)
    out = np.zeros((h, w), dtype=np.float32)
    if n > 0:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.20, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    return _cs_cache_put(key, np.maximum.reduce([
        out,
        np.roll(out, 1, axis=0) * 0.40,
        np.roll(out, -1, axis=1) * 0.40,
    ]).astype(np.float32))


def _cs_hash01(a, b, seed):
    return np.mod(np.sin(a * 12.9898 + b * 78.233 + seed * 0.017) * 43758.5453, 1.0).astype(np.float32)


def _cs_bifrost_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("bifrost", int(h), int(w), int(seed))
    cached = _CS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(1024, int(h), int(w))
    sh, sw = h, w
    if work < min(h, w):
        sh = max(256, int(round(h * work / max(h, w))))
        sw = max(256, int(round(w * work / max(h, w))))
    y, x = get_mgrid((sh, sw))
    xn = x / max(sw - 1, 1)
    yn = y / max(sh - 1, 1)
    cell = max(3.0, min(sh, sw) / 150.0)
    warp = _cs_norm01(np.sin(x * 0.033 + y * 0.057 + seed * 0.019) + np.sin(x * -0.021 + y * 0.044) * 0.48)
    gx = np.floor((x + warp * cell * 1.35) / cell).astype(np.float32)
    gy = np.floor((y - warp * cell * 0.85) / cell).astype(np.float32)
    lx = np.mod((x + warp * cell * 1.35) / cell, 1.0).astype(np.float32)
    ly = np.mod((y - warp * cell * 0.85) / cell, 1.0).astype(np.float32)
    h0 = _cs_hash01(gx, gy, seed + 1720)
    h1 = _cs_hash01(gx + 17.0, gy - 11.0, seed + 1720)
    boundary = np.minimum.reduce([lx, 1.0 - lx, ly, 1.0 - ly])
    slash_a = np.abs(lx - ly)
    slash_b = np.abs(lx + ly - 1.0)
    shard = np.minimum(boundary * 1.35, np.where(h1 > 0.5, slash_a, slash_b))
    seam = np.exp(-(shard * 16.0) ** 2).astype(np.float32)
    glint = np.exp(-np.abs(np.sin((x * 0.54 - y * 0.31 + h0 * 4.0) * np.pi)) * 9.5).astype(np.float32)
    micro = _cs_norm01(np.sin(x * 0.83 + y * 0.19 + warp * 2.5) + np.sin(x * -0.41 + y * 0.67) * 0.42)
    hue = np.mod(h0 + xn * 0.16 + yn * 0.10 + warp * 0.07 + seam * 0.04, 1.0).astype(np.float32)
    fields = (seam, glint, micro, hue)
    if (sh, sw) != (h, w):
        fields = tuple(_resize_array(field, h, w).astype(np.float32) for field in fields)
    return _cs_cache_put(key, fields)


def _cs_opal_fields(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = ("opal", int(h), int(w), int(seed))
    cached = _CS_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(1024, int(h), int(w))
    sh, sw = h, w
    if work < min(h, w):
        sh = max(256, int(round(h * work / max(h, w))))
        sw = max(256, int(round(w * work / max(h, w))))
    y, x = get_mgrid((sh, sw))
    xn = x / max(sw - 1, 1)
    yn = y / max(sh - 1, 1)
    cell = max(3.0, min(sh, sw) / 170.0)
    warp = _cs_norm01(np.sin(x * 0.029 + y * 0.052 + seed * 0.017) + np.cos(x * -0.018 + y * 0.041) * 0.50)
    qx = (x + warp * cell * 0.95) / cell
    qy = (y + (0.5 * np.floor(qx)) + warp * cell * 0.55) / (cell * 0.88)
    gx = np.floor(qx).astype(np.float32)
    gy = np.floor(qy).astype(np.float32)
    lx = np.mod(qx, 1.0).astype(np.float32)
    ly = np.mod(qy, 1.0).astype(np.float32)
    h0 = _cs_hash01(gx, gy, seed + 1619)
    h1 = _cs_hash01(gx + 23.0, gy - 19.0, seed + 1619)
    edge = np.minimum.reduce([lx, 1.0 - lx, ly, 1.0 - ly])
    scale_arc = np.exp(-np.abs(np.sin((ly + h1 * 0.22) * np.pi)) * 6.5).astype(np.float32)
    edge_glow = np.exp(-(edge * 18.0) ** 2).astype(np.float32)
    mica = _cs_norm01(np.sin(x * 0.71 + y * 0.23 + h0 * 3.0) + np.sin(x * -0.34 + y * 0.59) * 0.55)
    shifted_t = np.mod(h0 * 0.55 + xn * 0.28 + yn * 0.20 + warp * 0.09 + scale_arc * 0.04, 1.0).astype(np.float32)
    fields = (edge_glow, scale_arc, mica, shifted_t)
    if (sh, sw) != (h, w):
        fields = tuple(_resize_array(field, h, w).astype(np.float32) for field in fields)
    return _cs_cache_put(key, fields)


def paint_jelly_pearl_v2(paint, shape, mask, seed, pm, bb):
    """Transparent jelly pearl with fine colored mica, not a white frosting wash."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    body = _cs_norm01(multi_scale_noise((h, w), [8, 18, 42], [0.40, 0.36, 0.24], seed + 1614))
    angle = _cs_norm01((x / max(w - 1, 1)) * 0.42 + (y / max(h - 1, 1)) * 0.30 + body * 0.32)
    mica = _cs_micro((h, w), seed + 1615, 0.050)
    phase = angle * np.pi * 2.0
    pearl = np.stack([
        0.80 + 0.18 * np.sin(phase),
        0.82 + 0.17 * np.sin(phase + 2.10),
        0.88 + 0.20 * np.sin(phase + 4.20),
    ], axis=-1).astype(np.float32)
    candy_glow = np.stack([
        0.32 + 0.18 * np.sin(phase + 0.6),
        0.42 + 0.20 * np.sin(phase + 2.4),
        0.58 + 0.22 * np.sin(phase + 4.6),
    ], axis=-1).astype(np.float32)
    jelly = np.clip(base * (0.72 + body[:, :, None] * 0.08) + pearl * 0.18 + candy_glow * 0.14, 0, 1)
    jelly = np.clip(jelly + mica[:, :, None] * pearl * 0.25, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1 - blend) + jelly * blend + bb[:, :, None] * 0.18 * blend, 0, 1).astype(np.float32)


def spec_jelly_pearl(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    body = _cs_norm01(multi_scale_noise((h, w), [8, 18, 42], [0.40, 0.36, 0.24], seed + 1614))
    mica = _cs_micro((h, w), seed + 1615, 0.050)
    M = np.clip(86.0 + body * 52.0 * sm + mica * 122.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + (1 - mica) * 22.0 * sm + body * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + mica * 28.0 * sm + body * 12.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_deep_pearl_white_v2(paint, shape, mask, seed, pm, bb):
    """Deep Pearl as white pearl with blue/purple flop, not a dark dirty tri-coat."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    nacre = multi_scale_noise((h, w), [8, 18, 42], [0.45, 0.35, 0.20], seed + 1730)
    platelet = multi_scale_noise((h, w), [24, 64, 128], [0.42, 0.36, 0.22], seed + 1731)
    fine = _cs_micro((h, w), seed + 1732, 0.034)
    angle = np.clip(xn * 0.44 + (1.0 - yn) * 0.24 + nacre * 0.22, 0, 1)
    phase = angle * np.pi * 2.0
    white = np.array([0.88, 0.88, 0.82], dtype=np.float32)
    blue_pearl = np.stack([
        0.66 + 0.10 * np.sin(phase + 0.9),
        0.72 + 0.12 * np.sin(phase + 2.0),
        0.94 + 0.18 * np.sin(phase + 4.2),
    ], axis=-1).astype(np.float32)
    violet = np.array([0.50, 0.30, 0.86], dtype=np.float32)
    flop = np.clip(blue_pearl * 0.68 + violet[None, None, :] * angle[:, :, None] * 0.36, 0, 1)
    glaze = np.clip(white[None, None, :] * 0.72 + flop * 0.42 + platelet[:, :, None] * 0.045, 0, 1)
    glaze = np.clip(glaze + fine[:, :, None] * np.array([0.13, 0.13, 0.20], dtype=np.float32), 0, 1)
    carrier = np.clip(base * 0.10 + glaze * 0.96, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + carrier * blend + bb[:, :, None] * 0.18 * blend, 0, 1).astype(np.float32)


def spec_deep_pearl_white(shape, seed, sm, base_m, base_r):
    """Deep Pearl spec: bright pearl mica, blue/purple flop bands, smooth clear."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    nacre = multi_scale_noise((h, w), [8, 18, 42], [0.45, 0.35, 0.20], seed + 1730)
    platelet = multi_scale_noise((h, w), [24, 64, 128], [0.42, 0.36, 0.22], seed + 1731)
    fine = _cs_micro((h, w), seed + 1732, 0.034)
    angle = np.clip(xn * 0.44 + (1.0 - yn) * 0.24 + nacre * 0.22, 0, 1)
    wave = np.sin((xn * 18.0 + yn * 7.0 + nacre * 2.4) * np.pi) * 0.5 + 0.5
    M = np.clip(92.0 + angle * 44.0 * sm + wave * 38.0 * sm + fine * 58.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(16.0 + (1.0 - wave) * 18.0 * sm + (1.0 - fine) * 10.0 * sm + platelet * 6.0, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + wave * 15.0 * sm + fine * 14.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


# SPB Candy & Pearl owner MIXED 2026-05-26 (Cursor): Hypershift Spectral 360° —
# steeper 6-anchor sweep, higher sat/value, fine crossed spec interference.
def paint_hypershift_spectral_v2(paint, shape, mask, seed, pm, bb):
    """Full-spectrum HyperShift — bold 360° flop with nano-flake pop."""
    blend_strength = float(np.clip(pm, 0.0, 1.0))
    source = paint[:, :, :3] if paint.ndim == 3 and paint.shape[2] > 3 else paint
    if blend_strength <= 0.0:
        return source
    h, w = shape[:2] if len(shape) > 2 else shape
    base = np.asarray(source, dtype=np.float32)
    xn, yn, warp = _candy_hypershift_fields((h, w), seed)
    phase = seed * 0.017
    angle = np.mod(
        xn * 0.62 + yn * 0.31
        + np.sin(xn * 14.0 + yn * 9.0 + phase) * 0.09
        + np.cos(xn * -11.0 + yn * 19.0 + phase * 1.3) * 0.07
        + warp * 0.14,
        1.0,
    ).astype(np.float32)
    idx = (angle * 6.0).astype(np.int32) % 6
    t = np.clip(angle * 6.0 - idx.astype(np.float32), 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)  # smoothstep between anchors
    hue = _CANDY_HYPERSHIFT_ANCHORS[idx] * (1.0 - t) + _CANDY_HYPERSHIFT_ANCHORS[(idx + 1) % 6] * t
    micro = _cs_norm01(
        np.sin(xn * np.float32((w - 1) * 0.95) + yn * np.float32((h - 1) * 0.17) + hue * 6.0)
        + np.sin(xn * np.float32((w - 1) * -0.41) + yn * np.float32((h - 1) * 0.88) + hue * 4.2) * 0.72
    )
    flakes = _cs_micro((h, w), seed + 1781, 0.068)
    band_a = np.exp(-np.abs(np.sin((xn * 88.0 - yn * 54.0 + angle * 7.0) * np.pi)) * 10.5)
    band_b = np.exp(-np.abs(np.sin((xn * -52.0 + yn * 76.0 + warp * 5.5) * np.pi)) * 12.0)
    hue = np.mod(hue + micro * 0.055 + flakes * 0.08 + band_a * 0.04 + band_b * 0.035, 1.0)
    sat = np.clip(0.88 + micro * 0.08 + band_a * 0.06 + flakes * 0.04, 0.75, 1.0)
    val = np.clip(0.58 + band_a * 0.22 + band_b * 0.16 + flakes * 0.18 + micro * 0.06, 0.45, 0.98)
    rr, gg, bbv = hsv_to_rgb_vec(hue, sat, val)
    carrier = np.empty((h, w, 3), dtype=np.float32)
    carrier[:, :, 0] = rr
    carrier[:, :, 1] = gg
    carrier[:, :, 2] = bbv
    np.multiply(carrier, np.float32(0.94), out=carrier)
    carrier += base * np.float32(0.12)
    np.clip(carrier, 0, 1, out=carrier)
    bb_is_zero = np.isscalar(bb) and float(bb) == 0.0
    if blend_strength == 1.0 and float(mask.min()) >= 0.999:
        if bb_is_zero:
            return carrier
        bb = ensure_bb_2d(bb, shape)
        return np.clip(carrier + bb[:, :, None] * np.float32(0.20), 0, 1).astype(np.float32)
    bb = ensure_bb_2d(bb, shape)
    blend = blend_strength * mask[:, :, None]
    return np.clip(base * (1 - blend) + carrier * blend + bb[:, :, None] * 0.20 * blend, 0, 1).astype(np.float32)


def spec_hypershift_spectral(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    phase = seed * 0.017
    wave = (
        np.sin(xn * 16.0 + yn * 5.0 + phase) * 0.36
        + np.sin(xn * -7.0 + yn * 19.0 + phase * 1.7) * 0.28
        + np.cos((xn + yn) * 13.0 + phase * 0.6) * 0.20
    )
    warp = multi_scale_noise((h, w), [6, 14, 34], [0.48, 0.34, 0.18], seed + 1780)
    field = np.mod(xn * 0.54 + yn * 0.28 + wave * 0.075 + warp * 0.055, 1.0).astype(np.float32)
    flakes = _cs_micro((h, w), seed + 1781, 0.052)
    fine_bands = np.exp(-np.abs(np.sin((xn * 46.0 - yn * 31.0 + field * 4.5) * np.pi)) * 8.0)
    M = np.clip(178.0 + fine_bands * 42.0 * sm + flakes * 38.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + (1 - flakes) * 27.0 * sm + (1.0 - fine_bands) * 13.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + flakes * 16.0 * sm + fine_bands * 11.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


# SPB-67 Candy & Pearl truth-standard overrides: name-faithful paint plus
# independent candy/glass M/R/CC behavior. Kept at module tail so registry
# imports resolve these definitions after legacy compatibility functions above.
def paint_candy_apple_v2(paint, shape, mask, seed, pm, bb):
    """Satan's Apple: deep wet crimson candy with shadow crush and buried red flake."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    body, lacquer, flow, pins, edge = _candy_apple_fields((h, w), seed)
    candy_color = np.array([0.70, 0.012, 0.012], dtype=np.float32)
    black_cherry = np.array([0.14, 0.000, 0.018], dtype=np.float32)
    absorption = np.clip(0.78 + body * 0.13 + lacquer * 0.06, 0.70, 0.97)
    effect = base * (1.0 - absorption[:, :, None]) + candy_color[None, None, :] * absorption[:, :, None]
    effect = np.clip(
        effect * (1.0 - body[:, :, None] * 0.15)
        + black_cherry[None, None, :] * (1.0 - lacquer[:, :, None]) * 0.18
        + flow[:, :, None] * np.array([0.15, 0.018, 0.012], dtype=np.float32)
        + edge[:, :, None] * np.array([0.18, 0.020, 0.016], dtype=np.float32)
        + pins[:, :, None] * np.array([0.46, 0.072, 0.044], dtype=np.float32),
        0,
        1,
    )
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + effect * blend + bb[:, :, None] * 0.18 * blend, 0, 1).astype(np.float32)


def spec_candy_apple(shape, seed, sm, base_m, base_r):
    """Satan's Apple spec: wet lacquer sheets, buried crimson flake, satin shadow crush."""
    h, w = shape[:2] if len(shape) > 2 else shape
    body, lacquer, flow, pins, edge = _candy_apple_fields((h, w), seed)
    M = np.clip(base_m * 0.58 + edge * 64.0 * sm + pins * 108.0 * sm + flow * 34.0 * sm - body * 16.0, 0, 255)
    R = np.clip(max(base_r * 0.68, 15.0) + body * 48.0 * sm + (1.0 - lacquer) * 28.0 * sm - pins * 12.0 * sm, 15, 255)
    CC = np.clip(22.0 + lacquer * 62.0 * sm + flow * 64.0 * sm + edge * 44.0 * sm + pins * 24.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_candy_emerald_v2(paint, shape, mask, seed, pm, bb):
    """Radioactive Glass: uranium-green candy glass with bubbles, hot rims, and phosphor flecks."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    body, fine, bubble, glass_edge, phosphor = _candy_emerald_fields((h, w), seed)
    emerald = np.array([0.045, 0.56, 0.28], dtype=np.float32)
    absorption = np.clip(0.68 + body * 0.17 + fine * 0.10, 0.62, 0.95)
    effect = base * (1.0 - absorption[:, :, None]) + emerald[None, None, :] * absorption[:, :, None]
    effect = np.clip(
        effect
        + glass_edge[:, :, None] * np.array([0.12, 0.34, 0.15], dtype=np.float32)
        + bubble[:, :, None] * np.array([0.020, 0.095, 0.070], dtype=np.float32)
        + phosphor[:, :, None] * np.array([0.55, 0.95, 0.20], dtype=np.float32) * 0.42,
        0,
        1,
    )
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + effect * blend + bb[:, :, None] * 0.16 * blend, 0, 1).astype(np.float32)


def spec_candy_emerald(shape, seed, sm, base_m, base_r):
    """Radioactive Glass spec: hot glass rims, bubble roughness, phosphor pin flashes."""
    h, w = shape[:2] if len(shape) > 2 else shape
    body, fine, bubble, glass_edge, phosphor = _candy_emerald_fields((h, w), seed)
    M = np.clip(base_m * 0.56 + glass_edge * 74.0 * sm + phosphor * 84.0 * sm + fine * 18.0 * sm, 0, 255)
    R = np.clip(max(base_r * 0.64, 15.0) + bubble * 42.0 * sm + fine * 24.0 * sm - glass_edge * 12.0 * sm - phosphor * 8.0, 15, 255)
    CC = np.clip(18.0 + body * 42.0 * sm + glass_edge * 58.0 * sm + phosphor * 32.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# SPB-67 Candy & Pearl wave 2: tighten name fidelity and spec-channel life for
# the remaining low-score pearl/glass entries without changing their public IDs.
def paint_deep_pearl_white_v2(paint, shape, mask, seed, pm, bb):
    """Deep Pearl: buried nacre depth, blue/violet flop, and dense mica platelets."""
    source = paint[:, :, :3] if paint.ndim == 3 and paint.shape[2] > 3 else paint
    blend_strength = float(np.clip(pm, 0.0, 1.0))
    if blend_strength <= 0.0:
        return source
    h, w = shape[:2] if len(shape) > 2 else shape
    base = np.asarray(source, dtype=np.float32)
    xn, yn, nacre, _cloud, veil, mica, hair, _edge = _candy_deep_pearl_fields((h, w), seed)

    pearl_white = np.array([0.86, 0.84, 0.76], dtype=np.float32)
    blue_flop = np.array([0.42, 0.62, 0.96], dtype=np.float32)
    violet_flop = np.array([0.62, 0.36, 0.92], dtype=np.float32)
    angle = np.clip(bb * 0.36 + xn * 0.28 + (1.0 - yn) * 0.18 + nacre * 0.22, 0, 1)
    color = pearl_white[None, None, :] * 0.78
    color = np.clip(color + blue_flop[None, None, :] * (1.0 - angle[:, :, None]) * 0.34, 0, 1)
    color = np.clip(color + violet_flop[None, None, :] * angle[:, :, None] * 0.30, 0, 1)
    color = np.clip(
        color
        + veil[:, :, None] * np.array([0.09, 0.12, 0.22], dtype=np.float32)
        + hair[:, :, None] * np.array([0.035, 0.045, 0.070], dtype=np.float32)
        + mica[:, :, None] * np.array([0.18, 0.20, 0.28], dtype=np.float32),
        0,
        1,
    )
    carrier = np.clip(base * 0.12 + color * 0.96, 0, 1)
    bb_is_zero = np.isscalar(bb) and float(bb) == 0.0
    if blend_strength == 1.0 and bb_is_zero and float(mask.min()) >= 0.999:
        return carrier.astype(np.float32, copy=False)
    bb = ensure_bb_2d(bb, shape)
    blend = blend_strength * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + carrier * blend + bb[:, :, None] * 0.16 * blend, 0, 1).astype(np.float32)


def spec_deep_pearl_white(shape, seed, sm, base_m, base_r):
    """Deep Pearl spec: satin nacre valleys, mica flashes, and blue/violet clearcoat depth."""
    h, w = shape[:2] if len(shape) > 2 else shape
    _xn, _yn, nacre, cloud, veil, mica, hair, edge = _candy_deep_pearl_fields((h, w), seed)
    M = np.clip(72.0 + mica * 92.0 * sm + veil * 46.0 * sm + edge * 38.0 * sm, 0, 255)
    R = np.clip(18.0 + (1.0 - veil) * 34.0 * sm + cloud * 20.0 * sm - mica * 8.0 * sm, 15, 255)
    CC = np.clip(24.0 + nacre * 38.0 * sm + veil * 52.0 * sm + hair * 18.0 * sm + mica * 16.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def paint_tinted_clear_v2(paint, shape, mask, seed, pm, bb):
    """Tinted Clear — preserves base hue; adds amber/smoke clearcoat depth only (SPB owner REBUILD 2026-05-27)."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    depth = _candy_norm01(_candy_noise((h, w), [5, 13, 29], [0.45, 0.35, 0.20], seed + 1629, cap=640))
    flow = np.exp(-np.abs(np.sin((xn * 9.0 + yn * 4.0 + depth * 2.5) * np.pi)) * 6.4)
    meniscus = np.clip(_candy_edge01(depth * 0.72 + flow * 0.28) + flow * 0.30, 0, 1)
    pin = _candy_pinfield((h, w), seed + 1630, 0.006)
    amber = np.array([1.00, 0.72, 0.28], dtype=np.float32)
    smoke = np.array([0.22, 0.26, 0.32], dtype=np.float32)
    tint_vec = amber * (0.42 + depth[:, :, None] * 0.18) + smoke * (0.12 + (1.0 - depth[:, :, None]) * 0.10)
    strength = np.clip(0.06 + depth * 0.08 + flow * 0.05 + meniscus * 0.04, 0, 0.28)
    effect = np.clip(base * (1.0 - strength[:, :, None]) + base * tint_vec * strength[:, :, None], 0, 1)
    effect = np.clip(effect + meniscus[:, :, None] * np.array([0.04, 0.03, 0.015], dtype=np.float32) + pin[:, :, None] * 0.04, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + effect * blend + bb[:, :, None] * 0.12 * blend, 0, 1).astype(np.float32)


def spec_tinted_clear(shape, seed, sm, base_m, base_r):
    """Tinted Clear spec: dielectric clearcoat pockets, rough meniscus edges, sparse dust glints."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    depth = _candy_norm01(_candy_noise((h, w), [5, 13, 29], [0.45, 0.35, 0.20], seed + 1629, cap=640))
    flow = np.exp(-np.abs(np.sin((xn * 9.0 + yn * 4.0 + depth * 2.5) * np.pi)) * 6.4)
    meniscus = np.clip(_candy_edge01(depth * 0.72 + flow * 0.28) + flow * 0.30, 0, 1)
    pin = _candy_pinfield((h, w), seed + 1630, 0.006)
    M = np.clip(base_m * 0.18 + meniscus * 22.0 * sm + pin * 34.0 * sm, 0, 255)
    R = np.clip(max(base_r * 0.70, 15.0) + (1.0 - flow) * 28.0 * sm + depth * 16.0 * sm - meniscus * 9.0 * sm, 15, 255)
    CC = np.clip(26.0 + flow * 62.0 * sm + meniscus * 42.0 * sm + pin * 18.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# SPB Candy & Pearl owner REBUILD 2026-05-26 (Cursor): cabochon adularescence —
# deep royal blue rim, sky-blue body, hot white core, peach prismatic flash.
# Owner ref: real moonstone cabochon photo. composite target ≥85 after rebake.
def paint_moonstone_v2(paint, shape, mask, seed, pm, bb):
    """Moonstone cabochon — internal blue adularescence + white core + peach flash."""
    source = paint[:, :, :3] if paint.ndim == 3 and paint.shape[2] > 3 else paint
    blend_strength = float(np.clip(pm, 0.0, 1.0))
    if blend_strength <= 0.0:
        return source
    h, w = shape[:2] if len(shape) > 2 else shape
    base = np.asarray(source, dtype=np.float32)
    _xn, _yn, _r, r_norm, core, wave, moon_noise, mica = _candy_moonstone_fields((h, w), seed)

    billow = _candy_norm01(
        wave * 0.45
        + np.cos(_xn * -9.0 + _yn * 22.0 + seed * 0.003) * 0.35
        + moon_noise * 0.55
    )
    milk = _candy_norm01(_candy_noise((h, w), [4, 8, 16], [0.40, 0.35, 0.25], seed + 1619, cap=640))

    rim = np.clip((r_norm - 0.55) / 0.45, 0.0, 1.0) ** 1.2
    mid = np.clip(1.0 - np.abs(r_norm - 0.38) / 0.38, 0.0, 1.0)

    deep_blue = np.array([0.04, 0.10, 0.48], dtype=np.float32)
    sky_blue = np.array([0.28, 0.52, 0.94], dtype=np.float32)
    white_hot = np.array([0.97, 0.98, 1.00], dtype=np.float32)
    peach = np.array([1.00, 0.62, 0.38], dtype=np.float32)
    gold = np.array([1.00, 0.78, 0.42], dtype=np.float32)

    body = sky_blue[None, None, :] * (1.0 - rim[:, :, None]) + deep_blue[None, None, :] * rim[:, :, None]
    body = np.clip(body + mid[:, :, None] * np.array([0.12, 0.18, 0.22], dtype=np.float32), 0, 1)
    body = np.clip(body + white_hot[None, None, :] * core[:, :, None] * 0.88, 0, 1)
    prismatic = np.clip(core * billow * (0.55 + milk * 0.45), 0, 1)
    body = np.clip(
        body
        + peach[None, None, :] * prismatic[:, :, None] * 0.42
        + gold[None, None, :] * (prismatic ** 1.4)[:, :, None] * 0.22
        + milk[:, :, None] * np.array([0.08, 0.09, 0.14], dtype=np.float32),
        0,
        1,
    )
    body = np.clip(body + mica[:, :, None] * np.array([0.14, 0.16, 0.22], dtype=np.float32), 0, 1)

    carrier = np.clip(base * 0.10 + body * 0.94, 0, 1)
    bb_is_zero = np.isscalar(bb) and float(bb) == 0.0
    if blend_strength == 1.0 and bb_is_zero and float(mask.min()) >= 0.999:
        return carrier.astype(np.float32, copy=False)
    bb = ensure_bb_2d(bb, shape)
    blend = blend_strength * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + carrier * blend + bb[:, :, None] * 0.22 * blend, 0, 1).astype(np.float32)


def spec_moonstone(shape, seed, sm, base_m, base_r):
    """Moonstone spec — adularescent beam, rim satin, core glass + mica glints."""
    h, w = shape[:2] if len(shape) > 2 else shape
    xn, yn, _r, r_norm, core, wave, moon_noise, mica = _candy_moonstone_fields((h, w), seed)
    billow = _candy_norm01(
        wave * 0.45
        + moon_noise * 0.55
    )
    rim = np.clip((r_norm - 0.55) / 0.45, 0.0, 1.0)
    fissure = np.exp(-np.abs(np.sin((xn * 42.0 + yn * 28.0 + billow * 3.5) * np.pi)) * 11.0)
    M = np.clip(38.0 + core * 72.0 * sm + billow * 44.0 * sm + mica * 82.0 * sm + fissure * 58.0 * sm, 0, 255)
    R = np.clip(22.0 + rim * 38.0 * sm + (1.0 - core) * 24.0 * sm - mica * 6.0 * sm, 15, 255)
    CC = np.clip(28.0 + core * 92.0 * sm + billow * 48.0 * sm + fissure * 34.0 * sm + mica * 22.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def spec_hypershift_spectral(shape, seed, sm, base_m, base_r):
    """Hypershift spec — steep spectral hairlines + crossed interference + nano flake."""
    h, w = shape[:2] if len(shape) > 2 else shape
    xn, yn, warp = _candy_hypershift_fields((h, w), seed)
    angle = np.mod(xn * 0.62 + yn * 0.31 + warp * 0.14 + seed * 0.0017, 1.0).astype(np.float32)
    band_a = np.exp(-np.abs(np.sin((xn * 88.0 - yn * 54.0 + angle * 7.0) * np.pi)) * 10.5)
    band_b = np.exp(-np.abs(np.sin((xn * -52.0 + yn * 76.0 + warp * 5.5) * np.pi)) * 12.0)
    cross = np.exp(-np.abs(np.sin((xn * 64.0 + yn * 64.0 + angle * 9.0) * np.pi)) * 9.0)
    flakes = _candy_pinfield((h, w), seed + 1781, 0.038)
    phase_edge = _candy_edge01(angle + warp * 0.42)
    M = np.clip(148.0 + band_a * 68.0 * sm + band_b * 52.0 * sm + cross * 44.0 * sm + flakes * 86.0 * sm + phase_edge * 36.0 * sm, 0, 255)
    R = np.clip(12.0 + (1.0 - band_a) * 28.0 * sm + warp * 18.0 * sm - flakes * 8.0 * sm, 15, 255)
    CC = np.clip(18.0 + angle * 22.0 * sm + band_a * 46.0 * sm + band_b * 34.0 * sm + cross * 28.0 * sm + flakes * 24.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)
