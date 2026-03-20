"""
engine/render.py - Generic Finish Render Dispatch
==================================================
render_generic_finish - handles grad_*, gradm_*, grad3_*, ghostg_*, cs_duo_*, clr_*, mc_*.
Extracted from shokker_engine_v2. Uses PATTERN_REGISTRY (lazy) for ghost gradients.

Image-based patterns: _load_image_pattern loads grayscale PNG, caches by (path, shape),
applies tile/crop/rotate via engine.core helpers.
"""
import os
import numpy as np

# Cache for image patterns: (abs_path, shape) -> float32 (H,W) 0-1
_image_pattern_cache = {}


def _resize_image_pattern(arr, target_h, target_w):
    """Resize pattern array to target size using LANCZOS for better car-render quality."""
    from PIL import Image
    if arr.shape[0] == target_h and arr.shape[1] == target_w:
        return arr
    mn, mx = float(arr.min()), float(arr.max())
    rng = mx - mn + 1e-8
    u8 = (np.clip((arr - mn) / rng, 0, 1) * 255).astype(np.uint8)
    img = Image.fromarray(u8)
    resized = img.resize((target_w, target_h), Image.LANCZOS)
    out = np.array(resized).astype(np.float32) / 255.0
    return (out * rng + mn).astype(np.float32)


