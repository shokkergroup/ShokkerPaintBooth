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

PIPELINE / COMPOSITION ORDER:
  ============================
  For every zone the compose_finish flow is:

    1. Validate parameters (defaults applied for missing/None values)
    2. Look up the base material in BASE_REGISTRY
    3. Generate base spec arrays (M, R, optional CC) at base_shape
    4. Resize base arrays to canvas shape
    5. (Optional) GPU transfer for blend math
    6. Apply cc_quality / blend_base / paint_color modulations
    7. Apply base placement (offset, rotation, flip)
    8. Apply spec_pattern_stack overlays (delta on M/R/CC)
    9. Apply main pattern texture_fn or image (delta on M/R/CC)
   10. Mask + iron-rule clamp + dither, write uint8 spec
   11. Apply second/third/fourth/fifth-base overlays via blend_dual_base_spec
   12. Apply overlay_spec_pattern_stack

  Iron rules (CC>=16, R>=15 non-chrome) are enforced at step 10 and again
  inside every blend_dual_base_spec call.

CHANNEL SEMANTICS:
  Channel 0 (R) = Metallic, Channel 1 (G) = Roughness, Channel 2 (B) = Clearcoat,
  Channel 3 (A) = Specular Mask. See SPEC_MAP_REFERENCE.md.

DEBUG OUTPUT:
  Use engine.core.engine_core_set_verbose(True) to enable verbose per-zone logs.
"""

import math
import logging
import re as _re
import numpy as np
import time as _time
import cv2
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# 2026-04-21 HEENAN OVERNIGHT iter 2: docstring-driven default-channel
# resolver for spec-pattern layers. Mirrors the JS-side
# `_inferSpecPatternDefaultChannels` (paint-booth-2-state-zones.js:6899)
# so the engine and the UI agree on authored intent when no explicit
# `channels` value is supplied.
#
# iRacing spec map convention vs the engine's channel-letter convention:
#   docstring 'R=Metallic'   →  engine channel 'M'
#   docstring 'G=Roughness'  →  engine channel 'R'
#   docstring 'B=Clearcoat'  →  engine channel 'C'
#
# Returns 'MR' when no authored intent is found in the docstring — that
# matches the pre-fix blanket default for patterns that never declared
# their target channel.
#
# 2026-04-21 iter 7 follow-up: broadened the regex to also match the
# abbreviated form `R=Metallic.` (no `Targets` prefix) used by 15+
# pattern docstrings including guilloche_*, knurl_*, jeweling_circles,
# hairline_polish, lathe_concentric, bead_blast_uniform, etc. These
# patterns previously fell into the MR default even though they
# declared clear channel intent. Verified no negation-form matches
# (zero docstrings contain "not R=Metallic" / "no G=Roughness" / etc.).
_SPEC_TARGETS_PATTERN = _re.compile(
    r"\b([RGB])=(?:Metallic|Roughness|Clearcoat)\b",
    _re.IGNORECASE,
)


def _infer_spec_pattern_default_channels(sp_fn) -> str:
    if sp_fn is None:
        return "MR"
    doc = getattr(sp_fn, "__doc__", "") or ""
    if not doc:
        return "MR"
    # Collect the declared RGB letters, then emit in the canonical
    # MRC engine-channel order regardless of docstring phrasing. This
    # matches the JS resolver `_inferSpecPatternDefaultChannels` which
    # always outputs in MRC order via fixed-order if-statements.
    found = set()
    for match in _SPEC_TARGETS_PATTERN.finditer(doc):
        found.add(match.group(1).upper())
    channels = ""
    if "R" in found:
        channels += "M"   # R=Metallic  → engine channel M
    if "G" in found:
        channels += "R"   # G=Roughness → engine channel R
    if "B" in found:
        channels += "C"   # B=Clearcoat → engine channel C
    return channels or "MR"

logger = logging.getLogger("engine.compose")

# Compose pipeline version - bumped on signature/output-shape changes.
COMPOSE_VERSION = "6.1.2-platinum"

# ================================================================
# COMPOSE CONSTANTS — defaults for missing/invalid parameters
# ================================================================
DEFAULT_SCALE = 1.0           # Default pattern/base scale (no scaling)
DEFAULT_OPACITY = 1.0         # Default pattern opacity (fully visible)
DEFAULT_ROTATION = 0.0        # Default rotation in degrees
DEFAULT_OFFSET = 0.5          # Default offset (centered, no pan)
DEFAULT_STRENGTH = 1.0        # Default blend strength
DEFAULT_SPEC_MULT = 1.0       # Default spec multiplier
DEFAULT_NOISE_SCALE = 24      # Default noise scale for overlay blends
DEFAULT_CC_VALUE = 16         # Default clearcoat (max gloss)
PATTERN_OPACITY_MIN = 0.0     # Minimum pattern opacity
PATTERN_OPACITY_MAX = 1.0     # Maximum pattern opacity
SCALE_MIN = 0.01              # Minimum allowed scale factor
SCALE_MAX = 10.0              # Maximum allowed scale factor
STRENGTH_MAX = 2.0            # Maximum strength multiplier

# Pattern texture cache - avoids regenerating identical patterns across preview re-renders.
# Key: (pattern_id, h, w, seed, scale, rotation). Stores (pattern_val, tex_dict).
# Max 64 entries (~100MB at 2048x2048 with 4 arrays each). Cleared on paint file change.
_pattern_tex_cache: Dict[Any, Any] = {}
_PATTERN_CACHE_MAX = 64  # Increased from 32 -- handles complex multi-zone liveries with overlays
_pattern_cache_enabled = True

# Optional performance profiling: when COMPOSE_PROFILE is True, the @timed
# decorator below logs per-call wall-clock times at INFO level. Off by default
# so production renders stay quiet.
COMPOSE_PROFILE = False


def _set_compose_profile(flag: bool) -> None:
    """Enable / disable per-call profiling logs from @timed-decorated helpers."""
    global COMPOSE_PROFILE
    COMPOSE_PROFILE = bool(flag)


def _timed(label: Optional[str] = None):
    """Decorator: log function wall-clock time when COMPOSE_PROFILE is True.

    Args:
        label: Optional override for the log label; defaults to the function name.
    """
    def _wrap(fn):
        _name = label or fn.__name__

        def _inner(*args, **kwargs):
            if not COMPOSE_PROFILE:
                return fn(*args, **kwargs)
            _t0 = _time.time()
            try:
                return fn(*args, **kwargs)
            finally:
                logger.info("[profile] %s: %.2f ms", _name, (_time.time() - _t0) * 1000.0)
        _inner.__name__ = fn.__name__
        _inner.__doc__ = fn.__doc__
        return _inner
    return _wrap


def _get_cached_tex(tex_fn: Callable,
                    pattern_id: str,
                    shape: Tuple[int, int],
                    mask: np.ndarray,
                    seed: int,
                    sm: float,
                    scale: float = 1.0,
                    rotation: float = 0.0) -> Optional[Any]:
    """Call ``tex_fn`` with LRU caching. Returns the tex dict or None on failure.

    Args:
        tex_fn: Callable matching ``(shape, mask, seed, sm) -> dict``.
        pattern_id: Cache key prefix (the registry id).
        shape: (H, W).
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        sm: Spec multiplier.
        scale: Pattern scale factor (cached separately so size variations don't collide).
        rotation: Rotation in degrees (cached separately).

    Returns:
        The tex dict (whatever tex_fn returns) or None when generation failed.
    """
    # Validate scale and rotation defaults
    scale = max(SCALE_MIN, min(SCALE_MAX, float(scale if scale is not None else DEFAULT_SCALE)))
    rotation = float(rotation if rotation is not None else DEFAULT_ROTATION)
    if not _pattern_cache_enabled:
        try:
            result = tex_fn(shape, mask, seed, sm)
            logger.debug("_get_cached_tex: generated '%s' (uncached)", pattern_id)
            return result
        except Exception as _e:
            logger.warning("tex_fn failed for pattern '%s' (uncached, seed=%d): %s",
                           pattern_id, seed, _e)
            return None
    key = (pattern_id, int(shape[0]), int(shape[1]), int(seed),
           round(scale, 4), round(rotation, 2))
    cached = _pattern_tex_cache.get(key)
    if cached is not None:
        logger.debug("_get_cached_tex: cache hit for '%s'", pattern_id)
        return cached
    try:
        tex = tex_fn(shape, mask, seed, sm)
    except Exception as _e:
        logger.warning("tex_fn failed for pattern '%s' (seed=%d, shape=%s): %s",
                       pattern_id, seed, shape, _e)
        return None
    if len(_pattern_tex_cache) >= _PATTERN_CACHE_MAX:
        # Evict oldest entry (FIFO; close enough to LRU for our access pattern)
        _pattern_tex_cache.pop(next(iter(_pattern_tex_cache)))
    _pattern_tex_cache[key] = tex
    logger.debug("_get_cached_tex: cached '%s' (%d entries)", pattern_id, len(_pattern_tex_cache))
    return tex


def clear_pattern_cache() -> None:
    """Clear the pattern texture cache.

    Call when the paint file changes (different masks invalidate cached tex)
    or when canvas resolution changes mid-session. Safe to call any time.
    """
    _pattern_tex_cache.clear()


def pattern_cache_stats() -> Dict[str, int]:
    """Return cache occupancy stats for diagnostics."""
    return {
        "entries": len(_pattern_tex_cache),
        "max": _PATTERN_CACHE_MAX,
        "enabled": int(_pattern_cache_enabled),
    }


def _ggx_safe_R(R_arr: np.ndarray, M_arr: np.ndarray, lib=None) -> np.ndarray:
    """Conditional GGX roughness floor.

    Iron rule: R must be >= SPEC_ROUGHNESS_MIN (15) for non-chrome surfaces
    (M < SPEC_METALLIC_CHROME_THRESHOLD), or iRacing's GGX shader produces
    unrealistic mirror-flat highlights. Chrome (M>=240) is allowed R=0
    because that combination is the only way to get true mirror behaviour.

    This is the FINAL safety net at the compose output stage. Iron rules
    are also enforced inside individual finish_fn / spec_fn callers but
    rogue patterns sometimes slip through; this is the catch-all.

    Args:
        R_arr: Roughness array, any numeric dtype.
        M_arr: Metallic array of matching shape.
        lib: numpy or cupy module (pass ``xp`` for GPU). Defaults to numpy.

    Returns:
        Array with the same shape as R_arr, iron-rule compliant.
    """
    from engine.core import (SPEC_ROUGHNESS_MIN, SPEC_METALLIC_CHROME_THRESHOLD,
                              SPEC_CHANNEL_MAX, SPEC_CHANNEL_MIN)
    _np = lib if lib is not None else np
    R_clipped = _np.clip(R_arr, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX)
    return _np.where(M_arr < SPEC_METALLIC_CHROME_THRESHOLD,
                     _np.maximum(R_clipped, float(SPEC_ROUGHNESS_MIN)), R_clipped)


def _scale_base_spec_channels_toward_neutral(M_arr, R_arr, CC_arr, strength: float):
    """Scale a base's full material response toward neutral spec values."""
    _strength = float(strength)
    _neutral_M = 0.0
    _neutral_R = 128.0
    _neutral_CC = float(SPEC_CLEARCOAT_MIN)
    M_arr = _neutral_M + (M_arr - _neutral_M) * _strength
    R_arr = _neutral_R + (R_arr - _neutral_R) * _strength
    if CC_arr is not None:
        CC_arr = _neutral_CC + (CC_arr - _neutral_CC) * _strength
    return M_arr, R_arr, CC_arr


def _scale_base_clearcoat_scalar(base_cc: float, strength: float) -> float:
    """Scale a scalar clearcoat default toward the neutral floor."""
    _neutral_CC = float(SPEC_CLEARCOAT_MIN)
    return _neutral_CC + (float(base_cc) - _neutral_CC) * float(strength)

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
    SPEC_ROUGHNESS_MIN,
    SPEC_CLEARCOAT_MIN,
    SPEC_METALLIC_CHROME_THRESHOLD,
    SPEC_CHANNEL_MAX,
    SPEC_CHANNEL_MIN,
    SPEC_DEFAULT_OUTSIDE_M,
    SPEC_DEFAULT_OUTSIDE_R,
)
from engine.overlay import blend_dual_base_spec, blend_dual_base_paint, get_base_overlay_alpha, _normalize_second_base_blend_mode
from engine.spec_paint import paint_none


