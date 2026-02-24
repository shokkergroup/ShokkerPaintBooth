"""
Shokker 24K Arsenal Expansion Module
=====================================
155 Bases x 155 Patterns + 155 Specials = 24,180 Finish Combinations

This module defines all NEW paint/texture/spec functions and registry entries
for the 24K Arsenal expansion. Imported by shokker_engine_v2.py.

Factory functions generate parametric variants to avoid code explosion.
"""

import numpy as np
from PIL import Image


# ================================================================
# FACTORY HELPERS — Generate paint/texture/spec functions from params
# ================================================================


# No-op paint function for bases that don't modify paint
def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint

def _get_mgrid(shape):
    """Coordinate grid helper (same as engine's get_mgrid)."""
    return np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)

def _multi_scale_noise(shape, scales, weights, seed):
    """Multi-octave Perlin-like noise (same algo as engine)."""
    h, w = shape
    result = np.zeros((h, w), dtype=np.float32)
    rng = np.random.RandomState(seed)
    for scale, weight in zip(scales, weights):
        sh, sw = max(1, h // scale), max(1, w // scale)
        small = rng.randn(sh, sw).astype(np.float32)
        img = Image.fromarray(((small - small.min()) / (small.max() - small.min() + 1e-8) * 255).clip(0, 255).astype(np.uint8))
        img = img.resize((w, h), Image.BILINEAR)
        arr = np.array(img).astype(np.float32) / 255.0
        arr = arr * (small.max() - small.min()) + small.min()
        result += arr * weight
    return result


# ================================================================
# BASE PAINT FUNCTION FACTORIES
# ================================================================

def make_chrome_tint_fn(r_bias, g_bias, b_bias, blend=0.18):
    """Factory: chrome with color tint (blue chrome, red chrome, black chrome, etc.)"""
    def fn(paint, shape, mask, seed, pm, bb):
        b = blend * pm
        paint[:,:,0] = paint[:,:,0] * (1 - mask * b) + r_bias * mask * b
        paint[:,:,1] = paint[:,:,1] * (1 - mask * b) + g_bias * mask * b
        paint[:,:,2] = paint[:,:,2] * (1 - mask * b) + b_bias * mask * b
        reflection = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 150)
        paint = np.clip(paint + reflection[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_candy_tint_fn(warmth=0.0):
    """Factory: candy coat — deep transparent tint with sparkle. warmth: -1=cool, 0=neutral, 1=warm"""
    def fn(paint, shape, mask, seed, pm, bb):
        # Candy deepens saturation and adds fine sparkle
        gray = paint.mean(axis=2, keepdims=True)
        sat_boost = 0.15 * pm
        paint = np.clip(paint + (paint - gray) * sat_boost * mask[:,:,np.newaxis], 0, 1)
        # Warm/cool shift
        if warmth > 0:
            paint[:,:,0] = np.clip(paint[:,:,0] + 0.03 * warmth * pm * mask, 0, 1)
            paint[:,:,2] = np.clip(paint[:,:,2] - 0.02 * warmth * pm * mask, 0, 1)
        elif warmth < 0:
            paint[:,:,2] = np.clip(paint[:,:,2] + 0.03 * abs(warmth) * pm * mask, 0, 1)
            paint[:,:,0] = np.clip(paint[:,:,0] - 0.02 * abs(warmth) * pm * mask, 0, 1)
        # Fine sparkle
        rng = np.random.RandomState(seed + 77)
        sparkle = rng.random(shape).astype(np.float32)
        sparkle = np.where(sparkle > 0.96, sparkle * 0.08 * pm, 0)
        paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.06):
    """Factory: luxury fine sparkle with subtle depth."""
    def fn(paint, shape, mask, seed, pm, bb):
        flake = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 50)
        rng = np.random.RandomState(seed + 77)
        sparkle = rng.random(shape).astype(np.float32)
        sparkle = np.where(sparkle > sparkle_density, sparkle * sparkle_strength * pm, 0)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.03 * pm * mask + sparkle * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_tactical_variant_fn(noise_strength=0.03):
    """Factory: flat tactical/military coating with micro-texture."""
    def fn(paint, shape, mask, seed, pm, bb):
        noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 200)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + noise * noise_strength * pm * mask, 0, 1)
        return paint
    return fn

def make_wrap_texture_fn(grain_strength=0.04):
    """Factory: vinyl wrap micro-texture — slight orange-peel or grain."""
    def fn(paint, shape, mask, seed, pm, bb):
        grain = _multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + 300)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + grain * grain_strength * pm * mask, 0, 1)
        return paint
    return fn

def make_aged_fn(fade_strength=0.08, roughen=0.04):
    """Factory: aged/weathered paint — desaturation + noise."""
    def fn(paint, shape, mask, seed, pm, bb):
        gray = paint.mean(axis=2, keepdims=True)
        desat = fade_strength * pm
        paint = paint * (1 - desat * mask[:,:,np.newaxis]) + gray * desat * mask[:,:,np.newaxis]
        noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 400)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + noise * roughen * pm * mask, 0, 1)
        return paint
    return fn

def make_vivid_depth_fn(sat_boost=0.12, depth_darken=0.05):
    """Factory: vivid deep coat — saturates + deepens for luxury colors."""
    def fn(paint, shape, mask, seed, pm, bb):
        gray = paint.mean(axis=2, keepdims=True)
        boost = sat_boost * pm
        paint = np.clip(paint + (paint - gray) * boost * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint - depth_darken * pm * mask[:,:,np.newaxis], 0, 1)
        flake = _multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 50)
        paint = np.clip(paint + flake[:,:,np.newaxis] * 0.02 * pm * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_glow_fn(glow_color, glow_strength=0.06):
    """Factory: subtle glow/luminescence tint."""
    def fn(paint, shape, mask, seed, pm, bb):
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + glow_color[c] * glow_strength * pm * mask, 0, 1)
        noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 600)
        paint = np.clip(paint + noise[:,:,np.newaxis] * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_metallic_tint_fn(r_shift=0, g_shift=0, b_shift=0, flake_str=0.05):
    """Factory: metallic with color tint bias."""
    def fn(paint, shape, mask, seed, pm, bb):
        for c in range(3):
            flake = _multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17)
            paint[:,:,c] = np.clip(paint[:,:,c] + flake * flake_str * pm * mask, 0, 1)
        shifts = [r_shift, g_shift, b_shift]
        for c in range(3):
            if shifts[c] != 0:
                paint[:,:,c] = np.clip(paint[:,:,c] + shifts[c] * 0.04 * pm * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

# ================================================================
# CONCRETE NEW BASE PAINT FUNCTIONS (using factories + unique ones)
# ================================================================

# --- Chrome Tints ---
paint_black_chrome_tint = make_chrome_tint_fn(0.15, 0.15, 0.15, blend=0.25)
paint_blue_chrome_tint = make_chrome_tint_fn(0.60, 0.70, 0.95, blend=0.18)
paint_red_chrome_tint = make_chrome_tint_fn(0.95, 0.25, 0.20, blend=0.18)
paint_antique_patina = make_aged_fn(fade_strength=0.12, roughen=0.06)

# --- Candy Variants ---
paint_candy_depth = make_candy_tint_fn(warmth=0.0)
paint_candy_warm = make_candy_tint_fn(warmth=0.8)
paint_candy_cool = make_candy_tint_fn(warmth=-0.8)

# --- Pearl / Sparkle Variants ---
paint_dark_sparkle = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.04)
paint_warm_shimmer = make_luxury_sparkle_fn(sparkle_density=0.96, sparkle_strength=0.05)
paint_tri_coat_sparkle = make_luxury_sparkle_fn(sparkle_density=0.95, sparkle_strength=0.07)
paint_dealer_sparkle = make_luxury_sparkle_fn(sparkle_density=0.96, sparkle_strength=0.06)
paint_luxury_sparkle = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)
paint_confetti_sparkle = make_luxury_sparkle_fn(sparkle_density=0.93, sparkle_strength=0.10)
paint_crystal_sparkle = make_luxury_sparkle_fn(sparkle_density=0.98, sparkle_strength=0.04)

# --- Wrap Variants ---
paint_wrap_texture = make_wrap_texture_fn(grain_strength=0.04)
paint_textured_wrap = make_wrap_texture_fn(grain_strength=0.07)
paint_brushed_wrap = make_wrap_texture_fn(grain_strength=0.05)
paint_chrome_wrap = make_chrome_tint_fn(0.88, 0.88, 0.90, blend=0.20)
paint_stealth_flat = make_tactical_variant_fn(noise_strength=0.02)

# --- Tactical / Military ---
paint_armor_grain = make_tactical_variant_fn(noise_strength=0.05)
paint_rubber_texture = make_wrap_texture_fn(grain_strength=0.06)
paint_naval_coat = make_tactical_variant_fn(noise_strength=0.04)

# --- Ceramic / Glass ---
paint_porcelain_smooth = make_luxury_sparkle_fn(sparkle_density=0.99, sparkle_strength=0.02)
paint_obsidian_depth = make_vivid_depth_fn(sat_boost=0.05, depth_darken=0.08)
paint_glass_clean = make_luxury_sparkle_fn(sparkle_density=0.99, sparkle_strength=0.01)
paint_ceramic_flat = make_tactical_variant_fn(noise_strength=0.02)
paint_enamel_coat = make_luxury_sparkle_fn(sparkle_density=0.98, sparkle_strength=0.03)

# --- Racing Heritage ---
paint_show_polish = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)
paint_dirt_subtle = make_aged_fn(fade_strength=0.04, roughen=0.03)
paint_barn_aged = make_aged_fn(fade_strength=0.20, roughen=0.08)
paint_rat_rod_flat = make_aged_fn(fade_strength=0.15, roughen=0.10)
paint_pace_car_sheen = make_luxury_sparkle_fn(sparkle_density=0.96, sparkle_strength=0.06)
paint_pit_grime = make_aged_fn(fade_strength=0.06, roughen=0.05)
paint_asphalt_rough = make_tactical_variant_fn(noise_strength=0.07)
paint_checker_polish = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)

# --- Exotic Metal ---
paint_liquid_metal_flow = make_chrome_tint_fn(0.85, 0.85, 0.88, blend=0.22)
paint_dense_metal = make_metallic_tint_fn(r_shift=-0.3, g_shift=-0.3, b_shift=-0.2, flake_str=0.04)
paint_platinum_sheen = make_chrome_tint_fn(0.92, 0.92, 0.95, blend=0.20)
paint_cobalt_tint = make_metallic_tint_fn(r_shift=-0.3, g_shift=-0.1, b_shift=0.4, flake_str=0.04)

# --- Weathered & Aged ---
paint_sun_fade = make_aged_fn(fade_strength=0.25, roughen=0.06)
paint_salt_damage = make_aged_fn(fade_strength=0.15, roughen=0.08)
paint_desert_sand = make_aged_fn(fade_strength=0.10, roughen=0.07)
paint_acid_etch_base = make_aged_fn(fade_strength=0.12, roughen=0.09)
paint_heavy_patina = make_aged_fn(fade_strength=0.18, roughen=0.07)
paint_vintage_haze = make_aged_fn(fade_strength=0.10, roughen=0.04)

# --- OEM Automotive ---
paint_oem_metallic = make_metallic_tint_fn(flake_str=0.04)
paint_fire_engine_gloss = make_vivid_depth_fn(sat_boost=0.10, depth_darken=0.03)
paint_reflective_coat = make_luxury_sparkle_fn(sparkle_density=0.95, sparkle_strength=0.08)

# --- Carbon & Composite ---
paint_carbon_weave_base = make_wrap_texture_fn(grain_strength=0.05)
paint_kevlar_weave = make_wrap_texture_fn(grain_strength=0.04)
paint_fiberglass_gel = make_luxury_sparkle_fn(sparkle_density=0.98, sparkle_strength=0.03)
paint_carbon_ceramic_coat = make_wrap_texture_fn(grain_strength=0.03)
paint_aramid_weave = make_wrap_texture_fn(grain_strength=0.04)
paint_graphene_sheen = make_chrome_tint_fn(0.75, 0.75, 0.80, blend=0.15)
paint_forged_composite_base = make_wrap_texture_fn(grain_strength=0.06)
paint_hybrid_weave_base = make_wrap_texture_fn(grain_strength=0.05)

# --- Premium Luxury ---
paint_rosso_depth = make_vivid_depth_fn(sat_boost=0.15, depth_darken=0.06)
paint_lambo_green = make_vivid_depth_fn(sat_boost=0.18, depth_darken=0.04)
paint_pts_depth = make_vivid_depth_fn(sat_boost=0.14, depth_darken=0.05)
paint_mclaren_vivid = make_vivid_depth_fn(sat_boost=0.20, depth_darken=0.03)
paint_bugatti_depth = make_vivid_depth_fn(sat_boost=0.16, depth_darken=0.07)
paint_pagani_shift = make_luxury_sparkle_fn(sparkle_density=0.95, sparkle_strength=0.07)
paint_two_tone_split = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)

# --- Unique paint functions that need custom logic ---

def paint_moonstone_glow(paint, shape, mask, seed, pm, bb):
    """Soft translucent milky shimmer — pushes toward pale white with fine glow."""
    gray = paint.mean(axis=2, keepdims=True)
    # Push toward milky white
    white_blend = 0.12 * pm
    paint = paint * (1 - white_blend * mask[:,:,np.newaxis]) + 0.90 * white_blend * mask[:,:,np.newaxis]
    # Soft internal glow noise
    glow = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 700)
    paint = np.clip(paint + glow[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_opal_shift(paint, shape, mask, seed, pm, bb):
    """Fire opal — multi-color depth with internal color play."""
    h, w = shape
    # Per-channel noise for color play
    for c in range(3):
        noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 800 + c * 31)
        paint[:,:,c] = np.clip(paint[:,:,c] + noise * 0.06 * pm * mask, 0, 1)
    # Fine sparkle
    rng = np.random.RandomState(seed + 850)
    sparkle = rng.random(shape).astype(np.float32)
    sparkle = np.where(sparkle > 0.96, sparkle * 0.08 * pm, 0)
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_color_flip(paint, shape, mask, seed, pm, bb):
    """Wrap film color-flip — angle-dependent color shift simulation."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # Simulate angle with gradient
    angle_map = (x / max(w, 1) + y / max(h, 1)) * 0.5
    angle_noise = _multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 900)
    angle_map = np.clip(angle_map + angle_noise * 0.15, 0, 1)
    # Shift hue based on position
    for c in range(3):
        shift = np.sin(angle_map * np.pi * 2 + c * 2.094) * 0.06 * pm
        paint[:,:,c] = np.clip(paint[:,:,c] + shift * mask, 0, 1)
    return paint

def paint_mud_splatter(paint, shape, mask, seed, pm, bb):
    """Rally mud splatter — random mud-colored splats over paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 950)
    mud = np.zeros((h, w), dtype=np.float32)
    # Generate splatter spots
    num_splats = int(80 * pm)
    for _ in range(num_splats):
        cy, cx = rng.randint(0, h), rng.randint(0, w)
        radius = rng.randint(10, 60)
        y, x = _get_mgrid(shape)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2)
        splat = np.clip(1.0 - dist / radius, 0, 1) ** 2
        mud = np.maximum(mud, splat * rng.uniform(0.3, 1.0))
    mud = np.clip(mud, 0, 1)
    # Mud color: brownish desaturation
    mud_color = np.array([0.25, 0.20, 0.12])
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mud * 0.15 * pm * mask) + mud_color[c] * mud * 0.15 * pm * mask
    return paint

def paint_heat_wrap_tint(paint, shape, mask, seed, pm, bb):
    """Heat shield — metallic with heat-blue tint zones."""
    # Base chrome brighten
    blend = 0.15 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend) + 0.85 * mask * blend
    # Heat zones — blue-gold gradient
    heat = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1000)
    heat = np.clip(heat * 0.5 + 0.5, 0, 1)
    # Blue in cool zones, gold in hot zones
    paint[:,:,0] = np.clip(paint[:,:,0] + heat * 0.04 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + (1 - heat) * 0.02 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + (1 - heat) * 0.05 * pm * mask, 0, 1)
    return paint

def paint_naked_carbon(paint, shape, mask, seed, pm, bb):
    """Clear coat over visible carbon — Koenigsegg style."""
    h, w = shape
    y, x = _get_mgrid(shape)
    weave_size = 6
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x.astype(int) // weave_size + y.astype(int) // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Darken to show carbon weave through clear
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - cf * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- SHOKK Series Base Paint Functions ---

def paint_pulse_electric(paint, shape, mask, seed, pm, bb):
    """SHOKK Pulse — HIGH VOLTAGE electric storm with crackling arcs and plasma glow."""
    h, w = shape[:2] if len(shape) > 1 else shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed + 1100)

    # Layer 1: Base metallic with strong blue-white energy tint
    blend = 0.25 * pm
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + 0.55 * mask * blend
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + 0.70 * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + 0.95 * mask * blend

    # Layer 2: Multi-frequency electric wave interference
    wave1 = np.sin(y * 0.06 + x * 0.015) * 0.5 + 0.5
    wave2 = np.sin(y * 0.12 - x * 0.03 + 1.2) * 0.5 + 0.5
    wave3 = np.sin((y + x) * 0.04) * 0.5 + 0.5
    pulse = (wave1 * 0.4 + wave2 * 0.35 + wave3 * 0.25)
    pulse_noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1101)
    pulse_noise = (pulse_noise - pulse_noise.min()) / (pulse_noise.max() - pulse_noise.min() + 1e-8)
    pulse = np.clip(pulse + pulse_noise * 0.3, 0, 1)

    # Layer 3: Bright electric arc lines (thresholded peaks = visible arcs)
    arc_lines = np.where(pulse > 0.75, ((pulse - 0.75) / 0.25) ** 0.5, 0).astype(np.float32)
    arc_strength = 0.30 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + arc_lines * arc_strength * 0.6 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + arc_lines * arc_strength * 0.8 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + arc_lines * arc_strength * 1.0 * mask, 0, 1)

    # Layer 4: Random spark hotspots
    sparks = rng.random(shape).astype(np.float32)
    spark_pop = np.where(sparks > 0.985, 0.25 * pm, 0.0)
    paint = np.clip(paint + spark_pop[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    # Layer 5: Dark veins between arcs for contrast
    dark_veins = np.where(pulse < 0.25, (0.25 - pulse) * 0.20 * pm, 0).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - dark_veins * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_venom_acid(paint, shape, mask, seed, pm, bb):
    """SHOKK Venom — TOXIC acid reactive with corrosive drip pools and neon glow."""
    h, w = shape[:2] if len(shape) > 1 else shape
    rng = np.random.RandomState(seed + 1200)

    # Layer 1: Aggressive toxic green-yellow base tint
    blend = 0.22 * pm
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + 0.45 * mask * blend  # yellow-green
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + 0.90 * mask * blend  # strong green
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + 0.15 * mask * blend  # suppress blue

    # Layer 2: Acid bubble noise — multi-scale with visible pooling
    noise1 = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1201)
    noise1 = (noise1 - noise1.min()) / (noise1.max() - noise1.min() + 1e-8)
    noise2 = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1202)
    noise2 = (noise2 - noise2.min()) / (noise2.max() - noise2.min() + 1e-8)

    # Layer 3: Acid pools (bright neon green hotspots)
    acid_pools = np.clip((noise2 - 0.45) * 3.0, 0, 1)
    pool_glow = acid_pools * 0.25 * pm
    paint[:,:,1] = np.clip(paint[:,:,1] + pool_glow * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + pool_glow * 0.5 * mask, 0, 1)

    # Layer 4: Dark corrosion veins between pools
    corrosion = np.clip((0.3 - noise2) * 4.0, 0, 1) * 0.25 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - corrosion * mask, 0, 1)

    # Layer 5: Fine toxic sparkle (acid mist droplets)
    sparkle = rng.random(shape).astype(np.float32)
    toxic_spark = np.where(sparkle > 0.97, 0.18 * pm, 0.0)
    paint[:,:,1] = np.clip(paint[:,:,1] + toxic_spark * mask, 0, 1)

    # Layer 6: Surface texture grain
    grain = (noise1 - 0.5) * 0.12 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + grain * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blood_red_deep(paint, shape, mask, seed, pm, bb):
    """SHOKK Blood — ARTERIAL crimson with pulsing vein networks and wet blood sheen."""
    h, w = shape[:2] if len(shape) > 1 else shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed + 1300)

    # Layer 1: Deep arterial red base — saturate hard into crimson
    blend = 0.30 * pm
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + 0.75 * mask * blend  # strong red
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + 0.08 * mask * blend  # kill green
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + 0.05 * mask * blend  # kill blue

    # Layer 2: Vein network — noise-based branching dark veins
    vein_noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1301)
    vein_noise = (vein_noise - vein_noise.min()) / (vein_noise.max() - vein_noise.min() + 1e-8)
    veins = np.clip(1.0 - np.abs(vein_noise - 0.5) * 5.0, 0, 1)  # thin lines at 0.5 threshold
    vein_darken = veins * 0.30 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - vein_darken * mask, 0, 1)

    # Layer 3: Blood pooling — large-scale dark accumulation zones
    pool_noise = _multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 1302)
    pool_noise = (pool_noise - pool_noise.min()) / (pool_noise.max() - pool_noise.min() + 1e-8)
    pools = np.clip((pool_noise - 0.55) * 3.0, 0, 1)
    pool_bright = pools * 0.20 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + pool_bright * mask, 0, 1)  # brighter red in pools

    # Layer 4: Wet sheen highlights — scattered bright spots like fresh blood
    sparkle = rng.random(shape).astype(np.float32)
    wet_sheen = np.where(sparkle > 0.975, 0.20 * pm, 0.0)
    paint[:,:,0] = np.clip(paint[:,:,0] + wet_sheen * 0.8 * mask, 0, 1)
    paint = np.clip(paint + wet_sheen[:,:,np.newaxis] * 0.15 * mask[:,:,np.newaxis], 0, 1)

    # Layer 5: Overall darkening at edges for depth
    edge_noise = _multi_scale_noise(shape, [8, 16], [0.4, 0.6], seed + 1303)
    edge_noise = (edge_noise - edge_noise.min()) / (edge_noise.max() - edge_noise.min() + 1e-8)
    edge_dark = np.clip((0.35 - edge_noise) * 3, 0, 1) * 0.15 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - edge_dark * mask, 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_void_absorb(paint, shape, mask, seed, pm, bb):
    """SHOKK Void — LIGHT-EATING vantablack with electric edge corona and depth trap."""
    h, w = shape[:2] if len(shape) > 1 else shape
    rng = np.random.RandomState(seed + 1400)

    # Layer 1: AGGRESSIVE darkening — near total light absorption
    darken = 0.85 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - darken * mask), 0, 1)

    # Layer 2: Void depth noise — subtle darkness variation within the void
    depth_noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1401)
    depth_noise = (depth_noise - depth_noise.min()) / (depth_noise.max() - depth_noise.min() + 1e-8)
    extra_dark = depth_noise * 0.10 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - extra_dark * mask, 0, 1)

    # Layer 3: Electric edge corona — bright shimmer at boundaries
    edge_noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1402)
    edge_noise = (edge_noise - edge_noise.min()) / (edge_noise.max() - edge_noise.min() + 1e-8)
    corona = np.where(edge_noise > 0.78, ((edge_noise - 0.78) / 0.22) ** 0.5 * 0.30 * pm, 0).astype(np.float32)
    # Corona is blue-white
    paint[:,:,0] = np.clip(paint[:,:,0] + corona * 0.5 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + corona * 0.6 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + corona * 1.0 * mask, 0, 1)

    # Layer 4: Rare ultra-bright singularity pinpoints
    sparks = rng.random(shape).astype(np.float32)
    singularity = np.where(sparks > 0.997, 0.40 * pm, 0.0)
    paint = np.clip(paint + singularity[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.1 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_static_grain(paint, shape, mask, seed, pm, bb):
    """SHOKK Static — VIOLENT signal interference with scan lines, glitch bands, and noise bursts."""
    h, w = shape[:2] if len(shape) > 1 else shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed + 1500)

    # Layer 1: Desaturate toward gray static base
    gray = paint.mean(axis=2, keepdims=True)
    desat = 0.35 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + gray[:,:,0] * desat * mask, 0, 1)

    # Layer 2: Heavy per-pixel noise grain
    static = rng.random(shape).astype(np.float32)
    static_intensity = (static - 0.5) * 0.25 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + static_intensity * mask, 0, 1)

    # Layer 3: Horizontal scan line interference bands
    scan_period = max(3, h // 128)
    scan_lines = ((y.astype(np.int32) // scan_period) % 2).astype(np.float32)
    scan_darken = scan_lines * 0.15 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - scan_darken * mask, 0, 1)

    # Layer 4: Horizontal glitch displacement bands (random bright/dark strips)
    n_glitches = rng.randint(8, 20)
    for _ in range(n_glitches):
        gy = rng.randint(0, h)
        gh = rng.randint(2, max(3, h // 40))
        brightness = rng.uniform(-0.25, 0.35) * pm
        y_start = max(0, gy)
        y_end = min(h, gy + gh)
        for c in range(3):
            paint[y_start:y_end, :, c] = np.clip(
                paint[y_start:y_end, :, c] + brightness * mask[y_start:y_end, :], 0, 1)

    # Layer 5: Color channel separation (chromatic aberration feel)
    shift = max(2, h // 256)
    paint[shift:,:,0] = np.clip(paint[shift:,:,0] + 0.04 * pm * mask[shift:,:], 0, 1)
    paint[:-shift,:,2] = np.clip(paint[:-shift,:,2] + 0.04 * pm * mask[:-shift,:], 0, 1)

    # Layer 6: Bright static burst hotspots
    bursts = rng.random(shape).astype(np.float32)
    burst_pop = np.where(bursts > 0.99, 0.30 * pm, 0.0)
    paint = np.clip(paint + burst_pop[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Extreme & Experimental ---

def paint_quantum_absorb(paint, shape, mask, seed, pm, bb):
    """Quantum Black — near-perfect absorption, ultra-dark."""
    paint = paint * (1 - 0.20 * pm * mask[:,:,np.newaxis])
    return paint

def paint_neutron_bright(paint, shape, mask, seed, pm, bb):
    """Neutron Star — impossibly bright compressed mirror."""
    blend = 0.25 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend) + 0.98 * mask * blend
    return paint

def paint_plasma_glow(paint, shape, mask, seed, pm, bb):
    """Plasma Core — glowing reactor core metallic."""
    blend = 0.18 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend) + 0.85 * mask * blend
    # Purple-blue glow
    glow = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1600)
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 0.03 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.05 * pm * mask, 0, 1)
    return paint

def paint_dark_matter_shift(paint, shape, mask, seed, pm, bb):
    """Dark Matter — ultra-dark with hidden angle-dependent reveal."""
    paint = paint * (1 - 0.15 * pm * mask[:,:,np.newaxis])
    y, x = _get_mgrid(shape)
    h, w = shape
    angle = (x / max(w, 1) + y / max(h, 1)) * 0.5
    reveal = np.clip(np.sin(angle * np.pi * 4) * 0.5 + 0.5, 0, 1)
    reveal = np.where(reveal > 0.9, (reveal - 0.9) / 0.1 * 0.04 * pm, 0).astype(np.float32)
    paint = np.clip(paint + reveal[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

paint_superconductor_mirror = make_chrome_tint_fn(0.96, 0.96, 0.98, blend=0.25)

def paint_bio_glow(paint, shape, mask, seed, pm, bb):
    """Bioluminescent — soft glow with scattered bright points."""
    glow = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1700)
    # Green-blue glow
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.04 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.03 * pm * mask, 0, 1)
    rng = np.random.RandomState(seed + 1750)
    spots = rng.random(shape).astype(np.float32)
    spots = np.where(spots > 0.98, 0.06 * pm, 0).astype(np.float32)
    paint = np.clip(paint + spots[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

paint_solar_cell = make_metallic_tint_fn(r_shift=-0.2, g_shift=-0.1, b_shift=0.3, flake_str=0.03)
def paint_holo_rainbow(paint, shape, mask, seed, pm, bb):
    """Holographic Base — full rainbow prismatic color shift with iridescent bands.

    Creates visible holographic rainbow effect by generating position-dependent
    hue rotation across the entire spectrum. Paint colors cycle through R/G/B
    channels based on spatial frequency, producing the classic holographic
    rainbow shimmer seen on holographic foils and stickers.
    """
    h, w = shape[:2] if len(shape) > 1 else shape
    y, x = _get_mgrid(shape)

    # Multi-scale angle field for hue rotation — combines diagonal sweep
    # with noise perturbation for organic holographic feel
    angle_field = (x * 0.03 + y * 0.02)  # base diagonal sweep
    noise_perturb = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 2000)
    noise_perturb = (noise_perturb - noise_perturb.min()) / (noise_perturb.max() - noise_perturb.min() + 1e-8)
    angle_field = angle_field + noise_perturb * 1.5  # perturb the phase

    # Generate RGB hue bands from angle field (120 degree offsets like HSV)
    r_band = (np.sin(angle_field) * 0.5 + 0.5).astype(np.float32)
    g_band = (np.sin(angle_field + 2.094) * 0.5 + 0.5).astype(np.float32)  # +120 deg
    b_band = (np.sin(angle_field + 4.189) * 0.5 + 0.5).astype(np.float32)  # +240 deg

    # Secondary finer frequency for holographic depth
    fine_angle = x * 0.08 + y * 0.06
    fine_noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 2001)
    fine_noise = (fine_noise - fine_noise.min()) / (fine_noise.max() - fine_noise.min() + 1e-8)
    fine_angle = fine_angle + fine_noise * 1.0
    r_fine = (np.sin(fine_angle * 1.3) * 0.5 + 0.5).astype(np.float32)
    g_fine = (np.sin(fine_angle * 1.3 + 2.094) * 0.5 + 0.5).astype(np.float32)
    b_fine = (np.sin(fine_angle * 1.3 + 4.189) * 0.5 + 0.5).astype(np.float32)

    # Combine coarse and fine holo bands
    holo_r = r_band * 0.6 + r_fine * 0.4
    holo_g = g_band * 0.6 + g_fine * 0.4
    holo_b = b_band * 0.6 + b_fine * 0.4

    # Blend holographic color onto existing paint — aggressive enough to be visible
    blend = 0.35 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + holo_r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + holo_g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + holo_b * mask * blend, 0, 1)

    # Sparkle layer — holographic foils have visible micro-sparkle
    rng = np.random.RandomState(seed + 2050)
    sparkle = rng.random(shape).astype(np.float32)
    holo_sparkle = np.where(sparkle > 0.96, 0.20 * pm, 0.0)
    paint = np.clip(paint + holo_sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    # Overall brightness boost for that reflective holographic pop
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# NEW BASE REGISTRY ENTRIES (100 new — #56 to #155)
# ================================================================
# Format matches existing: {"M": int, "R": int, "CC": int, "paint_fn": fn, "desc": str}
# Optional: noise_scales, noise_weights, noise_M, noise_R, brush_grain

EXPANSION_BASES = {
    # Group 1: FOUNDATION (new entries only)
    "eggshell":         {"M": 0,   "R": 140, "CC": 8,  "paint_fn": _paint_noop, "desc": "Soft low-sheen like eggshell wall paint"},
    "semi_gloss":       {"M": 0,   "R": 60,  "CC": 16, "paint_fn": _paint_noop, "desc": "Between satin and gloss — utility finish"},
    # Group 2: METALLIC STANDARD (new entries)
    "metal_flake_base": {"M": 210, "R": 35,  "CC": 16, "paint_fn": "coarse_flake", "desc": "Heavy visible metal flake base coat",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 15},
    "candy_apple":      {"M": 195, "R": 12,  "CC": 16, "paint_fn": paint_candy_depth, "desc": "Classic candy apple red-style transparent tint"},
    "midnight_pearl":   {"M": 140, "R": 25,  "CC": 16, "paint_fn": paint_dark_sparkle, "desc": "Deep dark pearlescent with hidden sparkle",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 10},
    "champagne":        {"M": 160, "R": 45,  "CC": 16, "paint_fn": paint_warm_shimmer, "desc": "Warm gold-silver champagne metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 12},
    "pewter":           {"M": 175, "R": 70,  "CC": 0,  "paint_fn": "subtle_flake", "desc": "Dark gray aged pewter metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 20},
    # Group 3: CHROME & MIRROR (new entries)
    "black_chrome":     {"M": 248, "R": 8,   "CC": 0,  "paint_fn": paint_black_chrome_tint, "desc": "Near-black highly reflective chrome"},
    "blue_chrome":      {"M": 252, "R": 3,   "CC": 0,  "paint_fn": paint_blue_chrome_tint, "desc": "Tinted blue mirror chrome"},
    "red_chrome":       {"M": 252, "R": 3,   "CC": 0,  "paint_fn": paint_red_chrome_tint, "desc": "Tinted red mirror chrome"},
    "antique_chrome":   {"M": 240, "R": 15,  "CC": 0,  "paint_fn": paint_antique_patina, "desc": "Slightly aged imperfect chrome"},
    # Group 4: CANDY & PEARL (new entries)
    "candy_burgundy":   {"M": 200, "R": 14,  "CC": 16, "paint_fn": paint_candy_warm, "desc": "Deep burgundy candy transparent coat"},
    "candy_emerald":    {"M": 200, "R": 14,  "CC": 16, "paint_fn": paint_candy_cool, "desc": "Rich emerald green candy coat"},
    "candy_cobalt":     {"M": 200, "R": 14,  "CC": 16, "paint_fn": paint_candy_cool, "desc": "Deep cobalt blue candy transparent"},
    "tri_coat_pearl":   {"M": 130, "R": 25,  "CC": 16, "paint_fn": paint_tri_coat_sparkle, "desc": "Three-stage pearl base+mid+clear"},
    "moonstone":        {"M": 90,  "R": 35,  "CC": 16, "paint_fn": paint_moonstone_glow, "desc": "Soft translucent milky shimmer"},
    "opal":             {"M": 110, "R": 30,  "CC": 16, "paint_fn": paint_opal_shift, "desc": "Fire opal multi-color depth"},
}

EXPANSION_BASES.update({
    # Group 5: SATIN & WRAP (new entries)
    "matte_wrap":       {"M": 0,   "R": 190, "CC": 0,  "paint_fn": paint_wrap_texture, "desc": "Dead-flat vinyl wrap zero sheen"},
    "color_flip_wrap":  {"M": 150, "R": 70,  "CC": 0,  "paint_fn": paint_color_flip, "desc": "Wrap film that shifts color at angles"},
    "chrome_wrap":      {"M": 240, "R": 20,  "CC": 0,  "paint_fn": paint_chrome_wrap, "desc": "Mirror chrome vinyl wrap — slightly textured"},
    "gloss_wrap":       {"M": 10,  "R": 15,  "CC": 0,  "paint_fn": paint_wrap_texture, "desc": "High-gloss smooth vinyl wrap finish"},
    "textured_wrap":    {"M": 0,   "R": 150, "CC": 0,  "paint_fn": paint_textured_wrap, "desc": "Orange-peel textured vinyl wrap"},
    "brushed_wrap":     {"M": 180, "R": 80,  "CC": 0,  "paint_fn": paint_brushed_wrap, "desc": "Brushed metal vinyl wrap film",
                         "brush_grain": True, "noise_M": 15, "noise_R": 25},
    "stealth_wrap":     {"M": 20,  "R": 200, "CC": 0,  "paint_fn": paint_stealth_flat, "desc": "Ultra-matte radar-absorbing stealth look"},
    # Group 6: INDUSTRIAL & TACTICAL (new entries)
    "mil_spec_od":      {"M": 15,  "R": 180, "CC": 0,  "paint_fn": paint_armor_grain, "desc": "Olive drab military standard coating"},
    "mil_spec_tan":     {"M": 15,  "R": 175, "CC": 0,  "paint_fn": paint_armor_grain, "desc": "Desert tan flat tactical coat"},
    "armor_plate":      {"M": 200, "R": 100, "CC": 0,  "paint_fn": paint_armor_grain, "desc": "Heavy rolled steel armor plating",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "submarine_black":  {"M": 10,  "R": 210, "CC": 0,  "paint_fn": paint_rubber_texture, "desc": "Anechoic submarine hull coating"},
    "gunship_gray":     {"M": 30,  "R": 165, "CC": 0,  "paint_fn": paint_stealth_flat, "desc": "Military aircraft flat gray"},
    "battleship_gray":  {"M": 80,  "R": 140, "CC": 0,  "paint_fn": paint_naval_coat, "desc": "Naval warship haze gray coating"},
    # Group 7: CERAMIC & GLASS (new entries)
    "porcelain":        {"M": 20,  "R": 12,  "CC": 16, "paint_fn": paint_porcelain_smooth, "desc": "White porcelain enamel glassy finish"},
    "obsidian":         {"M": 40,  "R": 6,   "CC": 16, "paint_fn": paint_obsidian_depth, "desc": "Volcanic glass deep black mirror sheen"},
    "crystal_clear":    {"M": 5,   "R": 2,   "CC": 16, "paint_fn": paint_crystal_sparkle, "desc": "Optically clear crystal glass coat"},
    "tempered_glass":   {"M": 30,  "R": 4,   "CC": 16, "paint_fn": paint_glass_clean, "desc": "Safety glass smooth hard surface"},
    "ceramic_matte":    {"M": 50,  "R": 120, "CC": 0,  "paint_fn": paint_ceramic_flat, "desc": "Matte ceramic nano-coating"},
    "enamel":           {"M": 10,  "R": 18,  "CC": 16, "paint_fn": paint_enamel_coat, "desc": "Hard baked enamel glossy traditional paint"},
})

EXPANSION_BASES.update({
    # Group 8: RACING HERITAGE (new entries)
    "race_day_gloss":   {"M": 15,  "R": 10,  "CC": 16, "paint_fn": paint_show_polish, "desc": "Fresh-from-the-trailer showroom glossy"},
    "stock_car_enamel": {"M": 10,  "R": 30,  "CC": 16, "paint_fn": paint_enamel_coat, "desc": "Traditional thick NASCAR enamel paint"},
    "sprint_car_chrome":{"M": 248, "R": 8,   "CC": 0,  "paint_fn": "chrome_brighten", "desc": "Sprint car bright polished chrome"},
    "dirt_track_satin": {"M": 0,   "R": 110, "CC": 8,  "paint_fn": paint_dirt_subtle, "desc": "Slightly dusty satin from dirt track use"},
    "endurance_ceramic":{"M": 55,  "R": 12,  "CC": 16, "paint_fn": "ceramic_gloss", "desc": "24hr endurance race ceramic protection"},
    "rally_mud":        {"M": 30,  "R": 180, "CC": 0,  "paint_fn": paint_mud_splatter, "desc": "Partially mud-splattered rally coating"},
    "drag_strip_gloss": {"M": 200, "R": 8,   "CC": 16, "paint_fn": "fine_sparkle", "desc": "Ultra-polished quarter-mile show finish",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 8},
    "victory_lane":     {"M": 230, "R": 5,   "CC": 16, "paint_fn": paint_confetti_sparkle, "desc": "Champagne-soaked celebration metallic sparkle"},
    "barn_find":        {"M": 60,  "R": 160, "CC": 0,  "paint_fn": paint_barn_aged, "desc": "Decades-old stored car faded paint"},
    "rat_rod_primer":   {"M": 5,   "R": 220, "CC": 0,  "paint_fn": paint_rat_rod_flat, "desc": "Intentionally rough unfinished primer"},
    "pace_car_pearl":   {"M": 140, "R": 20,  "CC": 16, "paint_fn": paint_pace_car_sheen, "desc": "Official pace car triple-pearl coat",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 10},
    "heat_shield":      {"M": 220, "R": 60,  "CC": 0,  "paint_fn": paint_heat_wrap_tint, "desc": "Exhaust heat-wrap reflective coating"},
    "pit_lane_matte":   {"M": 0,   "R": 170, "CC": 0,  "paint_fn": paint_pit_grime, "desc": "Working pit lane matte with slight grime"},
    "asphalt_grind":    {"M": 40,  "R": 200, "CC": 0,  "paint_fn": paint_asphalt_rough, "desc": "Rough asphalt-ground surface texture"},
    "checkered_chrome": {"M": 245, "R": 10,  "CC": 0,  "paint_fn": paint_checker_polish, "desc": "Polished chrome with checkered reflection"},
    # Group 9: EXOTIC METAL (new entries)
    "liquid_titanium":  {"M": 235, "R": 15,  "CC": 0,  "paint_fn": paint_liquid_metal_flow, "desc": "Molten titanium pooling mirror"},
    "tungsten":         {"M": 210, "R": 45,  "CC": 0,  "paint_fn": paint_dense_metal, "desc": "Ultra-dense dark gray tungsten"},
    "platinum":         {"M": 245, "R": 8,   "CC": 0,  "paint_fn": paint_platinum_sheen, "desc": "Pure platinum bright white metal"},
    "cobalt_metal":     {"M": 200, "R": 40,  "CC": 0,  "paint_fn": paint_cobalt_tint, "desc": "Blue-gray cobalt metallic sheen",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 15},
    # Group 10: WEATHERED & AGED (new entries)
    "sun_baked":        {"M": 20,  "R": 200, "CC": 0,  "paint_fn": paint_sun_fade, "desc": "UV-damaged sun-faded peeling clear"},
    "salt_corroded":    {"M": 90,  "R": 150, "CC": 0,  "paint_fn": paint_salt_damage, "desc": "Coastal salt air corroded metal"},
    "desert_worn":      {"M": 40,  "R": 175, "CC": 0,  "paint_fn": paint_desert_sand, "desc": "Sand-blasted desert weathered surface"},
    "acid_rain":        {"M": 70,  "R": 130, "CC": 0,  "paint_fn": paint_acid_etch_base, "desc": "Chemical rain etched paint damage"},
    "oxidized_copper":  {"M": 145, "R": 100, "CC": 0,  "paint_fn": paint_heavy_patina, "desc": "Fully green-oxidized copper (Statue of Liberty)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 30},
    "vintage_chrome":   {"M": 230, "R": 25,  "CC": 0,  "paint_fn": paint_vintage_haze, "desc": "1950s chrome with cloudy oxidation spots"},
})

EXPANSION_BASES.update({
    # Group 11: OEM AUTOMOTIVE (new entries)
    "factory_basecoat": {"M": 120, "R": 40,  "CC": 16, "paint_fn": paint_oem_metallic, "desc": "Standard OEM factory metallic basecoat"},
    "showroom_clear":   {"M": 5,   "R": 6,   "CC": 16, "paint_fn": paint_show_polish, "desc": "Freshly detailed concours clearcoat"},
    "fleet_white":      {"M": 0,   "R": 35,  "CC": 16, "paint_fn": _paint_noop, "desc": "Government/fleet plain white gloss"},
    "taxi_yellow":      {"M": 0,   "R": 25,  "CC": 16, "paint_fn": _paint_noop, "desc": "NYC taxi cab bright yellow gloss"},
    "school_bus":       {"M": 0,   "R": 40,  "CC": 12, "paint_fn": _paint_noop, "desc": "National school bus chrome yellow"},
    "fire_engine":      {"M": 5,   "R": 15,  "CC": 16, "paint_fn": paint_fire_engine_gloss, "desc": "Deep wet fire apparatus red gloss"},
    "ambulance_white":  {"M": 0,   "R": 30,  "CC": 16, "paint_fn": paint_reflective_coat, "desc": "High-visibility emergency white reflective"},
    "police_black":     {"M": 5,   "R": 8,   "CC": 16, "paint_fn": _paint_noop, "desc": "Law enforcement glossy black"},
    "dealer_pearl":     {"M": 110, "R": 28,  "CC": 16, "paint_fn": paint_dealer_sparkle, "desc": "Dealer premium tri-coat pearl upgrade",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 10},
    # Group 12: CARBON & COMPOSITE (new entries)
    "carbon_base":      {"M": 100, "R": 60,  "CC": 0,  "paint_fn": paint_carbon_weave_base, "desc": "Raw exposed carbon fiber base material"},
    "kevlar_base":      {"M": 80,  "R": 90,  "CC": 0,  "paint_fn": paint_kevlar_weave, "desc": "Ballistic kevlar aramid fiber base"},
    "fiberglass":       {"M": 30,  "R": 80,  "CC": 8,  "paint_fn": paint_fiberglass_gel, "desc": "Raw fiberglass gelcoat semi-gloss"},
    "carbon_ceramic":   {"M": 110, "R": 40,  "CC": 0,  "paint_fn": paint_carbon_ceramic_coat, "desc": "Brake rotor carbon-ceramic composite"},
    "aramid":           {"M": 70,  "R": 95,  "CC": 0,  "paint_fn": paint_aramid_weave, "desc": "Woven aramid fiber natural gold-tan"},
    "graphene":         {"M": 180, "R": 20,  "CC": 0,  "paint_fn": paint_graphene_sheen, "desc": "Single-layer graphene ultra-thin metallic"},
    "forged_composite": {"M": 90,  "R": 70,  "CC": 0,  "paint_fn": paint_forged_composite_base, "desc": "Lamborghini-style forged carbon composite"},
    "hybrid_weave":     {"M": 95,  "R": 55,  "CC": 0,  "paint_fn": paint_hybrid_weave_base, "desc": "Carbon-kevlar hybrid bi-weave material"},
    # Group 13: PREMIUM LUXURY (new entries — satin_gold already exists)
    "bentley_silver":   {"M": 230, "R": 18,  "CC": 16, "paint_fn": paint_luxury_sparkle, "desc": "Rolls-Royce/Bentley ultra-fine silver"},
    "ferrari_rosso":    {"M": 25,  "R": 10,  "CC": 16, "paint_fn": paint_rosso_depth, "desc": "Ferrari Rosso Corsa deep wet red"},
    "lamborghini_verde":{"M": 70,  "R": 12,  "CC": 16, "paint_fn": paint_lambo_green, "desc": "Lamborghini Verde Mantis electric green"},
    "porsche_pts":      {"M": 80,  "R": 15,  "CC": 16, "paint_fn": paint_pts_depth, "desc": "Porsche Paint-to-Sample custom deep coat"},
    "mclaren_orange":   {"M": 50,  "R": 10,  "CC": 16, "paint_fn": paint_mclaren_vivid, "desc": "McLaren Papaya Spark vivid orange"},
    "bugatti_blue":     {"M": 120, "R": 8,   "CC": 16, "paint_fn": paint_bugatti_depth, "desc": "Bugatti Bleu de France deep two-tone"},
    "koenigsegg_clear": {"M": 130, "R": 5,   "CC": 16, "paint_fn": paint_naked_carbon, "desc": "Clear carbon visible weave (Koenigsegg style)"},
    "pagani_tricolore": {"M": 150, "R": 10,  "CC": 16, "paint_fn": paint_pagani_shift, "desc": "Pagani chameleon tricolore shift paint"},
    "maybach_two_tone": {"M": 100, "R": 15,  "CC": 16, "paint_fn": paint_two_tone_split, "desc": "Mercedes-Maybach duo-tone luxury split"},
    # Group 14: SHOKK SERIES (new entries — plasma_metal etc already exist)
    "shokk_pulse":      {"M": 220, "R": 15,  "CC": 16, "paint_fn": paint_pulse_electric, "desc": "Electric pulse wave metallic — Shokker signature"},
    "shokk_venom":      {"M": 210, "R": 20,  "CC": 16, "paint_fn": paint_venom_acid, "desc": "Toxic acid green-yellow metallic reactive"},
    "shokk_blood":      {"M": 190, "R": 25,  "CC": 16, "paint_fn": paint_blood_red_deep, "desc": "Deep arterial red metallic with dark edge"},
    "shokk_void":       {"M": 10,  "R": 240, "CC": 0,  "paint_fn": paint_void_absorb, "desc": "Near-vantablack with subtle edge shimmer"},
    "shokk_static":     {"M": 200, "R": 30,  "CC": 0,  "paint_fn": paint_static_grain, "desc": "Crackling static interference metallic"},
    # Group 15: EXTREME & EXPERIMENTAL (new entries)
    "quantum_black":    {"M": 5,   "R": 245, "CC": 0,  "paint_fn": paint_quantum_absorb, "desc": "Near-perfect light absorption ultra-black"},
    "neutron_star":     {"M": 255, "R": 0,   "CC": 0,  "paint_fn": paint_neutron_bright, "desc": "Impossibly bright compressed mirror"},
    "plasma_core":      {"M": 240, "R": 5,   "CC": 16, "paint_fn": paint_plasma_glow, "desc": "Glowing plasma reactor core metallic"},
    "dark_matter":      {"M": 30,  "R": 230, "CC": 0,  "paint_fn": paint_dark_matter_shift, "desc": "Ultra-dark with hidden angle-dependent reveal"},
    "superconductor":   {"M": 250, "R": 2,   "CC": 0,  "paint_fn": paint_superconductor_mirror, "desc": "Perfect zero-resistance mirror surface"},
    "bioluminescent":   {"M": 60,  "R": 40,  "CC": 16, "paint_fn": paint_bio_glow, "desc": "Deep sea organism soft glow finish"},
    "solar_panel":      {"M": 140, "R": 50,  "CC": 0,  "paint_fn": paint_solar_cell, "desc": "Photovoltaic solar cell dark blue-black"},
    "holographic_base": {"M": 200, "R": 10,  "CC": 16, "paint_fn": paint_holo_rainbow, "desc": "Full holographic rainbow prismatic base"},
})


# ================================================================
# PATTERN TEXTURE + PAINT FUNCTION FACTORIES
# ================================================================

def make_grid_texture_fn(cell_size, line_width=2, diagonal=False):
    """Factory: grid/mesh texture pattern."""
    def fn(shape, seed):
        h, w = shape
        y, x = _get_mgrid(shape)
        if diagonal:
            grid = ((x + y) % cell_size < line_width).astype(np.float32)
            grid2 = ((x - y) % cell_size < line_width).astype(np.float32)
            return np.maximum(grid, grid2)
        else:
            grid_h = (y % cell_size < line_width).astype(np.float32)
            grid_v = (x % cell_size < line_width).astype(np.float32)
            return np.maximum(grid_h, grid_v)
    return fn

def make_stripe_texture_fn(spacing, width, angle_rad=0.0):
    """Factory: parallel stripe texture at given angle."""
    def fn(shape, seed):
        h, w = shape
        y, x = _get_mgrid(shape)
        dist = x * np.cos(angle_rad) + y * np.sin(angle_rad)
        return ((dist % spacing) < width).astype(np.float32)
    return fn

def make_dot_texture_fn(spacing, radius):
    """Factory: repeating dot/circle grid."""
    def fn(shape, seed):
        h, w = shape
        y, x = _get_mgrid(shape)
        cy = (y % spacing) - spacing / 2
        cx = (x % spacing) - spacing / 2
        dist = np.sqrt(cy**2 + cx**2)
        return np.clip(1.0 - dist / radius, 0, 1)
    return fn

def make_wave_texture_fn(freq=0.05, amplitude=1.0):
    """Factory: sine wave texture."""
    def fn(shape, seed):
        h, w = shape
        y, x = _get_mgrid(shape)
        wave = np.sin(y * freq + _multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed) * 2) * 0.5 + 0.5
        return np.clip(wave * amplitude, 0, 1)
    return fn

def make_voronoi_texture_fn(num_points=80, edge_mode=False):
    """Factory: Voronoi cell texture - optimized with limited-radius distance."""
    def fn(shape, seed):
        import numpy as np
        h, w = shape[:2] if len(shape) > 2 else shape
        rng = np.random.RandomState(seed)
        pts_y = rng.randint(0, h, num_points)
        pts_x = rng.randint(0, w, num_points)
        min_dist = np.full((h, w), 1e9, dtype=np.float32)
        min_dist2 = np.full((h, w), 1e9, dtype=np.float32)
        # Limit radius: each point only affects nearby pixels
        r = int(max(h, w) * 1.5 / max(1, num_points**0.5)) + 20
        for py, px in zip(pts_y, pts_x):
            y0, y1 = max(0, int(py)-r), min(h, int(py)+r)
            x0, x1 = max(0, int(px)-r), min(w, int(px)+r)
            if y1<=y0 or x1<=x0: continue
            ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
            lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
            d = np.sqrt((ly - py)**2 + (lx - px)**2)
            roi_min = min_dist[y0:y1, x0:x1]
            roi_min2 = min_dist2[y0:y1, x0:x1]
            update = d < roi_min
            min_dist2[y0:y1, x0:x1] = np.where(update, roi_min, np.minimum(roi_min2, d))
            min_dist[y0:y1, x0:x1] = np.minimum(roi_min, d)
        if edge_mode:
            edge = min_dist2 - min_dist
            return np.clip(1.0 - edge / 8.0, 0, 1)
        else:
            return np.clip(min_dist / 40.0, 0, 1)
    return fn

def make_noise_texture_fn(scales, weights):
    """Factory: multi-scale noise as a texture."""
    def fn(shape, seed):
        return np.clip(_multi_scale_noise(shape, scales, weights, seed) * 0.5 + 0.5, 0, 1)
    return fn

def make_radial_texture_fn(num_arms=6, twist=0.05):
    """Factory: radial/spiral arm pattern from center."""
    def fn(shape, seed):
        h, w = shape
        y, x = _get_mgrid(shape)
        cy, cx = h / 2, w / 2
        angle = np.arctan2(y - cy, x - cx)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2)
        spiral = np.sin(angle * num_arms + dist * twist) * 0.5 + 0.5
        return spiral.astype(np.float32)
    return fn

def make_symbol_grid_fn(symbol_fn, cell_size=48):
    """Factory: repeating symbol in a grid. symbol_fn(y_local, x_local, size) -> 0..1"""
    def fn(shape, seed):
        h, w = shape
        y, x = _get_mgrid(shape)
        ly = y % cell_size
        lx = x % cell_size
        return symbol_fn(ly, lx, cell_size)
    return fn

# --- Symbol functions for make_symbol_grid_fn ---

def _cross_symbol(ly, lx, size):
    """Gothic cross shape."""
    cx, cy = size / 2, size / 2
    arm_w = size * 0.12
    in_vert = (np.abs(lx - cx) < arm_w) & (ly > size * 0.1) & (ly < size * 0.9)
    in_horiz = (np.abs(ly - cy) < arm_w) & (lx > size * 0.2) & (lx < size * 0.8)
    return (in_vert | in_horiz).astype(np.float32)

def _rune_symbol(ly, lx, size):
    """Elder Futhark rune shape — vertical stave with angled branches."""
    cx = size / 2
    stave_w = size * 0.08
    # Vertical stave (main line)
    stave = (np.abs(lx - cx) < stave_w) & (ly > size * 0.08) & (ly < size * 0.92)
    # Upper-right diagonal branch (like Fehu / Ansuz)
    dy1 = ly - size * 0.25
    dx1 = lx - cx
    branch1 = (np.abs(dy1 - dx1 * 0.8) < stave_w * 1.3) & (dx1 > 0) & (dx1 < size * 0.35) & (ly > size * 0.15) & (ly < size * 0.50)
    # Lower-right diagonal branch (angled the other way)
    dy2 = ly - size * 0.55
    branch2 = (np.abs(dy2 + dx1 * 0.8) < stave_w * 1.3) & (dx1 > 0) & (dx1 < size * 0.30) & (ly > size * 0.40) & (ly < size * 0.70)
    # Upper-left small tick (like Thurisaz thorn)
    dx3 = cx - lx
    dy3 = ly - size * 0.70
    branch3 = (np.abs(dy3 - dx3 * 1.0) < stave_w * 1.1) & (dx3 > 0) & (dx3 < size * 0.20) & (ly > size * 0.60) & (ly < size * 0.82)
    return (stave | branch1 | branch2 | branch3).astype(np.float32)

def _fleur_symbol(ly, lx, size):
    """Fleur-de-lis approximation."""
    cx, cy = size / 2, size / 2
    # Central petal
    d_center = np.sqrt((ly - cy * 0.6)**2 + (lx - cx)**2)
    center = np.clip(1.0 - d_center / (size * 0.2), 0, 1)
    # Side petals
    d_left = np.sqrt((ly - cy * 0.7)**2 + (lx - cx * 0.6)**2)
    d_right = np.sqrt((ly - cy * 0.7)**2 + (lx - cx * 1.4)**2)
    left = np.clip(1.0 - d_left / (size * 0.18), 0, 1)
    right = np.clip(1.0 - d_right / (size * 0.18), 0, 1)
    # Stem
    stem = ((np.abs(lx - cx) < size * 0.06) & (ly > cy)).astype(np.float32)
    return np.clip(center + left + right + stem * 0.8, 0, 1)

def _yin_yang_symbol(ly, lx, size):
    """Yin-yang circle."""
    cx, cy = size / 2, size / 2
    r = size * 0.4
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    inside = (dist < r).astype(np.float32)
    # Split by side
    angle = np.arctan2(ly - cy, lx - cx)
    half = (np.sin(angle + dist / r * np.pi) > 0).astype(np.float32)
    return inside * half

def _star_symbol(ly, lx, size):
    """Five-pointed star (filled)."""
    cx, cy = size / 2, size / 2
    angle = np.arctan2(ly - cy, lx - cx)
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    r_outer = size * 0.4
    r_inner = size * 0.18
    # Star radius varies with angle
    star_angle = (angle + np.pi) % (2 * np.pi / 5) - np.pi / 5
    star_r = r_inner + (r_outer - r_inner) * (1 - np.abs(star_angle) / (np.pi / 5))
    return (dist < star_r).astype(np.float32)

def _pentagram_symbol(ly, lx, size):
    """Pentagram — five-pointed star drawn as LINE STROKES connecting every other
    vertex of a regular pentagon, forming the classic occult/gothic pentagram with
    visible inner pentagon. NOT a filled star shape."""
    cx, cy = size / 2, size / 2
    r = size * 0.42
    line_w = size * 0.04  # stroke width
    result = np.zeros_like(ly, dtype=np.float32)
    # 5 vertices of the pentagon (top-pointing)
    verts = []
    for i in range(5):
        a = -np.pi / 2 + i * 2 * np.pi / 5  # start from top
        verts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
    # Draw 5 line segments connecting every other vertex (0->2, 2->4, 4->1, 1->3, 3->0)
    connections = [(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)]
    for i, j in connections:
        x1, y1 = verts[i]
        x2, y2 = verts[j]
        # Distance from point to line segment
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-8:
            continue
        # Project each pixel onto the line segment
        t = np.clip(((lx - x1) * dx + (ly - y1) * dy) / seg_len_sq, 0, 1)
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        dist = np.sqrt((lx - closest_x)**2 + (ly - closest_y)**2)
        line = np.clip(1.0 - dist / line_w, 0, 1)
        result = np.maximum(result, line)
    # Outer circle (optional, classic pentagram-in-circle)
    dist_center = np.sqrt((lx - cx)**2 + (ly - cy)**2)
    circle = np.clip(1.0 - np.abs(dist_center - r) / (line_w * 0.8), 0, 1) * 0.7
    result = np.maximum(result, circle)
    return result.astype(np.float32)

def _skull_simple(ly, lx, size):
    """Simple skull outline."""
    cx, cy = size / 2, size * 0.4
    # Head oval
    head_d = np.sqrt(((ly - cy) / (size * 0.3))**2 + ((lx - cx) / (size * 0.25))**2)
    head = np.clip(1.0 - head_d / 1.0, 0, 1)
    # Jaw
    jaw_d = np.sqrt(((ly - size * 0.65) / (size * 0.15))**2 + ((lx - cx) / (size * 0.18))**2)
    jaw = np.clip(1.0 - jaw_d / 1.0, 0, 1)
    return np.clip(head + jaw * 0.7, 0, 1)

def _biohazard_symbol(ly, lx, size):
    """Biohazard trefoil."""
    cx, cy = size / 2, size / 2
    result = np.zeros_like(ly)
    for i in range(3):
        a = i * 2 * np.pi / 3
        px, py = cx + np.cos(a) * size * 0.15, cy + np.sin(a) * size * 0.15
        d = np.sqrt((ly - py)**2 + (lx - px)**2)
        result = np.maximum(result, np.clip(1.0 - d / (size * 0.22), 0, 1))
    # Center hole
    d_center = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    hole = (d_center < size * 0.08).astype(np.float32)
    return np.clip(result - hole, 0, 1)


# ================================================================
# CONCRETE NEW TEXTURE FUNCTIONS (for new patterns)
# ================================================================

# --- Carbon & Weave Group ---
def texture_carbon_4x4(shape, seed):
    """Carbon fiber 4x4 twill weave pattern."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # 4x4 twill: each thread goes over 4, under 4, shifted by 1 each row
    period = 8
    ly = y % period
    lx = x % period
    shift = y % period
    pos = (lx + shift) % period
    twill = (pos < 4).astype(np.float32)
    # Add fiber direction shading
    fiber_h = np.sin(x * np.pi * 0.5) * 0.15
    fiber_v = np.sin(y * np.pi * 0.5) * 0.15
    shading = np.where(twill > 0.5, 0.7 + fiber_h, 0.3 + fiber_v)
    return np.clip(shading, 0, 1).astype(np.float32)
def texture_spread_tow(shape, seed):
    """Spread tow carbon - flat wide tape layup pattern."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # Wide flat tapes at alternating angles
    tape_w = 20
    # 0 degree tapes
    tape_0 = np.sin(x * np.pi / tape_w) * 0.5 + 0.5
    # 90 degree tapes
    tape_90 = np.sin(y * np.pi / tape_w) * 0.5 + 0.5
    # Layer them with slight offset
    layer = ((y // tape_w) % 2).astype(np.float32)
    result = np.where(layer > 0.5, tape_0 * 0.6 + tape_90 * 0.2, tape_0 * 0.2 + tape_90 * 0.6)
    return np.clip(result + 0.15, 0, 1).astype(np.float32)
def texture_carbon_uni(shape, seed):
    """Unidirectional carbon fiber - parallel fibers with subtle variation."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    # Parallel vertical fibers
    fiber_width = 3.0
    fiber = np.sin(x * np.pi / fiber_width) * 0.5 + 0.5
    # Slight waviness along length
    nh, nw = max(1, h // 16), max(1, w // 16)
    noise = rng.rand(nh, nw).astype(np.float32)
    wave = np.repeat(np.repeat(noise, 16, axis=0), 16, axis=1)[:h, :w]
    fiber_shifted = np.sin((x + wave * 2) * np.pi / fiber_width) * 0.5 + 0.5
    return np.clip(fiber_shifted * 0.7 + 0.15, 0, 1).astype(np.float32)
def texture_tweed_weave(shape, seed):
    """Tweed - irregular herringbone weave with nubby texture."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    block = 16
    col_block = (x // block).astype(int)
    even = (col_block % 2 == 0)
    angle_y = np.where(even, y + x, y - x).astype(np.float32)
    herring = np.sin(angle_y * np.pi / 4) * 0.5 + 0.5
    nh, nw = max(1, h // 3 + 1), max(1, w // 3 + 1)
    nubs = rng.rand(nh, nw).astype(np.float32)
    nub_map = np.repeat(np.repeat(nubs, 3, axis=0), 3, axis=1)[:h, :w]
    return np.clip(herring * 0.7 + nub_map * 0.3, 0, 1).astype(np.float32)
def texture_basket_weave(shape, seed):
    """Basket weave - interlocking over/under strips."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    size = 16
    ly = y % (size * 2)
    lx = x % (size * 2)
    # Horizontal strips in top half, vertical in bottom half, alternating
    h_strip = (ly < size).astype(np.float32)
    v_strip = (lx < size).astype(np.float32)
    # Create over/under by alternating which is on top
    block_y = ((y // size) % 2).astype(np.float32)
    block_x = ((x // size) % 2).astype(np.float32)
    checker = (block_y + block_x) % 2
    weave = np.where(checker > 0.5,
                     np.clip((ly % size) / size, 0.3, 0.9),
                     np.clip((lx % size) / size, 0.3, 0.9))
    return weave.astype(np.float32)
def texture_chainlink(shape, seed):
    """Chain-link fence - interlocking diamond wire mesh."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 24
    # Diamond grid using diagonal lines
    d1 = np.abs(((xf + yf) % cell) - cell / 2.0)
    d2 = np.abs(((xf - yf) % cell) - cell / 2.0)
    wire1 = np.clip(1.0 - d1 / 1.5, 0, 1)
    wire2 = np.clip(1.0 - d2 / 1.5, 0, 1)
    wire = np.maximum(wire1, wire2)
    # Add knot at intersections
    knot_y = ((xf + yf) % cell < 3) | ((xf + yf) % cell > cell - 3)
    knot_x = ((xf - yf) % cell < 3) | ((xf - yf) % cell > cell - 3)
    knots = (knot_y & knot_x).astype(np.float32) * 0.3
    return np.clip(wire + knots, 0, 1).astype(np.float32)
def texture_kevlar_weave_pat(shape, seed):
    """Kevlar aramid fiber - tight plain weave with golden sheen."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    size = max(2, int(8 * scale))
    # Plain weave (1x1): alternating over/under every thread
    checker = ((y // size + x // size) % 2).astype(np.float32)
    # Rounded thread profiles with FULL 0-1 range for contrast
    ty = np.sin((y % size) * np.pi / size)  # 0 to 1
    tx = np.sin((x % size) * np.pi / size)  # 0 to 1
    # Over threads at full height, under threads recessed to near 0
    weave = np.where(checker > 0.5, ty * 0.9 + 0.1, tx * 0.15)
    return weave.astype(np.float32)
def texture_nanoweave(shape, seed):
    """Nanoweave - ultra-fine tight mesh texture."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    # Very small cell size for nano-scale feel
    size = 4
    ty = np.sin(y * np.pi / size)
    tx = np.sin(x * np.pi / size)
    # Fine weave with slight variation
    checker = ((y // size + x // size) % 2).astype(np.float32)
    weave = np.abs(ty * tx) * 0.4
    base = checker * 0.3 + 0.3
    return np.clip(base + weave, 0, 1).astype(np.float32)
def texture_exhaust_wrap(shape, seed):
    """Exhaust wrap - diagonal bandage wrapping around tube."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    wrap_width = 16
    # Diagonal wrap bands
    diag = (x.astype(np.float32) + y.astype(np.float32) * 0.5)
    band = diag % wrap_width
    edge = np.clip(1.0 - np.abs(band - wrap_width / 2) / (wrap_width / 2) * 1.5, 0, 1)
    # Fiber texture within bands
    fiber = np.sin(diag * np.pi / 2) * 0.1
    # Slight wear
    nh, nw = max(1, h // 8), max(1, w // 8)
    wear = rng.rand(nh, nw).astype(np.float32)
    wear_map = np.repeat(np.repeat(wear, 8, axis=0), 8, axis=1)[:h, :w]
    return np.clip(edge * 0.7 + fiber + wear_map * 0.15 + 0.1, 0, 1).astype(np.float32)
def texture_harness_weave(shape, seed):
    """Harness/satin weave - long float threads with offset."""
    h, w = shape
    y, x = _get_mgrid(shape)
    period = 10
    # 5-harness satin: float over 4, under 1, shift 2 each row
    shift = (y * 2) % period
    pos = (x + shift) % period
    satin = (pos < 1).astype(np.float32)
    # Smooth thread appearance
    thread_x = np.sin(x * np.pi / 2.5) * 0.5 + 0.5
    thread_y = np.sin(y * np.pi / 2.5) * 0.5 + 0.5
    base = np.where(satin > 0.5, thread_y * 0.4 + 0.6, thread_x * 0.3 + 0.3)
    return base.astype(np.float32)

# --- Metal & Industrial Group ---
def texture_rivet_grid(shape, seed):
    """Rivet grid — raised dome-head rivets with beveled edges in a regular grid."""
    import numpy as np
    h, w = shape[:2]
    y, x = np.mgrid[:h, :w]
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    spacing = 24
    # Local position within each cell
    ly = yf % spacing
    lx = xf % spacing
    cy, cx = spacing / 2.0, spacing / 2.0
    dist = np.sqrt((ly - cy) ** 2 + (lx - cx) ** 2)
    rivet_r = 5.0
    # Dome shape: hemisphere profile
    dome = np.clip(1.0 - (dist / rivet_r) ** 2, 0, 1)
    dome = np.sqrt(np.maximum(dome, 0))  # hemisphere curve
    # Bright highlight on upper-left (lighting effect)
    highlight_dist = np.sqrt((ly - cy + 1.5) ** 2 + (lx - cx + 1.5) ** 2)
    highlight = np.clip(1.0 - highlight_dist / (rivet_r * 0.6), 0, 1) * 0.3
    # Shadow on lower-right
    shadow_dist = np.sqrt((ly - cy - 1.5) ** 2 + (lx - cx - 1.5) ** 2)
    shadow = np.clip(1.0 - shadow_dist / (rivet_r * 0.8), 0, 1) * 0.15
    rivet = dome * 0.7 + highlight - shadow * (dist < rivet_r).astype(np.float32)
    return np.clip(rivet, 0, 1).astype(np.float32)
def texture_corrugated(shape, seed):
    """Corrugated metal - rounded wavy ridges."""
    h, w = shape
    y, x = _get_mgrid(shape)
    period = 12.0
    # Rounded sine wave profile
    ridges = np.sin(y * np.pi * 2 / period) * 0.5 + 0.5
    # Specular highlight on ridge peaks
    highlight = np.clip(ridges - 0.7, 0, 1) * 3.0
    return np.clip(ridges * 0.7 + highlight * 0.3 + 0.1, 0, 1).astype(np.float32)
def texture_perforated(shape, seed):
    """Perforated metal — circular holes punched through sheet with beveled edges."""
    import numpy as np
    h, w = shape[:2]
    y, x = np.mgrid[:h, :w]
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    spacing = 12.0
    hole_r = 4.0
    # Offset every other row for staggered pattern
    row = np.floor(yf / spacing)
    x_offset = xf + (row % 2) * (spacing / 2)
    ly = yf % spacing
    lx = x_offset % spacing
    cy, cx = spacing / 2.0, spacing / 2.0
    dist = np.sqrt((ly - cy) ** 2 + (lx - cx) ** 2)
    # Hole: dark center, bright beveled rim
    hole_inside = (dist < hole_r).astype(np.float32) * 0.05  # very dark = hole
    bevel = np.clip(1.0 - np.abs(dist - hole_r) / 1.5, 0, 1) * 0.8  # bright rim
    # Metal surface between holes
    surface = (dist > hole_r + 1).astype(np.float32) * 0.45
    return np.clip(hole_inside + bevel + surface, 0, 1).astype(np.float32)
def texture_expanded_metal(shape, seed):
    """Expanded metal - diamond-shaped stretched mesh."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Stretched diamond cells (wider than tall)
    cell_w, cell_h = 20, 12
    row = np.floor(yf / cell_h)
    offset = (row % 2) * cell_w / 2
    lx = (xf + offset) % cell_w - cell_w / 2.0
    ly = yf % cell_h - cell_h / 2.0
    # Diamond shape
    diamond = np.abs(lx) / (cell_w * 0.45) + np.abs(ly) / (cell_h * 0.45)
    edge = np.clip(1.0 - np.abs(diamond - 1.0) * 6, 0, 1)
    return edge.astype(np.float32)
def texture_grating(shape, seed):
    """Grating — parallel flat bars with gaps showing depth shadows between them."""
    import numpy as np
    h, w = shape[:2]
    y, x = np.mgrid[:h, :w]
    yf = y.astype(np.float32)
    spacing = 10.0
    bar_w = 6.0  # bar is wider than gap
    pos = yf % spacing
    # Bar surface with slight rounded profile
    bar = (pos < bar_w).astype(np.float32)
    bar_profile = np.sin(pos / bar_w * np.pi) * bar  # rounded top
    # Gap shadow (dark between bars)
    gap = (pos >= bar_w).astype(np.float32)
    gap_depth = gap * 0.05  # very dark in gaps
    # Edge highlight on bar top edge
    edge = np.clip(1.0 - np.abs(pos - 0.5) / 1.0, 0, 1) * bar * 0.2
    return np.clip(bar_profile * 0.7 + edge + gap_depth, 0, 1).astype(np.float32)
def texture_knurled(shape, seed):
    """Knurled grip - diamond crosshatch pattern."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    spacing = 8*scale
    # Two diagonal groove sets creating diamond pattern
    d1 = (xf + yf) % spacing
    d2 = (xf - yf) % spacing
    groove1 = np.sin(d1 * np.pi / spacing) 
    groove2 = np.sin(d2 * np.pi / spacing)
    # Multiply to get raised diamond peaks
    knurl = groove1 * groove2
    return np.clip(knurl, 0, 1).astype(np.float32)
def texture_roll_cage(shape, seed):
    """Roll cage - tubular bar structure with cross braces."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 48*scale
    ly = yf % cell
    lx = xf % cell
    # Main bars: thick horizontal and vertical
    bar_w = 4.0
    h_bar = np.clip(1.0 - np.abs(ly - cell / 2.0) / bar_w, 0, 1)
    v_bar = np.clip(1.0 - np.abs(lx - cell / 2.0) / bar_w, 0, 1)
    top = np.clip(1.0 - ly / bar_w, 0, 1)
    bottom = np.clip(1.0 - (cell - ly) / bar_w, 0, 1)
    left = np.clip(1.0 - lx / bar_w, 0, 1)
    right = np.clip(1.0 - (cell - lx) / bar_w, 0, 1)
    frame = np.maximum(np.maximum(top, bottom), np.maximum(left, right))
    # Diagonal cross brace
    d1 = np.abs(ly - lx * cell / cell)
    diag = np.clip(1.0 - d1 / 3.0, 0, 1) * 0.8
    bars = np.maximum(np.maximum(h_bar, v_bar), np.maximum(frame, diag))
    return np.clip(bars, 0, 1).astype(np.float32)

# --- Nature & Organic Group ---
def texture_tree_bark(shape, seed):
    """Tree bark - vertical ridged bark with horizontal cracks."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    # Vertical ridges
    ridge_spacing = 12*scale
    ridges = np.sin(x * np.pi / ridge_spacing) * 0.5 + 0.5
    # Horizontal crack lines
    crack_spacing = 20*scale
    cracks = np.clip(1.0 - np.abs(y.astype(np.float32) % crack_spacing - 1) / 2.0, 0, 1) * 0.5
    # Bark roughness
    nh, nw = max(1, h // 4), max(1, w // 4)
    noise = rng.rand(nh, nw).astype(np.float32)
    nmap = np.repeat(np.repeat(noise, 4, axis=0), 4, axis=1)[:h, :w]
    return np.clip(ridges * 0.5 + cracks + nmap * 0.2 + 0.15, 0, 1).astype(np.float32)
def texture_coral_reef(shape, seed):
    """Coral reef — branching coral structures with rounded polyp tips."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    # Multiple coral branches growing upward from random base positions
    for _ in range(30):
        base_x = rng.uniform(0, w)
        base_y = h * rng.uniform(0.6, 0.95)  # start from lower area
        n_segments = rng.randint(5, 15)
        cx, cy = base_x, base_y
        branch_w = rng.uniform(4, 10)
        brightness = rng.uniform(0.4, 0.8)
        for seg in range(n_segments):
            # Branch grows upward with random horizontal drift
            next_cx = cx + rng.uniform(-8, 8)
            next_cy = cy - rng.uniform(5, 15)
            if next_cy < 0:
                break
            # Draw segment as thick line
            n_pts = max(2, int(np.sqrt((next_cy - cy) ** 2 + (next_cx - cx) ** 2)))
            for ti in range(n_pts):
                t = ti / max(1, n_pts - 1)
                py = int(cy + (next_cy - cy) * t)
                px = int(cx + (next_cx - cx) * t)
                bw = int(branch_w * (1.0 - seg * 0.05))
                y0, y1 = max(0, py - bw), min(h, py + bw)
                x0, x1 = max(0, px - bw), min(w, px + bw)
                if y1 > y0 and x1 > x0:
                    ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
                    lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
                    d = np.sqrt((ly - py) ** 2 + (lx - px) ** 2)
                    seg_val = np.clip(1.0 - d / bw, 0, 1) * brightness
                    np.maximum(out[y0:y1, x0:x1], seg_val, out=out[y0:y1, x0:x1])
            cx, cy = next_cx, next_cy
            # Random sub-branching
            if rng.rand() > 0.6 and seg > 2:
                branch_w *= 0.7
                cx += rng.uniform(-10, 10)
        # Polyp tip (rounded bright blob at end)
        tip_r = branch_w * 1.3
        m = int(tip_r) + 2
        ty, tx = int(cy), int(cx)
        y0, y1 = max(0, ty - m), min(h, ty + m)
        x0, x1 = max(0, tx - m), min(w, tx + m)
        if y1 > y0 and x1 > x0:
            ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
            lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
            d = np.sqrt((ly - ty) ** 2 + (lx - tx) ** 2)
            tip = np.clip(1.0 - d / tip_r, 0, 1) ** 0.5 * brightness
            np.maximum(out[y0:y1, x0:x1], tip, out=out[y0:y1, x0:x1])
    return np.clip(out, 0, 1)
def texture_river_stone(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    num_pts = 30
    pts_y = rng.randint(0, h, num_pts)
    pts_x = rng.randint(0, w, num_pts)
    min_dist = np.full((h, w), 1e9, dtype=np.float32)
    min_dist2 = np.full((h, w), 1e9, dtype=np.float32)
    r = int(max(h, w) * 0.45)
    for py, px in zip(pts_y, pts_x):
        y0, y1 = max(0, py-r), min(h, py+r)
        x0, x1 = max(0, px-r), min(w, px+r)
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        d = np.sqrt((ly-py)**2 + (lx-px)**2)
        roi1 = min_dist[y0:y1, x0:x1]
        roi2 = min_dist2[y0:y1, x0:x1]
        update = d < roi1
        min_dist2[y0:y1, x0:x1] = np.where(update, roi1, np.minimum(roi2, d))
        min_dist[y0:y1, x0:x1] = np.minimum(roi1, d)
    edge = min_dist2 - min_dist
    smooth = np.clip(min_dist / 30.0, 0, 1) * 0.6
    border = np.clip(1.0 - edge / 6.0, 0, 1) * 0.4
    return np.clip(smooth + border, 0, 1).astype(np.float32)

# === SYMBOL FACTORY BROKEN (4) ===
texture_glacier_crack = make_voronoi_texture_fn(num_points=40, edge_mode=True)

# --- Geometric Group ---
def texture_herringbone(shape, seed):
    """Herringbone — alternating V-shaped zigzag rows."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    block_h, block_w = 12, 24
    row = (yf / block_h).astype(int)
    x_shifted = xf + (row % 2) * (block_w // 2)
    lx = x_shifted % block_w
    ly = yf % block_h
    mid = block_w / 2.0
    v_line = np.abs(ly - (block_h / mid) * np.minimum(lx, block_w - lx))
    bone = np.clip(1.0 - v_line / 2.0, 0, 1)
    border = np.clip(1.0 - (yf % block_h) / 1.5, 0, 1) * 0.2
    return np.clip(bone + border, 0, 1)
def texture_argyle(shape, seed):
    """Argyle — overlapping diamonds with thin diagonal lines."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 48
    dy = np.abs((yf % cell) - cell / 2.0) / (cell / 2.0)
    dx = np.abs((xf % cell) - cell / 2.0) / (cell / 2.0)
    diamond = np.clip(1.0 - (dy + dx), 0, 1)
    diamond = np.clip(diamond * 2.5, 0, 1)
    d1 = np.abs((yf + xf) % cell - cell / 2.0)
    d2 = np.abs((yf - xf) % cell - cell / 2.0)
    line1 = (d1 < 1.5).astype(np.float32) * 0.6
    line2 = (d2 < 1.5).astype(np.float32) * 0.6
    return np.clip(diamond * 0.7 + line1 + line2, 0, 1)

def texture_greek_key(shape, seed):
    """Greek key — classic meander/labyrinth border pattern."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 32
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    half = cell / 2.0
    q = cell / 4.0
    border = ((ly < 2) | (ly > cell - 2) | (lx < 2) | (lx > cell - 2)).astype(np.float32)
    arm_top = ((ly > q - 1) & (ly < q + 1) & (lx > q)).astype(np.float32)
    arm_right = ((lx > cell - q - 1) & (lx < cell - q + 1) & (ly > q) & (ly < cell - q)).astype(np.float32)
    arm_bottom = ((ly > cell - q - 1) & (ly < cell - q + 1) & (lx < cell - q)).astype(np.float32)
    arm_left = ((lx > q - 1) & (lx < q + 1) & (ly > q) & (ly < half + 2)).astype(np.float32)
    return np.clip(border + arm_top + arm_right + arm_bottom + arm_left, 0, 1)


def texture_art_deco(shape, seed):
    """Art deco — repeating fan/arch pattern with radiating lines."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 64
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell * 0.95, cell / 2.0
    dy = ly - cy
    dx = lx - cx
    dist = np.sqrt(dy**2 + dx**2)
    angle = np.arctan2(dy, dx)
    arcs = (np.sin(dist * 0.35) > 0.5).astype(np.float32)
    rays = (np.sin(angle * 8) > 0.6).astype(np.float32)
    fan_mask = (dy < -2).astype(np.float32)
    arch = (dist < cell * 0.7).astype(np.float32)
    pattern = (arcs * 0.6 + rays * 0.5) * fan_mask * arch
    frame = ((ly < 2) | (ly > cell - 2) | (lx < 2) | (lx > cell - 2)).astype(np.float32) * 0.4
    return np.clip(pattern + frame, 0, 1)


def texture_tessellation(shape, seed):
    """Tessellation — hexagonal honeycomb tiling."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    size = 24.0
    row_h = size * np.sqrt(3)
    row = np.floor(yf / row_h)
    y_in_row = yf - row * row_h
    x_offset = xf + (row % 2) * (size * 1.5)
    col = np.floor(x_offset / (size * 3))
    x_in_col = x_offset - col * (size * 3)
    cx1, cy1 = size * 1.5, row_h / 2.0
    d1 = np.maximum(np.abs(x_in_col - cx1) * 1.15,
                     np.abs(x_in_col - cx1) * 0.577 + np.abs(y_in_row - cy1))
    edge = np.clip(1.0 - np.abs(d1 - size * 0.9) / 2.0, 0, 1)
    return edge
def texture_yin_yang(shape, seed):
    """Yin yang - classic taijitu symbol."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 56
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    r = cell * 0.42
    # Main circle
    circle = (dist < r).astype(np.float32)
    # Split: left vs right determined by S-curve
    s_curve_x = cx + np.sin(((ly - cy) / r) * np.pi) * r * 0.5
    yin = ((lx < s_curve_x) & (dist < r)).astype(np.float32)
    yang = ((lx >= s_curve_x) & (dist < r)).astype(np.float32)
    # Small dots (eyes)
    dot1_cy, dot1_cx = cy - r * 0.25, cx
    dot2_cy, dot2_cx = cy + r * 0.25, cx
    dot1 = (np.sqrt((ly - dot1_cy)**2 + (lx - dot1_cx)**2) < r * 0.12).astype(np.float32)
    dot2 = (np.sqrt((ly - dot2_cy)**2 + (lx - dot2_cx)**2) < r * 0.12).astype(np.float32)
    result = yin * 0.8 + yang * 0.2
    result = np.where(dot1 > 0, 0.2, result)  # dark dot in light
    result = np.where(dot2 > 0, 0.8, result)  # light dot in dark
    # Border ring
    border = np.clip(1.0 - np.abs(dist - r) / 2.0, 0, 1) * 0.5
    return np.clip(result + border, 0, 1).astype(np.float32)

# === DOT FACTORY BROKEN (2) ===

# --- Racing & Motorsport Group ---
def texture_checkered_flag(shape, seed):
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 16
    check = ((y.astype(int) // cell + x.astype(int) // cell) % 2).astype(np.float32)
    return check

def texture_racing_stripe(shape, seed):
    """Racing stripe — wide center stripe with thin flanking stripes."""
    h, w = shape
    y, x = _get_mgrid(shape)
    xf = x.astype(np.float32)
    center = w / 2.0
    main = np.clip(1.0 - np.abs(xf - center) / 12.0, 0, 1)
    flank1 = np.clip(1.0 - np.abs(xf - center - 24) / 4.0, 0, 1)
    flank2 = np.clip(1.0 - np.abs(xf - center + 24) / 4.0, 0, 1)
    return np.clip(main + flank1 * 0.7 + flank2 * 0.7, 0, 1)
def texture_starting_grid(shape, seed):
    """Starting grid — numbered box positions like race start."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell_h, cell_w = 48, 32
    ly = (y % cell_h).astype(np.float32)
    lx = (x % cell_w).astype(np.float32)
    border = ((ly < 2) | (ly > cell_h - 2) | (lx < 2) | (lx > cell_w - 2)).astype(np.float32)
    cy, cx = cell_h / 2.0, cell_w / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    marker = np.clip(1.0 - dist / 8.0, 0, 1) * 0.6
    return np.clip(border + marker, 0, 1)
def texture_tire_smoke(shape, seed):
    """Tire smoke — dense smoke cloud covering full canvas, thicker at bottom."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Layer 1: Ambient smoke haze — full canvas coverage
    haze = _multi_scale_noise(shape[:2], [16, 32, 64], [0.3, 0.4, 0.3], seed + 4)
    haze = (haze - haze.min()) / (haze.max() - haze.min() + 1e-8)
    rise_factor = np.clip(1.0 - yi / h, 0, 1)  # 1 at bottom, 0 at top
    out = haze * (0.08 + rise_factor * 0.12)  # haze stronger at bottom
    # Layer 2: Smoke plumes — wider, scaled to canvas
    for _ in range(30):
        cx = rng.uniform(-w * 0.05, w * 1.05)
        base_width = w * rng.uniform(0.04, 0.12)
        drift = rng.uniform(-0.3, 0.3)
        intensity = rng.uniform(0.25, 0.65)
        phase = rng.uniform(0, 2 * np.pi)
        rise = np.clip(1.0 - yi / h, 0, 1)
        width = base_width * (1.0 + (1.0 - rise) * 2.5)
        path_x = cx + (1.0 - rise) * drift * w * 0.3
        path_x += np.sin(yi * 0.03 + phase) * w * 0.03 * (1.0 - rise)
        path_x += np.sin(yi * 0.07 + phase * 2.1) * w * 0.015 * (1.0 - rise)
        dx = np.abs(xx - path_x)
        plume = np.clip(1.0 - dx / (width + 1), 0, 1) * rise ** 0.4
        out = np.maximum(out, plume * intensity)
    # Turbulent breakup texture
    nh, nw = max(1, h // 12 + 1), max(1, w // 12 + 1)
    turb = rng.rand(nh, nw).astype(np.float32)
    turb_map = np.repeat(np.repeat(turb, 12, 0), 12, 1)[:h, :w]
    out = out * (0.55 + turb_map * 0.6)
    return np.clip(out, 0, 1)

def texture_skid_marks(shape, seed):
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    for _ in range(int(20)):
        y0 = rng.randint(0, h)
        x0 = rng.randint(0, w)
        angle = rng.uniform(-0.2, 0.2)
        length = rng.randint(100, 500)
        width = rng.randint(3, 8)
        for t in range(length):
            yi = int(y0 + t * np.sin(angle + 1.5708))
            xi = int(x0 + t * np.cos(angle + 1.5708))
            if 0 <= yi < h and 0 <= xi < w:
                for dy in range(-width, width + 1):
                    yy = yi + dy
                    if 0 <= yy < h:
                        result[yy, xi] = max(result[yy, xi], rng.uniform(0.5, 1.0))
    return result

def texture_asphalt_texture(shape, seed):
    """Asphalt - granular surface with aggregate stones."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Multi-scale noise base
    base = _multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed) * 0.5 + 0.5
    # Aggregate stones (small bright spots)
    stones = np.zeros((h, w), dtype=np.float32)
    for _ in range(int(h * w * 0.003)):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        sr = rng.randint(1, 3)
        brightness = rng.uniform(0.5, 0.8)
        y1, y2 = max(0, sy - sr), min(h, sy + sr)
        x1, x2 = max(0, sx - sr), min(w, sx + sr)
        stones[y1:y2, x1:x2] = brightness
    return np.clip(base * 0.6 + stones * 0.4 + 0.1, 0, 1).astype(np.float32)
def texture_pit_lane_marks(shape, seed):
    """Pit lane - road markings with dashed center line and pit box lines."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Center dashed line
    center = np.clip(1.0 - np.abs(xf - w / 2.0) / 3.0, 0, 1)
    dashes = ((yf % 30) < 18).astype(np.float32)
    center_line = center * dashes * 0.8
    # Pit box markings (perpendicular lines)
    box_spacing = 64*scale
    box_line = np.clip(1.0 - np.abs(yf % box_spacing) / 2.0, 0, 1)
    # Edge lines
    edge_l = np.clip(1.0 - xf / 4.0, 0, 1) * 0.6
    edge_r = np.clip(1.0 - (w - 1 - xf) / 4.0, 0, 1) * 0.6
    return np.clip(center_line + box_line * 0.5 + edge_l + edge_r, 0, 1).astype(np.float32)
def texture_lap_counter(shape, seed):
    """Lap counter — segmented number display blocks."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 32
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    seg_w = cell * 0.6
    seg_h = cell * 0.08
    cx = cell / 2.0
    ht = ((ly > 2) & (ly < 2 + seg_h) & (lx > cx - seg_w/2) & (lx < cx + seg_w/2)).astype(np.float32)
    hm = ((ly > cell/2 - seg_h/2) & (ly < cell/2 + seg_h/2) & (lx > cx - seg_w/2) & (lx < cx + seg_w/2)).astype(np.float32)
    hb = ((ly > cell - 2 - seg_h) & (ly < cell - 2) & (lx > cx - seg_w/2) & (lx < cx + seg_w/2)).astype(np.float32)
    vlt = ((lx > cx - seg_w/2 - 1) & (lx < cx - seg_w/2 + seg_h) & (ly > 2) & (ly < cell/2)).astype(np.float32)
    vlb = ((lx > cx - seg_w/2 - 1) & (lx < cx - seg_w/2 + seg_h) & (ly > cell/2) & (ly < cell - 2)).astype(np.float32)
    vrt = ((lx > cx + seg_w/2 - seg_h) & (lx < cx + seg_w/2 + 1) & (ly > 2) & (ly < cell/2)).astype(np.float32)
    vrb = ((lx > cx + seg_w/2 - seg_h) & (lx < cx + seg_w/2 + 1) & (ly > cell/2) & (ly < cell - 2)).astype(np.float32)
    return np.clip(ht + hm + hb + vlt + vlb + vrt + vrb, 0, 1)
def texture_sponsor_fade(shape, seed):
    """Sponsor fade — block gradient panels like sponsor logo areas."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    block_w = 48
    col = (xf / block_w).astype(int)
    lx = (xf % block_w) / block_w
    panel = ((col % 2) == 0).astype(np.float32)
    fade = np.clip(1.0 - np.abs(lx - 0.5) * 3, 0, 1)
    return panel * fade * 0.8 + (1 - panel) * (1 - fade) * 0.3
def texture_rooster_tail(shape, seed):
    """Rooster tail - fan-shaped spray from bottom center."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed)
    # Fan from bottom center
    cy, cx = h * 0.95, w / 2.0
    angle = np.arctan2(cy - yf, xf - cx)
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    # Spray streaks
    streaks = np.sin(angle * 30 + dist * 0.05) * 0.5 + 0.5
    # Fade with distance and angle
    angle_mask = np.clip(1.0 - np.abs(angle) / 1.2, 0, 1)
    dist_fade = np.clip(dist / (h * 0.8), 0, 1) * angle_mask
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed) * 0.5 + 0.5
    return np.clip(streaks * dist_fade * 0.6 + noise * dist_fade * 0.4, 0, 1).astype(np.float32)
def texture_victory_confetti(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(200):
        cx, cy = rng.randint(0,w), rng.randint(0,h)
        cw, ch = rng.uniform(3,12), rng.uniform(8,25)
        angle = rng.uniform(0, np.pi)
        brightness = rng.uniform(0.5, 1.0)
        m = int(max(cw,ch))+2
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx, dy = lx-cx, ly-cy
        rdx = dx*np.cos(-angle)-dy*np.sin(-angle)
        rdy = dx*np.sin(-angle)+dy*np.cos(-angle)
        inside = (np.abs(rdx)<cw*0.5) & (np.abs(rdy)<ch*0.5)
        out[y0:y1,x0:x1] += inside.astype(np.float32)*brightness
    return np.clip(out, 0, 1)

def texture_trophy_laurel(shape, seed):
    """Trophy laurel — wreath of leaf shapes in oval arrangement."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 80
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    ring_r = cell * 0.35
    ring_dist = np.abs(dist - ring_r)
    num_leaves = 16
    leaf_angle = angle * num_leaves
    leaf = np.abs(np.sin(leaf_angle)) * np.clip(1.0 - ring_dist / 8.0, 0, 1)
    return np.clip(leaf * 1.5, 0, 1)
def texture_rpm_gauge(shape, seed):
    """RPM gauge - segmented arc gauge display."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 80
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    # Arc segments (upper half only)
    arc_mask = (angle < -0.3).astype(np.float32) * (angle > -np.pi + 0.3).astype(np.float32)
    arc = np.clip(1.0 - np.abs(dist - cell * 0.38) / 4.0, 0, 1) * arc_mask
    # Segment divisions
    seg = (np.abs(np.sin(angle * 5)) > 0.95).astype(np.float32) * arc_mask
    seg_line = seg * (dist > cell * 0.3).astype(np.float32) * (dist < cell * 0.45).astype(np.float32)
    return np.clip(arc * 0.7 + seg_line * 0.5, 0, 1).astype(np.float32)
def texture_finish_line(shape, seed):
    """Finish line - horizontal checkered band across the surface like a real start/finish line."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Repeating horizontal finish-line bands
    band_h = 40  # total band height
    band_spacing = 120  # space between bands
    full_period = band_h + band_spacing
    band_y = yf % full_period
    in_band = (band_y < band_h).astype(np.float32)
    # Checker within band: wider cells (landscape orientation like road markings)
    cell_w = 20  # wider than tall
    cell_h = int(band_h / 2)  # 2 rows of checkers per band
    check_x = (xf // cell_w).astype(int)
    check_y = (band_y // cell_h).astype(int)
    checker = ((check_x + check_y) % 2).astype(np.float32)
    return (checker * in_band).astype(np.float32)

# --- Racing Ghost Patterns (were in HTML catalog but had no Python backend) ---
def texture_aero_flow(shape, seed):
    """Aero flow - streamlined airflow lines around body."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Horizontal streamlines that curve around center obstacle
    cy, cx = h / 2.0, w * 0.3
    dist = np.sqrt((yf - cy)**2 + ((xf - cx) * 0.5)**2)
    deflection = np.clip(40 / (dist + 10), 0, 3)
    stream_y = yf + np.sign(yf - cy) * deflection * 5
    lines = np.sin(stream_y * np.pi / 8) * 0.5 + 0.5
    sharp = (lines > 0.6).astype(np.float32) * 0.7 + lines * 0.2
    return np.clip(sharp, 0, 1).astype(np.float32)
def texture_brake_dust(shape, seed):
    """Brake dust - radial spray of fine dark particles."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed)
    # Radial pattern from center
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    angle = np.arctan2(yf - cy, xf - cx)
    radial = np.clip(dist / (max(h, w) * 0.5), 0, 1)
    # Streaky radial pattern
    streaks = np.sin(angle * 20 + dist * 0.08) * 0.3
    noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed) * 0.5 + 0.5
    return np.clip(radial * 0.5 + streaks + noise * 0.3, 0, 1).astype(np.float32)

def texture_drift_marks(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(20):
        cx, cy = rng.randint(0,w), rng.randint(0,h)
        radius = rng.uniform(30, 120)
        arc_w = rng.uniform(2, 6)
        a_start = rng.uniform(0, 2*np.pi); a_span = rng.uniform(0.5, 2.0)
        m = int(radius + arc_w*3) + int(2*scale)
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dist = np.sqrt((lx-cx)**2+(ly-cy)**2)
        angle = np.arctan2(ly-cy, lx-cx)
        a_norm = ((angle - a_start) % (2*np.pi))
        in_arc = a_norm < a_span
        ring = np.exp(-((dist-radius)**2)/(2*arc_w**2))
        out[y0:y1,x0:x1] += ring * in_arc * rng.uniform(0.4, 0.9)
    return np.clip(out, 0, 1)

def texture_podium_stripe(shape, seed):
    """Podium stripes - 1st/2nd/3rd place stepped blocks."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell_w = 48
    cell_h = 64
    col = (xf / cell_w).astype(int) % 3
    ly = yf % cell_h
    # Step heights: 1st tallest, 2nd medium, 3rd shortest
    heights = np.where(col == 0, cell_h * 0.5,   # 2nd place
              np.where(col == 1, cell_h * 0.3,    # 1st place (tallest)
                       cell_h * 0.65))              # 3rd place
    podium = (ly > heights).astype(np.float32)
    # Add number markers in center
    border = np.clip(1.0 - np.abs(xf % cell_w - cell_w / 2) / (cell_w * 0.4), 0, 1)
    border_line = ((xf % cell_w < 2) | (xf % cell_w > cell_w - 2)).astype(np.float32) * 0.5
    return np.clip(podium * 0.7 + border * 0.1 + border_line, 0, 1).astype(np.float32)
def texture_rev_counter(shape, seed):
    """Rev counter - tachometer dial with tick marks."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 80
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    # Dial ring
    ring = np.clip(1.0 - np.abs(dist - cell * 0.4) / 2.0, 0, 1) * 0.5
    # Tick marks around dial
    tick_angle = angle % (np.pi / 6)
    ticks = np.clip(1.0 - tick_angle / 0.05, 0, 1) * (dist > cell * 0.32).astype(np.float32) * (dist < cell * 0.45).astype(np.float32)
    # Needle
    needle = np.clip(1.0 - np.abs(angle - 0.8) / 0.03, 0, 1) * np.clip(dist / (cell * 0.38), 0, 1)
    return np.clip(ring + ticks * 0.8 + needle, 0, 1).astype(np.float32)
def texture_speed_lines(shape, seed):
    """Speed lines - horizontal motion blur streaks, vectorized."""
    import numpy as np
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    for _ in range(80):
        sy = rng.randint(0, h)
        sx = rng.randint(0, w // 2)
        length = int(rng.randint(40, min(300, w)) * scale)
        thickness = max(1, int(rng.randint(1, 3) * scale))
        brightness = rng.uniform(0.4, 1.0)
        y0, y1 = max(0, sy), min(h, sy + thickness)
        x0, x1 = sx, min(w, sx + length)
        if y1<=y0 or x1<=x0: continue
        fade = np.linspace(1.0, 0.0, x1-x0, dtype=np.float32).reshape(1, -1)
        result[y0:y1, x0:x1] = np.maximum(result[y0:y1, x0:x1], brightness * fade)
    return result

def texture_track_map(shape, seed):
    """Track map — oval circuit outline with curves."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 96
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    ry, rx = cell * 0.35, cell * 0.42
    ellipse_dist = np.sqrt(((ly - cy) / ry)**2 + ((lx - cx) / rx)**2)
    track = np.clip(1.0 - np.abs(ellipse_dist - 1.0) * 8.0, 0, 1)
    return track
def texture_turbo_swirl(shape, seed):
    """Turbo swirl - turbine blade rotation pattern."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 80
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    # Curved blades (logarithmic spiral)
    blade_angle = angle + dist * 0.06
    blades = np.sin(blade_angle * 6) * 0.5 + 0.5
    # Sharpen blade edges
    sharp = (blades > 0.55).astype(np.float32) * 0.7
    # Center hub
    hub = np.clip(1.0 - dist / 8, 0, 1)
    mask = (dist < cell * 0.45).astype(np.float32)
    return np.clip((sharp + hub) * mask, 0, 1).astype(np.float32)

# === WAVE FACTORY REPLACEMENTS (8) ===
def texture_wind_tunnel(shape, seed):
    """Wind tunnel - parallel horizontal streamlines."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Evenly spaced horizontal lines
    spacing = 10*scale
    lines = np.sin(yf * np.pi / spacing) * 0.5 + 0.5
    sharp = (lines > 0.6).astype(np.float32) * 0.6
    # Arrow markers
    arrow_spacing = 60*scale
    arrow_x = xf % arrow_spacing
    arrow_y = yf % spacing - spacing / 2
    arrow = ((arrow_x > 25) & (arrow_x < 35) & (np.abs(arrow_y) < arrow_x - 25)).astype(np.float32) * 0.4
    return np.clip(sharp + arrow, 0, 1).astype(np.float32)

# === VORONOI FACTORY BROKEN (3) ===

# --- Textile & Fabric Group ---
def texture_denim(shape, seed):
    """Denim - diagonal twill weave."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    # 3/1 twill diagonal
    period = 4
    diag = (x + y * 3) % (period * 2)
    twill = (diag < period).astype(np.float32) * 0.3 + 0.3
    # Thread texture
    thread_h = np.sin(x * np.pi * 0.8) * 0.08
    thread_v = np.sin(y * np.pi * 0.8) * 0.08
    # Denim irregularity
    nh, nw = max(1, h // 4), max(1, w // 4)
    noise = rng.rand(nh, nw).astype(np.float32)
    nmap = np.repeat(np.repeat(noise, 4, axis=0), 4, axis=1)[:h, :w]
    return np.clip(twill + thread_h + thread_v + nmap * 0.15, 0, 1).astype(np.float32)
def texture_leather_grain(shape, seed):
    """Leather grain - pebbled leather surface."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Multi-scale noise for pebble texture
    base = _multi_scale_noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed) * 0.5 + 0.5
    # Sharpen pebble edges
    pebbles = np.clip(base * 1.5 - 0.25, 0, 1)
    # Add fine grain on top
    nh, nw = max(1, h // 2), max(1, w // 2)
    fine = rng.rand(nh, nw).astype(np.float32) * 0.15
    fine_map = np.repeat(np.repeat(fine, 2, axis=0), 2, axis=1)[:h, :w]
    return np.clip(pebbles * 0.8 + fine_map + 0.1, 0, 1).astype(np.float32)
def texture_quilted(shape, seed):
    """Quilted - puffy diamond padding with stitch lines."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 32
    # Diamond grid for stitch lines
    d1 = (xf + yf) % cell
    d2 = (xf - yf) % cell
    stitch1 = np.clip(1.0 - np.abs(d1) / 2.0, 0, 1)
    stitch2 = np.clip(1.0 - np.abs(d2) / 2.0, 0, 1)
    stitches = np.maximum(stitch1, stitch2) * 0.8
    # Puffy centers between stitches
    center1 = np.abs(d1 - cell / 2.0) / (cell / 2.0)
    center2 = np.abs(d2 - cell / 2.0) / (cell / 2.0)
    puff = (1.0 - np.maximum(center1, center2)) * 0.6
    return np.clip(np.maximum(stitches, puff) + 0.2, 0, 1).astype(np.float32)
def texture_velvet(shape, seed):
    """Velvet — soft nap texture with directional pile and subtle sheen variation."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xf = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Very fine fiber nap (tiny scale noise)
    nh, nw = max(1, h // 3 + 1), max(1, w // 3 + 1)
    fine = rng.rand(nh, nw).astype(np.float32)
    nap = np.repeat(np.repeat(fine, 3, 0), 3, 1)[:h, :w] * 0.2
    # Directional pile — subtle diagonal brushed direction
    pile = np.sin((xf + yf * 0.7) * 0.3) * 0.08 + 0.5
    # Sheen variation — larger scale light/dark areas from pile angle
    nh2, nw2 = max(1, h // 24 + 1), max(1, w // 24 + 1)
    sheen = rng.rand(nh2, nw2).astype(np.float32)
    sheen_map = np.repeat(np.repeat(sheen, 24, 0), 24, 1)[:h, :w] * 0.15
    return np.clip(pile + nap + sheen_map, 0, 1).astype(np.float32)
def texture_burlap(shape, seed):
    """Burlap - coarse woven fabric with visible thread crossing."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    spacing = 6*scale
    # Warp (vertical) and weft (horizontal) threads
    warp = np.sin(x * np.pi / spacing) * 0.5 + 0.5
    weft = np.sin(y * np.pi / spacing) * 0.5 + 0.5
    # Weave pattern - alternating over/under
    block = ((y // spacing + x // spacing) % 2).astype(np.float32)
    weave = np.where(block > 0.5, warp * 0.8 + weft * 0.2, warp * 0.2 + weft * 0.8)
    # Add coarse noise for burlap roughness
    nh, nw = max(1, h // 4), max(1, w // 4)
    noise_small = rng.rand(nh, nw).astype(np.float32)
    noise = np.repeat(np.repeat(noise_small, 4, axis=0), 4, axis=1)[:h, :w]
    return np.clip(weave * 0.8 + noise * 0.2, 0, 1).astype(np.float32)
def texture_lace(shape, seed):
    """Lace - delicate interlocking pattern with holes."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 32
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    # Scalloped edge circle
    scallop_r = cell * 0.35 + np.sin(angle * 8) * 3
    lace_ring = np.clip(1.0 - np.abs(dist - scallop_r) / 2.0, 0, 1)
    # Central hole
    hole = (dist < cell * 0.15).astype(np.float32)
    # Connecting threads between cells
    thread_h = np.clip(1.0 - np.abs(ly - cy) / 1.5, 0, 1) * ((lx < 3) | (lx > cell - 3)).astype(np.float32)
    thread_v = np.clip(1.0 - np.abs(lx - cx) / 1.5, 0, 1) * ((ly < 3) | (ly > cell - 3)).astype(np.float32)
    result = np.clip(lace_ring + thread_h + thread_v, 0, 1) * (1.0 - hole)
    return result.astype(np.float32)
def texture_silk_weave(shape, seed):
    """Silk weave - smooth satin with subtle sheen variation."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    # Long satin floats (8-harness)
    period = 16
    shift = (y * 2) % period
    pos = (x + shift) % period
    satin = np.sin(pos * np.pi / period) * 0.3 + 0.5
    # Smooth sheen gradient
    sheen = np.sin(y.astype(np.float32) * np.pi / 32) * 0.15
    return np.clip(satin + sheen, 0, 1).astype(np.float32)

# --- Tech & Digital Group ---
def texture_binary_code(shape, seed):
    """Binary code — columns of 0/1 bit blocks streaming down.
    Feature sizes scale with resolution so bits remain visible at 2048+."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Scale bit size: ~40 rows, ~32 columns for readable binary look
    bit_h = max(8, h // 40)
    bit_w = max(6, w // 32)
    rows = (h + bit_h - 1) // bit_h
    cols = (w + bit_w - 1) // bit_w
    bits = rng.randint(0, 2, (rows, cols)).astype(np.float32)
    result = np.repeat(np.repeat(bits, bit_h, axis=0), bit_w, axis=1)[:h, :w]
    y, x = _get_mgrid(shape)
    # Column gap lines between bit columns for readability
    gap_w = max(1, bit_w // 6)
    col_gap = ((x % bit_w) < gap_w).astype(np.float32) * 0.3
    # Row gap lines between bit rows for readability
    row_gap = ((y % bit_h) < max(1, bit_h // 8)).astype(np.float32) * 0.15
    return np.clip(result * 0.85 - col_gap - row_gap, 0, 1)
def texture_matrix_rain(shape, seed):
    """Matrix rain - vertical streaming columns with fade."""
    import numpy as np
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    col_w = 8
    num_cols = w // col_w
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    for c in range(num_cols):
        x0 = c * col_w
        x1 = min(x0 + col_w, w)
        cw = x1 - x0
        if cw <= 0: continue
        start = rng.randint(0, h)
        length = rng.randint(h // 4, h)
        brightness = rng.uniform(0.5, 1.0)
        dist_from_head = (yf - start) % h
        stream = np.clip(1.0 - dist_from_head / length, 0, 1) * brightness
        char_h = 6
        chars = rng.randint(0, 2, h // char_h + 1)
        char_pattern = np.repeat(chars, char_h)[:h].reshape(-1, 1).astype(np.float32)
        col_val = stream * (0.5 + char_pattern * 0.5)
        result[:, x0:x1] = np.maximum(result[:, x0:x1], np.broadcast_to(col_val, (h, cw)))
    return result

def texture_qr_code(shape, seed):
    """QR code - random black/white blocks with finder patterns.
    Cell size scales with resolution for recognizable QR look."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # ~25 cells across the shortest dimension for a dense QR look
    cell = max(8, min(h, w) // 25)
    gh, gw = max(1, h // cell + 1), max(1, w // cell + 1)
    blocks = (rng.rand(gh, gw) > 0.5).astype(np.float32)
    result = np.repeat(np.repeat(blocks, cell, axis=0), cell, axis=1)[:h, :w]
    y, x = _get_mgrid(shape)
    yi = y.astype(int)
    xi = x.astype(int)
    # Add thin grid lines between cells for QR authenticity
    grid_w = max(1, cell // 12)
    grid = ((yi % cell) < grid_w) | ((xi % cell) < grid_w)
    result = np.where(grid, 0.4, result)
    # Finder patterns in 3 corners (classic QR feature)
    for dy, dx in [(0, 0), (0, max(0, gw - 7)), (max(0, gh - 7), 0)]:
        py, px = dy * cell, dx * cell
        my = (yi >= py) & (yi < min(h, py + 7 * cell))
        mx = (xi >= px) & (xi < min(w, px + 7 * cell))
        fy = np.clip((yi - py) // cell, 0, 6)
        fx = np.clip((xi - px) // cell, 0, 6)
        outer = my & mx
        inner = outer & (fy >= 1) & (fy <= 5) & (fx >= 1) & (fx <= 5)
        core = outer & (fy >= 2) & (fy <= 4) & (fx >= 2) & (fx <= 4)
        result = np.where(outer, 1.0, result)
        result = np.where(inner, 0.0, result)
        result = np.where(core, 1.0, result)
    return result.astype(np.float32)
def texture_pixel_grid(shape, seed):
    """Pixel grid - blocky mosaic of random colored blocks.
    Cell size scales with resolution."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # ~20 pixel blocks across shortest dimension
    cell = max(8, min(h, w) // 20)
    gh, gw = max(1, h // cell), max(1, w // cell)
    # Random brightness per pixel block
    blocks = rng.rand(gh, gw).astype(np.float32)
    result = np.repeat(np.repeat(blocks, cell, axis=0), cell, axis=1)[:h, :w]
    # Add grid lines between blocks (scaled width) — crop to match result shape
    rh, rw = result.shape
    y, x = np.mgrid[0:rh, 0:rw]
    grid_w = max(1, cell // 10)
    border = ((y % cell < grid_w) | (x % cell < grid_w)).astype(np.float32) * 0.15
    return np.clip(result * 0.85 + border, 0, 1).astype(np.float32)
def texture_data_stream(shape, seed):
    """Data stream - flowing columns of binary/hex data.
    Column and character sizes scale with resolution."""
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    # Scale: ~50 columns across, ~60 character rows down
    col_width = max(10, w // 50)
    char_h = max(8, h // 60)
    num_cols = w // col_width + 1
    for c in range(num_cols):
        cx = c * col_width
        brightness = rng.uniform(0.3, 1.0)
        # Vertical fade: stream gets brighter toward head
        head_y = rng.randint(0, h)
        stream_len = rng.randint(h // 4, h)
        for yy in range(0, h, char_h):
            if rng.rand() > 0.25:
                y1 = max(0, yy)
                y2 = min(h, yy + char_h - max(1, char_h // 6))
                gap = max(1, col_width // 8)
                x1 = max(0, cx + gap)
                x2 = min(w, cx + col_width - gap)
                if y1 < y2 and x1 < x2:
                    # Distance from stream head for fade effect
                    dist = abs(yy - head_y) % h
                    fade = max(0.2, 1.0 - dist / stream_len) if dist < stream_len else 0.15
                    result[y1:y2, x1:x2] = brightness * fade * rng.uniform(0.5, 1.0)
    # Add subtle column separator lines
    y, x = _get_mgrid(shape)
    col_line = ((x % col_width) < max(1, col_width // 10)).astype(np.float32) * 0.12
    return np.clip(result + col_line, 0, 1).astype(np.float32)
def texture_wifi_waves(shape, seed):
    """WiFi waves — concentric arc signal waves from corner."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 64
    ly = yf % cell
    lx = xf % cell
    dist = np.sqrt(ly**2 + lx**2)
    rings = np.sin(dist * 0.3) * 0.5 + 0.5
    rings = (rings > 0.6).astype(np.float32)
    arc_mask = (dist < cell * 0.9).astype(np.float32) * (dist > 5).astype(np.float32)
    return rings * arc_mask
def texture_glitch_scan(shape, seed):
    """Glitch scanlines - horizontal scan lines with random displacement.
    Feature sizes scale with resolution."""
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    y, x = _get_mgrid(shape)
    # Scanlines: period scales with height (~128 visible bands)
    scan_period = max(4, h // 128)
    scan_on = max(1, scan_period // 2)
    scanlines = (y % scan_period < scan_on).astype(np.float32) * 0.3
    # Glitch blocks: larger and more numerous at higher res
    num_glitches = max(30, h // 20)
    for _ in range(num_glitches):
        gy = rng.randint(0, h)
        block_h = rng.randint(max(2, h // 300), max(4, h // 80))
        gx = rng.randint(0, w)
        block_w = rng.randint(max(20, w // 40), max(50, w // 5))
        brightness = rng.uniform(0.4, 1.0)
        y1, y2 = max(0, gy), min(h, gy + block_h)
        x1, x2 = max(0, gx), min(w, gx + block_w)
        result[y1:y2, x1:x2] = brightness
    return np.clip(scanlines + result * 0.7, 0, 1).astype(np.float32)

# --- Weather & Elements Group ---
def texture_tornado(shape, seed):
    """Tornado - funnel vortex narrowing downward."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Funnel narrows toward bottom
    cx = w / 2.0
    funnel_width = (1.0 - yf / h) * w * 0.4 + 10
    x_dist = np.abs(xf - cx)
    funnel = np.clip(1.0 - x_dist / funnel_width, 0, 1)
    # Spiral rotation inside funnel
    angle = np.arctan2(yf - h / 2, xf - cx)
    spiral = np.sin(angle * 8 + yf * 0.05) * 0.3
    return np.clip(funnel * 0.6 + spiral * funnel + 0.1, 0, 1).astype(np.float32)
def texture_sandstorm(shape, seed):
    """Sandstorm — dense blowing sand with full-canvas dust haze and wind streaks."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Layer 1: Ambient dust haze — full canvas coverage
    dust = _multi_scale_noise(shape[:2], [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 5)
    dust = (dust - dust.min()) / (dust.max() - dust.min() + 1e-8)
    out = dust * 0.20  # visible dust haze everywhere
    # Layer 2: Wind streaks — thicker, more numerous
    for _ in range(70):
        sy = rng.uniform(0, h)
        thickness = h * rng.uniform(0.005, 0.02)
        phase = rng.uniform(0, 2 * np.pi)
        brightness = rng.uniform(0.25, 0.65)
        wave_y = sy + np.sin(xx * 0.02 + phase) * h * 0.01 + np.sin(xx * 0.05 + phase * 1.3) * h * 0.006
        dist = np.abs(yi - wave_y)
        streak = np.clip(1.0 - dist / (thickness + 1), 0, 1) * brightness
        out = np.maximum(out, streak)
    # Layer 3: Suspended sand particles
    n_particles = max(200, int(h * w / 800))
    for _ in range(n_particles):
        py, px = rng.randint(0, h), rng.randint(0, w)
        pr = rng.uniform(1, 3)
        pb = rng.uniform(0.3, 0.7)
        r = int(pr) + 1
        y0, y1 = max(0, py - r), min(h, py + r)
        x0, x1 = max(0, px - r), min(w, px + r)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        d = np.sqrt((ly - py) ** 2 + (lx - px) ** 2)
        grain = np.clip(1.0 - d / pr, 0, 1) * pb
        np.maximum(out[y0:y1, x0:x1], grain, out=out[y0:y1, x0:x1])
    return np.clip(out, 0, 1)
def texture_hailstorm(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(150):
        cy, cx = rng.randint(0,h), rng.randint(0,w)
        r = rng.uniform(2, 7) * scale; depth = rng.uniform(0.3, 0.9)
        m = int(r)+2
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dist = np.sqrt((ly-cy)**2+(lx-cx)**2)
        dent = np.clip(1.0-dist/r, 0, 1)*depth
        np.maximum(out[y0:y1,x0:x1], dent, out=out[y0:y1,x0:x1])
    return out.astype(np.float32)

def texture_aurora_bands(shape, seed):
    """Aurora bands — flowing curtain-like bands covering full canvas with shimmer."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Layer 1: Ambient atmospheric shimmer — full canvas coverage
    shimmer = _multi_scale_noise(shape[:2], [16, 32, 64], [0.3, 0.4, 0.3], seed + 6)
    shimmer = (shimmer - shimmer.min()) / (shimmer.max() - shimmer.min() + 1e-8)
    out = shimmer * 0.10
    # Layer 2: Flowing curtain bands — more bands with wider gaussian spread
    for _ in range(12):
        base_y = rng.uniform(h * 0.05, h * 0.95)
        band_width = h * rng.uniform(0.03, 0.10)
        intensity = rng.uniform(0.3, 0.75)
        phase1 = rng.uniform(0, 2 * np.pi)
        phase2 = rng.uniform(0, 2 * np.pi)
        freq1 = rng.uniform(0.01, 0.03)
        freq2 = rng.uniform(0.025, 0.06)
        path_y = base_y + np.sin(xx * freq1 + phase1) * h * 0.05
        path_y += np.sin(xx * freq2 + phase2) * h * 0.025
        dist = np.abs(yi - path_y)
        band = np.exp(-(dist ** 2) / (2 * band_width ** 2)) * intensity
        rays = np.abs(np.sin(xx * 0.15 + phase1)) * 0.4 + 0.6
        band *= rays
        out = np.maximum(out, band)
    return np.clip(out, 0, 1)
def texture_solar_flare(shape, seed):
    """Solar flare - solar prominences arcing from surface."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    angle = np.arctan2(yf - cy, xf - cx)
    # Sun disk
    sun = np.clip(1.0 - dist / 50, 0, 1) * 0.8
    # Flare prominences (irregular radial extensions)
    flare_r = 50 + np.sin(angle * 7) * 20 + np.sin(angle * 13) * 10
    flare = np.clip(1.0 - np.abs(dist - flare_r) / 15, 0, 1) * 0.6
    # Corona glow
    corona = np.clip(1.0 - (dist - 45) / 60, 0, 1) * 0.3 * (dist > 40).astype(np.float32)
    return np.clip(sun + flare + corona, 0, 1).astype(np.float32)
def texture_nitro_burst(shape, seed):
    """Nitro burst - explosive radial burst lines."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    angle = np.arctan2(yf - cy, xf - cx)
    # Sharp radial burst rays
    rays = (np.sin(angle * 24) > 0.3).astype(np.float32)
    # Center explosion
    center = np.clip(1.0 - dist / 40, 0, 1)
    # Diminish with distance
    fade = np.clip(1.0 - dist / (max(h, w) * 0.45), 0, 1)
    return np.clip(rays * fade * 0.7 + center, 0, 1).astype(np.float32)

# --- Artistic & Cultural Group ---
texture_fleur_de_lis = make_symbol_grid_fn(_fleur_symbol, cell_size=48)
def texture_tribal_flame(shape, seed):
    """Tribal flame - stylized tribal flame licks."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed)
    # Multiple flame tongues rising from bottom
    result = np.zeros((h, w), dtype=np.float32)
    cx = w / 2.0
    # Tribal style: sharp angular flames
    for i in range(5):
        offset = (i - 2) * w * 0.15
        flame_cx = cx + offset
        # Flame narrows upward
        flame_width = (1.0 - yf / h) * 30 + 3
        dx = np.abs(xf - flame_cx)
        flame = np.clip(1.0 - dx / flame_width, 0, 1)
        # Pointed tip
        tip_y = h * (0.2 + abs(i - 2) * 0.1)
        height_mask = np.clip((h - yf) / (h - tip_y), 0, 1)
        result = np.maximum(result, flame * height_mask)
    return np.clip(result, 0, 1).astype(np.float32)
def texture_japanese_wave(shape, seed):
    """Japanese wave - Hokusai great wave curling crests."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Large rolling wave shape
    wave_period = 80
    wave_y = np.sin(xf * np.pi * 2 / wave_period) * 20
    wave_body = np.clip(1.0 - np.abs(yf - h * 0.5 - wave_y) / 25, 0, 1)
    # Curling crest detail
    crest_x = (xf % wave_period) / wave_period
    crest_y = yf - (h * 0.5 + wave_y)
    curl = np.clip(1.0 - np.sqrt(crest_x**2 + (crest_y / 15)**2) / 0.3, 0, 1)
    curl_mask = (crest_y < 0).astype(np.float32) * (crest_x < 0.3).astype(np.float32)
    # Foam texture
    foam = np.sin(xf * 0.5 + yf * 0.3) * 0.15 * wave_body
    return np.clip(wave_body * 0.6 + curl * curl_mask * 0.4 + foam, 0, 1).astype(np.float32)
def texture_aztec(shape, seed):
    """Aztec - stepped geometric pyramid motif."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 48
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    cy, cx = cell / 2.0, cell / 2.0
    # Chebyshev distance creates diamond/step shapes
    dist = np.maximum(np.abs(ly - cy), np.abs(lx - cx))
    # Create stepped rings
    steps = np.floor(dist / 4.0) * 4.0
    ring = np.abs(dist - steps) / 4.0
    # Add diagonal accent lines
    diag = np.abs((ly - cy) - (lx - cx))
    diag2 = np.abs((ly - cy) + (lx - cx))
    accent = np.clip(1.0 - np.minimum(diag, diag2) / 2.0, 0, 1) * 0.3
    result = np.clip(1.0 - ring + accent, 0, 1)
    return result.astype(np.float32)
def texture_mandala(shape, seed):
    """Mandala - symmetric radial pattern with rings and petals."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 96
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    # Concentric rings
    rings = np.sin(dist * 0.4) * 0.5 + 0.5
    # Petal symmetry (8-fold)
    petals = np.abs(np.cos(angle * 4)) * np.clip(1.0 - np.abs(dist - cell * 0.3) / 8, 0, 1)
    inner_petals = np.abs(np.cos(angle * 6 + 0.3)) * np.clip(1.0 - np.abs(dist - cell * 0.18) / 5, 0, 1)
    center = np.clip(1.0 - dist / 8, 0, 1)
    return np.clip(rings * 0.3 + petals * 0.5 + inner_petals * 0.4 + center, 0, 1).astype(np.float32)
def texture_paisley(shape, seed):
    """Paisley - teardrop/mango shaped motifs."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 48*scale
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell * 0.4, cell / 2.0
    # Teardrop shape: circle that tapers to point
    dy = ly - cy
    dx = lx - cx
    dist = np.sqrt(dy**2 + dx**2)
    angle = np.arctan2(dy, dx)
    # Teardrop: radius varies with angle
    tear_r = cell * 0.25 * (1.0 + 0.5 * np.cos(angle - np.pi / 2))
    tear = np.clip(1.0 - (dist - tear_r * 0.8) / 3.0, 0, 1) * (dist < tear_r).astype(np.float32)
    # Inner concentric rings
    rings = np.sin(dist * 0.8) * 0.3 * (dist < tear_r * 0.7).astype(np.float32)
    return np.clip(tear * 0.7 + np.abs(rings), 0, 1).astype(np.float32)
def texture_steampunk_gears(shape, seed):
    """Steampunk gears - interlocking gear teeth."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 64
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    # Gear body
    gear_r = cell * 0.35
    teeth_r = gear_r + 4 * (np.sin(angle * 12) > 0).astype(np.float32)
    gear = (dist < teeth_r).astype(np.float32)
    # Spoke holes
    spoke_dist = np.abs(dist - cell * 0.2)
    spokes = (spoke_dist < 3).astype(np.float32) * (np.abs(np.sin(angle * 3)) > 0.7).astype(np.float32)
    # Center axle
    axle = (dist < 6).astype(np.float32)
    hub_ring = np.clip(1.0 - np.abs(dist - 8) / 2, 0, 1)
    return np.clip(gear * 0.6 + spokes * 0.3 + axle + hub_ring * 0.4, 0, 1).astype(np.float32)
def texture_norse_rune(shape, seed):
    """Norse rune - angular runic letter symbols."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 40
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    # Vertical stave (main stroke)
    stave = np.clip(1.0 - np.abs(lx - cx) / 2.5, 0, 1)
    stave_mask = (ly > cell * 0.1).astype(np.float32) * (ly < cell * 0.9).astype(np.float32)
    # Angular branches (like Algiz rune)
    branch1 = np.clip(1.0 - np.abs((lx - cx) - (ly - cy) * 0.6) / 2.0, 0, 1)
    branch2 = np.clip(1.0 - np.abs((lx - cx) + (ly - cy) * 0.6) / 2.0, 0, 1)
    branch_mask = (ly < cy).astype(np.float32) * (ly > cell * 0.15).astype(np.float32)
    branches = np.maximum(branch1, branch2) * branch_mask
    return np.clip(stave * stave_mask + branches * 0.8, 0, 1).astype(np.float32)

# --- Damage & Wear Group ---
def texture_bullet_holes(shape, seed):
    """Bullet holes — impact craters with raised rim and dark center."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    # Scatter bullet impacts
    for _ in range(40):
        cy, cx = rng.randint(0, h), rng.randint(0, w)
        r_outer = rng.uniform(4, 10)  # crater outer radius
        r_inner = r_outer * 0.4  # dark center hole
        depth = rng.uniform(0.5, 1.0)
        m = int(r_outer) + 4
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - cy) ** 2 + (lx - cx) ** 2)
        # Raised rim ring
        rim = np.clip(1.0 - np.abs(dist - r_outer * 0.75) / 2.5, 0, 1) * depth
        # Dark center hole
        hole = np.clip(1.0 - dist / r_inner, 0, 1) * depth * 0.8
        # Radial cracks extending outward
        angle = np.arctan2(ly - cy, lx - cx)
        n_cracks = rng.randint(3, 6)
        crack_val = np.zeros_like(dist)
        for ci in range(n_cracks):
            ca = rng.uniform(0, 2 * np.pi)
            crack_dist = np.abs(np.sin(angle - ca)) * dist
            crack = np.clip(1.0 - crack_dist / 1.5, 0, 1) * np.clip(1.0 - (dist - r_outer) / 8, 0, 1)
            crack *= (dist > r_outer * 0.6).astype(np.float32)
            crack_val = np.maximum(crack_val, crack * 0.4)
        impact = np.maximum(rim, np.maximum(hole, crack_val))
        np.maximum(out[y0:y1, x0:x1], impact, out=out[y0:y1, x0:x1])
    return out
def texture_shrapnel(shape, seed):
    """Shrapnel — jagged torn metal fragments scattered across surface."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(60):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        # Irregular jagged polygon fragment
        n_verts = rng.randint(4, 8)
        angles = np.sort(rng.uniform(0, 2 * np.pi, n_verts))
        radii = rng.uniform(3, 15, n_verts)
        brightness = rng.uniform(0.4, 1.0)
        max_r = int(np.max(radii)) + 3
        y0, y1 = max(0, cy - max_r), min(h, cy + max_r)
        x0, x1 = max(0, cx - max_r), min(w, cx + max_r)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        pa = np.arctan2(ly - cy, lx - cx)
        pd = np.sqrt((ly - cy) ** 2 + (lx - cx) ** 2)
        # Interpolate radius at each angle
        frag_r = np.zeros_like(pa)
        for vi in range(n_verts):
            a1 = angles[vi]
            a2 = angles[(vi + 1) % n_verts]
            r1 = radii[vi]
            r2 = radii[(vi + 1) % n_verts]
            if a2 < a1:
                mask = (pa >= a1) | (pa < a2)
                span = (2 * np.pi - a1 + a2)
                t = np.where(pa >= a1, (pa - a1) / span, (pa + 2 * np.pi - a1) / span)
            else:
                mask = (pa >= a1) & (pa < a2)
                t = (pa - a1) / (a2 - a1 + 1e-8)
            frag_r = np.where(mask, r1 + (r2 - r1) * t, frag_r)
        inside = (pd < frag_r).astype(np.float32)
        edge = np.clip(1.0 - np.abs(pd - frag_r) / 1.5, 0, 1) * 0.5
        frag = np.maximum(inside * brightness * 0.7, edge * brightness)
        np.maximum(out[y0:y1, x0:x1], frag, out=out[y0:y1, x0:x1])
    return out
def texture_road_rash(shape, seed):
    """Road rash - scraped/abraded surface with directional scratches."""
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.ones((h, w), dtype=np.float32) * 0.3
    # Directional scratches (mostly horizontal)
    for _ in range(60):
        sy = rng.randint(0, h)
        sx = rng.randint(0, w)
        length = rng.randint(30, 200)
        angle = rng.uniform(-0.15, 0.15)  # mostly horizontal
        depth = rng.uniform(0.3, 0.9)
        for t in range(length):
            yi = int(sy + t * np.sin(angle))
            xi = int(sx + t * np.cos(angle))
            if 0 <= yi < h and 0 <= xi < w:
                for dy in range(-1, 2):
                    yy = yi + dy
                    if 0 <= yy < h:
                        result[yy, xi] = max(result[yy, xi], depth)
    # Overall noise for rough surface
    nh, nw = max(1, h // 4), max(1, w // 4)
    noise = rng.rand(nh, nw).astype(np.float32)
    nmap = np.repeat(np.repeat(noise, 4, axis=0), 4, axis=1)[:h, :w]
    return np.clip(result + nmap * 0.2, 0, 1).astype(np.float32)
def texture_rust_bloom(shape, seed):
    """Rust bloom — organic rust patches with rough edges and pitting."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    # Scatter rust patches of varying sizes
    for _ in range(35):
        cy, cx = rng.randint(0, h), rng.randint(0, w)
        base_r = rng.uniform(10, 45)
        intensity = rng.uniform(0.4, 0.9)
        m = int(base_r * 1.3) + 2
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - cy) ** 2 + (lx - cx) ** 2)
        angle = np.arctan2(ly - cy, lx - cx)
        # Irregular blob edge using harmonic distortion
        edge_r = base_r * (1.0 + 0.3 * np.sin(angle * 3 + rng.uniform(0, 6))
                           + 0.15 * np.sin(angle * 7 + rng.uniform(0, 6))
                           + 0.1 * np.sin(angle * 11 + rng.uniform(0, 6)))
        blob = np.clip(1.0 - dist / edge_r, 0, 1)
        # Rough interior pitting
        pit_scale = max(1, int(base_r / 4))
        py, px = (y1 - y0 + pit_scale - 1) // pit_scale, (x1 - x0 + pit_scale - 1) // pit_scale
        pits = rng.rand(max(1, py), max(1, px)).astype(np.float32)
        pit_map = np.repeat(np.repeat(pits, pit_scale, 0), pit_scale, 1)[:y1 - y0, :x1 - x0]
        rust = blob * (0.5 + pit_map * 0.5) * intensity
        np.maximum(out[y0:y1, x0:x1], rust, out=out[y0:y1, x0:x1])
    return np.clip(out, 0, 1)
def texture_peeling_paint(shape, seed):
    """Peeling paint — curling flakes lifting off surface with exposed underlayer."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    # Generate flake patches
    for _ in range(45):
        cy, cx = rng.randint(0, h), rng.randint(0, w)
        flake_r = rng.uniform(8, 35)
        curl_dir = rng.uniform(0, 2 * np.pi)  # direction paint curls
        depth = rng.uniform(0.4, 0.9)
        m = int(flake_r * 1.3) + 2
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - cy) ** 2 + (lx - cx) ** 2)
        angle = np.arctan2(ly - cy, lx - cx)
        # Irregular flake shape
        edge_r = flake_r * (1.0 + 0.25 * np.sin(angle * 5 + rng.uniform(0, 6))
                            + 0.15 * np.sin(angle * 9 + rng.uniform(0, 6)))
        inside = (dist < edge_r).astype(np.float32)
        # Curl-up effect: one side lifts (bright edge = curled lip)
        curl_proj = np.cos(angle - curl_dir)  # how aligned with curl direction
        curl = np.clip(curl_proj * 0.5 + 0.5, 0, 1)  # 0-1: back to front
        curled_edge = np.clip(1.0 - np.abs(dist - edge_r * 0.85) / 3.0, 0, 1) * curl * 0.8
        # Exposed underlayer (rough texture where paint is gone)
        exposed = inside * depth * 0.5
        flake = np.maximum(exposed, curled_edge * depth)
        # Sharp boundary edge
        boundary = np.clip(1.0 - np.abs(dist - edge_r) / 1.5, 0, 1) * inside * 0.6
        flake = np.maximum(flake, boundary)
        np.maximum(out[y0:y1, x0:x1], flake, out=out[y0:y1, x0:x1])
    return np.clip(out, 0, 1)
def texture_g_force(shape, seed):
    """G-force - radial acceleration lines from center."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    angle = np.arctan2(yf - cy, xf - cx)
    # Radial streaks
    streaks = np.sin(angle * 40) * 0.5 + 0.5
    # Intensity increases outward
    intensity = np.clip(dist / (max(h, w) * 0.4), 0, 1)
    # Concentric pressure waves
    waves = np.sin(dist * 0.15) * 0.2 * intensity
    return np.clip(streaks * intensity * 0.6 + waves + 0.1, 0, 1).astype(np.float32)
def texture_spark_scatter(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(120):
        cy, cx = rng.randint(0,h), rng.randint(0,w)
        brightness = rng.uniform(0.5, 1.0)
        sr = 3.0*scale; lr = 6.0*scale
        m = int(lr)+2
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dist = np.sqrt((ly-cy)**2+(lx-cx)**2)
        angle = np.arctan2(ly-cy, lx-cx)
        star = np.clip(1.0-dist/sr,0,1) + np.clip(1.0-dist/lr,0,1)*(np.abs(np.sin(angle*4))>0.8).astype(np.float32)*0.5
        np.maximum(out[y0:y1,x0:x1], star*brightness, out=out[y0:y1,x0:x1])
    return out.astype(np.float32)

# --- Gothic & Dark Group ---
def texture_gothic_cross(shape, seed):
    """Gothic cross - ornate pointed cross with flared ends."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 48
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    cy, cx = cell / 2.0, cell / 2.0
    dy = ly - cy
    dx = lx - cx
    # Cross arms with flared ends
    arm_w = 4.0
    v_arm = (np.abs(dx) < arm_w + np.abs(dy) * 0.15).astype(np.float32) * (np.abs(dy) < cell * 0.4).astype(np.float32)
    h_arm = (np.abs(dy) < arm_w + np.abs(dx) * 0.15).astype(np.float32) * (np.abs(dx) < cell * 0.35).astype(np.float32)
    cross = np.maximum(v_arm, h_arm)
    # Pointed ends
    top_point = np.clip(1.0 - np.abs(dx) / (3.0 + (cy - ly) * 0.3), 0, 1) * (ly < cy - cell * 0.3).astype(np.float32)
    return np.clip(cross + top_point * 0.5, 0, 1).astype(np.float32)
def texture_iron_cross(shape, seed):
    """Iron cross - flared arm military cross."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 48
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    cy, cx = cell / 2.0, cell / 2.0
    dy = np.abs(ly - cy)
    dx = np.abs(lx - cx)
    # Arms that narrow at center and widen at ends
    arm_w_center = 3.0
    arm_w_end = 8.0
    # Vertical arm
    v_dist = dy / (cell * 0.4)
    v_width = arm_w_center + (arm_w_end - arm_w_center) * v_dist
    v_arm = (dx < v_width).astype(np.float32) * (dy < cell * 0.4).astype(np.float32)
    # Horizontal arm
    h_dist = dx / (cell * 0.35)
    h_width = arm_w_center + (arm_w_end - arm_w_center) * h_dist
    h_arm = (dy < h_width).astype(np.float32) * (dx < cell * 0.35).astype(np.float32)
    return np.maximum(v_arm, h_arm).astype(np.float32)

def texture_skull_wings(shape, seed):
    """Affliction-style winged skull."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 64
    ly = y % cell
    lx = x % cell
    skull = _skull_simple(ly, lx, cell)
    # Add wing-like extensions
    cx = cell / 2
    wing_l = np.clip(1.0 - np.abs(lx - cx * 0.3) / (cell * 0.15), 0, 1)
    wing_r = np.clip(1.0 - np.abs(lx - cx * 1.7) / (cell * 0.15), 0, 1)
    wing_mask = ((ly > cell * 0.3) & (ly < cell * 0.6)).astype(np.float32)
    wings = (wing_l + wing_r) * wing_mask * 0.7
    return np.clip(skull + wings, 0, 1)

def texture_gothic_scroll(shape, seed):
    """Gothic scroll - ornate S-curve scrollwork."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 64*scale
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    # S-curve scroll using sine modulated radius
    angle = np.arctan2(ly - cy, lx - cx)
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    scroll_r = cell * 0.3 + np.sin(angle * 2) * cell * 0.12
    scroll = np.clip(1.0 - np.abs(dist - scroll_r) / 3.0, 0, 1)
    # Inner filigree spiral
    inner_r = cell * 0.15 + np.sin(angle * 3 + 1) * cell * 0.06
    inner = np.clip(1.0 - np.abs(dist - inner_r) / 2.0, 0, 1) * 0.6
    return np.clip(scroll + inner, 0, 1).astype(np.float32)
def texture_thorn_vine(shape, seed):
    """Thorn vine - sinuous vine with sharp thorns."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Sinuous vine path
    vine_x = w / 2.0 + np.sin(yf * np.pi / 40) * 30
    vine = np.clip(1.0 - np.abs(xf - vine_x) / 4.0, 0, 1)
    # Thorns at regular intervals
    thorn_spacing = 16*scale
    thorn_y = (yf % thorn_spacing)
    side = np.where((yf // thorn_spacing) % 2 == 0, 1.0, -1.0)
    thorn_tip_x = vine_x + side * 12
    thorn_base = (thorn_y < 6).astype(np.float32)
    thorn_dx = xf - vine_x
    thorn_shape = np.clip(1.0 - np.abs(thorn_dx - side * thorn_y * 2) / 2.0, 0, 1) * thorn_base
    return np.clip(vine + thorn_shape * 0.7, 0, 1).astype(np.float32)
texture_pentagram = make_symbol_grid_fn(_pentagram_symbol, cell_size=56)

# --- Medical & Science Group ---
def texture_ekg(shape, seed):
    """EKG heartbeat line — THE SHOKKER SIGNATURE PATTERN."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # EKG waveform
    period = 120
    phase = (x % period) / period
    # Flat → P wave → flat → QRS spike → flat → T wave → flat
    ekg = np.zeros_like(phase)
    ekg = np.where((phase > 0.1) & (phase < 0.2), np.sin((phase - 0.1) / 0.1 * np.pi) * 0.3, ekg)
    ekg = np.where((phase > 0.3) & (phase < 0.35), -0.2, ekg)
    ekg = np.where((phase > 0.35) & (phase < 0.4), 1.0, ekg)
    ekg = np.where((phase > 0.4) & (phase < 0.45), -0.4, ekg)
    ekg = np.where((phase > 0.55) & (phase < 0.7), np.sin((phase - 0.55) / 0.15 * np.pi) * 0.4, ekg)
    # Map to line: intensity falls off with distance from center
    center_y = h / 2 + ekg * h * 0.15
    dist_from_line = np.abs(y - center_y)
    line_width = 3.0
    return np.clip(1.0 - dist_from_line / line_width, 0, 1)

def texture_dna_helix(shape, seed):
    """DNA helix - double helix structure with rungs."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cx = w / 2.0
    period = 40
    # Two helical strands
    strand1_x = cx + np.sin(yf * np.pi * 2 / period) * 20
    strand2_x = cx - np.sin(yf * np.pi * 2 / period) * 20
    s1 = np.clip(1.0 - np.abs(xf - strand1_x) / 3.0, 0, 1)
    s2 = np.clip(1.0 - np.abs(xf - strand2_x) / 3.0, 0, 1)
    # Connecting rungs every ~10px
    rung_mask = (yf % 10 < 2).astype(np.float32)
    rung_x_min = np.minimum(strand1_x, strand2_x)
    rung_x_max = np.maximum(strand1_x, strand2_x)
    rung = ((xf > rung_x_min) & (xf < rung_x_max)).astype(np.float32) * rung_mask * 0.5
    return np.clip(s1 + s2 + rung, 0, 1).astype(np.float32)
def texture_molecular(shape, seed):
    """Molecular — atom spheres connected by bond lines in a lattice."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    # Generate atom positions on a jittered grid
    spacing = 28
    atoms = []
    for gy in range(0, h + spacing, spacing):
        for gx in range(0, w + spacing, spacing):
            ay = gy + rng.randint(-5, 6)
            ax = gx + rng.randint(-5, 6)
            ar = rng.uniform(4, 7)  # atom radius
            atoms.append((ay, ax, ar))
    # Draw bonds between nearby atoms
    for i, (ay1, ax1, _) in enumerate(atoms):
        for j in range(i + 1, min(i + 8, len(atoms))):
            ay2, ax2, _ = atoms[j]
            d = np.sqrt((ay1 - ay2) ** 2 + (ax1 - ax2) ** 2)
            if d > spacing * 1.6 or d < 5:
                continue
            # Draw bond line
            bond_len = int(d) + 1
            for t_idx in range(bond_len):
                t = t_idx / max(1, bond_len - 1)
                by = int(ay1 + (ay2 - ay1) * t)
                bx = int(ax1 + (ax2 - ax1) * t)
                bw = 1
                y0, y1_b = max(0, by - bw), min(h, by + bw + 1)
                x0, x1_b = max(0, bx - bw), min(w, bx + bw + 1)
                if y1_b > y0 and x1_b > x0:
                    out[y0:y1_b, x0:x1_b] = np.maximum(out[y0:y1_b, x0:x1_b], 0.45)
    # Draw atoms (spheres) on top of bonds
    for ay, ax, ar in atoms:
        m = int(ar) + 2
        y0, y1 = max(0, ay - m), min(h, ay + m)
        x0, x1 = max(0, ax - m), min(w, ax + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - ay) ** 2 + (lx - ax) ** 2)
        sphere = np.clip(1.0 - dist / ar, 0, 1) ** 0.6
        np.maximum(out[y0:y1, x0:x1], sphere, out=out[y0:y1, x0:x1])
    return np.clip(out, 0, 1)
def texture_atomic_orbital(shape, seed):
    """Atomic orbital - electron cloud rings scaled to resolution."""
    import numpy as np
    h, w = shape[:2] if len(shape) > 2 else shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xf = np.arange(w, dtype=np.float32).reshape(1, -1)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    angle = np.arctan2(yf - cy, xf - cx)
    r1, r2, r3 = 30*scale, 60*scale, 95*scale
    ring1 = np.clip(1.0 - np.abs(dist - r1) / (4.0*scale), 0, 1)
    ring2 = np.clip(1.0 - np.abs(dist - r2) / (5.0*scale), 0, 1)
    ring3 = np.clip(1.0 - np.abs(dist - r3) / (6.0*scale), 0, 1)
    nucleus = np.clip(1.0 - dist / (10.0*scale), 0, 1)
    lobe = np.abs(np.cos(angle * 2)) * np.clip(1.0 - np.abs(dist - 45*scale) / (15*scale), 0, 1) * 0.5
    return np.clip(ring1 + ring2 * 0.8 + ring3 * 0.6 + nucleus + lobe, 0, 1).astype(np.float32)

def texture_fingerprint(shape, seed):
    """Fingerprint - concentric ridge loops."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    # Elongated elliptical distance
    dist = np.sqrt(((yf - cy) * 0.8)**2 + ((xf - cx) * 1.2)**2)
    # Concentric ridges with slight wobble
    ridges = np.sin(dist * 0.5) * 0.5 + 0.5
    # Sharpen to fingerprint-like ridges
    sharp = (ridges > 0.5).astype(np.float32) * 0.7 + 0.15
    return sharp.astype(np.float32)
def texture_neuron_network(shape, seed):
    """Neuron network — cell bodies connected by branching dendrite lines."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    # Place neuron cell bodies
    n_neurons = 35
    neurons_y = rng.randint(0, h, n_neurons)
    neurons_x = rng.randint(0, w, n_neurons)
    # Draw dendrite connections between nearby neurons
    for i in range(n_neurons):
        ay, ax = int(neurons_y[i]), int(neurons_x[i])
        # Find 2-3 nearest neighbors to connect
        dists = np.sqrt((neurons_y - ay) ** 2.0 + (neurons_x - ax) ** 2.0)
        dists[i] = 1e9
        neighbors = np.argsort(dists)[:rng.randint(2, 4)]
        for ni in neighbors:
            by, bx = int(neurons_y[ni]), int(neurons_x[ni])
            # Draw wavy dendrite line
            n_pts = int(np.sqrt((ay - by) ** 2 + (ax - bx) ** 2)) + 1
            if n_pts < 2:
                continue
            for ti in range(n_pts):
                t = ti / max(1, n_pts - 1)
                py = int(ay + (by - ay) * t + np.sin(t * 6 + i) * 4)
                px = int(ax + (bx - ax) * t + np.cos(t * 6 + i) * 4)
                if 0 <= py < h and 0 <= px < w:
                    r = 1
                    y0, y1 = max(0, py - r), min(h, py + r + 1)
                    x0, x1 = max(0, px - r), min(w, px + r + 1)
                    out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], 0.4)
    # Draw cell bodies (soma) on top
    for i in range(n_neurons):
        cy, cx = int(neurons_y[i]), int(neurons_x[i])
        r = rng.uniform(4, 8)
        m = int(r) + 2
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - cy) ** 2 + (lx - cx) ** 2)
        soma = np.clip(1.0 - dist / r, 0, 1) ** 0.5
        np.maximum(out[y0:y1, x0:x1], soma * 0.8, out=out[y0:y1, x0:x1])
    return np.clip(out, 0, 1)
def texture_pulse_monitor(shape, seed):
    """Pulse monitor - ECG heartbeat trace line."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy = h / 2.0
    period = 80
    phase = (xf % period) / period
    # ECG waveform shape
    ecg = np.where(phase < 0.1, 0,
          np.where(phase < 0.15, (phase - 0.1) * 40,   # P wave up
          np.where(phase < 0.2, (0.2 - phase) * 40,    # P wave down
          np.where(phase < 0.3, 0,                       # PR segment
          np.where(phase < 0.33, -(phase - 0.3) * 100,  # Q dip
          np.where(phase < 0.4, (phase - 0.33) * 100,   # R spike up
          np.where(phase < 0.45, (0.45 - phase) * 60 - 3,  # S dip
          np.where(phase < 0.55, 0,                      # ST segment
          np.where(phase < 0.65, np.sin((phase - 0.55) * np.pi / 0.1) * 1.5, 0)))))))))  # T wave
    trace_y = cy - ecg * 15
    trace = np.clip(1.0 - np.abs(yf - trace_y) / 2.5, 0, 1)
    # Grid background
    grid_h = (yf % 20 < 1).astype(np.float32) * 0.15
    grid_v = (xf % 20 < 1).astype(np.float32) * 0.15
    return np.clip(trace * 0.8 + grid_h + grid_v, 0, 1).astype(np.float32)
texture_biohazard = make_symbol_grid_fn(_biohazard_symbol, cell_size=48)

# --- Animal & Wildlife Group ---
def texture_zebra(shape, seed):
    """Zebra - organic irregular black and white stripes."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    xf = x.astype(np.float32)
    dim = min(h, w)
    noise_block = max(8, dim // 64)
    nh, nw = max(1, h // noise_block + 1), max(1, w // noise_block + 1)
    noise = rng.rand(nh, nw).astype(np.float32)
    nmap = np.repeat(np.repeat(noise, noise_block, axis=0), noise_block, axis=1)[:h, :w]
    freq = 0.12
    wave = np.sin((xf * freq + nmap * 6) * np.pi)
    # Sharp binary stripe with strong contrast
    stripes = (wave > 0.0).astype(np.float32)
    return stripes

def texture_tiger_stripe(shape, seed):
    """Tiger stripe — bold directional organic stripes."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed)
    dim = min(h, w)
    noise_block = max(12, dim // 48)
    nh, nw = max(1, h // noise_block + 1), max(1, w // noise_block + 1)
    n1 = rng.rand(nh, nw).astype(np.float32)
    noise = np.repeat(np.repeat(n1, noise_block, axis=0), noise_block, axis=1)[:h, :w]
    # Second noise layer for y-axis distortion (more organic look)
    n2 = rng.rand(nh, nw).astype(np.float32)
    noise2 = np.repeat(np.repeat(n2, noise_block, axis=0), noise_block, axis=1)[:h, :w]
    freq = 0.12
    wave = np.sin((xf * freq + noise * 8 + yf * 0.02 * noise2) * np.pi)
    # Bold binary stripes — strong contrast
    stripes = (wave > 0.0).astype(np.float32)
    return stripes


def texture_giraffe(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    dim = min(h, w)
    # Scale point count and edge threshold with resolution
    num_pts = max(40, dim // 12)
    edge_thresh = max(5, dim // 100)
    pts_y = rng.randint(0, h, num_pts)
    pts_x = rng.randint(0, w, num_pts)
    min_dist = np.full((h, w), 1e9, dtype=np.float32)
    min_dist2 = np.full((h, w), 1e9, dtype=np.float32)
    for py, px in zip(pts_y, pts_x):
        r = int(max(h, w) * 0.4)
        y0, y1 = max(0, py-r), min(h, py+r)
        x0, x1 = max(0, px-r), min(w, px+r)
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        d = np.sqrt((ly-py)**2 + (lx-px)**2)
        roi1 = min_dist[y0:y1, x0:x1]
        roi2 = min_dist2[y0:y1, x0:x1]
        update = d < roi1
        min_dist2[y0:y1, x0:x1] = np.where(update, roi1, np.minimum(roi2, d))
        min_dist[y0:y1, x0:x1] = np.minimum(roi1, d)
    edge = min_dist2 - min_dist
    # Strong contrast: patches = 0.95 (bright), edges = 0.0 (dark network)
    patch = (edge > edge_thresh).astype(np.float32) * 0.95
    return np.clip(np.where(edge < edge_thresh, 0.0, patch), 0, 1).astype(np.float32)

def texture_crocodile(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    pts_y = rng.randint(0, h, 80)
    pts_x = rng.randint(0, w, 80)
    min_d = np.full((h, w), 999.0, dtype=np.float32)
    min_d2 = np.full((h, w), 999.0, dtype=np.float32)
    r = int(max(h, w) * 0.25)
    for py, px in zip(pts_y, pts_x):
        y0, y1 = max(0, py-r), min(h, py+r)
        x0, x1 = max(0, px-r), min(w, px+r)
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        d = np.sqrt((ly-py)**2 + (lx-px)**2)
        roi1 = min_d[y0:y1, x0:x1]
        roi2 = min_d2[y0:y1, x0:x1]
        update = d < roi1
        min_d2[y0:y1, x0:x1] = np.where(update, roi1, np.minimum(roi2, d))
        min_d[y0:y1, x0:x1] = np.where(update, d, roi1)
    edge = min_d2 - min_d
    bump = np.clip(edge / 12.0, 0, 1)
    noise = rng.rand(h, w).astype(np.float32) * 0.1
    return np.clip(bump + noise, 0, 1)

def texture_feather(shape, seed):
    """Feather - central shaft with angled barbs."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    dim = min(h, w)
    cell = max(48, dim // 16)
    ly = yf % cell
    lx = xf % cell
    cx = cell / 2.0
    # Central shaft
    shaft = np.clip(1.0 - np.abs(lx - cx) / 2.0, 0, 1) * 0.9
    # Barbs angling out from shaft
    side = np.sign(lx - cx)
    barb_angle = ly + side * (lx - cx) * 1.5
    barbs = np.sin(barb_angle * np.pi / 4) * 0.5 + 0.5
    barb_mask = np.clip(1.0 - np.abs(lx - cx) / (cell * 0.45), 0, 1)
    barb_fade = np.clip((np.abs(lx - cx) - 2) / 4, 0, 1)  # fade near shaft
    result = np.maximum(shaft, barbs * barb_mask * barb_fade * 0.6)
    return result.astype(np.float32)

# --- SHOKK Series Patterns ---
def texture_shokk_bolt(shape, seed):
    """Jagged lightning bolt Shokker logo strike."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # Zigzag bolt
    cell = 64
    ly = y % cell
    lx = x % cell
    cy = cell / 2
    # Bolt path: zigzag down center
    bolt_x = cy + np.where(ly < cell * 0.25, (ly / (cell * 0.25)) * cell * 0.3,
              np.where(ly < cell * 0.5, cell * 0.3 - ((ly - cell * 0.25) / (cell * 0.25)) * cell * 0.6,
              np.where(ly < cell * 0.75, -cell * 0.3 + ((ly - cell * 0.5) / (cell * 0.25)) * cell * 0.3,
              0.0)))
    dist = np.abs(lx - bolt_x)
    return np.clip(1.0 - dist / 4.0, 0, 1)

def texture_shokk_pulse_wave(shape, seed):
    """Shokk Pulse Wave - concentric energy pulses."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    # Concentric pulse rings with sharp edges
    pulse = np.sin(dist * 0.12) * 0.5 + 0.5
    sharp = np.clip(pulse * 3 - 1, 0, 1)
    # Energy glow
    glow = np.clip(1.0 - dist / (max(h, w) * 0.3), 0, 1) * 0.4
    return np.clip(sharp * 0.7 + glow, 0, 1).astype(np.float32)
texture_shokk_fracture = make_voronoi_texture_fn(num_points=30, edge_mode=True)
def texture_shokk_hex(shape, seed):
    """Shokk Hex - bold hexagonal cells with thick borders."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    size = 24.0
    row_h = size * np.sqrt(3)
    row = np.floor(yf / row_h)
    x_off = xf + (row % 2) * size
    col = np.floor(x_off / (size * 2))
    lx = x_off - col * size * 2 - size
    ly = yf - row * row_h - row_h / 2
    # Hex distance (Chebyshev approx for hexagon)
    hex_dist = np.maximum(np.abs(lx), np.abs(ly) * 1.155 + np.abs(lx) * 0.577)
    edge = np.clip(1.0 - np.abs(hex_dist - size * 0.85) / 2.5, 0, 1)
    fill = np.clip(1.0 - hex_dist / (size * 0.7), 0, 1) * 0.3
    return np.clip(edge + fill, 0, 1).astype(np.float32)
def texture_shokk_scream(shape, seed):
    """Shokk Scream - aggressive radial distortion lines."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2)
    angle = np.arctan2(yf - cy, xf - cx)
    # Jagged radial spikes
    spikes = np.abs(np.sin(angle * 16)) ** 0.3
    radial_fade = np.clip(dist / (max(h, w) * 0.35), 0, 1)
    # Distortion waves
    distort = np.sin(dist * 0.08 + angle * 3) * 0.3
    return np.clip(spikes * radial_fade * 0.7 + distort + 0.1, 0, 1).astype(np.float32)
def texture_shokk_grid(shape, seed):
    """Shokk Grid - energized hexagonal grid with glow."""
    h, w = shape
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Hex grid
    size = 20.0
    row_h = size * np.sqrt(3)
    row = np.floor(yf / row_h)
    x_off = xf + (row % 2) * size
    col = np.floor(x_off / (size * 2))
    lx = x_off - col * size * 2 - size
    ly = yf - row * row_h - row_h / 2
    dist = np.sqrt(lx**2 + ly**2)
    # Hex edge glow
    edge = np.clip(1.0 - np.abs(dist - size * 0.8) / 3.0, 0, 1)
    # Inner energy pulse
    inner = np.clip(1.0 - dist / (size * 0.5), 0, 1) * 0.4
    return np.clip(edge + inner, 0, 1).astype(np.float32)

# --- Abstract & Experimental ---
def texture_sound_wave(shape, seed):
    """Sound wave - audio waveform oscillation."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cy = h / 2.0
    # Complex waveform (sum of harmonics)
    wave = (np.sin(xf * 0.08) * 30 +
            np.sin(xf * 0.15) * 15 +
            np.sin(xf * 0.25) * 8 +
            np.sin(xf * 0.4) * 4)
    # Envelope
    envelope = np.sin(xf * 0.02) * 0.5 + 0.6
    wave_y = cy + wave * envelope * 0.3
    trace = np.clip(1.0 - np.abs(yf - wave_y) / 3.0, 0, 1)
    # Fill between center and wave
    fill = ((yf > np.minimum(cy, wave_y)) & (yf < np.maximum(cy, wave_y))).astype(np.float32) * 0.3
    return np.clip(trace + fill, 0, 1).astype(np.float32)
def texture_morse_code(shape, seed):
    """Morse code - dot-dash patterns in horizontal rows."""
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    row_h = 8
    dot_w = 4
    dash_w = 12
    gap = 4
    for row in range(0, h, row_h * 2):
        x_pos = 2
        while x_pos < w - dash_w:
            is_dash = rng.rand() > 0.4
            elem_w = dash_w if is_dash else dot_w
            y1, y2 = row + 2, min(h, row + row_h - 2)
            x1, x2 = x_pos, min(w, x_pos + elem_w)
            if y1 < y2 and x1 < x2:
                result[y1:y2, x1:x2] = rng.uniform(0.6, 1.0)
            x_pos += elem_w + gap + rng.randint(0, 4)
    return result.astype(np.float32)
def texture_fractal(shape, seed):
    """Fractal - Julia set. Uses float32 and early-out."""
    import numpy as np
    h, w = shape[:2] if len(shape) > 2 else shape
    cx_j, cy_j = np.float32(-0.7), np.float32(0.27015)
    zx = (np.arange(w, dtype=np.float32) / w - 0.5) * 3.0
    zy = (np.arange(h, dtype=np.float32) / h - 0.5) * 3.0
    zx = np.broadcast_to(zx.reshape(1, -1), (h, w)).copy()
    zy = np.broadcast_to(zy.reshape(-1, 1), (h, w)).copy()
    result = np.zeros((h, w), dtype=np.float32)
    escaped = np.zeros((h, w), dtype=np.bool_)
    for i in range(30):
        zx_new = zx * zx - zy * zy + cx_j
        zy = np.float32(2) * zx * zy + cy_j
        zx = zx_new
        new_escaped = (~escaped) & ((zx * zx + zy * zy) > np.float32(4))
        result[new_escaped] = (i + 1) / 30.0
        escaped |= new_escaped
        if escaped.all(): break
        zx[escaped] = 0; zy[escaped] = 0
    return result

# === RADIAL FACTORY REPLACEMENTS (13) ===

def texture_optical_illusion(shape, seed):
    h, w = shape
    y, x = _get_mgrid(shape)
    moire1 = np.sin(x * 0.1 + y * 0.05) * 0.5 + 0.5
    moire2 = np.sin(x * 0.11 + y * 0.053) * 0.5 + 0.5
    return np.clip(np.abs(moire1 - moire2) * 4, 0, 1)

def texture_biomechanical(shape, seed):
    """Biomechanical — Giger-esque organic/mechanical hybrid with tubes, ribs, and conduits."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xf = np.arange(w, dtype=np.float32).reshape(1, -1)
    out = np.zeros((h, w), dtype=np.float32)
    # Ribbed organic tubes running vertically with slight curve
    for _ in range(8):
        cx = rng.uniform(0, w)
        tube_w = rng.uniform(12, 30)
        phase = rng.uniform(0, 2 * np.pi)
        path_x = cx + np.sin(yf * 0.02 + phase) * 20
        dx = np.abs(xf - path_x)
        tube = np.clip(1.0 - dx / tube_w, 0, 1)
        # Ribbed segments along tube
        rib_spacing = rng.uniform(6, 12)
        ribs = np.abs(np.sin(yf * np.pi / rib_spacing)) ** 3 * 0.4
        tube_surface = tube * (0.4 + ribs)
        # Highlight along tube center
        highlight = np.clip(1.0 - dx / (tube_w * 0.3), 0, 1) * 0.3
        out = np.maximum(out, tube_surface + highlight * tube)
    # Mechanical joints / socket patterns at intersections
    joint_spacing = 60
    jy = yf % joint_spacing
    jx = xf % joint_spacing
    jcy, jcx = joint_spacing / 2.0, joint_spacing / 2.0
    jdist = np.sqrt((jy - jcy) ** 2 + (jx - jcx) ** 2)
    jangle = np.arctan2(jy - jcy, jx - jcx)
    # Socket ring with bolt-like segments
    socket = np.clip(1.0 - np.abs(jdist - 15) / 2.5, 0, 1) * 0.5
    bolts = (np.abs(np.sin(jangle * 6)) > 0.85).astype(np.float32) * (jdist < 18).astype(np.float32) * 0.4
    out = np.maximum(out, socket + bolts)
    # Fine surface sinew texture
    sinew = np.sin(yf * 0.4 + np.sin(xf * 0.08) * 3) * 0.15 + 0.15
    out = np.maximum(out, sinew * 0.3)
    return np.clip(out, 0, 1)
texture_voronoi_shatter = make_voronoi_texture_fn(num_points=60, edge_mode=True)


# ================================================================
# PATTERN PAINT MODIFIERS (generic reusable for new patterns)
# ================================================================

def make_darken_paint_fn(strength=0.10):
    """Factory: pattern darkens the paint."""
    def fn(paint, shape, mask, seed, pm, bb):
        # Use texture to get pattern shape
        # (The compose_finish function handles this differently — pattern_val is passed)
        # For the registry, this just defines how the pattern modulates paint
        for c in range(3):
            noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + c * 17)
            paint[:,:,c] = np.clip(paint[:,:,c] - np.abs(noise) * strength * pm * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_emboss_paint_fn(strength=0.08):
    """Factory: pattern embosses — brightens high areas, darkens low."""
    def fn(paint, shape, mask, seed, pm, bb):
        noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 100)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + noise * strength * pm * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_contrast_paint_fn(strength=0.12):
    """Factory: pattern adds contrast — used for checks, stripes, etc."""
    def fn(paint, shape, mask, seed, pm, bb):
        noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 200)
        brightness = paint.mean(axis=2)
        is_dark = (brightness < 0.15).astype(np.float32)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c]
                - noise * strength * pm * (1 - is_dark) * mask
                + noise * strength * 0.7 * pm * is_dark * mask, 0, 1)
        return paint
    return fn

def make_glow_paint_fn(r=0.0, g=0.0, b=0.0, strength=0.06):
    """Factory: pattern adds colored glow."""
    def fn(paint, shape, mask, seed, pm, bb):
        noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 300)
        glow_map = np.clip(noise * 0.5 + 0.5, 0, 1)
        paint[:,:,0] = np.clip(paint[:,:,0] + glow_map * r * strength * pm * mask, 0, 1)
        paint[:,:,1] = np.clip(paint[:,:,1] + glow_map * g * strength * pm * mask, 0, 1)
        paint[:,:,2] = np.clip(paint[:,:,2] + glow_map * b * strength * pm * mask, 0, 1)
        return paint
    return fn

def make_tint_paint_fn(r_shift=0, g_shift=0, b_shift=0, strength=0.06):
    """Factory: pattern applies color tint."""
    def fn(paint, shape, mask, seed, pm, bb):
        noise = _multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 400)
        paint[:,:,0] = np.clip(paint[:,:,0] + noise * r_shift * strength * pm * mask, 0, 1)
        paint[:,:,1] = np.clip(paint[:,:,1] + noise * g_shift * strength * pm * mask, 0, 1)
        paint[:,:,2] = np.clip(paint[:,:,2] + noise * b_shift * strength * pm * mask, 0, 1)
        return paint
    return fn

# ================================================================
# CONCRETE PATTERN PAINT FUNCTION INSTANCES
# ================================================================

# Standard paint modifiers for different pattern families
# NOTE: Strength values kept SUBTLE — paint mods should hint at the pattern, not overpower.
# The spec map does the heavy lifting. Paint changes should be barely noticeable.
ppaint_darken_light = make_darken_paint_fn(strength=0.06)
ppaint_darken_medium = make_darken_paint_fn(strength=0.10)
ppaint_darken_heavy = make_darken_paint_fn(strength=0.14)
ppaint_emboss_light = make_emboss_paint_fn(strength=0.05)
ppaint_emboss_medium = make_emboss_paint_fn(strength=0.08)
ppaint_emboss_heavy = make_emboss_paint_fn(strength=0.11)
ppaint_contrast_light = make_contrast_paint_fn(strength=0.08)
ppaint_contrast_medium = make_contrast_paint_fn(strength=0.12)
ppaint_glow_red = make_glow_paint_fn(r=1.0, g=0.2, b=0.0, strength=0.08)
ppaint_glow_blue = make_glow_paint_fn(r=0.1, g=0.3, b=1.0, strength=0.08)
ppaint_glow_green = make_glow_paint_fn(r=0.1, g=1.0, b=0.2, strength=0.08)
ppaint_glow_gold = make_glow_paint_fn(r=0.9, g=0.8, b=0.2, strength=0.08)
ppaint_glow_purple = make_glow_paint_fn(r=0.6, g=0.1, b=1.0, strength=0.08)
ppaint_glow_neon = make_glow_paint_fn(r=0.0, g=1.0, b=1.0, strength=0.10)
ppaint_tint_warm = make_tint_paint_fn(r_shift=0.3, g_shift=0.1, b_shift=-0.2, strength=0.06)
ppaint_tint_cool = make_tint_paint_fn(r_shift=-0.2, g_shift=0.1, b_shift=0.3, strength=0.06)
ppaint_tint_rust = make_tint_paint_fn(r_shift=0.5, g_shift=0.2, b_shift=-0.1, strength=0.08)
ppaint_tint_toxic = make_tint_paint_fn(r_shift=-0.1, g_shift=0.5, b_shift=-0.2, strength=0.07)
ppaint_tint_blood = make_tint_paint_fn(r_shift=0.6, g_shift=-0.1, b_shift=-0.1, strength=0.08)


def make_texture_paint_fn(tex_fn, strength=0.15, mode="darken"):
    """Factory: paint modifier that follows the ACTUAL pattern texture shape.
    Unlike make_darken_paint_fn (which uses random noise), this calls the
    texture function to generate the real pattern and applies darkening/emboss
    along the pattern lines. This makes patterns like Chain Link, Hex Mesh,
    etc. visible in the paint color, not just in the spec map.
    
    mode: "darken" = darken where pattern is strong
          "emboss" = lighten pattern edges, darken recesses
    """
    def fn(paint, shape, mask, seed, pm, bb):
        try:
            tex = tex_fn(shape, mask, seed + 500, 1.0)
            if isinstance(tex, dict):
                pv = tex.get("pattern_val", np.zeros(shape, dtype=np.float32))
            else:
                pv = tex
            # Normalize to 0-1
            pmin, pmax = float(pv.min()), float(pv.max())
            if pmax - pmin > 1e-8:
                pv = (pv - pmin) / (pmax - pmin)
            else:
                pv = np.zeros_like(pv)
            if mode == "emboss":
                # Emboss: brighten high areas, darken low
                mid = 0.5
                highlight = np.clip((pv - mid) * 2, 0, 1)
                shadow = np.clip((mid - pv) * 2, 0, 1)
                for c in range(3):
                    paint[:,:,c] = np.clip(
                        paint[:,:,c] + highlight * strength * 0.5 * pm * mask
                        - shadow * strength * pm * mask, 0, 1)
            else:
                # Darken: reduce brightness where pattern is strong
                for c in range(3):
                    paint[:,:,c] = np.clip(
                        paint[:,:,c] - pv * strength * pm * mask, 0, 1)
            paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
        except Exception as e:
            # Fallback to noise darkening if texture fails
            for c in range(3):
                noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + c * 17)
                paint[:,:,c] = np.clip(paint[:,:,c] - np.abs(noise) * strength * pm * mask, 0, 1)
        return paint
    return fn


# ================================================================
# Texture-aware paint instances (follow actual pattern shape, not random noise)
# Only reference texture fns defined in THIS file (not engine-only ones like hex_mesh, rivet_grid)
ppaint_tex_chainlink = make_texture_paint_fn(texture_chainlink, strength=0.18, mode="darken")
ppaint_tex_checkered_flag = make_texture_paint_fn(texture_checkered_flag, strength=0.15, mode="darken")

# ================================================================
# EXPANSION PATTERNS REGISTRY (100 new pattern entries)
# ================================================================
# Format: {"texture_fn": fn, "paint_fn": fn, "variable_cc": bool, "desc": str}



# ================================================================
# NEW PATTERN TEXTURE FUNCTIONS: Flames, Skate & Surf, Cartoons, Comics (48 total)
# ================================================================
# ================================================================
# NEW PATTERN TEXTURE FUNCTIONS: Flames, Skate & Surf, Cartoons, Comics (48 total)
# ================================================================

def texture_classic_hotrod(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    for i in range(7):
        cx = w * (i + 0.5) / 7 + rng.uniform(-15, 15)
        flame_h = h * rng.uniform(0.4, 0.7)
        width_base = w / 7 * 0.8
        progress = np.clip(1.0 - yi / flame_h, 0, 1)
        fw = width_base * progress ** 0.6
        scallop = np.sin(progress * np.pi * 2.5) * fw * 0.2
        dx = np.abs(xx - cx)
        tongue = np.clip(1.0 - dx / (fw + scallop + 1), 0, 1) * progress
        out = np.maximum(out, tongue)
    return np.clip(out, 0, 1)


def texture_ghost_flames(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    for i in range(8):
        cx = w * rng.uniform(0.05, 0.95)
        phase = rng.uniform(0, np.pi * 2)
        progress = np.clip(1.0 - yi / (h * 0.85), 0, 1)
        wobble = np.sin(yi * 0.03 + phase) * 40 * progress
        dx = np.abs(xx - cx - wobble)
        wisp = np.exp(-(dx**2) / (2 * (50 * progress + 3)**2)) * progress * 0.55
        out = np.maximum(out, wisp)
    return np.clip(out, 0, 1)


def texture_pinstripe_flames(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    for i in range(8):
        cx = w * (i + 0.5) / 8 + rng.uniform(-10, 10)
        flame_h = h * rng.uniform(0.3, 0.7)
        width_base = w / 8 * 0.6
        progress = np.clip(1.0 - yi / flame_h, 0, 1)
        fw = width_base * progress ** 0.7
        scallop = np.sin(progress * np.pi * 3) * fw * 0.15
        dx = np.abs(xx - cx)
        outer = fw + scallop + 1
        inner = np.maximum(outer - 5, 0)
        ring = np.where((dx < outer) & (dx > inner), progress * 0.85, 0.0)
        out = np.maximum(out, ring)
    return np.clip(out, 0, 1)


def texture_fire_lick(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    cell_w = rng.randint(30, 60)
    cell_h = rng.randint(40, 80)
    n_cols = w // cell_w + 2
    n_rows = h // cell_h + 2
    for r in range(n_rows):
        offset = cell_w // 2 if r % 2 else 0
        for c in range(n_cols):
            cx = c * cell_w + offset + cell_w // 2
            cy = r * cell_h + cell_h
            lrng = np.random.RandomState(seed + r * 100 + c)
            tip_h = cell_h * lrng.uniform(0.5, 0.9)
            y0 = max(0, int(cy - tip_h) - 1)
            y1 = min(h, int(cy) + 1)
            x0 = max(0, int(cx - cell_w))
            x1 = min(w, int(cx + cell_w))
            if y1 <= y0 or x1 <= x0:
                continue
            ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
            lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
            progress = np.clip((cy - ly) / tip_h, 0, 1)
            fw = cell_w * 0.3 * (1 - progress ** 2)
            wobble_val = np.sin(progress * np.pi * 2 + lrng.uniform(0, 6)) * fw * 0.3
            dx = np.abs(lx - cx - wobble_val)
            tongue = np.clip(1.0 - dx / (fw + 1), 0, 1) * (1 - progress * 0.3)
            roi = out[y0:y1, x0:x1]
            np.maximum(roi, tongue, out=roi)
    return np.clip(out, 0, 1)


def texture_inferno(shape, seed):
    """Inferno — raging wall of flames covering entire surface with heat shimmer."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Layer 1: Heat shimmer base — ensures FULL canvas coverage
    heat = _multi_scale_noise(shape[:2], [8, 16, 32], [0.3, 0.4, 0.3], seed + 1)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)
    out = heat * 0.18
    # Layer 2: Dense flame columns — widths scaled to canvas, near-full height
    for _ in range(40):
        cx = rng.uniform(-w * 0.05, w * 1.05)
        flame_h = h * rng.uniform(0.75, 1.0)
        width = w * rng.uniform(0.04, 0.14)
        phase = rng.uniform(0, 2 * np.pi)
        intensity = rng.uniform(0.4, 1.0)
        progress = np.clip(1.0 - yi / flame_h, 0, 1)
        wobble = np.sin(yi * 0.05 + phase) * width * 0.35 * progress
        wobble += np.sin(yi * 0.11 + phase * 2.3) * width * 0.15 * progress
        dx = np.abs(xx - cx - wobble)
        flame = np.clip(1.0 - dx / (width * progress + 1), 0, 1) * progress
        out = np.maximum(out, flame * intensity)
    # Layer 3: Hot bottom glow — intense heat at base
    bottom_glow = np.clip(1.0 - yi / (h * 0.25), 0, 1) ** 1.5 * 0.3
    out = np.maximum(out, bottom_glow)
    return np.clip(out, 0, 1)


def texture_fireball(shape, seed):
    """Fireball — explosive spheres with heat radiation covering the full canvas."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    sz = min(h, w)
    # Layer 1: Ambient heat field — full canvas glow
    heat = _multi_scale_noise(shape[:2], [16, 32, 64], [0.3, 0.4, 0.3], seed + 2)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)
    out = heat * 0.12
    # Layer 2: Multiple fireballs with wide radiant glow
    n_balls = rng.randint(4, 8)
    centers = []
    for _ in range(n_balls):
        cx = rng.randint(0, w)
        cy = rng.randint(0, h)
        max_r = rng.uniform(0.08, 0.20) * sz
        centers.append((cx, cy, max_r))
    # Radiant heat halos (extend far beyond fireball)
    yy = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xxg = np.arange(w, dtype=np.float32).reshape(1, -1)
    for cx, cy, max_r in centers:
        dist = np.sqrt((xxg - cx)**2 + (yy - cy)**2)
        halo = np.exp(-(dist**2) / (2 * (max_r * 2.5)**2)) * 0.25
        out = np.maximum(out, halo)
    # Fireball cores with irregular edges
    for cx, cy, max_r in centers:
        margin = int(max_r * 1.8) + 2
        y0, y1 = max(0, cy - margin), min(h, cy + margin)
        x0, x1 = max(0, cx - margin), min(w, cx + margin)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((lx - cx)**2 + (ly - cy)**2)
        angle = np.arctan2(ly - cy, lx - cx)
        edge_noise = sum(rng.uniform(0.05, 0.15) * np.sin(rng.randint(3, 10) * angle + rng.uniform(0, 6)) for _ in range(5))
        burst_r = max_r * (1 + edge_noise)
        core = np.exp(-(dist**2) / (2 * (max_r * 0.4)**2))
        outer = np.clip(1.0 - dist / burst_r, 0, 1)
        ball = (core * 0.7 + outer * 0.5) * (dist < burst_r * 1.3)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], ball)
    return np.clip(out, 0, 1)

def texture_hellfire(shape, seed):
    """Hellfire — chaotic meandering fire columns with ambient hellglow covering full canvas."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    # Layer 1: Ambient hell-glow base — full canvas coverage
    heat = _multi_scale_noise(shape[:2], [8, 16, 32], [0.3, 0.4, 0.3], seed + 3)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)
    out = heat * 0.15
    # Bottom heat intensifier
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    bottom_heat = np.clip(1.0 - yi / (h * 0.3), 0, 1) ** 1.5 * 0.2
    out = np.maximum(out, bottom_heat * np.ones((1, w), dtype=np.float32))
    # Layer 2: Meandering fire columns — wider, more numerous
    for _ in range(rng.randint(15, 25)):
        cx, cy = rng.uniform(0, w), float(h)
        seg_len = rng.randint(12, 30)
        width = w * rng.uniform(0.02, 0.06)
        points = [(cx, cy)]
        while cy > 0:
            cx += rng.uniform(-w * 0.05, w * 0.05)
            cy -= seg_len + rng.uniform(-5, 5)
            points.append((cx, max(0, cy)))
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            if abs(y1 - y2) < 1:
                continue
            seg_y0 = max(0, int(min(y1, y2)) - 1)
            seg_y1 = min(h, int(max(y1, y2)) + 1)
            seg_x0 = max(0, int(min(x1, x2) - width * 3))
            seg_x1 = min(w, int(max(x1, x2) + width * 3))
            if seg_y1 <= seg_y0 or seg_x1 <= seg_x0:
                continue
            ly = np.arange(seg_y0, seg_y1, dtype=np.float32).reshape(-1, 1)
            lx = np.arange(seg_x0, seg_x1, dtype=np.float32).reshape(1, -1)
            t = np.clip((ly - y1) / (y2 - y1), 0, 1)
            line_x = x1 + (x2 - x1) * t
            dx = np.abs(lx - line_x)
            w_here = width * (1 - np.abs(t - 0.5) * 0.4)
            seg_val = np.clip(1.0 - dx / (w_here + 1), 0, 1) * 0.85
            roi = out[seg_y0:seg_y1, seg_x0:seg_x1]
            np.maximum(roi, seg_val, out=roi)
    return np.clip(out, 0, 1)


def texture_wildfire(shape, seed):
    """Wildfire — chaotic spreading fire with turbulent flame edges rising from bottom."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Multiple overlapping flame fronts rising from bottom
    for _ in range(25):
        cx = rng.uniform(0, w)
        flame_h = h * rng.uniform(0.3, 0.95)
        width = rng.uniform(15, 80)
        phase = rng.uniform(0, 2 * np.pi)
        intensity = rng.uniform(0.3, 0.8)
        progress = np.clip(1.0 - yi / flame_h, 0, 1)
        # Turbulent wobble increases near flame tips
        wobble = np.sin(yi * 0.04 + phase) * width * 0.4 * progress
        wobble += np.sin(yi * 0.09 + phase * 1.7) * width * 0.2 * progress
        dx = np.abs(xx - cx - wobble)
        flame = np.clip(1.0 - dx / (width * progress + 1), 0, 1) * progress ** 0.7
        out = np.maximum(out, flame * intensity)
    # Add turbulent edge breakup using low-res noise
    n1 = np.repeat(np.repeat(rng.rand(max(1, h // 8 + 1), max(1, w // 8 + 1)).astype(np.float32), 8, 0), 8, 1)[:h, :w]
    edge_mask = (out > 0.1) & (out < 0.5)
    out = np.where(edge_mask, out * (0.6 + n1 * 0.8), out)
    return np.clip(out, 0, 1)


def texture_flame_fade(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(0, 1, w).reshape(1, -1)
    y = np.linspace(0, 1, h).reshape(-1, 1)
    for _ in range(rng.randint(5, 10)):
        cx = rng.uniform(0.1, 0.9)
        progress = np.clip((1.0 - y) / rng.uniform(0.4, 0.8), 0, 1)
        width = rng.uniform(0.05, 0.15) * progress
        dx = np.abs(x - cx)
        wobble = 0.02 * np.sin(y * rng.uniform(5, 15) * 2 * np.pi)
        flame = np.exp(-((dx - wobble)**2) / (2 * (width + 0.001)**2))
        out += flame * progress**1.5 * rng.uniform(0.3, 0.7)
    return np.clip(out, 0, 1)


def texture_blue_flame(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    for i in range(rng.randint(5, 9)):
        cx = w * (i + 0.5) / 7 + rng.uniform(-15, 15)
        flame_h = h * rng.uniform(0.3, 0.65)
        base_w = rng.uniform(15, 35)
        progress = np.clip(1.0 - yi / flame_h, 0, 1)
        fw = base_w * (1 - progress ** 0.5)
        out = np.maximum(out, np.exp(-((xx - cx)**2) / (2 * (fw + 0.5)**2)) * progress * 0.9)
    return np.clip(out, 0, 1)


def texture_torch_burn(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(2, 5)):
        ox, oy = rng.randint(0,w), rng.randint(h//2,h)
        angle = rng.uniform(-0.8,0.8)-np.pi/2
        cone_len = rng.uniform(h*0.3,h*0.7); cone_spread = rng.uniform(0.2,0.5)
        max_w = cone_len*cone_spread+5
        end_x = ox+np.cos(angle)*cone_len; end_y = oy+np.sin(angle)*cone_len
        y0 = max(0,int(min(oy,end_y)-max_w)); y1 = min(h,int(max(oy,end_y)+max_w))
        x0 = max(0,int(min(ox,end_x)-max_w)); x1 = min(w,int(max(ox,end_x)+max_w))
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx,dy = lx-ox,ly-oy
        along = dx*np.cos(angle)+dy*np.sin(angle)
        across = -dx*np.sin(angle)+dy*np.cos(angle)
        cone_w = along*cone_spread+5
        in_cone = (along>0)&(np.abs(across)<cone_w)
        intensity = np.exp(-(across**2)/(2*(cone_w*0.4+1)**2))*(1-np.clip(along/cone_len,0,1)*0.7)
        out[y0:y1,x0:x1] += intensity*in_cone*0.7
    return np.clip(out, 0, 1)

def texture_ember_scatter(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    sz = min(h, w)
    out = np.zeros((h, w), dtype=np.float32)
    n_embers = rng.randint(80, 180)
    for _ in range(n_embers):
        ex, ey = rng.randint(0, w), rng.randint(0, h)
        size = rng.uniform(0.002, 0.008) * sz; intensity = rng.uniform(0.5, 1.0)
        m = int(size * 4) + 2
        y0, y1 = max(0, ey-m), min(h, ey+m); x0, x1 = max(0, ex-m), min(w, ex+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        ember = np.exp(-((lx-ex)**2+(ly-ey)**2)/(2*size**2))*intensity
        out[y0:y1,x0:x1] = np.maximum(out[y0:y1,x0:x1], ember)
    return np.clip(out, 0, 1)

def texture_wave_curl(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    y = np.linspace(0, 1, h).reshape(-1, 1); x = np.linspace(0, 1, w).reshape(1, -1)
    for i in range(rng.randint(3, 6)):
        freq, phase, amp = rng.uniform(4,10), rng.uniform(0,2*np.pi), rng.uniform(0.08,0.18)
        cy = rng.uniform(0.2, 0.8)
        wave_y = cy + amp * np.sin(freq * x * 2 * np.pi + phase)
        band = np.exp(-((y - wave_y)**2) / (2*0.015**2))
        curl = np.where(y < wave_y - 0.03, 0.0, np.where(y < wave_y, np.exp(-((y-wave_y)**2)/(2*0.008**2))*0.7, 0.0))
        out += np.clip(band * 0.8 + curl, 0, 1)
    return np.clip(out, 0, 1)


def texture_ocean_foam(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(300, 600)):
        cx, cy, r = rng.randint(0,w), rng.randint(0,h), rng.uniform(2,12)
        m = int(r + 1.5*5) + 1
        y0, y1 = max(0,cy-m), min(h,cy+m); x0, x1 = max(0,cx-m), min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dist = np.sqrt((lx-cx)**2+(ly-cy)**2)
        out[y0:y1,x0:x1] += np.exp(-((dist-r)**2)/(2*1.5**2))*rng.uniform(0.4,1.0)
    out += np.repeat(np.repeat(rng.rand(max(1,h//4+1),max(1,w//4+1)).astype(np.float32),4,0),4,1)[:h,:w]*0.3
    return np.clip(out, 0, 1)

def texture_palm_frond(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n_fronds = rng.randint(4, 7)
    for _ in range(n_fronds):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        angle = rng.uniform(0, 2 * np.pi)
        length = rng.uniform(h * 0.25, h * 0.5)
        leaf_w_base = rng.uniform(20, 40) * scale
        end_x = cx + np.cos(angle) * length
        end_y = cy + np.sin(angle) * length
        margin = leaf_w_base * 1.5
        roi_y0 = max(0, int(min(cy, end_y) - margin))
        roi_y1 = min(h, int(max(cy, end_y) + margin))
        roi_x0 = max(0, int(min(cx, end_x) - margin))
        roi_x1 = min(w, int(max(cx, end_x) + margin))
        if roi_y1 <= roi_y0 or roi_x1 <= roi_x0:
            continue
        ry = yy[roi_y0:roi_y1, roi_x0:roi_x1]
        rx = xx[roi_y0:roi_y1, roi_x0:roi_x1]
        dx, dy = rx - cx, ry - cy
        along = dx * np.cos(angle) + dy * np.sin(angle)
        across = -dx * np.sin(angle) + dy * np.cos(angle)
        t = np.clip(along / length, 0, 1)
        in_frond = (along > 0) & (along < length)
        spine_w = 3.0 * scale * (1 - t * 0.5)
        spine = np.exp(-(across**2) / (2 * spine_w**2)) * in_frond * 0.7
        leaf_taper = leaf_w_base * (1 - t)
        leaflet_pattern = np.abs(np.sin(t * 12.0 * np.pi))
        leaflet = np.exp(-(across**2) / (2 * (leaf_taper * 0.3 + 1)**2)) * leaflet_pattern
        leaflet *= in_frond * (np.abs(across) < leaf_taper) * 0.5
        roi = out[roi_y0:roi_y1, roi_x0:roi_x1]
        roi += spine + leaflet
    return np.clip(out, 0, 1)


def texture_tiki_totem(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    nc, nr = rng.randint(3,6), rng.randint(4,7)
    cw, ch = w/nc, h/nr
    for r in range(nr):
        for c in range(nc):
            cx, cy = (c+0.5)*cw, (r+0.5)*ch
            y0 = max(0,int(cy-ch*0.55)); y1 = min(h,int(cy+ch*0.55))
            x0 = max(0,int(cx-cw*0.55)); x1 = min(w,int(cx+cw*0.55))
            if y1<=y0 or x1<=x0: continue
            ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
            lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
            bx = np.abs(lx-cx)/(cw*0.45); by = np.abs(ly-cy)/(ch*0.45)
            inside = (bx<1.0)&(by<1.0)
            roi = out[y0:y1,x0:x1]
            roi[inside & ((bx>0.85)|(by>0.85))] = 0.9
            for ex_off in [-0.2, 0.2]:
                dist = np.sqrt((lx-(cx+ex_off*cw))**2+(ly-(cy-ch*0.1))**2)
                roi += np.exp(-((dist-min(cw,ch)*0.1)**2)/(2*2.0**2))*0.6*inside
            roi[(np.abs(ly-(cy+ch*0.15))<ch*0.04)&(np.abs(lx-cx)<cw*0.25)] = 0.7
    return np.clip(out, 0, 1)

def texture_grip_tape(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    fine = rng.rand(h, w).astype(np.float32)
    coarse = np.repeat(np.repeat(rng.rand(max(1,h//2+1),max(1,w//2+1)).astype(np.float32),2,0),2,1)[:h,:w]
    grit = fine * 0.6 + coarse * 0.4
    scratches = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(20, 50)):
        sx, sy, angle = rng.randint(0,w), rng.randint(0,h), rng.uniform(-0.3, 0.3)
        for t in range(rng.randint(20, 80)):
            scratches[int(sy+np.sin(angle)*t)%h, int(sx+np.cos(angle)*t)%w] = rng.uniform(0.5, 1.0)
    return np.clip(grit * 0.7 + scratches * 0.3, 0, 1)


def texture_halfpipe(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(-1, 1, w).reshape(1,-1); y = np.linspace(0, 1, h).reshape(-1,1)
    for i in range(rng.randint(2, 5)):
        offset, width, depth = rng.uniform(-0.5,0.5), rng.uniform(0.3,0.7), rng.uniform(0.3,0.6)
        local_x = (x - offset) / width
        out += np.exp(-((y - depth*local_x**2)**2)/(2*0.02**2)) * (np.abs(local_x)<1.0) * 0.7
        out += (np.exp(-((x-(offset-width))**2)/(2*0.01**2)) + np.exp(-((x-(offset+width))**2)/(2*0.01**2))) * 0.4
    out += np.exp(-((y-0.05)**2)/(2*0.008**2)) * 0.5
    return np.clip(out, 0, 1)


def texture_bamboo_stalk(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1,-1); yy = np.arange(h, dtype=np.float32).reshape(-1,1)
    for _ in range(rng.randint(5, 10)):
        cx = rng.randint(0, w); stalk_w = rng.uniform(15, 35)
        dist_x = np.abs(xx - cx)
        out += np.exp(-(dist_x**2)/(2*(stalk_w*0.3)**2))*0.6 + np.exp(-((dist_x-stalk_w*0.4)**2)/(2*2.0**2))*0.5
        for j in range(rng.randint(4, 8)):
            ny = int(h*(j+0.5)/6 + rng.uniform(-10,10))
            out += np.exp(-((yy-ny)**2)/(2*3.0**2)) * (dist_x < stalk_w*0.5) * 0.4
    return np.clip(out, 0, 1)


def texture_surf_stripe(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(0,1,w).reshape(1,-1); y = np.linspace(0,1,h).reshape(-1,1)
    centers = np.sort(rng.uniform(0.1, 0.9, rng.randint(3,7)))
    widths = rng.uniform(0.02, 0.06, len(centers))
    for i in range(len(centers)):
        wobble = 0.01 * np.sin(y * rng.uniform(3,8)*2*np.pi + rng.uniform(0,6))
        out += np.exp(-((x-centers[i]-wobble)**2)/(2*widths[i]**2)) * rng.uniform(0.5, 1.0)
    out += np.exp(-((x-0.5)**2)/(2*0.003**2)) * 0.6
    return np.clip(out, 0, 1)


def texture_board_wax(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(40, 80)):
        cx, cy = rng.randint(0,w), rng.randint(0,h)
        r = rng.uniform(8, 25); i1, i2 = rng.uniform(0.3,0.8), rng.uniform(0.1,0.3)
        m = int(r*2.5)+1
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dist = np.sqrt((lx-cx)**2+(ly-cy)**2)
        out[y0:y1,x0:x1] += np.exp(-((dist-r)**2)/(2*2.5**2))*i1 + np.exp(-(dist**2)/(2*(r*0.7)**2))*i2
    out += rng.rand(h,w).astype(np.float32)*0.15
    return np.clip(out, 0, 1)

def texture_tropical_leaf(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(3, 7)):
        cx, cy = rng.randint(0,w), rng.randint(0,h)
        angle = rng.uniform(0, 2*np.pi)
        leaf_len = rng.uniform(h*0.25, h*0.5)
        leaf_wid = rng.uniform(leaf_len*0.3, leaf_len*0.5)
        m = int(max(leaf_len, leaf_wid)*0.7)+5
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx, dy = lx-cx, ly-cy
        rx = dx*np.cos(-angle)-dy*np.sin(-angle)
        ry = dx*np.sin(-angle)+dy*np.cos(-angle)
        along = rx/leaf_len; across = ry/(leaf_wid*(1-0.3*np.abs(along)))
        inside = (np.abs(along)<0.5) & (np.abs(across)<0.5)
        out[y0:y1,x0:x1] += np.exp(-(across**2)/0.3)*np.exp(-(along**2)/0.4)*inside*0.7
        out[y0:y1,x0:x1] += np.exp(-(ry**2)/(2*2.0**2))*(np.abs(along)<0.5)*0.3
    return np.clip(out, 0, 1)

def texture_rip_tide(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(0,1,w).reshape(1,-1); y = np.linspace(0,1,h).reshape(-1,1)
    n_waves = rng.randint(3, 7)
    for _ in range(n_waves):
        fx, fy = rng.uniform(2,6), rng.uniform(2,6)
        px, py = rng.uniform(0,2*np.pi), rng.uniform(0,2*np.pi)
        wave = (np.sin(fx*x*2*np.pi+px+np.sin(fy*y*2*np.pi+py)*1.5)*0.5+0.5)
        out += wave * rng.uniform(0.08, 0.18)
    # Normalize to 0-1 range
    mn, mx = out.min(), out.max()
    if mx > mn:
        out = (out - mn) / (mx - mn)
    return np.clip(out, 0, 1).astype(np.float32)


def texture_hibiscus(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    n_flowers = rng.randint(8, 18)
    for _ in range(n_flowers):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        size = rng.uniform(20, 45) * scale
        m = int(size * 1.3) + 1
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dx, dy = lx - cx, ly - cy
        dist = np.sqrt(dx ** 2 + dy ** 2)
        angle = np.arctan2(dy, dx)
        # 5-petal flower shape
        petal_r = size * (np.cos(5 * angle) * 0.35 + 0.65)
        petal = np.exp(-((dist - petal_r * 0.4) ** 2) / (2 * (size * 0.22) ** 2))
        petal *= (dist < petal_r).astype(np.float32) * rng.uniform(0.7, 1.0)
        center = np.exp(-(dist ** 2) / (2 * (size * 0.12) ** 2)) * 0.9
        flower = petal + center
        # Use max instead of += to prevent saturation from overlap
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], flower)
    return np.clip(out, 0, 1)

def texture_retro_flower_power(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    sz = min(h, w)
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(8, 18)):
        cx,cy = rng.randint(0,w),rng.randint(0,h)
        size = rng.uniform(0.03, 0.08) * sz
        n_p = rng.choice([5,6,7,8])
        m = int(size*1.3)+1
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx,dy = lx-cx,ly-cy; dist = np.sqrt(dx**2+dy**2); angle = np.arctan2(dy,dx)
        petal_r = size*(0.6+0.4*np.cos(n_p*angle))
        petal = np.exp(-((dist-petal_r*0.5)**2)/(2*(size*0.18)**2))*(dist<petal_r)
        flower = petal*rng.uniform(0.6,0.95) + np.exp(-(dist**2)/(2*(size*0.15)**2))*0.7
        out[y0:y1,x0:x1] = np.maximum(out[y0:y1,x0:x1], flower)
    return np.clip(out, 0, 1)

def texture_prehistoric_spot(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    wobble = np.repeat(np.repeat(rng.rand(max(1,h//8+1),max(1,w//8+1)).astype(np.float32),8,0),8,1)[:h,:w]
    for _ in range(rng.randint(8, 20)):
        cx,cy = rng.randint(0,w),rng.randint(0,h)
        rx,ry,angle = rng.uniform(15,50),rng.uniform(15,50),rng.uniform(0,np.pi)
        m = int(max(rx,ry)*1.3)+1
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx,dy = lx-cx,ly-cy
        rdx = dx*np.cos(-angle)-dy*np.sin(-angle)
        rdy = dx*np.sin(-angle)+dy*np.cos(-angle)
        ellipse = (rdx/rx)**2 + (rdy/ry)**2
        spot = np.where(ellipse<1.0, 1.0-ellipse*0.3, 0.0)
        out[y0:y1,x0:x1] += np.clip(spot*(1+wobble[y0:y1,x0:x1]*0.3),0,1)*rng.uniform(0.6,1.0)
    return np.clip(out, 0, 1)

def texture_toon_stars(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    sz = min(h, w)
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(10, 25)):
        cx,cy = rng.randint(0,w),rng.randint(0,h)
        size = rng.uniform(0.02, 0.06) * sz
        n_pts = rng.choice([4,5,6]); intensity = rng.uniform(0.6,1.0)
        m = int(size*1.2)+1
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx,dy = lx-cx,ly-cy; dist = np.sqrt(dx**2+dy**2); angle = np.arctan2(dy,dx)
        star_r = size*(0.4+0.6*np.abs(np.cos(n_pts*angle/2)))
        star = np.where(dist<star_r, 1.0-dist/star_r, 0.0)*intensity
        out[y0:y1,x0:x1] = np.maximum(out[y0:y1,x0:x1], star)
    return np.clip(out, 0, 1)

def texture_toon_speed(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(0,1,w,dtype=np.float32).reshape(1,-1)
    for _ in range(rng.randint(15, 35)):
        cy = rng.uniform(0,1); thick = rng.uniform(0.002,0.008)*scale
        sx, ex = rng.uniform(0,0.3), rng.uniform(0.7,1.0)
        intensity = rng.uniform(0.4, 1.0)
        # Only affect rows near cy
        cy_px = int(cy * h)
        band = int(thick * h * 6) + int(2*scale)
        y0, y1 = max(0, cy_px-band), min(h, cy_px+band)
        if y1<=y0: continue
        ly = np.linspace(y0/h, y1/h, y1-y0, dtype=np.float32).reshape(-1,1)
        line_y = cy + rng.uniform(0,0.01)*np.sin(x*20)
        line = np.exp(-((ly-line_y)**2)/(2*thick**2))
        mask = (x >= sx) & (x <= ex)
        taper = np.clip(np.where(mask, np.minimum((x-sx)/0.1, (ex-x)/0.1), 0), 0, 1)
        out[y0:y1] += line * taper * intensity
    return np.clip(out, 0, 1)

def texture_groovy_swirl(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    x = np.linspace(-1,1,w).reshape(1,-1); y = np.linspace(-1,1,h).reshape(-1,1)
    cx, cy = rng.uniform(-0.3,0.3), rng.uniform(-0.3,0.3)
    dist = np.sqrt((x-cx)**2+(y-cy)**2); angle = np.arctan2(y-cy, x-cx)
    spiral = np.sin(rng.randint(3,7)*angle + rng.uniform(3,8)*dist*2*np.pi)
    out = (spiral*0.5+0.5).astype(np.float32)*0.7 + np.exp(-(dist**2)/2.0).astype(np.float32)*0.3
    return np.clip(out, 0, 1)


def texture_zigzag_stripe(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    x = np.linspace(0,1,w).reshape(1,-1); y = np.linspace(0,1,h).reshape(-1,1)
    freq = rng.randint(4,10)*2*np.pi
    zigzag = y + rng.uniform(0.03,0.1)*np.abs(np.mod(x*rng.uniform(4,12),1.0)*2-1)
    stripe_val = np.sin(zigzag*freq)
    out = np.where(stripe_val > 0, 0.85, 0.15).astype(np.float32) + np.exp(-(stripe_val**2)/(2*0.05**2)).astype(np.float32)*0.3
    return np.clip(out, 0, 1).astype(np.float32)


def texture_toon_cloud(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(4, 10)):
        cx, cy = rng.randint(0,w), rng.randint(0,h)
        n_puffs = rng.randint(3,7); cloud_w = rng.uniform(30,80)
        m = int(cloud_w*0.7)+15
        cy0,cy1 = max(0,cy-m),min(h,cy+m); cx0,cx1 = max(0,cx-int(cloud_w)-10),min(w,cx+int(cloud_w)+10)
        if cy1<=cy0 or cx1<=cx0: continue
        ly = np.arange(cy0,cy1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(cx0,cx1,dtype=np.float32).reshape(1,-1)
        for p in range(n_puffs):
            px = cx+(p-n_puffs/2)*cloud_w/n_puffs; py = cy+rng.uniform(-10,5)
            r = rng.uniform(cloud_w/n_puffs*0.4, cloud_w/n_puffs*0.8)
            out[cy0:cy1,cx0:cx1] += np.exp(-((lx-px)**2+(ly-py)**2)/(2*r**2))*0.6
    return np.clip(out, 0, 1)

def texture_retro_atom(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(3, 8)):
        cx,cy = rng.randint(0,w),rng.randint(0,h)
        size = rng.uniform(20,50) * scale
        m = int(size*1.5)+1
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx,dy = lx-cx,ly-cy; dist = np.sqrt(dx**2+dy**2)
        out[y0:y1,x0:x1] += np.exp(-(dist**2)/(2*(size*0.1)**2))*0.8
        for o in range(rng.randint(2,4)):
            oa = o*np.pi/3+rng.uniform(-0.2,0.2)
            rdx = dx*np.cos(-oa)-dy*np.sin(-oa)
            rdy = dx*np.sin(-oa)+dy*np.cos(-oa)
            out[y0:y1,x0:x1] += np.exp(-((np.sqrt((rdx/size)**2+(rdy/(size*0.3))**2)-1.0)**2)/(2*0.03**2))*0.5
    return np.clip(out, 0, 1)

def texture_polka_pop(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(8, 20)):
        cx,cy,r = rng.randint(0,w),rng.randint(0,h),rng.uniform(12,40)
        m = int(r+12)
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dist = np.sqrt((lx-cx)**2+(ly-cy)**2)
        out[y0:y1,x0:x1] += np.where(dist<r, 0.7, 0.0) + np.exp(-((dist-r)**2)/(2*2.0**2))
    return np.clip(out, 0, 1)

def texture_toon_bones(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(6, 15)):
        cx,cy,size = rng.randint(0,w),rng.randint(0,h),rng.uniform(15,35)
        angle = rng.uniform(0, np.pi)
        m = int(size*0.8)+int(10*scale)
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx,dy = lx-cx,ly-cy
        for a_off in [0, np.pi/2]:
            ba = angle+a_off
            rdx = dx*np.cos(-ba)-dy*np.sin(-ba)
            rdy = dx*np.sin(-ba)+dy*np.cos(-ba)
            out[y0:y1,x0:x1] += np.exp(-(rdy**2)/(2*3.0**2))*(np.abs(rdx)<size*0.4)*0.6
            for end in [-1, 1]:
                kx = cx+end*size*0.4*np.cos(ba)
                ky = cy+end*size*0.4*np.sin(ba)
                for side in [-1, 1]:
                    bx = kx+side*4*np.cos(ba+np.pi/2)
                    by = ky+side*4*np.sin(ba+np.pi/2)
                    out[y0:y1,x0:x1] += np.exp(-((lx-bx)**2+(ly-by)**2)/(2*4.0**2))*0.5
    return np.clip(out, 0, 1)

def texture_cartoon_plaid(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(0,1,w).reshape(1,-1); y = np.linspace(0,1,h).reshape(-1,1)
    for i in range(rng.randint(3, 7)):
        pos, thick = (i+0.5)/5, rng.uniform(0.015,0.04)
        out += np.exp(-((y-pos-0.005*np.sin(x*rng.uniform(3,8)*2*np.pi))**2)/(2*thick**2))*rng.uniform(0.4,0.8)
    for i in range(rng.randint(3, 7)):
        pos, thick = (i+0.5)/5, rng.uniform(0.015,0.04)
        out += np.exp(-((x-pos-0.005*np.sin(y*rng.uniform(3,8)*2*np.pi))**2)/(2*thick**2))*rng.uniform(0.4,0.8)
    return np.clip(out, 0, 1)


def texture_toon_lightning(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0  # proportional to actual output resolution
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(3, 8)):
        sx, sy = rng.randint(w//4,3*w//4), rng.randint(0,h//4)
        points = [(sx, sy)]
        for s in range(rng.randint(4, 8)):
            lx, ly = points[-1]
            dx = int(rng.randint(-30,31)*scale)
            dy = int(rng.randint(15,40)*scale)
            points.append((int(np.clip(lx+dx,0,w-1)), int(np.clip(ly+dy,0,h-1))))
        for i in range(len(points)-1):
            x1,y1 = points[i]; x2,y2 = points[i+1]
            sm = int(20*scale)
            sy0,sy1 = max(0,min(y1,y2)-sm),min(h,max(y1,y2)+sm)
            sx0,sx1 = max(0,min(x1,x2)-sm),min(w,max(x1,x2)+sm)
            if sy1<=sy0 or sx1<=sx0: continue
            la = np.arange(sy0,sy1,dtype=np.float32).reshape(-1,1)
            lb = np.arange(sx0,sx1,dtype=np.float32).reshape(1,-1)
            seg = max(1, int(np.sqrt((x2-x1)**2+(y2-y1)**2)))
            for t_i in range(0, seg, max(1,int(3*scale))):
                t = t_i/seg; px,py = x1+(x2-x1)*t, y1+(y2-y1)*t
                gw = rng.uniform(2,5)*scale
                out[sy0:sy1,sx0:sx1] += np.exp(-((lb-px)**2+(la-py)**2)/(2*gw**2))*0.12
    return np.clip(out, 0, 1)

def texture_hero_burst(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    x = np.linspace(-1,1,w).reshape(1,-1); y = np.linspace(-1,1,h).reshape(-1,1)
    cx, cy = rng.uniform(-0.2,0.2), rng.uniform(-0.2,0.2)
    angle = np.arctan2(y-cy, x-cx)
    rays = np.sin(rng.randint(12,24)*angle)
    out = np.where(rays > 0, 0.85, 0.2).astype(np.float32)
    dist = np.sqrt((x-cx)**2+(y-cy)**2)
    fade = np.exp(-(dist**2)/3.0)
    out = (out*fade + (1-fade)*0.3).astype(np.float32)
    return np.clip(out, 0, 1).astype(np.float32)


def texture_web_pattern(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(-1,1,w,dtype=np.float32).reshape(1,-1)
    y = np.linspace(-1,1,h,dtype=np.float32).reshape(-1,1)
    cx, cy = rng.uniform(-0.3,0.3), rng.uniform(-0.3,0.3)
    dx, dy = x-cx, y-cy
    dist = np.sqrt(dx**2+dy**2)
    angle = np.arctan2(dy, dx)
    n_rad = rng.randint(8, 16)
    # Radials: accumulate all at once using pre-computed angle
    for i in range(n_rad):
        a = i*2*np.pi/n_rad
        out += np.exp(-((np.abs(np.sin(angle-a))*dist)**2)/(2*0.01**2))*0.6
    # Concentric rings
    for i in range(rng.randint(5, 12)):
        r = (i+1)*0.15
        wobble = 0.01*np.sin(angle*n_rad)
        out += np.exp(-((dist-r-wobble)**2)/(2*0.008**2))*0.5
    return np.clip(out, 0, 1)

def texture_dark_knight_scales(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    sw = rng.randint(15, 30); sh = int(sw*0.8)
    for r in range(h//sh+2):
        offset = sw//2 if r%2 else 0
        for c in range(w//sw+2):
            cx, cy = c*sw+offset, r*sh
            y0,y1 = max(0,cy-sh),min(h,cy+sh); x0,x1 = max(0,cx-sw),min(w,cx+sw)
            if y1<=y0 or x1<=x0: continue
            ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
            lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
            nx = (lx-cx)/(sw*0.5); ny = (ly-cy)/(sh*0.5)
            sd = nx**2+(ny-0.3)**2; inside = sd<1.0
            val = (1.0-sd)*inside*0.5 + np.exp(-((sd-0.9)**2)/(2*0.02**2))*inside*0.4
            np.maximum(out[y0:y1,x0:x1], val, out=out[y0:y1,x0:x1])
    return np.clip(out, 0, 1)

def texture_comic_halftone(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    ds = rng.randint(8, 16); angle = rng.uniform(0, np.pi/4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rx = xx*np.cos(angle)+yy*np.sin(angle); ry = -xx*np.sin(angle)+yy*np.cos(angle)
    gx = np.mod(rx, ds)-ds/2; gy = np.mod(ry, ds)-ds/2
    dist = np.sqrt(gx**2+gy**2)
    grad = np.linspace(0.3, 0.9, h).reshape(-1,1).astype(np.float32)
    return np.clip(np.where(dist < ds*0.45*grad, 0.85, 0.15).astype(np.float32), 0, 1)


def texture_pow_burst(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    sz = min(h, w)
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(2, 5)):
        cx, cy = rng.randint(w//4,3*w//4), rng.randint(h//4,3*h//4)
        size = rng.uniform(0.05, 0.12) * sz; n_spikes = rng.randint(8,16)
        m = int(size*1.5)+2
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dx,dy = lx-cx,ly-cy; dist = np.sqrt(dx**2+dy**2); angle = np.arctan2(dy,dx)
        burst_r = size*0.4 + size*0.6*(np.cos(n_spikes*angle)+1)/2
        inside = dist < burst_r
        burst = inside.astype(np.float32) * 0.9
        out[y0:y1,x0:x1] = np.maximum(out[y0:y1,x0:x1], burst)
    return np.clip(out, 0, 1)

def texture_cape_flow(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    x = np.linspace(0,1,w).reshape(1,-1); y = np.linspace(0,1,h).reshape(-1,1)
    out = np.zeros((h, w), dtype=np.float32)
    for i in range(rng.randint(4, 8)):
        freq, phase, amp = rng.uniform(2,5), rng.uniform(0,2*np.pi), rng.uniform(0.05,0.15)
        wave_x = (i+0.5)/6 + amp*np.sin(freq*y*2*np.pi+phase) + amp*0.3*np.sin(freq*2*y*2*np.pi+phase*1.5)
        dist = np.abs(x-wave_x)
        out += np.exp(-(dist**2)/(2*0.015**2))*0.6 + np.where(x<wave_x, 0.3, 0.0)*np.exp(-(dist**2)/(2*0.05**2))
    out *= (0.7 + 0.3*y**0.5)
    return np.clip(out, 0, 1)


def texture_power_bolt(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    sz = min(h, w)
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(3, 7)):
        cx, cy = rng.randint(w//4,3*w//4), rng.randint(h//4,3*h//4)
        size = rng.uniform(0.04, 0.10) * sz; angle = rng.uniform(-0.3, 0.3)
        m = int(size*1.2)+10
        by0,by1 = max(0,cy-m),min(h,cy+m); bx0,bx1 = max(0,cx-m),min(w,cx+m)
        if by1<=by0 or bx1<=bx0: continue
        ly = np.arange(by0,by1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(bx0,bx1,dtype=np.float32).reshape(1,-1)
        pts = [(0,-size*0.5),(size*0.15,-size*0.1),(-size*0.05,0),(size*0.2,size*0.5),(0,size*0.15),(size*0.1,size*0.05)]
        gw_bolt = max(2.0, size * 0.06)
        bolt = np.zeros_like(out[by0:by1,bx0:bx1])
        for i in range(len(pts)-1):
            x1 = cx+pts[i][0]*np.cos(angle)-pts[i][1]*np.sin(angle)
            y1 = cy+pts[i][0]*np.sin(angle)+pts[i][1]*np.cos(angle)
            x2 = cx+pts[i+1][0]*np.cos(angle)-pts[i+1][1]*np.sin(angle)
            y2 = cy+pts[i+1][0]*np.sin(angle)+pts[i+1][1]*np.cos(angle)
            seg = max(1, int(np.sqrt((x2-x1)**2+(y2-y1)**2)))
            step = max(1, int(seg * 0.15))
            for t in range(0, seg, step):
                f = t/seg; px,py = x1+(x2-x1)*f, y1+(y2-y1)*f
                bolt = np.maximum(bolt, np.exp(-((lx-px)**2+(ly-py)**2)/(2*gw_bolt**2))*0.9)
        bolt = np.maximum(bolt, np.exp(-((lx-cx)**2+(ly-cy)**2)/(2*(size*0.3)**2))*0.7)
        out[by0:by1,bx0:bx1] = np.maximum(out[by0:by1,bx0:bx1], bolt)
    return np.clip(out, 0, 1)

def texture_shield_rings(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(2, 5)):
        cx, cy = rng.randint(w//4,3*w//4), rng.randint(h//4,3*h//4)
        max_r = rng.uniform(25,60); n_rings = rng.randint(3,6)
        m = int(max_r*1.3)+1
        y0,y1 = max(0,cy-m),min(h,cy+m); x0,x1 = max(0,cx-m),min(w,cx+m)
        if y1<=y0 or x1<=x0: continue
        ly = np.arange(y0,y1,dtype=np.float32).reshape(-1,1)
        lx = np.arange(x0,x1,dtype=np.float32).reshape(1,-1)
        dist = np.sqrt((lx-cx)**2+(ly-cy)**2)
        roi = out[y0:y1,x0:x1]
        for r_i in range(n_rings):
            r = max_r*(r_i+1)/n_rings
            roi += np.exp(-((dist-r)**2)/(2*(max_r/n_rings*0.4)**2))*0.5
        roi += np.exp(-(dist**2)/(2*(max_r*0.15)**2))*0.7
    return np.clip(out, 0, 1)

def texture_comic_panel(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.ones((h,w),dtype=np.float32)*0.15
    nc, nr = rng.randint(2,5), rng.randint(2,4)
    for r in range(nr):
        for c in range(nc):
            px0 = int(c*w/nc + w*0.02); px1 = int((c+1)*w/nc - w*0.02)
            py0 = int(r*h/nr + h*0.02); py1 = int((r+1)*h/nr - h*0.02)
            if px1<=px0 or py1<=py0: continue
            ly = np.arange(py0,py1,dtype=np.float32).reshape(-1,1)
            lx = np.arange(px0,px1,dtype=np.float32).reshape(1,-1)
            xn = (lx-px0)/(px1-px0); yn = (ly-py0)/(py1-py0)
            bw = 0.008*(px1-px0)
            borders = np.maximum(np.exp(-((lx-px0)**2)/(2*bw**2)), np.exp(-((lx-px1)**2)/(2*bw**2)))
            borders = np.maximum(borders, np.exp(-((ly-py0)**2)/(2*bw**2)))
            borders = np.maximum(borders, np.exp(-((ly-py1)**2)/(2*bw**2)))
            out[py0:py1,px0:px1] = borders*0.8 + rng.uniform(0.2,0.5)
    return np.clip(out, 0, 1)

def texture_power_aura(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(-1,1,w,dtype=np.float32).reshape(1,-1)
    y = np.linspace(-1,1,h,dtype=np.float32).reshape(-1,1)
    cx, cy = rng.uniform(-0.2,0.2), rng.uniform(-0.1,0.1)
    dist = np.sqrt((x-cx)**2+(y-cy)**2)
    angle = np.arctan2(y-cy, x-cx)
    for _ in range(rng.randint(3, 6)):
        r = rng.uniform(0.3,0.8)
        wobble = 0.05*np.sin(rng.uniform(4,12)*angle+rng.uniform(0,2*np.pi))
        out += np.exp(-((dist-r-wobble)**2)/(2*0.03**2))*rng.uniform(0.3,0.6)
    out += np.exp(-(dist**2)/(2*0.15**2))*0.7
    for _ in range(rng.randint(6, 14)):
        ta = rng.uniform(0, 2*np.pi)
        out += np.exp(-((np.abs(np.sin(angle-ta))*dist)**2)/(2*0.02**2))*np.exp(-(dist**2)/1.5)*0.25
    return np.clip(out, 0, 1)

def texture_villain_stripe(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    x = np.linspace(0,1,w,dtype=np.float32).reshape(1,-1)
    y = np.linspace(0,1,h,dtype=np.float32).reshape(-1,1)
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(4, 9)):
        slope = rng.uniform(0.3,2.0)*rng.choice([-1,1]); intercept = rng.uniform(-0.5,1.5)
        thick = rng.uniform(0.01,0.04)
        dist = np.abs(y-slope*x-intercept)/np.sqrt(1+slope**2)
        along = (y-slope*x-intercept+1)/2
        taper = np.clip((along-rng.uniform(0,0.3))/0.1,0,1)*np.clip((rng.uniform(0.7,1.0)-along)/0.1,0,1)
        stripe = np.exp(-(dist**2)/(2*thick**2))*taper*rng.uniform(0.5,1.0)
        out = np.maximum(out, stripe)
    return np.clip(out, 0, 1)

def texture_gamma_pulse(shape, seed):
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(-1,1,w,dtype=np.float32).reshape(1,-1)
    y = np.linspace(-1,1,h,dtype=np.float32).reshape(-1,1)
    for _ in range(rng.randint(1, 4)):
        cx, cy = rng.uniform(-0.5,0.5), rng.uniform(-0.5,0.5)
        dist = np.sqrt((x-cx)**2+(y-cy)**2)
        for p in range(rng.randint(5, 12)):
            r = (p+1)*0.12; pw = 0.02+p*0.003
            out += np.exp(-((dist-r)**2)/(2*pw**2))*(1.0/(p+1))*0.5
        out += np.exp(-(dist**2)/(2*0.08**2))*0.8
    out += np.repeat(np.repeat(rng.rand(max(1,h//4+1),max(1,w//4+1)).astype(np.float32),4,0),4,1)[:h,:w]*0.1
    return np.clip(out, 0, 1)

EXPANSION_PATTERNS = {
    # Group 1: CARBON & WEAVE (new entries only — carbon_fiber, forged_carbon already exist)
    "carbon_4x4":       {"texture_fn": texture_carbon_4x4, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Larger 4-harness satin weave carbon"},
    "carbon_spread_tow":{"texture_fn": texture_spread_tow, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Flat spread tow ultra-thin carbon tape"},
    "carbon_uni":       {"texture_fn": texture_carbon_uni, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "All fibers running one direction"},
    "tweed_weave":      {"texture_fn": texture_tweed_weave, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Loose irregular tweed textile pattern"},
    "basket_weave":     {"texture_fn": texture_basket_weave, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Over-under basket weave pattern"},
    "chainlink":        {"texture_fn": texture_chainlink, "paint_fn": ppaint_tex_chainlink, "variable_cc": False, "desc": "Chain-link fence diagonal wire grid"},
    "kevlar_weave":     {"texture_fn": texture_kevlar_weave_pat, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Tight aramid fiber golden weave"},
    "nanoweave":        {"texture_fn": texture_nanoweave, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Microscopic tight-knit nano fiber pattern"},
    "exhaust_wrap":     {"texture_fn": texture_exhaust_wrap, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Heat-resistant exhaust header wrap textile"},
    "harness_weave":    {"texture_fn": texture_harness_weave, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Racing harness safety webbing pattern"},
    # Group 2: METAL & INDUSTRIAL (new entries — diamond_plate, hex_mesh etc exist)
    "rivet_grid":       {"texture_fn": texture_rivet_grid, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Evenly spaced industrial rivet dots"},
    "corrugated":       {"texture_fn": texture_corrugated, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Corrugated sheet metal parallel ridges"},
    "perforated":       {"texture_fn": texture_perforated, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Evenly punched round hole grid"},
    "expanded_metal":   {"texture_fn": texture_expanded_metal, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Stretched diamond-shape expanded mesh"},
    "grating":          {"texture_fn": texture_grating, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Industrial floor grating parallel bars"},
    "knurled":          {"texture_fn": texture_knurled, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Machine knurling diagonal cross-hatch grip"},
    "roll_cage":        {"texture_fn": texture_roll_cage, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Tubular roll cage safety bar grid structure"},
    # Group 3: NATURE & ORGANIC (new entries — wood_grain, marble etc exist)
    "tree_bark":        {"texture_fn": texture_tree_bark, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Rough furrowed tree bark texture"},
    "coral_reef":       {"texture_fn": texture_coral_reef, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Organic branching coral growth structure"},
    "river_stone":      {"texture_fn": texture_river_stone, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Smooth rounded river pebble mosaic"},
    "glacier_crack":    {"texture_fn": texture_glacier_crack, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Deep blue-white glacial ice fissure network"},
    # Group 4: GEOMETRIC (new entries — chevron, houndstooth etc exist)
    "herringbone":      {"texture_fn": texture_herringbone, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "V-shaped zigzag brick/tile pattern"},
    "argyle":           {"texture_fn": texture_argyle, "paint_fn": ppaint_contrast_light, "variable_cc": False, "desc": "Diamond/rhombus overlapping argyle pattern"},
    "greek_key":        {"texture_fn": texture_greek_key, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Continuous right-angle meander border"},
    "art_deco":         {"texture_fn": texture_art_deco, "paint_fn": ppaint_glow_gold, "variable_cc": False, "desc": "1920s geometric fan/sunburst motif"},
    "tessellation":     {"texture_fn": texture_tessellation, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Interlocking M.C. Escher-style tile shapes"},
    "yin_yang":         {"texture_fn": texture_yin_yang, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Repeating yin-yang circular duality symbol grid"},
    # Group 5: RACING & MOTORSPORT (new entries — tire_tread exists)
    "checkered_flag":   {"texture_fn": texture_checkered_flag, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Classic racing checkered flag grid"},
    "racing_stripe":    {"texture_fn": texture_racing_stripe, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Bold dual center racing stripes"},
    "starting_grid":    {"texture_fn": texture_starting_grid, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Grid slot number positions track layout"},
    "tire_smoke":       {"texture_fn": texture_tire_smoke, "paint_fn": ppaint_darken_light, "variable_cc": False, "desc": "Burnout tire smoke wisps and haze"},
    "skid_marks":       {"texture_fn": texture_skid_marks, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Black rubber tire skid marks streaks"},
    "asphalt_texture":  {"texture_fn": texture_asphalt_texture, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Road surface aggregate texture"},
    "pit_lane_marks":   {"texture_fn": texture_pit_lane_marks, "paint_fn": ppaint_contrast_light, "variable_cc": False, "desc": "Pit lane boundary lines and markings"},
    "lap_counter":      {"texture_fn": texture_lap_counter, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Repeating tally/hash mark lap counter"},
    "sponsor_fade":     {"texture_fn": texture_sponsor_fade, "paint_fn": ppaint_darken_light, "variable_cc": True, "desc": "Gradient fade zones typical of sponsor areas"},
    "rooster_tail":     {"texture_fn": texture_rooster_tail, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Dirt spray rooster tail splash pattern"},
    "victory_confetti": {"texture_fn": texture_victory_confetti, "paint_fn": ppaint_glow_gold, "variable_cc": False, "desc": "Scattered celebration confetti and streamers"},
    "trophy_laurel":    {"texture_fn": texture_trophy_laurel, "paint_fn": ppaint_glow_gold, "variable_cc": False, "desc": "Victory laurel wreath repeating motif"},
    "rpm_gauge":        {"texture_fn": texture_rpm_gauge, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Tachometer arc needle sweep pattern"},
    "finish_line":      {"texture_fn": texture_finish_line, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Bold start/finish line checkered band"},
    "aero_flow":        {"texture_fn": texture_aero_flow, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Aerodynamic airflow visualization streamlines"},
    "brake_dust":       {"texture_fn": texture_brake_dust, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Fine metallic brake pad dust scatter particles"},
    "drift_marks":      {"texture_fn": texture_drift_marks, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Curved rubber tire drift arc marks"},
    "podium_stripe":    {"texture_fn": texture_podium_stripe, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Wide bold victory podium horizontal bands"},
    "rev_counter":      {"texture_fn": texture_rev_counter, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Tachometer dial radial tick mark sweep"},
    "speed_lines":      {"texture_fn": texture_speed_lines, "paint_fn": ppaint_darken_light, "variable_cc": False, "desc": "Horizontal motion blur speed lines"},
    "track_map":        {"texture_fn": texture_track_map, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Race track circuit layout line map"},
    "turbo_swirl":      {"texture_fn": texture_turbo_swirl, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Turbocharger impeller spiral blade vortex"},
    "wind_tunnel":      {"texture_fn": texture_wind_tunnel, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Wind tunnel airflow visualization wave bands"},
    # Group 6: TEXTILE & FABRIC (new entries — snake_skin, leopard, fishnet exist)
    "denim":            {"texture_fn": texture_denim, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Blue jean diagonal twill weave"},
    "leather_grain":    {"texture_fn": texture_leather_grain, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Natural grain leather pebble texture"},
    "quilted":          {"texture_fn": texture_quilted, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Diamond-stitched quilted padding pattern"},
    "velvet":           {"texture_fn": texture_velvet, "paint_fn": ppaint_darken_light, "variable_cc": False, "desc": "Soft pile velvet nap direction texture"},
    "burlap":           {"texture_fn": texture_burlap, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Coarse loose-weave burlap/hessian cloth"},
    "lace":             {"texture_fn": texture_lace, "paint_fn": ppaint_darken_light, "variable_cc": True, "desc": "Delicate ornamental lace lacework pattern"},
    "silk_weave":       {"texture_fn": texture_silk_weave, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Fine lustrous silk satin weave sheen"},
    # Group 7: TECH & DIGITAL (new entries — circuit_board, hologram etc exist)
    "binary_code":      {"texture_fn": texture_binary_code, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Streaming 0s and 1s binary data columns"},
    "matrix_rain":      {"texture_fn": texture_matrix_rain, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Falling green character rain columns"},
    "qr_code":          {"texture_fn": texture_qr_code, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Dense QR code-style square block grid"},
    "pixel_grid":       {"texture_fn": texture_pixel_grid, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Retro 8-bit pixel block mosaic pattern"},
    "data_stream":      {"texture_fn": texture_data_stream, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Flowing horizontal data packet streams"},
    "wifi_waves":       {"texture_fn": texture_wifi_waves, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Concentric signal broadcast wave arcs"},
    "glitch_scan":      {"texture_fn": texture_glitch_scan, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Horizontal glitch scanline displacement bands"},
    # Group 8: WEATHER & ELEMENTS (new entries — lightning, plasma etc exist)
    "tornado":          {"texture_fn": texture_tornado, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Spiraling funnel vortex rotation"},
    "sandstorm":        {"texture_fn": texture_sandstorm, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Dense blowing sand particle streaks"},
    "hailstorm":        {"texture_fn": texture_hailstorm, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Dense scattered impact crater dimples"},
    "aurora_bands":     {"texture_fn": texture_aurora_bands, "paint_fn": ppaint_glow_green, "variable_cc": True, "desc": "Northern lights wavy curtain bands"},
    "solar_flare":      {"texture_fn": texture_solar_flare, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Erupting coronal mass ejection tendrils"},
    "nitro_burst":      {"texture_fn": texture_nitro_burst, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Nitrous oxide explosion radial burst flare"},
    # Group 9: ARTISTIC & CULTURAL (new entries — mosaic, damascus etc exist)
    "fleur_de_lis":     {"texture_fn": texture_fleur_de_lis, "paint_fn": ppaint_glow_gold, "variable_cc": False, "desc": "New Orleans royal French lily repeating motif"},
    "tribal_flame":     {"texture_fn": texture_tribal_flame, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Flowing tribal tattoo flame curves"},
    "japanese_wave":    {"texture_fn": texture_japanese_wave, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Kanagawa-style great wave curling crests"},
    "aztec":            {"texture_fn": texture_aztec, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Angular stepped Aztec/Mayan geometric blocks"},
    "mandala":          {"texture_fn": texture_mandala, "paint_fn": ppaint_glow_purple, "variable_cc": False, "desc": "Radial symmetry mandala flower pattern"},
    "paisley":          {"texture_fn": texture_paisley, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Teardrop curved paisley ornamental pattern"},
    "steampunk_gears":  {"texture_fn": texture_steampunk_gears, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Interlocking clockwork gear wheel array"},
    "norse_rune":       {"texture_fn": texture_norse_rune, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Elder Futhark rune symbol repeating grid"},
    # Group 10: DAMAGE & WEAR (new entries — battle_worn, acid_wash etc exist)
    "bullet_holes":     {"texture_fn": texture_bullet_holes, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Scattered impact penetration holes with stress cracks"},
    "shrapnel":         {"texture_fn": texture_shrapnel, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Irregular shrapnel damage fragment gouges"},
    "road_rash":        {"texture_fn": texture_road_rash, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Sliding contact abrasion scrape marks"},
    "rust_bloom":       {"texture_fn": texture_rust_bloom, "paint_fn": ppaint_tint_rust, "variable_cc": False, "desc": "Expanding rust spot corrosion blooms"},
    "peeling_paint":    {"texture_fn": texture_peeling_paint, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Curling paint peel flake patches"},
    "g_force":          {"texture_fn": texture_g_force, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Gravitational force distortion radial compression"},
    "spark_scatter":    {"texture_fn": texture_spark_scatter, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Scattered grinding spark hot particle spray"},
    # Group 11: GOTHIC & DARK (new entries — skull, spiderweb etc exist)
    "gothic_cross":     {"texture_fn": texture_gothic_cross, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Ornate gothic cathedral cross repeating grid"},
    "iron_cross":       {"texture_fn": texture_iron_cross, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Bold Iron Cross/Maltese cross motif array"},
    "skull_wings":      {"texture_fn": texture_skull_wings, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Affliction-style winged skull ornamental spread"},
    "gothic_scroll":    {"texture_fn": texture_gothic_scroll, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Flowing dark ornamental scroll filigree"},
    "thorn_vine":       {"texture_fn": texture_thorn_vine, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Twisted thorny vine dark botanical"},
    "pentagram":        {"texture_fn": texture_pentagram, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Five-pointed star geometric array"},
    # Group 12: MEDICAL & SCIENCE (all new)
    "ekg":              {"texture_fn": texture_ekg, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Heartbeat EKG monitor line pulse — THE SHOKKER SIGNATURE"},
    "dna_helix":        {"texture_fn": texture_dna_helix, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Double-helix DNA strand spiral pattern"},
    "molecular":        {"texture_fn": texture_molecular, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Ball-and-stick molecular bond diagram grid"},
    "atomic_orbital":   {"texture_fn": texture_atomic_orbital, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Electron cloud probability orbital rings"},
    "fingerprint":      {"texture_fn": texture_fingerprint, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Swirling concentric fingerprint ridge lines"},
    "neuron_network":   {"texture_fn": texture_neuron_network, "paint_fn": ppaint_glow_purple, "variable_cc": False, "desc": "Branching neural dendrite connection web"},
    "pulse_monitor":    {"texture_fn": texture_pulse_monitor, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Multi-line vital signs monitor waveforms"},
    "biohazard":        {"texture_fn": texture_biohazard, "paint_fn": ppaint_tint_toxic, "variable_cc": False, "desc": "Repeating biohazard trefoil warning symbol"},
    # Group 13: ANIMAL & WILDLIFE (new entries — camo, multicam, dazzle exist)
    "zebra":            {"texture_fn": texture_zebra, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Bold black-white zebra stripe pattern"},
    "tiger_stripe":     {"texture_fn": texture_tiger_stripe, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Organic tiger stripe broken bands"},
    "giraffe":          {"texture_fn": texture_giraffe, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Irregular polygon giraffe spot patch network"},
    "crocodile":        {"texture_fn": texture_crocodile, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Deep embossed crocodile hide square scales"},
    "feather":          {"texture_fn": texture_feather, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Layered overlapping bird feather barb pattern"},
    # Group 14: SHOKK SERIES (new entries — ember_mesh, turbine exist)
    "shokk_bolt":       {"texture_fn": texture_shokk_bolt, "paint_fn": ppaint_glow_neon, "variable_cc": False, "desc": "Jagged lightning bolt Shokker logo strike pattern"},
    "shokk_pulse_wave": {"texture_fn": texture_shokk_pulse_wave, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Radiating EKG-style pulse expanding outward"},
    "shokk_fracture":   {"texture_fn": texture_shokk_fracture, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Impact point with radiating fracture cracks"},
    "shokk_hex":        {"texture_fn": texture_shokk_hex, "paint_fn": ppaint_glow_neon, "variable_cc": False, "desc": "Hexagonal cells with electric edge glow"},
    "shokk_scream":     {"texture_fn": texture_shokk_scream, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Sound wave distortion from center blast"},
    "shokk_grid":       {"texture_fn": texture_shokk_grid, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Perspective-warped digital grid tunnel"},
    # Group 15: ABSTRACT & EXPERIMENTAL (new entries — stardust, interference exist)
    "sound_wave":       {"texture_fn": texture_sound_wave, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Audio waveform amplitude oscillation"},
    "morse_code":       {"texture_fn": texture_morse_code, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Dots and dashes Morse code band lines"},
    "fractal":          {"texture_fn": texture_fractal, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Self-similar Mandelbrot/Julia fractal branching"},
    "optical_illusion": {"texture_fn": texture_optical_illusion, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Moire interference impossible geometry"},
    "biomechanical":    {"texture_fn": texture_biomechanical, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "H.R. Giger-style organic-mechanical hybrid surface"},
    "voronoi_shatter":  {"texture_fn": texture_voronoi_shatter, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Clean voronoi cell shatter with sharp edges"},
    # Group 16: FLAMES (new)
    "classic_hotrod":      {"texture_fn": texture_classic_hotrod, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Classic hot rod flame tongues rising from bottom"},
    "ghost_flames":        {"texture_fn": texture_ghost_flames, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Translucent ghostly wisp flames"},
    "pinstripe_flames":    {"texture_fn": texture_pinstripe_flames, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Thin outlined pinstripe flame borders"},
    "fire_lick":           {"texture_fn": texture_fire_lick, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Tiled repeating flame lick tongues"},
    "inferno":             {"texture_fn": texture_inferno, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Dense chaotic full-coverage inferno blaze"},
    "fireball":            {"texture_fn": texture_fireball, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Explosive fireball burst with radial energy"},
    "hellfire":            {"texture_fn": texture_hellfire, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Jagged lightning-bolt hellfire streaks"},
    "wildfire":            {"texture_fn": texture_wildfire, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Multi-scale wildfire smoke and heat haze"},
    "flame_fade":          {"texture_fn": texture_flame_fade, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Soft gaussian flame fade with wobble"},
    "blue_flame":          {"texture_fn": texture_blue_flame, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Tight concentrated blue propane flame tips"},
    "torch_burn":          {"texture_fn": texture_torch_burn, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Directional torch cone burn pattern"},
    "ember_scatter":       {"texture_fn": texture_ember_scatter, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Floating ember particle scatter field"},
    # Group 17: SKATE & SURF (new)
    "wave_curl":           {"texture_fn": texture_wave_curl, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Rolling ocean wave curl bands"},
    "ocean_foam":          {"texture_fn": texture_ocean_foam, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Scattered ocean foam bubble rings"},
    "palm_frond":          {"texture_fn": texture_palm_frond, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Tropical palm frond leaf spread"},
    "tiki_totem":          {"texture_fn": texture_tiki_totem, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Carved tiki totem face grid"},
    "grip_tape":           {"texture_fn": texture_grip_tape, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Skateboard grip tape grit surface"},
    "halfpipe":            {"texture_fn": texture_halfpipe, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Curved halfpipe ramp cross-section"},
    "bamboo_stalk":        {"texture_fn": texture_bamboo_stalk, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Vertical bamboo stalk segments with nodes"},
    "surf_stripe":         {"texture_fn": texture_surf_stripe, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Retro surfboard racing stripe bands"},
    "board_wax":           {"texture_fn": texture_board_wax, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Circular board wax application swirls"},
    "tropical_leaf":       {"texture_fn": texture_tropical_leaf, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Large tropical monstera leaf shapes"},
    "rip_tide":            {"texture_fn": texture_rip_tide, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Turbulent rip tide interference waves"},
    "hibiscus":            {"texture_fn": texture_hibiscus, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Hawaiian hibiscus flower scatter"},
    # Group 18: CARTOONS (new)
    "retro_flower_power":  {"texture_fn": texture_retro_flower_power, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Groovy retro daisy flower power scatter"},
    "prehistoric_spot":    {"texture_fn": texture_prehistoric_spot, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Flintstones-style organic blob spots"},
    "toon_stars":          {"texture_fn": texture_toon_stars, "paint_fn": ppaint_glow_gold, "variable_cc": False, "desc": "Cartoon starburst scatter field"},
    "toon_speed":          {"texture_fn": texture_toon_speed, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Anime speed line motion streaks"},
    "groovy_swirl":        {"texture_fn": texture_groovy_swirl, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Psychedelic spiral swirl pattern"},
    "zigzag_stripe":       {"texture_fn": texture_zigzag_stripe, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Bold cartoon zigzag chevron stripes"},
    "toon_cloud":          {"texture_fn": texture_toon_cloud, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Puffy cartoon cumulus cloud puffs"},
    "retro_atom":          {"texture_fn": texture_retro_atom, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Retro atomic age orbital diagram"},
    "polka_pop":           {"texture_fn": texture_polka_pop, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Oversized pop-art polka dot scatter"},
    "toon_bones":          {"texture_fn": texture_toon_bones, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Cartoon crossbones skull motif"},
    "cartoon_plaid":       {"texture_fn": texture_cartoon_plaid, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Wobbly cartoon plaid tartan grid"},
    "toon_lightning":      {"texture_fn": texture_toon_lightning, "paint_fn": ppaint_glow_neon, "variable_cc": False, "desc": "Cartoon electric lightning bolt scatter"},
    # Group 19: COMICS (new)
    "hero_burst":          {"texture_fn": texture_hero_burst, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Manga-style radial action burst rays"},
    "web_pattern":         {"texture_fn": texture_web_pattern, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Spider web radial spoke and ring pattern"},
    "dark_knight_scales":  {"texture_fn": texture_dark_knight_scales, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Overlapping armored bat-scale grid"},
    "comic_halftone":      {"texture_fn": texture_comic_halftone, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Classic Ben-Day dot halftone gradient"},
    "pow_burst":           {"texture_fn": texture_pow_burst, "paint_fn": ppaint_glow_neon, "variable_cc": False, "desc": "Comic POW explosion starburst"},
    "cape_flow":           {"texture_fn": texture_cape_flow, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Flowing superhero cape fabric folds"},
    "power_bolt":          {"texture_fn": texture_power_bolt, "paint_fn": ppaint_glow_neon, "variable_cc": False, "desc": "Zig-zag power bolt lightning strike"},
    "shield_rings":        {"texture_fn": texture_shield_rings, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Concentric vibranium shield rings"},
    "comic_panel":         {"texture_fn": texture_comic_panel, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Comic book panel layout grid borders"},
    "power_aura":          {"texture_fn": texture_power_aura, "paint_fn": ppaint_glow_purple, "variable_cc": False, "desc": "Radiating energy aura halo rings"},
    "villain_stripe":      {"texture_fn": texture_villain_stripe, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Diagonal villain menace slash stripes"},
    "gamma_pulse":         {"texture_fn": texture_gamma_pulse, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Expanding gamma radiation pulse rings"},
}


# ================================================================
# SPEC FUNCTION FACTORIES FOR SPECIALS/MONOLITHICS
# ================================================================
# Spec fn signature: spec_fn(shape, mask, seed, sm) -> uint8 RGBA spec array
# R=Metallic, G=Roughness, B=Clearcoat (inverted: B=16 = MAX CC), A=SpecMask=255

def make_flat_spec_fn(M, R, CC, noise_M=0, noise_R=0, noise_scales=None, noise_weights=None):
    """Factory: simple flat spec with optional noise variation."""
    def fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        if noise_scales and noise_M > 0:
            mn = _multi_scale_noise(shape, noise_scales, noise_weights or [0.3, 0.4, 0.3], seed + 100)
            spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask) + mn * noise_M * sm * mask, 0, 255).astype(np.uint8)
        else:
            spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        if noise_scales and noise_R > 0:
            rn = _multi_scale_noise(shape, noise_scales, noise_weights or [0.3, 0.4, 0.3], seed + 200)
            spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask) + rn * noise_R * sm * mask, 0, 255).astype(np.uint8)
        else:
            spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,2] = CC
        spec[:,:,3] = 255
        return spec
    return fn

def make_chameleon_spec_fn(M_base, R_base, CC, color_shift_range=60, wave_scales=None):
    """Factory: chameleon/color-shift spec with angle-dependent M/R variation."""
    def fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        h, w = shape
        y, x = _get_mgrid(shape)
        angle = (x / max(w, 1) + y / max(h, 1)) * 0.5
        wn = _multi_scale_noise(shape, wave_scales or [8, 16, 32], [0.3, 0.4, 0.3], seed + 50)
        shift = np.sin((angle + wn * 0.3) * np.pi * 2) * color_shift_range * sm
        spec[:,:,0] = np.clip((M_base + shift) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,1] = np.clip((R_base - shift * 0.3) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,2] = CC
        spec[:,:,3] = 255
        return spec
    return fn

def make_prizm_spec_fn(M_base, R_base, CC, num_bands=8, band_scales=None):
    """Factory: prizm/panel-aware color shift spec with banded regions."""
    def fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        h, w = shape
        # Panel bands from noise
        bands = _multi_scale_noise(shape, band_scales or [32, 64, 128], [0.3, 0.4, 0.3], seed + 75)
        band_idx = (np.clip(bands * 0.5 + 0.5, 0, 1) * num_bands).astype(np.float32)
        m_var = np.sin(band_idx * np.pi * 2 / num_bands) * 40 * sm
        r_var = np.cos(band_idx * np.pi * 2 / num_bands) * 20 * sm
        spec[:,:,0] = np.clip((M_base + m_var) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,1] = np.clip((R_base + r_var) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,2] = CC
        spec[:,:,3] = 255
        return spec
    return fn

def make_effect_spec_fn(M_base, R_base, CC, effect_type="gradient"):
    """Factory: visual effect spec — gradient, radial, noise-driven, etc."""
    def fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        h, w = shape
        if effect_type == "gradient":
            y, x = _get_mgrid(shape)
            grad = y / max(h, 1)
            m_mod = grad * 80 * sm
            r_mod = (1 - grad) * 60 * sm
        elif effect_type == "radial":
            y, x = _get_mgrid(shape)
            cy, cx = h / 2, w / 2
            dist = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w) * 2
            dist = np.clip(dist, 0, 1)
            m_mod = dist * 60 * sm
            r_mod = (1 - dist) * 40 * sm
        elif effect_type == "noise":
            noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 500)
            m_mod = noise * 50 * sm
            r_mod = noise * 30 * sm
        elif effect_type == "bands":
            y, x = _get_mgrid(shape)
            bands = np.sin(y * 0.05) * 0.5 + 0.5
            m_mod = bands * 70 * sm
            r_mod = (1 - bands) * 40 * sm
        else:
            m_mod = np.zeros(shape, dtype=np.float32)
            r_mod = np.zeros(shape, dtype=np.float32)
        spec[:,:,0] = np.clip((M_base + m_mod) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,1] = np.clip((R_base + r_mod) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,2] = CC
        spec[:,:,3] = 255
        return spec
    return fn


# ================================================================
# SPECIAL PAINT FUNCTION FACTORIES (for monolithic finishes)
# ================================================================

def make_colorshift_paint_fn(hue_offsets, shift_speed=2.0):
    """Factory: color-shift paint — shifts hue based on spatial gradient."""
    def fn(paint, shape, mask, seed, pm, bb):
        h, w = shape
        y, x = _get_mgrid(shape)
        angle = (x / max(w, 1) + y / max(h, 1)) * 0.5
        noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100)
        phase = np.clip((angle + noise * 0.2) * shift_speed, 0, 1)
        for c in range(3):
            shift = 0.0
            for i, offset in enumerate(hue_offsets):
                weight = np.clip(1.0 - abs(phase - i / max(len(hue_offsets) - 1, 1)) * len(hue_offsets), 0, 1)
                shift += offset[c] * weight
            paint[:,:,c] = np.clip(paint[:,:,c] + shift * 0.06 * pm * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_weather_paint_fn(darken=0.0, desat=0.0, tint_rgb=None, noise_str=0.0):
    """Factory: weather/element paint effect — combines darken, desaturation, tinting, noise."""
    def fn(paint, shape, mask, seed, pm, bb):
        if desat > 0:
            gray = paint.mean(axis=2, keepdims=True)
            paint = paint * (1 - desat * pm * mask[:,:,np.newaxis]) + gray * desat * pm * mask[:,:,np.newaxis]
        if darken > 0:
            paint = np.clip(paint - darken * pm * mask[:,:,np.newaxis], 0, 1)
        if tint_rgb:
            for c in range(3):
                paint[:,:,c] = np.clip(paint[:,:,c] + tint_rgb[c] * 0.04 * pm * mask, 0, 1)
        if noise_str > 0:
            noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 300)
            paint = np.clip(paint + noise[:,:,np.newaxis] * noise_str * pm * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

# ================================================================
# COLOR CHANGING CORE ALGORITHMS — Self-contained implementations
# that mirror the main engine's quality (multi-directional sine waves,
# HSV hue ramps, dithered Fresnel, panel-aware color ramps).
# These replace the weak factory functions for all Color Changing finishes.
# ================================================================

def _hsv_to_rgb_24k(h_arr, s_arr, v_arr):
    """Vectorized HSV to RGB. h/s/v all in [0,1]. Returns (R, G, B) float32."""
    h6 = (h_arr * 6.0) % 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i
    p = v_arr * (1.0 - s_arr)
    q = v_arr * (1.0 - s_arr * f)
    t = v_arr * (1.0 - s_arr * (1.0 - f))
    r = np.where(i == 0, v_arr, np.where(i == 1, q, np.where(i == 2, p,
        np.where(i == 3, p, np.where(i == 4, t, v_arr)))))
    g = np.where(i == 0, t, np.where(i == 1, v_arr, np.where(i == 2, v_arr,
        np.where(i == 3, q, np.where(i == 4, p, p)))))
    b = np.where(i == 0, p, np.where(i == 1, p, np.where(i == 2, t,
        np.where(i == 3, v_arr, np.where(i == 4, v_arr, q)))))
    return r.astype(np.float32), g.astype(np.float32), b.astype(np.float32)


# --- CHAMELEON CORE ---

def _spec_chameleon_24k(shape, mask, seed, sm):
    """Chameleon spec — ultra-high metallic (M=220) for Fresnel color shift + sharp reflections."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    m_noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.3, 0.35, 0.2], seed + 701)
    M = np.clip(220 + m_noise * 15 * sm, 180, 250)
    cc_noise = _multi_scale_noise(shape, [16, 32, 48], [0.3, 0.4, 0.3], seed + 702)
    CC = np.clip(16 + cc_noise * 3 * sm, 14, 20)
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(15 * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _chameleon_core_24k(paint, shape, mask, seed, pm, bb, primary_hue, shift_range):
    """Full chameleon gradient paint — 8 multi-directional sine waves + Perlin noise
    mapped through HSV hue ramp. Mirrors main engine's paint_chameleon_gradient."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    field = (
        np.sin(yf * 0.012 + xf * 0.008) * 0.18 +
        np.sin(yf * 0.006 - xf * 0.015) * 0.14 +
        np.sin((yf + xf) * 0.022) * 0.15 +
        np.sin((yf - xf * 0.7) * 0.019) * 0.13 +
        np.sin(yf * 0.028 + xf * 0.004) * 0.10 +
        np.sin((yf * 0.8 + xf * 1.2) * 0.035) * 0.10 +
        np.sin((yf * 1.3 - xf * 0.6) * 0.042) * 0.10 +
        np.sin((yf * 0.5 + xf * 0.9) * 0.055) * 0.10
    )
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 711)
    field = field + noise * 0.20
    field = (field - field.min()) / (field.max() - field.min() + 1e-8)
    hue_start = primary_hue / 360.0
    hue_shift = shift_range / 360.0
    hue_map = (hue_start + field * hue_shift) % 1.0
    sat = np.full_like(hue_map, 0.85)
    val = np.full_like(hue_map, 0.75)
    r_new, g_new, b_new = _hsv_to_rgb_24k(hue_map, sat, val)
    blend = 0.7 * pm
    for c, ch in enumerate([r_new, g_new, b_new]):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - blend * mask) + ch * blend * mask, 0, 1)
    paint = np.clip(paint + bb * 1.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


# --- COLOR SHIFT v3 CORE (Dithered Fresnel) ---

def _cs_field_24k(shape, seed):
    """Low-frequency sweeping gradient field for color shift — mirrors main engine."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    f1 = np.sin(yf * 0.003 + xf * 0.002) * 0.30
    f2 = np.sin(yf * 0.002 - xf * 0.004) * 0.25
    f3 = np.sin((yf + xf) * 0.0025) * 0.20
    cy, cx = h * 0.45, w * 0.5
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2).astype(np.float32)
    f4 = np.sin(dist * 0.003) * 0.15
    field = f1 + f2 + f3 + f4
    noise = _multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 5001)
    field = field + noise * 0.08
    fmin, fmax = field.min(), field.max()
    return (field - fmin) / (fmax - fmin + 1e-8)

def _cs_dither_24k(shape, seed):
    """Per-pixel dither mask for stochastic population mixing."""
    rng = np.random.RandomState(seed + 6000)
    return rng.rand(shape[0], shape[1]).astype(np.float32)

def _spec_cs_24k(shape, mask, seed, sm, spec_a=None, spec_b=None):
    """Color Shift v3 spec — dual-population dithered Fresnel. Mirrors main engine."""
    if spec_a is None:
        spec_a = {'M': 235, 'R': 8, 'CC': 16}
    if spec_b is None:
        spec_b = {'M': 200, 'R': 28, 'CC': 22}
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    field = _cs_field_24k(shape, seed)
    dither = _cs_dither_24k(shape, seed)
    is_b = (dither >= (1.0 - field)).astype(np.float32)
    is_a = 1.0 - is_b
    M_arr = is_a * spec_a['M'] + is_b * spec_b['M']
    R_arr = is_a * spec_a['R'] + is_b * spec_b['R']
    CC_arr = is_a * spec_a['CC'] + is_b * spec_b['CC']
    m_noise = _multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 6100)
    M_arr = M_arr + m_noise * 5 * sm
    spec[:,:,0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, hue_shift, sat_delta=0.10, val_delta=-0.05):
    """Color Shift adaptive — reads zone color, creates shifted dual-population Fresnel."""
    h, w = shape
    field = _cs_field_24k(shape, seed)
    dither = _cs_dither_24k(shape, seed)
    is_b = (dither >= (1.0 - field)).astype(np.float32)
    is_a = 1.0 - is_b
    # Read zone color from existing paint
    zone_mask = mask > 0.5
    if np.any(zone_mask):
        mean_r = float(paint[zone_mask, 0].mean())
        mean_g = float(paint[zone_mask, 1].mean())
        mean_b = float(paint[zone_mask, 2].mean())
    else:
        mean_r, mean_g, mean_b = 0.5, 0.5, 0.5
    # RGB to HSV
    cmax = max(mean_r, mean_g, mean_b)
    cmin = min(mean_r, mean_g, mean_b)
    delta = cmax - cmin
    if delta < 0.001:
        base_h = 0.0
    elif cmax == mean_r:
        base_h = ((60 * ((mean_g - mean_b) / delta)) % 360) / 360.0
    elif cmax == mean_g:
        base_h = (60 * ((mean_b - mean_r) / delta) + 120) / 360.0
    else:
        base_h = (60 * ((mean_r - mean_g) / delta) + 240) / 360.0
    base_s = 0.0 if cmax < 0.001 else delta / cmax
    base_v = cmax
    # Color A = zone color with boost
    h_a = np.full((h, w), base_h, dtype=np.float32)
    s_a = np.full((h, w), np.clip(base_s + 0.10, 0, 1), dtype=np.float32)
    v_a = np.full((h, w), np.clip(base_v + 0.05, 0, 1), dtype=np.float32)
    r_a, g_a, b_a = _hsv_to_rgb_24k(h_a, s_a, v_a)
    # Color B = shifted color
    shifted_h = (base_h + hue_shift / 360.0) % 1.0
    h_b = np.full((h, w), shifted_h, dtype=np.float32)
    s_b = np.full((h, w), np.clip(base_s + sat_delta, 0, 1), dtype=np.float32)
    v_b = np.full((h, w), np.clip(base_v + val_delta, 0, 1), dtype=np.float32)
    r_b, g_b, b_b = _hsv_to_rgb_24k(h_b, s_b, v_b)
    # Mix populations
    r_mix = is_a * r_a + is_b * r_b
    g_mix = is_a * g_a + is_b * g_b
    b_mix = is_a * b_a + is_b * b_b
    # Metallic brighten
    r_mix = np.clip(r_mix + 0.08, 0, 1)
    g_mix = np.clip(g_mix + 0.08, 0, 1)
    b_mix = np.clip(b_mix + 0.08, 0, 1)
    blend = 0.70 * pm
    mask3 = mask[:,:,np.newaxis]
    shift_rgb = np.stack([r_mix, g_mix, b_mix], axis=2)
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3
    paint = np.clip(paint + bb * 1.2 * mask3, 0, 1)
    return paint

def _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, hue_a, hue_b,
                         sat_a=0.85, sat_b=0.80, val_a=0.78, val_b=0.75):
    """Color Shift preset — fixed two-color dithered Fresnel. Mirrors main engine."""
    h, w = shape
    field = _cs_field_24k(shape, seed)
    dither = _cs_dither_24k(shape, seed)
    is_b = (dither >= (1.0 - field)).astype(np.float32)
    is_a = 1.0 - is_b
    h_a_arr = np.full((h, w), hue_a / 360.0, dtype=np.float32)
    s_a_arr = np.full((h, w), sat_a, dtype=np.float32)
    v_a_arr = np.full((h, w), val_a, dtype=np.float32)
    r_a, g_a, b_a = _hsv_to_rgb_24k(h_a_arr, s_a_arr, v_a_arr)
    h_b_arr = np.full((h, w), hue_b / 360.0, dtype=np.float32)
    s_b_arr = np.full((h, w), sat_b, dtype=np.float32)
    v_b_arr = np.full((h, w), val_b, dtype=np.float32)
    r_b, g_b, b_b = _hsv_to_rgb_24k(h_b_arr, s_b_arr, v_b_arr)
    r_mix = is_a * r_a + is_b * r_b
    g_mix = is_a * g_a + is_b * g_b
    b_mix = is_a * b_a + is_b * b_b
    r_mix = np.clip(r_mix + 0.08, 0, 1)
    g_mix = np.clip(g_mix + 0.08, 0, 1)
    b_mix = np.clip(b_mix + 0.08, 0, 1)
    blend = 0.75 * pm
    mask3 = mask[:,:,np.newaxis]
    shift_rgb = np.stack([r_mix, g_mix, b_mix], axis=2)
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3
    paint = np.clip(paint + bb * 1.2 * mask3, 0, 1)
    return paint


# --- PRIZM v4 CORE (Panel-Aware Color Ramp) ---

def _panel_field_24k(shape, seed, complexity=3):
    """Panel direction field — simulated 3D orientation from UV. Mirrors main engine."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    yn = yf / max(h - 1, 1)
    xn = xf / max(w - 1, 1)
    rng = np.random.RandomState(seed + 7000)
    angles = rng.uniform(0, 2 * np.pi, 5)
    field = (np.cos(angles[0]) * yn + np.sin(angles[0]) * xn) * 0.35
    if complexity >= 2:
        field = field + (np.cos(angles[1]) * yn + np.sin(angles[1]) * xn) * 0.25
    if complexity >= 3:
        cy = 0.45 + rng.uniform(-0.1, 0.1)
        cx = 0.50 + rng.uniform(-0.1, 0.1)
        dist = np.sqrt((yn - cy)**2 + (xn - cx)**2)
        field = field + dist * 0.20
        freq = 1.5 + rng.uniform(-0.3, 0.3)
        wave = np.sin((yn * np.cos(angles[2]) + xn * np.sin(angles[2])) * freq * np.pi) * 0.12
        field = field + wave
        noise = _multi_scale_noise(shape, [64, 128, 256], [0.25, 0.40, 0.35], seed + 7001)
        field = field + noise * 0.06
    fmin, fmax = field.min(), field.max()
    return (field - fmin) / (fmax - fmin + 1e-8)

def _color_ramp_24k(field, stops):
    """Map 0-1 field through multi-stop color ramp with smoothstep interpolation."""
    stops = sorted(stops, key=lambda s: s[0])
    n = len(stops)
    h, w = field.shape
    stop_rgbs = []
    for pos, hue, sat, val in stops:
        h_a = np.array([[hue / 360.0]], dtype=np.float32)
        s_a = np.array([[sat]], dtype=np.float32)
        v_a = np.array([[val]], dtype=np.float32)
        r, g, b = _hsv_to_rgb_24k(h_a, s_a, v_a)
        stop_rgbs.append((float(r[0, 0]), float(g[0, 0]), float(b[0, 0])))
    out_r = np.zeros((h, w), dtype=np.float32)
    out_g = np.zeros((h, w), dtype=np.float32)
    out_b = np.zeros((h, w), dtype=np.float32)
    for i in range(n - 1):
        p0, p1 = stops[i][0], stops[i + 1][0]
        r0, g0, b0 = stop_rgbs[i]
        r1, g1, b1 = stop_rgbs[i + 1]
        if i == 0:
            seg = field <= p1
        elif i == n - 2:
            seg = field > p0
        else:
            seg = (field > p0) & (field <= p1)
        if not np.any(seg):
            continue
        span = max(p1 - p0, 1e-8)
        t = np.clip((field[seg] - p0) / span, 0, 1)
        t = t * t * (3.0 - 2.0 * t)  # smoothstep
        out_r[seg] = r0 + (r1 - r0) * t
        out_g[seg] = g0 + (g1 - g0) * t
        out_b[seg] = b0 + (b1 - b0) * t
    return out_r, out_g, out_b

def _flake_24k(r, g, b, shape, seed, intensity=0.03):
    """Micro-flake noise for metallic paint depth."""
    h, w = shape
    rng = np.random.RandomState(seed + 7100)
    cell_size = 4
    ny, nx = max(1, h // cell_size), max(1, w // cell_size)
    cell_vals = rng.rand(ny + 1, nx + 1).astype(np.float32)
    yidx = np.clip(np.arange(h) // cell_size, 0, ny - 1).astype(int)
    xidx = np.clip(np.arange(w) // cell_size, 0, nx - 1).astype(int)
    flake = cell_vals[yidx[:, None], xidx[None, :]]
    fine = rng.rand(h, w).astype(np.float32)
    flake = flake * 0.6 + fine * 0.4
    flake = (flake - 0.5) * 2.0 * intensity
    return np.clip(r + flake, 0, 1), np.clip(g + flake, 0, 1), np.clip(b + flake, 0, 1)

def _spec_prizm_24k(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=18):
    """Prizm spec — uniform high-metallic with subtle variation."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 7200)
    M_arr = metallic + noise * 4 * sm
    R_arr = roughness + noise * 3 * sm
    spec[:,:,0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.where(mask > 0.5, clearcoat, 0).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3,
                     flake_intensity=0.03, blend_strength=0.92):
    """Full Prizm paint — panel-aware multi-color ramp. Mirrors main engine's paint_prizm_core."""
    field = _panel_field_24k(shape, seed, complexity)
    ramp_r, ramp_g, ramp_b = _color_ramp_24k(field, stops)
    ramp_r, ramp_g, ramp_b = _flake_24k(ramp_r, ramp_g, ramp_b, shape, seed, flake_intensity)
    ramp_r = np.clip(ramp_r + 0.10, 0, 1)
    ramp_g = np.clip(ramp_g + 0.10, 0, 1)
    ramp_b = np.clip(ramp_b + 0.10, 0, 1)
    b_str = blend_strength * pm
    mask3 = mask[:,:,np.newaxis]
    shift_rgb = np.stack([ramp_r, ramp_g, ramp_b], axis=2)
    paint = paint * (1.0 - b_str * mask3) + shift_rgb * b_str * mask3
    paint = np.clip(paint + bb * 1.0 * mask3, 0, 1)
    return paint


# ================================================================
# CONCRETE SPEC + PAINT FUNCTIONS FOR NEW SPECIALS
# ================================================================

# --- Group 1: Chameleon Classic (UPGRADED — full sine-wave HSV hue ramp) ---
def spec_chameleon_amethyst(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_amethyst(paint, shape, mask, seed, pm, bb):
    """Amethyst — Purple to Blue to Teal (120 degree sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 280, 120)
def spec_chameleon_emerald(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_emerald(paint, shape, mask, seed, pm, bb):
    """Emerald — Green to Teal to Blue (100 degree sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 140, 100)
def spec_chameleon_obsidian(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_obsidian(paint, shape, mask, seed, pm, bb):
    """Obsidian — Deep Purple to Blue to Green (180 degree dark sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 250, 180)

# --- Group 2: Color Shift Adaptive (UPGRADED — dithered Fresnel dual-population) ---
def spec_cs_complementary(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm)
def paint_cs_complementary(paint, shape, mask, seed, pm, bb):
    """Complementary — shifts zone color 180 degrees (opposite)"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 180)
def spec_cs_triadic(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm)
def paint_cs_triadic(paint, shape, mask, seed, pm, bb):
    """Triadic — shifts zone color 120 degrees"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 120)
def spec_cs_split(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm)
def paint_cs_split(paint, shape, mask, seed, pm, bb):
    """Split-Complementary — shifts zone color 150 degrees"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 150)

# --- Group 3: Color Shift Preset (UPGRADED — fixed two-color dithered Fresnel) ---
def spec_cs_neon_dreams(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 240, 'R': 6, 'CC': 16}, {'M': 210, 'R': 22, 'CC': 20})
def paint_cs_neon_dreams(paint, shape, mask, seed, pm, bb):
    """Neon Dreams — Hot Pink to Electric Blue"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 320, 210, 0.90, 0.88, 0.82, 0.80)
def spec_cs_twilight(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 230, 'R': 10, 'CC': 18}, {'M': 195, 'R': 30, 'CC': 22})
def paint_cs_twilight(paint, shape, mask, seed, pm, bb):
    """Twilight — Warm Amber to Deep Violet"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 35, 275, 0.82, 0.80, 0.78, 0.72)
def spec_cs_toxic(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 225, 'R': 12, 'CC': 14}, {'M': 190, 'R': 32, 'CC': 20})
def paint_cs_toxic(paint, shape, mask, seed, pm, bb):
    """Toxic — Acid Green to Toxic Purple"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 90, 285, 0.92, 0.85, 0.80, 0.70)

# --- Group 4: Prizm Series (UPGRADED — panel-aware multi-color ramp) ---
def spec_prizm_neon(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=232, roughness=10, clearcoat=18)
def paint_prizm_neon(paint, shape, mask, seed, pm, bb):
    """Neon — Vivid neon sweep: Magenta to Cyan to Lime"""
    stops = [
        (0.00, 310, 0.92, 0.85),
        (0.30, 350, 0.88, 0.82),
        (0.55, 175, 0.90, 0.84),
        (0.80, 130, 0.88, 0.82),
        (1.00, 75,  0.85, 0.86),
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.025)
def spec_prizm_blood_moon(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=228, roughness=16, clearcoat=14)
def paint_prizm_blood_moon(paint, shape, mask, seed, pm, bb):
    """Blood Moon — Deep crimson to black to dark copper"""
    stops = [
        (0.00, 355, 0.90, 0.65),
        (0.30, 10,  0.85, 0.55),
        (0.55, 0,   0.70, 0.30),
        (0.80, 20,  0.80, 0.50),
        (1.00, 35,  0.75, 0.60),
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.035)

# --- Group 5: Effect & Visual (new entries) ---
spec_x_ray = make_effect_spec_fn(30, 180, 0, effect_type="gradient")
spec_infrared = make_effect_spec_fn(40, 100, 0, effect_type="noise")
spec_uv_blacklight = make_effect_spec_fn(50, 60, 16, effect_type="noise")
spec_double_exposure = make_effect_spec_fn(80, 50, 16, effect_type="gradient")
spec_depth_map = make_effect_spec_fn(60, 120, 0, effect_type="radial")
spec_polarized = make_effect_spec_fn(100, 40, 16, effect_type="bands")
paint_x_ray = make_weather_paint_fn(darken=0.12, desat=0.20, noise_str=0.04)
paint_infrared = make_colorshift_paint_fn([(0.6, 0.0, -0.3), (0.8, 0.4, 0.0), (0.0, 0.0, 0.5)])
paint_uv_blacklight = make_glow_fn([0.4, 0.0, 0.8], glow_strength=0.08)
paint_double_exposure = make_weather_paint_fn(desat=0.08, noise_str=0.05)
paint_depth_map = make_weather_paint_fn(desat=0.15, darken=0.06)
paint_polarized = make_colorshift_paint_fn([(0.3, 0.0, 0.4), (0.0, 0.4, 0.2), (0.4, 0.3, 0.0)])

# --- Group 6: Racing Legend (all new) ---
spec_victory_burnout = make_flat_spec_fn(180, 30, 16, noise_M=30, noise_R=20, noise_scales=[4, 8, 16])
spec_photo_finish = make_effect_spec_fn(120, 25, 16, effect_type="gradient")
spec_heat_haze = make_effect_spec_fn(60, 80, 0, effect_type="noise")
spec_race_worn = make_flat_spec_fn(80, 120, 8, noise_M=30, noise_R=40, noise_scales=[4, 8, 16])
spec_pace_lap = make_flat_spec_fn(30, 50, 16, noise_R=15, noise_scales=[16, 32])
spec_green_flag = make_flat_spec_fn(40, 30, 16, noise_M=20, noise_scales=[8, 16])
spec_black_flag = make_flat_spec_fn(20, 180, 0, noise_R=20, noise_scales=[8, 16])
spec_white_flag = make_flat_spec_fn(50, 15, 16, noise_M=15, noise_scales=[8, 16])
spec_under_lights = make_effect_spec_fn(80, 40, 16, effect_type="gradient")
spec_dawn_patrol = make_effect_spec_fn(60, 30, 16, effect_type="gradient")
spec_rain_race = make_flat_spec_fn(40, 60, 16, noise_R=25, noise_scales=[4, 8, 16])
spec_tunnel_run = make_effect_spec_fn(100, 35, 16, effect_type="gradient")
spec_drafting = make_effect_spec_fn(120, 25, 16, effect_type="bands")
spec_pole_position = make_flat_spec_fn(220, 10, 16, noise_M=20, noise_scales=[16, 32])
spec_last_lap = make_flat_spec_fn(150, 20, 16, noise_M=25, noise_R=15, noise_scales=[4, 8])

paint_victory_burnout = make_weather_paint_fn(noise_str=0.06, tint_rgb=[0.2, 0.15, 0.0])
paint_photo_finish = make_weather_paint_fn(noise_str=0.04)
paint_heat_haze = make_weather_paint_fn(noise_str=0.05, desat=0.06)
paint_race_worn = make_aged_fn(fade_strength=0.10, roughen=0.06)
paint_pace_lap = make_glow_fn([0.6, 0.5, 0.0], glow_strength=0.05)
paint_green_flag = make_glow_fn([0.0, 0.6, 0.1], glow_strength=0.06)
paint_black_flag = make_weather_paint_fn(darken=0.15, desat=0.10)
paint_white_flag = make_glow_fn([0.8, 0.8, 0.8], glow_strength=0.06)
paint_under_lights = make_weather_paint_fn(tint_rgb=[0.2, 0.2, 0.3], noise_str=0.03)
paint_dawn_patrol = make_glow_fn([0.5, 0.35, 0.1], glow_strength=0.05)
paint_rain_race = make_weather_paint_fn(tint_rgb=[0.0, 0.1, 0.2], noise_str=0.05)
paint_tunnel_run = make_weather_paint_fn(darken=0.08, noise_str=0.04)
paint_drafting = make_weather_paint_fn(noise_str=0.04)
paint_pole_position = make_luxury_sparkle_fn(sparkle_density=0.95, sparkle_strength=0.08)
paint_last_lap = make_vivid_depth_fn(sat_boost=0.15, depth_darken=0.04)

# --- Group 7: Weather & Element (new entries) ---
spec_tornado_alley = make_effect_spec_fn(50, 150, 0, effect_type="radial")
spec_volcanic_glass = make_flat_spec_fn(40, 6, 16, noise_M=20, noise_scales=[4, 8, 16])
spec_frozen_lake = make_flat_spec_fn(30, 10, 16, noise_R=15, noise_scales=[8, 16, 32])
spec_desert_mirage = make_effect_spec_fn(20, 100, 0, effect_type="noise")
spec_ocean_floor = make_flat_spec_fn(40, 80, 0, noise_M=15, noise_R=20, noise_scales=[8, 16, 32])
spec_meteor_shower = make_effect_spec_fn(180, 15, 0, effect_type="noise")
paint_tornado_alley = make_weather_paint_fn(darken=0.10, desat=0.12, noise_str=0.06)
paint_volcanic_glass = make_vivid_depth_fn(sat_boost=0.08, depth_darken=0.10)
paint_frozen_lake = make_glow_fn([0.1, 0.3, 0.5], glow_strength=0.05)
paint_desert_mirage = make_weather_paint_fn(desat=0.08, tint_rgb=[0.3, 0.2, 0.0], noise_str=0.05)
paint_ocean_floor = make_glow_fn([0.0, 0.2, 0.4], glow_strength=0.06)
paint_meteor_shower = make_luxury_sparkle_fn(sparkle_density=0.93, sparkle_strength=0.10)

# --- Group 8: Dark & Gothic (new entries) ---
spec_voodoo = make_flat_spec_fn(40, 140, 0, noise_M=15, noise_R=20, noise_scales=[4, 8, 16])
spec_reaper = make_effect_spec_fn(30, 200, 0, effect_type="gradient")
spec_possessed = make_flat_spec_fn(50, 100, 0, noise_M=25, noise_scales=[4, 8])
spec_wraith = make_effect_spec_fn(20, 160, 0, effect_type="noise")
spec_cursed = make_flat_spec_fn(35, 170, 0, noise_M=20, noise_R=25, noise_scales=[4, 8, 16])
spec_eclipse = make_effect_spec_fn(10, 220, 0, effect_type="radial")
spec_nightmare = make_effect_spec_fn(40, 180, 0, effect_type="noise")
paint_voodoo = make_glow_fn([0.2, 0.5, 0.1], glow_strength=0.06)
paint_reaper = make_weather_paint_fn(darken=0.18, desat=0.15)
paint_possessed = make_glow_fn([0.6, 0.0, 0.0], glow_strength=0.07)
paint_wraith = make_weather_paint_fn(darken=0.12, desat=0.20, noise_str=0.04)
paint_cursed = make_glow_fn([0.1, 0.4, 0.0], glow_strength=0.05)
paint_eclipse = make_weather_paint_fn(darken=0.20, tint_rgb=[0.3, 0.2, 0.0])
paint_nightmare = make_weather_paint_fn(darken=0.15, desat=0.10, noise_str=0.06)

# --- Group 9: Luxury & Exotic (new entries — galaxy exists) ---
spec_black_diamond = make_flat_spec_fn(200, 8, 16, noise_M=30, noise_scales=[2, 4, 8])
spec_liquid_gold = make_flat_spec_fn(245, 5, 16, noise_M=15, noise_scales=[4, 8, 16])
spec_silk_road = make_flat_spec_fn(120, 30, 16, noise_M=20, noise_R=15, noise_scales=[8, 16, 32])
spec_venetian_glass = make_chameleon_spec_fn(80, 20, 16, color_shift_range=40)
spec_mother_of_pearl = make_chameleon_spec_fn(100, 25, 16, color_shift_range=35)
spec_sapphire = make_flat_spec_fn(130, 8, 16, noise_M=20, noise_scales=[16, 32])
spec_ruby = make_flat_spec_fn(120, 10, 16, noise_M=20, noise_scales=[16, 32])
spec_alexandrite = make_chameleon_spec_fn(140, 15, 16, color_shift_range=60)
spec_stained_glass = make_prizm_spec_fn(60, 15, 16, num_bands=12)
spec_champagne_toast = make_flat_spec_fn(180, 12, 16, noise_M=25, noise_scales=[2, 4, 8])
spec_velvet_crush = make_flat_spec_fn(30, 130, 0, noise_R=20, noise_scales=[4, 8, 16])
paint_black_diamond = make_luxury_sparkle_fn(sparkle_density=0.96, sparkle_strength=0.06)
paint_liquid_gold = make_chrome_tint_fn(0.95, 0.85, 0.40, blend=0.20)
paint_silk_road = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)
paint_venetian_glass = make_colorshift_paint_fn([(0.4, 0.1, 0.0), (0.0, 0.3, 0.4), (0.3, 0.0, 0.3)])
paint_mother_of_pearl = make_colorshift_paint_fn([(0.3, 0.2, 0.1), (0.1, 0.3, 0.2), (0.2, 0.1, 0.3)])
paint_sapphire = make_vivid_depth_fn(sat_boost=0.15, depth_darken=0.08)
paint_ruby = make_vivid_depth_fn(sat_boost=0.18, depth_darken=0.06)
paint_alexandrite = make_colorshift_paint_fn([(0.0, 0.4, 0.2), (0.4, 0.0, 0.1), (0.2, 0.2, 0.0)])
paint_stained_glass = make_colorshift_paint_fn([(0.5, 0.0, 0.0), (0.0, 0.5, 0.0), (0.0, 0.0, 0.5), (0.4, 0.4, 0.0)])
paint_champagne_toast = make_glow_fn([0.5, 0.4, 0.1], glow_strength=0.06)
paint_velvet_crush = make_weather_paint_fn(darken=0.06, desat=0.05, noise_str=0.04)

# --- Group 10: Neon & Glow (new entries — neon_glow, radioactive, static, scorched exist) ---
spec_neon_vegas = make_flat_spec_fn(60, 40, 16, noise_M=20, noise_scales=[4, 8, 16])
spec_laser_grid = make_flat_spec_fn(80, 20, 16, noise_M=15, noise_scales=[8, 16])
spec_plasma_globe = make_effect_spec_fn(100, 30, 16, effect_type="radial")
spec_firefly = make_flat_spec_fn(40, 60, 0, noise_M=15, noise_scales=[2, 4])
spec_led_matrix = make_flat_spec_fn(70, 25, 16, noise_M=20, noise_scales=[2, 4, 8])
spec_cyberpunk = make_flat_spec_fn(90, 30, 16, noise_M=25, noise_R=15, noise_scales=[4, 8, 16])
paint_neon_vegas = make_colorshift_paint_fn([(0.8, 0.0, 0.3), (0.0, 0.8, 0.0), (0.8, 0.8, 0.0), (0.0, 0.3, 0.8)])
paint_laser_grid = make_glow_fn([0.0, 0.8, 0.0], glow_strength=0.08)
paint_plasma_globe = make_glow_fn([0.5, 0.1, 0.8], glow_strength=0.07)
paint_firefly = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.08)
paint_led_matrix = make_glow_fn([0.3, 0.6, 0.3], glow_strength=0.06)
paint_cyberpunk = make_colorshift_paint_fn([(0.7, 0.0, 0.5), (0.0, 0.3, 0.8)])

# --- Group 11: Texture & Surface (all new) ---
spec_croc_leather = make_flat_spec_fn(40, 60, 16, noise_R=20, noise_scales=[4, 8, 16])
spec_hammered_copper = make_flat_spec_fn(190, 55, 0, noise_M=25, noise_R=20, noise_scales=[4, 8])
spec_dark_brushed_steel = make_flat_spec_fn(220, 70, 0, noise_R=25, noise_scales=[4, 8, 16])
spec_etched_metal = make_flat_spec_fn(180, 50, 0, noise_M=20, noise_R=15, noise_scales=[4, 8, 16])
spec_sandstone = make_flat_spec_fn(20, 180, 0, noise_R=25, noise_scales=[4, 8])
spec_petrified_wood = make_flat_spec_fn(30, 120, 0, noise_R=20, noise_scales=[8, 16, 32])
spec_forged_iron = make_flat_spec_fn(200, 90, 0, noise_M=30, noise_R=25, noise_scales=[4, 8])
spec_acid_etched_glass = make_flat_spec_fn(15, 100, 16, noise_R=20, noise_scales=[4, 8, 16])
spec_concrete = make_flat_spec_fn(10, 190, 0, noise_R=20, noise_scales=[2, 4, 8])
spec_cast_iron = make_flat_spec_fn(180, 110, 0, noise_M=30, noise_R=30, noise_scales=[4, 8])
paint_croc_leather = make_emboss_paint_fn(strength=0.10)
paint_hammered_copper = make_metallic_tint_fn(r_shift=0.3, g_shift=0.1, b_shift=-0.2, flake_str=0.04)
paint_dark_brushed_steel = make_weather_paint_fn(darken=0.06, noise_str=0.04)
paint_etched_metal = make_emboss_paint_fn(strength=0.08)
paint_sandstone = make_weather_paint_fn(tint_rgb=[0.2, 0.15, 0.05], noise_str=0.05)
paint_petrified_wood = make_weather_paint_fn(desat=0.10, tint_rgb=[0.1, 0.08, 0.02], noise_str=0.04)
paint_forged_iron = make_weather_paint_fn(darken=0.08, noise_str=0.05)
paint_acid_etched_glass = make_weather_paint_fn(desat=0.15, noise_str=0.03)
paint_concrete = make_weather_paint_fn(desat=0.12, noise_str=0.06)
paint_cast_iron = make_weather_paint_fn(darken=0.06, noise_str=0.05)

# --- Group 12: Vintage & Retro (all new) ---
spec_barn_find = make_flat_spec_fn(50, 180, 0, noise_M=30, noise_R=35, noise_scales=[4, 8, 16])
spec_patina_truck = make_flat_spec_fn(60, 150, 0, noise_M=25, noise_R=30, noise_scales=[4, 8, 16])
spec_hot_rod_flames = make_flat_spec_fn(200, 12, 16, noise_M=20, noise_scales=[8, 16, 32])
spec_woodie_wagon = make_flat_spec_fn(20, 100, 8, noise_R=20, noise_scales=[8, 16, 32])
spec_drive_in = make_flat_spec_fn(100, 30, 16, noise_M=20, noise_scales=[4, 8, 16])
spec_muscle_car_stripe = make_flat_spec_fn(150, 15, 16, noise_M=15, noise_scales=[16, 32])
spec_pin_up = make_flat_spec_fn(10, 160, 0, noise_R=20, noise_scales=[4, 8])
spec_vinyl_record = make_flat_spec_fn(30, 80, 0, noise_R=15, noise_scales=[4, 8])
paint_barn_find = make_aged_fn(fade_strength=0.25, roughen=0.10)
paint_patina_truck = make_aged_fn(fade_strength=0.18, roughen=0.08)
paint_hot_rod_flames = make_vivid_depth_fn(sat_boost=0.18, depth_darken=0.04)
paint_woodie_wagon = make_weather_paint_fn(tint_rgb=[0.2, 0.12, 0.03], noise_str=0.04)
paint_drive_in = make_glow_fn([0.5, 0.3, 0.4], glow_strength=0.06)
paint_muscle_car_stripe = make_vivid_depth_fn(sat_boost=0.12, depth_darken=0.03)
paint_pin_up = make_aged_fn(fade_strength=0.10, roughen=0.06)
paint_vinyl_record = make_weather_paint_fn(darken=0.06, noise_str=0.03)

# --- Group 13: Surreal & Fantasy (all new) ---
spec_portal = make_effect_spec_fn(120, 20, 16, effect_type="radial")
spec_time_warp = make_effect_spec_fn(80, 40, 16, effect_type="radial")
spec_antimatter = make_flat_spec_fn(200, 10, 0, noise_M=30, noise_scales=[4, 8])
spec_singularity = make_effect_spec_fn(10, 240, 0, effect_type="radial")
spec_dreamscape = make_effect_spec_fn(60, 50, 16, effect_type="noise")
spec_acid_trip = make_chameleon_spec_fn(120, 20, 16, color_shift_range=80)
spec_mirage = make_effect_spec_fn(30, 100, 0, effect_type="noise")
spec_fourth_dimension = make_flat_spec_fn(180, 15, 16, noise_M=25, noise_scales=[8, 16, 32])
spec_glitch_reality = make_flat_spec_fn(100, 60, 0, noise_M=40, noise_R=30, noise_scales=[2, 4, 8])
spec_phantom_zone = make_flat_spec_fn(160, 30, 0, noise_M=20, noise_scales=[8, 16, 32])
paint_portal = make_colorshift_paint_fn([(0.3, 0.0, 0.6), (0.0, 0.4, 0.5), (0.5, 0.2, 0.3)])
paint_time_warp = make_colorshift_paint_fn([(0.3, 0.3, 0.0), (0.0, 0.3, 0.3), (0.3, 0.0, 0.3)])
paint_antimatter = make_weather_paint_fn(darken=0.05, noise_str=0.06)
paint_singularity = make_weather_paint_fn(darken=0.25, desat=0.20)
paint_dreamscape = make_weather_paint_fn(desat=0.06, noise_str=0.05, tint_rgb=[0.1, 0.1, 0.2])
paint_acid_trip = make_colorshift_paint_fn([(0.6, 0.0, 0.3), (0.0, 0.6, 0.2), (0.3, 0.2, 0.6), (0.6, 0.5, 0.0)])
paint_mirage = make_weather_paint_fn(desat=0.08, noise_str=0.06)
paint_fourth_dimension = make_luxury_sparkle_fn(sparkle_density=0.95, sparkle_strength=0.07)
paint_glitch_reality = make_weather_paint_fn(noise_str=0.08)
paint_phantom_zone = make_weather_paint_fn(darken=0.10, desat=0.12, tint_rgb=[0.1, 0.1, 0.3])

# --- Group 14: SHOKK SERIES (all new) ---
spec_shokk_ekg = make_effect_spec_fn(180, 20, 16, effect_type="bands")
spec_shokk_defib = make_effect_spec_fn(200, 15, 16, effect_type="radial")
spec_shokk_overload = make_flat_spec_fn(160, 40, 0, noise_M=40, noise_R=30, noise_scales=[2, 4, 8])
spec_shokk_blackout = make_flat_spec_fn(10, 240, 0, noise_R=10, noise_scales=[4, 8])
spec_shokk_resurrection = make_effect_spec_fn(120, 80, 0, effect_type="gradient")
spec_shokk_voltage = make_flat_spec_fn(220, 10, 0, noise_M=30, noise_scales=[2, 4, 8])
spec_shokk_flatline = make_effect_spec_fn(30, 200, 0, effect_type="bands")
spec_shokk_adrenaline = make_flat_spec_fn(190, 15, 16, noise_M=25, noise_scales=[4, 8])
spec_shokk_aftermath = make_flat_spec_fn(80, 140, 0, noise_M=30, noise_R=35, noise_scales=[4, 8, 16])
spec_shokk_unleashed = make_flat_spec_fn(220, 10, 16, noise_M=40, noise_R=20, noise_scales=[2, 4, 8, 16])

def paint_shokk_ekg(paint, shape, mask, seed, pm, bb):
    """SHOKK EKG — dramatic heartbeat monitor pulse. THE signature finish.
    Real EKG waveform: P-wave, QRS complex, T-wave repeating across surface."""
    h, w = shape
    y, x = _get_mgrid(shape)
    center_y = h * 0.5

    # --- Build a real EKG waveform per horizontal pixel ---
    # Period sized for ~3 full heartbeats across a 2048-wide texture
    period = max(60, w // 5)
    phase = (x % period).astype(np.float32) / period  # 0..1 per cycle

    # P-wave (small bump)
    p_wave = np.exp(-((phase - 0.10) ** 2) / (2 * 0.008)) * 0.15
    # QRS complex (sharp spike up then down)
    q_dip = -np.exp(-((phase - 0.28) ** 2) / (2 * 0.002)) * 0.20
    r_peak = np.exp(-((phase - 0.32) ** 2) / (2 * 0.0012)) * 1.0
    s_dip = -np.exp(-((phase - 0.36) ** 2) / (2 * 0.002)) * 0.25
    # T-wave (broad recovery bump)
    t_wave = np.exp(-((phase - 0.52) ** 2) / (2 * 0.012)) * 0.25

    ekg_waveform = p_wave + q_dip + r_peak + s_dip + t_wave

    # Amplitude: 35% of image height so the R-peak is clearly visible
    amplitude = h * 0.35
    ekg_y = center_y - ekg_waveform * amplitude  # negative = up in image coords

    # Distance from each pixel to the EKG line
    dist = np.abs(y - ekg_y)

    # Glow falloff: bright core (3px) with wider glow (30px)
    glow_width = max(8, h * 0.035)
    core_width = max(2, h * 0.006)
    core = np.clip(1.0 - dist / core_width, 0, 1)
    glow = np.clip(1.0 - dist / glow_width, 0, 1) ** 2

    # Shokker signature green (#00E639) glow with intensity — BOOSTED for visibility
    glow_strength = 0.55 * pm
    core_strength = 0.75 * pm

    # Green channel: strong glow
    paint[:,:,1] = np.clip(paint[:,:,1] + (core * core_strength + glow * glow_strength) * mask, 0, 1)
    # Red channel: slight suppress for contrast, but add warm hint at peaks
    paint[:,:,0] = np.clip(paint[:,:,0] - glow * 0.12 * pm * mask + core * 0.08 * pm * mask, 0, 1)
    # Blue channel: subtle cyan tint in glow
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.10 * pm * mask, 0, 1)

    # Darken areas away from the EKG line for drama — BOOSTED
    far_from_line = np.clip(dist / (h * 0.4), 0, 1)
    darken = far_from_line * 0.22 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    # Faint horizontal baseline (flatline between beats)
    baseline_dist = np.abs(y - center_y)
    baseline = np.clip(1.0 - baseline_dist / max(1, h * 0.003), 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + baseline * 0.04 * pm * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_defib(paint, shape, mask, seed, pm, bb):
    """SHOKK Defib — electric shock paddles burst with radiating arcs."""
    h, w = shape
    y, x = _get_mgrid(shape)
    from scipy.ndimage import gaussian_filter

    # Two paddle impact points
    cy = h * 0.45
    cx_left, cx_right = w * 0.35, w * 0.65

    # Radial burst from each paddle
    dist_l = np.sqrt((y - cy)**2 + (x - cx_left)**2) / max(h, w)
    dist_r = np.sqrt((y - cy)**2 + (x - cx_right)**2) / max(h, w)
    burst_l = np.clip(1.0 - dist_l * 4, 0, 1) ** 1.5
    burst_r = np.clip(1.0 - dist_r * 4, 0, 1) ** 1.5
    burst = np.clip(burst_l + burst_r, 0, 1)

    # Electric arcs between paddles
    arc_zone = (x > cx_left) & (x < cx_right)
    arc_y_center = cy + np.sin((x - cx_left) / (cx_right - cx_left) * np.pi * 4) * h * 0.08
    arc_dist = np.abs(y - arc_y_center)
    arc_core = np.clip(1.0 - arc_dist / max(2, h * 0.005), 0, 1)
    arc_glow = np.clip(1.0 - arc_dist / max(8, h * 0.02), 0, 1) ** 2
    arc = (arc_core * 0.8 + arc_glow * 0.4) * arc_zone.astype(np.float32)

    combined = np.clip(burst + arc, 0, 1)

    # Electric blue-white flash
    paint[:,:,0] = np.clip(paint[:,:,0] + combined * 0.30 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + combined * 0.35 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + combined * 0.45 * pm * mask, 0, 1)

    # Slight darken away from burst for contrast
    far = np.clip(1.0 - combined * 2, 0, 1)
    paint = np.clip(paint - far[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_overload(paint, shape, mask, seed, pm, bb):
    """SHOKK Overload — electrical system overload, glitching hot spots everywhere."""
    h, w = shape
    from scipy.ndimage import gaussian_filter
    # Base warm tint (overheating electronics)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.06 * pm * mask, 0, 1)
    # Overload glitch blocks: random rectangular hot zones
    rng = np.random.RandomState(seed + 1700)
    block_layer = np.zeros(shape, dtype=np.float32)
    n_blocks = max(15, (h * w) // (150 * 150))
    for _ in range(n_blocks):
        by, bx = rng.randint(0, h), rng.randint(0, w)
        bh = rng.randint(max(3, h // 80), max(6, h // 25))
        bw = rng.randint(max(3, w // 80), max(6, w // 25))
        y1, y2 = max(0, by), min(h, by + bh)
        x1, x2 = max(0, bx), min(w, bx + bw)
        block_layer[y1:y2, x1:x2] = 0.5 + rng.random() * 0.5
    block_glow = gaussian_filter(block_layer, sigma=max(1, h * 0.004))
    # Hot orange-yellow overload glow
    paint[:,:,0] = np.clip(paint[:,:,0] + block_glow * 0.30 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + block_glow * 0.18 * pm * mask, 0, 1)
    # Scan line interference
    y_arr = _get_mgrid(shape)[0]
    scan = (y_arr.astype(np.int32) % max(4, h // 120) < 2).astype(np.float32)
    paint = np.clip(paint - scan[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_blackout(paint, shape, mask, seed, pm, bb):
    """SHOKK Blackout — total power failure, near-black with faint emergency red."""
    h, w = shape
    # Heavy blackout
    paint = np.clip(paint * (1 - 0.35 * pm * mask[:,:,np.newaxis]), 0, 1)
    # Faint emergency red pulse strips
    y_grid = _get_mgrid(shape)[0]
    # Horizontal emergency strips
    strip_period = max(30, h // 8)
    strip_phase = (y_grid % strip_period).astype(np.float32) / strip_period
    strip = np.clip(1.0 - np.abs(strip_phase - 0.5) * 8, 0, 1)
    # Flicker via noise
    flicker = _multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 1750)
    flicker = np.clip(flicker * 0.5 + 0.5, 0, 1)
    emergency = strip * flicker * 0.15 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + emergency * mask, 0, 1)
    paint = np.clip(paint + bb * 0.15 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_resurrection(paint, shape, mask, seed, pm, bb):
    """SHOKK Resurrection — dark surface shattering with blinding light breaking through cracks."""
    h, w = shape
    from scipy.ndimage import gaussian_filter

    # Very dark base — the tomb
    paint = np.clip(paint - 0.22 * pm * mask[:,:,np.newaxis], 0, 1)

    # Crack network: sharp noise threshold creates fracture lines
    crack = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 500)
    # Sharp fracture lines where noise crosses threshold
    crack_lines = np.clip((crack - 0.46) * 15, 0, 1)
    crack_glow = gaussian_filter(crack_lines, sigma=max(2, h * 0.006))

    # Light breaking through: warm white-gold
    paint[:,:,0] = np.clip(paint[:,:,0] + crack_lines * 0.40 * pm * mask + crack_glow * 0.15 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + crack_lines * 0.35 * pm * mask + crack_glow * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + crack_lines * 0.20 * pm * mask + crack_glow * 0.06 * pm * mask, 0, 1)

    # Central light source burst (resurrection point)
    y, x = _get_mgrid(shape)
    cy, cx = h * 0.4, w * 0.5
    dist = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    light_burst = np.clip(1.0 - dist * 3.5, 0, 1) ** 2
    paint[:,:,0] = np.clip(paint[:,:,0] + light_burst * 0.25 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + light_burst * 0.22 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + light_burst * 0.15 * pm * mask, 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_voltage(paint, shape, mask, seed, pm, bb):
    """SHOKK Voltage — high-voltage arcs crawling across surface like Lichtenberg figures."""
    h, w = shape
    from scipy.ndimage import gaussian_filter
    # Multiple branching lightning paths (Lichtenberg pattern via noise thresholding)
    noise1 = _multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed + 1650)
    noise2 = _multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed + 1660)
    # Sharp threshold creates branching paths
    branch1 = np.clip((noise1 - 0.48) * 20, 0, 1)
    branch2 = np.clip((noise2 - 0.49) * 20, 0, 1)
    branches = np.clip(branch1 + branch2 * 0.7, 0, 1)
    # Glow around branches
    branch_glow = gaussian_filter(branches, sigma=max(2, h * 0.008))
    # Electric blue arcs with white core
    paint[:,:,0] = np.clip(paint[:,:,0] + branches * 0.25 * pm * mask + branch_glow * 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + branches * 0.30 * pm * mask + branch_glow * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + branches * 0.40 * pm * mask + branch_glow * 0.20 * pm * mask, 0, 1)
    # Darken non-arc areas for contrast
    dark = np.clip(1.0 - branch_glow * 3, 0, 1)
    paint = np.clip(paint - dark[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_flatline(paint, shape, mask, seed, pm, bb):
    """SHOKK Flatline — dark dead zone with one dramatic green pulse spike.
    Mostly black with a thin flatline and one R-peak burst."""
    h, w = shape
    y, x = _get_mgrid(shape)

    # Heavy darken for dead zone feel — BOOSTED
    paint = np.clip(paint - 0.30 * pm * mask[:,:,np.newaxis], 0, 1)

    center_y = h * 0.5
    # Faint flatline across entire width — BOOSTED
    line_dist = np.abs(y - center_y)
    flatline_glow = max(2, h * 0.004)
    flatline = np.clip(1.0 - line_dist / flatline_glow, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + flatline * 0.12 * pm * mask, 0, 1)

    # One dramatic R-peak spike near center
    spike_x = w * 0.5
    spike_zone = np.exp(-((x - spike_x)**2) / (2 * (w * 0.020)**2))
    spike_amp = h * 0.35
    spike_y = center_y - spike_zone * spike_amp
    spike_dist = np.abs(y - spike_y)
    spike_width = max(3, h * 0.008)
    spike_glow_w = max(10, h * 0.03)
    spike_core = np.clip(1.0 - spike_dist / spike_width, 0, 1)
    spike_glow = np.clip(1.0 - spike_dist / spike_glow_w, 0, 1) ** 2

    # Bright green spike — BOOSTED
    paint[:,:,1] = np.clip(paint[:,:,1] + (spike_core * 0.70 + spike_glow * 0.45) * pm * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] - spike_glow * 0.08 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + spike_glow * 0.06 * pm * mask, 0, 1)

    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_adrenaline(paint, shape, mask, seed, pm, bb):
    """SHOKK Adrenaline — racing heartbeat red pulse radiating from center outward."""
    h, w = shape
    y, x = _get_mgrid(shape)
    from scipy.ndimage import gaussian_filter
    cy, cx = h * 0.5, w * 0.5
    dist = np.sqrt((y - cy)**2 + (x - cx)**2)
    max_dist = np.sqrt(cy**2 + cx**2)
    # Pulsing concentric rings
    ring_freq = max(15, min(h, w) * 0.04)
    rings = np.sin(dist / ring_freq * np.pi * 2) * 0.5 + 0.5
    rings = rings ** 2  # sharpen
    # Fade rings toward edges
    fade = np.clip(1.0 - dist / (max_dist * 0.8), 0, 1)
    pulse = rings * fade
    # Hot red adrenaline glow
    paint[:,:,0] = np.clip(paint[:,:,0] + pulse * 0.35 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - pulse * 0.04 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - pulse * 0.04 * pm * mask, 0, 1)
    # Center hotspot
    center_glow = np.clip(1.0 - dist / (max_dist * 0.2), 0, 1) ** 2
    paint[:,:,0] = np.clip(paint[:,:,0] + center_glow * 0.20 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + center_glow * 0.05 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_aftermath(paint, shape, mask, seed, pm, bb):
    """SHOKK Aftermath — post-explosion scorched and charred with ember glow cracks."""
    h, w = shape
    from scipy.ndimage import gaussian_filter
    # Heavy char/scorch darkening — BOOSTED
    paint = np.clip(paint - 0.28 * pm * mask[:,:,np.newaxis], 0, 1)
    # Desaturate — stronger
    gray = paint.mean(axis=2, keepdims=True)
    paint = np.clip(paint + (gray - paint) * 0.55 * pm * mask[:,:,np.newaxis], 0, 1)
    # Ember glow cracks — lower threshold for more crack visibility
    crack = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 2500)
    ember_lines = np.where(crack > 0.68, (crack - 0.68) / 0.32, 0).astype(np.float32)
    ember_glow = gaussian_filter(ember_lines, sigma=max(1, h * 0.006))
    # Orange-red ember glow — BOOSTED significantly
    paint[:,:,0] = np.clip(paint[:,:,0] + ember_glow * 0.50 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + ember_glow * 0.22 * pm * mask, 0, 1)
    # Ash texture
    ash = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 2550)
    paint = np.clip(paint + (ash * 0.08 - 0.04)[:,:,np.newaxis] * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shokk_unleashed(paint, shape, mask, seed, pm, bb):
    """SHOKK Unleashed — maximum chaotic energy explosion.
    Lightning bolts, energy arcs, color-shifted chaos zones, bright plasma bursts."""
    h, w = shape
    y, x = _get_mgrid(shape)
    from scipy.ndimage import gaussian_filter

    # --- Chaotic multi-color energy zones ---
    noise_r = _multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed + 1800)
    noise_g = _multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed + 1837)
    noise_b = _multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed + 1874)
    # Boost intensity: these are actual visible color shifts — BOOSTED for chaos
    paint[:,:,0] = np.clip(paint[:,:,0] + noise_r * 0.32 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + noise_g * 0.32 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + noise_b * 0.32 * pm * mask, 0, 1)

    # --- Lightning/energy arcs ---
    # Multiple jagged arcs across the surface
    rng = np.random.RandomState(seed + 1900)
    n_arcs = max(5, min(12, w // 200))
    arc_layer = np.zeros(shape, dtype=np.float32)
    for i in range(n_arcs):
        # Random start/end points
        sy = rng.randint(0, h)
        ey = rng.randint(0, h)
        sx = rng.randint(0, w)
        ex = rng.randint(0, w)
        # Build arc path with random walk
        n_segments = max(20, w // 30)
        arc_x = np.linspace(sx, ex, n_segments).astype(np.int32)
        arc_y = np.linspace(sy, ey, n_segments).astype(np.int32)
        # Add jaggedness
        jitter = rng.randint(-max(3, h // 60), max(3, h // 60) + 1, size=n_segments)
        jitter = np.cumsum(jitter)
        jitter = jitter - np.linspace(jitter[0], jitter[-1], n_segments)  # keep endpoints
        arc_y = np.clip(arc_y + jitter.astype(np.int32), 0, h - 1)
        arc_x = np.clip(arc_x, 0, w - 1)
        # Draw arc with width
        for seg in range(len(arc_x)):
            ay, ax = arc_y[seg], arc_x[seg]
            r = max(1, int(h * 0.005))
            y_lo, y_hi = max(0, ay - r), min(h, ay + r + 1)
            x_lo, x_hi = max(0, ax - r), min(w, ax + r + 1)
            arc_layer[y_lo:y_hi, x_lo:x_hi] = 1.0

    arc_glow = gaussian_filter(arc_layer, sigma=max(2, h * 0.010))
    # Electric cyan-white arcs — BOOSTED
    paint[:,:,0] = np.clip(paint[:,:,0] + arc_glow * 0.42 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + arc_glow * 0.48 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + arc_glow * 0.55 * pm * mask, 0, 1)

    # --- Bright plasma bursts (larger than old specs) ---
    n_bursts = max(10, (h * w) // (150 * 150))
    burst_layer = np.zeros(shape, dtype=np.float32)
    for i in range(n_bursts):
        by = rng.randint(0, h)
        bx = rng.randint(0, w)
        br = max(8, int(min(h, w) * 0.03 * (0.5 + rng.random())))
        yy, xx = np.ogrid[max(0,by-br*3):min(h,by+br*3), max(0,bx-br*3):min(w,bx+br*3)]
        dd = ((yy - by)**2 + (xx - bx)**2).astype(np.float32)
        glow = np.clip(1.0 - dd / (br * br), 0, 1) ** 1.5
        burst_layer[max(0,by-br*3):min(h,by+br*3), max(0,bx-br*3):min(w,bx+br*3)] += glow

    burst_layer = np.clip(burst_layer, 0, 1)
    # Hot white-yellow bursts — BOOSTED
    paint[:,:,0] = np.clip(paint[:,:,0] + burst_layer * 0.48 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + burst_layer * 0.40 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + burst_layer * 0.22 * pm * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Group 15: One-of-a-Kind (all new) ---
spec_lafleur = make_prizm_spec_fn(140, 20, 16, num_bands=6)
spec_affliction = make_flat_spec_fn(100, 50, 0, noise_M=25, noise_R=20, noise_scales=[4, 8, 16])
spec_samurai = make_flat_spec_fn(30, 15, 16, noise_R=10, noise_scales=[8, 16, 32])
spec_dia_de_muertos = make_prizm_spec_fn(80, 25, 16, num_bands=8)
spec_northern_soul = make_flat_spec_fn(160, 30, 0, noise_M=20, noise_scales=[8, 16, 32])

def paint_lafleur(paint, shape, mask, seed, pm, bb):
    """Lafleur — Mardi Gras gold-purple-green with tiled fleur-de-lis motif.
    Procedural fleur-de-lis built from mirrored petal curves."""
    h, w = shape
    y, x = _get_mgrid(shape)
    from scipy.ndimage import gaussian_filter

    # --- Mardi Gras tri-color background zones ---
    zone = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 2000)
    zone = np.clip(zone * 0.5 + 0.5, 0, 1)
    # Gold zones
    gold_z = np.clip(zone * 3, 0, 1) * np.clip(1 - (zone * 3 - 1), 0, 1)
    # Purple zones
    purple_z = np.clip(zone * 3 - 1, 0, 1) * np.clip(1 - (zone * 3 - 2), 0, 1)
    # Green zones
    green_z = np.clip(zone * 3 - 2, 0, 1)

    # Apply Mardi Gras color tints at visible intensity
    paint[:,:,0] = np.clip(paint[:,:,0] + (gold_z * 0.20 + purple_z * 0.12) * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + (gold_z * 0.16 + green_z * 0.18) * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + purple_z * 0.18 * pm * mask, 0, 1)

    # --- Tiled fleur-de-lis ---
    tile_size = max(50, int(min(w, h) * 0.14))
    lx = (x % tile_size).astype(np.float32) / tile_size - 0.5  # -0.5..0.5
    ly = (y % tile_size).astype(np.float32) / tile_size - 0.5
    alx = np.abs(lx)

    # Center petal: tall pointed oval
    center_petal_w = 0.08
    center_petal_h = 0.32
    center_dist = (lx / center_petal_w)**2 + ((ly + 0.08) / center_petal_h)**2
    center_petal = np.clip(1.0 - center_dist * 1.5, 0, 1)

    # Side petals: curved outward from center, mirrored
    # Each side petal curves away from center axis
    side_offset_x = 0.18
    side_offset_y = -0.02
    side_w = 0.10
    side_h = 0.22
    # Rotation: petals angle outward ~30 degrees
    angle = 0.5  # radians
    rlx = (alx - side_offset_x) * np.cos(angle) - (ly - side_offset_y) * np.sin(angle)
    rly = (alx - side_offset_x) * np.sin(angle) + (ly - side_offset_y) * np.cos(angle)
    side_dist = (rlx / side_w)**2 + (rly / side_h)**2
    side_petals = np.clip(1.0 - side_dist * 1.5, 0, 1)
    # Only where side petals exist (abs_x > small threshold)
    side_petals *= (alx > 0.06).astype(np.float32)

    # Stem: thin vertical line below
    stem = ((alx < 0.025) & (ly > 0.10) & (ly < 0.38)).astype(np.float32)

    # Cross bar at base of petals
    crossbar = ((np.abs(ly - 0.12) < 0.018) & (alx < 0.14)).astype(np.float32)

    # Combine
    fdl = np.clip(center_petal + side_petals + stem + crossbar, 0, 1)
    fdl_soft = gaussian_filter(fdl, sigma=max(1, h * 0.003))

    # Fleur-de-lis rendered in bright gold
    paint[:,:,0] = np.clip(paint[:,:,0] + fdl_soft * 0.35 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + fdl_soft * 0.28 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + fdl_soft * 0.05 * pm * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_affliction(paint, shape, mask, seed, pm, bb):
    """Affliction — ornamental cross with spread wings, dark luxury gothic.
    Procedurally generates a centered cross with wing-like filigree radiating outward."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cy, cx = h * 0.45, w * 0.5

    # --- Darken base for gothic mood ---
    paint = np.clip(paint - 0.15 * pm * mask[:,:,np.newaxis], 0, 1)

    # --- Central ornamental cross ---
    # Vertical bar (taller)
    cross_vw = w * 0.015  # cross arm width
    cross_vh = h * 0.28   # vertical bar half-height
    vert = (np.abs(x - cx) < cross_vw) & (np.abs(y - cy) < cross_vh)
    # Horizontal bar (shorter, positioned higher)
    cross_hh = h * 0.015
    cross_hw = w * 0.10
    horiz_cy = cy - h * 0.08  # crossbar sits in upper portion
    horiz = (np.abs(y - horiz_cy) < cross_hh) & (np.abs(x - cx) < cross_hw)
    cross = (vert | horiz).astype(np.float32)

    # Soften cross edges with slight blur via distance
    from scipy.ndimage import gaussian_filter
    cross_soft = gaussian_filter(cross, sigma=max(1, h * 0.004))

    # Cross glow: silver-gold metallic
    paint[:,:,0] = np.clip(paint[:,:,0] + cross_soft * 0.40 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + cross_soft * 0.35 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + cross_soft * 0.25 * pm * mask, 0, 1)

    # --- Wings radiating from cross center ---
    # Wings are mirrored curves spreading outward from the crossbar
    dx = (x - cx) / (w * 0.5)  # normalized -1..1
    dy = (y - horiz_cy) / (h * 0.5)
    abs_dx = np.abs(dx)

    # Wing shape: curved feathered arcs
    # Main wing body: elliptical spread from crossbar
    wing_spread = 0.85  # how far wings extend (0-1 of half-width)
    wing_zone = (abs_dx > 0.04) & (abs_dx < wing_spread)

    # Wing curve: y follows a downward arc from center
    wing_curve_top = -0.02 - (abs_dx * 0.6) ** 1.5  # upper edge curves down
    wing_curve_bot = 0.08 + (abs_dx * 0.4) ** 1.3    # lower edge curves down more
    wing_body = wing_zone & (dy > wing_curve_top) & (dy < wing_curve_bot)

    # Feather striations: parallel lines within wing
    feather_freq = max(20, int(w * 0.03))
    feather_angle = np.arctan2(dy, dx)
    feather_lines = np.sin(feather_angle * feather_freq + abs_dx * 40) * 0.5 + 0.5
    feather_pattern = np.where(feather_lines > 0.45, 1.0, 0.3).astype(np.float32)

    wing_mask = wing_body.astype(np.float32) * feather_pattern
    # Fade wings toward tips
    tip_fade = np.clip(1.0 - (abs_dx / wing_spread) ** 2, 0, 1)
    wing_mask *= tip_fade

    wing_soft = gaussian_filter(wing_mask, sigma=max(1, h * 0.005))

    # Wing glow: slightly darker silver than cross
    paint[:,:,0] = np.clip(paint[:,:,0] + wing_soft * 0.28 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + wing_soft * 0.25 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + wing_soft * 0.20 * pm * mask, 0, 1)

    # --- Filigree scrollwork around cross (noise-based ornamental detail) ---
    filigree = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 2100)
    # Only show filigree near the cross/wing areas
    near_center = np.clip(1.0 - np.sqrt((dx)**2 + (dy)**2) / 0.6, 0, 1)
    filigree_mask = np.where(filigree > 0.72, (filigree - 0.72) / 0.28, 0).astype(np.float32)
    filigree_mask *= near_center * (1.0 - cross_soft) * (1.0 - wing_soft * 0.5)
    # Dim gold filigree accents
    paint[:,:,0] = np.clip(paint[:,:,0] + filigree_mask * 0.12 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + filigree_mask * 0.08 * pm * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_samurai(paint, shape, mask, seed, pm, bb):
    """Samurai — Japanese lacquerware with gold kintsugi cracks."""
    # Deep red-black base
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.02 * pm * mask, 0, 1)
    paint = np.clip(paint - 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    # Gold kintsugi cracks
    crack = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 2200)
    gold_lines = np.where(crack > 0.82, (crack - 0.82) / 0.18, 0).astype(np.float32)
    paint[:,:,0] = np.clip(paint[:,:,0] + gold_lines * 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + gold_lines * 0.05 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dia_de_muertos(paint, shape, mask, seed, pm, bb):
    """Dia de Muertos — tiled sugar skulls with marigold and deep purple celebration.
    Generates repeating skull face geometry with ornamental details."""
    h, w = shape
    y, x = _get_mgrid(shape)
    from scipy.ndimage import gaussian_filter

    # --- Deep purple base tint ---
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.04 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint - 0.06 * pm * mask[:,:,np.newaxis], 0, 1)

    # --- Tiled sugar skull pattern ---
    # Tile size: ~15% of texture width, repeating
    tile_w = max(40, int(w * 0.15))
    tile_h = max(50, int(h * 0.18))

    # Local coords within each tile (0..1)
    lx = (x % tile_w).astype(np.float32) / tile_w  # 0..1
    ly = (y % tile_h).astype(np.float32) / tile_h  # 0..1
    # Center of tile
    cx, cy = 0.5, 0.42

    # Skull outline: rounded shape (wider at top, narrow at chin)
    dx_norm = (lx - cx) / 0.30
    dy_top = (ly - cy) / 0.34
    dy_bot = (ly - cy) / 0.28
    dy_use = np.where(ly < cy, dy_top, dy_bot)
    skull_dist = dx_norm**2 + dy_use**2
    skull = np.clip(1.0 - skull_dist * 1.8, 0, 1)

    # Eye sockets: two circles, upper half of skull
    eye_r = 0.09
    eye_y = cy - 0.06
    left_eye_dist = ((lx - (cx - 0.11))**2 + (ly - eye_y)**2) / eye_r**2
    right_eye_dist = ((lx - (cx + 0.11))**2 + (ly - eye_y)**2) / eye_r**2
    eyes = np.clip(1.0 - left_eye_dist * 2, 0, 1) + np.clip(1.0 - right_eye_dist * 2, 0, 1)
    eyes = np.clip(eyes, 0, 1)

    # Nose: small inverted heart/triangle
    nose_y = cy + 0.06
    nose_dist = ((lx - cx)**2 * 4 + (ly - nose_y)**2 * 8)
    nose = np.clip(1.0 - nose_dist * 30, 0, 1)

    # Mouth: horizontal line of small vertical bars (stitched mouth)
    mouth_y = cy + 0.16
    mouth_zone = (np.abs(ly - mouth_y) < 0.025) & (np.abs(lx - cx) < 0.15)
    stitch_freq = tile_w * 0.4
    stitches = np.sin(lx * stitch_freq * np.pi) > 0.3
    mouth = (mouth_zone & stitches).astype(np.float32)

    # Forehead decoration: marigold petal arc
    petal_y = cy - 0.22
    petal_angle = np.arctan2(ly - petal_y, lx - cx)
    petal_dist = np.sqrt((lx - cx)**2 + (ly - petal_y)**2)
    petals = np.sin(petal_angle * 6) * 0.5 + 0.5
    petal_ring = (petal_dist > 0.08) & (petal_dist < 0.16) & (ly < cy - 0.10)
    petal_mask = petal_ring.astype(np.float32) * petals

    # Soften everything
    skull_soft = gaussian_filter(skull, sigma=max(1, h * 0.003))
    eye_soft = gaussian_filter(eyes, sigma=max(1, h * 0.002))
    nose_soft = gaussian_filter(nose, sigma=max(1, h * 0.002))
    mouth_soft = gaussian_filter(mouth, sigma=max(1, h * 0.002))
    petal_soft = gaussian_filter(petal_mask, sigma=max(1, h * 0.003))

    # --- Apply skull: white/cream skull face ---
    skull_vis = skull_soft * (1.0 - eye_soft * 0.8 - nose_soft * 0.6)
    paint[:,:,0] = np.clip(paint[:,:,0] + skull_vis * 0.30 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + skull_vis * 0.28 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + skull_vis * 0.25 * pm * mask, 0, 1)

    # Eye sockets: dark with slight purple glow
    paint[:,:,0] = np.clip(paint[:,:,0] - eye_soft * 0.15 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - eye_soft * 0.18 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + eye_soft * 0.05 * pm * mask, 0, 1)

    # Nose cavity: dark
    paint = np.clip(paint - nose_soft[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1)

    # Stitched mouth: dark lines
    paint = np.clip(paint - mouth_soft[:,:,np.newaxis] * 0.20 * pm * mask[:,:,np.newaxis], 0, 1)

    # Marigold petals: bright orange
    paint[:,:,0] = np.clip(paint[:,:,0] + petal_soft * 0.35 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + petal_soft * 0.18 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - petal_soft * 0.05 * pm * mask, 0, 1)

    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_northern_soul(paint, shape, mask, seed, pm, bb):
    """Northern Soul — warm gold on midnight vinyl."""
    # Darken base
    paint = np.clip(paint - 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    # Gold glow accents
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 2400)
    gold = np.where(noise > 0.7, (noise - 0.7) / 0.3, 0).astype(np.float32)
    paint[:,:,0] = np.clip(paint[:,:,0] + gold * 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + gold * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint



# ================================================================
# 24K+ ARSENAL — MISSING MONOLITHIC DEFINITIONS (135 entries)
# ================================================================
# These fill the gap between HTML SPECIAL_GROUPS catalog and Python registry.
# All use factory functions for efficient, consistent implementations.

# --- Chameleon Classic (5 gap-fill — UPGRADED to full sine-wave HSV hue ramp) ---
def spec_chameleon_aurora(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_aurora(paint, shape, mask, seed, pm, bb):
    """Aurora — Green to Cyan to Purple (Northern Lights sweep, 200 degrees)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 130, 200)
def spec_chameleon_fire(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_fire(paint, shape, mask, seed, pm, bb):
    """Fire — Red to Orange to Gold (50 degree warm sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 0, 50)
def spec_chameleon_frost(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_frost(paint, shape, mask, seed, pm, bb):
    """Frost — Icy Blue to Teal to Aqua (60 degree cool sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 195, 60)
def spec_chameleon_galaxy(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_galaxy(paint, shape, mask, seed, pm, bb):
    """Galaxy — Deep Purple to Blue to Teal to Green (160 degree cosmic sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 260, 160)
def spec_chameleon_neon(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_neon(paint, shape, mask, seed, pm, bb):
    """Neon — Magenta to Red to Orange to Yellow to Green (240 degree full neon sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 300, 240)

# --- Color Shift Adaptive (7 gap-fill — UPGRADED to dithered Fresnel dual-population) ---
def spec_cs_chrome_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 245, 'R': 5, 'CC': 18}, {'M': 220, 'R': 18, 'CC': 22})
def paint_cs_chrome_shift(paint, shape, mask, seed, pm, bb):
    """Chrome Shift — subtle 30 degree shift, ultra-high metallic feel"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 30, sat_delta=0.05, val_delta=0.05)
def spec_cs_earth(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 200, 'R': 20, 'CC': 14}, {'M': 170, 'R': 40, 'CC': 18})
def paint_cs_earth(paint, shape, mask, seed, pm, bb):
    """Earth — warm 45 degree shift towards earthy tones"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 45, sat_delta=-0.10, val_delta=-0.08)
def spec_cs_monochrome(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 220, 'R': 12, 'CC': 16}, {'M': 185, 'R': 35, 'CC': 20})
def paint_cs_monochrome(paint, shape, mask, seed, pm, bb):
    """Monochrome — no hue shift, only saturation/value differential"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 0, sat_delta=-0.30, val_delta=0.10)
def spec_cs_neon_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 238, 'R': 6, 'CC': 16}, {'M': 205, 'R': 24, 'CC': 20})
def paint_cs_neon_shift(paint, shape, mask, seed, pm, bb):
    """Neon Shift — vivid 90 degree shift"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 90, sat_delta=0.15, val_delta=0.05)
def spec_cs_ocean_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 225, 'R': 14, 'CC': 18}, {'M': 190, 'R': 32, 'CC': 22})
def paint_cs_ocean_shift(paint, shape, mask, seed, pm, bb):
    """Ocean Shift — cool -60 degree shift towards blue/teal"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, -60, sat_delta=0.08, val_delta=-0.03)
def spec_cs_prism_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 235, 'R': 8, 'CC': 16}, {'M': 200, 'R': 28, 'CC': 22})
def paint_cs_prism_shift(paint, shape, mask, seed, pm, bb):
    """Prism Shift — prismatic 120 degree shift"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 120, sat_delta=0.12, val_delta=0.0)
def spec_cs_vivid(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 232, 'R': 10, 'CC': 16}, {'M': 198, 'R': 26, 'CC': 20})
def paint_cs_vivid(paint, shape, mask, seed, pm, bb):
    """Vivid — 60 degree shift with strong saturation boost"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 60, sat_delta=0.20, val_delta=0.05)

# --- Color Shift Preset (5 gap-fill — UPGRADED to fixed two-color dithered Fresnel) ---
def spec_cs_candy_paint(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 228, 'R': 10, 'CC': 18}, {'M': 195, 'R': 28, 'CC': 22})
def paint_cs_candy_paint(paint, shape, mask, seed, pm, bb):
    """Candy Paint — Hot Pink to Teal"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 340, 180, 0.88, 0.85, 0.80, 0.78)
def spec_cs_dark_flame(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 215, 'R': 18, 'CC': 14}, {'M': 180, 'R': 38, 'CC': 18})
def paint_cs_dark_flame(paint, shape, mask, seed, pm, bb):
    """Dark Flame — Deep Crimson to Dark Orange"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 5, 30, 0.90, 0.85, 0.60, 0.55)
def spec_cs_gold_rush(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 240, 'R': 6, 'CC': 18}, {'M': 210, 'R': 20, 'CC': 22})
def paint_cs_gold_rush(paint, shape, mask, seed, pm, bb):
    """Gold Rush — Rich Gold to Warm Bronze"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 48, 25, 0.85, 0.78, 0.85, 0.72)
def spec_cs_oilslick(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 220, 'R': 14, 'CC': 16}, {'M': 185, 'R': 32, 'CC': 20})
def paint_cs_oilslick(paint, shape, mask, seed, pm, bb):
    """Oil Slick — Dark Violet to Dark Teal (iridescent dark)"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 280, 180, 0.75, 0.70, 0.50, 0.45)
def spec_cs_rose_gold_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 235, 'R': 8, 'CC': 18}, {'M': 205, 'R': 22, 'CC': 22})
def paint_cs_rose_gold_shift(paint, shape, mask, seed, pm, bb):
    """Rose Gold Shift — Rose Pink to Warm Gold"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 350, 38, 0.55, 0.50, 0.82, 0.80)

# --- Prizm Series (4 gap-fill — UPGRADED to panel-aware multi-color ramp) ---
def spec_prizm_cosmos(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=18)
def paint_prizm_cosmos(paint, shape, mask, seed, pm, bb):
    """Cosmos — Deep space: Violet to Indigo to Teal to Nebula Pink"""
    stops = [
        (0.00, 270, 0.80, 0.55),  # Deep Violet
        (0.30, 240, 0.82, 0.50),  # Indigo
        (0.55, 195, 0.78, 0.58),  # Deep Teal
        (0.80, 290, 0.72, 0.62),  # Nebula Purple
        (1.00, 330, 0.65, 0.65),  # Nebula Pink
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.030)
def spec_prizm_dark_matter(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=230, roughness=18, clearcoat=14)
def paint_prizm_dark_matter(paint, shape, mask, seed, pm, bb):
    """Dark Matter — Ultra-dark subtle shift: Near-Black to Dark Purple to Dark Blue"""
    stops = [
        (0.00, 270, 0.60, 0.20),  # Near-Black Purple
        (0.35, 250, 0.55, 0.18),  # Dark Blue-Purple
        (0.65, 220, 0.50, 0.22),  # Dark Blue
        (1.00, 280, 0.45, 0.25),  # Dark Violet
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.020)
def spec_prizm_fire_ice(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=228, roughness=12, clearcoat=18)
def paint_prizm_fire_ice(paint, shape, mask, seed, pm, bb):
    """Fire & Ice — Hot red/orange contrasting with cold blue/teal"""
    stops = [
        (0.00, 5,   0.88, 0.78),  # Fire Red
        (0.25, 30,  0.85, 0.82),  # Orange
        (0.50, 48,  0.80, 0.80),  # Gold (transition)
        (0.75, 195, 0.85, 0.76),  # Ice Teal
        (1.00, 220, 0.82, 0.72),  # Ice Blue
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.028)
def spec_prizm_spectrum(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=230, roughness=11, clearcoat=18)
def paint_prizm_spectrum(paint, shape, mask, seed, pm, bb):
    """Spectrum — Full visible spectrum: Red to Violet (7-stop rainbow)"""
    stops = [
        (0.00, 0,   0.85, 0.82),  # Red
        (0.16, 30,  0.82, 0.84),  # Orange
        (0.32, 55,  0.80, 0.86),  # Yellow
        (0.48, 120, 0.82, 0.78),  # Green
        (0.64, 200, 0.85, 0.76),  # Blue
        (0.82, 260, 0.80, 0.74),  # Indigo
        (1.00, 290, 0.78, 0.76),  # Violet
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.025)

# --- Effect & Visual (13 missing) — these PRESERVE car color, add visual effects ---
spec_chromatic_aberration = make_effect_spec_fn(80, 30, 16, effect_type="noise")
spec_crt_scanline = make_effect_spec_fn(70, 25, 16, effect_type="bands")
spec_datamosh = make_effect_spec_fn(60, 40, 16, effect_type="noise")
spec_embossed = make_flat_spec_fn(100, 80, 16, noise_M=20, noise_R=30, noise_scales=[4, 8, 16])
spec_film_burn = make_effect_spec_fn(80, 35, 16, effect_type="gradient")
spec_fish_eye = make_effect_spec_fn(60, 30, 16, effect_type="radial")
spec_halftone = make_effect_spec_fn(70, 35, 16, effect_type="noise")
spec_kaleidoscope = make_effect_spec_fn(90, 25, 16, effect_type="radial")
spec_long_exposure = make_effect_spec_fn(50, 40, 16, effect_type="gradient")
spec_negative = make_flat_spec_fn(80, 30, 16, noise_M=15, noise_scales=[8, 16])
spec_parallax = make_effect_spec_fn(70, 30, 16, effect_type="gradient")
spec_refraction = make_effect_spec_fn(60, 25, 16, effect_type="noise")
spec_solarization = make_effect_spec_fn(90, 20, 16, effect_type="gradient")
paint_chromatic_aberration = make_weather_paint_fn(noise_str=0.04, tint_rgb=[0.05, -0.02, 0.05])
paint_crt_scanline = make_weather_paint_fn(noise_str=0.03, darken=0.04)
paint_datamosh = make_weather_paint_fn(noise_str=0.06, desat=0.04)
paint_embossed = make_weather_paint_fn(noise_str=0.03)
paint_film_burn = make_weather_paint_fn(noise_str=0.04, tint_rgb=[0.05, 0.02, -0.02])
paint_fish_eye = make_weather_paint_fn(noise_str=0.03)
paint_halftone = make_weather_paint_fn(noise_str=0.04, desat=0.03)
paint_kaleidoscope = make_weather_paint_fn(noise_str=0.04)
paint_long_exposure = make_weather_paint_fn(noise_str=0.03, desat=0.05)
paint_negative = make_weather_paint_fn(noise_str=0.03, darken=0.03)
paint_parallax = make_weather_paint_fn(noise_str=0.03)
paint_refraction = make_weather_paint_fn(noise_str=0.04)
paint_solarization = make_weather_paint_fn(noise_str=0.04, tint_rgb=[0.03, 0.0, 0.03])

# --- Racing Legend (10 missing) ---
spec_burnout_zone = make_flat_spec_fn(160, 25, 16, noise_M=25, noise_R=15, noise_scales=[4, 8])
spec_chicane_blur = make_effect_spec_fn(80, 30, 16, effect_type="noise")
spec_cool_down = make_flat_spec_fn(40, 50, 16, noise_R=20, noise_scales=[8, 16])
spec_drag_chute = make_flat_spec_fn(60, 80, 16, noise_R=25, noise_scales=[4, 8, 16])
spec_flag_wave = make_effect_spec_fn(100, 20, 16, effect_type="bands")
spec_grid_walk = make_flat_spec_fn(50, 40, 16, noise_M=15, noise_scales=[8, 16])
spec_night_race = make_effect_spec_fn(30, 150, 0, effect_type="gradient")
spec_pit_stop = make_flat_spec_fn(100, 50, 16, noise_M=20, noise_R=15, noise_scales=[4, 8])
spec_red_mist = make_effect_spec_fn(120, 30, 16, effect_type="noise")
spec_slipstream = make_effect_spec_fn(90, 25, 16, effect_type="gradient")
paint_burnout_zone = make_weather_paint_fn(noise_str=0.05, tint_rgb=[0.15, 0.1, 0.0])
paint_chicane_blur = make_weather_paint_fn(noise_str=0.05, desat=0.04)
paint_cool_down = make_glow_fn([0.1, 0.2, 0.4], glow_strength=0.05)
paint_drag_chute = make_weather_paint_fn(darken=0.06, noise_str=0.04)
paint_flag_wave = make_weather_paint_fn(noise_str=0.04)
paint_grid_walk = make_weather_paint_fn(noise_str=0.03)
paint_night_race = make_weather_paint_fn(darken=0.10, tint_rgb=[0.05, 0.05, 0.15])
paint_pit_stop = make_weather_paint_fn(noise_str=0.04, tint_rgb=[0.05, 0.05, 0.0])
paint_red_mist = make_glow_fn([0.5, 0.0, 0.0], glow_strength=0.06)
paint_slipstream = make_weather_paint_fn(noise_str=0.04, desat=0.03)

# --- Weather & Element (15 missing) ---
spec_acid_rain = make_flat_spec_fn(40, 80, 0, noise_R=25, noise_scales=[4, 8, 16])
spec_black_ice = make_flat_spec_fn(30, 10, 16, noise_R=10, noise_scales=[16, 32])
spec_blizzard = make_effect_spec_fn(60, 40, 16, effect_type="noise")
spec_dew_drop = make_flat_spec_fn(50, 20, 16, noise_M=10, noise_scales=[2, 4])
spec_dust_storm = make_flat_spec_fn(30, 120, 0, noise_R=30, noise_scales=[4, 8, 16])
spec_fog_bank = make_effect_spec_fn(20, 60, 0, effect_type="gradient")
spec_hail_damage = make_flat_spec_fn(80, 100, 0, noise_R=35, noise_scales=[2, 4, 8])
spec_heat_wave = make_effect_spec_fn(40, 80, 0, effect_type="noise")
spec_hurricane = make_effect_spec_fn(50, 120, 0, effect_type="radial")
spec_lightning_strike = make_effect_spec_fn(200, 15, 16, effect_type="noise")
spec_magma_flow = make_flat_spec_fn(60, 60, 0, noise_M=20, noise_R=20, noise_scales=[4, 8, 16])
spec_monsoon = make_flat_spec_fn(30, 90, 0, noise_R=25, noise_scales=[4, 8, 16])
spec_permafrost = make_flat_spec_fn(25, 15, 16, noise_R=10, noise_scales=[16, 32])
spec_solar_wind = make_effect_spec_fn(150, 20, 16, effect_type="gradient")
spec_tidal_wave = make_effect_spec_fn(60, 70, 0, effect_type="radial")
paint_acid_rain = make_aged_fn(fade_strength=0.10, roughen=0.06)
paint_black_ice = make_vivid_depth_fn(sat_boost=0.05, depth_darken=0.08)
paint_blizzard = make_glow_fn([0.3, 0.35, 0.4], glow_strength=0.06)
paint_dew_drop = make_luxury_sparkle_fn(sparkle_density=0.96, sparkle_strength=0.06)
paint_dust_storm = make_weather_paint_fn(desat=0.15, tint_rgb=[0.2, 0.15, 0.05], noise_str=0.06)
paint_fog_bank = make_weather_paint_fn(desat=0.12, darken=0.04, noise_str=0.04)
paint_hail_damage = make_aged_fn(fade_strength=0.08, roughen=0.08)
paint_heat_wave = make_weather_paint_fn(tint_rgb=[0.2, 0.1, 0.0], noise_str=0.05)
paint_hurricane = make_weather_paint_fn(darken=0.10, noise_str=0.06)
paint_lightning_strike = make_glow_fn([0.5, 0.5, 0.7], glow_strength=0.08)
paint_magma_flow = make_glow_fn([0.6, 0.2, 0.0], glow_strength=0.07)
paint_monsoon = make_weather_paint_fn(tint_rgb=[0.0, 0.1, 0.2], noise_str=0.06)
paint_permafrost = make_glow_fn([0.15, 0.25, 0.35], glow_strength=0.05)
paint_solar_wind = make_glow_fn([0.4, 0.3, 0.1], glow_strength=0.06)
paint_tidal_wave = make_glow_fn([0.0, 0.3, 0.5], glow_strength=0.06)

# --- Dark & Gothic (15 missing) ---
spec_banshee = make_effect_spec_fn(20, 180, 0, effect_type="noise")
spec_blood_oath = make_flat_spec_fn(30, 200, 0, noise_R=25, noise_scales=[4, 8])
spec_catacombs = make_flat_spec_fn(25, 190, 0, noise_R=30, noise_scales=[4, 8, 16])
spec_dark_ritual = make_effect_spec_fn(15, 210, 0, effect_type="radial")
spec_death_metal = make_flat_spec_fn(120, 160, 0, noise_M=20, noise_R=25, noise_scales=[4, 8])
spec_demon_forge = make_flat_spec_fn(80, 150, 0, noise_M=20, noise_R=20, noise_scales=[4, 8, 16])
spec_gargoyle = make_flat_spec_fn(40, 170, 0, noise_R=30, noise_scales=[4, 8, 16])
spec_graveyard = make_flat_spec_fn(20, 180, 0, noise_R=25, noise_scales=[8, 16])
spec_haunted = make_effect_spec_fn(25, 160, 0, effect_type="noise")
spec_hellhound = make_flat_spec_fn(100, 140, 0, noise_M=25, noise_R=20, noise_scales=[4, 8])
spec_iron_maiden = make_flat_spec_fn(60, 180, 0, noise_R=30, noise_scales=[4, 8, 16])
spec_lich_king = make_effect_spec_fn(30, 200, 0, effect_type="gradient")
spec_necrotic = make_flat_spec_fn(20, 190, 0, noise_R=35, noise_scales=[4, 8])
spec_shadow_realm = make_effect_spec_fn(10, 220, 0, effect_type="gradient")
spec_spectral = make_effect_spec_fn(40, 140, 0, effect_type="noise")
paint_banshee = make_weather_paint_fn(darken=0.14, desat=0.18, noise_str=0.05)
paint_blood_oath = make_glow_fn([0.5, 0.0, 0.0], glow_strength=0.07)
paint_catacombs = make_weather_paint_fn(darken=0.16, desat=0.12, noise_str=0.05)
paint_dark_ritual = make_glow_fn([0.3, 0.0, 0.4], glow_strength=0.06)
paint_death_metal = make_weather_paint_fn(darken=0.12, noise_str=0.05)
paint_demon_forge = make_glow_fn([0.5, 0.15, 0.0], glow_strength=0.07)
paint_gargoyle = make_weather_paint_fn(darken=0.14, desat=0.15, noise_str=0.04)
paint_graveyard = make_weather_paint_fn(darken=0.16, desat=0.18, noise_str=0.04)
paint_haunted = make_weather_paint_fn(darken=0.12, desat=0.14, noise_str=0.05)
paint_hellhound = make_glow_fn([0.6, 0.1, 0.0], glow_strength=0.07)
paint_iron_maiden = make_weather_paint_fn(darken=0.10, noise_str=0.05)
paint_lich_king = make_glow_fn([0.1, 0.4, 0.1], glow_strength=0.06)
paint_necrotic = make_aged_fn(fade_strength=0.15, roughen=0.08)
paint_shadow_realm = make_weather_paint_fn(darken=0.20, desat=0.18)
paint_spectral = make_weather_paint_fn(darken=0.08, desat=0.12, noise_str=0.04)

# --- Neon & Glow (15 missing) ---
spec_aurora_glow = make_flat_spec_fn(80, 30, 16, noise_M=20, noise_scales=[8, 16])
spec_blacklight_paint = make_flat_spec_fn(60, 40, 16, noise_M=20, noise_scales=[4, 8])
spec_bioluminescent_wave = make_effect_spec_fn(70, 35, 16, effect_type="gradient")
spec_electric_arc = make_effect_spec_fn(150, 15, 16, effect_type="noise")
spec_fluorescent = make_flat_spec_fn(50, 30, 16, noise_M=15, noise_scales=[8, 16])
spec_glow_stick = make_flat_spec_fn(40, 35, 16, noise_M=15, noise_scales=[4, 8])
spec_laser_show = make_effect_spec_fn(120, 20, 16, effect_type="bands")
spec_magnesium_burn = make_effect_spec_fn(220, 8, 16, effect_type="noise")
spec_neon_sign = make_flat_spec_fn(90, 25, 16, noise_M=20, noise_scales=[4, 8])
spec_phosphorescent = make_flat_spec_fn(60, 40, 16, noise_M=15, noise_scales=[8, 16])
spec_rave = make_flat_spec_fn(70, 30, 16, noise_M=25, noise_scales=[4, 8])
spec_sodium_lamp = make_flat_spec_fn(100, 35, 16, noise_M=15, noise_scales=[8, 16])
spec_tesla_coil = make_effect_spec_fn(160, 15, 16, effect_type="noise")
spec_tracer_round = make_effect_spec_fn(180, 12, 16, effect_type="gradient")
spec_welding_arc = make_effect_spec_fn(200, 10, 16, effect_type="noise")
paint_aurora_glow = make_glow_fn([0.0, 0.5, 0.3], glow_strength=0.07)
paint_blacklight_paint = make_glow_fn([0.3, 0.0, 0.6], glow_strength=0.08)
paint_bioluminescent_wave = make_glow_fn([0.0, 0.6, 0.4], glow_strength=0.07)
paint_electric_arc = make_glow_fn([0.3, 0.5, 0.8], glow_strength=0.08)
paint_fluorescent = make_glow_fn([0.2, 0.6, 0.1], glow_strength=0.07)
paint_glow_stick = make_glow_fn([0.1, 0.7, 0.0], glow_strength=0.08)
paint_laser_show = make_colorshift_paint_fn([(0.8, 0.0, 0.0), (0.0, 0.8, 0.0), (0.0, 0.0, 0.8)])
paint_magnesium_burn = make_glow_fn([0.8, 0.8, 0.8], glow_strength=0.08)
paint_neon_sign = make_glow_fn([0.7, 0.0, 0.3], glow_strength=0.07)
paint_phosphorescent = make_glow_fn([0.1, 0.5, 0.2], glow_strength=0.06)
paint_rave = make_colorshift_paint_fn([(0.7, 0.0, 0.5), (0.0, 0.7, 0.3), (0.7, 0.7, 0.0)])
paint_sodium_lamp = make_glow_fn([0.6, 0.4, 0.0], glow_strength=0.06)
paint_tesla_coil = make_glow_fn([0.2, 0.3, 0.8], glow_strength=0.08)
paint_tracer_round = make_glow_fn([0.7, 0.4, 0.0], glow_strength=0.08)
paint_welding_arc = make_glow_fn([0.6, 0.6, 0.8], glow_strength=0.08)

# --- Texture & Surface (4 missing) ---
spec_granite = make_flat_spec_fn(60, 120, 0, noise_R=30, noise_scales=[2, 4, 8])
spec_obsidian_glass = make_flat_spec_fn(30, 8, 16, noise_M=15, noise_scales=[16, 32])
spec_slate_tile = make_flat_spec_fn(40, 140, 0, noise_R=25, noise_scales=[4, 8, 16])
spec_volcanic_rock = make_flat_spec_fn(35, 160, 0, noise_R=35, noise_scales=[2, 4, 8])
paint_granite = make_weather_paint_fn(noise_str=0.06, desat=0.08)
paint_obsidian_glass = make_vivid_depth_fn(sat_boost=0.06, depth_darken=0.12)
paint_slate_tile = make_weather_paint_fn(desat=0.10, noise_str=0.05)
paint_volcanic_rock = make_weather_paint_fn(darken=0.08, desat=0.10, noise_str=0.06)

# --- Vintage & Retro (17 missing) ---
spec_art_deco_gold = make_flat_spec_fn(200, 10, 16, noise_M=20, noise_scales=[8, 16, 32])
spec_beat_up_truck = make_flat_spec_fn(50, 140, 0, noise_R=35, noise_scales=[4, 8, 16])
spec_classic_racing = make_flat_spec_fn(120, 25, 16, noise_M=20, noise_scales=[8, 16])
spec_daguerreotype = make_flat_spec_fn(60, 80, 0, noise_R=20, noise_scales=[8, 16, 32])
spec_diner_chrome = make_flat_spec_fn(220, 5, 16, noise_M=15, noise_scales=[16, 32])
spec_faded_glory = make_flat_spec_fn(80, 90, 0, noise_R=25, noise_scales=[4, 8, 16])
spec_grindhouse = make_flat_spec_fn(50, 100, 0, noise_R=30, noise_scales=[4, 8])
spec_jukebox = make_flat_spec_fn(160, 15, 16, noise_M=20, noise_scales=[8, 16])
spec_moonshine = make_flat_spec_fn(40, 60, 0, noise_R=20, noise_scales=[8, 16, 32])
spec_nascar_heritage = make_flat_spec_fn(140, 20, 16, noise_M=20, noise_scales=[8, 16])
spec_nostalgia_drag = make_flat_spec_fn(100, 30, 16, noise_M=20, noise_R=15, noise_scales=[4, 8])
spec_old_school = make_flat_spec_fn(90, 50, 16, noise_R=20, noise_scales=[8, 16])
spec_psychedelic = make_effect_spec_fn(80, 30, 16, effect_type="radial")
spec_sepia = make_flat_spec_fn(60, 70, 0, noise_R=15, noise_scales=[8, 16, 32])
spec_tin_type = make_flat_spec_fn(100, 60, 0, noise_R=20, noise_scales=[8, 16])
spec_woodie = make_flat_spec_fn(50, 100, 0, noise_R=25, noise_scales=[4, 8, 16])
spec_zeppelin = make_flat_spec_fn(130, 30, 16, noise_M=15, noise_scales=[8, 16, 32])
paint_art_deco_gold = make_chrome_tint_fn(0.85, 0.75, 0.30, blend=0.15)
paint_beat_up_truck = make_aged_fn(fade_strength=0.18, roughen=0.10)
paint_classic_racing = make_vivid_depth_fn(sat_boost=0.12, depth_darken=0.04)
paint_daguerreotype = make_aged_fn(fade_strength=0.20, roughen=0.06)
paint_diner_chrome = make_chrome_tint_fn(0.9, 0.9, 0.9, blend=0.18)
paint_faded_glory = make_aged_fn(fade_strength=0.15, roughen=0.06)
paint_grindhouse = make_aged_fn(fade_strength=0.14, roughen=0.08)
paint_jukebox = make_chrome_tint_fn(0.8, 0.6, 0.3, blend=0.12)
paint_moonshine = make_weather_paint_fn(desat=0.08, noise_str=0.05)
paint_nascar_heritage = make_vivid_depth_fn(sat_boost=0.14, depth_darken=0.03)
paint_nostalgia_drag = make_vivid_depth_fn(sat_boost=0.10, depth_darken=0.05)
paint_old_school = make_aged_fn(fade_strength=0.10, roughen=0.05)
paint_psychedelic = make_colorshift_paint_fn([(0.6, 0.0, 0.4), (0.4, 0.6, 0.0), (0.0, 0.4, 0.6)])
paint_sepia = make_weather_paint_fn(desat=0.20, tint_rgb=[0.15, 0.1, 0.0])
paint_tin_type = make_aged_fn(fade_strength=0.16, roughen=0.05)
paint_woodie = make_weather_paint_fn(tint_rgb=[0.2, 0.12, 0.04], noise_str=0.05)
paint_zeppelin = make_chrome_tint_fn(0.7, 0.7, 0.75, blend=0.12)

# --- Surreal & Fantasy (14 missing) ---
spec_astral = make_effect_spec_fn(80, 30, 16, effect_type="gradient")
spec_crystal_cave = make_flat_spec_fn(120, 15, 16, noise_M=25, noise_scales=[4, 8, 16])
spec_dark_fairy = make_effect_spec_fn(50, 100, 0, effect_type="noise")
spec_dragon_breath = make_effect_spec_fn(150, 20, 16, effect_type="noise")
spec_enchanted = make_effect_spec_fn(70, 35, 16, effect_type="gradient")
spec_ethereal = make_effect_spec_fn(40, 50, 16, effect_type="gradient")
spec_fractal_dimension = make_effect_spec_fn(90, 25, 16, effect_type="radial")
spec_hallucination = make_effect_spec_fn(60, 35, 16, effect_type="noise")
spec_levitation = make_effect_spec_fn(50, 30, 16, effect_type="gradient")
spec_multiverse = make_effect_spec_fn(80, 25, 16, effect_type="radial")
spec_nebula_core = make_effect_spec_fn(100, 20, 16, effect_type="noise")
spec_simulation = make_effect_spec_fn(70, 30, 16, effect_type="bands")
spec_tesseract = make_effect_spec_fn(110, 20, 16, effect_type="radial")
spec_void_walker = make_effect_spec_fn(20, 200, 0, effect_type="gradient")
paint_astral = make_glow_fn([0.2, 0.2, 0.5], glow_strength=0.06)
paint_crystal_cave = make_luxury_sparkle_fn(sparkle_density=0.95, sparkle_strength=0.08)
paint_dark_fairy = make_glow_fn([0.3, 0.0, 0.4], glow_strength=0.06)
paint_dragon_breath = make_glow_fn([0.6, 0.2, 0.0], glow_strength=0.07)
paint_enchanted = make_glow_fn([0.2, 0.4, 0.3], glow_strength=0.06)
paint_ethereal = make_weather_paint_fn(desat=0.08, noise_str=0.04)
paint_fractal_dimension = make_colorshift_paint_fn([(0.4, 0.0, 0.3), (0.0, 0.3, 0.4), (0.3, 0.3, 0.0)])
paint_hallucination = make_colorshift_paint_fn([(0.5, 0.0, 0.3), (0.0, 0.5, 0.2), (0.3, 0.2, 0.5)])
paint_levitation = make_weather_paint_fn(noise_str=0.03, desat=0.04)
paint_multiverse = make_colorshift_paint_fn([(0.3, 0.0, 0.4), (0.0, 0.3, 0.3), (0.4, 0.2, 0.0)])
paint_nebula_core = make_glow_fn([0.4, 0.1, 0.5], glow_strength=0.07)
paint_simulation = make_glow_fn([0.0, 0.5, 0.2], glow_strength=0.06)
paint_tesseract = make_colorshift_paint_fn([(0.0, 0.3, 0.5), (0.4, 0.0, 0.3), (0.2, 0.4, 0.0)])
paint_void_walker = make_weather_paint_fn(darken=0.18, desat=0.15, noise_str=0.04)

# --- Novelty & Fun (11 missing) ---
spec_aged_leather = make_flat_spec_fn(40, 130, 0, noise_R=25, noise_scales=[4, 8, 16])
spec_bark = make_flat_spec_fn(30, 150, 0, noise_R=30, noise_scales=[4, 8, 16])
spec_bone = make_flat_spec_fn(60, 80, 0, noise_R=20, noise_scales=[8, 16])
spec_brick_wall = make_flat_spec_fn(35, 160, 0, noise_R=25, noise_scales=[4, 8])
spec_burlap = make_flat_spec_fn(20, 170, 0, noise_R=30, noise_scales=[2, 4, 8])
spec_cork = make_flat_spec_fn(25, 140, 0, noise_R=25, noise_scales=[2, 4, 8])
spec_linen = make_flat_spec_fn(30, 120, 0, noise_R=20, noise_scales=[4, 8])
spec_parchment = make_flat_spec_fn(50, 100, 0, noise_R=20, noise_scales=[8, 16, 32])
spec_stucco = make_flat_spec_fn(40, 150, 0, noise_R=30, noise_scales=[2, 4, 8])
spec_suede = make_flat_spec_fn(20, 160, 0, noise_R=20, noise_scales=[8, 16])
spec_terra_cotta = make_flat_spec_fn(35, 140, 0, noise_R=25, noise_scales=[4, 8, 16])
paint_aged_leather = make_aged_fn(fade_strength=0.12, roughen=0.06)
paint_bark = make_weather_paint_fn(tint_rgb=[0.15, 0.08, 0.02], noise_str=0.06)
paint_bone = make_weather_paint_fn(desat=0.15, tint_rgb=[0.1, 0.08, 0.04])
paint_brick_wall = make_weather_paint_fn(tint_rgb=[0.15, 0.05, 0.02], noise_str=0.05)
paint_burlap = make_weather_paint_fn(desat=0.12, tint_rgb=[0.12, 0.08, 0.02], noise_str=0.06)
paint_cork = make_weather_paint_fn(tint_rgb=[0.15, 0.1, 0.04], noise_str=0.05)
paint_linen = make_weather_paint_fn(desat=0.08, noise_str=0.04)
paint_parchment = make_aged_fn(fade_strength=0.14, roughen=0.05)
paint_stucco = make_weather_paint_fn(noise_str=0.06, desat=0.10)
paint_suede = make_weather_paint_fn(desat=0.10, noise_str=0.04)
paint_terra_cotta = make_weather_paint_fn(tint_rgb=[0.18, 0.08, 0.02], noise_str=0.05)


# ================================================================
# EXPANSION MONOLITHICS REGISTRY (240+ new special entries)
# ================================================================
# Format: (spec_fn, paint_fn) tuples — same as existing MONOLITHIC_REGISTRY

EXPANSION_MONOLITHICS = {
    # Group 1: Chameleon Classic (new entries — chameleon_midnight thru chameleon_copper, mystichrome exist)
    "chameleon_amethyst":   (spec_chameleon_amethyst, paint_chameleon_amethyst),
    "chameleon_emerald":    (spec_chameleon_emerald, paint_chameleon_emerald),
    "chameleon_obsidian":   (spec_chameleon_obsidian, paint_chameleon_obsidian),
    # Group 2: Color Shift Adaptive (new entries — cs_warm thru cs_extreme exist)
    "cs_complementary":     (spec_cs_complementary, paint_cs_complementary),
    "cs_triadic":           (spec_cs_triadic, paint_cs_triadic),
    "cs_split":             (spec_cs_split, paint_cs_split),
    # Group 3: Color Shift Preset (new entries — cs_emerald thru cs_mystichrome exist)
    "cs_neon_dreams":       (spec_cs_neon_dreams, paint_cs_neon_dreams),
    "cs_twilight":          (spec_cs_twilight, paint_cs_twilight),
    "cs_toxic":             (spec_cs_toxic, paint_cs_toxic),
    # Group 4: Prizm Series (new entries — prizm_holographic thru prizm_adaptive exist)
    "prizm_neon":           (spec_prizm_neon, paint_prizm_neon),
    "prizm_blood_moon":     (spec_prizm_blood_moon, paint_prizm_blood_moon),
    # Group 5: Effect & Visual (new entries — phantom thru thermochromic exist)
    "x_ray":                (spec_x_ray, paint_x_ray),
    "infrared":             (spec_infrared, paint_infrared),
    "uv_blacklight":        (spec_uv_blacklight, paint_uv_blacklight),
    "double_exposure":      (spec_double_exposure, paint_double_exposure),
    "depth_map":            (spec_depth_map, paint_depth_map),
    "polarized":            (spec_polarized, paint_polarized),
}

EXPANSION_MONOLITHICS.update({
    # Group 6: Racing Legend (all new)
    "victory_burnout":      (spec_victory_burnout, paint_victory_burnout),
    "photo_finish":         (spec_photo_finish, paint_photo_finish),
    "heat_haze":            (spec_heat_haze, paint_heat_haze),
    "race_worn":            (spec_race_worn, paint_race_worn),
    "pace_lap":             (spec_pace_lap, paint_pace_lap),
    "green_flag":           (spec_green_flag, paint_green_flag),
    "black_flag":           (spec_black_flag, paint_black_flag),
    "white_flag":           (spec_white_flag, paint_white_flag),
    "under_lights":         (spec_under_lights, paint_under_lights),
    "dawn_patrol":          (spec_dawn_patrol, paint_dawn_patrol),
    "rain_race":            (spec_rain_race, paint_rain_race),
    "tunnel_run":           (spec_tunnel_run, paint_tunnel_run),
    "drafting":             (spec_drafting, paint_drafting),
    "pole_position":        (spec_pole_position, paint_pole_position),
    "last_lap":             (spec_last_lap, paint_last_lap),
    # Group 7: Weather & Element (new entries — frost_bite thru oil_slick exist)
    "tornado_alley":        (spec_tornado_alley, paint_tornado_alley),
    "volcanic_glass":       (spec_volcanic_glass, paint_volcanic_glass),
    "frozen_lake":          (spec_frozen_lake, paint_frozen_lake),
    "desert_mirage":        (spec_desert_mirage, paint_desert_mirage),
    "ocean_floor":          (spec_ocean_floor, paint_ocean_floor),
    "meteor_shower":        (spec_meteor_shower, paint_meteor_shower),
    # Group 8: Dark & Gothic (new entries — worn_chrome, rust, weathered_paint exist)
    "voodoo":               (spec_voodoo, paint_voodoo),
    "reaper":               (spec_reaper, paint_reaper),
    "possessed":            (spec_possessed, paint_possessed),
    "wraith":               (spec_wraith, paint_wraith),
    "cursed":               (spec_cursed, paint_cursed),
    "eclipse":              (spec_eclipse, paint_eclipse),
    "nightmare":            (spec_nightmare, paint_nightmare),
})

EXPANSION_MONOLITHICS.update({
    # Group 9: Luxury & Exotic (new entries — galaxy exists)
    "black_diamond":        (spec_black_diamond, paint_black_diamond),
    "liquid_gold":          (spec_liquid_gold, paint_liquid_gold),
    "silk_road":            (spec_silk_road, paint_silk_road),
    "venetian_glass":       (spec_venetian_glass, paint_venetian_glass),
    "mother_of_pearl":      (spec_mother_of_pearl, paint_mother_of_pearl),
    "sapphire":             (spec_sapphire, paint_sapphire),
    "ruby":                 (spec_ruby, paint_ruby),
    "alexandrite":          (spec_alexandrite, paint_alexandrite),
    "stained_glass":        (spec_stained_glass, paint_stained_glass),
    "champagne_toast":      (spec_champagne_toast, paint_champagne_toast),
    "velvet_crush":         (spec_velvet_crush, paint_velvet_crush),
    # Group 10: Neon & Glow (new entries)
    "neon_vegas":           (spec_neon_vegas, paint_neon_vegas),
    "laser_grid":           (spec_laser_grid, paint_laser_grid),
    "plasma_globe":         (spec_plasma_globe, paint_plasma_globe),
    "firefly":              (spec_firefly, paint_firefly),
    "led_matrix":           (spec_led_matrix, paint_led_matrix),
    "cyber_punk":           (spec_cyberpunk, paint_cyberpunk),
    # Group 11: Texture & Surface (all new)
    "crocodile_leather":    (spec_croc_leather, paint_croc_leather),
    "hammered_copper":      (spec_hammered_copper, paint_hammered_copper),
    "brushed_steel_dark":   (spec_dark_brushed_steel, paint_dark_brushed_steel),
    "etched_metal":         (spec_etched_metal, paint_etched_metal),
    "sandstone":            (spec_sandstone, paint_sandstone),
    "petrified_wood":       (spec_petrified_wood, paint_petrified_wood),
    "forged_iron":          (spec_forged_iron, paint_forged_iron),
    "acid_etched_glass":    (spec_acid_etched_glass, paint_acid_etched_glass),
    "concrete":             (spec_concrete, paint_concrete),
    "cast_iron":            (spec_cast_iron, paint_cast_iron),
})


EXPANSION_MONOLITHICS.update({
    # Group 12: Vintage & Retro
    "barn_find":            (spec_barn_find, paint_barn_find),
    "patina_truck":         (spec_patina_truck, paint_patina_truck),
    "hot_rod_flames":       (spec_hot_rod_flames, paint_hot_rod_flames),
    "woodie_wagon":         (spec_woodie_wagon, paint_woodie_wagon),
    "drive_in":             (spec_drive_in, paint_drive_in),
    "muscle_car_stripe":    (spec_muscle_car_stripe, paint_muscle_car_stripe),
    "pin_up":               (spec_pin_up, paint_pin_up),
    "vinyl_record":         (spec_vinyl_record, paint_vinyl_record),
    # Group 13: Surreal & Fantasy
    "portal":               (spec_portal, paint_portal),
    "time_warp":            (spec_time_warp, paint_time_warp),
    "antimatter":           (spec_antimatter, paint_antimatter),
    "singularity":          (spec_singularity, paint_singularity),
    "dreamscape":           (spec_dreamscape, paint_dreamscape),
    "acid_trip":            (spec_acid_trip, paint_acid_trip),
    "mirage":               (spec_mirage, paint_mirage),
    "fourth_dimension":     (spec_fourth_dimension, paint_fourth_dimension),
    "glitch_reality":       (spec_glitch_reality, paint_glitch_reality),
    "phantom_zone":         (spec_phantom_zone, paint_phantom_zone),
})
EXPANSION_MONOLITHICS.update({
    # Group 14: SHOKK Series
    "shokk_ekg":            (spec_shokk_ekg, paint_shokk_ekg),
    "shokk_defib":          (spec_shokk_defib, paint_shokk_defib),
    "shokk_overload":       (spec_shokk_overload, paint_shokk_overload),
    "shokk_blackout":       (spec_shokk_blackout, paint_shokk_blackout),
    "shokk_resurrection":   (spec_shokk_resurrection, paint_shokk_resurrection),
    "shokk_voltage":        (spec_shokk_voltage, paint_shokk_voltage),
    "shokk_flatline":       (spec_shokk_flatline, paint_shokk_flatline),
    "shokk_adrenaline":     (spec_shokk_adrenaline, paint_shokk_adrenaline),
    "shokk_aftermath":      (spec_shokk_aftermath, paint_shokk_aftermath),
    "shokk_unleashed":      (spec_shokk_unleashed, paint_shokk_unleashed),
    # Group 15: One-of-a-Kind
    "shokk_lafleur":        (spec_lafleur, paint_lafleur),
    "shokk_affliction":     (spec_affliction, paint_affliction),
    "shokk_samurai":        (spec_samurai, paint_samurai),
    "shokk_dia_de_muertos": (spec_dia_de_muertos, paint_dia_de_muertos),
    "shokk_northern_soul":  (spec_northern_soul, paint_northern_soul),
})


# =============================================================================
# INTEGRATION API
# =============================================================================
# Called by shokker_engine_v2.py to merge expansion entries into the main registries.
# Resolves string-based paint_fn references to actual engine function objects.


# --- 24K+ ARSENAL: Missing Monolithic Registry Entries ---
EXPANSION_MONOLITHICS.update({
    # Chameleon Classic (5 new)
    "chameleon_aurora":  (spec_chameleon_aurora, paint_chameleon_aurora),
    "chameleon_fire":    (spec_chameleon_fire, paint_chameleon_fire),
    "chameleon_frost":   (spec_chameleon_frost, paint_chameleon_frost),
    "chameleon_galaxy":  (spec_chameleon_galaxy, paint_chameleon_galaxy),
    "chameleon_neon":    (spec_chameleon_neon, paint_chameleon_neon),
    # Color Shift Adaptive (7 new)
    "cs_chrome_shift":   (spec_cs_chrome_shift, paint_cs_chrome_shift),
    "cs_earth":          (spec_cs_earth, paint_cs_earth),
    "cs_monochrome":     (spec_cs_monochrome, paint_cs_monochrome),
    "cs_neon_shift":     (spec_cs_neon_shift, paint_cs_neon_shift),
    "cs_ocean_shift":    (spec_cs_ocean_shift, paint_cs_ocean_shift),
    "cs_prism_shift":    (spec_cs_prism_shift, paint_cs_prism_shift),
    "cs_vivid":          (spec_cs_vivid, paint_cs_vivid),
    # Color Shift Preset (5 new)
    "cs_candy_paint":    (spec_cs_candy_paint, paint_cs_candy_paint),
    "cs_dark_flame":     (spec_cs_dark_flame, paint_cs_dark_flame),
    "cs_gold_rush":      (spec_cs_gold_rush, paint_cs_gold_rush),
    "cs_oilslick":       (spec_cs_oilslick, paint_cs_oilslick),
    "cs_rose_gold_shift":(spec_cs_rose_gold_shift, paint_cs_rose_gold_shift),
    # Prizm Series (4 new)
    "prizm_cosmos":      (spec_prizm_cosmos, paint_prizm_cosmos),
    "prizm_dark_matter": (spec_prizm_dark_matter, paint_prizm_dark_matter),
    "prizm_fire_ice":    (spec_prizm_fire_ice, paint_prizm_fire_ice),
    "prizm_spectrum":    (spec_prizm_spectrum, paint_prizm_spectrum),
})
EXPANSION_MONOLITHICS.update({
    # Effect & Visual (13 new)
    "chromatic_aberration": (spec_chromatic_aberration, paint_chromatic_aberration),
    "crt_scanline":      (spec_crt_scanline, paint_crt_scanline),
    "datamosh":          (spec_datamosh, paint_datamosh),
    "embossed":          (spec_embossed, paint_embossed),
    "film_burn":         (spec_film_burn, paint_film_burn),
    "fish_eye":          (spec_fish_eye, paint_fish_eye),
    "halftone":          (spec_halftone, paint_halftone),
    "kaleidoscope":      (spec_kaleidoscope, paint_kaleidoscope),
    "long_exposure":     (spec_long_exposure, paint_long_exposure),
    "negative":          (spec_negative, paint_negative),
    "parallax":          (spec_parallax, paint_parallax),
    "refraction":        (spec_refraction, paint_refraction),
    "solarization":      (spec_solarization, paint_solarization),
    # Racing Legend (10 new)
    "burnout_zone":      (spec_burnout_zone, paint_burnout_zone),
    "chicane_blur":      (spec_chicane_blur, paint_chicane_blur),
    "cool_down":         (spec_cool_down, paint_cool_down),
    "drag_chute":        (spec_drag_chute, paint_drag_chute),
    "flag_wave":         (spec_flag_wave, paint_flag_wave),
    "grid_walk":         (spec_grid_walk, paint_grid_walk),
    "night_race":        (spec_night_race, paint_night_race),
    "pit_stop":          (spec_pit_stop, paint_pit_stop),
    "red_mist":          (spec_red_mist, paint_red_mist),
    "slipstream":        (spec_slipstream, paint_slipstream),
})
EXPANSION_MONOLITHICS.update({
    # Weather & Element (15 new)
    "acid_rain":         (spec_acid_rain, paint_acid_rain),
    "black_ice":         (spec_black_ice, paint_black_ice),
    "blizzard":          (spec_blizzard, paint_blizzard),
    "dew_drop":          (spec_dew_drop, paint_dew_drop),
    "dust_storm":        (spec_dust_storm, paint_dust_storm),
    "fog_bank":          (spec_fog_bank, paint_fog_bank),
    "hail_damage":       (spec_hail_damage, paint_hail_damage),
    "heat_wave":         (spec_heat_wave, paint_heat_wave),
    "hurricane":         (spec_hurricane, paint_hurricane),
    "lightning_strike":  (spec_lightning_strike, paint_lightning_strike),
    "magma_flow":        (spec_magma_flow, paint_magma_flow),
    "monsoon":           (spec_monsoon, paint_monsoon),
    "permafrost":        (spec_permafrost, paint_permafrost),
    "solar_wind":        (spec_solar_wind, paint_solar_wind),
    "tidal_wave":        (spec_tidal_wave, paint_tidal_wave),
    # Dark & Gothic (15 new)
    "banshee":           (spec_banshee, paint_banshee),
    "blood_oath":        (spec_blood_oath, paint_blood_oath),
    "catacombs":         (spec_catacombs, paint_catacombs),
    "dark_ritual":       (spec_dark_ritual, paint_dark_ritual),
    "death_metal":       (spec_death_metal, paint_death_metal),
    "demon_forge":       (spec_demon_forge, paint_demon_forge),
    "gargoyle":          (spec_gargoyle, paint_gargoyle),
    "graveyard":         (spec_graveyard, paint_graveyard),
    "haunted":           (spec_haunted, paint_haunted),
    "hellhound":         (spec_hellhound, paint_hellhound),
    "iron_maiden":       (spec_iron_maiden, paint_iron_maiden),
    "lich_king":         (spec_lich_king, paint_lich_king),
    "necrotic":          (spec_necrotic, paint_necrotic),
    "shadow_realm":      (spec_shadow_realm, paint_shadow_realm),
    "spectral":          (spec_spectral, paint_spectral),
})
EXPANSION_MONOLITHICS.update({
    # Neon & Glow (15 new)
    "aurora_glow":       (spec_aurora_glow, paint_aurora_glow),
    "blacklight_paint":  (spec_blacklight_paint, paint_blacklight_paint),
    "bioluminescent_wave":(spec_bioluminescent_wave, paint_bioluminescent_wave),
    "electric_arc":      (spec_electric_arc, paint_electric_arc),
    "fluorescent":       (spec_fluorescent, paint_fluorescent),
    "glow_stick":        (spec_glow_stick, paint_glow_stick),
    "laser_show":        (spec_laser_show, paint_laser_show),
    "magnesium_burn":    (spec_magnesium_burn, paint_magnesium_burn),
    "neon_sign":         (spec_neon_sign, paint_neon_sign),
    "phosphorescent":    (spec_phosphorescent, paint_phosphorescent),
    "rave":              (spec_rave, paint_rave),
    "sodium_lamp":       (spec_sodium_lamp, paint_sodium_lamp),
    "tesla_coil":        (spec_tesla_coil, paint_tesla_coil),
    "tracer_round":      (spec_tracer_round, paint_tracer_round),
    "welding_arc":       (spec_welding_arc, paint_welding_arc),
    # Texture & Surface (4 new)
    "granite":           (spec_granite, paint_granite),
    "obsidian_glass":    (spec_obsidian_glass, paint_obsidian_glass),
    "slate_tile":        (spec_slate_tile, paint_slate_tile),
    "volcanic_rock":     (spec_volcanic_rock, paint_volcanic_rock),
})
EXPANSION_MONOLITHICS.update({
    # Vintage & Retro (17 new)
    "art_deco_gold":     (spec_art_deco_gold, paint_art_deco_gold),
    "beat_up_truck":     (spec_beat_up_truck, paint_beat_up_truck),
    "classic_racing":    (spec_classic_racing, paint_classic_racing),
    "daguerreotype":     (spec_daguerreotype, paint_daguerreotype),
    "diner_chrome":      (spec_diner_chrome, paint_diner_chrome),
    "faded_glory":       (spec_faded_glory, paint_faded_glory),
    "grindhouse":        (spec_grindhouse, paint_grindhouse),
    "jukebox":           (spec_jukebox, paint_jukebox),
    "moonshine":         (spec_moonshine, paint_moonshine),
    "nascar_heritage":   (spec_nascar_heritage, paint_nascar_heritage),
    "nostalgia_drag":    (spec_nostalgia_drag, paint_nostalgia_drag),
    "old_school":        (spec_old_school, paint_old_school),
    "psychedelic":       (spec_psychedelic, paint_psychedelic),
    "sepia":             (spec_sepia, paint_sepia),
    "tin_type":          (spec_tin_type, paint_tin_type),
    "woodie":            (spec_woodie, paint_woodie),
    "zeppelin":          (spec_zeppelin, paint_zeppelin),
    # Surreal & Fantasy (14 new)
    "astral":            (spec_astral, paint_astral),
    "crystal_cave":      (spec_crystal_cave, paint_crystal_cave),
    "dark_fairy":        (spec_dark_fairy, paint_dark_fairy),
    "dragon_breath":     (spec_dragon_breath, paint_dragon_breath),
    "enchanted":         (spec_enchanted, paint_enchanted),
    "ethereal":          (spec_ethereal, paint_ethereal),
    "fractal_dimension": (spec_fractal_dimension, paint_fractal_dimension),
    "hallucination":     (spec_hallucination, paint_hallucination),
    "levitation":        (spec_levitation, paint_levitation),
    "multiverse":        (spec_multiverse, paint_multiverse),
    "nebula_core":       (spec_nebula_core, paint_nebula_core),
    "simulation":        (spec_simulation, paint_simulation),
    "tesseract":         (spec_tesseract, paint_tesseract),
    "void_walker":       (spec_void_walker, paint_void_walker),
    # Novelty & Fun (11 new)
    "aged_leather":      (spec_aged_leather, paint_aged_leather),
    "bark":              (spec_bark, paint_bark),
    "bone":              (spec_bone, paint_bone),
    "brick_wall":        (spec_brick_wall, paint_brick_wall),
    "burlap":            (spec_burlap, paint_burlap),
    "cork":              (spec_cork, paint_cork),
    "linen":             (spec_linen, paint_linen),
    "parchment":         (spec_parchment, paint_parchment),
    "stucco":            (spec_stucco, paint_stucco),
    "suede":             (spec_suede, paint_suede),
    "terra_cotta":       (spec_terra_cotta, paint_terra_cotta),
})

# Map of string shorthand -> engine function name for deferred resolution
_STRING_PAINT_FN_MAP = {
    "coarse_flake":   "paint_coarse_flake",
    "subtle_flake":   "paint_subtle_flake",
    "chrome_brighten": "paint_chrome_brighten",
    "ceramic_gloss":  "paint_ceramic_gloss",
    "fine_sparkle":   "paint_fine_sparkle",
}


def integrate_expansion(engine_module):
    """Merge all 24K Arsenal expansion entries into the engine's registries.

    Args:
        engine_module: The shokker_engine_v2 module object (already imported).
                       Used to resolve string paint_fn references and to access
                       BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY.

    Returns:
        dict with counts: {"bases": N, "patterns": N, "specials": N}
    """
    # --- Resolve string paint_fn references in EXPANSION_BASES ---
    for base_id, entry in EXPANSION_BASES.items():
        pfn = entry.get("paint_fn")
        if isinstance(pfn, str):
            engine_fn_name = _STRING_PAINT_FN_MAP.get(pfn)
            if engine_fn_name and hasattr(engine_module, engine_fn_name):
                entry["paint_fn"] = getattr(engine_module, engine_fn_name)
            else:
                # Fallback: try direct attribute lookup on engine
                if hasattr(engine_module, "paint_" + pfn):
                    entry["paint_fn"] = getattr(engine_module, "paint_" + pfn)
                else:
                    # Last resort: set to paint_none equivalent (no-op)
                    print(f"[24K] WARNING: Could not resolve paint_fn '{pfn}' for base '{base_id}' — using no-op")
                    entry["paint_fn"] = _paint_none_fallback

    # --- Wrap expansion texture_fn to match engine's 4-arg signature + dict return ---
    #
    # Engine calls: tex_fn(shape, mask, seed, sm) -> {"pattern_val": arr, "R_range": float, "M_range": float, "CC": int}
    # Expansion factories return: fn(shape, seed) -> raw numpy array (0-1 float)
    #
    # This wrapper bridges the gap so expansion patterns render correctly.
    # R_range/M_range are calibrated per paint_fn type to match the visual character
    # of native engine patterns (which range from -177 to +100 for R, -30 to +175 for M).
    #
    # Reference native ranges:
    #   diamond_plate: R=-132, M=60   |  dragon_scale: R=-157, M=135
    #   hex_mesh: R=-155, M=155       |  lightning: R=-177, M=175
    #   carbon_fiber: R=50, M=0       |  hammered: R=-112, M=95
    #   ripple: R=-85, M=100          |  plasma: R=-118, M=95

    # Map paint_fn instances to (R_range, M_range) tuned for visibility
    _PAINT_FN_MODULATION = {
        # Emboss: raised features = smoother + shinier (like diamond_plate, hammered)
        id(ppaint_emboss_light):   (-80.0,  60.0),
        id(ppaint_emboss_medium):  (-100.0, 80.0),
        id(ppaint_emboss_heavy):   (-120.0, 95.0),
        # Darken: recessed/shadow areas = rougher + less metallic
        id(ppaint_darken_light):   (60.0,  -20.0),
        id(ppaint_darken_medium):  (80.0,  -30.0),
        id(ppaint_darken_heavy):   (100.0, -40.0),
        # Contrast: strong visual difference (like hex_mesh, dragon_scale)
        id(ppaint_contrast_light):  (-100.0, 90.0),
        id(ppaint_contrast_medium): (-120.0, 110.0),
        # Glow: bright metallic sheen (like lightning, plasma)
        id(ppaint_glow_red):    (-130.0, 140.0),
        id(ppaint_glow_blue):   (-130.0, 140.0),
        id(ppaint_glow_green):  (-130.0, 140.0),
        id(ppaint_glow_gold):   (-130.0, 140.0),
        id(ppaint_glow_purple): (-130.0, 140.0),
        id(ppaint_glow_neon):   (-140.0, 150.0),
        # Tint: moderate modulation (like ripple)
        id(ppaint_tint_warm):  (-85.0, 70.0),
        id(ppaint_tint_cool):  (-85.0, 70.0),
        id(ppaint_tint_rust):  (-85.0, 70.0),
        id(ppaint_tint_toxic): (-85.0, 70.0),
        id(ppaint_tint_blood): (-85.0, 70.0),
    }
    # Strong universal fallback — visible on any base
    _DEFAULT_MODULATION = (-100.0, 80.0)

    def _wrap_texture_fn(original_fn, pattern_id, r_range, m_range):
        """Wrap an expansion texture_fn to match the engine's expected interface.

        CRITICAL FIX: Expansion texture functions use fixed pixel sizes for features
        (e.g., herringbone block_h=12). At swatch resolution (128x128) these are
        proportionally large and visible. At full render (2048x2048) they become
        microscopic and invisible on the car.

        Solution: Generate at a reference resolution and upscale to full size.
        This keeps features proportionally sized at any output resolution.
        """
        from PIL import Image as _PILImage
        # Generate ALL expansion textures at a fixed 1024 reference size, then
        # upscale to target resolution with NEAREST interpolation.  This ensures
        # hardcoded feature sizes (cell=48, period=8, etc.) remain proportionally
        # visible at any output resolution (2048, 4096, etc.) instead of becoming
        # microscopic.  NEAREST preserves the sharp geometric edges that define
        # most patterns (stripes, grids, cells, etc.).
        _REFERENCE_SIZE = 1024

        def wrapped(shape, mask, seed, sm):
            h, w = shape
            # Round up to nearest 32 to prevent internal crashes in texture fns
            # that use h//N*N patterns (repeat, tile, etc.) where N divides 32.
            _ALIGN = 32
            safe_h = ((h + _ALIGN - 1) // _ALIGN) * _ALIGN
            safe_w = ((w + _ALIGN - 1) // _ALIGN) * _ALIGN
            # Always generate at reference size and scale to target
            if max(safe_h, safe_w) > _REFERENCE_SIZE:
                scale_factor = max(safe_h, safe_w) / _REFERENCE_SIZE
                gen_h = max(32, ((int(safe_h / scale_factor) + _ALIGN - 1) // _ALIGN) * _ALIGN)
                gen_w = max(32, ((int(safe_w / scale_factor) + _ALIGN - 1) // _ALIGN) * _ALIGN)
                raw = original_fn((gen_h, gen_w), seed)
                # Upscale to exact target resolution (NEAREST for sharp edges)
                raw_u8 = (raw * 255).clip(0, 255).astype(np.uint8)
                raw_img = _PILImage.fromarray(raw_u8)
                raw_img = raw_img.resize((w, h), _PILImage.NEAREST)
                raw = np.array(raw_img).astype(np.float32) / 255.0
            else:
                raw = original_fn((safe_h, safe_w), seed)
                # Crop back to exact requested size
                raw = raw[:h, :w]
            return {
                "pattern_val": raw,
                "R_range": r_range,
                "M_range": m_range,
                "CC": None,  # None = use base CC (don't override)
            }
        wrapped.__name__ = f"wrapped_{pattern_id}"
        wrapped.__doc__ = f"Engine-compatible wrapper for expansion texture: {pattern_id}"
        return wrapped

    wrapped_count = 0
    for pat_id, pat_entry in EXPANSION_PATTERNS.items():
        tex_fn = pat_entry.get("texture_fn")
        if tex_fn is not None and callable(tex_fn):
            import inspect
            sig = inspect.signature(tex_fn)
            param_count = len(sig.parameters)
            if param_count < 4:
                # Look up R_range/M_range based on this pattern's paint_fn
                pfn = pat_entry.get("paint_fn")
                r_range, m_range = _PAINT_FN_MODULATION.get(
                    id(pfn), _DEFAULT_MODULATION)
                pat_entry["texture_fn"] = _wrap_texture_fn(
                    tex_fn, pat_id, r_range, m_range)
                wrapped_count += 1
    if wrapped_count:
        print(f"[24K Arsenal] Wrapped {wrapped_count} expansion texture_fn entries for engine compatibility")

    # --- Merge into engine registries ---
    engine_module.BASE_REGISTRY.update(EXPANSION_BASES)
    engine_module.PATTERN_REGISTRY.update(EXPANSION_PATTERNS)
    engine_module.MONOLITHIC_REGISTRY.update(EXPANSION_MONOLITHICS)

    counts = {
        "bases": len(EXPANSION_BASES),
        "patterns": len(EXPANSION_PATTERNS),
        "specials": len(EXPANSION_MONOLITHICS),
    }
    total = counts["bases"] + counts["patterns"] + counts["specials"]
    print(f"[24K Arsenal] Loaded {total} expansion entries: "
          f"{counts['bases']} bases, {counts['patterns']} patterns, {counts['specials']} specials")
    return counts


def _paint_none_fallback(paint, shape, mask, seed, pm, bb):
    """No-op paint function fallback for unresolved string references."""
    return paint


def get_expansion_group_map():
    """Return group metadata for UI organization.

    Returns dict with three keys: 'bases', 'patterns', 'specials'.
    Each maps group_name -> list of finish IDs in that group.
    """
    bases_groups = {
        "Foundation":           ["flat_matte", "dead_flat", "chalk", "eggshell", "semi_gloss"],
        "Metallic Standard":    ["metal_flake_base", "candy_apple", "midnight_pearl", "champagne", "pewter"],
        "Chrome & Mirror":      ["black_chrome", "blue_chrome", "red_chrome", "antique_chrome"],
        "Candy & Pearl":        ["candy_burgundy", "candy_emerald", "candy_cobalt", "tri_coat_pearl", "moonstone", "opal"],
        "Satin & Wrap":         ["matte_wrap", "color_flip_wrap", "chrome_wrap", "gloss_wrap", "textured_wrap", "brushed_wrap", "stealth_wrap"],
        "Industrial & Tactical":["mil_spec_od", "mil_spec_tan", "armor_plate", "submarine_black", "gunship_gray", "battleship_gray"],
        "Ceramic & Glass":      ["porcelain", "obsidian", "crystal_clear", "tempered_glass", "ceramic_matte", "enamel"],
        "Racing Heritage":      ["race_day_gloss", "stock_car_enamel", "sprint_car_chrome", "dirt_track_satin",
                                 "endurance_ceramic", "rally_mud", "drag_strip_gloss", "victory_lane",
                                 "barn_find", "rat_rod_primer", "pace_car_pearl", "heat_shield",
                                 "pit_lane_matte", "asphalt_grind", "checkered_chrome"],
        "Exotic Metal":         ["liquid_titanium", "tungsten", "platinum", "cobalt_metal"],
        "Weathered & Aged":     ["sun_baked", "salt_corroded", "desert_worn", "acid_rain", "oxidized_copper", "vintage_chrome"],
        "OEM Automotive":       ["factory_basecoat", "showroom_clear", "fleet_white", "taxi_yellow", "school_bus",
                                 "fire_engine", "ambulance_white", "police_black", "dealer_pearl"],
        "Carbon & Composite":   ["carbon_base", "kevlar_base", "fiberglass", "carbon_ceramic", "aramid",
                                 "graphene", "forged_composite", "hybrid_weave"],
        "Premium Luxury":       ["bentley_silver", "ferrari_rosso", "lamborghini_verde", "porsche_pts",
                                 "mclaren_orange", "bugatti_blue", "koenigsegg_clear", "pagani_tricolore", "maybach_two_tone"],
        "SHOKK Series":         ["shokk_pulse", "shokk_venom", "shokk_blood", "shokk_void", "shokk_static"],
        "Extreme & Experimental":["quantum_black", "neutron_star", "plasma_core", "dark_matter",
                                  "superconductor", "bioluminescent", "solar_panel", "holographic_base"],
    }

    patterns_groups = {
        "Grid & Geometric":     ["micro_grid", "hex_grid", "diamond_grid", "iso_grid", "octa_grid",
                                 "circuit_board", "maze_grid", "pixel_grid"],
        "Stripe & Line":        ["pin_stripe", "dual_stripe", "gradient_stripe", "barber_stripe",
                                 "racing_stripe", "hash_mark", "scan_line", "interference"],
        "Dot & Circle":         ["halftone_dot", "polka_dot", "bubble", "ring_dot",
                                 "scatter_dot", "gradient_dot", "target_ring", "ripple_dot"],
        "Wave & Flow":          ["sine_wave", "ocean_wave", "sound_wave", "heat_wave",
                                 "pulse_wave", "seismic_wave", "spiral_flow"],
        "Organic & Voronoi":    ["voronoi_cell", "cracked_earth", "cell_membrane", "coral",
                                 "lava_flow", "river_delta", "frost_pattern"],
        "Noise & Texture":      ["perlin_cloud", "marble_vein", "wood_grain", "granite",
                                 "sandpaper", "concrete_rough", "stucco"],
        "Radial & Burst":       ["sunburst", "starburst", "radar_sweep", "vortex",
                                 "explosion", "black_hole", "lighthouse"],
        "Symbol & Icon":        ["cross_grid", "fleur_grid", "yin_yang_grid", "star_field",
                                 "skull_array", "biohazard_tile", "arrow_field"],
        "Camo & Military":      ["digital_camo", "woodland_camo", "urban_camo", "arctic_camo",
                                 "desert_camo", "naval_camo", "dazzle_camo"],
        "Abstract & Art":       ["drip_paint", "splatter", "brush_stroke", "ink_wash",
                                 "graffiti_tag", "stencil_layer", "chalk_dust"],
        "Scale & Tile":         ["fish_scale", "dragon_scale", "roof_tile", "brick_wall",
                                 "cobblestone", "mosaic_tile", "chain_mail"],
        "Wire & Mesh":          ["chain_link", "barbed_wire", "wire_mesh", "cage_grid",
                                 "net_weave", "razor_mesh", "expanded_metal"],
        "Distortion & Glitch":  ["pixel_sort", "data_corrupt", "vhs_tracking", "signal_noise",
                                 "bit_crush", "screen_tear", "buffer_overflow"],
        "Racing & Speed":       ["speed_line", "tire_tread", "checkered_flag", "lap_counter",
                                 "draft_trail", "burnout_mark", "pit_mark"],
        "SHOKK Patterns":       ["shokk_pulse_pattern", "shokk_circuit", "shokk_fracture",
                                 "shokk_frequency", "shokk_grid", "shokk_static_pattern", "shokk_waveform"],
        "Flames":               ["classic_hotrod", "ghost_flames", "pinstripe_flames", "fire_lick",
                                 "inferno", "fireball", "hellfire", "wildfire", "flame_fade",
                                 "blue_flame", "torch_burn", "ember_scatter"],
        "Skate & Surf":         ["wave_curl", "ocean_foam", "palm_frond", "tiki_totem",
                                 "grip_tape", "halfpipe", "bamboo_stalk", "surf_stripe",
                                 "board_wax", "tropical_leaf", "rip_tide", "hibiscus"],
        "Cartoons":             ["retro_flower_power", "prehistoric_spot", "toon_stars", "toon_speed",
                                 "groovy_swirl", "zigzag_stripe", "toon_cloud", "retro_atom",
                                 "polka_pop", "toon_bones", "cartoon_plaid", "toon_lightning"],
        "Comics":               ["hero_burst", "web_pattern", "dark_knight_scales", "comic_halftone",
                                 "pow_burst", "cape_flow", "power_bolt", "shield_rings",
                                 "comic_panel", "power_aura", "villain_stripe", "gamma_pulse"],
        "Flames":               ["classic_hotrod", "ghost_flames", "pinstripe_flames", "fire_lick",
                                 "inferno", "fireball", "hellfire", "wildfire", "flame_fade",
                                 "blue_flame", "torch_burn", "ember_scatter"],
        "Skate & Surf":         ["wave_curl", "ocean_foam", "palm_frond", "tiki_totem",
                                 "grip_tape", "halfpipe", "bamboo_stalk", "surf_stripe",
                                 "board_wax", "tropical_leaf", "rip_tide", "hibiscus"],
        "Cartoons":             ["retro_flower_power", "prehistoric_spot", "toon_stars", "toon_speed",
                                 "groovy_swirl", "zigzag_stripe", "toon_cloud", "retro_atom",
                                 "polka_pop", "toon_bones", "cartoon_plaid", "toon_lightning"],
        "Comics":               ["hero_burst", "web_pattern", "dark_knight_scales", "comic_halftone",
                                 "pow_burst", "cape_flow", "power_bolt", "shield_rings",
                                 "comic_panel", "power_aura", "villain_stripe", "gamma_pulse"],
    }

    specials_groups = {
        "Chameleon Classic":    ["chameleon_mystic", "chameleon_dragon", "chameleon_scarab"],
        "Color Shift Adaptive": ["cs_thermal", "cs_mood", "cs_velocity"],
        "Color Shift Preset":   ["cs_aurora_borealis", "cs_lava_lamp", "cs_oil_spill"],
        "Prizm Series":         ["prizm_ultraviolet", "prizm_infrared"],
        "Effect & Visual":      ["holographic_foil", "thermochromic_pro", "glow_dark", "uv_reactive", "retro_reflective", "electrochromic"],
        "Racing Legend":        ["lemans_midnight", "daytona_sunrise", "monaco_gold", "nurburgring_green",
                                 "silverstone_silver", "talladega_thunder", "spa_rain", "bathurst_bronze",
                                 "indy_brick", "sebring_concrete", "laguna_blue", "suzuka_cherry",
                                 "brands_hatch", "watkins_glen", "last_lap"],
        "Weather & Element":    ["tornado_alley", "volcanic_glass", "frozen_lake", "desert_mirage", "ocean_floor", "meteor_shower"],
        "Dark & Gothic":        ["voodoo", "reaper", "possessed", "wraith", "cursed", "eclipse", "nightmare"],
        "Luxury & Exotic":      ["black_diamond", "liquid_gold", "silk_road", "venetian_glass", "mother_of_pearl",
                                 "sapphire", "ruby", "alexandrite", "stained_glass", "champagne_toast", "velvet_crush"],
        "Neon & Glow":          ["neon_vegas", "laser_grid", "plasma_globe", "firefly", "led_matrix", "cyber_punk"],
        "Texture & Surface":    ["crocodile_leather", "hammered_copper", "brushed_steel_dark", "etched_metal",
                                 "sandstone", "petrified_wood", "forged_iron", "acid_etched_glass", "concrete", "cast_iron"],
        "Vintage & Retro":      ["barn_find", "patina_truck", "hot_rod_flames", "woodie_wagon",
                                 "drive_in", "muscle_car_stripe", "pin_up", "vinyl_record"],
        "Surreal & Fantasy":    ["portal", "time_warp", "antimatter", "singularity", "dreamscape",
                                 "acid_trip", "mirage", "fourth_dimension", "glitch_reality", "phantom_zone"],
        "SHOKK Series":         ["shokk_ekg", "shokk_defib", "shokk_overload", "shokk_blackout", "shokk_resurrection",
                                 "shokk_voltage", "shokk_flatline", "shokk_adrenaline", "shokk_aftermath", "shokk_unleashed"],
        "One-of-a-Kind":        ["shokk_lafleur", "shokk_affliction", "shokk_samurai", "shokk_dia_de_muertos", "shokk_northern_soul"],
    }

    return {"bases": bases_groups, "patterns": patterns_groups, "specials": specials_groups}


def get_expansion_counts():
    """Quick count check for validation."""
    return {
        "bases": len(EXPANSION_BASES),
        "patterns": len(EXPANSION_PATTERNS),
        "specials": len(EXPANSION_MONOLITHICS),
        "total": len(EXPANSION_BASES) + len(EXPANSION_PATTERNS) + len(EXPANSION_MONOLITHICS),
    }
