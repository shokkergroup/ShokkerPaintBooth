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
import cv2
from collections import OrderedDict

_engine = None  # Injected by shokker_engine_v2 after import

# SPB-90 tick 56: was a single-entry cache (_PRIZM_CACHE_KEY/_VALUE) — every
# panel switch between any two Prizm finishes invalidated. Replaced with
# LRU OrderedDict sized to comfortably cover all 23 Prizm finishes.
_PRIZM_FIELD_CACHE: "OrderedDict" = OrderedDict()
_PRIZM_FIELD_CACHE_MAX = 32


def integrate_prizm(engine_module):
    """Wire this module into the host engine. Called once at startup."""
    global _engine
    _engine = engine_module


def _msn(shape, scales, weights, seed):
    """Multi-scale noise — use engine delegate if available, fall back to direct import."""
    if _engine is not None:
        return _engine.multi_scale_noise(shape, scales, weights, seed)
    from engine.core import multi_scale_noise
    return multi_scale_noise(shape, scales, weights, seed)


def get_mgrid(shape):
    """Get coordinate grid — use engine delegate if available, fall back to direct import."""
    if _engine is not None:
        return _engine.get_mgrid(shape)
    from engine.core import get_mgrid as _gm
    return _gm(shape)


def hsv_to_rgb_vec(h, s, v):
    """HSV to RGB — use engine delegate if available, fall back to direct import."""
    if _engine is not None:
        return _engine.hsv_to_rgb_vec(h, s, v)
    from engine.core import hsv_to_rgb_vec as _hsv
    return _hsv(h, s, v)


