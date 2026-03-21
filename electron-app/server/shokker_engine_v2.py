"""
Shokker Engine v2.0 - COLOR-BASED Zone Detection & Finish Application
======================================================================
BREAKTHROUGH: Uses actual pixel color analysis to create per-zone masks.

TABLE OF CONTENTS - Use these line numbers to jump to sections:
================================================================
  L55   Imports & re-exports (engine.utils, engine.core, engine.spec_paint, ...)
  L95   Spec Map Generators (spec_gloss, spec_chrome, spec_aurora, ...)
  L300  Paint Modifiers (paint_none, paint_carbon_darken, paint_lava_glow, ...)
  L420  FINISH_REGISTRY (legacy mode - maps finish names to spec+paint functions)
  L465  Texture Functions (texture_carbon_fiber, texture_hex_mesh, ...)
  L1027 Base Material Helpers & v5.5 SHOKK additions
  L1887 SHOKK Series - Upgraded + New Boundary-Pushing Patterns
  L3140 BASE_REGISTRY dict
  L3305 PATTERN_REGISTRY dict (~230 entries)
  L3538 Chameleon/Prizm stubs + module loading
  L3596 MONOLITHIC_REGISTRY dict
  L3664 Chameleon/Prizm module overrides (V5 extracted module loading)
  L3723 Expansion imports (24K, Color Mono, Paradigm, Fusions)
  L3767 render_generic_finish import
  L3776 Dual Layer Base system delegates (overlay_pattern_on_spec, etc.)
  L3949 build_multi_zone - THE CORE multi-zone rendering pipeline
  L4824 preview_render - quick preview rendering
  L5308 apply_single_finish, apply_composed_finish
  L5402 build_helmet_spec, build_suit_spec, build_matching_set
  L6068 apply_wear - post-processing wear/age effects
  L6161 build_export_package
  L6246 generate_gradient_mask, generate_night_variant
  L6334 full_render_pipeline
  L6460 if __name__ == '__main__' (example usage)
================================================================
"""

def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint

import numpy as np
from PIL import Image, ImageFilter
import struct
import os
import json
import time

from engine.utils import write_tga_32bit, write_tga_24bit, get_mgrid, generate_perlin_noise_2d, perlin_multi_octave
from engine.core import (
    hsv_to_rgb_vec, rgb_to_hsv_array, INTENSITY, _INTENSITY_SCALE,
    analyze_paint_colors, build_zone_mask, COLOR_WORD_MAP, parse_color_description,
    multi_scale_noise, _sample_zone_color,
    _resize_array, _tile_fractional, _crop_center_array, _scale_pattern_output,
    _rotate_array, _rotate_pattern_tex, _rotate_single_array, _compute_zone_auto_scale,
)

# (TGA + noise moved to engine.utils)
# (Color/mask/intensity + multi_scale_noise moved to engine.core)
# (Standard spec_/paint_ in engine.spec_paint - re-export for BASE_REGISTRY/compose)
from engine import spec_paint as _spec_paint
for _n in dir(_spec_paint):
    if _n.startswith("spec_") or _n.startswith("paint_") or _n == "_forged_carbon_chunks":
        globals()[_n] = getattr(_spec_paint, _n)
# (Color shift cs_* in engine.color_shift - re-export for MONOLITHIC_REGISTRY)
from engine import color_shift as _cs_mod
for _n in dir(_cs_mod):
    if _n.startswith("spec_cs_") or _n.startswith("paint_cs_"):
        globals()[_n] = getattr(_cs_mod, _n)
# (Compose: full implementation in engine.compose - re-export for callers)
from engine.compose import (
    compose_finish, compose_finish_stacked, compose_paint_mod, compose_paint_mod_stacked,
    _get_pattern_mask, _apply_spec_blend_mode, _apply_hsb_adjustments,
)


def _engine_rot_debug(msg):
    """No-op debug hook for rotation/build path logging. Set to print() when debugging."""
    pass


# ================================================================
# SPEC MAP GENERATORS (identical to v1 - proven working)
# ================================================================

# CHAMELEON v5 - COORDINATED DUAL-MAP COLOR SHIFT SYSTEM
#
# THE SHOKKER INNOVATION: Paint and spec are generated from the
# SAME master field, creating mathematically coordinated behavior:
#
# LAYER 1: Panel direction field (macro color ramp)
# LAYER 2: Multi-stop thin-film color ramp (physically motivated)
# LAYER 3: Voronoi micro-flake texture (per-flake hue variation)
# LAYER 4: Coordinated spec - spatially varied M/R/CC:
#   - Metallic INVERSELY correlated with field (darker paint = more metal)
#   - Roughness micro-varied for per-flake reflection differences
#   - Clearcoat OPPOSING metallic for dual-layer white flash competition
# LAYER 5: Metallic brightness compensation for iRacing PBR darkening
#
# This is NOT a gradient with flat spec. This is genuine differential
# Fresnel behavior exploiting iRacing's PBR pipeline.
# ================================================================



# ================================================================
# CHAMELEON V5 FUNCTIONS - EXTRACTED TO engine/chameleon.py
# ================================================================
# The chameleon v5 paint and spec functions are now in engine/chameleon.py.
# They are imported and override this stub at the bottom of this file.
# To edit chameleon functions: open engine/chameleon.py
# ================================================================


# ================================================================
# PRIZM V4 FUNCTIONS - EXTRACTED TO engine/prizm.py
# ================================================================
# The prizm v4 paint and spec functions are now in engine/prizm.py.
# They are imported and override this stub at the bottom of this file.
# To edit prizm functions: open engine/prizm.py
# ================================================================


# ================================================================
# v4.0 NEW MONOLITHICS (Glitch, Cel Shade, Thermochromic, Aurora)
# ================================================================

def spec_glitch(shape, mask, seed, sm):
    """Glitch - digital corruption: scanlines + channel offset zones."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    np.random.seed(seed + 900)
    # Base: medium metallic, low roughness
    M_arr = np.full((h, w), 120.0)
    R_arr = np.full((h, w), 40.0)
    # Scanlines: every 4th row = high roughness
    scanline = (np.arange(h) % 4 < 1).astype(np.float32)[:, np.newaxis]
    scanline = np.broadcast_to(scanline, (h, w)).astype(np.float32)
    R_arr = R_arr + scanline * 80 * sm
    # Random horizontal tear bands
    for _ in range(max(3, h // 100)):
        y_start = np.random.randint(0, h)
        band_h = np.random.randint(2, 8)
        tear_offset = np.random.randint(-40, 40)
        y_end = min(h, y_start + band_h)
        M_arr[y_start:y_end, :] = np.clip(M_arr[y_start:y_end, :] + tear_offset, 0, 255)
    spec[:,:,0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_glitch(paint, shape, mask, seed, pm, bb):
    """Glitch paint - RGB channel offset + tear bands."""
    h, w = shape
    np.random.seed(seed + 901)
    # RGB channel offset: shift R and B channels horizontally
    shift_r = int(np.random.randint(3, 8) * pm)
    shift_b = int(np.random.randint(-8, -3) * pm)
    r_shifted = np.roll(paint[:,:,0], shift_r, axis=1)
    b_shifted = np.roll(paint[:,:,2], shift_b, axis=1)
    paint[:,:,0] = paint[:,:,0] * (1 - 0.4 * pm * mask) + r_shifted * 0.4 * pm * mask
    paint[:,:,2] = paint[:,:,2] * (1 - 0.4 * pm * mask) + b_shifted * 0.4 * pm * mask
    # Horizontal tear bands
    for _ in range(max(3, h // 100)):
        y_start = np.random.randint(0, h)
        band_h = np.random.randint(2, 6)
        shift_px = np.random.randint(-20, 20)
        y_end = min(h, y_start + band_h)
        for c in range(3):
            paint[y_start:y_end, :, c] = np.roll(paint[y_start:y_end, :, c], shift_px, axis=1) * mask[y_start:y_end, :] + paint[y_start:y_end, :, c] * (1 - mask[y_start:y_end, :])
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_cel_shade(shape, mask, seed, sm):
    """Cel shade - posterized spec with bold edge outlines."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Simple flat spec - the magic happens in paint
    spec[:,:,0] = np.clip(80 * mask, 0, 255).astype(np.uint8)   # moderate metallic
    spec[:,:,1] = np.clip(60 * mask, 0, 255).astype(np.uint8)   # fairly smooth
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)  # clearcoat
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_cel_shade(paint, shape, mask, seed, pm, bb):
    """Cel shade - posterize paint to flat tones + Sobel edge outlines."""
    h, w = shape
    # Posterize: reduce to 4-5 tone levels
    levels = int(4 + pm)
    for c in range(3):
        channel = paint[:,:,c]
        quantized = np.floor(channel * levels) / levels
        paint[:,:,c] = channel * (1 - 0.7 * pm * mask) + quantized * 0.7 * pm * mask
    # Sobel edge detection for black outlines
    from PIL import ImageFilter
    gray = (paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114)
    gray_img = Image.fromarray((gray * 255).clip(0, 255).astype(np.uint8))
    edges = np.array(gray_img.filter(ImageFilter.FIND_EDGES)).astype(np.float32) / 255.0
    # Threshold edges to make crisp outlines
    outline = np.where(edges > 0.15, 1.0, 0.0) * 0.6 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - outline * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_thermochromic(shape, mask, seed, sm):
    """Thermochromic - noise-based 'heat zones' with variable metallic."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    heat = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 920)
    heat = np.clip((heat + 0.5) * 1.2, 0, 1)
    # Hot zones = high metallic, cool zones = low metallic
    M = 50 + heat * 180 * sm
    R = 30 + (1 - heat) * 80 * sm
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_thermochromic(paint, shape, mask, seed, pm, bb):
    """Thermochromic paint - maps noise to thermal colormap (blue→green→yellow→red)."""
    h, w = shape
    heat = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 920)
    heat = np.clip((heat + 0.5) * 1.2, 0, 1)
    # Thermal colormap: blue(cold) → green → yellow → red(hot)
    # H maps: 240°(blue) → 120°(green) → 60°(yellow) → 0°(red)
    hue = (1.0 - heat) * 240.0 / 360.0  # 0.667 → 0.0
    sat = np.full_like(heat, 0.8)
    val = np.full_like(heat, 0.7)
    r_th, g_th, b_th = hsv_to_rgb_vec(hue, sat, val)
    blend = 0.55 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r_th * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g_th * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b_th * blend * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_aurora(shape, mask, seed, sm):
    """Aurora - flowing borealis bands with high metallic shimmer."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Flowing sine wave bands
    wave = np.sin(yf * 0.02 + xf * 0.005) * 0.5 + np.sin(yf * 0.008 - xf * 0.012) * 0.3
    wave = np.clip((wave + 0.5) * 1.2, 0, 1)
    M = 200 + wave * 40 * sm
    R = 10 + (1 - wave) * 30 * sm
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_aurora(paint, shape, mask, seed, pm, bb):
    """Aurora paint - flowing sine-wave color bands (green/cyan/pink)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Multi-directional sine-wave field for flowing aurora bands
    field = (
        np.sin(yf * 0.02 + xf * 0.005) * 0.35 +
        np.sin(yf * 0.008 - xf * 0.012) * 0.35 +
        np.sin((yf * 0.5 + xf) * 0.006) * 0.30
    )
    field = np.clip((field + 0.5) * 1.0, 0, 1)
    # Aurora palette: green → cyan → pink through HSV
    hue = (0.33 + field * 0.5) % 1.0  # green(120°) → pink(300°)
    sat = np.full_like(field, 0.7)
    val = np.full_like(field, 0.65)
    r_au, g_au, b_au = hsv_to_rgb_vec(hue, sat, val)
    blend = 0.5 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r_au * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g_au * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b_au * blend * mask, 0, 1)
    paint = np.clip(paint + bb * 1.2 * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# v5.0 NEW MONOLITHIC FINISHES (4 new)
# ================================================================

def spec_static(shape, mask, seed, sm):
    """Static/TV noise - high-frequency random M+R producing chaotic reflections."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    np.random.seed(seed + 1500)
    noise = np.random.randint(0, 256, (h, w), dtype=np.uint8)
    spec[:,:,0] = np.clip(noise.astype(np.float32) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((255 - noise).astype(np.float32) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def paint_static(paint, shape, mask, seed, pm, bb):
    """Static paint - random B/W pixel noise."""
    h, w = shape
    np.random.seed(seed + 1501)
    noise = np.random.rand(h, w).astype(np.float32)
    gray = noise[:,:,np.newaxis] * np.ones((1, 1, 3))
    blend = 0.35 * pm
    paint = np.clip(paint * (1 - blend * mask[:,:,np.newaxis]) + gray * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def spec_scorched(shape, mask, seed, sm):
    """Scorched - burnt metal with variable roughness and low metallic edges."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    burn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1600)
    burn_val = np.clip(burn * 0.5 + 0.5, 0, 1)
    M = 40 + burn_val * 180  # Low in burnt areas, high in unburnt
    R = 200 - burn_val * 160  # High roughness in burnt areas
    spec[:,:,0] = np.clip(M * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def paint_scorched(paint, shape, mask, seed, pm, bb):
    """Scorched - darkens with orange/brown heat discoloration zones."""
    burn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1600)
    burn_val = np.clip(burn * 0.5 + 0.5, 0, 1)
    dark = burn_val * 0.2 * pm
    paint = np.clip(paint * (1 - dark[:,:,np.newaxis] * mask[:,:,np.newaxis]), 0, 1)
    # Warm tint in burnt areas
    warm = burn_val * 0.06 * pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] + warm * 0.8, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + warm * 0.3, 0, 1)
    return paint

def spec_radioactive(shape, mask, seed, sm):
    """Radioactive - glowing green edges with bright metallic hot spots and radiation glow."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    glow = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1700)
    glow_val = np.clip(glow * 0.5 + 0.5, 0, 1)
    # Edge detection for glowing edges (green glow at contour boundaries)
    edge_noise = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.35, 0.25], seed + 1702)
    edges = np.clip(1.0 - np.abs(edge_noise - 0.5) * 4.0, 0, 1)
    # Hot spots: high metallic at glow peaks AND edges
    M_val = np.clip(80 + glow_val * 140 + edges * 80, 0, 255)
    spec[:,:,0] = np.clip(M_val * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    # R: smooth at glowing edges (reflective), rougher in dark zones
    R_val = np.clip(120 - glow_val * 90 - edges * 60, 0, 255)
    spec[:,:,1] = np.clip(R_val * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    # CC: good clearcoat with slight variation
    CC_val = np.clip(16 + (1 - glow_val) * 15 + (1 - edges) * 10, 16, 255)
    spec[:,:,2] = np.clip(CC_val * mask + 16 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def paint_radioactive(paint, shape, mask, seed, pm, bb):
    """Radioactive - toxic green nuclear glow with glowing edges and radiation pulses."""
    if pm == 0.0:
        return paint
    h, w = shape
    # Radiation wave rings from center
    cy, cx = h / 2.0, w / 2.0
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt(((y - cy) / h)**2 + ((x - cx) / w)**2)
    waves = (np.sin(dist * np.pi * 30) * 0.5 + 0.5) * 0.25
    # Base toxic green glow
    glow = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1700)
    glow_val = np.clip(glow * 0.5 + 0.5, 0, 1)
    # Edge glow effect (green light at surface edges/contours)
    edge_noise = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.35, 0.25], seed + 1702)
    edges = np.clip(1.0 - np.abs(edge_noise - 0.5) * 4.0, 0, 1)
    edge_glow = edges * 0.35
    intensity = (glow_val * 0.5 + waves + edge_glow) * pm * mask
    # Strong toxic green: kill red/blue, boost green hard, extra green at edges
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - intensity * 0.65) + edge_glow * pm * mask * 0.05, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + intensity * 0.55 + edge_glow * pm * mask * 0.25, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - intensity * 0.55) + intensity * 0.06, 0, 1)
    # Hot spots (sparse bright green flecks)
    rng = np.random.RandomState(seed + 1701)
    spots = np.where(rng.random(shape).astype(np.float32) > 0.97, 0.18 * pm, 0.0)
    paint[:,:,1] = np.clip(paint[:,:,1] + spots * mask, 0, 1)
    return paint

def spec_holographic(shape, mask, seed, sm):
    """Holographic full wrap - fine-grained rainbow metallic shifting."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Fine holographic: ~40-60 cycles for visible rainbow bands
    rainbow = (np.sin(y * np.pi * 80 + x * np.pi * 60) * 0.5 + 0.5)
    rainbow2 = (np.sin(y * np.pi * 40 - x * np.pi * 90) * 0.5 + 0.5)
    rainbow = (rainbow + rainbow2) / 2.0
    spec[:,:,0] = np.clip((235 + rainbow * 20) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((4 + rainbow * 50) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def paint_holographic_full(paint, shape, mask, seed, pm, bb):
    """Full holographic - VIVID fine-grained rainbow color shift."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # 4 gratings at different angles - ~40-60 cycles for fine holographic bands
    g1 = (y * 50 + x * 40) % 1.0
    g2 = (y * 30 - x * 60) % 1.0
    g3 = ((y + x) * 45) % 1.0
    g4 = ((y - x * 0.7) * 55) % 1.0
    angle = (g1 + g2 * 0.6 + g3 * 0.4 + g4 * 0.3) / 2.3
    r_holo = np.sin(angle * np.pi * 2) * 0.5 + 0.5
    g_holo = np.sin(angle * np.pi * 2 + 2.094) * 0.5 + 0.5
    b_holo = np.sin(angle * np.pi * 2 + 4.189) * 0.5 + 0.5
    blend = 0.35 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r_holo * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g_holo * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b_holo * blend * mask, 0, 1)
    return paint


FINISH_REGISTRY = {
    # --- STANDARD ---
    "gloss":              (spec_gloss,             paint_none),
    "matte":              (spec_matte,             paint_none),
    "satin":              (spec_satin,             paint_none),
    "metallic":           (spec_metallic,          paint_subtle_flake),
    "pearl":              (spec_pearl,             paint_fine_sparkle),
    "chrome":             (spec_chrome,            paint_chrome_brighten),
    "candy":              (spec_candy,             paint_fine_sparkle),
    # --- METALLIC ---
    "satin_metal":        (spec_satin_metal,       paint_subtle_flake),
    "brushed_titanium":   (spec_brushed_titanium,  paint_brushed_grain),
    "anodized":           (spec_anodized,          paint_subtle_flake),
    "hammered":           (spec_hammered,          paint_hammered_dimples),
    # --- FLAKE ---
    "metal_flake":        (spec_metal_flake,       paint_coarse_flake),
    "holographic_flake":  (spec_holographic_flake, paint_coarse_flake),
    "stardust":           (spec_stardust,          paint_stardust_sparkle),
    # --- EXOTIC ---
    "frozen":             (spec_frozen,            paint_subtle_flake),
    "frost_bite":         (spec_frost_bite,        paint_subtle_flake),
    "carbon_fiber":       (spec_carbon_fiber,      paint_carbon_darken),
    # --- GEOMETRIC ---
    "diamond_plate":      (spec_diamond_plate,     paint_diamond_emboss),
    "dragon_scale":       (spec_dragon_scale,      paint_scale_pattern),
    "hex_mesh":           (spec_hex_mesh,          paint_hex_emboss),
    "ripple":             (spec_ripple,            paint_ripple_reflect),
    # --- EFFECTS ---
    "lightning":          (spec_lightning,          paint_lightning_glow),
    "plasma":             (spec_plasma,            paint_plasma_veins),
    "hologram":           (spec_hologram,          paint_hologram_lines),
    "interference":       (spec_interference,      paint_interference_shift),
    # --- DAMAGE ---
    "battle_worn":        (spec_battle_worn,       paint_scratch_marks),
    "worn_chrome":        (spec_worn_chrome,       paint_patina),
    "acid_wash":          (spec_acid_wash,         paint_acid_etch),
    "cracked_ice":        (spec_cracked_ice,       paint_ice_cracks),
    # --- SPECIAL ---
    "liquid_metal":       (spec_liquid_metal,      paint_liquid_reflect),
    "ember_glow":         (spec_ember_glow,        paint_ember_glow),
    "phantom":            (spec_phantom,           paint_phantom_fade),
    "blackout":           (spec_blackout,          paint_none),
}


# ================================================================
# v3.0 COMPOSITING SYSTEM - Base + Pattern
# ================================================================
# 18 bases x 32 patterns = 576+ combinations

# --- TEXTURE FUNCTIONS (v3.0 PATTERN SHAPE + MODULATION) ---
# Each returns {"pattern_val": 0-1 array, "R_range": float, "M_range": float, "CC": int_or_array}
#
# DESIGN: Patterns provide a SPATIAL SHAPE (pattern_val, 0-1 per pixel) and
# modulation ranges. compose_finish() uses these to create variation WITHIN
# the base material's own M/R values. This way:
#   - Chrome + Carbon Fiber = chrome surface with visible weave in roughness
#   - Matte + Carbon Fiber = matte surface with visible weave in roughness
#   - The base determines the "character", the pattern adds texture
#
# compose_finish() applies: base_R + pattern_val * R_range * sm
#                           base_M + pattern_val * M_range * sm (if M varies)

def texture_carbon_fiber(shape, mask, seed, sm):
    """2x2 twill weave - tight realistic carbon fiber, roughness-only modulation.
    !! DO NOT increase weave_size here - it's intentionally tight (6px) for realism.
    !! Other patterns (kevlar_weave, basket_weave) have their OWN texture functions.
    !! If you need a coarser weave, create a NEW function, don't modify this one."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 6  # Tight weave - real CF has hundreds of tows across a car panel
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Original spec: M=55(flat), R=30+cf*50. Pattern only modulates R via weave shape.
    return {"pattern_val": cf, "R_range": 50.0, "M_range": 25.0, "CC": None}

def texture_kevlar_weave(shape, mask, seed, sm):
    """Kevlar aramid weave - coarser than carbon fiber, visible at preview scale."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 24  # Kevlar weave is visibly coarser than CF
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    kv = twill_cell * horiz + (1 - twill_cell) * vert
    # Slightly softer contrast than CF
    kv = np.clip(kv * 1.15 - 0.08, 0, 1)
    return {"pattern_val": kv, "R_range": 45.0, "M_range": 20.0, "CC": None}

def texture_basket_weave(shape, mask, seed, sm):
    """Basket weave - large over/under blocks, very obvious at any scale."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 36  # Big basket blocks
    # Over-under: 2-wide tow bundles alternate
    bundle_x = (x // weave_size) % 2
    bundle_y = (y // weave_size) % 2
    # Checkerboard of horizontal vs vertical dominance
    checker = (bundle_x ^ bundle_y).astype(np.float32)
    # Within each cell, subtle tow curvature
    cell_x = (x % weave_size) / weave_size
    cell_y = (y % weave_size) / weave_size
    curve_h = np.sin(cell_x * np.pi) * 0.3
    curve_v = np.sin(cell_y * np.pi) * 0.3
    bw = checker * (0.6 + curve_h) + (1 - checker) * (0.4 + curve_v)
    bw = np.clip(bw, 0, 1)
    return {"pattern_val": bw, "R_range": 55.0, "M_range": 30.0, "CC": None}

def texture_forged_carbon(shape, mask, seed, sm):
    """Chopped carbon chunks - both M and R vary per chunk."""
    chunks, fine = _forged_carbon_chunks(shape, seed + 100)
    # Original: M=60+chunks*40, R=25+chunks*50+fine*8
    # Return chunks as pattern, fine noise baked into R_extra
    return {"pattern_val": chunks, "R_range": 50.0, "M_range": 40.0, "CC": None,
            "R_extra": fine * 8.0}  # extra fine noise added to R

def texture_diamond_plate(shape, mask, seed, sm):
    """Raised diamond tread - binary: raised diamonds vs flat surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    diamond_size = 20  # Tighter diamond tread pattern
    dx = (x % diamond_size) - diamond_size / 2
    dy = (y % diamond_size) - diamond_size / 2
    diamond = ((np.abs(dx) + np.abs(dy)) < diamond_size * 0.38).astype(np.float32)
    # Original: diamond(1)=M240/R8, flat(0)=M180/R140
    # Diamond areas are smoother and shinier. Pattern_val=1 means "diamond raised area"
    # R_range is NEGATIVE: diamonds make it smoother (lower R)
    return {"pattern_val": diamond, "R_range": -132.0, "M_range": 60.0, "CC": 0}

def texture_dragon_scale(shape, mask, seed, sm):
    """Hex reptile scales - gradient center=shiny to edge=rough."""
    h, w = shape
    scale_size = 24  # Tighter scales for realistic look
    y, x = get_mgrid((h, w))
    row = y // scale_size
    col = (x + (row % 2) * (scale_size // 2)) // scale_size
    cy = (row + 0.5) * scale_size
    cx = col * scale_size + (row % 2) * (scale_size // 2) + scale_size // 2
    dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (scale_size * 0.55)
    dist = np.clip(dist, 0, 1)
    # Original: center(0)=M255/R3, edge(1)=M120/R160
    # Use (1-dist) as pattern_val: 1=center(shiny), 0=edge(rough)
    center_val = 1.0 - dist
    # R_range negative: more pattern = smoother; M_range positive: more pattern = shinier
    return {"pattern_val": center_val, "R_range": -157.0, "M_range": 135.0, "CC": None}

def texture_hex_mesh(shape, mask, seed, sm):
    """Honeycomb wire grid - binary: open hex centers vs wire frame."""
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 16  # Finer honeycomb mesh
    row = y / (hex_size * 0.866)
    col = x / hex_size
    col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
    row_round = np.round(row)
    col_round = np.round(col_shifted)
    cy = row_round * hex_size * 0.866
    cx = (col_round + 0.5 * (row_round.astype(int) % 2)) * hex_size
    dist = np.sqrt((y - cy)**2 + (x - cx)**2)
    norm_dist = np.clip(dist / (hex_size * 0.45), 0, 1)
    wire = (norm_dist > 0.75).astype(np.float32)
    center = 1.0 - wire
    # Original: center=M255/R5, wire=M100/R160
    # center(1) = shiny/smooth, wire(0) = matte/rough
    return {"pattern_val": center, "R_range": -155.0, "M_range": 155.0, "CC": None}

def texture_ripple(shape, mask, seed, sm):
    """Concentric ring waves - sinusoidal peaks=shiny, valleys=matte."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 100)
    num_origins = int(6 + sm * 4)
    ripple_sum = np.zeros((h, w), dtype=np.float32)
    for _ in range(num_origins):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2).astype(np.float32)
        ring_spacing = rng.uniform(20, 40)
        ripple = np.sin(dist / ring_spacing * 2 * np.pi)
        fade = np.clip(1.0 - dist / (max(h, w) * 0.6), 0, 1)
        ripple_sum += ripple * fade
    rmax = np.abs(ripple_sum).max() + 1e-8
    ring_val = (ripple_sum / rmax + 1.0) * 0.5
    # Original: peak(1)=M240/R5, valley(0)=M140/R90
    return {"pattern_val": ring_val, "R_range": -85.0, "M_range": 100.0, "CC": None}

def texture_hammered(shape, mask, seed, sm):
    """Hand-hammered dimples - dimple centers=smooth, flat areas=rough."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    num_dimples = int(400 * sm)
    dimple_y = rng.randint(0, h, num_dimples).astype(np.float32)
    dimple_x = rng.randint(0, w, num_dimples).astype(np.float32)
    dimple_r = rng.randint(8, 22, num_dimples).astype(np.float32)
    ds = 4
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = (yg * ds).astype(np.float32)
    xg = (xg * ds).astype(np.float32)
    dimple_small = np.zeros((sh, sw), dtype=np.float32)
    for dy, dx, dr in zip(dimple_y, dimple_x, dimple_r):
        y_lo = max(0, int((dy - dr) / ds))
        y_hi = min(sh, int((dy + dr) / ds) + 1)
        x_lo = max(0, int((dx - dr) / ds))
        x_hi = min(sw, int((dx + dr) / ds) + 1)
        if y_hi <= y_lo or x_hi <= x_lo:
            continue
        sub_y = yg[y_lo:y_hi, x_lo:x_hi]
        sub_x = xg[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((sub_y - dy)**2 + (sub_x - dx)**2)
        dimple = np.clip(1.0 - dist / dr, 0, 1) ** 2
        dimple_small[y_lo:y_hi, x_lo:x_hi] = np.maximum(
            dimple_small[y_lo:y_hi, x_lo:x_hi], dimple)
    dimple_img = Image.fromarray((dimple_small * 255).astype(np.uint8))
    dimple_img = dimple_img.resize((w, h), Image.BILINEAR)
    dimple_map = np.array(dimple_img).astype(np.float32) / 255.0
    # Original: dimple(1)=M245/R8, flat(0)=M150/R120
    return {"pattern_val": dimple_map, "R_range": -112.0, "M_range": 95.0, "CC": 0}

def texture_lightning(shape, mask, seed, sm):
    """Forked lightning bolts - bolt paths are bright, bg is dark."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    num_bolts = int(3 + sm * 2)
    for b in range(num_bolts):
        py = rng.randint(0, h // 4)
        px = rng.randint(w // 4, 3 * w // 4)
        thickness = rng.randint(4, 8)
        for step in range(h * 2):
            py += rng.randint(1, 4)
            px += rng.randint(-6, 7)
            if py >= h:
                break
            px = max(0, min(w - 1, px))
            y_lo = max(0, py - thickness)
            y_hi = min(h, py + thickness + 1)
            x_lo = max(0, px - thickness)
            x_hi = min(w, px + thickness + 1)
            bolt_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                bolt_map[y_lo:y_hi, x_lo:x_hi], 1.0)
            if rng.random() < 0.03:
                fork_px, fork_py = px, py
                fork_thick = max(1, thickness // 2)
                fork_dir = rng.choice([-1, 1])
                for _ in range(rng.randint(20, 80)):
                    fork_py += rng.randint(1, 3)
                    fork_px += fork_dir * rng.randint(1, 5)
                    if fork_py >= h or fork_px < 0 or fork_px >= w:
                        break
                    fy_lo = max(0, fork_py - fork_thick)
                    fy_hi = min(h, fork_py + fork_thick + 1)
                    fx_lo = max(0, fork_px - fork_thick)
                    fx_hi = min(w, fork_px + fork_thick + 1)
                    bolt_map[fy_lo:fy_hi, fx_lo:fx_hi] = np.maximum(
                        bolt_map[fy_lo:fy_hi, fx_lo:fx_hi], 0.7)
    bolt_pil = Image.fromarray((bolt_map * 255).astype(np.uint8), 'L')
    bolt_pil = bolt_pil.filter(ImageFilter.GaussianBlur(radius=1.5))
    bolt_map = np.array(bolt_pil).astype(np.float32) / 255.0
    bolt_map = np.clip(bolt_map, 0, 1)
    # Original: bolt(1)=M255/R3, bg(0)=M80/R180
    # bolt_map=1 means bright bolt, 0 means dark background
    return {"pattern_val": bolt_map, "R_range": -177.0, "M_range": 175.0, "CC": None}

def texture_plasma(shape, mask, seed, sm):
    """Branching plasma veins - veins are bright, bg is matte."""
    n1 = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed+100)
    n2 = multi_scale_noise(shape, [1, 3, 6, 12], [0.2, 0.3, 0.3, 0.2], seed+200)
    veins = np.abs(n1 + n2 * 0.5)
    vein_mask_f = np.clip(1.0 - veins * 3.0, 0, 1) ** 2
    # Original: vein(1)=M255/R2, bg(0)=M160/R120
    return {"pattern_val": vein_mask_f, "R_range": -118.0, "M_range": 95.0, "CC": None}

def texture_hologram(shape, mask, seed, sm):
    """Holographic scanlines - visible banding in roughness AND metallic.
    Scanline thickness scales with resolution so bands remain visible at 2048+."""
    h, w = shape
    y = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Scale scanline period: ~80 visible bands across the height
    period = max(6, h // 80)
    half = max(1, period // 2)
    scanline = ((y.astype(int) % period) < half).astype(np.float32)
    # Add a subtle horizontal shimmer wave for holographic feel
    x = np.arange(w, dtype=np.float32).reshape(1, -1)
    shimmer = np.sin(x * 0.03 + y * 0.01) * 0.15 + 0.85
    scanline = np.broadcast_to(scanline, (h, w)).copy() * shimmer
    scanline = np.clip(scanline, 0, 1)
    # Boosted ranges: visible metallic + roughness modulation
    return {"pattern_val": scanline, "R_range": -100.0, "M_range": 60.0, "CC": None}

def texture_interference(shape, mask, seed, sm):
    """TV interference / VHS tracking distortion and static."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 80)
    
    # Base high-frequency TV static
    static = rng.random((h, w)).astype(np.float32)
    
    # Horizontal tracking bands across the height
    scan_y = (y / h) * 30.0 + rng.random() * 10.0
    tracking = np.sin(scan_y) * 0.5 + 0.5
    tracking = np.clip(tracking * 2.0 - 0.5, 0, 1) # sharpen the bands
    
    # Distortion blocks
    block_h = int(h / 15)
    block_y = (y // block_h).astype(np.float32)
    block_noise = np.sin(block_y * 13.7 + seed) * 0.5 + 0.5
    glitch = (block_noise > 0.85).astype(np.float32)
    
    # Combine static with tearing/bands
    pattern = np.clip(static * 0.4 + tracking * 0.4 + glitch * static * 0.8, 0, 1)
    
    return {"pattern_val": pattern, "R_range": -80.0, "M_range": 60.0, "CC": None}

def texture_battle_worn(shape, mask, seed, sm):
    """Scratch damage pattern - variable clearcoat. Uses noise, not geometric pattern."""
    h, w = shape
    mn = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed+100)
    rng = np.random.RandomState(seed + 301)
    scratch_noise = rng.randn(1, w) * 0.6
    scratch_noise = np.tile(scratch_noise, (h, 1))
    scratch_noise += rng.randn(h, w) * 0.3
    cc_noise = np.clip((mn + 0.5) * 16, 0, 16).astype(np.uint8)
    # Battle worn is a noise-based texture that doesn't fit simple pattern_val model.
    # Use composite noise as pattern_val, store raw noise components for R_extra.
    damage = np.clip((np.abs(mn) + np.abs(scratch_noise)) * 0.5, 0, 1)
    return {"pattern_val": damage, "R_range": 80.0, "M_range": 30.0, "CC": cc_noise,
            "R_extra": scratch_noise * 40.0, "M_extra": mn * 15.0}

def texture_acid_wash(shape, mask, seed, sm):
    """Corroded acid etch - variable clearcoat."""
    etch = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    etch_depth = np.clip(np.abs(etch) * 2, 0, 1)
    cc = np.clip(16 * (1 - etch_depth * 0.8), 0, 16).astype(np.uint8)
    # Original: M=200+etch*35, R=60+etch*60. Etch drives everything.
    return {"pattern_val": etch_depth, "R_range": 60.0, "M_range": 35.0, "CC": cc}

def texture_cracked_ice(shape, mask, seed, sm):
    """Frozen crack network - cracks add roughness."""
    h, w = shape
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed+200)
    crack1 = np.exp(-n1**2 * 20)
    crack2 = np.exp(-n2**2 * 20)
    cracks = np.clip(crack1 + crack2, 0, 1)
    # Original: M=230+mn*15 (near flat), R: ice=15, crack=15+cracks*115
    # cracks=1 means crack line = rougher
    return {"pattern_val": cracks, "R_range": 115.0, "M_range": 40.0, "CC": None}

def texture_metal_flake(shape, mask, seed, sm):
    """Coarse metallic flake sparkle - noise-driven M and R variation."""
    mf = multi_scale_noise(shape, [4, 8, 16, 32], [0.1, 0.2, 0.35, 0.35], seed+100)
    rf = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+200)
    # Metal flake has two independent noise fields. Use mf as pattern_val,
    # and store rf as R_extra for independent R noise.
    flake_val = np.clip((mf + 1) * 0.5, 0, 1)  # normalize to 0-1
    return {"pattern_val": flake_val, "R_range": -60.0, "M_range": 50.0, "CC": None,
            "R_extra": rf * 40.0}

def texture_holographic_flake(shape, mask, seed, sm):
    """Prismatic micro-grid flake - grid roughness + sparse bright flakes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    grid_size = 8
    diag1 = np.sin((x + y) * np.pi / grid_size) * 0.5 + 0.5
    diag2 = np.sin((x - y) * np.pi / (grid_size * 1.3)) * 0.5 + 0.5
    holo = diag1 * 0.6 + diag2 * 0.4
    rng = np.random.RandomState(seed + 100)
    sparkle = rng.random((h, w)).astype(np.float32)
    bright_flakes = (sparkle > (1.0 - 0.03 * sm)).astype(np.float32)
    # Original: M=245+flakes*10, R=5+holo*40. Grid modulates R, flakes add M.
    return {"pattern_val": holo, "R_range": -70.0, "M_range": 50.0, "CC": None,
            "M_extra": bright_flakes * 15.0}

def texture_stardust(shape, mask, seed, sm):
    """Deep starfield with multi-sized stars and nebula background."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    star_field = rng.random((h, w)).astype(np.float32)
    
    # Multi-sized stars
    tiny_stars = (star_field > 0.98).astype(np.float32) * 0.4
    med_stars = (star_field > 0.995).astype(np.float32) * 0.7
    large_stars = (star_field > 0.999).astype(np.float32) * 1.0
    stars = np.clip(tiny_stars + med_stars + large_stars, 0, 1)
    
    # Nebula background clouds
    nebula = multi_scale_noise(shape, [4, 8, 16], [0.5, 0.3, 0.2], seed+101)
    nebula = np.clip((nebula + 0.5) * 0.5, 0, 1) * 0.3
    
    pattern = np.clip(stars + nebula, 0, 1)
    return {"pattern_val": pattern, "R_range": 20.0, "M_range": 10.0, "CC": None,
            "R_extra": stars * -80.0, "M_extra": stars * 95.0}


# --- TEXTURE FUNCTIONS: Expansion Pack (14 new patterns) ---

def texture_pinstripe(shape, mask, seed, sm):
    """Thin parallel racing stripes at regular intervals."""
    h, w = shape
    y = np.arange(h).reshape(-1, 1)
    stripe = ((y % 16) < 2).astype(np.float32)
    stripe = np.broadcast_to(stripe, (h, w)).copy()
    # stripe=1 means raised stripe line = smoother/shinier
    return {"pattern_val": stripe, "R_range": -60.0, "M_range": 40.0, "CC": None}

def texture_camo(shape, mask, seed, sm):
    """Woodland blob camouflage - multi-layered thresholded noise."""
    h, w = shape
    # Three scales of noise for different blob sizes
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed + 700)
    n2 = multi_scale_noise(shape, [10, 20, 40], [0.5, 0.3, 0.2], seed + 701)
    n3 = multi_scale_noise(shape, [12, 24, 48], [0.5, 0.3, 0.2], seed + 702)
    
    # Thresholding into organic amoeba patches
    blob1 = (n1 > 0.2).astype(np.float32)
    blob2 = (n2 > 0.25).astype(np.float32)
    blob3 = (n3 > 0.3).astype(np.float32)
    
    # Layer them together into distinctly leveled patches
    camo = np.clip(blob1 * 0.3 + blob2 * 0.3 + blob3 * 0.4, 0, 1)
    return {"pattern_val": camo, "R_range": 60.0, "M_range": -30.0, "CC": 0}

def texture_wood_grain(shape, mask, seed, sm):
    """Natural wood grain - flowing horizontal lines with knots."""
    h, w = shape
    rng = np.random.RandomState(seed + 800)
    # Horizontal grain lines
    row_noise = rng.randn(h, 1).astype(np.float32) * 1.0
    grain = np.tile(row_noise, (1, w))
    # Add low-freq waviness
    y, x = get_mgrid((h, w))
    wave = np.sin(y * 0.03 + np.sin(x * 0.01) * 3) * 0.4
    grain = grain + wave + rng.randn(h, w).astype(np.float32) * 0.15
    grain = np.clip((grain + 2) / 4, 0, 1)
    return {"pattern_val": grain, "R_range": 80.0, "M_range": -50.0, "CC": 0}

def texture_snake_skin(shape, mask, seed, sm):
    """Elongated irregular scales - rectangular overlapping pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    scale_w, scale_h = 12, 18
    row = y // scale_h
    sx = (x + (row % 2) * (scale_w // 2)) % scale_w
    sy = y % scale_h
    # Gradient from center to edge of each scale
    edge_x = np.minimum(sx, scale_w - sx).astype(np.float32) / (scale_w * 0.5)
    edge_y = np.minimum(sy, scale_h - sy).astype(np.float32) / (scale_h * 0.5)
    center = np.clip(np.minimum(edge_x, edge_y) * 2.5, 0, 1)
    # center=1 = scale center (smooth), center=0 = edge (rough)
    return {"pattern_val": center, "R_range": -100.0, "M_range": 80.0, "CC": None}

def texture_snake_skin_2(shape, mask, seed, sm):
    """Diamond-shaped python scales with color variation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    ds = 24.0
    row = (y // ds).astype(np.float32)
    ox = (row % 2) * (ds / 2.0)
    lx = ((x + ox) % ds) - ds / 2.0
    ly = (y % ds) - ds / 2.0
    diamond = (np.abs(lx) + np.abs(ly)) / (ds * 0.5)
    center = np.clip(1.0 - diamond, 0, 1)
    return {"pattern_val": center, "R_range": -90.0, "M_range": 75.0, "CC": None}

def texture_snake_skin_3(shape, mask, seed, sm):
    """Hourglass saddle pattern viper scales."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cw, ch = 30.0, 22.0
    row = (y // ch).astype(np.float32)
    ox = (row % 2) * (cw / 2.0)
    lx = ((x + ox) % cw) / cw
    ly = (y % ch) / ch
    pinch = 0.3 + 0.4 * np.abs(ly - 0.5) * 2.0
    dist = np.abs(lx - 0.5) / (pinch * 0.5 + 1e-5)
    in_hourglass = dist < 1.0
    fade = np.where(in_hourglass, np.clip(1.0 - dist, 0, 1), 0.0)
    bg_hash = (np.sin(row * 5.3 + ((x + ox) // cw) * 11.7) * 0.5 + 0.5) * (1.0 - in_hourglass)
    pattern = np.clip(fade + bg_hash * 0.3, 0, 1)
    return {"pattern_val": pattern, "R_range": -85.0, "M_range": 70.0, "CC": None}

def texture_snake_skin_4(shape, mask, seed, sm):
    """Cobblestone pebble boa constrictor scales."""
    h, w = shape
    y, x = get_mgrid((h, w))
    from scipy.spatial import cKDTree
    rng = np.random.RandomState(seed + 4014)
    cell_s = 28.0
    grid_y = int(h / cell_s) + 2
    grid_x = int(w / cell_s) + 2
    cy, cx = np.mgrid[0:grid_y, 0:grid_x]
    pts_y = (cy * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    pts_x = (cx * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    points = np.column_stack((pts_y, pts_x))
    tree = cKDTree(points)
    coords = np.column_stack((y.flatten(), x.flatten()))
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(h, w).astype(np.float32)
    d2 = dists[:, 1].reshape(h, w).astype(np.float32)
    edge = d2 - d1
    centerDist = d1 / (cell_s * 0.6)
    center = np.clip(1.0 - centerDist * 0.8, 0, 1)
    is_groove = edge < 2.0
    pattern = np.where(is_groove, 0.0, center)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 60.0, "CC": None}

def texture_tire_tread(shape, mask, seed, sm):
    """Directional V-groove tire rubber pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    groove_period = max(20, min(h, w) // 40)
    # V-shaped grooves
    v_pos = ((x + y * 0.5) % groove_period).astype(np.float32)
    v_depth = np.abs(v_pos - groove_period / 2) / (groove_period / 2)
    groove = np.clip(v_depth, 0, 1)
    # groove=1 = raised rubber (rough), groove=0 = groove (smooth)
    return {"pattern_val": groove, "R_range": 80.0, "M_range": -40.0, "CC": 0}

def texture_circuit_board(shape, mask, seed, sm):
    """PCB trace lines with pads - orthogonal right-angle paths."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Traces: horizontal and vertical lines
    h_trace = ((y % 18) < 2).astype(np.float32)
    v_trace = ((x % 24) < 2).astype(np.float32)
    traces = np.clip(h_trace + v_trace, 0, 1)
    # Pads at intersections
    h_pad = ((y % 18) < 4).astype(np.float32)
    v_pad = ((x % 24) < 4).astype(np.float32)
    pads = (h_pad * v_pad)
    circuit = np.clip(traces + pads * 0.5, 0, 1)
    # traces/pads = conductive (metallic, smooth), bg = board (rough, matte)
    return {"pattern_val": circuit, "R_range": -120.0, "M_range": 140.0, "CC": None}

def texture_mosaic(shape, mask, seed, sm):
    """Voronoi cell stained glass tiles - irregular organic cells."""
    h, w = shape
    rng = np.random.RandomState(seed + 900)
    num_cells = 80
    cx = rng.randint(0, w, num_cells).astype(np.float32)
    cy = rng.randint(0, h, num_cells).astype(np.float32)
    # Downsampled Voronoi for speed
    ds = 4
    sh, sw = h // ds, w // ds
    yg = np.arange(sh).reshape(-1, 1).astype(np.float32) * ds
    xg = np.arange(sw).reshape(1, -1).astype(np.float32) * ds
    min_dist = np.full((sh, sw), 1e9, dtype=np.float32)
    min_dist2 = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(num_cells):
        dist = np.sqrt((yg - cy[i])**2 + (xg - cx[i])**2)
        update2 = (dist < min_dist2) & (dist >= min_dist)
        update1 = dist < min_dist
        min_dist2[update2] = dist[update2]
        min_dist2[update1] = min_dist[update1]
        min_dist[update1] = dist[update1]
    # Edge detection: where dist to nearest ≈ dist to 2nd nearest
    edge = np.clip(1.0 - (min_dist2 - min_dist) / 8.0, 0, 1)
    edge_img = Image.fromarray((edge * 255).astype(np.uint8))
    edge_full = np.array(edge_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # edge=1 = grout line (rough), edge=0 = tile center (smooth)
    return {"pattern_val": 1.0 - edge_full, "R_range": -90.0, "M_range": 80.0, "CC": None}

def texture_lava_flow(shape, mask, seed, sm):
    """Flowing molten rock cracks - directional with hot/cool zones."""
    h, w = shape
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [2, 6, 12], [0.3, 0.4, 0.3], seed+200)
    # Crack detection + directional flow
    cracks = np.exp(-n1**2 * 12)
    flow = np.clip((n2 + 0.3) * 1.5, 0, 1)
    lava = np.clip(cracks * 0.7 + flow * 0.3, 0, 1)
    # lava=1 = hot crack (smooth, metallic), lava=0 = cool rock (rough, matte)
    cc = np.clip(16 * (1 - lava * 0.6), 0, 16).astype(np.uint8)
    return {"pattern_val": lava, "R_range": -140.0, "M_range": 120.0, "CC": cc}

def texture_rain_drop(shape, mask, seed, sm):
    """Water droplet beading - scattered circular bumps on surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    num_drops = int(200 * sm)
    ds = 2
    sh, sw = h // ds, w // ds
    drop_map = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(num_drops):
        dy = rng.randint(0, sh)
        dx = rng.randint(0, sw)
        dr = rng.randint(1, 4)
        y_lo = max(0, dy - dr); y_hi = min(sh, dy + dr + 1)
        x_lo = max(0, dx - dr); x_hi = min(sw, dx + dr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - dy)**2 + (xg - dx)**2).astype(np.float32)
        drop = np.clip(1.0 - dist / dr, 0, 1) ** 2
        drop_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(drop_map[y_lo:y_hi, x_lo:x_hi], drop)
    drop_img = Image.fromarray((drop_map * 255).astype(np.uint8))
    drop_full = np.array(drop_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # drop=1 = water bead (ultra smooth, high metallic), drop=0 = surface
    return {"pattern_val": drop_full, "R_range": -80.0, "M_range": 60.0, "CC": None}

def texture_barbed_wire(shape, mask, seed, sm):
    """Twisted wire with barb spikes - aggressive repeating motif."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    wire_sp = max(24, dim // 42)
    barb_sp = max(12, dim // 85)
    wire_w = max(2, dim // 512)
    # Diagonal wire strands
    wire1 = np.abs(((x - y) % wire_sp) - wire_sp // 2).astype(np.float32) < wire_w
    wire2 = np.abs(((x + y) % wire_sp) - wire_sp // 2).astype(np.float32) < max(1, wire_w // 2)
    # Barb points at intersections
    barb_x = ((x % barb_sp) < max(3, dim // 340)).astype(np.float32)
    barb_y = ((y % barb_sp) < max(3, dim // 340)).astype(np.float32)
    barbs = barb_x * barb_y * (wire1 | wire2).astype(np.float32)
    wire = np.clip((wire1 | wire2).astype(np.float32) + barbs, 0, 1)
    # wire=1 = metal wire (smooth metallic), wire=0 = background
    return {"pattern_val": wire, "R_range": -100.0, "M_range": 130.0, "CC": 0}

def texture_chainmail(shape, mask, seed, sm):
    """Interlocking metal ring mesh - circular repeating pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    ring_size = max(10, min(h, w) // 100)
    row = y // ring_size
    cx = ((x + (row % 2) * (ring_size // 2)) % ring_size - ring_size // 2).astype(np.float32)
    cy = (y % ring_size - ring_size // 2).astype(np.float32)
    dist = np.sqrt(cx**2 + cy**2)
    ring_edge = (np.abs(dist - ring_size * 0.35) < 1.5).astype(np.float32)
    ring_center = (dist < ring_size * 0.25).astype(np.float32)
    # ring_edge=bright smooth wire, center=dark hole
    pattern = np.clip(ring_edge * 0.8 + ring_center * 0.2, 0, 1)
    return {"pattern_val": pattern, "R_range": -90.0, "M_range": 100.0, "CC": 0}

def texture_brick(shape, mask, seed, sm):
    """Offset brick pattern with mortar lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    brick_h, brick_w = max(12, dim // 85), max(24, dim // 42)
    row = y // brick_h
    bx = (x + (row % 2) * (brick_w // 2)) % brick_w
    by = y % brick_h
    mortar = ((bx < 2) | (by < 2)).astype(np.float32)
    brick = 1.0 - mortar
    # brick=1 = brick face (rough), mortar=0 = mortar line (smoother)
    return {"pattern_val": brick, "R_range": 60.0, "M_range": -40.0, "CC": 0}

def texture_leopard(shape, mask, seed, sm):
    """Organic leopard rosette spots - ring-shaped markings."""
    h, w = shape
    rng = np.random.RandomState(seed + 1200)
    num_spots = int(100 * sm)
    ds = 2
    sh, sw = h // ds, w // ds
    spot_map = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(num_spots):
        sy = rng.randint(0, sh)
        sx = rng.randint(0, sw)
        sr = rng.randint(3, 7)
        inner_r = sr * 0.45
        y_lo = max(0, sy - sr); y_hi = min(sh, sy + sr + 1)
        x_lo = max(0, sx - sr); x_hi = min(sw, sx + sr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - sy)**2 + (xg - sx)**2).astype(np.float32)
        ring = ((dist > inner_r) & (dist < sr)).astype(np.float32)
        spot_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(spot_map[y_lo:y_hi, x_lo:x_hi], ring)
    spot_img = Image.fromarray((spot_map * 255).astype(np.uint8))
    spot_full = np.array(spot_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # spot=1 = dark ring mark, spot=0 = fur/surface
    return {"pattern_val": spot_full, "R_range": 50.0, "M_range": -60.0, "CC": 0}

def texture_razor(shape, mask, seed, sm):
    """Diagonal slash marks - aggressive angular cuts."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    slash_period = max(20, dim // 50)
    slash_w = max(2, dim // 512)
    slash = ((x - y * 2) % slash_period).astype(np.float32)
    thin = (slash < slash_w).astype(np.float32)
    # slash=1 = exposed cut (bright metallic), slash=0 = surface
    return {"pattern_val": thin, "R_range": -80.0, "M_range": 120.0, "CC": 0}


# ================================================================
# v4.0 NEW PATTERN TEXTURES + PAINT FUNCTIONS
# ================================================================

def texture_tron(shape, mask, seed, sm):
    """Tron - neon grid with proportional lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    grid_size = max(48, dim // 21)
    line_w = max(2, dim // 512)
    # Grid lines
    hline = ((y % grid_size) < line_w).astype(np.float32)
    vline = ((x % grid_size) < line_w).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    return {"pattern_val": grid, "R_range": -120.0, "M_range": 180.0, "CC": 0}

def paint_tron_glow(paint, shape, mask, seed, pm, bb):
    """Tron lines - neon glow along grid lines (cyan-ish)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    grid_size = max(48, dim // 21)
    line_w = max(2, dim // 512)
    hline = ((y % grid_size) < line_w).astype(np.float32)
    vline = ((x % grid_size) < line_w).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    glow = grid * 0.12 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 0.2 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.9 * mask, 0, 1)  # cyan glow
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.8 * mask, 0, 1)
    return paint


def _voronoi_cells_fast(shape, n_pts, seed_offset, seed):
    """Fast Voronoi cell assignment using downsampling for large images."""
    h, w = shape
    np.random.seed(seed + seed_offset)
    n_pts = min(n_pts, 200)  # Cap to prevent O(n*h*w) explosion
    # Downsample for speed: run at 1/4 res, upscale result
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    pts_y = np.random.randint(0, sh, n_pts).astype(np.float32)
    pts_x = np.random.randint(0, sw, n_pts).astype(np.float32)
    y, x = np.mgrid[0:sh, 0:sw]
    y = y.astype(np.float32)
    x = x.astype(np.float32)
    min_dist = np.full((sh, sw), 1e9, dtype=np.float32)
    cell_id = np.zeros((sh, sw), dtype=np.int32)
    for i in range(n_pts):
        dist = (y - pts_y[i]) ** 2 + (x - pts_x[i]) ** 2
        closer = dist < min_dist
        cell_id = np.where(closer, i, cell_id)
        min_dist = np.where(closer, dist, min_dist)
    if ds > 1:
        cell_img = Image.fromarray(cell_id.astype(np.int16))
        cell_id = np.array(cell_img.resize((w, h), Image.NEAREST)).astype(np.int32)
    return cell_id

def texture_dazzle(shape, mask, seed, sm):
    """Dazzle camouflage - bold intersecting geometric zebra-like stripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 830)
    
    # Generate intersecting angled stripe fields
    stripe1 = np.sin((x * 0.05) + (y * 0.02) + rng.random()*10)*0.5+0.5
    stripe2 = np.sin((x * -0.03) + (y * 0.04) + rng.random()*10)*0.5+0.5
    stripe3 = np.sin((x * 0.01) + (y * -0.06) + rng.random()*10)*0.5+0.5
    
    # Sharp boundaries
    s1 = (stripe1 > 0.5).astype(np.float32)
    s2 = (stripe2 > 0.6).astype(np.float32)
    s3 = (stripe3 > 0.55).astype(np.float32)
    
    # XOR / Intersection logic for erratic geometry
    pattern = np.clip((s1 + s2 + s3) % 2, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -80.0, "CC": 0}

def paint_dazzle_contrast(paint, shape, mask, seed, pm, bb):
    """Dazzle - bold black/white patches for maximum contrast."""
    h, w = shape
    n_pts = max(20, int(h * w / 4000))
    cell_id = _voronoi_cells_fast(shape, n_pts, 830, seed)
    dark_cells = (cell_id % 2).astype(np.float32)
    darken = dark_cells * 0.35 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - darken * mask), 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def texture_marble(shape, mask, seed, sm):
    """Marble - soft noise veins using Gaussian zero-crossings."""
    h, w = shape
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 840)
    # Veins at zero-crossings of noise
    vein = np.exp(-noise**2 * 12)  # peaks at zero crossings
    vein = np.clip(vein, 0, 1)
    return {"pattern_val": vein, "R_range": -80.0, "M_range": 60.0, "CC": None}

def paint_marble_vein(paint, shape, mask, seed, pm, bb):
    """Marble veins - darken along vein lines for depth."""
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 840)
    vein = np.exp(-noise**2 * 12)
    darken = vein * 0.1 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - darken * mask, 0, 1)
    return paint


def texture_mega_flake(shape, mask, seed, sm):
    """Mega Flake - large hex glitter flakes (~12px)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 12
    row = (y / (hex_size * 0.866)).astype(int)
    col = (x / hex_size).astype(int)
    offset = np.where(row % 2 == 0, 0, hex_size // 2)
    cx = (col * hex_size + offset).astype(np.float32)
    cy = (row * hex_size * 0.866).astype(np.float32)
    # Distance to cell center = flake brightness variation
    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
    np.random.seed(seed + 850)
    # Each cell gets random brightness
    cell_hash = (row * 1337 + col * 7919 + seed) % 65536
    cell_rand = (np.sin(cell_hash.astype(np.float32) * 0.1) * 0.5 + 0.5)
    facet = np.clip(cell_rand * (1 - dist / hex_size * 0.5), 0, 1)
    return {"pattern_val": facet, "R_range": -50.0, "M_range": 60.0, "CC": 0}

def paint_mega_sparkle(paint, shape, mask, seed, pm, bb):
    """Mega Flake - random bright sparkle on each large flake facet."""
    h, w = shape
    np.random.seed(seed + 851)
    sparkle = np.random.rand(h, w).astype(np.float32)
    sparkle = np.where(sparkle > 0.85, sparkle * 0.12 * pm, 0)
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


def texture_multicam(shape, mask, seed, sm):
    """Multicam - 5-layer organic Perlin camo pattern."""
    h, w = shape
    # 5 layers at different scales for organic multi-color camo
    layers = []
    for layer_i in range(5):
        n = multi_scale_noise(shape, [16 + layer_i * 8, 32 + layer_i * 8],
                              [0.5, 0.5], seed + 860 + layer_i * 100)
        layers.append(np.clip((n + 0.5) * 1.2, 0, 1))
    # Combine: each layer dominates a different brightness range
    combined = np.zeros_like(layers[0])
    for layer_i, layer in enumerate(layers):
        threshold = layer_i / 5.0
        combined = np.where(layer > threshold + 0.3, layer * (layer_i + 1) / 5.0, combined)
    combined = np.clip(combined, 0, 1)
    return {"pattern_val": combined, "R_range": 70.0, "M_range": -50.0, "CC": 0}

def paint_multicam_colors(paint, shape, mask, seed, pm, bb):
    """Multicam - applies multi-tone desaturation for tactical look."""
    # Slight desaturation for camo zones
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 860)
    zones = np.clip((n + 0.5) * 1.2, 0, 1)
    desat = zones * 0.2 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    return paint


def _voronoi_cracks_fast(shape, n_pts, seed_offset, seed, crack_width=12.0):
    """Fast Voronoi crack detection using downsampling."""
    h, w = shape
    np.random.seed(seed + seed_offset)
    n_pts = min(n_pts, 200)  # Cap points
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    pts_y = np.random.randint(0, sh, n_pts).astype(np.float32)
    pts_x = np.random.randint(0, sw, n_pts).astype(np.float32)
    y, x = np.mgrid[0:sh, 0:sw]
    y = y.astype(np.float32)
    x = x.astype(np.float32)
    dist1 = np.full((sh, sw), 1e9, dtype=np.float32)
    dist2 = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(n_pts):
        dist = np.sqrt((y - pts_y[i]) ** 2 + (x - pts_x[i]) ** 2)
        new_dist2 = np.where(dist < dist1, dist1, np.where(dist < dist2, dist, dist2))
        dist1 = np.minimum(dist1, dist)
        dist2 = new_dist2
    crack = np.clip(1.0 - (dist2 - dist1) / crack_width, 0, 1)
    if ds > 1:
        crack_img = Image.fromarray((crack * 255).astype(np.uint8))
        crack = np.array(crack_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    return crack

def texture_magma_crack(shape, mask, seed, sm):
    """Magma Crack - Voronoi boundary cracks glow orange like lava."""
    h, w = shape
    n_pts = max(15, int(h * w / 6000))
    crack = _voronoi_cracks_fast(shape, n_pts, 870, seed, 12.0)
    return {"pattern_val": crack, "R_range": -160.0, "M_range": 140.0, "CC": 0}

def paint_magma_glow(paint, shape, mask, seed, pm, bb):
    """Magma cracks - orange glow along crack boundaries."""
    h, w = shape
    n_pts = max(15, int(h * w / 6000))
    crack = _voronoi_cracks_fast(shape, n_pts, 870, seed, 12.0)
    glow = crack * 0.2 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 1.0 * mask, 0, 1)   # red-orange
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.45 * mask, 0, 1)  # orange
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.05 * mask, 0, 1)  # minimal blue
    return paint


# ================================================================
# v5.0 NEW PATTERN TEXTURE + PAINT FUNCTIONS (12 new patterns)
# ================================================================

def texture_rivet_plate(shape, mask, seed, sm):
    """Rivet Plate - industrial riveted panel seams with chrome rivet heads.
    v2: Vectorized template stamping (was nested-loop distance maps - caused 90s hang)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    panel_h, panel_w = 80, 80
    # Panel seam lines: 2px grooves
    h_seam = ((y % panel_h) < 2).astype(np.float32)
    v_seam = ((x % panel_w) < 2).astype(np.float32)
    seams = np.clip(h_seam + v_seam, 0, 1)
    # Rivet heads - template stamping approach (O(n) per rivet, tiny template)
    rivet_r = 4
    # Build one small template (9x9 pixels)
    tpl_sz = rivet_r * 2 + 1
    ty = np.arange(tpl_sz, dtype=np.float32).reshape(-1, 1) - rivet_r
    tx = np.arange(tpl_sz, dtype=np.float32).reshape(1, -1) - rivet_r
    rivet_tpl = np.clip(1.0 - np.sqrt(ty * ty + tx * tx) / rivet_r, 0, 1) ** 2
    # Collect all rivet center positions
    rivet_map = np.zeros((h, w), dtype=np.float32)
    for ry in range(0, h, panel_h):
        for rx in range(0, w, panel_w):
            for (dy, dx) in [(0, 0), (0, panel_w // 2), (panel_h // 2, 0)]:
                cy, cx = ry + dy, rx + dx
                if cy >= h or cx >= w:
                    continue
                # Stamp the small template at this position
                y0 = max(0, cy - rivet_r)
                y1 = min(h, cy + rivet_r + 1)
                x0 = max(0, cx - rivet_r)
                x1 = min(w, cx + rivet_r + 1)
                ty0 = y0 - (cy - rivet_r)
                ty1 = ty0 + (y1 - y0)
                tx0 = x0 - (cx - rivet_r)
                tx1 = tx0 + (x1 - x0)
                rivet_map[y0:y1, x0:x1] = np.maximum(
                    rivet_map[y0:y1, x0:x1],
                    rivet_tpl[ty0:ty1, tx0:tx1]
                )
    # Combine: rivets are raised chrome bumps, seams are rough grooves
    pattern = np.clip(rivet_map - seams * 0.3, 0, 1)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 80.0, "CC": 0}

def paint_rivet_plate_emboss(paint, shape, mask, seed, pm, bb):
    """Rivet plate - darken seam grooves, brighten rivet heads."""
    h, w = shape
    y, x = get_mgrid((h, w))
    panel_h, panel_w = 80, 80
    h_seam = ((y % panel_h) < 2).astype(np.float32)
    v_seam = ((x % panel_w) < 2).astype(np.float32)
    seams = np.clip(h_seam + v_seam, 0, 1)
    darken = seams * 0.05 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_frost_crystal(shape, mask, seed, sm):
    """Frost Crystal - ice crystal branching fractals."""
    h, w = shape
    np.random.seed(seed + 1100)
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1101)
    n2 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1102)
    crystal = np.clip(np.abs(n1) + np.abs(n2) * 0.5 - 0.3, 0, 1)
    crystal = np.clip(crystal * 2, 0, 1)
    return {"pattern_val": crystal, "R_range": -80.0, "M_range": 60.0, "CC": None}

def paint_frost_crystal(paint, shape, mask, seed, pm, bb):
    """Frost crystal - whitens along crystal paths."""
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1101)
    n2 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1102)
    crystal = np.clip(np.abs(n1) + np.abs(n2) * 0.5 - 0.3, 0, 1)
    crystal = np.clip(crystal * 2, 0, 1)
    brighten = crystal * 0.03 * pm
    paint = np.clip(paint + brighten[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_wave(shape, mask, seed, sm):
    """Wave - smooth flowing sine wave ripples."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y = y.astype(np.float32) / h
    x = x.astype(np.float32) / w
    np.random.seed(seed + 1200)
    angle = np.random.uniform(0, np.pi)
    freq = 12.0
    wave = np.sin((y * np.cos(angle) + x * np.sin(angle)) * freq * np.pi * 2) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 70.0, "M_range": -40.0, "CC": None}

def paint_wave_shimmer(paint, shape, mask, seed, pm, bb):
    """Wave shimmer - subtle brightness oscillation along wave."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y = y.astype(np.float32) / h
    x = x.astype(np.float32) / w
    np.random.seed(seed + 1200)
    angle = np.random.uniform(0, np.pi)
    wave = np.sin((y * np.cos(angle) + x * np.sin(angle)) * 12 * np.pi * 2) * 0.5 + 0.5
    paint = np.clip(paint + (wave * 0.02 * pm)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_spiderweb(shape, mask, seed, sm):
    """Spiderweb - radial + concentric thin crack lines."""
    h, w = shape
    cy, cx = h // 2, w // 2
    y, x = get_mgrid((h, w))
    dy = (y - cy).astype(np.float32)
    dx = (x - cx).astype(np.float32)
    angle = np.arctan2(dy, dx)
    dist = np.sqrt(dy**2 + dx**2)
    # Radial spokes
    n_spokes = 16
    spoke = np.abs(np.sin(angle * n_spokes / 2))
    spoke_lines = (spoke < 0.05).astype(np.float32)
    # Concentric rings
    ring_spacing = 40.0
    rings = np.abs(np.sin(dist / ring_spacing * np.pi))
    ring_lines = (rings < 0.06).astype(np.float32)
    web = np.clip(spoke_lines + ring_lines, 0, 1)
    return {"pattern_val": web, "R_range": 80.0, "M_range": -40.0, "CC": 0}

def paint_spiderweb_crack(paint, shape, mask, seed, pm, bb):
    """Spiderweb - subtle darken along web lines."""
    h, w = shape
    cy, cx = h // 2, w // 2
    y, x = get_mgrid((h, w))
    dy = (y - cy).astype(np.float32)
    dx = (x - cx).astype(np.float32)
    angle = np.arctan2(dy, dx)
    dist = np.sqrt(dy**2 + dx**2)
    spoke = (np.abs(np.sin(angle * 8)) < 0.05).astype(np.float32)
    rings = (np.abs(np.sin(dist / 40 * np.pi)) < 0.06).astype(np.float32)
    web = np.clip(spoke + rings, 0, 1)
    paint = np.clip(paint - web[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_topographic(shape, mask, seed, sm):
    """Topographic - contour lines like elevation map."""
    h, w = shape
    elev = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    elev = (elev + 1) * 0.5  # 0-1
    n_contours = 20
    contour = np.abs(np.sin(elev * n_contours * np.pi))
    lines = (contour < 0.08).astype(np.float32)
    return {"pattern_val": lines, "R_range": 70.0, "M_range": -30.0, "CC": None}

def paint_topographic_line(paint, shape, mask, seed, pm, bb):
    """Topographic contour - slight darken on contour lines."""
    elev = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    elev = (elev + 1) * 0.5
    lines = (np.abs(np.sin(elev * 20 * np.pi)) < 0.08).astype(np.float32)
    paint = np.clip(paint - lines[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_crosshatch(shape, mask, seed, sm):
    """Crosshatch - overlapping 45deg line grids like pen strokes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    spacing = 20
    line_w = 2
    diag1 = ((y + x) % spacing < line_w).astype(np.float32)
    diag2 = ((y - x + 10000) % spacing < line_w).astype(np.float32)
    hatch = np.clip(diag1 + diag2, 0, 1)
    return {"pattern_val": hatch, "R_range": 55.0, "M_range": -25.0, "CC": 0}

def paint_crosshatch_ink(paint, shape, mask, seed, pm, bb):
    """Crosshatch ink - darken along hatch lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    spacing = max(20, dim // 50)
    line_w = max(2, dim // 512)
    diag1 = ((y + x) % spacing < line_w).astype(np.float32)
    diag2 = ((y - x + 10000) % spacing < line_w).astype(np.float32)
    hatch = np.clip(diag1 + diag2, 0, 1)
    paint = np.clip(paint - hatch[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_chevron(shape, mask, seed, sm):
    """Chevron - repeating V/arrow stripe pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(60, min(h, w) // 16)
    v_shape = np.abs((x % period) - period // 2).astype(np.float32) / (period // 2)
    stripe = ((y + v_shape * period // 2).astype(np.int32) % period < period // 3).astype(np.float32)
    return {"pattern_val": stripe, "R_range": 70.0, "M_range": -40.0, "CC": None}

def paint_chevron_contrast(paint, shape, mask, seed, pm, bb):
    """Chevron - alternating slight brightness difference."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(60, min(h, w) // 16)
    v_shape = np.abs((x % period) - period // 2).astype(np.float32) / (period // 2)
    stripe = ((y + v_shape * period // 2).astype(np.int32) % period < period // 3).astype(np.float32)
    paint = np.clip(paint + (stripe - 0.5)[:,:,np.newaxis] * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_celtic_knot(shape, mask, seed, sm):
    """Celtic Knot - interwoven band pattern using sin modulation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_n = y.astype(np.float32) / h * np.pi * 6
    x_n = x.astype(np.float32) / w * np.pi * 6
    band1 = np.sin(x_n + np.sin(y_n * 2) * 0.8)
    band2 = np.sin(y_n + np.sin(x_n * 2) * 0.8)
    weave = np.clip(np.abs(band1) + np.abs(band2) - 0.6, 0, 1)
    weave = np.clip(weave * 2, 0, 1)
    return {"pattern_val": weave, "R_range": 60.0, "M_range": -20.0, "CC": None}

def paint_celtic_emboss(paint, shape, mask, seed, pm, bb):
    """Celtic knot - subtle emboss on band edges."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_n = y.astype(np.float32) / h * np.pi * 6
    x_n = x.astype(np.float32) / w * np.pi * 6
    band1 = np.sin(x_n + np.sin(y_n * 2) * 0.8)
    band2 = np.sin(y_n + np.sin(x_n * 2) * 0.8)
    weave = np.clip(np.abs(band1) + np.abs(band2) - 0.6, 0, 1) * 2
    paint = np.clip(paint + (np.clip(weave, 0, 1) - 0.5)[:,:,np.newaxis] * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_skull(shape, mask, seed, sm):
    """Skull mesh - array of skull-like shapes from concentric ovals + eye holes."""
    h, w = shape
    cell_h, cell_w = 64, 48
    y, x = get_mgrid((h, w))
    # Tile coordinate
    ty = (y % cell_h).astype(np.float32) / cell_h - 0.5
    tx = (x % cell_w).astype(np.float32) / cell_w - 0.5
    # Skull outline: oval
    skull = np.clip(1.0 - (tx**2 / 0.12 + ty**2 / 0.18) * 1.5, 0, 1)
    # Eye holes: two small circles
    eye_l = np.clip(1.0 - ((tx + 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    eye_r = np.clip(1.0 - ((tx - 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    skull = np.clip(skull - eye_l * 0.8 - eye_r * 0.8, 0, 1)
    return {"pattern_val": skull, "R_range": 50.0, "M_range": -20.0, "CC": 0}

def paint_skull_darken(paint, shape, mask, seed, pm, bb):
    """Skull mesh - darkens eye holes and outline edges."""
    h, w = shape
    cell_h, cell_w = 64, 48
    y, x = get_mgrid((h, w))
    ty = (y % cell_h).astype(np.float32) / cell_h - 0.5
    tx = (x % cell_w).astype(np.float32) / cell_w - 0.5
    eye_l = np.clip(1.0 - ((tx + 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    eye_r = np.clip(1.0 - ((tx - 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    darken = (eye_l + eye_r) * 0.06 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_damascus(shape, mask, seed, sm):
    """Damascus steel - flowing layered wavy metal grain."""
    h, w = shape
    np.random.seed(seed + 1400)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1401)
    # Flowing horizontal waves disturbed by noise
    wave = np.sin((y * 30 + n1 * 3) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 70.0, "M_range": 50.0, "CC": 0}

def paint_damascus_layer(paint, shape, mask, seed, pm, bb):
    """Damascus - alternating bright/dark metal layers."""
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1401)
    h = shape[0]
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    wave = np.sin((y * 30 + n1 * 3) * np.pi) * 0.5 + 0.5
    paint = np.clip(paint + (wave - 0.5)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_houndstooth(shape, mask, seed, sm):
    """Houndstooth - classic four-pointed tooth check pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(24, min(h, w) // 32)
    cy = (y // cell) % 2
    cx = (x // cell) % 2
    sy = (y % cell).astype(np.float32) / cell
    sx = (x % cell).astype(np.float32) / cell
    check = (cy ^ cx).astype(np.float32)
    tooth_ur = ((cy == 0) & (cx == 0) & (sy < sx) & (sy < 0.5) & (sx < 0.5)).astype(np.float32)
    tooth_dl = ((cy == 1) & (cx == 1) & (sy > sx) & (sy > 0.5) & (sx > 0.5)).astype(np.float32)
    tooth_ul = ((cy == 0) & (cx == 1) & (sy < (1.0 - sx)) & (sy < 0.5) & (sx > 0.5)).astype(np.float32)
    tooth_dr = ((cy == 1) & (cx == 0) & (sy > (1.0 - sx)) & (sy > 0.5) & (sx < 0.5)).astype(np.float32)
    pattern = np.clip(check + tooth_ur + tooth_dl + tooth_ul + tooth_dr, 0, 1)
    return {"pattern_val": pattern, "R_range": 70.0, "M_range": -40.0, "CC": None}


def paint_houndstooth_contrast(paint, shape, mask, seed, pm, bb):
    """Houndstooth - alternating brightness for classic pattern visibility."""
    h, w = shape
    cell = max(32, min(h, w) // 28)
    y, x = get_mgrid((h, w))
    check = ((y // cell) % 2 ^ (x // cell) % 2).astype(np.float32)
    paint = np.clip(paint + (check - 0.5)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_plaid(shape, mask, seed, sm):
    """Plaid/Tartan - overlapping horizontal and vertical color bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    b1h = ((yf % 48) < 12).astype(np.float32)
    b2h = ((yf % 48) > 20).astype(np.float32) * ((yf % 48) < 26).astype(np.float32)
    b1v = ((xf % 48) < 12).astype(np.float32)
    b2v = ((xf % 48) > 20).astype(np.float32) * ((xf % 48) < 26).astype(np.float32)
    horiz = b1h * 0.7 + b2h * 0.4
    vert = b1v * 0.7 + b2v * 0.4
    plaid = np.clip(horiz + vert, 0, 1)
    return {"pattern_val": plaid, "R_range": 70.0, "M_range": -40.0, "CC": None}


def paint_plaid_tint(paint, shape, mask, seed, pm, bb):
    """Plaid - alternating warm/cool shift on bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    band_h = np.sin(y.astype(np.float32) / h * np.pi * 16) * 0.5 + 0.5
    band_v = np.sin(x.astype(np.float32) / w * np.pi * 16) * 0.5 + 0.5
    warm = band_h * 0.02 * pm
    cool = band_v * 0.02 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + warm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + cool * mask, 0, 1)
    return paint


# --- SPEC FUNCTIONS: Expansion Pack (5 new specials/monolithics) ---

def spec_oil_slick(shape, mask, seed, sm):
    """Oil slick - flowing rainbow pools with high metallic and variable roughness."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [4, 12, 24], [0.3, 0.4, 0.3], seed+200)
    pool = np.clip((n1 + n2) * 0.5 + 0.5, 0, 1)
    spec[:,:,0] = np.clip((220 + pool * 35) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 + pool * 60) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_galaxy(shape, mask, seed, sm):
    """Galaxy - deep space nebula with star clusters."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    nebula = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    nebula_val = np.clip((nebula + 0.5) * 1.2, 0, 1)
    rng = np.random.RandomState(seed + 200)
    stars = (rng.random((h, w)).astype(np.float32) > 0.98).astype(np.float32)
    combined = np.clip(nebula_val * 0.6 + stars * 0.4, 0, 1)
    spec[:,:,0] = np.clip((80 + combined * 175) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((30 + nebula_val * 40 + stars * 20) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_rust(shape, mask, seed, sm):
    """Progressive rust - oxidation patches with variable roughness and no clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    rust = np.clip((mn + 0.2) * 2, 0, 1)
    # Rusty areas: low metallic, high roughness, no clearcoat
    spec[:,:,0] = np.clip((180 - rust * 140) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((40 + rust * 180) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    cc = np.clip(16 * (1 - rust * 0.9), 0, 16).astype(np.uint8)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_neon_glow(shape, mask, seed, sm):
    """Neon glow - edge-detected high metallic with variable roughness for glow effect."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    mn = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+100)
    # Edge-like features from noise gradients
    edges = np.clip(np.abs(mn) * 3, 0, 1)
    spec[:,:,0] = np.clip((200 + edges * 55) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((10 + (1-edges) * 80) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_weathered_paint(shape, mask, seed, sm):
    """Weathered paint - faded peeling layers showing underlayer patches."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    peel = np.clip((mn + 0.1) * 1.5, 0, 1)
    # Peeled areas: exposed primer (low metallic, high roughness, no CC)
    # Intact areas: normal paint (mid metallic, low roughness, full CC)
    spec[:,:,0] = np.clip((180 - peel * 130) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((20 + peel * 160) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    cc = np.clip(16 * (1 - peel * 0.85), 0, 16).astype(np.uint8)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec


# --- v5.5 "SHOKK THE SYSTEM" ADDITIONS (5 new patterns + 5 new bases for #55) ---

def texture_fracture(shape, mask, seed, sm):
    """Fracture - shattered impact glass with radial + Voronoi crack network."""
    h, w = shape
    np.random.seed(seed + 5500)
    n_impacts = int(3 + sm * 2)
    impact_y = np.random.randint(h // 6, 5 * h // 6, n_impacts).astype(np.float32)
    impact_x = np.random.randint(w // 6, 5 * w // 6, n_impacts).astype(np.float32)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Voronoi crack network: thin lines at cell boundaries
    n_vor = max(30, int(h * w / 8000))
    np.random.seed(seed + 5501)
    vor_y = np.random.randint(0, h, n_vor).astype(np.float32)
    vor_x = np.random.randint(0, w, n_vor).astype(np.float32)
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    sy = np.arange(sh).reshape(-1, 1).astype(np.float32) * ds
    sx = np.arange(sw).reshape(1, -1).astype(np.float32) * ds
    d1 = np.full((sh, sw), 1e9, dtype=np.float32)
    d2 = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(n_vor):
        d = np.sqrt((sy - vor_y[i])**2 + (sx - vor_x[i])**2)
        nd2 = np.where(d < d1, d1, np.where(d < d2, d, d2))
        d1 = np.minimum(d1, d)
        d2 = nd2
    vor_crack = np.clip(1.0 - (d2 - d1) / 8.0, 0, 1)
    if ds > 1:
        vc_img = Image.fromarray((vor_crack * 255).astype(np.uint8))
        vor_crack = np.array(vc_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # Radial cracks from each impact point (8-12 spoke lines per impact)
    radial = np.zeros((h, w), dtype=np.float32)
    for i in range(n_impacts):
        dist = np.sqrt((yf - impact_y[i])**2 + (xf - impact_x[i])**2)
        angle = np.arctan2(yf - impact_y[i], xf - impact_x[i])
        n_spokes = np.random.randint(8, 13)
        spoke = np.abs(np.sin(angle * n_spokes / 2))
        spoke_line = (spoke < 0.04).astype(np.float32)
        # Fade with distance but not too fast
        fade = np.clip(1.0 - dist / (max(h, w) * 0.4), 0, 1)
        radial = np.maximum(radial, spoke_line * fade)
        # Concentric stress rings near impact
        stress = np.abs(np.sin(dist / 15 * np.pi))
        stress_line = (stress < 0.06).astype(np.float32) * np.clip(1.0 - dist / 80, 0, 1)
        radial = np.maximum(radial, stress_line)
    # Combine: Voronoi network + radial cracks
    cracks = np.clip(vor_crack * 0.6 + radial * 0.8, 0, 1)
    # Cracks lose clearcoat
    cc = np.clip(16 * (1 - cracks * 0.85), 0, 16).astype(np.uint8)
    # crack=1 → rough matte damaged, crack=0 → smooth intact
    return {"pattern_val": cracks, "R_range": 100.0, "M_range": -60.0, "CC": cc}

def paint_fracture_damage(paint, shape, mask, seed, pm, bb):
    """Fracture - darkens crack lines to simulate exposed substrate."""
    h, w = shape
    np.random.seed(seed + 5500)
    n_impacts = int(3 + 2)  # match texture at default sm
    impact_y = np.random.randint(h // 6, 5 * h // 6, n_impacts).astype(np.float32)
    impact_x = np.random.randint(w // 6, 5 * w // 6, n_impacts).astype(np.float32)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32); xf = x.astype(np.float32)
    # Simplified crack map for paint
    radial = np.zeros((h, w), dtype=np.float32)
    for i in range(n_impacts):
        dist = np.sqrt((yf - impact_y[i])**2 + (xf - impact_x[i])**2)
        angle = np.arctan2(yf - impact_y[i], xf - impact_x[i])
        spoke = (np.abs(np.sin(angle * 5)) < 0.04).astype(np.float32)
        fade = np.clip(1.0 - dist / (max(h, w) * 0.4), 0, 1)
        radial = np.maximum(radial, spoke * fade)
    darken = radial * 0.08 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_ember_mesh(shape, mask, seed, sm):
    """Ember Mesh - glowing hot wire grid with fading ember nodes at intersections."""
    h, w = shape
    cell = max(36, min(h, w) // 28)
    y, x = get_mgrid((h, w))
    line_w = max(2, int(2 * sm))
    hline = ((y % cell) < line_w).astype(np.float32)
    vline = ((x % cell) < line_w).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    # Hot nodes at intersections
    node_y = ((y % cell) < (line_w + 3)).astype(np.float32)
    node_x = ((x % cell) < (line_w + 3)).astype(np.float32)
    nodes = node_y * node_x
    ember = np.clip(grid * 0.7 + nodes * 0.3, 0, 1)
    return {"pattern_val": ember, "R_range": -80.0, "M_range": 140.0, "CC": 0}

def paint_ember_mesh_glow(paint, shape, mask, seed, pm, bb):
    """Ember mesh - orange/red glow on wire lines."""
    h, w = shape
    cell = max(36, min(h, w) // 28)
    y, x = get_mgrid((h, w))
    hline = ((y % cell) < 2).astype(np.float32)
    vline = ((x % cell) < 2).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    glow = grid * 0.1 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 0.9 * mask, 0, 1)   # red-orange
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.35 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.05 * mask, 0, 1)
    return paint

def texture_turbine(shape, mask, seed, sm):
    """Turbine - radial fan blade pattern spinning from center."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    y, x = get_mgrid((h, w))
    angle = np.arctan2(y.astype(np.float32) - cy, x.astype(np.float32) - cx)
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    n_blades = 12
    spiral_twist = dist / (max(h, w) * 0.3)
    blades = (np.sin((angle + spiral_twist) * n_blades) * 0.5 + 0.5)
    return {"pattern_val": blades, "R_range": 50.0, "M_range": -25.0, "CC": None}

def paint_turbine_spin(paint, shape, mask, seed, pm, bb):
    """Turbine - alternating light/dark blade sectors."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    y, x = get_mgrid((h, w))
    angle = np.arctan2(y.astype(np.float32) - cy, x.astype(np.float32) - cx)
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    blades = np.sin((angle + dist / (max(h, w) * 0.3)) * 12) * 0.5 + 0.5
    shift = (blades - 0.5) * 0.03 * pm
    paint = np.clip(paint + shift[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_static_noise(shape, mask, seed, sm):
    """Static Noise - TV static random pixel noise pattern."""
    h, w = shape
    np.random.seed(seed + 5540)
    # Coarse static: blocky pixel groups scaled to resolution
    block = max(4, min(h, w) // 256)
    sh, sw = h // block, w // block
    coarse = np.random.random((sh, sw)).astype(np.float32)
    coarse_img = Image.fromarray((coarse * 255).astype(np.uint8))
    coarse_up = np.array(coarse_img.resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0
    # Fine static overlay
    fine = np.random.random((h, w)).astype(np.float32)
    static_val = np.clip(coarse_up * 0.6 + fine * 0.4, 0, 1)
    return {"pattern_val": static_val, "R_range": 80.0, "M_range": -30.0, "CC": 0}

def paint_static_noise_grain(paint, shape, mask, seed, pm, bb):
    """Static noise - random brightness jitter like analog TV snow."""
    h, w = shape
    np.random.seed(seed + 5540)
    block = max(4, min(h, w) // 256)
    sh, sw = h // block, w // block
    coarse = np.random.random((sh, sw)).astype(np.float32)
    coarse_img = Image.fromarray((coarse * 255).astype(np.uint8))
    coarse_up = np.array(coarse_img.resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0
    grain = (coarse_up - 0.5) * 0.04 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_razor_wire(shape, mask, seed, sm):
    """Razor Wire - coiled helical wire with barbed loops."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_f = y.astype(np.float32)
    x_f = x.astype(np.float32)
    dim = min(h, w)
    spacing = max(50, dim // 20)
    coil_r = max(8, dim // 128)
    coil_freq = max(12, dim // 85)
    barb_sp = max(24, dim // 42)
    # Horizontal coil strands
    strand_y = (y_f % spacing).astype(np.float32)
    center = spacing / 2.0
    coil = np.sin(x_f / coil_freq * np.pi * 2) * coil_r
    dist_from_coil = np.abs(strand_y - center - coil)
    wire = np.clip(1.0 - dist_from_coil / 4.0, 0, 1)
    # Barb spikes at regular intervals
    barb_x = ((x % barb_sp) < max(3, dim // 340)).astype(np.float32)
    barb_mask = wire * barb_x
    result = np.clip(wire + barb_mask * 0.5, 0, 1)
    return {"pattern_val": result, "R_range": 65.0, "M_range": 80.0, "CC": 0}

def paint_razor_wire_scratch(paint, shape, mask, seed, pm, bb):
    """Razor wire - dark scratch marks along wire paths."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_f = y.astype(np.float32); x_f = x.astype(np.float32)
    dim = min(h, w)
    spacing = max(50, dim // 20)
    coil_r = max(8, dim // 128)
    coil_freq = max(12, dim // 85)
    strand_y = (y_f % spacing).astype(np.float32)
    coil = np.sin(x_f / coil_freq * np.pi * 2) * coil_r
    dist_from_coil = np.abs(strand_y - spacing / 2.0 - coil)
    wire = np.clip(1.0 - dist_from_coil / 4.0, 0, 1)
    darken = wire * 0.06 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# --- v5.5 NEW BASE PAINT FUNCTIONS ---

def paint_plasma_shift(paint, shape, mask, seed, pm, bb):
    """Plasma metal - electric purple/blue micro-shift hue injection."""
    h, w = shape
    np.random.seed(seed + 5550)
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5551)
    shift = np.clip(n * 0.5 + 0.5, 0, 1) * pm * 0.04
    paint[:,:,0] = np.clip(paint[:,:,0] + shift * 0.4 * mask, 0, 1)   # slight magenta
    paint[:,:,1] = np.clip(paint[:,:,1] - shift * 0.15 * mask, 0, 1)  # deepen green
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)   # blue push
    return paint

def paint_burnt_metal(paint, shape, mask, seed, pm, bb):
    """Burnt metal - exhaust header heat discoloration, golden/blue oxide."""
    h, w = shape
    np.random.seed(seed + 5560)
    heat = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5561)
    heat_val = np.clip(heat * 0.5 + 0.5, 0, 1)
    # Gold in hot zones, blue in cooler transition
    gold = heat_val * 0.04 * pm
    blue = (1 - heat_val) * 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + gold * 0.6 * mask - blue * 0.1 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + gold * 0.35 * mask - blue * 0.05 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - gold * 0.1 * mask + blue * 0.5 * mask, 0, 1)
    return paint

def paint_mercury_pool(paint, shape, mask, seed, pm, bb):
    """Mercury - liquid metal pooling effect, heavy desaturation with bright caustics."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    np.random.seed(seed + 5570)
    caustic = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5571)
    bright = np.clip(caustic, 0, 1) * 0.03 * pm
    paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_electric_blue_tint(paint, shape, mask, seed, pm, bb):
    """Electric blue tint - icy blue metallic color push."""
    shift = 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] - shift * 0.3 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + shift * 0.2 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)
    return paint

def paint_volcanic_ash(paint, shape, mask, seed, pm, bb):
    """Volcanic ash - desaturates and darkens with gritty fine grain."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.3 * pm
    darken = 0.06 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask - darken * mask, 0, 1)
    np.random.seed(seed + 5590)
    grain = np.random.randn(*shape).astype(np.float32) * 0.015 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# SHOKK PHASE TEXTURE FUNCTIONS (v4.0)
# Independent M/R/CC channel patterns using phase-shifted sin/cos
# These return M_pattern, R_pattern, CC_pattern as separate arrays
# ================================================================

# === SHOKK SERIES - UPGRADED EXISTING PATTERNS ===

def texture_shokk_bolt_v2(shape, mask, seed, sm):
    """SHOKK Bolt: Fractal branching lightning with independent R/M.
    R channel shows the main discharge path (chrome-mirror in the bolt),
    M channel shows the ionization field around it (metallic corona glow).
    Creates lightning that shifts between chrome and matte under different angles."""
    h, w = shape
    rng = np.random.RandomState(seed)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    glow_map = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    def _draw_bolt(x0, y0, x1, y1, thickness, brightness, depth=0):
        if depth > 6 or brightness < 0.1:
            return
        # Main segment with jitter
        n_segs = max(3, int(np.sqrt((x1-x0)**2 + (y1-y0)**2) / 20))
        pts_x = np.linspace(x0, x1, n_segs + 1)
        pts_y = np.linspace(y0, y1, n_segs + 1)
        for i in range(1, len(pts_x) - 1):
            pts_x[i] += rng.uniform(-30, 30) * (0.7 ** depth)
            pts_y[i] += rng.uniform(-15, 15) * (0.7 ** depth)
        for i in range(len(pts_x) - 1):
            sx, sy = pts_x[i], pts_y[i]
            ex, ey = pts_x[i+1], pts_y[i+1]
            seg_len = max(1, np.sqrt((ex-sx)**2 + (ey-sy)**2))
            # Distance from line segment
            dx, dy = ex - sx, ey - sy
            t = np.clip(((xx - sx) * dx + (yy - sy) * dy) / (seg_len**2 + 1e-8), 0, 1)
            proj_x = sx + t * dx
            proj_y = sy + t * dy
            dist = np.sqrt((xx - proj_x)**2 + (yy - proj_y)**2)
            # Sharp bolt core
            core = np.clip(1.0 - dist / max(1, thickness), 0, 1) * brightness
            bolt_map[:] = np.maximum(bolt_map, core)
            # Wide glow corona
            corona = np.exp(-(dist**2) / (2 * (thickness * 4)**2)) * brightness * 0.6
            glow_map[:] = np.maximum(glow_map, corona)
            # Branch
            if rng.rand() < 0.35 and depth < 4:
                bx = sx + (ex - sx) * rng.uniform(0.3, 0.7)
                by = sy + (ey - sy) * rng.uniform(0.3, 0.7)
                branch_angle = rng.uniform(-1.2, 1.2)
                branch_len = seg_len * rng.uniform(0.4, 0.9)
                bex = bx + np.cos(np.arctan2(ey-sy, ex-sx) + branch_angle) * branch_len
                bey = by + np.sin(np.arctan2(ey-sy, ex-sx) + branch_angle) * branch_len
                _draw_bolt(bx, by, bex, bey, thickness * 0.6, brightness * 0.7, depth + 1)

    # Main bolts
    for _ in range(rng.randint(2, 5)):
        x0 = rng.randint(w // 4, 3 * w // 4)
        _draw_bolt(x0, 0, x0 + rng.randint(-w//3, w//3), h, rng.uniform(2, 5), rng.uniform(0.7, 1.0))

    bolt_map = np.clip(bolt_map, 0, 1)
    glow_map = np.clip(glow_map, 0, 1)
    # R channel: bolt core (smooth=chrome in the bolt itself)
    R_pattern = 1.0 - bolt_map  # Low R = smooth where bolt is
    # M channel: glow corona (metallic shimmer around bolt)
    M_pattern = glow_map
    pv = (bolt_map + glow_map) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -70, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_fracture_v2(shape, mask, seed, sm):
    """SHOKK Fracture: Multi-layer impact crater with independent R/M for glass depth.
    R channel shows crack network (rough matte in cracks),
    M channel shows the glass shards between (mirror-chrome facets).
    Creates shattered windshield effect that catches light differently per shard."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    crack_map = np.zeros((h, w), dtype=np.float32)
    shard_map = np.zeros((h, w), dtype=np.float32)

    # Multiple impact points
    n_impacts = rng.randint(2, 5)
    for _ in range(n_impacts):
        cx, cy = rng.randint(w//6, 5*w//6), rng.randint(h//6, 5*h//6)
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        angle = np.arctan2(yy - cy, xx - cx)
        max_r = min(h, w) * rng.uniform(0.2, 0.45)

        # Radial cracks
        n_cracks = rng.randint(8, 16)
        for ci in range(n_cracks):
            crack_angle = ci * 2 * np.pi / n_cracks + rng.uniform(-0.2, 0.2)
            crack_width = rng.uniform(1.0, 2.5)
            ang_dist = np.abs(np.sin(angle - crack_angle))
            radial_crack = np.clip(1.0 - ang_dist * dist / crack_width, 0, 1)
            radial_crack *= np.clip(1.0 - dist / max_r, 0, 1)
            crack_map = np.maximum(crack_map, radial_crack * rng.uniform(0.5, 1.0))

        # Concentric ring cracks
        n_rings = rng.randint(3, 7)
        for ri in range(n_rings):
            ring_r = max_r * (ri + 1) / (n_rings + 1)
            ring = np.clip(1.0 - np.abs(dist - ring_r) / 2.0, 0, 1) * 0.7
            crack_map = np.maximum(crack_map, ring * np.clip(1.0 - dist / max_r, 0, 1))

        # Shard facets - each wedge between cracks gets a random "tilt" (metallic value)
        for ci in range(n_cracks):
            a1 = ci * 2 * np.pi / n_cracks
            a2 = (ci + 1) * 2 * np.pi / n_cracks
            mid_a = (a1 + a2) / 2
            in_wedge = (((angle - a1) % (2*np.pi)) < ((a2 - a1) % (2*np.pi))).astype(np.float32)
            tilt = rng.uniform(0.2, 1.0)
            shard_map += in_wedge * tilt * np.clip(1.0 - dist / max_r, 0, 1) * 0.3

        # Impact center crater
        crater = np.clip(1.0 - dist / 15, 0, 1)
        crack_map = np.maximum(crack_map, crater)

    crack_map = np.clip(crack_map, 0, 1)
    shard_map = np.clip(shard_map, 0, 1)
    R_pattern = crack_map  # High R in cracks = rough matte
    M_pattern = shard_map * (1.0 - crack_map * 0.8)  # Shards are metallic, cracks are not
    pv = np.clip(crack_map * 0.6 + shard_map * 0.4, 0, 1)
    CC_pattern = np.clip(crater * 0.8, 0, 1) if n_impacts == 1 else None
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 50, "R_range": -65,
            "CC": None, "CC_range": 20 if CC_pattern is not None else 0}


def texture_shokk_pulse_wave_v2(shape, mask, seed, sm):
    """SHOKK Pulse Wave: Expanding concentric pulses with R/M phase offset.
    R and M channels show rings offset by half a wavelength - when R is at peak
    (rough), M is at trough (non-metallic), and vice versa. Creates a 'breathing'
    effect where the surface oscillates between chrome and matte in concentric rings."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * rng.uniform(0.3, 0.7), w * rng.uniform(0.3, 0.7)
    dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    max_r = np.sqrt(h**2 + w**2) / 2
    norm_dist = dist / max(max_r, 1)

    freq = 6 + rng.randint(0, 8)
    # R channel: concentric rings
    R_pattern = (np.sin(norm_dist * 2 * np.pi * freq) + 1.0) / 2.0
    # M channel: SAME rings but phase-shifted by π (half wavelength)
    M_pattern = (np.sin(norm_dist * 2 * np.pi * freq + np.pi) + 1.0) / 2.0

    # Add EKG-style pulse spike on one radial line
    spike_angle = rng.uniform(0, 2 * np.pi)
    angle = np.arctan2(yy - cy, xx - cx)
    spike_mask = np.exp(-(((angle - spike_angle) % (2*np.pi))**2) / 0.005)
    pulse_height = np.sin(norm_dist * 2 * np.pi * freq * 3) * spike_mask
    R_pattern = np.clip(R_pattern + pulse_height * 0.3, 0, 1)

    # Fade out at edges
    fade = np.clip(1.0 - norm_dist * 0.3, 0.3, 1.0)
    R_pattern *= fade
    M_pattern *= fade

    pv = (R_pattern + M_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_scream_v2(shape, mask, seed, sm):
    """SHOKK Scream: Acoustic shockwave visualization with R/M opposition.
    Simulates visible sound - pressure waves radiate from center with compression
    zones (high M = chrome) and rarefaction zones (high R = matte). The R and M
    channels are in direct opposition: where one peaks, the other troughs."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    angle = np.arctan2(yy - cy, xx - cx)
    max_r = np.sqrt(h**2 + w**2) / 2

    # Pressure wave: concentric with angular distortion (mouth shape)
    freq = 5 + rng.randint(0, 4)
    # Mouth opening creates directional sound cone
    mouth_dir = rng.uniform(0, 2 * np.pi)
    directionality = 0.5 + 0.5 * np.cos(angle - mouth_dir)  # Stronger in mouth direction

    wave = np.sin(dist / max(max_r, 1) * 2 * np.pi * freq + angle * 0.5)
    # Compression zones (positive wave) = chrome metallic
    M_pattern = np.clip((wave + 1) / 2 * directionality, 0, 1)
    # Rarefaction zones (negative wave) = rough matte
    R_pattern = np.clip((-wave + 1) / 2 * directionality, 0, 1)

    # Add radial "scream lines" - visible sound propagation
    n_lines = 12 + rng.randint(0, 8)
    for i in range(n_lines):
        line_angle = mouth_dir + rng.uniform(-0.8, 0.8)
        ang_dist = np.abs(np.sin(angle - line_angle))
        line = np.clip(1.0 - ang_dist * 30, 0, 1) * np.clip(dist / max(max_r * 0.5, 1), 0, 1)
        M_pattern = np.clip(M_pattern + line * 0.2, 0, 1)

    # Center void
    center_void = np.clip(1.0 - dist / 20, 0, 1)
    R_pattern = np.clip(R_pattern + center_void * 0.5, 0, 1)

    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}


# === SHOKK SERIES - 7 NEW BOUNDARY-PUSHING PATTERNS ===

def texture_shokk_singularity(shape, mask, seed, sm):
    """SHOKK Singularity: Black hole gravitational lensing.
    R shows gravity well rings compressed toward center (smooth=chrome event horizon).
    M shows accretion disk spiral (metallic disk spinning around the void).
    CC modulates toward the event horizon for color distortion.
    The two channels create a hypnotic pull effect that morphs under lighting."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    angle = np.arctan2(yy - cy, xx - cx)
    max_r = min(h, w) / 2.0

    # Gravity well: rings that get tighter near center (logarithmic spacing)
    log_dist = np.log1p(dist / max(max_r * 0.1, 1))
    freq_gravity = 4 + rng.randint(0, 4)
    gravity_rings = (np.sin(log_dist * freq_gravity * 2 * np.pi) + 1.0) / 2.0
    # Smooth near center = event horizon (low R = chrome mirror)
    event_horizon = np.clip(1.0 - dist / (max_r * 0.15), 0, 1)
    R_pattern = gravity_rings * (1.0 - event_horizon) + (1.0 - event_horizon) * 0.1

    # Accretion disk: logarithmic spiral
    spiral_freq = 3 + rng.randint(0, 3)
    spiral = (np.sin(angle * spiral_freq + log_dist * 6) + 1.0) / 2.0
    # Disk is brightest at mid-range distance
    disk_mask = np.exp(-((dist - max_r * 0.35)**2) / (2 * (max_r * 0.2)**2))
    M_pattern = spiral * disk_mask + event_horizon * 0.8

    # CC: color shift toward event horizon
    CC_pattern = event_horizon * 0.8 + disk_mask * 0.3

    pv = np.clip((R_pattern + M_pattern) / 2.0, 0, 1)
    R_pattern = np.clip(R_pattern, 0, 1)
    M_pattern = np.clip(M_pattern, 0, 1)
    CC_pattern = np.clip(CC_pattern, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 55, "R_range": -70,
            "CC": None, "CC_range": 35}


def texture_shokk_nebula(shape, mask, seed, sm):
    """SHOKK Nebula: Cosmic gas cloud with star-forming regions.
    R channel shows diffuse dust clouds (multi-octave fractal noise = rough dust).
    M channel shows dense bright knots and filaments (chrome star cores).
    CC modulates for nebula color emission. Looks like Hubble imagery in metal."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Multi-octave Perlin-like noise for gas clouds
    dust = np.zeros((h, w), dtype=np.float32)
    stars = np.zeros((h, w), dtype=np.float32)
    for octave in range(5):
        freq = 2 ** (octave + 1)
        amp = 0.5 ** octave
        phase_x = rng.uniform(0, 100)
        phase_y = rng.uniform(0, 100)
        noise_x = np.sin(xx / max(w, 1) * freq * np.pi + phase_x) * np.cos(yy / max(h, 1) * freq * 0.7 * np.pi + phase_y)
        noise_y = np.cos(yy / max(h, 1) * freq * np.pi + phase_y * 1.3) * np.sin(xx / max(w, 1) * freq * 0.8 * np.pi + phase_x * 0.7)
        dust += (noise_x + noise_y) * amp

    dust = (dust - dust.min()) / (dust.max() - dust.min() + 1e-8)

    # Star-forming knots: bright compact regions
    n_stars = rng.randint(15, 40)
    for _ in range(n_stars):
        sx, sy = rng.randint(0, w), rng.randint(0, h)
        sr = rng.uniform(5, 25)
        brightness = rng.uniform(0.4, 1.0)
        star_dist = np.sqrt((xx - sx)**2 + (yy - sy)**2)
        star = np.exp(-(star_dist**2) / (2 * sr**2)) * brightness
        stars = np.maximum(stars, star)

    # Filaments: thin bright streaks connecting star regions
    filaments = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(5, 12)):
        fa = rng.uniform(0, np.pi)
        fp = rng.uniform(0, 100)
        fil = np.sin((xx * np.cos(fa) + yy * np.sin(fa)) / max(min(h,w), 1) * rng.uniform(3, 8) * np.pi + fp)
        fil = np.clip(fil, 0, 1) ** 3 * rng.uniform(0.3, 0.7)
        filaments = np.maximum(filaments, fil)

    R_pattern = np.clip(dust * 0.7 + filaments * 0.3, 0, 1)  # Rough dust clouds
    M_pattern = np.clip(stars * 0.7 + filaments * 0.5, 0, 1)  # Chrome star knots
    CC_pattern = np.clip(dust * 0.4 + stars * 0.6, 0, 1)  # Color in emission regions

    pv = np.clip((R_pattern + M_pattern) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 50, "R_range": -60,
            "CC": None, "CC_range": 30}


def texture_shokk_predator(shape, mask, seed, sm):
    """SHOKK Predator: Active camouflage distortion field.
    R channel shows hexagonal cell boundaries (rough edges of cloaking cells).
    M channel shows the shimmer field inside each cell (chrome cloaking surface).
    Each cell has a slightly different metallic phase, creating a Predator-style
    adaptive camo shimmer that shifts under lighting."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Hexagonal grid
    scale = min(h, w) / 256.0
    hex_size = 24 * scale
    hex_h = hex_size * np.sqrt(3)

    # Hex coordinates
    row = yy / max(hex_h, 1)
    col = xx / max(hex_size * 1.5, 1)
    row_i = np.floor(row).astype(int)
    col_i = np.floor(col).astype(int)

    # Offset for hex grid
    offset = (col_i % 2).astype(np.float32) * 0.5
    row_shifted = row - offset
    row_i_shifted = np.floor(row_shifted).astype(int)

    # Local coordinates within hex cell
    ly = (row_shifted % 1.0) - 0.5
    lx = (col % 1.0) - 0.5

    # Distance from cell center (hex approximation)
    hex_dist = np.maximum(np.abs(ly), (np.abs(ly) * 0.5 + np.abs(lx) * 0.866))

    # Cell boundaries
    border_width = 0.08
    borders = np.clip(1.0 - (0.5 - hex_dist) / border_width, 0, 1)

    # Each cell gets a unique shimmer phase based on cell coordinates
    cell_hash = (row_i_shifted * 7919 + col_i * 104729 + seed) % 1000
    cell_phase = cell_hash.astype(np.float32) / 1000.0

    # Cell shimmer: angular gradient within each cell for Fresnel-like angle dependence
    cell_angle = np.arctan2(ly, lx)
    shimmer = (np.sin(cell_angle * 3 + cell_phase * 2 * np.pi) + 1.0) / 2.0
    shimmer *= (1.0 - borders)  # No shimmer on borders

    # Distortion ripple across entire surface
    ripple = (np.sin(xx / max(w, 1) * 6 * np.pi + yy / max(h, 1) * 4 * np.pi) + 1.0) / 2.0
    distortion = ripple * 0.3

    R_pattern = np.clip(borders * 0.8 + distortion * 0.2, 0, 1)  # Rough hex borders
    M_pattern = np.clip(shimmer * 0.7 + cell_phase * 0.3, 0, 1)  # Chrome shimmer field
    pv = np.clip((borders + shimmer) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_bioform(shape, mask, seed, sm):
    """SHOKK Bioform: Alien reaction-diffusion organism.
    Uses Gray-Scott-inspired simulation to create organic spots and labyrinthine
    structures. R channel shows the activator (rough organic ridges),
    M channel shows the inhibitor (chrome smooth valleys). They're mathematically
    linked but visually distinct. The surface looks ALIVE."""
    h, w = shape
    rng = np.random.RandomState(seed)

    # Simplified reaction-diffusion via multi-frequency interference
    # (True R-D simulation is too slow; this captures the visual character)
    yf = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis]
    xf = np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :]

    # Activator pattern: leopard-like spots via threshold of summed waves
    activator = np.zeros((h, w), dtype=np.float32)
    for i in range(6):
        freq = rng.uniform(8, 25)
        angle = rng.uniform(0, np.pi)
        phase = rng.uniform(0, 2 * np.pi)
        wave = np.sin(2 * np.pi * freq * (xf * np.cos(angle) + yf * np.sin(angle)) + phase)
        activator += wave

    # Threshold to create sharp organic boundaries
    activator = activator / 6.0
    act_thresh = np.percentile(activator, 45)
    activator_binary = np.clip((activator - act_thresh) * 5, 0, 1)

    # Inhibitor: shifted spots (reaction-diffusion inhibitor is larger, smoother)
    inhibitor = np.zeros((h, w), dtype=np.float32)
    for i in range(4):
        freq = rng.uniform(5, 15)
        angle = rng.uniform(0, np.pi)
        phase = rng.uniform(0, 2 * np.pi)
        wave = np.sin(2 * np.pi * freq * (xf * np.cos(angle) + yf * np.sin(angle)) + phase)
        inhibitor += wave
    inhibitor = (inhibitor / 4.0 + 1.0) / 2.0  # Normalize to 0-1

    # Worm-like labyrinthine channels connecting the spots
    channel_freq = rng.uniform(12, 20)
    channels = np.sin(xf * channel_freq * 2 * np.pi + np.sin(yf * channel_freq * np.pi) * 2)
    channels = np.clip(channels, -0.3, 0.3) / 0.6 + 0.5

    R_pattern = np.clip(activator_binary * 0.7 + channels * 0.3, 0, 1)  # Rough organic ridges
    M_pattern = np.clip(inhibitor * 0.6 + (1.0 - activator_binary) * 0.4, 0, 1)  # Chrome valleys
    pv = np.clip((R_pattern + M_pattern) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_tesseract(shape, mask, seed, sm):
    """SHOKK Tesseract: 4D hypercube projected into 2D - exotic geometry.
    R channel shows outer cube wireframe edges. M channel shows inner cube edges
    rotated 45 degrees. Creates an optical illusion of depth and dimensionality
    where the two cubes seem to phase through each other under lighting changes."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Tiling cell size
    cell = max(40, min(h, w) // 5)
    ly = (yy % cell).astype(np.float32) / cell  # 0-1 within cell
    lx = (xx % cell).astype(np.float32) / cell

    # Outer cube: axis-aligned wireframe
    line_w = 0.04
    edge_h = np.clip(1.0 - np.minimum(ly, 1.0 - ly) / line_w, 0, 1)  # Top/bottom edges
    edge_v = np.clip(1.0 - np.minimum(lx, 1.0 - lx) / line_w, 0, 1)  # Left/right edges
    # Inner square at 60% size
    inner_off = 0.2
    inner_h = np.clip(1.0 - np.minimum(np.abs(ly - inner_off), np.abs(ly - (1-inner_off))) / line_w, 0, 1)
    inner_h *= ((lx > inner_off - line_w) & (lx < 1 - inner_off + line_w)).astype(np.float32)
    inner_v = np.clip(1.0 - np.minimum(np.abs(lx - inner_off), np.abs(lx - (1-inner_off))) / line_w, 0, 1)
    inner_v *= ((ly > inner_off - line_w) & (ly < 1 - inner_off + line_w)).astype(np.float32)

    # Corner connecting lines (perspective projection of 4D edges)
    def corner_line(y0, x0, y1, x1):
        dy, dx = y1 - y0, x1 - x0
        length = max(np.sqrt(dy**2 + dx**2), 1e-6)
        t = np.clip(((lx - x0) * dx + (ly - y0) * dy) / (length**2), 0, 1)
        px, py = x0 + t * dx, y0 + t * dy
        d = np.sqrt((lx - px)**2 + (ly - py)**2)
        return np.clip(1.0 - d / line_w, 0, 1)

    # 4 connecting edges from outer corners to inner corners
    connect = np.zeros_like(ly)
    for (oy, ox) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        iy = inner_off if oy == 0 else 1.0 - inner_off
        ix = inner_off if ox == 0 else 1.0 - inner_off
        connect = np.maximum(connect, corner_line(oy, ox, iy, ix))

    outer_cube = np.clip(np.maximum(edge_h, edge_v) + connect * 0.8, 0, 1)

    # Inner rotated cube: diamond orientation (45° rotation)
    cy, cx = 0.5, 0.5
    # Rotate local coords 45 degrees
    cos45, sin45 = np.cos(np.pi/4), np.sin(np.pi/4)
    ry = (ly - cy) * cos45 - (lx - cx) * sin45
    rx = (ly - cy) * sin45 + (lx - cx) * cos45
    diamond_size = 0.28
    diamond_h = np.clip(1.0 - np.minimum(np.abs(ry - diamond_size), np.abs(ry + diamond_size)) / line_w, 0, 1)
    diamond_h *= (np.abs(rx) < diamond_size + line_w).astype(np.float32)
    diamond_v = np.clip(1.0 - np.minimum(np.abs(rx - diamond_size), np.abs(rx + diamond_size)) / line_w, 0, 1)
    diamond_v *= (np.abs(ry) < diamond_size + line_w).astype(np.float32)
    inner_cube = np.clip(np.maximum(diamond_h, diamond_v), 0, 1)

    # Vertices: bright dots at intersections
    vertices = np.zeros_like(ly)
    for (vy, vx) in [(0,0),(0,1),(1,0),(1,1),(inner_off,inner_off),(inner_off,1-inner_off),(1-inner_off,inner_off),(1-inner_off,1-inner_off)]:
        vertices = np.maximum(vertices, np.exp(-((ly-vy)**2+(lx-vx)**2)/(line_w*3)**2) * 0.8)

    R_pattern = np.clip(outer_cube * 0.8 + vertices * 0.5, 0, 1)
    M_pattern = np.clip(inner_cube * 0.8 + vertices * 0.5, 0, 1)
    pv = np.clip((outer_cube + inner_cube + vertices) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_plasma_storm(shape, mask, seed, sm):
    """SHOKK Plasma Storm: Violent branching plasma discharge from multiple epicenters.
    R channel shows main Lichtenberg discharge paths (smooth=chrome lightning paths).
    M channel shows ionization field (metallic plasma glow surrounding paths).
    CC modulates for plasma color emission. Maximum energy pattern."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    discharge = np.zeros((h, w), dtype=np.float32)
    field = np.zeros((h, w), dtype=np.float32)

    # Multiple epicenters
    n_sources = rng.randint(3, 7)
    for src in range(n_sources):
        cx = rng.randint(w // 8, 7 * w // 8)
        cy = rng.randint(h // 8, 7 * h // 8)
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        angle = np.arctan2(yy - cy, xx - cx)

        # Lichtenberg figure: fractal branching via angular frequency modulation
        n_arms = rng.randint(4, 8)
        for arm in range(n_arms):
            arm_angle = arm * 2 * np.pi / n_arms + rng.uniform(-0.3, 0.3)
            # Main arm direction
            ang_diff = np.abs(np.sin(angle - arm_angle))
            # Width narrows with distance for branching effect
            max_dist = min(h, w) * rng.uniform(0.15, 0.4)
            arm_width = 3.0 + dist * 0.02
            arm_line = np.exp(-(ang_diff * dist)**2 / (2 * arm_width**2))
            arm_line *= np.clip(1.0 - dist / max_dist, 0, 1)
            discharge = np.maximum(discharge, arm_line * rng.uniform(0.5, 1.0))

            # Sub-branches
            for sub in range(rng.randint(2, 5)):
                sub_dist = max_dist * rng.uniform(0.2, 0.7)
                sub_angle = arm_angle + rng.uniform(-0.8, 0.8)
                sub_mask = (dist > sub_dist * 0.8) & (dist < sub_dist * 1.5)
                sub_ang_diff = np.abs(np.sin(angle - sub_angle))
                sub_line = np.exp(-(sub_ang_diff * dist)**2 / (2 * 2.0**2))
                sub_line *= sub_mask.astype(np.float32) * 0.5
                discharge = np.maximum(discharge, sub_line)

        # Epicenter core glow
        core = np.exp(-(dist**2) / (2 * 15**2)) * 0.8
        discharge = np.maximum(discharge, core)

        # Ionization field: wider diffuse glow
        ion_glow = np.exp(-(dist**2) / (2 * (max_dist * 0.6)**2)) * 0.5
        field = np.maximum(field, ion_glow)

    discharge = np.clip(discharge, 0, 1)
    field = np.clip(field, 0, 1)
    R_pattern = 1.0 - discharge  # Low R where discharge = chrome paths
    M_pattern = np.clip(field * 0.6 + discharge * 0.4, 0, 1)  # Metallic glow field
    CC_pattern = np.clip(discharge * 0.7 + field * 0.3, 0, 1)
    pv = np.clip((discharge + field) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 55, "R_range": -70,
            "CC": None, "CC_range": 30}


def texture_shokk_waveform(shape, mask, seed, sm):
    """SHOKK Waveform: Audio frequency decomposition frozen in metal.
    Horizontal bands represent frequency ranges (bass→treble bottom→top).
    R channel shows amplitude peaks (rough at loud parts).
    M channel shows frequency energy (chrome at resonant frequencies).
    The Shokker signature sound made visible - a music visualizer in spec map."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    n_bands = 16  # Frequency bands
    band_h = h / n_bands
    amplitude = np.zeros((h, w), dtype=np.float32)
    energy = np.zeros((h, w), dtype=np.float32)

    for band in range(n_bands):
        y_center = (band + 0.5) * band_h
        band_mask = np.exp(-((yy - y_center)**2) / (2 * (band_h * 0.35)**2))

        # Generate "audio" waveform for this frequency band
        freq = 1 + band * 0.5  # Lower bands = lower visual frequency
        base_amp = rng.uniform(0.3, 1.0)
        phase = rng.uniform(0, 2 * np.pi)

        # Waveform envelope: random amplitude modulation
        env_freq = rng.uniform(0.5, 3.0)
        envelope = np.abs(np.sin(xx / max(w, 1) * env_freq * np.pi + phase))
        # Bass bands get bigger amplitude bars
        bass_boost = max(0.5, 1.0 - band / n_bands * 0.7)

        # Amplitude bars (vertical bars whose height follows the waveform)
        bar_width = max(4, w // 64)
        bar_x = (xx // bar_width).astype(int)
        bar_val = np.zeros_like(xx)
        unique_bars = np.unique(bar_x)
        for bx in unique_bars[:min(len(unique_bars), 200)]:
            bar_center_x = (bx + 0.5) * bar_width
            bar_amp = base_amp * (0.3 + 0.7 * np.abs(np.sin(bx * 0.3 + phase)))
            bar_mask = (bar_x == bx).astype(np.float32)
            bar_val += bar_mask * bar_amp

        amplitude += band_mask * bar_val * bass_boost * 0.15

        # Energy: smooth sine wave per band
        wave = (np.sin(xx / max(w, 1) * freq * 2 * np.pi + phase) + 1.0) / 2.0
        energy += band_mask * wave * base_amp * 0.15

    # EKG signature pulse across center
    center_band = h // 2
    pulse_y = np.exp(-((yy - center_band)**2) / (2 * (band_h * 0.8)**2))
    pulse_x = np.sin(xx / max(w, 1) * 8 * np.pi)
    # Sharp EKG spike
    spike_pos = w * rng.uniform(0.3, 0.7)
    spike = np.exp(-((xx - spike_pos)**2) / (2 * 10**2)) * 3.0
    ekg = pulse_y * np.clip(pulse_x * 0.3 + spike, -0.5, 1.0)

    amplitude = np.clip(amplitude + ekg * 0.3, 0, 1)
    energy = np.clip(energy + ekg * 0.2, 0, 1)

    R_pattern = amplitude  # Rough at amplitude peaks
    M_pattern = energy  # Chrome at frequency energy
    pv = np.clip((amplitude + energy) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}

def texture_shokk_phase_split(shape, mask, seed, sm):
    """SHOKK Phase Split: M and R driven by perpendicular sine waves.
    Creates a shimmering effect where metallic and roughness oscillate independently."""
    h, w = shape
    rng = np.random.RandomState(seed)
    freq_m = 8 + rng.randint(0, 8)
    freq_r = 8 + rng.randint(0, 8)
    phase_m = rng.uniform(0, 2 * np.pi)
    phase_r = rng.uniform(0, 2 * np.pi)
    y = np.linspace(0, 2 * np.pi * freq_m, h, dtype=np.float32)
    x = np.linspace(0, 2 * np.pi * freq_r, w, dtype=np.float32)
    M_pattern = (np.sin(y[:, np.newaxis] + phase_m) + 1.0) / 2.0  # 0-1 vertical waves
    R_pattern = (np.cos(x[np.newaxis, :] + phase_r) + 1.0) / 2.0  # 0-1 horizontal waves
    # Unified pattern is the average for compatibility
    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 45, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}

def texture_shokk_phase_vortex(shape, mask, seed, sm):
    """SHOKK Phase Vortex: Radial M pattern + angular R pattern + radial CC.
    Creates a spinning eye effect where channels rotate independently."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    angle = np.arctan2(yy - cy, xx - cx)
    rng = np.random.RandomState(seed)
    freq_r = 3 + rng.randint(0, 5)
    freq_a = 4 + rng.randint(0, 6)
    M_pattern = (np.sin(dist / max(cy, cx) * np.pi * freq_r) + 1.0) / 2.0
    R_pattern = (np.cos(angle * freq_a + rng.uniform(0, np.pi)) + 1.0) / 2.0
    CC_pattern = (np.sin(dist / max(cy, cx) * np.pi * 2 + np.pi / 3) + 1.0) / 2.0
    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 50, "R_range": -65,
            "CC": None, "CC_range": 30}

def texture_shokk_phase_interference(shape, mask, seed, sm):
    """SHOKK Phase Interference: Two overlapping wave systems creating moiré-like
    interference patterns in each channel independently."""
    h, w = shape
    rng = np.random.RandomState(seed)
    f1 = 6 + rng.randint(0, 10)
    f2 = 6 + rng.randint(0, 10)
    a1 = rng.uniform(0, np.pi)
    a2 = rng.uniform(0, np.pi)
    y = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis]
    x = np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :]
    wave1_m = np.sin(2 * np.pi * f1 * (x * np.cos(a1) + y * np.sin(a1)))
    wave2_m = np.sin(2 * np.pi * f2 * (x * np.cos(a1 + 0.5) + y * np.sin(a1 + 0.5)))
    M_pattern = ((wave1_m + wave2_m) / 2.0 + 1.0) / 2.0
    wave1_r = np.sin(2 * np.pi * f1 * (x * np.cos(a2) + y * np.sin(a2)))
    wave2_r = np.sin(2 * np.pi * f2 * (x * np.cos(a2 + 0.7) + y * np.sin(a2 + 0.7)))
    R_pattern = ((wave1_r + wave2_r) / 2.0 + 1.0) / 2.0
    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 40, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}

def paint_shokk_phase(paint, shape, mask, seed, pm, bb):
    """Subtle paint tint for SHOKK Phase patterns - slight contrast shift."""
    if pm <= 0:
        return paint
    rng = np.random.RandomState(seed + 999)
    boost = 0.04 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + boost * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - boost * 0.3 * mask, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════
# TEXTURE VARIANTS - 50 new procedural textures for pattern variety
# Research-based: flame styles, tribal/ornamental, wave/flow, geometric, etc.
# Each gives a distinct look so pattern IDs are no longer aliased to one texture.
# ══════════════════════════════════════════════════════════════════════════

def texture_flame_sweep(shape, mask, seed, sm):
    """Classic hot rod flame - horizontal sweep, thick at bottom thinning up."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1)
    n = multi_scale_noise(shape, [3, 6, 12], [0.25, 0.4, 0.35], seed + 301)
    sweep = np.clip(1.0 - yn * 1.2 + n * 0.4, 0, 1)
    sweep = np.power(sweep, 1.2)
    cc = np.clip(16 * (1 - sweep * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": sweep, "R_range": -130.0, "M_range": 110.0, "CC": cc}

def texture_flame_ribbon(shape, mask, seed, sm):
    """Thin ribbon-like flame bands - elegant flowing strips."""
    h, w = shape
    y, x = get_mgrid((h, w))
    n = multi_scale_noise(shape, [2, 5, 10], [0.3, 0.4, 0.3], seed + 302)
    bands = np.sin(y.astype(np.float32) / max(h, 1) * np.pi * 8 + n * 2) * 0.5 + 0.5
    ribbon = np.clip(np.abs(bands - 0.5) * 2.5, 0, 1)
    cc = np.clip(16 * (1 - ribbon * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": ribbon, "R_range": -120.0, "M_range": 100.0, "CC": cc}

def texture_flame_tongues(shape, mask, seed, sm):
    """Vertical licking flame tongues - upward flicker."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = 1.0 - y.astype(np.float32) / max(h, 1)
    n = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 303)
    tongues = np.clip(yn * 1.1 + n * 0.35, 0, 1)
    tongues = np.power(tongues, 0.9)
    cc = np.clip(16 * (1 - tongues * 0.6), 0, 16).astype(np.uint8)
    return {"pattern_val": tongues, "R_range": -140.0, "M_range": 115.0, "CC": cc}

def texture_flame_teardrop(shape, mask, seed, sm):
    """Teardrop flame shapes - organic droplet flow."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1)
    xn = (x.astype(np.float32) / max(w, 1) - 0.5) * 2
    n = multi_scale_noise(shape, [5, 10, 20], [0.3, 0.4, 0.3], seed + 304)
    drop = np.clip(1.0 - yn - np.abs(xn) * 0.3 + n * 0.25, 0, 1)
    cc = np.clip(16 * (1 - drop * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": drop, "R_range": -125.0, "M_range": 105.0, "CC": cc}

def texture_flame_smoke_fade(shape, mask, seed, sm):
    """Flames fading into soft smoke - gradient with soft edges."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1)
    n = multi_scale_noise(shape, [6, 12, 24], [0.35, 0.4, 0.25], seed + 305)
    fade = np.clip((1.0 - yn) * 1.3 + n * 0.5, 0, 1)
    fade = np.power(fade, 1.5)
    cc = np.clip(16 * (1 - fade * 0.4), 0, 16).astype(np.uint8)
    return {"pattern_val": fade, "R_range": -100.0, "M_range": 90.0, "CC": cc}

def texture_flame_aggressive(shape, mask, seed, sm):
    """Sharp high-contrast flames - hellfire style."""
    h, w = shape
    n1 = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.4, 0.2], seed + 306)
    n2 = multi_scale_noise(shape, [1, 3, 6], [0.3, 0.4, 0.3], seed + 307)
    cracks = np.exp(-n1 ** 2 * 8)
    flow = np.clip((n2 + 0.2) * 1.8, 0, 1)
    agg = np.clip(cracks * 0.8 + flow * 0.2, 0, 1)
    cc = np.clip(16 * (1 - agg * 0.7), 0, 16).astype(np.uint8)
    return {"pattern_val": agg, "R_range": -150.0, "M_range": 130.0, "CC": cc}

def texture_flame_ghost_soft(shape, mask, seed, sm):
    """Very soft transparent flame wisps - ghost flames."""
    h, w = shape
    n = multi_scale_noise(shape, [8, 16, 32], [0.35, 0.4, 0.25], seed + 308)
    y, x = get_mgrid((h, w))
    yn = 1.0 - y.astype(np.float32) / max(h, 1)
    soft = np.clip(yn * 0.6 + n * 0.5, 0, 1)
    soft = np.power(soft, 2.0)
    return {"pattern_val": soft, "R_range": -60.0, "M_range": 50.0, "CC": None}

def texture_flame_ball(shape, mask, seed, sm):
    """Radial burst / fireball - explosive center."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    yy, xx = y.astype(np.float32), x.astype(np.float32)
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    r = max(cy, cx) * 0.8
    n = multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 309)
    ball = np.clip(1.0 - dist / r + n * 0.2, 0, 1)
    ball = np.power(ball, 0.8)
    cc = np.clip(16 * (1 - ball * 0.6), 0, 16).astype(np.uint8)
    return {"pattern_val": ball, "R_range": -140.0, "M_range": 120.0, "CC": cc}

def texture_flame_tribal_curves(shape, mask, seed, sm):
    """Flowing tribal tattoo-style flame curves."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1) * np.pi * 4
    xn = x.astype(np.float32) / max(w, 1) * np.pi * 4
    n = multi_scale_noise(shape, [3, 6, 12], [0.25, 0.4, 0.35], seed + 310)
    curves = np.sin(yn + np.sin(xn) * 0.7 + n * 1.5) * 0.5 + 0.5
    curves = np.clip(np.abs(curves - 0.5) * 2, 0, 1)
    cc = np.clip(16 * (1 - curves * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": curves, "R_range": -130.0, "M_range": 110.0, "CC": cc}

def texture_flame_wild(shape, mask, seed, sm):
    """Chaotic multi-directional wildfire."""
    h, w = shape
    n1 = multi_scale_noise(shape, [2, 5, 10], [0.3, 0.4, 0.3], seed + 311)
    n2 = multi_scale_noise(shape, [3, 7, 14], [0.3, 0.4, 0.3], seed + 312)
    wild = np.clip(np.abs(n1) * 0.7 + np.abs(n2) * 0.5 + 0.2, 0, 1)
    cc = np.clip(16 * (1 - wild * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": wild, "R_range": -135.0, "M_range": 115.0, "CC": cc}

def texture_tribal_bands(shape, mask, seed, sm):
    """Thick horizontal tribal bands with sin modulation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1) * np.pi * 6
    xn = x.astype(np.float32) / max(w, 1) * np.pi * 4
    band = np.sin(yn + np.sin(xn * 2) * 0.6) * 0.5 + 0.5
    band = np.clip(np.abs(band - 0.5) * 2.2, 0, 1)
    return {"pattern_val": band, "R_range": 55.0, "M_range": -25.0, "CC": None}

def texture_tribal_scroll(shape, mask, seed, sm):
    """Scroll-like ornamental curves - gothic scroll."""
    h, w = shape
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    n = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 314)
    wave = np.sin((y * 25 + n * 4) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 65.0, "M_range": 45.0, "CC": 0}

def texture_tribal_knot_dense(shape, mask, seed, sm):
    """Denser celtic-style interwoven knot."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_n = y.astype(np.float32) / h * np.pi * 8
    x_n = x.astype(np.float32) / w * np.pi * 8
    b1 = np.sin(x_n + np.sin(y_n * 2.5) * 0.9)
    b2 = np.sin(y_n + np.sin(x_n * 2.5) * 0.9)
    weave = np.clip(np.abs(b1) + np.abs(b2) - 0.5, 0, 1) * 2
    return {"pattern_val": weave, "R_range": 60.0, "M_range": -20.0, "CC": None}

def texture_tribal_meander(shape, mask, seed, sm):
    """Greek-key style continuous meander."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(20, min(h, w) // 24)
    cy = (y // cell).astype(np.int32) % 2
    cx = (x // cell).astype(np.int32) % 2
    sy = (y % cell).astype(np.float32) / cell
    sx = (x % cell).astype(np.float32) / cell
    edge = (np.abs(sy - 0.5) < 0.15) | (np.abs(sx - 0.5) < 0.15)
    corner = ((sy < 0.35) & (sx < 0.35)) | ((sy > 0.65) & (sx > 0.65))
    meander = np.clip((edge | corner).astype(np.float32), 0, 1)
    return {"pattern_val": meander, "R_range": 70.0, "M_range": -35.0, "CC": None}

def texture_paisley_flow(shape, mask, seed, sm):
    """Paisley teardrop curved ornamental flow."""
    h, w = shape
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w)
    n = multi_scale_noise(shape, [5, 10, 20], [0.3, 0.4, 0.3], seed + 317)
    wave = np.sin((y * 20 + x * 15 + n * 3) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 68.0, "M_range": 48.0, "CC": 0}

def texture_wave_vertical(shape, mask, seed, sm):
    """Vertical wave bands - upright curtain."""
    h, w = shape
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w, 1) * np.pi * 10
    n = multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 318)
    wave = np.sin(xn + n * 2) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -80.0, "M_range": 70.0, "CC": None}

def texture_wave_diagonal(shape, mask, seed, sm):
    """Diagonal wave bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    diag = (y.astype(np.float32) + x.astype(np.float32)) / max(h + w, 1) * np.pi * 12
    n = multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 319)
    wave = np.sin(diag + n * 2) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -75.0, "M_range": 65.0, "CC": None}

def texture_wave_gentle(shape, mask, seed, sm):
    """Low-frequency soft waves."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1) * np.pi * 4
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 320)
    wave = np.sin(yn + n * 1.5) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -70.0, "M_range": 60.0, "CC": None}

def texture_wave_choppy(shape, mask, seed, sm):
    """High-frequency choppy waves."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1) * np.pi * 20
    n = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 321)
    wave = np.sin(yn + n * 3) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -90.0, "M_range": 80.0, "CC": None}

def texture_chevron_bold(shape, mask, seed, sm):
    """Bold wide chevron stripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(40, min(h, w) // 12)
    v = (x.astype(np.float32) + (y.astype(np.float32) % period)) % period
    chev = (v < period // 2).astype(np.float32)
    return {"pattern_val": chev, "R_range": 75.0, "M_range": -45.0, "CC": None}

def texture_chevron_fine(shape, mask, seed, sm):
    """Finer chevron stripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(20, min(h, w) // 24)
    v = (x.astype(np.float32) + (y.astype(np.float32) % period)) % period
    chev = (v < period // 2).astype(np.float32)
    return {"pattern_val": chev, "R_range": 65.0, "M_range": -40.0, "CC": None}

def texture_herringbone(shape, mask, seed, sm):
    """Classic herringbone V zigzag."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(16, min(h, w) // 32)
    row = (y // cell).astype(np.int32) % 2
    v = (x.astype(np.float32) + row * (cell // 2)) % cell
    herr = (v < cell * 0.55).astype(np.float32)
    return {"pattern_val": herr, "R_range": 72.0, "M_range": -42.0, "CC": None}

def texture_aztec_steps(shape, mask, seed, sm):
    """Stepped Aztec-style geometric blocks."""
    h, w = shape
    y, x = get_mgrid((h, w))
    step = max(12, min(h, w) // 40)
    sy = (y // step).astype(np.int32) % 2
    sx = (x // step).astype(np.int32) % 2
    aztec = ((sy + sx) % 2).astype(np.float32)
    return {"pattern_val": aztec, "R_range": 68.0, "M_range": -38.0, "CC": None}

def texture_art_deco_fan(shape, mask, seed, sm):
    """Art deco fan / sunburst rays."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    yy, xx = y.astype(np.float32) - cy, x.astype(np.float32) - cx
    angle = np.arctan2(yy, xx)
    rays = np.sin(angle * 12) * 0.5 + 0.5
    return {"pattern_val": rays, "R_range": 80.0, "M_range": -50.0, "CC": None}

def texture_ripple_dense(shape, mask, seed, sm):
    """Denser concentric ripples."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    scale = max(h, w) / 8.0
    ripple = np.sin(dist / scale * np.pi * 2) * 0.5 + 0.5
    return {"pattern_val": ripple, "R_range": -70.0, "M_range": 55.0, "CC": None}

def texture_ripple_soft(shape, mask, seed, sm):
    """Softer broader ripples."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    scale = max(h, w) / 3.0
    n = multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 328)
    ripple = np.sin(dist / scale * np.pi + n) * 0.5 + 0.5
    return {"pattern_val": ripple, "R_range": -65.0, "M_range": 50.0, "CC": None}

def texture_pinstripe_vertical(shape, mask, seed, sm):
    """Vertical pinstripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(16, w // 30)
    stripe = (x.astype(np.int32) % period < 2).astype(np.float32)
    return {"pattern_val": stripe, "R_range": -90.0, "M_range": 80.0, "CC": 0}

def texture_pinstripe_diagonal(shape, mask, seed, sm):
    """Diagonal pinstripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    d = (y.astype(np.float32) + x.astype(np.float32)) / 2
    period = max(20, min(h, w) // 25)
    stripe = (d.astype(np.int32) % period < 2).astype(np.float32)
    return {"pattern_val": stripe, "R_range": -85.0, "M_range": 75.0, "CC": 0}

def texture_pinstripe_fine(shape, mask, seed, sm):
    """Very fine pinstripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(8, w // 60)
    stripe = (x.astype(np.int32) % period < 1).astype(np.float32)
    return {"pattern_val": stripe, "R_range": -95.0, "M_range": 85.0, "CC": 0}

def texture_grating_heavy(shape, mask, seed, sm):
    """Heavy industrial grating bars."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(24, h // 20)
    bar = (y.astype(np.int32) % period < 4).astype(np.float32)
    return {"pattern_val": bar, "R_range": -100.0, "M_range": 90.0, "CC": 0}

def texture_plasma_soft(shape, mask, seed, sm):
    """Softer plasma - subtle ghost energy."""
    h, w = shape
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.35, 0.4, 0.25], seed + 333)
    n2 = multi_scale_noise(shape, [2, 4, 8], [0.35, 0.4, 0.25], seed + 334)
    plasma = np.clip(np.abs(n1) * 0.6 + np.abs(n2) * 0.4, 0, 1)
    plasma = np.power(plasma, 1.3)
    return {"pattern_val": plasma, "R_range": -50.0, "M_range": 40.0, "CC": None}

def texture_plasma_fractal(shape, mask, seed, sm):
    """Deeply recursive high-frequency fractal noise."""
    h, w = shape
    # Much smaller tiles = higher frequency multi-scale noise
    n1 = multi_scale_noise(shape, [8, 16, 32, 64], [0.25, 0.35, 0.25, 0.15], seed + 335)
    n2 = multi_scale_noise(shape, [16, 32, 64, 128], [0.3, 0.3, 0.2, 0.2], seed + 336)
    
    # Recursive shatter effect
    frac = np.abs(np.sin(n1 * 10.0)) * 0.5 + np.abs(np.sin(n2 * 15.0)) * 0.5
    frac = np.power(frac, 1.5)
    return {"pattern_val": frac, "R_range": -80.0, "M_range": 70.0, "CC": None}

def texture_fractal_2(shape, mask, seed, sm):
    """High-frequency geometric crystal fracturing fractal (Variant 2)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    sz = 16.0
    val = np.zeros((h, w), dtype=np.float32)
    for i in range(5): # 5 octaves of geometric folding
        lx = (x % sz) / sz
        ly = (y % sz) / sz
        fold = np.abs(lx - 0.5) + np.abs(ly - 0.5)
        val += fold * (0.5 ** i)
        sz /= 2.0
    val = (np.sin(val * 20.0) * 0.5 + 0.5)
    return {"pattern_val": val, "R_range": -75.0, "M_range": 65.0, "CC": None}

def texture_fractal_3(shape, mask, seed, sm):
    """Dense interwoven fractal network overlay (Variant 3)."""
    h, w = shape
    # extremely dense interwoven network using high frequency ridges
    n1 = multi_scale_noise(shape, [12, 24, 48, 96], [0.3, 0.3, 0.2, 0.2], seed + 400)
    n2 = multi_scale_noise(shape, [10, 20, 40, 80], [0.3, 0.3, 0.2, 0.2], seed + 401)
    
    # Ridged multi-fractal style
    ridge1 = 1.0 - np.abs(n1 * 2.0 - 1.0)
    ridge2 = 1.0 - np.abs(n2 * 2.0 - 1.0)
    
    network = np.clip(ridge1 * ridge2 * 2.5, 0, 1)
    return {"pattern_val": network, "R_range": -90.0, "M_range": 80.0, "CC": None}

def texture_stardust_2(shape, mask, seed, sm):
    """Supernova starburst cluster and intense glittering core."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 200)
    
    cx, cy = w/2, h/2
    dist = np.sqrt((x - cx)**2 + (y - cy)**2) / (w * 0.5)
    core = np.clip(1.0 - dist*1.5, 0, 1)
    
    angle = np.arctan2(y - cy, x - cx)
    rays = np.sin(angle * 40.0) * 0.5 + 0.5
    rays = rays * core * 0.6
    
    # Clustered stars near center
    glitter = rng.random((h, w)).astype(np.float32)
    star_thresh = 0.99 - core * 0.05  # More likely near core
    stars = (glitter > star_thresh).astype(np.float32)
    
    burst = np.clip(core * 0.3 + rays + stars, 0, 1)
    return {"pattern_val": burst, "R_range": -60.0, "M_range": 80.0, "CC": None}

def texture_biomechanical_2(shape, mask, seed, sm):
    """Procedural intricate organic-mechanical Giger style."""
    h, w = shape
    from scipy.spatial import cKDTree
    rng = np.random.RandomState(seed + 900)
    y, x = get_mgrid((h, w))
    
    # Density of cells
    cell_s = 25.0
    grid_y, grid_x = int(h / cell_s) + 2, int(w / cell_s) + 2
    cy, cx = np.mgrid[0:grid_y, 0:grid_x]
    pts_y = (cy * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    pts_x = (cx * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    tree = cKDTree(np.column_stack((pts_y, pts_x)))
    
    coords = np.column_stack((y.flatten(), x.flatten()))
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(h, w).astype(np.float32)
    d2 = dists[:, 1].reshape(h, w).astype(np.float32)
    
    # Cell borders and centers
    edge = d2 - d1
    bones = np.clip(1.0 - d1 / (cell_s * 0.5), 0, 1)
    joints = np.where(edge < 1.5, 0.0, bones)
    
    # Mechanical tubes/wires winding through
    wires_n = multi_scale_noise(shape, [6, 12, 24], [0.4, 0.4, 0.2], seed + 901)
    tubes = np.abs(np.sin(wires_n * 20.0))
    tubes = np.power(tubes, 2.0) # sharp thin tubes
    
    mech = np.clip(joints * 0.6 + tubes * 0.8, 0, 1)
    return {"pattern_val": mech, "R_range": -85.0, "M_range": 75.0, "CC": None}

def texture_hologram_vertical(shape, mask, seed, sm):
    """Vertical scanline hologram style."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(4, h // 40)
    scan = np.sin(y.astype(np.float32) / period * np.pi * 2) * 0.5 + 0.5
    n = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 338)
    scan = np.clip(scan + n * 0.2, 0, 1)
    return {"pattern_val": scan, "R_range": -60.0, "M_range": 50.0, "CC": None}

def texture_circuit_dense(shape, mask, seed, sm):
    """Denser circuit board traces."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(8, min(h, w) // 64)
    gx = (x.astype(np.int32) // cell) % 2
    gy = (y.astype(np.int32) // cell) % 2
    thin = ((x.astype(np.int32) % cell) < 2) | ((y.astype(np.int32) % cell) < 2)
    trace = ((gx | gy) & thin).astype(np.float32)
    n = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 339)
    trace = np.clip(trace + n * 0.15, 0, 1)
    return {"pattern_val": trace, "R_range": -80.0, "M_range": 100.0, "CC": 0}

def texture_crosshatch_fine(shape, mask, seed, sm):
    """Finer crosshatch pen strokes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(12, min(h, w) // 50)
    d1 = (x.astype(np.float32) + y.astype(np.float32)) % period
    d2 = (x.astype(np.float32) - y.astype(np.float32)) % period
    hatch = ((d1 < 2) | (d2 < 2)).astype(np.float32)
    return {"pattern_val": hatch, "R_range": 50.0, "M_range": -30.0, "CC": None}

def texture_houndstooth_bold(shape, mask, seed, sm):
    """Bolder houndstooth check."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(32, min(h, w) // 24)
    cy = (y // cell) % 2
    cx = (x // cell) % 2
    sy = (y % cell).astype(np.float32) / cell
    sx = (x % cell).astype(np.float32) / cell
    check = (cy ^ cx).astype(np.float32)
    tooth = ((sy < sx) & (sy < 0.6) & (sx < 0.6)) | ((sy > sx) & (sy > 0.4) & (sx > 0.4))
    pattern = np.clip(check + tooth.astype(np.float32), 0, 1)
    return {"pattern_val": pattern, "R_range": 72.0, "M_range": -42.0, "CC": None}

def texture_hex_honeycomb(shape, mask, seed, sm):
    """Honeycomb hex grid variant."""
    h, w = shape
    y, x = get_mgrid((h, w))
    size = max(14, min(h, w) // 80)
    row = (y // (size * 1.5)).astype(np.int32)
    cx = (x + (row % 2) * size) % (size * 2)
    cy = (y % (size * 1.5)).astype(np.float32)
    dx = np.abs(cx.astype(np.float32) - size)
    dy = cy - size * 0.75
    dist = np.sqrt(dx ** 2 + dy ** 2 * 1.2)
    edge = (np.abs(dist - size * 0.6) < 2).astype(np.float32)
    return {"pattern_val": edge, "R_range": -85.0, "M_range": 95.0, "CC": 0}

def texture_damascus_vertical(shape, mask, seed, sm):
    """Vertical damascus-style grain."""
    h, w = shape
    x = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w)
    n = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 343)
    wave = np.sin((x * 30 + n * 3) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 65.0, "M_range": 48.0, "CC": 0}

def texture_leopard_sparse(shape, mask, seed, sm):
    """Sparser leopard spots."""
    h, w = shape
    rng = np.random.RandomState(seed + 344)
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 345)
    spots = np.exp(-n ** 2 * 4)
    return {"pattern_val": spots, "R_range": 40.0, "M_range": -25.0, "CC": None}

def texture_lightning_soft(shape, mask, seed, sm):
    """Softer lightning branches."""
    h, w = shape
    n = multi_scale_noise(shape, [2, 4, 8], [0.35, 0.4, 0.25], seed + 346)
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w, 1)
    branch = np.clip(np.abs(n) * 1.5 - 0.3 - xn * 0.2, 0, 1)
    return {"pattern_val": branch, "R_range": -110.0, "M_range": 120.0, "CC": 0}

def texture_turbine_swirl(shape, mask, seed, sm):
    """Turbine swirl variant - groovy spiral."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    yy, xx = y.astype(np.float32) - cy, x.astype(np.float32) - cx
    angle = np.arctan2(yy, xx)
    dist = np.sqrt(yy ** 2 + xx ** 2) / (max(cy, cx) + 1e-8)
    swirl = np.sin(angle * 5 + dist * 15) * 0.5 + 0.5
    return {"pattern_val": swirl, "R_range": -70.0, "M_range": 65.0, "CC": None}

def texture_stardust_fine(shape, mask, seed, sm):
    """Finer stardust scatter."""
    h, w = shape
    rng = np.random.RandomState(seed + 348)
    n = multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + 349)
    dust = np.clip(np.abs(n) - 0.5, 0, 1) * 2
    return {"pattern_val": dust, "R_range": -50.0, "M_range": 60.0, "CC": None}

def texture_cracked_ice_fine(shape, mask, seed, sm):
    """Finer cracked ice network."""
    h, w = shape
    n = multi_scale_noise(shape, [2, 4, 8, 16], [0.25, 0.3, 0.3, 0.15], seed + 350)
    cracks = np.exp(-n ** 2 * 10)
    return {"pattern_val": cracks, "R_range": -60.0, "M_range": 70.0, "CC": None}

def texture_snake_fine(shape, mask, seed, sm):
    """Finer snake skin scale pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    n = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 351)
    scale = max(6, min(h, w) // 60)
    row = (y // scale).astype(np.int32) % 2
    sx = (x + row * (scale // 2)) % scale
    sy = (y % scale).astype(np.float32)
    dist = np.sqrt((sx - scale / 2) ** 2 + (sy - scale / 2) ** 2)
    edge = (np.abs(dist - scale * 0.35) < 1.5).astype(np.float32) + n * 0.2
    return {"pattern_val": np.clip(edge, 0, 1), "R_range": -75.0, "M_range": 65.0, "CC": None}


# ══════════════════════════════════════════════════════════════════════════
# CLEARCOAT BLEND BASES - 10 extreme paint effects for the Blend Base dropdown
# These have DRAMATIC, unmissable color transforms designed for blending.
# ══════════════════════════════════════════════════════════════════════════

def paint_blend_arctic_freeze(paint, shape, mask, seed, pm, bb):
    """BLEND: Deep icy blue freeze - unmissable cold transformation."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    # Heavy desaturation + extreme blue push
    paint = paint * (1 - 0.65 * pm * mask[:,:,np.newaxis]) + gray * 0.65 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.20 * pm * mask[:,:,np.newaxis], 0, 1)  # darken base
    paint[:,:,0] = np.clip(paint[:,:,0] - 0.18 * pm * mask, 0, 1)  # kill red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.08 * pm * mask, 0, 1)  # slight green for ice
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.35 * pm * mask, 0, 1)  # massive blue tint
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_inferno(paint, shape, mask, seed, pm, bb):
    """BLEND: Hot ember red/orange - fiery transformation."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.50 * pm * mask[:,:,np.newaxis]) + gray * 0.50 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.15 * pm * mask[:,:,np.newaxis], 0, 1)  # darken
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.40 * pm * mask, 0, 1)  # massive red push
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.15 * pm * mask, 0, 1)  # orange component
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.25 * pm * mask, 0, 1)  # kill blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_toxic(paint, shape, mask, seed, pm, bb):
    """BLEND: Sickly neon green - toxic radioactive glow."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] - 0.15 * pm * mask, 0, 1)  # kill red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.40 * pm * mask, 0, 1)  # massive green
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.20 * pm * mask, 0, 1)  # kill blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_royal_purple(paint, shape, mask, seed, pm, bb):
    """BLEND: Deep royal purple - majestic violet transformation."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.50 * pm * mask[:,:,np.newaxis]) + gray * 0.50 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.18 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.22 * pm * mask, 0, 1)  # red for purple
    paint[:,:,1] = np.clip(paint[:,:,1] - 0.20 * pm * mask, 0, 1)  # kill green
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.35 * pm * mask, 0, 1)  # heavy blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_midnight(paint, shape, mask, seed, pm, bb):
    """BLEND: Near-black midnight - extreme darkening and desaturation."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.70 * pm * mask[:,:,np.newaxis]) + gray * 0.70 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.45 * pm * mask[:,:,np.newaxis], 0, 1)  # extreme darken
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05 * pm * mask, 0, 1)  # hint of blue
    paint = np.clip(paint + bb * 0.2 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_solar_gold(paint, shape, mask, seed, pm, bb):
    """BLEND: Rich warm gold - luxury golden transformation."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.45 * pm * mask[:,:,np.newaxis]) + gray * 0.45 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.30 * pm * mask, 0, 1)  # warm gold red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.18 * pm * mask, 0, 1)  # warm gold green
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.15 * pm * mask, 0, 1)  # kill cool blue
    paint = np.clip(paint + bb * 0.4 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_blood_wash(paint, shape, mask, seed, pm, bb):
    """BLEND: Deep blood red wash - dark dramatic crimson."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.25 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.45 * pm * mask, 0, 1)  # massive red
    paint[:,:,1] = np.clip(paint[:,:,1] - 0.20 * pm * mask, 0, 1)  # kill green
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.20 * pm * mask, 0, 1)  # kill blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_electric_cyan(paint, shape, mask, seed, pm, bb):
    """BLEND: Electric cyan shock - vivid teal-blue neon."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.50 * pm * mask[:,:,np.newaxis]) + gray * 0.50 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] - 0.20 * pm * mask, 0, 1)  # kill red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.35 * pm * mask, 0, 1)  # teal green
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.35 * pm * mask, 0, 1)  # teal blue
    paint = np.clip(paint + bb * 0.4 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_bronze_heat(paint, shape, mask, seed, pm, bb):
    """BLEND: Warm bronze patina - aged metallic warmth."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.40 * pm * mask[:,:,np.newaxis]) + gray * 0.40 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.25 * pm * mask, 0, 1)  # bronze red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.12 * pm * mask, 0, 1)  # bronze warmth
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.18 * pm * mask, 0, 1)  # kill cool
    paint = np.clip(paint + bb * 0.35 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_ghost_silver(paint, shape, mask, seed, pm, bb):
    """BLEND: Ghostly silver bleach - pale ethereal washout."""
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    # Near-total desaturation + brighten for ghostly silver
    paint = paint * (1 - 0.75 * pm * mask[:,:,np.newaxis]) + gray * 0.75 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + 0.20 * pm * mask[:,:,np.newaxis], 0, 1)  # brighten (bleach)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.08 * pm * mask, 0, 1)  # cool tint
    paint = np.clip(paint + bb * 0.5 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

# Curated blend base entries - these go in BASE_REGISTRY alongside normal bases
BLEND_BASES = {
    "cc_arctic_freeze":  {"M": 200, "R": 20, "CC": 16, "paint_fn": paint_blend_arctic_freeze,  "desc": "BLEND: Deep icy blue freeze", "blend_only": True},
    "cc_inferno":        {"M": 150, "R": 40, "CC": 16, "paint_fn": paint_blend_inferno,         "desc": "BLEND: Hot ember red/orange fire", "blend_only": True},
    "cc_toxic":          {"M": 100, "R": 60, "CC": 16, "paint_fn": paint_blend_toxic,           "desc": "BLEND: Sickly neon green radioactive", "blend_only": True},
    "cc_royal_purple":   {"M": 120, "R": 30, "CC": 16, "paint_fn": paint_blend_royal_purple,    "desc": "BLEND: Deep royal purple majestic", "blend_only": True},
    "cc_midnight":       {"M": 5,   "R": 8,  "CC": 16, "paint_fn": paint_blend_midnight,        "desc": "BLEND: Near-black midnight void", "blend_only": True},
    "cc_solar_gold":     {"M": 230, "R": 25, "CC": 16, "paint_fn": paint_blend_solar_gold,      "desc": "BLEND: Rich warm luxury gold", "blend_only": True},
    "cc_blood_wash":     {"M": 80,  "R": 45, "CC": 16, "paint_fn": paint_blend_blood_wash,      "desc": "BLEND: Deep dramatic crimson wash", "blend_only": True},
    "cc_electric_cyan":  {"M": 180, "R": 15, "CC": 16, "paint_fn": paint_blend_electric_cyan,   "desc": "BLEND: Vivid teal-blue neon shock", "blend_only": True},
    "cc_bronze_heat":    {"M": 200, "R": 50, "CC": 16, "paint_fn": paint_blend_bronze_heat,     "desc": "BLEND: Warm bronze aged patina", "blend_only": True},
    "cc_ghost_silver":   {"M": 240, "R": 10, "CC": 16, "paint_fn": paint_blend_ghost_silver,    "desc": "BLEND: Ghostly pale silver bleach", "blend_only": True},
}


# --- BASE MATERIAL REGISTRY ---
# Organized by category, alphabetized within each section. 58 bases total.
BASE_REGISTRY = {
    # ── STANDARD FINISHES ──────────────────────────────────────────────
    "ceramic":          {"M": 60,  "R": 8,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Ultra-smooth ceramic coating deep wet shine",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 30, "noise_R": 15},
    "gloss":            {"M": 0,   "R": 20,  "CC": 16, "paint_fn": paint_none,            "desc": "Standard glossy clearcoat"},
    "piano_black":      {"M": 5,   "R": 3,   "CC": 16, "paint_fn": paint_none,            "desc": "Deep piano black ultra-gloss mirror finish",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 10},
    "satin":            {"M": 0,   "R": 100, "CC": 50,  "paint_fn": paint_none,            "desc": "Soft satin semi-gloss clearcoat - CC=50 protective but not gloss"},
    "scuffed_satin":    {"M": 0,   "R": 80,  "CC": 16,  "paint_fn": paint_none,            "desc": "Clearcoated but with visible surface texture - orange peel lite"},
    "silk":             {"M": 30,  "R": 85,  "CC": 16,  "paint_fn": paint_silk_sheen,      "desc": "Silky smooth fabric-like sheen"},
    "wet_look":         {"M": 10,  "R": 5,   "CC": 16, "paint_fn": paint_wet_gloss,       "desc": "Deep wet clearcoat show shine"},
    # ── METALLIC & FLAKE ──────────────────────────────────────────────
    "copper":           {"M": 190, "R": 55,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Warm oxidized copper metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 35, "noise_R": 20},
    "diamond_coat":     {"M": 220, "R": 3,   "CC": 16, "paint_fn": paint_diamond_sparkle, "desc": "Diamond dust ultra-fine sparkle coat",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 25, "noise_R": 8},
    "electric_ice":     {"M": 240, "R": 10,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "Icy electric blue metallic - cold neon shimmer",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 8},
    "gunmetal":         {"M": 220, "R": 40,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Dark aggressive blue-gray metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 30, "noise_R": 15},
    "metallic":         {"M": 200, "R": 50,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Standard metallic with visible flake",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 40, "noise_R": 18},
    "pearl":            {"M": 100, "R": 40,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Pearlescent iridescent sheen",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 12},
    "pearlescent_white":{"M": 120, "R": 30,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Tri-coat pearlescent white deep sparkle",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 10},
    "plasma_metal":     {"M": 230, "R": 18,  "CC": 16, "paint_fn": paint_plasma_shift,    "desc": "Electric plasma purple-blue metallic shift",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 12},
    "rose_gold":        {"M": 240, "R": 12,  "CC": 16, "paint_fn": paint_rose_gold_tint,  "desc": "Pink-gold metallic warm shimmer",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 10},
    "satin_gold":       {"M": 235, "R": 60,  "CC": 0,  "paint_fn": paint_warm_metal,      "desc": "Satin gold metallic warm sheen",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 18},
    # ── CHROME & MIRROR ───────────────────────────────────────────────
    "chrome":           {"M": 255, "R": 2,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Pure mirror chrome",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "dark_chrome":      {"M": 250, "R": 5,   "CC": 0,  "paint_fn": paint_smoked_darken,   "desc": "Smoked dark chrome black mirror",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.45, "perlin_lacunarity": 2.0, "noise_M": 35, "noise_R": 12},
    "mercury":          {"M": 255, "R": 3,   "CC": 0,  "paint_fn": paint_mercury_pool,    "desc": "Liquid mercury pooling mirror - desaturated chrome flow",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.5, "perlin_lacunarity": 1.8, "noise_M": 30, "noise_R": 10},
    # mirror_gold removed - M=255 G=2 identical to chrome; gold tint comes from paint color layer
    "satin_chrome":     {"M": 250, "R": 45,  "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "BMW silky satin chrome",
                         "noise_scales": [4, 8], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 25},
    "surgical_steel":   {"M": 245, "R": 6,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Medical grade mirror surgical steel",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 15, "noise_R": 8},
    # ── CANDY & CLEARCOAT VARIANTS ────────────────────────────────────
    "candy":            {"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Deep wet candy transparent glass",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 35, "noise_R": 15},
    "candy_chrome":     {"M": 250, "R": 4,   "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Candy-tinted chrome - deep color over mirror base",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 60, "noise_R": 15},
    "clear_matte":      {"M": 0,   "R": 160, "CC": 80,  "paint_fn": paint_none,            "desc": "Matte clearcoat - has a coat but it's rough (CC=80 scuffed)"},
    "smoked":           {"M": 15,  "R": 10,  "CC": 16, "paint_fn": paint_smoked_darken,   "desc": "Smoked tinted darkened clearcoat"},
    "spectraflame":     {"M": 245, "R": 8,   "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Hot Wheels candy-over-chrome deep sparkle",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 80, "noise_R": 25},
    "tinted_clear":     {"M": 40,  "R": 8,   "CC": 16, "paint_fn": paint_tinted_clearcoat,"desc": "Deep tinted clearcoat over base color",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 12, "noise_R": 10},
    # ── GAP-FILL: COATED OVER METAL / DEEP GLASS ────────────────────────
    "hydrographic":     {"M": 240, "R": 5,   "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Mirror metal under maximum deep clearcoat - wet glass over chrome",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 20, "noise_R": 6},
    "jelly_pearl":      {"M": 120, "R": 10,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Ultra-wet candy pearl - max depth, like looking through colored glass",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 18, "noise_R": 8},
    "orange_peel_gloss":{"M": 0,   "R": 160, "CC": 16, "paint_fn": paint_none,            "desc": "Orange-peel texture sealed under thick clearcoat",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.7, "perlin_lacunarity": 2.2, "noise_M": 0, "noise_R": 40},
    "tinted_lacquer":   {"M": 130, "R": 80,  "CC": 16, "paint_fn": paint_tinted_clearcoat,"desc": "Semi-metallic under thick lacquer pour - depth and warmth",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.4, "perlin_lacunarity": 1.8, "noise_M": 25, "noise_R": 20},
    # ── MATTE & FLAT ─────────────────────────────────────────────────
    "blackout":         {"M": 30,  "R": 220, "CC": 35,  "paint_fn": paint_none,            "desc": "Stealth murdered-out - thin protective matte coat (CC=35)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 15},
    "flat_black":       {"M": 0,   "R": 250, "CC": 0,  "paint_fn": paint_none,            "desc": "Dead flat zero-sheen black - no reflection at all"},
    "frozen":           {"M": 225, "R": 140, "CC": 0,  "paint_fn": paint_subtle_flake,    "desc": "Frozen icy matte metal",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 30},
    "frozen_matte":     {"M": 210, "R": 160, "CC": 0,  "paint_fn": paint_subtle_flake,    "desc": "BMW Individual frozen matte metallic",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "matte":            {"M": 0,   "R": 215, "CC": 0,  "paint_fn": paint_none,            "desc": "Flat matte zero shine"},
    "vantablack":       {"M": 0,   "R": 255, "CC": 0,  "paint_fn": paint_none,            "desc": "Absolute void zero reflection",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 3, "noise_R": 5},
    "volcanic":         {"M": 80,  "R": 180, "CC": 70,  "paint_fn": paint_volcanic_ash,    "desc": "Volcanic ash coating - the ash layer IS the coat, heavily degraded (CC=70)"},
    # ── BRUSHED & DIRECTIONAL GRAIN ──────────────────────────────────
    "brushed_aluminum": {"M": 230, "R": 55,  "CC": 0,  "paint_fn": paint_brushed_grain,   "desc": "Brushed natural aluminum directional grain",
                         "brush_grain": True, "noise_M": 15, "noise_R": 30},
    "brushed_titanium": {"M": 180, "R": 70,  "CC": 0,  "paint_fn": paint_brushed_grain,   "desc": "Heavy directional titanium grain",
                         "brush_grain": True, "noise_M": 25, "noise_R": 45},
    "satin_metal":      {"M": 235, "R": 65,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Subtle brushed satin metallic",
                         "brush_grain": True, "noise_R": 20},
    # ── TACTICAL & INDUSTRIAL ────────────────────────────────────────
    "cerakote":         {"M": 40,  "R": 130, "CC": 30,  "paint_fn": paint_tactical_flat,   "desc": "Mil-spec ceramic tactical coating - hard coat, low sheen (CC=30)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 20},
    "duracoat":         {"M": 25,  "R": 170, "CC": 35,  "paint_fn": paint_tactical_flat,   "desc": "Tactical epoxy coat - air-dried dull finish (CC=35 faint protection)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.45, "perlin_lacunarity": 2.0, "noise_M": 12, "noise_R": 25},
    "powder_coat":      {"M": 20,  "R": 155, "CC": 40,  "paint_fn": paint_none,            "desc": "Thick powder coat - cured protective surface, semi-matte (CC=40)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 30},
    "rugged":           {"M": 50,  "R": 190, "CC": 25,  "paint_fn": paint_tactical_flat,   "desc": "Rugged off-road coat - very rough protective layer (CC=25 barely there)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 35},
    # ── RAW METAL & WEATHERED ────────────────────────────────────────
    "anodized":         {"M": 170, "R": 80,  "CC": 0,  "paint_fn": paint_subtle_flake,    "desc": "Gritty matte anodized aluminum",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "burnt_headers":    {"M": 190, "R": 45,  "CC": 0,  "paint_fn": paint_burnt_metal,     "desc": "Exhaust header heat-treated gold-blue oxide",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 20},
    "galvanized":       {"M": 195, "R": 65,  "CC": 30,  "paint_fn": paint_galvanized_speckle, "desc": "Hot-dip galvanized zinc - the zinc IS the coat (CC=30 thin metallic coat)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 25, "noise_R": 30},
    "heat_treated":     {"M": 185, "R": 35,  "CC": 0,  "paint_fn": paint_heat_tint,       "desc": "Heat-treated titanium blue-gold zones",
                         "noise_scales": [8, 16], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 15},
    "patina_bronze":    {"M": 160, "R": 90,  "CC": 0,  "paint_fn": paint_patina_green,    "desc": "Aged oxidized bronze with green patina",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35},
    "patina_coat":      {"M": 100, "R": 150, "CC": 50, "paint_fn": paint_patina_green,    "desc": "Old weathered paint with fresh satin clearcoat sprayed over - protected patina",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 35},
    "battle_patina":    {"M": 200, "R": 150, "CC": 50, "paint_fn": paint_burnt_metal,     "desc": "Heavily worn metal base with thin protective satin coat - used racecar look",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 40},
    "cerakote_gloss":   {"M": 200, "R": 70,  "CC": 16, "paint_fn": paint_tactical_flat,   "desc": "Industrial ceramic coating over metal - glossy sealed finish",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 20},
    "raw_aluminum":     {"M": 240, "R": 30,  "CC": 0,  "paint_fn": paint_raw_aluminum,    "desc": "Bare unfinished aluminum sheet metal",
                         "noise_scales": [4, 8], "noise_weights": [0.4, 0.6], "noise_M": 25, "noise_R": 25},
    "sandblasted":      {"M": 200, "R": 180, "CC": 0,  "paint_fn": paint_none,            "desc": "Raw sandblasted metal rough texture",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 30},
    # titanium_raw removed - M=200 G=50 identical to metallic; differentiate via paint color
    # ── EXOTIC & COLOR-SHIFT ─────────────────────────────────────────
    "chameleon":        {"M": 160, "R": 25,  "CC": 16, "paint_fn": paint_cp_chameleon,  "desc": "Dual-tone chameleon color-shift driven by surface angle",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 60, "noise_R": 35},
    "iridescent":       {"M": 210, "R": 20,  "CC": 16, "paint_fn": paint_iridescent_shift,"desc": "Rainbow angle-shift iridescent wrap",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 50, "noise_R": 25},
    # ── WRAP & COATING ───────────────────────────────────────────────
    "liquid_wrap":      {"M": 80,  "R": 110, "CC": 50,  "paint_fn": paint_satin_wrap,      "desc": "Liquid rubber peel coat - the rubber IS the clearcoat layer (CC=50 satin-ish)"},
    "primer":           {"M": 0,   "R": 200, "CC": 20,  "paint_fn": paint_primer_flat,     "desc": "Raw primer - thin base coat, barely sealing (CC=20 barely there)"},
    "satin_wrap":       {"M": 0,   "R": 130, "CC": 60,  "paint_fn": paint_satin_wrap,      "desc": "Vinyl wrap satin surface - the film IS the coat layer (CC=60)"},
    # ── ORGANIC / PERLIN NOISE ───────────────────────────────────────
    "living_matte":     {"M": 0,   "R": 180, "CC": 45,  "paint_fn": paint_none,            "desc": "Organic matte - natural coat with Perlin surface variation (CC=45 protected)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "noise_M": 0, "noise_R": 30},
    "organic_metal":    {"M": 210, "R": 45,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Organic flowing metallic with Perlin noise terrain",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "noise_M": 35, "noise_R": 20, "noise_CC": 8},
    "terrain_chrome":   {"M": 250, "R": 8,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Chrome with Perlin terrain-like distortion in roughness",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.45, "noise_M": 0, "noise_R": 25},
    # ── WORN & DEGRADED CLEARCOAT (CC=81–255) ────────────────────────────────
    # The full 81-255 spectrum - progressive clearcoat breakdown.
    # Perfect second-layer candidates for the Dual Layer Base system.
    "track_worn":       {"M": 210, "R": 55,  "CC": 100, "paint_fn": paint_subtle_flake,   "desc": "Race-worn metallic - degraded clearcoat, battle-scarred (CC=100)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 20, "noise_CC": 15},
    "sun_fade":         {"M": 60,  "R": 130, "CC": 120, "paint_fn": paint_none,            "desc": "UV sun-damaged paint - bleached, chalky, coat breaking down (CC=120)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 30, "noise_CC": 20},
    "acid_etch":        {"M": 100, "R": 110, "CC": 130, "paint_fn": paint_patina_green,    "desc": "Acid-rain etched surface - pitted with partial clearcoat failure (CC=130)",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 20, "noise_R": 25, "noise_CC": 25},
    "oxidized":         {"M": 180, "R": 70,  "CC": 160, "paint_fn": paint_burnt_metal,     "desc": "Oxidized metallic - rust bloom, clearcoat near-destroyed (CC=160)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35, "noise_CC": 30},
    "chalky_base":      {"M": 10,  "R": 195, "CC": 180, "paint_fn": paint_primer_flat,     "desc": "Chalk-oxidized paint - heavy flat haze, nearly no coat left (CC=180)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.65, "perlin_lacunarity": 2.0, "noise_M": 5, "noise_R": 35, "noise_CC": 30},
    "barn_find":        {"M": 80,  "R": 160, "CC": 210, "paint_fn": paint_primer_flat,     "desc": "Barn-find condition - decades of clearcoat breakdown, deep chalky flat (CC=210)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.7, "perlin_lacunarity": 1.8, "noise_M": 10, "noise_R": 40, "noise_CC": 35},
    "crumbling_clear":  {"M": 30,  "R": 180, "CC": 235, "paint_fn": paint_volcanic_ash,    "desc": "Peeling, crumbling clearcoat - paint underneath showing through (CC=235)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.2, "noise_M": 8, "noise_R": 30, "noise_CC": 35},
    "destroyed_coat":   {"M": 0,   "R": 210, "CC": 255, "paint_fn": paint_none,            "desc": "Completely destroyed clearcoat - maximum degradation, pure chalk-rough (CC=255)"},
}
# Register clearcoat blend bases into main registry
BASE_REGISTRY.update(BLEND_BASES)

# ================================================================
# BATCH 1: Dedicated texture functions for broken pattern aliases
# ================================================================

def texture_matrix_rain(shape, mask, seed, sm):
    """Matrix rain - falling vertical character-like rain columns."""
    h, w = shape
    rng = np.random.RandomState(seed + 7001)
    pattern = np.zeros((h, w), dtype=np.float32)
    # Random column positions
    n_cols = max(20, w // 8)
    col_xs = rng.randint(0, w, n_cols)
    for i in range(n_cols):
        cx = col_xs[i]
        col_len = rng.randint(h // 6, h // 2)
        y_offset = rng.randint(0, h)
        char_spacing = rng.randint(4, 10)
        # Each column has cascading bright dots that fade downward
        for cy in range(0, col_len, char_spacing):
            y_pos = (y_offset + cy) % h
            brightness = 1.0 - (cy / col_len) * 0.8  # fade down
            # Each "character" is a small bright block ~3-5px
            char_h = rng.randint(2, 5)
            char_w = rng.randint(1, 3)
            y_lo = max(0, y_pos)
            y_hi = min(h, y_pos + char_h)
            x_lo = max(0, cx - char_w // 2)
            x_hi = min(w, cx + char_w // 2 + 1)
            pattern[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                pattern[y_lo:y_hi, x_lo:x_hi], brightness)
    return {"pattern_val": pattern, "R_range": -100.0, "M_range": 140.0, "CC": 0}

def texture_giraffe(shape, mask, seed, sm):
    """Giraffe spots - large irregular Voronoi polygon patches with thin borders."""
    h, w = shape
    from scipy.spatial import cKDTree
    rng = np.random.RandomState(seed + 7002)
    cell_s = 50.0  # Large cells (40-60px range)
    grid_y = int(h / cell_s) + 2
    grid_x = int(w / cell_s) + 2
    cy_g, cx_g = np.mgrid[0:grid_y, 0:grid_x]
    pts_y = (cy_g * cell_s + rng.rand(grid_y, grid_x) * cell_s * 0.8).flatten()
    pts_x = (cx_g * cell_s + rng.rand(grid_y, grid_x) * cell_s * 0.8).flatten()
    points = np.column_stack((pts_y, pts_x))
    tree = cKDTree(points)
    y, x = get_mgrid((h, w))
    coords = np.column_stack((y.flatten().astype(np.float32),
                               x.flatten().astype(np.float32)))
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(h, w).astype(np.float32)
    d2 = dists[:, 1].reshape(h, w).astype(np.float32)
    edge = d2 - d1
    # Thin dark borders (border_width ~3px), patches are bright
    border = np.clip(edge / 3.0, 0, 1)
    return {"pattern_val": border, "R_range": 50.0, "M_range": -60.0, "CC": 0}

def texture_checkered_flag(shape, mask, seed, sm):
    """Checkered flag - clean alternating chess-board squares."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = 25  # ~25px squares
    row = (y // cell).astype(np.int32) % 2
    col = (x // cell).astype(np.int32) % 2
    pattern = (row ^ col).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -50.0, "CC": 0}

def texture_zebra_stripe(shape, mask, seed, sm):
    """Zebra stripe - organic wavy horizontal stripes with noise distortion."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Use noise to wobble stripe boundaries
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7004)
    stripe_freq = 0.08  # ~12px stripe width
    warped_y = y.astype(np.float32) + n * 25.0  # organic wobble
    wave = np.sin(warped_y * stripe_freq * np.pi * 2)
    # Sharp threshold for bold stripes, slight variation for broken edges
    n2 = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 7005)
    threshold = 0.0 + n2 * 0.15
    pattern = (wave > threshold).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 70.0, "M_range": -60.0, "CC": 0}

def texture_fingerprint(shape, mask, seed, sm):
    """Fingerprint - concentric swirling ridges from center."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    dy = (y.astype(np.float32) - cy)
    dx = (x.astype(np.float32) - cx)
    angle = np.arctan2(dy, dx)
    dist = np.sqrt(dy ** 2 + dx ** 2)
    # Angular perturbation via noise for swirl effect
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7006)
    # Spiral: ridges = sin(distance + angle_perturbation)
    ridge_freq = 0.35  # ~3px ridge spacing
    swirl_strength = 3.0
    spiral = np.sin((dist * ridge_freq + angle * swirl_strength + n * 4.0) * np.pi)
    ridges = (np.abs(spiral) < 0.3).astype(np.float32)
    return {"pattern_val": ridges, "R_range": 80.0, "M_range": -35.0, "CC": None}

def texture_data_stream(shape, mask, seed, sm):
    """Data stream - flowing horizontal data packet bands with digital blocks."""
    h, w = shape
    rng = np.random.RandomState(seed + 7007)
    pattern = np.zeros((h, w), dtype=np.float32)
    # Create horizontal bands of data at various y positions
    n_bands = max(10, h // 20)
    for _ in range(n_bands):
        band_y = rng.randint(0, h)
        band_h = rng.randint(3, 8)
        y_lo = max(0, band_y)
        y_hi = min(h, band_y + band_h)
        if y_hi <= y_lo:
            continue
        # Within each band, place blocks (packets) of varying width
        n_packets = rng.randint(5, w // 10)
        x_pos = 0
        for _ in range(n_packets):
            gap = rng.randint(2, 15)
            pkt_w = rng.randint(4, 30)
            x_pos += gap
            if x_pos >= w:
                break
            x_end = min(w, x_pos + pkt_w)
            brightness = rng.uniform(0.5, 1.0)
            pattern[y_lo:y_hi, x_pos:x_end] = brightness
            x_pos = x_end
    return {"pattern_val": pattern, "R_range": -90.0, "M_range": 120.0, "CC": 0}

def texture_chainlink(shape, mask, seed, sm):
    """Chainlink fence - diagonal diamond mesh pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = 25.0  # ~25px cell size
    line_w = 2.0  # thin wire
    # Diamond grid = rotated square grid (45 degrees)
    # Two sets of diagonal lines
    d1 = ((y.astype(np.float32) + x.astype(np.float32)) % cell)
    d2 = ((y.astype(np.float32) - x.astype(np.float32) + 10000) % cell)
    wire1 = (d1 < line_w).astype(np.float32)
    wire2 = (d2 < line_w).astype(np.float32)
    pattern = np.clip(wire1 + wire2, 0, 1)
    return {"pattern_val": pattern, "R_range": -80.0, "M_range": 100.0, "CC": 0}

def texture_pentagram_star(shape, mask, seed, sm):
    """Pentagram star - tiled five-pointed stars in a grid."""
    h, w = shape
    rng = np.random.RandomState(seed + 7009)
    y, x = get_mgrid((h, w))
    cell = 60  # tile size
    pattern = np.zeros((h, w), dtype=np.float32)
    # For each tile, draw a 5-pointed star using angular math
    ty = (y % cell).astype(np.float32) - cell / 2.0
    tx = (x % cell).astype(np.float32) - cell / 2.0
    angle = np.arctan2(ty, tx)
    dist = np.sqrt(ty ** 2 + tx ** 2)
    # Star shape: radius oscillates 5 times around the circle
    # r(theta) = outer where cos(5*theta/2) peaks, inner otherwise
    outer_r = cell * 0.42
    inner_r = cell * 0.18
    # 5-pointed star equation
    star_angle = np.abs(((angle / (2 * np.pi) * 5) % 1.0) - 0.5) * 2.0  # 0-1 sawtooth
    star_r = inner_r + (outer_r - inner_r) * (1.0 - star_angle)
    inside = (dist < star_r).astype(np.float32)
    return {"pattern_val": inside, "R_range": 70.0, "M_range": -50.0, "CC": 0}

def texture_biohazard_symbol(shape, mask, seed, sm):
    """Biohazard trefoil symbol - three overlapping crescents tiled in a grid."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = 80  # tile size for each symbol
    # Local coordinates within each tile
    ly = (y % cell).astype(np.float32) - cell / 2.0
    lx = (x % cell).astype(np.float32) - cell / 2.0
    pattern = np.zeros((h, w), dtype=np.float32)
    R = cell * 0.32  # outer radius of each crescent arc
    r = cell * 0.16  # inner radius (cutout)
    center_hole = cell * 0.08  # center hole radius
    # Three crescents at 120-degree intervals
    for k in range(3):
        a = k * 2.0 * np.pi / 3.0
        # Center of each crescent arc, offset from tile center
        offset = cell * 0.14
        cy_k = np.sin(a) * offset
        cx_k = np.cos(a) * offset
        dy = ly - cy_k
        dx = lx - cx_k
        dist = np.sqrt(dy ** 2 + dx ** 2)
        crescent = ((dist < R) & (dist > r)).astype(np.float32)
        pattern = np.maximum(pattern, crescent)
    # Cut out center hole
    center_dist = np.sqrt(ly ** 2 + lx ** 2)
    pattern = np.where(center_dist < center_hole, 0.0, pattern)
    return {"pattern_val": pattern, "R_range": 65.0, "M_range": -40.0, "CC": 0}

def texture_feather_barb(shape, mask, seed, sm):
    """Feather barb - central spine with diagonal parallel barbs branching off."""
    h, w = shape
    y, x = get_mgrid((h, w))
    tile_h = 60  # vertical tile for each feather unit
    tile_w = 80  # horizontal tile
    # Local coordinates
    ly = (y % tile_h).astype(np.float32)
    lx = (x % tile_w).astype(np.float32)
    pattern = np.zeros((h, w), dtype=np.float32)
    # Central rachis (spine) - horizontal center line of each tile
    spine_y = tile_h / 2.0
    spine_thick = 2.0
    spine = (np.abs(ly - spine_y) < spine_thick).astype(np.float32)
    pattern = np.maximum(pattern, spine)
    # Diagonal barbs branching off the spine
    barb_spacing = 4.0  # spacing between parallel barbs
    barb_thick = 1.2
    # Upper barbs: angled lines going up-right from spine
    # Line equation: y = spine_y - (x - x0) * slope => x + y*slope = const
    slope = 0.6
    upper_region = ly < spine_y
    diag_upper = ((lx * slope + ly) % barb_spacing)
    upper_barbs = ((diag_upper < barb_thick) & upper_region).astype(np.float32)
    # Lower barbs: angled lines going down-right from spine
    lower_region = ly > spine_y
    diag_lower = ((lx * slope - ly + tile_h) % barb_spacing)
    lower_barbs = ((diag_lower < barb_thick) & lower_region).astype(np.float32)
    pattern = np.maximum(pattern, upper_barbs)
    pattern = np.maximum(pattern, lower_barbs)
    return {"pattern_val": pattern, "R_range": 55.0, "M_range": -30.0, "CC": None}


# ══════════════════════════════════════════════════════════════════════════
# BATCH 2 — Unique texture functions for formerly-duplicated patterns
# Each returns {"pattern_val": float32[H,W] 0-1, "R_range", "M_range", "CC"}
# ══════════════════════════════════════════════════════════════════════════

def texture_binary_code_v2(shape, mask, seed, sm):
    """Binary code — columns of 1/0 rectangular cells like a binary readout."""
    h, w = shape
    rng = np.random.RandomState(seed)
    cell_w = max(8, min(h, w) // 64)
    cell_h = max(12, int(cell_w * 1.5))
    rows = (h + cell_h - 1) // cell_h
    cols = (w + cell_w - 1) // cell_w
    bits = rng.randint(0, 2, (rows, cols)).astype(np.float32)
    result = np.repeat(np.repeat(bits, cell_h, axis=0), cell_w, axis=1)[:h, :w]
    y, x = get_mgrid((h, w))
    # Column separator lines
    gap = max(1, cell_w // 6)
    col_gap = ((x % cell_w) < gap).astype(np.float32) * 0.3
    row_gap = ((y % cell_h) < max(1, cell_h // 8)).astype(np.float32) * 0.15
    pv = np.clip(result * 0.85 - col_gap - row_gap, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -100.0, "M_range": 150.0, "CC": 0}

def texture_palm_frond_v2(shape, mask, seed, sm):
    """Palm frond — radiating leaf veins with central spine, tiled."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    y_arr, x_arr = get_mgrid((h, w))
    yf = y_arr.astype(np.float32)
    xf = x_arr.astype(np.float32)
    scale = min(h, w) / 256.0
    n_fronds = rng.randint(4, 7)
    for _ in range(n_fronds):
        cx = rng.randint(0, w)
        cy = rng.randint(0, h)
        angle = rng.uniform(0, 2 * np.pi)
        length = rng.uniform(h * 0.25, h * 0.5)
        leaf_w_base = rng.uniform(20, 40) * scale
        end_x = cx + np.cos(angle) * length
        end_y = cy + np.sin(angle) * length
        margin = leaf_w_base * 1.5
        ry0 = max(0, int(min(cy, end_y) - margin))
        ry1 = min(h, int(max(cy, end_y) + margin))
        rx0 = max(0, int(min(cx, end_x) - margin))
        rx1 = min(w, int(max(cx, end_x) + margin))
        if ry1 <= ry0 or rx1 <= rx0:
            continue
        ry = yf[ry0:ry1, rx0:rx1]
        rx = xf[ry0:ry1, rx0:rx1]
        dx, dy = rx - cx, ry - cy
        along = dx * np.cos(angle) + dy * np.sin(angle)
        across = -dx * np.sin(angle) + dy * np.cos(angle)
        t = np.clip(along / max(1, length), 0, 1)
        in_frond = (along > 0) & (along < length)
        spine_w = 3.0 * scale * (1 - t * 0.5)
        spine = np.exp(-(across ** 2) / (2 * spine_w ** 2 + 1e-6)) * in_frond * 0.7
        leaf_taper = leaf_w_base * (1 - t)
        leaflet_pattern = np.abs(np.sin(t * 12.0 * np.pi))
        leaflet = np.exp(-(across ** 2) / (2 * (leaf_taper * 0.3 + 1) ** 2)) * leaflet_pattern
        leaflet *= in_frond * (np.abs(across) < leaf_taper) * 0.5
        out[ry0:ry1, rx0:rx1] += spine + leaflet
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -40.0, "M_range": 30.0, "CC": None}

def texture_ekg_v2(shape, mask, seed, sm):
    """EKG heartbeat line — horizontal baseline with sharp QRS spikes, multiple scan lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    out = np.zeros((h, w), dtype=np.float32)
    period = max(80, min(h, w) // 6)
    n_lines = max(3, h // 120)
    for li in range(n_lines):
        center_y = h * (li + 1) / (n_lines + 1)
        phase = (xf % period).astype(np.float32) / period
        # Build EKG waveform: flat -> P wave -> flat -> QRS spike -> flat -> T wave -> flat
        ekg = np.zeros_like(phase)
        ekg = np.where((phase > 0.10) & (phase < 0.20),
                        np.sin((phase - 0.10) / 0.10 * np.pi) * 0.3, ekg)
        ekg = np.where((phase > 0.30) & (phase < 0.35), -0.2, ekg)
        ekg = np.where((phase > 0.35) & (phase < 0.40), 1.0, ekg)
        ekg = np.where((phase > 0.40) & (phase < 0.45), -0.4, ekg)
        ekg = np.where((phase > 0.55) & (phase < 0.70),
                        np.sin((phase - 0.55) / 0.15 * np.pi) * 0.4, ekg)
        trace_y = center_y + ekg * h * 0.06
        dist_from_line = np.abs(yf - trace_y)
        line_w = max(2.0, min(h, w) / 300.0)
        line = np.clip(1.0 - dist_from_line / line_w, 0, 1)
        out = np.maximum(out, line)
    pv = out.astype(np.float32)
    return {"pattern_val": pv, "R_range": -80.0, "M_range": 120.0, "CC": 0}

def texture_tire_smoke_v2(shape, mask, seed, sm):
    """Tire smoke — turbulent noise stretched horizontally, wispy smoke trails."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xf = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Layer 1: Ambient smoke haze
    haze = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 4)
    haze = (haze - haze.min()) / (haze.max() - haze.min() + 1e-8)
    rise_factor = np.clip(1.0 - yf / h, 0, 1)
    out = haze * (0.08 + rise_factor * 0.12)
    # Layer 2: Smoke plumes — wider, rising from bottom
    for _ in range(30):
        cx = rng.uniform(-w * 0.05, w * 1.05)
        base_width = w * rng.uniform(0.04, 0.12)
        drift = rng.uniform(-0.3, 0.3)
        intensity = rng.uniform(0.25, 0.65)
        phase = rng.uniform(0, 2 * np.pi)
        rise = np.clip(1.0 - yf / h, 0, 1)
        width = base_width * (1.0 + (1.0 - rise) * 2.5)
        path_x = cx + (1.0 - rise) * drift * w * 0.3
        path_x += np.sin(yf * 0.03 + phase) * w * 0.03 * (1.0 - rise)
        path_x += np.sin(yf * 0.07 + phase * 2.1) * w * 0.015 * (1.0 - rise)
        dx = np.abs(xf - path_x)
        plume = np.clip(1.0 - dx / (width + 1), 0, 1) * rise ** 0.4
        out = np.maximum(out, plume * intensity)
    # Turbulent breakup
    nh, nw = max(1, h // 12 + 1), max(1, w // 12 + 1)
    turb = rng.rand(nh, nw).astype(np.float32)
    turb_map = np.repeat(np.repeat(turb, 12, 0), 12, 1)[:h, :w]
    out = out * (0.55 + turb_map * 0.6)
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -30.0, "M_range": 20.0, "CC": None}

def texture_ember_scatter_v2(shape, mask, seed, sm):
    """Ember scatter — small bright dots with streaked trails, noise-based density."""
    h, w = shape
    rng = np.random.RandomState(seed)
    sz = min(h, w)
    out = np.zeros((h, w), dtype=np.float32)
    # Density map — embers cluster in hot zones
    density = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 100)
    density = (density - density.min()) / (density.max() - density.min() + 1e-8)
    n_embers = rng.randint(120, 250)
    for _ in range(n_embers):
        ex = rng.randint(0, w)
        ey = rng.randint(0, h)
        # Skip if density is low at this point
        if density[ey % h, ex % w] < rng.uniform(0.2, 0.6):
            continue
        size = rng.uniform(0.002, 0.008) * sz
        intensity = rng.uniform(0.5, 1.0)
        # Elongated trail (ember streak) — stretch in y direction
        trail_len = rng.uniform(1.5, 4.0)
        m = int(size * trail_len * 2) + 3
        y0, y1 = max(0, ey - m), min(h, ey + m)
        x0, x1 = max(0, ex - int(size * 2) - 2), min(w, ex + int(size * 2) + 2)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        ember = np.exp(-((lx - ex) ** 2 / (2 * size ** 2) +
                         (ly - ey) ** 2 / (2 * (size * trail_len) ** 2))) * intensity
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], ember)
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -50.0, "M_range": 100.0, "CC": None}

def texture_gothic_cross_v2(shape, mask, seed, sm):
    """Gothic cross — tiled ornate pointed cross/crucifix shapes in a grid."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(40, min(h, w) // 12)
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    cy, cx = cell / 2.0, cell / 2.0
    dy = ly - cy
    dx = lx - cx
    # Cross arms with flared (gothic pointed) ends
    arm_w = max(3.0, cell * 0.08)
    v_arm = (np.abs(dx) < arm_w + np.abs(dy) * 0.15).astype(np.float32) * \
            (np.abs(dy) < cell * 0.4).astype(np.float32)
    h_arm = (np.abs(dy) < arm_w + np.abs(dx) * 0.15).astype(np.float32) * \
            (np.abs(dx) < cell * 0.35).astype(np.float32)
    cross = np.maximum(v_arm, h_arm)
    # Pointed top
    denom = np.maximum(3.0 + (cy - ly) * 0.3, 1e-6)
    top_point = np.clip(1.0 - np.abs(dx) / denom, 0, 1) * \
                (ly < cy - cell * 0.3).astype(np.float32)
    pv = np.clip(cross + top_point * 0.5, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -60.0, "M_range": 50.0, "CC": None}

def texture_speed_lines_v2(shape, mask, seed, sm):
    """Speed lines — horizontal motion blur streaks, manga style."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    scale = min(h, w) / 256.0
    cy = h / 2.0
    for _ in range(100):
        sy = rng.randint(0, h)
        sx = rng.randint(0, w // 3)
        length = int(rng.randint(50, min(400, w)) * scale)
        thickness = max(1, int(rng.randint(1, 4) * scale))
        brightness = rng.uniform(0.3, 1.0)
        # Lines near center are longer/brighter (convergence)
        dist_from_center = abs(sy - cy) / (h / 2.0)
        brightness *= (1.0 - dist_from_center * 0.5)
        length = int(length * (1.0 - dist_from_center * 0.3))
        y0, y1 = max(0, sy), min(h, sy + thickness)
        x0, x1 = sx, min(w, sx + length)
        if y1 <= y0 or x1 <= x0:
            continue
        fade = np.linspace(1.0, 0.0, x1 - x0, dtype=np.float32).reshape(1, -1)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], brightness * fade)
    pv = out.astype(np.float32)
    return {"pattern_val": pv, "R_range": -50.0, "M_range": 40.0, "CC": None}

def texture_ocean_foam_v2(shape, mask, seed, sm):
    """Ocean foam — clusters of bubble circles with organic density variation."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    # Density field — foam clusters
    density = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 77)
    density = (density - density.min()) / (density.max() - density.min() + 1e-8)
    n_bubbles = rng.randint(300, 700)
    for _ in range(n_bubbles):
        bx = rng.randint(0, w)
        by = rng.randint(0, h)
        if density[by, bx] < 0.35:
            continue
        r = rng.uniform(2, 10) * density[by, bx]
        m = int(r + 3)
        y0, y1 = max(0, by - m), min(h, by + m)
        x0, x1 = max(0, bx - m), min(w, bx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((lx - bx) ** 2 + (ly - by) ** 2)
        # Ring shape for bubbles
        ring = np.exp(-((dist - r) ** 2) / (2 * 1.2 ** 2)) * rng.uniform(0.4, 1.0)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], ring)
    # Soft foam base layer
    foam_base = np.repeat(np.repeat(
        rng.rand(max(1, h // 4 + 1), max(1, w // 4 + 1)).astype(np.float32),
        4, 0), 4, 1)[:h, :w] * 0.15
    out += foam_base * (density > 0.3).astype(np.float32)
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -20.0, "M_range": 15.0, "CC": None}

def texture_asphalt_v2(shape, mask, seed, sm):
    """Asphalt — rough road texture with multi-scale noise and aggregate stones."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Multi-scale noise base (coarser than static noise)
    base = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed) * 0.5 + 0.5
    # Aggregate stone particles
    stones = np.zeros((h, w), dtype=np.float32)
    n_stones = int(h * w * 0.003)
    for _ in range(n_stones):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        sr = rng.randint(1, 4)
        brightness = rng.uniform(0.5, 1.0)
        y0, y1 = max(0, sy - sr), min(h, sy + sr + 1)
        x0, x1 = max(0, sx - sr), min(w, sx + sr + 1)
        if y1 > y0 and x1 > x0:
            ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
            lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
            dist = np.sqrt((ly - sy) ** 2 + (lx - sx) ** 2)
            stone = np.clip(1.0 - dist / sr, 0, 1) * brightness
            stones[y0:y1, x0:x1] = np.maximum(stones[y0:y1, x0:x1], stone)
    pv = np.clip(base * 0.6 + stones * 0.5, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": 60.0, "M_range": -40.0, "CC": None}

def texture_dna_helix_v2(shape, mask, seed, sm):
    """DNA double helix — two intertwined sine waves with connecting rungs, tiled vertically."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Tile horizontally in columns
    col_w = max(60, min(h, w) // 6)
    lx = (xf % col_w).astype(np.float32)
    cx = col_w / 2.0
    period = max(40, min(h, w) // 10)
    amplitude = col_w * 0.3
    strand1_x = cx + np.sin(yf * np.pi * 2 / period) * amplitude
    strand2_x = cx - np.sin(yf * np.pi * 2 / period) * amplitude
    line_w = max(2.0, col_w / 25.0)
    s1 = np.clip(1.0 - np.abs(lx - strand1_x) / line_w, 0, 1)
    s2 = np.clip(1.0 - np.abs(lx - strand2_x) / line_w, 0, 1)
    # Connecting rungs at regular intervals
    rung_spacing = max(8, period // 5)
    rung_mask = (yf % rung_spacing < max(2, rung_spacing // 5)).astype(np.float32)
    rung_x_min = np.minimum(strand1_x, strand2_x)
    rung_x_max = np.maximum(strand1_x, strand2_x)
    rung = ((lx > rung_x_min) & (lx < rung_x_max)).astype(np.float32) * rung_mask * 0.5
    pv = np.clip(s1 + s2 + rung, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -70.0, "M_range": 90.0, "CC": None}

def texture_neuron_network_v2(shape, mask, seed, sm):
    """Neuron network — cell bodies (circles) with branching dendrite connections."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    n_neurons = max(20, int(35 * min(h, w) / 512))
    neurons_y = rng.randint(0, h, n_neurons)
    neurons_x = rng.randint(0, w, n_neurons)
    # Draw dendrite connections between nearby neurons
    for i in range(n_neurons):
        ay, ax = int(neurons_y[i]), int(neurons_x[i])
        dists = np.sqrt((neurons_y.astype(np.float64) - ay) ** 2 +
                        (neurons_x.astype(np.float64) - ax) ** 2)
        dists[i] = 1e9
        neighbors = np.argsort(dists)[:rng.randint(2, 4)]
        for ni in neighbors:
            by, bx = int(neurons_y[ni]), int(neurons_x[ni])
            n_pts = int(np.sqrt((ay - by) ** 2 + (ax - bx) ** 2)) + 1
            if n_pts < 2:
                continue
            for ti in range(n_pts):
                t = ti / max(1, n_pts - 1)
                py = int(ay + (by - ay) * t + np.sin(t * 6 + i) * 4)
                px = int(ax + (bx - ax) * t + np.cos(t * 6 + i) * 4)
                if 0 <= py < h and 0 <= px < w:
                    r = 1
                    y0, y1 = max(0, py - r), min(h, py + r + 1)
                    x0, x1 = max(0, px - r), min(w, px + r + 1)
                    out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], 0.4)
    # Draw cell bodies (soma) on top
    for i in range(n_neurons):
        cy_n, cx_n = int(neurons_y[i]), int(neurons_x[i])
        r = rng.uniform(4, 8) * min(h, w) / 512.0
        m = int(r) + 2
        y0, y1 = max(0, cy_n - m), min(h, cy_n + m)
        x0, x1 = max(0, cx_n - m), min(w, cx_n + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - cy_n) ** 2 + (lx - cx_n) ** 2)
        soma = np.clip(1.0 - dist / max(1, r), 0, 1) ** 0.5
        np.maximum(out[y0:y1, x0:x1], soma * 0.8, out=out[y0:y1, x0:x1])
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -80.0, "M_range": 110.0, "CC": 0}

def texture_molecular_v2(shape, mask, seed, sm):
    """Molecular — ball-and-stick model with atom circles and bond lines."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    spacing = max(20, min(h, w) // 18)
    atoms = []
    for gy in range(0, h + spacing, spacing):
        for gx in range(0, w + spacing, spacing):
            ay = gy + rng.randint(-5, 6)
            ax = gx + rng.randint(-5, 6)
            ar = rng.uniform(3, 6) * min(h, w) / 512.0
            atoms.append((ay, ax, ar))
    # Draw bonds between nearby atoms
    for i, (ay1, ax1, _) in enumerate(atoms):
        for j in range(i + 1, min(i + 8, len(atoms))):
            ay2, ax2, _ = atoms[j]
            d = np.sqrt((ay1 - ay2) ** 2 + (ax1 - ax2) ** 2)
            if d > spacing * 1.6 or d < 5:
                continue
            bond_len = int(d) + 1
            for t_idx in range(bond_len):
                t = t_idx / max(1, bond_len - 1)
                by = int(ay1 + (ay2 - ay1) * t)
                bx = int(ax1 + (ax2 - ax1) * t)
                bw = 1
                y0, y1 = max(0, by - bw), min(h, by + bw + 1)
                x0, x1 = max(0, bx - bw), min(w, bx + bw + 1)
                if y1 > y0 and x1 > x0:
                    out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], 0.45)
    # Draw atoms on top
    for ay, ax, ar in atoms:
        m = int(ar) + 2
        y0, y1 = max(0, ay - m), min(h, ay + m)
        x0, x1 = max(0, ax - m), min(w, ax + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - ay) ** 2 + (lx - ax) ** 2)
        sphere = np.clip(1.0 - dist / max(1, ar), 0, 1) ** 0.6
        np.maximum(out[y0:y1, x0:x1], sphere, out=out[y0:y1, x0:x1])
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -60.0, "M_range": 80.0, "CC": None}


# ---------------------------------------------------------------------------
# V5.3 DEDICATED TEXTURE FUNCTIONS (15 rewritten patterns)
# Each replaces a generic/shared texture_fn with a visually accurate version.
# ---------------------------------------------------------------------------

def texture_aero_flow_v2(shape, mask, seed, sm):
    """Aerodynamic flow lines with curl-noise distortion."""
    h, w = shape
    rng = np.random.default_rng(seed + 7000)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)
    # Base horizontal flow lines
    freq_y = 30.0
    flow = np.sin(yf * freq_y * np.pi) * 0.5 + 0.5
    # Curl-noise distortion: use multi-scale noise to displace y coordinate
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7001)
    n2 = multi_scale_noise(shape, [4, 8, 16], [0.25, 0.45, 0.3], seed + 7002)
    # Vertical wobble displacement
    displacement = n1 * 0.15 + n2 * 0.08
    yf_warped = yf + displacement
    flow_warped = np.sin(yf_warped * freq_y * np.pi) * 0.5 + 0.5
    # Add horizontal streaking via x-frequency modulation
    streak = np.sin(xf * 6.0 * np.pi + n1 * 4.0) * 0.3 + 0.7
    pattern = np.clip(flow_warped * streak, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -85.0, "M_range": 75.0, "CC": 0}


def texture_aztec_steps_v2(shape, mask, seed, sm):
    """Nested concentric rectangles creating stepped pyramid motif, tiled."""
    h, w = shape
    rng = np.random.default_rng(seed + 7010)
    y, x = get_mgrid((h, w))
    cell_size = max(40, min(h, w) // 10)
    # Local coordinates within each tile cell [0..1]
    lx = (x.astype(np.float32) % cell_size) / cell_size
    ly = (y.astype(np.float32) % cell_size) / cell_size
    # Concentric rectangular distance (Chebyshev from center)
    rect_dist = np.maximum(np.abs(lx - 0.5), np.abs(ly - 0.5))
    # Quantize into stepped bands
    n_steps = 6
    stepped = np.floor(rect_dist * n_steps * 2.0).astype(np.int32)
    pattern = (stepped % 2).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 68.0, "M_range": -38.0, "CC": None}


def texture_bamboo_stalk_v2(shape, mask, seed, sm):
    """Wide vertical bamboo stalks with horizontal node joints and grain noise."""
    h, w = shape
    rng = np.random.default_rng(seed + 7020)
    y, x = get_mgrid((h, w))
    xf = x.astype(np.float32)
    yf = y.astype(np.float32)
    # Wide vertical stalks (~20px)
    stalk_period = max(30, w // 16)
    stalk_width = stalk_period * 0.6
    x_in_cell = xf % stalk_period
    stalk_mask = np.clip(1.0 - np.abs(x_in_cell - stalk_period * 0.5) / (stalk_width * 0.5), 0, 1)
    stalk_mask = np.where(stalk_mask > 0, 1.0, 0.0).astype(np.float32)
    # Horizontal node joints every ~60px
    node_period = max(50, h // 8)
    node_band = np.abs(yf % node_period - node_period * 0.5)
    node_line = np.where(node_band < 2.5, 1.0, 0.0).astype(np.float32)
    # Subtle grain noise on stalk surface
    grain = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 7021)
    grain = grain * 0.15 + 0.85  # subtle variation 0.7-1.0
    # Combine: stalk body with grain, plus joint lines
    pattern = stalk_mask * grain
    pattern = np.clip(pattern + node_line * stalk_mask * 0.4, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 55.0, "CC": 0}


def texture_hibiscus_v2(shape, mask, seed, sm):
    """5-petal hibiscus flower using rose curve r=cos(5*theta), tiled."""
    h, w = shape
    rng = np.random.default_rng(seed + 7030)
    y, x = get_mgrid((h, w))
    cell_size = max(60, min(h, w) // 6)
    # Local coordinates centered in each tile cell
    lx = (x.astype(np.float32) % cell_size) - cell_size * 0.5
    ly = (y.astype(np.float32) % cell_size) - cell_size * 0.5
    # Polar coordinates
    r = np.sqrt(lx ** 2 + ly ** 2) / (cell_size * 0.45)
    theta = np.arctan2(ly, lx)
    # Rose curve: r_rose = cos(5 * theta) → 5 petals
    r_rose = np.abs(np.cos(2.5 * theta))  # 5-petal rose
    # Petal mask: bright where r < r_rose
    petal = np.clip(1.0 - (r / (r_rose + 0.05)) * 1.2, 0, 1)
    # Add center dot
    center = np.clip(1.0 - r * 5.0, 0, 1)
    pattern = np.clip(petal + center * 0.5, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 50.0, "M_range": -30.0, "CC": None}


def texture_iron_cross_v2(shape, mask, seed, sm):
    """Flared 4-arm Iron Cross with arms narrowing toward tips, tiled in cells."""
    h, w = shape
    rng = np.random.default_rng(seed + 7040)
    y, x = get_mgrid((h, w))
    cell_size = max(50, min(h, w) // 8)
    # Local coordinates centered [-0.5, 0.5]
    lx = (x.astype(np.float32) % cell_size) / cell_size - 0.5
    ly = (y.astype(np.float32) % cell_size) / cell_size - 0.5
    ax, ay = np.abs(lx), np.abs(ly)
    # Central diamond: abs(x)+abs(y) < radius
    diamond = (ax + ay < 0.22).astype(np.float32)
    # Four rectangular arms that narrow: arm width tapers with distance
    arm_len = 0.45
    arm_base_w = 0.14
    arm_tip_w = 0.04
    # Horizontal arms
    h_arm_dist = ax
    h_arm_width = arm_base_w + (arm_tip_w - arm_base_w) * (h_arm_dist / arm_len)
    h_arm = ((ax < arm_len) & (ay < h_arm_width)).astype(np.float32)
    # Vertical arms
    v_arm_dist = ay
    v_arm_width = arm_base_w + (arm_tip_w - arm_base_w) * (v_arm_dist / arm_len)
    v_arm = ((ay < arm_len) & (ax < v_arm_width)).astype(np.float32)
    pattern = np.clip(diamond + h_arm + v_arm, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 72.0, "M_range": -50.0, "CC": None}


def texture_gothic_scroll_v2(shape, mask, seed, sm):
    """Curling spiral scrollwork using parametric spirals arranged symmetrically."""
    h, w = shape
    rng = np.random.default_rng(seed + 7050)
    y, x = get_mgrid((h, w))
    cell_size = max(80, min(h, w) // 5)
    lx = (x.astype(np.float32) % cell_size) - cell_size * 0.5
    ly = (y.astype(np.float32) % cell_size) - cell_size * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) / (cell_size * 0.5) + 1e-8
    theta = np.arctan2(ly, lx)
    # Archimedean spiral: r = a + b*theta
    # Distance from spiral arm: measure sin(theta - r * k)
    k_spiral = 6.0
    scroll1 = np.sin(theta - r * k_spiral * np.pi) * 0.5 + 0.5
    scroll2 = np.sin(-theta - r * k_spiral * np.pi + np.pi * 0.5) * 0.5 + 0.5
    # Combine symmetric pair
    combined = np.minimum(scroll1, scroll2)
    # Sharpen scrollwork lines
    line = np.where(combined < 0.35, 1.0, 0.0).astype(np.float32)
    # Fade edges for filigree softness
    edge_fade = np.clip(1.0 - r * 0.3, 0.3, 1.0)
    pattern = (line * edge_fade).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -45.0, "CC": None}


def texture_drift_marks_v2(shape, mask, seed, sm):
    """Wide diagonal rubber drift streaks with soft edges, irregular spacing."""
    h, w = shape
    rng = np.random.default_rng(seed + 7060)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Diagonal projection at ~30 degrees
    diag = xf * 0.87 + yf * 0.5
    # Generate multiple wide streaks at irregular intervals
    n_streaks = rng.integers(6, 12)
    total_span = np.sqrt(float(h ** 2 + w ** 2))
    positions = np.sort(rng.uniform(0, total_span, n_streaks))
    widths = rng.uniform(25, 50, n_streaks)
    pattern = np.zeros((h, w), dtype=np.float32)
    for i in range(n_streaks):
        dist_from_center = np.abs(diag - positions[i])
        half_w = widths[i] * 0.5
        # Soft-edged streak using smoothstep
        t = np.clip(dist_from_center / half_w, 0, 1)
        streak = 1.0 - t * t * (3.0 - 2.0 * t)  # smoothstep falloff
        pattern = np.maximum(pattern, streak)
    # Add slight noise for rubber texture
    grain = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 7061)
    pattern = np.clip(pattern * (0.85 + grain * 0.15), 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -90.0, "M_range": 70.0, "CC": 0}


def texture_caustic_v2(shape, mask, seed, sm):
    """Multi-source interference pattern with 8-12 random point sources, bright peaks."""
    h, w = shape
    rng = np.random.default_rng(seed + 7070)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    n_sources = rng.integers(8, 13)
    src_y = rng.uniform(0, h, n_sources).astype(np.float32)
    src_x = rng.uniform(0, w, n_sources).astype(np.float32)
    freq = rng.uniform(0.08, 0.15, n_sources).astype(np.float32)
    # Sum of sine waves from each point source
    wave_sum = np.zeros((h, w), dtype=np.float32)
    for i in range(n_sources):
        dist = np.sqrt((yf - src_y[i]) ** 2 + (xf - src_x[i]) ** 2)
        wave_sum += np.sin(dist * freq[i] * 2.0 * np.pi) * 0.5 + 0.5
    # Normalize and enhance bright intersection peaks
    wave_sum = wave_sum / n_sources
    # Square to emphasize constructive interference peaks
    pattern = np.clip(wave_sum ** 2 * 2.5, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 55.0, "CC": 0}


def texture_frost_crystal_v2(shape, mask, seed, sm):
    """Hexagonal grid with dendritic branches growing from vertices at 60-deg angles."""
    h, w = shape
    rng = np.random.default_rng(seed + 7080)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Hexagonal grid parameters
    hex_size = max(40, min(h, w) // 8)
    # Hex grid: offset every other row
    row = np.floor(yf / (hex_size * 0.866)).astype(np.int32)
    x_offset = np.where(row % 2 == 0, 0.0, hex_size * 0.5)
    # Distance to nearest hex center
    hx = ((xf + x_offset) % hex_size) - hex_size * 0.5
    hy = (yf % (hex_size * 0.866)) - hex_size * 0.433
    dist_center = np.sqrt(hx ** 2 + hy ** 2)
    # Angle from hex center
    angle = np.arctan2(hy, hx)
    # Dendritic branches at 60-degree intervals (6-fold symmetry)
    branch_angle = np.abs(np.sin(angle * 3.0))  # peaks at 0, 60, 120, ... deg
    # Branch mask: thin lines radiating from center
    branch_width = hex_size * 0.04
    branch_mask = np.where(branch_angle < 0.15, 1.0, 0.0).astype(np.float32)
    # Sub-branches: secondary branching at smaller scale
    sub_branch = np.abs(np.sin(angle * 6.0 + dist_center * 0.3))
    sub_mask = np.where((sub_branch < 0.12) & (dist_center > hex_size * 0.15), 0.7, 0.0)
    # Combine: hex edge + branches + sub-branches
    hex_edge = np.clip(1.0 - np.abs(dist_center - hex_size * 0.4) / (hex_size * 0.05), 0, 1)
    crystal = np.clip(branch_mask + sub_mask.astype(np.float32) + hex_edge * 0.6, 0, 1)
    # Fade with distance from center for crystal look
    fade = np.clip(1.0 - dist_center / (hex_size * 0.5), 0.1, 1.0)
    pattern = np.clip(crystal * fade, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -80.0, "M_range": 60.0, "CC": None}


def texture_glitch_scan_v2(shape, mask, seed, sm):
    """Horizontal bands with random x-offset displacement, scanline flicker, binary noise."""
    h, w = shape
    rng = np.random.default_rng(seed + 7090)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Divide into horizontal bands of varying height
    band_height = max(4, h // 60)
    band_idx = (yf / band_height).astype(np.int32)
    n_bands = int(np.ceil(h / band_height)) + 1
    # Random x-displacement per band
    offsets = rng.integers(-w // 6, w // 6, n_bands)
    # Build offset map
    offset_map = np.zeros((h, w), dtype=np.float32)
    for i in range(n_bands):
        band_mask = (band_idx == i)
        offset_map = np.where(band_mask, float(offsets[i % n_bands]), offset_map)
    # Displaced x coordinate
    x_displaced = (xf + offset_map) % w
    # Scanline flicker: thin horizontal lines
    scanline = ((yf.astype(np.int32) % 3) == 0).astype(np.float32) * 0.3
    # Binary threshold noise from displaced coordinates
    noise_seed = seed + 7091
    # Create block noise using displaced coordinates
    block_w = max(6, w // 80)
    block_h = band_height
    bx = (x_displaced / block_w).astype(np.int32)
    by = (yf / block_h).astype(np.int32)
    # Hash-based pseudo-random binary values
    hash_val = ((bx * 73856093) ^ (by * 19349663) ^ noise_seed) % 1000
    binary = (hash_val > 500).astype(np.float32)
    # Combine: binary blocks + scanline flicker
    pattern = np.clip(binary * 0.8 + scanline, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -75.0, "M_range": 65.0, "CC": 0}


def texture_corrugated_v2(shape, mask, seed, sm):
    """Smooth sine-wave corrugation cross-section with smoothstep transitions."""
    h, w = shape
    rng = np.random.default_rng(seed + 7100)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    # Corrugation frequency
    freq = max(15, h // 20)
    phase = yf / freq * np.pi * 2.0
    # Raw sine wave
    raw = np.sin(phase) * 0.5 + 0.5
    # Smoothstep for rounded ridges: 3t^2 - 2t^3
    t = raw
    smooth = t * t * (3.0 - 2.0 * t)
    pattern = smooth.astype(np.float32)
    return {"pattern_val": pattern, "R_range": -100.0, "M_range": 90.0, "CC": 0}


def texture_herringbone_v2(shape, mask, seed, sm):
    """Proper V-stitch herringbone with short diagonal segments alternating in 2x2 cells."""
    h, w = shape
    rng = np.random.default_rng(seed + 7110)
    y, x = get_mgrid((h, w))
    # Cell dimensions: each cell contains one diagonal segment
    cell_w = max(12, w // 40)
    cell_h = max(20, h // 25)
    # Which cell
    cx = (x.astype(np.float32) / cell_w).astype(np.int32)
    cy = (y.astype(np.float32) / cell_h).astype(np.int32)
    # Local coordinates within cell [0, 1]
    lx = (x.astype(np.float32) % cell_w) / cell_w
    ly = (y.astype(np.float32) % cell_h) / cell_h
    # Alternating diagonal direction in checkerboard pattern
    direction = ((cx + cy) % 2).astype(np.float32)  # 0 or 1
    # Diagonal line: for direction 0: y = x, for direction 1: y = 1-x
    diag_0 = np.abs(ly - lx)
    diag_1 = np.abs(ly - (1.0 - lx))
    diag = np.where(direction < 0.5, diag_0, diag_1)
    # Line thickness
    thickness = 0.2
    line = np.clip(1.0 - diag / thickness, 0, 1).astype(np.float32)
    return {"pattern_val": line, "R_range": 72.0, "M_range": -42.0, "CC": None}


def texture_dazzle_v2(shape, mask, seed, sm):
    """Sharp geometric Voronoi patches with binary coloring overlaid with angled stripes."""
    h, w = shape
    rng = np.random.default_rng(seed + 7120)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Voronoi cells
    n_pts = max(25, int(h * w / 3000))
    n_pts = min(n_pts, 150)
    cell_id = _voronoi_cells_fast(shape, n_pts, 7120, seed)
    # Binary coloring per cell
    cell_color = (cell_id * 73856093 + seed) % 2
    voronoi_binary = cell_color.astype(np.float32)
    # Angled stripe field overlay
    angle1 = rng.uniform(0.3, 1.2)
    stripe1 = np.sin((xf * np.cos(angle1) + yf * np.sin(angle1)) * 0.08 * np.pi) > 0
    angle2 = rng.uniform(-1.2, -0.3)
    stripe2 = np.sin((xf * np.cos(angle2) + yf * np.sin(angle2)) * 0.12 * np.pi) > 0
    stripe_xor = (stripe1.astype(np.int32) ^ stripe2.astype(np.int32)).astype(np.float32)
    # Combine: XOR voronoi with stripe field for dazzle camo
    pattern = ((voronoi_binary.astype(np.int32) ^ stripe_xor.astype(np.int32)) % 2).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -80.0, "CC": 0}


def texture_leopard_rosette_v2(shape, mask, seed, sm):
    """Leopard rosette open rings using abs(dist - ring_radius) < thickness."""
    h, w = shape
    rng = np.random.default_rng(seed + 7130)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Work at 1/4 resolution for speed, then upscale
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    ys = np.arange(sh, dtype=np.float32) * ds
    xs = np.arange(sw, dtype=np.float32) * ds
    yg, xg = np.meshgrid(ys, xs, indexing='ij')
    # Scatter rosette centers in jittered grid
    cell_size = max(35, min(h, w) // 10)
    n_y = int(np.ceil(h / cell_size)) + 2
    n_x = int(np.ceil(w / cell_size)) + 2
    pat_small = np.zeros((sh, sw), dtype=np.float32)
    for iy in range(n_y):
        for ix in range(n_x):
            cy = iy * cell_size + rng.uniform(-cell_size * 0.25, cell_size * 0.25)
            cx_v = ix * cell_size + rng.uniform(-cell_size * 0.25, cell_size * 0.25)
            ring_r = rng.uniform(cell_size * 0.25, cell_size * 0.4)
            thickness = rng.uniform(2.5, 4.5)
            # Quick bounding-box skip
            margin = ring_r + thickness + 2
            if cy + margin < 0 or cy - margin > h or cx_v + margin < 0 or cx_v - margin > w:
                continue
            dist = np.sqrt((yg - cy) ** 2 + (xg - cx_v) ** 2)
            ring = np.clip(1.0 - np.abs(dist - ring_r) / thickness, 0, 1)
            center_dot = np.clip(1.0 - dist / (ring_r * 0.25 + 1e-6), 0, 1) * 0.6
            pat_small = np.maximum(pat_small, np.maximum(ring, center_dot))
    # Upscale to full resolution
    if ds > 1:
        from PIL import Image as _PILImg
        pat_img = _PILImg.fromarray((np.clip(pat_small, 0, 1) * 255).astype(np.uint8))
        pattern = np.array(pat_img.resize((w, h), _PILImg.BILINEAR), dtype=np.float32) / 255.0
    else:
        pattern = np.clip(pat_small, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 40.0, "M_range": -25.0, "CC": None}


def texture_aurora_bands_v2(shape, mask, seed, sm):
    """Multi-frequency flowing curtain bands with vertical fade and horizontal shimmer."""
    h, w = shape
    rng = np.random.default_rng(seed + 7140)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)
    # Vertical fade: bright at top, fading to dark at bottom
    v_fade = np.clip(1.0 - yf * 1.3, 0, 1) ** 0.7
    # Multi-frequency horizontal curtain waves
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7141)
    curtain = np.zeros((h, w), dtype=np.float32)
    freqs = [3.0, 5.0, 8.0, 13.0]
    amps = [0.35, 0.3, 0.2, 0.15]
    for freq, amp in zip(freqs, amps):
        phase = rng.uniform(0, 2 * np.pi)
        # Horizontally stretched noise displacement
        displacement = n1 * 0.3
        wave = np.sin((xf + displacement) * freq * np.pi * 2.0 + phase)
        curtain += wave * amp
    curtain = curtain * 0.5 + 0.5  # normalize to [0,1]
    # Horizontal shimmer via stretched noise
    shimmer = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 7142)
    shimmer = shimmer * 0.15 + 0.85
    pattern = np.clip(curtain * v_fade * shimmer, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -60.0, "M_range": 50.0, "CC": None}


# --- PATTERN TEXTURE REGISTRY ---
# !! ARCHITECTURE GUARD - READ BEFORE MODIFYING !!
# See ARCHITECTURE.md for full documentation.
# - Each entry maps a pattern ID to {texture_fn, paint_fn, variable_cc, desc}
# - texture_fn generates the spatial pattern array (0-1)
# - paint_fn modifies the RGB paint layer in pattern grooves
# - Adding entries is SAFE. Removing or renaming entries WILL break the UI.
# - If a UI pattern ID is missing here, it silently renders as "none" (invisible).
# - The v7.0 alias block (~line 5170+) maps 162 UI patterns to closest texture_fn.
#   If you need different visuals for an alias, create a NEW texture_fn and re-point it.
#   DO NOT modify the shared texture_fn - it breaks every other pattern using it.
PATTERN_REGISTRY = {
    "acid_wash":         {"texture_fn": texture_acid_wash,        "paint_fn": paint_acid_etch,        "variable_cc": True,  "desc": "Corroded acid-etched surface"},
    "aero_flow": {"texture_fn": texture_aero_flow_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Aerodynamic flow visualization streaks"},
    "argyle": {"texture_fn": texture_plaid, "paint_fn": paint_plaid_tint, "variable_cc": False, "desc": "Diamond/rhombus overlapping argyle"},
    "art_deco": {"texture_fn": texture_art_deco_fan, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "1920s geometric fan/sunburst motif"},
    "asphalt_texture": {"texture_fn": texture_asphalt_v2, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Road surface aggregate texture"},
    "atomic_orbital": {"texture_fn": texture_ripple_dense, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Electron cloud probability orbital rings"},
    "aurora_bands": {"texture_fn": texture_aurora_bands_v2, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Northern lights wavy curtain bands"},
    "aztec": {"texture_fn": texture_aztec_steps_v2, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Angular stepped Aztec geometric blocks"},
    "bamboo_stalk": {"texture_fn": texture_bamboo_stalk_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Vertical bamboo stalks with joints"},
    "barbed_wire":       {"texture_fn": texture_barbed_wire,     "paint_fn": paint_barbed_scratch,   "variable_cc": False, "desc": "Twisted wire with barb spikes"},
    "basket_weave": {"texture_fn": texture_basket_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Over-under basket weave pattern"},
    "battle_worn":       {"texture_fn": texture_battle_worn,      "paint_fn": paint_scratch_marks,    "variable_cc": True,  "desc": "Scratched weathered damage"},
    "binary_code": {"texture_fn": texture_binary_code_v2, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Streaming 0s and 1s binary data"},
    "biohazard": {"texture_fn": texture_biohazard_symbol, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Repeating biohazard trefoil symbol"},
    # "biomechanical" LIVES IN engine/registry.py
    "biomechanical_2": {"texture_fn": texture_biomechanical_2, "paint_fn": paint_damascus_layer, "variable_cc": False, "desc": "Procedural Giger-style organic mechanical"},
    "blue_flame": {"texture_fn": texture_flame_aggressive, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Blue flame - superseded by flame_blue_propane"},
    "board_wax": {"texture_fn": texture_ripple_soft, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Circular surfboard wax rub pattern"},
    "brake_dust": {"texture_fn": texture_metal_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Hot brake dust particle scatter"},
    # "brick" REMOVED - Artistic & Cultural category replaced by image-based patterns (see engine/registry.py)
    "bullet_holes": {"texture_fn": texture_fracture, "paint_fn": paint_fracture_damage, "variable_cc": True, "desc": "Scattered impact penetration holes"},
    "camo":              {"texture_fn": texture_camo,            "paint_fn": paint_camo_pattern,     "variable_cc": False, "desc": "Digital splinter camouflage blocks"},
    "carbon_fiber":      {"texture_fn": texture_carbon_fiber,     "paint_fn": paint_carbon_darken,    "variable_cc": False, "desc": "Woven 2x2 twill weave"},
    "caustic": {"texture_fn": texture_caustic_v2, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Underwater dancing light caustic pools"},
    "celtic_knot":       {"texture_fn": texture_celtic_knot,    "paint_fn": paint_celtic_emboss,    "variable_cc": False, "desc": "Interwoven flowing band knot pattern"},
    "chainlink": {"texture_fn": texture_chainlink, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Chain-link fence diagonal wire grid"},
    "chainmail":         {"texture_fn": texture_chainmail,       "paint_fn": paint_chainmail_emboss, "variable_cc": False, "desc": "Interlocking metal ring mesh"},
    "checkered_flag": {"texture_fn": texture_checkered_flag, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Classic racing checkered flag grid"},
    "chevron":           {"texture_fn": texture_chevron,        "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Repeating V/arrow stripe pattern"},
    "circuit_board":     {"texture_fn": texture_circuit_board,   "paint_fn": paint_circuit_glow,     "variable_cc": False, "desc": "PCB trace lines with pads and vias"},
    "circuitboard": {"texture_fn": texture_circuit_board, "paint_fn": paint_circuit_glow, "variable_cc": False, "desc": "PCB trace pattern metallic traces"},
    "classic_hotrod": {"texture_fn": texture_flame_sweep, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Classic hot rod - superseded by flame_hotrod_classic"},
    "corrugated": {"texture_fn": texture_corrugated_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Corrugated sheet metal parallel ridges"},
    "cracked_ice":       {"texture_fn": texture_cracked_ice,      "paint_fn": paint_ice_cracks,       "variable_cc": False, "desc": "Frozen crack network"},
    "crocodile": {"texture_fn": texture_dragon_scale, "paint_fn": paint_scale_pattern, "variable_cc": False, "desc": "Deep embossed crocodile hide scales"},
    "crosshatch":        {"texture_fn": texture_crosshatch_fine, "paint_fn": paint_crosshatch_ink,   "variable_cc": False, "desc": "Overlapping diagonal pen stroke lines"},
    # "damascus" REMOVED - Artistic & Cultural replaced by image-based (engine/registry.py)
    "data_stream": {"texture_fn": texture_data_stream, "paint_fn": paint_hologram_lines, "variable_cc": False, "desc": "Flowing horizontal data packet streams"},
    "dazzle":            {"texture_fn": texture_dazzle_v2,          "paint_fn": paint_dazzle_contrast,  "variable_cc": False, "desc": "Bold Voronoi B/W dazzle camo patches"},
    # "denim" REMOVED - Artistic & Cultural replaced by image-based (engine/registry.py)
    "diamond_plate":     {"texture_fn": texture_diamond_plate,    "paint_fn": paint_diamond_emboss,   "variable_cc": False, "desc": "Industrial raised diamond tread"},
    "dimensional": {"texture_fn": texture_interference, "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Newtons rings thin-film interference"},
    "dna_helix": {"texture_fn": texture_dna_helix_v2, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Double-helix DNA strand spiral"},
    # "dragon_scale" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "drift_marks": {"texture_fn": texture_drift_marks_v2, "paint_fn": paint_tread_darken, "variable_cc": False, "desc": "Sideways drift tire trail marks"},
    "ekg": {"texture_fn": texture_ekg_v2, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Heartbeat EKG monitor line pulse"},
    "ember_mesh":        {"texture_fn": texture_ember_mesh,    "paint_fn": paint_ember_mesh_glow,  "variable_cc": False, "desc": "Glowing hot wire grid with ember nodes"},
    "ember_scatter": {"texture_fn": texture_ember_scatter_v2, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Floating glowing embers scattered"},
    "expanded_metal": {"texture_fn": texture_grating_heavy, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Stretched diamond expanded mesh"},
    "feather": {"texture_fn": texture_feather_barb, "paint_fn": paint_snake_emboss, "variable_cc": False, "desc": "Layered overlapping bird feather barbs"},
    "fingerprint": {"texture_fn": texture_fingerprint, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Swirling concentric fingerprint ridges"},
    "finish_line": {"texture_fn": texture_houndstooth_bold, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Bold start/finish line checkered band"},
    "fire_lick": {"texture_fn": texture_flame_tongues, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Flickering flame tongues licking upward"},
    "fireball": {"texture_fn": texture_flame_ball, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Explosive spherical fireball burst"},
    "flame_fade": {"texture_fn": texture_flame_smoke_fade, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Flames gradually fading into smoke"},
    # "fleur_de_lis" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "fractal": {"texture_fn": texture_plasma_fractal, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Self-similar Mandelbrot fractal branching"},
    "fractal_2": {"texture_fn": texture_fractal_2, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "High-frequency geometric fracturing"},
    "fractal_3": {"texture_fn": texture_fractal_3, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Dense interwoven fractal network"},
    "fracture":          {"texture_fn": texture_fracture,      "paint_fn": paint_fracture_damage,  "variable_cc": True,  "desc": "Shattered impact glass with radial crack network"},
    "fresnel_ghost": {"texture_fn": texture_hex_honeycomb, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Hidden hex pattern Fresnel amplification"},
    "frost_crystal":     {"texture_fn": texture_frost_crystal_v2,  "paint_fn": paint_frost_crystal,    "variable_cc": False, "desc": "Ice crystal branching fractals"},
    "g_force": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Acceleration force vector compression"},
    "ghost_flames": {"texture_fn": texture_plasma_soft, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "[Legacy] Ghost flames - superseded by flame_ghost"},
    "giraffe": {"texture_fn": texture_giraffe, "paint_fn": paint_leopard_spots, "variable_cc": False, "desc": "Irregular polygon giraffe spot patches"},
    "glacier_crack": {"texture_fn": texture_cracked_ice, "paint_fn": paint_ice_cracks, "variable_cc": False, "desc": "Deep blue-white glacial ice fissures"},
    "glitch_scan": {"texture_fn": texture_glitch_scan_v2, "paint_fn": paint_hologram_lines, "variable_cc": False, "desc": "Horizontal glitch scanline displacement"},
    "gothic_cross": {"texture_fn": texture_gothic_cross_v2, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Ornate gothic cathedral cross grid"},
    "gothic_scroll": {"texture_fn": texture_gothic_scroll_v2, "paint_fn": paint_damascus_layer, "variable_cc": False, "desc": "Flowing dark ornamental scroll filigree"},
    "grating": {"texture_fn": texture_grating_heavy, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Industrial floor grating parallel bars"},
    "greek_key": {"texture_fn": texture_tribal_meander, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Continuous right-angle meander border"},
    "grip_tape": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Coarse skateboard grip tape texture"},
    "hailstorm": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "Dense scattered impact crater dimples"},
    "halfpipe": {"texture_fn": texture_wave_gentle, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Curved halfpipe ramp cross-section"},
    "hammered":          {"texture_fn": texture_hammered,         "paint_fn": paint_hammered_dimples, "variable_cc": False, "desc": "Hand-hammered dimple pattern"},
    "hellfire": {"texture_fn": texture_flame_aggressive, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Hellfire - superseded by flame_hellfire_column"},
    "herringbone": {"texture_fn": texture_herringbone_v2, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "V-shaped zigzag brick/tile pattern"},
    "hex_mesh":          {"texture_fn": texture_hex_mesh,         "paint_fn": paint_hex_emboss,       "variable_cc": False, "desc": "Honeycomb wire grid"},
    "hibiscus": {"texture_fn": texture_hibiscus_v2, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Hawaiian hibiscus flower pattern"},
    "hologram":          {"texture_fn": texture_hologram,         "paint_fn": paint_hologram_lines,   "variable_cc": False, "desc": "Horizontal scanline projection"},
    "holographic": {"texture_fn": texture_holographic_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Hologram diffraction grating rainbow"},
    "holographic_flake": {"texture_fn": texture_holographic_flake,"paint_fn": paint_coarse_flake,     "variable_cc": False, "desc": "Rainbow prismatic micro-grid flake"},
    "houndstooth":       {"texture_fn": texture_houndstooth,    "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Classic houndstooth check textile"},
    "inferno": {"texture_fn": texture_flame_wild, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Inferno - superseded by flame_inferno_wall"},
    "interference":      {"texture_fn": texture_interference,     "paint_fn": paint_interference_shift,"variable_cc": False, "desc": "Flowing rainbow wave bands"},
    "iron_cross": {"texture_fn": texture_iron_cross_v2, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Bold Iron Cross motif array"},
    # "japanese_wave" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "kevlar_weave": {"texture_fn": texture_kevlar_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Tight aramid fiber golden weave"},
    "knurled": {"texture_fn": texture_crosshatch, "paint_fn": paint_crosshatch_ink, "variable_cc": False, "desc": "Machine knurling diagonal cross-hatch"},
    "lap_counter": {"texture_fn": texture_pinstripe_fine, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Repeating tally mark lap counter"},
    "lava_flow":         {"texture_fn": texture_lava_flow,       "paint_fn": paint_lava_glow,        "variable_cc": True,  "desc": "Flowing molten rock with hot cracks"},
    "leather_grain": {"texture_fn": texture_hammered, "paint_fn": paint_hammered_dimples, "variable_cc": False, "desc": "Natural grain leather pebble texture"},
    "leopard":           {"texture_fn": texture_leopard_rosette_v2,  "paint_fn": paint_leopard_spots,    "variable_cc": False, "desc": "Organic leopard rosette spots"},
    "lightning":         {"texture_fn": texture_lightning_soft,    "paint_fn": paint_lightning_glow,   "variable_cc": False, "desc": "Forked lightning bolt paths"},
    "magma_crack":       {"texture_fn": texture_magma_crack,     "paint_fn": paint_magma_glow,       "variable_cc": False, "desc": "Voronoi boundary cracks with orange lava glow"},
    # "mandala" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "marble":            {"texture_fn": texture_marble,          "paint_fn": paint_marble_vein,      "variable_cc": False, "desc": "Soft noise veins like polished marble"},
    "matrix_rain": {"texture_fn": texture_matrix_rain, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Falling green character rain columns"},
    "mega_flake":        {"texture_fn": texture_mega_flake,      "paint_fn": paint_mega_sparkle,     "variable_cc": False, "desc": "Large hex glitter flake facets"},
    "metal_flake":       {"texture_fn": texture_metal_flake,      "paint_fn": paint_coarse_flake,     "variable_cc": False, "desc": "Coarse visible metallic flake"},
    "molecular": {"texture_fn": texture_molecular_v2, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Ball-and-stick molecular bond diagram"},
    # "mosaic" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "multicam":          {"texture_fn": texture_multicam,        "paint_fn": paint_multicam_colors,  "variable_cc": False, "desc": "5-layer organic Perlin camo pattern"},
    "nanoweave": {"texture_fn": texture_carbon_fiber, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Microscopic tight-knit nano fiber"},
    "neural": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Living neural network Voronoi cells"},
    "neuron_network": {"texture_fn": texture_neuron_network_v2, "paint_fn": paint_circuit_glow, "variable_cc": False, "desc": "Branching neural dendrite connection web"},
    "nitro_burst": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Nitrous oxide flame burst spray"},
    "none":              {"texture_fn": None,                     "paint_fn": paint_none,             "variable_cc": False, "desc": "No pattern overlay"},
    # "norse_rune" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "ocean_foam": {"texture_fn": texture_ocean_foam_v2, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "White sea foam bubbles on water"},
    "optical_illusion": {"texture_fn": texture_interference, "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Moire interference exotic geometry"},
    "p_plasma": {"texture_fn": texture_plasma, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Plasma ball discharge electric tendrils"},
    "p_tessellation": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Geometric Penrose-style tiling"},
    "p_topographic": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Contour map elevation isolines"},
    # "paisley" REMOVED - Artistic & Cultural replaced by image-based (engine/registry.py)
    "palm_frond": {"texture_fn": texture_palm_frond_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Tropical palm leaf frond silhouettes"},
    "peeling_paint": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Curling paint peel flake patches"},
    "pentagram": {"texture_fn": texture_pentagram_star, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Five-pointed star geometric array"},
    "perforated": {"texture_fn": texture_metal_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Evenly punched round hole grid"},
    "pinstripe":         {"texture_fn": texture_pinstripe,       "paint_fn": paint_pinstripe,        "variable_cc": False, "desc": "Thin parallel racing stripes"},
    "pinstripe_flames": {"texture_fn": texture_pinstripe_diagonal, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "[Legacy] Pinstripe flames - superseded by flame_pinstripe_outline"},
    "pit_lane_marks": {"texture_fn": texture_pinstripe_fine, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Pit lane boundary lines and markings"},
    "pixel_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Retro 8-bit pixel block mosaic"},
    "plaid":             {"texture_fn": texture_plaid,          "paint_fn": paint_plaid_tint,       "variable_cc": False, "desc": "Overlapping tartan plaid bands"},
    "plasma":            {"texture_fn": texture_plasma,           "paint_fn": paint_plasma_veins,     "variable_cc": False, "desc": "Branching electric plasma veins"},
    "podium_stripe": {"texture_fn": texture_chevron_bold, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Victory podium step stripe bands"},
    "pulse_monitor": {"texture_fn": texture_wave_choppy, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Multi-line vital signs monitor waveforms"},
    "qr_code": {"texture_fn": texture_houndstooth, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Dense QR code square block grid"},
    "racing_stripe": {"texture_fn": texture_pinstripe_vertical, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Bold dual center racing stripes"},
    "rain_drop":         {"texture_fn": texture_rain_drop,       "paint_fn": paint_rain_droplets,    "variable_cc": False, "desc": "Water droplet beading on surface"},
    "razor":             {"texture_fn": texture_razor,           "paint_fn": paint_razor_slash,      "variable_cc": False, "desc": "Diagonal aggressive slash marks"},
    "razor_wire":        {"texture_fn": texture_razor_wire,    "paint_fn": paint_razor_wire_scratch, "variable_cc": False, "desc": "Coiled helical wire with barbed loops"},
    "rev_counter": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Tachometer LED bar segment array"},
    "rip_tide": {"texture_fn": texture_wave_choppy, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Dangerous swirling rip current flow"},
    "ripple":            {"texture_fn": texture_ripple,           "paint_fn": paint_ripple_reflect,   "variable_cc": False, "desc": "Concentric water drop rings"},
    "rivet_grid": {"texture_fn": texture_rivet_plate, "paint_fn": paint_rivet_plate_emboss, "variable_cc": False, "desc": "Evenly spaced industrial rivet dots"},
    "rivet_plate":       {"texture_fn": texture_rivet_plate,    "paint_fn": paint_rivet_plate_emboss, "variable_cc": False, "desc": "Industrial riveted panel seams with chrome heads"},
    "road_rash": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Sliding contact abrasion scrape marks"},
    "roll_cage": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Tubular roll cage structure grid"},
    "rooster_tail": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "Dirt spray rooster tail splash"},
    "rpm_gauge": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Tachometer arc needle sweep"},
    "rust_bloom": {"texture_fn": texture_acid_wash, "paint_fn": paint_acid_etch, "variable_cc": True, "desc": "Expanding rust spot corrosion blooms"},
    "sandstorm": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Dense blowing sand particle streaks"},
    "shokk_bioform":      {"texture_fn": texture_shokk_bioform,      "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Alien reaction-diffusion organic living surface"},
    "shokk_bolt": {"texture_fn": texture_shokk_bolt_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Fractal branching lightning with chrome/matte split"},
    "shokk_fracture": {"texture_fn": texture_shokk_fracture_v2, "paint_fn": paint_shokk_phase, "variable_cc": True, "desc": "SHOKK: Shattered glass with chrome shard facets"},
    "shokk_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Perspective-warped digital grid tunnel"},
    "shokk_hex": {"texture_fn": texture_hex_mesh, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Hexagonal cells with electric edge glow"},
    "shokk_nebula":       {"texture_fn": texture_shokk_nebula,       "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Cosmic gas cloud with star-forming knots"},
    "shokk_phase_interference": {"texture_fn": texture_shokk_phase_interference, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK Phase: Dual-wave moiré interference pattern"},
    "shokk_phase_split":        {"texture_fn": texture_shokk_phase_split,        "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK Phase: Independent M/R sine waves - shimmer split"},
    "shokk_phase_vortex":       {"texture_fn": texture_shokk_phase_vortex,       "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK Phase: Radial/angular vortex with CC modulation"},
    "shokk_plasma_storm": {"texture_fn": texture_shokk_plasma_storm, "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Multi-epicenter branching plasma discharge"},
    "shokk_predator":     {"texture_fn": texture_shokk_predator,     "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Active camo distortion field hexagonal shimmer"},
    "shokk_pulse_wave": {"texture_fn": texture_shokk_pulse_wave_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Breathing concentric chrome/matte rings"},
    "shokk_scream": {"texture_fn": texture_shokk_scream_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Acoustic shockwave pressure visualization"},
    "shokk_singularity":  {"texture_fn": texture_shokk_singularity,  "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Black hole gravity well with accretion disk"},
    "shokk_tesseract":    {"texture_fn": texture_shokk_tesseract,    "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: 4D hypercube exotic geometry wireframe"},
    "shokk_waveform":     {"texture_fn": texture_shokk_waveform,     "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Audio frequency decomposition visualizer"},
    "shrapnel": {"texture_fn": texture_fracture, "paint_fn": paint_fracture_damage, "variable_cc": True, "desc": "Irregular shrapnel damage fragments"},
    "skid_marks": {"texture_fn": texture_tire_tread, "paint_fn": paint_tread_darken, "variable_cc": False, "desc": "Black rubber tire skid marks"},
    "skull":             {"texture_fn": texture_skull,          "paint_fn": paint_skull_darken,     "variable_cc": False, "desc": "Repeating skull mesh array"},
    "skull_wings": {"texture_fn": texture_skull, "paint_fn": paint_skull_darken, "variable_cc": False, "desc": "Affliction-style winged skull spread"},
    "snake_skin":        {"texture_fn": texture_snake_skin,      "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Elongated overlapping reptile scales"},
    "snake_skin_2":      {"texture_fn": texture_snake_skin_2,    "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Diamond-shaped python scales with color variation"},
    "snake_skin_3":      {"texture_fn": texture_snake_skin_3,    "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Hourglass saddle pattern viper scales"},
    "snake_skin_4":      {"texture_fn": texture_snake_skin_4,    "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Cobblestone pebble boa constrictor scales"},
    "solar_flare": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Erupting coronal mass ejection"},
    "sound_wave": {"texture_fn": texture_wave_gentle, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Audio waveform amplitude oscillation"},
    "soundwave": {"texture_fn": texture_wave_vertical, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Audio waveform visualization"},
    "spark_scatter": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Grinding metal spark shower trails"},
    "speed_lines": {"texture_fn": texture_speed_lines_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Motion speed streak action lines"},
    "spiderweb":         {"texture_fn": texture_spiderweb,      "paint_fn": paint_spiderweb_crack,  "variable_cc": False, "desc": "Radial + concentric web crack lines"},
    "sponsor_fade": {"texture_fn": texture_pinstripe_fine, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Gradient fade zones for sponsor areas"},
    "stardust":          {"texture_fn": texture_stardust,         "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Sparse bright star pinpoints"},
    "stardust_2":        {"texture_fn": texture_stardust_2,       "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Supernova explosion starburst"},
    "starting_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Grid slot positions track layout"},
    "static_noise":      {"texture_fn": texture_static_noise,  "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "TV static blocky pixel noise grain"},
    # "steampunk_gears" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "surf_stripe": {"texture_fn": texture_pinstripe_diagonal, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Retro surfboard racing stripes"},
    "tessellation": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Interlocking M.C. Escher-style tiles"},
    "thorn_vine": {"texture_fn": texture_barbed_wire, "paint_fn": paint_barbed_scratch, "variable_cc": False, "desc": "Twisted thorny vine dark botanical"},
    "tiger_stripe": {"texture_fn": texture_camo, "paint_fn": paint_camo_pattern, "variable_cc": False, "desc": "Organic tiger stripe broken bands"},
    "tiki_totem": {"texture_fn": texture_tribal_bands, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Carved tiki pole face pattern"},
    "tire_smoke": {"texture_fn": texture_tire_smoke_v2, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Burnout tire smoke wisps and haze"},
    "tire_tread":        {"texture_fn": texture_tire_tread,      "paint_fn": paint_tread_darken,     "variable_cc": False, "desc": "Directional V-groove rubber tread"},
    "topographic":       {"texture_fn": texture_topographic,    "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Elevation contour map lines"},
    "torch_burn": {"texture_fn": texture_flame_teardrop, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Focused torch flame burn marks"},
    "tornado": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Spiraling funnel vortex rotation"},
    "track_map": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Race circuit layout line pattern"},
    "tribal_flame": {"texture_fn": texture_flame_tribal_curves, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Tribal flame - superseded by flame_tribal_knife"},
    "tron":              {"texture_fn": texture_tron,            "paint_fn": paint_tron_glow,        "variable_cc": False, "desc": "Neon 48px grid with 2px light lines"},
    "trophy_laurel": {"texture_fn": texture_tribal_knot_dense, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Victory laurel wreath motif"},
    "tropical_leaf": {"texture_fn": texture_pinstripe_vertical, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Large monstera tropical leaf outlines"},
    "turbine":           {"texture_fn": texture_turbine,       "paint_fn": paint_turbine_spin,     "variable_cc": False, "desc": "Radial fan blade spiral from center"},
    "turbo_swirl": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Turbocharger compressor spiral vortex"},
    "victory_confetti": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Scattered celebration confetti"},
    "voronoi_shatter": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Clean voronoi cell shatter sharp edges"},
    "wave":              {"texture_fn": texture_wave,           "paint_fn": paint_wave_shimmer,     "variable_cc": False, "desc": "Smooth flowing sine wave ripples"},
    "wave_curl": {"texture_fn": texture_wave_choppy, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Curling ocean wave barrel shape"},
    "wildfire": {"texture_fn": texture_flame_wild, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Wildfire - superseded by flame_inferno_wall"},
    "wind_tunnel": {"texture_fn": texture_pinstripe_diagonal, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Flow visualization smoke streaks"},
    "wood_grain":        {"texture_fn": texture_wood_grain,      "paint_fn": paint_wood_grain,       "variable_cc": False, "desc": "Natural flowing wood grain texture"},
    "zebra": {"texture_fn": texture_zebra_stripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Bold black-white zebra stripe pattern"},
}

# Stubs for engine/chameleon.py functions - real implementations injected at startup.
# These exist only so MONOLITHIC_REGISTRY dict literal can evaluate without NameError.
# All are overridden by globals().update(_ch_fns) + MONOLITHIC_REGISTRY patch below.
def _chameleon_stub_paint(paint, shape, mask, seed, pm, bb): return paint
def _chameleon_stub_spec(shape, mask, seed, sm):
    import numpy as np
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 219; spec[:,:,1] = 12; spec[:,:,2] = 16
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec
spec_chameleon_pro       = _chameleon_stub_spec
paint_chameleon_arctic   = _chameleon_stub_paint
paint_chameleon_amethyst = _chameleon_stub_paint
paint_chameleon_copper   = _chameleon_stub_paint
paint_chameleon_emerald  = _chameleon_stub_paint
paint_chameleon_midnight = _chameleon_stub_paint
paint_chameleon_obsidian = _chameleon_stub_paint
paint_chameleon_ocean    = _chameleon_stub_paint
paint_chameleon_phoenix  = _chameleon_stub_paint
paint_chameleon_venom    = _chameleon_stub_paint
paint_mystichrome        = _chameleon_stub_paint

# Stubs for engine/prizm.py functions - real implementations injected at startup.
def _prizm_stub_paint(paint, shape, mask, seed, pm, bb): return paint
def _prizm_stub_spec(shape, mask, seed, sm):
    import numpy as np
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 225; spec[:,:,1] = 14; spec[:,:,2] = 30
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec
spec_prizm_adaptive      = _prizm_stub_spec
spec_prizm_arctic        = _prizm_stub_spec
spec_prizm_black_rainbow = _prizm_stub_spec
spec_prizm_duochrome     = _prizm_stub_spec
spec_prizm_ember         = _prizm_stub_spec
spec_prizm_holographic   = _prizm_stub_spec
spec_prizm_iridescent    = _prizm_stub_spec
spec_prizm_midnight      = _prizm_stub_spec
spec_prizm_mystichrome   = _prizm_stub_spec
spec_prizm_oceanic       = _prizm_stub_spec
spec_prizm_phoenix       = _prizm_stub_spec
spec_prizm_solar         = _prizm_stub_spec
spec_prizm_venom         = _prizm_stub_spec
paint_prizm_adaptive     = _prizm_stub_paint
paint_prizm_arctic       = _prizm_stub_paint
paint_prizm_black_rainbow= _prizm_stub_paint
paint_prizm_duochrome    = _prizm_stub_paint
paint_prizm_ember        = _prizm_stub_paint
paint_prizm_holographic  = _prizm_stub_paint
paint_prizm_iridescent   = _prizm_stub_paint
paint_prizm_midnight     = _prizm_stub_paint
paint_prizm_mystichrome  = _prizm_stub_paint
paint_prizm_oceanic      = _prizm_stub_paint
paint_prizm_phoenix      = _prizm_stub_paint
paint_prizm_solar        = _prizm_stub_paint
paint_prizm_venom        = _prizm_stub_paint

# --- MONOLITHIC FINISHES (can't decompose) ---
MONOLITHIC_REGISTRY = {
    "aurora":             (spec_aurora,        paint_aurora),
    "cel_shade":          (spec_cel_shade,     paint_cel_shade),
    "chameleon_arctic":   (spec_chameleon_pro, paint_chameleon_arctic),
    "chameleon_amethyst": (spec_chameleon_pro, paint_chameleon_amethyst),
    "chameleon_copper":   (spec_chameleon_pro, paint_chameleon_copper),
    "chameleon_emerald":  (spec_chameleon_pro, paint_chameleon_emerald),
    "chameleon_midnight": (spec_chameleon_pro, paint_chameleon_midnight),
    "chameleon_obsidian": (spec_chameleon_pro, paint_chameleon_obsidian),
    "chameleon_ocean":    (spec_chameleon_pro, paint_chameleon_ocean),
    "chameleon_phoenix":  (spec_chameleon_pro, paint_chameleon_phoenix),
    "chameleon_venom":    (spec_chameleon_pro, paint_chameleon_venom),
    "cs_chrome_shift":(spec_cs_chrome_shift, paint_cs_chrome_shift),
    "cs_complementary":(spec_cs_complementary, paint_cs_complementary),
    "cs_cool":       (spec_cs_cool,      paint_cs_cool),
    "cs_deepocean":  (spec_cs_deepocean,  paint_cs_deepocean),
    "cs_earth":      (spec_cs_earth,     paint_cs_earth),
    "cs_emerald":    (spec_cs_emerald,    paint_cs_emerald),
    "cs_extreme":    (spec_cs_extreme,   paint_cs_extreme),
    "cs_inferno":    (spec_cs_inferno,    paint_cs_inferno),
    "cs_monochrome": (spec_cs_monochrome, paint_cs_monochrome),
    "cs_mystichrome":(spec_cs_mystichrome,paint_cs_mystichrome),
    "cs_nebula":     (spec_cs_nebula,     paint_cs_nebula),
    "cs_neon_shift": (spec_cs_neon_shift, paint_cs_neon_shift),
    "cs_ocean_shift":(spec_cs_ocean_shift,paint_cs_ocean_shift),
    "cs_prism_shift":(spec_cs_prism_shift,paint_cs_prism_shift),
    "cs_rainbow":    (spec_cs_rainbow,   paint_cs_rainbow),
    "cs_solarflare": (spec_cs_solarflare, paint_cs_solarflare),
    "cs_split":      (spec_cs_split,     paint_cs_split),
    "cs_subtle":     (spec_cs_subtle,    paint_cs_subtle),
    "cs_supernova":  (spec_cs_supernova,  paint_cs_supernova),
    "cs_triadic":    (spec_cs_triadic,   paint_cs_triadic),
    "cs_vivid":      (spec_cs_vivid,     paint_cs_vivid),
    "cs_warm":       (spec_cs_warm,      paint_cs_warm),
    "ember_glow":   (spec_ember_glow,   paint_ember_glow),
    "frost_bite":   (spec_frost_bite,    paint_subtle_flake),
    "galaxy":       (spec_galaxy,        paint_galaxy_nebula),
    "glitch":             (spec_glitch,        paint_glitch),
    "holographic_wrap":   (spec_holographic,   paint_holographic_full),
    "liquid_metal": (spec_liquid_metal,  paint_liquid_reflect),
    "mystichrome":        (spec_chameleon_pro, paint_mystichrome),
    "neon_glow":    (spec_neon_glow,     paint_neon_edge),
    "oil_slick":    (spec_oil_slick,     paint_oil_slick),
    "phantom":      (spec_phantom,      paint_phantom_fade),
    "prizm_adaptive":     (spec_prizm_adaptive,     paint_prizm_adaptive),
    "prizm_arctic":       (spec_prizm_arctic,       paint_prizm_arctic),
    "prizm_black_rainbow":(spec_prizm_black_rainbow,paint_prizm_black_rainbow),
    "prizm_duochrome":    (spec_prizm_duochrome,    paint_prizm_duochrome),
    "prizm_ember":        (spec_prizm_ember,        paint_prizm_ember),
    "prizm_holographic":  (spec_prizm_holographic,  paint_prizm_holographic),
    "prizm_iridescent":   (spec_prizm_iridescent,   paint_prizm_iridescent),
    "prizm_midnight":     (spec_prizm_midnight,     paint_prizm_midnight),
    "prizm_mystichrome":  (spec_prizm_mystichrome,  paint_prizm_mystichrome),
    "prizm_oceanic":      (spec_prizm_oceanic,      paint_prizm_oceanic),
    "prizm_phoenix":      (spec_prizm_phoenix,      paint_prizm_phoenix),
    "prizm_solar":        (spec_prizm_solar,        paint_prizm_solar),
    "prizm_venom":        (spec_prizm_venom,        paint_prizm_venom),
    "radioactive":        (spec_radioactive,   paint_radioactive),
    "rust":         (spec_rust,          paint_rust_corrosion),
    "scorched":           (spec_scorched,      paint_scorched),
    "static":             (spec_static,        paint_static),
    "thermochromic":      (spec_thermochromic, paint_thermochromic),
    "weathered_paint": (spec_weathered_paint, paint_weathered_peel),
    "worn_chrome":  (spec_worn_chrome,   paint_patina),
}



# --- CHAMELEON + PRIZM MODULE OVERRIDES (V5 Extracted Modules) ---
# Uses importlib.util to load modules BY FILE PATH - bypasses engine/__init__.py
# and avoids the circular import (engine/__init__ re-imports shokker_engine_v2).
# Edit engine/chameleon.py and engine/prizm.py directly for these finishes.
try:
    import sys as _sys, os as _os, importlib.util as _ilu
    _engine_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "engine")

    # Load chameleon module directly (unique name avoids package cache conflict)
    _ch_path = _os.path.join(_engine_dir, "chameleon.py")
    if _os.path.exists(_ch_path):
        _ch_spec = _ilu.spec_from_file_location("__shokker_chameleon__", _ch_path)
        _chameleon_mod = _ilu.module_from_spec(_ch_spec)
        _ch_spec.loader.exec_module(_chameleon_mod)
        _chameleon_mod.integrate_chameleon(_sys.modules[__name__])
        # Inject all paint_* and spec_* functions into this module's namespace
        _ch_fns = {k: v for k, v in vars(_chameleon_mod).items()
                   if k.startswith('paint_') or k.startswith('spec_')}
        globals().update(_ch_fns)
        # Also patch MONOLITHIC_REGISTRY which captured the stub at construction time.
        # The dict stores function objects directly - replace BOTH spec and paint with real ones.
        _real_spec_ch_pro = _ch_fns.get('spec_chameleon_pro')
        if _real_spec_ch_pro:
            _chameleon_keys = [k for k, v in MONOLITHIC_REGISTRY.items()
                               if k.startswith('chameleon_') or k == 'mystichrome']
            for _ck in _chameleon_keys:
                _old_spec, _old_paint = MONOLITHIC_REGISTRY[_ck]
                # Use real paint from chameleon module (e.g. paint_chameleon_arctic); fallback to existing
                _real_paint = _ch_fns.get('paint_' + _ck, _old_paint)
                MONOLITHIC_REGISTRY[_ck] = (_real_spec_ch_pro, _real_paint)
        print(f"[V5] Chameleon module loaded ({len(_ch_fns)} functions)")
    else:
        print("[V5] engine/chameleon.py not found - using legacy chameleon stubs")
except Exception as _ch_err:
    print(f"[V5] Chameleon load error: {_ch_err}")

try:
    # Load prizm module directly
    _pz_path = _os.path.join(_engine_dir, "prizm.py")
    if _os.path.exists(_pz_path):
        _pz_spec = _ilu.spec_from_file_location("__shokker_prizm__", _pz_path)
        _prizm_mod = _ilu.module_from_spec(_pz_spec)
        _pz_spec.loader.exec_module(_prizm_mod)
        _prizm_mod.integrate_prizm(_sys.modules[__name__])
        _pz_fns = {k: v for k, v in vars(_prizm_mod).items()
                   if k.startswith('paint_') or k.startswith('spec_')}
        globals().update(_pz_fns)
        # Patch MONOLITHIC_REGISTRY prizm entries - same reason as chameleon above.
        for _pzk in [k for k in MONOLITHIC_REGISTRY if k.startswith('prizm_')]:
            _old_spec, _old_paint = MONOLITHIC_REGISTRY[_pzk]
            _new_spec  = _pz_fns.get(f'spec_{_pzk}',  _old_spec)
            _new_paint = _pz_fns.get(f'paint_{_pzk}', _old_paint)
            MONOLITHIC_REGISTRY[_pzk] = (_new_spec, _new_paint)
        print(f"[V5] Prizm module loaded ({len(_pz_fns)} functions)")
    else:
        print("[V5] engine/prizm.py not found - using legacy prizm stubs")
except Exception as _pz_err:
    print(f"[V5] Prizm load error: {_pz_err}")

# --- 24K ARSENAL EXPANSION ---
# Import and merge the 100/100/105 expansion entries into our registries
try:
    import sys as _sys
    import shokker_24k_expansion as _exp24k
    # Get a reference to THIS module so expansion can resolve string paint_fn refs
    _this_module = _sys.modules[__name__]
    _exp24k.integrate_expansion(_this_module)
except ImportError:
    print("[24K Arsenal] Expansion module not found - running with base 55/55/50 finishes")
except Exception as e:
    print(f"[24K Arsenal] Expansion load error: {e}")

# --- PATTERN EXPANSION (Decades, Flames, Music, Astro v2, Hero, Reactive) ---
# NEW_PATTERNS includes astro v2 (12 physics-based cosmic) and other expansion IDs
try:
    from engine.pattern_expansion import NEW_PATTERNS
    PATTERN_REGISTRY.update(NEW_PATTERNS)
except Exception as _e:
    pass

# --- COLOR MONOLITHICS EXPANSION (260+ color-changing finishes) ---
try:
    import shokker_color_monolithics as _clr_mono
    _clr_mono.integrate_color_monolithics(_sys.modules[__name__])
except ImportError:
    print("[Color Monolithics] Module not found - running without color finishes")
except Exception as e:
    print(f"[Color Monolithics] Load error: {e}")

# --- PARADIGM EXPANSION (Exotic Materials - PBR physics exploits) ---
try:
    import shokker_paradigm_expansion as _paradigm
    _paradigm.integrate_paradigm(_sys.modules[__name__])
except ImportError:
    print("[PARADIGM] Module not found - running without paradigm materials")
except Exception as e:
    print(f"[PARADIGM] Load error: {e}")

# --- FUSIONS EXPANSION (150 Paradigm Shift Hybrid Materials) ---
try:
    import shokker_fusions_expansion as _fusions
    _fusions.integrate_fusions(_sys.modules[__name__])
except ImportError:
    print("[FUSIONS] Module not found - running without paradigm shift fusions")
except Exception as e:
    print(f"[FUSIONS] Load error: {e}")

# --- ATELIER EXPANSION (Ultra-Detail / Pro Grade finishes) ---
try:
    import shokker_atelier_expansion as _atelier
    _atelier.integrate_atelier(_sys.modules[__name__])
except ImportError:
    print("[Atelier] Module not found - running without ultra-detail finishes")
except Exception as e:
    print(f"[Atelier] Load error: {e}")


# ================================================================
# GENERIC FALLBACK RENDERER - moved to engine.render
# ================================================================
from engine.render import render_generic_finish



# --- COMPOSE FUNCTIONS (array helpers from engine.core) ---

# ================================================================
# DUAL LAYER BASE SYSTEM - implementation in engine/overlay.py
# ================================================================
def _normalize_second_base_blend_mode(mode):
    """Delegate to engine.overlay (kept here for callers that use it by name)."""
    from engine.overlay import _normalize_second_base_blend_mode as _norm
    return _norm(mode)


def blend_dual_base_spec(spec_primary, spec_secondary, strength,
                          blend_mode="noise", noise_scale=24, seed=42,
                          pattern_mask=None, zone_mask=None, overlay_scale=1.0):
    """Delegate to engine.overlay with noise_fn=multi_scale_noise. overlay_scale from engine.overlay_context when not passed."""
    from engine.overlay import blend_dual_base_spec as _blend_spec
    try:
        from engine import overlay_context
        _scale = getattr(overlay_context, "overlay_scale", 1.0)
    except Exception:
        _scale = 1.0
    return _blend_spec(
        spec_primary, spec_secondary, strength,
        blend_mode=blend_mode, noise_scale=noise_scale, seed=seed,
        pattern_mask=pattern_mask, zone_mask=zone_mask,
        noise_fn=multi_scale_noise, overlay_scale=_scale
    )


def blend_dual_base_paint(paint_primary, paint_secondary, alpha_map):
    """Delegate to engine.overlay."""
    from engine.overlay import blend_dual_base_paint as _blend_paint
    return _blend_paint(paint_primary, paint_secondary, alpha_map)


def overlay_pattern_on_spec(spec, pattern_id, shape, mask, seed, sm, scale=1.0, opacity=1.0, spec_mult=1.0, rotation=0):
    """Overlay a pattern texture ON TOP of an existing spec map.

    Used to add patterns over monolithic finishes. The monolithic generates
    its own complete spec, then this function modulates M/R/CC with the
    pattern texture - same math as compose_finish, but starting from an
    arbitrary spec map instead of a flat base.

    opacity: 0-1, how much the pattern affects the monolithic's values.
             1.0 = full pattern modulation, 0.5 = half-strength.
    """
    if not pattern_id or pattern_id == "none" or pattern_id not in PATTERN_REGISTRY:
        return spec  # Nothing to overlay

    pattern = PATTERN_REGISTRY[pattern_id]
    # Image-based patterns (V5 engine registry): no texture_fn, use image_path
    image_path = pattern.get("image_path")
    if image_path:
        try:
            from engine.render import _load_image_pattern
            pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if pv is None:
                return spec
            pv = np.asarray(pv, dtype=np.float32)
            pv_min, pv_max = float(pv.min()), float(pv.max())
            if pv_max - pv_min > 1e-8:
                pv = (pv - pv_min) / (pv_max - pv_min)
            else:
                pv = np.zeros_like(pv)
            R_range, M_range = 60.0, 50.0
            M_arr = spec[:, :, 0].astype(np.float32)
            R_arr = spec[:, :, 1].astype(np.float32)
            M_arr = M_arr + pv * M_range * sm * opacity * spec_mult
            R_arr = R_arr + pv * R_range * sm * opacity * spec_mult
            spec[:, :, 0] = np.clip(M_arr * mask + spec[:, :, 0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:, :, 1] = np.clip(R_arr * mask + spec[:, :, 1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            return spec
        except Exception:
            return spec

    tex_fn = pattern.get("texture_fn")
    if tex_fn is None:
        return spec

    # Generate pattern texture at NATIVE resolution, apply scale via tiling/cropping
    tex = tex_fn(shape, mask, seed, sm)
    pv = tex["pattern_val"]
    R_range = tex["R_range"]
    M_range = tex["M_range"]

    # Scale via tiling/cropping
    if scale != 1.0 and scale > 0:
        pv, tex = _scale_pattern_output(pv, tex, scale, shape)

    # Rotate pattern if requested
    rot_angle = float(rotation) % 360
    if rot_angle != 0:
        pv = _rotate_array(pv, rot_angle, fill_value=0.0)

    # Read existing spec values as float
    M_arr = spec[:, :, 0].astype(np.float32)
    R_arr = spec[:, :, 1].astype(np.float32)

    # Modulate with pattern (same math as compose_finish, spec_mult scales spec punch)
    M_arr = M_arr + pv * M_range * sm * opacity * spec_mult
    R_arr = R_arr + pv * R_range * sm * opacity * spec_mult

    # Write back with mask
    spec[:, :, 0] = np.clip(M_arr * mask + spec[:, :, 0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_arr * mask + spec[:, :, 1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)

    return spec


def overlay_pattern_paint(paint, pattern_id, shape, mask, seed, pm, bb, scale=1.0, opacity=1.0, rotation=0, spec_mult=1.0):
    """Overlay a pattern's paint modifier ON TOP of a monolithic's paint output.

    Applies the pattern's paint_fn (if any) with attenuated strength.
    Uses spatial blending via pattern_val so paint follows actual texture shape.
    """
    if not pattern_id or pattern_id == "none" or pattern_id not in PATTERN_REGISTRY:
        return paint
    pattern = PATTERN_REGISTRY[pattern_id]
    pat_paint_fn = pattern.get("paint_fn", paint_none)
    if pat_paint_fn is paint_none:
        return paint
    hard_mask = np.where(mask > 0.5, mask, 0.0).astype(np.float32)
    # Save paint before pattern modification for spatial blending
    paint_before = paint.copy()
    # Run pattern paint - boosted for visibility (pattern paint_fns have tiny multipliers)
    # !! ARCHITECTURE GUARD - Same _PAT_PAINT_BOOST as compose_paint_mod. Keep in sync.
    _PAT_PAINT_BOOST = 3.5
    paint = pat_paint_fn(paint, shape, hard_mask, seed, pm * 0.5 * opacity * spec_mult * _PAT_PAINT_BOOST, bb * 0.5 * opacity * spec_mult * _PAT_PAINT_BOOST)
    # --- SPATIAL BLEND: use pattern_val to make paint follow texture shape ---
    image_path = pattern.get("image_path")
    if image_path:
        try:
            from engine.render import _load_image_pattern
            pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if pv is not None:
                pv = np.asarray(pv, dtype=np.float32)
                pv_min, pv_max = float(pv.min()), float(pv.max())
                if pv_max - pv_min > 1e-8:
                    pv = (pv - pv_min) / (pv_max - pv_min)
                else:
                    pv = np.ones_like(pv) * 0.5
                pv_3d = pv[:, :, np.newaxis] * opacity * spec_mult * 0.35
                paint = np.clip(paint_before * (1.0 - pv_3d) + paint * pv_3d, 0, 1).astype(np.float32)
        except Exception:
            pass
        return paint
    tex_fn = pattern.get("texture_fn")
    if tex_fn is not None:
        try:
            # Generate texture at NATIVE resolution, apply scale via tiling/cropping
            tex = tex_fn(shape, mask, seed, 1.0)
            pv = tex["pattern_val"] if isinstance(tex, dict) else tex
            # Scale via tiling/cropping
            if scale != 1.0 and scale > 0:
                if isinstance(tex, dict):
                    pv, tex = _scale_pattern_output(pv, tex, scale, shape)
                else:
                    if scale < 1.0:
                        factor = 1.0 / scale
                        pv = _tile_fractional(pv, factor, shape[0], shape[1])
                    else:
                        pv = _crop_center_array(pv, scale, shape[0], shape[1])
            rot_angle = float(rotation) % 360
            if rot_angle != 0:
                pv = _rotate_single_array(pv, rot_angle, shape)
            pv_min, pv_max = float(pv.min()), float(pv.max())
            if pv_max - pv_min > 1e-8:
                pv = (pv - pv_min) / (pv_max - pv_min)
            else:
                pv = np.ones_like(pv) * 0.5
            pv_3d = pv[:, :, np.newaxis]
            paint = paint_before * (1.0 - pv_3d) + paint * pv_3d
        except Exception:
            pass  # Fallback: keep uniform paint mod
    return paint


# ================================================================
# MULTI-ZONE BUILD - THE CORE (FIXED!)
# ================================================================

def build_multi_zone(paint_file, output_dir, zones, iracing_id="23371", seed=51, save_debug_images=False, import_spec_map=None, car_prefix="car_num", stamp_image=None, stamp_spec_finish="gloss", preview_mode=False):
    """
    Apply different finishes to different color-detected zones.

    Zone format supports THREE modes:

    1. LEGACY (backward compat): "finish" key maps to FINISH_REGISTRY
       {"name": "Body", "color": "blue", "finish": "chrome", "intensity": "100"}

    2. COMPOSITING (v3.0): "base" + optional "pattern" keys
       {"name": "Body", "color": "blue", "base": "chrome", "pattern": "carbon_fiber", "intensity": "100"}
       18 bases x 32 patterns = 576+ combinations!

    3. MONOLITHIC: "finish" key maps to MONOLITHIC_REGISTRY (phantom, ember_glow, etc.)
       {"name": "Body", "color": "blue", "finish": "phantom", "intensity": "100"}

    zones = [
        {
            "name": "Blue body panels",
            "color": "blue",
            "base": "chrome",           # v3.0 compositing
            "pattern": "carbon_fiber",   # Optional, defaults to "none"
            "intensity": "100",
        },
        {
            "name": "Gold accents",
            "color": {"hue_range": [40, 65], "sat_min": 0.3},
            "finish": "prismatic",       # Legacy mode still works
            "intensity": "100",
        },
        {
            "name": "Car Number",
            "color": [
                {"color_rgb": [255, 170, 0], "tolerance": 40},
                {"color_rgb": [51, 102, 255], "tolerance": 40},
                {"color_rgb": [200, 30, 30], "tolerance": 40},
            ],
            "base": "metallic",
            "pattern": "holographic_flake",
            "intensity": "150",
        },
        {
            "name": "Dark areas",
            "color": "dark",
            "base": "matte",
            "pattern": "carbon_fiber",
            "intensity": "80",
        },
        {
            "name": "Everything else",
            "color": "remaining",
            "finish": "gloss",
            "intensity": "50",
        },
    ]
    """
    print("=" * 60)
    print("  SHOKKER ENGINE v3.0 PRO - Base + Pattern Compositing")
    print(f"  Zones: {len(zones)}")
    print(f"  Combinations: {len(BASE_REGISTRY)} bases x {len(PATTERN_REGISTRY)} patterns = {len(BASE_REGISTRY) * len(PATTERN_REGISTRY)}+")
    print("=" * 60)

    start_time = time.time()
    if not preview_mode:
        os.makedirs(output_dir, exist_ok=True)

    # Load paint -- PROTECT THE ORIGINAL SOURCE FILE
    # ALWAYS back up the source in its own directory on first render.
    # On subsequent renders, ALWAYS load from the backup to prevent
    # cumulative degradation (re-processing a previously rendered file).
    import shutil
    if not preview_mode:
        print(f"\n  Loading: {paint_file}")
        paint_basename = os.path.basename(paint_file)
        source_normalized = os.path.normpath(os.path.abspath(paint_file))
        source_dir = os.path.dirname(source_normalized)

        if paint_basename.startswith("ORIGINAL_"):
            # Source is already the backup file - use it directly
            print(f"  Source is already the backup file - using directly")
        else:
            # Check for backup in the SOURCE directory (where the paint lives)
            backup_path = os.path.join(source_dir, f"ORIGINAL_{paint_basename}")
            if not os.path.exists(backup_path):
                # First render ever for this file - back it up
                shutil.copy2(paint_file, backup_path)
                print(f"  Backed up original to: {source_dir}/ORIGINAL_{paint_basename}")
            else:
                # Backup exists - ALWAYS load from it to avoid stacking effects
                paint_file = backup_path
                print(f"  Loading from backup: ORIGINAL_{paint_basename} (prevents re-processing)")

    t_load = time.time()
    scheme_img = Image.open(paint_file).convert('RGB')
    scheme = np.array(scheme_img).astype(np.float32) / 255.0
    h, w = scheme.shape[:2]
    shape = (h, w)
    print(f"  Resolution: {w}x{h}  ({time.time()-t_load:.2f}s)")

    # Analyze colors
    t_analyze = time.time()
    print()
    stats = analyze_paint_colors(scheme)
    print(f"  Color analysis: {time.time()-t_analyze:.2f}s")

    # Auto-generate zone names if not provided (Paint Booth UI doesn't send them)
    for i, zone in enumerate(zones):
        if "name" not in zone:
            base = zone.get("base", "")
            finish = zone.get("finish", "")
            pattern = zone.get("pattern", "")
            color = zone.get("color", "")
            if isinstance(color, str) and color == "remaining":
                zone["name"] = f"Zone {i+1} (remaining)"
            elif finish:
                zone["name"] = f"Zone {i+1} ({finish})"
            elif base:
                pat_label = f"+{pattern}" if pattern and pattern != "none" else ""
                zone["name"] = f"Zone {i+1} ({base}{pat_label})"
            else:
                zone["name"] = f"Zone {i+1}"

    # Build per-zone masks
    t_masks = time.time()
    print(f"\n  Building zone masks...")
    zone_masks = []
    claimed = np.zeros((h, w), dtype=np.float32)  # Track what's been claimed

    # First pass: build masks for non-remainder zones
    for i, zone in enumerate(zones):
        color_desc = zone.get("color", "everything")

        # SPATIAL REGION MASK: if the zone has a pre-drawn region mask, use it directly
        # This bypasses color detection entirely - great for numbers, sponsors, artwork
        if "region_mask" in zone and zone["region_mask"] is not None:
            region = zone["region_mask"]
            # Ensure it's the right size
            if region.shape[0] != h or region.shape[1] != w:
                from PIL import Image as PILImage
                rm_img = PILImage.fromarray((region * 255).astype(np.uint8))
                rm_img = rm_img.resize((w, h), PILImage.NEAREST)
                region = np.array(rm_img).astype(np.float32) / 255.0
            mask = region.astype(np.float32)
            # Subtract already-claimed areas
            mask = np.clip(mask - claimed * 0.8, 0, 1)
            claimed = np.clip(claimed + mask, 0, 1)
            pixel_count = np.sum(mask > 0.1)
            pct = pixel_count / (h * w) * 100
            print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (SPATIAL REGION MASK)")
            zone_masks.append(mask)
            continue

        # Parse selector(s) - can be a single selector or a LIST of selectors (multi-color zone)
        if isinstance(color_desc, list):
            # Multi-color zone: union of multiple color selectors
            # Each element is a dict like {"color_rgb": [R,G,B], "tolerance": 40}
            union_mask = np.zeros((h, w), dtype=np.float32)
            for sub_desc in color_desc:
                if isinstance(sub_desc, dict):
                    sub_selector = sub_desc
                else:
                    sub_selector = parse_color_description(str(sub_desc))
                sub_mask = build_zone_mask(scheme, stats, sub_selector, blur_radius=3)
                union_mask = np.maximum(union_mask, sub_mask)  # OR/union
            mask = union_mask
            print(f"    Zone {i+1} [{zone['name']}]: multi-color ({len(color_desc)} selectors)")
        elif isinstance(color_desc, dict):
            selector = color_desc
            if selector.get("remainder"):
                zone_masks.append(None)  # Placeholder
                continue
            mask = build_zone_mask(scheme, stats, selector, blur_radius=3)
        else:
            selector = parse_color_description(str(color_desc))
            if selector.get("remainder"):
                zone_masks.append(None)  # Placeholder
                continue
            mask = build_zone_mask(scheme, stats, selector, blur_radius=3)

        # ---- SPATIAL MASK: intersect color mask with drawn include/exclude regions ----
        # spatial_mask is a 2D numpy array: 0=unset, 1=include, 2=exclude
        # Unlike region_mask which REPLACES color detection, spatial_mask REFINES it.
        spatial = zone.get("spatial_mask")
        if spatial is not None and isinstance(spatial, np.ndarray):
            # Resize if needed
            if spatial.shape[0] != h or spatial.shape[1] != w:
                sm_img = Image.fromarray(spatial.astype(np.uint8))
                sm_img = sm_img.resize((w, h), Image.NEAREST)
                spatial = np.array(sm_img).astype(np.uint8)
            # Exclude: zero out pixels marked as 2
            mask = np.where(spatial == 2, 0.0, mask)
            # Include: if ANY pixels are marked as 1, restrict to only those
            has_include = np.any(spatial == 1)
            if has_include:
                mask = np.where(spatial == 1, mask, 0.0)

        # Subtract already-claimed areas (higher priority zones come first)
        mask = np.clip(mask - claimed * 0.8, 0, 1)

        # Add to claimed
        claimed = np.clip(claimed + mask, 0, 1)

        pixel_count = np.sum(mask > 0.1)
        pct = pixel_count / (h * w) * 100
        print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (color: {color_desc})")

        zone_masks.append(mask)

    # Harden zone masks: threshold soft masks so zones get clean ownership.
    # Without this, later zones (especially "remaining") bleed into earlier zones
    # because soft masks (0.0-1.0) leave gaps that remainder fills, then the blend
    # formula (zone_spec * mask + existing * (1-mask)) pulls values toward the later zone.
    HARD_THRESHOLD = 0.15  # Pixels above this get full ownership (mask=1.0)
    for i in range(len(zone_masks)):
        if zone_masks[i] is not None:
            soft = zone_masks[i]
            # Keep soft edges at the boundary but harden the core
            zone_masks[i] = np.where(soft > HARD_THRESHOLD, 1.0, soft / HARD_THRESHOLD * soft).astype(np.float32)

    # Rebuild claimed from hardened masks (so remainder doesn't bleed into them)
    claimed_hard = np.zeros((h, w), dtype=np.float32)
    for i in range(len(zone_masks)):
        if zone_masks[i] is not None:
            claimed_hard = np.clip(claimed_hard + zone_masks[i], 0, 1)

    # Second pass: fill in "remainder" zones
    for i, zone in enumerate(zones):
        if zone_masks[i] is not None:
            continue
        # Remainder = everything not yet claimed (using hardened masks)
        remainder_mask = np.clip(1.0 - claimed_hard, 0, 1)
        # Blur for soft edges at zone boundaries only
        rm_img = Image.fromarray((remainder_mask * 255).astype(np.uint8))
        rm_img = rm_img.filter(ImageFilter.GaussianBlur(radius=2))
        remainder_mask = np.array(rm_img).astype(np.float32) / 255.0
        # Zero out remainder inside claimed zones to prevent overwriting
        remainder_mask = np.where(claimed_hard > 0.5, 0.0, remainder_mask).astype(np.float32)

        pixel_count = np.sum(remainder_mask > 0.1)
        pct = pixel_count / (h * w) * 100
        print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (remainder)")
        zone_masks[i] = remainder_mask

    print(f"  Zone masks built: {time.time()-t_masks:.2f}s")

    # Per-zone "prior claimed": sum of earlier zone masks (clip to 1).
    # Stacks for ALL zones: Zone 1 wins, then Zone 2 gets remainder, then Zone 3, etc.
    # effective_mask[i] = zone_masks[i] * (1 - prior_claimed[i]) so later zones never overwrite earlier.
    prior_claimed = []
    _cum = np.zeros((h, w), dtype=np.float32)
    for _idx in range(len(zone_masks)):
        prior_claimed.append(_cum.copy())
        if zone_masks[_idx] is not None:
            _cum = np.clip(_cum + zone_masks[_idx], 0, 1)

    # Initialize outputs
    # Start with default spec OR imported spec map (for merge mode)
    if import_spec_map and os.path.exists(import_spec_map):
        print(f"\n  IMPORT SPEC MAP: Loading {os.path.basename(import_spec_map)}")
        try:
            imp_img = Image.open(import_spec_map)
            # Handle both RGBA (32-bit) and RGB (24-bit) spec maps
            if imp_img.mode == 'RGBA':
                combined_spec = np.array(imp_img).astype(np.uint8)
            elif imp_img.mode == 'RGB':
                rgb = np.array(imp_img).astype(np.uint8)
                alpha = np.full((rgb.shape[0], rgb.shape[1], 1), 255, dtype=np.uint8)
                combined_spec = np.concatenate([rgb, alpha], axis=2)
            else:
                imp_img = imp_img.convert('RGBA')
                combined_spec = np.array(imp_img).astype(np.uint8)
            # Resize to match paint if needed
            if combined_spec.shape[0] != h or combined_spec.shape[1] != w:
                imp_resized = Image.fromarray(combined_spec).resize((w, h), Image.LANCZOS)
                combined_spec = np.array(imp_resized).astype(np.uint8)
            print(f"    Imported spec: {combined_spec.shape[1]}x{combined_spec.shape[0]} RGBA")
            print(f"    Zones will MERGE on top of imported spec map")
        except Exception as e:
            print(f"    WARNING: Failed to load import spec map: {e}")
            print(f"    Falling back to default spec")
            combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
            combined_spec[:,:,0] = 5       # Low metallic
            combined_spec[:,:,1] = 100     # Medium-rough
            combined_spec[:,:,2] = 16      # Max clearcoat
            combined_spec[:,:,3] = 255     # Full spec mask
    else:
        combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
        combined_spec[:,:,0] = 5       # Low metallic
        combined_spec[:,:,1] = 100     # Medium-rough
        combined_spec[:,:,2] = 16      # Max clearcoat
        combined_spec[:,:,3] = 255     # Full spec mask
    paint = scheme.copy()

    # Apply each zone's finish using ITS OWN mask
    # Supports three dispatch modes:
    #   1. Compositing: zone has "base" key => compose_finish() + compose_paint_mod()
    #   2. Monolithic: zone has "finish" in MONOLITHIC_REGISTRY => special spec_fn/paint_fn
    #   3. Legacy: zone has "finish" in FINISH_REGISTRY => existing spec_fn/paint_fn
    t_finishes = time.time()
    print(f"\n  Applying finishes...")
    for i, zone in enumerate(zones):
        t_zone = time.time()
        name = zone["name"]
        intensity = zone.get("intensity", "100")
        # Use effective mask so this zone does not overwrite earlier zones (same-color overlap)
        zone_mask_raw = zone_masks[i]
        if zone_mask_raw is not None and i > 0 and prior_claimed[i] is not None:
            zone_mask = (zone_mask_raw * (1.0 - prior_claimed[i])).astype(np.float32)
        else:
            zone_mask = zone_mask_raw
        try:
            from engine import overlay_context
            overlay_context.overlay_scale = max(0.01, min(5.0, float(zone.get("second_base_scale", 1.0))))
        except Exception:
            pass

        if zone_mask is None or np.max(zone_mask) < 0.01:
            print(f"    [{name}] => SKIPPED (no matching pixels)")
            continue

        # Custom intensity overrides per-zone slider values
        # Custom sliders now use 0-1 normalized range (same as presets),
        # so they also need _INTENSITY_SCALE applied.
        custom = zone.get("custom_intensity")
        if custom:
            sm = float(custom.get("spec", 1.0))  * _INTENSITY_SCALE["spec"]
            pm = float(custom.get("paint", 1.0)) * _INTENSITY_SCALE["paint"]
            bb = float(custom.get("bright", 1.0)) * _INTENSITY_SCALE["bright"]
        else:
            sm, pm, bb = _parse_intensity(intensity)
        # Base vs Pattern Intensity: when pattern_intensity is set, pattern uses it so lowering base doesn't kill pattern
        pat_int = zone.get("pattern_intensity")
        if pat_int is not None:
            sm_pattern, _, _ = _parse_intensity(pat_int)
            try:
                pattern_intensity_01 = max(0.0, min(1.0, float(pat_int) / 100.0))
            except (TypeError, ValueError):
                pattern_intensity_01 = 1.0
        else:
            sm_pattern = sm
            pattern_intensity_01 = 1.0

        # --- Dispatch: determine which rendering path to use ---
        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")
        _engine_rot_debug(f"BUILD_MULTI_ZONE [{name}]: base_id={base_id}, finish_name={finish_name}, "
                          f"rotation={zone.get('rotation')}, finish_colors={zone.get('finish_colors') is not None}, "
                          f"in_MONO_REG={finish_name in MONOLITHIC_REGISTRY if finish_name else 'N/A'}, "
                          f"in_FINISH_REG={finish_name in FINISH_REGISTRY if finish_name else 'N/A'}")

        if base_id:
            # CHECK: Is this actually a monolithic masquerading as a base?
            # This lets the UI send monolithics via "base" key seamlessly.
            if base_id not in BASE_REGISTRY and base_id in MONOLITHIC_REGISTRY:
                finish_name = base_id
                base_id = None  # Fall through to monolithic path below
            elif base_id not in BASE_REGISTRY:
                print(f"    WARNING: Unknown base '{base_id}', skipping")
                continue

        if base_id:
            _engine_rot_debug(f"  [{name}] -> PATH 1 (compositing): base={base_id}")
            # PATH 1: v3.0 COMPOSITING - base + pattern (or pattern stack)
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                print(f"    WARNING: Unknown pattern '{pattern_id}', using 'none'")
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # SMART AUTO-SCALE: adapt pattern density to zone coverage area
            # Small zones (car numbers, sponsors) get denser patterns automatically
            auto_scale = _compute_zone_auto_scale(zone_mask, shape)
            if auto_scale < 1.0 and pattern_id != "none":
                print(f"      [{name}] Auto-scale: {auto_scale:.3f} (zone covers {(auto_scale**2)*100:.1f}% of canvas)")
            zone_scale *= auto_scale  # User slider multiplies on top of auto-scale

            # ZONE TARGETING: Fit to Zone bounding box
            # Concentrates the entire pattern into the zone's bounding box.
            # Without this, small zones (car numbers, logos) only see a tiny crop
            # of a full-canvas pattern. With it, the whole pattern squeezes into the zone.
            if zone.get("pattern_fit_zone", False) and zone_mask is not None:
                rows = np.any(zone_mask > 0.1, axis=1)
                cols = np.any(zone_mask > 0.1, axis=0)
                if rows.any() and cols.any():
                    r_min, r_max = np.where(rows)[0][[0, -1]]
                    c_min, c_max = np.where(cols)[0][[0, -1]]
                    bbox_h = r_max - r_min + 1
                    bbox_w = c_max - c_min + 1
                    bbox_center_y = (r_min + r_max) / 2.0 / h
                    bbox_center_x = (c_min + c_max) / 2.0 / w
                    # Override offset to center pattern on zone bbox
                    zone['pattern_offset_x'] = bbox_center_x
                    zone['pattern_offset_y'] = bbox_center_y
                    # ZOOM IN so the pattern fills just the bbox area
                    # fit_ratio < 1.0 for small zones; dividing by it zooms in
                    fit_ratio = max(bbox_h / h, bbox_w / w)
                    if fit_ratio > 0.01:
                        zone_scale = zone_scale / fit_ratio  # zoom in to concentrate
                    print(f"      [{name}] Fit-to-Zone: bbox=({r_min},{c_min})-({r_max},{c_max}), fit_ratio={fit_ratio:.3f}, effective_scale={zone_scale:.3f}, center=({bbox_center_x:.3f},{bbox_center_y:.3f})")

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) if _z_cc is not None else None
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {"pattern_sm": sm_pattern, "pattern_intensity": pattern_intensity_01}
            _v6kw["base_strength"] = float(zone.get("base_strength", 1.0))
            _v6kw["base_spec_strength"] = float(zone.get("base_spec_strength", 1.0))
            _v6kw["base_spec_blend_mode"] = zone.get("base_spec_blend_mode", "normal")
            _v6kw["base_color_mode"] = zone.get("base_color_mode", "source")
            _v6kw["base_color"] = zone.get("base_color", [1.0, 1.0, 1.0])
            _v6kw["base_color_source"] = zone.get("base_color_source")
            _v6kw["base_color_strength"] = float(zone.get("base_color_strength", 1.0))
            _v6kw["base_hue_offset"] = float(zone.get("base_hue_offset", 0))
            _v6kw["base_saturation_adjust"] = float(zone.get("base_saturation_adjust", 0))
            _v6kw["base_brightness_adjust"] = float(zone.get("base_brightness_adjust", 0))
            _v6kw["pattern_opacity"] = float(zone.get("pattern_opacity", 1.0))
            _v6kw["pattern_offset_x"] = max(0.0, min(1.0, float(zone.get("pattern_offset_x", 0.5))))
            _v6kw["pattern_offset_y"] = max(0.0, min(1.0, float(zone.get("pattern_offset_y", 0.5))))
            _v6kw["pattern_flip_h"] = bool(zone.get("pattern_flip_h", False))
            _v6kw["pattern_flip_v"] = bool(zone.get("pattern_flip_v", False))
            _v6kw["base_offset_x"] = max(0.0, min(1.0, float(zone.get("base_offset_x", 0.5))))
            _v6kw["base_offset_y"] = max(0.0, min(1.0, float(zone.get("base_offset_y", 0.5))))
            _v6kw["base_rotation"] = float(zone.get("base_rotation", 0))
            _v6kw["base_flip_h"] = bool(zone.get("base_flip_h", False))
            _v6kw["base_flip_v"] = bool(zone.get("base_flip_v", False))
            if zone.get("spec_pattern_stack"): _v6kw["spec_pattern_stack"] = zone["spec_pattern_stack"]
            if zone.get("overlay_spec_pattern_stack"): _v6kw["overlay_spec_pattern_stack"] = zone["overlay_spec_pattern_stack"]
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba; print(f"    [{name}] v6.1 BLEND: base={_z_bb}, dir={_z_bd}, amount={_z_ba:.2f}")
            if _z_pc: _v6kw["paint_color"] = _z_pc
            # Dual Layer Base Overlay
            _z_sb = zone.get("second_base")
            if _z_sb:
                _v6kw["second_base"] = _z_sb
                _v6kw["second_base_color"] = zone.get("second_base_color", [1.0, 1.0, 1.0])
                _v6kw["second_base_strength"] = float(zone.get("second_base_strength", 0.0))
                _v6kw["second_base_spec_strength"] = float(zone.get("second_base_spec_strength", 1.0))
                _v6kw["second_base_blend_mode"] = zone.get("second_base_blend_mode", "noise")
                _v6kw["second_base_noise_scale"] = int(zone.get("second_base_noise_scale", 24))
                _v6kw["second_base_scale"] = float(zone.get("second_base_scale", 1.0))
                _v6kw["second_base_pattern"] = zone.get("second_base_pattern")
                # Keep react-to-pattern overlays spatially aligned with the primary pattern scale.
                _v6kw["second_base_pattern_scale"] = float(zone.get("second_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["second_base_pattern_rotation"] = float(zone.get("second_base_pattern_rotation", 0.0))
                _v6kw["second_base_pattern_opacity"] = float(zone.get("second_base_pattern_opacity", 1.0))
                _v6kw["second_base_pattern_strength"] = float(zone.get("second_base_pattern_strength", 1.0))
                _v6kw["second_base_pattern_invert"] = bool(zone.get("second_base_pattern_invert", False))
                _v6kw["second_base_pattern_harden"] = bool(zone.get("second_base_pattern_harden", False))
                _sb_ox = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                _sb_oy = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                _sb_pscale = _v6kw["second_base_pattern_scale"]
                # Fit-to-Zone for 2nd base overlay
                if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _sb_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _sb_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _sb_pscale = _sb_pscale / _ft_ratio
                _v6kw["second_base_pattern_offset_x"] = _sb_ox
                _v6kw["second_base_pattern_offset_y"] = _sb_oy
                _v6kw["second_base_pattern_scale"] = _sb_pscale
            _v6kw["second_base_color_source"] = zone.get("second_base_color_source")
            _z_tb = zone.get("third_base")
            if _z_tb:
                _v6kw["third_base"] = _z_tb
                _v6kw["third_base_color"] = zone.get("third_base_color", [1.0, 1.0, 1.0])
                _v6kw["third_base_strength"] = float(zone.get("third_base_strength", 0.0))
                _v6kw["third_base_spec_strength"] = float(zone.get("third_base_spec_strength", 1.0))
                _v6kw["third_base_blend_mode"] = zone.get("third_base_blend_mode", "noise")
                _v6kw["third_base_noise_scale"] = int(zone.get("third_base_noise_scale", 24))
                _v6kw["third_base_scale"] = float(zone.get("third_base_scale", 1.0))
                _v6kw["third_base_pattern"] = zone.get("third_base_pattern")
                _v6kw["third_base_pattern_scale"] = float(zone.get("third_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["third_base_pattern_rotation"] = float(zone.get("third_base_pattern_rotation", 0.0))
                _v6kw["third_base_pattern_opacity"] = float(zone.get("third_base_pattern_opacity", 1.0))
                _v6kw["third_base_pattern_strength"] = float(zone.get("third_base_pattern_strength", 1.0))
                _v6kw["third_base_pattern_invert"] = bool(zone.get("third_base_pattern_invert", False))
                _v6kw["third_base_pattern_harden"] = bool(zone.get("third_base_pattern_harden", False))
                _tb_ox = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_x", 0.5))))
                _tb_oy = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_y", 0.5))))
                _tb_pscale = _v6kw["third_base_pattern_scale"]
                # Fit-to-Zone for 3rd base overlay
                if zone.get("third_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _tb_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _tb_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _tb_pscale = _tb_pscale / _ft_ratio
                _v6kw["third_base_pattern_offset_x"] = _tb_ox
                _v6kw["third_base_pattern_offset_y"] = _tb_oy
                _v6kw["third_base_pattern_scale"] = _tb_pscale
            _v6kw["third_base_color_source"] = zone.get("third_base_color_source")
            _z_fb = zone.get("fourth_base")
            if _z_fb:
                _v6kw["fourth_base"] = _z_fb
                _v6kw["fourth_base_color"] = zone.get("fourth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fourth_base_strength"] = float(zone.get("fourth_base_strength", 0.0))
                _v6kw["fourth_base_spec_strength"] = float(zone.get("fourth_base_spec_strength", 1.0))
                _v6kw["fourth_base_blend_mode"] = zone.get("fourth_base_blend_mode", "noise")
                _v6kw["fourth_base_noise_scale"] = int(zone.get("fourth_base_noise_scale", 24))
                _v6kw["fourth_base_scale"] = float(zone.get("fourth_base_scale", 1.0))
                _v6kw["fourth_base_pattern"] = zone.get("fourth_base_pattern")
                _v6kw["fourth_base_pattern_scale"] = float(zone.get("fourth_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["fourth_base_pattern_rotation"] = float(zone.get("fourth_base_pattern_rotation", 0.0))
                _v6kw["fourth_base_pattern_opacity"] = float(zone.get("fourth_base_pattern_opacity", 1.0))
                _v6kw["fourth_base_pattern_strength"] = float(zone.get("fourth_base_pattern_strength", 1.0))
                _v6kw["fourth_base_pattern_invert"] = bool(zone.get("fourth_base_pattern_invert", False))
                _v6kw["fourth_base_pattern_harden"] = bool(zone.get("fourth_base_pattern_harden", False))
                _fb_ox = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_x", 0.5))))
                _fb_oy = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_y", 0.5))))
                _fb_pscale = _v6kw["fourth_base_pattern_scale"]
                # Fit-to-Zone for 4th base overlay
                if zone.get("fourth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fb_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _fb_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _fb_pscale = _fb_pscale / _ft_ratio
                _v6kw["fourth_base_pattern_offset_x"] = _fb_ox
                _v6kw["fourth_base_pattern_offset_y"] = _fb_oy
                _v6kw["fourth_base_pattern_scale"] = _fb_pscale
            _v6kw["fourth_base_color_source"] = zone.get("fourth_base_color_source")
            _z_fif = zone.get("fifth_base")
            if _z_fif:
                _v6kw["fifth_base"] = _z_fif
                _v6kw["fifth_base_color"] = zone.get("fifth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fifth_base_strength"] = float(zone.get("fifth_base_strength", 0.0))
                _v6kw["fifth_base_spec_strength"] = float(zone.get("fifth_base_spec_strength", 1.0))
                _v6kw["fifth_base_blend_mode"] = zone.get("fifth_base_blend_mode", "noise")
                _v6kw["fifth_base_noise_scale"] = int(zone.get("fifth_base_noise_scale", 24))
                _v6kw["fifth_base_scale"] = float(zone.get("fifth_base_scale", 1.0))
                _v6kw["fifth_base_pattern"] = zone.get("fifth_base_pattern")
                _v6kw["fifth_base_pattern_scale"] = float(zone.get("fifth_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["fifth_base_pattern_rotation"] = float(zone.get("fifth_base_pattern_rotation", 0.0))
                _v6kw["fifth_base_pattern_opacity"] = float(zone.get("fifth_base_pattern_opacity", 1.0))
                _v6kw["fifth_base_pattern_strength"] = float(zone.get("fifth_base_pattern_strength", 1.0))
                _v6kw["fifth_base_pattern_invert"] = bool(zone.get("fifth_base_pattern_invert", False))
                _v6kw["fifth_base_pattern_harden"] = bool(zone.get("fifth_base_pattern_harden", False))
                _fif_ox = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_x", 0.5))))
                _fif_oy = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_y", 0.5))))
                _fif_pscale = _v6kw["fifth_base_pattern_scale"]
                # Fit-to-Zone for 5th base overlay
                if zone.get("fifth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fif_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _fif_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _fif_pscale = _fif_pscale / _ft_ratio
                _v6kw["fifth_base_pattern_offset_x"] = _fif_ox
                _v6kw["fifth_base_pattern_offset_y"] = _fif_oy
                _v6kw["fifth_base_pattern_scale"] = _fif_pscale
            _v6kw["fifth_base_color_source"] = zone.get("fifth_base_color_source")
            _v6kw["monolithic_registry"] = MONOLITHIC_REGISTRY

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                # (prevents double-rendering at zone_scale=1.0 which overwhelms the stack's scale)
                stack_ids = {ps.get("id") for ps in pattern_stack[:3] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation})
                for ps in pattern_stack[:3]:  # Max 3 additional
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)) * auto_scale,  # Auto-scale stack layers too
                            "rotation": float(ps.get("rotation", 0)),
                            "blend_mode": ps.get("blend_mode", "normal"),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%{"["+p.get("blend_mode","normal")+"]" if p.get("blend_mode","normal") != "normal" else ""}' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                bs_label = f" base@{zone_base_scale:.2f}x" if zone_base_scale != 1.0 else ""
                print(f"    [{name}] => {label} ({intensity}){bs_label} [stacked compositing]")
                # v6.1: build blend paint kwargs
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0), "pattern_intensity": pattern_intensity_01}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                if all_patterns:
                    zone_spec = compose_finish_stacked(base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                else:
                    zone_spec = compose_finish(base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod(base_id, "none", paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.2f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                bs_label = f" base@{zone_base_scale:.2f}x" if zone_base_scale != 1.0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}{bs_label} [compositing]")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0), "pattern_intensity": pattern_intensity_01}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                zone_spec = compose_finish(base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation, **_v6paint)

        elif finish_name and zone.get("finish_colors") and (
            finish_name.startswith("grad_") or finish_name.startswith("gradm_")
            or finish_name.startswith("grad3_") or finish_name.startswith("ghostg_")
            or finish_name.startswith("mc_")
        ):
            # PATH 4 first for client-defined gradient types - client colors always win over registry
            zone_rotation = float(zone.get("rotation", 0))
            _engine_rot_debug(f"  [{name}] -> PATH 4 (generic, client gradient): finish={finish_name}, rotation={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)

        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            _engine_rot_debug(f"  [{name}] -> PATH 2 (monolithic): finish={finish_name}")
            # PATH 2: MONOLITHIC - special finishes (now with optional pattern overlay!)
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_pat_scale = float(zone.get("scale", 1.0))
            mono_pat_opacity = float(zone.get("pattern_opacity", 1.0))
            # SMART AUTO-SCALE for monolithic pattern overlay
            mono_auto_scale = _compute_zone_auto_scale(zone_mask, shape)
            mono_pat_scale *= mono_auto_scale
            mono_pat_rotation = float(zone.get("rotation", 0))
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            bs_label = f" base@{mono_base_scale:.2f}x" if mono_base_scale != 1.0 else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}){bs_label} [monolithic]")

            _mono_base_strength = max(0.0, min(2.0, float(zone.get("base_strength", 1.0))))
            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                # Use FULL mask for tile generation - monolithic covers entire tile.
                # Original zone_mask handles final clipping. This prevents existing
                # car art (numbers, sponsors, decals) from leaking into tiled output.
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                # Generate spec at tile size (full coverage)
                tile_spec = spec_fn(tile_shape, tile_mask, seed + i * 13, sm * _mono_base_strength)
                # Tile spec to fill original shape
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                # For paint: run paint_fn on ORIGINAL paint at full resolution.
                # Scaling only affects the spec map (material properties), NOT the paint.
                # Previous approach created a blank canvas which destroyed the car livery.
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm * _mono_base_strength, bb * _mono_base_strength)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm * _mono_base_strength)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm * _mono_base_strength, bb * _mono_base_strength)

            # Apply HSB adjustments to monolithic paint (same as base+pattern path)
            _mono_hue = float(zone.get("base_hue_offset", 0))
            _mono_sat = float(zone.get("base_saturation_adjust", 0))
            _mono_bri = float(zone.get("base_brightness_adjust", 0))
            if abs(_mono_hue) >= 0.5 or abs(_mono_sat) >= 0.5 or abs(_mono_bri) >= 0.5:
                paint = _apply_hsb_adjustments(paint, zone_mask, _mono_hue, _mono_sat, _mono_bri)

            # Optional pattern overlay on top of monolithic
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_pat_scale, mono_pat_opacity, spec_mult=spec_mult, rotation=mono_pat_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_pat_scale, mono_pat_opacity, rotation=mono_pat_rotation)

            # Dual Layer Base Overlay on monolithic (same as base+pattern path)
            _z_sb = zone.get("second_base")
            _z_sb_color_src = zone.get("second_base_color_source")
            _z_sb_is_mono = _z_sb and str(_z_sb).startswith("mono:")
            _z_sb_in_base = _z_sb and _z_sb in BASE_REGISTRY
            _z_sb_in_mono = _z_sb_is_mono and _z_sb[5:] in MONOLITHIC_REGISTRY
            _z_sb_src_is_mono = _z_sb_color_src and str(_z_sb_color_src).startswith("mono:") and _z_sb_color_src[5:] in MONOLITHIC_REGISTRY
            _z_sb_str = float(zone.get("second_base_strength", 0))
            print(f"    [{name}] OVERLAY CHECK: sb='{_z_sb}', src='{_z_sb_color_src}', is_mono={_z_sb_is_mono}, in_base={_z_sb_in_base}, in_mono={_z_sb_in_mono}, src_in_mono={_z_sb_src_is_mono}, strength={_z_sb_str}")
            if (_z_sb_in_base or _z_sb_in_mono or _z_sb_src_is_mono) and _z_sb_str > 0.001:
                try:
                    _sb_strength = float(zone.get("second_base_strength", 0))
                    _has_sb_spec = bool(_z_sb_in_base or _z_sb_in_mono)
                    spec_secondary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
                    if _z_sb_in_mono:
                        # Special finish as overlay - use its spec_fn
                        _mono_id = _z_sb[5:]
                        _sb_spec_fn = MONOLITHIC_REGISTRY[_mono_id][0]
                        _sb_seed_off = abs(hash(_z_sb)) % 10000
                        spec_secondary = _sb_spec_fn(shape, zone_mask, seed + i * 13 + _sb_seed_off, sm)
                        print(f"    [{name}] 2nd base overlay: MONO spec '{_mono_id}'")
                    else:
                        # Regular base as overlay - existing logic
                        _sb_def = BASE_REGISTRY[_z_sb]
                        _sb_M = float(_sb_def["M"])
                        _sb_R = float(_sb_def["R"])
                        _sb_CC = int(_sb_def.get("CC", 16))
                        _sb_seed_off = abs(hash(_z_sb)) % 10000
                        if _sb_def.get("base_spec_fn"):
                            _sb_result = _sb_def["base_spec_fn"](shape, seed + i * 13 + _sb_seed_off, sm, _sb_M, _sb_R)
                            _sb_M_arr = _sb_result[0]
                            _sb_R_arr = _sb_result[1]
                            _sb_CC_arr = _sb_result[2] if len(_sb_result) > 2 else np.full(shape, float(_sb_CC))
                        elif _sb_def.get("perlin"):
                            _sb_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed + i * 13 + _sb_seed_off)
                            _sb_M_arr = _sb_M + _sb_noise * _sb_def.get("noise_M", 0) * sm
                            _sb_R_arr = _sb_R + _sb_noise * _sb_def.get("noise_R", 0) * sm
                            _sb_CC_arr = np.full(shape, float(_sb_CC))
                        else:
                            _sb_M_arr = np.full(shape, _sb_M)
                            _sb_R_arr = np.full(shape, _sb_R)
                            _sb_CC_arr = np.full(shape, float(_sb_CC))
                        _sb_M_final = _sb_M_arr * zone_mask + 5.0 * (1 - zone_mask)
                        _sb_R_final = _sb_R_arr * zone_mask + 100.0 * (1 - zone_mask)
                        spec_secondary[:,:,0] = np.clip(_sb_M_final, 0, 255).astype(np.uint8)
                        spec_secondary[:,:,1] = np.clip(_sb_R_final, 0, 255).astype(np.uint8)
                        spec_secondary[:,:,2] = np.clip(_sb_CC_arr * zone_mask, 0, 255).astype(np.uint8)
                        spec_secondary[:,:,3] = 255
                    _sb_bm = zone.get("second_base_blend_mode", "noise")
                    # Use "React to zone pattern" (second_base_pattern) first; fallback to zone L1 pattern
                    _pat_id = zone.get("second_base_pattern") or zone.get("pattern") or zone.get("mono_pattern")
                    _sb_bm_norm = _normalize_second_base_blend_mode(_sb_bm)
                    # Build pattern mask for pattern, pattern_vivid, AND tint (so tint is pattern-driven, not uniform)
                    _sb_needs_mask = _sb_bm_norm in ("pattern", "pattern_vivid", "tint")
                    # Monolithic path: use same effective scale space as zone pattern overlay.
                    _sb_pat_scale = max(0.1, min(10.0, float(zone.get("second_base_pattern_scale", 1.0)) * mono_auto_scale))
                    _sb_pat_rot = float(zone.get("second_base_pattern_rotation", 0))
                    _sb_pat_op = zone.get("second_base_pattern_opacity", 1.0)
                    _sb_pat_op = min(1.0, float(_sb_pat_op)) if float(_sb_pat_op) > 1 else float(_sb_pat_op)
                    _sb_pat_str = max(0.0, min(2.0, float(zone.get("second_base_pattern_strength", 1.0))))
                    _sb_pat_ox = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                    _sb_pat_oy = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                    # Fit-to-Zone for 2nd base overlay (monolithic path)
                    if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                        _ftrows = np.any(zone_mask > 0.1, axis=1)
                        _ftcols = np.any(zone_mask > 0.1, axis=0)
                        if _ftrows.any() and _ftcols.any():
                            _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                            _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                            _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                            if _ft_ratio > 0.01:
                                _sb_pat_ox = (_ftc_min + _ftc_max) / 2.0 / w
                                _sb_pat_oy = (_ftr_min + _ftr_max) / 2.0 / h
                                _sb_pat_scale = _sb_pat_scale / _ft_ratio
                    _pat_mask = _get_pattern_mask(_pat_id, shape, zone_mask, seed + i * 13, sm, scale=_sb_pat_scale, rotation=_sb_pat_rot, opacity=_sb_pat_op, strength=_sb_pat_str, offset_x=_sb_pat_ox, offset_y=_sb_pat_oy) if _sb_needs_mask and _pat_id else None
                    if _pat_mask is not None:
                        if zone.get("second_base_pattern_invert"):
                            _pat_mask = 1.0 - _pat_mask
                        if zone.get("second_base_pattern_harden"):
                            _pat_mask = np.clip((_pat_mask.astype(np.float32) - 0.45) / 0.15, 0, 1)
                    if _pat_mask is not None and _sb_bm_norm == "pattern_vivid":
                        print(f"[POP DEBUG] mode={_sb_bm}, pattern_id={_pat_id}, pat_in_reg={_pat_id in PATTERN_REGISTRY if _pat_id else False}, pattern_mask_is_None=False")
                    if _has_sb_spec:
                        zone_spec, _ = blend_dual_base_spec(
                            zone_spec, spec_secondary,
                            strength=_sb_strength,
                            blend_mode=_sb_bm,
                            noise_scale=int(zone.get("second_base_noise_scale", 24)),
                            seed=seed + i * 13,
                            pattern_mask=_pat_mask,
                            zone_mask=zone_mask
                        )
                    # Paint side: tint overlay with second_base_color and blend
                    hard_mask = np.where(zone_mask > 0.5, zone_mask, 0.0).astype(np.float32)
                    paint_overlay = paint.copy()
                    _sb_mask3d = hard_mask[:, :, np.newaxis]
                    _sb_src_mono_id = None
                    if _z_sb_src_is_mono:
                        _sb_src_mono_id = _z_sb_color_src[5:]
                    elif _z_sb_in_mono and MONOLITHIC_REGISTRY.get(_z_sb[5:]):
                        _sb_src_mono_id = _z_sb[5:]
                    if _sb_src_mono_id and MONOLITHIC_REGISTRY.get(_sb_src_mono_id):
                        # Use the mono's paint_fn - it generates its own colors
                        # from a neutral seed so strong underlying bases (e.g. prizm_duochrome)
                        # don't swallow overlay identity.
                        _mono_paint_fn = MONOLITHIC_REGISTRY[_sb_src_mono_id][1]
                        _seed_paint = np.full_like(paint[:, :, :3], 0.533, dtype=np.float32)
                        _color_paint = _mono_paint_fn(_seed_paint, shape, hard_mask, seed + i * 13 + 7777, 1.0, 0.0)
                        if _color_paint is not None:
                            paint_overlay[:, :, :3] = _color_paint[:, :, :3]
                        print(f"    [{name}] 2nd base overlay: MONO color source '{_sb_src_mono_id}'")
                    else:
                        _sb_color = zone.get("second_base_color", [1.0, 1.0, 1.0])
                        if _sb_color is not None and len(_sb_color) >= 3:
                            _sb_r = float(_sb_color[0])
                            _sb_g = float(_sb_color[1])
                            _sb_b = float(_sb_color[2])
                            _sb_rgb = np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                            paint_overlay[:, :, :3] = paint_overlay[:, :, :3] * (1.0 - _sb_mask3d) + _sb_rgb * _sb_mask3d
                            if _z_sb_in_base:
                                _sb_def = BASE_REGISTRY[_z_sb]
                                _sb_pfn = _sb_def.get("paint_fn", paint_none)
                                if _sb_pfn is not paint_none:
                                    paint_overlay = _sb_pfn(paint_overlay, shape, hard_mask, seed + i * 13 + 7777, 1.0, 1.0)
                                # Apply user's overlay color after paint_fn so the chosen tint is always visible (Fix 2)
                                paint_overlay[:, :, :3] *= np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                    _sb_ns = int(zone.get("second_base_noise_scale", 24))
                    _sb_bm = zone.get("second_base_blend_mode", "noise")
                    _sb_bm_norm = _normalize_second_base_blend_mode(_sb_bm)
                    if _sb_bm_norm in ("pattern", "pattern_vivid", "tint"):
                        _blend_w = _get_pattern_mask(_pat_id, shape, hard_mask, seed + i * 13, 1.0, scale=_sb_pat_scale, rotation=_sb_pat_rot, opacity=_sb_pat_op, strength=_sb_pat_str, offset_x=_sb_pat_ox, offset_y=_sb_pat_oy) if _pat_id else None
                        if _blend_w is None:
                            _blend_w = np.full(shape, _sb_strength, dtype=np.float32)
                        else:
                            if zone.get("second_base_pattern_invert"):
                                _blend_w = 1.0 - _blend_w
                            if zone.get("second_base_pattern_harden"):
                                _blend_w = np.clip((_blend_w.astype(np.float32) - 0.45) / 0.15, 0, 1)
                            if _sb_bm_norm == "pattern_vivid":
                                _thr = np.clip(1.0 - float(_sb_strength), 0.0, 1.0)
                                _blend_w = np.clip((_blend_w - _thr) / max(0.08, 1e-4), 0.0, 1.0).astype(np.float32)
                            elif _sb_bm_norm == "tint":
                                _blend_w = np.clip(_blend_w * _sb_strength * 0.35, 0, 1).astype(np.float32)
                            else:
                                _blend_w = _blend_w * _sb_strength
                    elif _sb_bm_norm == "noise":
                        _nz = multi_scale_noise(shape, [_sb_ns, _sb_ns * 2, _sb_ns * 4], [0.5, 0.3, 0.2], seed + 1234)
                        _blend_w = np.clip(_nz, 0, 1).astype(np.float32)
                    else:
                        _blend_w = np.ones(shape, dtype=np.float32)
                    _blend_w = _blend_w * hard_mask
                    # Pattern-Pop / Tint: alpha already scaled in _blend_w; use 1.0 for pattern/tint/pop
                    _mul = 1.0 if _sb_bm_norm in ("pattern", "pattern_vivid", "tint") else _sb_strength
                    _blend_w3d = (_blend_w * _mul)[:, :, np.newaxis]
                    # Use overlay RGB only so 3-channel paint never shape-mismatches (overlay may be 4-ch from paint_fn)
                    paint[:, :, :3] = paint[:, :, :3] * (1.0 - _blend_w3d) + paint_overlay[:, :, :3] * _blend_w3d
                except Exception as _e:
                    import traceback
                    print(f"    [{name}] 2nd base overlay ERROR: {_e}")
                    traceback.print_exc()

        elif finish_name and finish_name in FINISH_REGISTRY:
            _engine_rot_debug(f"  [{name}] -> PATH 3 (legacy): finish={finish_name}")
            # PATH 3: LEGACY - backward compat with original FINISH_REGISTRY
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            print(f"    [{name}] => {finish_name} ({intensity}) [legacy]")
            zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
            paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)

        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK - client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            _engine_rot_debug(f"  [{name}] -> PATH 4 (generic fallback): finish={finish_name}, rotation={zone_rotation}, fc_keys={list(zone.get('finish_colors',{}).keys())}")
            print(f"    [DEBUG-ROT] PATH4: finish={finish_name}, zone.rotation={zone.get('rotation')}, parsed={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        else:
            label = finish_name or base_id or "???"
            _engine_rot_debug(f"  [{name}] -> NO PATH MATCHED! finish={finish_name}, base={base_id}, has_fc={zone.get('finish_colors') is not None}")
            print(f"    WARNING: Unknown finish/base '{label}', skipping")
            continue

        # Apply zone spec with hard ownership: where mask is strong, fully replace
        # Vectorized across all 4 channels at once for speed
        mask3d = zone_mask[:,:,np.newaxis]  # (h, w, 1)
        strong = mask3d > 0.5
        soft = (mask3d > 0.05) & ~strong
        blended = np.clip(
            zone_spec.astype(np.float32) * mask3d +
            combined_spec.astype(np.float32) * (1 - mask3d),
            0, 255
        ).astype(np.uint8)
        combined_spec = np.where(strong, zone_spec, np.where(soft, blended, combined_spec))

        if os.environ.get("SHOKKER_TIMING") == "1":
            print(f"      [{name}] zone time: {time.time()-t_zone:.2f}s")

    # ---- Per-zone wear: BATCHED (single apply_wear call for ALL zones) ----
    # Instead of N separate apply_wear calls (each 5-8s), compute once at max level
    # then blend proportionally per zone.
    wear_zones = [(i, zone, zone_masks[i], int(zone.get("wear_level", 0)))
                  for i, zone in enumerate(zones)
                  if int(zone.get("wear_level", 0)) > 0 and np.max(zone_masks[i]) > 0.01]
    if wear_zones:
        max_wear = max(wl for _, _, _, wl in wear_zones)
        print(f"\n  Batched per-zone wear: {len(wear_zones)} zones, max wear={max_wear}%")
        t_wear = time.time()
        worn_spec, worn_paint = apply_wear(
            combined_spec.copy(), (np.clip(paint, 0, 1) * 255).astype(np.uint8),
            max_wear, seed + 777
        )
        # Blend worn results per zone, scaled by each zone's wear fraction
        for zi, zone, zm, wl in wear_zones:
            wear_frac = wl / max_wear  # 0.0-1.0 how much of the max wear this zone gets
            mask_bool = zm > 0.5
            mask3d = mask_bool[:,:,np.newaxis]
            # Interpolate between unworn and worn based on wear fraction
            if wear_frac >= 0.99:
                # Full strength - just swap
                combined_spec = np.where(mask3d, worn_spec, combined_spec)
                paint = np.where(mask3d, worn_paint.astype(np.float32) / 255.0, paint)
            else:
                # Partial strength - lerp between original and worn
                spec_lerp = np.clip(
                    combined_spec.astype(np.float32) * (1 - wear_frac) +
                    worn_spec.astype(np.float32) * wear_frac, 0, 255
                ).astype(np.uint8)
                paint_lerp = np.clip(
                    paint * (1 - wear_frac) +
                    worn_paint.astype(np.float32) / 255.0 * wear_frac, 0, 1
                )
                combined_spec = np.where(mask3d, spec_lerp, combined_spec)
                paint = np.where(mask3d, paint_lerp, paint)
            print(f"    Zone {zi+1} [{zone['name']}]: wear {wl}% (frac={wear_frac:.2f})")
        print(f"  Batched wear applied in {time.time()-t_wear:.2f}s")

    print(f"  All finishes applied: {time.time()-t_finishes:.2f}s")

    # ---- SPEC STAMPS: Apply stamp overlays on top of ALL zones ----
    if stamp_image and os.path.exists(stamp_image):
        print(f"\n  Applying spec stamp: {os.path.basename(stamp_image)} (finish={stamp_spec_finish})")
        t_stamp = time.time()
        try:
            stamp_img = Image.open(stamp_image).convert('RGBA')
            if stamp_img.size != (w, h):
                stamp_img = stamp_img.resize((w, h), Image.LANCZOS)
            stamp_arr = np.array(stamp_img)
            stamp_alpha = stamp_arr[:, :, 3].astype(np.float32) / 255.0  # 0-1 mask
            stamp_rgb = stamp_arr[:, :, :3].astype(np.float32) / 255.0

            # Only process if stamp has any non-transparent pixels
            if np.max(stamp_alpha) > 0.01:
                # Generate spec for stamped area using chosen finish
                from engine.spec_paint import (spec_gloss, spec_matte, spec_satin,
                    spec_metallic, spec_pearl, spec_chrome, spec_satin_metal)
                STAMP_SPEC_MAP = {
                    "gloss": spec_gloss,
                    "matte": spec_matte,
                    "satin": spec_satin,
                    "metallic": spec_metallic,
                    "pearl": spec_pearl,
                    "chrome": spec_chrome,
                    "satin_metal": spec_satin_metal,
                }
                spec_fn = STAMP_SPEC_MAP.get(stamp_spec_finish, spec_gloss)
                stamp_spec = spec_fn((h, w), stamp_alpha, seed + 9999, 1.0)

                # Blend stamp onto paint (RGB channels only)
                alpha3 = stamp_alpha[:, :, np.newaxis]
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - alpha3) + stamp_rgb * alpha3
                if paint.shape[2] > 3:
                    paint[:, :, 3] = np.maximum(paint[:, :, 3], stamp_alpha)

                # Blend stamp spec onto combined_spec (all 4 channels)
                alpha4 = stamp_alpha[:, :, np.newaxis]
                combined_spec = (
                    combined_spec.astype(np.float32) * (1.0 - alpha4) +
                    stamp_spec.astype(np.float32) * alpha4
                ).astype(np.uint8)

                stamp_px = np.sum(stamp_alpha > 0.01)
                print(f"  Stamp applied: {stamp_px:,} pixels affected, finish={stamp_spec_finish}")
            else:
                print(f"  Stamp skipped: no visible pixels")
        except Exception as e:
            print(f"  Stamp ERROR: {e}")
        print(f"  Stamp time: {time.time()-t_stamp:.2f}s")

    # Convert paint to uint8
    t_save = time.time()
    paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    if paint_rgb.shape[2] == 4:
        paint_rgb = paint_rgb[:, :, :3]

    # ---- PREVIEW MODE: return arrays directly, skip all file I/O ----
    if preview_mode:
        return (paint_rgb, combined_spec)

    # Save outputs - car_prefix is "car_num" (custom numbers) or "car" (no custom numbers)
    # Spec map is ALWAYS car_spec regardless of custom number setting
    paint_path = os.path.join(output_dir, f"{car_prefix}_{iracing_id}.tga")
    spec_path = os.path.join(output_dir, f"car_spec_{iracing_id}.tga")

    write_tga_24bit(paint_path, paint_rgb)
    write_tga_32bit(spec_path, combined_spec)

    # Save previews
    Image.fromarray(paint_rgb).save(os.path.join(output_dir, "PREVIEW_paint.png"))
    Image.fromarray(combined_spec).save(os.path.join(output_dir, "PREVIEW_spec.png"))

    # Save individual zone mask previews (only when debug images requested)
    if save_debug_images:
        for i, (zone, mask) in enumerate(zip(zones, zone_masks)):
            mask_img = (mask * 255).astype(np.uint8)
            Image.fromarray(mask_img).save(
                os.path.join(output_dir, f"PREVIEW_zone{i+1}_{zone['name'].replace(' ', '_').replace('/', '_')}.png")
            )

        # Save combined zone map (color-coded)
        zone_map = np.zeros((h, w, 3), dtype=np.uint8)
        zone_colors = [
            [255, 50, 50],   # Red
            [50, 255, 50],   # Green
            [50, 100, 255],  # Blue
            [255, 255, 50],  # Yellow
            [255, 50, 255],  # Magenta
            [50, 255, 255],  # Cyan
            [255, 150, 50],  # Orange
            [150, 50, 255],  # Purple
        ]
        for i, mask in enumerate(zone_masks):
            color = zone_colors[i % len(zone_colors)]
            for c in range(3):
                zone_map[:,:,c] = np.clip(
                    zone_map[:,:,c] + (mask * color[c]).astype(np.uint8),
                    0, 255
                ).astype(np.uint8)
        Image.fromarray(zone_map).save(os.path.join(output_dir, "PREVIEW_zone_map.png"))

    print(f"  File I/O + previews: {time.time()-t_save:.2f}s")

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  DONE in {elapsed:.1f}s!")
    print(f"  Paint: {paint_path}")
    print(f"  Spec:  {spec_path}")
    if save_debug_images:
        print(f"  Zone previews saved for debugging")
    print(f"{'=' * 60}")

    return paint_rgb, combined_spec, zone_masks


# ================================================================
# LIVE PREVIEW - Low-res fast render (no file I/O)
# ================================================================

def preview_render(paint_file, zones, seed=51, preview_scale=0.25, import_spec_map=None):
    """Live preview: runs the FULL render pipeline at reduced resolution.

    Uses build_multi_zone with preview_mode=True so the preview matches
    the actual render output exactly (all features: HSB, overlays, patterns,
    blend modes, color sources, etc.).

    Returns:
        (paint_rgb_uint8, combined_spec_uint8, elapsed_ms)
    """
    import time as _time
    import tempfile
    t0 = _time.time()

    # Downscale paint for speed
    scheme_img = Image.open(paint_file).convert('RGB')
    orig_w, orig_h = scheme_img.size
    preview_w = max(16, int(orig_w * preview_scale))
    preview_h = max(16, int(orig_h * preview_scale))
    scheme_img = scheme_img.resize((preview_w, preview_h), Image.LANCZOS)

    # Save to temp file (build_multi_zone expects a file path)
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    tmp_path = tmp.name
    tmp.close()
    scheme_img.save(tmp_path)

    # Downscale import spec map if provided
    preview_spec = None
    if import_spec_map and os.path.exists(import_spec_map):
        try:
            spec_img = Image.open(import_spec_map).convert('RGBA')
            spec_img = spec_img.resize((preview_w, preview_h), Image.LANCZOS)
            tmp_spec = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            preview_spec = tmp_spec.name
            tmp_spec.close()
            spec_img.save(preview_spec)
        except Exception:
            preview_spec = import_spec_map

    # Resize any region_mask / spatial_mask in zones to preview res
    for z in zones:
        if "region_mask" in z and z["region_mask"] is not None:
            rm = z["region_mask"]
            if isinstance(rm, np.ndarray) and (rm.shape[0] != preview_h or rm.shape[1] != preview_w):
                rm_img = Image.fromarray((rm * 255).astype(np.uint8) if rm.max() <= 1.0 else rm.astype(np.uint8))
                rm_img = rm_img.resize((preview_w, preview_h), Image.NEAREST)
                z["region_mask"] = np.array(rm_img).astype(np.float32) / 255.0
        if "spatial_mask" in z and z["spatial_mask"] is not None:
            sm = z["spatial_mask"]
            if isinstance(sm, np.ndarray) and (sm.shape[0] != preview_h or sm.shape[1] != preview_w):
                sm_img = Image.fromarray(sm.astype(np.uint8))
                sm_img = sm_img.resize((preview_w, preview_h), Image.NEAREST)
                z["spatial_mask"] = np.array(sm_img).astype(np.uint8)

    try:
        result = build_multi_zone(
            paint_file=tmp_path,
            output_dir=None,
            zones=zones,
            iracing_id="preview",
            seed=seed,
            import_spec_map=preview_spec or import_spec_map,
            preview_mode=True,
        )
        paint_rgb, combined_spec = result
    except Exception as e:
        print(f"  [preview_render] WARNING: render failed, returning blank: {e}")
        import traceback
        traceback.print_exc()
        paint_rgb = np.full((preview_h, preview_w, 3), 128, dtype=np.uint8)
        combined_spec = np.zeros((preview_h, preview_w, 4), dtype=np.uint8)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        if preview_spec and preview_spec != import_spec_map:
            try:
                os.unlink(preview_spec)
            except Exception:
                pass

    elapsed_ms = int((_time.time() - t0) * 1000)
    print(f"  [preview_render] {preview_w}x{preview_h} ({len(zones)} zones) in {elapsed_ms}ms")

    return paint_rgb, combined_spec, elapsed_ms


# ================================================================
# CONVENIENCE: Apply single finish to whole car (backward compat)
# ================================================================

def apply_single_finish(paint_file, finish_name, output_dir, iracing_id="23371",
                        seed=51, intensity="100"):
    """Apply one finish to the whole car (backward compatible)."""
    zones = [{
        "name": "Whole Car",
        "color": "everything",
        "finish": finish_name,
        "intensity": intensity,
    }]
    return build_multi_zone(paint_file, output_dir, zones, iracing_id, seed)


def apply_composed_finish(paint_file, base, pattern, output_dir, iracing_id="23371",
                          seed=51, intensity="100"):
    """Apply a composed base+pattern finish to the whole car (v3.0)."""
    zones = [{
        "name": "Whole Car",
        "color": "everything",
        "base": base,
        "pattern": pattern or "none",
        "intensity": intensity,
    }]
    return build_multi_zone(paint_file, output_dir, zones, iracing_id, seed)


# ================================================================
# SHARED HELPERS (extracted for reuse in helmet/suit/wear)
# ================================================================

def _parse_intensity(intensity):
    """Parse intensity string to (spec_mult, paint_mult, bright_boost).
    Accepts any integer 0-100 (not just multiples of 10) via linear interpolation.
    Applies channel-specific scaling so 100% = 1.0 maps to correct internal multiplier."""
    # Fast path: exact match in table (multiples of 10)
    if intensity in INTENSITY:
        preset = INTENSITY[intensity]
    else:
        # Parse as numeric - support any 0-100 value the slider sends
        try:
            pct = max(0.0, min(100.0, float(intensity))) / 100.0
        except (TypeError, ValueError):
            pct = 1.0  # unknown string → full intensity
        preset = {"paint": pct, "spec": pct, "bright": pct}
    return (preset["spec"]  * _INTENSITY_SCALE["spec"],
            preset["paint"] * _INTENSITY_SCALE["paint"],
            preset["bright"] * _INTENSITY_SCALE["bright"])


def _build_color_mask(paint_rgb, zone, shape):
    """Build a zone mask from color description. Simplified version for helmet/suit.

    Uses the same color matching as build_multi_zone but without
    the full claimed/remainder tracking (caller handles that).
    """
    color_desc = zone.get("color", "everything")
    h, w = shape
    scheme = paint_rgb.astype(np.float32) / 255.0 if paint_rgb.max() > 1 else paint_rgb

    # Analyze colors
    stats = analyze_paint_colors(scheme)

    if isinstance(color_desc, list):
        # Multi-color zone: union of multiple selectors
        union_mask = np.zeros((h, w), dtype=np.float32)
        for sub_desc in color_desc:
            if isinstance(sub_desc, dict):
                sub_selector = sub_desc
            else:
                sub_selector = parse_color_description(str(sub_desc))
            sub_mask = build_zone_mask(scheme, stats, sub_selector, blur_radius=3)
            union_mask = np.maximum(union_mask, sub_mask)
        mask = union_mask
    elif isinstance(color_desc, dict):
        selector = color_desc
        if selector.get("remainder"):
            # Remainder zone - return full mask (caller clips with claimed)
            return np.ones((h, w), dtype=np.float32)
        mask = build_zone_mask(scheme, stats, selector, blur_radius=3)
    else:
        selector = parse_color_description(str(color_desc))
        if selector.get("remainder"):
            return np.ones((h, w), dtype=np.float32)
        mask = build_zone_mask(scheme, stats, selector, blur_radius=3)

    # Harden soft masks
    HARD_THRESHOLD = 0.15
    mask = np.where(mask > HARD_THRESHOLD, 1.0, mask / HARD_THRESHOLD * mask).astype(np.float32)
    return mask


# ================================================================
# HELMET & SUIT SPEC MAP GENERATOR
# ================================================================

def build_helmet_spec(helmet_paint_file, output_dir, zones, iracing_id="23371", seed=51):
    """Generate a spec map for an iRacing helmet paint file.

    Helmet paints are typically 512x512 or 1024x1024 24-bit TGA.
    Uses the same zone/finish system as cars - color-match zones on the
    helmet paint and apply finishes to generate helmet_spec_<id>.tga.

    The helmet UV layout has the crown on top, visor in the middle,
    chin bar at bottom. Colors match just like car paints.
    """
    print(f"\n{'='*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO - Helmet Spec Generator")
    print(f"  ID: {iracing_id}")
    print(f"{'='*60}")
    start_time = time.time()

    # Load helmet paint (24-bit or 32-bit TGA)
    img = Image.open(helmet_paint_file)
    if img.mode == 'RGBA':
        paint_rgb = np.array(img)[:,:,:3]
    else:
        paint_rgb = np.array(img)
    h, w = paint_rgb.shape[:2]
    print(f"  Helmet: {w}x{h}")

    shape = (h, w)
    paint = paint_rgb.astype(np.float32) / 255.0

    # Build spec using same zone logic as cars
    combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
    combined_spec[:,:,1] = 100  # default R
    combined_spec[:,:,3] = 255  # full spec mask

    claimed = np.zeros(shape, dtype=np.float32)

    for i, zone in enumerate(zones):
        name = zone.get("name", f"Zone {i+1}")
        intensity = zone.get("intensity", "100")
        sm, pm, bb = _parse_intensity(intensity)

        zone_mask = _build_color_mask(paint_rgb, zone, shape)
        zone_mask = np.clip(zone_mask - claimed * 0.8, 0, 1).astype(np.float32)

        if zone_mask.max() < 0.01:
            print(f"    [{name}] => no pixels matched, skipping")
            continue

        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")

        if base_id:
            if base_id not in BASE_REGISTRY:
                continue
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) if _z_cc is not None else None
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            _v6kw["base_strength"] = float(zone.get("base_strength", 1.0))
            _v6kw["base_spec_strength"] = float(zone.get("base_spec_strength", 1.0))
            _v6kw["base_spec_blend_mode"] = zone.get("base_spec_blend_mode", "normal")
            _v6kw["base_color_mode"] = zone.get("base_color_mode", "source")
            _v6kw["base_color"] = zone.get("base_color", [1.0, 1.0, 1.0])
            _v6kw["base_color_source"] = zone.get("base_color_source")
            _v6kw["base_color_strength"] = float(zone.get("base_color_strength", 1.0))
            _v6kw["base_hue_offset"] = float(zone.get("base_hue_offset", 0))
            _v6kw["base_saturation_adjust"] = float(zone.get("base_saturation_adjust", 0))
            _v6kw["base_brightness_adjust"] = float(zone.get("base_brightness_adjust", 0))
            _v6kw["pattern_opacity"] = float(zone.get("pattern_opacity", 1.0))
            _v6kw["pattern_offset_x"] = max(0.0, min(1.0, float(zone.get("pattern_offset_x", 0.5))))
            _v6kw["pattern_offset_y"] = max(0.0, min(1.0, float(zone.get("pattern_offset_y", 0.5))))
            _v6kw["pattern_flip_h"] = bool(zone.get("pattern_flip_h", False))
            _v6kw["pattern_flip_v"] = bool(zone.get("pattern_flip_v", False))
            _v6kw["base_offset_x"] = max(0.0, min(1.0, float(zone.get("base_offset_x", 0.5))))
            _v6kw["base_offset_y"] = max(0.0, min(1.0, float(zone.get("base_offset_y", 0.5))))
            _v6kw["base_rotation"] = float(zone.get("base_rotation", 0))
            _v6kw["base_flip_h"] = bool(zone.get("base_flip_h", False))
            _v6kw["base_flip_v"] = bool(zone.get("base_flip_v", False))
            if zone.get("spec_pattern_stack"): _v6kw["spec_pattern_stack"] = zone["spec_pattern_stack"]
            if zone.get("overlay_spec_pattern_stack"): _v6kw["overlay_spec_pattern_stack"] = zone["overlay_spec_pattern_stack"]
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc
            # Dual Layer Base Overlay
            _z_sb = zone.get("second_base")
            if _z_sb:
                _v6kw["second_base"] = _z_sb
                _v6kw["second_base_color"] = zone.get("second_base_color", [1.0, 1.0, 1.0])
                _v6kw["second_base_strength"] = float(zone.get("second_base_strength", 0.0))
                _v6kw["second_base_spec_strength"] = float(zone.get("second_base_spec_strength", 1.0))
                _v6kw["second_base_blend_mode"] = zone.get("second_base_blend_mode", "noise")
                _v6kw["second_base_noise_scale"] = int(zone.get("second_base_noise_scale", 24))
                _v6kw["second_base_scale"] = float(zone.get("second_base_scale", 1.0))
                _v6kw["second_base_pattern"] = zone.get("second_base_pattern")
                _v6kw["second_base_pattern_scale"] = float(zone.get("second_base_pattern_scale", 1.0))
                _v6kw["second_base_pattern_rotation"] = float(zone.get("second_base_pattern_rotation", 0.0))
                _v6kw["second_base_pattern_opacity"] = float(zone.get("second_base_pattern_opacity", 1.0))
                _v6kw["second_base_pattern_strength"] = float(zone.get("second_base_pattern_strength", 1.0))
                _v6kw["second_base_pattern_invert"] = bool(zone.get("second_base_pattern_invert", False))
                _v6kw["second_base_pattern_harden"] = bool(zone.get("second_base_pattern_harden", False))
                _sb_oxN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                _sb_oyN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                _sb_pscaleN = _v6kw["second_base_pattern_scale"]
                # Fit-to-Zone for 2nd base overlay
                if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _sb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _sb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _sb_pscaleN = _sb_pscaleN / _ft_ratio
                _v6kw["second_base_pattern_offset_x"] = _sb_oxN
                _v6kw["second_base_pattern_offset_y"] = _sb_oyN
                _v6kw["second_base_pattern_scale"] = _sb_pscaleN
            _v6kw["second_base_color_source"] = zone.get("second_base_color_source")
            _z_tb = zone.get("third_base")
            if _z_tb:
                _v6kw["third_base"] = _z_tb
                _v6kw["third_base_color"] = zone.get("third_base_color", [1.0, 1.0, 1.0])
                _v6kw["third_base_strength"] = float(zone.get("third_base_strength", 0.0))
                _v6kw["third_base_spec_strength"] = float(zone.get("third_base_spec_strength", 1.0))
                _v6kw["third_base_blend_mode"] = zone.get("third_base_blend_mode", "noise")
                _v6kw["third_base_noise_scale"] = int(zone.get("third_base_noise_scale", 24))
                _v6kw["third_base_scale"] = float(zone.get("third_base_scale", 1.0))
                _v6kw["third_base_pattern"] = zone.get("third_base_pattern")
                _v6kw["third_base_pattern_scale"] = float(zone.get("third_base_pattern_scale", 1.0))
                _v6kw["third_base_pattern_rotation"] = float(zone.get("third_base_pattern_rotation", 0.0))
                _v6kw["third_base_pattern_opacity"] = float(zone.get("third_base_pattern_opacity", 1.0))
                _v6kw["third_base_pattern_strength"] = float(zone.get("third_base_pattern_strength", 1.0))
                _v6kw["third_base_pattern_invert"] = bool(zone.get("third_base_pattern_invert", False))
                _v6kw["third_base_pattern_harden"] = bool(zone.get("third_base_pattern_harden", False))
                _tb_oxN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_x", 0.5))))
                _tb_oyN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_y", 0.5))))
                _tb_pscaleN = _v6kw["third_base_pattern_scale"]
                # Fit-to-Zone for 3rd base overlay
                if zone.get("third_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _tb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _tb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _tb_pscaleN = _tb_pscaleN / _ft_ratio
                _v6kw["third_base_pattern_offset_x"] = _tb_oxN
                _v6kw["third_base_pattern_offset_y"] = _tb_oyN
                _v6kw["third_base_pattern_scale"] = _tb_pscaleN
            _v6kw["third_base_color_source"] = zone.get("third_base_color_source")
            _z_fb = zone.get("fourth_base")
            if _z_fb:
                _v6kw["fourth_base"] = _z_fb
                _v6kw["fourth_base_color"] = zone.get("fourth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fourth_base_strength"] = float(zone.get("fourth_base_strength", 0.0))
                _v6kw["fourth_base_spec_strength"] = float(zone.get("fourth_base_spec_strength", 1.0))
                _v6kw["fourth_base_blend_mode"] = zone.get("fourth_base_blend_mode", "noise")
                _v6kw["fourth_base_noise_scale"] = int(zone.get("fourth_base_noise_scale", 24))
                _v6kw["fourth_base_scale"] = float(zone.get("fourth_base_scale", 1.0))
                _v6kw["fourth_base_pattern"] = zone.get("fourth_base_pattern")
                _v6kw["fourth_base_pattern_scale"] = float(zone.get("fourth_base_pattern_scale", 1.0))
                _v6kw["fourth_base_pattern_rotation"] = float(zone.get("fourth_base_pattern_rotation", 0.0))
                _v6kw["fourth_base_pattern_opacity"] = float(zone.get("fourth_base_pattern_opacity", 1.0))
                _v6kw["fourth_base_pattern_strength"] = float(zone.get("fourth_base_pattern_strength", 1.0))
                _v6kw["fourth_base_pattern_invert"] = bool(zone.get("fourth_base_pattern_invert", False))
                _v6kw["fourth_base_pattern_harden"] = bool(zone.get("fourth_base_pattern_harden", False))
                _fb_oxN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_x", 0.5))))
                _fb_oyN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_y", 0.5))))
                _fb_pscaleN = _v6kw["fourth_base_pattern_scale"]
                # Fit-to-Zone for 4th base overlay
                if zone.get("fourth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fb_pscaleN = _fb_pscaleN / _ft_ratio
                _v6kw["fourth_base_pattern_offset_x"] = _fb_oxN
                _v6kw["fourth_base_pattern_offset_y"] = _fb_oyN
                _v6kw["fourth_base_pattern_scale"] = _fb_pscaleN
            _v6kw["fourth_base_color_source"] = zone.get("fourth_base_color_source")
            _z_fif = zone.get("fifth_base")
            if _z_fif:
                _v6kw["fifth_base"] = _z_fif
                _v6kw["fifth_base_color"] = zone.get("fifth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fifth_base_strength"] = float(zone.get("fifth_base_strength", 0.0))
                _v6kw["fifth_base_spec_strength"] = float(zone.get("fifth_base_spec_strength", 1.0))
                _v6kw["fifth_base_blend_mode"] = zone.get("fifth_base_blend_mode", "noise")
                _v6kw["fifth_base_noise_scale"] = int(zone.get("fifth_base_noise_scale", 24))
                _v6kw["fifth_base_scale"] = float(zone.get("fifth_base_scale", 1.0))
                _v6kw["fifth_base_pattern"] = zone.get("fifth_base_pattern")
                _v6kw["fifth_base_pattern_scale"] = float(zone.get("fifth_base_pattern_scale", 1.0))
                _v6kw["fifth_base_pattern_rotation"] = float(zone.get("fifth_base_pattern_rotation", 0.0))
                _v6kw["fifth_base_pattern_opacity"] = float(zone.get("fifth_base_pattern_opacity", 1.0))
                _v6kw["fifth_base_pattern_strength"] = float(zone.get("fifth_base_pattern_strength", 1.0))
                _v6kw["fifth_base_pattern_invert"] = bool(zone.get("fifth_base_pattern_invert", False))
                _v6kw["fifth_base_pattern_harden"] = bool(zone.get("fifth_base_pattern_harden", False))
                _fif_oxN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_x", 0.5))))
                _fif_oyN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_y", 0.5))))
                _fif_pscaleN = _v6kw["fifth_base_pattern_scale"]
                # Fit-to-Zone for 5th base overlay
                if zone.get("fifth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fif_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fif_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fif_pscaleN = _fif_pscaleN / _ft_ratio
                _v6kw["fifth_base_pattern_offset_x"] = _fif_oxN
                _v6kw["fifth_base_pattern_offset_y"] = _fif_oyN
                _v6kw["fifth_base_pattern_scale"] = _fif_pscaleN
            _v6kw["fifth_base_color_source"] = zone.get("fifth_base_color_source")
            _v6kw["monolithic_registry"] = MONOLITHIC_REGISTRY

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                stack_ids = {ps.get("id") for ps in pattern_stack[:3] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation})
                for ps in pattern_stack[:3]:  # Max 3 additional
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                            "blend_mode": ps.get("blend_mode", "normal"),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%{"["+p.get("blend_mode","normal")+"]" if p.get("blend_mode","normal") != "normal" else ""}' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                print(f"    [{name}] => {label} ({intensity}) [stacked compositing]")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                if all_patterns:
                    zone_spec = compose_finish_stacked(base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                else:
                    zone_spec = compose_finish(base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod(base_id, "none", paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.1f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                zone_spec = compose_finish(base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation, **_v6paint)
        elif finish_name and zone.get("finish_colors") and (
            finish_name.startswith("grad_") or finish_name.startswith("gradm_")
            or finish_name.startswith("grad3_") or finish_name.startswith("ghostg_")
            or finish_name.startswith("mc_")
        ):
            zone_rotation = float(zone.get("rotation", 0))
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}) [monolithic]")

            _mono_base_strength = max(0.0, min(2.0, float(zone.get("base_strength", 1.0))))
            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                # Use FULL mask for tile generation - monolithic covers entire tile.
                # Original zone_mask handles final clipping. This prevents existing
                # car art (numbers, sponsors, decals) from leaking into tiled output.
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                tile_spec = spec_fn(tile_shape, tile_mask, seed + i * 13, sm * _mono_base_strength)
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                # For paint: run paint_fn on ORIGINAL paint at full resolution.
                # Scaling only affects the spec map (material properties), NOT the paint.
                # Previous approach created a blank canvas which destroyed the car livery.
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm * _mono_base_strength, bb * _mono_base_strength)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm * _mono_base_strength)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm * _mono_base_strength, bb * _mono_base_strength)

            # Apply HSB adjustments to monolithic paint (same as base+pattern path)
            _mono_hue = float(zone.get("base_hue_offset", 0))
            _mono_sat = float(zone.get("base_saturation_adjust", 0))
            _mono_bri = float(zone.get("base_brightness_adjust", 0))
            if abs(_mono_hue) >= 0.5 or abs(_mono_sat) >= 0.5 or abs(_mono_bri) >= 0.5:
                paint = _apply_hsb_adjustments(paint, zone_mask, _mono_hue, _mono_sat, _mono_bri)

            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in FINISH_REGISTRY:
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            print(f"    [{name}] => {finish_name} ({intensity}) [legacy]")
            zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
            paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK - client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            print(f"    [DEBUG-ROT] PATH4: finish={finish_name}, zone.rotation={zone.get('rotation')}, parsed={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        else:
            continue

        claimed = np.clip(claimed + zone_mask, 0, 1)
        mask3d = zone_mask[:,:,np.newaxis]
        soft = mask3d > 0.05
        blended = np.clip(
            zone_spec.astype(np.float32) * mask3d +
            combined_spec.astype(np.float32) * (1 - mask3d),
            0, 255
        ).astype(np.uint8)
        combined_spec = np.where(soft, blended, combined_spec)

    # Save outputs
    os.makedirs(output_dir, exist_ok=True)
    spec_path = os.path.join(output_dir, f"helmet_spec_{iracing_id}.tga")
    write_tga_32bit(spec_path, combined_spec)
    Image.fromarray(combined_spec).save(os.path.join(output_dir, "PREVIEW_helmet_spec.png"))

    # Also save modified paint if it changed
    helmet_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    paint_path = os.path.join(output_dir, f"helmet_{iracing_id}.tga")
    write_tga_24bit(paint_path, helmet_paint)
    Image.fromarray(helmet_paint).save(os.path.join(output_dir, "PREVIEW_helmet_paint.png"))

    elapsed = time.time() - start_time
    print(f"\n  Helmet done in {elapsed:.1f}s!")
    print(f"  Spec:  {spec_path}")
    print(f"  Paint: {paint_path}")
    return helmet_paint, combined_spec


def build_suit_spec(suit_paint_file, output_dir, zones, iracing_id="23371", seed=51):
    """Generate a spec map for an iRacing suit (firesuit) paint file.

    Suit paints are typically 1024x1024 24-bit TGA.
    Layout: shirt (upper left/center), pants (lower center),
    gloves (lower left), shoes (lower left corner).

    Uses exact same zone/finish system as cars and helmets.
    """
    print(f"\n{'='*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO - Suit Spec Generator")
    print(f"  ID: {iracing_id}")
    print(f"{'='*60}")
    start_time = time.time()

    img = Image.open(suit_paint_file)
    if img.mode == 'RGBA':
        paint_rgb = np.array(img)[:,:,:3]
    else:
        paint_rgb = np.array(img)
    h, w = paint_rgb.shape[:2]
    print(f"  Suit: {w}x{h}")

    shape = (h, w)
    paint = paint_rgb.astype(np.float32) / 255.0

    combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
    combined_spec[:,:,1] = 100
    combined_spec[:,:,3] = 255
    claimed = np.zeros(shape, dtype=np.float32)

    for i, zone in enumerate(zones):
        name = zone.get("name", f"Zone {i+1}")
        intensity = zone.get("intensity", "100")
        sm, pm, bb = _parse_intensity(intensity)

        zone_mask = _build_color_mask(paint_rgb, zone, shape)
        zone_mask = np.clip(zone_mask - claimed * 0.8, 0, 1).astype(np.float32)

        if zone_mask.max() < 0.01:
            print(f"    [{name}] => no pixels matched, skipping")
            continue

        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")

        if base_id:
            if base_id not in BASE_REGISTRY:
                continue
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) if _z_cc is not None else None
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            _v6kw["base_strength"] = float(zone.get("base_strength", 1.0))
            _v6kw["base_spec_strength"] = float(zone.get("base_spec_strength", 1.0))
            _v6kw["base_spec_blend_mode"] = zone.get("base_spec_blend_mode", "normal")
            _v6kw["base_color_mode"] = zone.get("base_color_mode", "source")
            _v6kw["base_color"] = zone.get("base_color", [1.0, 1.0, 1.0])
            _v6kw["base_color_source"] = zone.get("base_color_source")
            _v6kw["base_color_strength"] = float(zone.get("base_color_strength", 1.0))
            _v6kw["base_hue_offset"] = float(zone.get("base_hue_offset", 0))
            _v6kw["base_saturation_adjust"] = float(zone.get("base_saturation_adjust", 0))
            _v6kw["base_brightness_adjust"] = float(zone.get("base_brightness_adjust", 0))
            _v6kw["pattern_opacity"] = float(zone.get("pattern_opacity", 1.0))
            _v6kw["pattern_offset_x"] = max(0.0, min(1.0, float(zone.get("pattern_offset_x", 0.5))))
            _v6kw["pattern_offset_y"] = max(0.0, min(1.0, float(zone.get("pattern_offset_y", 0.5))))
            _v6kw["pattern_flip_h"] = bool(zone.get("pattern_flip_h", False))
            _v6kw["pattern_flip_v"] = bool(zone.get("pattern_flip_v", False))
            _v6kw["base_offset_x"] = max(0.0, min(1.0, float(zone.get("base_offset_x", 0.5))))
            _v6kw["base_offset_y"] = max(0.0, min(1.0, float(zone.get("base_offset_y", 0.5))))
            _v6kw["base_rotation"] = float(zone.get("base_rotation", 0))
            _v6kw["base_flip_h"] = bool(zone.get("base_flip_h", False))
            _v6kw["base_flip_v"] = bool(zone.get("base_flip_v", False))
            if zone.get("spec_pattern_stack"): _v6kw["spec_pattern_stack"] = zone["spec_pattern_stack"]
            if zone.get("overlay_spec_pattern_stack"): _v6kw["overlay_spec_pattern_stack"] = zone["overlay_spec_pattern_stack"]
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc
            # Dual Layer Base Overlay
            _z_sb = zone.get("second_base")
            if _z_sb:
                _v6kw["second_base"] = _z_sb
                _v6kw["second_base_color"] = zone.get("second_base_color", [1.0, 1.0, 1.0])
                _v6kw["second_base_strength"] = float(zone.get("second_base_strength", 0.0))
                _v6kw["second_base_spec_strength"] = float(zone.get("second_base_spec_strength", 1.0))
                _v6kw["second_base_blend_mode"] = zone.get("second_base_blend_mode", "noise")
                _v6kw["second_base_noise_scale"] = int(zone.get("second_base_noise_scale", 24))
                _v6kw["second_base_scale"] = float(zone.get("second_base_scale", 1.0))
                _v6kw["second_base_pattern"] = zone.get("second_base_pattern")
                _v6kw["second_base_pattern_scale"] = float(zone.get("second_base_pattern_scale", 1.0))
                _v6kw["second_base_pattern_rotation"] = float(zone.get("second_base_pattern_rotation", 0.0))
                _v6kw["second_base_pattern_opacity"] = float(zone.get("second_base_pattern_opacity", 1.0))
                _v6kw["second_base_pattern_strength"] = float(zone.get("second_base_pattern_strength", 1.0))
                _v6kw["second_base_pattern_invert"] = bool(zone.get("second_base_pattern_invert", False))
                _v6kw["second_base_pattern_harden"] = bool(zone.get("second_base_pattern_harden", False))
                _sb_oxN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                _sb_oyN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                _sb_pscaleN = _v6kw["second_base_pattern_scale"]
                # Fit-to-Zone for 2nd base overlay
                if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _sb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _sb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _sb_pscaleN = _sb_pscaleN / _ft_ratio
                _v6kw["second_base_pattern_offset_x"] = _sb_oxN
                _v6kw["second_base_pattern_offset_y"] = _sb_oyN
                _v6kw["second_base_pattern_scale"] = _sb_pscaleN
            _v6kw["second_base_color_source"] = zone.get("second_base_color_source")
            _z_tb = zone.get("third_base")
            if _z_tb:
                _v6kw["third_base"] = _z_tb
                _v6kw["third_base_color"] = zone.get("third_base_color", [1.0, 1.0, 1.0])
                _v6kw["third_base_strength"] = float(zone.get("third_base_strength", 0.0))
                _v6kw["third_base_spec_strength"] = float(zone.get("third_base_spec_strength", 1.0))
                _v6kw["third_base_blend_mode"] = zone.get("third_base_blend_mode", "noise")
                _v6kw["third_base_noise_scale"] = int(zone.get("third_base_noise_scale", 24))
                _v6kw["third_base_scale"] = float(zone.get("third_base_scale", 1.0))
                _v6kw["third_base_pattern"] = zone.get("third_base_pattern")
                _v6kw["third_base_pattern_scale"] = float(zone.get("third_base_pattern_scale", 1.0))
                _v6kw["third_base_pattern_rotation"] = float(zone.get("third_base_pattern_rotation", 0.0))
                _v6kw["third_base_pattern_opacity"] = float(zone.get("third_base_pattern_opacity", 1.0))
                _v6kw["third_base_pattern_strength"] = float(zone.get("third_base_pattern_strength", 1.0))
                _v6kw["third_base_pattern_invert"] = bool(zone.get("third_base_pattern_invert", False))
                _v6kw["third_base_pattern_harden"] = bool(zone.get("third_base_pattern_harden", False))
                _tb_oxN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_x", 0.5))))
                _tb_oyN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_y", 0.5))))
                _tb_pscaleN = _v6kw["third_base_pattern_scale"]
                # Fit-to-Zone for 3rd base overlay
                if zone.get("third_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _tb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _tb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _tb_pscaleN = _tb_pscaleN / _ft_ratio
                _v6kw["third_base_pattern_offset_x"] = _tb_oxN
                _v6kw["third_base_pattern_offset_y"] = _tb_oyN
                _v6kw["third_base_pattern_scale"] = _tb_pscaleN
            _v6kw["third_base_color_source"] = zone.get("third_base_color_source")
            _z_fb = zone.get("fourth_base")
            if _z_fb:
                _v6kw["fourth_base"] = _z_fb
                _v6kw["fourth_base_color"] = zone.get("fourth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fourth_base_strength"] = float(zone.get("fourth_base_strength", 0.0))
                _v6kw["fourth_base_spec_strength"] = float(zone.get("fourth_base_spec_strength", 1.0))
                _v6kw["fourth_base_blend_mode"] = zone.get("fourth_base_blend_mode", "noise")
                _v6kw["fourth_base_noise_scale"] = int(zone.get("fourth_base_noise_scale", 24))
                _v6kw["fourth_base_scale"] = float(zone.get("fourth_base_scale", 1.0))
                _v6kw["fourth_base_pattern"] = zone.get("fourth_base_pattern")
                _v6kw["fourth_base_pattern_scale"] = float(zone.get("fourth_base_pattern_scale", 1.0))
                _v6kw["fourth_base_pattern_rotation"] = float(zone.get("fourth_base_pattern_rotation", 0.0))
                _v6kw["fourth_base_pattern_opacity"] = float(zone.get("fourth_base_pattern_opacity", 1.0))
                _v6kw["fourth_base_pattern_strength"] = float(zone.get("fourth_base_pattern_strength", 1.0))
                _v6kw["fourth_base_pattern_invert"] = bool(zone.get("fourth_base_pattern_invert", False))
                _v6kw["fourth_base_pattern_harden"] = bool(zone.get("fourth_base_pattern_harden", False))
                _fb_oxN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_x", 0.5))))
                _fb_oyN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_y", 0.5))))
                _fb_pscaleN = _v6kw["fourth_base_pattern_scale"]
                # Fit-to-Zone for 4th base overlay
                if zone.get("fourth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fb_pscaleN = _fb_pscaleN / _ft_ratio
                _v6kw["fourth_base_pattern_offset_x"] = _fb_oxN
                _v6kw["fourth_base_pattern_offset_y"] = _fb_oyN
                _v6kw["fourth_base_pattern_scale"] = _fb_pscaleN
            _v6kw["fourth_base_color_source"] = zone.get("fourth_base_color_source")
            _z_fif = zone.get("fifth_base")
            if _z_fif:
                _v6kw["fifth_base"] = _z_fif
                _v6kw["fifth_base_color"] = zone.get("fifth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fifth_base_strength"] = float(zone.get("fifth_base_strength", 0.0))
                _v6kw["fifth_base_spec_strength"] = float(zone.get("fifth_base_spec_strength", 1.0))
                _v6kw["fifth_base_blend_mode"] = zone.get("fifth_base_blend_mode", "noise")
                _v6kw["fifth_base_noise_scale"] = int(zone.get("fifth_base_noise_scale", 24))
                _v6kw["fifth_base_scale"] = float(zone.get("fifth_base_scale", 1.0))
                _v6kw["fifth_base_pattern"] = zone.get("fifth_base_pattern")
                _v6kw["fifth_base_pattern_scale"] = float(zone.get("fifth_base_pattern_scale", 1.0))
                _v6kw["fifth_base_pattern_rotation"] = float(zone.get("fifth_base_pattern_rotation", 0.0))
                _v6kw["fifth_base_pattern_opacity"] = float(zone.get("fifth_base_pattern_opacity", 1.0))
                _v6kw["fifth_base_pattern_strength"] = float(zone.get("fifth_base_pattern_strength", 1.0))
                _v6kw["fifth_base_pattern_invert"] = bool(zone.get("fifth_base_pattern_invert", False))
                _v6kw["fifth_base_pattern_harden"] = bool(zone.get("fifth_base_pattern_harden", False))
                _fif_oxN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_x", 0.5))))
                _fif_oyN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_y", 0.5))))
                _fif_pscaleN = _v6kw["fifth_base_pattern_scale"]
                # Fit-to-Zone for 5th base overlay
                if zone.get("fifth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fif_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fif_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fif_pscaleN = _fif_pscaleN / _ft_ratio
                _v6kw["fifth_base_pattern_offset_x"] = _fif_oxN
                _v6kw["fifth_base_pattern_offset_y"] = _fif_oyN
                _v6kw["fifth_base_pattern_scale"] = _fif_pscaleN
            _v6kw["fifth_base_color_source"] = zone.get("fifth_base_color_source")
            _v6kw["monolithic_registry"] = MONOLITHIC_REGISTRY

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                stack_ids = {ps.get("id") for ps in pattern_stack[:3] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation})
                for ps in pattern_stack[:3]:  # Max 3 additional
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                            "blend_mode": ps.get("blend_mode", "normal"),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%{"["+p.get("blend_mode","normal")+"]" if p.get("blend_mode","normal") != "normal" else ""}' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                print(f"    [{name}] => {label} ({intensity}) [stacked compositing]")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                if all_patterns:
                    zone_spec = compose_finish_stacked(base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                else:
                    zone_spec = compose_finish(base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod(base_id, "none", paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.1f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                zone_spec = compose_finish(base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation, **_v6paint)
        elif finish_name and zone.get("finish_colors") and (
            finish_name.startswith("grad_") or finish_name.startswith("gradm_")
            or finish_name.startswith("grad3_") or finish_name.startswith("ghostg_")
            or finish_name.startswith("mc_")
        ):
            zone_rotation = float(zone.get("rotation", 0))
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}) [monolithic]")

            _mono_base_strength = max(0.0, min(2.0, float(zone.get("base_strength", 1.0))))
            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                # Use FULL mask for tile generation - monolithic covers entire tile.
                # Original zone_mask handles final clipping. This prevents existing
                # car art (numbers, sponsors, decals) from leaking into tiled output.
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                tile_spec = spec_fn(tile_shape, tile_mask, seed + i * 13, sm * _mono_base_strength)
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                # For paint: run paint_fn on ORIGINAL paint at full resolution.
                # Scaling only affects the spec map (material properties), NOT the paint.
                # Previous approach created a blank canvas which destroyed the car livery.
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm * _mono_base_strength, bb * _mono_base_strength)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm * _mono_base_strength)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm * _mono_base_strength, bb * _mono_base_strength)

            # Apply HSB adjustments to monolithic paint (same as base+pattern path)
            _mono_hue = float(zone.get("base_hue_offset", 0))
            _mono_sat = float(zone.get("base_saturation_adjust", 0))
            _mono_bri = float(zone.get("base_brightness_adjust", 0))
            if abs(_mono_hue) >= 0.5 or abs(_mono_sat) >= 0.5 or abs(_mono_bri) >= 0.5:
                paint = _apply_hsb_adjustments(paint, zone_mask, _mono_hue, _mono_sat, _mono_bri)

            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in FINISH_REGISTRY:
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            print(f"    [{name}] => {finish_name} ({intensity}) [legacy]")
            zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
            paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK - client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            print(f"    [DEBUG-ROT] PATH4: finish={finish_name}, zone.rotation={zone.get('rotation')}, parsed={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        else:
            continue

        claimed = np.clip(claimed + zone_mask, 0, 1)
        mask3d = zone_mask[:,:,np.newaxis]
        soft = mask3d > 0.05
        blended = np.clip(
            zone_spec.astype(np.float32) * mask3d +
            combined_spec.astype(np.float32) * (1 - mask3d),
            0, 255
        ).astype(np.uint8)
        combined_spec = np.where(soft, blended, combined_spec)

    os.makedirs(output_dir, exist_ok=True)
    spec_path = os.path.join(output_dir, f"suit_spec_{iracing_id}.tga")
    write_tga_32bit(spec_path, combined_spec)
    Image.fromarray(combined_spec).save(os.path.join(output_dir, "PREVIEW_suit_spec.png"))

    suit_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    paint_path = os.path.join(output_dir, f"suit_{iracing_id}.tga")
    write_tga_24bit(paint_path, suit_paint)
    Image.fromarray(suit_paint).save(os.path.join(output_dir, "PREVIEW_suit_paint.png"))

    elapsed = time.time() - start_time
    print(f"\n  Suit done in {elapsed:.1f}s!")
    print(f"  Spec:  {spec_path}")
    print(f"  Paint: {paint_path}")
    return suit_paint, combined_spec


def build_matching_set(car_paint_file, output_dir, zones, iracing_id="23371", seed=51,
                       helmet_paint_file=None, suit_paint_file=None, import_spec_map=None, car_prefix="car_num",
                       stamp_image=None, stamp_spec_finish="gloss"):
    """Build car + matching helmet + matching suit in one call.

    If helmet/suit paint files are provided, applies the SAME zone config
    to all three. If not provided, generates simple spec maps based on
    the car's primary zone finish.

    Returns dict with all outputs.
    """
    print(f"\n{'='*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO - MATCHING SET BUILDER")
    print(f"  Car + Helmet + Suit - One Click")
    print(f"{'='*60}")
    total_start = time.time()

    results = {}

    # 1. Build car (always)
    car_paint, car_spec, zone_masks = build_multi_zone(
        car_paint_file, output_dir, zones, iracing_id, seed, import_spec_map=import_spec_map, car_prefix=car_prefix,
        stamp_image=stamp_image, stamp_spec_finish=stamp_spec_finish)
    results["car_paint"] = car_paint
    results["car_spec"] = car_spec

    # 2. Build helmet spec (only if paint file explicitly provided)
    if helmet_paint_file and os.path.exists(helmet_paint_file):
        h_paint, h_spec = build_helmet_spec(
            helmet_paint_file, output_dir, zones, iracing_id, seed)
        results["helmet_paint"] = h_paint
        results["helmet_spec"] = h_spec
    else:
        print(f"\n  Helmet: skipped (no paint file provided)")

    # 3. Build suit spec (only if paint file explicitly provided)
    if suit_paint_file and os.path.exists(suit_paint_file):
        s_paint, s_spec = build_suit_spec(
            suit_paint_file, output_dir, zones, iracing_id, seed)
        results["suit_paint"] = s_paint
        results["suit_spec"] = s_spec
    else:
        print(f"\n  Suit: skipped (no paint file provided)")

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  MATCHING SET COMPLETE in {total_elapsed:.1f}s!")
    items = ["car"]
    if "helmet_paint" in results or "helmet_spec" in results:
        items.append("helmet")
    if "suit_paint" in results or "suit_spec" in results:
        items.append("suit")
    print(f"  Generated: {' + '.join(items)}")
    print(f"{'='*60}")

    return results


# ================================================================
# WEAR / AGE POST-PROCESSING
# ================================================================

def apply_wear(spec_map, paint_rgb, wear_level, seed=51):
    """Apply wear/age post-processing to an already-rendered spec map + paint.

    wear_level: 0-100
        0   = showroom fresh (no change)
        25  = light track wear (micro-scratches, slight clearcoat fade)
        50  = mid-season (visible scratches, roughness increase, paint chips)
        75  = heavy use (deep scratches, clearcoat loss, paint fade)
        100 = track-beaten veteran (severe damage, extensive clearcoat loss)

    Applies:
    1. Micro-scratches (directional noise => adds roughness)
    2. Clearcoat degradation (noise-driven CC reduction)
    3. Paint fading/chips (brightens/desaturates paint in damaged areas)
    4. Edge wear (stronger damage at high-frequency paint boundaries)

    Returns (modified_spec, modified_paint).
    """
    if wear_level <= 0:
        return spec_map.copy(), paint_rgb.copy()

    w_frac = np.clip(wear_level / 100.0, 0, 1)
    h, w = spec_map.shape[:2]
    shape = (h, w)
    rng = np.random.RandomState(seed + 777)

    spec = spec_map.copy().astype(np.float32)
    paint = paint_rgb.copy().astype(np.float32) / 255.0

    # 1. Micro-scratches: directional noise (horizontal bias like real track rash)
    scratch_h = rng.randn(1, w).astype(np.float32) * 0.6
    scratch_h = np.tile(scratch_h, (h, 1))
    scratch_fine = rng.randn(h, w).astype(np.float32) * 0.4
    scratch = np.clip(scratch_h + scratch_fine, -1, 1)

    # Roughness increase from scratches (R channel)
    roughness_add = np.abs(scratch) * 60 * w_frac
    spec[:,:,1] = np.clip(spec[:,:,1] + roughness_add, 0, 255)

    # Metallic reduction from scratches (scuffs reduce metallic sheen)
    metallic_sub = np.abs(scratch) * 30 * w_frac
    spec[:,:,0] = np.clip(spec[:,:,0] - metallic_sub, 0, 255)

    # 2. Clearcoat degradation
    cc_noise = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed + 888)
    cc_damage = np.clip(np.abs(cc_noise) * 2, 0, 1) * w_frac

    # Only degrade where clearcoat exists (B channel > 0)
    current_cc = spec[:,:,2].astype(np.float32)
    cc_reduction = cc_damage * 16  # up to 16 units lost
    spec[:,:,2] = np.clip(current_cc - cc_reduction, 0, 16).astype(np.uint8)

    # 3. Paint fading/chips in damaged areas
    if w_frac > 0.2:
        chip_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 999)
        chip_mask = np.clip(np.abs(chip_noise) * 3 - (1.5 - w_frac * 1.5), 0, 1)
        # Desaturate and brighten damaged areas
        gray = paint.mean(axis=2, keepdims=True)
        faded = paint * (1 - chip_mask[:,:,np.newaxis] * 0.3) + \
                gray * chip_mask[:,:,np.newaxis] * 0.2 + \
                chip_mask[:,:,np.newaxis] * 0.05  # slight brighten (exposed primer)
        paint = np.clip(faded, 0, 1)

    # 4. Edge wear - stronger damage at color boundaries
    if w_frac > 0.3:
        # Detect edges via Sobel-like gradient magnitude
        from PIL import ImageFilter as IF
        gray_img = Image.fromarray((paint.mean(axis=2) * 255).astype(np.uint8))
        edge_img = gray_img.filter(IF.FIND_EDGES)
        edge_map = np.array(edge_img).astype(np.float32) / 255.0
        # Blur edges to spread wear zone
        edge_pil = Image.fromarray((edge_map * 255).astype(np.uint8))
        edge_pil = edge_pil.filter(IF.GaussianBlur(radius=3))
        edge_map = np.array(edge_pil).astype(np.float32) / 255.0
        edge_wear = edge_map * w_frac * 0.7

        # Extra roughness at edges
        spec[:,:,1] = np.clip(spec[:,:,1] + edge_wear * 80, 0, 255)
        # Extra metallic loss at edges
        spec[:,:,0] = np.clip(spec[:,:,0] - edge_wear * 40, 0, 255)
        # Extra CC loss at edges
        spec[:,:,2] = np.clip(spec[:,:,2].astype(np.float32) - edge_wear * 10, 0, 16)

    result_spec = np.clip(spec, 0, 255).astype(np.uint8)
    result_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    return result_spec, result_paint


# ================================================================
# EXPORT PACKAGE BUILDER
# ================================================================

def build_export_package(output_dir, iracing_id="23371", car_folder_name=None,
                         include_helmet=True, include_suit=True,
                         wear_level=0, zones_config=None):
    """Bundle all render outputs into an organized export package.

    Creates a ZIP file containing:
    - car_num_<id>.tga (paint)
    - car_spec_<id>.tga (spec map)
    - helmet_spec_<id>.tga (if generated)
    - suit_spec_<id>.tga (if generated)
    - PREVIEW_*.png files
    - config.json (zone config for reloading)
    - README.txt (what's in the package)

    Returns path to the ZIP file.
    """
    import zipfile

    os.makedirs(output_dir, exist_ok=True)

    # Save config if provided
    if zones_config:
        config_path = os.path.join(output_dir, "shokker_config.json")
        config_data = {
            "iracing_id": iracing_id,
            "car_folder": car_folder_name or "unknown",
            "zones": zones_config,
            "wear_level": wear_level,
            "engine_version": "3.0 PRO",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

    # Create README
    readme_path = os.path.join(output_dir, "README.txt")
    readme = f"""SHOKKER ENGINE v3.0 PRO - Export Package
========================================
iRacing ID: {iracing_id}
Car: {car_folder_name or 'N/A'}
Wear Level: {wear_level}/100
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

FILE GUIDE:
-----------
car_num_{iracing_id}.tga     => Paint file (copy to iRacing paint folder)
car_spec_{iracing_id}.tga    => Spec map (copy to iRacing paint folder)
helmet_spec_{iracing_id}.tga => Helmet spec (copy to iRacing paint folder)
suit_spec_{iracing_id}.tga   => Suit spec (copy to iRacing paint folder)
PREVIEW_*.png                => Preview images for reference
shokker_config.json          => Re-import this in Paint Booth to reload

INSTALLATION:
Copy the .tga files to your iRacing paint folder:
  Documents/iRacing/paint/<car_folder>/

Powered by Shokker Engine v3.0 PRO
"""
    with open(readme_path, 'w') as f:
        f.write(readme)

    # Build ZIP
    zip_name = f"shokker_{iracing_id}_{car_folder_name or 'export'}_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(output_dir, zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(output_dir):
            if fname == zip_name:
                continue  # don't add zip to itself
            fpath = os.path.join(output_dir, fname)
            if os.path.isfile(fpath):
                # Only include relevant files
                if fname.endswith(('.tga', '.png', '.json', '.txt')):
                    zf.write(fpath, fname)

    zip_size = os.path.getsize(zip_path)
    print(f"\n  Export package: {zip_path}")
    print(f"  Size: {zip_size / 1024 / 1024:.1f} MB")
    return zip_path


# ================================================================
# GRADIENT MASK GENERATOR
# ================================================================

def generate_gradient_mask(height, width, direction="horizontal", center=None,
                           start_pct=0.0, end_pct=1.0):
    """Generate a float32 gradient mask (0-1) for zone fade transitions.

    Args:
        height, width: Output dimensions
        direction: 'horizontal', 'vertical', 'radial', 'diagonal'
        center: (cx, cy) normalized 0-1 for radial gradients. Default center.
        start_pct: Where gradient begins (0.0 = edge)
        end_pct: Where gradient ends (1.0 = opposite edge)

    Returns:
        float32 array (height, width) with values 0.0-1.0
    """
    if direction == "horizontal":
        grad = np.linspace(0, 1, width, dtype=np.float32)
        mask = np.tile(grad, (height, 1))
    elif direction == "vertical":
        grad = np.linspace(0, 1, height, dtype=np.float32)
        mask = np.tile(grad.reshape(-1, 1), (1, width))
    elif direction == "diagonal":
        gx = np.linspace(0, 1, width, dtype=np.float32)
        gy = np.linspace(0, 1, height, dtype=np.float32)
        mask = (gx[np.newaxis, :] + gy[:, np.newaxis]) / 2.0
    elif direction == "radial":
        cx = center[0] if center else 0.5
        cy = center[1] if center else 0.5
        gx = np.linspace(0, 1, width, dtype=np.float32)
        gy = np.linspace(0, 1, height, dtype=np.float32)
        dx = gx[np.newaxis, :] - cx
        dy = gy[:, np.newaxis] - cy
        dist = np.sqrt(dx*dx + dy*dy)
        max_dist = np.sqrt(max(cx, 1-cx)**2 + max(cy, 1-cy)**2)
        mask = np.clip(dist / max(max_dist, 1e-6), 0, 1).astype(np.float32)
    else:
        mask = np.full((height, width), 0.5, dtype=np.float32)

    # Apply start/end clipping
    if start_pct > 0 or end_pct < 1:
        span = max(end_pct - start_pct, 1e-6)
        mask = np.clip((mask - start_pct) / span, 0, 1).astype(np.float32)

    return mask


# ================================================================
# DAY/NIGHT DUAL SPEC MAP GENERATOR
# ================================================================

def generate_night_variant(day_spec, night_boost=0.7):
    """Generate a night-optimized spec map from the day spec map.

    Night variant has enhanced reflectivity for track lighting:
    - Metallic boost: more reflection under spotlights
    - Roughness reduction: sharper, more dramatic reflections
    - Clearcoat: push to max for that under-lights pop

    Args:
        day_spec: RGBA uint8 array (R=Metallic, G=Roughness, B=Clearcoat, A=SpecMask)
        night_boost: 0.0-1.0 strength of night enhancement

    Returns:
        night_spec: RGBA uint8 array with night-optimized values
    """
    night = day_spec.copy().astype(np.float32)
    boost = np.clip(night_boost, 0.0, 1.0)

    # R channel = Metallic: boost reflectivity
    night[:,:,0] = np.clip(night[:,:,0] * (1.0 + 0.3 * boost) + 15 * boost, 0, 255)

    # G channel = Roughness: reduce for sharper reflections
    night[:,:,1] = np.clip(night[:,:,1] * (1.0 - 0.25 * boost) - 8 * boost, 0, 255)

    # B channel = Clearcoat: push toward 16 (ON) where any CC exists
    cc = night[:,:,2]
    cc_mask = cc > 0  # pixels that already have clearcoat
    cc[cc_mask] = np.clip(cc[cc_mask] + 4 * boost, 0, 16)
    night[:,:,2] = cc

    # A channel = SpecMask: keep as-is

    return night.astype(np.uint8)


# ================================================================
# FULL RENDER PIPELINE (Car + Helmet + Suit + Wear + Export)
# ================================================================

def full_render_pipeline(car_paint_file, output_dir, zones, iracing_id="23371",
                         seed=51, helmet_paint_file=None, suit_paint_file=None,
                         wear_level=0, car_folder_name=None, export_zip=True,
                         dual_spec=False, night_boost=0.7, import_spec_map=None,
                         car_prefix="car_num", stamp_image=None, stamp_spec_finish="gloss"):
    """The ultimate one-call render pipeline.

    1. Builds car spec map + paint modifications
    2. Generates matching helmet spec (from paint file or default)
    3. Generates matching suit spec (from paint file or default)
    4. Applies wear/age post-processing to all outputs
    5. Bundles everything into an export ZIP

    Returns dict with all outputs + export path.
    """
    print(f"\n{'*'*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO - FULL RENDER PIPELINE")
    print(f"  Car + Helmet + Suit + Wear({wear_level}) + Export")
    print(f"{'*'*60}")
    pipeline_start = time.time()

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Build matching set (car + helmet + suit)
    t_step1 = time.time()
    results = build_matching_set(
        car_paint_file, output_dir, zones, iracing_id, seed,
        helmet_paint_file, suit_paint_file, import_spec_map=import_spec_map,
        car_prefix=car_prefix, stamp_image=stamp_image, stamp_spec_finish=stamp_spec_finish
    )
    print(f"  Step 1 (matching set): {time.time()-t_step1:.1f}s")

    # Step 2: Apply wear post-processing
    if wear_level > 0:
        t_step2 = time.time()
        print(f"\n  Applying wear level {wear_level}/100...")

        # Wear on car
        car_spec_worn, car_paint_worn = apply_wear(
            results["car_spec"], results["car_paint"], wear_level, seed)
        # Overwrite files
        write_tga_24bit(os.path.join(output_dir, f"car_num_{iracing_id}.tga"), car_paint_worn)
        write_tga_32bit(os.path.join(output_dir, f"car_spec_{iracing_id}.tga"), car_spec_worn)
        Image.fromarray(car_paint_worn).save(os.path.join(output_dir, "PREVIEW_paint.png"))
        Image.fromarray(car_spec_worn).save(os.path.join(output_dir, "PREVIEW_spec.png"))
        results["car_paint"] = car_paint_worn
        results["car_spec"] = car_spec_worn

        # Wear on helmet (lighter - helmets don't get as beat up)
        if "helmet_spec" in results:
            helmet_wear = max(0, wear_level - 20)  # 20% less wear than car
            if helmet_wear > 0:
                h_paint = results.get("helmet_paint",
                    np.full((*results["helmet_spec"].shape[:2], 3), 128, dtype=np.uint8))
                h_spec_worn, h_paint_worn = apply_wear(
                    results["helmet_spec"], h_paint, helmet_wear, seed + 1)
                write_tga_32bit(os.path.join(output_dir, f"helmet_spec_{iracing_id}.tga"), h_spec_worn)
                Image.fromarray(h_spec_worn).save(os.path.join(output_dir, "PREVIEW_helmet_spec.png"))
                results["helmet_spec"] = h_spec_worn

        # Wear on suit (much lighter - suits are fabric)
        if "suit_spec" in results:
            suit_wear = max(0, wear_level - 40)  # 40% less wear than car
            if suit_wear > 0:
                s_paint = results.get("suit_paint",
                    np.full((*results["suit_spec"].shape[:2], 3), 128, dtype=np.uint8))
                s_spec_worn, s_paint_worn = apply_wear(
                    results["suit_spec"], s_paint, suit_wear, seed + 2)
                write_tga_32bit(os.path.join(output_dir, f"suit_spec_{iracing_id}.tga"), s_spec_worn)
                Image.fromarray(s_spec_worn).save(os.path.join(output_dir, "PREVIEW_suit_spec.png"))
                results["suit_spec"] = s_spec_worn

        print(f"  Wear applied: car={wear_level}, helmet={max(0,wear_level-20)}, suit={max(0,wear_level-40)}")
        print(f"  Step 2 (wear): {time.time()-t_step2:.1f}s")

    # Step 2.5: Day/Night dual spec maps
    if dual_spec:
        print(f"\n  Generating night spec variants (boost={night_boost})...")

        # Night car spec
        night_car = generate_night_variant(results["car_spec"], night_boost)
        write_tga_32bit(os.path.join(output_dir, f"car_spec_night_{iracing_id}.tga"), night_car)
        Image.fromarray(night_car).save(os.path.join(output_dir, "PREVIEW_spec_night.png"))
        results["car_spec_night"] = night_car

        # Night helmet spec
        if "helmet_spec" in results:
            night_helmet = generate_night_variant(results["helmet_spec"], night_boost)
            write_tga_32bit(os.path.join(output_dir, f"helmet_spec_night_{iracing_id}.tga"), night_helmet)
            Image.fromarray(night_helmet).save(os.path.join(output_dir, "PREVIEW_helmet_spec_night.png"))
            results["helmet_spec_night"] = night_helmet

        # Night suit spec
        if "suit_spec" in results:
            night_suit = generate_night_variant(results["suit_spec"], night_boost)
            write_tga_32bit(os.path.join(output_dir, f"suit_spec_night_{iracing_id}.tga"), night_suit)
            Image.fromarray(night_suit).save(os.path.join(output_dir, "PREVIEW_suit_spec_night.png"))
            results["suit_spec_night"] = night_suit

        print(f"  Night variants generated: car{' + helmet' if 'helmet_spec' in results else ''}{' + suit' if 'suit_spec' in results else ''}")

    # Step 3: Export package
    if export_zip:
        zones_serializable = []
        for z in zones:
            zs = {}
            for k, v in z.items():
                if callable(v):
                    continue
                zs[k] = v
            zones_serializable.append(zs)

        results["export_zip"] = build_export_package(
            output_dir, iracing_id, car_folder_name,
            "helmet_spec" in results, "suit_spec" in results,
            wear_level, zones_serializable
        )

    pipeline_elapsed = time.time() - pipeline_start
    print(f"\n{'*'*60}")
    print(f"  FULL PIPELINE COMPLETE in {pipeline_elapsed:.1f}s!")
    print(f"{'*'*60}")

    return results


# ================================================================
# MAIN - Example usage
# ================================================================
if __name__ == '__main__':
    # Example: Superman #51 ARCA with color-based zones
    paint = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\Driver Paints\Dillon Bryant\db51sm_tga.tga"
    output = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\Driver Paints\Dillon Bryant\v2_test"

    zones = [
        {
            "name": "Blue body",
            "color": "blue",
            "finish": "holographic_flake",
            "intensity": "100",
        },
        {
            "name": "Red/Yellow accents",
            "color": {"hue_range": [0, 70], "sat_min": 0.25},
            "finish": "prismatic",
            "intensity": "100",
        },
        {
            "name": "Dark areas",
            "color": "dark",
            "finish": "carbon_fiber",
            "intensity": "80",
        },
        {
            "name": "Everything else",
            "color": "remaining",
            "finish": "gloss",
            "intensity": "50",
        },
    ]

    build_multi_zone(paint, output, zones, iracing_id="23371", seed=51)



# ================================================================
# END OF ENGINE - Dead duplicate block (2,673 lines) removed
# 2026-03-11. Backup: _archive/shokker_engine_v2_pre_dedup.py
# ================================================================
