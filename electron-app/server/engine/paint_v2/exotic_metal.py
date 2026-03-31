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
    depth variation. Beer-Lambert exponential absorption: alpha_red >> alpha_blue
    gives characteristic deepening at high absorption depths.
    WARN-CANDY-002 FIX: replaced linear channel scale with Beer-Lambert exp(-alpha*depth).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Crystalline structure modulation — seed-derived for per-painter variation
    crystal_noise = multi_scale_noise((h, w), [1, 2, 4, 8],
                                      [0.4, 0.3, 0.2, 0.1], seed + 1401)

    # Absorption depth field (0.1–1.0)
    depth = np.clip(crystal_noise * 0.8 + 0.2, 0.1, 1.0)

    # Beer-Lambert selective absorption: cobalt absorbs red/green, transmits blue
    effect = np.zeros((h, w, 3), dtype=np.float32)
    effect[:,:,0] = base[:,:,0] * np.exp(-3.5 * depth)  # Red: heavily absorbed
    effect[:,:,1] = base[:,:,1] * np.exp(-2.0 * depth)  # Green: moderately absorbed
    effect[:,:,2] = base[:,:,2] * np.exp(-0.3 * depth)  # Blue: transmits through
    
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + 
                     effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_candy_cobalt(shape, seed, sm, base_m, base_r):
    """
    Cobalt spinel optical properties: high brilliance with deep saturation.
    """
    h, w = shape

    # Crystalline structure dominates specularity — seeds derived from seed param
    crystal = multi_scale_noise((h, w), [2, 4, 8],
                               [0.5, 0.3, 0.2], seed + 1410)
    M = np.clip(base_m * (0.7 + crystal * 0.3) * 255.0, 0, 255).astype(np.float32)

    # Roughness reduced by crystal alignment — seeds derived from seed param
    rough_mod = multi_scale_noise((h, w), [1, 3, 6],
                                 [0.4, 0.3, 0.3], seed + 1411)
    R = np.clip(base_r * (0.5 + rough_mod * 0.2) * 255.0, 15, 255).astype(np.float32)  # GGX floor

    # CC: max gloss clearcoat (B=16 = max gloss in iRacing), slight crystal variation
    CC = np.clip(16.0 + crystal * 8.0, 16, 30).astype(np.float32)

    return M, R, CC


# ============================================================================
# COBALT METAL - Ferromagnetic Domain Alignment Pattern
# ============================================================================

def paint_cobalt_metal_v2(paint, shape, mask, seed, pm, bb):
    """
    Ferromagnetic cobalt metal exhibiting quantized crystalline domain facets.
    Discrete grain orientations produce sharp facet boundaries — not smooth sinusoidal
    modulation. Cobalt's hexagonal close-packed crystal structure creates 6 distinct
    grain orientation regions with bright centres and dark boundaries between them.
    LAZY-EXOTIC-001 FIX: quantized floor(grain*6)/6 crystalline facets replace sinusoid.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Multi-scale grain texture drives facet orientation map
    grain = multi_scale_noise((h, w), [2, 4, 8, 16],
                              [0.35, 0.3, 0.2, 0.15], seed + 1402)
    # Quantize to 6 discrete crystalline orientation bands (cobalt HCP: 6-fold symmetry)
    facets = np.floor(grain * 6.0) / 6.0
    # Domain boundary: bright at facet centre, dark at grain boundary edge
    facet_center_dist = np.abs(grain - facets - 1.0 / 12.0)
    facet_glow = np.exp(-facet_center_dist * 25.0)  # sharp per-facet brightness peak
    modulation = np.clip(facets * 0.5 + facet_glow * 0.4, 0, 1)

    effect = base * np.clip(0.85 + modulation * 0.25, 0.7, 1.3)[:, :, np.newaxis]

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    # Cobalt blue-tinted metallic reflection — WEAK-EXOTIC-001 FIX
    result[..., 2] = np.clip(result[..., 2] * 1.06, 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.12 * pm * mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_cobalt_metal(shape, seed, sm, base_m, base_r):
    """
    Ferromagnetic surface: moderate specularity with domain-aligned roughness.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

    # Domain pattern affects specularity
    y, x = get_mgrid((h, w))
    domain = np.sin((x + y * 0.5) / 20.0) * 0.5 + 0.5
    M = np.clip(base_m * (0.75 + domain * 0.25), 0, 1).astype(np.float32)
    
    # Roughness follows grain boundaries
    grain = multi_scale_noise((h, w), [2, 4, 8], 
                             [0.4, 0.35, 0.25], 1412)
    R = np.clip(base_r * (0.6 + grain * 0.25), 0, 1).astype(np.float32)
    
    # BUG-EXOTIC-SPEC-001 FIX: CC in 0-255 range (16=max gloss). Polished cobalt grain shimmer.
    CC = np.clip(16.0 + grain * 8.0 * sm, 16, 30).astype(np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32))