def _scale_down_spec_pattern_legacy_slow(sp_fn: Callable,
                             sp_scale: float,
                             canvas_shape: Union[Tuple[int, int], Tuple[int, int, int]],
                             seed_val: int,
                             sm_val: float,
                             sp_params: Dict[str, Any]) -> np.ndarray:
    """Generate a spec pattern at higher resolution, then downsample to canvas size.

    When scale < 1.0, instead of tiling the pattern (which creates visible
    grid boundaries), we generate the pattern at a larger resolution
    (canvas_size / scale) then smoothly downsample (cv2 INTER_AREA) back to
    canvas size. This effectively shrinks the pattern features without any
    tile seams.

    Args:
        sp_fn: The spec pattern generator function (signature
            ``sp_fn(shape, seed, sm, **kwargs) -> 2D float array``).
        sp_scale: The user scale factor (0 < sp_scale < 1.0).
        canvas_shape: Target (H, W) or (H, W, C) shape.
        seed_val: Deterministic seed.
        sm_val: Smoothness parameter passed through to sp_fn.
        sp_params: Extra keyword args forwarded to sp_fn.

    Returns:
        float32 array at canvas_shape[:2] dimensions with scaled-down pattern.
        Returns a neutral 0.5 array on irrecoverable failure.
    """
    h, w = int(canvas_shape[0]), int(canvas_shape[1])
    # Validate scale — protect against zero/negative
    sp_scale = max(SCALE_MIN, min(DEFAULT_SCALE, float(sp_scale)))
    inv_scale = 1.0 / sp_scale
    # Generate at higher resolution — cap at 8x to avoid memory issues
    MAX_UPSCALE = 8.0
    MAX_DIMENSION = 16384
    inv_scale_capped = min(inv_scale, MAX_UPSCALE)
    gen_h = min(MAX_DIMENSION, max(h, int(math.ceil(h * inv_scale_capped))))
    gen_w = min(MAX_DIMENSION, max(w, int(math.ceil(w * inv_scale_capped))))
    gen_shape = (gen_h, gen_w) if len(canvas_shape) == 2 else (gen_h, gen_w, canvas_shape[2])
    try:
        big_arr = sp_fn(gen_shape, seed_val, sm_val, **sp_params)
        logger.debug("_scale_down_spec_pattern: generated at %dx%d for %.2fx scale", gen_w, gen_h, sp_scale)
    except Exception as e:
        # Fallback: generate at canvas size and use smooth resize instead of tiling
        logger.warning("_scale_down_spec_pattern: upscale gen failed (%s), using canvas size", e)
        try:
            big_arr = sp_fn(canvas_shape, seed_val, sm_val, **sp_params)
        except Exception as e2:
            logger.error("_scale_down_spec_pattern: fallback also failed (%s), returning neutral", e2)
            return np.full((h, w), 0.5, dtype=np.float32)
        return np.asarray(big_arr, dtype=np.float32)
    # Downsample to canvas size using smooth interpolation (INTER_AREA for downscale)
    try:
        if big_arr.shape[0] != h or big_arr.shape[1] != w:
            big_arr = cv2.resize(big_arr.astype(np.float32), (w, h),
                                 interpolation=cv2.INTER_AREA)
    except cv2.error as e:
        logger.warning("_scale_down_spec_pattern: cv2.resize failed: %s", e)
    return np.asarray(big_arr, dtype=np.float32)


def _scale_down_spec_pattern(sp_fn: Callable,
                             sp_scale: float,
                             canvas_shape: Union[Tuple[int, int], Tuple[int, int, int]],
                             seed_val: int,
                             sm_val: float,
                             sp_params: Dict[str, Any]) -> np.ndarray:
    """Generate a scaled-down spec pattern without huge intermediate canvases."""
    h, w = int(canvas_shape[0]), int(canvas_shape[1])
    sp_scale = max(SCALE_MIN, min(DEFAULT_SCALE, float(sp_scale)))
    try:
        base_arr = sp_fn(canvas_shape, seed_val, sm_val, **sp_params)
    except Exception as e:
        logger.error("_scale_down_spec_pattern: generation failed (%s), returning neutral", e)
        return np.full((h, w), 0.5, dtype=np.float32)

    base_arr = np.asarray(base_arr, dtype=np.float32)
    try:
        if base_arr.shape[0] != h or base_arr.shape[1] != w:
            base_arr = cv2.resize(base_arr, (w, h), interpolation=cv2.INTER_LINEAR)
        inv_scale = min(10.0, 1.0 / sp_scale)
        yy = (np.floor(np.arange(h, dtype=np.float32) * inv_scale).astype(np.int32) % h)
        xx = (np.floor(np.arange(w, dtype=np.float32) * inv_scale).astype(np.int32) % w)
        return np.asarray(base_arr[yy[:, np.newaxis], xx[np.newaxis, :]], dtype=np.float32)
    except Exception as e:
        logger.warning("_scale_down_spec_pattern: periodic resample failed (%s), using canvas pattern", e)
        return np.asarray(base_arr, dtype=np.float32)


def _get_pattern_mask(pattern_id: Optional[str],
                      shape: Tuple[int, int],
                      mask: np.ndarray,
                      seed: int,
                      sm: float,
                      scale: float = 1.0,
                      rotation: float = 0.0,
                      opacity: float = 1.0,
                      strength: float = 1.0,
                      offset_x: float = 0.5,
                      offset_y: float = 0.5) -> Optional[np.ndarray]:
    """Build a (H, W) float32 alpha mask from a registered pattern.

    Used as the blend alpha when blend_mode='pattern' or any pattern-driven
    second-base mode. Resolves both image-based patterns (image_path) and
    procedural patterns (texture_fn).

    Args:
        pattern_id: Pattern registry id, or None / "none" / unknown id -> returns None.
        shape: (H, W) target shape.
        mask: (H, W) zone mask in [0, 1].
        seed: Deterministic seed.
        sm: Spec multiplier passed to texture_fn.
        scale: Pattern scale (0.1-10.0).
        rotation: Rotation in degrees.
        opacity: Alpha multiplier in [0, 1].
        strength: Strength multiplier in [0, 2].
        offset_x: Horizontal pan in [0, 1] (0.5 = centred).
        offset_y: Vertical pan in [0, 1].

    Returns:
        (H, W) float32 mask in [0, 1], or None when the pattern is unavailable
        / generation failed.
    """
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


def _apply_pattern_offset(pv: np.ndarray,
                          shape: Tuple[int, int],
                          offset_x: Optional[float],
                          offset_y: Optional[float]) -> None:
    """Apply a pan offset to a pattern array in-place.

    Args:
        pv: 2D pattern array. Modified in place via slice assignment.
        shape: (H, W) reference shape; used to convert normalized offsets to pixels.
        offset_x: 0-1 horizontal pan; 0.5 = centred (no shift). None defaults to centre.
        offset_y: 0-1 vertical pan; 0.5 = centred. None defaults to centre.

    Returns:
        None (operates in place).

    Notes:
        Uses xp.roll for GPU/CPU dual support. Single-pixel zones are skipped
        when shift would be zero. Errors are logged but never raised.
    """
    if pv is None or pv.size == 0:
        return
    try:
        h, w = int(shape[0]), int(shape[1])
        ox = float(offset_x) if offset_x is not None else DEFAULT_OFFSET
        oy = float(offset_y) if offset_y is not None else DEFAULT_OFFSET
        # Clamp offsets to valid range -- avoid surprise from sliders that overshoot
        ox = max(0.0, min(1.0, ox))
        oy = max(0.0, min(1.0, oy))
        shift_x = int(round((ox - 0.5) * w))
        shift_y = int(round((oy - 0.5) * h))
        if shift_x != 0 or shift_y != 0:
            # xp.roll works on both numpy and cupy
            pv[:] = xp.roll(pv, (-shift_y, -shift_x), axis=(0, 1))
    except Exception as e:
        logger.debug("_apply_pattern_offset: offset failed (%s), pattern unchanged", e)


def _dither_channel(arr: np.ndarray,
                    rng: Optional[np.random.RandomState] = None) -> np.ndarray:
    """Apply uniform-noise dither to a float array before uint8 conversion.

    Adds noise in [-0.5, 0.5] to break 8-bit banding artifacts in gradients.
    Vectorized numpy (no per-pixel loops).

    Args:
        arr: Source 2D float array; not mutated.
        rng: Optional RandomState for reproducibility (defaults to seed=42).

    Returns:
        uint8 array of the same shape, clipped to [0, 255].
    """
    if rng is None:
        rng = np.random.RandomState(42)
    if arr is None or arr.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    # Single-allocation path: copy + in-place add of noise. Total temp memory =
    # 1 * shape (vs 2x for `arr + rng.uniform(...)`).
    out = np.array(arr, dtype=np.float32, copy=True)
    out += rng.uniform(-0.5, 0.5, arr.shape).astype(np.float32)
    return np.clip(out, 0, 255).astype(np.uint8)


def _antialias_pattern(pv: np.ndarray, sigma: float = 0.5) -> np.ndarray:
    """Apply a subtle Gaussian blur to soften jagged pattern edges.

    Reduces moire artifacts in iRacing's renderer. sigma=0.5 is just enough
    to smooth 1px stairstepping without losing detail. Larger values (>1.0)
    soften features visibly and should only be used by callers that want
    that look explicitly.

    Args:
        pv: 2D pattern float array.
        sigma: Gaussian standard deviation in pixels.

    Returns:
        Blurred float32 array of the same shape. Returns input unchanged
        on empty input.
    """
    if pv is None or pv.size == 0:
        return pv
    if sigma <= 0:
        return pv  # no-op fast path
    # cv2.GaussianBlur needs odd kernel size; ksize=0 lets OpenCV pick from sigma
    try:
        return cv2.GaussianBlur(pv.astype(np.float32, copy=False), (0, 0),
                                sigmaX=float(sigma), sigmaY=float(sigma))
    except cv2.error as e:
        logger.warning("_antialias_pattern: GaussianBlur failed (sigma=%.3f, shape=%s): %s",
                       sigma, pv.shape, e)
        return pv


def _apply_spec_pattern_box_size(sp_arr: np.ndarray,
                                 canvas_shape: Tuple[int, int],
                                 box_size_pct: int,
                                 offset_x: float,
                                 offset_y: float) -> np.ndarray:
    """Mask a spec pattern to only affect a box region of the canvas.

    Args:
        sp_arr: 2D spec pattern array (values around 0.5 = neutral).
        canvas_shape: (H, W) canvas dimensions.
        box_size_pct: 5-100 (each dimension as percent of canvas).
        offset_x: 0-1 horizontal centre of the box.
        offset_y: 0-1 vertical centre of the box.

    Returns:
        2D array where pixels outside the box are 0.5 (= no effect in
        delta-style spec math).
    """
    if box_size_pct >= 100:
        return sp_arr
    h, w = int(canvas_shape[0]), int(canvas_shape[1])
    # Validate inputs and clamp -- defensive against UI sliders out of range
    box_size_pct = max(1, min(100, int(box_size_pct)))
    offset_x = max(0.0, min(1.0, float(offset_x)))
    offset_y = max(0.0, min(1.0, float(offset_y)))
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
    sp_np = np.asarray(sp_arr)
    result = np.full_like(sp_np, 0.5, dtype=np.float32)
    # Copy the pattern data inside the box region.
    # The pattern was generated at full canvas size, so crop the corresponding region.
    result[y0:y1, x0:x1] = sp_np[y0:y1, x0:x1]
    return result


def _boost_overlay_mono_color(rgb: np.ndarray) -> np.ndarray:
    """Boost monolithic overlay readability without white-clipping.

    Algorithm: 18% saturation push (move colors away from gray) followed by
    a 12% global gain. The fused expression keeps it to one intermediate
    array (vs three for the naive saturate-then-multiply path).

    Args:
        rgb: (H, W, 3) float32 paint array in [0, 1]. CuPy inputs accepted
            and transferred to CPU.

    Returns:
        (H, W, 3) float32 CPU array with boosted readability.
    """
    # Ensure CPU numpy array -- accept CuPy arrays via .get()
    if hasattr(rgb, 'get'):
        rgb = rgb.get()
    rgb_np = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    if rgb_np.ndim != 3 or rgb_np.shape[2] < 3:
        logger.warning("_boost_overlay_mono_color: expected (H, W, 3) got shape %s, returning input unchanged",
                       rgb_np.shape)
        return rgb_np
    gray = rgb_np.mean(axis=2, keepdims=True)
    # Fused: (gray + (rgb - gray)*1.18) * 1.12 -- single intermediate array
    result = gray + (rgb_np - gray) * 1.18
    result *= 1.12
    return np.clip(result, 0.0, 1.0)


def _mono_overlay_seed_paint(paint: np.ndarray) -> np.ndarray:
    """Generate neutral seed paint so mono overlays match the swatch intent.

    Mono finishes work by re-coloring a neutral mid-gray base (0.533 ~= 50% perceptual
    gray after sRGB display gamma). Using the actual paint as the seed would let the
    underlying color bleed through and contaminate the swatch.

    Args:
        paint: (H, W, 3+) float32 paint array.

    Returns:
        (H, W, 3) float32 array filled with 0.533 (CPU/numpy).
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint_cpu = to_cpu(paint) if is_gpu() else paint
    return np.full_like(paint_cpu[:, :, :3], 0.533, dtype=np.float32)


def _base_color_replaces_source_before_material(base_color_mode, base_color_strength, base_strength=1.0) -> bool:
    """Return True when a base color should be the material renderer's input.

    Full-strength replacement color modes are not tints. They are the new paint
    substrate for the selected material, so PSD/source art must not be sampled
    by the material paint_fn before the override happens.
    """
    mode = str(base_color_mode or "source").strip().lower()
    if mode in ("", "source", "none"):
        return False
    try:
        color_strength = float(base_color_strength if base_color_strength is not None else 1.0)
    except (TypeError, ValueError):
        color_strength = 1.0
    try:
        material_strength = float(base_strength if base_strength is not None else 1.0)
    except (TypeError, ValueError):
        material_strength = 1.0
    return (
        mode in ("solid", "gradient", "special", "from_special", "mono")
        and color_strength >= 0.999
        and material_strength >= 0.999
    )


def _overlay_mono_color_source(base_id, color_source):
    """Resolve the special color source for a base overlay layer.

    ``overlay`` means "same as overlay base", so a mono base owns the color.
    ``solid`` means the user explicitly wants the swatch color, so do not auto
    promote a mono base into its own color renderer.
    """
    src = str(color_source or "").strip()
    src_l = src.lower()
    if src.startswith("mono:"):
        return src
    if src_l in ("solid", "source", "none", "null"):
        return None
    if base_id and str(base_id).startswith("mono:") and src_l in ("", "overlay"):
        return str(base_id)
    return None


def _apply_hsb_adjustments(paint: np.ndarray,
                           mask: np.ndarray,
                           hue_offset_deg: float,
                           saturation_adjust: float,
                           brightness_adjust: float) -> np.ndarray:
    """Apply Hue/Saturation/Brightness adjustments to paint inside the mask.

    Args:
        paint: (H, W, 3+) float32 paint array.
        mask: (H, W) zone mask; resized to match paint if dimensions differ.
        hue_offset_deg: -180 to +180 degrees of hue rotation.
        saturation_adjust: -100 to +100 (applied multiplicatively: sat * (1 + adjust/100)).
        brightness_adjust: -100 to +100 (applied multiplicatively: val * (1 + adjust/100)).

    Returns:
        (H, W, 3+) float32 paint with HSB adjustments inside the mask only.
        On error, returns the input unchanged. Always operates on CPU numpy
        arrays (HSV conversion uses cv2 internally).

    Notes:
        Fast path: when all three adjustments are below 0.5 we skip the
        sRGB -> HSV -> sRGB round-trip entirely (typical for the
        "Edit zone" UI when the user hasn't moved any HSB sliders).
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    try:
        if (abs(hue_offset_deg) < 0.5 and
                abs(saturation_adjust) < 0.5 and
                abs(brightness_adjust) < 0.5):
            return paint  # fast path: no-op
        # rgb_to_hsv_array / hsv_to_rgb_vec use cv2 internally -> need CPU numpy arrays
        _paint_cpu = paint.get() if hasattr(paint, 'get') else np.asarray(paint)
        _mask_cpu = mask.get() if hasattr(mask, 'get') else np.asarray(mask)
        rgb = np.clip(_paint_cpu[:, :, :3], 0.0, 1.0).astype(np.float32)
        # Ensure mask matches paint dimensions
        if _mask_cpu.shape[0] != rgb.shape[0] or _mask_cpu.shape[1] != rgb.shape[1]:
            _mask_cpu = cv2.resize(_mask_cpu.astype(np.float32), (rgb.shape[1], rgb.shape[0]),
                                   interpolation=cv2.INTER_NEAREST)
        hsv = rgb_to_hsv_array(rgb)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        if abs(hue_offset_deg) >= 0.5:
            h = (h + hue_offset_deg / 360.0) % 1.0
        if abs(saturation_adjust) >= 0.5:
            s = np.clip(s * (1.0 + saturation_adjust / 100.0), 0.0, 1.0)
        if abs(brightness_adjust) >= 0.5:
            v = np.clip(v * (1.0 + brightness_adjust / 100.0), 0.0, 1.0)
        r, g, b = hsv_to_rgb_vec(h, s, v)
        adjusted = np.stack([np.clip(r, 0, 1), np.clip(g, 0, 1), np.clip(b, 0, 1)],
                            axis=-1).astype(np.float32)
        # All blending is CPU-only
        m3 = _mask_cpu[:, :, np.newaxis]
        _paint_cpu = _paint_cpu.copy()
        _paint_cpu[:, :, :3] = _paint_cpu[:, :, :3] * (1.0 - m3) + adjusted * m3
        return _paint_cpu
    except Exception as e:
        # Log once via logger (no per-zone print spam)
        logger.warning("_apply_hsb_adjustments failed (h=%.1f, s=%.1f, b=%.1f): %s",
                       hue_offset_deg, saturation_adjust, brightness_adjust, e)
        return paint


def generate_custom_gradient(shape: Tuple[int, int],
                             gradient_config: Dict[str, Any]) -> np.ndarray:
    """Generate a custom multi-stop gradient image.

    Args:
        shape: (H, W) tuple for the output size.
        gradient_config: dict with keys:
            stops: list of {"pos": 0.0-1.0, "color": [R, G, B]} (0-1 float each)
            direction: "horizontal" | "vertical" | "diagonal_down" | "diagonal_up"
                       | "radial" | "angular"
            angle: optional rotation in degrees (only applies to linear directions).

    Returns:
        (H, W, 3) float32 array with values in [0, 1]. Returns a black image
        if shape is invalid; returns a single-color image if exactly one stop
        is supplied.

    Notes:
        - Channels are interpolated independently via np.interp (vectorized);
          this is the perf-equivalent of a hand-rolled gradient texture.
        - All math runs in sRGB space (no gamma round-trip) so the gradient
          matches what artists see in the editor.
    """
    H, W = int(shape[0]), int(shape[1])
    if H <= 0 or W <= 0:
        logger.warning("generate_custom_gradient: invalid shape %s, returning empty", shape)
        return np.zeros((max(1, H), max(1, W), 3), dtype=np.float32)
    if not isinstance(gradient_config, dict):
        raise TypeError(f"generate_custom_gradient: gradient_config must be dict, got {type(gradient_config).__name__}")
    stops = gradient_config.get("stops", [{"pos": 0.0, "color": [0, 0, 0]}, {"pos": 1.0, "color": [1, 1, 1]}])
    direction = str(gradient_config.get("direction", "horizontal")).strip().lower()
    angle_deg = float(gradient_config.get("angle", 0))

    # Sort stops by position and clamp
    stops = sorted(stops, key=lambda s: float(s.get("pos", 0)))
    positions = np.array([max(0.0, min(1.0, float(s["pos"]))) for s in stops], dtype=np.float32)
    colors = np.array([[float(c) for c in s["color"][:3]] for s in stops], dtype=np.float32)

    # Ensure at least 2 stops
    if len(positions) < 2:
        if len(positions) == 1:
            positions = np.array([0.0, 1.0], dtype=np.float32)
            colors = np.vstack([colors, colors])
        else:
            return np.zeros((H, W, 3), dtype=np.float32)

    # Build the parametric coordinate t (0-1) for each pixel
    if direction == "vertical":
        t = np.linspace(0, 1, H, dtype=np.float32)[:, np.newaxis].repeat(W, axis=1)
    elif direction == "diagonal_down":
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, np.newaxis]
        xx = np.linspace(0, 1, W, dtype=np.float32)[np.newaxis, :]
        t = np.clip((xx + yy) * 0.5, 0, 1).astype(np.float32)
    elif direction == "diagonal_up":
        yy = np.linspace(1, 0, H, dtype=np.float32)[:, np.newaxis]
        xx = np.linspace(0, 1, W, dtype=np.float32)[np.newaxis, :]
        t = np.clip((xx + yy) * 0.5, 0, 1).astype(np.float32)
    elif direction == "radial":
        cy, cx = H / 2.0, W / 2.0
        yy = np.arange(H, dtype=np.float32)[:, np.newaxis] - cy
        xx = np.arange(W, dtype=np.float32)[np.newaxis, :] - cx
        dist = np.sqrt(xx * xx + yy * yy)
        max_dist = np.sqrt(cy * cy + cx * cx)
        t = np.clip(dist / max(max_dist, 1e-6), 0, 1).astype(np.float32)
    elif direction == "angular":
        cy, cx = H / 2.0, W / 2.0
        yy = np.arange(H, dtype=np.float32)[:, np.newaxis] - cy
        xx = np.arange(W, dtype=np.float32)[np.newaxis, :] - cx
        ang = np.arctan2(-yy, xx)  # 0 at right, CCW positive
        t = ((ang + np.pi) / (2.0 * np.pi)).astype(np.float32)
        t = np.clip(t, 0, 1)
    else:  # horizontal (default)
        t = np.linspace(0, 1, W, dtype=np.float32)[np.newaxis, :].repeat(H, axis=0)

    # Apply optional angle rotation for linear directions
    if angle_deg != 0 and direction not in ("radial", "angular"):
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        cy, cx = H / 2.0, W / 2.0
        yy = np.arange(H, dtype=np.float32)[:, np.newaxis] - cy
        xx = np.arange(W, dtype=np.float32)[np.newaxis, :] - cx
        rotated = xx * cos_a + yy * sin_a
        rmin, rmax = float(rotated.min()), float(rotated.max())
        span = max(rmax - rmin, 1e-6)
        t = np.clip((rotated - rmin) / span, 0, 1).astype(np.float32)

    # Interpolate each RGB channel using np.interp (vectorized)
    out = np.empty((H, W, 3), dtype=np.float32)
    t_flat = t.ravel()
    for ch in range(3):
        out[:, :, ch] = np.interp(t_flat, positions, colors[:, ch]).reshape(H, W)

    return np.clip(out, 0.0, 1.0)


