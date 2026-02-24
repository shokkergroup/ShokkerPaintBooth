# ================================================================
# SHOKKER COLOR SHIFT v2 — Adaptive + Preset System
# 
# TWO MODES:
#   ADAPTIVE: Reads the existing paint color in the zone, shifts HUE
#             from that starting point. "Your color → shifted color"
#   PRESET:   Bold fixed color ramp (like Neonizm style) regardless
#             of base paint. For when you want a specific look.
#
# STRENGTH LEVELS (controlled by shift_strength param):
#   gentle:   Subtle hue drift, original color still dominant
#   moderate: Clear color transition, original still recognizable  
#   bold:     Strong shift, dramatic but blended
#   full:     Full replacement, Neonizm-level vivid color sweep
#
# The spec side stays the same — coordinated Fresnel zones.
# ================================================================


def _sample_zone_color(paint, mask):
    """Sample the dominant color in a masked zone.
    
    Returns (hue, sat, val) as floats in 0-1 range.
    This is the "starting point" for adaptive color shift.
    """
    # Get pixels where mask is strong (>0.5)
    strong = mask > 0.5
    if np.sum(strong) < 100:
        # Fallback: not enough pixels, use medium gray
        return 0.0, 0.0, 0.6
    
    # Extract RGB values in the zone
    r_vals = paint[:,:,0][strong]
    g_vals = paint[:,:,1][strong]
    b_vals = paint[:,:,2][strong]
    
    # Use median (robust to outliers from anti-aliasing)
    r_med = np.median(r_vals)
    g_med = np.median(g_vals)
    b_med = np.median(b_vals)
    
    # Convert to HSV
    maxc = max(r_med, g_med, b_med)
    minc = min(r_med, g_med, b_med)
    delta = maxc - minc
    
    # Value
    val = maxc
    
    # Saturation
    sat = delta / maxc if maxc > 0 else 0.0
    
    # Hue
    if delta < 0.001:
        hue = 0.0  # achromatic (gray/white/black)
    elif maxc == r_med:
        hue = (((g_med - b_med) / delta) % 6) / 6.0
    elif maxc == g_med:
        hue = (((b_med - r_med) / delta) + 2) / 6.0
    else:
        hue = (((r_med - g_med) / delta) + 4) / 6.0
    
    return float(hue), float(sat), float(val)


def paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                               hue_shift_degrees=60, shift_strength=0.85,
                               flake_size=6, flake_hue_spread=0.04,
                               saturation_boost=0.25):
    """ADAPTIVE color shift — starts from the zone's existing paint color.
    
    This is the Shokker innovation: it reads whatever color is already
    painted in the zone and creates a gradient that flows FROM that color
    THROUGH shifted hues. Gray becomes gray→teal→blue. Red becomes
    red→orange→gold. The car's identity is preserved while adding shift.
    
    Args:
        hue_shift_degrees: How far to shift in degrees (30=subtle, 120=dramatic, 300=rainbow)
        shift_strength: How much of the zone gets shifted (0.3=gentle, 0.6=moderate, 0.85=bold, 1.0=full)
        flake_size: Voronoi cell size for micro-flake texture (4-12)
        flake_hue_spread: Per-flake hue variation (0.0-0.15)
        saturation_boost: How much to boost saturation for grays (0.0-0.5)
    """
    h, w = shape
    
    # STEP 1: Sample the zone's existing color
    zone_hue, zone_sat, zone_val = _sample_zone_color(paint, mask)
    
    # STEP 2: Generate the gradient field (same one spec will use)
    field = _generate_colorshift_field(shape, seed)
    
    # STEP 3: Generate micro-flake texture
    flake_val, flake_edge = _generate_flake_field(shape, seed, cell_size=flake_size)
    
    # STEP 4: Build the adaptive color ramp
    # The key insight: field=0 stays near original color, field=1 is max shifted
    hue_shift = hue_shift_degrees / 360.0
    
    # Start from the zone's actual hue
    hue_map = (zone_hue + field * hue_shift) % 1.0
    
    # Add per-flake micro-variation
    flake_offset = (flake_val - 0.5) * flake_hue_spread
    hue_map = (hue_map + flake_offset) % 1.0
    
    # STEP 5: Handle saturation
    # For achromatic zones (gray, silver, white, black) we need to INJECT saturation
    # because shifting hue on a gray pixel does nothing without saturation
    if zone_sat < 0.15:
        # Zone is achromatic — inject saturation that ramps with the field
        # At field=0 (original zone), keep it lower sat
        # At field=1 (max shift), full vivid sat
        base_sat = 0.15 + saturation_boost  # minimum sat even at field=0
        saturation = base_sat + field * (0.70 - base_sat)  # ramp up to 0.70
    else:
        # Zone already has color — maintain original sat with slight boost
        saturation = np.clip(zone_sat + field * 0.15 + 0.05, 0, 1.0)
    
    # Peak saturation at mid-shift for vivid transitions
    saturation = saturation + 0.10 * np.sin(field * np.pi)
    saturation = np.clip(saturation, 0, 1.0)
    
    # STEP 6: Value/brightness
    # Preserve the original zone brightness but compensate for metallic darkening
    # iRacing metallic eats ~40% of perceived brightness
    value = np.clip(zone_val * 0.85 + 0.20 + field * 0.08, 0.25, 0.95)
    
    # Flake edge darkening
    value = value - flake_edge * 0.03
    
    # STEP 7: Convert HSV to RGB
    r_new, g_new, b_new = hsv_to_rgb_vec(hue_map, saturation, value)
    shift_rgb = np.stack([r_new, g_new, b_new], axis=2)
    
    # STEP 8: Blend with original paint
    # shift_strength controls how much of the zone gets the color shift
    # At 0.3 (gentle): original paint heavily visible, just a tint
    # At 0.85 (bold): color shift dominates but original peeks through
    # At 1.0 (full): complete replacement like Neonizm
    #
    # IMPORTANT: We scale blend by the field too — field=0 regions stay
    # closer to original, field=1 regions get full shift. This creates
    # the natural "flow from original to shifted" look.
    field_blend = 0.3 + field * 0.7  # field=0 → 30% shifted, field=1 → 100% shifted
    blend = shift_strength * pm * field_blend
    
    mask3 = mask[:, :, np.newaxis]
    paint = paint * (1.0 - blend[:,:,np.newaxis] * mask3) + shift_rgb * blend[:,:,np.newaxis] * mask3
    
    # Brightness boost for very dark zones
    paint = np.clip(paint + bb * 1.2 * mask3, 0, 1)
    
    return paint


def paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                             primary_hue=120, shift_range=240,
                             flake_size=6, flake_hue_spread=0.06,
                             shift_strength=0.95):
    """PRESET color shift — bold fixed color ramp (Neonizm-style).
    
    Ignores original paint color. Stamps a vivid color gradient directly.
    For when you want a SPECIFIC dramatic look, not an adaptive tint.
    
    Args:
        primary_hue: Starting hue in degrees (0-360)
        shift_range: Degrees of hue shift (30=narrow, 120=medium, 300=rainbow)
        shift_strength: Blend strength (0.85-1.0 recommended for preset mode)
    """
    h, w = shape
    
    # Generate fields
    field = _generate_colorshift_field(shape, seed)
    flake_val, flake_edge = _generate_flake_field(shape, seed, cell_size=flake_size)
    
    # Fixed color ramp — vivid and bold
    hue_start = primary_hue / 360.0
    hue_shift = shift_range / 360.0
    hue_map = (hue_start + field * hue_shift) % 1.0
    
    # Per-flake offset
    flake_offset = (flake_val - 0.5) * flake_hue_spread
    hue_map = (hue_map + flake_offset) % 1.0
    
    # Vivid saturation
    saturation = 0.82 + 0.13 * np.sin(field * np.pi)
    
    # Bright value — compensate for metallic darkening
    value = 0.70 + 0.12 * np.sin(field * np.pi * 0.5)
    value = value - flake_edge * 0.03
    
    # Convert
    r_new, g_new, b_new = hsv_to_rgb_vec(hue_map, saturation, value)
    shift_rgb = np.stack([r_new, g_new, b_new], axis=2)
    
    # Strong blend — preset mode wants to REPLACE, not tint
    blend = shift_strength * pm
    mask3 = mask[:, :, np.newaxis]
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3
    
    # Brightness boost
    paint = np.clip(paint + bb * 1.3 * mask3, 0, 1)
    
    return paint


# ================================================================
# ADAPTIVE PRESETS — "Your color + shift direction"
# These read the zone's existing color and shift from there.
# Perfect for customer cars — preserves their design identity.
# ================================================================

# --- Adaptive: Warm Shift (your color → +60° warmer) ---
def paint_cs_warm(paint, shape, mask, seed, pm, bb):
    """Adaptive Warm Shift — shifts toward warmer tones (+60°)"""
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=60, shift_strength=0.85,
                                      saturation_boost=0.30)

def spec_cs_warm(shape, mask, seed, sm):
    """Coordinated spec for warm shift"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=215, M_range=35, R_base=11, R_var=6,
                               CC_base=16, CC_range=14)

# --- Adaptive: Cool Shift (your color → +180° cooler/complementary) ---
def paint_cs_cool(paint, shape, mask, seed, pm, bb):
    """Adaptive Cool Shift — shifts toward cool complementary (+180°)"""
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=180, shift_strength=0.85,
                                      saturation_boost=0.30)

def spec_cs_cool(shape, mask, seed, sm):
    """Coordinated spec for cool shift"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=215, M_range=38, R_base=12, R_var=7,
                               CC_base=16, CC_range=16)


# --- Adaptive: Rainbow Shift (your color → through full spectrum) ---
def paint_cs_rainbow(paint, shape, mask, seed, pm, bb):
    """Adaptive Rainbow — full 300° spectrum sweep from your color"""
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=300, shift_strength=0.90,
                                      saturation_boost=0.35, flake_hue_spread=0.07)

