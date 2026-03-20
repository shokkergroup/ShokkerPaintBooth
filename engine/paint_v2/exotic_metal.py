# -*- coding: utf-8 -*-
"""
Exotic Metal Paint System - Advanced optical and physical property simulations.
Implements 9 unique metallic finishes using real physics models and procedural texturing.
"""

import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# ============================================================================
# CANDY COBALT - Cobalt Aluminate Spinel Crystal Blue Absorption
# ============================================================================

def paint_candy_cobalt_v2(paint, shape, mask, seed, pm, bb):
    """
    Cobalt aluminate spinel exhibiting selective blue absorption with crystalline
    depth variation. Uses spectral response tuning for deep blue saturation.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Crystalline structure modulation
    crystal_noise = multi_scale_noise((h, w), [1, 2, 4, 8], 
                                      [0.4, 0.3, 0.2, 0.1], 1401)
    
    # Spectral absorption curve (blue-optimized)
    depth = np.clip(crystal_noise * 0.8 + 0.2, 0.1, 1.0)
    
    # Selective color absorption
    effect = np.zeros((h, w, 3), dtype=np.float32)
    effect[:,:,0] = base[:,:,0] * 0.3 * depth  # Red channel reduced
    effect[:,:,1] = base[:,:,1] * 0.5 * depth  # Green channel reduced
    effect[:,:,2] = base[:,:,2] * 1.2 * depth  # Blue channel enhanced
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_candy_cobalt(shape, seed, sm, base_m, base_r):
    """
    Cobalt spinel optical properties: high brilliance with deep saturation.
    """
    h, w = shape
    
    # Crystalline structure dominates specularity
    crystal = multi_scale_noise((h, w), [2, 4, 8], 
                               [0.5, 0.3, 0.2], 1410)
    M = np.clip(base_m * (0.7 + crystal * 0.3) * 255.0, 0, 255).astype(np.float32)
    
    # Roughness reduced by crystal alignment
    rough_mod = multi_scale_noise((h, w), [1, 3, 6], 
                                 [0.4, 0.3, 0.3], 1411)
    R = np.clip(base_r * (0.5 + rough_mod * 0.2) * 255.0, 0, 255).astype(np.float32)
    
    # Color constancy around blue
    CC = np.clip(crystal * 0.3 + 0.7 * 255.0, 0, 255).astype(np.float32)
    
    return M, R, CC


# ============================================================================
# COBALT METAL - Ferromagnetic Domain Alignment Pattern
# ============================================================================

def paint_cobalt_metal_v2(paint, shape, mask, seed, pm, bb):
    """
    Ferromagnetic cobalt metal exhibiting domain alignment patterns.
    Surface texture follows magnetic grain boundaries with directional bias.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Domain alignment pattern
    y, x = get_mgrid((h, w))
    domain_pattern = np.sin((x + y * 0.5) / 20.0 + seed * 0.01) * 0.5 + 0.5
    
    # Multi-scale grain texture
    grain = multi_scale_noise((h, w), [2, 4, 8, 16], 
                             [0.35, 0.3, 0.2, 0.15], 1402)
    
    # Domain modulation
    modulation = np.clip(grain * 0.7 + domain_pattern * 0.3, 0, 1)
    
    effect = base * np.clip(0.85 + modulation * 0.25, 0.7, 1.3)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_cobalt_metal(shape, seed, sm, base_m, base_r):
    """
    Ferromagnetic surface: moderate specularity with domain-aligned roughness.
    """
    h, w = shape
    
    # Domain pattern affects specularity
    y, x = get_mgrid((h, w))
    domain = np.sin((x + y * 0.5) / 20.0) * 0.5 + 0.5
    M = np.clip(base_m * (0.75 + domain * 0.25), 0, 1).astype(np.float32)
    
    # Roughness follows grain boundaries
    grain = multi_scale_noise((h, w), [2, 4, 8], 
                             [0.4, 0.35, 0.25], 1412)
    R = np.clip(base_r * (0.6 + grain * 0.25), 0, 1).astype(np.float32)
    
    # Neutral color
    CC = np.ones((h, w), dtype=np.float32) * 0.9
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# ============================================================================
# LIQUID TITANIUM - Liquid Metal Surface Tension Meniscus
# ============================================================================

