"""
Shokker Engine v1.0 - Multi-Zone Paint Finish Generator
========================================================
Takes a painted car TGA and applies DIFFERENT finishes to
DIFFERENT zones of the car, combining them into one final output.

KEY DIFFERENCE FROM PAINT STUDIO v2:
- Paint Studio v2 applies ONE finish to the WHOLE car
- Shokker Engine applies DIFFERENT finishes to DIFFERENT zones
- Finishes marked "spec_only" do NOT modify the paint at all
- Paint modifications are MUCH more subtle than v2 (fixes color change issues)

ZONE MASKING:
- Uses brightness-based auto-masking by default
- Can also accept custom masks (from the HTML app zone painter)

FIXED ISSUES FROM v2:
- Anodized: removed harsh brush artifacts, uses smoother pattern
- Electric/Lava/Oil Slick: reduced paint color modification dramatically
- All finishes: "spec_only" mode available to ONLY change spec map
"""

import numpy as np
from PIL import Image, ImageFilter
import struct
import os
import json
import time


def write_tga_32bit(filepath, rgba_array):
    h, w = rgba_array.shape[:2]
    with open(filepath, 'wb') as f:
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 2))
        f.write(struct.pack('<5B', 0, 0, 0, 0, 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', w))
        f.write(struct.pack('<H', h))
        f.write(struct.pack('<B', 32))
        f.write(struct.pack('<B', 0x28))
        bgra = np.stack([rgba_array[:,:,2], rgba_array[:,:,1],
                         rgba_array[:,:,0], rgba_array[:,:,3]], axis=-1)
        f.write(bgra.tobytes())


def write_tga_24bit(filepath, rgb_array):
    h, w = rgb_array.shape[:2]
    with open(filepath, 'wb') as f:
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 2))
        f.write(struct.pack('<5B', 0, 0, 0, 0, 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', w))
        f.write(struct.pack('<H', h))
        f.write(struct.pack('<B', 24))
        f.write(struct.pack('<B', 0x20))
        bgr = np.stack([rgb_array[:,:,2], rgb_array[:,:,1], rgb_array[:,:,0]], axis=-1)
        f.write(bgr.tobytes())


# ================================================================
# NOISE GENERATORS
# ================================================================

def generate_perlin_noise_2d(shape, res, seed=None):
    if seed is not None:
        np.random.seed(seed)
    def f(t):
        return 6*t**5 - 15*t**4 + 10*t**3
    delta = (res[0]/shape[0], res[1]/shape[1])
    d = (shape[0]//res[0], shape[1]//res[1])
    grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1,2,0) % 1
    angles = 2*np.pi*np.random.rand(res[0]+1, res[1]+1)
    gradients = np.dstack((np.cos(angles), np.sin(angles)))
    g00 = gradients[:-1,:-1].repeat(d[0],0).repeat(d[1],1)
    g10 = gradients[1:,:-1].repeat(d[0],0).repeat(d[1],1)
    g01 = gradients[:-1,1:].repeat(d[0],0).repeat(d[1],1)
    g11 = gradients[1:,1:].repeat(d[0],0).repeat(d[1],1)
    n00 = np.sum(np.dstack((grid[:,:,0], grid[:,:,1]))*g00, 2)
    n10 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]))*g10, 2)
    n01 = np.sum(np.dstack((grid[:,:,0], grid[:,:,1]-1))*g01, 2)
    n11 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]-1))*g11, 2)
    t = f(grid)
    n0 = n00*(1-t[:,:,0]) + t[:,:,0]*n10
    n1 = n01*(1-t[:,:,0]) + t[:,:,0]*n11
    return np.sqrt(2)*((1-t[:,:,1])*n0 + t[:,:,1]*n1)