def spec_cs_rainbow(shape, mask, seed, sm):
    """Coordinated spec for rainbow shift"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=205, M_range=45, R_base=12, R_var=9,
                               CC_base=16, CC_range=20)

# --- Adaptive: Subtle Shift (your color → gentle +40° drift) ---
def paint_cs_subtle(paint, shape, mask, seed, pm, bb):
    """Adaptive Subtle — gentle color drift, very refined"""
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=40, shift_strength=0.55,
                                      saturation_boost=0.15, flake_hue_spread=0.02)

def spec_cs_subtle(shape, mask, seed, sm):
    """Coordinated spec for subtle shift"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=220, M_range=25, R_base=10, R_var=5,
                               CC_base=16, CC_range=10)

# --- Adaptive: Extreme Shift (your color → +200° dramatic departure) ---
def paint_cs_extreme(paint, shape, mask, seed, pm, bb):
    """Adaptive Extreme — dramatic hue departure, full vivid"""
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=200, shift_strength=0.95,
                                      saturation_boost=0.40, flake_hue_spread=0.08)

def spec_cs_extreme(shape, mask, seed, sm):
    """Coordinated spec for extreme shift"""
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=200, M_range=50, R_base=13, R_var=10,
                               CC_base=16, CC_range=22)


# ================================================================
# PRESET COLOR SHIFTS — Bold fixed color ramps (Neonizm-style)
# These REPLACE the paint with vivid gradients regardless of base.
# For showcase cars, billboards, and maximum visual impact.
# ================================================================

# --- Preset: Emerald (Green → Blue → Purple) ---
def paint_cs_emerald(paint, shape, mask, seed, pm, bb):
    """Preset Emerald — Green → Blue → Purple (ChromaFlair classic)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    primary_hue=120, shift_range=240,
                                    shift_strength=0.95)

def spec_cs_emerald(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=210, M_range=40, R_base=12, R_var=8,
                               CC_base=16, CC_range=18)

# --- Preset: Inferno (Red → Orange → Gold → Green) ---
def paint_cs_inferno(paint, shape, mask, seed, pm, bb):
    """Preset Inferno — Red → Orange → Gold → Green"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    primary_hue=0, shift_range=130,
                                    flake_size=5, shift_strength=0.95)

def spec_cs_inferno(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=215, M_range=35, R_base=10, R_var=6,
                               CC_base=16, CC_range=14)


# --- Preset: Nebula (Purple → Pink → Gold) ---
def paint_cs_nebula(paint, shape, mask, seed, pm, bb):
    """Preset Nebula — Purple → Pink → Gold (cosmic luxury)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    primary_hue=270, shift_range=120,
                                    flake_size=7, shift_strength=0.95)

def spec_cs_nebula(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=220, M_range=35, R_base=14, R_var=7,
                               CC_base=16, CC_range=16)

# --- Preset: Deep Ocean (Teal → Blue → Violet) ---
def paint_cs_deepocean(paint, shape, mask, seed, pm, bb):
    """Preset Deep Ocean — Teal → Blue → Indigo → Violet"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    primary_hue=180, shift_range=110,
                                    shift_strength=0.95)

def spec_cs_deepocean(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=215, M_range=38, R_base=11, R_var=7,
                               CC_base=16, CC_range=16)

# --- Preset: Supernova (Copper → Magenta → Teal, widest shift) ---
def paint_cs_supernova(paint, shape, mask, seed, pm, bb):
    """Preset Supernova — Copper → Magenta → Teal (full spectrum)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    primary_hue=20, shift_range=300,
                                    flake_size=5, flake_hue_spread=0.08,
                                    shift_strength=0.95)

def spec_cs_supernova(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=205, M_range=45, R_base=12, R_var=9,
                               CC_base=16, CC_range=20)

# --- Preset: Solar Flare (Gold → Amber → Red) ---
def paint_cs_solarflare(paint, shape, mask, seed, pm, bb):
    """Preset Solar Flare — Gold → Amber → Red (sunset metal)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    primary_hue=45, shift_range=90,
                                    flake_size=5, flake_hue_spread=0.04,
                                    shift_strength=0.95)

def spec_cs_solarflare(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=225, M_range=30, R_base=10, R_var=5,
                               CC_base=16, CC_range=12)

# --- Preset: Mystichrome Pro (Green → Blue → Purple, tighter than emerald) ---
def paint_cs_mystichrome(paint, shape, mask, seed, pm, bb):
    """Preset Mystichrome Pro — Ford SVT tribute with coordinated spec"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    primary_hue=120, shift_range=200,
                                    flake_size=6, flake_hue_spread=0.05,
                                    shift_strength=0.95)

def spec_cs_mystichrome(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
                               M_base=218, M_range=38, R_base=11, R_var=6,
                               CC_base=16, CC_range=16)