# ───────────────────────────────────────────────────────────────────────────
# Fit-to-bbox helper — resize a full-canvas image (RGB paint or RGBA spec)
# so its entire content fits inside the mask's bounding box rather than being
# sampled positionally. Used when a user draws a small rectangle selection.
# ───────────────────────────────────────────────────────────────────────────
def _resize_to_mask_bbox(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Resize `img` so the full image content fits inside the bbox of `mask`.

    Pixels outside the bbox are preserved as-is from `img`. If the mask bbox
    spans essentially the whole canvas (>=95% in both dimensions), the original
    image is returned unchanged (no-op).

    Args:
        img: (H, W, C) array (RGB float32 or RGBA uint8).
        mask: (H, W) boolean or float mask where the zone is active.

    Returns:
        Same-shape array. Bbox area contains the full image resized to fit;
        rest is left untouched.
    """
    try:
        if img is None or mask is None or img.ndim < 2:
            return img
        mb = mask > 0.05 if mask.dtype != bool else mask
        if not mb.any():
            return img
        rows = np.any(mb, axis=1)
        cols = np.any(mb, axis=0)
        r_min, r_max = np.where(rows)[0][[0, -1]]
        c_min, c_max = np.where(cols)[0][[0, -1]]
        bh = int(r_max - r_min + 1)
        bw = int(c_max - c_min + 1)
        H, W = int(img.shape[0]), int(img.shape[1])
        if bh <= 1 or bw <= 1:
            return img
        # Skip if bbox already ~full canvas
        if bh >= int(H * 0.95) and bw >= int(W * 0.95):
            return img
        try:
            import cv2 as _cv2
            _interp = _cv2.INTER_LINEAR if img.dtype in (np.float32, np.float64) else _cv2.INTER_AREA
            resized = _cv2.resize(np.ascontiguousarray(img), (bw, bh), interpolation=_interp)
        except Exception:
            from PIL import Image as _PIL
            _u8 = img.astype(np.uint8) if img.dtype == np.uint8 else (np.clip(img, 0, 1) * 255).astype(np.uint8)
            _mode = 'RGBA' if _u8.ndim == 3 and _u8.shape[2] == 4 else ('RGB' if _u8.ndim == 3 else 'L')
            _im = _PIL.fromarray(_u8, _mode).resize((bw, bh), _PIL.LANCZOS)
            _arr = np.asarray(_im)
            if img.dtype in (np.float32, np.float64):
                resized = (_arr.astype(np.float32) / 255.0)
            else:
                resized = _arr.astype(img.dtype)
        out = img.copy()
        out[r_min:r_max + 1, c_min:c_max + 1] = resized
        return out
    except Exception as _fit_err:
        print(f"[compose] _resize_to_mask_bbox failed: {_fit_err}")
        return img


def _apply_base_color_override(paint, shape, hard_mask, seed, base_color_mode, base_color, base_color_source, base_color_strength, monolithic_registry, fit_to_bbox=False):
    """Apply base color override to paint. Always operates on CPU (numpy) arrays.
    CuPy inputs are converted at the top. Returns a numpy array.

    If ``fit_to_bbox`` is True and the hard_mask has a meaningful bbox (e.g. a
    small rectangle selection), the generated color source is RESIZED to fit
    inside the bbox rather than being sampled from its full-canvas position.
    This matches what the user expects when they draw a small rectangle and pick
    a gradient/special color — the whole gradient compresses into the rectangle.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
                    try:
                        _src_raw = mono_paint_fn(_mono_overlay_seed_paint(paint), actual_shape, hard_mask, seed + 4242, 1.0, 0.0)
                        if isinstance(_src_raw, dict):
                            # Some paint functions return dicts — extract the array
                            _src_raw = _src_raw.get('paint', _src_raw.get('result', paint))
                        if _src_raw is not None:
                            _src_np = _src_raw.get() if hasattr(_src_raw, 'get') and not isinstance(_src_raw, dict) else np.asarray(_src_raw)
                            src = _boost_overlay_mono_color(np.clip(_src_np[:, :, :3], 0.0, 1.0))
                    except Exception as _mono_paint_err:
                        print(f"[compose] WARNING: mono paint_fn for '{mono_id}' failed: {_mono_paint_err}")
                    _found = True
                if not _found:
                    # REVERSE FALLBACK: mono: ID is a base-registered finish (migrated to Specials)
                    try:
                        from engine.registry import BASE_REGISTRY as _BR
                        if mono_id in _BR:
                            _base_paint_fn = _BR[mono_id].get("paint_fn", paint_none)
                            if _base_paint_fn is not paint_none:
                                _src_raw = _base_paint_fn(_mono_overlay_seed_paint(paint), actual_shape, hard_mask, seed + 4242, 1.0, 0.0)
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
                            _src_raw = base_paint_fn(_mono_overlay_seed_paint(paint), actual_shape, hard_mask, seed + 4242, 1.0, 0.0)
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
        # 2026-04-22 ship-readiness Iter 5 defensive hardening:
        # accept `base_color` as either a hex-string ("#RRGGBB" or "#RGB")
        # OR an [R, G, B] float array (0-1). The live render payload
        # builder at paint-booth-3-canvas.js:5612 converts hex → RGB-array
        # before send, so painters don't hit this path with strings; but
        # export/fleet/PSD paths and direct API calls historically pass
        # the hex string straight through. Pre-hardening, a hex string
        # would crash at `float(clr[0])` → `float('#')` → ValueError.
        # Also: handle degenerate `len < 3` arrays and non-numeric
        # entries without crashing. A truly unparseable value falls
        # back to white (sentinel for "no override"), same as
        # baseColor being None.
        clr = None
        if isinstance(base_color, str):
            s = base_color.strip()
            if s.startswith("#"):
                hex_part = s[1:]
                if len(hex_part) == 3:
                    hex_part = "".join(c * 2 for c in hex_part)
                if len(hex_part) == 6:
                    try:
                        clr = [
                            int(hex_part[0:2], 16) / 255.0,
                            int(hex_part[2:4], 16) / 255.0,
                            int(hex_part[4:6], 16) / 255.0,
                        ]
                    except ValueError:
                        clr = None
        elif isinstance(base_color, (list, tuple, np.ndarray)):
            # 2026-04-22 Codex P2 fix: restrict the array path to sequence-
            # like types only. The previous `hasattr(__len__) and len >= 3`
            # check accepted mappings like {'r':1,'g':0,'b':0}, which then
            # crashed with KeyError: 0 at `clr[0]`. Dicts / Mappings now
            # fall through to the white-sentinel fallback below.
            if len(base_color) >= 3:
                clr = base_color
        if clr is None:
            clr = [1.0, 1.0, 1.0]
        try:
            cr, cg, cb = float(clr[0]), float(clr[1]), float(clr[2])
        except (ValueError, TypeError, KeyError, IndexError):
            cr, cg, cb = 1.0, 1.0, 1.0
        tint_rgb = np.array([cr, cg, cb], dtype=np.float32)[np.newaxis, np.newaxis, :]
        src = np.empty_like(np.clip(paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
        src[:, :, :] = np.clip(tint_rgb, 0.0, 1.0)
    elif mode == "gradient":
        # base_color is repurposed as gradient_config dict.
        # 2026-04-22 painter-reported gray-fill fix: require >=2 stops.
        # A single-stop "gradient" is mathematically uniform color.
        # If someone wants a uniform color they should use mode='solid'.
        # produces a uniform gray/tinted wash across the entire zone —
        # what the painter saw as "gray covers the paint preview." If
        # someone wants a uniform color they should use mode='solid'.
        # Zero-stop and any other malformed-stops case falls through to
        # the generate_custom_gradient try/except below and lands as a
        # no-op (src stays None → paint returned unchanged).
        _grad_stops = base_color.get("stops") if isinstance(base_color, dict) else None
        if isinstance(_grad_stops, (list, tuple)) and len(_grad_stops) >= 2:
            try:
                grad = generate_custom_gradient(actual_shape, base_color)
                src = np.clip(grad, 0.0, 1.0)
            except Exception as _ge:
                print(f"[compose] WARNING: gradient generation failed: {_ge}")

    if src is None:
        return paint

    # Everything is CPU here (paint + hard_mask + src)
    src = src.get() if hasattr(src, 'get') else (np.asarray(src) if not isinstance(src, np.ndarray) else src)

    # ── FIT-TO-BBOX ────────────────────────────────────────────────────────────
    # If the user drew a small selection rectangle (or any bounded mask), resize
    # the full-canvas source image INTO the mask bbox so the whole gradient/
    # pattern fits the selection rather than being cropped by it.
    if fit_to_bbox and hard_mask is not None:
        try:
            mask_bool = hard_mask > 0.05
            if mask_bool.any():
                rows = np.any(mask_bool, axis=1)
                cols = np.any(mask_bool, axis=0)
                r_min, r_max = np.where(rows)[0][[0, -1]]
                c_min, c_max = np.where(cols)[0][[0, -1]]
                bh = int(r_max - r_min + 1)
                bw = int(c_max - c_min + 1)
                H, W = int(paint.shape[0]), int(paint.shape[1])
                # Only resize if bbox is meaningfully smaller than full canvas
                if bh > 1 and bw > 1 and (bh < H * 0.95 or bw < W * 0.95):
                    try:
                        import cv2 as _cv2
                        resized = _cv2.resize(np.ascontiguousarray(src, dtype=np.float32),
                                              (bw, bh), interpolation=_cv2.INTER_LINEAR)
                    except Exception:
                        # Fallback: PIL resize if cv2 unavailable
                        from PIL import Image as _PIL
                        _src_u8 = (np.clip(src, 0, 1) * 255).astype(np.uint8)
                        _im = _PIL.fromarray(_src_u8, 'RGB').resize((bw, bh), _PIL.LANCZOS)
                        resized = np.asarray(_im, dtype=np.float32) / 255.0
                    fitted = np.zeros_like(src)
                    fitted[r_min:r_max + 1, c_min:c_max + 1, :] = resized
                    src = fitted
        except Exception as _fit_err:
            # Never break the render over a fit-zone failure
            print(f"[compose] fit-to-bbox failed: {_fit_err} — using full-canvas source")

    w = (hard_mask * strength)[:, :, np.newaxis]
    paint = paint.copy()
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - w) + src * w
    return paint


def _apply_spec_blend_mode(base_val: np.ndarray,
                           pattern_contrib: np.ndarray,
                           opacity: float,
                           mode: str = "normal") -> np.ndarray:
    """Apply a pattern contribution to a spec channel using a Photoshop-style blend mode.

    Args:
        base_val: Spec channel array in [0, 255] (the underlying spec channel).
        pattern_contrib: Pattern contribution centered around 0 (delta scale).
        opacity: Blend strength in [0, 1].
        mode: One of "normal", "multiply", "screen", "overlay", "hardlight",
            "softlight". Unknown modes fall back to "normal" (additive).

    Returns:
        Blended channel array (same dtype as base_val, clipped to [0, 255]).

    Blend formulas (all on normalized 0-1 values):
        - normal:    base + pattern * opacity
        - multiply:  base * (1 - opacity + opacity * 2 * p)        (darkens where p<0.5)
        - screen:    1 - (1-base)(1 - opacity*p)
        - overlay:   if base<0.5: 2*base*p; else: 1 - 2*(1-base)(1-p)
        - hardlight: same as overlay but threshold on p instead of base
        - softlight: gentler overlay variant (no harsh midtone break)
    """
    if mode == "normal" or mode not in ("multiply", "screen", "overlay", "hardlight", "softlight"):
        return base_val + pattern_contrib * opacity
    p_abs = xp.abs(pattern_contrib)
    p_max_val = float(xp.max(p_abs))
    p_max = p_max_val if p_max_val > 1e-8 else 1.0
    p_norm = pattern_contrib / p_max
    p_factor = xp.clip(p_norm * 0.5 + 0.5, 0, 1)
    b_norm = xp.clip(base_val / 255.0, 0, 1)
    if mode == "multiply":
        # Darkens where pattern is dark; opacity controls intensity
        blended_norm = b_norm * (1.0 - opacity + opacity * p_factor * 2.0)
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "screen":
        # Lightens; inverse of multiply
        screen_factor = p_factor * opacity
        blended_norm = 1.0 - (1.0 - b_norm) * (1.0 - screen_factor)
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "overlay":
        # Photoshop overlay: midtone-preserving contrast boost driven by base
        dark = 2.0 * b_norm * p_factor
        light = 1.0 - 2.0 * (1.0 - b_norm) * (1.0 - p_factor)
        overlay_result = xp.where(b_norm < 0.5, dark, light)
        blended_norm = b_norm * (1.0 - opacity) + overlay_result * opacity
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "hardlight":
        # Hard Light: like overlay but threshold drives off pattern (steeper)
        dark = 2.0 * b_norm * p_factor
        light = 1.0 - 2.0 * (1.0 - b_norm) * (1.0 - p_factor)
        hl_result = xp.where(p_factor < 0.5, dark, light)
        blended_norm = b_norm * (1.0 - opacity) + hl_result * opacity
        return xp.clip(blended_norm * 255.0, 0, 255)
    elif mode == "softlight":
        # Soft Light: gentler version, subtle spec shifts only
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
                   dither=True,
                   **kwargs):
    """Compose a base material + pattern texture into a final spec map.
    base_spec_blend_mode: how pattern spec contributions blend with base spec
        (normal/multiply/screen/overlay/hardlight/softlight).
    dither: when True (default), apply noise dithering before uint8 conversion to
        reduce 8-bit banding artifacts in gradients.
    When second_base/third_base/fourth_base/fifth_base start with "mono:", they are
    looked up in monolithic_registry (spec_fn, paint_fn) and the spec_fn is used as the overlay."""
    _t_compose = _time.time()
    _gpu_active = is_gpu()
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    from engine.core import SPEC_ROUGHNESS_MIN, SPEC_CLEARCOAT_MIN, SPEC_METALLIC_CHROME_THRESHOLD

    # --- Fit-to-bbox flag — when set, the final spec output is resized to fit
    # inside the zone mask bbox. Lets users draw a small rectangle and have the
    # entire spec pattern compress into that rectangle (matching user intent).
    _spec_fit_to_bbox = bool(kwargs.get("base_color_fit_zone", False))

    # --- Parameter validation and default coercion ---
    if pattern_sm is None:
        pattern_sm = sm
    scale = max(SCALE_MIN, min(SCALE_MAX, float(scale if scale is not None else DEFAULT_SCALE)))
    spec_mult = max(0.0, min(5.0, float(spec_mult if spec_mult is not None else DEFAULT_SPEC_MULT)))
    rotation = float(rotation if rotation is not None else DEFAULT_ROTATION)
    pattern_opacity = max(PATTERN_OPACITY_MIN, min(PATTERN_OPACITY_MAX,
                          float(pattern_opacity if pattern_opacity is not None else DEFAULT_OPACITY)))
    base_scale = max(SCALE_MIN, min(SCALE_MAX, float(base_scale if base_scale is not None else DEFAULT_SCALE)))
    base_strength = max(0.0, min(STRENGTH_MAX, float(base_strength if base_strength is not None else DEFAULT_STRENGTH)))
    base_spec_strength = max(0.0, min(STRENGTH_MAX, float(base_spec_strength if base_spec_strength is not None else DEFAULT_STRENGTH)))
    pattern_offset_x = max(0.0, min(1.0, float(pattern_offset_x if pattern_offset_x is not None else DEFAULT_OFFSET)))
    pattern_offset_y = max(0.0, min(1.0, float(pattern_offset_y if pattern_offset_y is not None else DEFAULT_OFFSET)))
    pattern_intensity = max(0.0, min(1.0, float(pattern_intensity if pattern_intensity is not None else DEFAULT_STRENGTH)))

    logger.debug("compose_finish: base='%s' pattern='%s' scale=%.2f opacity=%.2f",
                 base_id, pattern_id, scale, pattern_opacity)

    _pat_int_raw = max(0.0, min(1.0, float(pattern_intensity)))
    _pat_int = _pat_int_raw ** 0.5 if _pat_int_raw > 0 else 0.0  # perceptual curve matches paint
    pattern_sm_eff = pattern_sm * _pat_int  # sqrt curve: 5%->22%, 50%->71%, 100%->100%

    # Pattern strength map: per-pixel modulation of pattern_sm_eff
    _psm_raw = kwargs.get("pattern_strength_map")
    if _psm_raw is not None:
        try:
            _psm_arr = np.asarray(_psm_raw, dtype=np.float32)
            if _psm_arr.shape[0] != shape[0] or _psm_arr.shape[1] != shape[1]:
                _psm_arr = cv2.resize(_psm_arr, (shape[1], shape[0]),
                                      interpolation=cv2.INTER_LINEAR)
            pattern_sm_eff = pattern_sm_eff * _psm_arr
        except Exception as _psm_e:
            print(f"[compose] WARNING: pattern_strength_map failed: {_psm_e}")

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
        # Transfer pattern_sm_eff to GPU if it's a per-pixel array
        if isinstance(pattern_sm_eff, np.ndarray):
            pattern_sm_eff = to_gpu(pattern_sm_eff)

    if base_scale != 1.0 and base_scale > 0:
        MAX_BASE_DIM = 4096
        base_h = min(MAX_BASE_DIM, max(4, int(shape[0] / base_scale)))
        base_w = min(MAX_BASE_DIM, max(4, int(shape[1] / base_scale)))
        base_shape = (base_h, base_w)
    else:
        base_shape = shape

    _base_seed_offset = abs(hash(base_id)) % 10000
    _bss = max(0.0, min(2.0, float(base_spec_strength)))
    effective_base_CC = _scale_base_clearcoat_scalar(base_CC, _bss)
    if base.get("base_spec_fn"):
        spec_result = base["base_spec_fn"](base_shape, seed + _base_seed_offset, _sm_base, base_M, base_R)
        if len(spec_result) == 3:
            M_arr, R_arr, CC_arr = spec_result
        else:
            M_arr, R_arr = spec_result
            CC_arr = None
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

    if _bss < 0.999 or _bss > 1.001:
        M_arr, R_arr, CC_arr = _scale_base_spec_channels_toward_neutral(
            M_arr, R_arr, CC_arr, _bss
        )

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
        if effective_base_CC > 0:
            cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        else:
            cc_value = (1.0 - float(cc_quality)) * 90.0
        if CC_arr is not None:
            CC_arr = CC_arr - float(effective_base_CC) + cc_value
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
        elif effective_base_CC != base2_CC:
            CC_arr = float(effective_base_CC) * (1.0 - grad) + float(base2_CC) * grad

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
            sp_opacity_raw = float(sp_layer.get("opacity", 0.5))
            sp_opacity = sp_opacity_raw ** 0.5 if sp_opacity_raw > 0 else 0.0
            sp_blend = sp_layer.get("blend_mode", "normal")
            sp_params = sp_layer.get("params", {})
            # Which channels to affect.
            # 2026-04-21 HEENAN OVERNIGHT iter 2: previous behavior was a
            # blanket fallback to "MR" when the layer dict had no `channels`
            # key. That silently routed every spec pattern to M+R only,
            # ignoring the docstring intent of patterns that author
            # `Targets B=Clearcoat` (e.g. abstract_rothko_field — its
            # clearcoat-depth effect was NEVER applied). The JS UI sets
            # `channels` correctly via _buildSpecPatternLayer, so live
            # painter saves are unaffected; the bug bit direct API calls,
            # the first ~2s before the JS normalize timer fires, and any
            # server-side dispatch path that doesn't pre-populate channels.
            #
            # The fix: when (and only when) the layer dict has no truthy
            # `channels` value, parse the pattern function's docstring for
            # `Targets [RGB]=...` declarations and route accordingly. Falls
            # back to "MR" only when no authored intent is present, so
            # patterns without docstrings keep their pre-fix behavior.
            #
            # Strict back-compat: any layer that explicitly sets
            # channels="MR" / "C" / "MR" / etc. is preserved unchanged.
            _explicit_channels = sp_layer.get("channels")
            if _explicit_channels:
                sp_channels = _explicit_channels  # preserves all painter-explicit values
            else:
                sp_channels = _infer_spec_pattern_default_channels(sp_fn)
            # Position/transform params
            sp_offset_x = float(sp_layer.get("offset_x", 0.5))
            sp_offset_y = float(sp_layer.get("offset_y", 0.5))
            sp_scale = float(sp_layer.get("scale", 1.0))
            sp_rotation = float(sp_layer.get("rotation", 0))
            sp_box_size = int(sp_layer.get("box_size", 100))
            # Generate pattern (returns 0-1 float32 numpy array) -> stays CPU for transforms
            _sp_seed = seed + 5000 + hash(sp_name) % 10000
            # 2026-04-21 painter-report fix: spec pattern functions use `sm`
            # as a [0, 1] compression factor (0 = flatten to 0.5, 1 =
            # preserve amplitude). `_sm_base = sm * base_spec_strength`
            # can exceed 1 when a base has `base_spec_strength` > 1, which
            # pushed `_sm_scale` output outside [0, 1] and tripped the
            # `_validate_spec_output` assertion — the render then fell
            # back to a solid mid-gray. Cap the sm passed to spec patterns
            # so the contract stays intact even if a future base raises
            # strength.
            _sp_sm = min(1.0, float(_sm_base))
            if sp_scale < 1.0 and abs(sp_scale - 1.0) > 0.01:
                # Scale down: regenerate at higher resolution then downsample (no tile seams)
                sp_arr = _scale_down_spec_pattern(sp_fn, sp_scale, base_shape, _sp_seed, _sp_sm, sp_params)
            else:
                sp_arr = sp_fn(base_shape, _sp_seed, _sp_sm, **sp_params)
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
            sp_range = float(sp_layer.get("range", 60.0))  # spec units of variation (boosted from 40)
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

    final_CC = CC_arr if CC_arr is not None else effective_base_CC
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

                # Anti-alias pattern to reduce moire in iRacing renderer (#26)
                pv = _antialias_pattern(pv, sigma=0.5)

                M_pv = tex.get("M_pattern", pv)
                R_pv = tex.get("R_pattern", pv)
                CC_pv = tex.get("CC_pattern", None)

                # Anti-alias separate M/R/CC channels if they differ from pv
                if M_pv is not pv and M_pv is not None:
                    M_pv = _antialias_pattern(M_pv, sigma=0.5)
                if R_pv is not pv and R_pv is not None:
                    R_pv = _antialias_pattern(R_pv, sigma=0.5)
                if CC_pv is not None and CC_pv is not pv:
                    CC_pv = _antialias_pattern(CC_pv, sigma=0.5)

                # NOTE: M_pv/R_pv/CC_pv scaling is intentionally NOT re-applied here --
                # _scale_pattern_output above already handled it. The previous double-scale
                # block was removed in v6.1.2 (was a known bug).

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
                    elif effective_base_CC > 0:
                        CC_arr = xp.full(shape, float(effective_base_CC), dtype=xp.float32) + CC_pv * CC_range * _pat_scale

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
    # CONDITIONAL GGX FLOOR: R >= SPEC_ROUGHNESS_MIN for non-chrome, R >= 0 for chrome
    # CLEARCOAT FLOOR: CC >= SPEC_CLEARCOAT_MIN where mask is active (prevents invisible clearcoat)
    # This is the FINAL safety net — catches any upstream spec function that missed the floor.
    _outside_M = SPEC_DEFAULT_OUTSIDE_M   # Metallic outside zone mask
    _outside_R = SPEC_DEFAULT_OUTSIDE_R   # Roughness outside zone mask
    _dither_rng = np.random.RandomState(seed if seed else 42) if dither else None
    if _gpu_active:
        M_final = M_arr * mask + _outside_M * (1 - mask)
        R_final = R_arr * mask + _outside_R * (1 - mask)
        _M_cpu = to_cpu(xp.clip(M_final, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(xp.float32))
        _R_cpu = to_cpu(_ggx_safe_R(R_final, M_final, lib=xp).astype(xp.float32))
        if dither:
            spec[:,:,0] = _dither_channel(_M_cpu, _dither_rng)
            spec[:,:,1] = _dither_channel(_R_cpu, _dither_rng)
        else:
            spec[:,:,0] = np.clip(_M_cpu, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.uint8)
            spec[:,:,1] = np.clip(_R_cpu, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.uint8)
        _is_cc_arr = hasattr(final_CC, 'shape')  # works for both numpy and cupy arrays
        if _is_cc_arr:
            final_CC = to_gpu(final_CC)  # ensure on GPU
            # Enforce clearcoat floor: CC >= SPEC_CLEARCOAT_MIN inside mask
            _CC_floored = xp.where(mask > 0.5, xp.maximum(final_CC, float(SPEC_CLEARCOAT_MIN)), final_CC)
            _CC_cpu = to_cpu(xp.clip(_CC_floored * mask, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(xp.float32))
            spec[:,:,2] = _dither_channel(_CC_cpu, _dither_rng) if dither else np.clip(_CC_cpu, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.uint8)
        else:
            _mask_cpu_cc = to_cpu(mask)
            # Enforce clearcoat floor for scalar CC
            _cc_val = max(int(final_CC), SPEC_CLEARCOAT_MIN) if int(final_CC) > 0 else int(final_CC)
            spec[:,:,2] = np.where(_mask_cpu_cc > 0.5, _cc_val, 0).astype(np.uint8)
        spec[:,:,3] = SPEC_CHANNEL_MAX
    else:
        M_final = M_arr * mask + _outside_M * (1 - mask)
        R_final = R_arr * mask + _outside_R * (1 - mask)
        _M_f = np.clip(M_final, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.float32)
        _R_f = _ggx_safe_R(R_final, M_final).astype(np.float32)
        if dither:
            spec[:,:,0] = _dither_channel(_M_f, _dither_rng)
            spec[:,:,1] = _dither_channel(_R_f, _dither_rng)
        else:
            spec[:,:,0] = np.clip(_M_f, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.uint8)
            spec[:,:,1] = np.clip(_R_f, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.uint8)
        if isinstance(final_CC, np.ndarray):
            # Enforce clearcoat floor: CC >= SPEC_CLEARCOAT_MIN inside mask
            _CC_floored = np.where(mask > 0.5, np.maximum(final_CC, float(SPEC_CLEARCOAT_MIN)), final_CC)
            _CC_f = np.clip(_CC_floored * mask, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.float32)
            spec[:,:,2] = _dither_channel(_CC_f, _dither_rng) if dither else np.clip(_CC_f, SPEC_CHANNEL_MIN, SPEC_CHANNEL_MAX).astype(np.uint8)
        else:
            _cc_val = max(int(final_CC), SPEC_CLEARCOAT_MIN) if int(final_CC) > 0 else int(final_CC)
            spec[:,:,2] = np.where(mask > 0.5, _cc_val, 0).astype(np.uint8)
        spec[:,:,3] = SPEC_CHANNEL_MAX

    _t_spec_done = _time.time()
    logger.debug("compose_finish spec assembly: %.1fms (base='%s')", (_t_spec_done - _t_compose) * 1000, base_id)

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
        except Exception as e:
            logger.warning("compose_finish: second_base overlay failed for '%s': %s", second_base, e)

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
            spec, _tb_alpha = blend_dual_base_spec(
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
        except Exception as e:
            logger.warning("compose_finish: third_base overlay failed for '%s': %s", third_base, e)

    # 2026-04-23 HEENAN FAMILY 6h Alpha-hardening Iter 14 (Animal): the 4th and
    # 5th overlay base blocks below were MISSING from compose_finish entirely
    # (R13). The kwargs existed in the signature and painters could set them,
    # but compose_finish silently dropped them from the spec path — while
    # compose_paint_mod still honored them on the paint path. Result: painter
    # saw color change from 4th/5th overlay bases but no spec contribution,
    # asymmetric silent trust violation. Both blocks are ports of the 3rd
    # overlay block above with distinct seed offsets (+2999 / +3999 for base
    # generation; +9999 / +10999 for the blend_dual_base_spec alpha seed) and
    # ordinal-renamed locals (_fb_* for 4th, _fif_* for 5th). Pinned by
    # tests/test_regression_spec_strength_material_truth.py's parametric
    # ["third","fourth","fifth"] suite.
    if fourth_base and fourth_base_strength > 0.001:
        try:
            _fb_seed = seed + 2999
            _fb_seed_off = abs(hash(fourth_base)) % 10000
            spec_quaternary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(fourth_base).startswith("mono:"):
                _fb_stripped = fourth_base[5:]
                if monolithic_registry is not None and _fb_stripped in monolithic_registry:
                    _fb_spec_fn = monolithic_registry[_fb_stripped][0]
                    spec_quaternary = _fb_spec_fn(shape, mask, _fb_seed + _fb_seed_off, sm)
                elif _fb_stripped in BASE_REGISTRY:
                    fourth_base = _fb_stripped
            if fourth_base in BASE_REGISTRY:
                _fb_def = BASE_REGISTRY[fourth_base]
                _fb_M = float(_fb_def["M"])
                _fb_R = float(_fb_def["R"])
                _fb_CC = int(_fb_def.get("CC", 16))
                if _fb_def.get("base_spec_fn"):
                    _fb_result = _fb_def["base_spec_fn"](shape, _fb_seed + _fb_seed_off, sm, _fb_M, _fb_R)
                    _fb_M_arr = _fb_result[0]
                    _fb_R_arr = _fb_result[1]
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
                _fb_M_final = _fb_M_arr * mask + 5.0 * (1 - mask)
                _fb_R_final = _fb_R_arr * mask + 100.0 * (1 - mask)
                spec_quaternary[:,:,0] = np.clip(_fb_M_final, 0, 255).astype(np.uint8)
                spec_quaternary[:,:,1] = _ggx_safe_R(_fb_R_final, _fb_M_final).astype(np.uint8)
                spec_quaternary[:,:,2] = np.clip(_fb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_quaternary[:,:,3] = 255
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = None if fourth_base_pattern == '__none__' else (fourth_base_pattern if fourth_base_pattern else pattern_id)
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
                spec, spec_quaternary,
                strength=fourth_base_spec_strength,
                blend_mode=fourth_base_blend_mode,
                noise_scale=fourth_base_noise_scale,
                seed=seed + 9999,
                pattern_mask=_fb_pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=max(0.01, min(5.0, float(fourth_base_scale)))
            )
        except Exception as e:
            logger.warning("compose_finish: fourth_base overlay failed for '%s': %s", fourth_base, e)

    if fifth_base and fifth_base_strength > 0.001:
        try:
            _fif_seed = seed + 3999
            _fif_seed_off = abs(hash(fifth_base)) % 10000
            spec_quinary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
            if str(fifth_base).startswith("mono:"):
                _fif_stripped = fifth_base[5:]
                if monolithic_registry is not None and _fif_stripped in monolithic_registry:
                    _fif_spec_fn = monolithic_registry[_fif_stripped][0]
                    spec_quinary = _fif_spec_fn(shape, mask, _fif_seed + _fif_seed_off, sm)
                elif _fif_stripped in BASE_REGISTRY:
                    fifth_base = _fif_stripped
            if fifth_base in BASE_REGISTRY:
                _fif_def = BASE_REGISTRY[fifth_base]
                _fif_M = float(_fif_def["M"])
                _fif_R = float(_fif_def["R"])
                _fif_CC = int(_fif_def.get("CC", 16))
                if _fif_def.get("base_spec_fn"):
                    _fif_result = _fif_def["base_spec_fn"](shape, _fif_seed + _fif_seed_off, sm, _fif_M, _fif_R)
                    _fif_M_arr = _fif_result[0]
                    _fif_R_arr = _fif_result[1]
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
                _fif_M_final = _fif_M_arr * mask + 5.0 * (1 - mask)
                _fif_R_final = _fif_R_arr * mask + 100.0 * (1 - mask)
                spec_quinary[:,:,0] = np.clip(_fif_M_final, 0, 255).astype(np.uint8)
                spec_quinary[:,:,1] = _ggx_safe_R(_fif_R_final, _fif_M_final).astype(np.uint8)
                spec_quinary[:,:,2] = np.clip(_fif_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_quinary[:,:,3] = 255
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = None if fifth_base_pattern == '__none__' else (fifth_base_pattern if fifth_base_pattern else pattern_id)
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
                spec, spec_quinary,
                strength=fifth_base_spec_strength,
                blend_mode=fifth_base_blend_mode,
                noise_scale=fifth_base_noise_scale,
                seed=seed + 10999,
                pattern_mask=_fif_pattern_mask,
                zone_mask=mask,
                noise_fn=multi_scale_noise,
                overlay_scale=max(0.01, min(5.0, float(fifth_base_scale)))
            )
        except Exception as e:
            logger.warning("compose_finish: fifth_base overlay failed for '%s': %s", fifth_base, e)

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
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _ovsp_opacity_raw ** 0.5 if _ovsp_opacity_raw > 0 else 0.0
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
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
        except Exception as e:
            logger.warning("compose_finish: fourth_base overlay failed: %s", e)

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
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _ovsp_opacity_raw ** 0.5 if _ovsp_opacity_raw > 0 else 0.0
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
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
        except Exception as e:
            logger.warning("compose_finish: fifth_base overlay failed: %s", e)

    _apply_named_overlay_spec_stack("third_overlay_spec_pattern_stack", 8000)
    _apply_named_overlay_spec_stack("fourth_overlay_spec_pattern_stack", 9000)
    _apply_named_overlay_spec_stack("fifth_overlay_spec_pattern_stack", 10000)

    _ms = int((_time.time() - _t_compose) * 1000)
    if _gpu_active and COMPOSE_PROFILE:
        # Profile-only GPU log -- previously this printed unconditionally
        # which spammed production renders.
        print(f"[GPU] compose_finish: {_ms}ms (GPU)")
    # Iron rule enforcement (final safety net):
    #   R >= SPEC_ROUGHNESS_MIN (15) for non-chrome (M < 240)
    #   CC >= SPEC_CLEARCOAT_MIN (16) ALWAYS (matches legacy behavior; intentional
    #   even for matte finishes since iRacing's CC=0 path is unstable).
    # Inlined here (vs core.enforce_iron_rules which conditionally skips CC=0).
    _M = spec[:, :, 0]
    _non_chrome = _M < SPEC_METALLIC_CHROME_THRESHOLD
    np.maximum(spec[:, :, 1], SPEC_ROUGHNESS_MIN, out=spec[:, :, 1], where=_non_chrome)
    np.maximum(spec[:, :, 2], SPEC_CLEARCOAT_MIN, out=spec[:, :, 2])

    # Fit-to-bbox: resize the full-canvas spec into the mask's bbox so the
    # entire spec pattern compresses into a small rectangle selection.
    if _spec_fit_to_bbox and mask is not None:
        spec = _resize_to_mask_bbox(spec, mask)
        # Re-enforce iron rules after resize (interpolation can push values below floors)
        _M2 = spec[:, :, 0]; _nc2 = _M2 < SPEC_METALLIC_CHROME_THRESHOLD
        np.maximum(spec[:, :, 1], SPEC_ROUGHNESS_MIN, out=spec[:, :, 1], where=_nc2)
        np.maximum(spec[:, :, 2], SPEC_CLEARCOAT_MIN, out=spec[:, :, 2])

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
                           dither=True,
                           **kwargs):
    """Compose a base material + MULTIPLE stacked patterns into a final spec map.
    base_spec_blend_mode: master override for how pattern spec contributions blend with base spec.
    dither: when True (default), apply noise dithering before uint8 conversion to
        reduce 8-bit banding artifacts in gradients."""
    monolithic_registry = kwargs.pop("monolithic_registry", None)
    _gpu_active = is_gpu()
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    if pattern_sm is None:
        pattern_sm = sm
    _pat_int_raw = max(0.0, min(1.0, float(pattern_intensity)))
    _pat_int = _pat_int_raw ** 0.5 if _pat_int_raw > 0 else 0.0  # perceptual curve
    pattern_sm_eff = pattern_sm * _pat_int  # sqrt curve: 5%→22%, 50%→71%, 100%→100%

    # Pattern strength map: per-pixel modulation of pattern_sm_eff
    _psm_raw = kwargs.get("pattern_strength_map")
    if _psm_raw is not None:
        try:
            _psm_arr = np.asarray(_psm_raw, dtype=np.float32)
            if _psm_arr.shape[0] != shape[0] or _psm_arr.shape[1] != shape[1]:
                _psm_arr = cv2.resize(_psm_arr, (shape[1], shape[0]),
                                      interpolation=cv2.INTER_LINEAR)
            pattern_sm_eff = pattern_sm_eff * _psm_arr
        except Exception as _psm_e:
            print(f"[compose] WARNING: pattern_strength_map failed: {_psm_e}")

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
        # Transfer pattern_sm_eff to GPU if it's a per-pixel array
        if isinstance(pattern_sm_eff, np.ndarray):
            pattern_sm_eff = to_gpu(pattern_sm_eff)

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
    effective_base_CC = _scale_base_clearcoat_scalar(base_CC, _bss)
    if base.get("base_spec_fn"):
        spec_result = base["base_spec_fn"](base_shape, seed + _base_seed_offset, _sm_base, base_M, base_R)
        if len(spec_result) == 3:
            M_arr, R_arr, CC_arr = spec_result
        else:
            M_arr, R_arr = spec_result
            CC_arr = None
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

    if _bss < 0.999 or _bss > 1.001:
        M_arr, R_arr, CC_arr = _scale_base_spec_channels_toward_neutral(
            M_arr, R_arr, CC_arr, _bss
        )

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

    if cc_quality is not None and effective_base_CC > 0:
        cc_value = 16.0 + (1.0 - float(cc_quality)) * 239.0
        if CC_arr is not None:
            CC_arr = CC_arr - float(effective_base_CC) + cc_value
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
        elif effective_base_CC != base2_CC:
            CC_arr = float(effective_base_CC) * (1.0 - grad) + float(base2_CC) * grad

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
            sp_opacity_raw = float(sp_layer.get("opacity", 0.5))
            sp_opacity = sp_opacity_raw ** 0.5 if sp_opacity_raw > 0 else 0.0
            sp_blend = sp_layer.get("blend_mode", "normal")
            sp_params = sp_layer.get("params", {})
            # 2026-04-21 HEENAN OVERNIGHT iter 2: same docstring-inferred
            # default channel resolver as the compose_finish path. See
            # _infer_spec_pattern_default_channels at module top for
            # rationale; back-compat preserved when `channels` is set.
            _explicit_channels = sp_layer.get("channels")
            if _explicit_channels:
                sp_channels = _explicit_channels
            else:
                sp_channels = _infer_spec_pattern_default_channels(sp_fn)
            sp_offset_x = float(sp_layer.get("offset_x", 0.5))
            sp_offset_y = float(sp_layer.get("offset_y", 0.5))
            sp_scale = float(sp_layer.get("scale", 1.0))
            sp_rotation = float(sp_layer.get("rotation", 0))
            sp_box_size = int(sp_layer.get("box_size", 100))
            # Generate pattern (CPU) -> transform (CPU) -> transfer to GPU
            _sp_seed = seed + 5000 + hash(sp_name) % 10000
            # Cap sm at 1.0 to satisfy the spec-pattern compression contract.
            # See matching fix in compose_finish above.
            _sp_sm = min(1.0, float(_sm_base))
            if sp_scale < 1.0 and abs(sp_scale - 1.0) > 0.01:
                # Scale down: regenerate at higher resolution then downsample (no tile seams)
                sp_arr = _scale_down_spec_pattern(sp_fn, sp_scale, base_shape, _sp_seed, _sp_sm, sp_params)
            else:
                sp_arr = sp_fn(base_shape, _sp_seed, _sp_sm, **sp_params)
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
        final_CC = xp.full(shape, float(effective_base_CC), dtype=xp.float32)

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
        # Anti-alias pattern to reduce moire in iRacing renderer (#26)
        pv = _antialias_pattern(pv, sigma=0.5)
        M_pv = tex.get("M_pattern", pv)
        R_pv = tex.get("R_pattern", pv)
        CC_pv = tex.get("CC_pattern", None)
        # Anti-alias separate M/R/CC channels if they differ from pv
        if M_pv is not pv and M_pv is not None:
            M_pv = _antialias_pattern(M_pv, sigma=0.5)
        if R_pv is not pv and R_pv is not None:
            R_pv = _antialias_pattern(R_pv, sigma=0.5)
        if CC_pv is not None and CC_pv is not pv:
            CC_pv = _antialias_pattern(CC_pv, sigma=0.5)
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
    _dither_rng = np.random.RandomState(seed if seed else 42) if dither else None
    if _gpu_active:
        M_final = M_arr * mask + 5.0 * (1 - mask)
        R_final = R_arr * mask + 100.0 * (1 - mask)
        _M_cpu = to_cpu(xp.clip(M_final, 0, 255).astype(xp.float32))
        _R_cpu = to_cpu(_ggx_safe_R(R_final, M_final, lib=xp).astype(xp.float32))
        if dither:
            spec[:,:,0] = _dither_channel(_M_cpu, _dither_rng)
            spec[:,:,1] = _dither_channel(_R_cpu, _dither_rng)
        else:
            spec[:,:,0] = _M_cpu.astype(np.uint8)
            spec[:,:,1] = _R_cpu.astype(np.uint8)
        _is_cc_arr = hasattr(final_CC, 'shape')
        if _is_cc_arr:
            final_CC = to_gpu(final_CC)
            _CC_cpu = to_cpu(xp.clip(final_CC * mask, 0, 255).astype(xp.float32))
            spec[:,:,2] = _dither_channel(_CC_cpu, _dither_rng) if dither else _CC_cpu.astype(np.uint8)
        else:
            _mask_cpu_cc = to_cpu(mask)
            spec[:,:,2] = np.clip(final_CC * _mask_cpu_cc, 0, 255).astype(np.uint8)
        spec[:,:,3] = 255
    else:
        M_final = M_arr * mask + 5.0 * (1 - mask)
        R_final = R_arr * mask + 100.0 * (1 - mask)
        _M_f = np.clip(M_final, 0, 255).astype(np.float32)
        _R_f = _ggx_safe_R(R_final, M_final).astype(np.float32)
        if dither:
            spec[:,:,0] = _dither_channel(_M_f, _dither_rng)
            spec[:,:,1] = _dither_channel(_R_f, _dither_rng)
        else:
            spec[:,:,0] = _M_f.astype(np.uint8)
            spec[:,:,1] = _R_f.astype(np.uint8)
        _CC_f = np.clip(final_CC * mask, 0, 255).astype(np.float32)
        spec[:,:,2] = _dither_channel(_CC_f, _dither_rng) if dither else _CC_f.astype(np.uint8)
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
            spec, _sb_alpha = blend_dual_base_spec(
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
            # PAINT OVERLAY: apply overlay base's paint_fn and blend with same alpha
            if second_base_strength > 0.001 and second_base in BASE_REGISTRY and _sb_alpha is not None:
                _sb_paint_fn = BASE_REGISTRY[second_base].get("paint_fn", paint_none)
                if _sb_paint_fn is not paint_none:
                    try:
                        _sb_paint_result = _sb_paint_fn(paint.copy(), shape, hard_mask, _sb_seed + _sb_seed_off, 1.0, 0.0)
                        _sb_paint = np.asarray(_sb_paint_result) if not isinstance(_sb_paint_result, np.ndarray) else _sb_paint_result
                        if isinstance(_sb_paint, dict): _sb_paint = _sb_paint.get('paint', paint)
                    except Exception:
                        _sb_paint = paint
                else:
                    _sb_paint = paint.copy()
                # Apply second_base_color_source override (tint, solid color, etc.)
                _sb_cm = second_base_color_source or None
                if _sb_cm and _sb_cm.startswith("mono:"):
                    _sb_paint = _apply_base_color_override(_sb_paint, shape, hard_mask, seed + 999, "from_special", second_base_color, _sb_cm, 1.0, monolithic_registry)
                elif second_base_color is not None:
                    _sb_c = np.array(second_base_color[:3], dtype=np.float32).reshape(1, 1, 3)
                    _sb_paint = _sb_paint * (1.0 - hard_mask[:,:,np.newaxis]) + _sb_c * hard_mask[:,:,np.newaxis]
                # HSB adjustments for overlay
                if second_base_hue_shift or second_base_saturation or second_base_brightness:
                    _sb_paint = _apply_hsb_adjustments(_sb_paint, hard_mask, second_base_hue_shift, second_base_saturation, second_base_brightness)
                # Blend using the same alpha from spec blend, scaled by strength
                _sb_paint_alpha = np.clip(_sb_alpha * second_base_strength, 0, 1)
                _sb_a4 = _sb_paint_alpha[:, :, np.newaxis]
                paint = paint * (1.0 - _sb_a4) + _sb_paint * _sb_a4
        except Exception as _sb_err:
            print(f"[compose] WARNING: second base overlay failed: {_sb_err}")
            import traceback; traceback.print_exc()

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
            spec, _tb_alpha = blend_dual_base_spec(
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
            # Paint blend for 3rd overlay (stacked path)
            if third_base_strength > 0.001 and _tb_alpha is not None:
                _tb_paint_ov = paint.copy()
                if third_base_color is not None:
                    _tb_c = np.array(third_base_color[:3], dtype=np.float32).reshape(1,1,3)
                    _tb_paint_ov[:,:,:3] = _tb_paint_ov[:,:,:3] * (1.0 - hard_mask[:,:,np.newaxis]) + _tb_c * hard_mask[:,:,np.newaxis]
                _tb_pa = np.clip(_tb_alpha * third_base_strength, 0, 1)[:,:,np.newaxis]
                paint[:,:,:3] = paint[:,:,:3] * (1.0 - _tb_pa) + _tb_paint_ov[:,:,:3] * _tb_pa
        except Exception as _e3:
            print(f"[compose] WARNING: 3rd overlay failed: {_e3}")

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
            spec, _fb_alpha = blend_dual_base_spec(
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
            # Paint blend for 4th overlay (stacked path)
            if fourth_base_strength > 0.001 and _fb_alpha is not None:
                _fb_paint_ov = paint.copy()
                if fourth_base_color is not None:
                    _fb_c = np.array(fourth_base_color[:3], dtype=np.float32).reshape(1,1,3)
                    _fb_paint_ov[:,:,:3] = _fb_paint_ov[:,:,:3] * (1.0 - hard_mask[:,:,np.newaxis]) + _fb_c * hard_mask[:,:,np.newaxis]
                _fb_pa = np.clip(_fb_alpha * fourth_base_strength, 0, 1)[:,:,np.newaxis]
                paint[:,:,:3] = paint[:,:,:3] * (1.0 - _fb_pa) + _fb_paint_ov[:,:,:3] * _fb_pa
        except Exception as _e4:
            print(f"[compose] WARNING: 4th overlay failed: {_e4}")

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
            spec, _fif_alpha = blend_dual_base_spec(
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
            # Paint blend for 5th overlay (stacked path)
            if fifth_base_strength > 0.001 and _fif_alpha is not None:
                _fif_paint_ov = paint.copy()
                if fifth_base_color is not None:
                    _fif_c = np.array(fifth_base_color[:3], dtype=np.float32).reshape(1,1,3)
                    _fif_paint_ov[:,:,:3] = _fif_paint_ov[:,:,:3] * (1.0 - hard_mask[:,:,np.newaxis]) + _fif_c * hard_mask[:,:,np.newaxis]
                _fif_pa = np.clip(_fif_alpha * fifth_base_strength, 0, 1)[:,:,np.newaxis]
                paint[:,:,:3] = paint[:,:,:3] * (1.0 - _fif_pa) + _fif_paint_ov[:,:,:3] * _fif_pa
        except Exception as _e5:
            print(f"[compose] WARNING: 5th overlay failed: {_e5}")

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
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _ovsp_opacity_raw ** 0.5 if _ovsp_opacity_raw > 0 else 0.0
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
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
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _ovsp_opacity_raw ** 0.5 if _ovsp_opacity_raw > 0 else 0.0
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MR")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
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

    # Iron rule enforcement (final safety net): R>=15 for non-chrome (M<240), CC>=16 always.
    # In-place np.maximum with `where` avoids the extra astype / np.where round-trip.
    _non_chrome = spec[:, :, 0] < SPEC_METALLIC_CHROME_THRESHOLD
    np.maximum(spec[:, :, 1], SPEC_ROUGHNESS_MIN, out=spec[:, :, 1], where=_non_chrome)
    np.maximum(spec[:, :, 2], SPEC_CLEARCOAT_MIN, out=spec[:, :, 2])
    return spec


def compose_paint_mod(base_id, pattern_id, paint, shape, mask, seed, pm, bb, scale=1.0, rotation=0, blend_base=None, blend_dir="horizontal", blend_amount=0.5,
                      base_color_mode="source", base_color=None, base_color_source=None, base_color_strength=1.0, base_color_fit_zone=False,
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
    # blend_base debug removed — was [BLEND DEBUG] print
    if has_blend:
        base2 = BASE_REGISTRY[blend_base]
        base2_paint_fn = base2.get("paint_fn", paint_none)

    _BASE_PAINT_BOOST = 1.0 * max(0.0, min(2.0, float(base_strength)))
    _base_color_preseeded = _base_color_replaces_source_before_material(
        base_color_mode, base_color_strength, _BASE_PAINT_BOOST
    )
    if _base_color_preseeded:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, 1.0,
            monolithic_registry,
            fit_to_bbox=bool(base_color_fit_zone),
        )
    if base_paint_fn is not paint_none and _BASE_PAINT_BOOST > 0.001:
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

    if not _base_color_preseeded:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, base_color_strength,
            monolithic_registry,
            fit_to_bbox=bool(base_color_fit_zone),
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
            _direct_pattern_paint = (
                getattr(pat_paint_fn, "_spb_pattern_direct_paint", False)
                and abs(float(scale or 1.0) - 1.0) < 1e-6
                and abs(float(rotation or 0.0) % 360.0) < 1e-6
                and abs(float(pattern_offset_x or 0.5) - 0.5) < 1e-6
                and abs(float(pattern_offset_y or 0.5) - 0.5) < 1e-6
                and not pattern_flip_h
                and not pattern_flip_v
            )
            if _direct_pattern_paint:
                if _pi < 1.0 - 1e-6:
                    paint = paint_before_pattern * (1.0 - _pi) + paint * _pi
            elif tex_fn is not None:
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
            _sb_color_src = _overlay_mono_color_source(second_base, second_base_color_source)
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
            # Apply HSB AFTER blend so it affects the visible result (overlay may be grey/neutral)
            if abs(second_base_hue_shift) > 0.5 or abs(second_base_saturation) > 0.5 or abs(second_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_sb, 0, 1)
                paint = _apply_hsb_adjustments(paint, _hsb_mask, second_base_hue_shift, second_base_saturation, second_base_brightness)
                paint = np.asarray(paint)
            print(f"    [PAINT OVERLAY 2nd] blend_mode={_sb_bm_norm}, applied successfully")
        except Exception as _e:
            import traceback
            print(f"    [PAINT OVERLAY 2nd] ERROR: {_e}")
            traceback.print_exc()

    if (third_base or third_base_color_source) and third_base_strength > 0.001:
        print(f"    [PAINT OVERLAY 3rd] tb={third_base}, color_src={third_base_color_source}, str={third_base_strength}, blend={third_base_blend_mode}")
        try:
            _tb_color_src = _overlay_mono_color_source(third_base, third_base_color_source)
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
            if _tb_bm_norm == "pattern_screen":
                _screened_tb = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_tb_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb3) + _screened_tb * _alpha_tb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb3) + _paint_overlay_tb_cpu[:, :, :3] * _alpha_tb3
            # Apply HSB AFTER blend so it affects the visible result (overlay may be grey/neutral)
            if abs(third_base_hue_shift) > 0.5 or abs(third_base_saturation) > 0.5 or abs(third_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_tb, 0, 1)
                paint = _apply_hsb_adjustments(paint, _hsb_mask, third_base_hue_shift, third_base_saturation, third_base_brightness)
                paint = np.asarray(paint)
        except Exception as _e:
            import traceback
            print(f"    [PAINT OVERLAY 3rd] ERROR: {_e}")
            traceback.print_exc()

    if (fourth_base or fourth_base_color_source) and fourth_base_strength > 0.001:
        try:
            _fb_color_src = _overlay_mono_color_source(fourth_base, fourth_base_color_source)
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
            if _fb_bm_norm == "pattern_screen":
                _screened_fb = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fb_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb3) + _screened_fb * _alpha_fb3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb3) + _paint_overlay_fb_cpu[:, :, :3] * _alpha_fb3
            # Apply HSB AFTER blend so it affects the visible result (overlay may be grey/neutral)
            if abs(fourth_base_hue_shift) > 0.5 or abs(fourth_base_saturation) > 0.5 or abs(fourth_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_fb, 0, 1)
                paint = _apply_hsb_adjustments(paint, _hsb_mask, fourth_base_hue_shift, fourth_base_saturation, fourth_base_brightness)
                paint = np.asarray(paint)
        except Exception:
            pass

    if (fifth_base or fifth_base_color_source) and fifth_base_strength > 0.001:
        try:
            _fif_color_src = _overlay_mono_color_source(fifth_base, fifth_base_color_source)
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
            if _fif_bm_norm == "pattern_screen":
                _screened_fif = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fif_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif3) + _screened_fif * _alpha_fif3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif3) + _paint_overlay_fif_cpu[:, :, :3] * _alpha_fif3
            # Apply HSB AFTER blend so it affects the visible result (overlay may be grey/neutral)
            if abs(fifth_base_hue_shift) > 0.5 or abs(fifth_base_saturation) > 0.5 or abs(fifth_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_fif, 0, 1)
                paint = _apply_hsb_adjustments(paint, _hsb_mask, fifth_base_hue_shift, fifth_base_saturation, fifth_base_brightness)
                paint = np.asarray(paint)
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
    base_color_fit_zone = bool(kwargs.pop("base_color_fit_zone", False))
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
    _base_color_preseeded_stk = _base_color_replaces_source_before_material(
        base_color_mode, base_color_strength, _BASE_PAINT_BOOST
    )
    if _base_color_preseeded_stk:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, 1.0,
            monolithic_registry,
            fit_to_bbox=base_color_fit_zone,
        )
    if base_paint_fn is not paint_none and _BASE_PAINT_BOOST > 0.001:
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

    if not _base_color_preseeded_stk:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, base_color_strength,
            monolithic_registry,
            fit_to_bbox=base_color_fit_zone,
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
            _tex_ox_stk = float(layer.get("offset_x", pattern_offset_x))
            _tex_oy_stk = float(layer.get("offset_y", pattern_offset_y))
            _direct_pattern_paint = (
                getattr(pat_paint_fn, "_spb_pattern_direct_paint", False)
                and abs(float(scale or 1.0) - 1.0) < 1e-6
                and abs(float(rotation or 0.0) % 360.0) < 1e-6
                and abs(_tex_ox_stk - 0.5) < 1e-6
                and abs(_tex_oy_stk - 0.5) < 1e-6
            )
            if _direct_pattern_paint:
                if _pi_stk < 1.0 - 1e-6:
                    paint = paint_before_layer * (1.0 - _pi_stk) + paint * _pi_stk
            elif tex_fn is not None:
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
            _sb_color_src = _overlay_mono_color_source(second_base, second_base_color_source)
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
            # Apply HSB AFTER blend so it affects the visible combined result (not just the overlay which may be grey/neutral)
            if abs(second_base_hue_shift) > 0.5 or abs(second_base_saturation) > 0.5 or abs(second_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_sb_st, 0, 1)  # Only in overlay-affected pixels
                paint = _apply_hsb_adjustments(paint, _hsb_mask, second_base_hue_shift, second_base_saturation, second_base_brightness)
                paint = np.asarray(paint)
        except Exception:
            pass

    if (third_base or third_base_color_source) and third_base_strength > 0.001:
        try:
            _tb_color_src = _overlay_mono_color_source(third_base, third_base_color_source)
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
            if _tb_bm_norm == "pattern_screen":
                _screened_tb_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_tb_st_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb_st3) + _screened_tb_st * _alpha_tb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_tb_st3) + _paint_overlay_tb_st_cpu[:, :, :3] * _alpha_tb_st3
            # Apply HSB AFTER blend so it affects the visible combined result (not just the overlay which may be grey/neutral)
            if abs(third_base_hue_shift) > 0.5 or abs(third_base_saturation) > 0.5 or abs(third_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_tb_st, 0, 1)
                paint = _apply_hsb_adjustments(paint, _hsb_mask, third_base_hue_shift, third_base_saturation, third_base_brightness)
                paint = np.asarray(paint)
        except Exception:
            pass

    if (fourth_base or fourth_base_color_source) and fourth_base_strength > 0.001:
        try:
            _fb_color_src = _overlay_mono_color_source(fourth_base, fourth_base_color_source)
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
            if _fb_bm_norm == "pattern_screen":
                _screened_fb_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fb_st_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb_st3) + _screened_fb_st * _alpha_fb_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fb_st3) + _paint_overlay_fb_st_cpu[:, :, :3] * _alpha_fb_st3
            # Apply HSB AFTER blend so it affects the visible combined result (not just the overlay which may be grey/neutral)
            if abs(fourth_base_hue_shift) > 0.5 or abs(fourth_base_saturation) > 0.5 or abs(fourth_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_fb_st, 0, 1)
                paint = _apply_hsb_adjustments(paint, _hsb_mask, fourth_base_hue_shift, fourth_base_saturation, fourth_base_brightness)
                paint = np.asarray(paint)
        except Exception:
            pass

    if (fifth_base or fifth_base_color_source) and fifth_base_strength > 0.001:
        try:
            _fif_color_src = _overlay_mono_color_source(fifth_base, fifth_base_color_source)
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
            if _fif_bm_norm == "pattern_screen":
                _screened_fif_st = 1.0 - (1.0 - paint[:, :, :3]) * (1.0 - _paint_overlay_fif_st_cpu[:, :, :3])
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif_st3) + _screened_fif_st * _alpha_fif_st3
            else:
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - _alpha_fif_st3) + _paint_overlay_fif_st_cpu[:, :, :3] * _alpha_fif_st3
            # Apply HSB AFTER blend so it affects the visible combined result (not just the overlay which may be grey/neutral)
            if abs(fifth_base_hue_shift) > 0.5 or abs(fifth_base_saturation) > 0.5 or abs(fifth_base_brightness) > 0.5:
                _hsb_mask = hard_mask * np.clip(_alpha_fif_st, 0, 1)
                paint = _apply_hsb_adjustments(paint, _hsb_mask, fifth_base_hue_shift, fifth_base_saturation, fifth_base_brightness)
                paint = np.asarray(paint)
        except Exception:
            pass

    return paint


