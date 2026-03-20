"""
engine/color_shift.py - ALL Color Shift Functions
===================================================
ONE file. ALL color shift. Find something CS-related? It's here.

STRUCTURE:
  SECTION 1: Shared CS Helpers     (_cs_direct_rgb, _spec_cs_v5, _cs_adaptive_v5)
  SECTION 2: CS Adaptive Group     (cs_cool, cs_warm, cs_complementary, cs_rainbow, ...)
  SECTION 3: CS Presets            (cs_deepocean, cs_solarflare, cs_mystichrome, ...)
  SECTION 4: CS Candy/Oil/Rose     (cs_candypaint, cs_oilslick, cs_rosegold, cs_goldrust, cs_toxic)
  SECTION 5: Color Shift Duo       (75 two-color chameleon pairs: cs_fire_ice, cs_black_silver, ...)

FIX GUIDE:
  "CS Cool shows wrong colors"     → SECTION 2, paint_cs_cool
  "Deep Ocean recolors base"       → SECTION 3, paint_cs_deepocean
  "cs_black_silver is brown"       → SECTION 5, _make_colorshift_paint_direct
  "All CS Presets have artifacts"  → SECTION 1, _cs_direct_rgb
  "Swatch thumbnails wrong"        → Update CS_PRESET_META at bottom of SECTION 3

CORE PRINCIPLE - why it was broken before:
  HSV color space has h=0° for ALL neutral/achromatic colors (black, white, gray, silver).
  h=0° in HSV = RED. Any flake_hue_spread on an achromatic color = red contamination = brown.
  SOLUTION: _cs_direct_rgb uses pure RGB interpolation. No HSV involved at all.
  ALL CS functions in this file use _cs_direct_rgb or explicit absolute RGB stops.
"""

import numpy as np
from engine.core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec, rgb_to_hsv_array


# ================================================================
# SECTION 1: SHARED CS HELPERS
# ================================================================

def _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
                    hue_offsets=None, sat_curve=None, val_curve=None,
                    flake_intensity=0.0, flake_hue_spread=0.0, blend_strength=0.90):
    """Zone-color-adaptive CS: sample paint color, apply hue/sat/val ramp from curves.
    hue_offsets: list of (field_pos, hue_deg) - hue = zone_hue + interp(deg)/360
    sat_curve / val_curve: list of (index, value) - mapped to field segments, additive to zone S/V.
    """
    h, w = shape
    # Sample zone color (mean under mask or center)
    m = mask > 0.2
    if np.any(m):
        zone_rgb = np.array([
            np.mean(paint[:,:,0][m]), np.mean(paint[:,:,1][m]), np.mean(paint[:,:,2][m])
        ], dtype=np.float32)
    else:
        cy, cx = h // 2, w // 2
        zone_rgb = paint[cy, cx, :3].copy()
    zone_rgb = np.clip(zone_rgb, 1e-5, 1.0)
    hsv1 = rgb_to_hsv_array(zone_rgb.reshape(1, 1, 3))
    z_h, z_s, z_v = float(hsv1[0,0,0]), float(hsv1[0,0,1]), float(hsv1[0,0,2])

    field = multi_scale_noise(shape, [96, 192, 48], [0.45, 0.35, 0.20], seed + 6000)
    field = np.clip(field * 0.5 + 0.5, 0, 1)

    def interp_hue_stops(stops, f):
        """stops = [(field_pos, hue_deg), ...]; f in [0,1]. Linear interpolate hue_deg."""
        if not stops:
            return 0.0
        pts = sorted(stops, key=lambda x: x[0])
        if f <= pts[0][0]:
            return pts[0][1]
        if f >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            p0, v0 = pts[i]
            p1, v1 = pts[i + 1]
            if p0 <= f <= p1:
                t = (f - p0) / max(p1 - p0, 1e-8)
                return v0 * (1 - t) + v1 * t
        return pts[-1][1]

    def interp_index_curve(points, f):
        """points = [(segment_index, value), ...]; f in [0,1]. Map f to segment and interpolate."""
        if not points:
            return 0.0
        pts = sorted(points, key=lambda x: x[0])
        n = len(pts)
        if n == 1:
            return pts[0][1]
        seg = f * (n - 1)
        i0 = min(max(0, int(np.floor(seg))), n - 2)
        i1 = i0 + 1
        t = seg - i0
        return pts[i0][1] * (1 - t) + pts[i1][1] * t

    hue_offsets = hue_offsets or [(0.0, 0), (1.0, 0)]
    sat_curve = sat_curve or [(0, 0.15), (1, 0.15)]
    val_curve = val_curve or [(0, 0.2), (1, 0.2)]

    hue_deg = np.vectorize(lambda f: interp_hue_stops(hue_offsets, f))(field)
    sat_delta = np.vectorize(lambda f: interp_index_curve(sat_curve, f))(field)
    val_delta = np.vectorize(lambda f: interp_index_curve(val_curve, f))(field)

    H = (z_h + hue_deg.astype(np.float32) / 360.0) % 1.0
    S = np.clip(z_s + sat_delta.astype(np.float32), 0, 1)
    V = np.clip(z_v + val_delta.astype(np.float32), 0, 1)

    r, g, b = hsv_to_rgb_vec(H, S, V)
    tr = np.clip(r.astype(np.float32), 0, 1)
    tg = np.clip(g.astype(np.float32), 0, 1)
    tb = np.clip(b.astype(np.float32), 0, 1)

    if flake_intensity > 0:
        micro = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.35, 0.25], seed + 6100)
        s = micro * flake_intensity * pm * mask
        tr = np.clip(tr + s, 0, 1)
        tg = np.clip(tg + s, 0, 1)
        tb = np.clip(tb + s, 0, 1)

    blend = blend_strength * pm
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + tr * mask * blend, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + tg * mask * blend, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + tb * mask * blend, 0, 1)
    return result


def _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.025):
    """Direct RGB multi-stop color shift - NO HSV, NO BROWN.

    This is the foundation of all CS rendering in V5.
    HSV was replaced because h=0° contamination caused brown on neutral colors.

    Args:
        paint:     (h,w,4) float32 paint array [0,1]
        shape:     (h, w) tuple
        mask:      (h,w) float32 mask [0,1]
        seed:      int - determines noise field pattern
        pm:        float - paint multiplier / intensity [0,1.5]
        bb:        bounding box (unused, kept for API compat)
        rgb_stops: list of (field_pos, r, g, b) - absolute RGB at each field value
                   field_pos 0.0 = face-on view (dominant), 1.0 = glancing edge
        shimmer:   float - brightness shimmer intensity (0 = none)

    Returns: paint array with color shift applied
    """
    h, w = shape
    # Structural field: large scales simulate panel orientation variation
    field = multi_scale_noise(shape, [96, 192, 48], [0.45, 0.35, 0.20], seed + 6000)
    field = np.clip(field * 0.5 + 0.5, 0, 1)

    # Sort stops by field position
    stops = sorted(rgb_stops, key=lambda x: x[0])
    n = len(stops)

    # Interpolate RGB at each pixel from the stop ramp
    tr = np.zeros((h, w), dtype=np.float32)
    tg = np.zeros((h, w), dtype=np.float32)
    tb = np.zeros((h, w), dtype=np.float32)

    for i in range(n - 1):
        p0, r0, g0, b0 = stops[i]
        p1, r1, g1, b1 = stops[i + 1]
        in_range = (field >= p0) & (field <= p1)
        if not np.any(in_range):
            continue
        t = np.where(in_range, np.clip((field - p0) / max(p1 - p0, 1e-6), 0, 1), 0.0)
        tr = np.where(in_range, r0 * (1 - t) + r1 * t, tr)
        tg = np.where(in_range, g0 * (1 - t) + g1 * t, tg)
        tb = np.where(in_range, b0 * (1 - t) + b1 * t, tb)

    # Fill below first stop and above last stop
    p0, r0, g0, b0 = stops[0]
    p_last, r_last, g_last, b_last = stops[-1]
    tr = np.where(field < p0, r0, tr)
    tg = np.where(field < p0, g0, tg)
    tb = np.where(field < p0, b0, tb)
    tr = np.where(field > p_last, r_last, tr)
    tg = np.where(field > p_last, g_last, tg)
    tb = np.where(field > p_last, b_last, tb)

    # Apply to paint
    blend = 0.90 * pm
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + tr * mask * blend, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + tg * mask * blend, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + tb * mask * blend, 0, 1)

    # Brightness-only shimmer (NO hue shift - avoids color contamination)
    avg_lum = 0.299 * tr.mean() + 0.587 * tg.mean() + 0.114 * tb.mean()
    if avg_lum > 0.04 and shimmer > 0:
        micro = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.35, 0.25], seed + 6100)
        s = micro * shimmer * pm * mask
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + s, 0, 1)

    return result


def _spec_cs_v5(shape, mask, seed, sm,
                M_base=228, M_range=25, R_base=10, R_range=10,
                CC_base=16, CC_range=40):  # CC: 16=max gloss, 17-255=progressively degraded. Range=40 spans fresh→slightly worn.
    """Shared spec function for all CS finishes.
    High metallic for chameleon behavior. Coordinate field-driven M/R/CC variation.
    To use a custom spec for a finish, define spec_cs_XXX in that finish's section.
    """
    # Import from legacy engine (spec_chameleon_v5 lives there)
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from shokker_engine_v2 import spec_chameleon_v5
    return spec_chameleon_v5(shape, mask, seed, sm, field=None,
                              M_base=M_base, M_range=M_range,
                              R_base=R_base, R_range=R_range,
                              CC_base=CC_base, CC_range=CC_range)


# ================================================================
# SECTION 2: CS ADAPTIVE GROUP
# These read the zone's base color and shift FROM it.
# Exception: cs_cool and cs_warm are ABSOLUTE - they ignore base color
# and always render cool/warm tones regardless of zone.
# ================================================================