def paint_liquid_titanium_v2(paint, shape, mask, seed, pm, bb):
    """
    Molten titanium effect with surface tension-driven meniscus simulation.
    Creates flowing, undulating surface with coherent directional flow.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Surface tension flow field
    y, x = get_mgrid((h, w))
    flow_x = np.sin(y / 15.0 + seed * 0.001) * 0.5
    flow_y = np.cos(x / 15.0 + seed * 0.001) * 0.5
    
    # Meniscus height field
    meniscus = multi_scale_noise((h, w), [3, 8, 16], 
                                [0.5, 0.3, 0.2], 1403)
    meniscus = np.clip(meniscus + flow_x + flow_y, -1, 1) * 0.5 + 0.5
    
    # Reflectance variation from curvature
    effect = base * np.clip(0.9 + meniscus * 0.35, 0.7, 1.4)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_liquid_titanium(shape, seed, sm, base_m, base_r):
    """
    Liquid surface: very high specularity with meniscus-driven roughness variation.
    """
    h, w = shape
    
    # High base specularity for liquid surface
    y, x = get_mgrid((h, w))
    meniscus = multi_scale_noise((h, w), [3, 8], 
                                [0.6, 0.4], 1413)
    M = np.clip(base_m * (0.95 + meniscus * 0.05), 0.85, 1.0).astype(np.float32)
    
    # Very low roughness with meniscus variation
    R = np.clip(base_r * (0.25 + meniscus * 0.15), 0, 1).astype(np.float32)
    
    # Neutral with slight warm cast
    CC = np.ones((h, w), dtype=np.float32) * 0.95
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# ============================================================================
# MERCURY - Marangoni Flow Surface Tension Pattern
# ============================================================================

def paint_mercury_v2(paint, shape, mask, seed, pm, bb):
    """
    Mercury surface: Marangoni convection creates dynamic flowing pattern.
    Temperature-gradient driven surface flow with characteristic silvery sheen.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Marangoni convection pattern (temperature-gradient driven)
    y, x = get_mgrid((h, w))
    gradient_x = np.cos(x / 12.0 + seed * 0.002) * 0.6
    gradient_y = np.sin(y / 12.0 + seed * 0.002) * 0.6
    
    # Convection cells
    convection = multi_scale_noise((h, w), [4, 10, 20], 
                                  [0.45, 0.35, 0.2], 1404)
    convection = np.clip(gradient_x + gradient_y + convection * 0.3, -1, 1) * 0.5 + 0.5
    
    # Mercury's characteristic reflectivity enhancement
    effect = base * np.clip(1.1 + convection * 0.25, 0.8, 1.5)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.2 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_mercury(shape, seed, sm, base_m, base_r):
    """
    Mercury optical properties: extreme specularity with flow-pattern variation.
    """
    h, w = shape
    
    # Very high specularity with Marangoni modulation
    y, x = get_mgrid((h, w))
    flow = np.sin(x / 12.0) * np.cos(y / 12.0) * 0.5 + 0.5
    M = np.clip(base_m * (0.98 + flow * 0.02), 0.9, 1.0).astype(np.float32)
    
    # Extremely low roughness
    roughness = multi_scale_noise((h, w), [4, 10], 
                                 [0.6, 0.4], 1414)
    R = np.clip(base_r * (0.15 + roughness * 0.1), 0, 1).astype(np.float32)
    
    # Pure neutral silver
    CC = np.ones((h, w), dtype=np.float32) * 1.0
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# ============================================================================
# PARADIGM MERCURY - Darker Alien Variant
# ============================================================================