def _sample_zone_color_local(paint, mask):
    """Local zone color sampler for prizm_adaptive (no circular dep needed).

    Returns (hue, sat, val) 0-1 floats - the dominant color of the zone.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
# Panel-aware color-shift (reference technique decoded):
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
        noise = _msn(shape, [8, 16, 32], [0.25, 0.40, 0.35], seed + 7001)
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


_PRIZM_MATERIAL_PROFILES = {
    "adaptive":       {"m": 150, "mr": 72, "r": 34, "rr": 54, "cc": 42, "cr": 58, "motif": "sensor", "paint": "adaptive", "bright": 0.03},
    "alien_skin":     {"m": 118, "mr": 68, "r": 48, "rr": 64, "cc": 30, "cr": 72, "motif": "cell", "paint": "skin", "bright": 0.00},
    "arctic":         {"m": 92,  "mr": 54, "r": 72, "rr": 70, "cc": 20, "cr": 50, "motif": "ice", "paint": "frozen", "bright": 0.02},
    "aurora_shift":   {"m": 128, "mr": 78, "r": 28, "rr": 62, "cc": 46, "cr": 72, "motif": "curtain", "paint": "veil", "bright": 0.04},
    "black_rainbow":  {"m": 72,  "mr": 96, "r": 64, "rr": 88, "cc": 18, "cr": 80, "motif": "hidden_rainbow", "paint": "blackout", "bright": -0.12},
    "blood_moon":     {"m": 88,  "mr": 86, "r": 58, "rr": 82, "cc": 22, "cr": 68, "motif": "lunar", "paint": "eclipse", "bright": -0.06},
    "candy_paint":    {"m": 95,  "mr": 72, "r": 18, "rr": 44, "cc": 66, "cr": 84, "motif": "candy_drip", "paint": "candy", "bright": 0.05},
    "chrome_rose":    {"m": 188, "mr": 58, "r": 22, "rr": 46, "cc": 34, "cr": 60, "motif": "rose_vine", "paint": "rose_chrome", "bright": 0.03},
    "copper_flame":   {"m": 168, "mr": 62, "r": 38, "rr": 62, "cc": 26, "cr": 56, "motif": "flame", "paint": "oxide_heat", "bright": 0.01},
    "cosmos":         {"m": 82,  "mr": 84, "r": 42, "rr": 80, "cc": 24, "cr": 70, "motif": "orbit", "paint": "nebula", "bright": -0.03},
    "dark_matter":    {"m": 36,  "mr": 70, "r": 112, "rr": 84, "cc": 16, "cr": 50, "motif": "void", "paint": "void", "bright": -0.16},
    "deep_space":     {"m": 66,  "mr": 86, "r": 44, "rr": 78, "cc": 24, "cr": 78, "motif": "starfield", "paint": "deep_space", "bright": -0.04},
    "duochrome":      {"m": 132, "mr": 58, "r": 30, "rr": 42, "cc": 46, "cr": 54, "motif": "split_edge", "paint": "duo", "bright": 0.01},
    "ember":          {"m": 148, "mr": 62, "r": 42, "rr": 64, "cc": 22, "cr": 58, "motif": "ember", "paint": "molten", "bright": 0.02},
    "fire_ice":       {"m": 112, "mr": 88, "r": 32, "rr": 74, "cc": 36, "cr": 76, "motif": "thermal_crack", "paint": "fire_ice", "bright": 0.03},
    "galaxy_dust":    {"m": 92,  "mr": 88, "r": 52, "rr": 86, "cc": 26, "cr": 76, "motif": "starfield", "paint": "dust", "bright": 0.00},
    "holographic":    {"m": 138, "mr": 94, "r": 20, "rr": 56, "cc": 58, "cr": 88, "motif": "holo_glyph", "paint": "hologram", "bright": 0.05},
    "iridescent":     {"m": 56,  "mr": 48, "r": 24, "rr": 34, "cc": 74, "cr": 70, "motif": "pearl_shell", "paint": "pearl", "bright": 0.04},
    "midnight":       {"m": 92,  "mr": 76, "r": 36, "rr": 68, "cc": 34, "cr": 74, "motif": "city_glint", "paint": "midnight", "bright": -0.02},
    "mystichrome":    {"m": 118, "mr": 70, "r": 28, "rr": 52, "cc": 42, "cr": 64, "motif": "muscle_curve", "paint": "mystic", "bright": 0.02},
    "neon":           {"m": 84,  "mr": 64, "r": 18, "rr": 54, "cc": 68, "cr": 76, "motif": "neon_trace", "paint": "neon", "bright": 0.06},
    "oceanic":        {"m": 72,  "mr": 76, "r": 32, "rr": 72, "cc": 42, "cr": 76, "motif": "wave", "paint": "water", "bright": 0.02},
    "phoenix":        {"m": 126, "mr": 74, "r": 36, "rr": 68, "cc": 34, "cr": 70, "motif": "feather_flame", "paint": "phoenix", "bright": 0.03},
    "solar":          {"m": 132, "mr": 68, "r": 34, "rr": 64, "cc": 38, "cr": 66, "motif": "sun_ray", "paint": "solar", "bright": 0.04},
    "spectrum":       {"m": 104, "mr": 82, "r": 22, "rr": 62, "cc": 54, "cr": 82, "motif": "scan_prism", "paint": "spectrum", "bright": 0.05},
    "sunset_strip":   {"m": 94,  "mr": 72, "r": 40, "rr": 72, "cc": 32, "cr": 68, "motif": "street_glass", "paint": "sunset", "bright": 0.01},
    "titanium":       {"m": 176, "mr": 46, "r": 70, "rr": 70, "cc": 18, "cr": 44, "motif": "brushed_titanium", "paint": "titanium", "bright": -0.01},
    "toxic_waste":    {"m": 80,  "mr": 78, "r": 48, "rr": 76, "cc": 28, "cr": 72, "motif": "toxic_bubble", "paint": "toxic", "bright": 0.02},
    "venom":          {"m": 86,  "mr": 76, "r": 42, "rr": 74, "cc": 30, "cr": 72, "motif": "fang_edge", "paint": "venom", "bright": 0.02},
    "default":        {"m": 118, "mr": 66, "r": 34, "rr": 60, "cc": 38, "cr": 62, "motif": "microflake", "paint": "faceted", "bright": 0.02},
}


def _profile_from_spec_params(metallic, roughness, clearcoat):
    key = (int(metallic), int(roughness), int(clearcoat))
    return {
        (228, 12, 40): "holographic",
        (230, 14, 35): "midnight",
        (225, 14, 38): "phoenix",
        (228, 12, 32): "oceanic",
        (225, 16, 55): "ember",
        (235, 10, 22): "arctic",
        (222, 16, 45): "solar",
        (228, 14, 48): "venom",
        (230, 12, 30): "mystichrome",
        (232, 12, 50): "black_rainbow",
        (230, 14, 28): "duochrome",
        (235, 10, 25): "iridescent",
        (228, 14, 35): "adaptive",
        (240, 15, 22): "galaxy_dust",
        (230, 16, 28): "sunset_strip",
        (225, 18, 30): "toxic_waste",
        (248, 15, 20): "chrome_rose",
        (235, 15, 25): "deep_space",
        (220, 20, 30): "copper_flame",
        (215, 22, 32): "alien_skin",
        (210, 25, 35): "titanium",
        (232, 15, 24): "aurora_shift",
        (225, 16, 26): "candy_paint",
        (232, 10, 18): "neon",
        (228, 16, 14): "blood_moon",
        (225, 14, 18): "cosmos",
        (230, 18, 14): "dark_matter",
        (228, 12, 18): "fire_ice",
        (230, 11, 18): "spectrum",
    }.get(key, "default")


def _profile_from_stops(stops, flake_intensity, blend_strength):
    sig = (
        len(stops),
        int(round(stops[0][1])),
        int(round(stops[-1][1])),
        int(round(flake_intensity * 1000)),
        int(round(blend_strength * 100)),
    )
    return {
        (6, 350, 310, 40, 92): "holographic",
        (4, 275, 48, 25, 92): "midnight",
        (5, 5, 140, 30, 92): "phoenix",
        (4, 175, 320, 25, 92): "oceanic",
        (4, 25, 270, 30, 92): "ember",
        (4, 210, 178, 20, 92): "arctic",
        (5, 50, 340, 30, 92): "solar",
        (4, 130, 280, 25, 92): "venom",
        (5, 140, 290, 25, 92): "mystichrome",
        (7, 350, 340, 35, 95): "black_rainbow",
        (2, 175, 280, 20, 92): "duochrome",
        (5, 200, 170, 15, 85): "iridescent",
        (4, 270, 170, 35, 92): "galaxy_dust",
        (4, 25, 225, 30, 92): "sunset_strip",
        (4, 110, 275, 40, 92): "toxic_waste",
        (4, 0, 0, 20, 92): "chrome_rose",
        (4, 0, 0, 50, 92): "deep_space",
        (4, 25, 30, 40, 92): "copper_flame",
        (4, 90, 48, 30, 92): "alien_skin",
        (4, 215, 195, 20, 88): "titanium",
        (5, 145, 325, 35, 92): "aurora_shift",
        (4, 335, 178, 40, 92): "candy_paint",
        (5, 310, 75, 25, 92): "neon",
        (5, 355, 35, 35, 92): "blood_moon",
        (5, 270, 330, 30, 92): "cosmos",
        (4, 270, 280, 20, 92): "dark_matter",
        (5, 5, 220, 28, 92): "fire_ice",
        (7, 0, 290, 25, 92): "spectrum",
    }.get(sig, "default")


def _prizm_profile(profile):
    return _PRIZM_MATERIAL_PROFILES.get(profile or "default", _PRIZM_MATERIAL_PROFILES["default"])


def _cached_prizm_field_details(shape, seed, profile_name, flow_complexity):
    """LRU render cache (SPB-90 tick 56): covers cycling through all 23
    Prizm finishes without thrashing. Paint and spec are called back-to-back
    per finish, then user may switch finishes — keep recent entries warm.
    """
    key = (int(shape[0]), int(shape[1]), int(seed), str(profile_name), int(flow_complexity))
    cached = _PRIZM_FIELD_CACHE.get(key)
    if cached is not None:
        _PRIZM_FIELD_CACHE.move_to_end(key)
        return cached
    h, w = shape
    # SPB paint-finish perf loop 2026-05-31: these two dense motif profiles were just over 4s
    # at 2K. Their full-res nano/pin layer remains native; only the shared carrier drops.
    carrier_limit = 640 if str(profile_name) in {"galaxy_dust", "toxic_waste"} else 1024
    carrier_scale = min(1.0, float(carrier_limit) / float(max(h, w)))
    carrier_shape = (
        max(1, int(round(h * carrier_scale))),
        max(1, int(round(w * carrier_scale))),
    )
    field_small = _generate_panel_direction_field(carrier_shape, seed, flow_complexity).astype(np.float32)
    details_small = _material_detail_fields(carrier_shape, seed + 33, profile_name, field_small)
    field = _upsample_to_shape(field_small, shape)
    details = {name: _upsample_to_shape(value, shape) for name, value in details_small.items()}
    if carrier_scale < 1.0:
        rng = np.random.RandomState(seed + 9917)
        native = rng.rand(h, w).astype(np.float32)
        details["nano"] = native
        details["pin"] = np.maximum(details["pin"], (native > 0.994).astype(np.float32))
        details["fine"] = _normalize01(details["fine"] * 0.70 + native * 0.30)
        details["motif"] = np.clip(details["motif"] + details["pin"] * 0.34, 0.0, 1.0)
        details["facet"] = np.clip(details["facet"] + details["pin"] * 0.65, 0.0, 1.0)
    value = (field, details)
    _PRIZM_FIELD_CACHE[key] = value
    _PRIZM_FIELD_CACHE.move_to_end(key)
    while len(_PRIZM_FIELD_CACHE) > _PRIZM_FIELD_CACHE_MAX:
        _PRIZM_FIELD_CACHE.popitem(last=False)
    return value


def _ring_field(xn, yn, cx, cy, freq):
    dist = np.sqrt((xn - cx) ** 2 + (yn - cy) ** 2)
    return 1.0 - np.clip(np.abs(np.sin(dist * freq * np.pi)), 0.0, 1.0)


def _normalize01(arr):
    arr = arr.astype(np.float32, copy=False)
    amin = float(arr.min())
    amax = float(arr.max())
    return (arr - amin) / (amax - amin + 1e-8)


def _cell_noise(shape, rng, cell):
    h, w = shape
    cy = max(1, int(np.ceil(h / float(cell))))
    cx = max(1, int(np.ceil(w / float(cell))))
    vals = rng.rand(cy, cx).astype(np.float32)
    return np.repeat(np.repeat(vals, cell, axis=0), cell, axis=1)[:h, :w]


def _upsample_to_shape(arr, shape):
    h, w = shape
    ay, ax = arr.shape[:2]
    if (ay, ax) == (h, w):
        return arr.astype(np.float32, copy=False)
    return cv2.resize(
        np.asarray(arr, dtype=np.float32),
        (int(w), int(h)),
        interpolation=cv2.INTER_NEAREST,
    ).astype(np.float32, copy=False)


def _material_detail_fields(shape, seed, profile_name, field):
    h, w = shape
    y, x = get_mgrid(shape)
    yn = y.astype(np.float32) / max(h - 1, 1)
    xn = x.astype(np.float32) / max(w - 1, 1)
    rng = np.random.RandomState(seed + 8123)

    nano = rng.rand(h, w).astype(np.float32)
    cell3 = _cell_noise(shape, rng, 3)
    cell7 = _cell_noise(shape, rng, 7)
    cell15 = _cell_noise(shape, rng, 15)
    cell31 = _cell_noise(shape, rng, 31)
    fine = _normalize01(nano * 0.46 + cell3 * 0.30 + cell7 * 0.17 + cell15 * 0.07)
    grain = _normalize01(cell7 * 0.28 + cell15 * 0.40 + cell31 * 0.24 + nano * 0.08)

    # Not a generic stripe layer: these are material cues, mixed differently by profile.
    weave = (np.sin((xn * 92.0 + grain * 1.8) * np.pi) * np.sin((yn * 86.0 - fine * 1.4) * np.pi))
    weave = np.clip((weave + 1.0) * 0.5, 0.0, 1.0)
    shard = np.maximum(
        1.0 - np.abs(np.sin((xn * 13.0 + yn * 17.0 + fine * 1.5) * np.pi)) * 5.0,
        1.0 - np.abs(np.sin((xn * -19.0 + yn * 11.0 + grain) * np.pi)) * 4.5,
    )
    shard = np.clip(shard, 0.0, 1.0)
    ring_a = ((xn - (0.35 + rng.uniform(-0.15, 0.15))) ** 2 + (yn - (0.48 + rng.uniform(-0.16, 0.16))) ** 2)
    ring_b = ((xn - (0.70 + rng.uniform(-0.12, 0.12))) ** 2 + (yn - (0.58 + rng.uniform(-0.12, 0.12))) ** 2)
    rings = np.maximum(
        1.0 - np.clip(np.abs(np.sin(ring_a * 58.0 * np.pi)) * 3.8, 0.0, 1.0),
        1.0 - np.clip(np.abs(np.sin(ring_b * 46.0 * np.pi)) * 3.8, 0.0, 1.0),
    )
    waves = 1.0 - np.clip(np.abs(np.sin((yn * 22.0 + np.sin(xn * 9.0 + fine * 2.0)) * np.pi)) * 3.6, 0.0, 1.0)
    # SPB overnight 2026-05-27 tick 2 — denser pin/dots for car-scale optical punch
    dots = (nano > 0.972).astype(np.float32)
    bubbles = np.clip(
        (fine > 0.66).astype(np.float32) * 0.48
        + (grain > 0.64).astype(np.float32) * 0.30
        + rings * 0.22
        + dots * 0.85,
        0.0,
        1.0,
    )
    rays = 1.0 - np.clip(np.abs(np.sin((xn * 7.0 - yn * 5.0 + field * 2.0) * np.pi)) * 3.2, 0.0, 1.0)
    trace = np.clip((field > 0.46).astype(np.float32) * (field < 0.53).astype(np.float32) * (0.55 + fine), 0.0, 1.0)
    polish_a = rng.uniform(0.0, np.pi)
    polish = 1.0 - np.clip(
        np.abs(np.sin((xn * np.cos(polish_a) + yn * np.sin(polish_a) + fine * 0.16) * 142.0 * np.pi)) * 4.8,
        0.0,
        1.0,
    )
    hair = np.clip(polish * (0.45 + grain * 0.55), 0.0, 1.0)
    pin = ((nano > 0.988) | ((fine > 0.84) & (grain > 0.68))).astype(np.float32)
    facet = np.clip(shard * 0.45 + hair * 0.30 + pin * 0.85, 0.0, 1.0)

    motif = {
        "sensor": trace * 0.65 + dots,
        "cell": bubbles * 0.55 + weave * 0.25,
        "ice": shard * 0.68 + hair * 0.22 + pin * 0.70,
        "curtain": waves * 0.65 + trace * 0.45,
        "hidden_rainbow": trace * 0.7 + dots * 0.8,
        "lunar": rings * 0.8 + (fine > 0.50).astype(np.float32) * 0.25,
        "candy_drip": waves * 0.45 + bubbles * 0.35,
        "rose_vine": rings * 0.30 + trace * 0.42 + hair * 0.36 + pin * 0.60,
        "flame": waves * 0.58 + shard * 0.28 + pin * 0.85,
        "orbit": rings * 0.65 + dots * 1.0,
        "void": np.clip(1.0 - rings * 0.65 - fine * 0.35, 0.0, 1.0),
        "starfield": dots * 1.0 + rings * 0.35,
        "split_edge": trace * 0.8 + shard * 0.25,
        "ember": rays * 0.45 + shard * 0.35 + dots * 0.4,
        "thermal_crack": shard * 0.64 + waves * 0.22 + hair * 0.30 + pin * 0.72,
        "holo_glyph": trace * 0.55 + weave * 0.25 + dots,
        "pearl_shell": rings * 0.35 + waves * 0.45 + fine * 0.18,
        "city_glint": trace * 0.45 + dots * 0.9,
        "muscle_curve": waves * 0.4 + trace * 0.35 + dots * 0.5,
        "neon_trace": trace * 0.9 + dots,
        "wave": waves * 0.75 + rings * 0.25,
        "feather_flame": rays * 0.45 + waves * 0.35 + shard * 0.25,
        "sun_ray": rays * 0.75 + dots * 0.45,
        "scan_prism": trace * 0.55 + rays * 0.4 + dots * 0.8,
        "street_glass": shard * 0.45 + dots * 0.8,
        "brushed_titanium": weave * 0.55 + shard * 0.35,
        "toxic_bubble": bubbles * 0.70 + dots * 0.75,
        "fang_edge": shard * 0.55 + trace * 0.35,
        "microflake": fine * 0.35 + dots,
    }.get(_prizm_profile(profile_name)["motif"], fine * 0.35 + dots)

    motif = np.clip(motif, 0.0, 1.0)
    return {
        "fine": fine,
        "grain": grain,
        "nano": nano,
        "dots": dots,
        "pin": pin,
        "hair": hair,
        "facet": facet,
        "weave": weave,
        "shard": shard,
        "rings": rings,
        "waves": waves,
        "bubbles": bubbles,
        "rays": rays,
        "trace": trace,
        "motif": motif,
    }


def _apply_prizm_material_paint(shift_rgb, field, details, shape, seed, profile_name):
    p = _prizm_profile(profile_name)
    d = details
    motif = d["motif"][:, :, np.newaxis]
    fine = d["fine"][:, :, np.newaxis]
    nano = d["nano"][:, :, np.newaxis]
    dots = d["dots"][:, :, np.newaxis]
    hair = d["hair"][:, :, np.newaxis]
    pin = d["pin"][:, :, np.newaxis]
    facet = d["facet"][:, :, np.newaxis]
    shard = d["shard"][:, :, np.newaxis]
    rings = d["rings"][:, :, np.newaxis]
    waves = d["waves"][:, :, np.newaxis]
    bubbles = d["bubbles"][:, :, np.newaxis]
    trace = d["trace"][:, :, np.newaxis]
    paint_style = p["paint"]

    out = shift_rgb.astype(np.float32)
    out = np.clip(out + float(p["bright"]), 0.0, 1.0)

    if paint_style in {"blackout", "void", "eclipse", "deep_space"}:
        darken = {"blackout": 0.38, "void": 0.48, "eclipse": 0.30, "deep_space": 0.22}[paint_style]
        dust_lane = np.clip((1.0 - field[:, :, np.newaxis]) * motif * 0.55 + rings * 0.20 + hair * 0.18, 0.0, 1.0)
        star_pin = np.clip(pin * 1.15 + dots * 0.60 + facet * 0.20, 0.0, 1.0)
        out = out * (1.0 - darken * (0.58 + fine * 0.34) - rings * 0.035)
        if profile_name == "black_rainbow":
            out = np.clip(out + dust_lane * np.array([0.09, 0.035, 0.18], dtype=np.float32) + star_pin * np.array([0.12, 0.14, 0.24], dtype=np.float32), 0.0, 1.0)
        elif profile_name == "blood_moon":
            out = np.clip(out + dust_lane * np.array([0.13, 0.015, 0.035], dtype=np.float32) + star_pin * np.array([0.16, 0.06, 0.035], dtype=np.float32), 0.0, 1.0)
        else:
            out = np.clip(out + dust_lane * np.array([0.055, 0.035, 0.15], dtype=np.float32) + star_pin * np.array([0.14, 0.17, 0.26], dtype=np.float32), 0.0, 1.0)
    elif paint_style in {"frozen", "titanium"}:
        frost = shard if paint_style == "frozen" else d["weave"][:, :, np.newaxis]
        brushed = np.clip(hair * 0.60 + trace * 0.35 + pin * 0.25, 0.0, 1.0)
        out = np.clip(out * (0.86 + frost * 0.13) + frost * np.array([0.045, 0.070, 0.095], dtype=np.float32) + brushed * np.array([0.020, 0.035, 0.055], dtype=np.float32), 0.0, 1.0)
    elif paint_style in {"molten", "phoenix", "oxide_heat", "fire_ice", "solar"}:
        heat = np.maximum(d["rays"], np.maximum(d["waves"], d["shard"]))[:, :, np.newaxis]
        ember = np.clip(pin * 1.05 + dots * 0.55 + facet * 0.28, 0.0, 1.0)
        filament = np.clip(hair * 0.70 + trace * 0.30 + waves * 0.18, 0.0, 1.0)
        if profile_name == "fire_ice":
            cold = np.clip(shard * 0.70 + hair * 0.35 + (1.0 - field[:, :, np.newaxis]) * 0.18, 0.0, 1.0)
            hot = np.clip(heat * 0.65 + ember * 0.45 + field[:, :, np.newaxis] * 0.18, 0.0, 1.0)
            out = np.clip(out * 0.84 + hot * np.array([0.24, 0.070, 0.000], dtype=np.float32) + cold * np.array([0.065, 0.105, 0.145], dtype=np.float32) + filament * np.array([0.055, 0.025, 0.010], dtype=np.float32), 0.0, 1.0)
        elif profile_name == "solar":
            corona = np.clip(heat * 0.65 + rings * 0.22 + ember * 0.45, 0.0, 1.0)
            out = np.clip(out + corona * np.array([0.16, 0.105, 0.015], dtype=np.float32) + filament * np.array([0.055, 0.040, 0.000], dtype=np.float32), 0.0, 1.0)
        elif profile_name == "phoenix":
            feather = np.clip(waves * 0.45 + hair * 0.42 + facet * 0.30, 0.0, 1.0)
            out = np.clip(out + feather * np.array([0.14, 0.060, 0.005], dtype=np.float32) + ember * np.array([0.18, 0.075, 0.000], dtype=np.float32), 0.0, 1.0)
        elif profile_name == "copper_flame":
            scale = np.clip(facet * 0.52 + rings * 0.35 + trace * 0.26, 0.0, 1.0)
            out = np.clip(out + scale * np.array([0.15, 0.060, 0.015], dtype=np.float32) + ember * np.array([0.13, 0.045, 0.000], dtype=np.float32), 0.0, 1.0)
        else:
            out = np.clip(out + heat * np.array([0.11, 0.050, 0.000], dtype=np.float32) + ember * np.array([0.13, 0.055, 0.000], dtype=np.float32), 0.0, 1.0)
    elif paint_style in {"water", "veil"}:
        current = np.clip(waves * 0.70 + hair * 0.22 + pin * 0.24, 0.0, 1.0)
        out = np.clip(out + current * np.array([0.000, 0.050, 0.080], dtype=np.float32), 0.0, 1.0)
    elif paint_style in {"candy", "neon", "spectrum", "hologram"}:
        gloss_trace = np.clip(motif * 0.55 + trace * 0.25 + pin * 0.35, 0.0, 1.0)
        out = np.clip(out * (0.95 + motif * 0.08) + gloss_trace * np.array([0.065, 0.055, 0.080], dtype=np.float32) + dots * 0.075, 0.0, 1.0)
    elif paint_style in {"skin", "toxic", "venom"}:
        cell = np.clip(bubbles * 0.48 + rings * 0.22 + facet * 0.26 + hair * 0.12, 0.0, 1.0)
        pits = np.clip((1.0 - fine) * bubbles * 0.45 + pin * 0.38, 0.0, 1.0)
        if profile_name == "alien_skin":
            out = np.clip(out * (0.82 + cell * 0.18) + cell * np.array([0.035, 0.105, 0.035], dtype=np.float32) + pits * np.array([0.070, 0.050, 0.015], dtype=np.float32), 0.0, 1.0)
        elif profile_name == "toxic_waste":
            out = np.clip(out * (0.80 + cell * 0.16) + cell * np.array([0.015, 0.140, 0.010], dtype=np.float32) + pits * np.array([0.095, 0.105, 0.000], dtype=np.float32), 0.0, 1.0)
        else:
            out = np.clip(out * (0.84 + cell * 0.17) + cell * np.array([0.025, 0.080, 0.040], dtype=np.float32) + pits * np.array([0.075, 0.050, 0.010], dtype=np.float32), 0.0, 1.0)
    elif paint_style in {"nebula", "dust"}:
        starfield = np.clip(pin * 1.10 + dots * 0.72 + facet * 0.22, 0.0, 1.0)
        dust_lane = np.clip(motif * 0.45 + rings * 0.22 + hair * 0.24, 0.0, 1.0)
        out = np.clip(out * (0.84 + fine * 0.12) + dust_lane * np.array([0.060, 0.040, 0.125], dtype=np.float32) + starfield * np.array([0.21, 0.20, 0.27], dtype=np.float32), 0.0, 1.0)
    elif paint_style == "rose_chrome":
        out = np.clip(out + motif * np.array([0.08, 0.025, 0.04], dtype=np.float32), 0.0, 1.0)
    else:
        out = np.clip(out + motif * 0.035 + dots * 0.09, 0.0, 1.0)

    relief = (fine - 0.5) * 0.072 + (nano - 0.5) * 0.038 + (hair - 0.5) * 0.030
    if profile_name in {"galaxy_dust", "deep_space", "cosmos", "dark_matter"}:
        relief += pin * 0.16 + dots * 0.11 + rings * 0.030
        out = np.clip(out + pin * np.array([0.20, 0.20, 0.26], dtype=np.float32) + dots * np.array([0.13, 0.11, 0.18], dtype=np.float32), 0.0, 1.0)
    elif profile_name in {"fire_ice", "arctic"}:
        relief += shard * 0.075 + hair * 0.055 + pin * 0.080
        out = np.clip(out + shard * np.array([0.055, 0.075, 0.110], dtype=np.float32) + hair * np.array([0.030, 0.052, 0.085], dtype=np.float32), 0.0, 1.0)
    elif profile_name in {"solar", "phoenix", "copper_flame", "ember"}:
        relief += hair * 0.070 + pin * 0.095 + facet * 0.045
        out = np.clip(out + pin * np.array([0.20, 0.080, 0.000], dtype=np.float32) + hair * np.array([0.050, 0.030, 0.000], dtype=np.float32), 0.0, 1.0)
    elif profile_name in {"alien_skin", "toxic_waste", "venom"}:
        relief += bubbles * 0.070 + rings * 0.035 + pin * 0.070
        out = np.clip(out + bubbles * np.array([0.025, 0.085, 0.020], dtype=np.float32) + pin * np.array([0.095, 0.120, 0.018], dtype=np.float32), 0.0, 1.0)

    micro_carrier = relief + ((fine - 0.5) * 0.040 + (nano - 0.5) * 0.018)
    material_glint = (
        pin * np.array([0.11, 0.10, 0.12], dtype=np.float32)
        + hair * np.array([0.030, 0.026, 0.036], dtype=np.float32)
        + facet * np.array([0.026, 0.020, 0.030], dtype=np.float32)
    )
    if paint_style in {"frozen", "titanium"}:
        material_glint += hair * np.array([0.020, 0.034, 0.052], dtype=np.float32)
    elif paint_style in {"molten", "phoenix", "oxide_heat", "fire_ice", "solar"}:
        material_glint += pin * np.array([0.075, 0.030, 0.000], dtype=np.float32)
    elif paint_style in {"blackout", "void", "eclipse", "deep_space"}:
        material_glint += pin * np.array([0.040, 0.025, 0.080], dtype=np.float32)
    out = np.clip(
        out + micro_carrier * np.array([1.00, 0.92, 1.08], dtype=np.float32) + material_glint,
        0.0,
        1.0,
    )

    return out


# ================================================================
# PRIZM v4 CORE FUNCTIONS
# ================================================================

def spec_prizm(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=30, profile=None, flow_complexity=3):
    """Prizm v4 spec map — panel-aware and range-widened for stronger living flash.

    Compared to the old nearly-uniform coat, this version coordinates M/R/Cc to
    the same panel direction field used by paint, plus independent micro-octaves.
    """
    # SPB-90 tick 56: stale global declaration kept for backward compat; the
    # cache itself is now the LRU OrderedDict `_PRIZM_FIELD_CACHE`.
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    m = np.clip(mask.astype(np.float32), 0.0, 1.0)
    try:
        from engine import overnight_boost as _ob
    except Exception:
        class _ob:  # noqa: N801
            @staticmethod
            def wave_mult(b, k="spec"):
                return b

    profile_name = profile or _profile_from_spec_params(metallic, roughness, clearcoat)
    p = _prizm_profile(profile_name)

    # Reuse the panel direction field so spec follows the same macro flow as paint.
    field, details = _cached_prizm_field_details(shape, seed, profile_name, flow_complexity)
    f_center = np.clip(np.abs(field - 0.5) * 2.0, 0.0, 1.0)  # 0 near mid-panels, 1 near extremes
    motif = details["motif"]
    dots = details["dots"]
    hair = details["hair"]
    pin = details["pin"]
    facet = details["facet"]

    # Reuse paint-detail carriers instead of generating three more 2048 fields.
    noise_m = (details["fine"] - 0.5) * 2.0
    noise_r = (details["grain"] - 0.5) * 2.0
    noise_c = (details["nano"] - 0.5) * 2.0

    # Material-specific spec: not every Prizm finish is full chrome.
    M_arr = (
        float(p["m"])
        + (field - 0.5) * float(p["mr"]) * 0.75 * sm
        + noise_m * float(p["mr"]) * 0.22 * sm
        + motif * float(p["mr"]) * 0.42 * sm
        + facet * float(p["mr"]) * 0.20 * sm
        + hair * float(p["mr"]) * 0.16 * sm
        + dots * 38.0 * sm * _ob.wave_mult(1.0, "sparkle")
        + pin * 62.0 * sm * _ob.wave_mult(1.0, "glint")
    )

    # Roughness: opposing metallic trend with its own octave profile.
    R_arr = (
        float(p["r"])
        + (0.5 - field) * float(p["rr"]) * 0.42 * sm
        + noise_r * float(p["rr"]) * 0.24 * sm
        + (1.0 - motif) * float(p["rr"]) * 0.18 * sm
        + hair * float(p["rr"]) * 0.12 * sm
        - pin * 18.0 * sm
    )

    # Clearcoat pockets and satin valleys give angle-change discovery without a generic overlay.
    Cc_arr = (
        float(p["cc"])
        + noise_c * float(p["cr"]) * 0.20 * sm
        + motif * float(p["cr"]) * 0.55 * sm
        + facet * float(p["cr"]) * 0.18 * sm
        + hair * float(p["cr"]) * 0.22 * sm
        - f_center * float(p["cr"]) * 0.16 * sm
    )

    paint_style = p["paint"]
    if paint_style in {"candy", "neon", "spectrum", "hologram", "pearl"}:
        M_arr = M_arr * 0.70 + (pin + facet) * 24.0
        R_arr = R_arr * 0.88 + hair * 16.0
        Cc_arr = Cc_arr + 34.0 + motif * 18.0
    elif paint_style in {"frozen", "titanium"}:
        M_arr = M_arr * 0.64 + facet * 32.0 + pin * 34.0
        R_arr = R_arr + hair * 38.0 + details["shard"] * 18.0
        Cc_arr = Cc_arr + hair * 34.0 + pin * 26.0
    elif paint_style in {"skin", "toxic", "venom", "water", "veil"}:
        M_arr = M_arr * 0.72 + pin * 42.0
        R_arr = R_arr + details["bubbles"] * 28.0 + hair * 14.0
        Cc_arr = Cc_arr + motif * 30.0 + pin * 22.0
    elif paint_style in {"blackout", "void", "eclipse", "deep_space", "nebula", "dust"}:
        M_arr = M_arr * 0.62 + pin * 58.0 + facet * 18.0
        R_arr = R_arr + (1.0 - motif) * 24.0
        Cc_arr = Cc_arr + pin * 34.0 + hair * 20.0
    elif paint_style in {"rose_chrome", "oxide_heat", "molten", "phoenix", "fire_ice", "solar"}:
        Cc_arr = Cc_arr + hair * 18.0 + pin * 18.0

    sparkle = ((pin > 0.5) | ((noise_m > 0.54) & (motif > 0.55))) & (m > 0.4)
    M_arr = np.where(sparkle, M_arr + 24.0 * sm, M_arr)
    R_arr = np.where(sparkle, R_arr * 0.80 + 12.0, R_arr)
    Cc_arr = np.where(sparkle, Cc_arr + 22.0 * sm, Cc_arr)

    # Apply mask + legal packing constraints.
    spec[:, :, 0] = np.clip(M_arr * m, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.where(m > 0.01, np.clip(R_arr, 15, 255), 0).astype(np.uint8)
    spec[:, :, 2] = np.where(m > 0.5, np.clip(Cc_arr, 16, 255), 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    # SPB-90 tick 56: removed the explicit cache wipe-after-render here.
    # Original code cleared the single-entry cache to "release memory";
    # with the new LRU cache (max=32 entries) memory is bounded and
    # keeping entries warm yields ~25-100× warm-render speedup when the
    # same finish renders again later.
    return spec


def paint_prizm_core(paint, shape, mask, seed, pm, bb,
                     color_stops, flow_complexity=3, flake_intensity=0.03,
                     blend_strength=0.92, profile=None):
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    profile_name = profile or _profile_from_stops(color_stops, flake_intensity, blend_strength)

    # Step 1: Generate panel direction field
    field, details = _cached_prizm_field_details(shape, seed, profile_name, flow_complexity)

    # Step 2: Map colors through the direction field
    ramp_r, ramp_g, ramp_b = _apply_color_ramp(field, color_stops)

    # Step 3: Add micro-flake noise
    ramp_r, ramp_g, ramp_b = _add_micro_flake(ramp_r, ramp_g, ramp_b, shape, seed, flake_intensity)

    # Step 4: Compensate for material recipes without forcing every finish into chrome.
    metallic_brighten = 0.06
    ramp_r = np.clip(ramp_r + metallic_brighten, 0, 1)
    ramp_g = np.clip(ramp_g + metallic_brighten, 0, 1)
    ramp_b = np.clip(ramp_b + metallic_brighten, 0, 1)

    shift_rgb = np.stack([ramp_r, ramp_g, ramp_b], axis=2)
    shift_rgb = _apply_prizm_material_paint(shift_rgb, field, details, shape, seed, profile_name)

    # Step 5: Blend with original paint using mask
    blend = blend_strength * pm
    mask3 = mask[:, :, np.newaxis]

    # Paint is always 3-channel RGB - blend only the 3 channels
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3

    # Brightness boost for dark source paints
    bb_2d = np.mean(bb[:,:,:3], axis=2) if hasattr(bb, 'ndim') and bb.ndim == 3 else (bb if hasattr(bb, 'ndim') and bb.ndim == 2 else np.full(paint.shape[:2], float(np.mean(bb)), dtype=np.float32))
    paint = np.clip(paint + bb_2d[:,:,np.newaxis] * 1.0 * mask3, 0, 1)

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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 275, 0.82, 0.68),  # Deep Purple
        (0.40, 195, 0.85, 0.72),  # Teal
        (0.70, 165, 0.80, 0.75),  # Aqua
        (1.00, 48,  0.78, 0.80),  # Gold
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025, profile="adaptive")

def spec_prizm_midnight(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=14, clearcoat=35)  # Midnight: luxury depth coat

# --- Prizm: Phoenix (Red → Gold → Green - warm to cool transition) ---
def paint_prizm_phoenix(paint, shape, mask, seed, pm, bb):
    """Phoenix - Red to Gold to Green (fire-to-earth shift)"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 210, 0.18, 0.88),  # Silver (low sat, high val)
        (0.30, 200, 0.45, 0.85),  # Ice Blue
        (0.60, 195, 0.68, 0.80),  # Sky Blue
        (1.00, 178, 0.75, 0.76),  # Teal
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=2, flake_intensity=0.02)