def paint_cs_cool(paint, shape, mask, seed, pm, bb):
    """CS Cool - ABSOLUTE cool palette. Always blue/teal/purple.
    Does NOT read base color. Locks to cool spectrum regardless of zone.

    FIX: Was previously reading zone hue and shifting 180° - red base = orange/pink/blue.
    Now uses absolute RGB stops so color is always predictably cool.
    """
    rgb_stops = [
        (0.00, 0.05, 0.55, 0.80),   # Cerulean blue (face-on)
        (0.25, 0.00, 0.40, 0.75),   # Deep blue
        (0.50, 0.10, 0.25, 0.70),   # Blue-indigo
        (0.75, 0.35, 0.10, 0.65),   # Indigo-purple
        (1.00, 0.45, 0.05, 0.60),   # Deep violet (glancing edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.030)

def spec_cs_cool(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=232, M_range=28, CC_range=30)  # Fresh icy coat - tight range near perfect


def paint_cs_warm(paint, shape, mask, seed, pm, bb):
    """CS Warm - ABSOLUTE warm palette. Always gold/amber/orange/red.
    Does NOT read base color. Locks to warm spectrum regardless of zone.
    """
    rgb_stops = [
        (0.00, 0.90, 0.80, 0.10),   # Gold (face-on)
        (0.25, 0.92, 0.60, 0.05),   # Amber
        (0.50, 0.90, 0.40, 0.03),   # Orange
        (0.75, 0.85, 0.15, 0.02),   # Red-orange
        (1.00, 0.70, 0.05, 0.05),   # Deep crimson (glancing edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.025)

def spec_cs_warm(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=230, M_range=25, CC_range=35)  # Warm metallic - slight daily-driver character


def paint_cs_complementary(paint, shape, mask, seed, pm, bb):
    """CS Complementary - reads zone hue, sweeps to its 180° opposite."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.25, 45), (0.5, 90), (0.75, 135), (1.0, 180)],
        sat_curve=[(0, 0.12), (1, 0.15), (2, 0.18), (3, 0.15), (4, 0.12)],
        val_curve=[(0, 0.18), (1, 0.20), (2, 0.22), (3, 0.20), (4, 0.18)])

def spec_cs_complementary(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=230, M_range=28, CC_range=40)


def paint_cs_monochrome(paint, shape, mask, seed, pm, bb):
    """CS Monochrome - stays on zone hue, sweeps saturation/value for depth."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, -5), (0.25, -2), (0.5, 0), (0.75, 2), (1.0, 5)],
        sat_curve=[(0, -0.10), (1, 0.05), (2, 0.15), (3, 0.05), (4, -0.10)],
        val_curve=[(0, 0.05), (1, 0.15), (2, 0.28), (3, 0.15), (4, 0.05)],
        flake_intensity=0.04, flake_hue_spread=0.02, blend_strength=0.90)

def spec_cs_monochrome(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=225, M_range=30, R_range=8, CC_range=35)  # Monochrome: refined, near-perfect coat


def paint_cs_subtle(paint, shape, mask, seed, pm, bb):
    """CS Subtle - barely perceptible ±20° color drift for refined finishes."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, -15), (0.25, -5), (0.5, 5), (0.75, 15), (1.0, 25)],
        sat_curve=[(0, 0.08), (1, 0.10), (2, 0.12), (3, 0.10), (4, 0.08)],
        val_curve=[(0, 0.15), (1, 0.17), (2, 0.19), (3, 0.17), (4, 0.15)],
        flake_intensity=0.03, flake_hue_spread=0.04, blend_strength=0.88)

def spec_cs_subtle(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=222, M_range=18, R_range=8, CC_range=28)  # Subtle: refined coat, minimal variation


def paint_cs_rainbow(paint, shape, mask, seed, pm, bb):
    """CS Rainbow - full 360° spectral sweep through every color of light."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.14, 30), (0.28, 60), (0.43, 120),
                     (0.57, 180), (0.71, 240), (0.86, 300), (1.0, 355)],
        sat_curve=[(0, 0.20), (1, 0.22), (2, 0.24), (3, 0.25),
                   (4, 0.24), (5, 0.22), (6, 0.20), (7, 0.18)],
        val_curve=[(0, 0.22), (1, 0.24), (2, 0.26), (3, 0.26),
                   (4, 0.26), (5, 0.24), (6, 0.22), (7, 0.20)],
        flake_intensity=0.05, flake_hue_spread=0.10)

def spec_cs_rainbow(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=228, M_range=30, CC_range=45)  # Rainbow: max CC variety for spectral depth


