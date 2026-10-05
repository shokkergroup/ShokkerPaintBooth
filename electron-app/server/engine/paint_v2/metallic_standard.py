# -*- coding: utf-8 -*-
"""
METALLIC STANDARD -- 14 bases, each with unique paint_fn + spec_fn
Standard metallic and pearl finishes with distinct flake/pigment physics.

Techniques (all different):
  candy_apple          - Beer-Lambert double-pass candy absorption
  champagne_metallic   - Oriented gold-mica flake with warm bias
  metal_flake_base     - Large aluminum flake Voronoi scatter
  original_metal_flake - 1960s mega-flake prismatic refraction
  champagne_flake      - Gold-coated aluminum flake specular map
  fine_silver_flake    - Micro-diamond particle Mie scattering
  blue_ice_flake       - Frozen crystal dendritic growth pattern
  bronze_flake         - Copper-tin alloy oxidation gradient
  gunmetal_flake       - Chameleon-shift multi-angle interference
  green_flake          - Dichroic glass flake color-split
  fire_flake           - Thermal gradient blackbody emission color
  midnight_pearl       - Deep-base mica with Rayleigh blue scatter
  pearlescent_white    - Multi-mica rainbow interference stack
  pewter               - Tin-lead alloy grain boundary diffusion
"""
from collections import OrderedDict

import numpy as np
import cv2
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d

_SMOOTH_FIELD_CACHE = OrderedDict()
_SMOOTH_FIELD_CACHE_MAX = 48
# SPB paint-finish perf loop tick 2026-05-31 05:08; owner: "Speed is king in this app."
# Exact smooth-field reuse + dead math removal: blue_ice_flake 5270.4->5226.2 ms, bronze_flake 5106.9->5039.6 ms; std drift 0.
# SPB paint-finish perf loop tick 2026-05-31 07:08; owner: "Speed is king in this app."
# Exact full-canvas blend fast paths: metal_flake_base 4797.3->3709.3 ms, midnight_pearl 4099.2->3931.1 ms; paint/spec std drift 0.


def _smooth_field(shape, seed, feature_px):
    h, w = shape[:2] if len(shape) > 2 else shape
    key = (int(h), int(w), int(seed), int(feature_px))
    cached = _SMOOTH_FIELD_CACHE.get(key)
    if cached is not None:
        _SMOOTH_FIELD_CACHE.move_to_end(key)
        return cached
    rng = np.random.RandomState(seed)
    gh = max(3, int(np.ceil(h / max(1, feature_px))))
    gw = max(3, int(np.ceil(w / max(1, feature_px))))
    small = rng.rand(gh, gw).astype(np.float32)
    field = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    sigma = max(1.0, float(feature_px) / 18.0)
    field = cv2.GaussianBlur(field, (0, 0), sigmaX=sigma, sigmaY=sigma)
    span = float(field.max() - field.min())
    if span < 1e-7:
        out = np.full((h, w), 0.5, dtype=np.float32)
    else:
        out = ((field - float(field.min())) / span).astype(np.float32)
    _SMOOTH_FIELD_CACHE[key] = out
    _SMOOTH_FIELD_CACHE.move_to_end(key)
    while len(_SMOOTH_FIELD_CACHE) > _SMOOTH_FIELD_CACHE_MAX:
        _SMOOTH_FIELD_CACHE.popitem(last=False)
    return out


