# -*- coding: utf-8 -*-
"""
CHROME & MIRROR — 10 bases, each with unique paint_fn + spec_fn
Chrome is fundamentally about REFLECTION. Every technique here models
a different physical phenomenon of how light interacts with highly
reflective metallic surfaces.

Techniques (all different):
  chrome         - Fresnel reflection + environment distortion mapping
  black_chrome   - Smoke absorption gradient + specular peak preservation
  blue_chrome    - Thin-film interference (soap bubble physics on metal)
  red_chrome     - Anodization simulation (oxide layer tinting)
  satin_chrome   - Directional micro-brushing (anisotropic reflection)
  antique_chrome - Patina accumulation + pitting corrosion model
  bullseye_chrome- Concentric ring diffraction pattern
  checkered_chrome- Flag pattern via threshold-modulated reflectance
  dark_chrome    - Exponential darkening with specular highlight preservation
  vintage_chrome - Age-yellowing via UV degradation + chrome pit scatter
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d

# ==================================================================
# CHROME — Fresnel reflection + environment distortion
# Real chrome acts as a curved mirror. We simulate the warped
# reflections by distorting the paint buffer through a noise-based
# normal map, then adding Fresnel-modulated brightness.
# ==================================================================

def paint_chrome_mirror(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 100)
    base = paint.copy()

    # Environment distortion via displacement mapping
    # Noise as a "normal map" that warps reflected image
    disp_x = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 1)
    disp_y = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 2)
    # Convert to pixel offsets (subtle — chrome is smooth)
    ox = ((disp_x - 0.5) * 6.0).astype(int)
    oy = ((disp_y - 0.5) * 6.0).astype(int)

    # Warp the paint buffer (reflected environment)
    yy, xx = np.mgrid[0:h, 0:w]
    sy = np.clip(yy + oy, 0, h - 1)
    sx = np.clip(xx + ox, 0, w - 1)
    warped = base[sy, sx, :]

    # Fresnel: reflectance increases at grazing angles (edges)
    # Simulate with mask edge proximity
    from PIL import Image as _Img, ImageFilter as _Filt
    mask_blur = np.array(_Img.fromarray((mask * 255).astype(np.uint8)).filter(
        _Filt.GaussianBlur(radius=max(h // 32, 3))
    )).astype(np.float32) / 255.0
    fresnel = np.clip((mask - mask_blur * 0.95) * 5.0, 0, 1)

    # Chrome = desaturated + bright + warped reflection
    gray = warped.mean(axis=2, keepdims=True)
    chrome_color = np.clip(gray * 0.85 + warped * 0.15, 0, 1)
    # Fresnel boost at edges
    chrome_color = np.clip(chrome_color + fresnel[:,:,np.newaxis] * 0.15, 0, 1)

    effect = chrome_color.astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.6 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_chrome_mirror(shape, seed, sm, base_m, base_r):
    """Pure chrome: near-max metallic, near-zero roughness, slight
    variation from the environment distortion map."""
    h, w = shape[:2] if len(shape) > 2 else shape
    disp = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 1)
    M = np.clip(245.0 + disp * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(2.0 + disp * 8.0 * sm, 15, 255)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat chrome
    return M, R, CC

# ==================================================================
# BLACK CHROME — Smoke absorption gradient
# Black chrome is chrome with a dark tint layer. Light enters the
# tint, gets partially absorbed (Beer-Lambert), reflects off chrome
# underneath, passes through tint again. Double-pass absorption
# makes it very dark but preserves specular highlights.
# ==================================================================

def paint_black_chrome_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Micro-texture for absorption variation
    micro = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.4, 0.3], seed + 10)

    # Beer-Lambert double-pass through tinted layer
    # Absorption coefficient varies with micro-texture
    alpha = 2.5 + micro * 0.8  # strong absorption
    transmitted = np.exp(-alpha * 2.0)  # double pass (in + out)

    # Chrome reflection underneath: desaturated bright
    gray = base.mean(axis=2, keepdims=True)
    chrome_under = np.clip(gray * 0.9 + base * 0.1, 0, 1)

    # Apply absorption — dark with preserved specular peaks
    effect = np.clip(chrome_under * transmitted[:,:,np.newaxis], 0, 1)

    # Specular highlight preservation: brightest areas punch through more
    highlight = np.clip((gray[:,:,0] - 0.5) * 2.0, 0, 1)
    effect = np.clip(effect + highlight[:,:,np.newaxis] * 0.08, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.3 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_black_chrome(shape, seed, sm, base_m, base_r):
    """Black chrome: max metallic, very low roughness, no clearcoat.
    Absorption layer doesn't change metallic/roughness — it's a tint."""
    h, w = shape[:2] if len(shape) > 2 else shape
    micro = multi_scale_noise((h, w), [2, 4, 8], [0.3, 0.4, 0.3], seed + 10)
    M = np.clip(248.0 + micro * 7.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(3.0 + micro * 6.0 * sm, 15, 255)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat black chrome
    return M, R, CC

# ==================================================================
# BLUE CHROME — Thin-film interference (soap bubble physics on metal)
# A nanometer-thin oxide layer on chrome creates wavelength-dependent
# interference. Blue is constructive at ~450nm film thickness.
# The color shifts with viewing angle (thicker apparent path at edges).
# ==================================================================

def _hsv_to_rgb(h, s, v):
    """Inline HSV→RGB for thin-film interference. h in degrees [0,360)."""
    h = h % 360.0
    c = v * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = v - c
    if h < 60:   r, g, b = c, x, 0.0
    elif h < 120: r, g, b = x, c, 0.0
    elif h < 180: r, g, b = 0.0, c, x
    elif h < 240: r, g, b = 0.0, x, c
    elif h < 300: r, g, b = x, 0.0, c
    else:         r, g, b = c, 0.0, x
    return (r + m, g + m, b + m)


def paint_blue_chrome_v2(paint, shape, mask, seed, pm, bb):
    """Blue chrome: real thin-film interference simulation.
    Per-pixel FBM film thickness → hue LUT (blue→purple→gold→green-blue)
    blended 50/50 with chrome base. Creates iridescent oil-slick-on-chrome look."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Chrome base — desaturated, bright (mirror substrate)
    gray = base.mean(axis=2, keepdims=True)
    chrome_base = np.clip(gray * 0.88 + base * 0.12, 0, 1)

    # 2-octave FBM film thickness map: 0.3 – 1.0
    n1 = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 71)
    n2 = multi_scale_noise((h, w), [4,  8], [0.5, 0.5], seed + 72)
    thickness = np.clip(0.3 + (n1 * 0.5 + n2 * 0.5) * 0.7, 0.3, 1.0).astype(np.float32)

    # Thin-film hue LUT: thickness → hue (degrees)
    # 0.3→blue(240), 0.5→purple(280), 0.7→gold(50), 1.0→green-blue(180)
    # Piecewise linear interpolation across four stops
    t = thickness
    hue = np.where(t < 0.5,
                   240.0 + (t - 0.3) / 0.2 * 40.0,      # 240→280 (blue→purple)
                   np.where(t < 0.7,
                            280.0 + (t - 0.5) / 0.2 * (-230.0),  # 280→50 (purple→gold, wraps)
                            50.0  + (t - 0.7) / 0.3 * 130.0))    # 50→180 (gold→green-blue)
    hue = hue.astype(np.float32) % 360.0

    # Convert hue map to RGB (vectorised)
    # S=0.7, V=0.90 for vivid but not over-saturated thin-film color
    S = np.float32(0.70)
    V = np.float32(0.90)
    c_arr  = V * S
    h60    = (hue / 60.0) % 2.0
    x_arr  = c_arr * (1.0 - np.abs(h60 - 1.0))
    m_arr  = V - c_arr
    hi     = (hue / 60.0).astype(np.int32) % 6

    tf_r = np.where(hi == 0, c_arr, np.where(hi == 1, x_arr, np.where(hi == 2, m_arr,
           np.where(hi == 3, m_arr, np.where(hi == 4, x_arr, c_arr))))) + m_arr
    tf_g = np.where(hi == 0, x_arr, np.where(hi == 1, c_arr, np.where(hi == 2, c_arr,
           np.where(hi == 3, x_arr, np.where(hi == 4, m_arr, m_arr))))) + m_arr
    tf_b = np.where(hi == 0, m_arr, np.where(hi == 1, m_arr, np.where(hi == 2, x_arr,
           np.where(hi == 3, c_arr, np.where(hi == 4, c_arr, x_arr))))) + m_arr
    thin_film = np.stack([tf_r, tf_g, tf_b], axis=-1).astype(np.float32)

    # Lerp: 50% chrome base + 50% thin-film color
    effect = np.clip(chrome_base * 0.5 + thin_film * 0.5, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.4 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_blue_chrome(shape, seed, sm, base_m, base_r):
    """Blue chrome spec: spatially varied via FBM — still near-mirror but not flat.
    M: 220-255 (very metallic), R: 2-8 (near-mirror), CC: 14-18."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_blue_chrome_v2: seed+71 [8,16] and seed+72 [4,8]
    noise = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 71)
    M  = np.clip(220.0 + noise * 35.0, 0, 255).astype(np.float32)
    R  = np.clip(2.0   + noise *  6.0, 15, 255)
    CC = np.clip(14.0  + noise *  4.0, 0,  16).astype(np.float32)
    return M, R, CC

# ==================================================================
# RED CHROME — Anodization simulation (oxide layer tinting)
# Anodized chrome has a controlled oxide layer that absorbs specific
# wavelengths. Red anodization absorbs green and blue, transmits red.
# The oxide thickness creates subtle depth variations.
# ==================================================================

def paint_red_chrome_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()

    # Anodization depth map — thicker = more saturated red
    anod_depth = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 30)

    # Chrome reflectance base
    gray = base.mean(axis=2, keepdims=True)
    chrome_base = np.clip(gray * 0.9, 0, 1)

    # Selective absorption: oxide absorbs G and B proportional to depth
    # Red transmits through, G and B get absorbed exponentially
    absorb_g = np.exp(-anod_depth * 3.5)  # strong green absorption
    absorb_b = np.exp(-anod_depth * 5.0)  # even stronger blue absorption

    effect_r = np.clip(chrome_base[:,:,0] * 0.85 + 0.1, 0, 1)
    effect_g = np.clip(chrome_base[:,:,0] * absorb_g * 0.3, 0, 1)
    effect_b = np.clip(chrome_base[:,:,0] * absorb_b * 0.15, 0, 1)
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.5 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_red_chrome(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    anod = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 30)
    M = np.clip(240.0 + anod * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + anod * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat red chrome
    return M, R, CC


# ==================================================================
# SATIN CHROME — Directional micro-brushing (anisotropic reflection)
# Satin chrome has been brushed in one direction, creating parallel
# micro-grooves that scatter light perpendicular to the brush direction.
# This is physically anisotropic — NOT random roughness.
# ==================================================================

def paint_satin_chrome_v2(paint, shape, mask, seed, pm, bb):
    """Satin chrome: silky directional sheen, subtle groove (not heavy stripes)."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 40)
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Very subtle directional variation (silk, not stripy)
    groove = np.sin(y * 0.8 + rng.rand() * 6.28) * 0.5 + 0.5
    grooves = np.clip(groove[:, :, np.newaxis], 0, 1).astype(np.float32)
    gray = base.mean(axis=2, keepdims=True)
    satin_base = np.clip(gray * 0.88 + base * 0.12, 0, 1)
    # Very gentle modulation (0.96–1.04)
    effect = np.clip(satin_base * (0.96 + grooves * 0.08), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_satin_chrome(shape, seed, sm, base_m, base_r):
    """Satin chrome: high metallic, R with directional horizontal brush-grain anisotropy.
    Matches paint_satin_chrome_v2's sin(y*0.8) groove direction — horizontal brush lines
    scatter light perpendicular to brush direction (anisotropic roughness variation).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    # MARRIED to paint_satin_chrome_v2: seed+40 (same groove RNG)
    rng = np.random.RandomState(seed + 40)
    # Horizontal brush lines: per-row low-freq base + fine per-pixel scatter
    brush_row = rng.randn(h, 1).astype(np.float32)          # direction: constant across row
    brush_px  = rng.randn(h, w).astype(np.float32) * 0.3    # micro-texture within lines
    brush = brush_row + brush_px                              # broadcasts to (h, w)
    # R: base 45, ±(10 + sm*8) directional anisotropy, clamped to satin range [15, 85]
    amplitude = 10.0 + sm * 8.0
    R  = np.clip(45.0 + brush * amplitude, 15.0, 85.0).astype(np.float32)
    M  = np.full((h, w), 250.0, dtype=np.float32)
    CC = np.full((h, w), 40.0,  dtype=np.float32)
    return M, R, CC


# ==================================================================
# ANTIQUE CHROME — Patina accumulation + pitting corrosion
# Old chrome develops pits where the plating has worn through, and
# dark patina accumulates in low spots. Uses Voronoi-like cell
# pattern for pit locations and diffusion for patina spread.
# ==================================================================

def paint_antique_chrome_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 50)
    base = paint.copy()

    # Chrome base — slightly warm/yellow (aged)
    gray = base.mean(axis=2, keepdims=True)
    chrome_aged = np.clip(gray * 0.75, 0, 1)
    chrome_aged = np.stack([
        np.clip(chrome_aged[:,:,0] + 0.06, 0, 1),  # warm
        np.clip(chrome_aged[:,:,0] + 0.04, 0, 1),
        np.clip(chrome_aged[:,:,0] - 0.02, 0, 1),  # slightly cool shadows
    ], axis=-1)
    # Pitting: random point scatter simulating corrosion pits
    pit_map = np.zeros((h, w), dtype=np.float32)
    n_pits = 200 + (seed % 100)
    for _ in range(n_pits):
        py, px = rng.randint(0, h), rng.randint(0, w)
        pr = rng.randint(1, max(2, h // 256))
        pit_map[max(0,py-pr):min(h,py+pr), max(0,px-pr):min(w,px+pr)] = rng.uniform(0.3, 1.0)

    # Patina spread: blur the pit map to simulate oxidation creep
    from PIL import Image as _Img, ImageFilter as _Filt
    patina = np.array(_Img.fromarray((pit_map * 255).astype(np.uint8)).filter(
        _Filt.GaussianBlur(radius=max(h // 128, 2))
    )).astype(np.float32) / 255.0

    # Patina color: dark greenish-brown
    patina_color = np.stack([
        np.full((h,w), 0.12, dtype=np.float32),
        np.full((h,w), 0.10, dtype=np.float32),
        np.full((h,w), 0.06, dtype=np.float32),
    ], axis=-1)

    effect = np.clip(chrome_aged * (1.0 - patina[:,:,np.newaxis] * 0.7) +
                     patina_color * patina[:,:,np.newaxis] * 0.5, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_antique_chrome(shape, seed, sm, base_m, base_r):
    """Pitted areas lose metallic and gain roughness. Clean chrome areas stay shiny."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 50)
    pit_map = np.zeros((h, w), dtype=np.float32)
    n_pits = 200 + (seed % 100)
    for _ in range(n_pits):
        py, px = rng.randint(0, h), rng.randint(0, w)
        pr = rng.randint(1, max(2, h // 256))
        pit_map[max(0,py-pr):min(h,py+pr), max(0,px-pr):min(w,px+pr)] = rng.uniform(0.3, 1.0)
    from PIL import Image as _Img, ImageFilter as _Filt
    patina = np.array(_Img.fromarray((pit_map * 255).astype(np.uint8)).filter(
        _Filt.GaussianBlur(radius=max(h // 128, 2))
    )).astype(np.float32) / 255.0
    # Corroded spots: less metallic, much rougher
    M = np.clip(220.0 - patina * 120.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + patina * 160.0 * sm, 15, 255)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat antique chrome
    return M, R, CC


# ==================================================================
# BULLSEYE CHROME — Concentric ring diffraction pattern
# Creates target/bullseye patterns from circular wave interference.
# Like the rings you see on a freshly polished chrome hubcap
# from the rotational polishing process.
# ==================================================================
def paint_bullseye_chrome_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 60)
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Multiple bullseye centers (polishing contact points)
    n_centers = 3 + (seed % 3)
    rings = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_centers):
        cy = rng.uniform(0.2, 0.8) * h
        cx = rng.uniform(0.2, 0.8) * w
        dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
        # Concentric rings from radial sine wave
        freq = rng.uniform(0.15, 0.3)
        ring = np.sin(dist * freq) * 0.5 + 0.5
        # Rings fade with distance from center
        fade = np.exp(-dist / (max(h, w) * 0.5))
        rings = np.clip(rings + ring * fade, 0, 1)

    rings = np.clip(rings / max(n_centers * 0.4, 1), 0, 1).astype(np.float32)

    # Chrome base
    gray = base.mean(axis=2, keepdims=True)
    chrome_base = np.clip(gray * 0.85 + 0.1, 0, 1)

    # Rings modulate chrome brightness
    effect = np.clip(chrome_base * (0.7 + rings[:,:,np.newaxis] * 0.3), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.5 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_bullseye_chrome(shape, seed, sm, base_m, base_r):
    """Ring grooves create directional roughness variation."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 60)
    y, x = get_mgrid((h, w))
    rings = np.zeros((h, w), dtype=np.float32)
    for _ in range(3 + (seed % 3)):
        cy, cx = rng.uniform(0.2, 0.8) * h, rng.uniform(0.2, 0.8) * w
        dist = np.sqrt((y - cy)**2 + (x - cx)**2)
        ring = np.sin(dist * rng.uniform(0.15, 0.3)) * 0.5 + 0.5
        rings = np.clip(rings + ring * np.exp(-dist / (max(h,w)*0.5)), 0, 1)
    rings = np.clip(rings / max((3 + seed % 3) * 0.4, 1), 0, 1)
    M = np.clip(250.0 + rings * 5.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(3.0 + rings * 15.0 * sm, 15, 255)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat bullseye chrome
    return M, R, CC


# ==================================================================
# CHECKERED CHROME — Flag pattern via threshold-modulated reflectance
# Racing checkered flag pattern built from coordinate-space modular
# arithmetic. Chrome squares alternate with dark matte squares.
# ==================================================================
def paint_checkered_chrome_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Checker size scales with canvas
    cell = max(h // 16, 4)
    # Integer division creates checker grid
    check_y = (y // cell).astype(int)
    check_x = (x // cell).astype(int)
    checker = ((check_y + check_x) % 2).astype(np.float32)

    # Chrome squares: bright, desaturated
    gray = base.mean(axis=2, keepdims=True)
    chrome_sq = np.clip(gray * 0.85 + 0.12, 0, 1)
    # Dark squares: very dark, slight warmth
    dark_sq = np.clip(gray * 0.08 + 0.02, 0, 1)
    dark_sq = np.concatenate([dark_sq, dark_sq * 0.95, dark_sq * 0.9], axis=-1)

    # Blend based on checker pattern
    effect = (chrome_sq * checker[:,:,np.newaxis] +
              dark_sq * (1.0 - checker[:,:,np.newaxis])).astype(np.float32)

    # Subtle edge softening at checker boundaries (anti-alias)
    from PIL import Image as _Img, ImageFilter as _Filt
    soft = np.array(_Img.fromarray((checker * 255).astype(np.uint8)).filter(
        _Filt.GaussianBlur(radius=1)
    )).astype(np.float32) / 255.0
    effect = np.clip(chrome_sq * soft[:,:,np.newaxis] +
                     dark_sq * (1.0 - soft[:,:,np.newaxis]), 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.45 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_checkered_chrome(shape, seed, sm, base_m, base_r):
    """Chrome squares: max metallic, zero roughness. Dark squares: low metallic, high roughness."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    cell = max(h // 16, 4)
    checker = (((y // cell).astype(int) + (x // cell).astype(int)) % 2).astype(np.float32)
    M = np.clip(checker * 250.0 + (1.0 - checker) * 30.0, 0, 255).astype(np.float32)
    R = np.clip(checker * 3.0 + (1.0 - checker) * 180.0 * sm, 15, 255)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat checkered chrome
    return M, R, CC


# ==================================================================
# DARK CHROME — Exponential darkening + specular highlight preservation
# PVD (Physical Vapor Deposition) dark chrome. The metallic layer is
# thinner than regular chrome, absorbing more light. But specular
# peaks still punch through. Uses a gamma/power curve approach.
# ==================================================================

def paint_dark_chrome_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # PVD thickness variation
    pvd_thick = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 80)

    # Chrome base — expand to 3 channels
    gray = base.mean(axis=2)
    chrome_base = np.clip(gray * 0.85 + 0.08, 0, 1)

    # Power curve darkening: gamma > 1 crushes midtones while
    # preserving highlights (specular peaks punch through)
    gamma = 2.8 + pvd_thick * 0.6  # 2.8-3.4 gamma
    darkened = np.power(np.clip(chrome_base, 0.001, 1.0), gamma)

    # Slight cool tint (dark chrome has a blue-gray character)
    effect_r = darkened
    effect_g = darkened
    effect_b = np.clip(darkened * 1.08, 0, 1)  # subtle blue
    effect = np.stack([effect_r, effect_g, effect_b], axis=-1)
    effect = effect.astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_dark_chrome(shape, seed, sm, base_m, base_r):
    """Thin PVD layer: still metallic but slightly less than pure chrome.
    Roughness slightly elevated from thinner deposition."""
    h, w = shape[:2] if len(shape) > 2 else shape
    pvd = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 80)
    M = np.clip(230.0 + pvd * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(8.0 + pvd * 15.0 * sm, 15, 255)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat dark chrome
    return M, R, CC

# ==================================================================
# VINTAGE CHROME — UV yellowing + pit scatter
# Classic car chrome that has aged gracefully. UV exposure causes
# a warm yellow shift. Micro-pits from decades of use scatter
# light slightly, reducing sharpness. Different from antique —
# this is dignified aging, not corrosion. Think 1957 Bel Air bumper.
# ==================================================================

def paint_vintage_chrome_v2(paint, shape, mask, seed, pm, bb):
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 90)
    base = paint.copy()

    # Chrome base — slightly warm from UV yellowing
    gray = base.mean(axis=2, keepdims=True)
    chrome_base = np.clip(gray * 0.82, 0, 1)

    # UV yellowing gradient — more yellowing on sun-exposed areas (top)
    y, x = get_mgrid((h, w))
    yn = y / max(h - 1, 1)
    uv_exposure = np.clip(1.0 - yn * 0.6, 0.4, 1.0)  # Top gets more UV

    # Age noise — irregular yellowing patches
    age_noise = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 91)

    # Yellow shift: R stays, G slight warm, B drops
    yellow_amount = uv_exposure * (0.5 + age_noise * 0.5)
    effect_r = np.clip(chrome_base[:,:,0] + yellow_amount * 0.08, 0, 1)
    effect_g = np.clip(chrome_base[:,:,0] + yellow_amount * 0.04, 0, 1)
    effect_b = np.clip(chrome_base[:,:,0] - yellow_amount * 0.06, 0, 1)
    # Micro-pit scatter — slight haziness from decades of tiny impacts
    pit_scatter = rng.rand(h, w).astype(np.float32)
    # Blur to simulate scatter (pits are sub-pixel, effect is diffuse)
    from PIL import Image as _Img, ImageFilter as _Filt
    scatter = np.array(_Img.fromarray((pit_scatter * 255).astype(np.uint8)).filter(
        _Filt.GaussianBlur(radius=max(h // 512, 1))
    )).astype(np.float32) / 255.0

    effect = np.stack([effect_r, effect_g, effect_b], axis=-1).astype(np.float32)
    # Scatter slightly reduces contrast
    effect = np.clip(effect * (0.92 + scatter[:,:,np.newaxis] * 0.08), 0, 1)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(
        base * (1.0 - mask[:,:,np.newaxis] * blend) +
        effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.45 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_vintage_chrome(shape, seed, sm, base_m, base_r):
    """Aged chrome: still metallic but roughness elevated from micro-pitting.
    UV damage doesn't change metallic/roughness much, just color."""
    h, w = shape[:2] if len(shape) > 2 else shape
    age = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 91)
    rng = np.random.RandomState(seed + 90)
    pits = rng.rand(h, w).astype(np.float32)
    M = np.clip(235.0 + age * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(12.0 + pits * 20.0 * sm + age * 10.0, 15, 255)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat vintage chrome
    return M, R, CC