def paint_cs_vivid(paint, shape, mask, seed, pm, bb):
    """CS Vivid - maximum saturation electric color sweep."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.2, 25), (0.4, 50), (0.6, 80), (0.8, 120), (1.0, 160)],
        sat_curve=[(0, 0.25), (1, 0.28), (2, 0.30), (3, 0.32), (4, 0.28), (5, 0.25)],
        val_curve=[(0, 0.24), (1, 0.28), (2, 0.30), (3, 0.30), (4, 0.28), (5, 0.24)],
        flake_intensity=0.05, flake_hue_spread=0.08, blend_strength=0.95)

def spec_cs_vivid(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=232, M_range=28, CC_range=40)  # Vivid: fresh energetic coat


def paint_cs_extreme(paint, shape, mask, seed, pm, bb):
    """CS Extreme - dramatic wide color push (200° departure from base)."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.2, 50), (0.4, 100), (0.6, 150), (0.8, 180), (1.0, 210)],
        sat_curve=[(0, 0.18), (1, 0.22), (2, 0.25), (3, 0.22), (4, 0.18), (5, 0.15)],
        val_curve=[(0, 0.20), (1, 0.24), (2, 0.26), (3, 0.24), (4, 0.20), (5, 0.18)],
        flake_intensity=0.05, flake_hue_spread=0.09, blend_strength=0.95)

def spec_cs_extreme(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=235, M_range=30, CC_range=50)  # Extreme: max CC range for dramatic depth shifts


def paint_cs_triadic(paint, shape, mask, seed, pm, bb):
    """CS Triadic - three equidistant colors at 120° intervals from zone hue."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.2, 40), (0.4, 80), (0.6, 120), (0.8, 200), (1.0, 240)],
        sat_curve=[(0, 0.15), (1, 0.18), (2, 0.20), (3, 0.22), (4, 0.20), (5, 0.15)],
        val_curve=[(0, 0.18), (1, 0.22), (2, 0.24), (3, 0.24), (4, 0.22), (5, 0.18)],
        flake_intensity=0.045, flake_hue_spread=0.07)

def spec_cs_triadic(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=228, M_range=28, CC_range=40)


def paint_cs_split(paint, shape, mask, seed, pm, bb):
    """CS Split - zone color + two colors flanking its complement (split-complementary)."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.25, 50), (0.5, 150), (0.75, 180), (1.0, 210)],
        sat_curve=[(0, 0.12), (1, 0.16), (2, 0.20), (3, 0.16), (4, 0.12)],
        val_curve=[(0, 0.18), (1, 0.22), (2, 0.24), (3, 0.22), (4, 0.18)])

def spec_cs_split(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=230, M_range=28, CC_range=40)


def paint_cs_neon_shift(paint, shape, mask, seed, pm, bb):
    """CS Neon - electric fluorescent sweep from zone base."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.2, 40), (0.4, 80), (0.6, 140), (0.8, 200), (1.0, 260)],
        sat_curve=[(0, 0.25), (1, 0.30), (2, 0.32), (3, 0.30), (4, 0.28), (5, 0.25)],
        val_curve=[(0, 0.28), (1, 0.32), (2, 0.34), (3, 0.32), (4, 0.30), (5, 0.28)],
        flake_intensity=0.05, flake_hue_spread=0.08, blend_strength=0.95)

def spec_cs_neon_shift(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=220, M_range=25, R_base=12, CC_range=45)  # Neon: big CC variation for electric depth


def paint_cs_ocean_shift(paint, shape, mask, seed, pm, bb):
    """CS Ocean Shift - aquatic spectrum: teal → cyan → blue → indigo (relative to zone)."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 0), (0.25, -20), (0.5, -40), (0.75, -55), (1.0, -70)],
        sat_curve=[(0, 0.12), (1, 0.18), (2, 0.22), (3, 0.18), (4, 0.14)],
        val_curve=[(0, 0.18), (1, 0.22), (2, 0.24), (3, 0.20), (4, 0.16)],
        flake_intensity=0.035, flake_hue_spread=0.05)

def spec_cs_ocean_shift(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=228, M_range=28, CC_range=38)  # Ocean: flowing coat variation


def paint_cs_chrome_shift(paint, shape, mask, seed, pm, bb):
    """CS Chrome Shift - silver-to-blue metallic chrome spectrum sweep."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, -10), (0.25, 0), (0.5, 15), (0.75, 30), (1.0, 50)],
        sat_curve=[(0, -0.30), (1, -0.25), (2, -0.15), (3, -0.20), (4, -0.25)],
        val_curve=[(0, 0.35), (1, 0.38), (2, 0.40), (3, 0.38), (4, 0.35)],
        flake_intensity=0.06, flake_hue_spread=0.03, blend_strength=0.90)

def spec_cs_chrome_shift(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=242, M_range=15, R_base=6, R_range=6, CC_range=20)  # Chrome shift: tight CC - chrome is mostly no-coat


def paint_cs_earth(paint, shape, mask, seed, pm, bb):
    """CS Earth - warm natural earth tones: olive → umber → sienna → sage."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, 15), (0.25, 25), (0.5, 40), (0.75, 55), (1.0, 70)],
        sat_curve=[(0, -0.15), (1, -0.10), (2, -0.05), (3, -0.10), (4, -0.15)],
        val_curve=[(0, 0.08), (1, 0.12), (2, 0.15), (3, 0.12), (4, 0.08)],
        flake_intensity=0.03, flake_hue_spread=0.04, blend_strength=0.88)

def spec_cs_earth(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=210, M_range=20,
                        R_base=18, R_range=12, CC_base=16, CC_range=60)  # Earth: weathered coat - CC=16-76 for authentic aged look


def paint_cs_prism_shift(paint, shape, mask, seed, pm, bb):
    """CS Prism - spectral dispersion like white light through a crystal prism."""
    return _cs_adaptive_v5(paint, shape, mask, seed, pm, bb,
        hue_offsets=[(0.0, -30), (0.17, 0), (0.33, 30), (0.5, 60),
                     (0.67, 120), (0.83, 180), (1.0, 240)],
        sat_curve=[(0, 0.18), (1, 0.22), (2, 0.25), (3, 0.28),
                   (4, 0.25), (5, 0.22), (6, 0.18)],
        val_curve=[(0, 0.22), (1, 0.25), (2, 0.28), (3, 0.30),
                   (4, 0.28), (5, 0.25), (6, 0.22)],
        flake_intensity=0.05, flake_hue_spread=0.09)

def spec_cs_prism_shift(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=225, M_range=30, CC_range=45)  # Prism: max CC variation for crystal depth


# ================================================================
# SECTION 3: CS PRESETS
# Fixed-color ramps. These do NOT read the base color.
# All use _cs_direct_rgb for clean, accurate RGB output.
#
# TO ADD A NEW PRESET:
#   1. def paint_cs_mypreset(paint, shape, mask, seed, pm, bb):
#          rgb_stops = [(0.0, r,g,b), (0.5, r,g,b), (1.0, r,g,b)]
#          return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops)
#      def spec_cs_mypreset(shape, mask, seed, sm):
#          return _spec_cs_v5(shape, mask, seed, sm)
#   2. Register in engine/registry.py
#   3. Add to paint-booth-v2.html CS_PRESET_DEFS array
# ================================================================

