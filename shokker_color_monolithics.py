"""
Shokker Color Monolithics Generator
====================================
Generates ~260+ color-changing monolithic finishes from template functions.
These monolithics REPLACE paint color (not just tweak light behavior like bases).

Categories:
  1. Solid Color + Material  (~160)  20 colors × 8 materials
  2. Gradient Pairs          (~40)   two-color directional blends
  3. Color-Shift Duos        (~30)   angle-dependent two-tone shifts
  4. Multi-Color Patterns    (~25)   noise-driven multi-color effects

Integration: Called from shokker_engine_v2.py after 24K expansion.
"""

import numpy as np

# Will be set by integrate_color_monolithics() from engine module
_engine = None


# ================================================================
# COLOR PALETTE — 20 core colors (RGB 0-1 float)
# ================================================================
COLOR_PALETTE = {
    # === ORIGINAL 20 ===
    "racing_red":     (0.85, 0.08, 0.08),
    "fire_orange":    (0.95, 0.45, 0.05),
    "sunburst_yellow":(0.95, 0.85, 0.10),
    "lime_green":     (0.45, 0.90, 0.15),
    "forest_green":   (0.10, 0.45, 0.15),
    "teal":           (0.05, 0.65, 0.65),
    "sky_blue":       (0.30, 0.65, 0.95),
    "royal_blue":     (0.15, 0.25, 0.85),
    "navy":           (0.08, 0.08, 0.35),
    "purple":         (0.50, 0.12, 0.70),
    "violet":         (0.65, 0.20, 0.85),
    "hot_pink":       (0.95, 0.15, 0.55),
    "magenta":        (0.85, 0.05, 0.65),
    "white":          (0.95, 0.95, 0.95),
    "black":          (0.05, 0.05, 0.05),
    "gunmetal":       (0.28, 0.30, 0.32),
    "silver":         (0.78, 0.78, 0.80),
    "gold":           (0.85, 0.70, 0.25),
    "bronze":         (0.70, 0.45, 0.18),
    "copper":         (0.75, 0.42, 0.28),
    # === ICONIC RACING COLORS ===
    "grabber_blue":   (0.00, 0.44, 0.78),   # Ford Grabber Blue
    "hugger_orange":  (0.96, 0.47, 0.13),   # Chevy Hugger Orange
    "plum_crazy":     (0.44, 0.16, 0.60),   # Mopar Plum Crazy Purple
    "hemi_orange":    (0.93, 0.35, 0.08),   # Mopar Hemi Orange
    "torch_red":      (0.80, 0.02, 0.02),   # Chevy Torch Red
    "velocity_yellow":(0.98, 0.82, 0.00),   # Chevy Velocity Yellow
    "competition_yellow": (0.98, 0.90, 0.05),  # Classic racing yellow
    "british_racing_green": (0.00, 0.26, 0.15), # BRG
    "gulf_blue":      (0.27, 0.58, 0.82),   # Gulf Racing blue
    "gulf_orange":    (0.96, 0.55, 0.17),   # Gulf Racing orange
    "candy_apple_red":(0.72, 0.01, 0.04),   # Deep candy apple
    "arrest_me_red":  (0.90, 0.03, 0.05),   # Bright stop-sign red
    "midnight_blue":  (0.04, 0.06, 0.22),   # Deep night blue
    "charcoal":       (0.18, 0.18, 0.20),   # Dark neutral gray
    "cream":          (0.96, 0.94, 0.86),   # Vintage cream/ivory
    # === EXPANDED PALETTE (matches JS CLR_PALETTE) ===
    "crimson":        (0.71, 0.08, 0.16),
    "coral":          (1.00, 0.50, 0.31),
    "peach":          (1.00, 0.71, 0.51),
    "amber":          (1.00, 0.75, 0.00),
    "honey":          (0.92, 0.75, 0.33),
    "mint":           (0.60, 1.00, 0.60),
    "sage":           (0.51, 0.69, 0.51),
    "emerald":        (0.00, 0.61, 0.31),
    "jade":           (0.00, 0.66, 0.47),
    "aqua":           (0.00, 0.78, 0.78),
    "cobalt":         (0.00, 0.28, 0.67),
    "indigo":         (0.25, 0.00, 0.59),
    "lavender":       (0.71, 0.51, 0.90),
    "plum":           (0.56, 0.27, 0.52),
    "rose":           (1.00, 0.31, 0.47),
    "blush":          (0.94, 0.63, 0.67),
    "maroon":         (0.50, 0.00, 0.00),
    "burgundy":       (0.50, 0.00, 0.13),
    "chocolate":      (0.48, 0.25, 0.00),
    "ivory":          (1.00, 1.00, 0.94),
    "slate":          (0.44, 0.50, 0.56),
    "graphite":       (0.25, 0.25, 0.25),
    "pewter":         (0.59, 0.59, 0.65),
    "champagne":      (0.97, 0.91, 0.81),
    "titanium":       (0.53, 0.57, 0.61),
}


# ================================================================
# MATERIAL TEMPLATES — spec values (M, R, CC) + paint behavior
# ================================================================
# Each material: (metallic, roughness, clearcoat, paint_style)
# paint_style controls how the color is applied:
#   "solid"    = flat color replacement
#   "flake"    = add subtle metallic flake noise
#   "pearl"    = add pearlescent shimmer (slight hue shift)
#   "candy"    = transparent tinted layer over brightened base
#   "chrome"   = push toward bright reflective version of color
#   "flat"     = dead matte, zero sheen
MATERIAL_TEMPLATES = {
    "gloss":    {"M": 5,   "R": 20,  "CC": 16,  "style": "solid"},
    "matte":    {"M": 5,   "R": 180, "CC": 0,   "style": "solid"},
    "satin":    {"M": 15,  "R": 90,  "CC": 8,   "style": "solid"},
    "metallic": {"M": 200, "R": 50,  "CC": 16,  "style": "flake"},
    "pearl":    {"M": 99,  "R": 35,  "CC": 16,  "style": "pearl"},
    "candy":    {"M": 200, "R": 15,  "CC": 16,  "style": "candy"},
    "chrome":   {"M": 250, "R": 3,   "CC": 0,   "style": "chrome"},
    "flat":     {"M": 0,   "R": 230, "CC": 0,   "style": "flat"},
}