def spec_prizm_arctic(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=235, roughness=10, clearcoat=22, flow_complexity=2)  # Arctic: crisp near-perfect frozen coat

# --- Prizm: Solar (Gold → Orange → Red → Crimson - sunset) ---
def paint_prizm_solar(paint, shape, mask, seed, pm, bb):
    """Solar - Gold to Orange to Red to Crimson (sunset shift)"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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

# --- Prizm: Black Rainbow (dark base with rainbow highlights) ---
def paint_prizm_black_rainbow(paint, shape, mask, seed, pm, bb):
    """Black Rainbow - Dark base with vivid rainbow color shift"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 175, 0.85, 0.80),  # Teal
        (1.00, 280, 0.80, 0.75),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=2, flake_intensity=0.02)

def spec_prizm_duochrome(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=14, clearcoat=28, flow_complexity=2)  # Duochrome: clean minimal coat - just enough

# --- Prizm: Iridescent (Subtle pearlescent - low saturation, high metallic) ---
def paint_prizm_iridescent(paint, shape, mask, seed, pm, bb):
    """Iridescent - Subtle pearl-like color shift (low saturation)"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
                            flow_complexity=3, flake_intensity=0.025, profile="adaptive")

def spec_prizm_adaptive(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=14, clearcoat=35)  # Adaptive: mid coat - works with any zone color


# ================================================================
# PRIZM WAVE 2 — 10 additional presets (previously JS-only, now wired)
# ================================================================

def paint_prizm_galaxy_dust(paint, shape, mask, seed, pm, bb):
    """Galaxy Dust — Purple → pink → white → teal angular sweep"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 270, 0.78, 0.50), (0.30, 315, 0.62, 0.62), (0.58, 330, 0.18, 0.72), (0.78, 195, 0.54, 0.58), (1.00, 170, 0.62, 0.56)]
    paint = paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=3, flake_intensity=0.04, profile="galaxy_dust", blend_strength=0.88)
    if max(shape) > 1024:
        # SPB paint-finish perf loop 2026-05-31: core dust profile already adds starfield/dust at 2K.
        return paint
    field, details = _cached_prizm_field_details(shape, seed, "galaxy_dust", 3)
    dust = np.clip(details["motif"] * 0.45 + details["rings"] * 0.22 + details["hair"] * 0.32, 0.0, 1.0)
    stars = np.clip(details["pin"] * 1.15 + details["dots"] * 0.80 + details["facet"] * 0.18, 0.0, 1.0)
    veil = np.clip((details["fine"] - 0.45) * 0.10 + dust * 0.08 + stars * 0.18, -0.06, 0.32)
    overlay = (
        veil[:, :, np.newaxis] * np.array([0.95, 0.86, 1.10], dtype=np.float32)
        + stars[:, :, np.newaxis] * np.array([0.16, 0.14, 0.22], dtype=np.float32)
        + dust[:, :, np.newaxis] * np.array([0.035, 0.020, 0.085], dtype=np.float32)
    )
    return np.clip(paint + overlay * mask[:, :, np.newaxis] * pm, 0.0, 1.0)

def spec_prizm_galaxy_dust(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=240, roughness=15, clearcoat=22)

def paint_prizm_sunset_strip(paint, shape, mask, seed, pm, bb):
    """Sunset Strip — Orange → magenta → violet → navy angular sweep"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 25, 0.88, 0.88), (0.35, 340, 0.80, 0.72), (0.65, 275, 0.75, 0.55), (1.00, 225, 0.85, 0.40)]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=3, flake_intensity=0.03)

def spec_prizm_sunset_strip(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=16, clearcoat=28)

def paint_prizm_toxic_waste(paint, shape, mask, seed, pm, bb):
    """Toxic Waste — Acid green → black → neon yellow → purple faceted shift"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 112, 0.88, 0.72), (0.26, 92, 0.74, 0.42), (0.48, 0, 0.0, 0.10), (0.72, 64, 0.86, 0.78), (1.00, 274, 0.72, 0.48)]
    paint = paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=2, flake_intensity=0.035, profile="toxic_waste", blend_strength=0.88)
    if max(shape) > 1024:
        # SPB paint-finish perf loop 2026-05-31: core toxic profile already carries bubbles/pits/pin detail at 2K.
        return paint
    field, details = _cached_prizm_field_details(shape, seed, "toxic_waste", 2)
    cells = np.clip(details["bubbles"] * 0.55 + details["rings"] * 0.28 + details["facet"] * 0.20, 0.0, 1.0)
    pits = np.clip((1.0 - details["fine"]) * details["bubbles"] * 0.55 + details["pin"] * 0.45, 0.0, 1.0)
    acid = np.clip(details["hair"] * 0.40 + details["pin"] * 0.70 + cells * 0.35, 0.0, 1.0)
    overlay = (
        cells[:, :, np.newaxis] * np.array([0.020, 0.105, 0.010], dtype=np.float32)
        + acid[:, :, np.newaxis] * np.array([0.105, 0.150, 0.000], dtype=np.float32)
        - pits[:, :, np.newaxis] * np.array([0.075, 0.050, 0.025], dtype=np.float32)
    )
    return np.clip(paint + overlay * mask[:, :, np.newaxis] * pm, 0.0, 1.0)