def paint_p_mercury_v2(paint, shape, mask, seed, pm, bb):
    """
    Paradigm mercury: darker, more alien variant with absorption in highlights.
    Exotic material with non-standard optical behavior and inky darkness.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Chaotic, writhing surface pattern
    chaos = multi_scale_noise((h, w), [3, 6, 12, 24], 
                             [0.3, 0.3, 0.25, 0.15], 1405)
    
    # Absorption modulation - inverts typical specularity
    y, x = get_mgrid((h, w))
    absorption = np.sin(x / 8.0) * np.sin(y / 8.0 + seed * 0.003) * 0.5 + 0.5
    
    # Darkened effect with inky absorption
    effect = base * np.clip(0.4 + chaos * 0.2 + absorption * 0.15, 0.3, 0.8)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.08 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_p_mercury(shape, seed, sm, base_m, base_r):
    """Liquid metal: high M, very low R, max clearcoat. Slight R increase in pools only."""
    h, w = shape[:2] if len(shape) > 2 else shape
    pool = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], 1415)
    M = np.full((h, w), 248.0, dtype=np.float32)
    R = np.clip((0.02 + pool * 0.03) * 255.0, 0, 255).astype(np.float32)  # 5-13
    CC = np.full((h, w), 16.0, dtype=np.float32)
    CC = np.clip(CC, 16.0, 255.0).astype(np.float32)  # 16 = max clearcoat
    return M, R, CC


# ============================================================================
# PLATINUM - Noble Metal d-Band UV Reflectance Model
# ============================================================================

def paint_platinum_v2(paint, shape, mask, seed, pm, bb):
    """
    Platinum: noble metal with d-band electron response and superior UV reflectance.
    Highly polished appearance with subtle wavelength-dependent variations.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # d-band structure creates micro-reflectance nodes
    d_band = multi_scale_noise((h, w), [1, 3, 6, 12], 
                               [0.3, 0.25, 0.25, 0.2], 1406)
    
    # Subtle wavelength dispersion (d-band response)
    y, x = get_mgrid((h, w))
    uv_response = np.cos(x / 25.0) * 0.3 + np.sin(y / 25.0) * 0.2
    
    # Enhance all channels with noble metal response
    effect = base * np.clip(1.15 + d_band * 0.15 + uv_response * 0.1, 0.95, 1.35)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.16 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_platinum(shape, seed, sm, base_m, base_r):
    """
    Platinum specs: highest noble metal specularity with controlled roughness.
    """
    h, w = shape
    
    # Ultra-high specularity with d-band nodes
    d_band = multi_scale_noise((h, w), [3, 6], 
                              [0.5, 0.5], 1416)
    M = np.clip(base_m * (0.95 + d_band * 0.05), 0.88, 1.0).astype(np.float32)
    
    # Low roughness befitting noble metal polish
    y, x = get_mgrid((h, w))
    polish = np.clip(np.cos(x / 25.0) * np.cos(y / 25.0) * 0.5 + 0.5, 0, 1)
    R = np.clip(base_r * (0.35 + polish * 0.2), 0, 1).astype(np.float32)
    
    # Pure neutral - noble metal
    CC = np.ones((h, w), dtype=np.float32) * 0.98
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# ============================================================================
# SURGICAL STEEL - Austenitic Stainless Passive Oxide Film
# ============================================================================