# ================================================================
# SPEC MAP DELTA COMPRESSION (#12)
# ================================================================
# Encodes the difference between two spec maps using RLE, enabling
# incremental preview updates that send only changed pixels instead
# of a full base64 PNG.  Typical preview tweaks change < 10% of
# pixels, so the delta + RLE payload is dramatically smaller.

import zlib as _zlib
import struct as _struct


def compress_spec_delta(spec_new, spec_old):
    """Compute and RLE-encode the delta between two spec maps.

    Both inputs should be uint8 numpy arrays of identical shape
    (H, W, C) where C is typically 4 (RGBA spec channels).

    Returns a bytes object containing:
        [4B height][4B width][4B channels][zlib-compressed RLE payload]

    The RLE payload encodes (delta_value, run_length) pairs per
    flattened byte so that long runs of zero-delta (unchanged pixels)
    collapse to a single pair.
    """
    spec_new = np.asarray(spec_new, dtype=np.uint8)
    spec_old = np.asarray(spec_old, dtype=np.uint8)
    if spec_new.shape != spec_old.shape:
        raise ValueError(
            f"Shape mismatch: new {spec_new.shape} vs old {spec_old.shape}"
        )

    # Delta as signed int16 then clamp to [-128, 127] stored as uint8
    # (offset by 128 so 0 delta == 128 in storage, enabling unsigned RLE)
    delta = spec_new.astype(np.int16) - spec_old.astype(np.int16)
    delta_u8 = np.clip(delta + 128, 0, 255).astype(np.uint8)

    flat = delta_u8.ravel()

    # RLE encode: list of (value, run_length) with max run 65535
    rle_parts = []
    n = len(flat)
    if n == 0:
        rle_payload = b""
    else:
        i = 0
        while i < n:
            val = int(flat[i])
            run = 1
            while i + run < n and flat[i + run] == val and run < 65535:
                run += 1
            # Pack: 1 byte value + 2 byte run (little-endian unsigned short)
            rle_parts.append(_struct.pack("<BH", val, run))
            i += run
        rle_payload = b"".join(rle_parts)

    h, w = spec_new.shape[:2]
    c = spec_new.shape[2] if spec_new.ndim == 3 else 1
    header = _struct.pack("<III", h, w, c)
    compressed = _zlib.compress(rle_payload, level=1)  # fast compression
    return header + compressed