def spec_prizm_toxic_waste(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=225, roughness=18, clearcoat=30, flow_complexity=2)

def paint_prizm_chrome_rose(paint, shape, mask, seed, pm, bb):
    """Chrome Rose — Chrome silver → rose → pink → platinum faceted"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 0, 0.05, 0.85), (0.35, 350, 0.40, 0.72), (0.65, 345, 0.30, 0.78), (1.00, 0, 0.03, 0.88)]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=2, flake_intensity=0.02)

def spec_prizm_chrome_rose(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=248, roughness=15, clearcoat=20, flow_complexity=2)

def paint_prizm_deep_space(paint, shape, mask, seed, pm, bb):
    """Deep Space — Black → deep blue → purple → white flash angular"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 0, 0.0, 0.045), (0.30, 224, 0.82, 0.28), (0.58, 266, 0.72, 0.36), (0.82, 285, 0.45, 0.30), (1.00, 205, 0.28, 0.44)]
    paint = paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=3, flake_intensity=0.045, profile="deep_space", blend_strength=0.90)
    field, details = _cached_prizm_field_details(shape, seed, "deep_space", 3)
    stars = np.clip(details["pin"] * 1.35 + details["dots"] * 0.90 + details["facet"] * 0.15, 0.0, 1.0)
    dust = np.clip(details["motif"] * 0.38 + details["rings"] * 0.20 + details["hair"] * 0.25, 0.0, 1.0)
    void_mottle = np.clip((details["fine"] - 0.55) * 0.12 + dust * 0.06, -0.08, 0.18)
    overlay = (
        void_mottle[:, :, np.newaxis] * np.array([0.65, 0.80, 1.18], dtype=np.float32)
        + stars[:, :, np.newaxis] * np.array([0.13, 0.17, 0.25], dtype=np.float32)
        + dust[:, :, np.newaxis] * np.array([0.030, 0.018, 0.090], dtype=np.float32)
    )
    return np.clip(paint + overlay * mask[:, :, np.newaxis] * pm, 0.0, 1.0)

