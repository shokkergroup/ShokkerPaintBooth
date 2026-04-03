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
from scipy.spatial import cKDTree
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


def paint_candy_v2(paint, shape, mask, seed, pm, bb):
    """
    Generic candy coat — Beer-Lambert per-channel absorption.
    FIX: was hardcoded red → now tints toward base paint's dominant hue.
    Added micro-sparkle for candy depth.
    """
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Generate variation — married to spec
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1600)

    # Per-channel absorption: candy deepens the EXISTING base color instead of forcing red
    # Higher absorption on channels that are already lower → saturates the dominant hue
    avg = base[:, :, :3].mean(axis=2, keepdims=True).clip(0.1, 1.0)
    channel_strength = 1.0 - (base[:, :, :3] / avg)  # channels below avg get more absorption
    absorption = np.clip(0.6 + noise[:, :, np.newaxis] * 0.25 + channel_strength * 0.15, 0.3, 0.95)

    effect = base.copy()
    effect[:, :, :3] = np.clip(base[:, :, :3] * (1.0 - absorption * 0.5) +
                                base[:, :, :3] * absorption * 0.5 * 1.3, 0, 1)  # candy deepens + saturates

    # Micro-sparkle: 0.3% of pixels get bright candy highlights
    rng = np.random.RandomState(seed + 1600)
    sparkle_mask = (rng.random((h, w)) > 0.997).astype(np.float32)
    sparkle = sparkle_mask * 0.25 * pm
    effect[:, :, :3] = np.clip(effect[:, :, :3] + sparkle[:, :, np.newaxis], 0, 1)

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.20 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy(shape, seed, sm, base_m, base_r):
    """Generic candy spec. MARRIED to paint seed+1600. FIX: removed *255 double-scaling."""
    h, w = shape[:2] if len(shape) > 2 else shape
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1600)
    M = np.clip(base_m * 0.65 + noise * 30.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r * 0.4 + noise * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + noise * 8.0 * sm, 16, 32).astype(np.float32)
    return M, R, CC


def paint_candy_burgundy_v2(paint, shape, mask, seed, pm, bb):
    """
    Deep burgundy candy with wine-red absorption profile.
    Multi-scale absorption creates depth with warm undertones.
    """
    bb = ensure_bb_2d(bb, shape)
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
    # Near-IR absorption deepens blue in thick-coat zones — WEAK-CANDY-001 FIX
    # Burgundy red wine is dark because it absorbs short wavelengths heavily
    # BUG-CANDY-001 FIX: multiply by mask so blue suppression only applies inside painted zone
    result[..., 2] = np.clip(result[..., 2] * (1.0 - absorption * 0.15 * mask), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_burgundy(shape, seed, sm, base_m, base_r):
    """
    Burgundy spec — muted highlight with wine-stained appearance.
    G channel clamped to minimum 15 (iRacing GGX requires non-zero roughness for candy).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_candy_burgundy_v2: seed+1602 [4,8], seed+1603 [1,2]
    noise_coarse = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 1602)
    noise_fine = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 1603)
    M = base_m * 0.65 + (noise_coarse * 0.12 + noise_fine * 0.06)
    R = base_r * 0.35 + noise_fine * 0.12
    CC = np.clip(16.0 + noise_coarse * 8.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            CC)


def paint_candy_chrome_v2(paint, shape, mask, seed, pm, bb):
    """
    Candy over chrome base — maximum reflection + color filter.
    Fresnel effect with strong directional highlights over reflective substrate.
    """
    bb = ensure_bb_2d(bb, shape)
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
    G channel clamped to minimum 15 (iRacing GGX requires non-zero roughness for candy).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    grid = get_mgrid((h, w))
    fresnel_spec = 0.5 + 0.3 * np.abs(np.sin(grid[1] * np.pi))
    M = base_m * 0.9 + fresnel_spec * 0.2
    fine_noise = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 1607)
    R = base_r * 0.8 + fine_noise * 0.15
    CC = np.clip(16.0 + fine_noise * 4.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            CC)

def paint_candy_emerald_v2(paint, shape, mask, seed, pm, bb):
    """
    Green candy with copper phthalocyanine pigment absorption.
    Deep green with subtle blue shift — wavelength-dependent penetration.
    """
    bb = ensure_bb_2d(bb, shape)
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
    # Copper phthalocyanine micro-crystalline fleck sparkle — WEAK-CANDY-001 FIX
    # CuPc pigments have angular crystal facets that produce bright micro-specular points
    rng = np.random.RandomState(seed + 1699)
    sparkle = (rng.random((h, w)) < 0.003).astype(np.float32) * pm * 0.4 * mask
    # WARN-CANDY-001 FIX: green-yellow tint matches CuPc spectral output (not white)
    result = np.clip(result + sparkle[:,:,np.newaxis] * np.array([0.8, 1.0, 0.3], dtype=np.float32), 0, 1).astype(np.float32)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_candy_emerald(shape, seed, sm, base_m, base_r):
    """
    Emerald spec — cool green reflection with moderate sparkle.
    G channel clamped to minimum 15 (iRacing GGX requires non-zero roughness for candy).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_candy_emerald_v2: seed+1608 [2,4], seed+1609 [1,3,6]
    noise_primary = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1608)
    noise_secondary = multi_scale_noise((h, w), [1, 3, 6], [0.4, 0.3, 0.3], seed + 1609)
    M = base_m * 0.6 + (noise_primary * 0.14 + noise_secondary * 0.06)
    R = base_r * 0.45 + noise_secondary * 0.14
    CC = np.clip(16.0 + noise_primary * 8.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            CC)