# ================================================================
# FACTORY: Solid Color + Material generators
# ================================================================

def _make_solid_spec(M, R, CC):
    """Factory: returns a spec_fn closure for given material values."""
    def spec_fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        # Apply material values where mask is active
        spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,2] = CC
        spec[:,:,3] = 255  # Full authority
        return spec
    return spec_fn


def _make_solid_paint(r, g, b, style="solid"):
    """Factory: returns a paint_fn closure that replaces paint with target color."""
    def paint_fn(paint, shape, mask, seed, pm, bb):
        m3 = mask[:,:,np.newaxis]
        blend = 0.92 * pm  # Strong replacement, pm scales it
        if style == "solid":
            # Direct color replacement
            paint[:,:,0] = paint[:,:,0] * (1 - m3[:,:,0] * blend) + r * m3[:,:,0] * blend
            paint[:,:,1] = paint[:,:,1] * (1 - m3[:,:,0] * blend) + g * m3[:,:,0] * blend
            paint[:,:,2] = paint[:,:,2] * (1 - m3[:,:,0] * blend) + b * m3[:,:,0] * blend
        elif style == "flat":
            # Same as solid but slightly darker for dead matte look
            dr, dg, db = r * 0.85, g * 0.85, b * 0.85
            paint[:,:,0] = paint[:,:,0] * (1 - m3[:,:,0] * blend) + dr * m3[:,:,0] * blend
            paint[:,:,1] = paint[:,:,1] * (1 - m3[:,:,0] * blend) + dg * m3[:,:,0] * blend
            paint[:,:,2] = paint[:,:,2] * (1 - m3[:,:,0] * blend) + db * m3[:,:,0] * blend
        elif style == "flake":
            # Color replacement + subtle metallic flake noise
            paint[:,:,0] = paint[:,:,0] * (1 - m3[:,:,0] * blend) + r * m3[:,:,0] * blend
            paint[:,:,1] = paint[:,:,1] * (1 - m3[:,:,0] * blend) + g * m3[:,:,0] * blend
            paint[:,:,2] = paint[:,:,2] * (1 - m3[:,:,0] * blend) + b * m3[:,:,0] * blend
            flake = _engine.multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + 7000)
            for c in range(3):
                paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.04 * pm * mask, 0, 1)
        elif style == "pearl":
            # Color replacement + pearlescent hue shift shimmer
            paint[:,:,0] = paint[:,:,0] * (1 - m3[:,:,0] * blend) + r * m3[:,:,0] * blend
            paint[:,:,1] = paint[:,:,1] * (1 - m3[:,:,0] * blend) + g * m3[:,:,0] * blend
            paint[:,:,2] = paint[:,:,2] * (1 - m3[:,:,0] * blend) + b * m3[:,:,0] * blend
            shimmer = _engine.multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 7100)
            # Shift hue slightly based on noise (pearlescent effect)
            paint[:,:,0] = np.clip(paint[:,:,0] + shimmer * 0.06 * pm * mask, 0, 1)
            paint[:,:,2] = np.clip(paint[:,:,2] - shimmer * 0.04 * pm * mask, 0, 1)
        elif style == "candy":
            # Brighten base first, then tint with transparent color layer
            bright = 0.70 * pm
            paint[:,:,0] = paint[:,:,0] * (1 - m3[:,:,0] * bright) + min(r * 1.3, 1.0) * m3[:,:,0] * bright
            paint[:,:,1] = paint[:,:,1] * (1 - m3[:,:,0] * bright) + min(g * 1.3, 1.0) * m3[:,:,0] * bright
            paint[:,:,2] = paint[:,:,2] * (1 - m3[:,:,0] * bright) + min(b * 1.3, 1.0) * m3[:,:,0] * bright
            # Add depth variation (candy has translucent depth)
            depth = _engine.multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 7200)
            tint = np.clip(depth * 0.08 * pm, -0.05, 0.05)
            for c in range(3):
                paint[:,:,c] = np.clip(paint[:,:,c] + tint * mask, 0, 1)
        elif style == "chrome":
            # Push toward bright reflective version of color
            cr, cg, cb = min(r + 0.3, 0.98), min(g + 0.3, 0.98), min(b + 0.3, 0.98)
            paint[:,:,0] = paint[:,:,0] * (1 - m3[:,:,0] * blend) + cr * m3[:,:,0] * blend
            paint[:,:,1] = paint[:,:,1] * (1 - m3[:,:,0] * blend) + cg * m3[:,:,0] * blend
            paint[:,:,2] = paint[:,:,2] * (1 - m3[:,:,0] * blend) + cb * m3[:,:,0] * blend
            # Add reflection noise
            refl = _engine.multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 7300)
            paint = np.clip(paint + refl[:,:,np.newaxis] * 0.04 * pm * m3, 0, 1)
        return paint
    return paint_fn


# ================================================================
# FACTORY: Gradient (two-color directional blend)
# ================================================================

def _make_gradient_spec(M=80, R=40, CC=16):
    """Gradient spec — moderate metallic for color visibility."""
    def spec_fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,2] = CC
        spec[:,:,3] = 255
        return spec
    return spec_fn


def _make_gradient_paint(r1, g1, b1, r2, g2, b2, direction="vertical"):
    """Factory: two-color gradient blend across the zone."""
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = shape
        m3 = mask[:,:,np.newaxis]
        blend = 0.88 * pm
        # Create gradient ramp 0-1
        if direction == "vertical":
            ramp = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
            ramp = np.broadcast_to(ramp, (h, w))
        elif direction == "horizontal":
            ramp = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
            ramp = np.broadcast_to(ramp, (h, w))
        elif direction == "diagonal":
            y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
            x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
            ramp = np.clip((y + x) / 2.0, 0, 1)
        else:  # radial
            cy, cx = h / 2, w / 2
            y, x = np.mgrid[0:h, 0:w].astype(np.float32)
            ramp = np.sqrt(((y - cy) / h) ** 2 + ((x - cx) / w) ** 2)
            ramp = np.clip(ramp / ramp.max(), 0, 1)
        # Add slight noise to soften banding
        noise = _engine.multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 7500)
        ramp = np.clip(ramp + noise * 0.08, 0, 1)
        inv = 1.0 - ramp
        # Blend colors
        tr = r1 * inv + r2 * ramp
        tg = g1 * inv + g2 * ramp
        tb = b1 * inv + b2 * ramp
        paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + tr * mask * blend
        paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + tg * mask * blend
        paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + tb * mask * blend
        return paint
    return paint_fn


