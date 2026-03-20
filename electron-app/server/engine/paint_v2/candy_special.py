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
from engine.core import multi_scale_noise, get_mgrid


def paint_candy_v2(paint, shape, mask, seed, pm, bb):
    """
    Generic candy coat — Beer-Lambert single-pass absorption.
    Simple colored transparency over base with depth-dependent darkening.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Generate subtle base variation
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1600)
    
    # Candy absorption: color intensity modulated by noise
    candy_color = np.array([0.8, 0.1, 0.1])  # Red candy base
    absorption = 0.7 + noise * 0.2  # Depth variation
    effect = base * (1.0 - absorption[:,:,np.newaxis]) + candy_color[np.newaxis, np.newaxis, :] * absorption[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy(shape, seed, sm, base_m, base_r):
    """
    Generic candy spec — weak highlight with slight roughness from pigment settling.
    """
    h, w = shape
    M = base_m * 0.6 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1600) * 0.2
    R = base_r * 0.4 + multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1601) * 0.15
    CC = np.ones((h, w), dtype=np.float32) * 0.5
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_candy_burgundy_v2(paint, shape, mask, seed, pm, bb):
    """
    Deep burgundy candy with wine-red absorption profile.
    Multi-scale absorption creates depth with warm undertones.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise_coarse = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 1602)
    noise_fine = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 1603)
    
    # Wine-red absorption: deep burgundy with warm variation
    burgundy = np.array([0.4, 0.05, 0.08])
    absorption = 0.75 + (noise_coarse * 0.15 + noise_fine * 0.1)
    effect = base * (1.0 - absorption[:,:,np.newaxis]) + burgundy[np.newaxis, np.newaxis, :] * absorption[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_burgundy(shape, seed, sm, base_m, base_r):
    """
    Burgundy spec — muted highlight with wine-stained appearance.
    """
    h, w = shape
    M = base_m * 0.5 + multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 1604) * 0.15
    R = base_r * 0.3 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1605) * 0.12
    CC = np.ones((h, w), dtype=np.float32) * 0.4
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_candy_chrome_v2(paint, shape, mask, seed, pm, bb):
    """
    Candy over chrome base — maximum reflection + color filter.
    Fresnel effect with strong directional highlights over reflective substrate.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Fresnel approximation: more reflection at grazing angles
    grid = get_mgrid((h, w))
    fresnel = 0.3 + 0.4 * np.abs(np.sin(grid[1] * np.pi))  # View angle simulation
    
    noise = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.3, 0.3], seed + 1606)
    
    # Chrome candy: intense color filter over reflective base
    candy_filter = np.array([0.9, 0.3, 0.1])
    reflection = fresnel * (0.8 + noise * 0.15)
    effect = base * (1.0 - reflection[:,:,np.newaxis] * 0.6) + candy_filter[np.newaxis, np.newaxis, :] * reflection[:,:,np.newaxis] * 0.7
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_chrome(shape, seed, sm, base_m, base_r):
    """
    Chrome candy spec — strong metallic highlight with sharp edges.
    """
    h, w = shape
    grid = get_mgrid((h, w))
    fresnel_spec = 0.5 + 0.3 * np.abs(np.sin(grid[1] * np.pi))
    M = base_m * 0.9 + fresnel_spec * 0.2
    R = base_r * 0.8 + multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1607) * 0.15
    CC = np.ones((h, w), dtype=np.float32) * 0.8
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))

def paint_candy_emerald_v2(paint, shape, mask, seed, pm, bb):
    """
    Green candy with copper phthalocyanine pigment absorption.
    Deep green with subtle blue shift — wavelength-dependent penetration.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise_primary = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1608)
    noise_secondary = multi_scale_noise((h, w), [1, 3, 6], [0.4, 0.3, 0.3], seed + 1609)
    
    # Emerald absorption: deep green with blue undertone
    emerald = np.array([0.1, 0.5, 0.3])
    absorption = 0.72 + (noise_primary * 0.15 + noise_secondary * 0.08)
    effect = base * (1.0 - absorption[:,:,np.newaxis]) + emerald[np.newaxis, np.newaxis, :] * absorption[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_emerald(shape, seed, sm, base_m, base_r):
    """
    Emerald spec — cool green reflection with moderate sparkle.
    """
    h, w = shape
    M = base_m * 0.55 + multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.3, 0.3], seed + 1610) * 0.18
    R = base_r * 0.45 + multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1611) * 0.14
    CC = np.ones((h, w), dtype=np.float32) * 0.55
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_hydrographic_v2(paint, shape, mask, seed, pm, bb):
    """
    Water transfer film with Plateau-Rayleigh instability pattern.
    Thin film creates ripple-like surface waves with color shifts.
    """
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
    M = base_m * 0.5 + ripple_pattern * 0.25
    R = base_r * 0.35 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1613) * 0.18
    CC = np.ones((h, w), dtype=np.float32) * 0.6
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_jelly_pearl_v2(paint, shape, mask, seed, pm, bb):
    """
    Translucent jelly base with suspended pearl mica.
    Soft translucency with embedded light-scattering particles.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Pearl particle distribution (sparse high-intensity spots)
    particle_noise = multi_scale_noise((h, w), [8, 16], [0.4, 0.6], seed + 1614)
    particles = np.clip(particle_noise * 2.0 - 1.5, 0, 1)
    
    # Jelly base: translucent with soft color
    jelly = np.array([0.7, 0.5, 0.6])
    jelly_strength = 0.5
    particle_contribution = particles[:,:,np.newaxis] * np.array([0.9, 0.85, 0.8])
    effect = base * (1.0 - jelly_strength) + jelly[np.newaxis, np.newaxis, :] * jelly_strength + particle_contribution * 0.3
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_jelly_pearl(shape, seed, sm, base_m, base_r):
    """
    Jelly pearl spec — soft scattered highlights from particle suspension.
    """
    h, w = shape
    particle_noise = multi_scale_noise((h, w), [8, 16], [0.4, 0.6], seed + 1615)
    particles = np.clip(particle_noise * 2.0 - 1.5, 0, 1)
    M = base_m * 0.4 + particles * 0.35
    R = base_r * 0.25 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1616) * 0.2
    CC = np.ones((h, w), dtype=np.float32) * 0.65
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))

def paint_moonstone_v2(paint, shape, mask, seed, pm, bb):
    """
    Adularescence light scattering from orthoclase feldspar layers.
    Moving light shimmer effect — glow travels across surface.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    grid = get_mgrid((h, w))
    # Adularescence: light ray traveling across surface
    shimmer = 0.5 + 0.4 * np.sin((grid[0] + grid[1]) * 3 + seed) * np.exp(-((grid[0] - 0.5)**2 + (grid[1] - 0.5)**2) * 3)
    
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
    """
    h, w = shape
    grid = get_mgrid((h, w))
    shimmer = 0.5 + 0.4 * np.sin((grid[0] + grid[1]) * 3 + seed)
    M = base_m * 0.7 + shimmer * 0.3
    R = base_r * 0.5 + multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1618) * 0.2
    CC = np.ones((h, w), dtype=np.float32) * 0.7
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_opal_v2(paint, shape, mask, seed, pm, bb):
    """
    Play-of-color from silica sphere diffraction grating.
    Spectral iridescence from multiple sphere sizes at different depths.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    grid = get_mgrid((h, w))
    # Diffraction grating simulation: multiple wavelengths create rainbow
    red_grating = 0.4 + 0.3 * np.sin(grid[0] * 5 + seed * 0.7)
    green_grating = 0.4 + 0.3 * np.sin(grid[0] * 7 + seed * 1.1)
    blue_grating = 0.4 + 0.3 * np.sin(grid[0] * 9 + seed * 1.5)
    
    noise = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.3, 0.3], seed + 1619)
    
    # Build spectral effect
    r_channel = red_grating * 0.7 + noise * 0.15
    g_channel = green_grating * 0.6 + noise * 0.12
    b_channel = blue_grating * 0.65 + noise * 0.14
    
    effect = np.stack([r_channel, g_channel, b_channel], axis=2)
    effect = base * 0.4 + effect * 0.6
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.32 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_opal(shape, seed, sm, base_m, base_r):
    """
    Opal spec — spectral iridescent highlights with shifting colors.
    """
    h, w = shape
    grid = get_mgrid((h, w))
    color_shift = np.sin(grid[0] * 5 + seed * 0.7)
    M = base_m * 0.65 + (color_shift * 0.5 + 0.5) * 0.25
    R = base_r * 0.4 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1620) * 0.25
    CC = np.ones((h, w), dtype=np.float32) * 0.75
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_smoked_v2(paint, shape, mask, seed, pm, bb):
    """
    Smoke tint darkening via Beer-Lambert gray absorption.
    Translucent smoke effect — darkens underlying color uniformly.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.3, 0.3], seed + 1621)
    
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
    M = base_m * 0.4 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1622) * 0.12
    R = base_r * 0.3 + multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1623) * 0.1
    CC = np.ones((h, w), dtype=np.float32) * 0.3
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))

def paint_spectraflame_v2(paint, shape, mask, seed, pm, bb):
    """
    Multi-wavelength selective candy — different from standard candy.
    Wavelength-dependent absorption at three key color channels.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise_r = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1624)
    noise_g = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1625)
    noise_b = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1626)
    
    # Wavelength-dependent absorption
    r_absorption = 0.6 + noise_r * 0.18
    g_absorption = 0.75 + noise_g * 0.15
    b_absorption = 0.85 + noise_b * 0.12
    
    # Spectraflame: intense multi-color (orange-red-gold)
    effect_r = base[:,:,0] * (1.0 - r_absorption) + 0.95 * r_absorption
    effect_g = base[:,:,1] * (1.0 - g_absorption) + 0.45 * g_absorption
    effect_b = base[:,:,2] * (1.0 - b_absorption) + 0.15 * b_absorption
    
    effect = np.stack([effect_r, effect_g, effect_b], axis=2)
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.24 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_spectraflame(shape, seed, sm, base_m, base_r):
    """
    Spectraflame spec — intense multi-wavelength highlight.
    """
    h, w = shape
    M = base_m * 0.65 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1627) * 0.22
    R = base_r * 0.55 + multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1628) * 0.18
    CC = np.ones((h, w), dtype=np.float32) * 0.72
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_tinted_clear_v2(paint, shape, mask, seed, pm, bb):
    """
    Colored clearcoat with uniform Beer-Lambert tint.
    Subtle color shift — nearly transparent with consistent hue.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1629)
    
    # Tinted clear: light blue tint, very transparent
    clear_tint = np.array([0.85, 0.9, 0.95])
    tint_strength = 0.35 + noise * 0.1
    effect = base * (1.0 - tint_strength[:,:,np.newaxis]) + clear_tint[np.newaxis, np.newaxis, :] * tint_strength[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.2 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_tinted_clear(shape, seed, sm, base_m, base_r):
    """
    Tinted clear spec — uniform transparent highlight.
    """
    h, w = shape
    M = base_m * 0.7 + multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1630) * 0.15
    R = base_r * 0.6 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1631) * 0.12
    CC = np.ones((h, w), dtype=np.float32) * 0.8
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_tinted_lacquer_v2(paint, shape, mask, seed, pm, bb):
    """
    Nitrocellulose lacquer with dissolved dye molecules.
    Glossy finish with slight orange-peel texture from drying patterns.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Orange-peel texture pattern
    texture = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.3, 0.3], seed + 1632)
    
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
    texture = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.3, 0.3], seed + 1634)
    M = base_m * 0.75 + texture * 0.2
    R = base_r * 0.65 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1635) * 0.16
    CC = np.ones((h, w), dtype=np.float32) * 0.7
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))


