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
try:
    import cv2 as _cv2
except ImportError:
    _cv2 = None

_engine = None  # Injected by shokker_engine_v2 after import

# LRU-style cache for expensive field/flake generators (max 8 entries)
_chameleon_cache = {}


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
    _cache_key = ('field', shape, seed, flow_complexity)
    if _cache_key in _chameleon_cache:
        return _chameleon_cache[_cache_key].copy()
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
        noise = _msn(shape, [8, 16, 32], [0.25, 0.40, 0.35], seed + 8001)
        field = field + noise * 0.05

    # Normalize to 0-1
    fmin, fmax = field.min(), field.max()
    field = (field - fmin) / (fmax - fmin + 1e-8)
    _chameleon_cache[_cache_key] = field.copy()
    if len(_chameleon_cache) > 8:
        _chameleon_cache.pop(next(iter(_chameleon_cache)))
    return field


def _chameleon_v5_flake(shape, seed, cell_size=5):
    """Generate Voronoi-like micro-flake cells for paint depth.
    Returns per-pixel flake value (0-1) and edge detection mask.
    """
    _cache_key = ('flake', shape, seed, cell_size)
    if _cache_key in _chameleon_cache:
        return _chameleon_cache[_cache_key].copy()
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
    _chameleon_cache[_cache_key] = flake.copy()
    if len(_chameleon_cache) > 8:
        _chameleon_cache.pop(next(iter(_chameleon_cache)))
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
    Resolution-capped: computes at 512 max then upscales.

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
    # --- Resolution cap: compute at 512 max ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)

    if field is None:
        field = _chameleon_v5_field((sh, sw), seed)
    elif ds > 1:
        # If field passed in at full res, downsample it
        if _cv2 is not None:
            field = _cv2.resize(field, (sw, sh), interpolation=_cv2.INTER_LINEAR)
        else:
            field = field[::ds, ::ds][:sh, :sw]

    # Metallic: INVERSE of field - darker/warmer paint = more metallic
    M_arr = M_base + (1.0 - field) * M_range

    # Roughness: low base with micro-flake variation
    flake = _chameleon_v5_flake((sh, sw), seed + 50, cell_size=max(2, 5 * sh // h) if ds > 1 else 5)
    mask_s = mask
    if ds > 1:
        if _cv2 is not None:
            mask_s = _cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=_cv2.INTER_LINEAR)
        else:
            mask_s = mask[::ds, ::ds][:sh, :sw]
    R_arr = R_base + flake * R_range * sm

    # Clearcoat: OPPOSING metallic - follows field
    CC_arr = CC_base + field * CC_range

    # Independent noise overlays for M and R — creates viewing-angle shimmer
    m_noise = _msn((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + 8200)
    M_arr = M_arr + m_noise * 8 * sm
    # R noise at DIFFERENT scale + seed so M and R vary independently (key for shimmer)
    r_noise = _msn((sh, sw), [32, 64, 128], [0.3, 0.4, 0.3], seed + 8310)
    R_arr = R_arr + r_noise * 8 * sm

    spec_small = np.zeros((sh, sw, 4), dtype=np.uint8)
    spec_small[:,:,0] = np.clip(M_arr * mask_s, 0, 255).astype(np.uint8)
    spec_small[:,:,1] = np.where(mask_s > 0.01, np.clip(R_arr, 15, 255), 0).astype(np.uint8)
    spec_small[:,:,2] = np.where(mask_s > 0.01, np.clip(CC_arr, 16, 255), 0).astype(np.uint8)
    spec_small[:,:,3] = np.clip(mask_s * 255, 0, 255).astype(np.uint8)

    if ds > 1:
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        if _cv2 is not None:
            for ch in range(4):
                spec[:,:,ch] = _cv2.resize(spec_small[:,:,ch].astype(np.float32), (w, h), interpolation=_cv2.INTER_LINEAR).astype(np.uint8)
        else:
            from PIL import Image
            for ch in range(4):
                spec[:,:,ch] = np.array(Image.fromarray(spec_small[:,:,ch]).resize((w, h), Image.BILINEAR))
        return spec
    return spec_small


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
    Resolution-capped: field/ramp computed at 512 max then upscaled.

    color_stops: [(position, H_deg, S, V), ...] - at least 3 stops
    flake_intensity: brightness variation per flake (0.02-0.08)
    flake_hue_spread: hue variation per flake in 0-1 range (0.02-0.10)
    metallic_brighten: compensation for iRacing metallic darkening
    """
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    # --- Resolution cap: compute field/ramp at 512 max ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)

    # Step 1: Generate master field at small res (SAME seed → matches spec)
    field = _chameleon_v5_field((sh, sw), seed, flow_complexity)

    # Step 2: Map through multi-stop color ramp at small res
    ramp_r, ramp_g, ramp_b = _chameleon_v5_color_ramp(field, color_stops)

    # Step 3: Add Voronoi micro-flake texture at small res
    flake = _chameleon_v5_flake((sh, sw), seed, cell_size=max(2, 5 * sh // h) if ds > 1 else 5)
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

    # Upscale ramps to full resolution
    if ds > 1:
        if _cv2 is not None:
            ramp_r = _cv2.resize(ramp_r, (w, h), interpolation=_cv2.INTER_LINEAR)
            ramp_g = _cv2.resize(ramp_g, (w, h), interpolation=_cv2.INTER_LINEAR)
            ramp_b = _cv2.resize(ramp_b, (w, h), interpolation=_cv2.INTER_LINEAR)
        else:
            from PIL import Image
            ramp_r = np.array(Image.fromarray(ramp_r).resize((w, h), Image.BILINEAR))
            ramp_g = np.array(Image.fromarray(ramp_g).resize((w, h), Image.BILINEAR))
            ramp_b = np.array(Image.fromarray(ramp_b).resize((w, h), Image.BILINEAR))

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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
        # Downsample noise by 4x for speed, then upscale — amplitude is only 0.15
        _ds = 4
        _h_ds, _w_ds = max(4, h // _ds), max(4, w // _ds)
        _noise_small = _msn((_h_ds, _w_ds),
                            [max(2, int(_w_ds * 0.05)), max(4, int(_w_ds * 0.1))],
                            [0.6, 0.4], seed + 9100 + i * 37)
        if _cv2 is not None:
            noise_warp = _cv2.resize(_noise_small, (w, h),
                                     interpolation=_cv2.INTER_LINEAR) * 0.15
        else:
            # Fallback: numpy repeat upscale (no cv2)
            noise_warp = np.repeat(np.repeat(_noise_small, _ds, axis=0), _ds, axis=1)[:h, :w] * 0.15
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
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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


# --- Aurora Presets (Extended — 20 new) ---

def paint_aurora_electric_candy(paint, shape, mask, seed, pm, bb):
    """Electric Candy — WILD: hot pink → electric blue → neon yellow → lime → magenta sharp bands"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 330, 0.95, 0.82),   # Hot Pink
        (0.20, 220, 0.96, 0.88),   # Electric Blue
        (0.40, 60,  0.98, 0.92),   # Neon Yellow
        (0.60, 100, 0.94, 0.85),   # Lime Green
        (0.80, 300, 0.96, 0.80),   # Magenta
        (1.00, 330, 0.95, 0.82),   # Back to Hot Pink
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=16, flow_stretch=6.5, band_sharpness=2.0,
                                  flake_intensity=0.07)

def paint_aurora_ocean_phosphor(paint, shape, mask, seed, pm, bb):
    """Ocean Phosphorescence — deep navy → bioluminescent blue → cyan → teal → seafoam gentle bands"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 235, 0.88, 0.35),   # Deep Navy
        (0.25, 210, 0.85, 0.55),   # Bioluminescent Blue
        (0.50, 185, 0.80, 0.68),   # Cyan Glow
        (0.75, 170, 0.75, 0.60),   # Dark Teal
        (1.00, 155, 0.68, 0.72),   # Seafoam
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=7, flow_stretch=5.5, band_sharpness=0.9,
                                  flake_intensity=0.02)

def paint_aurora_molten_earth(paint, shape, mask, seed, pm, bb):
    """Molten Earth — burnt sienna → copper → dark red → amber → charcoal warm earthy flow"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 18,  0.78, 0.58),   # Burnt Sienna
        (0.25, 25,  0.72, 0.65),   # Copper
        (0.50, 5,   0.82, 0.48),   # Dark Red
        (0.75, 38,  0.80, 0.72),   # Amber
        (1.00, 0,   0.08, 0.28),   # Charcoal
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=9, flow_stretch=4.5, band_sharpness=1.1,
                                  flake_intensity=0.03)

def paint_aurora_arctic_shimmer(paint, shape, mask, seed, pm, bb):
    """Arctic Shimmer — ice white → pale blue → silver → frost blue → pale lavender cold delicate"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 200, 0.12, 0.96),   # Ice White
        (0.25, 208, 0.38, 0.88),   # Pale Blue
        (0.50, 210, 0.08, 0.92),   # Silver
        (0.75, 215, 0.45, 0.84),   # Frost Blue
        (1.00, 265, 0.28, 0.90),   # Pale Lavender
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=8, flow_stretch=5.0, band_sharpness=0.8,
                                  flake_intensity=0.02, metallic_brighten=0.15)

def paint_aurora_neon_storm(paint, shape, mask, seed, pm, bb):
    """Neon Storm — ULTRA WILD: neon green → hot pink → electric purple → bright orange → cyan"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 115, 0.98, 0.90),   # Neon Green
        (0.20, 330, 0.97, 0.86),   # Hot Pink
        (0.40, 280, 0.96, 0.82),   # Electric Purple
        (0.60, 25,  0.98, 0.92),   # Bright Orange
        (0.80, 185, 0.96, 0.88),   # Cyan
        (1.00, 115, 0.98, 0.90),   # Back to Neon Green
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=18, flow_stretch=7.5, band_sharpness=2.5,
                                  flake_intensity=0.08)

def paint_aurora_twilight_veil(paint, shape, mask, seed, pm, bb):
    """Twilight Veil — deep purple → rose gold → dusty pink → slate blue → dark magenta elegant"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 275, 0.78, 0.52),   # Deep Purple
        (0.25, 25,  0.55, 0.72),   # Rose Gold
        (0.50, 345, 0.48, 0.78),   # Dusty Pink
        (0.75, 220, 0.45, 0.60),   # Slate Blue
        (1.00, 305, 0.72, 0.48),   # Dark Magenta
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=10, flow_stretch=5.0, band_sharpness=1.2,
                                  flake_intensity=0.03)

def paint_aurora_dragon_fire(paint, shape, mask, seed, pm, bb):
    """Dragon Fire — WILD: bright orange → deep red → gold → black → surprise electric blue"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 25,  0.96, 0.88),   # Bright Orange
        (0.20, 5,   0.92, 0.65),   # Deep Red
        (0.40, 45,  0.90, 0.82),   # Gold
        (0.60, 0,   0.05, 0.12),   # Near-Black
        (0.80, 220, 0.95, 0.82),   # Electric Blue (surprise)
        (1.00, 25,  0.96, 0.88),   # Back to Orange
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=15, flow_stretch=6.0, band_sharpness=2.2,
                                  flake_intensity=0.06)

def paint_aurora_crystal_prism(paint, shape, mask, seed, pm, bb):
    """Crystal Prism — WILD: full rainbow red → orange → yellow → green → blue → violet spectrum"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 0,   0.92, 0.85),   # Red
        (0.17, 25,  0.90, 0.88),   # Orange
        (0.33, 58,  0.92, 0.90),   # Yellow
        (0.50, 118, 0.88, 0.82),   # Green
        (0.67, 215, 0.90, 0.80),   # Blue
        (0.83, 270, 0.85, 0.78),   # Violet
        (1.00, 0,   0.90, 0.84),   # Back to Red
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=17, flow_stretch=7.0, band_sharpness=2.0,
                                  flake_intensity=0.06)

def paint_aurora_shadow_silk(paint, shape, mask, seed, pm, bb):
    """Shadow Silk — very dark: black → dark purple → dark teal → charcoal → midnight blue luxury"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 0,   0.05, 0.10),   # Near-Black
        (0.25, 275, 0.65, 0.22),   # Dark Purple
        (0.50, 185, 0.60, 0.24),   # Dark Teal
        (0.75, 0,   0.05, 0.18),   # Charcoal
        (1.00, 230, 0.70, 0.20),   # Midnight Blue
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=9, flow_stretch=6.0, band_sharpness=1.0,
                                  flake_intensity=0.02, metallic_brighten=0.04)

def paint_aurora_copper_patina(paint, shape, mask, seed, pm, bb):
    """Copper Patina — copper → verdigris green → brown → teal → oxidized orange aged metal flow"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 22,  0.72, 0.65),   # Copper
        (0.25, 162, 0.58, 0.52),   # Verdigris Green
        (0.50, 28,  0.55, 0.40),   # Brown
        (0.75, 178, 0.62, 0.55),   # Teal
        (1.00, 18,  0.80, 0.60),   # Oxidized Orange
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=9, flow_stretch=4.5, band_sharpness=1.1,
                                  flake_intensity=0.03)

def paint_aurora_poison_ivy(paint, shape, mask, seed, pm, bb):
    """Poison Ivy — ULTRA WILD: toxic green → black → bright lime → dark emerald → acid yellow"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 112, 0.96, 0.82),   # Toxic Green
        (0.20, 0,   0.05, 0.10),   # Black
        (0.40, 90,  0.98, 0.90),   # Bright Lime
        (0.60, 145, 0.88, 0.42),   # Dark Emerald
        (0.80, 65,  0.98, 0.92),   # Acid Yellow
        (1.00, 112, 0.96, 0.82),   # Back to Toxic Green
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=16, flow_stretch=6.5, band_sharpness=2.3,
                                  flake_intensity=0.07)

def paint_aurora_champagne_dream(paint, shape, mask, seed, pm, bb):
    """Champagne Dream — pale gold → cream → blush pink → soft peach → pearl white luxurious"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 45,  0.45, 0.90),   # Pale Gold
        (0.25, 35,  0.15, 0.96),   # Cream
        (0.50, 348, 0.35, 0.92),   # Blush Pink
        (0.75, 22,  0.38, 0.94),   # Soft Peach
        (1.00, 0,   0.08, 0.97),   # Pearl White
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=8, flow_stretch=5.0, band_sharpness=0.8,
                                  flake_intensity=0.02, metallic_brighten=0.14)

def paint_aurora_thunderhead(paint, shape, mask, seed, pm, bb):
    """Thunderhead — steel grey → dark charcoal → silver flash → slate → gunmetal dramatic storm"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 210, 0.15, 0.62),   # Steel Grey
        (0.25, 215, 0.10, 0.30),   # Dark Charcoal
        (0.50, 210, 0.08, 0.80),   # Silver Flash
        (0.75, 218, 0.18, 0.50),   # Slate
        (1.00, 215, 0.12, 0.38),   # Gunmetal
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=10, flow_stretch=5.5, band_sharpness=1.4,
                                  flake_intensity=0.04)

def paint_aurora_coral_reef(paint, shape, mask, seed, pm, bb):
    """Coral Reef — coral pink → turquoise → sand gold → seafoam → deep blue tropical underwater"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 10,  0.78, 0.80),   # Coral Pink
        (0.25, 175, 0.80, 0.72),   # Turquoise
        (0.50, 42,  0.65, 0.78),   # Sand Gold
        (0.75, 158, 0.62, 0.76),   # Seafoam
        (1.00, 225, 0.82, 0.58),   # Deep Blue
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=10, flow_stretch=5.0, band_sharpness=1.0,
                                  flake_intensity=0.03)

def paint_aurora_black_rainbow(paint, shape, mask, seed, pm, bb):
    """Black Rainbow — WILD: dark versions of rainbow — dark red → dark orange → dark yellow → dark green → dark blue"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 0,   0.88, 0.38),   # Dark Red
        (0.17, 20,  0.85, 0.42),   # Dark Orange
        (0.33, 55,  0.82, 0.45),   # Dark Yellow
        (0.50, 118, 0.80, 0.38),   # Dark Green
        (0.67, 225, 0.85, 0.35),   # Dark Blue
        (0.83, 270, 0.80, 0.38),   # Dark Purple
        (1.00, 0,   0.86, 0.38),   # Back to Dark Red
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=14, flow_stretch=6.0, band_sharpness=2.0,
                                  flake_intensity=0.05, metallic_brighten=0.06)

