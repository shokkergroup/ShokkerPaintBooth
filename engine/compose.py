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

import numpy as np

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
        tex = tex_fn(shape, mask, seed, sm)
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
        out = np.clip(pv * mask * max(0.0, min(1.0, float(opacity))) * max(0.0, min(2.0, float(strength))), 0, 1).astype(np.float32)
        _apply_pattern_offset(out, shape, offset_x, offset_y)
        return out
    except Exception:
        return None


def _apply_pattern_offset(pv, shape, offset_x, offset_y):
    """Apply pan offset to pattern array in-place. offset_x/y in [0,1]; 0.5 = no shift."""
    if pv is None or pv.size == 0:
        return
    try:
        h, w = int(shape[0]), int(shape[1])
        ox = float(offset_x) if offset_x is not None else 0.5
        oy = float(offset_y) if offset_y is not None else 0.5
        shift_x = int(round((ox - 0.5) * w))
        shift_y = int(round((oy - 0.5) * h))
        if shift_x != 0 or shift_y != 0:
            pv[:] = np.roll(pv, (-shift_y, -shift_x), axis=(0, 1))
    except Exception:
        pass


def _boost_overlay_mono_color(rgb):
    """Boost monolithic overlay readability without white blowout."""
    rgb = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    gray = rgb.mean(axis=2, keepdims=True)
    sat_boost = np.clip(gray + (rgb - gray) * 1.18, 0.0, 1.0)
    val_boost = np.clip(sat_boost * 1.12, 0.0, 1.0)
    return val_boost


def _mono_overlay_seed_paint(paint):
    """Generate neutral seed paint so mono overlays match swatch intent."""
    seed = np.full_like(paint[:, :, :3], 0.533, dtype=np.float32)
    return seed


def _apply_hsb_adjustments(paint, mask, hue_offset_deg, saturation_adjust, brightness_adjust):
    """Apply Hue/Saturation/Brightness adjustments to paint inside mask.
    hue_offset_deg: -180 to +180 degrees
    saturation_adjust: -100 to +100 (multiplicative: sat * (1 + adjust/100))
    brightness_adjust: -100 to +100 (multiplicative: val * (1 + adjust/100))
    """
    if abs(hue_offset_deg) < 0.5 and abs(saturation_adjust) < 0.5 and abs(brightness_adjust) < 0.5:
        return paint
    rgb = np.clip(paint[:, :, :3], 0.0, 1.0).astype(np.float32)
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
    m3 = mask[:, :, np.newaxis]
    paint = paint.copy()
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3) + adjusted * m3
    return paint


def _apply_base_color_override(paint, shape, hard_mask, seed, base_color_mode, base_color, base_color_source, base_color_strength, monolithic_registry):
    mode = str(base_color_mode or "source").strip().lower()
    if mode in ("", "source", "none"):
        return paint
    strength = max(0.0, min(1.0, float(base_color_strength if base_color_strength is not None else 1.0)))
    if strength <= 0.001:
        return paint

    src = None
    if mode in ("special", "from_special", "mono"):
        if isinstance(base_color_source, str):
            # --- Mono (special) source: "mono:finish_id" ---
            if base_color_source.startswith("mono:") and monolithic_registry is not None:
                mono_id = base_color_source[5:]
                if mono_id in monolithic_registry:
                    mono_paint_fn = monolithic_registry[mono_id][1]
                    src = mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 4242, 1.0, 0.0)
                    if src is not None:
                        src = _boost_overlay_mono_color(np.clip(src[:, :, :3], 0.0, 1.0))
            # --- Base finish source: raw ID or "base:finish_id" ---
            elif not base_color_source.startswith("mono:"):
                try:
                    from engine.registry import BASE_REGISTRY
                    raw_id = base_color_source[5:] if base_color_source.startswith("base:") else base_color_source
                    if raw_id in BASE_REGISTRY:
                        base_entry = BASE_REGISTRY[raw_id]
                        base_paint_fn = base_entry.get("paint_fn", paint_none)
                        if base_paint_fn is not paint_none:
                            src = base_paint_fn(paint.copy(), shape, hard_mask, seed + 4242, 1.0, 0.0)
                            if src is not None:
                                src = np.clip(src[:, :, :3], 0.0, 1.0)
                    # Also check monolithic registry with raw ID (user picked a special without prefix)
                    elif monolithic_registry is not None and raw_id in monolithic_registry:
                        mono_paint_fn = monolithic_registry[raw_id][1]
                        src = mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 4242, 1.0, 0.0)
                        if src is not None:
                            src = _boost_overlay_mono_color(np.clip(src[:, :, :3], 0.0, 1.0))
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

    w = (hard_mask * strength)[:, :, np.newaxis]
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - w) + src * w
    return paint


def _apply_spec_blend_mode(base_val, pattern_contrib, opacity, mode="normal"):
    """Apply a pattern contribution to a spec channel using the specified blend mode."""
    if mode == "normal" or mode not in ("multiply", "screen", "overlay", "hardlight", "softlight"):
        return base_val + pattern_contrib * opacity
    p_abs = np.abs(pattern_contrib)
    p_max = float(np.max(p_abs)) if np.max(p_abs) > 1e-8 else 1.0
    p_norm = pattern_contrib / p_max
    p_factor = np.clip(p_norm * 0.5 + 0.5, 0, 1)
    b_norm = np.clip(base_val / 255.0, 0, 1)
    if mode == "multiply":
        blended_norm = b_norm * (1.0 - opacity + opacity * p_factor * 2.0)
        return np.clip(blended_norm * 255.0, 0, 255)
    elif mode == "screen":
        screen_factor = p_factor * opacity
        blended_norm = 1.0 - (1.0 - b_norm) * (1.0 - screen_factor)
        return np.clip(blended_norm * 255.0, 0, 255)
    elif mode == "overlay":
        dark = 2.0 * b_norm * p_factor
        light = 1.0 - 2.0 * (1.0 - b_norm) * (1.0 - p_factor)
        overlay_result = np.where(b_norm < 0.5, dark, light)
        blended_norm = b_norm * (1.0 - opacity) + overlay_result * opacity
        return np.clip(blended_norm * 255.0, 0, 255)
    elif mode == "hardlight":
        # Hard Light: like overlay but with base/pattern roles swapped
        dark = 2.0 * b_norm * p_factor
        light = 1.0 - 2.0 * (1.0 - b_norm) * (1.0 - p_factor)
        hl_result = np.where(p_factor < 0.5, dark, light)
        blended_norm = b_norm * (1.0 - opacity) + hl_result * opacity
        return np.clip(blended_norm * 255.0, 0, 255)
    elif mode == "softlight":
        # Soft Light: gentler version — subtle spec shifts
        sl_result = (1.0 - 2.0 * p_factor) * b_norm * b_norm + 2.0 * p_factor * b_norm
        blended_norm = b_norm * (1.0 - opacity) + sl_result * opacity
        return np.clip(blended_norm * 255.0, 0, 255)
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
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    if pattern_sm is None:
        pattern_sm = sm
    _pat_int = max(0.0, min(1.0, float(pattern_intensity)))
    pattern_sm_eff = pattern_sm * _pat_int  # linear 0-100%: 5%=hint, 100%=full (matches paint)
    # NOTE: base_strength is a paint slider, handled in compose_paint_mod — not used in spec compositing.
    _sm_base = sm * max(0.0, min(2.0, float(base_spec_strength)))
    base = BASE_REGISTRY[base_id]
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    base_M = float(base["M"])
    base_R = float(base["R"])
    base_CC = int(base["CC"]) if base.get("CC") is not None else 16

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
    else:
        M_arr = np.full(base_shape, base_M, dtype=np.float32)
        R_arr = np.full(base_shape, base_R, dtype=np.float32)
        CC_arr = None

    if base_scale != 1.0 and base_scale > 0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1]):
        M_arr = _resize_array(M_arr, shape[0], shape[1])
        R_arr = _resize_array(R_arr, shape[0], shape[1])
        if CC_arr is not None:
            CC_arr = _resize_array(CC_arr, shape[0], shape[1])

    if cc_quality is not None:
        if base_CC > 0:
            cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        else:
            cc_value = (1.0 - float(cc_quality)) * 90.0
        if CC_arr is not None:
            CC_arr = CC_arr - float(base_CC) + cc_value
        else:
            CC_arr = np.full(shape, cc_value, dtype=np.float32)

    if blend_base and blend_base in BASE_REGISTRY and blend_base != base_id:
        base2 = BASE_REGISTRY[blend_base]
        base2_M = float(base2["M"])
        base2_R = float(base2["R"])
        base2_CC = int(base2["CC"]) if base2.get("CC") is not None else 16
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
    _bo_x = max(0.0, min(1.0, float(base_offset_x if base_offset_x is not None else 0.5)))
    _bo_y = max(0.0, min(1.0, float(base_offset_y if base_offset_y is not None else 0.5)))
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
            # Generate pattern (returns 0-1 float32 array)
            sp_arr = sp_fn(base_shape, seed + 5000 + hash(sp_name) % 10000, _sm_base, **sp_params)
            # Convert 0-1 pattern to spec-range contribution
            # Pattern centered at 0.5 means no change; >0.5 = increase, <0.5 = decrease
            sp_delta = (sp_arr - 0.5) * 2.0  # -1 to +1 range
            sp_range = float(sp_layer.get("range", 40.0))  # How many spec units of variation
            sp_contrib = sp_delta * sp_range  # Actual spec contribution

            if "M" in sp_channels and M_arr is not None:
                M_arr = _apply_spec_blend_mode(M_arr, sp_contrib, sp_opacity, sp_blend)
                M_arr = np.clip(M_arr, 0, 255).astype(np.float32)
            if "R" in sp_channels and R_arr is not None:
                R_arr = _apply_spec_blend_mode(R_arr, sp_contrib, sp_opacity, sp_blend)
                R_arr = np.clip(R_arr, 0, 255).astype(np.float32)
            if "C" in sp_channels and CC_arr is not None:
                CC_arr = _apply_spec_blend_mode(CC_arr, sp_contrib, sp_opacity, sp_blend)
                CC_arr = np.clip(CC_arr, 16, 255).astype(np.float32)

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
                R_range, M_range = 60.0, 50.0
                _pat_scale = pattern_sm_eff * spec_mult * max(0.0, min(1.0, float(pattern_opacity)))
                # Mask the pattern so it only affects pixels INSIDE the zone
                pv_masked = pv * mask
                M_arr = M_arr + pv_masked * M_range * _pat_scale
                R_arr = R_arr + pv_masked * R_range * _pat_scale
        elif tex_fn is not None:
            tex = tex_fn(shape, mask, seed, sm)
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

            if rot_angle != 0:
                if M_pv is not pv:
                    M_pv = _rotate_single_array(M_pv, rot_angle, shape)
                if R_pv is not pv:
                    R_pv = _rotate_single_array(R_pv, rot_angle, shape)
                if CC_pv is not None:
                    CC_pv = _rotate_single_array(CC_pv, rot_angle, shape)

            _pat_scale = pattern_sm_eff * spec_mult * max(0.0, min(1.0, float(pattern_opacity)))
            M_arr = M_arr + M_pv * M_range * _pat_scale
            R_arr = R_arr + R_pv * R_range * _pat_scale

            CC_range = tex.get("CC_range", 0)
            if CC_pv is not None and CC_range != 0:
                if CC_arr is not None:
                    CC_arr = CC_arr + CC_pv * CC_range * _pat_scale
                elif base_CC > 0:
                    CC_arr = np.full(shape, float(base_CC), dtype=np.float32) + CC_pv * CC_range * _pat_scale

            if "R_extra" in tex:
                R_arr = R_arr + tex["R_extra"] * _pat_scale
            if "M_extra" in tex:
                M_arr = M_arr + tex["M_extra"] * _pat_scale

            pat_CC = tex.get("CC")
            if pat_CC is None:
                pass
            elif isinstance(pat_CC, np.ndarray):
                final_CC = pat_CC
            else:
                final_CC = int(pat_CC)

    M_final = M_arr * mask + 5.0 * (1 - mask)
    R_final = R_arr * mask + 100.0 * (1 - mask)

    spec[:,:,0] = np.clip(M_final, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_final, 0, 255).astype(np.uint8)
    if isinstance(final_CC, np.ndarray):
        spec[:,:,2] = np.clip(final_CC * mask, 0, 255).astype(np.uint8)
    else:
        spec[:,:,2] = np.where(mask > 0.5, final_CC, 0).astype(np.uint8)
    spec[:,:,3] = 255

    if second_base and second_base_strength > 0.001:
        try:
            _sb_seed = seed + 999
            _sb_seed_off = abs(hash(second_base)) % 10000
            spec_secondary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(second_base).startswith("mono:") and monolithic_registry is not None:
                _mono_id = second_base[5:]
                if _mono_id in monolithic_registry:
                    _sb_spec_fn = monolithic_registry[_mono_id][0]
                    spec_secondary = _sb_spec_fn(shape, mask, _sb_seed + _sb_seed_off, sm)
            elif second_base in BASE_REGISTRY:
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
                spec_secondary[:,:,1] = np.clip(_sb_R_final, 0, 255).astype(np.uint8)
                spec_secondary[:,:,2] = np.clip(_sb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_secondary[:,:,3] = 255

            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_sb = second_base_pattern if second_base_pattern else pattern_id
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
            if str(third_base).startswith("mono:") and monolithic_registry is not None:
                _mono_id = third_base[5:]
                if _mono_id in monolithic_registry:
                    _tb_spec_fn = monolithic_registry[_mono_id][0]
                    spec_tertiary = _tb_spec_fn(shape, mask, _tb_seed + _tb_seed_off, sm)
            elif third_base in BASE_REGISTRY:
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
                spec_tertiary[:,:,1] = np.clip(_tb_R_final, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,2] = np.clip(_tb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,3] = 255
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = third_base_pattern if third_base_pattern else pattern_id
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
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    if pattern_sm is None:
        pattern_sm = sm
    _pat_int = max(0.0, min(1.0, float(pattern_intensity)))
    pattern_sm_eff = pattern_sm * _pat_int  # linear 0-100%: 5%=hint, 100%=full
    # NOTE: base_strength is a paint slider, handled in compose_paint_mod_stacked — not used in spec compositing.
    _sm_base = sm * max(0.0, min(2.0, float(base_spec_strength)))
    base = BASE_REGISTRY[base_id]
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    base_M = float(base["M"])
    base_R = float(base["R"])
    base_CC = int(base["CC"]) if base.get("CC") is not None else 16

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
    elif "noise_scales" in base:
        noise_weights = base.get("noise_weights", [1.0/len(base["noise_scales"])] * len(base["noise_scales"]))
        noise = multi_scale_noise(base_shape, base["noise_scales"], noise_weights, seed + 100)
        M_arr = base_M + noise * base.get("noise_M", 0) * _sm_base
        R_arr = base_R + noise * base.get("noise_R", 0) * _sm_base
        if base.get("noise_CC", 0) > 0:
            CC_arr = np.full(base_shape, float(base_CC), dtype=np.float32)
            CC_arr = CC_arr + noise * base.get("noise_CC", 0) * _sm_base
    else:
        M_arr = np.full(base_shape, base_M, dtype=np.float32)
        R_arr = np.full(base_shape, base_R, dtype=np.float32)

    if base_scale != 1.0 and base_scale > 0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1]):
        M_arr = _resize_array(M_arr, shape[0], shape[1])
        R_arr = _resize_array(R_arr, shape[0], shape[1])
        if CC_arr is not None:
            CC_arr = _resize_array(CC_arr, shape[0], shape[1])

    if cc_quality is not None and base_CC > 0:
        cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        if CC_arr is not None:
            CC_arr = CC_arr - float(base_CC) + cc_value
        else:
            CC_arr = np.full(shape, cc_value, dtype=np.float32)

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
    _bo_x = max(0.0, min(1.0, float(base_offset_x if base_offset_x is not None else 0.5)))
    _bo_y = max(0.0, min(1.0, float(base_offset_y if base_offset_y is not None else 0.5)))
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
            # Generate pattern (returns 0-1 float32 array)
            sp_arr = sp_fn(base_shape, seed + 5000 + hash(sp_name) % 10000, _sm_base, **sp_params)
            # Convert 0-1 pattern to spec-range contribution
            # Pattern centered at 0.5 means no change; >0.5 = increase, <0.5 = decrease
            sp_delta = (sp_arr - 0.5) * 2.0  # -1 to +1 range
            sp_range = float(sp_layer.get("range", 40.0))  # How many spec units of variation
            sp_contrib = sp_delta * sp_range  # Actual spec contribution

            if "M" in sp_channels and M_arr is not None:
                M_arr = _apply_spec_blend_mode(M_arr, sp_contrib, sp_opacity, sp_blend)
                M_arr = np.clip(M_arr, 0, 255).astype(np.float32)
            if "R" in sp_channels and R_arr is not None:
                R_arr = _apply_spec_blend_mode(R_arr, sp_contrib, sp_opacity, sp_blend)
                R_arr = np.clip(R_arr, 0, 255).astype(np.float32)
            if "C" in sp_channels and CC_arr is not None:
                CC_arr = _apply_spec_blend_mode(CC_arr, sp_contrib, sp_opacity, sp_blend)
                CC_arr = np.clip(CC_arr, 16, 255).astype(np.float32)

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
                # Mask the pattern so it only affects pixels INSIDE the zone
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
        tex = tex_fn(shape, mask, layer_seed, sm)
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
        # Master spec blend mode overrides per-layer blend when set
        _effective_spec_blend = base_spec_blend_mode if base_spec_blend_mode != "normal" else blend_mode
        M_contrib = M_pv * M_range * pattern_sm_eff * spec_mult
        R_contrib = R_pv * R_range * pattern_sm_eff * spec_mult
        M_arr = _apply_spec_blend_mode(M_arr, M_contrib, opacity, _effective_spec_blend)
        R_arr = _apply_spec_blend_mode(R_arr, R_contrib, opacity, _effective_spec_blend)
        CC_range = tex.get("CC_range", 0)
        if CC_pv is not None and CC_range != 0:
            final_CC = final_CC + CC_pv * CC_range * pattern_sm_eff * opacity * spec_mult
        if "R_extra" in tex:
            R_arr = R_arr + tex["R_extra"] * pattern_sm_eff * opacity * spec_mult
        if "M_extra" in tex:
            M_arr = M_arr + tex["M_extra"] * pattern_sm_eff * opacity * spec_mult
        pat_CC = tex.get("CC")
        if pat_CC is not None:
            if isinstance(pat_CC, np.ndarray):
                final_CC = final_CC * (1.0 - opacity) + pat_CC * opacity
            else:
                final_CC = final_CC * (1.0 - opacity) + float(pat_CC) * opacity

    M_final = M_arr * mask + 5.0 * (1 - mask)
    R_final = R_arr * mask + 100.0 * (1 - mask)
    spec[:,:,0] = np.clip(M_final, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R_final, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(final_CC * mask, 0, 255).astype(np.uint8)
    spec[:,:,3] = 255

    if second_base and second_base_strength > 0.001:
        try:
            _sb_seed = seed + 999
            _sb_seed_off = abs(hash(second_base)) % 10000
            spec_secondary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(second_base).startswith("mono:") and monolithic_registry is not None:
                _mono_id = second_base[5:]
                if _mono_id in monolithic_registry:
                    _sb_spec_fn = monolithic_registry[_mono_id][0]
                    spec_secondary = _sb_spec_fn(shape, mask, _sb_seed + _sb_seed_off, sm)
            elif second_base in BASE_REGISTRY:
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
                spec_secondary[:,:,1] = np.clip(_sb_R_final, 0, 255).astype(np.uint8)
                spec_secondary[:,:,2] = np.clip(_sb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_secondary[:,:,3] = 255
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id = second_base_pattern if second_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
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
            if str(third_base).startswith("mono:") and monolithic_registry is not None:
                _mono_id = third_base[5:]
                if _mono_id in monolithic_registry:
                    _tb_spec_fn = monolithic_registry[_mono_id][0]
                    spec_tertiary = _tb_spec_fn(shape, mask, _tb_seed + _tb_seed_off, sm)
            elif third_base in BASE_REGISTRY:
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
                spec_tertiary[:,:,1] = np.clip(_tb_R_final, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,2] = np.clip(_tb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,3] = 255
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = third_base_pattern if third_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
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
            if str(fourth_base).startswith("mono:") and monolithic_registry is not None:
                _mono_id = fourth_base[5:]
                if _mono_id in monolithic_registry:
                    _fb_spec_fn = monolithic_registry[_mono_id][0]
                    spec_fourth = _fb_spec_fn(shape, mask, _fb_seed + _fb_seed_off, sm)
            elif fourth_base in BASE_REGISTRY:
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
            _pat_id_fb = fourth_base_pattern if fourth_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
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
            if str(fifth_base).startswith("mono:") and monolithic_registry is not None:
                _mono_id = fifth_base[5:]
                if _mono_id in monolithic_registry:
                    _fif_spec_fn = monolithic_registry[_mono_id][0]
                    spec_fifth = _fif_spec_fn(shape, mask, _fif_seed + _fif_seed_off, sm)
            elif fifth_base in BASE_REGISTRY:
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
            _pat_id_fif = fifth_base_pattern if fifth_base_pattern else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
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
                      monolithic_registry=None, base_strength=1.0, base_spec_strength=1.0, spec_mult=1.0,
                      pattern_intensity=1.0,
                      base_hue_offset=0, base_saturation_adjust=0, base_brightness_adjust=0):
    """Apply base paint modifier then pattern paint modifier WITH spatial texture blending.
    pattern_intensity 0-1: 5%% = hint, 100%% = full (linear; avoids flip below 50%%).
    When second_base_color_source (etc.) is 'mono:xyz', the overlay color comes from that special's paint_fn (gradients, color shifts, etc.)."""
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    hard_mask = np.where(mask > 0.1, mask, 0.0).astype(np.float32)
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
        if has_pattern:
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST * 0.7, bb * _BASE_PAINT_BOOST * 0.7)
        else:
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST, bb * _BASE_PAINT_BOOST)

    # Record what the base paint_fn produced so we can blend it against the
    # base color override using base_strength as a mix weight.
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
    if _BASE_PAINT_BOOST < 1.0 and base_paint_fn is not paint_none:
        _str_w = np.clip(_BASE_PAINT_BOOST, 0.0, 1.0)
        _mask3 = hard_mask[:, :, np.newaxis]
        # paint currently = color_override result; _paint_after_base = full material
        paint[:, :, :3] = (
            _paint_after_base[:, :, :3] * _str_w
            + paint[:, :, :3] * (1.0 - _str_w)
        ) * _mask3 + paint[:, :, :3] * (1.0 - _mask3)

    if has_blend and base2_paint_fn is not paint_none:
        print(f"    [BLEND PAINT v6.1] base={base_id} + blend={blend_base}, dir={blend_dir}, amount={blend_amount:.2f}")
        paint_blend = paint.copy()
        _BLEND_PM, _BLEND_BB = 1.0, 1.0
        paint_blend = base2_paint_fn(paint_blend, shape, hard_mask, seed + 5000, _BLEND_PM, _BLEND_BB)
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

    # pattern_intensity 0–1: 5% = hint, 100% = full (linear so slider matches expectation)
    _pi = max(0.0, min(1.0, float(pattern_intensity)))
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
                # Scale alpha by pattern_intensity so 5% shows a hint, 100% full
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
            paint_before_pattern = paint.copy()
            _PAT_PAINT_BOOST = 1.8
            if base_paint_fn is not paint_none:
                paint = pat_paint_fn(paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST * 0.7 * spec_mult, bb * _PAT_PAINT_BOOST * 0.7 * spec_mult)
            else:
                paint = pat_paint_fn(paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST * spec_mult, bb * _PAT_PAINT_BOOST * spec_mult)
            if tex_fn is not None:
                try:
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
            paint_overlay = paint.copy()
            _sb_mask3d = hard_mask[:, :, np.newaxis]
            if (_sb_color_src and monolithic_registry is not None and _sb_color_src[5:] in monolithic_registry):
                _mono_id = _sb_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                print(f"    [PAINT OVERLAY 2nd] Using mono paint_fn for '{_mono_id}', fn={_mono_paint_fn}")
                # Mono paint_fn MODIFIES existing colors (chameleon shifts hues, etc.)
                # Pass the actual paint so the effect has real colors to transform.
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 7777, 1.0, 0.0)
                if _color_paint is None:
                    print(f"    [PAINT OVERLAY 2nd] WARNING: mono paint_fn returned None!")
                    _color_paint = paint.copy()
                else:
                    _cp_shape = _color_paint.shape if hasattr(_color_paint, 'shape') else 'N/A'
                    _cp_dtype = _color_paint.dtype if hasattr(_color_paint, 'dtype') else 'N/A'
                    _cp_min = float(_color_paint[:,:,:3].min()) if hasattr(_color_paint, 'min') else 'N/A'
                    _cp_max = float(_color_paint[:,:,:3].max()) if hasattr(_color_paint, 'max') else 'N/A'
                    print(f"    [PAINT OVERLAY 2nd] mono paint result: shape={_cp_shape}, dtype={_cp_dtype}, range=[{_cp_min:.3f}, {_cp_max:.3f}]")
                paint_overlay[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
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
                paint_overlay[:, :, :3] = paint_overlay[:, :, :3] * (1.0 - _sb_mask3d) + _sb_rgb * _sb_mask3d
            if second_base and second_base in BASE_REGISTRY:
                _sb_def2 = BASE_REGISTRY[second_base]
                _sb_pfn = _sb_def2.get("paint_fn", paint_none)
                # When "From Special" is active, skip the base paint_fn — the special's
                # colors are the user's explicit choice.  The base overlay contributes
                # its SPEC (metallic/roughness/CC) which is the PBR-correct approach;
                # its paint_fn would wash out the special's colors (e.g. Chrome pushes
                # toward silver, destroying a Bruise purple-to-black gradient).
                if _sb_pfn is not paint_none and not _sb_color_src:
                    paint_overlay = _sb_pfn(paint_overlay, shape, hard_mask, seed + 7777, 1.0, 0.0)
                # When source is 'overlay', we already used the base's color; don't multiply again.
                if second_base_color is not None and not _sb_color_src and str(second_base_color_source or '').strip().lower() != 'overlay':
                    _sb_r = float(second_base_color[0]) if len(second_base_color) > 0 else 1.0
                    _sb_g = float(second_base_color[1]) if len(second_base_color) > 1 else 1.0
                    _sb_b = float(second_base_color[2]) if len(second_base_color) > 2 else 1.0
                    paint_overlay[:, :, :3] *= np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_sb = second_base_pattern if (second_base_pattern and second_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None)
            _sb_pat_mask = _get_pattern_mask(_pat_id_sb, shape, hard_mask, seed, 1.0,
                scale=second_base_pattern_scale, rotation=second_base_pattern_rotation,
                opacity=second_base_pattern_opacity, strength=second_base_pattern_strength,
                offset_x=second_base_pattern_offset_x, offset_y=second_base_pattern_offset_y) if _pat_id_sb else None
            if _sb_pat_mask is not None:
                if second_base_pattern_invert:
                    _sb_pat_mask = 1.0 - _sb_pat_mask
                if second_base_pattern_harden:
                    _sb_pat_mask = np.clip((_sb_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_sb = get_base_overlay_alpha(
                shape, second_base_strength, second_base_blend_mode,
                noise_scale=int(second_base_noise_scale), seed=seed,
                pattern_mask=_sb_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(second_base_scale)))
            )
            _alpha_sb3 = _alpha_sb[:, :, np.newaxis]
            if _sb_bm_norm == "pattern_screen":
                _screened = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb3) + _screened * _alpha_sb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb3) + paint_overlay[:, :, :3] * _alpha_sb3
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
            paint_overlay_tb = paint.copy()
            _tb_mask3d = hard_mask[:, :, np.newaxis]
            if (_tb_color_src and monolithic_registry is not None and _tb_color_src[5:] in monolithic_registry):
                _mono_id = _tb_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 9999, 1.0, 0.0)
                if _color_paint is not None:
                    paint_overlay_tb[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
            elif _tb_color_src:
                print(f"    [PAINT OVERLAY 3rd] WARNING: special source '{_tb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _tb_color = third_base_color if third_base_color is not None else [1.0, 1.0, 1.0]
                _tb_r = float(_tb_color[0]) if len(_tb_color) > 0 else 1.0
                _tb_g = float(_tb_color[1]) if len(_tb_color) > 1 else 1.0
                _tb_b = float(_tb_color[2]) if len(_tb_color) > 2 else 1.0
                _tb_rgb = np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
                paint_overlay_tb[:, :, :3] = paint_overlay_tb[:, :, :3] * (1.0 - _tb_mask3d) + _tb_rgb * _tb_mask3d
            if third_base and third_base in BASE_REGISTRY:
                _tb_def2 = BASE_REGISTRY[third_base]
                _tb_pfn = _tb_def2.get("paint_fn", paint_none)
                if _tb_pfn is not paint_none and not _tb_color_src:
                    paint_overlay_tb = _tb_pfn(paint_overlay_tb, shape, hard_mask, seed + 9999, 1.0, 0.0)
                if third_base_color is not None and not _tb_color_src and str(third_base_color_source or '').strip().lower() != 'overlay':
                    _tb_r = float(third_base_color[0]) if len(third_base_color) > 0 else 1.0
                    _tb_g = float(third_base_color[1]) if len(third_base_color) > 1 else 1.0
                    _tb_b = float(third_base_color[2]) if len(third_base_color) > 2 else 1.0
                    paint_overlay_tb[:, :, :3] *= np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = third_base_pattern if (third_base_pattern and third_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None)
            _tb_pat_mask = _get_pattern_mask(_pat_id_tb, shape, hard_mask, seed + 5555, 1.0,
                scale=third_base_pattern_scale, rotation=third_base_pattern_rotation,
                opacity=third_base_pattern_opacity, strength=third_base_pattern_strength,
                offset_x=third_base_pattern_offset_x, offset_y=third_base_pattern_offset_y) if _pat_id_tb else None
            if _tb_pat_mask is not None:
                if third_base_pattern_invert:
                    _tb_pat_mask = 1.0 - _tb_pat_mask
                if third_base_pattern_harden:
                    _tb_pat_mask = np.clip((_tb_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_tb = get_base_overlay_alpha(
                shape, third_base_strength, third_base_blend_mode,
                noise_scale=int(third_base_noise_scale), seed=seed + 8888,
                pattern_mask=_tb_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(third_base_scale)))
            )
            _alpha_tb3 = _alpha_tb[:, :, np.newaxis]
            if _tb_bm_norm == "pattern_screen":
                _screened_tb = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay_tb[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb3) + _screened_tb * _alpha_tb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb3) + paint_overlay_tb[:, :, :3] * _alpha_tb3
        except Exception as _e:
            import traceback
            print(f"    [PAINT OVERLAY 3rd] ERROR: {_e}")
            traceback.print_exc()

    if (fourth_base or fourth_base_color_source) and fourth_base_strength > 0.001:
        try:
            _fb_color_src = fourth_base_color_source if (fourth_base_color_source and str(fourth_base_color_source).startswith("mono:")) else None
            if not _fb_color_src and fourth_base and str(fourth_base).startswith("mono:"):
                _fb_color_src = fourth_base
            paint_overlay_fb = paint.copy()
            _fb_mask3d = hard_mask[:, :, np.newaxis]
            if (_fb_color_src and monolithic_registry is not None and _fb_color_src[5:] in monolithic_registry):
                _mono_id = _fb_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 11111, 1.0, 0.0)
                if _color_paint is not None:
                    paint_overlay_fb[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
            elif _fb_color_src:
                print(f"    [PAINT OVERLAY 4th] WARNING: special source '{_fb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fb_color = fourth_base_color if fourth_base_color is not None else [1.0, 1.0, 1.0]
                _fb_r = float(_fb_color[0]) if len(_fb_color) > 0 else 1.0
                _fb_g = float(_fb_color[1]) if len(_fb_color) > 1 else 1.0
                _fb_b = float(_fb_color[2]) if len(_fb_color) > 2 else 1.0
                _fb_rgb = np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
                paint_overlay_fb[:, :, :3] = paint_overlay_fb[:, :, :3] * (1.0 - _fb_mask3d) + _fb_rgb * _fb_mask3d
            if fourth_base and fourth_base in BASE_REGISTRY:
                _fb_def2 = BASE_REGISTRY[fourth_base]
                _fb_pfn = _fb_def2.get("paint_fn", paint_none)
                if _fb_pfn is not paint_none and not _fb_color_src:
                    paint_overlay_fb = _fb_pfn(paint_overlay_fb, shape, hard_mask, seed + 11111, 1.0, 0.0)
                if fourth_base_color is not None and not _fb_color_src and str(fourth_base_color_source or '').strip().lower() != 'overlay':
                    _fb_r = float(fourth_base_color[0]) if len(fourth_base_color) > 0 else 1.0
                    _fb_g = float(fourth_base_color[1]) if len(fourth_base_color) > 1 else 1.0
                    _fb_b = float(fourth_base_color[2]) if len(fourth_base_color) > 2 else 1.0
                    paint_overlay_fb[:, :, :3] *= np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = fourth_base_pattern if (fourth_base_pattern and fourth_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None)
            _fb_pat_mask = _get_pattern_mask(_pat_id_fb, shape, hard_mask, seed + 3333, 1.0,
                scale=fourth_base_pattern_scale, rotation=fourth_base_pattern_rotation,
                opacity=fourth_base_pattern_opacity, strength=fourth_base_pattern_strength,
                offset_x=fourth_base_pattern_offset_x, offset_y=fourth_base_pattern_offset_y) if _pat_id_fb else None
            if _fb_pat_mask is not None:
                if fourth_base_pattern_invert:
                    _fb_pat_mask = 1.0 - _fb_pat_mask
                if fourth_base_pattern_harden:
                    _fb_pat_mask = np.clip((_fb_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fb = get_base_overlay_alpha(
                shape, fourth_base_strength, fourth_base_blend_mode,
                noise_scale=int(fourth_base_noise_scale), seed=seed + 2999,
                pattern_mask=_fb_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fourth_base_scale)))
            )
            _alpha_fb3 = _alpha_fb[:, :, np.newaxis]
            if _fb_bm_norm == "pattern_screen":
                _screened_fb = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay_fb[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb3) + _screened_fb * _alpha_fb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb3) + paint_overlay_fb[:, :, :3] * _alpha_fb3
        except Exception:
            pass

    if (fifth_base or fifth_base_color_source) and fifth_base_strength > 0.001:
        try:
            _fif_color_src = fifth_base_color_source if (fifth_base_color_source and str(fifth_base_color_source).startswith("mono:")) else None
            if not _fif_color_src and fifth_base and str(fifth_base).startswith("mono:"):
                _fif_color_src = fifth_base
            paint_overlay_fif = paint.copy()
            _fif_mask3d = hard_mask[:, :, np.newaxis]
            if (_fif_color_src and monolithic_registry is not None and _fif_color_src[5:] in monolithic_registry):
                _mono_id = _fif_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 13333, 1.0, 0.0)
                if _color_paint is not None:
                    paint_overlay_fif[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
            elif _fif_color_src:
                print(f"    [PAINT OVERLAY 5th] WARNING: special source '{_fif_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fif_color = fifth_base_color if fifth_base_color is not None else [1.0, 1.0, 1.0]
                _fif_r = float(_fif_color[0]) if len(_fif_color) > 0 else 1.0
                _fif_g = float(_fif_color[1]) if len(_fif_color) > 1 else 1.0
                _fif_b = float(_fif_color[2]) if len(_fif_color) > 2 else 1.0
                _fif_rgb = np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
                paint_overlay_fif[:, :, :3] = paint_overlay_fif[:, :, :3] * (1.0 - _fif_mask3d) + _fif_rgb * _fif_mask3d
            if fifth_base and fifth_base in BASE_REGISTRY:
                _fif_def2 = BASE_REGISTRY[fifth_base]
                _fif_pfn = _fif_def2.get("paint_fn", paint_none)
                if _fif_pfn is not paint_none and not _fif_color_src:
                    paint_overlay_fif = _fif_pfn(paint_overlay_fif, shape, hard_mask, seed + 13333, 1.0, 0.0)
                if fifth_base_color is not None and not _fif_color_src and str(fifth_base_color_source or '').strip().lower() != 'overlay':
                    _fif_r = float(fifth_base_color[0]) if len(fifth_base_color) > 0 else 1.0
                    _fif_g = float(fifth_base_color[1]) if len(fifth_base_color) > 1 else 1.0
                    _fif_b = float(fifth_base_color[2]) if len(fifth_base_color) > 2 else 1.0
                    paint_overlay_fif[:, :, :3] *= np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = fifth_base_pattern if (fifth_base_pattern and fifth_base_pattern != 'none') else (pattern_id if pattern_id and pattern_id != 'none' else None)
            _fif_pat_mask = _get_pattern_mask(_pat_id_fif, shape, hard_mask, seed + 4444, 1.0,
                scale=fifth_base_pattern_scale, rotation=fifth_base_pattern_rotation,
                opacity=fifth_base_pattern_opacity, strength=fifth_base_pattern_strength,
                offset_x=fifth_base_pattern_offset_x, offset_y=fifth_base_pattern_offset_y) if _pat_id_fif else None
            if _fif_pat_mask is not None:
                if fifth_base_pattern_invert:
                    _fif_pat_mask = 1.0 - _fif_pat_mask
                if fifth_base_pattern_harden:
                    _fif_pat_mask = np.clip((_fif_pat_mask.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fif = get_base_overlay_alpha(
                shape, fifth_base_strength, fifth_base_blend_mode,
                noise_scale=int(fifth_base_noise_scale), seed=seed + 3999,
                pattern_mask=_fif_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fifth_base_scale)))
            )
            _alpha_fif3 = _alpha_fif[:, :, np.newaxis]
            if _fif_bm_norm == "pattern_screen":
                _screened_fif = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay_fif[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif3) + _screened_fif * _alpha_fif3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif3) + paint_overlay_fif[:, :, :3] * _alpha_fif3
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
                              base_strength=1.0, base_spec_strength=1.0, spec_mult=1.0, **kwargs):
    """Apply base paint modifier then MULTIPLE stacked pattern paint modifiers.
    When second_base_color_source (etc.) is 'mono:xyz', overlay color comes from that special's paint_fn."""
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
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
    hard_mask = np.where(mask > 0.1, mask, 0.0).astype(np.float32)
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
        if has_any_pattern and active_paint_fns > 0:
            atten = 0.6 / max(1, active_paint_fns)
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST * atten, bb * _BASE_PAINT_BOOST * atten)
        else:
            paint = base_paint_fn(paint, shape, hard_mask, seed, pm * _BASE_PAINT_BOOST, bb * _BASE_PAINT_BOOST)

    # Record base material output before color override (same fix as compose_paint_mod)
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
    if _BASE_PAINT_BOOST < 1.0 and base_paint_fn is not paint_none:
        _str_w = np.clip(_BASE_PAINT_BOOST, 0.0, 1.0)
        _mask3 = hard_mask[:, :, np.newaxis]
        paint[:, :, :3] = (
            _paint_after_base_stk[:, :, :3] * _str_w
            + paint[:, :, :3] * (1.0 - _str_w)
        ) * _mask3 + paint[:, :, :3] * (1.0 - _mask3)


    if has_blend and base2_paint_fn is not paint_none:
        print(f"    [BLEND PAINT v6.1 STACKED] base={base_id} + blend={blend_base}, dir={blend_dir}, amount={blend_amount:.2f}")
        paint_blend = paint.copy()
        paint_blend = base2_paint_fn(paint_blend, shape, hard_mask, seed + 5000, 1.0, 1.0)
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
            # Get the full color version
            rgba = _load_color_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if rgba is not None:
                r, g, b, alpha = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3]
                # Scale alpha by opacity, zone pattern_intensity, and mask (5% = hint, 100% = full)
                alpha_3d = (alpha[:, :, np.newaxis] * opacity * _pi_stk) * hard_mask[:, :, np.newaxis]
                rgb_3d = rgba[:, :, :3]
                # Apply base darkening from image (emulate old shadow behavior if image is dark)
                # But mainly alpha blend color!
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
                    pv_3d = (pv[:, :, np.newaxis] * opacity * _pi_stk * spec_mult * 0.35)
                    # Mask so pattern only modifies paint INSIDE the zone
                    mask_3d = hard_mask[:, :, np.newaxis]
                    pv_masked = pv_3d * mask_3d
                    paint = np.clip(paint * (1.0 - pv_masked), 0, 1).astype(np.float32)
        elif pat_paint_fn is not paint_none:
            atten = opacity * 0.6 / max(1, active_paint_fns)
            layer_seed = seed + layer_idx * 7
            paint_before_layer = paint.copy()
            paint = pat_paint_fn(paint, shape, hard_mask, layer_seed, pm * atten * spec_mult * _PAT_PAINT_BOOST, bb * atten * spec_mult * _PAT_PAINT_BOOST)
            if tex_fn is not None:
                try:
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
            paint_overlay = paint.copy()
            _sb_mask3d = hard_mask[:, :, np.newaxis]
            if (_sb_color_src and monolithic_registry is not None and _sb_color_src[5:] in monolithic_registry):
                _mono_id = _sb_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 7777, 1.0, 0.0)
                if _color_paint is not None:
                    paint_overlay[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
            elif _sb_color_src:
                print(f"    [PAINT OVERLAY 2nd STACKED] WARNING: special source '{_sb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _sb_color = second_base_color if second_base_color is not None else [1.0, 1.0, 1.0]
                _sb_r = float(_sb_color[0]) if len(_sb_color) > 0 else 1.0
                _sb_g = float(_sb_color[1]) if len(_sb_color) > 1 else 1.0
                _sb_b = float(_sb_color[2]) if len(_sb_color) > 2 else 1.0
                _sb_rgb = np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                paint_overlay[:, :, :3] = paint_overlay[:, :, :3] * (1.0 - _sb_mask3d) + _sb_rgb * _sb_mask3d
            if second_base and second_base in BASE_REGISTRY:
                _sb_def2 = BASE_REGISTRY[second_base]
                _sb_pfn = _sb_def2.get("paint_fn", paint_none)
                # Skip base paint_fn when From Special is active (same fix as compose_paint_mod)
                if _sb_pfn is not paint_none and not _sb_color_src:
                    paint_overlay = _sb_pfn(paint_overlay, shape, hard_mask, seed + 7777, 1.0, 0.0)
                if second_base_color is not None and not _sb_color_src and str(second_base_color_source or '').strip().lower() != 'overlay':
                    _sb_r = float(second_base_color[0]) if len(second_base_color) > 0 else 1.0
                    _sb_g = float(second_base_color[1]) if len(second_base_color) > 1 else 1.0
                    _sb_b = float(second_base_color[2]) if len(second_base_color) > 2 else 1.0
                    paint_overlay[:, :, :3] *= np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_st = second_base_pattern if (second_base_pattern and second_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
            _sb_pat_mask_st = _get_pattern_mask(_pat_id_st, shape, hard_mask, seed, 1.0,
                scale=second_base_pattern_scale, rotation=second_base_pattern_rotation,
                opacity=second_base_pattern_opacity, strength=second_base_pattern_strength,
                offset_x=second_base_pattern_offset_x, offset_y=second_base_pattern_offset_y) if _pat_id_st and _pat_id_st != 'none' else None
            if _sb_pat_mask_st is not None:
                if second_base_pattern_invert:
                    _sb_pat_mask_st = 1.0 - _sb_pat_mask_st
                if second_base_pattern_harden:
                    _sb_pat_mask_st = np.clip((_sb_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_sb_st = get_base_overlay_alpha(
                shape, second_base_strength, second_base_blend_mode,
                noise_scale=int(second_base_noise_scale), seed=seed,
                pattern_mask=_sb_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(second_base_scale)))
            )
            _alpha_sb_st3 = _alpha_sb_st[:, :, np.newaxis]
            if _sb_bm_norm == "pattern_screen":
                _screened_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb_st3) + _screened_st * _alpha_sb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_sb_st3) + paint_overlay[:, :, :3] * _alpha_sb_st3
        except Exception:
            pass

    if (third_base or third_base_color_source) and third_base_strength > 0.001:
        try:
            _tb_color_src = third_base_color_source if (third_base_color_source and str(third_base_color_source).startswith("mono:")) else None
            if not _tb_color_src and third_base and str(third_base).startswith("mono:"):
                _tb_color_src = third_base
            paint_overlay_tb = paint.copy()
            _tb_mask3d = hard_mask[:, :, np.newaxis]
            if (_tb_color_src and monolithic_registry is not None and _tb_color_src[5:] in monolithic_registry):
                _mono_id = _tb_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 9999, 1.0, 0.0)
                if _color_paint is not None:
                    paint_overlay_tb[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
            elif _tb_color_src:
                print(f"    [PAINT OVERLAY 3rd STACKED] WARNING: special source '{_tb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _tb_color = third_base_color if third_base_color is not None else [1.0, 1.0, 1.0]
                _tb_r = float(_tb_color[0]) if len(_tb_color) > 0 else 1.0
                _tb_g = float(_tb_color[1]) if len(_tb_color) > 1 else 1.0
                _tb_b = float(_tb_color[2]) if len(_tb_color) > 2 else 1.0
                _tb_rgb = np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
                paint_overlay_tb[:, :, :3] = paint_overlay_tb[:, :, :3] * (1.0 - _tb_mask3d) + _tb_rgb * _tb_mask3d
            if third_base and third_base in BASE_REGISTRY:
                _tb_def2 = BASE_REGISTRY[third_base]
                _tb_pfn = _tb_def2.get("paint_fn", paint_none)
                if _tb_pfn is not paint_none and not _tb_color_src:
                    paint_overlay_tb = _tb_pfn(paint_overlay_tb, shape, hard_mask, seed + 9999, 1.0, 0.0)
                if third_base_color is not None and not _tb_color_src and str(third_base_color_source or '').strip().lower() != 'overlay':
                    _tb_r = float(third_base_color[0]) if len(third_base_color) > 0 else 1.0
                    _tb_g = float(third_base_color[1]) if len(third_base_color) > 1 else 1.0
                    _tb_b = float(third_base_color[2]) if len(third_base_color) > 2 else 1.0
                    paint_overlay_tb[:, :, :3] *= np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = third_base_pattern if (third_base_pattern and third_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
            _tb_pat_mask_st = _get_pattern_mask(_pat_id_tb, shape, hard_mask, seed + 5555, 1.0,
                scale=third_base_pattern_scale, rotation=third_base_pattern_rotation,
                opacity=third_base_pattern_opacity, strength=third_base_pattern_strength,
                offset_x=third_base_pattern_offset_x, offset_y=third_base_pattern_offset_y) if _pat_id_tb and _pat_id_tb != 'none' else None
            if _tb_pat_mask_st is not None:
                if third_base_pattern_invert:
                    _tb_pat_mask_st = 1.0 - _tb_pat_mask_st
                if third_base_pattern_harden:
                    _tb_pat_mask_st = np.clip((_tb_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_tb_st = get_base_overlay_alpha(
                shape, third_base_strength, third_base_blend_mode,
                noise_scale=int(third_base_noise_scale), seed=seed + 8888,
                pattern_mask=_tb_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(third_base_scale)))
            )
            _alpha_tb_st3 = _alpha_tb_st[:, :, np.newaxis]
            if _tb_bm_norm == "pattern_screen":
                _screened_tb_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay_tb[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb_st3) + _screened_tb_st * _alpha_tb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb_st3) + paint_overlay_tb[:, :, :3] * _alpha_tb_st3
        except Exception:
            pass

    if (fourth_base or fourth_base_color_source) and fourth_base_strength > 0.001:
        try:
            _fb_color_src = fourth_base_color_source if (fourth_base_color_source and str(fourth_base_color_source).startswith("mono:")) else None
            if not _fb_color_src and fourth_base and str(fourth_base).startswith("mono:"):
                _fb_color_src = fourth_base
            paint_overlay_fb = paint.copy()
            _fb_mask3d = hard_mask[:, :, np.newaxis]
            if (_fb_color_src and monolithic_registry is not None and _fb_color_src[5:] in monolithic_registry):
                _mono_id = _fb_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 11111, 1.0, 0.0)
                if _color_paint is not None:
                    paint_overlay_fb[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
            elif _fb_color_src:
                print(f"    [PAINT OVERLAY 4th STACKED] WARNING: special source '{_fb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fb_color = fourth_base_color if fourth_base_color is not None else [1.0, 1.0, 1.0]
                _fb_r = float(_fb_color[0]) if len(_fb_color) > 0 else 1.0
                _fb_g = float(_fb_color[1]) if len(_fb_color) > 1 else 1.0
                _fb_b = float(_fb_color[2]) if len(_fb_color) > 2 else 1.0
                _fb_rgb = np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
                paint_overlay_fb[:, :, :3] = paint_overlay_fb[:, :, :3] * (1.0 - _fb_mask3d) + _fb_rgb * _fb_mask3d
            if fourth_base and fourth_base in BASE_REGISTRY:
                _fb_def2 = BASE_REGISTRY[fourth_base]
                _fb_pfn = _fb_def2.get("paint_fn", paint_none)
                if _fb_pfn is not paint_none and not _fb_color_src:
                    paint_overlay_fb = _fb_pfn(paint_overlay_fb, shape, hard_mask, seed + 11111, 1.0, 0.0)
                if fourth_base_color is not None and not _fb_color_src and str(fourth_base_color_source or '').strip().lower() != 'overlay':
                    _fb_r = float(fourth_base_color[0]) if len(fourth_base_color) > 0 else 1.0
                    _fb_g = float(fourth_base_color[1]) if len(fourth_base_color) > 1 else 1.0
                    _fb_b = float(fourth_base_color[2]) if len(fourth_base_color) > 2 else 1.0
                    paint_overlay_fb[:, :, :3] *= np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = fourth_base_pattern if (fourth_base_pattern and fourth_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
            _fb_pat_mask_st = _get_pattern_mask(_pat_id_fb, shape, hard_mask, seed + 3333, 1.0,
                scale=fourth_base_pattern_scale, rotation=fourth_base_pattern_rotation,
                opacity=fourth_base_pattern_opacity, strength=fourth_base_pattern_strength,
                offset_x=fourth_base_pattern_offset_x, offset_y=fourth_base_pattern_offset_y) if _pat_id_fb and _pat_id_fb != 'none' else None
            if _fb_pat_mask_st is not None:
                if fourth_base_pattern_invert:
                    _fb_pat_mask_st = 1.0 - _fb_pat_mask_st
                if fourth_base_pattern_harden:
                    _fb_pat_mask_st = np.clip((_fb_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fb_st = get_base_overlay_alpha(
                shape, fourth_base_strength, fourth_base_blend_mode,
                noise_scale=int(fourth_base_noise_scale), seed=seed + 2999,
                pattern_mask=_fb_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fourth_base_scale)))
            )
            _alpha_fb_st3 = _alpha_fb_st[:, :, np.newaxis]
            if _fb_bm_norm == "pattern_screen":
                _screened_fb_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay_fb[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb_st3) + _screened_fb_st * _alpha_fb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb_st3) + paint_overlay_fb[:, :, :3] * _alpha_fb_st3
        except Exception:
            pass

    if (fifth_base or fifth_base_color_source) and fifth_base_strength > 0.001:
        try:
            _fif_color_src = fifth_base_color_source if (fifth_base_color_source and str(fifth_base_color_source).startswith("mono:")) else None
            if not _fif_color_src and fifth_base and str(fifth_base).startswith("mono:"):
                _fif_color_src = fifth_base
            paint_overlay_fif = paint.copy()
            _fif_mask3d = hard_mask[:, :, np.newaxis]
            if (_fif_color_src and monolithic_registry is not None and _fif_color_src[5:] in monolithic_registry):
                _mono_id = _fif_color_src[5:]
                _mono_paint_fn = monolithic_registry[_mono_id][1]
                _color_paint = _mono_paint_fn(_mono_overlay_seed_paint(paint), shape, hard_mask, seed + 13333, 1.0, 0.0)
                if _color_paint is not None:
                    paint_overlay_fif[:, :, :3] = _boost_overlay_mono_color(_color_paint[:, :, :3])
            elif _fif_color_src:
                print(f"    [PAINT OVERLAY 5th STACKED] WARNING: special source '{_fif_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fif_color = fifth_base_color if fifth_base_color is not None else [1.0, 1.0, 1.0]
                _fif_r = float(_fif_color[0]) if len(_fif_color) > 0 else 1.0
                _fif_g = float(_fif_color[1]) if len(_fif_color) > 1 else 1.0
                _fif_b = float(_fif_color[2]) if len(_fif_color) > 2 else 1.0
                _fif_rgb = np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
                paint_overlay_fif[:, :, :3] = paint_overlay_fif[:, :, :3] * (1.0 - _fif_mask3d) + _fif_rgb * _fif_mask3d
            if fifth_base and fifth_base in BASE_REGISTRY:
                _fif_def2 = BASE_REGISTRY[fifth_base]
                _fif_pfn = _fif_def2.get("paint_fn", paint_none)
                if _fif_pfn is not paint_none and not _fif_color_src:
                    paint_overlay_fif = _fif_pfn(paint_overlay_fif, shape, hard_mask, seed + 13333, 1.0, 0.0)
                if fifth_base_color is not None and not _fif_color_src and str(fifth_base_color_source or '').strip().lower() != 'overlay':
                    _fif_r = float(fifth_base_color[0]) if len(fifth_base_color) > 0 else 1.0
                    _fif_g = float(fifth_base_color[1]) if len(fifth_base_color) > 1 else 1.0
                    _fif_b = float(fifth_base_color[2]) if len(fifth_base_color) > 2 else 1.0
                    paint_overlay_fif[:, :, :3] *= np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = fifth_base_pattern if (fifth_base_pattern and fifth_base_pattern != 'none') else (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
            _fif_pat_mask_st = _get_pattern_mask(_pat_id_fif, shape, hard_mask, seed + 4444, 1.0,
                scale=fifth_base_pattern_scale, rotation=fifth_base_pattern_rotation,
                opacity=fifth_base_pattern_opacity, strength=fifth_base_pattern_strength,
                offset_x=fifth_base_pattern_offset_x, offset_y=fifth_base_pattern_offset_y) if _pat_id_fif and _pat_id_fif != 'none' else None
            if _fif_pat_mask_st is not None:
                if fifth_base_pattern_invert:
                    _fif_pat_mask_st = 1.0 - _fif_pat_mask_st
                if fifth_base_pattern_harden:
                    _fif_pat_mask_st = np.clip((_fif_pat_mask_st.astype(np.float32) - 0.30) / 0.40, 0, 1)
            _alpha_fif_st = get_base_overlay_alpha(
                shape, fifth_base_strength, fifth_base_blend_mode,
                noise_scale=int(fifth_base_noise_scale), seed=seed + 3999,
                pattern_mask=_fif_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(fifth_base_scale)))
            )
            _alpha_fif_st3 = _alpha_fif_st[:, :, np.newaxis]
            if _fif_bm_norm == "pattern_screen":
                _screened_fif_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - paint_overlay_fif[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif_st3) + _screened_fif_st * _alpha_fif_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif_st3) + paint_overlay_fif[:, :, :3] * _alpha_fif_st3
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
