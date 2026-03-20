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
    Translucent jelly pearl: BASE COLOR SHOWS THROUGH with pearlescent wash.
    Pearl particles create shimmer highlights that shift. No fixed jelly color.
    """
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
    # Pearl particle field
    particle_noise = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 1615)
    particles = np.clip((particle_noise - 0.3) * 2.5, 0, 1)
    # Angle-shift noise for metallic variation
    angle = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 1616)
    # M: pearl mica particles are metallic, background is moderate
    M = np.clip(80.0 + particles * 140.0 * sm + angle * 30.0 * sm, 0, 255).astype(np.float32)
    # R: glossy with pearl micro-texture
    R = np.clip(6.0 + (1.0 - particles) * 15.0 * sm + angle * 5.0 * sm, 0, 255).astype(np.float32)
    # CC: good clearcoat, slight variation
    CC = np.clip(16.0 + (1.0 - particles) * 10.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC

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
    Dragon's Pearl Scale: iridescent overlapping hexagonal scale pattern
    with pearlescent shimmer at each scale edge. Not a diffraction grating.
    """
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Generate hexagonal/fish-scale pattern using Voronoi-like cells
    from scipy.spatial import cKDTree
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

    # Per-scale iridescent hue (each scale gets a random hue)
    n_pts = len(cy_pts)
    scale_hues = rng.uniform(0, 1, size=n_pts).astype(np.float32)
    hue_map = scale_hues[labels]

    # Angle-shift simulation: noise shifts hue for viewing angle effect
    angle_noise = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1620)
    shifted_hue = (hue_map + angle_noise * 0.15) % 1.0

    # Convert hue to RGB (iridescent pearl colors)
    r_ch = np.clip(np.abs(shifted_hue * 6 - 3) - 1, 0, 1) * 0.6 + 0.3
    g_ch = np.clip(2 - np.abs(shifted_hue * 6 - 2), 0, 1) * 0.5 + 0.3
    b_ch = np.clip(2 - np.abs(shifted_hue * 6 - 4), 0, 1) * 0.6 + 0.3

    # Pearl shimmer at scale edges
    edge_shimmer = edge_glow * 0.3
    r_ch = np.clip(r_ch + edge_shimmer * 0.8, 0, 1)
    g_ch = np.clip(g_ch + edge_shimmer * 0.7, 0, 1)
    b_ch = np.clip(b_ch + edge_shimmer * 0.9, 0, 1)

    effect = np.stack([r_ch, g_ch, b_ch], axis=2)
    # Blend with base - scales overlay on base color
    effect = base * 0.35 + effect * 0.65

    blend = np.clip(pm, 0.0, 1.0)
    mask_3d = mask[:,:,np.newaxis]
    result = np.clip(base * (1.0 - mask_3d * blend) + effect * (mask_3d * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.25 * pm * mask_3d, 0, 1).astype(np.float32)


def spec_opal(shape, seed, sm, base_m, base_r):
    """
    Dragon's Pearl Scale spec: hexagonal scale pattern with metallic edges,
    smooth glossy interior, pearlescent clearcoat variation per scale.
    """
    h, w = shape
    # Scale pattern using noise-based Voronoi approximation
    scale_noise = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 1620)
    edge_detect = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1621)
    # Approximate scale edges
    edges = np.clip(1.0 - np.abs(scale_noise - 0.5) * 4.0, 0, 1)
    # M: edges are highly metallic (pearl shimmer), interior is moderate
    M = np.clip(80.0 + edges * 160.0 * sm + edge_detect * 20.0 * sm, 0, 255).astype(np.float32)
    # R: smooth glossy interior, slightly rougher at edges (texture)
    R = np.clip(5.0 + (1.0 - edges) * 8.0 * sm + edge_detect * 6.0 * sm, 0, 255).astype(np.float32)
    # CC: pearlescent variation, slightly higher at edges
    CC = np.clip(16.0 + edges * 15.0 * sm + scale_noise * 8.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


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
    Sentient Polycarbonate: color-shifting clear optical polymer.
    Shifts hue based on noise topology (simulating viewing angle).
    Like looking through an optical crystal that bends light differently at each point.
    """
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
    hue_shift = topo * 0.4 + fine * 0.15  # 0-0.55 range shift

    # Apply hue rotation to the base paint color
    # Convert RGB to approximate hue, shift it, convert back
    # Simplified: rotate RGB channels based on topology
    cos_shift = np.cos(hue_shift * np.pi * 2.0)
    sin_shift = np.sin(hue_shift * np.pi * 2.0)

    # Hue rotation matrix (simplified)
    r_out = base[:,:,0] * (0.667 + 0.333 * cos_shift) + base[:,:,1] * (0.333 - 0.333 * cos_shift - 0.577 * sin_shift) + base[:,:,2] * (0.333 - 0.333 * cos_shift + 0.577 * sin_shift)
    g_out = base[:,:,0] * (0.333 - 0.333 * cos_shift + 0.577 * sin_shift) + base[:,:,1] * (0.667 + 0.333 * cos_shift) + base[:,:,2] * (0.333 - 0.333 * cos_shift - 0.577 * sin_shift)
    b_out = base[:,:,0] * (0.333 - 0.333 * cos_shift - 0.577 * sin_shift) + base[:,:,1] * (0.333 - 0.333 * cos_shift + 0.577 * sin_shift) + base[:,:,2] * (0.667 + 0.333 * cos_shift)

    # Polycarbonate clear crystal shimmer (slight brightening at high-angle zones)
    crystal_shimmer = np.clip((topo - 0.3) * 2.0, 0, 1) * 0.08
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
    # Optical interference topology
    topo = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1627)
    fine = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 1628)
    # M: moderate metallic with interference variation (polycarbonate is partially reflective)
    M = np.clip(100.0 + topo * 80.0 * sm + fine * 25.0 * sm, 0, 255).astype(np.float32)
    # R: very low roughness (glassy smooth polymer), slight variation
    R = np.clip(3.0 + fine * 6.0 * sm + topo * 4.0 * sm, 0, 255).astype(np.float32)
    # CC: excellent clearcoat (optical grade polymer), minimal variation
    CC = np.clip(16.0 + (1.0 - topo) * 8.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


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
    Tri-coat pearl spec: THREE DISTINCT ZONES with different metallic/roughness
    creating visible color-shift regions. Each coat is distinguishable.
    """
    h, w = shape
    # Three banded/zoned layers with distinct characteristics
    layer1 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1639)
    layer2 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1640)
    layer3 = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 1641)

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
    R = np.clip(w1 * 4.0 + w2 * 25.0 + w3 * 8.0 + 3.0, 0, 255).astype(np.float32)

    # CC varies by coat zone for visible shift
    CC = np.clip(16.0 + w1 * 5.0 + w2 * 20.0 * sm + w3 * 10.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC