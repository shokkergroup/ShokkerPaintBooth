"""
Shokker Engine v2.0 - COLOR-BASED Zone Detection & Finish Application
======================================================================
BREAKTHROUGH: Uses actual pixel color analysis to create per-zone masks.

HOW IT WORKS:
1. User describes zones in natural language (or color values)
   Example: "The blue body panels => holographic_flake"
           "The gold swoosh => prismatic"
           "The dark/black areas => carbon_fiber"
           "The white numbers => gloss"

2. Engine ANALYZES the paint scheme's actual colors:
   - Converts each pixel to HSV/RGB
   - Clusters similar colors together
   - Matches user descriptions to color ranges

3. Creates PER-ZONE MASKS from color matching:
   - Each zone gets its own mask (0.0 to 1.0)
   - Masks are soft-edged (gaussian blur) for clean transitions
   - Zones can overlap - priority goes to most specific match

4. Applies DIFFERENT finishes to DIFFERENT zones using THEIR OWN masks

COLOR SELECTORS:
Each zone defines HOW to find its pixels using one or more selectors:
- "color_rgb": [R, G, B] + tolerance - match pixels near this color
- "color_range": {"r": [lo, hi], "g": [lo, hi], "b": [lo, hi]} - range match
- "hue_range": [lo, hi] + sat/val constraints - match by HSV hue
- "brightness": {"min": 0.0, "max": 0.3} - match by brightness level
- "saturation": {"min": 0.6, "max": 1.0} - match by color saturation
- "all_painted": true - everything that isn't blank/template
- "remainder": true - everything not claimed by other zones

MULTI-COLOR ZONES:
A zone's "color" field can be a LIST of selectors to union-match multiple colors.
All matched pixels receive the SAME finish. Great for multi-color car numbers.
Example: "color": [{"color_rgb": [255,170,0], "tolerance": 40},
                    {"color_rgb": [51,102,255], "tolerance": 40},
                    {"color_rgb": [200,30,30], "tolerance": 40}]

NATURAL LANGUAGE MAPPING (for Claude Code integration):
- "blue" => hue 200-260
- "red" => hue 340-20
- "yellow/gold" => hue 40-70
- "green" => hue 80-160
- "orange" => hue 20-45
- "purple" => hue 260-310
- "pink" => hue 310-340
- "white" => brightness > 0.85, saturation < 0.15
- "black/dark" => brightness < 0.15
- "gray" => saturation < 0.1, brightness 0.15-0.85
"""

import numpy as np
from PIL import Image, ImageFilter
import struct
import os
import json
import time


# ================================================================
# TGA WRITERS
# ================================================================

def write_tga_32bit(filepath, rgba_array):
    h, w = rgba_array.shape[:2]
    with open(filepath, 'wb') as f:
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 2))
        f.write(struct.pack('<5B', 0, 0, 0, 0, 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', w))
        f.write(struct.pack('<H', h))
        f.write(struct.pack('<B', 32))
        f.write(struct.pack('<B', 0x28))
        bgra = np.stack([rgba_array[:,:,2], rgba_array[:,:,1],
                         rgba_array[:,:,0], rgba_array[:,:,3]], axis=-1)
        f.write(bgra.tobytes())


def write_tga_24bit(filepath, rgb_array):
    h, w = rgb_array.shape[:2]
    with open(filepath, 'wb') as f:
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 2))
        f.write(struct.pack('<5B', 0, 0, 0, 0, 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', w))
        f.write(struct.pack('<H', h))
        f.write(struct.pack('<B', 24))
        f.write(struct.pack('<B', 0x20))
        bgr = np.stack([rgb_array[:,:,2], rgb_array[:,:,1], rgb_array[:,:,0]], axis=-1)
        f.write(bgr.tobytes())


# ================================================================
# NOISE GENERATORS
# ================================================================

# Coordinate grid cache — avoids re-allocating ~32MB per texture function call
_mgrid_cache = {}
def get_mgrid(shape):
    """Return cached (y, x) coordinate grids for the given (h, w) shape."""
    if shape not in _mgrid_cache:
        h, w = shape
        _mgrid_cache[shape] = np.mgrid[0:h, 0:w]
    return _mgrid_cache[shape]

def generate_perlin_noise_2d(shape, res, seed=None):
    if seed is not None:
        np.random.seed(seed)
    def f(t):
        return 6*t**5 - 15*t**4 + 10*t**3
    delta = (res[0]/shape[0], res[1]/shape[1])
    d = (shape[0]//res[0], shape[1]//res[1])
    grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1,2,0) % 1
    angles = 2*np.pi*np.random.rand(res[0]+1, res[1]+1)
    gradients = np.dstack((np.cos(angles), np.sin(angles)))
    g00 = gradients[:-1,:-1].repeat(d[0],0).repeat(d[1],1)
    g10 = gradients[1:,:-1].repeat(d[0],0).repeat(d[1],1)
    g01 = gradients[:-1,1:].repeat(d[0],0).repeat(d[1],1)
    g11 = gradients[1:,1:].repeat(d[0],0).repeat(d[1],1)
    n00 = np.sum(np.dstack((grid[:,:,0], grid[:,:,1]))*g00, 2)
    n10 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]))*g10, 2)
    n01 = np.sum(np.dstack((grid[:,:,0], grid[:,:,1]-1))*g01, 2)
    n11 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]-1))*g11, 2)
    t = f(grid)
    n0 = n00*(1-t[:,:,0]) + t[:,:,0]*n10
    n1 = n01*(1-t[:,:,0]) + t[:,:,0]*n11
    return np.sqrt(2)*((1-t[:,:,1])*n0 + t[:,:,1]*n1)


def perlin_multi_octave(shape, octaves=4, persistence=0.5, lacunarity=2.0, seed=42):
    """Generate multi-octave Perlin noise for organic, coherent material textures.

    Unlike random noise (np.random.randn), Perlin noise has spatial coherence —
    nearby pixels are correlated, producing natural-looking surface variation.

    Multi-octave layering adds detail at multiple scales:
      octave 1: large gentle hills (base frequency)
      octave 2: medium bumps (2x freq, 0.5x amplitude)
      octave 3: small ripples (4x freq, 0.25x amplitude)
      octave 4: fine grain (8x freq, 0.125x amplitude)

    Returns: normalized float32 array, range roughly [-1, 1]
    """
    h, w = shape
    # Ensure dimensions are workable for Perlin grid (need divisible dims)
    # Use minimum resolution of 4 for base octave
    result = np.zeros((h, w), dtype=np.float32)
    amplitude = 1.0
    frequency = 4  # base grid cells
    max_value = 0.0

    for i in range(octaves):
        # Perlin needs shape divisible by resolution — pad if needed
        res_y = min(frequency, h)
        res_x = min(frequency, w)
        # Ensure shape is divisible by resolution
        pad_h = int(np.ceil(h / res_y)) * res_y
        pad_w = int(np.ceil(w / res_x)) * res_x
        try:
            noise = generate_perlin_noise_2d((pad_h, pad_w), (res_y, res_x), seed=seed + i * 31)
            # Crop back to original size
            noise = noise[:h, :w]
        except Exception:
            # Fallback to scaled random if Perlin fails at this resolution
            np.random.seed(seed + i * 31)
            noise = np.random.randn(h, w).astype(np.float32)

        result += noise * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency = int(frequency * lacunarity)

    # Normalize to roughly [-1, 1]
    if max_value > 0:
        result = result / max_value
    return result


def multi_scale_noise(shape, scales, weights, seed=42):
    h, w = shape
    combined = np.zeros((h, w))
    total_weight = sum(weights)
    for scale, weight in zip(scales, weights):
        np.random.seed(seed + scale * 7)
        if scale == 1:
            noise = np.random.randn(h, w)
        else:
            small_h = max(1, h // scale)
            small_w = max(1, w // scale)
            small_noise = np.random.randn(small_h, small_w)
            noise_img = Image.fromarray(
                ((small_noise + 3) / 6 * 255).clip(0, 255).astype(np.uint8)
            )
            noise_img = noise_img.resize((w, h), Image.BILINEAR)
            noise = np.array(noise_img).astype(np.float32) / 255.0 * 2 - 1
        combined += noise * weight
    return combined / total_weight


def hsv_to_rgb_vec(h, s, v):
    c = v * s
    hp = h * 6.0
    x = c * (1 - np.abs(hp % 2 - 1))
    r = np.zeros_like(c); g = np.zeros_like(c); b = np.zeros_like(c)
    for lo in range(6):
        m = (hp >= lo) & (hp < lo+1)
        if lo==0: r[m]=c[m]; g[m]=x[m]
        elif lo==1: r[m]=x[m]; g[m]=c[m]
        elif lo==2: g[m]=c[m]; b[m]=x[m]
        elif lo==3: g[m]=x[m]; b[m]=c[m]
        elif lo==4: r[m]=x[m]; b[m]=c[m]
        elif lo==5: r[m]=c[m]; b[m]=x[m]
    off = v - c
    return r+off, g+off, b+off


# ================================================================
# INTENSITY PRESETS — Normalized (100% = 1.0 for all channels)
# All three values are identical per level — the percentage IS the multiplier.
# Channel-specific scaling happens at consumption via _INTENSITY_SCALE.
# ================================================================
INTENSITY = {
    "10":  {"paint": 0.10, "spec": 0.10, "bright": 0.10},
    "20":  {"paint": 0.20, "spec": 0.20, "bright": 0.20},
    "30":  {"paint": 0.30, "spec": 0.30, "bright": 0.30},
    "40":  {"paint": 0.40, "spec": 0.40, "bright": 0.40},
    "50":  {"paint": 0.50, "spec": 0.50, "bright": 0.50},
    "60":  {"paint": 0.60, "spec": 0.60, "bright": 0.60},
    "70":  {"paint": 0.70, "spec": 0.70, "bright": 0.70},
    "80":  {"paint": 0.80, "spec": 0.80, "bright": 0.80},
    "90":  {"paint": 0.90, "spec": 0.90, "bright": 0.90},
    "100": {"paint": 1.00, "spec": 1.00, "bright": 1.00},
}

# Channel-specific scale factors — converts normalized 0-1 intensity
# to the internal multiplier each channel actually needs.
# These bake in the "how much juice this channel needs" so the user
# never has to think about it — 100% just means full effect.
_INTENSITY_SCALE = {
    "paint": 1.50,   # paint functions need up to 1.5x multiplier for full effect
    "spec":  2.00,   # spec modulation needs up to 2.0x for visible texture
    "bright": 0.15,  # brightness boost caps at 0.15 (adds ~7-15% brightness)
}


# ================================================================
# COLOR ANALYSIS - THE NEW BRAIN
# ================================================================

def rgb_to_hsv_array(scheme):
    """Convert RGB float [0,1] array to HSV float [0,1] array."""
    r, g, b = scheme[:,:,0], scheme[:,:,1], scheme[:,:,2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc

    # Hue
    hue = np.zeros_like(r)
    mask_r = (maxc == r) & (delta > 0)
    mask_g = (maxc == g) & (delta > 0)
    mask_b = (maxc == b) & (delta > 0)
    hue[mask_r] = (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6) / 6.0
    hue[mask_g] = (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2) / 6.0
    hue[mask_b] = (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4) / 6.0

    # Saturation
    sat = np.zeros_like(r)
    sat[maxc > 0] = delta[maxc > 0] / maxc[maxc > 0]

    # Value
    val = maxc

    return np.stack([hue, sat, val], axis=-1)


def analyze_paint_colors(scheme):
    """Analyze paint and return HSV + stats for zone matching."""
    hsv = rgb_to_hsv_array(scheme)
    brightness = scheme[:,:,0]*0.299 + scheme[:,:,1]*0.587 + scheme[:,:,2]*0.114

    stats = {
        "hue": hsv[:,:,0],
        "sat": hsv[:,:,1],
        "val": hsv[:,:,2],
        "brightness": brightness,
        "rgb": scheme,
    }

    # Report dominant colors
    h, w = scheme.shape[:2]
    total_pixels = h * w
    bright_pct = np.sum(brightness > 0.85) / total_pixels * 100
    dark_pct = np.sum(brightness < 0.15) / total_pixels * 100
    saturated_pct = np.sum(hsv[:,:,1] > 0.3) / total_pixels * 100

    print(f"    Paint Analysis:")
    print(f"      Bright (>85%): {bright_pct:.1f}% of pixels")
    print(f"      Dark (<15%):   {dark_pct:.1f}% of pixels")
    print(f"      Saturated:     {saturated_pct:.1f}% of pixels")

    # Detect dominant hue ranges
    sat_mask = hsv[:,:,1] > 0.15  # Only count saturated pixels
    if np.any(sat_mask):
        hues = hsv[:,:,0][sat_mask] * 360
        for name, lo, hi in [
            ("Red", 340, 20), ("Orange", 20, 45), ("Yellow/Gold", 45, 70),
            ("Green", 70, 160), ("Cyan", 160, 200), ("Blue", 200, 260),
            ("Purple", 260, 310), ("Pink", 310, 340)
        ]:
            if lo > hi:  # Red wraps around
                count = np.sum((hues >= lo) | (hues < hi))
            else:
                count = np.sum((hues >= lo) & (hues < hi))
            pct = count / total_pixels * 100
            if pct > 1.0:
                print(f"      {name}: {pct:.1f}%")

    return stats


def build_zone_mask(scheme, stats, selector, blur_radius=3):
    """
    Build a zone mask from a color selector.

    Selector types:
    - {"color_rgb": [R,G,B], "tolerance": 30}
    - {"color_range": {"r": [lo,hi], "g": [lo,hi], "b": [lo,hi]}}
    - {"hue_range": [lo_deg, hi_deg], "sat_min": 0.2, "val_min": 0.1}
    - {"brightness": {"min": 0.0, "max": 0.3}}
    - {"saturation": {"min": 0.5, "max": 1.0}}
    - {"all_painted": True}  (everything with saturation OR not template gray)
    - {"remainder": True}  (handled separately after other zones)
    """
    h, w = scheme.shape[:2]
    mask = np.zeros((h, w), dtype=np.float32)

    if "color_rgb" in selector:
        # Match pixels near a specific RGB color
        target = np.array(selector["color_rgb"], dtype=np.float32) / 255.0
        tolerance = selector.get("tolerance", 30) / 255.0
        dist = np.sqrt(
            (scheme[:,:,0] - target[0])**2 +
            (scheme[:,:,1] - target[1])**2 +
            (scheme[:,:,2] - target[2])**2
        )
        # Soft falloff: 1.0 at center, 0.0 at tolerance edge
        mask = np.clip(1.0 - dist / (tolerance * np.sqrt(3)), 0, 1)

    elif "color_range" in selector:
        # Match pixels within RGB ranges
        cr = selector["color_range"]
        r_lo, r_hi = cr.get("r", [0, 255])
        g_lo, g_hi = cr.get("g", [0, 255])
        b_lo, b_hi = cr.get("b", [0, 255])
        rgb255 = (scheme * 255).astype(np.float32)
        r_match = (rgb255[:,:,0] >= r_lo) & (rgb255[:,:,0] <= r_hi)
        g_match = (rgb255[:,:,1] >= g_lo) & (rgb255[:,:,1] <= g_hi)
        b_match = (rgb255[:,:,2] >= b_lo) & (rgb255[:,:,2] <= b_hi)
        mask = (r_match & g_match & b_match).astype(np.float32)

    elif "hue_range" in selector:
        # Match by HSV hue range (in degrees 0-360)
        hue_lo, hue_hi = selector["hue_range"]
        sat_min = selector.get("sat_min", 0.15)
        sat_max = selector.get("sat_max", 1.0)
        val_min = selector.get("val_min", 0.05)
        val_max = selector.get("val_max", 1.0)

        hue_deg = stats["hue"] * 360.0
        sat = stats["sat"]
        val = stats["val"]

        # Hue matching (handles wrap-around for reds)
        if hue_lo > hue_hi:
            hue_match = (hue_deg >= hue_lo) | (hue_deg <= hue_hi)
        else:
            hue_match = (hue_deg >= hue_lo) & (hue_deg <= hue_hi)

        sat_match = (sat >= sat_min) & (sat <= sat_max)
        val_match = (val >= val_min) & (val <= val_max)

        mask = (hue_match & sat_match & val_match).astype(np.float32)

    elif "brightness" in selector:
        br = selector["brightness"]
        bmin = br.get("min", 0.0)
        bmax = br.get("max", 1.0)
        brightness = stats["brightness"]
        mask = ((brightness >= bmin) & (brightness <= bmax)).astype(np.float32)
        # Soft edge at boundaries
        edge = 0.05
        mask = np.where(brightness < bmin + edge,
                       np.clip((brightness - bmin) / edge, 0, 1), mask)
        mask = np.where(brightness > bmax - edge,
                       np.clip((bmax - brightness) / edge, 0, 1), mask)

    elif "saturation" in selector:
        sr = selector["saturation"]
        smin = sr.get("min", 0.0)
        smax = sr.get("max", 1.0)
        sat = stats["sat"]
        mask = ((sat >= smin) & (sat <= smax)).astype(np.float32)

    elif selector.get("all_painted"):
        # Everything that looks like actual paint (not template gray/white)
        sat = stats["sat"]
        brightness = stats["brightness"]
        # Painted = either has color (saturation) or is dark (intentional)
        mask = ((sat > 0.08) | (brightness < 0.25)).astype(np.float32)

    elif selector.get("remainder"):
        # Placeholder - handled in main loop after other zones
        mask = np.ones((h, w), dtype=np.float32)

    # Gaussian blur for soft edges
    if blur_radius > 0 and np.any(mask > 0):
        mask_img = Image.fromarray((mask * 255).astype(np.uint8))
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        mask = np.array(mask_img).astype(np.float32) / 255.0

    return mask


# ================================================================
# NATURAL LANGUAGE COLOR MAPPING
# ================================================================
# Maps common color words to selectors

COLOR_WORD_MAP = {
    # Hue-based colors (degrees)
    "red":         {"hue_range": [340, 20], "sat_min": 0.2},
    "orange":      {"hue_range": [15, 45], "sat_min": 0.2},
    "yellow":      {"hue_range": [45, 70], "sat_min": 0.2},
    "gold":        {"hue_range": [35, 55], "sat_min": 0.25, "val_min": 0.4},
    "green":       {"hue_range": [70, 160], "sat_min": 0.15},
    "lime":        {"hue_range": [70, 100], "sat_min": 0.3},
    "teal":        {"hue_range": [160, 200], "sat_min": 0.2},
    "cyan":        {"hue_range": [170, 200], "sat_min": 0.2},
    "blue":        {"hue_range": [200, 260], "sat_min": 0.15},
    "navy":        {"hue_range": [210, 250], "sat_min": 0.2, "val_max": 0.4},
    "purple":      {"hue_range": [260, 310], "sat_min": 0.15},
    "magenta":     {"hue_range": [290, 330], "sat_min": 0.2},
    "pink":        {"hue_range": [310, 350], "sat_min": 0.15},
    "maroon":      {"hue_range": [340, 15], "sat_min": 0.2, "val_max": 0.4},
    # Achromatic
    "white":       {"brightness": {"min": 0.85, "max": 1.0}},
    "light":       {"brightness": {"min": 0.7, "max": 1.0}},
    "gray":        {"saturation": {"min": 0.0, "max": 0.1}, "brightness": {"min": 0.15, "max": 0.85}},
    "dark":        {"brightness": {"min": 0.0, "max": 0.25}},
    "black":       {"brightness": {"min": 0.0, "max": 0.2}},
    # Special
    "everything":  {"all_painted": True},
    "body":        {"all_painted": True},
    "all":         {"all_painted": True},
    "remaining":   {"remainder": True},
    "rest":        {"remainder": True},
    "other":       {"remainder": True},
}


def parse_color_description(desc):
    """
    Parse a natural language color description into a selector.

    Examples:
    - "blue" => hue_range [200, 260]
    - "dark blue" => hue_range [200, 260] + val_max 0.4
    - "bright red" => hue_range [340, 20] + val_min 0.6
    - "rgb(255, 200, 0)" => color_rgb [255, 200, 0]
    - "#FF0000" => color_rgb [255, 0, 0]
    - "yellow/gold accents" => hue_range [35, 70]
    """
    desc = desc.lower().strip()

    # Try hex color
    if desc.startswith("#") and len(desc) == 7:
        r = int(desc[1:3], 16)
        g = int(desc[3:5], 16)
        b = int(desc[5:7], 16)
        return {"color_rgb": [r, g, b], "tolerance": 40}

    # Try rgb() notation
    if desc.startswith("rgb("):
        parts = desc.replace("rgb(", "").replace(")", "").split(",")
        if len(parts) == 3:
            return {"color_rgb": [int(p.strip()) for p in parts], "tolerance": 40}

    # Check for modifier + color word combos
    words = desc.replace("/", " ").replace("-", " ").split()

    # Find the primary color word
    selector = None
    for word in words:
        # Strip common non-color words
        if word in ("the", "a", "an", "areas", "area", "parts", "part", "panels",
                    "panel", "accents", "accent", "stripe", "stripes", "swoosh",
                    "trim", "decals", "decal", "logos", "logo", "numbers", "number",
                    "sponsors", "sponsor", "hood", "roof", "bumper", "skirt",
                    "fender", "door", "doors", "side", "front", "rear", "back",
                    "top", "bottom", "base", "main"):
            continue
        if word in COLOR_WORD_MAP:
            selector = dict(COLOR_WORD_MAP[word])
            break

    if selector is None:
        # Default: try to match everything as "all_painted"
        print(f"    WARNING: Could not parse color '{desc}', using all_painted")
        return {"all_painted": True}

    # Apply modifiers
    if "dark" in words or "deep" in words:
        if "hue_range" in selector:
            selector["val_max"] = selector.get("val_max", 0.45)
    if "bright" in words or "vivid" in words or "neon" in words:
        if "hue_range" in selector:
            selector["val_min"] = max(selector.get("val_min", 0.05), 0.55)
            selector["sat_min"] = max(selector.get("sat_min", 0.15), 0.4)
    if "light" in words or "pastel" in words:
        if "hue_range" in selector:
            selector["val_min"] = max(selector.get("val_min", 0.05), 0.6)
            selector["sat_max"] = min(selector.get("sat_max", 1.0), 0.5)

    return selector


# ================================================================
# SPEC MAP GENERATORS (identical to v1 - proven working)
# ================================================================

def spec_gloss(shape, mask, seed, sm):
    """Gloss -- standard clearcoat paint. Dielectric (M=0), very smooth (R=20), full clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(0 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=0 dielectric
    spec[:,:,1] = np.clip(20 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=20 smooth
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_matte(shape, mask, seed, sm):
    """Matte -- flat non-reflective paint. No metallic, very rough (R=215), no clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 0  # M=0 dielectric
    spec[:,:,1] = np.clip(215 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=215 very rough
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def spec_satin(shape, mask, seed, sm):
    """Satin -- semi-gloss between matte and gloss. No metallic, mid-rough (R=100), partial clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 0  # M=0 dielectric
    spec[:,:,1] = np.clip(100 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=100 mid
    spec[:,:,2] = 10; spec[:,:,3] = 255  # CC=10 partial clearcoat (not full 16)
    return spec

def spec_metallic(shape, mask, seed, sm):
    """Metallic -- standard metallic paint with visible micro-flake. M=200, R=50, visible flake texture."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [4, 8, 16], [0.2, 0.4, 0.4], seed+100)  # Visible flake scales
    spec[:,:,0] = np.clip(200 * mask + 5 * (1-mask) + mn * 40 * sm * mask, 0, 255).astype(np.uint8)  # M=200
    spec[:,:,1] = np.clip(50 * mask + 100 * (1-mask) + mn * 18 * sm * mask, 0, 255).astype(np.uint8)  # R=50
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_pearl(shape, mask, seed, sm):
    """Pearlescent -- moderate metallic so paint color shows through with soft iridescent sheen.
    M=100 (moderate, not chrome-like), R=40 (smooth but not mirror), large gentle waves."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    wave = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    # M=100: moderate metallic lets paint color shine through with pearlescent depth
    spec[:,:,0] = np.clip(100 * mask + 5 * (1-mask) + wave * 20 * sm * mask, 0, 255).astype(np.uint8)
    # R=40: smooth but not mirror — soft diffuse glow, not sharp reflection
    spec[:,:,1] = np.clip(40 * mask + 100 * (1-mask) + wave * 12 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_chrome(shape, mask, seed, sm):
    """Chrome -- pure mirror. Max metallic, near-zero roughness, NO clearcoat (raw metal)."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(255 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=255 full metal
    spec[:,:,1] = np.clip(2 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=2 mirror smooth
    spec[:,:,2] = 0; spec[:,:,3] = 255  # CC=0 raw chrome, no clearcoat
    return spec

def spec_satin_metal(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    np.random.seed(seed)
    brush = np.random.randn(1, w) * 0.5
    brush = np.tile(brush, (h, 1))
    brush += np.random.randn(h, w) * 0.2
    spec[:,:,0] = np.clip(235 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(65 * mask + 100 * (1-mask) + brush * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_metal_flake(shape, mask, seed, sm):
    """Metal flake -- heavy metallic with coarse visible flake sparkle. Like classic hot rod paint."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [4, 8, 16, 32], [0.1, 0.2, 0.35, 0.35], seed+100)  # Visible flake
    rf = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+200)
    spec[:,:,0] = np.clip(240 * mask + 5 * (1-mask) + mf * 50 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(12 * mask + 100 * (1-mask) + rf * 40 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_holographic_flake(shape, mask, seed, sm):
    """Holographic flake -- prismatic micro-grid that creates rainbow diffraction.
    Unlike metal_flake (random coarse sparkle), this has fine directional stripe interference.
    The grid creates the holographic 'rainbow shift' effect in-sim."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Fine diagonal micro-grid — creates prismatic interference
    grid_size = 8  # Fine grid for holographic shimmer
    diag1 = np.sin((x + y) * np.pi / grid_size) * 0.5 + 0.5
    diag2 = np.sin((x - y) * np.pi / (grid_size * 1.3)) * 0.5 + 0.5
    holo = diag1 * 0.6 + diag2 * 0.4  # Cross-hatch interference
    # Add per-flake sparkle on top of grid
    rng = np.random.RandomState(seed + 100)
    sparkle = rng.random((h, w)).astype(np.float32)
    bright_flakes = (sparkle > (1.0 - 0.03 * sm)).astype(np.float32)
    spec[:,:,0] = np.clip(245 * mask + 5 * (1-mask) + bright_flakes * 10 * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 + holo * 40 * sm) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_stardust(shape, mask, seed, sm):
    """Stardust -- dark mirror base with sparse bright pinpoint stars scattered across surface."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Dark mirror base: medium-high metallic, moderate roughness (so paint color shows)
    spec[:,:,0] = np.clip(160 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(55 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    # Scatter bright star points: ultra-smooth mirror pinpoints that flash in light
    rng = np.random.RandomState(seed + 100)
    star_field = rng.random((h, w)).astype(np.float32)
    # Density: ~2% of pixels become stars (sparse enough to see individual sparkles)
    stars = (star_field > (1.0 - 0.02 * sm)).astype(np.float32)
    # Stars: max metallic, zero roughness = bright pinpoint flashes
    spec[:,:,0] = np.clip(spec[:,:,0].astype(np.float32) + stars * 95 * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.where(stars > 0.5, np.clip(3 * mask + 100 * (1-mask), 0, 255), spec[:,:,1]).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_candy(shape, mask, seed, sm):
    """Candy -- deep transparent gloss like looking through tinted glass at a metallic base.
    M=130 (moderate metallic so color shows through), R=15 (very smooth wet surface), full clearcoat.
    Key: lower metallic than chrome lets the paint color dominate with depth."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(130 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=130 lets color show
    spec[:,:,1] = np.clip(15 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=15 wet smooth
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_brushed_titanium(shape, mask, seed, sm):
    """Brushed titanium -- STRONG directional horizontal grain with moderate metallic.
    Unlike satin_metal (subtle brush), this has aggressive visible grain lines."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    # Heavy directional grain: each row is a brush stroke, minimal vertical variation
    row_grain = rng.randn(h, 1).astype(np.float32) * 0.8
    row_grain = np.tile(row_grain, (1, w))
    # Add slight per-pixel variation (but keep directional character)
    row_grain += rng.randn(h, w).astype(np.float32) * 0.1
    # Medium metallic (not chrome-mirror, shows as brushed metal)
    spec[:,:,0] = np.clip(180 * mask + 5 * (1-mask) + row_grain * 25 * sm * mask, 0, 255).astype(np.uint8)
    # Roughness dominated by grain direction: visible streaks of smooth/rough
    spec[:,:,1] = np.clip(70 * mask + 100 * (1-mask) + row_grain * 45 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # no clearcoat = raw metal look
    return spec

def spec_anodized(shape, mask, seed, sm):
    """Anodized aluminum -- matte metallic with fine industrial grain and NO clearcoat.
    Higher roughness than pearl/metallic, gritty industrial feel. Color pops through the matte."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Visible industrial grain texture
    grain = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    # Medium metallic: enough to reflect but not mirror-chrome
    spec[:,:,0] = np.clip(170 * mask + 5 * (1-mask) + grain * 20 * sm * mask, 0, 255).astype(np.uint8)
    # HIGH roughness base (80) with grain variation: gritty matte surface
    spec[:,:,1] = np.clip(80 * mask + 100 * (1-mask) + grain * 25 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # NO clearcoat = raw anodized look
    return spec

def spec_hex_mesh(shape, mask, seed, sm):
    """Hex mesh -- honeycomb wire grid where wire is matte and hex centers are chrome mirror.
    Like looking through metallic chicken wire. Visible geometric pattern at car scale."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 24  # visible at car scale
    # Hex grid coordinates
    row = y / (hex_size * 0.866)  # sqrt(3)/2 spacing
    col = x / hex_size
    # Offset every other row
    col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
    # Distance from nearest hex center
    row_round = np.round(row)
    col_round = np.round(col_shifted)
    cy = row_round * hex_size * 0.866
    cx = (col_round + 0.5 * (row_round.astype(int) % 2)) * hex_size
    dist = np.sqrt((y - cy)**2 + (x - cx)**2)
    # Normalize: 0=center, 1=edge
    norm_dist = np.clip(dist / (hex_size * 0.45), 0, 1)
    # Wire frame: the outer ring of each hex
    wire = (norm_dist > 0.75).astype(np.float32)
    center = 1.0 - wire
    # Wire: matte rough metal. Center: chrome mirror
    spec[:,:,0] = np.clip((255 * center + 100 * wire) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 * center + 160 * wire) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_frozen(shape, mask, seed, sm):
    """Frozen -- icy matte metal. High metallic, high roughness, no clearcoat.
    Frost crystals visible as large-scale noise patches."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)  # Visible frost patches
    spec[:,:,0] = np.clip(225 * mask + 5 * (1-mask) + mn * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(140 * mask + 100 * (1-mask) + mn * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def spec_carbon_fiber(shape, mask, seed, sm):
    """Carbon fiber 2x2 twill weave — visible crosshatch pattern at car scale.
    Weave threads alternate shiny/matte creating the classic carbon look.
    Metallic ~50 (semi-metallic resin-coated fiber), low roughness on weave peaks."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Weave size 24px = visible threads at 2048x2048 car scale
    weave_size = 24
    # 2x2 twill: two threads over, two under — classic carbon weave
    # Diagonal bias creates the characteristic angled crosshatch
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)  # 0-1 per horizontal repeat
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)  # 0-1 per vertical repeat
    # Horizontal tows vs vertical tows — 2x2 twill offset
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5  # horizontal thread shape
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5   # vertical thread shape
    # Twill: which thread is on top alternates in a diagonal pattern
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    # Thread edge definition — sharper transitions between tows
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Spec channels: fiber peaks are smoother/shinier, valleys are rougher
    spec[:,:,0] = np.clip(55 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # Metallic: semi-metallic
    spec[:,:,1] = np.clip((30 + cf * 50 * sm) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # Roughness: weave varies 30-80
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_ripple(shape, mask, seed, sm):
    """Ripple -- concentric expanding rings like a water drop impact on liquid metal.
    Multiple ring origins create overlapping interference-like patterns. Visible at car scale."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Multiple ring origins scattered across the surface
    rng = np.random.RandomState(seed + 100)
    num_origins = int(6 + sm * 4)  # 6-10 ring centers
    ripple_sum = np.zeros((h, w), dtype=np.float32)
    for _ in range(num_origins):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2).astype(np.float32)
        ring_spacing = rng.uniform(20, 40)  # visible ring spacing
        ripple = np.sin(dist / ring_spacing * 2 * np.pi)
        # Fade out with distance from origin
        fade = np.clip(1.0 - dist / (max(h, w) * 0.6), 0, 1)
        ripple_sum += ripple * fade
    # Normalize
    rmax = np.abs(ripple_sum).max() + 1e-8
    ripple_norm = ripple_sum / rmax
    # Ring peaks: chrome mirror smooth. Ring valleys: matte rough
    ring_val = (ripple_norm + 1.0) * 0.5  # 0-1
    spec[:,:,0] = np.clip((240 * ring_val + 140 * (1-ring_val)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 * ring_val + 90 * (1-ring_val)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_hammered(shape, mask, seed, sm):
    """Hammered metal -- random circular dimple impacts across surface like hand-hammered copper.
    Each dimple is a smooth concave mirror, flat areas between are matte. Visible texture."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Generate random dimple positions
    rng = np.random.RandomState(seed + 100)
    num_dimples = int(400 * sm)
    dimple_y = rng.randint(0, h, num_dimples).astype(np.float32)
    dimple_x = rng.randint(0, w, num_dimples).astype(np.float32)
    dimple_r = rng.randint(8, 22, num_dimples).astype(np.float32)
    # Downsample 4x for speed
    ds = 4
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = (yg * ds).astype(np.float32)
    xg = (xg * ds).astype(np.float32)
    dimple_small = np.zeros((sh, sw), dtype=np.float32)
    for dy, dx, dr in zip(dimple_y, dimple_x, dimple_r):
        # Only compute within bounding box of each dimple (massive speedup)
        y_lo = max(0, int((dy - dr) / ds))
        y_hi = min(sh, int((dy + dr) / ds) + 1)
        x_lo = max(0, int((dx - dr) / ds))
        x_hi = min(sw, int((dx + dr) / ds) + 1)
        if y_hi <= y_lo or x_hi <= x_lo:
            continue
        sub_y = yg[y_lo:y_hi, x_lo:x_hi]
        sub_x = xg[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((sub_y - dy)**2 + (sub_x - dx)**2)
        dimple = np.clip(1.0 - dist / dr, 0, 1) ** 2
        dimple_small[y_lo:y_hi, x_lo:x_hi] = np.maximum(
            dimple_small[y_lo:y_hi, x_lo:x_hi], dimple)
    # Upsample
    dimple_img = Image.fromarray((dimple_small * 255).astype(np.uint8))
    dimple_img = dimple_img.resize((w, h), Image.BILINEAR)
    dimple_map = np.array(dimple_img).astype(np.float32) / 255.0
    # Dimple centers: smooth mirror. Flat areas between: matte rough
    spec[:,:,0] = np.clip((245 * dimple_map + 150 * (1-dimple_map)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((8 * dimple_map + 120 * (1-dimple_map)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # no clearcoat = raw hammered metal
    return spec

def spec_lightning(shape, mask, seed, sm):
    """Lightning bolt -- bright forked bolt paths on a dark matte surface.
    Unlike plasma (thin veins everywhere), lightning has THICK main bolts with thin forks.
    High contrast: bolt = chrome mirror, background = dark matte."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Generate lightning using random walk paths
    rng = np.random.RandomState(seed + 100)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    num_bolts = int(3 + sm * 2)  # 3-5 main bolts
    for b in range(num_bolts):
        # Start from random edge position
        py = rng.randint(0, h // 4)
        px = rng.randint(w // 4, 3 * w // 4)
        thickness = rng.randint(4, 8)  # main bolt width
        # Walk downward with random jitter (lightning goes top to bottom)
        for step in range(h * 2):
            py += rng.randint(1, 4)  # mostly downward
            px += rng.randint(-6, 7)  # horizontal jitter
            if py >= h:
                break
            px = max(0, min(w - 1, px))
            # Draw thick bolt
            y_lo = max(0, py - thickness)
            y_hi = min(h, py + thickness + 1)
            x_lo = max(0, px - thickness)
            x_hi = min(w, px + thickness + 1)
            bolt_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                bolt_map[y_lo:y_hi, x_lo:x_hi], 1.0)
            # Random fork branches
            if rng.random() < 0.03:
                fork_px, fork_py = px, py
                fork_thick = max(1, thickness // 2)
                fork_dir = rng.choice([-1, 1])
                for _ in range(rng.randint(20, 80)):
                    fork_py += rng.randint(1, 3)
                    fork_px += fork_dir * rng.randint(1, 5)
                    if fork_py >= h or fork_px < 0 or fork_px >= w:
                        break
                    fy_lo = max(0, fork_py - fork_thick)
                    fy_hi = min(h, fork_py + fork_thick + 1)
                    fx_lo = max(0, fork_px - fork_thick)
                    fx_hi = min(w, fork_px + fork_thick + 1)
                    bolt_map[fy_lo:fy_hi, fx_lo:fx_hi] = np.maximum(
                        bolt_map[fy_lo:fy_hi, fx_lo:fx_hi], 0.7)
    # Slight blur to soften bolt edges (using PIL, no scipy dependency)
    bolt_pil = Image.fromarray((bolt_map * 255).astype(np.uint8), 'L')
    bolt_pil = bolt_pil.filter(ImageFilter.GaussianBlur(radius=1.5))
    bolt_map = np.array(bolt_pil).astype(np.float32) / 255.0
    bolt_map = np.clip(bolt_map, 0, 1)
    # Background: dark matte. Bolts: chrome mirror = extreme contrast
    spec[:,:,0] = np.clip((255 * bolt_map + 80 * (1-bolt_map)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((3 * bolt_map + 180 * (1-bolt_map)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_frost_bite(shape, mask, seed, sm):
    """Frost bite -- aggressive frozen metal. Higher roughness than frozen, no clearcoat.
    Rougher and more crystalline than 'frozen' — visible ice crystal patches."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)  # Visible crystal patches
    rn = multi_scale_noise(shape, [8, 16, 24], [0.3, 0.4, 0.3], seed+200)
    spec[:,:,0] = np.clip(230 * mask + 5 * (1-mask) + mn * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(160 * mask + 100 * (1-mask) + rn * 40 * sm * mask, 0, 255).astype(np.uint8)  # R=160 rougher than frozen
    spec[:,:,2] = 0; spec[:,:,3] = 255  # CC=0 raw frozen metal, no clearcoat
    return spec


# ================================================================
# NEW SPEC GENERATORS - Exotic Finishes
# ================================================================

def spec_battle_worn(shape, mask, seed, sm):
    """Scratched weathered metal -- variable clearcoat, wild roughness variation."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    mn = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed+100)
    # Scratch pattern: directional noise
    rng = np.random.RandomState(seed + 301)
    scratch_noise = rng.randn(1, w) * 0.6
    scratch_noise = np.tile(scratch_noise, (h, 1))
    scratch_noise += rng.randn(h, w) * 0.3
    spec[:,:,0] = np.clip(200 * mask + 5 * (1-mask) + mn * 30 * sm * mask + scratch_noise * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(50 * mask + 100 * (1-mask) + scratch_noise * 80 * sm * mask + mn * 40 * sm * mask, 0, 255).astype(np.uint8)
    # VARIABLE clearcoat: 0-16 based on scratch damage
    cc_noise = np.clip((mn + 0.5) * 16, 0, 16)
    spec[:,:,2] = np.clip(cc_noise * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_diamond_plate(shape, mask, seed, sm):
    """Diamond tread plate -- LARGE geometric diamond pattern, visible at car scale."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    diamond_size = 32  # Bigger diamonds (was 12) so visible on the car
    dx = (x % diamond_size) - diamond_size / 2
    dy = (y % diamond_size) - diamond_size / 2
    diamond = ((np.abs(dx) + np.abs(dy)) < diamond_size * 0.38).astype(np.float32)
    # Diamonds are smooth mirror, flat areas are rough = huge visual contrast
    spec[:,:,0] = np.clip((240 * diamond + 180 * (1-diamond)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((8 * diamond + 140 * (1 - diamond)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # no clearcoat, raw metal
    return spec

def spec_dragon_scale(shape, mask, seed, sm):
    """Overlapping scale pattern -- mirror centers, rough matte edges. BIG scales."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    scale_size = 40  # MUCH bigger scales (was 16) so you can actually SEE them on the car
    y, x = get_mgrid((h, w))
    row = y // scale_size
    col = (x + (row % 2) * (scale_size // 2)) // scale_size
    cy = (row + 0.5) * scale_size
    cx = col * scale_size + (row % 2) * (scale_size // 2) + scale_size // 2
    dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (scale_size * 0.55)
    dist = np.clip(dist, 0, 1)
    # Centers: chrome mirror. Edges: rough matte (HUGE contrast so you see the scales)
    spec[:,:,0] = np.clip((255 * (1-dist) + 120 * dist) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((3 * (1-dist) + 160 * dist) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_worn_chrome(shape, mask, seed, sm):
    """Patchy chrome with worn areas -- all 3 channels variable."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [4, 8, 16], [0.2, 0.4, 0.4], seed+100)
    wear = np.clip((mn + 0.3) * 1.5, 0, 1)  # patchy wear map
    # Chrome patches: high R, low G. Worn patches: lower R, higher G
    spec[:,:,0] = np.clip((255 * (1-wear) + 100 * wear) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((2 * (1-wear) + 120 * wear) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    # Clearcoat worn through in damaged spots
    cc = np.clip(16 * (1-wear), 0, 16)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_liquid_metal(shape, mask, seed, sm):
    """Mercury/T-1000 -- chrome mirror with large visible pooling distortions."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    wave = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    # Max metallic everywhere, but roughness has large flowing pools
    # Some areas mirror-smooth (G=2), other areas slightly diffuse (G=40)
    spec[:,:,0] = np.clip(255 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    pool = np.clip((wave + 0.5) * 1.3, 0, 1)
    spec[:,:,1] = np.clip((2 * (1-pool) + 50 * pool) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # CC=0 raw liquid metal, no clearcoat
    return spec

def spec_plasma(shape, mask, seed, sm):
    """Electric plasma -- branching vein pattern visible as roughness contrast."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    n1 = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed+100)
    n2 = multi_scale_noise(shape, [1, 3, 6, 12], [0.2, 0.3, 0.3, 0.2], seed+200)
    veins = np.abs(n1 + n2 * 0.5)
    vein_mask_f = np.clip(1.0 - veins * 3.0, 0, 1) ** 2  # thin bright lines
    # Veins are mirror-smooth chrome, background is matte -- visible lightning pattern
    spec[:,:,0] = np.clip((255 * vein_mask_f + 160 * (1-vein_mask_f)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((2 * vein_mask_f + 120 * (1-vein_mask_f)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_ember_glow(shape, mask, seed, sm):
    """Hot ember -- medium metallic with mid clearcoat for warm depth."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    hot_mask = np.clip((mn + 0.2) * 2.0, 0, 1)
    spec[:,:,0] = np.clip((180 + hot_mask * 40) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(40 * mask + 100 * (1-mask) + mn * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16  # Full clearcoat (iRacing: 0-15=OFF, 16=ON)
    spec[:,:,3] = 255
    return spec

def spec_acid_wash(shape, mask, seed, sm):
    """Acid etched -- splotchy high-variance roughness, corroded clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    etch = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    spec[:,:,0] = np.clip(200 * mask + 5 * (1-mask) + etch * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(60 * mask + 100 * (1-mask) + etch * 60 * sm * mask, 0, 255).astype(np.uint8)
    # Clearcoat eaten away in heavily etched areas
    etch_depth = np.clip(np.abs(etch) * 2, 0, 1)
    cc = np.clip(16 * (1 - etch_depth * 0.8), 0, 16)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_hologram(shape, mask, seed, sm):
    """Holographic projection -- horizontal scanline banding visible in roughness."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y = np.arange(h).reshape(-1, 1)
    # Visible scanline bands in the roughness channel (alternating smooth/rough rows)
    scanline = ((y % 6) < 3).astype(np.float32)
    scanline = np.broadcast_to(scanline, (h, w))
    spec[:,:,0] = np.clip(220 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    # Roughness alternates: 5 on bright lines, 80 on dark lines = visible line pattern
    spec[:,:,1] = np.clip((5 * scanline + 80 * (1 - scanline)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_interference(shape, mask, seed, sm):
    """Thin-film interference -- flowing rainbow bands via roughness waves."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Large flowing wave bands that create visible stripes of different reflectivity
    wave = np.sin(y * 0.02 + x * 0.01) * 0.4 + np.sin(y * 0.01 - x * 0.015) * 0.3 + \
           np.sin((y + x) * 0.008) * 0.3
    wave = (wave + 1.0) * 0.5  # normalize 0-1
    # High metallic with wave-modulated roughness = visible flowing bands on the car
    spec[:,:,0] = np.clip(240 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 + wave * 100) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def _forged_carbon_chunks(shape, seed):
    """Generate forged carbon chunk pattern — irregular angular fiber patches.
    Returns a float array [0..1] where different value ranges = different chunks.
    Uses large-scale smooth noise with hard quantisation for chunk boundaries."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Layer 1: large smooth blobs (the main chunk shapes) — tighter for realistic forged CF
    s1h, s1w = max(1, h // 24), max(1, w // 24)
    raw1 = rng.randn(s1h, s1w).astype(np.float32)
    img1 = Image.fromarray(((raw1 + 3) / 6 * 255).clip(0, 255).astype(np.uint8))
    n1 = np.array(img1.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # Layer 2: medium detail (breaks up the blobs into angular sub-chunks)
    s2h, s2w = max(1, h // 12), max(1, w // 12)
    raw2 = rng.randn(s2h, s2w).astype(np.float32)
    img2 = Image.fromarray(((raw2 + 3) / 6 * 255).clip(0, 255).astype(np.uint8))
    n2 = np.array(img2.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # Layer 3: fine grain for surface texture within chunks
    s3h, s3w = max(1, h // 4), max(1, w // 4)
    raw3 = rng.randn(s3h, s3w).astype(np.float32)
    img3 = Image.fromarray(((raw3 + 3) / 6 * 255).clip(0, 255).astype(np.uint8))
    n3 = np.array(img3.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # Combine: large shapes dominate, medium adds sub-structure, fine adds grain
    combined = n1 * 0.55 + n2 * 0.35 + n3 * 0.10
    # Quantise into ~8-12 discrete chunk levels for sharp boundaries
    num_levels = 10
    quantised = np.floor(combined * num_levels) / num_levels
    # Normalise to [0, 1]
    qmin, qmax = quantised.min(), quantised.max()
    if qmax > qmin:
        quantised = (quantised - qmin) / (qmax - qmin)
    return quantised, n3  # return fine noise too for per-chunk sheen

def spec_forged_carbon(shape, mask, seed, sm):
    """Chopped carbon fiber — irregular chunks with varying roughness/reflectivity.
    Each chunk is a pressed fiber strand at a random angle, creating subtle
    differences in roughness and metallic response across the surface."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    chunks, fine = _forged_carbon_chunks(shape, seed + 100)
    # Metallic: moderate-high, slight per-chunk variation (carbon is semi-metallic)
    metal_base = 60 + chunks * 40 * sm  # 60..100 range
    spec[:,:,0] = np.clip(metal_base * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # Roughness: each chunk has slightly different roughness (fiber orientation)
    # Lower roughness = shinier chunk face, higher = matte fiber edge
    rough_base = 25 + chunks * 50 * sm + fine * 8 * sm  # 25..83 range
    spec[:,:,1] = np.clip(rough_base * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # Clearcoat: ON (real forged carbon has epoxy clearcoat, B=16=ON in iRacing)
    spec[:,:,2] = np.clip(16 * mask + 0 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_cracked_ice(shape, mask, seed, sm):
    """Frozen cracked surface -- smooth ice with rough crack lines."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Simplified crack pattern using noise zero-crossings
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed+200)
    # Cracks where noise is near zero
    crack1 = np.exp(-n1**2 * 20)
    crack2 = np.exp(-n2**2 * 20)
    cracks = np.clip(crack1 + crack2, 0, 1)
    mn = multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed+300)
    spec[:,:,0] = np.clip((230 + mn * 15 * sm) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    # Smooth ice (15) vs rough cracks (130)
    spec[:,:,1] = np.clip((15 * (1-cracks) + 130 * cracks) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_phantom(shape, mask, seed, sm):
    """Phantom -- ultra-mirror finish that makes paint vanish into reflections.
    High metallic + near-zero roughness = environment reflects instead of paint color.
    Paint 'disappears' at most angles, ghosts back when lighting is just right.
    Noise pattern creates hot spots where paint peeks through vs fully vanished."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Noise for where paint "peeks through" vs fully mirrored
    peek = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    peek_map = np.clip((peek + 0.3) * 0.8, 0, 1)  # mostly mirrored, some peek spots
    # R = very high metallic everywhere (mirror behavior)
    spec[:,:,0] = np.clip((245 - peek_map * 30 * sm) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    # G = the key: ultra-low roughness makes the color vanish into reflections
    # Near 0 = perfect mirror (color invisible), 15-25 = slight diffuse (color peeks through)
    spec[:,:,1] = np.clip((2 + peek_map * 20 * sm) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    # B = max clearcoat for glossy wet look
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def paint_phantom_fade(paint, shape, mask, seed, pm, bb):
    """Phantom paint -- slightly desaturate and brighten to enhance the mirror vanishing effect.
    The paint color becomes more 'ghostly' so when it does peek through reflections,
    it looks ethereal rather than solid."""
    h, w = shape
    # Slight desaturation: push toward silver/white to enhance mirror
    gray = paint.mean(axis=2, keepdims=True)
    desat = 0.25 * pm
    paint = paint * (1 - desat * mask[:,:,np.newaxis]) + gray * desat * mask[:,:,np.newaxis]
    # Brighten slightly so the color reads cleaner when it peeks through
    paint = np.clip(paint + bb * 1.5 * mask[:,:,np.newaxis], 0, 1)
    # Subtle noise shimmer
    shimmer = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 500)
    paint = np.clip(paint + shimmer[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def spec_blackout(shape, mask, seed, sm):
    """Stealth murdered-out -- minimal metallic, max rough, no clearcoat. Full spec authority."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(30 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=30 near-zero
    spec[:,:,1] = np.clip(220 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=220 very rough
    spec[:,:,2] = 0  # No clearcoat
    spec[:,:,3] = 255  # Full spec authority (A=255)
    return spec


# ================================================================
# PAINT MODIFIERS (SUBTLE - no color shifts)
# ================================================================

def paint_none(paint, shape, mask, seed, pm, bb):
    return paint

def paint_subtle_flake(paint, shape, mask, seed, pm, bb):
    """Fine metallic flake -- subtle sparkle texture on the base paint.
    Mostly a spec map effect; paint changes are minimal."""
    for c in range(3):
        flake = multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.05 * pm * mask, 0, 1)  # Was 0.10
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)  # Was bb*1.5
    return paint

def paint_fine_sparkle(paint, shape, mask, seed, pm, bb):
    """Fine sparkle points -- candy/pearl glitter effect.
    Mostly a spec map effect; paint changes are minimal."""
    flake = multi_scale_noise(shape, [1], [1.0], seed + 50)
    h, w = shape
    rng = np.random.RandomState(seed + 77)
    sparkle = rng.random((h, w)).astype(np.float32)
    sparkle = np.where(sparkle > 0.96, sparkle * 0.10 * pm, 0)  # Was 0.95/0.25
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.04 * pm * mask + sparkle * mask, 0, 1)  # Was 0.08
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)  # Was bb*1.5
    return paint

def paint_coarse_flake(paint, shape, mask, seed, pm, bb):
    """Coarse metallic flake -- holographic/prismatic color shift visible in paint.
    Subtle enough to add sparkle without destroying the base paint design.
    The spec map handles the real metallic/flake appearance."""
    h, w = shape
    r_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+11)
    g_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+22)
    b_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+33)
    strength = 0.06 * pm  # Was 0.14 — too aggressive, spec does the real work
    paint[:,:,0] = np.clip(paint[:,:,0] + r_flake * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + g_flake * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + b_flake * strength * mask, 0, 1)
    # Sparkle glints -- visible bright spots (rare, subtle)
    rng = np.random.RandomState(seed + 99)
    glint = rng.random((h, w)).astype(np.float32)
    glint = np.where(glint > 0.96, glint * 0.08 * pm, 0)  # Was 0.94/0.18 — too many/strong
    paint = np.clip(paint + glint[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)  # Was bb*2.0 — insane
    return paint

def paint_carbon_darken(paint, shape, mask, seed, pm, bb):
    """Carbon fiber weave -- visible crosshatch darkening matching the spec pattern.
    Uses same 6px weave_size as texture_carbon_fiber for alignment."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 6  # Must match texture_carbon_fiber
    # Same 2x2 twill pattern as spec function
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Adaptive: dark paint gets lightened weave, light paint gets darkened weave
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    is_dark = np.clip((0.2 - brightness) / 0.15, 0, 1)  # smooth transition
    darken_strength = 0.10 * pm
    lighten_strength = 0.07 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            - cf * darken_strength * (1 - is_dark) * mask
            + cf * lighten_strength * is_dark * mask, 0, 1)
    # Weave peak sheen — subtle glossy highlight on raised threads
    sheen = np.clip(cf - 0.4, 0, 0.6) / 0.6
    paint = np.clip(paint + sheen[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_chrome_brighten(paint, shape, mask, seed, pm, bb):
    """Chrome mirror effect -- pushes paint toward bright reflective silver.
    SUBTLER than before: adds a chrome sheen without destroying the base paint.
    The spec map does the heavy lifting for chrome appearance."""
    blend = 0.22 * pm  # Bumped from 0.15 — PBR research: metallic albedo needs brighter for chrome to read correctly
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend) + 0.92 * mask * blend
    h, w = shape
    reflection = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 150)
    paint = np.clip(paint + reflection[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# FINISH REGISTRY
# ================================================================

# ================================================================
# NEW PAINT MODIFIERS - Exotic Effects
# ================================================================

def paint_scratch_marks(paint, shape, mask, seed, pm, bb):
    """Battle-worn scratches -- directional linear marks across the surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 300)
    scratches = np.zeros((h, w), dtype=np.float32)
    num_scratches = int(120 * pm)
    for _ in range(num_scratches):
        y0 = rng.randint(0, h)
        x0 = rng.randint(0, w)
        angle = rng.uniform(-0.3, 0.3)
        length = rng.randint(50, 400)
        for t in range(length):
            yi = int(y0 + t * np.sin(angle))
            xi = int(x0 + t * np.cos(angle))
            if 0 <= yi < h and 0 <= xi < w:
                width = rng.randint(1, 3)
                for dy in range(-width, width + 1):
                    yy = yi + dy
                    if 0 <= yy < h:
                        scratches[yy, xi] = max(scratches[yy, xi], rng.uniform(0.3, 1.0))
    # Scratches brighten on dark paint, darken on light paint
    brightness = paint.mean(axis=2)
    is_dark = (brightness < 0.15).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + scratches * 0.12 * pm * mask * is_dark        # lighten scratches on dark
            - scratches * 0.10 * pm * mask * (1 - is_dark),  # darken scratches on light
        0, 1)
    return paint

def paint_diamond_emboss(paint, shape, mask, seed, pm, bb):
    """Diamond plate -- geometric raised diamond shapes visible on paint."""
    h, w = shape
    y, x = get_mgrid((h, w))
    diamond_size = 16
    dx = (x % diamond_size) - diamond_size / 2
    dy = (y % diamond_size) - diamond_size / 2
    diamond = (np.abs(dx) + np.abs(dy)) < diamond_size * 0.35
    diamond_f = diamond.astype(np.float32)
    # Raised diamonds: brighten. Flat areas: slight darken. Visible on ALL paints.
    paint = np.clip(paint + diamond_f[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint - (1 - diamond_f)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    # Extra brightness boost so diamond pattern shows on dark paints
    paint = np.clip(paint + bb * 1.5 * diamond_f[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_scale_pattern(paint, shape, mask, seed, pm, bb):
    """Dragon scales -- overlapping hexagonal scale pattern with per-scale color shift."""
    h, w = shape
    scale_size = 24
    y, x = get_mgrid((h, w))
    # Offset hex grid
    row = y // scale_size
    col = (x + (row % 2) * (scale_size // 2)) // scale_size
    # Distance from scale center
    cy = (row + 0.5) * scale_size
    cx = col * scale_size + (row % 2) * (scale_size // 2) + scale_size // 2
    dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (scale_size * 0.6)
    dist = np.clip(dist, 0, 1)
    # Per-scale color variation (visible shimmer)
    color_shift = np.zeros((h, w, 3), dtype=np.float32)
    for c in range(3):
        noise = multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 401 + c)
        color_shift[:,:,c] = noise * 0.08 * pm
    # Scale centers shimmer bright, edges are darker grooves
    center_boost = (1 - dist) * 0.12 * pm
    edge_groove = dist * 0.08 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + center_boost * mask + color_shift[:,:,c] * (1 - dist) * mask
            - edge_groove * mask, 0, 1)
    # Brightness boost on scale centers for dark paints
    paint = np.clip(paint + bb * 2.0 * (1 - dist)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_patina(paint, shape, mask, seed, pm, bb):
    """Worn chrome patina -- greenish/brownish oxidation in rough areas."""
    h, w = shape
    # Generate patchy oxidation map
    patina_map = multi_scale_noise(shape, [4, 8, 16], [0.2, 0.4, 0.4], seed + 500)
    patina_mask = np.clip((patina_map + 0.3) * 1.5, 0, 1)  # biased toward more patina
    # Patina tint: greenish-brown (oxidized copper/chrome)
    tint_r = -0.04 * pm  # less red
    tint_g = 0.02 * pm   # slight green
    tint_b = -0.03 * pm  # less blue
    paint[:,:,0] = np.clip(paint[:,:,0] + tint_r * patina_mask * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + tint_g * patina_mask * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + tint_b * patina_mask * mask, 0, 1)
    return paint

def paint_liquid_reflect(paint, shape, mask, seed, pm, bb):
    """Liquid metal -- large flowing wave reflections like mercury."""
    h, w = shape
    wave1 = multi_scale_noise(shape, [16, 32], [0.4, 0.6], seed + 600)
    wave2 = multi_scale_noise(shape, [24, 48], [0.5, 0.5], seed + 601)
    combined = (wave1 + wave2) * 0.5
    # Push paint toward bright silver in wave peaks
    wave_peaks = np.clip(combined, 0, 1)
    blend = wave_peaks * 0.30 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + 0.88 * blend * mask
    # Wave brightness modulation visible even on dark paints
    paint = np.clip(paint + bb * 2.5 * wave_peaks[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_plasma_veins(paint, shape, mask, seed, pm, bb):
    """Plasma veins -- branching lightning/vein patterns that glow."""
    h, w = shape
    n1 = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed + 700)
    n2 = multi_scale_noise(shape, [1, 3, 6, 12], [0.2, 0.3, 0.3, 0.2], seed + 701)
    veins = np.abs(n1 + n2 * 0.5)
    vein_mask = np.clip(1.0 - veins * 3.0, 0, 1)
    vein_mask = vein_mask ** 2
    # Veins glow bright -- visible even on black paint
    glow = vein_mask * 0.22 * pm
    paint = np.clip(paint + glow[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    # Blue/purple tint to veins (electric plasma look)
    paint[:,:,0] = np.clip(paint[:,:,0] + vein_mask * 0.05 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + vein_mask * 0.10 * pm * mask, 0, 1)
    return paint

def paint_ember_glow(paint, shape, mask, seed, pm, bb):
    """Ember glow -- hot spots where paint appears to glow from within."""
    h, w = shape
    # Generate hot spot map
    hotspots = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 800)
    hot_mask = np.clip((hotspots + 0.2) * 2.0, 0, 1)
    # Read the paint brightness to enhance warm areas
    brightness = paint.mean(axis=2)
    warmth = np.clip(brightness * 1.5, 0, 1)
    # Add warm glow (orange/red tint) in hot areas
    glow_strength = hot_mask * warmth * pm * 0.08
    paint[:,:,0] = np.clip(paint[:,:,0] + glow_strength * 1.5 * mask, 0, 1)  # more red
    paint[:,:,1] = np.clip(paint[:,:,1] + glow_strength * 0.6 * mask, 0, 1)  # some green (orange)
    paint[:,:,2] = np.clip(paint[:,:,2] - glow_strength * 0.3 * mask, 0, 1)  # less blue
    # Darken cool areas slightly for contrast
    cool_mask = 1.0 - hot_mask
    paint = np.clip(paint - cool_mask[:,:,np.newaxis] * 0.02 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_acid_etch(paint, shape, mask, seed, pm, bb):
    """Acid wash -- corroded erosion patterns with desaturation."""
    h, w = shape
    # Heavy splotchy erosion pattern
    etch = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed + 900)
    etch_mask = np.clip(np.abs(etch) * 2.0, 0, 1)
    # Dark erosion lines
    paint = np.clip(paint - etch_mask[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    # Desaturate in heavily etched areas
    gray = paint.mean(axis=2, keepdims=True)
    desat = etch_mask[:,:,np.newaxis] * 0.3 * pm * mask[:,:,np.newaxis]
    paint = paint * (1 - desat) + gray * desat
    return paint

def paint_hologram_lines(paint, shape, mask, seed, pm, bb):
    """Hologram scanlines -- horizontal line pattern with chromatic aberration.
    Scanline thickness scales with resolution for visibility at 2048+."""
    h, w = shape
    y = np.arange(h)
    # Scale scanline period to match texture_hologram (~80 bands)
    period = max(4, h // 80)
    half = max(1, period // 2)
    scanline = ((y % period) < half).astype(np.float32).reshape(-1, 1)
    scanline = np.broadcast_to(scanline, (h, w)).copy()
    # Scanlines add visible brightness on ALL paint colors
    paint = np.clip(paint + scanline[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    # Chromatic aberration: shift R and B channels for rainbow fringing
    shift = max(2, int(pm * max(3, h // 500)))
    shifted_r = np.roll(paint[:,:,0], -shift, axis=0)
    shifted_b = np.roll(paint[:,:,2], shift, axis=0)
    blend = 0.30 * pm
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + shifted_r * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + shifted_b * mask * blend
    # Base brightness boost for dark paints
    paint = np.clip(paint + bb * 2.5 * scanline[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_interference_shift(paint, shape, mask, seed, pm, bb):
    """Thin-film interference -- actual hue rotation creating rainbow bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Large-scale sine waves for rainbow band direction
    wave = np.sin(y * 0.015 + x * 0.008 + seed * 0.1) * 0.5 + \
           np.sin(y * 0.008 - x * 0.012 + seed * 0.2) * 0.3 + \
           np.sin((y + x) * 0.006 + seed * 0.3) * 0.2
    # Normalize to 0-1 for hue rotation amount
    hue_shift = (wave + 1.0) * 0.5  # 0 to 1
    # Convert paint to HSV, rotate hue, convert back
    r, g, b = paint[:,:,0], paint[:,:,1], paint[:,:,2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin + 1e-8
    # Compute hue (0-1)
    hue = np.zeros((h, w), dtype=np.float32)
    m_r = (cmax == r)
    m_g = (cmax == g) & ~m_r
    m_b = ~m_r & ~m_g
    hue[m_r] = ((g[m_r] - b[m_r]) / delta[m_r]) % 6 / 6
    hue[m_g] = ((b[m_g] - r[m_g]) / delta[m_g] + 2) / 6
    hue[m_b] = ((r[m_b] - g[m_b]) / delta[m_b] + 4) / 6
    sat = delta / (cmax + 1e-8)
    val = cmax
    # Rotate hue by the interference wave
    shift_amount = hue_shift * 0.4 * pm  # rotate up to 40% of the hue wheel
    new_hue = (hue + shift_amount * mask) % 1.0
    # Convert back to RGB
    new_rgb = np.stack(hsv_to_rgb_vec(new_hue, sat, val), axis=2)
    # Blend based on mask intensity
    blend = mask * 0.7 * pm
    paint = paint * (1 - blend[:,:,np.newaxis]) + new_rgb * blend[:,:,np.newaxis]
    paint = np.clip(paint, 0, 1)
    return paint

def paint_forged_carbon(paint, shape, mask, seed, pm, bb):
    """Forged carbon — darkens toward carbon black with per-chunk brightness variation.
    Real forged carbon is almost black with subtle tonal shifts between fiber chunks."""
    h, w = shape
    chunks, fine = _forged_carbon_chunks(shape, seed + 1000)
    mask3 = mask[:,:,np.newaxis]
    # Step 1: Darken heavily toward near-black (carbon is dark)
    # pm controls how aggressive: at pm=1.0, moderate darkening; at extreme, very dark
    darken_strength = 0.06 * pm  # 0.06 per pm level
    paint = paint * (1 - mask3 * darken_strength) + mask3 * darken_strength * np.array([0.03, 0.03, 0.04])
    # Step 2: Per-chunk tonal variation — some chunks slightly lighter/warmer
    # This creates the distinctive forged carbon "swirl" look
    chunk_brightness = (chunks - 0.5) * 0.04 * pm  # subtle +-0.04 brightness shift
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + chunk_brightness * mask, 0, 1)
    # Step 3: Very subtle warm/cool shift per chunk (some chunks slightly blue, some warm)
    warm_shift = (chunks > 0.5).astype(np.float32) * 0.008 * pm
    cool_shift = (chunks <= 0.5).astype(np.float32) * 0.005 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + warm_shift * mask, 0, 1)   # slightly warmer reds
    paint[:,:,2] = np.clip(paint[:,:,2] + cool_shift * mask, 0, 1)   # slightly cooler blues
    return paint

def paint_ice_cracks(paint, shape, mask, seed, pm, bb):
    """Cracked ice -- Voronoi crack network with blue tint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    # Generate Voronoi seed points
    num_points = 200
    points_y = rng.randint(0, h, num_points)
    points_x = rng.randint(0, w, num_points)
    # Compute distance to nearest two points for each pixel (downsampled for speed)
    ds = 4  # downsample factor
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = yg * ds
    xg = xg * ds
    dist1 = np.full((sh, sw), 1e9)
    dist2 = np.full((sh, sw), 1e9)
    for py, px in zip(points_y, points_x):
        d = np.sqrt((yg - py)**2 + (xg - px)**2).astype(np.float32)
        update2 = d < dist2
        update1 = d < dist1
        dist2 = np.where(update2, np.minimum(d, dist2), dist2)
        dist2 = np.where(update1, dist1, dist2)
        dist1 = np.where(update1, d, dist1)
    # Crack = where dist1 ~ dist2 (boundary between cells)
    crack_raw = np.clip(1.0 - (dist2 - dist1) / 8.0, 0, 1)
    # Upsample back to full resolution
    crack_img = Image.fromarray((crack_raw * 255).astype(np.uint8))
    crack_img = crack_img.resize((w, h), Image.BILINEAR)
    cracks = np.array(crack_img).astype(np.float32) / 255.0
    # Dark crack lines
    paint = np.clip(paint - cracks[:,:,np.newaxis] * 0.1 * pm * mask[:,:,np.newaxis], 0, 1)
    # Blue tint on ice surfaces (non-crack areas)
    ice = 1.0 - cracks
    paint[:,:,2] = np.clip(paint[:,:,2] + ice * 0.03 * pm * mask, 0, 1)  # add blue
    paint[:,:,0] = np.clip(paint[:,:,0] - ice * 0.01 * pm * mask, 0, 1)  # less red
    return paint


def paint_stardust_sparkle(paint, shape, mask, seed, pm, bb):
    """Stardust -- scattered bright pinpoint sparkles across the paint surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 1200)
    sparkles = rng.random((h, w)).astype(np.float32)
    # Sparse bright pinpoints (matching the star density in spec)
    star_mask = (sparkles > (1.0 - 0.02)).astype(np.float32)
    # Stars brighten the paint dramatically at their point
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + star_mask * 0.35 * pm * mask, 0, 1)
    # General subtle brightness boost
    paint = np.clip(paint + bb * 1.0 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hex_emboss(paint, shape, mask, seed, pm, bb):
    """Hex mesh -- honeycomb wire pattern visible in the paint with light/shadow."""
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 24
    row = y / (hex_size * 0.866)
    col = x / hex_size
    col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
    row_round = np.round(row)
    col_round = np.round(col_shifted)
    cy = row_round * hex_size * 0.866
    cx = (col_round + 0.5 * (row_round.astype(int) % 2)) * hex_size
    dist = np.sqrt((y - cy)**2 + (x - cx)**2)
    norm_dist = np.clip(dist / (hex_size * 0.45), 0, 1)
    wire = (norm_dist > 0.75).astype(np.float32)
    # Wire darkens, centers brighten
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            - wire * 0.08 * pm * mask
            + (1 - wire) * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.5 * (1 - wire)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_ripple_reflect(paint, shape, mask, seed, pm, bb):
    """Ripple -- concentric ring reflections like water surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 1300)
    ripple_sum = np.zeros((h, w), dtype=np.float32)
    for _ in range(6):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2).astype(np.float32)
        ring_spacing = rng.uniform(20, 40)
        ripple = np.sin(dist / ring_spacing * 2 * np.pi)
        fade = np.clip(1.0 - dist / (max(h, w) * 0.6), 0, 1)
        ripple_sum += ripple * fade
    rmax = np.abs(ripple_sum).max() + 1e-8
    ripple_norm = ripple_sum / rmax
    wave_peaks = np.clip(ripple_norm, 0, 1)
    # Brighten on ring peaks, darken in valleys
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + wave_peaks * 0.08 * pm * mask
            - (1 - wave_peaks) * 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 2.0 * wave_peaks[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hammered_dimples(paint, shape, mask, seed, pm, bb):
    """Hammered -- dimple indentation pattern visible in the paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1400)
    num_dimples = 400
    # Quick dimple map (same algorithm as spec but for paint effect)
    ds = 4
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = (yg * ds).astype(np.float32)
    xg = (xg * ds).astype(np.float32)
    dimple_small = np.zeros((sh, sw), dtype=np.float32)
    dimple_y = rng.randint(0, h, num_dimples).astype(np.float32)
    dimple_x = rng.randint(0, w, num_dimples).astype(np.float32)
    dimple_r = rng.randint(8, 22, num_dimples).astype(np.float32)
    for dy, dx, dr in zip(dimple_y, dimple_x, dimple_r):
        y_lo = max(0, int((dy - dr) / ds))
        y_hi = min(sh, int((dy + dr) / ds) + 1)
        x_lo = max(0, int((dx - dr) / ds))
        x_hi = min(sw, int((dx + dr) / ds) + 1)
        if y_hi <= y_lo or x_hi <= x_lo:
            continue
        sub_y = yg[y_lo:y_hi, x_lo:x_hi]
        sub_x = xg[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((sub_y - dy)**2 + (sub_x - dx)**2)
        dimple = np.clip(1.0 - dist / dr, 0, 1) ** 2
        dimple_small[y_lo:y_hi, x_lo:x_hi] = np.maximum(
            dimple_small[y_lo:y_hi, x_lo:x_hi], dimple)
    dimple_img = Image.fromarray((dimple_small * 255).astype(np.uint8))
    dimple_img = dimple_img.resize((w, h), Image.BILINEAR)
    dimple_map = np.array(dimple_img).astype(np.float32) / 255.0
    # Dimple centers catch light, edges are dark grooves
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + dimple_map * 0.06 * pm * mask
            - (1 - dimple_map) * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.5 * dimple_map[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_lightning_glow(paint, shape, mask, seed, pm, bb):
    """Lightning -- bolt paths glow bright white/blue against the paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1500)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    num_bolts = 4
    for b in range(num_bolts):
        py = rng.randint(0, h // 4)
        px = rng.randint(w // 4, 3 * w // 4)
        thickness = rng.randint(3, 6)
        for step in range(h * 2):
            py += rng.randint(1, 4)
            px += rng.randint(-6, 7)
            if py >= h: break
            px = max(0, min(w - 1, px))
            y_lo, y_hi = max(0, py - thickness), min(h, py + thickness + 1)
            x_lo, x_hi = max(0, px - thickness), min(w, px + thickness + 1)
            bolt_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                bolt_map[y_lo:y_hi, x_lo:x_hi], 1.0)
            if rng.random() < 0.03:
                fork_px, fork_py = px, py
                fork_dir = rng.choice([-1, 1])
                for _ in range(rng.randint(15, 60)):
                    fork_py += rng.randint(1, 3)
                    fork_px += fork_dir * rng.randint(1, 5)
                    if fork_py >= h or fork_px < 0 or fork_px >= w: break
                    ft = max(1, thickness // 2)
                    bolt_map[max(0,fork_py-ft):min(h,fork_py+ft+1),
                             max(0,fork_px-ft):min(w,fork_px+ft+1)] = \
                        np.maximum(bolt_map[max(0,fork_py-ft):min(h,fork_py+ft+1),
                                            max(0,fork_px-ft):min(w,fork_px+ft+1)], 0.6)
    bolt_map = np.clip(bolt_map, 0, 1)
    # Bolts glow bright white/blue
    paint = np.clip(paint + bolt_map[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1)
    # Blue tint on bolts
    paint[:,:,2] = np.clip(paint[:,:,2] + bolt_map * 0.08 * pm * mask, 0, 1)
    # Darken background slightly for contrast
    paint = np.clip(paint - (1 - bolt_map)[:,:,np.newaxis] * 0.02 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_brushed_grain(paint, shape, mask, seed, pm, bb):
    """Brushed titanium -- horizontal grain lines visible in the paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1600)
    row_grain = rng.randn(h, 1).astype(np.float32) * 0.7
    row_grain = np.tile(row_grain, (1, w))
    row_grain += rng.randn(h, w).astype(np.float32) * 0.08
    grain_light = np.clip(row_grain, 0, 1)
    grain_dark = np.clip(-row_grain, 0, 1)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + grain_light * 0.06 * pm * mask
            - grain_dark * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.0 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- PAINT MODIFIERS: Expansion Pack (25 new finishes) ---

def paint_ceramic_gloss(paint, shape, mask, seed, pm, bb):
    """Ceramic coating — ultra-deep wet gloss effect."""
    # Saturate colors slightly and add very smooth reflection
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    for c in range(3):
        # Boost saturation relative to luminance
        diff = paint[:,:,c] - brightness
        paint[:,:,c] = np.clip(brightness + diff * (1.0 + 0.15 * pm) + bb * 1.5, 0, 1) * mask[:,:] + paint[:,:,c] * (1 - mask)
    return paint

def paint_satin_wrap(paint, shape, mask, seed, pm, bb):
    """Satin vinyl wrap — slightly desaturated, uniform matte sheen."""
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    for c in range(3):
        diff = paint[:,:,c] - brightness
        paint[:,:,c] = np.clip(brightness + diff * 0.85, 0, 1) * mask + paint[:,:,c] * (1 - mask)
    return paint

def paint_primer_flat(paint, shape, mask, seed, pm, bb):
    """Primer — desaturate and push toward flat gray."""
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    gray_blend = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = (paint[:,:,c] * (1 - gray_blend * mask) + brightness * gray_blend * mask)
    # Add very fine grain noise
    rng = np.random.RandomState(seed + 500)
    grain = rng.randn(*shape).astype(np.float32) * 0.03 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + grain * mask, 0, 1)
    return paint

def paint_warm_metal(paint, shape, mask, seed, pm, bb):
    """Warm metallic shift — push toward copper/gold tones."""
    for c in range(3):
        shift = [0.06, 0.02, -0.03][c]  # warm: more red/green, less blue
        flake = multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.08 * pm * mask + shift * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_chameleon_shift(paint, shape, mask, seed, pm, bb):
    """Chameleon color-shift — hue rotates across surface based on angle noise."""
    h, w = shape
    y, x = get_mgrid((h, w))
    angle = np.sin(y * 0.015 + x * 0.01) * 0.3 + np.sin(y * 0.008 - x * 0.012) * 0.2
    angle = angle * pm
    # Rotate RGB channels based on angle field
    cos_a = np.cos(angle * np.pi * 2)
    sin_a = np.sin(angle * np.pi * 2)
    r, g, b = paint[:,:,0].copy(), paint[:,:,1].copy(), paint[:,:,2].copy()
    paint[:,:,0] = np.clip(r * cos_a + g * sin_a, 0, 1) * mask + r * (1 - mask)
    paint[:,:,1] = np.clip(g * cos_a + b * sin_a, 0, 1) * mask + g * (1 - mask)
    paint[:,:,2] = np.clip(b * cos_a + r * sin_a, 0, 1) * mask + b * (1 - mask)
    paint = np.clip(paint + bb * 1.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_pinstripe(paint, shape, mask, seed, pm, bb):
    """Pinstripe — thin regular lines lighten/darken paint."""
    h, w = shape
    y, x = get_mgrid((h, w))
    stripe = ((y % 16) < 2).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + stripe * 0.12 * pm * mask, 0, 1)
    return paint

def paint_camo_pattern(paint, shape, mask, seed, pm, bb):
    """Camo — splinter blocks shift paint toward green/tan/brown."""
    rng = np.random.RandomState(seed + 700)
    h, w = shape
    block_h, block_w = max(1, h // 16), max(1, w // 16)
    raw = rng.randint(0, 3, (block_h, block_w)).astype(np.float32)
    img = Image.fromarray((raw * 127).astype(np.uint8))
    blocks = np.array(img.resize((w, h), Image.NEAREST)).astype(np.float32) / 254.0
    # 3 camo tones: dark, medium, light
    for c in range(3):
        tone_shift = [[-0.1, 0.0, 0.05], [-0.05, 0.04, 0.06], [-0.08, -0.02, 0.0]][c]
        shift = np.where(blocks < 0.33, tone_shift[0], np.where(blocks < 0.66, tone_shift[1], tone_shift[2]))
        paint[:,:,c] = np.clip(paint[:,:,c] + shift * pm * mask, 0, 1)
    return paint

def paint_wood_grain(paint, shape, mask, seed, pm, bb):
    """Wood grain — warm directional streaks."""
    h, w = shape
    rng = np.random.RandomState(seed + 800)
    # Horizontal flowing grain
    row_grain = rng.randn(h, 1).astype(np.float32) * 0.8
    grain = np.tile(row_grain, (1, w))
    grain += rng.randn(h, w).astype(np.float32) * 0.1
    grain_val = np.clip(grain, -1, 1)
    # Warm tint (browns)
    for c in range(3):
        tint = [0.04, 0.02, -0.02][c]
        paint[:,:,c] = np.clip(paint[:,:,c] + grain_val * 0.06 * pm * mask + tint * pm * mask, 0, 1)
    return paint

def paint_snake_emboss(paint, shape, mask, seed, pm, bb):
    """Snake skin — elongated scale edge darkening."""
    h, w = shape
    y, x = get_mgrid((h, w))
    scale_w, scale_h = 12, 18
    row = y // scale_h
    sx = (x + (row % 2) * (scale_w // 2)) % scale_w
    sy = y % scale_h
    edge_x = np.minimum(sx, scale_w - sx) / (scale_w * 0.5)
    edge_y = np.minimum(sy, scale_h - sy) / (scale_h * 0.5)
    edge = np.clip(np.minimum(edge_x, edge_y) * 3, 0, 1)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - (1 - edge) * 0.08 * pm * mask, 0, 1)
    return paint

def paint_tread_darken(paint, shape, mask, seed, pm, bb):
    """Tire tread — V-groove darkening in directional pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    groove_period = 20
    groove = np.abs(((x + y * 0.5) % groove_period) - groove_period / 2) / (groove_period / 2)
    groove = np.clip(groove, 0, 1)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - (1 - groove) * 0.10 * pm * mask, 0, 1)
    return paint

def paint_circuit_glow(paint, shape, mask, seed, pm, bb):
    """Circuit board — trace lines glow slightly."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Orthogonal grid lines
    hlines = ((y % 18) < 2).astype(np.float32)
    vlines = ((x % 24) < 2).astype(np.float32)
    traces = np.clip(hlines + vlines, 0, 1)
    for c in range(3):
        glow = [0.08, 0.12, 0.06][c]  # green-ish glow
        paint[:,:,c] = np.clip(paint[:,:,c] + traces * glow * pm * mask, 0, 1)
    return paint

def paint_mosaic_tint(paint, shape, mask, seed, pm, bb):
    """Mosaic — Voronoi cells get slight random tint shifts."""
    h, w = shape
    rng = np.random.RandomState(seed + 900)
    num_cells = 80
    cx = rng.randint(0, w, num_cells).astype(np.float32)
    cy = rng.randint(0, h, num_cells).astype(np.float32)
    tints = rng.randn(num_cells, 3).astype(np.float32) * 0.06 * pm
    y, x = get_mgrid((h, w))
    # Find nearest cell center for each pixel (downsampled for speed)
    ds = 4
    sh, sw = h // ds, w // ds
    yg = np.arange(sh).reshape(-1, 1) * ds
    xg = np.arange(sw).reshape(1, -1) * ds
    nearest = np.zeros((sh, sw), dtype=np.int32)
    min_dist = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(num_cells):
        dist = (yg - cy[i])**2 + (xg - cx[i])**2
        closer = dist < min_dist
        nearest[closer] = i
        min_dist[closer] = dist[closer]
    nearest_img = Image.fromarray(nearest.astype(np.uint8))
    nearest_full = np.array(nearest_img.resize((w, h), Image.NEAREST))
    for c in range(3):
        shift = tints[nearest_full, c]
        paint[:,:,c] = np.clip(paint[:,:,c] + shift * mask, 0, 1)
    return paint

def paint_lava_glow(paint, shape, mask, seed, pm, bb):
    """Lava flow — hot cracks glow orange/red."""
    mn = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    cracks = np.exp(-mn**2 * 15)
    hot = np.clip(cracks * 2, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + hot * 0.15 * pm * mask, 0, 1)  # red glow
    paint[:,:,1] = np.clip(paint[:,:,1] + hot * 0.06 * pm * mask, 0, 1)  # slight orange
    paint[:,:,2] = np.clip(paint[:,:,2] - hot * 0.03 * pm * mask, 0, 1)  # less blue
    return paint

def paint_rain_droplets(paint, shape, mask, seed, pm, bb):
    """Rain drops — tiny bright circular highlights scattered on surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    num_drops = int(200 * pm)
    for _ in range(num_drops):
        dy, dx, dr = rng.randint(0, h), rng.randint(0, w), rng.randint(2, 5)
        y_lo = max(0, dy - dr); y_hi = min(h, dy + dr + 1)
        x_lo = max(0, dx - dr); x_hi = min(w, dx + dr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - dy)**2 + (xg - dx)**2)
        drop = np.clip(1.0 - dist / dr, 0, 1) ** 2
        for c in range(3):
            region = paint[y_lo:y_hi, x_lo:x_hi, c]
            m = mask[y_lo:y_hi, x_lo:x_hi]
            paint[y_lo:y_hi, x_lo:x_hi, c] = np.clip(region + drop * 0.08 * m, 0, 1)
    return paint

def paint_barbed_scratch(paint, shape, mask, seed, pm, bb):
    """Barbed wire — sharp scratch marks at regular intervals."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Diagonal slash marks
    slash = np.abs(((x - y) % 24) - 12) < 2
    barb = np.abs(((x + y) % 24) - 12) < 1
    wire = (slash | barb).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - wire * 0.10 * pm * mask, 0, 1)
    return paint

def paint_chainmail_emboss(paint, shape, mask, seed, pm, bb):
    """Chainmail — interlocking ring edge shadows."""
    h, w = shape
    y, x = get_mgrid((h, w))
    ring_size = 10
    # Offset rows of circles
    row = y // ring_size
    cx = (x + (row % 2) * (ring_size // 2)) % ring_size - ring_size // 2
    cy = y % ring_size - ring_size // 2
    dist = np.sqrt(cx.astype(np.float32)**2 + cy.astype(np.float32)**2)
    ring_edge = np.abs(dist - ring_size * 0.35) < 1.5
    ring_center = dist < ring_size * 0.25
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            - ring_edge.astype(np.float32) * 0.08 * pm * mask
            + ring_center.astype(np.float32) * 0.03 * pm * mask, 0, 1)
    return paint

def paint_brick_mortar(paint, shape, mask, seed, pm, bb):
    """Brick — mortar line darkening between blocks."""
    h, w = shape
    y, x = get_mgrid((h, w))
    brick_h, brick_w = 12, 24
    row = y // brick_h
    bx = (x + (row % 2) * (brick_w // 2)) % brick_w
    by = y % brick_h
    mortar = ((bx < 2) | (by < 2)).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - mortar * 0.12 * pm * mask, 0, 1)
    return paint

def paint_leopard_spots(paint, shape, mask, seed, pm, bb):
    """Leopard — organic rosette spot darkening."""
    h, w = shape
    rng = np.random.RandomState(seed + 1200)
    num_spots = int(120 * pm)
    spot_map = np.zeros((h, w), dtype=np.float32)
    for _ in range(num_spots):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        sr = rng.randint(4, 10)
        inner_r = sr * 0.5
        y_lo = max(0, sy - sr); y_hi = min(h, sy + sr + 1)
        x_lo = max(0, sx - sr); x_hi = min(w, sx + sr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - sy)**2 + (xg - sx)**2).astype(np.float32)
        ring = ((dist > inner_r) & (dist < sr)).astype(np.float32)
        spot_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(spot_map[y_lo:y_hi, x_lo:x_hi], ring)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - spot_map * 0.12 * pm * mask, 0, 1)
    return paint

def paint_razor_slash(paint, shape, mask, seed, pm, bb):
    """Razor — diagonal slash mark brightening."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    slash_period = max(20, dim // 50)
    slash_w = max(2, dim // 512)
    slash = ((x - y * 2) % slash_period)
    thin_slash = (slash < slash_w).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + thin_slash * 0.10 * pm * mask, 0, 1)
    return paint

def paint_oil_slick(paint, shape, mask, seed, pm, bb):
    """Oil slick — rainbow color pools on surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [4, 12, 24], [0.3, 0.4, 0.3], seed+200)
    hue = (n1 * 0.5 + n2 * 0.5 + 1) * 0.5  # 0-1
    strength = 0.10 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + np.sin(hue * np.pi * 2) * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + np.sin(hue * np.pi * 2 + 2.094) * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.sin(hue * np.pi * 2 + 4.189) * strength * mask, 0, 1)
    return paint

def paint_galaxy_nebula(paint, shape, mask, seed, pm, bb):
    """Galaxy — nebula clouds with color variation."""
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+200)
    nebula = np.clip((n1 + 0.3) * 1.5, 0, 1)
    strength = 0.12 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + nebula * n2 * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + nebula * 0.3 * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + nebula * 0.8 * strength * mask, 0, 1)
    return paint

def paint_rust_corrosion(paint, shape, mask, seed, pm, bb):
    """Rust — orange/brown oxidation patches eating through paint."""
    mn = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    rust = np.clip((mn + 0.2) * 2, 0, 1)
    strength = 0.15 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + rust * strength * 1.2 * mask, 0, 1)  # orange-red
    paint[:,:,1] = np.clip(paint[:,:,1] + rust * strength * 0.4 * mask - rust * 0.02 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - rust * strength * 0.5 * mask, 0, 1)  # remove blue
    return paint

def paint_neon_edge(paint, shape, mask, seed, pm, bb):
    """Neon glow — edges and features glow bright fluorescent."""
    from PIL import ImageFilter
    h, w = shape
    rng = np.random.RandomState(seed)
    # Detect edges in paint brightness
    brightness = (paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114)
    bright_img = Image.fromarray((brightness * 255).astype(np.uint8))
    edges = np.array(bright_img.filter(ImageFilter.FIND_EDGES)).astype(np.float32) / 255.0
    # Also generate noise-based glow so effect works on uniform paint
    noise = rng.rand(h, w).astype(np.float32)
    noise_img = Image.fromarray((noise * 255).astype(np.uint8))
    noise_edges = np.array(noise_img.filter(ImageFilter.FIND_EDGES)).astype(np.float32) / 255.0
    # Combine real edges with noise edges as fallback
    combined = np.clip(edges * 3 + noise_edges * 1.5, 0, 1)
    glow = combined * pm * mask
    # Strong fluorescent green/cyan glow
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 0.15, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.65, 0, 1)  # bright green neon
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.40, 0, 1)  # cyan tint
    return paint

def paint_weathered_peel(paint, shape, mask, seed, pm, bb):
    """Weathered paint — patches fade toward primer gray."""
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    peel = np.clip((mn + 0.1) * 1.5, 0, 1)
    peel_strength = 0.25 * pm
    gray = 0.45  # primer gray
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - peel * peel_strength * mask) + gray * peel * peel_strength * mask
    return paint


# ================================================================
# NEW BASE PAINT FUNCTIONS (v4.0)
# ================================================================

def paint_spectraflame(paint, shape, mask, seed, pm, bb):
    """Spectraflame — Hot Wheels candy-over-chrome: deepens color + adds sparkle depth."""
    h, w = shape
    np.random.seed(seed + 800)
    # Fine sparkle layer
    sparkle = np.random.rand(h, w).astype(np.float32)
    sparkle = np.where(sparkle > 0.97, 1.0, 0.0) * 0.08 * pm
    # Deep color saturation boost (candy-over-chrome effect)
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    for c in range(3):
        diff = paint[:,:,c] - mean_c
        paint[:,:,c] = np.clip(paint[:,:,c] + diff * 0.3 * pm * mask + sparkle * mask, 0, 1)
    # Slight brightness boost to show the chrome underneath
    paint = np.clip(paint + bb * 1.2 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_rose_gold_tint(paint, shape, mask, seed, pm, bb):
    """Rose Gold — shifts paint toward pink-gold tint."""
    # Rose gold = warm pink-gold tone
    tint_r, tint_g, tint_b = 0.85, 0.62, 0.58
    blend = 0.20 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + tint_r * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + tint_g * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + tint_b * blend * mask, 0, 1)
    # Add fine sparkle
    np.random.seed(seed + 810)
    sparkle = np.random.rand(*shape).astype(np.float32)
    sparkle = np.where(sparkle > 0.96, 1.0, 0.0) * 0.05 * pm
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_tactical_flat(paint, shape, mask, seed, pm, bb):
    """Tactical flat — Cerakote/Duracoat: desaturates + flattens toward olive-gray."""
    # Slight desaturation for military/tactical look
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.25 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    # Subtle grain texture
    np.random.seed(seed + 820)
    grain = np.random.randn(*shape).astype(np.float32) * 0.015 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# v5.0 NEW PAINT FUNCTIONS — for 50-base expansion
# ================================================================

def paint_wet_gloss(paint, shape, mask, seed, pm, bb):
    """Wet look — deepens color toward black, adds slight reflection brightening."""
    darken = 0.08 * pm
    paint = np.clip(paint * (1 - darken * mask[:,:,np.newaxis]) + bb * 0.01 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_silk_sheen(paint, shape, mask, seed, pm, bb):
    """Silk finish — very subtle directional brightening like light on silk fabric."""
    np.random.seed(seed + 900)
    h, w = shape
    y_grad = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    silk = np.sin(y_grad * np.pi * 3) * 0.02 * pm
    paint = np.clip(paint + silk[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_patina_green(paint, shape, mask, seed, pm, bb):
    """Aged patina — shifts toward green/teal oxidation."""
    np.random.seed(seed + 910)
    noise = np.random.randn(*shape).astype(np.float32) * 0.3
    patina_mask = np.clip(noise + 0.2, 0, 1) * mask * pm * 0.12
    # Green/teal shift
    paint[:,:,0] = np.clip(paint[:,:,0] - patina_mask * 0.06, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + patina_mask * 0.04, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + patina_mask * 0.02, 0, 1)
    return paint

def paint_iridescent_shift(paint, shape, mask, seed, pm, bb):
    """Iridescent — rainbow hue shifts across surface based on position."""
    h, w = shape
    np.random.seed(seed + 920)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    angle = np.sin(y * np.pi * 4 + x * np.pi * 3) * 0.5 + 0.5
    shift_r = np.sin(angle * np.pi * 2) * 0.03 * pm
    shift_g = np.sin(angle * np.pi * 2 + 2.094) * 0.03 * pm
    shift_b = np.sin(angle * np.pi * 2 + 4.189) * 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + shift_r * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + shift_g * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift_b * mask, 0, 1)
    return paint

def paint_raw_aluminum(paint, shape, mask, seed, pm, bb):
    """Raw aluminum — desaturates heavily, adds fine grain."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.35 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    np.random.seed(seed + 930)
    grain = np.random.randn(*shape).astype(np.float32) * 0.01 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_tinted_clearcoat(paint, shape, mask, seed, pm, bb):
    """Tinted clear — deepens color saturation under clearcoat."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    for c in range(3):
        diff = paint[:,:,c] - mean_c
        paint[:,:,c] = np.clip(paint[:,:,c] + diff * 0.12 * pm * mask, 0, 1)
    return paint

def paint_galvanized_speckle(paint, shape, mask, seed, pm, bb):
    """Galvanized zinc — speckled crystalline grain pattern."""
    np.random.seed(seed + 940)
    h, w = shape
    grain = np.random.randn(h // 2, w // 2).astype(np.float32) * 0.4
    grain = np.array(Image.fromarray(((grain + 2) * 64).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0 - 0.5
    paint = np.clip(paint + (grain * 0.025 * pm)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_heat_tint(paint, shape, mask, seed, pm, bb):
    """Heat-treated titanium — blue/purple/gold tinting zones."""
    np.random.seed(seed + 950)
    h, w = shape
    noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 951)
    heat_val = np.clip(noise * 0.5 + 0.5, 0, 1)
    # Blue zone
    blue_mask = np.clip(1 - np.abs(heat_val - 0.3) * 5, 0, 1) * mask * pm * 0.06
    paint[:,:,2] = np.clip(paint[:,:,2] + blue_mask, 0, 1)
    # Gold zone
    gold_mask = np.clip(1 - np.abs(heat_val - 0.7) * 5, 0, 1) * mask * pm * 0.04
    paint[:,:,0] = np.clip(paint[:,:,0] + gold_mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + gold_mask * 0.6, 0, 1)
    return paint

def paint_smoked_darken(paint, shape, mask, seed, pm, bb):
    """Smoked — darkens paint uniformly like tinted lens."""
    darken = 0.15 * pm
    paint = np.clip(paint * (1 - darken * mask[:,:,np.newaxis]), 0, 1)
    return paint

def paint_diamond_sparkle(paint, shape, mask, seed, pm, bb):
    """Diamond dust — extremely fine ultra-bright point sparkles."""
    np.random.seed(seed + 960)
    h, w = shape
    sparkle = (np.random.rand(h, w).astype(np.float32) > 0.997).astype(np.float32) * 0.08 * pm
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# CHAMELEON COLOR-SHIFT FINISHES
# Strategy: spatial gradient color ramp (multi-directional sine waves + Perlin noise)
# mapped through HSV hue ramp.  High metallic (M=220) exploits PBR Fresnel for
# genuine brightness shift at grazing angles; CC=16 adds white specular "flash".
# Camera motion in replays creates convincing color-shift illusion.
# ================================================================

def spec_chameleon_pro(shape, mask, seed, sm):
    """Chameleon spec — ultra-high metallic for Fresnel color shift + sharp reflections."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    np.random.seed(seed + 700)
    # M=220 base with smooth multi-octave spatial noise for organic feel
    m_noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.3, 0.35, 0.2], seed + 701)
    M = np.clip(220 + m_noise * 15 * sm, 180, 250)
    R = 15  # Very smooth — sharp reflections for mirror-like shift
    # Clearcoat with subtle spatial variation (16 = max shine)
    cc_noise = multi_scale_noise(shape, [16, 32, 48], [0.3, 0.4, 0.3], seed + 702)
    CC = np.clip(16 + cc_noise * 3 * sm, 14, 20)
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(CC * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, primary_hue, shift_range):
    """Core chameleon paint — multi-directional sine-wave field mapped through HSV hue ramp.

    primary_hue: starting hue in degrees (0-360)
    shift_range: degrees of hue shift across the gradient field (+/-)
    """
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    # Multi-directional sine-wave field — 8 waves at varied angles/frequencies
    # More waves + higher frequencies = finer, organic color transitions
    # that wrap smoothly around compound car body curves
    np.random.seed(seed + 710)
    field = (
        # Primary large-scale flow (sets overall gradient direction)
        np.sin(yf * 0.012 + xf * 0.008) * 0.18 +
        np.sin(yf * 0.006 - xf * 0.015) * 0.14 +
        # Medium-scale complexity (breaks up broad bands)
        np.sin((yf + xf) * 0.022) * 0.15 +
        np.sin((yf - xf * 0.7) * 0.019) * 0.13 +
        np.sin(yf * 0.028 + xf * 0.004) * 0.10 +
        # Fine detail (adds organic micro-variation across panels)
        np.sin((yf * 0.8 + xf * 1.2) * 0.035) * 0.10 +
        np.sin((yf * 1.3 - xf * 0.6) * 0.042) * 0.10 +
        np.sin((yf * 0.5 + xf * 0.9) * 0.055) * 0.10
    )

    # Add smooth Perlin-like noise for organic breakup (now BILINEAR, no blocks)
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 711)
    field = field + noise * 0.20

    # Normalize to 0..1
    field = (field - field.min()) / (field.max() - field.min() + 1e-8)

    # Map through HSV hue ramp
    hue_start = primary_hue / 360.0
    hue_shift = shift_range / 360.0
    hue_map = (hue_start + field * hue_shift) % 1.0

    # Convert HSV to RGB — full saturation, high value for vivid color
    saturation = np.full_like(hue_map, 0.85)
    value = np.full_like(hue_map, 0.75)
    r_new, g_new, b_new = hsv_to_rgb_vec(hue_map, saturation, value)

    # Blend with original paint — pm controls strength (0.7 = strong default)
    blend = 0.7 * pm
    for c, ch in enumerate([r_new, g_new, b_new]):
        paint[:,:,c] = np.clip(
            paint[:,:,c] * (1 - blend * mask) + ch * blend * mask,
            0, 1
        )

    # Brightness boost for dark paints to show the shift
    paint = np.clip(paint + bb * 1.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


# --- Chameleon Preset Wrappers ---

def paint_chameleon_midnight(paint, shape, mask, seed, pm, bb):
    """Midnight — Purple → Teal → Gold"""
    return paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, 270, 150)

def paint_chameleon_phoenix(paint, shape, mask, seed, pm, bb):
    """Phoenix — Red → Orange → Gold"""
    return paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, 0, 60)

def paint_chameleon_ocean(paint, shape, mask, seed, pm, bb):
    """Ocean — Blue → Teal → Emerald"""
    return paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, 220, 100)

def paint_chameleon_venom(paint, shape, mask, seed, pm, bb):
    """Venom — Green → Teal → Purple"""
    return paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, 120, -150)

def paint_chameleon_copper(paint, shape, mask, seed, pm, bb):
    """Copper — Copper → Magenta → Violet"""
    return paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, 20, 280)

def paint_chameleon_arctic(paint, shape, mask, seed, pm, bb):
    """Arctic — Teal → Blue → Purple"""
    return paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, 180, 90)


# --- Mystichrome (Ford SVT tribute — 3-color ramp, 240° shift) ---

def paint_mystichrome(paint, shape, mask, seed, pm, bb):
    """Mystichrome — Green → Blue → Purple (Ford SVT Cobra tribute, 240° shift)"""
    return paint_chameleon_gradient(paint, shape, mask, seed, pm, bb, 120, 240)


# ================================================================
# COLOR SHIFT CORE — Shared field generators + coordinated spec
# Used by both v2 adaptive/preset paint functions and the spec side.
# ================================================================

def _generate_colorshift_field(shape, seed):
    """Generate the master gradient field for color shift.
    Returns normalized 0-1 field. LOW frequencies for smooth, sweeping
    gradients that flow across entire panels — not choppy patches.
    Deterministic for a given seed so paint + spec stay coordinated.
    """
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    np.random.seed(seed + 5000)
    # LOW frequencies = long sweeping flows across the car
    # At 0.003, one full cycle = ~2094px = roughly one full car panel
    f1 = np.sin(yf * 0.003 + xf * 0.002) * 0.30   # Primary diagonal sweep
    f2 = np.sin(yf * 0.002 - xf * 0.004) * 0.25   # Counter-diagonal
    f3 = np.sin((yf + xf) * 0.0025) * 0.20         # Cross flow
    # Gentle radial for organic curvature
    cy, cx = h * 0.45, w * 0.5
    dist = np.sqrt((yf - cy)**2 + (xf - cx)**2).astype(np.float32)
    f4 = np.sin(dist * 0.003) * 0.15
    field = f1 + f2 + f3 + f4
    # LIGHT noise — just enough to prevent visible banding, not enough to break up the flow
    noise = multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 5001)
    field = field + noise * 0.08
    fmin, fmax = field.min(), field.max()
    field = (field - fmin) / (fmax - fmin + 1e-8)
    return field


def _generate_flake_field(shape, seed, cell_size=6):
    """Generate Voronoi-like flake cells for micro-texture.
    Returns: flake_val (0-1 per-cell random), flake_edge (boundary detection).
    """
    h, w = shape
    rng = np.random.RandomState(seed + 5100)
    ny = h // cell_size
    nx = w // cell_size
    cell_values = rng.rand(ny + 2, nx + 2).astype(np.float32)
    yidx = np.clip(np.arange(h) // cell_size, 0, ny).astype(int)
    xidx = np.clip(np.arange(w) // cell_size, 0, nx).astype(int)
    flake_val = cell_values[yidx[:, None], xidx[None, :]]
    gy = np.abs(np.diff(flake_val, axis=0, prepend=flake_val[:1, :]))
    gx = np.abs(np.diff(flake_val, axis=1, prepend=flake_val[:, :1]))
    flake_edge = np.clip((gy + gx) * 8.0, 0, 1)
    return flake_val, flake_edge


# ================================================================
# SHOKKER COLOR SHIFT v3 — Per-Pixel Dithered Fresnel System
#
# THE BREAKTHROUGH: Instead of painting a gradient and applying
# generic metallic spec, we CREATE TWO PIXEL POPULATIONS:
#
#   Population A: paint=ColorA + spec=(high M, low R, CC=16)
#     → Head-on: vivid Color A reflections
#     → Grazing: Fresnel washes to white (color A lost)
#
#   Population B: paint=ColorB + spec=(moderate M, higher R, CC=20)
#     → Head-on: Color B visible (roughness holds diffuse)
#     → Grazing: RETAINS Color B better (lower metallic)
#
# RESULT: Viewing angle determines which population dominates
# visually, creating a TRUE color-shift illusion.
#
# The gradient field controls the RATIO of A-to-B pixels spatially.
# Per-pixel stochastic dithering mixes them at the sub-pixel level
# so the eye blends them together.
# ================================================================


def _generate_dither_mask(shape, seed):
    """Generate a deterministic per-pixel random field for dithering.
    Returns a 0-1 float array. Pixel is 'A' if dither < threshold,
    'B' otherwise. Uses the SAME seed as color shift field for
    reproducibility between paint and spec calls.
    """
    h, w = shape
    rng = np.random.RandomState(seed + 6000)
    return rng.rand(h, w).astype(np.float32)


def spec_colorshift_pro(shape, mask, seed, sm,
                        spec_a=None, spec_b=None):
    """v3 PIXEL-DITHERED color shift spec generator.

    Each pixel gets EITHER spec_a or spec_b properties based on the
    dither mask + gradient field. This is what creates the differential
    Fresnel response that produces the color-shift illusion.

    Args:
        spec_a: dict with M, R, CC for Color A pixels (high metallic, low roughness)
        spec_b: dict with M, R, CC for Color B pixels (moderate metallic, higher roughness)
    """
    if spec_a is None:
        spec_a = {'M': 235, 'R': 8, 'CC': 16}
    if spec_b is None:
        spec_b = {'M': 200, 'R': 28, 'CC': 22}

    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)

    # Get the gradient field (spatial color ratio) and dither mask
    field = _generate_colorshift_field(shape, seed)
    dither = _generate_dither_mask(shape, seed)

    # Pixel is "A" where dither < (1 - field), "B" where dither >= (1 - field)
    # field=0 → almost all pixels are A
    # field=1 → almost all pixels are B
    # field=0.5 → 50/50 mix
    is_b = (dither >= (1.0 - field)).astype(np.float32)
    is_a = 1.0 - is_b

    # Build per-pixel spec values
    M_arr = is_a * spec_a['M'] + is_b * spec_b['M']
    R_arr = is_a * spec_a['R'] + is_b * spec_b['R']
    CC_arr = is_a * spec_a['CC'] + is_b * spec_b['CC']

    # Add very light noise to prevent perfectly uniform blocks
    m_noise = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 6010)
    M_arr = M_arr + m_noise * 4 * sm
    r_noise = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 6020)
    R_arr = R_arr + r_noise * 3 * sm

    spec[:, :, 0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC_arr * mask, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


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
                               hue_shift_degrees=60, shift_strength=0.95,
                               saturation_boost=0.30):
    """v3 ADAPTIVE color shift — reads zone color, dithers two populations.

    Samples the zone's existing color and creates two pixel populations:
      Pop A: zone's color (or saturated version for grays) + high M/low R spec
      Pop B: shifted color (zone hue + shift) + moderate M/higher R spec
    The gradient field controls the A:B ratio spatially.

    Args:
        hue_shift_degrees: How far to shift Color B from zone color (30-180)
        shift_strength: Blend with original (0.85-1.0)
        saturation_boost: Extra saturation for achromatic zones (0.0-0.5)
    """
    h, w = shape
    zone_hue, zone_sat, zone_val = _sample_zone_color(paint, mask)

    # For achromatic zones, inject saturation
    if zone_sat < 0.15:
        sat_a = 0.50 + saturation_boost
    else:
        sat_a = min(zone_sat + 0.12, 1.0)

    # Compensate value for metallic darkening in iRacing
    val_a = min(zone_val * 0.80 + 0.25, 0.92)

    hue_shift = hue_shift_degrees / 360.0
    hue_b = (zone_hue + hue_shift) % 1.0
    sat_b = min(sat_a + 0.08, 1.0)
    val_b = val_a

    # Build Color A and Color B as (H,S,V) in degrees
    color_a = (zone_hue * 360.0, sat_a, val_a)
    color_b = (hue_b * 360.0, sat_b, val_b)

    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                                    color_a=color_a, color_b=color_b,
                                    shift_strength=shift_strength)


def paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
                             color_a=None, color_b=None,
                             shift_strength=0.95):
    """v3 PIXEL-DITHERED color shift paint generator.

    Creates two interleaved pixel populations with DIFFERENT paint colors.
    The gradient field controls the spatial RATIO of A-to-B pixels.
    Each pixel gets either Color A or Color B (stochastic dithering).

    When combined with the matching spec_colorshift_pro (which assigns
    different M/R/CC to each population), iRacing's Fresnel equation
    produces different apparent colors at different viewing angles.

    THIS IS THE ILLUSION: head-on favors one color, grazing favors the other.

    Args:
        color_a: (H, S, V) for population A. H in degrees.
                 Gets high metallic + low roughness spec (vivid head-on, fades at grazing)
        color_b: (H, S, V) for population B. H in degrees.
                 Gets moderate metallic + higher roughness (holds color at grazing)
        shift_strength: Blend with original paint (0.85-1.0)
    """
    h, w = shape

    # Defaults: emerald (teal + purple)
    if color_a is None:
        color_a = (165, 0.85, 0.78)   # Teal-green
    if color_b is None:
        color_b = (285, 0.80, 0.75)   # Purple-magenta

    # Generate gradient field + dither mask (SAME seed as spec for coordination)
    field = _generate_colorshift_field(shape, seed)
    dither = _generate_dither_mask(shape, seed)

    # Dither: pixel is B where dither >= (1 - field)
    is_b = (dither >= (1.0 - field)).astype(np.float32)
    is_a = 1.0 - is_b

    # Convert HSV colors to RGB
    ha, sa, va = color_a
    hb, sb, vb = color_b
    ra, ga, ba = hsv_to_rgb_vec(
        np.full((h, w), ha / 360.0, dtype=np.float32),
        np.full((h, w), sa, dtype=np.float32),
        np.full((h, w), va, dtype=np.float32))
    rgb_a = np.stack([ra, ga, ba], axis=2)

    rb, gb, bb_c = hsv_to_rgb_vec(
        np.full((h, w), hb / 360.0, dtype=np.float32),
        np.full((h, w), sb, dtype=np.float32),
        np.full((h, w), vb, dtype=np.float32))
    rgb_b = np.stack([rb, gb, bb_c], axis=2)

    # Per-pixel color selection
    is_a3 = is_a[:, :, np.newaxis]
    is_b3 = is_b[:, :, np.newaxis]
    shift_rgb = rgb_a * is_a3 + rgb_b * is_b3

    # Blend with original paint
    blend = shift_strength * pm
    mask3 = mask[:, :, np.newaxis]
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3

    # Brightness boost (compensate for metallic darkening)
    paint = np.clip(paint + bb * 1.2 * mask3, 0, 1)

    return paint


# ================================================================
# ADAPTIVE PRESETS — "Your color + Fresnel shift direction"
# These read the zone's existing color and dither two populations.
# Pop A = zone color (high M, low R) — vivid head-on, fades at grazing
# Pop B = shifted color (moderate M, higher R) — holds at grazing
# ================================================================

# --- Adaptive: Warm Shift (your color + warm shifted population) ---
def paint_cs_warm(paint, shape, mask, seed, pm, bb):
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=60, shift_strength=0.95)
def spec_cs_warm(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 195, 'R': 25, 'CC': 20})

# --- Adaptive: Cool Shift (your color + cool complement population) ---
def paint_cs_cool(paint, shape, mask, seed, pm, bb):
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=180, shift_strength=0.95)
def spec_cs_cool(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 195, 'R': 28, 'CC': 22})

# --- Adaptive: Rainbow Shift (your color + full spectrum population) ---
def paint_cs_rainbow(paint, shape, mask, seed, pm, bb):
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=240, shift_strength=0.95,
                                      saturation_boost=0.35)
def spec_cs_rainbow(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 230, 'R': 8, 'CC': 16}, spec_b={'M': 190, 'R': 30, 'CC': 22})

# --- Adaptive: Subtle Shift (your color + gentle drift) ---
def paint_cs_subtle(paint, shape, mask, seed, pm, bb):
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=40, shift_strength=0.85,
                                      saturation_boost=0.15)
def spec_cs_subtle(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 225, 'R': 10, 'CC': 16}, spec_b={'M': 210, 'R': 18, 'CC': 18})

# --- Adaptive: Extreme Shift (your color + dramatic departure) ---
def paint_cs_extreme(paint, shape, mask, seed, pm, bb):
    return paint_colorshift_adaptive(paint, shape, mask, seed, pm, bb,
                                      hue_shift_degrees=200, shift_strength=0.95,
                                      saturation_boost=0.40)
def spec_cs_extreme(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 240, 'R': 6, 'CC': 16}, spec_b={'M': 185, 'R': 32, 'CC': 24})


# ================================================================
# PRESET COLOR SHIFTS — Bold fixed two-color Fresnel pairs
# Each preset defines Color A (dominates head-on) and Color B
# (emerges at grazing angles). The dither field controls spatial mix.
# Spec properties differ per population for differential Fresnel.
# ================================================================

# --- Preset: Emerald (Teal ↔ Purple) ---
def paint_cs_emerald(paint, shape, mask, seed, pm, bb):
    """Emerald — Teal head-on, Purple at grazing (Mystichrome-style)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
        color_a=(165, 0.85, 0.78), color_b=(285, 0.80, 0.75))
def spec_cs_emerald(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 200, 'R': 26, 'CC': 20})

# --- Preset: Inferno (Red ↔ Gold) ---
def paint_cs_inferno(paint, shape, mask, seed, pm, bb):
    """Inferno — Red head-on, Gold at grazing (hot metal)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
        color_a=(5, 0.88, 0.78), color_b=(48, 0.82, 0.82))
def spec_cs_inferno(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 205, 'R': 22, 'CC': 18})

# --- Preset: Nebula (Purple ↔ Gold) ---
def paint_cs_nebula(paint, shape, mask, seed, pm, bb):
    """Nebula — Purple head-on, Gold at grazing (cosmic luxury)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
        color_a=(280, 0.78, 0.72), color_b=(45, 0.82, 0.80))
def spec_cs_nebula(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 198, 'R': 28, 'CC': 22})

# --- Preset: Deep Ocean (Teal ↔ Deep Indigo) ---
def paint_cs_deepocean(paint, shape, mask, seed, pm, bb):
    """Deep Ocean — Teal head-on, Indigo at grazing"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
        color_a=(185, 0.82, 0.72), color_b=(260, 0.78, 0.62))
def spec_cs_deepocean(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 200, 'R': 26, 'CC': 20})

# --- Preset: Supernova (Copper ↔ Teal) ---
def paint_cs_supernova(paint, shape, mask, seed, pm, bb):
    """Supernova — Copper head-on, Teal at grazing (widest shift)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
        color_a=(25, 0.82, 0.78), color_b=(175, 0.80, 0.72))
def spec_cs_supernova(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 240, 'R': 6, 'CC': 16}, spec_b={'M': 190, 'R': 30, 'CC': 22})

# --- Preset: Solar Flare (Gold ↔ Crimson) ---
def paint_cs_solarflare(paint, shape, mask, seed, pm, bb):
    """Solar Flare — Gold head-on, Crimson at grazing (sunset)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
        color_a=(48, 0.85, 0.82), color_b=(350, 0.80, 0.68))
def spec_cs_solarflare(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 205, 'R': 22, 'CC': 18})

# --- Preset: Mystichrome (Green ↔ Purple, Ford SVT tribute) ---
def paint_cs_mystichrome(paint, shape, mask, seed, pm, bb):
    """Mystichrome — Green head-on, Purple at grazing (Ford SVT)"""
    return paint_colorshift_preset(paint, shape, mask, seed, pm, bb,
        color_a=(140, 0.82, 0.74), color_b=(275, 0.80, 0.72))
def spec_cs_mystichrome(shape, mask, seed, sm):
    return spec_colorshift_pro(shape, mask, seed, sm,
        spec_a={'M': 235, 'R': 8, 'CC': 16}, spec_b={'M': 200, 'R': 26, 'CC': 20})


# ================================================================
# SHOKKER PRIZM v4 — Panel-Aware Color Shift System
#
# THE NEONIZM BREAKTHROUGH DECODED:
# Real color-shift illusion comes from painting DIFFERENT COLORS
# on DIFFERENT BODY PANELS based on their 3D orientation.
# When the camera orbits the car, different panels face the viewer,
# creating the perception of color change.
#
# HOW IT WORKS:
# 1. Generate a "panel direction field" — smooth 2D field encoding
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
        # Center of texture vs edges — simulates convex body panels
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
        # Much lower than v1-v3 noise — just enough to make boundaries organic
        noise = multi_scale_noise(shape, [64, 128, 256], [0.25, 0.40, 0.35], seed + 7001)
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
    Very subtle (1-4% variation) — just enough to prevent perfectly flat color.
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

    # Apply as brightness variation (not hue shift — keep colors clean)
    paint_r = np.clip(paint_r + flake, 0, 1)
    paint_g = np.clip(paint_g + flake, 0, 1)
    paint_b = np.clip(paint_b + flake, 0, 1)

    return paint_r, paint_g, paint_b


# ================================================================
# PRIZM v4 CORE FUNCTIONS
# ================================================================

def spec_prizm(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=18):
    """Prizm v4 spec map — uniform high-metallic with subtle variation.

    The spec is deliberately SIMPLE. The color shift illusion comes
    from the PAINT, not from per-pixel spec tricks.

    Metallic: High (220-235) — amplifies paint color through PBR Fresnel
    Roughness: Low (10-20) — smooth reflections for vivid color
    Clearcoat: Low (16-22) — subtle secondary specular
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)

    # Base values with very light noise for realism
    noise = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 7200)
    M_arr = metallic + noise * 4 * sm
    R_arr = roughness + noise * 3 * sm

    # Apply mask
    spec[:, :, 0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.where(mask > 0.5, clearcoat, 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def paint_prizm_core(paint, shape, mask, seed, pm, bb,
                     color_stops, flow_complexity=3, flake_intensity=0.03,
                     blend_strength=0.92):
    """Prizm v4 CORE paint function — panel-aware multi-color ramp.

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

    shift_rgb = np.stack([ramp_r, ramp_g, ramp_b], axis=2)
    paint = paint * (1.0 - blend * mask3) + shift_rgb * blend * mask3

    # Brightness boost for dark source paints
    paint = np.clip(paint + bb * 1.0 * mask3, 0, 1)

    return paint


# ================================================================
# PRIZM v4 PRESETS — Physically Plausible Color Ramps
#
# Real thin-film interference follows spectral sequences:
# Low-order: Gold → Copper → Magenta → Purple → Blue
# Mid-order: Blue → Teal → Green → Yellow → Orange
# High-order: Full rainbow sweep
#
# Each preset defines a color ramp that follows these natural
# sequences, creating believable color-shift illusions.
# ================================================================

# --- Prizm: Holographic (Full rainbow sweep — the flagship effect) ---
def paint_prizm_holographic(paint, shape, mask, seed, pm, bb):
    """Holographic — Full rainbow sweep across panels (Neonizm's signature)"""
    stops = [
        (0.00, 350, 0.75, 0.82),  # Red-Pink
        (0.18, 35,  0.80, 0.85),  # Gold
        (0.36, 120, 0.78, 0.80),  # Green
        (0.54, 190, 0.82, 0.78),  # Teal
        (0.72, 250, 0.78, 0.76),  # Blue-Purple
        (1.00, 310, 0.72, 0.80),  # Magenta
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.03)

def spec_prizm_holographic(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=12, clearcoat=18)

# --- Prizm: Midnight (Purple → Teal → Gold — dark luxury) ---
def paint_prizm_midnight(paint, shape, mask, seed, pm, bb):
    """Midnight — Purple to Teal to Gold (deep luxury shift)"""
    stops = [
        (0.00, 275, 0.82, 0.68),  # Deep Purple
        (0.40, 195, 0.85, 0.72),  # Teal
        (0.70, 165, 0.80, 0.75),  # Aqua
        (1.00, 48,  0.78, 0.80),  # Gold
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_midnight(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=14, clearcoat=16)

# --- Prizm: Phoenix (Red → Gold → Green — warm to cool transition) ---
def paint_prizm_phoenix(paint, shape, mask, seed, pm, bb):
    """Phoenix — Red to Gold to Green (fire-to-earth shift)"""
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
    return spec_prizm(shape, mask, seed, sm, metallic=225, roughness=14, clearcoat=18)

# --- Prizm: Oceanic (Teal → Blue → Purple → Magenta — cool spectrum) ---
def paint_prizm_oceanic(paint, shape, mask, seed, pm, bb):
    """Oceanic — Teal to Blue to Purple to Magenta (deep sea shift)"""
    stops = [
        (0.00, 175, 0.85, 0.78),  # Teal
        (0.35, 220, 0.82, 0.74),  # Blue
        (0.65, 265, 0.80, 0.72),  # Purple
        (1.00, 320, 0.75, 0.76),  # Magenta
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_oceanic(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=12, clearcoat=18)

# --- Prizm: Ember (Copper → Magenta → Purple — warm metal) ---
def paint_prizm_ember(paint, shape, mask, seed, pm, bb):
    """Ember — Copper to Magenta to Purple (molten metal shift)"""
    stops = [
        (0.00, 25,  0.82, 0.82),  # Copper
        (0.35, 345, 0.78, 0.78),  # Rose
        (0.65, 310, 0.80, 0.74),  # Magenta
        (1.00, 270, 0.78, 0.70),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.03)

def spec_prizm_ember(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=225, roughness=16, clearcoat=20)

# --- Prizm: Arctic (Silver → Ice Blue → Teal — cold metallic) ---
def paint_prizm_arctic(paint, shape, mask, seed, pm, bb):
    """Arctic — Silver to Ice Blue to Teal (frozen metal shift)"""
    stops = [
        (0.00, 210, 0.18, 0.88),  # Silver (low sat, high val)
        (0.30, 200, 0.45, 0.85),  # Ice Blue
        (0.60, 195, 0.68, 0.80),  # Sky Blue
        (1.00, 178, 0.75, 0.76),  # Teal
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=2, flake_intensity=0.02)

def spec_prizm_arctic(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=235, roughness=10, clearcoat=16)

# --- Prizm: Solar (Gold → Orange → Red → Crimson — sunset) ---
def paint_prizm_solar(paint, shape, mask, seed, pm, bb):
    """Solar — Gold to Orange to Red to Crimson (sunset shift)"""
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
    return spec_prizm(shape, mask, seed, sm, metallic=222, roughness=16, clearcoat=20)

# --- Prizm: Venom (Green → Teal → Purple — toxic shift) ---
def paint_prizm_venom(paint, shape, mask, seed, pm, bb):
    """Venom — Green to Teal to Purple (toxic color shift)"""
    stops = [
        (0.00, 130, 0.85, 0.78),  # Bright Green
        (0.35, 165, 0.82, 0.76),  # Teal-Green
        (0.65, 210, 0.78, 0.74),  # Blue
        (1.00, 280, 0.80, 0.72),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=3, flake_intensity=0.025)

def spec_prizm_venom(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=14, clearcoat=18)

# --- Prizm: Mystichrome (Green → Blue → Purple — Ford SVT tribute) ---
def paint_prizm_mystichrome(paint, shape, mask, seed, pm, bb):
    """Mystichrome — Green to Blue to Purple (Ford SVT Cobra tribute)"""
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
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=12, clearcoat=16)

# --- Prizm: Black Rainbow (Dark base with rainbow highlights — Neonizm's signature product) ---
def paint_prizm_black_rainbow(paint, shape, mask, seed, pm, bb):
    """Black Rainbow — Dark base with vivid rainbow color shift"""
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
    return spec_prizm(shape, mask, seed, sm, metallic=232, roughness=12, clearcoat=16)

# --- Prizm: Duochrome (Two-color only — clean, minimal shift) ---
def paint_prizm_duochrome(paint, shape, mask, seed, pm, bb):
    """Duochrome — Clean two-color shift (teal ↔ purple)"""
    stops = [
        (0.00, 175, 0.85, 0.80),  # Teal
        (1.00, 280, 0.80, 0.75),  # Purple
    ]
    return paint_prizm_core(paint, shape, mask, seed, pm, bb, stops,
                            flow_complexity=2, flake_intensity=0.02)

def spec_prizm_duochrome(shape, mask, seed, sm):
    return spec_prizm(shape, mask, seed, sm, metallic=230, roughness=14, clearcoat=18)

# --- Prizm: Iridescent (Subtle pearlescent — low saturation, high metallic) ---
def paint_prizm_iridescent(paint, shape, mask, seed, pm, bb):
    """Iridescent — Subtle pearl-like color shift (low saturation)"""
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
    return spec_prizm(shape, mask, seed, sm, metallic=235, roughness=10, clearcoat=16)

# --- Prizm: Adaptive (reads zone color, creates shift from it) ---
def paint_prizm_adaptive(paint, shape, mask, seed, pm, bb):
    """Adaptive Prizm — reads zone color, generates complementary color ramp"""
    zone_hue, zone_sat, zone_val = _sample_zone_color(paint, mask)

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
    return spec_prizm(shape, mask, seed, sm, metallic=228, roughness=14, clearcoat=18)


# ================================================================
# v4.0 NEW MONOLITHICS (Glitch, Cel Shade, Thermochromic, Aurora)
# ================================================================

def spec_glitch(shape, mask, seed, sm):
    """Glitch — digital corruption: scanlines + channel offset zones."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    np.random.seed(seed + 900)
    # Base: medium metallic, low roughness
    M_arr = np.full((h, w), 120.0)
    R_arr = np.full((h, w), 40.0)
    # Scanlines: every 4th row = high roughness
    scanline = (np.arange(h) % 4 < 1).astype(np.float32)[:, np.newaxis]
    scanline = np.broadcast_to(scanline, (h, w)).astype(np.float32)
    R_arr = R_arr + scanline * 80 * sm
    # Random horizontal tear bands
    for _ in range(max(3, h // 100)):
        y_start = np.random.randint(0, h)
        band_h = np.random.randint(2, 8)
        tear_offset = np.random.randint(-40, 40)
        y_end = min(h, y_start + band_h)
        M_arr[y_start:y_end, :] = np.clip(M_arr[y_start:y_end, :] + tear_offset, 0, 255)
    spec[:,:,0] = np.clip(M_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_arr * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_glitch(paint, shape, mask, seed, pm, bb):
    """Glitch paint — RGB channel offset + tear bands."""
    h, w = shape
    np.random.seed(seed + 901)
    # RGB channel offset: shift R and B channels horizontally
    shift_r = int(np.random.randint(3, 8) * pm)
    shift_b = int(np.random.randint(-8, -3) * pm)
    r_shifted = np.roll(paint[:,:,0], shift_r, axis=1)
    b_shifted = np.roll(paint[:,:,2], shift_b, axis=1)
    paint[:,:,0] = paint[:,:,0] * (1 - 0.4 * pm * mask) + r_shifted * 0.4 * pm * mask
    paint[:,:,2] = paint[:,:,2] * (1 - 0.4 * pm * mask) + b_shifted * 0.4 * pm * mask
    # Horizontal tear bands
    for _ in range(max(3, h // 100)):
        y_start = np.random.randint(0, h)
        band_h = np.random.randint(2, 6)
        shift_px = np.random.randint(-20, 20)
        y_end = min(h, y_start + band_h)
        for c in range(3):
            paint[y_start:y_end, :, c] = np.roll(paint[y_start:y_end, :, c], shift_px, axis=1) * mask[y_start:y_end, :] + paint[y_start:y_end, :, c] * (1 - mask[y_start:y_end, :])
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_cel_shade(shape, mask, seed, sm):
    """Cel shade — posterized spec with bold edge outlines."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Simple flat spec — the magic happens in paint
    spec[:,:,0] = np.clip(80 * mask, 0, 255).astype(np.uint8)   # moderate metallic
    spec[:,:,1] = np.clip(60 * mask, 0, 255).astype(np.uint8)   # fairly smooth
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)  # clearcoat
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_cel_shade(paint, shape, mask, seed, pm, bb):
    """Cel shade — posterize paint to flat tones + Sobel edge outlines."""
    h, w = shape
    # Posterize: reduce to 4-5 tone levels
    levels = int(4 + pm)
    for c in range(3):
        channel = paint[:,:,c]
        quantized = np.floor(channel * levels) / levels
        paint[:,:,c] = channel * (1 - 0.7 * pm * mask) + quantized * 0.7 * pm * mask
    # Sobel edge detection for black outlines
    from PIL import ImageFilter
    gray = (paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114)
    gray_img = Image.fromarray((gray * 255).clip(0, 255).astype(np.uint8))
    edges = np.array(gray_img.filter(ImageFilter.FIND_EDGES)).astype(np.float32) / 255.0
    # Threshold edges to make crisp outlines
    outline = np.where(edges > 0.15, 1.0, 0.0) * 0.6 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - outline * mask, 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_thermochromic(shape, mask, seed, sm):
    """Thermochromic — noise-based 'heat zones' with variable metallic."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    heat = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 920)
    heat = np.clip((heat + 0.5) * 1.2, 0, 1)
    # Hot zones = high metallic, cool zones = low metallic
    M = 50 + heat * 180 * sm
    R = 30 + (1 - heat) * 80 * sm
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_thermochromic(paint, shape, mask, seed, pm, bb):
    """Thermochromic paint — maps noise to thermal colormap (blue→green→yellow→red)."""
    h, w = shape
    heat = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 920)
    heat = np.clip((heat + 0.5) * 1.2, 0, 1)
    # Thermal colormap: blue(cold) → green → yellow → red(hot)
    # H maps: 240°(blue) → 120°(green) → 60°(yellow) → 0°(red)
    hue = (1.0 - heat) * 240.0 / 360.0  # 0.667 → 0.0
    sat = np.full_like(heat, 0.8)
    val = np.full_like(heat, 0.7)
    r_th, g_th, b_th = hsv_to_rgb_vec(hue, sat, val)
    blend = 0.55 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r_th * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g_th * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b_th * blend * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_aurora(shape, mask, seed, sm):
    """Aurora — flowing borealis bands with high metallic shimmer."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Flowing sine wave bands
    wave = np.sin(yf * 0.02 + xf * 0.005) * 0.5 + np.sin(yf * 0.008 - xf * 0.012) * 0.3
    wave = np.clip((wave + 0.5) * 1.2, 0, 1)
    M = 200 + wave * 40 * sm
    R = 10 + (1 - wave) * 30 * sm
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_aurora(paint, shape, mask, seed, pm, bb):
    """Aurora paint — flowing sine-wave color bands (green/cyan/pink)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Multi-directional sine-wave field for flowing aurora bands
    field = (
        np.sin(yf * 0.02 + xf * 0.005) * 0.35 +
        np.sin(yf * 0.008 - xf * 0.012) * 0.35 +
        np.sin((yf * 0.5 + xf) * 0.006) * 0.30
    )
    field = np.clip((field + 0.5) * 1.0, 0, 1)
    # Aurora palette: green → cyan → pink through HSV
    hue = (0.33 + field * 0.5) % 1.0  # green(120°) → pink(300°)
    sat = np.full_like(field, 0.7)
    val = np.full_like(field, 0.65)
    r_au, g_au, b_au = hsv_to_rgb_vec(hue, sat, val)
    blend = 0.5 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r_au * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g_au * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b_au * blend * mask, 0, 1)
    paint = np.clip(paint + bb * 1.2 * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# v5.0 NEW MONOLITHIC FINISHES (4 new)
# ================================================================

def spec_static(shape, mask, seed, sm):
    """Static/TV noise — high-frequency random M+R producing chaotic reflections."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    np.random.seed(seed + 1500)
    noise = np.random.randint(0, 256, (h, w), dtype=np.uint8)
    spec[:,:,0] = np.clip(noise.astype(np.float32) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((255 - noise).astype(np.float32) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def paint_static(paint, shape, mask, seed, pm, bb):
    """Static paint — random B/W pixel noise."""
    h, w = shape
    np.random.seed(seed + 1501)
    noise = np.random.rand(h, w).astype(np.float32)
    gray = noise[:,:,np.newaxis] * np.ones((1, 1, 3))
    blend = 0.35 * pm
    paint = np.clip(paint * (1 - blend * mask[:,:,np.newaxis]) + gray * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def spec_scorched(shape, mask, seed, sm):
    """Scorched — burnt metal with variable roughness and low metallic edges."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    burn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1600)
    burn_val = np.clip(burn * 0.5 + 0.5, 0, 1)
    M = 40 + burn_val * 180  # Low in burnt areas, high in unburnt
    R = 200 - burn_val * 160  # High roughness in burnt areas
    spec[:,:,0] = np.clip(M * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def paint_scorched(paint, shape, mask, seed, pm, bb):
    """Scorched — darkens with orange/brown heat discoloration zones."""
    burn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1600)
    burn_val = np.clip(burn * 0.5 + 0.5, 0, 1)
    dark = burn_val * 0.2 * pm
    paint = np.clip(paint * (1 - dark[:,:,np.newaxis] * mask[:,:,np.newaxis]), 0, 1)
    # Warm tint in burnt areas
    warm = burn_val * 0.06 * pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] + warm * 0.8, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + warm * 0.3, 0, 1)
    return paint

def spec_radioactive(shape, mask, seed, sm):
    """Radioactive — glowing green zones with high metallic hot spots."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    glow = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1700)
    glow_val = np.clip(glow * 0.5 + 0.5, 0, 1)
    # Hot spots are very metallic + smooth, cold areas are rough
    spec[:,:,0] = np.clip((60 + glow_val * 195) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((160 - glow_val * 140) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip((16 + (1 - glow_val) * 20) * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def paint_radioactive(paint, shape, mask, seed, pm, bb):
    """Radioactive — green glow zones."""
    glow = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1700)
    glow_val = np.clip(glow * 0.5 + 0.5, 0, 1)
    green_glow = glow_val * 0.15 * pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] - green_glow * 0.3, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + green_glow * 1.0, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - green_glow * 0.2, 0, 1)
    return paint

def spec_holographic(shape, mask, seed, sm):
    """Holographic full wrap — rainbow metallic shifting across entire surface."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    rainbow = np.sin(y * np.pi * 8 + x * np.pi * 6) * 0.5 + 0.5
    spec[:,:,0] = np.clip((220 + rainbow * 35) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 + rainbow * 30) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def paint_holographic_full(paint, shape, mask, seed, pm, bb):
    """Full holographic — strong rainbow color shift across surface."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    angle = (y * 4 + x * 3) % 1.0
    r_holo = np.sin(angle * np.pi * 2) * 0.5 + 0.5
    g_holo = np.sin(angle * np.pi * 2 + 2.094) * 0.5 + 0.5
    b_holo = np.sin(angle * np.pi * 2 + 4.189) * 0.5 + 0.5
    blend = 0.2 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r_holo * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g_holo * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b_holo * blend * mask, 0, 1)
    return paint


FINISH_REGISTRY = {
    # --- STANDARD ---
    "gloss":              (spec_gloss,             paint_none),
    "matte":              (spec_matte,             paint_none),
    "satin":              (spec_satin,             paint_none),
    "metallic":           (spec_metallic,          paint_subtle_flake),
    "pearl":              (spec_pearl,             paint_fine_sparkle),
    "chrome":             (spec_chrome,            paint_chrome_brighten),
    "candy":              (spec_candy,             paint_fine_sparkle),
    # --- METALLIC ---
    "satin_metal":        (spec_satin_metal,       paint_subtle_flake),
    "brushed_titanium":   (spec_brushed_titanium,  paint_brushed_grain),
    "anodized":           (spec_anodized,          paint_subtle_flake),
    "hammered":           (spec_hammered,          paint_hammered_dimples),
    # --- FLAKE ---
    "metal_flake":        (spec_metal_flake,       paint_coarse_flake),
    "holographic_flake":  (spec_holographic_flake, paint_coarse_flake),
    "stardust":           (spec_stardust,          paint_stardust_sparkle),
    # --- EXOTIC ---
    "frozen":             (spec_frozen,            paint_subtle_flake),
    "frost_bite":         (spec_frost_bite,        paint_subtle_flake),
    "carbon_fiber":       (spec_carbon_fiber,      paint_carbon_darken),
    "forged_carbon":      (spec_forged_carbon,     paint_forged_carbon),
    # --- GEOMETRIC ---
    "diamond_plate":      (spec_diamond_plate,     paint_diamond_emboss),
    "dragon_scale":       (spec_dragon_scale,      paint_scale_pattern),
    "hex_mesh":           (spec_hex_mesh,          paint_hex_emboss),
    "ripple":             (spec_ripple,            paint_ripple_reflect),
    # --- EFFECTS ---
    "lightning":          (spec_lightning,          paint_lightning_glow),
    "plasma":             (spec_plasma,            paint_plasma_veins),
    "hologram":           (spec_hologram,          paint_hologram_lines),
    "interference":       (spec_interference,      paint_interference_shift),
    # --- DAMAGE ---
    "battle_worn":        (spec_battle_worn,       paint_scratch_marks),
    "worn_chrome":        (spec_worn_chrome,       paint_patina),
    "acid_wash":          (spec_acid_wash,         paint_acid_etch),
    "cracked_ice":        (spec_cracked_ice,       paint_ice_cracks),
    # --- SPECIAL ---
    "liquid_metal":       (spec_liquid_metal,      paint_liquid_reflect),
    "ember_glow":         (spec_ember_glow,        paint_ember_glow),
    "phantom":            (spec_phantom,           paint_phantom_fade),
    "blackout":           (spec_blackout,          paint_none),
}


# ================================================================
# v3.0 COMPOSITING SYSTEM — Base + Pattern
# ================================================================
# 18 bases x 32 patterns = 576+ combinations

# --- TEXTURE FUNCTIONS (v3.0 PATTERN SHAPE + MODULATION) ---
# Each returns {"pattern_val": 0-1 array, "R_range": float, "M_range": float, "CC": int_or_array}
#
# DESIGN: Patterns provide a SPATIAL SHAPE (pattern_val, 0-1 per pixel) and
# modulation ranges. compose_finish() uses these to create variation WITHIN
# the base material's own M/R values. This way:
#   - Chrome + Carbon Fiber = chrome surface with visible weave in roughness
#   - Matte + Carbon Fiber = matte surface with visible weave in roughness
#   - The base determines the "character", the pattern adds texture
#
# compose_finish() applies: base_R + pattern_val * R_range * sm
#                           base_M + pattern_val * M_range * sm (if M varies)

def texture_carbon_fiber(shape, mask, seed, sm):
    """2x2 twill weave — tight realistic carbon fiber, roughness-only modulation.
    !! DO NOT increase weave_size here — it's intentionally tight (6px) for realism.
    !! Other patterns (kevlar_weave, basket_weave) have their OWN texture functions.
    !! If you need a coarser weave, create a NEW function, don't modify this one."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 6  # Tight weave — real CF has hundreds of tows across a car panel
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Original spec: M=55(flat), R=30+cf*50. Pattern only modulates R via weave shape.
    return {"pattern_val": cf, "R_range": 50.0, "M_range": 25.0, "CC": None}

def texture_kevlar_weave(shape, mask, seed, sm):
    """Kevlar aramid weave — coarser than carbon fiber, visible at preview scale."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 24  # Kevlar weave is visibly coarser than CF
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    kv = twill_cell * horiz + (1 - twill_cell) * vert
    # Slightly softer contrast than CF
    kv = np.clip(kv * 1.15 - 0.08, 0, 1)
    return {"pattern_val": kv, "R_range": 45.0, "M_range": 20.0, "CC": None}

def texture_basket_weave(shape, mask, seed, sm):
    """Basket weave — large over/under blocks, very obvious at any scale."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 36  # Big basket blocks
    # Over-under: 2-wide tow bundles alternate
    bundle_x = (x // weave_size) % 2
    bundle_y = (y // weave_size) % 2
    # Checkerboard of horizontal vs vertical dominance
    checker = (bundle_x ^ bundle_y).astype(np.float32)
    # Within each cell, subtle tow curvature
    cell_x = (x % weave_size) / weave_size
    cell_y = (y % weave_size) / weave_size
    curve_h = np.sin(cell_x * np.pi) * 0.3
    curve_v = np.sin(cell_y * np.pi) * 0.3
    bw = checker * (0.6 + curve_h) + (1 - checker) * (0.4 + curve_v)
    bw = np.clip(bw, 0, 1)
    return {"pattern_val": bw, "R_range": 55.0, "M_range": 30.0, "CC": None}

def texture_forged_carbon(shape, mask, seed, sm):
    """Chopped carbon chunks — both M and R vary per chunk."""
    chunks, fine = _forged_carbon_chunks(shape, seed + 100)
    # Original: M=60+chunks*40, R=25+chunks*50+fine*8
    # Return chunks as pattern, fine noise baked into R_extra
    return {"pattern_val": chunks, "R_range": 50.0, "M_range": 40.0, "CC": None,
            "R_extra": fine * 8.0}  # extra fine noise added to R

def texture_diamond_plate(shape, mask, seed, sm):
    """Raised diamond tread — binary: raised diamonds vs flat surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    diamond_size = 20  # Tighter diamond tread pattern
    dx = (x % diamond_size) - diamond_size / 2
    dy = (y % diamond_size) - diamond_size / 2
    diamond = ((np.abs(dx) + np.abs(dy)) < diamond_size * 0.38).astype(np.float32)
    # Original: diamond(1)=M240/R8, flat(0)=M180/R140
    # Diamond areas are smoother and shinier. Pattern_val=1 means "diamond raised area"
    # R_range is NEGATIVE: diamonds make it smoother (lower R)
    return {"pattern_val": diamond, "R_range": -132.0, "M_range": 60.0, "CC": 0}

def texture_dragon_scale(shape, mask, seed, sm):
    """Hex reptile scales — gradient center=shiny to edge=rough."""
    h, w = shape
    scale_size = 24  # Tighter scales for realistic look
    y, x = get_mgrid((h, w))
    row = y // scale_size
    col = (x + (row % 2) * (scale_size // 2)) // scale_size
    cy = (row + 0.5) * scale_size
    cx = col * scale_size + (row % 2) * (scale_size // 2) + scale_size // 2
    dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (scale_size * 0.55)
    dist = np.clip(dist, 0, 1)
    # Original: center(0)=M255/R3, edge(1)=M120/R160
    # Use (1-dist) as pattern_val: 1=center(shiny), 0=edge(rough)
    center_val = 1.0 - dist
    # R_range negative: more pattern = smoother; M_range positive: more pattern = shinier
    return {"pattern_val": center_val, "R_range": -157.0, "M_range": 135.0, "CC": None}

def texture_hex_mesh(shape, mask, seed, sm):
    """Honeycomb wire grid — binary: open hex centers vs wire frame."""
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 16  # Finer honeycomb mesh
    row = y / (hex_size * 0.866)
    col = x / hex_size
    col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
    row_round = np.round(row)
    col_round = np.round(col_shifted)
    cy = row_round * hex_size * 0.866
    cx = (col_round + 0.5 * (row_round.astype(int) % 2)) * hex_size
    dist = np.sqrt((y - cy)**2 + (x - cx)**2)
    norm_dist = np.clip(dist / (hex_size * 0.45), 0, 1)
    wire = (norm_dist > 0.75).astype(np.float32)
    center = 1.0 - wire
    # Original: center=M255/R5, wire=M100/R160
    # center(1) = shiny/smooth, wire(0) = matte/rough
    return {"pattern_val": center, "R_range": -155.0, "M_range": 155.0, "CC": None}

def texture_ripple(shape, mask, seed, sm):
    """Concentric ring waves — sinusoidal peaks=shiny, valleys=matte."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 100)
    num_origins = int(6 + sm * 4)
    ripple_sum = np.zeros((h, w), dtype=np.float32)
    for _ in range(num_origins):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2).astype(np.float32)
        ring_spacing = rng.uniform(20, 40)
        ripple = np.sin(dist / ring_spacing * 2 * np.pi)
        fade = np.clip(1.0 - dist / (max(h, w) * 0.6), 0, 1)
        ripple_sum += ripple * fade
    rmax = np.abs(ripple_sum).max() + 1e-8
    ring_val = (ripple_sum / rmax + 1.0) * 0.5
    # Original: peak(1)=M240/R5, valley(0)=M140/R90
    return {"pattern_val": ring_val, "R_range": -85.0, "M_range": 100.0, "CC": None}

def texture_hammered(shape, mask, seed, sm):
    """Hand-hammered dimples — dimple centers=smooth, flat areas=rough."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    num_dimples = int(400 * sm)
    dimple_y = rng.randint(0, h, num_dimples).astype(np.float32)
    dimple_x = rng.randint(0, w, num_dimples).astype(np.float32)
    dimple_r = rng.randint(8, 22, num_dimples).astype(np.float32)
    ds = 4
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = (yg * ds).astype(np.float32)
    xg = (xg * ds).astype(np.float32)
    dimple_small = np.zeros((sh, sw), dtype=np.float32)
    for dy, dx, dr in zip(dimple_y, dimple_x, dimple_r):
        y_lo = max(0, int((dy - dr) / ds))
        y_hi = min(sh, int((dy + dr) / ds) + 1)
        x_lo = max(0, int((dx - dr) / ds))
        x_hi = min(sw, int((dx + dr) / ds) + 1)
        if y_hi <= y_lo or x_hi <= x_lo:
            continue
        sub_y = yg[y_lo:y_hi, x_lo:x_hi]
        sub_x = xg[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((sub_y - dy)**2 + (sub_x - dx)**2)
        dimple = np.clip(1.0 - dist / dr, 0, 1) ** 2
        dimple_small[y_lo:y_hi, x_lo:x_hi] = np.maximum(
            dimple_small[y_lo:y_hi, x_lo:x_hi], dimple)
    dimple_img = Image.fromarray((dimple_small * 255).astype(np.uint8))
    dimple_img = dimple_img.resize((w, h), Image.BILINEAR)
    dimple_map = np.array(dimple_img).astype(np.float32) / 255.0
    # Original: dimple(1)=M245/R8, flat(0)=M150/R120
    return {"pattern_val": dimple_map, "R_range": -112.0, "M_range": 95.0, "CC": 0}

def texture_lightning(shape, mask, seed, sm):
    """Forked lightning bolts — bolt paths are bright, bg is dark."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    num_bolts = int(3 + sm * 2)
    for b in range(num_bolts):
        py = rng.randint(0, h // 4)
        px = rng.randint(w // 4, 3 * w // 4)
        thickness = rng.randint(4, 8)
        for step in range(h * 2):
            py += rng.randint(1, 4)
            px += rng.randint(-6, 7)
            if py >= h:
                break
            px = max(0, min(w - 1, px))
            y_lo = max(0, py - thickness)
            y_hi = min(h, py + thickness + 1)
            x_lo = max(0, px - thickness)
            x_hi = min(w, px + thickness + 1)
            bolt_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                bolt_map[y_lo:y_hi, x_lo:x_hi], 1.0)
            if rng.random() < 0.03:
                fork_px, fork_py = px, py
                fork_thick = max(1, thickness // 2)
                fork_dir = rng.choice([-1, 1])
                for _ in range(rng.randint(20, 80)):
                    fork_py += rng.randint(1, 3)
                    fork_px += fork_dir * rng.randint(1, 5)
                    if fork_py >= h or fork_px < 0 or fork_px >= w:
                        break
                    fy_lo = max(0, fork_py - fork_thick)
                    fy_hi = min(h, fork_py + fork_thick + 1)
                    fx_lo = max(0, fork_px - fork_thick)
                    fx_hi = min(w, fork_px + fork_thick + 1)
                    bolt_map[fy_lo:fy_hi, fx_lo:fx_hi] = np.maximum(
                        bolt_map[fy_lo:fy_hi, fx_lo:fx_hi], 0.7)
    bolt_pil = Image.fromarray((bolt_map * 255).astype(np.uint8), 'L')
    bolt_pil = bolt_pil.filter(ImageFilter.GaussianBlur(radius=1.5))
    bolt_map = np.array(bolt_pil).astype(np.float32) / 255.0
    bolt_map = np.clip(bolt_map, 0, 1)
    # Original: bolt(1)=M255/R3, bg(0)=M80/R180
    # bolt_map=1 means bright bolt, 0 means dark background
    return {"pattern_val": bolt_map, "R_range": -177.0, "M_range": 175.0, "CC": None}

def texture_plasma(shape, mask, seed, sm):
    """Branching plasma veins — veins are bright, bg is matte."""
    n1 = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed+100)
    n2 = multi_scale_noise(shape, [1, 3, 6, 12], [0.2, 0.3, 0.3, 0.2], seed+200)
    veins = np.abs(n1 + n2 * 0.5)
    vein_mask_f = np.clip(1.0 - veins * 3.0, 0, 1) ** 2
    # Original: vein(1)=M255/R2, bg(0)=M160/R120
    return {"pattern_val": vein_mask_f, "R_range": -118.0, "M_range": 95.0, "CC": None}

def texture_hologram(shape, mask, seed, sm):
    """Holographic scanlines — visible banding in roughness AND metallic.
    Scanline thickness scales with resolution so bands remain visible at 2048+."""
    h, w = shape
    y = np.arange(h, dtype=np.float32).reshape(-1, 1)
    # Scale scanline period: ~80 visible bands across the height
    period = max(6, h // 80)
    half = max(1, period // 2)
    scanline = ((y.astype(int) % period) < half).astype(np.float32)
    # Add a subtle horizontal shimmer wave for holographic feel
    x = np.arange(w, dtype=np.float32).reshape(1, -1)
    shimmer = np.sin(x * 0.03 + y * 0.01) * 0.15 + 0.85
    scanline = np.broadcast_to(scanline, (h, w)).copy() * shimmer
    scanline = np.clip(scanline, 0, 1)
    # Boosted ranges: visible metallic + roughness modulation
    return {"pattern_val": scanline, "R_range": -100.0, "M_range": 60.0, "CC": None}

def texture_interference(shape, mask, seed, sm):
    """Flowing rainbow wave bands — R-only modulation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    wave = np.sin(y * 0.02 + x * 0.01) * 0.4 + np.sin(y * 0.01 - x * 0.015) * 0.3 + \
           np.sin((y + x) * 0.008) * 0.3
    wave = (wave + 1.0) * 0.5
    # Original: M=240(flat), R=5+wave*100. wave=1 means rougher.
    return {"pattern_val": wave, "R_range": 100.0, "M_range": 40.0, "CC": None}

def texture_battle_worn(shape, mask, seed, sm):
    """Scratch damage pattern — variable clearcoat. Uses noise, not geometric pattern."""
    h, w = shape
    mn = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed+100)
    rng = np.random.RandomState(seed + 301)
    scratch_noise = rng.randn(1, w) * 0.6
    scratch_noise = np.tile(scratch_noise, (h, 1))
    scratch_noise += rng.randn(h, w) * 0.3
    cc_noise = np.clip((mn + 0.5) * 16, 0, 16).astype(np.uint8)
    # Battle worn is a noise-based texture that doesn't fit simple pattern_val model.
    # Use composite noise as pattern_val, store raw noise components for R_extra.
    damage = np.clip((np.abs(mn) + np.abs(scratch_noise)) * 0.5, 0, 1)
    return {"pattern_val": damage, "R_range": 80.0, "M_range": 30.0, "CC": cc_noise,
            "R_extra": scratch_noise * 40.0, "M_extra": mn * 15.0}

def texture_acid_wash(shape, mask, seed, sm):
    """Corroded acid etch — variable clearcoat."""
    etch = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    etch_depth = np.clip(np.abs(etch) * 2, 0, 1)
    cc = np.clip(16 * (1 - etch_depth * 0.8), 0, 16).astype(np.uint8)
    # Original: M=200+etch*35, R=60+etch*60. Etch drives everything.
    return {"pattern_val": etch_depth, "R_range": 60.0, "M_range": 35.0, "CC": cc}

def texture_cracked_ice(shape, mask, seed, sm):
    """Frozen crack network — cracks add roughness."""
    h, w = shape
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed+200)
    crack1 = np.exp(-n1**2 * 20)
    crack2 = np.exp(-n2**2 * 20)
    cracks = np.clip(crack1 + crack2, 0, 1)
    # Original: M=230+mn*15 (near flat), R: ice=15, crack=15+cracks*115
    # cracks=1 means crack line = rougher
    return {"pattern_val": cracks, "R_range": 115.0, "M_range": 40.0, "CC": None}

def texture_metal_flake(shape, mask, seed, sm):
    """Coarse metallic flake sparkle — noise-driven M and R variation."""
    mf = multi_scale_noise(shape, [4, 8, 16, 32], [0.1, 0.2, 0.35, 0.35], seed+100)
    rf = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+200)
    # Metal flake has two independent noise fields. Use mf as pattern_val,
    # and store rf as R_extra for independent R noise.
    flake_val = np.clip((mf + 1) * 0.5, 0, 1)  # normalize to 0-1
    return {"pattern_val": flake_val, "R_range": -60.0, "M_range": 50.0, "CC": None,
            "R_extra": rf * 40.0}

def texture_holographic_flake(shape, mask, seed, sm):
    """Prismatic micro-grid flake — grid roughness + sparse bright flakes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    grid_size = 8
    diag1 = np.sin((x + y) * np.pi / grid_size) * 0.5 + 0.5
    diag2 = np.sin((x - y) * np.pi / (grid_size * 1.3)) * 0.5 + 0.5
    holo = diag1 * 0.6 + diag2 * 0.4
    rng = np.random.RandomState(seed + 100)
    sparkle = rng.random((h, w)).astype(np.float32)
    bright_flakes = (sparkle > (1.0 - 0.03 * sm)).astype(np.float32)
    # Original: M=245+flakes*10, R=5+holo*40. Grid modulates R, flakes add M.
    return {"pattern_val": holo, "R_range": -70.0, "M_range": 50.0, "CC": None,
            "M_extra": bright_flakes * 15.0}

def texture_stardust(shape, mask, seed, sm):
    """Sparse star pinpoints — stars are max metallic, ultra-smooth."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    star_field = rng.random((h, w)).astype(np.float32)
    stars = (star_field > (1.0 - 0.02 * sm)).astype(np.float32)
    # Original: bg=M160/R55, star=M255/R3. Stars add +95 M and -52 R.
    return {"pattern_val": stars, "R_range": -52.0, "M_range": 95.0, "CC": None}


# --- TEXTURE FUNCTIONS: Expansion Pack (14 new patterns) ---

def texture_pinstripe(shape, mask, seed, sm):
    """Thin parallel racing stripes at regular intervals."""
    h, w = shape
    y = np.arange(h).reshape(-1, 1)
    stripe = ((y % 16) < 2).astype(np.float32)
    stripe = np.broadcast_to(stripe, (h, w)).copy()
    # stripe=1 means raised stripe line = smoother/shinier
    return {"pattern_val": stripe, "R_range": -60.0, "M_range": 40.0, "CC": None}

def texture_camo(shape, mask, seed, sm):
    """Digital/splinter camouflage — blocky angular patches."""
    h, w = shape
    rng = np.random.RandomState(seed + 700)
    block_h, block_w = max(1, h // 16), max(1, w // 16)
    raw = rng.random((block_h, block_w)).astype(np.float32)
    img = Image.fromarray((raw * 255).astype(np.uint8))
    blocks = np.array(img.resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0
    # Quantize to 3 levels for sharp camo boundaries
    blocks = np.floor(blocks * 3) / 2.0
    blocks = np.clip(blocks, 0, 1)
    return {"pattern_val": blocks, "R_range": 60.0, "M_range": -30.0, "CC": 0}

def texture_wood_grain(shape, mask, seed, sm):
    """Natural wood grain — flowing horizontal lines with knots."""
    h, w = shape
    rng = np.random.RandomState(seed + 800)
    # Horizontal grain lines
    row_noise = rng.randn(h, 1).astype(np.float32) * 1.0
    grain = np.tile(row_noise, (1, w))
    # Add low-freq waviness
    y, x = get_mgrid((h, w))
    wave = np.sin(y * 0.03 + np.sin(x * 0.01) * 3) * 0.4
    grain = grain + wave + rng.randn(h, w).astype(np.float32) * 0.15
    grain = np.clip((grain + 2) / 4, 0, 1)
    return {"pattern_val": grain, "R_range": 80.0, "M_range": -50.0, "CC": 0}

def texture_snake_skin(shape, mask, seed, sm):
    """Elongated irregular scales — rectangular overlapping pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    scale_w, scale_h = 12, 18
    row = y // scale_h
    sx = (x + (row % 2) * (scale_w // 2)) % scale_w
    sy = y % scale_h
    # Gradient from center to edge of each scale
    edge_x = np.minimum(sx, scale_w - sx).astype(np.float32) / (scale_w * 0.5)
    edge_y = np.minimum(sy, scale_h - sy).astype(np.float32) / (scale_h * 0.5)
    center = np.clip(np.minimum(edge_x, edge_y) * 2.5, 0, 1)
    # center=1 = scale center (smooth), center=0 = edge (rough)
    return {"pattern_val": center, "R_range": -100.0, "M_range": 80.0, "CC": None}

def texture_tire_tread(shape, mask, seed, sm):
    """Directional V-groove tire rubber pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    groove_period = max(20, min(h, w) // 40)
    # V-shaped grooves
    v_pos = ((x + y * 0.5) % groove_period).astype(np.float32)
    v_depth = np.abs(v_pos - groove_period / 2) / (groove_period / 2)
    groove = np.clip(v_depth, 0, 1)
    # groove=1 = raised rubber (rough), groove=0 = groove (smooth)
    return {"pattern_val": groove, "R_range": 80.0, "M_range": -40.0, "CC": 0}

def texture_circuit_board(shape, mask, seed, sm):
    """PCB trace lines with pads — orthogonal right-angle paths."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Traces: horizontal and vertical lines
    h_trace = ((y % 18) < 2).astype(np.float32)
    v_trace = ((x % 24) < 2).astype(np.float32)
    traces = np.clip(h_trace + v_trace, 0, 1)
    # Pads at intersections
    h_pad = ((y % 18) < 4).astype(np.float32)
    v_pad = ((x % 24) < 4).astype(np.float32)
    pads = (h_pad * v_pad)
    circuit = np.clip(traces + pads * 0.5, 0, 1)
    # traces/pads = conductive (metallic, smooth), bg = board (rough, matte)
    return {"pattern_val": circuit, "R_range": -120.0, "M_range": 140.0, "CC": None}

def texture_mosaic(shape, mask, seed, sm):
    """Voronoi cell stained glass tiles — irregular organic cells."""
    h, w = shape
    rng = np.random.RandomState(seed + 900)
    num_cells = 80
    cx = rng.randint(0, w, num_cells).astype(np.float32)
    cy = rng.randint(0, h, num_cells).astype(np.float32)
    # Downsampled Voronoi for speed
    ds = 4
    sh, sw = h // ds, w // ds
    yg = np.arange(sh).reshape(-1, 1).astype(np.float32) * ds
    xg = np.arange(sw).reshape(1, -1).astype(np.float32) * ds
    min_dist = np.full((sh, sw), 1e9, dtype=np.float32)
    min_dist2 = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(num_cells):
        dist = np.sqrt((yg - cy[i])**2 + (xg - cx[i])**2)
        update2 = (dist < min_dist2) & (dist >= min_dist)
        update1 = dist < min_dist
        min_dist2[update2] = dist[update2]
        min_dist2[update1] = min_dist[update1]
        min_dist[update1] = dist[update1]
    # Edge detection: where dist to nearest ≈ dist to 2nd nearest
    edge = np.clip(1.0 - (min_dist2 - min_dist) / 8.0, 0, 1)
    edge_img = Image.fromarray((edge * 255).astype(np.uint8))
    edge_full = np.array(edge_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # edge=1 = grout line (rough), edge=0 = tile center (smooth)
    return {"pattern_val": 1.0 - edge_full, "R_range": -90.0, "M_range": 80.0, "CC": None}

def texture_lava_flow(shape, mask, seed, sm):
    """Flowing molten rock cracks — directional with hot/cool zones."""
    h, w = shape
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [2, 6, 12], [0.3, 0.4, 0.3], seed+200)
    # Crack detection + directional flow
    cracks = np.exp(-n1**2 * 12)
    flow = np.clip((n2 + 0.3) * 1.5, 0, 1)
    lava = np.clip(cracks * 0.7 + flow * 0.3, 0, 1)
    # lava=1 = hot crack (smooth, metallic), lava=0 = cool rock (rough, matte)
    cc = np.clip(16 * (1 - lava * 0.6), 0, 16).astype(np.uint8)
    return {"pattern_val": lava, "R_range": -140.0, "M_range": 120.0, "CC": cc}

def texture_rain_drop(shape, mask, seed, sm):
    """Water droplet beading — scattered circular bumps on surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    num_drops = int(200 * sm)
    ds = 2
    sh, sw = h // ds, w // ds
    drop_map = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(num_drops):
        dy = rng.randint(0, sh)
        dx = rng.randint(0, sw)
        dr = rng.randint(1, 4)
        y_lo = max(0, dy - dr); y_hi = min(sh, dy + dr + 1)
        x_lo = max(0, dx - dr); x_hi = min(sw, dx + dr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - dy)**2 + (xg - dx)**2).astype(np.float32)
        drop = np.clip(1.0 - dist / dr, 0, 1) ** 2
        drop_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(drop_map[y_lo:y_hi, x_lo:x_hi], drop)
    drop_img = Image.fromarray((drop_map * 255).astype(np.uint8))
    drop_full = np.array(drop_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # drop=1 = water bead (ultra smooth, high metallic), drop=0 = surface
    return {"pattern_val": drop_full, "R_range": -80.0, "M_range": 60.0, "CC": None}

def texture_barbed_wire(shape, mask, seed, sm):
    """Twisted wire with barb spikes — aggressive repeating motif."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    wire_sp = max(24, dim // 42)
    barb_sp = max(12, dim // 85)
    wire_w = max(2, dim // 512)
    # Diagonal wire strands
    wire1 = np.abs(((x - y) % wire_sp) - wire_sp // 2).astype(np.float32) < wire_w
    wire2 = np.abs(((x + y) % wire_sp) - wire_sp // 2).astype(np.float32) < max(1, wire_w // 2)
    # Barb points at intersections
    barb_x = ((x % barb_sp) < max(3, dim // 340)).astype(np.float32)
    barb_y = ((y % barb_sp) < max(3, dim // 340)).astype(np.float32)
    barbs = barb_x * barb_y * (wire1 | wire2).astype(np.float32)
    wire = np.clip((wire1 | wire2).astype(np.float32) + barbs, 0, 1)
    # wire=1 = metal wire (smooth metallic), wire=0 = background
    return {"pattern_val": wire, "R_range": -100.0, "M_range": 130.0, "CC": 0}

def texture_chainmail(shape, mask, seed, sm):
    """Interlocking metal ring mesh — circular repeating pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    ring_size = max(10, min(h, w) // 100)
    row = y // ring_size
    cx = ((x + (row % 2) * (ring_size // 2)) % ring_size - ring_size // 2).astype(np.float32)
    cy = (y % ring_size - ring_size // 2).astype(np.float32)
    dist = np.sqrt(cx**2 + cy**2)
    ring_edge = (np.abs(dist - ring_size * 0.35) < 1.5).astype(np.float32)
    ring_center = (dist < ring_size * 0.25).astype(np.float32)
    # ring_edge=bright smooth wire, center=dark hole
    pattern = np.clip(ring_edge * 0.8 + ring_center * 0.2, 0, 1)
    return {"pattern_val": pattern, "R_range": -90.0, "M_range": 100.0, "CC": 0}

def texture_brick(shape, mask, seed, sm):
    """Offset brick pattern with mortar lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    brick_h, brick_w = max(12, dim // 85), max(24, dim // 42)
    row = y // brick_h
    bx = (x + (row % 2) * (brick_w // 2)) % brick_w
    by = y % brick_h
    mortar = ((bx < 2) | (by < 2)).astype(np.float32)
    brick = 1.0 - mortar
    # brick=1 = brick face (rough), mortar=0 = mortar line (smoother)
    return {"pattern_val": brick, "R_range": 60.0, "M_range": -40.0, "CC": 0}

def texture_leopard(shape, mask, seed, sm):
    """Organic leopard rosette spots — ring-shaped markings."""
    h, w = shape
    rng = np.random.RandomState(seed + 1200)
    num_spots = int(100 * sm)
    ds = 2
    sh, sw = h // ds, w // ds
    spot_map = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(num_spots):
        sy = rng.randint(0, sh)
        sx = rng.randint(0, sw)
        sr = rng.randint(3, 7)
        inner_r = sr * 0.45
        y_lo = max(0, sy - sr); y_hi = min(sh, sy + sr + 1)
        x_lo = max(0, sx - sr); x_hi = min(sw, sx + sr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - sy)**2 + (xg - sx)**2).astype(np.float32)
        ring = ((dist > inner_r) & (dist < sr)).astype(np.float32)
        spot_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(spot_map[y_lo:y_hi, x_lo:x_hi], ring)
    spot_img = Image.fromarray((spot_map * 255).astype(np.uint8))
    spot_full = np.array(spot_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # spot=1 = dark ring mark, spot=0 = fur/surface
    return {"pattern_val": spot_full, "R_range": 50.0, "M_range": -60.0, "CC": 0}

def texture_razor(shape, mask, seed, sm):
    """Diagonal slash marks — aggressive angular cuts."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    slash_period = max(20, dim // 50)
    slash_w = max(2, dim // 512)
    slash = ((x - y * 2) % slash_period).astype(np.float32)
    thin = (slash < slash_w).astype(np.float32)
    # slash=1 = exposed cut (bright metallic), slash=0 = surface
    return {"pattern_val": thin, "R_range": -80.0, "M_range": 120.0, "CC": 0}


# ================================================================
# v4.0 NEW PATTERN TEXTURES + PAINT FUNCTIONS
# ================================================================

def texture_tron(shape, mask, seed, sm):
    """Tron — neon grid with proportional lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    grid_size = max(48, dim // 21)
    line_w = max(2, dim // 512)
    # Grid lines
    hline = ((y % grid_size) < line_w).astype(np.float32)
    vline = ((x % grid_size) < line_w).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    return {"pattern_val": grid, "R_range": -120.0, "M_range": 180.0, "CC": 0}

def paint_tron_glow(paint, shape, mask, seed, pm, bb):
    """Tron lines — neon glow along grid lines (cyan-ish)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    grid_size = max(48, dim // 21)
    line_w = max(2, dim // 512)
    hline = ((y % grid_size) < line_w).astype(np.float32)
    vline = ((x % grid_size) < line_w).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    glow = grid * 0.12 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 0.2 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.9 * mask, 0, 1)  # cyan glow
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.8 * mask, 0, 1)
    return paint


def _voronoi_cells_fast(shape, n_pts, seed_offset, seed):
    """Fast Voronoi cell assignment using downsampling for large images."""
    h, w = shape
    np.random.seed(seed + seed_offset)
    n_pts = min(n_pts, 200)  # Cap to prevent O(n*h*w) explosion
    # Downsample for speed: run at 1/4 res, upscale result
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    pts_y = np.random.randint(0, sh, n_pts).astype(np.float32)
    pts_x = np.random.randint(0, sw, n_pts).astype(np.float32)
    y, x = np.mgrid[0:sh, 0:sw]
    y = y.astype(np.float32)
    x = x.astype(np.float32)
    min_dist = np.full((sh, sw), 1e9, dtype=np.float32)
    cell_id = np.zeros((sh, sw), dtype=np.int32)
    for i in range(n_pts):
        dist = (y - pts_y[i]) ** 2 + (x - pts_x[i]) ** 2
        closer = dist < min_dist
        cell_id = np.where(closer, i, cell_id)
        min_dist = np.where(closer, dist, min_dist)
    if ds > 1:
        cell_img = Image.fromarray(cell_id.astype(np.int16))
        cell_id = np.array(cell_img.resize((w, h), Image.NEAREST)).astype(np.int32)
    return cell_id

def texture_dazzle(shape, mask, seed, sm):
    """Dazzle — bold Voronoi B/W patches (WW1 dazzle camo)."""
    h, w = shape
    n_pts = max(20, int(h * w / 4000))
    cell_id = _voronoi_cells_fast(shape, n_pts, 830, seed)
    pattern = (cell_id % 2).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -80.0, "CC": 0}

def paint_dazzle_contrast(paint, shape, mask, seed, pm, bb):
    """Dazzle — bold black/white patches for maximum contrast."""
    h, w = shape
    n_pts = max(20, int(h * w / 4000))
    cell_id = _voronoi_cells_fast(shape, n_pts, 830, seed)
    dark_cells = (cell_id % 2).astype(np.float32)
    darken = dark_cells * 0.35 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - darken * mask), 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def texture_marble(shape, mask, seed, sm):
    """Marble — soft noise veins using Gaussian zero-crossings."""
    h, w = shape
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 840)
    # Veins at zero-crossings of noise
    vein = np.exp(-noise**2 * 12)  # peaks at zero crossings
    vein = np.clip(vein, 0, 1)
    return {"pattern_val": vein, "R_range": -80.0, "M_range": 60.0, "CC": None}

def paint_marble_vein(paint, shape, mask, seed, pm, bb):
    """Marble veins — darken along vein lines for depth."""
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 840)
    vein = np.exp(-noise**2 * 12)
    darken = vein * 0.1 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - darken * mask, 0, 1)
    return paint


def texture_mega_flake(shape, mask, seed, sm):
    """Mega Flake — large hex glitter flakes (~12px)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 12
    row = (y / (hex_size * 0.866)).astype(int)
    col = (x / hex_size).astype(int)
    offset = np.where(row % 2 == 0, 0, hex_size // 2)
    cx = (col * hex_size + offset).astype(np.float32)
    cy = (row * hex_size * 0.866).astype(np.float32)
    # Distance to cell center = flake brightness variation
    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
    np.random.seed(seed + 850)
    # Each cell gets random brightness
    cell_hash = (row * 1337 + col * 7919 + seed) % 65536
    cell_rand = (np.sin(cell_hash.astype(np.float32) * 0.1) * 0.5 + 0.5)
    facet = np.clip(cell_rand * (1 - dist / hex_size * 0.5), 0, 1)
    return {"pattern_val": facet, "R_range": -50.0, "M_range": 60.0, "CC": 0}

def paint_mega_sparkle(paint, shape, mask, seed, pm, bb):
    """Mega Flake — random bright sparkle on each large flake facet."""
    h, w = shape
    np.random.seed(seed + 851)
    sparkle = np.random.rand(h, w).astype(np.float32)
    sparkle = np.where(sparkle > 0.85, sparkle * 0.12 * pm, 0)
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


def texture_multicam(shape, mask, seed, sm):
    """Multicam — 5-layer organic Perlin camo pattern."""
    h, w = shape
    # 5 layers at different scales for organic multi-color camo
    layers = []
    for layer_i in range(5):
        n = multi_scale_noise(shape, [16 + layer_i * 8, 32 + layer_i * 8],
                              [0.5, 0.5], seed + 860 + layer_i * 100)
        layers.append(np.clip((n + 0.5) * 1.2, 0, 1))
    # Combine: each layer dominates a different brightness range
    combined = np.zeros_like(layers[0])
    for layer_i, layer in enumerate(layers):
        threshold = layer_i / 5.0
        combined = np.where(layer > threshold + 0.3, layer * (layer_i + 1) / 5.0, combined)
    combined = np.clip(combined, 0, 1)
    return {"pattern_val": combined, "R_range": 70.0, "M_range": -50.0, "CC": 0}

def paint_multicam_colors(paint, shape, mask, seed, pm, bb):
    """Multicam — applies multi-tone desaturation for tactical look."""
    # Slight desaturation for camo zones
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 860)
    zones = np.clip((n + 0.5) * 1.2, 0, 1)
    desat = zones * 0.2 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    return paint


def _voronoi_cracks_fast(shape, n_pts, seed_offset, seed, crack_width=12.0):
    """Fast Voronoi crack detection using downsampling."""
    h, w = shape
    np.random.seed(seed + seed_offset)
    n_pts = min(n_pts, 200)  # Cap points
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    pts_y = np.random.randint(0, sh, n_pts).astype(np.float32)
    pts_x = np.random.randint(0, sw, n_pts).astype(np.float32)
    y, x = np.mgrid[0:sh, 0:sw]
    y = y.astype(np.float32)
    x = x.astype(np.float32)
    dist1 = np.full((sh, sw), 1e9, dtype=np.float32)
    dist2 = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(n_pts):
        dist = np.sqrt((y - pts_y[i]) ** 2 + (x - pts_x[i]) ** 2)
        new_dist2 = np.where(dist < dist1, dist1, np.where(dist < dist2, dist, dist2))
        dist1 = np.minimum(dist1, dist)
        dist2 = new_dist2
    crack = np.clip(1.0 - (dist2 - dist1) / crack_width, 0, 1)
    if ds > 1:
        crack_img = Image.fromarray((crack * 255).astype(np.uint8))
        crack = np.array(crack_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    return crack

def texture_magma_crack(shape, mask, seed, sm):
    """Magma Crack — Voronoi boundary cracks glow orange like lava."""
    h, w = shape
    n_pts = max(15, int(h * w / 6000))
    crack = _voronoi_cracks_fast(shape, n_pts, 870, seed, 12.0)
    return {"pattern_val": crack, "R_range": -160.0, "M_range": 140.0, "CC": 0}

def paint_magma_glow(paint, shape, mask, seed, pm, bb):
    """Magma cracks — orange glow along crack boundaries."""
    h, w = shape
    n_pts = max(15, int(h * w / 6000))
    crack = _voronoi_cracks_fast(shape, n_pts, 870, seed, 12.0)
    glow = crack * 0.2 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 1.0 * mask, 0, 1)   # red-orange
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.45 * mask, 0, 1)  # orange
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.05 * mask, 0, 1)  # minimal blue
    return paint


# ================================================================
# v5.0 NEW PATTERN TEXTURE + PAINT FUNCTIONS (12 new patterns)
# ================================================================

def texture_rivet_plate(shape, mask, seed, sm):
    """Rivet Plate — industrial riveted panel seams with chrome rivet heads.
    v2: Vectorized template stamping (was nested-loop distance maps — caused 90s hang)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    panel_h, panel_w = 80, 80
    # Panel seam lines: 2px grooves
    h_seam = ((y % panel_h) < 2).astype(np.float32)
    v_seam = ((x % panel_w) < 2).astype(np.float32)
    seams = np.clip(h_seam + v_seam, 0, 1)
    # Rivet heads — template stamping approach (O(n) per rivet, tiny template)
    rivet_r = 4
    # Build one small template (9x9 pixels)
    tpl_sz = rivet_r * 2 + 1
    ty = np.arange(tpl_sz, dtype=np.float32).reshape(-1, 1) - rivet_r
    tx = np.arange(tpl_sz, dtype=np.float32).reshape(1, -1) - rivet_r
    rivet_tpl = np.clip(1.0 - np.sqrt(ty * ty + tx * tx) / rivet_r, 0, 1) ** 2
    # Collect all rivet center positions
    rivet_map = np.zeros((h, w), dtype=np.float32)
    for ry in range(0, h, panel_h):
        for rx in range(0, w, panel_w):
            for (dy, dx) in [(0, 0), (0, panel_w // 2), (panel_h // 2, 0)]:
                cy, cx = ry + dy, rx + dx
                if cy >= h or cx >= w:
                    continue
                # Stamp the small template at this position
                y0 = max(0, cy - rivet_r)
                y1 = min(h, cy + rivet_r + 1)
                x0 = max(0, cx - rivet_r)
                x1 = min(w, cx + rivet_r + 1)
                ty0 = y0 - (cy - rivet_r)
                ty1 = ty0 + (y1 - y0)
                tx0 = x0 - (cx - rivet_r)
                tx1 = tx0 + (x1 - x0)
                rivet_map[y0:y1, x0:x1] = np.maximum(
                    rivet_map[y0:y1, x0:x1],
                    rivet_tpl[ty0:ty1, tx0:tx1]
                )
    # Combine: rivets are raised chrome bumps, seams are rough grooves
    pattern = np.clip(rivet_map - seams * 0.3, 0, 1)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 80.0, "CC": 0}

def paint_rivet_plate_emboss(paint, shape, mask, seed, pm, bb):
    """Rivet plate — darken seam grooves, brighten rivet heads."""
    h, w = shape
    y, x = get_mgrid((h, w))
    panel_h, panel_w = 80, 80
    h_seam = ((y % panel_h) < 2).astype(np.float32)
    v_seam = ((x % panel_w) < 2).astype(np.float32)
    seams = np.clip(h_seam + v_seam, 0, 1)
    darken = seams * 0.05 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_frost_crystal(shape, mask, seed, sm):
    """Frost Crystal — ice crystal branching fractals."""
    h, w = shape
    np.random.seed(seed + 1100)
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1101)
    n2 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1102)
    crystal = np.clip(np.abs(n1) + np.abs(n2) * 0.5 - 0.3, 0, 1)
    crystal = np.clip(crystal * 2, 0, 1)
    return {"pattern_val": crystal, "R_range": -80.0, "M_range": 60.0, "CC": None}

def paint_frost_crystal(paint, shape, mask, seed, pm, bb):
    """Frost crystal — whitens along crystal paths."""
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1101)
    n2 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1102)
    crystal = np.clip(np.abs(n1) + np.abs(n2) * 0.5 - 0.3, 0, 1)
    crystal = np.clip(crystal * 2, 0, 1)
    brighten = crystal * 0.03 * pm
    paint = np.clip(paint + brighten[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_wave(shape, mask, seed, sm):
    """Wave — smooth flowing sine wave ripples."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y = y.astype(np.float32) / h
    x = x.astype(np.float32) / w
    np.random.seed(seed + 1200)
    angle = np.random.uniform(0, np.pi)
    freq = 12.0
    wave = np.sin((y * np.cos(angle) + x * np.sin(angle)) * freq * np.pi * 2) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 70.0, "M_range": -40.0, "CC": None}

def paint_wave_shimmer(paint, shape, mask, seed, pm, bb):
    """Wave shimmer — subtle brightness oscillation along wave."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y = y.astype(np.float32) / h
    x = x.astype(np.float32) / w
    np.random.seed(seed + 1200)
    angle = np.random.uniform(0, np.pi)
    wave = np.sin((y * np.cos(angle) + x * np.sin(angle)) * 12 * np.pi * 2) * 0.5 + 0.5
    paint = np.clip(paint + (wave * 0.02 * pm)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_spiderweb(shape, mask, seed, sm):
    """Spiderweb — radial + concentric thin crack lines."""
    h, w = shape
    cy, cx = h // 2, w // 2
    y, x = get_mgrid((h, w))
    dy = (y - cy).astype(np.float32)
    dx = (x - cx).astype(np.float32)
    angle = np.arctan2(dy, dx)
    dist = np.sqrt(dy**2 + dx**2)
    # Radial spokes
    n_spokes = 16
    spoke = np.abs(np.sin(angle * n_spokes / 2))
    spoke_lines = (spoke < 0.05).astype(np.float32)
    # Concentric rings
    ring_spacing = 40.0
    rings = np.abs(np.sin(dist / ring_spacing * np.pi))
    ring_lines = (rings < 0.06).astype(np.float32)
    web = np.clip(spoke_lines + ring_lines, 0, 1)
    return {"pattern_val": web, "R_range": 80.0, "M_range": -40.0, "CC": 0}

def paint_spiderweb_crack(paint, shape, mask, seed, pm, bb):
    """Spiderweb — subtle darken along web lines."""
    h, w = shape
    cy, cx = h // 2, w // 2
    y, x = get_mgrid((h, w))
    dy = (y - cy).astype(np.float32)
    dx = (x - cx).astype(np.float32)
    angle = np.arctan2(dy, dx)
    dist = np.sqrt(dy**2 + dx**2)
    spoke = (np.abs(np.sin(angle * 8)) < 0.05).astype(np.float32)
    rings = (np.abs(np.sin(dist / 40 * np.pi)) < 0.06).astype(np.float32)
    web = np.clip(spoke + rings, 0, 1)
    paint = np.clip(paint - web[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_topographic(shape, mask, seed, sm):
    """Topographic — contour lines like elevation map."""
    h, w = shape
    elev = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    elev = (elev + 1) * 0.5  # 0-1
    n_contours = 20
    contour = np.abs(np.sin(elev * n_contours * np.pi))
    lines = (contour < 0.08).astype(np.float32)
    return {"pattern_val": lines, "R_range": 70.0, "M_range": -30.0, "CC": None}

def paint_topographic_line(paint, shape, mask, seed, pm, bb):
    """Topographic contour — slight darken on contour lines."""
    elev = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    elev = (elev + 1) * 0.5
    lines = (np.abs(np.sin(elev * 20 * np.pi)) < 0.08).astype(np.float32)
    paint = np.clip(paint - lines[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_crosshatch(shape, mask, seed, sm):
    """Crosshatch — overlapping 45deg line grids like pen strokes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    spacing = 20
    line_w = 2
    diag1 = ((y + x) % spacing < line_w).astype(np.float32)
    diag2 = ((y - x + 10000) % spacing < line_w).astype(np.float32)
    hatch = np.clip(diag1 + diag2, 0, 1)
    return {"pattern_val": hatch, "R_range": 55.0, "M_range": -25.0, "CC": 0}

def paint_crosshatch_ink(paint, shape, mask, seed, pm, bb):
    """Crosshatch ink — darken along hatch lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    spacing = max(20, dim // 50)
    line_w = max(2, dim // 512)
    diag1 = ((y + x) % spacing < line_w).astype(np.float32)
    diag2 = ((y - x + 10000) % spacing < line_w).astype(np.float32)
    hatch = np.clip(diag1 + diag2, 0, 1)
    paint = np.clip(paint - hatch[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_chevron(shape, mask, seed, sm):
    """Chevron — repeating V/arrow stripe pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(60, min(h, w) // 16)
    v_shape = np.abs((x % period) - period // 2).astype(np.float32) / (period // 2)
    stripe = ((y + v_shape * period // 2).astype(np.int32) % period < period // 3).astype(np.float32)
    return {"pattern_val": stripe, "R_range": 70.0, "M_range": -40.0, "CC": None}

def paint_chevron_contrast(paint, shape, mask, seed, pm, bb):
    """Chevron — alternating slight brightness difference."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(60, min(h, w) // 16)
    v_shape = np.abs((x % period) - period // 2).astype(np.float32) / (period // 2)
    stripe = ((y + v_shape * period // 2).astype(np.int32) % period < period // 3).astype(np.float32)
    paint = np.clip(paint + (stripe - 0.5)[:,:,np.newaxis] * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_celtic_knot(shape, mask, seed, sm):
    """Celtic Knot — interwoven band pattern using sin modulation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_n = y.astype(np.float32) / h * np.pi * 6
    x_n = x.astype(np.float32) / w * np.pi * 6
    band1 = np.sin(x_n + np.sin(y_n * 2) * 0.8)
    band2 = np.sin(y_n + np.sin(x_n * 2) * 0.8)
    weave = np.clip(np.abs(band1) + np.abs(band2) - 0.6, 0, 1)
    weave = np.clip(weave * 2, 0, 1)
    return {"pattern_val": weave, "R_range": 60.0, "M_range": -20.0, "CC": None}

def paint_celtic_emboss(paint, shape, mask, seed, pm, bb):
    """Celtic knot — subtle emboss on band edges."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_n = y.astype(np.float32) / h * np.pi * 6
    x_n = x.astype(np.float32) / w * np.pi * 6
    band1 = np.sin(x_n + np.sin(y_n * 2) * 0.8)
    band2 = np.sin(y_n + np.sin(x_n * 2) * 0.8)
    weave = np.clip(np.abs(band1) + np.abs(band2) - 0.6, 0, 1) * 2
    paint = np.clip(paint + (np.clip(weave, 0, 1) - 0.5)[:,:,np.newaxis] * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_skull(shape, mask, seed, sm):
    """Skull mesh — array of skull-like shapes from concentric ovals + eye holes."""
    h, w = shape
    cell_h, cell_w = 64, 48
    y, x = get_mgrid((h, w))
    # Tile coordinate
    ty = (y % cell_h).astype(np.float32) / cell_h - 0.5
    tx = (x % cell_w).astype(np.float32) / cell_w - 0.5
    # Skull outline: oval
    skull = np.clip(1.0 - (tx**2 / 0.12 + ty**2 / 0.18) * 1.5, 0, 1)
    # Eye holes: two small circles
    eye_l = np.clip(1.0 - ((tx + 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    eye_r = np.clip(1.0 - ((tx - 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    skull = np.clip(skull - eye_l * 0.8 - eye_r * 0.8, 0, 1)
    return {"pattern_val": skull, "R_range": 50.0, "M_range": -20.0, "CC": 0}

def paint_skull_darken(paint, shape, mask, seed, pm, bb):
    """Skull mesh — darkens eye holes and outline edges."""
    h, w = shape
    cell_h, cell_w = 64, 48
    y, x = get_mgrid((h, w))
    ty = (y % cell_h).astype(np.float32) / cell_h - 0.5
    tx = (x % cell_w).astype(np.float32) / cell_w - 0.5
    eye_l = np.clip(1.0 - ((tx + 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    eye_r = np.clip(1.0 - ((tx - 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    darken = (eye_l + eye_r) * 0.06 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_damascus(shape, mask, seed, sm):
    """Damascus steel — flowing layered wavy metal grain."""
    h, w = shape
    np.random.seed(seed + 1400)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1401)
    # Flowing horizontal waves disturbed by noise
    wave = np.sin((y * 30 + n1 * 3) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 70.0, "M_range": 50.0, "CC": 0}

def paint_damascus_layer(paint, shape, mask, seed, pm, bb):
    """Damascus — alternating bright/dark metal layers."""
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 1401)
    h = shape[0]
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    wave = np.sin((y * 30 + n1 * 3) * np.pi) * 0.5 + 0.5
    paint = np.clip(paint + (wave - 0.5)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_houndstooth(shape, mask, seed, sm):
    """Houndstooth — classic four-pointed tooth check pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(24, min(h, w) // 32)
    cy = (y // cell) % 2
    cx = (x // cell) % 2
    sy = (y % cell).astype(np.float32) / cell
    sx = (x % cell).astype(np.float32) / cell
    check = (cy ^ cx).astype(np.float32)
    tooth_ur = ((cy == 0) & (cx == 0) & (sy < sx) & (sy < 0.5) & (sx < 0.5)).astype(np.float32)
    tooth_dl = ((cy == 1) & (cx == 1) & (sy > sx) & (sy > 0.5) & (sx > 0.5)).astype(np.float32)
    tooth_ul = ((cy == 0) & (cx == 1) & (sy < (1.0 - sx)) & (sy < 0.5) & (sx > 0.5)).astype(np.float32)
    tooth_dr = ((cy == 1) & (cx == 0) & (sy > (1.0 - sx)) & (sy > 0.5) & (sx < 0.5)).astype(np.float32)
    pattern = np.clip(check + tooth_ur + tooth_dl + tooth_ul + tooth_dr, 0, 1)
    return {"pattern_val": pattern, "R_range": 70.0, "M_range": -40.0, "CC": None}


def paint_houndstooth_contrast(paint, shape, mask, seed, pm, bb):
    """Houndstooth — alternating brightness for classic pattern visibility."""
    h, w = shape
    cell = max(32, min(h, w) // 28)
    y, x = get_mgrid((h, w))
    check = ((y // cell) % 2 ^ (x // cell) % 2).astype(np.float32)
    paint = np.clip(paint + (check - 0.5)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_plaid(shape, mask, seed, sm):
    """Plaid/Tartan — overlapping horizontal and vertical color bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    b1h = ((yf % 48) < 12).astype(np.float32)
    b2h = ((yf % 48) > 20).astype(np.float32) * ((yf % 48) < 26).astype(np.float32)
    b1v = ((xf % 48) < 12).astype(np.float32)
    b2v = ((xf % 48) > 20).astype(np.float32) * ((xf % 48) < 26).astype(np.float32)
    horiz = b1h * 0.7 + b2h * 0.4
    vert = b1v * 0.7 + b2v * 0.4
    plaid = np.clip(horiz + vert, 0, 1)
    return {"pattern_val": plaid, "R_range": 70.0, "M_range": -40.0, "CC": None}


def paint_plaid_tint(paint, shape, mask, seed, pm, bb):
    """Plaid — alternating warm/cool shift on bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    band_h = np.sin(y.astype(np.float32) / h * np.pi * 16) * 0.5 + 0.5
    band_v = np.sin(x.astype(np.float32) / w * np.pi * 16) * 0.5 + 0.5
    warm = band_h * 0.02 * pm
    cool = band_v * 0.02 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + warm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + cool * mask, 0, 1)
    return paint


# --- SPEC FUNCTIONS: Expansion Pack (5 new specials/monolithics) ---

def spec_oil_slick(shape, mask, seed, sm):
    """Oil slick — flowing rainbow pools with high metallic and variable roughness."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [4, 12, 24], [0.3, 0.4, 0.3], seed+200)
    pool = np.clip((n1 + n2) * 0.5 + 0.5, 0, 1)
    spec[:,:,0] = np.clip((220 + pool * 35) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 + pool * 60) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_galaxy(shape, mask, seed, sm):
    """Galaxy — deep space nebula with star clusters."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    nebula = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    nebula_val = np.clip((nebula + 0.5) * 1.2, 0, 1)
    rng = np.random.RandomState(seed + 200)
    stars = (rng.random((h, w)).astype(np.float32) > 0.98).astype(np.float32)
    combined = np.clip(nebula_val * 0.6 + stars * 0.4, 0, 1)
    spec[:,:,0] = np.clip((80 + combined * 175) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((30 + nebula_val * 40 + stars * 20) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_rust(shape, mask, seed, sm):
    """Progressive rust — oxidation patches with variable roughness and no clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    rust = np.clip((mn + 0.2) * 2, 0, 1)
    # Rusty areas: low metallic, high roughness, no clearcoat
    spec[:,:,0] = np.clip((180 - rust * 140) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((40 + rust * 180) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    cc = np.clip(16 * (1 - rust * 0.9), 0, 16).astype(np.uint8)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_neon_glow(shape, mask, seed, sm):
    """Neon glow — edge-detected high metallic with variable roughness for glow effect."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    mn = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+100)
    # Edge-like features from noise gradients
    edges = np.clip(np.abs(mn) * 3, 0, 1)
    spec[:,:,0] = np.clip((200 + edges * 55) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((10 + (1-edges) * 80) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_weathered_paint(shape, mask, seed, sm):
    """Weathered paint — faded peeling layers showing underlayer patches."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    peel = np.clip((mn + 0.1) * 1.5, 0, 1)
    # Peeled areas: exposed primer (low metallic, high roughness, no CC)
    # Intact areas: normal paint (mid metallic, low roughness, full CC)
    spec[:,:,0] = np.clip((180 - peel * 130) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((20 + peel * 160) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    cc = np.clip(16 * (1 - peel * 0.85), 0, 16).astype(np.uint8)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec


# --- v5.5 "SHOKK THE SYSTEM" ADDITIONS (5 new patterns + 5 new bases for #55) ---

def texture_fracture(shape, mask, seed, sm):
    """Fracture — shattered impact glass with radial + Voronoi crack network."""
    h, w = shape
    np.random.seed(seed + 5500)
    n_impacts = int(3 + sm * 2)
    impact_y = np.random.randint(h // 6, 5 * h // 6, n_impacts).astype(np.float32)
    impact_x = np.random.randint(w // 6, 5 * w // 6, n_impacts).astype(np.float32)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Voronoi crack network: thin lines at cell boundaries
    n_vor = max(30, int(h * w / 8000))
    np.random.seed(seed + 5501)
    vor_y = np.random.randint(0, h, n_vor).astype(np.float32)
    vor_x = np.random.randint(0, w, n_vor).astype(np.float32)
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    sy = np.arange(sh).reshape(-1, 1).astype(np.float32) * ds
    sx = np.arange(sw).reshape(1, -1).astype(np.float32) * ds
    d1 = np.full((sh, sw), 1e9, dtype=np.float32)
    d2 = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(n_vor):
        d = np.sqrt((sy - vor_y[i])**2 + (sx - vor_x[i])**2)
        nd2 = np.where(d < d1, d1, np.where(d < d2, d, d2))
        d1 = np.minimum(d1, d)
        d2 = nd2
    vor_crack = np.clip(1.0 - (d2 - d1) / 8.0, 0, 1)
    if ds > 1:
        vc_img = Image.fromarray((vor_crack * 255).astype(np.uint8))
        vor_crack = np.array(vc_img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # Radial cracks from each impact point (8-12 spoke lines per impact)
    radial = np.zeros((h, w), dtype=np.float32)
    for i in range(n_impacts):
        dist = np.sqrt((yf - impact_y[i])**2 + (xf - impact_x[i])**2)
        angle = np.arctan2(yf - impact_y[i], xf - impact_x[i])
        n_spokes = np.random.randint(8, 13)
        spoke = np.abs(np.sin(angle * n_spokes / 2))
        spoke_line = (spoke < 0.04).astype(np.float32)
        # Fade with distance but not too fast
        fade = np.clip(1.0 - dist / (max(h, w) * 0.4), 0, 1)
        radial = np.maximum(radial, spoke_line * fade)
        # Concentric stress rings near impact
        stress = np.abs(np.sin(dist / 15 * np.pi))
        stress_line = (stress < 0.06).astype(np.float32) * np.clip(1.0 - dist / 80, 0, 1)
        radial = np.maximum(radial, stress_line)
    # Combine: Voronoi network + radial cracks
    cracks = np.clip(vor_crack * 0.6 + radial * 0.8, 0, 1)
    # Cracks lose clearcoat
    cc = np.clip(16 * (1 - cracks * 0.85), 0, 16).astype(np.uint8)
    # crack=1 → rough matte damaged, crack=0 → smooth intact
    return {"pattern_val": cracks, "R_range": 100.0, "M_range": -60.0, "CC": cc}

def paint_fracture_damage(paint, shape, mask, seed, pm, bb):
    """Fracture — darkens crack lines to simulate exposed substrate."""
    h, w = shape
    np.random.seed(seed + 5500)
    n_impacts = int(3 + 2)  # match texture at default sm
    impact_y = np.random.randint(h // 6, 5 * h // 6, n_impacts).astype(np.float32)
    impact_x = np.random.randint(w // 6, 5 * w // 6, n_impacts).astype(np.float32)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32); xf = x.astype(np.float32)
    # Simplified crack map for paint
    radial = np.zeros((h, w), dtype=np.float32)
    for i in range(n_impacts):
        dist = np.sqrt((yf - impact_y[i])**2 + (xf - impact_x[i])**2)
        angle = np.arctan2(yf - impact_y[i], xf - impact_x[i])
        spoke = (np.abs(np.sin(angle * 5)) < 0.04).astype(np.float32)
        fade = np.clip(1.0 - dist / (max(h, w) * 0.4), 0, 1)
        radial = np.maximum(radial, spoke * fade)
    darken = radial * 0.08 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_ember_mesh(shape, mask, seed, sm):
    """Ember Mesh — glowing hot wire grid with fading ember nodes at intersections."""
    h, w = shape
    cell = max(36, min(h, w) // 28)
    y, x = get_mgrid((h, w))
    line_w = max(2, int(2 * sm))
    hline = ((y % cell) < line_w).astype(np.float32)
    vline = ((x % cell) < line_w).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    # Hot nodes at intersections
    node_y = ((y % cell) < (line_w + 3)).astype(np.float32)
    node_x = ((x % cell) < (line_w + 3)).astype(np.float32)
    nodes = node_y * node_x
    ember = np.clip(grid * 0.7 + nodes * 0.3, 0, 1)
    return {"pattern_val": ember, "R_range": -80.0, "M_range": 140.0, "CC": 0}

def paint_ember_mesh_glow(paint, shape, mask, seed, pm, bb):
    """Ember mesh — orange/red glow on wire lines."""
    h, w = shape
    cell = max(36, min(h, w) // 28)
    y, x = get_mgrid((h, w))
    hline = ((y % cell) < 2).astype(np.float32)
    vline = ((x % cell) < 2).astype(np.float32)
    grid = np.clip(hline + vline, 0, 1)
    glow = grid * 0.1 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + glow * 0.9 * mask, 0, 1)   # red-orange
    paint[:,:,1] = np.clip(paint[:,:,1] + glow * 0.35 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.05 * mask, 0, 1)
    return paint

def texture_turbine(shape, mask, seed, sm):
    """Turbine — radial fan blade pattern spinning from center."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    y, x = get_mgrid((h, w))
    angle = np.arctan2(y.astype(np.float32) - cy, x.astype(np.float32) - cx)
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    n_blades = 12
    spiral_twist = dist / (max(h, w) * 0.3)
    blades = (np.sin((angle + spiral_twist) * n_blades) * 0.5 + 0.5)
    return {"pattern_val": blades, "R_range": 50.0, "M_range": -25.0, "CC": None}

def paint_turbine_spin(paint, shape, mask, seed, pm, bb):
    """Turbine — alternating light/dark blade sectors."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    y, x = get_mgrid((h, w))
    angle = np.arctan2(y.astype(np.float32) - cy, x.astype(np.float32) - cx)
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    blades = np.sin((angle + dist / (max(h, w) * 0.3)) * 12) * 0.5 + 0.5
    shift = (blades - 0.5) * 0.03 * pm
    paint = np.clip(paint + shift[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_static_noise(shape, mask, seed, sm):
    """Static Noise — TV static random pixel noise pattern."""
    h, w = shape
    np.random.seed(seed + 5540)
    # Coarse static: blocky pixel groups scaled to resolution
    block = max(4, min(h, w) // 256)
    sh, sw = h // block, w // block
    coarse = np.random.random((sh, sw)).astype(np.float32)
    coarse_img = Image.fromarray((coarse * 255).astype(np.uint8))
    coarse_up = np.array(coarse_img.resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0
    # Fine static overlay
    fine = np.random.random((h, w)).astype(np.float32)
    static_val = np.clip(coarse_up * 0.6 + fine * 0.4, 0, 1)
    return {"pattern_val": static_val, "R_range": 80.0, "M_range": -30.0, "CC": 0}

def paint_static_noise_grain(paint, shape, mask, seed, pm, bb):
    """Static noise — random brightness jitter like analog TV snow."""
    h, w = shape
    np.random.seed(seed + 5540)
    block = max(4, min(h, w) // 256)
    sh, sw = h // block, w // block
    coarse = np.random.random((sh, sw)).astype(np.float32)
    coarse_img = Image.fromarray((coarse * 255).astype(np.uint8))
    coarse_up = np.array(coarse_img.resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0
    grain = (coarse_up - 0.5) * 0.04 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_razor_wire(shape, mask, seed, sm):
    """Razor Wire — coiled helical wire with barbed loops."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_f = y.astype(np.float32)
    x_f = x.astype(np.float32)
    dim = min(h, w)
    spacing = max(50, dim // 20)
    coil_r = max(8, dim // 128)
    coil_freq = max(12, dim // 85)
    barb_sp = max(24, dim // 42)
    # Horizontal coil strands
    strand_y = (y_f % spacing).astype(np.float32)
    center = spacing / 2.0
    coil = np.sin(x_f / coil_freq * np.pi * 2) * coil_r
    dist_from_coil = np.abs(strand_y - center - coil)
    wire = np.clip(1.0 - dist_from_coil / 4.0, 0, 1)
    # Barb spikes at regular intervals
    barb_x = ((x % barb_sp) < max(3, dim // 340)).astype(np.float32)
    barb_mask = wire * barb_x
    result = np.clip(wire + barb_mask * 0.5, 0, 1)
    return {"pattern_val": result, "R_range": 65.0, "M_range": 80.0, "CC": 0}

def paint_razor_wire_scratch(paint, shape, mask, seed, pm, bb):
    """Razor wire — dark scratch marks along wire paths."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_f = y.astype(np.float32); x_f = x.astype(np.float32)
    dim = min(h, w)
    spacing = max(50, dim // 20)
    coil_r = max(8, dim // 128)
    coil_freq = max(12, dim // 85)
    strand_y = (y_f % spacing).astype(np.float32)
    coil = np.sin(x_f / coil_freq * np.pi * 2) * coil_r
    dist_from_coil = np.abs(strand_y - spacing / 2.0 - coil)
    wire = np.clip(1.0 - dist_from_coil / 4.0, 0, 1)
    darken = wire * 0.06 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# --- v5.5 NEW BASE PAINT FUNCTIONS ---

def paint_plasma_shift(paint, shape, mask, seed, pm, bb):
    """Plasma metal — electric purple/blue micro-shift hue injection."""
    h, w = shape
    np.random.seed(seed + 5550)
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5551)
    shift = np.clip(n * 0.5 + 0.5, 0, 1) * pm * 0.04
    paint[:,:,0] = np.clip(paint[:,:,0] + shift * 0.4 * mask, 0, 1)   # slight magenta
    paint[:,:,1] = np.clip(paint[:,:,1] - shift * 0.15 * mask, 0, 1)  # deepen green
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)   # blue push
    return paint

def paint_burnt_metal(paint, shape, mask, seed, pm, bb):
    """Burnt metal — exhaust header heat discoloration, golden/blue oxide."""
    h, w = shape
    np.random.seed(seed + 5560)
    heat = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5561)
    heat_val = np.clip(heat * 0.5 + 0.5, 0, 1)
    # Gold in hot zones, blue in cooler transition
    gold = heat_val * 0.04 * pm
    blue = (1 - heat_val) * 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + gold * 0.6 * mask - blue * 0.1 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + gold * 0.35 * mask - blue * 0.05 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - gold * 0.1 * mask + blue * 0.5 * mask, 0, 1)
    return paint

def paint_mercury_pool(paint, shape, mask, seed, pm, bb):
    """Mercury — liquid metal pooling effect, heavy desaturation with bright caustics."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    np.random.seed(seed + 5570)
    caustic = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5571)
    bright = np.clip(caustic, 0, 1) * 0.03 * pm
    paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_electric_blue_tint(paint, shape, mask, seed, pm, bb):
    """Electric blue tint — icy blue metallic color push."""
    shift = 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] - shift * 0.3 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + shift * 0.2 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)
    return paint

def paint_volcanic_ash(paint, shape, mask, seed, pm, bb):
    """Volcanic ash — desaturates and darkens with gritty fine grain."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.3 * pm
    darken = 0.06 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask - darken * mask, 0, 1)
    np.random.seed(seed + 5590)
    grain = np.random.randn(*shape).astype(np.float32) * 0.015 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# SHOKK PHASE TEXTURE FUNCTIONS (v4.0)
# Independent M/R/CC channel patterns using phase-shifted sin/cos
# These return M_pattern, R_pattern, CC_pattern as separate arrays
# ================================================================

# === SHOKK SERIES — UPGRADED EXISTING PATTERNS ===

def texture_shokk_bolt_v2(shape, mask, seed, sm):
    """SHOKK Bolt: Fractal branching lightning with independent R/M.
    R channel shows the main discharge path (chrome-mirror in the bolt),
    M channel shows the ionization field around it (metallic corona glow).
    Creates lightning that shifts between chrome and matte under different angles."""
    h, w = shape
    rng = np.random.RandomState(seed)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    glow_map = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    def _draw_bolt(x0, y0, x1, y1, thickness, brightness, depth=0):
        if depth > 6 or brightness < 0.1:
            return
        # Main segment with jitter
        n_segs = max(3, int(np.sqrt((x1-x0)**2 + (y1-y0)**2) / 20))
        pts_x = np.linspace(x0, x1, n_segs + 1)
        pts_y = np.linspace(y0, y1, n_segs + 1)
        for i in range(1, len(pts_x) - 1):
            pts_x[i] += rng.uniform(-30, 30) * (0.7 ** depth)
            pts_y[i] += rng.uniform(-15, 15) * (0.7 ** depth)
        for i in range(len(pts_x) - 1):
            sx, sy = pts_x[i], pts_y[i]
            ex, ey = pts_x[i+1], pts_y[i+1]
            seg_len = max(1, np.sqrt((ex-sx)**2 + (ey-sy)**2))
            # Distance from line segment
            dx, dy = ex - sx, ey - sy
            t = np.clip(((xx - sx) * dx + (yy - sy) * dy) / (seg_len**2 + 1e-8), 0, 1)
            proj_x = sx + t * dx
            proj_y = sy + t * dy
            dist = np.sqrt((xx - proj_x)**2 + (yy - proj_y)**2)
            # Sharp bolt core
            core = np.clip(1.0 - dist / max(1, thickness), 0, 1) * brightness
            bolt_map[:] = np.maximum(bolt_map, core)
            # Wide glow corona
            corona = np.exp(-(dist**2) / (2 * (thickness * 4)**2)) * brightness * 0.6
            glow_map[:] = np.maximum(glow_map, corona)
            # Branch
            if rng.rand() < 0.35 and depth < 4:
                bx = sx + (ex - sx) * rng.uniform(0.3, 0.7)
                by = sy + (ey - sy) * rng.uniform(0.3, 0.7)
                branch_angle = rng.uniform(-1.2, 1.2)
                branch_len = seg_len * rng.uniform(0.4, 0.9)
                bex = bx + np.cos(np.arctan2(ey-sy, ex-sx) + branch_angle) * branch_len
                bey = by + np.sin(np.arctan2(ey-sy, ex-sx) + branch_angle) * branch_len
                _draw_bolt(bx, by, bex, bey, thickness * 0.6, brightness * 0.7, depth + 1)

    # Main bolts
    for _ in range(rng.randint(2, 5)):
        x0 = rng.randint(w // 4, 3 * w // 4)
        _draw_bolt(x0, 0, x0 + rng.randint(-w//3, w//3), h, rng.uniform(2, 5), rng.uniform(0.7, 1.0))

    bolt_map = np.clip(bolt_map, 0, 1)
    glow_map = np.clip(glow_map, 0, 1)
    # R channel: bolt core (smooth=chrome in the bolt itself)
    R_pattern = 1.0 - bolt_map  # Low R = smooth where bolt is
    # M channel: glow corona (metallic shimmer around bolt)
    M_pattern = glow_map
    pv = (bolt_map + glow_map) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -70, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_fracture_v2(shape, mask, seed, sm):
    """SHOKK Fracture: Multi-layer impact crater with independent R/M for glass depth.
    R channel shows crack network (rough matte in cracks),
    M channel shows the glass shards between (mirror-chrome facets).
    Creates shattered windshield effect that catches light differently per shard."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    crack_map = np.zeros((h, w), dtype=np.float32)
    shard_map = np.zeros((h, w), dtype=np.float32)

    # Multiple impact points
    n_impacts = rng.randint(2, 5)
    for _ in range(n_impacts):
        cx, cy = rng.randint(w//6, 5*w//6), rng.randint(h//6, 5*h//6)
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        angle = np.arctan2(yy - cy, xx - cx)
        max_r = min(h, w) * rng.uniform(0.2, 0.45)

        # Radial cracks
        n_cracks = rng.randint(8, 16)
        for ci in range(n_cracks):
            crack_angle = ci * 2 * np.pi / n_cracks + rng.uniform(-0.2, 0.2)
            crack_width = rng.uniform(1.0, 2.5)
            ang_dist = np.abs(np.sin(angle - crack_angle))
            radial_crack = np.clip(1.0 - ang_dist * dist / crack_width, 0, 1)
            radial_crack *= np.clip(1.0 - dist / max_r, 0, 1)
            crack_map = np.maximum(crack_map, radial_crack * rng.uniform(0.5, 1.0))

        # Concentric ring cracks
        n_rings = rng.randint(3, 7)
        for ri in range(n_rings):
            ring_r = max_r * (ri + 1) / (n_rings + 1)
            ring = np.clip(1.0 - np.abs(dist - ring_r) / 2.0, 0, 1) * 0.7
            crack_map = np.maximum(crack_map, ring * np.clip(1.0 - dist / max_r, 0, 1))

        # Shard facets - each wedge between cracks gets a random "tilt" (metallic value)
        for ci in range(n_cracks):
            a1 = ci * 2 * np.pi / n_cracks
            a2 = (ci + 1) * 2 * np.pi / n_cracks
            mid_a = (a1 + a2) / 2
            in_wedge = (((angle - a1) % (2*np.pi)) < ((a2 - a1) % (2*np.pi))).astype(np.float32)
            tilt = rng.uniform(0.2, 1.0)
            shard_map += in_wedge * tilt * np.clip(1.0 - dist / max_r, 0, 1) * 0.3

        # Impact center crater
        crater = np.clip(1.0 - dist / 15, 0, 1)
        crack_map = np.maximum(crack_map, crater)

    crack_map = np.clip(crack_map, 0, 1)
    shard_map = np.clip(shard_map, 0, 1)
    R_pattern = crack_map  # High R in cracks = rough matte
    M_pattern = shard_map * (1.0 - crack_map * 0.8)  # Shards are metallic, cracks are not
    pv = np.clip(crack_map * 0.6 + shard_map * 0.4, 0, 1)
    CC_pattern = np.clip(crater * 0.8, 0, 1) if n_impacts == 1 else None
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 50, "R_range": -65,
            "CC": None, "CC_range": 20 if CC_pattern is not None else 0}


def texture_shokk_pulse_wave_v2(shape, mask, seed, sm):
    """SHOKK Pulse Wave: Expanding concentric pulses with R/M phase offset.
    R and M channels show rings offset by half a wavelength — when R is at peak
    (rough), M is at trough (non-metallic), and vice versa. Creates a 'breathing'
    effect where the surface oscillates between chrome and matte in concentric rings."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * rng.uniform(0.3, 0.7), w * rng.uniform(0.3, 0.7)
    dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    max_r = np.sqrt(h**2 + w**2) / 2
    norm_dist = dist / max(max_r, 1)

    freq = 6 + rng.randint(0, 8)
    # R channel: concentric rings
    R_pattern = (np.sin(norm_dist * 2 * np.pi * freq) + 1.0) / 2.0
    # M channel: SAME rings but phase-shifted by π (half wavelength)
    M_pattern = (np.sin(norm_dist * 2 * np.pi * freq + np.pi) + 1.0) / 2.0

    # Add EKG-style pulse spike on one radial line
    spike_angle = rng.uniform(0, 2 * np.pi)
    angle = np.arctan2(yy - cy, xx - cx)
    spike_mask = np.exp(-(((angle - spike_angle) % (2*np.pi))**2) / 0.005)
    pulse_height = np.sin(norm_dist * 2 * np.pi * freq * 3) * spike_mask
    R_pattern = np.clip(R_pattern + pulse_height * 0.3, 0, 1)

    # Fade out at edges
    fade = np.clip(1.0 - norm_dist * 0.3, 0.3, 1.0)
    R_pattern *= fade
    M_pattern *= fade

    pv = (R_pattern + M_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_scream_v2(shape, mask, seed, sm):
    """SHOKK Scream: Acoustic shockwave visualization with R/M opposition.
    Simulates visible sound — pressure waves radiate from center with compression
    zones (high M = chrome) and rarefaction zones (high R = matte). The R and M
    channels are in direct opposition: where one peaks, the other troughs."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    angle = np.arctan2(yy - cy, xx - cx)
    max_r = np.sqrt(h**2 + w**2) / 2

    # Pressure wave: concentric with angular distortion (mouth shape)
    freq = 5 + rng.randint(0, 4)
    # Mouth opening creates directional sound cone
    mouth_dir = rng.uniform(0, 2 * np.pi)
    directionality = 0.5 + 0.5 * np.cos(angle - mouth_dir)  # Stronger in mouth direction

    wave = np.sin(dist / max(max_r, 1) * 2 * np.pi * freq + angle * 0.5)
    # Compression zones (positive wave) = chrome metallic
    M_pattern = np.clip((wave + 1) / 2 * directionality, 0, 1)
    # Rarefaction zones (negative wave) = rough matte
    R_pattern = np.clip((-wave + 1) / 2 * directionality, 0, 1)

    # Add radial "scream lines" — visible sound propagation
    n_lines = 12 + rng.randint(0, 8)
    for i in range(n_lines):
        line_angle = mouth_dir + rng.uniform(-0.8, 0.8)
        ang_dist = np.abs(np.sin(angle - line_angle))
        line = np.clip(1.0 - ang_dist * 30, 0, 1) * np.clip(dist / max(max_r * 0.5, 1), 0, 1)
        M_pattern = np.clip(M_pattern + line * 0.2, 0, 1)

    # Center void
    center_void = np.clip(1.0 - dist / 20, 0, 1)
    R_pattern = np.clip(R_pattern + center_void * 0.5, 0, 1)

    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}


# === SHOKK SERIES — 7 NEW BOUNDARY-PUSHING PATTERNS ===

def texture_shokk_singularity(shape, mask, seed, sm):
    """SHOKK Singularity: Black hole gravitational lensing.
    R shows gravity well rings compressed toward center (smooth=chrome event horizon).
    M shows accretion disk spiral (metallic disk spinning around the void).
    CC modulates toward the event horizon for color distortion.
    The two channels create a hypnotic pull effect that morphs under lighting."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    angle = np.arctan2(yy - cy, xx - cx)
    max_r = min(h, w) / 2.0

    # Gravity well: rings that get tighter near center (logarithmic spacing)
    log_dist = np.log1p(dist / max(max_r * 0.1, 1))
    freq_gravity = 4 + rng.randint(0, 4)
    gravity_rings = (np.sin(log_dist * freq_gravity * 2 * np.pi) + 1.0) / 2.0
    # Smooth near center = event horizon (low R = chrome mirror)
    event_horizon = np.clip(1.0 - dist / (max_r * 0.15), 0, 1)
    R_pattern = gravity_rings * (1.0 - event_horizon) + (1.0 - event_horizon) * 0.1

    # Accretion disk: logarithmic spiral
    spiral_freq = 3 + rng.randint(0, 3)
    spiral = (np.sin(angle * spiral_freq + log_dist * 6) + 1.0) / 2.0
    # Disk is brightest at mid-range distance
    disk_mask = np.exp(-((dist - max_r * 0.35)**2) / (2 * (max_r * 0.2)**2))
    M_pattern = spiral * disk_mask + event_horizon * 0.8

    # CC: color shift toward event horizon
    CC_pattern = event_horizon * 0.8 + disk_mask * 0.3

    pv = np.clip((R_pattern + M_pattern) / 2.0, 0, 1)
    R_pattern = np.clip(R_pattern, 0, 1)
    M_pattern = np.clip(M_pattern, 0, 1)
    CC_pattern = np.clip(CC_pattern, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 55, "R_range": -70,
            "CC": None, "CC_range": 35}


def texture_shokk_nebula(shape, mask, seed, sm):
    """SHOKK Nebula: Cosmic gas cloud with star-forming regions.
    R channel shows diffuse dust clouds (multi-octave fractal noise = rough dust).
    M channel shows dense bright knots and filaments (chrome star cores).
    CC modulates for nebula color emission. Looks like Hubble imagery in metal."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Multi-octave Perlin-like noise for gas clouds
    dust = np.zeros((h, w), dtype=np.float32)
    stars = np.zeros((h, w), dtype=np.float32)
    for octave in range(5):
        freq = 2 ** (octave + 1)
        amp = 0.5 ** octave
        phase_x = rng.uniform(0, 100)
        phase_y = rng.uniform(0, 100)
        noise_x = np.sin(xx / max(w, 1) * freq * np.pi + phase_x) * np.cos(yy / max(h, 1) * freq * 0.7 * np.pi + phase_y)
        noise_y = np.cos(yy / max(h, 1) * freq * np.pi + phase_y * 1.3) * np.sin(xx / max(w, 1) * freq * 0.8 * np.pi + phase_x * 0.7)
        dust += (noise_x + noise_y) * amp

    dust = (dust - dust.min()) / (dust.max() - dust.min() + 1e-8)

    # Star-forming knots: bright compact regions
    n_stars = rng.randint(15, 40)
    for _ in range(n_stars):
        sx, sy = rng.randint(0, w), rng.randint(0, h)
        sr = rng.uniform(5, 25)
        brightness = rng.uniform(0.4, 1.0)
        star_dist = np.sqrt((xx - sx)**2 + (yy - sy)**2)
        star = np.exp(-(star_dist**2) / (2 * sr**2)) * brightness
        stars = np.maximum(stars, star)

    # Filaments: thin bright streaks connecting star regions
    filaments = np.zeros((h, w), dtype=np.float32)
    for _ in range(rng.randint(5, 12)):
        fa = rng.uniform(0, np.pi)
        fp = rng.uniform(0, 100)
        fil = np.sin((xx * np.cos(fa) + yy * np.sin(fa)) / max(min(h,w), 1) * rng.uniform(3, 8) * np.pi + fp)
        fil = np.clip(fil, 0, 1) ** 3 * rng.uniform(0.3, 0.7)
        filaments = np.maximum(filaments, fil)

    R_pattern = np.clip(dust * 0.7 + filaments * 0.3, 0, 1)  # Rough dust clouds
    M_pattern = np.clip(stars * 0.7 + filaments * 0.5, 0, 1)  # Chrome star knots
    CC_pattern = np.clip(dust * 0.4 + stars * 0.6, 0, 1)  # Color in emission regions

    pv = np.clip((R_pattern + M_pattern) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 50, "R_range": -60,
            "CC": None, "CC_range": 30}


def texture_shokk_predator(shape, mask, seed, sm):
    """SHOKK Predator: Active camouflage distortion field.
    R channel shows hexagonal cell boundaries (rough edges of cloaking cells).
    M channel shows the shimmer field inside each cell (chrome cloaking surface).
    Each cell has a slightly different metallic phase, creating a Predator-style
    adaptive camo shimmer that shifts under lighting."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Hexagonal grid
    scale = min(h, w) / 256.0
    hex_size = 24 * scale
    hex_h = hex_size * np.sqrt(3)

    # Hex coordinates
    row = yy / max(hex_h, 1)
    col = xx / max(hex_size * 1.5, 1)
    row_i = np.floor(row).astype(int)
    col_i = np.floor(col).astype(int)

    # Offset for hex grid
    offset = (col_i % 2).astype(np.float32) * 0.5
    row_shifted = row - offset
    row_i_shifted = np.floor(row_shifted).astype(int)

    # Local coordinates within hex cell
    ly = (row_shifted % 1.0) - 0.5
    lx = (col % 1.0) - 0.5

    # Distance from cell center (hex approximation)
    hex_dist = np.maximum(np.abs(ly), (np.abs(ly) * 0.5 + np.abs(lx) * 0.866))

    # Cell boundaries
    border_width = 0.08
    borders = np.clip(1.0 - (0.5 - hex_dist) / border_width, 0, 1)

    # Each cell gets a unique shimmer phase based on cell coordinates
    cell_hash = (row_i_shifted * 7919 + col_i * 104729 + seed) % 1000
    cell_phase = cell_hash.astype(np.float32) / 1000.0

    # Cell shimmer: angular gradient within each cell for Fresnel-like angle dependence
    cell_angle = np.arctan2(ly, lx)
    shimmer = (np.sin(cell_angle * 3 + cell_phase * 2 * np.pi) + 1.0) / 2.0
    shimmer *= (1.0 - borders)  # No shimmer on borders

    # Distortion ripple across entire surface
    ripple = (np.sin(xx / max(w, 1) * 6 * np.pi + yy / max(h, 1) * 4 * np.pi) + 1.0) / 2.0
    distortion = ripple * 0.3

    R_pattern = np.clip(borders * 0.8 + distortion * 0.2, 0, 1)  # Rough hex borders
    M_pattern = np.clip(shimmer * 0.7 + cell_phase * 0.3, 0, 1)  # Chrome shimmer field
    pv = np.clip((borders + shimmer) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_bioform(shape, mask, seed, sm):
    """SHOKK Bioform: Alien reaction-diffusion organism.
    Uses Gray-Scott-inspired simulation to create organic spots and labyrinthine
    structures. R channel shows the activator (rough organic ridges),
    M channel shows the inhibitor (chrome smooth valleys). They're mathematically
    linked but visually distinct. The surface looks ALIVE."""
    h, w = shape
    rng = np.random.RandomState(seed)

    # Simplified reaction-diffusion via multi-frequency interference
    # (True R-D simulation is too slow; this captures the visual character)
    yf = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis]
    xf = np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :]

    # Activator pattern: leopard-like spots via threshold of summed waves
    activator = np.zeros((h, w), dtype=np.float32)
    for i in range(6):
        freq = rng.uniform(8, 25)
        angle = rng.uniform(0, np.pi)
        phase = rng.uniform(0, 2 * np.pi)
        wave = np.sin(2 * np.pi * freq * (xf * np.cos(angle) + yf * np.sin(angle)) + phase)
        activator += wave

    # Threshold to create sharp organic boundaries
    activator = activator / 6.0
    act_thresh = np.percentile(activator, 45)
    activator_binary = np.clip((activator - act_thresh) * 5, 0, 1)

    # Inhibitor: shifted spots (reaction-diffusion inhibitor is larger, smoother)
    inhibitor = np.zeros((h, w), dtype=np.float32)
    for i in range(4):
        freq = rng.uniform(5, 15)
        angle = rng.uniform(0, np.pi)
        phase = rng.uniform(0, 2 * np.pi)
        wave = np.sin(2 * np.pi * freq * (xf * np.cos(angle) + yf * np.sin(angle)) + phase)
        inhibitor += wave
    inhibitor = (inhibitor / 4.0 + 1.0) / 2.0  # Normalize to 0-1

    # Worm-like labyrinthine channels connecting the spots
    channel_freq = rng.uniform(12, 20)
    channels = np.sin(xf * channel_freq * 2 * np.pi + np.sin(yf * channel_freq * np.pi) * 2)
    channels = np.clip(channels, -0.3, 0.3) / 0.6 + 0.5

    R_pattern = np.clip(activator_binary * 0.7 + channels * 0.3, 0, 1)  # Rough organic ridges
    M_pattern = np.clip(inhibitor * 0.6 + (1.0 - activator_binary) * 0.4, 0, 1)  # Chrome valleys
    pv = np.clip((R_pattern + M_pattern) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_tesseract(shape, mask, seed, sm):
    """SHOKK Tesseract: 4D hypercube projected into 2D — impossible geometry.
    R channel shows outer cube wireframe edges. M channel shows inner cube edges
    rotated 45 degrees. Creates an optical illusion of depth and dimensionality
    where the two cubes seem to phase through each other under lighting changes."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Tiling cell size
    cell = max(40, min(h, w) // 5)
    ly = (yy % cell).astype(np.float32) / cell  # 0-1 within cell
    lx = (xx % cell).astype(np.float32) / cell

    # Outer cube: axis-aligned wireframe
    line_w = 0.04
    edge_h = np.clip(1.0 - np.minimum(ly, 1.0 - ly) / line_w, 0, 1)  # Top/bottom edges
    edge_v = np.clip(1.0 - np.minimum(lx, 1.0 - lx) / line_w, 0, 1)  # Left/right edges
    # Inner square at 60% size
    inner_off = 0.2
    inner_h = np.clip(1.0 - np.minimum(np.abs(ly - inner_off), np.abs(ly - (1-inner_off))) / line_w, 0, 1)
    inner_h *= ((lx > inner_off - line_w) & (lx < 1 - inner_off + line_w)).astype(np.float32)
    inner_v = np.clip(1.0 - np.minimum(np.abs(lx - inner_off), np.abs(lx - (1-inner_off))) / line_w, 0, 1)
    inner_v *= ((ly > inner_off - line_w) & (ly < 1 - inner_off + line_w)).astype(np.float32)

    # Corner connecting lines (perspective projection of 4D edges)
    def corner_line(y0, x0, y1, x1):
        dy, dx = y1 - y0, x1 - x0
        length = max(np.sqrt(dy**2 + dx**2), 1e-6)
        t = np.clip(((lx - x0) * dx + (ly - y0) * dy) / (length**2), 0, 1)
        px, py = x0 + t * dx, y0 + t * dy
        d = np.sqrt((lx - px)**2 + (ly - py)**2)
        return np.clip(1.0 - d / line_w, 0, 1)

    # 4 connecting edges from outer corners to inner corners
    connect = np.zeros_like(ly)
    for (oy, ox) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        iy = inner_off if oy == 0 else 1.0 - inner_off
        ix = inner_off if ox == 0 else 1.0 - inner_off
        connect = np.maximum(connect, corner_line(oy, ox, iy, ix))

    outer_cube = np.clip(np.maximum(edge_h, edge_v) + connect * 0.8, 0, 1)

    # Inner rotated cube: diamond orientation (45° rotation)
    cy, cx = 0.5, 0.5
    # Rotate local coords 45 degrees
    cos45, sin45 = np.cos(np.pi/4), np.sin(np.pi/4)
    ry = (ly - cy) * cos45 - (lx - cx) * sin45
    rx = (ly - cy) * sin45 + (lx - cx) * cos45
    diamond_size = 0.28
    diamond_h = np.clip(1.0 - np.minimum(np.abs(ry - diamond_size), np.abs(ry + diamond_size)) / line_w, 0, 1)
    diamond_h *= (np.abs(rx) < diamond_size + line_w).astype(np.float32)
    diamond_v = np.clip(1.0 - np.minimum(np.abs(rx - diamond_size), np.abs(rx + diamond_size)) / line_w, 0, 1)
    diamond_v *= (np.abs(ry) < diamond_size + line_w).astype(np.float32)
    inner_cube = np.clip(np.maximum(diamond_h, diamond_v), 0, 1)

    # Vertices: bright dots at intersections
    vertices = np.zeros_like(ly)
    for (vy, vx) in [(0,0),(0,1),(1,0),(1,1),(inner_off,inner_off),(inner_off,1-inner_off),(1-inner_off,inner_off),(1-inner_off,1-inner_off)]:
        vertices = np.maximum(vertices, np.exp(-((ly-vy)**2+(lx-vx)**2)/(line_w*3)**2) * 0.8)

    R_pattern = np.clip(outer_cube * 0.8 + vertices * 0.5, 0, 1)
    M_pattern = np.clip(inner_cube * 0.8 + vertices * 0.5, 0, 1)
    pv = np.clip((outer_cube + inner_cube + vertices) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_plasma_storm(shape, mask, seed, sm):
    """SHOKK Plasma Storm: Violent branching plasma discharge from multiple epicenters.
    R channel shows main Lichtenberg discharge paths (smooth=chrome lightning paths).
    M channel shows ionization field (metallic plasma glow surrounding paths).
    CC modulates for plasma color emission. Maximum energy pattern."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    discharge = np.zeros((h, w), dtype=np.float32)
    field = np.zeros((h, w), dtype=np.float32)

    # Multiple epicenters
    n_sources = rng.randint(3, 7)
    for src in range(n_sources):
        cx = rng.randint(w // 8, 7 * w // 8)
        cy = rng.randint(h // 8, 7 * h // 8)
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        angle = np.arctan2(yy - cy, xx - cx)

        # Lichtenberg figure: fractal branching via angular frequency modulation
        n_arms = rng.randint(4, 8)
        for arm in range(n_arms):
            arm_angle = arm * 2 * np.pi / n_arms + rng.uniform(-0.3, 0.3)
            # Main arm direction
            ang_diff = np.abs(np.sin(angle - arm_angle))
            # Width narrows with distance for branching effect
            max_dist = min(h, w) * rng.uniform(0.15, 0.4)
            arm_width = 3.0 + dist * 0.02
            arm_line = np.exp(-(ang_diff * dist)**2 / (2 * arm_width**2))
            arm_line *= np.clip(1.0 - dist / max_dist, 0, 1)
            discharge = np.maximum(discharge, arm_line * rng.uniform(0.5, 1.0))

            # Sub-branches
            for sub in range(rng.randint(2, 5)):
                sub_dist = max_dist * rng.uniform(0.2, 0.7)
                sub_angle = arm_angle + rng.uniform(-0.8, 0.8)
                sub_mask = (dist > sub_dist * 0.8) & (dist < sub_dist * 1.5)
                sub_ang_diff = np.abs(np.sin(angle - sub_angle))
                sub_line = np.exp(-(sub_ang_diff * dist)**2 / (2 * 2.0**2))
                sub_line *= sub_mask.astype(np.float32) * 0.5
                discharge = np.maximum(discharge, sub_line)

        # Epicenter core glow
        core = np.exp(-(dist**2) / (2 * 15**2)) * 0.8
        discharge = np.maximum(discharge, core)

        # Ionization field: wider diffuse glow
        ion_glow = np.exp(-(dist**2) / (2 * (max_dist * 0.6)**2)) * 0.5
        field = np.maximum(field, ion_glow)

    discharge = np.clip(discharge, 0, 1)
    field = np.clip(field, 0, 1)
    R_pattern = 1.0 - discharge  # Low R where discharge = chrome paths
    M_pattern = np.clip(field * 0.6 + discharge * 0.4, 0, 1)  # Metallic glow field
    CC_pattern = np.clip(discharge * 0.7 + field * 0.3, 0, 1)
    pv = np.clip((discharge + field) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 55, "R_range": -70,
            "CC": None, "CC_range": 30}


def texture_shokk_waveform(shape, mask, seed, sm):
    """SHOKK Waveform: Audio frequency decomposition frozen in metal.
    Horizontal bands represent frequency ranges (bass→treble bottom→top).
    R channel shows amplitude peaks (rough at loud parts).
    M channel shows frequency energy (chrome at resonant frequencies).
    The Shokker signature sound made visible — a music visualizer in spec map."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    n_bands = 16  # Frequency bands
    band_h = h / n_bands
    amplitude = np.zeros((h, w), dtype=np.float32)
    energy = np.zeros((h, w), dtype=np.float32)

    for band in range(n_bands):
        y_center = (band + 0.5) * band_h
        band_mask = np.exp(-((yy - y_center)**2) / (2 * (band_h * 0.35)**2))

        # Generate "audio" waveform for this frequency band
        freq = 1 + band * 0.5  # Lower bands = lower visual frequency
        base_amp = rng.uniform(0.3, 1.0)
        phase = rng.uniform(0, 2 * np.pi)

        # Waveform envelope: random amplitude modulation
        env_freq = rng.uniform(0.5, 3.0)
        envelope = np.abs(np.sin(xx / max(w, 1) * env_freq * np.pi + phase))
        # Bass bands get bigger amplitude bars
        bass_boost = max(0.5, 1.0 - band / n_bands * 0.7)

        # Amplitude bars (vertical bars whose height follows the waveform)
        bar_width = max(4, w // 64)
        bar_x = (xx // bar_width).astype(int)
        bar_val = np.zeros_like(xx)
        unique_bars = np.unique(bar_x)
        for bx in unique_bars[:min(len(unique_bars), 200)]:
            bar_center_x = (bx + 0.5) * bar_width
            bar_amp = base_amp * (0.3 + 0.7 * np.abs(np.sin(bx * 0.3 + phase)))
            bar_mask = (bar_x == bx).astype(np.float32)
            bar_val += bar_mask * bar_amp

        amplitude += band_mask * bar_val * bass_boost * 0.15

        # Energy: smooth sine wave per band
        wave = (np.sin(xx / max(w, 1) * freq * 2 * np.pi + phase) + 1.0) / 2.0
        energy += band_mask * wave * base_amp * 0.15

    # EKG signature pulse across center
    center_band = h // 2
    pulse_y = np.exp(-((yy - center_band)**2) / (2 * (band_h * 0.8)**2))
    pulse_x = np.sin(xx / max(w, 1) * 8 * np.pi)
    # Sharp EKG spike
    spike_pos = w * rng.uniform(0.3, 0.7)
    spike = np.exp(-((xx - spike_pos)**2) / (2 * 10**2)) * 3.0
    ekg = pulse_y * np.clip(pulse_x * 0.3 + spike, -0.5, 1.0)

    amplitude = np.clip(amplitude + ekg * 0.3, 0, 1)
    energy = np.clip(energy + ekg * 0.2, 0, 1)

    R_pattern = amplitude  # Rough at amplitude peaks
    M_pattern = energy  # Chrome at frequency energy
    pv = np.clip((amplitude + energy) / 2.0, 0, 1)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}

def texture_shokk_phase_split(shape, mask, seed, sm):
    """SHOKK Phase Split: M and R driven by perpendicular sine waves.
    Creates a shimmering effect where metallic and roughness oscillate independently."""
    h, w = shape
    rng = np.random.RandomState(seed)
    freq_m = 8 + rng.randint(0, 8)
    freq_r = 8 + rng.randint(0, 8)
    phase_m = rng.uniform(0, 2 * np.pi)
    phase_r = rng.uniform(0, 2 * np.pi)
    y = np.linspace(0, 2 * np.pi * freq_m, h, dtype=np.float32)
    x = np.linspace(0, 2 * np.pi * freq_r, w, dtype=np.float32)
    M_pattern = (np.sin(y[:, np.newaxis] + phase_m) + 1.0) / 2.0  # 0-1 vertical waves
    R_pattern = (np.cos(x[np.newaxis, :] + phase_r) + 1.0) / 2.0  # 0-1 horizontal waves
    # Unified pattern is the average for compatibility
    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 45, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}

def texture_shokk_phase_vortex(shape, mask, seed, sm):
    """SHOKK Phase Vortex: Radial M pattern + angular R pattern + radial CC.
    Creates a spinning eye effect where channels rotate independently."""
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    angle = np.arctan2(yy - cy, xx - cx)
    rng = np.random.RandomState(seed)
    freq_r = 3 + rng.randint(0, 5)
    freq_a = 4 + rng.randint(0, 6)
    M_pattern = (np.sin(dist / max(cy, cx) * np.pi * freq_r) + 1.0) / 2.0
    R_pattern = (np.cos(angle * freq_a + rng.uniform(0, np.pi)) + 1.0) / 2.0
    CC_pattern = (np.sin(dist / max(cy, cx) * np.pi * 2 + np.pi / 3) + 1.0) / 2.0
    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 50, "R_range": -65,
            "CC": None, "CC_range": 30}

def texture_shokk_phase_interference(shape, mask, seed, sm):
    """SHOKK Phase Interference: Two overlapping wave systems creating moiré-like
    interference patterns in each channel independently."""
    h, w = shape
    rng = np.random.RandomState(seed)
    f1 = 6 + rng.randint(0, 10)
    f2 = 6 + rng.randint(0, 10)
    a1 = rng.uniform(0, np.pi)
    a2 = rng.uniform(0, np.pi)
    y = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis]
    x = np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :]
    wave1_m = np.sin(2 * np.pi * f1 * (x * np.cos(a1) + y * np.sin(a1)))
    wave2_m = np.sin(2 * np.pi * f2 * (x * np.cos(a1 + 0.5) + y * np.sin(a1 + 0.5)))
    M_pattern = ((wave1_m + wave2_m) / 2.0 + 1.0) / 2.0
    wave1_r = np.sin(2 * np.pi * f1 * (x * np.cos(a2) + y * np.sin(a2)))
    wave2_r = np.sin(2 * np.pi * f2 * (x * np.cos(a2 + 0.7) + y * np.sin(a2 + 0.7)))
    R_pattern = ((wave1_r + wave2_r) / 2.0 + 1.0) / 2.0
    pv = (M_pattern + R_pattern) / 2.0
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 40, "R_range": -60, "CC": None, "CC_pattern": None, "CC_range": 0}

def paint_shokk_phase(paint, shape, mask, seed, pm, bb):
    """Subtle paint tint for SHOKK Phase patterns — slight contrast shift."""
    if pm <= 0:
        return paint
    rng = np.random.RandomState(seed + 999)
    boost = 0.04 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + boost * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - boost * 0.3 * mask, 0, 1)
    return paint


# --- BASE MATERIAL REGISTRY ---
# Organized by category, alphabetized within each section. 58 bases total.
BASE_REGISTRY = {
    # ── STANDARD FINISHES ──────────────────────────────────────────────
    "ceramic":          {"M": 60,  "R": 8,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Ultra-smooth ceramic coating deep wet shine"},
    "gloss":            {"M": 0,   "R": 20,  "CC": 16, "paint_fn": paint_none,            "desc": "Standard glossy clearcoat"},
    "piano_black":      {"M": 5,   "R": 3,   "CC": 16, "paint_fn": paint_none,            "desc": "Deep piano black ultra-gloss mirror finish"},
    "satin":            {"M": 0,   "R": 100, "CC": 10, "paint_fn": paint_none,            "desc": "Soft satin partial clearcoat"},
    "silk":             {"M": 30,  "R": 85,  "CC": 16, "paint_fn": paint_silk_sheen,      "desc": "Silky smooth fabric-like sheen"},
    "wet_look":         {"M": 10,  "R": 5,   "CC": 16, "paint_fn": paint_wet_gloss,       "desc": "Deep wet clearcoat show shine"},
    # ── METALLIC & FLAKE ──────────────────────────────────────────────
    "copper":           {"M": 190, "R": 55,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Warm oxidized copper metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 35, "noise_R": 20},
    "diamond_coat":     {"M": 220, "R": 3,   "CC": 16, "paint_fn": paint_diamond_sparkle, "desc": "Diamond dust ultra-fine sparkle coat"},
    "electric_ice":     {"M": 240, "R": 10,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "Icy electric blue metallic — cold neon shimmer",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 8},
    "gunmetal":         {"M": 220, "R": 40,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Dark aggressive blue-gray metallic",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 30, "noise_R": 15},
    "metallic":         {"M": 200, "R": 50,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Standard metallic with visible flake",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 40, "noise_R": 18},
    "pearl":            {"M": 100, "R": 40,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Pearlescent iridescent sheen",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 12},
    "pearlescent_white":{"M": 120, "R": 30,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Tri-coat pearlescent white deep sparkle",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 10},
    "plasma_metal":     {"M": 230, "R": 18,  "CC": 16, "paint_fn": paint_plasma_shift,    "desc": "Electric plasma purple-blue metallic shift",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 12},
    "rose_gold":        {"M": 240, "R": 12,  "CC": 16, "paint_fn": paint_rose_gold_tint,  "desc": "Pink-gold metallic warm shimmer",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 10},
    "satin_gold":       {"M": 235, "R": 60,  "CC": 0,  "paint_fn": paint_warm_metal,      "desc": "Satin gold metallic warm sheen",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 18},
    # ── CHROME & MIRROR ───────────────────────────────────────────────
    "chrome":           {"M": 255, "R": 2,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Pure mirror chrome"},
    "dark_chrome":      {"M": 250, "R": 5,   "CC": 0,  "paint_fn": paint_smoked_darken,   "desc": "Smoked dark chrome black mirror"},
    "mercury":          {"M": 255, "R": 3,   "CC": 0,  "paint_fn": paint_mercury_pool,    "desc": "Liquid mercury pooling mirror — desaturated chrome flow"},
    "mirror_gold":      {"M": 255, "R": 2,   "CC": 0,  "paint_fn": paint_warm_metal,      "desc": "Pure mirror gold chrome"},
    "satin_chrome":     {"M": 250, "R": 45,  "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "BMW silky satin chrome",
                         "noise_scales": [4, 8], "noise_weights": [0.4, 0.6], "noise_M": 0, "noise_R": 15},
    "surgical_steel":   {"M": 245, "R": 6,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Medical grade mirror surgical steel"},
    # ── CANDY & CLEARCOAT VARIANTS ────────────────────────────────────
    "candy":            {"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Deep wet candy transparent glass"},
    "candy_chrome":     {"M": 250, "R": 4,   "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Candy-tinted chrome — deep color over mirror base"},
    "clear_matte":      {"M": 0,   "R": 160, "CC": 16, "paint_fn": paint_none,            "desc": "Matte clearcoat — flat but protected"},
    "smoked":           {"M": 15,  "R": 10,  "CC": 16, "paint_fn": paint_smoked_darken,   "desc": "Smoked tinted darkened clearcoat"},
    "spectraflame":     {"M": 245, "R": 8,   "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Hot Wheels candy-over-chrome deep sparkle"},
    "tinted_clear":     {"M": 40,  "R": 8,   "CC": 16, "paint_fn": paint_tinted_clearcoat,"desc": "Deep tinted clearcoat over base color"},
    # ── MATTE & FLAT ─────────────────────────────────────────────────
    "blackout":         {"M": 30,  "R": 220, "CC": 0,  "paint_fn": paint_none,            "desc": "Stealth murdered-out ultra dark"},
    "flat_black":       {"M": 0,   "R": 250, "CC": 0,  "paint_fn": paint_none,            "desc": "Dead flat zero-sheen black — no reflection at all"},
    "frozen":           {"M": 225, "R": 140, "CC": 0,  "paint_fn": paint_subtle_flake,    "desc": "Frozen icy matte metal",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 30},
    "frozen_matte":     {"M": 210, "R": 160, "CC": 0,  "paint_fn": paint_subtle_flake,    "desc": "BMW Individual frozen matte metallic",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "matte":            {"M": 0,   "R": 215, "CC": 0,  "paint_fn": paint_none,            "desc": "Flat matte zero shine"},
    "vantablack":       {"M": 0,   "R": 255, "CC": 0,  "paint_fn": paint_none,            "desc": "Absolute void zero reflection"},
    "volcanic":         {"M": 80,  "R": 180, "CC": 0,  "paint_fn": paint_volcanic_ash,    "desc": "Volcanic ash coating — dark gritty desaturated matte"},
    # ── BRUSHED & DIRECTIONAL GRAIN ──────────────────────────────────
    "brushed_aluminum": {"M": 230, "R": 55,  "CC": 0,  "paint_fn": paint_brushed_grain,   "desc": "Brushed natural aluminum directional grain",
                         "brush_grain": True, "noise_M": 15, "noise_R": 30},
    "brushed_titanium": {"M": 180, "R": 70,  "CC": 0,  "paint_fn": paint_brushed_grain,   "desc": "Heavy directional titanium grain",
                         "brush_grain": True, "noise_M": 25, "noise_R": 45},
    "satin_metal":      {"M": 235, "R": 65,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Subtle brushed satin metallic",
                         "brush_grain": True, "noise_R": 20},
    # ── TACTICAL & INDUSTRIAL ────────────────────────────────────────
    "cerakote":         {"M": 40,  "R": 130, "CC": 0,  "paint_fn": paint_tactical_flat,   "desc": "Mil-spec ceramic tactical coating"},
    "duracoat":         {"M": 25,  "R": 170, "CC": 0,  "paint_fn": paint_tactical_flat,   "desc": "Tactical epoxy durable coating"},
    "powder_coat":      {"M": 20,  "R": 155, "CC": 0,  "paint_fn": paint_none,            "desc": "Thick industrial powder coat finish"},
    "rugged":           {"M": 50,  "R": 190, "CC": 0,  "paint_fn": paint_tactical_flat,   "desc": "Rugged off-road tactical rough coating"},
    # ── RAW METAL & WEATHERED ────────────────────────────────────────
    "anodized":         {"M": 170, "R": 80,  "CC": 0,  "paint_fn": paint_subtle_flake,    "desc": "Gritty matte anodized aluminum",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "burnt_headers":    {"M": 190, "R": 45,  "CC": 0,  "paint_fn": paint_burnt_metal,     "desc": "Exhaust header heat-treated gold-blue oxide",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 20},
    "galvanized":       {"M": 195, "R": 65,  "CC": 0,  "paint_fn": paint_galvanized_speckle, "desc": "Hot-dip galvanized zinc crystalline",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 25, "noise_R": 30},
    "heat_treated":     {"M": 185, "R": 35,  "CC": 0,  "paint_fn": paint_heat_tint,       "desc": "Heat-treated titanium blue-gold zones",
                         "noise_scales": [8, 16], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 15},
    "patina_bronze":    {"M": 160, "R": 90,  "CC": 0,  "paint_fn": paint_patina_green,    "desc": "Aged oxidized bronze with green patina",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35},
    "raw_aluminum":     {"M": 240, "R": 30,  "CC": 0,  "paint_fn": paint_raw_aluminum,    "desc": "Bare unfinished aluminum sheet metal",
                         "noise_scales": [4, 8], "noise_weights": [0.4, 0.6], "noise_M": 10, "noise_R": 20},
    "sandblasted":      {"M": 200, "R": 180, "CC": 0,  "paint_fn": paint_none,            "desc": "Raw sandblasted metal rough texture"},
    "titanium_raw":     {"M": 200, "R": 50,  "CC": 0,  "paint_fn": paint_raw_aluminum,    "desc": "Raw unpolished titanium industrial metal",
                         "noise_scales": [4, 8, 16], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 25},
    # ── EXOTIC & COLOR-SHIFT ─────────────────────────────────────────
    "chameleon":        {"M": 160, "R": 25,  "CC": 16, "paint_fn": paint_chameleon_shift,  "desc": "Dual-tone color-shift angle-dependent"},
    "iridescent":       {"M": 210, "R": 20,  "CC": 16, "paint_fn": paint_iridescent_shift,"desc": "Rainbow angle-shift iridescent wrap"},
    # ── WRAP & COATING ───────────────────────────────────────────────
    "liquid_wrap":      {"M": 80,  "R": 110, "CC": 0,  "paint_fn": paint_satin_wrap,      "desc": "Liquid rubber peel coat — textured matte wrap"},
    "primer":           {"M": 0,   "R": 200, "CC": 0,  "paint_fn": paint_primer_flat,     "desc": "Raw flat primer gray zero sheen"},
    "satin_wrap":       {"M": 0,   "R": 130, "CC": 0,  "paint_fn": paint_satin_wrap,      "desc": "Vinyl wrap satin non-metallic sheen"},
    # ── ORGANIC / PERLIN NOISE ───────────────────────────────────────
    "living_matte":     {"M": 0,   "R": 180, "CC": 0,  "paint_fn": paint_none,            "desc": "Organic matte with natural Perlin surface variation",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "noise_M": 0, "noise_R": 30},
    "organic_metal":    {"M": 210, "R": 45,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Organic flowing metallic with Perlin noise terrain",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "noise_M": 35, "noise_R": 20, "noise_CC": 8},
    "terrain_chrome":   {"M": 250, "R": 8,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Chrome with Perlin terrain-like distortion in roughness",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.45, "noise_M": 0, "noise_R": 25},
}

# --- PATTERN TEXTURE REGISTRY ---
# !! ARCHITECTURE GUARD — READ BEFORE MODIFYING !!
# See ARCHITECTURE.md for full documentation.
# - Each entry maps a pattern ID to {texture_fn, paint_fn, variable_cc, desc}
# - texture_fn generates the spatial pattern array (0-1)
# - paint_fn modifies the RGB paint layer in pattern grooves
# - Adding entries is SAFE. Removing or renaming entries WILL break the UI.
# - If a UI pattern ID is missing here, it silently renders as "none" (invisible).
# - The v7.0 alias block (~line 5170+) maps 162 UI patterns to closest texture_fn.
#   If you need different visuals for an alias, create a NEW texture_fn and re-point it.
#   DO NOT modify the shared texture_fn — it breaks every other pattern using it.
PATTERN_REGISTRY = {
    "acid_wash":         {"texture_fn": texture_acid_wash,        "paint_fn": paint_acid_etch,        "variable_cc": True,  "desc": "Corroded acid-etched surface"},
    "aero_flow": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Aerodynamic flow visualization streaks"},
    "argyle": {"texture_fn": texture_plaid, "paint_fn": paint_plaid_tint, "variable_cc": False, "desc": "Diamond/rhombus overlapping argyle"},
    "art_deco": {"texture_fn": texture_chevron, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "1920s geometric fan/sunburst motif"},
    "asphalt_texture": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Road surface aggregate texture"},
    "atomic_orbital": {"texture_fn": texture_ripple, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Electron cloud probability orbital rings"},
    "aurora_bands": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Northern lights wavy curtain bands"},
    "aztec": {"texture_fn": texture_chevron, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Angular stepped Aztec geometric blocks"},
    "bamboo_stalk": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Vertical bamboo stalks with joints"},
    "barbed_wire":       {"texture_fn": texture_barbed_wire,     "paint_fn": paint_barbed_scratch,   "variable_cc": False, "desc": "Twisted wire with barb spikes"},
    "basket_weave": {"texture_fn": texture_basket_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Over-under basket weave pattern"},
    "battle_worn":       {"texture_fn": texture_battle_worn,      "paint_fn": paint_scratch_marks,    "variable_cc": True,  "desc": "Scratched weathered damage"},
    "binary_code": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Streaming 0s and 1s binary data"},
    "biohazard": {"texture_fn": texture_spiderweb, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Repeating biohazard trefoil symbol"},
    "biomechanical": {"texture_fn": texture_circuit_board, "paint_fn": paint_circuit_glow, "variable_cc": False, "desc": "H.R. Giger organic-mechanical hybrid"},
    "blue_flame": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Intense blue-white hot flame tips"},
    "board_wax": {"texture_fn": texture_ripple, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Circular surfboard wax rub pattern"},
    "brake_dust": {"texture_fn": texture_metal_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Hot brake dust particle scatter"},
    "brick":             {"texture_fn": texture_brick,           "paint_fn": paint_brick_mortar,     "variable_cc": False, "desc": "Offset brick blocks with mortar lines"},
    "bullet_holes": {"texture_fn": texture_fracture, "paint_fn": paint_fracture_damage, "variable_cc": True, "desc": "Scattered impact penetration holes"},
    "camo":              {"texture_fn": texture_camo,            "paint_fn": paint_camo_pattern,     "variable_cc": False, "desc": "Digital splinter camouflage blocks"},
    "cape_flow": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Flowing superhero cape fabric waves"},
    "carbon_4x4": {"texture_fn": texture_kevlar_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Larger 4-harness satin weave carbon"},
    "carbon_fiber":      {"texture_fn": texture_carbon_fiber,     "paint_fn": paint_carbon_darken,    "variable_cc": False, "desc": "Woven 2x2 twill weave"},
    "carbon_spread_tow": {"texture_fn": texture_carbon_fiber, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Flat spread tow ultra-thin carbon tape"},
    "carbon_uni": {"texture_fn": texture_carbon_fiber, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Uni-directional carbon fiber"},
    "cartoon_plaid": {"texture_fn": texture_plaid, "paint_fn": paint_plaid_tint, "variable_cc": False, "desc": "Exaggerated bold cartoon plaid check"},
    "caustic": {"texture_fn": texture_ripple, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Underwater dancing light caustic pools"},
    "celtic_knot":       {"texture_fn": texture_celtic_knot,    "paint_fn": paint_celtic_emboss,    "variable_cc": False, "desc": "Interwoven flowing band knot pattern"},
    "chainlink": {"texture_fn": texture_hex_mesh, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Chain-link fence diagonal wire grid"},
    "chainmail":         {"texture_fn": texture_chainmail,       "paint_fn": paint_chainmail_emboss, "variable_cc": False, "desc": "Interlocking metal ring mesh"},
    "checkered_flag": {"texture_fn": texture_houndstooth, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Classic racing checkered flag grid"},
    "chevron":           {"texture_fn": texture_chevron,        "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Repeating V/arrow stripe pattern"},
    "circuit_board":     {"texture_fn": texture_circuit_board,   "paint_fn": paint_circuit_glow,     "variable_cc": False, "desc": "PCB trace lines with pads and vias"},
    "circuitboard": {"texture_fn": texture_circuit_board, "paint_fn": paint_circuit_glow, "variable_cc": False, "desc": "PCB trace pattern metallic traces"},
    "classic_hotrod": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Traditional hot rod flame sweep"},
    "comic_halftone": {"texture_fn": texture_metal_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Ben-Day dot halftone print pattern"},
    "comic_panel": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Comic book panel grid layout lines"},
    "corrugated": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Corrugated sheet metal parallel ridges"},
    "cracked_ice":       {"texture_fn": texture_cracked_ice,      "paint_fn": paint_ice_cracks,       "variable_cc": False, "desc": "Frozen crack network"},
    "crocodile": {"texture_fn": texture_dragon_scale, "paint_fn": paint_scale_pattern, "variable_cc": False, "desc": "Deep embossed crocodile hide scales"},
    "crosshatch":        {"texture_fn": texture_crosshatch,     "paint_fn": paint_crosshatch_ink,   "variable_cc": False, "desc": "Overlapping diagonal pen stroke lines"},
    "damascus":          {"texture_fn": texture_damascus,       "paint_fn": paint_damascus_layer,   "variable_cc": False, "desc": "Flowing damascus steel wavy grain"},
    "dark_knight_scales": {"texture_fn": texture_dragon_scale, "paint_fn": paint_scale_pattern, "variable_cc": False, "desc": "Armored scale mail dark hero texture"},
    "data_stream": {"texture_fn": texture_hologram, "paint_fn": paint_hologram_lines, "variable_cc": False, "desc": "Flowing horizontal data packet streams"},
    "dazzle":            {"texture_fn": texture_dazzle,          "paint_fn": paint_dazzle_contrast,  "variable_cc": False, "desc": "Bold Voronoi B/W dazzle camo patches"},
    "denim": {"texture_fn": texture_crosshatch, "paint_fn": paint_crosshatch_ink, "variable_cc": False, "desc": "Blue jean diagonal twill weave"},
    "diamond_plate":     {"texture_fn": texture_diamond_plate,    "paint_fn": paint_diamond_emboss,   "variable_cc": False, "desc": "Industrial raised diamond tread"},
    "dimensional": {"texture_fn": texture_interference, "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Newtons rings thin-film interference"},
    "dna_helix": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Double-helix DNA strand spiral"},
    "dragon_scale":      {"texture_fn": texture_dragon_scale,     "paint_fn": paint_scale_pattern,    "variable_cc": False, "desc": "Overlapping hex reptile scales"},
    "drift_marks": {"texture_fn": texture_tire_tread, "paint_fn": paint_tread_darken, "variable_cc": False, "desc": "Sideways drift tire trail marks"},
    "ekg": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Heartbeat EKG monitor line pulse"},
    "ember_mesh":        {"texture_fn": texture_ember_mesh,    "paint_fn": paint_ember_mesh_glow,  "variable_cc": False, "desc": "Glowing hot wire grid with ember nodes"},
    "ember_scatter": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Floating glowing embers scattered"},
    "exhaust_wrap": {"texture_fn": texture_kevlar_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Header wrap woven heat tape"},
    "expanded_metal": {"texture_fn": texture_hex_mesh, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Stretched diamond expanded mesh"},
    "feather": {"texture_fn": texture_snake_skin, "paint_fn": paint_snake_emboss, "variable_cc": False, "desc": "Layered overlapping bird feather barbs"},
    "fingerprint": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Swirling concentric fingerprint ridges"},
    "finish_line": {"texture_fn": texture_houndstooth, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Bold start/finish line checkered band"},
    "fire_lick": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Flickering flame tongues licking upward"},
    "fireball": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Explosive spherical fireball burst"},
    "flame_fade": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Flames gradually fading into smoke"},
    "fleur_de_lis": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "French lily repeating motif"},
    "forged_carbon":     {"texture_fn": texture_forged_carbon,    "paint_fn": paint_forged_carbon,    "variable_cc": False, "desc": "Chopped irregular carbon chunks"},
    "fractal": {"texture_fn": texture_plasma, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Self-similar Mandelbrot fractal branching"},
    "fracture":          {"texture_fn": texture_fracture,      "paint_fn": paint_fracture_damage,  "variable_cc": True,  "desc": "Shattered impact glass with radial crack network"},
    "fresnel_ghost": {"texture_fn": texture_hex_mesh, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Hidden hex pattern Fresnel amplification"},
    "frost_crystal":     {"texture_fn": texture_frost_crystal,  "paint_fn": paint_frost_crystal,    "variable_cc": False, "desc": "Ice crystal branching fractals"},
    "g_force": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Acceleration force vector compression"},
    "gamma_pulse": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Radioactive gamma energy pulse waves"},
    "ghost_flames": {"texture_fn": texture_plasma, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Subtle transparent flame wisps"},
    "giraffe": {"texture_fn": texture_leopard, "paint_fn": paint_leopard_spots, "variable_cc": False, "desc": "Irregular polygon giraffe spot patches"},
    "glacier_crack": {"texture_fn": texture_cracked_ice, "paint_fn": paint_ice_cracks, "variable_cc": False, "desc": "Deep blue-white glacial ice fissures"},
    "glitch_scan": {"texture_fn": texture_hologram, "paint_fn": paint_hologram_lines, "variable_cc": False, "desc": "Horizontal glitch scanline displacement"},
    "gothic_cross": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Ornate gothic cathedral cross grid"},
    "gothic_scroll": {"texture_fn": texture_damascus, "paint_fn": paint_damascus_layer, "variable_cc": False, "desc": "Flowing dark ornamental scroll filigree"},
    "grating": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Industrial floor grating parallel bars"},
    "greek_key": {"texture_fn": texture_chevron, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Continuous right-angle meander border"},
    "grip_tape": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Coarse skateboard grip tape texture"},
    "groovy_swirl": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Psychedelic 70s groovy swirl pattern"},
    "hailstorm": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "Dense scattered impact crater dimples"},
    "halfpipe": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Curved halfpipe ramp cross-section"},
    "hammered":          {"texture_fn": texture_hammered,         "paint_fn": paint_hammered_dimples, "variable_cc": False, "desc": "Hand-hammered dimple pattern"},
    "harness_weave": {"texture_fn": texture_basket_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Racing harness nylon webbing"},
    "hellfire": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Dark menacing flames from below"},
    "hero_burst": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Comic book superhero starburst explosion"},
    "herringbone": {"texture_fn": texture_chevron, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "V-shaped zigzag brick/tile pattern"},
    "hex_mesh":          {"texture_fn": texture_hex_mesh,         "paint_fn": paint_hex_emboss,       "variable_cc": False, "desc": "Honeycomb wire grid"},
    "hibiscus": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Hawaiian hibiscus flower pattern"},
    "hologram":          {"texture_fn": texture_hologram,         "paint_fn": paint_hologram_lines,   "variable_cc": False, "desc": "Horizontal scanline projection"},
    "holographic": {"texture_fn": texture_holographic_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Hologram diffraction grating rainbow"},
    "holographic_flake": {"texture_fn": texture_holographic_flake,"paint_fn": paint_coarse_flake,     "variable_cc": False, "desc": "Rainbow prismatic micro-grid flake"},
    "houndstooth":       {"texture_fn": texture_houndstooth,    "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Classic houndstooth check textile"},
    "inferno": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Intense raging fire consuming everything"},
    "interference":      {"texture_fn": texture_interference,     "paint_fn": paint_interference_shift,"variable_cc": False, "desc": "Flowing rainbow wave bands"},
    "iron_cross": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Bold Iron Cross motif array"},
    "japanese_wave": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Kanagawa-style great wave curling crests"},
    "kevlar_weave": {"texture_fn": texture_kevlar_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Tight aramid fiber golden weave"},
    "knurled": {"texture_fn": texture_crosshatch, "paint_fn": paint_crosshatch_ink, "variable_cc": False, "desc": "Machine knurling diagonal cross-hatch"},
    "lap_counter": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Repeating tally mark lap counter"},
    "lava_flow":         {"texture_fn": texture_lava_flow,       "paint_fn": paint_lava_glow,        "variable_cc": True,  "desc": "Flowing molten rock with hot cracks"},
    "leather_grain": {"texture_fn": texture_hammered, "paint_fn": paint_hammered_dimples, "variable_cc": False, "desc": "Natural grain leather pebble texture"},
    "leopard":           {"texture_fn": texture_leopard,         "paint_fn": paint_leopard_spots,    "variable_cc": False, "desc": "Organic leopard rosette spots"},
    "lightning":         {"texture_fn": texture_lightning,        "paint_fn": paint_lightning_glow,   "variable_cc": False, "desc": "Forked lightning bolt paths"},
    "magma_crack":       {"texture_fn": texture_magma_crack,     "paint_fn": paint_magma_glow,       "variable_cc": False, "desc": "Voronoi boundary cracks with orange lava glow"},
    "mandala": {"texture_fn": texture_spiderweb, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Radial symmetry mandala flower"},
    "marble":            {"texture_fn": texture_marble,          "paint_fn": paint_marble_vein,      "variable_cc": False, "desc": "Soft noise veins like polished marble"},
    "matrix_rain": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Falling green character rain columns"},
    "mega_flake":        {"texture_fn": texture_mega_flake,      "paint_fn": paint_mega_sparkle,     "variable_cc": False, "desc": "Large hex glitter flake facets"},
    "metal_flake":       {"texture_fn": texture_metal_flake,      "paint_fn": paint_coarse_flake,     "variable_cc": False, "desc": "Coarse visible metallic flake"},
    "molecular": {"texture_fn": texture_hex_mesh, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Ball-and-stick molecular bond diagram"},
    "mosaic":            {"texture_fn": texture_mosaic,          "paint_fn": paint_mosaic_tint,      "variable_cc": False, "desc": "Irregular Voronoi stained glass tiles"},
    "multicam":          {"texture_fn": texture_multicam,        "paint_fn": paint_multicam_colors,  "variable_cc": False, "desc": "5-layer organic Perlin camo pattern"},
    "nanoweave": {"texture_fn": texture_carbon_fiber, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Microscopic tight-knit nano fiber"},
    "neural": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Living neural network Voronoi cells"},
    "neuron_network": {"texture_fn": texture_circuit_board, "paint_fn": paint_circuit_glow, "variable_cc": False, "desc": "Branching neural dendrite connection web"},
    "nitro_burst": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Nitrous oxide flame burst spray"},
    "none":              {"texture_fn": None,                     "paint_fn": paint_none,             "variable_cc": False, "desc": "No pattern overlay"},
    "norse_rune": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Elder Futhark rune symbol grid"},
    "ocean_foam": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "White sea foam bubbles on water"},
    "optical_illusion": {"texture_fn": texture_interference, "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Moire interference impossible geometry"},
    "p_plasma": {"texture_fn": texture_plasma, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Plasma ball discharge electric tendrils"},
    "p_tessellation": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Geometric Penrose-style tiling"},
    "p_topographic": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Contour map elevation isolines"},
    "paisley": {"texture_fn": texture_damascus, "paint_fn": paint_damascus_layer, "variable_cc": False, "desc": "Teardrop curved paisley ornamental"},
    "palm_frond": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Tropical palm leaf frond silhouettes"},
    "peeling_paint": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Curling paint peel flake patches"},
    "pentagram": {"texture_fn": texture_spiderweb, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Five-pointed star geometric array"},
    "perforated": {"texture_fn": texture_metal_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Evenly punched round hole grid"},
    "pinstripe":         {"texture_fn": texture_pinstripe,       "paint_fn": paint_pinstripe,        "variable_cc": False, "desc": "Thin parallel racing stripes"},
    "pinstripe_flames": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Thin elegant pinstripe flame outlines"},
    "pit_lane_marks": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Pit lane boundary lines and markings"},
    "pixel_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Retro 8-bit pixel block mosaic"},
    "plaid":             {"texture_fn": texture_plaid,          "paint_fn": paint_plaid_tint,       "variable_cc": False, "desc": "Overlapping tartan plaid bands"},
    "plasma":            {"texture_fn": texture_plasma,           "paint_fn": paint_plasma_veins,     "variable_cc": False, "desc": "Branching electric plasma veins"},
    "podium_stripe": {"texture_fn": texture_chevron, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Victory podium step stripe bands"},
    "polka_pop": {"texture_fn": texture_leopard, "paint_fn": paint_leopard_spots, "variable_cc": False, "desc": "Bold pop art polka dot pattern"},
    "pow_burst": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Comic action word explosion burst"},
    "power_aura": {"texture_fn": texture_plasma, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Glowing energy aura surrounding hero"},
    "power_bolt": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Electric power bolt lightning strike"},
    "prehistoric_spot": {"texture_fn": texture_leopard, "paint_fn": paint_leopard_spots, "variable_cc": False, "desc": "Flintstones-style animal print spots"},
    "pulse_monitor": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Multi-line vital signs monitor waveforms"},
    "qr_code": {"texture_fn": texture_houndstooth, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Dense QR code square block grid"},
    "racing_stripe": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Bold dual center racing stripes"},
    "rain_drop":         {"texture_fn": texture_rain_drop,       "paint_fn": paint_rain_droplets,    "variable_cc": False, "desc": "Water droplet beading on surface"},
    "razor":             {"texture_fn": texture_razor,           "paint_fn": paint_razor_slash,      "variable_cc": False, "desc": "Diagonal aggressive slash marks"},
    "razor_wire":        {"texture_fn": texture_razor_wire,    "paint_fn": paint_razor_wire_scratch, "variable_cc": False, "desc": "Coiled helical wire with barbed loops"},
    "retro_atom": {"texture_fn": texture_ripple, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "1950s atomic age orbital symbol"},
    "retro_flower_power": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Groovy retro 60s daisy flower"},
    "rev_counter": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Tachometer LED bar segment array"},
    "rip_tide": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Dangerous swirling rip current flow"},
    "ripple":            {"texture_fn": texture_ripple,           "paint_fn": paint_ripple_reflect,   "variable_cc": False, "desc": "Concentric water drop rings"},
    "rivet_grid": {"texture_fn": texture_rivet_plate, "paint_fn": paint_rivet_plate_emboss, "variable_cc": False, "desc": "Evenly spaced industrial rivet dots"},
    "rivet_plate":       {"texture_fn": texture_rivet_plate,    "paint_fn": paint_rivet_plate_emboss, "variable_cc": False, "desc": "Industrial riveted panel seams with chrome heads"},
    "road_rash": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Sliding contact abrasion scrape marks"},
    "roll_cage": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Tubular roll cage structure grid"},
    "rooster_tail": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "Dirt spray rooster tail splash"},
    "rpm_gauge": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Tachometer arc needle sweep"},
    "rust_bloom": {"texture_fn": texture_acid_wash, "paint_fn": paint_acid_etch, "variable_cc": True, "desc": "Expanding rust spot corrosion blooms"},
    "sandstorm": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Dense blowing sand particle streaks"},
    "shield_rings": {"texture_fn": texture_ripple, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Concentric hero shield ring pattern"},
    "shokk_bioform":      {"texture_fn": texture_shokk_bioform,      "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Alien reaction-diffusion organic living surface"},
    "shokk_bolt": {"texture_fn": texture_shokk_bolt_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Fractal branching lightning with chrome/matte split"},
    "shokk_fracture": {"texture_fn": texture_shokk_fracture_v2, "paint_fn": paint_shokk_phase, "variable_cc": True, "desc": "SHOKK: Shattered glass with chrome shard facets"},
    "shokk_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Perspective-warped digital grid tunnel"},
    "shokk_hex": {"texture_fn": texture_hex_mesh, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Hexagonal cells with electric edge glow"},
    "shokk_nebula":       {"texture_fn": texture_shokk_nebula,       "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Cosmic gas cloud with star-forming knots"},
    "shokk_phase_interference": {"texture_fn": texture_shokk_phase_interference, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK Phase: Dual-wave moiré interference pattern"},
    "shokk_phase_split":        {"texture_fn": texture_shokk_phase_split,        "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK Phase: Independent M/R sine waves — shimmer split"},
    "shokk_phase_vortex":       {"texture_fn": texture_shokk_phase_vortex,       "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK Phase: Radial/angular vortex with CC modulation"},
    "shokk_plasma_storm": {"texture_fn": texture_shokk_plasma_storm, "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Multi-epicenter branching plasma discharge"},
    "shokk_predator":     {"texture_fn": texture_shokk_predator,     "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Active camo distortion field hexagonal shimmer"},
    "shokk_pulse_wave": {"texture_fn": texture_shokk_pulse_wave_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Breathing concentric chrome/matte rings"},
    "shokk_scream": {"texture_fn": texture_shokk_scream_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Acoustic shockwave pressure visualization"},
    "shokk_singularity":  {"texture_fn": texture_shokk_singularity,  "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Black hole gravity well with accretion disk"},
    "shokk_tesseract":    {"texture_fn": texture_shokk_tesseract,    "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: 4D hypercube impossible geometry wireframe"},
    "shokk_waveform":     {"texture_fn": texture_shokk_waveform,     "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Audio frequency decomposition visualizer"},
    "shrapnel": {"texture_fn": texture_fracture, "paint_fn": paint_fracture_damage, "variable_cc": True, "desc": "Irregular shrapnel damage fragments"},
    "skid_marks": {"texture_fn": texture_tire_tread, "paint_fn": paint_tread_darken, "variable_cc": False, "desc": "Black rubber tire skid marks"},
    "skull":             {"texture_fn": texture_skull,          "paint_fn": paint_skull_darken,     "variable_cc": False, "desc": "Repeating skull mesh array"},
    "skull_wings": {"texture_fn": texture_skull, "paint_fn": paint_skull_darken, "variable_cc": False, "desc": "Affliction-style winged skull spread"},
    "snake_skin":        {"texture_fn": texture_snake_skin,      "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Elongated overlapping reptile scales"},
    "solar_flare": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Erupting coronal mass ejection"},
    "sound_wave": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Audio waveform amplitude oscillation"},
    "soundwave": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Audio waveform visualization"},
    "spark_scatter": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Grinding metal spark shower trails"},
    "speed_lines": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Motion speed streak action lines"},
    "spiderweb":         {"texture_fn": texture_spiderweb,      "paint_fn": paint_spiderweb_crack,  "variable_cc": False, "desc": "Radial + concentric web crack lines"},
    "sponsor_fade": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Gradient fade zones for sponsor areas"},
    "stardust":          {"texture_fn": texture_stardust,         "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Sparse bright star pinpoints"},
    "starting_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Grid slot positions track layout"},
    "static_noise":      {"texture_fn": texture_static_noise,  "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "TV static blocky pixel noise grain"},
    "steampunk_gears": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Interlocking clockwork gear wheel array"},
    "surf_stripe": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Retro surfboard racing stripes"},
    "tessellation": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Interlocking M.C. Escher-style tiles"},
    "thorn_vine": {"texture_fn": texture_barbed_wire, "paint_fn": paint_barbed_scratch, "variable_cc": False, "desc": "Twisted thorny vine dark botanical"},
    "tiger_stripe": {"texture_fn": texture_camo, "paint_fn": paint_camo_pattern, "variable_cc": False, "desc": "Organic tiger stripe broken bands"},
    "tiki_totem": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Carved tiki pole face pattern"},
    "tire_smoke": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Burnout tire smoke wisps and haze"},
    "tire_tread":        {"texture_fn": texture_tire_tread,      "paint_fn": paint_tread_darken,     "variable_cc": False, "desc": "Directional V-groove rubber tread"},
    "toon_bones": {"texture_fn": texture_skull, "paint_fn": paint_skull_darken, "variable_cc": False, "desc": "Cartoon crossbones skull pattern"},
    "toon_cloud": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "Puffy cartoon cloud shapes"},
    "toon_lightning": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Cartoon jagged lightning bolt shapes"},
    "toon_speed": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Cartoon speed lines motion blur"},
    "toon_stars": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Cartoon star burst impact shapes"},
    "topographic":       {"texture_fn": texture_topographic,    "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Elevation contour map lines"},
    "torch_burn": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Focused torch flame burn marks"},
    "tornado": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Spiraling funnel vortex rotation"},
    "track_map": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Race circuit layout line pattern"},
    "tribal_flame": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Flowing tribal tattoo flame curves"},
    "tron":              {"texture_fn": texture_tron,            "paint_fn": paint_tron_glow,        "variable_cc": False, "desc": "Neon 48px grid with 2px light lines"},
    "trophy_laurel": {"texture_fn": texture_celtic_knot, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Victory laurel wreath motif"},
    "tropical_leaf": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Large monstera tropical leaf outlines"},
    "turbine":           {"texture_fn": texture_turbine,       "paint_fn": paint_turbine_spin,     "variable_cc": False, "desc": "Radial fan blade spiral from center"},
    "turbo_swirl": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Turbocharger compressor spiral vortex"},
    "victory_confetti": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Scattered celebration confetti"},
    "villain_stripe": {"texture_fn": texture_chevron, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Diagonal villain menace stripe"},
    "voronoi_shatter": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Clean voronoi cell shatter sharp edges"},
    "wave":              {"texture_fn": texture_wave,           "paint_fn": paint_wave_shimmer,     "variable_cc": False, "desc": "Smooth flowing sine wave ripples"},
    "wave_curl": {"texture_fn": texture_wave, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Curling ocean wave barrel shape"},
    "web_pattern": {"texture_fn": texture_spiderweb, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Spider web radial strand pattern"},
    "wildfire": {"texture_fn": texture_lava_flow, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Chaotic spreading wildfire pattern"},
    "wind_tunnel": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Flow visualization smoke streaks"},
    "wood_grain":        {"texture_fn": texture_wood_grain,      "paint_fn": paint_wood_grain,       "variable_cc": False, "desc": "Natural flowing wood grain texture"},
    "zebra": {"texture_fn": texture_pinstripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Bold black-white zebra stripe pattern"},
    "zigzag_stripe": {"texture_fn": texture_chevron, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Sharp cartoon zigzag stripe"},
}

# --- MONOLITHIC FINISHES (can't decompose) ---
MONOLITHIC_REGISTRY = {
    "aurora":             (spec_aurora,        paint_aurora),
    "cel_shade":          (spec_cel_shade,     paint_cel_shade),
    "chameleon_arctic":   (spec_chameleon_pro, paint_chameleon_arctic),
    "chameleon_copper":   (spec_chameleon_pro, paint_chameleon_copper),
    "chameleon_midnight": (spec_chameleon_pro, paint_chameleon_midnight),
    "chameleon_ocean":    (spec_chameleon_pro, paint_chameleon_ocean),
    "chameleon_phoenix":  (spec_chameleon_pro, paint_chameleon_phoenix),
    "chameleon_venom":    (spec_chameleon_pro, paint_chameleon_venom),
    "cs_cool":       (spec_cs_cool,      paint_cs_cool),
    "cs_deepocean":  (spec_cs_deepocean,  paint_cs_deepocean),
    "cs_emerald":    (spec_cs_emerald,    paint_cs_emerald),
    "cs_extreme":    (spec_cs_extreme,   paint_cs_extreme),
    "cs_inferno":    (spec_cs_inferno,    paint_cs_inferno),
    "cs_mystichrome":(spec_cs_mystichrome,paint_cs_mystichrome),
    "cs_nebula":     (spec_cs_nebula,     paint_cs_nebula),
    "cs_rainbow":    (spec_cs_rainbow,   paint_cs_rainbow),
    "cs_solarflare": (spec_cs_solarflare, paint_cs_solarflare),
    "cs_subtle":     (spec_cs_subtle,    paint_cs_subtle),
    "cs_supernova":  (spec_cs_supernova,  paint_cs_supernova),
    "cs_warm":       (spec_cs_warm,      paint_cs_warm),
    "ember_glow":   (spec_ember_glow,   paint_ember_glow),
    "frost_bite":   (spec_frost_bite,    paint_subtle_flake),
    "galaxy":       (spec_galaxy,        paint_galaxy_nebula),
    "glitch":             (spec_glitch,        paint_glitch),
    "holographic_wrap":   (spec_holographic,   paint_holographic_full),
    "liquid_metal": (spec_liquid_metal,  paint_liquid_reflect),
    "mystichrome":        (spec_chameleon_pro, paint_mystichrome),
    "neon_glow":    (spec_neon_glow,     paint_neon_edge),
    "oil_slick":    (spec_oil_slick,     paint_oil_slick),
    "phantom":      (spec_phantom,      paint_phantom_fade),
    "prizm_adaptive":     (spec_prizm_adaptive,     paint_prizm_adaptive),
    "prizm_arctic":       (spec_prizm_arctic,       paint_prizm_arctic),
    "prizm_black_rainbow":(spec_prizm_black_rainbow,paint_prizm_black_rainbow),
    "prizm_duochrome":    (spec_prizm_duochrome,    paint_prizm_duochrome),
    "prizm_ember":        (spec_prizm_ember,        paint_prizm_ember),
    "prizm_holographic":  (spec_prizm_holographic,  paint_prizm_holographic),
    "prizm_iridescent":   (spec_prizm_iridescent,   paint_prizm_iridescent),
    "prizm_midnight":     (spec_prizm_midnight,     paint_prizm_midnight),
    "prizm_mystichrome":  (spec_prizm_mystichrome,  paint_prizm_mystichrome),
    "prizm_oceanic":      (spec_prizm_oceanic,      paint_prizm_oceanic),
    "prizm_phoenix":      (spec_prizm_phoenix,      paint_prizm_phoenix),
    "prizm_solar":        (spec_prizm_solar,        paint_prizm_solar),
    "prizm_venom":        (spec_prizm_venom,        paint_prizm_venom),
    "radioactive":        (spec_radioactive,   paint_radioactive),
    "rust":         (spec_rust,          paint_rust_corrosion),
    "scorched":           (spec_scorched,      paint_scorched),
    "static":             (spec_static,        paint_static),
    "thermochromic":      (spec_thermochromic, paint_thermochromic),
    "weathered_paint": (spec_weathered_paint, paint_weathered_peel),
    "worn_chrome":  (spec_worn_chrome,   paint_patina),
}


# --- 24K ARSENAL EXPANSION ---
# Import and merge the 100/100/105 expansion entries into our registries
try:
    import sys as _sys
    import shokker_24k_expansion as _exp24k
    # Get a reference to THIS module so expansion can resolve string paint_fn refs
    _this_module = _sys.modules[__name__]
    _exp24k.integrate_expansion(_this_module)
except ImportError:
    print("[24K Arsenal] Expansion module not found — running with base 55/55/50 finishes")
except Exception as e:
    print(f"[24K Arsenal] Expansion load error: {e}")

# --- COLOR MONOLITHICS EXPANSION (260+ color-changing finishes) ---
try:
    import shokker_color_monolithics as _clr_mono
    _clr_mono.integrate_color_monolithics(_sys.modules[__name__])
except ImportError:
    print("[Color Monolithics] Module not found — running without color finishes")
except Exception as e:
    print(f"[Color Monolithics] Load error: {e}")

# --- PARADIGM EXPANSION (Impossible Materials — PBR physics exploits) ---
try:
    import shokker_paradigm_expansion as _paradigm
    _paradigm.integrate_paradigm(_sys.modules[__name__])
except ImportError:
    print("[PARADIGM] Module not found — running without impossible materials")
except Exception as e:
    print(f"[PARADIGM] Load error: {e}")


# ================================================================
# GENERIC FALLBACK RENDERER — handles client-defined finishes
# ================================================================
# When a finish ID isn't in MONOLITHIC_REGISTRY, the client sends
# color data (finish_colors) and we render generically based on prefix.

def _hex_to_rgb_float(hex_str):
    """Convert '#RRGGBB' hex to (r, g, b) floats 0-1."""
    if not hex_str or len(hex_str) < 7:
        return (0.5, 0.5, 0.5)
    r = int(hex_str[1:3], 16) / 255.0
    g = int(hex_str[3:5], 16) / 255.0
    b = int(hex_str[5:7], 16) / 255.0
    return (r, g, b)

def _get_grad_direction(finish_id):
    """Determine gradient direction from finish ID suffix."""
    if finish_id.endswith('vortex'):
        return 'radial'
    elif finish_id.endswith('_diag'):
        return 'diagonal'
    elif finish_id.endswith('_h'):
        return 'horizontal'
    return 'vertical'

def _generic_grad_spec(shape, mask, seed, sm):
    """Generic gradient spec: moderate metallic, low roughness, clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(80 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(40 * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def _generic_cs_spec(shape, mask, seed, sm):
    """Generic color-shift spec: high metallic for iridescence."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(200 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(25 * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def _generic_solid_spec_fn(shape, mask, seed, sm, mat_key):
    """Generic solid spec based on material key extracted from finish ID."""
    MATS = {
        'gloss':    (5, 20, 16), 'matte':    (5, 180, 0),
        'satin':    (15, 90, 8), 'metallic': (200, 50, 16),
        'pearl':    (120, 35, 16), 'candy':  (200, 15, 16),
        'chrome':   (250, 3, 0),  'flat':    (0, 230, 0),
    }
    M, R, CC = MATS.get(mat_key, (5, 20, 16))
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = CC; spec[:,:,3] = 255
    return spec

def _apply_generic_gradient(paint, shape, mask, c1, c2, direction, seed, pm, bb, mirror=False, rotation=0):
    """Apply a 2-color gradient to paint. Supports vertical/horizontal/diagonal/radial/mirror + rotation."""
    h, w = shape
    blend = 0.85 * pm
    y, x = np.mgrid[0:h, 0:w]
    yf = y.astype(np.float32) / max(h - 1, 1)
    xf = x.astype(np.float32) / max(w - 1, 1)
    if direction == 'radial':
        cx, cy = 0.5, 0.5
        dist = np.sqrt((xf - cx)**2 + (yf - cy)**2) * 1.414
        t = np.clip(dist, 0, 1)
    else:
        # Compute base angle from direction name
        if direction == 'horizontal':
            base_angle = 90.0
        elif direction == 'diagonal':
            base_angle = 45.0
        else:  # vertical
            base_angle = 0.0
        total_angle = base_angle + float(rotation)
        rad = np.deg2rad(total_angle)
        _engine_rot_debug(f"ENGINE _apply_generic_gradient: dir={direction}, base_angle={base_angle}, rotation={rotation}, total_angle={total_angle}")
        t = np.cos(rad) * yf + np.sin(rad) * xf
        # Normalize t to 0-1 range
        t_min, t_max = t.min(), t.max()
        if t_max - t_min > 1e-6:
            t = (t - t_min) / (t_max - t_min)
        else:
            t = np.zeros_like(t)
    if mirror:
        t = np.where(t < 0.5, t * 2, (1 - t) * 2)
    r = c1[0] + (c2[0] - c1[0]) * t
    g = c1[1] + (c2[1] - c1[1]) * t
    b = c1[2] + (c2[2] - c1[2]) * t
    r += bb
    g += bb
    b += bb
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint

def _apply_generic_3color_gradient(paint, shape, mask, c1, c2, c3, direction, seed, pm, bb, rotation=0):
    """Apply a 3-color gradient (c1 -> c2 -> c3) with rotation support."""
    h, w = shape
    blend = 0.85 * pm
    y, x = np.mgrid[0:h, 0:w]
    yf = y.astype(np.float32) / max(h - 1, 1)
    xf = x.astype(np.float32) / max(w - 1, 1)
    # Compute base angle from direction name
    if direction == 'horizontal':
        base_angle = 90.0
    elif direction == 'diagonal':
        base_angle = 45.0
    else:  # vertical
        base_angle = 0.0
    total_angle = base_angle + float(rotation)
    rad = np.deg2rad(total_angle)
    t = np.cos(rad) * yf + np.sin(rad) * xf
    # Normalize t to 0-1 range
    t_min, t_max = t.min(), t.max()
    if t_max - t_min > 1e-6:
        t = (t - t_min) / (t_max - t_min)
    else:
        t = np.zeros_like(t)
    # Two-segment interpolation
    seg1 = t < 0.5
    t1 = np.clip(t * 2, 0, 1)
    t2 = np.clip((t - 0.5) * 2, 0, 1)
    r = np.where(seg1, c1[0] + (c2[0] - c1[0]) * t1, c2[0] + (c3[0] - c2[0]) * t2)
    g = np.where(seg1, c1[1] + (c2[1] - c1[1]) * t1, c2[1] + (c3[1] - c2[1]) * t2)
    b = np.where(seg1, c1[2] + (c2[2] - c1[2]) * t1, c2[2] + (c3[2] - c2[2]) * t2)
    r += bb; g += bb; b += bb
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint

def _apply_generic_colorshift(paint, shape, mask, c1, c2, seed, pm, bb):
    """Apply angle-dependent color shift between c1 and c2."""
    h, w = shape
    blend = 0.85 * pm
    y, x = np.mgrid[0:h, 0:w]
    yf = y.astype(np.float32) / max(h - 1, 1)
    xf = x.astype(np.float32) / max(w - 1, 1)
    # Angle-based shift using view-angle approximation
    angle = np.arctan2(yf - 0.5, xf - 0.5)
    shift = (np.sin(angle * 2.0 + seed * 0.1) + 1) * 0.5
    r = c1[0] * (1 - shift) + c2[0] * shift
    g = c1[1] * (1 - shift) + c2[1] * shift
    b = c1[2] * (1 - shift) + c2[2] * shift
    r += bb; g += bb; b += bb
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint

def _apply_generic_solid(paint, shape, mask, c1, seed, pm, bb):
    """Apply a flat solid color."""
    blend = 0.85 * pm
    r, g, b = c1[0] + bb, c1[1] + bb, c1[2] + bb
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint

def _engine_rot_debug(msg):
    pass  # Debug logging removed in build 29

def render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed, sm, pm, bb, rotation=0):
    """Generic fallback renderer. Returns (zone_spec, paint) or (None, paint) if can't handle."""
    _engine_rot_debug(f"ENGINE render_generic_finish: finish={finish_name}, rotation={rotation}")
    fc = zone.get("finish_colors")
    if not fc:
        return None, paint
    c1 = _hex_to_rgb_float(fc.get("c1"))
    c2 = _hex_to_rgb_float(fc.get("c2")) if fc.get("c2") else c1
    c3 = _hex_to_rgb_float(fc.get("c3")) if fc.get("c3") else None
    direction = _get_grad_direction(finish_name)

    if finish_name.startswith('gradm_'):
        # Mirror gradient
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, mirror=True, rotation=rotation)
    elif finish_name.startswith('grad3_'):
        # 3-color gradient
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        if c3:
            paint = _apply_generic_3color_gradient(paint, shape, zone_mask, c1, c2, c3, direction, seed, pm, bb, rotation=rotation)
        else:
            paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation)
    elif finish_name.startswith('ghostg_'):
        # Ghost gradient — base gradient + ghosted pattern overlay
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, 'vertical', seed, pm, bb, rotation=rotation)
        # Extract ghost pattern name from finish_colors
        ghost_pat = fc.get("ghost") if fc else None
        if ghost_pat and ghost_pat in PATTERN_REGISTRY:
            # Generate the actual pattern texture
            pat_entry = PATTERN_REGISTRY[ghost_pat]
            tex_fn = pat_entry["texture_fn"]
            pat_paint_fn = pat_entry["paint_fn"]
            try:
                tex_result = tex_fn(shape, zone_mask, seed + 9999, sm)
                if isinstance(tex_result, dict):
                    pattern_val = tex_result.get("pattern_val", np.zeros(shape, dtype=np.float32))
                else:
                    pattern_val = tex_result
                # Normalize pattern to 0-1 range
                pmin, pmax = float(pattern_val.min()), float(pattern_val.max())
                if pmax - pmin > 1e-8:
                    pattern_norm = (pattern_val - pmin) / (pmax - pmin)
                else:
                    pattern_norm = np.zeros_like(pattern_val)
                # Apply ghost pattern at subtle intensity (0.08-0.12 range)
                ghost_strength = 0.10 * pm
                for ch in range(3):
                    # Darken where pattern is strong, creating a "ghosted" emboss look
                    paint[:,:,ch] = np.clip(
                        paint[:,:,ch] - pattern_norm * ghost_strength * zone_mask,
                        0, 1
                    )
                    # Add slight brightness in pattern valleys for depth
                    paint[:,:,ch] = np.clip(
                        paint[:,:,ch] + (1.0 - pattern_norm) * ghost_strength * 0.3 * zone_mask,
                        0, 1
                    )
            except Exception as e:
                print(f"[Ghost Gradient] Pattern '{ghost_pat}' render failed: {e}")
                # Fallback to noise
                h, w = shape
                rng = np.random.RandomState(seed + 7777)
                noise = rng.randn(h, w).astype(np.float32) * 0.05
                for ch in range(3):
                    paint[:,:,ch] = np.clip(paint[:,:,ch] + noise * zone_mask, 0, 1)
        else:
            # No valid ghost pattern — use enhanced noise fallback
            h, w = shape
            rng = np.random.RandomState(seed + 7777)
            noise = rng.randn(h, w).astype(np.float32) * 0.05
            for ch in range(3):
                paint[:,:,ch] = np.clip(paint[:,:,ch] + noise * zone_mask, 0, 1)
    elif finish_name.startswith('cs_duo_'):
        # Color shift duo
        zone_spec = _generic_cs_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_colorshift(paint, shape, zone_mask, c1, c2, seed, pm, bb)
    elif finish_name.startswith('grad_'):
        # Standard 2-color gradient (new entries not in original registry)
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation)
    elif finish_name.startswith('clr_'):
        # Solid color — extract material from ID suffix
        parts = finish_name.split('_')
        mat_key = parts[-1] if len(parts) >= 3 else 'gloss'
        zone_spec = _generic_solid_spec_fn(shape, zone_mask, seed, sm, mat_key)
        paint = _apply_generic_solid(paint, shape, zone_mask, c1, seed, pm, bb)
    else:
        # Unknown prefix — try generic gradient
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb)

    return zone_spec, paint


# --- COMPOSE FUNCTIONS ---

def _resize_array(arr, target_h, target_w):
    """Resize a 2D numpy array using PIL for smooth interpolation."""
    img = Image.fromarray(((arr - arr.min()) / (arr.max() - arr.min() + 1e-8) * 255).clip(0, 255).astype(np.uint8))
    img = img.resize((target_w, target_h), Image.BILINEAR)  # BILINEAR is ~3x faster than LANCZOS, visually identical for patterns
    result = np.array(img).astype(np.float32) / 255.0
    # Restore original value range
    result = result * (arr.max() - arr.min()) + arr.min()
    return result


def _tile_array(arr, repeats_h, repeats_w, target_h, target_w):
    """Tile a 2D array repeats_h x repeats_w times, then resize to target dims.
    Used for scale < 1.0: more repetitions = smaller-looking pattern."""
    tiled = np.tile(arr, (repeats_h, repeats_w))
    if tiled.shape[0] == target_h and tiled.shape[1] == target_w:
        return tiled
    return _resize_array(tiled, target_h, target_w)


def _tile_fractional(arr, factor, target_h, target_w):
    """Tile a 2D array by a fractional factor and resize to target dims.
    Uses tile-then-crop for exact fractional coverage.
    factor=2.5 means 2.5x more repetitions (scale=0.40).
    """
    import math
    h, w = arr.shape[:2]
    reps = int(math.ceil(factor))  # Tile enough to cover
    reps = min(reps, 10)  # Cap at 10x10 to prevent memory explosions
    if reps < 2:
        reps = 2
    tiled = np.tile(arr, (reps, reps))
    # Crop to exact fractional coverage
    crop_h = min(tiled.shape[0], max(4, int(round(h * factor))))
    crop_w = min(tiled.shape[1], max(4, int(round(w * factor))))
    tiled = tiled[:crop_h, :crop_w]
    # Resize to target
    return _resize_array(tiled, target_h, target_w)


def _crop_center_array(arr, crop_frac, target_h, target_w):
    """Crop the center portion of a 2D array (crop_frac of each dim), then resize to target dims.
    Used for scale > 1.0: shows less of the pattern = bigger-looking pattern."""
    h, w = arr.shape[:2]
    ch = max(4, int(h / crop_frac))
    cw = max(4, int(w / crop_frac))
    y0 = (h - ch) // 2
    x0 = (w - cw) // 2
    cropped = arr[y0:y0+ch, x0:x0+cw]
    if cropped.shape[0] == target_h and cropped.shape[1] == target_w:
        return cropped
    return _resize_array(cropped, target_h, target_w)


def _scale_pattern_output(pv, tex, scale, shape):
    """Apply scale to pattern_val and all associated tex arrays using tiling/cropping.
    Uses precise fractional tiling for scale < 1.0.
    Returns (scaled_pv, modified_tex)."""
    h, w = shape
    if scale < 1.0:
        # Smaller pattern = MORE repetitions via fractional tiling
        factor = 1.0 / scale  # e.g., 2.5 for scale=0.40, 10.0 for scale=0.10
        pv = _tile_fractional(pv, factor, h, w)
        if "R_extra" in tex and isinstance(tex["R_extra"], np.ndarray):
            tex["R_extra"] = _tile_fractional(tex["R_extra"], factor, h, w)
        if "M_extra" in tex and isinstance(tex["M_extra"], np.ndarray):
            tex["M_extra"] = _tile_fractional(tex["M_extra"], factor, h, w)
        pat_CC = tex.get("CC")
        if isinstance(pat_CC, np.ndarray):
            tex["CC"] = _tile_fractional(pat_CC, factor, h, w)
    else:
        # Bigger pattern = crop center and expand
        pv = _crop_center_array(pv, scale, h, w)
        if "R_extra" in tex and isinstance(tex["R_extra"], np.ndarray):
            tex["R_extra"] = _crop_center_array(tex["R_extra"], scale, h, w)
        if "M_extra" in tex and isinstance(tex["M_extra"], np.ndarray):
            tex["M_extra"] = _crop_center_array(tex["M_extra"], scale, h, w)
        pat_CC = tex.get("CC")
        if isinstance(pat_CC, np.ndarray):
            tex["CC"] = _crop_center_array(pat_CC, scale, h, w)
    return pv, tex




def _rotate_array(arr, angle, fill_value=0.0):
    """Rotate a 2D numpy array by angle (degrees) around center, keeping same dims.
    Uses PIL rotation with BILINEAR interpolation. Fill value used for exposed corners."""
    if angle == 0 or angle == 360:
        return arr
    arr_min, arr_max = float(arr.min()), float(arr.max())
    val_range = arr_max - arr_min
    if val_range < 1e-8:
        return arr  # Uniform array, rotation does nothing
    # Normalize to 0-255 for PIL
    norm = ((arr - arr_min) / val_range * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(norm)
    # PIL rotate: positive = counter-clockwise (standard math convention)
    fill_norm = int(((fill_value - arr_min) / val_range * 255))
    fill_norm = max(0, min(255, fill_norm))
    rotated = img.rotate(angle, resample=Image.BILINEAR, expand=False, fillcolor=fill_norm)
    result = np.array(rotated).astype(np.float32) / 255.0 * val_range + arr_min
    return result


def _rotate_pattern_tex(tex, angle, shape):
    """Rotate all spatial arrays in a texture output dict by the given angle (degrees).
    Works with pattern_val, R_extra, M_extra, and ndarray CC fields."""
    if angle == 0 or angle == 360:
        return tex
    # Rotate the primary pattern value
    tex["pattern_val"] = _rotate_array(tex["pattern_val"], angle, fill_value=0.0)
    # Rotate extra noise fields if present
    if "R_extra" in tex and isinstance(tex["R_extra"], np.ndarray):
        tex["R_extra"] = _rotate_array(tex["R_extra"], angle, fill_value=0.0)
    if "M_extra" in tex and isinstance(tex["M_extra"], np.ndarray):
        tex["M_extra"] = _rotate_array(tex["M_extra"], angle, fill_value=0.0)
    # Rotate variable CC if it's a spatial array
    if isinstance(tex.get("CC"), np.ndarray):
        tex["CC"] = _rotate_array(tex["CC"], angle, fill_value=0.0)
    return tex


def _rotate_single_array(arr, angle, shape):
    """Rotate a single 2D array by angle degrees. Used for independent channel patterns."""
    if angle == 0 or angle == 360:
        return arr
    rotated = _rotate_array(arr, angle, fill_value=0.0)
    # Ensure output shape matches target (rotation may shift slightly)
    if rotated.shape[0] != shape[0] or rotated.shape[1] != shape[1]:
        rotated = _resize_array(rotated, shape[0], shape[1])
    return rotated


def compose_finish(base_id, pattern_id, shape, mask, seed, sm, scale=1.0, spec_mult=1.0, rotation=0, base_scale=1.0, cc_quality=None, blend_base=None, blend_dir="horizontal", blend_amount=0.5, paint_color=None):
    """Compose a base material + pattern texture into a final spec map.

    v4.0 MODULATION approach: Base provides flat M/R/CC values (with optional noise).
    Pattern provides a spatial shape (pattern_val, 0-1) and modulation ranges.
    The pattern creates variation WITHIN the base's own M/R values:

        final_R = base_R + pattern_val * R_range * sm
        final_M = base_M + pattern_val * M_range * sm

    This way "Chrome + Carbon Fiber" gives a chrome surface with visible weave texture
    in the roughness channel, while "Matte + Carbon Fiber" gives a matte surface with
    the same weave — the base determines the character, the pattern adds texture.

    When pattern is "none", just the base material with its own noise is applied.

    scale: Pattern size multiplier (default 1.0). >1 = bigger pattern, <1 = smaller.
    rotation: Pattern rotation in degrees (0-359).
    base_scale: Base material tiling multiplier (default 1.0).
    cc_quality: Clearcoat quality override (0.0-1.0). None=use base default.
                1.0=perfect clearcoat (CC=16), 0.0=fully degraded (CC=255).
                Values between create intermediate clearcoat states.
    blend_base: Second base material ID for gradient spec ramps. None=no blend.
    blend_dir: Blend direction: "horizontal", "vertical", "radial", "diagonal".
    blend_amount: Blend curve power (0.0-1.0). 0.5=linear.
    paint_color: RGB tuple (0-1 float) of underlying paint for paint-reactive spec.
    """
    base = BASE_REGISTRY[base_id]
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    base_M = float(base["M"])
    base_R = float(base["R"])
    base_CC = int(base["CC"]) if base.get("CC") is not None else 16

    # --- BASE SCALE: determine generation shape for base noise ---
    if base_scale != 1.0 and base_scale > 0:
        MAX_BASE_DIM = 4096
        base_h = min(MAX_BASE_DIM, max(4, int(shape[0] / base_scale)))
        base_w = min(MAX_BASE_DIM, max(4, int(shape[1] / base_scale)))
        base_shape = (base_h, base_w)
    else:
        base_shape = shape

    # --- Base material with its own noise/grain ---
    if base.get("brush_grain"):
        rng = np.random.RandomState(seed)
        # Horizontal grain: columns vary, rows are constant
        noise = np.tile(rng.randn(1, base_shape[1]) * 0.5, (base_shape[0], 1))
        noise += rng.randn(base_shape[0], base_shape[1]) * 0.2
        M_arr = base_M + noise * base.get("noise_M", 0) * sm
        R_arr = base_R + noise * base.get("noise_R", 0) * sm
        # CC noise: spatial clearcoat variation (noise_CC in base = variation magnitude)
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * sm
        else:
            CC_arr = None
    elif base.get("perlin"):
        # --- MULTI-OCTAVE PERLIN NOISE (v4.0) ---
        # Spatially coherent noise — nearby pixels are correlated for organic surfaces
        p_oct = base.get("perlin_octaves", 4)
        p_pers = base.get("perlin_persistence", 0.5)
        p_lac = base.get("perlin_lacunarity", 2.0)
        noise = perlin_multi_octave(base_shape, octaves=p_oct, persistence=p_pers, lacunarity=p_lac, seed=seed + 200)
        M_arr = base_M + noise * base.get("noise_M", 0) * sm
        R_arr = base_R + noise * base.get("noise_R", 0) * sm
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * sm
        else:
            CC_arr = None
    elif "noise_scales" in base:
        noise = multi_scale_noise(base_shape, base["noise_scales"], base["noise_weights"], seed + 100)
        M_arr = base_M + noise * base.get("noise_M", 0) * sm
        R_arr = base_R + noise * base.get("noise_R", 0) * sm
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * sm
        else:
            CC_arr = None
    else:
        M_arr = np.full(base_shape, base_M, dtype=np.float32)
        R_arr = np.full(base_shape, base_R, dtype=np.float32)
        CC_arr = None

    # --- BASE SCALE: resize base noise back to original shape ---
    if base_scale != 1.0 and base_scale > 0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1]):
        M_arr = _resize_array(M_arr, shape[0], shape[1])
        R_arr = _resize_array(R_arr, shape[0], shape[1])
        if CC_arr is not None:
            CC_arr = _resize_array(CC_arr, shape[0], shape[1])

    # --- CLEARCOAT QUALITY OVERRIDE (v4.0) ---
    # cc_quality: 1.0=perfect (CC=16), 0.0=fully degraded (CC=255)
    # Maps linearly: CC_value = 16 + (1 - cc_quality) * 239
    if cc_quality is not None and base_CC > 0:
        # Only apply to clearcoated surfaces (base_CC > 0)
        cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        if CC_arr is not None:
            # Shift existing noise to center around the override value
            CC_arr = CC_arr - float(base_CC) + cc_value
        else:
            CC_arr = np.full(shape, cc_value, dtype=np.float32)

    # --- GRADIENT SPEC RAMP (v4.0 — SHOKK Shift) ---
    # Blend between primary base and a second base across the zone
    if blend_base and blend_base in BASE_REGISTRY and blend_base != base_id:
        base2 = BASE_REGISTRY[blend_base]
        base2_M = float(base2["M"])
        base2_R = float(base2["R"])
        base2_CC = int(base2["CC"]) if base2.get("CC") is not None else 16
        h, w = shape
        # Build directional gradient mask (0.0 = primary base, 1.0 = blend base)
        if blend_dir == "vertical":
            grad = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
        elif blend_dir == "radial":
            cy, cx = h / 2.0, w / 2.0
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            grad = np.sqrt((yy - cy)**2 + (xx - cx)**2) / (np.sqrt(cy**2 + cx**2) + 1e-8)
            grad = np.clip(grad, 0, 1)
        elif blend_dir == "diagonal":
            grad = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis] * 0.5 + \
                   np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :] * 0.5
        else:  # horizontal (default)
            grad = np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :]
        # Apply blend curve (blend_amount controls sharpness: <0.5=sharper, >0.5=softer)
        ba = max(0.1, min(3.0, blend_amount * 2.0 + 0.1))
        grad = np.power(grad, ba)
        # Lerp M and R arrays toward blend base values
        M_arr = M_arr * (1.0 - grad) + base2_M * grad
        R_arr = R_arr * (1.0 - grad) + base2_R * grad
        # Lerp CC
        if CC_arr is not None:
            CC_arr = CC_arr * (1.0 - grad) + float(base2_CC) * grad
        elif base_CC != base2_CC:
            CC_arr = float(base_CC) * (1.0 - grad) + float(base2_CC) * grad

    # --- PAINT-REACTIVE SPEC (v4.0) ---
    # Automatically adjust M/R/CC based on underlying paint color
    if paint_color is not None and len(paint_color) >= 3:
        pr, pg, pb = float(paint_color[0]), float(paint_color[1]), float(paint_color[2])
        luminance = 0.299 * pr + 0.587 * pg + 0.114 * pb
        # Dark colors: +5-15 roughness (real dark paint shows more surface texture)
        # Light colors: -3-8 roughness (light paint looks smoother under clearcoat)
        dark_boost = (1.0 - luminance) * 12.0 * sm
        R_arr = R_arr + dark_boost
        # High-saturation colors: slight metallic boost (+5-10) for richer look
        max_c = max(pr, pg, pb)
        min_c = min(pr, pg, pb)
        saturation = (max_c - min_c) / (max_c + 1e-8)
        if saturation > 0.3:
            sat_boost = (saturation - 0.3) * 15.0 * sm
            M_arr = M_arr + sat_boost

    # --- Apply pattern modulation on top of base ---
    # !! ARCHITECTURE GUARD — DO NOT MODIFY SCALE/ROTATION LOGIC BELOW !!
    # Scale works by generating texture at modified resolution, then resizing.
    # See ARCHITECTURE.md "Scale Mechanism" section.
    # If patterns look wrong, the fix is in the TEXTURE FUNCTION, not here.
    final_CC = CC_arr if CC_arr is not None else base_CC  # scalar or array
    has_pattern = (pattern_id and pattern_id != "none" and pattern_id in PATTERN_REGISTRY)

    if has_pattern:
        pattern = PATTERN_REGISTRY[pattern_id]
        tex_fn = pattern["texture_fn"]
        if tex_fn is not None:
            # --- Generate texture at NATIVE resolution (always) ---
            tex = tex_fn(shape, mask, seed, sm)
            pv = tex["pattern_val"]     # 0-1 spatial shape
            R_range = tex["R_range"]    # how much R varies (can be negative)
            M_range = tex["M_range"]    # how much M varies (can be negative)

            # --- SCALE: tile (scale<1) or crop-expand (scale>1) the finished pattern ---
            if scale != 1.0 and scale > 0:
                pv, tex = _scale_pattern_output(pv, tex, scale, shape)

            # --- ROTATION: rotate pattern texture by specified angle ---
            rot_angle = float(rotation) % 360
            if rot_angle != 0:
                tex["pattern_val"] = pv  # Put pv back in tex dict for rotation
                tex = _rotate_pattern_tex(tex, rot_angle, shape)
                pv = tex["pattern_val"]  # Pull rotated pv back out

            # --- SHOKK Phase: Independent channel patterns (v4.0) ---
            # If pattern provides per-channel arrays, use them instead of unified pv
            M_pv = tex.get("M_pattern", pv)   # independent M spatial shape (or fallback to pv)
            R_pv = tex.get("R_pattern", pv)   # independent R spatial shape (or fallback to pv)
            CC_pv = tex.get("CC_pattern", None)  # independent CC spatial shape (None = no CC modulation)

            # Scale per-channel patterns if they differ from pv
            if scale != 1.0 and scale > 0:
                if M_pv is not pv:
                    if scale < 1.0:
                        factor = 1.0 / scale
                        M_pv = _tile_fractional(M_pv, factor, shape[0], shape[1])
                    else:
                        M_pv = _crop_center_array(M_pv, scale, shape[0], shape[1])
                if R_pv is not pv:
                    if scale < 1.0:
                        factor = 1.0 / scale
                        R_pv = _tile_fractional(R_pv, factor, shape[0], shape[1])
                    else:
                        R_pv = _crop_center_array(R_pv, scale, shape[0], shape[1])
                if CC_pv is not None:
                    if scale < 1.0:
                        factor = 1.0 / scale
                        CC_pv = _tile_fractional(CC_pv, factor, shape[0], shape[1])
                    else:
                        CC_pv = _crop_center_array(CC_pv, scale, shape[0], shape[1])

            # Rotate per-channel patterns if rotation was applied
            if rot_angle != 0:
                if M_pv is not pv:
                    M_pv = _rotate_single_array(M_pv, rot_angle, shape)
                if R_pv is not pv:
                    R_pv = _rotate_single_array(R_pv, rot_angle, shape)
                if CC_pv is not None:
                    CC_pv = _rotate_single_array(CC_pv, rot_angle, shape)

            # Modulate base values with pattern shape (spec_mult scales spec punch independently)
            M_arr = M_arr + M_pv * M_range * sm * spec_mult
            R_arr = R_arr + R_pv * R_range * sm * spec_mult

            # CC channel modulation via independent CC pattern
            CC_range = tex.get("CC_range", 0)
            if CC_pv is not None and CC_range != 0:
                if CC_arr is not None:
                    CC_arr = CC_arr + CC_pv * CC_range * sm * spec_mult
                elif base_CC > 0:
                    CC_arr = np.full(shape, float(base_CC), dtype=np.float32) + CC_pv * CC_range * sm * spec_mult

            # Handle extra noise components (some patterns have independent noise)
            if "R_extra" in tex:
                R_arr = R_arr + tex["R_extra"] * sm * spec_mult
            if "M_extra" in tex:
                M_arr = M_arr + tex["M_extra"] * sm * spec_mult

            # CC: use pattern's CC (may be array for variable-CC patterns)
            pat_CC = tex.get("CC")
            if pat_CC is None:
                pass  # Keep base CC (expansion patterns default)
            elif isinstance(pat_CC, np.ndarray):
                # Variable CC (battle_worn, acid_wash) — use pattern CC directly
                final_CC = pat_CC
            else:
                # Fixed CC — use pattern CC value (overrides base)
                final_CC = int(pat_CC)

    # --- Apply zone mask: inside=our values, outside=neutral (M=5, R=100) ---
    M_final = M_arr * mask + 5.0 * (1 - mask)
    R_final = R_arr * mask + 100.0 * (1 - mask)

    spec[:,:,0] = np.clip(M_final, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_final, 0, 255).astype(np.uint8)
    if isinstance(final_CC, np.ndarray):
        spec[:,:,2] = np.clip(final_CC * mask, 0, 255).astype(np.uint8)  # 16=max shine, 17-255=progressively duller
    else:
        spec[:,:,2] = np.where(mask > 0.5, final_CC, 0).astype(np.uint8)
    spec[:,:,3] = 255
    return spec


def compose_finish_stacked(base_id, all_patterns, shape, mask, seed, sm, spec_mult=1.0, base_scale=1.0, cc_quality=None, blend_base=None, blend_dir="horizontal", blend_amount=0.5, paint_color=None):
    """Compose a base material + MULTIPLE stacked patterns into a final spec map.

    all_patterns: list of {"id": str, "opacity": float (0-1), "scale": float, "rotation": float (0-359)}

    Blending: Weighted additive — each pattern's contribution is scaled by its opacity.
    v4.0 params: cc_quality, blend_base, blend_dir, blend_amount, paint_color
    (see compose_finish for detailed docs on each).

    base_scale: Base material tiling multiplier (default 1.0).
    """
    base = BASE_REGISTRY[base_id]
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    base_M = float(base["M"])
    base_R = float(base["R"])
    base_CC = int(base["CC"]) if base.get("CC") is not None else 16

    # --- BASE SCALE: determine generation shape for base noise ---
    if base_scale != 1.0 and base_scale > 0:
        MAX_BASE_DIM = 4096
        base_h = min(MAX_BASE_DIM, max(4, int(shape[0] / base_scale)))
        base_w = min(MAX_BASE_DIM, max(4, int(shape[1] / base_scale)))
        base_shape = (base_h, base_w)
    else:
        base_shape = shape

    # --- Base material with its own noise/grain ---
    CC_arr = None
    if base.get("brush_grain"):
        rng = np.random.RandomState(seed)
        noise = np.tile(rng.randn(1, base_shape[1]) * 0.5, (base_shape[0], 1))
        noise += rng.randn(base_shape[0], base_shape[1]) * 0.2
        M_arr = base_M + noise * base.get("noise_M", 0) * sm
        R_arr = base_R + noise * base.get("noise_R", 0) * sm
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * sm
    elif base.get("perlin"):
        # --- MULTI-OCTAVE PERLIN NOISE (v4.0) ---
        p_oct = base.get("perlin_octaves", 4)
        p_pers = base.get("perlin_persistence", 0.5)
        p_lac = base.get("perlin_lacunarity", 2.0)
        noise = perlin_multi_octave(base_shape, octaves=p_oct, persistence=p_pers, lacunarity=p_lac, seed=seed + 200)
        M_arr = base_M + noise * base.get("noise_M", 0) * sm
        R_arr = base_R + noise * base.get("noise_R", 0) * sm
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * sm
    elif "noise_scales" in base:
        noise = multi_scale_noise(base_shape, base["noise_scales"], base["noise_weights"], seed + 100)
        M_arr = base_M + noise * base.get("noise_M", 0) * sm
        R_arr = base_R + noise * base.get("noise_R", 0) * sm
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * sm
    else:
        M_arr = np.full(base_shape, base_M, dtype=np.float32)
        R_arr = np.full(base_shape, base_R, dtype=np.float32)

    # --- BASE SCALE: resize base noise back to original shape ---
    if base_scale != 1.0 and base_scale > 0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1]):
        M_arr = _resize_array(M_arr, shape[0], shape[1])
        R_arr = _resize_array(R_arr, shape[0], shape[1])
        if CC_arr is not None:
            CC_arr = _resize_array(CC_arr, shape[0], shape[1])

    # --- CLEARCOAT QUALITY OVERRIDE (v4.0) ---
    if cc_quality is not None and base_CC > 0:
        cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        if CC_arr is not None:
            CC_arr = CC_arr - float(base_CC) + cc_value
        else:
            CC_arr = np.full(shape, cc_value, dtype=np.float32)

    # --- GRADIENT SPEC RAMPS / SHOKK Shift (v4.0) ---
    h, w = shape
    if blend_base and blend_base in BASE_REGISTRY and blend_base != base_id:
        base2 = BASE_REGISTRY[blend_base]
        base2_M = float(base2["M"])
        base2_R = float(base2["R"])
        base2_CC = int(base2["CC"]) if base2.get("CC") is not None else 16
        if blend_dir == "vertical":
            grad = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
        elif blend_dir == "radial":
            cy, cx = h / 2.0, w / 2.0
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
            grad = dist / (max(cy, cx) + 1e-8)
            grad = np.clip(grad, 0, 1)
        elif blend_dir == "diagonal":
            grad = (np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis] + np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :]) / 2.0
        else:
            grad = np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, w, dtype=np.float32)[np.newaxis, :]
        ba = max(0.1, min(3.0, blend_amount * 2.0 + 0.1))
        grad = np.power(grad, ba)
        M_arr = M_arr * (1.0 - grad) + base2_M * grad
        R_arr = R_arr * (1.0 - grad) + base2_R * grad
        if CC_arr is not None:
            CC_arr = CC_arr * (1.0 - grad) + float(base2_CC) * grad
        elif base_CC != base2_CC:
            CC_arr = float(base_CC) * (1.0 - grad) + float(base2_CC) * grad

    # --- PAINT-REACTIVE SPEC (v4.0) ---
    if paint_color is not None and len(paint_color) >= 3:
        pr, pg, pb = float(paint_color[0]), float(paint_color[1]), float(paint_color[2])
        luminance = 0.299 * pr + 0.587 * pg + 0.114 * pb
        dark_boost = (1.0 - luminance) * 12.0 * sm
        R_arr = R_arr + dark_boost
        max_c = max(pr, pg, pb)
        min_c = min(pr, pg, pb)
        saturation = (max_c - min_c) / (max_c + 1e-8)
        if saturation > 0.3:
            sat_boost = (saturation - 0.3) * 15.0 * sm
            M_arr = M_arr + sat_boost

    # --- Stack patterns: weighted additive blend ---
    # Start CC from base (may already be array from CC noise/quality/gradient)
    if CC_arr is not None:
        final_CC = CC_arr.copy()
    else:
        final_CC = np.full(shape, float(base_CC), dtype=np.float32)

    for layer_idx, layer in enumerate(all_patterns):
        pat_id = layer["id"]
        opacity = float(layer.get("opacity", 1.0))
        scale = float(layer.get("scale", 1.0))

        if pat_id not in PATTERN_REGISTRY or opacity <= 0:
            continue

        pattern = PATTERN_REGISTRY[pat_id]
        tex_fn = pattern["texture_fn"]
        if tex_fn is None:
            continue

        layer_seed = seed + layer_idx * 7

        # --- Generate texture at NATIVE resolution (always) ---
        tex = tex_fn(shape, mask, layer_seed, sm)
        pv = tex["pattern_val"]
        R_range = tex["R_range"]
        M_range = tex["M_range"]

        # --- SCALE: tile (scale<1) or crop-expand (scale>1) the finished pattern ---
        if scale != 1.0 and scale > 0:
            pv, tex = _scale_pattern_output(pv, tex, scale, shape)

        # --- ROTATION: rotate pattern texture by specified angle ---
        layer_rotation = float(layer.get("rotation", 0)) % 360
        if layer_rotation != 0:
            tex["pattern_val"] = pv
            tex = _rotate_pattern_tex(tex, layer_rotation, shape)
            pv = tex["pattern_val"]

        # --- SHOKK Phase: Independent channel patterns (v4.0) ---
        M_pv = tex.get("M_pattern", pv)
        R_pv = tex.get("R_pattern", pv)
        CC_pv = tex.get("CC_pattern", None)

        # Scale per-channel patterns if they differ from pv
        if scale != 1.0 and scale > 0:
            if M_pv is not pv:
                if scale < 1.0:
                    factor = 1.0 / scale
                    M_pv = _tile_fractional(M_pv, factor, shape[0], shape[1])
                else:
                    M_pv = _crop_center_array(M_pv, scale, shape[0], shape[1])
            if R_pv is not pv:
                if scale < 1.0:
                    factor = 1.0 / scale
                    R_pv = _tile_fractional(R_pv, factor, shape[0], shape[1])
                else:
                    R_pv = _crop_center_array(R_pv, scale, shape[0], shape[1])
            if CC_pv is not None:
                if scale < 1.0:
                    factor = 1.0 / scale
                    CC_pv = _tile_fractional(CC_pv, factor, shape[0], shape[1])
                else:
                    CC_pv = _crop_center_array(CC_pv, scale, shape[0], shape[1])

        # Rotate per-channel patterns if rotation was applied
        if layer_rotation != 0:
            if M_pv is not pv:
                M_pv = _rotate_single_array(M_pv, layer_rotation, shape)
            if R_pv is not pv:
                R_pv = _rotate_single_array(R_pv, layer_rotation, shape)
            if CC_pv is not None:
                CC_pv = _rotate_single_array(CC_pv, layer_rotation, shape)

        # Weighted additive modulation (spec_mult scales spec punch independently)
        M_arr = M_arr + M_pv * M_range * sm * opacity * spec_mult
        R_arr = R_arr + R_pv * R_range * sm * opacity * spec_mult

        # CC channel modulation via independent CC pattern
        CC_range = tex.get("CC_range", 0)
        if CC_pv is not None and CC_range != 0:
            final_CC = final_CC + CC_pv * CC_range * sm * opacity * spec_mult

        # Handle extra noise components, scaled by opacity and spec_mult
        if "R_extra" in tex:
            R_arr = R_arr + tex["R_extra"] * sm * opacity * spec_mult
        if "M_extra" in tex:
            M_arr = M_arr + tex["M_extra"] * sm * opacity * spec_mult

        # CC: weighted blend toward this layer's CC (None = keep base)
        pat_CC = tex.get("CC")
        if pat_CC is not None:
            if isinstance(pat_CC, np.ndarray):
                final_CC = final_CC * (1.0 - opacity) + pat_CC * opacity
            else:
                final_CC = final_CC * (1.0 - opacity) + float(pat_CC) * opacity

    # --- Apply zone mask: inside=our values, outside=neutral (M=5, R=100) ---
    M_final = M_arr * mask + 5.0 * (1 - mask)
    R_final = R_arr * mask + 100.0 * (1 - mask)

    spec[:,:,0] = np.clip(M_final, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_final, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(final_CC * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec


def compose_paint_mod(base_id, pattern_id, paint, shape, mask, seed, pm, bb, scale=1.0, rotation=0):
    """Apply base paint modifier then pattern paint modifier WITH spatial texture blending.

    IMPORTANT: Uses a hard mask threshold (0.5) to prevent soft-edge bleeding.
    Pixels with mask < 0.5 are NOT modified — this matches the spec map threshold.

    When pattern is "none", base runs at FULL strength (1.0x).
    When a pattern IS applied, both run at 0.7x to prevent double-stacking.

    SPATIAL BLENDING (v4.1): When a pattern has a texture_fn, we generate the
    pattern_val and use it to spatially blend the paint modification. This makes
    pattern paint effects follow the ACTUAL texture shape instead of random noise.
    Without this, patterns are invisible on color-changing bases because the
    random-noise paint darkening gets lost in the dramatic color shift.
    """
    # Hard threshold the mask to prevent soft-edge bleed into neighboring zones
    hard_mask = np.where(mask > 0.5, mask, 0.0).astype(np.float32)

    base = BASE_REGISTRY[base_id]
    base_paint_fn = base.get("paint_fn", paint_none)
    has_pattern = (pattern_id and pattern_id != "none" and pattern_id in PATTERN_REGISTRY)

    if base_paint_fn is not paint_none:
        if has_pattern:
            # Reduce base paint effect when pattern also has a paint effect
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm * 0.7, bb * 0.7)
        else:
            # No pattern — base runs at full strength
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm, bb)

    if has_pattern:
        pattern = PATTERN_REGISTRY[pattern_id]
        pat_paint_fn = pattern.get("paint_fn", paint_none)
        if pat_paint_fn is not paint_none:
            # Save paint BEFORE pattern modification for spatial blending
            paint_before_pattern = paint.copy()

            # Pattern paint boost: most pattern paint_fns have tiny multipliers (0.02-0.08)
            # that produce nearly invisible changes. Boosting pm/bb here makes ALL patterns
            # produce visible paint-layer effects without editing 50+ individual functions.
            # !! ARCHITECTURE GUARD — If patterns are too subtle, increase these multipliers.
            # !! If patterns are overpowering, decrease them. Do NOT edit individual paint_fns.
            _PAT_PAINT_BOOST = 3.5  # Global pattern paint visibility multiplier
            if base_paint_fn is not paint_none:
                paint = pat_paint_fn(paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST * 0.7, bb * _PAT_PAINT_BOOST * 0.7)
            else:
                paint = pat_paint_fn(paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST, bb * _PAT_PAINT_BOOST)

            # --- SPATIAL BLEND: use pattern_val to make paint follow texture shape ---
            tex_fn = pattern.get("texture_fn")
            if tex_fn is not None:
                try:
                    # Generate texture at NATIVE resolution, apply scale via tiling/cropping
                    tex = tex_fn(shape, mask, seed, 1.0)
                    pv = tex["pattern_val"] if isinstance(tex, dict) else tex
                    # Scale via tiling/cropping
                    if scale != 1.0 and scale > 0:
                        if isinstance(tex, dict):
                            pv, tex = _scale_pattern_output(pv, tex, scale, shape)
                        else:
                            if scale < 1.0:
                                factor = 1.0 / scale
                                pv = _tile_fractional(pv, factor, shape[0], shape[1])
                            else:
                                pv = _crop_center_array(pv, scale, shape[0], shape[1])
                    # Apply rotation if needed
                    rot_angle = float(rotation) % 360
                    if rot_angle != 0:
                        pv = _rotate_single_array(pv, rot_angle, shape)
                    # Normalize to 0-1
                    pv_min, pv_max = float(pv.min()), float(pv.max())
                    if pv_max - pv_min > 1e-8:
                        pv = (pv - pv_min) / (pv_max - pv_min)
                    else:
                        pv = np.ones_like(pv) * 0.5
                    # Spatial blend: WHERE pattern features are (high pv), keep paint mod.
                    # WHERE pattern is absent (low pv), revert to pre-pattern paint.
                    # This makes patterns visible even on color-changing bases.
                    pv_3d = pv[:, :, np.newaxis]
                    paint = paint_before_pattern * (1.0 - pv_3d) + paint * pv_3d
                except Exception:
                    pass  # If texture gen fails, keep the uniform paint mod (original behavior)
    return paint


def compose_paint_mod_stacked(base_id, all_patterns, paint, shape, mask, seed, pm, bb):
    """Apply base paint modifier then MULTIPLE stacked pattern paint modifiers.

    Each pattern's paint_fn runs with attenuated strength based on its opacity
    and the total number of active paint functions (prevents over-stacking).
    Uses spatial blending via pattern_val so paint follows actual texture shape.
    """
    hard_mask = np.where(mask > 0.5, mask, 0.0).astype(np.float32)

    base = BASE_REGISTRY[base_id]
    base_paint_fn = base.get("paint_fn", paint_none)
    has_any_pattern = len(all_patterns) > 0

    # Count how many pattern layers have a non-trivial paint_fn
    active_paint_fns = 0
    for layer in all_patterns:
        pat_id = layer["id"]
        if pat_id in PATTERN_REGISTRY:
            pfn = PATTERN_REGISTRY[pat_id].get("paint_fn", paint_none)
            if pfn is not paint_none:
                active_paint_fns += 1

    # Base paint: reduce if any patterns also have paint effects
    if base_paint_fn is not paint_none:
        if has_any_pattern and active_paint_fns > 0:
            atten = 0.6 / max(1, active_paint_fns)
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm * atten, bb * atten)
        else:
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm, bb)

    # Each pattern paint: opacity-weighted, attenuated by count
    # Pattern paint boost: same 3.5x global boost as compose_paint_mod (see ARCHITECTURE GUARD there)
    _PAT_PAINT_BOOST = 3.5
    for layer_idx, layer in enumerate(all_patterns):
        pat_id = layer["id"]
        opacity = float(layer.get("opacity", 1.0))
        scale = float(layer.get("scale", 1.0))
        rotation = float(layer.get("rotation", 0))
        if pat_id not in PATTERN_REGISTRY or opacity <= 0:
            continue
        pattern = PATTERN_REGISTRY[pat_id]
        pat_paint_fn = pattern.get("paint_fn", paint_none)
        if pat_paint_fn is not paint_none:
            # Attenuate: opacity * (0.6 / num_active) to prevent paint destruction
            atten = opacity * 0.6 / max(1, active_paint_fns)
            layer_seed = seed + layer_idx * 7
            paint_before_layer = paint.copy()
            paint = pat_paint_fn(paint, shape, hard_mask, layer_seed, pm * atten * _PAT_PAINT_BOOST, bb * atten * _PAT_PAINT_BOOST)

            # --- SPATIAL BLEND: use pattern_val to make paint follow texture shape ---
            tex_fn = pattern.get("texture_fn")
            if tex_fn is not None:
                try:
                    tex = tex_fn(shape, mask, layer_seed, 1.0)
                    pv = tex["pattern_val"] if isinstance(tex, dict) else tex
                    # Scale via tiling/cropping
                    if scale != 1.0 and scale > 0:
                        if isinstance(tex, dict):
                            pv, tex = _scale_pattern_output(pv, tex, scale, shape)
                        else:
                            if scale < 1.0:
                                factor = 1.0 / scale
                                pv = _tile_fractional(pv, factor, shape[0], shape[1])
                            else:
                                pv = _crop_center_array(pv, scale, shape[0], shape[1])
                    # Apply rotation if needed
                    rot_angle = rotation % 360
                    if rot_angle != 0:
                        pv = _rotate_single_array(pv, rot_angle, shape)
                    # Normalize to 0-1
                    pv_min, pv_max = float(pv.min()), float(pv.max())
                    if pv_max - pv_min > 1e-8:
                        pv = (pv - pv_min) / (pv_max - pv_min)
                    else:
                        pv = np.ones_like(pv) * 0.5
                    pv_3d = pv[:, :, np.newaxis]
                    paint = paint_before_layer * (1.0 - pv_3d) + paint * pv_3d
                except Exception:
                    pass  # Fallback: keep uniform paint mod

    return paint


def overlay_pattern_on_spec(spec, pattern_id, shape, mask, seed, sm, scale=1.0, opacity=1.0, spec_mult=1.0, rotation=0):
    """Overlay a pattern texture ON TOP of an existing spec map.

    Used to add patterns over monolithic finishes. The monolithic generates
    its own complete spec, then this function modulates M/R/CC with the
    pattern texture — same math as compose_finish, but starting from an
    arbitrary spec map instead of a flat base.

    opacity: 0-1, how much the pattern affects the monolithic's values.
             1.0 = full pattern modulation, 0.5 = half-strength.
    """
    if not pattern_id or pattern_id == "none" or pattern_id not in PATTERN_REGISTRY:
        return spec  # Nothing to overlay

    pattern = PATTERN_REGISTRY[pattern_id]
    tex_fn = pattern["texture_fn"]
    if tex_fn is None:
        return spec

    # Generate pattern texture at NATIVE resolution, apply scale via tiling/cropping
    tex = tex_fn(shape, mask, seed, sm)
    pv = tex["pattern_val"]
    R_range = tex["R_range"]
    M_range = tex["M_range"]

    # Scale via tiling/cropping
    if scale != 1.0 and scale > 0:
        pv, tex = _scale_pattern_output(pv, tex, scale, shape)

    # Rotate pattern if requested
    rot_angle = float(rotation) % 360
    if rot_angle != 0:
        pv = _rotate_array(pv, rot_angle, fill_value=0.0)

    # Read existing spec values as float
    M_arr = spec[:, :, 0].astype(np.float32)
    R_arr = spec[:, :, 1].astype(np.float32)

    # Modulate with pattern (same math as compose_finish, spec_mult scales spec punch)
    M_arr = M_arr + pv * M_range * sm * opacity * spec_mult
    R_arr = R_arr + pv * R_range * sm * opacity * spec_mult

    # Write back with mask
    spec[:, :, 0] = np.clip(M_arr * mask + spec[:, :, 0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_arr * mask + spec[:, :, 1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)

    return spec


def overlay_pattern_paint(paint, pattern_id, shape, mask, seed, pm, bb, scale=1.0, opacity=1.0, rotation=0):
    """Overlay a pattern's paint modifier ON TOP of a monolithic's paint output.

    Applies the pattern's paint_fn (if any) with attenuated strength.
    Uses spatial blending via pattern_val so paint follows actual texture shape.
    """
    if not pattern_id or pattern_id == "none" or pattern_id not in PATTERN_REGISTRY:
        return paint
    pattern = PATTERN_REGISTRY[pattern_id]
    pat_paint_fn = pattern.get("paint_fn", paint_none)
    if pat_paint_fn is paint_none:
        return paint
    hard_mask = np.where(mask > 0.5, mask, 0.0).astype(np.float32)
    # Save paint before pattern modification for spatial blending
    paint_before = paint.copy()
    # Run pattern paint — boosted for visibility (pattern paint_fns have tiny multipliers)
    # !! ARCHITECTURE GUARD — Same _PAT_PAINT_BOOST as compose_paint_mod. Keep in sync.
    _PAT_PAINT_BOOST = 3.5
    paint = pat_paint_fn(paint, shape, hard_mask, seed, pm * 0.5 * opacity * _PAT_PAINT_BOOST, bb * 0.5 * opacity * _PAT_PAINT_BOOST)
    # --- SPATIAL BLEND: use pattern_val to make paint follow texture shape ---
    tex_fn = pattern.get("texture_fn")
    if tex_fn is not None:
        try:
            # Generate texture at NATIVE resolution, apply scale via tiling/cropping
            tex = tex_fn(shape, mask, seed, 1.0)
            pv = tex["pattern_val"] if isinstance(tex, dict) else tex
            # Scale via tiling/cropping
            if scale != 1.0 and scale > 0:
                if isinstance(tex, dict):
                    pv, tex = _scale_pattern_output(pv, tex, scale, shape)
                else:
                    if scale < 1.0:
                        factor = 1.0 / scale
                        pv = _tile_fractional(pv, factor, shape[0], shape[1])
                    else:
                        pv = _crop_center_array(pv, scale, shape[0], shape[1])
            rot_angle = float(rotation) % 360
            if rot_angle != 0:
                pv = _rotate_single_array(pv, rot_angle, shape)
            pv_min, pv_max = float(pv.min()), float(pv.max())
            if pv_max - pv_min > 1e-8:
                pv = (pv - pv_min) / (pv_max - pv_min)
            else:
                pv = np.ones_like(pv) * 0.5
            pv_3d = pv[:, :, np.newaxis]
            paint = paint_before * (1.0 - pv_3d) + paint * pv_3d
        except Exception:
            pass  # Fallback: keep uniform paint mod
    return paint


# ================================================================
# MULTI-ZONE BUILD - THE CORE (FIXED!)
# ================================================================

def build_multi_zone(paint_file, output_dir, zones, iracing_id="23371", seed=51, save_debug_images=False, import_spec_map=None, car_prefix="car_num"):
    """
    Apply different finishes to different color-detected zones.

    Zone format supports THREE modes:

    1. LEGACY (backward compat): "finish" key maps to FINISH_REGISTRY
       {"name": "Body", "color": "blue", "finish": "chrome", "intensity": "100"}

    2. COMPOSITING (v3.0): "base" + optional "pattern" keys
       {"name": "Body", "color": "blue", "base": "chrome", "pattern": "carbon_fiber", "intensity": "100"}
       18 bases x 32 patterns = 576+ combinations!

    3. MONOLITHIC: "finish" key maps to MONOLITHIC_REGISTRY (phantom, ember_glow, etc.)
       {"name": "Body", "color": "blue", "finish": "phantom", "intensity": "100"}

    zones = [
        {
            "name": "Blue body panels",
            "color": "blue",
            "base": "chrome",           # v3.0 compositing
            "pattern": "carbon_fiber",   # Optional, defaults to "none"
            "intensity": "100",
        },
        {
            "name": "Gold accents",
            "color": {"hue_range": [40, 65], "sat_min": 0.3},
            "finish": "prismatic",       # Legacy mode still works
            "intensity": "100",
        },
        {
            "name": "Car Number",
            "color": [
                {"color_rgb": [255, 170, 0], "tolerance": 40},
                {"color_rgb": [51, 102, 255], "tolerance": 40},
                {"color_rgb": [200, 30, 30], "tolerance": 40},
            ],
            "base": "metallic",
            "pattern": "holographic_flake",
            "intensity": "150",
        },
        {
            "name": "Dark areas",
            "color": "dark",
            "base": "matte",
            "pattern": "carbon_fiber",
            "intensity": "80",
        },
        {
            "name": "Everything else",
            "color": "remaining",
            "finish": "gloss",
            "intensity": "50",
        },
    ]
    """
    print("=" * 60)
    print("  SHOKKER ENGINE v3.0 PRO - Base + Pattern Compositing")
    print(f"  Zones: {len(zones)}")
    print(f"  Combinations: {len(BASE_REGISTRY)} bases x {len(PATTERN_REGISTRY)} patterns = {len(BASE_REGISTRY) * len(PATTERN_REGISTRY)}+")
    print("=" * 60)

    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    # Load paint -- PROTECT THE ORIGINAL SOURCE FILE
    # ALWAYS back up the source in its own directory on first render.
    # On subsequent renders, ALWAYS load from the backup to prevent
    # cumulative degradation (re-processing a previously rendered file).
    import shutil
    print(f"\n  Loading: {paint_file}")
    paint_basename = os.path.basename(paint_file)
    source_normalized = os.path.normpath(os.path.abspath(paint_file))
    source_dir = os.path.dirname(source_normalized)

    if paint_basename.startswith("ORIGINAL_"):
        # Source is already the backup file — use it directly
        print(f"  Source is already the backup file — using directly")
    else:
        # Check for backup in the SOURCE directory (where the paint lives)
        backup_path = os.path.join(source_dir, f"ORIGINAL_{paint_basename}")
        if not os.path.exists(backup_path):
            # First render ever for this file — back it up
            shutil.copy2(paint_file, backup_path)
            print(f"  Backed up original to: {source_dir}/ORIGINAL_{paint_basename}")
        else:
            # Backup exists — ALWAYS load from it to avoid stacking effects
            paint_file = backup_path
            print(f"  Loading from backup: ORIGINAL_{paint_basename} (prevents re-processing)")

    t_load = time.time()
    scheme_img = Image.open(paint_file).convert('RGB')
    scheme = np.array(scheme_img).astype(np.float32) / 255.0
    h, w = scheme.shape[:2]
    shape = (h, w)
    print(f"  Resolution: {w}x{h}  ({time.time()-t_load:.2f}s)")

    # Analyze colors
    t_analyze = time.time()
    print()
    stats = analyze_paint_colors(scheme)
    print(f"  Color analysis: {time.time()-t_analyze:.2f}s")

    # Auto-generate zone names if not provided (Paint Booth UI doesn't send them)
    for i, zone in enumerate(zones):
        if "name" not in zone:
            base = zone.get("base", "")
            finish = zone.get("finish", "")
            pattern = zone.get("pattern", "")
            color = zone.get("color", "")
            if isinstance(color, str) and color == "remaining":
                zone["name"] = f"Zone {i+1} (remaining)"
            elif finish:
                zone["name"] = f"Zone {i+1} ({finish})"
            elif base:
                pat_label = f"+{pattern}" if pattern and pattern != "none" else ""
                zone["name"] = f"Zone {i+1} ({base}{pat_label})"
            else:
                zone["name"] = f"Zone {i+1}"

    # Build per-zone masks
    t_masks = time.time()
    print(f"\n  Building zone masks...")
    zone_masks = []
    claimed = np.zeros((h, w), dtype=np.float32)  # Track what's been claimed

    # First pass: build masks for non-remainder zones
    for i, zone in enumerate(zones):
        color_desc = zone.get("color", "everything")

        # SPATIAL REGION MASK: if the zone has a pre-drawn region mask, use it directly
        # This bypasses color detection entirely — great for numbers, sponsors, artwork
        if "region_mask" in zone and zone["region_mask"] is not None:
            region = zone["region_mask"]
            # Ensure it's the right size
            if region.shape[0] != h or region.shape[1] != w:
                from PIL import Image as PILImage
                rm_img = PILImage.fromarray((region * 255).astype(np.uint8))
                rm_img = rm_img.resize((w, h), PILImage.NEAREST)
                region = np.array(rm_img).astype(np.float32) / 255.0
            mask = region.astype(np.float32)
            # Subtract already-claimed areas
            mask = np.clip(mask - claimed * 0.8, 0, 1)
            claimed = np.clip(claimed + mask, 0, 1)
            pixel_count = np.sum(mask > 0.1)
            pct = pixel_count / (h * w) * 100
            print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (SPATIAL REGION MASK)")
            zone_masks.append(mask)
            continue

        # Parse selector(s) — can be a single selector or a LIST of selectors (multi-color zone)
        if isinstance(color_desc, list):
            # Multi-color zone: union of multiple color selectors
            # Each element is a dict like {"color_rgb": [R,G,B], "tolerance": 40}
            union_mask = np.zeros((h, w), dtype=np.float32)
            for sub_desc in color_desc:
                if isinstance(sub_desc, dict):
                    sub_selector = sub_desc
                else:
                    sub_selector = parse_color_description(str(sub_desc))
                sub_mask = build_zone_mask(scheme, stats, sub_selector, blur_radius=3)
                union_mask = np.maximum(union_mask, sub_mask)  # OR/union
            mask = union_mask
            print(f"    Zone {i+1} [{zone['name']}]: multi-color ({len(color_desc)} selectors)")
        elif isinstance(color_desc, dict):
            selector = color_desc
            if selector.get("remainder"):
                zone_masks.append(None)  # Placeholder
                continue
            mask = build_zone_mask(scheme, stats, selector, blur_radius=3)
        else:
            selector = parse_color_description(str(color_desc))
            if selector.get("remainder"):
                zone_masks.append(None)  # Placeholder
                continue
            mask = build_zone_mask(scheme, stats, selector, blur_radius=3)

        # Subtract already-claimed areas (higher priority zones come first)
        mask = np.clip(mask - claimed * 0.8, 0, 1)

        # Add to claimed
        claimed = np.clip(claimed + mask, 0, 1)

        pixel_count = np.sum(mask > 0.1)
        pct = pixel_count / (h * w) * 100
        print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (color: {color_desc})")

        zone_masks.append(mask)

    # Harden zone masks: threshold soft masks so zones get clean ownership.
    # Without this, later zones (especially "remaining") bleed into earlier zones
    # because soft masks (0.0-1.0) leave gaps that remainder fills, then the blend
    # formula (zone_spec * mask + existing * (1-mask)) pulls values toward the later zone.
    HARD_THRESHOLD = 0.15  # Pixels above this get full ownership (mask=1.0)
    for i in range(len(zone_masks)):
        if zone_masks[i] is not None:
            soft = zone_masks[i]
            # Keep soft edges at the boundary but harden the core
            zone_masks[i] = np.where(soft > HARD_THRESHOLD, 1.0, soft / HARD_THRESHOLD * soft).astype(np.float32)

    # Rebuild claimed from hardened masks (so remainder doesn't bleed into them)
    claimed_hard = np.zeros((h, w), dtype=np.float32)
    for i in range(len(zone_masks)):
        if zone_masks[i] is not None:
            claimed_hard = np.clip(claimed_hard + zone_masks[i], 0, 1)

    # Second pass: fill in "remainder" zones
    for i, zone in enumerate(zones):
        if zone_masks[i] is not None:
            continue
        # Remainder = everything not yet claimed (using hardened masks)
        remainder_mask = np.clip(1.0 - claimed_hard, 0, 1)
        # Blur for soft edges at zone boundaries only
        rm_img = Image.fromarray((remainder_mask * 255).astype(np.uint8))
        rm_img = rm_img.filter(ImageFilter.GaussianBlur(radius=2))
        remainder_mask = np.array(rm_img).astype(np.float32) / 255.0
        # Zero out remainder inside claimed zones to prevent overwriting
        remainder_mask = np.where(claimed_hard > 0.5, 0.0, remainder_mask).astype(np.float32)

        pixel_count = np.sum(remainder_mask > 0.1)
        pct = pixel_count / (h * w) * 100
        print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (remainder)")
        zone_masks[i] = remainder_mask

    print(f"  Zone masks built: {time.time()-t_masks:.2f}s")

    # Initialize outputs
    # Start with default spec OR imported spec map (for merge mode)
    if import_spec_map and os.path.exists(import_spec_map):
        print(f"\n  IMPORT SPEC MAP: Loading {os.path.basename(import_spec_map)}")
        try:
            imp_img = Image.open(import_spec_map)
            # Handle both RGBA (32-bit) and RGB (24-bit) spec maps
            if imp_img.mode == 'RGBA':
                combined_spec = np.array(imp_img).astype(np.uint8)
            elif imp_img.mode == 'RGB':
                rgb = np.array(imp_img).astype(np.uint8)
                alpha = np.full((rgb.shape[0], rgb.shape[1], 1), 255, dtype=np.uint8)
                combined_spec = np.concatenate([rgb, alpha], axis=2)
            else:
                imp_img = imp_img.convert('RGBA')
                combined_spec = np.array(imp_img).astype(np.uint8)
            # Resize to match paint if needed
            if combined_spec.shape[0] != h or combined_spec.shape[1] != w:
                imp_resized = Image.fromarray(combined_spec).resize((w, h), Image.LANCZOS)
                combined_spec = np.array(imp_resized).astype(np.uint8)
            print(f"    Imported spec: {combined_spec.shape[1]}x{combined_spec.shape[0]} RGBA")
            print(f"    Zones will MERGE on top of imported spec map")
        except Exception as e:
            print(f"    WARNING: Failed to load import spec map: {e}")
            print(f"    Falling back to default spec")
            combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
            combined_spec[:,:,0] = 5       # Low metallic
            combined_spec[:,:,1] = 100     # Medium-rough
            combined_spec[:,:,2] = 16      # Max clearcoat
            combined_spec[:,:,3] = 255     # Full spec mask
    else:
        combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
        combined_spec[:,:,0] = 5       # Low metallic
        combined_spec[:,:,1] = 100     # Medium-rough
        combined_spec[:,:,2] = 16      # Max clearcoat
        combined_spec[:,:,3] = 255     # Full spec mask
    paint = scheme.copy()

    # Apply each zone's finish using ITS OWN mask
    # Supports three dispatch modes:
    #   1. Compositing: zone has "base" key => compose_finish() + compose_paint_mod()
    #   2. Monolithic: zone has "finish" in MONOLITHIC_REGISTRY => special spec_fn/paint_fn
    #   3. Legacy: zone has "finish" in FINISH_REGISTRY => existing spec_fn/paint_fn
    t_finishes = time.time()
    print(f"\n  Applying finishes...")
    for i, zone in enumerate(zones):
        t_zone = time.time()
        name = zone["name"]
        intensity = zone.get("intensity", "100")
        zone_mask = zone_masks[i]

        if np.max(zone_mask) < 0.01:
            print(f"    [{name}] => SKIPPED (no matching pixels)")
            continue

        # Custom intensity overrides per-zone slider values
        # Custom sliders now use 0-1 normalized range (same as presets),
        # so they also need _INTENSITY_SCALE applied.
        custom = zone.get("custom_intensity")
        if custom:
            sm = float(custom.get("spec", 1.0))  * _INTENSITY_SCALE["spec"]
            pm = float(custom.get("paint", 1.0)) * _INTENSITY_SCALE["paint"]
            bb = float(custom.get("bright", 1.0)) * _INTENSITY_SCALE["bright"]
        else:
            preset = INTENSITY.get(intensity, INTENSITY["100"])
            pm = preset["paint"] * _INTENSITY_SCALE["paint"]
            sm = preset["spec"]  * _INTENSITY_SCALE["spec"]
            bb = preset["bright"] * _INTENSITY_SCALE["bright"]

        # --- Dispatch: determine which rendering path to use ---
        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")
        _engine_rot_debug(f"BUILD_MULTI_ZONE [{name}]: base_id={base_id}, finish_name={finish_name}, "
                          f"rotation={zone.get('rotation')}, finish_colors={zone.get('finish_colors') is not None}, "
                          f"in_MONO_REG={finish_name in MONOLITHIC_REGISTRY if finish_name else 'N/A'}, "
                          f"in_FINISH_REG={finish_name in FINISH_REGISTRY if finish_name else 'N/A'}")

        if base_id:
            # CHECK: Is this actually a monolithic masquerading as a base?
            # This lets the UI send monolithics via "base" key seamlessly.
            if base_id not in BASE_REGISTRY and base_id in MONOLITHIC_REGISTRY:
                finish_name = base_id
                base_id = None  # Fall through to monolithic path below
            elif base_id not in BASE_REGISTRY:
                print(f"    WARNING: Unknown base '{base_id}', skipping")
                continue

        if base_id:
            _engine_rot_debug(f"  [{name}] -> PATH 1 (compositing): base={base_id}")
            # PATH 1: v3.0 COMPOSITING — base + pattern (or pattern stack)
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                print(f"    WARNING: Unknown pattern '{pattern_id}', using 'none'")
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) if _z_cc is not None else None
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                # (prevents double-rendering at zone_scale=1.0 which overwhelms the stack's scale)
                stack_ids = {ps.get("id") for ps in pattern_stack[:3] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation})
                for ps in pattern_stack[:3]:  # Max 3 additional
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                bs_label = f" base@{zone_base_scale:.2f}x" if zone_base_scale != 1.0 else ""
                print(f"    [{name}] => {label} ({intensity}){bs_label} [stacked compositing]")
                if all_patterns:
                    zone_spec = compose_finish_stacked(base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb)
                else:
                    zone_spec = compose_finish(base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.1f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                bs_label = f" base@{zone_base_scale:.2f}x" if zone_base_scale != 1.0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}{bs_label} [compositing]")
                zone_spec = compose_finish(base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation)

        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            _engine_rot_debug(f"  [{name}] -> PATH 2 (monolithic): finish={finish_name}")
            # PATH 2: MONOLITHIC — special finishes (now with optional pattern overlay!)
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_pat_scale = float(zone.get("scale", 1.0))
            mono_pat_opacity = float(zone.get("pattern_opacity", 1.0))
            mono_pat_rotation = float(zone.get("rotation", 0))
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            bs_label = f" base@{mono_base_scale:.2f}x" if mono_base_scale != 1.0 else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}){bs_label} [monolithic]")

            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                # Use FULL mask for tile generation — monolithic covers entire tile.
                # Original zone_mask handles final clipping. This prevents existing
                # car art (numbers, sponsors, decals) from leaking into tiled output.
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                # Generate spec at tile size (full coverage)
                tile_spec = spec_fn(tile_shape, tile_mask, seed + i * 13, sm)
                # Tile spec to fill original shape
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                # For paint: run paint_fn on ORIGINAL paint at full resolution.
                # Scaling only affects the spec map (material properties), NOT the paint.
                # Previous approach created a blank canvas which destroyed the car livery.
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)

            # Optional pattern overlay on top of monolithic
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_pat_scale, mono_pat_opacity, spec_mult=spec_mult, rotation=mono_pat_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_pat_scale, mono_pat_opacity, rotation=mono_pat_rotation)

        elif finish_name and finish_name in FINISH_REGISTRY:
            _engine_rot_debug(f"  [{name}] -> PATH 3 (legacy): finish={finish_name}")
            # PATH 3: LEGACY — backward compat with original FINISH_REGISTRY
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            print(f"    [{name}] => {finish_name} ({intensity}) [legacy]")
            zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
            paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)

        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK — client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            _engine_rot_debug(f"  [{name}] -> PATH 4 (generic fallback): finish={finish_name}, rotation={zone_rotation}, fc_keys={list(zone.get('finish_colors',{}).keys())}")
            print(f"    [DEBUG-ROT] PATH4: finish={finish_name}, zone.rotation={zone.get('rotation')}, parsed={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        else:
            label = finish_name or base_id or "???"
            _engine_rot_debug(f"  [{name}] -> NO PATH MATCHED! finish={finish_name}, base={base_id}, has_fc={zone.get('finish_colors') is not None}")
            print(f"    WARNING: Unknown finish/base '{label}', skipping")
            continue

        # Apply zone spec with hard ownership: where mask is strong, fully replace
        # Vectorized across all 4 channels at once for speed
        mask3d = zone_mask[:,:,np.newaxis]  # (h, w, 1)
        strong = mask3d > 0.5
        soft = (mask3d > 0.05) & ~strong
        blended = np.clip(
            zone_spec.astype(np.float32) * mask3d +
            combined_spec.astype(np.float32) * (1 - mask3d),
            0, 255
        ).astype(np.uint8)
        combined_spec = np.where(strong, zone_spec, np.where(soft, blended, combined_spec))

        print(f"      [{name}] rendered in {time.time()-t_zone:.2f}s")

    # ---- Per-zone wear: BATCHED (single apply_wear call for ALL zones) ----
    # Instead of N separate apply_wear calls (each 5-8s), compute once at max level
    # then blend proportionally per zone.
    wear_zones = [(i, zone, zone_masks[i], int(zone.get("wear_level", 0)))
                  for i, zone in enumerate(zones)
                  if int(zone.get("wear_level", 0)) > 0 and np.max(zone_masks[i]) > 0.01]
    if wear_zones:
        max_wear = max(wl for _, _, _, wl in wear_zones)
        print(f"\n  Batched per-zone wear: {len(wear_zones)} zones, max wear={max_wear}%")
        t_wear = time.time()
        worn_spec, worn_paint = apply_wear(
            combined_spec.copy(), (np.clip(paint, 0, 1) * 255).astype(np.uint8),
            max_wear, seed + 777
        )
        # Blend worn results per zone, scaled by each zone's wear fraction
        for zi, zone, zm, wl in wear_zones:
            wear_frac = wl / max_wear  # 0.0-1.0 how much of the max wear this zone gets
            mask_bool = zm > 0.5
            mask3d = mask_bool[:,:,np.newaxis]
            # Interpolate between unworn and worn based on wear fraction
            if wear_frac >= 0.99:
                # Full strength — just swap
                combined_spec = np.where(mask3d, worn_spec, combined_spec)
                paint = np.where(mask3d, worn_paint.astype(np.float32) / 255.0, paint)
            else:
                # Partial strength — lerp between original and worn
                spec_lerp = np.clip(
                    combined_spec.astype(np.float32) * (1 - wear_frac) +
                    worn_spec.astype(np.float32) * wear_frac, 0, 255
                ).astype(np.uint8)
                paint_lerp = np.clip(
                    paint * (1 - wear_frac) +
                    worn_paint.astype(np.float32) / 255.0 * wear_frac, 0, 1
                )
                combined_spec = np.where(mask3d, spec_lerp, combined_spec)
                paint = np.where(mask3d, paint_lerp, paint)
            print(f"    Zone {zi+1} [{zone['name']}]: wear {wl}% (frac={wear_frac:.2f})")
        print(f"  Batched wear applied in {time.time()-t_wear:.2f}s")

    print(f"  All finishes applied: {time.time()-t_finishes:.2f}s")

    # Convert paint to uint8
    t_save = time.time()
    paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    # Save outputs — car_prefix is "car_num" (custom numbers) or "car" (no custom numbers)
    # Spec map is ALWAYS car_spec regardless of custom number setting
    paint_path = os.path.join(output_dir, f"{car_prefix}_{iracing_id}.tga")
    spec_path = os.path.join(output_dir, f"car_spec_{iracing_id}.tga")

    write_tga_24bit(paint_path, paint_rgb)
    write_tga_32bit(spec_path, combined_spec)

    # Save previews
    Image.fromarray(paint_rgb).save(os.path.join(output_dir, "PREVIEW_paint.png"))
    Image.fromarray(combined_spec).save(os.path.join(output_dir, "PREVIEW_spec.png"))

    # Save individual zone mask previews (only when debug images requested)
    if save_debug_images:
        for i, (zone, mask) in enumerate(zip(zones, zone_masks)):
            mask_img = (mask * 255).astype(np.uint8)
            Image.fromarray(mask_img).save(
                os.path.join(output_dir, f"PREVIEW_zone{i+1}_{zone['name'].replace(' ', '_').replace('/', '_')}.png")
            )

        # Save combined zone map (color-coded)
        zone_map = np.zeros((h, w, 3), dtype=np.uint8)
        zone_colors = [
            [255, 50, 50],   # Red
            [50, 255, 50],   # Green
            [50, 100, 255],  # Blue
            [255, 255, 50],  # Yellow
            [255, 50, 255],  # Magenta
            [50, 255, 255],  # Cyan
            [255, 150, 50],  # Orange
            [150, 50, 255],  # Purple
        ]
        for i, mask in enumerate(zone_masks):
            color = zone_colors[i % len(zone_colors)]
            for c in range(3):
                zone_map[:,:,c] = np.clip(
                    zone_map[:,:,c] + (mask * color[c]).astype(np.uint8),
                    0, 255
                ).astype(np.uint8)
        Image.fromarray(zone_map).save(os.path.join(output_dir, "PREVIEW_zone_map.png"))

    print(f"  File I/O + previews: {time.time()-t_save:.2f}s")

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  DONE in {elapsed:.1f}s!")
    print(f"  Paint: {paint_path}")
    print(f"  Spec:  {spec_path}")
    if save_debug_images:
        print(f"  Zone previews saved for debugging")
    print(f"{'=' * 60}")

    return paint_rgb, combined_spec, zone_masks


# ================================================================
# LIVE PREVIEW — Low-res fast render (no file I/O)
# ================================================================

def preview_render(paint_file, zones, seed=51, preview_scale=0.25, import_spec_map=None):
    """Low-res preview render: returns (paint_rgb, spec_rgba) numpy arrays.

    Stripped-down version of build_multi_zone for near-real-time preview.
    At 0.25 scale (512x512 from 2048x2048), renders in ~100-250ms.

    SKIPS: ORIGINAL_ backup logic, TGA writing, PNG saving, zone map
           generation, wear post-processing, helmet/suit, night variants.

    Returns:
        (paint_rgb_uint8, combined_spec_uint8) — numpy arrays ready for
        conversion to base64 PNG on the server side.
    """
    import time as _time
    t0 = _time.time()

    # Load paint directly — NO backup logic (preview is read-only)
    scheme_img = Image.open(paint_file).convert('RGB')
    orig_w, orig_h = scheme_img.size  # PIL gives (w, h)

    # Immediately downscale for speed
    preview_w = max(16, int(orig_w * preview_scale))
    preview_h = max(16, int(orig_h * preview_scale))
    scheme_img = scheme_img.resize((preview_w, preview_h), Image.LANCZOS)
    scheme = np.array(scheme_img).astype(np.float32) / 255.0
    h, w = scheme.shape[:2]
    shape = (h, w)

    # Analyze colors at reduced resolution
    stats = analyze_paint_colors(scheme)

    # Build per-zone masks at reduced resolution
    zone_masks = []
    claimed = np.zeros((h, w), dtype=np.float32)

    # First pass: non-remainder zones
    for i, zone in enumerate(zones):
        color_desc = zone.get("color", "everything")

        # SPATIAL REGION MASK
        if "region_mask" in zone and zone["region_mask"] is not None:
            region = zone["region_mask"]
            # Resize region mask to preview resolution with NEAREST (binary mask)
            if region.shape[0] != h or region.shape[1] != w:
                rm_img = Image.fromarray((region * 255).astype(np.uint8))
                rm_img = rm_img.resize((w, h), Image.NEAREST)
                region = np.array(rm_img).astype(np.float32) / 255.0
            mask = region.astype(np.float32)
            mask = np.clip(mask - claimed * 0.8, 0, 1)
            claimed = np.clip(claimed + mask, 0, 1)
            zone_masks.append(mask)
            continue

        # Parse selector(s)
        if isinstance(color_desc, list):
            union_mask = np.zeros((h, w), dtype=np.float32)
            for sub_desc in color_desc:
                if isinstance(sub_desc, dict):
                    sub_selector = sub_desc
                else:
                    sub_selector = parse_color_description(str(sub_desc))
                sub_mask = build_zone_mask(scheme, stats, sub_selector, blur_radius=3)
                union_mask = np.maximum(union_mask, sub_mask)
            mask = union_mask
        elif isinstance(color_desc, dict):
            selector = color_desc
            if selector.get("remainder"):
                zone_masks.append(None)
                continue
            mask = build_zone_mask(scheme, stats, selector, blur_radius=3)
        else:
            selector = parse_color_description(str(color_desc))
            if selector.get("remainder"):
                zone_masks.append(None)
                continue
            mask = build_zone_mask(scheme, stats, selector, blur_radius=3)

        mask = np.clip(mask - claimed * 0.8, 0, 1)
        claimed = np.clip(claimed + mask, 0, 1)
        zone_masks.append(mask)

    # Harden zone masks
    HARD_THRESHOLD = 0.15
    for i in range(len(zone_masks)):
        if zone_masks[i] is not None:
            soft = zone_masks[i]
            zone_masks[i] = np.where(soft > HARD_THRESHOLD, 1.0, soft / HARD_THRESHOLD * soft).astype(np.float32)

    # Rebuild claimed from hardened masks
    claimed_hard = np.zeros((h, w), dtype=np.float32)
    for i in range(len(zone_masks)):
        if zone_masks[i] is not None:
            claimed_hard = np.clip(claimed_hard + zone_masks[i], 0, 1)

    # Second pass: remainder zones
    for i, zone in enumerate(zones):
        if zone_masks[i] is not None:
            continue
        remainder_mask = np.clip(1.0 - claimed_hard, 0, 1)
        rm_img = Image.fromarray((remainder_mask * 255).astype(np.uint8))
        rm_img = rm_img.filter(ImageFilter.GaussianBlur(radius=2))
        remainder_mask = np.array(rm_img).astype(np.float32) / 255.0
        remainder_mask = np.where(claimed_hard > 0.5, 0.0, remainder_mask).astype(np.float32)
        zone_masks[i] = remainder_mask

    # Initialize outputs — use imported spec map if provided
    if import_spec_map and os.path.exists(import_spec_map):
        try:
            imp_img = Image.open(import_spec_map)
            if imp_img.mode == 'RGBA':
                combined_spec = np.array(imp_img).astype(np.uint8)
            elif imp_img.mode == 'RGB':
                rgb = np.array(imp_img).astype(np.uint8)
                alpha = np.full((rgb.shape[0], rgb.shape[1], 1), 255, dtype=np.uint8)
                combined_spec = np.concatenate([rgb, alpha], axis=2)
            else:
                imp_img = imp_img.convert('RGBA')
                combined_spec = np.array(imp_img).astype(np.uint8)
            # Resize to preview resolution
            if combined_spec.shape[0] != h or combined_spec.shape[1] != w:
                imp_resized = Image.fromarray(combined_spec).resize((w, h), Image.LANCZOS)
                combined_spec = np.array(imp_resized).astype(np.uint8)
        except Exception:
            combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
            combined_spec[:,:,0] = 5
            combined_spec[:,:,1] = 100
            combined_spec[:,:,2] = 16
            combined_spec[:,:,3] = 255
    else:
        combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
        combined_spec[:,:,0] = 5       # Low metallic
        combined_spec[:,:,1] = 100     # Medium-rough
        combined_spec[:,:,2] = 16      # Max clearcoat
        combined_spec[:,:,3] = 255     # Full spec mask
    paint = scheme.copy()

    # Apply each zone's finish
    # !! ARCHITECTURE GUARD — 4-PATH DISPATCH BELOW !!
    # PATH 1: base_id in BASE_REGISTRY → compose_finish() (compositing)
    # PATH 2: finish_name in MONOLITHIC_REGISTRY → monolithic render
    # PATH 3: finish_name in FINISH_REGISTRY → legacy flat finish
    # PATH 4: finish_name + finish_colors → generic fallback
    # DO NOT reorder these paths. DO NOT add new paths without updating ARCHITECTURE.md.
    for i, zone in enumerate(zones):
        zone_mask = zone_masks[i]
        if np.max(zone_mask) < 0.01:
            continue

        intensity = zone.get("intensity", "100")
        custom = zone.get("custom_intensity")
        if custom:
            sm = float(custom.get("spec", 1.0))  * _INTENSITY_SCALE["spec"]
            pm = float(custom.get("paint", 1.0)) * _INTENSITY_SCALE["paint"]
            bb = float(custom.get("bright", 1.0)) * _INTENSITY_SCALE["bright"]
        else:
            preset = INTENSITY.get(intensity, INTENSITY["100"])
            pm = preset["paint"] * _INTENSITY_SCALE["paint"]
            sm = preset["spec"]  * _INTENSITY_SCALE["spec"]
            bb = preset["bright"] * _INTENSITY_SCALE["bright"]

        # Dispatch: compositing / monolithic / legacy
        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")
        zone_spec = None

        if base_id:
            # CHECK: Is this actually a monolithic masquerading as a base?
            # (same safeguard as full render — lets monolithics sent via "base" key work)
            if base_id not in BASE_REGISTRY and base_id in MONOLITHIC_REGISTRY:
                finish_name = base_id
                base_id = None  # Fall through to monolithic path below
            elif base_id not in BASE_REGISTRY:
                continue

        if base_id:
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) if _z_cc is not None else None
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc

            if pattern_stack or primary_pat_opacity < 1.0:
                # DEDUP: skip primary pattern if it already appears in the stack
                stack_ids = {ps.get("id") for ps in pattern_stack[:3] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation})
                for ps in pattern_stack[:3]:
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                        })
                if all_patterns:
                    zone_spec = compose_finish_stacked(base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb)
                else:
                    zone_spec = compose_finish(base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
            else:
                zone_spec = compose_finish(base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation)

        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            _engine_rot_debug(f"DISPATCH: finish={finish_name} -> PATH 2 (MONOLITHIC_REGISTRY) -- NO ROTATION SUPPORT")
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_base_scale = float(zone.get("base_scale", 1.0))

            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                # Use FULL mask for tile generation — monolithic covers entire tile.
                # Original zone_mask handles final clipping. This prevents existing
                # car art (numbers, sponsors, decals) from leaking into tiled output.
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                tile_spec = spec_fn(tile_shape, tile_mask, seed + i * 13, sm)
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                # For paint: run paint_fn on ORIGINAL paint at full resolution.
                # Scaling only affects the spec map (material properties), NOT the paint.
                # Previous approach created a blank canvas which destroyed the car livery.
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)

        elif finish_name and finish_name in FINISH_REGISTRY:
            _engine_rot_debug(f"DISPATCH: finish={finish_name} -> PATH 3 (FINISH_REGISTRY) -- NO ROTATION SUPPORT")
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
            paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)

        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK — client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            _engine_rot_debug(f"DISPATCH: finish={finish_name} -> PATH 4 (GENERIC), rotation={zone_rotation}, has_finish_colors={bool(zone.get('finish_colors'))}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        else:
            _engine_rot_debug(f"DISPATCH: finish={finish_name} -> UNKNOWN (no path matched), base_id={base_id}, has_finish_colors={bool(zone.get('finish_colors'))}")
            continue

        if zone_spec is None:
            continue

        # Blend zone spec with hard ownership (vectorized across all 4 channels)
        mask3d = zone_mask[:,:,np.newaxis]
        strong = mask3d > 0.5
        soft = (mask3d > 0.05) & ~strong
        blended = np.clip(
            zone_spec.astype(np.float32) * mask3d +
            combined_spec.astype(np.float32) * (1 - mask3d),
            0, 255
        ).astype(np.uint8)
        combined_spec = np.where(strong, zone_spec, np.where(soft, blended, combined_spec))

    # Batched per-zone wear (single apply_wear call — fast even at low res)
    wear_zones = [(i, zone, zone_masks[i], int(zone.get("wear_level", 0)))
                  for i, zone in enumerate(zones)
                  if int(zone.get("wear_level", 0)) > 0 and zone_masks[i] is not None and np.max(zone_masks[i]) > 0.01]
    if wear_zones:
        max_wear = max(wl for _, _, _, wl in wear_zones)
        worn_spec, worn_paint = apply_wear(
            combined_spec.copy(), (np.clip(paint, 0, 1) * 255).astype(np.uint8),
            max_wear, seed + 777
        )
        for zi, zone, zm, wl in wear_zones:
            wear_frac = wl / max_wear
            mask_bool = zm > 0.5
            mask3d = mask_bool[:,:,np.newaxis]
            if wear_frac >= 0.99:
                combined_spec = np.where(mask3d, worn_spec, combined_spec)
                paint = np.where(mask3d, worn_paint.astype(np.float32) / 255.0, paint)
            else:
                spec_lerp = np.clip(
                    combined_spec.astype(np.float32) * (1 - wear_frac) +
                    worn_spec.astype(np.float32) * wear_frac, 0, 255
                ).astype(np.uint8)
                paint_lerp = np.clip(
                    paint * (1 - wear_frac) +
                    worn_paint.astype(np.float32) / 255.0 * wear_frac, 0, 1
                )
                combined_spec = np.where(mask3d, spec_lerp, combined_spec)
                paint = np.where(mask3d, paint_lerp, paint)

    # Convert paint to uint8
    paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    elapsed_ms = (_time.time() - t0) * 1000
    print(f"  [preview_render] {preview_w}x{preview_h} ({len(zones)} zones) in {elapsed_ms:.0f}ms")

    return paint_rgb, combined_spec, elapsed_ms


# ================================================================
# CONVENIENCE: Apply single finish to whole car (backward compat)
# ================================================================

def apply_single_finish(paint_file, finish_name, output_dir, iracing_id="23371",
                        seed=51, intensity="100"):
    """Apply one finish to the whole car (backward compatible)."""
    zones = [{
        "name": "Whole Car",
        "color": "everything",
        "finish": finish_name,
        "intensity": intensity,
    }]
    return build_multi_zone(paint_file, output_dir, zones, iracing_id, seed)


def apply_composed_finish(paint_file, base, pattern, output_dir, iracing_id="23371",
                          seed=51, intensity="100"):
    """Apply a composed base+pattern finish to the whole car (v3.0)."""
    zones = [{
        "name": "Whole Car",
        "color": "everything",
        "base": base,
        "pattern": pattern or "none",
        "intensity": intensity,
    }]
    return build_multi_zone(paint_file, output_dir, zones, iracing_id, seed)


# ================================================================
# SHARED HELPERS (extracted for reuse in helmet/suit/wear)
# ================================================================

def _parse_intensity(intensity):
    """Parse intensity string to (spec_mult, paint_mult, bright_boost).
    Applies channel-specific scaling so 100% = 1.0 in the table maps to
    the correct internal multiplier each channel needs."""
    preset = INTENSITY.get(intensity, INTENSITY["100"])
    return (preset["spec"]  * _INTENSITY_SCALE["spec"],
            preset["paint"] * _INTENSITY_SCALE["paint"],
            preset["bright"] * _INTENSITY_SCALE["bright"])


def _build_color_mask(paint_rgb, zone, shape):
    """Build a zone mask from color description. Simplified version for helmet/suit.

    Uses the same color matching as build_multi_zone but without
    the full claimed/remainder tracking (caller handles that).
    """
    color_desc = zone.get("color", "everything")
    h, w = shape
    scheme = paint_rgb.astype(np.float32) / 255.0 if paint_rgb.max() > 1 else paint_rgb

    # Analyze colors
    stats = analyze_paint_colors(scheme)

    if isinstance(color_desc, list):
        # Multi-color zone: union of multiple selectors
        union_mask = np.zeros((h, w), dtype=np.float32)
        for sub_desc in color_desc:
            if isinstance(sub_desc, dict):
                sub_selector = sub_desc
            else:
                sub_selector = parse_color_description(str(sub_desc))
            sub_mask = build_zone_mask(scheme, stats, sub_selector, blur_radius=3)
            union_mask = np.maximum(union_mask, sub_mask)
        mask = union_mask
    elif isinstance(color_desc, dict):
        selector = color_desc
        if selector.get("remainder"):
            # Remainder zone — return full mask (caller clips with claimed)
            return np.ones((h, w), dtype=np.float32)
        mask = build_zone_mask(scheme, stats, selector, blur_radius=3)
    else:
        selector = parse_color_description(str(color_desc))
        if selector.get("remainder"):
            return np.ones((h, w), dtype=np.float32)
        mask = build_zone_mask(scheme, stats, selector, blur_radius=3)

    # Harden soft masks
    HARD_THRESHOLD = 0.15
    mask = np.where(mask > HARD_THRESHOLD, 1.0, mask / HARD_THRESHOLD * mask).astype(np.float32)
    return mask


# ================================================================
# HELMET & SUIT SPEC MAP GENERATOR
# ================================================================

def build_helmet_spec(helmet_paint_file, output_dir, zones, iracing_id="23371", seed=51):
    """Generate a spec map for an iRacing helmet paint file.

    Helmet paints are typically 512x512 or 1024x1024 24-bit TGA.
    Uses the same zone/finish system as cars — color-match zones on the
    helmet paint and apply finishes to generate helmet_spec_<id>.tga.

    The helmet UV layout has the crown on top, visor in the middle,
    chin bar at bottom. Colors match just like car paints.
    """
    print(f"\n{'='*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO — Helmet Spec Generator")
    print(f"  ID: {iracing_id}")
    print(f"{'='*60}")
    start_time = time.time()

    # Load helmet paint (24-bit or 32-bit TGA)
    img = Image.open(helmet_paint_file)
    if img.mode == 'RGBA':
        paint_rgb = np.array(img)[:,:,:3]
    else:
        paint_rgb = np.array(img)
    h, w = paint_rgb.shape[:2]
    print(f"  Helmet: {w}x{h}")

    shape = (h, w)
    paint = paint_rgb.astype(np.float32) / 255.0

    # Build spec using same zone logic as cars
    combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
    combined_spec[:,:,1] = 100  # default R
    combined_spec[:,:,3] = 255  # full spec mask

    claimed = np.zeros(shape, dtype=np.float32)

    for i, zone in enumerate(zones):
        name = zone.get("name", f"Zone {i+1}")
        intensity = zone.get("intensity", "100")
        sm, pm, bb = _parse_intensity(intensity)

        zone_mask = _build_color_mask(paint_rgb, zone, shape)
        zone_mask = np.clip(zone_mask - claimed * 0.8, 0, 1).astype(np.float32)

        if zone_mask.max() < 0.01:
            print(f"    [{name}] => no pixels matched, skipping")
            continue

        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")

        if base_id:
            if base_id not in BASE_REGISTRY:
                continue
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) if _z_cc is not None else None
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                stack_ids = {ps.get("id") for ps in pattern_stack[:3] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation})
                for ps in pattern_stack[:3]:  # Max 3 additional
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                print(f"    [{name}] => {label} ({intensity}) [stacked compositing]")
                if all_patterns:
                    zone_spec = compose_finish_stacked(base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb)
                else:
                    zone_spec = compose_finish(base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.1f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}")
                zone_spec = compose_finish(base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation)
        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}) [monolithic]")

            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                # Use FULL mask for tile generation — monolithic covers entire tile.
                # Original zone_mask handles final clipping. This prevents existing
                # car art (numbers, sponsors, decals) from leaking into tiled output.
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                tile_spec = spec_fn(tile_shape, tile_mask, seed + i * 13, sm)
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                # For paint: run paint_fn on ORIGINAL paint at full resolution.
                # Scaling only affects the spec map (material properties), NOT the paint.
                # Previous approach created a blank canvas which destroyed the car livery.
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in FINISH_REGISTRY:
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            print(f"    [{name}] => {finish_name} ({intensity}) [legacy]")
            zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
            paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK — client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            print(f"    [DEBUG-ROT] PATH4: finish={finish_name}, zone.rotation={zone.get('rotation')}, parsed={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        else:
            continue

        claimed = np.clip(claimed + zone_mask, 0, 1)
        mask3d = zone_mask[:,:,np.newaxis]
        soft = mask3d > 0.05
        blended = np.clip(
            zone_spec.astype(np.float32) * mask3d +
            combined_spec.astype(np.float32) * (1 - mask3d),
            0, 255
        ).astype(np.uint8)
        combined_spec = np.where(soft, blended, combined_spec)

    # Save outputs
    os.makedirs(output_dir, exist_ok=True)
    spec_path = os.path.join(output_dir, f"helmet_spec_{iracing_id}.tga")
    write_tga_32bit(spec_path, combined_spec)
    Image.fromarray(combined_spec).save(os.path.join(output_dir, "PREVIEW_helmet_spec.png"))

    # Also save modified paint if it changed
    helmet_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    paint_path = os.path.join(output_dir, f"helmet_{iracing_id}.tga")
    write_tga_24bit(paint_path, helmet_paint)
    Image.fromarray(helmet_paint).save(os.path.join(output_dir, "PREVIEW_helmet_paint.png"))

    elapsed = time.time() - start_time
    print(f"\n  Helmet done in {elapsed:.1f}s!")
    print(f"  Spec:  {spec_path}")
    print(f"  Paint: {paint_path}")
    return helmet_paint, combined_spec


def build_suit_spec(suit_paint_file, output_dir, zones, iracing_id="23371", seed=51):
    """Generate a spec map for an iRacing suit (firesuit) paint file.

    Suit paints are typically 1024x1024 24-bit TGA.
    Layout: shirt (upper left/center), pants (lower center),
    gloves (lower left), shoes (lower left corner).

    Uses exact same zone/finish system as cars and helmets.
    """
    print(f"\n{'='*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO — Suit Spec Generator")
    print(f"  ID: {iracing_id}")
    print(f"{'='*60}")
    start_time = time.time()

    img = Image.open(suit_paint_file)
    if img.mode == 'RGBA':
        paint_rgb = np.array(img)[:,:,:3]
    else:
        paint_rgb = np.array(img)
    h, w = paint_rgb.shape[:2]
    print(f"  Suit: {w}x{h}")

    shape = (h, w)
    paint = paint_rgb.astype(np.float32) / 255.0

    combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
    combined_spec[:,:,1] = 100
    combined_spec[:,:,3] = 255
    claimed = np.zeros(shape, dtype=np.float32)

    for i, zone in enumerate(zones):
        name = zone.get("name", f"Zone {i+1}")
        intensity = zone.get("intensity", "100")
        sm, pm, bb = _parse_intensity(intensity)

        zone_mask = _build_color_mask(paint_rgb, zone, shape)
        zone_mask = np.clip(zone_mask - claimed * 0.8, 0, 1).astype(np.float32)

        if zone_mask.max() < 0.01:
            print(f"    [{name}] => no pixels matched, skipping")
            continue

        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")

        if base_id:
            if base_id not in BASE_REGISTRY:
                continue
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) if _z_cc is not None else None
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                stack_ids = {ps.get("id") for ps in pattern_stack[:3] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation})
                for ps in pattern_stack[:3]:  # Max 3 additional
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                print(f"    [{name}] => {label} ({intensity}) [stacked compositing]")
                if all_patterns:
                    zone_spec = compose_finish_stacked(base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                    paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb)
                else:
                    zone_spec = compose_finish(base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.1f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}")
                zone_spec = compose_finish(base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation)
        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}) [monolithic]")

            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                # Use FULL mask for tile generation — monolithic covers entire tile.
                # Original zone_mask handles final clipping. This prevents existing
                # car art (numbers, sponsors, decals) from leaking into tiled output.
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                tile_spec = spec_fn(tile_shape, tile_mask, seed + i * 13, sm)
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                # For paint: run paint_fn on ORIGINAL paint at full resolution.
                # Scaling only affects the spec map (material properties), NOT the paint.
                # Previous approach created a blank canvas which destroyed the car livery.
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in FINISH_REGISTRY:
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            print(f"    [{name}] => {finish_name} ({intensity}) [legacy]")
            zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
            paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK — client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            print(f"    [DEBUG-ROT] PATH4: finish={finish_name}, zone.rotation={zone.get('rotation')}, parsed={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        else:
            continue

        claimed = np.clip(claimed + zone_mask, 0, 1)
        mask3d = zone_mask[:,:,np.newaxis]
        soft = mask3d > 0.05
        blended = np.clip(
            zone_spec.astype(np.float32) * mask3d +
            combined_spec.astype(np.float32) * (1 - mask3d),
            0, 255
        ).astype(np.uint8)
        combined_spec = np.where(soft, blended, combined_spec)

    os.makedirs(output_dir, exist_ok=True)
    spec_path = os.path.join(output_dir, f"suit_spec_{iracing_id}.tga")
    write_tga_32bit(spec_path, combined_spec)
    Image.fromarray(combined_spec).save(os.path.join(output_dir, "PREVIEW_suit_spec.png"))

    suit_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    paint_path = os.path.join(output_dir, f"suit_{iracing_id}.tga")
    write_tga_24bit(paint_path, suit_paint)
    Image.fromarray(suit_paint).save(os.path.join(output_dir, "PREVIEW_suit_paint.png"))

    elapsed = time.time() - start_time
    print(f"\n  Suit done in {elapsed:.1f}s!")
    print(f"  Spec:  {spec_path}")
    print(f"  Paint: {paint_path}")
    return suit_paint, combined_spec


def build_matching_set(car_paint_file, output_dir, zones, iracing_id="23371", seed=51,
                       helmet_paint_file=None, suit_paint_file=None, import_spec_map=None, car_prefix="car_num"):
    """Build car + matching helmet + matching suit in one call.

    If helmet/suit paint files are provided, applies the SAME zone config
    to all three. If not provided, generates simple spec maps based on
    the car's primary zone finish.

    Returns dict with all outputs.
    """
    print(f"\n{'='*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO — MATCHING SET BUILDER")
    print(f"  Car + Helmet + Suit — One Click")
    print(f"{'='*60}")
    total_start = time.time()

    results = {}

    # 1. Build car (always)
    car_paint, car_spec, zone_masks = build_multi_zone(
        car_paint_file, output_dir, zones, iracing_id, seed, import_spec_map=import_spec_map, car_prefix=car_prefix)
    results["car_paint"] = car_paint
    results["car_spec"] = car_spec

    # 2. Build helmet spec (only if paint file explicitly provided)
    if helmet_paint_file and os.path.exists(helmet_paint_file):
        h_paint, h_spec = build_helmet_spec(
            helmet_paint_file, output_dir, zones, iracing_id, seed)
        results["helmet_paint"] = h_paint
        results["helmet_spec"] = h_spec
    else:
        print(f"\n  Helmet: skipped (no paint file provided)")

    # 3. Build suit spec (only if paint file explicitly provided)
    if suit_paint_file and os.path.exists(suit_paint_file):
        s_paint, s_spec = build_suit_spec(
            suit_paint_file, output_dir, zones, iracing_id, seed)
        results["suit_paint"] = s_paint
        results["suit_spec"] = s_spec
    else:
        print(f"\n  Suit: skipped (no paint file provided)")

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  MATCHING SET COMPLETE in {total_elapsed:.1f}s!")
    items = ["car"]
    if "helmet_paint" in results or "helmet_spec" in results:
        items.append("helmet")
    if "suit_paint" in results or "suit_spec" in results:
        items.append("suit")
    print(f"  Generated: {' + '.join(items)}")
    print(f"{'='*60}")

    return results


# ================================================================
# WEAR / AGE POST-PROCESSING
# ================================================================

def apply_wear(spec_map, paint_rgb, wear_level, seed=51):
    """Apply wear/age post-processing to an already-rendered spec map + paint.

    wear_level: 0-100
        0   = showroom fresh (no change)
        25  = light track wear (micro-scratches, slight clearcoat fade)
        50  = mid-season (visible scratches, roughness increase, paint chips)
        75  = heavy use (deep scratches, clearcoat loss, paint fade)
        100 = track-beaten veteran (severe damage, extensive clearcoat loss)

    Applies:
    1. Micro-scratches (directional noise => adds roughness)
    2. Clearcoat degradation (noise-driven CC reduction)
    3. Paint fading/chips (brightens/desaturates paint in damaged areas)
    4. Edge wear (stronger damage at high-frequency paint boundaries)

    Returns (modified_spec, modified_paint).
    """
    if wear_level <= 0:
        return spec_map.copy(), paint_rgb.copy()

    w_frac = np.clip(wear_level / 100.0, 0, 1)
    h, w = spec_map.shape[:2]
    shape = (h, w)
    rng = np.random.RandomState(seed + 777)

    spec = spec_map.copy().astype(np.float32)
    paint = paint_rgb.copy().astype(np.float32) / 255.0

    # 1. Micro-scratches: directional noise (horizontal bias like real track rash)
    scratch_h = rng.randn(1, w).astype(np.float32) * 0.6
    scratch_h = np.tile(scratch_h, (h, 1))
    scratch_fine = rng.randn(h, w).astype(np.float32) * 0.4
    scratch = np.clip(scratch_h + scratch_fine, -1, 1)

    # Roughness increase from scratches (R channel)
    roughness_add = np.abs(scratch) * 60 * w_frac
    spec[:,:,1] = np.clip(spec[:,:,1] + roughness_add, 0, 255)

    # Metallic reduction from scratches (scuffs reduce metallic sheen)
    metallic_sub = np.abs(scratch) * 30 * w_frac
    spec[:,:,0] = np.clip(spec[:,:,0] - metallic_sub, 0, 255)

    # 2. Clearcoat degradation
    cc_noise = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed + 888)
    cc_damage = np.clip(np.abs(cc_noise) * 2, 0, 1) * w_frac

    # Only degrade where clearcoat exists (B channel > 0)
    current_cc = spec[:,:,2].astype(np.float32)
    cc_reduction = cc_damage * 16  # up to 16 units lost
    spec[:,:,2] = np.clip(current_cc - cc_reduction, 0, 16).astype(np.uint8)

    # 3. Paint fading/chips in damaged areas
    if w_frac > 0.2:
        chip_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 999)
        chip_mask = np.clip(np.abs(chip_noise) * 3 - (1.5 - w_frac * 1.5), 0, 1)
        # Desaturate and brighten damaged areas
        gray = paint.mean(axis=2, keepdims=True)
        faded = paint * (1 - chip_mask[:,:,np.newaxis] * 0.3) + \
                gray * chip_mask[:,:,np.newaxis] * 0.2 + \
                chip_mask[:,:,np.newaxis] * 0.05  # slight brighten (exposed primer)
        paint = np.clip(faded, 0, 1)

    # 4. Edge wear — stronger damage at color boundaries
    if w_frac > 0.3:
        # Detect edges via Sobel-like gradient magnitude
        from PIL import ImageFilter as IF
        gray_img = Image.fromarray((paint.mean(axis=2) * 255).astype(np.uint8))
        edge_img = gray_img.filter(IF.FIND_EDGES)
        edge_map = np.array(edge_img).astype(np.float32) / 255.0
        # Blur edges to spread wear zone
        edge_pil = Image.fromarray((edge_map * 255).astype(np.uint8))
        edge_pil = edge_pil.filter(IF.GaussianBlur(radius=3))
        edge_map = np.array(edge_pil).astype(np.float32) / 255.0
        edge_wear = edge_map * w_frac * 0.7

        # Extra roughness at edges
        spec[:,:,1] = np.clip(spec[:,:,1] + edge_wear * 80, 0, 255)
        # Extra metallic loss at edges
        spec[:,:,0] = np.clip(spec[:,:,0] - edge_wear * 40, 0, 255)
        # Extra CC loss at edges
        spec[:,:,2] = np.clip(spec[:,:,2].astype(np.float32) - edge_wear * 10, 0, 16)

    result_spec = np.clip(spec, 0, 255).astype(np.uint8)
    result_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    return result_spec, result_paint


# ================================================================
# EXPORT PACKAGE BUILDER
# ================================================================

def build_export_package(output_dir, iracing_id="23371", car_folder_name=None,
                         include_helmet=True, include_suit=True,
                         wear_level=0, zones_config=None):
    """Bundle all render outputs into an organized export package.

    Creates a ZIP file containing:
    - car_num_<id>.tga (paint)
    - car_spec_<id>.tga (spec map)
    - helmet_spec_<id>.tga (if generated)
    - suit_spec_<id>.tga (if generated)
    - PREVIEW_*.png files
    - config.json (zone config for reloading)
    - README.txt (what's in the package)

    Returns path to the ZIP file.
    """
    import zipfile

    os.makedirs(output_dir, exist_ok=True)

    # Save config if provided
    if zones_config:
        config_path = os.path.join(output_dir, "shokker_config.json")
        config_data = {
            "iracing_id": iracing_id,
            "car_folder": car_folder_name or "unknown",
            "zones": zones_config,
            "wear_level": wear_level,
            "engine_version": "3.0 PRO",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

    # Create README
    readme_path = os.path.join(output_dir, "README.txt")
    readme = f"""SHOKKER ENGINE v3.0 PRO — Export Package
========================================
iRacing ID: {iracing_id}
Car: {car_folder_name or 'N/A'}
Wear Level: {wear_level}/100
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}

FILE GUIDE:
-----------
car_num_{iracing_id}.tga     => Paint file (copy to iRacing paint folder)
car_spec_{iracing_id}.tga    => Spec map (copy to iRacing paint folder)
helmet_spec_{iracing_id}.tga => Helmet spec (copy to iRacing paint folder)
suit_spec_{iracing_id}.tga   => Suit spec (copy to iRacing paint folder)
PREVIEW_*.png                => Preview images for reference
shokker_config.json          => Re-import this in Paint Booth to reload

INSTALLATION:
Copy the .tga files to your iRacing paint folder:
  Documents/iRacing/paint/<car_folder>/

Powered by Shokker Engine v3.0 PRO
"""
    with open(readme_path, 'w') as f:
        f.write(readme)

    # Build ZIP
    zip_name = f"shokker_{iracing_id}_{car_folder_name or 'export'}_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(output_dir, zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(output_dir):
            if fname == zip_name:
                continue  # don't add zip to itself
            fpath = os.path.join(output_dir, fname)
            if os.path.isfile(fpath):
                # Only include relevant files
                if fname.endswith(('.tga', '.png', '.json', '.txt')):
                    zf.write(fpath, fname)

    zip_size = os.path.getsize(zip_path)
    print(f"\n  Export package: {zip_path}")
    print(f"  Size: {zip_size / 1024 / 1024:.1f} MB")
    return zip_path


# ================================================================
# GRADIENT MASK GENERATOR
# ================================================================

def generate_gradient_mask(height, width, direction="horizontal", center=None,
                           start_pct=0.0, end_pct=1.0):
    """Generate a float32 gradient mask (0-1) for zone fade transitions.

    Args:
        height, width: Output dimensions
        direction: 'horizontal', 'vertical', 'radial', 'diagonal'
        center: (cx, cy) normalized 0-1 for radial gradients. Default center.
        start_pct: Where gradient begins (0.0 = edge)
        end_pct: Where gradient ends (1.0 = opposite edge)

    Returns:
        float32 array (height, width) with values 0.0-1.0
    """
    if direction == "horizontal":
        grad = np.linspace(0, 1, width, dtype=np.float32)
        mask = np.tile(grad, (height, 1))
    elif direction == "vertical":
        grad = np.linspace(0, 1, height, dtype=np.float32)
        mask = np.tile(grad.reshape(-1, 1), (1, width))
    elif direction == "diagonal":
        gx = np.linspace(0, 1, width, dtype=np.float32)
        gy = np.linspace(0, 1, height, dtype=np.float32)
        mask = (gx[np.newaxis, :] + gy[:, np.newaxis]) / 2.0
    elif direction == "radial":
        cx = center[0] if center else 0.5
        cy = center[1] if center else 0.5
        gx = np.linspace(0, 1, width, dtype=np.float32)
        gy = np.linspace(0, 1, height, dtype=np.float32)
        dx = gx[np.newaxis, :] - cx
        dy = gy[:, np.newaxis] - cy
        dist = np.sqrt(dx*dx + dy*dy)
        max_dist = np.sqrt(max(cx, 1-cx)**2 + max(cy, 1-cy)**2)
        mask = np.clip(dist / max(max_dist, 1e-6), 0, 1).astype(np.float32)
    else:
        mask = np.full((height, width), 0.5, dtype=np.float32)

    # Apply start/end clipping
    if start_pct > 0 or end_pct < 1:
        span = max(end_pct - start_pct, 1e-6)
        mask = np.clip((mask - start_pct) / span, 0, 1).astype(np.float32)

    return mask


# ================================================================
# DAY/NIGHT DUAL SPEC MAP GENERATOR
# ================================================================

def generate_night_variant(day_spec, night_boost=0.7):
    """Generate a night-optimized spec map from the day spec map.

    Night variant has enhanced reflectivity for track lighting:
    - Metallic boost: more reflection under spotlights
    - Roughness reduction: sharper, more dramatic reflections
    - Clearcoat: push to max for that under-lights pop

    Args:
        day_spec: RGBA uint8 array (R=Metallic, G=Roughness, B=Clearcoat, A=SpecMask)
        night_boost: 0.0-1.0 strength of night enhancement

    Returns:
        night_spec: RGBA uint8 array with night-optimized values
    """
    night = day_spec.copy().astype(np.float32)
    boost = np.clip(night_boost, 0.0, 1.0)

    # R channel = Metallic: boost reflectivity
    night[:,:,0] = np.clip(night[:,:,0] * (1.0 + 0.3 * boost) + 15 * boost, 0, 255)

    # G channel = Roughness: reduce for sharper reflections
    night[:,:,1] = np.clip(night[:,:,1] * (1.0 - 0.25 * boost) - 8 * boost, 0, 255)

    # B channel = Clearcoat: push toward 16 (ON) where any CC exists
    cc = night[:,:,2]
    cc_mask = cc > 0  # pixels that already have clearcoat
    cc[cc_mask] = np.clip(cc[cc_mask] + 4 * boost, 0, 16)
    night[:,:,2] = cc

    # A channel = SpecMask: keep as-is

    return night.astype(np.uint8)


# ================================================================
# FULL RENDER PIPELINE (Car + Helmet + Suit + Wear + Export)
# ================================================================

def full_render_pipeline(car_paint_file, output_dir, zones, iracing_id="23371",
                         seed=51, helmet_paint_file=None, suit_paint_file=None,
                         wear_level=0, car_folder_name=None, export_zip=True,
                         dual_spec=False, night_boost=0.7, import_spec_map=None,
                         car_prefix="car_num"):
    """The ultimate one-call render pipeline.

    1. Builds car spec map + paint modifications
    2. Generates matching helmet spec (from paint file or default)
    3. Generates matching suit spec (from paint file or default)
    4. Applies wear/age post-processing to all outputs
    5. Bundles everything into an export ZIP

    Returns dict with all outputs + export path.
    """
    print(f"\n{'*'*60}")
    print(f"  SHOKKER ENGINE v3.0 PRO — FULL RENDER PIPELINE")
    print(f"  Car + Helmet + Suit + Wear({wear_level}) + Export")
    print(f"{'*'*60}")
    pipeline_start = time.time()

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Build matching set (car + helmet + suit)
    t_step1 = time.time()
    results = build_matching_set(
        car_paint_file, output_dir, zones, iracing_id, seed,
        helmet_paint_file, suit_paint_file, import_spec_map=import_spec_map,
        car_prefix=car_prefix
    )
    print(f"  Step 1 (matching set): {time.time()-t_step1:.1f}s")

    # Step 2: Apply wear post-processing
    if wear_level > 0:
        t_step2 = time.time()
        print(f"\n  Applying wear level {wear_level}/100...")

        # Wear on car
        car_spec_worn, car_paint_worn = apply_wear(
            results["car_spec"], results["car_paint"], wear_level, seed)
        # Overwrite files
        write_tga_24bit(os.path.join(output_dir, f"car_num_{iracing_id}.tga"), car_paint_worn)
        write_tga_32bit(os.path.join(output_dir, f"car_spec_{iracing_id}.tga"), car_spec_worn)
        Image.fromarray(car_paint_worn).save(os.path.join(output_dir, "PREVIEW_paint.png"))
        Image.fromarray(car_spec_worn).save(os.path.join(output_dir, "PREVIEW_spec.png"))
        results["car_paint"] = car_paint_worn
        results["car_spec"] = car_spec_worn

        # Wear on helmet (lighter — helmets don't get as beat up)
        if "helmet_spec" in results:
            helmet_wear = max(0, wear_level - 20)  # 20% less wear than car
            if helmet_wear > 0:
                h_paint = results.get("helmet_paint",
                    np.full((*results["helmet_spec"].shape[:2], 3), 128, dtype=np.uint8))
                h_spec_worn, h_paint_worn = apply_wear(
                    results["helmet_spec"], h_paint, helmet_wear, seed + 1)
                write_tga_32bit(os.path.join(output_dir, f"helmet_spec_{iracing_id}.tga"), h_spec_worn)
                Image.fromarray(h_spec_worn).save(os.path.join(output_dir, "PREVIEW_helmet_spec.png"))
                results["helmet_spec"] = h_spec_worn

        # Wear on suit (much lighter — suits are fabric)
        if "suit_spec" in results:
            suit_wear = max(0, wear_level - 40)  # 40% less wear than car
            if suit_wear > 0:
                s_paint = results.get("suit_paint",
                    np.full((*results["suit_spec"].shape[:2], 3), 128, dtype=np.uint8))
                s_spec_worn, s_paint_worn = apply_wear(
                    results["suit_spec"], s_paint, suit_wear, seed + 2)
                write_tga_32bit(os.path.join(output_dir, f"suit_spec_{iracing_id}.tga"), s_spec_worn)
                Image.fromarray(s_spec_worn).save(os.path.join(output_dir, "PREVIEW_suit_spec.png"))
                results["suit_spec"] = s_spec_worn

        print(f"  Wear applied: car={wear_level}, helmet={max(0,wear_level-20)}, suit={max(0,wear_level-40)}")
        print(f"  Step 2 (wear): {time.time()-t_step2:.1f}s")

    # Step 2.5: Day/Night dual spec maps
    if dual_spec:
        print(f"\n  Generating night spec variants (boost={night_boost})...")

        # Night car spec
        night_car = generate_night_variant(results["car_spec"], night_boost)
        write_tga_32bit(os.path.join(output_dir, f"car_spec_night_{iracing_id}.tga"), night_car)
        Image.fromarray(night_car).save(os.path.join(output_dir, "PREVIEW_spec_night.png"))
        results["car_spec_night"] = night_car

        # Night helmet spec
        if "helmet_spec" in results:
            night_helmet = generate_night_variant(results["helmet_spec"], night_boost)
            write_tga_32bit(os.path.join(output_dir, f"helmet_spec_night_{iracing_id}.tga"), night_helmet)
            Image.fromarray(night_helmet).save(os.path.join(output_dir, "PREVIEW_helmet_spec_night.png"))
            results["helmet_spec_night"] = night_helmet

        # Night suit spec
        if "suit_spec" in results:
            night_suit = generate_night_variant(results["suit_spec"], night_boost)
            write_tga_32bit(os.path.join(output_dir, f"suit_spec_night_{iracing_id}.tga"), night_suit)
            Image.fromarray(night_suit).save(os.path.join(output_dir, "PREVIEW_suit_spec_night.png"))
            results["suit_spec_night"] = night_suit

        print(f"  Night variants generated: car{' + helmet' if 'helmet_spec' in results else ''}{' + suit' if 'suit_spec' in results else ''}")

    # Step 3: Export package
    if export_zip:
        zones_serializable = []
        for z in zones:
            zs = {}
            for k, v in z.items():
                if callable(v):
                    continue
                zs[k] = v
            zones_serializable.append(zs)

        results["export_zip"] = build_export_package(
            output_dir, iracing_id, car_folder_name,
            "helmet_spec" in results, "suit_spec" in results,
            wear_level, zones_serializable
        )

    pipeline_elapsed = time.time() - pipeline_start
    print(f"\n{'*'*60}")
    print(f"  FULL PIPELINE COMPLETE in {pipeline_elapsed:.1f}s!")
    print(f"{'*'*60}")

    return results


# ================================================================
# MAIN - Example usage
# ================================================================
if __name__ == '__main__':
    # Example: Superman #51 ARCA with color-based zones
    paint = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\Driver Paints\Dillon Bryant\db51sm_tga.tga"
    output = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\Driver Paints\Dillon Bryant\v2_test"

    zones = [
        {
            "name": "Blue body",
            "color": "blue",
            "finish": "holographic_flake",
            "intensity": "100",
        },
        {
            "name": "Red/Yellow accents",
            "color": {"hue_range": [0, 70], "sat_min": 0.25},
            "finish": "prismatic",
            "intensity": "100",
        },
        {
            "name": "Dark areas",
            "color": "dark",
            "finish": "carbon_fiber",
            "intensity": "80",
        },
        {
            "name": "Everything else",
            "color": "remaining",
            "finish": "gloss",
            "intensity": "50",
        },
    ]

    build_multi_zone(paint, output, zones, iracing_id="23371", seed=51)