def decompress_spec_delta(compressed, spec_old):
    """Reconstruct a spec map from a compressed delta and the previous map.

    compressed is the bytes object returned by compress_spec_delta.
    spec_old must be the same array that was used as *spec_old* when
    the delta was created.

    Returns a uint8 numpy array with the same shape as *spec_old*.
    """
    spec_old = np.asarray(spec_old, dtype=np.uint8)
    if len(compressed) < 12:
        raise ValueError("Compressed payload too short (missing header)")

    h, w, c = _struct.unpack_from("<III", compressed, 0)
    expected_size = h * w * c
    rle_payload = _zlib.decompress(compressed[12:])

    # Decode RLE
    flat = np.empty(expected_size, dtype=np.uint8)
    pos = 0
    offset = 0
    payload_len = len(rle_payload)
    while offset + 2 < payload_len:
        val, run = _struct.unpack_from("<BH", rle_payload, offset)
        offset += 3
        end = min(pos + run, expected_size)
        flat[pos:end] = val
        pos = end
        if pos >= expected_size:
            break

    # Any remaining bytes default to 128 (zero delta)
    if pos < expected_size:
        flat[pos:] = 128

    if c > 1:
        delta_u8 = flat.reshape((h, w, c))
    else:
        delta_u8 = flat.reshape((h, w))

    # Reverse offset: storage 128 == 0 delta
    delta = delta_u8.astype(np.int16) - 128
    result = np.clip(spec_old.astype(np.int16) + delta, 0, 255).astype(np.uint8)
    return result


