"""
engine/compose.py - Base + Pattern Compositing
==============================================
Compose base material and pattern texture into spec maps and paint.

Pattern-driven spec: When a pattern has a texture_fn that returns R_range and M_range,
compose applies pattern_val * R_range/M_range to the spec map (see compose_finish and
compose_finish_stacked). Image-only patterns (image_path, no texture_fn) do not drive
spec; with small tiling the visible spec change may come mainly from the base.

Full implementation (extracted from shokker_engine_v2 monolith).
Uses LAZY import for BASE_REGISTRY/PATTERN_REGISTRY to avoid circular import.
"""

import math
import numpy as np
import time as _time
import cv2
from functools import lru_cache

# Pattern texture cache — avoids regenerating identical patterns across preview re-renders.
# Key: (pattern_id, h, w, seed, scale, rotation). Stores (pattern_val, tex_dict).
# Max 32 entries (~50MB at 2048x2048 with 4 arrays each). Cleared on paint file change.
_pattern_tex_cache = {}
_PATTERN_CACHE_MAX = 32
_pattern_cache_enabled = True


def _get_cached_tex(tex_fn, pattern_id, shape, mask, seed, sm, scale=1.0, rotation=0):
    """Call tex_fn with caching. Returns tex dict or None on failure."""
    if not _pattern_cache_enabled:
        try:
            return tex_fn(shape, mask, seed, sm)
        except Exception as _e:
            print(f"[compose] WARNING: tex_fn failed for pattern '{pattern_id}': {_e}")
            return None
    key = (pattern_id, shape[0], shape[1], seed, round(float(scale), 4), round(float(rotation), 2))
    if key in _pattern_tex_cache:
        return _pattern_tex_cache[key]
    try:
        tex = tex_fn(shape, mask, seed, sm)
    except Exception as _e:
        print(f"[compose] WARNING: tex_fn failed for pattern '{pattern_id}': {_e}")
        return None
    if len(_pattern_tex_cache) >= _PATTERN_CACHE_MAX:
        # Evict oldest entry
        _pattern_tex_cache.pop(next(iter(_pattern_tex_cache)))
    _pattern_tex_cache[key] = tex
    return tex


def clear_pattern_cache():
    """Clear the pattern texture cache (call when paint file or resolution changes)."""
    _pattern_tex_cache.clear()


def _ggx_safe_R(R_arr, M_arr, lib=None):
    """Conditional GGX floor: R >= 15 for non-chrome (M < 240), R >= 0 for chrome (M >= 240).
    Final safety net at the compose output stage. Works with numpy or cupy (pass lib=xp for GPU)."""
    _np = lib if lib is not None else np
    R_clipped = _np.clip(R_arr, 0, 255)
    return _np.where(M_arr < 240, _np.maximum(R_clipped, 15.0), R_clipped)

try:
    from engine.gpu import xp, to_cpu, to_gpu, is_gpu
except ImportError:
    import numpy as xp
    def to_cpu(a): return a
    def to_gpu(a): return a
    def is_gpu(): return False

from engine.core import (
    _resize_array,
    _tile_fractional,
    _crop_center_array,
    _scale_pattern_output,
    _rotate_pattern_tex,
    _rotate_single_array,
    multi_scale_noise,
    perlin_multi_octave,
    rgb_to_hsv_array,
    hsv_to_rgb_vec,
)
from engine.overlay import blend_dual_base_spec, get_base_overlay_alpha, _normalize_second_base_blend_mode
from engine.spec_paint import paint_none


def _scale_down_spec_pattern(sp_fn, sp_scale, canvas_shape, seed_val, sm_val, sp_params):
    """Generate a spec pattern at higher resolution, then downsample to canvas size.

    When scale < 1.0, instead of tiling the pattern (which creates visible
    grid boundaries), we generate the pattern at a larger resolution
    (canvas_size / scale) and then smoothly downsample back to canvas size.
    This effectively 'shrinks' the pattern features without any tile seams.

    Args:
        sp_fn: The spec pattern generator function.
        sp_scale: The user scale factor (0 < sp_scale < 1.0).
        canvas_shape: Target (H, W) or (H, W, C) shape.
        seed_val: Seed for pattern generation.
        sm_val: Smoothness parameter.
        sp_params: Extra keyword args for sp_fn.

    Returns:
        float32 array at canvas_shape[:2] dimensions with scaled-down pattern.
    """
    h, w = canvas_shape[0], canvas_shape[1]
    inv_scale = 1.0 / sp_scale
    # Generate at higher resolution — cap at 8x to avoid memory issues
    inv_scale_capped = min(inv_scale, 8.0)
    gen_h = min(16384, max(h, int(math.ceil(h * inv_scale_capped))))
    gen_w = min(16384, max(w, int(math.ceil(w * inv_scale_capped))))
    gen_shape = (gen_h, gen_w) if len(canvas_shape) == 2 else (gen_h, gen_w, canvas_shape[2])
    try:
        big_arr = sp_fn(gen_shape, seed_val, sm_val, **sp_params)
    except Exception:
        # Fallback: generate at canvas size and use smooth resize instead of tiling
        big_arr = sp_fn(canvas_shape, seed_val, sm_val, **sp_params)
        return big_arr
    # Downsample to canvas size using smooth interpolation (INTER_AREA for downscale)
    if big_arr.shape[0] != h or big_arr.shape[1] != w:
        big_arr = cv2.resize(big_arr.astype(np.float32), (w, h),
                             interpolation=cv2.INTER_AREA)
    return big_arr.astype(np.float32)


def _get_pattern_mask(pattern_id, shape, mask, seed, sm, scale=1.0, rotation=0.0, opacity=1.0, strength=1.0, offset_x=0.5, offset_y=0.5):
    """Return (H,W) float32 0-1 array from pattern's texture_fn or image_path for use as blend alpha when blend_mode='pattern'.
    Optional: scale, rotation, opacity, strength. offset_x, offset_y in [0,1]: 0.5 = center (no pan); 0 = left/top, 1 = right/bottom. Returns None if unavailable."""
    from engine.registry import PATTERN_REGISTRY
    from engine.render import _load_image_pattern
    if not pattern_id or pattern_id == "none" or pattern_id not in PATTERN_REGISTRY:
        return None
    pattern = PATTERN_REGISTRY[pattern_id]
    image_path = pattern.get("image_path")
    if image_path:
        pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
        if pv is None:
            return None
        h, w = shape[0], shape[1]
        out = np.clip(pv * mask * max(0.0, min(1.0, float(opacity))) * max(0.0, min(2.0, float(strength))), 0, 1).astype(np.float32)
        _apply_pattern_offset(out, shape, offset_x, offset_y)
        return out
    tex_fn = pattern.get("texture_fn")
    if not tex_fn:
        return None
    try:
        h, w = shape[0], shape[1]
        # tex_fn needs CPU mask
        _mask_cpu = to_cpu(mask) if is_gpu() else mask
        # Cache tex_fn output by function identity + shape + seed
        _cache_key = (id(tex_fn), h, w, seed)
        if _pattern_cache_enabled and _cache_key in _pattern_tex_cache:
            tex = _pattern_tex_cache[_cache_key]
        else:
            tex = tex_fn(shape, _mask_cpu, seed, sm)
            if _pattern_cache_enabled:
                if len(_pattern_tex_cache) >= _PATTERN_CACHE_MAX:
                    _pattern_tex_cache.pop(next(iter(_pattern_tex_cache)))
                _pattern_tex_cache[_cache_key] = tex
        if isinstance(tex, dict):
            pv = tex.get("pattern_val")
        else:
            pv = tex
        if pv is None:
            return None
        pv = np.asarray(pv, dtype=np.float32)
        if pv.ndim != 2:
            return None
        use_scale = max(0.1, min(10.0, float(scale)))
        if abs(use_scale - 1.0) > 0.01:
            if isinstance(tex, dict):
                pv, tex = _scale_pattern_output(pv, tex, use_scale, shape)
            else:
                if use_scale < 1.0:
                    pv = _tile_fractional(pv, 1.0 / use_scale, h, w)
                else:
                    pv = _crop_center_array(pv, use_scale, h, w)
        if pv.shape[0] != h or pv.shape[1] != w:
            pv = _resize_array(pv, h, w)
        if abs(float(rotation) % 360.0) > 0.5:
            pv = _rotate_single_array(pv, float(rotation), shape)
        pmin, pmax = float(pv.min()), float(pv.max())
        if pmax - pmin > 1e-8:
            pv = (pv - pmin) / (pmax - pmin)
        else:
            pv = np.zeros_like(pv)
        # Use CPU mask for final multiply (returns CPU array for downstream)
        out = np.clip(pv * _mask_cpu * max(0.0, min(1.0, float(opacity))) * max(0.0, min(2.0, float(strength))), 0, 1).astype(np.float32)
        _apply_pattern_offset(out, shape, offset_x, offset_y)
        return out
    except Exception:
        return None


def _apply_pattern_offset(pv, shape, offset_x, offset_y):
    """Apply pan offset to pattern array in-place. offset_x/y in [0,1]; 0.5 = no shift.
    Uses np.roll (CPU only). If pv is a CuPy array, transfers to CPU, rolls, transfers back."""
    if pv is None or pv.size == 0:
        return
    try:
        h, w = int(shape[0]), int(shape[1])
        ox = float(offset_x) if offset_x is not None else 0.5
        oy = float(offset_y) if offset_y is not None else 0.5
        shift_x = int(round((ox - 0.5) * w))
        shift_y = int(round((oy - 0.5) * h))
        if shift_x != 0 or shift_y != 0:
            # xp.roll works on both numpy and cupy
            pv[:] = xp.roll(pv, (-shift_y, -shift_x), axis=(0, 1))
    except Exception:
        pass