def paint_tri_coat_pearl_v2(paint, shape, mask, seed, pm, bb):
    """
    Three-layer pearl with additive color mixing.
    Stacked color layers create complex iridescent effect.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Three independent pearl layers
    layer1 = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1636)
    layer2 = multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 1637)
    layer3 = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1638)
    
    # Three color components mix additively
    color1 = np.array([0.95, 0.4, 0.3])  # Red pearl
    color2 = np.array([0.3, 0.7, 0.95])  # Blue pearl
    color3 = np.array([0.4, 0.95, 0.5])  # Green pearl
    
    effect = (layer1[:,:,np.newaxis] * color1 + layer2[:,:,np.newaxis] * color2 + layer3[:,:,np.newaxis] * color3) / 3.0
    effect = np.clip(effect, 0, 1)
    effect = base * 0.5 + effect * 0.5
    
    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.3 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_tri_coat_pearl(shape, seed, sm, base_m, base_r):
    """
    Tri-coat pearl spec — complex multi-layer iridescent highlight.
    """
    h, w = shape
    layer1 = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1639)
    layer2 = multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 1640)
    layer3 = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1641)
    
    combined_layer = (layer1 + layer2 + layer3) / 3.0
    M = base_m * 0.6 + combined_layer * 0.3
    R = base_r * 0.5 + multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1642) * 0.22
    CC = np.ones((h, w), dtype=np.float32) * 0.78
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), 
            np.clip(R * 255.0, 0, 255).astype(np.float32), 
            np.clip(CC * 255.0, 0, 255).astype(np.float32))