# -*- coding: utf-8 -*-
"""
BRUSHED & DIRECTIONAL -- 3 bases, each with unique paint_fn + spec_fn

Techniques:
  brushed_aluminum  - Anisotropic micro-groove lathe turning model
  brushed_titanium  - Electron beam surface remelting texture
  brushed_wrap      - Vinyl film embossed groove with stretch distortion
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid


# ==================================================================
# BRUSHED ALUMINUM - Anisotropic micro-groove lathe turning
# ==================================================================
def paint_brushed_aluminum_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Micro-groove lines from mechanical brushing (horizontal dominant)
    groove_freq = 0.3  # tight groove spacing
    groove_var = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1201)
    grooves = np.sin(x * groove_freq + groove_var * 3.0) * 0.5 + 0.5
    # Groove depth modulation (pressure variation during brushing)
    pressure = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1202)
    groove_depth = grooves * (0.03 + pressure * 0.02)
    # Aluminum base color
    gray = base.mean(axis=2)
    alu = np.clip(gray * 0.2 + 0.58, 0, 1)
    effect = np.clip(np.stack([alu + groove_depth, alu + groove_depth, alu + groove_depth + 0.01]*1, axis=-1)[:,:,:3], 0, 1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.35 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_brushed_aluminum(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    groove_var = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 1201)
    grooves = np.sin(x * 0.3 + groove_var * 3.0) * 0.5 + 0.5
    # Brushed: high metallic, anisotropic roughness (higher across grooves)
    M = np.clip(195.0 + grooves * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + grooves * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(4.0 + grooves * 4.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# BRUSHED TITANIUM - Electron beam surface remelting
# ==================================================================
def paint_brushed_titanium_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # E-beam remelting: overlapping melt tracks create directional texture
    track_spacing = 40.0
    track_phase = np.mod(y, track_spacing) / track_spacing
    # Melt pool shape: Gaussian profile per track
    melt_pool = np.exp(-((track_phase - 0.5)**2) / (2.0 * 0.15**2))
    # Resolidification grain direction follows melt pool gradient
    grain_dir = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.35, 0.35], seed + 1211)
    resolid = melt_pool * grain_dir * 0.04
    # Titanium color: darker, slightly blue-grey
    gray = base.mean(axis=2)
    ti_base = np.clip(gray * 0.15 + 0.42, 0, 1)
    # Heat tint at track overlap zones
    overlap = np.clip((track_phase - 0.85) * 8.0, 0, 1) + np.clip((0.15 - track_phase) * 8.0, 0, 1)
    heat_tint_b = overlap * 0.03  # slight blue at overlaps
    effect = np.stack([
        np.clip(ti_base + resolid - overlap * 0.01, 0, 1),
        np.clip(ti_base + resolid - overlap * 0.005, 0, 1),
        np.clip(ti_base + resolid + heat_tint_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.32 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_brushed_titanium(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    track = np.mod(y, 40.0) / 40.0
    melt = np.exp(-((track - 0.5)**2) / (2.0 * 0.15**2))
    # Titanium: high metallic, moderate roughness from resolidification
    M = np.clip(190.0 + melt * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(14.0 + melt * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(6.0 + melt * 4.0, 0, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# BRUSHED WRAP - Vinyl embossed groove with stretch distortion
# ==================================================================
def paint_brushed_wrap_v2(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Embossed groove pattern in vinyl (stamped, not cut)
    groove_base = np.sin(x * 0.25) * 0.5 + 0.5
    # Stretch distortion from application (vinyl stretches over curves)
    stretch = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 1221)
    # Stretched zones: grooves spread apart. Compressed: tighter
    distorted_groove = np.sin(x * 0.25 * (0.8 + stretch * 0.4)) * 0.5 + 0.5
    groove_tex = distorted_groove * 0.03
    # Vinyl base: slightly glossy grey-silver
    gray = base.mean(axis=2)
    vinyl = np.clip(gray * 0.2 + 0.52, 0, 1)
    # Vinyl has slight color shift in stretched areas
    effect = np.stack([
        np.clip(vinyl + groove_tex + stretch * 0.01, 0, 1),
        np.clip(vinyl + groove_tex, 0, 1),
        np.clip(vinyl + groove_tex - stretch * 0.005, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.30 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_brushed_wrap(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    stretch = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 1221)
    M = np.clip(140.0 + stretch * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(16.0 + stretch * 12.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(6.0 + stretch * 4.0, 0, 255).astype(np.float32)
    return M, R, CC
