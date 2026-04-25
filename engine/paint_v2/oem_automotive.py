# -*- coding: utf-8 -*-
"""
OEM AUTOMOTIVE -- 9 bases, each with unique paint_fn + spec_fn
Factory and service vehicle finishes with distinct physics.

Techniques (all different):
  ambulance_white   - Retro-reflective microprismatic bead simulation
  dealer_pearl      - Tri-coat pearl: base + mica mid + clearcoat interference
  factory_basecoat  - Electrostatic spray deposition bell-cup pattern
  fire_engine       - High-chroma cadmium pigment saturation model
  fleet_white       - Crosslinked polyurethane uniform cure model
  police_black      - Soot-particle carbon black absorption model
  school_bus        - Chrome yellow lead-free pigment with UV stabilizer
  showroom_clear    - Multi-layer clearcoat Fresnel reflection stack
  taxi_yellow       - Photodegradation UV yellowing + wear model
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


# ==================================================================
# AMBULANCE WHITE - Retro-reflective microprismatic bead simulation
# High-vis white with embedded glass beads that retro-reflect light.
# Each bead acts as a tiny corner reflector, creating localized
# brightness hotspots distributed across the surface.
# ==================================================================

def paint_ambulance_white_v2(paint, shape, mask, seed, pm, bb):
    """Ambulance high-vis white with microprismatic retro-reflective glass bead simulation."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 600)

    # Push base toward bright white (keep 0-1)
    gray = base.mean(axis=2)
    white_base = np.clip(gray * 0.15 + 0.82, 0, 1)

    # Microprismatic glass bead distribution (sparse bright spots)
    bead_field = rng.rand(h, w).astype(np.float32)
    bead_mask = (bead_field > 0.92).astype(np.float32)  # ~8% coverage
    # Bead retro-reflection intensity (Gaussian falloff from bead center)
    bead_blur = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 601)
    retro_boost = (bead_mask * 0.06 + bead_blur * 0.02).astype(np.float32)

    effect_r = np.clip(white_base + retro_boost + 0.01, 0, 1)
    effect_g = np.clip(white_base + retro_boost, 0, 1)
    effect_b = np.clip(white_base + retro_boost - 0.005, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_ambulance_white(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 600)
    bead = (rng.rand(h, w) > 0.92).astype(np.float32)
    # White paint: zero metallic, low roughness, retro-reflective beads add specular
    M = np.clip(5.0 + bead * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + bead * 4.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + bead * 3.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# DEALER PEARL - Tri-coat pearl with mica interference
# Three distinct layers: colored basecoat, mica flake mid-coat with
# thin-film interference, and deep clearcoat. The mica layer creates
# angle-dependent color travel (different from Lamborghini's approach
# which uses OPD formula — this uses discrete layer stacking).
# ==================================================================

def paint_dealer_pearl_v2(paint, shape, mask, seed, pm, bb):
    """Dealer tri-coat pearl: basecoat + mica flake interference + deep clearcoat."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Layer 1: Colored basecoat (preserve hue, push saturation)
    gray = base.mean(axis=2, keepdims=True)
    basecoat = base * 0.7 + gray * 0.3  # reduce saturation slightly

    # Layer 2: Mica flake interference
    mica_orient = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 611)
    mica_density = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 612)
    # Interference shift — mica flakes at different orientations shift color
    shift_amount = mica_orient * 0.08 * mica_density
    pearl_r = basecoat[:,:,0] + shift_amount * 1.2
    pearl_g = basecoat[:,:,1] + shift_amount * 0.6
    pearl_b = basecoat[:,:,2] - shift_amount * 0.3

    # Layer 3: Deep clearcoat adds depth (darken slightly in shadows)
    depth = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 613)
    depth_mod = 0.92 + depth * 0.08
    effect = np.stack([
        np.clip(pearl_r * depth_mod, 0, 1),
        np.clip(pearl_g * depth_mod, 0, 1),
        np.clip(pearl_b * depth_mod, 0, 1)
    ], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.22 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_dealer_pearl(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    mica = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 611)
    depth = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 613)
    M = np.clip(80.0 + mica * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + depth * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(18.0 + depth * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FACTORY BASECOAT - Electrostatic bell-cup spray deposition
# Factory robots use high-speed bell-cup atomizers with electrostatic
# charge. Creates characteristic radial spray overlap patterns where
# adjacent passes create slight thickness variation.
# ==================================================================

def paint_factory_basecoat_v2(paint, shape, mask, seed, pm, bb):
    """Factory electrostatic bell-cup spray deposition with radial overlap bands."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Bell-cup spray pattern: radial overlap bands (horizontal robot passes)
    pass_spacing = 80.0  # pixels between spray passes
    pass_phase = np.mod(y, pass_spacing) / pass_spacing
    # Gaussian overlap profile per pass
    overlap = np.exp(-((pass_phase - 0.5) ** 2) / (2.0 * 0.12 ** 2))
    overlap = overlap * 0.04 + 0.96  # subtle 4% thickness variation

    # Electrostatic wraparound (paint deposits slightly more on edges)
    edge_charge = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 621)
    charge_boost = edge_charge * 0.015

    # Standard metallic basecoat color (0-1)
    gray = base.mean(axis=2)
    bc = np.clip(gray * 0.4 + 0.35, 0, 1)
    effect_r = np.clip(bc * overlap + charge_boost, 0, 1)
    effect_g = np.clip(bc * overlap + charge_boost, 0, 1)
    effect_b = np.clip(bc * overlap + charge_boost - 0.005, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_factory_basecoat(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    pass_phase = np.mod(y, 80.0) / 80.0
    overlap = np.exp(-((pass_phase - 0.5) ** 2) / (2.0 * 0.12 ** 2))
    # Factory basecoat: moderate metallic, controlled roughness
    M = np.clip(110.0 + overlap * 30.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(12.0 + overlap * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + overlap * 4.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FIRE ENGINE - High-chroma cadmium pigment saturation
# Fire engine red uses high-chroma pigments (historically cadmium red)
# with extremely high color saturation. Models pigment particle
# scattering where red wavelengths scatter forward, others absorb.
# ==================================================================

def paint_fire_engine_v2(paint, shape, mask, seed, pm, bb):
    """Fire engine red: high-chroma cadmium pigment with forward scattering model."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Pigment particle scatter map (cadmium red particles vary in size)
    scatter = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 631)
    # Forward scattering: larger particles scatter more red
    red_scatter = 0.88 + scatter * 0.10  # strong red
    # Absorption: green and blue heavily absorbed by pigment
    green_absorb = np.exp(-3.5 * (0.8 + scatter * 0.4))  # near zero
    blue_absorb = np.exp(-4.2 * (0.8 + scatter * 0.4))   # even less

    # High-gloss wet look from heavy clearcoat
    gloss = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 632)
    gloss_boost = gloss * 0.03

    effect = np.stack([
        np.clip(red_scatter + gloss_boost, 0, 1),
        np.clip(green_absorb + gloss_boost * 0.3, 0, 1),
        np.clip(blue_absorb + gloss_boost * 0.2, 0, 1)
    ], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_fire_engine(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    scatter = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 631)
    # Fire engine: no metallic (solid pigment), very low roughness (high gloss)
    M = np.clip(8.0 + scatter * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(3.0 + scatter * 6.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(18.0 + scatter * 5.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FLEET WHITE - Crosslinked polyurethane uniform cure
# Fleet/commercial white is about uniform durability, not aesthetics.
# Polyurethane crosslink density varies with cure temperature,
# creating micro-regions of slightly different hardness/sheen.
# ==================================================================

def paint_fleet_white_v2(paint, shape, mask, seed, pm, bb):
    """Fleet white crosslinked polyurethane with cure-temperature sheen variation."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Crosslink density map (cure temperature variation across oven)
    crosslink = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.35, 0.35], seed + 641)
    # Higher crosslink = slightly glossier, lower = slightly chalky
    sheen_var = crosslink * 0.015

    # Fleet white: bright but not brilliant (0-1)
    gray = base.mean(axis=2)
    white_flat = np.clip(gray * 0.1 + 0.78, 0, 1)
    effect_r = np.clip(white_flat + sheen_var + 0.01, 0, 1)
    effect_g = np.clip(white_flat + sheen_var + 0.005, 0, 1)
    effect_b = np.clip(white_flat + sheen_var - 0.01, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_fleet_white(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    crosslink = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.35, 0.35], seed + 641)
    # Fleet white: zero metallic, moderate roughness (not showroom gloss)
    M = np.clip(2.0 + crosslink * 4.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + crosslink * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + crosslink * 4.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# POLICE BLACK - Carbon black pigment absorption model
# Police interceptor black uses carbon black nanoparticles that
# absorb across all visible wavelengths. Particle size distribution
# creates subtle warm/cool shift. Stealth finish = subdued gloss.
# ==================================================================

def paint_police_black_v2(paint, shape, mask, seed, pm, bb):
    """Police interceptor carbon black nanoparticle absorption with stealth gloss."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Carbon black particle size distribution
    particle_size = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 651)
    # Larger particles = slightly warmer (brown-black), smaller = cooler (blue-black)
    warm_cool = particle_size * 0.02

    # Near-total absorption across all wavelengths
    absorb_base = 0.04  # very dark
    # Subtle variation from particle density
    density_var = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 652)
    absorb_mod = density_var * 0.015

    effect_r = np.clip(absorb_base + absorb_mod + warm_cool, 0, 1)
    effect_g = np.clip(absorb_base + absorb_mod, 0, 1)
    effect_b = np.clip(absorb_base + absorb_mod - warm_cool * 0.5, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_police_black(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    particle = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 651)
    # Police black: zero metallic, moderate roughness (subdued stealth gloss)
    M = np.clip(3.0 + particle * 6.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(12.0 + particle * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + particle * 4.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# SCHOOL BUS - Chrome yellow pigment with UV stabilizer
# School bus yellow (Federal Standard 13432) uses lead-free chrome
# yellow pigment stabilized with HALS UV absorbers. The UV stabilizer
# creates a slight matte haze over the otherwise bright pigment.
# ==================================================================

def paint_school_bus_v2(paint, shape, mask, seed, pm, bb):
    """School bus chrome yellow pigment with HALS UV stabilizer matte haze."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Chrome yellow pigment — highly saturated yellow
    pigment = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 661)
    yellow_r = 0.94 + pigment * 0.04
    yellow_g = 0.72 + pigment * 0.06
    yellow_b = 0.02 + pigment * 0.02

    # HALS UV stabilizer haze (slight surface whitening)
    hals = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 662)
    haze = hals * 0.025  # subtle matte haze

    effect = np.stack([
        np.clip(yellow_r + haze, 0, 1),
        np.clip(yellow_g + haze, 0, 1),
        np.clip(yellow_b + haze * 0.5, 0, 1)
    ], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_school_bus(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    hals = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 662)
    # School bus: no metallic, moderate roughness from UV stabilizer haze
    M = np.clip(4.0 + hals * 6.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + hals * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + hals * 4.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# SHOWROOM CLEAR - Multi-layer clearcoat Fresnel reflection
# Fresh-off-the-lot deep clearcoat with multiple clear layers.
# Each layer boundary creates a Fresnel reflection, stacking to
# produce visible depth and mirror-like wet look.
# ==================================================================

def paint_showroom_clear_v2(paint, shape, mask, seed, pm, bb):
    """Showroom multi-layer clearcoat Fresnel reflection stack with wet-look depth."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Multi-layer Fresnel stack: 3 clear layers, each reflects ~4%
    # Cumulative reflection increases perceived brightness/depth
    n_layers = 3
    fresnel_accum = np.zeros((h, w), dtype=np.float32)
    for i in range(n_layers):
        layer_var = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 671 + i)
        # Fresnel reflectance at normal incidence: R = ((n1-n2)/(n1+n2))^2
        n_clear = 1.50 + layer_var * 0.02  # slight RI variation per layer
        fresnel_r = ((n_clear - 1.0) / (n_clear + 1.0)) ** 2
        fresnel_accum += fresnel_r

    # The clearcoat brightens highlights and adds depth
    depth_color = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 674)
    depth_darken = 0.95 + depth_color * 0.05

    # Enhance base paint color with clearcoat depth
    effect = base * depth_darken[:,:,np.newaxis]
    # Add Fresnel highlight boost
    effect = np.clip(effect + fresnel_accum[:,:,np.newaxis] * 0.15, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_showroom_clear(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    depth = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 674)
    # Showroom: preserves base metallic, ultra-low roughness (mirror clear)
    M = np.clip(base_m * 0.8 + depth * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(2.0 + depth * 4.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(22.0 + depth * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# TAXI YELLOW - Photodegradation UV yellowing + wear model
# Taxi yellow after years of UV exposure. UV photons break polymer
# bonds creating chromophores (yellowing) and surface chalking.
# Models exponential UV dose accumulation + mechanical wear zones.
# ==================================================================

def paint_taxi_yellow_v2(paint, shape, mask, seed, pm, bb):
    """Taxi yellow with UV photodegradation yellowing, chalking, and wear zones."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # UV dose map (0-1, top surfaces get more UV = more degradation)
    uv_dose = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.35, 0.35], seed + 681)
    chromophore = 1.0 - np.exp(-2.5 * np.clip(uv_dose, 0, 1))

    # Base taxi yellow (already yellowed from new)
    taxi_r = 0.88 + chromophore * 0.06  # gets more orange with UV
    taxi_g = 0.68 - chromophore * 0.08  # green drops = more orange
    taxi_b = 0.04 - chromophore * 0.02  # blue drops further

    # Mechanical wear zones (door handles, edges, high-contact areas)
    wear = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 682)
    # Chalking from UV (surface becomes matte/powdery)
    chalk = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 683)
    chalk_whiten = chalk * chromophore * 0.06

    effect = np.stack([
        np.clip(taxi_r + chalk_whiten, 0, 1),
        np.clip(taxi_g + chalk_whiten, 0, 1),
        np.clip(taxi_b + chalk_whiten, 0, 1)
    ], axis=-1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_taxi_yellow(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    uv = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.35, 0.35], seed + 681)
    chalk = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 683)
    chromophore = 1.0 - np.exp(-2.5 * np.clip(uv, 0, 1))
    # Worn taxi: zero metallic, high roughness from chalking
    M = np.clip(3.0 + chalk * 5.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(25.0 + chromophore * 40.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + (1.0 - chromophore) * 8.0, 16, 255).astype(np.float32)
    return M, R, CC
