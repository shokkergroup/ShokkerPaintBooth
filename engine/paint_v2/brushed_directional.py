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
from engine.paint_v2 import ensure_bb_2d


# ==================================================================
# BRUSHED ALUMINUM - Anisotropic micro-groove lathe turning
# ==================================================================
def paint_brushed_aluminum_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # STRONG horizontal groove lines — the signature brushed metal look
    groove_freq = 0.5  # visible groove spacing
    # Low-freq variation for realism, but keep directional dominance
    groove_var = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1201)
    grooves = np.sin(x * groove_freq + groove_var * 1.5) * 0.5 + 0.5
    # Fine secondary grooves for detail
    fine_grooves = np.sin(x * 1.8 + groove_var * 0.8) * 0.5 + 0.5
    grooves = grooves * 0.7 + fine_grooves * 0.3
    # Pressure variation
    pressure = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 1202)
    groove_depth = grooves * (0.08 + pressure * 0.05)  # 3x stronger
    # Aluminum base color — keep directional texture visible
    gray = base.mean(axis=2)
    alu = np.clip(gray * 0.2 + 0.55, 0, 1)
    r_ch = np.clip(alu + groove_depth, 0, 1)
    g_ch = np.clip(alu + groove_depth, 0, 1)
    b_ch = np.clip(alu + groove_depth + 0.015, 0, 1)  # slight cool tint
    effect = np.stack([r_ch, g_ch, b_ch], axis=-1).astype(np.float32)
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
    CC = np.clip(16.0 + grooves * 4.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# BRUSHED TITANIUM - Electron beam surface remelting
# ==================================================================
def paint_brushed_titanium_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # E-beam remelting: overlapping horizontal melt tracks
    track_spacing = 40.0
    track_phase = np.mod(y, track_spacing) / track_spacing
    melt_pool = np.exp(-((track_phase - 0.5)**2) / (2.0 * 0.15**2))
    # Directional grain along X (horizontal brushing)
    grain_dir = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.35, 0.35], seed + 1211)
    # Add explicit horizontal line texture
    h_lines = np.sin(y.astype(np.float32) * 0.8) * 0.5 + 0.5
    resolid = (melt_pool * 0.6 + h_lines * 0.4) * grain_dir * 0.10  # 2.5x stronger
    # Titanium base: darker, slightly blue-grey
    gray = base.mean(axis=2)
    ti_base = np.clip(gray * 0.15 + 0.42, 0, 1)
    # Heat tint at track overlap zones (stronger for visibility)
    overlap = np.clip((track_phase - 0.85) * 8.0, 0, 1) + np.clip((0.15 - track_phase) * 8.0, 0, 1)
    heat_tint_b = overlap * 0.06  # doubled blue tint at overlaps
    heat_tint_r = overlap * 0.02  # slight warm at overlaps
    effect = np.stack([
        np.clip(ti_base + resolid - overlap * 0.02 + heat_tint_r, 0, 1),
        np.clip(ti_base + resolid - overlap * 0.01, 0, 1),
        np.clip(ti_base + resolid + heat_tint_b, 0, 1)
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.32 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_brushed_titanium(shape, seed, sm, base_m, base_r):
    """Brushed titanium: strong directional grain with anisotropic R variation."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    track = np.mod(y, 40.0) / 40.0
    melt = np.exp(-((track - 0.5)**2) / (2.0 * 0.15**2))
    # Fine directional noise aligned with brush direction
    brush = multi_scale_noise((h, w), [2, 128], [0.7, 0.3], seed + 1310)
    M = np.clip(190.0 + melt * 40.0 * sm + brush * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + melt * 25.0 * sm + brush * 18.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + melt * 6.0 + brush * 3.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# BRUSHED WRAP - Vinyl embossed groove with stretch distortion
# ==================================================================
def paint_brushed_wrap_v2(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
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
    CC = np.clip(16.0 + stretch * 4.0, 16, 255).astype(np.float32)
    return M, R, CC


# 2026-04-24 regular-base rebuild override: dense anisotropic aluminum
def _bd_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min())
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def paint_brushed_aluminum_v2(paint, shape, mask, seed, pm, bb):
    """Natural brushed aluminum: fine hairline scratches, not broad stripes."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    warp = multi_scale_noise((h, w), [8, 18, 42], [0.42, 0.36, 0.22], seed + 1201)
    hair = _bd_norm01(
        np.sin(y * 1.65 + warp * 2.4) * 0.42 +
        np.sin(y * 3.85 + x * 0.011 + warp * 1.3) * 0.32 +
        np.sin(y * 8.60 + x * 0.019) * 0.16
    )
    long_scratch = _bd_norm01(np.sin(x * 0.018 + warp * 3.0) + np.sin(x * 0.043 + y * 0.006) * 0.42)
    dust = _bd_norm01(multi_scale_noise((h, w), [1, 2, 5], [0.45, 0.34, 0.21], seed + 1203))
    grain = np.clip(hair * 0.60 + long_scratch * 0.24 + dust * 0.16, 0, 1)
    gray = base.mean(axis=2)
    alu = np.clip(gray * 0.10 + 0.58 + (grain - 0.5) * 0.18, 0, 1)
    effect = np.stack([
        np.clip(alu * 0.985 + long_scratch * 0.015, 0, 1),
        np.clip(alu, 0, 1),
        np.clip(alu * 1.025 + hair * 0.012, 0, 1),
    ], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, None]
    return np.clip(base * (1.0 - blend) + effect * blend + bb[:, :, None] * 0.22 * blend, 0, 1).astype(np.float32)


def spec_brushed_aluminum(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    warp = multi_scale_noise((h, w), [8, 18, 42], [0.42, 0.36, 0.22], seed + 1201)
    hair = _bd_norm01(
        np.sin(y * 1.65 + warp * 2.4) * 0.42 +
        np.sin(y * 3.85 + x * 0.011 + warp * 1.3) * 0.32 +
        np.sin(y * 8.60 + x * 0.019) * 0.16
    )
    long_scratch = _bd_norm01(np.sin(x * 0.018 + warp * 3.0) + np.sin(x * 0.043 + y * 0.006) * 0.42)
    M = np.clip(178.0 + hair * 46.0 * sm + long_scratch * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(22.0 + (1.0 - hair) * 34.0 * sm + long_scratch * 16.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + (1.0 - hair) * 20.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC
