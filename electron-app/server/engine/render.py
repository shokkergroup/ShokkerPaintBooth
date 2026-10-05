"""
engine/render.py - Generic Finish Render Dispatch
==================================================
render_generic_finish - handles grad_*, gradm_*, grad3_*, ghostg_*, cs_duo_*, clr_*, mc_*.
Extracted from shokker_engine_v2. Uses PATTERN_REGISTRY (lazy) for ghost gradients.

Image-based patterns: _load_image_pattern loads grayscale PNG, caches by (path, shape),
applies tile/crop/rotate via engine.core helpers.
"""
import os
import cv2
import numpy as np
from collections import OrderedDict
from PIL import Image

# Two-tier image pattern cache (LRU, bounded):
#   Tier 1: (abs_path,)                        -> raw float32 (H,W) 0-1 at native resolution
#   Tier 2: (abs_path, h, w, use_scale, use_rot) -> transformed float32 (H,W) ready for use
# Tier 1 avoids disk I/O on cache misses for Tier 2 (new scale/rotation of same image).
# Both tiers use OrderedDict for LRU eviction.
_IMAGE_CACHE_MAX_TIER2 = 32
_IMAGE_CACHE_MAX_TIER1 = 16
_image_pattern_cache_raw = OrderedDict()   # Tier 1
_image_pattern_cache = OrderedDict()       # Tier 2 (keyed by abs_path, h, w, scale, rot)


def clear_image_pattern_cache():
    """Clear both tiers of the image pattern cache.
    Call when resolution changes or assets are updated."""
    _image_pattern_cache.clear()
    _image_pattern_cache_raw.clear()


def _lru_get(cache, key):
    """LRU cache lookup: move key to end (most-recent) and return value, or None."""
    if key in cache:
        cache.move_to_end(key)
        return cache[key]
    return None


def _lru_put(cache, key, value, max_size):
    """LRU cache insert: add/update key, evict oldest if over max_size."""
    if key in cache:
        cache.move_to_end(key)
    cache[key] = value
    while len(cache) > max_size:
        cache.popitem(last=False)


