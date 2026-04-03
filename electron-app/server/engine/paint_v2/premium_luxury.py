# -*- coding: utf-8 -*-
"""
PREMIUM LUXURY -- 9 bases, each with unique paint_fn + spec_fn
Each models a specific luxury automotive paint technology.

Techniques (all different):
  bentley_silver    - Metallic flake orientation mapping (directional sparkle)
  bugatti_blue      - Multi-coat depth with color-shifting interference
  ferrari_rosso     - Triple-layer candy: base + pigment + clearcoat depth
  koenigsegg_clear  - Naked carbon visible through tinted clear layer
  lamborghini_verde - Pearlescent flip: angle-dependent color shift green->gold
  maybach_two_tone  - Horizontal split with gradient blend zone
  mclaren_orange    - Fluorescent pigment glow simulation
  pagani_tricolore  - Three-zone vertical color fade
  porsche_pts       - Paint-to-sample precision color matching (ultra-flat)
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# ==================================================================
# BENTLEY SILVER - Directional metallic flake orientation
# Bentley's signature silver has large oriented flakes that create
# a directional sparkle. Flakes align with spray direction causing
# brightness to shift based on viewing angle.
# ==================================================================

def paint_bentley_silver_v2(paint, shape, mask, seed, pm, bb):
    """Bentley signature silver with directional metallic flake orientation sparkle."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 400)
    base = paint.copy()
    # Oriented flake map — spray direction creates preferred flake alignment
    flake_orient = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 401)
    # Large flake sparkle (coarser noise = bigger flakes)
    flake_large = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 402)
    # Spray direction gradient (vertical = spray gun passes)
    y, x = get_mgrid((h, w))
    spray_dir = np.sin(y * 0.02 + flake_orient * 2.0) * 0.5 + 0.5

    # Silver metallic base
    gray = base.mean(axis=2, keepdims=True)
    silver = np.clip(gray * 0.3 + 0.55, 0, 1)
    # Directional sparkle from oriented flakes
    sparkle = flake_orient * spray_dir * flake_large
    effect = np.clip(silver + sparkle[:,:,np.newaxis] * 0.12, 0, 1)
    # Slight warm silver (Bentley's signature)
    effect = np.concatenate([
        np.clip(effect[:,:,0:1] + 0.02, 0, 1),
        effect[:,:,1:2],
        np.clip(effect[:,:,2:3] - 0.01, 0, 1)
    ], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.28 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_bentley_silver(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 401)
    M = np.clip(180.0 + flake * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + flake * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + flake * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# BUGATTI BLUE - Multi-coat depth with color-shifting interference
# Bugatti's deep blue uses 5+ coats creating visible depth. Light
# bounces between layers creating subtle interference shifts.
# ==================================================================

def paint_bugatti_blue_v2(paint, shape, mask, seed, pm, bb):
    """Bugatti deep blue multi-coat with 5-layer color-shifting interference depth."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Multi-coat depth — each layer slightly modifies the color
    depth_var = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 410)
    n_coats = 5
    coat_accum_r, coat_accum_g, coat_accum_b = 0.0, 0.0, 0.0
    for i in range(n_coats):
        layer = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 410 + i)
        # Each coat shifts color slightly (interference)
        coat_accum_r += layer * 0.02 * (i % 2)
        coat_accum_g += layer * 0.01 * ((i + 1) % 3)
        coat_accum_b += layer * 0.15 / n_coats  # blue dominant

    # Deep Bugatti blue
    gray = base.mean(axis=2, keepdims=True)
    effect_r = np.clip(gray[:,:,0] * 0.05 + coat_accum_r + 0.02, 0, 1)
    effect_g = np.clip(gray[:,:,0] * 0.08 + coat_accum_g + 0.05, 0, 1)
    effect_b = np.clip(gray[:,:,0] * 0.2 + coat_accum_b + 0.35, 0, 1)
    # Depth variation
    depth_mod = 0.85 + depth_var * 0.15
    effect = np.stack([effect_r * depth_mod, effect_g * depth_mod, effect_b * depth_mod], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_bugatti_blue(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    depth = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 410)
    M = np.clip(60.0 + depth * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + depth * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + depth * 6.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FERRARI ROSSO - Triple-layer candy coat
# Real candy paint: reflective base -> translucent pigment mid-coat
# -> thick clearcoat. Light passes through pigment twice (in + out)
# creating depth-dependent color saturation via Beer-Lambert law.
# ==================================================================

def paint_ferrari_rosso_v2(paint, shape, mask, seed, pm, bb):
    """Ferrari Rosso triple-layer candy: Beer-Lambert absorption through translucent pigment."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 420)

    # Layer 1: Reflective metallic base (silver-aluminum)
    base_reflect = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.4, 0.3], seed + 421)
    # Layer 2: Translucent red pigment — Beer-Lambert absorption
    # Absorption coefficient varies spatially (pigment density variation)
    pigment_density = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 422)
    pigment_thick = 0.8 + pigment_density * 0.4  # thickness variation
    # Beer-Lambert: I = I0 * exp(-alpha * d) — double-pass through pigment
    alpha_r, alpha_g, alpha_b = 0.15, 2.8, 3.2  # red passes, green/blue absorbed
    transmit_r = np.exp(-alpha_r * pigment_thick * 2.0)
    transmit_g = np.exp(-alpha_g * pigment_thick * 2.0)
    transmit_b = np.exp(-alpha_b * pigment_thick * 2.0)

    # Reflected light colored by double-pass through pigment
    reflect = 0.7 + base_reflect * 0.3  # metallic base reflectance
    effect_r = np.clip(reflect * transmit_r, 0, 1)
    effect_g = np.clip(reflect * transmit_g, 0, 1)
    effect_b = np.clip(reflect * transmit_b, 0, 1)
    # Layer 3: Clearcoat adds gloss sheen on highlights
    clear_sheen = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 423)
    effect_r = np.clip(effect_r + clear_sheen * 0.04, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_ferrari_rosso(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    pigment = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 422)
    # Candy coat: moderate metallic from base layer, very low roughness from clearcoat
    M = np.clip(120.0 + pigment * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(4.0 + pigment * 8.0 * sm, 15, 255).astype(np.float32)  # GGX floor — MiMo audit catch
    # Thick clearcoat
    CC = np.clip(22.0 + pigment * 8.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# KOENIGSEGG CLEAR - Naked carbon through tinted clearcoat
# The famous Koenigsegg clearcoat carbon — visible weave pattern
# underneath a tinted amber/smoke clear layer. The clear layer uses
# Beer-Lambert tinting while the carbon weave is a 2x2 twill
# generated mathematically (not borrowed from carbon_composite).
# ==================================================================

def paint_koenigsegg_clear_v2(paint, shape, mask, seed, pm, bb):
    """Koenigsegg naked carbon under amber-tinted clearcoat via Beer-Lambert tinting."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Carbon weave — diamond twill via modular arithmetic on pixel coords
    # Different from carbon_composite: uses diamond pattern not standard 2x2
    cell = 18  # pixels per tow
    row_phase = (y / cell).astype(int) % 4
    col_phase = (x / cell).astype(int) % 4
    # Diamond twill: warp-over when (row+col)%4 < 2
    warp_over = ((row_phase + col_phase) % 4 < 2).astype(np.float32)
    # Tow edge darkening (borders between tows)
    tow_edge_y = np.abs(np.mod(y, cell) - cell * 0.5) / (cell * 0.5)
    tow_edge_x = np.abs(np.mod(x, cell) - cell * 0.5) / (cell * 0.5)
    tow_shade = 1.0 - np.maximum(tow_edge_y, tow_edge_x) * 0.35

    # Carbon base color: dark gray with weave pattern
    carbon_lum = 0.08 + warp_over * 0.07  # warp vs weft brightness
    carbon_lum *= tow_shade
    # Sub-tow fiber noise for realism
    fiber = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 431)
    carbon_lum += fiber * 0.015

    # Tinted clearcoat — Beer-Lambert amber/smoke tint
    clear_tint_r = np.exp(-0.3 * 1.0)   # barely absorbs red
    clear_tint_g = np.exp(-0.7 * 1.0)   # moderate green absorption
    clear_tint_b = np.exp(-1.6 * 1.0)   # heavy blue absorption -> amber tint
    effect_r = np.clip(carbon_lum * clear_tint_r + 0.03, 0, 1)
    effect_g = np.clip(carbon_lum * clear_tint_g + 0.01, 0, 1)
    effect_b = np.clip(carbon_lum * clear_tint_b, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_koenigsegg_clear(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    cell = 18
    row_p = (y / cell).astype(int) % 4
    col_p = (x / cell).astype(int) % 4
    weave = ((row_p + col_p) % 4 < 2).astype(np.float32)
    # Carbon under clearcoat: low metallic, low roughness (glossy clear)
    M = np.clip(15.0 + weave * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + weave * 6.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + weave * 4.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# LAMBORGHINI VERDE - Pearlescent color flip (green->gold)
# Thin-film interference on mica flakes creates angle-dependent
# color shift. Uses optical path difference (OPD) formula:
# OPD = 2*n*d*cos(theta) where theta varies with surface normal.
# Different from chrome thin-film: uses mica substrate + 2 colors.
# ==================================================================

def paint_lamborghini_verde_v2(paint, shape, mask, seed, pm, bb):
    """Lamborghini Verde pearlescent flip: thin-film OPD interference green-to-gold shift."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Surface normal variation (simulates curved body panels)
    normal_map = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 441)
    # Pseudo viewing angle from surface normal
    cos_theta = np.clip(0.3 + normal_map * 0.7, 0.01, 1.0)
    # Thin-film OPD on mica flakes: OPD = 2 * n * d * cos(theta)
    n_film = 1.58  # mica refractive index
    d_film = 0.45  # film thickness in wavelength units (tuned for green->gold)
    opd = 2.0 * n_film * d_film * cos_theta

    # Interference produces color shift: green at face-on, gold at oblique
    # Phase determines which wavelength constructively interferes
    phase = opd * 2.0 * np.pi
    # Green channel dominant at low angles, red rises at oblique angles
    green_strength = np.clip(0.5 + 0.4 * np.cos(phase), 0, 1)
    gold_shift = np.clip(0.5 + 0.4 * np.cos(phase - 1.2), 0, 1)

    # Mica flake sparkle (fine oriented flakes)
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 442)
    sparkle = np.clip(flake * 0.08, 0, 0.1)

    effect_r = np.clip(gold_shift * 0.45 + sparkle + 0.08, 0, 1)
    effect_g = np.clip(green_strength * 0.55 + sparkle + 0.20, 0, 1)
    effect_b = np.clip(0.04 + sparkle * 0.5, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_lamborghini_verde(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    normal = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 441)
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 442)
    # Pearl: moderate metallic from mica, very smooth clearcoat
    M = np.clip(100.0 + flake * 80.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + normal * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(18.0 + normal * 6.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# MAYBACH TWO-TONE - Horizontal split with gradient blend zone
# Maybach's signature two-tone: dark upper, lighter lower body with
# a precise coachline divider. Uses sigmoid blend for the transition
# zone and separate noise textures per zone for realism.
# ==================================================================

def paint_maybach_two_tone_v2(paint, shape, mask, seed, pm, bb):
    """Maybach two-tone horizontal split with sigmoid coachline blend zone."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Coachline position — slightly above center with gentle waviness
    wave = multi_scale_noise((h, w), [128, 256], [0.6, 0.4], seed + 451)
    split_y = 0.48 + wave * 0.015  # subtle waviness in the divider line
    # Sigmoid blend zone (sharp but smooth transition)
    y_norm = y / max(h - 1, 1)
    blend_zone = 1.0 / (1.0 + np.exp(-80.0 * (y_norm - split_y)))  # steep sigmoid

    # Upper zone: deep dark paint (near-black with warm undertone)
    upper_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 452)
    upper_r = 0.06 + upper_noise * 0.02
    upper_g = 0.05 + upper_noise * 0.015
    upper_b = 0.055 + upper_noise * 0.018

    # Lower zone: champagne/silver metallic
    lower_noise = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.35, 0.35], seed + 453)
    lower_r = 0.62 + lower_noise * 0.06
    lower_g = 0.58 + lower_noise * 0.05
    lower_b = 0.52 + lower_noise * 0.04

    # Blend upper and lower using sigmoid
    effect_r = np.clip(upper_r * (1.0 - blend_zone) + lower_r * blend_zone, 0, 1)
    effect_g = np.clip(upper_g * (1.0 - blend_zone) + lower_g * blend_zone, 0, 1)
    effect_b = np.clip(upper_b * (1.0 - blend_zone) + lower_b * blend_zone, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend_pm = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend_pm) + effect * (mask[:,:,np.newaxis] * blend_pm), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_maybach_two_tone(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    y_norm = y / max(h - 1, 1)
    # Upper = glossy non-metallic, lower = metallic
    split = 1.0 / (1.0 + np.exp(-80.0 * (y_norm - 0.48)))
    upper_m, lower_m = 10.0, 160.0
    upper_r, lower_r = 4.0, 10.0
    M = np.clip(upper_m * (1.0 - split) + lower_m * split * sm + (1.0 - sm) * 30.0, 0, 255).astype(np.float32)
    R = np.clip(upper_r * (1.0 - split) + lower_r * split * sm, 15, 255).astype(np.float32)
    CC = np.clip(18.0 + split * 4.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# MCLAREN ORANGE - Fluorescent pigment glow simulation
# McLaren's Papaya Spark uses fluorescent pigments that absorb UV
# and re-emit visible orange. This creates an apparent glow where
# the paint looks brighter than incident light alone. Modeled as
# local energy gain: output > input in orange wavelengths.
# ==================================================================

def paint_mclaren_orange_v2(paint, shape, mask, seed, pm, bb):
    """McLaren Papaya Spark fluorescent pigment with UV re-emission glow simulation."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Fluorescent pigment density variation
    pigment_var = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 461)
    # UV absorption map (varies with surface orientation)
    uv_absorb = multi_scale_noise((h, w), [32, 64, 128], [0.35, 0.35, 0.3], seed + 462)

    # Base orange from pigment
    base_orange_r = 0.92 + pigment_var * 0.06
    base_orange_g = 0.40 + pigment_var * 0.08
    base_orange_b = 0.02 + pigment_var * 0.02

    # Fluorescent glow — energy gain from UV re-emission
    # Stokes shift: absorbed UV re-emitted as orange (lower energy)
    glow_intensity = np.clip(uv_absorb * 0.12, 0, 0.15)
    glow_r = glow_intensity * 1.0   # full red emission
    glow_g = glow_intensity * 0.35  # partial green emission
    glow_b = glow_intensity * 0.02  # negligible blue

    # Fine metallic flake in the paint (McLaren adds metallic to the orange)
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 463)
    flake_boost = flake * 0.04

    effect_r = np.clip(base_orange_r + glow_r + flake_boost, 0, 1)
    effect_g = np.clip(base_orange_g + glow_g + flake_boost * 0.5, 0, 1)
    effect_b = np.clip(base_orange_b + glow_b, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_mclaren_orange(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 463)
    uv = multi_scale_noise((h, w), [32, 64, 128], [0.35, 0.35, 0.3], seed + 462)
    # Metallic flake in orange + glossy clearcoat
    M = np.clip(90.0 + flake * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + uv * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + uv * 6.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PAGANI TRICOLORE - Three-zone vertical color fade
# Pagani's bespoke tricolore uses three distinct color zones that
# fade into each other vertically. Uses smoothstep interpolation
# (Hermite polynomial) for seamless zone transitions.
# ==================================================================

def paint_pagani_tricolore_v2(paint, shape, mask, seed, pm, bb):
    """Pagani tricolore three-zone vertical fade with smoothstep Hermite transitions."""
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Noise-driven surface angle simulation (replaces hard stripe boundaries)
    angle_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 471)
    fine_noise = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 472)

    # Surface angle parameter: combines position + noise for angle-resolved shift
    # This simulates how real tricolore paint shifts color based on viewing angle
    y_norm = y / max(h - 1, 1)
    angle_param = np.clip(y_norm * 0.6 + angle_noise * 0.25 + fine_noise * 0.15, 0, 1)

    # Smoothstep for soft transitions
    def smoothstep(edge0, edge1, val):
        t = np.clip((val - edge0) / (edge1 - edge0 + 1e-8), 0, 1)
        return t * t * (3.0 - 2.0 * t)

    # Three premium colors with SOFT noise-driven transitions
    # Deep wine red
    c1 = np.array([0.38, 0.04, 0.08], dtype=np.float32)
    # Champagne gold
    c2 = np.array([0.78, 0.68, 0.42], dtype=np.float32)
    # Midnight blue
    c3 = np.array([0.06, 0.08, 0.22], dtype=np.float32)

    # Noise-warped transition zones (wide soft blending, not hard stripes)
    t1 = smoothstep(0.15, 0.42, angle_param)  # wine -> gold
    t2 = smoothstep(0.55, 0.82, angle_param)  # gold -> blue

    # Three-way blend
    effect_r = c1[0] * (1.0 - t1) + c2[0] * (t1 * (1.0 - t2)) + c3[0] * t2
    effect_g = c1[1] * (1.0 - t1) + c2[1] * (t1 * (1.0 - t2)) + c3[1] * t2
    effect_b = c1[2] * (1.0 - t1) + c2[2] * (t1 * (1.0 - t2)) + c3[2] * t2

    # Pearl shimmer in transition zones (where two colors meet)
    transition_intensity = t1 * (1.0 - t1) + t2 * (1.0 - t2)
    pearl = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 473)
    shimmer = transition_intensity * pearl * 0.12

    effect = np.stack([
        np.clip(effect_r + shimmer * 0.8, 0, 1),
        np.clip(effect_g + shimmer * 0.6, 0, 1),
        np.clip(effect_b + shimmer * 0.4, 0, 1)
    ], axis=-1).astype(np.float32)

    blend_pm = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend_pm) + effect * (mask[:,:,np.newaxis] * blend_pm), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pagani_tricolore(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    y_norm = y / max(h - 1, 1)
    # Noise-based angle simulation for spec variation
    angle_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 471)
    fine = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 474)
    angle_param = np.clip(y_norm * 0.6 + angle_noise * 0.25 + fine * 0.15, 0, 1)

    def smoothstep(edge0, edge1, val):
        t = np.clip((val - edge0) / (edge1 - edge0 + 1e-8), 0, 1)
        return t * t * (3.0 - 2.0 * t)

    t1 = smoothstep(0.15, 0.42, angle_param)
    t2 = smoothstep(0.55, 0.82, angle_param)
    # Wine zone: low M (dielectric), Gold zone: high M (metallic), Blue zone: medium M
    M = np.clip((30.0 * (1.0 - t1) + 200.0 * t1 * (1.0 - t2) + 80.0 * t2) * sm + 20.0 * (1.0 - sm), 0, 255).astype(np.float32)
    # Low roughness across all zones (premium gloss), slight variation
    R = np.clip(4.0 + t1 * 5.0 * sm + fine * 3.0 * sm, 15, 255).astype(np.float32)  # GGX floor — MiMo audit catch
    # CC: glossy everywhere, slight variation at transitions
    transition_boost = (t1 * (1.0 - t1) + t2 * (1.0 - t2)) * 2.0
    CC = np.clip(16.0 + transition_boost * 8.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PORSCHE PTS - Paint-to-Sample precision color match (ultra-flat)
# Porsche PTS is about color accuracy, not effects. The paint is
# exceptionally uniform — no flake, no pearl, no texture variation.
# Modeled as ultra-low-variance solid with only micro-orange-peel
# texture from the clearcoat application process.
# ==================================================================

def paint_porsche_pts_v2(paint, shape, mask, seed, pm, bb):
    """Porsche Paint-to-Sample ultra-flat precision color with micro orange-peel texture."""
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # PTS: preserve the exact input color, just make it ultra-uniform
    # Extract dominant color from paint within mask
    gray = base.mean(axis=2)

    # Micro orange-peel texture from clearcoat (very subtle, high frequency)
    peel = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 481)
    peel_amplitude = 0.008  # barely visible — PTS is about perfection

    # Clearcoat flow marks (ultra-subtle, large scale)
    flow = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 482)
    flow_amplitude = 0.004  # nearly invisible

    # The effect is the base paint with micro-variation removed then
    # only the tiniest physical texture added back
    # Flatten color variation: push toward per-channel mean
    ch_mean_r = np.mean(base[:,:,0])
    ch_mean_g = np.mean(base[:,:,1])
    ch_mean_b = np.mean(base[:,:,2])
    # Blend 90% toward mean (ultra-uniform) + tiny physical texture
    flat_r = ch_mean_r * 0.9 + base[:,:,0] * 0.1 + peel * peel_amplitude + flow * flow_amplitude
    flat_g = ch_mean_g * 0.9 + base[:,:,1] * 0.1 + peel * peel_amplitude + flow * flow_amplitude
    flat_b = ch_mean_b * 0.9 + base[:,:,2] * 0.1 + peel * peel_amplitude + flow * flow_amplitude
    effect = np.stack([
        np.clip(flat_r, 0, 1),
        np.clip(flat_g, 0, 1),
        np.clip(flat_b, 0, 1)
    ], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_porsche_pts(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    peel = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 481)
    # PTS: zero metallic (solid color), extremely low roughness (mirror clearcoat)
    # Only micro-variation from orange peel
    M = np.clip(3.0 + peel * 4.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(3.0 + peel * 5.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + peel * 3.0, 0, 255).astype(np.float32)
    return M, R, CC
