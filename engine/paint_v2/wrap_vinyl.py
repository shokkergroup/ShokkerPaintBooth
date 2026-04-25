"""
Vinyl wrap paint functions for Shokker Paint Booth V5.
Implements 8 vinyl wrap bases with unique mathematical techniques.
"""

import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


# =============================================================================
# CHROME WRAP - Conformable chrome vinyl with stretch distortion
# =============================================================================

def paint_chrome_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Chrome wrap with elastic stretch distortion using advection-like flow.
    Creates directional chrome sheen with constraint-based warping.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Laminar flow field — subtle stretch only (smoother chrome wrap base)
    y, x = get_mgrid((h, w))
    flow_base = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 2500)
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
    return np.clip(result + bb[:,:,np.newaxis] * 0.45 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_chrome_wrap(shape, seed, sm, base_m, base_r):
    """
    Chrome wrap specular: high mirror with directional anisotropy.
    Chrome film IS metallic — M near 255, R near 0.
    """
    h, w = shape
    
    direction = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 2500)
    metallic = 0.85 + 0.15 * multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 2503)
    roughness = 0.02 + 0.02 * multi_scale_noise((h, w), [1, 3], [0.6, 0.4], seed + 2504)
    # CC 16 = full clearcoat; mirror chrome vinyl = full gloss
    cc = np.full((h, w), 16.0, dtype=np.float32)
    
    # metallic is ALREADY 0.85-1.0 (i.e. 0-1 range) — scale to 0-255
    M_arr = np.clip(metallic * 255.0, 0, 255).astype(np.float32)
    R_arr = np.clip(roughness * 255.0, 0, 255).astype(np.float32)
    # Per-pixel GGX floor: R>=15 only where M<240
    R_arr = np.where(M_arr < 240, np.maximum(R_arr, 15), R_arr)
    return M_arr, R_arr, cc


# =============================================================================
# COLOR FLIP WRAP - Dichroic color-shift vinyl (angle-dependent)
# =============================================================================

