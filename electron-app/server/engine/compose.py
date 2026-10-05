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
from collections import OrderedDict
import numpy as np
from engine.spec_overlay_v2.contract import version as _spec_overlay_version
from engine.spec_overlay_v2.contract import opacity as _spec_overlay_opacity
from engine.spec_overlay_v2.contract import seed as _spec_overlay_seed
from engine.spec_overlay_v2.contract import active_layers as _spec_active_layers, active_options as _spec_active_options
from engine.spec_overlay_v2.compose import apply_stacks as _apply_spec_overlay_v2_stacks
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


_BASE_SPEC_FN_RESULT_CACHE = OrderedDict()
_BASE_SPEC_FN_RESULT_CACHE_BYTES = 0
_BASE_SPEC_FN_RESULT_CACHE_MAX_BYTES = 384 * 1024 * 1024
_BASE_SPEC_FN_RESULT_CACHE_MAX_ITEMS = 8
_SPEC_PATTERN_ARRAY_CACHE = OrderedDict()
_SPEC_PATTERN_ARRAY_CACHE_BYTES = 0
_SPEC_PATTERN_ARRAY_CACHE_MAX_BYTES = 256 * 1024 * 1024
# [2026-07-07] 12 -> 24: a 5-layer spec stack across the 3 preview stages needs
# 15 entries; 12 thrashed the LRU every full-quality pass. Byte cap still rules.
_SPEC_PATTERN_ARRAY_CACHE_MAX_ITEMS = 24


def _spec_cache_float_key(value, places=5):
    try:
        if isinstance(value, np.ndarray):
            return None
        return round(float(value), places)
    except Exception:
        return None


