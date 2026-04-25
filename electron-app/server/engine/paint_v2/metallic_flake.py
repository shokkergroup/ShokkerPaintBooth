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
from engine.paint_v2 import ensure_bb_2d


# ==================================================================
# COPPER METALLIC - Drude model free-electron plasma reflection
# ==================================================================
def paint_copper_metallic_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    grain = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 901)
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
    R = np.clip(6.0 + ed * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + ed * 5.0, 16, 255).astype(np.float32)  # CC≥16
    return M, R, CC


# ============================================================================
# 2026-04-24 regular-base rebuild overrides
# ============================================================================

def _mf_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _mf_micro(shape, seed, density):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(seed)
    n = min(int(h * w * density), 150000)
    out = np.zeros((h, w), dtype=np.float32)
    if n > 0:
        yy = rng.integers(0, h, n)
        xx = rng.integers(0, w, n)
        vals = rng.uniform(0.18, 1.0, n).astype(np.float32)
        np.maximum.at(out, (yy, xx), vals)
    return np.maximum.reduce([
        out,
        np.roll(out, 1, axis=0) * 0.34,
        np.roll(out, -1, axis=1) * 0.34,
    ]).astype(np.float32)


def paint_copper_metallic_v2(paint, shape, mask, seed, pm, bb):
    """Standard copper: copper color first, subtle fine grain second."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    grain = _mf_norm01(multi_scale_noise((h, w), [2, 5, 12, 28], [0.34, 0.30, 0.23, 0.13], seed + 900))
    polish = _mf_norm01(multi_scale_noise((h, w), [18, 42], [0.58, 0.42], seed + 901))
    micro = _mf_micro((h, w), seed + 902, 0.026)
    fine = _mf_norm01(multi_scale_noise((h, w), [1, 2, 4], [0.42, 0.34, 0.24], seed + 903))
    copper = np.array([0.82, 0.39, 0.16], dtype=np.float32)
    warm = np.array([0.96, 0.57, 0.24], dtype=np.float32)
    effect = copper[None, None, :] * (0.82 + polish[:, :, None] * 0.14) + warm[None, None, :] * micro[:, :, None] * 0.10
    effect = np.clip(
        effect
        + (grain[:, :, None] - 0.5) * np.array([0.045, 0.028, 0.010], dtype=np.float32)
        + (fine[:, :, None] - 0.5) * np.array([0.075, 0.040, 0.012], dtype=np.float32),
        0, 1
    )
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.20 * blend, 0, 1).astype(np.float32)


def spec_copper_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    grain = _mf_norm01(multi_scale_noise((h, w), [2, 5, 12, 28], [0.34, 0.30, 0.23, 0.13], seed + 900))
    micro = _mf_micro((h, w), seed + 902, 0.026)
    fine = _mf_norm01(multi_scale_noise((h, w), [1, 2, 4], [0.42, 0.34, 0.24], seed + 903))
    M = np.clip(184.0 + grain * 38.0 * sm + micro * 28.0 * sm + fine * 24.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + (1 - micro) * 26.0 * sm + grain * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + grain * 12.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_standard_metallic_v2(paint, shape, mask, seed, pm, bb):
    """Plain standard metallic: preserves base hue with dense fine metal flake."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    flake = _mf_micro((h, w), seed + 943, 0.040)
    grain = _mf_norm01(multi_scale_noise((h, w), [2, 6, 14, 32], [0.34, 0.30, 0.22, 0.14], seed + 941))
    gray = base.mean(axis=2, keepdims=True)
    metallic = np.clip(base * 0.78 + gray * 0.16 + 0.04, 0, 1)
    metallic = np.clip(metallic * (0.92 + grain[:, :, None] * 0.12) + flake[:, :, None] * 0.11, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1 - blend) + metallic * blend + bb[:, :, None] * 0.18 * blend, 0, 1).astype(np.float32)