def paint_hydrographic_v2(paint, shape, mask, seed, pm, bb):
    """
    Water transfer film with Plateau-Rayleigh instability pattern.
    Thin film creates ripple-like surface waves with color shifts.
    """
    bb = ensure_bb_2d(bb, shape)
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
    noise_cc = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1613)
    R = base_r * 0.35 + noise_cc * 0.18
    CC = np.clip(16.0 + noise_cc * 8.0 * sm, 16, 32).astype(np.float32)
    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            CC)


def paint_jelly_pearl_v2(paint, shape, mask, seed, pm, bb):
    """
    Translucent jelly pearl: BASE COLOR SHOWS THROUGH with pearlescent wash.
    Pearl particles create shimmer highlights that shift. No fixed jelly color.
    """
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Pearl particle distribution (scattered bright shimmer spots)
    particle_noise = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 1614)
    particles = np.clip((particle_noise - 0.3) * 2.0, 0, 1)

    # Pearlescent angle-shift simulation
    angle_noise = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1615)
    pearl_shift = angle_noise * 0.5 + 0.5  # 0-1 "viewing angle"

    # Translucent LIGHTEN of base paint (not replacement)
    # Jelly effect: lift the base color toward white with pearl iridescence
    lighten_amount = 0.25  # how much to lighten
    lightened = np.clip(base + lighten_amount, 0, 1)

    # Pearl shimmer highlights that shift color based on "angle"
    shimmer_r = particles * (0.6 + 0.4 * np.sin(pearl_shift * np.pi * 2.0))
    shimmer_g = particles * (0.6 + 0.4 * np.sin(pearl_shift * np.pi * 2.0 + 2.1))
    shimmer_b = particles * (0.6 + 0.4 * np.sin(pearl_shift * np.pi * 2.0 + 4.2))

    # Effect: lightened base + pearl shimmer overlay (base color shows through)
    effect = np.stack([
        np.clip(lightened[:,:,0] + shimmer_r * 0.2, 0, 1),
        np.clip(lightened[:,:,1] + shimmer_g * 0.15, 0, 1),
        np.clip(lightened[:,:,2] + shimmer_b * 0.2, 0, 1),
    ], axis=-1)

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.20 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_jelly_pearl(shape, seed, sm, base_m, base_r):
    """
    Jelly pearl spec: pearlescent shimmer with scattered highlight particles.
    Moderate metallic from mica particles, low roughness for gloss, good clearcoat.
    """
    h, w = shape
    # MARRIED to paint_jelly_pearl_v2: seed+1614 [4,8,16], seed+1615 [16,32]
    particle_noise = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 1614)
    particles = np.clip((particle_noise - 0.3) * 2.0, 0, 1)
    angle = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1615)
    # M: pearl zones = high metallic (mica shimmer), non-pearl = moderate
    M = np.clip(80.0 + particles * 140.0 * sm + angle * 30.0 * sm, 0, 255).astype(np.float32)
    # R: pearl zones = glossy (LOW R), non-pearl = slightly rougher
    # particles HIGH → R low (glossy pearl shimmer). particles LOW → R higher (matte jelly)
    R = np.clip(15.0 + (1.0 - particles) * 20.0 * sm + angle * 5.0 * sm, 15, 255).astype(np.float32)
    # CC: pearl zones = pearlescent (HIGHER CC), non-pearl = less
    CC = np.clip(16.0 + particles * 14.0 * sm + (1.0 - particles) * 4.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC

def paint_moonstone_v2(paint, shape, mask, seed, pm, bb):
    """
    Adularescence light scattering from orthoclase feldspar layers.
    Moving light shimmer effect — glow travels across surface.
    """
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    
    grid = get_mgrid((h, w))
    # WARN-CANDY-003 FIX: seed-derived center avoids every moonstone instance sharing same peak position
    cy = 0.35 + (seed % 31) / 100.0
    cx = 0.35 + (seed % 29) / 100.0
    # Adularescence: light ray traveling across surface
    shimmer = 0.5 + 0.4 * np.sin((grid[0] + grid[1]) * 3 + seed) * np.exp(-((grid[0] - cy)**2 + (grid[1] - cx)**2) * 3)
    
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
    FLAT-FIX: base_m/base_r are 0-255 scale, not 0-1. Fixed math.
    """
    h, w = shape
    grid = get_mgrid((h, w))
    # MARRIED to paint_moonstone_v2: same grid shimmer + Gaussian envelope
    cy = 0.35 + (seed % 31) / 100.0
    cx = 0.35 + (seed % 29) / 100.0
    shimmer = 0.5 + 0.4 * np.sin((grid[0] + grid[1]) * 3 + seed) * np.exp(-((grid[0] - cy)**2 + (grid[1] - cx)**2) * 3)
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1617)
    # base_m, base_r are in 0-255 range — work in that range directly
    M = np.clip(base_m + (shimmer - 0.5) * 40.0 * sm + noise * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + (noise - 0.5) * 25.0 * sm + shimmer * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + shimmer * 12.0 * sm + noise * 6.0 * sm, 0, 255).astype(np.float32)
    return (M, R, CC)


def paint_opal_v2(paint, shape, mask, seed, pm, bb):
    """
    Dragon's Pearl Scale: iridescent overlapping hexagonal scale pattern
    with pearlescent shimmer at each scale edge. Not a diffraction grating.
    """
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Generate hexagonal/fish-scale pattern using Voronoi-like cells
    rng = np.random.RandomState(seed + 1619)
    n_scales = 200  # number of scale centers
    # Hexagonal-ish grid with jitter for organic look
    grid_n = int(np.sqrt(n_scales))
    cy_pts = []
    cx_pts = []
    for gy in range(grid_n + 2):
        for gx in range(grid_n + 2):
            base_y = (gy + 0.5) / (grid_n + 1) * h
            base_x = (gx + 0.5 + (gy % 2) * 0.5) / (grid_n + 1) * w
            cy_pts.append(base_y + rng.randn() * h / (grid_n * 3))
            cx_pts.append(base_x + rng.randn() * w / (grid_n * 3))
    pts = np.stack([cy_pts, cx_pts], axis=1)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.stack([yy.ravel(), xx.ravel()], axis=1).astype(np.float64)
    dists, indices = tree.query(coords)
    labels = indices.reshape(h, w)
    dists = dists.reshape(h, w).astype(np.float32)
    max_d = np.percentile(dists, 95) + 1e-8
    dist_norm = np.clip(dists / max_d, 0, 1)

    # Scale edges: where dist_norm is high (near boundary between cells)
    edge_glow = np.clip(1.0 - dist_norm * 3.0, 0, 1)  # bright at edges
    scale_interior = np.clip(dist_norm * 2.5, 0, 1)  # smooth interior

    # Per-scale hue — COHERENT dragon scale gradient (gold → green → teal)
    # Instead of random hue per cell, use spatial position + gentle noise
    # so adjacent scales shift smoothly like real iridescent reptile scales
    n_pts = len(cy_pts)
    pts_arr = np.array(pts)
    # Spatial gradient: diagonal flow from gold (top-left) to teal (bottom-right)
    spatial_t = (pts_arr[:, 0] / (h + 1e-8) * 0.5 +
                 pts_arr[:, 1] / (w + 1e-8) * 0.5)
    spatial_t = np.clip(spatial_t, 0, 1).astype(np.float32)
    # Add per-scale jitter — small, keeping neighbors coherent
    jitter = rng.uniform(-0.08, 0.08, size=n_pts).astype(np.float32)
    scale_t = np.clip(spatial_t + jitter, 0, 1)
    t_map = scale_t[labels]

    # Angle-shift simulation: noise shifts position along the gradient
    angle_noise = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1620)
    shifted_t = np.clip(t_map + angle_noise * 0.12, 0, 1)

    # Dragon scale color palette: warm gold → olive green → emerald → teal
    # 4-stop gradient mapped to t=0..1
    # t=0.0: warm gold     [0.82, 0.65, 0.18]
    # t=0.33: olive-bronze  [0.55, 0.62, 0.15]
    # t=0.66: emerald green [0.12, 0.58, 0.30]
    # t=1.0: deep teal      [0.08, 0.45, 0.42]
    c0 = np.array([0.82, 0.65, 0.18], dtype=np.float32)
    c1 = np.array([0.55, 0.62, 0.15], dtype=np.float32)
    c2 = np.array([0.12, 0.58, 0.30], dtype=np.float32)
    c3 = np.array([0.08, 0.45, 0.42], dtype=np.float32)

    # Piecewise linear interpolation through the 4 stops
    t3 = shifted_t * 3.0  # scale to 0-3 for 3 segments
    seg = np.clip(np.floor(t3).astype(int), 0, 2)
    frac = np.clip(t3 - seg, 0, 1)

    colors_lut = np.stack([c0, c1, c2, c3])  # (4, 3)
    r_ch = colors_lut[seg, 0] * (1 - frac) + colors_lut[np.minimum(seg + 1, 3), 0] * frac
    g_ch = colors_lut[seg, 1] * (1 - frac) + colors_lut[np.minimum(seg + 1, 3), 1] * frac
    b_ch = colors_lut[seg, 2] * (1 - frac) + colors_lut[np.minimum(seg + 1, 3), 2] * frac

    # Pearl shimmer at scale edges — boosted from 0.3 to 0.5 for visible sparkle
    edge_shimmer = edge_glow * 0.5
    r_ch = np.clip(r_ch + edge_shimmer * 0.8, 0, 1)
    g_ch = np.clip(g_ch + edge_shimmer * 0.7, 0, 1)
    b_ch = np.clip(b_ch + edge_shimmer * 0.9, 0, 1)

    # Per-scale brightness: gold brighter, teal darker (adds dimension)
    scale_bright = np.clip(1.0 - shifted_t * 0.3, 0.7, 1.0)
    r_ch = np.clip(r_ch * scale_bright, 0, 1)
    g_ch = np.clip(g_ch * scale_bright, 0, 1)
    b_ch = np.clip(b_ch * scale_bright, 0, 1)

    effect = np.stack([r_ch, g_ch, b_ch], axis=2)
    # FIX: stronger scale overlay (was 0.35/0.65 → 0.15/0.85) so dragon scales dominate
    effect = base * 0.15 + effect * 0.85

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_opal(shape, seed, sm, base_m, base_r):
    """
    Dragon's Pearl Scale spec: hexagonal scale pattern with metallic edges (M=200+),
    smooth glossy interior (M=80-120), pearlescent clearcoat variation per scale.

    Uses the SAME Voronoi cell structure as paint_opal_v2 (cKDTree, seed+1619)
    so spec edges align perfectly with paint edges.
    """
    h, w = shape
    rng = np.random.RandomState(seed + 1619)
    n_scales = 200
    grid_n = int(np.sqrt(n_scales))
    cy_pts, cx_pts = [], []
    for gy in range(grid_n + 2):
        for gx in range(grid_n + 2):
            base_y = (gy + 0.5) / (grid_n + 1) * h
            base_x = (gx + 0.5 + (gy % 2) * 0.5) / (grid_n + 1) * w
            cy_pts.append(base_y + rng.randn() * h / (grid_n * 3))
            cx_pts.append(base_x + rng.randn() * w / (grid_n * 3))
    pts = np.stack([cy_pts, cx_pts], axis=1)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.stack([yy.ravel(), xx.ravel()], axis=1).astype(np.float64)
    dists, indices = tree.query(coords)
    labels = indices.reshape(h, w)
    dists = dists.reshape(h, w).astype(np.float32)
    max_d = np.percentile(dists, 95) + 1e-8
    dist_norm = np.clip(dists / max_d, 0, 1)

    edge_mask = np.clip(1.0 - dist_norm * 3.0, 0, 1)    # 1 at edges, 0 at centers
    interior_mask = np.clip(dist_norm * 2.5, 0, 1)        # 1 at centers, 0 at edges

    # Per-scale clearcoat variation — MARRIED to paint via same rng sequence
    n_pts = len(cy_pts)
    angle_noise = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1620)
    cc_map = np.clip(angle_noise * 0.5 + 0.5, 0, 1).astype(np.float32)

    # M: edges highly metallic (pearl shimmer), interior moderate
    M = np.clip(80.0 + edge_mask * 170.0 * sm, 0, 255).astype(np.float32)

    # R: GLOSSY INTERIORS (low R), rougher edges (higher R) — FIX: was inverted
    R = np.clip(15.0 + edge_mask * 35.0 * sm, 15, 255).astype(np.float32)

    # CC: pearlescent at edges, moderate variation via angle noise
    CC = np.clip(16.0 + edge_mask * 18.0 * sm + cc_map * 10.0 * sm, 16, 255).astype(np.float32)

    return M, R, CC


def paint_smoked_v2(paint, shape, mask, seed, pm, bb):
    """
    Smoke tint darkening via Beer-Lambert gray absorption.
    Translucent smoke effect — darkens underlying color uniformly.
    """
    bb = ensure_bb_2d(bb, shape)
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
    # MARRIED to paint_smoked_v2: seed+1621, scales [2,4,8]
    noise = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.3, 0.3], seed + 1621)
    M = base_m * 0.5 + noise * 0.12
    R = base_r * 0.35 + noise * 0.1
    CC = np.clip(16.0 + noise * 10.0 * sm, 16, 34).astype(np.float32)
    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            CC)

def paint_spectraflame_v2(paint, shape, mask, seed, pm, bb):
    """
    Sentient Polycarbonate: color-shifting clear optical polymer.
    Shifts hue based on noise topology (simulating viewing angle).
    Like looking through an optical crystal that bends light differently at each point.
    """
    bb = ensure_bb_2d(bb, shape)
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Viewing angle topology simulation (noise = surface angle variation)
    topo = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1624)
    fine = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 1625)

    # Convert base paint to grayscale luminance for hue-shift reference
    lum = base[:,:,0] * 0.299 + base[:,:,1] * 0.587 + base[:,:,2] * 0.114

    # Hue shift amount driven by noise topology (simulates angle-dependent refraction)
    hue_shift = topo * 0.55 + fine * 0.20  # 0-0.75 range shift (was 0-0.55, too subtle)

    # Apply hue rotation to the base paint color
    # Convert RGB to approximate hue, shift it, convert back
    # Simplified: rotate RGB channels based on topology
    cos_shift = np.cos(hue_shift * np.pi * 2.0)
    sin_shift = np.sin(hue_shift * np.pi * 2.0)

    # Rodrigues hue rotation around (1,1,1) luminance axis — corrected coefficients
    c, s = cos_shift, sin_shift
    r_out = base[:,:,0] * (0.333 + 0.667 * c) + base[:,:,1] * (0.333 - 0.333 * c - 0.577 * s) + base[:,:,2] * (0.333 - 0.333 * c + 0.577 * s)
    g_out = base[:,:,0] * (0.333 - 0.333 * c + 0.577 * s) + base[:,:,1] * (0.333 + 0.667 * c) + base[:,:,2] * (0.333 - 0.333 * c - 0.577 * s)
    b_out = base[:,:,0] * (0.333 - 0.333 * c - 0.577 * s) + base[:,:,1] * (0.333 - 0.333 * c + 0.577 * s) + base[:,:,2] * (0.333 + 0.667 * c)

    # Polycarbonate clear crystal shimmer — boosted from 0.08 to 0.14 for visible sparkle
    crystal_shimmer = np.clip((topo - 0.3) * 2.0, 0, 1) * 0.14
    r_out = np.clip(r_out + crystal_shimmer, 0, 1)
    g_out = np.clip(g_out + crystal_shimmer * 0.8, 0, 1)
    b_out = np.clip(b_out + crystal_shimmer * 1.1, 0, 1)

    effect = np.stack([r_out, g_out, b_out], axis=2).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_spectraflame(shape, seed, sm, base_m, base_r):
    """
    Sentient Polycarbonate spec: glassy low roughness with subtle
    interference-like variation. Clear optical polymer surface.
    """
    h, w = shape
    # MARRIED to paint_spectraflame_v2: seed+1624 [8,16,32], seed+1625 [2,4,8]
    topo = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1624)
    fine = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 1625)
    # M: moderate metallic with interference variation
    M = np.clip(100.0 + topo * 80.0 * sm + fine * 25.0 * sm, 0, 255).astype(np.float32)
    # R: glassy smooth with ACTUAL variation above GGX floor (was 3-13, all clamped to 15)
    R = np.clip(16.0 + fine * 12.0 * sm + topo * 8.0 * sm, 15, 255).astype(np.float32)
    # CC: optical grade polymer, variation follows topology
    CC = np.clip(16.0 + topo * 10.0 * sm + fine * 4.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_tinted_clear_v2(paint, shape, mask, seed, pm, bb):
    """
    Colored clearcoat with uniform Beer-Lambert tint.
    Subtle color shift — nearly transparent with consistent hue.
    """
    bb = ensure_bb_2d(bb, shape)
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
    # MARRIED to paint_tinted_clear_v2: seed+1629, scales [1,2,4]
    noise = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1629)
    M = base_m * 0.85 + noise * 0.1
    R = base_r * 0.6 + noise * 0.1
    CC = np.clip(16.0 + noise * 6.0 * sm, 16, 28).astype(np.float32)
    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            CC)


def paint_tinted_lacquer_v2(paint, shape, mask, seed, pm, bb):
    """
    Nitrocellulose lacquer with dissolved dye molecules.
    Glossy finish with slight orange-peel texture from drying patterns.
    """
    bb = ensure_bb_2d(bb, shape)
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
    noise_r = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1635)
    R = base_r * 0.65 + noise_r * 0.16
    CC = np.clip(16.0 + noise_r * 7.0 * sm, 16, 30).astype(np.float32)
    return (np.clip(M * 255.0, 0, 255).astype(np.float32),
            np.clip(R * 255.0, 15, 255).astype(np.float32),
            CC)


def paint_tri_coat_pearl_v2(paint, shape, mask, seed, pm, bb):
    """
    Three-layer pearl with ZONE-WEIGHTED color mixing.
    Each zone has a dominant coat color — not flat averaging.
    FIX: was /3.0 equal blend → now zone-weighted like spec's w1/w2/w3.
    """
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Three independent pearl layers — same seeds as spec for marriage
    layer1 = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1636)
    layer2 = multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 1637)
    layer3 = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1638)

    # Normalize to 0-1 range for zone weighting
    l1 = np.clip(layer1 * 0.5 + 0.5, 0.01, 1.0)
    l2 = np.clip(layer2 * 0.5 + 0.5, 0.01, 1.0)
    l3 = np.clip(layer3 * 0.5 + 0.5, 0.01, 1.0)

    # Zone weights — whichever layer is strongest DOMINATES (matches spec's w1/w2/w3)
    total = l1 + l2 + l3 + 1e-8
    w1 = (l1 / total)[:, :, np.newaxis]
    w2 = (l2 / total)[:, :, np.newaxis]
    w3 = (l3 / total)[:, :, np.newaxis]

    color1 = np.array([0.95, 0.4, 0.3])   # Red pearl (coat 1)
    color2 = np.array([0.3, 0.7, 0.95])   # Blue pearl (coat 2)
    color3 = np.array([0.4, 0.95, 0.5])   # Green pearl (coat 3)

    # Zone-weighted mix: dominant coat shows its color clearly
    effect = w1 * color1 + w2 * color2 + w3 * color3
    effect = np.clip(effect, 0, 1)

    # Stronger overlay — 0.35 base + 0.65 tri-coat (was 0.5/0.5)
    effect = base * 0.35 + effect * 0.65

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.3 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_tri_coat_pearl(shape, seed, sm, base_m, base_r):
    """
    Tri-coat pearl spec: THREE DISTINCT ZONES with different metallic/roughness
    creating visible color-shift regions. Each coat is distinguishable.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_tri_coat_pearl_v2: same seeds AND scales
    layer1 = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1636)
    layer2 = multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 1637)
    layer3 = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 1638)

    # Create three DOMINANT zones (each layer claims territory)
    l1 = np.clip(layer1 * 0.5 + 0.5, 0, 1)
    l2 = np.clip(layer2 * 0.5 + 0.5, 0, 1)
    l3 = np.clip(layer3 * 0.5 + 0.5, 0, 1)

    # Determine which "coat" dominates at each pixel
    total = l1 + l2 + l3 + 1e-8
    w1 = l1 / total  # coat 1 weight
    w2 = l2 / total  # coat 2 weight
    w3 = l3 / total  # coat 3 weight

    # Coat 1: High metallic, very smooth (chrome pearl)
    # Coat 2: Medium metallic, moderate roughness (satin pearl)
    # Coat 3: Low metallic, smooth (gloss pearl)
    M = np.clip((w1 * 220.0 + w2 * 140.0 + w3 * 60.0) * sm + 30.0 * (1.0 - sm), 0, 255).astype(np.float32)
    R = np.clip(w1 * 4.0 + w2 * 25.0 + w3 * 8.0 + 3.0, 15, 255).astype(np.float32)

    # CC varies by coat zone for visible shift
    CC = np.clip(16.0 + w1 * 5.0 + w2 * 20.0 * sm + w3 * 10.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


# ============================================================================
# CANDY APPLE — Deep crimson Beer-Lambert, shadow-crush absorption
# ============================================================================

def paint_candy_apple_v2(paint, shape, mask, seed, pm, bb):
    """
    Candy apple — deeply saturated crimson candy, Beer-Lambert single-pass.
    High base absorption (0.82+) vs generic candy (0.70+) creates a characteristic
    'shadow crush': mid-tones go almost black, only bright specular zones show vivid
    crimson. Distinct from candy_v2 [0.8,0.1,0.1] (lighter red) and candy_burgundy
    [0.4,0.05,0.08] (wine-brown). Candy apple = near-monochromatic crimson, green+blue
    both suppressed hard.
    WEAK-036 FIX: replaces paint_smoked_darken (15% gray darkener, zero red physics).
    """
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Two-scale noise for organic depth variation
    noise_coarse = multi_scale_noise((h, w), [4, 8], [0.55, 0.45], seed + 1645)
    noise_fine   = multi_scale_noise((h, w), [1, 2], [0.60, 0.40], seed + 1646)

    # Deep crimson — more saturated than generic candy, near-monochromatic red
    candy_color = np.array([0.72, 0.02, 0.02], dtype=np.float32)

    # High base absorption for "shadow crush" — mid-tones crushed toward black
    absorption = np.float32(0.82) + (noise_coarse * np.float32(0.10) + noise_fine * np.float32(0.05))
    absorption = np.clip(absorption, np.float32(0.72), np.float32(0.97))

    effect = (base * (np.float32(1.0) - absorption[:, :, np.newaxis])
              + candy_color[np.newaxis, np.newaxis, :] * absorption[:, :, np.newaxis])

    blend   = np.float32(np.clip(pm, 0.0, 1.0))
    mask_3d = mask[:, :, np.newaxis]
    result  = np.clip(base * (np.float32(1.0) - mask_3d * blend)
                      + effect * (mask_3d * blend), 0, 1)
    # Green + blue suppression in candy zones (short-wavelength absorption)
    result[..., 1] = np.clip(result[..., 1] * (np.float32(1.0) - absorption * np.float32(0.12) * mask), 0, 1)
    result[..., 2] = np.clip(result[..., 2] * (np.float32(1.0) - absorption * np.float32(0.18) * mask), 0, 1)
    # Higher bb boost (0.20) — bright specular pops hard against crushed shadow
    return np.clip(result + bb[:, :, np.newaxis] * np.float32(0.20) * pm * mask_3d, 0, 1).astype(np.float32)