# ==================================================================
# CANDY APPLE - Beer-Lambert double-pass candy absorption
# ==================================================================
def paint_candy_apple_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    depth = _smooth_field((h, w), seed + 701, 128)
    clear = _smooth_field((h, w), seed + 702, 256)
    gloss_band = np.clip(
        0.5
        + 0.5 * np.sin((x / max(w, 1)) * np.pi * 1.15 + clear * 0.35),
        0,
        1,
    ).astype(np.float32)
    # Smooth candy color: wet dark red depth without baked-in block texture.
    effect = np.stack([
        np.clip(0.18 + depth * 0.070 + gloss_band * 0.030, 0, 1),
        np.clip(0.006 + depth * 0.010 + clear * 0.004, 0, 1),
        np.clip(0.004 + depth * 0.007, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.32 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_candy_apple(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    depth = _smooth_field((h, w), seed + 701, 128)
    clear = _smooth_field((h, w), seed + 702, 256)
    M = np.clip(142.0 + depth * 24.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(11.0 + (1.0 - clear) * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(28.0 + clear * 10.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# CHAMPAGNE METALLIC - Oriented gold-mica flake with warm bias
# ==================================================================
def paint_champagne_metallic_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Gold mica flake orientation (spray-aligned)
    orient = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 711)
    spray = np.sin(y * 0.015 + orient * 1.8) * 0.5 + 0.5
    flake_bright = orient * spray
    gray = base.mean(axis=2)
    champagne = np.clip(gray * 0.25 + 0.50, 0, 1)
    effect_r = np.clip(champagne + flake_bright * 0.08 + 0.06, 0, 1)
    effect_g = np.clip(champagne + flake_bright * 0.06 + 0.03, 0, 1)
    effect_b = np.clip(champagne + flake_bright * 0.03 - 0.02, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.38 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_champagne_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    orient = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 711)
    M = np.clip(150.0 + orient * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + orient * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + orient * 5.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# METAL FLAKE BASE - Large aluminum flake Voronoi scatter
# ==================================================================
def paint_metal_flake_base_v2(paint, shape, mask, seed, pm, bb):
    source = paint[:, :, :3] if paint.ndim == 3 and paint.shape[2] > 3 else paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = np.asarray(source, dtype=np.float32)
    blend = float(np.clip(pm, 0.0, 1.0))
    if blend <= 0.0:
        return base.copy()
    rng = np.random.RandomState(seed + 720)
    # Voronoi-like flake centers (sparse large flakes)
    n_flakes = 800
    cy = rng.randint(0, h, n_flakes)
    cx = rng.randint(0, w, n_flakes)
    flake_map = np.zeros((h, w), dtype=np.float32)
    for i in range(n_flakes):
        r = rng.randint(3, 8)
        y0, y1 = max(0, cy[i]-r), min(h, cy[i]+r)
        x0, x1 = max(0, cx[i]-r), min(w, cx[i]+r)
        brightness = rng.rand() * 0.15 + 0.05
        flake_map[y0:y1, x0:x1] += brightness
    flake_map = np.clip(flake_map, 0, 0.2)
    gray = base.mean(axis=2)
    metal = np.clip(gray * 0.3 + 0.45, 0, 1)
    effect = np.clip(np.stack([metal + flake_map]*3, axis=-1), 0, 1).astype(np.float32)
    bb_is_zero = np.isscalar(bb) and float(bb) == 0.0
    if blend == 1.0 and bb_is_zero and float(mask.min()) >= 0.999:
        return effect
    bb = ensure_bb_2d(bb, shape)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base + (effect - base) * (m3 * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.42 * pm * m3, 0, 1).astype(np.float32)

def spec_metal_flake_base(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 720)
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.4, 0.3], seed + 721)
    M = np.clip(190.0 + flake * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + flake * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + flake * 5.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# ORIGINAL METAL FLAKE - 1960s mega-flake prismatic refraction
# ==================================================================
def paint_original_metal_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    flake_coarse = _smooth_field((h, w), seed + 731, 44)
    # Broad vintage flake travel without nearest-neighbor square tiles.
    prism_phase = flake_coarse * np.pi * 2.6
    prism_r = np.clip(0.5 + 0.3 * np.cos(prism_phase), 0, 1)
    prism_g = np.clip(0.5 + 0.3 * np.cos(prism_phase - 2.094), 0, 1)
    prism_b = np.clip(0.5 + 0.3 * np.cos(prism_phase + 2.094), 0, 1)
    flake_mask = np.clip((flake_coarse - 0.50) * 2.2, 0, 1) * 0.08
    gray = base.mean(axis=2)
    metal = np.clip(gray * 0.3 + 0.42, 0, 1)
    effect = np.stack([
        np.clip(metal + flake_mask * prism_r, 0, 1),
        np.clip(metal + flake_mask * prism_g, 0, 1),
        np.clip(metal + flake_mask * prism_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.44 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_original_metal_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = _smooth_field((h, w), seed + 731, 44)
    M = np.clip(198.0 + flake * 34.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + (1.0 - flake) * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + flake * 5.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# CHAMPAGNE FLAKE - Gold-coated aluminum flake specular map
# ==================================================================
def paint_champagne_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Gold-coated flakes: high specular at certain orientations
    flake_orient = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 741)
    specular_hit = np.clip((flake_orient - 0.6) * 5.0, 0, 1) * 0.10
    gold_base = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 742)
    gray = base.mean(axis=2)
    warm = np.clip(gray * 0.2 + 0.52, 0, 1)
    effect = np.stack([
        np.clip(warm + gold_base * 0.04 + specular_hit + 0.05, 0, 1),
        np.clip(warm + gold_base * 0.03 + specular_hit * 0.8 + 0.02, 0, 1),
        np.clip(warm + gold_base * 0.01 + specular_hit * 0.3 - 0.03, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.38 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_champagne_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 741)
    M = np.clip(165.0 + flake * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(7.0 + flake * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + flake * 5.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FINE SILVER FLAKE - Micro-diamond particle Mie scattering
# ==================================================================
def paint_fine_silver_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Mie scattering: particle size ~ wavelength, creates forward scatter halo
    particle = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 751)
    # Mie efficiency: peaks when size ~ wavelength, oscillates
    mie_q = 2.0 + 1.5 * np.cos(particle * 12.0)  # oscillating scatter efficiency
    scatter_intensity = np.clip(mie_q / 4.0, 0, 1) * 0.08
    # Silver base
    gray = base.mean(axis=2)
    silver = np.clip(gray * 0.2 + 0.58, 0, 1)
    effect = np.stack([
        np.clip(silver + scatter_intensity, 0, 1),
        np.clip(silver + scatter_intensity, 0, 1),
        np.clip(silver + scatter_intensity + 0.01, 0, 1)  # slight cool bias
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.40 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_fine_silver_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    particle = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 751)
    M = np.clip(185.0 + particle * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(4.0 + particle * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + particle * 5.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# BLUE ICE FLAKE - Frozen crystal dendritic growth pattern
# ==================================================================
def paint_blue_ice_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Dendritic crystal growth: 6-fold symmetry (ice crystal)
    angle = np.arctan2(y - h/2, x - w/2)
    hex_sym = np.cos(6.0 * angle) * 0.5 + 0.5  # 6-fold
    crystal = _smooth_field((h, w), seed + 761, 88)
    dendrite = hex_sym * crystal * 0.028
    # Ice blue base
    ice_r = 0.52 + crystal * 0.04
    ice_g = 0.62 + crystal * 0.05
    ice_b = 0.78 + crystal * 0.06
    # Flake sparkle
    shimmer = _smooth_field((h, w), seed + 762, 34)
    sparkle = np.clip((shimmer - 0.68) * 3.5, 0, 1) * 0.030
    effect = np.stack([
        np.clip(ice_r + dendrite + sparkle, 0, 1),
        np.clip(ice_g + dendrite + sparkle, 0, 1),
        np.clip(ice_b + dendrite + sparkle * 1.5, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.36 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_blue_ice_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    crystal = _smooth_field((h, w), seed + 761, 88)
    M = np.clip(142.0 + crystal * 36.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + crystal * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + crystal * 5.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# BRONZE FLAKE - Copper-tin alloy oxidation gradient
# ==================================================================
def paint_bronze_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    alloy_ratio = _smooth_field((h, w), seed + 771, 96)
    oxide = _smooth_field((h, w), seed + 772, 180)
    oxide_depth = np.clip(oxide, 0, 1) * 0.035
    bronze_r = 0.55 + alloy_ratio * 0.12 - oxide_depth
    bronze_g = 0.38 + alloy_ratio * 0.06 - oxide_depth * 0.8
    bronze_b = 0.15 + alloy_ratio * 0.03 + oxide_depth * 0.3  # patina green-blue
    flake = _smooth_field((h, w), seed + 773, 42)
    sparkle = flake * 0.025
    effect = np.stack([
        np.clip(bronze_r + sparkle, 0, 1),
        np.clip(bronze_g + sparkle * 0.7, 0, 1),
        np.clip(bronze_b + sparkle * 0.3, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.36 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_bronze_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    alloy = _smooth_field((h, w), seed + 771, 96)
    oxide = _smooth_field((h, w), seed + 772, 180)
    M = np.clip(160.0 + alloy * 36.0 * sm - oxide * 18.0, 0, 255).astype(np.float32)
    R = np.clip(10.0 + oxide * 16.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + (1.0 - oxide) * 6.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# GUNMETAL FLAKE - Chameleon-shift multi-angle interference
# ==================================================================
def paint_gunmetal_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    angle_map = _smooth_field((h, w), seed + 781, 86)
    phase = angle_map * np.pi * 2.0
    shift_r = 0.25 + 0.06 * np.cos(phase)
    shift_g = 0.27 + 0.06 * np.cos(phase - 2.094)
    shift_b = 0.30 + 0.06 * np.cos(phase + 2.094)
    flake = _smooth_field((h, w), seed + 782, 40)
    sparkle = flake * 0.018
    effect = np.stack([
        np.clip(shift_r + sparkle, 0, 1),
        np.clip(shift_g + sparkle, 0, 1),
        np.clip(shift_b + sparkle, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_gunmetal_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    angle = _smooth_field((h, w), seed + 781, 86)
    M = np.clip(145.0 + angle * 38.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + angle * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + angle * 5.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# GREEN FLAKE - Dichroic glass flake color-split
# ==================================================================
def paint_green_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    glow = _smooth_field((h, w), seed + 791, 116)
    depth = _smooth_field((h, w), seed + 792, 220)
    shoulder = np.clip(0.5 + 0.5 * np.sin((y / max(h, 1)) * np.pi * 0.9 + depth * 0.35), 0, 1)
    # Clean neon-green metallic base; no visible square/shard texture in the paint layer.
    effect = np.empty_like(base, dtype=np.float32)
    effect[:, :, 0] = np.clip(0.030 + depth * 0.040 + shoulder * 0.020, 0, 1)
    effect[:, :, 1] = np.clip(0.330 + glow * 0.185 + shoulder * 0.060, 0, 1)
    effect[:, :, 2] = np.clip(0.028 + depth * 0.030, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    # SPB paint-finish perf loop tick 2026-05-31 10:23; owner: "Speed is king in this app."
    # Same blend math with fewer full-canvas temporaries: green_flake 5166.9 -> 4752.8 ms; paint/spec std drift 0.
    result = np.clip(base + (effect - base) * (m3 * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.30 * pm * m3, 0, 1).astype(np.float32)

def spec_green_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    glow = _smooth_field((h, w), seed + 791, 116)
    depth = _smooth_field((h, w), seed + 792, 220)
    M = np.clip(142.0 + glow * 32.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(12.0 + depth * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(18.0 + glow * 8.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FIRE FLAKE - Thermal gradient blackbody emission color
# ==================================================================
def paint_fire_flake_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    temp_map = _smooth_field((h, w), seed + 801, 78)
    temp = np.clip(temp_map, 0, 1)  # 0=cool ember, 1=hot flame
    # Simplified Planck: R peaks first, G follows, B last
    fire_r = np.clip(0.6 + temp * 0.38, 0, 1)
    fire_g = np.clip(temp * 0.55 - 0.05, 0, 1)
    fire_b = np.clip(temp * 0.15 - 0.08, 0, 1)
    ember_field = _smooth_field((h, w), seed + 802, 36)
    ember = np.clip((ember_field - 0.70) * 3.6, 0, 1) * 0.036
    effect = np.stack([
        np.clip(fire_r + ember, 0, 1),
        np.clip(fire_g + ember * 0.6, 0, 1),
        np.clip(fire_b + ember * 0.2, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.40 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_fire_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    temp = _smooth_field((h, w), seed + 801, 78)
    M = np.clip(140.0 + temp * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + temp * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + temp * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# MIDNIGHT PEARL - Deep-base mica with Rayleigh blue scatter
# ==================================================================
def paint_midnight_pearl_v2(paint, shape, mask, seed, pm, bb):
    source = paint[:, :, :3] if paint.ndim == 3 and paint.shape[2] > 3 else paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = np.asarray(source, dtype=np.float32)
    blend = float(np.clip(pm, 0.0, 1.0))
    if blend <= 0.0:
        return base.copy()
    y, x = get_mgrid((h, w))
    depth = _smooth_field((h, w), seed + 811, 150)
    mica = _smooth_field((h, w), seed + 812, 52)
    fine = _smooth_field((h, w), seed + 813, 18)
    travel = np.sin((x * 0.010) + (y * 0.006) + mica * 3.4).astype(np.float32)
    pearl = np.clip((mica - 0.42) * 2.4, 0, 1) * (0.55 + fine * 0.45)
    violet = np.clip((travel + 1.0) * 0.5, 0, 1)
    # Deep black pearl: still dark, but with readable blue/violet/teal mica travel.
    dark = 0.026 + depth * 0.018
    scatter_r = pearl * (0.010 + violet * 0.020)
    scatter_g = pearl * (0.014 + (1.0 - violet) * 0.016)
    scatter_b = pearl * (0.040 + fine * 0.018)
    effect = np.stack([
        np.clip(dark + scatter_r, 0, 1),
        np.clip(dark + scatter_g, 0, 1),
        np.clip(dark + scatter_b, 0, 1)
    ], axis=-1).astype(np.float32)
    bb_is_zero = np.isscalar(bb) and float(bb) == 0.0
    if blend == 1.0 and bb_is_zero and float(mask.min()) >= 0.999:
        return effect
    bb = ensure_bb_2d(bb, shape)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base + (effect - base) * (m3 * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.25 * pm * m3, 0, 1).astype(np.float32)

def spec_midnight_pearl(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    mica = _smooth_field((h, w), seed + 812, 52)
    fine = _smooth_field((h, w), seed + 813, 18)
    pearl = np.clip((mica - 0.40) * 2.2, 0, 1)
    M = np.clip(62.0 + pearl * 54.0 * sm + fine * 12.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + (1.0 - pearl) * 8.0 * sm + fine * 4.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + pearl * 7.0 + fine * 3.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PEARLESCENT WHITE - Multi-mica rainbow interference stack
# ==================================================================
def paint_pearlescent_white_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Multi-mica layers: each mica type has different thickness -> different color
    mica1 = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 821)
    mica2 = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 822)
    mica3 = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 823)
    # Each mica shifts a different color channel
    rainbow_r = mica1 * 0.04
    rainbow_g = mica2 * 0.04
    rainbow_b = mica3 * 0.04
    # Bright white base
    gray = base.mean(axis=2)
    white = np.clip(gray * 0.1 + 0.85, 0, 1)
    effect = np.stack([
        np.clip(white + rainbow_r, 0, 1),
        np.clip(white + rainbow_g, 0, 1),
        np.clip(white + rainbow_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pearlescent_white(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    mica = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 821)
    M = np.clip(85.0 + mica * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + mica * 7.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + mica * 5.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PEWTER - Tin-lead alloy grain boundary diffusion
# ==================================================================
def paint_pewter_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Grain boundaries: Voronoi-approximated crystal grains
    # Grain interiors are smooth, boundaries are darker (diffusion channels)
    grain = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 831)
    # Grain boundary detection via gradient magnitude
    gy = np.gradient(grain, axis=0)
    gx = np.gradient(grain, axis=1)
    boundary = np.sqrt(gy**2 + gx**2)
    boundary = np.clip(boundary / (boundary.max() + 1e-8), 0, 1)
    # Pewter color: muted warm grey
    gray = base.mean(axis=2)
    pewter_base = np.clip(gray * 0.2 + 0.42, 0, 1)
    # Boundaries darken, interiors have subtle color travel
    color_travel = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 832)
    effect_r = np.clip(pewter_base - boundary * 0.04 + color_travel * 0.015, 0, 1)
    effect_g = np.clip(pewter_base - boundary * 0.04 + color_travel * 0.010, 0, 1)
    effect_b = np.clip(pewter_base - boundary * 0.04 + color_travel * 0.005, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.32 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pewter(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    grain = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 831)
    gy = np.gradient(grain, axis=0)
    gx = np.gradient(grain, axis=1)
    boundary = np.sqrt(gy**2 + gx**2)
    boundary = np.clip(boundary / (boundary.max() + 1e-8), 0, 1)
    # Pewter: moderate metallic, boundaries rougher
    M = np.clip(120.0 + grain * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(14.0 + boundary * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + (1.0 - boundary) * 6.0, 16, 255).astype(np.float32)
    return M, R, CC