def spec_standard_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    grain = _mf_norm01(multi_scale_noise((h, w), [2, 6, 14, 32], [0.34, 0.30, 0.22, 0.14], seed + 941))
    flake = _mf_micro((h, w), seed + 943, 0.040)
    M = np.clip(168.0 + grain * 38.0 * sm + flake * 45.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(22.0 + (1 - flake) * 30.0 * sm + grain * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + flake * 10.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_rose_gold_metallic_v2(paint, shape, mask, seed, pm, bb):
    """Synthesized biomech flesh: rose-gold alloy with organic metallic pores."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    tissue = _mf_norm01(multi_scale_noise((h, w), [4, 9, 21, 48], [0.34, 0.30, 0.22, 0.14], seed + 971))
    pores = _mf_micro((h, w), seed + 972, 0.032)
    vein = _mf_norm01(
        np.sin(x * 0.055 + tissue * 4.0) +
        np.sin(y * 0.071 + x * 0.016 + tissue * 2.5) * 0.55
    )
    vein = np.clip((vein - 0.60) * 2.7, 0, 1)
    flesh = np.array([0.88, 0.48, 0.40], dtype=np.float32)
    gold = np.array([0.96, 0.66, 0.36], dtype=np.float32)
    deep = np.array([0.42, 0.12, 0.13], dtype=np.float32)
    effect = flesh[None, None, :] * (0.70 + tissue[:, :, None] * 0.18) + gold[None, None, :] * pores[:, :, None] * 0.15
    effect = np.clip(effect * (1 - vein[:, :, None] * 0.18) + deep[None, None, :] * vein[:, :, None] * 0.24, 0, 1)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1 - blend) + effect * blend + bb[:, :, None] * 0.18 * blend, 0, 1).astype(np.float32)


def spec_rose_gold_metallic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    tissue = _mf_norm01(multi_scale_noise((h, w), [4, 9, 21, 48], [0.34, 0.30, 0.22, 0.14], seed + 971))
    pores = _mf_micro((h, w), seed + 972, 0.032)
    M = np.clip(160.0 + tissue * 48.0 * sm + pores * 36.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + tissue * 30.0 * sm + (1 - pores) * 16.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + tissue * 18.0 * sm + pores * 14.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


_spb_paint_copper_metallic_v2 = paint_copper_metallic_v2
_spb_spec_copper_metallic = spec_copper_metallic
_spb_paint_standard_metallic_v2 = paint_standard_metallic_v2
_spb_spec_standard_metallic = spec_standard_metallic
_spb_paint_rose_gold_metallic_v2 = paint_rose_gold_metallic_v2
_spb_spec_rose_gold_metallic = spec_rose_gold_metallic

# ==================================================================
# DIAMOND COAT - Snell's law total internal reflection sparkle
# ==================================================================
def paint_diamond_coat_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    dispersion = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 912)
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
    R = np.clip(3.0 + flake * 6.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(20.0 + flake * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# ELECTRIC ICE - Lichtenberg figure dielectric breakdown pattern
# ==================================================================
def paint_electric_ice_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Lichtenberg: fractal branching from dielectric breakdown
    # Approximate with multi-octave noise thresholded at different levels
    n1 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 921)
    n2 = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 922)
    n3 = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 923)
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
    """Electric ice spec: Lichtenberg-branching glaze surface.

    FIVE-HOUR SHIFT Win A6 (Animal-flagged SPEC_FLAT identity violator):
    pre-fix the gradient×8.0 was clipped to [0,1] then multiplied by
    60/10/5, but the gradient magnitudes from a low-frequency noise
    field [8,16,32] are tiny so the clipped ridge field stayed near
    zero. Audit: M_std≈1.64 R_std≈1.5 CC_std≈0 → flagged FLAT.
    Boost gradient amplification, drop the [0,1] clip on the ridge
    field, and add a high-frequency frost crackle pass so the surface
    actually looks electric.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    n1 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 921)
    n2 = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 922)
    ice_base = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 924)
    # NEW (Win A6): high-frequency frost crackle so micro-detail registers.
    frost = multi_scale_noise((h, w), [3, 8], [0.6, 0.4], seed + 925)
    # Primary ridge from Lichtenberg branching — boost amplification 8→32 and
    # widen [0,1] clip so the ridge field carries real signal.
    ridge = np.clip((np.abs(np.gradient(n1, axis=0)) + np.abs(np.gradient(n1, axis=1))) * 32.0, 0, 2.0)
    # Fine branch contribution — same boost.
    fine_branch = np.clip((np.abs(np.gradient(n2, axis=0)) + np.abs(np.gradient(n2, axis=1))) * 48.0, 0, 2.0) * 0.5
    lightning = np.clip(ridge + fine_branch + np.abs(frost) * 0.5, 0, 2.0)
    M = np.clip(120.0 + lightning * 50.0 * sm + ice_base * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + lightning * 12.0 * sm + ice_base * 3.0 * sm + np.abs(frost) * 6.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + lightning * 4.0 + ice_base * 2.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# GUNMETAL METALLIC - Beckmann micro-facet BRDF distribution
# ==================================================================
def paint_gunmetal_metallic_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Beckmann distribution: D(h) = exp(-tan^2(theta)/m^2) / (pi*m^2*cos^4(theta))
    # m = surface roughness parameter
    surface_slope = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 931)
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
    slope = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 931)
    M = np.clip(160.0 + slope * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(12.0 + slope * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + slope * 5.0, 16, 255).astype(np.float32)  # CC≥16
    return M, R, CC

# ==================================================================
# STANDARD METALLIC - Kubelka-Munk two-flux scattering
# ==================================================================
def paint_standard_metallic_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Kubelka-Munk: two opposing light fluxes (forward + backward)
    # R_inf = 1 + K/S - sqrt((K/S)^2 + 2*K/S)  where K=absorption, S=scatter
    scatter = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 941)
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
    scatter = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 941)
    M = np.clip(155.0 + scatter * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(10.0 + scatter * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + scatter * 5.0, 16, 255).astype(np.float32)  # CC≥16
    return M, R, CC

# ==================================================================
# PEARL CLASSIC - Nacre aragonite layered interference
# ==================================================================
def paint_pearl_classic_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    R = np.clip(5.0 + layer * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + layer * 5.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# PLASMA METAL - Ion bombardment surface energy modification
# ==================================================================
def paint_plasma_metal_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    tex = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 962)
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
    tex = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 962)
    # Texture roughness inversely proportional to surface energy (matching paint)
    texture_var = tex * (1.0 - np.clip(ion, 0, 1))
    M = np.clip(150.0 + ion * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + (1.0 - ion) * 18.0 * sm + texture_var * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + ion * 6.0, 16, 255).astype(np.float32)  # CC≥16
    return M, R, CC

# ==================================================================
# ROSE GOLD METALLIC - Au-Cu alloy d-band electronic color
# ==================================================================
def paint_rose_gold_metallic_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    R = np.clip(6.0 + cu * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + cu * 5.0, 16, 255).astype(np.float32)  # CC≥16
    return M, R, CC

# ==================================================================
# SATIN GOLD - Anisotropic Ward BRDF tangent-direction sheen
# ==================================================================
def paint_satin_gold_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    R = np.clip(15.0 + brush * 12.0 * sm, 15, 255).astype(np.float32)  # satin = moderate rough
    CC = np.clip(16.0 + brush * 5.0, 16, 255).astype(np.float32)  # CC≥16
    return M, R, CC


# Re-apply the 2026-04-24 regular-base overrides after legacy duplicate
# definitions later in this module.
paint_copper_metallic_v2 = _spb_paint_copper_metallic_v2
spec_copper_metallic = _spb_spec_copper_metallic
paint_standard_metallic_v2 = _spb_paint_standard_metallic_v2
spec_standard_metallic = _spb_spec_standard_metallic
paint_rose_gold_metallic_v2 = _spb_paint_rose_gold_metallic_v2
spec_rose_gold_metallic = _spb_spec_rose_gold_metallic