# ============================================================================
# LIQUID TITANIUM - Liquid Metal Surface Tension Meniscus
# ============================================================================

def paint_liquid_titanium_v2(paint, shape, mask, seed, pm, bb):
    """
    Molten titanium effect with domain-warp driven flow topology.
    Two noise fields define displacement vectors; a third field sampled at the
    warped positions produces organic, folded flow patterns impossible to fake
    with a simple sinusoid — titanium melt convects in turbulent Rayleigh–Bénard
    cells, not periodic fringe patterns.
    LAZY-EXOTIC-001 FIX: domain-warp flow replaces plain sin(y/15)+cos(x/15).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Two independent noise fields become warp displacement vectors
    warp_u = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + 1450)
    warp_v = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + 1451)
    disp_x = np.sin(warp_u * np.pi)   # x-direction warp [-1, 1]
    disp_y = np.cos(warp_v * np.pi)   # y-direction warp [-1, 1]

    # Pixel-space warp: 5% of canvas size per axis
    yy = np.arange(h, dtype=np.float32).reshape(h, 1) * np.ones((1, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1, w) * np.ones((h, 1), dtype=np.float32)
    yi = np.clip((yy + disp_y * h * 0.05).astype(np.int32), 0, h - 1)
    xi = np.clip((xx + disp_x * w * 0.05).astype(np.int32), 0, w - 1)

    # Sample a third noise field at warped positions → organic folded flow topology
    flow_base = multi_scale_noise((h, w), [3, 8, 16], [0.5, 0.3, 0.2], seed + 1403)
    meniscus = flow_base[yi, xi]

    # Reflectance variation from flow curvature
    effect = base * np.clip(0.9 + meniscus * 0.35, 0.7, 1.4)[:, :, np.newaxis]

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    # Cool silver — R*0.95, B*1.05 — WEAK-EXOTIC-001 FIX
    result[..., 0] = np.clip(result[..., 0] * 0.95, 0, 1)
    result[..., 2] = np.clip(result[..., 2] * 1.05, 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.18 * pm * mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_liquid_titanium(shape, seed, sm, base_m, base_r):
    """
    Liquid surface: very high specularity with meniscus-driven roughness variation.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

    # High base specularity for liquid surface
    y, x = get_mgrid((h, w))
    meniscus = multi_scale_noise((h, w), [3, 8], 
                                [0.6, 0.4], 1413)
    M = np.clip(base_m * (0.95 + meniscus * 0.05), 0.85, 1.0).astype(np.float32)
    
    # Very low roughness with meniscus variation
    R = np.clip(base_r * (0.25 + meniscus * 0.15), 0, 1).astype(np.float32)
    
    # BUG-EXOTIC-SPEC-001 FIX: CC in 0-255 range. Near-perfect liquid mirror surface.
    CC = np.clip(16.0 + meniscus * 4.0 * sm, 16, 22).astype(np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32))


# ============================================================================
# MERCURY - Marangoni Flow Surface Tension Pattern
# ============================================================================