def paint_surgical_steel_v2(paint, shape, mask, seed, pm, bb):
    """
    Austenitic stainless steel: passive oxide film creates matte-polished finish.
    Grain structure visible beneath protective oxide layer.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Austenite grain structure
    grains = multi_scale_noise((h, w), [4, 8, 16, 32], 
                              [0.35, 0.3, 0.2, 0.15], 1407)
    
    # Passive oxide film creates characteristic matte-polished look
    oxide_film = multi_scale_noise((h, w), [2, 5, 10], 
                                  [0.4, 0.35, 0.25], 1417)
    
    # Combination of grain and oxide
    surface = np.clip(grains * 0.6 + oxide_film * 0.4, 0, 1)
    
    effect = base * np.clip(0.95 + surface * 0.15, 0.85, 1.15)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.11 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_surgical_steel(shape, seed, sm, base_m, base_r):
    """
    Surgical steel specs: moderate specularity with oxide film roughness.
    """
    h, w = shape
    
    # Moderate specularity with grain variation
    grains = multi_scale_noise((h, w), [4, 8], 
                              [0.5, 0.5], 1418)
    M = np.clip(base_m * (0.7 + grains * 0.2), 0, 1).astype(np.float32)
    
    # Characteristic matte-polished roughness
    oxide = multi_scale_noise((h, w), [2, 5], 
                             [0.6, 0.4], 1419)
    R = np.clip(base_r * (0.55 + oxide * 0.25), 0, 1).astype(np.float32)
    
    # Cool neutral tone typical of stainless
    CC = np.ones((h, w), dtype=np.float32) * 0.92
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# ============================================================================
# TITANIUM RAW - Alpha-Beta Phase Grain Boundary Texture
# ============================================================================

def paint_titanium_raw_v2(paint, shape, mask, seed, pm, bb):
    """
    Raw titanium: alpha-beta phase grain boundaries create distinctive texture.
    Unpolished surface with visible phase separation and crystallographic anisotropy.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Alpha and beta phase grains
    alpha_phase = multi_scale_noise((h, w), [6, 12, 24], 
                                   [0.4, 0.35, 0.25], 1408)
    beta_phase = multi_scale_noise((h, w), [8, 16, 32], 
                                  [0.4, 0.35, 0.25], 1420)
    
    # Phase boundary contrast
    y, x = get_mgrid((h, w))
    phase_boundary = np.sin(x / 20.0 + y / 20.0 + seed * 0.001) * 0.5 + 0.5
    
    grain_texture = np.clip(alpha_phase * 0.5 + beta_phase * 0.3 + 
                           phase_boundary * 0.2, 0, 1)
    
    effect = base * np.clip(0.9 + grain_texture * 0.25, 0.75, 1.25)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.13 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_titanium_raw(shape, seed, sm, base_m, base_r):
    """
    Raw titanium specs: phase-dependent specularity variation.
    """
    h, w = shape
    
    # Specularity varies by phase
    alpha = multi_scale_noise((h, w), [6, 12], 
                             [0.5, 0.5], 1421)
    beta = multi_scale_noise((h, w), [8, 16], 
                            [0.5, 0.5], 1422)
    M = np.clip(base_m * (0.65 + alpha * 0.15 + beta * 0.15), 0, 1).astype(np.float32)
    
    # High roughness from unpolished grain boundaries
    y, x = get_mgrid((h, w))
    phase_boundary = np.sin(x / 20.0 + y / 20.0) * 0.5 + 0.5
    R = np.clip(base_r * (0.68 + phase_boundary * 0.25), 0, 1).astype(np.float32)
    
    # Neutral with slight warm undertone
    CC = np.ones((h, w), dtype=np.float32) * 0.88
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))


# ============================================================================
# TUNGSTEN - Refractory Metal High-Density Grain Structure
# ============================================================================

def paint_tungsten_v2(paint, shape, mask, seed, pm, bb):
    """
    Tungsten: highest density refractory metal with characteristic grain structure.
    Dense, tight grain boundaries with deep gray appearance and metallic sheen.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Dense grain structure at multiple scales
    grain_fine = multi_scale_noise((h, w), [1, 2, 4], 
                                  [0.4, 0.35, 0.25], 1409)
    grain_coarse = multi_scale_noise((h, w), [8, 16, 32], 
                                    [0.35, 0.35, 0.3], 1423)
    
    # High-density packing creates tight grain boundaries
    grain_density = np.clip(grain_fine * 0.5 + grain_coarse * 0.5, 0, 1)
    
    # Tungsten's characteristic darkening
    effect = base * np.clip(0.85 + grain_density * 0.2, 0.7, 1.1)[:,:,np.newaxis]
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.09 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_tungsten(shape, seed, sm, base_m, base_r):
    """
    Tungsten specs: moderate specularity with dense grain roughness.
    """
    h, w = shape
    
    # Moderate specularity for refractory metal
    grain = multi_scale_noise((h, w), [8, 16], 
                             [0.6, 0.4], 1424)
    M = np.clip(base_m * (0.68 + grain * 0.18), 0, 1).astype(np.float32)
    
    # High roughness from dense grain boundaries
    fine_grain = multi_scale_noise((h, w), [1, 4], 
                                  [0.5, 0.5], 1425)
    R = np.clip(base_r * (0.62 + fine_grain * 0.28), 0, 1).astype(np.float32)
    
    # Deep neutral gray tone
    CC = np.ones((h, w), dtype=np.float32) * 0.75
    
    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 0, 255).astype(np.float32), np.clip(CC * 255.0, 0, 255).astype(np.float32))