def paint_color_flip_v2(paint, shape, mask, seed, pm, bb):
    """
    Chromatic flip-wrap: colors wrap/invert at extreme viewing angles.
    Like a chrome that flips between two color states with dramatic wrap transition.
    Dichroic-style — not just rainbow iridescence, but a FLIP between two distinct colors.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape

    y, x = get_mgrid((h, w))

    # Noise-based viewing angle simulation (simulates body curvature)
    angle_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 2505)
    fine_noise = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 2506)

    # Viewing angle parameter: combines position + body noise
    y_norm = y / max(h - 1, 1)
    x_norm = x / max(w - 1, 1)
    # Angle parameter driven by surface curvature simulation
    angle_param = np.clip(
        y_norm * 0.3 + x_norm * 0.25 + angle_noise * 0.3 + fine_noise * 0.15,
        0, 1
    )

    # Two-state chromatic flip: State A and State B
    rng = np.random.RandomState(seed + 2507)
    # Generate two complementary premium colors
    hue_a = rng.uniform(0, 1)
    hue_b = (hue_a + 0.45 + rng.uniform(-0.1, 0.1)) % 1.0  # near-complementary
    # Convert hues to saturated RGB
    def hue2rgb(h_val):
        r = np.abs(h_val * 6 - 3) - 1
        g = 2 - np.abs(h_val * 6 - 2)
        b = 2 - np.abs(h_val * 6 - 4)
        return np.clip(r, 0, 1) * 0.85 + 0.1, np.clip(g, 0, 1) * 0.8 + 0.1, np.clip(b, 0, 1) * 0.85 + 0.1

    ar, ag, ab = hue2rgb(hue_a)
    br, bg, bb_c = hue2rgb(hue_b)

    # Sharp-ish flip transition (steeper sigmoid, not linear)
    flip = 1.0 / (1.0 + np.exp(-(angle_param - 0.5) * 12.0))  # steep sigmoid
    # Chrome-like metallic shimmer at transition zone
    transition_zone = np.clip(1.0 - np.abs(angle_param - 0.5) * 4.0, 0, 1)
    chrome_shimmer = transition_zone * 0.15

    r_ch = ar * (1.0 - flip) + br * flip + chrome_shimmer
    g_ch = ag * (1.0 - flip) + bg * flip + chrome_shimmer * 0.8
    b_ch = ab * (1.0 - flip) + bb_c * flip + chrome_shimmer * 0.6

    flip_effect = np.stack([
        np.clip(r_ch, 0, 1),
        np.clip(g_ch, 0, 1),
        np.clip(b_ch, 0, 1)
    ], axis=-1).astype(np.float32)

    blend = pm * 0.82
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) +
                     flip_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_color_flip(shape, seed, sm, base_m, base_r):
    """
    Color flip spec: high metallic chrome-like base with angle-dependent
    roughness variation for dichroic effect. Very glossy.
    """
    h, w = shape

    # Angle simulation noise
    angle_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 2505)
    fine = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 2507)
    y, x = get_mgrid((h, w))
    angle_param = np.clip(y / max(h - 1, 1) * 0.3 + x / max(w - 1, 1) * 0.25 + angle_noise * 0.3, 0, 1)

    # Transition zone gets different spec
    transition = np.clip(1.0 - np.abs(angle_param - 0.5) * 4.0, 0, 1)

    # M: high metallic throughout (chrome-like), highest at transition
    M = np.clip(180.0 + transition * 60.0 * sm + fine * 15.0 * sm, 0, 255).astype(np.float32)
    # R: very low (glossy), slightly higher at transitions for diffuse color shift
    R = np.clip(4.0 + transition * 8.0 * sm + fine * 3.0 * sm, 15, 255).astype(np.float32)  # GGX floor
    # CC: max clearcoat glossy film
    CC = np.clip(16.0 + (1.0 - transition) * 5.0 * sm, 16, 255).astype(np.float32)

    return M, R, CC


# =============================================================================
# GLOSS WRAP - High-gloss calendered vinyl with lamination sheen
# =============================================================================

def paint_gloss_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Gloss wrap using Fresnel-like edge brightening with calendering waves.
    Creates mirror-like finish with soft radial falloff.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    
    gloss_noise = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 2509)
    gloss_effect = (0.88 + 0.1 * gloss_noise) * (fresnel_pow + calendar * 0.06)
    gloss_effect = np.stack([gloss_effect, gloss_effect, gloss_effect], axis=-1)
    
    blend = pm * np.clip(fresnel_pow + 0.2, 0, 1)[:,:,np.newaxis]
    result = np.clip(paint * (1.0 - mask[:,:,np.newaxis] * blend) +
                     gloss_effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_gloss_wrap(shape, seed, sm, base_m, base_r):
    """
    Gloss wrap specular: dielectric vinyl, zero metallic, low roughness.
    The vinyl film itself acts as the clearcoat layer.
    """
    h, w = shape
    
    peel = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 2511)
    metallic = np.clip(3.0 + peel * 5.0 * sm, 0, 255).astype(np.float32)
    roughness = np.clip(6.0 + peel * 6.0 * sm, 15, 255).astype(np.float32)  # GGX floor
    cc = np.clip(16.0 + peel * 4.0, 16, 255).astype(np.float32)
    
    return (metallic, roughness, cc)


# =============================================================================
# LIQUID WRAP - Liquid metal peelable coating
# =============================================================================

def paint_liquid_wrap_v2(paint, shape, mask, seed, pm, bb):
    """Liquid rubber/vinyl peel coat: WEAK-016 FIX — stretchy rubber/vinyl character.
    Distinct from satin_wrap: fine Perlin micro-texture + slight darkening at stretch points.
    Previously simulated liquid-metal pooling — wrong material character for rubber peel coat."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    # Fine rubber compound particle variation texture
    rubber_grain = multi_scale_noise((h, w), [16, 32, 64], [0.45, 0.35, 0.2], seed + 2512)
    # Stretch point simulation: gradient noise for high-curvature area darkening
    stretch_pts  = multi_scale_noise((h, w), [1, 2, 3], [0.5, 0.3, 0.2], seed + 2513)
    # Slight darkening at stretch peaks (0-5% darker where rubber stretches)
    stretch_darken = 1.0 - np.clip((stretch_pts - 0.7) / 0.3, 0, 1) * 0.05 * pm
    # ~10% desaturation: rubber coat slightly mutes the underlying color
    gray = paint.mean(axis=2, keepdims=True)
    desaturated = paint * 0.90 + gray * 0.10
    # Fine rubber grain: subtle brightness variation from compound particles
    grain_effect = 1.0 + (rubber_grain - 0.5) * 0.03 * pm
    result = np.clip(desaturated * stretch_darken[:,:,np.newaxis] * grain_effect[:,:,np.newaxis], 0, 1)
    blend = pm * mask[:,:,np.newaxis]
    out = np.clip(paint * (1.0 - blend) + result * blend, 0, 1)
    return np.clip(out + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_liquid_wrap(shape, seed, sm, base_m, base_r):
    """Liquid rubber peel coat spec: WEAK-016 FIX — rubber/vinyl character distinct from satin_wrap.
    G: 60-100 (slightly rougher than satin), no metallic (R near 0), fine Perlin texture.
    Previously: R=22-37 (too smooth), CC=50-58 — nearly identical range to satin_wrap."""
    h, w = shape
    # Fine Perlin texture for rubber compound surface variation
    rubber_tex = multi_scale_noise((h, w), [16, 32, 64], [0.45, 0.35, 0.2], seed + 2516)
    # M: near zero — rubber/vinyl is dielectric, no metallic character
    metallic  = np.clip(0.0 + rubber_tex * 3.0 * sm, 0, 255).astype(np.float32)
    # R: 60-100 range — slightly rougher than satin (satin ~35-55), rubber is not as smooth
    roughness = np.clip(60.0 + rubber_tex * 40.0 * sm, 15, 255).astype(np.float32)  # R≥15
    # CC: same satin-ish range (40-58) — rubber self-seals like vinyl
    cc        = np.clip(40.0 + rubber_tex * 18.0, 16, 255).astype(np.float32)
    return (metallic, roughness, cc)


# =============================================================================
# MATTE WRAP - Matte finish cast vinyl with anti-glare diffusion
# =============================================================================

def paint_matte_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Matte wrap using Lambertian diffusion with micro-texture pattern.
    Creates non-directional light scatter using isotropic Perlin-like noise.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    return np.clip(result + bb[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_matte_wrap(shape, seed, sm, base_m, base_r):
    """
    Matte wrap specular: no metallic, high roughness for diffuse scattering.
    """
    h, w = shape
    
    # Matte: zero metallicity
    metallic = np.zeros((h, w), dtype=np.float32)

    # High roughness for matte diffusion
    rough_base = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 2519)
    roughness = np.clip(166.0 + rough_base * 51.0 * sm, 15, 255).astype(np.float32)

    # Dead flat = max dull clearcoat (CC 255); 0-15 invalid per spec map ref
    clearcoat = np.full((h, w), 255.0, dtype=np.float32)

    return (metallic, roughness, clearcoat)


# =============================================================================
# SATIN WRAP - Satin finish vinyl with directional micro-texture
# =============================================================================

def paint_satin_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Satin wrap using Gabor-like directional texture with soft directional highlights.
    Creates woven appearance with slight directionality.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    
    y, x = get_mgrid((h, w))
    
    # Directional texture (aligned waves)
    direction = 0.3 * np.pi + 0.2 * np.pi * multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 2520)
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
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_satin_wrap(shape, seed, sm, base_m, base_r):
    """
    Satin wrap specular: dielectric vinyl with mid-range roughness for
    satin sheen. The vinyl film is the protection layer (CC=60).
    """
    h, w = shape
    
    grain = multi_scale_noise((h, w), [1, 2, 4, 8], [0.3, 0.25, 0.25, 0.2], seed + 2524)
    metallic = np.clip(3.0 + grain * 5.0 * sm, 0, 255).astype(np.float32)
    roughness = np.clip(35.0 + grain * 20.0 * sm, 15, 255).astype(np.float32)  # GGX floor
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Multi-scale fractal for RCS reduction (absorptive random roughness)
    fractal_1 = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 2525)
    fractal_2 = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 2526)
    
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
    return np.clip(result + bb[:,:,np.newaxis] * 0.06 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_stealth_wrap(shape, seed, sm, base_m, base_r):
    """
    Stealth wrap specular: absorptive, low metallic, high roughness.
    """
    h, w = shape
    
    # Almost no metallic (absorptive)
    absorb = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 2527)
    metallic = np.clip(13.0 + absorb * 25.0 * sm, 0, 255).astype(np.float32)

    # Very high roughness for absorptive scattering
    rough_noise = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 2528)
    roughness = np.clip(191.0 + rough_noise * 51.0 * sm, 15, 255).astype(np.float32)

    # Minimal clearcoat for stealth — base_m is ALREADY 0-255, no *255 needed
    clearcoat = np.clip(120.0 + base_m * 0.1 + absorb * 15.0, 16, 255).astype(np.float32)

    return (metallic, roughness, clearcoat)