def spec_prizm_deep_space(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=235, roughness=15, clearcoat=25)

def paint_prizm_copper_flame(paint, shape, mask, seed, pm, bb):
    """Copper Flame — Copper → flame orange → dark red → bronze flowing"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 25, 0.72, 0.65), (0.35, 18, 0.88, 0.82), (0.65, 350, 0.82, 0.45), (1.00, 30, 0.68, 0.55)]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=2, flake_intensity=0.04)

def spec_prizm_copper_flame(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=220, roughness=20, clearcoat=30, flow_complexity=2)

def paint_prizm_alien_skin(paint, shape, mask, seed, pm, bb):
    """Alien Skin — Lime → teal → dark green → gold faceted shift"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 90, 0.85, 0.75), (0.35, 170, 0.78, 0.62), (0.65, 135, 0.80, 0.35), (1.00, 48, 0.82, 0.72)]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=2, flake_intensity=0.03)

def spec_prizm_alien_skin(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=215, roughness=22, clearcoat=32, flow_complexity=2)

def paint_prizm_titanium(paint, shape, mask, seed, pm, bb):
    """Titanium — Blue-grey → purple-grey → gold-grey → steel flowing"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 215, 0.18, 0.58), (0.35, 270, 0.15, 0.55), (0.65, 42, 0.20, 0.58), (1.00, 195, 0.12, 0.60)]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=3, flake_intensity=0.02, blend_strength=0.88)

def spec_prizm_titanium(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=210, roughness=25, clearcoat=35)

def paint_prizm_aurora_shift(paint, shape, mask, seed, pm, bb):
    """Aurora Shift — Northern lights colors in angular prizm style"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 145, 0.82, 0.72), (0.25, 185, 0.78, 0.70), (0.50, 230, 0.80, 0.65), (0.75, 275, 0.75, 0.55), (1.00, 325, 0.72, 0.65)]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=3, flake_intensity=0.035)

