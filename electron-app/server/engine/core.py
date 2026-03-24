"""
engine/core.py â€” Primitive Functions
=====================================
All low-level utilities. Nothing that renders finishes lives here.
Everything else imports FROM here â€” this module imports nothing from engine/.

CONTENTS:
  - TGA file writers (write_tga_32bit, write_tga_24bit)
  - Noise generators (multi_scale_noise, perlin_multi_octave)
  - Coordinate helpers (get_mgrid)
  - Color conversion (hsv_to_rgb_vec, rgb_to_hsv_array)
  - Color analysis & masking (analyze_paint_colors, build_zone_mask)
  - Natural language color parsing (parse_color_description)
  - Intensity presets

FIX GUIDE:
  - Noise looks wrong â†’ edit multi_scale_noise or perlin_multi_octave
  - Color matching not finding right pixels â†’ edit build_zone_mask
  - Color words not parsing â†’ edit COLOR_WORD_MAP or parse_color_description
  - TGA files corrupted â†’ edit write_tga_32bit / write_tga_24bit
"""

import numpy as np
from PIL import Image, ImageFilter
import struct
import cv2
from scipy.ndimage import gaussian_filter


# ================================================================
# TGA FILE WRITERS
# ================================================================

def write_tga_32bit(filepath, rgba_array):
    """Write a 32-bit BGRA TGA file (paint + alpha). iRacing uses 32-bit for paint."""
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
    """Write a 24-bit BGR TGA file (spec map). iRacing spec maps are 24-bit."""
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
# COORDINATE GRID CACHE
# Avoids re-allocating ~32MB per texture function call
# ================================================================

_mgrid_cache = {}


def get_mgrid(shape):
    """Return cached (y, x) coordinate grids for the given (h, w) shape."""
    if shape not in _mgrid_cache:
        h, w = shape
        _mgrid_cache[shape] = np.mgrid[0:h, 0:w]
    return _mgrid_cache[shape]


# ================================================================
# NOISE GENERATORS
# ================================================================