# =============================================================================
# TEXTURED WRAP - Carbon fiber textured vinyl overlay
# =============================================================================

def paint_textured_wrap_v2(paint, shape, mask, seed, pm, bb):
    """Orange-peel embossed vinyl wrap. Applies raised-dimple surface texture to the
    user's base paint color — preserves any chosen color, adds 3D emboss character
    via bump modulation (peaks lighter, valleys darker). No hardcoded color."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    # Coarse bump map: large dimples characteristic of orange-peel vinyl texture
    bump_coarse = multi_scale_noise((h, w), [8, 16], [0.55, 0.45], seed + 2529)
    # Fine surface grain: micro-texture variation on vinyl film surface
    bump_fine = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 2530)
    # Combine into orange-peel pattern (75% coarse dimples, 25% fine grain)
    texture = np.clip(0.75 * bump_coarse + 0.25 * bump_fine, 0, 1)
    # Brightness modulation: peaks +14%, valleys -14% (light on bumps, shadow in dimples)
    bump_mod = (1.0 + 0.28 * (texture - 0.5))[:, :, np.newaxis]
    textured = np.clip(paint * bump_mod, 0, 1)
    blend = pm * (0.80 + 0.20 * texture[:, :, np.newaxis])
    result = paint * (1.0 - mask[:, :, np.newaxis] * blend) + textured * (mask[:, :, np.newaxis] * blend)
    result = np.clip(result, 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_textured_wrap(shape, seed, sm, base_m, base_r):
    """
    Textured wrap specular: slight metallic with woven roughness pattern.
    """
    h, w = shape
    
    tex = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 2530)
    weave_rough = multi_scale_noise((h, w), [3, 6, 12], [0.4, 0.35, 0.25], seed + 2531)
    metallic = np.clip(38.0 + tex * 38.0 * sm, 0, 255).astype(np.float32)
    roughness = np.clip(77.0 + weave_rough * 51.0 * sm, 15, 255).astype(np.float32)
    cc = np.clip(40.0 + weave_rough * 8.0, 16, 255).astype(np.float32)

    return (metallic, roughness, cc)


# =============================================================================
# BRUSHED WRAP - Brushed metal vinyl with directional grain
# =============================================================================

def paint_brushed_wrap_v2(paint, shape, mask, seed, pm, bb):
    """
    Brushed metal vinyl: directional horizontal grain lines with
    localized brightness variation from machining-pattern print.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    return np.clip(result + bb[:,:,np.newaxis] * 0.20 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


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
    R = np.clip(18.0 + row * 25.0 * sm + depth * 10.0, 15, 255).astype(np.float32)  # GGX floor
    CC = np.clip(35.0 + depth * 6.0, 16, 255).astype(np.float32)

    return (M, R, CC)