# ================================================================
# FACTORY: Color-Shift Duo (angle-dependent two-tone)
# ================================================================

def _make_colorshift_spec_v5():
    """Color-shift v5 spec — coordinated field-driven M/R/CC variation."""
    def spec_fn(shape, mask, seed, sm):
        return _engine.spec_chameleon_v5(shape, mask, seed, sm,
                                          M_base=215, M_range=35,
                                          R_base=12, R_range=15,
                                          CC_base=14, CC_range=12)
    return spec_fn


def _make_colorshift_paint_v5(r1, g1, b1, r2, g2, b2):
    """V5 Color Shift Duo: two-color shift using panel orientation field +
    multi-stop HSV ramp + Voronoi micro-flake. Generates 5 color stops
    that smoothly transition between the two colors via a blended mid-tone.
    """
    def _rgb_to_hsv(r, g, b):
        """Convert single RGB float to HSV (H in degrees, S 0-1, V 0-1)."""
        mx = max(r, g, b)
        mn = min(r, g, b)
        v = mx
        d = mx - mn
        s = 0.0 if mx == 0 else d / mx
        if d == 0:
            h = 0.0
        elif mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h *= 60
        if h < 0: h += 360
        return h, s, v

    h1, s1, v1 = _rgb_to_hsv(r1, g1, b1)
    h2, s2, v2 = _rgb_to_hsv(r2, g2, b2)

    # Build 5 color stops: color1 → blend → mid → blend → color2
    dh = h2 - h1
    if dh > 180: dh -= 360
    if dh < -180: dh += 360
    h_mid = (h1 + dh * 0.5) % 360
    s_mid = (s1 + s2) * 0.5
    v_mid = max((v1 + v2) * 0.5, 0.55)

    stops = [
        (0.00, h1, min(s1 + 0.10, 1.0), min(v1 * 0.95 + 0.15, 0.94)),
        (0.25, (h1 + dh * 0.20) % 360, min(s1 + 0.05, 1.0), min(v1 * 0.90 + 0.18, 0.94)),
        (0.50, h_mid, min(s_mid + 0.08, 1.0), min(v_mid + 0.10, 0.94)),
        (0.75, (h1 + dh * 0.80) % 360, min(s2 + 0.05, 1.0), min(v2 * 0.90 + 0.18, 0.94)),
        (1.00, h2, min(s2 + 0.10, 1.0), min(v2 * 0.95 + 0.15, 0.94)),
    ]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _engine.paint_chameleon_v5_core(
            paint, shape, mask, seed, pm, bb, stops,
            flow_complexity=3,
            flake_intensity=0.035,
            flake_hue_spread=0.05,
            blend_strength=0.90,
            metallic_brighten=0.10
        )
    return paint_fn


# ================================================================
# FACTORY: Multi-Color Pattern (noise-driven 3+ color blends)
# ================================================================

def _make_multicolor_spec(M=150, R=45, CC=16):
    """Multi-color pattern spec."""
    def spec_fn(shape, mask, seed, sm):
        spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
        spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
        spec[:,:,2] = CC
        spec[:,:,3] = 255
        return spec
    return spec_fn


def _make_multicolor_paint(colors, pattern_type="swirl"):
    """Factory: noise-driven multi-color pattern.
    colors: list of (r,g,b) tuples (3-4 colors)
    pattern_type: swirl, camo, marble, splatter
    """
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = shape
        blend = 0.85 * pm
        n_colors = len(colors)
        if pattern_type == "swirl":
            n1 = _engine.multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8000)
            n2 = _engine.multi_scale_noise(shape, [8, 24, 48], [0.3, 0.4, 0.3], seed + 8100)
            # Combine noises to create swirl zones
            zone_map = np.clip((n1 + n2 + 1) * 0.5, 0, 0.999)
            zone_idx = (zone_map * n_colors).astype(int)
        elif pattern_type == "camo":
            n1 = _engine.multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 8200)
            # Hard-edge camo blobs
            zone_map = np.clip((n1 + 1) * 0.5, 0, 0.999)
            zone_idx = (zone_map * n_colors).astype(int)
        elif pattern_type == "marble":
            n1 = _engine.multi_scale_noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 8300)
            y, x = _engine.get_mgrid((h, w))
            # Marble veining effect
            vein = np.sin((y / h * 4 + n1 * 3) * np.pi)
            zone_map = np.clip((vein + 1) * 0.5, 0, 0.999)
            zone_idx = (zone_map * n_colors).astype(int)
        else:  # splatter
            n1 = _engine.multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 8400)
            zone_map = np.clip((n1 + 1) * 0.5, 0, 0.999)
            zone_idx = (zone_map * n_colors).astype(int)

        # Build target color arrays from zone indices
        tr = np.zeros((h, w), dtype=np.float32)
        tg = np.zeros((h, w), dtype=np.float32)
        tb = np.zeros((h, w), dtype=np.float32)
        for i, (cr, cg, cb) in enumerate(colors):
            where = (zone_idx == i)
            tr[where] = cr
            tg[where] = cg
            tb[where] = cb

        paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + tr * mask * blend
        paint[:,:,1] = paint[:,:,1] * (1 - mask * blend) + tg * mask * blend
        paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + tb * mask * blend
        return paint
    return paint_fn


# ================================================================
# CATALOG BUILDER — generates all entries
# ================================================================

def _build_solid_color_entries():
    """Generate ~160 solid color + material monolithics."""
    entries = {}
    for color_name, (r, g, b) in COLOR_PALETTE.items():
        for mat_name, mat in MATERIAL_TEMPLATES.items():
            key = f"clr_{color_name}_{mat_name}"
            spec_fn = _make_solid_spec(mat["M"], mat["R"], mat["CC"])
            paint_fn = _make_solid_paint(r, g, b, mat["style"])
            entries[key] = (spec_fn, paint_fn)
    return entries


def _build_gradient_entries():
    """Generate ~40 gradient pair monolithics."""
    GRADIENT_PAIRS = [
        # (name, color1, color2, direction)
        ("fire_fade",        "racing_red",     "fire_orange",     "vertical"),
        ("sunset",           "fire_orange",    "sunburst_yellow", "vertical"),
        ("ocean_depths",     "sky_blue",       "navy",            "vertical"),
        ("forest_canopy",    "lime_green",     "forest_green",    "vertical"),
        ("twilight",         "purple",         "navy",            "vertical"),
        ("lava_flow",        "racing_red",     "sunburst_yellow", "vertical"),
        ("arctic_dawn",      "white",          "sky_blue",        "vertical"),
        ("midnight_ember",   "black",          "racing_red",      "vertical"),
        ("golden_hour",      "gold",           "fire_orange",     "vertical"),
        ("steel_forge",      "silver",         "gunmetal",        "vertical"),
        ("copper_patina",    "copper",         "teal",            "vertical"),
        ("neon_rush",        "hot_pink",       "lime_green",      "vertical"),
        ("bruise",           "purple",         "black",           "vertical"),
        ("ice_fire",         "sky_blue",       "racing_red",      "vertical"),
        ("toxic_waste",      "lime_green",     "sunburst_yellow", "vertical"),
        # Horizontal variants
        ("fire_fade_h",      "racing_red",     "fire_orange",     "horizontal"),
        ("ocean_depths_h",   "sky_blue",       "navy",            "horizontal"),
        ("twilight_h",       "purple",         "navy",            "horizontal"),
        ("golden_hour_h",    "gold",           "fire_orange",     "horizontal"),
        ("neon_rush_h",      "hot_pink",       "lime_green",      "horizontal"),
        # Diagonal variants
        ("fire_fade_diag",   "racing_red",     "fire_orange",     "diagonal"),
        ("ocean_depths_diag","sky_blue",       "navy",            "diagonal"),
        ("sunset_diag",      "fire_orange",    "sunburst_yellow", "diagonal"),
        ("twilight_diag",    "purple",         "navy",            "diagonal"),
        # Radial variants
        ("fire_vortex",      "racing_red",     "sunburst_yellow", "radial"),
        ("blue_vortex",      "sky_blue",       "navy",            "radial"),
        ("gold_vortex",      "gold",           "black",           "radial"),
        ("green_vortex",     "lime_green",     "forest_green",    "radial"),
        ("pink_vortex",      "hot_pink",       "purple",          "radial"),
        ("white_vortex",     "white",          "gunmetal",        "radial"),
        ("shadow_vortex",    "gunmetal",       "black",           "radial"),
        ("copper_vortex",    "copper",         "bronze",          "radial"),
        ("violet_vortex",    "violet",         "navy",            "radial"),
        ("teal_vortex",      "teal",           "forest_green",    "radial"),
    ]
    entries = {}
    grad_spec = _make_gradient_spec()
    for name, c1_name, c2_name, direction in GRADIENT_PAIRS:
        r1, g1, b1 = COLOR_PALETTE[c1_name]
        r2, g2, b2 = COLOR_PALETTE[c2_name]
        key = f"grad_{name}"
        paint_fn = _make_gradient_paint(r1, g1, b1, r2, g2, b2, direction)
        entries[key] = (grad_spec, paint_fn)
    return entries