def paint_mercury_v2(paint, shape, mask, seed, pm, bb):
    """
    Mercury surface: gravity-pooled meniscus via Gaussian vertical convection blobs.
    Real mercury under gravity pools into distinct bright ellipsoids separated by dark
    thinning zones — an exp() meniscus profile, NOT a periodic fringe pattern.
    Horizontally the pool centres wander via noise (sloshing), vertically each pool
    follows a Gaussian brightness envelope around its centre-line.
    LAZY-EXOTIC-001 FIX: exp() meniscus pools replace plain cos(x/12)+sin(y/12).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Pool centres shift horizontally via low-freq noise (mercury sloshing)
    pool_noise = multi_scale_noise((h, w), [16, 32, 64], [0.5, 0.3, 0.2], seed + 1452)
    # Pool centre y-positions: noise maps to 0.15–0.85 of canvas height
    pool_center_y = pool_noise * 0.70 + 0.15   # (h, w), float in [0.15, 0.85]

    # Normalised y coordinate — (h, 1) broadcasts against (h, w) pool_center_y
    yy_norm = np.arange(h, dtype=np.float32).reshape(h, 1) / float(h)
    sigma = 0.09   # pool half-width = 9% of canvas height
    pool_field = np.exp(-((yy_norm - pool_center_y) ** 2) / (2.0 * sigma ** 2))

    # Fine surface ripple modulates pool edges for organic look
    ripple = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 1404)
    convection = np.clip(pool_field * 0.70 + ripple * 0.30, 0, 1)

    # Mercury's characteristic high reflectivity in pooled zones
    effect = base * np.clip(1.1 + convection * 0.25, 0.8, 1.5)[:, :, np.newaxis]

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    # Warm silver — R*1.03, B*0.97 — WEAK-EXOTIC-001 FIX
    result[..., 0] = np.clip(result[..., 0] * 1.03, 0, 1)
    result[..., 2] = np.clip(result[..., 2] * 0.97, 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.2 * pm * mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_mercury(shape, seed, sm, base_m, base_r):
    """
    Mercury optical properties: Benard-Marangoni convection cell modulation.
    Surface-tension-driven Marangoni instability creates irregular convective
    cells on liquid mercury. Cell interiors are mirror-flat (low R, high M);
    cell boundaries where cooler mercury wells up are marginally rougher.
    Structurally distinct from spec_liquid_titanium warped-sine swirl field.
    WARN-EXOTIC-002 FIX: replaced sin(x)*cos(y) periodic grid with
    multi-scale noise cellular structure.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

    # Marangoni cell field: multi-scale noise at medium spatial frequency
    # produces irregular, roughly-hexagonal cellular texture
    cell = multi_scale_noise((h, w), [16, 32, 8], [0.5, 0.35, 0.15], seed + 1414)

    # Edge mask: peaks at intermediate cell values (cell boundaries), zero at extremes
    edge = 1.0 - np.abs(cell * 2.0 - 1.0)   # 0 at extremes, 1 at mid (boundaries)
    edge = np.minimum(edge * 1.6, 1.0)        # sharpen boundary band

    # M: extremely high (liquid mercury is near-perfect mirror); small dip at boundaries
    M = np.clip(base_m * (1.0 - edge * 0.07 * sm), 0.85, 1.0).astype(np.float32)

    # R: near-zero (liquid mirror surface); marginal rise at Marangoni cell boundaries
    R = np.clip(base_r * (0.10 + edge * 0.20 * sm), 0.0, 0.28).astype(np.float32)

    # CC: maximum gloss -- liquid mercury has no surface defects
    CC = np.full((h, w), 16.0, dtype=np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


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
    R = np.clip((0.02 + pool * 0.03) * 255.0, 15, 255).astype(np.float32)  # GGX floor (was 5-13)
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
    # Cool neutral noble metal — R*0.97, G*0.99, B*1.02 — WEAK-EXOTIC-001 FIX
    result[..., 0] = np.clip(result[..., 0] * 0.97, 0, 1)
    result[..., 1] = np.clip(result[..., 1] * 0.99, 0, 1)
    result[..., 2] = np.clip(result[..., 2] * 1.02, 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.16 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_platinum(shape, seed, sm, base_m, base_r):
    """
    Platinum specs: highest noble metal specularity with controlled roughness.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

    # Ultra-high specularity with d-band nodes
    d_band = multi_scale_noise((h, w), [3, 6], 
                              [0.5, 0.5], 1416)
    M = np.clip(base_m * (0.95 + d_band * 0.05), 0.88, 1.0).astype(np.float32)
    
    # Low roughness befitting noble metal polish
    y, x = get_mgrid((h, w))
    polish = np.clip(np.cos(x / 25.0) * np.cos(y / 25.0) * 0.5 + 0.5, 0, 1)
    R = np.clip(base_r * (0.35 + polish * 0.2), 0, 1).astype(np.float32)
    
    # BUG-EXOTIC-SPEC-001 FIX: CC in 0-255 range. High-polish platinum, d-band node variation.
    CC = np.clip(16.0 + d_band * 6.0 * sm, 16, 24).astype(np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32))


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
    # Cold 316 SST tone — R*0.95, G*0.98, B*1.02 — WEAK-EXOTIC-001 FIX
    result[..., 0] = np.clip(result[..., 0] * 0.95, 0, 1)
    result[..., 1] = np.clip(result[..., 1] * 0.98, 0, 1)
    result[..., 2] = np.clip(result[..., 2] * 1.02, 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.11 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_surgical_steel(shape, seed, sm, base_m, base_r):
    """
    Surgical steel specs: moderate specularity with oxide film roughness.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

    # Moderate specularity with grain variation
    grains = multi_scale_noise((h, w), [4, 8], 
                              [0.5, 0.5], 1418)
    M = np.clip(base_m * (0.7 + grains * 0.2), 0, 1).astype(np.float32)
    
    # Characteristic matte-polished roughness
    oxide = multi_scale_noise((h, w), [2, 5], 
                             [0.6, 0.4], 1419)
    R = np.clip(base_r * (0.55 + oxide * 0.25), 0, 1).astype(np.float32)
    
    # BUG-EXOTIC-SPEC-001 FIX: CC in 0-255 range. Polished steel with slight oxide variation.
    CC = np.clip(16.0 + oxide * 20.0 * sm, 16, 45).astype(np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32))


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
    # Warm gray alpha-beta titanium — R*1.05, G*0.98, B*0.96 — WEAK-EXOTIC-001 FIX
    result[..., 0] = np.clip(result[..., 0] * 1.05, 0, 1)
    result[..., 1] = np.clip(result[..., 1] * 0.98, 0, 1)
    result[..., 2] = np.clip(result[..., 2] * 0.96, 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.13 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_titanium_raw(shape, seed, sm, base_m, base_r):
    """
    Raw titanium specs: phase-dependent specularity variation.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

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
    
    # BUG-EXOTIC-SPEC-001 FIX: CC in 0-255 range. Raw titanium thermal interference color.
    CC = np.clip(30.0 + phase_boundary * 40.0 * sm, 30, 80).astype(np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32))


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
    # Charcoal desaturation — refractory metal near-gray — WEAK-EXOTIC-001 FIX
    gray = result.mean(axis=2, keepdims=True).astype(np.float32)
    result = np.clip(result * 0.3 + gray * 0.7, 0, 1).astype(np.float32)
    return np.clip(result + bb[:,:,np.newaxis] * 0.09 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_tungsten(shape, seed, sm, base_m, base_r):
    """
    Tungsten specs: moderate specularity with dense grain roughness.
    """
    h, w = shape[:2] if len(shape) > 2 else shape

    # Moderate specularity for refractory metal
    grain = multi_scale_noise((h, w), [8, 16], 
                             [0.6, 0.4], 1424)
    M = np.clip(base_m * (0.68 + grain * 0.18), 0, 1).astype(np.float32)
    
    # High roughness from dense grain boundaries
    fine_grain = multi_scale_noise((h, w), [1, 4], 
                                  [0.5, 0.5], 1425)
    R = np.clip(base_r * (0.62 + fine_grain * 0.28), 0, 1).astype(np.float32)
    
    # BUG-EXOTIC-SPEC-001 FIX: CC in 0-255 range. Refractory metal satin — polished but not mirror.
    CC = np.clip(50.0 + grain * 30.0 * sm, 50, 90).astype(np.float32)

    return (np.clip(M * 255.0, 0, 255).astype(np.float32), np.clip(R * 255.0, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32))
