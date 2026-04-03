# -*- coding: utf-8 -*-
"""
NEON UNDERGROUND -- 10 neon-glow bases, each with unique spatial structure.
Blacklight reactive, fluorescent paint, neon sign tubes.
Seeds 9200-9209.  All specs: M 240+, R 15-20, CC 16.
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


# ═══════════════════════════════════════════════════════════════════════
# 1. NEON PINK BLAZE  (seed 9200) — hot pink neon with pulsing glow zones
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_pink_blaze(paint, shape, mask, seed, pm, bb):
    """Hot pink neon with concentric pulsing glow zones radiating from multiple centers."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Pulsing radial glow: concentric rings from noise-seeded centers
    y, x = get_mgrid((h, w))
    pulse_field = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 9200)
    # Convert noise to radial pulsing rings
    ring_phase = np.sin(pulse_field * 8.0 * np.pi) * 0.5 + 0.5
    glow_intensity = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 9201)
    glow = np.clip(ring_phase * 0.6 + glow_intensity * 0.2, 0, 1)
    # Hot pink: R high, G low, B mid
    nr = np.clip(0.95 + glow * 0.05, 0, 1)
    ng = np.clip(0.05 + glow * 0.15, 0, 1)
    nb = np.clip(0.45 + glow * 0.20, 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.20 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_pink_blaze(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    pulse = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 9200)
    ring = np.sin(pulse * 8.0 * np.pi) * 0.5 + 0.5
    M = np.clip(242.0 + ring * 13.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(16.0 + ring * 4.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 2. NEON TOXIC GREEN  (seed 9201) — radioactive green with Geiger scatter
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_toxic_green(paint, shape, mask, seed, pm, bb):
    """Radioactive green with Geiger-counter scatter particles — random hot spots."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Geiger scatter: high-frequency speckle for particle hits
    geiger = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 9210)
    hot_spots = np.clip((geiger - 0.4) * 3.0, 0, 1)
    # Low-frequency radiation field
    rad_field = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 9211)
    glow = np.clip(rad_field * 0.3 + 0.5, 0, 1)
    nr = np.clip(0.10 + hot_spots * 0.25 + glow * 0.05, 0, 1)
    ng = np.clip(0.85 + hot_spots * 0.15 + glow * 0.10, 0, 1)
    nb = np.clip(0.02 + hot_spots * 0.08, 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.18 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_toxic_green(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    geiger = multi_scale_noise((h, w), [1, 2, 4], [0.5, 0.3, 0.2], seed + 9210)
    hot = np.clip((geiger - 0.4) * 3.0, 0, 1)
    M = np.clip(245.0 + hot * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + hot * 5.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 3. NEON ELECTRIC BLUE  (seed 9202) — deep UV blue with plasma veins
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_electric_blue(paint, shape, mask, seed, pm, bb):
    """Deep UV blue with plasma discharge veins — branching lightning structure."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Plasma veins: multi-octave noise thresholded to vein-like ridges
    vein_field = multi_scale_noise((h, w), [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 9220)
    veins = np.clip(np.abs(vein_field) * 2.5, 0, 1)
    # Invert so veins are bright (where noise crosses zero = discharge paths)
    discharge = np.clip(1.0 - veins, 0, 1)
    glow_ambient = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 9221)
    nr = np.clip(0.02 + discharge * 0.30 + glow_ambient * 0.03, 0, 1)
    ng = np.clip(0.05 + discharge * 0.20 + glow_ambient * 0.05, 0, 1)
    nb = np.clip(0.80 + discharge * 0.20 + glow_ambient * 0.05, 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.22 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_electric_blue(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    vein = multi_scale_noise((h, w), [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 9220)
    discharge = np.clip(1.0 - np.abs(vein) * 2.5, 0, 1)
    M = np.clip(240.0 + discharge * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(17.0 + discharge * 3.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 4. NEON BLACKLIGHT  (seed 9203) — UV-reactive purple glowing in dark zones
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_blacklight(paint, shape, mask, seed, pm, bb):
    """UV-reactive purple that glows in dark zones — inverse brightness response."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Dark zone map: areas that "absorb" visible light and re-emit UV glow
    dark_zones = multi_scale_noise((h, w), [16, 32, 64, 128], [0.2, 0.3, 0.3, 0.2], seed + 9230)
    # UV responsiveness: darker zones glow brighter (inverse)
    uv_response = np.clip(1.0 - (dark_zones * 0.5 + 0.5), 0, 1)
    flicker = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 9231)
    glow = np.clip(uv_response * 0.7 + flicker * 0.15, 0, 1)
    nr = np.clip(0.40 + glow * 0.30, 0, 1)
    ng = np.clip(0.02 + glow * 0.08, 0, 1)
    nb = np.clip(0.75 + glow * 0.25, 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.18 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_blacklight(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    dark = multi_scale_noise((h, w), [16, 32, 64, 128], [0.2, 0.3, 0.3, 0.2], seed + 9230)
    uv = np.clip(1.0 - (dark * 0.5 + 0.5), 0, 1)
    M = np.clip(244.0 + uv * 11.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(18.0 + uv * 2.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 5. NEON ORANGE HAZARD  (seed 9204) — construction orange + warning stripes
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_orange_hazard(paint, shape, mask, seed, pm, bb):
    """Construction orange with warning stripe pattern — diagonal hazard bands."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Diagonal warning stripes: (x + y) mod period
    stripe_period = 48.0
    stripe_phase = np.mod((x.astype(np.float32) + y.astype(np.float32)), stripe_period) / stripe_period
    # Hard-edged stripe bands (50/50 split)
    stripe_mask = (stripe_phase < 0.5).astype(np.float32)
    # Add noise to stripe edges for realism
    edge_noise = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 9240)
    stripe_mask = np.clip(stripe_mask + edge_noise * 0.08, 0, 1)
    # Orange glow base
    glow = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 9241)
    nr = np.clip(0.98 * stripe_mask + 0.15 * (1.0 - stripe_mask) + glow * 0.02, 0, 1)
    ng = np.clip(0.45 * stripe_mask + 0.10 * (1.0 - stripe_mask) + glow * 0.02, 0, 1)
    nb = np.clip(0.02 * stripe_mask + 0.02 * (1.0 - stripe_mask), 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.15 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_orange_hazard(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    stripe = (np.mod((x.astype(np.float32) + y.astype(np.float32)), 48.0) / 48.0 < 0.5).astype(np.float32)
    M = np.clip(240.0 + stripe * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + stripe * 5.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 6. NEON RED ALERT  (seed 9205) — emergency red with siren concentric rings
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_red_alert(paint, shape, mask, seed, pm, bb):
    """Emergency red with siren-like concentric rings emanating from center."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Concentric rings from center of texture
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    max_dist = np.sqrt(cy ** 2 + cx ** 2)
    norm_dist = dist / max(max_dist, 1.0)
    # Siren rings: sin of distance creates concentric bands
    ring_count = 12.0
    siren = np.sin(norm_dist * ring_count * 2.0 * np.pi) * 0.5 + 0.5
    # Intensity falloff from center
    falloff = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9250)
    glow = np.clip(siren * 0.6 + falloff * 0.2 + 0.2, 0, 1)
    nr = np.clip(0.92 + glow * 0.08, 0, 1)
    ng = np.clip(0.02 + glow * 0.06, 0, 1)
    nb = np.clip(0.02 + glow * 0.04, 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.20 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_red_alert(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    norm_dist = dist / max(np.sqrt(cy ** 2 + cx ** 2), 1.0)
    siren = np.sin(norm_dist * 12.0 * 2.0 * np.pi) * 0.5 + 0.5
    M = np.clip(243.0 + siren * 12.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + siren * 5.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 7. NEON CYBER YELLOW  (seed 9206) — cyberpunk yellow with circuit traces
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_cyber_yellow(paint, shape, mask, seed, pm, bb):
    """Cyberpunk yellow with circuit trace pattern — PCB-like grid with glowing traces."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Circuit grid: orthogonal lines at regular intervals
    grid_h = 24.0
    grid_v = 24.0
    h_lines = np.clip(1.0 - np.abs(np.mod(y.astype(np.float32), grid_h) - grid_h / 2.0) / (grid_h / 2.0), 0, 1)
    v_lines = np.clip(1.0 - np.abs(np.mod(x.astype(np.float32), grid_v) - grid_v / 2.0) / (grid_v / 2.0), 0, 1)
    # Threshold to thin lines
    h_traces = np.clip((h_lines - 0.85) * 12.0, 0, 1)
    v_traces = np.clip((v_lines - 0.85) * 12.0, 0, 1)
    circuit = np.clip(h_traces + v_traces, 0, 1)
    # Noise-modulated trace brightness
    trace_glow = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 9260)
    # Selective activation: some traces glow, some are dim
    activation = np.clip(trace_glow * 0.5 + 0.5, 0, 1)
    active_circuit = circuit * activation
    bg_glow = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 9261)
    nr = np.clip(0.95 * active_circuit + 0.08 * (1.0 - active_circuit) + bg_glow * 0.02, 0, 1)
    ng = np.clip(0.90 * active_circuit + 0.06 * (1.0 - active_circuit) + bg_glow * 0.02, 0, 1)
    nb = np.clip(0.05 * active_circuit + 0.04 * (1.0 - active_circuit), 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.18 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_cyber_yellow(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    h_t = np.clip((np.clip(1.0 - np.abs(np.mod(y.astype(np.float32), 24.0) - 12.0) / 12.0, 0, 1) - 0.85) * 12.0, 0, 1)
    v_t = np.clip((np.clip(1.0 - np.abs(np.mod(x.astype(np.float32), 24.0) - 12.0) / 12.0, 0, 1) - 0.85) * 12.0, 0, 1)
    circuit = np.clip(h_t + v_t, 0, 1)
    M = np.clip(240.0 + circuit * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(16.0 + circuit * 4.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 8. NEON ICE WHITE  (seed 9207) — cold white neon with frost crystallization
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_ice_white(paint, shape, mask, seed, pm, bb):
    """Cold white neon with frost crystallization — dendritic ice crystal growth pattern."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Frost dendrites: high-frequency angular noise for crystal branches
    crystal_a = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 9270)
    crystal_b = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 9271)
    # Dendritic ridges: where two noise fields cross zero
    dendrite = np.clip(1.0 - np.abs(crystal_a - crystal_b) * 3.0, 0, 1)
    # Background cold glow
    cold_field = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 9272)
    glow = np.clip(dendrite * 0.5 + cold_field * 0.15 + 0.4, 0, 1)
    nr = np.clip(0.88 + glow * 0.12, 0, 1)
    ng = np.clip(0.90 + glow * 0.10, 0, 1)
    nb = np.clip(0.98 + glow * 0.02, 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.25 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_ice_white(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    ca = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 9270)
    cb = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 9271)
    dendrite = np.clip(1.0 - np.abs(ca - cb) * 3.0, 0, 1)
    M = np.clip(248.0 + dendrite * 7.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + dendrite * 5.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 9. NEON DUAL GLOW  (seed 9208) — two-color neon (pink+blue) split field
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_dual_glow(paint, shape, mask, seed, pm, bb):
    """Two-color neon (pink+blue) split by a warped spatial field — organic boundary."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Warped spatial divider: diagonal baseline + noise warp
    baseline = (x.astype(np.float32) / max(w, 1) + y.astype(np.float32) / max(h, 1)) * 0.5
    warp = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9280)
    divider = np.clip(baseline + warp * 0.15, 0, 1)
    # Smooth split: sigmoid-like transition
    split = 1.0 / (1.0 + np.exp(-20.0 * (divider - 0.5)))
    # Pink side
    glow_a = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 9281)
    # Blue side
    glow_b = multi_scale_noise((h, w), [8, 16], [0.5, 0.5], seed + 9282)
    pink_r, pink_g, pink_b = 0.95, 0.12, 0.55
    blue_r, blue_g, blue_b = 0.08, 0.20, 0.95
    nr = np.clip(pink_r * split + blue_r * (1.0 - split) + glow_a * 0.03 + glow_b * 0.03, 0, 1)
    ng = np.clip(pink_g * split + blue_g * (1.0 - split) + glow_a * 0.02 + glow_b * 0.02, 0, 1)
    nb = np.clip(pink_b * split + blue_b * (1.0 - split) + glow_a * 0.02 + glow_b * 0.04, 0, 1)
    effect = np.stack([nr, ng, nb], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.20 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_dual_glow(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    baseline = (x.astype(np.float32) / max(w, 1) + y.astype(np.float32) / max(h, 1)) * 0.5
    warp = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9280)
    split = 1.0 / (1.0 + np.exp(-20.0 * (np.clip(baseline + warp * 0.15, 0, 1) - 0.5)))
    M = np.clip(242.0 + split * 10.0 * sm + (1.0 - split) * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(16.0 + split * 4.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC


# ═══════════════════════════════════════════════════════════════════════
# 10. NEON RAINBOW TUBE  (seed 9209) — full spectrum tube with banding
# ═══════════════════════════════════════════════════════════════════════

def paint_neon_rainbow_tube(paint, shape, mask, seed, pm, bb):
    """Full spectrum neon tube with horizontal banding — smooth hue sweep across surface."""
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Hue sweep: position-based hue with noise warp for organic feel
    hue_warp = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9290)
    # Primary sweep along x-axis with gentle warp
    hue = np.mod((x.astype(np.float32) / max(w, 1)) * 1.0 + hue_warp * 0.08, 1.0)
    # Band structure: modulate brightness in horizontal bands
    band_noise = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 9291)
    band = np.sin(y.astype(np.float32) / max(h, 1) * 20.0 * np.pi + band_noise * 2.0) * 0.5 + 0.5
    brightness = np.clip(0.75 + band * 0.25, 0, 1)
    # HSV -> RGB (vectorized): S=1.0, V=brightness
    i = (hue * 6.0).astype(np.int32) % 6
    f = hue * 6.0 - np.floor(hue * 6.0)
    p = np.zeros_like(brightness)
    q = brightness * (1.0 - f)
    t = brightness * f
    v = brightness
    # Build RGB from HSV sectors
    nr = np.where(i == 0, v, np.where(i == 1, q, np.where(i == 2, p, np.where(i == 3, p, np.where(i == 4, t, v)))))
    ng = np.where(i == 0, t, np.where(i == 1, v, np.where(i == 2, v, np.where(i == 3, q, np.where(i == 4, p, p)))))
    nb = np.where(i == 0, p, np.where(i == 1, p, np.where(i == 2, t, np.where(i == 3, v, np.where(i == 4, v, q)))))
    effect = np.stack([np.clip(nr, 0, 1), np.clip(ng, 0, 1), np.clip(nb, 0, 1)], axis=-1).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:, :, np.newaxis] * blend) +
                     effect * (mask[:, :, np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:, :, np.newaxis] * 0.20 * pm *
                   mask[:, :, np.newaxis], 0, 1).astype(np.float32)


def spec_neon_rainbow_tube(shape, seed, sm, base_m, base_r):
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    hue_warp = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9290)
    hue = np.mod((x.astype(np.float32) / max(w, 1)) + hue_warp * 0.08, 1.0)
    band_noise = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 9291)
    band = np.sin(y.astype(np.float32) / max(h, 1) * 20.0 * np.pi + band_noise * 2.0) * 0.5 + 0.5
    M = np.clip(245.0 + band * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + hue * 5.0 * sm, 15, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)
    return M, R, CC