def fractal_noise(shape, octaves=6, persistence=0.5, seed=42):
    noise = np.zeros(shape)
    amp = 1.0; freq = 1; max_amp = 0
    for i in range(octaves):
        res = (max(2, 2*freq), max(2, 2*freq))
        adj = (shape[0]-shape[0]%res[0]+res[0] if shape[0]%res[0]!=0 else shape[0],
               shape[1]-shape[1]%res[1]+res[1] if shape[1]%res[1]!=0 else shape[1])
        on = generate_perlin_noise_2d(adj, res, seed=seed+i if seed else None)
        noise += amp * on[:shape[0], :shape[1]]
        max_amp += amp; amp *= persistence; freq *= 2
    return noise / max_amp


def multi_scale_noise(shape, scales, weights, seed=42):
    h, w = shape
    combined = np.zeros((h, w))
    total_weight = sum(weights)
    for scale, weight in zip(scales, weights):
        np.random.seed(seed + scale * 7)
        if scale == 1:
            noise = np.random.randn(h, w)
        else:
            small_h = max(1, h // scale)
            small_w = max(1, w // scale)
            small_noise = np.random.randn(small_h, small_w)
            noise_img = Image.fromarray(
                ((small_noise + 3) / 6 * 255).clip(0, 255).astype(np.uint8)
            )
            noise_img = noise_img.resize((w, h), Image.BILINEAR)
            noise = np.array(noise_img).astype(np.float32) / 255.0 * 2 - 1
        combined += noise * weight
    return combined / total_weight


def hsv_to_rgb_vec(h, s, v):
    c = v * s
    hp = h * 6.0
    x = c * (1 - np.abs(hp % 2 - 1))
    r = np.zeros_like(c); g = np.zeros_like(c); b = np.zeros_like(c)
    for lo in range(6):
        m = (hp >= lo) & (hp < lo+1)
        if lo==0: r[m]=c[m]; g[m]=x[m]
        elif lo==1: r[m]=x[m]; g[m]=c[m]
        elif lo==2: g[m]=c[m]; b[m]=x[m]
        elif lo==3: g[m]=x[m]; b[m]=c[m]
        elif lo==4: r[m]=x[m]; b[m]=c[m]
        elif lo==5: r[m]=c[m]; b[m]=x[m]
    off = v - c
    return r+off, g+off, b+off


# ================================================================
# INTENSITY PRESETS - Reduced paint modification from v2
# ================================================================
INTENSITY = {
    "subtle":     {"paint": 0.3,  "spec": 0.6,  "bright": 0.02},
    "medium":     {"paint": 0.6,  "spec": 1.0,  "bright": 0.04},
    "aggressive": {"paint": 1.0,  "spec": 1.5,  "bright": 0.06},
    "extreme":    {"paint": 1.5,  "spec": 2.0,  "bright": 0.10},
}


# ================================================================
# SPEC MAP GENERATORS (the MAIN effect - no paint modification)
# ================================================================

def spec_gloss(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(5 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(25 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_matte(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 0
    spec[:,:,1] = np.clip(190 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0
    spec[:,:,3] = 255
    return spec

def spec_satin(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 0
    spec[:,:,1] = np.clip(100 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_metallic(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed+100)
    spec[:,:,0] = np.clip(225 * mask + 5 * (1-mask) + mn * 40 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(20 * mask + 100 * (1-mask) + mn * 18 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_pearl(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [1, 2, 3], [0.4, 0.35, 0.25], seed+100)
    spec[:,:,0] = np.clip(190 * mask + 5 * (1-mask) + mn * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(18 * mask + 100 * (1-mask) + mn * 10 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_chrome(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(255 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(2 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_satin_metal(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    np.random.seed(seed)
    brush = np.random.randn(1, w) * 0.5
    brush = np.tile(brush, (h, 1))
    brush += np.random.randn(h, w) * 0.2
    spec[:,:,0] = np.clip(235 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(65 * mask + 100 * (1-mask) + brush * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_metal_flake(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [1, 2, 4, 8], [0.15, 0.25, 0.35, 0.25], seed+100)
    rf = multi_scale_noise(shape, [1, 3, 6], [0.3, 0.4, 0.3], seed+200)
    spec[:,:,0] = np.clip(240 * mask + 5 * (1-mask) + mf * 50 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(12 * mask + 100 * (1-mask) + rf * 40 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_holographic_flake(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [1, 2, 4, 6], [0.2, 0.3, 0.3, 0.2], seed+100)
    rf = multi_scale_noise(shape, [1, 3], [0.5, 0.5], seed+200)
    spec[:,:,0] = np.clip(245 * mask + 5 * (1-mask) + mf * 45 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(10 * mask + 100 * (1-mask) + rf * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_galaxy_flake(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [1, 2, 4, 6], [0.2, 0.3, 0.3, 0.2], seed+100)
    spec[:,:,0] = np.clip(245 * mask + 5 * (1-mask) + mf * 45 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(6 * mask + 100 * (1-mask) + mf * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_candy(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+100)
    spec[:,:,0] = np.clip(235 * mask + 5 * (1-mask) + mn * 25 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(6 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_chameleon(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed+100)
    spec[:,:,0] = np.clip(240 * mask + 5 * (1-mask) + mn * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(10 * mask + 100 * (1-mask) + mn * 12 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_anodized(shape, mask, seed, sm):
    """FIXED: No more harsh brush artifacts. Smooth grain pattern instead."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    # Smooth fine grain instead of harsh directional brush
    grain = multi_scale_noise(shape, [1, 2, 3], [0.4, 0.35, 0.25], seed+100)
    spec[:,:,0] = np.clip(210 * mask + 5 * (1-mask) + grain * 15 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(50 * mask + 100 * (1-mask) + grain * 10 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0  # No clearcoat
    spec[:,:,3] = 255
    return spec

def spec_prismatic(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [1, 2, 4, 6], [0.2, 0.3, 0.3, 0.2], seed+100)
    rf = multi_scale_noise(shape, [1, 3], [0.5, 0.5], seed+200)
    spec[:,:,0] = np.clip(250 * mask + 5 * (1-mask) + mf * 40 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(8 * mask + 100 * (1-mask) + rf * 25 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_frozen(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed+100)
    spec[:,:,0] = np.clip(225 * mask + 5 * (1-mask) + mn * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(140 * mask + 100 * (1-mask) + mn * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0
    spec[:,:,3] = 255
    return spec

def spec_carbon_fiber(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    weave_size = 6
    cf = (((x // weave_size + y // weave_size) % 2).astype(np.float32) * 0.6 +
          ((np.sin(x * np.pi / weave_size) * np.sin(y * np.pi / weave_size) + 1) / 2) * 0.4)
    spec[:,:,0] = np.clip(50 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(45 * mask + 100 * (1-mask) + cf * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_oil_slick(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed+100)
    spec[:,:,0] = np.clip(250 * mask + 5 * (1-mask) + mn * 15 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(5 * mask + 100 * (1-mask) + mn * 8 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_lava_flake(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [1, 2, 4, 8], [0.15, 0.25, 0.35, 0.25], seed+100)
    spec[:,:,0] = np.clip(240 * mask + 5 * (1-mask) + mf * 45 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(10 * mask + 100 * (1-mask) + mf * 25 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_electric(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [1, 2, 3], [0.4, 0.35, 0.25], seed+100)
    spec[:,:,0] = np.clip(235 * mask + 5 * (1-mask) + mn * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(8 * mask + 100 * (1-mask) + mn * 15 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def spec_frost_bite(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+100)
    rn = multi_scale_noise(shape, [2, 6, 10], [0.3, 0.4, 0.3], seed+200)
    spec[:,:,0] = np.clip(230 * mask + 5 * (1-mask) + mn * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(80 * mask + 100 * (1-mask) + rn * 40 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec


# ================================================================
# PAINT MODIFIERS (SUBTLE - only flake noise, no color shifts)
# ================================================================

def paint_none(paint, shape, mask, seed, pm, bb):
    """No paint modification - spec map does everything."""
    return paint

def paint_subtle_flake(paint, shape, mask, seed, pm, bb):
    """Subtle per-channel flake noise. Does NOT change colors."""
    for c in range(3):
        flake = multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_fine_sparkle(paint, shape, mask, seed, pm, bb):
    """Very fine 1px sparkle dots."""
    flake = multi_scale_noise(shape, [1], [1.0], seed + 50)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_coarse_flake(paint, shape, mask, seed, pm, bb):
    """Bigger flake particles (4-8px) with per-channel color variation."""
    r_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+11)
    g_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+22)
    b_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+33)
    strength = 0.06 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + r_flake * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + g_flake * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + b_flake * strength * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_carbon_darken(paint, shape, mask, seed, pm, bb):
    """Carbon fiber darkening pattern."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    weave_size = 6
    cf = (((x // weave_size + y // weave_size) % 2).astype(np.float32) * 0.6 +
          ((np.sin(x * np.pi / weave_size) * np.sin(y * np.pi / weave_size) + 1) / 2) * 0.4)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - cf * 0.08 * pm * mask, 0, 1)
    return paint

def paint_chrome_brighten(paint, shape, mask, seed, pm, bb):
    """Brighten for chrome rendering."""
    blend = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend) + 0.92 * mask * blend
    return paint


# ================================================================
# FINISH REGISTRY
# ================================================================
# Each finish maps to: (spec_function, paint_function, description)

FINISH_REGISTRY = {
    "gloss":              (spec_gloss,             paint_none,            "Standard glossy clear coat"),
    "matte":              (spec_matte,             paint_none,            "Flat matte finish"),
    "satin":              (spec_satin,             paint_none,            "Satin sheen"),
    "metallic":           (spec_metallic,          paint_subtle_flake,    "Standard metallic with fine flake"),
    "pearl":              (spec_pearl,             paint_fine_sparkle,    "Pearlescent shimmer"),
    "chrome":             (spec_chrome,            paint_chrome_brighten, "Mirror chrome"),
    "satin_metal":        (spec_satin_metal,       paint_subtle_flake,    "Brushed satin metallic"),
    "metal_flake":        (spec_metal_flake,       paint_coarse_flake,    "Visible metal flake particles"),
    "holographic_flake":  (spec_holographic_flake, paint_coarse_flake,    "Rainbow holographic flake"),
    "galaxy_flake":       (spec_galaxy_flake,      paint_coarse_flake,    "Dense rainbow sparkle"),
    "candy":              (spec_candy,             paint_fine_sparkle,    "Deep candy coat"),
    "chameleon":          (spec_chameleon,         paint_subtle_flake,    "Color-shift chameleon"),
    "anodized":           (spec_anodized,          paint_subtle_flake,    "Anodized aluminum"),
    "prismatic":          (spec_prismatic,         paint_coarse_flake,    "Rainbow prismatic"),
    "frozen":             (spec_frozen,            paint_subtle_flake,    "Frozen matte metallic"),
    "carbon_fiber":       (spec_carbon_fiber,      paint_carbon_darken,   "Carbon fiber weave"),
    "oil_slick":          (spec_oil_slick,         paint_fine_sparkle,    "Oil slick iridescent"),
    "lava_flake":         (spec_lava_flake,        paint_coarse_flake,    "Lava red/gold flake"),
    "electric":           (spec_electric,          paint_subtle_flake,    "Electric shimmer"),
    "frost_bite":         (spec_frost_bite,        paint_subtle_flake,    "Ice crystalline"),
}


# ================================================================
# MASK COMPUTATION
# ================================================================

def compute_mask(scheme, threshold=0.40, softness=0.15):
    """Brightness-based mask: 1.0 = dark areas, 0.0 = bright areas."""
    brightness = scheme[:,:,0]*0.299 + scheme[:,:,1]*0.587 + scheme[:,:,2]*0.114
    low = threshold - softness/2
    high = threshold + softness/2
    mask = np.clip((high - brightness) / (high - low + 1e-10), 0, 1)
    mask_img = Image.fromarray((mask*255).astype(np.uint8))
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=2))
    return np.array(mask_img).astype(np.float32) / 255.0


# ================================================================
# SINGLE FINISH APPLICATION
# ================================================================

def apply_single_finish(scheme_path, finish_name, output_dir, seed=42,
                        threshold=0.40, softness=0.15, iracing_id="23371",
                        intensity="aggressive"):
    """Apply one finish to the whole car (backward compatible with Paint Studio)."""
    os.makedirs(output_dir, exist_ok=True)

    scheme_img = Image.open(scheme_path).convert('RGB')
    scheme = np.array(scheme_img).astype(np.float32) / 255.0
    h, w = scheme.shape[:2]
    shape = (h, w)
    mask = compute_mask(scheme, threshold, softness)

    if finish_name not in FINISH_REGISTRY:
        print(f"  ERROR: Unknown finish '{finish_name}'")
        return None, None

    preset = INTENSITY.get(intensity, INTENSITY["aggressive"])
    pm = preset["paint"]
    sm = preset["spec"]
    bb = preset["bright"]

    spec_fn, paint_fn, desc = FINISH_REGISTRY[finish_name]

    # Generate spec map
    spec = spec_fn(shape, mask, seed, sm)

    # Modify paint (SUBTLY)
    paint = scheme.copy()
    paint = paint_fn(paint, shape, mask, seed, pm, bb)

    paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    # Save
    write_tga_24bit(os.path.join(output_dir, f"car_num_{iracing_id}.tga"), paint_rgb)
    write_tga_32bit(os.path.join(output_dir, f"car_spec_{iracing_id}.tga"), spec)
    Image.fromarray(paint_rgb).save(os.path.join(output_dir, "PREVIEW_paint.png"))
    Image.fromarray(spec).save(os.path.join(output_dir, "PREVIEW_spec.png"))
    Image.fromarray((mask * 255).astype(np.uint8)).save(os.path.join(output_dir, "PREVIEW_mask.png"))

    return paint_rgb, spec


# ================================================================
# MAIN: Generate all 20 finishes for a car
# ================================================================

def generate_all_finishes(scheme_path, output_base, iracing_id="23371",
                          intensity="aggressive", prefix=""):
    """Generate all 20 finishes for a given car paint file."""
    finish_names = list(FINISH_REGISTRY.keys())

    print("=" * 70)
    print("  SHOKKER ENGINE v1.0")
    print(f"  {len(finish_names)} finishes | Intensity: {intensity.upper()}")
    print(f"  FIXED: Minimal paint changes, spec does the work")
    print("=" * 70)

    total_start = time.time()
    count = 0

    for finish_name in finish_names:
        folder = f"{prefix}{finish_name}" if prefix else finish_name
        version_dir = os.path.join(output_base, folder)

        start = time.time()
        print(f"  [{finish_name}]", end="", flush=True)
        paint, spec = apply_single_finish(
            scheme_path, finish_name, version_dir,
            seed=51, threshold=0.40, iracing_id=iracing_id,
            intensity=intensity
        )
        elapsed = time.time() - start
        if paint is not None:
            print(f" ... done ({elapsed:.1f}s)")
            count += 1

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 70}")
    print(f"  ALL {count} FINISHES GENERATED in {total_elapsed:.0f}s!")
    print(f"{'=' * 70}")
    print(f"  Output: {os.path.abspath(output_base)}")


if __name__ == '__main__':
    # Generate all finishes for the Bryant Superman 51 ARCA
    scheme = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\BryantSuperman51 TGA.tga"
    output = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\output\arca51_superman_v2"

    generate_all_finishes(scheme, output, iracing_id="23371",
                          intensity="aggressive", prefix="superman51_")