def _build_colorshift_entries():
    """Generate all 75 color-shift duo monolithics using the v5 engine.
    This list MUST match the CS_DUO_DEFS in paint-booth-v2.html exactly.
    """
    COLORSHIFT_DUOS = [
        # === ORIGINAL 25 (from HTML lines 7200-7224) ===
        ("cs_fire_ice",         "racing_red",       "sky_blue"),
        ("cs_sunset_ocean",     "fire_orange",      "royal_blue"),
        ("cs_gold_emerald",     "gold",             "forest_green"),
        ("cs_copper_teal",      "copper",           "teal"),
        ("cs_pink_purple",      "hot_pink",         "purple"),
        ("cs_lime_blue",        "lime_green",       "royal_blue"),
        ("cs_red_gold",         "racing_red",       "gold"),
        ("cs_navy_silver",      "navy",             "silver"),
        ("cs_violet_teal",      "violet",           "teal"),
        ("cs_bronze_green",     "bronze",           "forest_green"),
        ("cs_black_red",        "black",            "racing_red"),
        ("cs_white_blue",       "white",            "royal_blue"),
        ("cs_magenta_gold",     "magenta",          "gold"),
        ("cs_gunmetal_orange",  "gunmetal",         "fire_orange"),
        ("cs_purple_lime",      "purple",           "lime_green"),
        ("cs_navy_gold",        "navy",             "gold"),
        ("cs_teal_pink",        "teal",             "hot_pink"),
        ("cs_red_black",        "racing_red",       "black"),
        ("cs_blue_orange",      "royal_blue",       "fire_orange"),
        ("cs_silver_purple",    "silver",           "purple"),
        ("cs_green_gold",       "forest_green",     "gold"),
        ("cs_bronze_navy",      "bronze",           "navy"),
        ("cs_copper_violet",    "copper",           "violet"),
        ("cs_yellow_blue",      "sunburst_yellow",  "royal_blue"),
        ("cs_pink_teal",        "hot_pink",         "teal"),
        # === BATCH 2: 30 more (from HTML lines 7226-7255) ===
        ("cs_orange_purple",    "fire_orange",      "purple"),
        ("cs_gold_navy",        "gold",             "navy"),
        ("cs_lime_pink",        "lime_green",       "hot_pink"),
        ("cs_copper_blue",      "copper",           "royal_blue"),
        ("cs_white_red",        "white",            "racing_red"),
        ("cs_black_gold",       "black",            "gold"),
        ("cs_silver_red",       "silver",           "racing_red"),
        ("cs_teal_orange",      "teal",             "fire_orange"),
        ("cs_purple_gold",      "purple",           "gold"),
        ("cs_navy_orange",      "navy",             "fire_orange"),
        ("cs_green_blue",       "forest_green",     "royal_blue"),
        ("cs_bronze_red",       "bronze",           "racing_red"),
        ("cs_violet_gold",      "violet",           "gold"),
        ("cs_magenta_teal",     "magenta",          "teal"),
        ("cs_gunmetal_lime",    "gunmetal",         "lime_green"),
        ("cs_black_blue",       "black",            "royal_blue"),
        ("cs_white_green",      "white",            "forest_green"),
        ("cs_copper_gold",      "copper",           "gold"),
        ("cs_red_purple",       "racing_red",       "purple"),
        ("cs_sky_gold",         "sky_blue",         "gold"),
        ("cs_orange_navy",      "fire_orange",      "navy"),
        ("cs_lime_violet",      "lime_green",       "violet"),
        ("cs_silver_teal",      "silver",           "teal"),
        ("cs_bronze_purple",    "bronze",           "purple"),
        ("cs_pink_gold",        "hot_pink",         "gold"),
        ("cs_black_silver",     "black",            "silver"),
        ("cs_white_purple",     "white",            "purple"),
        ("cs_copper_lime",      "copper",           "lime_green"),
        ("cs_magenta_blue",     "magenta",          "royal_blue"),
        ("cs_gunmetal_gold",    "gunmetal",         "gold"),
        # === EXPANSION: 20 new (from HTML lines 7257-7276) ===
        ("cs_crimson_jade",     "crimson",          "jade"),
        ("cs_coral_cobalt",     "coral",            "cobalt"),
        ("cs_amber_indigo",     "amber",            "indigo"),
        ("cs_honey_plum",       "honey",            "plum"),
        ("cs_mint_maroon",      "mint",             "maroon"),
        ("cs_rose_emerald",     "rose",             "emerald"),
        ("cs_slate_amber",      "slate",            "amber"),
        ("cs_champagne_cobalt", "champagne",        "cobalt"),
        ("cs_titanium_crimson", "titanium",         "crimson"),
        ("cs_lavender_jade",    "lavender",         "jade"),
        ("cs_charcoal_honey",   "charcoal",         "honey"),
        ("cs_ivory_indigo",     "ivory",            "indigo"),
        ("cs_peach_cobalt",     "peach",            "cobalt"),
        ("cs_sage_crimson",     "sage",             "crimson"),
        ("cs_blush_emerald",    "blush",            "emerald"),
        ("cs_burgundy_gold",    "burgundy",         "gold"),
        ("cs_chocolate_mint",   "chocolate",        "mint"),
        ("cs_pewter_rose",      "pewter",           "rose"),
        ("cs_graphite_coral",   "graphite",         "coral"),
        ("cs_aqua_maroon",      "aqua",             "maroon"),
    ]
    entries = {}
    cs_spec = _make_colorshift_spec_v5()
    for name, c1_name, c2_name in COLORSHIFT_DUOS:
        r1, g1, b1 = COLOR_PALETTE[c1_name]
        r2, g2, b2 = COLOR_PALETTE[c2_name]
        paint_fn = _make_colorshift_paint_v5(r1, g1, b1, r2, g2, b2)
        entries[name] = (cs_spec, paint_fn)
    return entries


def _build_multicolor_entries():
    """Generate ~25 multi-color pattern monolithics."""
    P = COLOR_PALETTE  # shorthand
    MULTICOLOR_DEFS = [
        # (name, [colors], pattern_type)
        ("mc_usa_flag",      [P["racing_red"], P["white"], P["royal_blue"]],           "swirl"),
        ("mc_rasta",         [P["racing_red"], P["sunburst_yellow"], P["forest_green"]],"swirl"),
        ("mc_halloween",     [P["fire_orange"], P["black"], P["purple"]],              "swirl"),
        ("mc_christmas",     [P["racing_red"], P["forest_green"], P["gold"]],          "swirl"),
        ("mc_miami_vice",    [P["hot_pink"], P["teal"], P["white"]],                   "swirl"),
        ("mc_fire_storm",    [P["racing_red"], P["fire_orange"], P["sunburst_yellow"]],"swirl"),
        ("mc_deep_space",    [P["navy"], P["purple"], P["black"]],                     "swirl"),
        ("mc_tropical",      [P["lime_green"], P["teal"], P["sunburst_yellow"]],       "swirl"),
        ("mc_vaporwave",     [P["hot_pink"], P["purple"], P["sky_blue"]],              "swirl"),
        ("mc_earth_tone",    [P["bronze"], P["copper"], P["gold"]],                    "swirl"),
        # Camo patterns
        ("mc_woodland_camo", [P["forest_green"], P["bronze"], P["black"]],             "camo"),
        ("mc_desert_camo",   [P["bronze"], P["sunburst_yellow"], P["gunmetal"]],       "camo"),
        ("mc_urban_camo",    [P["gunmetal"], P["silver"], P["black"]],                 "camo"),
        ("mc_snow_camo",     [P["white"], P["silver"], P["sky_blue"]],                 "camo"),
        ("mc_neon_camo",     [P["lime_green"], P["hot_pink"], P["black"]],             "camo"),
        ("mc_blue_camo",     [P["royal_blue"], P["navy"], P["sky_blue"]],              "camo"),
        # Marble patterns
        ("mc_white_marble",  [P["white"], P["silver"], P["gunmetal"]],                 "marble"),
        ("mc_black_marble",  [P["black"], P["gunmetal"], P["silver"]],                 "marble"),
        ("mc_green_marble",  [P["forest_green"], P["teal"], P["black"]],               "marble"),
        ("mc_red_marble",    [P["racing_red"], P["black"], P["gunmetal"]],             "marble"),
        ("mc_gold_marble",   [P["gold"], P["bronze"], P["black"]],                     "marble"),
        # Splatter patterns
        ("mc_paint_splat",   [P["racing_red"], P["royal_blue"], P["sunburst_yellow"], P["lime_green"]], "splatter"),
        ("mc_ink_splat",     [P["black"], P["gunmetal"], P["white"]],                  "splatter"),
        ("mc_neon_splat",    [P["hot_pink"], P["lime_green"], P["sky_blue"], P["sunburst_yellow"]], "splatter"),
        ("mc_blood_splat",   [P["racing_red"], P["black"], P["gunmetal"]],             "splatter"),
    ]
    entries = {}
    mc_spec = _make_multicolor_spec()
    for name, colors, ptype in MULTICOLOR_DEFS:
        paint_fn = _make_multicolor_paint(colors, ptype)
        entries[name] = (mc_spec, paint_fn)
    return entries


