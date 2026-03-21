"""
engine/chameleon.py - Chameleon v5 Color Shift Paint Functions
===============================================================
ONE file. ALL chameleon. Extracted from shokker_engine_v2.py.

CONTENTS:
  _chameleon_v5_field      - panel direction noise field generator
  _chameleon_v5_color_ramp - multi-stop HSV ramp mapper
  _chameleon_v5_flake      - Voronoi micro-flake texture
  spec_chameleon_v5        - coordinated metallic spec (M/R/CC per-pixel)
  spec_chameleon_pro       - backward-compatible spec wrapper
  paint_chameleon_v5_core  - CORE paint function: all chameleon presets use this
  paint_chameleon_gradient - backward-compatible 2-param wrapper
  paint_chameleon_midnight  - Deep purple → indigo → teal → gold
  paint_chameleon_phoenix   - Crimson → red → orange → gold
  paint_chameleon_ocean     - Teal → blue → indigo → violet
  paint_chameleon_venom     - Toxic green → teal → blue → magenta
  paint_chameleon_copper    - Copper → rose gold → magenta → violet → teal
  paint_chameleon_arctic    - Silver → ice blue → sky → aqua
  paint_chameleon_amethyst  - Deep purple → violet → pink → rose
  paint_chameleon_emerald   - Emerald → teal → cyan → blue → sapphire
  paint_chameleon_obsidian  - Black → deep purple → dark blue → dark teal
  paint_mystichrome         - Green → blue → purple (Ford SVT tribute)

DEPENDENCY INJECTION:
  Call integrate_chameleon(engine_module) after import.
  Used by shokker_engine_v2.py via:
    import engine.chameleon as _chameleon_mod
    _chameleon_mod.integrate_chameleon(sys.modules[__name__])
    from engine.chameleon import *

FIX GUIDE:
  "Wrong color in chameleon preset"  → find paint_chameleon_XXX, fix color_stops
  "Alpha index crash"                → paint is always 3-channel RGB (already fixed)
  "Spec doesn't coordinate"          → spec_chameleon_v5 uses same seed/field
"""

import numpy as np
import colorsys

_engine = None  # Injected by shokker_engine_v2 after import


def integrate_chameleon(engine_module):
    """Wire this module into the host engine. Called once at startup."""
    global _engine
    _engine = engine_module


def _msn(shape, scales, weights, seed):
    """Delegate multi_scale_noise to host engine (avoids reimplementing it)."""
    return _engine.multi_scale_noise(shape, scales, weights, seed)


def get_mgrid(shape):
    """Delegate get_mgrid to host engine."""
    return _engine.get_mgrid(shape)


def hsv_to_rgb_vec(h, s, v):
    """Delegate hsv_to_rgb_vec to host engine."""
    return _engine.hsv_to_rgb_vec(h, s, v)


# ================================================================
def _chameleon_v5_field(shape, seed, flow_complexity=3):
    """Generate the master panel-orientation field for chameleon v5.
    
    Returns normalized 0-1 field. Different UV regions get different values
    based on simulated 3D surface orientation. This SAME field drives both
    paint color AND spec channel variation for perfect coordination.
    """
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    yn = yf / max(h - 1, 1)
    xn = xf / max(w - 1, 1)

    rng = np.random.RandomState(seed + 8000)
    angles = rng.uniform(0, 2 * np.pi, 6)

    # Primary diagonal sweep - dominant orientation change
    a1 = angles[0]
    field = (np.cos(a1) * yn + np.sin(a1) * xn) * 0.30

    # Secondary cross-flow - perpendicular variation
    a2 = angles[1]
    field = field + (np.cos(a2) * yn + np.sin(a2) * xn) * 0.22

    if flow_complexity >= 2:
        # Radial component - center vs edges (convex body panels)
        cy = 0.45 + rng.uniform(-0.08, 0.08)
        cx = 0.50 + rng.uniform(-0.08, 0.08)
        dist = np.sqrt((yn - cy)**2 + (xn - cx)**2)
        field = field + dist * 0.18

    if flow_complexity >= 3:
        # Low-frequency sine undulation for organic curvature
        for i in range(3):
            freq = 1.2 + rng.uniform(-0.3, 0.5)
            phase = angles[2 + i]
            amp = 0.10 - i * 0.02
            wave = np.sin((yn * np.cos(phase) + xn * np.sin(phase)) * freq * np.pi)
            field = field + wave * amp

        # Very light noise for organic panel boundary breakup
        noise = _msn(shape, [64, 128, 256], [0.25, 0.40, 0.35], seed + 8001)
        field = field + noise * 0.05

    # Normalize to 0-1
    fmin, fmax = field.min(), field.max()
    field = (field - fmin) / (fmax - fmin + 1e-8)
    return field


