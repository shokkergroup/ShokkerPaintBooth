# -*- coding: utf-8 -*-
"""
Exotic Metal Paint System - Advanced optical and physical property simulations.
Implements 9 unique metallic finishes using real physics models and procedural texturing.
"""

import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


def _norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _micro_speckle(shape, seed, density=0.035):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(seed)
    n = min(int(h * w * density), 160000)
    out = np.zeros((h, w), dtype=np.float32)
    if n > 0:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.15, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    return np.maximum.reduce([
        out,
        np.roll(out, 1, axis=0) * 0.35,
        np.roll(out, -1, axis=1) * 0.35,
    ]).astype(np.float32)


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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    """Cobalt spinel optical properties. MARRIED to paint seed+1401."""
    h, w = shape
    # MARRIED to paint_candy_cobalt_v2: seed+1401 [1,2,4,8]
    crystal = multi_scale_noise((h, w), [1, 2, 4, 8], [0.4, 0.3, 0.2, 0.1], seed + 1401)
    # base_m is 0-255 — compute directly in 0-255 range (was double-scaling via *255)
    M = np.clip(base_m * 0.7 + crystal * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r * 0.5 + crystal * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + crystal * 8.0 * sm, 16, 30).astype(np.float32)
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Multi-scale grain texture drives facet orientation map
    grain = multi_scale_noise((h, w), [16, 32, 64, 128],
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
    """Ferromagnetic surface. MARRIED to paint seed+1402 [2,4,8,16]."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_cobalt_metal_v2: seed+1402 [2,4,8,16]
    grain = multi_scale_noise((h, w), [16, 32, 64, 128], [0.35, 0.3, 0.2, 0.15], seed + 1402)
    facets = np.floor(grain * 6.0) / 6.0
    facet_glow = np.exp(-np.abs(grain - facets - 1.0 / 12.0) * 25.0)
    # base_m is 0-255 — compute directly (was double-scaling via clip(0,1) then *255)
    M = np.clip(base_m * 0.75 + facet_glow * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r * 0.6 + grain * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + grain * 8.0 * sm, 16, 30).astype(np.float32)
    return M, R, CC


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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    """Liquid titanium surface. MARRIED to paint seed+1450/1451/1403.

    FIVE-HOUR SHIFT Win A1 (Animal's deferred fix from TWENTY WINS shift):
    pre-fix this function returned R floored at 15 + meniscus noise of
    amplitude only ±2 along R, so spec_std landed under the audit's 4.0
    threshold and the finish read "dead silver paint" rather than liquid
    titanium. Audit categorised it as SPEC_FLAT identity violation (B).
    Adding directional brush stripe (high-frequency flow noise) so the
    "liquid" name has visible character. base_r ignored — identity now
    lives in the spec map per Animal's recommendation.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_liquid_titanium_v2: use flow topology seed+1403 [3,8,16]
    meniscus = multi_scale_noise((h, w), [3, 8, 16], [0.5, 0.3, 0.2], seed + 1403)
    # NEW (Win A1): high-frequency directional flow stripes — fakes meniscus
    # surface tension lines you'd see on actual liquid metal.
    flow = multi_scale_noise((h, w), [2, 64], [0.7, 0.3], seed + 1404)
    # base_m is 0-255 — direct computation (was double-scaling)
    M = np.clip(base_m * 0.95 + meniscus * 12.0 * sm + flow * 18.0 * sm, 0, 255).astype(np.float32)
    # base_r ignored: identity lives in the spec map. R band 8-28, well clear of GGX floor.
    R = np.clip(8.0 + meniscus * 6.0 * sm + np.abs(flow) * 14.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(16.0 + meniscus * 4.0 * sm, 16, 22).astype(np.float32)
    return M, R, CC


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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    ripple = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 1404)
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
    """Mercury Marangoni cells. MARRIED to paint seed+1452/1404."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED: use paint's pool_noise seed+1452 and ripple seed+1404
    cell = multi_scale_noise((h, w), [16, 32, 64], [0.5, 0.3, 0.2], seed + 1452)  # Match paint scales
    edge = np.minimum((1.0 - np.abs(cell * 2.0 - 1.0)) * 1.6, 1.0)
    # base_m is 0-255 — direct computation (was double-scaling)
    # Mercury M is near-max, slight dip at cell boundaries
    M = np.clip(base_m - edge * 18.0 * sm, 0, 255).astype(np.float32)
    # R: very low (liquid mirror), slight rise at boundaries
    R = np.clip(15.0 + edge * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ============================================================================
# PARADIGM MERCURY - Darker Alien Variant
# ============================================================================

def paint_p_mercury_v2(paint, shape, mask, seed, pm, bb):
    """
    Paradigm mercury: darker, more alien variant with absorption in highlights.
    Exotic material with non-standard optical behavior and inky darkness.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Chaotic, writhing surface pattern
    chaos = multi_scale_noise((h, w), [3, 6, 12, 24],
                             [0.3, 0.3, 0.25, 0.15], seed + 1405)
    
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
    pool = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1415)
    M = np.full((h, w), 248.0, dtype=np.float32)
    # P-Mercury is chrome-level metallic — R<15 allowed for M≥240
    R = np.clip(5.0 + pool * 8.0 * sm, 0, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ============================================================================
# PLATINUM - Noble Metal d-Band UV Reflectance Model
# ============================================================================

def paint_platinum_v2(paint, shape, mask, seed, pm, bb):
    """
    Platinum: noble metal with d-band electron response and superior UV reflectance.
    Highly polished appearance with subtle wavelength-dependent variations.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # d-band structure creates micro-reflectance nodes
    d_band = multi_scale_noise((h, w), [1, 3, 6, 12],
                               [0.3, 0.25, 0.25, 0.2], seed + 1406)
    
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
    """Platinum noble metal. MARRIED to paint seed+1406 [1,3,6,12].

    FIVE-HOUR SHIFT Win A2 (Animal's deferred fix from TWENTY WINS shift):
    pre-fix R was `base_r * 0.35 + d_band * 8.0 * sm` clamped to 15 floor.
    base_r=4 → R locked at 15.0 floor everywhere → R_std=0.0 in audit
    → flagged SPEC_FLAT (B). Premium luxury finish reading as gray static.
    Lifting R into a real GGX-safe band [15..35] driven by polish grain.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_platinum_v2: seed+1406 [1,3,6,12]
    d_band = multi_scale_noise((h, w), [1, 3, 6, 12], [0.3, 0.25, 0.25, 0.2], seed + 1406)
    # NEW (Win A2): mid-frequency polish grain — noble metal microstructure.
    grain = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 1407)
    M = np.clip(base_m * 0.95 + d_band * 12.0 * sm, 0, 255).astype(np.float32)
    # R band 15-35 (clear of GGX floor; base_r intentionally ignored — identity in spec map).
    R = np.clip(15.0 + d_band * 6.0 * sm + grain * 12.0 * sm, 15, 35).astype(np.float32)
    CC = np.clip(16.0 + d_band * 6.0 * sm, 16, 24).astype(np.float32)
    return M, R, CC


# ============================================================================
# SURGICAL STEEL - Austenitic Stainless Passive Oxide Film
# ============================================================================

def paint_surgical_steel_v2(paint, shape, mask, seed, pm, bb):
    """
    Austenitic stainless steel: passive oxide film creates matte-polished finish.
    Grain structure visible beneath protective oxide layer.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Austenite grain structure
    grains = multi_scale_noise((h, w), [4, 8, 16, 32],
                              [0.35, 0.3, 0.2, 0.15], seed + 1407)

    # Passive oxide film creates characteristic matte-polished look
    oxide_film = multi_scale_noise((h, w), [2, 5, 10],
                                  [0.4, 0.35, 0.25], seed + 1417)
    
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
    """Surgical steel austenite. MARRIED to paint seed+1407/1417."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_surgical_steel_v2: seed+1407 [4,8,16,32], seed+1417 [2,5,10]
    grains = multi_scale_noise((h, w), [4, 8, 16, 32], [0.35, 0.3, 0.2, 0.15], seed + 1407)
    oxide = multi_scale_noise((h, w), [2, 5, 10], [0.4, 0.35, 0.25], seed + 1417)
    surface = np.clip(grains * 0.6 + oxide * 0.4, 0, 1)
    # base_m is 0-255 — direct computation (was double-scaling)
    M = np.clip(base_m * 0.7 + surface * 30.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r * 0.55 + oxide * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + oxide * 20.0 * sm, 16, 45).astype(np.float32)
    return M, R, CC


# ============================================================================
# TITANIUM RAW - Alpha-Beta Phase Grain Boundary Texture
# ============================================================================

def paint_titanium_raw_v2(paint, shape, mask, seed, pm, bb):
    """
    Raw titanium: alpha-beta phase grain boundaries create distinctive texture.
    Unpolished surface with visible phase separation and crystallographic anisotropy.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Alpha and beta phase grains
    alpha_phase = multi_scale_noise((h, w), [6, 12, 24],
                                   [0.4, 0.35, 0.25], seed + 1408)
    beta_phase = multi_scale_noise((h, w), [8, 16, 32],
                                  [0.4, 0.35, 0.25], seed + 1420)
    
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
    """Raw titanium alpha-beta phase. MARRIED to paint seed+1408/1420."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_titanium_raw_v2: seed+1408 [6,12,24], seed+1420 [8,16,32]
    alpha = multi_scale_noise((h, w), [6, 12, 24], [0.4, 0.35, 0.25], seed + 1408)
    beta = multi_scale_noise((h, w), [8, 16, 32], [0.4, 0.35, 0.25], seed + 1420)
    grain = np.clip(alpha * 0.5 + beta * 0.3, 0, 1)
    # base_m is 0-255 — direct computation (was double-scaling)
    M = np.clip(base_m * 0.65 + grain * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r * 0.68 + grain * 25.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(30.0 + grain * 40.0 * sm, 30, 80).astype(np.float32)
    return M, R, CC


# ============================================================================
# TUNGSTEN - Refractory Metal High-Density Grain Structure
# ============================================================================

def paint_tungsten_v2(paint, shape, mask, seed, pm, bb):
    """
    Tungsten: highest density refractory metal with characteristic grain structure.
    Dense, tight grain boundaries with deep gray appearance and metallic sheen.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    # Dense grain structure at multiple scales
    grain_fine = multi_scale_noise((h, w), [1, 2, 4],
                                  [0.4, 0.35, 0.25], seed + 1409)
    grain_coarse = multi_scale_noise((h, w), [8, 16, 32],
                                    [0.35, 0.35, 0.3], seed + 1423)
    
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
    """Tungsten refractory metal. MARRIED to paint seed+1409/1423."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_tungsten_v2: seed+1409 [1,2,4], seed+1423 [8,16,32]
    grain_fine = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], seed + 1409)
    grain_coarse = multi_scale_noise((h, w), [8, 16, 32], [0.35, 0.35, 0.3], seed + 1423)
    grain = np.clip(grain_fine * 0.5 + grain_coarse * 0.5, 0, 1)
    # base_m is 0-255 — direct computation (was double-scaling)
    M = np.clip(base_m * 0.68 + grain * 30.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r * 0.62 + grain * 25.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(50.0 + grain * 30.0 * sm, 50, 90).astype(np.float32)
    return M, R, CC


# ============================================================================
# 2026-04-24 regular-base rebuild overrides
# ============================================================================

def paint_titanium_raw_v2(paint, shape, mask, seed, pm, bb):
    """Raw titanium with tight crystalline grain and fine phase needles."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    alpha = _norm01(multi_scale_noise((h, w), [2, 4, 9, 18], [0.36, 0.30, 0.22, 0.12], seed + 1408))
    beta = _norm01(multi_scale_noise((h, w), [3, 7, 13, 27], [0.34, 0.30, 0.22, 0.14], seed + 1420))
    phase = _norm01(alpha * 0.56 + beta * 0.44)
    edge = np.clip(
        np.abs(np.gradient(phase, axis=0)) * 9.0 +
        np.abs(np.gradient(phase, axis=1)) * 9.0,
        0, 1
    )
    needles = _norm01(
        np.sin((x * 0.58 + y * 0.17) + phase * 2.5) +
        np.sin((x * -0.23 + y * 0.51) + beta * 2.1) +
        np.sin((x * 0.12 - y * 0.64) + alpha * 2.7)
    )
    needles = np.clip((needles - 0.61) * 3.4, 0, 1)
    micro = _micro_speckle((h, w), seed + 1421, 0.018)
    gray = base.mean(axis=2)
    ti = np.clip(gray * 0.16 + 0.46 + phase * 0.10 - edge * 0.08 + needles * 0.09 + micro * 0.035, 0, 1)
    effect = np.stack([
        np.clip(ti + needles * 0.055 + phase * 0.025, 0, 1),
        np.clip(ti + phase * 0.012, 0, 1),
        np.clip(ti + edge * 0.055 + beta * 0.025, 0, 1),
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, None] * blend) + effect * (mask[:, :, None] * blend), 0, 1)
    return np.clip(result + bb[:, :, None] * 0.13 * pm * mask[:, :, None], 0, 1).astype(np.float32)


def spec_titanium_raw(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    alpha = _norm01(multi_scale_noise((h, w), [2, 4, 9, 18], [0.36, 0.30, 0.22, 0.12], seed + 1408))
    beta = _norm01(multi_scale_noise((h, w), [3, 7, 13, 27], [0.34, 0.30, 0.22, 0.14], seed + 1420))
    phase = _norm01(alpha * 0.56 + beta * 0.44)
    edge = np.clip(
        np.abs(np.gradient(phase, axis=0)) * 10.0 +
        np.abs(np.gradient(phase, axis=1)) * 10.0,
        0, 1
    )
    micro = _micro_speckle((h, w), seed + 1421, 0.018)
    M = np.clip(base_m * 0.62 + phase * 36.0 * sm + edge * 32.0 * sm + micro * 22.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(36.0 + phase * 34.0 * sm + edge * 54.0 * sm - micro * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(38.0 + edge * 48.0 * sm + phase * 18.0 * sm, 16, 105).astype(np.float32)
    return M, R, CC


def paint_chromaflair_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    angle = _norm01(
        xn * 0.42 + yn * 0.28 +
        multi_scale_noise((h, w), [10, 22, 48], [0.40, 0.36, 0.24], seed + 1510) * 0.35
    )
    foil = _norm01(
        np.sin((x * 0.52 + y * 0.09) + angle * 4.0) +
        np.sin((x * -0.18 + y * 0.61) + angle * 3.5) * 0.65 +
        np.sin((x * 1.33 - y * 0.21) + seed * 0.01) * 0.25
    )
    dust = _micro_speckle((h, w), seed + 1511, 0.042)
    magenta = np.array([0.86, 0.06, 0.72], dtype=np.float32)
    emerald = np.array([0.06, 0.78, 0.38], dtype=np.float32)
    amber = np.array([0.96, 0.58, 0.10], dtype=np.float32)
    blue = np.array([0.05, 0.30, 0.95], dtype=np.float32)
    w1 = np.clip(1.0 - np.abs(angle - 0.18) * 3.2, 0, 1)
    w2 = np.clip(1.0 - np.abs(angle - 0.48) * 3.0, 0, 1)
    w3 = np.clip(1.0 - np.abs(angle - 0.72) * 3.1, 0, 1)
    w4 = np.clip(1.0 - np.abs(angle - 0.94) * 3.6, 0, 1)
    weights = w1 + w2 + w3 + w4 + 1e-5
    chroma = (
        magenta[None, None, :] * w1[:, :, None] +
        emerald[None, None, :] * w2[:, :, None] +
        amber[None, None, :] * w3[:, :, None] +
        blue[None, None, :] * w4[:, :, None]
    ) / weights[:, :, None]
    pigment = np.clip(chroma * (0.62 + foil[:, :, None] * 0.30) + dust[:, :, None] * chroma * 0.28, 0, 1)
    carrier = np.clip(base * 0.36 + pigment * 0.78, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1 - blend) + carrier * blend + bb[:, :, None] * 0.18 * blend, 0, 1).astype(np.float32)


def spec_chromaflair(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    foil = _norm01(
        multi_scale_noise((h, w), [4, 9, 18, 42], [0.36, 0.30, 0.22, 0.12], seed + 1510)
        + _micro_speckle((h, w), seed + 1511, 0.042) * 0.55
    )
    M = np.clip(176.0 + foil * 72.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + (1 - foil) * 28.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + foil * 16.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_xirallic_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    facet = _norm01(
        np.sin(x * 0.83 + y * 0.21) +
        np.sin(x * -0.36 + y * 0.74) * 0.72 +
        np.sin((x + y) * 1.51) * 0.24 +
        multi_scale_noise((h, w), [2, 5, 11], [0.46, 0.34, 0.20], seed + 1520) * 0.55
    )
    flakes = _micro_speckle((h, w), seed + 1521, 0.060)
    blue_silver = np.array([0.55, 0.70, 0.92], dtype=np.float32)
    champagne = np.array([0.92, 0.78, 0.50], dtype=np.float32)
    crystal_tint = blue_silver[None, None, :] * (0.70 + facet[:, :, None] * 0.18) + champagne[None, None, :] * (facet[:, :, None] * 0.16)
    intercoat = np.clip(base * 0.76 + base.mean(axis=2, keepdims=True) * 0.13, 0, 1)
    effect = np.clip(intercoat + crystal_tint * flakes[:, :, None] * 0.34 + (facet[:, :, None] - 0.5) * 0.055, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.16 * blend, 0, 1).astype(np.float32)


def spec_xirallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    facet = _norm01(multi_scale_noise((h, w), [2, 5, 11, 23], [0.40, 0.30, 0.20, 0.10], seed + 1520))
    flakes = _micro_speckle((h, w), seed + 1521, 0.060)
    crystal = np.clip(facet * 0.46 + flakes * 0.72, 0, 1)
    M = np.clip(116.0 + crystal * 126.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + (1 - flakes) * 44.0 * sm + facet * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + crystal * 28.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC
