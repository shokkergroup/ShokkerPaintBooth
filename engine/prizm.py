"""
engine/prizm.py - Prizm v4 Panel-Aware Color Shift System
==========================================================
ONE file. ALL prizm. Extracted from shokker_engine_v2.py.

Prizm simulates thin-film interference (soap bubble, oil slick, tempered steel).
Unlike Chameleon (HSV multi-stop ramp), Prizm uses panel-direction fields
mapped to physically-motivated spectral color sequences.

CONTENTS:
  _generate_panel_direction_field - dual-axis noise panel field
  _apply_color_ramp               - prizm-specific ramp application
  _add_micro_flake                - prizm micro-texture layer
  spec_prizm                      - coordinated prizm spec
  paint_prizm_core                - CORE prizm paint function (ALL presets call this)
  paint_prizm_holographic         - Full spectral rainbow sweep
  paint_prizm_midnight            - Purple → Teal → Gold
  paint_prizm_phoenix             - Red → Gold → Green
  paint_prizm_oceanic             - Teal → Blue → Purple → Magenta
  paint_prizm_ember               - Copper → Magenta → Purple
  paint_prizm_arctic              - Silver → Ice Blue → Teal
  paint_prizm_solar               - Gold → Orange → Red → Crimson
  paint_prizm_venom               - Green → Teal → Purple
  paint_prizm_mystichrome         - Green → Blue → Purple (Ford SVT tribute)
  paint_prizm_black_rainbow       - Dark base with vivid rainbow highlights
  paint_prizm_duochrome           - Clean two-color shift (teal ↔ purple)
  paint_prizm_iridescent          - Subtle pearlescent (low saturation)
  paint_prizm_adaptive            - Reads zone color, creates complementary ramp

DEPENDENCY INJECTION:
  Call integrate_prizm(engine_module) after import.

FIX GUIDE:
  "Wrong colors in prizm preset"      → find paint_prizm_XXX, fix rgb_stops
  "Alpha index crash in prizm"        → paint is always 3-channel RGB (fixed)
  "Prize spec doesn't match paint"    → spec_prizm uses same panel direction field
  "paint_prizm_adaptive reads wrong"  → _sample_zone_color_local samples zone avg
"""

import numpy as np
import colorsys

_engine = None  # Injected by shokker_engine_v2 after import


def integrate_prizm(engine_module):
    """Wire this module into the host engine. Called once at startup."""
    global _engine
    _engine = engine_module


def _msn(shape, scales, weights, seed):
    """Delegate multi_scale_noise to host engine."""
    return _engine.multi_scale_noise(shape, scales, weights, seed)


def get_mgrid(shape):
    """Delegate get_mgrid to host engine."""
    return _engine.get_mgrid(shape)


def hsv_to_rgb_vec(h, s, v):
    """Delegate hsv_to_rgb_vec to host engine."""
    return _engine.hsv_to_rgb_vec(h, s, v)


def _sample_zone_color_local(paint, mask):
    """Local zone color sampler for prizm_adaptive (no circular dep needed).

    Returns (hue, sat, val) 0-1 floats - the dominant color of the zone.
    """
    masked = paint * mask[:, :, np.newaxis]
    total = float(np.sum(mask)) + 1e-8
    avg_r = float(np.sum(masked[:, :, 0]) / total)
    avg_g = float(np.sum(masked[:, :, 1]) / total)
    avg_b = float(np.sum(masked[:, :, 2]) / total)
    h, s, v = colorsys.rgb_to_hsv(
        min(1.0, avg_r), min(1.0, avg_g), min(1.0, avg_b)
    )
    return h, s, v


# ================================================================
# ================================================================
# SHOKKER PRIZM v4 - Panel-Aware Color Shift System
#
# THE NEONIZM BREAKTHROUGH DECODED:
# Real color-shift illusion comes from painting DIFFERENT COLORS
# on DIFFERENT BODY PANELS based on their 3D orientation.
# When the camera orbits the car, different panels face the viewer,
# creating the perception of color change.
#
# HOW IT WORKS:
# 1. Generate a "panel direction field" - smooth 2D field encoding
#    simulated 3D surface orientation from UV coordinates.
#    On any car UV template:
#      - Top regions → hood/roof (face UP)
#      - Left/right regions → doors/quarters (face SIDE)
#      - Bottom/edge regions → bumpers/splitter (face FORWARD/DOWN)
# 2. Map a MULTI-COLOR RAMP through the direction field.
#    Each panel "direction" maps to a different point on the ramp.
# 3. Apply uniform high-metallic spec (M=220-235, R=10-20, CC=16-22).
#    The metallic PBR amplifies the color difference across panels.
# 4. Add subtle micro-flake noise for depth realism.
#
# WHY THIS BEATS v1-v3:
# - v1/v2: Sine-wave gradients → uniform repetitive pattern, no panel awareness
# - v3: Pixel dithering → visible noise/sparkle, Fresnel can't selectively suppress hues
# - v4: Panel-mapped colors → DIFFERENT panels = DIFFERENT colors = TRUE shift illusion
#
# The spec map is deliberately SIMPLE. The magic is in the PAINT.
# ================================================================


def _generate_panel_direction_field(shape, seed, flow_complexity=3):
    """Generate a smooth panel-orientation field for color shift mapping.

    Returns a normalized 0-1 field where different UV regions get different
    values based on their simulated 3D orientation. This field is then used
    to index into a color ramp.

    The field uses multiple directional components:
    - Primary diagonal flow (simulates top-left to bottom-right orientation change)
    - Vertical gradient (top=UP-facing, bottom=FORWARD-facing)
    - Horizontal gradient (left side vs right side)
    - Radial component (center vs edges)
    - Perlin noise for organic panel boundary breakup

    flow_complexity: 1=simple (2-axis), 2=moderate (3-axis), 3=rich (full 5-axis)
    """
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    # Normalized coordinates (0-1)
    yn = yf / max(h - 1, 1)
    xn = xf / max(w - 1, 1)

    rng = np.random.RandomState(seed + 7000)
    # Random rotation angles for the directional components
    # This ensures each seed creates a unique orientation mapping
    angles = rng.uniform(0, 2 * np.pi, 5)

    # Component 1: Primary diagonal sweep
    # Simulates the dominant orientation change across the car body
    a1 = angles[0]
    d1 = np.cos(a1) * yn + np.sin(a1) * xn
    field = d1 * 0.35

    if flow_complexity >= 2:
        # Component 2: Secondary cross-flow
        # Adds perpendicular variation (e.g., top vs bottom within a side panel)
        a2 = angles[1]
        d2 = np.cos(a2) * yn + np.sin(a2) * xn
        field = field + d2 * 0.25

    if flow_complexity >= 3:
        # Component 3: Radial component
        # Center of texture vs edges - simulates convex body panels
        cy, cx = 0.45 + rng.uniform(-0.1, 0.1), 0.50 + rng.uniform(-0.1, 0.1)
        dist = np.sqrt((yn - cy)**2 + (xn - cx)**2)
        field = field + dist * 0.20

        # Component 4: Low-frequency sine undulation
        # Adds organic curvature that prevents the field from being purely linear
        freq = 1.5 + rng.uniform(-0.3, 0.3)
        phase = angles[2]
        wave = np.sin((yn * np.cos(phase) + xn * np.sin(phase)) * freq * np.pi) * 0.12
        field = field + wave

        # Component 5: Perlin-scale noise for panel boundary breakup
        # Much lower than v1-v3 noise - just enough to make boundaries organic
        noise = _msn(shape, [64, 128, 256], [0.25, 0.40, 0.35], seed + 7001)
        field = field + noise * 0.06

    # Normalize to 0-1
    fmin, fmax = field.min(), field.max()
    field = (field - fmin) / (fmax - fmin + 1e-8)

    return field