# ================================================================
# UI METADATA — for swatch display & categorization
# ================================================================

def get_color_monolithic_metadata():
    """Returns metadata dict for each color monolithic entry.
    Used by the UI to show proper swatches, names, and categories.
    Format: {key: {"name": display_name, "category": cat, "swatch": [r,g,b] or [[r,g,b],[r,g,b]]}}
    """
    meta = {}

    # Solid Color + Material entries
    COLOR_DISPLAY = {
        "racing_red": "Racing Red", "fire_orange": "Fire Orange",
        "sunburst_yellow": "Sunburst Yellow", "lime_green": "Lime Green",
        "forest_green": "Forest Green", "teal": "Teal",
        "sky_blue": "Sky Blue", "royal_blue": "Royal Blue",
        "navy": "Navy", "purple": "Purple", "violet": "Violet",
        "hot_pink": "Hot Pink", "magenta": "Magenta",
        "white": "White", "black": "Black", "gunmetal": "Gunmetal",
        "silver": "Silver", "gold": "Gold", "bronze": "Bronze", "copper": "Copper",
    }
    MAT_DISPLAY = {
        "gloss": "Gloss", "matte": "Matte", "satin": "Satin",
        "metallic": "Metallic", "pearl": "Pearl", "candy": "Candy",
        "chrome": "Chrome", "flat": "Flat",
    }
    for color_name, (r, g, b) in COLOR_PALETTE.items():
        for mat_name in MATERIAL_TEMPLATES:
            key = f"clr_{color_name}_{mat_name}"
            cdisp = COLOR_DISPLAY.get(color_name, color_name.replace("_", " ").title())
            mdisp = MAT_DISPLAY.get(mat_name, mat_name.title())
            meta[key] = {
                "name": f"{cdisp} {mdisp}",
                "category": f"Solid {mdisp}",
                "swatch": [int(r*255), int(g*255), int(b*255)],
            }

    # Gradient entries — swatch shows both colors
    GRADIENT_DISPLAY = {
        "fire_fade": ("Fire Fade", "racing_red", "fire_orange"),
        "sunset": ("Sunset", "fire_orange", "sunburst_yellow"),
        "ocean_depths": ("Ocean Depths", "sky_blue", "navy"),
        "forest_canopy": ("Forest Canopy", "lime_green", "forest_green"),
        "twilight": ("Twilight", "purple", "navy"),
        "lava_flow": ("Lava Flow", "racing_red", "sunburst_yellow"),
        "arctic_dawn": ("Arctic Dawn", "white", "sky_blue"),
        "midnight_ember": ("Midnight Ember", "black", "racing_red"),
        "golden_hour": ("Golden Hour", "gold", "fire_orange"),
        "steel_forge": ("Steel Forge", "silver", "gunmetal"),
        "copper_patina": ("Copper Patina", "copper", "teal"),
        "neon_rush": ("Neon Rush", "hot_pink", "lime_green"),
        "bruise": ("Bruise", "purple", "black"),
        "ice_fire": ("Ice & Fire", "sky_blue", "racing_red"),
        "toxic_waste": ("Toxic Waste", "lime_green", "sunburst_yellow"),
    }
    DIR_SUFFIX = {"": " V", "_h": " H", "_diag": " D", "_diag": " D"}
    for base_name, (display, c1, c2) in GRADIENT_DISPLAY.items():
        r1, g1, b1 = COLOR_PALETTE[c1]
        r2, g2, b2 = COLOR_PALETTE[c2]
        sw1 = [int(r1*255), int(g1*255), int(b1*255)]
        sw2 = [int(r2*255), int(g2*255), int(b2*255)]
        # Vertical (base)
        meta[f"grad_{base_name}"] = {
            "name": display, "category": "Gradient",
            "swatch": [sw1, sw2],
        }
        # Horizontal variant
        if f"grad_{base_name}_h" in _all_keys_cache:
            meta[f"grad_{base_name}_h"] = {
                "name": f"{display} H", "category": "Gradient",
                "swatch": [sw1, sw2],
            }
        # Diagonal variant
        if f"grad_{base_name}_diag" in _all_keys_cache:
            meta[f"grad_{base_name}_diag"] = {
                "name": f"{display} Diag", "category": "Gradient",
                "swatch": [sw1, sw2],
            }

    # Radial vortex variants
    VORTEX_DISPLAY = {
        "fire_vortex": ("Fire Vortex", "racing_red", "sunburst_yellow"),
        "blue_vortex": ("Blue Vortex", "sky_blue", "navy"),
        "gold_vortex": ("Gold Vortex", "gold", "black"),
        "green_vortex": ("Green Vortex", "lime_green", "forest_green"),
        "pink_vortex": ("Pink Vortex", "hot_pink", "purple"),
        "white_vortex": ("White Vortex", "white", "gunmetal"),
        "shadow_vortex": ("Shadow Vortex", "gunmetal", "black"),
        "copper_vortex": ("Copper Vortex", "copper", "bronze"),
        "violet_vortex": ("Violet Vortex", "violet", "navy"),
        "teal_vortex": ("Teal Vortex", "teal", "forest_green"),
    }
    for base_name, (display, c1, c2) in VORTEX_DISPLAY.items():
        r1, g1, b1 = COLOR_PALETTE[c1]
        r2, g2, b2 = COLOR_PALETTE[c2]
        meta[f"grad_{base_name}"] = {
            "name": display, "category": "Gradient Radial",
            "swatch": [[int(r1*255),int(g1*255),int(b1*255)],
                        [int(r2*255),int(g2*255),int(b2*255)]],
        }

    # Color-Shift Duo entries — auto-generate from build data
    # Pull the COLORSHIFT_DUOS from _build_colorshift_entries to stay in sync
    _CS_DUOS_META = [
        # === ORIGINAL 25 ===
        ("cs_fire_ice", "Fire & Ice", "racing_red", "sky_blue"),
        ("cs_sunset_ocean", "Sunset Ocean", "fire_orange", "royal_blue"),
        ("cs_gold_emerald", "Gold Emerald", "gold", "forest_green"),
        ("cs_copper_teal", "Copper Teal", "copper", "teal"),
        ("cs_pink_purple", "Pink Purple", "hot_pink", "purple"),
        ("cs_lime_blue", "Lime Blue", "lime_green", "royal_blue"),
        ("cs_red_gold", "Red Gold", "racing_red", "gold"),
        ("cs_navy_silver", "Navy Silver", "navy", "silver"),
        ("cs_violet_teal", "Violet Teal", "violet", "teal"),
        ("cs_bronze_green", "Bronze Green", "bronze", "forest_green"),
        ("cs_black_red", "Black Red", "black", "racing_red"),
        ("cs_white_blue", "White Blue", "white", "royal_blue"),
        ("cs_magenta_gold", "Magenta Gold", "magenta", "gold"),
        ("cs_gunmetal_orange", "Gunmetal Orange", "gunmetal", "fire_orange"),
        ("cs_purple_lime", "Purple Lime", "purple", "lime_green"),
        ("cs_navy_gold", "Navy Gold", "navy", "gold"),
        ("cs_teal_pink", "Teal Pink", "teal", "hot_pink"),
        ("cs_red_black", "Red Black", "racing_red", "black"),
        ("cs_blue_orange", "Blue Orange", "royal_blue", "fire_orange"),
        ("cs_silver_purple", "Silver Purple", "silver", "purple"),
        ("cs_green_gold", "Green Gold", "forest_green", "gold"),
        ("cs_bronze_navy", "Bronze Navy", "bronze", "navy"),
        ("cs_copper_violet", "Copper Violet", "copper", "violet"),
        ("cs_yellow_blue", "Yellow Blue", "sunburst_yellow", "royal_blue"),
        ("cs_pink_teal", "Pink Teal", "hot_pink", "teal"),
        # === BATCH 2: 30 more ===
        ("cs_orange_purple", "Orange Purple", "fire_orange", "purple"),
        ("cs_gold_navy", "Gold Navy", "gold", "navy"),
        ("cs_lime_pink", "Lime Pink", "lime_green", "hot_pink"),
        ("cs_copper_blue", "Copper Blue", "copper", "royal_blue"),
        ("cs_white_red", "White Red", "white", "racing_red"),
        ("cs_black_gold", "Black Gold", "black", "gold"),
        ("cs_silver_red", "Silver Red", "silver", "racing_red"),
        ("cs_teal_orange", "Teal Orange", "teal", "fire_orange"),
        ("cs_purple_gold", "Purple Gold", "purple", "gold"),
        ("cs_navy_orange", "Navy Orange", "navy", "fire_orange"),
        ("cs_green_blue", "Green Blue", "forest_green", "royal_blue"),
        ("cs_bronze_red", "Bronze Red", "bronze", "racing_red"),
        ("cs_violet_gold", "Violet Gold", "violet", "gold"),
        ("cs_magenta_teal", "Magenta Teal", "magenta", "teal"),
        ("cs_gunmetal_lime", "Gunmetal Lime", "gunmetal", "lime_green"),
        ("cs_black_blue", "Black Blue", "black", "royal_blue"),
        ("cs_white_green", "White Green", "white", "forest_green"),
        ("cs_copper_gold", "Copper Gold", "copper", "gold"),
        ("cs_red_purple", "Red Purple", "racing_red", "purple"),
        ("cs_sky_gold", "Sky Gold", "sky_blue", "gold"),
        ("cs_orange_navy", "Orange Navy", "fire_orange", "navy"),
        ("cs_lime_violet", "Lime Violet", "lime_green", "violet"),
        ("cs_silver_teal", "Silver Teal", "silver", "teal"),
        ("cs_bronze_purple", "Bronze Purple", "bronze", "purple"),
        ("cs_pink_gold", "Pink Gold", "hot_pink", "gold"),
        ("cs_black_silver", "Black Silver", "black", "silver"),
        ("cs_white_purple", "White Purple", "white", "purple"),
        ("cs_copper_lime", "Copper Lime", "copper", "lime_green"),
        ("cs_magenta_blue", "Magenta Blue", "magenta", "royal_blue"),
        ("cs_gunmetal_gold", "Gunmetal Gold", "gunmetal", "gold"),
        # === EXPANSION: 20 new ===
        ("cs_crimson_jade", "Crimson Jade", "crimson", "jade"),
        ("cs_coral_cobalt", "Coral Cobalt", "coral", "cobalt"),
        ("cs_amber_indigo", "Amber Indigo", "amber", "indigo"),
        ("cs_honey_plum", "Honey Plum", "honey", "plum"),
        ("cs_mint_maroon", "Mint Maroon", "mint", "maroon"),
        ("cs_rose_emerald", "Rose Emerald", "rose", "emerald"),
        ("cs_slate_amber", "Slate Amber", "slate", "amber"),
        ("cs_champagne_cobalt", "Champagne Cobalt", "champagne", "cobalt"),
        ("cs_titanium_crimson", "Titanium Crimson", "titanium", "crimson"),
        ("cs_lavender_jade", "Lavender Jade", "lavender", "jade"),
        ("cs_charcoal_honey", "Charcoal Honey", "charcoal", "honey"),
        ("cs_ivory_indigo", "Ivory Indigo", "ivory", "indigo"),
        ("cs_peach_cobalt", "Peach Cobalt", "peach", "cobalt"),
        ("cs_sage_crimson", "Sage Crimson", "sage", "crimson"),
        ("cs_blush_emerald", "Blush Emerald", "blush", "emerald"),
        ("cs_burgundy_gold", "Burgundy Gold", "burgundy", "gold"),
        ("cs_chocolate_mint", "Chocolate Mint", "chocolate", "mint"),
        ("cs_pewter_rose", "Pewter Rose", "pewter", "rose"),
        ("cs_graphite_coral", "Graphite Coral", "graphite", "coral"),
        ("cs_aqua_maroon", "Aqua Maroon", "aqua", "maroon"),
    ]
    for key, display, c1, c2 in _CS_DUOS_META:
        r1, g1, b1 = COLOR_PALETTE[c1]
        r2, g2, b2 = COLOR_PALETTE[c2]
        meta[key] = {
            "name": display, "category": "Color Shift",
            "swatch": [[int(r1*255),int(g1*255),int(b1*255)],
                        [int(r2*255),int(g2*255),int(b2*255)]],
        }


    # Multi-Color Pattern entries
    MC_DISPLAY = {
        "mc_usa_flag": ("USA Flag", "swirl"), "mc_rasta": ("Rasta", "swirl"),
        "mc_halloween": ("Halloween", "swirl"), "mc_christmas": ("Christmas", "swirl"),
        "mc_miami_vice": ("Miami Vice", "swirl"), "mc_fire_storm": ("Fire Storm", "swirl"),
        "mc_deep_space": ("Deep Space", "swirl"), "mc_tropical": ("Tropical", "swirl"),
        "mc_vaporwave": ("Vaporwave", "swirl"), "mc_earth_tone": ("Earth Tone", "swirl"),
        "mc_woodland_camo": ("Woodland Camo", "camo"), "mc_desert_camo": ("Desert Camo", "camo"),
        "mc_urban_camo": ("Urban Camo", "camo"), "mc_snow_camo": ("Snow Camo", "camo"),
        "mc_neon_camo": ("Neon Camo", "camo"), "mc_blue_camo": ("Blue Camo", "camo"),
        "mc_white_marble": ("White Marble", "marble"), "mc_black_marble": ("Black Marble", "marble"),
        "mc_green_marble": ("Green Marble", "marble"), "mc_red_marble": ("Red Marble", "marble"),
        "mc_gold_marble": ("Gold Marble", "marble"),
        "mc_paint_splat": ("Paint Splatter", "splatter"), "mc_ink_splat": ("Ink Splatter", "splatter"),
        "mc_neon_splat": ("Neon Splatter", "splatter"), "mc_blood_splat": ("Blood Splatter", "splatter"),
    }
    MC_FIRST_COLOR = {
        "mc_usa_flag": "racing_red", "mc_rasta": "racing_red", "mc_halloween": "fire_orange",
        "mc_christmas": "racing_red", "mc_miami_vice": "hot_pink", "mc_fire_storm": "racing_red",
        "mc_deep_space": "navy", "mc_tropical": "lime_green", "mc_vaporwave": "hot_pink",
        "mc_earth_tone": "bronze", "mc_woodland_camo": "forest_green", "mc_desert_camo": "bronze",
        "mc_urban_camo": "gunmetal", "mc_snow_camo": "white", "mc_neon_camo": "lime_green",
        "mc_blue_camo": "royal_blue", "mc_white_marble": "white", "mc_black_marble": "black",
        "mc_green_marble": "forest_green", "mc_red_marble": "racing_red",
        "mc_gold_marble": "gold", "mc_paint_splat": "racing_red", "mc_ink_splat": "black",
        "mc_neon_splat": "hot_pink", "mc_blood_splat": "racing_red",
    }
    for key, (display, ptype) in MC_DISPLAY.items():
        c1 = MC_FIRST_COLOR[key]
        r1, g1, b1 = COLOR_PALETTE[c1]
        cat = f"Multi {ptype.title()}"
        meta[key] = {
            "name": display, "category": cat,
            "swatch": [int(r1*255), int(g1*255), int(b1*255)],
        }

    return meta