# ================================================================
# FINISH MIXER - Blend 2-3 finishes at custom weight ratios
# ================================================================

def _resolve_finish_spec(finish_id, shape, mask, seed, sm, monolithic_registry=None):
    """Resolve a finish ID to (M_arr, R_arr, CC_arr) arrays.

    Checks BASE_REGISTRY first (uses base_spec_fn or static M/R/CC values),
    then MONOLITHIC_REGISTRY (uses spec_fn which returns a 4-channel spec).
    Returns float32 arrays of shape (H, W).
    """
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY as _MONO
    mono_reg = monolithic_registry if monolithic_registry is not None else _MONO
    h, w = shape[0], shape[1]

    if finish_id in BASE_REGISTRY:
        base = BASE_REGISTRY[finish_id]
        base_M = float(base["M"])
        base_R = float(base["R"])
        base_CC = float(base.get("CC", 16))
        _seed_off = abs(hash(finish_id)) % 10000
        if base.get("base_spec_fn"):
            result = base["base_spec_fn"]((h, w), seed + _seed_off, sm, base_M, base_R)
            M_arr = np.asarray(result[0], dtype=np.float32)
            R_arr = np.asarray(result[1], dtype=np.float32)
            CC_arr = np.asarray(result[2], dtype=np.float32) if len(result) > 2 else np.full((h, w), base_CC, dtype=np.float32)
        elif base.get("perlin") or "noise_scales" in base or base.get("brush_grain"):
            # For noise-based bases, generate simple noise-based spec
            noise = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + abs(hash(finish_id)) % 10000)
            M_arr = (base_M + noise * base.get("noise_M", 0) * sm).astype(np.float32)
            R_arr = (base_R + noise * base.get("noise_R", 0) * sm).astype(np.float32)
            CC_arr = np.full((h, w), base_CC, dtype=np.float32)
            if base.get("noise_CC", 0) > 0:
                CC_arr = (CC_arr + noise * base["noise_CC"] * sm).astype(np.float32)
        else:
            M_arr = np.full((h, w), base_M, dtype=np.float32)
            R_arr = np.full((h, w), base_R, dtype=np.float32)
            CC_arr = np.full((h, w), base_CC, dtype=np.float32)
        return M_arr, R_arr, CC_arr

    if finish_id in mono_reg:
        entry = mono_reg[finish_id]
        spec_fn = entry[0]
        spec_arr = spec_fn((h, w), mask, seed, sm)
        spec_arr = np.asarray(spec_arr)
        if spec_arr.ndim == 3 and spec_arr.shape[2] >= 3:
            M_arr = spec_arr[:, :, 0].astype(np.float32)
            R_arr = spec_arr[:, :, 1].astype(np.float32)
            CC_arr = spec_arr[:, :, 2].astype(np.float32)
        else:
            M_arr = np.full((h, w), 128.0, dtype=np.float32)
            R_arr = np.full((h, w), 80.0, dtype=np.float32)
            CC_arr = np.full((h, w), 16.0, dtype=np.float32)
        return M_arr, R_arr, CC_arr

    # Fallback: neutral spec
    return (np.full((h, w), 0.0, dtype=np.float32),
            np.full((h, w), 128.0, dtype=np.float32),
            np.full((h, w), 16.0, dtype=np.float32))