def _opaque_pattern_photo_like(lum: np.ndarray, abs_path: str) -> bool:
    """Detect continuous-tone / photo-style opaque art (surf/skate collages, scans).

    Those assets need a **gentle** mask curve. Sparse ink-on-black masks need the
    aggressive POP hardening path instead. Transparent PNGs bypass this entirely.
    """
    ext = os.path.splitext(abs_path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        return True
    x = np.asarray(lum, dtype=np.float64).ravel()
    if x.size < 256:
        return False
    p05, p95 = np.percentile(x, (5.0, 95.0))
    spread = float(p95 - p05) + 1e-9
    lo, hi = p05 + 0.12 * spread, p95 - 0.12 * spread
    central = float(np.mean((x >= lo) & (x <= hi)))
    # Photos: wide tonal spread with lots of interior values; line-art masks sit on
    # near-black plate with thin bright strokes → low ``central``.
    return bool(spread > 0.30 and central > 0.26)


def _pattern_light_bg(lum: np.ndarray):
    """Detect a dark-on-LIGHT pattern plate and return ``(bg_lum, is_light_bg)``.

    ``is_light_bg`` is True when the art is line-art / a stencil drawn on a light (white-ish)
    background — the case the engine's "light ink on a BLACK plate" convention inverts.
    Signals combined (all must hold), chosen to fire on dense stencils (mosaic, fleur-de-lis)
    yet stay quiet on photos and on the dark-plate art that already renders correctly:

      * a bright reference level (95th-pct luma) above 0.60 — there is real "paper",
      * the bright extreme dominates the dark extreme (more paper than ink),
      * the border frame is predominantly light — the background, not the subject.

    ``bg_lum`` is that bright reference, used by callers as the key-out level so the DESIGN
    (darker ink) becomes the opaque, overlay-fillable mask. Dark-background plates return
    ``is_light_bg=False`` and are left on the original luminance path untouched.

    Pattern transparency fix (2026-05-31): see ``_load_color_image_pattern`` /
    ``_load_image_pattern``. Dark-on-white plates were filling the whole zone with their
    background while the design read blank.
    """
    if lum.ndim != 2 or lum.size < 256:
        return 1.0, False
    bg_lum = float(np.percentile(lum, 95.0))
    frac_hi = float(np.mean(lum > 0.80))
    frac_lo = float(np.mean(lum < 0.20))
    border = np.concatenate([lum[0, :], lum[-1, :], lum[:, 0], lum[:, -1]])
    border_light_frac = float(np.mean(border > 0.55))
    is_light_bg = (
        bg_lum > 0.60
        and frac_hi >= 0.12
        and frac_hi > frac_lo
        and border_light_frac >= 0.55
    )
    return bg_lum, is_light_bg


def _resize_image_pattern(arr, target_h, target_w):
    """Resize pattern array to target size using LANCZOS for better car-render quality."""
    if arr.shape[0] == target_h and arr.shape[1] == target_w:
        return arr
    mn, mx = float(arr.min()), float(arr.max())
    rng = mx - mn + 1e-8
    u8 = (np.clip((arr - mn) / rng, 0, 1) * 255).astype(np.uint8)
    img = Image.fromarray(u8)
    resized = img.resize((target_w, target_h), Image.LANCZOS)
    out = np.array(resized).astype(np.float32) / 255.0
    return (out * rng + mn).astype(np.float32)


def _open_pattern_rgba(abs_path, target_h, target_w):
    """Open a pattern image, using decoder downsampling when the source is huge."""
    img = Image.open(abs_path)
    try:
        src_w, src_h = img.size
        if src_w >= target_w and src_h >= target_h and (src_w > target_w * 2 or src_h > target_h * 2):
            img.draft("RGBA", (target_w, target_h))
    except Exception:
        pass
    return img.convert("RGBA")


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
    Two-tier cache: Tier 1 caches raw decoded array (avoids disk I/O); Tier 2 caches
    transformed result keyed by (abs_path, h, w, scale, rot). Returns None on failure.
    Opaque **mask-style** PNGs (sparse ink on black) get contrast hardening for Pattern POP.
    Opaque **photo-like** JPEG/PNG collages use a gentler curve (see ``_opaque_pattern_photo_like``).
    """
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
    # Tier 2 check — fully-transformed result (LRU)
    cache_key = (abs_path, h, w, use_scale, use_rot)
    cached_t2 = _lru_get(_image_pattern_cache, cache_key)
    if cached_t2 is not None:
        return cached_t2
    try:
        from engine.core import _tile_fractional, _crop_center_array, _rotate_single_array
        # Tier 1 check — raw decoded float32 array (avoids disk I/O and PIL decode) (LRU)
        raw_key = (abs_path,)
        cached_t1 = _lru_get(_image_pattern_cache_raw, raw_key)
        opaque_photo_like = False
        if cached_t1 is not None:
            if len(cached_t1) == 3:
                arr, has_transparency, opaque_photo_like = cached_t1
            else:
                arr, has_transparency = cached_t1
                opaque_photo_like = (not has_transparency) and _opaque_pattern_photo_like(
                    arr, abs_path
                )
            arr = arr.copy()  # Don't mutate cached raw
        else:
            img_rgba = _open_pattern_rgba(abs_path, h, w)
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
                # Opaque plate: coverage = luminance assumes a BLACK background (light ink ->
                # high coverage). For DARK-on-WHITE stencils that inverts (the white bg fills
                # the zone). Detect a dominant light flat background and flip so the design
                # carries the coverage. Mirrors _load_color_image_pattern's alpha fix (2026-05-31).
                _bg_lum, _is_light_bg = _pattern_light_bg(lum)
                if _is_light_bg:
                    arr = np.clip((_bg_lum - lum) * (1.0 / max(_bg_lum, 1e-3)), 0.0, 1.0).astype(np.float32)
                else:
                    arr = lum
            if arr.ndim != 2:
                return None
            opaque_photo_like = (not has_transparency) and _opaque_pattern_photo_like(arr, abs_path)
            # Store raw decoded array in Tier 1 cache (LRU)
            _lru_put(
                _image_pattern_cache_raw,
                raw_key,
                (arr, has_transparency, opaque_photo_like),
                _IMAGE_CACHE_MAX_TIER1,
            )
            arr = arr.copy()  # Work on a copy from here on

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
        # For opaque images (no alpha): mask-style art gets hard POP hardening; photos / collages
        # get a gentle path so surf-skate JPEGs are not posterized into "clown camo".
        if not has_transparency:
            if opaque_photo_like:
                std = float(np.std(arr))
                if std < 0.20:
                    arr = np.clip((arr.astype(np.float32) - 0.5) * 1.28 + 0.5, 0.0, 1.0).astype(
                        np.float32
                    )
            else:
                arr = np.clip((arr.astype(np.float32) - 0.25) / 0.5, 0.0, 1.0).astype(np.float32)
                std = float(np.std(arr))
                if std < 0.28:
                    arr = np.clip((arr - 0.5) * 1.8 + 0.5, 0.0, 1.0).astype(np.float32)
        # Store in Tier 2 cache (LRU)
        result = arr.astype(np.float32)
        _lru_put(_image_pattern_cache, cache_key, result, _IMAGE_CACHE_MAX_TIER2)
        return result
    except Exception:
        return None

def _load_color_image_pattern(image_path, shape, scale=1.0, rotation=0.0, preserve_alpha=False):
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
    cache_key = (abs_path, h, w, use_scale, use_rot, "color", bool(preserve_alpha))
    cached_color = _lru_get(_image_pattern_cache, cache_key)
    if cached_color is not None:
        return cached_color
        
    try:
        img_rgba = _open_pattern_rgba(abs_path, h, w)
        rgba = np.array(img_rgba, dtype=np.float32) / 255.0

        ih, iw = rgba.shape[0], rgba.shape[1]

        # STEP 1: Always normalize to canvas size first (the "1.0x" baseline).
        # Small images get tiled to fill; large images get shrunk to fit.
        if ih < h or iw < w:
            n_h = max(1, (h + ih - 1) // ih)
            n_w = max(1, (w + iw - 1) // iw)
            rgba = np.tile(rgba, (n_h, n_w, 1))[:h, :w, :]
        elif ih > h or iw > w:
            rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
        # rgba is now exactly (h, w, 4) — the "1.0x" view.

        # STEP 2: Apply scale relative to the normalized baseline.
        # scale < 1.0 = shrink motifs (more repetitions); scale > 1.0 = zoom in (bigger).
        if abs(use_scale - 1.0) > 0.01:
            if use_scale < 1.0:
                # Shrink the normalized pattern, then tile to fill canvas
                tile_h = max(4, int(h * use_scale))
                tile_w = max(4, int(w * use_scale))
                small = cv2.resize(rgba, (tile_w, tile_h), interpolation=cv2.INTER_AREA)
                n_h = max(1, (h + tile_h - 1) // tile_h)
                n_w = max(1, (w + tile_w - 1) // tile_w)
                rgba = np.tile(small, (n_h, n_w, 1))[:h, :w, :]
            else:
                # Zoom in: crop center of the normalized pattern, then resize back to canvas
                crop_h = max(4, int(h / use_scale))
                crop_w = max(4, int(w / use_scale))
                y0 = max(0, (h - crop_h) // 2)
                x0 = max(0, (w - crop_w) // 2)
                rgba = rgba[y0:y0+crop_h, x0:x0+crop_w, :]
                rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_LINEAR)

        if rgba.shape[0] != h or rgba.shape[1] != w:
            rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_LINEAR)
        
        if abs(use_rot) > 0.5:
            if preserve_alpha:
                matrix = cv2.getRotationMatrix2D((w / 2., h / 2.), use_rot, 1.)
                rgba = cv2.warpAffine(rgba, matrix, (w, h), flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_WRAP)
            else:
                from engine.core import _rotate_single_array
                for ch in range(4):
                    rgba[:, :, ch] = _rotate_single_array(rgba[:, :, ch], use_rot, (h, w))
        
        # Alpha handling for image patterns:
        # - If fully opaque source: synthesize alpha from luminance (black -> transparent).
        # - For patternexamples assets: also key out near-black even when an alpha channel exists,
        #   so dark baked backgrounds (e.g. Biomechanical-style plates) don't sit on top of the base.
        alpha = rgba[:, :, 3]
        lum = 0.299 * rgba[:, :, 0] + 0.587 * rgba[:, :, 1] + 0.114 * rgba[:, :, 2]
        if preserve_alpha:
            pass  # Authored RGBA for full paint overlays; never erase dark/light ink.
        elif float(alpha.min()) > 0.999:  # No transparency in image -> synthesize alpha
            # Original convention: light ink on a BLACK plate (black -> transparent via lum).
            # Pattern transparency fix (2026-05-31): many cultural/geometric plates (e.g.
            # aztec_alt1.jpg) are drawn DARK-on-WHITE. Under the black-plate assumption their
            # white background went fully opaque (zone fills with white, design reads blank).
            # Detect a dominant LIGHT flat background and key it out so the DESIGN becomes the
            # opaque, overlay-fillable mask. Dark-background plates are untouched.
            bg_lum, is_light_bg = _pattern_light_bg(lum)
            if is_light_bg:
                rgba[:, :, 3] = np.clip((bg_lum - lum) * (1.5 / max(bg_lum, 1e-3)), 0.0, 1.0)
            else:
                rgba[:, :, 3] = np.clip(lum * 1.5, 0, 1)
        elif "patternexamples" in image_path.replace("\\", "/").lower():
            # Soft black-key: keep details, but remove deep black backing.
            dark_key = np.clip((lum - 0.08) / 0.35, 0.0, 1.0).astype(np.float32)
            rgba[:, :, 3] = np.clip(alpha * dark_key, 0.0, 1.0)
            
        _lru_put(_image_pattern_cache, cache_key, rgba, _IMAGE_CACHE_MAX_TIER2)
        return rgba
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
    """Generic gradient spec with fine interference detail for extended gradients."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    xf = x / max(w - 1, 1)
    yf = y / max(h - 1, 1)
    phase = (int(seed) % 997) * 0.017
    silk = (
        np.sin((xf * 37.0 + yf * 23.0 + phase) * np.pi) * 0.45
        + np.sin((xf * 91.0 - yf * 67.0 + phase * 1.7) * np.pi) * 0.30
        + np.sin((xf * 173.0 + yf * 151.0 + phase * 0.6) * np.pi) * 0.15
    )
    ridge = np.clip(1.0 - np.abs(np.sin((xf * 51.0 - yf * 39.0 + phase) * np.pi)) * 28.0, 0.0, 1.0)
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip((88 + silk * 34 + ridge * 56) * mask * sm + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((46 - ridge * 18 + silk * 8) * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((16 + ridge * 14 + (silk + 1.0) * 4) * mask, 16, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
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
        'gloss': (5, 20, 16), 'matte': (5, 180, 200),
        'satin': (15, 90, 40), 'metallic': (200, 50, 16),
        'pearl': (120, 35, 16), 'candy': (200, 15, 16),
        'chrome': (250, 3, 16), 'flat': (0, 230, 220),
    }
    M, R, CC = MATS.get(mat_key, (5, 20, 16))
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)  # GGX floor
    spec[:, :, 2] = CC
    spec[:, :, 3] = 255
    return spec


def _generic_transformed_uv(xf, yf, base_scale=1.0, base_offset_x=0.5, base_offset_y=0.5, base_flip_h=False, base_flip_v=False):
    use_scale = max(0.01, min(10.0, float(base_scale if base_scale is not None else 1.0)))
    ox = max(0.0, min(1.0, float(base_offset_x if base_offset_x is not None else 0.5)))
    oy = max(0.0, min(1.0, float(base_offset_y if base_offset_y is not None else 0.5)))
    xft = 1.0 - xf if base_flip_h else xf
    yft = 1.0 - yf if base_flip_v else yf
    xft = (xft - ox) * use_scale + 0.5
    yft = (yft - oy) * use_scale + 0.5
    return xft.astype(np.float32, copy=False), yft.astype(np.float32, copy=False), use_scale


def _generic_direction_t(xf, yf, direction, rotation):
    if direction == 'horizontal':
        base_angle = 90.0
    elif direction == 'diagonal':
        base_angle = 45.0
    else:
        base_angle = 0.0
    total_angle = base_angle + float(rotation)
    rad = np.deg2rad(total_angle)
    cs = float(np.cos(rad))
    sn = float(np.sin(rad))
    span = max(1e-6, abs(cs) + abs(sn))
    t = (cs * (yf - 0.5) + sn * (xf - 0.5)) / span + 0.5
    return t.astype(np.float32, copy=False)


def _apply_generic_gradient(
    paint, shape, mask, c1, c2, direction, seed, pm, bb, mirror=False,
    rotation=0, base_scale=1.0, base_offset_x=0.5, base_offset_y=0.5,
    base_flip_h=False, base_flip_v=False,
):
    """Apply a 2-color gradient to paint. Zone-aware with fine interference detail."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    blend = 0.90 * pm
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
    xf_s, yf_s, use_scale = _generic_transformed_uv(
        xf, yf, base_scale, base_offset_x, base_offset_y, base_flip_h, base_flip_v
    )
    phase = (int(seed) % 1543) * 0.013
    warp = (
        np.sin((xf_s * 9.0 + yf_s * 5.0 + phase) * np.pi) * 0.035
        + np.sin((xf_s * 31.0 - yf_s * 17.0 + phase * 1.7) * np.pi) * 0.020
        + np.sin((xf_s * 89.0 + yf_s * 71.0 + phase * 0.6) * np.pi) * 0.010
    ).astype(np.float32)
    if direction == 'radial':
        cx, cy = 0.5, 0.5
        dist = np.sqrt((xf_s - cx) ** 2 + (yf_s - cy) ** 2) * 1.414
        angle = np.arctan2(yf_s - cy, xf_s - cx)
        spiral = np.sin((dist * 16.0 + angle * 2.8 + phase) * np.pi) * 0.055
        t = np.clip(dist + spiral + warp, 0, 1)
    else:
        t = _generic_direction_t(xf_s, yf_s, direction, rotation)
        contour = np.sin((t * 34.0 + xf_s * 2.0 - yf_s * 1.4 + phase) * np.pi) * 0.030
        t = np.clip(t + warp + contour, 0, 1)
    if mirror:
        t = np.where(t < 0.5, t * 2, (1 - t) * 2)
    ribbon = np.clip(1.0 - np.abs(np.sin((t * 22.0 + xf_s * 3.0 - yf_s * 2.0 + phase) * np.pi)) * 34.0, 0.0, 1.0)
    micro = np.sin((xf_s * 157.0 - yf_s * 131.0 + phase * 2.1) * np.pi) * 0.018
    r = c1[0] + (c2[0] - c1[0]) * t
    g = c1[1] + (c2[1] - c1[1]) * t
    b = c1[2] + (c2[2] - c1[2]) * t
    highlight = ribbon * 0.105 + micro
    r = r + bb + highlight
    g = g + bb + highlight * 0.90
    b = b + bb + highlight * 1.08
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint


def _apply_generic_3color_gradient(
    paint, shape, mask, c1, c2, c3, direction, seed, pm, bb,
    rotation=0, base_scale=1.0, base_offset_x=0.5, base_offset_y=0.5,
    base_flip_h=False, base_flip_v=False,
):
    """Apply a 3-color gradient (c1 -> c2 -> c3). Zone-aware: maps to zone bbox."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    xf_s, yf_s, _use_scale = _generic_transformed_uv(
        xf, yf, base_scale, base_offset_x, base_offset_y, base_flip_h, base_flip_v
    )
    t = np.clip(_generic_direction_t(xf_s, yf_s, direction, rotation), 0, 1)
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    blend = 0.85 * pm
    r, g, b = c1[0] + bb, c1[1] + bb, c1[2] + bb
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mask * blend) + r * mask * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mask * blend) + g * mask * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mask * blend) + b * mask * blend, 0, 1)
    return paint