def _apply_color_ramp(field, color_stops):
    """Map a 0-1 field through a multi-stop color ramp.

    color_stops: list of (position, H, S, V) where position is 0-1
                 H is in degrees (0-360), S and V are 0-1.
                 Must be sorted by position. At least 2 stops.

    Returns: (R, G, B) float32 arrays in 0-1 range.
    """
    # Sort stops by position
    stops = sorted(color_stops, key=lambda s: s[0])
    n = len(stops)
    h, w = field.shape

    # Convert all stop colors to RGB
    stop_rgbs = []
    for pos, hue, sat, val in stops:
        # Single-pixel HSV to RGB
        h_arr = np.array([[hue / 360.0]], dtype=np.float32)
        s_arr = np.array([[sat]], dtype=np.float32)
        v_arr = np.array([[val]], dtype=np.float32)
        r, g, b = hsv_to_rgb_vec(h_arr, s_arr, v_arr)
        stop_rgbs.append((float(r[0, 0]), float(g[0, 0]), float(b[0, 0])))

    # Initialize output
    out_r = np.zeros((h, w), dtype=np.float32)
    out_g = np.zeros((h, w), dtype=np.float32)
    out_b = np.zeros((h, w), dtype=np.float32)

    # For each adjacent pair of stops, interpolate
    for i in range(n - 1):
        p0 = stops[i][0]
        p1 = stops[i + 1][0]
        r0, g0, b0 = stop_rgbs[i]
        r1, g1, b1 = stop_rgbs[i + 1]

        # Which pixels fall in this segment?
        if i == 0:
            seg = field <= p1
        elif i == n - 2:
            seg = field > p0
        else:
            seg = (field > p0) & (field <= p1)

        if not np.any(seg):
            continue

        # Local interpolation factor (0 at p0, 1 at p1)
        span = max(p1 - p0, 1e-8)
        t = np.clip((field[seg] - p0) / span, 0, 1)

        # Smooth interpolation (smoothstep for natural transition)
        t = t * t * (3.0 - 2.0 * t)

        out_r[seg] = r0 + (r1 - r0) * t
        out_g[seg] = g0 + (g1 - g0) * t
        out_b[seg] = b0 + (b1 - b0) * t

    return out_r, out_g, out_b