def _resolve_finish_paint_fn(finish_id, monolithic_registry=None):
    """Resolve a finish ID to its paint_fn callable.

    Returns paint_none if not found.
    """
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY as _MONO
    mono_reg = monolithic_registry if monolithic_registry is not None else _MONO

    if finish_id in BASE_REGISTRY:
        return BASE_REGISTRY[finish_id].get("paint_fn", paint_none)
    if finish_id in mono_reg:
        return mono_reg[finish_id][1]
    return paint_none


def mix_finishes(shape, mask, seed, sm, finish_ids, weights, monolithic_registry=None):
    """Blend 2-3 finishes into a single spec map by weighted average.

    Args:
        shape: (H, W) tuple.
        mask: (H, W) float32 mask array.
        seed: int random seed.
        sm: float smoothness multiplier.
        finish_ids: list of 2-3 finish ID strings (base or monolithic).
        weights: list of floats summing to 1.0, one per finish_id.
        monolithic_registry: optional override for MONOLITHIC_REGISTRY.

    Returns:
        numpy uint8 array (H, W, 4) spec map [M, R, CC, 0].
    """
    assert len(finish_ids) == len(weights), "finish_ids and weights must be same length"
    assert 2 <= len(finish_ids) <= 3, "Mix requires 2-3 finishes"
    # Normalize weights to sum to 1.0
    w_sum = sum(weights)
    if w_sum <= 0:
        weights = [1.0 / len(weights)] * len(weights)
    else:
        weights = [w / w_sum for w in weights]

    h, w = shape[0], shape[1]
    M_blend = np.zeros((h, w), dtype=np.float32)
    R_blend = np.zeros((h, w), dtype=np.float32)
    CC_blend = np.zeros((h, w), dtype=np.float32)

    for fid, wt in zip(finish_ids, weights):
        M_arr, R_arr, CC_arr = _resolve_finish_spec(fid, shape, mask, seed, sm, monolithic_registry)
        # Ensure correct shape
        if M_arr.shape != (h, w):
            M_arr = cv2.resize(M_arr, (w, h), interpolation=cv2.INTER_LINEAR)
        if R_arr.shape != (h, w):
            R_arr = cv2.resize(R_arr, (w, h), interpolation=cv2.INTER_LINEAR)
        if CC_arr.shape != (h, w):
            CC_arr = cv2.resize(CC_arr, (w, h), interpolation=cv2.INTER_LINEAR)
        M_blend += M_arr * wt
        R_blend += R_arr * wt
        CC_blend += CC_arr * wt

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(M_blend, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R_blend, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC_blend, 0, 255).astype(np.uint8)
    spec[:, :, 3] = 255  # Full spec mask - CRITICAL: without this, spec appears black
    # Iron rule enforcement (mix_finish_spec output): R>=15 non-chrome, CC>=16 always.
    _non_chrome_mix = spec[:, :, 0] < SPEC_METALLIC_CHROME_THRESHOLD
    np.maximum(spec[:, :, 1], SPEC_ROUGHNESS_MIN, out=spec[:, :, 1], where=_non_chrome_mix)
    np.maximum(spec[:, :, 2], SPEC_CLEARCOAT_MIN, out=spec[:, :, 2])
    return spec


def mix_finish_paint(paint, shape, mask, seed, pm, bb, finish_ids, weights, monolithic_registry=None):
    """Blend 2-3 finishes' paint modifications by weighted average.

    Each finish's paint_fn is called independently on a copy of the input paint,
    then the results are blended by weight.

    Args:
        paint: (H, W, 3) float32 paint array.
        shape: (H, W) tuple.
        mask: (H, W) float32 mask.
        seed: int random seed.
        pm: float paint modifier strength.
        bb: float brightness bias.
        finish_ids: list of 2-3 finish ID strings.
        weights: list of floats summing to 1.0.
        monolithic_registry: optional override for MONOLITHIC_REGISTRY.

    Returns:
        (H, W, 3) float32 blended paint array.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    assert len(finish_ids) == len(weights), "finish_ids and weights must be same length"
    w_sum = sum(weights)
    if w_sum <= 0:
        weights = [1.0 / len(weights)] * len(weights)
    else:
        weights = [w / w_sum for w in weights]

    paint = np.asarray(paint, dtype=np.float32)
    result = np.zeros_like(paint)
    h, w = shape[0], shape[1]

    # Ensure bb is proper 2D shape
    if np.isscalar(bb) or (hasattr(bb, 'ndim') and bb.ndim == 0):
        bb = np.full((h, w), float(bb), dtype=np.float32)
    bb = np.asarray(bb, dtype=np.float32)
    if bb.shape != (h, w):
        bb = np.broadcast_to(bb, (h, w)).copy()

    for fid, wt in zip(finish_ids, weights):
        paint_fn = _resolve_finish_paint_fn(fid, monolithic_registry)
        try:
            painted = paint_fn(paint.copy(), shape, mask, seed, pm, bb)
            painted = np.asarray(painted, dtype=np.float32)
            # Ensure 3-channel output
            if painted.ndim == 3 and painted.shape[2] > 3:
                painted = painted[:, :, :3]
            elif painted.ndim == 2:
                painted = np.stack([painted] * 3, axis=2)
            result += painted * wt
        except Exception as e:
            # Fallback: use unmodified paint for this component
            print(f"[mix_finish_paint] WARNING: paint_fn for '{fid}' failed: {e}")
            result += paint * wt

    return np.clip(result, 0, 1).astype(np.float32)


__all__ = [
    "compose_finish",
    "compose_finish_stacked",
    "compose_paint_mod",
    "compose_paint_mod_stacked",
    "_get_pattern_mask",
    "_apply_spec_blend_mode",
    "compress_spec_delta",
    "decompress_spec_delta",
    "mix_finishes",
    "mix_finish_paint",
]