def multi_scale_noise(shape, scales, weights, seed=42):
    """Multi-scale noise: layered at different frequencies. Uses RandomState, normalizes to [-1, 1].
    Used by spec/paint functions and Color Shift for consistent blending."""
    h, w = shape
    result = np.zeros((h, w), dtype=np.float32)
    rng = np.random.RandomState(seed)
    for scale, weight in zip(scales, weights):
        sh, sw = max(1, int(h) // scale), max(1, int(w) // scale)
        small = rng.randn(sh, sw).astype(np.float32)
        smin, smax = float(small.min()), float(small.max())
        arr = cv2.resize(small, (int(w), int(h)), interpolation=cv2.INTER_LINEAR)
        arr = arr * (smax - smin) + smin
        result += arr * weight
    rmin, rmax = float(result.min()), float(result.max())
    if rmax > rmin:
        result = (result - rmin) / (rmax - rmin) * 2.0 - 1.0
    return result


def perlin_multi_octave(shape, octaves=4, persistence=0.5, lacunarity=2.0, seed=42):
    """Multi-octave Perlin noise for organic, spatially coherent textures.

    Unlike random noise, Perlin has spatial coherence â€” nearby pixels are correlated.
    Use for: wood grain, marble veining, organic surface variation.
    """
    h, w = shape
    result = np.zeros((h, w), dtype=np.float32)
    amplitude = 1.0
    frequency = 4
    max_value = 0.0

    for i in range(octaves):
        res_y = min(frequency, h)
        res_x = min(frequency, w)
        pad_h = int(np.ceil(h / res_y)) * res_y
        pad_w = int(np.ceil(w / res_x)) * res_x
        try:
            noise = _generate_perlin_2d((pad_h, pad_w), (res_y, res_x), seed=seed + i * 31)
            noise = noise[:h, :w]
        except Exception:
            np.random.seed(seed + i * 31)
            noise = np.random.randn(h, w).astype(np.float32)
        result += noise * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency = int(frequency * lacunarity)

    if max_value > 0:
        result = result / max_value
    return result


def _generate_perlin_2d(shape, res, seed=None):
    """Single-octave 2D Perlin noise. Internal â€” use perlin_multi_octave instead."""
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


# Public alias for legacy callers (e.g. shokker_engine_v2 via engine.utils)
generate_perlin_noise_2d = _generate_perlin_2d


# ================================================================
# COLOR CONVERSION
# ================================================================

def hsv_to_rgb_vec(h, s, v):
    """Vectorized HSV â†’ RGB conversion (numpy arrays).
    All inputs 0-1. Returns (r, g, b) as float arrays 0-1.
    """
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


def rgb_to_hsv_array(scheme):
    """Convert RGB float [0,1] array to HSV float [0,1] array.
    Input shape: (h, w, 3). Output shape: (h, w, 3) [H, S, V all 0-1].
    """
    r, g, b = scheme[:,:,0], scheme[:,:,1], scheme[:,:,2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc

    hue = np.zeros_like(r)
    mask_r = (maxc == r) & (delta > 0)
    mask_g = (maxc == g) & (delta > 0)
    mask_b = (maxc == b) & (delta > 0)
    hue[mask_r] = (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6) / 6.0
    hue[mask_g] = (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2) / 6.0
    hue[mask_b] = (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4) / 6.0

    sat = np.zeros_like(r)
    sat[maxc > 0] = delta[maxc > 0] / maxc[maxc > 0]
    val = maxc

    return np.stack([hue, sat, val], axis=-1)


# ================================================================
# INTENSITY PRESETS
# 100% = 1.0 for all channels. Channel-specific scaling via _INTENSITY_SCALE.
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

# How much to scale each channel at 100% intensity.
# Baked in so users never have to think about it â€” 100% = full effect.
_INTENSITY_SCALE = {
    "paint":  1.50,  # paint functions need up to 1.5x for full effect
    "spec":   2.00,  # spec modulation needs 2.0x for visible texture
    "bright": 0.15,  # brightness boost caps at 0.15 (7-15% brightness add)
}


# ================================================================
# COLOR ANALYSIS â€” how zones find their pixels
# ================================================================

def analyze_paint_colors(scheme):
    """Analyze paint image and return HSV stats for zone matching.
    Used internally before zone masking â€” logs color breakdown to console.
    """
    hsv = rgb_to_hsv_array(scheme)
    brightness = scheme[:,:,0]*0.299 + scheme[:,:,1]*0.587 + scheme[:,:,2]*0.114
    stats = {
        "hue": hsv[:,:,0], "sat": hsv[:,:,1], "val": hsv[:,:,2],
        "brightness": brightness, "rgb": scheme,
    }
    h, w = scheme.shape[:2]
    total_pixels = h * w
    bright_pct = np.sum(brightness > 0.85) / total_pixels * 100
    dark_pct = np.sum(brightness < 0.15) / total_pixels * 100
    saturated_pct = np.sum(hsv[:,:,1] > 0.3) / total_pixels * 100
    print(f"    Paint Analysis:")
    print(f"      Bright (>85%): {bright_pct:.1f}%  Dark (<15%): {dark_pct:.1f}%  Saturated: {saturated_pct:.1f}%")
    return stats


def build_zone_mask(scheme, stats, selector, blur_radius=3):
    """Build a float32 zone mask [0,1] from a color selector dict.

    Selector types â€” choose the one that matches your zone:
        {"color_rgb": [R, G, B], "tolerance": 30}   â†’ exact color match with soft falloff
        {"color_range": {"r": [lo,hi], "g": [lo,hi], "b": [lo,hi]}}  â†’ RGB range box
        {"hue_range": [lo_deg, hi_deg], "sat_min": 0.2, "val_min": 0.1}  â†’ HSV hue
        {"brightness": {"min": 0.0, "max": 0.3}}    â†’ lightness range
        {"saturation": {"min": 0.5, "max": 1.0}}    â†’ saturation range
        {"all_painted": True}    â†’ everything with color or darkness (not template)
        {"remainder": True}      â†’ everything not claimed by other zones

    Returns float32 (h,w) array, 1.0 = fully in zone, 0.0 = not in zone.
    """
    h, w = scheme.shape[:2]
    mask = np.zeros((h, w), dtype=np.float32)

    if "color_rgb" in selector:
        target = np.array(selector["color_rgb"], dtype=np.float32) / 255.0
        tolerance = selector.get("tolerance", 30) / 255.0
        dist = np.sqrt(
            (scheme[:,:,0] - target[0])**2 +
            (scheme[:,:,1] - target[1])**2 +
            (scheme[:,:,2] - target[2])**2
        )
        mask = np.clip(1.0 - dist / (tolerance * np.sqrt(3)), 0, 1)

    elif "color_range" in selector:
        cr = selector["color_range"]
        r_lo, r_hi = cr.get("r", [0, 255])
        g_lo, g_hi = cr.get("g", [0, 255])
        b_lo, b_hi = cr.get("b", [0, 255])
        rgb255 = (scheme * 255).astype(np.float32)
        mask = (
            (rgb255[:,:,0] >= r_lo) & (rgb255[:,:,0] <= r_hi) &
            (rgb255[:,:,1] >= g_lo) & (rgb255[:,:,1] <= g_hi) &
            (rgb255[:,:,2] >= b_lo) & (rgb255[:,:,2] <= b_hi)
        ).astype(np.float32)

    elif "hue_range" in selector:
        hue_lo, hue_hi = selector["hue_range"]
        sat_min = selector.get("sat_min", 0.15)
        sat_max = selector.get("sat_max", 1.0)
        val_min = selector.get("val_min", 0.05)
        val_max = selector.get("val_max", 1.0)
        hue_deg = stats["hue"] * 360.0
        if hue_lo > hue_hi:  # wraps through 0Â° (reds)
            hue_match = (hue_deg >= hue_lo) | (hue_deg <= hue_hi)
        else:
            hue_match = (hue_deg >= hue_lo) & (hue_deg <= hue_hi)
        mask = (
            hue_match &
            (stats["sat"] >= sat_min) & (stats["sat"] <= sat_max) &
            (stats["val"] >= val_min) & (stats["val"] <= val_max)
        ).astype(np.float32)

    elif "brightness" in selector:
        br = selector["brightness"]
        bmin, bmax = br.get("min", 0.0), br.get("max", 1.0)
        brightness = stats["brightness"]
        mask = ((brightness >= bmin) & (brightness <= bmax)).astype(np.float32)
        edge = 0.05
        mask = np.where(brightness < bmin + edge, np.clip((brightness - bmin) / edge, 0, 1), mask)
        mask = np.where(brightness > bmax - edge, np.clip((bmax - brightness) / edge, 0, 1), mask)

    elif "saturation" in selector:
        sr = selector["saturation"]
        smin, smax = sr.get("min", 0.0), sr.get("max", 1.0)
        mask = ((stats["sat"] >= smin) & (stats["sat"] <= smax)).astype(np.float32)

    elif selector.get("all_painted"):
        mask = ((stats["sat"] > 0.08) | (stats["brightness"] < 0.25)).astype(np.float32)

    elif selector.get("remainder"):
        mask = np.ones((h, w), dtype=np.float32)  # handled post-loop

    # Soft edges via Gaussian blur
    if blur_radius > 0 and np.any(mask > 0):
        mask = gaussian_filter(mask, sigma=blur_radius)

    return mask


# ================================================================
# NATURAL LANGUAGE COLOR WORD MAPPING
# ================================================================

COLOR_WORD_MAP = {
    # Hue-based
    "red":      {"hue_range": [340, 20],  "sat_min": 0.2},
    "orange":   {"hue_range": [15, 45],   "sat_min": 0.2},
    "yellow":   {"hue_range": [45, 70],   "sat_min": 0.2},
    "gold":     {"hue_range": [35, 55],   "sat_min": 0.25, "val_min": 0.4},
    "green":    {"hue_range": [70, 160],  "sat_min": 0.15},
    "lime":     {"hue_range": [70, 100],  "sat_min": 0.3},
    "teal":     {"hue_range": [160, 200], "sat_min": 0.2},
    "cyan":     {"hue_range": [170, 200], "sat_min": 0.2},
    "blue":     {"hue_range": [200, 260], "sat_min": 0.15},
    "navy":     {"hue_range": [210, 250], "sat_min": 0.2,  "val_max": 0.4},
    "purple":   {"hue_range": [260, 310], "sat_min": 0.15},
    "magenta":  {"hue_range": [290, 330], "sat_min": 0.2},
    "pink":     {"hue_range": [310, 350], "sat_min": 0.15},
    "maroon":   {"hue_range": [340, 15],  "sat_min": 0.2,  "val_max": 0.4},
    # Achromatic
    "white":    {"brightness": {"min": 0.85, "max": 1.0}},
    "light":    {"brightness": {"min": 0.7,  "max": 1.0}},
    "gray":     {"saturation": {"min": 0.0, "max": 0.1}},
    "grey":     {"saturation": {"min": 0.0, "max": 0.1}},
    "dark":     {"brightness": {"min": 0.0, "max": 0.25}},
    "black":    {"brightness": {"min": 0.0, "max": 0.2}},
    "silver":   {"brightness": {"min": 0.5, "max": 0.85}, "saturation": {"min": 0.0, "max": 0.1}},
    # Catchalls
    "everything": {"all_painted": True},
    "body":       {"all_painted": True},
    "all":        {"all_painted": True},
    "remaining":  {"remainder": True},
    "rest":       {"remainder": True},
    "other":      {"remainder": True},
}


def parse_color_description(desc):
    """Parse a natural language color word into a zone selector dict.

    Examples:
        "blue"        â†’ hue_range [200, 260]
        "dark blue"   â†’ hue_range [200, 260] + val_max 0.4
        "#FF0000"     â†’ color_rgb [255, 0, 0]
        "rgb(255,0,0)"â†’ color_rgb [255, 0, 0]
        "everything"  â†’ all_painted: True
    """
    desc = desc.lower().strip()

    if desc.startswith("#") and len(desc) == 7:
        r = int(desc[1:3], 16); g = int(desc[3:5], 16); b = int(desc[5:7], 16)
        return {"color_rgb": [r, g, b], "tolerance": 40}

    if desc.startswith("rgb("):
        parts = desc.replace("rgb(", "").replace(")", "").split(",")
        if len(parts) == 3:
            return {"color_rgb": [int(p.strip()) for p in parts], "tolerance": 40}

    words = desc.replace("/", " ").replace("-", " ").split()
    _skip = {"the","a","an","areas","area","parts","part","panels","panel","accents","accent",
              "stripe","stripes","trim","decals","decal","logos","logo","numbers","number",
              "hood","roof","bumper","skirt","fender","door","doors","side","front","rear",
              "back","top","bottom","base","main","sponsors","sponsor"}

    selector = None
    for word in words:
        if word in _skip:
            continue
        if word in COLOR_WORD_MAP:
            selector = dict(COLOR_WORD_MAP[word])
            break

    if selector is None:
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
# ZONE COLOR SAMPLING â€” for adaptive color shift / pipeline
# ================================================================

def _sample_zone_color(paint, mask):
    """Sample the dominant color in a masked zone.

    Returns (hue, sat, val) as floats in 0-1 range.
    Used by adaptive color shift and pipeline zone sampling.
    """
    strong = mask > 0.5
    if np.sum(strong) < 100:
        return 0.0, 0.0, 0.6
    r_vals = paint[:,:,0][strong]
    g_vals = paint[:,:,1][strong]
    b_vals = paint[:,:,2][strong]
    r_med = float(np.median(r_vals))
    g_med = float(np.median(g_vals))
    b_med = float(np.median(b_vals))
    maxc = max(r_med, g_med, b_med)
    minc = min(r_med, g_med, b_med)
    delta = maxc - minc
    val = maxc
    sat = delta / maxc if maxc > 0 else 0.0
    if delta < 0.001:
        hue = 0.0
    elif maxc == r_med:
        hue = (((g_med - b_med) / delta) % 6) / 6.0
    elif maxc == g_med:
        hue = (((b_med - r_med) / delta) + 2) / 6.0
    else:
        hue = (((r_med - g_med) / delta) + 4) / 6.0
    return float(hue), float(sat), float(val)


# ================================================================
# ARRAY HELPERS â€” resize, tile, crop, rotate (used by compose)
# ================================================================

def _resize_array(arr, target_h, target_w):
    """Resize a 2D float32 array to target dimensions using cv2."""
    if arr.shape[0] == target_h and arr.shape[1] == target_w:
        return arr
    return cv2.resize(arr.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_LINEAR)


def _tile_fractional(arr, factor, target_h, target_w):
    """Tile a 2D array by a fractional factor and resize to target dims."""
    import math
    h, w = arr.shape[:2]
    reps = min(10, max(2, int(math.ceil(factor))))
    tiled = np.tile(arr, (reps, reps))
    crop_h = min(tiled.shape[0], max(4, int(round(h * factor))))
    crop_w = min(tiled.shape[1], max(4, int(round(w * factor))))
    tiled = tiled[:crop_h, :crop_w]
    return _resize_array(tiled, target_h, target_w)


def _crop_center_array(arr, crop_frac, target_h, target_w):
    """Crop the center portion of a 2D array, then resize to target dims."""
    h, w = arr.shape[:2]
    ch = max(4, int(h / crop_frac))
    cw = max(4, int(w / crop_frac))
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    cropped = arr[y0:y0+ch, x0:x0+cw]
    if cropped.shape[0] == target_h and cropped.shape[1] == target_w:
        return cropped
    return _resize_array(cropped, target_h, target_w)


def _rotate_array(arr, angle, fill_value=0.0):
    """Rotate a 2D numpy array by angle (degrees) around center."""
    if angle == 0 or angle == 360:
        return arr
    arr_min, arr_max = float(arr.min()), float(arr.max())
    val_range = arr_max - arr_min
    if val_range < 1e-8:
        return arr
    norm = ((arr - arr_min) / val_range * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(norm)
    fill_norm = max(0, min(255, int(((fill_value - arr_min) / val_range * 255))))
    rotated = img.rotate(angle, resample=Image.BILINEAR, expand=False, fillcolor=fill_norm)
    return np.array(rotated).astype(np.float32) / 255.0 * val_range + arr_min


def _rotate_single_array(arr, angle, shape):
    """Rotate a single 2D array by angle degrees."""
    if angle == 0 or angle == 360:
        return arr
    rotated = _rotate_array(arr, angle, fill_value=0.0)
    if rotated.shape[0] != shape[0] or rotated.shape[1] != shape[1]:
        rotated = _resize_array(rotated, shape[0], shape[1])
    return rotated


def _scale_pattern_output(pv, tex, scale, shape):
    """Apply scale to pattern_val and all associated tex arrays."""
    h, w = shape
    if scale < 1.0:
        factor = 1.0 / scale
        pv = _tile_fractional(pv, factor, h, w)
        for k in ("R_extra", "M_extra"):
            if k in tex and isinstance(tex[k], np.ndarray):
                tex[k] = _tile_fractional(tex[k], factor, h, w)
        if isinstance(tex.get("CC"), np.ndarray):
            tex["CC"] = _tile_fractional(tex["CC"], factor, h, w)
    else:
        pv = _crop_center_array(pv, scale, h, w)
        for k in ("R_extra", "M_extra"):
            if k in tex and isinstance(tex[k], np.ndarray):
                tex[k] = _crop_center_array(tex[k], scale, h, w)
        if isinstance(tex.get("CC"), np.ndarray):
            tex["CC"] = _crop_center_array(tex["CC"], scale, h, w)
    return pv, tex


def _rotate_pattern_tex(tex, angle, shape):
    """Rotate all spatial arrays in a texture output dict by the given angle."""
    if angle == 0 or angle == 360:
        return tex
    tex["pattern_val"] = _rotate_array(tex["pattern_val"], angle, fill_value=0.0)
    for k in ("R_extra", "M_extra"):
        if k in tex and isinstance(tex[k], np.ndarray):
            tex[k] = _rotate_array(tex[k], angle, fill_value=0.0)
    if isinstance(tex.get("CC"), np.ndarray):
        tex["CC"] = _rotate_array(tex["CC"], angle, fill_value=0.0)
    return tex


def _compute_zone_auto_scale(zone_mask, shape):
    """Compute an auto-scale factor for patterns based on zone mask coverage area."""
    h, w = shape
    total_area = h * w
    if total_area == 0:
        return 1.0
    rows = np.any(zone_mask > 0.1, axis=1)
    cols = np.any(zone_mask > 0.1, axis=0)
    if not np.any(rows) or not np.any(cols):
        return 1.0
    r_min, r_max = np.where(rows)[0][[0, -1]]
    c_min, c_max = np.where(cols)[0][[0, -1]]
    bbox_area = (r_max - r_min + 1) * (c_max - c_min + 1)
    area_ratio = bbox_area / total_area
    if area_ratio > 0.6:
        return 1.0
    return max(0.15, min(1.0, area_ratio ** 0.5))