def _spec_pattern_cache_value_key(value):
    if isinstance(value, dict):
        return tuple(sorted((str(k), _spec_pattern_cache_value_key(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_spec_pattern_cache_value_key(v) for v in value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float):
        return round(float(value), 6)
    if isinstance(value, (str, int, bool, type(None))):
        return value
    return repr(value)


def _copy_base_spec_result(spec_result):
    copied = []
    for item in spec_result:
        if item is None:
            copied.append(None)
        else:
            copied.append(np.asarray(item, dtype=np.float32).copy())
    return tuple(copied)


def _invoke_base_spec_compat(base_spec_fn, shape, seed, sm, base_m, base_r):
    """Call ``base_spec_fn`` whether it is base-style ``(shape, seed, sm, M, R)`` or a
    monolithic-style ``(shape, mask, seed, sm)`` fn registered onto a base, and normalize
    the result to the base contract (an ``(M, R, CC)`` tuple of 2D arrays).

    2026-06-03 fix: the concurrent rebuild wired paradigm_v3's spec_nebula /
    spec_infinite_finish (both ``(shape, mask, seed, sm)`` returning a stacked ``(h,w,3)``
    array) onto the ``nebula`` / ``infinite_finish`` BASES, so the 5-arg base call raised
    "takes 4 positional arguments but 5 were given" everywhere bases render (app pipeline +
    picker bake). Try the base signature; on TypeError fall back to the monolithic one with
    a full-coverage mask, then unstack ``(h,w,3)`` -> ``(M, R, CC)`` so every downstream
    consumer (which expects the tuple) keeps working unchanged.
    """
    try:
        res = base_spec_fn(shape, seed, sm, base_m, base_r)
    except TypeError:
        mask = np.ones((int(shape[0]), int(shape[1])), dtype=np.float32)
        res = base_spec_fn(shape, mask, seed, sm)
    if isinstance(res, np.ndarray) and res.ndim == 3 and res.shape[2] >= 3:
        return (res[:, :, 0], res[:, :, 1], res[:, :, 2])
    return res


def _cached_base_spec_result(base_id, base_spec_fn, shape, seed, sm, base_m, base_r):
    """Cache pure base_spec_fn output across repeat app renders.

    SPB-PERF-2026-06-02 / owner live 24-32s render logs: base spec maps are
    deterministic for finish + shape + seed + strength, and they are often
    reused while the user changes unrelated zones. Store bounded float32 copies
    and hand callers fresh copies so downstream blending cannot mutate cache.
    """
    if not callable(base_spec_fn):
        return None
    try:
        h, w = int(shape[0]), int(shape[1])
    except Exception:
        return _invoke_base_spec_compat(base_spec_fn, shape, seed, sm, base_m, base_r)
    if h <= 0 or w <= 0:
        return _invoke_base_spec_compat(base_spec_fn, shape, seed, sm, base_m, base_r)
    sm_key = _spec_cache_float_key(sm)
    bm_key = _spec_cache_float_key(base_m, 4)
    br_key = _spec_cache_float_key(base_r, 4)
    if sm_key is None or bm_key is None or br_key is None:
        return _invoke_base_spec_compat(base_spec_fn, shape, seed, sm, base_m, base_r)
    fn_key = (
        getattr(base_spec_fn, "__module__", ""),
        getattr(base_spec_fn, "__qualname__", getattr(base_spec_fn, "__name__", "")),
    )
    cache_key = (str(base_id), fn_key, int(h), int(w), int(seed), sm_key, bm_key, br_key)
    global _BASE_SPEC_FN_RESULT_CACHE_BYTES
    cached = _BASE_SPEC_FN_RESULT_CACHE.get(cache_key)
    if cached is not None:
        _BASE_SPEC_FN_RESULT_CACHE.move_to_end(cache_key)
        return _copy_base_spec_result(cached[1])

    result = _invoke_base_spec_compat(base_spec_fn, shape, seed, sm, base_m, base_r)
    if not isinstance(result, (tuple, list)) or len(result) < 2:
        return result
    try:
        stored = _copy_base_spec_result(result)
        byte_count = int(sum(0 if arr is None else arr.nbytes for arr in stored))
    except Exception:
        return result
    if byte_count <= 0 or byte_count > _BASE_SPEC_FN_RESULT_CACHE_MAX_BYTES // 2:
        return _copy_base_spec_result(stored)
    _BASE_SPEC_FN_RESULT_CACHE[cache_key] = (byte_count, stored)
    _BASE_SPEC_FN_RESULT_CACHE.move_to_end(cache_key)
    _BASE_SPEC_FN_RESULT_CACHE_BYTES += byte_count
    while (
        len(_BASE_SPEC_FN_RESULT_CACHE) > _BASE_SPEC_FN_RESULT_CACHE_MAX_ITEMS
        or _BASE_SPEC_FN_RESULT_CACHE_BYTES > _BASE_SPEC_FN_RESULT_CACHE_MAX_BYTES
    ):
        _old_key, (_old_bytes, _old_value) = _BASE_SPEC_FN_RESULT_CACHE.popitem(last=False)
        _BASE_SPEC_FN_RESULT_CACHE_BYTES -= int(_old_bytes)
    return _copy_base_spec_result(stored)


def _infer_spec_pattern_default_channels(sp_fn) -> str:
    # 2026-05-23 owner directive: default to all 3 channels (MRC) when
    # nothing is declared, so the clearcoat channel stops being silently
    # dropped. Patterns with explicit Targets tags in their docstring still
    # get the channels they declare.
    if sp_fn is None:
        return "MRC"
    doc = getattr(sp_fn, "__doc__", "") or ""
    if not doc:
        return "MRC"
    found = set()
    for match in _SPEC_TARGETS_PATTERN.finditer(doc):
        found.add(match.group(1).upper())
    channels = ""
    if "R" in found:
        channels += "M"
    if "G" in found:
        channels += "R"
    if "B" in found:
        channels += "C"
    return channels or "MRC"


_SPEC_PATTERN_MISSING_WARNED: set = set()


def _get_spec_pattern_fn_or_skip(catalog: Dict[str, Callable], pattern_id: str, context: str):
    """Return the spec-pattern renderer for ``pattern_id``, or ``None`` if it is
    not in the catalog.

    SPB-2026-05-30 (owner: "live preview keeps breaking"): this used to raise
    ValueError on any unknown id, which turned a single stale/removed spec
    pattern in a SAVED zone into a hard 500 that killed the ENTIRE car preview.
    A loop agent removed ``spec_heat_scale`` from the catalog on 2026-05-26
    while the owner's project still referenced it -> every preview 500'd.

    A live painter tool must degrade gracefully: skip the missing layer, warn
    once per id, and render everything else. Callers MUST guard with
    ``if fn is None: continue``.
    """
    sp_fn = catalog.get(pattern_id)
    if sp_fn is None:
        if pattern_id not in _SPEC_PATTERN_MISSING_WARNED:
            _SPEC_PATTERN_MISSING_WARNED.add(pattern_id)
            logger.warning(
                "Skipping unknown spec pattern '%s' in %s (not in catalog; "
                "likely renamed/removed). Layer ignored; render continues.",
                pattern_id, context,
            )
    return sp_fn


# Backward-compat alias: the old name raised; it now skips. Kept so any stray
# reference (mirrors, partial syncs) cannot reintroduce the crash.
_get_spec_pattern_fn_or_raise = _get_spec_pattern_fn_or_skip

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

from engine.pattern_paint_placement import render_pattern_paint, composite_pattern_layer, composite_pattern_pixels
from engine.pattern_artwork import pattern_color_source, pattern_paint_source, load_pattern_artwork
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


def _copy_pattern_tex(tex):
    """Return a shallow copy of a pattern tex dict with copied ndarray payloads."""
    if not isinstance(tex, dict):
        return np.array(tex, copy=True) if isinstance(tex, np.ndarray) else tex
    out = {}
    for k, v in tex.items():
        out[k] = np.array(v, copy=True) if isinstance(v, np.ndarray) else v
    return out


def _overlay_inherits_primary_pattern_transform(
    overlay_pattern_setting: Optional[str],
    resolved_pattern_id: Optional[str],
    primary_pattern_id: Optional[str],
) -> bool:
    """True when overlay react-to should reuse the live primary pattern transform."""
    if not resolved_pattern_id or not primary_pattern_id:
        return False
    if str(resolved_pattern_id).strip().lower() == "none":
        return False
    if str(resolved_pattern_id) != str(primary_pattern_id):
        return False
    raw = overlay_pattern_setting
    if raw is None:
        return True
    s = str(raw).strip()
    if s.lower() in ("", "none", "__none__"):
        return True
    return s == str(primary_pattern_id)


def _resolve_overlay_pattern_transform(
    overlay_pattern_setting: Optional[str],
    resolved_pattern_id: Optional[str],
    primary_pattern_id: Optional[str],
    primary_scale: float,
    primary_rotation: float,
    primary_offset_x: float,
    primary_offset_y: float,
    overlay_scale: float,
    overlay_rotation: float,
    overlay_offset_x: float,
    overlay_offset_y: float,
):
    """Return the scale/rotation/offset tuple used for overlay pattern masks."""
    if _overlay_inherits_primary_pattern_transform(
        overlay_pattern_setting, resolved_pattern_id, primary_pattern_id
    ):
        return primary_scale, primary_rotation, primary_offset_x, primary_offset_y
    return overlay_scale, overlay_rotation, overlay_offset_x, overlay_offset_y


def _get_overlay_pattern_mask(
    overlay_pattern_setting: Optional[str],
    resolved_pattern_id: Optional[str],
    primary_pattern_id: Optional[str],
    primary_scale: float,
    primary_rotation: float,
    primary_offset_x: float,
    primary_offset_y: float,
    overlay_pattern_scale: float,
    overlay_pattern_rotation: float,
    overlay_pattern_offset_x: float,
    overlay_pattern_offset_y: float,
    shape: Tuple[int, int],
    mask: np.ndarray,
    seed: int,
    sm: float,
    pattern_opacity: float,
    pattern_strength: float,
    fit_zone: bool = False,
) -> Optional[np.ndarray]:
    """Build overlay react-to pattern mask, inheriting primary transform when configured."""
    if not resolved_pattern_id:
        return None
    pat_scale, pat_rot, pat_ox, pat_oy = _resolve_overlay_pattern_transform(
        overlay_pattern_setting,
        resolved_pattern_id,
        primary_pattern_id,
        primary_scale,
        primary_rotation,
        primary_offset_x,
        primary_offset_y,
        overlay_pattern_scale,
        overlay_pattern_rotation,
        overlay_pattern_offset_x,
        overlay_pattern_offset_y,
    )
    return _get_pattern_mask(
        resolved_pattern_id,
        shape,
        mask,
        seed,
        sm,
        scale=pat_scale,
        rotation=pat_rot,
        opacity=pattern_opacity,
        strength=pattern_strength,
        offset_x=pat_ox,
        offset_y=pat_oy,
        fit_zone=fit_zone,
    )


def _resolve_overlay_pattern_mask_id(
    overlay_pattern: Optional[str],
    primary_pattern_id: Optional[str],
    blend_mode: Optional[str],
    stacked_primary_id: Optional[str] = None,
) -> Optional[str]:
    """Pattern id used for 2nd–5th overlay *alpha* masks (``get_base_overlay_alpha`` / spec dual-base).

    Pattern-driven overlay modes use the overlay layer's explicit pattern when
    set. If the overlay react-pattern is left on the UI's "- Zone primary -"
    option, they inherit the zone's primary pattern. If no real primary pattern
    exists, they no-op instead of becoming a full-zone tint. **Tint** is
    different: without an explicit overlay pattern, return ``None`` so the
    overlay uses a uniform zone wash.

    ``stacked_primary_id``: first stacked pattern id (``compose_*_stacked``);
    retained for call-site compatibility; pattern-only overlay modes no longer
    borrow it as an implicit fallback.
    """
    if overlay_pattern is not None:
        s = str(overlay_pattern).strip()
        if s.lower() == "__none__":
            bm = _normalize_second_base_blend_mode(blend_mode)
            if bm == "tint":
                return None
            overlay_pattern = None
        elif s.lower().replace(" ", "_").replace("-", "_") in {
            "_none_",
            "none_(base_only)",
            "none_(independent)",
            "base_only",
        }:
            bm = _normalize_second_base_blend_mode(blend_mode)
            if bm == "tint":
                return None
            overlay_pattern = None
        elif s and s.lower() not in ("none", "__none__", ""):
            return overlay_pattern
    if overlay_pattern is not None:
        s = str(overlay_pattern).strip()
        if s and s.lower() not in ("none", "__none__", ""):
            return overlay_pattern
    bm = _normalize_second_base_blend_mode(blend_mode)
    if bm == "tint":
        return None
    fb = stacked_primary_id if stacked_primary_id is not None else primary_pattern_id
    if bm in {
        "pattern",
        "pattern_vivid",
        "pattern_edges",
        "pattern_peaks",
        "pattern_contour",
        "pattern_screen",
        "pattern_threshold",
    }:
        if fb and str(fb).strip().lower() != "none":
            return fb
        return None
    if fb and str(fb).strip().lower() != "none":
        return fb
    return None


def _resolve_pattern_registry_entry(pattern_id: Optional[str], registry: Optional[dict] = None) -> Optional[dict]:
    """Resolve a pattern entry across the modular and legacy registries.

    Some UI compatibility aliases are wired onto ``shokker_engine_v2`` during
    startup. Direct engine paths and audit tools should still see those aliases
    even when ``server_v5`` has not patched ``engine.registry`` yet.
    """
    if not pattern_id or str(pattern_id).strip().lower() in ("", "none", "__none__"):
        return None
    if registry is not None:
        entry = registry.get(pattern_id)
        if isinstance(entry, dict):
            return entry
    try:
        import shokker_engine_v2 as _legacy_engine
        entry = getattr(_legacy_engine, "PATTERN_REGISTRY", {}).get(pattern_id)
        if isinstance(entry, dict):
            return entry
    except Exception:
        pass
    return None


def _build_base_overlay_spec_for_weight_mix(base_id, shape, mask, seed, sm, base_registry, monolithic_registry=None, spec_scale=1.0, rotation=0.0, spec_rotation=0.0):
    """Build one overlay-base spec map without blending it into the primary.

    Base overlay sliders are mixed as a material-weight budget later. Keeping
    the generation step separate lets 2nd-5th overlays blend together instead
    of sequentially overwriting one another.
    """
    overlay_id = base_id
    spec_overlay = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    if not overlay_id:
        return None, overlay_id
    if str(overlay_id).startswith("mono:"):
        stripped = str(overlay_id)[5:]
        if monolithic_registry is not None and stripped in monolithic_registry:
            spec_fn = monolithic_registry[stripped][0]
            _mono_spec = spec_fn(shape, mask, seed, sm).astype(np.uint8)
            # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation parity with the primary base.
            _rot_total = (float(rotation) + float(spec_rotation)) % 360.0
            if _rot_total:
                for _c in range(3):
                    _mono_spec[:, :, _c] = np.clip(_rotate_single_array(
                        _mono_spec[:, :, _c].astype(np.float32), _rot_total, shape), 0, 255).astype(np.uint8)
            return _mono_spec, overlay_id
        if stripped in base_registry:
            overlay_id = stripped
    if overlay_id not in base_registry:
        return None, overlay_id
    base_def = base_registry[overlay_id]
    base_M = float(base_def["M"])
    base_R = float(base_def["R"])
    base_CC = int(base_def.get("CC", 16))
    if base_def.get("base_spec_fn"):
        result = _cached_base_spec_result(overlay_id, base_def["base_spec_fn"], shape, seed, sm, base_M, base_R)
        M_arr = result[0]
        R_arr = result[1]
        CC_arr = result[2] if len(result) > 2 else np.full(shape, float(base_CC))
    elif base_def.get("perlin"):
        noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed)
        M_arr = base_M + noise * base_def.get("noise_M", 0) * sm
        R_arr = base_R + noise * base_def.get("noise_R", 0) * sm
        CC_arr = np.full(shape, float(base_CC))
    else:
        M_arr = np.full(shape, base_M)
        R_arr = np.full(shape, base_R)
        CC_arr = np.full(shape, float(base_CC))
    # [SPB-OVERLAY-PARITY 2026-08-20] Spec Scale was honoured only by the legacy
    # per-tier blocks, which the weighted mixer suppresses - the slider was dead
    # on every live render. Same helper the primary base uses.
    if abs(float(spec_scale) - 1.0) > 0.01:
        M_arr, R_arr, CC_arr = _apply_base_scale_to_spec_channels(M_arr, R_arr, CC_arr, shape, float(spec_scale))
    # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation parity: <tier>_base_rotation
    # rotates the overlay material; <tier>_base_spec_rotation adds a spec-only
    # offset - the same split the primary base's Rotation / Spec Rotation use.
    _rot_total = (float(rotation) + float(spec_rotation)) % 360.0
    if _rot_total:
        M_arr = _rotate_single_array(np.asarray(M_arr, dtype=np.float32), _rot_total, shape)
        R_arr = _rotate_single_array(np.asarray(R_arr, dtype=np.float32), _rot_total, shape)
        CC_arr = _rotate_single_array(np.asarray(CC_arr, dtype=np.float32), _rot_total, shape)
    M_final = M_arr * mask + 5.0 * (1 - mask)
    R_final = R_arr * mask + 100.0 * (1 - mask)
    spec_overlay[:, :, 0] = np.clip(M_final, 0, 255).astype(np.uint8)
    spec_overlay[:, :, 1] = _ggx_safe_R(R_final, M_final).astype(np.uint8)
    spec_overlay[:, :, 2] = np.clip(CC_arr * mask, 0, 255).astype(np.uint8)
    spec_overlay[:, :, 3] = 255
    return spec_overlay, overlay_id


def _weighted_mix_base_overlay_specs(spec_primary, overlay_layers, shape, mask):
    """Mix 2nd-5th base overlay specs as one normalized material stack.

    Painter contract:
    - If overlay strengths total <= 100%, the base keeps the remainder.
    - If overlay strengths total > 100%, active overlays normalize against
      each other so they remain proportional instead of stacking in order.
    - Pattern-bound layers use their pattern-derived alpha; two layers bound
      to the same active pattern naturally blend together inside that mask.
    """
    active = []
    H, W = shape[:2]
    for layer in overlay_layers:
        spec_overlay = layer.get("spec")
        if spec_overlay is None or spec_overlay.size == 0:
            continue
        try:
            strength = max(0.0, min(1.0, float(layer.get("strength", 0.0))))
        except (TypeError, ValueError):
            strength = 0.0
        if strength <= 1e-6:
            continue
        feature_alpha = get_base_overlay_alpha(
            (H, W), 1.0, layer.get("blend_mode", "noise"),
            noise_scale=int(layer.get("noise_scale", 24) or 24),
            seed=int(layer.get("seed", 42) or 42),
            pattern_mask=layer.get("pattern_mask"),
            zone_mask=mask,
            noise_fn=multi_scale_noise,
            overlay_scale=max(0.01, min(5.0, float(layer.get("overlay_scale", 1.0) or 1.0))),
        )
        weight = np.clip(feature_alpha * strength, 0.0, 1.0).astype(np.float32)
        layer["_overlay_alpha"] = weight
        if float(weight.max()) <= 1e-6:
            continue
        active.append((spec_overlay.astype(np.float32), weight))
    if not active:
        return spec_primary

    primary = spec_primary.astype(np.float32)
    weight_sum = np.zeros((H, W), dtype=np.float32)
    overlay_accum = np.zeros_like(primary, dtype=np.float32)
    for overlay_spec, weight in active:
        w4 = weight[:, :, np.newaxis]
        overlay_accum += overlay_spec * w4
        weight_sum += weight

    safe_sum = np.maximum(weight_sum, 1e-6)
    under_budget = weight_sum <= 1.0
    base_weight = np.where(under_budget, 1.0 - weight_sum, 0.0).astype(np.float32)
    overlay_divisor = np.where(under_budget, 1.0, safe_sum).astype(np.float32)
    result = primary * base_weight[:, :, np.newaxis] + overlay_accum / overlay_divisor[:, :, np.newaxis]

    np.maximum(result[:, :, 2], float(SPEC_CLEARCOAT_MIN), out=result[:, :, 2])
    non_chrome = result[:, :, 0] < float(SPEC_METALLIC_CHROME_THRESHOLD)
    r_chan = result[:, :, 1]
    r_chan[non_chrome] = np.maximum(r_chan[non_chrome], float(SPEC_ROUGHNESS_MIN))
    return np.clip(result, 0, 255).astype(np.uint8)


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


# [2026-07-08] Canvas-res reference channel stats for the scale-down value
# correction — tiny entries ((mean, std) per channel), keyed WITHOUT scale so a
# whole slider drag shares one full-res generation per pattern + canvas res.
_SPEC_SCALE_REF_STATS_CACHE = OrderedDict()
_SPEC_SCALE_REF_STATS_MAX = 64


def _spec_scale_ref_stats(sp_fn, canvas_shape, seed_val, sm_val, sp_params):
    """Per-channel (mean, std) of the generator at CANVAS resolution, cached."""
    try:
        key = (
            getattr(sp_fn, "__module__", ""),
            getattr(sp_fn, "__qualname__", getattr(sp_fn, "__name__", "")),
            int(canvas_shape[0]), int(canvas_shape[1]),
            int(seed_val), _spec_cache_float_key(sm_val),
            _spec_pattern_cache_value_key(sp_params or {}),
        )
    except Exception:
        return None
    hit = _SPEC_SCALE_REF_STATS_CACHE.get(key)
    if hit is not None:
        _SPEC_SCALE_REF_STATS_CACHE.move_to_end(key)
        return hit
    try:
        ref = np.asarray(sp_fn(canvas_shape, seed_val, sm_val, **(sp_params or {})), dtype=np.float32)
        r3 = ref if ref.ndim == 3 else ref[:, :, np.newaxis]
        stats = tuple((float(r3[:, :, c].mean()), float(r3[:, :, c].std())) for c in range(r3.shape[2]))
    except Exception as e:
        logger.warning("_spec_scale_ref_stats: reference gen failed (%s)", e)
        return None
    _SPEC_SCALE_REF_STATS_CACHE[key] = stats
    while len(_SPEC_SCALE_REF_STATS_CACHE) > _SPEC_SCALE_REF_STATS_MAX:
        _SPEC_SCALE_REF_STATS_CACHE.popitem(last=False)
    return stats


def _scale_down_spec_pattern(sp_fn: Callable,
                             sp_scale: float,
                             canvas_shape: Union[Tuple[int, int], Tuple[int, int, int]],
                             seed_val: int,
                             sm_val: float,
                             sp_params: Dict[str, Any]) -> np.ndarray:
    """Generate a scaled-down spec pattern without huge intermediate canvases.

    [SPB 2026-07-07 owner perf: "spec pattern overlays destroy render times,
    ESPECIALLY scaling down to 0.25"] Measured: the top spec generators cost
    3-5s at 2048² and the old path ALWAYS generated at full canvas res, then
    stride-decimated (cost independent of scale, features aliased). New path:
    generate ONE TILE at (canvas × scale) resolution and np.tile it — cost
    drops ~1/scale² (0.25 → ~16x faster) and features render at native tile
    res (crisper than nearest-neighbor decimation). Seam behavior matches the
    old %-wrap gather (non-seamless patterns wrapped either way).
    Guard: tests/regression_pattern_perf_budget_test.py (tile-res contract).
    """
    h, w = int(canvas_shape[0]), int(canvas_shape[1])
    sp_scale = max(SCALE_MIN, min(DEFAULT_SCALE, float(sp_scale)))
    tile_h = max(64, min(h, int(round(h * sp_scale))))
    tile_w = max(64, min(w, int(round(w * sp_scale))))
    try:
        tile = np.asarray(sp_fn((tile_h, tile_w), seed_val, sm_val, **sp_params), dtype=np.float32)
        # Spec patterns return 2D fields OR (H, W, 3) per-channel M/R/CC stacks.
        if tile.ndim in (2, 3) and tile.shape[0] > 0 and tile.shape[1] > 0:
            if tile.shape[0] != tile_h or tile.shape[1] != tile_w:
                tile = cv2.resize(tile, (tile_w, tile_h), interpolation=cv2.INTER_LINEAR)
            # [SPB 2026-07-08 owner: "spec colors coming through are OFF, especially
            # Metallic"] Statistics-dependent generators self-normalize per call, so
            # a 512² tile carries DIFFERENT channel means than the 2048² generation
            # the old decimate path sampled (measured: up to 15/255 mean drift on
            # spec_laser_etched). Moment-match the tile to canvas-res reference
            # stats — computed ONCE per (pattern, canvas, seed, sm) and cached, so
            # only the first scale-down tick pays a full-res generation; every
            # later tick keeps the ~1/scale² tile speedup AND the correct values.
            # Guard: tests/regression_spec_scale_value_parity_test.py
            ref_stats = _spec_scale_ref_stats(sp_fn, canvas_shape, seed_val, sm_val, sp_params)
            if ref_stats is not None:
                t3 = tile if tile.ndim == 3 else tile[:, :, np.newaxis]
                for c in range(min(t3.shape[2], len(ref_stats))):
                    ref_mean, ref_std = ref_stats[c]
                    ch = t3[:, :, c]
                    t_mean = float(ch.mean())
                    t_std = float(ch.std())
                    if ref_std > 1e-4 and t_std > 1e-4:
                        t3[:, :, c] = (ch - t_mean) * (ref_std / t_std) + ref_mean
                    else:
                        t3[:, :, c] = ch + (ref_mean - t_mean)
                tile = np.clip(t3 if tile.ndim == 3 else t3[:, :, 0], 0.0, 1.0)
            th, tw = tile.shape[0], tile.shape[1]
            reps_y = -(-h // th)
            reps_x = -(-w // tw)
            reps = (reps_y, reps_x) if tile.ndim == 2 else (reps_y, reps_x, 1)
            return np.ascontiguousarray(np.tile(tile, reps)[:h, :w], dtype=np.float32)
        logger.warning("_scale_down_spec_pattern: tile gen returned shape %s, falling back", getattr(tile, 'shape', None))
    except Exception as e:
        logger.warning("_scale_down_spec_pattern: tile-res gen failed (%s), falling back to canvas-res", e)

    # Fallback: previous behavior — full-canvas generation + periodic stride gather.
    try:
        base_arr = sp_fn(canvas_shape, seed_val, sm_val, **sp_params)
    except Exception as e:
        raise RuntimeError(f"Scaled spec pattern renderer failed: {e}") from e

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
                      offset_y: float = 0.5,
                      fit_zone: bool = False) -> Optional[np.ndarray]:
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
    from engine.render import _load_image_pattern, _load_color_image_pattern
    if not pattern_id or pattern_id == "none":
        return None
    pattern = _resolve_pattern_registry_entry(pattern_id, PATTERN_REGISTRY)
    if pattern is None:
        return None
    image_path = pattern.get("image_path")
    if image_path:
        h, w = shape[0], shape[1]
        # [SPB image-pattern overlay alignment fix 2026-06-06, REVISED] Build the overlay
        # mask from the SAME loader the PRIMARY visible image path uses
        # (_load_color_image_pattern -> alpha), then offset the FULL pattern BEFORE masking
        # and honor fit_zone. This makes an image-based pattern (e.g. Art Deco) used as a
        # react-to overlay tile/place IDENTICALLY to the primary at ALL scales. The legacy
        # _load_image_pattern coverage diverged from the primary at fractional scale
        # (measured: 0.20 -> xcorr 0.80, visibly offset; _load_color alpha -> xcorr 1.0)
        # because the two loaders use different resize + coverage processing. Offset BEFORE
        # mask + fit_zone fixes the scale=1.0 case; matching the loader fixes ALL scales.
        _rgba = _load_color_image_pattern(image_path, shape, scale=scale, rotation=rotation)
        if _rgba is not None and getattr(_rgba, "ndim", 0) == 3 and _rgba.shape[2] >= 4:
            pv = np.asarray(_rgba[:, :, 3], dtype=np.float32).copy()
        else:
            pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if pv is None:
                return None
            pv = np.asarray(pv, dtype=np.float32).copy()
        _apply_pattern_offset(pv, shape, offset_x, offset_y)
        if fit_zone:
            pv = _fit_pattern_to_mask_bbox(pv, mask)
        out = np.clip(pv * mask * max(0.0, min(1.0, float(opacity))) * max(0.0, min(2.0, float(strength))), 0, 1).astype(np.float32)
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
            tex = _copy_pattern_tex(_pattern_tex_cache[_cache_key])
        else:
            tex = tex_fn(shape, _mask_cpu, seed, sm)
            if _pattern_cache_enabled:
                if len(_pattern_tex_cache) >= _PATTERN_CACHE_MAX:
                    _pattern_tex_cache.pop(next(iter(_pattern_tex_cache)))
                _pattern_tex_cache[_cache_key] = tex
            tex = _copy_pattern_tex(tex)
        if isinstance(tex, dict):
            pv = tex.get("pattern_val")
        else:
            pv = tex
        if pv is None:
            return None
        pv = np.asarray(pv, dtype=np.float32)
        if pv.ndim != 2:
            return None
        use_scale = max(SCALE_MIN, min(SCALE_MAX, float(scale)))
        rot_angle = float(rotation) % 360.0
        if abs(use_scale - 1.0) > 0.01:
            if use_scale < 1.0:
                # [SPB 2026-06-10 whole-car-tiling fix v2 — fast] tile the pure cached
                # pattern_val DOWN (motifs shrink + repeat) — no regenerate-at-4096. The
                # cached tex is the output-res pure pattern, so tiling it stays clean.
                pv = _tile_fractional(np.asarray(pv, dtype=np.float32), 1.0 / use_scale, h, w)
                if isinstance(tex, dict):
                    for _k in ("R_extra", "M_extra", "CC"):
                        if isinstance(tex.get(_k), np.ndarray):
                            tex[_k] = _tile_fractional(np.asarray(tex[_k], dtype=np.float32), 1.0 / use_scale, h, w)
            else:
                pv = _crop_center_array(pv, use_scale, h, w)
        if pv.shape[0] != h or pv.shape[1] != w:
            pv = _resize_array(pv, h, w)
        if rot_angle > 0.5:
            if isinstance(tex, dict):
                tex["pattern_val"] = pv
                tex = _rotate_pattern_tex(tex, rot_angle, shape)
                pv = tex["pattern_val"]
            else:
                pv = _rotate_single_array(pv, rot_angle, shape)
        pv = np.asarray(pv, dtype=np.float32).copy()
        _apply_pattern_offset(pv, shape, offset_x, offset_y)
        pv = _antialias_pattern(pv, sigma=0.5)
        pmin, pmax = float(pv.min()), float(pv.max())
        if pmax - pmin > 1e-8:
            pv = (pv - pmin) / (pmax - pmin)
        else:
            pv = np.zeros_like(pv)
        if getattr(tex_fn, "_spb_rebuilt_pattern", False):
            # SPB-4 rebuilt patterns carry fine dark detail by design. When the
            # same renderer is reused as a base-overlay pattern mask, the raw
            # luminance can be too sparse for an explicit overlay color to read.
            # Lift detail/edge energy only for the alpha mask; the paint renderer
            # keeps its original authored palette and density.
            try:
                gy, gx = np.gradient(pv.astype(np.float32, copy=False))
                edge = np.clip((np.abs(gx) + np.abs(gy)) * 4.0, 0.0, 1.0)
                pv = np.clip(pv * 0.78 + np.sqrt(np.clip(pv, 0.0, 1.0)) * 0.16 + edge * 0.20, 0.0, 1.0)
            except Exception:
                pv = np.clip(pv * 1.18, 0.0, 1.0)
        # Use CPU mask for final multiply (returns CPU array for downstream)
        out = np.clip(pv * _mask_cpu * max(0.0, min(1.0, float(opacity))) * max(0.0, min(2.0, float(strength))), 0, 1).astype(np.float32)
        return out
    except Exception:
        return None


def _harden_overlay_pattern_mask(pattern_mask: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Crispen overlay pattern masks without crushing scaled or low-contrast patterns.

    The old fixed ``(mask - 0.30) / 0.40`` curve made Harden fragile: a valid
    pattern could become almost empty after scale/rotation/zone masking. Use
    the live nonzero mask distribution instead so "Harden" still means "only in
    the pattern", but the pattern remains visible.
    """
    if pattern_mask is None:
        return None
    pm = np.nan_to_num(np.asarray(pattern_mask, dtype=np.float32), nan=0.0, posinf=1.0, neginf=0.0)
    pm = np.clip(pm, 0.0, 1.0)
    active = pm[pm > 1e-5]
    if active.size == 0:
        return pm
    p_low = float(np.percentile(active, 20))
    p_high = float(np.percentile(active, 92))
    if p_high - p_low > 1e-4:
        norm = np.clip((pm - p_low) / (p_high - p_low), 0.0, 1.0)
    else:
        max_v = float(active.max())
        norm = pm / max(max_v, 1e-4)
    return np.clip((norm - 0.18) / 0.22, 0.0, 1.0).astype(np.float32)


def _apply_texture_pattern_paint_modulation(
    paint: np.ndarray,
    pattern_id: Optional[str],
    shape: Tuple[int, int],
    hard_mask: np.ndarray,
    seed: int,
    scale: float,
    rotation: float,
    pattern_offset_x: float,
    pattern_offset_y: float,
    pattern_flip_h: bool,
    pattern_flip_v: bool,
    pattern_intensity: float,
    pm: float,
    spec_mult: float,
) -> np.ndarray:
    """Add restrained paint visibility for texture-backed patterns.

    This is deliberately much softer than the old catch-all visibility rescue.
    It only modulates the existing paint with the pattern's own texture mask,
    so authored paint functions keep their look and no-op texture patterns do
    not disappear.
    """
    pv = _get_pattern_mask(
        pattern_id, shape, hard_mask, seed, 1.0,
        scale=scale, rotation=rotation,
        opacity=1.0, strength=1.0,
        offset_x=pattern_offset_x, offset_y=pattern_offset_y,
    )
    if pv is None:
        return paint
    if pattern_flip_h:
        pv = np.fliplr(pv).copy()
    if pattern_flip_v:
        pv = np.flipud(pv).copy()
    pv = np.clip(np.asarray(pv, dtype=np.float32), 0.0, 1.0) * hard_mask
    active = pv[hard_mask > 0.05]
    if active.size and float(active.max() - active.min()) > 1e-5:
        lo = float(np.percentile(active, 4))
        hi = float(np.percentile(active, 96))
        if hi - lo > 1e-5:
            pv = np.clip((pv - lo) / (hi - lo), 0.0, 1.0) * hard_mask
    pv_3d = pv[:, :, np.newaxis]
    mask_3d = hard_mask[:, :, np.newaxis]
    contrast = np.clip(
        0.30 * max(0.0, float(pattern_intensity)) * max(0.0, float(pm)) * max(0.1, float(spec_mult)),
        0.0,
        0.36,
    )
    factor = 1.0 + (pv_3d - 0.5) * contrast
    modulated = np.clip(paint[:, :, :3] * factor, 0.0, 1.0)
    paint[:, :, :3] = modulated * mask_3d + paint[:, :, :3] * (1.0 - mask_3d)
    return paint


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


def _transform_base_color_source(src: np.ndarray,
                                 shape: Tuple[int, int],
                                 scale: float = 1.0,
                                 offset_x: float = 0.5,
                                 offset_y: float = 0.5,
                                 rotation: float = 0.0,
                                 flip_h: bool = False,
                                 flip_v: bool = False,
                                 clip01: bool = True) -> np.ndarray:
    """Apply base placement controls to a generated RGB color source.

    ``clip01=False`` skips the final [0,1] clamp so this can transform a SIGNED
    delta (e.g. a base-material delta that may be negative) without destroying it.
    """
    if src is None or src.size == 0:
        return src
    h, w = int(shape[0]), int(shape[1])
    out = np.asarray(src, dtype=np.float32)
    use_scale = max(SCALE_MIN, min(SCALE_MAX, float(scale if scale is not None else DEFAULT_SCALE)))
    if abs(use_scale - 1.0) > 0.01:
        if use_scale < 1.0:
            chans = [_tile_fractional(out[:, :, ch], 1.0 / use_scale, h, w)
                     for ch in range(min(3, out.shape[2]))]
            # [SPB-PERF 2026-08-06] copy=False: np.stack already returns a FRESH array and
            # _tile_fractional is float32 by contract, so this astype was a pure 50MB copy
            # at 2048². Skipping it is byte-identical; a non-float32 input still converts.
            out = np.stack(chans, axis=2).astype(np.float32, copy=False)
        else:
            out = _crop_center_array(out, use_scale, h, w).astype(np.float32, copy=False)
    if out.shape[0] != h or out.shape[1] != w:
        out = _resize_array(out, h, w).astype(np.float32, copy=False)
    rot = float(rotation if rotation is not None else DEFAULT_ROTATION) % 360.0
    if abs(rot) > 0.5:
        chans = [_rotate_single_array(out[:, :, ch], rot, (h, w))
                 for ch in range(min(3, out.shape[2]))]
        # [SPB-PERF 2026-08-06] copy=False — np.stack output is already a fresh float32
        # array (see the scale branch above). Byte-identical.
        out = np.stack(chans, axis=2).astype(np.float32, copy=False)
    if flip_h:
        out = np.fliplr(out).copy()
    if flip_v:
        out = np.flipud(out).copy()
    ox = max(0.0, min(1.0, float(offset_x if offset_x is not None else DEFAULT_OFFSET)))
    oy = max(0.0, min(1.0, float(offset_y if offset_y is not None else DEFAULT_OFFSET)))
    if abs(ox - 0.5) > 0.001 or abs(oy - 0.5) > 0.001:
        out = out.copy()
        for ch in range(min(3, out.shape[2])):
            _apply_pattern_offset(out[:, :, ch], (h, w), ox, oy)
    out3 = out[:, :, :3]
    return np.clip(out3, 0.0, 1.0) if clip01 else out3.astype(np.float32, copy=False)


def _base_placement_active(
    scale=1.0,
    offset_x=0.5,
    offset_y=0.5,
    rotation=0.0,
    flip_h=False,
    flip_v=False,
) -> bool:
    use_scale = max(SCALE_MIN, min(SCALE_MAX, float(scale if scale is not None else DEFAULT_SCALE)))
    ox = max(0.0, min(1.0, float(offset_x if offset_x is not None else DEFAULT_OFFSET)))
    oy = max(0.0, min(1.0, float(offset_y if offset_y is not None else DEFAULT_OFFSET)))
    rot = float(rotation if rotation is not None else DEFAULT_ROTATION) % 360.0
    return (
        abs(use_scale - 1.0) > 0.01
        or abs(ox - 0.5) > 0.001
        or abs(oy - 0.5) > 0.001
        or abs(rot) > 0.5
        or bool(flip_h)
        or bool(flip_v)
    )


def _apply_base_placement_to_paint(
    paint,
    shape,
    hard_mask,
    base_scale=1.0,
    base_offset_x=0.5,
    base_offset_y=0.5,
    base_rotation=0.0,
    base_flip_h=False,
    base_flip_v=False,
    background_paint=None,
):
    """Tile/shrink base paint like spec overlays when base_scale < 1 (SPB-2026-05-18)."""
    if not _base_placement_active(
        base_scale, base_offset_x, base_offset_y, base_rotation, base_flip_h, base_flip_v
    ):
        return paint
    paint = paint.get() if hasattr(paint, "get") else np.asarray(paint)
    if background_paint is not None:
        background_paint = (
            background_paint.get() if hasattr(background_paint, "get") else np.asarray(background_paint)
        )
    hard_mask = hard_mask.get() if hasattr(hard_mask, "get") else np.asarray(hard_mask)
    h, w = int(shape[0]), int(shape[1])
    rgb = np.clip(paint[:, :, :3], 0.0, 1.0).astype(np.float32, copy=False)
    _hm_f = np.asarray(hard_mask, dtype=np.float32)
    mask3 = (_hm_f[:, :, np.newaxis] > 0.001)
    # SPB 2026-06-17: the SOURCE for the tiled delta must come from STRONGLY in-zone
    # pixels only. A soft (gaussian-blurred) zone mask — produced by a COLOR selection
    # such as "the black areas" — has edge values in (0.001, 0.5) sitting right on the
    # decal / other-zone boundary; including those in the tiled source replicated their
    # foreign colors across the zone (the "mini-cars" report). Tile from strong pixels,
    # composite with the soft mask. Falls back to the soft set if the zone is all-soft.
    strong3 = (_hm_f[:, :, np.newaxis] >= 0.5)
    src3 = strong3 if bool(strong3.any()) else mask3
    if background_paint is not None:
        # SOURCE-SAFE + ZONE-CONFINED base placement.
        #
        # 2026-06-02 fix (delta, partial): scale/tile/rotate the base-MATERIAL delta
        # (current paint minus the pre-material background) instead of the composited
        # paint. The composite already holds the iRacing template decals / car number /
        # sponsor logos, and tiling the whole composite stamped miniature copies of the
        # ENTIRE car when base_scale < 1 (the recurring "mini-cars" regression).
        #
        # 2026-06-17 TRUE root-cause fix (zone-confine the delta source — the missing
        # half): the 2026-06-02 comment ASSUMED "the delta is ~0 over those decal pixels."
        # That only holds for pass-through bases (gloss). The owner's bases (Frost Lace /
        # Glacier Core / arctic_ice / crystal_clear / ...) GENERATE their own opaque color,
        # and compose_paint_mod renders them over a FULL-CANVAS (ones) mask, so the material
        # overwrites the decals AND every other zone. The delta is therefore large and
        # decal/other-zone-shaped EVERYWHERE — not just inside this zone. Tiling that
        # full-canvas delta replicated the whole car's content back into the zone (proven:
        # in-zone content changed by max 0.47 depending only on what was painted elsewhere).
        # The masking step at the END cannot undo it because the foreign content has already
        # been tiled INTO the zone region.
        #
        # CURE: zero the delta OUTSIDE the zone mask before tiling, so the tiled source
        # contains ONLY this zone's own material. base_scale<1 then produces repeats of the
        # zone's selected area only — never the rest of the car. "Tile the zone's FIELD,
        # not the canvas." Guard: tests/regression_base_scale_no_whole_canvas_tile_test.py
        # + _fractured_proof/test_zone_scale_tiling.py (realistic color-generating base).
        out = background_paint.astype(np.float32, copy=True)
        bg_rgb = np.clip(out[:, :, :3], 0.0, 1.0)
        # Confine the material delta to the zone's STRONGLY selected area BEFORE tiling.
        # src3 (>=0.5) drops both off-zone content AND the soft anti-aliased edge pixels
        # that overlap decals / other zones, so neither can be replicated into the zone.
        base_delta = ((rgb - bg_rgb) * src3).astype(np.float32)
        # PASS-THROUGH base (gloss / clear / tint): the material barely departs from the source,
        # so base_scale must be a NO-OP. Tiling a near-zero delta still shuffled sub-threshold
        # source residue (e.g. car-number markers) into other quadrants -> guard it out so the
        # source paint shows unchanged. Opaque bases have a large delta and are unaffected.
        if float(np.mean(np.abs(base_delta))) < 0.020:
            return paint
        transformed_delta = _transform_base_color_source(
            base_delta, (h, w), scale=base_scale,
            offset_x=base_offset_x, offset_y=base_offset_y, rotation=base_rotation,
            flip_h=bool(base_flip_h), flip_v=bool(base_flip_v), clip01=False,
        )
        out[:, :, :3] = np.where(mask3, np.clip(bg_rgb + transformed_delta, 0.0, 1.0), bg_rgb)
    else:
        # Defense-in-depth source-safe fallback (SPB whole-canvas tiling guard 2026-06-02):
        # a caller omitted background_paint. Historically this branch transformed the WHOLE
        # composited rgb, which — when base_scale < 1 — stamped a 2x2 grid of mini-cars
        # (the composite already holds the iRacing template decals / car number / sponsor
        # logos). PROVEN reproduction: re-rendering the real client composite through this
        # whole-rgb transform tiled the entire car (see tests + C:\temp\pat_scale2 before/after).
        # Without a true pre-material background we CANNOT separate base material from decals,
        # so there is no safe way to tile — any whole-rgb transform replicates the decals.
        # The two in-tree call sites always pass background_paint, so this is purely a safety
        # net: refuse to tile (return the composite unchanged) rather than risk mini-cars.
        logger.warning(
            "_apply_base_placement_to_paint: base_scale=%.3f placement active but "
            "background_paint is None — skipping placement to avoid whole-composite tiling. "
            "Pass background_paint (pre-material composite) to enable source-safe base scaling.",
            float(base_scale),
        )
        return paint
    return np.clip(out, 0.0, 1.0).astype(np.float32, copy=False)


def _base_spec_generation_shape(shape, base_scale: float):
    """Full-res + post tile when scale < 1; smaller internal res when scale > 1."""
    h, w = int(shape[0]), int(shape[1])
    if base_scale is None or abs(base_scale - 1.0) < 0.01 or base_scale <= 0:
        return (h, w), False
    if base_scale < 1.0:
        return (h, w), True
    max_dim = 4096
    base_h = min(max_dim, max(4, int(h / base_scale)))
    base_w = min(max_dim, max(4, int(w / base_scale)))
    return (base_h, base_w), False


def _apply_base_scale_to_spec_channels(M_arr, R_arr, CC_arr, shape, base_scale: float):
    """Match pattern/spec overlay tiling for sub-1.0 base scale."""
    h, w = int(shape[0]), int(shape[1])
    if base_scale is None or abs(base_scale - 1.0) < 0.01 or base_scale <= 0:
        return M_arr, R_arr, CC_arr
    if base_scale < 1.0:
        tiles = 1.0 / float(base_scale)
        M_arr = _tile_fractional(M_arr, tiles, h, w)
        R_arr = _tile_fractional(R_arr, tiles, h, w)
        if CC_arr is not None:
            CC_arr = _tile_fractional(CC_arr, tiles, h, w)
        return M_arr, R_arr, CC_arr
    if M_arr.shape[0] != h or M_arr.shape[1] != w:
        M_arr = _resize_array(M_arr, h, w)
        R_arr = _resize_array(R_arr, h, w)
        if CC_arr is not None:
            CC_arr = _resize_array(CC_arr, h, w)
    return M_arr, R_arr, CC_arr


# [gauntlet 2026-07-04, measured] Dither noise cache: every compose call created a
# fresh RandomState(seed) and drew up to 3 full-res uniform planes (float64 alloc +
# astype) per zone — 0.208s of the 0.393s warm compose_finish floor. The 3 planes are
# fully determined by (seed, shape) and the M/R/CC draw ORDER is fixed at every call
# site, so serving cached planes in sequence is BIT-IDENTICAL to the old draws
# (verified: np.array_equal on RandomState(seed).uniform x3 vs cache). ~3.6x faster
# per channel (72.6ms -> 20.0ms @2048).
_DITHER_NOISE_CACHE = OrderedDict()  # (seed, h, w) -> [plane0, plane1, plane2] float32


class _DitherPlanes:
    """Sequential provider of the 3 per-compose dither planes for (seed, shape)."""

    def __init__(self, seed):
        self.seed = int(seed)
        self.idx = 0

    def next_plane(self, shape):
        key = (self.seed, int(shape[0]), int(shape[1]))
        planes = _DITHER_NOISE_CACHE.get(key)
        if planes is None:
            rng = np.random.RandomState(self.seed)
            planes = [rng.uniform(-0.5, 0.5, shape).astype(np.float32) for _ in range(3)]
            _DITHER_NOISE_CACHE[key] = planes
            while len(_DITHER_NOISE_CACHE) > 3:
                _DITHER_NOISE_CACHE.popitem(last=False)
        else:
            _DITHER_NOISE_CACHE.move_to_end(key)
        plane = planes[min(self.idx, 2)]
        self.idx += 1
        return plane


def _dither_channel(arr: np.ndarray,
                    rng=None) -> np.ndarray:
    """Apply uniform-noise dither to a float array before uint8 conversion.

    Adds noise in [-0.5, 0.5] to break 8-bit banding artifacts in gradients.
    Vectorized numpy (no per-pixel loops).

    Args:
        arr: Source 2D float array; not mutated.
        rng: _DitherPlanes (cached fast path), RandomState (legacy), or None
             (defaults to seed=42 legacy draw).

    Returns:
        uint8 array of the same shape, clipped to [0, 255].
    """
    if arr is None or arr.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    # Single-allocation path: copy + in-place add of noise. Total temp memory =
    # 1 * shape (vs 2x for `arr + rng.uniform(...)`).
    out = np.array(arr, dtype=np.float32, copy=True)
    if isinstance(rng, _DitherPlanes):
        out += rng.next_plane(arr.shape)
    else:
        if rng is None:
            rng = np.random.RandomState(42)
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


def _cached_spec_pattern_array(sp_fn: Callable,
                               sp_name: str,
                               canvas_shape: Tuple[int, int],
                               seed_val: int,
                               sm_val: float,
                               sp_params: Dict[str, Any],
                               sp_scale: float,
                               sp_rotation: float,
                               sp_offset_x: float,
                               sp_offset_y: float,
                               sp_box_size: int) -> np.ndarray:
    """Render a transformed spec-pattern stack layer with bounded reuse.

    SPB-PERF-2026-06-02 / live full-render optimization: spec overlays such
    as `spec_retroreflective` are deterministic for pattern + shape + seed +
    transform. The same expensive 2048 overlay is often reused while the user
    edits unrelated zones or masks, so cache the transformed float32 array and
    hand callers a private copy.
    """
    h, w = int(canvas_shape[0]), int(canvas_shape[1])
    sm_key = _spec_cache_float_key(sm_val)
    if h <= 0 or w <= 0 or sm_key is None:
        return _render_spec_pattern_array_uncached(
            sp_fn, canvas_shape, seed_val, sm_val, sp_params,
            sp_scale, sp_rotation, sp_offset_x, sp_offset_y, sp_box_size,
        )
    fn_key = (
        getattr(sp_fn, "__module__", ""),
        getattr(sp_fn, "__qualname__", getattr(sp_fn, "__name__", "")),
        getattr(sp_fn, "_spb_source_fingerprint", ""),
    )
    cache_key = (
        str(sp_name),
        fn_key,
        h,
        w,
        int(seed_val),
        sm_key,
        _spec_cache_float_key(sp_scale, 4),
        _spec_cache_float_key(sp_rotation, 4),
        _spec_cache_float_key(sp_offset_x, 4),
        _spec_cache_float_key(sp_offset_y, 4),
        int(sp_box_size),
        _spec_pattern_cache_value_key(sp_params or {}),
    )
    global _SPEC_PATTERN_ARRAY_CACHE_BYTES
    cached = _SPEC_PATTERN_ARRAY_CACHE.get(cache_key)
    if cached is not None:
        _SPEC_PATTERN_ARRAY_CACHE.move_to_end(cache_key)
        return np.asarray(cached[1], dtype=np.float32).copy()

    arr = _render_spec_pattern_array_uncached(
        sp_fn, canvas_shape, seed_val, sm_val, sp_params,
        sp_scale, sp_rotation, sp_offset_x, sp_offset_y, sp_box_size,
    )
    arr = np.asarray(arr, dtype=np.float32)
    try:
        stored = arr.copy()
        byte_count = int(stored.nbytes)
        _SPEC_PATTERN_ARRAY_CACHE[cache_key] = (byte_count, stored)
        _SPEC_PATTERN_ARRAY_CACHE.move_to_end(cache_key)
        _SPEC_PATTERN_ARRAY_CACHE_BYTES += byte_count
        while (
            len(_SPEC_PATTERN_ARRAY_CACHE) > _SPEC_PATTERN_ARRAY_CACHE_MAX_ITEMS
            or _SPEC_PATTERN_ARRAY_CACHE_BYTES > _SPEC_PATTERN_ARRAY_CACHE_MAX_BYTES
        ):
            _, (old_bytes, _) = _SPEC_PATTERN_ARRAY_CACHE.popitem(last=False)
            _SPEC_PATTERN_ARRAY_CACHE_BYTES = max(0, _SPEC_PATTERN_ARRAY_CACHE_BYTES - int(old_bytes))
    except Exception:
        pass
    return arr.copy()


def _render_spec_pattern_array_uncached(sp_fn: Callable,
                                        canvas_shape: Tuple[int, int],
                                        seed_val: int,
                                        sm_val: float,
                                        sp_params: Dict[str, Any],
                                        sp_scale: float,
                                        sp_rotation: float,
                                        sp_offset_x: float,
                                        sp_offset_y: float,
                                        sp_box_size: int) -> np.ndarray:
    h, w = int(canvas_shape[0]), int(canvas_shape[1])
    if getattr(sp_fn, "_spb_overlay_version", 1) >= 2:
        from engine.spec_overlay_v2.contract import transform
        return transform(sp_fn, (h, w), seed_val, sm_val, sp_params, sp_scale,
                         sp_rotation, sp_offset_x, sp_offset_y, sp_box_size)
    sp_scale = float(sp_scale)
    if sp_scale < 1.0 and abs(sp_scale - 1.0) > 0.01:
        sp_arr = _scale_down_spec_pattern(sp_fn, sp_scale, (h, w), seed_val, sm_val, sp_params)
    else:
        sp_arr = sp_fn((h, w), seed_val, sm_val, **(sp_params or {}))
        if abs(sp_scale - 1.0) > 0.01:
            sp_arr = _crop_center_array(sp_arr, sp_scale, h, w)
    if abs(float(sp_rotation)) > 0.5:
        sp_arr = _rotate_single_array(sp_arr, float(sp_rotation), (h, w))
    if abs(float(sp_offset_x) - 0.5) > 0.01 or abs(float(sp_offset_y) - 0.5) > 0.01:
        _apply_pattern_offset(sp_arr, (h, w), float(sp_offset_x), float(sp_offset_y))
    if int(sp_box_size) < 100:
        sp_arr = _apply_spec_pattern_box_size(sp_arr, (h, w), int(sp_box_size), float(sp_offset_x), float(sp_offset_y))
    return np.asarray(sp_arr, dtype=np.float32)


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
    # SPB-2026-05-18: special/mono (e.g. Casino) overlay on the material after paint_fn —
    # preseed + metallic re-sample caused hall-of-mirrors tiling and broken coverage.
    if mode in ("special", "from_special", "mono"):
        return False
    # SPB 2026-06-29 FIX (owner: base color "only works From special"; solid/gradient
    # vanished). The rebuilt OPAQUE bases (Candy&Pearl/Carbon/Ceramic/OPTIC LAB/FLAMES…)
    # paint OVER the preseeded color substrate, so a full-strength solid/gradient base
    # color disappeared entirely. Route solid/gradient through the SAME post-material
    # override that 'special' already uses (owner-confirmed correct): the color is applied
    # AFTER the material renders, so the chosen color shows while the base's SPEC
    # (metalness/roughness/clearcoat) is preserved — exactly "Labradorite spec + solid green".
    # (color_strength/material_strength kept above for clarity / future opacity-probe path.)
    return False


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
    if src_l == "overlay":
        return str(base_id) if base_id and str(base_id).startswith("mono:") else None
    if src and ":" not in src:
        try:
            return None if src in BASE_REGISTRY else "mono:" + src
        except Exception:
            return "mono:" + src
    if base_id and str(base_id).startswith("mono:") and src_l in ("", "overlay"):
        return str(base_id)
    return None


def _overlay_should_apply_base_paint_fn(color_source) -> bool:
    """Return True when overlay paint should use the selected base's paint_fn.

    Solid / from-base / from-special colors are explicit user paint colors. The
    selected overlay base still contributes its spec/material, but its paint_fn
    must not recolor the explicit swatch. "Same as overlay" is the case where
    the base renderer owns the visible paint.
    """
    src_l = str(color_source or "").strip().lower()
    return src_l in ("overlay", "same_as_overlay", "same-as-overlay")


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


def _fit_pattern_to_mask_bbox(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fit a pattern source into the active mask bbox while preserving dtype/shape."""
    fitted = _resize_to_mask_bbox(img, mask)
    if fitted is img:
        return fitted
    try:
        return np.asarray(fitted, dtype=getattr(img, "dtype", None))
    except Exception:
        return fitted


def _fit_paint_source_to_mask_bbox(paint_src: np.ndarray, base_paint: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fit a full-canvas paint source into the active mask bbox, then apply it only inside the mask."""
    fitted = _fit_pattern_to_mask_bbox(paint_src, mask)
    if fitted is paint_src:
        return paint_src
    out = np.asarray(base_paint).copy()
    src = np.asarray(fitted)
    if src.ndim == 2:
        src = np.repeat(src[:, :, np.newaxis], 3, axis=2)
    if out.ndim == 2:
        out = np.repeat(out[:, :, np.newaxis], 3, axis=2)
    mask3 = np.clip(np.asarray(mask, dtype=np.float32), 0.0, 1.0)[:, :, np.newaxis]
    out[:, :, :3] = out[:, :, :3] * (1.0 - mask3) + src[:, :, :3] * mask3
    return np.ascontiguousarray(out, dtype=getattr(base_paint, "dtype", np.float32))


def _invoke_mono_paint_fn_for_color_source(
    mono_paint_fn,
    paint,
    actual_shape,
    hard_mask,
    seed,
    *,
    base_scale=1.0,
    base_offset_x=0.5,
    base_offset_y=0.5,
    base_rotation=0.0,
    base_flip_h=False,
    base_flip_v=False,
):
    """Sample a monolithic paint_fn full-canvas with placement on the texture, not the composite."""
    from engine.paint_v2.placement_context import clear_zone_placement, set_zone_placement

    h, w = int(actual_shape[0]), int(actual_shape[1])
    full_mask = np.ones((h, w), dtype=np.float32)
    set_zone_placement(
        scale=base_scale,
        offset_x=base_offset_x,
        offset_y=base_offset_y,
        rotation=base_rotation,
        flip_h=bool(base_flip_h),
        flip_v=bool(base_flip_v),
    )
    try:
        _src_raw = mono_paint_fn(_mono_overlay_seed_paint(paint), actual_shape, full_mask, seed + 4242, 1.0, 0.0)
        # SPB 2026-06-09 owner "Base Scale does nothing" fix: capture BEFORE the
        # finally-clear wipes the flag. Downstream checks after clear always saw
        # False, so consuming families (cultural placement inside paint_fn) got
        # the outer transform a SECOND time while non-consuming monolithics
        # relied on a check that could never skip for them. Placement is now
        # guaranteed HERE: consumed inside the paint_fn or applied as a fallback
        # transform below — callers must not transform this source again.
        from engine.paint_v2.placement_context import zone_placement_was_applied as _zpwa
        _placement_applied = _zpwa()
    finally:
        clear_zone_placement()
    if isinstance(_src_raw, dict):
        _src_raw = _src_raw.get("paint", _src_raw.get("result", paint))
    if _src_raw is None:
        return None
    _src_np = _src_raw.get() if hasattr(_src_raw, "get") and not isinstance(_src_raw, dict) else np.asarray(_src_raw)
    src = _boost_overlay_mono_color(np.clip(_src_np[:, :, :3], 0.0, 1.0))
    if not _placement_applied:
        src = _transform_base_color_source(
            src,
            actual_shape,
            scale=base_scale,
            offset_x=base_offset_x,
            offset_y=base_offset_y,
            rotation=base_rotation,
            flip_h=bool(base_flip_h),
            flip_v=bool(base_flip_v),
        )
    return np.clip(src, 0.0, 1.0)


def _invoke_base_paint_fn_for_color_source(
    base_paint_fn,
    paint,
    actual_shape,
    seed,
    *,
    base_scale=1.0,
    base_offset_x=0.5,
    base_offset_y=0.5,
    base_rotation=0.0,
    base_flip_h=False,
    base_flip_v=False,
):
    """Sample a base color source as a full material plate before zone masking.

    SPB-105 owner report, 2026-05-20: COLORSHOXX Arctic Mirage used as
    "From special" at Base Scale < 1.0 dragged neutral/template blocks into
    the paint map. The source must be generated full-canvas first, like
    Grunge & Fun, then masked into the zone by the caller.
    """
    from engine.paint_v2.placement_context import clear_zone_placement, set_zone_placement, zone_placement_was_applied

    h, w = int(actual_shape[0]), int(actual_shape[1])
    full_mask = np.ones((h, w), dtype=np.float32)
    set_zone_placement(
        scale=base_scale,
        offset_x=base_offset_x,
        offset_y=base_offset_y,
        rotation=base_rotation,
        flip_h=bool(base_flip_h),
        flip_v=bool(base_flip_v),
    )
    try:
        _src_raw = base_paint_fn(_mono_overlay_seed_paint(paint), actual_shape, full_mask, seed + 4242, 1.0, 0.0)
        _placement_applied = zone_placement_was_applied()
    finally:
        clear_zone_placement()
    if _src_raw is None:
        return None
    _src_np = _src_raw.get() if hasattr(_src_raw, 'get') else np.asarray(_src_raw)
    src = np.clip(_src_np[:, :, :3], 0.0, 1.0)
    if not _placement_applied:
        src = _transform_base_color_source(
            src,
            actual_shape,
            scale=base_scale,
            offset_x=base_offset_x,
            offset_y=base_offset_y,
            rotation=base_rotation,
            flip_h=bool(base_flip_h),
            flip_v=bool(base_flip_v),
        )
    return np.clip(src, 0.0, 1.0)


def _color_lab_blend(paint, src, hard_mask, depth, flip_deg, underglow, strength=1.0):
    """[SPB COLOR LAB 2026-08-27 — owner: replace Color Strength/Scale/Rotation with a
    "revolutionary" trio]. Three dials that behave like a real paint booth instead of a
    crossfade-to-gray (the old Strength) and two no-ops-on-solids (old Scale/Rotation):

      DEPTH (0..1)      candy-coat absorption — the chosen color multiplies over the zone's OWN
                        value structure (metallic grain / art survives INSIDE the color); more
                        depth = more coats = deeper, edge-darkening candy. 0 = no color.
      FLIP (degrees)    two-tone shift — the paint's dark population rotates to the flip hue,
                        reading like an angle-shift/chameleon two-tone. 0 = off.
      UNDERGLOW (0..1)  ground coat — gold (warm colors) or silver (cool colors) blooms through
                        the bright structure, screen-blended like metal shimmer under candy.

    All three are driven by the underlying paint's value structure, so they NEVER fade the zone
    toward flat gray. paint float 0..1 (h,w,3+), src = the color-source field 0..1."""
    p3 = np.clip(paint[:, :, :3].astype(np.float32), 0.0, 1.0)
    s3 = np.clip(src[:, :, :3].astype(np.float32), 0.0, 1.0)
    d = max(0.0, min(1.0, float(depth if depth is not None else 0.65)))
    fdeg = float(flip_deg or 0.0) % 360.0
    u = max(0.0, min(1.0, float(underglow or 0.0)))
    V = (0.299 * p3[..., 0] + 0.587 * p3[..., 1] + 0.114 * p3[..., 2])

    # DEPTH — Beer-Lambert-ish: transmittance = color^coats over a value-lifted body
    # (0.72 slope keeps the metal/art structure alive inside even the deepest candy)
    lift = (V * 0.72 + 0.45)[..., None]
    T = np.clip(s3, 0.02, 1.0) ** (0.30 + 2.1 * d)
    candy = np.clip(lift * T + np.clip(V - 0.90, 0.0, 1.0)[..., None] * 1.3, 0.0, 1.0)
    alpha = min(1.0, d * 3.0)
    out = p3 * (1.0 - alpha) + candy * alpha

    # UNDERGLOW — metal ground coat shining through (gold under warm, silver under cool).
    # [2026-08-27b owner: "can't tell WHAT Underglow is doing"] the first weighting only fired
    # above V=0.55 — real bases sit mid-value, so the effect was invisible. Now: a base shimmer
    # across the WHOLE surface (metal visible through the translucent color) that ramps molten
    # in the highlights.
    if u > 0.001:
        mean_rgb = s3.reshape(-1, 3).mean(axis=0)
        under = (np.array([1.0, 0.82, 0.35], np.float32) if float(mean_rgb[0]) >= float(mean_rgb[2])
                 else np.array([0.92, 0.95, 1.0], np.float32))
        wb = u * (0.22 + 0.78 * np.clip((V - 0.30) / 0.55, 0.0, 1.0) ** 1.3)
        out = 1.0 - (1.0 - out) * (1.0 - under[None, None, :] * wb[..., None] * 0.85)

    # FLIP — YIQ hue rotation applied to the dark population only
    if fdeg > 0.5:
        rad = np.deg2rad(fdeg)
        cosA, sinA = float(np.cos(rad)), float(np.sin(rad))
        M1 = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], np.float32)
        M2 = np.linalg.inv(M1).astype(np.float32)
        Rm = np.array([[1, 0, 0], [0, cosA, -sinA], [0, sinA, cosA]], np.float32)
        Mh = (M2 @ Rm @ M1).astype(np.float32)
        flipped = np.clip(out @ Mh.T, 0.0, 1.0)
        wd = np.clip((0.55 - V) / 0.35, 0.0, 1.0) ** 1.2
        out = out * (1.0 - wd[..., None]) + flipped * wd[..., None]

    w = (np.asarray(hard_mask, np.float32) * max(0.0, min(1.0, float(strength))))[:, :, None]
    res = paint.copy()
    res[:, :, :3] = p3 * (1.0 - w) + out * w
    return res


def _apply_base_color_override(paint, shape, hard_mask, seed, base_color_mode, base_color, base_color_source, base_color_strength, monolithic_registry, fit_to_bbox=False,
                               base_scale=1.0, base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0,
                               base_flip_h=False, base_flip_v=False,
                               base_color_depth=None, base_color_flip=0.0, base_color_underglow=0.0):
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
    # "finish" = use the material's OWN colour: no override of any kind.
    if mode in ("", "source", "none", "finish"):
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
    # SPB 2026-06-09 owner "Base Scale does nothing" fix: explicit tracking of
    # whether the generated source still needs the placement transform. The two
    # _invoke_*_for_color_source helpers now GUARANTEE placement (consumed
    # inside the paint_fn or fallback-transformed in the helper), so sources
    # from them must not be transformed again (that was the hall-of-mirrors /
    # double-scale family). Solid colors, gradients, and the registry reverse-
    # fallback have no helper and DO need the transform below. The old
    # zone_placement_was_applied() check was dead — the helpers clear the
    # thread-local context in their finally, so it always returned False.
    _src_needs_placement = True
    if mode in ("special", "from_special", "mono"):
        if isinstance(base_color_source, str):
            # --- Mono (special) source: "mono:finish_id" ---
            if base_color_source.startswith("mono:"):
                mono_id = base_color_source[5:]
                _found = False
                if monolithic_registry is not None and mono_id in monolithic_registry:
                    mono_paint_fn = monolithic_registry[mono_id][1]
                    try:
                        src = _invoke_mono_paint_fn_for_color_source(
                            mono_paint_fn,
                            paint,
                            actual_shape,
                            hard_mask,
                            seed,
                            base_scale=base_scale,
                            base_offset_x=base_offset_x,
                            base_offset_y=base_offset_y,
                            base_rotation=base_rotation,
                            base_flip_h=base_flip_h,
                            base_flip_v=base_flip_v,
                        )
                        _src_needs_placement = False  # helper guarantees placement
                    except Exception as _mono_paint_err:
                        print(f"[compose] WARNING: mono paint_fn for '{mono_id}' failed: {_mono_paint_err}")
                    _found = True
                if not _found:
                    # REVERSE FALLBACK: mono: ID is a base-registered finish (migrated
                    # to Specials) — e.g. every PRISM FORGE pf_* finish lives in
                    # BASE_REGISTRY, not MONOLITHIC_REGISTRY.
                    #
                    # SPB 2026-06-26 WHOLE-CANVAS-TILE ROOT FIX (owner: "NONE of the
                    # sources should tile an entire canvas down — for every single
                    # finish"). The old fallback rendered the source with the ZONE
                    # silhouette mask and the LIVE source-art context still active, then
                    # left `_src_needs_placement=True` so line ~2186 tiled that
                    # decal-bearing, car-shaped render at base_scale<1 — stamping a grid
                    # of mini-cars (the recurring "tiling the whole canvas" report,
                    # reproduced on fs_howl + mono:pf_event_horizon_spectra @0.20).
                    #
                    # CURE: render it the SAME clean way as a `base:` source via
                    # _invoke_base_paint_fn_for_color_source — ONES mask (full-canvas,
                    # no silhouette) + neutral gray seed + managed placement context
                    # (set/clear) so a context-reading finish cannot bleed decals in.
                    # That helper guarantees placement (consumes it inside the paint_fn
                    # OR tiles the PURE full-frame pattern), so we must NOT transform it
                    # again. Result: base_scale<1 yields a FINER pure pattern, never a
                    # tiled silhouette. (Same proven path as the SPB-105 base: fix.)
                    try:
                        from engine.registry import BASE_REGISTRY as _BR
                        if mono_id in _BR:
                            _base_paint_fn = _BR[mono_id].get("paint_fn", paint_none)
                            if _base_paint_fn is not paint_none:
                                _rev_src = _invoke_base_paint_fn_for_color_source(
                                    _base_paint_fn,
                                    paint,
                                    actual_shape,
                                    seed,
                                    base_scale=base_scale,
                                    base_offset_x=base_offset_x,
                                    base_offset_y=base_offset_y,
                                    base_rotation=base_rotation,
                                    base_flip_h=base_flip_h,
                                    base_flip_v=base_flip_v,
                                )
                                if _rev_src is not None:
                                    # keep the historical readability boost for mono: sources
                                    src = _boost_overlay_mono_color(_rev_src)
                                    _src_needs_placement = False  # helper guarantees placement
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
                            src = _invoke_base_paint_fn_for_color_source(
                                base_paint_fn,
                                paint,
                                actual_shape,
                                seed,
                                base_scale=base_scale,
                                base_offset_x=base_offset_x,
                                base_offset_y=base_offset_y,
                                base_rotation=base_rotation,
                                base_flip_h=base_flip_h,
                                base_flip_v=base_flip_v,
                            )
                            _src_needs_placement = False  # helper guarantees placement
                    # Also check monolithic registry with raw ID (user picked a special without prefix)
                    elif monolithic_registry is not None and raw_id in monolithic_registry:
                        mono_paint_fn = monolithic_registry[raw_id][1]
                        src = _invoke_mono_paint_fn_for_color_source(
                            mono_paint_fn,
                            paint,
                            actual_shape,
                            hard_mask,
                            seed,
                            base_scale=base_scale,
                            base_offset_x=base_offset_x,
                            base_offset_y=base_offset_y,
                            base_rotation=base_rotation,
                            base_flip_h=base_flip_h,
                            base_flip_v=base_flip_v,
                        )
                        _src_needs_placement = False  # helper guarantees placement
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
    # Placement for sources that have no helper (solid / gradient / registry
    # reverse-fallback). Helper-generated special sources arrive here already
    # placed (_src_needs_placement=False) — transforming them again was the
    # double-scale / hall-of-mirrors recurrence.
    if _src_needs_placement:
        src = _transform_base_color_source(
            src, actual_shape,
            scale=base_scale,
            offset_x=base_offset_x,
            offset_y=base_offset_y,
            rotation=base_rotation,
            flip_h=bool(base_flip_h),
            flip_v=bool(base_flip_v),
        )

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

    if base_color_depth is not None:
        # [SPB COLOR LAB 2026-08-27] new pipeline — legacy crossfade below stays byte-identical
        # for payloads without the new keys (old saved projects render unchanged).
        return _color_lab_blend(paint, src, hard_mask, base_color_depth, base_color_flip,
                                base_color_underglow, strength)
    w = (hard_mask * strength)[:, :, np.newaxis]
    paint = paint.copy()
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - w) + src * w
    return paint


def _base_color_mode_is_explicit(base_color_mode, base_color_strength) -> bool:
    mode = str(base_color_mode or "source").strip().lower()
    if mode in ("", "source", "none"):
        return False
    try:
        return float(base_color_strength if base_color_strength is not None else 1.0) > 0.001
    except (TypeError, ValueError):
        return True


def _tint_direct_pattern_paint(pattern_paint: np.ndarray,
                               color_substrate: np.ndarray,
                               hard_mask: np.ndarray,
                               strength: float) -> np.ndarray:
    """Make SPB rebuilt direct-pattern paint obey explicit base color choices.

    The rebuilt regular patterns may have authored default colors, but when the
    painter picks a solid/gradient/special color source those colors need to
    drive the pattern. This preserves the renderer's luminance/detail while
    borrowing hue/chroma from the already-colorized substrate.
    """
    try:
        tint_strength = max(0.0, min(1.0, float(strength if strength is not None else 1.0)))
    except (TypeError, ValueError):
        tint_strength = 1.0
    if tint_strength <= 0.001:
        return pattern_paint
    patt = np.clip(np.asarray(pattern_paint, dtype=np.float32)[:, :, :3], 0.0, 1.0)
    src = np.clip(np.asarray(color_substrate, dtype=np.float32)[:, :, :3], 0.0, 1.0)
    if patt.shape[:2] != src.shape[:2]:
        return pattern_paint
    lum = (
        patt[:, :, 0] * 0.299
        + patt[:, :, 1] * 0.587
        + patt[:, :, 2] * 0.114
    )
    # Keep fine light/dark pattern identity without reintroducing the default
    # palette as the dominant color.
    detail = np.clip(0.42 + lum[:, :, np.newaxis] * 1.08, 0.0, 1.35)
    colorized = np.clip(src * detail, 0.0, 1.0)
    colorized = np.clip(colorized + lum[:, :, np.newaxis] * 0.08, 0.0, 1.0)
    mask3 = np.asarray(hard_mask, dtype=np.float32)[:, :, np.newaxis]
    if mask3.shape[:2] != patt.shape[:2]:
        mask3 = np.ones(patt.shape[:2] + (1,), dtype=np.float32)
    local_strength = np.clip(mask3, 0.0, 1.0) * tint_strength
    out = patt * (1.0 - local_strength) + colorized * local_strength
    return np.ascontiguousarray(np.clip(out, 0.0, 1.0).astype(np.float32))


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


# ── PHYSICAL SPEC BLEND MODES (2026-06-12, owner-approved rewrite) ──────────
# Photoshop modes are photo vocabulary; a spec map is three physical dials.
# These modes are OPTICAL BEHAVIORS built on the Ghost Fracture physics:
# M = paint-tinted reflection lobe, R = gates reflection sharpness,
# CC = paint-INDEPENDENT env mirror (THE color-shift channel).
PHYSICAL_SPEC_BLEND_MODES = (
    "ghost_carve", "chrome_inlay", "frost_etch",
    "angle_flip", "ember_gate", "depth_press",
)


def apply_physical_spec_blend(M_arr, R_arr, CC_arr, pv, opacity, mode):
    """Blend a pattern field into ALL THREE spec channels as a physical effect.

    Args:
        M_arr/R_arr/CC_arr: spec channels in [0,255] (float arrays; CC may be
            a scalar — it is broadcast against pv).
        pv: pattern field normalized to [0,1].
        opacity: 0-1 strength.
        mode: one of PHYSICAL_SPEC_BLEND_MODES.

    Returns:
        (M, R, CC) blended float arrays clipped to [0,255].

    Modes:
        ghost_carve  — the pattern carves env-mirror cells into the clearcoat
                       (the Ghost Fracture recipe as a blend mode): pattern
                       lows cut CC dark, highs flood toward mirror; the metal
                       lobe is untouched so ANY base keeps its tinted flash
                       and the crush ritual works on ANY finish/combo.
        chrome_inlay — dielectric mirror inlay where the pattern is hot:
                       metal dips, clearcoat ceilings, gloss floors (the
                       "blue insight" — hardest possible env flash).
        frost_etch   — the pattern sandblasts the gloss: roughness up, metal
                       slightly down. Etched areas go milky in sun while the
                       rest stays mirror.
        angle_flip   — pattern hot areas get metal-flash physics, the negative
                       space gets mirror-flash physics: the pattern APPEARS at
                       one viewing angle and INVERTS at another.
        ember_gate   — only the pattern's top ridges ignite (CC pinned near
                       max + gloss floor): sparkle ignition along edges, calm
                       everywhere else.
        depth_press  — emboss in spec only: every pattern element gets a lit
                       rim and a shadow rim — reads stamped INTO the paint.
    """
    o = float(max(0.0, min(1.0, opacity)))
    pv = xp.clip(xp.asarray(pv, xp.float32), 0, 1)
    M = xp.asarray(M_arr, xp.float32)
    R = xp.asarray(R_arr, xp.float32)
    CC = CC_arr if hasattr(CC_arr, "ndim") else xp.full_like(pv, float(CC_arr))
    CC = xp.asarray(CC, xp.float32)
    if mode == "ghost_carve":
        # ABSOLUTE target, not a relative nudge: pull clearcoat toward the
        # measured Ghost Fracture contract (carved cells swing ~64<->240) so
        # the carve hits FULL strength on ANY base — even ones with CC near 0
        # (metallics) or pinned high. This is what makes "crush ritual on any
        # finish/combo" actually true.
        target = 64.0 + 176.0 * pv
        CC = xp.clip(CC + (target - CC) * o, 0, 255)
        R = xp.clip(R - 25.0 * pv * o, 16, 255)
    elif mode == "chrome_inlay":
        hot = xp.clip(pv * 1.6 - 0.6, 0, 1) * o
        M = xp.clip(M * (1.0 - 0.85 * hot), 0, 255)
        R = xp.clip(R * (1.0 - 0.65 * hot), 16, 255)
        CC = xp.clip(CC + (245.0 - CC) * hot, 0, 255)
    elif mode == "frost_etch":
        M = xp.clip(M - 45.0 * pv * o, 0, 255)
        R = xp.clip(R + 150.0 * pv * o, 16, 255)
        CC = xp.clip(CC - 35.0 * pv * o, 0, 255)
    elif mode == "angle_flip":
        s = (pv - 0.5) * 2.0 * o
        M = xp.clip(M + 85.0 * s, 0, 255)
        CC = xp.clip(CC - 135.0 * s, 0, 255)
    elif mode == "ember_gate":
        g = xp.clip((pv - 0.80) / 0.06, 0, 1) * o
        CC = xp.clip(CC + (252.0 - CC) * g, 0, 255)
        R = xp.clip(R * (1.0 - g) + 34.0 * g, 16, 255)
    elif mode == "depth_press":
        gy, gx = xp.gradient(pv)
        e = (gx + gy) * 0.7071
        e_max = float(xp.max(xp.abs(e)))
        e = e / (e_max if e_max > 1e-8 else 1.0)
        ep = xp.clip(e, 0, 1)
        en = xp.clip(-e, 0, 1)
        M = xp.clip(M + (110.0 * ep - 70.0 * en) * o, 0, 255)
        CC = xp.clip(CC + 90.0 * ep * o, 0, 255)
    return M, R, CC


def _normalize_pattern_field(pv):
    """Normalize a pattern value array to [0,1] for physical blending."""
    pv = xp.asarray(pv, xp.float32)
    lo = float(xp.min(pv))
    hi = float(xp.max(pv))
    if hi - lo > 1e-8:
        return (pv - lo) / (hi - lo)
    return xp.zeros_like(pv)


def _apply_spec_pattern_to_channels(sp_arr, M_arr, R_arr, CC_arr,
                                     sp_range, sp_opacity, sp_blend, sp_channels,
                                     cc_fallback=None):
    """Apply a spec pattern array to M/R/CC channels.

    Handles BOTH 2-D (legacy single-channel — same delta applied to selected
    channels) AND 3-D (h,w,3) [M,R,CC] independent per-channel deltas.

    The 3-D path is the post-2026-05-23 owner directive: pattern functions
    can author truly independent M / R / CC fields per pixel, giving real
    depth (one region chrome, another matte, in the same finish).

    cc_fallback: when the layer targets the CC channel ("C" in sp_channels)
    but CC_arr is None (the base spec_fn returned only M/R, e.g. f_metallic
    and most Foundation metallic bases), materialize a flat CC field at this
    scalar level so the CC pattern delta has something to write into. Without
    it the entire CC branch is skipped and CC stays a constant scalar
    (final_CC = effective_base_CC) — which is exactly why CC-dominant spec
    patterns (diffraction / holographic / iridescent / heat_discoloration)
    produced ZERO clearcoat variation on metallic bases. When None (default)
    behavior is unchanged, so callers that don't opt in keep the old path.

    Returns: (M_arr, R_arr, CC_arr) updated in place semantics — each
    returned even if not modified.
    """
    if sp_arr is None:
        return M_arr, R_arr, CC_arr
    # If this layer writes the CC channel but the base produced no per-pixel
    # CC field, seed one at the base gloss level so the CC math below runs.
    if (CC_arr is None and cc_fallback is not None and "C" in sp_channels
            and getattr(sp_arr, "ndim", 2) >= 2):
        try:
            _sp_h, _sp_w = int(sp_arr.shape[0]), int(sp_arr.shape[1])
            CC_arr = xp.full((_sp_h, _sp_w), float(cc_fallback), dtype=xp.float32)
        except Exception:
            CC_arr = None
    arr_ndim = getattr(sp_arr, "ndim", 2)
    # 3-channel path
    if arr_ndim == 3 and sp_arr.shape[2] >= 3:
        M_ch = sp_arr[:, :, 0]
        R_ch = sp_arr[:, :, 1]
        CC_ch = sp_arr[:, :, 2]
        if "M" in sp_channels and M_arr is not None:
            M_contrib = (M_ch - 0.5) * 2.0 * sp_range
            M_arr = _apply_spec_blend_mode(M_arr, M_contrib, sp_opacity, sp_blend)
            M_arr = xp.clip(M_arr, 0, 255).astype(xp.float32)
        if "R" in sp_channels and R_arr is not None:
            R_contrib = (R_ch - 0.5) * 2.0 * sp_range
            R_arr = _apply_spec_blend_mode(R_arr, R_contrib, sp_opacity, sp_blend)
            R_arr = xp.clip(R_arr, 0, 255).astype(xp.float32)
        if "C" in sp_channels and CC_arr is not None:
            # CC semantics: pattern channel 0..1 brightness where 1 = "glossy"
            # (low B value in the spec map, near 16). So invert the delta
            # direction — bright pattern pushes B toward LOW (more gloss).
            #
            # 2026-05-25 OWNER-EYE FIX: on metallic bases (base CC=16, gloss
            # floor) the "subtract toward more gloss" direction has zero
            # headroom — high-pattern-CC pixels get clipped to 16 and produce
            # no visible variation. The "add toward duller" direction works
            # fine. To restore visible CC variation on metallic finishes we:
            #
            #   1) POLARIZE pattern CC away from 0.5 toward 0.0/1.0 extremes
            #      — boosts the amplitude of every pattern's CC swings without
            #      requiring the 246+ pattern functions to be rewritten.
            #
            #   2) AMPLIFY the CC contribution scale 2.5x vs M/R so that even
            #      the "dull intent" half (which DOES have headroom) punches
            #      hard enough to be visible against the gloss floor.
            #
            # Together these make CC patterns visible on metallic AND
            # non-metallic bases. On non-metallic bases the gloss direction
            # also gets visible variation.
            _cc_centered = CC_ch - 0.5                  # range [-0.5, +0.5]
            _cc_sign = xp.sign(_cc_centered)
            _cc_polarized = 0.5 + _cc_sign * xp.sqrt(xp.abs(_cc_centered) * 2.0) * 0.5
            _cc_polarized = xp.clip(_cc_polarized, 0.0, 1.0)
            CC_contrib = (_cc_polarized - 0.5) * 2.0 * sp_range * 2.5
            CC_arr = _apply_spec_blend_mode(CC_arr, -CC_contrib, sp_opacity, sp_blend)
            CC_arr = xp.clip(CC_arr, 16, 255).astype(xp.float32)
        return M_arr, R_arr, CC_arr
    # Legacy 2-D path: identical delta on each selected channel
    sp_delta = (sp_arr - 0.5) * 2.0
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
    return M_arr, R_arr, CC_arr


def compose_finish(base_id, pattern_id, shape, mask, seed, sm, scale=1.0, spec_mult=1.0, rotation=0,
                   pattern_opacity=1.0,
                   base_scale=1.0, base_strength=1.0, base_spec_strength=1.0, base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0,
                   base_flip_h=False, base_flip_v=False,
                   cc_quality=None, blend_base=None, blend_dir="horizontal",
                   blend_amount=0.5, paint_color=None,
                   second_base=None, second_base_color=None, second_base_strength=0.0, second_base_spec_strength=1.0, second_base_rotation=0.0, second_base_spec_rotation=0.0,
                   second_base_blend_mode="noise", second_base_noise_scale=24,
                   second_base_scale=1.0, second_base_color_scale=1.0, second_base_spec_scale=1.0, second_base_pattern=None,
                   second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                   second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                   second_base_pattern_invert=False, second_base_pattern_harden=False,
                   second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                   third_base=None, third_base_color=None, third_base_strength=0.0, third_base_spec_strength=1.0, third_base_rotation=0.0, third_base_spec_rotation=0.0,
                   third_base_blend_mode="noise", third_base_noise_scale=24,
                   third_base_scale=1.0, third_base_color_scale=1.0, third_base_spec_scale=1.0, third_base_pattern=None,
                   third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                   third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                   third_base_pattern_invert=False, third_base_pattern_harden=False,
                   third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                   fourth_base=None, fourth_base_color=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0, fourth_base_rotation=0.0, fourth_base_spec_rotation=0.0,
                   fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                   fourth_base_scale=1.0, fourth_base_color_scale=1.0, fourth_base_spec_scale=1.0, fourth_base_pattern=None,
                   fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                   fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                   fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                   fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                   fifth_base=None, fifth_base_color=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0, fifth_base_rotation=0.0, fifth_base_spec_rotation=0.0,
                   fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                   fifth_base_scale=1.0, fifth_base_color_scale=1.0, fifth_base_spec_scale=1.0, fifth_base_pattern=None,
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
    pattern_fit_zone = bool(kwargs.get("pattern_fit_zone", False))
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

    base_shape, _base_spec_tile_after = _base_spec_generation_shape(shape, base_scale)

    _base_seed_offset = abs(hash(base_id)) % 10000
    _bss = max(0.0, min(2.0, float(base_spec_strength)))
    effective_base_CC = _scale_base_clearcoat_scalar(base_CC, _bss)
    if base.get("base_spec_fn"):
        spec_result = _cached_base_spec_result(base_id, base["base_spec_fn"], base_shape, seed + _base_seed_offset, _sm_base, base_M, base_R)
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

    if _base_spec_tile_after or (
        base_scale > 1.0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1])
    ):
        M_arr, R_arr, CC_arr = _apply_base_scale_to_spec_channels(
            M_arr, R_arr, CC_arr, shape, base_scale
        )

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
    kwargs = _spec_active_options(kwargs)
    _spec_patterns = _spec_active_layers(kwargs.get("spec_pattern_stack", []) or base.get("spec_pattern_stack", []))
    if _spec_patterns:
        from engine.spec_patterns import PATTERN_CATALOG
        for sp_layer in _spec_patterns:
            sp_name = sp_layer.get("pattern", "")
            sp_fn = _get_spec_pattern_fn_or_skip(PATTERN_CATALOG, sp_name, "spec_pattern_stack")
            if sp_fn is None:
                continue
            # SPB-105 / v2 tick 1: new overlays follow the completed material.
            if _spec_overlay_version(sp_layer, sp_fn) >= 2:
                continue
            sp_opacity_raw = float(sp_layer.get("opacity", 0.5))
            sp_opacity = _spec_overlay_opacity(sp_layer, sp_fn)
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
            _sp_seed = _spec_overlay_seed(sp_layer, sp_fn, seed, 5000)
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
            # SPB-2026-05-19 owner: spec pattern stack must use the COMPOSED shape, not
            # base_shape. When base_scale > 1, base_shape is smaller (e.g. 1107x1107) and
            # M_arr / R_arr / CC_arr were already resized to `shape`; generating sp_arr at
            # base_shape would broadcast-fail (2048,2048) vs (1107,1107).
            _sp_shape = (int(shape[0]), int(shape[1]))
            sp_arr = _cached_spec_pattern_array(
                sp_fn, sp_name, _sp_shape, _sp_seed, _sp_sm, sp_params,
                sp_scale, sp_rotation, sp_offset_x, sp_offset_y, sp_box_size,
            )
            if _gpu_active:
                sp_arr = to_gpu(sp_arr)
            sp_range = float(sp_layer.get("range", 60.0))
            M_arr, R_arr, CC_arr = _apply_spec_pattern_to_channels(
                sp_arr, M_arr, R_arr, CC_arr,
                sp_range, sp_opacity, sp_blend, sp_channels,
                cc_fallback=effective_base_CC,
            )

    final_CC = CC_arr if CC_arr is not None else effective_base_CC
    pattern_entry = _resolve_pattern_registry_entry(pattern_id, PATTERN_REGISTRY)
    has_pattern = pattern_entry is not None

    if has_pattern and not kwargs.get("independent_pattern_spec", False):
        pattern = pattern_entry
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
                if pattern_fit_zone:
                    pv = _fit_pattern_to_mask_bbox(pv, to_cpu(mask) if _gpu_active else mask)
                # Transfer to GPU for blending math
                if _gpu_active:
                    pv = to_gpu(pv)
                R_range, M_range = 60.0, 50.0
                _pat_scale = pattern_sm_eff * spec_mult * max(0.0, min(1.0, float(pattern_opacity)))
                # Mask the pattern so it only affects pixels INSIDE the zone
                pv_masked = pv * mask
                if base_spec_blend_mode in PHYSICAL_SPEC_BLEND_MODES:
                    # the single-pattern path is what the booth actually hits —
                    # physical modes MUST fire here too (2026-06-12 fix: this
                    # path silently ignored every blend mode)
                    M_arr, R_arr, final_CC = apply_physical_spec_blend(
                        M_arr, R_arr, final_CC, _normalize_pattern_field(pv_masked),
                        max(0.0, min(1.0, float(pattern_opacity))) * pattern_sm_eff,
                        base_spec_blend_mode)
                else:
                    M_arr = M_arr + pv_masked * M_range * _pat_scale
                    R_arr = R_arr + pv_masked * R_range * _pat_scale
        elif tex_fn is not None:
            # tex_fn needs CPU mask
            _mask_cpu_tex = to_cpu(mask) if _gpu_active else mask
            try:
                tex = tex_fn(shape, _mask_cpu_tex, seed, sm)
            except Exception as _tex_err:
                raise RuntimeError(
                    f"Pattern texture renderer failed [{pattern_id}]: {_tex_err}"
                ) from _tex_err
            if tex is not None:
                pv = tex["pattern_val"]
                R_range = tex["R_range"]
                M_range = tex["M_range"]

                if scale != 1.0 and scale > 0:
                    # [SPB 2026-06-10 whole-car-tiling fix v2 — fast] scale<1 tiles the pure
                    # output-res pattern_val DOWN (motifs shrink + repeat); scale>1 crops.
                    # No regenerate-at-4096 — single output-res gen above keeps render fast.
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

                if pattern_fit_zone:
                    _mask_cpu_fit = to_cpu(mask) if _gpu_active else mask
                    _pv_before_fit = pv
                    pv = _fit_pattern_to_mask_bbox(pv, _mask_cpu_fit)
                    if M_pv is _pv_before_fit:
                        M_pv = pv
                    elif M_pv is not None:
                        M_pv = _fit_pattern_to_mask_bbox(M_pv, _mask_cpu_fit)
                    if R_pv is _pv_before_fit:
                        R_pv = pv
                    elif R_pv is not None:
                        R_pv = _fit_pattern_to_mask_bbox(R_pv, _mask_cpu_fit)
                    if CC_pv is not None:
                        CC_pv = _fit_pattern_to_mask_bbox(CC_pv, _mask_cpu_fit)

                # Transfer pattern arrays to GPU for blending
                if _gpu_active:
                    M_pv = to_gpu(M_pv)
                    R_pv = to_gpu(R_pv)
                    if CC_pv is not None:
                        CC_pv = to_gpu(CC_pv)

                _pat_scale = pattern_sm_eff * spec_mult * max(0.0, min(1.0, float(pattern_opacity)))
                if base_spec_blend_mode in PHYSICAL_SPEC_BLEND_MODES:
                    _pv_phys = _normalize_pattern_field(np.asarray(pv, np.float32))
                    if _gpu_active:
                        _pv_phys = to_gpu(_pv_phys)
                    M_arr, R_arr, final_CC = apply_physical_spec_blend(
                        M_arr, R_arr, final_CC, _pv_phys * mask,
                        max(0.0, min(1.0, float(pattern_opacity))) * pattern_sm_eff,
                        base_spec_blend_mode)
                    # physical modes own all three channels — skip legacy contribs
                    tex = dict(tex)
                    tex.pop("R_extra", None)
                    tex.pop("M_extra", None)
                    tex.pop("CC", None)
                    CC_pv = None
                else:
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
    _dither_rng = _DitherPlanes(seed if seed else 42) if dither else None  # [gauntlet 2026-07-04] cached planes, bit-identical
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

    _overlay_spec_alpha_masks = {
        "overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
        "third_overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
        "fourth_overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
        "fifth_overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
    }
    _weighted_overlay_layers = []
    for _ov in (
        {"base": second_base, "paint_strength": second_base_strength, "spec_strength": second_base_spec_strength, "blend_mode": second_base_blend_mode, "noise_scale": second_base_noise_scale, "scale": second_base_scale, "pattern": second_base_pattern, "pattern_scale": second_base_pattern_scale, "pattern_rotation": second_base_pattern_rotation, "pattern_opacity": second_base_pattern_opacity, "pattern_strength": second_base_pattern_strength, "pattern_invert": second_base_pattern_invert, "pattern_harden": second_base_pattern_harden, "pattern_offset_x": second_base_pattern_offset_x, "pattern_offset_y": second_base_pattern_offset_y, "seed": seed, "spec_seed": seed + 999, "spec_scale": second_base_spec_scale, "rotation": second_base_rotation, "spec_rotation": second_base_spec_rotation, "stack_key": "overlay_spec_pattern_stack"},
        {"base": third_base, "paint_strength": third_base_strength, "spec_strength": third_base_spec_strength, "blend_mode": third_base_blend_mode, "noise_scale": third_base_noise_scale, "scale": third_base_scale, "pattern": third_base_pattern, "pattern_scale": third_base_pattern_scale, "pattern_rotation": third_base_pattern_rotation, "pattern_opacity": third_base_pattern_opacity, "pattern_strength": third_base_pattern_strength, "pattern_invert": third_base_pattern_invert, "pattern_harden": third_base_pattern_harden, "pattern_offset_x": third_base_pattern_offset_x, "pattern_offset_y": third_base_pattern_offset_y, "seed": seed + 8888, "spec_seed": seed + 1999, "spec_scale": third_base_spec_scale, "rotation": third_base_rotation, "spec_rotation": third_base_spec_rotation, "stack_key": "third_overlay_spec_pattern_stack"},
        {"base": fourth_base, "paint_strength": fourth_base_strength, "spec_strength": fourth_base_spec_strength, "blend_mode": fourth_base_blend_mode, "noise_scale": fourth_base_noise_scale, "scale": fourth_base_scale, "pattern": fourth_base_pattern, "pattern_scale": fourth_base_pattern_scale, "pattern_rotation": fourth_base_pattern_rotation, "pattern_opacity": fourth_base_pattern_opacity, "pattern_strength": fourth_base_pattern_strength, "pattern_invert": fourth_base_pattern_invert, "pattern_harden": fourth_base_pattern_harden, "pattern_offset_x": fourth_base_pattern_offset_x, "pattern_offset_y": fourth_base_pattern_offset_y, "seed": seed + 9999, "spec_seed": seed + 2999, "spec_scale": fourth_base_spec_scale, "rotation": fourth_base_rotation, "spec_rotation": fourth_base_spec_rotation, "stack_key": "fourth_overlay_spec_pattern_stack"},
        {"base": fifth_base, "paint_strength": fifth_base_strength, "spec_strength": fifth_base_spec_strength, "blend_mode": fifth_base_blend_mode, "noise_scale": fifth_base_noise_scale, "scale": fifth_base_scale, "pattern": fifth_base_pattern, "pattern_scale": fifth_base_pattern_scale, "pattern_rotation": fifth_base_pattern_rotation, "pattern_opacity": fifth_base_pattern_opacity, "pattern_strength": fifth_base_pattern_strength, "pattern_invert": fifth_base_pattern_invert, "pattern_harden": fifth_base_pattern_harden, "pattern_offset_x": fifth_base_pattern_offset_x, "pattern_offset_y": fifth_base_pattern_offset_y, "seed": seed + 10999, "spec_seed": seed + 3999, "spec_scale": fifth_base_spec_scale, "rotation": fifth_base_rotation, "spec_rotation": fifth_base_spec_rotation, "stack_key": "fifth_overlay_spec_pattern_stack"},
    ):
        # [SPB-OVERLAY-PARITY 2026-08-20] This loop builds the overlay's SPEC
        # contribution, so it is gated by SPEC strength. It used to gate on PAINT
        # strength, which made a spec-only overlay (paint 0, spec 100) impossible
        # and let the paint slider silently switch the whole material layer off.
        if not _ov["base"] or float(_ov["spec_strength"] or 0.0) <= 1e-6:
            continue
        try:
            _ov_spec, _ = _build_base_overlay_spec_for_weight_mix(
                _ov["base"], shape, mask,
                _ov["spec_seed"] + abs(hash(_ov["base"])) % 10000,
                sm, BASE_REGISTRY, monolithic_registry,
                spec_scale=float(_ov.get("spec_scale", 1.0) or 1.0),
                rotation=float(_ov.get("rotation", 0.0) or 0.0),
                spec_rotation=float(_ov.get("spec_rotation", 0.0) or 0.0),
            )
            if _ov_spec is None:
                continue
            _pat_id_ov = _resolve_overlay_pattern_mask_id(
                _ov["pattern"], pattern_id, _ov["blend_mode"]
            )
            _ov_pattern_mask = _get_pattern_mask(
                _pat_id_ov, shape, mask, seed, sm,
                scale=_ov["pattern_scale"], rotation=_ov["pattern_rotation"],
                opacity=_ov["pattern_opacity"], strength=_ov["pattern_strength"],
                offset_x=_ov["pattern_offset_x"], offset_y=_ov["pattern_offset_y"],
            ) if _pat_id_ov else None
            if _ov_pattern_mask is not None:
                if _ov["pattern_invert"]:
                    _ov_pattern_mask = 1.0 - _ov_pattern_mask
                if _ov["pattern_harden"]:
                    _ov_pattern_mask = _harden_overlay_pattern_mask(_ov_pattern_mask)
            _weighted_overlay_layers.append({
                "spec": _ov_spec,
                "strength": _ov["spec_strength"],
                "blend_mode": _ov["blend_mode"],
                "noise_scale": _ov["noise_scale"],
                "seed": _ov["seed"],
                "pattern_mask": _ov_pattern_mask,
                "overlay_scale": _ov["scale"],
                "stack_key": _ov["stack_key"],
            })
        except Exception as _ov_mix_err:
            logger.warning("compose_finish: weighted overlay prepare failed for '%s': %s", _ov["base"], _ov_mix_err)
    if _weighted_overlay_layers:
        spec = _weighted_mix_base_overlay_specs(spec, _weighted_overlay_layers, shape, mask)
        for _layer in _weighted_overlay_layers:
            _stack_key = _layer.get("stack_key")
            _layer_alpha = _layer.get("_overlay_alpha")
            if _stack_key in _overlay_spec_alpha_masks and _layer_alpha is not None:
                _overlay_spec_alpha_masks[_stack_key] = np.maximum(
                    _overlay_spec_alpha_masks[_stack_key],
                    np.clip(_layer_alpha, 0.0, 1.0).astype(np.float32),
                )
        second_base_strength = third_base_strength = fourth_base_strength = fifth_base_strength = 0.0

    if second_base and second_base_strength > 0.001 and second_base_spec_strength > 1e-6:
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
                    _sb_result = _cached_base_spec_result(second_base, _sb_def["base_spec_fn"], shape, _sb_seed + _sb_seed_off, sm, _sb_M, _sb_R)
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
                # SPB-2026-05-19 owner: per-overlay Spec Scale parity knob
                if abs(float(second_base_spec_scale) - 1.0) > 0.01:
                    _sb_M_arr, _sb_R_arr, _sb_CC_arr = _apply_base_scale_to_spec_channels(
                        _sb_M_arr, _sb_R_arr, _sb_CC_arr, shape, float(second_base_spec_scale)
                    )
                _sb_M_final = _sb_M_arr * mask + 5.0 * (1 - mask)
                _sb_R_final = _sb_R_arr * mask + 100.0 * (1 - mask)
                spec_secondary[:,:,0] = np.clip(_sb_M_final, 0, 255).astype(np.uint8)
                spec_secondary[:,:,1] = _ggx_safe_R(_sb_R_final, _sb_M_final).astype(np.uint8)
                spec_secondary[:,:,2] = np.clip(_sb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_secondary[:,:,3] = 255

            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_sb = _resolve_overlay_pattern_mask_id(
                second_base_pattern, pattern_id, second_base_blend_mode
            )
            _sb_pat_scale, _sb_pat_rot, _sb_pat_ox, _sb_pat_oy = _resolve_overlay_pattern_transform(
                second_base_pattern, _pat_id_sb, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                second_base_pattern_scale, second_base_pattern_rotation,
                second_base_pattern_offset_x, second_base_pattern_offset_y,
            )
            pattern_mask = _get_pattern_mask(_pat_id_sb, shape, mask, seed, sm,
                scale=_sb_pat_scale, rotation=_sb_pat_rot,
                opacity=second_base_pattern_opacity, strength=second_base_pattern_strength,
                offset_x=_sb_pat_ox, offset_y=_sb_pat_oy) if _pat_id_sb else None
            if pattern_mask is not None:
                if second_base_pattern_invert:
                    pattern_mask = 1.0 - pattern_mask
                if second_base_pattern_harden:
                    pattern_mask = _harden_overlay_pattern_mask(pattern_mask)
            spec, _sb_alpha = blend_dual_base_spec(
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
            if _sb_alpha is not None:
                _overlay_spec_alpha_masks["overlay_spec_pattern_stack"] = np.clip(_sb_alpha, 0.0, 1.0).astype(np.float32)
        except Exception as e:
            logger.warning("compose_finish: second_base overlay failed for '%s': %s", second_base, e)

    if third_base and third_base_strength > 0.001 and third_base_spec_strength > 1e-6:
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
                    _tb_result = _cached_base_spec_result(third_base, _tb_def["base_spec_fn"], shape, _tb_seed + _tb_seed_off, sm, _tb_M, _tb_R)
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
                # SPB-2026-05-19 owner: per-overlay Spec Scale parity knob
                if abs(float(third_base_spec_scale) - 1.0) > 0.01:
                    _tb_M_arr, _tb_R_arr, _tb_CC_arr = _apply_base_scale_to_spec_channels(
                        _tb_M_arr, _tb_R_arr, _tb_CC_arr, shape, float(third_base_spec_scale)
                    )
                _tb_M_final = _tb_M_arr * mask + 5.0 * (1 - mask)
                _tb_R_final = _tb_R_arr * mask + 100.0 * (1 - mask)
                spec_tertiary[:,:,0] = np.clip(_tb_M_final, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,1] = _ggx_safe_R(_tb_R_final, _tb_M_final).astype(np.uint8)
                spec_tertiary[:,:,2] = np.clip(_tb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,3] = 255
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = _resolve_overlay_pattern_mask_id(
                third_base_pattern, pattern_id, third_base_blend_mode
            )
            _tb_pat_scale, _tb_pat_rot, _tb_pat_ox, _tb_pat_oy = _resolve_overlay_pattern_transform(
                third_base_pattern, _pat_id_tb, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                third_base_pattern_scale, third_base_pattern_rotation,
                third_base_pattern_offset_x, third_base_pattern_offset_y,
            )
            _tb_pattern_mask = _get_pattern_mask(_pat_id_tb, shape, mask, seed, sm,
                scale=_tb_pat_scale, rotation=_tb_pat_rot,
                opacity=third_base_pattern_opacity, strength=third_base_pattern_strength,
                offset_x=_tb_pat_ox, offset_y=_tb_pat_oy) if _pat_id_tb else None
            if _tb_pattern_mask is not None:
                if third_base_pattern_invert:
                    _tb_pattern_mask = 1.0 - _tb_pattern_mask
                if third_base_pattern_harden:
                    _tb_pattern_mask = _harden_overlay_pattern_mask(_tb_pattern_mask)
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
            if _tb_alpha is not None:
                _overlay_spec_alpha_masks["third_overlay_spec_pattern_stack"] = np.clip(_tb_alpha, 0.0, 1.0).astype(np.float32)
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
    if fourth_base and fourth_base_strength > 0.001 and fourth_base_spec_strength > 1e-6:
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
                    _fb_result = _cached_base_spec_result(fourth_base, _fb_def["base_spec_fn"], shape, _fb_seed + _fb_seed_off, sm, _fb_M, _fb_R)
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
                # SPB-2026-05-19 owner: per-overlay Spec Scale parity knob
                if abs(float(fourth_base_spec_scale) - 1.0) > 0.01:
                    _fb_M_arr, _fb_R_arr, _fb_CC_arr = _apply_base_scale_to_spec_channels(
                        _fb_M_arr, _fb_R_arr, _fb_CC_arr, shape, float(fourth_base_spec_scale)
                    )
                _fb_M_final = _fb_M_arr * mask + 5.0 * (1 - mask)
                _fb_R_final = _fb_R_arr * mask + 100.0 * (1 - mask)
                spec_quaternary[:,:,0] = np.clip(_fb_M_final, 0, 255).astype(np.uint8)
                spec_quaternary[:,:,1] = _ggx_safe_R(_fb_R_final, _fb_M_final).astype(np.uint8)
                spec_quaternary[:,:,2] = np.clip(_fb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_quaternary[:,:,3] = 255
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = _resolve_overlay_pattern_mask_id(
                fourth_base_pattern, pattern_id, fourth_base_blend_mode
            )
            _fb_pat_scale, _fb_pat_rot, _fb_pat_ox, _fb_pat_oy = _resolve_overlay_pattern_transform(
                fourth_base_pattern, _pat_id_fb, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                fourth_base_pattern_scale, fourth_base_pattern_rotation,
                fourth_base_pattern_offset_x, fourth_base_pattern_offset_y,
            )
            _fb_pattern_mask = _get_pattern_mask(_pat_id_fb, shape, mask, seed, sm,
                scale=_fb_pat_scale, rotation=_fb_pat_rot,
                opacity=fourth_base_pattern_opacity, strength=fourth_base_pattern_strength,
                offset_x=_fb_pat_ox, offset_y=_fb_pat_oy) if _pat_id_fb else None
            if _fb_pattern_mask is not None:
                if fourth_base_pattern_invert:
                    _fb_pattern_mask = 1.0 - _fb_pattern_mask
                if fourth_base_pattern_harden:
                    _fb_pattern_mask = _harden_overlay_pattern_mask(_fb_pattern_mask)
            spec, _fb_alpha = blend_dual_base_spec(
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
            if _fb_alpha is not None:
                _overlay_spec_alpha_masks["fourth_overlay_spec_pattern_stack"] = np.clip(_fb_alpha, 0.0, 1.0).astype(np.float32)
        except Exception as e:
            logger.warning("compose_finish: fourth_base overlay failed for '%s': %s", fourth_base, e)

    if fifth_base and fifth_base_strength > 0.001 and fifth_base_spec_strength > 1e-6:
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
                    _fif_result = _cached_base_spec_result(fifth_base, _fif_def["base_spec_fn"], shape, _fif_seed + _fif_seed_off, sm, _fif_M, _fif_R)
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
                # SPB-2026-05-19 owner: per-overlay Spec Scale parity knob
                if abs(float(fifth_base_spec_scale) - 1.0) > 0.01:
                    _fif_M_arr, _fif_R_arr, _fif_CC_arr = _apply_base_scale_to_spec_channels(
                        _fif_M_arr, _fif_R_arr, _fif_CC_arr, shape, float(fifth_base_spec_scale)
                    )
                _fif_M_final = _fif_M_arr * mask + 5.0 * (1 - mask)
                _fif_R_final = _fif_R_arr * mask + 100.0 * (1 - mask)
                spec_quinary[:,:,0] = np.clip(_fif_M_final, 0, 255).astype(np.uint8)
                spec_quinary[:,:,1] = _ggx_safe_R(_fif_R_final, _fif_M_final).astype(np.uint8)
                spec_quinary[:,:,2] = np.clip(_fif_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_quinary[:,:,3] = 255
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = _resolve_overlay_pattern_mask_id(
                fifth_base_pattern, pattern_id, fifth_base_blend_mode
            )
            _fif_pat_scale, _fif_pat_rot, _fif_pat_ox, _fif_pat_oy = _resolve_overlay_pattern_transform(
                fifth_base_pattern, _pat_id_fif, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                fifth_base_pattern_scale, fifth_base_pattern_rotation,
                fifth_base_pattern_offset_x, fifth_base_pattern_offset_y,
            )
            _fif_pattern_mask = _get_pattern_mask(_pat_id_fif, shape, mask, seed, sm,
                scale=_fif_pat_scale, rotation=_fif_pat_rot,
                opacity=fifth_base_pattern_opacity, strength=fifth_base_pattern_strength,
                offset_x=_fif_pat_ox, offset_y=_fif_pat_oy) if _pat_id_fif else None
            if _fif_pattern_mask is not None:
                if fifth_base_pattern_invert:
                    _fif_pattern_mask = 1.0 - _fif_pattern_mask
                if fifth_base_pattern_harden:
                    _fif_pattern_mask = _harden_overlay_pattern_mask(_fif_pattern_mask)
            spec, _fif_alpha = blend_dual_base_spec(
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
            if _fif_alpha is not None:
                _overlay_spec_alpha_masks["fifth_overlay_spec_pattern_stack"] = np.clip(_fif_alpha, 0.0, 1.0).astype(np.float32)
        except Exception as e:
            logger.warning("compose_finish: fifth_base overlay failed for '%s': %s", fifth_base, e)

    # --- Overlay Spec Pattern Stack (applied after all base blending) ---
    _overlay_spec_patterns = kwargs.get("overlay_spec_pattern_stack", [])
    if _overlay_spec_patterns:
        try:
            _overlay_spec_target_mask = _overlay_spec_alpha_masks.get("overlay_spec_pattern_stack", np.zeros_like(mask, dtype=np.float32))
            # SPB-USER-2026-05-27 spec-overlay audit: owner observed that
            # "SPEC PATTERNS are supposed to overlay the BASE SPEC PATTERN".
            # If no second-base overlay supplied an alpha mask, the previous
            # writeback mask stayed all-zero, so overlay spec layers rendered
            # but could not affect the base spec at all (regression: C delta
            # 0 -> visible channel delta in tests).
            # [SPB-OVERLAY-PARITY 2026-08-20] ...but only when NO overlay base is
            # authored on this tier. A zero alpha from an authored overlay means
            # the buyer turned it OFF - flooding the zone made spec_strength=0
            # measurably WORSE than 20%.
            if float(np.max(_overlay_spec_target_mask)) <= 0.001 and not second_base:
                _overlay_spec_target_mask = np.asarray(mask, dtype=np.float32)
            from engine.spec_patterns import PATTERN_CATALOG
            # Work on float32 M/R/CC extracted from spec
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _overlay_spec_patterns:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = _get_spec_pattern_fn_or_skip(
                    PATTERN_CATALOG,
                    _ovsp_name,
                    "overlay_spec_pattern_stack",
                )
                if _ovsp_fn is None:
                    continue
                if _spec_overlay_version(_ovsp, _ovsp_fn) >= 2:
                    continue
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _spec_overlay_opacity(_ovsp, _ovsp_fn)
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MRC")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = _spec_overlay_seed(_ovsp, _ovsp_fn, seed, 7000)
                _ovsp_arr = _cached_spec_pattern_array(
                    _ovsp_fn, _ovsp_name, (int(shape[0]), int(shape[1])),
                    _ovsp_seed, sm, _ovsp_params,
                    _ovsp_scale, _ovsp_rotation, _ovsp_offset_x, _ovsp_offset_y, _ovsp_box_size,
                )
                _ov_M, _ov_R, _ov_CC = _apply_spec_pattern_to_channels(
                    _ovsp_arr, _ov_M, _ov_R, _ov_CC,
                    _ovsp_range, _ovsp_opacity, _ovsp_blend, _ovsp_channels,
                )
            # Write back through this overlay layer's actual alpha, not the whole zone.
            spec[:,:,0] = np.clip(_ov_M * _overlay_spec_target_mask + spec[:,:,0].astype(np.float32) * (1 - _overlay_spec_target_mask), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * _overlay_spec_target_mask + spec[:,:,1].astype(np.float32) * (1 - _overlay_spec_target_mask), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * _overlay_spec_target_mask + spec[:,:,2].astype(np.float32) * (1 - _overlay_spec_target_mask), 0, 255).astype(np.uint8)
        except Exception as e:
            raise RuntimeError(f"Overlay spec pattern stack failed: {e}") from e

    def _apply_named_overlay_spec_stack(stack_key, seed_offset):
        _stack = kwargs.get(stack_key, [])
        if not _stack:
            return
        try:
            _overlay_spec_target_mask = _overlay_spec_alpha_masks.get(stack_key, np.zeros_like(mask, dtype=np.float32))
            # SPB-USER-2026-05-27: when an overlay spec stack is authored
            # without its matching base overlay, blend it over the current
            # base spec instead of writing through an all-zero alpha mask.
            # [SPB-OVERLAY-PARITY 2026-08-20] authored-but-zeroed tiers stay OFF.
            _authored = {"overlay_spec_pattern_stack": second_base,
                         "third_overlay_spec_pattern_stack": third_base,
                         "fourth_overlay_spec_pattern_stack": fourth_base,
                         "fifth_overlay_spec_pattern_stack": fifth_base}.get(stack_key)
            if float(np.max(_overlay_spec_target_mask)) <= 0.001 and not _authored:
                _overlay_spec_target_mask = np.asarray(mask, dtype=np.float32)
            from engine.spec_patterns import PATTERN_CATALOG
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _stack:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = _get_spec_pattern_fn_or_skip(PATTERN_CATALOG, _ovsp_name, stack_key)
                if _ovsp_fn is None:
                    continue
                if _spec_overlay_version(_ovsp, _ovsp_fn) >= 2:
                    continue
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _spec_overlay_opacity(_ovsp, _ovsp_fn)
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MRC")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = _spec_overlay_seed(_ovsp, _ovsp_fn, seed, seed_offset)
                _ovsp_arr = _cached_spec_pattern_array(
                    _ovsp_fn, _ovsp_name, (int(shape[0]), int(shape[1])),
                    _ovsp_seed, sm, _ovsp_params,
                    _ovsp_scale, _ovsp_rotation, _ovsp_offset_x, _ovsp_offset_y, _ovsp_box_size,
                )
                _ov_M, _ov_R, _ov_CC = _apply_spec_pattern_to_channels(
                    _ovsp_arr, _ov_M, _ov_R, _ov_CC,
                    _ovsp_range, _ovsp_opacity, _ovsp_blend, _ovsp_channels,
                )
            spec[:,:,0] = np.clip(_ov_M * _overlay_spec_target_mask + spec[:,:,0].astype(np.float32) * (1 - _overlay_spec_target_mask), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * _overlay_spec_target_mask + spec[:,:,1].astype(np.float32) * (1 - _overlay_spec_target_mask), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * _overlay_spec_target_mask + spec[:,:,2].astype(np.float32) * (1 - _overlay_spec_target_mask), 0, 255).astype(np.uint8)
        except Exception as e:
            raise RuntimeError(f"Named overlay spec pattern stack failed [{stack_key}]: {e}") from e

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

    return _apply_spec_overlay_v2_stacks(
        spec, _spec_patterns, kwargs, mask, seed, sm,
        _overlay_spec_alpha_masks, (second_base, third_base, fourth_base, fifth_base))


def compose_finish_stacked(base_id, all_patterns, shape, mask, seed, sm, spec_mult=1.0, base_scale=1.0, base_strength=1.0, base_spec_strength=1.0, base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0, base_flip_h=False, base_flip_v=False, pattern_opacity=1.0, cc_quality=None, blend_base=None, blend_dir="horizontal", blend_amount=0.5, paint_color=None,
                           second_base=None, second_base_color=None, second_base_strength=0.0, second_base_spec_strength=1.0, second_base_rotation=0.0, second_base_spec_rotation=0.0,
                           second_base_blend_mode="noise", second_base_noise_scale=24,
                           second_base_scale=1.0, second_base_color_scale=1.0, second_base_spec_scale=1.0, second_base_pattern=None,
                           second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                           second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                           second_base_pattern_invert=False, second_base_pattern_harden=False,
                           third_base=None, third_base_color=None, third_base_strength=0.0, third_base_spec_strength=1.0, third_base_rotation=0.0, third_base_spec_rotation=0.0,
                           third_base_blend_mode="noise", third_base_noise_scale=24,
                           third_base_scale=1.0, third_base_color_scale=1.0, third_base_spec_scale=1.0, third_base_pattern=None,
                           third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                           third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                           third_base_pattern_invert=False, third_base_pattern_harden=False,
                           second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                           third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                           fourth_base=None, fourth_base_color=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0, fourth_base_rotation=0.0, fourth_base_spec_rotation=0.0,
                           fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                           fourth_base_scale=1.0, fourth_base_color_scale=1.0, fourth_base_spec_scale=1.0, fourth_base_pattern=None,
                           fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                           fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                           fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                           fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                           fifth_base=None, fifth_base_color=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0, fifth_base_rotation=0.0, fifth_base_spec_rotation=0.0,
                           fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                           fifth_base_scale=1.0, fifth_base_color_scale=1.0, fifth_base_spec_scale=1.0, fifth_base_pattern=None,
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
    pattern_fit_zone = bool(kwargs.get("pattern_fit_zone", False))
    _stacked_primary_pat = (
        all_patterns[0].get("id")
        if all_patterns and isinstance(all_patterns[0], dict)
        else (all_patterns[0] if all_patterns else None)
    )
    _stk_pri_scale = float(all_patterns[0].get("scale", 1.0)) if all_patterns and isinstance(all_patterns[0], dict) else 1.0
    _stk_pri_rot = float(all_patterns[0].get("rotation", 0.0)) if all_patterns and isinstance(all_patterns[0], dict) else 0.0
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

    base_shape, _base_spec_tile_after = _base_spec_generation_shape(shape, base_scale)

    CC_arr = None
    _bss = max(0.0, min(2.0, float(base_spec_strength)))
    _base_seed_offset = abs(hash(base_id)) % 10000
    effective_base_CC = _scale_base_clearcoat_scalar(base_CC, _bss)
    if base.get("base_spec_fn"):
        spec_result = _cached_base_spec_result(base_id, base["base_spec_fn"], base_shape, seed + _base_seed_offset, _sm_base, base_M, base_R)
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

    if _base_spec_tile_after or (
        base_scale > 1.0 and (base_shape[0] != shape[0] or base_shape[1] != shape[1])
    ):
        M_arr, R_arr, CC_arr = _apply_base_scale_to_spec_channels(
            M_arr, R_arr, CC_arr, shape, base_scale
        )

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
    kwargs = _spec_active_options(kwargs)
    _spec_patterns = _spec_active_layers(kwargs.get("spec_pattern_stack", []) or base.get("spec_pattern_stack", []))
    if _spec_patterns:
        from engine.spec_patterns import PATTERN_CATALOG
        for sp_layer in _spec_patterns:
            sp_name = sp_layer.get("pattern", "")
            sp_fn = _get_spec_pattern_fn_or_skip(PATTERN_CATALOG, sp_name, "spec_pattern_stack")
            if sp_fn is None:
                continue
            # SPB-105 / v2 tick 1: new overlays follow the completed material.
            if _spec_overlay_version(sp_layer, sp_fn) >= 2:
                continue
            sp_opacity_raw = float(sp_layer.get("opacity", 0.5))
            sp_opacity = _spec_overlay_opacity(sp_layer, sp_fn)
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
            _sp_seed = _spec_overlay_seed(sp_layer, sp_fn, seed, 5000)
            # Cap sm at 1.0 to satisfy the spec-pattern compression contract.
            # See matching fix in compose_finish above.
            _sp_sm = min(1.0, float(_sm_base))
            # SPB-2026-05-19 owner: see matching fix in compose_finish — spec pattern
            # stack must run at composed `shape` (not base_shape) so it broadcasts
            # correctly against the resized M_arr/R_arr/CC_arr when base_scale > 1.
            _sp_shape = (int(shape[0]), int(shape[1]))
            sp_arr = _cached_spec_pattern_array(
                sp_fn, sp_name, _sp_shape, _sp_seed, _sp_sm, sp_params,
                sp_scale, sp_rotation, sp_offset_x, sp_offset_y, sp_box_size,
            )
            if _gpu_active:
                sp_arr = to_gpu(sp_arr)
            sp_range = float(sp_layer.get("range", 40.0))
            M_arr, R_arr, CC_arr = _apply_spec_pattern_to_channels(
                sp_arr, M_arr, R_arr, CC_arr,
                sp_range, sp_opacity, sp_blend, sp_channels,
            )

    if CC_arr is not None:
        final_CC = CC_arr.copy()
    else:
        final_CC = xp.full(shape, float(effective_base_CC), dtype=xp.float32)

    _mask_cpu_stk = to_cpu(mask) if _gpu_active else mask
    for layer_idx, layer in enumerate([] if kwargs.get("independent_pattern_spec", False) else all_patterns):
        pat_id = layer["id"]
        opacity = float(layer.get("opacity", 1.0))
        scale = float(layer.get("scale", 1.0))
        layer_fit_zone = bool(layer.get("fit_zone", pattern_fit_zone))
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
                if layer_fit_zone:
                    pv = _fit_pattern_to_mask_bbox(pv, _mask_cpu_stk)
                if _gpu_active:
                    pv = to_gpu(pv)
                pv_masked = pv * mask
                _eff_blend = base_spec_blend_mode if base_spec_blend_mode != "normal" else layer.get("blend_mode", "normal")
                if _eff_blend in PHYSICAL_SPEC_BLEND_MODES:
                    M_arr, R_arr, final_CC = apply_physical_spec_blend(
                        M_arr, R_arr, final_CC, _normalize_pattern_field(pv_masked),
                        opacity * pattern_sm_eff, _eff_blend)
                else:
                    M_contrib = pv_masked * 50.0 * pattern_sm_eff * spec_mult
                    R_contrib = pv_masked * 60.0 * pattern_sm_eff * spec_mult
                    M_arr = _apply_spec_blend_mode(M_arr, M_contrib, opacity, _eff_blend)
                    R_arr = _apply_spec_blend_mode(R_arr, R_contrib, opacity, _eff_blend)
            continue
        if tex_fn is None:
            continue
        layer_seed = seed + layer_idx * 7
        try:
            tex = tex_fn(shape, _mask_cpu_stk, layer_seed, sm)
        except Exception as _tex_err_stk:
            raise RuntimeError(
                f"Stacked pattern texture renderer failed [{pat_id}]: {_tex_err_stk}"
            ) from _tex_err_stk
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
        if layer_fit_zone:
            _pv_before_fit = pv
            pv = _fit_pattern_to_mask_bbox(pv, _mask_cpu_stk)
            if M_pv is _pv_before_fit:
                M_pv = pv
            elif M_pv is not None:
                M_pv = _fit_pattern_to_mask_bbox(M_pv, _mask_cpu_stk)
            if R_pv is _pv_before_fit:
                R_pv = pv
            elif R_pv is not None:
                R_pv = _fit_pattern_to_mask_bbox(R_pv, _mask_cpu_stk)
            if CC_pv is not None:
                CC_pv = _fit_pattern_to_mask_bbox(CC_pv, _mask_cpu_stk)
        # Transfer pattern arrays to GPU for blending
        if _gpu_active:
            M_pv = to_gpu(M_pv)
            R_pv = to_gpu(R_pv)
            if CC_pv is not None:
                CC_pv = to_gpu(CC_pv)
        _effective_spec_blend = base_spec_blend_mode if base_spec_blend_mode != "normal" else blend_mode
        if _effective_spec_blend in PHYSICAL_SPEC_BLEND_MODES:
            # physical modes own ALL THREE channels for this layer (the legacy
            # per-channel contributions + additive CC are superseded).
            # Normalize on CPU then transfer — pv is CPU here while mask may be
            # GPU, and mixing the two throws on GPU-active machines.
            _pv_phys = _normalize_pattern_field(np.asarray(pv, np.float32))
            if _gpu_active:
                _pv_phys = to_gpu(_pv_phys)
            M_arr, R_arr, final_CC = apply_physical_spec_blend(
                M_arr, R_arr, final_CC, _pv_phys * mask,
                opacity * pattern_sm_eff, _effective_spec_blend)
            continue
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
    _dither_rng = _DitherPlanes(seed if seed else 42) if dither else None  # [gauntlet 2026-07-04] cached planes, bit-identical
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

    _stack_default_pattern = (all_patterns[0].get("id") if all_patterns and isinstance(all_patterns[0], dict) else (all_patterns[0] if all_patterns else None))
    _overlay_spec_alpha_masks_stk = {
        "overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
        "third_overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
        "fourth_overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
        "fifth_overlay_spec_pattern_stack": np.zeros_like(mask, dtype=np.float32),
    }
    _weighted_overlay_layers = []
    for _ov in (
        {"base": second_base, "paint_strength": second_base_strength, "spec_strength": second_base_spec_strength, "blend_mode": second_base_blend_mode, "noise_scale": second_base_noise_scale, "scale": second_base_scale, "pattern": second_base_pattern, "pattern_scale": second_base_pattern_scale, "pattern_rotation": second_base_pattern_rotation, "pattern_opacity": second_base_pattern_opacity, "pattern_strength": second_base_pattern_strength, "pattern_invert": second_base_pattern_invert, "pattern_harden": second_base_pattern_harden, "pattern_offset_x": second_base_pattern_offset_x, "pattern_offset_y": second_base_pattern_offset_y, "seed": seed, "spec_seed": seed + 999, "spec_scale": second_base_spec_scale, "rotation": second_base_rotation, "spec_rotation": second_base_spec_rotation, "stack_key": "overlay_spec_pattern_stack"},
        {"base": third_base, "paint_strength": third_base_strength, "spec_strength": third_base_spec_strength, "blend_mode": third_base_blend_mode, "noise_scale": third_base_noise_scale, "scale": third_base_scale, "pattern": third_base_pattern, "pattern_scale": third_base_pattern_scale, "pattern_rotation": third_base_pattern_rotation, "pattern_opacity": third_base_pattern_opacity, "pattern_strength": third_base_pattern_strength, "pattern_invert": third_base_pattern_invert, "pattern_harden": third_base_pattern_harden, "pattern_offset_x": third_base_pattern_offset_x, "pattern_offset_y": third_base_pattern_offset_y, "seed": seed + 8888, "spec_seed": seed + 1999, "spec_scale": third_base_spec_scale, "rotation": third_base_rotation, "spec_rotation": third_base_spec_rotation, "stack_key": "third_overlay_spec_pattern_stack"},
        {"base": fourth_base, "paint_strength": fourth_base_strength, "spec_strength": fourth_base_spec_strength, "blend_mode": fourth_base_blend_mode, "noise_scale": fourth_base_noise_scale, "scale": fourth_base_scale, "pattern": fourth_base_pattern, "pattern_scale": fourth_base_pattern_scale, "pattern_rotation": fourth_base_pattern_rotation, "pattern_opacity": fourth_base_pattern_opacity, "pattern_strength": fourth_base_pattern_strength, "pattern_invert": fourth_base_pattern_invert, "pattern_harden": fourth_base_pattern_harden, "pattern_offset_x": fourth_base_pattern_offset_x, "pattern_offset_y": fourth_base_pattern_offset_y, "seed": seed + 9999, "spec_seed": seed + 2999, "spec_scale": fourth_base_spec_scale, "rotation": fourth_base_rotation, "spec_rotation": fourth_base_spec_rotation, "stack_key": "fourth_overlay_spec_pattern_stack"},
        {"base": fifth_base, "paint_strength": fifth_base_strength, "spec_strength": fifth_base_spec_strength, "blend_mode": fifth_base_blend_mode, "noise_scale": fifth_base_noise_scale, "scale": fifth_base_scale, "pattern": fifth_base_pattern, "pattern_scale": fifth_base_pattern_scale, "pattern_rotation": fifth_base_pattern_rotation, "pattern_opacity": fifth_base_pattern_opacity, "pattern_strength": fifth_base_pattern_strength, "pattern_invert": fifth_base_pattern_invert, "pattern_harden": fifth_base_pattern_harden, "pattern_offset_x": fifth_base_pattern_offset_x, "pattern_offset_y": fifth_base_pattern_offset_y, "seed": seed + 10999, "spec_seed": seed + 3999, "spec_scale": fifth_base_spec_scale, "rotation": fifth_base_rotation, "spec_rotation": fifth_base_spec_rotation, "stack_key": "fifth_overlay_spec_pattern_stack"},
    ):
        # [SPB-OVERLAY-PARITY 2026-08-20] This loop builds the overlay's SPEC
        # contribution, so it is gated by SPEC strength. It used to gate on PAINT
        # strength, which made a spec-only overlay (paint 0, spec 100) impossible
        # and let the paint slider silently switch the whole material layer off.
        if not _ov["base"] or float(_ov["spec_strength"] or 0.0) <= 1e-6:
            continue
        try:
            _ov_spec, _ = _build_base_overlay_spec_for_weight_mix(
                _ov["base"], shape, mask,
                _ov["spec_seed"] + abs(hash(_ov["base"])) % 10000,
                sm, BASE_REGISTRY, monolithic_registry,
                spec_scale=float(_ov.get("spec_scale", 1.0) or 1.0),
                rotation=float(_ov.get("rotation", 0.0) or 0.0),
                spec_rotation=float(_ov.get("spec_rotation", 0.0) or 0.0),
            )
            if _ov_spec is None:
                continue
            _pat_id_ov = _resolve_overlay_pattern_mask_id(
                _ov["pattern"], _stack_default_pattern, _ov["blend_mode"]
            )
            _ov_pattern_mask = _get_pattern_mask(
                _pat_id_ov, shape, mask, seed, sm,
                scale=_ov["pattern_scale"], rotation=_ov["pattern_rotation"],
                opacity=_ov["pattern_opacity"], strength=_ov["pattern_strength"],
                offset_x=_ov["pattern_offset_x"], offset_y=_ov["pattern_offset_y"],
            ) if _pat_id_ov else None
            if _ov_pattern_mask is not None:
                if _ov["pattern_invert"]:
                    _ov_pattern_mask = 1.0 - _ov_pattern_mask
                if _ov["pattern_harden"]:
                    _ov_pattern_mask = _harden_overlay_pattern_mask(_ov_pattern_mask)
            _weighted_overlay_layers.append({
                "spec": _ov_spec,
                "strength": _ov["spec_strength"],
                "blend_mode": _ov["blend_mode"],
                "noise_scale": _ov["noise_scale"],
                "seed": _ov["seed"],
                "pattern_mask": _ov_pattern_mask,
                "overlay_scale": _ov["scale"],
                "stack_key": _ov["stack_key"],
            })
        except Exception as _ov_mix_err:
            logger.warning("compose_finish_stacked: weighted overlay prepare failed for '%s': %s", _ov["base"], _ov_mix_err)
    if _weighted_overlay_layers:
        spec = _weighted_mix_base_overlay_specs(spec, _weighted_overlay_layers, shape, mask)
        for _layer in _weighted_overlay_layers:
            _stack_key = _layer.get("stack_key")
            _layer_alpha = _layer.get("_overlay_alpha")
            if _stack_key in _overlay_spec_alpha_masks_stk and _layer_alpha is not None:
                _overlay_spec_alpha_masks_stk[_stack_key] = np.maximum(
                    _overlay_spec_alpha_masks_stk[_stack_key],
                    np.clip(_layer_alpha, 0.0, 1.0).astype(np.float32),
                )
        second_base_strength = third_base_strength = fourth_base_strength = fifth_base_strength = 0.0

    if second_base and second_base_strength > 0.001 and second_base_spec_strength > 1e-6:
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
                    _sb_result = _cached_base_spec_result(second_base, _sb_def["base_spec_fn"], shape, _sb_seed + _sb_seed_off, sm, _sb_M, _sb_R)
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
            _pat_id = _resolve_overlay_pattern_mask_id(
                second_base_pattern, pattern_id, second_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            pattern_mask = _get_overlay_pattern_mask(
                second_base_pattern, _pat_id, _stacked_primary_pat or pattern_id,
                float(all_patterns[0].get("scale", 1.0)) if all_patterns and isinstance(all_patterns[0], dict) else 1.0,
                float(all_patterns[0].get("rotation", 0.0)) if all_patterns and isinstance(all_patterns[0], dict) else 0.0,
                pattern_offset_x, pattern_offset_y,
                second_base_pattern_scale, second_base_pattern_rotation,
                second_base_pattern_offset_x, second_base_pattern_offset_y,
                shape, mask, seed, sm,
                second_base_pattern_opacity, second_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if pattern_mask is not None:
                if second_base_pattern_invert:
                    pattern_mask = 1.0 - pattern_mask
                if second_base_pattern_harden:
                    pattern_mask = _harden_overlay_pattern_mask(pattern_mask)
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
            if _sb_alpha is not None:
                _overlay_spec_alpha_masks_stk["overlay_spec_pattern_stack"] = np.clip(_sb_alpha, 0.0, 1.0).astype(np.float32)
            # [SPB-OVERLAY-PARITY 2026-08-20] A 27-line "PAINT OVERLAY" block lived
            # here referencing `paint` and `hard_mask` - names that do not exist in
            # compose_finish_stacked (it is SPEC-only; paint is composed by
            # compose_paint_mod_stacked). Every run raised NameError into the
            # swallowing except below and printed a bogus warning. Removed.
        except Exception as _sb_err:
            print(f"[compose] WARNING: second base overlay failed: {_sb_err}")
            import traceback; traceback.print_exc()

    if third_base and third_base_strength > 0.001 and third_base_spec_strength > 1e-6:
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
                    _tb_result = _cached_base_spec_result(third_base, _tb_def["base_spec_fn"], shape, _tb_seed + _tb_seed_off, sm, _tb_M, _tb_R)
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
                # SPB-2026-05-19 owner: per-overlay Spec Scale parity knob
                if abs(float(third_base_spec_scale) - 1.0) > 0.01:
                    _tb_M_arr, _tb_R_arr, _tb_CC_arr = _apply_base_scale_to_spec_channels(
                        _tb_M_arr, _tb_R_arr, _tb_CC_arr, shape, float(third_base_spec_scale)
                    )
                _tb_M_final = _tb_M_arr * mask + 5.0 * (1 - mask)
                _tb_R_final = _tb_R_arr * mask + 100.0 * (1 - mask)
                spec_tertiary[:,:,0] = np.clip(_tb_M_final, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,1] = _ggx_safe_R(_tb_R_final, _tb_M_final).astype(np.uint8)
                spec_tertiary[:,:,2] = np.clip(_tb_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_tertiary[:,:,3] = 255
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = _resolve_overlay_pattern_mask_id(
                third_base_pattern, pattern_id, third_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            _tb_pattern_mask = _get_overlay_pattern_mask(
                third_base_pattern, _pat_id_tb, _stacked_primary_pat or pattern_id,
                _stk_pri_scale, _stk_pri_rot, pattern_offset_x, pattern_offset_y,
                third_base_pattern_scale, third_base_pattern_rotation,
                third_base_pattern_offset_x, third_base_pattern_offset_y,
                shape, mask, seed, sm,
                third_base_pattern_opacity, third_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _tb_pattern_mask is not None:
                if third_base_pattern_invert:
                    _tb_pattern_mask = 1.0 - _tb_pattern_mask
                if third_base_pattern_harden:
                    _tb_pattern_mask = _harden_overlay_pattern_mask(_tb_pattern_mask)
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
            if _tb_alpha is not None:
                _overlay_spec_alpha_masks_stk["third_overlay_spec_pattern_stack"] = np.clip(_tb_alpha, 0.0, 1.0).astype(np.float32)
            # Paint blend for 3rd overlay (stacked path)
            if third_base_strength > 0.001 and _tb_alpha is not None:
                _tb_paint_ov = paint.copy()
                if third_base_color is not None:
                    _tb_c = np.array(third_base_color[:3], dtype=np.float32).reshape(1,1,3)
                    _tb_paint_ov[:,:,:3] = _tb_paint_ov[:,:,:3] * (1.0 - hard_mask[:,:,np.newaxis]) + _tb_c * hard_mask[:,:,np.newaxis]
                # HSB adjustments for 3rd overlay — parity with 2nd base (2026-05-30 owner fix; gated, no-op when 0)
                if third_base_hue_shift or third_base_saturation or third_base_brightness:
                    _tb_paint_ov = _apply_hsb_adjustments(_tb_paint_ov, hard_mask, third_base_hue_shift, third_base_saturation, third_base_brightness)
                _tb_pa = np.clip(_tb_alpha * third_base_strength, 0, 1)[:,:,np.newaxis]
                paint[:,:,:3] = paint[:,:,:3] * (1.0 - _tb_pa) + _tb_paint_ov[:,:,:3] * _tb_pa
        except Exception as _e3:
            print(f"[compose] WARNING: 3rd overlay failed: {_e3}")

    if fourth_base and fourth_base_strength > 0.001 and fourth_base_spec_strength > 1e-6:
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
                    _fb_result = _cached_base_spec_result(fourth_base, _fb_def["base_spec_fn"], shape, _fb_seed + _fb_seed_off, sm, _fb_M, _fb_R)
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
            _pat_id_fb = _resolve_overlay_pattern_mask_id(
                fourth_base_pattern, pattern_id, fourth_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            _fb_pattern_mask = _get_overlay_pattern_mask(
                fourth_base_pattern, _pat_id_fb, _stacked_primary_pat or pattern_id,
                _stk_pri_scale, _stk_pri_rot, pattern_offset_x, pattern_offset_y,
                fourth_base_pattern_scale, fourth_base_pattern_rotation,
                fourth_base_pattern_offset_x, fourth_base_pattern_offset_y,
                shape, mask, seed, sm,
                fourth_base_pattern_opacity, fourth_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _fb_pattern_mask is not None:
                if fourth_base_pattern_invert:
                    _fb_pattern_mask = 1.0 - _fb_pattern_mask
                if fourth_base_pattern_harden:
                    _fb_pattern_mask = _harden_overlay_pattern_mask(_fb_pattern_mask)
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
            if _fb_alpha is not None:
                _overlay_spec_alpha_masks_stk["fourth_overlay_spec_pattern_stack"] = np.clip(_fb_alpha, 0.0, 1.0).astype(np.float32)
            # Paint blend for 4th overlay (stacked path)
            if fourth_base_strength > 0.001 and _fb_alpha is not None:
                _fb_paint_ov = paint.copy()
                if fourth_base_color is not None:
                    _fb_c = np.array(fourth_base_color[:3], dtype=np.float32).reshape(1,1,3)
                    _fb_paint_ov[:,:,:3] = _fb_paint_ov[:,:,:3] * (1.0 - hard_mask[:,:,np.newaxis]) + _fb_c * hard_mask[:,:,np.newaxis]
                # HSB adjustments for 4th overlay — parity with 2nd base (2026-05-30 owner fix; gated, no-op when 0)
                if fourth_base_hue_shift or fourth_base_saturation or fourth_base_brightness:
                    _fb_paint_ov = _apply_hsb_adjustments(_fb_paint_ov, hard_mask, fourth_base_hue_shift, fourth_base_saturation, fourth_base_brightness)
                _fb_pa = np.clip(_fb_alpha * fourth_base_strength, 0, 1)[:,:,np.newaxis]
                paint[:,:,:3] = paint[:,:,:3] * (1.0 - _fb_pa) + _fb_paint_ov[:,:,:3] * _fb_pa
        except Exception as _e4:
            print(f"[compose] WARNING: 4th overlay failed: {_e4}")

    if fifth_base and fifth_base_strength > 0.001 and fifth_base_spec_strength > 1e-6:
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
                    _fif_result = _cached_base_spec_result(fifth_base, _fif_def["base_spec_fn"], shape, _fif_seed + _fif_seed_off, sm, _fif_M, _fif_R)
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
                # SPB-2026-05-19 owner: per-overlay Spec Scale parity knob
                if abs(float(fifth_base_spec_scale) - 1.0) > 0.01:
                    _fif_M_arr, _fif_R_arr, _fif_CC_arr = _apply_base_scale_to_spec_channels(
                        _fif_M_arr, _fif_R_arr, _fif_CC_arr, shape, float(fifth_base_spec_scale)
                    )
                spec_fifth[:,:,0] = np.clip(_fif_M_arr * mask + 5.0 * (1 - mask), 0, 255).astype(np.uint8)
                spec_fifth[:,:,1] = np.clip(_fif_R_arr * mask + 100.0 * (1 - mask), 0, 255).astype(np.uint8)
                spec_fifth[:,:,2] = np.clip(_fif_CC_arr * mask, 0, 255).astype(np.uint8)
                spec_fifth[:,:,3] = 255
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = _resolve_overlay_pattern_mask_id(
                fifth_base_pattern, pattern_id, fifth_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            _fif_pattern_mask = _get_overlay_pattern_mask(
                fifth_base_pattern, _pat_id_fif, _stacked_primary_pat or pattern_id,
                _stk_pri_scale, _stk_pri_rot, pattern_offset_x, pattern_offset_y,
                fifth_base_pattern_scale, fifth_base_pattern_rotation,
                fifth_base_pattern_offset_x, fifth_base_pattern_offset_y,
                shape, mask, seed, sm,
                fifth_base_pattern_opacity, fifth_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _fif_pattern_mask is not None:
                if fifth_base_pattern_invert:
                    _fif_pattern_mask = 1.0 - _fif_pattern_mask
                if fifth_base_pattern_harden:
                    _fif_pattern_mask = _harden_overlay_pattern_mask(_fif_pattern_mask)
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
            if _fif_alpha is not None:
                _overlay_spec_alpha_masks_stk["fifth_overlay_spec_pattern_stack"] = np.clip(_fif_alpha, 0.0, 1.0).astype(np.float32)
            # Paint blend for 5th overlay (stacked path)
            if fifth_base_strength > 0.001 and _fif_alpha is not None:
                _fif_paint_ov = paint.copy()
                if fifth_base_color is not None:
                    _fif_c = np.array(fifth_base_color[:3], dtype=np.float32).reshape(1,1,3)
                    _fif_paint_ov[:,:,:3] = _fif_paint_ov[:,:,:3] * (1.0 - hard_mask[:,:,np.newaxis]) + _fif_c * hard_mask[:,:,np.newaxis]
                # HSB adjustments for 5th overlay — parity with 2nd base (2026-05-30 owner fix; gated, no-op when 0)
                if fifth_base_hue_shift or fifth_base_saturation or fifth_base_brightness:
                    _fif_paint_ov = _apply_hsb_adjustments(_fif_paint_ov, hard_mask, fifth_base_hue_shift, fifth_base_saturation, fifth_base_brightness)
                _fif_pa = np.clip(_fif_alpha * fifth_base_strength, 0, 1)[:,:,np.newaxis]
                paint[:,:,:3] = paint[:,:,:3] * (1.0 - _fif_pa) + _fif_paint_ov[:,:,:3] * _fif_pa
        except Exception as _e5:
            print(f"[compose] WARNING: 5th overlay failed: {_e5}")

    # --- Overlay Spec Pattern Stack (applied after all base blending) ---
    _overlay_spec_patterns_stk = kwargs.get("overlay_spec_pattern_stack", [])
    if _overlay_spec_patterns_stk:
        try:
            _overlay_spec_target_mask_stk = _overlay_spec_alpha_masks_stk.get("overlay_spec_pattern_stack", np.zeros_like(mask, dtype=np.float32))
            # SPB-USER-2026-05-27 parity with compose_finish: standalone
            # overlay spec stacks must affect the existing/base spec when no
            # overlay-base alpha exists (focused test: zero delta -> visible).
            # [SPB-OVERLAY-PARITY 2026-08-20] authored-but-zeroed tiers stay OFF.
            if float(np.max(_overlay_spec_target_mask_stk)) <= 0.001 and not second_base:
                _overlay_spec_target_mask_stk = np.asarray(mask, dtype=np.float32)
            from engine.spec_patterns import PATTERN_CATALOG
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _overlay_spec_patterns_stk:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = _get_spec_pattern_fn_or_skip(
                    PATTERN_CATALOG,
                    _ovsp_name,
                    "overlay_spec_pattern_stack",
                )
                if _ovsp_fn is None:
                    continue
                if _spec_overlay_version(_ovsp, _ovsp_fn) >= 2:
                    continue
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _spec_overlay_opacity(_ovsp, _ovsp_fn)
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MRC")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = _spec_overlay_seed(_ovsp, _ovsp_fn, seed, 7000)
                _ovsp_arr = _cached_spec_pattern_array(
                    _ovsp_fn, _ovsp_name, (int(shape[0]), int(shape[1])),
                    _ovsp_seed, sm, _ovsp_params,
                    _ovsp_scale, _ovsp_rotation, _ovsp_offset_x, _ovsp_offset_y, _ovsp_box_size,
                )
                _ov_M, _ov_R, _ov_CC = _apply_spec_pattern_to_channels(
                    _ovsp_arr, _ov_M, _ov_R, _ov_CC,
                    _ovsp_range, _ovsp_opacity, _ovsp_blend, _ovsp_channels,
                )
            spec[:,:,0] = np.clip(_ov_M * _overlay_spec_target_mask_stk + spec[:,:,0].astype(np.float32) * (1 - _overlay_spec_target_mask_stk), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * _overlay_spec_target_mask_stk + spec[:,:,1].astype(np.float32) * (1 - _overlay_spec_target_mask_stk), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * _overlay_spec_target_mask_stk + spec[:,:,2].astype(np.float32) * (1 - _overlay_spec_target_mask_stk), 0, 255).astype(np.uint8)
        except Exception as e:
            raise RuntimeError(f"Overlay spec pattern stack failed: {e}") from e

    def _apply_named_overlay_spec_stack_stk(stack_key, seed_offset):
        _stack = kwargs.get(stack_key, [])
        if not _stack:
            return
        try:
            _overlay_spec_target_mask_stk = _overlay_spec_alpha_masks_stk.get(stack_key, np.zeros_like(mask, dtype=np.float32))
            # SPB-USER-2026-05-27 parity with compose_finish named stacks:
            # fall back to the zone mask instead of a silent all-zero writeback.
            # [SPB-OVERLAY-PARITY 2026-08-20] authored-but-zeroed tiers stay OFF.
            _authored = {"overlay_spec_pattern_stack": second_base,
                         "third_overlay_spec_pattern_stack": third_base,
                         "fourth_overlay_spec_pattern_stack": fourth_base,
                         "fifth_overlay_spec_pattern_stack": fifth_base}.get(stack_key)
            if float(np.max(_overlay_spec_target_mask_stk)) <= 0.001 and not _authored:
                _overlay_spec_target_mask_stk = np.asarray(mask, dtype=np.float32)
            from engine.spec_patterns import PATTERN_CATALOG
            _ov_M = spec[:,:,0].astype(np.float32)
            _ov_R = spec[:,:,1].astype(np.float32)
            _ov_CC = spec[:,:,2].astype(np.float32)
            for _ovsp in _stack:
                _ovsp_name = _ovsp.get("pattern", "")
                _ovsp_fn = _get_spec_pattern_fn_or_skip(PATTERN_CATALOG, _ovsp_name, stack_key)
                if _ovsp_fn is None:
                    continue
                if _spec_overlay_version(_ovsp, _ovsp_fn) >= 2:
                    continue
                _ovsp_opacity_raw = float(_ovsp.get("opacity", 0.5))
                # Perceptual sqrt curve: low slider values still produce visible spec shifts
                # 5%→22%, 10%→32%, 30%→55%, 50%→71%, 100%→100%
                _ovsp_opacity = _spec_overlay_opacity(_ovsp, _ovsp_fn)
                _ovsp_blend = _ovsp.get("blend_mode", "normal")
                _ovsp_channels = _ovsp.get("channels", "MRC")
                _ovsp_offset_x = float(_ovsp.get("offset_x", 0.5))
                _ovsp_offset_y = float(_ovsp.get("offset_y", 0.5))
                _ovsp_scale = float(_ovsp.get("scale", 1.0))
                _ovsp_rotation = float(_ovsp.get("rotation", 0))
                _ovsp_box_size = int(_ovsp.get("box_size", 100))
                _ovsp_range = float(_ovsp.get("range", 60.0))  # was 40, boosted for visibility
                _ovsp_params = _ovsp.get("params", {})
                _ovsp_seed = _spec_overlay_seed(_ovsp, _ovsp_fn, seed, seed_offset)
                _ovsp_arr = _cached_spec_pattern_array(
                    _ovsp_fn, _ovsp_name, (int(shape[0]), int(shape[1])),
                    _ovsp_seed, sm, _ovsp_params,
                    _ovsp_scale, _ovsp_rotation, _ovsp_offset_x, _ovsp_offset_y, _ovsp_box_size,
                )
                _ov_M, _ov_R, _ov_CC = _apply_spec_pattern_to_channels(
                    _ovsp_arr, _ov_M, _ov_R, _ov_CC,
                    _ovsp_range, _ovsp_opacity, _ovsp_blend, _ovsp_channels,
                )
            spec[:,:,0] = np.clip(_ov_M * _overlay_spec_target_mask_stk + spec[:,:,0].astype(np.float32) * (1 - _overlay_spec_target_mask_stk), 0, 255).astype(np.uint8)
            spec[:,:,1] = np.clip(_ov_R * _overlay_spec_target_mask_stk + spec[:,:,1].astype(np.float32) * (1 - _overlay_spec_target_mask_stk), 0, 255).astype(np.uint8)
            spec[:,:,2] = np.clip(_ov_CC * _overlay_spec_target_mask_stk + spec[:,:,2].astype(np.float32) * (1 - _overlay_spec_target_mask_stk), 0, 255).astype(np.uint8)
        except Exception as e:
            raise RuntimeError(f"Named overlay spec pattern stack failed [{stack_key}]: {e}") from e

    _apply_named_overlay_spec_stack_stk("third_overlay_spec_pattern_stack", 8000)
    _apply_named_overlay_spec_stack_stk("fourth_overlay_spec_pattern_stack", 9000)
    _apply_named_overlay_spec_stack_stk("fifth_overlay_spec_pattern_stack", 10000)

    # Iron rule enforcement (final safety net): R>=15 for non-chrome (M<240), CC>=16 always.
    # In-place np.maximum with `where` avoids the extra astype / np.where round-trip.
    _non_chrome = spec[:, :, 0] < SPEC_METALLIC_CHROME_THRESHOLD
    np.maximum(spec[:, :, 1], SPEC_ROUGHNESS_MIN, out=spec[:, :, 1], where=_non_chrome)
    np.maximum(spec[:, :, 2], SPEC_CLEARCOAT_MIN, out=spec[:, :, 2])
    return _apply_spec_overlay_v2_stacks(
        spec, _spec_patterns, kwargs, mask, seed, sm,
        _overlay_spec_alpha_masks_stk, (second_base, third_base, fourth_base, fifth_base))


def _blend_base_result_over_source(source_paint, base_result, mask, strength):
    """Literal Base Strength contract: source at 0, complete base result at 1."""
    try:
        weight = max(0.0, min(1.0, float(strength)))
    except (TypeError, ValueError):
        weight = 1.0
    if weight >= 0.999:
        return base_result
    source = np.asarray(source_paint, dtype=np.float32)
    result = np.asarray(base_result, dtype=np.float32)
    out = np.array(result, dtype=np.float32, copy=True)
    alpha = np.clip(np.asarray(mask, dtype=np.float32) * weight, 0.0, 1.0)[:, :, np.newaxis]
    out[:, :, :3] = source[:, :, :3] * (1.0 - alpha) + result[:, :, :3] * alpha
    return out


# BUGFIX 2026-10-04 (encyclopedia pass, "suspected dead controls"): measured with real 2048
# renders (docs/handoff_reports/BUGFIX_2026-10-04.md) -- the Pro Strength Map and the
# per-layer pattern Blend dropdown changed the SPEC only; the PAINT was byte-identical for
# every setting (paint diff 0.000). These two helpers carry both controls into the paint.
_PAINT_LAYER_BLEND_MODES = ("multiply", "screen", "overlay", "hardlight", "softlight")


def _paint_strength_map_blend(before, after, strength_map):
    """Per-pixel pattern strength for PAINT: before + (after-before) * map (map 0..1, any size)."""
    if strength_map is None or before is None:
        return after
    try:
        arr = np.asarray(strength_map, dtype=np.float32)
        if arr.ndim != 2 or arr.size == 0:
            return after
        h, w = after.shape[:2]
        if arr.shape != (h, w):
            arr = cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR)
        k = np.clip(arr, 0.0, 1.0)[:, :, np.newaxis]
        out = np.array(after, dtype=np.float32, copy=True)
        out[:, :, :3] = before[:, :, :3] + (out[:, :, :3] - before[:, :, :3]) * k
        return out
    except Exception as _psm_paint_err:
        print(f"[compose] WARNING: paint pattern_strength_map skipped: {_psm_paint_err}")
        return after


def _stack_layer_paint_blend(before, after, mode):
    """Photoshop-style blend of ONE stacked pattern layer onto the paint under it.

    ``after`` is the layer composited NORMAL. Coverage is recovered from how far the layer
    moved each pixel (a = clip(4*max|after-before|, 0, 1)), the layer ink from
    ``before + delta / a``; untouched pixels (delta 0) stay exactly ``before``.
    """
    if before is None or mode not in _PAINT_LAYER_BLEND_MODES:
        return after
    b = np.clip(np.asarray(before[:, :, :3], dtype=np.float32), 0.0, 1.0)
    n = np.asarray(after[:, :, :3], dtype=np.float32)
    d = n - b
    a = np.clip(np.max(np.abs(d), axis=2, keepdims=True) * 4.0, 0.0, 1.0)
    top = np.clip(b + d / np.maximum(a, 1e-4), 0.0, 1.0)
    if mode == "multiply":
        bl = b * top
    elif mode == "screen":
        bl = 1.0 - (1.0 - b) * (1.0 - top)
    elif mode == "overlay":
        bl = np.where(b < 0.5, 2.0 * b * top, 1.0 - 2.0 * (1.0 - b) * (1.0 - top))
    elif mode == "hardlight":
        bl = np.where(top < 0.5, 2.0 * b * top, 1.0 - 2.0 * (1.0 - b) * (1.0 - top))
    else:  # softlight
        bl = (1.0 - 2.0 * top) * b * b + 2.0 * top * b
    out = np.array(after, dtype=np.float32, copy=True)
    out[:, :, :3] = b * (1.0 - a) + bl * a
    return out


def compose_paint_mod(base_id, pattern_id, paint, shape, mask, seed, pm, bb, scale=1.0, rotation=0, blend_base=None, blend_dir="horizontal", blend_amount=0.5,
                   base_color_mode="source", base_color=None, base_color_source=None, base_color_strength=1.0, base_color_fit_zone=False, base_color_scale=1.0, base_color_rotation=None,
                      base_color_depth=None, base_color_flip=0.0, base_color_underglow=0.0,
                      second_base=None, second_base_color=None, second_base_color_source=None, second_base_strength=0.0, second_base_spec_strength=1.0, second_base_color_strength=1.0, second_base_rotation=0.0,
                      second_base_blend_mode="noise", second_base_noise_scale=24,
                      second_base_scale=1.0, second_base_color_scale=1.0, second_base_spec_scale=1.0, second_base_pattern=None,
                      second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                      second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                      second_base_pattern_invert=False, second_base_pattern_harden=False,
                      second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                      third_base=None, third_base_color=None, third_base_color_source=None, third_base_strength=0.0, third_base_spec_strength=1.0, third_base_color_strength=1.0, third_base_rotation=0.0,
                      third_base_blend_mode="noise", third_base_noise_scale=24,
                      third_base_scale=1.0, third_base_color_scale=1.0, third_base_spec_scale=1.0, third_base_pattern=None,
                      third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                      third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                      third_base_pattern_invert=False, third_base_pattern_harden=False,
                      third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                      fourth_base=None, fourth_base_color=None, fourth_base_color_source=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0, fourth_base_color_strength=1.0, fourth_base_rotation=0.0,
                      fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                      fourth_base_scale=1.0, fourth_base_color_scale=1.0, fourth_base_spec_scale=1.0, fourth_base_pattern=None,
                      fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                      fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                      fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                      fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                      fifth_base=None, fifth_base_color=None, fifth_base_color_source=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0, fifth_base_color_strength=1.0, fifth_base_rotation=0.0,
                      fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                      fifth_base_scale=1.0, fifth_base_color_scale=1.0, fifth_base_spec_scale=1.0, fifth_base_pattern=None,
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
                      pattern_intensity=1.0, pattern_strength_map=None,
                      base_hue_offset=0, base_saturation_adjust=0, base_brightness_adjust=0,
                      base_scale=1.0, base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0,
                      base_flip_h=False, base_flip_v=False,
                      pattern_offset_x=0.5, pattern_offset_y=0.5,
                      pattern_flip_h=False, pattern_flip_v=False,
                      pattern_fit_zone=False, pattern_paint_mode="legacy",
                      pattern_hue_shift=0., pattern_saturation=0.):
    """Apply base paint modifier then pattern paint modifier WITH spatial texture blending.
    pattern_intensity 0-1: 5%% = hint, 100%% = full (linear; avoids flip below 50%%).
    When second_base_color_source (etc.) is 'mono:xyz', the overlay color comes from that special's paint_fn (gradients, color shifts, etc.).
    PURE CPU: always receives and returns numpy arrays. The caller (build_multi_zone) handles GPU↔CPU conversion."""
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY
    # Ensure CPU numpy — CuPy inputs converted here (caller should prefer to_cpu before calling)
    if hasattr(paint, 'get'):
        paint = paint.get()
    paint = np.asarray(paint)
    _source_paint_for_base_strength = paint.copy()
    if hasattr(mask, 'get'):
        mask = mask.get()
    mask = np.asarray(mask)
    hard_mask = np.where(mask > 0.1, mask, np.float32(0.0)).astype(np.float32)
    base = BASE_REGISTRY[base_id]
    base_paint_fn = base.get("paint_fn", paint_none)
    pattern_entry = _resolve_pattern_registry_entry(pattern_id, PATTERN_REGISTRY)
    has_pattern = pattern_entry is not None
    has_blend = (blend_base and blend_base in BASE_REGISTRY and blend_base != base_id)
    # blend_base debug removed — was [BLEND DEBUG] print
    if has_blend:
        base2 = BASE_REGISTRY[blend_base]
        base2_paint_fn = base2.get("paint_fn", paint_none)

    # SPB-93 / 2026-07-16 natural controls. Owner verdict: "when you take the
    # BASE STRENGTH down it should start sliding more toward the SOURCE PAINT."
    # Render the complete target first, then mix once. The old path multiplied
    # renderer inputs and left the chosen base color visible at zero.
    _BASE_STRENGTH_RAW = max(0.0, min(2.0, float(base_strength)))
    _BASE_STRENGTH_MIX = min(1.0, _BASE_STRENGTH_RAW)
    _BASE_PAINT_BOOST = max(1.0, _BASE_STRENGTH_RAW)
    _base_placement_for_material = (
        not _base_color_mode_is_explicit(base_color_mode, base_color_strength)
        and _base_placement_active(
            base_scale, base_offset_x, base_offset_y, base_rotation, base_flip_h, base_flip_v
        )
    )
    _paint_before_base_placement = paint.copy() if _base_placement_for_material else None
    # SPB 2026-06-23 WHOLE-CAR-TILING FINAL FIX — regular-base (PATH 1) parity with the
    # monolithic finer-pass. base_scale<1 must make the base's OWN pattern get FINER, NOT
    # tile the car-body silhouette. The old delta-tile zeroed the delta OUTSIDE the zone
    # (`* src3`) BEFORE tiling, so the body shape repeated. CURE: render the base over a
    # CLEAN flat seed (zone mean colour, decal-free) => a PURE full-canvas pattern, tile
    # THAT finer, then confine to the zone. "Tile the FIELD, not the canvas."
    _finer_base_active = bool(
        _base_placement_for_material
        and not base_color_fit_zone
        and base_scale is not None and float(base_scale) < 0.999
        # SPB 2026-06-26 PASS-THROUGH GUARD (owner: numbers/sponsors stripped + marker
        # regression). A pass-through base (gloss/clear, paint_fn IS paint_none) has NO
        # pattern of its own to make finer, and its whole paint_fn block — including the
        # _op<0.045 deactivation check — is SKIPPED, leaving this flag True so the final
        # block tiled the real SOURCE COMPOSITE (decals/car number) confined to the zone
        # = the "whole-canvas tile" + "decals removed/replicated" report. For these bases
        # base_scale must stay a no-op (the source paint / pattern shows through), so the
        # guarded _apply_base_placement_to_paint path handles it instead.
        and base_paint_fn is not paint_none
    )
    _finer_clean_seed = None
    if _finer_base_active:
        _bg0 = _paint_before_base_placement
        _bg0 = np.asarray(_bg0.get() if hasattr(_bg0, "get") else _bg0, dtype=np.float32)
        _hmf0 = np.asarray(hard_mask.get() if hasattr(hard_mask, "get") else hard_mask, dtype=np.float32)
        _zsel = _hmf0 > 0.001
        if bool(np.any(_zsel)):
            _seed_col = np.clip(np.mean(_bg0[:, :, :3][_zsel], axis=0), 0.0, 1.0).astype(np.float32)
        else:
            _seed_col = np.array([0.533, 0.533, 0.533], dtype=np.float32)
        _ch0 = _bg0.shape[2] if _bg0.ndim == 3 else 3
        _finer_clean_seed = np.empty((int(shape[0]), int(shape[1]), _ch0), dtype=np.float32)
        _finer_clean_seed[:, :, :3] = _seed_col
        if _ch0 > 3:
            _finer_clean_seed[:, :, 3:] = _bg0[:, :, 3:]
    # SPB 2026-06-09 owner "Base Scale does nothing" fix: on the EXPLICIT base-
    # color path (solid / gradient / From-special) the material-placement branch
    # above is skipped, and this path previously honored ONLY base_color_scale —
    # the Base Scale slider was silently ignored. Both sliders now compose
    # multiplicatively (each defaults to 1.0, so either alone behaves normally).
    # Guarded by tests/regression_base_transform_controls_test.py.
    _effective_color_scale = (
        float(base_scale if base_scale is not None else 1.0)
        * float(base_color_scale if base_color_scale is not None else 1.0)
    )
    _base_color_preseeded = _base_color_replaces_source_before_material(
        base_color_mode, base_color_strength, _BASE_PAINT_BOOST
    )
    if _base_color_preseeded:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, 1.0,
            monolithic_registry,
            fit_to_bbox=bool(base_color_fit_zone),
            base_scale=_effective_color_scale,
            base_offset_x=base_offset_x,
            base_offset_y=base_offset_y,
            base_rotation=base_rotation if base_color_rotation is None else base_color_rotation,
            base_flip_h=base_flip_h,
            base_flip_v=base_flip_v,
        )
    # [SPB 2026-07-08 owner: "USE SOURCE PAINT is SUPPOSED to use the SOURCE PAINT
    # of the car as it is — all colors remain; what I'm changing is the SPEC BASE."]
    # In base_color_mode='source' the base contributes SPEC ONLY: art-producing
    # base paint_fns (Ghost Graphic etc.) were overwriting the painter's source
    # colors (repro: 4-hue source went gray). Skip the base paint pass entirely —
    # patterns still draw later on the untouched source substrate, and the HSB
    # sliders still adjust the source colors. Explicit color modes (solid /
    # special / gradient) are unaffected.
    # Guard: tests/regression_source_mode_keeps_colors_test.py
    _source_paint_lock = str(base_color_mode or "source").strip().lower() in ("", "source", "none")
    if base_paint_fn is not paint_none and _BASE_PAINT_BOOST > 0.001 and not _source_paint_lock:
        # External paint_fn expects CPU (numpy) arrays — paint is already CPU here
        try:
            _paint_before_base_fn = paint.copy() if base_color_fit_zone else None
            _base_fit_mask = (
                np.ones_like(hard_mask, dtype=np.float32)
                if (base_color_fit_zone or _base_placement_for_material)
                else hard_mask
            )
            if _finer_base_active:
                # OPAQUE-ONLY finer path. Render the base PURE over the clean seed, then measure how
                # much material it adds. A pass-through base (gloss/clear/tint) barely departs from
                # the flat seed -> base_scale must stay a no-op so the SOURCE PAINT shows (don't
                # replace it with a flat tile). Only opaque bases get the pure finer tiling.
                _pmw = _BASE_PAINT_BOOST * (0.7 if has_pattern and pattern_paint_mode == "legacy" else 1.0)
                _pure_res = base_paint_fn(_finer_clean_seed, shape, _base_fit_mask, seed, pm * _pmw, bb * _pmw)
                _pure_arr = np.asarray(_pure_res) if not isinstance(_pure_res, np.ndarray) else _pure_res
                _op = float(np.mean(np.abs(np.asarray(_pure_arr, dtype=np.float32)[:, :, :3] - _seed_col[None, None, :])))
                if _op < 0.045:
                    _finer_base_active = False
                    _pr = base_paint_fn(paint, shape, _base_fit_mask, seed, pm * _pmw, bb * _pmw)
                    paint = np.asarray(_pr) if not isinstance(_pr, np.ndarray) else _pr
                else:
                    paint = _pure_arr
            else:
                if has_pattern and pattern_paint_mode == "legacy":
                    _paint_result = base_paint_fn(paint, shape, _base_fit_mask, seed, pm * _BASE_PAINT_BOOST * 0.7, bb * _BASE_PAINT_BOOST * 0.7)
                else:
                    _paint_result = base_paint_fn(paint, shape, _base_fit_mask, seed, pm * _BASE_PAINT_BOOST, bb * _BASE_PAINT_BOOST)
                paint = np.asarray(_paint_result) if not isinstance(_paint_result, np.ndarray) else _paint_result
            if base_color_fit_zone and _paint_before_base_fn is not None:
                paint = _fit_paint_source_to_mask_bbox(paint, _paint_before_base_fn, hard_mask)
        except Exception as _bp_err:
            raise RuntimeError(f"Base paint renderer failed [{base_id}]: {_bp_err}") from _bp_err

    if not _base_color_preseeded:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, base_color_strength,
            monolithic_registry,
            fit_to_bbox=bool(base_color_fit_zone),
            base_color_depth=base_color_depth,
            base_color_flip=base_color_flip,
            base_color_underglow=base_color_underglow,
            base_scale=_effective_color_scale,
            base_offset_x=base_offset_x,
            base_offset_y=base_offset_y,
            base_rotation=base_rotation if base_color_rotation is None else base_color_rotation,
            base_flip_h=base_flip_h,
            base_flip_v=base_flip_v,
        )

    # HSB adjustments (hue shift, saturation, brightness)
    _hue_off = base_hue_offset
    _sat_adj = base_saturation_adjust
    _bri_adj = base_brightness_adjust
    if _hue_off or _sat_adj or _bri_adj:
        paint = _apply_hsb_adjustments(paint, hard_mask, _hue_off, _sat_adj, _bri_adj)

    # SPB-2026-05-18: When a special/gradient/solid base color is active, placement
    # (scale/rotate/pan) is already applied inside _apply_base_color_override on the
    # generated source. Re-tiling the full composited paint here produced miniature
    # copies of the entire car canvas (casino-as-color over metallic foundation).
    # [SPB WHOLE-CANVAS-TILE 2026-08-15 — owner: "if the BASE SCALE is scaled down it's actually
    # scaling down the entire canvas... on ALL BASE FINISHES". Reproduced: glitch_rgb @0.1 in
    # source mode = a 10x10 grid of mini-cars, decals included.]
    # Root cause: the 2026-07-08 _source_paint_lock SKIPS the base paint pass in source mode,
    # but this placement block still ran. Its finer branch tiles `paint` assuming it holds the
    # PURE full-canvas base pattern that block would have produced — in source mode `paint` is
    # the painter's SOURCE COMPOSITE (decals, numbers), so it tiled the car itself. In source
    # mode nothing base-derived is on the canvas, so there is NOTHING to place: base_scale
    # must be a paint no-op (it still scales the SPEC through the spec path). Same shape as the
    # monolithic source-parity fix earlier today — the lock landed without auditing downstream
    # consumers of `paint`. Guard: tests/regression_source_mode_keeps_colors_test.py +
    # tests/regression_base_scale_no_whole_canvas_tile_test.py.
    if not _base_color_mode_is_explicit(base_color_mode, base_color_strength) and not _source_paint_lock:
        if _finer_base_active:
            # Tile the PURE full-canvas base pattern finer, then confine to the zone.
            _h0, _w0 = int(shape[0]), int(shape[1])
            _pure_finer = _transform_base_color_source(
                np.clip(np.asarray(paint)[:, :, :3], 0.0, 1.0).astype(np.float32), (_h0, _w0),
                scale=base_scale, offset_x=base_offset_x, offset_y=base_offset_y,
                rotation=base_rotation, flip_h=bool(base_flip_h), flip_v=bool(base_flip_v),
            )
            _bgp = _paint_before_base_placement
            _bgp = np.asarray(_bgp.get() if hasattr(_bgp, "get") else _bgp, dtype=np.float32)
            _hm3 = (np.asarray(hard_mask.get() if hasattr(hard_mask, "get") else hard_mask, dtype=np.float32)[:, :, np.newaxis] > 0.001)
            paint = np.array(paint, dtype=np.float32, copy=True)
            paint[:, :, :3] = np.where(_hm3, _pure_finer, np.clip(_bgp[:, :, :3], 0.0, 1.0)).astype(np.float32, copy=False)
        else:
            paint = _apply_base_placement_to_paint(
                paint,
                shape,
                hard_mask,
                base_scale=base_scale,
                base_offset_x=base_offset_x,
                base_offset_y=base_offset_y,
                base_rotation=base_rotation,
                base_flip_h=base_flip_h,
                base_flip_v=base_flip_v,
                background_paint=_paint_before_base_placement,
            )

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
    # Base Strength envelopes the completed base/material/color/HSB result.
    # Patterns intentionally remain outside this mix and are applied afterward.
    paint = _blend_base_result_over_source(
        _source_paint_for_base_strength, paint, hard_mask, _BASE_STRENGTH_MIX
    )

    _pi_raw = max(0.0, min(1.0, float(pattern_intensity)))
    _pi = _pi_raw ** 0.5 if _pi_raw > 0 else 0.0
    # BUGFIX 2026-10-04: Strength Map reaches the paint (snapshot before the pattern block).
    _psm_paint_before = paint.copy() if (has_pattern and pattern_strength_map is not None) else None
    if has_pattern:
        pattern = pattern_entry
        pat_paint_fn, tex_fn = pattern_paint_source(pattern, pattern_paint_mode)
        pat_paint_fn = pat_paint_fn or paint_none
        image_path = pattern_color_source(pattern_id, pattern, pattern_paint_mode)
        if image_path:
            from engine.render import _load_image_pattern, _load_color_image_pattern
            # Get the full color version
            if pattern_paint_mode in ("overlay", "blend"):
                rgba = load_pattern_artwork(image_path, shape, scale=scale, rotation=rotation,
                    offset_x=pattern_offset_x, offset_y=pattern_offset_y,
                    flip_h=pattern_flip_h, flip_v=pattern_flip_v,
                    fit_zone=pattern_fit_zone, mask=hard_mask)
            else:
                rgba = _load_color_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if rgba is not None:
                if pattern_fit_zone and pattern_paint_mode == "legacy":
                    rgba = _fit_pattern_to_mask_bbox(rgba, hard_mask)
                r, g, b, alpha = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3]
                # Scale alpha by pattern_intensity so 5% shows a hint, 100% full — all CPU
                alpha_3d = (alpha[:, :, np.newaxis] * _pi) * hard_mask[:, :, np.newaxis]
                rgb_3d = rgba[:, :, :3]
                if pattern_paint_mode in ("overlay", "blend"):
                    paint = composite_pattern_pixels(paint, rgb_3d, hard_mask * alpha,
                        amount=_pi_raw * np.clip(spec_mult, 0, 1), mode=pattern_paint_mode,
                        hue_shift=pattern_hue_shift, saturation=pattern_saturation)
                else:
                    paint[:, :, :3] = paint[:, :, :3] * (1.0 - alpha_3d) + rgb_3d * alpha_3d
            else:
                pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
                if pv is not None:
                    if pattern_fit_zone:
                        pv = _fit_pattern_to_mask_bbox(pv, hard_mask)
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
        elif pattern_paint_mode in ("overlay", "blend"):
            paint = composite_pattern_layer(
                pat_paint_fn, paint, shape, hard_mask, seed,
                strength=spec_mult, intensity=_pi_raw, mode=pattern_paint_mode, texture_fn=tex_fn,
                hue_shift=pattern_hue_shift, saturation=pattern_saturation,
                scale=scale, rotation=rotation, offset_x=pattern_offset_x,
                offset_y=pattern_offset_y, flip_h=pattern_flip_h,
                flip_v=pattern_flip_v, fit_zone=pattern_fit_zone)
        elif pat_paint_fn is not paint_none:
            # External pat_paint_fn expects CPU arrays — paint is already CPU here
            paint_before_pattern = paint.copy()
            _PAT_PAINT_BOOST = 1.8
            try:
                if base_paint_fn is not paint_none:
                    _pat_result = render_pattern_paint(pat_paint_fn, paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST * 0.7 * spec_mult, bb * _PAT_PAINT_BOOST * 0.7 * spec_mult, scale=scale, rotation=rotation, offset_x=pattern_offset_x, offset_y=pattern_offset_y, flip_h=pattern_flip_h, flip_v=pattern_flip_v, fit_zone=pattern_fit_zone)
                else:
                    _pat_result = render_pattern_paint(pat_paint_fn, paint, shape, hard_mask, seed, pm * _PAT_PAINT_BOOST * spec_mult, bb * _PAT_PAINT_BOOST * spec_mult, scale=scale, rotation=rotation, offset_x=pattern_offset_x, offset_y=pattern_offset_y, flip_h=pattern_flip_h, flip_v=pattern_flip_v, fit_zone=pattern_fit_zone)
                paint = np.asarray(_pat_result) if not isinstance(_pat_result, np.ndarray) else _pat_result
            except Exception as _pp_err:
                raise RuntimeError(f"Pattern paint renderer failed [{pattern_id}]: {_pp_err}") from _pp_err
            # SPB-105 scale repair tick 1: placement already transformed the ink.
            # A second texture mask made smaller direct patterns fade/disappear.
            _direct_pattern_paint = getattr(pat_paint_fn, "_spb_pattern_direct_paint", False)
            if _direct_pattern_paint:
                if _base_color_mode_is_explicit(base_color_mode, base_color_strength):
                    paint = _tint_direct_pattern_paint(paint, paint_before_pattern, hard_mask, base_color_strength)
                if _pi < 1.0 - 1e-6:
                    paint = paint_before_pattern * (1.0 - _pi) + paint * _pi
            elif tex_fn is not None:
                try:
                    # tex_fn expects CPU mask — mask is already CPU here
                    if scale != 1.0 and 0.0 < scale < 1.0:
                        # [SPB 2026-06-10 whole-car-tiling fix v2 — fast] Scale DOWN a procedural
                        # tex_fn pattern by generating the PURE pattern ONCE at output resolution
                        # (ones mask -> no zone/composite contamination) then TILING it down so
                        # motifs shrink and repeat ("tile down", the owner's expected behaviour).
                        # Replaces the slow regenerate-at-4096 path (3x 6.4s gens -> 23.8s render).
                        # Single 2048 gen (~1.9s) + near-free tile. The earlier whole-car tiling
                        # came from the np.tile path tiling a contaminated array; generating the
                        # pure pattern fresh here keeps the tile clean.
                        tex = tex_fn(shape, np.ones(shape, dtype=np.float32), seed, 1.0)
                        pv = tex["pattern_val"] if isinstance(tex, dict) else tex
                        pv = _tile_fractional(np.asarray(pv, dtype=np.float32), 1.0 / scale, shape[0], shape[1])
                        if isinstance(tex, dict):
                            for _k in ("R_extra", "M_extra", "CC"):
                                if isinstance(tex.get(_k), np.ndarray):
                                    tex[_k] = _tile_fractional(np.asarray(tex[_k], dtype=np.float32), 1.0 / scale, shape[0], shape[1])
                    else:
                        tex = tex_fn(shape, mask, seed, 1.0)
                        pv = tex["pattern_val"] if isinstance(tex, dict) else tex
                        if scale > 1.0:
                            pv = _crop_center_array(pv, scale, shape[0], shape[1])
                    rot_angle = float(rotation) % 360
                    if rot_angle != 0:
                        pv = _rotate_single_array(pv, rot_angle, shape)
                    if pattern_fit_zone:
                        pv = _fit_pattern_to_mask_bbox(pv, hard_mask)
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
            try:
                _paint_delta = float(np.mean(np.abs(paint[:, :, :3] - paint_before_pattern[:, :, :3])))
            except Exception:
                _paint_delta = 1.0
            if tex_fn is not None and _paint_delta < 0.010 and _pi > 0.001:
                paint = _apply_texture_pattern_paint_modulation(
                    paint, pattern_id, shape, hard_mask, seed,
                    scale, rotation, pattern_offset_x, pattern_offset_y,
                    pattern_flip_h, pattern_flip_v, _pi, pm, spec_mult,
                )
        elif tex_fn is not None:
            try:
                paint = _apply_texture_pattern_paint_modulation(
                    paint, pattern_id, shape, hard_mask, seed,
                    scale, rotation, pattern_offset_x, pattern_offset_y,
                    pattern_flip_h, pattern_flip_v, _pi, pm, spec_mult,
                )
            except Exception:
                pass
    if _psm_paint_before is not None:
        paint = _paint_strength_map_blend(_psm_paint_before, paint, pattern_strength_map)
        _psm_paint_before = None

    if second_base_strength > 0.001 and (second_base or second_base_color_source or second_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _sb_shape, hard_mask, seed + 7777,
                    base_scale=second_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"2nd base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                else:
                    _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                    _cp_shape = _color_paint.shape if hasattr(_color_paint, 'shape') else 'N/A'
                    _cp_dtype = _color_paint.dtype if hasattr(_color_paint, 'dtype') else 'N/A'
                    _cp_min = float(_color_paint[:,:,:3].min()) if hasattr(_color_paint, 'min') else 'N/A'
                    _cp_max = float(_color_paint[:,:,:3].max()) if hasattr(_color_paint, 'max') else 'N/A'
                    print(f"    [PAINT OVERLAY 2nd] mono paint result: shape={_cp_shape}, dtype={_cp_dtype}, range=[{_cp_min:.3f}, {_cp_max:.3f}]")
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(second_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_cpu.shape[0], _paint_overlay_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(second_base_color_strength)))
                _paint_overlay_cpu[:, :, :3] = _paint_overlay_cpu[:, :, :3] * (1.0 - _sb_mask3d * _ovcs) + _ovcp * (_sb_mask3d * _ovcs)
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
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(second_base_color_strength)))
                _paint_overlay_cpu[:, :, :3] = _paint_overlay_cpu[:, :, :3] * (1.0 - _sb_mask3d * _ovcs) + _sb_rgb * (_sb_mask3d * _ovcs)
            if second_base and second_base in BASE_REGISTRY:
                _sb_def2 = BASE_REGISTRY[second_base]
                _sb_pfn = _sb_def2.get("paint_fn", paint_none)
                # When "From Special" is active, skip the base paint_fn — the special's
                # colors are the user's explicit choice.  The base overlay contributes
                # its SPEC (metallic/roughness/CC) which is the PBR-correct approach;
                # its paint_fn would wash out the special's colors (e.g. Chrome pushes
                # toward silver, destroying a Bruise purple-to-black gradient).
                if _sb_pfn is not paint_none and not _sb_color_src and _overlay_should_apply_base_paint_fn(second_base_color_source):
                    # External paint_fn expects CPU arrays — _paint_overlay_cpu is already CPU
                    _paint_overlay_cpu = _sb_pfn(_paint_overlay_cpu, _sb_shape, hard_mask, seed + 7777, 1.0, 0.0)
                    _paint_overlay_cpu = np.asarray(_paint_overlay_cpu) if not isinstance(_paint_overlay_cpu, np.ndarray) else _paint_overlay_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_sb = _resolve_overlay_pattern_mask_id(
                second_base_pattern, pattern_id, second_base_blend_mode
            )
            _sb_pat_mask = _get_overlay_pattern_mask(
                second_base_pattern, _pat_id_sb, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                second_base_pattern_scale, second_base_pattern_rotation,
                second_base_pattern_offset_x, second_base_pattern_offset_y,
                _sb_shape, hard_mask, seed, 1.0,
                second_base_pattern_opacity, second_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _sb_pat_mask is not None:
                if second_base_pattern_invert:
                    _sb_pat_mask = 1.0 - _sb_pat_mask
                if second_base_pattern_harden:
                    _sb_pat_mask = _harden_overlay_pattern_mask(_sb_pat_mask)
            _alpha_sb = get_base_overlay_alpha(
                _sb_shape, second_base_strength, second_base_blend_mode,
                noise_scale=int(second_base_noise_scale), seed=seed,
                pattern_mask=_sb_pat_mask, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(second_base_scale)))
            )
            _alpha_sb3 = _alpha_sb[:, :, np.newaxis]
            # [SPB-OVERLAY-PARITY 2026-08-20] base-HSB used to be applied HERE (to the
            # overlay) AND again after the blend - the only tier that got it twice.
            # The post-blend application below is the one every tier shares.
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
            raise RuntimeError(f"2nd base overlay paint renderer failed: {_e}") from _e

    if third_base_strength > 0.001 and (third_base or third_base_color_source or third_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _tb_shape, hard_mask, seed + 9999,
                    base_scale=third_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"3rd base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(third_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_tb_cpu.shape[0], _paint_overlay_tb_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(third_base_color_strength)))
                _paint_overlay_tb_cpu[:, :, :3] = _paint_overlay_tb_cpu[:, :, :3] * (1.0 - _tb_mask3d * _ovcs) + _ovcp * (_tb_mask3d * _ovcs)
            elif _tb_color_src:
                print(f"    [PAINT OVERLAY 3rd] WARNING: special source '{_tb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _tb_color = third_base_color if third_base_color is not None else [1.0, 1.0, 1.0]
                _tb_r = float(_tb_color[0]) if len(_tb_color) > 0 else 1.0
                _tb_g = float(_tb_color[1]) if len(_tb_color) > 1 else 1.0
                _tb_b = float(_tb_color[2]) if len(_tb_color) > 2 else 1.0
                _tb_rgb = np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(third_base_color_strength)))
                _paint_overlay_tb_cpu[:, :, :3] = _paint_overlay_tb_cpu[:, :, :3] * (1.0 - _tb_mask3d * _ovcs) + _tb_rgb * (_tb_mask3d * _ovcs)
            if third_base and third_base in BASE_REGISTRY:
                _tb_def2 = BASE_REGISTRY[third_base]
                _tb_pfn = _tb_def2.get("paint_fn", paint_none)
                if _tb_pfn is not paint_none and not _tb_color_src and _overlay_should_apply_base_paint_fn(third_base_color_source):
                    _paint_overlay_tb_cpu = _tb_pfn(_paint_overlay_tb_cpu, _tb_shape, hard_mask, seed + 9999, 1.0, 0.0)
                    _paint_overlay_tb_cpu = np.asarray(_paint_overlay_tb_cpu) if not isinstance(_paint_overlay_tb_cpu, np.ndarray) else _paint_overlay_tb_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = _resolve_overlay_pattern_mask_id(
                third_base_pattern, pattern_id, third_base_blend_mode
            )
            _tb_pat_mask = _get_overlay_pattern_mask(
                third_base_pattern, _pat_id_tb, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                third_base_pattern_scale, third_base_pattern_rotation,
                third_base_pattern_offset_x, third_base_pattern_offset_y,
                _tb_shape, hard_mask, seed, 1.0,
                third_base_pattern_opacity, third_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _tb_pat_mask is not None:
                if third_base_pattern_invert:
                    _tb_pat_mask = 1.0 - _tb_pat_mask
                if third_base_pattern_harden:
                    _tb_pat_mask = _harden_overlay_pattern_mask(_tb_pat_mask)
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
            raise RuntimeError(f"3rd base overlay paint renderer failed: {_e}") from _e

    if fourth_base_strength > 0.001 and (fourth_base or fourth_base_color_source or fourth_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _fb_shape, hard_mask, seed + 11111,
                    base_scale=fourth_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"4th base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(fourth_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_fb_cpu.shape[0], _paint_overlay_fb_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(fourth_base_color_strength)))
                _paint_overlay_fb_cpu[:, :, :3] = _paint_overlay_fb_cpu[:, :, :3] * (1.0 - _fb_mask3d * _ovcs) + _ovcp * (_fb_mask3d * _ovcs)
            elif _fb_color_src:
                print(f"    [PAINT OVERLAY 4th] WARNING: special source '{_fb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fb_color = fourth_base_color if fourth_base_color is not None else [1.0, 1.0, 1.0]
                _fb_r = float(_fb_color[0]) if len(_fb_color) > 0 else 1.0
                _fb_g = float(_fb_color[1]) if len(_fb_color) > 1 else 1.0
                _fb_b = float(_fb_color[2]) if len(_fb_color) > 2 else 1.0
                _fb_rgb = np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(fourth_base_color_strength)))
                _paint_overlay_fb_cpu[:, :, :3] = _paint_overlay_fb_cpu[:, :, :3] * (1.0 - _fb_mask3d * _ovcs) + _fb_rgb * (_fb_mask3d * _ovcs)
            if fourth_base and fourth_base in BASE_REGISTRY:
                _fb_def2 = BASE_REGISTRY[fourth_base]
                _fb_pfn = _fb_def2.get("paint_fn", paint_none)
                if _fb_pfn is not paint_none and not _fb_color_src and _overlay_should_apply_base_paint_fn(fourth_base_color_source):
                    _paint_overlay_fb_cpu = _fb_pfn(_paint_overlay_fb_cpu, _fb_shape, hard_mask, seed + 11111, 1.0, 0.0)
                    _paint_overlay_fb_cpu = np.asarray(_paint_overlay_fb_cpu) if not isinstance(_paint_overlay_fb_cpu, np.ndarray) else _paint_overlay_fb_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = _resolve_overlay_pattern_mask_id(
                fourth_base_pattern, pattern_id, fourth_base_blend_mode
            )
            _fb_pat_mask = _get_overlay_pattern_mask(
                fourth_base_pattern, _pat_id_fb, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                fourth_base_pattern_scale, fourth_base_pattern_rotation,
                fourth_base_pattern_offset_x, fourth_base_pattern_offset_y,
                _fb_shape, hard_mask, seed, 1.0,
                fourth_base_pattern_opacity, fourth_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _fb_pat_mask is not None:
                if fourth_base_pattern_invert:
                    _fb_pat_mask = 1.0 - _fb_pat_mask
                if fourth_base_pattern_harden:
                    _fb_pat_mask = _harden_overlay_pattern_mask(_fb_pat_mask)
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
        except Exception as _e:
            raise RuntimeError(f"4th base overlay paint renderer failed: {_e}") from _e

    if fifth_base_strength > 0.001 and (fifth_base or fifth_base_color_source or fifth_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _fif_shape, hard_mask, seed + 13333,
                    base_scale=fifth_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"5th base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(fifth_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_fif_cpu.shape[0], _paint_overlay_fif_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(fifth_base_color_strength)))
                _paint_overlay_fif_cpu[:, :, :3] = _paint_overlay_fif_cpu[:, :, :3] * (1.0 - _fif_mask3d * _ovcs) + _ovcp * (_fif_mask3d * _ovcs)
            elif _fif_color_src:
                print(f"    [PAINT OVERLAY 5th] WARNING: special source '{_fif_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fif_color = fifth_base_color if fifth_base_color is not None else [1.0, 1.0, 1.0]
                _fif_r = float(_fif_color[0]) if len(_fif_color) > 0 else 1.0
                _fif_g = float(_fif_color[1]) if len(_fif_color) > 1 else 1.0
                _fif_b = float(_fif_color[2]) if len(_fif_color) > 2 else 1.0
                _fif_rgb = np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(fifth_base_color_strength)))
                _paint_overlay_fif_cpu[:, :, :3] = _paint_overlay_fif_cpu[:, :, :3] * (1.0 - _fif_mask3d * _ovcs) + _fif_rgb * (_fif_mask3d * _ovcs)
            if fifth_base and fifth_base in BASE_REGISTRY:
                _fif_def2 = BASE_REGISTRY[fifth_base]
                _fif_pfn = _fif_def2.get("paint_fn", paint_none)
                if _fif_pfn is not paint_none and not _fif_color_src and _overlay_should_apply_base_paint_fn(fifth_base_color_source):
                    _paint_overlay_fif_cpu = _fif_pfn(_paint_overlay_fif_cpu, _fif_shape, hard_mask, seed + 13333, 1.0, 0.0)
                    _paint_overlay_fif_cpu = np.asarray(_paint_overlay_fif_cpu) if not isinstance(_paint_overlay_fif_cpu, np.ndarray) else _paint_overlay_fif_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = _resolve_overlay_pattern_mask_id(
                fifth_base_pattern, pattern_id, fifth_base_blend_mode
            )
            _fif_pat_mask = _get_overlay_pattern_mask(
                fifth_base_pattern, _pat_id_fif, pattern_id,
                scale, rotation, pattern_offset_x, pattern_offset_y,
                fifth_base_pattern_scale, fifth_base_pattern_rotation,
                fifth_base_pattern_offset_x, fifth_base_pattern_offset_y,
                _fif_shape, hard_mask, seed, 1.0,
                fifth_base_pattern_opacity, fifth_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _fif_pat_mask is not None:
                if fifth_base_pattern_invert:
                    _fif_pat_mask = 1.0 - _fif_pat_mask
                if fifth_base_pattern_harden:
                    _fif_pat_mask = _harden_overlay_pattern_mask(_fif_pat_mask)
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
        except Exception as _e:
            raise RuntimeError(f"5th base overlay paint renderer failed: {_e}") from _e

    return paint


def compose_paint_mod_stacked(base_id, all_patterns, paint, shape, mask, seed, pm, bb, blend_base=None, blend_dir="horizontal", blend_amount=0.5,
                              second_base=None, second_base_color=None, second_base_strength=0.0, second_base_spec_strength=1.0, second_base_color_strength=1.0, second_base_rotation=0.0,
                              second_base_blend_mode="noise", second_base_noise_scale=24,
                              second_base_scale=1.0, second_base_color_scale=1.0, second_base_spec_scale=1.0, second_base_pattern=None,
                              second_base_pattern_scale=1.0, second_base_pattern_rotation=0.0,
                              second_base_pattern_opacity=1.0, second_base_pattern_strength=1.0,
                              second_base_pattern_invert=False, second_base_pattern_harden=False,
                              second_base_pattern_offset_x=0.5, second_base_pattern_offset_y=0.5,
                              third_base=None, third_base_color=None, third_base_strength=0.0, third_base_spec_strength=1.0, third_base_color_strength=1.0, third_base_rotation=0.0,
                              third_base_blend_mode="noise", third_base_noise_scale=24,
                              third_base_scale=1.0, third_base_color_scale=1.0, third_base_spec_scale=1.0, third_base_pattern=None,
                              third_base_pattern_scale=1.0, third_base_pattern_rotation=0.0,
                              third_base_pattern_opacity=1.0, third_base_pattern_strength=1.0,
                              third_base_pattern_invert=False, third_base_pattern_harden=False,
                              third_base_pattern_offset_x=0.5, third_base_pattern_offset_y=0.5,
                              fourth_base=None, fourth_base_color=None, fourth_base_strength=0.0, fourth_base_spec_strength=1.0, fourth_base_color_strength=1.0, fourth_base_rotation=0.0,
                              fourth_base_blend_mode="noise", fourth_base_noise_scale=24,
                              fourth_base_scale=1.0, fourth_base_color_scale=1.0, fourth_base_spec_scale=1.0, fourth_base_pattern=None,
                              fourth_base_pattern_scale=1.0, fourth_base_pattern_rotation=0.0,
                              fourth_base_pattern_opacity=1.0, fourth_base_pattern_strength=1.0,
                              fourth_base_pattern_invert=False, fourth_base_pattern_harden=False,
                              fourth_base_pattern_offset_x=0.5, fourth_base_pattern_offset_y=0.5,
                              fifth_base=None, fifth_base_color=None, fifth_base_strength=0.0, fifth_base_spec_strength=1.0, fifth_base_color_strength=1.0, fifth_base_rotation=0.0,
                              fifth_base_blend_mode="noise", fifth_base_noise_scale=24,
                              fifth_base_scale=1.0, fifth_base_color_scale=1.0, fifth_base_spec_scale=1.0, fifth_base_pattern=None,
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
                              base_scale=1.0, base_offset_x=0.5, base_offset_y=0.5, base_rotation=0.0,
                              base_flip_h=False, base_flip_v=False,
                              pattern_offset_x=0.5, pattern_offset_y=0.5,
                              pattern_paint_mode="legacy", pattern_hue_shift=0., pattern_saturation=0., **kwargs):
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
    base_color_scale = float(kwargs.pop("base_color_scale", 1.0))
    base_color_rotation = kwargs.pop("base_color_rotation", None)
    # [SPB COLOR LAB 2026-08-27] depth None = legacy crossfade pipeline
    base_color_depth = kwargs.pop("base_color_depth", None)
    base_color_flip = float(kwargs.pop("base_color_flip", 0.0) or 0.0)
    base_color_underglow = float(kwargs.pop("base_color_underglow", 0.0) or 0.0)
    pattern_fit_zone = bool(kwargs.pop("pattern_fit_zone", False))
    base_hue_offset = float(kwargs.pop("base_hue_offset", 0))
    base_saturation_adjust = float(kwargs.pop("base_saturation_adjust", 0))
    base_brightness_adjust = float(kwargs.pop("base_brightness_adjust", 0))
    monolithic_registry = kwargs.pop("monolithic_registry", None)
    _pi_stk = max(0.0, min(1.0, float(kwargs.pop("pattern_intensity", 1.0))))
    hard_mask = np.where(np.asarray(mask) > 0.1, np.asarray(mask), np.float32(0.0)).astype(np.float32)
    _stacked_primary_pat = (
        all_patterns[0].get("id")
        if all_patterns and isinstance(all_patterns[0], dict)
        else (all_patterns[0] if all_patterns else None)
    )
    _stk_pri_scale = float(all_patterns[0].get("scale", 1.0)) if all_patterns and isinstance(all_patterns[0], dict) else 1.0
    _stk_pri_rot = float(all_patterns[0].get("rotation", 0.0)) if all_patterns and isinstance(all_patterns[0], dict) else 0.0
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

    _source_paint_for_base_strength_stk = paint.copy()
    _BASE_STRENGTH_RAW = max(0.0, min(2.0, float(base_strength)))
    _BASE_STRENGTH_MIX = min(1.0, _BASE_STRENGTH_RAW)
    _BASE_PAINT_BOOST = max(1.0, _BASE_STRENGTH_RAW)
    _base_placement_for_material_stk = (
        not _base_color_mode_is_explicit(base_color_mode, base_color_strength)
        and _base_placement_active(
            base_scale, base_offset_x, base_offset_y, base_rotation, base_flip_h, base_flip_v
        )
    )
    _paint_before_base_placement_stk = paint.copy() if _base_placement_for_material_stk else None
    # SPB 2026-06-23 WHOLE-CAR-TILING FINAL FIX (stacked path) — same cure as the single
    # path: scale<1 renders the base over a CLEAN flat seed => PURE full-canvas pattern,
    # tiled finer + confined to the zone. Never tile the car-body silhouette.
    _finer_base_active_stk = bool(
        _base_placement_for_material_stk
        and not base_color_fit_zone
        and base_scale is not None and float(base_scale) < 0.999
        # SPB 2026-06-26 PASS-THROUGH GUARD (see compose_paint_mod) — a pass-through base
        # (paint_fn IS paint_none) must NOT tile the source composite; base_scale stays a
        # no-op so decals/source paint show through.
        and base_paint_fn is not paint_none
    )
    _finer_clean_seed_stk = None
    if _finer_base_active_stk:
        _bg0s = _paint_before_base_placement_stk
        _bg0s = np.asarray(_bg0s.get() if hasattr(_bg0s, "get") else _bg0s, dtype=np.float32)
        _hmf0s = np.asarray(hard_mask.get() if hasattr(hard_mask, "get") else hard_mask, dtype=np.float32)
        _zsels = _hmf0s > 0.001
        if bool(np.any(_zsels)):
            _seed_cols = np.clip(np.mean(_bg0s[:, :, :3][_zsels], axis=0), 0.0, 1.0).astype(np.float32)
        else:
            _seed_cols = np.array([0.533, 0.533, 0.533], dtype=np.float32)
        _ch0s = _bg0s.shape[2] if _bg0s.ndim == 3 else 3
        _finer_clean_seed_stk = np.empty((int(shape[0]), int(shape[1]), _ch0s), dtype=np.float32)
        _finer_clean_seed_stk[:, :, :3] = _seed_cols
        if _ch0s > 3:
            _finer_clean_seed_stk[:, :, 3:] = _bg0s[:, :, 3:]
    # SPB 2026-06-09: same Base Scale fix as compose_paint_mod — explicit base-
    # color path honors BOTH sliders (base_scale × base_color_scale).
    _effective_color_scale_stk = (
        float(base_scale if base_scale is not None else 1.0)
        * float(base_color_scale if base_color_scale is not None else 1.0)
    )
    _base_color_preseeded_stk = _base_color_replaces_source_before_material(
        base_color_mode, base_color_strength, _BASE_PAINT_BOOST
    )
    if _base_color_preseeded_stk:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, 1.0,
            monolithic_registry,
            fit_to_bbox=base_color_fit_zone,
            base_scale=_effective_color_scale_stk,
            base_offset_x=base_offset_x,
            base_offset_y=base_offset_y,
            base_rotation=base_rotation if base_color_rotation is None else base_color_rotation,
            base_flip_h=base_flip_h,
            base_flip_v=base_flip_v,
        )
    # [SPB 2026-07-08 owner] same source-paint lock as the single-base path: in
    # base_color_mode='source' the base contributes SPEC ONLY — never overwrite
    # the painter's source colors with the base's own paint art.
    _source_paint_lock_stk = str(base_color_mode or "source").strip().lower() in ("", "source", "none")
    if base_paint_fn is not paint_none and _BASE_PAINT_BOOST > 0.001 and not _source_paint_lock_stk:
        # External paint_fn expects CPU (numpy) arrays — paint is already CPU here
        try:
            _paint_before_base_fn_stk = paint.copy() if base_color_fit_zone else None
            _base_fit_mask_stk = (
                np.ones_like(hard_mask, dtype=np.float32)
                if (base_color_fit_zone or _base_placement_for_material_stk)
                else hard_mask
            )
            if _finer_base_active_stk:
                # OPAQUE-ONLY finer path (pass-through bases keep base_scale a no-op; see single path).
                _pmw_s = _BASE_PAINT_BOOST * (0.6 / max(1, active_paint_fns) if (has_any_pattern and active_paint_fns > 0 and pattern_paint_mode == "legacy") else 1.0)
                _pure_res_s = base_paint_fn(_finer_clean_seed_stk, shape, _base_fit_mask_stk, seed, pm * _pmw_s, bb * _pmw_s)
                _pure_arr_s = np.asarray(_pure_res_s) if not isinstance(_pure_res_s, np.ndarray) else _pure_res_s
                _op_s = float(np.mean(np.abs(np.asarray(_pure_arr_s, dtype=np.float32)[:, :, :3] - _seed_cols[None, None, :])))
                if _op_s < 0.045:
                    _finer_base_active_stk = False
                    _pr_s = base_paint_fn(paint, shape, _base_fit_mask_stk, seed, pm * _pmw_s, bb * _pmw_s)
                    paint = np.asarray(_pr_s) if not isinstance(_pr_s, np.ndarray) else _pr_s
                else:
                    paint = _pure_arr_s
            else:
                if has_any_pattern and active_paint_fns > 0 and pattern_paint_mode == "legacy":
                    atten = 0.6 / max(1, active_paint_fns)
                    _paint_result_stk = base_paint_fn(paint, shape, _base_fit_mask_stk, seed, pm * _BASE_PAINT_BOOST * atten, bb * _BASE_PAINT_BOOST * atten)
                else:
                    _paint_result_stk = base_paint_fn(paint, shape, _base_fit_mask_stk, seed, pm * _BASE_PAINT_BOOST, bb * _BASE_PAINT_BOOST)
                paint = np.asarray(_paint_result_stk) if not isinstance(_paint_result_stk, np.ndarray) else _paint_result_stk
            if base_color_fit_zone and _paint_before_base_fn_stk is not None:
                paint = _fit_paint_source_to_mask_bbox(paint, _paint_before_base_fn_stk, hard_mask)
        except Exception as _bp_err_stk:
            raise RuntimeError(f"Stacked base paint renderer failed [{base_id}]: {_bp_err_stk}") from _bp_err_stk

    if not _base_color_preseeded_stk:
        paint = _apply_base_color_override(
            paint, shape, hard_mask, seed,
            base_color_mode, base_color, base_color_source, base_color_strength,
            monolithic_registry,
            fit_to_bbox=base_color_fit_zone,
            base_color_depth=base_color_depth,
            base_color_flip=base_color_flip,
            base_color_underglow=base_color_underglow,
            base_scale=_effective_color_scale_stk,
            base_offset_x=base_offset_x,
            base_offset_y=base_offset_y,
            base_rotation=base_rotation if base_color_rotation is None else base_color_rotation,
            base_flip_h=base_flip_h,
            base_flip_v=base_flip_v,
        )

    # HSB adjustments (hue shift, saturation, brightness)
    _hue_off = base_hue_offset
    _sat_adj = base_saturation_adjust
    _bri_adj = base_brightness_adjust
    if _hue_off or _sat_adj or _bri_adj:
        paint = _apply_hsb_adjustments(paint, hard_mask, _hue_off, _sat_adj, _bri_adj)

    # [SPB WHOLE-CANVAS-TILE 2026-08-15] Stacked twin of the fix above: in source mode the base
    # paint pass was skipped (_source_paint_lock_stk), so placement has nothing base-derived to
    # transform — tiling here replicated the painter's source composite as mini-cars.
    if not _base_color_mode_is_explicit(base_color_mode, base_color_strength) and not _source_paint_lock_stk:
        if _finer_base_active_stk:
            _h0s, _w0s = int(shape[0]), int(shape[1])
            _pure_finer_stk = _transform_base_color_source(
                np.clip(np.asarray(paint)[:, :, :3], 0.0, 1.0).astype(np.float32), (_h0s, _w0s),
                scale=base_scale, offset_x=base_offset_x, offset_y=base_offset_y,
                rotation=base_rotation, flip_h=bool(base_flip_h), flip_v=bool(base_flip_v),
            )
            _bgps = _paint_before_base_placement_stk
            _bgps = np.asarray(_bgps.get() if hasattr(_bgps, "get") else _bgps, dtype=np.float32)
            _hm3s = (np.asarray(hard_mask.get() if hasattr(hard_mask, "get") else hard_mask, dtype=np.float32)[:, :, np.newaxis] > 0.001)
            paint = np.array(paint, dtype=np.float32, copy=True)
            paint[:, :, :3] = np.where(_hm3s, _pure_finer_stk, np.clip(_bgps[:, :, :3], 0.0, 1.0)).astype(np.float32, copy=False)
        else:
            paint = _apply_base_placement_to_paint(
                paint,
                shape,
                hard_mask,
                base_scale=base_scale,
                base_offset_x=base_offset_x,
                base_offset_y=base_offset_y,
                base_rotation=base_rotation,
                base_flip_h=base_flip_h,
                base_flip_v=base_flip_v,
                background_paint=_paint_before_base_placement_stk,
            )

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

    paint = _blend_base_result_over_source(
        _source_paint_for_base_strength_stk, paint, hard_mask, _BASE_STRENGTH_MIX
    )

    _PAT_PAINT_BOOST = 1.8
    # BUGFIX 2026-10-04: Strength Map + per-layer Blend now reach the paint (were spec-only).
    _psm_stk = kwargs.get("pattern_strength_map")
    _psm_stk_before = paint.copy() if (_psm_stk is not None and all_patterns) else None
    for layer_idx, layer in enumerate(all_patterns):
        pat_id = layer["id"]
        opacity = float(layer.get("opacity", 1.0))
        scale = float(layer.get("scale", 1.0))
        rotation = float(layer.get("rotation", 0))
        layer_fit_zone = bool(layer.get("fit_zone", pattern_fit_zone))
        if pat_id not in PATTERN_REGISTRY or opacity <= 0:
            continue
        _lb_mode = str(layer.get("blend_mode", "normal") or "normal").lower()
        _lb_before = paint.copy() if _lb_mode in _PAINT_LAYER_BLEND_MODES else None
        pattern = PATTERN_REGISTRY[pat_id]
        pat_paint_fn, tex_fn = pattern_paint_source(pattern, pattern_paint_mode)
        pat_paint_fn = pat_paint_fn or paint_none
        image_path = pattern_color_source(pat_id, pattern, pattern_paint_mode)
        if image_path:
            from engine.render import _load_image_pattern, _load_color_image_pattern
            _img_ox_stk = float(layer.get("offset_x", pattern_offset_x))
            _img_oy_stk = float(layer.get("offset_y", pattern_offset_y))
            # Get the full color version
            if pattern_paint_mode in ("overlay", "blend"):
                rgba = load_pattern_artwork(image_path, shape, scale=scale, rotation=rotation,
                    offset_x=_img_ox_stk, offset_y=_img_oy_stk,
                    flip_h=bool(layer.get("flip_h", False)), flip_v=bool(layer.get("flip_v", False)),
                    fit_zone=layer_fit_zone, mask=hard_mask)
            else:
                rgba = _load_color_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if rgba is not None:
                # Per-pattern offset (supports Fit-to-Zone and Manual Placement)
                if pattern_paint_mode == "legacy" and (abs(_img_ox_stk - 0.5) > 0.001 or abs(_img_oy_stk - 0.5) > 0.001):
                    for _ch in range(rgba.shape[2]):
                        _apply_pattern_offset(rgba[:, :, _ch], shape, _img_ox_stk, _img_oy_stk)
                if layer_fit_zone and pattern_paint_mode == "legacy":
                    rgba = _fit_pattern_to_mask_bbox(rgba, hard_mask)
                r, g, b, alpha = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3]
                # Scale alpha by opacity, zone pattern_intensity, and mask (5% = hint, 100% = full)
                alpha_3d = (alpha[:, :, np.newaxis] * opacity * _pi_stk) * hard_mask[:, :, np.newaxis]
                rgb_3d = rgba[:, :, :3]
                # All CPU blend
                if pattern_paint_mode in ("overlay", "blend"):
                    paint = composite_pattern_pixels(paint, rgb_3d, hard_mask * alpha,
                        amount=opacity * _pi_stk * np.clip(spec_mult, 0, 1), mode=pattern_paint_mode,
                        hue_shift=float(layer.get("hue_shift", 0)), saturation=float(layer.get("saturation", 0)))
                else:
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
                    if layer_fit_zone:
                        pv = _fit_pattern_to_mask_bbox(pv, hard_mask)
                    pv_3d = (pv[:, :, np.newaxis] * opacity * _pi_stk * spec_mult * 0.35)
                    # Mask so pattern only modifies paint INSIDE the zone
                    mask_3d = hard_mask[:, :, np.newaxis]
                    pv_masked = pv_3d * mask_3d
                    paint = np.clip(paint * (1.0 - pv_masked), 0, 1).astype(np.float32)
        elif pat_paint_fn is not paint_none or (pattern_paint_mode in ("overlay", "blend") and tex_fn is not None):
            if pattern_paint_mode in ("overlay", "blend"):
                paint = composite_pattern_layer(
                    pat_paint_fn, paint, shape, hard_mask, seed + layer_idx * 7,
                    opacity=opacity, strength=spec_mult, intensity=_pi_stk,
                    hue_shift=float(layer.get("hue_shift", 0)), saturation=float(layer.get("saturation", 0)),
                    mode=pattern_paint_mode, texture_fn=tex_fn, scale=scale, rotation=rotation,
                    offset_x=float(layer.get("offset_x", pattern_offset_x)),
                    offset_y=float(layer.get("offset_y", pattern_offset_y)),
                    fit_zone=layer_fit_zone)
                paint = _stack_layer_paint_blend(_lb_before, paint, _lb_mode)
                continue
            atten = opacity * 0.6 / max(1, active_paint_fns)
            layer_seed = seed + layer_idx * 7
            # External paint_fn expects CPU arrays — paint is already CPU here
            paint_before_layer = paint.copy()
            try:
                _layer_result = render_pattern_paint(pat_paint_fn, paint, shape, hard_mask, layer_seed, pm * atten * spec_mult * _PAT_PAINT_BOOST, bb * atten * spec_mult * _PAT_PAINT_BOOST, scale=scale, rotation=rotation, offset_x=float(layer.get("offset_x", pattern_offset_x)), offset_y=float(layer.get("offset_y", pattern_offset_y)), fit_zone=layer_fit_zone)
                paint = np.asarray(_layer_result) if not isinstance(_layer_result, np.ndarray) else _layer_result
            except Exception as _pp_err_stk:
                raise RuntimeError(f"Stacked pattern paint renderer failed [{pat_id}]: {_pp_err_stk}") from _pp_err_stk
            _tex_ox_stk = float(layer.get("offset_x", pattern_offset_x))
            _tex_oy_stk = float(layer.get("offset_y", pattern_offset_y))
            # Same single-pass direct-pattern placement as the primary pattern.
            _direct_pattern_paint = getattr(pat_paint_fn, "_spb_pattern_direct_paint", False)
            if _direct_pattern_paint:
                if _base_color_mode_is_explicit(base_color_mode, base_color_strength):
                    paint = _tint_direct_pattern_paint(paint, paint_before_layer, hard_mask, base_color_strength)
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
                    if layer_fit_zone:
                        pv = _fit_pattern_to_mask_bbox(pv, hard_mask)
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
        paint = _stack_layer_paint_blend(_lb_before, paint, _lb_mode)
    if _psm_stk_before is not None:
        paint = _paint_strength_map_blend(_psm_stk_before, paint, _psm_stk)
        _psm_stk_before = None

    if second_base_strength > 0.001 and (second_base or second_base_color_source or second_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _sb_shape, hard_mask, seed + 7777,
                    base_scale=second_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"2nd stacked base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(second_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_st_cpu.shape[0], _paint_overlay_st_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(second_base_color_strength)))
                _paint_overlay_st_cpu[:, :, :3] = _paint_overlay_st_cpu[:, :, :3] * (1.0 - _sb_mask3d * _ovcs) + _ovcp * (_sb_mask3d * _ovcs)
            elif _sb_color_src:
                print(f"    [PAINT OVERLAY 2nd STACKED] WARNING: special source '{_sb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _sb_color = second_base_color if second_base_color is not None else [1.0, 1.0, 1.0]
                _sb_r = float(_sb_color[0]) if len(_sb_color) > 0 else 1.0
                _sb_g = float(_sb_color[1]) if len(_sb_color) > 1 else 1.0
                _sb_b = float(_sb_color[2]) if len(_sb_color) > 2 else 1.0
                _sb_rgb = np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(second_base_color_strength)))
                _paint_overlay_st_cpu[:, :, :3] = _paint_overlay_st_cpu[:, :, :3] * (1.0 - _sb_mask3d * _ovcs) + _sb_rgb * (_sb_mask3d * _ovcs)
            if second_base and second_base in BASE_REGISTRY:
                _sb_def2 = BASE_REGISTRY[second_base]
                _sb_pfn = _sb_def2.get("paint_fn", paint_none)
                # Skip base paint_fn when From Special is active (same fix as compose_paint_mod)
                if _sb_pfn is not paint_none and not _sb_color_src and _overlay_should_apply_base_paint_fn(second_base_color_source):
                    _paint_overlay_st_cpu = _sb_pfn(_paint_overlay_st_cpu, _sb_shape, hard_mask, seed + 7777, 1.0, 0.0)
                    _paint_overlay_st_cpu = np.asarray(_paint_overlay_st_cpu) if not isinstance(_paint_overlay_st_cpu, np.ndarray) else _paint_overlay_st_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _sb_bm_norm = _normalize_second_base_blend_mode(second_base_blend_mode)
            _pat_id_st = _resolve_overlay_pattern_mask_id(
                second_base_pattern, None, second_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            _sb_pat_mask_st = _get_overlay_pattern_mask(
                second_base_pattern, _pat_id_st, _stacked_primary_pat,
                _stk_pri_scale, _stk_pri_rot, pattern_offset_x, pattern_offset_y,
                second_base_pattern_scale, second_base_pattern_rotation,
                second_base_pattern_offset_x, second_base_pattern_offset_y,
                _sb_shape, hard_mask, seed, 1.0,
                second_base_pattern_opacity, second_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _sb_pat_mask_st is not None:
                if second_base_pattern_invert:
                    _sb_pat_mask_st = 1.0 - _sb_pat_mask_st
                if second_base_pattern_harden:
                    _sb_pat_mask_st = _harden_overlay_pattern_mask(_sb_pat_mask_st)
            _alpha_sb_st = get_base_overlay_alpha(
                _sb_shape, second_base_strength, second_base_blend_mode,
                noise_scale=int(second_base_noise_scale), seed=seed,
                pattern_mask=_sb_pat_mask_st, zone_mask=hard_mask,
                noise_fn=multi_scale_noise, overlay_scale=max(0.01, min(5.0, float(second_base_scale)))
            )
            _alpha_sb_st3 = _alpha_sb_st[:, :, np.newaxis]
            # [SPB-OVERLAY-PARITY 2026-08-20] base-HSB used to be applied HERE (to the
            # overlay) AND again after the blend - the only tier that got it twice.
            # The post-blend application below is the one every tier shares.
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
        except Exception as _e:
            raise RuntimeError(f"2nd stacked base overlay paint renderer failed: {_e}") from _e

    if third_base_strength > 0.001 and (third_base or third_base_color_source or third_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _tb_shape, hard_mask, seed + 9999,
                    base_scale=third_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"3rd stacked base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(third_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_tb_st_cpu.shape[0], _paint_overlay_tb_st_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(third_base_color_strength)))
                _paint_overlay_tb_st_cpu[:, :, :3] = _paint_overlay_tb_st_cpu[:, :, :3] * (1.0 - _tb_mask3d * _ovcs) + _ovcp * (_tb_mask3d * _ovcs)
            elif _tb_color_src:
                print(f"    [PAINT OVERLAY 3rd STACKED] WARNING: special source '{_tb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _tb_color = third_base_color if third_base_color is not None else [1.0, 1.0, 1.0]
                _tb_r = float(_tb_color[0]) if len(_tb_color) > 0 else 1.0
                _tb_g = float(_tb_color[1]) if len(_tb_color) > 1 else 1.0
                _tb_b = float(_tb_color[2]) if len(_tb_color) > 2 else 1.0
                _tb_rgb = np.array([_tb_r, _tb_g, _tb_b], dtype=np.float32)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(third_base_color_strength)))
                _paint_overlay_tb_st_cpu[:, :, :3] = _paint_overlay_tb_st_cpu[:, :, :3] * (1.0 - _tb_mask3d * _ovcs) + _tb_rgb * (_tb_mask3d * _ovcs)
            if third_base and third_base in BASE_REGISTRY:
                _tb_def2 = BASE_REGISTRY[third_base]
                _tb_pfn = _tb_def2.get("paint_fn", paint_none)
                if _tb_pfn is not paint_none and not _tb_color_src and _overlay_should_apply_base_paint_fn(third_base_color_source):
                    _paint_overlay_tb_st_cpu = _tb_pfn(_paint_overlay_tb_st_cpu, _tb_shape, hard_mask, seed + 9999, 1.0, 0.0)
                    _paint_overlay_tb_st_cpu = np.asarray(_paint_overlay_tb_st_cpu) if not isinstance(_paint_overlay_tb_st_cpu, np.ndarray) else _paint_overlay_tb_st_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _tb_bm_norm = _normalize_second_base_blend_mode(third_base_blend_mode)
            _pat_id_tb = _resolve_overlay_pattern_mask_id(
                third_base_pattern, None, third_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            _tb_pat_mask_st = _get_overlay_pattern_mask(
                third_base_pattern, _pat_id_tb, _stacked_primary_pat,
                _stk_pri_scale, _stk_pri_rot, pattern_offset_x, pattern_offset_y,
                third_base_pattern_scale, third_base_pattern_rotation,
                third_base_pattern_offset_x, third_base_pattern_offset_y,
                _tb_shape, hard_mask, seed, 1.0,
                third_base_pattern_opacity, third_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _tb_pat_mask_st is not None:
                if third_base_pattern_invert:
                    _tb_pat_mask_st = 1.0 - _tb_pat_mask_st
                if third_base_pattern_harden:
                    _tb_pat_mask_st = _harden_overlay_pattern_mask(_tb_pat_mask_st)
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
        except Exception as _e:
            raise RuntimeError(f"3rd stacked base overlay paint renderer failed: {_e}") from _e

    if fourth_base_strength > 0.001 and (fourth_base or fourth_base_color_source or fourth_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _fb_shape, hard_mask, seed + 11111,
                    base_scale=fourth_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"4th stacked base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(fourth_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_fb_st_cpu.shape[0], _paint_overlay_fb_st_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(fourth_base_color_strength)))
                _paint_overlay_fb_st_cpu[:, :, :3] = _paint_overlay_fb_st_cpu[:, :, :3] * (1.0 - _fb_mask3d * _ovcs) + _ovcp * (_fb_mask3d * _ovcs)
            elif _fb_color_src:
                print(f"    [PAINT OVERLAY 4th STACKED] WARNING: special source '{_fb_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fb_color = fourth_base_color if fourth_base_color is not None else [1.0, 1.0, 1.0]
                _fb_r = float(_fb_color[0]) if len(_fb_color) > 0 else 1.0
                _fb_g = float(_fb_color[1]) if len(_fb_color) > 1 else 1.0
                _fb_b = float(_fb_color[2]) if len(_fb_color) > 2 else 1.0
                _fb_rgb = np.array([_fb_r, _fb_g, _fb_b], dtype=np.float32)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(fourth_base_color_strength)))
                _paint_overlay_fb_st_cpu[:, :, :3] = _paint_overlay_fb_st_cpu[:, :, :3] * (1.0 - _fb_mask3d * _ovcs) + _fb_rgb * (_fb_mask3d * _ovcs)
            if fourth_base and fourth_base in BASE_REGISTRY:
                _fb_def2 = BASE_REGISTRY[fourth_base]
                _fb_pfn = _fb_def2.get("paint_fn", paint_none)
                if _fb_pfn is not paint_none and not _fb_color_src and _overlay_should_apply_base_paint_fn(fourth_base_color_source):
                    _paint_overlay_fb_st_cpu = _fb_pfn(_paint_overlay_fb_st_cpu, _fb_shape, hard_mask, seed + 11111, 1.0, 0.0)
                    _paint_overlay_fb_st_cpu = np.asarray(_paint_overlay_fb_st_cpu) if not isinstance(_paint_overlay_fb_st_cpu, np.ndarray) else _paint_overlay_fb_st_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _fb_bm_norm = _normalize_second_base_blend_mode(fourth_base_blend_mode)
            _pat_id_fb = _resolve_overlay_pattern_mask_id(
                fourth_base_pattern, None, fourth_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            _fb_pat_mask_st = _get_overlay_pattern_mask(
                fourth_base_pattern, _pat_id_fb, _stacked_primary_pat,
                _stk_pri_scale, _stk_pri_rot, pattern_offset_x, pattern_offset_y,
                fourth_base_pattern_scale, fourth_base_pattern_rotation,
                fourth_base_pattern_offset_x, fourth_base_pattern_offset_y,
                _fb_shape, hard_mask, seed, 1.0,
                fourth_base_pattern_opacity, fourth_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _fb_pat_mask_st is not None:
                if fourth_base_pattern_invert:
                    _fb_pat_mask_st = 1.0 - _fb_pat_mask_st
                if fourth_base_pattern_harden:
                    _fb_pat_mask_st = _harden_overlay_pattern_mask(_fb_pat_mask_st)
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
        except Exception as _e:
            raise RuntimeError(f"4th stacked base overlay paint renderer failed: {_e}") from _e

    if fifth_base_strength > 0.001 and (fifth_base or fifth_base_color_source or fifth_base_color is not None):
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
                _color_paint = _invoke_mono_paint_fn_for_color_source(
                    _mono_paint_fn, paint, _fif_shape, hard_mask, seed + 13333,
                    base_scale=fifth_base_color_scale,
                )
                if _color_paint is None:
                    raise RuntimeError(
                        f"5th stacked base overlay mono paint renderer returned no paint [{_mono_id}]"
                    )
                _color_paint = _color_paint.get() if hasattr(_color_paint, 'get') else np.asarray(_color_paint)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Rotation + Color Strength parity.
                _ovcp = np.asarray(np.clip(_color_paint[:, :, :3], 0.0, 1.0), dtype=np.float32)
                _ovrot = float(fifth_base_rotation) % 360.0
                if _ovrot:
                    _ovcp = np.stack([_rotate_single_array(_ovcp[:, :, _c], _ovrot, (_paint_overlay_fif_st_cpu.shape[0], _paint_overlay_fif_st_cpu.shape[1])) for _c in range(3)], axis=2)
                _ovcs = max(0.0, min(1.0, float(fifth_base_color_strength)))
                _paint_overlay_fif_st_cpu[:, :, :3] = _paint_overlay_fif_st_cpu[:, :, :3] * (1.0 - _fif_mask3d * _ovcs) + _ovcp * (_fif_mask3d * _ovcs)
            elif _fif_color_src:
                print(f"    [PAINT OVERLAY 5th STACKED] WARNING: special source '{_fif_color_src}' not found in registry; skipping solid color fallback")
            else:
                _fif_color = fifth_base_color if fifth_base_color is not None else [1.0, 1.0, 1.0]
                _fif_r = float(_fif_color[0]) if len(_fif_color) > 0 else 1.0
                _fif_g = float(_fif_color[1]) if len(_fif_color) > 1 else 1.0
                _fif_b = float(_fif_color[2]) if len(_fif_color) > 2 else 1.0
                _fif_rgb = np.array([_fif_r, _fif_g, _fif_b], dtype=np.float32)
                # [SPB-OVERLAY-PARITY-2 2026-08-20] Color Strength parity with the
                # primary base: fade the chosen colour over the underlying paint.
                _ovcs = max(0.0, min(1.0, float(fifth_base_color_strength)))
                _paint_overlay_fif_st_cpu[:, :, :3] = _paint_overlay_fif_st_cpu[:, :, :3] * (1.0 - _fif_mask3d * _ovcs) + _fif_rgb * (_fif_mask3d * _ovcs)
            if fifth_base and fifth_base in BASE_REGISTRY:
                _fif_def2 = BASE_REGISTRY[fifth_base]
                _fif_pfn = _fif_def2.get("paint_fn", paint_none)
                if _fif_pfn is not paint_none and not _fif_color_src and _overlay_should_apply_base_paint_fn(fifth_base_color_source):
                    _paint_overlay_fif_st_cpu = _fif_pfn(_paint_overlay_fif_st_cpu, _fif_shape, hard_mask, seed + 13333, 1.0, 0.0)
                    _paint_overlay_fif_st_cpu = np.asarray(_paint_overlay_fif_st_cpu) if not isinstance(_paint_overlay_fif_st_cpu, np.ndarray) else _paint_overlay_fif_st_cpu
                # [SPB-OVERLAY-PARITY 2026-08-20] the colour flood above already applied
                # the chosen colour once; a re-multiply here squared it (0.5 -> 0.25,
                # every overlay colour dark + oversaturated; only pure white survived).
            _fif_bm_norm = _normalize_second_base_blend_mode(fifth_base_blend_mode)
            _pat_id_fif = _resolve_overlay_pattern_mask_id(
                fifth_base_pattern, None, fifth_base_blend_mode,
                stacked_primary_id=_stacked_primary_pat,
            )
            _fif_pat_mask_st = _get_overlay_pattern_mask(
                fifth_base_pattern, _pat_id_fif, _stacked_primary_pat,
                _stk_pri_scale, _stk_pri_rot, pattern_offset_x, pattern_offset_y,
                fifth_base_pattern_scale, fifth_base_pattern_rotation,
                fifth_base_pattern_offset_x, fifth_base_pattern_offset_y,
                _fif_shape, hard_mask, seed, 1.0,
                fifth_base_pattern_opacity, fifth_base_pattern_strength,
                fit_zone=pattern_fit_zone,
            )
            if _fif_pat_mask_st is not None:
                if fifth_base_pattern_invert:
                    _fif_pat_mask_st = 1.0 - _fif_pat_mask_st
                if fifth_base_pattern_harden:
                    _fif_pat_mask_st = _harden_overlay_pattern_mask(_fif_pat_mask_st)
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
        except Exception as _e:
            raise RuntimeError(f"5th stacked base overlay paint renderer failed: {_e}") from _e

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

def _resolve_finish_spec(finish_id, shape, mask, seed, sm, monolithic_registry=None, registry_type=None):
    """Resolve a finish ID to (M_arr, R_arr, CC_arr) arrays.

    Checks BASE_REGISTRY first (uses base_spec_fn or static M/R/CC values),
    then MONOLITHIC_REGISTRY (uses spec_fn which returns a 4-channel spec).
    ``registry_type`` can pin one of those registries when a catalog id exists
    in both. Easy Spec Sculpt uses that pin so the real thumbnail a customer
    clicks is guaranteed to be the material that actually renders.
    Returns float32 arrays of shape (H, W).
    """
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY as _MONO
    mono_reg = monolithic_registry if monolithic_registry is not None else _MONO
    h, w = shape[0], shape[1]
    registry_type = str(registry_type or "").strip().lower() or None
    if registry_type not in {None, "base", "monolithic"}:
        raise ValueError(f"Unknown finish registry type: {registry_type}")

    if registry_type != "monolithic" and finish_id in BASE_REGISTRY:
        base = BASE_REGISTRY[finish_id]
        base_M = float(base["M"])
        base_R = float(base["R"])
        base_CC = float(base.get("CC", 16))
        _seed_off = abs(hash(finish_id)) % 10000
        if base.get("base_spec_fn"):
            result = _cached_base_spec_result(finish_id, base["base_spec_fn"], (h, w), seed + _seed_off, sm, base_M, base_R)
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

    if registry_type != "base" and finish_id in mono_reg:
        entry = mono_reg[finish_id]
        spec_fn = entry[0]
        try:
            spec_arr = spec_fn((h, w), mask, seed, sm)
        except Exception as exc:
            raise RuntimeError(f"Mix finish spec renderer failed [{finish_id}]: {exc}") from exc
        spec_arr = np.asarray(spec_arr)
        if spec_arr.ndim == 3 and spec_arr.shape[2] >= 3:
            M_arr = spec_arr[:, :, 0].astype(np.float32)
            R_arr = spec_arr[:, :, 1].astype(np.float32)
            CC_arr = spec_arr[:, :, 2].astype(np.float32)
        else:
            raise RuntimeError(
                f"Mix finish spec renderer returned invalid spec shape [{finish_id}]: "
                f"{getattr(spec_arr, 'shape', None)}"
            )
        return M_arr, R_arr, CC_arr

    qualifier = f" ({registry_type})" if registry_type else ""
    raise ValueError(f"Unknown mix finish spec ID{qualifier}: {finish_id}")


def _resolve_finish_paint_fn(finish_id, monolithic_registry=None):
    """Resolve a finish ID to its paint_fn callable.

    Raises when the ID does not resolve; mix previews must not silently
    substitute no-op paint for a selected finish.
    """
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY as _MONO
    mono_reg = monolithic_registry if monolithic_registry is not None else _MONO

    if finish_id in BASE_REGISTRY:
        return BASE_REGISTRY[finish_id].get("paint_fn", paint_none)
    if finish_id in mono_reg:
        return mono_reg[finish_id][1]
    raise ValueError(f"Unknown mix finish paint ID: {finish_id}")


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
            raise RuntimeError(f"Mix paint renderer failed [{fid}]: {e}") from e

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