def spec_prizm_aurora_shift(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=232, roughness=15, clearcoat=24)

def paint_prizm_candy_paint(paint, shape, mask, seed, pm, bb):
    """Candy Paint — Hot pink → purple → blue → teal faceted shift"""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [(0.00, 335, 0.88, 0.82), (0.35, 275, 0.82, 0.58), (0.65, 220, 0.85, 0.70), (1.00, 178, 0.78, 0.62)]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops, flow_complexity=2, flake_intensity=0.04)

def spec_prizm_candy_paint(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=225, roughness=16, clearcoat=26, flow_complexity=2)


# --- Prizm expansion gap-fill IDs. Kept here so the whole picker category uses one source of truth. ---
def paint_prizm_neon(paint, shape, mask, seed, pm, bb):
    """Neon - fluorescent candy gloss with spec-only tube traces and hot pin sparks."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 310, 0.92, 0.85),
        (0.30, 350, 0.88, 0.82),
        (0.55, 175, 0.90, 0.84),
        (0.80, 130, 0.88, 0.82),
        (1.00, 75,  0.85, 0.86),
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025, profile="neon")

def spec_prizm_neon(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=232, roughness=10, clearcoat=18, profile="neon")


def paint_prizm_blood_moon(paint, shape, mask, seed, pm, bb):
    """Blood Moon - dark eclipse enamel with lunar spec rings and red glass pockets."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 355, 0.90, 0.65),
        (0.30, 10,  0.85, 0.55),
        (0.55, 0,   0.70, 0.30),
        (0.80, 20,  0.80, 0.50),
        (1.00, 35,  0.75, 0.60),
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.035, profile="blood_moon")

def spec_prizm_blood_moon(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=16, clearcoat=14, profile="blood_moon")


def paint_prizm_cosmos(paint, shape, mask, seed, pm, bb):
    """Cosmos - nebula pearl with buried orbit rings and star-dust spec events."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 270, 0.80, 0.55),
        (0.30, 240, 0.82, 0.50),
        (0.55, 195, 0.78, 0.58),
        (0.80, 290, 0.72, 0.62),
        (1.00, 330, 0.65, 0.65),
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.030, profile="cosmos")

def spec_prizm_cosmos(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=18, profile="cosmos")


def paint_prizm_dark_matter(paint, shape, mask, seed, pm, bb):
    """Dark Matter - matte void shift with tiny chrome singularity flecks."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 270, 0.60, 0.20),
        (0.35, 250, 0.55, 0.18),
        (0.65, 220, 0.50, 0.22),
        (1.00, 280, 0.45, 0.25),
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.020, profile="dark_matter")

def spec_prizm_dark_matter(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=18, clearcoat=14, profile="dark_matter")


