"""
Shokker 24K Arsenal Expansion Module
=====================================
155 Bases x 155 Patterns + 155 Specials = 24,180 Finish Combinations

This module defines all NEW paint/texture/spec functions and registry entries
for the 24K Arsenal expansion. Imported by shokker_engine_v2.py.

Factory functions generate parametric variants to avoid code explosion.
"""

import numpy as np
from engine.spec_paint import (
    paint_tricolore_shift,
    paint_carbon_weave,
    paint_opal_fire,
    spec_absolute_zero,
    spec_armor_plate_v2,
    spec_battleship_gray_v2,
    spec_bioluminescent,
    spec_black_hole_accretion,
    spec_blackout_v2,
    spec_cerakote_v2,
    spec_dark_matter,
    spec_duracoat_v2,
    spec_gunship_gray_v2,
    spec_holographic_base,
    spec_martian_regolith,
    spec_mil_spec_od_v3,
    spec_mil_spec_tan_v2,
    spec_plasma_core,
    spec_powder_coat_v2,
    spec_quantum_black,
    spec_sandblasted_v2,
    spec_solar_panel,
    spec_submarine_black_v2,
)

# ======================================================================
# 2026 CATEGORY BASE OVERHAUL
# Exotic Metal, Extreme & Experimental, Industrial & Tactical, Metallic Standard
# OEM Automotive, Premium Luxury, Racing Heritage, Satin & Wrap, Weathered & Aged
# ======================================================================

def paint_liquid_metal_flow_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    from engine.core import _get_mgrid
    y, x = _get_mgrid(shape)
    flow = np.sin(x * 0.15 + np.sin(y * 0.08) * 3.0) * 0.5 + 0.5
    flow = np.clip((flow + 1.0) * 0.5, 0, 1).astype(np.float32)
    gray = paint.mean(axis=2, keepdims=True)
    paint = np.clip(paint * 0.5 + gray * 0.5 + flow[:,:,np.newaxis] * 0.15 * mask[:,:,np.newaxis] * pm, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05 * mask * pm, 0, 1)
    return np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)

def spec_exotic_metal(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    from engine.core import _multi_scale_noise, _get_mgrid
    y, x = _get_mgrid(shape)
    flow = np.sin(x * 0.15 + np.sin(y * 0.08) * 3.0) * 0.5 + 0.5
    grain = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed)
    M = np.clip(180 + flow * 75.0, 0, 255).astype(np.float32)
    R = np.clip(5 + grain * 25.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 16.0, dtype=np.float32)  # CC=16 exotic metal gloss (was 0=mirror)

def paint_tungsten_heavy(paint, shape, mask, seed, pm, bb):
    from engine.core import _multi_scale_noise
    gray = paint.mean(axis=2, keepdims=True)
    paint[:,:,0] = np.clip(paint[:,:,0] * 0.6 + gray[:,:,0] * 0.2, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * 0.6 + gray[:,:,0] * 0.2, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * 0.6 + gray[:,:,0] * 0.35 + 0.05*pm*mask, 0, 1)
    flake = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed)
    return np.clip(paint + flake[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis] + bb * 0.3, 0, 1)

def paint_oem_metallic_v2(paint, shape, mask, seed, pm, bb):
    from engine.core import _multi_scale_noise
    flake1 = _multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+1)
    flake2 = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed+5)
    pearl = np.clip((flake1 * 0.7 + flake2 * 0.3), 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + pearl * 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + pearl * 0.08 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + pearl * 0.12 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.5, 0, 1)

def spec_oem_automotive(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    peel = _multi_scale_noise(shape, [16, 32], [0.7, 0.3], seed)
    M = np.clip(30 + peel * 10.0, 0, 255).astype(np.float32)
    R = np.clip(45 + peel * 20.0, 0, 255).astype(np.float32)
    CC = np.clip(32 - peel * 16.0, 16, 255).astype(np.float32)
    return M, R, CC

def paint_mil_spec_od_v2(paint, shape, mask, seed, pm, bb):
    from engine.core import _multi_scale_noise
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * 0.4 + gray * 0.4
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.15*pm*mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.16*pm*mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05*pm*mask, 0, 1)
    grime = _multi_scale_noise(shape, [8, 16], [0.6, 0.4], seed)
    paint = np.clip(paint - grime[:,:,np.newaxis]*0.05*pm*mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.2, 0, 1)

def spec_industrial_tactical(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    grit = _multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed)
    M = np.clip(5 + grit * 40.0, 0, 255).astype(np.float32)
    R = np.clip(170 + grit * 85.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 180.0, dtype=np.float32)  # CC=180 tactical dull (was 0=mirror)

def paint_matte_wrap_v2(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    from scipy.ndimage import gaussian_filter
    smoothed = gaussian_filter(paint, sigma=[2, 2, 0])
    blend = pm * mask[:,:,np.newaxis]
    paint = paint * (1.0 - blend * 0.8) + smoothed * blend * 0.8
    return np.clip(paint + bb * 0.15 * blend, 0, 1)

def spec_satin_wrap(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    ripple = _multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed)
    M = np.clip(10 + ripple * 5.0, 0, 255).astype(np.float32)
    R = np.clip(120 + ripple * 20.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 120.0, dtype=np.float32)  # CC=120 satin sheen (was 0=mirror)

def paint_sun_fade_v2(paint, shape, mask, seed, pm, bb):
    from engine.core import _multi_scale_noise
    damage = _multi_scale_noise(shape, [16,32,64], [0.4, 0.4, 0.2], seed)
    paint = np.clip(paint + damage[:,:,np.newaxis]*0.15*mask[:,:,np.newaxis]*pm, 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    return np.clip(paint * 0.6 + gray * 0.4 + bb * 0.2, 0, 1)

def spec_weathered_aged(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    rot = _multi_scale_noise(shape, [8, 16, 32], [0.4, 0.3, 0.3], seed)
    M = np.where(rot > 0.6, 90.0, 15.0).astype(np.float32)
    R = np.where(rot > 0.6, 220.0, 90.0).astype(np.float32)
    CC = np.where(rot < 0.4, 24.0, 16.0).astype(np.float32)
    return M, R, CC

def paint_race_day_gloss_v2(paint, shape, mask, seed, pm, bb):
    from engine.core import _multi_scale_noise
    paint = np.clip(paint * 1.1, 0, 1)
    dust = _multi_scale_noise(shape, [2,4,8], [0.5, 0.3, 0.2], seed+1)
    dust_mask = np.where(dust > 0.8, 1, 0).astype(np.float32)
    paint = np.clip(paint - dust_mask[:,:,np.newaxis]*0.3*mask[:,:,np.newaxis]*pm, 0, 1)
    return np.clip(paint + bb * 0.7, 0, 1)

def spec_racing_heritage(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    scuff = _multi_scale_noise(shape, [2, 4, 8], [0.4, 0.4, 0.2], seed)
    M = np.clip(100 - scuff * 80.0, 0, 255).astype(np.float32)
    R = np.clip(15 + scuff * 200.0, 0, 255).astype(np.float32)
    CC = np.clip(32 - scuff * 32.0, 16, 255).astype(np.float32)
    return M, R, CC

def paint_quantum_black_v2(paint, shape, mask, seed, pm, bb):
    from engine.core import _multi_scale_noise
    paint = np.clip(paint * 0.02, 0, 1) 
    flux = _multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed)
    glow = np.where(flux > 0.95, 1, 0).astype(np.float32)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.4 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.05, 0, 1)

def spec_extreme_experimental(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    void = _multi_scale_noise(shape, [1, 2, 4], [0.33, 0.33, 0.34], seed+99)
    M = np.where(void > 0.8, 255.0, 0.0).astype(np.float32)
    R = np.where(void > 0.8, 0.0, 255.0).astype(np.float32)
    CC = np.where(void > 0.95, 255.0, 16.0).astype(np.float32)
    return M, R, CC

def paint_bentley_silver_v2(paint, shape, mask, seed, pm, bb):
    if pm == 0.0:
        return paint
    from engine.core import _multi_scale_noise
    blend = pm * mask
    gray = paint.mean(axis=2, keepdims=True)
    target = gray * 0.10 + 0.90
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * 0.5) + target[:,:,0] * blend * 0.5
    flake = _multi_scale_noise(shape, [1,2], [0.7,0.3], seed)
    return np.clip(paint + flake[:,:,np.newaxis]*0.05*blend[:,:,np.newaxis] + bb*0.8*blend[:,:,np.newaxis], 0, 1)

def spec_premium_luxury(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    flake = _multi_scale_noise(shape, [1, 2], [0.8, 0.2], seed)
    M = np.clip(180 + flake * 75.0, 0, 255).astype(np.float32)
    R = np.clip(5 + flake * 5.0, 0, 255).astype(np.float32)
    CC = np.full(shape, 16.0, dtype=np.float32)  # CC=16 luxury high gloss (was 255=dead flat)
    return M, R, CC

def spec_metallic_standard(shape, mask, seed, sm):
    from engine.core import _multi_scale_noise
    flake = _multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+1)
    M = np.clip(120 + flake * 80.0, 0, 255).astype(np.float32)
    R = np.clip(30 - flake * 15.0, 0, 255).astype(np.float32)
    CC = np.full(shape, 24.0, dtype=np.float32)
    return M, R, CC


from PIL import Image


# ================================================================
# FACTORY HELPERS - Generate paint/texture/spec functions from params
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
        sh, sw = max(1, int(h) // scale), max(1, int(w) // scale)
        small = rng.randn(sh, sw).astype(np.float32)
        img = Image.fromarray(((small - small.min()) / (small.max() - small.min() + 1e-8) * 255).clip(0, 255).astype(np.uint8))
        # Cast w, h to Python ints to prevent PIL throwing [Errno 22] Invalid argument on Windows with numpy ints
        img = img.resize((int(w), int(h)), Image.BILINEAR)
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
    """Factory: candy coat - deep transparent tint with visible sparkle. warmth: -1=cool, 0=neutral, 1=warm"""
    def fn(paint, shape, mask, seed, pm, bb):
        # Strong candy saturation deepening
        gray = paint.mean(axis=2, keepdims=True)
        sat_boost = 0.45 * pm
        paint = np.clip(paint + (paint - gray) * sat_boost * mask[:,:,np.newaxis], 0, 1)
        # Candy darkening (transparent color over base)
        paint = np.clip(paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]), 0, 1)
        # Warm/cool color shift (much stronger)
        if warmth > 0:
            paint[:,:,0] = np.clip(paint[:,:,0] + 0.15 * warmth * pm * mask, 0, 1)
            paint[:,:,2] = np.clip(paint[:,:,2] - 0.10 * warmth * pm * mask, 0, 1)
        elif warmth < 0:
            paint[:,:,2] = np.clip(paint[:,:,2] + 0.15 * abs(warmth) * pm * mask, 0, 1)
            paint[:,:,0] = np.clip(paint[:,:,0] - 0.10 * abs(warmth) * pm * mask, 0, 1)
        # Visible sparkle
        rng = np.random.RandomState(seed + 77)
        sparkle = rng.random(shape).astype(np.float32)
        sparkle = np.where(sparkle > 0.90, (sparkle - 0.90) * 2.5 * pm, 0)
        paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
        paint = np.clip(paint + bb * 0.8 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.06):
    """Factory: luxury fine sparkle with subtle depth."""
    def fn(paint, shape, mask, seed, pm, bb):
        flake = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 50)
        rng = np.random.RandomState(seed + 77)
        sparkle = rng.random(shape).astype(np.float32)
        # Boost the sparkle intensity so it's visible, scaled by pm multiply by 2.0
        sparkle = np.where(sparkle > sparkle_density, (sparkle - sparkle_density) * sparkle_strength * 25.0 * pm, 0)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.03 * pm * mask + sparkle * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_tactical_variant_fn(noise_strength=0.03):
    """Factory: flat tactical/military coating with micro-texture."""
    def fn(paint, shape, mask, seed, pm, bb):
        # Extremely subtle noise, scaled back drastically per user feedback
        noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 200)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + noise * (noise_strength * 0.3) * pm * mask, 0, 1)
        return paint
    return fn

def make_wrap_texture_fn(grain_strength=0.04):
    """Factory: vinyl wrap micro-texture - slight orange-peel or grain."""
    def fn(paint, shape, mask, seed, pm, bb):
        grain = _multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + 300)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + grain * grain_strength * pm * mask, 0, 1)
        return paint
    return fn

def make_aged_fn(fade_strength=0.08, roughen=0.04):
    """Factory: aged/weathered paint - organic desaturation + noise."""
    def fn(paint, shape, mask, seed, pm, bb):
        gray = paint.mean(axis=2, keepdims=True)
        # Use noise to create patchy fading rather than a flat, solid black desaturation
        # Noise is roughly -2.5 to 2.5. Scale it down so it ranges ~0 to 1
        fade_mask = np.clip(_multi_scale_noise(shape, [8, 16], [0.6, 0.4], seed + 400) * 0.2 + 0.5, 0, 1)
        desat = fade_strength * pm * fade_mask * mask
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat) + gray[:,:,0] * desat, 0, 1)
        
        # Subtle roughness - reduce the intensity so it's not overly flaky
        noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 401)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + noise * (roughen * 0.25) * pm * mask, 0, 1)
        return paint
    return fn

def make_vivid_depth_fn(sat_boost=0.12, depth_darken=0.05):
    """Factory: vivid deep coat - saturates + deepens for luxury colors."""
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

def make_glow_fn(glow_color, glow_strength=0.18):
    """Factory: TRUE NEON GLOW with spatial variation.
    v4: Uses mask-edge glow + noise blobs for actual glowing-material look.
    Old v1-v3 either tinted imperceptibly or did flat color LERP."""
    def fn(paint, shape, mask, seed, pm, bb):
        from PIL import Image as _Img, ImageFilter as _Filt
        h, w = shape

        # === MASK EDGE GLOW: bright glow along zone boundaries ===
        mask_u8 = (mask * 255).astype(np.uint8)
        mask_img = _Img.fromarray(mask_u8)
        edges_raw = np.array(mask_img.filter(_Filt.FIND_EDGES)).astype(np.float32) / 255.0
        # Dilate for wider glow band
        edge_bright = np.clip(edges_raw * 3, 0, 1)
        edge_img = _Img.fromarray((edge_bright * 255).astype(np.uint8))
        edge_img = edge_img.filter(_Filt.GaussianBlur(radius=max(2, min(h, w) // 100)))
        mask_edges = np.array(edge_img).astype(np.float32) / 255.0

        # === NOISE GLOW BLOBS: large-scale organic glow variation ===
        noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 600)
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
        glow_blobs = np.clip((noise - 0.25) * 2.5, 0, 1)

        # === COMBINE: edges + blobs ===
        glow_field = np.clip(mask_edges * 1.5 + glow_blobs * 0.7, 0, 1)
        strength = min(0.70, glow_strength * 3.0) * pm
        glow = glow_field * strength * mask

        # Apply glow color with spatial variation
        for c in range(3):
            paint[:,:,c] = np.clip(
                paint[:,:,c] * (1 - glow * 0.5) + glow_color[c] * glow,
                0, 1)

        # === EMISSION BRIGHTENING where glow is strong ===
        bright = glow_field * glow_strength * 0.6 * pm * mask
        paint = np.clip(paint + bright[:,:,np.newaxis], 0, 1)

        # === HOT CORE: white-hot where glow peaks ===
        hot = np.clip((glow_field - 0.5) * 3.0, 0, 1) * pm * mask * 0.15
        paint = np.clip(paint + hot[:,:,np.newaxis], 0, 1)
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
def paint_black_chrome_tint(paint, shape, mask, seed, pm, bb):
    """Black chrome - deep darkening toward near-black with reflective surface highlights."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Push strongly toward very dark (black chrome is near-black)
    target = gray * 0.08
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask
    # Sharp bright reflection highlights
    rng = np.random.RandomState(seed + 700)
    highlight = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 701)
    bright = np.clip(highlight, 0.3, 1.0) * 0.06 * blend
    paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blue_chrome_tint(paint, shape, mask, seed, pm, bb):
    """Blue chrome - strong blue tint with bright caustic reflections."""
    h, w = shape
    blend = 0.20 * pm
    # Strong blue tint over chrome
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.6) + 0.40 * blend * mask * 0.6, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.5) + 0.55 * blend * mask * 0.5, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.4) + 0.95 * blend * mask * 0.4, 0, 1)
    # Chrome caustic reflections
    caustic = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 710)
    paint = np.clip(paint + caustic[:,:,np.newaxis] * 0.06 * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_red_chrome_tint(paint, shape, mask, seed, pm, bb):
    """Red chrome - strong red-copper tint with warm metallic highlights."""
    h, w = shape
    blend = 0.20 * pm
    # Strong red tint
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.4) + 0.95 * blend * mask * 0.4, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.6) + 0.18 * blend * mask * 0.6, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.6) + 0.12 * blend * mask * 0.6, 0, 1)
    # Warm metallic highlight
    caustic = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 720)
    warm = np.clip(caustic, 0.2, 1.0) * 0.05 * blend
    paint[:,:,0] = np.clip(paint[:,:,0] + warm * mask * 1.2, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + warm * mask * 0.6, 0, 1)
    return paint

def paint_antique_patina(paint, shape, mask, seed, pm, bb):
    """Antique chrome - heavy desaturation + warm yellowing + irregular patina spots."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Desaturate strongly
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask * 0.5) + gray[:,:,0] * blend * mask * 0.5
    # Warm yellowing (aged chrome turns slightly yellow)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.04 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.02 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.02 * blend * mask, 0, 1)
    # Irregular patina spots
    rng = np.random.RandomState(seed + 730)
    patina = rng.random((h, w)).astype(np.float32)
    spots = np.where(patina > 0.85, (patina - 0.85) * 3.0, 0).astype(np.float32)
    paint[:,:,1] = np.clip(paint[:,:,1] - spots * 0.08 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - spots * 0.04 * blend * mask, 0, 1)
    return paint

# --- Candy Variants ---
paint_candy_depth = make_candy_tint_fn(warmth=0.0)
paint_candy_warm = make_candy_tint_fn(warmth=0.8)
paint_candy_cool = make_candy_tint_fn(warmth=-0.8)

# --- Pearl / Sparkle Variants ---
paint_dark_sparkle = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.04)
paint_warm_shimmer = make_luxury_sparkle_fn(sparkle_density=0.96, sparkle_strength=0.05)
def paint_tri_coat_sparkle(paint, shape, mask, seed, pm, bb):
    """Tri-coat pearl - strong saturation + dense pearlescent sparkle + directional sheen."""
    h, w = shape
    # Strong saturation boost (pearl mid-coat)
    gray = paint.mean(axis=2, keepdims=True)
    paint = np.clip(paint + (paint - gray) * 0.35 * pm * mask[:,:,np.newaxis], 0, 1)
    # Dense pearlescent sparkle
    rng = np.random.RandomState(seed + 900)
    sparkle = rng.random((h, w)).astype(np.float32)
    sparkle_bright = np.where(sparkle > 0.88, (sparkle - 0.88) * 2.5 * pm, 0.0)
    # Pearl iridescence (slight RGB separation in sparkle)
    paint[:,:,0] = np.clip(paint[:,:,0] + sparkle_bright * mask * 1.0, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + np.roll(sparkle_bright, 1, axis=1) * mask * 0.95, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.roll(sparkle_bright, -1, axis=1) * mask * 1.05, 0, 1)
    # Directional pearl sheen band
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    sheen = np.clip(1.0 - np.abs(y - 0.35) * 4, 0, 1) * 0.08 * pm
    paint = np.clip(paint + sheen[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)
    return paint
paint_dealer_sparkle = make_luxury_sparkle_fn(sparkle_density=0.93, sparkle_strength=0.12)
paint_luxury_sparkle = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)
paint_confetti_sparkle = make_luxury_sparkle_fn(sparkle_density=0.85, sparkle_strength=0.50)
paint_crystal_sparkle = make_luxury_sparkle_fn(sparkle_density=0.98, sparkle_strength=0.04)

# --- Wrap Variants ---
def paint_matte_wrap_tension(paint, shape, mask, seed, pm, bb):
    """Dead flat wrap vinyl - zero reflection with a slight matte milkiness."""
    h, w = shape
    # 1. Kill specular reflection entirely
    paint = paint * (1 - 0.95 * pm * mask[:,:,np.newaxis])
    # 2. Add a very slight desaturated milkiness to represent thick vinyl vs bare paint
    gray = paint.mean(axis=2, keepdims=True)
    for c in range(3):
         paint[:,:,c] = np.clip(paint[:,:,c] * (1 - 0.2 * pm * mask) + gray[:,:,0] * 0.2 * pm * mask, 0, 1)
         paint[:,:,c] = np.clip(paint[:,:,c] + 0.03 * pm * mask, 0, 1) # vinyl thickness
    return paint

def paint_gloss_wrap_sheet(paint, shape, mask, seed, pm, bb):
    """High-gloss vinyl film - subtle plasticity to color and thick clearcoat."""
    h, w = shape
    from PIL import Image as _Img, ImageFilter as _Filt

    # 1. Slight plastic softening (blur) to underlying color
    paint_img = _Img.fromarray((paint * 255).astype(np.uint8))
    blurred = np.array(paint_img.filter(_Filt.GaussianBlur(radius=1.0))).astype(np.float32) / 255.0
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * 0.7 + blurred[:,:,c] * 0.3 * pm * mask, 0, 1)
    # 2. Standard thick gloss pass without global sweeping waves
    paint = np.clip(paint + bb * 0.85 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_stealth_absorb(paint, shape, mask, seed, pm, bb):
    """Ultra-matte stealth radar absorption - violently kills luminance and desaturates color."""
    h, w = shape
    # 1. Devour light (crush brightness)
    paint = paint * (1 - 0.80 * pm * mask[:,:,np.newaxis])
    # 2. Devour color (desaturate to neutral dark grey)
    gray = paint.mean(axis=2, keepdims=True)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - 0.9 * pm * mask) + gray[:,:,0] * 0.9 * pm * mask, 0, 1)
    # 3. Microscopic anechoic grid
    y, x = _get_mgrid(shape)
    grid = ((y % 4 < 2) & (x % 4 < 2)).astype(np.float32)
    grid_darken = 1.0 - (0.15 * pm * grid * mask)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * grid_darken, 0, 1)
    return paint

paint_wrap_texture = make_wrap_texture_fn(grain_strength=0.04)
paint_textured_wrap = make_wrap_texture_fn(grain_strength=0.07)
paint_brushed_wrap = make_wrap_texture_fn(grain_strength=0.05)
paint_chrome_wrap = make_chrome_tint_fn(0.88, 0.88, 0.90, blend=0.20)
def paint_stealth_flat(paint, shape, mask, seed, pm, bb):
    """Stealth/gunship - desaturated flat grey with radar-absorbing quality."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Strong desaturation toward neutral grey
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask * 0.5) + gray[:,:,0] * blend * mask * 0.5
    # Very fine micro-texture (RAM coating surface)
    rng = np.random.RandomState(seed + 500)
    micro = (rng.random((h, w)).astype(np.float32) - 0.5) * 0.04
    paint = np.clip(paint + micro[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Tactical / Military ---
def paint_armor_grain(paint, shape, mask, seed, pm, bb):
    """Armor plate - dark steel grey push + rolling mill directional marks."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    target = gray * 0.3 + 0.15
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask * 0.4) + target[:,:,0] * blend * mask * 0.4
    rng = np.random.RandomState(seed + 510)
    y, x = _get_mgrid(shape)
    marks = np.sin(y * 0.15 + rng.random(1)[0] * 100) * 0.5 + 0.5
    faint_marks = np.where(marks > 0.85, (marks - 0.85) * 4.0, 0).astype(np.float32) * 0.04
    paint = np.clip(paint + faint_marks[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    grain = (rng.random((h, w)).astype(np.float32) - 0.5) * 0.06
    paint = np.clip(paint + grain[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_rubber_texture(paint, shape, mask, seed, pm, bb):
    """Submarine hull - deep black rubbery coating with acoustic tile pattern."""
    h, w = shape
    blend = 0.20 * pm
    paint = paint * (1 - 0.7 * blend * mask[:,:,np.newaxis])
    y, x = _get_mgrid(shape)
    tile_size = 24
    tile_edge_h = (y % tile_size < 1).astype(np.float32)
    tile_edge_v = (x % tile_size < 1).astype(np.float32)
    tiles = np.maximum(tile_edge_h, tile_edge_v) * 0.03
    paint = np.clip(paint + tiles[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    rng = np.random.RandomState(seed + 520)
    micro = (rng.random((h, w)).astype(np.float32) - 0.5) * 0.03
    paint = np.clip(paint + micro[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint
def paint_crystal_sparkle(paint, shape, mask, seed, pm, bb):
    """Crystal clear - prismatic micro-sparkle with slight brightening."""
    blend = 0.20 * pm
    rng = np.random.RandomState(seed + 600)
    sparkle = rng.random(shape).astype(np.float32)
    bright_dots = np.where(sparkle > 0.92, (sparkle - 0.92) * 5.0, 0).astype(np.float32)
    # Prismatic color scatter
    paint[:,:,0] = np.clip(paint[:,:,0] + bright_dots * 0.12 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + bright_dots * 0.08 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + bright_dots * 0.15 * blend * mask, 0, 1)
    # Slight overall brightening (clear coat clarity)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint
def paint_naval_coat(paint, shape, mask, seed, pm, bb):
    """Battleship gray - blue-grey tint + salt-air micro-pitting."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    paint[:,:,0] = paint[:,:,0] * (1 - blend * mask * 0.3) + (gray[:,:,0] * 0.45) * blend * mask * 0.3
    paint[:,:,1] = paint[:,:,1] * (1 - blend * mask * 0.3) + (gray[:,:,0] * 0.48) * blend * mask * 0.3
    paint[:,:,2] = paint[:,:,2] * (1 - blend * mask * 0.25) + (gray[:,:,0] * 0.55) * blend * mask * 0.25
    rng = np.random.RandomState(seed + 530)
    pitting = rng.random((h, w)).astype(np.float32)
    pits = np.where(pitting > 0.92, (pitting - 0.92) * 6.0, 0).astype(np.float32) * 0.05
    paint = np.clip(paint - pits[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Ceramic & Glass ---
def paint_porcelain_smooth(paint, shape, mask, seed, pm, bb):
    """Porcelain - push toward bright white with slight cool blue tint."""
    blend = 0.20 * pm
    # Push toward porcelain white (slightly cool/blue)
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.4) + 0.90 * blend * mask * 0.4, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.4) + 0.91 * blend * mask * 0.4, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.4) + 0.95 * blend * mask * 0.4, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_obsidian_depth(paint, shape, mask, seed, pm, bb):
    """Obsidian volcanic glass - deep black with reflective surface depth."""
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    target = gray * 0.10  # Very dark
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask
    # Slight blue-purple sheen (obsidian has a slight color)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.03 * blend * mask, 0, 1)
    return paint

def paint_glass_clean(paint, shape, mask, seed, pm, bb):
    """Tempered glass - slight green tint (real tempered glass has iron-oxide green)."""
    if pm == 0.0:
        return paint
    blend = np.clip(pm * 0.15, 0, 0.6)
    # Slight green tint
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.1), 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.02 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.05), 0, 1)
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_ceramic_flat(paint, shape, mask, seed, pm, bb):
    """Ceramic matte - smooth, slightly desaturated, flat surface."""
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Desaturate partially (matte ceramic dampens color)
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask * 0.3) + gray[:,:,0] * blend * mask * 0.3
    # Fine micro-surface noise
    rng = np.random.RandomState(seed + 610)
    noise = (rng.random(shape).astype(np.float32) - 0.5) * 0.03
    paint = np.clip(paint + noise[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_enamel_coat(paint, shape, mask, seed, pm, bb):
    """Hard baked enamel - vivid color with deep glossy wet look."""
    blend = 0.20 * pm
    # Boost saturation (enamel has vivid deep color)
    gray = paint.mean(axis=2, keepdims=True)
    for c in range(3):
        diff = paint[:,:,c] - gray[:,:,0]
        paint[:,:,c] = np.clip(paint[:,:,c] + diff * 0.15 * blend * mask, 0, 1)
    # Slight darkening for depth
    paint = np.clip(paint * (1 - 0.05 * blend * mask[:,:,np.newaxis]), 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Racing Heritage ---

def paint_sprint_car_chrome(paint, shape, mask, seed, pm, bb):
    """Sprint car spun aluminum chrome - warped circular reflections from thin sheet metal."""
    h, w = shape
    # Brighten heavily to chrome base
    gray = paint.mean(axis=2, keepdims=True)
    target = gray * 0.15 + 0.85
    blend = 0.25 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask, 0, 1)
    
    # Warped circular spun reflection
    y, x = _get_mgrid(shape)
    cx, cy = w // 2, h // 2
    r = np.sqrt((x - cx)**2 + (y - cy)**2)
    spun = np.sin(r * 0.15) * 0.5 + 0.5
    spun = spun.astype(np.float32)
    # Warping variation
    warp = np.sin(x * 0.05 + y * 0.02) * 0.2
    spun = np.clip(spun + warp, 0, 1)
    
    # Apply as a warped reflection highlight
    highlight = spun * 0.15 * pm
    paint = np.clip(paint + highlight[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_drag_strip_gloss(paint, shape, mask, seed, pm, bb):
    """Ultra-polished quarter-mile show finish - exponent-sharpened deep mirror glaze."""
    h, w = shape
    # Compute gray from ORIGINAL paint (before modifications)
    gray = paint.mean(axis=2, keepdims=True)
    # Build saturation and shadow maps without in-place mutation
    result = paint.copy()
    for c in range(3):
        diff = paint[:,:,c] - gray[:,:,0]
        # Push saturation up slightly (small effect on white/desaturated paints, big on vivid)
        sat_boost = np.clip(paint[:,:,c] + diff * 0.25 * pm * mask, 0, 1)
        # Deepen shadows lightly - 0.92 not 0.8 so white stays white
        result[:,:,c] = np.clip(sat_boost * (1 - 0.08 * pm * mask), 0, 1)

    # Extremely bright, exponentiated localized specular glint
    glint = np.clip(_multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 900) * 0.5 + 0.5, 0, 1)
    sharp_glint = (glint ** 8).astype(np.float32)  # Extremely tight localized highlight
    result = np.clip(result + sharp_glint[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1)

    # Subtle clearcoat tint (spec map handles the real clearcoat)
    result = np.clip(result + bb * 0.25 * mask[:,:,np.newaxis], 0, 1)
    return result


def paint_dirt_track_sweep(paint, shape, mask, seed, pm, bb):
    """Slightly dusty satin from dirt track use - specific directional brown/tan dust sweeps."""
    h, w = shape
    # Base satin cut
    paint = np.clip(paint * (1 - 0.15 * pm * mask[:,:,np.newaxis]), 0, 1)
    # Directional dust sweep (lateral)
    rng = np.random.RandomState(seed + 412)
    y, x = _get_mgrid(shape)
    dust_sweep = _multi_scale_noise(shape, [12, 24], [0.6, 0.4], seed + 413)
    # Stretch horizontally
    dust_sweep = np.clip(dust_sweep + np.sin(x * 0.5) * 0.2, 0, 1)
    dust_color = np.array([0.65, 0.55, 0.45]) # Tan dirt
    dust_blend = 0.25 * pm * dust_sweep * mask
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - dust_blend) + dust_color[c] * dust_blend
    return paint

def paint_pace_car_pearl(paint, shape, mask, seed, pm, bb):
    """Official pace car triple-pearl coat - 3 distinct interference layers."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # Layer 1: Cool highlight (cyan-blue) based on X gradient
    l1 = (x / max(w, 1)) * 0.2 * pm
    # Layer 2: Warm highlight (gold-pink) based on Y gradient
    l2 = (1.0 - y / max(h, 1)) * 0.2 * pm
    # Layer 3: Central tight pop (pure white)
    cx, cy = w // 2, h // 2
    dist = np.sqrt((x - cx)**2 + (y - cy)**2) / max(w, h)
    l3 = np.clip(1.0 - dist * 2.0, 0, 1) * 0.15 * pm
    
    # Layer application
    paint[:,:,0] = np.clip(paint[:,:,0] + l2 * mask + l3 * mask, 0, 1) # Warm + pop
    paint[:,:,1] = np.clip(paint[:,:,1] + (l1 * 0.5 + l2 * 0.5) * mask + l3 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + l1 * mask + l3 * mask, 0, 1) # Cool + pop
    
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_barn_find_chalk(paint, shape, mask, seed, pm, bb):
    """Decades-old stored car faded paint - chalky oxidation breakdown."""
    h, w = shape
    # Fade unevenly toward off-white/grey, preserving some of the original color underneath
    # Noise is ~ -2.5 to 2.5. Multiply by 0.15 and add 0.5 to get a soft cloudy 0-1 map, not harsh cow print blocky noise.
    fade_noise = np.clip(_multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 450) * 0.15 + 0.5, 0, 1)
    fade_strength = 0.45 * pm * fade_noise * mask # Reduced from 0.6 to preserve color
    
    gray = paint.mean(axis=2, keepdims=True)
    for c in range(3):
        # Desaturate partially
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - 0.2*pm*mask) + gray[:,:,0] * 0.2*pm*mask, 0, 1)
        # Mix with chalky off-white where fade is strongest
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - fade_strength) + 0.85 * fade_strength, 0, 1)
        
    return paint

paint_show_polish = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)
paint_dirt_subtle = make_aged_fn(fade_strength=0.04, roughen=0.03)
paint_barn_aged = make_aged_fn(fade_strength=0.20, roughen=0.08)
paint_rat_rod_flat = make_aged_fn(fade_strength=0.15, roughen=0.10)
paint_pace_car_sheen = make_luxury_sparkle_fn(sparkle_density=0.96, sparkle_strength=0.06)
paint_pit_grime = make_aged_fn(fade_strength=0.06, roughen=0.05)
paint_asphalt_rough = make_tactical_variant_fn(noise_strength=0.07)
def paint_checker_polish(paint, shape, mask, seed, pm, bb):
    """Polished chrome finish with a large-scale geometric checkered reflection map."""
    h, w = shape
    
    # 1. Base chrome brightening 
    gray = paint.mean(axis=2, keepdims=True)
    target = gray * 0.15 + 0.85
    blend = 0.25 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask, 0, 1)
        
    # 2. Add subtle cool tint for chrome feel
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05 * pm * mask, 0, 1)
    
    # 3. Checkerboard Generation
    y, x = _get_mgrid(shape)
    
    # Set checker square size (scale relative to overall dimension for consistency)
    square_size = max(h, w) // 16  # Approx 16 squares across the longest dimension
    if square_size < 1: square_size = 1
    
    # Integer division to get grid coordinates, modulo 2 for alternating 0/1 pattern
    checker_map = ((x // square_size) + (y // square_size)) % 2
    checker_map = checker_map.astype(np.float32)
    
    # 4. Apply checker pattern as a subtle luminance drop mimicking a varied reflection map
    # We darken the "black" squares of the checkerboard by about 15%
    darken_factor = 1.0 - (0.15 * pm * checker_map * mask)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * darken_factor, 0, 1)
        
    # Base coat metallic sheen 
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Exotic Metal ---
def paint_liquid_metal_flow(paint, shape, mask, seed, pm, bb):
    """Liquid titanium - bright flowing molten metal with rippled caustics."""
    h, w = shape
    # Push toward bright silver-blue (titanium color)
    gray = paint.mean(axis=2, keepdims=True)
    target = gray * 0.15 + 0.75
    blend = 0.22 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask
    # Titanium slight blue tint
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.03 * pm * mask, 0, 1)
    # Rippled caustic flow pattern
    y, x = _get_mgrid(shape)
    flow = np.sin(x * 0.08 + y * 0.04 + np.sin(y * 0.06) * 3.0) * 0.5 + 0.5
    flow = flow.astype(np.float32)
    paint = np.clip(paint + flow[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    # Metallic flake + sparkle
    for c in range(3):
        flake = _multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.05 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dense_metal(paint, shape, mask, seed, pm, bb):
    """Tungsten - ultra-dense dark grey-blue heavy metal."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    # Dark grey-blue tungsten tint
    blend = 0.20 * pm
    target_r = gray * 0.28
    target_g = gray * 0.30
    target_b = gray * 0.35
    paint[:,:,0] = paint[:,:,0] * (1 - blend * mask) + target_r[:,:,0] * blend * mask
    paint[:,:,1] = paint[:,:,1] * (1 - blend * mask) + target_g[:,:,0] * blend * mask
    paint[:,:,2] = paint[:,:,2] * (1 - blend * mask) + target_b[:,:,0] * blend * mask
    # Fine metal grain texture + flake
    for c in range(3):
        flake = _multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17 + 800)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_platinum_sheen(paint, shape, mask, seed, pm, bb):
    """Platinum - bright white-silver metallic with subtle warm undertone."""
    h, w = shape
    # Push toward bright platinum white
    blend = 0.20 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask * 0.5) + 0.90 * blend * mask * 0.5
    # Subtle warm undertone
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.02 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.01 * pm * mask, 0, 1)
    # Metallic flake + sparkle
    for c in range(3):
        flake = _multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17 + 810)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.05 * pm * mask, 0, 1)
    rng = np.random.RandomState(seed + 811)
    sparkle = rng.random((h, w)).astype(np.float32)
    sparkle = np.where(sparkle > 0.96, sparkle * 0.10 * pm, 0).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + sparkle * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_cobalt_tint(paint, shape, mask, seed, pm, bb):
    """Cobalt metal - strong blue-grey metallic with electric blue highlights."""
    h, w = shape
    # Blue-grey cobalt tint
    blend = 0.20 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.5) + 0.40 * blend * mask * 0.5, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.4) + 0.50 * blend * mask * 0.4, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.3) + 0.75 * blend * mask * 0.3, 0, 1)
    # Metallic flake with blue bias
    for c in range(3):
        flake = _multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17 + 820)
        strength = 0.06 if c == 2 else 0.04  # stronger blue channel flake
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * strength * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Weathered & Aged ---
paint_sun_fade = make_aged_fn(fade_strength=0.25, roughen=0.06)
paint_salt_damage = make_aged_fn(fade_strength=0.15, roughen=0.08)
paint_desert_sand = make_aged_fn(fade_strength=0.10, roughen=0.07)
paint_acid_etch_base = make_aged_fn(fade_strength=0.12, roughen=0.09)
paint_heavy_patina = make_aged_fn(fade_strength=0.18, roughen=0.07)
paint_vintage_haze = make_aged_fn(fade_strength=0.10, roughen=0.04)

# --- OEM Automotive ---
paint_oem_metallic = make_metallic_tint_fn(flake_str=0.08)
paint_fire_engine_gloss = make_vivid_depth_fn(sat_boost=0.15, depth_darken=0.05)
paint_reflective_coat = make_luxury_sparkle_fn(sparkle_density=0.93, sparkle_strength=0.12)
paint_fleet_plain = make_metallic_tint_fn(flake_str=0.02)  # Minimal - fleet vehicles are plain
paint_taxi_vivid = make_vivid_depth_fn(sat_boost=0.18, depth_darken=0.03)  # Vivid cab yellow
paint_school_bus_coat = make_vivid_depth_fn(sat_boost=0.12, depth_darken=0.06)  # Thicker enamel
def paint_police_deepblack(paint, shape, mask, seed, pm, bb):
    """Police interceptor - ultra-deep wet black with faint metallic sparkle."""
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.40 * pm * mask[:,:,np.newaxis]) + gray * 0.08 * pm * mask[:,:,np.newaxis]
    rng = np.random.RandomState(seed + 911)
    sparkle = rng.random(shape).astype(np.float32)
    sparkle = np.where(sparkle > 0.97, sparkle * 0.06 * pm, 0)
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Carbon & Composite ---
def paint_carbon_weave_base(paint, shape, mask, seed, pm, bb):
    """Raw carbon fiber - desaturate toward dark grey-black with fine weave grain."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Push toward dark desaturated carbon
    target = gray * 0.3  # Very dark
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask
    # Fine weave grain texture
    rng = np.random.RandomState(seed + 400)
    grain = rng.random((h, w)).astype(np.float32)
    weave_x = np.abs(np.arange(w) % 6 - 3) / 3.0  # 6px weave period
    weave_y = np.abs(np.arange(h) % 6 - 3) / 3.0
    weave = (weave_x.reshape(1, w) * 0.5 + weave_y.reshape(h, 1) * 0.5)
    paint = np.clip(paint + (weave[:,:,np.newaxis] * 0.08 + grain[:,:,np.newaxis] * 0.04) * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_kevlar_base_fn(paint, shape, mask, seed, pm, bb):
    """Kevlar base - warm golden-tan tint with coarser weave grain."""
    h, w = shape
    blend = 0.20 * pm
    # Push toward warm golden-tan
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.5) + 0.60 * blend * mask * 0.5, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.5) + 0.50 * blend * mask * 0.5, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.5) + 0.25 * blend * mask * 0.5, 0, 1)
    # Coarser weave pattern (8px)
    weave_x = np.abs(np.arange(shape[1]) % 8 - 4) / 4.0
    weave_y = np.abs(np.arange(shape[0]) % 8 - 4) / 4.0
    weave = weave_x.reshape(1, shape[1]) * 0.6 + weave_y.reshape(shape[0], 1) * 0.4
    paint = np.clip(paint + weave[:,:,np.newaxis] * 0.06 * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_fiberglass_gel_fn(paint, shape, mask, seed, pm, bb):
    """Fiberglass gelcoat - translucent milky white-blue shift with subtle texture."""
    h, w = shape
    blend = 0.20 * pm
    # Push toward pale milky blue-white
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.4) + 0.75 * blend * mask * 0.4, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.4) + 0.82 * blend * mask * 0.4, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.4) + 0.88 * blend * mask * 0.4, 0, 1)
    # Subtle fibrous texture
    rng = np.random.RandomState(seed + 410)
    fiber_noise = rng.random((h, w)).astype(np.float32) * 0.04
    paint = np.clip(paint + fiber_noise[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_carbon_ceramic_fn(paint, shape, mask, seed, pm, bb):
    """Carbon ceramic brake rotor - dark grey-blue matte with fine gritty texture."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Push toward dark grey with slight blue
    target_r = gray * 0.35
    target_g = gray * 0.37
    target_b = gray * 0.42
    paint[:,:,0] = paint[:,:,0] * (1 - blend * mask) + target_r[:,:,0] * blend * mask
    paint[:,:,1] = paint[:,:,1] * (1 - blend * mask) + target_g[:,:,0] * blend * mask
    paint[:,:,2] = paint[:,:,2] * (1 - blend * mask) + target_b[:,:,0] * blend * mask
    # Gritty ceramic texture
    rng = np.random.RandomState(seed + 420)
    grit = (rng.random((h, w)).astype(np.float32) - 0.5) * 0.08
    paint = np.clip(paint + grit[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_aramid_weave_fn(paint, shape, mask, seed, pm, bb):
    """Aramid fiber - golden-yellow warm tint with tight weave texture."""
    h, w = shape
    blend = 0.20 * pm
    # Warm golden-yellow tint
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.5) + 0.65 * blend * mask * 0.5, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.5) + 0.55 * blend * mask * 0.5, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.5) + 0.18 * blend * mask * 0.5, 0, 1)
    # Tight weave (4px)
    weave_x = np.abs(np.arange(w) % 4 - 2) / 2.0
    weave_y = np.abs(np.arange(h) % 4 - 2) / 2.0
    weave = weave_x.reshape(1, w) * 0.5 + weave_y.reshape(h, 1) * 0.5
    paint = np.clip(paint + weave[:,:,np.newaxis] * 0.05 * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_graphene_sheen_fn(paint, shape, mask, seed, pm, bb):
    """Graphene - ultra-dark near-black with subtle iridescent metallic sheen."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Push toward very dark grey (graphene is near-black)
    target = gray * 0.15
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask
    # Subtle iridescent sheen (different per channel)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    sheen = np.clip(1.0 - np.abs(y - 0.4) * 4, 0, 1) * 0.06 * blend
    paint[:,:,1] = np.clip(paint[:,:,1] + sheen * mask * 1.2, 0, 1)  # slight green
    paint[:,:,2] = np.clip(paint[:,:,2] + sheen * mask * 0.8, 0, 1)  # slight blue
    return paint

def paint_forged_composite_fn(paint, shape, mask, seed, pm, bb):
    """Forged carbon composite - Lamborghini-style random irregular dark chunks."""
    h, w = shape
    blend = 0.20 * pm
    gray = paint.mean(axis=2, keepdims=True)
    # Dark base
    target = gray * 0.25
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + target[:,:,0] * blend * mask
    # Irregular chunk pattern via multi-scale noise
    chunks = _multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 430)
    # Threshold to create irregular chunk shapes
    chunk_mask = np.where(chunks > 0.0, 0.08, -0.04).astype(np.float32)
    paint = np.clip(paint + chunk_mask[:,:,np.newaxis] * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hybrid_weave_fn(paint, shape, mask, seed, pm, bb):
    """Hybrid carbon-kevlar bi-weave - alternating dark carbon and golden kevlar."""
    h, w = shape
    blend = 0.20 * pm
    # Create alternating bands (carbon=dark, kevlar=golden)
    band = (np.arange(h) // 6 % 2).reshape(h, 1).astype(np.float32)  # 6px bands
    # Carbon dark in band=0
    gray = paint.mean(axis=2, keepdims=True)
    carbon_r = gray[:,:,0] * 0.30
    carbon_g = gray[:,:,0] * 0.30
    carbon_b = gray[:,:,0] * 0.32
    # Kevlar golden in band=1
    kevlar_r = paint[:,:,0] * 0.7 + 0.60 * 0.3
    kevlar_g = paint[:,:,1] * 0.7 + 0.50 * 0.3
    kevlar_b = paint[:,:,2] * 0.7 + 0.25 * 0.3
    # Blend based on band
    for c, (cv, kv) in enumerate([(carbon_r, kevlar_r), (carbon_g, kevlar_g), (carbon_b, kevlar_b)]):
        mixed = cv * (1 - band) + kv * band
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + mixed * blend * mask
    return paint


# ================================================================
# BASE SPEC FUNCTIONS - Material-specific spec map generators
# ================================================================
# Each returns (M_arr, R_arr) with the actual material pattern.
# These replace generic noise with physically accurate patterns.

def _base_spec_carbon_weave(shape, seed, sm, base_M, base_R):
    """Carbon fiber 2x2 twill weave - classic crosshatch pattern."""
    h, w = shape
    y, x = _get_mgrid((h, w))
    weave_size = 24  # visible threads at car scale
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Weave peaks = shinier (lower R), valleys = rougher
    M_arr = np.full(shape, base_M, dtype=np.float32) + cf * 30 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - cf) * 50 * sm
    return (M_arr, R_arr)

def _base_spec_kevlar_weave(shape, seed, sm, base_M, base_R):
    """Kevlar aramid weave - coarser plain weave at 32px, rougher than carbon."""
    h, w = shape
    y, x = _get_mgrid((h, w))
    weave_size = 32  # kevlar is coarser than CF
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    # Plain weave (each thread crosses over/under alternately)
    cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    kv = cell * horiz + (1 - cell) * vert
    kv = np.clip(kv * 1.15 - 0.08, 0, 1)
    M_arr = np.full(shape, base_M, dtype=np.float32) + kv * 20 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - kv) * 40 * sm
    return (M_arr, R_arr)

def _base_spec_fiberglass(shape, seed, sm, base_M, base_R):
    """Fiberglass mat - random directional fiber strands creating a rough mat texture."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Random fibers at various angles
    fiber_map = np.zeros(shape, dtype=np.float32)
    n_fibers = max(200, h * w // 500)
    for _ in range(n_fibers):
        x0 = rng.randint(0, w)
        y0 = rng.randint(0, h)
        angle = rng.random() * np.pi
        length = rng.randint(10, 50)
        for t in range(length):
            fx = int(x0 + np.cos(angle) * t) % w
            fy = int(y0 + np.sin(angle) * t) % h
            fiber_map[fy, fx] = min(fiber_map[fy, fx] + 0.15, 1.0)
    # Smooth slightly to simulate resin filling
    from scipy.ndimage import uniform_filter
    fiber_map = uniform_filter(fiber_map, size=3)
    M_arr = np.full(shape, base_M, dtype=np.float32) + fiber_map * 20 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + fiber_map * 30 * sm
    return (M_arr, R_arr)

def _base_spec_carbon_ceramic(shape, seed, sm, base_M, base_R):
    """Carbon ceramic - fine gritty particles with tiny pore variation."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Fine random grit (ceramic particles)
    grit = rng.random((h, w)).astype(np.float32)
    # Add medium-scale pore variation
    pore_h, pore_w = max(1, h // 8), max(1, w // 8)
    pores = rng.random((pore_h, pore_w)).astype(np.float32)
    from PIL import Image as PILImage
    pores_big = np.array(PILImage.fromarray((pores * 255).astype(np.uint8)).resize((w, h), PILImage.BILINEAR)).astype(np.float32) / 255.0
    combined = grit * 0.6 + pores_big * 0.4
    M_arr = np.full(shape, base_M, dtype=np.float32) + combined * 35 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + combined * 25 * sm
    return (M_arr, R_arr)

def _base_spec_aramid(shape, seed, sm, base_M, base_R):
    """Aramid - tight 16px plain weave, finer than kevlar."""
    h, w = shape
    y, x = _get_mgrid((h, w))
    weave_size = 16  # aramid is tighter than kevlar
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    ar = cell * horiz + (1 - cell) * vert
    ar = np.clip(ar * 1.2 - 0.1, 0, 1)
    M_arr = np.full(shape, base_M, dtype=np.float32) + ar * 15 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - ar) * 35 * sm
    return (M_arr, R_arr)

def _base_spec_graphene(shape, seed, sm, base_M, base_R):
    """Graphene - ultra-smooth near-mirror with faint molecular ripple texture."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Very faint hexagonal-like ripple (graphene lattice analog)
    ripple = (np.sin(x * 80 * np.pi + y * 46 * np.pi) * 0.3 +
              np.sin(x * 46 * np.pi - y * 80 * np.pi) * 0.3 +
              np.sin((x + y) * 55 * np.pi) * 0.2) * 0.5 + 0.5
    M_arr = np.full(shape, base_M, dtype=np.float32) + ripple * 15 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + ripple * 8 * sm
    return (M_arr, R_arr)

def _base_spec_forged_composite(shape, seed, sm, base_M, base_R):
    """Forged carbon composite - irregular chopped fiber chunks with sharp boundaries."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Large blobs for main chunk shapes
    s1h, s1w = max(1, h // 24), max(1, w // 24)
    raw1 = rng.randn(s1h, s1w).astype(np.float32)
    from PIL import Image as PILImage
    n1 = np.array(PILImage.fromarray(((raw1 + 3) / 6 * 255).clip(0, 255).astype(np.uint8)).resize((w, h), PILImage.BILINEAR)).astype(np.float32) / 255.0
    # Medium sub-chunks
    s2h, s2w = max(1, h // 12), max(1, w // 12)
    raw2 = rng.randn(s2h, s2w).astype(np.float32)
    n2 = np.array(PILImage.fromarray(((raw2 + 3) / 6 * 255).clip(0, 255).astype(np.uint8)).resize((w, h), PILImage.BILINEAR)).astype(np.float32) / 255.0
    # Fine surface grain
    s3h, s3w = max(1, h // 4), max(1, w // 4)
    raw3 = rng.randn(s3h, s3w).astype(np.float32)
    n3 = np.array(PILImage.fromarray(((raw3 + 3) / 6 * 255).clip(0, 255).astype(np.uint8)).resize((w, h), PILImage.BILINEAR)).astype(np.float32) / 255.0
    combined = n1 * 0.55 + n2 * 0.35 + n3 * 0.10
    # Quantize into discrete chunks with sharp boundaries
    num_levels = 10
    quantised = np.floor(combined * num_levels) / num_levels
    qmin, qmax = quantised.min(), quantised.max()
    if qmax > qmin:
        quantised = (quantised - qmin) / (qmax - qmin)
    # Each chunk has different metallic/roughness (fiber orientation)
    M_arr = np.full(shape, base_M, dtype=np.float32) + quantised * 40 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + quantised * 50 * sm + n3 * 8 * sm
    return (M_arr, R_arr)

def _base_spec_hybrid_weave(shape, seed, sm, base_M, base_R):
    """Hybrid carbon-kevlar bi-weave - alternating bands of carbon and kevlar weave."""
    h, w = shape
    y, x = _get_mgrid((h, w))
    # Carbon bands: 24px weave
    cf_size = 24
    tow_cx = (x % (cf_size * 2)) / (cf_size * 2)
    tow_cy = (y % (cf_size * 2)) / (cf_size * 2)
    cf_h = np.sin(tow_cx * np.pi * 2) * 0.5 + 0.5
    cf_v = np.sin(tow_cy * np.pi * 2) * 0.5 + 0.5
    cf_cell = ((x // cf_size + y // cf_size) % 2).astype(np.float32)
    cf = cf_cell * cf_h + (1 - cf_cell) * cf_v
    # Kevlar bands: 32px weave
    kv_size = 32
    tow_kx = (x % (kv_size * 2)) / (kv_size * 2)
    tow_ky = (y % (kv_size * 2)) / (kv_size * 2)
    kv_h = np.sin(tow_kx * np.pi * 2) * 0.5 + 0.5
    kv_v = np.sin(tow_ky * np.pi * 2) * 0.5 + 0.5
    kv_cell = ((x // kv_size + y // kv_size) % 2).astype(np.float32)
    kv = kv_cell * kv_h + (1 - kv_cell) * kv_v
    # Alternating bands (48px per band)
    band = ((y // 48) % 2).astype(np.float32)
    weave = cf * (1 - band) + kv * band
    # Carbon bands: higher M, lower R. Kevlar bands: lower M, higher R
    M_arr = np.full(shape, base_M, dtype=np.float32) + weave * 25 * sm + (1 - band) * 10
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - weave) * 35 * sm + band * 15
    return (M_arr, R_arr)


# ================================================================
# EXTREME & EXPERIMENTAL SPEC FUNCTIONS
# ================================================================
# Showstopper spec patterns - write dramatic visual patterns into
# M/R/CC channels of the spec map. These go far beyond subtle noise.

def _base_spec_plasma_core(shape, seed, sm, base_M, base_R):
    """Plasma core - snaking plasma veins with extreme M/R contrast."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # Plasma veins: sine modulation creates organic flowing paths
    vein1 = np.sin(x * 0.06 + np.sin(y * 0.04) * 4.0) * 0.5 + 0.5
    vein2 = np.sin(y * 0.05 + np.sin(x * 0.03) * 5.0) * 0.5 + 0.5
    veins = np.clip(vein1 * vein2, 0, 1).astype(np.float32)
    # Hot veins = extremely metallic + very smooth. Rest = rough dark
    hot = np.where(veins > 0.65, (veins - 0.65) / 0.35, 0).astype(np.float32)
    M_arr = np.full(shape, base_M * 0.6, dtype=np.float32) + hot * 120 * sm
    R_arr = np.full(shape, base_R + 60, dtype=np.float32) - hot * 80 * sm
    R_arr = np.clip(R_arr, 0, 255)
    return (M_arr, R_arr)

def _base_spec_bioluminescent(shape, seed, sm, base_M, base_R):
    """Bioluminescent - organic glow waves + scattered luminous dots."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # Organic glow waves
    glow = np.sin(x * 0.03 + np.sin(y * 0.02) * 5.0) * 0.5 + 0.5
    glow2 = np.sin(y * 0.025 + np.sin(x * 0.04) * 3.0) * 0.5 + 0.5
    flow = np.clip(glow * 0.6 + glow2 * 0.4, 0, 1).astype(np.float32)
    # Luminous dots: bright metallic points scattered across surface
    rng = np.random.RandomState(seed + 950)
    dots = rng.random((h, w)).astype(np.float32)
    bright_dots = np.where(dots > 0.95, (dots - 0.95) * 15.0, 0).astype(np.float32)
    M_arr = np.full(shape, base_M, dtype=np.float32) + flow * 50 * sm + bright_dots * 100 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - flow) * 40 * sm - bright_dots * 30 * sm
    R_arr = np.clip(R_arr, 0, 255)
    return (M_arr, R_arr)

def _base_spec_holographic(shape, seed, sm, base_M, base_R):
    """Holographic - diagonal rainbow banding with alternating M/R values."""
    h, w = shape
    y, x = _get_mgrid(shape)
    # Diagonal sweep: many thin bands with different M/R
    sweep = (x.astype(np.float32) * 0.04 + y.astype(np.float32) * 0.025)
    # 12 discrete bands (like holographic foil color zones)
    num_bands = 12
    band_id = (np.floor(sweep * num_bands) % num_bands).astype(np.float32)
    band_norm = band_id / num_bands
    # Each band has different metallic and roughness - creates spectral variation
    M_wave = np.sin(band_norm * np.pi * 2) * 0.5 + 0.5  # oscillating metallic
    R_wave = np.cos(band_norm * np.pi * 2 + 1.0) * 0.5 + 0.5  # offset roughness
    M_arr = np.full(shape, base_M * 0.5, dtype=np.float32) + M_wave.astype(np.float32) * 100 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + R_wave.astype(np.float32) * 60 * sm
    return (M_arr, R_arr)

def _base_spec_quantum_black(shape, seed, sm, base_M, base_R):
    """Quantum black - near-zero metallic, almost nothing in spec. Faint dot imperfections."""
    h, w = shape
    rng = np.random.RandomState(seed + 960)
    # Near-zero base with faint random imperfections
    faint = rng.random((h, w)).astype(np.float32)
    dots = np.where(faint > 0.97, (faint - 0.97) * 20.0, 0).astype(np.float32)
    M_arr = np.full(shape, base_M, dtype=np.float32) + dots * 15 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) - dots * 10 * sm
    return (M_arr, R_arr)

def _base_spec_neutron_star(shape, seed, sm, base_M, base_R):
    """Neutron star - radial concentric pulse waves from center, extreme M."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.float32)
    # Concentric rings of varying metallic intensity
    pulse = (np.sin(dist * 0.04) * 0.5 + 0.5).astype(np.float32)
    M_arr = np.full(shape, base_M - 30, dtype=np.float32) + pulse * 50 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - pulse) * 15 * sm
    return (M_arr, R_arr)

def _base_spec_dark_matter(shape, seed, sm, base_M, base_R):
    """Dark matter - sharp geometric angular bands with alternating M/R."""
    h, w = shape
    y, x = _get_mgrid(shape)
    angle = (x.astype(np.float32) / max(w, 1) + y.astype(np.float32) / max(h, 1)) * 0.5
    # Sharp peaked geometric bands
    band1 = (np.abs(np.sin(angle * np.pi * 8)) ** 4).astype(np.float32)
    band2 = (np.abs(np.cos(angle * np.pi * 5 + 1.2)) ** 4).astype(np.float32)
    combined = np.clip(band1 * 0.6 + band2 * 0.4, 0, 1)
    M_arr = np.full(shape, base_M, dtype=np.float32) + combined * 60 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) - combined * 40 * sm
    R_arr = np.clip(R_arr, 0, 255)
    return (M_arr, R_arr)

def _base_spec_superconductor(shape, seed, sm, base_M, base_R):
    """Superconductor - rippling Meissner effect magnetic field lines."""
    h, w = shape
    y, x = _get_mgrid(shape)
    field1 = (np.sin(x * 0.04 + y * 0.02) * np.cos(y * 0.03) * 0.5 + 0.5).astype(np.float32)
    field2 = (np.sin(x * 0.025 - y * 0.035 + 2.0) * 0.5 + 0.5).astype(np.float32)
    field = field1 * 0.6 + field2 * 0.4
    M_arr = np.full(shape, base_M, dtype=np.float32) + field * 30 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - field) * 20 * sm
    return (M_arr, R_arr)

def _base_spec_solar_panel(shape, seed, sm, base_M, base_R):
    """Solar panel - visible photovoltaic grid with bus-bar lines."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell_size = 40
    grid_h = (y % cell_size < 2).astype(np.float32)
    grid_v = (x % cell_size < 2).astype(np.float32)
    grid = np.maximum(grid_h, grid_v)
    # Grid bus-bars: high metallic, low roughness (silver conductors)
    # Cell body: moderate metallic, moderate roughness (silicon)
    M_arr = np.full(shape, base_M, dtype=np.float32) + grid * 80 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) - grid * 35 * sm + (1 - grid) * 15 * sm
    R_arr = np.clip(R_arr, 0, 255)
    return (M_arr, R_arr)

# --- INDUSTRIAL & TACTICAL SPEC FUNCTIONS ---

def _base_spec_armor_plate(shape, seed, sm, base_M, base_R):
    """Armor plate - rolling mill directional marks + heavy metal grain."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed + 540)
    # Rolling mill marks (horizontal directional lines)
    marks = np.sin(y * 0.15 + rng.random(1)[0] * 100) * 0.5 + 0.5
    mill_lines = np.where(marks > 0.8, (marks - 0.8) * 3.0, 0).astype(np.float32)
    # Heavy grain
    grain = rng.random((h, w)).astype(np.float32)
    M_arr = np.full(shape, base_M, dtype=np.float32) + mill_lines * 35 * sm + grain * 15 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) + (1 - mill_lines) * 20 * sm + grain * 15 * sm
    return (M_arr, R_arr)

def _base_spec_submarine(shape, seed, sm, base_M, base_R):
    """Submarine hull - acoustic dampening tile grid pattern."""
    h, w = shape
    y, x = _get_mgrid(shape)
    tile_size = 24
    tile_edge_h = (y % tile_size < 2).astype(np.float32)
    tile_edge_v = (x % tile_size < 2).astype(np.float32)
    grid = np.maximum(tile_edge_h, tile_edge_v)
    # Grid seams: slightly different roughness (rubber gaps between tiles)
    # Tile body: uniform high roughness (anechoic coating)
    M_arr = np.full(shape, base_M, dtype=np.float32) + grid * 20 * sm
    R_arr = np.full(shape, base_R, dtype=np.float32) - grid * 30 * sm
    R_arr = np.clip(R_arr, 0, 255)
    # Micro variation within tiles
    rng = np.random.RandomState(seed + 550)
    micro = rng.random((h, w)).astype(np.float32) * 8 * sm
    R_arr = R_arr + micro
    return (M_arr, R_arr)

# --- Premium Luxury ---
paint_rosso_depth = make_vivid_depth_fn(sat_boost=0.15, depth_darken=0.06)
paint_lambo_green = make_vivid_depth_fn(sat_boost=0.18, depth_darken=0.04)
paint_pts_depth = make_vivid_depth_fn(sat_boost=0.14, depth_darken=0.05)
paint_mclaren_vivid = make_vivid_depth_fn(sat_boost=0.20, depth_darken=0.03)
paint_bugatti_depth = make_vivid_depth_fn(sat_boost=0.16, depth_darken=0.07)
paint_pagani_shift = make_luxury_sparkle_fn(sparkle_density=0.95, sparkle_strength=0.07)
paint_two_tone_split = make_luxury_sparkle_fn(sparkle_density=0.97, sparkle_strength=0.05)

def paint_bentley_silver_liquid(paint, shape, mask, seed, pm, bb):
    """Rolls-Royce/Bentley ultra-fine silver - smooth bright liquid metal (toned down flake)."""
    h, w = shape
    # Bright silver push
    paint = np.clip(paint * (1 - 0.2*pm*mask[:,:,np.newaxis]) + 0.9*0.2*pm*mask[:,:,np.newaxis], 0, 1)
    # Flake is substantially smaller and fainter
    rng = np.random.RandomState(seed + 101)
    liquid_flake = (rng.random(shape).astype(np.float32) - 0.5) * 0.05 # Dropped vastly from 0.15
    paint = np.clip(paint + liquid_flake[:,:,np.newaxis] * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_lambo_verde_shift(paint, shape, mask, seed, pm, bb):
    """Lamborghini Verde Mantis - angle-dependent shifting electric yellow-green."""
    h, w = shape
    # Base vivid green
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - 0.2*pm*mask) + 0.2*0.2*pm*mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - 0.2*pm*mask) + 0.9*0.2*pm*mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - 0.2*pm*mask) + 0.1*0.2*pm*mask, 0, 1)
    # Highlight shifts to electric yellow based on tangent/reflection
    y, x = _get_mgrid(shape)
    shift_angle = (x * 0.7 + y * 0.3) / max(w, h)
    yellow_push = np.sin(shift_angle * np.pi * 3) ** 2
    yellow_push = yellow_push.astype(np.float32) * 0.4 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + yellow_push * mask, 0, 1) # Add red to green = yellow
    paint = np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_bugatti_blue_layer(paint, shape, mask, seed, pm, bb):
    """Bugatti Bleu de France - bi-layer transparency blue shift without harsh diagonal stripes."""
    h, w = shape
    # Add deep cyan-blue tint shift over whatever the base color is
    blend = 0.3 * pm
    # Shift toward Bugatti Blue (High cyan/blue, low red)
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + 0.05 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.5) + 0.35 * blend * mask * 0.5, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.8) + 0.85 * blend * mask * 0.8, 0, 1)
    
    # Subtle organic bi-layer cyan reflection (No diagonal stripes)
    cyan_pop = _multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 104)
    cyan_pop = (cyan_pop ** 3).astype(np.float32) * 0.4 * pm
    paint[:,:,1] = np.clip(paint[:,:,1] + cyan_pop * mask, 0, 1) # Green
    paint[:,:,2] = np.clip(paint[:,:,2] + cyan_pop * 1.5 * mask, 0, 1) # Blue
    paint = np.clip(paint + bb * 0.7 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_koenigsegg_clear_weave(paint, shape, mask, seed, pm, bb):
    """Clear carbon visible weave (Koenigsegg style) - projected geometric carbon weave matrix."""
    h, w = shape
    # Subtle darkening for carbon under clearcoat
    paint = np.clip(paint * (1 - 0.1*pm*mask[:,:,np.newaxis]), 0, 1)
    # Geometric 2D Grid Weave (checkerboard variant)
    y, x = _get_mgrid(shape)
    period = 8  # 8px weave block
    wx = (x // period) % 2
    wy = (y // period) % 2
    weave_mask = (wx == wy).astype(np.float32)
    # Apply weave as a slight luminance deviation (the weave catching light)
    weave_highlight = weave_mask * 0.15 * pm
    for c in range(3):
         paint[:,:,c] = np.clip(paint[:,:,c] + weave_highlight * mask, 0, 1)
    # Thick Koenigsegg clearcoat
    paint = np.clip(paint + bb * 0.8 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_maybach_split(paint, shape, mask, seed, pm, bb):
    """Mercedes-Maybach luxury base - high-gloss deep metallic with very subtle smooth linear gradients, removing the harsh 50/50 block split."""
    h, w = shape
    y, x = _get_mgrid(shape)
    
    # 1. Deepen the base color gracefully
    gray = paint.mean(axis=2, keepdims=True)
    for c in range(3):
        # Slightly deepen the red/blue for a richer tint
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - 0.15*pm*mask), 0, 1)
        
    # 2. Add ultra-fine luxury metallic dust
    dust = _multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed + 106)
    paint = np.clip(paint + dust[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    
    # 3. Add a soft gradient shadow on the lower half of the template map (soft, not harsh split)
    y_grad = y / max(h, 1)
    bottom_darken = np.clip((y_grad - 0.5) * 2.0, 0, 1) * 0.2 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - bottom_darken * mask), 0, 1)

    paint = np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Unique paint functions that need custom logic ---

def paint_moonstone_glow(paint, shape, mask, seed, pm, bb):
    """Moonstone - visible milky translucent shimmer with iridescent color pearls."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    # Strong milky white push
    white_blend = 0.35 * pm
    paint = paint * (1 - white_blend * mask[:,:,np.newaxis]) + 0.88 * white_blend * mask[:,:,np.newaxis]
    # Soft internal glow with iridescent color pearls
    glow = _multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 700)
    # Channel-separated glow for iridescence
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 0.15 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.18 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.22 * pm * mask, 0, 1)
    # Fine pearlescent sparkle
    rng = np.random.RandomState(seed + 701)
    sparkle = rng.random((h, w)).astype(np.float32)
    sp = np.where(sparkle > 0.92, (sparkle - 0.92) * 1.5 * pm, 0.0)
    paint = np.clip(paint + sp[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_opal_shift(paint, shape, mask, seed, pm, bb):
    """Fire opal - strong multi-color internal play with visible sparkle."""
    h, w = shape
    # Per-channel noise for dramatic color play
    for c in range(3):
        noise = _multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 800 + c * 31)
        paint[:,:,c] = np.clip(paint[:,:,c] + noise * 0.30 * pm * mask, 0, 1)
    # Dense visible sparkle
    rng = np.random.RandomState(seed + 850)
    sparkle = rng.random((h, w)).astype(np.float32)
    sparkle_bright = np.where(sparkle > 0.90, (sparkle - 0.90) * 2.0 * pm, 0.0)
    # Iridescent sparkle (each channel slightly offset)
    paint[:,:,0] = np.clip(paint[:,:,0] + sparkle_bright * mask * 1.1, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + sparkle_bright * mask * 0.9, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + sparkle_bright * mask * 1.0, 0, 1)
    paint = np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_color_flip(paint, shape, mask, seed, pm, bb):
    """Wrap film color-flip - aggressive angle-dependent color shift simulation."""
    import colorsys
    h, w = shape
    y, x = _get_mgrid(shape)
    
    # Simulate a realistic 3D curved surface for the angle
    cx, cy = w / 2.0, h / 2.0
    # Radial distance from center creates a dome-like angle map
    dist_sq = ((x - cx)**2) / (w**2) + ((y - cy)**2) / (h**2)
    angle_base = np.clip(np.sqrt(dist_sq) * 2.0, 0, 1)
    
    # Add flowing organic noise to warp the flip (like viewing a curved car panel)
    angle_noise = _multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 900)
    angle_map = np.clip(angle_base * 0.7 + angle_noise * 0.3, 0, 1)
    
    # Convert RGB to HSV to cleanly rotate the hue
    # (Since numpy doesn't have a fast vectorized RGB->HSV, we do an approximation or loop)
    # Fast RGB color shift matrix approximation (hue rotation by ~60 to 90 degrees based on angle)
    
    # The shift angle in radians (up to ~120 degrees of color flip)
    shift_amount = angle_map * (np.pi * 0.6) * pm
    
    cos_A = np.cos(shift_amount)
    sin_A = np.sin(shift_amount)
    
    # Hue rotation matrix components
    matrix = np.zeros((h, w, 3, 3), dtype=np.float32)
    matrix[:,:,0,0] = cos_A + (1.0 - cos_A) / 3.0
    matrix[:,:,0,1] = (1.0 - cos_A) / 3.0 - np.sqrt(1/3.0) * sin_A
    matrix[:,:,0,2] = (1.0 - cos_A) / 3.0 + np.sqrt(1/3.0) * sin_A
    
    matrix[:,:,1,0] = (1.0 - cos_A) / 3.0 + np.sqrt(1/3.0) * sin_A
    matrix[:,:,1,1] = cos_A + (1.0 - cos_A) / 3.0
    matrix[:,:,1,2] = (1.0 - cos_A) / 3.0 - np.sqrt(1/3.0) * sin_A
    
    matrix[:,:,2,0] = (1.0 - cos_A) / 3.0 - np.sqrt(1/3.0) * sin_A
    matrix[:,:,2,1] = (1.0 - cos_A) / 3.0 + np.sqrt(1/3.0) * sin_A
    matrix[:,:,2,2] = cos_A + (1.0 - cos_A) / 3.0
    
    new_paint = np.zeros_like(paint)
    for c in range(3):
        new_paint[:,:,c] = (paint[:,:,0] * matrix[:,:,c,0] + 
                            paint[:,:,1] * matrix[:,:,c,1] + 
                            paint[:,:,2] * matrix[:,:,c,2])
    
    # Apply mask and keep brightness roughly the same
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - mask) + new_paint[:,:,c] * mask, 0, 1)
        
    return paint

def paint_mud_splatter(paint, shape, mask, seed, pm, bb):
    """Rally mud splatter - random mud-colored splats over paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 950)
    mud = np.zeros((h, w), dtype=np.float32)
    
    num_splats = int(80 * pm)
    for _ in range(num_splats):
        cy, cx = rng.randint(0, h), rng.randint(0, w)
        radius = rng.randint(10, 60)
        
        # Optimize by only calculating distance within the splat's bounding box
        y_min, y_max = max(0, cy - radius), min(h, cy + radius + 1)
        x_min, x_max = max(0, cx - radius), min(w, cx + radius + 1)
        
        if y_min >= y_max or x_min >= x_max:
            continue
            
        y, x = np.mgrid[y_min:y_max, x_min:x_max]
        dist = np.sqrt((y - cy)**2 + (x - cx)**2)
        splat = np.clip(1.0 - dist / radius, 0, 1) ** 2
        
        mud[y_min:y_max, x_min:x_max] = np.maximum(
            mud[y_min:y_max, x_min:x_max], 
            splat * rng.uniform(0.3, 1.0)
        )
        
    mud = np.clip(mud, 0, 1)
    # Mud color: brownish desaturation
    mud_color = np.array([0.25, 0.20, 0.12])
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mud * 0.15 * pm * mask) + mud_color[c] * mud * 0.15 * pm * mask
    return paint

def paint_heat_wrap_tint(paint, shape, mask, seed, pm, bb):
    """Heat shield - metallic with heat-blue tint zones."""
    # Base chrome brighten
    blend = 0.15 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend) + 0.85 * mask * blend
    # Heat zones - blue-gold gradient
    heat = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1000)
    heat = np.clip(heat * 0.5 + 0.5, 0, 1)
    # Blue in cool zones, gold in hot zones
    paint[:,:,0] = np.clip(paint[:,:,0] + heat * 0.04 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + (1 - heat) * 0.02 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + (1 - heat) * 0.05 * pm * mask, 0, 1)
    return paint

def paint_naked_carbon(paint, shape, mask, seed, pm, bb):
    """Clear coat over visible carbon - Koenigsegg style."""
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
    """SHOKK Pulse - HIGH VOLTAGE electric storm with vicious crackling arcs and deep glowing plasma."""
    h, w = shape[:2] if len(shape) > 1 else shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed + 1100)

    # Layer 1: Base metallic with intense blue-orange plasma core (Shokker colors)
    blend = 0.35 * pm
    # Push orange/red into the shadows
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + 0.95 * mask * blend # High red/orange
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + 0.45 * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + 0.10 * mask * blend

    # Layer 2: Violent electric wave interference (The Pulse)
    wave1 = np.sin(y * 0.08 + x * 0.02) * 0.5 + 0.5
    wave2 = np.sin(y * 0.15 - x * 0.04 + 1.5) * 0.5 + 0.5
    wave3 = np.sin((y + x) * 0.05) * 0.5 + 0.5
    pulse = (wave1 * 0.45 + wave2 * 0.35 + wave3 * 0.20)
    
    # Sharp, jagged noise for the electricity
    pulse_noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.4, 0.3, 0.2, 0.1], seed + 1101)
    pulse_noise = (pulse_noise - pulse_noise.min()) / (pulse_noise.max() - pulse_noise.min() + 1e-8)
    pulse = np.clip(pulse * 0.7 + pulse_noise * 0.5, 0, 1)

    # Layer 3: Blinding cyan/white electric arc lines (thresholded sharp peaks)
    arc_arg = np.maximum(0.0, (pulse - 0.85) / 0.15)
    arc_lines = np.where(pulse > 0.85, np.sqrt(arc_arg), 0).astype(np.float32)
    arc_strength = 0.60 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + arc_lines * arc_strength * 0.4 * mask, 0, 1) # White core
    paint[:,:,1] = np.clip(paint[:,:,1] + arc_lines * arc_strength * 0.8 * mask, 0, 1) # Cyan halo
    paint[:,:,2] = np.clip(paint[:,:,2] + arc_lines * arc_strength * 1.0 * mask, 0, 1) # Heavy blue

    # Layer 4: Aggressive random spark hotspots (Plasma bursts)
    sparks = rng.random(shape).astype(np.float32)
    spark_pop = np.where(sparks > 0.992, 0.45 * pm, 0.0)
    paint = np.clip(paint + spark_pop[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    # Layer 5: Deep charred metallic veins between the arcs for maximum contrast
    dark_veins = np.where(pulse < 0.35, (0.35 - pulse) * 2.5 * pm, 0).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - dark_veins * mask, 0, 1)

    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_venom_acid(paint, shape, mask, seed, pm, bb):
    """SHOKK Venom - TOXIC reactive acid with corrosive dripping pools and intense neon vapor glow."""
    h, w = shape[:2] if len(shape) > 1 else shape
    rng = np.random.RandomState(seed + 1200)

    # Layer 1: Hyper-aggressive toxic yellow-green base
    blend = 0.35 * pm
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + 0.60 * mask * blend  # High red for yellow mixing
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + 0.95 * mask * blend  # Max green
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + 0.05 * mask * blend  # Kill blue entirely

    # Layer 2: Acid bubbling & caustic flow
    noise1 = _multi_scale_noise(shape, [2, 4, 8], [0.4, 0.4, 0.2], seed + 1201)
    noise1 = (noise1 - noise1.min()) / (noise1.max() - noise1.min() + 1e-8)
    noise2 = _multi_scale_noise(shape, [16, 32, 64], [0.5, 0.3, 0.2], seed + 1202)
    noise2 = (noise2 - noise2.min()) / (noise2.max() - noise2.min() + 1e-8)

    # Layer 3: Sizzling acid pools (blinding neon green/yellow hotspots)
    acid_pools = np.clip((noise2 - 0.55) * 4.0, 0, 1)
    pool_glow = acid_pools * 0.45 * pm
    paint[:,:,1] = np.clip(paint[:,:,1] + pool_glow * mask, 0, 1) # Pure green glow
    paint[:,:,0] = np.clip(paint[:,:,0] + pool_glow * 0.7 * mask, 0, 1) # Yellow core

    # Layer 4: Deep black-green corrosion veins where the acid burns through
    corrosion = np.clip((0.4 - noise2) * 5.0, 0, 1) * 0.60 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - corrosion * mask, 0, 1)

    # Layer 5: Radioactive fine mist (sharp glittering specs)
    sparkle = rng.random(shape).astype(np.float32)
    toxic_spark = np.where(sparkle > 0.985, 0.35 * pm, 0.0)
    paint[:,:,1] = np.clip(paint[:,:,1] + toxic_spark * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + toxic_spark * 0.5 * mask, 0, 1) # Yellow sparks

    # Layer 6: Caustic surface bubbling
    grain = (noise1 - 0.5) * 0.25 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + grain * mask, 0, 1)

    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blood_red_deep(paint, shape, mask, seed, pm, bb):
    """SHOKK Blood - ARTERIAL crimson with violent pulsing vein networks and heavy, wet obsidian pooling."""
    h, w = shape[:2] if len(shape) > 1 else shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed + 1300)

    # Layer 1: Overwhelming arterial red base - pure, crushing crimson
    blend = 0.45 * pm
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + 0.95 * mask * blend  # Maximum red
    paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + 0.02 * mask * blend  # Kill green
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + 0.02 * mask * blend  # Kill blue

    # Layer 2: Jagged vein network - deep, nearly black spiderwebbing veins
    vein_noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.3, 0.3, 0.2, 0.2], seed + 1301)
    vein_noise = (vein_noise - vein_noise.min()) / (vein_noise.max() - vein_noise.min() + 1e-8)
    veins = np.clip(1.0 - np.abs(vein_noise - 0.5) * 8.0, 0, 1)  # Extremely tight, sharp veins
    vein_darken = veins * 0.70 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - vein_darken * mask, 0, 1)

    # Layer 3: Massive blood pools - dark, coagulated shadows with bright wet rims
    pool_noise = _multi_scale_noise(shape, [16, 32, 64], [0.4, 0.4, 0.2], seed + 1302)
    pool_noise = (pool_noise - pool_noise.min()) / (pool_noise.max() - pool_noise.min() + 1e-8)
    
    # The pools themselves go black
    pools_dark = np.clip((0.45 - pool_noise) * 4.0, 0, 1)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - pools_dark * 0.6 * pm * mask, 0, 1)

    # The rims of the pools catch light and glow pure bright red
    pool_rims = np.clip(1.0 - np.abs(pool_noise - 0.45) * 10.0, 0, 1)
    pool_bright = pool_rims * 0.40 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + pool_bright * mask, 0, 1) # Blinding red rims

    # Layer 4: Liquid wet sheen - scattered bright specular hits like freshly spilled blood
    sparkle = rng.random(shape).astype(np.float32)
    wet_sheen = np.where(sparkle > 0.985, 0.40 * pm, 0.0)
    paint[:,:,0] = np.clip(paint[:,:,0] + wet_sheen * 0.9 * mask, 0, 1)
    paint = np.clip(paint + wet_sheen[:,:,np.newaxis] * 0.25 * mask[:,:,np.newaxis], 0, 1)

    # Layer 5: Heavy vignetting and depth
    edge_noise = _multi_scale_noise(shape, [8, 16], [0.4, 0.6], seed + 1303)
    edge_noise = (edge_noise - edge_noise.min()) / (edge_noise.max() - edge_noise.min() + 1e-8)
    edge_dark = np.clip((0.40 - edge_noise) * 4, 0, 1) * 0.35 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - edge_dark * mask, 0, 1)

    paint = np.clip(paint + bb * 0.35 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_void_absorb(paint, shape, mask, seed, pm, bb):
    """SHOKK Void - CRUSHING avant-black singularity with an unstable, hyper-bright event horizon corona."""
    h, w = shape[:2] if len(shape) > 1 else shape
    rng = np.random.RandomState(seed + 1400)

    # Layer 1: MAXIMUM darkening - completely kill the base paint layer to true black
    darken = 0.98 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - darken * mask), 0, 1)

    # Layer 2: Total void vacuum noise - sucking in any remaining light
    depth_noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1401)
    depth_noise = (depth_noise - depth_noise.min()) / (depth_noise.max() - depth_noise.min() + 1e-8)
    extra_dark = depth_noise * 0.30 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - extra_dark * mask, 0, 1)

    # Layer 3: Searing Event Horizon Edge Corona - vivid violet/blue electric plasma burning at the edges of the void
    edge_noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.4, 0.3, 0.2, 0.1], seed + 1402)
    edge_noise = (edge_noise - edge_noise.min()) / (edge_noise.max() - edge_noise.min() + 1e-8)
    
    # Sharp, bright energy bursts
    corona_arg = np.maximum(0.0, (edge_noise - 0.85) / 0.15)
    corona = np.where(edge_noise > 0.85, np.sqrt(corona_arg) * 0.80 * pm, 0).astype(np.float32)
    
    # Intense Purple/Blue/Cyan fire
    paint[:,:,0] = np.clip(paint[:,:,0] + corona * 0.6 * mask, 0, 1) # Red (creates purple)
    paint[:,:,1] = np.clip(paint[:,:,1] + corona * 0.4 * mask, 0, 1) # Green
    paint[:,:,2] = np.clip(paint[:,:,2] + corona * 1.0 * mask, 0, 1) # Heavy Blue

    # Layer 4: Hawking radiation - rare, blinding white singularity pinpoints that pop against the black
    sparks = rng.random(shape).astype(np.float32)
    singularity = np.where(sparks > 0.998, 0.80 * pm, 0.0)
    paint = np.clip(paint + singularity[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    return paint

def paint_static_grain(paint, shape, mask, seed, pm, bb):
    """SHOKK Static - VIOLENT signal interference with scan lines, glitch bands, and noise bursts."""
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
    """Quantum Black - near-perfect light absorption, Vantablack-level dark.
    Only the faintest noise-based highlight bleed reveals it's a surface at all."""
    h, w = shape
    blend = 0.20 * pm
    # EXTREME darkening - 95% light absorption
    paint = paint * (1 - 0.95 * blend * mask[:,:,np.newaxis])
    # Faint noise-based highlight bleed (surface imperfections catch microscopic light)
    rng = np.random.RandomState(seed + 900)
    bleed = rng.random((h, w)).astype(np.float32)
    faint = np.where(bleed > 0.97, (bleed - 0.97) * 15.0, 0).astype(np.float32)
    paint = np.clip(paint + faint[:,:,np.newaxis] * 0.03 * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_neutron_bright(paint, shape, mask, seed, pm, bb):
    """Neutron Star - blinding compressed mirror with pulsing radial brightness waves."""
    h, w = shape
    blend = 0.20 * pm
    # Push toward blinding white
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend * 0.8) + 0.98 * mask * blend * 0.8
    # Pulsing radial brightness waves from center
    y, x = _get_mgrid(shape)
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.float32)
    pulse = (np.sin(dist * 0.05) * 0.5 + 0.5).astype(np.float32)
    paint = np.clip(paint + pulse[:,:,np.newaxis] * 0.04 * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_plasma_glow(paint, shape, mask, seed, pm, bb):
    """Plasma Core - glowing reactor core with plasma veins snaking across surface."""
    h, w = shape
    blend = 0.20 * pm
    # Deep purple-magenta metallic base
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.5) + 0.55 * blend * mask * 0.5, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.6) + 0.10 * blend * mask * 0.6, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.4) + 0.80 * blend * mask * 0.4, 0, 1)
    # Plasma veins that snake across surface
    y, x = _get_mgrid(shape)
    vein1 = np.sin(x * 0.06 + np.sin(y * 0.04) * 4.0) * 0.5 + 0.5
    vein2 = np.sin(y * 0.05 + np.sin(x * 0.03) * 5.0) * 0.5 + 0.5
    veins = np.clip(vein1 * vein2, 0, 1).astype(np.float32)
    hot_veins = np.where(veins > 0.7, (veins - 0.7) / 0.3, 0).astype(np.float32)
    # Veins glow bright magenta-white
    paint[:,:,0] = np.clip(paint[:,:,0] + hot_veins * 0.15 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + hot_veins * 0.05 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + hot_veins * 0.10 * blend * mask, 0, 1)
    return paint

def paint_dark_matter_shift(paint, shape, mask, seed, pm, bb):
    """Dark Matter - ultra-dark with geometric angular reveal bands that shift color."""
    h, w = shape
    blend = 0.20 * pm
    # Ultra-dark base
    paint = paint * (1 - 0.85 * blend * mask[:,:,np.newaxis])
    # Geometric angular reveal bands
    y, x = _get_mgrid(shape)
    angle = (x.astype(np.float32) / max(w, 1) + y.astype(np.float32) / max(h, 1)) * 0.5
    band1 = np.abs(np.sin(angle * np.pi * 8)) ** 4  # sharp peaked bands
    band2 = np.abs(np.cos(angle * np.pi * 5 + 1.2)) ** 4
    # Each band reveals a different color (dark purple / dark teal)
    paint[:,:,0] = np.clip(paint[:,:,0] + band1.astype(np.float32) * 0.08 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + band1.astype(np.float32) * 0.12 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + band2.astype(np.float32) * 0.06 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + band2.astype(np.float32) * 0.08 * blend * mask, 0, 1)
    return paint

def paint_superconductor_mirror(paint, shape, mask, seed, pm, bb):
    """Superconductor - near-pure mirror with rippling magnetic field lines."""
    h, w = shape
    blend = 0.20 * pm
    # Push toward near-pure mirror white
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend * 0.7) + 0.96 * mask * blend * 0.7
    # Rippling magnetic field lines (Meissner effect visualization)
    y, x = _get_mgrid(shape)
    field1 = np.sin(x * 0.04 + y * 0.02) * np.cos(y * 0.03) * 0.5 + 0.5
    field2 = np.sin(x * 0.025 - y * 0.035 + 2.0) * 0.5 + 0.5
    field = (field1 * 0.6 + field2 * 0.4).astype(np.float32)
    # Field lines show as very faint blue-cyan traces
    paint[:,:,1] = np.clip(paint[:,:,1] + field * 0.03 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + field * 0.05 * blend * mask, 0, 1)
    return paint

def paint_bio_glow(paint, shape, mask, seed, pm, bb):
    """Bioluminescent - deep sea organism with organic glow waves and bright luminous dots."""
    h, w = shape
    blend = 0.20 * pm
    # Deep dark teal-green base (deep sea)
    gray = paint.mean(axis=2, keepdims=True)
    paint[:,:,0] = paint[:,:,0] * (1 - blend * mask * 0.6) + (gray[:,:,0] * 0.1) * blend * mask * 0.6
    paint[:,:,1] = paint[:,:,1] * (1 - blend * mask * 0.4) + (gray[:,:,0] * 0.2 + 0.15) * blend * mask * 0.4
    paint[:,:,2] = paint[:,:,2] * (1 - blend * mask * 0.4) + (gray[:,:,0] * 0.15 + 0.12) * blend * mask * 0.4
    # Organic glow waves
    y, x = _get_mgrid(shape)
    glow_wave = np.sin(x * 0.03 + np.sin(y * 0.02) * 5.0) * 0.5 + 0.5
    paint[:,:,1] = np.clip(paint[:,:,1] + glow_wave.astype(np.float32) * 0.08 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow_wave.astype(np.float32) * 0.06 * blend * mask, 0, 1)
    # Scattered bright luminous dots
    rng = np.random.RandomState(seed + 910)
    dots = rng.random((h, w)).astype(np.float32)
    bright_dots = np.where(dots > 0.96, (dots - 0.96) * 12.0, 0).astype(np.float32)
    paint[:,:,1] = np.clip(paint[:,:,1] + bright_dots * 0.15 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + bright_dots * 0.10 * blend * mask, 0, 1)
    return paint

def paint_solar_cell(paint, shape, mask, seed, pm, bb):
    """Solar Panel - dark blue-black photovoltaic with visible cell grid lines."""
    h, w = shape
    blend = 0.20 * pm
    # Dark blue-black solar cell base
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask * 0.7) + 0.05 * blend * mask * 0.7, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask * 0.7) + 0.08 * blend * mask * 0.7, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask * 0.5) + 0.25 * blend * mask * 0.5, 0, 1)
    # Visible photovoltaic grid lines
    y, x = _get_mgrid(shape)
    cell_size = 40
    grid_h = (y % cell_size < 2).astype(np.float32)
    grid_v = (x % cell_size < 2).astype(np.float32)
    grid = np.maximum(grid_h, grid_v)
    # Grid lines are slightly lighter (silver bus-bars)
    paint[:,:,0] = np.clip(paint[:,:,0] + grid * 0.08 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + grid * 0.08 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + grid * 0.06 * blend * mask, 0, 1)
    return paint
def paint_holo_rainbow(paint, shape, mask, seed, pm, bb):
    """Holographic Base - full rainbow prismatic color shift with iridescent bands.

    Creates visible holographic rainbow effect by generating position-dependent
    hue rotation across the entire spectrum. Paint colors cycle through R/G/B
    channels based on spatial frequency, producing the classic holographic
    rainbow shimmer seen on holographic foils and stickers.
    """
    h, w = shape[:2] if len(shape) > 1 else shape
    y, x = _get_mgrid(shape)

    # Multi-scale angle field for hue rotation - combines diagonal sweep
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

    # Blend holographic color onto existing paint - aggressive enough to be visible
    blend = 0.35 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + holo_r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + holo_g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + holo_b * mask * blend, 0, 1)

    # Sparkle layer - holographic foils have visible micro-sparkle
    rng = np.random.RandomState(seed + 2050)
    sparkle = rng.random(shape).astype(np.float32)
    holo_sparkle = np.where(sparkle > 0.96, 0.20 * pm, 0.0)
    paint = np.clip(paint + holo_sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

    # Overall brightness boost for that reflective holographic pop
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# NEW BASE REGISTRY ENTRIES (100 new - #56 to #155)
# ================================================================
# Format matches existing: {"M": int, "R": int, "CC": int, "paint_fn": fn, "desc": str}
# Optional: noise_scales, noise_weights, noise_M, noise_R, brush_grain

EXPANSION_BASES = {
    # Group 1: FOUNDATION (new entries only)
    "eggshell":         {"M": 0,   "R": 140, "CC": 95,  "paint_fn": _paint_noop, "desc": "Soft low-sheen like eggshell wall paint"},
    "semi_gloss":       {"M": 0,   "R": 60,  "CC": 16, "paint_fn": _paint_noop, "desc": "Between satin and gloss - utility finish"},
    # Group 2: METALLIC STANDARD (new entries)
    "metal_flake_base": { "base_spec_fn": spec_metallic_standard,"M": 210, "R": 35,  "CC": 16, "paint_fn": _paint_noop, "desc": "Heavy visible metal flake base coat", "_resolve_paint_fn": "paint_coarse_flake",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 15},
    "candy_apple":      { "base_spec_fn": spec_metallic_standard,"M": 230, "R": 2, "CC": 150, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_smoked_darken", "desc": "A deeply unholy crimson candy gloss that pulls light into a violently crushed shadow point", "noise_scales": [4], "noise_M": 250, "noise_R": -10},
    "midnight_pearl":   { "base_spec_fn": spec_metallic_standard,"M": 140, "R": 25,  "CC": 16, "paint_fn": paint_dark_sparkle, "desc": "Deep dark pearlescent with hidden sparkle",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 10},
    "champagne":        { "base_spec_fn": spec_metallic_standard,"M": 160, "R": 45,  "CC": 16, "paint_fn": paint_warm_shimmer, "desc": "Warm gold-silver champagne metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 12},
    "pewter":           { "base_spec_fn": spec_metallic_standard,"M": 100, "R": 90, "CC": 80, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_chameleon_shift", "desc": "A dark, cursed grey meta-lead finish pulsing with forbidden underworld geometry", "perlin": True, "perlin_octaves": 3, "noise_R": 40},
    # Group 3: CHROME & MIRROR (new entries)
    "black_chrome":     {"M": 248, "R": 8,   "CC": 16,  "paint_fn": paint_black_chrome_tint, "desc": "Near-black highly reflective chrome",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 30, "noise_R": 12},
    "blue_chrome":      {"M": 252, "R": 3,   "CC": 16,  "paint_fn": paint_blue_chrome_tint, "desc": "Tinted blue mirror chrome",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 25, "noise_R": 10},
    "antique_chrome":   {"M": 240, "R": 15,  "CC": 50,  "paint_fn": paint_antique_patina, "desc": "Slightly aged imperfect chrome",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 40, "noise_R": 30},
    # Group 4: CANDY & PEARL (new entries)
    "candy_burgundy":   {"M": 20, "R": 60, "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_cp_candy_burgundy", "desc": "Viscous, dark thick semi-dried fluid coating, highly uneven and organically unsettling", "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.6, "noise_R": 100},
    "tri_coat_pearl":   {"M": 130, "R": 25,  "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_cp_tri_coat_pearl", "desc": "Three-stage pearl base+mid+clear",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 40, "noise_R": 20},
    "moonstone":        {"M": 90,  "R": 35,  "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_cp_moonstone", "desc": "Soft translucent milky shimmer",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 25, "noise_R": 30},
    "opal":             {"M": 180, "R": 50, "CC": 100, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_cp_opal", "desc": "Massive multi-colored shifting pearl mimicking the biological armored plate of a dragon", "noise_scales": [8, 16], "noise_M": 120, "noise_R": 80},
}

EXPANSION_BASES.update({
    # Group 5: SATIN & WRAP (new entries)
    "matte_wrap":       {"M": 5, "R": 160, "CC": 165, "paint_fn": paint_matte_wrap_v2, "base_spec_fn": spec_satin_wrap, "desc": "Ultra-smooth vinyl wrap"},
    "color_flip_wrap":  {"M": 5, "R": 160, "CC": 16, "paint_fn": paint_matte_wrap_v2, "base_spec_fn": spec_satin_wrap, "desc": "Color shifting matte wrap"},
    "chrome_wrap":      { "base_spec_fn": spec_satin_wrap,"M": 240, "R": 20,  "CC": 16,  "paint_fn": paint_chrome_wrap, "desc": "Mirror chrome vinyl wrap - slightly textured"},
    "gloss_wrap":       { "base_spec_fn": spec_satin_wrap,"M": 10,  "R": 15,  "CC": 16,  "paint_fn": paint_gloss_wrap_sheet, "desc": "High-gloss smooth vinyl wrap finish"},
    "textured_wrap":    { "base_spec_fn": spec_satin_wrap,"M": 0,   "R": 150, "CC": 40,  "paint_fn": paint_textured_wrap, "desc": "Orange-peel textured vinyl wrap"},
    "brushed_wrap":     { "base_spec_fn": spec_satin_wrap,"M": 180, "R": 80,  "CC": 35,  "paint_fn": paint_brushed_wrap, "desc": "Brushed metal vinyl wrap film"},
    # Group 6: INDUSTRIAL & TACTICAL (new entries)
    "mil_spec_od":      {"base_spec_fn": spec_mil_spec_od_v3, "M": 2, "R": 180, "CC": 195, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_mil_spec_od_v3", "desc": "Military specification Olive Drab"},
    "mil_spec_tan":     { "base_spec_fn": spec_martian_regolith, "M": 0, "R": 220, "CC": 200, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_martian_regolith", "desc": "Martian Regolith Dust"},
    "armor_plate":      {"base_spec_fn": spec_armor_plate_v2, "M": 60, "R": 160, "CC": 130, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_armor_plate_v2", "desc": "Heavy armor plating coat"},
    "submarine_black":  {"base_spec_fn": spec_submarine_black_v2, "M": 0, "R": 235, "CC": 210, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_submarine_black_v2", "desc": "Anechoic submarine hull coating"},
    "battleship_gray":  {"base_spec_fn": spec_battleship_gray_v2, "M": 20, "R": 140, "CC": 120, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_battleship_gray_v2", "desc": "Naval warship haze gray coating"},
    # Group 7: CERAMIC & GLASS (new entries)
    "porcelain":        {"M": 0, "R": 50, "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_ice_cracks", "desc": "Fractured monolithic bone ivory finish with subsurface micro-cracks", "perlin": True, "perlin_lacunarity": 3.0, "noise_R": 50},
    "obsidian":         {"M": 40,  "R": 6,   "CC": 16, "paint_fn": paint_obsidian_depth, "desc": "Volcanic glass deep black mirror sheen",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 45, "noise_R": 15},
    "crystal_clear":    {"M": 0, "R": 0, "CC": 255, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_wet_gloss", "desc": "A completely lucid, perfectly clear viscous water coating that never dries or sets", "noise_scales": [4, 8], "noise_R": 10},
    "tempered_glass":   {"M": 30,  "R": 4,   "CC": 16, "paint_fn": paint_glass_clean, "desc": "Safety glass smooth hard surface",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.35, "perlin_lacunarity": 2.0, "noise_M": 30, "noise_R": 12},
    "ceramic_matte":    {"M": 50,  "R": 120, "CC": 160,  "paint_fn": paint_ceramic_flat, "desc": "Matte ceramic nano-coating",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 35, "noise_R": 30},
    "enamel":           {"M": 10,  "R": 18,  "CC": 16, "paint_fn": paint_enamel_coat, "desc": "Hard baked enamel glossy traditional paint",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 15},
})

EXPANSION_BASES.update({
    # Group 8: RACING HERITAGE (new entries)
    "stock_car_enamel": {"M": 5, "R": 12, "CC": 16, "paint_fn": paint_race_day_gloss_v2, "base_spec_fn": spec_racing_heritage, "desc": "Classic thick stock car enamel"},
    # dirt_track_satin: REMOVED per audit 2026-03-15
    "endurance_ceramic":{ "base_spec_fn": spec_racing_heritage,"M": 20, "R": 220, "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_volcanic_ash", "desc": "Scorched, ablative ceramic reentry vehicle plating heavily charred by atmospheric friction", "perlin": True, "perlin_octaves": 5, "noise_M": 50, "noise_R": 200},
    "rally_mud":        { "base_spec_fn": spec_racing_heritage,"M": 30,  "R": 180, "CC": 80,  "paint_fn": paint_mud_splatter, "desc": "Partially mud-splattered rally coating",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 40, "noise_R": 40},
    "drag_strip_gloss": { "base_spec_fn": spec_racing_heritage,"M": 200, "R": 8,   "CC": 16, "paint_fn": paint_drag_strip_gloss, "desc": "Ultra-polished quarter-mile show finish"},
    "victory_lane":     { "base_spec_fn": spec_racing_heritage,"M": 230, "R": 5,   "CC": 16, "paint_fn": paint_confetti_sparkle, "desc": "Champagne-soaked celebration metallic sparkle",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.4, 0.4, 0.2], "noise_M": 25, "noise_R": 8},
    "barn_find":        { "base_spec_fn": spec_racing_heritage,"M": 60,  "R": 160, "CC": 210,  "paint_fn": paint_barn_find_chalk, "desc": "Decades-old stored car faded paint"},
    # rat_rod_primer: REMOVED per audit 2026-03-15
    "pace_car_pearl":   { "base_spec_fn": spec_racing_heritage,"M": 140, "R": 20,  "CC": 16, "paint_fn": paint_pace_car_pearl, "desc": "Official pace car triple-pearl coat",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 10},
    # heat_shield: REMOVED per audit 2026-03-15
    # pit_lane_matte: REMOVED per audit 2026-03-15
    "asphalt_grind":    { "base_spec_fn": spec_racing_heritage,"M": 40,  "R": 200, "CC": 200,  "paint_fn": paint_asphalt_rough, "desc": "Rough asphalt-ground surface texture",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.6, "noise_M": 25, "noise_R": 45},
    "checkered_chrome": { "base_spec_fn": spec_racing_heritage,"M": 245, "R": 10,  "CC": 16,  "paint_fn": paint_checker_polish, "desc": "Polished chrome with checkered reflection",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.5, 0.2], "noise_M": 30, "noise_R": 10},
    # Group 9: EXOTIC METAL (new entries)
    "liquid_titanium":  {"M": 240, "R": 5, "CC": 16, "paint_fn": paint_liquid_metal_flow_v2, "base_spec_fn": spec_exotic_metal, "desc": "Fluid pooling molten titanium"},
    "tungsten":         {"M": 220, "R": 35, "CC": 16, "paint_fn": paint_tungsten_heavy, "base_spec_fn": spec_exotic_metal, "desc": "Ultra-dense aerospace dark tungsten", "noise_scales": [2,4], "noise_weights": [0.6,0.4], "noise_M": 30, "noise_R": 20},
    "platinum":         {"M": 245, "R": 8, "CC": 16, "paint_fn": paint_platinum_sheen, "base_spec_fn": spec_exotic_metal, "desc": "Pure platinum bright white metal"},
    "cobalt_metal":     {"M": 200, "R": 40, "CC": 16, "paint_fn": paint_cobalt_tint, "base_spec_fn": spec_exotic_metal, "desc": "Blue-gray cobalt metallic sheen"},
    # Group 10: WEATHERED & AGED (new entries)
    "sun_baked":        {"M": 15, "R": 220, "CC": 155, "paint_fn": paint_sun_fade_v2, "base_spec_fn": spec_weathered_aged, "desc": "UV-destroyed clearcoat"},
    "salt_corroded":    { "base_spec_fn": spec_weathered_aged,"M": 90,  "R": 150, "CC": 120,  "paint_fn": paint_salt_damage, "desc": "Coastal salt air corroded metal"},
    "desert_worn":      { "base_spec_fn": spec_weathered_aged,"M": 40,  "R": 175, "CC": 130,  "paint_fn": paint_desert_sand, "desc": "Sand-blasted desert weathered surface"},
    "acid_rain":        {"M": 70, "R": 130, "CC": 140,  "paint_fn": paint_sun_fade_v2, "base_spec_fn": spec_weathered_aged, "desc": "Chemical rain etched paint damage"},
    "oxidized_copper":  { "base_spec_fn": spec_weathered_aged,"M": 145, "R": 100, "CC": 120,  "paint_fn": paint_heavy_patina, "desc": "Fully green-oxidized copper (Statue of Liberty)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 30},
    "vintage_chrome":   { "base_spec_fn": spec_weathered_aged,"M": 230, "R": 25,  "CC": 50,  "paint_fn": paint_vintage_haze, "desc": "1950s chrome with cloudy oxidation spots"},
})

EXPANSION_BASES.update({
    # Group 11: OEM AUTOMOTIVE (new entries)
    "factory_basecoat": {"M": 140, "R": 30, "CC": 16, "paint_fn": paint_oem_metallic_v2, "base_spec_fn": spec_oem_automotive, "desc": "Pristine factory metallic clearcoat"},
    "showroom_clear":   {"M": 10, "R": 5, "CC": 16, "paint_fn": paint_oem_metallic_v2, "base_spec_fn": spec_oem_automotive, "desc": "Showroom polished clearcoat", "noise_M": 5, "noise_R": 5},
    "fleet_white":      {"M": 0, "R": 30, "CC": 16, "paint_fn": paint_matte_wrap_v2, "base_spec_fn": spec_oem_automotive, "desc": "Basic fleet gloss white"},
    "taxi_yellow":      {"M": 0, "R": 35, "CC": 16, "paint_fn": paint_oem_metallic_v2, "base_spec_fn": spec_oem_automotive, "desc": "Commercial cab yellow"},
    "school_bus":       {"M": 0, "R": 40, "CC": 16, "paint_fn": _paint_noop, "base_spec_fn": spec_oem_automotive, "_resolve_paint_fn": "paint_electric_blue_tint", "desc": "High-visibility fluorescent polymer polymer"},
    "fire_engine":      { "base_spec_fn": spec_oem_automotive,"M": 5,   "R": 15,  "CC": 16, "paint_fn": paint_fire_engine_gloss, "desc": "Deep wet fire apparatus red gloss",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 5, "noise_R": 6},
    "ambulance_white":  { "base_spec_fn": spec_oem_automotive,"M": 0,   "R": 30,  "CC": 16, "paint_fn": paint_reflective_coat, "desc": "High-visibility emergency white reflective",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 8, "noise_R": 10},
    "police_black":     { "base_spec_fn": spec_oem_automotive,"M": 5,   "R": 8,   "CC": 16, "paint_fn": paint_police_deepblack, "desc": "Law enforcement glossy black",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.25, "perlin_lacunarity": 2.0, "noise_M": 3, "noise_R": 4},
    "dealer_pearl":     { "base_spec_fn": spec_oem_automotive,"M": 110, "R": 28,  "CC": 16, "paint_fn": paint_dealer_sparkle, "desc": "Dealer premium tri-coat pearl upgrade",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 12},
    # Group 12: CARBON & COMPOSITE (new entries)
    "carbon_base":      {"M": 100, "R": 60,  "CC": 16,  "paint_fn": paint_carbon_weave_base, "desc": "Raw exposed carbon fiber base material",
                         "base_spec_fn": _base_spec_carbon_weave},
    "kevlar_base":      {"M": 80,  "R": 90,  "CC": 180,  "paint_fn": paint_kevlar_base_fn, "desc": "Ballistic kevlar aramid fiber base",
                         "base_spec_fn": _base_spec_kevlar_weave},
    "fiberglass":       {"M": 30,  "R": 80,  "CC": 30,  "paint_fn": paint_fiberglass_gel_fn, "desc": "Raw fiberglass gelcoat semi-gloss",
                         "base_spec_fn": _base_spec_fiberglass},
    "carbon_ceramic":   {"M": 110, "R": 40,  "CC": 120,  "paint_fn": paint_carbon_ceramic_fn, "desc": "Brake rotor carbon-ceramic composite",
                         "base_spec_fn": _base_spec_carbon_ceramic},
    "aramid":           {"M": 70,  "R": 95,  "CC": 100,  "paint_fn": paint_aramid_weave_fn, "desc": "Woven aramid fiber natural gold-tan",
                         "base_spec_fn": _base_spec_aramid},
    "graphene":         {"M": 180, "R": 20,  "CC": 16,  "paint_fn": paint_graphene_sheen_fn, "desc": "Single-layer graphene ultra-thin metallic",
                         "base_spec_fn": _base_spec_graphene},
    "forged_composite": {"M": 90,  "R": 70,  "CC": 16,  "paint_fn": paint_forged_composite_fn, "desc": "Lamborghini-style forged carbon composite",
                         "base_spec_fn": _base_spec_forged_composite},
    "hybrid_weave":     {"M": 95,  "R": 55,  "CC": 16,  "paint_fn": paint_hybrid_weave_fn, "desc": "Carbon-kevlar hybrid bi-weave material",
                         "base_spec_fn": _base_spec_hybrid_weave},
    # Group 13: PREMIUM LUXURY (new entries - satin_gold already exists)
    "bentley_silver":   {"M": 250, "R": 4, "CC": 16, "paint_fn": paint_bentley_silver_v2, "base_spec_fn": spec_premium_luxury, "desc": "Bespoke ultra-fine silver luxury finish"},
    "ferrari_rosso":    { "base_spec_fn": spec_premium_luxury,"M": 80, "R": 80, "CC": 30, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_fine_sparkle", "desc": "Surface cooling magma with deep incandescent red subsurface scattering", "noise_scales": [2, 4, 8], "noise_M": 100, "noise_R": 100},
    "lamborghini_verde":{ "base_spec_fn": spec_premium_luxury,"M": 70,  "R": 12,  "CC": 16, "paint_fn": paint_lambo_verde_shift, "desc": "Lamborghini Verde Mantis electric green"},
    "porsche_pts":      {"M": 80, "R": 15, "CC": 16, "paint_fn": paint_bentley_silver_v2, "base_spec_fn": spec_premium_luxury, "desc": "Porsche Paint-to-Sample custom deep coat"},
    "mclaren_orange":   { "base_spec_fn": spec_premium_luxury,"M": 50,  "R": 10,  "CC": 16, "paint_fn": paint_mclaren_vivid, "desc": "McLaren Papaya Spark vivid orange"},
    "bugatti_blue":     { "base_spec_fn": spec_premium_luxury,"M": 120, "R": 8,   "CC": 16, "paint_fn": paint_bugatti_blue_layer, "desc": "Bugatti Bleu de France deep two-tone"},
    "koenigsegg_clear": { "base_spec_fn": spec_premium_luxury,"M": 130, "R": 5,   "CC": 16, "paint_fn": paint_koenigsegg_clear_weave, "desc": "Clear carbon visible weave (Koenigsegg style)"},
    "pagani_tricolore": { "base_spec_fn": spec_premium_luxury,"M": 160, "R": 15,  "CC": 16, "paint_fn": paint_tricolore_shift, "desc": "Pagani tricolore - premium three-tone angle-resolved shift: sapphire blue shadows, amethyst mid, bronze gold highlights"},
    "maybach_two_tone": { "base_spec_fn": spec_premium_luxury,"M": 100, "R": 15,  "CC": 16, "paint_fn": paint_maybach_split, "desc": "Mercedes-Maybach duo-tone luxury split"},
    # Group 14: SHOKK SERIES (new entries - plasma_metal etc already exist)
    "shokk_pulse":      {"M": 220, "R": 15,  "CC": 16, "paint_fn": paint_pulse_electric, "desc": "Electric pulse wave metallic - Shokker signature"},
    "shokk_venom":      {"M": 210, "R": 20,  "CC": 16, "paint_fn": paint_venom_acid, "desc": "Toxic acid green-yellow metallic reactive"},
    "shokk_blood":      {"M": 190, "R": 25,  "CC": 16, "paint_fn": paint_blood_red_deep, "desc": "Deep arterial red metallic with dark edge"},
    "shokk_void":       {"M": 10,  "R": 240, "CC": 230,  "paint_fn": paint_void_absorb, "desc": "Near-vantablack with subtle edge shimmer"},
    "shokk_static":     {"M": 200, "R": 30,  "CC": 16,  "paint_fn": paint_static_grain, "desc": "Crackling static interference metallic"},
    # Group 15: EXTREME & EXPERIMENTAL (new entries)
    "quantum_black":    {"M": 0, "R": 255, "CC": 240, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_quantum_black", "base_spec_fn": spec_quantum_black, "desc": "100% absorbing void material"},
    "neutron_star":     { "base_spec_fn": spec_black_hole_accretion,"M": 0, "R": 255, "CC": 255, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_black_hole_accretion", "desc": "Total void black sink surrounded by an intense glowing ring of orbital light reflection", "noise_scales": [2], "noise_R": 250},
    "plasma_core":      { "base_spec_fn": spec_plasma_core,"M": 220, "R": 8,   "CC": 30,  "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_plasma_core", "desc": "Glowing subatomic plasma core material"},
    "dark_matter":      {"M": 30,  "R": 230, "CC": 220,  "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_dark_matter", "desc": "Ultra-dark with hidden angle-dependent reveal",
                         "base_spec_fn": spec_dark_matter},
    "superconductor":   { "base_spec_fn": spec_absolute_zero,"M": 255, "R": 90, "CC": 40, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_absolute_zero", "desc": "Heavily frosted metal sitting indefinitely at absolute zero, perpetually generating micro-ice", "noise_scales": [8, 16, 32], "noise_R": 90},
    "bioluminescent":   {"M": 60,  "R": 40,  "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_bioluminescent", "desc": "Deep sea organism soft glow finish",
                         "base_spec_fn": spec_bioluminescent},
    "solar_panel":      { "base_spec_fn": spec_solar_panel,"M": 15,  "R": 45,  "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_solar_panel", "desc": "Photovoltaic solar cell dark blue-black"},
    "holographic_base": { "base_spec_fn": spec_holographic_base,"M": 200, "R": 6,   "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_holographic_base", "desc": "Full holographic rainbow prismatic base"},
    # Group 16: PARADIGM CROSSOVER (bases listed in paradigm groups but need rendering path)
    "carbon_weave":     {"M": 70,  "R": 35,  "CC": 16, "paint_fn": paint_carbon_weave,    "desc": "Carbon weave - visible diagonal twill weave carbon fiber pattern under coat",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 15},
    "nebula":           {"M": 0,   "R": 25,  "CC": 16, "paint_fn": paint_opal_fire,        "desc": "Nebula - space dust cloud, purple-blue cosmic nebula with star sparkles",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 20},
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
    """Elder Futhark rune shape - vertical stave with angled branches."""
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
    """Pentagram - five-pointed star drawn as LINE STROKES connecting every other
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
    """Nanoweave - microscopic tight twill weave at 2-3px scale."""
    h, w = shape
    y, x = _get_mgrid(shape)
    rng = np.random.RandomState(seed)
    size = 3  # nano-scale cell
    # Twill pattern: diagonal offset checker
    row_shift = (y // size).astype(int)
    checker = ((y // size + x // size + row_shift) % 2).astype(np.float32)
    # Thread profiles: over-threads raised, under-threads recessed
    ty = np.sin((y % size) * np.pi / size)
    tx = np.sin((x % size) * np.pi / size)
    over = ty * 0.85 + 0.15
    under = tx * 0.12
    weave = np.where(checker > 0.5, over, under)
    # Micro-variation to break perfect grid
    noise = rng.rand(h // 2 + 1, w // 2 + 1).astype(np.float32)
    from PIL import Image as _Im
    noise_up = np.array(_Im.fromarray((noise * 255).astype(np.uint8)).resize((int(w), int(h)), _Im.BILINEAR), dtype=np.float32) / 255.0
    weave = weave * (0.9 + noise_up * 0.1)
    return np.clip(weave, 0, 1).astype(np.float32)
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
    """Rivet grid - raised dome-head rivets with beveled edges in a regular grid."""
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
    """Perforated metal - circular holes punched through sheet with beveled edges."""
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
    """Grating - parallel flat bars with gaps showing depth shadows between them."""
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
    """Roll cage - thick structural tube grid with cylindrical shading."""
    h, w = shape
    scale = min(h, w) / 256.0
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    cell = 45 * scale  # ~45px cells
    bar_half = 5.0 * scale  # ~10px wide bars
    ly = yf % cell
    lx = xf % cell
    # Distance from nearest horizontal bar (at cell edges)
    dy_bar = np.minimum(ly, cell - ly)
    # Distance from nearest vertical bar (at cell edges)
    dx_bar = np.minimum(lx, cell - lx)
    # Cylindrical shading: bright center fading to dark edges
    h_bar = np.where(dy_bar < bar_half,
                     np.sqrt(np.clip(1.0 - (dy_bar / bar_half) ** 2, 0, 1)),
                     0.0).astype(np.float32)
    v_bar = np.where(dx_bar < bar_half,
                     np.sqrt(np.clip(1.0 - (dx_bar / bar_half) ** 2, 0, 1)),
                     0.0).astype(np.float32)
    # At intersections, use the brighter of the two bars
    bars = np.maximum(h_bar, v_bar)
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
    """Coral reef - branching coral structures with rounded polyp tips."""
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
    """Herringbone - alternating V-shaped zigzag rows."""
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
    """Argyle - overlapping diamonds with thin diagonal lines."""
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
    """Greek key - classic meander/labyrinth border pattern."""
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
    """Art deco - repeating fan/arch pattern with radiating lines."""
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
    """Tessellation - hexagonal honeycomb tiling."""
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
    """Racing stripe - wide center stripe with thin flanking stripes."""
    h, w = shape
    y, x = _get_mgrid(shape)
    xf = x.astype(np.float32)
    center = w / 2.0
    main = np.clip(1.0 - np.abs(xf - center) / 12.0, 0, 1)
    flank1 = np.clip(1.0 - np.abs(xf - center - 24) / 4.0, 0, 1)
    flank2 = np.clip(1.0 - np.abs(xf - center + 24) / 4.0, 0, 1)
    return np.clip(main + flank1 * 0.7 + flank2 * 0.7, 0, 1)
def texture_starting_grid(shape, seed):
    """Starting grid - numbered box positions like race start."""
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
    """Tire smoke - dense smoke cloud covering full canvas, thicker at bottom."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Layer 1: Ambient smoke haze - full canvas coverage
    haze = _multi_scale_noise(shape[:2], [16, 32, 64], [0.3, 0.4, 0.3], seed + 4)
    haze = (haze - haze.min()) / (haze.max() - haze.min() + 1e-8)
    rise_factor = np.clip(1.0 - yi / h, 0, 1)  # 1 at bottom, 0 at top
    out = haze * (0.08 + rise_factor * 0.12)  # haze stronger at bottom
    # Layer 2: Smoke plumes - wider, scaled to canvas
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
    """Pit lane - alternating thick horizontal bands with diagonal hash/chevron marks."""
    h, w = shape
    scale = min(h, w) / 256.0
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed)
    band_h = 40 * scale  # thick band height
    gap_h = 30 * scale   # gap between bands
    period = band_h + gap_h
    band_y = yf % period
    in_band = (band_y < band_h).astype(np.float32)
    # Alternating band brightness
    band_idx = (yf // period).astype(int)
    alt = ((band_idx % 2) == 0).astype(np.float32)
    base_band = in_band * (alt * 0.6 + (1 - alt) * 0.35)
    # Diagonal hash marks within bands (chevron/speed-limit feel)
    hash_spacing = 20 * scale
    diag = (xf + yf * 0.7) % hash_spacing
    hash_line = np.clip(1.0 - np.abs(diag - hash_spacing * 0.5) / (hash_spacing * 0.12), 0, 1)
    hash_marks = hash_line * in_band * 0.5
    # Edge border lines
    edge_l = np.clip(1.0 - xf / (3.0 * scale), 0, 1) * 0.7
    edge_r = np.clip(1.0 - (w - 1 - xf) / (3.0 * scale), 0, 1) * 0.7
    # Center dashed speed limit line
    center = np.clip(1.0 - np.abs(xf - w / 2.0) / (2.0 * scale), 0, 1)
    dashes = ((yf % (24 * scale)) < (14 * scale)).astype(np.float32)
    center_line = center * dashes * 0.6
    return np.clip(base_band + hash_marks + edge_l + edge_r + center_line, 0, 1).astype(np.float32)
def texture_lap_counter(shape, seed):
    """Lap counter - vertical strips with sequentially varying intensities like counting sectors."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    scale = min(h, w) / 256.0
    # Vertical sector strips
    n_sectors = rng.randint(8, 16)
    strip_w = w / n_sectors
    sector_idx = np.clip((xf / strip_w).astype(int), 0, n_sectors - 1)
    # Each sector has a slightly different intensity/pattern
    sector_intensities = rng.uniform(0.2, 0.9, n_sectors).astype(np.float32)
    out = np.zeros((h, w), dtype=np.float32)
    for i in range(n_sectors):
        mask = (sector_idx == i).astype(np.float32)
        # Base intensity ramps up across sectors (like counting laps)
        base = sector_intensities[i] * (0.4 + 0.6 * i / n_sectors)
        out += mask * base
    # Sector divider lines
    local_x = xf % strip_w
    divider = np.clip(1.0 - np.abs(local_x) / (2.0 * scale), 0, 1) * 0.6
    divider += np.clip(1.0 - np.abs(local_x - strip_w) / (2.0 * scale), 0, 1) * 0.6
    # Horizontal tick marks within each sector (like counter notches)
    tick_spacing = 20 * scale
    tick = np.clip(1.0 - np.abs(yf % tick_spacing) / (1.5 * scale), 0, 1) * 0.3
    return np.clip(out + divider + tick, 0, 1).astype(np.float32)
def texture_sponsor_fade(shape, seed):
    """Sponsor fade - horizontal gradient bands at different y positions, like fading sponsor logos."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    out = np.zeros((h, w), dtype=np.float32)
    # Multiple horizontal fade bands at random y positions
    n_bands = rng.randint(4, 8)
    for _ in range(n_bands):
        band_y = rng.uniform(0, h)
        band_h = rng.uniform(h * 0.04, h * 0.12)
        intensity = rng.uniform(0.4, 0.9)
        # Fade direction: left-to-right or right-to-left
        direction = 1.0 if rng.rand() > 0.5 else -1.0
        fade_start = rng.uniform(0.1, 0.4)
        fade_end = rng.uniform(0.6, 0.95)
        # Vertical band mask
        v_mask = np.exp(-((yf - band_y)**2) / (2 * band_h**2))
        # Horizontal gradient
        norm_x = xf / w
        if direction < 0:
            norm_x = 1.0 - norm_x
        h_grad = np.clip((norm_x - fade_start) / (fade_end - fade_start), 0, 1)
        # Bright on one side, fading to transparent
        out += v_mask * (1.0 - h_grad) * intensity
    return np.clip(out, 0, 1).astype(np.float32)
def texture_rooster_tail(shape, seed):
    """Rooster tail - fan-shaped directional spray/splash radiating upward from points."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    # Multiple spray sources along bottom
    n_sources = rng.randint(2, 5)
    for _ in range(n_sources):
        sx = rng.uniform(w * 0.15, w * 0.85)
        sy = h * rng.uniform(0.85, 0.98)
        angle = np.arctan2(sy - yf, xf - sx)
        dist = np.sqrt((yf - sy)**2 + (xf - sx)**2)
        # Fan cone pointing upward (angle near 0 = pointing up)
        fan_width = rng.uniform(0.8, 1.4)
        angle_mask = np.clip(1.0 - np.abs(angle) / fan_width, 0, 1)
        # Radial spray streaks
        n_streaks = rng.randint(20, 40)
        streaks = np.sin(angle * n_streaks + dist * 0.03) * 0.5 + 0.5
        streaks = (streaks > 0.6).astype(np.float32)
        # Distance fade — spray dissipates
        max_reach = h * rng.uniform(0.5, 0.9)
        dist_fade = np.clip(1.0 - dist / max_reach, 0, 1)
        # Splatter droplets
        intensity = rng.uniform(0.4, 0.8)
        spray = streaks * angle_mask * dist_fade * intensity
        out += spray
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed) * 0.5 + 0.5
    return np.clip(out * 0.7 + noise * 0.15, 0, 1).astype(np.float32)
def texture_victory_confetti(shape, seed):
    """Scattered confetti pieces - small rectangles at random rotations and sizes."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0
    out = np.zeros((h, w), dtype=np.float32)
    n_pieces = max(150, int(300 * scale))
    for _ in range(n_pieces):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        # Various sizes - some small squares, some elongated rectangles
        pw = rng.uniform(2, 8) * scale
        ph = rng.uniform(4, 16) * scale
        if rng.rand() > 0.5:
            pw, ph = ph, pw  # mix orientations
        angle = rng.uniform(0, np.pi)
        brightness = rng.uniform(0.4, 1.0)
        m = int(max(pw, ph) * 0.8) + 2
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dx, dy = lx - cx, ly - cy
        # Rotate into confetti piece local coords
        cos_a, sin_a = np.cos(-angle), np.sin(-angle)
        rdx = dx * cos_a - dy * sin_a
        rdy = dx * sin_a + dy * cos_a
        inside = (np.abs(rdx) < pw * 0.5) & (np.abs(rdy) < ph * 0.5)
        out[y0:y1, x0:x1] = np.where(inside, np.maximum(out[y0:y1, x0:x1], brightness), out[y0:y1, x0:x1])
    return np.clip(out, 0, 1).astype(np.float32)

def texture_trophy_laurel(shape, seed):
    """Trophy laurel - wreath of leaf shapes in oval arrangement."""
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
    """RPM gauge - concentric tachometer arcs with tick marks and intensity zones."""
    h, w = shape
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    scale = min(h, w) / 256.0
    cell = int(100 * scale)
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell * 0.55, cell / 2.0
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    # Gauge sweep: upper 240 degrees (from -210 to +30 degrees)
    a_start, a_end = -np.pi + 0.5, -0.5
    arc_mask = ((angle > a_start) & (angle < a_end)).astype(np.float32)
    # Main arc band
    arc_r = cell * 0.38
    arc_w = 3.5 * scale
    arc = np.clip(1.0 - np.abs(dist - arc_r) / arc_w, 0, 1) * arc_mask
    # Inner arc (second ring)
    inner_r = cell * 0.30
    inner_arc = np.clip(1.0 - np.abs(dist - inner_r) / (arc_w * 0.6), 0, 1) * arc_mask * 0.4
    # Tick marks radiating from center
    n_ticks = 12
    tick_angles = np.linspace(a_start, a_end, n_ticks + 1)
    ticks = np.zeros_like(dist)
    for ta in tick_angles:
        a_diff = np.abs(angle - ta)
        tick_line = (a_diff < 0.03).astype(np.float32)
        tick_range = ((dist > cell * 0.28) & (dist < cell * 0.42)).astype(np.float32)
        ticks += tick_line * tick_range * 0.7
    # Intensity zones: green (low rpm) to red (high rpm)
    # Map angle to 0-1 across the sweep
    sweep_frac = np.clip((angle - a_start) / (a_end - a_start), 0, 1)
    # Redline zone (last 20% of sweep)
    redline = (sweep_frac > 0.8).astype(np.float32) * arc_mask * 0.3
    zone_intensity = sweep_frac * 0.3 * arc_mask * (dist > cell * 0.26).astype(np.float32) * (dist < cell * 0.44).astype(np.float32)
    return np.clip(arc + inner_arc + ticks + redline + zone_intensity, 0, 1).astype(np.float32)
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
    """Brake dust - very fine directional speckle with radial density gradient."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    # Very fine particles — smaller than metal flake
    n_particles = int(h * w * 0.012)  # dense coverage
    px = rng.randint(0, w, n_particles)
    py = rng.randint(0, h, n_particles)
    # Density gradient: heavier toward bottom-right (like dust thrown from spinning wheel)
    cx, cy = w * 0.3, h * 0.3
    max_dist = np.sqrt(cx**2 + cy**2) * 1.5
    particle_dist = np.sqrt((px - cx)**2 + (py - cy)**2)
    # Particles more likely to survive farther from origin (dust accumulates at edges)
    keep_prob = np.clip(particle_dist / max_dist, 0.15, 1.0)
    keep = rng.rand(n_particles) < keep_prob
    px, py = px[keep], py[keep]
    # Each particle is 1-2px, very fine
    for i in range(len(px)):
        sz = 1 if rng.rand() < 0.7 else 2
        brightness = rng.uniform(0.3, 0.9)
        y0, y1 = py[i], min(h, py[i] + sz)
        x0, x1 = px[i], min(w, px[i] + sz)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], brightness)
    # Slight radial streaking from center (spinning wheel effect)
    y, x = _get_mgrid(shape)
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    angle = np.arctan2(yf - cy, xf - cx)
    radial_streak = np.sin(angle * 40) * 0.08
    return np.clip(out + radial_streak, 0, 1).astype(np.float32)

def texture_drift_marks(shape, seed):
    """Lateral rubber drift smear marks - curved arcing streaks across surface."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0
    out = np.zeros((h, w), dtype=np.float32)
    # Multiple overlapping lateral arc paths
    n_arcs = max(15, int(30 * scale))
    for _ in range(n_arcs):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        radius = rng.uniform(40, 150) * scale
        arc_w = rng.uniform(3, 8) * scale  # rubber smear width
        a_start = rng.uniform(0, 2 * np.pi)
        a_span = rng.uniform(0.8, 2.5)  # longer arcs for drift feel
        brightness = rng.uniform(0.3, 0.85)
        m = int(radius + arc_w * 3) + 2
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((lx - cx) ** 2 + (ly - cy) ** 2)
        angle = np.arctan2(ly - cy, lx - cx)
        a_norm = ((angle - a_start) % (2 * np.pi))
        in_arc = (a_norm < a_span).astype(np.float32)
        # Fade at arc ends for natural taper
        fade = np.clip(np.minimum(a_norm, a_span - a_norm) / 0.3, 0, 1)
        ring = np.exp(-((dist - radius) ** 2) / (2 * arc_w ** 2))
        out[y0:y1, x0:x1] += ring * in_arc * fade * brightness
    return np.clip(out, 0, 1).astype(np.float32)

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
        length = int(rng.randint(40, max(41, min(300, w))) * scale)
        thickness = max(1, int(rng.randint(1, 3) * scale))
        brightness = rng.uniform(0.4, 1.0)
        y0, y1 = max(0, sy), min(h, sy + thickness)
        x0, x1 = sx, min(w, sx + length)
        if y1<=y0 or x1<=x0: continue
        fade = np.linspace(1.0, 0.0, x1-x0, dtype=np.float32).reshape(1, -1)
        result[y0:y1, x0:x1] = np.maximum(result[y0:y1, x0:x1], brightness * fade)
    return result

def texture_track_map(shape, seed):
    """Track map - racing circuit layout with curving road, edge lines, and corners."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    scale = min(h, w) / 256.0
    cell = int(120 * scale)
    ly = yf % cell
    lx = xf % cell
    cy, cx = cell / 2.0, cell / 2.0
    # Irregular track shape using superellipse with angle-varying radius
    angle = np.arctan2(ly - cy, lx - cx)
    # Base oval with bumps for corners (like a real circuit, not a perfect oval)
    r_base = cell * 0.38
    r_vary = cell * 0.06 * np.sin(angle * 3 + 0.5) + cell * 0.04 * np.sin(angle * 5 + 1.2)
    target_r = r_base + r_vary
    dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
    norm_d = dist / target_r
    # Road surface (track width)
    road_w = cell * 0.06
    road = np.clip(1.0 - np.abs(dist - target_r) / road_w, 0, 1) * 0.6
    # Edge lines (curb markings)
    outer_edge = np.clip(1.0 - np.abs(dist - (target_r + road_w * 0.8)) / (1.5 * scale), 0, 1) * 0.9
    inner_edge = np.clip(1.0 - np.abs(dist - (target_r - road_w * 0.8)) / (1.5 * scale), 0, 1) * 0.9
    # Start/finish line (short perpendicular mark)
    sf_angle = np.abs(angle - 0.0)
    sf_line = (sf_angle < 0.04).astype(np.float32) * road * 0.8
    return np.clip(road + outer_edge + inner_edge + sf_line, 0, 1).astype(np.float32)
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
    """Velvet - soft nap texture with directional pile and subtle sheen variation."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xf = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Very fine fiber nap (tiny scale noise)
    nh, nw = max(1, h // 3 + 1), max(1, w // 3 + 1)
    fine = rng.rand(nh, nw).astype(np.float32)
    nap = np.repeat(np.repeat(fine, 3, 0), 3, 1)[:h, :w] * 0.2
    # Directional pile - subtle diagonal brushed direction
    pile = np.sin((xf + yf * 0.7) * 0.3) * 0.08 + 0.5
    # Sheen variation - larger scale light/dark areas from pile angle
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
    """Binary code - columns of 0/1 bit blocks streaming down.
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
    """QR code - 8x8px grid of on/off blocks with 3 corner finder patterns."""
    h, w = shape
    rng = np.random.RandomState(seed)
    cell = max(8, min(h, w) // 30)
    gh, gw = max(1, h // cell + 1), max(1, w // cell + 1)
    # Random on/off blocks
    blocks = (rng.rand(gh, gw) > 0.5).astype(np.float32)
    result = np.repeat(np.repeat(blocks, cell, axis=0), cell, axis=1)[:h, :w]
    y, x = _get_mgrid(shape)
    yi = y.astype(int)
    xi = x.astype(int)
    # 3 corner finder patterns (7x7 cell concentric squares)
    for gy, gx in [(0, 0), (0, max(0, gw - 7)), (max(0, gh - 7), 0)]:
        py, px = gy * cell, gx * cell
        in_y = (yi >= py) & (yi < min(h, py + 7 * cell))
        in_x = (xi >= px) & (xi < min(w, px + 7 * cell))
        fy = np.clip((yi - py) // cell, 0, 6)
        fx = np.clip((xi - px) // cell, 0, 6)
        outer = in_y & in_x
        ring1 = outer & (fy >= 1) & (fy <= 5) & (fx >= 1) & (fx <= 5)
        core = outer & (fy >= 2) & (fy <= 4) & (fx >= 2) & (fx <= 4)
        result = np.where(outer, 1.0, result)
        result = np.where(ring1, 0.0, result)
        result = np.where(core, 1.0, result)
    return result.astype(np.float32)
def texture_pixel_grid(shape, seed):
    """Pixel grid - blocky mosaic of random colored blocks.
    Cell size scales with resolution."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # ~20 pixel blocks across shortest dimension
    cell = max(8, min(h, w) // 20)
    gh, gw = max(1, -(-h // cell)), max(1, -(-w // cell))
    # Random brightness per pixel block
    blocks = rng.rand(gh, gw).astype(np.float32)
    result = np.repeat(np.repeat(blocks, cell, axis=0), cell, axis=1)[:h, :w]
    # Add grid lines between blocks (scaled width)
    y, x = np.mgrid[0:h, 0:w]
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
    """WiFi waves - concentric arc signal waves from corner."""
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

# --- NEW METALLIC STANDARD FLAKE BASES (8 new entries added in HTML v0.3.x) ---
# These mirror the HTML swatch renderers added to the Metallic Standard category.
# Using paint_coarse_flake (same as metal_flake_base) as the paint physics base.
EXPANSION_BASES.update({
    "champagne_flake":      {"M": 255, "R": 0, "CC": 16, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_warm_metal", "desc": "A hyper-reflective pure 24K gold with absolute 0 roughness and high metal flake scaling", "noise_scales": [1, 2], "noise_M": 50},
    "fine_silver_flake":    {"M": 0, "R": 5, "CC": 150, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_diamond_sparkle", "desc": "A dielectric clear thick resin suspending pure crushed silver mica shards", "noise_scales": [8, 16], "noise_M": 150},
    "blue_ice_flake":       {"M": 200, "R": 5, "CC": 100, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_ice_cracks", "desc": "Jagged frozen ice fractals catching deep light in a frozen state", "perlin": True, "perlin_octaves": 5, "noise_M": -50, "noise_R": 60},
    "bronze_flake":         {"M": 100, "R": 120, "CC": 100, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_patina_green", "desc": "10,000-year oxidized shipwreck brass, aggressively dripping with rich verdigris", "perlin": True, "perlin_octaves": 4, "noise_R": 100},
    "green_flake":          {"M": 180, "R": 20, "CC": 50, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_interference_shift", "desc": "Dark space meteorite that fades to an intense glowing neon green at its specular angles", "noise_scales": [2, 4], "noise_M": 100},
    "fire_flake":           {"M": 220, "R": 80, "CC": 20, "paint_fn": _paint_noop, "_resolve_paint_fn": "paint_burnt_metal", "desc": "The violent surface of the sun exploding with massive bright spots of solar plasma", "perlin": True, "perlin_octaves": 3, "noise_M": 150, "noise_R": 50},
})
def texture_glitch_scan(shape, seed):
    """Glitch scanlines - horizontal lines with shifted pixel chunks for digital corruption."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Base gradient as source image to shift
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    base = (xf / w * 0.5 + yf / h * 0.5).astype(np.float32)
    result = base.copy()
    # Scanlines
    scan_period = max(2, h // 200)
    scanlines = ((y % scan_period) == 0).astype(np.float32) * 0.15
    # Horizontal displacement glitch blocks
    num_glitches = max(40, h // 12)
    for _ in range(num_glitches):
        gy = rng.randint(0, h)
        block_h = rng.randint(max(1, h // 400), max(3, h // 60))
        shift = rng.randint(-w // 4, w // 4)
        brightness_mod = rng.uniform(0.3, 1.0)
        y1, y2 = max(0, gy), min(h, gy + block_h)
        if y1 >= y2:
            continue
        # Shift the row pixels horizontally
        row_block = result[y1:y2, :].copy()
        shifted = np.roll(row_block, shift, axis=1)
        result[y1:y2, :] = shifted * brightness_mod
    # Add horizontal banding artifacts
    band_noise = rng.rand(h, 1).astype(np.float32) * 0.2
    result += np.broadcast_to(band_noise, (h, w))
    return np.clip(result + scanlines, 0, 1).astype(np.float32)

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
    """Sandstorm - directional stretched noise with dune shapes and fine grain."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    # Large-scale dune shapes: noise stretched along wind direction (horizontal)
    dune_h = max(1, h // 6)
    dune_w = max(1, w // 32)
    dune_noise = rng.rand(dune_h, dune_w).astype(np.float32)
    from PIL import Image
    dune_img = Image.fromarray((dune_noise * 255).clip(0, 255).astype(np.uint8))
    dune_img = dune_img.resize((int(w), int(h)), Image.BILINEAR)
    dunes = np.array(dune_img).astype(np.float32) / 255.0
    # Medium-scale sand ripples: also stretched
    mid_h = max(1, h // 16)
    mid_w = max(1, w // 8)
    mid_noise = rng.rand(mid_h, mid_w).astype(np.float32)
    mid_img = Image.fromarray((mid_noise * 255).clip(0, 255).astype(np.uint8))
    mid_img = mid_img.resize((int(w), int(h)), Image.BILINEAR)
    ripples = np.array(mid_img).astype(np.float32) / 255.0
    # Fine grain: dense small noise
    fine = rng.rand(h, w).astype(np.float32)
    # Combine: large dunes + medium ripple + fine grain
    out = dunes * 0.45 + ripples * 0.35 + fine * 0.20
    mn, mx = out.min(), out.max()
    if mx > mn:
        out = (out - mn) / (mx - mn)
    return out.astype(np.float32)
def texture_hailstorm(shape, seed):
    """Hailstorm - random circular impact craters with raised rims."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0
    out = np.full((h, w), 0.15, dtype=np.float32)  # base surface level
    for _ in range(int(180 * scale)):
        cy, cx = rng.randint(0, h), rng.randint(0, w)
        r = rng.uniform(3, 10) * scale  # crater radius
        depth = rng.uniform(0.3, 0.85)
        m = int(r * 1.6) + 2
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - cy)**2 + (lx - cx)**2)
        norm_d = dist / r
        # Crater profile: dip in center, raised rim at edge
        # Inside crater: bowl shape going down
        crater_inside = np.clip(1.0 - norm_d, 0, 1) * depth
        # Raised rim: ring just outside crater radius
        rim = np.exp(-((norm_d - 1.0)**2) / (2 * 0.08**2)) * depth * 0.5
        crater = rim - crater_inside
        out[y0:y1, x0:x1] += crater
    return np.clip(out, 0, 1).astype(np.float32)

def texture_aurora_bands(shape, seed):
    """Aurora bands - flowing curtain-like bands covering full canvas with shimmer."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Layer 1: Ambient atmospheric shimmer - full canvas coverage
    shimmer = _multi_scale_noise(shape[:2], [16, 32, 64], [0.3, 0.4, 0.3], seed + 6)
    shimmer = (shimmer - shimmer.min()) / (shimmer.max() - shimmer.min() + 1e-8)
    out = shimmer * 0.10
    # Layer 2: Flowing curtain bands - more bands with wider gaussian spread
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
    """Bullet holes - impact craters with raised rim and dark center."""
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
    """Shrapnel - jagged torn metal fragments scattered across surface."""
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
    """Rust bloom - organic rust patches with rough edges and pitting."""
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
    """Peeling paint - curling flakes lifting off surface with exposed underlayer."""
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
    denom = np.maximum(3.0 + (cy - ly) * 0.3, 1e-6)
    top_point = np.clip(1.0 - np.abs(dx) / denom, 0, 1) * (ly < cy - cell * 0.3).astype(np.float32)
    return np.clip(cross + top_point * 0.5, 0, 1).astype(np.float32)
def texture_iron_cross(shape, seed):
    """Iron Cross / Maltese cross - repeating cross with flared arms tiled in grid."""
    h, w = shape
    scale = min(h, w) / 256.0
    y, x = _get_mgrid(shape)
    cell = int(50 * scale)
    if cell < 10:
        cell = 10
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    cy, cx = cell / 2.0, cell / 2.0
    dy = np.abs(ly - cy)
    dx = np.abs(lx - cx)
    arm_len = cell * 0.42
    # Each arm tapers from center then flares at the tip (Maltese cross shape)
    # Vertical arms
    v_t = np.clip(dy / arm_len, 0, 1)  # 0 at center, 1 at tip
    v_width = 3.0 * scale * (0.6 + 0.8 * v_t ** 1.5)  # narrow mid, flared ends
    v_arm = (dx < v_width).astype(np.float32) * (dy < arm_len).astype(np.float32)
    # Horizontal arms
    h_t = np.clip(dx / arm_len, 0, 1)
    h_width = 3.0 * scale * (0.6 + 0.8 * h_t ** 1.5)
    h_arm = (dy < h_width).astype(np.float32) * (dx < arm_len).astype(np.float32)
    # Center disc
    center = (np.sqrt(dx ** 2 + dy ** 2) < 4.0 * scale).astype(np.float32)
    cross = np.maximum(np.maximum(v_arm, h_arm), center)
    return cross.astype(np.float32)

def texture_skull_wings(shape, seed):
    """Affliction-style winged skull with feathered wing arcs."""
    h, w = shape
    y, x = _get_mgrid(shape)
    cell = 80
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    skull = _skull_simple(ly, lx, cell)
    cx = cell / 2.0
    cy_wing = cell * 0.42
    # Symmetrical feathered wings — multiple curved arcs spreading outward
    wings = np.zeros_like(ly)
    for i in range(5):
        # Each feather arc starts near skull center and curves outward/down
        arc_r = cell * (0.22 + i * 0.06)
        droop = cell * 0.02 * i  # feathers droop more as they go outward
        feather_w = max(1.5, 3.0 - i * 0.3)  # outer feathers thinner
        for side in [-1.0, 1.0]:
            # Feather center follows an arc
            arc_cx = cx + side * cell * 0.12
            angle = np.arctan2(ly - (cy_wing + droop), (lx - arc_cx) * side)
            dist = np.sqrt((ly - (cy_wing + droop))**2 + (lx - arc_cx)**2)
            # Only draw in the outward-facing half (wing spread direction)
            angle_mask = ((angle > -2.2) & (angle < 0.5)).astype(np.float32) if side > 0 else ((angle > -0.5) & (angle < 2.2)).astype(np.float32)
            # Arc shape
            arc_val = np.clip(1.0 - np.abs(dist - arc_r) / feather_w, 0, 1) * angle_mask
            # Taper at tips
            taper = np.clip(1.0 - np.abs(angle - (-0.85)) / 1.5, 0, 1)
            wings += arc_val * taper * 0.6
    return np.clip(skull + wings, 0, 1).astype(np.float32)

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
    """EKG heartbeat line - THE SHOKKER SIGNATURE PATTERN."""
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
    """Molecular - atom spheres connected by bond lines in a lattice."""
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
    """Neuron network - cell bodies connected by branching dendrite lines."""
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
    """Tiger stripe - curved horizontal bands that taper, noise-warped for organic feel."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    dim = min(h, w)
    # Multi-scale noise for warping
    noise_block = max(8, dim // 32)
    nh, nw = max(1, h // noise_block + 1), max(1, w // noise_block + 1)
    n1 = rng.rand(nh, nw).astype(np.float32)
    warp_y = np.repeat(np.repeat(n1, noise_block, axis=0), noise_block, axis=1)[:h, :w]
    n2 = rng.rand(nh, nw).astype(np.float32)
    warp_x = np.repeat(np.repeat(n2, noise_block, axis=0), noise_block, axis=1)[:h, :w]
    # Warp coordinates for organic curves
    warped_y = yf + warp_y * 25 + np.sin(xf * 0.03 + warp_x * 4) * 12
    # Multiple stripe frequencies for irregular spacing and varying thickness
    stripe_freq = 0.06 * (256.0 / dim)
    s1 = np.sin(warped_y * stripe_freq * np.pi)
    s2 = np.sin(warped_y * stripe_freq * 0.7 * np.pi + 1.5)
    combined = s1 * 0.6 + s2 * 0.4
    # Soft threshold for varying thickness
    stripes = np.clip(combined * 2.5, -1, 1) * 0.5 + 0.5
    return stripes.astype(np.float32)


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
    """Moire interference fringes from overlapping concentric circles at offset centers."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    dim = float(min(h, w))
    n_centers = rng.randint(2, 4)
    ring_freq = 0.4 * (256.0 / dim)
    patterns = []
    for i in range(n_centers):
        cx = w * rng.uniform(0.2, 0.8)
        cy = h * rng.uniform(0.2, 0.8)
        dist = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
        rings = np.sin(dist * ring_freq * np.pi) * 0.5 + 0.5
        patterns.append(rings)
    moire = patterns[0]
    for p in patterns[1:]:
        moire = moire * p
    moire = (moire - moire.min()) / (moire.max() - moire.min() + 1e-8)
    return np.clip(moire * 1.5, 0, 1).astype(np.float32)

def texture_pixel_mosaic(shape, seed):
    """Retro 8-bit pixel blocks - downscaled noise upscaled to chunky squares."""
    h, w = shape
    rng = np.random.RandomState(seed)
    block = max(4, min(h, w) // 32)
    gh, gw = max(1, -(-h // block)), max(1, -(-w // block))
    grid = rng.rand(gh, gw).astype(np.float32)
    result = np.repeat(np.repeat(grid, block, axis=0), block, axis=1)[:h, :w]
    return result.astype(np.float32)

def texture_caustic_light(shape, seed):
    """Underwater caustic light - overlapping bright sine wave lines at different angles."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(5, 8)):
        angle = rng.uniform(0, np.pi)
        freq = rng.uniform(0.08, 0.25) * (256.0 / dim)
        phase = rng.uniform(0, 2 * np.pi)
        proj = xf * np.cos(angle) + yf * np.sin(angle)
        distort = np.sin(xf * rng.uniform(0.01, 0.04) + rng.uniform(0, 6)) * 8
        distort += np.sin(yf * rng.uniform(0.01, 0.04) + rng.uniform(0, 6)) * 8
        wave = np.sin((proj + distort) * freq * np.pi + phase)
        caustic = np.clip(1.0 - np.abs(wave) * 1.8, 0, 1) ** 2
        out += caustic * rng.uniform(0.15, 0.35)
    mn, mx = out.min(), out.max()
    if mx > mn:
        out = (out - mn) / (mx - mn)
    return np.clip(out, 0, 1).astype(np.float32)

def texture_biomechanical(shape, seed):
    """Biomechanical - Giger-esque organic/mechanical hybrid with tubes, ribs, and conduits."""
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
        # (The compose_finish function handles this differently - pattern_val is passed)
        # For the registry, this just defines how the pattern modulates paint
        for c in range(3):
            noise = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + c * 17)
            paint[:,:,c] = np.clip(paint[:,:,c] - np.abs(noise) * strength * pm * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_emboss_paint_fn(strength=0.08):
    """Factory: pattern embosses - brightens high areas, darkens low."""
    def fn(paint, shape, mask, seed, pm, bb):
        noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 100)
        for c in range(3):
            paint[:,:,c] = np.clip(paint[:,:,c] + noise * strength * pm * mask, 0, 1)
        paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
        return paint
    return fn

def make_contrast_paint_fn(strength=0.12):
    """Factory: pattern adds contrast - used for checks, stripes, etc."""
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
# NOTE: Strength values kept SUBTLE - paint mods should hint at the pattern, not overpower.
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
    """Inferno - raging wall of flames covering entire surface with heat shimmer."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Layer 1: Heat shimmer base - ensures FULL canvas coverage
    heat = _multi_scale_noise(shape[:2], [8, 16, 32], [0.3, 0.4, 0.3], seed + 1)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)
    out = heat * 0.18
    # Layer 2: Dense flame columns - widths scaled to canvas, near-full height
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
    # Layer 3: Hot bottom glow - intense heat at base
    bottom_glow = np.clip(1.0 - yi / (h * 0.25), 0, 1) ** 1.5 * 0.3
    out = np.maximum(out, bottom_glow)
    return np.clip(out, 0, 1)


def texture_fireball(shape, seed):
    """Fireball - explosive spheres with heat radiation covering the full canvas."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    sz = min(h, w)
    # Layer 1: Ambient heat field - full canvas glow
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
    """Hellfire - chaotic meandering fire columns with ambient hellglow covering full canvas."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    # Layer 1: Ambient hell-glow base - full canvas coverage
    heat = _multi_scale_noise(shape[:2], [8, 16, 32], [0.3, 0.4, 0.3], seed + 3)
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-8)
    out = heat * 0.15
    # Bottom heat intensifier
    yi = np.arange(h, dtype=np.float32).reshape(-1, 1)
    bottom_heat = np.clip(1.0 - yi / (h * 0.3), 0, 1) ** 1.5 * 0.2
    out = np.maximum(out, bottom_heat * np.ones((1, w), dtype=np.float32))
    # Layer 2: Meandering fire columns - wider, more numerous
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
    """Wildfire - chaotic spreading fire with turbulent flame edges rising from bottom."""
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
    """Wave curl - horizontal wave bands that curl over at the crest like breaking ocean waves."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    y = np.linspace(0, 1, h).reshape(-1, 1)
    x = np.linspace(0, 1, w).reshape(1, -1)
    for i in range(rng.randint(3, 6)):
        freq = rng.uniform(3, 7)
        phase = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.06, 0.14)
        cy = rng.uniform(0.15, 0.85)
        intensity = rng.uniform(0.5, 0.9)
        # Main wave body
        wave_y = cy + amp * np.sin(freq * x * 2 * np.pi + phase)
        body = np.exp(-((y - wave_y)**2) / (2 * 0.018**2)) * intensity
        # Curl/crest: tight spiral above the wave crest
        curl_center = wave_y - 0.025
        curl_r = 0.018
        # Parametric curl: distance from a small circle above the wave peak
        dy_curl = y - curl_center
        dx_curl = (x * freq * 2 * np.pi + phase) % (2 * np.pi) / (2 * np.pi) * 0.06 - 0.03
        curl_dist = np.sqrt(dy_curl**2 + dx_curl**2)
        curl = np.exp(-((curl_dist - curl_r)**2) / (2 * 0.005**2)) * intensity * 0.7
        # Only show curl above wave crest
        curl_mask = (y < wave_y).astype(np.float32)
        # Foam spray above curl
        foam_y = wave_y - 0.05
        foam = np.exp(-((y - foam_y)**2) / (2 * 0.008**2)) * 0.25 * intensity
        foam_mask = (y < wave_y - 0.02).astype(np.float32)
        out += body + curl * curl_mask + foam * foam_mask
    return np.clip(out, 0, 1).astype(np.float32)


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
    """Skateboard grip tape - dense fine-grained sandpaper with visible grain structure."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    # Multi-scale noise weighted toward high frequency for coarse grit
    fine = rng.rand(h, w).astype(np.float32)
    # Medium grain (2x2 blocks)
    med_h, med_w = max(1, h // 2 + 1), max(1, w // 2 + 1)
    med = np.repeat(np.repeat(rng.rand(med_h, med_w).astype(np.float32), 2, 0), 2, 1)[:h, :w]
    # Coarse grain (4x4 blocks) for visible grain structure
    coarse_h, coarse_w = max(1, h // 4 + 1), max(1, w // 4 + 1)
    coarse = np.repeat(np.repeat(rng.rand(coarse_h, coarse_w).astype(np.float32), 4, 0), 4, 1)[:h, :w]
    # Weight toward high frequency but keep visible grain
    grit = fine * 0.50 + med * 0.30 + coarse * 0.20
    # Normalize to use full range
    grit = (grit - grit.min()) / (grit.max() - grit.min() + 1e-8)
    return grit.astype(np.float32)


def texture_halfpipe(shape, seed):
    """Halfpipe - repeating U-shaped concave arcs like a halfpipe cross-section."""
    import numpy as np
    h, w = shape[:2]
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    scale = min(h, w) / 256.0
    cell_h = int(40 * scale)
    if cell_h < 8:
        cell_h = 8
    # Repeating U-curves vertically
    ly = yf % cell_h
    t = ly / cell_h  # 0 to 1 within each cell
    # U-shape: parabola centered in each cell
    u_curve = 4.0 * (t - 0.5) ** 2  # 0 at center, 1 at edges = U shape
    # Shading: bright on curve walls, dark at bottom
    shading = np.clip(u_curve, 0, 1)
    # Add subtle horizontal stripe at the lip of each pipe
    lip = np.clip(1.0 - np.minimum(t, 1.0 - t) / 0.08, 0, 1) * 0.7
    result = np.maximum(shading, lip)
    return np.clip(result, 0, 1).astype(np.float32)


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
    """Board wax - overlapping circular arc smears from wax rubbing motions."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    out = np.zeros((h, w), dtype=np.float32)
    scale = min(h, w) / 256.0
    # Many overlapping circular arc smears
    for _ in range(rng.randint(50, 100)):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        r = rng.uniform(10, 35) * scale  # radius of circular rub
        arc_start = rng.uniform(0, 2 * np.pi)  # where arc begins
        arc_span = rng.uniform(np.pi * 0.4, np.pi * 1.6)  # how far arc sweeps
        thickness = rng.uniform(1.5, 4.0) * scale  # width of smear
        intensity = rng.uniform(0.25, 0.7)
        m = int(r + thickness + 2)
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((lx - cx)**2 + (ly - cy)**2)
        angle = np.arctan2(ly - cy, lx - cx)
        # Normalize angle to arc range
        a_diff = (angle - arc_start) % (2 * np.pi)
        in_arc = (a_diff < arc_span).astype(np.float32)
        # Ring profile (distance from arc radius)
        ring = np.exp(-((dist - r)**2) / (2 * thickness**2))
        out[y0:y1, x0:x1] += ring * in_arc * intensity
    # Very light surface grain
    out += rng.rand(h, w).astype(np.float32) * 0.08
    return np.clip(out, 0, 1).astype(np.float32)

def texture_tropical_leaf(shape, seed):
    """Large tropical leaves with oval outlines, central midrib, and branching veins."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    scale = min(h, w) / 256.0
    out = np.zeros((h, w), dtype=np.float32)
    n_leaves = rng.randint(3, 7)
    for _ in range(n_leaves):
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        angle = rng.uniform(0, 2 * np.pi)
        leaf_len = rng.uniform(h * 0.2, h * 0.45)
        leaf_wid = rng.uniform(leaf_len * 0.25, leaf_len * 0.4)
        m = int(max(leaf_len, leaf_wid) * 0.7) + 5
        y0, y1 = max(0, cy - m), min(h, cy + m)
        x0, x1 = max(0, cx - m), min(w, cx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dx, dy = lx - cx, ly - cy
        cos_a, sin_a = np.cos(-angle), np.sin(-angle)
        rx = dx * cos_a - dy * sin_a  # along leaf
        ry = dx * sin_a + dy * cos_a  # across leaf
        along = rx / leaf_len
        # Leaf edge tapers at both ends
        edge_taper = np.clip(1.0 - 4.0 * along ** 2, 0, 1)
        across = ry / (leaf_wid * np.maximum(edge_taper, 0.05))
        inside = (np.abs(along) < 0.5) & (np.abs(across) < 0.5)
        # Leaf body - soft oval
        leaf_body = np.exp(-(across ** 2) / 0.25) * np.exp(-(along ** 2) / 0.35) * inside * 0.6
        out[y0:y1, x0:x1] += leaf_body
        # Central midrib - thin bright line along leaf axis
        midrib = np.exp(-(ry ** 2) / (2 * (1.5 * scale) ** 2)) * (np.abs(along) < 0.48) * 0.4
        out[y0:y1, x0:x1] += midrib
        # Branching side veins at ~45 degrees
        n_veins = rng.randint(4, 8)
        for v in range(n_veins):
            vein_pos = (v + 0.5) / n_veins - 0.5  # position along midrib
            vein_angle = 0.6 if v % 2 == 0 else -0.6  # alternate sides
            vein_x = rx - vein_pos * leaf_len
            vein_y = ry - vein_angle * vein_x
            vein_dist = np.abs(vein_y)
            vein_mask = (np.abs(vein_x) < leaf_wid * 0.4) & inside
            vein = np.exp(-(vein_dist ** 2) / (2 * (1.0 * scale) ** 2)) * vein_mask * 0.25
            out[y0:y1, x0:x1] += vein
    return np.clip(out, 0, 1).astype(np.float32)

def texture_rip_tide(shape, seed):
    """Turbulent water currents - domain-warped noise creating flow-like stream patterns."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    y, x = _get_mgrid(shape)
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    dim = float(min(h, w))
    # Domain warping: use noise to distort coordinates, creating flow patterns
    warp_scale = max(1, int(dim) // 16)
    wh, ww = max(1, h // warp_scale + 1), max(1, w // warp_scale + 1)
    from PIL import Image
    wx_small = rng.randn(wh, ww).astype(np.float32)
    wy_small = rng.randn(wh, ww).astype(np.float32)
    wx_img = Image.fromarray(((wx_small - wx_small.min()) / (wx_small.max() - wx_small.min() + 1e-8) * 255).clip(0, 255).astype(np.uint8))
    wy_img = Image.fromarray(((wy_small - wy_small.min()) / (wy_small.max() - wy_small.min() + 1e-8) * 255).clip(0, 255).astype(np.uint8))
    wx = np.array(wx_img.resize((int(w), int(h)), Image.BILINEAR)).astype(np.float32) / 255.0 - 0.5
    wy = np.array(wy_img.resize((int(w), int(h)), Image.BILINEAR)).astype(np.float32) / 255.0 - 0.5
    # Warp coordinates
    warp_amt = dim * 0.15
    xw = xf + wx * warp_amt
    yw = yf + wy * warp_amt
    # Multiple flow lines at different frequencies
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(5, 9)):
        freq = rng.uniform(0.03, 0.12) * (256.0 / dim)
        angle = rng.uniform(0, np.pi)
        proj = xw * np.cos(angle) + yw * np.sin(angle)
        flow = np.sin(proj * freq * np.pi * 2) * 0.5 + 0.5
        out += flow * rng.uniform(0.1, 0.25)
    mn, mx = out.min(), out.max()
    if mx > mn:
        out = (out - mn) / (mx - mn)
    return out.astype(np.float32)


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
    """Groovy 70s spiral — tiled so multiple spiral centers repeat across canvas."""
    import numpy as np
    rng = np.random.RandomState(seed)
    h, w = shape[:2]
    tile = 256  # ~8 tiles across 2048
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xf = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Modular coords — each tile gets its own spiral center
    ly = (yf % tile) / tile * 2 - 1  # normalized [-1,1] within tile
    lx = (xf % tile) / tile * 2 - 1
    cx, cy = rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2)
    dist = np.sqrt((lx - cx)**2 + (ly - cy)**2)
    angle = np.arctan2(ly - cy, lx - cx)
    n_arms = rng.randint(4, 8)
    tightness = rng.uniform(5, 10)
    spiral = np.sin(n_arms * angle + tightness * dist * 2 * np.pi)
    out = (spiral * 0.5 + 0.5).astype(np.float32) * 0.75
    # Soft center glow per tile
    out += np.exp(-(dist**2) / 0.8).astype(np.float32) * 0.25
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
    # Group 1: CARBON & WEAVE (new entries only - carbon_fiber, forged_carbon already exist)
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
    # Group 2: METAL & INDUSTRIAL (new entries - diamond_plate, hex_mesh etc exist)
    "rivet_grid":       {"texture_fn": texture_rivet_grid, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Evenly spaced industrial rivet dots"},
    "corrugated":       {"texture_fn": texture_corrugated, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Corrugated sheet metal parallel ridges"},
    "perforated":       {"texture_fn": texture_perforated, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Evenly punched round hole grid"},
    "expanded_metal":   {"texture_fn": texture_expanded_metal, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Stretched diamond-shape expanded mesh"},
    "grating":          {"texture_fn": texture_grating, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Industrial floor grating parallel bars"},
    "knurled":          {"texture_fn": texture_knurled, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Machine knurling diagonal cross-hatch grip"},
    "roll_cage":        {"texture_fn": texture_roll_cage, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Tubular roll cage safety bar grid structure"},
    # Group 3: NATURE & ORGANIC (new entries - wood_grain, marble etc exist)
    "tree_bark":        {"texture_fn": texture_tree_bark, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Rough furrowed tree bark texture"},
    "coral_reef":       {"texture_fn": texture_coral_reef, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Organic branching coral growth structure"},
    "river_stone":      {"texture_fn": texture_river_stone, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Smooth rounded river pebble mosaic"},
    "glacier_crack":    {"texture_fn": texture_glacier_crack, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Deep blue-white glacial ice fissure network"},
    # Group 4: GEOMETRIC (new entries - chevron, houndstooth etc exist)
    "herringbone":      {"texture_fn": texture_herringbone, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "V-shaped zigzag brick/tile pattern"},
    "argyle":           {"texture_fn": texture_argyle, "paint_fn": ppaint_contrast_light, "variable_cc": False, "desc": "Diamond/rhombus overlapping argyle pattern"},
    "greek_key":        {"texture_fn": texture_greek_key, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Continuous right-angle meander border"},
    "art_deco":         {"texture_fn": texture_art_deco, "paint_fn": ppaint_glow_gold, "variable_cc": False, "desc": "1920s geometric fan/sunburst motif"},
    "tessellation":     {"texture_fn": texture_tessellation, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Interlocking M.C. Escher-style tile shapes"},
    "yin_yang":         {"texture_fn": texture_yin_yang, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Repeating yin-yang circular duality symbol grid"},
    # Group 5: RACING & MOTORSPORT (new entries - tire_tread exists)
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
    # Group 6: TEXTILE & FABRIC (denim REMOVED - Artistic & Cultural now image-based)
    "leather_grain":    {"texture_fn": texture_leather_grain, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Natural grain leather pebble texture"},
    "quilted":          {"texture_fn": texture_quilted, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Diamond-stitched quilted padding pattern"},
    "velvet":           {"texture_fn": texture_velvet, "paint_fn": ppaint_darken_light, "variable_cc": False, "desc": "Soft pile velvet nap direction texture"},
    # "burlap" REMOVED - Artistic & Cultural category replaced by image-based (engine/registry.py)
    "lace":             {"texture_fn": texture_lace, "paint_fn": ppaint_darken_light, "variable_cc": True, "desc": "Delicate ornamental lace lacework pattern"},
    "silk_weave":       {"texture_fn": texture_silk_weave, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Fine lustrous silk satin weave sheen"},
    # Group 7: TECH & DIGITAL (new entries - circuit_board, hologram etc exist)
    "binary_code":      {"texture_fn": texture_binary_code, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Streaming 0s and 1s binary data columns"},
    "matrix_rain":      {"texture_fn": texture_matrix_rain, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Falling green character rain columns"},
    "qr_code":          {"texture_fn": texture_qr_code, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Dense QR code-style square block grid"},
    "pixel_grid":       {"texture_fn": texture_pixel_grid, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Retro 8-bit pixel block mosaic pattern"},
    "pixel_mosaic":     {"texture_fn": texture_pixel_mosaic, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Chunky retro 8-bit pixel block mosaic"},
    "data_stream":      {"texture_fn": texture_data_stream, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Flowing horizontal data packet streams"},
    "wifi_waves":       {"texture_fn": texture_wifi_waves, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Concentric signal broadcast wave arcs"},
    "glitch_scan":      {"texture_fn": texture_glitch_scan, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Horizontal glitch scanline displacement bands"},
    # Group 8: WEATHER & ELEMENTS (new entries - lightning, plasma etc exist)
    "tornado":          {"texture_fn": texture_tornado, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Spiraling funnel vortex rotation"},
    "sandstorm":        {"texture_fn": texture_sandstorm, "paint_fn": ppaint_tint_warm, "variable_cc": False, "desc": "Dense blowing sand particle streaks"},
    "hailstorm":        {"texture_fn": texture_hailstorm, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Dense scattered impact crater dimples"},
    "aurora_bands":     {"texture_fn": texture_aurora_bands, "paint_fn": ppaint_glow_green, "variable_cc": True, "desc": "Northern lights wavy curtain bands"},
    "solar_flare":      {"texture_fn": texture_solar_flare, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Erupting coronal mass ejection tendrils"},
    "nitro_burst":      {"texture_fn": texture_nitro_burst, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Nitrous oxide explosion radial burst flare"},
    # Group 9: ARTISTIC & CULTURAL - only aztec kept (procedural); rest replaced by image-based in engine/registry.py
    "tribal_flame":     {"texture_fn": texture_tribal_flame, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Flowing tribal tattoo flame curves"},
    "aztec":            {"texture_fn": texture_aztec, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Angular stepped Aztec/Mayan geometric blocks"},
    # Group 10: DAMAGE & WEAR v2 (14 physics-based; replaces 7 old entries)
    # Sourced from engine.expansions.damage_wear_v2 (scalar-bb wrapped)
    # Group 11: GOTHIC & DARK (new entries - skull, spiderweb etc exist)
    "gothic_cross":     {"texture_fn": texture_gothic_cross, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Ornate gothic cathedral cross repeating grid"},
    "iron_cross":       {"texture_fn": texture_iron_cross, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Bold Iron Cross/Maltese cross motif array"},
    "skull_wings":      {"texture_fn": texture_skull_wings, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Affliction-style winged skull ornamental spread"},
    "gothic_scroll":    {"texture_fn": texture_gothic_scroll, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Flowing dark ornamental scroll filigree"},
    "thorn_vine":       {"texture_fn": texture_thorn_vine, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Twisted thorny vine dark botanical"},
    "pentagram":        {"texture_fn": texture_pentagram, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Five-pointed star geometric array"},
    # Group 12: MEDICAL & SCIENCE (all new)
    "ekg":              {"texture_fn": texture_ekg, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Heartbeat EKG monitor line pulse - THE SHOKKER SIGNATURE"},
    "dna_helix":        {"texture_fn": texture_dna_helix, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Double-helix DNA strand spiral pattern"},
    "molecular":        {"texture_fn": texture_molecular, "paint_fn": ppaint_emboss_medium, "variable_cc": False, "desc": "Ball-and-stick molecular bond diagram grid"},
    "atomic_orbital":   {"texture_fn": texture_atomic_orbital, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Electron cloud probability orbital rings"},
    "fingerprint":      {"texture_fn": texture_fingerprint, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Swirling concentric fingerprint ridge lines"},
    "neuron_network":   {"texture_fn": texture_neuron_network, "paint_fn": ppaint_glow_purple, "variable_cc": False, "desc": "Branching neural dendrite connection web"},
    "pulse_monitor":    {"texture_fn": texture_pulse_monitor, "paint_fn": ppaint_glow_green, "variable_cc": False, "desc": "Multi-line vital signs monitor waveforms"},
    "biohazard":        {"texture_fn": texture_biohazard, "paint_fn": ppaint_tint_toxic, "variable_cc": False, "desc": "Repeating biohazard trefoil warning symbol"},
    # Group 13: ANIMAL & WILDLIFE (new entries - camo, multicam, dazzle exist)
    "zebra":            {"texture_fn": texture_zebra, "paint_fn": ppaint_contrast_medium, "variable_cc": False, "desc": "Bold black-white zebra stripe pattern"},
    "tiger_stripe":     {"texture_fn": texture_tiger_stripe, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Organic tiger stripe broken bands"},
    "giraffe":          {"texture_fn": texture_giraffe, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Irregular polygon giraffe spot patch network"},
    "crocodile":        {"texture_fn": texture_crocodile, "paint_fn": ppaint_emboss_heavy, "variable_cc": False, "desc": "Deep embossed crocodile hide square scales"},
    "feather":          {"texture_fn": texture_feather, "paint_fn": ppaint_emboss_light, "variable_cc": False, "desc": "Layered overlapping bird feather barb pattern"},
    # Group 14: SHOKK SERIES (new entries - ember_mesh, turbine exist)
    "shokk_bolt":       {"texture_fn": texture_shokk_bolt, "paint_fn": ppaint_glow_neon, "variable_cc": False, "desc": "Jagged lightning bolt Shokker logo strike pattern"},
    "shokk_pulse_wave": {"texture_fn": texture_shokk_pulse_wave, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Radiating EKG-style pulse expanding outward"},
    "shokk_fracture":   {"texture_fn": texture_shokk_fracture, "paint_fn": ppaint_darken_heavy, "variable_cc": False, "desc": "Impact point with radiating fracture cracks"},
    "shokk_hex":        {"texture_fn": texture_shokk_hex, "paint_fn": ppaint_glow_neon, "variable_cc": False, "desc": "Hexagonal cells with electric edge glow"},
    "shokk_scream":     {"texture_fn": texture_shokk_scream, "paint_fn": ppaint_glow_red, "variable_cc": False, "desc": "Sound wave distortion from center blast"},
    "shokk_grid":       {"texture_fn": texture_shokk_grid, "paint_fn": ppaint_glow_blue, "variable_cc": False, "desc": "Perspective-warped digital grid tunnel"},
    # Group 15: ABSTRACT & EXPERIMENTAL (new entries - stardust, interference exist)
    # NOTE: biomechanical, fractal, optical_illusion, sound_wave, voronoi_shatter
    # have been REPLACED by image-based versions in engine/registry.py (abstract_experimental category).
    # DO NOT re-add them here - the image versions are superior.
    "morse_code":       {"texture_fn": texture_morse_code, "paint_fn": ppaint_darken_medium, "variable_cc": False, "desc": "Dots and dashes Morse code band lines"},
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
    "caustic_light":       {"texture_fn": texture_caustic_light, "paint_fn": ppaint_tint_cool, "variable_cc": False, "desc": "Underwater caustic light refraction lines"},
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

# Group 10 Damage & Wear v2 (14 entries, scalar-bb wrapped)
try:
    from engine.expansions.damage_wear_v2 import DAMAGE_WEAR_PATTERNS
    EXPANSION_PATTERNS.update(DAMAGE_WEAR_PATTERNS)
except Exception:
    pass


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
    """Factory: visual effect spec - gradient, radial, noise-driven, etc."""
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
    """Factory: color-shift paint - shifts hue based on spatial gradient."""
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
    """Factory: weather/element paint effect - combines darken, desaturation, tinting, noise."""
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
# COLOR CHANGING CORE ALGORITHMS - Self-contained implementations
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
    """Chameleon spec - ultra-high metallic (M=220) for Fresnel color shift + sharp reflections."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    m_noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.3, 0.35, 0.2], seed + 701)
    M = np.clip(220 + m_noise * 15 * sm, 180, 250)
    cc_noise = _multi_scale_noise(shape, [16, 32, 48], [0.3, 0.4, 0.3], seed + 702)
    CC = np.clip(16 + cc_noise * 3 * sm, 16, 20)
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(15 * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _chameleon_core_24k(paint, shape, mask, seed, pm, bb, primary_hue, shift_range):
    """Full chameleon gradient paint - 8 multi-directional sine waves + Perlin noise
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
    """Low-frequency sweeping gradient field for color shift - mirrors main engine."""
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
    """Color Shift v3 spec - dual-population dithered Fresnel. Mirrors main engine."""
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
    spec[:,:,2] = np.clip(CC_arr * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _spec_cs_v5_24k(shape, mask, seed, sm, M_base=225, M_range=30, CC_range=14):
    """Color Shift v5 spec - coordinated field-driven M/R/CC variation."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    field = _panel_field_24k(shape, seed, complexity=3)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 6200)
    M_arr = M_base + field * M_range + noise * 8 * sm
    R_base = 12
    R_range = 15
    R_arr = R_base + (1.0 - field) * R_range + noise * 5 * sm
    CC_arr = 16 + field * CC_range * 0.5
    spec[:,:,0] = np.clip(M_arr * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_arr * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC_arr * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, hue_shift, sat_delta=0.10, val_delta=-0.05):
    """Color Shift adaptive - reads zone color, creates shifted dual-population Fresnel."""
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
    """Color Shift preset - fixed two-color dithered Fresnel. Mirrors main engine."""
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
    """Panel direction field - simulated 3D orientation from UV. Mirrors main engine."""
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
    """Prizm spec - uniform high-metallic with subtle variation."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 7200)
    M_arr = metallic + noise * 4 * sm
    R_arr = roughness + noise * 3 * sm
    spec[:,:,0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.where(mask > 0.5, np.clip(clearcoat, 16, 255), 16).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3,
                     flake_intensity=0.03, blend_strength=0.92):
    """Full Prizm paint - panel-aware multi-color ramp. Mirrors main engine's paint_prizm_core."""
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

# --- Group 1: Chameleon Classic (UPGRADED - full sine-wave HSV hue ramp) ---
def spec_chameleon_amethyst(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_amethyst(paint, shape, mask, seed, pm, bb):
    """Amethyst - Purple to Blue to Teal (120 degree sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 280, 120)
def spec_chameleon_emerald(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_emerald(paint, shape, mask, seed, pm, bb):
    """Emerald - Green to Teal to Blue (100 degree sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 140, 100)
def spec_chameleon_obsidian(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_obsidian(paint, shape, mask, seed, pm, bb):
    """Obsidian - Deep Purple to Blue to Green (180 degree dark sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 250, 180)

# --- Group 2: Color Shift Adaptive (UPGRADED - dithered Fresnel dual-population) ---
def spec_cs_complementary(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm)
def paint_cs_complementary(paint, shape, mask, seed, pm, bb):
    """Complementary - shifts zone color 180 degrees (opposite)"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 180)
def spec_cs_triadic(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm)
def paint_cs_triadic(paint, shape, mask, seed, pm, bb):
    """Triadic - shifts zone color 120 degrees"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 120)
def spec_cs_split(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm)
def paint_cs_split(paint, shape, mask, seed, pm, bb):
    """Split-Complementary - shifts zone color 150 degrees"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 150)

# --- Group 3: Color Shift Preset (UPGRADED - fixed two-color dithered Fresnel) ---
def spec_cs_neon_dreams(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 240, 'R': 6, 'CC': 16}, {'M': 210, 'R': 22, 'CC': 20})
def paint_cs_neon_dreams(paint, shape, mask, seed, pm, bb):
    """Neon Dreams - Hot Pink to Electric Blue"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 320, 210, 0.90, 0.88, 0.82, 0.80)
def spec_cs_twilight(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 230, 'R': 10, 'CC': 18}, {'M': 195, 'R': 30, 'CC': 22})
def paint_cs_twilight(paint, shape, mask, seed, pm, bb):
    """Twilight - Warm Amber to Deep Violet"""
    return _cs_preset_core_24k(paint, shape, mask, seed, pm, bb, 35, 275, 0.82, 0.80, 0.78, 0.72)
def spec_cs_toxic(shape, mask, seed, sm):
    return _spec_cs_v5_24k(shape, mask, seed, sm, M_base=225, M_range=28, CC_range=14)
def paint_cs_toxic(paint, shape, mask, seed, pm, bb):
    """Toxic - Acid Green shifting through Toxic Yellow to Deep Purple"""
    stops = [
        (0.00, 95,  0.92, 0.80),   # Acid Green
        (0.25, 75,  0.88, 0.82),   # Yellow-Green
        (0.50, 55,  0.85, 0.78),   # Toxic Yellow
        (0.75, 310, 0.80, 0.65),   # Deep Magenta
        (1.00, 285, 0.82, 0.60),   # Toxic Purple
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.040)

# --- Group 4: Prizm Series (UPGRADED - panel-aware multi-color ramp) ---
def spec_prizm_neon(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=232, roughness=10, clearcoat=18)
def paint_prizm_neon(paint, shape, mask, seed, pm, bb):
    """Neon - Vivid neon sweep: Magenta to Cyan to Lime"""
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
    """Blood Moon - Deep crimson to black to dark copper"""
    stops = [
        (0.00, 355, 0.90, 0.65),
        (0.30, 10,  0.85, 0.55),
        (0.55, 0,   0.70, 0.30),
        (0.80, 20,  0.80, 0.50),
        (1.00, 35,  0.75, 0.60),
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.035)

# --- Group 5: Effect & Visual (new entries) ---
spec_x_ray = make_effect_spec_fn(30, 180, 16, effect_type="gradient")  # CC was 0=mirror
spec_infrared = make_effect_spec_fn(40, 100, 16, effect_type="noise")  # CC was 0=mirror
spec_uv_blacklight = make_effect_spec_fn(50, 60, 16, effect_type="noise")
spec_double_exposure = make_effect_spec_fn(80, 50, 16, effect_type="gradient")
spec_depth_map = make_effect_spec_fn(60, 120, 16, effect_type="radial")  # CC was 0=mirror
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
spec_heat_haze = make_effect_spec_fn(60, 80, 16, effect_type="noise")  # CC was 0=mirror
spec_race_worn = make_flat_spec_fn(80, 120, 100, noise_M=30, noise_R=40, noise_scales=[4, 8, 16])  # CC=100: genuinely worn clearcoat
spec_pace_lap = make_flat_spec_fn(30, 50, 16, noise_R=15, noise_scales=[16, 32])
spec_green_flag = make_flat_spec_fn(40, 30, 16, noise_M=20, noise_scales=[8, 16])
spec_black_flag = make_flat_spec_fn(20, 180, 16, noise_R=20, noise_scales=[8, 16])  # CC was 0=mirror
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

# --- Group 7: Weather & Element (TOTAL REWRITE - custom procedural) ---

def spec_tornado_alley(shape, mask, seed, sm):
    """Tornado Alley - spiral vortex: roughness rotating from center."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1400)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    angle = np.arctan2(y - 0.5, x - 0.5)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    spiral = np.sin(angle * 4 + dist * 20 + noise * 3) * 0.5 + 0.5
    M = 30 + spiral * 30 + noise * 10 * sm
    R = 100 + (1 - spiral) * 80 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_volcanic_glass(shape, mask, seed, sm):
    """Volcanic Glass - smooth obsidian with magma vein channels."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1410)
    veins = np.where(np.abs(noise) < 0.05, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    veins_s = gaussian_filter(veins, sigma=max(1, h * 0.003))
    M = 30 + veins_s * 80 + noise * 10 * sm
    R = 5 + veins_s * 20 + noise * 5 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip((16 - veins_s * 10) * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_frozen_lake(shape, mask, seed, sm):
    """Frozen Lake - thick ice: glossy clearcoat with trapped bubble roughness spots."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1420)
    bubbles = np.where(noise > 0.55, (noise - 0.55) / 0.45, 0).astype(np.float32)
    M = 20 + bubbles * 40 + noise * 8 * sm
    R = 6 + bubbles * 30 + noise * 5 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_desert_mirage(shape, mask, seed, sm):
    """Desert Mirage - heat shimmer: undulating roughness distortion."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1430)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    shimmer = np.sin(y * np.pi * 30 + noise * 4) * 0.5 + 0.5
    M = 15 + shimmer * 25 + noise * 8 * sm
    R = 60 + (1 - shimmer) * 60 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_ocean_floor(shape, mask, seed, sm):
    """Ocean Floor - deep sea: dark with scattered bioluminescent metallic spots."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1440)
    bio_spots = np.where(noise > 0.6, (noise - 0.6) / 0.4, 0).astype(np.float32)
    M = 20 + bio_spots * 80 + noise * 8 * sm
    R = 80 - bio_spots * 50 + noise * 12 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(bio_spots * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_meteor_shower(shape, mask, seed, sm):
    """Meteor Shower - bright streaking trails: high metallic lines in dark field."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1450)
    # Diagonal streak lines
    y = np.arange(h, dtype=np.float32).reshape(-1, 1)
    x = np.arange(w, dtype=np.float32).reshape(1, -1)
    streaks = np.sin((y * 0.7 + x) * 0.08 + noise * 3) * 0.5 + 0.5
    trail = np.clip(streaks - 0.7, 0, 1) * 3.3
    M = 30 + trail * 180 + noise * 10 * sm
    R = 100 - trail * 80 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(trail * 12 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_tornado_alley(paint, shape, mask, seed, pm, bb):
    """Tornado Alley - spiral wind desaturation with debris-colored tinting."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1401)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.15 * pm * mask[:,:,np.newaxis]) + gray * 0.15 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.03 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.02 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_volcanic_glass(paint, shape, mask, seed, pm, bb):
    """Volcanic Glass - deep darkening with orange magma vein glow."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1410)
    veins = np.where(np.abs(noise) < 0.05, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    veins_glow = gaussian_filter(veins, sigma=max(2, h * 0.008))
    paint = np.clip(paint - 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + veins_glow * 0.15 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + veins_glow * 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_frozen_lake(paint, shape, mask, seed, pm, bb):
    """Frozen Lake - cold blue-white surface with trapped bubble highlights."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1421)
    bubbles = np.where(noise > 0.55, (noise - 0.55) / 0.45, 0).astype(np.float32)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.04 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bubbles[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_desert_mirage(paint, shape, mask, seed, pm, bb):
    """Desert Mirage - warm heat shimmer with sandy desaturation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1431)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]) + gray * 0.10 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.05 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_ocean_floor(paint, shape, mask, seed, pm, bb):
    """Ocean Floor - deep blue darkening with bioluminescent spot highlights."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1441)
    bio = np.where(noise > 0.6, (noise - 0.6) / 0.4, 0).astype(np.float32)
    paint = np.clip(paint - 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + bio * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + bio * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_meteor_shower(paint, shape, mask, seed, pm, bb):
    """Meteor Shower - bright diagonal streaks across darkened surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1451)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1)
    x = np.arange(w, dtype=np.float32).reshape(1, -1)
    streaks = np.sin((y * 0.7 + x) * 0.08 + noise * 3) * 0.5 + 0.5
    trail = np.clip(streaks - 0.7, 0, 1) * 3.3
    paint = np.clip(paint - 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + trail * 0.15 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + trail * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + trail * 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Group 8: Dark & Gothic (7 new entries - custom procedural effects) ---

def spec_voodoo(shape, mask, seed, sm):
    """Voodoo - ritual markings: thin glowing sigils in rough dark base."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1050)
    marks = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    marks_s = gaussian_filter(marks, sigma=max(1, h * 0.003))
    M = 25 + marks_s * 80 + noise * 8 * sm
    R = 160 - marks_s * 120 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(marks_s * 8 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_reaper(shape, mask, seed, sm):
    """Reaper - death's scythe marks: deep scratch channels with extreme roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1060)
    scythe = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 1061)
    cuts = np.where(np.abs(scythe) < 0.05, 1.0, 0.0).astype(np.float32)
    M = 15 + noise * 10 * sm
    R = 180 + cuts * 50 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_possessed(shape, mask, seed, sm):
    """Possessed - pulsing energy: concentric rings of metallic shimmer in dark base."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1070)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    x = np.arange(w, dtype=np.float32).reshape(1, -1) / max(w - 1, 1)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    rings = np.sin(dist * np.pi * 30 + noise * 3) * 0.5 + 0.5
    M = 20 + rings * 80 + noise * 10 * sm
    R = 150 - rings * 80 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(rings * 8 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_wraith(shape, mask, seed, sm):
    """Wraith - phase-shifted: alternating high/low metallic streaks for ghostly flicker."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1080)
    phase = np.sin(noise * 6) * 0.5 + 0.5
    M = 10 + phase * 90 + noise * 12 * sm
    R = 160 - phase * 80 + noise * 18 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(phase * 6 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_cursed(shape, mask, seed, sm):
    """Cursed - infection veins: thin bright channels spreading from noise."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1090)
    veins = np.where(np.abs(noise) < 0.05, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    veins_s = gaussian_filter(veins, sigma=max(1, h * 0.003))
    M = 20 + veins_s * 100 + noise * 8 * sm
    R = 170 - veins_s * 140 + noise * 12 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(veins_s * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_eclipse(shape, mask, seed, sm):
    """Eclipse - total darkness with bright corona rim around radial center."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1100)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.45)**2 + (x - 0.5)**2)
    corona = np.clip(1.0 - np.abs(dist - 0.25) * 12, 0, 1)
    M = 5 + corona * 200 + noise * 5 * sm
    R = 220 - corona * 200 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(corona * 14 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_nightmare(shape, mask, seed, sm):
    """Nightmare - distortion ripples: warped roughness field creating unsettling sheen."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1110)
    warp = np.sin(noise * 8) * 0.5 + 0.5
    M = 30 + warp * 60 + noise * 15 * sm
    R = 130 + (1 - warp) * 80 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(warp * 4 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_voodoo(paint, shape, mask, seed, pm, bb):
    """Voodoo - eerie green ritual markings glowing on darkened surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1050)
    marks = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    marks_s = gaussian_filter(marks, sigma=max(1, h * 0.003))
    marks_glow = gaussian_filter(marks, sigma=max(2, h * 0.010))
    paint = np.clip(paint - 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + marks_glow * 0.18 * pm * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + marks_s * 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + marks_s * 0.20 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_reaper(paint, shape, mask, seed, pm, bb):
    """Reaper - deep darkness with scythe-cut highlight streaks."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1062)
    scythe = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 1061)
    cuts = np.where(np.abs(scythe) < 0.05, 1.0, 0.0).astype(np.float32)
    paint = np.clip(paint - 0.18 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.20 * pm * mask[:,:,np.newaxis]) + gray * 0.20 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + cuts[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_possessed(paint, shape, mask, seed, pm, bb):
    """Possessed - pulsing red energy rings emanating from center."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1071)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    rings = np.sin(dist * np.pi * 30 + noise * 3) * 0.5 + 0.5
    pulse = np.clip(rings - 0.5, 0, 1) * 2
    paint = np.clip(paint - 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + pulse * 0.20 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - pulse * 0.05 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - pulse * 0.05 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_wraith(paint, shape, mask, seed, pm, bb):
    """Wraith - ghostly phase-shift: fading transparency with cold shimmer."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1081)
    phase = np.sin(noise * 6) * 0.5 + 0.5
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.22 * pm * mask[:,:,np.newaxis]) + gray * 0.22 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + phase[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + phase * 0.05 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_cursed(paint, shape, mask, seed, pm, bb):
    """Cursed - glowing green infection veins spreading through darkened surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1090)
    veins = np.where(np.abs(noise) < 0.05, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    veins_s = gaussian_filter(veins, sigma=max(1, h * 0.003))
    veins_glow = gaussian_filter(veins, sigma=max(2, h * 0.010))
    paint = np.clip(paint - 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + veins_glow * 0.15 * pm * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + veins_s * 0.05 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + veins_s * 0.20 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_eclipse(paint, shape, mask, seed, pm, bb):
    """Eclipse - radial darkness with bright golden corona at the rim."""
    h, w = shape
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1101)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.45)**2 + (x - 0.5)**2)
    corona = np.clip(1.0 - np.abs(dist - 0.25) * 12, 0, 1)
    core_dark = np.clip(1.0 - dist / 0.22, 0, 1)
    paint = np.clip(paint - (0.15 + core_dark[:,:,np.newaxis] * 0.10) * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + corona * 0.25 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + corona * 0.15 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + corona * 0.05 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_nightmare(paint, shape, mask, seed, pm, bb):
    """Nightmare - distortion ripples with desaturated unsettling color shifts."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1111)
    warp = np.sin(noise * 8) * 0.5 + 0.5
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.15 * pm * mask[:,:,np.newaxis]) + gray * 0.15 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    shift = np.clip(warp - 0.5, 0, 1) * 2
    paint[:,:,0] = np.clip(paint[:,:,0] + shift * 0.06 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Group 9: Luxury & Exotic (new entries - galaxy exists) ---
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
spec_velvet_crush = make_flat_spec_fn(30, 130, 200, noise_R=20, noise_scales=[4, 8, 16])  # CC was 0=mirror
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

# --- Group 10: Neon & Glow (new entries - neon_glow, radioactive, static, scorched exist) ---
spec_neon_vegas = make_flat_spec_fn(60, 40, 16, noise_M=20, noise_scales=[4, 8, 16])
spec_laser_grid = make_flat_spec_fn(80, 20, 16, noise_M=15, noise_scales=[8, 16])
spec_plasma_globe = make_effect_spec_fn(100, 30, 16, effect_type="radial")
spec_firefly = make_flat_spec_fn(40, 60, 16, noise_M=15, noise_scales=[2, 4])  # CC was 0=mirror
spec_led_matrix = make_flat_spec_fn(70, 25, 16, noise_M=20, noise_scales=[2, 4, 8])
spec_cyberpunk = make_flat_spec_fn(90, 30, 16, noise_M=25, noise_R=15, noise_scales=[4, 8, 16])
def paint_neon_vegas(paint, shape, mask, seed, pm, bb):
    """Neon Vegas - multi-color neon strip glow like Las Vegas signage."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Vertical color strips
    strip = (x * 12) % 1.0
    blend = 0.25 * pm
    # Cycle through neon colors
    r = (np.sin(strip * np.pi * 2) * 0.5 + 0.5) * 0.8
    g = (np.sin(strip * np.pi * 2 + 2.1) * 0.5 + 0.5) * 0.8
    b = (np.sin(strip * np.pi * 2 + 4.2) * 0.5 + 0.5) * 0.8
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b * blend * mask, 0, 1)
    return paint

def paint_laser_grid(paint, shape, mask, seed, pm, bb):
    """Laser Grid - bright green horizontal + vertical grid lines like a laser grid."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Grid lines - thin bright lines at regular intervals
    grid_freq = 25  # ~25 lines across surface
    h_lines = np.clip(1.0 - np.abs(np.sin(y * np.pi * grid_freq)) * 8, 0, 1)
    v_lines = np.clip(1.0 - np.abs(np.sin(x * np.pi * grid_freq)) * 8, 0, 1)
    grid = np.clip(h_lines + v_lines, 0, 1)
    blend = grid * 0.35 * pm * mask
    # Bright green laser color
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * 0.3), 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.75, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * 0.3), 0, 1)
    return paint

def paint_plasma_globe(paint, shape, mask, seed, pm, bb):
    """Plasma Globe - purple/pink tendrils radiating from center like a plasma ball."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    angle = np.arctan2(y - cy, x - cx)
    dist = np.sqrt(((y - cy) / h)**2 + ((x - cx) / w)**2)
    # Radial tendrils via angle-based sine waves
    n_tendrils = 8
    tendrils = np.zeros(shape, dtype=np.float32)
    for i in range(n_tendrils):
        offset = i * np.pi * 2 / n_tendrils
        t = np.clip(1.0 - np.abs(np.sin(angle * n_tendrils / 2 + offset)) * 4, 0, 1)
        t *= np.clip(1.0 - dist * 1.5, 0, 1)  # Fade with distance
        tendrils = np.clip(tendrils + t, 0, 1)
    blend = tendrils * 0.30 * pm * mask
    # Purple/pink plasma color
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * 0.55, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.10, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * 0.70, 0, 1)
    return paint

# (firefly is defined above as full function)
# paint_firefly already defined above

def paint_led_matrix(paint, shape, mask, seed, pm, bb):
    """LED Matrix - visible dot/pixel grid pattern like an LED display."""
    h, w = shape
    # Pixel grid
    dot_spacing = max(4, min(h, w) // 60)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    dy = (y % dot_spacing) - dot_spacing / 2.0
    dx = (x % dot_spacing) - dot_spacing / 2.0
    dot_dist = np.sqrt(dy**2 + dx**2) / (dot_spacing * 0.35)
    dots = np.clip(1.0 - dot_dist, 0, 1) ** 1.5
    # Color varies by position
    hue_shift = ((y // dot_spacing + x // dot_spacing) % 3).astype(np.float32) / 3.0
    blend = dots * 0.30 * pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * (0.2 + hue_shift * 0.3), 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * (0.5 - hue_shift * 0.2), 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * (0.3 + (1 - hue_shift) * 0.3), 0, 1)
    return paint

def paint_cyberpunk(paint, shape, mask, seed, pm, bb):
    """Cyberpunk - neon magenta/cyan split with horizontal glitch lines."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Split: left half magenta, right half cyan
    split = np.clip((x - 0.5) * 8, -1, 1) * 0.5 + 0.5
    blend = 0.25 * pm
    # Magenta (left) / Cyan (right)
    paint[:,:,0] = np.clip(paint[:,:,0] + (1 - split) * 0.30 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + split * 0.20 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + split * 0.35 * blend * mask + (1 - split) * 0.15 * blend * mask, 0, 1)
    # Horizontal glitch lines
    rng = np.random.RandomState(seed + 790)
    n_glitch = max(3, h // 80)
    for _ in range(n_glitch):
        gy = rng.randint(0, h - 4)
        gh = rng.randint(2, max(3, h // 100))
        gend = min(h, gy + gh)
        dx = rng.randint(-w // 10, w // 10)
        gm = mask[gy:gend, :]
        for c in range(3):
            shifted = np.roll(paint[gy:gend, :, c], dx, axis=1)
            paint[gy:gend, :, c] = np.clip(
                paint[gy:gend, :, c] * (1 - gm * 0.5 * pm) + shifted * gm * 0.5 * pm, 0, 1)
    return paint
def paint_firefly(paint, shape, mask, seed, pm, bb):
    """Firefly - scattered warm yellow-green point lights like fireflies in the dark."""
    h, w = shape
    rng = np.random.RandomState(seed + 780)
    result = paint.copy()
    # Slightly darken base for contrast
    result = np.clip(result * (1 - 0.08 * pm * mask[:,:,np.newaxis]), 0, 1)
    # Scatter firefly point lights
    n_flies = max(15, (h * w) // 8000)
    for _ in range(n_flies):
        fy = rng.randint(0, h)
        fx = rng.randint(0, w)
        if mask[fy, fx] < 0.3:
            continue
        # Radial glow from firefly point
        radius = rng.randint(max(3, min(h, w) // 150), max(5, min(h, w) // 60))
        brightness = 0.3 + rng.random() * 0.4
        y_lo = max(0, fy - radius); y_hi = min(h, fy + radius)
        x_lo = max(0, fx - radius); x_hi = min(w, fx + radius)
        yy, xx = np.mgrid[y_lo:y_hi, x_lo:x_hi].astype(np.float32)
        dist = np.sqrt((yy - fy)**2 + (xx - fx)**2) / radius
        glow = np.clip(1.0 - dist, 0, 1) ** 2 * brightness * pm
        local_mask = mask[y_lo:y_hi, x_lo:x_hi]
        result[y_lo:y_hi, x_lo:x_hi, 0] = np.clip(result[y_lo:y_hi, x_lo:x_hi, 0] + glow * 0.6 * local_mask, 0, 1)
        result[y_lo:y_hi, x_lo:x_hi, 1] = np.clip(result[y_lo:y_hi, x_lo:x_hi, 1] + glow * 0.7 * local_mask, 0, 1)
        result[y_lo:y_hi, x_lo:x_hi, 2] = np.clip(result[y_lo:y_hi, x_lo:x_hi, 2] + glow * 0.1 * local_mask, 0, 1)
    return result

# --- Group 11: Texture & Surface (TOTAL REWRITE - custom material simulation) ---

def spec_croc_leather(shape, mask, seed, sm):
    """Croc Leather - reptile scale emboss: regular dimples with glossy clearcoat."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1200)
    scale_size = max(12, min(w, h) // 20)
    y, x = _get_mgrid(shape)
    scale_grid = np.abs(np.sin(y * np.pi * 2 / scale_size + noise * 0.5)) * \
                 np.abs(np.sin(x * np.pi * 2 / scale_size + noise * 0.3))
    M = 30 + scale_grid * 40 + noise * 8 * sm
    R = 50 + (1 - scale_grid) * 60 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_hammered_copper(shape, mask, seed, sm):
    """Hammered Copper - dimpled metallic with variable hammer impressions."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1210)
    # Random dimple impressions from noise peaks
    dimples = np.where(noise > 0.3, (noise - 0.3) / 0.7, 0).astype(np.float32)
    M = 170 + dimples * 40 + noise * 15 * sm
    R = 40 + (1 - dimples) * 50 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 60; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_dark_brushed_steel(shape, mask, seed, sm):
    """Dark Brushed Steel - strong directional scratch roughness in one axis."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1220)
    # Horizontal brush direction
    x_noise = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 1221)
    M = 200 + noise * 20 * sm
    R = 50 + x_noise * 50 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 60; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_etched_metal(shape, mask, seed, sm):
    """Etched Metal - chemical etch: fine relief patterns in smooth metallic."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1230)
    etch = np.where(np.abs(noise) < 0.1, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    etch_soft = gaussian_filter(etch, sigma=max(1, h * 0.002))
    M = 160 + etch_soft * 30 + noise * 12 * sm
    R = 30 + (1 - etch_soft) * 40 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 200; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_sandstone(shape, mask, seed, sm):
    """Sandstone - granular mineral surface: high roughness with fine grain noise."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1240)
    grain = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 1241)
    M = 15 + noise * 8 * sm
    R = 150 + grain * 40 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 180; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_petrified_wood(shape, mask, seed, sm):
    """Petrified Wood - fossilized grain: directional streaks with mixed roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1250)
    grain = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1251)
    M = 25 + grain * 20 + noise * 8 * sm
    R = 100 + noise * 60 + grain * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 80; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_forged_iron(shape, mask, seed, sm):
    """Forged Iron - blacksmith hammer marks: high metallic with rough impact zones."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1260)
    impacts = np.where(noise > 0.4, (noise - 0.4) / 0.6, 0).astype(np.float32)
    M = 180 + impacts * 30 + noise * 15 * sm
    R = 60 + impacts * 60 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_acid_etched_glass(shape, mask, seed, sm):
    """Acid Etched Glass - frosted patches in clear glass: variable roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1270)
    frost = np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 10 + frost * 15 + noise * 5 * sm
    R = 20 + frost * 100 + noise * 15 * sm
    CC = np.clip(16 - frost * 12, 16, 255)
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_concrete(shape, mask, seed, sm):
    """Concrete - raw poured: zero metallic, high roughness with aggregate noise."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1280)
    agg = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 1281)
    M = 6 + noise * 4 * sm
    R = 170 + agg * 40 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 240; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_cast_iron(shape, mask, seed, sm):
    """Cast Iron - heavy pour: high metallic with rough scale marks and pitting."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1290)
    pitting = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 1291)
    pits = np.where(pitting > 0.5, (pitting - 0.5) * 2, 0).astype(np.float32)
    M = 160 + noise * 20 * sm - pits * 40
    R = 80 + pits * 80 + noise * 25 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 100; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def paint_croc_leather(paint, shape, mask, seed, pm, bb):
    """Croc Leather - darkened scale pattern with glossy emboss highlighting."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1200)
    scale_size = max(12, min(w, h) // 20)
    y, x = _get_mgrid(shape)
    scales = np.abs(np.sin(y * np.pi * 2 / scale_size + noise * 0.5)) * \
             np.abs(np.sin(x * np.pi * 2 / scale_size + noise * 0.3))
    paint = np.clip(paint - (1 - scales)[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + scales[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hammered_copper(paint, shape, mask, seed, pm, bb):
    """Hammered Copper - warm copper tint with dimple highlight variation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1210)
    dimples = np.where(noise > 0.3, (noise - 0.3) / 0.7, 0).astype(np.float32)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + dimples[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dark_brushed_steel(paint, shape, mask, seed, pm, bb):
    """Dark Brushed Steel - darkened surface with directional scratch highlights."""
    h, w = shape
    scratch = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 1221)
    paint = np.clip(paint - 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]) + gray * 0.10 * pm * mask[:,:,np.newaxis]
    highlights = np.clip(scratch - 0.5, 0, 1) * 2
    paint = np.clip(paint + highlights[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_etched_metal(paint, shape, mask, seed, pm, bb):
    """Etched Metal - chemical etch relief: darkened recesses, bright raised areas."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1230)
    etch = np.where(np.abs(noise) < 0.1, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    etch_soft = gaussian_filter(etch, sigma=max(1, h * 0.002))
    paint = np.clip(paint - etch_soft[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + (1 - etch_soft[:,:,np.newaxis]) * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_sandstone(paint, shape, mask, seed, pm, bb):
    """Sandstone - warm tan mineral surface with fine granular noise texture."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1240)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.15 * pm * mask[:,:,np.newaxis]) + gray * 0.15 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_petrified_wood(paint, shape, mask, seed, pm, bb):
    """Petrified Wood - fossilized grain streaks with warm earth tones."""
    h, w = shape
    grain = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1251)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.12 * pm * mask[:,:,np.newaxis]) + gray * 0.12 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + grain * 0.05 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + grain * 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_forged_iron(paint, shape, mask, seed, pm, bb):
    """Forged Iron - dark iron with hammer impact highlight spots."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1260)
    impacts = np.where(noise > 0.4, (noise - 0.4) / 0.6, 0).astype(np.float32)
    paint = np.clip(paint - 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]) + gray * 0.10 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + impacts[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_acid_etched_glass(paint, shape, mask, seed, pm, bb):
    """Acid Etched Glass - frosted glass patches desaturating through clear areas."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1270)
    frost = np.clip(noise * 0.5 + 0.5, 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - frost[:,:,np.newaxis] * 0.18 * pm * mask[:,:,np.newaxis]) + \
            gray * frost[:,:,np.newaxis] * 0.18 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_concrete(paint, shape, mask, seed, pm, bb):
    """Concrete - heavy gray desaturation with aggregate grain texture."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1280)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.25 * pm * mask[:,:,np.newaxis]) + gray * 0.25 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_cast_iron(paint, shape, mask, seed, pm, bb):
    """Cast Iron - dark metallic desaturation with rough pour texture."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1290)
    paint = np.clip(paint - 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.12 * pm * mask[:,:,np.newaxis]) + gray * 0.12 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Group 12: Vintage & Retro (all new) ---
spec_barn_find = make_flat_spec_fn(50, 180, 160, noise_M=30, noise_R=35, noise_scales=[4, 8, 16])  # CC was 0=mirror
spec_patina_truck = make_flat_spec_fn(60, 150, 160, noise_M=25, noise_R=30, noise_scales=[4, 8, 16])  # CC was 0=mirror
spec_hot_rod_flames = make_flat_spec_fn(200, 12, 16, noise_M=20, noise_scales=[8, 16, 32])
spec_woodie_wagon = make_flat_spec_fn(20, 100, 60, noise_R=20, noise_scales=[8, 16, 32])  # CC=60: semi-gloss lacquer over wood panels
spec_drive_in = make_flat_spec_fn(100, 30, 16, noise_M=20, noise_scales=[4, 8, 16])
spec_muscle_car_stripe = make_flat_spec_fn(150, 15, 16, noise_M=15, noise_scales=[16, 32])
spec_pin_up = make_flat_spec_fn(10, 160, 40, noise_R=20, noise_scales=[4, 8])  # CC was 0=mirror
spec_vinyl_record = make_flat_spec_fn(30, 80, 40, noise_R=15, noise_scales=[4, 8])  # CC was 0=mirror
paint_barn_find = make_aged_fn(fade_strength=0.25, roughen=0.10)
paint_patina_truck = make_aged_fn(fade_strength=0.18, roughen=0.08)
paint_hot_rod_flames = make_vivid_depth_fn(sat_boost=0.18, depth_darken=0.04)
paint_woodie_wagon = make_weather_paint_fn(tint_rgb=[0.2, 0.12, 0.03], noise_str=0.04)
paint_drive_in = make_glow_fn([0.5, 0.3, 0.4], glow_strength=0.06)
paint_muscle_car_stripe = make_vivid_depth_fn(sat_boost=0.12, depth_darken=0.03)
paint_pin_up = make_aged_fn(fade_strength=0.10, roughen=0.06)
paint_vinyl_record = make_weather_paint_fn(darken=0.06, noise_str=0.03)

# --- Group 13: Surreal & Fantasy (TOTAL REWRITE - custom procedural) ---

def spec_portal(shape, mask, seed, sm):
    """Portal - swirling dimensional vortex: radial metallic spiral."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1700)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    angle = np.arctan2(y - 0.5, x - 0.5)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    vortex = np.sin(angle * 5 + dist * 25 + noise * 4) * 0.5 + 0.5
    rim = np.clip(1.0 - np.abs(dist - 0.3) * 10, 0, 1)
    M = 60 + vortex * 100 + rim * 60 + noise * 12 * sm
    R = 15 + (1 - vortex) * 25 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_time_warp(shape, mask, seed, sm):
    """Time Warp - temporal spiral distortion: roughness spiraling inward."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1710)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    angle = np.arctan2(y - 0.5, x - 0.5)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    spiral = np.sin(angle * 3 + dist * 18 + noise * 3) * 0.5 + 0.5
    M = 60 + spiral * 60 + noise * 12 * sm
    R = 20 + (1 - spiral) * 40 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_antimatter(shape, mask, seed, sm):
    """Antimatter - inverted reality: very high metallic with negative-image roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1720)
    invert = 1.0 - np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 180 + invert * 30 + noise * 15 * sm
    R = 5 + (1 - invert) * 15 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_singularity(shape, mask, seed, sm):
    """Singularity - gravity well: extreme radial pull to matte center void."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1730)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    pull = np.clip(1.0 - dist * 3, 0, 1)
    M = 5 + (1 - pull) * 80 + noise * 8 * sm
    R = 200 + pull * 40 - (1 - pull) * 100 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_dreamscape(shape, mask, seed, sm):
    """Dreamscape - soft focus dream: low-frequency smooth metallic clouds."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1740)
    cloud = np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 40 + cloud * 40 + noise * 8 * sm
    R = 30 + (1 - cloud) * 30 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_acid_trip(shape, mask, seed, sm):
    """Acid Trip - psychedelic waves: multi-frequency metallic rainbow undulation."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1750)
    wave1 = np.sin(noise * 8) * 0.5 + 0.5
    wave2 = np.sin(noise * 12 + 1.5) * 0.5 + 0.5
    M = 80 + wave1 * 80 + wave2 * 40 + noise * 15 * sm
    R = 10 + (1 - wave1) * 20 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_mirage(shape, mask, seed, sm):
    """Mirage - heat shimmer: undulating roughness distortion field."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1760)
    shimmer = np.sin(noise * 6) * 0.5 + 0.5
    M = 20 + shimmer * 25 + noise * 8 * sm
    R = 50 + (1 - shimmer) * 60 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_fourth_dimension(shape, mask, seed, sm):
    """4th Dimension - hyperspace facets: geometric metallic patches."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1770)
    facets = np.sin(noise * 10) * 0.5 + 0.5
    edges = np.where(np.abs(facets - 0.5) < 0.08, 1.0, 0.0).astype(np.float32)
    M = 150 + facets * 60 + noise * 15 * sm
    R = 10 + edges * 30 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_glitch_reality(shape, mask, seed, sm):
    """Glitch Reality - digital corruption: random block patches of varied material."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1780)
    blocks = np.round(noise * 3) / 3
    M = 60 + blocks * 140 + noise * 25 * sm
    R = 30 + (1 - blocks) * 100 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(blocks * 14 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_phantom_zone(shape, mask, seed, sm):
    """Phantom Zone - crystalline prison: faceted cold metallic with high roughness edges."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1790)
    crystal = np.sin(noise * 8) * 0.5 + 0.5
    edges = np.where(np.abs(crystal - 0.5) < 0.05, 1.0, 0.0).astype(np.float32)
    M = 130 + crystal * 40 + noise * 12 * sm
    R = 15 + edges * 60 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip((16 - edges * 10) * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_portal(paint, shape, mask, seed, pm, bb):
    """Portal - swirling dimensional purple-teal vortex energy overlay."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1701)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    rim = np.clip(1.0 - np.abs(dist - 0.3) * 10, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + rim * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + rim * 0.15 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_time_warp(paint, shape, mask, seed, pm, bb):
    """Time Warp - sepia-gold age distortion with spiral blur."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1711)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]) + gray * 0.10 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.04 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_antimatter(paint, shape, mask, seed, pm, bb):
    """Antimatter - negative image: inverted color tones."""
    h, w = shape
    inverted = 1.0 - paint
    blend = 0.15 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * blend) + inverted[:,:,c] * mask * blend, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_singularity(paint, shape, mask, seed, pm, bb):
    """Singularity - extreme radial darkening pulling to void center."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    pull = np.clip(1.0 - dist * 3, 0, 1)
    paint = np.clip(paint - pull[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - pull[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis]) + \
            gray * pull[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dreamscape(paint, shape, mask, seed, pm, bb):
    """Dreamscape - soft pastel cloud tints with gentle desaturation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1741)
    cloud = np.clip(noise * 0.5 + 0.5, 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.08 * pm * mask[:,:,np.newaxis]) + gray * 0.08 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + cloud * 0.04 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + cloud * 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_acid_trip(paint, shape, mask, seed, pm, bb):
    """Acid Trip - psychedelic rainbow waves pulsing across surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1751)
    phase = noise * np.pi * 2
    paint[:,:,0] = np.clip(paint[:,:,0] + np.sin(phase) * 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + np.sin(phase + 2.1) * 0.08 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.sin(phase + 4.2) * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_mirage(paint, shape, mask, seed, pm, bb):
    """Mirage - warm shimmer: heat distortion with desaturation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1761)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]) + gray * 0.10 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_fourth_dimension(paint, shape, mask, seed, pm, bb):
    """4th Dimension - geometric facet highlights with cold shimmer."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1771)
    facets = np.sin(noise * 10) * 0.5 + 0.5
    edges = np.where(np.abs(facets - 0.5) < 0.08, 1.0, 0.0).astype(np.float32)
    paint = np.clip(paint + edges[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + facets * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_glitch_reality(paint, shape, mask, seed, pm, bb):
    """Glitch Reality - random digital block color displacement."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1781)
    blocks = np.round(noise * 3) / 3
    shift = (blocks - 0.5) * 2
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + shift * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_phantom_zone(paint, shape, mask, seed, pm, bb):
    """Phantom Zone - cold crystalline prison with ice-blue desaturation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1791)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.15 * pm * mask[:,:,np.newaxis]) + gray * 0.15 * pm * mask[:,:,np.newaxis]
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint



# ================================================================
# 24K+ ARSENAL - MISSING MONOLITHIC DEFINITIONS (135 entries)
# ================================================================
# These fill the gap between HTML SPECIAL_GROUPS catalog and Python registry.
# All use factory functions for efficient, consistent implementations.

# --- Chameleon Classic (5 gap-fill - UPGRADED to full sine-wave HSV hue ramp) ---
def spec_chameleon_aurora(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_aurora(paint, shape, mask, seed, pm, bb):
    """Aurora - Green to Cyan to Purple (Northern Lights sweep, 200 degrees)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 130, 200)
def spec_chameleon_fire(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_fire(paint, shape, mask, seed, pm, bb):
    """Fire - Red to Orange to Gold (50 degree warm sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 0, 50)
def spec_chameleon_frost(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_frost(paint, shape, mask, seed, pm, bb):
    """Frost - Icy Blue to Teal to Aqua (60 degree cool sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 195, 60)
def spec_chameleon_galaxy(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_galaxy(paint, shape, mask, seed, pm, bb):
    """Galaxy - Deep Purple to Blue to Teal to Green (160 degree cosmic sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 260, 160)
def spec_chameleon_neon(shape, mask, seed, sm):
    return _spec_chameleon_24k(shape, mask, seed, sm)
def paint_chameleon_neon(paint, shape, mask, seed, pm, bb):
    """Neon - Magenta to Red to Orange to Yellow to Green (240 degree full neon sweep)"""
    return _chameleon_core_24k(paint, shape, mask, seed, pm, bb, 300, 240)

# --- Color Shift Adaptive (7 gap-fill - UPGRADED to dithered Fresnel dual-population) ---
def spec_cs_chrome_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 245, 'R': 5, 'CC': 18}, {'M': 220, 'R': 18, 'CC': 22})
def paint_cs_chrome_shift(paint, shape, mask, seed, pm, bb):
    """Chrome Shift - subtle 30 degree shift, ultra-high metallic feel"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 30, sat_delta=0.05, val_delta=0.05)
def spec_cs_earth(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 200, 'R': 20, 'CC': 14}, {'M': 170, 'R': 40, 'CC': 18})
def paint_cs_earth(paint, shape, mask, seed, pm, bb):
    """Earth - warm 45 degree shift towards earthy tones"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 45, sat_delta=-0.10, val_delta=-0.08)
def spec_cs_monochrome(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 220, 'R': 12, 'CC': 16}, {'M': 185, 'R': 35, 'CC': 20})
def paint_cs_monochrome(paint, shape, mask, seed, pm, bb):
    """Monochrome - no hue shift, only saturation/value differential"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 0, sat_delta=-0.30, val_delta=0.10)
def spec_cs_neon_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 238, 'R': 6, 'CC': 16}, {'M': 205, 'R': 24, 'CC': 20})
def paint_cs_neon_shift(paint, shape, mask, seed, pm, bb):
    """Neon Shift - vivid 90 degree shift"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 90, sat_delta=0.15, val_delta=0.05)
def spec_cs_ocean_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 225, 'R': 14, 'CC': 18}, {'M': 190, 'R': 32, 'CC': 22})
def paint_cs_ocean_shift(paint, shape, mask, seed, pm, bb):
    """Ocean Shift - cool -60 degree shift towards blue/teal"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, -60, sat_delta=0.08, val_delta=-0.03)
def spec_cs_prism_shift(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 235, 'R': 8, 'CC': 16}, {'M': 200, 'R': 28, 'CC': 22})
def paint_cs_prism_shift(paint, shape, mask, seed, pm, bb):
    """Prism Shift - prismatic 120 degree shift"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 120, sat_delta=0.12, val_delta=0.0)
def spec_cs_vivid(shape, mask, seed, sm):
    return _spec_cs_24k(shape, mask, seed, sm, {'M': 232, 'R': 10, 'CC': 16}, {'M': 198, 'R': 26, 'CC': 20})
def paint_cs_vivid(paint, shape, mask, seed, pm, bb):
    """Vivid - 60 degree shift with strong saturation boost"""
    return _cs_adaptive_core_24k(paint, shape, mask, seed, pm, bb, 60, sat_delta=0.20, val_delta=0.05)

# --- Color Shift Preset (6 gap-fill - UPGRADED to v5 multi-stop chameleon) ---
def spec_cs_candy_paint(shape, mask, seed, sm):
    return _spec_cs_v5_24k(shape, mask, seed, sm, M_base=228, M_range=30, CC_range=16)
def paint_cs_candy_paint(paint, shape, mask, seed, pm, bb):
    """Candy Paint - Hot Pink shifting through Coral to Teal with candy depth"""
    stops = [
        (0.00, 340, 0.90, 0.82),   # Hot Pink
        (0.20, 355, 0.85, 0.78),   # Rose
        (0.40, 10,  0.80, 0.80),   # Coral
        (0.60, 160, 0.82, 0.76),   # Aqua
        (0.80, 180, 0.85, 0.78),   # Teal
        (1.00, 195, 0.82, 0.76),   # Deep Teal
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.040)
def spec_cs_dark_flame(shape, mask, seed, sm):
    return _spec_cs_v5_24k(shape, mask, seed, sm, M_base=215, M_range=28, CC_range=12)
def paint_cs_dark_flame(paint, shape, mask, seed, pm, bb):
    """Dark Flame - Deep Crimson through Black Cherry to Dark Amber"""
    stops = [
        (0.00, 350, 0.92, 0.55),   # Deep Crimson
        (0.20, 5,   0.88, 0.60),   # Dark Red
        (0.40, 340, 0.80, 0.45),   # Black Cherry
        (0.60, 15,  0.85, 0.55),   # Dark Orange
        (0.80, 25,  0.82, 0.60),   # Dark Amber
        (1.00, 35,  0.78, 0.55),   # Burnt Gold
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.045)
def spec_cs_gold_rush(shape, mask, seed, sm):
    return _spec_cs_v5_24k(shape, mask, seed, sm, M_base=240, M_range=25, CC_range=16)
def paint_cs_gold_rush(paint, shape, mask, seed, pm, bb):
    """Gold Rush - Rich Gold sweeping through Copper to Warm Bronze"""
    stops = [
        (0.00, 50,  0.88, 0.86),   # Bright Gold
        (0.25, 45,  0.85, 0.82),   # Rich Gold
        (0.50, 35,  0.82, 0.78),   # Amber-Gold
        (0.75, 25,  0.80, 0.72),   # Copper
        (1.00, 18,  0.78, 0.68),   # Warm Bronze
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.050)
def spec_cs_oilslick(shape, mask, seed, sm):
    return _spec_cs_v5_24k(shape, mask, seed, sm, M_base=220, M_range=30, CC_range=14)
def paint_cs_oilslick(paint, shape, mask, seed, pm, bb):
    """Oil Slick - Dark iridescent: Violet through Dark Blue to Dark Teal"""
    stops = [
        (0.00, 280, 0.75, 0.42),   # Dark Violet
        (0.20, 260, 0.70, 0.38),   # Dark Indigo
        (0.40, 230, 0.72, 0.40),   # Dark Blue
        (0.60, 210, 0.68, 0.42),   # Dark Steel Blue
        (0.80, 190, 0.70, 0.44),   # Dark Teal
        (1.00, 170, 0.65, 0.40),   # Dark Cyan
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.030)
def spec_cs_rose_gold_shift(shape, mask, seed, sm):
    return _spec_cs_v5_24k(shape, mask, seed, sm, M_base=235, M_range=25, CC_range=16)
def paint_cs_rose_gold_shift(paint, shape, mask, seed, pm, bb):
    """Rose Gold Shift - Rose Pink sweeping through Peach to Warm Gold"""
    stops = [
        (0.00, 345, 0.55, 0.84),   # Rose Pink
        (0.25, 355, 0.48, 0.82),   # Soft Rose
        (0.50, 15,  0.45, 0.84),   # Peach
        (0.75, 30,  0.52, 0.82),   # Light Copper
        (1.00, 42,  0.58, 0.80),   # Warm Gold
    ]
    return _prizm_core_24k(paint, shape, mask, seed, pm, bb, stops, complexity=3, flake_intensity=0.035)

# --- Prizm Series (4 gap-fill - UPGRADED to panel-aware multi-color ramp) ---
def spec_prizm_cosmos(shape, mask, seed, sm):
    return _spec_prizm_24k(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=18)
def paint_prizm_cosmos(paint, shape, mask, seed, pm, bb):
    """Cosmos - Deep space: Violet to Indigo to Teal to Nebula Pink"""
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
    """Dark Matter - Ultra-dark subtle shift: Near-Black to Dark Purple to Dark Blue"""
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
    """Fire & Ice - Hot red/orange contrasting with cold blue/teal"""
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
    """Spectrum - Full visible spectrum: Red to Violet (7-stop rainbow)"""
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

# --- Effect & Visual (13 missing) - these PRESERVE car color, add visual effects ---
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
def paint_chromatic_aberration(paint, shape, mask, seed, pm, bb):
    """Chromatic Aberration - RGB channel offset for prismatic fringe effect."""
    h, w = shape
    offset = max(3, int(w * 0.008))  # ~0.8% of width
    shifted_r = np.roll(paint[:,:,0], offset, axis=1)
    shifted_b = np.roll(paint[:,:,2], -offset, axis=1)
    blend = 0.35 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + shifted_r * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + shifted_b * blend * mask, 0, 1)
    return paint

def paint_crt_scanline(paint, shape, mask, seed, pm, bb):
    """CRT Scanline - visible horizontal scanline darkening bands."""
    h, w = shape
    y = np.arange(h, dtype=np.float32)
    scanline_freq = max(2, h // 200)  # ~200 scanlines
    lines = (np.sin(y * np.pi / scanline_freq) * 0.5 + 0.5) ** 2
    darken = (1.0 - lines * 0.35 * pm)[:, np.newaxis]
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * 0.9 + mask * 0.9 * darken[:,:]), 0, 1)
    # Slight green tint for CRT feel
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    return paint

def paint_datamosh(paint, shape, mask, seed, pm, bb):
    """Datamosh - horizontal band displacement + channel corruption glitch."""
    h, w = shape
    rng = np.random.RandomState(seed + 700)
    result = paint.copy()
    # Horizontal band displacement - visible glitch strips
    n_bands = max(5, h // 60)
    for _ in range(n_bands):
        band_y = rng.randint(0, h - 20)
        band_h = rng.randint(8, max(10, h // 20))
        band_end = min(h, band_y + band_h)
        dx = rng.randint(-w // 8, w // 8)  # Horizontal shift
        band_mask = mask[band_y:band_end, :]
        blend = 0.6 * pm
        # Shift the band horizontally
        for c in range(3):
            shifted = np.roll(paint[band_y:band_end, :, c], dx, axis=1)
            result[band_y:band_end, :, c] = np.clip(
                result[band_y:band_end, :, c] * (1 - band_mask * blend) +
                shifted * band_mask * blend, 0, 1)
        # Channel swap on some bands for color corruption
        if rng.random() > 0.5:
            swap_ch = rng.choice([0, 1, 2], 2, replace=False)
            temp = result[band_y:band_end, :, swap_ch[0]].copy()
            result[band_y:band_end, :, swap_ch[0]] = result[band_y:band_end, :, swap_ch[1]]
            result[band_y:band_end, :, swap_ch[1]] = temp
    return result

def paint_embossed(paint, shape, mask, seed, pm, bb):
    """Embossed - raised relief effect via directional light + shadow."""
    h, w = shape
    gray = paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114
    # Directional emboss: right-down light source
    shifted = np.roll(np.roll(gray, 1, axis=0), 1, axis=1)
    emboss = np.clip((gray - shifted) * 3.0 + 0.5, 0, 1)
    blend = 0.30 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * blend) + emboss * mask * blend, 0, 1)
    return paint

def paint_film_burn(paint, shape, mask, seed, pm, bb):
    """Film Burn - warm amber/orange light leak gradient from edges."""
    h, w = shape
    # Radial light leak from top-right corner
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((y / h)**2 + ((w - x) / w)**2)
    burn = np.clip(1.0 - dist * 1.2, 0, 1) ** 1.5
    blend = 0.25 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + burn * 0.35 * blend * mask, 0, 1)  # orange
    paint[:,:,1] = np.clip(paint[:,:,1] + burn * 0.15 * blend * mask, 0, 1)  # amber
    paint[:,:,2] = np.clip(paint[:,:,2] - burn * 0.10 * blend * mask, 0, 1)  # reduce blue
    return paint

def paint_fish_eye(paint, shape, mask, seed, pm, bb):
    """Fish Eye - barrel distortion warping + edge darkening."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    # Normalized distance from center
    ny = (y - cy) / cy
    nx = (x - cx) / cx
    dist = np.sqrt(ny**2 + nx**2)
    # Barrel distortion: bend coordinates outward
    distortion = 1.0 + dist**2 * 0.3 * pm
    # Map source coordinates
    src_y = np.clip((ny / distortion * cy + cy).astype(int), 0, h - 1)
    src_x = np.clip((nx / distortion * cx + cx).astype(int), 0, w - 1)
    result = paint.copy()
    blend = 0.40 * pm
    for c in range(3):
        warped = paint[src_y, src_x, c]
        result[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * blend) + warped * mask * blend, 0, 1)
    # Edge darkening vignette
    vignette = np.clip(dist * 0.6, 0, 1) ** 2 * 0.20 * pm
    result = np.clip(result - vignette[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return result

def paint_halftone(paint, shape, mask, seed, pm, bb):
    """Halftone - visible dot grid pattern like newsprint."""
    h, w = shape
    dot_size = max(4, min(h, w) // 80)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    # Grid of dots
    dy = (y % dot_size) - dot_size / 2.0
    dx = (x % dot_size) - dot_size / 2.0
    dist = np.sqrt(dy**2 + dx**2) / (dot_size / 2.0)
    # Dot size varies with image brightness
    gray = paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114
    dot_threshold = gray * 1.2
    dots = np.where(dist < dot_threshold, 1.0, 0.3)
    blend = 0.30 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * blend) + paint[:,:,c] * dots * mask * blend, 0, 1)
    return paint

def paint_kaleidoscope(paint, shape, mask, seed, pm, bb):
    """Kaleidoscope - radial symmetric color pattern with high saturation."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    # Polar coordinates from center
    angle = np.arctan2(y - cy, x - cx)  # -pi to pi
    dist = np.sqrt(((y - cy) / cy)**2 + ((x - cx) / cx)**2)
    # Create kaleidoscope: fold angle into 6 symmetric segments
    n_segments = 6
    folded = np.abs(((angle / (2 * np.pi) + 0.5) * n_segments) % 1.0 - 0.5) * 2
    # Rainbow color from folded angle + radial variation
    hue = (folded + dist * 0.3) % 1.0
    sat = np.clip(0.7 + dist * 0.3, 0, 1)
    val = np.clip(0.8 - dist * 0.2, 0.3, 1)
    # HSV to RGB
    c = val * sat
    hp = hue * 6.0
    x2 = c * (1 - np.abs(hp % 2 - 1))
    r = np.zeros_like(c); g = np.zeros_like(c); b = np.zeros_like(c)
    for lo in range(6):
        m = (hp >= lo) & (hp < lo + 1)
        if lo == 0: r[m] = c[m]; g[m] = x2[m]
        elif lo == 1: r[m] = x2[m]; g[m] = c[m]
        elif lo == 2: g[m] = c[m]; b[m] = x2[m]
        elif lo == 3: g[m] = x2[m]; b[m] = c[m]
        elif lo == 4: r[m] = x2[m]; b[m] = c[m]
        elif lo == 5: r[m] = c[m]; b[m] = x2[m]
    off = val - c
    r += off; g += off; b += off
    blend = 0.30 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint

def paint_long_exposure(paint, shape, mask, seed, pm, bb):
    """Long Exposure - horizontal motion blur + light trail brightening."""
    from PIL import Image as _Img, ImageFilter as _Filt
    h, w = shape
    blur_radius = max(2, w // 40)
    result = paint.copy()
    blend = 0.35 * pm
    for c in range(3):
        ch_img = _Img.fromarray((paint[:,:,c] * 255).astype(np.uint8))
        # Horizontal-only blur via box blur with tall kernel
        blurred = ch_img.filter(_Filt.BoxBlur(blur_radius))
        blurred_arr = np.array(blurred).astype(np.float32) / 255.0
        result[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * blend) + blurred_arr * mask * blend, 0, 1)
    # Light trail: brighten the blurred result
    result = np.clip(result + 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    return result

def paint_negative(paint, shape, mask, seed, pm, bb):
    """Negative - photographic negative color inversion."""
    blend = 0.50 * pm
    inverted = 1.0 - paint
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * blend) + inverted[:,:,c] * mask * blend, 0, 1)
    return paint

def paint_parallax(paint, shape, mask, seed, pm, bb):
    """Parallax - depth-based brightness layering for pseudo-3D."""
    h, w = shape
    gray = paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114
    # Create depth layers: bright areas pop forward (brighter), dark areas recede
    depth = (gray - 0.5) * 2.0  # -1 to +1
    # Near layer: brighten
    near_boost = np.clip(depth, 0, 1) * 0.20 * pm
    # Far layer: darken + desaturate
    far_darken = np.clip(-depth, 0, 1) * 0.15 * pm
    # Apply with edge enhancement for depth perception
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    edges = np.clip((gx + gy) * 5.0, 0, 1) * 0.10 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + near_boost * mask - far_darken * mask + edges * mask, 0, 1)
    return paint

def paint_refraction(paint, shape, mask, seed, pm, bb):
    """Refraction - prismatic color split via per-channel noise displacement."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 800)
    noise_norm = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    # Each channel gets shifted by noise field at different scales
    blend = 0.30 * pm
    result = paint.copy()
    for c in range(3):
        # Create displaced version via noise-weighted sampling
        shift_amount = (c - 1) * 0.08  # R:left, G:center, B:right
        hue_shift = noise_norm * shift_amount * pm
        result[:,:,c] = np.clip(
            paint[:,:,c] * (1 - mask * blend) +
            np.clip(paint[:,:,c] + hue_shift, 0, 1) * mask * blend,
            0, 1)
    # Add prismatic edge highlights where noise gradient is strong
    grad = np.abs(np.diff(noise_norm, axis=1, prepend=noise_norm[:,:1]))
    prism = np.clip(grad * 8, 0, 1) * 0.08 * pm
    paint[:,:,0] = np.clip(result[:,:,0] + prism * mask, 0, 1)
    paint[:,:,1] = result[:,:,1]
    paint[:,:,2] = np.clip(result[:,:,2] + prism * 0.5 * mask, 0, 1)
    return paint

def paint_solarization(paint, shape, mask, seed, pm, bb):
    """Solarization - Sabattier effect: partial inversion at threshold."""
    blend = 0.40 * pm
    # Invert only mid-tones (threshold at 0.5)
    solarized = np.where(paint > 0.5, 1.0 - paint, paint * 2.0)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - mask * blend) + solarized[:,:,c] * mask * blend, 0, 1)
    return paint

# --- Racing Legend (10 missing) ---
spec_burnout_zone = make_flat_spec_fn(160, 25, 16, noise_M=25, noise_R=15, noise_scales=[4, 8])
spec_chicane_blur = make_effect_spec_fn(80, 30, 16, effect_type="noise")
spec_cool_down = make_flat_spec_fn(40, 50, 16, noise_R=20, noise_scales=[8, 16])
spec_drag_chute = make_flat_spec_fn(60, 80, 16, noise_R=25, noise_scales=[4, 8, 16])
spec_flag_wave = make_effect_spec_fn(100, 20, 16, effect_type="bands")
spec_grid_walk = make_flat_spec_fn(50, 40, 16, noise_M=15, noise_scales=[8, 16])
spec_night_race = make_effect_spec_fn(30, 150, 30, effect_type="gradient")  # CC was 0=mirror
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

# --- Weather & Element (15 remaining - TOTAL REWRITE custom procedural) ---

def spec_acid_rain(shape, mask, seed, sm):
    """Acid Rain - corrosive streaks: vertical roughness channels in smooth surface."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1500)
    x_freq = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    streaks = np.sin(x_freq * np.pi * 40 + noise * 2) * 0.5 + 0.5
    corrode = np.where(streaks > 0.7, (streaks - 0.7) / 0.3, 0).astype(np.float32)
    M = 30 + noise * 10 * sm
    R = 50 + corrode * 100 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip((16 - corrode * 12) * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_black_ice(shape, mask, seed, sm):
    """Black Ice - invisible ice glaze: ultra-smooth, high clearcoat, slight metallic."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1510)
    M = 25 + noise * 8 * sm
    R = 4 + noise * 4 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_blizzard(shape, mask, seed, sm):
    """Blizzard - whiteout snow: high diffuse roughness with icy glossy patches."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1520)
    snow = np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 40 + snow * 20 + noise * 8 * sm
    R = 30 + (1 - snow) * 40 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip((16 + snow * 2) * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_dew_drop(shape, mask, seed, sm):
    """Dew Drop - morning dew: scattered high-metallic gloss spots in smooth base."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1530)
    drops = np.where(noise > 0.6, (noise - 0.6) / 0.4, 0).astype(np.float32)
    M = 35 + drops * 60 + noise * 8 * sm
    R = 15 + (1 - drops) * 10 + noise * 5 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_dust_storm(shape, mask, seed, sm):
    """Dust Storm - sandy particle noise: high roughness with granular variation."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1540)
    grain = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 1541)
    M = 15 + noise * 8 * sm
    R = 100 + grain * 40 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 200; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_fog_bank(shape, mask, seed, sm):
    """Fog Bank - soft obscurity: gradient roughness fading from smooth to rough."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1550)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    fog = np.clip(y + noise * 0.3, 0, 1)
    M = 10 + fog * 15 + noise * 5 * sm
    R = 40 + fog * 60 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip((16 - fog * 10) * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_hail_damage(shape, mask, seed, sm):
    """Hail Damage - impact dents: scattered roughness bumps in smooth body."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1560)
    dents = np.where(noise > 0.5, (noise - 0.5) * 2, 0).astype(np.float32)
    M = 60 + noise * 15 * sm
    R = 30 + dents * 80 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip((16 - dents * 10) * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_heat_wave(shape, mask, seed, sm):
    """Heat Wave - shimmer distortion: undulating roughness bands."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1570)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    wave = np.sin(y * np.pi * 25 + noise * 4) * 0.5 + 0.5
    M = 20 + wave * 25 + noise * 8 * sm
    R = 50 + (1 - wave) * 50 + noise * 12 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_hurricane(shape, mask, seed, sm):
    """Hurricane - spiral eye wall: radial roughness spiral from center."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1580)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    angle = np.arctan2(y - 0.5, x - 0.5)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    spiral = np.sin(angle * 3 + dist * 15 + noise * 2) * 0.5 + 0.5
    eye = np.clip(1.0 - dist / 0.1, 0, 1)
    M = 25 + spiral * 30 + eye * 40 + noise * 8 * sm
    R = 80 + (1 - spiral) * 60 - eye * 60 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_lightning_strike(shape, mask, seed, sm):
    """Lightning Strike - bolt crack channels: very high metallic, very low roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1590)
    bolt = np.where(np.abs(noise) < 0.04, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    bolt_s = gaussian_filter(bolt, sigma=max(1, h * 0.003))
    M = 30 + bolt_s * 200 + noise * 8 * sm
    R = 80 - bolt_s * 70 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(bolt_s * 14 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_magma_flow(shape, mask, seed, sm):
    """Magma Flow - molten lava: bright glossy channels in rough cooled crust."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1600)
    lava = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    lava_s = gaussian_filter(lava, sigma=max(1, h * 0.003))
    M = 40 + lava_s * 140 + noise * 10 * sm
    R = 140 - lava_s * 130 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(lava_s * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_monsoon(shape, mask, seed, sm):
    """Monsoon - heavy rain sheet: vertical roughness streaks."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1610)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    rain = np.sin(y * np.pi * 60 + noise * 3) * 0.5 + 0.5
    M = 25 + rain * 20 + noise * 8 * sm
    R = 60 + (1 - rain) * 40 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(rain * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_permafrost(shape, mask, seed, sm):
    """Permafrost - deep freeze: ultra-smooth ice with subtle crystal facets."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1620)
    crystal = np.clip(np.abs(noise) * 3, 0, 1)
    facets = np.where(crystal > 0.6, (crystal - 0.6) / 0.4, 0).astype(np.float32)
    M = 20 + facets * 30 + noise * 8 * sm
    R = 8 + facets * 12 + noise * 5 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_solar_wind(shape, mask, seed, sm):
    """Solar Wind - charged particle aurora: horizontal shimmer bands."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1630)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    aurora = np.sin(y * np.pi * 15 + noise * 3) * 0.5 + 0.5
    M = 100 + aurora * 60 + noise * 15 * sm
    R = 15 + (1 - aurora) * 20 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_tidal_wave(shape, mask, seed, sm):
    """Tidal Wave - massive wave surge: curved roughness bands flowing across."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1640)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    wave = np.sin(y * np.pi * 8 + noise * 3) * 0.5 + 0.5
    crest = np.clip(wave - 0.7, 0, 1) * 3.3
    M = 35 + crest * 50 + noise * 10 * sm
    R = 50 + (1 - wave) * 40 + noise * 12 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(crest * 12 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_acid_rain(paint, shape, mask, seed, pm, bb):
    """Acid Rain - corrosive green-yellow streaks dissolving surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1501)
    x_freq = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    streaks = np.sin(x_freq * np.pi * 40 + noise * 2) * 0.5 + 0.5
    corrode = np.clip((streaks - 0.65) * 3, 0, 1)
    paint = np.clip(paint - corrode[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + corrode * 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_black_ice(paint, shape, mask, seed, pm, bb):
    """Black Ice - transparent ice glaze: subtle darkening with glassy depth."""
    h, w = shape
    paint = np.clip(paint - 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blizzard(paint, shape, mask, seed, pm, bb):
    """Blizzard - whiteout: heavy white overlay washing out color."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1521)
    snow = np.clip(noise * 0.5 + 0.5, 0, 1)
    paint = np.clip(paint + snow[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]) + gray * 0.10 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dew_drop(paint, shape, mask, seed, pm, bb):
    """Dew Drop - fresh morning: bright sparkle drops on clean surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1531)
    drops = np.where(noise > 0.6, (noise - 0.6) / 0.4, 0).astype(np.float32)
    paint = np.clip(paint + drops[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dust_storm(paint, shape, mask, seed, pm, bb):
    """Dust Storm - sandy particle overlay with warm desaturation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1541)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.18 * pm * mask[:,:,np.newaxis]) + gray * 0.18 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_fog_bank(paint, shape, mask, seed, pm, bb):
    """Fog Bank - soft white fog gradient washing out detail."""
    h, w = shape
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1551)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    fog = np.clip(y + noise * 0.3, 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - fog[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis]) + \
            gray * fog[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + fog[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hail_damage(paint, shape, mask, seed, pm, bb):
    """Hail Damage - impact dent dimples affecting surface highlights."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1561)
    dents = np.where(noise > 0.5, (noise - 0.5) * 2, 0).astype(np.float32)
    paint = np.clip(paint - dents[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_heat_wave(paint, shape, mask, seed, pm, bb):
    """Heat Wave - warm shimmer with amber tint distortion."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1571)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.05 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hurricane(paint, shape, mask, seed, pm, bb):
    """Hurricane - spiral wind with desaturation and noise distortion."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1581)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.12 * pm * mask[:,:,np.newaxis]) + gray * 0.12 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_lightning_strike(paint, shape, mask, seed, pm, bb):
    """Lightning Strike - bright white-blue bolt channels on darkened surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1590)
    bolt = np.where(np.abs(noise) < 0.04, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    bolt_glow = gaussian_filter(bolt, sigma=max(2, h * 0.008))
    paint = np.clip(paint - 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + bolt_glow * 0.15 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + bolt_glow * 0.18 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + bolt_glow * 0.25 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_magma_flow(paint, shape, mask, seed, pm, bb):
    """Magma Flow - molten orange-red lava channels in dark cooled crust."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1601)
    lava = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    lava_glow = gaussian_filter(lava, sigma=max(2, h * 0.008))
    paint = np.clip(paint - 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + lava_glow * 0.25 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + lava_glow * 0.10 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_monsoon(paint, shape, mask, seed, pm, bb):
    """Monsoon - heavy rain sheet with cool blue-gray tinting."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1611)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.02 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_permafrost(paint, shape, mask, seed, pm, bb):
    """Permafrost - deep freeze: icy blue-white crystal tint on base."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1621)
    crystal = np.clip(np.abs(noise) * 3, 0, 1)
    facets = np.where(crystal > 0.6, (crystal - 0.6) / 0.4, 0).astype(np.float32)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + facets[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_solar_wind(paint, shape, mask, seed, pm, bb):
    """Solar Wind - aurora-like golden-green shimmer bands."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1631)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    aurora = np.sin(y * np.pi * 15 + noise * 3) * 0.5 + 0.5
    band = np.clip(aurora - 0.4, 0, 1) * 1.7
    paint[:,:,0] = np.clip(paint[:,:,0] + band * 0.10 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + band * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + band * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_tidal_wave(paint, shape, mask, seed, pm, bb):
    """Tidal Wave - surge blue-white crests on deep dark base."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1641)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    wave = np.sin(y * np.pi * 8 + noise * 3) * 0.5 + 0.5
    crest = np.clip(wave - 0.7, 0, 1) * 3.3
    paint = np.clip(paint - 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + crest * 0.10 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + crest * 0.15 * pm * mask, 0, 1)
    paint = np.clip(paint + crest[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Dark & Gothic (15 entries - TOTAL REWRITE to custom procedural effects) ---

def spec_banshee(shape, mask, seed, sm):
    """Banshee - ghostly wailing: horizontal roughness bands with low metallic."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 900)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    wail = np.sin(y * np.pi * 20 + noise * 4) * 0.5 + 0.5
    M = 15 + wail * 30 + noise * 10 * sm
    R = 120 + (1 - wail) * 100 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_blood_oath(shape, mask, seed, sm):
    """Blood Oath - blood-drip: wet glossy channels in rough matte surface."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 910)
    x_freq = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    drip_base = np.sin(x_freq * np.pi * 30 + noise * 2) * 0.5 + 0.5
    y_pos = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    drip_flow = drip_base * np.clip(1.0 - y_pos * 0.3, 0.5, 1.0)
    drip = np.where(drip_flow > 0.7, 1.0, 0.0).astype(np.float32)
    M = 20 + drip * 100 + noise * 8 * sm
    R = 200 - drip * 170 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(drip * 8 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_catacombs(shape, mask, seed, sm):
    """Catacombs - ancient stone: extremely rough with erosion channels."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise1 = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 920)
    noise2 = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 921)
    erosion = np.clip(noise1 * 0.6 + noise2 * 0.4, -1, 1)
    crack = np.where(erosion > 0.5, (erosion - 0.5) * 2, 0).astype(np.float32)
    M = 8 + noise2 * 5 * sm
    R = 160 + crack * 80 + noise1 * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_dark_ritual(shape, mask, seed, sm):
    """Dark Ritual - arcane runes: glowing low-roughness sigils in rough dark base."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 930)
    rune_field = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 931)
    runes = np.where(np.abs(rune_field) < 0.08, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    runes_soft = gaussian_filter(runes, sigma=max(1, h * 0.003))
    M = 10 + runes_soft * 120 + noise * 8 * sm
    R = 200 - runes_soft * 180 + noise * 10 * sm
    CC = np.clip(runes_soft * 16, 16, 255)
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_death_metal(shape, mask, seed, sm):
    """Death Metal - brushed dark metal with aggressive scratch patterns."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 940)
    scratch = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 941)
    M = 160 + noise * 30 * sm
    R = 100 + scratch * 80 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 80; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_demon_forge(shape, mask, seed, sm):
    """Demon Forge - molten cracks: bright hot lines, dark everywhere else."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 950)
    crack = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    crack_soft = gaussian_filter(crack, sigma=max(1, h * 0.003))
    M = 30 + crack_soft * 200 + noise * 10 * sm
    R = 180 - crack_soft * 170 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(crack_soft * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_gargoyle(shape, mask, seed, sm):
    """Gargoyle - worn stone statue: very high roughness, zero clearcoat."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 960)
    erosion = _multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.30, 0.35, 0.20], seed + 961)
    M = 10 + noise * 8 * sm
    R = 180 + erosion * 50 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 160; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_graveyard(shape, mask, seed, sm):
    """Graveyard - dead matte with fog wisps of slightly smoother areas."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 970)
    fog = np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 8 + fog * 15 + noise * 5 * sm
    R = 200 - fog * 40 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 180; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_haunted(shape, mask, seed, sm):
    """Haunted - flickering ghost presence: irregular patches of metallic shimmer."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 980)
    ghost_spots = np.where(noise > 0.55, (noise - 0.55) / 0.45, 0).astype(np.float32)
    M = 15 + ghost_spots * 100 + noise * 10 * sm
    R = 170 - ghost_spots * 120 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(ghost_spots * 6 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_hellhound(shape, mask, seed, sm):
    """Hellhound - charred surface with ember cracks glowing through."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 990)
    ember = np.where(np.abs(noise) < 0.07, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    ember_soft = gaussian_filter(ember, sigma=max(1, h * 0.003))
    M = 50 + ember_soft * 160 + noise * 15 * sm
    R = 140 - ember_soft * 120 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(ember_soft * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_iron_maiden(shape, mask, seed, sm):
    """Iron Maiden - industrial riveted metal: high metallic, scratch roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1000)
    tile = max(20, min(w, h) // 10)
    y, x = _get_mgrid(shape)
    rvt_d = np.sqrt(((x % tile) - tile / 2.0)**2 + ((y % tile) - tile / 2.0)**2) / (tile / 2.0)
    rivets = np.clip(1.0 - rvt_d * 3, 0, 1)
    M = 140 + rivets * 60 + noise * 20 * sm
    R = 120 + noise * 40 * sm - rivets * 60
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 80; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_lich_king(shape, mask, seed, sm):
    """Lich King - ice crystal: sharp faceted highlights in dark frozen base."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1010)
    crystal = np.clip(np.abs(noise) * 3, 0, 1)
    facets = np.where(crystal > 0.6, (crystal - 0.6) / 0.4, 0).astype(np.float32)
    M = 40 + facets * 150 + noise * 10 * sm
    R = 140 - facets * 100 + noise * 20 * sm
    CC = np.clip(facets * 16, 16, 255)
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_necrotic(shape, mask, seed, sm):
    """Necrotic - decaying organic: extreme roughness with degradation noise."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16, 32], [0.1, 0.2, 0.3, 0.25, 0.15], seed + 1020)
    decay = np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 10 + decay * 15 + noise * 5 * sm
    R = 140 + decay * 90 + noise * 25 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_shadow_realm(shape, mask, seed, sm):
    """Shadow Realm - near-complete absorption: ultra-low metallic, extreme roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1030)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    depth = np.clip(1.0 - np.sqrt((y - 0.5)**2 + (x - 0.5)**2) * 1.5, 0, 1)
    M = 5 + (1 - depth) * 10 + noise * 3 * sm
    R = 220 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_spectral(shape, mask, seed, sm):
    """Spectral - ghostly semi-transparent: variable metallic with shimmer bands."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1040)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    shimmer = np.sin(y * np.pi * 12 + noise * 3) * 0.5 + 0.5
    M = 30 + shimmer * 80 + noise * 12 * sm
    R = 100 + (1 - shimmer) * 80 + noise * 15 * sm
    CC = np.clip(shimmer * 16, 16, 255)
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec
def paint_banshee(paint, shape, mask, seed, pm, bb):
    """Banshee - ghostly spectral wisps streaming across the surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 901)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    wisp1 = np.sin(y * np.pi * 15 + noise * 3 + x * np.pi * 2) * 0.5 + 0.5
    wisp2 = np.sin(y * np.pi * 25 - x * np.pi * 5 + noise * 2) * 0.5 + 0.5
    wisps = np.clip(wisp1 * 0.6 + wisp2 * 0.4, 0, 1)
    # BOOSTED: heavy darkening for ghostly pallor
    paint = np.clip(paint - 0.30 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: aggressive desaturation - ghosts have no color
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    wisp_vis = np.clip(wisps - 0.4, 0, 1) * 2.5
    # BOOSTED: dramatic white-blue wisp streaks
    paint[:,:,0] = np.clip(paint[:,:,0] + wisp_vis * 0.20 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + wisp_vis * 0.28 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + wisp_vis * 0.40 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blood_oath(paint, shape, mask, seed, pm, bb):
    """Blood Oath - dripping crimson blood streaks on darkened surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 911)
    x_freq = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    y_pos = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    drip_base = np.sin(x_freq * np.pi * 30 + noise * 2) * 0.5 + 0.5
    drip = np.clip((drip_base - 0.65) * 5, 0, 1) * np.clip(1.0 - y_pos * 0.2, 0.6, 1.0)
    # BOOSTED: deep darkening - blood on black
    paint = np.clip(paint - 0.25 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: vivid crimson drip channels
    paint[:,:,0] = np.clip(paint[:,:,0] + drip * 0.65 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - drip * 0.25 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - drip * 0.25 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_catacombs(paint, shape, mask, seed, pm, bb):
    """Catacombs - ancient stone erosion with moss-green crevice tinting."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 922)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: heavy desaturation - ancient stone has no color
    paint = paint * (1 - 0.60 * pm * mask[:,:,np.newaxis]) + gray * 0.60 * pm * mask[:,:,np.newaxis]
    # BOOSTED: deep darkening - underground tomb
    paint = np.clip(paint - 0.30 * pm * mask[:,:,np.newaxis], 0, 1)
    crevice = np.clip((noise - 0.3) * 2, 0, 1)
    # BOOSTED: visible moss-green staining in erosion channels
    paint[:,:,1] = np.clip(paint[:,:,1] + crevice * 0.18 * pm * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] - crevice * 0.06 * pm * mask, 0, 1)
    grain = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 923)
    paint = np.clip(paint + grain[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dark_ritual(paint, shape, mask, seed, pm, bb):
    """Dark Ritual - glowing purple arcane sigils on darkened surface."""
    h, w = shape
    rune_field = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 931)
    runes = np.where(np.abs(rune_field) < 0.08, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    runes_soft = gaussian_filter(runes, sigma=max(1, h * 0.004))
    rune_glow = gaussian_filter(runes, sigma=max(2, h * 0.012))
    # BOOSTED: much deeper background darkness - ritual chamber
    paint = np.clip(paint - 0.35 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: vivid purple-magenta rune glow halo
    paint[:,:,0] = np.clip(paint[:,:,0] + rune_glow * 0.30 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + rune_glow * 0.50 * pm * mask, 0, 1)
    # BOOSTED: bright hot rune core lines
    paint[:,:,0] = np.clip(paint[:,:,0] + runes_soft * 0.35 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + runes_soft * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + runes_soft * 0.55 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_death_metal(paint, shape, mask, seed, pm, bb):
    """Death Metal - aggressive dark metallic with scratch highlight streaks."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 942)
    scratch = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 941)
    # BOOSTED: heavy darkening - black metal base
    paint = np.clip(paint - 0.28 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: strong desaturation - cold industrial
    paint = paint * (1 - 0.35 * pm * mask[:,:,np.newaxis]) + gray * 0.35 * pm * mask[:,:,np.newaxis]
    scratches = np.clip(scratch - 0.6, 0, 1) * 2.5
    # BOOSTED: bright visible scratch highlights cutting through dark
    paint = np.clip(paint + scratches[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_demon_forge(paint, shape, mask, seed, pm, bb):
    """Demon Forge - molten orange/red cracks glowing through dark surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 950)
    crack = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    crack_soft = gaussian_filter(crack, sigma=max(1, h * 0.003))
    crack_glow = gaussian_filter(crack, sigma=max(2, h * 0.010))
    # BOOSTED: much darker surrounding areas - forge darkness
    paint = np.clip(paint - 0.35 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: bright orange-red glow halo around cracks
    paint[:,:,0] = np.clip(paint[:,:,0] + crack_glow * 0.55 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + crack_glow * 0.22 * pm * mask, 0, 1)
    # BOOSTED: white-hot crack core lines
    paint[:,:,0] = np.clip(paint[:,:,0] + crack_soft * 0.65 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + crack_soft * 0.35 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + crack_soft * 0.10 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_gargoyle(paint, shape, mask, seed, pm, bb):
    """Gargoyle - stone gray wash with dark erosion and lichen spots."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 962)
    erosion = _multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.30, 0.35, 0.20], seed + 961)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: near-total desaturation - lifeless stone
    paint = paint * (1 - 0.65 * pm * mask[:,:,np.newaxis]) + gray * 0.65 * pm * mask[:,:,np.newaxis]
    # BOOSTED: deep erosion darkening
    paint = np.clip(paint - (0.22 + erosion[:,:,np.newaxis] * 0.15) * pm * mask[:,:,np.newaxis], 0, 1)
    lichen = np.clip(noise - 0.5, 0, 1) * 2
    # BOOSTED: visible green-yellow lichen colonies
    paint[:,:,1] = np.clip(paint[:,:,1] + lichen * 0.14 * pm * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + lichen * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_graveyard(paint, shape, mask, seed, pm, bb):
    """Graveyard - dark fog overlay with cold blue-gray desaturation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 971)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: heavy desaturation - colorless death
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    # BOOSTED: deep darkness
    paint = np.clip(paint - 0.30 * pm * mask[:,:,np.newaxis], 0, 1)
    fog = np.clip(noise * 0.5 + 0.5, 0, 1)
    fog_vis = np.clip(fog - 0.3, 0, 1) * 1.4
    # BOOSTED: cold blue fog wisps
    paint[:,:,2] = np.clip(paint[:,:,2] + fog_vis * 0.25 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + fog_vis * 0.12 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_haunted(paint, shape, mask, seed, pm, bb):
    """Haunted - ghost patches with cold desaturation and shimmer."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 981)
    ghost = np.where(noise > 0.55, (noise - 0.55) / 0.45, 0).astype(np.float32)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: heavy cold desaturation - life drained away
    paint = paint * (1 - 0.45 * pm * mask[:,:,np.newaxis]) + gray * 0.45 * pm * mask[:,:,np.newaxis]
    # BOOSTED: darker base
    paint = np.clip(paint - 0.25 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: bright ghostly shimmer patches popping through
    paint = np.clip(paint + ghost[:,:,np.newaxis] * 0.28 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: cold blue ghost tint
    paint[:,:,2] = np.clip(paint[:,:,2] + ghost * 0.16 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hellhound(paint, shape, mask, seed, pm, bb):
    """Hellhound - charred black with ember-orange fissures glowing through."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 990)
    ember = np.where(np.abs(noise) < 0.07, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    ember_soft = gaussian_filter(ember, sigma=max(1, h * 0.003))
    ember_glow = gaussian_filter(ember, sigma=max(2, h * 0.010))
    # BOOSTED: deep char blackening
    paint = np.clip(paint - 0.35 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: strong desaturation - burnt to ash
    paint = paint * (1 - 0.35 * pm * mask[:,:,np.newaxis]) + gray * 0.35 * pm * mask[:,:,np.newaxis]
    # BOOSTED: vivid ember glow halo
    paint[:,:,0] = np.clip(paint[:,:,0] + ember_glow * 0.55 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + ember_glow * 0.20 * pm * mask, 0, 1)
    # BOOSTED: white-hot ember core fissures
    paint[:,:,0] = np.clip(paint[:,:,0] + ember_soft * 0.60 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + ember_soft * 0.28 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_iron_maiden(paint, shape, mask, seed, pm, bb):
    """Iron Maiden - dark industrial metal with rivet highlights and rust stain."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1001)
    # BOOSTED: deep industrial darkening
    paint = np.clip(paint - 0.24 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: heavy cold desaturation - raw iron
    paint = paint * (1 - 0.40 * pm * mask[:,:,np.newaxis]) + gray * 0.40 * pm * mask[:,:,np.newaxis]
    rust = np.clip(noise - 0.4, 0, 1) * 1.5
    # BOOSTED: visible rust-orange staining
    paint[:,:,0] = np.clip(paint[:,:,0] + rust * 0.22 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + rust * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_lich_king(paint, shape, mask, seed, pm, bb):
    """Lich King - frozen undead: icy blue-green glow from crystal facets."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1010)
    crystal = np.clip(np.abs(noise) * 3, 0, 1)
    facets = np.where(crystal > 0.6, (crystal - 0.6) / 0.4, 0).astype(np.float32)
    # BOOSTED: deep freeze darkening
    paint = np.clip(paint - 0.28 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: stronger base ice tint - frozen surface
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.10 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.16 * pm * mask, 0, 1)
    # BOOSTED: bright glowing ice crystal facets
    paint[:,:,0] = np.clip(paint[:,:,0] + facets * 0.15 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + facets * 0.40 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + facets * 0.30 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_necrotic(paint, shape, mask, seed, pm, bb):
    """Necrotic - organic decay: sickly green-brown discoloration with dark rot."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8, 16, 32], [0.1, 0.2, 0.3, 0.25, 0.15], seed + 1021)
    decay = np.clip(noise * 0.5 + 0.5, 0, 1)
    rot = np.clip(decay - 0.6, 0, 1) * 2.5
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: heavy desaturation - organic death
    paint = paint * (1 - 0.50 * pm * mask[:,:,np.newaxis]) + gray * 0.50 * pm * mask[:,:,np.newaxis]
    # BOOSTED: deep decay darkening
    paint = np.clip(paint - decay[:,:,np.newaxis] * 0.28 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: sickly yellow-green decay tint
    paint[:,:,0] = np.clip(paint[:,:,0] + decay * 0.10 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + decay * 0.18 * pm * mask, 0, 1)
    # BOOSTED: vivid dark rot patches - brown-black necrosis
    paint[:,:,0] = np.clip(paint[:,:,0] + rot * 0.14 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - rot * 0.12 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - rot * 0.16 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_shadow_realm(paint, shape, mask, seed, pm, bb):
    """Shadow Realm - engulfing darkness with faint purple void shimmer."""
    h, w = shape
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1031)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    depth = np.clip(1.0 - np.sqrt((y - 0.5)**2 + (x - 0.5)**2) * 1.5, 0, 1)
    # BOOSTED: near-total darkness - consumed by void
    paint = np.clip(paint - 0.45 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: extreme desaturation - color devoured
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    edge_shimmer = np.clip(1.0 - depth, 0, 1) * noise
    # BOOSTED: vivid purple-magenta void shimmer at edges
    paint[:,:,0] = np.clip(paint[:,:,0] + edge_shimmer * 0.14 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + edge_shimmer * 0.22 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_spectral(paint, shape, mask, seed, pm, bb):
    """Spectral - ethereal desaturation with pale blue-white ghostly shimmer."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1041)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    shimmer = np.sin(y * np.pi * 12 + noise * 3) * 0.5 + 0.5
    gray = paint.mean(axis=2, keepdims=True)
    # BOOSTED: strong ethereal desaturation - fading from reality
    paint = paint * (1 - 0.42 * pm * mask[:,:,np.newaxis]) + gray * 0.42 * pm * mask[:,:,np.newaxis]
    # BOOSTED: deeper darkening for ghostly contrast
    paint = np.clip(paint - 0.18 * pm * mask[:,:,np.newaxis], 0, 1)
    shimmer_vis = np.clip(shimmer - 0.3, 0, 1) * 1.4
    # BOOSTED: bright white shimmer bands cutting through
    paint = np.clip(paint + shimmer_vis[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1)
    # BOOSTED: cold blue spectral tint
    paint[:,:,2] = np.clip(paint[:,:,2] + shimmer_vis * 0.14 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Neon & Glow (15 missing) - ULTRA LOW ROUGHNESS for glow-like brightness ---
spec_aurora_glow = make_flat_spec_fn(120, 8, 16, noise_M=25, noise_scales=[8, 16])
spec_blacklight_paint = make_flat_spec_fn(100, 10, 16, noise_M=20, noise_scales=[4, 8])
spec_bioluminescent_wave = make_effect_spec_fn(110, 8, 16, effect_type="gradient")
spec_electric_arc = make_effect_spec_fn(200, 5, 16, effect_type="noise")
spec_fluorescent = make_flat_spec_fn(90, 10, 16, noise_M=20, noise_scales=[8, 16])
spec_glow_stick = make_flat_spec_fn(80, 12, 16, noise_M=15, noise_scales=[4, 8])
spec_laser_show = make_effect_spec_fn(180, 5, 16, effect_type="bands")
spec_magnesium_burn = make_effect_spec_fn(240, 3, 16, effect_type="noise")
spec_neon_sign = make_flat_spec_fn(140, 8, 16, noise_M=25, noise_scales=[4, 8])
spec_phosphorescent = make_flat_spec_fn(100, 12, 16, noise_M=15, noise_scales=[8, 16])
spec_rave = make_flat_spec_fn(120, 8, 16, noise_M=30, noise_scales=[4, 8])
spec_sodium_lamp = make_flat_spec_fn(150, 10, 16, noise_M=20, noise_scales=[8, 16])
spec_tesla_coil = make_effect_spec_fn(200, 5, 16, effect_type="noise")
spec_tracer_round = make_effect_spec_fn(220, 4, 16, effect_type="gradient")
spec_welding_arc = make_effect_spec_fn(240, 3, 16, effect_type="noise")
def paint_aurora_glow(paint, shape, mask, seed, pm, bb):
    """Aurora Glow - flowing horizontal bands of green/purple/blue like northern lights."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Multiple wavy horizontal bands at different frequencies
    wave1 = np.sin(y * np.pi * 20 + np.sin(x * np.pi * 4) * 2) * 0.5 + 0.5
    wave2 = np.sin(y * np.pi * 35 + np.sin(x * np.pi * 6) * 1.5) * 0.5 + 0.5
    wave3 = np.sin(y * np.pi * 12 - np.sin(x * np.pi * 3) * 3) * 0.5 + 0.5
    # Green/teal core with purple edges
    band = (wave1 + wave2 * 0.5 + wave3 * 0.3) / 1.8
    blend = 0.30 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + (0.1 + band * 0.3) * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + (0.3 + band * 0.6) * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + (0.2 + (1 - band) * 0.5) * blend * mask, 0, 1)
    # Brighten band peaks
    bright = np.clip(band - 0.5, 0, 1) * 0.15 * pm
    paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blacklight_paint(paint, shape, mask, seed, pm, bb):
    """Blacklight Paint - UV reactive: hypersaturate + purple wash with bright hot spots."""
    h, w = shape
    # Boost saturation massively
    gray = (paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114)[:,:,np.newaxis]
    saturated = np.clip(paint + (paint - gray) * 1.2 * pm, 0, 1)
    # Purple UV wash overlay
    blend = 0.25 * pm
    saturated[:,:,0] = np.clip(saturated[:,:,0] + 0.15 * blend * mask, 0, 1)
    saturated[:,:,2] = np.clip(saturated[:,:,2] + 0.25 * blend * mask, 0, 1)
    paint = np.clip(paint * (1 - blend * mask[:,:,np.newaxis]) + saturated * blend * mask[:,:,np.newaxis], 0, 1)
    # Bright UV noise spots
    rng = np.random.RandomState(seed + 700)
    spots = rng.random(shape).astype(np.float32)
    hot = np.where(spots > 0.95, 0.18 * pm, 0.0)
    paint[:,:,2] = np.clip(paint[:,:,2] + hot * mask, 0, 1)
    return paint

def paint_bioluminescent_wave(paint, shape, mask, seed, pm, bb):
    """Bioluminescent Wave - horizontal sine wave glow bands in blue-green."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Organic wave motion
    wave = np.sin(y * np.pi * 16 + np.sin(x * np.pi * 8) * 1.5) * 0.5 + 0.5
    wave2 = np.sin(y * np.pi * 24 - x * np.pi * 5) * 0.5 + 0.5
    glow = np.clip((wave * 0.6 + wave2 * 0.4), 0, 1)
    blend = 0.30 * pm
    # Blue-green ocean bioluminescence
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * glow * mask), 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.35 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.25 * blend * mask, 0, 1)
    return paint

def paint_electric_arc(paint, shape, mask, seed, pm, bb):
    """Electric Arc - jagged lightning bolt lines crackling across surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 710)
    arc_map = np.zeros(shape, dtype=np.float32)
    # Generate several lightning bolts
    n_arcs = max(3, min(h, w) // 200)
    for _ in range(n_arcs):
        # Start from random edge point
        py = rng.randint(0, h)
        px = 0 if rng.random() > 0.5 else w - 1
        # Walk across with jagged steps
        for step in range(max(80, w // 8)):
            # Jagged movement
            py = np.clip(py + rng.randint(-6, 7), 0, h - 1)
            px = np.clip(px + (3 if px < w // 2 else -3), 0, w - 1)
            # Draw thick bolt
            y_lo = max(0, py - 2); y_hi = min(h, py + 3)
            x_lo = max(0, px - 1); x_hi = min(w, px + 2)
            arc_map[y_lo:y_hi, x_lo:x_hi] = 1.0
    # Dilate arcs for glow aura
    from PIL import Image as _Img, ImageFilter as _Filt
    arc_img = _Img.fromarray((arc_map * 255).astype(np.uint8))
    glow_img = arc_img.filter(_Filt.GaussianBlur(radius=max(2, min(h, w) // 120)))
    glow = np.array(glow_img).astype(np.float32) / 255.0
    combined = np.clip(arc_map * 1.0 + glow * 0.6, 0, 1)
    blend = combined * 0.40 * pm * mask
    # Blue-white electrical color
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * 0.3, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.5, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * 0.9, 0, 1)
    return paint

def paint_fluorescent(paint, shape, mask, seed, pm, bb):
    """Fluorescent - bright flat greenish-white glow with slight tube flicker."""
    h, w = shape
    # Harsh flat glow with horizontal tube bands
    y = np.arange(h, dtype=np.float32)
    tube_bands = (np.sin(y * np.pi / max(2, h // 12)) * 0.5 + 0.5)[:, np.newaxis]
    flicker = 0.85 + tube_bands * 0.15
    blend = 0.25 * pm
    # Greenish-white fluorescent
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.15 * blend * mask * flicker[:,:], 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.30 * blend * mask * flicker[:,:], 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.08 * blend * mask * flicker[:,:], 0, 1)
    # Overall brightness boost
    paint = np.clip(paint + 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_glow_stick(paint, shape, mask, seed, pm, bb):
    """Glow Stick - neon green chemical glow with bright contour lines + pulse variation."""
    from PIL import Image as _Img, ImageFilter as _Filt
    h, w = shape
    # Mask edge contours for glow tube effect
    mask_img = _Img.fromarray((mask * 255).astype(np.uint8))
    edges = np.array(mask_img.filter(_Filt.FIND_EDGES)).astype(np.float32) / 255.0
    edge_glow = np.array(_Img.fromarray((np.clip(edges * 3, 0, 1) * 255).astype(np.uint8)).filter(
        _Filt.GaussianBlur(radius=max(2, min(h, w) // 100)))).astype(np.float32) / 255.0
    # Pulsing noise variation
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 720)
    pulse = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    glow = np.clip(edge_glow * 1.5 + pulse * 0.5, 0, 1) * pm * mask
    # Chemical NEON green - kill red/blue, boost green hard
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - glow * 0.5) + glow * 0.03, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - glow * 0.3) + glow * 0.50, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - glow * 0.5), 0, 1)
    # Bright green core where glow peaks
    hot = np.clip((glow - 0.4) * 3, 0, 1) * 0.12
    paint[:,:,1] = np.clip(paint[:,:,1] + hot, 0, 1)
    return paint

def paint_laser_show(paint, shape, mask, seed, pm, bb):
    """Laser Show - thin bright beam lines radiating from random points."""
    h, w = shape
    rng = np.random.RandomState(seed + 730)
    beams = np.zeros(shape, dtype=np.float32)
    n_beams = max(4, min(h, w) // 150)
    # Generate thin beam lines at various angles
    for _ in range(n_beams):
        angle = rng.random() * np.pi
        cy = rng.randint(h // 4, 3 * h // 4)
        cx = rng.randint(w // 4, 3 * w // 4)
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        # Distance from beam line
        beam_dir_y = np.sin(angle)
        beam_dir_x = np.cos(angle)
        cross = np.abs((y - cy) * beam_dir_x - (x - cx) * beam_dir_y)
        beam = np.clip(1.0 - cross / max(2, min(h, w) // 400), 0, 1)
        color_idx = rng.randint(0, 3)
        beams = np.clip(beams + beam, 0, 1)
    blend = beams * 0.35 * pm * mask
    # Multi-color laser beams (RGB)
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * 0.8, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.3, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * 0.6, 0, 1)
    return paint

def paint_magnesium_burn(paint, shape, mask, seed, pm, bb):
    """Magnesium Burn - large centered white-hot bloom covering most of surface."""
    h, w = shape
    cy, cx = h * 0.5, w * 0.5  # True center
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt(((y - cy) / h)**2 + ((x - cx) / w)**2)
    # Large bloom covering ~80% of surface
    bloom = np.clip(1.0 - dist * 1.5, 0, 1) ** 1.5
    # Outer glow ring
    outer = np.clip(1.0 - dist * 1.0, 0, 1) * 0.3
    combined = np.clip(bloom + outer, 0, 1)
    blend = combined * 0.50 * pm * mask
    # White-hot center with slight blue tint
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * 0.90, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.88, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * 0.95, 0, 1)
    return paint

def paint_neon_sign(paint, shape, mask, seed, pm, bb):
    """Neon Sign - bright edge contour glow in hot pink, like a neon tube."""
    from PIL import Image as _Img, ImageFilter as _Filt
    h, w = shape
    # Detect mask edges for tube-like contour glow
    mask_img = _Img.fromarray((mask * 255).astype(np.uint8))
    edges = np.array(mask_img.filter(_Filt.FIND_EDGES)).astype(np.float32) / 255.0
    # Widen for neon tube thickness
    edge_bright = np.clip(edges * 4, 0, 1)
    edge_img = _Img.fromarray((edge_bright * 255).astype(np.uint8))
    tube = np.array(edge_img.filter(_Filt.GaussianBlur(radius=max(3, min(h, w) // 60)))).astype(np.float32) / 255.0
    # Add interior noise glow
    noise = _multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 740)
    noise_glow = np.clip((noise - noise.min()) / (noise.max() - noise.min() + 1e-8) - 0.4, 0, 1) * 0.4
    combined = np.clip(tube + noise_glow, 0, 1)
    blend = combined * 0.40 * pm * mask
    # Hot pink neon
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * 0.85, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.05, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * 0.35, 0, 1)
    return paint

def paint_phosphorescent(paint, shape, mask, seed, pm, bb):
    """Phosphorescent - glows brighter in dark areas (stored charge release)."""
    h, w = shape
    gray = paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114
    # Glow is inverse of brightness - darker areas glow more
    glow_intensity = np.clip(1.0 - gray * 1.5, 0, 1)
    blend = glow_intensity * 0.30 * pm * mask
    # Pale green phosphorescent glow
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * 0.10, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.55, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * 0.15, 0, 1)
    return paint

def paint_rave(paint, shape, mask, seed, pm, bb):
    """Rave - dense small neon confetti blocks covering the surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 750)
    result = paint.copy()
    # Much smaller blocks for dense confetti look
    block_h = max(3, h // 80)
    block_w = max(3, w // 80)
    neon_colors = [
        (1.0, 0.0, 0.5),  (0.0, 1.0, 0.0),  (0.0, 0.5, 1.0),
        (1.0, 1.0, 0.0),  (0.8, 0.0, 1.0),  (1.0, 0.3, 0.0),
        (0.0, 1.0, 1.0),  (1.0, 0.0, 1.0),
    ]
    # Many blocks for dense coverage
    n_blocks = max(60, (h * w) // (block_h * block_w * 2))
    for _ in range(n_blocks):
        by = rng.randint(0, max(1, h - block_h))
        bx = rng.randint(0, max(1, w - block_w))
        color = neon_colors[rng.randint(0, len(neon_colors))]
        bm = mask[by:by+block_h, bx:bx+block_w]
        blend = 0.40 * pm
        for c in range(3):
            result[by:by+block_h, bx:bx+block_w, c] = np.clip(
                result[by:by+block_h, bx:bx+block_w, c] * (1 - bm * blend) +
                color[c] * bm * blend, 0, 1)
    return result

def paint_sodium_lamp(paint, shape, mask, seed, pm, bb):
    """Sodium Lamp - flat amber/orange monochromatic wash (street light effect)."""
    h, w = shape
    gray = paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114
    blend = 0.35 * pm
    # Convert to amber monochrome
    amber_r = gray * 0.95
    amber_g = gray * 0.65
    amber_b = gray * 0.15
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + amber_r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + amber_g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + amber_b * mask * blend, 0, 1)
    return paint

def paint_tesla_coil(paint, shape, mask, seed, pm, bb):
    """Tesla Coil - dense branching arc discharge covering full surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 760)
    arcs = np.zeros(shape, dtype=np.float32)
    # Many bolts from ALL edges for full surface coverage
    n_bolts = max(8, min(h, w) // 80)
    for i in range(n_bolts):
        # Alternate start edge: top, bottom, left, right
        edge = i % 4
        if edge == 0:  # top
            py, px = 0, rng.randint(0, w)
        elif edge == 1:  # bottom
            py, px = h - 1, rng.randint(0, w)
        elif edge == 2:  # left
            py, px = rng.randint(0, h), 0
        else:  # right
            py, px = rng.randint(0, h), w - 1
        # Walk across surface with jagged random walk
        for step in range(max(100, max(h, w) // 4)):
            # Move toward center-ish with jag
            dy = rng.randint(-4, 5) + (1 if py < h // 2 else -1)
            dx = rng.randint(-4, 5) + (1 if px < w // 2 else -1)
            py = np.clip(py + dy, 0, h - 1)
            px = np.clip(px + dx, 0, w - 1)
            arcs[max(0,py-1):min(h,py+2), max(0,px-1):min(w,px+2)] = 1.0
            # Branch frequently
            if rng.random() > 0.80:
                bpx, bpy = px, py
                for bs in range(rng.randint(8, 25)):
                    bpy = np.clip(bpy + rng.randint(-3, 4), 0, h - 1)
                    bpx = np.clip(bpx + rng.randint(-3, 4), 0, w - 1)
                    arcs[max(0,bpy-1):min(h,bpy+1), max(0,bpx-1):min(w,bpx+1)] = 0.7
    # Glow aura
    from PIL import Image as _Img, ImageFilter as _Filt
    arc_img = _Img.fromarray((np.clip(arcs, 0, 1) * 255).astype(np.uint8))
    glow = np.array(arc_img.filter(_Filt.GaussianBlur(radius=max(3, min(h, w) // 100)))).astype(np.float32) / 255.0
    combined = np.clip(arcs + glow * 0.5, 0, 1) * pm * mask
    # Blue-purple electrical
    paint[:,:,0] = np.clip(paint[:,:,0] + combined * 0.25, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + combined * 0.15, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + combined * 0.80, 0, 1)
    return paint

def paint_tracer_round(paint, shape, mask, seed, pm, bb):
    """Tracer Round - bright diagonal streak lines across surface."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Multiple diagonal streak lines
    streaks = np.zeros(shape, dtype=np.float32)
    for offset in [0.0, 0.25, 0.5, 0.75]:
        line = np.abs((y * 2 + x * 3 + offset) % 1.0 - 0.5) * 2
        streak = np.clip(1.0 - line * 15, 0, 1)
        streaks = np.clip(streaks + streak, 0, 1)
    blend = streaks * 0.35 * pm * mask
    # Orange-yellow tracer glow
    paint[:,:,0] = np.clip(paint[:,:,0] + blend * 0.85, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + blend * 0.50, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + blend * 0.05, 0, 1)
    return paint

def paint_welding_arc(paint, shape, mask, seed, pm, bb):
    """Welding Arc - intense blue-white point bloom with scatter sparks."""
    h, w = shape
    rng = np.random.RandomState(seed + 770)
    # Multiple bright arc points
    n_points = max(2, min(h, w) // 400)
    bloom = np.zeros(shape, dtype=np.float32)
    for _ in range(n_points):
        cy = rng.randint(h // 6, 5 * h // 6)
        cx = rng.randint(w // 6, 5 * w // 6)
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        dist = np.sqrt(((y - cy) / h)**2 + ((x - cx) / w)**2)
        point_bloom = np.clip(1.0 - dist * 5.0, 0, 1) ** 2
        bloom = np.clip(bloom + point_bloom, 0, 1)
    # Scatter sparks
    sparks = rng.random(shape).astype(np.float32)
    spark_map = np.where(sparks > 0.985, 0.5, 0.0) * mask * pm
    combined = (bloom * 0.40 * pm * mask) + spark_map
    # Blue-white arc color
    paint[:,:,0] = np.clip(paint[:,:,0] + combined * 0.55, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + combined * 0.60, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + combined * 0.95, 0, 1)
    return paint

# --- Texture & Surface (4 remaining - custom procedural) ---

def spec_granite(shape, mask, seed, sm):
    """Granite - polished speckled stone: mixed low metallic with variable roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1300)
    speckle = _multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 1301)
    M = 40 + speckle * 30 + noise * 10 * sm
    R = 80 + noise * 50 + speckle * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 180; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_obsidian_glass(shape, mask, seed, sm):
    """Obsidian Glass - volcanic glass: very low roughness, subtle metallic shimmer."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1310)
    M = 25 + noise * 12 * sm
    R = 6 + noise * 5 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_slate_tile(shape, mask, seed, sm):
    """Slate Tile - natural layered stone: directional roughness bands."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1320)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    layers = np.sin(y * np.pi * 40 + noise * 2) * 0.5 + 0.5
    M = 30 + layers * 15 + noise * 8 * sm
    R = 110 + (1 - layers) * 50 + noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 160; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def spec_volcanic_rock(shape, mask, seed, sm):
    """Volcanic Rock - rough pumice: very high roughness with air pocket variation."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1330)
    pores = np.where(noise > 0.5, (noise - 0.5) * 2, 0).astype(np.float32)
    M = 20 + noise * 10 * sm
    R = 140 + pores * 60 + noise * 25 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 220; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # CC was 0=mirror
    return spec

def paint_granite(paint, shape, mask, seed, pm, bb):
    """Granite - speckled stone desaturation with mineral grain noise."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 1302)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.18 * pm * mask[:,:,np.newaxis]) + gray * 0.18 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_obsidian_glass(paint, shape, mask, seed, pm, bb):
    """Obsidian Glass - deep darkening with smooth glassy depth."""
    h, w = shape
    paint = np.clip(paint - 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.08 * pm * mask[:,:,np.newaxis]) + gray * 0.08 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_slate_tile(paint, shape, mask, seed, pm, bb):
    """Slate Tile - cool gray-blue desaturation with layered texture."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1321)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.15 * pm * mask[:,:,np.newaxis]) + gray * 0.15 * pm * mask[:,:,np.newaxis]
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_volcanic_rock(paint, shape, mask, seed, pm, bb):
    """Volcanic Rock - dark rough surface with porous texture variation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 1331)
    paint = np.clip(paint - 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.14 * pm * mask[:,:,np.newaxis]) + gray * 0.14 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + noise[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Vintage & Retro (17 missing) ---
spec_art_deco_gold = make_flat_spec_fn(200, 10, 16, noise_M=20, noise_scales=[8, 16, 32])
spec_beat_up_truck = make_flat_spec_fn(50, 140, 160, noise_R=35, noise_scales=[4, 8, 16])  # CC was 0=mirror
spec_classic_racing = make_flat_spec_fn(120, 25, 16, noise_M=20, noise_scales=[8, 16])
spec_daguerreotype = make_flat_spec_fn(60, 80, 40, noise_R=20, noise_scales=[8, 16, 32])  # CC was 0=mirror
spec_diner_chrome = make_flat_spec_fn(220, 5, 16, noise_M=15, noise_scales=[16, 32])
spec_faded_glory = make_flat_spec_fn(80, 90, 120, noise_R=25, noise_scales=[4, 8, 16])  # CC was 0=mirror
spec_grindhouse = make_flat_spec_fn(50, 100, 80, noise_R=30, noise_scales=[4, 8])  # CC was 0=mirror
spec_jukebox = make_flat_spec_fn(160, 15, 16, noise_M=20, noise_scales=[8, 16])
spec_moonshine = make_flat_spec_fn(40, 60, 80, noise_R=20, noise_scales=[8, 16, 32])  # CC was 0=mirror
spec_nascar_heritage = make_flat_spec_fn(140, 20, 16, noise_M=20, noise_scales=[8, 16])
spec_nostalgia_drag = make_flat_spec_fn(100, 30, 16, noise_M=20, noise_R=15, noise_scales=[4, 8])
spec_old_school = make_flat_spec_fn(90, 50, 16, noise_R=20, noise_scales=[8, 16])
spec_psychedelic = make_effect_spec_fn(80, 30, 16, effect_type="radial")
spec_sepia = make_flat_spec_fn(60, 70, 40, noise_R=15, noise_scales=[8, 16, 32])  # CC was 0=mirror
spec_tin_type = make_flat_spec_fn(100, 60, 40, noise_R=20, noise_scales=[8, 16])  # CC was 0=mirror
spec_woodie = make_flat_spec_fn(50, 100, 80, noise_R=25, noise_scales=[4, 8, 16])  # CC was 0=mirror
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

# --- Surreal & Fantasy (14 remaining - TOTAL REWRITE custom procedural) ---

def spec_astral(shape, mask, seed, sm):
    """Astral - ethereal projection: gradient metallic with soft glow bands."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1800)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    glow = np.sin(y * np.pi * 10 + noise * 3) * 0.5 + 0.5
    M = 50 + glow * 50 + noise * 10 * sm
    R = 20 + (1 - glow) * 20 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_crystal_cave(shape, mask, seed, sm):
    """Crystal Cave - gemstone facets: high metallic with sharp crystalline facets."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1810)
    facets = np.sin(noise * 12) * 0.5 + 0.5
    edges = np.where(np.abs(facets - 0.5) < 0.06, 1.0, 0.0).astype(np.float32)
    M = 100 + facets * 80 + noise * 15 * sm
    R = 8 + edges * 25 + noise * 6 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_dark_fairy(shape, mask, seed, sm):
    """Dark Fairy - twisted magic: low metallic with glowing accent channels."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1820)
    magic = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    magic_s = gaussian_filter(magic, sigma=max(1, h * 0.004))
    M = 30 + magic_s * 60 + noise * 8 * sm
    R = 70 + (1 - magic_s) * 40 + noise * 12 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(magic_s * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_dragon_breath(shape, mask, seed, sm):
    """Dragon Breath - hot exhale: bright metallic with fire-gradient roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1830)
    heat = np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 100 + heat * 80 + noise * 15 * sm
    R = 8 + (1 - heat) * 25 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_enchanted(shape, mask, seed, sm):
    """Enchanted - magical sparkle: shimmer spots in smooth glossy base."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1840)
    sparkle = np.where(noise > 0.6, (noise - 0.6) / 0.4, 0).astype(np.float32)
    M = 40 + sparkle * 80 + noise * 10 * sm
    R = 20 + (1 - sparkle) * 20 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_ethereal(shape, mask, seed, sm):
    """Ethereal - otherworldly presence: ghostly smooth with soft shimmer."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1850)
    ghost = np.clip(noise * 0.5 + 0.5, 0, 1)
    M = 30 + ghost * 25 + noise * 8 * sm
    R = 25 + ghost * 15 + noise * 6 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_fractal_dimension(shape, mask, seed, sm):
    """Fractal Dimension - recursive depth: radial metallic rings diminishing."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1860)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    rings = np.sin(dist * np.pi * 25 + noise * 3) * 0.5 + 0.5
    M = 60 + rings * 60 + noise * 12 * sm
    R = 15 + (1 - rings) * 20 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_hallucination(shape, mask, seed, sm):
    """Hallucination - visual warping: multi-frequency undulation of M and R."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1870)
    warp1 = np.sin(noise * 8) * 0.5 + 0.5
    warp2 = np.sin(noise * 12 + 2.0) * 0.5 + 0.5
    M = 40 + warp1 * 80 + warp2 * 30 + noise * 12 * sm
    R = 15 + (1 - warp1) * 30 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_levitation(shape, mask, seed, sm):
    """Levitation - anti-gravity aura: upward gradient metallic lift."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1880)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    lift = np.clip(1.0 - y, 0, 1)
    M = 30 + lift * 50 + noise * 10 * sm
    R = 20 + (1 - lift) * 20 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_multiverse(shape, mask, seed, sm):
    """Multiverse - parallel overlap: radial rings with alternating material zones."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1890)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    rings = np.sin(dist * np.pi * 20 + noise * 4) * 0.5 + 0.5
    M = 50 + rings * 80 + noise * 12 * sm
    R = 15 + (1 - rings) * 30 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_nebula_core(shape, mask, seed, sm):
    """Nebula Core - dense star nursery: bright metallic glow spots in dark base."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1900)
    stars = np.where(noise > 0.55, (noise - 0.55) / 0.45, 0).astype(np.float32)
    M = 30 + stars * 120 + noise * 10 * sm
    R = 60 - stars * 40 + noise * 10 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(stars * 12 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_simulation(shape, mask, seed, sm):
    """Simulation - matrix code: horizontal band metallic with digital steps."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1910)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    scan = np.sin(y * np.pi * 50 + noise * 2) * 0.5 + 0.5
    M = 50 + scan * 40 + noise * 10 * sm
    R = 20 + (1 - scan) * 20 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_tesseract(shape, mask, seed, sm):
    """Tesseract - 4D projection: geometric metallic facets with edge highlights."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1920)
    facets = np.sin(noise * 14) * 0.5 + 0.5
    edges = np.where(np.abs(facets - 0.5) < 0.05, 1.0, 0.0).astype(np.float32)
    M = 80 + facets * 80 + noise * 12 * sm
    R = 10 + edges * 30 + noise * 8 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(16 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_void_walker(shape, mask, seed, sm):
    """Void Walker - dimensional void: near-zero metallic, extreme roughness."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1930)
    void_edge = np.clip(np.abs(noise) * 3, 0, 1)
    shimmer = np.where(void_edge > 0.8, (void_edge - 0.8) / 0.2, 0).astype(np.float32)
    M = 5 + shimmer * 40 + noise * 5 * sm
    R = 180 - shimmer * 80 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(shimmer * 10 * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_astral(paint, shape, mask, seed, pm, bb):
    """Astral - ethereal blue-purple glow bands overlaid on base."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1801)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    glow = np.sin(y * np.pi * 10 + noise * 3) * 0.5 + 0.5
    band = np.clip(glow - 0.4, 0, 1) * 1.7
    paint[:,:,0] = np.clip(paint[:,:,0] + band * 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + band * 0.06 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + band * 0.12 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_crystal_cave(paint, shape, mask, seed, pm, bb):
    """Crystal Cave - gemstone facet highlights with prismatic color hints."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1811)
    facets = np.sin(noise * 12) * 0.5 + 0.5
    bright = np.where(facets > 0.7, (facets - 0.7) / 0.3, 0).astype(np.float32)
    paint = np.clip(paint + bright[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    phase = noise * np.pi * 2
    paint[:,:,0] = np.clip(paint[:,:,0] + np.sin(phase) * 0.03 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.sin(phase + 2) * 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dark_fairy(paint, shape, mask, seed, pm, bb):
    """Dark Fairy - twisted purple-green magic glow channels."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1821)
    magic = np.where(np.abs(noise) < 0.06, 1.0, 0.0).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    magic_glow = gaussian_filter(magic, sigma=max(2, h * 0.008))
    paint = np.clip(paint - 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + magic_glow * 0.10 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + magic_glow * 0.15 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_dragon_breath(paint, shape, mask, seed, pm, bb):
    """Dragon Breath - hot exhale: gradient orange-red fire overlay."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1831)
    heat = np.clip(noise * 0.5 + 0.5, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + heat * 0.12 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + heat * 0.05 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - heat * 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_enchanted(paint, shape, mask, seed, pm, bb):
    """Enchanted - magical green-gold sparkle spots over glossy base."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1841)
    sparkle = np.where(noise > 0.6, (noise - 0.6) / 0.4, 0).astype(np.float32)
    paint[:,:,1] = np.clip(paint[:,:,1] + sparkle * 0.10 * pm * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + sparkle * 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_ethereal(paint, shape, mask, seed, pm, bb):
    """Ethereal - otherworldly soft glow with gentle desaturation."""
    h, w = shape
    noise = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1851)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.10 * pm * mask[:,:,np.newaxis]) + gray * 0.10 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_fractal_dimension(paint, shape, mask, seed, pm, bb):
    """Fractal Dimension - recursive depth rings with color shifting."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1861)
    phase = noise * np.pi * 2
    paint[:,:,0] = np.clip(paint[:,:,0] + np.sin(phase) * 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + np.sin(phase + 2.5) * 0.06 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.sin(phase + 5.0) * 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hallucination(paint, shape, mask, seed, pm, bb):
    """Hallucination - warping rainbow color morph across surface."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1871)
    phase = noise * np.pi * 3
    paint[:,:,0] = np.clip(paint[:,:,0] + np.sin(phase) * 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + np.sin(phase + 2.1) * 0.08 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.sin(phase + 4.2) * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_levitation(paint, shape, mask, seed, pm, bb):
    """Levitation - anti-gravity: upward lightening with shimmer aura."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    lift = np.clip(1.0 - y, 0, 1)
    paint = np.clip(paint + lift[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + lift * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_multiverse(paint, shape, mask, seed, pm, bb):
    """Multiverse - parallel universe overlap: radial color shifts."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1891)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    dist = np.sqrt((y - 0.5)**2 + (x - 0.5)**2)
    rings = np.sin(dist * np.pi * 20 + noise * 4) * 0.5 + 0.5
    phase = rings * np.pi * 2
    paint[:,:,0] = np.clip(paint[:,:,0] + np.sin(phase) * 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + np.sin(phase + 2) * 0.06 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.sin(phase + 4) * 0.06 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_nebula_core(paint, shape, mask, seed, pm, bb):
    """Nebula Core - dense star nursery: purple-magenta glow with bright spots."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 1901)
    stars = np.where(noise > 0.55, (noise - 0.55) / 0.45, 0).astype(np.float32)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.06 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + stars[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_simulation(paint, shape, mask, seed, pm, bb):
    """Simulation - matrix green code rain scanlines."""
    h, w = shape
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1911)
    y = np.arange(h, dtype=np.float32).reshape(-1, 1) / max(h - 1, 1)
    scan = np.sin(y * np.pi * 50 + noise * 2) * 0.5 + 0.5
    lines = np.clip(scan - 0.6, 0, 1) * 2.5
    paint[:,:,1] = np.clip(paint[:,:,1] + lines * 0.12 * pm * mask, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + lines * 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_tesseract(paint, shape, mask, seed, pm, bb):
    """Tesseract - 4D projection: geometric facet highlights with cold tint."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1921)
    facets = np.sin(noise * 14) * 0.5 + 0.5
    edges = np.where(np.abs(facets - 0.5) < 0.05, 1.0, 0.0).astype(np.float32)
    paint = np.clip(paint + edges[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + facets * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_void_walker(paint, shape, mask, seed, pm, bb):
    """Void Walker - dimensional void: deep darkness with edge shimmer."""
    h, w = shape
    noise = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1931)
    void_edge = np.clip(np.abs(noise) * 3, 0, 1)
    shimmer = np.where(void_edge > 0.8, (void_edge - 0.8) / 0.2, 0).astype(np.float32)
    paint = np.clip(paint - 0.15 * pm * mask[:,:,np.newaxis], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.12 * pm * mask[:,:,np.newaxis]) + gray * 0.12 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + shimmer * 0.06 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shimmer * 0.08 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- Novelty & Fun (11 missing) ---
spec_aged_leather = make_flat_spec_fn(40, 130, 180, noise_R=25, noise_scales=[4, 8, 16])  # CC was 0=mirror
spec_bark = make_flat_spec_fn(30, 150, 200, noise_R=30, noise_scales=[4, 8, 16])  # CC was 0=mirror
spec_bone = make_flat_spec_fn(60, 80, 100, noise_R=20, noise_scales=[8, 16])  # CC was 0=mirror
spec_brick_wall = make_flat_spec_fn(35, 160, 220, noise_R=25, noise_scales=[4, 8])  # CC was 0=mirror
spec_burlap = make_flat_spec_fn(20, 170, 230, noise_R=30, noise_scales=[2, 4, 8])  # CC was 0=mirror
spec_cork = make_flat_spec_fn(25, 140, 200, noise_R=25, noise_scales=[2, 4, 8])  # CC was 0=mirror
spec_linen = make_flat_spec_fn(30, 120, 160, noise_R=20, noise_scales=[4, 8])  # CC was 0=mirror
spec_parchment = make_flat_spec_fn(50, 100, 140, noise_R=20, noise_scales=[8, 16, 32])  # CC was 0=mirror
spec_stucco = make_flat_spec_fn(40, 150, 220, noise_R=30, noise_scales=[2, 4, 8])  # CC was 0=mirror
spec_suede = make_flat_spec_fn(20, 160, 200, noise_R=20, noise_scales=[8, 16])  # CC was 0=mirror
spec_terra_cotta = make_flat_spec_fn(35, 140, 180, noise_R=25, noise_scales=[4, 8, 16])  # CC was 0=mirror
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
# Format: (spec_fn, paint_fn) tuples - same as existing MONOLITHIC_REGISTRY

EXPANSION_MONOLITHICS = {
    # Group 1: Chameleon Classic (new entries - chameleon_midnight thru chameleon_copper, mystichrome exist)
    "chameleon_amethyst":   (spec_chameleon_amethyst, paint_chameleon_amethyst),
    "chameleon_emerald":    (spec_chameleon_emerald, paint_chameleon_emerald),
    "chameleon_obsidian":   (spec_chameleon_obsidian, paint_chameleon_obsidian),
    # Group 2: Color Shift Adaptive (new entries - cs_warm thru cs_extreme exist)
    "cs_complementary":     (spec_cs_complementary, paint_cs_complementary),
    "cs_triadic":           (spec_cs_triadic, paint_cs_triadic),
    "cs_split":             (spec_cs_split, paint_cs_split),
    # Group 3: Color Shift Preset (new entries - cs_emerald thru cs_mystichrome exist)
    "cs_neon_dreams":       (spec_cs_neon_dreams, paint_cs_neon_dreams),
    "cs_twilight":          (spec_cs_twilight, paint_cs_twilight),
    "cs_toxic":             (spec_cs_toxic, paint_cs_toxic),
    # Group 4: Prizm Series (new entries - prizm_holographic thru prizm_adaptive exist)
    "prizm_neon":           (spec_prizm_neon, paint_prizm_neon),
    "prizm_blood_moon":     (spec_prizm_blood_moon, paint_prizm_blood_moon),
    # Group 5: Effect & Visual (new entries - phantom thru thermochromic exist)
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
    # Group 7: Weather & Element (new entries - frost_bite thru oil_slick exist)
    "tornado_alley":        (spec_tornado_alley, paint_tornado_alley),
    "volcanic_glass":       (spec_volcanic_glass, paint_volcanic_glass),
    "frozen_lake":          (spec_frozen_lake, paint_frozen_lake),
    "desert_mirage":        (spec_desert_mirage, paint_desert_mirage),
    "ocean_floor":          (spec_ocean_floor, paint_ocean_floor),
    "meteor_shower":        (spec_meteor_shower, paint_meteor_shower),
    # Group 8: Dark & Gothic (new entries - worn_chrome, rust, weathered_paint exist)
    "voodoo":               (spec_voodoo, paint_voodoo),
    "reaper":               (spec_reaper, paint_reaper),
    "possessed":            (spec_possessed, paint_possessed),
    "wraith":               (spec_wraith, paint_wraith),
    "cursed":               (spec_cursed, paint_cursed),
    "eclipse":              (spec_eclipse, paint_eclipse),
    "nightmare":            (spec_nightmare, paint_nightmare),
})

EXPANSION_MONOLITHICS.update({
    # Group 9: Luxury & Exotic (new entries - galaxy exists)
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

# =============================================================================
# GAP-FILLING MONOLITHICS - March 2026 (v5 audit additions)
# Fills the identified "rough metal / industrial / no-CC" coverage holes
# All 12 entries have unique spec textures - NOT static M/G/CC fills
# =============================================================================

# --- Rough Full-Metal + No-CC Zone (M=180-255, G=170-240, CC=0) ---
# Almost zero coverage existed here before

def spec_mill_scale(shape, mask, seed, sm):
    """Mill Scale - hot-rolled steel straight from the mill.
    Dark flaky oxide layer: irregular metallic patches over rough substrate."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    base_noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 3100)
    fine_noise  = _multi_scale_noise(shape, [2, 4], [0.6, 0.4], seed + 3101)
    # Flaky oxide patches - noise-threshold creates irregular plate edges
    flakes = np.where(base_noise > 0.15, (base_noise - 0.15) / 0.85, 0).astype(np.float32)
    # Where flake is thick: medium-high M, high R. Bare metal under: high M, medium R.
    M  = 170 + flakes * 45 - fine_noise * 20 * sm
    R  = 185 + (1 - flakes) * 40 + fine_noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 180*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 220  # CC was 0=mirror
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_mill_scale(paint, shape, mask, seed, pm, bb):
    """Mill Scale - dark blue-gray oxide, heavy desaturation with warm bare-metal glints."""
    h, w = shape
    base_noise = _multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 3100)
    flakes = np.where(base_noise > 0.15, (base_noise - 0.15) / 0.85, 0).astype(np.float32)
    gray = paint.mean(axis=2, keepdims=True)
    # Heavy desaturation - mill scale is near-black oxide
    paint = paint * (1 - 0.30 * pm * mask[:,:,np.newaxis]) + gray * 0.30 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    # Where oxide thins: warm silver glints
    paint[:,:,0] = np.clip(paint[:,:,0] + (1-flakes) * 0.06 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + (1-flakes) * 0.04 * pm * mask, 0, 1)
    # Slight blue-steel tint in thick oxide zones
    paint[:,:,2] = np.clip(paint[:,:,2] + flakes * 0.04 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)


def spec_grinding_marks(shape, mask, seed, sm):
    """Grinding Marks - angle-grinder surface: strong directional scratch pattern.
    Long radial streaks from the grinding disc with raw high-metallic exposure."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Directional streaks: vary roughness heavily along one axis
    x_noise = _multi_scale_noise(shape, [2, 3, 6], [0.5, 0.3, 0.2], seed + 3110)
    base_noise = _multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 3111)
    # The grinding creates alternating bright/rough bands
    streak = np.abs(np.sin(x_noise * 18 + base_noise * 2)) ** 0.4
    M = 210 + streak * 30 + base_noise * 10 * sm
    R = 160 + (1 - streak) * 50 + x_noise * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 180*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 180  # CC was 0=mirror
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_grinding_marks(paint, shape, mask, seed, pm, bb):
    """Grinding Marks - bright silver-white in streak highlights, dull between."""
    h, w = shape
    x_noise = _multi_scale_noise(shape, [2, 3, 6], [0.5, 0.3, 0.2], seed + 3110)
    base_noise = _multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 3111)
    streak = np.abs(np.sin(x_noise * 18 + base_noise * 2)) ** 0.4
    gray = paint.mean(axis=2, keepdims=True)
    # Partial desaturation on the whole surface
    paint = paint * (1 - 0.20 * pm * mask[:,:,np.newaxis]) + gray * 0.20 * pm * mask[:,:,np.newaxis]
    # Brightening at streak peaks = fresh exposed metal
    highlights = np.clip((streak - 0.5) * 2, 0, 1)
    paint = np.clip(paint + highlights[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)


def spec_raw_weld(shape, mask, seed, sm):
    """Raw Weld - unground weld bead: rippled oxidized seam cutting across the surface.
    Alternating oxidation zones create iridescent rainbow heat colors."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 3120)
    # Ripple pattern from weld bead
    bead = np.sin((y + noise * 0.08) * np.pi * 30) * 0.5 + 0.5
    heat_zones = np.sin((y + noise * 0.05) * np.pi * 8) * 0.5 + 0.5  # Heat spread
    M = 130 + heat_zones * 60 + noise * 15 * sm
    R = 90 + bead * 80 + noise * 20 * sm      # Rough bead, smoother between
    CC_val = np.clip((1 - heat_zones) * 16, 16, 255)  # Slight CC at cooler zones only
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 150*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC_val * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_raw_weld(paint, shape, mask, seed, pm, bb):
    """Raw Weld - rainbow heat oxidation: blue/gold/purple iridescence in heat zones."""
    h, w = shape
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    noise = _multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 3120)
    heat_zones = np.sin((y + noise * 0.05) * np.pi * 8) * 0.5 + 0.5
    # Heat oxidation colors: gold -> blue -> purple as temperature decreases from seam
    paint[:,:,0] = np.clip(paint[:,:,0] + heat_zones * 0.12 * pm * mask, 0, 1)  # Gold/copper
    paint[:,:,1] = np.clip(paint[:,:,1] + (1-heat_zones) * 0.06 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + (1-heat_zones) * 0.10 * pm * mask, 0, 1)  # Blue outer
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.08 * pm * mask[:,:,np.newaxis]) + gray * 0.08 * pm * mask[:,:,np.newaxis]
    return np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)


# --- Semi-Metal Rough + No-CC Zone (M=100-170, G=180-240, CC=0) ---

def spec_bare_aluminum(shape, mask, seed, sm):
    """Bare Aluminum - uncoated machined aluminum with visible tooling marks.
    Medium metallic, moderate roughness, zero CC. Looks dull but still metallic."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    tool_noise = _multi_scale_noise(shape, [3, 6, 12], [0.4, 0.4, 0.2], seed + 3130)
    grain_noise = _multi_scale_noise(shape, [2, 4], [0.6, 0.4], seed + 3131)
    # Light tooling lines in one direction
    tool_marks = np.abs(np.sin(tool_noise * 12)) ** 0.5
    M = 165 + grain_noise * 20 * sm
    R = 85 + tool_marks * 60 + grain_noise * 18 * sm
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 120*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 160  # CC was 0=mirror
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_bare_aluminum(paint, shape, mask, seed, pm, bb):
    """Bare Aluminum - cool gray-silver with slight tooling directional highlights."""
    h, w = shape
    tool_noise = _multi_scale_noise(shape, [3, 6, 12], [0.4, 0.4, 0.2], seed + 3130)
    tool_marks = np.abs(np.sin(tool_noise * 12)) ** 0.5
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.22 * pm * mask[:,:,np.newaxis]) + gray * 0.22 * pm * mask[:,:,np.newaxis]
    # Very slight blue-cool tone (aluminum is cooler than steel)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.04 * pm * mask, 0, 1)
    # Tooling line bright flashes
    bright = np.clip((tool_marks - 0.7) * 3.3, 0, 1)
    paint = np.clip(paint + bright[:,:,np.newaxis] * 0.07 * pm * mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)


def spec_phosphate_coat(shape, mask, seed, sm):
    """Phosphate Coat - military phosphating: matte gray-green semi-metallic surface.
    Used on gun parts and mil-spec hardware. Zero sheen, fine crystalline texture."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    crystal_noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 3140)
    large_noise   = _multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 3141)
    # Fine crystalline phosphate surface - micro-rough
    M = 110 + crystal_noise * 25 * sm + large_noise * 15
    R = 190 + crystal_noise * 30 * sm
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 180*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 200  # CC was 0=mirror
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_phosphate_coat(paint, shape, mask, seed, pm, bb):
    """Phosphate Coat - flat gray-green military matte. Desaturates to near-neutral."""
    h, w = shape
    crystal_noise = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 3140)
    gray = paint.mean(axis=2, keepdims=True)
    # Very heavy desaturation - phosphate is extremely matte
    paint = paint * (1 - 0.40 * pm * mask[:,:,np.newaxis]) + gray * 0.40 * pm * mask[:,:,np.newaxis]
    # Slight olive/green tinge (phosphate's characteristic color)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.03 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.02 * pm * mask, 0, 1)
    paint = np.clip(paint + crystal_noise[:,:,np.newaxis] * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)


# --- Dielectric Rough No-CC Zone (M=0-20, G=180-255, CC=0) ---

def spec_raw_concrete(shape, mask, seed, sm):
    """Raw Concrete - unpainted poured concrete with aggregate exposure.
    Coarse multi-scale grain: near-zero metallic, very high roughness, no CC."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    agg = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 3150)   # Fine aggregate
    form = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 3151) # Form-board marks
    # Aggregates create slight metallic glint (quartz/mica in concrete)
    minerals = np.where(agg > 0.55, (agg - 0.55) / 0.45, 0).astype(np.float32)
    M = 5 + minerals * 20 + form * 5 * sm
    R = 190 + agg * 40 + form * 20 * sm
    spec[:,:,0] = np.clip(M * mask + 2*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 200*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 250  # CC was 0=mirror
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_raw_concrete(paint, shape, mask, seed, pm, bb):
    """Raw Concrete - gray mineral surface, heavy desaturation with aggregate glints."""
    h, w = shape
    agg = _multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 3150)
    form = _multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 3151)
    minerals = np.where(agg > 0.55, (agg - 0.55) / 0.45, 0).astype(np.float32)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.45 * pm * mask[:,:,np.newaxis]) + gray * 0.45 * pm * mask[:,:,np.newaxis]
    # Warm aggregate mineral flints
    paint[:,:,0] = np.clip(paint[:,:,0] + minerals * 0.05 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + minerals * 0.04 * pm * mask, 0, 1)
    # Form-board shadow banding
    paint = np.clip(paint - form[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:,:,np.newaxis], 0, 1)


def spec_worn_asphalt(shape, mask, seed, sm):
    """Worn Asphalt - old road surface, ultra-matte. Aggregate pebbles in binder.
    Near-zero metallic, maximum roughness. Some mineral glitter in old chip."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    pebble = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 3160)
    binder = _multi_scale_noise(shape, [8, 16, 32], [0.4, 0.4, 0.2], seed + 3161)
    # Old asphalt: pebbles have slight metallic shimmer (granite chips)
    chip_glint = np.where(pebble > 0.6, (pebble - 0.6) / 0.4, 0).astype(np.float32)
    M = 8 + chip_glint * 18 + binder * 4 * sm
    R = 215 + pebble * 35 + binder * 5 * sm
    spec[:,:,0] = np.clip(M * mask + 2*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 220*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 240  # CC was 0=mirror
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_worn_asphalt(paint, shape, mask, seed, pm, bb):
    """Worn Asphalt - very dark near-black, maximum desaturation with pebble depth."""
    h, w = shape
    pebble = _multi_scale_noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 3160)
    chip_glint = np.where(pebble > 0.6, (pebble - 0.6) / 0.4, 0).astype(np.float32)
    gray = paint.mean(axis=2, keepdims=True)
    # Almost complete color kill - asphalt is near-black gray
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.15 * pm * mask[:,:,np.newaxis], 0, 1)
    # Granite chip glints are slightly warmer
    paint[:,:,0] = np.clip(paint[:,:,0] + chip_glint * 0.04 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + chip_glint * 0.04 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.15 * mask[:,:,np.newaxis], 0, 1)


# --- Premium Rough Finishes (cross-zone - genuinely new material effects) ---

def spec_chrome_oxidized(shape, mask, seed, sm):
    """Chrome Oxidized - old chrome gone dull. Starts mirror-bright, fades to chalky patches.
    Unique: per-pixel blend between chrome and rough dielectric based on oxidation noise."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    oxide = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 3170)
    fine  = _multi_scale_noise(shape, [2, 4], [0.6, 0.4], seed + 3171)
    # Blend: low oxide = chrome (M=250, G=3), high oxide = chalky dielectric (M=10, G=160)
    ox = np.clip(oxide * 0.5 + 0.5, 0, 1)
    M  = 250 * (1 - ox) + 10 * ox + fine * 10 * sm
    R  = 3   * (1 - ox) + 160 * ox + fine * 15 * sm
    CC_val = np.clip((1 - ox) * 16, 16, 255)  # CC fades with oxidation
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC_val * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_chrome_oxidized(paint, shape, mask, seed, pm, bb):
    """Chrome Oxidized - silvery chrome dulling to chalky white in oxidation patches."""
    h, w = shape
    oxide = _multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 3170)
    ox = np.clip(oxide * 0.5 + 0.5, 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    # Chrome areas: desaturate slightly + brighten
    # Oxide areas: milk/cream-white chalky overlay
    chrome_effect = (1 - ox)[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis]
    oxide_effect  = ox[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis]
    paint = paint * (1 - 0.10 * ox[:,:,np.newaxis] * pm * mask[:,:,np.newaxis]) + \
            gray   *     0.10 * ox[:,:,np.newaxis] * pm * mask[:,:,np.newaxis]
    # Bring oxidized patches toward white-chalky
    paint = np.clip(paint + oxide_effect * 0.5, 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)


def spec_carbon_raw(shape, mask, seed, sm):
    """Carbon Raw - unfinished carbon fiber, no clear coat at all.
    The weave texture reads WITHOUT the gloss - matte cross-hatch with fiber micro-sheen."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1) * h
    x = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w) * w
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.4, 0.3, 0.3], seed + 3180)
    fiber_size = max(6, min(h, w) // 30)
    # Weave: 45-degree cross-hatch
    diag1 = np.abs(np.sin((x + y) * np.pi * 2 / fiber_size + noise * 0.3)) ** 2
    diag2 = np.abs(np.sin((x - y) * np.pi * 2 / fiber_size + noise * 0.3)) ** 2
    weave = (diag1 + diag2) * 0.5
    # On the fiber strands: low roughness, moderate metallic (carbon fiber has slight sheen)
    # In the cross-gaps: higher roughness, slightly less metallic (resin between fibers)
    M = 100 + weave * 50 + noise * 12 * sm
    R = 120 + (1 - weave) * 60 + noise * 15 * sm
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 150*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 200  # CC was 0=mirror
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_carbon_raw(paint, shape, mask, seed, pm, bb):
    """Carbon Raw - very dark near-black with visible fiber strand brightness variation."""
    h, w = shape
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1) * h
    x = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w) * w
    noise = _multi_scale_noise(shape, [2, 4, 8], [0.4, 0.3, 0.3], seed + 3180)
    fiber_size = max(6, min(h, w) // 30)
    diag1 = np.abs(np.sin((x + y) * np.pi * 2 / fiber_size + noise * 0.3)) ** 2
    diag2 = np.abs(np.sin((x - y) * np.pi * 2 / fiber_size + noise * 0.3)) ** 2
    weave = (diag1 + diag2) * 0.5
    gray = paint.mean(axis=2, keepdims=True)
    # Very dark base - raw carbon is near-black
    paint = paint * (1 - 0.35 * pm * mask[:,:,np.newaxis]) + gray * 0.35 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    # Fiber strand directional sheen: very slight brighter on diagonals
    paint = np.clip(paint + weave[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.35 * mask[:,:,np.newaxis], 0, 1)


def spec_heat_blued(shape, mask, seed, sm):
    """Heat Blued Steel - tempered steel: controlled surface oxygen creates deep blue-black.
    High metallic, moderate roughness, ultra-thin CC from the oxide layer itself."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    heat_noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 3190)
    fine_noise  = _multi_scale_noise(shape, [2, 4], [0.6, 0.4], seed + 3191)
    # Heat bluing is very smooth - high M, low-moderate R
    M = 200 + heat_noise * 25 + fine_noise * 12 * sm
    R = 45  + heat_noise * 25 + fine_noise * 10 * sm
    # Slight CC from the blue oxide - varies with heat concentration
    ox_map = np.clip(heat_noise * 0.5 + 0.5, 0, 1)
    CC_val = np.clip(ox_map * 16, 16, 255)
    spec[:,:,0] = np.clip(M * mask + 5*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100*(1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC_val * mask, 16, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_heat_blued(paint, shape, mask, seed, pm, bb):
    """Heat Blued Steel - rich midnight blue-black with slight peacock iridescence."""
    h, w = shape
    heat_noise = _multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 3190)
    iridescence = _multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 3192)
    gray = paint.mean(axis=2, keepdims=True)
    # Desaturate heavily toward blue-black
    paint = paint * (1 - 0.30 * pm * mask[:,:,np.newaxis]) + gray * 0.30 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    # Rich blue depth
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.10 * pm * mask, 0, 1)
    # Peacock iridescence: slight purple-green shift in heat concentration zones
    peacock = np.clip(iridescence * 0.5 + 0.5, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + peacock * 0.04 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + (1-peacock) * 0.04 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.35 * mask[:,:,np.newaxis], 0, 1)


# Register all 12 new gap-filling finishes
EXPANSION_MONOLITHICS.update({
    # Rough Full-Metal + No-CC (3 new)
    "mill_scale":        (spec_mill_scale, paint_mill_scale),
    "grinding_marks":    (spec_grinding_marks, paint_grinding_marks),
    "raw_weld":          (spec_raw_weld, paint_raw_weld),
    # Semi-Metal Rough + No-CC (2 new)
    "bare_aluminum":     (spec_bare_aluminum, paint_bare_aluminum),
    "phosphate_coat":    (spec_phosphate_coat, paint_phosphate_coat),
    # Dielectric Rough + No-CC (2 new)
    "raw_concrete":      (spec_raw_concrete, paint_raw_concrete),
    "worn_asphalt":      (spec_worn_asphalt, paint_worn_asphalt),
    # Premium cross-zone effects (3 new)
    "chrome_oxidized":   (spec_chrome_oxidized, paint_chrome_oxidized),
    "carbon_raw":        (spec_carbon_raw, paint_carbon_raw),
    "heat_blued":        (spec_heat_blued, paint_heat_blued),
})

# Also register in the specials_groups UI metadata (appended to Texture & Surface)
# NOTE: get_specials_groups() below is patched separately - see line ~11227

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
                    print(f"[24K] WARNING: Could not resolve paint_fn '{pfn}' for base '{base_id}' - using no-op")
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
    # Strong universal fallback - visible on any base
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
    # --- Resolve deferred paint_fn references to actual engine functions ---
    # Some expansion bases need engine paint functions that aren't importable at
    # module load time. They use _resolve_paint_fn key with the engine function name.
    resolved_count = 0
    for base_id, base_entry in EXPANSION_BASES.items():
        resolve_name = base_entry.pop("_resolve_paint_fn", None)
        if resolve_name:
            engine_fn = getattr(engine_module, resolve_name, None)
            if engine_fn is not None:
                base_entry["paint_fn"] = engine_fn
                resolved_count += 1
            else:
                print(f"[24K Arsenal] WARNING: Could not resolve '{resolve_name}' for base '{base_id}'")
    if resolved_count:
        print(f"[24K Arsenal] Resolved {resolved_count} deferred paint_fn references to engine functions")

    # --- Merge into engine registries ---
    engine_module.BASE_REGISTRY.update(EXPANSION_BASES)
    engine_module.PATTERN_REGISTRY.update(EXPANSION_PATTERNS)
    engine_module.MONOLITHIC_REGISTRY.update(EXPANSION_MONOLITHICS)

    # --- Register Aurora & Chromatic Flow using already-initialized engine module ---
    # CRITICAL: Aurora paint functions live in engine/chameleon.py. That module is loaded
    # by shokker_engine_v2 as "__shokker_chameleon__" (via importlib.util) and its paint_*
    # functions are injected directly into engine_module via globals().update(_ch_fns).
    # We must NOT use "import engine.chameleon" here — that would import a DIFFERENT,
    # uninitialized module instance where _engine=None, causing AttributeError at render time.
    # Instead, look up the functions directly from engine_module (already injected).
    _aurora_id_map = [
        ("aurora_borealis",       "paint_aurora_borealis"),
        ("aurora_solar_wind",     "paint_aurora_solar_wind"),
        ("aurora_nebula",         "paint_aurora_nebula"),
        ("aurora_chromatic_surge","paint_aurora_chromatic_surge"),
        ("aurora_frozen_flame",   "paint_aurora_frozen_flame"),
        ("aurora_deep_ocean",     "paint_aurora_deep_ocean"),
        ("aurora_volcanic",       "paint_aurora_volcanic"),
        ("aurora_ethereal",       "paint_aurora_ethereal"),
        ("aurora_toxic_current",  "paint_aurora_toxic_current"),
        ("aurora_midnight_silk",  "paint_aurora_midnight_silk"),
    ]
    _aurora_registered = 0
    for _aid, _afn in _aurora_id_map:
        _paint_fn = getattr(engine_module, _afn, None)
        if _paint_fn is not None:
            engine_module.MONOLITHIC_REGISTRY[_aid] = (_spec_chameleon_24k, _paint_fn)
            _aurora_registered += 1
        else:
            print(f"[24K Arsenal] WARNING: Aurora paint fn '{_afn}' not found in engine — "
                  f"chameleon module may not be loaded. '{_aid}' will have no color.")
    if _aurora_registered:
        print(f"[24K Arsenal] Registered {_aurora_registered}/10 Aurora & Chromatic Flow finishes")

    # --- Register Chromatic Flake monolithic finishes ---
    # Factory-generated multi-color micro-flake effects. Each palette has 4-5 colors
    # distributed via multi-scale noise creating subtle color shifting across the canvas.
    # Uses local _multi_scale_noise (already defined in this module) — NOT engine.chameleon.

    def _chromatic_flake_paint(paint, shape, mask, seed, pm, bb,
                               colors, flake_scale=3, cluster_scale=30, flow_scale=200):
        """Chromatic Flake paint — replace color with multi-color micro-flake pattern."""
        if pm < 0.01:
            return paint
        h, w = shape[:2] if len(shape) > 2 else shape
        rng = np.random.RandomState(seed)

        # Fine flakes — per-pixel random assignment weighted by cluster noise
        fine_noise = rng.rand(h, w).astype(np.float32)

        # Medium clusters — which color dominates in each region
        cluster = _multi_scale_noise((h, w), [cluster_scale, cluster_scale * 2],
                                     [0.7, 0.3], seed + 100)

        # Large flow — overall color gradient across the car
        flow = _multi_scale_noise((h, w), [flow_scale, int(flow_scale * 1.5)],
                                  [0.8, 0.2], seed + 200)

        # Combine: flow for primary tendency, cluster for variation, fine for flakes
        combined = flow * 0.5 + cluster * 0.3 + fine_noise * 0.2

        # Quantize into color bins
        n_colors = len(colors)
        color_idx = np.clip((combined * n_colors).astype(np.int32), 0, n_colors - 1)

        # Build recolored paint (colors are 0-255 int, paint is 0-1 float)
        result = paint.copy()
        for i, (r, g, b) in enumerate(colors):
            cmask = (color_idx == i)
            result[cmask, 0] = r / 255.0
            result[cmask, 1] = g / 255.0
            result[cmask, 2] = b / 255.0

        # Blend with original paint using pm, respect zone mask
        out = paint.copy()
        m3 = mask[:, :, np.newaxis] if mask.ndim == 2 else mask
        blended = paint[:, :, :3] * (1.0 - pm) + result[:, :, :3] * pm
        out[:, :, :3] = blended * m3 + paint[:, :, :3] * (1.0 - m3)
        # Apply brightness boost
        out = np.clip(out + bb * 0.4 * m3, 0, 1)
        return out

    def _chromatic_flake_spec(shape, mask, seed, sm,
                              colors, spec_profiles,
                              flake_scale=3, cluster_scale=30, flow_scale=200):
        """Chromatic Flake spec — per-color M/R/CC values aligned with paint noise."""
        h, w = shape[:2] if len(shape) > 2 else shape
        rng = np.random.RandomState(seed)

        # Reproduce the same noise fields as paint to keep colors aligned
        fine_noise = rng.rand(h, w).astype(np.float32)
        cluster = _multi_scale_noise((h, w), [cluster_scale, cluster_scale * 2],
                                     [0.7, 0.3], seed + 100)
        flow = _multi_scale_noise((h, w), [flow_scale, int(flow_scale * 1.5)],
                                  [0.8, 0.2], seed + 200)
        combined = flow * 0.5 + cluster * 0.3 + fine_noise * 0.2
        n_colors = len(colors)
        color_idx = np.clip((combined * n_colors).astype(np.int32), 0, n_colors - 1)

        # Build spec arrays
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        # Add per-pixel noise for sparkle variation
        sparkle = _multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 300)

        for i, (base_M, base_R, base_CC) in enumerate(spec_profiles):
            cmask = (color_idx == i)
            spec[cmask, 0] = np.clip(base_M + sparkle[cmask] * 15 * sm, 0, 255).astype(np.uint8)
            spec[cmask, 1] = np.clip(base_R + sparkle[cmask] * 10 * sm, 0, 255).astype(np.uint8)
            spec[cmask, 2] = np.clip(base_CC, 16, 255).astype(np.uint8)

        # Alpha channel from mask
        spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
        return spec

    # 30 Chromatic Flake palette presets
    # Each: (id, display_name, desc, swatch, colors_rgb_list, spec_profiles_list)
    #   colors: list of (R, G, B) 0-255
    #   spec_profiles: list of (M, R, CC) per color
    _CF_PRESETS = [
        ("cf_midnight_galaxy", "Midnight Galaxy",
         "Deep navy, electric purple, teal, silver, dark magenta micro-flake shimmer",
         "#1a1a44",
         [(20, 20, 60), (100, 30, 180), (30, 140, 140), (180, 180, 195), (120, 20, 90)],
         [(160, 15, 18), (140, 20, 20), (150, 12, 18), (200, 8, 16), (130, 22, 20)]),

        ("cf_volcanic_ember", "Volcanic Ember",
         "Deep red, burnt orange, gold, charcoal, crimson multi-flake fire shimmer",
         "#8b2500",
         [(140, 20, 10), (180, 90, 20), (210, 180, 50), (50, 45, 40), (170, 20, 30)],
         [(120, 30, 22), (130, 25, 20), (170, 15, 18), (60, 50, 30), (110, 35, 22)]),

        ("cf_arctic_aurora", "Arctic Aurora",
         "Ice blue, mint green, lavender, white, pale cyan crystalline flake",
         "#c8e8ff",
         [(180, 210, 240), (160, 230, 190), (190, 170, 220), (240, 240, 245), (180, 230, 235)],
         [(180, 10, 16), (160, 12, 16), (170, 14, 18), (210, 6, 16), (175, 10, 16)]),

        ("cf_black_opal", "Black Opal",
         "Black, deep green, deep blue, purple flash, copper — precious stone flake",
         "#0a0a12",
         [(15, 15, 18), (10, 60, 30), (15, 20, 70), (80, 20, 100), (160, 100, 50)],
         [(200, 8, 16), (180, 12, 18), (190, 10, 16), (160, 18, 20), (170, 15, 18)]),

        ("cf_dragon_scale", "Dragon Scale",
         "Emerald, gold, dark red, bronze, olive — ancient reptilian flake",
         "#2a6030",
         [(20, 120, 40), (200, 180, 50), (120, 20, 15), (160, 120, 60), (90, 100, 40)],
         [(150, 18, 20), (180, 12, 18), (110, 30, 24), (160, 15, 18), (120, 25, 22)]),

        ("cf_toxic_nebula", "Toxic Nebula",
         "Neon green, black, electric purple, acid yellow, dark teal biohazard flake",
         "#22cc44",
         [(50, 240, 60), (15, 15, 15), (130, 30, 200), (220, 230, 30), (20, 80, 70)],
         [(140, 20, 20), (40, 50, 30), (130, 22, 20), (160, 15, 18), (100, 30, 24)]),

        ("cf_rose_gold_dust", "Rose Gold Dust",
         "Rose pink, gold, copper, cream, blush — luxury micro-flake dust",
         "#e8a0a0",
         [(210, 150, 150), (210, 185, 80), (190, 120, 70), (240, 230, 210), (220, 175, 165)],
         [(180, 10, 16), (190, 8, 16), (170, 12, 18), (160, 14, 16), (175, 10, 16)]),

        ("cf_deep_space", "Deep Space",
         "Black, deep blue, purple, silver sparkle, dark teal — cosmic void flake",
         "#0a0a1a",
         [(10, 10, 15), (15, 20, 60), (50, 15, 70), (170, 175, 185), (15, 50, 55)],
         [(180, 10, 16), (170, 12, 18), (150, 16, 20), (210, 6, 16), (140, 18, 20)]),

        ("cf_phoenix_feather", "Phoenix Feather",
         "Orange, red, gold, amber, dark scarlet — burning plumage flake",
         "#ee6622",
         [(230, 120, 20), (200, 30, 20), (220, 190, 50), (210, 160, 40), (130, 15, 15)],
         [(150, 18, 20), (120, 28, 24), (180, 10, 16), (160, 14, 18), (100, 35, 26)]),

        ("cf_frozen_mercury", "Frozen Mercury",
         "Silver, ice blue, platinum, pearl white, steel grey — liquid metal flake",
         "#c8ccd0",
         [(190, 195, 200), (180, 210, 230), (210, 210, 215), (235, 235, 238), (140, 145, 155)],
         [(220, 5, 16), (200, 8, 16), (230, 4, 16), (210, 6, 16), (190, 10, 16)]),

        ("cf_jungle_venom", "Jungle Venom",
         "Dark green, lime, black, gold, toxic yellow — serpent scale flake",
         "#1a4020",
         [(20, 60, 15), (120, 210, 40), (12, 12, 12), (190, 170, 40), (200, 210, 30)],
         [(130, 22, 22), (150, 15, 18), (50, 45, 28), (170, 12, 18), (155, 14, 18)]),

        ("cf_cobalt_storm", "Cobalt Storm",
         "Deep blue, electric blue, slate, silver, navy — thunderstorm flake",
         "#1a2266",
         [(20, 25, 90), (40, 100, 220), (100, 105, 115), (180, 185, 195), (15, 18, 55)],
         [(170, 12, 18), (160, 15, 18), (140, 20, 22), (200, 8, 16), (150, 16, 20)]),

        ("cf_sunset_strip", "Sunset Strip",
         "Coral, magenta, gold, peach, deep orange — Hollywood boulevard flake",
         "#ee6655",
         [(230, 110, 90), (200, 50, 120), (220, 190, 60), (240, 190, 160), (210, 100, 30)],
         [(160, 14, 18), (140, 20, 20), (180, 10, 16), (170, 12, 16), (150, 16, 18)]),

        ("cf_absinthe_dreams", "Absinthe Dreams",
         "Chartreuse, dark green, gold, emerald, black — green fairy flake",
         "#88aa20",
         [(160, 200, 20), (20, 60, 20), (200, 180, 50), (30, 140, 60), (15, 15, 10)],
         [(150, 15, 18), (110, 28, 24), (175, 10, 16), (140, 18, 20), (50, 45, 28)]),

        ("cf_titanium_rain", "Titanium Rain",
         "Gunmetal, silver, dark grey, blue-grey, platinum — industrial metal flake",
         "#707880",
         [(90, 95, 100), (180, 185, 190), (60, 62, 65), (100, 110, 125), (210, 212, 218)],
         [(200, 8, 16), (215, 6, 16), (160, 18, 20), (180, 12, 18), (225, 4, 16)]),

        ("cf_blood_moon", "Blood Moon",
         "Dark crimson, orange, black, deep red, rust — lunar eclipse flake",
         "#550808",
         [(100, 10, 10), (190, 100, 20), (12, 10, 10), (130, 15, 12), (150, 70, 30)],
         [(110, 30, 24), (150, 18, 20), (40, 50, 30), (100, 35, 26), (130, 22, 22)]),

        ("cf_peacock_strut", "Peacock Strut",
         "Teal, royal blue, emerald, gold, deep purple — iridescent feather flake",
         "#1a8888",
         [(30, 140, 140), (40, 50, 170), (30, 150, 60), (200, 180, 50), (60, 20, 110)],
         [(170, 12, 18), (160, 14, 18), (150, 16, 20), (185, 10, 16), (140, 20, 20)]),

        ("cf_champagne_frost", "Champagne Frost",
         "Pale gold, cream, silver, champagne, pearl — elegant celebration flake",
         "#e8dcc0",
         [(220, 200, 150), (240, 235, 220), (195, 200, 205), (215, 195, 145), (230, 228, 225)],
         [(195, 8, 16), (180, 10, 16), (210, 6, 16), (190, 8, 16), (200, 7, 16)]),

        ("cf_neon_viper", "Neon Viper",
         "Hot pink, electric blue, neon green, black, purple — aggressive neon flake",
         "#ee22aa",
         [(240, 40, 160), (30, 100, 230), (50, 240, 60), (15, 12, 18), (140, 30, 190)],
         [(150, 16, 18), (160, 14, 18), (145, 18, 20), (40, 48, 28), (135, 20, 20)]),

        ("cf_obsidian_fire", "Obsidian Fire",
         "Black, dark red, orange glow, charcoal, ember — volcanic glass flake",
         "#1a0808",
         [(12, 10, 10), (100, 15, 10), (210, 120, 20), (45, 42, 40), (180, 60, 15)],
         [(180, 10, 16), (110, 30, 24), (160, 15, 18), (80, 35, 26), (140, 20, 20)]),

        ("cf_mermaid_scale", "Mermaid Scale",
         "Aqua, purple, teal, silver, seafoam — underwater shimmer flake",
         "#44ccbb",
         [(80, 210, 210), (130, 60, 170), (40, 150, 140), (190, 195, 200), (140, 220, 200)],
         [(170, 12, 18), (145, 18, 20), (155, 15, 18), (205, 7, 16), (165, 12, 18)]),

        ("cf_carbon_prizm", "Carbon Prizm",
         "Charcoal base with subtle rainbow color-shift micro-flake",
         "#333340",
         [(55, 52, 58), (60, 50, 50), (50, 55, 60), (58, 50, 55), (52, 58, 52)],
         [(160, 18, 20), (155, 20, 22), (165, 16, 20), (150, 22, 22), (158, 19, 20)]),

        ("cf_molten_copper", "Molten Copper",
         "Copper, bronze, gold, burnt orange, dark brown — liquid forge flake",
         "#cc7744",
         [(190, 110, 50), (160, 120, 60), (210, 180, 50), (180, 90, 20), (70, 40, 20)],
         [(175, 12, 18), (165, 14, 18), (185, 10, 16), (155, 18, 20), (100, 30, 24)]),

        ("cf_electric_storm", "Electric Storm",
         "Purple, electric blue, white flash, dark grey, violet — lightning flake",
         "#6644cc",
         [(100, 40, 180), (40, 100, 230), (230, 235, 240), (55, 55, 60), (130, 60, 170)],
         [(150, 16, 18), (165, 12, 18), (220, 5, 16), (100, 28, 24), (140, 18, 20)]),

        ("cf_desert_mirage", "Desert Mirage",
         "Sand gold, terracotta, dusty rose, sage, camel — arid shimmer flake",
         "#ccaa77",
         [(200, 175, 110), (180, 100, 70), (190, 150, 140), (140, 160, 120), (195, 170, 130)],
         [(150, 18, 20), (130, 24, 24), (155, 16, 18), (135, 22, 22), (148, 18, 20)]),

        ("cf_venom_strike", "Venom Strike",
         "Acid green, black, neon yellow, dark emerald, lime — toxic attack flake",
         "#44ee22",
         [(80, 220, 30), (10, 12, 8), (210, 230, 20), (15, 70, 25), (140, 220, 50)],
         [(145, 18, 20), (40, 48, 28), (160, 14, 18), (110, 28, 24), (150, 16, 18)]),

        ("cf_sapphire_ice", "Sapphire Ice",
         "Deep sapphire, ice blue, white, crystal blue, navy — frozen gem flake",
         "#2244aa",
         [(25, 40, 140), (180, 215, 240), (235, 238, 242), (80, 150, 210), (15, 20, 65)],
         [(180, 10, 16), (195, 8, 16), (215, 5, 16), (175, 12, 18), (160, 15, 18)]),

        ("cf_inferno_chrome", "Inferno Chrome",
         "Chrome silver, fire red, orange, gold, dark steel — blazing metal flake",
         "#cc4422",
         [(195, 200, 205), (200, 35, 15), (225, 130, 20), (215, 185, 50), (80, 82, 88)],
         [(225, 5, 16), (120, 28, 24), (155, 16, 18), (180, 10, 16), (180, 12, 18)]),

        ("cf_phantom_violet", "Phantom Violet",
         "Deep violet, silver, black, lavender, dark purple — spectral flake",
         "#3a1870",
         [(60, 20, 100), (185, 188, 195), (12, 10, 15), (170, 150, 200), (45, 15, 75)],
         [(150, 16, 18), (210, 6, 16), (50, 45, 28), (165, 12, 18), (130, 22, 22)]),

        ("cf_solar_flare", "Solar Flare",
         "Bright gold, white-hot, amber, orange, deep yellow — stellar eruption flake",
         "#eeaa22",
         [(230, 200, 40), (245, 240, 220), (210, 160, 40), (230, 140, 25), (220, 200, 30)],
         [(190, 8, 16), (225, 4, 16), (175, 12, 18), (165, 14, 18), (185, 10, 16)]),
    ]

    # Factory: generate paint_fn and spec_fn closures for each preset
    _cf_registered = 0
    for _cf_id, _cf_name, _cf_desc, _cf_swatch, _cf_colors, _cf_specs in _CF_PRESETS:
        # Capture loop variables in default args
        def _make_cf_paint(colors=_cf_colors):
            def _paint(paint, shape, mask, seed, pm, bb):
                return _chromatic_flake_paint(paint, shape, mask, seed, pm, bb, colors)
            _paint.__name__ = f"paint_{_cf_id}"
            return _paint

        def _make_cf_spec(colors=_cf_colors, spec_profiles=_cf_specs):
            def _spec(shape, mask, seed, sm):
                return _chromatic_flake_spec(shape, mask, seed, sm, colors, spec_profiles)
            _spec.__name__ = f"spec_{_cf_id}"
            return _spec

        _pf = _make_cf_paint()
        _sf = _make_cf_spec()
        engine_module.MONOLITHIC_REGISTRY[_cf_id] = (_sf, _pf)
        _cf_registered += 1

    if _cf_registered:
        print(f"[24K Arsenal] Registered {_cf_registered}/30 Chromatic Flake finishes")

    # --- Sort registries alphabetically after merge ---
    for reg_name in ('BASE_REGISTRY', 'PATTERN_REGISTRY', 'MONOLITHIC_REGISTRY'):
        reg = getattr(engine_module, reg_name, None)
        if reg is not None:
            sorted_reg = dict(sorted(reg.items()))
            reg.clear()
            reg.update(sorted_reg)

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
        "Racing Heritage":      ["race_day_gloss", "stock_car_enamel", "bullseye_chrome",
                                 "endurance_ceramic", "rally_mud", "drag_strip_gloss", "victory_lane",
                                 "barn_find", "pace_car_pearl",
                                 "asphalt_grind", "checkered_chrome"],
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
        "Raw Industrial":       ["mill_scale", "grinding_marks", "raw_weld",
                                 "bare_aluminum", "phosphate_coat",
                                 "raw_concrete", "worn_asphalt",
                                 "chrome_oxidized", "carbon_raw", "heat_blued"],
        "Vintage & Retro":      ["barn_find", "patina_truck", "hot_rod_flames", "woodie_wagon",
                                 "drive_in", "muscle_car_stripe", "pin_up", "vinyl_record"],
        "Surreal & Fantasy":    ["portal", "time_warp", "antimatter", "singularity", "dreamscape",
                                 "acid_trip", "mirage", "fourth_dimension", "glitch_reality", "phantom_zone"],
    }

    return {"bases": bases_groups, "patterns": patterns_groups, "specials": specials_groups}


# ============================================================
# Aurora & Chromatic Flow — registered inside integrate_expansion()
# ============================================================
# NOTE: Aurora paint functions are NOT registered here at module scope.
# They are registered inside integrate_expansion() where we have a reference
# to the already-initialized engine_module, so we can look up the paint
# functions that were injected by integrate_chameleon (via globals().update).
#
# DO NOT use "import engine.chameleon" here — it produces a separate,
# uninitialized module instance (_engine=None) and breaks rendering.
#
# The aurora ID → paint function name map is defined in integrate_expansion().


def get_expansion_counts():
    """Quick count check for validation."""
    return {
        "bases": len(EXPANSION_BASES),
        "patterns": len(EXPANSION_PATTERNS),
        "specials": len(EXPANSION_MONOLITHICS),
        "total": len(EXPANSION_BASES) + len(EXPANSION_PATTERNS) + len(EXPANSION_MONOLITHICS),
    }
