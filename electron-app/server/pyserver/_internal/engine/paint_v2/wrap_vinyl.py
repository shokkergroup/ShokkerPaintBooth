"""
Vinyl wrap paint functions for Shokker Paint Booth V5.
Implements 8 vinyl wrap bases with unique mathematical techniques.
"""

import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# =============================================================================
# CHROME WRAP - Conformable chrome vinyl with stretch distortion
# =============================================================================

def paint_chrome_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Chrome wrap with elastic stretch distortion using advection-like flow.
    Creates directional chrome sheen with constraint-based warping.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Laminar flow field — subtle stretch only (smoother chrome wrap base)
    y, x = get_mgrid((h, w))
    flow_base = multi_scale_noise((h, w), [4, 8, 16], [0.35, 0.35, 0.3], seed + 2500)
    flow_perp = multi_scale_noise((h, w), [6, 12, 24], [0.3, 0.4, 0.3], seed + 2501)
    
    flow_mag = np.sqrt(flow_base**2 + flow_perp**2) + 1e-6
    flow_x = flow_base / flow_mag
    flow_y = flow_perp / flow_mag
    
    # Gentle sheen variation (reduced aggression)
    sheen = 0.92 + 0.08 * (np.sin(6 * (x * flow_x + y * flow_y) / max(w, 1)) * 0.5 + 0.5)
    chrome_effect = np.stack([sheen, sheen, sheen], axis=-1) * 0.97
    
    # Lighter blend so base stays smoother
    blend = pm * 0.35 * np.clip(np.abs(flow_x), 0.2, 1.0)[:,:,np.newaxis]
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     chrome_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_chrome_wrap(shape, seed, sm, base_m, base_r):
    """
    Chrome wrap specular: high mirror with directional anisotropy.
    Chrome film IS metallic — M near 255, R near 0.
    """
    h, w = shape
    
    direction = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 2500)
    metallic = 0.85 + 0.15 * multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 2503)
    roughness = 0.02 + 0.02 * multi_scale_noise((h, w), [1, 3], [0.6, 0.4], seed + 2504)
    # CC 16 = full clearcoat; mirror chrome vinyl = full gloss
    cc = np.full((h, w), 16.0, dtype=np.float32)
    
    return (np.clip(metallic * 255.0, 0, 255).astype(np.float32),
            np.clip(roughness * 255.0, 0, 255).astype(np.float32),
            cc)


# =============================================================================
# COLOR FLIP WRAP - Dichroic color-shift vinyl (angle-dependent)
# =============================================================================

