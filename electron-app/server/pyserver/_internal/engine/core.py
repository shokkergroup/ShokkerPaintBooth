"""
engine/core.py - Primitive Functions
=====================================
All low-level utilities. Nothing that renders finishes lives here.
Everything else imports FROM here - this module imports nothing from engine/.

CONTENTS:
  - TGA file writers (write_tga_32bit, write_tga_24bit)
  - Noise generators (multi_scale_noise, perlin_multi_octave, simplex_noise_2d)
  - Coordinate helpers (get_mgrid)
  - Color conversion (hsv_to_rgb_vec, rgb_to_hsv_array, rgb_to_lab, hex/named parsing)
  - Color analysis & masking (analyze_paint_colors, build_zone_mask)
  - Natural language color parsing (parse_color_description)
  - Numerical helpers (close_enough, clamp, safe_divide)
  - Intensity presets

CHANNEL SEMANTICS:
  Spec channels follow the SPEC_MAP_REFERENCE.md convention:
      R = Metallic   (0=dielectric, 255=full metal)
      G = Roughness  (0=mirror, 255=matte) -- enforced floor SPEC_ROUGHNESS_MIN for non-chrome
      B = Clearcoat  (0=none, 16=max gloss, 255=destroyed) -- enforced floor SPEC_CLEARCOAT_MIN
      A = Specular Mask (rarely consumer-facing)

COLOR SPACE ASSUMPTIONS:
  Paint arrays are assumed to be sRGB-encoded float32 in [0, 1] (not linear). Spec maps
  are uint8 in the canonical sim convention. Color conversions (HSV/Lab) operate on the
  sRGB values directly without gamma correction -- iRacing does its own gamma so the
  perceived hue is what the artist sees in the editor.

PREMULTIPLIED ALPHA:
  Paint arrays are NOT premultiplied. Alpha is the 4th channel; RGB is straight.
  Compose only multiplies through alpha at the final output stage.

ENGINE VERSION:
  Single source of truth for the core primitives. Bumped when the public API of any
  exported function changes (signatures, return shapes, validated input types).

FIX GUIDE:
  - Noise looks wrong         -> edit multi_scale_noise or perlin_multi_octave
  - Color matching is off     -> edit build_zone_mask
  - Color words don't parse   -> edit COLOR_WORD_MAP or parse_color_description
  - TGA files corrupted       -> edit write_tga_32bit / write_tga_24bit
"""

import math
import logging
import numpy as np
from PIL import Image
import struct
import cv2
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger("engine.core")

# Engine version constant -- single source of truth, bumped on public API changes.
CORE_ENGINE_VERSION = "6.1.2-platinum"

# ================================================================
# SPEC MAP CONSTANTS - canonical values used across the engine
# ================================================================
# These constants encode iron rules from SPEC_MAP_REFERENCE.md:
#   - Roughness must be >= SPEC_ROUGHNESS_MIN (15) for non-chrome finishes
#     (otherwise iRacing's GGX shader produces unrealistic mirror-flat highlights)
#   - Clearcoat must be >= SPEC_CLEARCOAT_MIN (16) for "max gloss" finishes
#     (CC=0 disables clearcoat entirely; CC<16 is the buggy half-coat zone)
#   - Chrome bypasses the roughness floor when Metallic >= SPEC_METALLIC_CHROME_THRESHOLD
SPEC_ROUGHNESS_MIN = 15       # GGX floor: min roughness for non-chrome finishes
SPEC_CLEARCOAT_MIN = 16       # Clearcoat minimum for "max gloss" (factory fresh)
SPEC_METALLIC_CHROME_THRESHOLD = 240  # M >= 240 = chrome (roughness floor bypassed)
SPEC_CHANNEL_MAX = 255        # Max value for any 8-bit spec channel
SPEC_CHANNEL_MIN = 0          # Min value for any 8-bit spec channel
SPEC_DEFAULT_OUTSIDE_M = 5.0  # Metallic value outside zone mask
SPEC_DEFAULT_OUTSIDE_R = 100.0  # Roughness value outside zone mask

# Numerical safety constants
EPSILON = 1e-8                # General numerical floor (avoid divide-by-zero)
DEFAULT_TOLERANCE = 1e-3      # Default tolerance for close_enough()

# Verbose debug toggle: when True, extra debug logs are emitted from low-level helpers.
# Set engine_core_set_verbose(True) at runtime to enable.
_VERBOSE = False


def engine_core_set_verbose(flag: bool) -> None:
    """Toggle verbose debug output across this module.

    Args:
        flag: True to enable per-call debug logs, False to silence.
    """
    global _VERBOSE
    _VERBOSE = bool(flag)


def _vlog(msg: str, *args: Any) -> None:
    """Internal: emit a debug message only when verbose mode is on."""
    if _VERBOSE:
        logger.debug(msg, *args)


# GPU acceleration (optional) -- lazy import to avoid circular deps.
# When CuPy is unavailable this module falls back to numpy transparently;
# callers do not need to branch on GPU availability.
try:
    from engine.gpu import xp, to_cpu, to_gpu, is_gpu
except ImportError:
    xp = np
    def to_cpu(a): return a
    def to_gpu(a): return a
    def is_gpu(): return False


# ================================================================
# NUMERICAL & VALIDATION HELPERS
# ================================================================

def close_enough(a: Union[float, np.ndarray], b: Union[float, np.ndarray],
                 tol: float = DEFAULT_TOLERANCE) -> bool:
    """Return True if the absolute difference between a and b is <= tol.

    Works for scalars and arrays. For arrays, returns True only if every
    element pair is within tolerance.

    Args:
        a: First value or array.
        b: Second value or array.
        tol: Maximum allowed absolute difference.

    Returns:
        bool: True when a and b are within tol everywhere.
    """
    diff = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))
    return bool(np.all(diff <= float(tol)))


def clamp(value: Union[int, float], lo: Union[int, float], hi: Union[int, float]) -> float:
    """Clamp a scalar value to [lo, hi]. Returns float."""
    return float(max(lo, min(hi, value)))


def safe_divide(numer: Union[float, np.ndarray], denom: Union[float, np.ndarray],
                fallback: float = 0.0) -> Union[float, np.ndarray]:
    """Divide numer / denom, returning fallback wherever denom is ~0.

    Avoids RuntimeWarning: invalid value encountered in true_divide.
    """
    denom_arr = np.asarray(denom, dtype=np.float32)
    safe_denom = np.where(np.abs(denom_arr) < EPSILON, 1.0, denom_arr)
    out = np.asarray(numer, dtype=np.float32) / safe_denom
    return np.where(np.abs(denom_arr) < EPSILON, fallback, out)


def validate_spec_output(spec: np.ndarray, context: str = "") -> np.ndarray:
    """Validate that a spec map array is uint8, 4-channel, and contiguous.

    Args:
        spec: Candidate (H, W, 4) uint8 array.
        context: Optional caller name for the error message.

    Returns:
        The validated array (possibly coerced to uint8). Raises ValueError on
        irrecoverable shape mismatches.
    """
    label = f"[{context}] " if context else ""
    if not isinstance(spec, np.ndarray):
        raise ValueError(f"{label}spec output must be numpy.ndarray, got {type(spec).__name__}")
    if spec.ndim != 3:
        raise ValueError(f"{label}spec must be 3-dim (H, W, 4); got shape {spec.shape}")
    if spec.shape[2] != 4:
        raise ValueError(f"{label}spec must have 4 channels (M, R, CC, A); got {spec.shape[2]}")
    if spec.dtype != np.uint8:
        spec = np.clip(spec, 0, 255).astype(np.uint8)
    if not spec.flags['C_CONTIGUOUS']:
        spec = np.ascontiguousarray(spec)
    if not np.isfinite(spec).all():
        # uint8 cannot hold NaN/Inf, but the upstream float input might have
        logger.warning("%sspec contained non-finite values prior to uint8 conversion", label)
    return spec


def enforce_iron_rules(spec: np.ndarray) -> np.ndarray:
    """Apply the engine's iron rules in place: CC>=16, R>=15 for non-chrome.

    Used as a final safety net at the very end of any pipeline that produces a
    spec map. Modifies the array in place AND returns it for chaining.

    Args:
        spec: (H, W, 4) uint8 spec array (M, R, CC, A).

    Returns:
        The same array with iron rules enforced.
    """
    if spec is None or spec.size == 0:
        return spec
    M = spec[:, :, 0]
    R = spec[:, :, 1]
    CC = spec[:, :, 2]
    # CC floor: every pixel with any clearcoat at all must be at least SPEC_CLEARCOAT_MIN
    np.maximum(CC, SPEC_CLEARCOAT_MIN, out=CC, where=(CC > 0))
    # R floor: non-chrome must respect the GGX roughness minimum
    non_chrome = M < SPEC_METALLIC_CHROME_THRESHOLD
    np.maximum(R, SPEC_ROUGHNESS_MIN, out=R, where=non_chrome)
    return spec


# ================================================================
# TGA FILE WRITERS
# ================================================================

def write_tga_32bit(filepath: str, rgba_array: np.ndarray) -> None:
    """Write a 32-bit BGRA TGA file (paint + alpha). iRacing uses 32-bit for paint.

    The TGA header is a single 18-byte struct.pack call (8x faster than per-field
    packing). Channel swap RGBA->BGRA uses fancy indexing (zero allocation beyond
    the contiguous copy required for tobytes()).

    Args:
        filepath: Destination path (any extension; TGA bytes regardless).
        rgba_array: (H, W, 4) uint8 or convertible array. (H, W, 3) inputs are
            auto-promoted with alpha=255. Other shapes are rejected with a warning.

    Returns:
        None. Errors are logged, not raised, so a failed write does not
        abort an in-progress render.
    """
    try:
        rgba_array = np.asarray(rgba_array)
        if rgba_array.ndim != 3 or rgba_array.shape[2] < 4:
            logger.warning("write_tga_32bit: expected (H,W,4) array, got shape %s (file=%s)",
                           rgba_array.shape, filepath)
            if rgba_array.ndim == 3 and rgba_array.shape[2] == 3:
                # Auto-add alpha channel (fully opaque) -- pre-allocate instead of concat
                h0, w0 = rgba_array.shape[:2]
                tmp = np.empty((h0, w0, 4), dtype=np.uint8)
                tmp[:, :, :3] = rgba_array if rgba_array.dtype == np.uint8 else np.clip(rgba_array, 0, 255).astype(np.uint8)
                tmp[:, :, 3] = 255
                rgba_array = tmp
            else:
                return
        # Edge case: zero-area arrays would silently emit a malformed TGA
        if rgba_array.shape[0] == 0 or rgba_array.shape[1] == 0:
            logger.warning("write_tga_32bit: refusing to write zero-area image (file=%s)", filepath)
            return
        # Ensure uint8 output
        if rgba_array.dtype != np.uint8:
            rgba_array = np.clip(rgba_array, 0, 255).astype(np.uint8)
        h, w = rgba_array.shape[:2]
        # Single pack for entire 18-byte TGA header (avoids 8 separate struct.pack calls)
        header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x28)
        # RGBA->BGRA: swap R and B channels in-place on a contiguous copy
        bgra = np.ascontiguousarray(rgba_array[:, :, [2, 1, 0, 3]])
        with open(filepath, 'wb') as f:
            f.write(header)
            f.write(bgra.tobytes())
        _vlog("write_tga_32bit: wrote %dx%d to %s", w, h, filepath)
    except (OSError, IOError) as e:
        logger.error("write_tga_32bit IO error for '%s': %s", filepath, e)
    except Exception as e:
        logger.error("write_tga_32bit failed for '%s': %s", filepath, e)


def write_tga_24bit(filepath: str, rgb_array: np.ndarray) -> None:
    """Write a 24-bit BGR TGA file (spec map). iRacing spec maps are 24-bit.

    Args:
        filepath: Destination path.
        rgb_array: (H, W, 3) uint8 or convertible. Extra channels are trimmed.

    Returns:
        None. Errors are logged, never raised, so a failed spec write
        cannot interrupt the parent render.
    """
    try:
        rgb_array = np.asarray(rgb_array)
        if rgb_array.ndim != 3 or rgb_array.shape[2] < 3:
            logger.warning("write_tga_24bit: expected (H,W,3+) array, got shape %s (file=%s)",
                           rgb_array.shape, filepath)
            return
        if rgb_array.shape[0] == 0 or rgb_array.shape[1] == 0:
            logger.warning("write_tga_24bit: refusing to write zero-area image (file=%s)", filepath)
            return
        # Ensure uint8 output
        if rgb_array.dtype != np.uint8:
            rgb_array = np.clip(rgb_array, 0, 255).astype(np.uint8)
        # Trim extra channels (spec maps are 3-channel only)
        if rgb_array.shape[2] > 3:
            rgb_array = rgb_array[:, :, :3]
        h, w = rgb_array.shape[:2]
        # Single pack for entire 18-byte TGA header (avoids 8 separate struct.pack calls)
        header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, w, h, 24, 0x20)
        # RGB->BGR: fancy-index swap is faster than np.stack for 3 channels
        bgr = np.ascontiguousarray(rgb_array[:, :, [2, 1, 0]])
        with open(filepath, 'wb') as f:
            f.write(header)
            f.write(bgr.tobytes())
        _vlog("write_tga_24bit: wrote %dx%d spec map to %s", w, h, filepath)
    except (OSError, IOError) as e:
        logger.error("write_tga_24bit IO error for '%s': %s", filepath, e)
    except Exception as e:
        logger.error("write_tga_24bit failed for '%s': %s", filepath, e)


# ================================================================
# COORDINATE GRID CACHE
# Avoids re-allocating ~32MB per texture function call
# ================================================================

_mgrid_cache: Dict[Tuple[int, int], np.ndarray] = {}
# Bound the mgrid cache so unique resolutions in long sessions don't grow it forever
# (each entry is 2 * H * W int64 = 16 bytes/pixel; at 2048x2048 that's 64 MB per shape).
_MGRID_CACHE_MAX = 8