def _apply_spec_pattern_box_size(sp_arr, canvas_shape, box_size_pct, offset_x, offset_y):
    """Mask a spec pattern array to only affect a box region of the canvas.
    box_size_pct: integer 5-100 (percentage of canvas each dimension).
    offset_x/offset_y: 0-1 center position of the box.
    Returns the masked array (0.5 outside the box = no effect in delta math).
    """
    if box_size_pct >= 100:
        return sp_arr
    h, w = int(canvas_shape[0]), int(canvas_shape[1])
    box_w = max(1, int(w * box_size_pct / 100.0))
    box_h = max(1, int(h * box_size_pct / 100.0))
    # Center of box at offset position
    cx = int(offset_x * w)
    cy = int(offset_y * h)
    x0 = max(0, cx - box_w // 2)
    y0 = max(0, cy - box_h // 2)
    x1 = min(w, x0 + box_w)
    y1 = min(h, y0 + box_h)
    # Clamp to ensure box stays within canvas
    if x1 - x0 < box_w and x0 == 0:
        x1 = min(w, box_w)
    if y1 - y0 < box_h and y0 == 0:
        y1 = min(h, box_h)
    # Fill outside the box with 0.5 (neutral = no change in delta math)
    result = np.full_like(np.asarray(sp_arr), 0.5, dtype=np.float32)
    # Copy the pattern data inside the box region
    # The pattern was generated at full canvas size, so crop the corresponding region
    result[y0:y1, x0:x1] = np.asarray(sp_arr)[y0:y1, x0:x1]
    return result


def _boost_overlay_mono_color(rgb):
    """Boost monolithic overlay readability without white blowout.
    Always returns numpy (CPU) array since callers in compose_paint_mod work on CPU."""
    # Ensure CPU numpy array — accept CuPy arrays via .get()
    if hasattr(rgb, 'get'):
        rgb = rgb.get()
    rgb_np = np.asarray(rgb, dtype=np.float32)
    rgb_np = np.clip(rgb_np, 0.0, 1.0)
    gray = rgb_np.mean(axis=2, keepdims=True)
    sat_boost = np.clip(gray + (rgb_np - gray) * 1.18, 0.0, 1.0)
    val_boost = np.clip(sat_boost * 1.12, 0.0, 1.0)
    return val_boost


def _mono_overlay_seed_paint(paint):
    """Generate neutral seed paint so mono overlays match swatch intent.
    Always returns CPU (numpy) array — external paint_fn functions expect numpy."""
    paint_cpu = to_cpu(paint) if is_gpu() else paint
    return np.full_like(paint_cpu[:, :, :3], 0.533, dtype=np.float32)


def _apply_hsb_adjustments(paint, mask, hue_offset_deg, saturation_adjust, brightness_adjust):
    """Apply Hue/Saturation/Brightness adjustments to paint inside mask.
    hue_offset_deg: -180 to +180 degrees
    saturation_adjust: -100 to +100 (multiplicative: sat * (1 + adjust/100))
    brightness_adjust: -100 to +100 (multiplicative: val * (1 + adjust/100))
    Always operates on CPU (numpy) arrays. CuPy inputs are converted via .get().
    """
    try:
        if abs(hue_offset_deg) < 0.5 and abs(saturation_adjust) < 0.5 and abs(brightness_adjust) < 0.5:
            return paint
        # rgb_to_hsv_array / hsv_to_rgb_vec use cv2 internally -> need CPU numpy arrays
        _paint_cpu = paint.get() if hasattr(paint, 'get') else np.asarray(paint)
        _mask_cpu = mask.get() if hasattr(mask, 'get') else np.asarray(mask)
        rgb = np.clip(_paint_cpu[:, :, :3], 0.0, 1.0).astype(np.float32)
        # Ensure mask matches paint dimensions
        if _mask_cpu.shape[0] != rgb.shape[0] or _mask_cpu.shape[1] != rgb.shape[1]:
            from PIL import Image
            _mask_cpu = np.array(Image.fromarray((_mask_cpu * 255).astype(np.uint8)).resize(
                (rgb.shape[1], rgb.shape[0]), Image.NEAREST)).astype(np.float32) / 255.0
        hsv = rgb_to_hsv_array(rgb)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        if abs(hue_offset_deg) >= 0.5:
            h = (h + hue_offset_deg / 360.0) % 1.0
        if abs(saturation_adjust) >= 0.5:
            s = np.clip(s * (1.0 + saturation_adjust / 100.0), 0.0, 1.0)
        if abs(brightness_adjust) >= 0.5:
            v = np.clip(v * (1.0 + brightness_adjust / 100.0), 0.0, 1.0)
        r, g, b = hsv_to_rgb_vec(h, s, v)
        adjusted = np.stack([np.clip(r, 0, 1), np.clip(g, 0, 1), np.clip(b, 0, 1)], axis=-1).astype(np.float32)
        # All blending is CPU-only
        m3 = _mask_cpu[:, :, np.newaxis]
        _paint_cpu = _paint_cpu.copy()
        _paint_cpu[:, :, :3] = _paint_cpu[:, :, :3] * (1.0 - m3) + adjusted * m3
        return _paint_cpu
    except Exception as e:
        print(f"  [HSB] WARNING: _apply_hsb_adjustments failed ({e}), returning paint unchanged")
        return paint


def _apply_base_color_override(paint, shape, hard_mask, seed, base_color_mode, base_color, base_color_source, base_color_strength, monolithic_registry):
    """Apply base color override to paint. Always operates on CPU (numpy) arrays.
    CuPy inputs are converted at the top. Returns a numpy array."""
    mode = str(base_color_mode or "source").strip().lower()
    if mode in ("", "source", "none"):
        return paint
    strength = max(0.0, min(1.0, float(base_color_strength if base_color_strength is not None else 1.0)))
    if strength <= 0.001:
        return paint

    # Ensure CPU numpy — accept CuPy inputs
    paint = paint.get() if hasattr(paint, 'get') else np.asarray(paint)
    hard_mask = hard_mask.get() if hasattr(hard_mask, 'get') else np.asarray(hard_mask)

    # Always use the actual canvas size from the paint array, not the shape parameter.
    # During preview renders the paint is already downscaled but shape may still carry
    # the original file resolution, causing a size mismatch inside overlay paint_fns.
    actual_shape = (paint.shape[0], paint.shape[1])

    src = None
    if mode in ("special", "from_special", "mono"):
        if isinstance(base_color_source, str):
            # --- Mono (special) source: "mono:finish_id" ---
            if base_color_source.startswith("mono:"):
                mono_id = base_color_source[5:]
                _found = False
                if monolithic_registry is not None and mono_id in monolithic_registry:
                    mono_paint_fn = monolithic_registry[mono_id][1]
                    _src_raw = mono_paint_fn(_mono_overlay_seed_paint(paint), actual_shape, hard_mask, seed + 4242, 1.0, 0.0)
                    if _src_raw is not None:
                        _src_np = _src_raw.get() if hasattr(_src_raw, 'get') else np.asarray(_src_raw)
                        src = _boost_overlay_mono_color(np.clip(_src_np[:, :, :3], 0.0, 1.0))
                    _found = True
                if not _found:
                    # REVERSE FALLBACK: mono: ID is a base-registered finish (migrated to Specials)
                    try:
                        from engine.registry import BASE_REGISTRY as _BR
                        if mono_id in _BR:
                            _base_paint_fn = _BR[mono_id].get("paint_fn", paint_none)
                            if _base_paint_fn is not paint_none:
                                _src_raw = _base_paint_fn(paint.copy(), actual_shape, hard_mask, seed + 4242, 1.0, 0.0)
                                if _src_raw is not None:
                                    _src_np = np.asarray(_src_raw)
                                    src = _boost_overlay_mono_color(np.clip(_src_np[:, :, :3], 0.0, 1.0))
                    except ImportError:
                        pass
            # --- Base finish source: raw ID or "base:finish_id" ---
            elif not base_color_source.startswith("mono:"):
                try:
                    from engine.registry import BASE_REGISTRY
                    raw_id = base_color_source[5:] if base_color_source.startswith("base:") else base_color_source
                    if raw_id in BASE_REGISTRY:
                        base_entry = BASE_REGISTRY[raw_id]
                        base_paint_fn = base_entry.get("paint_fn", paint_none)
                        if base_paint_fn is not paint_none:
                            _src_raw = base_paint_fn(paint.copy(), actual_shape, hard_mask, seed + 4242, 1.0, 0.0)
                            if _src_raw is not None:
                                _src_np = _src_raw.get() if hasattr(_src_raw, 'get') else np.asarray(_src_raw)
                                src = np.clip(_src_np[:, :, :3], 0.0, 1.0)
                    # Also check monolithic registry with raw ID (user picked a special without prefix)
                    elif monolithic_registry is not None and raw_id in monolithic_registry:
                        mono_paint_fn = monolithic_registry[raw_id][1]
                        _src_raw = mono_paint_fn(_mono_overlay_seed_paint(paint), actual_shape, hard_mask, seed + 4242, 1.0, 0.0)
                        if _src_raw is not None:
                            _src_np = _src_raw.get() if hasattr(_src_raw, 'get') else np.asarray(_src_raw)
                            src = _boost_overlay_mono_color(np.clip(_src_np[:, :, :3], 0.0, 1.0))
                except Exception:
                    pass
    elif mode == "solid":
        clr = base_color if (base_color is not None and len(base_color) >= 3) else [1.0, 1.0, 1.0]
        cr, cg, cb = float(clr[0]), float(clr[1]), float(clr[2])
        base_rgb = np.clip(paint[:, :, :3], 0.0, 1.0)
        gray = base_rgb.mean(axis=2, keepdims=True)
        tint_rgb = np.array([cr, cg, cb], dtype=np.float32)[np.newaxis, np.newaxis, :]
        src = np.clip(gray * 0.25 + tint_rgb * 0.75, 0.0, 1.0)

    if src is None:
        return paint

    # Everything is CPU here (paint + hard_mask + src)
    src = src.get() if hasattr(src, 'get') else (np.asarray(src) if not isinstance(src, np.ndarray) else src)
    w = (hard_mask * strength)[:, :, np.newaxis]
    paint = paint.copy()
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - w) + src * w
    return paint


def _apply_spec_blend_mode(base_val, pattern_contrib, opacity, mode="normal"):
    """Apply a pattern contribution to a spec channel using the specified blend mode."""
    if mode == "normal" or mode not in ("multiply", "screen", "overlay", "hardlight", "softlight"):
        return base_val + pattern_contrib * opacity
    p_abs = xp.abs(pattern_contrib)
    p_max = float(xp.max(p_abs)) if float(xp.max(p_abs)) > 1e-8 else 1.0
    p_norm = pattern_contrib / p_max
    p_factor = xp.clip(p_norm * 0.5 + 0.5, 0, 1)
    b_norm = xp.clip(base_val / 255.0, 0, 1)
    if mode == "multiply":
        blended_norm = b_norm * (1.0 - opacity + opacity * p_factor * 2.0)
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "screen":
        screen_factor = p_factor * opacity
        blended_norm = 1.0 - (1.0 - b_norm) * (1.0 - screen_factor)
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "overlay":
        dark = 2.0 * b_norm * p_factor
        light = 1.0 - 2.0 * (1.0 - b_norm) * (1.0 - p_factor)
        overlay_result = xp.where(b_norm < 0.5, dark, light)
        blended_norm = b_norm * (1.0 - opacity) + overlay_result * opacity
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "hardlight":
        # Hard Light: like overlay but with base/pattern roles swapped
        dark = 2.0 * b_norm * p_factor
        light = 1.0 - 2.0 * (1.0 - b_norm) * (1.0 - p_factor)
        hl_result = xp.where(p_factor < 0.5, dark, light)
        blended_norm = b_norm * (1.0 - opacity) + hl_result * opacity
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "softlight":
        # Soft Light: gentler version — subtle spec shifts
        sl_result = (1.0 - 2.0 * p_factor) * b_norm * b_norm + 2.0 * p_factor * b_norm
        blended_norm = b_norm * (1.0 - opacity) + sl_result * opacity
        return xp.clip(blended_norm * 255.0, 0, 255)
    return base_val + pattern_contrib * opacity


def compose_finish(base_id, pattern_id, shape, mask, seed, sm, scale=1.0, spec_mult=1.0, rotation=0,
                   pattern_opacity=1.0,
                   base_scale=1.0, base_strength=1.0, base_spec_strength=1.0, base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0,
                   base_flip_h=False, base_flip_v=False,
                   cc_quality=None, blend_base=None, blend_dir="horizontal",
                   blend_amount=0.5, paint_color=None,
                   second_base=None, second_base_color=None, second_base_strength=0.0, second_base_spec_strength=1.0,
                   second_base_blend_mode="noise", second_base_noise_scale=24,
                   second_base_scale=1.0, second_base_pattern=None,
                   second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                   second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                   second_base_pattern_invert=False, second_base_pattern_harden=False,
                   second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                   third_base=None, third_base_color=None, third_base_strength=0.0, third_base_spec_strength=1.0,
                   third_base_blend_mode="noise", third_base_noise_scale=24,
                   third_base_scale=1.0, third_base_pattern=None,
                   third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                   third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                   third_base_pattern_invert=False, third_base_pattern_harden=False,
                   third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                   fourth_base=None, fourth_base_color=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0,
                   fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                   fourth_base_scale=1.0, fourth_base_pattern=None,
                   fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                   fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                   fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                   fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                   fifth_base=None, fifth_base_color=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0,
                   fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                   fifth_base_scale=1.0, fifth_base_pattern=None,
                   fifth_base_pattern_scale=1.0, fifth_base_pattern_rotation=0.0,
                   fifth_base_pattern_opacity=1.0, fifth_base_pattern_strength=1.0,
                   fifth_base_pattern_invert=False, fifth_base_pattern_harden=False,
                   fifth_base_pattern_offset_x=0.5, fifth_base_pattern_offset_y=0.5,
                   pattern_offset_x=0.5, pattern_offset_y=0.5,
                   pattern_flip_h=False, pattern_flip_v=False,
                   pattern_sm=None,
                   pattern_intensity=1.0,
                   base_spec_blend_mode="normal",
                   monolithic_registry=None,
                   **kwargs):
    """Compose a base material + pattern texture into a final spec map.
    base_spec_blend_mode: how pattern spec contributions blend with base spec
        (normal/multiply/screen/overlay/hardlight/softlight).
    When second_base/third_base/fourth_base/fifth_base start with "mono:", they are
    looked up in monolithic_registry (spec_fn, paint_fn) and the spec_fn is used as the overlay."""
    _t_compose = _time.time()
    _gpu_active = is_gpu()
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    if pattern_sm is None:
        pattern_sm = sm
    _pat_int_raw = max(0.0, min(1.0, float(pattern_intensity)))
    _pat_int = _pat_int_raw ** 0.5 if _pat_int_raw > 0 else 0.0  # perceptual curve matches paint
    pattern_sm_eff = pattern_sm * _pat_int  # sqrt curve: 5%→22%, 50%→71%, 100%→100%
    # NOTE: base_strength is a paint slider, handled in compose_paint_mod — not used in spec compositing.
    _sm_base = sm * max(0.0, min(2.0, float(base_spec_strength)))
    base = BASE_REGISTRY[base_id]
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)  # stays CPU (uint8 output)
    base_M = float(base["M"])
    base_R = float(base["R"])
    base_CC = int(base["CC"]) if base.get("CC") is not None else 16

    # Transfer mask to GPU at entry — used throughout
    if _gpu_active:
        mask = to_gpu(mask)

    if base_scale != 1.0 and base_scale > 0:
        MAX_BASE_DIM = 4096
        base_h = min(MAX_BASE_DIM, max(4, int(shape[0] / base_scale)))
        base_w = min(MAX_BASE_DIM, max(4, int(shape[1] / base_scale)))
        base_shape = (base_h, base_w)
    else:
        base_shape = shape

    _base_seed_offset = abs(hash(base_id)) % 10000
    _bss = max(0.0, min(2.0, float(base_spec_strength)))
    if base.get("base_spec_fn"):
        spec_result = base["base_spec_fn"](base_shape, seed + _base_seed_offset, _sm_base, base_M, base_R)
        if len(spec_result) == 3:
            M_arr, R_arr, CC_arr = spec_result
        else:
            M_arr, R_arr = spec_result
            CC_arr = None
        # Scale spec variation by base_spec_strength so the slider actually works.
        # Most custom spec functions ignore sm, so we post-scale: at bss=0 → flat base values,
        # at bss=1.0 → full variation, at bss=2.0 → amplified variation.
        if _bss < 0.999 or _bss > 1.001:
            M_arr = base_M + (M_arr - base_M) * _bss
            R_arr = base_R + (R_arr - base_R) * _bss
            if CC_arr is not None:
                CC_arr = float(base_CC) + (CC_arr - float(base_CC)) * _bss
    elif base.get("brush_grain"):
        rng = np.random.RandomState(seed + _base_seed_offset)
        noise = np.tile(rng.randn(1, base_shape[1]) * 0.5, (base_shape[0], 1))
        noise += rng.randn(base_shape[0], base_shape[1]) * 0.2
        M_arr = base_M + noise * base.get("noise_M", 0) * _sm_base
        R_arr = base_R + noise * base.get("noise_R", 0) * _sm_base
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * _sm_base
        else:
            CC_arr = None
        # Lerp toward neutral when spec strength < 1.0 so slider actually reduces the effect
        if _bss < 0.999:
            _neutral_M, _neutral_R = 0.0, 128.0
            M_arr = _neutral_M + (M_arr - _neutral_M) * _bss
            R_arr = _neutral_R + (R_arr - _neutral_R) * _bss
    elif base.get("perlin"):
        p_oct = base.get("perlin_octaves", 4)
        p_pers = base.get("perlin_persistence", 0.5)
        p_lac = base.get("perlin_lacunarity", 2.0)
        noise = perlin_multi_octave(base_shape, octaves=p_oct, persistence=p_pers, lacunarity=p_lac, seed=seed + 200 + _base_seed_offset)
        M_arr = base_M + noise * base.get("noise_M", 0) * _sm_base
        R_arr = base_R + noise * base.get("noise_R", 0) * _sm_base
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * _sm_base
        else:
            CC_arr = None
        # Lerp toward neutral when spec strength < 1.0
        if _bss < 0.999:
            _neutral_M, _neutral_R = 0.0, 128.0
            M_arr = _neutral_M + (M_arr - _neutral_M) * _bss
            R_arr = _neutral_R + (R_arr - _neutral_R) * _bss
    elif "noise_scales" in base:
        noise_weights = base.get("noise_weights", [1.0/len(base["noise_scales"])] * len(base["noise_scales"]))
        noise = multi_scale_noise(base_shape, base["noise_scales"], noise_weights, seed + 100 + _base_seed_offset)
        M_arr = base_M + noise * base.get("noise_M", 0) * _sm_base
        R_arr = base_R + noise * base.get("noise_R", 0) * _sm_base
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * _sm_base
        else:
            CC_arr = None
        # Lerp toward neutral when spec strength < 1.0
        if _bss < 0.999:
            _neutral_M, _neutral_R = 0.0, 128.0
            M_arr = _neutral_M + (M_arr - _neutral_M) * _bss
            R_arr = _neutral_R + (R_arr - _neutral_R) * _bss
    else:
        # Flat-value base (no noise/perlin/custom spec fn) — apply spec strength
        # by lerping toward "zero effect" neutral. bss=1.0 → full base values, bss=0 → flat paint.
        # Neutral = no metallic (M=0), mid roughness (R=128), minimal clearcoat.
        # Chrome at 5%: M≈13 (barely metallic), R≈122 (rough) — hint of chrome only.
        _neutral_M, _neutral_R = 0.0, 128.0
        M_arr = np.full(base_shape, _neutral_M + (base_M - _neutral_M) * _bss, dtype=np.float32)
        R_arr = np.full(base_shape, _neutral_R + (base_R - _neutral_R) * _bss, dtype=np.float32)
        CC_arr = None

    if base_scale != 1.0 and base_scale > 0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1]):
        M_arr = _resize_array(M_arr, shape[0], shape[1])
        R_arr = _resize_array(R_arr, shape[0], shape[1])
        if CC_arr is not None:
            CC_arr = _resize_array(CC_arr, shape[0], shape[1])

    # Transfer base spec arrays to GPU after generation + resize (they arrive as numpy)
    if _gpu_active:
        M_arr = to_gpu(M_arr)
        R_arr = to_gpu(R_arr)
        if CC_arr is not None:
            CC_arr = to_gpu(CC_arr)

    if cc_quality is not None:
        if base_CC > 0:
            cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        else:
            cc_value = (1.0 - float(cc_quality)) * 90.0
        if CC_arr is not None:
            CC_arr = CC_arr - float(base_CC) + cc_value
        else:
            CC_arr = xp.full(shape, cc_value, dtype=xp.float32)

    if blend_base and blend_base in BASE_REGISTRY and blend_base != base_id:
        base2 = BASE_REGISTRY[blend_base]
        base2_M = float(base2["M"])
        base2_R = float(base2["R"])
        base2_CC = int(base2["CC"]) if base2.get("CC") is not None else 16
        h, w = shape
        # np.any/np.where for bbox indices need CPU mask
        _mask_cpu_blend = to_cpu(mask) if _gpu_active else mask
        rows_active = np.any(_mask_cpu_blend > 0.1, axis=1)
        cols_active = np.any(_mask_cpu_blend > 0.1, axis=0)
        if np.any(rows_active) and np.any(cols_active):
            r_min, r_max = np.where(rows_active)[0][[0, -1]]
            c_min, c_max = np.where(cols_active)[0][[0, -1]]
            bbox_h = max(1, r_max - r_min + 1)
            bbox_w = max(1, c_max - c_min + 1)
        else:
            r_min, c_min = 0, 0
            bbox_h, bbox_w = h, w

        # Build gradient on CPU (linspace/mgrid slicing), then transfer to GPU
        if blend_dir == "vertical":
            grad = np.zeros((h, w), dtype=np.float32)
            zone_grad = np.linspace(0, 1, bbox_h, dtype=np.float32)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
            grad[r_min:r_min + bbox_h, :] = zone_grad
            grad[:r_min, :] = 0.0
            grad[r_min + bbox_h:, :] = 1.0
        elif blend_dir == "radial":
            cy = r_min + bbox_h / 2.0
            cx = c_min + bbox_w / 2.0
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            max_radius = np.sqrt((bbox_h / 2.0)**2 + (bbox_w / 2.0)**2) + 1e-8
            grad = np.sqrt((yy - cy)**2 + (xx - cx)**2) / max_radius
            grad = np.clip(grad, 0, 1)
        elif blend_dir == "diagonal":
            grad = np.zeros((h, w), dtype=np.float32)
            v_grad = np.linspace(0, 1, bbox_h, dtype=np.float32)[:, np.newaxis]
            h_grad = np.linspace(0, 1, bbox_w, dtype=np.float32)[np.newaxis, :]
            grad[r_min:r_min + bbox_h, c_min:c_min + bbox_w] = v_grad * 0.5 + h_grad * 0.5
            grad[:r_min, :] = 0.0
            grad[r_min + bbox_h:, :] = 1.0
            grad[:, :c_min] = 0.0
            grad[:, c_min + bbox_w:] = 1.0
        else:
            grad = np.zeros((h, w), dtype=np.float32)
            zone_grad = np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, bbox_w, dtype=np.float32)[np.newaxis, :]
            grad[:, c_min:c_min + bbox_w] = zone_grad
            grad[:, :c_min] = 0.0
            grad[:, c_min + bbox_w:] = 1.0

        ba = max(0.1, min(3.0, blend_amount * 2.0 + 0.1))
        grad = np.power(grad, ba)
        if _gpu_active:
            grad = to_gpu(grad)
        M_arr = M_arr * (1.0 - grad) + base2_M * grad
        R_arr = R_arr * (1.0 - grad) + base2_R * grad
        if CC_arr is not None:
            CC_arr = CC_arr * (1.0 - grad) + float(base2_CC) * grad
        elif base_CC != base2_CC:
            CC_arr = float(base_CC) * (1.0 - grad) + float(base2_CC) * grad

    if paint_color is not None and len(paint_color) >= 3:
        pr, pg, pb = float(paint_color[0]), float(paint_color[1]), float(paint_color[2])
        luminance = 0.299 * pr + 0.587 * pg + 0.114 * pb
        dark_boost = (1.0 - luminance) * 35.0 * sm
        R_arr = R_arr + dark_boost
        max_c = max(pr, pg, pb)
        min_c = min(pr, pg, pb)
        saturation = (max_c - min_c) / (max_c + 1e-8)
        if saturation > 0.3:
            sat_boost = (saturation - 0.3) * 30.0 * sm
            M_arr = M_arr + sat_boost
        if CC_arr is not None and luminance < 0.4:
            cc_haze = (0.4 - luminance) * 20.0 * sm
            CC_arr = CC_arr + cc_haze

    # Base placement: offset (pan), rotation, flip - reposition gradient/duo like patterns
    # _apply_pattern_offset uses np.roll, _rotate_single_array uses scipy -> need CPU
    _bo_x = max(0.0, min(1.0, float(base_offset_x if base_offset_x is not None else 0.5)))
    _bo_y = max(0.0, min(1.0, float(base_offset_y if base_offset_y is not None else 0.5)))
    _need_transform = (_bo_x != 0.5 or _bo_y != 0.5) or (abs(float(base_rotation if base_rotation is not None else 0) % 360.0) > 0.5) or base_flip_h or base_flip_v
    if _need_transform and _gpu_active:
        M_arr = to_cpu(M_arr)
        R_arr = to_cpu(R_arr)
        if CC_arr is not None:
            CC_arr = to_cpu(CC_arr)
    if _bo_x != 0.5 or _bo_y != 0.5:
        _apply_pattern_offset(M_arr, shape, _bo_x, _bo_y)
        _apply_pattern_offset(R_arr, shape, _bo_x, _bo_y)
        if CC_arr is not None:
            _apply_pattern_offset(CC_arr, shape, _bo_x, _bo_y)
    _bro = float(base_rotation if base_rotation is not None else 0) % 360.0
    if abs(_bro) > 0.5:
        M_arr = _rotate_single_array(M_arr, _bro, shape)
        R_arr = _rotate_single_array(R_arr, _bro, shape)
        if CC_arr is not None:
            CC_arr = _rotate_single_array(CC_arr, _bro, shape)
    if base_flip_h:
        M_arr = np.fliplr(M_arr)
        R_arr = np.fliplr(R_arr)
        if CC_arr is not None:
            CC_arr = np.fliplr(CC_arr)
    if base_flip_v:
        M_arr = np.flipud(M_arr)
        R_arr = np.flipud(R_arr)
        if CC_arr is not None:
            CC_arr = np.flipud(CC_arr)
    if _need_transform and _gpu_active:
        M_arr = to_gpu(M_arr)
        R_arr = to_gpu(R_arr)
        if CC_arr is not None:
            CC_arr = to_gpu(CC_arr)

    # --- Spec Pattern Overlays ---
    _spec_patterns = kwargs.get("spec_pattern_stack", []) or base.get("spec_pattern_stack", [])
    if _spec_patterns:
        from engine.spec_patterns import PATTERN_CATALOG
        for sp_layer in _spec_patterns:
            sp_name = sp_layer.get("pattern", "")
            sp_fn = PATTERN_CATALOG.get(sp_name)
            if sp_fn is None:
                continue
            sp_opacity = float(sp_layer.get("opacity", 0.5))
            sp_blend = sp_layer.get("blend_mode", "normal")
            sp_params = sp_layer.get("params", {})
            # Which channels to affect (default: M and R)
            sp_channels = sp_layer.get("channels", "MR")  # "M", "R", "CC", "MR", "MRC", etc.
            # Position/transform params
            sp_offset_x = float(sp_layer.get("offset_x", 0.5))
            sp_offset_y = float(sp_layer.get("offset_y", 0.5))
            sp_scale = float(sp_layer.get("scale", 1.0))
            sp_rotation = float(sp_layer.get("rotation", 0))
            sp_box_size = int(sp_layer.get("box_size", 100))
            # Generate pattern (returns 0-1 float32 numpy array) -> stays CPU for transforms
            _sp_seed = seed + 5000 + hash(sp_name) % 10000
            if sp_scale < 1.0 and abs(sp_scale - 1.0) > 0.01:
                # Scale down: regenerate at higher resolution then downsample (no tile seams)
                sp_arr = _scale_down_spec_pattern(sp_fn, sp_scale, base_shape, _sp_seed, _sm_base, sp_params)
            else:
                sp_arr = sp_fn(base_shape, _sp_seed, _sm_base, **sp_params)
                # Apply scale (crop for scale > 1)
                if abs(sp_scale - 1.0) > 0.01:
                    sp_arr = _crop_center_array(sp_arr, sp_scale, base_shape[0], base_shape[1])
            if abs(sp_rotation) > 0.5:
                sp_arr = _rotate_single_array(sp_arr, sp_rotation, base_shape)
            if abs(sp_offset_x - 0.5) > 0.01 or abs(sp_offset_y - 0.5) > 0.01:
                _apply_pattern_offset(sp_arr, base_shape, sp_offset_x, sp_offset_y)
            # Apply box size masking (restrict pattern to a sub-region)
            if sp_box_size < 100:
                sp_arr = _apply_spec_pattern_box_size(sp_arr, base_shape, sp_box_size, sp_offset_x, sp_offset_y)
            # Transfer to GPU for math
            if _gpu_active:
                sp_arr = to_gpu(sp_arr)
            # Convert 0-1 pattern to spec-range contribution
            # Pattern centered at 0.5 means no change; >0.5 = increase, <0.5 = decrease
            sp_delta = (sp_arr - 0.5) * 2.0  # -1 to +1 range
            sp_range = float(sp_layer.get("range", 40.0))  # How many spec units of variation
            sp_contrib = sp_delta * sp_range  # Actual spec contribution

            if "M" in sp_channels and M_arr is not None:
                M_arr = _apply_spec_blend_mode(M_arr, sp_contrib, sp_opacity, sp_blend)
                M_arr = xp.clip(M_arr, 0, 255).astype(xp.float32)
            if "R" in sp_channels and R_arr is not None:
                R_arr = _apply_spec_blend_mode(R_arr, sp_contrib, sp_opacity, sp_blend)
                R_arr = xp.clip(R_arr, 0, 255).astype(xp.float32)
            if "C" in sp_channels and CC_arr is not None:
                CC_arr = _apply_spec_blend_mode(CC_arr, sp_contrib, sp_opacity, sp_blend)
                CC_arr = xp.clip(CC_arr, 16, 255).astype(xp.float32)

    final_CC = CC_arr if CC_arr is not None else base_CC
    has_pattern = (pattern_id and pattern_id != "none" and pattern_id in PATTERN_REGISTRY)

    if has_pattern:
        pattern = PATTERN_REGISTRY[pattern_id]
        tex_fn = pattern.get("texture_fn")
        image_path = pattern.get("image_path")
        if image_path:
            from engine.render import _load_image_pattern
            pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if pv is not None:
                pv_min, pv_max = float(pv.min()), float(pv.max())
                if pv_max - pv_min > 1e-8:
                    pv = (pv - pv_min) / (pv_max - pv_min)
                else:
                    pv = np.zeros_like(pv)
                pv = pv.copy()
                _apply_pattern_offset(pv, shape, pattern_offset_x, pattern_offset_y)
                # Transfer to GPU for blending math
                if _gpu_active:
                    pv = to_gpu(pv)
                R_range, M_range = 60.0, 50.0
                _pat_scale = pattern_sm_eff * spec_mult * max(0.0, min(1.0, float(pattern_opacity)))
                # Mask the pattern so it only affects pixels INSIDE the zone
                pv_masked = pv * mask
                M_arr = M_arr + pv_masked * M_range * _pat_scale
                R_arr = R_arr + pv_masked * R_range * _pat_scale
        elif tex_fn is not None:
            # tex_fn needs CPU mask
            _mask_cpu_tex = to_cpu(mask) if _gpu_active else mask
            try:
                tex = tex_fn(shape, _mask_cpu_tex, seed, sm)
            except Exception as _tex_err:
                print(f"[compose] WARNING: tex_fn failed for pattern '{pattern_id}': {_tex_err}")
                tex = None
            if tex is not None:
                pv = tex["pattern_val"]
                R_range = tex["R_range"]
                M_range = tex["M_range"]

                if scale != 1.0 and scale > 0:
                    pv, tex = _scale_pattern_output(pv, tex, scale, shape)

                rot_angle = float(rotation) % 360
                if rot_angle != 0:
                    tex["pattern_val"] = pv
                    tex = _rotate_pattern_tex(tex, rot_angle, shape)
                    pv = tex["pattern_val"]
                pv = np.asarray(pv, dtype=np.float32).copy()
                _apply_pattern_offset(pv, shape, pattern_offset_x, pattern_offset_y)
                if pattern_flip_h:
                    pv = np.fliplr(pv)
                if pattern_flip_v:
                    pv = np.flipud(pv)

                M_pv = tex.get("M_pattern", pv)
                R_pv = tex.get("R_pattern", pv)
                CC_pv = tex.get("CC_pattern", None)

                # NOTE: M_pv/R_pv/CC_pv scaling was ALREADY handled by _scale_pattern_output above.
                if False and scale != 1.0 and scale > 0:  # DISABLED — was causing double-scale bug
                    if M_pv is not pv:
                        if scale < 1.0:
                            M_pv = _tile_fractional(M_pv, 1.0 / scale, shape[0], shape[1])
                        else:
                            M_pv = _crop_center_array(M_pv, scale, shape[0], shape[1])
                    if R_pv is not pv:
                        if scale < 1.0:
                            R_pv = _tile_fractional(R_pv, 1.0 / scale, shape[0], shape[1])
                        else:
                            R_pv = _crop_center_array(R_pv, scale, shape[0], shape[1])
                    if CC_pv is not None:
                        if scale < 1.0:
                            CC_pv = _tile_fractional(CC_pv, 1.0 / scale, shape[0], shape[1])
                        else:
                            CC_pv = _crop_center_array(CC_pv, scale, shape[0], shape[1])

                if rot_angle != 0:
                    if M_pv is not pv:
                        M_pv = _rotate_single_array(M_pv, rot_angle, shape)
                    if R_pv is not pv:
                        R_pv = _rotate_single_array(R_pv, rot_angle, shape)
                    if CC_pv is not None:
                        CC_pv = _rotate_single_array(CC_pv, rot_angle, shape)

                # Transfer pattern arrays to GPU for blending
                if _gpu_active:
                    M_pv = to_gpu(M_pv)
                    R_pv = to_gpu(R_pv)
                    if CC_pv is not None:
                        CC_pv = to_gpu(CC_pv)

                _pat_scale = pattern_sm_eff * spec_mult * max(0.0, min(1.0, float(pattern_opacity)))
                M_arr = M_arr + M_pv * M_range * _pat_scale
                R_arr = R_arr + R_pv * R_range * _pat_scale

                CC_range = tex.get("CC_range", 0)
                if CC_pv is not None and CC_range != 0:
                    if CC_arr is not None:
                        CC_arr = CC_arr + CC_pv * CC_range * _pat_scale
                    elif base_CC > 0:
                        CC_arr = xp.full(shape, float(base_CC), dtype=xp.float32) + CC_pv * CC_range * _pat_scale

                if "R_extra" in tex:
                    _r_extra = to_gpu(tex["R_extra"]) if _gpu_active else tex["R_extra"]
                    R_arr = R_arr + _r_extra * _pat_scale
                if "M_extra" in tex:
                    _m_extra = to_gpu(tex["M_extra"]) if _gpu_active else tex["M_extra"]
                    M_arr = M_arr + _m_extra * _pat_scale

                pat_CC = tex.get("CC")
                if pat_CC is None:
                    pass
                elif isinstance(pat_CC, np.ndarray):
                    final_CC = to_gpu(pat_CC) if _gpu_active else pat_CC
                else:
                    final_CC = int(pat_CC)

    # GPU-accelerate final spec assembly (mask blending + clipping)
    # M_arr/R_arr/mask are already on GPU when _gpu_active
    # CONDITIONAL GGX FLOOR: R >= 15 for non-chrome (M < 240), R >= 0 for chrome (M >= 240)
    # This is the FINAL safety net — catches any upstream spec function that missed the floor.
    if _gpu_active:
        M_final = M_arr * mask + 5.0 * (1 - mask)
        R_final = R_arr * mask + 100.0 * (1 - mask)
        spec[:,:,0] = to_cpu(xp.clip(M_final, 0, 255).astype(xp.uint8))
        # Conditional GGX floor via helper
        spec[:,:,1] = to_cpu(_ggx_safe_R(R_final, M_final, lib=xp).astype(xp.uint8))
        _is_cc_arr = hasattr(final_CC, 'shape')  # works for both numpy and cupy arrays
        if _is_cc_arr:
            final_CC = to_gpu(final_CC)  # ensure on GPU
            spec[:,:,2] = to_cpu(xp.clip(final_CC * mask, 0, 255).astype(xp.uint8))
        else:
            _mask_cpu_cc = to_cpu(mask)
            spec[:,:,2] = np.where(_mask_cpu_cc > 0.5, final_CC, 0).astype(np.uint8)
        spec[:,:,3] = 255
    else:
        M_final = M_arr * mask + 5.0 * (1 - mask)
        R_final = R_arr * mask + 100.0 * (1 - mask)
        spec[:,:,0] = np.clip(M_final, 0, 255).astype(np.uint8)
        # Conditional GGX floor via helper
        spec[:,:,1] = _ggx_safe_R(R_final, M_final).astype(np.uint8)
        if isinstance(final_CC, np.ndarray):
            spec[:,:,2] = np.clip(final_CC * mask, 0, 255).astype(np.uint8)
        else:
            spec[:,:,2] = np.where(mask > 0.5, final_CC, 0).astype(np.uint8)
        spec[:,:,3] = 255

    # From here on, mask is needed as CPU for overlay functions — transfer back
    if _gpu_active:
        mask = to_cpu(mask)

    if second_base and second_base_strength > 0.001:
        try:
            _sb_seed = seed + 999
            _sb_seed_off = abs(hash(second_base)) % 10000
            spec_secondary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            # Strip mono: prefix if the ID is actually a base (migrated finishes)
            if str(second_base).startswith("mono:"):
                _sb_stripped = second_base[5:]
                if monolithic_registry is not None and _sb_stripped in monolithic_registry:
                    _sb_spec_fn = monolithic_registry[_sb_stripped][0]
                    spec_secondary = _sb_spec_fn(shape, mask, _sb_seed + _sb_seed_off, sm)
                elif _sb_stripped in BASE_REGISTRY:
                    second_base = _sb_stripped  # fallback: treat as base
            if second_base in BASE_REGISTRY:
                _sb_def = BASE_REGISTRY[second_base]
                _sb_M = float(_sb_def["M"])
                _sb_R = float(_sb_def["R"])
                _sb_CC = int(_sb_def.get("CC", 16))
                if _sb_def.get("base_spec_fn"):
                    _sb_result = _sb_def["base_spec_fn"](shape, _sb_seed + _sb_seed_off, sm, _sb_M, _sb_R)
                    _sb_M_arr = _sb_result[0]
                    _sb_R_arr = _sb_result[1]
                    _sb_CC_arr = _sb_result[2] if len(_sb_result) > 2 else np.full(shape, float(_sb_CC))
                elif _sb_def.get("perlin"):
                    _sb_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], _sb_seed + _sb_seed_off)
                    _sb_M_arr = _sb_M + _sb_noise * _sb_def.get("noise_M", 0) * sm
                    _sb_R_arr = _sb_R + _sb_noise * _sb_def.get("noise_R", 0) * sm
                    _sb_CC_arr = np.full(shape, float(_sb_CC))
                else:
                    _sb_M_arr = np.full(shape, _sb_M)
                    _sb_R_arr = np.full(shape, _sb_R)
                    _sb_CC_arr = np.full(shape, float(_sb_CC))
                _sb_M_final = _sb_M_arr * mask + 5.0 * (1 - mask)
                _sb_R_final = _sb_R_arr * mask + 100.0 * (1 - mask)
                spec_secondary[:,:,0] = np.clip(_sb_M_final, 0, 255).astype(np.uint8)
                spec_secondary[:,:,1] = _ggx_safe_R(_sb_R_final, _sb_M_final).astype(np.uint8)
                spec_secondary[:,:,2] = np.clip(_sb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_secondary[:,:,3] = 255

            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_sb = None if second_base_pattern == '__none__' else (second_base_pattern if second_base_pattern else pattern_id)
            pattern_mask = _get_pattern_mask(_pat_id_sb, shape, mask, seed, sm,
                scale=second_base_pattern_scale, rotation=second_base_pattern_rotation,
                opacity=second_base_pattern_opacity, strength=second_base_pattern_strength,
                offset_x=second_base_pattern_offset_x, offset_y=second_base_pattern_offset_y) if _pat_id_sb else None
            if pattern_mask is not None:
                if second_base_pattern_invert:
                    pattern_mask = 1.0 - pattern_mask
                if second_base_pattern_harden:
                    pattern_mask = np.clip((pattern_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            spec, _ = blend_dual_base_spec(
                spec, spec_secondary,
                strength=second_base_spec_strength,
                blend_mode=second_base_blend_mode,
                noise_scale=second_base_noise_scale,
                seed=seed,
                pattern_mask=pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=second_base_scale
            )
        except Exception:
            pass

    if third_base and third_base_strength > 0.001:
        try:
            _tb_seed = seed + 1999
            _tb_seed_off = abs(hash(third_base)) % 10000
            spec_tertiary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(third_base).startswith("mono:"):
                _tb_stripped = third_base[5:]
                if monolithic_registry is not None and _tb_stripped in monolithic_registry:
                    _tb_spec_fn = monolithic_registry[_tb_stripped][0]
                    spec_tertiary = _tb_spec_fn(shape, mask, _tb_seed + _tb_seed_off, sm)
                elif _tb_stripped in BASE_REGISTRY:
                    third_base = _tb_stripped
            if third_base in BASE_REGISTRY:
                _tb_def = BASE_REGISTRY[third_base]
                _tb_M = float(_tb_def["M"])
                _tb_R = float(_tb_def["R"])
                _tb_CC = int(_tb_def.get("CC", 16))
                if _tb_def.get("base_spec_fn"):
                    _tb_result = _tb_def["base_spec_fn"](shape, _tb_seed + _tb_seed_off, sm, _tb_M, _tb_R)
                    _tb_M_arr = _tb_result[0]
                    _tb_R_arr = _tb_result[1]
                    _tb_CC_arr = _tb_result[2] if len(_tb_result) > 2 else np.full(shape, float(_tb_CC))
                elif _tb_def.get("perlin"):
                    _tb_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], _tb_seed + _tb_seed_off)
                    _tb_M_arr = _tb_M + _tb_noise * _tb_def.get("noise_M", 0) * sm
                    _tb_R_arr = _tb_R + _tb_noise * _tb_def.get("noise_R", 0) * sm
                    _tb_CC_arr = np.full(shape, float(_tb_CC))
                else:
                    _tb_M_arr = np.full(shape, _tb_M)
                    _tb_R_arr = np.full(shape, _tb_R)
                    _tb_CC_arr = np.full(shape, float(_tb_CC))
                _tb_M_final = _tb_M_arr * mask + 5.0 * (1 - mask)
                _tb_R_final = _tb_R_arr * mask + 100.0 * (1 - mask)
                spec_tertiary[:,:,0] = np.clip(_tb_M_final, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,1] = _ggx_safe_R(_tb_R_final, _tb_M_final).astype(np.uint8)
                spec_tertiary[:,:,2] = np.clip(_tb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,3] = 255
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = None if third_base_pattern == '__none__' else (third_base_pattern if third_base_pattern else pattern_id)
            _tb_pattern_mask = _get_pattern_mask(_pat_id_tb, shape, mask, seed, sm,
                scale=third_base_pattern_scale, rotation=third_base_pattern_rotation,
                opacity=third_base_pattern_opacity, strength=third_base_pattern_strength,
                offset_x=third_base_pattern_offset_x, offset_y=third_base_pattern_offset_y) if _pat_id_tb else None
            if _tb_pattern_mask is not None:
                if third_base_pattern_invert:
                    _tb_pattern_mask = 1.0 - _tb_pattern_mask
                if third_base_pattern_harden:
                    _tb_pattern_mask = np.clip((_tb_pattern_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            spec, _ = blend_dual_base_spec(
                spec, spec_tertiary,
                strength=third_base_spec_strength,
                blend_mode=third_base_blend_mode,
                noise_scale=third_base_noise_scale,
                seed=seed + 8888,
                pattern_mask=_tb_pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=max(0.01, min(5.0, float(third_base_scale)))
            )
        except Exception:
            pass

    # --- Overlay Spec Pattern Stack (applied after all base blending) ---
    _overlay_spec_patterns = kwargs.get("overlay_spec_pattern_stack", [])
    if _overlay_spec_patterns:
        try:
            from engine.spec_patterns import PATTERN_CATALOG
            # Work on float32 M/R/CC extracted from spec
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _overlay_spec_patterns:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = PATTERN_CATALOG.get(_ovsp_name)
                if _ovsp_fn is None:
                    continue
                _ovsp_opacity = float(_ovsp.get("opacity", 0.5))
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 40.0))
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = seed + 7000 + hash(_ovsp_name) % 10000
                if _ovsp_scale < 1.0 and abs(_ovsp_scale - 1.0) > 0.01:
                    _ovsp_arr = _scale_down_spec_pattern(_ovsp_fn, _ovsp_scale, shape, _ovsp_seed, sm, _ovsp_params)
                else:
                    _ovsp_arr = _ovsp_fn(shape, _ovsp_seed, sm, **_ovsp_params)
                    if abs(_ovsp_scale - 1.0) > 0.01:
                        _oh, _ow = shape[0], shape[1]
                        _ovsp_arr = _crop_center_array(_ovsp_arr, _ovsp_scale, _oh, _ow)
                if abs(_ovsp_rotation) > 0.5:
                    _ovsp_arr = _rotate_single_array(_ovsp_arr, _ovsp_rotation, shape)
                if abs(_ovsp_offset_x - 0.5) > 0.01 or abs(_ovsp_offset_y - 0.5) > 0.01:
                    _apply_pattern_offset(_ovsp_arr, shape, _ovsp_offset_x, _ovsp_offset_y)
                if _ovsp_box_size < 100:
                    _ovsp_arr = _apply_spec_pattern_box_size(_ovsp_arr, shape, _ovsp_box_size, _ovsp_offset_x, _ovsp_offset_y)
                _ovsp_delta = (_ovsp_arr - 0.5) * 2.0
                _ovsp_contrib = _ovsp_delta * _ovsp_range
                if "M" in _ovsp_channels:
                    _ov_M = _apply_spec_blend_mode(_ov_M, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_M = np.clip(_ov_M, 0, 255).astype(np.float32)
                if "R" in _ovsp_channels:
                    _ov_R = _apply_spec_blend_mode(_ov_R, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_R = np.clip(_ov_R, 0, 255).astype(np.float32)
                if "C" in _ovsp_channels:
                    _ov_CC = _apply_spec_blend_mode(_ov_CC, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_CC = np.clip(_ov_CC, 16, 255).astype(np.float32)
            # Write back, respecting zone mask
            spec[:,:,0] = np.clip(_ov_M * mask + spec[:,:,0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * mask + spec[:,:,1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * mask + spec[:,:,2].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
        except Exception:
            pass

    def _apply_named_overlay_spec_stack(stack_key, seed_offset):
        _stack = kwargs.get(stack_key, [])
        if not _stack:
            return
        try:
            from engine.spec_patterns import PATTERN_CATALOG
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _stack:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = PATTERN_CATALOG.get(_ovsp_name)
                if _ovsp_fn is None:
                    continue
                _ovsp_opacity = float(_ovsp.get("opacity", 0.5))
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 40.0))
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = seed + seed_offset + hash(_ovsp_name) % 10000
                if _ovsp_scale < 1.0 and abs(_ovsp_scale - 1.0) > 0.01:
                    _ovsp_arr = _scale_down_spec_pattern(_ovsp_fn, _ovsp_scale, shape, _ovsp_seed, sm, _ovsp_params)
                else:
                    _ovsp_arr = _ovsp_fn(shape, _ovsp_seed, sm, **_ovsp_params)
                    if abs(_ovsp_scale - 1.0) > 0.01:
                        _oh, _ow = shape[0], shape[1]
                        _ovsp_arr = _crop_center_array(_ovsp_arr, _ovsp_scale, _oh, _ow)
                if abs(_ovsp_rotation) > 0.5:
                    _ovsp_arr = _rotate_single_array(_ovsp_arr, _ovsp_rotation, shape)
                if abs(_ovsp_offset_x - 0.5) > 0.01 or abs(_ovsp_offset_y - 0.5) > 0.01:
                    _apply_pattern_offset(_ovsp_arr, shape, _ovsp_offset_x, _ovsp_offset_y)
                if _ovsp_box_size < 100:
                    _ovsp_arr = _apply_spec_pattern_box_size(_ovsp_arr, shape, _ovsp_box_size, _ovsp_offset_x, _ovsp_offset_y)
                _ovsp_delta = (_ovsp_arr - 0.5) * 2.0
                _ovsp_contrib = _ovsp_delta * _ovsp_range
                if "M" in _ovsp_channels:
                    _ov_M = _apply_spec_blend_mode(_ov_M, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_M = np.clip(_ov_M, 0, 255).astype(np.float32)
                if "R" in _ovsp_channels:
                    _ov_R = _apply_spec_blend_mode(_ov_R, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_R = np.clip(_ov_R, 0, 255).astype(np.float32)
                if "C" in _ovsp_channels:
                    _ov_CC = _apply_spec_blend_mode(_ov_CC, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_CC = np.clip(_ov_CC, 16, 255).astype(np.float32)
            spec[:,:,0] = np.clip(_ov_M * mask + spec[:,:,0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * mask + spec[:,:,1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * mask + spec[:,:,2].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
        except Exception:
            pass

    _apply_named_overlay_spec_stack("third_overlay_spec_pattern_stack", 8000)
    _apply_named_overlay_spec_stack("fourth_overlay_spec_pattern_stack", 9000)
    _apply_named_overlay_spec_stack("fifth_overlay_spec_pattern_stack", 10000)

    _ms = int((_time.time() - _t_compose) * 1000)
    if _gpu_active:
        print(f"[GPU] compose_finish: {_ms}ms (GPU)")
    return spec


def compose_finish_stacked(base_id, all_patterns, shape, mask, seed, sm, spec_mult=1.0, base_scale=1.0, base_strength=1.0, base_spec_strength=1.0, base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0, base_flip_h=False, base_flip_v=False, pattern_opacity=1.0, cc_quality=None, blend_base=None, blend_dir="horizontal", blend_amount=0.5, paint_color=None,
                           second_base=None, second_base_color=None, second_base_strength=0.0, second_base_spec_strength=1.0,
                           second_base_blend_mode="noise", second_base_noise_scale=24,
                           second_base_scale=1.0, second_base_pattern=None,
                           second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                           second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                           second_base_pattern_invert=False, second_base_pattern_harden=False,
                           third_base=None, third_base_color=None, third_base_strength=0.0, third_base_spec_strength=1.0,
                           third_base_blend_mode="noise", third_base_noise_scale=24,
                           third_base_scale=1.0, third_base_pattern=None,
                           third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                           third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                           third_base_pattern_invert=False, third_base_pattern_harden=False,
                           second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                           third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                           fourth_base=None, fourth_base_color=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0,
                           fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                           fourth_base_scale=1.0, fourth_base_pattern=None,
                           fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                           fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                           fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                           fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                           fifth_base=None, fifth_base_color=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0,
                           fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                           fifth_base_scale=1.0, fifth_base_pattern=None,
                           fifth_base_pattern_scale=1.0, fifth_base_pattern_rotation=0.0,
                           fifth_base_pattern_opacity=1.0, fifth_base_pattern_strength=1.0,
                           fifth_base_pattern_invert=False, fifth_base_pattern_harden=False,
                           fifth_base_pattern_offset_x=0.5, fifth_base_pattern_offset_y=0.5,
                           pattern_sm=None,
                           pattern_offset_x=0.5, pattern_offset_y=0.5, 
                           pattern_flip_h=False, pattern_flip_v=False,
                           pattern_intensity=1.0,
                           base_spec_blend_mode="normal",
                           **kwargs):
    """Compose a base material + MULTIPLE stacked patterns into a final spec map.
    base_spec_blend_mode: master override for how pattern spec contributions blend with base spec."""
    monolithic_registry = kwargs.pop("monolithic_registry", None)
    _gpu_active = is_gpu()
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    if pattern_sm is None:
        pattern_sm = sm
    _pat_int_raw = max(0.0, min(1.0, float(pattern_intensity)))
    _pat_int = _pat_int_raw ** 0.5 if _pat_int_raw > 0 else 0.0  # perceptual curve
    pattern_sm_eff = pattern_sm * _pat_int  # sqrt curve: 5%→22%, 50%→71%, 100%→100%
    # NOTE: base_strength is a paint slider, handled in compose_paint_mod_stacked — not used in spec compositing.
    _sm_base = sm * max(0.0, min(2.0, float(base_spec_strength)))
    base = BASE_REGISTRY[base_id]
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)  # stays CPU (uint8 output)
    base_M = float(base["M"])
    base_R = float(base["R"])
    base_CC = int(base["CC"]) if base.get("CC") is not None else 16

    # Transfer mask to GPU at entry
    if _gpu_active:
        mask = to_gpu(mask)

    if base_scale != 1.0 and base_scale > 0:
        MAX_BASE_DIM = 4096
        base_h = min(MAX_BASE_DIM, max(4, int(shape[0] / base_scale)))
        base_w = min(MAX_BASE_DIM, max(4, int(shape[1] / base_scale)))
        base_shape = (base_h, base_w)
    else:
        base_shape = shape

    CC_arr = None
    _bss = max(0.0, min(2.0, float(base_spec_strength)))
    _base_seed_offset = abs(hash(base_id)) % 10000
    if base.get("base_spec_fn"):
        spec_result = base["base_spec_fn"](base_shape, seed + _base_seed_offset, _sm_base, base_M, base_R)
        if len(spec_result) == 3:
            M_arr, R_arr, CC_arr = spec_result
        else:
            M_arr, R_arr = spec_result
            CC_arr = None
        # Scale spec variation by base_spec_strength so the slider works
        if _bss < 0.999 or _bss > 1.001:
            M_arr = base_M + (M_arr - base_M) * _bss
            R_arr = base_R + (R_arr - base_R) * _bss
            if CC_arr is not None:
                CC_arr = float(base_CC) + (CC_arr - float(base_CC)) * _bss
    elif base.get("brush_grain"):
        rng = np.random.RandomState(seed)
        noise = np.tile(rng.randn(1, base_shape[1]) * 0.5, (base_shape[0], 1))
        noise += rng.randn(base_shape[0], base_shape[1]) * 0.2
        M_arr = base_M + noise * base.get("noise_M", 0) * _sm_base
        R_arr = base_R + noise * base.get("noise_R", 0) * _sm_base
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * _sm_base
        if _bss < 0.999:
            _neutral_M, _neutral_R = 0.0, 128.0
            M_arr = _neutral_M + (M_arr - _neutral_M) * _bss
            R_arr = _neutral_R + (R_arr - _neutral_R) * _bss
    elif base.get("perlin"):
        p_oct = base.get("perlin_octaves", 4)
        p_pers = base.get("perlin_persistence", 0.5)
        p_lac = base.get("perlin_lacunarity", 2.0)
        noise = perlin_multi_octave(base_shape, octaves=p_oct, persistence=p_pers, lacunarity=p_lac, seed=seed + 200)
        M_arr = base_M + noise * base.get("noise_M", 0) * _sm_base
        R_arr = base_R + noise * base.get("noise_R", 0) * _sm_base
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * _sm_base
        if _bss < 0.999:
            _neutral_M, _neutral_R = 0.0, 128.0
            M_arr = _neutral_M + (M_arr - _neutral_M) * _bss
            R_arr = _neutral_R + (R_arr - _neutral_R) * _bss
    elif "noise_scales" in base:
        noise_weights = base.get("noise_weights", [1.0/len(base["noise_scales"])] * len(base["noise_scales"]))
        noise = multi_scale_noise(base_shape, base["noise_scales"], noise_weights, seed + 100)
        M_arr = base_M + noise * base.get("noise_M", 0) * _sm_base
        R_arr = base_R + noise * base.get("noise_R", 0) * _sm_base
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * _sm_base
        if _bss < 0.999:
            _neutral_M, _neutral_R = 0.0, 128.0
            M_arr = _neutral_M + (M_arr - _neutral_M) * _bss
            R_arr = _neutral_R + (R_arr - _neutral_R) * _bss
    else:
        # Flat-value base (no noise/perlin/custom spec fn) — apply spec strength
        # by lerping toward "zero effect" neutral. bss=1.0 → full base values, bss=0 → flat paint.
        # Neutral = no metallic (M=0), mid roughness (R=128), minimal clearcoat.
        # Chrome at 5%: M≈13 (barely metallic), R≈122 (rough) — hint of chrome only.
        _neutral_M, _neutral_R = 0.0, 128.0
        M_arr = np.full(base_shape, _neutral_M + (base_M - _neutral_M) * _bss, dtype=np.float32)
        R_arr = np.full(base_shape, _neutral_R + (base_R - _neutral_R) * _bss, dtype=np.float32)

    if base_scale != 1.0 and base_scale > 0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1]):
        M_arr = _resize_array(M_arr, shape[0], shape[1])
        R_arr = _resize_array(R_arr, shape[0], shape[1])
        if CC_arr is not None:
            CC_arr = _resize_array(CC_arr, shape[0], shape[1])

    # Transfer base spec arrays to GPU after generation + resize
    if _gpu_active:
        M_arr = to_gpu(M_arr)
        R_arr = to_gpu(R_arr)
        if CC_arr is not None:
            CC_arr = to_gpu(CC_arr)

    if cc_quality is not None and base_CC > 0:
        cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        if CC_arr is not None:
            CC_arr = CC_arr - float(base_CC) + cc_value
        else:
            CC_arr = xp.full(shape, cc_value, dtype=xp.float32)

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
        if _gpu_active:
            grad = to_gpu(grad)
        M_arr = M_arr * (1.0 - grad) + base2_M * grad
        R_arr = R_arr * (1.0 - grad) + base2_R * grad
        if CC_arr is not None:
            CC_arr = CC_arr * (1.0 - grad) + float(base2_CC) * grad
        elif base_CC != base2_CC:
            CC_arr = float(base_CC) * (1.0 - grad) + float(base2_CC) * grad

    if paint_color is not None and len(paint_color) >= 3:
        pr, pg, pb = float(paint_color[0]), float(paint_color[1]), float(paint_color[2])
        luminance = 0.299 * pr + 0.587 * pg + 0.114 * pb
        dark_boost = (1.0 - luminance) * 35.0 * sm
        R_arr = R_arr + dark_boost
        max_c = max(pr, pg, pb)
        min_c = min(pr, pg, pb)
        saturation = (max_c - min_c) / (max_c + 1e-8)
        if saturation > 0.3:
            sat_boost = (saturation - 0.3) * 30.0 * sm
            M_arr = M_arr + sat_boost
        if CC_arr is not None and luminance < 0.4:
            cc_haze = (0.4 - luminance) * 20.0 * sm
            CC_arr = CC_arr + cc_haze

    # Base placement: offset, rotation, flip — need CPU for np.roll/scipy
    _bo_x = max(0.0, min(1.0, float(base_offset_x if base_offset_x is not None else 0.5)))
    _bo_y = max(0.0, min(1.0, float(base_offset_y if base_offset_y is not None else 0.5)))
    _need_transform = (_bo_x != 0.5 or _bo_y != 0.5) or (abs(float(base_rotation if base_rotation is not None else 0) % 360.0) > 0.5) or base_flip_h or base_flip_v
    if _need_transform and _gpu_active:
        M_arr = to_cpu(M_arr)
        R_arr = to_cpu(R_arr)
        if CC_arr is not None:
            CC_arr = to_cpu(CC_arr)
    if _bo_x != 0.5 or _bo_y != 0.5:
        _apply_pattern_offset(M_arr, shape, _bo_x, _bo_y)
        _apply_pattern_offset(R_arr, shape, _bo_x, _bo_y)
        if CC_arr is not None:
            _apply_pattern_offset(CC_arr, shape, _bo_x, _bo_y)
    _bro = float(base_rotation if base_rotation is not None else 0) % 360.0
    if abs(_bro) > 0.5:
        M_arr = _rotate_single_array(M_arr, _bro, shape)
        R_arr = _rotate_single_array(R_arr, _bro, shape)
        if CC_arr is not None:
            CC_arr = _rotate_single_array(CC_arr, _bro, shape)
    if base_flip_h:
        M_arr = np.fliplr(M_arr)
        R_arr = np.fliplr(R_arr)
        if CC_arr is not None:
            CC_arr = np.fliplr(CC_arr)
    if base_flip_v:
        M_arr = np.flipud(M_arr)
        R_arr = np.flipud(R_arr)
        if CC_arr is not None:
            CC_arr = np.flipud(CC_arr)
    if _need_transform and _gpu_active:
        M_arr = to_gpu(M_arr)
        R_arr = to_gpu(R_arr)
        if CC_arr is not None:
            CC_arr = to_gpu(CC_arr)

    # --- Spec Pattern Overlays ---
    _spec_patterns = kwargs.get("spec_pattern_stack", []) or base.get("spec_pattern_stack", [])
    if _spec_patterns:
        from engine.spec_patterns import PATTERN_CATALOG
        for sp_layer in _spec_patterns:
            sp_name = sp_layer.get("pattern", "")
            sp_fn = PATTERN_CATALOG.get(sp_name)
            if sp_fn is None:
                continue
            sp_opacity = float(sp_layer.get("opacity", 0.5))
            sp_blend = sp_layer.get("blend_mode", "normal")
            sp_params = sp_layer.get("params", {})
            sp_channels = sp_layer.get("channels", "MR")
            sp_offset_x = float(sp_layer.get("offset_x", 0.5))
            sp_offset_y = float(sp_layer.get("offset_y", 0.5))
            sp_scale = float(sp_layer.get("scale", 1.0))
            sp_rotation = float(sp_layer.get("rotation", 0))
            sp_box_size = int(sp_layer.get("box_size", 100))
            # Generate pattern (CPU) -> transform (CPU) -> transfer to GPU
            _sp_seed = seed + 5000 + hash(sp_name) % 10000
            if sp_scale < 1.0 and abs(sp_scale - 1.0) > 0.01:
                # Scale down: regenerate at higher resolution then downsample (no tile seams)
                sp_arr = _scale_down_spec_pattern(sp_fn, sp_scale, base_shape, _sp_seed, _sm_base, sp_params)
            else:
                sp_arr = sp_fn(base_shape, _sp_seed, _sm_base, **sp_params)
                # Apply scale (crop for scale > 1)
                if abs(sp_scale - 1.0) > 0.01:
                    sp_arr = _crop_center_array(sp_arr, sp_scale, base_shape[0], base_shape[1])
            if abs(sp_rotation) > 0.5:
                sp_arr = _rotate_single_array(sp_arr, sp_rotation, base_shape)
            if abs(sp_offset_x - 0.5) > 0.01 or abs(sp_offset_y - 0.5) > 0.01:
                _apply_pattern_offset(sp_arr, base_shape, sp_offset_x, sp_offset_y)
            # Apply box size masking (restrict pattern to a sub-region)
            if sp_box_size < 100:
                sp_arr = _apply_spec_pattern_box_size(sp_arr, base_shape, sp_box_size, sp_offset_x, sp_offset_y)
            if _gpu_active:
                sp_arr = to_gpu(sp_arr)
            sp_delta = (sp_arr - 0.5) * 2.0
            sp_range = float(sp_layer.get("range", 40.0))
            sp_contrib = sp_delta * sp_range

            if "M" in sp_channels and M_arr is not None:
                M_arr = _apply_spec_blend_mode(M_arr, sp_contrib, sp_opacity, sp_blend)
                M_arr = xp.clip(M_arr, 0, 255).astype(xp.float32)
            if "R" in sp_channels and R_arr is not None:
                R_arr = _apply_spec_blend_mode(R_arr, sp_contrib, sp_opacity, sp_blend)
                R_arr = xp.clip(R_arr, 0, 255).astype(xp.float32)
            if "C" in sp_channels and CC_arr is not None:
                CC_arr = _apply_spec_blend_mode(CC_arr, sp_contrib, sp_opacity, sp_blend)
                CC_arr = xp.clip(CC_arr, 16, 255).astype(xp.float32)

    if CC_arr is not None:
        final_CC = CC_arr.copy()
    else:
        final_CC = xp.full(shape, float(base_CC), dtype=xp.float32)

    _mask_cpu_stk = to_cpu(mask) if _gpu_active else mask
    for layer_idx, layer in enumerate(all_patterns):
        pat_id = layer["id"]
        opacity = float(layer.get("opacity", 1.0))
        scale = float(layer.get("scale", 1.0))
        if pat_id not in PATTERN_REGISTRY or opacity <= 0:
            continue
        pattern = PATTERN_REGISTRY[pat_id]
        tex_fn = pattern.get("texture_fn")
        image_path = pattern.get("image_path")
        if image_path:
            from engine.render import _load_image_pattern
            pv = _load_image_pattern(image_path, shape, scale=scale, rotation=float(layer.get("rotation", 0)))
            if pv is not None:
                pv_min, pv_max = float(pv.min()), float(pv.max())
                if pv_max - pv_min > 1e-8:
                    pv = (pv - pv_min) / (pv_max - pv_min)
                else:
                    pv = np.zeros_like(pv)
                _img_ox = float(layer.get("offset_x", pattern_offset_x))
                _img_oy = float(layer.get("offset_y", pattern_offset_y))
                if abs(_img_ox - 0.5) > 0.001 or abs(_img_oy - 0.5) > 0.001:
                    _apply_pattern_offset(pv, shape, _img_ox, _img_oy)
                if _gpu_active:
                    pv = to_gpu(pv)
                pv_masked = pv * mask
                M_contrib = pv_masked * 50.0 * pattern_sm_eff * spec_mult
                R_contrib = pv_masked * 60.0 * pattern_sm_eff * spec_mult
                _eff_blend = base_spec_blend_mode if base_spec_blend_mode != "normal" else layer.get("blend_mode", "normal")
                M_arr = _apply_spec_blend_mode(M_arr, M_contrib, opacity, _eff_blend)
                R_arr = _apply_spec_blend_mode(R_arr, R_contrib, opacity, _eff_blend)
            continue
        if tex_fn is None:
            continue
        layer_seed = seed + layer_idx * 7
        try:
            tex = tex_fn(shape, _mask_cpu_stk, layer_seed, sm)
        except Exception as _tex_err_stk:
            print(f"[compose] WARNING: tex_fn failed for pattern '{pat_id}': {_tex_err_stk}")
            continue
        pv = tex["pattern_val"]
        R_range = tex["R_range"]
        M_range = tex["M_range"]
        if scale != 1.0 and scale > 0:
            pv, tex = _scale_pattern_output(pv, tex, scale, shape)
        layer_rotation = float(layer.get("rotation", 0)) % 360
        if layer_rotation != 0:
            tex["pattern_val"] = pv
            tex = _rotate_pattern_tex(tex, layer_rotation, shape)
            pv = tex["pattern_val"]
        M_pv = tex.get("M_pattern", pv)
        R_pv = tex.get("R_pattern", pv)
        CC_pv = tex.get("CC_pattern", None)
        if scale != 1.0 and scale > 0:
            if M_pv is not pv:
                if scale < 1.0:
                    M_pv = _tile_fractional(M_pv, 1.0 / scale, shape[0], shape[1])
                else:
                    M_pv = _crop_center_array(M_pv, scale, shape[0], shape[1])
            if R_pv is not pv:
                if scale < 1.0:
                    R_pv = _tile_fractional(R_pv, 1.0 / scale, shape[0], shape[1])
                else:
                    R_pv = _crop_center_array(R_pv, scale, shape[0], shape[1])
            if CC_pv is not None:
                if scale < 1.0:
                    CC_pv = _tile_fractional(CC_pv, 1.0 / scale, shape[0], shape[1])
                else:
                    CC_pv = _crop_center_array(CC_pv, scale, shape[0], shape[1])
        if layer_rotation != 0:
            if M_pv is not pv:
                M_pv = _rotate_single_array(M_pv, layer_rotation, shape)
            if R_pv is not pv:
                R_pv = _rotate_single_array(R_pv, layer_rotation, shape)
            if CC_pv is not None:
                CC_pv = _rotate_single_array(CC_pv, layer_rotation, shape)
        blend_mode = layer.get("blend_mode", "normal")
        _p_ox = float(layer.get("offset_x", pattern_offset_x))
        _p_oy = float(layer.get("offset_y", pattern_offset_y))
        if abs(_p_ox - 0.5) > 0.001 or abs(_p_oy - 0.5) > 0.001:
            _apply_pattern_offset(pv, shape, _p_ox, _p_oy)
            if M_pv is not pv:
                _apply_pattern_offset(M_pv, shape, _p_ox, _p_oy)
            if R_pv is not pv:
                _apply_pattern_offset(R_pv, shape, _p_ox, _p_oy)
            if CC_pv is not None:
                _apply_pattern_offset(CC_pv, shape, _p_ox, _p_oy)
        # Transfer pattern arrays to GPU for blending
        if _gpu_active:
            M_pv = to_gpu(M_pv)
            R_pv = to_gpu(R_pv)
            if CC_pv is not None:
                CC_pv = to_gpu(CC_pv)
        _effective_spec_blend = base_spec_blend_mode if base_spec_blend_mode != "normal" else blend_mode
        M_contrib = M_pv * M_range * pattern_sm_eff * spec_mult
        R_contrib = R_pv * R_range * pattern_sm_eff * spec_mult
        M_arr = _apply_spec_blend_mode(M_arr, M_contrib, opacity, _effective_spec_blend)
        R_arr = _apply_spec_blend_mode(R_arr, R_contrib, opacity, _effective_spec_blend)
        CC_range = tex.get("CC_range", 0)
        if CC_pv is not None and CC_range != 0:
            final_CC = final_CC + CC_pv * CC_range * pattern_sm_eff * opacity * spec_mult
        if "R_extra" in tex:
            _r_extra = to_gpu(tex["R_extra"]) if _gpu_active else tex["R_extra"]
            R_arr = R_arr + _r_extra * pattern_sm_eff * opacity * spec_mult
        if "M_extra" in tex:
            _m_extra = to_gpu(tex["M_extra"]) if _gpu_active else tex["M_extra"]
            M_arr = M_arr + _m_extra * pattern_sm_eff * opacity * spec_mult
        pat_CC = tex.get("CC")
        if pat_CC is not None:
            if isinstance(pat_CC, np.ndarray):
                _pat_cc_g = to_gpu(pat_CC) if _gpu_active else pat_CC
                final_CC = final_CC * (1.0 - opacity) + _pat_cc_g * opacity
            else:
                final_CC = final_CC * (1.0 - opacity) + float(pat_CC) * opacity

    # GPU-accelerate final spec assembly — M_arr/R_arr/mask already on GPU when _gpu_active
    if _gpu_active:
        M_final = M_arr * mask + 5.0 * (1 - mask)
        R_final = R_arr * mask + 100.0 * (1 - mask)
        spec[:,:,0] = to_cpu(xp.clip(M_final, 0, 255).astype(xp.uint8))
        spec[:,:,1] = to_cpu(_ggx_safe_R(R_final, M_final, lib=xp).astype(xp.uint8))
        _is_cc_arr = hasattr(final_CC, 'shape')
        if _is_cc_arr:
            final_CC = to_gpu(final_CC)
            spec[:,:,2] = to_cpu(xp.clip(final_CC * mask, 0, 255).astype(xp.uint8))
        else:
            _mask_cpu_cc = to_cpu(mask)
            spec[:,:,2] = np.clip(final_CC * _mask_cpu_cc, 0, 255).astype(np.uint8)
        spec[:,:,3] = 255
    else:
        M_final = M_arr * mask + 5.0 * (1 - mask)
        R_final = R_arr * mask + 100.0 * (1 - mask)
        spec[:,:,0] = np.clip(M_final, 0, 255).astype(np.uint8)
        spec[:,:,1] = _ggx_safe_R(R_final, M_final).astype(np.uint8)
        spec[:,:,2] = np.clip(final_CC * mask, 0, 255).astype(np.uint8)
        spec[:,:,3] = 255

    # Transfer mask back to CPU for overlay functions
    if _gpu_active:
        mask = to_cpu(mask)

    if second_base and second_base_strength > 0.001:
        try:
            _sb_seed = seed + 999
            _sb_seed_off = abs(hash(second_base)) % 10000
            spec_secondary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            # Strip mono: prefix if the ID is actually a base (migrated finishes)
            if str(second_base).startswith("mono:"):
                _sb_stripped = second_base[5:]
                if monolithic_registry is not None and _sb_stripped in monolithic_registry:
                    _sb_spec_fn = monolithic_registry[_sb_stripped][0]
                    spec_secondary = _sb_spec_fn(shape, mask, _sb_seed + _sb_seed_off, sm)
                elif _sb_stripped in BASE_REGISTRY:
                    second_base = _sb_stripped  # fallback: treat as base
            if second_base in BASE_REGISTRY:
                _sb_def = BASE_REGISTRY[second_base]
                _sb_M = float(_sb_def["M"])
                _sb_R = float(_sb_def["R"])
                _sb_CC = int(_sb_def.get("CC", 16))
                if _sb_def.get("base_spec_fn"):
                    _sb_result = _sb_def["base_spec_fn"](shape, _sb_seed + _sb_seed_off, sm, _sb_M, _sb_R)
                    _sb_M_arr = _sb_result[0]
                    _sb_R_arr = _sb_result[1]
                    _sb_CC_arr = _sb_result[2] if len(_sb_result) > 2 else np.full(shape, float(_sb_CC))
                elif _sb_def.get("perlin"):
                    _sb_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], _sb_seed + _sb_seed_off)
                    _sb_M_arr = _sb_M + _sb_noise * _sb_def.get("noise_M", 0) * sm
                    _sb_R_arr = _sb_R + _sb_noise * _sb_def.get("noise_R", 0) * sm
                    _sb_CC_arr = np.full(shape, float(_sb_CC))
                else:
                    _sb_M_arr = np.full(shape, _sb_M)
                    _sb_R_arr = np.full(shape, _sb_R)
                    _sb_CC_arr = np.full(shape, float(_sb_CC))
                _sb_M_final = _sb_M_arr * mask + 5.0 * (1 - mask)
                _sb_R_final = _sb_R_arr * mask + 100.0 * (1 - mask)
                spec_secondary[:,:,0] = np.clip(_sb_M_final, 0, 255).astype(np.uint8)
                spec_secondary[:,:,1] = _ggx_safe_R(_sb_R_final, _sb_M_final).astype(np.uint8)
                spec_secondary[:,:,2] = np.clip(_sb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_secondary[:,:,3] = 255
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id = None if second_base_pattern == '__none__' else (second_base_pattern if second_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            pattern_mask = _get_pattern_mask(_pat_id, shape, mask, seed, sm,
                scale=second_base_pattern_scale, rotation=second_base_pattern_rotation,
                opacity=second_base_pattern_opacity, strength=second_base_pattern_strength,
                offset_x=second_base_pattern_offset_x, offset_y=second_base_pattern_offset_y) if _pat_id else None
            if pattern_mask is not None:
                if second_base_pattern_invert:
                    pattern_mask = 1.0 - pattern_mask
                if second_base_pattern_harden:
                    pattern_mask = np.clip((pattern_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            spec, _ = blend_dual_base_spec(
                spec, spec_secondary,
                strength=second_base_spec_strength,
                blend_mode=second_base_blend_mode,
                noise_scale=second_base_noise_scale,
                seed=seed,
                pattern_mask=pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=max(0.01, min(5.0, float(second_base_scale)))
            )
        except Exception:
            pass

    if third_base and third_base_strength > 0.001:
        try:
            _tb_seed = seed + 1999
            _tb_seed_off = abs(hash(third_base)) % 10000
            spec_tertiary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(third_base).startswith("mono:"):
                _tb_stripped = third_base[5:]
                if monolithic_registry is not None and _tb_stripped in monolithic_registry:
                    _tb_spec_fn = monolithic_registry[_tb_stripped][0]
                    spec_tertiary = _tb_spec_fn(shape, mask, _tb_seed + _tb_seed_off, sm)
                elif _tb_stripped in BASE_REGISTRY:
                    third_base = _tb_stripped
            if third_base in BASE_REGISTRY:
                _tb_def = BASE_REGISTRY[third_base]
                _tb_M = float(_tb_def["M"])
                _tb_R = float(_tb_def["R"])
                _tb_CC = int(_tb_def.get("CC", 16))
                if _tb_def.get("base_spec_fn"):
                    _tb_result = _tb_def["base_spec_fn"](shape, _tb_seed + _tb_seed_off, sm, _tb_M, _tb_R)
                    _tb_M_arr = _tb_result[0]
                    _tb_R_arr = _tb_result[1]
                    _tb_CC_arr = _tb_result[2] if len(_tb_result) > 2 else np.full(shape, float(_tb_CC))
                elif _tb_def.get("perlin"):
                    _tb_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], _tb_seed + _tb_seed_off)
                    _tb_M_arr = _tb_M + _tb_noise * _tb_def.get("noise_M", 0) * sm
                    _tb_R_arr = _tb_R + _tb_noise * _tb_def.get("noise_R", 0) * sm
                    _tb_CC_arr = np.full(shape, float(_tb_CC))
                else:
                    _tb_M_arr = np.full(shape, _tb_M)
                    _tb_R_arr = np.full(shape, _tb_R)
                    _tb_CC_arr = np.full(shape, float(_tb_CC))
                _tb_M_final = _tb_M_arr * mask + 5.0 * (1 - mask)
                _tb_R_final = _tb_R_arr * mask + 100.0 * (1 - mask)
                spec_tertiary[:,:,0] = np.clip(_tb_M_final, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,1] = _ggx_safe_R(_tb_R_final, _tb_M_final).astype(np.uint8)
                spec_tertiary[:,:,2] = np.clip(_tb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,3] = 255
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = None if third_base_pattern == '__none__' else (third_base_pattern if third_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            _tb_pattern_mask = _get_pattern_mask(_pat_id_tb, shape, mask, seed, sm,
                scale=third_base_pattern_scale, rotation=third_base_pattern_rotation,
                opacity=third_base_pattern_opacity, strength=third_base_pattern_strength,
                offset_x=third_base_pattern_offset_x, offset_y=third_base_pattern_offset_y) if _pat_id_tb else None
            if _tb_pattern_mask is not None:
                if third_base_pattern_invert:
                    _tb_pattern_mask = 1.0 - _tb_pattern_mask
                if third_base_pattern_harden:
                    _tb_pattern_mask = np.clip((_tb_pattern_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            spec, _ = blend_dual_base_spec(
                spec, spec_tertiary,
                strength=third_base_spec_strength,
                blend_mode=third_base_blend_mode,
                noise_scale=third_base_noise_scale,
                seed=seed + 8888,
                pattern_mask=_tb_pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=max(0.01, min(5.0, float(third_base_scale)))
            )
        except Exception:
            pass

    if fourth_base and fourth_base_strength > 0.001:
        try:
            _fb_seed = seed + 2999
            _fb_seed_off = abs(hash(fourth_base)) % 10000
            spec_fourth = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(fourth_base).startswith("mono:"):
                _fb_stripped = fourth_base[5:]
                if monolithic_registry is not None and _fb_stripped in monolithic_registry:
                    _fb_spec_fn = monolithic_registry[_fb_stripped][0]
                    spec_fourth = _fb_spec_fn(shape, mask, _fb_seed + _fb_seed_off, sm)
                elif _fb_stripped in BASE_REGISTRY:
                    fourth_base = _fb_stripped
            if fourth_base in BASE_REGISTRY:
                _fb_def = BASE_REGISTRY[fourth_base]
                _fb_M = float(_fb_def["M"])
                _fb_R = float(_fb_def["R"])
                _fb_CC = int(_fb_def.get("CC", 16))
                if _fb_def.get("base_spec_fn"):
                    _fb_result = _fb_def["base_spec_fn"](shape, _fb_seed + _fb_seed_off, sm, _fb_M, _fb_R)
                    _fb_M_arr, _fb_R_arr = _fb_result[0], _fb_result[1]
                    _fb_CC_arr = _fb_result[2] if len(_fb_result) > 2 else np.full(shape, float(_fb_CC))
                elif _fb_def.get("perlin"):
                    _fb_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], _fb_seed + _fb_seed_off)
                    _fb_M_arr = _fb_M + _fb_noise * _fb_def.get("noise_M", 0) * sm
                    _fb_R_arr = _fb_R + _fb_noise * _fb_def.get("noise_R", 0) * sm
                    _fb_CC_arr = np.full(shape, float(_fb_CC))
                else:
                    _fb_M_arr = np.full(shape, _fb_M)
                    _fb_R_arr = np.full(shape, _fb_R)
                    _fb_CC_arr = np.full(shape, float(_fb_CC))
                spec_fourth[:,:,0] = np.clip(_fb_M_arr * mask + 5.0 * (1 - mask), 0, 255).astype(np.uint8)
                spec_fourth[:,:,1] = np.clip(_fb_R_arr * mask + 100.0 * (1 - mask), 0, 255).astype(np.uint8)
                spec_fourth[:,:,2] = np.clip(_fb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_fourth[:,:,3] = 255
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = None if fourth_base_pattern == '__none__' else (fourth_base_pattern if fourth_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            _fb_pattern_mask = _get_pattern_mask(_pat_id_fb, shape, mask, seed, sm,
                scale=fourth_base_pattern_scale, rotation=fourth_base_pattern_rotation,
                opacity=fourth_base_pattern_opacity, strength=fourth_base_pattern_strength,
                offset_x=fourth_base_pattern_offset_x, offset_y=fourth_base_pattern_offset_y) if _pat_id_fb else None
            if _fb_pattern_mask is not None:
                if fourth_base_pattern_invert:
                    _fb_pattern_mask = 1.0 - _fb_pattern_mask
                if fourth_base_pattern_harden:
                    _fb_pattern_mask = np.clip((_fb_pattern_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            spec, _ = blend_dual_base_spec(
                spec, spec_fourth,
                strength=fourth_base_spec_strength,
                blend_mode=fourth_base_blend_mode,
                noise_scale=fourth_base_noise_scale,
                seed=seed + 7777,
                pattern_mask=_fb_pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=max(0.01, min(5.0, float(fourth_base_scale)))
            )
        except Exception:
            pass

    if fifth_base and fifth_base_strength > 0.001:
        try:
            _fif_seed = seed + 3999
            _fif_seed_off = abs(hash(fifth_base)) % 10000
            spec_fifth = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(fifth_base).startswith("mono:"):
                _fif_stripped = fifth_base[5:]
                if monolithic_registry is not None and _fif_stripped in monolithic_registry:
                    _fif_spec_fn = monolithic_registry[_fif_stripped][0]
                    spec_fifth = _fif_spec_fn(shape, mask, _fif_seed + _fif_seed_off, sm)
                elif _fif_stripped in BASE_REGISTRY:
                    fifth_base = _fif_stripped
            if fifth_base in BASE_REGISTRY:
                _fif_def = BASE_REGISTRY[fifth_base]
                _fif_M = float(_fif_def["M"])
                _fif_R = float(_fif_def["R"])
                _fif_CC = int(_fif_def.get("CC", 16))
                if _fif_def.get("base_spec_fn"):
                    _fif_result = _fif_def["base_spec_fn"](shape, _fif_seed + _fif_seed_off, sm, _fif_M, _fif_R)
                    _fif_M_arr, _fif_R_arr = _fif_result[0], _fif_result[1]
                    _fif_CC_arr = _fif_result[2] if len(_fif_result) > 2 else np.full(shape, float(_fif_CC))
                elif _fif_def.get("perlin"):
                    _fif_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], _fif_seed + _fif_seed_off)
                    _fif_M_arr = _fif_M + _fif_noise * _fif_def.get("noise_M", 0) * sm
                    _fif_R_arr = _fif_R + _fif_noise * _fif_def.get("noise_R", 0) * sm
                    _fif_CC_arr = np.full(shape, float(_fif_CC))
                else:
                    _fif_M_arr = np.full(shape, _fif_M)
                    _fif_R_arr = np.full(shape, _fif_R)
                    _fif_CC_arr = np.full(shape, float(_fif_CC))
                spec_fifth[:,:,0] = np.clip(_fif_M_arr * mask + 5.0 * (1 - mask), 0, 255).astype(np.uint8)
                spec_fifth[:,:,1] = np.clip(_fif_R_arr * mask + 100.0 * (1 - mask), 0, 255).astype(np.uint8)
                spec_fifth[:,:,2] = np.clip(_fif_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_fifth[:,:,3] = 255
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = None if fifth_base_pattern == '__none__' else (fifth_base_pattern if fifth_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            _fif_pattern_mask = _get_pattern_mask(_pat_id_fif, shape, mask, seed, sm,
                scale=fifth_base_pattern_scale, rotation=fifth_base_pattern_rotation,
                opacity=fifth_base_pattern_opacity, strength=fifth_base_pattern_strength,
                offset_x=fifth_base_pattern_offset_x, offset_y=fifth_base_pattern_offset_y) if _pat_id_fif else None
            if _fif_pattern_mask is not None:
                if fifth_base_pattern_invert:
                    _fif_pattern_mask = 1.0 - _fif_pattern_mask
                if fifth_base_pattern_harden:
                    _fif_pattern_mask = np.clip((_fif_pattern_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            spec, _ = blend_dual_base_spec(
                spec, spec_fifth,
                strength=fifth_base_spec_strength,
                blend_mode=fifth_base_blend_mode,
                noise_scale=fifth_base_noise_scale,
                seed=seed + 6666,
                pattern_mask=_fif_pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=max(0.01, min(5.0, float(fifth_base_scale)))
            )
        except Exception:
            pass

    # --- Overlay Spec Pattern Stack (applied after all base blending) ---
    _overlay_spec_patterns_stk = kwargs.get("overlay_spec_pattern_stack", [])
    if _overlay_spec_patterns_stk:
        try:
            from engine.spec_patterns import PATTERN_CATALOG
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _overlay_spec_patterns_stk:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = PATTERN_CATALOG.get(_ovsp_name)
                if _ovsp_fn is None:
                    continue
                _ovsp_opacity = float(_ovsp.get("opacity", 0.5))
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 40.0))
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = seed + 7000 + hash(_ovsp_name) % 10000
                if _ovsp_scale < 1.0 and abs(_ovsp_scale - 1.0) > 0.01:
                    _ovsp_arr = _scale_down_spec_pattern(_ovsp_fn, _ovsp_scale, shape, _ovsp_seed, sm, _ovsp_params)
                else:
                    _ovsp_arr = _ovsp_fn(shape, _ovsp_seed, sm, **_ovsp_params)
                    if abs(_ovsp_scale - 1.0) > 0.01:
                        _oh, _ow = shape[0], shape[1]
                        _ovsp_arr = _crop_center_array(_ovsp_arr, _ovsp_scale, _oh, _ow)
                if abs(_ovsp_rotation) > 0.5:
                    _ovsp_arr = _rotate_single_array(_ovsp_arr, _ovsp_rotation, shape)
                if abs(_ovsp_offset_x - 0.5) > 0.01 or abs(_ovsp_offset_y - 0.5) > 0.01:
                    _apply_pattern_offset(_ovsp_arr, shape, _ovsp_offset_x, _ovsp_offset_y)
                if _ovsp_box_size < 100:
                    _ovsp_arr = _apply_spec_pattern_box_size(_ovsp_arr, shape, _ovsp_box_size, _ovsp_offset_x, _ovsp_offset_y)
                _ovsp_delta = (_ovsp_arr - 0.5) * 2.0
                _ovsp_contrib = _ovsp_delta * _ovsp_range
                if "M" in _ovsp_channels:
                    _ov_M = _apply_spec_blend_mode(_ov_M, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_M = np.clip(_ov_M, 0, 255).astype(np.float32)
                if "R" in _ovsp_channels:
                    _ov_R = _apply_spec_blend_mode(_ov_R, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_R = np.clip(_ov_R, 0, 255).astype(np.float32)
                if "C" in _ovsp_channels:
                    _ov_CC = _apply_spec_blend_mode(_ov_CC, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_CC = np.clip(_ov_CC, 16, 255).astype(np.float32)
            spec[:,:,0] = np.clip(_ov_M * mask + spec[:,:,0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * mask + spec[:,:,1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * mask + spec[:,:,2].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
        except Exception:
            pass

    def _apply_named_overlay_spec_stack_stk(stack_key, seed_offset):
        _stack = kwargs.get(stack_key, [])
        if not _stack:
            return
        try:
            from engine.spec_patterns import PATTERN_CATALOG
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _stack:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = PATTERN_CATALOG.get(_ovsp_name)
                if _ovsp_fn is None:
                    continue
                _ovsp_opacity = float(_ovsp.get("opacity", 0.5))
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 40.0))
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = seed + seed_offset + hash(_ovsp_name) % 10000
                if _ovsp_scale < 1.0 and abs(_ovsp_scale - 1.0) > 0.01:
                    _ovsp_arr = _scale_down_spec_pattern(_ovsp_fn, _ovsp_scale, shape, _ovsp_seed, sm, _ovsp_params)
                else:
                    _ovsp_arr = _ovsp_fn(shape, _ovsp_seed, sm, **_ovsp_params)
                    if abs(_ovsp_scale - 1.0) > 0.01:
                        _oh, _ow = shape[0], shape[1]
                        _ovsp_arr = _crop_center_array(_ovsp_arr, _ovsp_scale, _oh, _ow)
                if abs(_ovsp_rotation) > 0.5:
                    _ovsp_arr = _rotate_single_array(_ovsp_arr, _ovsp_rotation, shape)
                if abs(_ovsp_offset_x - 0.5) > 0.01 or abs(_ovsp_offset_y - 0.5) > 0.01:
                    _apply_pattern_offset(_ovsp_arr, shape, _ovsp_offset_x, _ovsp_offset_y)
                if _ovsp_box_size < 100:
                    _ovsp_arr = _apply_spec_pattern_box_size(_ovsp_arr, shape, _ovsp_box_size, _ovsp_offset_x, _ovsp_offset_y)
                _ovsp_delta = (_ovsp_arr - 0.5) * 2.0
                _ovsp_contrib = _ovsp_delta * _ovsp_range
                if "M" in _ovsp_channels:
                    _ov_M = _apply_spec_blend_mode(_ov_M, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_M = np.clip(_ov_M, 0, 255).astype(np.float32)
                if "R" in _ovsp_channels:
                    _ov_R = _apply_spec_blend_mode(_ov_R, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_R = np.clip(_ov_R, 0, 255).astype(np.float32)
                if "C" in _ovsp_channels:
                    _ov_CC = _apply_spec_blend_mode(_ov_CC, _ovsp_contrib, _ovsp_opacity, _ovsp_blend)
                    _ov_CC = np.clip(_ov_CC, 16, 255).astype(np.float32)
            spec[:,:,0] = np.clip(_ov_M * mask + spec[:,:,0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * mask + spec[:,:,1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * mask + spec[:,:,2].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
        except Exception:
            pass

    _apply_named_overlay_spec_stack_stk("third_overlay_spec_pattern_stack", 8000)
    _apply_named_overlay_spec_stack_stk("fourth_overlay_spec_pattern_stack", 9000)
    _apply_named_overlay_spec_stack_stk("fifth_overlay_spec_pattern_stack", 10000)

    return spec


def compose_paint_mod(base_id, pattern_id, paint, shape, mask, seed, pm, bb, scale=1.0, rotation=0, blend_base=None, blend_dir="horizontal", blend_amount=0.5,
                      base_color_mode="source", base_color=None, base_color_source=None, base_color_strength=1.0,
                      second_base=None, second_base_color=None, second_base_color_source=None, second_base_strength=0.0, second_base_spec_strength=1.0,
                      second_base_blend_mode="noise", second_base_noise_scale=24,
                      second_base_scale=1.0, second_base_pattern=None,
                      second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                      second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                      second_base_pattern_invert=False, second_base_pattern_harden=False,
                      second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                      third_base=None, third_base_color=None, third_base_color_source=None, third_base_strength=0.0, third_base_spec_strength=1.0,
                      third_base_blend_mode="noise", third_base_noise_scale=24,
                      third_base_scale=1.0, third_base_pattern=None,
                      third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                      third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                      third_base_pattern_invert=False, third_base_pattern_harden=False,
                      third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                      fourth_base=None, fourth_base_color=None, fourth_base_color_source=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0,
                      fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                      fourth_base_scale=1.0, fourth_base_pattern=None,
                      fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                      fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                      fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                      fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                      fifth_base=None, fifth_base_color=None, fifth_base_color_source=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0,
                      fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                      fifth_base_scale=1.0, fifth_base_pattern=None,
                      fifth_base_pattern_scale=1.0, fifth_base_pattern_rotation=0.0,
                      fifth_base_pattern_opacity=1.0, fifth_base_pattern_strength=1.0,
                      fifth_base_pattern_invert=False, fifth_base_pattern_harden=False,
                      fifth_base_pattern_offset_x=0.5, fifth_base_pattern_offset_y=0.5,
                      second_base_hue_shift=0, second_base_saturation=0, second_base_brightness=0,
                      second_base_pattern_hue_shift=0, second_base_pattern_saturation=0, second_base_pattern_brightness=0,
                      third_base_hue_shift=0, third_base_saturation=0, third_base_brightness=0,
                      fourth_base_hue_shift=0, fourth_base_saturation=0, fourth_base_brightness=0,
                      fifth_base_hue_shift=0, fifth_base_saturation=0, fifth_base_brightness=0,
                      monolithic_registry=None, base_strength=1.0, base_spec_strength=1.0, spec_mult=1.0,
                      pattern_intensity=1.0,
                      base_hue_offset=0, base_saturation_adjust=0, base_brightness_adjust=0,
                      base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0,
                      base_flip_h=False, base_flip_v=False,
                      pattern_offset_x=0.5, pattern_offset_y=0.5,
                      pattern_flip_h=False, pattern_flip_v=False):
    """Apply base paint modifier then pattern paint modifier WITH spatial texture blending.
    pattern_intensity 0-1: 5%% = hint, 100%% = full (linear; avoids flip below 50%%).
    When second_base_color_source (etc.) is 'mono:xyz', the overlay color comes from that special's paint_fn (gradients, color shifts, etc.).
    PURE CPU: always receives and returns numpy arrays. The caller (build_multi_zone) handles GPU↔CPU conversion."""
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    # Ensure CPU numpy — CuPy inputs converted here (caller should prefer to_cpu before calling)
    if hasattr(paint, 'get'):
        paint = paint.get()
    paint = np.asarray(paint)
    if hasattr(mask, 'get'):
        mask = mask.get()
    mask = np.asarray(mask)
    hard_mask = np.where(mask > 0.1, mask, np.float32(0.0)).astype(np.float32)
    base = BASE_REGISTRY[base_id]
    base_paint_fn = base.get("paint_fn", paint_none)
    has_pattern = (pattern_id and pattern_id != "none" and pattern_id in PATTERN_REGISTRY)
    has_blend = (blend_base and blend_base in BASE_REGISTRY and blend_base != base_id)
    if blend_base:
        print(f"    [BLEND DEBUG] blend_base='{blend_base}', in_registry={blend_base in BASE_REGISTRY}, same_as_primary={blend_base == base_id}, has_blend={has_blend}")
    if has_blend:
        base2 = BASE_REGISTRY[blend_base]
        base2_paint_fn = base2.get("paint_fn", paint_none)

    _BASE_PAINT_BOOST = 1.0 * max(0.0, min(2.0, float(base_strength)))
    if base_paint_fn is not paint_none:
        # External paint_fn expects CPU (numpy) arrays — paint is already CPU here
        try:
            if has_pattern:
                _paint_result = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST * 0.7, bb * _BASE_PAINT_BOOST * 0.7)
            else:
                _paint_result = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST, bb * _BASE_PAINT_BOOST)
            paint = np.asarray(_paint_result) if not isinstance(_paint_result, np.ndarray) else _paint_result
        except Exception as _bp_err:
            print(f"[compose] WARNING: base_paint_fn failed for base '{base_id}': {_bp_err}")

    # Record what the base paint_fn produced so we can blend it against the
    # base color override using base_strength as a mix weight.
    # Only copy when the lerp will actually be used (avoids ~32MB memcpy on most renders).
    _needs_lerp = (_BASE_PAINT_BOOST < 1.0 - 0.001) and (base_paint_fn is not paint_none)
    if _needs_lerp:
        _paint_after_base = paint.copy()

    paint = _apply_base_color_override(
        paint, shape, hard_mask, seed,
        base_color_mode, base_color, base_color_source, base_color_strength,
        monolithic_registry
    )

    # HSB adjustments (hue shift, saturation, brightness)
    _hue_off = base_hue_offset
    _sat_adj = base_saturation_adjust
    _bri_adj = base_brightness_adjust
    if _hue_off or _sat_adj or _bri_adj:
        paint = _apply_hsb_adjustments(paint, hard_mask, _hue_off, _sat_adj, _bri_adj)

    # base_strength controls how much of the base material effect vs. the base
    # color override shows.  At strength=1.0 the material effect is fully present;
    # at 0.0 the material effect is suppressed and only the base color remains.
    # We achieve this by lerping the paint_fn output back toward the color-only
    # result according to (1 - base_strength).
    if _needs_lerp:
        _str_w = np.clip(_BASE_PAINT_BOOST, 0.0, 1.0)
        _mask3 = hard_mask[:, :, np.newaxis]
        # paint currently = color_override result; _paint_after_base = full material
        paint[:, :, :3] = (
            _paint_after_base[:, :, :3] * _str_w
            + paint[:, :, :3] * (1.0 - _str_w)
        ) * _mask3 + paint[:, :, :3] * (1.0 - _mask3)

    # Base transforms (offset, rotation, flip) applied to paint channels — all CPU
    _bo_x = max(0.0, min(1.0, float(base_offset_x if base_offset_x is not None else 0.5)))
    _bo_y = max(0.0, min(1.0, float(base_offset_y if base_offset_y is not None else 0.5)))
    _bro = float(base_rotation if base_rotation is not None else 0) % 360.0
    if abs(_bo_x - 0.5) > 0.001 or abs(_bo_y - 0.5) > 0.001:
        for ch in range(min(3, paint.shape[2])):
            _apply_pattern_offset(paint[:, :, ch], shape, _bo_x, _bo_y)
    if abs(_bro) > 0.5:
        for ch in range(min(3, paint.shape[2])):
            paint[:, :, ch] = _rotate_single_array(paint[:, :, ch], _bro, shape)
    if base_flip_h:
        paint = np.fliplr(paint).copy()
    if base_flip_v:
        paint = np.flipud(paint).copy()

    if has_blend and base2_paint_fn is not paint_none:
        print(f"    [BLEND PAINT v6.1] base={base_id} + blend={blend_base}, dir={blend_dir}, amount={blend_amount:.2f}")
        _BLEND_PM, _BLEND_BB = 1.0, 1.0
        # External paint_fn expects CPU (numpy) arrays — paint is already CPU here
        _paint_blend_result = base2_paint_fn(paint.copy(), shape, hard_mask, seed + 5000, _BLEND_PM, _BLEND_BB)
        paint_blend = np.asarray(_paint_blend_result) if not isinstance(_paint_blend_result, np.ndarray) else _paint_blend_result
        h, w = shape
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
        if blend_dir == "vertical":
            grad = np.zeros((h, w), dtype=np.float32)
            zone_grad = np.linspace(0, 1, bbox_h, dtype=np.float32)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
            grad[r_min:r_min + bbox_h, :] = zone_grad
            grad[:r_min, :] = 0.0
            grad[r_min + bbox_h:, :] = 1.0
        elif blend_dir == "radial":
            cy, cx = r_min + bbox_h / 2.0, c_min + bbox_w / 2.0
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            max_radius = np.sqrt((bbox_h / 2.0)**2 + (bbox_w / 2.0)**2) + 1e-8
            grad = np.clip(np.sqrt((yy - cy)**2 + (xx - cx)**2) / max_radius, 0, 1)
        elif blend_dir == "diagonal":
            grad = np.zeros((h, w), dtype=np.float32)
            v_grad = np.linspace(0, 1, bbox_h, dtype=np.float32)[:, np.newaxis]
            h_grad = np.linspace(0, 1, bbox_w, dtype=np.float32)[np.newaxis, :]
            grad[r_min:r_min + bbox_h, c_min:c_min + bbox_w] = v_grad * 0.5 + h_grad * 0.5
            grad[:r_min, :] = 0.0
            grad[r_min + bbox_h:, :] = 1.0
        else:
            grad = np.zeros((h, w), dtype=np.float32)
            zone_grad = np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, bbox_w, dtype=np.float32)[np.newaxis, :]
            grad[:, c_min:c_min + bbox_w] = zone_grad
            grad[:, :c_min] = 0.0
            grad[:, c_min + bbox_w:] = 1.0
        ba = max(0.1, min(3.0, blend_amount * 2.0 + 0.1))
        grad = np.power(grad, ba) * hard_mask
        grad_3d = grad[:, :, np.newaxis]
        paint = paint * (1.0 - grad_3d) + paint_blend * grad_3d

    # pattern_intensity 0–1: perceptual curve so low values still show pattern
    # sqrt curve: 5%→22%, 25%→50%, 50%→71%, 100%→100% (prevents disappearing below 50%)
    _pi_raw = max(0.0, min(1.0, float(pattern_intensity)))
    _pi = _pi_raw ** 0.5 if _pi_raw > 0 else 0.0
    if has_pattern:
        pattern = PATTERN_REGISTRY[pattern_id]
        pat_paint_fn = pattern.get("paint_fn", paint_none)
        tex_fn = pattern.get("texture_fn")
        image_path = pattern.get("image_path")
        if image_path:
            from engine.render import _load_image_pattern, _load_color_image_pattern
            # Get the full color version
            rgba = _load_color_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if rgba is not None:
                r, g, b, alpha = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3]
                # Scale alpha by pattern_intensity so 5% shows a hint, 100% full — all CPU
                alpha_3d = (alpha[:, :, np.newaxis] * _pi) * hard_mask[:, :, np.newaxis]
                rgb_3d = rgba[:, :, :3]
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - alpha_3d) + rgb_3d * alpha_3d
            else:
                pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
                if pv is not None:
                    pv_min, pv_max = float(pv.min()), float(pv.max())
                    if pv_max - pv_min > 1e-8:
                        pv = (pv - pv_min) / (pv_max - pv_min)
                    else:
                        pv = np.ones_like(pv) * 0.5
                    pv_3d = pv[:, :, np.newaxis]
                    # Mask the pattern so it only modifies paint INSIDE the zone
                    mask_3d = hard_mask[:, :, np.newaxis]
                    pv_masked = pv_3d * mask_3d
                    fac = 0.35 * pm * spec_mult * _pi
                    paint = np.clip(paint * (1.0 - pv_masked * fac) - pv_masked * bb * 0.1 * spec_mult, 0, 1).astype(np.float32)
        elif pat_paint_fn is not paint_none:
            # External pat_paint_fn expects CPU arrays — paint is already CPU here
            paint_before_pattern = paint.copy()
            _PAT_PAINT_BOOST = 1.8
            try:
                if base_paint_fn is not paint_none:
                    _pat_result = pat_paint_fn(paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST * 0.7 * spec_mult, bb * _PAT_PAINT_BOOST * 0.7 * spec_mult)
                else:
                    _pat_result = pat_paint_fn(paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST * spec_mult, bb * _PAT_PAINT_BOOST * spec_mult)
                paint = np.asarray(_pat_result) if not isinstance(_pat_result, np.ndarray) else _pat_result
            except Exception as _pp_err:
                print(f"[compose] WARNING: pat_paint_fn failed for pattern '{pattern_id}': {_pp_err}")
                paint = paint_before_pattern
            if tex_fn is not None:
                try:
                    # tex_fn expects CPU mask — mask is already CPU here
                    tex = tex_fn(shape, mask, seed, 1.0)
                    pv = tex["pattern_val"] if isinstance(tex, dict) else tex
                    if scale != 1.0 and scale > 0:
                        if isinstance(tex, dict):
                            pv, tex = _scale_pattern_output(pv, tex, scale, shape)
                        else:
                            if scale < 1.0:
                                pv = _tile_fractional(pv, 1.0 / scale, shape[0], shape[1])
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
                    # Scale blend by pattern_intensity so 5% = hint, 100% = full (no flip below 50%)
                    pv_3d = pv[:, :, np.newaxis] * _pi
                    paint = paint_before_pattern * (1.0 - pv_3d) + paint * pv_3d
                except Exception:
                    pass

    if (second_base or second_base_color_source) and second_base_strength > 0.001:
        try:
            # When overlay base is a special, use it as color source if none set (so user doesn't pick twice)
            _sb_color_src = second_base_color_source if (second_base_color_source and str(second_base_color_source).startswith("mono:")) else None
            if not _sb_color_src and second_base and str(second_base).startswith("mono:"):
                _sb_color_src = second_base
            print(f"    [PAINT OVERLAY 2nd] second_base={second_base}, color_src={_sb_color_src}, strength={second_base_strength}, blend_mode={second_base_blend_mode}")
            # Overlay operations are CPU-only — paint is already CPU here
            _paint_overlay_cpu = paint.copy()
            # Use actual canvas dimensions from paint array (preview renders may have a smaller
            # canvas than the shape parameter which can still carry the original file resolution).
            _sb_shape = (paint.shape[0], paint.shape[1])
            _sb_mask3d = hard_mask[:, :, np.newaxis]
            if (_sb_color_src and _sb_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _sb_color_src[5:] in monolithic_registry) or
                    _sb_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _sb_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                print(f"    [PAINT OVERLAY 2nd] Using mono paint_fn for '{_mono_id}', fn={_mono_paint_fn}")
                # Mono paint_fn MODIFIES existing colors (chameleon shifts hues, etc.)
                # Pass the actual paint so the effect has real colors to transform.
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _sb_shape, hard_mask, seed + 7777, 1.0, 0.0)
                if _color_paint is None:
                    print(f"    [PAINT OVERLAY 2nd] WARNING: mono paint_fn returned None!")
                    _color_paint = _paint_overlay_cpu.copy()
                else:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _cp_shape = _color_paint.shape if hasattr(_color_paint, 'shape') else 'N/A'
                    _cp_dtype = _color_paint.dtype if hasattr(_color_paint, 'dtype') else 'N/A'
                    _cp_min = float(_color_paint[:,:,:3].min()) if hasattr(_color_paint, 'min') else 'N/A'
                    _cp_max = float(_color_paint[:,:,:3].max()) if hasattr(_color_paint, 'max') else 'N/A'
                    print(f"    [PAINT OVERLAY 2nd] mono paint result: shape={_cp_shape}, dtype={_cp_dtype}, range=[{_cp_min:.3f}, {_cp_max:.3f}]")
                _paint_overlay_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _sb_color_src:
                # User explicitly chose "From special", but that special isn't available in the active registry.
                # Keep overlay driven by base overlay paint_fn and do not fall back to solid color tint.
                print(f"    [PAINT OVERLAY 2nd] WARNING: special source '{_sb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _sb_color = second_base_color if second_base_color is not None else [1.0, 1.0, 1.0]
                _sb_r = float(_sb_color[0]) if len(_sb_color) > 0 else 1.0
                _sb_g = float(_sb_color[1]) if len(_sb_color) > 1 else 1.0
                _sb_b = float(_sb_color[2]) if len(_sb_color) > 2 else 1.0
                _sb_rgb = np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                print(f"    [PAINT OVERLAY 2nd] Using solid color: ({_sb_r:.3f}, {_sb_g:.3f}, {_sb_b:.3f})")
                _paint_overlay_cpu[:, :, :3] = _paint_overlay_cpu[:, :, :3] * (1.0 - _sb_mask3d) + _sb_rgb * _sb_mask3d
            if second_base and second_base in BASE_REGISTRY:
                _sb_def2 = BASE_REGISTRY[second_base]
                _sb_pfn = _sb_def2.get("paint_fn", paint_none)
                # When "From Special" is active, skip the base paint_fn — the special's
                # colors are the user's explicit choice.  The base overlay contributes
                # its SPEC (metallic/roughness/CC) which is the PBR-correct approach;
                # its paint_fn would wash out the special's colors (e.g. Chrome pushes
                # toward silver, destroying a Bruise purple-to-black gradient).
                if _sb_pfn is not paint_none and not _sb_color_src:
                    # External paint_fn expects CPU arrays — _paint_overlay_cpu is already CPU
                    _paint_overlay_cpu = _sb_pfn(_paint_overlay_cpu, _sb_shape, hard_mask, seed + 7777, 1.0, 0.0)
                    _paint_overlay_cpu = np.asarray(_paint_overlay_cpu) if not isinstance(_paint_overlay_cpu, np.ndarray) else _paint_overlay_cpu
                # When source is 'overlay', we already used the base's color; don't multiply again.
                if second_base_color is not None and not _sb_color_src and str(second_base_color_source or '').strip().lower() != 'overlay':
                    _sb_r = float(second_base_color[0]) if len(second_base_color) > 0 else 1.0
                    _sb_g = float(second_base_color[1]) if len(second_base_color) > 1 else 1.0
                    _sb_b = float(second_base_color[2]) if len(second_base_color) > 2 else 1.0
                    _paint_overlay_cpu[:, :, :3] *= np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_sb = None if second_base_pattern == '__none__' else (second_base_pattern if (second_base_pattern and second_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None))
            _sb_pat_mask = _get_pattern_mask(_pat_id_sb, _sb_shape, hard_mask, seed, 1.0,
                scale=second_base_pattern_scale, rotation=second_base_pattern_rotation,
                opacity=second_base_pattern_opacity, strength=second_base_pattern_strength,
                offset_x=second_base_pattern_offset_x, offset_y=second_base_pattern_offset_y) if _pat_id_sb else None
            if _sb_pat_mask is not None:
                if second_base_pattern_invert:
                    _sb_pat_mask = 1.0 - _sb_pat_mask
                if second_base_pattern_harden:
                    _sb_pat_mask = np.clip((_sb_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_sb = get_base_overlay_alpha(
                _sb_shape, second_base_strength, second_base_blend_mode,
                noise_scale=int(second_base_noise_scale), seed=seed,
                pattern_mask=_sb_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(second_base_scale)))
            )
            _alpha_sb3 = _alpha_sb[:, :, np.newaxis]
            if abs(second_base_hue_shift) > 0.5 or abs(second_base_saturation) > 0.5 or abs(second_base_brightness) > 0.5:
                print(f"    [OVERLAY HSB] 2nd base: hue={second_base_hue_shift}, sat={second_base_saturation}, brt={second_base_brightness}")
                _paint_overlay_cpu = _apply_hsb_adjustments(_paint_overlay_cpu, hard_mask, second_base_hue_shift, second_base_saturation, second_base_brightness)
                _paint_overlay_cpu = np.asarray(_paint_overlay_cpu)
            if abs(second_base_pattern_hue_shift) > 0.5 or abs(second_base_pattern_saturation) > 0.5 or abs(second_base_pattern_brightness) > 0.5:
                _paint_overlay_cpu = _apply_hsb_adjustments(_paint_overlay_cpu, hard_mask, second_base_pattern_hue_shift, second_base_pattern_saturation, second_base_pattern_brightness)
                _paint_overlay_cpu = np.asarray(_paint_overlay_cpu)
            # Blend back — all CPU
            if _sb_bm_norm == "pattern_screen":
                _screened = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb3) + _screened * _alpha_sb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb3) + _paint_overlay_cpu[:, :, :3] * _alpha_sb3
            print(f"    [PAINT OVERLAY 2nd] blend_mode={_sb_bm_norm}, applied successfully")
        except Exception as _e:
            import traceback
            print(f"    [PAINT OVERLAY 2nd] ERROR: {_e}")
            traceback.print_exc()

    if (third_base or third_base_color_source) and third_base_strength > 0.001:
        print(f"    [PAINT OVERLAY 3rd] tb={third_base}, color_src={third_base_color_source}, str={third_base_strength}, blend={third_base_blend_mode}")
        try:
            _tb_color_src = third_base_color_source if (third_base_color_source and str(third_base_color_source).startswith("mono:")) else None
            if not _tb_color_src and third_base and str(third_base).startswith("mono:"):
                _tb_color_src = third_base
            _paint_overlay_tb_cpu = paint.copy()
            _tb_shape = (paint.shape[0], paint.shape[1])
            _tb_mask3d = hard_mask[:, :, np.newaxis]
            if (_tb_color_src and _tb_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _tb_color_src[5:] in monolithic_registry) or
                    _tb_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _tb_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _tb_shape, hard_mask, seed + 9999, 1.0, 0.0)
                if _color_paint is not None:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _paint_overlay_tb_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _tb_color_src:
                print(f"    [PAINT OVERLAY 3rd] WARNING: special source '{_tb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _tb_color = third_base_color if third_base_color is not None else [1.0, 1.0, 1.0]
                _tb_r = float(_tb_color[0]) if len(_tb_color) > 0 else 1.0
                _tb_g = float(_tb_color[1]) if len(_tb_color) > 1 else 1.0
                _tb_b = float(_tb_color[2]) if len(_tb_color) > 2 else 1.0
                _tb_rgb = np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
                _paint_overlay_tb_cpu[:, :, :3] = _paint_overlay_tb_cpu[:, :, :3] * (1.0 - _tb_mask3d) + _tb_rgb * _tb_mask3d
            if third_base and third_base in BASE_REGISTRY:
                _tb_def2 = BASE_REGISTRY[third_base]
                _tb_pfn = _tb_def2.get("paint_fn", paint_none)
                if _tb_pfn is not paint_none and not _tb_color_src:
                    _paint_overlay_tb_cpu = _tb_pfn(_paint_overlay_tb_cpu, _tb_shape, hard_mask, seed + 9999, 1.0, 0.0)
                    _paint_overlay_tb_cpu = np.asarray(_paint_overlay_tb_cpu) if not isinstance(_paint_overlay_tb_cpu, np.ndarray) else _paint_overlay_tb_cpu
                if third_base_color is not None and not _tb_color_src and str(third_base_color_source or '').strip().lower() != 'overlay':
                    _tb_r = float(third_base_color[0]) if len(third_base_color) > 0 else 1.0
                    _tb_g = float(third_base_color[1]) if len(third_base_color) > 1 else 1.0
                    _tb_b = float(third_base_color[2]) if len(third_base_color) > 2 else 1.0
                    _paint_overlay_tb_cpu[:, :, :3] *= np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = None if third_base_pattern == '__none__' else (third_base_pattern if (third_base_pattern and third_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None))
            _tb_pat_mask = _get_pattern_mask(_pat_id_tb, _tb_shape, hard_mask, seed + 5555, 1.0,
                scale=third_base_pattern_scale, rotation=third_base_pattern_rotation,
                opacity=third_base_pattern_opacity, strength=third_base_pattern_strength,
                offset_x=third_base_pattern_offset_x, offset_y=third_base_pattern_offset_y) if _pat_id_tb else None
            if _tb_pat_mask is not None:
                if third_base_pattern_invert:
                    _tb_pat_mask = 1.0 - _tb_pat_mask
                if third_base_pattern_harden:
                    _tb_pat_mask = np.clip((_tb_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_tb = get_base_overlay_alpha(
                _tb_shape, third_base_strength, third_base_blend_mode,
                noise_scale=int(third_base_noise_scale), seed=seed + 8888,
                pattern_mask=_tb_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(third_base_scale)))
            )
            _alpha_tb3 = _alpha_tb[:, :, np.newaxis]
            if abs(third_base_hue_shift) > 0.5 or abs(third_base_saturation) > 0.5 or abs(third_base_brightness) > 0.5:
                _paint_overlay_tb_cpu = _apply_hsb_adjustments(_paint_overlay_tb_cpu, hard_mask, third_base_hue_shift, third_base_saturation, third_base_brightness)
                _paint_overlay_tb_cpu = np.asarray(_paint_overlay_tb_cpu)
            if _tb_bm_norm == "pattern_screen":
                _screened_tb = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_tb_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb3) + _screened_tb * _alpha_tb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb3) + _paint_overlay_tb_cpu[:, :, :3] * _alpha_tb3
        except Exception as _e:
            import traceback
            print(f"    [PAINT OVERLAY 3rd] ERROR: {_e}")
            traceback.print_exc()

    if (fourth_base or fourth_base_color_source) and fourth_base_strength > 0.001:
        try:
            _fb_color_src = fourth_base_color_source if (fourth_base_color_source and str(fourth_base_color_source).startswith("mono:")) else None
            if not _fb_color_src and fourth_base and str(fourth_base).startswith("mono:"):
                _fb_color_src = fourth_base
            _paint_overlay_fb_cpu = paint.copy()
            _fb_shape = (paint.shape[0], paint.shape[1])
            _fb_mask3d = hard_mask[:, :, np.newaxis]
            if (_fb_color_src and _fb_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _fb_color_src[5:] in monolithic_registry) or
                    _fb_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _fb_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _fb_shape, hard_mask, seed + 11111, 1.0, 0.0)
                if _color_paint is not None:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _paint_overlay_fb_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _fb_color_src:
                print(f"    [PAINT OVERLAY 4th] WARNING: special source '{_fb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fb_color = fourth_base_color if fourth_base_color is not None else [1.0, 1.0, 1.0]
                _fb_r = float(_fb_color[0]) if len(_fb_color) > 0 else 1.0
                _fb_g = float(_fb_color[1]) if len(_fb_color) > 1 else 1.0
                _fb_b = float(_fb_color[2]) if len(_fb_color) > 2 else 1.0
                _fb_rgb = np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
                _paint_overlay_fb_cpu[:, :, :3] = _paint_overlay_fb_cpu[:, :, :3] * (1.0 - _fb_mask3d) + _fb_rgb * _fb_mask3d
            if fourth_base and fourth_base in BASE_REGISTRY:
                _fb_def2 = BASE_REGISTRY[fourth_base]
                _fb_pfn = _fb_def2.get("paint_fn", paint_none)
                if _fb_pfn is not paint_none and not _fb_color_src:
                    _paint_overlay_fb_cpu = _fb_pfn(_paint_overlay_fb_cpu, _fb_shape, hard_mask, seed + 11111, 1.0, 0.0)
                    _paint_overlay_fb_cpu = np.asarray(_paint_overlay_fb_cpu) if not isinstance(_paint_overlay_fb_cpu, np.ndarray) else _paint_overlay_fb_cpu
                if fourth_base_color is not None and not _fb_color_src and str(fourth_base_color_source or '').strip().lower() != 'overlay':
                    _fb_r = float(fourth_base_color[0]) if len(fourth_base_color) > 0 else 1.0
                    _fb_g = float(fourth_base_color[1]) if len(fourth_base_color) > 1 else 1.0
                    _fb_b = float(fourth_base_color[2]) if len(fourth_base_color) > 2 else 1.0
                    _paint_overlay_fb_cpu[:, :, :3] *= np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = None if fourth_base_pattern == '__none__' else (fourth_base_pattern if (fourth_base_pattern and fourth_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None))
            _fb_pat_mask = _get_pattern_mask(_pat_id_fb, _fb_shape, hard_mask, seed + 3333, 1.0,
                scale=fourth_base_pattern_scale, rotation=fourth_base_pattern_rotation,
                opacity=fourth_base_pattern_opacity, strength=fourth_base_pattern_strength,
                offset_x=fourth_base_pattern_offset_x, offset_y=fourth_base_pattern_offset_y) if _pat_id_fb else None
            if _fb_pat_mask is not None:
                if fourth_base_pattern_invert:
                    _fb_pat_mask = 1.0 - _fb_pat_mask
                if fourth_base_pattern_harden:
                    _fb_pat_mask = np.clip((_fb_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fb = get_base_overlay_alpha(
                _fb_shape, fourth_base_strength, fourth_base_blend_mode,
                noise_scale=int(fourth_base_noise_scale), seed=seed + 2999,
                pattern_mask=_fb_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fourth_base_scale)))
            )
            _alpha_fb3 = _alpha_fb[:, :, np.newaxis]
            if abs(fourth_base_hue_shift) > 0.5 or abs(fourth_base_saturation) > 0.5 or abs(fourth_base_brightness) > 0.5:
                _paint_overlay_fb_cpu = _apply_hsb_adjustments(_paint_overlay_fb_cpu, hard_mask, fourth_base_hue_shift, fourth_base_saturation, fourth_base_brightness)
                _paint_overlay_fb_cpu = np.asarray(_paint_overlay_fb_cpu)
            if _fb_bm_norm == "pattern_screen":
                _screened_fb = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fb_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb3) + _screened_fb * _alpha_fb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb3) + _paint_overlay_fb_cpu[:, :, :3] * _alpha_fb3
        except Exception:
            pass

    if (fifth_base or fifth_base_color_source) and fifth_base_strength > 0.001:
        try:
            _fif_color_src = fifth_base_color_source if (fifth_base_color_source and str(fifth_base_color_source).startswith("mono:")) else None
            if not _fif_color_src and fifth_base and str(fifth_base).startswith("mono:"):
                _fif_color_src = fifth_base
            _paint_overlay_fif_cpu = paint.copy()
            _fif_shape = (paint.shape[0], paint.shape[1])
            _fif_mask3d = hard_mask[:, :, np.newaxis]
            if (_fif_color_src and _fif_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _fif_color_src[5:] in monolithic_registry) or
                    _fif_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _fif_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _fif_shape, hard_mask, seed + 13333, 1.0, 0.0)
                if _color_paint is not None:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _paint_overlay_fif_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _fif_color_src:
                print(f"    [PAINT OVERLAY 5th] WARNING: special source '{_fif_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fif_color = fifth_base_color if fifth_base_color is not None else [1.0, 1.0, 1.0]
                _fif_r = float(_fif_color[0]) if len(_fif_color) > 0 else 1.0
                _fif_g = float(_fif_color[1]) if len(_fif_color) > 1 else 1.0
                _fif_b = float(_fif_color[2]) if len(_fif_color) > 2 else 1.0
                _fif_rgb = np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
                _paint_overlay_fif_cpu[:, :, :3] = _paint_overlay_fif_cpu[:, :, :3] * (1.0 - _fif_mask3d) + _fif_rgb * _fif_mask3d
            if fifth_base and fifth_base in BASE_REGISTRY:
                _fif_def2 = BASE_REGISTRY[fifth_base]
                _fif_pfn = _fif_def2.get("paint_fn", paint_none)
                if _fif_pfn is not paint_none and not _fif_color_src:
                    _paint_overlay_fif_cpu = _fif_pfn(_paint_overlay_fif_cpu, _fif_shape, hard_mask, seed + 13333, 1.0, 0.0)
                    _paint_overlay_fif_cpu = np.asarray(_paint_overlay_fif_cpu) if not isinstance(_paint_overlay_fif_cpu, np.ndarray) else _paint_overlay_fif_cpu
                if fifth_base_color is not None and not _fif_color_src and str(fifth_base_color_source or '').strip().lower() != 'overlay':
                    _fif_r = float(fifth_base_color[0]) if len(fifth_base_color) > 0 else 1.0
                    _fif_g = float(fifth_base_color[1]) if len(fifth_base_color) > 1 else 1.0
                    _fif_b = float(fifth_base_color[2]) if len(fifth_base_color) > 2 else 1.0
                    _paint_overlay_fif_cpu[:, :, :3] *= np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = None if fifth_base_pattern == '__none__' else (fifth_base_pattern if (fifth_base_pattern and fifth_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None))
            _fif_pat_mask = _get_pattern_mask(_pat_id_fif, _fif_shape, hard_mask, seed + 4444, 1.0,
                scale=fifth_base_pattern_scale, rotation=fifth_base_pattern_rotation,
                opacity=fifth_base_pattern_opacity, strength=fifth_base_pattern_strength,
                offset_x=fifth_base_pattern_offset_x, offset_y=fifth_base_pattern_offset_y) if _pat_id_fif else None
            if _fif_pat_mask is not None:
                if fifth_base_pattern_invert:
                    _fif_pat_mask = 1.0 - _fif_pat_mask
                if fifth_base_pattern_harden:
                    _fif_pat_mask = np.clip((_fif_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fif = get_base_overlay_alpha(
                _fif_shape, fifth_base_strength, fifth_base_blend_mode,
                noise_scale=int(fifth_base_noise_scale), seed=seed + 3999,
                pattern_mask=_fif_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fifth_base_scale)))
            )
            _alpha_fif3 = _alpha_fif[:, :, np.newaxis]
            if abs(fifth_base_hue_shift) > 0.5 or abs(fifth_base_saturation) > 0.5 or abs(fifth_base_brightness) > 0.5:
                _paint_overlay_fif_cpu = _apply_hsb_adjustments(_paint_overlay_fif_cpu, hard_mask, fifth_base_hue_shift, fifth_base_saturation, fifth_base_brightness)
                _paint_overlay_fif_cpu = np.asarray(_paint_overlay_fif_cpu)
            if _fif_bm_norm == "pattern_screen":
                _screened_fif = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fif_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif3) + _screened_fif * _alpha_fif3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif3) + _paint_overlay_fif_cpu[:, :, :3] * _alpha_fif3
        except Exception:
            pass

    return paint


def compose_paint_mod_stacked(base_id, all_patterns, paint, shape, mask, seed, pm, bb, blend_base=None, blend_dir="horizontal", blend_amount=0.5,
                              second_base=None, second_base_color=None, second_base_strength=0.0, second_base_spec_strength=1.0,
                              second_base_blend_mode="noise", second_base_noise_scale=24,
                              second_base_scale=1.0, second_base_pattern=None,
                              second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                              second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                              second_base_pattern_invert=False, second_base_pattern_harden=False,
                              second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                              third_base=None, third_base_color=None, third_base_strength=0.0, third_base_spec_strength=1.0,
                              third_base_blend_mode="noise", third_base_noise_scale=24,
                              third_base_scale=1.0, third_base_pattern=None,
                              third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                              third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                              third_base_pattern_invert=False, third_base_pattern_harden=False,
                              third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                              fourth_base=None, fourth_base_color=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0,
                              fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                              fourth_base_scale=1.0, fourth_base_pattern=None,
                              fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                              fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                              fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                              fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                              fifth_base=None, fifth_base_color=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0,
                              fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                              fifth_base_scale=1.0, fifth_base_pattern=None,
                              fifth_base_pattern_scale=1.0, fifth_base_pattern_rotation=0.0,
                              fifth_base_pattern_opacity=1.0, fifth_base_pattern_strength=1.0,
                              fifth_base_pattern_invert=False, fifth_base_pattern_harden=False,
                              fifth_base_pattern_offset_x=0.5, fifth_base_pattern_offset_y=0.5,
                              second_base_hue_shift=0, second_base_saturation=0, second_base_brightness=0,
                              second_base_pattern_hue_shift=0, second_base_pattern_saturation=0, second_base_pattern_brightness=0,
                              third_base_hue_shift=0, third_base_saturation=0, third_base_brightness=0,
                              fourth_base_hue_shift=0, fourth_base_saturation=0, fourth_base_brightness=0,
                              fifth_base_hue_shift=0, fifth_base_saturation=0, fifth_base_brightness=0,
                              base_strength=1.0, base_spec_strength=1.0, spec_mult=1.0,
                              base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0,
                              base_flip_h=False, base_flip_v=False,
                              pattern_offset_x=0.5, pattern_offset_y=0.5,
                              **kwargs):
    """Apply base paint modifier then MULTIPLE stacked pattern paint modifiers.
    When second_base_color_source (etc.) is 'mono:xyz', overlay color comes from that special's paint_fn.
    PURE CPU: always receives and returns numpy arrays. The caller (build_multi_zone) handles GPU↔CPU conversion."""
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    # Ensure CPU numpy — CuPy inputs converted here (caller should prefer to_cpu before calling)
    if hasattr(paint, 'get'):
        paint = paint.get()
    paint = np.asarray(paint)
    if hasattr(mask, 'get'):
        mask = mask.get()
    mask = np.asarray(mask)
    second_base_color_source = kwargs.pop("second_base_color_source", None)
    third_base_color_source = kwargs.pop("third_base_color_source", None)
    fourth_base_color_source = kwargs.pop("fourth_base_color_source", None)
    fifth_base_color_source = kwargs.pop("fifth_base_color_source", None)
    base_color_mode = kwargs.pop("base_color_mode", "source")
    base_color = kwargs.pop("base_color", None)
    base_color_source = kwargs.pop("base_color_source", None)
    base_color_strength = kwargs.pop("base_color_strength", 1.0)
    base_hue_offset = float(kwargs.pop("base_hue_offset", 0))
    base_saturation_adjust = float(kwargs.pop("base_saturation_adjust", 0))
    base_brightness_adjust = float(kwargs.pop("base_brightness_adjust", 0))
    monolithic_registry = kwargs.pop("monolithic_registry", None)
    _pi_stk = max(0.0, min(1.0, float(kwargs.pop("pattern_intensity", 1.0))))
    hard_mask = np.where(np.asarray(mask) > 0.1, np.asarray(mask), np.float32(0.0)).astype(np.float32)
    base = BASE_REGISTRY[base_id]
    base_paint_fn = base.get("paint_fn", paint_none)
    has_any_pattern = len(all_patterns) > 0
    has_blend = (blend_base and blend_base in BASE_REGISTRY and blend_base != base_id)
    if has_blend:
        base2 = BASE_REGISTRY[blend_base]
        base2_paint_fn = base2.get("paint_fn", paint_none)

    active_paint_fns = 0
    for layer in all_patterns:
        pat_id = layer["id"]
        if pat_id in PATTERN_REGISTRY:
            pfn = PATTERN_REGISTRY[pat_id].get("paint_fn", paint_none)
            if pfn is not paint_none:
                active_paint_fns += 1

    _BASE_PAINT_BOOST = 1.0 * max(0.0, min(2.0, float(base_strength)))
    if base_paint_fn is not paint_none:
        # External paint_fn expects CPU (numpy) arrays — paint is already CPU here
        try:
            if has_any_pattern and active_paint_fns > 0:
                atten = 0.6 / max(1, active_paint_fns)
                _paint_result_stk = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST * atten, bb * _BASE_PAINT_BOOST * atten)
            else:
                _paint_result_stk = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST, bb * _BASE_PAINT_BOOST)
            paint = np.asarray(_paint_result_stk) if not isinstance(_paint_result_stk, np.ndarray) else _paint_result_stk
        except Exception as _bp_err_stk:
            print(f"[compose] WARNING: base_paint_fn failed for base '{base_id}': {_bp_err_stk}")

    # Record base material output before color override (same fix as compose_paint_mod)
    # Only copy when the lerp will actually be used (avoids ~32MB memcpy on most renders).
    _needs_lerp_stk = (_BASE_PAINT_BOOST < 1.0 - 0.001) and (base_paint_fn is not paint_none)
    if _needs_lerp_stk:
        _paint_after_base_stk = paint.copy()

    paint = _apply_base_color_override(
        paint, shape, hard_mask, seed,
        base_color_mode, base_color, base_color_source, base_color_strength,
        monolithic_registry
    )

    # HSB adjustments (hue shift, saturation, brightness)
    _hue_off = base_hue_offset
    _sat_adj = base_saturation_adjust
    _bri_adj = base_brightness_adjust
    if _hue_off or _sat_adj or _bri_adj:
        paint = _apply_hsb_adjustments(paint, hard_mask, _hue_off, _sat_adj, _bri_adj)

    # base_strength blends the material effect against the base color override
    if _needs_lerp_stk:
        _str_w = np.clip(_BASE_PAINT_BOOST, 0.0, 1.0)
        _mask3 = hard_mask[:, :, np.newaxis]
        paint[:, :, :3] = (
            _paint_after_base_stk[:, :, :3] * _str_w
            + paint[:, :, :3] * (1.0 - _str_w)
        ) * _mask3 + paint[:, :, :3] * (1.0 - _mask3)

    # Base transforms (offset, rotation, flip) applied to paint channels — all CPU
    _bo_x_stk = max(0.0, min(1.0, float(base_offset_x if base_offset_x is not None else 0.5)))
    _bo_y_stk = max(0.0, min(1.0, float(base_offset_y if base_offset_y is not None else 0.5)))
    _bro_stk = float(base_rotation if base_rotation is not None else 0) % 360.0
    if abs(_bo_x_stk - 0.5) > 0.001 or abs(_bo_y_stk - 0.5) > 0.001:
        for ch in range(min(3, paint.shape[2])):
            _apply_pattern_offset(paint[:, :, ch], shape, _bo_x_stk, _bo_y_stk)
    if abs(_bro_stk) > 0.5:
        for ch in range(min(3, paint.shape[2])):
            paint[:, :, ch] = _rotate_single_array(paint[:, :, ch], _bro_stk, shape)
    if base_flip_h:
        paint = np.fliplr(paint).copy()
    if base_flip_v:
        paint = np.flipud(paint).copy()

    if has_blend and base2_paint_fn is not paint_none:
        print(f"    [BLEND PAINT v6.1 STACKED] base={base_id} + blend={blend_base}, dir={blend_dir}, amount={blend_amount:.2f}")
        # External paint_fn expects CPU (numpy) arrays — paint is already CPU here
        _paint_blend_result_stk = base2_paint_fn(paint.copy(), shape, hard_mask, seed + 5000, 1.0, 1.0)
        paint_blend = np.asarray(_paint_blend_result_stk) if not isinstance(_paint_blend_result_stk, np.ndarray) else _paint_blend_result_stk
        h, w = shape
        rows_active = np.any(mask > 0.1, axis=1)
        cols_active = np.any(mask > 0.1, axis=0)
        if np.any(rows_active) and np.any(cols_active):
            r_min, r_max = np.where(rows_active)[0][[0, -1]]
            c_min, c_max = np.where(cols_active)[0][[0, -1]]
            bbox_h, bbox_w = max(1, r_max - r_min + 1), max(1, c_max - c_min + 1)
        else:
            r_min, c_min, bbox_h, bbox_w = 0, 0, h, w
        if blend_dir == "vertical":
            grad = np.zeros((h, w), dtype=np.float32)
            grad[r_min:r_min + bbox_h, :] = np.linspace(0, 1, bbox_h, dtype=np.float32)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
            grad[:r_min, :] = 0.0
            grad[r_min + bbox_h:, :] = 1.0
        elif blend_dir == "radial":
            cy, cx = r_min + bbox_h / 2.0, c_min + bbox_w / 2.0
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            grad = np.clip(np.sqrt((yy - cy)**2 + (xx - cx)**2) / (np.sqrt((bbox_h/2.0)**2 + (bbox_w/2.0)**2) + 1e-8), 0, 1)
        elif blend_dir == "diagonal":
            grad = np.zeros((h, w), dtype=np.float32)
            grad[r_min:r_min + bbox_h, c_min:c_min + bbox_w] = np.linspace(0, 1, bbox_h, dtype=np.float32)[:, np.newaxis] * 0.5 + np.linspace(0, 1, bbox_w, dtype=np.float32)[np.newaxis, :] * 0.5
            grad[:r_min, :] = 0.0
            grad[r_min + bbox_h:, :] = 1.0
        else:
            grad = np.zeros((h, w), dtype=np.float32)
            grad[:, c_min:c_min + bbox_w] = np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, bbox_w, dtype=np.float32)[np.newaxis, :]
            grad[:, :c_min] = 0.0
            grad[:, c_min + bbox_w:] = 1.0
        ba = max(0.1, min(3.0, blend_amount * 2.0 + 0.1))
        grad = np.power(grad, ba) * hard_mask
        grad_3d = grad[:, :, np.newaxis]
        paint = paint * (1.0 - grad_3d) + paint_blend * grad_3d

    _PAT_PAINT_BOOST = 1.8
    for layer_idx, layer in enumerate(all_patterns):
        pat_id = layer["id"]
        opacity = float(layer.get("opacity", 1.0))
        scale = float(layer.get("scale", 1.0))
        rotation = float(layer.get("rotation", 0))
        if pat_id not in PATTERN_REGISTRY or opacity <= 0:
            continue
        pattern = PATTERN_REGISTRY[pat_id]
        pat_paint_fn = pattern.get("paint_fn", paint_none)
        tex_fn = pattern.get("texture_fn")
        image_path = pattern.get("image_path")
        if image_path:
            from engine.render import _load_image_pattern, _load_color_image_pattern
            _img_ox_stk = float(layer.get("offset_x", pattern_offset_x))
            _img_oy_stk = float(layer.get("offset_y", pattern_offset_y))
            # Get the full color version
            rgba = _load_color_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if rgba is not None:
                # Per-pattern offset (supports Fit-to-Zone and Manual Placement)
                if abs(_img_ox_stk - 0.5) > 0.001 or abs(_img_oy_stk - 0.5) > 0.001:
                    for _ch in range(rgba.shape[2]):
                        _apply_pattern_offset(rgba[:, :, _ch], shape, _img_ox_stk, _img_oy_stk)
                r, g, b, alpha = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3]
                # Scale alpha by opacity, zone pattern_intensity, and mask (5% = hint, 100% = full)
                alpha_3d = (alpha[:, :, np.newaxis] * opacity * _pi_stk) * hard_mask[:, :, np.newaxis]
                rgb_3d = rgba[:, :, :3]
                # All CPU blend
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - alpha_3d) + rgb_3d * alpha_3d
            else:
                # Fallback to legacy grayscale shadow loading
                pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
                if pv is not None:
                    pv_min, pv_max = float(pv.min()), float(pv.max())
                    if pv_max - pv_min > 1e-8:
                        pv = (pv - pv_min) / (pv_max - pv_min)
                    else:
                        pv = np.ones_like(pv) * 0.5
                    if abs(_img_ox_stk - 0.5) > 0.001 or abs(_img_oy_stk - 0.5) > 0.001:
                        _apply_pattern_offset(pv, shape, _img_ox_stk, _img_oy_stk)
                    pv_3d = (pv[:, :, np.newaxis] * opacity * _pi_stk * spec_mult * 0.35)
                    # Mask so pattern only modifies paint INSIDE the zone
                    mask_3d = hard_mask[:, :, np.newaxis]
                    pv_masked = pv_3d * mask_3d
                    paint = np.clip(paint * (1.0 - pv_masked), 0, 1).astype(np.float32)
        elif pat_paint_fn is not paint_none:
            atten = opacity * 0.6 / max(1, active_paint_fns)
            layer_seed = seed + layer_idx * 7
            # External paint_fn expects CPU arrays — paint is already CPU here
            paint_before_layer = paint.copy()
            try:
                _layer_result = pat_paint_fn(paint, shape, hard_mask, layer_seed, pm * atten * spec_mult * _PAT_PAINT_BOOST, bb * atten * spec_mult * _PAT_PAINT_BOOST)
                paint = np.asarray(_layer_result) if not isinstance(_layer_result, np.ndarray) else _layer_result
            except Exception as _pp_err_stk:
                print(f"[compose] WARNING: pat_paint_fn failed for pattern '{pat_id}': {_pp_err_stk}")
                paint = paint_before_layer
            if tex_fn is not None:
                try:
                    # tex_fn expects CPU mask — mask is already CPU here
                    tex = tex_fn(shape, mask, layer_seed, 1.0)
                    pv = tex["pattern_val"] if isinstance(tex, dict) else tex
                    if scale != 1.0 and scale > 0:
                        if isinstance(tex, dict):
                            pv, tex = _scale_pattern_output(pv, tex, scale, shape)
                        else:
                            if scale < 1.0:
                                pv = _tile_fractional(pv, 1.0 / scale, shape[0], shape[1])
                            else:
                                pv = _crop_center_array(pv, scale, shape[0], shape[1])
                    rot_angle = rotation % 360
                    if rot_angle != 0:
                        pv = _rotate_single_array(pv, rot_angle, shape)
                    # Per-pattern offset (supports Fit-to-Zone and Manual Placement)
                    _tex_ox_stk = float(layer.get("offset_x", pattern_offset_x))
                    _tex_oy_stk = float(layer.get("offset_y", pattern_offset_y))
                    if abs(_tex_ox_stk - 0.5) > 0.001 or abs(_tex_oy_stk - 0.5) > 0.001:
                        _apply_pattern_offset(pv, shape, _tex_ox_stk, _tex_oy_stk)
                    pv_min, pv_max = float(pv.min()), float(pv.max())
                    if pv_max - pv_min > 1e-8:
                        pv = (pv - pv_min) / (pv_max - pv_min)
                    else:
                        pv = np.ones_like(pv) * 0.5
                    # Scale blend by zone pattern_intensity so 5% = hint, 100% = full
                    pv_3d = pv[:, :, np.newaxis] * _pi_stk
                    paint = paint_before_layer * (1.0 - pv_3d) + paint * pv_3d
                except Exception:
                    pass

    if (second_base or second_base_color_source) and second_base_strength > 0.001:
        try:
            # When overlay base is a special, use it as color source if none set (so user doesn't pick twice)
            _sb_color_src = second_base_color_source if (second_base_color_source and str(second_base_color_source).startswith("mono:")) else None
            if not _sb_color_src and second_base and str(second_base).startswith("mono:"):
                _sb_color_src = second_base
            _paint_overlay_st_cpu = paint.copy()
            _sb_shape = (paint.shape[0], paint.shape[1])
            _sb_mask3d = hard_mask[:, :, np.newaxis]
            if (_sb_color_src and _sb_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _sb_color_src[5:] in monolithic_registry) or
                    _sb_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _sb_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _sb_shape, hard_mask, seed + 7777, 1.0, 0.0)
                if _color_paint is not None:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _paint_overlay_st_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _sb_color_src:
                print(f"    [PAINT OVERLAY 2nd STACKED] WARNING: special source '{_sb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _sb_color = second_base_color if second_base_color is not None else [1.0, 1.0, 1.0]
                _sb_r = float(_sb_color[0]) if len(_sb_color) > 0 else 1.0
                _sb_g = float(_sb_color[1]) if len(_sb_color) > 1 else 1.0
                _sb_b = float(_sb_color[2]) if len(_sb_color) > 2 else 1.0
                _sb_rgb = np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                _paint_overlay_st_cpu[:, :, :3] = _paint_overlay_st_cpu[:, :, :3] * (1.0 - _sb_mask3d) + _sb_rgb * _sb_mask3d
            if second_base and second_base in BASE_REGISTRY:
                _sb_def2 = BASE_REGISTRY[second_base]
                _sb_pfn = _sb_def2.get("paint_fn", paint_none)
                # Skip base paint_fn when From Special is active (same fix as compose_paint_mod)
                if _sb_pfn is not paint_none and not _sb_color_src:
                    _paint_overlay_st_cpu = _sb_pfn(_paint_overlay_st_cpu, _sb_shape, hard_mask, seed + 7777, 1.0, 0.0)
                    _paint_overlay_st_cpu = np.asarray(_paint_overlay_st_cpu) if not isinstance(_paint_overlay_st_cpu, np.ndarray) else _paint_overlay_st_cpu
                if second_base_color is not None and not _sb_color_src and str(second_base_color_source or '').strip().lower() != 'overlay':
                    _sb_r = float(second_base_color[0]) if len(second_base_color) > 0 else 1.0
                    _sb_g = float(second_base_color[1]) if len(second_base_color) > 1 else 1.0
                    _sb_b = float(second_base_color[2]) if len(second_base_color) > 2 else 1.0
                    _paint_overlay_st_cpu[:, :, :3] *= np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_st = None if second_base_pattern == '__none__' else (second_base_pattern if (second_base_pattern and second_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            _sb_pat_mask_st = _get_pattern_mask(_pat_id_st, _sb_shape, hard_mask, seed, 1.0,
                scale=second_base_pattern_scale, rotation=second_base_pattern_rotation,
                opacity=second_base_pattern_opacity, strength=second_base_pattern_strength,
                offset_x=second_base_pattern_offset_x, offset_y=second_base_pattern_offset_y) if _pat_id_st and _pat_id_st != 'none' else None
            if _sb_pat_mask_st is not None:
                if second_base_pattern_invert:
                    _sb_pat_mask_st = 1.0 - _sb_pat_mask_st
                if second_base_pattern_harden:
                    _sb_pat_mask_st = np.clip((_sb_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_sb_st = get_base_overlay_alpha(
                _sb_shape, second_base_strength, second_base_blend_mode,
                noise_scale=int(second_base_noise_scale), seed=seed,
                pattern_mask=_sb_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(second_base_scale)))
            )
            _alpha_sb_st3 = _alpha_sb_st[:, :, np.newaxis]
            if abs(second_base_hue_shift) > 0.5 or abs(second_base_saturation) > 0.5 or abs(second_base_brightness) > 0.5:
                print(f"    [OVERLAY HSB] 2nd base: hue={second_base_hue_shift}, sat={second_base_saturation}, brt={second_base_brightness}")
                _paint_overlay_st_cpu = _apply_hsb_adjustments(_paint_overlay_st_cpu, hard_mask, second_base_hue_shift, second_base_saturation, second_base_brightness)
            if abs(second_base_pattern_hue_shift) > 0.5 or abs(second_base_pattern_saturation) > 0.5 or abs(second_base_pattern_brightness) > 0.5:
                _paint_overlay_st_cpu = _apply_hsb_adjustments(_paint_overlay_st_cpu, hard_mask, second_base_pattern_hue_shift, second_base_pattern_saturation, second_base_pattern_brightness)
            if _sb_bm_norm == "pattern_screen":
                _screened_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_st_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb_st3) + _screened_st * _alpha_sb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb_st3) + _paint_overlay_st_cpu[:, :, :3] * _alpha_sb_st3
        except Exception:
            pass

    if (third_base or third_base_color_source) and third_base_strength > 0.001:
        try:
            _tb_color_src = third_base_color_source if (third_base_color_source and str(third_base_color_source).startswith("mono:")) else None
            if not _tb_color_src and third_base and str(third_base).startswith("mono:"):
                _tb_color_src = third_base
            _paint_overlay_tb_st_cpu = paint.copy()
            _tb_shape = (paint.shape[0], paint.shape[1])
            _tb_mask3d = hard_mask[:, :, np.newaxis]
            if (_tb_color_src and _tb_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _tb_color_src[5:] in monolithic_registry) or
                    _tb_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _tb_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _tb_shape, hard_mask, seed + 9999, 1.0, 0.0)
                if _color_paint is not None:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _paint_overlay_tb_st_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _tb_color_src:
                print(f"    [PAINT OVERLAY 3rd STACKED] WARNING: special source '{_tb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _tb_color = third_base_color if third_base_color is not None else [1.0, 1.0, 1.0]
                _tb_r = float(_tb_color[0]) if len(_tb_color) > 0 else 1.0
                _tb_g = float(_tb_color[1]) if len(_tb_color) > 1 else 1.0
                _tb_b = float(_tb_color[2]) if len(_tb_color) > 2 else 1.0
                _tb_rgb = np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
                _paint_overlay_tb_st_cpu[:, :, :3] = _paint_overlay_tb_st_cpu[:, :, :3] * (1.0 - _tb_mask3d) + _tb_rgb * _tb_mask3d
            if third_base and third_base in BASE_REGISTRY:
                _tb_def2 = BASE_REGISTRY[third_base]
                _tb_pfn = _tb_def2.get("paint_fn", paint_none)
                if _tb_pfn is not paint_none and not _tb_color_src:
                    _paint_overlay_tb_st_cpu = _tb_pfn(_paint_overlay_tb_st_cpu, _tb_shape, hard_mask, seed + 9999, 1.0, 0.0)
                    _paint_overlay_tb_st_cpu = np.asarray(_paint_overlay_tb_st_cpu) if not isinstance(_paint_overlay_tb_st_cpu, np.ndarray) else _paint_overlay_tb_st_cpu
                if third_base_color is not None and not _tb_color_src and str(third_base_color_source or '').strip().lower() != 'overlay':
                    _tb_r = float(third_base_color[0]) if len(third_base_color) > 0 else 1.0
                    _tb_g = float(third_base_color[1]) if len(third_base_color) > 1 else 1.0
                    _tb_b = float(third_base_color[2]) if len(third_base_color) > 2 else 1.0
                    _paint_overlay_tb_st_cpu[:, :, :3] *= np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = None if third_base_pattern == '__none__' else (third_base_pattern if (third_base_pattern and third_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            _tb_pat_mask_st = _get_pattern_mask(_pat_id_tb, _tb_shape, hard_mask, seed + 5555, 1.0,
                scale=third_base_pattern_scale, rotation=third_base_pattern_rotation,
                opacity=third_base_pattern_opacity, strength=third_base_pattern_strength,
                offset_x=third_base_pattern_offset_x, offset_y=third_base_pattern_offset_y) if _pat_id_tb and _pat_id_tb != 'none' else None
            if _tb_pat_mask_st is not None:
                if third_base_pattern_invert:
                    _tb_pat_mask_st = 1.0 - _tb_pat_mask_st
                if third_base_pattern_harden:
                    _tb_pat_mask_st = np.clip((_tb_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_tb_st = get_base_overlay_alpha(
                _tb_shape, third_base_strength, third_base_blend_mode,
                noise_scale=int(third_base_noise_scale), seed=seed + 8888,
                pattern_mask=_tb_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(third_base_scale)))
            )
            _alpha_tb_st3 = _alpha_tb_st[:, :, np.newaxis]
            if abs(third_base_hue_shift) > 0.5 or abs(third_base_saturation) > 0.5 or abs(third_base_brightness) > 0.5:
                _paint_overlay_tb_st_cpu = _apply_hsb_adjustments(_paint_overlay_tb_st_cpu, hard_mask, third_base_hue_shift, third_base_saturation, third_base_brightness)
            if _tb_bm_norm == "pattern_screen":
                _screened_tb_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_tb_st_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb_st3) + _screened_tb_st * _alpha_tb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb_st3) + _paint_overlay_tb_st_cpu[:, :, :3] * _alpha_tb_st3
        except Exception:
            pass

    if (fourth_base or fourth_base_color_source) and fourth_base_strength > 0.001:
        try:
            _fb_color_src = fourth_base_color_source if (fourth_base_color_source and str(fourth_base_color_source).startswith("mono:")) else None
            if not _fb_color_src and fourth_base and str(fourth_base).startswith("mono:"):
                _fb_color_src = fourth_base
            _paint_overlay_fb_st_cpu = paint.copy()
            _fb_shape = (paint.shape[0], paint.shape[1])
            _fb_mask3d = hard_mask[:, :, np.newaxis]
            if (_fb_color_src and _fb_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _fb_color_src[5:] in monolithic_registry) or
                    _fb_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _fb_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _fb_shape, hard_mask, seed + 11111, 1.0, 0.0)
                if _color_paint is not None:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _paint_overlay_fb_st_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _fb_color_src:
                print(f"    [PAINT OVERLAY 4th STACKED] WARNING: special source '{_fb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fb_color = fourth_base_color if fourth_base_color is not None else [1.0, 1.0, 1.0]
                _fb_r = float(_fb_color[0]) if len(_fb_color) > 0 else 1.0
                _fb_g = float(_fb_color[1]) if len(_fb_color) > 1 else 1.0
                _fb_b = float(_fb_color[2]) if len(_fb_color) > 2 else 1.0
                _fb_rgb = np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
                _paint_overlay_fb_st_cpu[:, :, :3] = _paint_overlay_fb_st_cpu[:, :, :3] * (1.0 - _fb_mask3d) + _fb_rgb * _fb_mask3d
            if fourth_base and fourth_base in BASE_REGISTRY:
                _fb_def2 = BASE_REGISTRY[fourth_base]
                _fb_pfn = _fb_def2.get("paint_fn", paint_none)
                if _fb_pfn is not paint_none and not _fb_color_src:
                    _paint_overlay_fb_st_cpu = _fb_pfn(_paint_overlay_fb_st_cpu, _fb_shape, hard_mask, seed + 11111, 1.0, 0.0)
                    _paint_overlay_fb_st_cpu = np.asarray(_paint_overlay_fb_st_cpu) if not isinstance(_paint_overlay_fb_st_cpu, np.ndarray) else _paint_overlay_fb_st_cpu
                if fourth_base_color is not None and not _fb_color_src and str(fourth_base_color_source or '').strip().lower() != 'overlay':
                    _fb_r = float(fourth_base_color[0]) if len(fourth_base_color) > 0 else 1.0
                    _fb_g = float(fourth_base_color[1]) if len(fourth_base_color) > 1 else 1.0
                    _fb_b = float(fourth_base_color[2]) if len(fourth_base_color) > 2 else 1.0
                    _paint_overlay_fb_st_cpu[:, :, :3] *= np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = None if fourth_base_pattern == '__none__' else (fourth_base_pattern if (fourth_base_pattern and fourth_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            _fb_pat_mask_st = _get_pattern_mask(_pat_id_fb, _fb_shape, hard_mask, seed + 3333, 1.0,
                scale=fourth_base_pattern_scale, rotation=fourth_base_pattern_rotation,
                opacity=fourth_base_pattern_opacity, strength=fourth_base_pattern_strength,
                offset_x=fourth_base_pattern_offset_x, offset_y=fourth_base_pattern_offset_y) if _pat_id_fb and _pat_id_fb != 'none' else None
            if _fb_pat_mask_st is not None:
                if fourth_base_pattern_invert:
                    _fb_pat_mask_st = 1.0 - _fb_pat_mask_st
                if fourth_base_pattern_harden:
                    _fb_pat_mask_st = np.clip((_fb_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fb_st = get_base_overlay_alpha(
                _fb_shape, fourth_base_strength, fourth_base_blend_mode,
                noise_scale=int(fourth_base_noise_scale), seed=seed + 2999,
                pattern_mask=_fb_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fourth_base_scale)))
            )
            _alpha_fb_st3 = _alpha_fb_st[:, :, np.newaxis]
            if abs(fourth_base_hue_shift) > 0.5 or abs(fourth_base_saturation) > 0.5 or abs(fourth_base_brightness) > 0.5:
                _paint_overlay_fb_st_cpu = _apply_hsb_adjustments(_paint_overlay_fb_st_cpu, hard_mask, fourth_base_hue_shift, fourth_base_saturation, fourth_base_brightness)
            if _fb_bm_norm == "pattern_screen":
                _screened_fb_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fb_st_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb_st3) + _screened_fb_st * _alpha_fb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb_st3) + _paint_overlay_fb_st_cpu[:, :, :3] * _alpha_fb_st3
        except Exception:
            pass

    if (fifth_base or fifth_base_color_source) and fifth_base_strength > 0.001:
        try:
            _fif_color_src = fifth_base_color_source if (fifth_base_color_source and str(fifth_base_color_source).startswith("mono:")) else None
            if not _fif_color_src and fifth_base and str(fifth_base).startswith("mono:"):
                _fif_color_src = fifth_base
            _paint_overlay_fif_st_cpu = paint.copy()
            _fif_shape = (paint.shape[0], paint.shape[1])
            _fif_mask3d = hard_mask[:, :, np.newaxis]
            if (_fif_color_src and _fif_color_src.startswith("mono:") and (
                    (monolithic_registry is not None and _fif_color_src[5:] in monolithic_registry) or
                    _fif_color_src[5:] in BASE_REGISTRY)):
                _mono_id = _fif_color_src[5:]
                if monolithic_registry is not None and _mono_id in monolithic_registry:
                    _mono_paint_fn = monolithic_registry[_mono_id][1]
                else:
                    _mono_paint_fn = BASE_REGISTRY[_mono_id].get("paint_fn", paint_none)
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), _fif_shape, hard_mask, seed + 13333, 1.0, 0.0)
                if _color_paint is not None:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _paint_overlay_fif_st_cpu[:, :, :3] = np.asarray(_boost_overlay_mono_color(_color_paint[:, :, :3]))
            elif _fif_color_src:
                print(f"    [PAINT OVERLAY 5th STACKED] WARNING: special source '{_fif_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fif_color = fifth_base_color if fifth_base_color is not None else [1.0, 1.0, 1.0]
                _fif_r = float(_fif_color[0]) if len(_fif_color) > 0 else 1.0
                _fif_g = float(_fif_color[1]) if len(_fif_color) > 1 else 1.0
                _fif_b = float(_fif_color[2]) if len(_fif_color) > 2 else 1.0
                _fif_rgb = np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
                _paint_overlay_fif_st_cpu[:, :, :3] = _paint_overlay_fif_st_cpu[:, :, :3] * (1.0 - _fif_mask3d) + _fif_rgb * _fif_mask3d
            if fifth_base and fifth_base in BASE_REGISTRY:
                _fif_def2 = BASE_REGISTRY[fifth_base]
                _fif_pfn = _fif_def2.get("paint_fn", paint_none)
                if _fif_pfn is not paint_none and not _fif_color_src:
                    _paint_overlay_fif_st_cpu = _fif_pfn(_paint_overlay_fif_st_cpu, _fif_shape, hard_mask, seed + 13333, 1.0, 0.0)
                    _paint_overlay_fif_st_cpu = np.asarray(_paint_overlay_fif_st_cpu) if not isinstance(_paint_overlay_fif_st_cpu, np.ndarray) else _paint_overlay_fif_st_cpu
                if fifth_base_color is not None and not _fif_color_src and str(fifth_base_color_source or '').strip().lower() != 'overlay':
                    _fif_r = float(fifth_base_color[0]) if len(fifth_base_color) > 0 else 1.0
                    _fif_g = float(fifth_base_color[1]) if len(fifth_base_color) > 1 else 1.0
                    _fif_b = float(fifth_base_color[2]) if len(fifth_base_color) > 2 else 1.0
                    _paint_overlay_fif_st_cpu[:, :, :3] *= np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = None if fifth_base_pattern == '__none__' else (fifth_base_pattern if (fifth_base_pattern and fifth_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None)))
            _fif_pat_mask_st = _get_pattern_mask(_pat_id_fif, _fif_shape, hard_mask, seed + 4444, 1.0,
                scale=fifth_base_pattern_scale, rotation=fifth_base_pattern_rotation,
                opacity=fifth_base_pattern_opacity, strength=fifth_base_pattern_strength,
                offset_x=fifth_base_pattern_offset_x, offset_y=fifth_base_pattern_offset_y) if _pat_id_fif and _pat_id_fif != 'none' else None
            if _fif_pat_mask_st is not None:
                if fifth_base_pattern_invert:
                    _fif_pat_mask_st = 1.0 - _fif_pat_mask_st
                if fifth_base_pattern_harden:
                    _fif_pat_mask_st = np.clip((_fif_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fif_st = get_base_overlay_alpha(
                _fif_shape, fifth_base_strength, fifth_base_blend_mode,
                noise_scale=int(fifth_base_noise_scale), seed=seed + 3999,
                pattern_mask=_fif_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fifth_base_scale)))
            )
            _alpha_fif_st3 = _alpha_fif_st[:, :, np.newaxis]
            if abs(fifth_base_hue_shift) > 0.5 or abs(fifth_base_saturation) > 0.5 or abs(fifth_base_brightness) > 0.5:
                _paint_overlay_fif_st_cpu = _apply_hsb_adjustments(_paint_overlay_fif_st_cpu, hard_mask, fifth_base_hue_shift, fifth_base_saturation, fifth_base_brightness)
            if _fif_bm_norm == "pattern_screen":
                _screened_fif_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fif_st_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif_st3) + _screened_fif_st * _alpha_fif_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif_st3) + _paint_overlay_fif_st_cpu[:, :, :3] * _alpha_fif_st3
        except Exception:
            pass

    return paint


__all__ = [
    "compose_finish",
    "compose_finish_stacked",
    "compose_paint_mod",
    "compose_paint_mod_stacked",
    "_get_pattern_mask",
    "_apply_spec_blend_mode",
]
