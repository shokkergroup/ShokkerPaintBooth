# -*- coding: utf-8 -*-
"""
METALLIC & FLAKE -- 9 bases, each with unique paint_fn + spec_fn
Metallic and specialty flake finishes.

Techniques (all different):
  copper_metallic    - Drude model free-electron plasma reflection
  diamond_coat       - Snell's law total internal reflection sparkle
  electric_ice       - Lichtenberg figure dielectric breakdown pattern
  gunmetal_metallic  - Beckmann micro-facet BRDF distribution
  standard_metallic  - Kubelka-Munk two-flux scattering model
  pearl_classic      - Nacre-structure layered aragonite interference
  plasma_metal       - Ion bombardment surface energy modification
  rose_gold_metallic - Au-Cu alloy d-band electronic color model
  satin_gold         - Anisotropic Ward BRDF tangent-direction sheen
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# ==================================================================
# COPPER METALLIC - Drude model free-electron plasma reflection
# ==================================================================
def paint_copper_metallic_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Drude: reflectance depends on plasma frequency vs light frequency
    # Copper plasma freq is in UV; reflects red/orange, absorbs blue
    electron_density = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 900)
    plasma_var = 0.85 + electron_density * 0.3
    # Reflectance: R ~ 1 - (w/wp)^2 for w < wp
    refl_r = np.clip(plasma_var * 0.95, 0, 1)   # red: well below plasma freq
    refl_g = np.clip(plasma_var * 0.55, 0, 1)   # green: closer to plasma freq
    refl_b = np.clip(plasma_var * 0.20, 0, 1)   # blue: near/above plasma freq
    # Surface grain from polycrystalline structure
    grain = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 901)
    grain_mod = grain * 0.03
    effect = np.stack([
        np.clip(refl_r + grain_mod, 0, 1),
        np.clip(refl_g + grain_mod * 0.7, 0, 1),
        np.clip(refl_b + grain_mod * 0.3, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.38 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_copper_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    ed = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 900)
    M = np.clip(200.0 + ed * 45.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + ed * 10.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(12.0 + ed * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# DIAMOND COAT - Snell's law total internal reflection sparkle
# ==================================================================
def paint_diamond_coat_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Diamond n=2.42, critical angle for TIR = arcsin(1/2.42) = 24.4deg
    # Flakes at angle > critical angle trap light via TIR -> bright sparkle
    flake_angle = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 911)
    critical = np.arcsin(1.0 / 2.42)  # ~0.426 rad
    # Normalized angle: flakes randomly oriented
    angle_norm = flake_angle * (np.pi / 2.0)
    tir_mask = (angle_norm > critical).astype(np.float32)
    # TIR sparkle: brilliant white flashes
    sparkle = tir_mask * 0.15
    # Base: bright clear with prismatic dispersion
    dispersion = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 912)
    prism = dispersion * np.pi * 2.0
    gray = base.mean(axis=2)
    bright = np.clip(gray * 0.2 + 0.65, 0, 1)
    effect = np.stack([
        np.clip(bright + sparkle + np.cos(prism) * 0.02, 0, 1),
        np.clip(bright + sparkle + np.cos(prism - 2.094) * 0.02, 0, 1),
        np.clip(bright + sparkle + np.cos(prism + 2.094) * 0.02, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.44 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_diamond_coat(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    flake = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 911)
    M = np.clip(170.0 + flake * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(3.0 + flake * 6.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(20.0 + flake * 6.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# ELECTRIC ICE - Lichtenberg figure dielectric breakdown pattern
# ==================================================================
def paint_electric_ice_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Lichtenberg: fractal branching from dielectric breakdown
    # Approximate with multi-octave noise thresholded at different levels
    n1 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 921)
    n2 = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 922)
    n3 = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 923)
    # Branch-like structures from gradient ridges
    gy1 = np.abs(np.gradient(n1, axis=0))
    gx1 = np.abs(np.gradient(n1, axis=1))
    ridge = np.clip((gy1 + gx1) * 8.0, 0, 1)
    # Fine branches
    gy2 = np.abs(np.gradient(n2, axis=0))
    gx2 = np.abs(np.gradient(n2, axis=1))
    fine_branch = np.clip((gy2 + gx2) * 12.0, 0, 1) * 0.5
    lightning = np.clip(ridge + fine_branch, 0, 1) * 0.12
    # Ice blue base
    ice_base = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 924)
    effect = np.stack([
        np.clip(0.45 + ice_base * 0.04 + lightning * 0.8, 0, 1),
        np.clip(0.55 + ice_base * 0.05 + lightning, 0, 1),
        np.clip(0.75 + ice_base * 0.06 + lightning * 1.2, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.36 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_electric_ice(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    n1 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 921)
    ridge = np.clip((np.abs(np.gradient(n1, axis=0)) + np.abs(np.gradient(n1, axis=1))) * 8.0, 0, 1)
    M = np.clip(120.0 + ridge * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + ridge * 10.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(16.0 + ridge * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# GUNMETAL METALLIC - Beckmann micro-facet BRDF distribution
# ==================================================================
def paint_gunmetal_metallic_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Beckmann distribution: D(h) = exp(-tan^2(theta)/m^2) / (pi*m^2*cos^4(theta))
    # m = surface roughness parameter
    surface_slope = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 931)
    m_rough = 0.25  # gunmetal roughness
    theta = surface_slope * (np.pi / 4.0)  # slope angle
    cos_t = np.cos(theta)
    tan_t = np.tan(theta)
    beckmann = np.exp(-(tan_t**2) / (m_rough**2)) / (np.pi * m_rough**2 * cos_t**4 + 1e-8)
    beckmann = np.clip(beckmann / (beckmann.max() + 1e-8), 0, 1)
    # Dark gunmetal base
    gray = base.mean(axis=2)
    gun_base = np.clip(gray * 0.15 + 0.22, 0, 1)
    specular = beckmann * 0.08
    effect = np.stack([np.clip(gun_base + specular, 0, 1)] * 3, axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_gunmetal_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    slope = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 931)
    M = np.clip(160.0 + slope * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(12.0 + slope * 15.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(10.0 + slope * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# STANDARD METALLIC - Kubelka-Munk two-flux scattering
# ==================================================================
def paint_standard_metallic_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Kubelka-Munk: two opposing light fluxes (forward + backward)
    # R_inf = 1 + K/S - sqrt((K/S)^2 + 2*K/S)  where K=absorption, S=scatter
    scatter = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 941)
    absorb = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 942)
    K = 0.3 + absorb * 0.3   # absorption coefficient
    S = 0.8 + scatter * 0.4  # scattering coefficient
    KS = K / (S + 1e-8)
    R_inf = 1.0 + KS - np.sqrt(KS**2 + 2.0 * KS + 1e-8)
    R_inf = np.clip(R_inf, 0, 1)
    gray = base.mean(axis=2)
    metal_color = np.clip(gray * 0.3 + 0.35, 0, 1)
    reflectance = metal_color * (1.0 - R_inf) + R_inf * 0.6
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 943)
    effect = np.clip(np.stack([reflectance + flake * 0.04] * 3, axis=-1), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_standard_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    scatter = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 941)
    M = np.clip(155.0 + scatter * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(10.0 + scatter * 12.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(12.0 + scatter * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PEARL CLASSIC - Nacre aragonite layered interference
# ==================================================================
def paint_pearl_classic_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Nacre: alternating aragonite/protein layers create iridescence
    layer_thick = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 951)
    # Constructive interference depends on layer thickness
    phase = layer_thick * np.pi * 4.0
    irid_r = np.clip(0.5 + 0.08 * np.cos(phase), 0, 1)
    irid_g = np.clip(0.5 + 0.08 * np.cos(phase - 1.5), 0, 1)
    irid_b = np.clip(0.5 + 0.08 * np.cos(phase + 1.5), 0, 1)
    # Soft pearl base
    gray = base.mean(axis=2)
    pearl = np.clip(gray * 0.2 + 0.62, 0, 1)
    effect = np.stack([
        np.clip(pearl * irid_r + 0.02, 0, 1),
        np.clip(pearl * irid_g + 0.01, 0, 1),
        np.clip(pearl * irid_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.36 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_pearl_classic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    layer = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 951)
    M = np.clip(90.0 + layer * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + layer * 8.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(16.0 + layer * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PLASMA METAL - Ion bombardment surface energy modification
# ==================================================================
def paint_plasma_metal_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Plasma treatment: ion bombardment creates localized surface energy zones
    # High energy zones = more wettable = smoother coating
    # Low energy zones = beading = textured
    ion_dose = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 961)
    # Surface energy gradient
    energy = np.clip(ion_dose, 0, 1)
    # Color: iridescent from oxidation layers formed during plasma treatment
    oxide_phase = energy * np.pi * 3.0
    irid_r = 0.38 + 0.10 * np.cos(oxide_phase)
    irid_g = 0.42 + 0.10 * np.cos(oxide_phase - 1.8)
    irid_b = 0.50 + 0.10 * np.cos(oxide_phase + 1.8)
    # Texture roughness inversely proportional to surface energy
    tex = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 962)
    texture = tex * (1.0 - energy) * 0.04
    effect = np.stack([
        np.clip(irid_r + texture, 0, 1),
        np.clip(irid_g + texture, 0, 1),
        np.clip(irid_b + texture, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.34 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_plasma_metal(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    ion = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 961)
    M = np.clip(150.0 + ion * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + (1.0 - ion) * 18.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(14.0 + ion * 6.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# ROSE GOLD METALLIC - Au-Cu alloy d-band electronic color
# ==================================================================
def paint_rose_gold_metallic_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Au-Cu alloy: d-band transitions absorb blue/green, reflect red/yellow
    # Cu fraction varies -> more Cu = pinker, more Au = yellower
    cu_fraction = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 971)
    cu = 0.4 + cu_fraction * 0.3  # 40-70% copper range
    # d-band absorption edge shifts with alloy composition
    rose_r = np.clip(0.72 + cu * 0.15, 0, 1)   # strong red from both Au and Cu
    rose_g = np.clip(0.48 - cu * 0.08, 0, 1)    # green absorbed by d-band
    rose_b = np.clip(0.42 - cu * 0.12, 0, 1)    # blue strongly absorbed
    # Flake sparkle
    flake = multi_scale_noise((h, w), [1, 2, 4], [0.3, 0.35, 0.35], seed + 972)
    sparkle = flake * 0.04
    effect = np.stack([
        np.clip(rose_r + sparkle, 0, 1),
        np.clip(rose_g + sparkle * 0.6, 0, 1),
        np.clip(rose_b + sparkle * 0.4, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.38 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_rose_gold_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    cu = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 971)
    M = np.clip(185.0 + cu * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + cu * 10.0 * sm, 0, 255).astype(np.float32)
    CC = np.clip(14.0 + cu * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# SATIN GOLD - Anisotropic Ward BRDF tangent-direction sheen
# ==================================================================
def paint_satin_gold_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Ward anisotropic BRDF: different roughness in tangent vs bitangent
    # alpha_x (along brush) << alpha_y (across brush) -> directional sheen
    brush_dir = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 981)
    # Micro-brush lines along horizontal direction
    brush_freq = 0.08
    brush_lines = np.sin(y * brush_freq + brush_dir * 2.0) * 0.5 + 0.5
    # Anisotropic specular: bright along brush direction
    alpha_x, alpha_y = 0.05, 0.25  # strong anisotropy
    aniso_spec = np.exp(-(brush_lines**2) / (2.0 * alpha_x**2)) * 0.08
    # Gold satin base
    gray = base.mean(axis=2)
    gold = np.clip(gray * 0.2 + 0.52, 0, 1)
    effect = np.stack([
        np.clip(gold + aniso_spec + 0.06, 0, 1),
        np.clip(gold + aniso_spec + 0.03, 0, 1),
        np.clip(gold + aniso_spec * 0.3 - 0.04, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_satin_gold(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    brush = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 981)
    M = np.clip(170.0 + brush * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + brush * 12.0 * sm, 0, 255).astype(np.float32)  # satin = moderate rough
    CC = np.clip(8.0 + brush * 5.0, 0, 255).astype(np.float32)
    return M, R, CC
