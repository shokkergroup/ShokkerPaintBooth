# -*- coding: utf-8 -*-
"""
METALLIC STANDARD -- 14 bases, each with unique paint_fn + spec_fn
Standard metallic and pearl finishes with distinct flake/pigment physics.

Techniques (all different):
  candy_apple          - Beer-Lambert double-pass candy absorption
  champagne_metallic   - Oriented gold-mica flake with warm bias
  metal_flake_base     - Large aluminum flake Voronoi scatter
  original_metal_flake - 1960s mega-flake prismatic refraction
  champagne_flake      - Gold-coated aluminum flake specular map
  fine_silver_flake    - Micro-diamond particle Mie scattering
  blue_ice_flake       - Frozen crystal dendritic growth pattern
  bronze_flake         - Copper-tin alloy oxidation gradient
  gunmetal_flake       - Chameleon-shift multi-angle interference
  green_flake          - Dichroic glass flake color-split
  fire_flake           - Thermal gradient blackbody emission color
  midnight_pearl       - Deep-base mica with Rayleigh blue scatter
  pearlescent_white    - Multi-mica rainbow interference stack
  pewter               - Tin-lead alloy grain boundary diffusion
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# ==================================================================
# CANDY APPLE - Beer-Lambert double-pass candy absorption
# ==================================================================
def paint_candy_apple_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    reflect = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.4, 0.3], seed + 701)
    thickness = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 702)
    thick = 0.7 + thickness * 0.6
    # Beer-Lambert: red passes, green/blue absorbed (double pass)
    t_r = np.exp(-0.2 * thick * 2.0)
    t_g = np.exp(-2.5 * thick * 2.0)
    t_b = np.exp(-3.8 * thick * 2.0)
    base_r = 0.65 + reflect * 0.3
    effect = np.stack([
        np.clip(base_r * t_r, 0, 1),
        np.clip(base_r * t_g * 0.5, 0, 1),
        np.clip(base_r * t_b * 0.3, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.40 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_candy_apple(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    thick = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 702)
    M = np.clip(130.0 + thick * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(4.0 + thick * 7.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + thick * 6.0, 0, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# CHAMPAGNE METALLIC - Oriented gold-mica flake with warm bias
# ==================================================================
def paint_champagne_metallic_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Gold mica flake orientation (spray-aligned)
    orient = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 711)
    spray = np.sin(y * 0.015 + orient * 1.8) * 0.5 + 0.5
    flake_bright = orient * spray
    gray = base.mean(axis=2)
    champagne = np.clip(gray * 0.25 + 0.50, 0, 1)
    effect_r = np.clip(champagne + flake_bright * 0.08 + 0.06, 0, 1)
    effect_g = np.clip(champagne + flake_bright * 0.06 + 0.03, 0, 1)
    effect_b = np.clip(champagne + flake_bright * 0.03 - 0.02, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.38 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_champagne_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    orient = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 711)
    M = np.clip(150.0 + orient * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + orient * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(14.0 + orient * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# METAL FLAKE BASE - Large aluminum flake Voronoi scatter
# ==================================================================
def paint_metal_flake_base_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 720)
    # Voronoi-like flake centers (sparse large flakes)
    n_flakes = 800
    cy = rng.randint(0, h, n_flakes)
    cx = rng.randint(0, w, n_flakes)
    flake_map = np.zeros((h, w), dtype=np.float32)
    for i in range(n_flakes):
        r = rng.randint(3, 8)
        y0, y1 = max(0, cy[i]-r), min(h, cy[i]+r)
        x0, x1 = max(0, cx[i]-r), min(w, cx[i]+r)
        brightness = rng.rand() * 0.15 + 0.05
        flake_map[y0:y1, x0:x1] += brightness
    flake_map = np.clip(flake_map, 0, 0.2)
    gray = base.mean(axis=2)
    metal = np.clip(gray * 0.3 + 0.45, 0, 1)
    effect = np.clip(np.stack([metal + flake_map]*3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.42 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_metal_flake_base(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 720)
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.4, 0.3], seed + 721)
    M = np.clip(190.0 + flake * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + flake * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(12.0 + flake * 5.0, 0, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# ORIGINAL METAL FLAKE - 1960s mega-flake prismatic refraction
# ==================================================================
def paint_original_metal_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    rng = np.random.RandomState(seed + 730)
    # Huge flakes (~20px each) with prismatic color from thickness variation
    flake_coarse = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 731)
    # Prismatic refraction: flake thickness -> color split
    prism_phase = flake_coarse * np.pi * 3.0
    prism_r = np.clip(0.5 + 0.3 * np.cos(prism_phase), 0, 1)
    prism_g = np.clip(0.5 + 0.3 * np.cos(prism_phase - 2.094), 0, 1)
    prism_b = np.clip(0.5 + 0.3 * np.cos(prism_phase + 2.094), 0, 1)
    # Sparse mega-flake visibility
    flake_mask = (flake_coarse > 0.45).astype(np.float32) * 0.12
    gray = base.mean(axis=2)
    metal = np.clip(gray * 0.3 + 0.42, 0, 1)
    effect = np.stack([
        np.clip(metal + flake_mask * prism_r, 0, 1),
        np.clip(metal + flake_mask * prism_g, 0, 1),
        np.clip(metal + flake_mask * prism_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.44 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_original_metal_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 731)
    M = np.clip(200.0 + flake * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + flake * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(10.0 + flake * 6.0, 0, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# CHAMPAGNE FLAKE - Gold-coated aluminum flake specular map
# ==================================================================
def paint_champagne_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Gold-coated flakes: high specular at certain orientations
    flake_orient = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 741)
    specular_hit = np.clip((flake_orient - 0.6) * 5.0, 0, 1) * 0.10
    gold_base = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 742)
    gray = base.mean(axis=2)
    warm = np.clip(gray * 0.2 + 0.52, 0, 1)
    effect = np.stack([
        np.clip(warm + gold_base * 0.04 + specular_hit + 0.05, 0, 1),
        np.clip(warm + gold_base * 0.03 + specular_hit * 0.8 + 0.02, 0, 1),
        np.clip(warm + gold_base * 0.01 + specular_hit * 0.3 - 0.03, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.38 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_champagne_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 741)
    M = np.clip(165.0 + flake * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(7.0 + flake * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(14.0 + flake * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FINE SILVER FLAKE - Micro-diamond particle Mie scattering
# ==================================================================
def paint_fine_silver_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Mie scattering: particle size ~ wavelength, creates forward scatter halo
    particle = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 751)
    # Mie efficiency: peaks when size ~ wavelength, oscillates
    mie_q = 2.0 + 1.5 * np.cos(particle * 12.0)  # oscillating scatter efficiency
    scatter_intensity = np.clip(mie_q / 4.0, 0, 1) * 0.08
    # Silver base
    gray = base.mean(axis=2)
    silver = np.clip(gray * 0.2 + 0.58, 0, 1)
    effect = np.stack([
        np.clip(silver + scatter_intensity, 0, 1),
        np.clip(silver + scatter_intensity, 0, 1),
        np.clip(silver + scatter_intensity + 0.01, 0, 1)  # slight cool bias
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.40 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_fine_silver_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    particle = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 751)
    M = np.clip(185.0 + particle * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(4.0 + particle * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(15.0 + particle * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# BLUE ICE FLAKE - Frozen crystal dendritic growth pattern
# ==================================================================
def paint_blue_ice_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Dendritic crystal growth: 6-fold symmetry (ice crystal)
    angle = np.arctan2(y - h/2, x - w/2)
    radius = np.sqrt((y - h/2)**2 + (x - w/2)**2) / max(h, w)
    hex_sym = np.cos(6.0 * angle) * 0.5 + 0.5  # 6-fold
    crystal = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 761)
    dendrite = hex_sym * crystal * 0.06
    # Ice blue base
    ice_r = 0.52 + crystal * 0.04
    ice_g = 0.62 + crystal * 0.05
    ice_b = 0.78 + crystal * 0.06
    # Flake sparkle
    flake = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 762)
    sparkle = np.clip((flake - 0.7) * 4.0, 0, 1) * 0.06
    effect = np.stack([
        np.clip(ice_r + dendrite + sparkle, 0, 1),
        np.clip(ice_g + dendrite + sparkle, 0, 1),
        np.clip(ice_b + dendrite + sparkle * 1.5, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.36 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_blue_ice_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    crystal = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 761)
    M = np.clip(140.0 + crystal * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + crystal * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + crystal * 5.0, 0, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# BRONZE FLAKE - Copper-tin alloy oxidation gradient
# ==================================================================
def paint_bronze_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Bronze = copper-tin alloy; oxidation creates patina gradient
    alloy_ratio = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 771)
    # High copper = warmer red-brown, high tin = cooler yellow
    oxide = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 772)
    oxide_depth = np.clip(oxide, 0, 1) * 0.06
    bronze_r = 0.55 + alloy_ratio * 0.12 - oxide_depth
    bronze_g = 0.38 + alloy_ratio * 0.06 - oxide_depth * 0.8
    bronze_b = 0.15 + alloy_ratio * 0.03 + oxide_depth * 0.3  # patina green-blue
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 773)
    sparkle = flake * 0.05
    effect = np.stack([
        np.clip(bronze_r + sparkle, 0, 1),
        np.clip(bronze_g + sparkle * 0.7, 0, 1),
        np.clip(bronze_b + sparkle * 0.3, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.36 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_bronze_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    alloy = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 771)
    oxide = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], seed + 772)
    M = np.clip(160.0 + alloy * 50.0 * sm - oxide * 30.0, 0, 255).astype(np.float32)
    R = np.clip(10.0 + oxide * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(10.0 + (1.0 - oxide) * 6.0, 0, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# GUNMETAL FLAKE - Chameleon-shift multi-angle interference
# ==================================================================
def paint_gunmetal_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Chameleon flakes: multi-layer thin film with angle-dependent color
    angle_map = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 781)
    # Different viewing angles shift between purple-green-gold
    phase = angle_map * np.pi * 2.0
    shift_r = 0.25 + 0.06 * np.cos(phase)
    shift_g = 0.27 + 0.06 * np.cos(phase - 2.094)
    shift_b = 0.30 + 0.06 * np.cos(phase + 2.094)
    # Gunmetal dark base
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 782)
    sparkle = flake * 0.04
    effect = np.stack([
        np.clip(shift_r + sparkle, 0, 1),
        np.clip(shift_g + sparkle, 0, 1),
        np.clip(shift_b + sparkle, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_gunmetal_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    angle = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 781)
    M = np.clip(145.0 + angle * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + angle * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(14.0 + angle * 5.0, 0, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# GREEN FLAKE - Dichroic glass flake color-split
# ==================================================================
def paint_green_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Dichroic flakes: transmit green, reflect complementary magenta
    flake_orient = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 791)
    dichroic_split = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 792)
    # Transmitted green vs reflected magenta based on flake angle
    green_dom = np.clip(0.5 + dichroic_split * 0.4, 0, 1)
    magenta_bleed = np.clip(0.5 - dichroic_split * 0.3, 0, 0.5) * 0.15
    sparkle = np.clip((flake_orient - 0.65) * 4.0, 0, 1) * 0.08
    effect = np.stack([
        np.clip(0.12 + magenta_bleed + sparkle, 0, 1),
        np.clip(0.35 + green_dom * 0.25 + sparkle, 0, 1),
        np.clip(0.10 + magenta_bleed * 0.6 + sparkle * 0.5, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.36 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_green_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 791)
    M = np.clip(130.0 + flake * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(7.0 + flake * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(14.0 + flake * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FIRE FLAKE - Thermal gradient blackbody emission color
# ==================================================================
def paint_fire_flake_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Blackbody radiation: temperature maps to color (cool=red, hot=yellow-white)
    temp_map = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 801)
    temp = np.clip(temp_map, 0, 1)  # 0=cool ember, 1=hot flame
    # Simplified Planck: R peaks first, G follows, B last
    fire_r = np.clip(0.6 + temp * 0.38, 0, 1)
    fire_g = np.clip(temp * 0.55 - 0.05, 0, 1)
    fire_b = np.clip(temp * 0.15 - 0.08, 0, 1)
    # Ember flake sparkle
    flake = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 802)
    ember = np.clip((flake - 0.7) * 4.0, 0, 1) * 0.08
    effect = np.stack([
        np.clip(fire_r + ember, 0, 1),
        np.clip(fire_g + ember * 0.6, 0, 1),
        np.clip(fire_b + ember * 0.2, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.40 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_fire_flake(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    temp = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 801)
    M = np.clip(140.0 + temp * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + temp * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(12.0 + temp * 6.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# MIDNIGHT PEARL - Deep-base mica with Rayleigh blue scatter
# ==================================================================
def paint_midnight_pearl_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Rayleigh scatter: intensity ~ 1/lambda^4, so blue scatters most
    # In deep black base, scattered blue light creates subtle blue pearl
    depth = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 811)
    mica = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 812)
    # Rayleigh: blue scatters 16x more than red (ratio of (700/400)^4)
    scatter_r = mica * 0.005  # minimal red scatter
    scatter_g = mica * 0.012  # some green scatter
    scatter_b = mica * 0.035  # strong blue scatter
    # Deep black base
    dark = 0.03 + depth * 0.02
    effect = np.stack([
        np.clip(dark + scatter_r, 0, 1),
        np.clip(dark + scatter_g, 0, 1),
        np.clip(dark + scatter_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_midnight_pearl(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    mica = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 812)
    M = np.clip(70.0 + mica * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + mica * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + mica * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PEARLESCENT WHITE - Multi-mica rainbow interference stack
# ==================================================================
def paint_pearlescent_white_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Multi-mica layers: each mica type has different thickness -> different color
    mica1 = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 821)
    mica2 = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 822)
    mica3 = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 823)
    # Each mica shifts a different color channel
    rainbow_r = mica1 * 0.04
    rainbow_g = mica2 * 0.04
    rainbow_b = mica3 * 0.04
    # Bright white base
    gray = base.mean(axis=2)
    white = np.clip(gray * 0.1 + 0.85, 0, 1)
    effect = np.stack([
        np.clip(white + rainbow_r, 0, 1),
        np.clip(white + rainbow_g, 0, 1),
        np.clip(white + rainbow_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pearlescent_white(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    mica = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.35, 0.35], seed + 821)
    M = np.clip(85.0 + mica * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + mica * 7.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + mica * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PEWTER - Tin-lead alloy grain boundary diffusion
# ==================================================================
def paint_pewter_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Grain boundaries: Voronoi-approximated crystal grains
    # Grain interiors are smooth, boundaries are darker (diffusion channels)
    grain = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 831)
    # Grain boundary detection via gradient magnitude
    gy = np.gradient(grain, axis=0)
    gx = np.gradient(grain, axis=1)
    boundary = np.sqrt(gy**2 + gx**2)
    boundary = np.clip(boundary / (boundary.max() + 1e-8), 0, 1)
    # Pewter color: muted warm grey
    gray = base.mean(axis=2)
    pewter_base = np.clip(gray * 0.2 + 0.42, 0, 1)
    # Boundaries darken, interiors have subtle color travel
    color_travel = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 832)
    effect_r = np.clip(pewter_base - boundary * 0.04 + color_travel * 0.015, 0, 1)
    effect_g = np.clip(pewter_base - boundary * 0.04 + color_travel * 0.010, 0, 1)
    effect_b = np.clip(pewter_base - boundary * 0.04 + color_travel * 0.005, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.32 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pewter(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    grain = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 831)
    gy = np.gradient(grain, axis=0)
    gx = np.gradient(grain, axis=1)
    boundary = np.sqrt(gy**2 + gx**2)
    boundary = np.clip(boundary / (boundary.max() + 1e-8), 0, 1)
    # Pewter: moderate metallic, boundaries rougher
    M = np.clip(120.0 + grain * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(14.0 + boundary * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(10.0 + (1.0 - boundary) * 6.0, 0, 255).astype(np.float32)
    return M, R, CC
