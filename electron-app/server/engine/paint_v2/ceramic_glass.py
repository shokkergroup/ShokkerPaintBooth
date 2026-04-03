# -*- coding: utf-8 -*-
"""
CERAMIC & GLASS -- 6 bases, each with unique paint_fn + spec_fn
These are non-metallic dielectric materials with very different
optical properties from metals. Glass transmits, ceramic scatters,
enamel has depth, obsidian absorbs.

Techniques (all different):
  ceramic_matte  - Micro-facet scattering model (Oren-Nayar inspired)
  crystal_clear  - Snell's law refraction distortion + caustics
  enamel         - Multi-layer depth simulation (glaze over substrate)
  obsidian       - Volcanic glass: Fresnel + absorption gradient
  porcelain      - Subsurface scattering via blur-chain diffusion
  tempered_glass - Stress birefringence pattern (photoelastic effect)
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d

# ==================================================================
# CERAMIC MATTE - Flat matte ceramic (no micro-facet noise in base)
# ==================================================================

def paint_ceramic_matte_v2(paint, shape, mask, seed, pm, bb):
    """Ceramic matte: solid flat look, no facet or Oren-Nayar noise."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    ceramic = np.clip(base * 0.78 + gray * 0.22, 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + ceramic * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.1 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_ceramic_matte(shape, seed, sm, base_m, base_r):
    """Ceramic matte: dielectric, high roughness, flat spec (CC=160)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    M = np.full((h, w), 0.0, dtype=np.float32)
    R = np.full((h, w), 120.0, dtype=np.float32)
    CC = np.full((h, w), 160.0, dtype=np.float32)
    return M, R, CC


# ==================================================================
# CRYSTAL CLEAR - Snell's law refraction + caustic highlights
# Clear glass refracts what's behind it. We simulate by displacing
# the paint buffer using Snell's law angles derived from a surface
# curvature map. Caustic bright spots form where rays converge.
# ==================================================================

def paint_crystal_clear_v2(paint, shape, mask, seed, pm, bb):
    """Crystal clear glass with Snell's law refraction distortion and caustic highlights."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Surface curvature map (glass isn't perfectly flat)
    curve = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 210)

    # Snell's law: n1*sin(theta1) = n2*sin(theta2), n_glass = 1.52
    # Refraction displacement proportional to curvature gradient
    grad_y = np.gradient(curve, axis=0)
    grad_x = np.gradient(curve, axis=1)
    n_ratio = 1.0 / 1.52  # air to glass    # Refracted displacement (pixels)
    disp_scale = max(h, w) * 0.02
    dx = (grad_x * n_ratio * disp_scale).astype(int)
    dy = (grad_y * n_ratio * disp_scale).astype(int)

    yy, xx = np.mgrid[0:h, 0:w]
    sy = np.clip(yy + dy, 0, h - 1)
    sx = np.clip(xx + dx, 0, w - 1)
    refracted = base[sy, sx, :]

    # Caustic highlights: where curvature focuses light (high Laplacian)
    laplacian = (np.roll(curve, 1, 0) + np.roll(curve, -1, 0) +
                 np.roll(curve, 1, 1) + np.roll(curve, -1, 1) - 4.0 * curve)
    caustics = np.clip(laplacian * 15.0, 0, 1)

    # Glass tints slightly cool
    effect = np.clip(refracted * 0.92, 0, 1)
    effect[:,:,2] = np.clip(effect[:,:,2] + 0.03, 0, 1)
    effect = np.clip(effect + caustics[:,:,np.newaxis] * 0.2, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_crystal_clear(shape, seed, sm, base_m, base_r):
    """Glass: zero metallic, very low roughness, moderate clearcoat."""
    h, w = shape[:2] if len(shape) > 2 else shape
    curve = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 210)
    M = np.clip(base_m * 0.05 + curve * 3.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + curve * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + curve * 10.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# ENAMEL - Clean baked gloss (no heavy glaze simulation)
# Enamel reads as a smooth, deep gloss; base layer kept simple.
# ==================================================================

def paint_enamel_coating_v2(paint, shape, mask, seed, pm, bb):
    """Enamel: solid deep gloss, no texture or glaze variation in base."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    # Slight saturation boost and very subtle depth (no noise)
    deep = np.clip(base * 1.05 + gray * 0.02, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + deep * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.2 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_enamel_coating(shape, seed, sm, base_m, base_r):
    """Enamel: dielectric, low roughness (glassy), flat spec."""
    h, w = shape[:2] if len(shape) > 2 else shape
    M = np.full((h, w), base_m * 0.1, dtype=np.float32)
    R = np.full((h, w), 18.0, dtype=np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ==================================================================
# OBSIDIAN - Volcanic glass: Fresnel + absorption
# Natural obsidian is a dark volcanic glass. It absorbs almost all
# light (like void) but being glass it has strong Fresnel reflections
# at edges. The key difference from void: obsidian has smooth glass
# specularity, not micro-texture light trapping.
# ==================================================================

def paint_obsidian_glass_v2(paint, shape, mask, seed, pm, bb):
    """Obsidian volcanic glass with Fresnel edge reflections and conchoidal fracture detail."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Deep absorption — volcanic glass is nearly opaque
    micro = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 230)
    absorbed = np.exp(-(4.0 + micro * 1.0))  # strong absorption

    gray = base.mean(axis=2, keepdims=True)
    obsidian_base = np.clip(gray * absorbed[:,:,np.newaxis] + 0.005, 0, 0.04)
    # Fresnel reflections at edges — glass has strong specular at grazing
    # Schlick approximation: R = R0 + (1-R0)(1-cos_theta)^5
    # R0 for glass (n=1.5) = ((1.5-1)/(1.5+1))^2 = 0.04
    from PIL import Image as _Img, ImageFilter as _Filt
    mask_blur = np.array(_Img.fromarray((mask * 255).astype(np.uint8)).filter(
        _Filt.GaussianBlur(radius=max(h // 32, 3))
    )).astype(np.float32) / 255.0
    edge = np.clip((mask - mask_blur) * 6.0, 0, 1)
    R0 = 0.04
    fresnel = R0 + (1.0 - R0) * np.power(np.clip(edge, 0, 1), 2.0)

    # Fresnel reflection is bright, slightly cool (environment reflected)
    effect = obsidian_base.copy()
    effect = np.clip(effect + fresnel[:,:,np.newaxis] * np.array([0.35, 0.38, 0.42]) * 0.4, 0, 1)

    # Conchoidal fracture highlights — obsidian has shell-like fracture
    fracture = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 231)
    fracture_edge = np.clip((fracture - 0.7) * 5.0, 0, 1)
    effect = np.clip(effect + fracture_edge[:,:,np.newaxis] * 0.04, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_obsidian_glass(shape, seed, sm, base_m, base_r):
    """Obsidian: dielectric glass, very low roughness (glass-smooth), no clearcoat needed."""
    h, w = shape[:2] if len(shape) > 2 else shape
    micro = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 230)
    M = np.clip(base_m * 0.05 + micro * 4.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + micro * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(5.0 + micro * 5.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PORCELAIN - Subsurface scattering via blur-chain diffusion
# Porcelain's signature look is the soft glow from light scattering
# inside the translucent material. We simulate SSS by progressively
# blurring the paint at increasing radii and blending — light enters,
# bounces around inside, exits spread out. Warm tones scatter more.
# ==================================================================

def paint_porcelain_depth_v2(paint, shape, mask, seed, pm, bb):
    """Porcelain with subsurface scattering via progressive blur-chain diffusion."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    from PIL import Image as _Img, ImageFilter as _Filt

    # Create warm porcelain base (slight cream/ivory shift)
    gray = base.mean(axis=2, keepdims=True)
    porcelain = np.clip(base * 0.4 + gray * 0.5 + 0.08, 0, 1)
    porcelain[:,:,0] = np.clip(porcelain[:,:,0] + 0.03, 0, 1)  # warm
    porcelain[:,:,2] = np.clip(porcelain[:,:,2] - 0.02, 0, 1)  # less blue

    # SSS via progressive blur chain (multi-scale scatter)
    # Each blur represents deeper penetration
    sss_accum = np.zeros_like(porcelain)
    weights = [0.4, 0.25, 0.2, 0.15]  # near surface to deep
    radii = [max(h//256,1), max(h//128,2), max(h//64,3), max(h//32,4)]
    for weight, radius in zip(weights, radii):
        blurred = np.zeros_like(porcelain)
        for c in range(3):
            ch_pil = _Img.fromarray((porcelain[:,:,c] * 255).astype(np.uint8))
            blurred[:,:,c] = np.array(ch_pil.filter(
                _Filt.GaussianBlur(radius=radius)
            )).astype(np.float32) / 255.0
        sss_accum += blurred * weight
    # Red channel scatters more in porcelain (warm glow)
    sss_accum[:,:,0] = np.clip(sss_accum[:,:,0] * 1.08, 0, 1)

    # Surface gloss on top of SSS
    surface_gloss = np.clip(porcelain * 0.3 + sss_accum * 0.7, 0, 1)

    # Fine craze pattern (very subtle on quality porcelain)
    craze = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 241)
    craze_lines = np.clip((craze - 0.85) * 10.0, 0, 0.05)
    surface_gloss = np.clip(surface_gloss - craze_lines[:,:,np.newaxis], 0, 1)

    effect = surface_gloss.astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_porcelain_depth(shape, seed, sm, base_m, base_r):
    """Porcelain: dielectric, low-moderate roughness, some clearcoat from glaze."""
    h, w = shape[:2] if len(shape) > 2 else shape
    craze = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 241)
    M = np.clip(base_m * 0.05 + craze * 3.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(25.0 + craze * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + craze * 8.0, 0, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# TEMPERED GLASS - Stress birefringence (photoelastic effect)
# Tempered glass has internal stress patterns from rapid cooling.
# When viewed through polarization, these stresses create rainbow
# interference fringes. This is the "butterfly wing" pattern you
# see in car windshields with polarized sunglasses.
# ==================================================================
def paint_tempered_glass_v2(paint, shape, mask, seed, pm, bb):
    """Tempered glass with stress birefringence interference fringes from quenching jets."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    yn = y / max(h - 1, 1)
    xn = x / max(w - 1, 1)

    # Internal stress field from quenching pattern
    # Multiple stress centers (cooling jet positions)
    rng = np.random.RandomState(seed + 250)
    stress = np.zeros((h, w), dtype=np.float32)
    n_jets = 8 + (seed % 6)
    for _ in range(n_jets):
        cy, cx = rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)
        dist = np.sqrt((yn - cy)**2 + (xn - cx)**2)
        # Concentric stress rings from each cooling jet
        freq = rng.uniform(15.0, 30.0)
        stress += np.sin(dist * freq) * np.exp(-dist * 3.0)

    stress = (stress - stress.min()) / (stress.max() - stress.min() + 1e-8)

    # Birefringence: stress creates phase retardation between polarization axes
    # This maps to color via the Michel-Levy chart (stress -> hue)
    # Low stress = gray, medium = yellow/blue, high = red/green
    hue = stress * 2.0 * np.pi  # full color wheel
    sat = np.clip(stress * 0.5, 0, 0.35)  # subtle saturation

    # HSV to RGB for the interference color
    h_idx = (hue / (np.pi / 3.0)).astype(int) % 6
    f_val = (hue / (np.pi / 3.0)) - np.floor(hue / (np.pi / 3.0))
    v_val = np.ones_like(stress) * 0.9  # bright glass
    p_val = v_val * (1.0 - sat)
    q_val = v_val * (1.0 - sat * f_val)
    t_val = v_val * (1.0 - sat * (1.0 - f_val))

    # Build RGB from HSV sectors
    bire_r = np.where(h_idx == 0, v_val, np.where(h_idx == 1, q_val,
             np.where(h_idx == 2, p_val, np.where(h_idx == 3, p_val,
             np.where(h_idx == 4, t_val, v_val)))))
    bire_g = np.where(h_idx == 0, t_val, np.where(h_idx == 1, v_val,
             np.where(h_idx == 2, v_val, np.where(h_idx == 3, q_val,
             np.where(h_idx == 4, p_val, p_val)))))
    bire_b = np.where(h_idx == 0, p_val, np.where(h_idx == 1, p_val,
             np.where(h_idx == 2, t_val, np.where(h_idx == 3, v_val,
             np.where(h_idx == 4, v_val, q_val)))))

    # Blend birefringence color with base glass appearance
    gray = base.mean(axis=2, keepdims=True)
    glass_base = np.clip(gray * 0.85 + 0.08, 0, 1)
    bire = np.stack([bire_r, bire_g, bire_b], axis=-1).astype(np.float32)
    effect = np.clip(glass_base * 0.7 + bire * 0.3, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_tempered_glass(shape, seed, sm, base_m, base_r):
    """Tempered glass: dielectric, very low roughness, clearcoat from glass surface."""
    h, w = shape[:2] if len(shape) > 2 else shape
    stress = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 250)
    M = np.clip(base_m * 0.05 + stress * 3.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(4.0 + stress * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + stress * 10.0, 0, 255).astype(np.float32)
    return M, R, CC