def render_generic_finish(
    finish_name, zone, paint, shape, zone_mask, seed, sm, pm, bb,
    rotation=0, base_scale=1.0, base_offset_x=0.5, base_offset_y=0.5,
    base_flip_h=False, base_flip_v=False,
):
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
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, mirror=True, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)
    elif finish_name.startswith('grad3_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        if c3:
            paint = _apply_generic_3color_gradient(paint, shape, zone_mask, c1, c2, c3, direction, seed, pm, bb, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)
        else:
            paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)
    elif finish_name.startswith('ghostg_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, 'vertical', seed, pm, bb, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)
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
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)
    elif finish_name.startswith('clr_'):
        parts = finish_name.split('_')
        mat_key = parts[-1] if len(parts) >= 3 else 'gloss'
        zone_spec = _generic_solid_spec_fn(shape, zone_mask, seed, sm, mat_key)
        paint = _apply_generic_solid(paint, shape, zone_mask, c1, seed, pm, bb)
    elif finish_name.startswith('mc_'):
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        if c3:
            paint = _apply_generic_3color_gradient(paint, shape, zone_mask, c1, c2, c3, direction, seed, pm, bb, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)
        else:
            paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)
    else:
        zone_spec = _generic_grad_spec(shape, zone_mask, seed, sm)
        paint = _apply_generic_gradient(paint, shape, zone_mask, c1, c2, direction, seed, pm, bb, rotation=rotation, base_scale=base_scale, base_offset_x=base_offset_x, base_offset_y=base_offset_y, base_flip_h=base_flip_h, base_flip_v=base_flip_v)

    return zone_spec, paint


__all__ = ["render_generic_finish", "clear_image_pattern_cache"]