def paint_prizm_fire_ice(paint, shape, mask, seed, pm, bb):
    """Fire & Ice - hot enamel cracking into frozen satin glass."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    field, details = _cached_prizm_field_details(shape, seed, "fire_ice", 3)
    h, w = shape
    y, x = get_mgrid(shape)
    yn = y.astype(np.float32) / max(h - 1, 1)
    xn = x.astype(np.float32) / max(w - 1, 1)

    split = np.clip((field + (xn - yn) * 0.07 + details["hair"] * 0.035 - 0.46) / 0.34, 0.0, 1.0)
    split = split * split * (3.0 - 2.0 * split)
    crack = np.clip(details["shard"] * 1.05 + details["hair"] * 0.55 + details["pin"] * 0.95, 0.0, 1.0)
    frost = np.clip(details["shard"] * 0.66 + details["waves"] * 0.22 + details["hair"] * 0.45 + details["pin"] * 0.96, 0.0, 1.0)
    ember = np.clip(details["waves"] * 0.42 + details["pin"] * 1.05 + details["fine"] * 0.40, 0.0, 1.0)

    fire = np.zeros((h, w, 3), dtype=np.float32)
    fire[:, :, 0] = np.clip(0.78 + ember * 0.22, 0.0, 1.0)
    fire[:, :, 1] = np.clip(0.08 + field * 0.28 + ember * 0.26, 0.0, 0.82)
    fire[:, :, 2] = np.clip(0.015 + crack * 0.035, 0.0, 0.18)

    ice = np.zeros((h, w, 3), dtype=np.float32)
    ice[:, :, 0] = np.clip(0.76 + frost * 0.22, 0.0, 1.0)
    ice[:, :, 1] = np.clip(0.90 + frost * 0.09, 0.0, 1.0)
    ice[:, :, 2] = np.clip(0.98 + details["dots"] * 0.02, 0.0, 1.0)
    ice = np.clip(ice + crack[:, :, np.newaxis] * np.array([0.02, 0.06, 0.12], dtype=np.float32), 0.0, 1.0)

    seam_glow = np.clip(1.0 - np.abs(split - 0.50) * 8.0, 0.0, 1.0)
    shift_rgb = fire * (1.0 - split[:, :, np.newaxis]) + ice * split[:, :, np.newaxis]
    shift_rgb = np.clip(
        shift_rgb
        + seam_glow[:, :, np.newaxis] * np.array([0.12, 0.09, 0.04], dtype=np.float32)
        + details["dots"][:, :, np.newaxis] * np.array([0.10, 0.12, 0.16], dtype=np.float32),
        0.0,
        1.0,
    )
    micro = (
        (details["fine"] - 0.5) * 0.090
        + (details["nano"] - 0.5) * 0.044
        + details["hair"] * 0.050
        + details["pin"] * 0.085
    )[:, :, np.newaxis]
    hot_mask = (1.0 - split)[:, :, np.newaxis]
    ice_mask = split[:, :, np.newaxis]
    shift_rgb = np.clip(
        shift_rgb
        + micro * np.array([1.00, 0.92, 1.08], dtype=np.float32)
        + crack[:, :, np.newaxis] * hot_mask * np.array([0.105, 0.060, 0.000], dtype=np.float32)
        + crack[:, :, np.newaxis] * ice_mask * np.array([0.035, 0.090, 0.155], dtype=np.float32)
        + details["hair"][:, :, np.newaxis] * ice_mask * np.array([0.020, 0.040, 0.075], dtype=np.float32),
        0.0,
        1.0,
    )
    dark_crackle = np.clip(crack * 0.35 + details["fine"] * 0.16, 0.0, 1.0)[:, :, np.newaxis]
    shift_rgb = np.clip(
        shift_rgb
        - dark_crackle * hot_mask * np.array([0.070, 0.030, 0.010], dtype=np.float32)
        - dark_crackle * ice_mask * np.array([0.018, 0.030, 0.045], dtype=np.float32)
        + details["pin"][:, :, np.newaxis] * np.array([0.105, 0.075, 0.080], dtype=np.float32),
        0.0,
        1.0,
    )

    mask3 = mask[:, :, np.newaxis]
    blend = 0.96 * pm
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3
    bb_2d = np.mean(bb[:,:,:3], axis=2) if hasattr(bb, 'ndim') and bb.ndim == 3 else (bb if hasattr(bb, 'ndim') and bb.ndim == 2 else np.full(paint.shape[:2], float(np.mean(bb)), dtype=np.float32))
    return np.clip(paint + bb_2d[:, :, np.newaxis] * 0.45 * mask3, 0, 1)

def spec_prizm_fire_ice(shape, mask, seed, sm):
    field, details = _cached_prizm_field_details(shape, seed, "fire_ice", 3)
    h, w = shape
    y, x = get_mgrid(shape)
    yn = y.astype(np.float32) / max(h - 1, 1)
    xn = x.astype(np.float32) / max(w - 1, 1)
    m = np.clip(mask.astype(np.float32), 0.0, 1.0)

    split = np.clip((field + (xn - yn) * 0.07 + details["hair"] * 0.035 - 0.46) / 0.34, 0.0, 1.0)
    split = split * split * (3.0 - 2.0 * split)
    seam = np.clip(1.0 - np.abs(split - 0.50) * 7.0, 0.0, 1.0)
    hot = (1.0 - split)
    ice = split
    crack = np.clip(details["shard"] * 0.92 + details["hair"] * 0.44 + details["pin"] * 0.90, 0.0, 1.0)
    frost = np.clip(details["shard"] * 0.46 + details["waves"] * 0.20 + details["hair"] * 0.42 + details["pin"] * 0.90, 0.0, 1.0)
    ember = np.clip(details["waves"] * 0.40 + details["pin"] * 0.90 + details["fine"] * 0.28, 0.0, 1.0)

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    M_arr = 58.0 + hot * (94.0 + ember * 78.0) + ice * (34.0 + frost * 82.0) + seam * 82.0
    R_arr = 24.0 + hot * (18.0 - ember * 10.0) + ice * (62.0 + frost * 70.0) + crack * 18.0
    Cc_arr = 30.0 + hot * (22.0 + ember * 20.0) + ice * (36.0 + frost * 58.0) + seam * 38.0
    sparkle = ((details["dots"] > 0.5) | (crack > 0.62)) & (m > 0.4)
    M_arr = np.where(sparkle, M_arr + 36.0, M_arr)
    Cc_arr = np.where(sparkle, Cc_arr * 0.42 + 16.0 * 0.58, Cc_arr)

    spec[:, :, 0] = np.clip(M_arr * m * sm, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.where(m > 0.01, np.clip(R_arr * sm, 15, 255), 0).astype(np.uint8)
    spec[:, :, 2] = np.where(m > 0.5, np.clip(Cc_arr * sm, 16, 255), 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    return spec


def paint_prizm_spectrum(paint, shape, mask, seed, pm, bb):
    """Spectrum - full rainbow wrap with scan-prism spec traces instead of flat chrome."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    stops = [
        (0.00, 0,   0.85, 0.82),
        (0.16, 30,  0.82, 0.84),
        (0.32, 55,  0.80, 0.86),
        (0.48, 120, 0.82, 0.78),
        (0.64, 200, 0.85, 0.76),
        (0.82, 260, 0.80, 0.74),
        (1.00, 290, 0.78, 0.76),
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025, profile="spectrum")

def spec_prizm_spectrum(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=11, clearcoat=18, profile="spectrum")


# ================================================================
# END OF engine/prizm.py
# ================================================================