def paint_aurora_cherry_blossom(paint, shape, mask, seed, pm, bb):
    """Cherry Blossom — soft pink → white → pale rose → light green → blush delicate spring"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 345, 0.42, 0.92),   # Soft Pink
        (0.25, 0,   0.05, 0.98),   # White
        (0.50, 355, 0.38, 0.90),   # Pale Rose
        (0.75, 110, 0.30, 0.88),   # Light Green
        (1.00, 340, 0.35, 0.94),   # Blush
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=8, flow_stretch=4.5, band_sharpness=0.7,
                                  flake_intensity=0.02, metallic_brighten=0.12)

def paint_aurora_plasma_reactor(paint, shape, mask, seed, pm, bb):
    """Plasma Reactor — ULTRA WILD: electric cyan → white-hot → purple → bright blue → magenta"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 185, 0.96, 0.88),   # Electric Cyan
        (0.20, 195, 0.10, 0.98),   # White-Hot
        (0.40, 278, 0.95, 0.80),   # Purple
        (0.60, 218, 0.96, 0.90),   # Bright Blue
        (0.80, 308, 0.95, 0.85),   # Magenta
        (1.00, 185, 0.96, 0.88),   # Back to Cyan
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=18, flow_stretch=7.0, band_sharpness=2.5,
                                  flake_intensity=0.08)

def paint_aurora_autumn_ember(paint, shape, mask, seed, pm, bb):
    """Autumn Ember — burnt orange → dark red → gold → maroon → brown fall foliage flow"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 22,  0.88, 0.72),   # Burnt Orange
        (0.25, 5,   0.85, 0.50),   # Dark Red
        (0.50, 42,  0.82, 0.78),   # Gold
        (0.75, 355, 0.78, 0.38),   # Maroon
        (1.00, 20,  0.65, 0.38),   # Brown
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=9, flow_stretch=4.5, band_sharpness=1.1,
                                  flake_intensity=0.03)

def paint_aurora_ice_crystal(paint, shape, mask, seed, pm, bb):
    """Ice Crystal — very pale blue → white → crystal clear → frost → pale cyan nearly-white ice"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 208, 0.30, 0.94),   # Very Pale Blue
        (0.25, 200, 0.06, 0.99),   # White
        (0.50, 195, 0.18, 0.97),   # Crystal Clear
        (0.75, 205, 0.25, 0.95),   # Frost
        (1.00, 190, 0.32, 0.93),   # Pale Cyan
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=8, flow_stretch=5.5, band_sharpness=0.7,
                                  flake_intensity=0.02, metallic_brighten=0.16)

def paint_aurora_supernova(paint, shape, mask, seed, pm, bb):
    """Supernova — ULTRA WILD: white-hot → orange → red → deep purple → black stellar explosion"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 55,  0.10, 0.99),   # White-Hot Core
        (0.20, 35,  0.90, 0.92),   # Orange
        (0.40, 5,   0.95, 0.72),   # Red
        (0.60, 275, 0.85, 0.45),   # Deep Purple
        (0.80, 0,   0.05, 0.08),   # Black
        (1.00, 55,  0.10, 0.99),   # Back to White-Hot
    ]
    return paint_aurora_flow_core(paint, shape, mask, seed, pm, bb, stops,
                                  num_bands=16, flow_stretch=7.5, band_sharpness=2.2,
                                  flake_intensity=0.07)


# ================================================================
# END OF engine/chameleon.py
# ================================================================