def paint_color_flip_v2(paint, shape, mask, seed, pm, bb):
    """
    Dichroic vinyl with view-angle color shift using polar coordinate mapping.
    Creates rainbow iridescence effect.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    y, x = get_mgrid((h, w))
    # Normalize to [-1, 1]
    y_norm = (y / h - 0.5) * 2
    x_norm = (x / w - 0.5) * 2
    
    # Polar angle for hue rotation
    angle = np.arctan2(y_norm, x_norm) / np.pi  # [-1, 1]
    radius = np.sqrt(y_norm**2 + x_norm**2)
    
    # Multi-layer iridescence — softer detail so base isn't too busy
    irido_base = multi_scale_noise((h, w), [4, 8, 16], [0.35, 0.35, 0.3], seed + 2505)
    irido_detail = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 2506)
    
    # Hue cycling: angle-dominated, subtle detail
    hue_offset = angle * 0.5 + irido_detail * 0.1
    
    # RGB hue rotation (simple approximation)
    r = 0.5 + 0.5 * np.sin(hue_offset * np.pi + 0)
    g = 0.5 + 0.5 * np.sin(hue_offset * np.pi + 2.09)
    b = 0.5 + 0.5 * np.sin(hue_offset * np.pi + 4.19)
    
    flip_effect = np.stack([r, g, b], axis=-1) * (0.7 + 0.3 * irido_base[:,:,np.newaxis])
    
    blend = pm * (0.6 + 0.4 * radius[:,:,np.newaxis])
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     flip_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_color_flip(shape, seed, sm, base_m, base_r):
    """
    Color flip specular: moderate metallic with multi-layer interference.
    """
    h, w = shape
    
    # Iridescent effect reduces roughness in highlights
    irido = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 2507)
    
    metallic = 0.55 + 0.35 * irido
    
    # Variable roughness for angle-dependent appearance
    roughness = 0.08 + 0.06 * multi_scale_noise((h, w), [1, 3, 6], [0.5, 0.3, 0.2], seed + 2508)
    
    # Full clearcoat for glossy color-flip film (CC 16 = max gloss)
    clearcoat = np.full((h, w), 16.0, dtype=np.float32)
    
    return (np.clip(metallic * 255.0, 0, 255).astype(np.float32), 
            np.clip(roughness * 255.0, 0, 255).astype(np.float32),
            np.clip(clearcoat, 16, 255).astype(np.float32))


# =============================================================================
# GLOSS WRAP - High-gloss calendered vinyl with lamination sheen
# =============================================================================

def paint_gloss_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Gloss wrap using Fresnel-like edge brightening with calendering waves.
    Creates mirror-like finish with soft radial falloff.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    y, x = get_mgrid((h, w))
    y_norm = (y / h - 0.5) * 2
    x_norm = (x / w - 0.5) * 2
    
    # Fresnel-like effect: brighter at edges
    fresnel = np.sqrt(y_norm**2 + x_norm**2)
    fresnel = np.clip(1.0 - fresnel, 0, 1)
    fresnel_pow = np.clip(fresnel, 0, None) ** 0.5  # Soften curve
    
    # Very subtle calendering (reduced so base isn't overly textured)
    calendar_y = 0.5 + 0.5 * np.sin(3 * np.pi * y / max(h, 1))
    calendar_x = 0.5 + 0.5 * np.sin(3 * np.pi * x / max(w, 1))
    calendar = calendar_y * calendar_x
    
    gloss_noise = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 2509)
    gloss_effect = (0.88 + 0.1 * gloss_noise) * (fresnel_pow + calendar * 0.06)
    gloss_effect = np.stack([gloss_effect, gloss_effect, gloss_effect], axis=-1)
    
    blend = pm * np.clip(fresnel_pow + 0.2, 0, 1)[:,:,np.newaxis]
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     gloss_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_gloss_wrap(shape, seed, sm, base_m, base_r):
    """
    Gloss wrap specular: dielectric vinyl, zero metallic, low roughness.
    The vinyl film itself acts as the clearcoat layer.
    """
    h, w = shape
    
    peel = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 2511)
    metallic = np.clip(3.0 + peel * 5.0 * sm, 0, 255).astype(np.float32)
    roughness = np.clip(6.0 + peel * 6.0 * sm, 0, 255).astype(np.float32)
    cc = np.clip(16.0 + peel * 4.0, 0, 255).astype(np.float32)
    
    return (metallic, roughness, cc)


# =============================================================================
# LIQUID WRAP - Liquid metal peelable coating
# =============================================================================

def paint_liquid_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Liquid metal effect using curl noise for organic flow patterns.
    Simulates mercury-like pooling and drip behavior.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Curl noise for organic liquid flow (approximated via cross-derivatives)
    base_noise = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 2512)
    deriv_noise = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 2513)
    
    # Approximation of curl: perpendicular gradient flow
    curl_x = deriv_noise
    curl_y = base_noise
    
    # Liquid pooling effect: concentration toward low areas
    pooling = np.clip(1.0 - np.abs(curl_x - curl_y), 0, 1)
    pooling = np.power(pooling, 1.5)
    
    # Metallic shimmer with liquid surface tension (sharp highlights)
    surface = 0.9 + 0.1 * multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 2514)
    liquid_effect = np.stack([surface, surface, surface], axis=-1) * (0.8 + 0.2 * pooling[:,:,np.newaxis])
    
    # Apply with pool-based blending
    blend = pm * np.clip(pooling[:,:,np.newaxis], 0.2, 1.0)
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     liquid_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_liquid_wrap(shape, seed, sm, base_m, base_r):
    """
    Liquid rubber peel coat: dielectric polymer, the rubber IS the coat.
    M near 0, moderate roughness from rubbery texture, CC from self-sealing.
    """
    h, w = shape
    
    tension = multi_scale_noise((h, w), [3, 6, 12], [0.35, 0.35, 0.3], seed + 2516)
    metallic = np.clip(2.0 + tension * 4.0 * sm, 0, 255).astype(np.float32)
    roughness = np.clip(22.0 + tension * 15.0 * sm, 0, 255).astype(np.float32)
    cc = np.clip(50.0 + tension * 8.0, 0, 255).astype(np.float32)
    
    return (metallic, roughness, cc)


# =============================================================================
# MATTE WRAP - Matte finish cast vinyl with anti-glare diffusion
# =============================================================================

def paint_matte_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Matte wrap using Lambertian diffusion with micro-texture pattern.
    Creates non-directional light scatter using isotropic Perlin-like noise.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Multi-scale diffusion pattern for anti-glare
    diffuse_base = multi_scale_noise((h, w), [1, 2, 4, 8], [0.3, 0.25, 0.25, 0.2], seed + 2517)
    diffuse_detail = multi_scale_noise((h, w), [1, 3, 6], [0.4, 0.35, 0.25], seed + 2518)
    
    # Combine diffusion patterns
    diffusion = 0.85 * diffuse_base + 0.15 * diffuse_detail
    diffusion = np.clip(diffusion, 0.7, 1.0)
    
    # Matte effect: reduce saturation and brightness uniformly
    matte_effect = paint * 0.92 * diffusion[:,:,np.newaxis]
    
    # Add micro-texture through subtle darkening
    texture_mask = 0.95 + 0.05 * (diffuse_detail - 0.5)[:,:,np.newaxis]
    matte_effect = matte_effect * texture_mask
    
    blend = pm * 0.8
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     matte_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_matte_wrap(shape, seed, sm, base_m, base_r):
    """
    Matte wrap specular: no metallic, high roughness for diffuse scattering.
    """
    h, w = shape
    
    # Matte: zero metallicity
    metallic = np.zeros((h, w), dtype=np.float32)
    
    # High roughness for matte diffusion
    rough_base = multi_scale_noise((h, w), [2, 4, 8], [0.35, 0.35, 0.3], seed + 2519)
    roughness = 0.65 + 0.2 * rough_base
    
    # Dead flat = max dull clearcoat (CC 255); 0-15 invalid per spec map ref
    clearcoat = np.full((h, w), 255.0, dtype=np.float32)
    
    return (metallic, np.clip(roughness * 255.0, 0, 255).astype(np.float32), clearcoat)


# =============================================================================
# SATIN WRAP - Satin finish vinyl with directional micro-texture
# =============================================================================

def paint_satin_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Satin wrap using Gabor-like directional texture with soft directional highlights.
    Creates woven appearance with slight directionality.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    y, x = get_mgrid((h, w))
    
    # Directional texture (aligned waves)
    direction = 0.3 * np.pi + 0.2 * np.pi * multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 2520)
    aligned = np.cos(8 * (x * np.cos(direction) + y * np.sin(direction)) / w)
    
    # Texture amplitude modulation
    texture_amp = 0.5 + 0.4 * multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 2521)
    texture = aligned * texture_amp
    
    # Satin surface: moderate brightness with subtle directional sheen
    satin_base = 0.88 + 0.1 * multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 2522)
    satin_sheen = satin_base * (1.0 + 0.15 * texture)
    satin_effect = np.stack([satin_sheen, satin_sheen, satin_sheen], axis=-1)
    
    blend = pm * (0.7 + 0.2 * texture_amp[:,:,np.newaxis])
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     satin_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_satin_wrap(shape, seed, sm, base_m, base_r):
    """
    Satin wrap specular: dielectric vinyl with mid-range roughness for
    satin sheen. The vinyl film is the protection layer (CC=60).
    """
    h, w = shape
    
    grain = multi_scale_noise((h, w), [1, 2, 4, 8], [0.3, 0.25, 0.25, 0.2], seed + 2524)
    metallic = np.clip(3.0 + grain * 5.0 * sm, 0, 255).astype(np.float32)
    roughness = np.clip(35.0 + grain * 20.0 * sm, 0, 255).astype(np.float32)
    cc = np.clip(60.0 + grain * 6.0, 16, 255).astype(np.float32)
    
    return (metallic, roughness, cc)


# =============================================================================
# STEALTH WRAP - Military-grade IR-suppressive wrap
# =============================================================================

def paint_stealth_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Stealth wrap using fractal decomposition for low-RCS appearance.
    Creates absorption pattern that minimizes reflectivity.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Multi-scale fractal for RCS reduction (absorptive random roughness)
    fractal_1 = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 2525)
    fractal_2 = multi_scale_noise((h, w), [2, 4, 8], [0.35, 0.35, 0.3], seed + 2526)
    
    # Combine fractals for self-similar absorption
    rcs_pattern = np.clip(0.6 * fractal_1 + 0.4 * fractal_2, 0, 1)
    rcs_pattern = np.power(rcs_pattern, 1.2)  # Emphasize darkening
    
    # Stealth color: absorptive dark with minimal highlights
    stealth_color = np.array([0.15, 0.15, 0.16], dtype=np.float32)  # Near-black
    stealth_effect = stealth_color * (0.8 + 0.15 * rcs_pattern[:,:,np.newaxis])
    
    # Add fractal roughness to surface
    roughness_noise = 0.3 + 0.4 * rcs_pattern
    stealth_effect = stealth_effect * (0.95 + 0.05 * roughness_noise[:,:,np.newaxis])
    
    blend = pm * (0.9 + 0.1 * rcs_pattern[:,:,np.newaxis])
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     stealth_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_stealth_wrap(shape, seed, sm, base_m, base_r):
    """
    Stealth wrap specular: absorptive, low metallic, high roughness.
    """
    h, w = shape
    
    # Almost no metallic (absorptive)
    metallic = 0.05 + 0.1 * multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 2527)
    
    # Very high roughness for absorptive scattering
    rough_noise = multi_scale_noise((h, w), [2, 4, 8], [0.35, 0.35, 0.3], seed + 2528)
    roughness = 0.75 + 0.2 * rough_noise
    
    # Minimal clearcoat for stealth
    clearcoat = np.full((h, w), np.clip(0.1 + 0.05 * base_m, 0, 1), dtype=np.float32)
    
    return (np.clip(metallic * 255.0, 0, 255).astype(np.float32),
            np.clip(roughness * 255.0, 0, 255).astype(np.float32),
            np.clip(clearcoat * 255.0, 16, 255).astype(np.float32))


# =============================================================================
# TEXTURED WRAP - Carbon fiber textured vinyl overlay
# =============================================================================

def paint_textured_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Carbon fiber texture using wave interference for weave pattern.
    Creates realistic woven overlay with alternating fiber direction.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    
    y, x = get_mgrid((h, w))
    
    # Two-directional wave pattern for weave
    weave_1 = np.sin(12 * np.pi * x / w) * np.sin(12 * np.pi * y / h)
    weave_2 = np.sin(12 * np.pi * x / w + np.pi/4) * np.cos(12 * np.pi * y / h + np.pi/4)
    
    # Combine weaves with phase offset
    weave = 0.6 * weave_1 + 0.4 * weave_2
    weave = (weave + 1.0) / 2.0  # Normalize to [0, 1]
    
    # Add stochastic fiber variations
    fiber_noise = multi_scale_noise((h, w), [1, 2, 4, 8], [0.3, 0.25, 0.25, 0.2], seed + 2529)
    texture_pattern = 0.7 * weave + 0.3 * fiber_noise
    
    # Carbon fiber color (dark gray with slight sheen)
    carbon_base = np.array([0.25, 0.25, 0.26])
    carbon_sheen = carbon_base + 0.1 * texture_pattern[:,:,np.newaxis]
    carbon_effect = np.stack([carbon_sheen[:,:,0], carbon_sheen[:,:,1], carbon_sheen[:,:,2]], axis=-1)
    
    # Texture depth variation
    depth = 0.9 + 0.08 * (texture_pattern - 0.5)[:,:,np.newaxis]
    carbon_effect = carbon_effect * depth
    
    blend = pm * (0.85 + 0.15 * texture_pattern[:,:,np.newaxis])
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     carbon_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_textured_wrap(shape, seed, sm, base_m, base_r):
    """
    Textured wrap specular: slight metallic with woven roughness pattern.
    """
    h, w = shape
    
    metallic = 0.15 + 0.15 * multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 2530)
    weave_rough = multi_scale_noise((h, w), [3, 6, 12], [0.4, 0.35, 0.25], seed + 2531)
    roughness = 0.3 + 0.2 * weave_rough
    cc = np.clip(40.0 + weave_rough * 8.0, 16, 255)
    
    return (np.clip(metallic * 255.0, 0, 255).astype(np.float32),
            np.clip(roughness * 255.0, 0, 255).astype(np.float32),
            cc.astype(np.float32))


# =============================================================================
# BRUSHED WRAP - Brushed metal vinyl with directional grain
# =============================================================================

def paint_brushed_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Brushed metal vinyl: directional horizontal grain lines with
    localized brightness variation from machining-pattern print.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 2540)

    row_grain = rng.randn(h, 1).astype(np.float32) * 0.6
    row_grain = np.tile(row_grain, (1, w))
    cross_grain = rng.randn(h, w).astype(np.float32) * 0.06
    grain = row_grain + cross_grain

    depth_field = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 2541)
    brightness_mod = 0.90 + depth_field * 0.10

    gray = base.mean(axis=2, keepdims=True)
    metallic_base = np.clip(gray * 0.3 + 0.50, 0, 1)
    grain_light = np.clip(grain, 0, 1)[:, :, np.newaxis]
    grain_dark = np.clip(-grain, 0, 1)[:, :, np.newaxis]
    effect = np.clip(metallic_base * brightness_mod[:, :, np.newaxis]
                     + grain_light * 0.06 * pm
                     - grain_dark * 0.04 * pm, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return result.astype(np.float32)


def spec_brushed_wrap(shape, seed, sm, base_m, base_r):
    """
    Brushed wrap spec: moderate metallic from printed metal look,
    anisotropic roughness from grain direction, vinyl CC.
    """
    h, w = shape
    rng = np.random.RandomState(seed + 2540)
    row = np.abs(rng.randn(h, 1).astype(np.float32))
    row = np.tile(row, (1, w))
    row = np.clip(row / (row.max() + 1e-8), 0, 1)

    depth = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 2541)

    M = np.clip(120.0 + row * 40.0 * sm + depth * 20.0, 0, 255).astype(np.float32)
    R = np.clip(18.0 + row * 25.0 * sm + depth * 10.0, 0, 255).astype(np.float32)
    CC = np.clip(35.0 + depth * 6.0, 16, 255).astype(np.float32)
    
    return (M, R, CC)