def paint_cs_deepocean(paint, shape, mask, seed, pm, bb):
    """CS Deep Ocean - absolute blue spectrum: teal surface to abyssal violet.
    Should shift through BLUES only. Fixed: was recoloring base entirely.
    """
    rgb_stops = [
        (0.00, 0.00, 0.75, 0.75),   # Bright teal surface (face)
        (0.25, 0.00, 0.50, 0.85),   # Cerulean
        (0.50, 0.05, 0.25, 0.85),   # Royal blue
        (0.75, 0.15, 0.05, 0.70),   # Indigo
        (1.00, 0.25, 0.00, 0.55),   # Deep violet abyss (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.025)

def spec_cs_deepocean(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=230, M_range=28, CC_range=38)


def paint_cs_solarflare(paint, shape, mask, seed, pm, bb):
    """CS Solar Flare - absolute fire: yellow-gold through deep crimson.
    Should be yellow/orange/red/crimson. Fixed: was showing pink (HSV h=345° wraparound).
    """
    rgb_stops = [
        (0.00, 0.98, 0.92, 0.05),   # Bright solar yellow (face)
        (0.20, 0.98, 0.70, 0.02),   # Gold-amber
        (0.40, 0.95, 0.45, 0.02),   # Orange
        (0.60, 0.90, 0.18, 0.03),   # Red-orange
        (0.80, 0.78, 0.05, 0.05),   # Deep red
        (1.00, 0.45, 0.02, 0.08),   # Near-black crimson (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.03)

def spec_cs_solarflare(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=230, M_range=26, CC_range=40)  # Solar: energetic range


def paint_cs_inferno(paint, shape, mask, seed, pm, bb):
    """CS Inferno - absolute blazing fire: deep crimson through bright gold."""
    rgb_stops = [
        (0.00, 0.50, 0.02, 0.02),   # Deep crimson (face)
        (0.20, 0.82, 0.05, 0.05),   # Red
        (0.40, 0.92, 0.28, 0.02),   # Orange-red
        (0.60, 0.95, 0.50, 0.02),   # Orange
        (0.80, 0.95, 0.72, 0.03),   # Gold
        (1.00, 0.90, 0.85, 0.05),   # Bright amber-gold (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.030)

def spec_cs_inferno(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=232, M_range=26, CC_range=40)  # Inferno: fiery range


def paint_cs_nebula(paint, shape, mask, seed, pm, bb):
    """CS Nebula - cosmic: deep purple → magenta → rose → warm gold."""
    rgb_stops = [
        (0.00, 0.25, 0.00, 0.55),   # Deep space purple (face)
        (0.25, 0.55, 0.00, 0.55),   # Magenta
        (0.50, 0.80, 0.10, 0.35),   # Rose-magenta
        (0.75, 0.90, 0.60, 0.05),   # Warm gold
        (1.00, 0.85, 0.72, 0.02),   # Amber-gold (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.030)

def spec_cs_nebula(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=228, M_range=30, CC_range=50)  # Nebula: cosmic depth variation


def paint_cs_mystichrome(paint, shape, mask, seed, pm, bb):
    """CS Mystichrome - Ford SVT tribute: absolute forest green → teal → blue → purple."""
    rgb_stops = [
        (0.00, 0.10, 0.55, 0.20),   # Forest green (face)
        (0.20, 0.00, 0.55, 0.45),   # Teal-green
        (0.40, 0.00, 0.30, 0.80),   # Blue
        (0.60, 0.05, 0.10, 0.80),   # Deep blue
        (0.80, 0.25, 0.00, 0.72),   # Indigo
        (1.00, 0.42, 0.00, 0.70),   # Purple (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.025)

def spec_cs_mystichrome(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=232, M_range=28, CC_range=38)  # Mystichrome: premium swept coat


def paint_cs_supernova(paint, shape, mask, seed, pm, bb):
    """CS Supernova - widest shift: copper → gold → lime → green → teal → cyan."""
    rgb_stops = [
        (0.00, 0.80, 0.45, 0.10),   # Copper (face)
        (0.20, 0.90, 0.72, 0.05),   # Gold
        (0.40, 0.65, 0.90, 0.05),   # Yellow-green
        (0.60, 0.05, 0.80, 0.30),   # Green
        (0.80, 0.00, 0.75, 0.65),   # Teal
        (1.00, 0.00, 0.85, 0.90),   # Bright cyan (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.035)

def spec_cs_supernova(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=235, M_range=32, CC_range=50)  # Supernova: widest coat variation


def paint_cs_emerald(paint, shape, mask, seed, pm, bb):
    """CS Emerald - gem teal to deep violet."""
    rgb_stops = [
        (0.00, 0.00, 0.72, 0.50),   # Emerald teal (face)
        (0.25, 0.00, 0.70, 0.75),   # Cyan-teal
        (0.50, 0.00, 0.35, 0.88),   # Blue
        (0.75, 0.20, 0.05, 0.78),   # Indigo
        (1.00, 0.40, 0.00, 0.72),   # Deep purple (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.025)

def spec_cs_emerald(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=230, M_range=28, CC_range=38)  # Emerald: jewel depth


# ----------------------------------------------------------------
# CS CANDY PAINT, OIL SLICK, ROSE GOLD, GOLD RUSH, TOXIC
# These also use _cs_direct_rgb for clean output.
# Legacy implementations delegate to shokker_engine_v2 until rewritten.
# ----------------------------------------------------------------

def _delegate_to_legacy(fn_name, paint, shape, mask, seed, pm, bb):
    """Temporary helper - delegates to legacy engine until V5 rewrite is complete."""
    try:
        import shokker_engine_v2 as _e
        fn = getattr(_e, fn_name, None)
        if fn:
            return fn(paint, shape, mask, seed, pm, bb)
    except Exception:
        pass
    return paint

def _delegate_spec_to_legacy(fn_name, shape, mask, seed, sm):
    try:
        import shokker_engine_v2 as _e
        fn = getattr(_e, fn_name, None)
        if fn:
            return fn(shape, mask, seed, sm)
    except Exception:
        pass
    import numpy as np
    return _spec_cs_v5(shape, mask, seed, sm)


def paint_cs_candypaint(paint, shape, mask, seed, pm, bb):
    """CS Candy Paint - absolute electric candy sweep: magenta → violet → cobalt → teal → lime.
    Vivid saturated colors only. No base color dependency.
    """
    rgb_stops = [
        (0.00, 0.95, 0.05, 0.55),   # Electric magenta (face)
        (0.20, 0.70, 0.00, 0.90),   # Violet
        (0.40, 0.10, 0.10, 0.95),   # Deep cobalt blue
        (0.60, 0.00, 0.65, 0.80),   # Teal-cyan
        (0.80, 0.10, 0.90, 0.20),   # Lime-green
        (1.00, 0.85, 0.90, 0.00),   # Yellow-lime (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.035)

def spec_cs_candypaint(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=228, M_range=28, R_base=12, CC_range=35)  # Candy: rich coat


def paint_cs_oilslick(paint, shape, mask, seed, pm, bb):
    """CS Oil Slick - iridescent petroleum rainbow: full spectral sweep.
    Like a puddle of oil in sunlight: red → orange → gold → green → teal → blue → violet.
    """
    rgb_stops = [
        (0.00, 0.85, 0.10, 0.20),   # Deep red (face)
        (0.15, 0.92, 0.45, 0.02),   # Orange
        (0.30, 0.92, 0.82, 0.02),   # Gold-yellow
        (0.45, 0.10, 0.85, 0.15),   # Lime-green
        (0.60, 0.00, 0.75, 0.65),   # Teal
        (0.75, 0.05, 0.30, 0.90),   # Blue
        (0.88, 0.40, 0.05, 0.85),   # Violet
        (1.00, 0.75, 0.05, 0.70),   # Magenta-purple (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.04)

def spec_cs_oilslick(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=235, M_range=20, R_base=8, R_range=8, CC_range=30)  # Oil slick: thin coat variation


def paint_cs_rosegold(paint, shape, mask, seed, pm, bb):
    """CS Rose Gold - warm metallic luxury sweep: champagne → rose gold → copper → blush."""
    rgb_stops = [
        (0.00, 0.97, 0.90, 0.72),   # Champagne (face)
        (0.25, 0.92, 0.68, 0.58),   # Rose gold warm
        (0.50, 0.88, 0.50, 0.45),   # Rose copper
        (0.75, 0.82, 0.38, 0.38),   # Deep copper rose
        (1.00, 0.72, 0.28, 0.30),   # Dark copper (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.020)

def spec_cs_rosegold(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=225, M_range=22, R_base=14, CC_range=35)  # Rose gold: warm satin-to-gloss range


def paint_cs_goldrush(paint, shape, mask, seed, pm, bb):
    """CS Gold Rush - precious metal spectrum: bright gold → amber → bronze → dark copper."""
    rgb_stops = [
        (0.00, 0.98, 0.88, 0.10),   # Bright gold (face)
        (0.25, 0.95, 0.72, 0.05),   # Deep gold
        (0.50, 0.85, 0.55, 0.08),   # Amber-bronze
        (0.75, 0.72, 0.38, 0.10),   # Bronze
        (1.00, 0.55, 0.25, 0.08),   # Dark copper (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.022)

def spec_cs_goldrush(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=230, M_range=24, R_base=12, CC_range=38)  # Gold rush: precious metal depth


def paint_cs_toxic(paint, shape, mask, seed, pm, bb):
    """CS Toxic - biohazard acid: nuclear yellow-green → toxic chartreuse → hazardous lime."""
    rgb_stops = [
        (0.00, 0.55, 0.95, 0.02),   # Nuclear yellow-green (face)
        (0.25, 0.30, 0.98, 0.05),   # Toxic chartreuse
        (0.50, 0.05, 0.95, 0.20),   # Lime-green
        (0.75, 0.00, 0.88, 0.55),   # Teal-green
        (1.00, 0.00, 0.75, 0.75),   # Toxic cyan (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.030)

def spec_cs_toxic(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=222, M_range=28, R_base=14, CC_range=45)  # Toxic: wide range for acid-burn coat feel


def paint_cs_darkflame(paint, shape, mask, seed, pm, bb):
    """CS Dark Flame - volcanic dark fire: near-black → deep crimson → dark orange → char.
    Darker than cs_inferno - moodier, less bright. Classic dark flame paint job feel.
    """
    rgb_stops = [
        (0.00, 0.08, 0.00, 0.00),   # Near-black charcoal (face)
        (0.20, 0.40, 0.02, 0.02),   # Dark crimson
        (0.40, 0.72, 0.08, 0.02),   # Deep red
        (0.60, 0.82, 0.28, 0.02),   # Dark orange
        (0.80, 0.70, 0.45, 0.02),   # Burnt amber
        (1.00, 0.12, 0.05, 0.05),   # Dark ash (edge)
    ]
    return _cs_direct_rgb(paint, shape, mask, seed, pm, bb, rgb_stops, shimmer=0.018)

def spec_cs_darkflame(shape, mask, seed, sm):
    return _spec_cs_v5(shape, mask, seed, sm, M_base=228, M_range=25, R_base=14, CC_range=55)  # Dark flame: heavy worn coat character - CC=16-71


# ================================================================
# SECTION 5: COLOR SHIFT DUO (75 pairs)
# Two-color chameleon paint pairs. Pure direct RGB - no HSV.
# Field power=2.5 biases ~70% of pixels toward color1 (face view).
# Color2 appears at the glancing edge.
#
# TO FIX A SPECIFIC PAIR:
#   Search for the pair name (e.g. "cs_black_silver")
#   Its colors come from CS_DUO_DEFS below.
#   The rendering logic is _make_colorshift_paint_direct - all pairs share it.
#   If the LOGIC is wrong, fix in _make_colorshift_paint_direct.
#   If the COLORS are wrong, fix in CS_DUO_DEFS.
# ================================================================

# Color palette reference (RGB float 0-1)
_CS_COLORS = {
    "racing_red":      (0.85, 0.05, 0.05),
    "fire_orange":     (0.95, 0.45, 0.02),
    "sunburst_yellow": (0.98, 0.88, 0.00),
    "lime_green":      (0.20, 0.90, 0.10),
    "forest_green":    (0.05, 0.40, 0.08),
    "teal":            (0.00, 0.60, 0.55),
    "sky_blue":        (0.30, 0.70, 0.95),
    "royal_blue":      (0.10, 0.25, 0.85),
    "navy":            (0.02, 0.05, 0.45),
    "purple":          (0.50, 0.00, 0.65),
    "violet":          (0.60, 0.10, 0.90),
    "hot_pink":        (0.95, 0.10, 0.55),
    "magenta":         (0.90, 0.00, 0.80),
    "white":           (0.96, 0.96, 0.96),
    "black":           (0.03, 0.03, 0.03),
    "gunmetal":        (0.22, 0.25, 0.28),
    "silver":          (0.75, 0.75, 0.78),
    "gold":            (0.90, 0.72, 0.05),
    "bronze":          (0.55, 0.35, 0.08),
    "copper":          (0.72, 0.38, 0.10),
    # Expansion colors
    "crimson":         (0.60, 0.00, 0.08),
    "jade":            (0.00, 0.55, 0.35),
    "coral":           (0.90, 0.40, 0.30),
    "cobalt":          (0.05, 0.10, 0.72),
    "amber":           (0.95, 0.68, 0.00),
    "indigo":          (0.22, 0.00, 0.62),
    "honey":           (0.95, 0.75, 0.10),
    "plum":            (0.55, 0.05, 0.40),
    "mint":            (0.15, 0.88, 0.60),
    "maroon":          (0.50, 0.00, 0.00),
    "rose":            (0.90, 0.25, 0.45),
    "emerald":         (0.00, 0.60, 0.20),
    "slate":           (0.44, 0.50, 0.56),
    "champagne":       (0.97, 0.91, 0.81),
    "titanium":        (0.53, 0.57, 0.61),
    "lavender":        (0.72, 0.60, 0.95),
    "charcoal":        (0.25, 0.25, 0.25),
    "ivory":           (1.00, 1.00, 0.94),
    "peach":           (0.98, 0.72, 0.55),
    "sage":            (0.55, 0.70, 0.50),
    "blush":           (0.95, 0.70, 0.75),
    "burgundy":        (0.50, 0.00, 0.13),
    "chocolate":       (0.48, 0.25, 0.00),
    "pewter":          (0.59, 0.59, 0.65),
    "graphite":        (0.25, 0.25, 0.25),
    "aqua":            (0.00, 0.88, 0.85),
}

# All 75 duo definitions: (key, color1_name, color2_name)
CS_DUO_DEFS = [
    # === ORIGINAL 25 ===
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
    # === BATCH 2: 30 more ===
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
    # === EXPANSION: 20 new ===
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


def _make_colorshift_paint_direct(r1, g1, b1, r2, g2, b2):
    """Factory: creates a direct RGB chameleon paint function for a color pair.

    No HSV. No brown artifacts. Black+Silver = actual black and silver.
    Field power=2.5 → ~70% of pixels show color1 (face color).
    Color2 appears at the glancing/edge zone.
    """
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = shape
        # Structural orientation field
        field = multi_scale_noise(shape, [96, 192, 48], [0.45, 0.35, 0.20], seed + 6000)
        field = np.clip(field * 0.5 + 0.5, 0, 1)
        # Non-linear: color1 dominates face view
        t = np.clip(np.power(field, 2.5), 0, 1)

        # Direct RGB - no HSV involved
        tr = r1 * (1.0 - t) + r2 * t
        tg = g1 * (1.0 - t) + g2 * t
        tb = b1 * (1.0 - t) + b2 * t

        blend = 0.90 * pm
        result = paint.copy()
        result[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + tr * mask * blend, 0, 1)
        result[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + tg * mask * blend, 0, 1)
        result[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + tb * mask * blend, 0, 1)

        # Brightness-only micro shimmer (no hue - avoids color contamination on neutrals)
        lum1 = 0.299 * r1 + 0.587 * g1 + 0.114 * b1
        lum2 = 0.299 * r2 + 0.587 * g2 + 0.114 * b2
        if lum1 > 0.04 or lum2 > 0.04:
            micro = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.35, 0.25], seed + 6100)
            shimmer = micro * 0.025 * pm * mask
            for c in range(3):
                result[:,:,c] = np.clip(result[:,:,c] + shimmer, 0, 1)

        return result
    return paint_fn


def _make_colorshift_spec():
    """Shared spec factory for all Color Shift Duo entries. High metallic for chameleon.
    CC_base=16 (max gloss), CC_range=40: field-driven variation spans 16-56.
    This gives the 75 pairs distinct coat character across the panel surface.
    """
    def spec_fn(shape, mask, seed, sm):
        return _spec_cs_v5(shape, mask, seed, sm,
                           M_base=215, M_range=35, R_base=12, R_range=15,
                           CC_base=16, CC_range=40)
    return spec_fn


def build_cs_duo_registry():
    """Build and return all 75 Color Shift Duo (spec_fn, paint_fn) tuples.
    Called by registry.py to populate MONOLITHIC_REGISTRY.
    """
    entries = {}
    shared_spec = _make_colorshift_spec()
    for key, c1_name, c2_name in CS_DUO_DEFS:
        r1, g1, b1 = _CS_COLORS[c1_name]
        r2, g2, b2 = _CS_COLORS[c2_name]
        paint_fn = _make_colorshift_paint_direct(r1, g1, b1, r2, g2, b2)
        entries[key] = (shared_spec, paint_fn)
    return entries


def get_cs_duo_metadata():
    """Return UI metadata for all 75 Color Shift Duo entries (for swatches)."""
    _DISPLAY_NAMES = {
        name: name.replace("_", " ").title()
        for name in _CS_COLORS
    }
    meta = {}
    for key, c1_name, c2_name in CS_DUO_DEFS:
        r1, g1, b1 = _CS_COLORS[c1_name]
        r2, g2, b2 = _CS_COLORS[c2_name]
        display = key.replace("cs_", "").replace("_", " / ").title()
        meta[key] = {
            "name": display,
            "category": "Color Shift",
            "swatch": [
                [int(r1*255), int(g1*255), int(b1*255)],
                [int(r2*255), int(g2*255), int(b2*255)],
            ],
        }
    return meta