def _add_micro_flake(paint_r, paint_g, paint_b, shape, seed, flake_intensity=0.03):
    """Add subtle micro-flake noise for paint depth.

    This simulates the metallic pigment variation in real paint.
    Very subtle (1-4% variation) - just enough to prevent perfectly flat color.
    """
    h, w = shape
    rng = np.random.RandomState(seed + 7100)

    # Multi-scale flake: medium cells + fine noise
    # Cell-based variation (like metallic flake particles)
    cell_size = 4
    ny, nx = max(1, h // cell_size), max(1, w // cell_size)
    cell_vals = rng.rand(ny + 1, nx + 1).astype(np.float32)
    yidx = np.clip(np.arange(h) // cell_size, 0, ny - 1).astype(int)
    xidx = np.clip(np.arange(w) // cell_size, 0, nx - 1).astype(int)
    flake = cell_vals[yidx[:, None], xidx[None, :]]

    # Add finer noise layer
    fine = rng.rand(h, w).astype(np.float32)
    flake = flake * 0.6 + fine * 0.4

    # Center around 0 and scale
    flake = (flake - 0.5) * 2.0 * flake_intensity

    # Apply as brightness variation (not hue shift - keep colors clean)
    paint_r = np.clip(paint_r + flake, 0, 1)
    paint_g = np.clip(paint_g + flake, 0, 1)
    paint_b = np.clip(paint_b + flake, 0, 1)

    return paint_r, paint_g, paint_b


# ================================================================
# PRIZM v4 CORE FUNCTIONS
# ================================================================

def spec_prizm(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=30):
    """Prizm v4 spec map - uniform high-metallic with subtle variation.

    CC SCALE: 16=max gloss, 17-255=progressively degraded.
    Default clearcoat=30: good coat with slight character (not showroom-perfect).
    Each preset overrides this to give its own coat personality.

    Metallic: High (220-235) - amplifies paint color through PBR Fresnel
    Roughness: Low (10-20) - smooth reflections for vivid color
    Clearcoat: 16-60 range across presets - variety of coat depth
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)

    # Base values with very light noise for realism
    noise = _msn(shape, [32, 64], [0.5, 0.5], seed + 7200)
    M_arr = metallic + noise * 4 * sm
    R_arr = roughness + noise * 3 * sm

    # Apply mask
    spec[:, :, 0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_arr * mask, 15, 255).astype(np.uint8)  # GGX floor
    spec[:, :, 2] = np.where(mask > 0.5, clearcoat, 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def paint_prizm_core(paint, shape, mask, seed, pm, bb,
                     color_stops, flow_complexity=3, flake_intensity=0.03,
                     blend_strength=0.92):
    """Prizm v4 CORE paint function - panel-aware multi-color ramp.

    This is the heart of the v4 system. It:
    1. Generates a panel direction field (simulated 3D orientation from UV)
    2. Maps a multi-color ramp through the direction field
    3. Adds micro-flake noise for depth
    4. Blends with the original paint at the specified strength

    color_stops: list of (position, H, S, V)
                 H in degrees, S/V in 0-1, position in 0-1
                 Example: [(0.0, 120, 0.85, 0.80),   # Green
                           (0.35, 200, 0.82, 0.78),  # Teal/Blue
                           (0.65, 270, 0.80, 0.75),  # Purple
                           (1.0, 320, 0.78, 0.72)]   # Magenta

    flow_complexity: 1-3, controls direction field richness
    flake_intensity: 0.0-0.10, metallic flake noise
    blend_strength: 0.0-1.0, how much to replace original paint
    """
    h, w = shape

    # Step 1: Generate panel direction field
    field = _generate_panel_direction_field(shape, seed, flow_complexity)

    # Step 2: Map colors through the direction field
    ramp_r, ramp_g, ramp_b = _apply_color_ramp(field, color_stops)

    # Step 3: Add micro-flake noise
    ramp_r, ramp_g, ramp_b = _add_micro_flake(ramp_r, ramp_g, ramp_b, shape, seed, flake_intensity)

    # Step 4: Compensate for iRacing metallic darkening
    # Metallic surfaces appear darker because PBR uses albedo as F0.
    # Brighten paint colors to compensate (same as Neonizm does).
    metallic_brighten = 0.10
    ramp_r = np.clip(ramp_r + metallic_brighten, 0, 1)
    ramp_g = np.clip(ramp_g + metallic_brighten, 0, 1)
    ramp_b = np.clip(ramp_b + metallic_brighten, 0, 1)

    # Step 5: Blend with original paint using mask
    blend = blend_strength * pm
    mask3 = mask[:, :, np.newaxis]

    # Paint is always 3-channel RGB - blend only the 3 channels
    shift_rgb = np.stack([ramp_r, ramp_g, ramp_b], axis=2)
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3

    # Brightness boost for dark source paints
    paint = np.clip(paint + bb * 1.0 * mask3, 0, 1)

    return paint


# ================================================================
# PRIZM v4 PRESETS - Physically Plausible Color Ramps
#
# Real thin-film interference follows spectral sequences:
# Low-order: Gold → Copper → Magenta → Purple → Blue
# Mid-order: Blue → Teal → Green → Yellow → Orange
# High-order: Full rainbow sweep
#
# Each preset defines a color ramp that follows these natural
# sequences, creating believable color-shift illusions.
# ================================================================

# --- Prizm: Holographic (Full rainbow sweep - the flagship effect) ---
def paint_prizm_holographic(paint, shape, mask, seed, pm, bb):
    """Holographic - Full rainbow sweep across panels (VIVID signature effect)"""
    stops = [
        (0.00, 350, 0.88, 0.85),  # Red-Pink (vivid)
        (0.18, 35,  0.90, 0.88),  # Gold (vivid)
        (0.36, 120, 0.88, 0.84),  # Green (vivid)
        (0.54, 190, 0.90, 0.82),  # Teal (vivid)
        (0.72, 250, 0.88, 0.80),  # Blue-Purple (vivid)
        (1.00, 310, 0.85, 0.84),  # Magenta (vivid)
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.04)

def spec_prizm_holographic(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=12, clearcoat=40)  # Holographic: wide vivid coat for max spectral depth

# --- Prizm: Midnight (Purple → Teal → Gold - dark luxury) ---
def paint_prizm_midnight(paint, shape, mask, seed, pm, bb):
    """Midnight - Purple to Teal to Gold (deep luxury shift)"""
    stops = [
        (0.00, 275, 0.82, 0.68),  # Deep Purple
        (0.40, 195, 0.85, 0.72),  # Teal
        (0.70, 165, 0.80, 0.75),  # Aqua
        (1.00, 48,  0.78, 0.80),  # Gold
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_midnight(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=14, clearcoat=35)  # Midnight: luxury depth coat

# --- Prizm: Phoenix (Red → Gold → Green - warm to cool transition) ---
def paint_prizm_phoenix(paint, shape, mask, seed, pm, bb):
    """Phoenix - Red to Gold to Green (fire-to-earth shift)"""
    stops = [
        (0.00, 5,   0.88, 0.80),  # Red
        (0.30, 30,  0.85, 0.84),  # Orange
        (0.55, 48,  0.82, 0.85),  # Gold
        (0.80, 85,  0.78, 0.80),  # Yellow-Green
        (1.00, 140, 0.75, 0.76),  # Green
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.03)

def spec_prizm_phoenix(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=38)  # Phoenix: energetic warm coat

# --- Prizm: Oceanic (Teal → Blue → Purple → Magenta - cool spectrum) ---
def paint_prizm_oceanic(paint, shape, mask, seed, pm, bb):
    """Oceanic - Teal to Blue to Purple to Magenta (deep sea shift)"""
    stops = [
        (0.00, 175, 0.85, 0.78),  # Teal
        (0.35, 220, 0.82, 0.74),  # Blue
        (0.65, 265, 0.80, 0.72),  # Purple
        (1.00, 320, 0.75, 0.76),  # Magenta
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_oceanic(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=12, clearcoat=32)  # Oceanic: flowing deep-sea coat

# --- Prizm: Ember (Copper → Magenta → Purple - warm metal) ---
def paint_prizm_ember(paint, shape, mask, seed, pm, bb):
    """Ember - Copper to Magenta to Purple (molten metal shift)"""
    stops = [
        (0.00, 25,  0.82, 0.82),  # Copper
        (0.35, 345, 0.78, 0.78),  # Rose
        (0.65, 310, 0.80, 0.74),  # Magenta
        (1.00, 270, 0.78, 0.70),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.03)

def spec_prizm_ember(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=225, roughness=16, clearcoat=55)  # Ember: heavily worn coat - molten metal burns the clear

# --- Prizm: Arctic (Silver → Ice Blue → Teal - cold metallic) ---
def paint_prizm_arctic(paint, shape, mask, seed, pm, bb):
    """Arctic - Silver to Ice Blue to Teal (frozen metal shift)"""
    stops = [
        (0.00, 210, 0.18, 0.88),  # Silver (low sat, high val)
        (0.30, 200, 0.45, 0.85),  # Ice Blue
        (0.60, 195, 0.68, 0.80),  # Sky Blue
        (1.00, 178, 0.75, 0.76),  # Teal
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=2, flake_intensity=0.02)

def spec_prizm_arctic(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=235, roughness=10, clearcoat=22)  # Arctic: crisp near-perfect frozen coat

# --- Prizm: Solar (Gold → Orange → Red → Crimson - sunset) ---
def paint_prizm_solar(paint, shape, mask, seed, pm, bb):
    """Solar - Gold to Orange to Red to Crimson (sunset shift)"""
    stops = [
        (0.00, 50,  0.82, 0.86),  # Gold
        (0.30, 35,  0.85, 0.84),  # Amber
        (0.55, 15,  0.88, 0.80),  # Orange-Red
        (0.80, 355, 0.85, 0.75),  # Red
        (1.00, 340, 0.80, 0.68),  # Crimson
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.03)

def spec_prizm_solar(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=222, roughness=16, clearcoat=45)  # Solar: sun-baked - slightly worn coat from heat

# --- Prizm: Venom (Green → Teal → Purple - toxic shift) ---
def paint_prizm_venom(paint, shape, mask, seed, pm, bb):
    """Venom - Green to Teal to Purple (toxic color shift)"""
    stops = [
        (0.00, 130, 0.85, 0.78),  # Bright Green
        (0.35, 165, 0.82, 0.76),  # Teal-Green
        (0.65, 210, 0.78, 0.74),  # Blue
        (1.00, 280, 0.80, 0.72),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_venom(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=14, clearcoat=48)  # Venom: acid-eat coat - worn and dangerous

# --- Prizm: Mystichrome (Green → Blue → Purple - Ford SVT tribute) ---
def paint_prizm_mystichrome(paint, shape, mask, seed, pm, bb):
    """Mystichrome - Green to Blue to Purple (Ford SVT Cobra tribute)"""
    stops = [
        (0.00, 140, 0.82, 0.76),  # Forest Green
        (0.30, 175, 0.80, 0.74),  # Teal
        (0.55, 220, 0.78, 0.72),  # Blue
        (0.80, 260, 0.80, 0.70),  # Indigo
        (1.00, 290, 0.78, 0.72),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_mystichrome(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=12, clearcoat=30)  # Mystichrome: premium swept coat

# --- Prizm: Black Rainbow (Dark base with rainbow highlights - Neonizm's signature product) ---
def paint_prizm_black_rainbow(paint, shape, mask, seed, pm, bb):
    """Black Rainbow - Dark base with vivid rainbow color shift"""
    stops = [
        (0.00, 350, 0.80, 0.65),  # Dark Red
        (0.16, 30,  0.82, 0.68),  # Dark Gold
        (0.33, 90,  0.78, 0.65),  # Dark Green
        (0.50, 180, 0.82, 0.62),  # Dark Teal
        (0.66, 240, 0.80, 0.60),  # Dark Blue
        (0.83, 290, 0.78, 0.62),  # Dark Purple
        (1.00, 340, 0.75, 0.64),  # Dark Magenta
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.035,
                            blend_strength=0.95)

def spec_prizm_black_rainbow(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=232, roughness=12, clearcoat=50)  # Black Rainbow: maximum coat drama on dark base

# --- Prizm: Duochrome (Two-color only - clean, minimal shift) ---
def paint_prizm_duochrome(paint, shape, mask, seed, pm, bb):
    """Duochrome - Clean two-color shift (teal ↔ purple)"""
    stops = [
        (0.00, 175, 0.85, 0.80),  # Teal
        (1.00, 280, 0.80, 0.75),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=2, flake_intensity=0.02)

def spec_prizm_duochrome(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=14, clearcoat=28)  # Duochrome: clean minimal coat - just enough

# --- Prizm: Iridescent (Subtle pearlescent - low saturation, high metallic) ---
def paint_prizm_iridescent(paint, shape, mask, seed, pm, bb):
    """Iridescent - Subtle pearl-like color shift (low saturation)"""
    stops = [
        (0.00, 200, 0.35, 0.88),  # Pearl Blue
        (0.25, 280, 0.30, 0.86),  # Pearl Lavender
        (0.50, 340, 0.32, 0.87),  # Pearl Pink
        (0.75, 40,  0.30, 0.89),  # Pearl Cream
        (1.00, 170, 0.33, 0.87),  # Pearl Aqua
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.015,
                            blend_strength=0.85)

def spec_prizm_iridescent(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=235, roughness=10, clearcoat=25)  # Iridescent: near-perfect pearl coat

# --- Prizm: Adaptive (reads zone color, creates shift from it) ---
def paint_prizm_adaptive(paint, shape, mask, seed, pm, bb):
    """Adaptive Prizm - reads zone color, generates complementary color ramp"""
    zone_hue, zone_sat, zone_val = _sample_zone_color_local(paint, mask)

    # If achromatic, inject a base hue
    if zone_sat < 0.15:
        zone_hue = 0.55  # Default to teal for grays
        zone_sat = 0.50

    h_deg = zone_hue * 360.0

    # Build a 4-stop ramp centered on the zone color
    # with complementary and analogous colors
    stops = [
        (0.00, h_deg % 360,         min(zone_sat + 0.15, 1.0), min(zone_val * 0.85 + 0.20, 0.90)),
        (0.33, (h_deg + 72) % 360,  min(zone_sat + 0.12, 1.0), min(zone_val * 0.85 + 0.18, 0.88)),
        (0.66, (h_deg + 144) % 360, min(zone_sat + 0.10, 1.0), min(zone_val * 0.85 + 0.16, 0.86)),
        (1.00, (h_deg + 216) % 360, min(zone_sat + 0.08, 1.0), min(zone_val * 0.85 + 0.18, 0.88)),
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_adaptive(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=14, clearcoat=35)  # Adaptive: mid coat - works with any zone color


# ================================================================
# END OF engine/prizm.py
# ================================================================