def _chameleon_v5_flake(shape, seed, cell_size=5):
    """Generate Voronoi-like micro-flake cells for paint depth.
    Returns per-pixel flake value (0-1) and edge detection mask.
    """
    h, w = shape
    rng = np.random.RandomState(seed + 8100)
    ny = max(1, h // cell_size)
    nx = max(1, w // cell_size)
    cell_vals = rng.rand(ny + 2, nx + 2).astype(np.float32)
    yidx = np.clip(np.arange(h) // cell_size, 0, ny).astype(int)
    xidx = np.clip(np.arange(w) // cell_size, 0, nx).astype(int)
    flake = cell_vals[yidx[:, None], xidx[None, :]]
    # Add fine noise within cells
    fine = rng.rand(h, w).astype(np.float32) * 0.3
    flake = flake * 0.7 + fine
    return flake


def _chameleon_v5_color_ramp(field, color_stops):
    """Map 0-1 field through multi-stop HSV color ramp with smoothstep.
    color_stops: list of (position, H_deg, S, V). Returns R,G,B float arrays.
    """
    stops = sorted(color_stops, key=lambda s: s[0])
    n = len(stops)
    h, w = field.shape

    # Convert stops to RGB
    stop_rgb = []
    for pos, hue, sat, val in stops:
        h_arr = np.array([[hue / 360.0]], dtype=np.float32)
        s_arr = np.array([[sat]], dtype=np.float32)
        v_arr = np.array([[val]], dtype=np.float32)
        r, g, b = hsv_to_rgb_vec(h_arr, s_arr, v_arr)
        stop_rgb.append((float(r[0,0]), float(g[0,0]), float(b[0,0])))

    out_r = np.zeros((h, w), dtype=np.float32)
    out_g = np.zeros((h, w), dtype=np.float32)
    out_b = np.zeros((h, w), dtype=np.float32)

    for i in range(n - 1):
        p0, p1 = stops[i][0], stops[i+1][0]
        r0, g0, b0 = stop_rgb[i]
        r1, g1, b1 = stop_rgb[i+1]
        if i == 0:
            seg = field <= p1
        elif i == n - 2:
            seg = field > p0
        else:
            seg = (field > p0) & (field <= p1)
        if not np.any(seg):
            continue
        span = max(p1 - p0, 1e-8)
        t = np.clip((field[seg] - p0) / span, 0, 1)
        t = t * t * (3.0 - 2.0 * t)  # smoothstep
        out_r[seg] = r0 + (r1 - r0) * t
        out_g[seg] = g0 + (g1 - g0) * t
        out_b[seg] = b0 + (b1 - b0) * t

    return out_r, out_g, out_b


def spec_chameleon_v5(shape, mask, seed, sm, field=None,
                      M_base=225, M_range=30, R_base=10, R_range=12,
                      CC_base=16, CC_range=50):
    """Chameleon v5 COORDINATED spec - spatially varied M/R/CC driven by paint field.

    CC SCALE: 16=max gloss, 17-255=progressively degraded. CC_range=50 means the
    field drives CC from 16 (perfectly glazed face-on panels) to 66 (slightly worn
    coat on glancing panels). This mirrors how real chromaflair paint looks:
    the clearcoat appears thicker and glossier when viewed straight-on.

    CRITICAL: M is INVERSELY correlated with field. Where paint is warm/low-field,
    metallic is higher → stronger Fresnel → color fades to white at grazing.
    Where paint is cool/high-field, metallic is lower → color HOLDS at grazing.
    This creates GENUINE differential Fresnel behavior across the car.

    Clearcoat OPPOSES metallic - where M is high (edges), CC is low (colored
    reflections dominate). Where M is lower (flats), CC is higher (white
    flash competes). This creates the dual-layer effect of real chameleon paint.
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)

    if field is None:
        field = _chameleon_v5_field(shape, seed)

    # Metallic: INVERSE of field - darker/warmer paint = more metallic
    M_arr = M_base + (1.0 - field) * M_range

    # Roughness: low base with micro-flake variation
    flake = _chameleon_v5_flake(shape, seed + 50, cell_size=5)
    R_arr = R_base + flake * R_range * sm

    # Clearcoat: OPPOSING metallic - follows field
    CC_arr = CC_base + field * CC_range

    # Light smooth noise overlay for organic feel
    m_noise = _msn(shape, [32, 64], [0.5, 0.5], seed + 8200)
    M_arr = M_arr + m_noise * 5 * sm
    r_noise = _msn(shape, [16, 32], [0.5, 0.5], seed + 8210)
    R_arr = R_arr + r_noise * 3 * sm

    spec[:,:,0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def spec_chameleon_pro(shape, mask, seed, sm):
    """Chameleon spec - backward-compatible wrapper using v5 coordinated system."""
    return spec_chameleon_v5(shape, mask, seed, sm)


def paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb,
                            color_stops, flow_complexity=3,
                            flake_intensity=0.04, flake_hue_spread=0.06,
                            blend_strength=0.93, metallic_brighten=0.12):
    """Chameleon v5 CORE - coordinated dual-map paint with micro-flake texture.

    This is the heart of the new system:
    1. Generates panel direction field (same field spec uses)
    2. Maps multi-stop physically-motivated color ramp through field
    3. Adds Voronoi micro-flake texture with per-flake hue variation
    4. Compensates for iRacing metallic PBR darkening
    5. Blends with original paint at high strength

    color_stops: [(position, H_deg, S, V), ...] - at least 3 stops
    flake_intensity: brightness variation per flake (0.02-0.08)
    flake_hue_spread: hue variation per flake in 0-1 range (0.02-0.10)
    metallic_brighten: compensation for iRacing metallic darkening
    """
    h, w = shape

    # Step 1: Generate master field (SAME seed → matches spec)
    field = _chameleon_v5_field(shape, seed, flow_complexity)

    # Step 2: Map through multi-stop color ramp
    ramp_r, ramp_g, ramp_b = _chameleon_v5_color_ramp(field, color_stops)

    # Step 3: Add Voronoi micro-flake texture
    flake = _chameleon_v5_flake(shape, seed, cell_size=5)
    # Per-flake brightness variation
    flake_bright = (flake - 0.5) * 2.0 * flake_intensity
    ramp_r = np.clip(ramp_r + flake_bright, 0, 1)
    ramp_g = np.clip(ramp_g + flake_bright, 0, 1)
    ramp_b = np.clip(ramp_b + flake_bright, 0, 1)

    # Per-flake hue shift - each flake catches light at slightly different angle
    hue_shift = (flake - 0.5) * flake_hue_spread
    ramp_r = np.clip(ramp_r + hue_shift * 0.8, 0, 1)
    ramp_g = np.clip(ramp_g - hue_shift * 0.3, 0, 1)
    ramp_b = np.clip(ramp_b + hue_shift * 0.5, 0, 1)

    # Step 4: Metallic brightness compensation
    ramp_r = np.clip(ramp_r + metallic_brighten, 0, 1)
    ramp_g = np.clip(ramp_g + metallic_brighten, 0, 1)
    ramp_b = np.clip(ramp_b + metallic_brighten, 0, 1)

    # Step 5: Blend with original paint
    blend = blend_strength * pm
    mask3 = mask[:, :, np.newaxis]
    # Paint is always 3-channel RGB - blend only the 3 channels
    shift_rgb = np.stack([ramp_r, ramp_g, ramp_b], axis=2)
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3

    # Brightness boost for dark source paints
    paint = np.clip(paint + bb * 1.2 * mask3, 0, 1)
    return paint


def paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, primary_hue, shift_range):
    """Backward-compatible wrapper - converts old 2-param HSV ramp to v5 multi-stop.
    Now generates a 5-stop physically-motivated ramp from the primary hue + shift range.
    """
    h_start = primary_hue
    h_end = primary_hue + shift_range
    stops = [
        (0.00, h_start % 360,                  0.88, 0.82),
        (0.25, (h_start + shift_range*0.25) % 360, 0.90, 0.84),
        (0.50, (h_start + shift_range*0.50) % 360, 0.92, 0.85),
        (0.75, (h_start + shift_range*0.75) % 360, 0.90, 0.83),
        (1.00, h_end % 360,                    0.87, 0.80),
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops)


# --- Chameleon Classic Presets (v5 - rich multi-stop ramps) ---

def paint_chameleon_midnight(paint, shape, mask, seed, pm, bb):
    """Midnight - Deep purple → indigo → teal → gold (dark luxury shift)"""
    stops = [
        (0.00, 275, 0.85, 0.65),   # Deep Purple
        (0.25, 245, 0.82, 0.68),   # Indigo
        (0.50, 195, 0.88, 0.72),   # Teal
        (0.75, 165, 0.82, 0.76),   # Aqua
        (1.00, 48,  0.80, 0.82),   # Gold
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.035, flake_hue_spread=0.05)

def paint_chameleon_phoenix(paint, shape, mask, seed, pm, bb):
    """Phoenix - Crimson → red → orange → gold → yellow-green (fire rebirth)"""
    stops = [
        (0.00, 345, 0.92, 0.75),   # Crimson
        (0.20, 8,   0.90, 0.80),   # Red
        (0.40, 25,  0.88, 0.84),   # Orange
        (0.60, 42,  0.85, 0.86),   # Gold
        (0.80, 65,  0.82, 0.84),   # Yellow-Green
        (1.00, 95,  0.78, 0.80),   # Green
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.045, flake_hue_spread=0.07)

def paint_chameleon_ocean(paint, shape, mask, seed, pm, bb):
    """Ocean - Teal → cerulean → blue → indigo → violet (deep sea)"""
    stops = [
        (0.00, 178, 0.88, 0.78),   # Teal
        (0.25, 200, 0.90, 0.76),   # Cerulean
        (0.50, 225, 0.88, 0.74),   # Blue
        (0.75, 255, 0.85, 0.70),   # Indigo
        (1.00, 280, 0.82, 0.72),   # Violet
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.035, flake_hue_spread=0.05)

def paint_chameleon_venom(paint, shape, mask, seed, pm, bb):
    """Venom - Toxic green → teal → blue → purple → magenta (toxic shift)"""
    stops = [
        (0.00, 110, 0.92, 0.82),   # Toxic Green
        (0.25, 155, 0.88, 0.78),   # Teal-Green
        (0.50, 205, 0.85, 0.74),   # Blue
        (0.75, 265, 0.88, 0.72),   # Purple
        (1.00, 310, 0.85, 0.76),   # Magenta
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.04, flake_hue_spread=0.06)

def paint_chameleon_copper(paint, shape, mask, seed, pm, bb):
    """Copper - Copper → rose gold → magenta → violet → teal (full spectrum)"""
    stops = [
        (0.00, 22,  0.85, 0.82),   # Copper
        (0.20, 350, 0.78, 0.80),   # Rose Gold
        (0.40, 320, 0.82, 0.76),   # Magenta
        (0.60, 275, 0.85, 0.72),   # Violet
        (0.80, 220, 0.82, 0.74),   # Blue
        (1.00, 178, 0.80, 0.76),   # Teal
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.05, flake_hue_spread=0.08)

def paint_chameleon_arctic(paint, shape, mask, seed, pm, bb):
    """Arctic - Silver → ice blue → sky → teal → aqua (frozen metallic)"""
    stops = [
        (0.00, 210, 0.20, 0.90),   # Silver (low sat, high value)
        (0.25, 205, 0.45, 0.87),   # Ice Blue
        (0.50, 200, 0.65, 0.84),   # Sky Blue
        (0.75, 188, 0.75, 0.80),   # Teal
        (1.00, 175, 0.80, 0.78),   # Aqua
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flow_complexity=2, flake_intensity=0.03,
                                   flake_hue_spread=0.04, metallic_brighten=0.14)

def paint_chameleon_amethyst(paint, shape, mask, seed, pm, bb):
    """Amethyst - Deep purple → violet → pink → magenta → rose (jewel shift)"""
    stops = [
        (0.00, 270, 0.88, 0.68),   # Deep Purple
        (0.25, 290, 0.85, 0.72),   # Violet
        (0.50, 320, 0.82, 0.78),   # Pink
        (0.75, 340, 0.85, 0.80),   # Magenta
        (1.00, 355, 0.80, 0.82),   # Rose
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.04, flake_hue_spread=0.06)

def paint_chameleon_emerald(paint, shape, mask, seed, pm, bb):
    """Emerald - Emerald → teal → cyan → sky blue → sapphire (jewel ocean)"""
    stops = [
        (0.00, 145, 0.90, 0.72),   # Emerald
        (0.25, 170, 0.88, 0.76),   # Teal
        (0.50, 185, 0.85, 0.78),   # Cyan
        (0.75, 200, 0.82, 0.80),   # Sky Blue
        (1.00, 225, 0.85, 0.76),   # Sapphire
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.035, flake_hue_spread=0.05)

def paint_chameleon_obsidian(paint, shape, mask, seed, pm, bb):
    """Obsidian - Black → deep purple → dark blue → dark teal (stealth shift)"""
    stops = [
        (0.00, 270, 0.70, 0.35),   # Near-Black Purple
        (0.30, 260, 0.75, 0.42),   # Deep Purple
        (0.55, 235, 0.72, 0.45),   # Dark Blue
        (0.80, 200, 0.68, 0.42),   # Dark Teal
        (1.00, 180, 0.65, 0.38),   # Dark Cyan
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.05, flake_hue_spread=0.08,
                                   blend_strength=0.95, metallic_brighten=0.18)


# --- Mystichrome (Ford SVT tribute - 3-color ramp, 240° shift) ---

def paint_mystichrome(paint, shape, mask, seed, pm, bb):
    """Mystichrome - Green → blue → purple (Ford SVT Cobra tribute, wide shift)"""
    stops = [
        (0.00, 140, 0.85, 0.76),   # Forest Green
        (0.20, 165, 0.88, 0.78),   # Teal
        (0.40, 200, 0.90, 0.76),   # Blue
        (0.60, 235, 0.88, 0.74),   # Deep Blue
        (0.80, 265, 0.85, 0.72),   # Indigo
        (1.00, 290, 0.82, 0.74),   # Purple
    ]
    return paint_chameleon_v5_core(paint, shape, mask, seed, pm, bb, stops,
                                   flake_intensity=0.04, flake_hue_spread=0.06)


# ================================================================
# AURORA & CHROMATIC FLOW — Fine intertwined color bands
# ================================================================
# These use higher-frequency flowing fields than chameleon presets.
# The result is visible color threads/bands woven across the surface
# rather than broad panel-based color shifts.

def _aurora_flow_field(shape, seed, num_bands=8, flow_stretch=4.0):
    """Generate a high-frequency flowing field for aurora-style color bands.

    Unlike chameleon's broad panel field, this creates many narrow parallel
    bands with noise distortion — like northern lights curtains.
    """
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h - 1, 1)
    xn = x.astype(np.float32) / max(w - 1, 1)

    rng = np.random.RandomState(seed + 9000)
    base_angle = rng.uniform(0, 2 * np.pi)

    # Project onto flow direction
    proj = np.cos(base_angle) * yn + np.sin(base_angle) * xn

    # Multi-frequency band structure
    field = np.zeros((h, w), dtype=np.float32)
    for i in range(num_bands):
        freq = (i + 2) * 3.5
        phase = rng.uniform(0, 2 * np.pi)
        # Perpendicular noise distortion creates the curtain wobble
        perp = -np.sin(base_angle) * yn + np.cos(base_angle) * xn
        noise_warp = _msn((h, w), [max(8, int(w * 0.05)), max(16, int(w * 0.1))],
                         [0.6, 0.4], seed + 9100 + i * 37) * 0.15
        warped = proj + noise_warp * perp * flow_stretch
        band = np.sin(warped * freq * np.pi + phase)
        weight = 1.0 / (i + 1) ** 0.6
        field += band * weight

    # Normalize to 0-1
    fmin, fmax = field.min(), field.max()
    if fmax - fmin > 1e-6:
        field = (field - fmin) / (fmax - fmin)
    return field


def paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, color_stops,
                           num_bands=8, flow_stretch=4.0, band_sharpness=1.0,
                           flake_intensity=0.03, blend_strength=0.93,
                           metallic_brighten=0.12):
    """Aurora flow CORE — fine intertwined color bands flowing across the surface.

    Unlike chameleon which shifts broadly across panels, aurora creates visible
    color threads that weave across the car. Think northern lights curtains
    or oil-film rainbow bands but as a paint effect.

    band_sharpness: 1.0 = smooth blending, 2.0+ = sharper band edges
    flow_stretch: how much the bands stretch along flow direction
    num_bands: more bands = finer color threads
    """
    h, w = shape

    # Generate the flowing band field
    field = _aurora_flow_field(shape, seed, num_bands, flow_stretch)

    # Apply sharpness (power curve sharpens band edges)
    if band_sharpness != 1.0:
        field = np.clip(field, 0, 1) ** band_sharpness

    # Map through color ramp
    ramp_r, ramp_g, ramp_b = _chameleon_v5_color_ramp(field, color_stops)

    # Fine flake texture for metallic micro-variation
    flake = _chameleon_v5_flake(shape, seed + 200, cell_size=4)
    flake_bright = (flake - 0.5) * 2.0 * flake_intensity
    ramp_r = np.clip(ramp_r + flake_bright, 0, 1)
    ramp_g = np.clip(ramp_g + flake_bright, 0, 1)
    ramp_b = np.clip(ramp_b + flake_bright, 0, 1)

    # Metallic brightness compensation
    ramp_r = np.clip(ramp_r + metallic_brighten, 0, 1)
    ramp_g = np.clip(ramp_g + metallic_brighten, 0, 1)
    ramp_b = np.clip(ramp_b + metallic_brighten, 0, 1)

    # Blend with original paint
    blend = blend_strength * pm
    mask3 = mask[:, :, np.newaxis]
    shift_rgb = np.stack([ramp_r, ramp_g, ramp_b], axis=2)
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3
    paint = np.clip(paint + bb * 1.2 * mask3, 0, 1)
    return paint


# --- Aurora Presets ---

def paint_aurora_borealis(paint, shape, mask, seed, pm, bb):
    """Northern Lights — Green → teal → cyan → blue → violet flowing curtains"""
    stops = [
        (0.00, 120, 0.88, 0.82),   # Green
        (0.20, 165, 0.85, 0.78),   # Teal
        (0.40, 185, 0.90, 0.80),   # Cyan
        (0.60, 210, 0.85, 0.76),   # Blue
        (0.80, 260, 0.82, 0.72),   # Violet
        (1.00, 130, 0.85, 0.80),   # Back to green
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=10, flow_stretch=5.0, band_sharpness=1.2)

def paint_aurora_solar_wind(paint, shape, mask, seed, pm, bb):
    """Solar Wind — Orange → gold → yellow → lime → cyan → blue electric bands"""
    stops = [
        (0.00, 25,  0.92, 0.85),   # Orange
        (0.20, 42,  0.90, 0.88),   # Gold
        (0.40, 55,  0.88, 0.90),   # Yellow
        (0.60, 90,  0.85, 0.82),   # Lime
        (0.80, 180, 0.88, 0.78),   # Cyan
        (1.00, 220, 0.82, 0.74),   # Blue
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=12, flow_stretch=6.0, band_sharpness=1.0)

def paint_aurora_nebula(paint, shape, mask, seed, pm, bb):
    """Nebula — Deep purple → magenta → pink → rose → coral → amber flowing wisps"""
    stops = [
        (0.00, 280, 0.85, 0.65),   # Deep Purple
        (0.20, 310, 0.88, 0.72),   # Magenta
        (0.40, 335, 0.82, 0.80),   # Pink
        (0.60, 350, 0.78, 0.85),   # Rose
        (0.80, 15,  0.85, 0.82),   # Coral
        (1.00, 35,  0.80, 0.80),   # Amber
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=8, flow_stretch=4.0, band_sharpness=1.5)

def paint_aurora_chromatic_surge(paint, shape, mask, seed, pm, bb):
    """Chromatic Surge — Full rainbow spectrum in tight concentrated bands"""
    stops = [
        (0.00, 0,   0.90, 0.82),   # Red
        (0.14, 30,  0.88, 0.85),   # Orange
        (0.28, 55,  0.90, 0.88),   # Yellow
        (0.42, 120, 0.85, 0.80),   # Green
        (0.57, 185, 0.88, 0.78),   # Cyan
        (0.71, 230, 0.85, 0.76),   # Blue
        (0.85, 280, 0.82, 0.74),   # Purple
        (1.00, 340, 0.88, 0.80),   # Magenta
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=16, flow_stretch=3.0, band_sharpness=0.8)

def paint_aurora_frozen_flame(paint, shape, mask, seed, pm, bb):
    """Frozen Flame — Ice blue → white → gold → red concentrated flow"""
    stops = [
        (0.00, 200, 0.60, 0.90),   # Ice Blue
        (0.25, 210, 0.15, 0.95),   # Near-White
        (0.50, 45,  0.85, 0.88),   # Gold
        (0.75, 15,  0.90, 0.78),   # Red-Orange
        (1.00, 200, 0.55, 0.88),   # Back to Ice
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=14, flow_stretch=5.0, band_sharpness=1.8)

def paint_aurora_deep_ocean(paint, shape, mask, seed, pm, bb):
    """Deep Ocean — Dark navy → sapphire → teal → aqua → seafoam subtle flowing bands"""
    stops = [
        (0.00, 230, 0.85, 0.45),   # Dark Navy
        (0.25, 218, 0.82, 0.58),   # Sapphire
        (0.50, 190, 0.80, 0.65),   # Teal
        (0.75, 170, 0.75, 0.72),   # Aqua
        (1.00, 155, 0.70, 0.78),   # Seafoam
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=6, flow_stretch=7.0, band_sharpness=1.0)

def paint_aurora_volcanic(paint, shape, mask, seed, pm, bb):
    """Volcanic Flow — Black → deep red → orange → gold flowing magma veins"""
    stops = [
        (0.00, 0,   0.10, 0.15),   # Near-Black
        (0.20, 0,   0.85, 0.45),   # Deep Red
        (0.40, 10,  0.90, 0.65),   # Red
        (0.60, 25,  0.92, 0.78),   # Orange
        (0.80, 45,  0.88, 0.85),   # Gold
        (1.00, 0,   0.08, 0.18),   # Back to Dark
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=10, flow_stretch=4.0, band_sharpness=2.0)

def paint_aurora_ethereal(paint, shape, mask, seed, pm, bb):
    """Ethereal — Soft pastel flowing: lavender → mint → peach → sky ultra-fine threads"""
    stops = [
        (0.00, 270, 0.40, 0.88),   # Lavender
        (0.25, 155, 0.35, 0.90),   # Mint
        (0.50, 20,  0.35, 0.92),   # Peach
        (0.75, 200, 0.30, 0.90),   # Sky
        (1.00, 280, 0.38, 0.87),   # Lavender return
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=20, flow_stretch=3.0, band_sharpness=0.7,
                                  flake_intensity=0.02)

def paint_aurora_toxic_current(paint, shape, mask, seed, pm, bb):
    """Toxic Current — Acid green → neon yellow → electric blue concentrated electric bands"""
    stops = [
        (0.00, 110, 0.95, 0.85),   # Acid Green
        (0.25, 80,  0.92, 0.90),   # Neon Yellow-Green
        (0.50, 60,  0.90, 0.92),   # Neon Yellow
        (0.75, 200, 0.92, 0.80),   # Electric Blue
        (1.00, 120, 0.90, 0.82),   # Back to Green
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=14, flow_stretch=4.5, band_sharpness=1.5)

def paint_aurora_midnight_silk(paint, shape, mask, seed, pm, bb):
    """Midnight Silk — Very dark with subtle deep blue → purple → teal threads barely visible"""
    stops = [
        (0.00, 240, 0.70, 0.30),   # Dark Blue
        (0.25, 270, 0.65, 0.28),   # Dark Purple
        (0.50, 300, 0.60, 0.32),   # Dark Magenta
        (0.75, 200, 0.68, 0.30),   # Dark Teal
        (1.00, 235, 0.72, 0.28),   # Dark Blue return
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=8, flow_stretch=6.0, band_sharpness=1.0,
                                  flake_intensity=0.02, metallic_brighten=0.05)


# ================================================================
# END OF engine/chameleon.py
# ================================================================