def _get_pattern_root():
    """Root dir for assets/patterns (same as server so dev + Electron find files)."""
    try:
        from config import CFG
        if getattr(CFG, "ROOT_DIR", None) and os.path.isdir(CFG.ROOT_DIR):
            return CFG.ROOT_DIR
    except Exception:
        pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_image_pattern(image_path, shape, scale=1.0, rotation=0.0):
    """Load PNG/JPG pattern from image_path (relative to server root), return (H,W) float32 0-1.
    User images live in assets/patterns/<category>/ - NEVER overwrite these.
    If missing, falls back to assets/patterns/_placeholders/<stem>_placeholder.png.
    Cached by (abs_path, shape, scale, rotation). Returns None on failure.
    Opaque images with low luminance spread get a contrast boost so Pattern-Reactive
    (and pattern_vivid) show clear diversity, like patterns that have transparency."""
    if not image_path or not isinstance(shape, (tuple, list)) or len(shape) < 2:
        return None
    root = _get_pattern_root()
    abs_path = os.path.normpath(os.path.join(root, image_path.replace("/", os.sep)))
    if not os.path.isfile(abs_path):
        stem = os.path.splitext(os.path.basename(image_path))[0]
        fallback = os.path.normpath(os.path.join(root, "assets", "patterns", "_placeholders", f"{stem}_placeholder.png"))
        if os.path.isfile(fallback):
            abs_path = fallback
        else:
            import logging
            logging.getLogger("shokker_v5").warning(
                f"Pattern image not found: {abs_path!r} (root={root!r}); placeholder missing: {fallback!r}"
            )
            return None
    h, w = int(shape[0]), int(shape[1])
    use_scale = max(0.1, min(10.0, float(scale)))
    use_rot = float(rotation) % 360.0
    cache_key = (abs_path, h, w, use_scale, use_rot)
    if cache_key in _image_pattern_cache:
        return _image_pattern_cache[cache_key]
    try:
        from PIL import Image
        from engine.core import _tile_fractional, _crop_center_array, _rotate_single_array
        img_rgba = Image.open(abs_path).convert("RGBA")
        rgba = np.array(img_rgba, dtype=np.float32) / 255.0
        rgb = rgba[:, :, :3]
        alpha = rgba[:, :, 3]
        # If the PNG actually uses transparency, treat alpha as the primary mask driver.
        # This lets upgraded transparent assets behave like clean pattern masks, while
        # keeping opaque black-background user PNGs working through luminance fallback.
        lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]).astype(np.float32)
        has_transparency = float(alpha.min()) < 0.999
        if has_transparency:
            arr = np.clip(np.maximum(lum, alpha), 0.0, 1.0).astype(np.float32)
        else:
            arr = lum
        if arr.ndim != 2:
            return None
        ih, iw = arr.shape[0], arr.shape[1]
        
        # STEP 1: Always normalize to canvas size first (the "1.0x" baseline).
        # Small images get tiled to fill; large images get shrunk to fit.
        if ih < h or iw < w:
            n_h = max(1, (h + ih - 1) // ih)
            n_w = max(1, (w + iw - 1) // iw)
            arr = np.tile(arr, (n_h, n_w))[:h, :w]
        elif ih > h or iw > w:
            arr = _resize_image_pattern(arr, h, w)
        # arr is now exactly (h, w) — the "1.0x" view.

        # STEP 2: Apply scale relative to the normalized baseline.
        # scale < 1.0 = shrink motifs (more repetitions); scale > 1.0 = zoom in (bigger).
        if abs(use_scale - 1.0) > 0.01:
            if use_scale < 1.0:
                # Shrink the normalized pattern, then tile to fill canvas
                tile_h = max(4, int(h * use_scale))
                tile_w = max(4, int(w * use_scale))
                small = _resize_image_pattern(arr, tile_h, tile_w)
                n_h = max(1, (h + tile_h - 1) // tile_h)
                n_w = max(1, (w + tile_w - 1) // tile_w)
                arr = np.tile(small, (n_h, n_w))[:h, :w]
            else:
                # Zoom in: crop center of the normalized pattern
                arr = _crop_center_array(arr, use_scale, h, w)
                if arr.shape[0] != h or arr.shape[1] != w:
                    arr = _resize_image_pattern(arr, h, w)
        if arr.shape[0] != h or arr.shape[1] != w:
            arr = _resize_image_pattern(arr, h, w)
        if abs(use_rot) > 0.5:
            arr = _rotate_single_array(arr, use_rot, (h, w))
        pmin, pmax = float(arr.min()), float(arr.max())
        if pmax - pmin > 1e-8:
            arr = (arr - pmin) / (pmax - pmin)
        else:
            arr = np.zeros_like(arr)
        # For opaque images (no alpha): harden mask so dark background -> 0, light pattern -> 1,
        # matching transparent PNGs (Biomechanical-style). Ensures PATTERN POP + HARDEN only color the pattern.
        if not has_transparency:
            arr = np.clip((arr.astype(np.float32) - 0.25) / 0.5, 0.0, 1.0).astype(np.float32)
        # For opaque images with low luminance spread, boost contrast so Pattern-Reactive
        # gets clear light/dark areas (like Biomechanical/Optical Illusion with transparency).
        if not has_transparency:
            std = float(np.std(arr))
            if std < 0.28:
                arr = np.clip((arr - 0.5) * 1.8 + 0.5, 0.0, 1.0).astype(np.float32)
        _image_pattern_cache[cache_key] = arr.astype(np.float32)
        return _image_pattern_cache[cache_key]
    except Exception:
        return None

def _load_color_image_pattern(image_path, shape, scale=1.0, rotation=0.0):
    """Load PNG/JPG pattern from image_path and retain RGB colors. Returns (H,W,4) float32 0-1 RGBA array."""
    if not image_path or not isinstance(shape, (tuple, list)) or len(shape) < 2:
        return None
    root = _get_pattern_root()
    abs_path = os.path.normpath(os.path.join(root, image_path.replace("/", os.sep)))
    if not os.path.isfile(abs_path):
        return None
    
    h, w = int(shape[0]), int(shape[1])
    use_scale = max(0.1, min(10.0, float(scale)))
    use_rot = float(rotation) % 360.0
    cache_key = (abs_path, h, w, use_scale, use_rot, "color")
    if cache_key in _image_pattern_cache:
        return _image_pattern_cache[cache_key]
        
    try:
        from PIL import Image
        img_rgba = Image.open(abs_path).convert("RGBA")
        rgba = np.array(img_rgba, dtype=np.float32) / 255.0
        
        ih, iw = rgba.shape[0], rgba.shape[1]
        
        # At scale=1.0: fit image to (h,w). If smaller: tile to fill; if larger: scale down to fit canvas (e.g. 4K -> 2048x2048).
        if abs(use_scale - 1.0) <= 0.01:
            if ih < h or iw < w:
                n_h = max(1, (h + ih - 1) // ih)
                n_w = max(1, (w + iw - 1) // iw)
                rgba = np.tile(rgba, (n_h, n_w, 1))[:h, :w, :]
            elif ih > h or iw > w:
                if rgba.shape[0] != h or rgba.shape[1] != w:
                    import cv2
                    rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
        else:
            # Match original grayscale logic:
            # 1. Expand drawing canvas by 1/scale so we can tile it or crop from it
            gen_h, gen_w = max(4, int(h / use_scale)), max(4, int(w / use_scale))
            
            if use_scale < 1.0:
                # scale < 1.0: tile in expanded canvas
                n_h = max(1, (gen_h + ih - 1) // ih)
                n_w = max(1, (gen_w + iw - 1) // iw)
                rgba = np.tile(rgba, (n_h, n_w, 1))[:gen_h, :gen_w, :]
            else:
                # scale > 1.0: crop from center of image array (treating image as repeating pattern first if smaller)
                if ih < gen_h or iw < gen_w:
                    n_h = max(1, (gen_h + ih - 1) // ih)
                    n_w = max(1, (gen_w + iw - 1) // iw)
                    rgba = np.tile(rgba, (n_h, n_w, 1))
                curr_h, curr_w = rgba.shape[0], rgba.shape[1]
                y0, x0 = max(0, (curr_h - gen_h) // 2), max(0, (curr_w - gen_w) // 2)
                rgba = rgba[y0:y0+gen_h, x0:x0+gen_w, :]
                
            # Resize the scaled canvas back down/up to actual render window shape
            if rgba.shape[0] != h or rgba.shape[1] != w:
                import cv2
                rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA if use_scale < 1.0 else cv2.INTER_LINEAR)
        
        if abs(use_rot) > 0.5:
            from engine.core import _rotate_single_array
            for ch in range(4):
                rgba[:, :, ch] = _rotate_single_array(rgba[:, :, ch], use_rot, (h, w))
        
        # Alpha handling for image patterns:
        # - If fully opaque source: synthesize alpha from luminance (black -> transparent).
        # - For patternexamples assets: also key out near-black even when an alpha channel exists,
        #   so dark baked backgrounds (e.g. Biomechanical-style plates) don't sit on top of the base.
        alpha = rgba[:, :, 3]
        lum = 0.299 * rgba[:, :, 0] + 0.587 * rgba[:, :, 1] + 0.114 * rgba[:, :, 2]
        if float(alpha.min()) > 0.999:  # No transparency in image
            rgba[:, :, 3] = np.clip(lum * 1.5, 0, 1)
        elif "patternexamples" in image_path.replace("\\", "/").lower():
            # Soft black-key: keep details, but remove deep black backing.
            dark_key = np.clip((lum - 0.08) / 0.35, 0.0, 1.0).astype(np.float32)
            rgba[:, :, 3] = np.clip(alpha * dark_key, 0.0, 1.0)
            
        _image_pattern_cache[cache_key] = rgba
        return _image_pattern_cache[cache_key]
    except Exception as e:
        print(f"Error loading color image pattern: {e}")
        return None


def _hex_to_rgb_float(hex_str):
    """Convert '#RRGGBB' or 'RRGGBB' hex to (r, g, b) floats 0-1. Tolerates missing #."""
    if not hex_str:
        return (0.5, 0.5, 0.5)
    s = hex_str.strip()
    if len(s) >= 7 and s[0] == '#':
        s = s[1:7]
    elif len(s) >= 6:
        s = s[:6]
    else:
        return (0.5, 0.5, 0.5)
    try:
        r = int(s[0:2], 16) / 255.0
        g = int(s[2:4], 16) / 255.0
        b = int(s[4:6], 16) / 255.0
        return (r, g, b)
    except (ValueError, TypeError):
        return (0.5, 0.5, 0.5)


def _get_grad_direction(finish_id):
    """Determine gradient direction from finish ID suffix."""
    if finish_id.endswith('vortex') or 'radial' in finish_id.lower():
        return 'radial'
    elif finish_id.endswith('_diag'):
        return 'diagonal'
    elif finish_id.endswith('_h'):
        return 'horizontal'
    return 'vertical'


def _generic_grad_spec(shape, mask, seed, sm):
    """Generic gradient spec: moderate metallic, low roughness, clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(80 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(40 * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def _generic_cs_spec(shape, mask, seed, sm):
    """Generic color-shift spec: high metallic for iridescence."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(200 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(25 * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def _generic_solid_spec_fn(shape, mask, seed, sm, mat_key):
    """Generic solid spec based on material key extracted from finish ID."""
    MATS = {
        'gloss': (5, 20, 16), 'matte': (5, 180, 0),
        'satin': (15, 90, 8), 'metallic': (200, 50, 16),
        'pearl': (120, 35, 16), 'candy': (200, 15, 16),
        'chrome': (250, 3, 0), 'flat': (0, 230, 0),
    }
    M, R, CC = MATS.get(mat_key, (5, 20, 16))
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = CC
    spec[:, :, 3] = 255
    return spec


def _apply_generic_gradient(paint, shape, mask, c1, c2, direction, seed, pm, bb, mirror=False, rotation=0):
    """Apply a 2-color gradient to paint. Zone-aware: maps gradient to zone bbox."""
    h, w = shape
    blend = 0.85 * pm
    y, x = np.mgrid[0:h, 0:w]
    rows_active = np.any(mask > 0.1, axis=1)
    cols_active = np.any(mask > 0.1, axis=0)
    if np.any(rows_active) and np.any(cols_active):
        r_min, r_max = np.where(rows_active)[0][[0, -1]]
        c_min, c_max = np.where(cols_active)[0][[0, -1]]
        bbox_h = max(1, r_max - r_min + 1)
        bbox_w = max(1, c_max - c_min + 1)
    else:
        r_min, c_min = 0, 0
        bbox_h, bbox_w = h, w
    yf = (y.astype(np.float32) - r_min) / max(bbox_h - 1, 1)
    xf = (x.astype(np.float32) - c_min) / max(bbox_w - 1, 1)
    if direction == 'radial':
        cx, cy = 0.5, 0.5
        dist = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2) * 1.414
        t = np.clip(dist, 0, 1)
    else:
        if direction == 'horizontal':
            base_angle = 90.0
        elif direction == 'diagonal':
            base_angle = 45.0
        else:
            base_angle = 0.0
        total_angle = base_angle + float(rotation)
        rad = np.deg2rad(total_angle)
        t = np.cos(rad) * yf + np.sin(rad) * xf
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
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint


def _apply_generic_3color_gradient(paint, shape, mask, c1, c2, c3, direction, seed, pm, bb, rotation=0):
    """Apply a 3-color gradient (c1 -> c2 -> c3). Zone-aware: maps to zone bbox."""
    h, w = shape
    blend = 0.85 * pm
    y, x = np.mgrid[0:h, 0:w]
    rows_active = np.any(mask > 0.1, axis=1)
    cols_active = np.any(mask > 0.1, axis=0)
    if np.any(rows_active) and np.any(cols_active):
        r_min, r_max = np.where(rows_active)[0][[0, -1]]
        c_min, c_max = np.where(cols_active)[0][[0, -1]]
        bbox_h = max(1, r_max - r_min + 1)
        bbox_w = max(1, c_max - c_min + 1)
    else:
        r_min, c_min = 0, 0
        bbox_h, bbox_w = h, w
    yf = (y.astype(np.float32) - r_min) / max(bbox_h - 1, 1)
    xf = (x.astype(np.float32) - c_min) / max(bbox_w - 1, 1)
    if direction == 'horizontal':
        base_angle = 90.0
    elif direction == 'diagonal':
        base_angle = 45.0
    else:
        base_angle = 0.0
    total_angle = base_angle + float(rotation)
    rad = np.deg2rad(total_angle)
    t = np.cos(rad) * yf + np.sin(rad) * xf
    t_min, t_max = t.min(), t.max()
    if t_max - t_min > 1e-6:
        t = (t - t_min) / (t_max - t_min)
    else:
        t = np.zeros_like(t)
    seg1 = t < 0.5
    t1 = np.clip(t * 2, 0, 1)
    t2 = np.clip((t - 0.5) * 2, 0, 1)
    r = np.where(seg1, c1[0] + (c2[0] - c1[0]) * t1, c2[0] + (c3[0] - c2[0]) * t2)
    g = np.where(seg1, c1[1] + (c2[1] - c1[1]) * t1, c2[1] + (c3[1] - c2[1]) * t2)
    b = np.where(seg1, c1[2] + (c2[2] - c1[2]) * t1, c2[2] + (c3[2] - c2[2]) * t2)
    r += bb
    g += bb
    b += bb
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint


def _apply_generic_colorshift(paint, shape, mask, c1, c2, seed, pm, bb):
    """Apply angle-dependent color shift. Zone-aware: centers on zone bbox."""
    h, w = shape
    blend = 0.85 * pm
    y, x = np.mgrid[0:h, 0:w]
    rows_active = np.any(mask > 0.1, axis=1)
    cols_active = np.any(mask > 0.1, axis=0)
    if np.any(rows_active) and np.any(cols_active):
        r_min, r_max = np.where(rows_active)[0][[0, -1]]
        c_min, c_max = np.where(cols_active)[0][[0, -1]]
        bbox_h = max(1, r_max - r_min + 1)
        bbox_w = max(1, c_max - c_min + 1)
    else:
        r_min, c_min = 0, 0
        bbox_h, bbox_w = h, w
    yf = (y.astype(np.float32) - r_min) / max(bbox_h - 1, 1)
    xf = (x.astype(np.float32) - c_min) / max(bbox_w - 1, 1)
    angle = np.arctan2(yf - 0.5, xf - 0.5)
    shift = (np.sin(angle * 2.0 + seed * 0.1) + 1) * 0.5
    r = c1[0] * (1 - shift) + c2[0] * shift
    g = c1[1] * (1 - shift) + c2[1] * shift
    b = c1[2] * (1 - shift) + c2[2] * shift
    r += bb
    g += bb
    b += bb
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint


def _apply_generic_solid(paint, shape, mask, c1, seed, pm, bb):
    """Apply a flat solid color."""
    blend = 0.85 * pm
    r, g, b = c1[0] + bb, c1[1] + bb, c1[2] + bb
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint


def render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed, sm, pm, bb, rotation=0):
    """Generic fallback renderer. Returns (zone_spec, paint) or (None, paint) if can't handle.
    Handles grad_*, gradm_*, grad3_*, ghostg_*, cs_duo_*, clr_*, mc_*.
    """
    fc = zone.get("finish_colors")
    if not fc:
        return None, paint
    c1 = _hex_to_rgb_float(fc.get("c1"))
    c2 = _hex_to_rgb_float(fc.get("c2")) if fc.get("c2") else c1
    c3 = _hex_to_rgb_float(fc.get("c3")) if fc.get("c3") else None
    direction = _get_grad_direction(finish_name)

    if finish_name.startswith('gradm_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, mirror=True, rotation=rotation)
    elif finish_name.startswith('grad3_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        if c3:
            paint = _apply_generic_3color_gradient(paint, shape, zone_mask, c1, c2, c3, direction, seed, pm, bb, rotation=rotation)
        else:
            paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation)
    elif finish_name.startswith('ghostg_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, 'vertical', seed, pm, bb, rotation=rotation)
        ghost_pat = fc.get("ghost") if fc else None
        applied = False
        if ghost_pat:
            from engine.pattern_registry_data import PATTERN_REGISTRY
            if ghost_pat in PATTERN_REGISTRY:
                pat_entry = PATTERN_REGISTRY[ghost_pat]
                tex_fn = pat_entry["texture_fn"]
                try:
                    tex_result = tex_fn(shape, zone_mask, seed + 9999, sm)
                    if isinstance(tex_result, dict):
                        pattern_val = tex_result.get("pattern_val", np.zeros(shape, dtype=np.float32))
                    else:
                        pattern_val = tex_result
                    pmin, pmax = float(pattern_val.min()), float(pattern_val.max())
                    if pmax - pmin > 1e-8:
                        pattern_norm = (pattern_val - pmin) / (pmax - pmin)
                    else:
                        pattern_norm = np.zeros_like(pattern_val)
                    ghost_strength = 0.10 * pm
                    for ch in range(3):
                        paint[:, :, ch] = np.clip(
                            paint[:, :, ch] - pattern_norm * ghost_strength * zone_mask,
                            0, 1
                        )
                        paint[:, :, ch] = np.clip(
                            paint[:, :, ch] + (1.0 - pattern_norm) * ghost_strength * 0.3 * zone_mask,
                            0, 1
                        )
                    applied = True
                except Exception as e:
                    print(f"[Ghost Gradient] Pattern '{ghost_pat}' render failed: {e}")
        if not applied:
            h, w = shape
            rng = np.random.RandomState(seed + 7777)
            noise = rng.randn(h, w).astype(np.float32) * 0.05
            for ch in range(3):
                paint[:, :, ch] = np.clip(paint[:, :, ch] + noise * zone_mask, 0, 1)
    elif finish_name.startswith('cs_duo_'):
        zone_spec = _generic_cs_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_colorshift(paint, shape, zone_mask, c1, c2, seed, pm, bb)
    elif finish_name.startswith('grad_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation)
    elif finish_name.startswith('clr_'):
        parts = finish_name.split('_')
        mat_key = parts[-1] if len(parts) >= 3 else 'gloss'
        zone_spec = _generic_solid_spec_fn(shape, zone_mask, seed, sm, mat_key)
        paint = _apply_generic_solid(paint, shape, zone_mask, c1, seed, pm, bb)
    elif finish_name.startswith('mc_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        if c3:
            paint = _apply_generic_3color_gradient(paint, shape, zone_mask, c1, c2, c3, direction, seed, pm, bb, rotation=rotation)
        else:
            paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation)
    else:
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb)

    return zone_spec, paint


__all__ = ["render_generic_finish"]