# ================================================================
# INTEGRATION — called from shokker_engine_v2.py
# ================================================================

# Cache for keys (used by metadata function)
_all_keys_cache = set()

def integrate_color_monolithics(engine_module):
    """Merge all color monolithic entries into the engine's MONOLITHIC_REGISTRY.
    Called from shokker_engine_v2.py after 24K expansion.
    """
    global _engine, _all_keys_cache

    _engine = engine_module

    # Build all entries
    solid_entries = _build_solid_color_entries()
    gradient_entries = _build_gradient_entries()
    colorshift_entries = _build_colorshift_entries()
    multicolor_entries = _build_multicolor_entries()

    # Merge into engine registry
    all_entries = {}
    all_entries.update(solid_entries)
    all_entries.update(gradient_entries)
    all_entries.update(colorshift_entries)
    all_entries.update(multicolor_entries)

    _all_keys_cache = set(all_entries.keys())

    engine_module.MONOLITHIC_REGISTRY.update(all_entries)

    # --- Sort MONOLITHIC_REGISTRY alphabetically after merge ---
    sorted_reg = dict(sorted(engine_module.MONOLITHIC_REGISTRY.items()))
    engine_module.MONOLITHIC_REGISTRY.clear()
    engine_module.MONOLITHIC_REGISTRY.update(sorted_reg)

    counts = {
        "solid": len(solid_entries),
        "gradient": len(gradient_entries),
        "colorshift": len(colorshift_entries),
        "multicolor": len(multicolor_entries),
        "total": len(all_entries),
    }
    print(f"[Color Monolithics] Loaded {counts['total']} entries: "
          f"{counts['solid']} solid, {counts['gradient']} gradient, "
          f"{counts['colorshift']} color-shift, {counts['multicolor']} multi-color")

    return counts