def paint_none(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
               seed: int, pm: float, bb: float) -> np.ndarray:
    """Identity paint function: returns the input paint unchanged.

    Used as the default placeholder when a finish has no paint-side processing
    (e.g. a pure spec-map finish). Canonical definition shared by all modules
    so identity comparisons against paint_none work everywhere.

    Args:
        paint: (H, W, 3) or (H, W, 4) float32 paint array.
        shape: (H, W) target shape (unused; kept for signature compatibility).
        mask: (H, W) zone mask in [0, 1] (unused).
        seed: Random seed (unused).
        pm: Paint multiplier (unused).
        bb: Brightness boost (unused).

    Returns:
        The same paint array, with any 4th+ channels trimmed when present.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return paint


def get_mgrid(shape: Tuple[int, int]) -> np.ndarray:
    """Return cached (y, x) coordinate grids for the given (h, w) shape.

    The (2, H, W) int64 grid is cached because allocating it on every texture
    call costs ~32 MB/call at 2048x2048. Cache is bounded by _MGRID_CACHE_MAX
    to avoid unbounded memory growth in long-running sessions.

    Args:
        shape: (height, width) tuple.

    Returns:
        np.ndarray with shape (2, H, W); index 0 is y, index 1 is x.
    """
    key = (int(shape[0]), int(shape[1]))
    cached = _mgrid_cache.get(key)
    if cached is not None:
        return cached
    h, w = key
    if h <= 0 or w <= 0:
        raise ValueError(f"get_mgrid: shape must be positive, got {shape}")
    grid = np.mgrid[0:h, 0:w]
    if len(_mgrid_cache) >= _MGRID_CACHE_MAX:
        _mgrid_cache.pop(next(iter(_mgrid_cache)))
    _mgrid_cache[key] = grid
    return grid


def clear_mgrid_cache() -> None:
    """Drop all cached coordinate grids (call when memory pressure is high)."""
    _mgrid_cache.clear()


# ================================================================
# NOISE GENERATORS
# ================================================================

# Noise cache - LRU with 64 max entries. Same seed+shape = instant hit (0ms vs 80ms+).
# Memory budget: at 2048x2048 each entry is ~16 MB; 64 entries = ~1 GB worst case
# but typical sessions use 5-15 unique noise configs so actual usage is far lower.
_noise_cache: Dict[Any, np.ndarray] = {}
_NOISE_CACHE_MAX = 64


def clear_noise_cache() -> None:
    """Clear all cached noise arrays. Call when resolution changes."""
    _noise_cache.clear()


def noise_cache_stats() -> Dict[str, int]:
    """Return cache occupancy statistics for diagnostics."""
    return {"entries": len(_noise_cache), "max": _NOISE_CACHE_MAX}


def multi_scale_noise(shape: Tuple[int, int],
                      scales: Sequence[int],
                      weights: Sequence[float],
                      seed: int = 42) -> np.ndarray:
    """Multi-scale noise: layered random fields at different frequencies.

    Each layer is generated by drawing random Gaussian noise on a small grid
    of size (h/scale, w/scale) then nearest-neighbor upsampling to (h, w).
    Layers are weighted-summed and the result is normalized to [-1, 1].
    Results are cached by (shape, seed, scales, weights) for instant reuse.

    Args:
        shape: (h, w) tuple. Negative or zero dimensions return a zero array.
        scales: Iterable of integer feature sizes in pixels (e.g. [16, 32, 64]).
        weights: Iterable of float weights, one per scale.
        seed: Deterministic seed for reproducibility.

    Returns:
        float32 array of shape (h, w) with values normalized to [-1, 1].
        On failure or invalid shape, returns a zero array of the requested size.

    Notes:
        - Same seed + shape + scales + weights -> identical output (deterministic).
        - Internally uses cv2.INTER_NEAREST for ~2x speedup vs linear; the noise
          is already coarse so interpolation quality is irrelevant.
    """
    if len(scales) != len(weights):
        logger.warning("multi_scale_noise: scales/weights length mismatch (%d vs %d)",
                       len(scales), len(weights))
    _key = (int(shape[0]), int(shape[1]), tuple(scales), tuple(weights), int(seed))
    cached = _noise_cache.get(_key)
    if cached is not None:
        return cached

    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        logger.warning("multi_scale_noise: invalid shape (%d, %d), returning zeros", h, w)
        return np.zeros((max(1, h), max(1, w)), dtype=np.float32)
    # Single-pixel zone edge case: scaled grids degenerate to 1x1; we still produce
    # a valid (1, 1) noise array.
    result = np.zeros((h, w), dtype=np.float32)
    rng = np.random.RandomState(seed)
    for scale, weight in zip(scales, weights):
        # Ensure scale produces at least a 1x1 grid for visible texture
        scale = max(1, int(scale))
        sh, sw = max(1, h // scale), max(1, w // scale)
        # For very small scales (< 4px grid), use structured noise via GaussianBlur
        # instead of pure random to produce smoother, more visible texture
        small = rng.randn(sh, sw).astype(np.float32)
        if sh < 4 or sw < 4:
            # Structured noise: blur random to create coherent features
            k = max(3, (min(sh, sw) // 2) * 2 + 1)  # odd kernel
            small = cv2.GaussianBlur(small, (k, k), 0)
        try:
            # INTER_NEAREST is ~2x faster than INTER_LINEAR for upscaling noise.
            # Since we're upscaling random data, interpolation quality is irrelevant --
            # the noise is already smoothed by the scale-based grid size.
            arr = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        except cv2.error as e:
            logger.warning("multi_scale_noise: cv2.resize failed (scale=%d, sh=%d, sw=%d, target=(%d,%d)): %s",
                           scale, sh, sw, w, h, e)
            arr = np.zeros((h, w), dtype=np.float32)
        # In-place accumulate avoids creating arr*weight as a temp array
        if weight != 0.0:
            result += arr * float(weight)
    rmin, rmax = float(result.min()), float(result.max())
    if rmax > rmin:
        # In-place normalize to [-1, 1] -- avoids two extra temp arrays
        scale_factor = 2.0 / (rmax - rmin)
        result -= rmin
        result *= scale_factor
        result -= 1.0
    # Final NaN/Inf scrub (defensive against cv2 edge cases)
    if not np.isfinite(result).all():
        np.nan_to_num(result, copy=False, nan=0.0, posinf=1.0, neginf=-1.0)

    if len(_noise_cache) >= _NOISE_CACHE_MAX:
        _noise_cache.pop(next(iter(_noise_cache)))
    _noise_cache[_key] = result
    return result


def perlin_multi_octave(shape: Tuple[int, int],
                        octaves: int = 4,
                        persistence: float = 0.5,
                        lacunarity: float = 2.0,
                        seed: int = 42) -> np.ndarray:
    """Multi-octave Perlin noise for organic, spatially coherent textures.

    Args:
        shape: (h, w) tuple. Negative dimensions yield a zero array.
        octaves: Number of octaves (1-8). More octaves = more detail, slower.
        persistence: Amplitude reduction per octave (0.01-1.0). 0.5 = each
            octave half the amplitude of the previous.
        lacunarity: Frequency multiplier per octave (1.0-4.0). 2.0 = each
            octave double the frequency.
        seed: Deterministic seed; same inputs produce identical output.

    Returns:
        float32 (h, w) array roughly in [-1, 1] (not strictly normalized;
        amplitude depends on octave count and persistence).

    Notes:
        Cached by (shape, octaves, persistence, lacunarity, seed). Falls back
        to smoothed random noise on a per-octave basis if Perlin generation
        fails for any reason.
    """
    # Validate and coerce parameters
    octaves = max(1, min(8, int(octaves)))        # Clamp octaves to 1-8
    persistence = max(0.01, min(1.0, float(persistence)))
    lacunarity = max(1.0, min(4.0, float(lacunarity)))

    cache_key = ("perlin", shape, octaves, persistence, lacunarity, seed)
    if cache_key in _noise_cache:
        return _noise_cache[cache_key]

    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        logger.warning("perlin_multi_octave: invalid shape (%d, %d), returning zeros", h, w)
        return np.zeros((max(1, h), max(1, w)), dtype=np.float32)
    result = np.zeros((h, w), dtype=np.float32)
    amplitude = 1.0
    frequency = 4
    max_value = 0.0

    for i in range(octaves):
        res_y = min(frequency, h)
        res_x = min(frequency, w)
        pad_h = int(np.ceil(h / max(1, res_y))) * max(1, res_y)
        pad_w = int(np.ceil(w / max(1, res_x))) * max(1, res_x)
        try:
            noise = _generate_perlin_2d((pad_h, pad_w), (max(1, res_y), max(1, res_x)), seed=seed + i * 31)
            noise = noise[:h, :w]
        except Exception as e:
            logger.debug("perlin_multi_octave: octave %d fell back to random noise: %s", i, e)
            np.random.seed(seed + i * 31)
            noise = np.random.randn(h, w).astype(np.float32)
            # Smooth the fallback random noise for better quality
            noise = cv2.GaussianBlur(noise, (5, 5), 1.5)
        result += noise * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency = max(1, int(frequency * lacunarity))

    if max_value > 0:
        result = result / max_value

    if len(_noise_cache) >= _NOISE_CACHE_MAX:
        _noise_cache.pop(next(iter(_noise_cache)))
    _noise_cache[cache_key] = result
    return result


def _generate_perlin_2d(shape, res, seed=None):
    """Single-octave 2D Perlin noise. Internal â€" use perlin_multi_octave instead."""
    if seed is not None:
        np.random.seed(seed)
    def f(t):
        return 6*t**5 - 15*t**4 + 10*t**3
    delta = (res[0]/shape[0], res[1]/shape[1])
    d = (shape[0]//res[0], shape[1]//res[1])
    grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1,2,0) % 1
    angles = 2*np.pi*np.random.rand(res[0]+1, res[1]+1)
    gradients = np.dstack((np.cos(angles), np.sin(angles)))
    # Use advanced indexing instead of .repeat() -- zero-copy broadcast, no temp arrays.
    yi = np.clip(np.arange(shape[0]) // d[0], 0, gradients.shape[0] - 2)
    xi = np.clip(np.arange(shape[1]) // d[1], 0, gradients.shape[1] - 2)
    g00 = gradients[yi[:, None], xi[None, :]]
    g10 = gradients[yi[:, None] + 1, xi[None, :]]
    g01 = gradients[yi[:, None], xi[None, :] + 1]
    g11 = gradients[yi[:, None] + 1, xi[None, :] + 1]
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
# SIMPLEX-STYLE NOISE (permutation-table based, smoother than zoom)
# ================================================================

# Pre-computed permutation table (Ken Perlin's classic shuffled 0-255, doubled)
_SIMPLEX_PERM = np.array([
    151,160,137,91,90,15,131,13,201,95,96,53,194,233,7,225,
    140,36,103,30,69,142,8,99,37,240,21,10,23,190,6,148,
    247,120,234,75,0,26,197,62,94,252,219,203,117,35,11,32,
    57,177,33,88,237,149,56,87,174,20,125,136,171,168,68,175,
    74,165,71,134,139,48,27,166,77,146,158,231,83,111,229,122,
    60,211,133,230,220,105,92,41,55,46,245,40,244,102,143,54,
    65,25,63,161,1,216,80,73,209,76,132,187,208,89,18,169,
    200,196,135,130,116,188,159,86,164,100,109,198,173,186,3,64,
    52,217,226,250,124,123,5,202,38,147,118,126,255,82,85,212,
    207,206,59,227,47,16,58,17,182,189,28,42,223,183,170,213,
    119,248,152,2,44,154,163,70,221,153,101,155,167,43,172,9,
    129,22,39,253,19,98,108,110,79,113,224,232,178,185,112,104,
    218,246,97,228,251,34,242,193,238,210,144,12,191,179,162,241,
    81,51,145,235,249,14,239,107,49,192,214,31,181,199,106,157,
    184,84,204,176,115,121,50,45,127,4,150,254,138,236,205,93,
    222,114,67,29,24,72,243,141,128,195,78,66,215,61,156,180,
], dtype=np.int32)
_SIMPLEX_PERM = np.concatenate([_SIMPLEX_PERM, _SIMPLEX_PERM])  # double for overflow-free indexing

# Gradient vectors for 2D simplex (12 directions)
_SIMPLEX_GRAD2 = np.array([
    [1,1],[-1,1],[1,-1],[-1,-1],
    [1,0],[-1,0],[0,1],[0,-1],
    [1,1],[-1,1],[1,-1],[-1,-1],
], dtype=np.float32)


def simplex_noise_2d(shape, scale=64.0, seed=42):
    """Generate smooth 2D noise using a permutation-table gradient approach.
    Cached by (shape, scale, seed)."""
    cache_key = ("simplex", shape, scale, seed)
    if cache_key in _noise_cache:
        return _noise_cache[cache_key]

    h, w = shape
    # Build seeded permutation table
    rng = np.random.RandomState(seed)
    perm = _SIMPLEX_PERM.copy()
    # Shuffle the first 256 entries with seed, then mirror
    base_perm = perm[:256].copy()
    rng.shuffle(base_perm)
    perm[:256] = base_perm
    perm[256:] = base_perm

    # Skew factors for 2D simplex
    F2 = 0.5 * (np.sqrt(3.0) - 1.0)
    G2 = (3.0 - np.sqrt(3.0)) / 6.0

    # Create coordinate grids
    yy, xx = np.mgrid[0:h, 0:w]
    xin = xx.astype(np.float64) / max(1.0, scale)
    yin = yy.astype(np.float64) / max(1.0, scale)

    # Skew input space to determine simplex cell
    s = (xin + yin) * F2
    i = np.floor(xin + s).astype(np.int32)
    j = np.floor(yin + s).astype(np.int32)
    t = (i + j).astype(np.float64) * G2

    # Unskew cell origin back to (x,y) space
    X0 = i - t
    Y0 = j - t
    x0 = xin - X0
    y0 = yin - Y0

    # Determine which simplex we're in (upper or lower triangle)
    i1 = np.where(x0 > y0, 1, 0)
    j1 = np.where(x0 > y0, 0, 1)

    x1 = x0 - i1 + G2
    y1 = y0 - j1 + G2
    x2 = x0 - 1.0 + 2.0 * G2
    y2 = y0 - 1.0 + 2.0 * G2

    # Hash coordinates to gradient indices
    ii = i & 255
    jj = j & 255

    gi0 = perm[ii + perm[jj] % 256] % 12
    gi1 = perm[(ii + i1) & 255 + perm[((jj + j1) & 255)] % 256] % 12
    gi2 = perm[(ii + 1) & 255 + perm[((jj + 1) & 255)] % 256] % 12

    # Contribution from each corner
    def _contrib(gidx, dx, dy):
        t_val = 0.5 - dx * dx - dy * dy
        mask = t_val > 0
        t_val = np.where(mask, t_val, 0.0)
        t_val *= t_val  # t^2
        t_val *= t_val  # t^4
        # Dot product with gradient
        grad = _SIMPLEX_GRAD2[gidx % 12]
        dot = grad[..., 0] * dx + grad[..., 1] * dy
        return np.where(mask, t_val * dot, 0.0)

    n0 = _contrib(gi0, x0, y0)
    n1 = _contrib(gi1, x1, y1)
    n2 = _contrib(gi2, x2, y2)

    # Scale to [-1, 1]
    result = (70.0 * (n0 + n1 + n2)).astype(np.float32)
    rmin, rmax = float(result.min()), float(result.max())
    if rmax > rmin:
        result = (result - rmin) / (rmax - rmin) * 2.0 - 1.0

    if len(_noise_cache) >= _NOISE_CACHE_MAX:
        _noise_cache.pop(next(iter(_noise_cache)))
    _noise_cache[cache_key] = result
    return result


def multi_scale_simplex(shape, scales, weights, seed=42):
    """Multi-scale noise using simplex_noise_2d instead of random+zoom.

    Drop-in alternative to multi_scale_noise for smoother organic results,
    especially at low scales (< 16). Existing code is not affected.

    Args:
        shape: (height, width) tuple
        scales: list of scale values (feature sizes in pixels)
        weights: list of weights for each scale layer
        seed: Random seed for reproducibility

    Returns:
        float32 array (h, w) normalized to [-1, 1]
    """
    h, w = shape
    result = np.zeros((h, w), dtype=np.float32)
    for idx, (scale, weight) in enumerate(zip(scales, weights)):
        layer = simplex_noise_2d(shape, scale=float(max(1, scale)), seed=seed + idx * 37)
        result += layer * weight
    rmin, rmax = float(result.min()), float(result.max())
    if rmax > rmin:
        result = (result - rmin) / (rmax - rmin) * 2.0 - 1.0
    return result


# ================================================================
# COLOR CONVERSION
# ================================================================

def hsv_to_rgb_vec(h_arr: Union[np.ndarray, float],
                   s_arr: Union[np.ndarray, float],
                   v_arr: Union[np.ndarray, float]
                   ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized HSV -> RGB conversion using cv2.cvtColor (zero Python loops).

    Operates in sRGB space directly (no gamma round-trip): the H/S/V values are
    treated as sRGB-space coordinates as iRacing's editor would interpret them.

    Args:
        h_arr: Hue in [0, 1] (will be scaled to degrees internally).
        s_arr: Saturation in [0, 1].
        v_arr: Value in [0, 1].

    Returns:
        Tuple of (r, g, b) float32 arrays each in [0, 1] with the broadcast shape
        of the inputs.
    """
    h = np.asarray(h_arr, dtype=np.float32)
    s = np.asarray(s_arr, dtype=np.float32)
    v = np.asarray(v_arr, dtype=np.float32)
    orig_shape = h.shape
    # cv2.cvtColor requires a 3-channel image; flatten to (N,1,3) then restore.
    hsv = np.stack([h.ravel() * 360.0, s.ravel(), v.ravel()], axis=-1).reshape(-1, 1, 3)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)  # float32 H in [0,360], S/V in [0,1]
    rgb = rgb.reshape(orig_shape + (3,))
    return rgb[..., 0], rgb[..., 1], rgb[..., 2]


def rgb_to_hsv_array(scheme: np.ndarray) -> np.ndarray:
    """Convert RGB float [0, 1] array to HSV float [0, 1] array using cv2.

    Args:
        scheme: (H, W, 3) float32 RGB array in sRGB space.

    Returns:
        (H, W, 3) float32 HSV array. cv2 returns H in [0, 360] internally;
        this wrapper renormalizes H to [0, 1] for consistency with hsv_to_rgb_vec.
    """
    rgb = np.asarray(scheme, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError(f"rgb_to_hsv_array: expected (H, W, 3+) array, got shape {rgb.shape}")
    if rgb.shape[2] > 3:
        rgb = rgb[..., :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)   # H in [0,360], S/V in [0,1]
    hsv[..., 0] /= 360.0                          # normalise H to [0,1]
    return hsv


def rgb_to_lab_array(scheme: np.ndarray) -> np.ndarray:
    """Convert RGB float [0, 1] to CIE Lab via cv2.

    Args:
        scheme: (H, W, 3) float32 sRGB array in [0, 1].

    Returns:
        (H, W, 3) float32 Lab array. L in [0, 100], a/b roughly [-127, 127].
        Used by perceptual color-distance calculations in build_zone_mask
        when callers need true perceptual matching (slower than weighted RGB).
    """
    rgb = np.asarray(scheme, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError(f"rgb_to_lab_array: expected (H, W, 3+) array, got shape {rgb.shape}")
    return cv2.cvtColor(rgb[..., :3], cv2.COLOR_RGB2Lab)


# Common CSS named colors for parse_hex_color() / parse_color_description().
# Each value is an (r, g, b) tuple in [0, 255]. Subset of the most-requested names
# from livery design briefs; extend here when new aliases are needed.
NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "black":   (0, 0, 0),
    "white":   (255, 255, 255),
    "red":     (255, 0, 0),
    "green":   (0, 128, 0),
    "blue":    (0, 0, 255),
    "yellow":  (255, 255, 0),
    "cyan":    (0, 255, 255),
    "magenta": (255, 0, 255),
    "orange":  (255, 165, 0),
    "purple":  (128, 0, 128),
    "pink":    (255, 192, 203),
    "brown":   (139, 69, 19),
    "gray":    (128, 128, 128),
    "grey":    (128, 128, 128),
    "silver":  (192, 192, 192),
    "gold":    (255, 215, 0),
    "navy":    (0, 0, 128),
    "teal":    (0, 128, 128),
    "maroon":  (128, 0, 0),
    "olive":   (128, 128, 0),
    "lime":    (0, 255, 0),
}


def parse_hex_color(text: str) -> Optional[Tuple[int, int, int, int]]:
    """Parse a #RGB / #RRGGBB / #RRGGBBAA / named color string to (R, G, B, A).

    Args:
        text: Color string. Whitespace is stripped. The leading '#' is optional.
            Supported forms:
              - #RGB        -> 4-bit per channel, nibble-replicated (#F0A == #FF00AA)
              - #RRGGBB     -> standard 8-bit per channel
              - #RRGGBBAA   -> 8-bit per channel + alpha
              - <name>      -> looked up in NAMED_COLORS

    Returns:
        Tuple (R, G, B, A) of ints in [0, 255], or None if the string cannot
        be parsed. Alpha defaults to 255 when not provided.
    """
    if not text:
        return None
    s = str(text).strip().lower().lstrip('#')
    # Named lookup first (no leading hex digits required)
    if s in NAMED_COLORS:
        r, g, b = NAMED_COLORS[s]
        return (r, g, b, 255)
    if not all(c in "0123456789abcdef" for c in s):
        return None
    try:
        if len(s) == 3:
            r = int(s[0] * 2, 16)
            g = int(s[1] * 2, 16)
            b = int(s[2] * 2, 16)
            return (r, g, b, 255)
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
        if len(s) == 8:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
    except ValueError:
        return None
    return None


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
# Baked in so users never have to think about it â€" 100% = full effect.
_INTENSITY_SCALE = {
    "paint":  1.50,  # paint functions need up to 1.5x for full effect
    "spec":   2.00,  # spec modulation needs 2.0x for visible texture
    "bright": 0.15,  # brightness boost caps at 0.15 (7-15% brightness add)
}


# ================================================================
# COLOR ANALYSIS â€" how zones find their pixels
# ================================================================

def analyze_paint_colors(scheme: np.ndarray) -> Dict[str, np.ndarray]:
    """Analyze paint image and return HSV/luma stats for zone matching.

    Args:
        scheme: (H, W, 3+) float32 or convertible RGB array in [0, 1].

    Returns:
        Dict with keys:
            - "hue", "sat", "val": HSV channels in [0, 1]
            - "brightness": ITU-R BT.601 luma (0.299 R + 0.587 G + 0.114 B)
            - "rgb": the (clipped) input scheme

    Notes:
        Brightness uses BT.601 weights because they match how iRacing's pixel
        shader computes luminance for tonemap. Switching to BT.709 would shift
        all "bright"/"dark" thresholds and require recalibrating zone presets.
    """
    try:
        scheme = np.asarray(scheme, dtype=np.float32)
        if scheme.ndim != 3 or scheme.shape[2] < 3:
            logger.warning("analyze_paint_colors: unexpected scheme shape %s", scheme.shape)
            h, w = scheme.shape[:2] if scheme.ndim >= 2 else (1, 1)
            return {"hue": np.zeros((h, w), dtype=np.float32),
                    "sat": np.zeros((h, w), dtype=np.float32),
                    "val": np.zeros((h, w), dtype=np.float32),
                    "brightness": np.zeros((h, w), dtype=np.float32),
                    "rgb": scheme}
        # Ensure values are in 0-1 range
        scheme = np.clip(scheme, 0.0, 1.0)
        hsv = rgb_to_hsv_array(scheme)
        # ITU-R BT.601 luma -- single fused multiply-add chain
        brightness = (scheme[:, :, 0] * 0.299 +
                      scheme[:, :, 1] * 0.587 +
                      scheme[:, :, 2] * 0.114)
        stats = {
            "hue": hsv[:, :, 0],
            "sat": hsv[:, :, 1],
            "val": hsv[:, :, 2],
            "brightness": brightness,
            "rgb": scheme,
        }
        h, w = scheme.shape[:2]
        total_pixels = max(1, h * w)  # Avoid division by zero
        # Single pass through brightness for two thresholds
        bright_pct = float(np.count_nonzero(brightness > 0.85)) / total_pixels * 100.0
        dark_pct = float(np.count_nonzero(brightness < 0.15)) / total_pixels * 100.0
        saturated_pct = float(np.count_nonzero(hsv[:, :, 1] > 0.3)) / total_pixels * 100.0
        # Quiet by default in production -- use _vlog so verbose mode controls noise
        _vlog("Paint Analysis: bright=%.1f%% dark=%.1f%% saturated=%.1f%%",
              bright_pct, dark_pct, saturated_pct)
        if _VERBOSE:
            print("    Paint Analysis:")
            print(f"      Bright (>85%): {bright_pct:.1f}%  Dark (<15%): {dark_pct:.1f}%  Saturated: {saturated_pct:.1f}%")
        return stats
    except Exception as e:
        logger.error("analyze_paint_colors failed: %s", e)
        h, w = scheme.shape[:2] if hasattr(scheme, 'shape') and scheme.ndim >= 2 else (1, 1)
        return {"hue": np.zeros((h, w), dtype=np.float32),
                "sat": np.zeros((h, w), dtype=np.float32),
                "val": np.zeros((h, w), dtype=np.float32),
                "brightness": np.zeros((h, w), dtype=np.float32),
                "rgb": scheme}


def feather_mask(mask: np.ndarray, radius: float = 3.0,
                 use_gaussian: bool = True) -> np.ndarray:
    """Soften a binary or grayscale mask via Gaussian (preferred) or box blur.

    Args:
        mask: (H, W) float32 mask in [0, 1].
        radius: Feather radius in pixels (sigma for Gaussian, half-width for box).
        use_gaussian: True for Gaussian (smoother edges, slightly slower);
            False for separable box blur (faster but produces visible bands at
            high radii).

    Returns:
        (H, W) float32 feathered mask, clamped to [0, 1].

    Notes:
        Gaussian is the right choice for nearly all use cases. Box blur is only
        retained for old-style chunky pattern edges that artists explicitly want.
    """
    if mask is None or mask.size == 0 or radius <= 0:
        return mask
    arr = mask.astype(np.float32, copy=False)
    if use_gaussian:
        ksize = int(radius * 6 + 1) | 1  # ensure odd
        try:
            return cv2.GaussianBlur(arr, (ksize, ksize), float(radius))
        except cv2.error as e:
            logger.warning("feather_mask: GaussianBlur failed (radius=%.2f): %s", radius, e)
    # Box blur fallback
    ksize = max(1, int(radius * 2 + 1))
    return cv2.blur(arr, (ksize, ksize))


def build_zone_mask(scheme: np.ndarray,
                    stats: Dict[str, np.ndarray],
                    selector: Dict[str, Any],
                    blur_radius: float = 3.0) -> np.ndarray:
    """Build a float32 zone mask in [0, 1] from a color selector dict.

    Args:
        scheme: (H, W, 3) float32 paint array in [0, 1].
        stats: Dict produced by analyze_paint_colors() (provides hue/sat/val).
        selector: One of the supported selector dicts (see below).
        blur_radius: Gaussian sigma for soft edges in pixels (0 = no blur).

    Returns:
        Float32 (H, W) array; 1.0 = fully in zone, 0.0 = not in zone.

    Selector types - choose the one that matches your zone:
        {"color_rgb": [R, G, B], "tolerance": 30}                   -> color match with soft falloff
        {"color_range": {"r": [lo,hi], "g": [lo,hi], "b": [lo,hi]}} -> RGB range box
        {"hue_range": [lo_deg, hi_deg], "sat_min": 0.2, "val_min": 0.1} -> HSV hue band
        {"brightness": {"min": 0.0, "max": 0.3}}                    -> lightness range
        {"saturation": {"min": 0.5, "max": 1.0}}                    -> saturation range
        {"all_painted": True}                                       -> everything with color or darkness
        {"remainder": True}                                         -> everything not claimed by other zones

    Notes:
        - color_rgb path is GPU-accelerated when CuPy is available (biggest win
          on 2048x2048 textures: ~5x speedup).
        - The CPU path uses BT.601-weighted Euclidean distance for perceptual
          similarity (R=0.30, G=0.59, B=0.11 squared weights).
    """
    if scheme is None or scheme.ndim < 2:
        raise ValueError("build_zone_mask: scheme must be a 2D+ image array")
    if not isinstance(selector, dict):
        raise TypeError(f"build_zone_mask: selector must be dict, got {type(selector).__name__}")
    h, w = scheme.shape[:2]
    _gpu = is_gpu()

    if "color_rgb" in selector:
        target = np.array(selector["color_rgb"], dtype=np.float32) / 255.0
        tolerance = selector.get("tolerance", 30) / 255.0
        # Effective radius: tolerance directly in Euclidean RGB space (no sqrt(3) reduction).
        # tolerance=35 means "catch colors within 35/255 Euclidean distance" — what the user expects.
        # Soft edge: linear falloff from 1.0 at center to 0.0 at radius boundary.
        tol_radius = max(tolerance, 0.001)
        # 2026-04-21 HEENAN OVERNIGHT iter 5: unified GPU and CPU branches
        # on the BT.601-weighted perceptual metric. Pre-fix, GPU used
        # unweighted Euclidean (a perf shortcut dropped the weights the
        # CPU branch documents). Measured painter-visible impact of the
        # divergence: at default tolerance=30, CPU caught 1.2x-1.4x more
        # pixels than GPU on a realistic gold/red/dark palette (2.6%-5.8%
        # extra canvas coverage); at tolerance=20 the delta grew to up
        # to 20%. Cross-platform preset sharing rendered differently for
        # no good reason. Adopting the weighted form on GPU matches the
        # CPU branch's documented "perceptually-weighted" intent.
        # Painter-visible effect for GPU-only painters: at the same
        # tolerance, they will now catch the same pixels a CPU painter
        # would — generally slightly more coverage. A painter who was
        # tuning tolerance for the pre-fix GPU behavior may want to
        # reduce their saved tolerance by ~20% for equivalent output.
        if _gpu:
            _scheme_g = to_gpu(scheme)
            _t0, _t1, _t2 = float(target[0]), float(target[1]), float(target[2])
            _dr = _scheme_g[:,:,0] - _t0
            _dg = _scheme_g[:,:,1] - _t1
            _db = _scheme_g[:,:,2] - _t2
            dist = xp.sqrt(_dr*_dr * 0.30 + _dg*_dg * 0.59 + _db*_db * 0.11)
            mask = xp.clip(1.0 - dist / tol_radius, 0, 1)
            mask = to_cpu(mask)
        else:
            # Perceptually-weighted distance: red-green difference matters more than brightness
            # Weights approximate human visual sensitivity (ITU-R BT.601 luma)
            dr = (scheme[:,:,0] - target[0])
            dg = (scheme[:,:,1] - target[1])
            db = (scheme[:,:,2] - target[2])
            # Weighted distance: green channel most sensitive, red next, blue least
            dist = np.sqrt(dr*dr * 0.30 + dg*dg * 0.59 + db*db * 0.11)
            mask = np.clip(1.0 - dist / tol_radius, 0, 1)

    elif "color_range" in selector:
        cr = selector["color_range"]
        r_lo, r_hi = cr.get("r", [0, 255])
        g_lo, g_hi = cr.get("g", [0, 255])
        b_lo, b_hi = cr.get("b", [0, 255])
        if _gpu:
            _scheme_g = to_gpu(scheme)
            rgb255 = (_scheme_g * 255).astype(xp.float32)
            mask = (
                (rgb255[:,:,0] >= r_lo) & (rgb255[:,:,0] <= r_hi) &
                (rgb255[:,:,1] >= g_lo) & (rgb255[:,:,1] <= g_hi) &
                (rgb255[:,:,2] >= b_lo) & (rgb255[:,:,2] <= b_hi)
            ).astype(xp.float32)
            mask = to_cpu(mask)
        else:
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
        if hue_lo > hue_hi:  # wraps through 0 degrees (reds)
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

    else:
        mask = np.zeros((h, w), dtype=np.float32)

    # Soft edges via Gaussian blur (cv2). Use feather_mask helper for consistency.
    if blur_radius > 0 and np.any(mask > 0):
        mask = feather_mask(mask, radius=float(blur_radius), use_gaussian=True)

    # Final NaN/Inf guard -- pattern selectors with bad inputs could produce
    # non-finite values that propagate downstream and cause silent black zones.
    if not np.isfinite(mask).all():
        np.nan_to_num(mask, copy=False, nan=0.0, posinf=1.0, neginf=0.0)

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


def parse_color_description(desc: str) -> Dict[str, Any]:
    """Parse a natural language color word or hex string into a zone selector dict.

    Args:
        desc: Free-form description, e.g. "dark blue", "#FF0000", "rgb(255,0,0)",
            "everything". None / empty returns {"all_painted": True}.

    Returns:
        Selector dict suitable for build_zone_mask().

    Examples:
        "blue"            -> hue_range [200, 260]
        "dark blue"       -> hue_range [200, 260] + val_max 0.4
        "#FF0000"         -> color_rgb [255, 0, 0]
        "#F00"            -> color_rgb [255, 0, 0]
        "rgb(255,0,0)"    -> color_rgb [255, 0, 0]
        "everything"      -> all_painted: True
    """
    if not desc:
        return {"all_painted": True}
    desc = str(desc).lower().strip()

    # Hex (3 / 6 / 8 nibble forms) handled by parse_hex_color
    if desc.startswith("#"):
        parsed = parse_hex_color(desc)
        if parsed is not None:
            r, g, b, _a = parsed
            return {"color_rgb": [r, g, b], "tolerance": 40}

    if desc.startswith("rgb("):
        try:
            parts = desc.replace("rgb(", "").replace(")", "").split(",")
            if len(parts) == 3:
                return {"color_rgb": [max(0, min(255, int(p.strip()))) for p in parts],
                        "tolerance": 40}
        except ValueError:
            logger.warning("parse_color_description: bad rgb() syntax in '%s'", desc)

    words = desc.replace("/", " ").replace("-", " ").split()
    _skip = {"the", "a", "an", "areas", "area", "parts", "part", "panels", "panel",
             "accents", "accent", "stripe", "stripes", "trim", "decals", "decal",
             "logos", "logo", "numbers", "number", "hood", "roof", "bumper", "skirt",
             "fender", "door", "doors", "side", "front", "rear", "back", "top",
             "bottom", "base", "main", "sponsors", "sponsor"}

    selector: Optional[Dict[str, Any]] = None
    for word in words:
        if word in _skip:
            continue
        if word in COLOR_WORD_MAP:
            selector = dict(COLOR_WORD_MAP[word])
            break

    if selector is None:
        # Quiet by default -- noisy print was causing log spam in production renders
        _vlog("parse_color_description: could not parse '%s', defaulting to all_painted", desc)
        return {"all_painted": True}

    # Apply modifiers (dark/bright/light)
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
# ZONE COLOR SAMPLING â€" for adaptive color shift / pipeline
# ================================================================

def _sample_zone_color(paint: np.ndarray,
                       mask: np.ndarray
                       ) -> Tuple[float, float, float]:
    """Sample the dominant color (median R/G/B) inside a masked zone.

    Args:
        paint: (H, W, 3+) float32 paint array in [0, 1].
        mask:  (H, W) float32 zone mask; pixels with mask > 0.5 are sampled.

    Returns:
        (hue, sat, val) tuple of floats in [0, 1]. When the zone has fewer
        than 100 strong pixels (single-pixel / sliver zones) returns a neutral
        gray default to avoid noisy color picks.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    strong = mask > 0.5
    if int(np.count_nonzero(strong)) < 100:
        # Single-pixel / extremely thin zone -- return neutral mid-gray default
        return 0.0, 0.0, 0.6
    # Single masked array slice + axis-wise median is faster than 3 separate slices
    masked_pixels = paint[strong]  # shape (N, 3)
    r_med = float(np.median(masked_pixels[:, 0]))
    g_med = float(np.median(masked_pixels[:, 1]))
    b_med = float(np.median(masked_pixels[:, 2]))
    maxc = max(r_med, g_med, b_med)
    minc = min(r_med, g_med, b_med)
    delta = maxc - minc
    val = maxc
    sat = delta / maxc if maxc > EPSILON else 0.0
    if delta < 1e-3:
        hue = 0.0
    elif maxc == r_med:
        hue = (((g_med - b_med) / delta) % 6) / 6.0
    elif maxc == g_med:
        hue = (((b_med - r_med) / delta) + 2) / 6.0
    else:
        hue = (((r_med - g_med) / delta) + 4) / 6.0
    return float(hue), float(sat), float(val)


# ================================================================
# ARRAY HELPERS â€" resize, tile, crop, rotate (used by compose)
# ================================================================

def _resize_array(arr: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Resize a 2D float32 array to target dimensions using cv2 bilinear.

    Args:
        arr: 2D source array.
        target_h: Target height in pixels.
        target_w: Target width in pixels.

    Returns:
        Resized float32 array. Returns the input unchanged when already at
        target size (zero-copy fast path).
    """
    if arr.shape[0] == target_h and arr.shape[1] == target_w:
        return arr
    if target_h <= 0 or target_w <= 0:
        raise ValueError(f"_resize_array: target dims must be positive, got ({target_h}, {target_w})")
    return cv2.resize(arr.astype(np.float32, copy=False),
                      (target_w, target_h), interpolation=cv2.INTER_LINEAR)


def _tile_fractional(arr: np.ndarray, factor: float, target_h: int, target_w: int) -> np.ndarray:
    """Tile a 2D array by a fractional factor and resize to target dims.

    Args:
        arr: Source 2D array.
        factor: Fractional tile multiplier; >=1 tiles up before cropping.
        target_h: Final height.
        target_w: Final width.

    Returns:
        Float32 array of shape (target_h, target_w).
    """
    h, w = arr.shape[:2]
    reps = min(10, max(2, int(math.ceil(factor))))
    tiled = np.tile(arr, (reps, reps))
    crop_h = min(tiled.shape[0], max(4, int(round(h * factor))))
    crop_w = min(tiled.shape[1], max(4, int(round(w * factor))))
    tiled = tiled[:crop_h, :crop_w]
    return _resize_array(tiled, target_h, target_w)


def _crop_center_array(arr: np.ndarray, crop_frac: float, target_h: int, target_w: int) -> np.ndarray:
    """Crop the centre portion of a 2D array then resize to target dims.

    Args:
        arr: Source 2D array.
        crop_frac: Crop denominator; e.g. 2.0 keeps the centre half.
        target_h: Final height.
        target_w: Final width.

    Returns:
        Float32 array of shape (target_h, target_w).
    """
    h, w = arr.shape[:2]
    if crop_frac <= 0:
        raise ValueError(f"_crop_center_array: crop_frac must be > 0, got {crop_frac}")
    ch = max(4, int(h / crop_frac))
    cw = max(4, int(w / crop_frac))
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    cropped = arr[y0:y0 + ch, x0:x0 + cw]
    if cropped.shape[0] == target_h and cropped.shape[1] == target_w:
        return cropped
    return _resize_array(cropped, target_h, target_w)


def _rotate_array(arr: np.ndarray, angle: float, fill_value: float = 0.0) -> np.ndarray:
    """Rotate a 2D numpy array by `angle` degrees around the centre.

    Uses cv2.warpAffine directly (no PIL conversion); ~3-5x faster than the
    legacy PIL path on typical 2048x2048 arrays.

    Args:
        arr: 2D source array.
        angle: Rotation in degrees (positive = counter-clockwise).
        fill_value: Value to fill background pixels exposed by rotation.

    Returns:
        Rotated float32 array of the same shape. Returns the input unchanged
        when angle is 0 / 360 or the input is empty.
    """
    if angle == 0 or angle == 360:
        return arr
    h, w = arr.shape[:2]
    if h == 0 or w == 0:
        return arr
    # cv2.warpAffine works on float32 directly -- no uint8 conversion needed
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(arr.astype(np.float32, copy=False), M, (w, h),
                              flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=float(fill_value))
    return rotated


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


def _compute_zone_auto_scale(zone_mask: np.ndarray,
                             shape: Tuple[int, int]) -> float:
    """Compute an auto-scale factor for patterns based on zone mask coverage area.

    Zones that cover most of the canvas use scale=1.0; small zones get scaled-up
    pattern (smaller features) so the pattern reads at the zone's apparent size.

    Args:
        zone_mask: (H, W) float32 mask in [0, 1].
        shape: (H, W) target shape.

    Returns:
        Auto-scale factor in [0.15, 1.0].
    """
    h, w = shape
    total_area = h * w
    if total_area == 0 or zone_mask is None or zone_mask.size == 0:
        return 1.0
    # Edge case: zero-coverage mask -> default to 1.0 rather than divide-by-zero
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
    return float(max(0.15, min(1.0, area_ratio ** 0.5)))
