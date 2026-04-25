"""
Shokker Engine v2 — COLOR-BASED Zone Detection & Finish Application
======================================================================
The central engine module for the Shokker Paint Booth (SPB).

WHAT THIS ENGINE DOES
---------------------
Given a paint .tga/.png and a list of "zones" (color-described regions of the
car), this engine generates iRacing-ready outputs:

  * car_num_<id>.tga    : the modified paint (24-bit RGB)
  * car_spec_<id>.tga   : the spec/material map (32-bit RGBA)
  * helmet_spec_<id>.tga, suit_spec_<id>.tga (optional, via matching set)

It composes per-zone "base + pattern + monolithic" finishes by analyzing the
source paint's color distribution, building per-zone masks via HSV thresholds
or pre-drawn region masks, and overlaying spec/paint modifications produced by
hundreds of pluggable finish functions.

SPEC-MAP CHANNEL SEMANTICS (iRacing PBR)
----------------------------------------
The spec map is RGBA uint8 with strictly defined channel meanings:

  * R = Metallic        (0   = dielectric,        255 = mirror metal)
  * G = Roughness       (0   = mirror smooth,     255 = matte)
  * B = Clearcoat       (0-15 = no clearcoat,      16  = max gloss CC,
                         16-255 = progressively duller — counter-intuitive!)
  * A = Spec mask       (255 = active pixel,        0 = transparent)

IRON RULES (do not violate; enforce centrally via _enforce_iron_rules)
----------------------------------------------------------------------
  1. CC must be >= 16 anywhere paint exists, OR == 0 (no clearcoat at all).
     Values 1-15 produce GGX whitewash/blowout in iRacing's shader.
  2. Where M < 240 (non-mirror), Roughness floor is 15. Mirror chrome (M>=240)
     may go to R=0 for true mirror reflectivity.
  3. The alpha (spec mask) channel is generally driven by the union of zone
     masks; consumer tools currently do not paint per-pixel A directly.

COLOR SPACE
-----------
All paint arrays inside the engine are sRGB-ish floats normalized to 0..1
(numpy float32) unless explicitly noted. Output TGAs are written as 8-bit
sRGB without any gamma conversion — iRacing expects sRGB textures and we
preserve that pipeline. Spec maps are linear 8-bit (R/G/B/A interpreted
directly as PBR channel values, not as colors).

TABLE OF CONTENTS — Use these line numbers as a navigation aid:
================================================================
  L55    Imports & re-exports (engine.utils, engine.core, engine.spec_paint, ...)
  L95    Spec Map Generators (spec_gloss, spec_chrome, spec_aurora, ...)
  L300   Paint Modifiers (paint_none, paint_carbon_darken, paint_lava_glow, ...)
  L420   FINISH_REGISTRY (legacy mode - maps finish names to spec+paint functions)
  L465   Texture Functions (texture_carbon_fiber, texture_hex_mesh, ...)
  L1027  Base Material Helpers & v5.5 SHOKK additions
  L1887  SHOKK Series - Upgraded + New Boundary-Pushing Patterns
  L3140  BASE_REGISTRY dict
  L3305  PATTERN_REGISTRY dict (~230 entries)
  L3538  Chameleon/Prizm stubs + module loading
  L3596  MONOLITHIC_REGISTRY dict
  L3664  Chameleon/Prizm module overrides (V5 extracted module loading)
  L3723  Expansion imports (24K, Color Mono, Paradigm, Fusions)
  L3767  render_generic_finish import
  L3776  Dual Layer Base system delegates (overlay_pattern_on_spec, etc.)
  L3949  build_multi_zone - THE CORE multi-zone rendering pipeline
  L4824  preview_render - quick preview rendering
  L5308  apply_single_finish, apply_composed_finish
  L5402  build_helmet_spec, build_suit_spec, build_matching_set
  L6068  apply_wear - post-processing wear/age effects
  L6161  build_export_package
  L6246  generate_gradient_mask, generate_night_variant
  L6334  full_render_pipeline
  L6460  if __name__ == '__main__' (example smoke test)
================================================================

ENVIRONMENTAL TOGGLES
---------------------
  * SPB_VERBOSE_ENGINE=1   : enable per-zone DEBUG-level logging.
  * SPB_QUIET_ENGINE=1     : suppress all non-error engine prints.

STABLE PUBLIC INTERFACE
-----------------------
The following functions are the *stable* public surface — their signatures
must not change without a major version bump and a deliberate migration:
build_multi_zone, preview_render, apply_single_finish, apply_composed_finish,
build_helmet_spec, build_suit_spec, build_matching_set, apply_wear,
build_export_package, generate_gradient_mask, generate_night_variant,
full_render_pipeline. The four registries (BASE_REGISTRY, PATTERN_REGISTRY,
FINISH_REGISTRY, MONOLITHIC_REGISTRY) are also part of the stable surface.
"""

def _paint_noop(paint, shape, mask, seed, pm, bb):
    """No-op paint modifier: ensures input is RGB and returns it unchanged.

    INTERNAL helper used as a default ``paint_fn`` for finishes that only
    affect the spec map. Kept at module top so it is defined before the
    BASE_REGISTRY/FINISH_REGISTRY blocks reference it.

    Args:
        paint: HxWx{3,4} float array of paint pixels (0..1 sRGB-ish).
        shape: (h, w) tuple. Currently unused (preserved for signature parity).
        mask:  HxW float mask 0..1 indicating zone coverage. Unused here.
        seed:  RNG seed. Unused here.
        pm:    Paint multiplier (intensity). Unused here.
        bb:    Brightness boost. Unused here.

    Returns:
        HxWx3 paint array (RGBA stripped to RGB).
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return paint

import numpy as np
import cv2
from PIL import Image, ImageFilter
import struct
import os
import json
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from scipy.ndimage import gaussian_filter as _scipy_gaussian_filter

# Backwards-compat alias kept for legacy code paths inside this module that
# imported ``os`` under a private name. Prefer plain ``os`` in new code.
_os = os

# ================================================================
# MODULE-LEVEL CONSTANTS — extracted magic numbers
# ================================================================

#: Engine semantic version. Bump on user-visible behaviour changes.
ENGINE_VERSION = "6.2.0"

#: Display name shown in console banners.
ENGINE_DISPLAY_NAME = "SHOKKER ENGINE v6.2 PRO"

#: Iron-rule clearcoat floor — anything above 0 must be at least this value
#: to avoid GGX-shader whitewash in iRacing's PBR pipeline.
CC_FLOOR = 16

#: Iron-rule roughness floor for non-mirror pixels (M < CHROME_M_THRESHOLD).
ROUGHNESS_FLOOR_NONMIRROR = 15

#: Metallic threshold above which a pixel is treated as "mirror" — mirror
#: pixels are exempt from the roughness floor so true chromes can read 0.
CHROME_M_THRESHOLD = 240

#: Default progress fractions for full_render_pipeline stages.
PROGRESS_BUILD = 0.70
PROGRESS_WEAR = 0.85
PROGRESS_EXPORT = 0.98

# ================================================================
# LOGGING — replace bare print() over time with logger.* calls.
# Honours SPB_VERBOSE_ENGINE=1 (DEBUG) and SPB_QUIET_ENGINE=1 (ERROR).
# ================================================================

logger = logging.getLogger("shokker.engine")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_h)
    logger.propagate = False

if os.environ.get("SPB_QUIET_ENGINE") == "1":
    logger.setLevel(logging.ERROR)
elif os.environ.get("SPB_VERBOSE_ENGINE") == "1":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


def _enforce_iron_rules(spec):
    """Centralized enforcement of the SPB iron rules on a spec-map array.

    INTERNAL helper. Mutates a copy and returns the safe array. Use this at
    every public exit point that produces a spec map so we have ONE place to
    audit and ONE place to fix bugs in CC>=16 and roughness floors.

    Args:
        spec: HxWx4 uint8 (or castable) RGBA spec map. R=Metallic, G=Roughness,
            B=Clearcoat, A=SpecMask.

    Returns:
        HxWx4 uint8 array clipped to PBR-safe values.
    """
    if spec is None:
        return spec
    s = np.asarray(spec).astype(np.float32, copy=True)
    if s.ndim != 3 or s.shape[2] < 3:
        return np.asarray(spec, dtype=np.uint8)
    M = s[:, :, 0]
    R = s[:, :, 1]
    B = s[:, :, 2]
    # CC: anywhere CC>0, force >=CC_FLOOR (no 1-15 grey zone). Pixels at
    # exactly 0 stay at 0 to allow "no clearcoat at all" in matte zones.
    cc_active = B > 0
    s[:, :, 2] = np.where(cc_active, np.maximum(B, CC_FLOOR), 0)
    # Roughness floor on non-mirror pixels.
    s[:, :, 1] = np.where(M < CHROME_M_THRESHOLD,
                          np.maximum(R, ROUGHNESS_FLOOR_NONMIRROR), R)
    # NaN/Inf safety
    s = np.nan_to_num(s, nan=0.0, posinf=255.0, neginf=0.0)
    return np.clip(s, 0, 255).astype(np.uint8)


def _coerce_seed(seed, default=51):
    """Robustly convert user-supplied seed (str/int/None) to a stable int.

    Strings are hashed deterministically so users can pass mnemonic seeds
    like ``"sunset_red"`` and get reproducible noise. None falls back to the
    default. Out-of-range ints are masked to the lower 32 bits.

    Args:
        seed: int, numeric str, arbitrary str, or None.
        default: fallback seed when ``seed`` is None or unparseable.

    Returns:
        Non-negative 32-bit int suitable for ``np.random.seed``.
    """
    if seed is None:
        return int(default) & 0xFFFFFFFF
    if isinstance(seed, (int, np.integer)):
        return int(seed) & 0xFFFFFFFF
    s = str(seed).strip()
    if not s:
        return int(default) & 0xFFFFFFFF
    try:
        return int(s) & 0xFFFFFFFF
    except ValueError:
        # Hash arbitrary strings deterministically.
        import hashlib as _hl
        return int(_hl.md5(s.encode("utf-8")).hexdigest()[:8], 16) & 0xFFFFFFFF


def _safe_div(num, den, eps=1e-6):
    """Element-wise safe division avoiding zero/NaN/Inf. INTERNAL.

    Args:
        num: numerator (scalar or ndarray).
        den: denominator (scalar or ndarray).
        eps: minimum absolute denominator after sign preservation.

    Returns:
        ``num / den`` with denominators below ``eps`` clamped to ``eps``.
    """
    d = np.where(np.abs(den) < eps, np.sign(den) * eps + (den == 0) * eps, den)
    out = np.divide(num, d)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def _validate_zones(zones):
    """Validate the high-level shape of a ``zones`` argument. INTERNAL.

    Raises ``ValueError`` with an actionable message rather than letting a
    cryptic IndexError surface deep inside build_multi_zone.

    Args:
        zones: list of dict zone specs.
    """
    if zones is None:
        raise ValueError(
            "zones must be a list of zone dicts; got None. "
            "Pass at least one zone, e.g. "
            "[{'color': 'everything', 'finish': 'gloss', 'intensity': '100'}]."
        )
    if not isinstance(zones, (list, tuple)):
        raise ValueError(
            f"zones must be a list, got {type(zones).__name__}. "
            "See the build_multi_zone docstring for the supported zone format."
        )
    if len(zones) == 0:
        raise ValueError(
            "zones is empty — at least one zone is required. "
            "Use color='everything' for a whole-car render."
        )
    for i, z in enumerate(zones):
        if not isinstance(z, dict):
            raise ValueError(
                f"zones[{i}] must be a dict, got {type(z).__name__}."
            )


def _validate_paint_file(paint_file):
    """Validate a paint file path exists and is a recognized format. INTERNAL.

    Args:
        paint_file: str/Path to the input paint image.

    Raises:
        ValueError: if missing or unsupported extension.
    """
    if paint_file is None:
        raise ValueError("paint_file is None — supply a .tga or .png path.")
    p = Path(paint_file)
    if not p.exists():
        raise ValueError(f"paint_file does not exist: {paint_file}")
    if p.suffix.lower() not in {".tga", ".png", ".jpg", ".jpeg", ".bmp"}:
        raise ValueError(
            f"paint_file has unsupported extension '{p.suffix}'. "
            "Use .tga (preferred), .png, or another PIL-readable format."
        )


def _format_zone_id(idx, zone):
    """Format a human-readable zone identifier for error messages. INTERNAL.

    Always safe to call — never raises even if ``zone`` is malformed.
    """
    try:
        name = zone.get("name") if isinstance(zone, dict) else None
        finish = (zone.get("finish") or zone.get("base") or "?") if isinstance(zone, dict) else "?"
        return f"zone[{idx}] '{name or 'unnamed'}' ({finish})"
    except Exception:
        return f"zone[{idx}]"


def _normalize_source_layer_mask(source_layer_mask, target_shape, zone_idx=None, zone=None):
    """Decode/resize a source-layer restriction mask into a binary float32 map.

    Internal helper used in both the mask-building phase and the final
    render-compositing phase so layer-restricted zones behave consistently.
    """
    if source_layer_mask is None:
        return None
    _zone_label = _format_zone_id(zone_idx, zone) if zone_idx is not None else "zone[?]"
    try:
        if isinstance(source_layer_mask, dict):
            _rw = int(source_layer_mask.get("width", 0))
            _rh = int(source_layer_mask.get("height", 0))
            _runs = source_layer_mask.get("runs", []) or []
            _flat = np.zeros(_rw * _rh, dtype=np.float32)
            _pos = 0
            for run_val, run_len in _runs:
                _flat[_pos:_pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                _pos += run_len
            source_layer_mask = _flat.reshape((_rh, _rw))
        elif isinstance(source_layer_mask, list):
            source_layer_mask = np.array(source_layer_mask, dtype=np.float32)
        else:
            source_layer_mask = np.asarray(source_layer_mask, dtype=np.float32)
    except Exception as _slm_decode_err:
        logger.warning(f"    {_zone_label} WARNING: invalid source_layer_mask ({_slm_decode_err})")
        return None

    try:
        _target_h, _target_w = int(target_shape[0]), int(target_shape[1])
        if source_layer_mask.shape != (_target_h, _target_w):
            source_layer_mask = cv2.resize(
                source_layer_mask,
                (_target_w, _target_h),
                interpolation=cv2.INTER_NEAREST
            )
        source_layer_mask = source_layer_mask.astype(np.float32)
        if np.max(source_layer_mask) > 1.0:
            source_layer_mask = source_layer_mask / 255.0
        return np.where(source_layer_mask > 0.01, 1.0, 0.0).astype(np.float32)
    except Exception as _slm_shape_err:
        logger.warning(f"    {_zone_label} WARNING: source_layer_mask normalize failed ({_slm_shape_err})")
        return None


def _build_remainder_zone_mask(zone, zone_idx, zones, zone_masks, claimed_hard, sigma=2.0):
    """Build a remainder mask, resolving source-layer-restricted zones locally."""
    h, w = claimed_hard.shape
    source_layer_mask = _normalize_source_layer_mask(
        zone.get("source_layer_mask"), (h, w), zone_idx, zone
    )

    if source_layer_mask is None:
        remainder_mask = np.clip(1.0 - claimed_hard, 0, 1).astype(np.float32)
        if sigma and sigma > 0:
            remainder_mask = _scipy_gaussian_filter(remainder_mask, sigma=sigma)
        remainder_mask = np.where(claimed_hard > 0.5, 0.0, remainder_mask).astype(np.float32)
        return remainder_mask

    # "Remaining" inside a source layer should mean "remaining within that
    # layer's own claim space". Earlier unrestricted/global zones live in the
    # flattened composite and otherwise erase the source-layer remainder before
    # the painter's Numbers/Logos restriction ever gets a chance to apply.
    layer_claimed = np.zeros((h, w), dtype=np.float32)
    for prev_idx in range(zone_idx):
        prev_mask = zone_masks[prev_idx]
        if prev_mask is None:
            continue
        prev_zone = zones[prev_idx]
        prev_source_layer_mask = _normalize_source_layer_mask(
            prev_zone.get("source_layer_mask"), (h, w), prev_idx, prev_zone
        )
        if prev_source_layer_mask is None:
            continue
        overlap_scope = (prev_source_layer_mask * source_layer_mask).astype(np.float32)
        if float(np.max(overlap_scope)) <= 0.01:
            continue
        layer_claimed = np.clip(layer_claimed + (prev_mask * overlap_scope), 0, 1)

    remainder_mask = np.clip(source_layer_mask - layer_claimed, 0, 1).astype(np.float32)
    if sigma and sigma > 0:
        remainder_mask = _scipy_gaussian_filter(remainder_mask, sigma=sigma)
    remainder_mask = np.where(source_layer_mask > 0.5, remainder_mask, 0.0).astype(np.float32)
    remainder_mask = np.where(layer_claimed > 0.5, 0.0, remainder_mask).astype(np.float32)
    return remainder_mask


def get_cache_stats():
    """Return a small dict describing engine cache occupancy.

    PUBLIC, stable. Useful for QA tooling and the /debug endpoints in the
    Flask server. Returns zero counts if no caches have been populated yet.

    Returns:
        dict with keys ``zone_cache_entries`` and ``zone_cache_keys``.
    """
    cache = getattr(build_multi_zone, "_zone_cache", {}) if "build_multi_zone" in globals() else {}
    return {
        "zone_cache_entries": len(cache),
        "zone_cache_keys": list(cache.keys())[:32],
        "engine_version": ENGINE_VERSION,
    }

from engine.utils import write_tga_32bit, write_tga_24bit, get_mgrid, generate_perlin_noise_2d, perlin_multi_octave
from engine.core import (
    hsv_to_rgb_vec, rgb_to_hsv_array, INTENSITY, _INTENSITY_SCALE,
    analyze_paint_colors, build_zone_mask, COLOR_WORD_MAP, parse_color_description,
    multi_scale_noise, _sample_zone_color,
    _resize_array, _tile_fractional, _crop_center_array, _scale_pattern_output,
    _rotate_array, _rotate_pattern_tex, _rotate_single_array, _compute_zone_auto_scale,
)

# (TGA + noise moved to engine.utils)
# (Color/mask/intensity + multi_scale_noise moved to engine.core)
# (Standard spec_/paint_ in engine.spec_paint - re-export for BASE_REGISTRY/compose)
from engine import spec_paint as _spec_paint
for _n in dir(_spec_paint):
    if _n.startswith("spec_") or _n.startswith("paint_") or _n == "_forged_carbon_chunks":
        globals()[_n] = getattr(_spec_paint, _n)
# (Color shift cs_* in engine.color_shift - re-export for MONOLITHIC_REGISTRY)
from engine import color_shift as _cs_mod
for _n in dir(_cs_mod):
    if _n.startswith("spec_cs_") or _n.startswith("paint_cs_"):
        globals()[_n] = getattr(_cs_mod, _n)
# (Compose: full implementation in engine.compose - re-export for callers)
from engine.compose import (
    compose_finish, compose_finish_stacked, compose_paint_mod, compose_paint_mod_stacked,
    _get_pattern_mask, _apply_spec_blend_mode, _apply_hsb_adjustments,
)

# GPU acceleration
try:
    from engine.gpu import xp, to_cpu, to_gpu, is_gpu
except ImportError:
    import numpy as xp
    def to_cpu(a): return a
    def to_gpu(a): return a
    def is_gpu(): return False


def _engine_rot_debug(msg):
    """No-op debug hook for rotation/build path logging. INTERNAL.

    Routes to the module logger at DEBUG level so SPB_VERBOSE_ENGINE=1
    surfaces the messages without us having to flip a hard-coded boolean.
    The function is kept so existing call sites (line ~84 originally) do
    not need to be touched for ad-hoc debugging.

    Args:
        msg: any printable object, formatted via ``str(msg)``.
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(str(msg))


# ================================================================
# SPEC MAP GENERATORS (identical to v1 - proven working)
# ================================================================

# CHAMELEON v5 - COORDINATED DUAL-MAP COLOR SHIFT SYSTEM
#
# THE SHOKKER INNOVATION: Paint and spec are generated from the
# SAME master field, creating mathematically coordinated behavior:
#
# LAYER 1: Panel direction field (macro color ramp)
# LAYER 2: Multi-stop thin-film color ramp (physically motivated)
# LAYER 3: Voronoi micro-flake texture (per-flake hue variation)
# LAYER 4: Coordinated spec - spatially varied M/R/CC:
#   - Metallic INVERSELY correlated with field (darker paint = more metal)
#   - Roughness micro-varied for per-flake reflection differences
#   - Clearcoat OPPOSING metallic for dual-layer white flash competition
# LAYER 5: Metallic brightness compensation for iRacing PBR darkening
#
# This is NOT a gradient with flat spec. This is genuine differential
# Fresnel behavior exploiting iRacing's PBR pipeline.
# ================================================================



# ================================================================
# CHAMELEON V5 FUNCTIONS - EXTRACTED TO engine/chameleon.py
# ================================================================
# The chameleon v5 paint and spec functions are now in engine/chameleon.py.
# They are imported and override this stub at the bottom of this file.
# To edit chameleon functions: open engine/chameleon.py
# ================================================================


# ================================================================
# PRIZM V4 FUNCTIONS - EXTRACTED TO engine/prizm.py
# ================================================================
# The prizm v4 paint and spec functions are now in engine/prizm.py.
# They are imported and override this stub at the bottom of this file.
# To edit prizm functions: open engine/prizm.py
# ================================================================


# ================================================================
# v4.0 NEW MONOLITHICS (Glitch, Cel Shade, Thermochromic, Aurora)
# ================================================================

def spec_glitch(shape, mask, seed, sm):
    """Glitch - digital corruption: scanlines + channel offset zones."""
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
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8); spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)  # WARN-GLITCH-001 FIX: CC=16 floor avoids GGX whitewash
    return spec

def paint_glitch(paint, shape, mask, seed, pm, bb):
    """Glitch paint - RGB channel offset + tear bands."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    np.random.seed(seed + 901)
    # RGB channel offset: shift R and B channels horizontally
    shift_r = int(np.random.randint(3, 8) * pm)
    shift_b = int(np.random.randint(-8, -3) * pm)
    r_shifted = np.roll(paint[:,:,0], shift_r, axis=1)
    b_shifted = np.roll(paint[:,:,2], shift_b, axis=1)
    paint[:,:,0] = paint[:,:,0] * (1 - 0.4 * pm * mask) + r_shifted * 0.4 * pm * mask
    paint[:,:,2] = paint[:,:,2] * (1 - 0.4 * pm * mask) + b_shifted * 0.4 * pm * mask
    # Horizontal tear bands — scaled by pm so pm=0 means no effect
    if pm > 0.01:
        n_tears = max(3, int(h // 100 * pm))
        for _ in range(n_tears):
            y_start = np.random.randint(0, h)
            band_h = np.random.randint(2, max(3, int(6 * pm)))
            shift_px = int(np.random.randint(-20, 20) * pm)
            if shift_px == 0: continue
            y_end = min(h, y_start + band_h)
            for c in range(3):
                paint[y_start:y_end, :, c] = np.roll(paint[y_start:y_end, :, c], shift_px, axis=1) * mask[y_start:y_end, :] + paint[y_start:y_end, :, c] * (1 - mask[y_start:y_end, :])
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_cel_shade(shape, mask, seed, sm):
    """Cel shade - posterized spec with bold edge outlines."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    # Simple flat spec - the magic happens in paint
    spec[:,:,0] = np.clip(80 * mask, 0, 255).astype(np.uint8)   # moderate metallic
    spec[:,:,1] = np.clip(60 * mask, 0, 255).astype(np.uint8)   # fairly smooth
    spec[:,:,2] = np.where(mask > 0.5, 16, 0).astype(np.uint8)  # clearcoat
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_cel_shade(paint, shape, mask, seed, pm, bb):
    """Cel shade - posterize paint to flat tones + Sobel edge outlines."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    paint[:, :, :3] = np.clip(paint[:, :, :3] - (outline * mask)[:, :, np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


def spec_thermochromic(shape, mask, seed, sm):
    """Thermochromic - noise-based 'heat zones' with variable metallic."""
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
    """Thermochromic paint - maps noise to thermal colormap (blue→green→yellow→red)."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Aurora - flowing borealis bands with high metallic shimmer."""
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
    """Aurora paint - flowing sine-wave color bands (green/cyan/pink)."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
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
    """Static/TV noise - high-frequency random M+R producing chaotic reflections."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    np.random.seed(seed + 1500)
    noise = np.random.randint(0, 256, (h, w), dtype=np.uint8)
    spec[:,:,0] = np.clip(noise.astype(np.float32) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((255 - noise).astype(np.float32) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255  # CC≥16
    spec[:,:,1] = np.maximum(spec[:,:,1], 15)  # R≥15 roughness floor (non-chrome)
    return spec

def paint_static(paint, shape, mask, seed, pm, bb):
    """Static paint - random B/W pixel noise."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    np.random.seed(seed + 1501)
    noise = np.random.rand(h, w).astype(np.float32)
    gray = noise[:,:,np.newaxis] * np.ones((1, 1, 3))
    blend = 0.35 * pm
    paint = np.clip(paint * (1 - blend * mask[:,:,np.newaxis]) + gray * blend * mask[:,:,np.newaxis], 0, 1)
    return paint

def spec_scorched(shape, mask, seed, sm):
    """Scorched - burnt metal with variable roughness and low metallic edges."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    burn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1600)
    burn_val = np.clip(burn * 0.5 + 0.5, 0, 1)
    M = 40 + burn_val * 180  # Low in burnt areas, high in unburnt
    R = 200 - burn_val * 160  # High roughness in burnt areas
    spec[:,:,0] = np.clip(M * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1-mask), 15, 255).astype(np.uint8)  # R≥15
    spec[:,:,2] = 16; spec[:,:,3] = 255  # CC≥16
    return spec

def paint_scorched(paint, shape, mask, seed, pm, bb):
    """Scorched - darkens with orange/brown heat discoloration zones."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Radioactive - glowing green edges with bright metallic hot spots and radiation glow."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    glow = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1700)
    glow_val = np.clip(glow * 0.5 + 0.5, 0, 1)
    # Edge detection for glowing edges (green glow at contour boundaries)
    edge_noise = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 1702)
    edges = np.clip(1.0 - np.abs(edge_noise - 0.5) * 4.0, 0, 1)
    # Hot spots: high metallic at glow peaks AND edges
    M_val = np.clip(80 + glow_val * 140 + edges * 80, 0, 255)
    R_val = np.clip(120 - glow_val * 90 - edges * 60, 0, 255)
    R_val = np.where(M_val < 240, np.maximum(R_val, 15), R_val)  # R≥15 for non-chrome
    spec[:,:,0] = np.clip(M_val * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.where(mask > 0.01, R_val, 100).astype(np.uint8)
    # CC: good clearcoat with slight variation
    CC_val = np.clip(16 + (1 - glow_val) * 15 + (1 - edges) * 10, 16, 255)
    spec[:,:,2] = np.clip(CC_val * mask + 16 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,3] = 255
    spec[:,:,1] = np.maximum(spec[:,:,1], 15)  # R≥15 roughness floor (non-chrome)
    return spec

def paint_radioactive(paint, shape, mask, seed, pm, bb):
    """Radioactive - toxic green nuclear glow with glowing edges and radiation pulses."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint
    h, w = shape
    # Radiation wave rings from center
    cy, cx = h / 2.0, w / 2.0
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt(((y - cy) / h)**2 + ((x - cx) / w)**2)
    waves = (np.sin(dist * np.pi * 30) * 0.5 + 0.5) * 0.25
    # Base toxic green glow
    glow = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1700)
    glow_val = np.clip(glow * 0.5 + 0.5, 0, 1)
    # Edge glow effect (green light at surface edges/contours)
    edge_noise = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 1702)
    edges = np.clip(1.0 - np.abs(edge_noise - 0.5) * 4.0, 0, 1)
    edge_glow = edges * 0.35
    intensity = (glow_val * 0.5 + waves + edge_glow) * pm * mask
    # Strong toxic green: kill red/blue, boost green hard, extra green at edges
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - intensity * 0.65) + edge_glow * pm * mask * 0.05, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + intensity * 0.55 + edge_glow * pm * mask * 0.25, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - intensity * 0.55) + intensity * 0.06, 0, 1)
    # Hot spots (sparse bright green flecks)
    rng = np.random.RandomState(seed + 1701)
    spots = np.where(rng.random(shape).astype(np.float32) > 0.97, 0.18 * pm, 0.0)
    paint[:,:,1] = np.clip(paint[:,:,1] + spots * mask, 0, 1)
    return paint

def spec_holographic(shape, mask, seed, sm):
    """Holographic full wrap - fine-grained rainbow metallic shifting."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # Fine holographic: ~40-60 cycles for visible rainbow bands
    rainbow = (np.sin(y * np.pi * 80 + x * np.pi * 60) * 0.5 + 0.5)
    rainbow2 = (np.sin(y * np.pi * 40 - x * np.pi * 90) * 0.5 + 0.5)
    rainbow = (rainbow + rainbow2) / 2.0
    M_raw = np.clip(235 + rainbow * 20, 0, 255)
    R_raw = np.clip(4 + rainbow * 50, 0, 255)
    R_raw = np.where(M_raw < 240, np.maximum(R_raw, 15), R_raw)
    spec[:,:,0] = np.clip(M_raw * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.where(mask > 0.01, R_raw, 100).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def paint_holographic_full(paint, shape, mask, seed, pm, bb):
    """Full holographic - VIVID fine-grained rainbow color shift."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    # 4 gratings at different angles - ~40-60 cycles for fine holographic bands
    g1 = (y * 50 + x * 40) % 1.0
    g2 = (y * 30 - x * 60) % 1.0
    g3 = ((y + x) * 45) % 1.0
    g4 = ((y - x * 0.7) * 55) % 1.0
    angle = (g1 + g2 * 0.6 + g3 * 0.4 + g4 * 0.3) / 2.3
    r_holo = np.sin(angle * np.pi * 2) * 0.5 + 0.5
    g_holo = np.sin(angle * np.pi * 2 + 2.094) * 0.5 + 0.5
    b_holo = np.sin(angle * np.pi * 2 + 4.189) * 0.5 + 0.5
    blend = 0.35 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r_holo * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g_holo * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b_holo * blend * mask, 0, 1)
    return paint


FINISH_REGISTRY = {
    # --- STANDARD ---
    "gloss":              (spec_gloss,             paint_none),
    "matte":              (spec_matte,             paint_matte_flat),  # WEAK-010: upgraded from paint_none
    "satin":              (spec_satin,             paint_none),         # WEAK-011: spec_satin now has real FBM
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
    # ── RESEARCH SESSION 6: 8 New Special Finishes (2026-03-29) ─────────────
    "iridescent_fog":        (spec_iridescent_fog,        paint_iridescent_fog),
    "chrome_delete_edge":    (spec_chrome_delete_edge,    paint_chrome_delete_edge),
    "carbon_clearcoat_lock": (spec_carbon_clearcoat_phaselock, paint_carbon_clearcoat_phaselock),
    "racing_scratch":        (spec_racing_scratch,        paint_racing_scratch),
    "pearlescent_flip":      (spec_pearlescent_flip,      paint_pearlescent_flip),
    "frost_crystal":         (spec_frost_crystal,         paint_frost_crystal),
    "satin_wax":             (spec_satin_wax,             paint_satin_wax),
    "uv_night_accent":       (spec_uv_night_accent,       paint_uv_night_accent),
}

# Wire v2 paint implementations into FINISH_REGISTRY (BROKEN-001/002, WEAK-003/005)
try:
    from engine.paint_v2.candy_special import (
        paint_candy_v2 as _paint_candy_v2,
        paint_jelly_pearl_v2 as _paint_jelly_pearl_v2,
        paint_spectraflame_v2 as _paint_spectraflame_v2,
        spec_jelly_pearl as _spec_jelly_pearl,
    )
    import numpy as _np_fr

    def _adapt_bb(fn):
        """Wrap v2 paint fn to handle scalar bb (FINISH_REGISTRY callers may pass scalar)."""
        def _wrapped(paint, shape, mask, seed, pm, bb):
            bb_val = bb
            try:
                if _np_fr.isscalar(bb):
                    h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                    bb_val = _np_fr.full((int(h), int(w)), float(bb), dtype=_np_fr.float32)
                elif hasattr(bb, "ndim") and bb.ndim == 0:
                    h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                    bb_val = _np_fr.full((int(h), int(w)), float(bb), dtype=_np_fr.float32)
            except Exception:
                bb_val = bb
            return fn(paint, shape, mask, seed, pm, bb_val)
        return _wrapped

    FINISH_REGISTRY["candy"] = (FINISH_REGISTRY["candy"][0], _adapt_bb(_paint_candy_v2))
    FINISH_REGISTRY["jelly_pearl"] = (_spec_jelly_pearl, _adapt_bb(_paint_jelly_pearl_v2))  # CONCERN-CX-001: use dedicated spec fn
    FINISH_REGISTRY["pearl"] = (spec_pearl, _adapt_bb(_paint_jelly_pearl_v2))  # WEAK-018: upgraded pearl paint to jelly_pearl_v2
    FINISH_REGISTRY["spectraflame"] = (FINISH_REGISTRY.get("spectraflame", (spec_candy, paint_spectraflame))[0], _adapt_bb(_paint_spectraflame_v2))
except Exception as _v2_fr_exc:
    print(f"[V2 FINISH_REGISTRY] v2 wire-in skipped: {_v2_fr_exc}")


# ================================================================
# v3.0 COMPOSITING SYSTEM - Base + Pattern
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
    """2x2 twill weave - visible carbon fiber at car scale.
    weave_size=20 ensures ~50 repeats across 2048px - clearly visible weave.
    Matched with paint_carbon_darken and spec_carbon_fiber (24px)."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 20  # Visible at car scale: ~50 repeats across 2048px
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    cf = np.clip(cf * 1.5 - 0.25, 0, 1)  # Boosted contrast for visibility
    return {"pattern_val": cf, "R_range": 80.0, "M_range": 40.0, "CC": None}

def texture_kevlar_weave(shape, mask, seed, sm):
    """Kevlar aramid weave - coarser than carbon fiber, visible at preview scale."""
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

def texture_forged_carbon(shape, mask, seed, sm):
    """Chopped carbon chunks - both M and R vary per chunk."""
    chunks, fine = _forged_carbon_chunks(shape, seed + 100)
    # Original: M=60+chunks*40, R=25+chunks*50+fine*8
    # Return chunks as pattern, fine noise baked into R_extra
    return {"pattern_val": chunks, "R_range": 50.0, "M_range": 40.0, "CC": None,
            "R_extra": fine * 8.0}  # extra fine noise added to R

def texture_diamond_plate(shape, mask, seed, sm):
    """Raised diamond tread - binary: raised diamonds vs flat surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    diamond_size = 20  # Tighter diamond tread pattern
    dx = (x % diamond_size) - diamond_size / 2
    dy = (y % diamond_size) - diamond_size / 2
    diamond = ((np.abs(dx) + np.abs(dy)) < diamond_size * 0.38).astype(np.float32)
    # Background metal grain for full coverage
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 1980) * 0.15 + 0.09
    diamond = np.clip(diamond + bg, 0, 1)
    return {"pattern_val": diamond, "R_range": -132.0, "M_range": 60.0, "CC": 0}

def texture_dragon_scale(shape, mask, seed, sm):
    """Hex reptile scales - gradient center=shiny to edge=rough."""
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
    # Per-scale texture variation (each scale slightly different)
    scale_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100)
    center_val = np.clip(center_val + scale_noise * 0.06 * center_val, 0, 1)
    return {"pattern_val": center_val.astype(np.float32), "R_range": -157.0, "M_range": 135.0, "CC": None}

def texture_hex_mesh(shape, mask, seed, sm):
    """Honeycomb wire grid - binary: open hex centers vs wire frame."""
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
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2580) * 0.12 + 0.07
    center = np.clip(center + bg_fill, 0, 1)
    return {"pattern_val": center, "R_range": -155.0, "M_range": 155.0, "CC": None}

def texture_ripple(shape, mask, seed, sm):
    """Concentric ring waves - sinusoidal peaks=shiny, valleys=matte."""
    h, w = shape
    # Resolution-cap: compute at 2048 max (effectively full res)
    ds = max(1, min(h, w) // 2048)
    ch, cw = max(64, h // ds), max(64, w // ds)
    y, x = get_mgrid((ch, cw))
    rng = np.random.RandomState(seed + 100)
    num_origins = int(6 + sm * 4)
    ripple_sum = np.zeros((ch, cw), dtype=np.float32)
    for _ in range(num_origins):
        cy = rng.randint(0, ch)
        cx = rng.randint(0, cw)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2).astype(np.float32)
        ring_spacing = rng.uniform(20, 40) * cw / max(w, 1)  # Scale spacing to compute res
        ripple = np.sin(dist / max(ring_spacing, 1) * 2 * np.pi)
        fade = np.clip(1.0 - dist / (max(ch, cw) * 0.6), 0, 1)
        ripple_sum += ripple * fade
    rmax = np.abs(ripple_sum).max() + 1e-8
    ring_val = (ripple_sum / rmax + 1.0) * 0.5
    if (ch, cw) != (h, w):
        ring_val = cv2.resize(ring_val.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    # Original: peak(1)=M240/R5, valley(0)=M140/R90
    return {"pattern_val": ring_val, "R_range": -85.0, "M_range": 100.0, "CC": None}

def texture_hammered(shape, mask, seed, sm):
    """Hand-hammered dimples - dimple centers=smooth, flat areas=rough."""
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
    dimple_map = cv2.resize(dimple_small.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    # Original: dimple(1)=M245/R8, flat(0)=M150/R120
    return {"pattern_val": dimple_map, "R_range": -112.0, "M_range": 95.0, "CC": 0}

def texture_lightning(shape, mask, seed, sm):
    """Forked lightning bolts - bolt paths bright, electric storm background."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    num_bolts = int(7 + sm * 4)  # More bolts for coverage
    for b in range(num_bolts):
        py = rng.randint(0, h // 3)  # Wider start range
        px = rng.randint(w // 6, 5 * w // 6)  # Wider horizontal spread
        thickness = rng.randint(3, 7)
        for step in range(h * 2):
            py += rng.randint(1, 4)
            px += rng.randint(-8, 9)  # More lateral wander
            if py >= h:
                break
            px = max(0, min(w - 1, px))
            y_lo = max(0, py - thickness)
            y_hi = min(h, py + thickness + 1)
            x_lo = max(0, px - thickness)
            x_hi = min(w, px + thickness + 1)
            bolt_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                bolt_map[y_lo:y_hi, x_lo:x_hi], 1.0)
            # More frequent forks (0.03 → 0.06)
            if rng.random() < 0.06:
                fork_px, fork_py = px, py
                fork_thick = max(2, thickness // 2)
                fork_dir = rng.choice([-1, 1])
                for _ in range(rng.randint(30, 100)):
                    fork_py += rng.randint(1, 3)
                    fork_px += fork_dir * rng.randint(1, 6)
                    if fork_py >= h or fork_px < 0 or fork_px >= w:
                        break
                    fy_lo = max(0, fork_py - fork_thick)
                    fy_hi = min(h, fork_py + fork_thick + 1)
                    fx_lo = max(0, fork_px - fork_thick)
                    fx_hi = min(w, fork_px + fork_thick + 1)
                    bolt_map[fy_lo:fy_hi, fx_lo:fx_hi] = np.maximum(
                        bolt_map[fy_lo:fy_hi, fx_lo:fx_hi], 0.85)  # Brighter forks
    bolt_map = cv2.GaussianBlur(bolt_map.astype(np.float32), (0, 0), 2.5)
    # Richer background electric storm — multi-scale noise fill
    bg_storm = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 200)
    bg_storm = np.clip(bg_storm * 0.25 + 0.15, 0.05, 0.35)  # Much brighter floor
    # Secondary crackling veins in background
    vein1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 300)
    vein2 = multi_scale_noise(shape, [12, 32, 56], [0.3, 0.3, 0.4], seed + 400)
    veins = np.abs(vein1 + vein2 * 0.5)
    vein_lines = np.clip(1.0 - veins * 4.0, 0, 1) ** 1.5 * 0.3
    bolt_map = np.clip(bolt_map + bg_storm + vein_lines, 0, 1)
    return {"pattern_val": bolt_map, "R_range": -177.0, "M_range": 175.0, "CC": None}

def texture_plasma(shape, mask, seed, sm):
    """Branching plasma veins - veins are bright, bg is matte."""
    n1 = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed+100)
    n2 = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed+200)
    veins = np.abs(n1 + n2 * 0.5)
    vein_mask_f = np.clip(1.0 - veins * 3.0, 0, 1) ** 2
    # Original: vein(1)=M255/R2, bg(0)=M160/R120
    return {"pattern_val": vein_mask_f, "R_range": -118.0, "M_range": 95.0, "CC": None}

def texture_hologram(shape, mask, seed, sm):
    """Holographic scanlines - visible banding in roughness AND metallic.
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
    """TV interference / VHS tracking distortion and static."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 80)
    
    # Base high-frequency TV static
    static = rng.random((h, w)).astype(np.float32)
    
    # Horizontal tracking bands across the height
    scan_y = (y / h) * 30.0 + rng.random() * 10.0
    tracking = np.sin(scan_y) * 0.5 + 0.5
    tracking = np.clip(tracking * 2.0 - 0.5, 0, 1) # sharpen the bands
    
    # Distortion blocks
    block_h = int(h / 15)
    block_y = (y // block_h).astype(np.float32)
    block_noise = np.sin(block_y * 13.7 + seed) * 0.5 + 0.5
    glitch = (block_noise > 0.85).astype(np.float32)
    
    # Combine static with tearing/bands
    pattern = np.clip(static * 0.4 + tracking * 0.4 + glitch * static * 0.8, 0, 1)
    
    return {"pattern_val": pattern, "R_range": -80.0, "M_range": 60.0, "CC": None}

def texture_battle_worn(shape, mask, seed, sm):
    """Scratch damage pattern - variable clearcoat. Uses noise, not geometric pattern."""
    h, w = shape
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
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
    """Corroded acid etch - variable clearcoat."""
    etch = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed+100)
    etch_depth = np.clip(np.abs(etch) * 2, 0, 1)
    cc = np.clip(16 * (1 - etch_depth * 0.8), 0, 16).astype(np.uint8)
    # Original: M=200+etch*35, R=60+etch*60. Etch drives everything.
    return {"pattern_val": etch_depth, "R_range": 60.0, "M_range": 35.0, "CC": cc}

def texture_cracked_ice(shape, mask, seed, sm):
    """Frozen crack network - cracks add roughness."""
    h, w = shape
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [12, 24, 48], [0.3, 0.4, 0.3], seed+200)
    crack1 = np.exp(-n1**2 * 20)
    crack2 = np.exp(-n2**2 * 20)
    cracks = np.clip(crack1 + crack2, 0, 1)
    # Original: M=230+mn*15 (near flat), R: ice=15, crack=15+cracks*115
    # cracks=1 means crack line = rougher
    return {"pattern_val": cracks, "R_range": 115.0, "M_range": 40.0, "CC": None}

def texture_metal_flake(shape, mask, seed, sm):
    """Coarse metallic flake sparkle - noise-driven M and R variation."""
    mf = multi_scale_noise(shape, [16, 32, 64, 128], [0.1, 0.2, 0.35, 0.35], seed+100)
    rf = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+200)
    # Metal flake has two independent noise fields. Use mf as pattern_val,
    # and store rf as R_extra for independent R noise.
    flake_val = np.clip((mf + 1) * 0.5, 0, 1)  # normalize to 0-1
    return {"pattern_val": flake_val, "R_range": -60.0, "M_range": 50.0, "CC": None,
            "R_extra": rf * 40.0}

def texture_holographic_flake(shape, mask, seed, sm):
    """Prismatic micro-grid flake - grid roughness + sparse bright flakes."""
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
    """Deep starfield with multi-sized stars and nebula background."""
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    star_field = rng.random((h, w)).astype(np.float32)
    
    # Multi-sized stars
    tiny_stars = (star_field > 0.98).astype(np.float32) * 0.4
    med_stars = (star_field > 0.995).astype(np.float32) * 0.7
    large_stars = (star_field > 0.999).astype(np.float32) * 1.0
    stars = np.clip(tiny_stars + med_stars + large_stars, 0, 1)
    
    # Nebula background clouds
    nebula = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed+101)
    nebula = np.clip((nebula + 0.5) * 0.6, 0, 1) * 0.45  # Brighter nebula (was *0.3)

    pattern = np.clip(stars + nebula, 0, 1)
    return {"pattern_val": pattern, "R_range": 35.0, "M_range": 20.0, "CC": None,
            "R_extra": stars * -80.0, "M_extra": stars * 95.0}


# --- TEXTURE FUNCTIONS: Expansion Pack (14 new patterns) ---

def texture_pinstripe(shape, mask, seed, sm):
    """Racing pinstripes v2 — scaled, anti-aliased, multi-width with fine grain."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    dim = min(h, w)
    # Scale: ~80 stripes across canvas (was fixed 16px period)
    period = max(6, dim / 80.0)
    stripe_w = max(1.5, period * 0.2)
    # Primary stripes (horizontal)
    phase = yf % period
    stripe1 = np.clip(1.0 - np.abs(phase - period * 0.5) / stripe_w, 0, 1)
    # Thinner secondary stripes (offset)
    stripe2 = np.clip(1.0 - np.abs(phase - period * 0.15) / (stripe_w * 0.5), 0, 1) * 0.5
    # Combine + fine grain texture
    grain = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100)
    pv = np.clip(stripe1 + stripe2 + grain * 0.04, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -65.0, "M_range": 45.0, "CC": None}

def texture_camo(shape, mask, seed, sm):
    """Camo v2 — multi-scale blobs with sharp boundaries, edge noise, 4 distinct tone zones.
    Wider scale range for organic irregular patches. Fine grain at boundaries."""
    h, w = shape
    # Wide scale range: small splinter detail + large zone blobs
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 700)
    n2 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 701)
    n3 = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 702)
    fine = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 703)
    # 4 tone zones with slightly soft boundaries (not pure hard threshold)
    zone1 = np.clip((n2 - 0.15) * 4.0, 0, 1)  # Large dark patches
    zone2 = np.clip((n1 - 0.10) * 3.5, 0, 1)  # Medium mid-tone patches
    zone3 = np.clip((n3 - 0.20) * 3.0, 0, 1)  # Splinter light patches
    # Layered composition: dark base → mid → light → fine grain
    camo = zone1 * 0.25 + zone2 * 0.35 + zone3 * 0.40
    # Add fine-grain edge noise for realistic disruption
    camo = np.clip(camo + fine * 0.06, 0, 1)
    return {"pattern_val": camo.astype(np.float32), "R_range": 60.0, "M_range": -30.0, "CC": 0}

def texture_wood_grain(shape, mask, seed, sm):
    """Natural wood grain — tight flowing horizontal lines with growth rings and knots."""
    h, w = shape
    dim = min(h, w)
    rng = np.random.RandomState(seed + 800)
    # Fine horizontal grain lines — per-row noise at full resolution
    row_noise = rng.randn(h, 1).astype(np.float32) * 0.8
    grain = np.tile(row_noise, (1, w))
    # Growth ring pattern — tight sine waves with noise warp
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    # Fine waviness — high frequency for tight grain
    warp = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 801) * 8.0
    ring_freq = max(0.08, dim / 800.0)  # ~256 rings at 2048
    rings = np.sin((yf + warp) * ring_freq) * 0.3
    # Knots — small elliptical distortions
    n_knots = max(3, dim // 300)
    knot_field = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_knots):
        ky, kx = rng.randint(0, h), rng.randint(0, w)
        kr = rng.uniform(10, max(20, dim // 60))
        dist = np.sqrt(((yf - ky) / 1.5) ** 2 + (xf - kx) ** 2)
        knot = np.exp(-(dist ** 2) / (2 * kr ** 2)) * 0.5
        knot_field = np.maximum(knot_field, knot)
    # Fine surface grain noise
    fine = rng.randn(h, w).astype(np.float32) * 0.1
    grain = np.clip((grain + rings + knot_field + fine + 1.5) / 3.0, 0, 1)
    return {"pattern_val": grain.astype(np.float32), "R_range": 80.0, "M_range": -50.0, "CC": 0}

def texture_snake_skin(shape, mask, seed, sm):
    """Elongated irregular scales - rectangular overlapping pattern."""
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

def texture_snake_skin_2(shape, mask, seed, sm):
    """Diamond-shaped python scales with color variation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    ds = 24.0
    row = (y // ds).astype(np.float32)
    ox = (row % 2) * (ds / 2.0)
    lx = ((x + ox) % ds) - ds / 2.0
    ly = (y % ds) - ds / 2.0
    diamond = (np.abs(lx) + np.abs(ly)) / (ds * 0.5)
    center = np.clip(1.0 - diamond, 0, 1)
    return {"pattern_val": center, "R_range": -90.0, "M_range": 75.0, "CC": None}

def texture_snake_skin_3(shape, mask, seed, sm):
    """Hourglass saddle pattern viper scales."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cw, ch = 30.0, 22.0
    row = (y // ch).astype(np.float32)
    ox = (row % 2) * (cw / 2.0)
    lx = ((x + ox) % cw) / cw
    ly = (y % ch) / ch
    pinch = 0.3 + 0.4 * np.abs(ly - 0.5) * 2.0
    dist = np.abs(lx - 0.5) / (pinch * 0.5 + 1e-5)
    in_hourglass = dist < 1.0
    fade = np.where(in_hourglass, np.clip(1.0 - dist, 0, 1), 0.0)
    bg_hash = (np.sin(row * 5.3 + ((x + ox) // cw) * 11.7) * 0.5 + 0.5) * (1.0 - in_hourglass)
    pattern = np.clip(fade + bg_hash * 0.3, 0, 1)
    return {"pattern_val": pattern, "R_range": -85.0, "M_range": 70.0, "CC": None}

def texture_snake_skin_4(shape, mask, seed, sm):
    """Cobblestone pebble boa constrictor scales."""
    h, w = shape
    y, x = get_mgrid((h, w))
    from scipy.spatial import cKDTree
    rng = np.random.RandomState(seed + 4014)
    cell_s = 28.0
    grid_y = int(h / cell_s) + 2
    grid_x = int(w / cell_s) + 2
    cy, cx = np.mgrid[0:grid_y, 0:grid_x]
    pts_y = (cy * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    pts_x = (cx * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    points = np.column_stack((pts_y, pts_x))
    tree = cKDTree(points)
    coords = np.column_stack((y.flatten(), x.flatten()))
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(h, w).astype(np.float32)
    d2 = dists[:, 1].reshape(h, w).astype(np.float32)
    edge = d2 - d1
    centerDist = d1 / (cell_s * 0.6)
    center = np.clip(1.0 - centerDist * 0.8, 0, 1)
    is_groove = edge < 2.0
    pattern = np.where(is_groove, 0.0, center)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 60.0, "CC": None}

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
    """PCB trace lines with pads - orthogonal right-angle paths."""
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
    # PCB board background texture for full coverage
    pcb_bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1650) * 0.14 + 0.09
    circuit = np.clip(circuit + pcb_bg, 0, 1)
    return {"pattern_val": circuit, "R_range": -120.0, "M_range": 140.0, "CC": None}

def texture_mosaic(shape, mask, seed, sm):
    """Tessellation v2 — dense Voronoi tiles with per-cell tonal variation and sharp grout."""
    h, w = shape
    from scipy.spatial import cKDTree
    dim = min(h, w)
    # Dense cells: ~1050 at 2048 for fine 20-40px tiles (was /4000 = ~1050, now /1600 = ~2621)
    num_cells = max(200, int(dim * dim / 1600))
    rng = np.random.RandomState(seed + 900)
    pts = np.column_stack([rng.uniform(0, h, num_cells), rng.uniform(0, w, num_cells)]).astype(np.float32)
    # Use cKDTree for speed
    tree = cKDTree(pts)
    yg, xg = np.mgrid[0:h, 0:w]
    coords = np.column_stack([yg.ravel().astype(np.float32), xg.ravel().astype(np.float32)])
    d, idx = tree.query(coords, k=2, workers=-1)
    d1 = d[:, 0].reshape(h, w).astype(np.float32)
    d2 = d[:, 1].reshape(h, w).astype(np.float32)
    cell_id = idx[:, 0].reshape(h, w)
    # Sharp grout lines at cell boundaries
    edge = d2 - d1
    grout = np.clip(1.0 - edge / max(2.0, dim / 800.0), 0, 1)
    # Per-cell tonal variation (each tile slightly different brightness)
    cell_tone = rng.uniform(0.3, 0.9, num_cells).astype(np.float32)
    tile_shade = cell_tone[cell_id]
    # Combine: tile body + sharp grout lines
    pv = np.clip(tile_shade * (1.0 - grout * 0.7) + grout * 0.15, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -90.0, "M_range": 80.0, "CC": None}

def texture_lava_flow(shape, mask, seed, sm):
    """Flowing molten rock cracks - directional with hot/cool zones."""
    h, w = shape
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [8, 24, 48], [0.3, 0.4, 0.3], seed+200)
    # Crack detection + directional flow
    cracks = np.exp(-n1**2 * 12)
    flow = np.clip((n2 + 0.3) * 1.5, 0, 1)
    lava = np.clip(cracks * 0.7 + flow * 0.3, 0, 1)
    # lava=1 = hot crack (smooth, metallic), lava=0 = cool rock (rough, matte)
    cc = np.clip(16 * (1 - lava * 0.6), 0, 16).astype(np.uint8)
    return {"pattern_val": lava, "R_range": -140.0, "M_range": 120.0, "CC": cc}

def texture_rain_drop(shape, mask, seed, sm):
    """Water droplets v2 — denser beading with size variation, surface texture, and highlights."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    num_drops = int(350 * sm)  # More drops (was 200)
    ds = 2
    sh, sw = h // ds, w // ds
    drop_map = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(num_drops):
        dy = rng.randint(0, sh)
        dx = rng.randint(0, sw)
        dr = rng.randint(1, 6)  # Larger max radius (was 4)
        y_lo = max(0, dy - dr); y_hi = min(sh, dy + dr + 1)
        x_lo = max(0, dx - dr); x_hi = min(sw, dx + dr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - dy)**2 + (xg - dx)**2).astype(np.float32)
        # Dome profile without squaring (full contrast)
        drop = np.clip(1.0 - dist / dr, 0, 1)
        # Highlight on upper-left of each droplet
        hl_dist = np.sqrt((yg - dy + 0.8)**2 + (xg - dx + 0.8)**2).astype(np.float32)
        highlight = np.clip(1.0 - hl_dist / (dr * 0.4), 0, 1) * 0.3
        drop_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(drop_map[y_lo:y_hi, x_lo:x_hi], drop + highlight)
    drop_full = cv2.resize(np.clip(drop_map, 0, 1).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    # Surface texture between drops
    surface = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1101)
    result = np.clip(drop_full + surface * 0.06, 0, 1)
    return {"pattern_val": result.astype(np.float32), "R_range": -80.0, "M_range": 60.0, "CC": None}

def texture_barbed_wire(shape, mask, seed, sm):
    """Twisted wire with barb spikes - aggressive repeating motif."""
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
    # Background metal surface texture for full coverage
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 1450) * 0.15 + 0.08
    wire = np.clip(wire + bg, 0, 1)
    return {"pattern_val": wire, "R_range": -100.0, "M_range": 130.0, "CC": 0}

def texture_chainmail(shape, mask, seed, sm):
    """Interlocking metal ring mesh - circular repeating pattern."""
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
    """Organic leopard rosette spots - ring-shaped markings."""
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
    spot_full = cv2.resize(spot_map.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    # spot=1 = dark ring mark, spot=0 = fur/surface
    return {"pattern_val": spot_full, "R_range": 50.0, "M_range": -60.0, "CC": 0}

def texture_razor(shape, mask, seed, sm):
    """Razor v2 — diagonal slash marks with scratched surface texture between cuts."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    dim = min(h, w)
    slash_period = max(12, dim // 65)
    slash_w = max(1.5, dim // 400)
    slash = (xf - yf * 2) % slash_period
    # Anti-aliased slashes
    cuts = np.clip(1.0 - np.abs(slash - slash_period * 0.5) / slash_w, 0, 1)
    # Scratched surface between cuts
    scratch_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 200)
    surface = np.clip(scratch_noise * 0.08 + 0.05, 0, 0.15)
    pv = np.clip(cuts + surface, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -80.0, "M_range": 120.0, "CC": 0}


# ================================================================
# v4.0 NEW PATTERN TEXTURES + PAINT FUNCTIONS
# ================================================================

def texture_tron(shape, mask, seed, sm):
    """Tron v2 — neon grid with cell texture fill and glow around lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    dim = min(h, w)
    grid_size = max(36, dim // 28)  # Denser grid (was dim//21)
    line_w = max(2, dim // 400)
    # Grid lines
    hline = np.clip(1.0 - np.abs((yf % grid_size) - line_w * 0.5) / line_w, 0, 1)
    vline = np.clip(1.0 - np.abs((xf % grid_size) - line_w * 0.5) / line_w, 0, 1)
    grid = np.clip(hline + vline, 0, 1)
    # Glow around lines (wider, dimmer halo)
    glow_w = line_w * 3
    h_glow = np.clip(1.0 - np.abs((yf % grid_size) - line_w * 0.5) / glow_w, 0, 1) * 0.15
    v_glow = np.clip(1.0 - np.abs((xf % grid_size) - line_w * 0.5) / glow_w, 0, 1) * 0.15
    # Cell interior noise (subtle circuit texture)
    cell_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100)
    cell_fill = np.clip(cell_noise * 0.06 + 0.04, 0, 0.12)
    pv = np.clip(grid + h_glow + v_glow + cell_fill, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -120.0, "M_range": 180.0, "CC": 0}

def paint_tron_glow(paint, shape, mask, seed, pm, bb):
    """Tron lines - neon glow along grid lines (cyan-ish)."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Dazzle camouflage - bold intersecting geometric zebra-like stripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 830)
    
    # Generate intersecting angled stripe fields
    stripe1 = np.sin((x * 0.05) + (y * 0.02) + rng.random()*10)*0.5+0.5
    stripe2 = np.sin((x * -0.03) + (y * 0.04) + rng.random()*10)*0.5+0.5
    stripe3 = np.sin((x * 0.01) + (y * -0.06) + rng.random()*10)*0.5+0.5
    
    # Sharp boundaries
    s1 = (stripe1 > 0.5).astype(np.float32)
    s2 = (stripe2 > 0.6).astype(np.float32)
    s3 = (stripe3 > 0.55).astype(np.float32)
    
    # XOR / Intersection logic for erratic geometry
    pattern = np.clip((s1 + s2 + s3) % 2, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -80.0, "CC": 0}

def paint_dazzle_contrast(paint, shape, mask, seed, pm, bb):
    """Dazzle - bold black/white patches for maximum contrast."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape
    n_pts = max(20, int(h * w / 4000))
    cell_id = _voronoi_cells_fast(shape, n_pts, 830, seed)
    dark_cells = (cell_id % 2).astype(np.float32)
    darken = dark_cells * 0.35 * pm
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - (darken * mask)[:, :, np.newaxis]), 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint


def texture_marble(shape, mask, seed, sm):
    """Marble - soft noise veins using Gaussian zero-crossings."""
    h, w = shape
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 840)
    # Veins at zero-crossings of noise
    vein = np.exp(-noise**2 * 12)  # peaks at zero crossings
    vein = np.clip(vein, 0, 1)
    return {"pattern_val": vein, "R_range": -80.0, "M_range": 60.0, "CC": None}

def paint_marble_vein(paint, shape, mask, seed, pm, bb):
    """Marble veins - darken along vein lines for depth."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 840)
    vein = np.exp(-noise**2 * 12)
    darken = vein * 0.1 * pm
    paint[:, :, :3] = np.clip(paint[:, :, :3] - (darken * mask)[:, :, np.newaxis], 0, 1)
    return paint


def texture_mega_flake(shape, mask, seed, sm):
    """Mega Flake - large hex glitter flakes (~12px)."""
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
    """Mega Flake - random bright sparkle on each large flake facet."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape
    np.random.seed(seed + 851)
    sparkle = np.random.rand(h, w).astype(np.float32)
    sparkle = np.where(sparkle > 0.85, sparkle * 0.12 * pm, 0)
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


def texture_multicam(shape, mask, seed, sm):
    """Multicam - 5-layer organic Perlin camo pattern."""
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
    """Multicam - applies multi-tone desaturation for tactical look."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    # Slight desaturation for camo zones
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 860)
    zones = np.clip((n + 0.5) * 1.2, 0, 1)
    desat = zones * 0.2 * pm
    dm = (desat * mask)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - dm) + mean_c[:, :, np.newaxis] * dm, 0, 1)
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
        crack = cv2.resize(crack.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return crack

def texture_magma_crack(shape, mask, seed, sm):
    """Magma Crack - Voronoi boundary cracks glow orange like lava."""
    h, w = shape
    n_pts = max(15, int(h * w / 6000))
    crack = _voronoi_cracks_fast(shape, n_pts, 870, seed, 12.0)
    return {"pattern_val": crack, "R_range": -160.0, "M_range": 140.0, "CC": 0}

def paint_magma_glow(paint, shape, mask, seed, pm, bb):
    """Magma cracks - orange glow along crack boundaries."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Rivet Plate v3 — dense industrial riveted panels with seams, surface grain, and
    raised chrome dome rivets. Small features for 2048 car-scale visibility.
    Vectorized template stamping for speed."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    panel_h, panel_w = 48, 48  # Smaller panels = denser grid on car
    # Panel seam grooves: 4px wide, dark (visible at car scale)
    h_seam = np.clip(1.0 - np.abs((yf % panel_h) - 1.5) / 2.0, 0, 1)
    v_seam = np.clip(1.0 - np.abs((xf % panel_w) - 1.5) / 2.0, 0, 1)
    seams = np.clip(h_seam + v_seam, 0, 1)
    # Panel surface texture: subtle hammered/brushed grain per panel
    panel_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 500)
    surface = np.clip(panel_noise * 0.15 + 0.5, 0, 1).astype(np.float32)
    # Rivet heads: 5px radius domes, NO squaring (full contrast)
    rivet_r = 5
    tpl_sz = rivet_r * 2 + 1
    ty = np.arange(tpl_sz, dtype=np.float32).reshape(-1, 1) - rivet_r
    tx = np.arange(tpl_sz, dtype=np.float32).reshape(1, -1) - rivet_r
    dist = np.sqrt(ty * ty + tx * tx)
    # Hemisphere dome with highlight (light from upper-left)
    dome = np.clip(1.0 - dist / rivet_r, 0, 1)
    highlight = np.clip(1.0 - np.sqrt((ty + 1.5)**2 + (tx + 1.5)**2) / (rivet_r * 0.6), 0, 1) * 0.3
    rivet_tpl = np.clip(dome + highlight, 0, 1)
    # Stamp rivets at panel corners + mid-seam positions
    rivet_map = np.zeros((h, w), dtype=np.float32)
    for ry in range(0, h, panel_h):
        for rx in range(0, w, panel_w):
            # 4 rivets per panel: corners near seams
            for (dy, dx) in [(4, 4), (4, panel_w - 5), (panel_h - 5, 4), (panel_h - 5, panel_w - 5)]:
                cy_r, cx_r = ry + dy, rx + dx
                if cy_r >= h or cx_r >= w:
                    continue
                y0 = max(0, cy_r - rivet_r)
                y1 = min(h, cy_r + rivet_r + 1)
                x0 = max(0, cx_r - rivet_r)
                x1 = min(w, cx_r + rivet_r + 1)
                ty0, tx0 = y0 - (cy_r - rivet_r), x0 - (cx_r - rivet_r)
                rivet_map[y0:y1, x0:x1] = np.maximum(
                    rivet_map[y0:y1, x0:x1],
                    rivet_tpl[ty0:ty0 + y1 - y0, tx0:tx0 + x1 - x0])
    # Combine: surface texture + seam grooves (dark) + rivet bumps (bright)
    pattern = np.clip(surface * (1 - seams * 0.6) + rivet_map * 0.9, 0, 1)
    return {"pattern_val": pattern, "R_range": -85.0, "M_range": 90.0, "CC": 0}

def paint_rivet_plate_emboss(paint, shape, mask, seed, pm, bb):
    """Rivet plate - darken seam grooves, brighten rivet heads."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    y, x = get_mgrid((h, w))
    panel_h, panel_w = 80, 80
    h_seam = ((y % panel_h) < 2).astype(np.float32)
    v_seam = ((x % panel_w) < 2).astype(np.float32)
    seams = np.clip(h_seam + v_seam, 0, 1)
    darken = seams * 0.18 * pm  # Visible seam grooves (was 5%)
    # Rivet heads — small bright dots at grid intersections
    rivet = (h_seam * v_seam) * 0.12 * pm
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis] + rivet[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_frost_crystal(shape, mask, seed, sm):
    """Frost Crystal - ice crystal branching fractals with sharp dendrite edges."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    # Multi-scale ice crystal structure — fine scales for dendrite detail
    n1 = multi_scale_noise(shape, [32, 64, 128], [0.25, 0.40, 0.35], seed + 1101)
    n2 = multi_scale_noise(shape, [48, 96, 192], [0.30, 0.40, 0.30], seed + 1102)
    n3 = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 1103)
    # Create crystal branches using ridge detection (abs of centered noise)
    ridge1 = 1.0 - np.abs(n1 - 0.5) * 2.0  # Bright at ridge lines
    ridge2 = 1.0 - np.abs(n2 - 0.5) * 2.0
    crystal = ridge1 * 0.5 + ridge2 * 0.3 + n3 * 0.2
    # Sharpen the crystal edges
    crystal = np.clip((crystal - 0.2) * 1.8, 0, 1)
    # Add micro-frost texture
    frost_fine = multi_scale_noise(shape, [96, 192], [0.5, 0.5], seed + 1104)
    crystal = np.clip(crystal * 0.75 + frost_fine * 0.25, 0.0, 1.0).astype(np.float32)
    return {"pattern_val": crystal, "R_range": -80.0, "M_range": 60.0, "CC": None}

def paint_frost_crystal(paint, shape, mask, seed, pm, bb):
    """Frost crystal - whitens along crystal paths with icy blue tint."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:,:,np.newaxis]
    crystal = texture_frost_crystal(shape, mask, seed, 1.0)['pattern_val']
    # Cool-white tint along crystal ridges
    brighten = crystal * 0.12 * pm
    blue_tint = crystal * 0.06 * pm
    mask3 = mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + brighten * 0.8 * mask, 0, 1)  # R
    paint[:,:,1] = np.clip(paint[:,:,1] + brighten * 0.9 * mask, 0, 1)  # G
    paint[:,:,2] = np.clip(paint[:,:,2] + (brighten + blue_tint) * mask, 0, 1)  # B boost
    return paint

def texture_wave(shape, mask, seed, sm):
    """Wave - smooth flowing sine wave ripples."""
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
    """Wave shimmer - subtle brightness oscillation along wave."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Spiderweb - radial + concentric thin crack lines."""
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
    ring_spacing = max(15.0, min(h, w) / 60.0)  # Denser webs (was fixed 40px)
    rings = np.abs(np.sin(dist / ring_spacing * np.pi))
    ring_lines = (rings < 0.06).astype(np.float32)
    # Anti-aliased web lines (smooth falloff)
    spoke_aa = np.clip(1.0 - spoke / 0.08, 0, 1)
    ring_aa = np.clip(1.0 - rings / 0.10, 0, 1)
    # Web silk between structures (subtle radial gradient)
    silk = np.clip(0.08 - dist / (max(h, w) * 0.8), 0, 0.08)
    # Dew drops on web (fine noise)
    dew = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 100) * 0.04
    web = np.clip(spoke_aa + ring_aa + silk + np.where(spoke_aa + ring_aa > 0.1, dew, 0), 0, 1)
    # Background cobweb haze for full canvas coverage
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1350) * 0.12 + 0.08
    web = np.clip(web + bg, 0, 1)
    return {"pattern_val": web.astype(np.float32), "R_range": 80.0, "M_range": -40.0, "CC": 0}

def paint_spiderweb_crack(paint, shape, mask, seed, pm, bb):
    """Spiderweb - subtle darken along web lines."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    paint = np.clip(paint - web[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1)  # 15% darken (was 4%)
    return paint

def texture_topographic(shape, mask, seed, sm):
    """Topographic v2 — contour lines with elevation shading between them."""
    h, w = shape
    elev = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    elev = (elev + 1) * 0.5  # 0-1
    n_contours = 25  # More contours (was 20)
    contour = np.abs(np.sin(elev * n_contours * np.pi))
    # Anti-aliased contour lines (smooth falloff, not binary)
    lines = np.clip(1.0 - contour / 0.12, 0, 1)
    # Elevation shading between contours (full canvas coverage)
    shade = elev * 0.32  # Terrain brightness (was 0.25)
    pv = np.clip(lines + shade, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": 70.0, "M_range": -30.0, "CC": None}

def paint_topographic_line(paint, shape, mask, seed, pm, bb):
    """Topographic contour — visible dark contour lines + elevation tinting."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    elev = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1300)
    elev = (elev + 1) * 0.5
    lines = (np.abs(np.sin(elev * 20 * np.pi)) < 0.08).astype(np.float32)
    # Stronger contour darkening (20% vs 5%)
    paint = np.clip(paint - lines[:, :, np.newaxis] * 0.20 * pm * mask[:, :, np.newaxis], 0, 1)
    # Subtle elevation tinting — higher = slightly lighter
    elev_tint = elev * 0.08 * pm
    paint = np.clip(paint + elev_tint[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    return paint

def texture_crosshatch(shape, mask, seed, sm):
    """Crosshatch - overlapping 45deg line grids like pen strokes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    spacing = 20
    line_w = 2
    diag1 = ((y + x) % spacing < line_w).astype(np.float32)
    diag2 = ((y - x + 10000) % spacing < line_w).astype(np.float32)
    hatch = np.clip(diag1 + diag2, 0, 1)
    # Subtle surface grain for full coverage
    bg = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 1550) * 0.12 + 0.07
    hatch = np.clip(hatch + bg, 0, 1)
    return {"pattern_val": hatch, "R_range": 55.0, "M_range": -25.0, "CC": 0}

def paint_crosshatch_ink(paint, shape, mask, seed, pm, bb):
    """Crosshatch ink - darken along hatch lines."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Chevron v2 — dense V-stripes with anti-aliased edges and size scaling."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    dim = min(h, w)
    # ~50 chevrons across canvas (was min 60px = ~34 max)
    period = max(8, dim / 50.0)
    stripe_w = period * 0.3
    # V-shape: diagonal fold
    v_offset = np.abs((xf % period) - period * 0.5) * 0.8
    phase = (yf + v_offset) % period
    # Anti-aliased stripe (smooth falloff, not binary)
    chevron = np.clip(1.0 - np.abs(phase - period * 0.5) / stripe_w, 0, 1)
    # Second thinner chevron offset
    phase2 = (yf + v_offset + period * 0.4) % period
    chevron2 = np.clip(1.0 - np.abs(phase2 - period * 0.5) / (stripe_w * 0.4), 0, 1) * 0.4
    pv = np.clip(chevron + chevron2, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": 75.0, "M_range": -45.0, "CC": None}

def paint_chevron_contrast(paint, shape, mask, seed, pm, bb):
    """Chevron - alternating slight brightness difference."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(60, min(h, w) // 16)
    v_shape = np.abs((x % period) - period // 2).astype(np.float32) / (period // 2)
    stripe = ((y + v_shape * period // 2).astype(np.int32) % period < period // 3).astype(np.float32)
    paint = np.clip(paint + (stripe - 0.5)[:,:,np.newaxis] * 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_celtic_knot(shape, mask, seed, sm):
    """Celtic knot v2 — dense interlocking bands with over-under weave illusion."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    # ~20 knot repeats across canvas (was 6 fixed)
    freq = max(12, dim / 50.0)
    yf = y.astype(np.float32) / freq * np.pi
    xf = x.astype(np.float32) / freq * np.pi
    # Two sets of interlocking bands with stronger modulation
    band1 = np.sin(xf + np.sin(yf * 2.5) * 1.2)
    band2 = np.sin(yf + np.sin(xf * 2.5) * 1.2)
    # Third diagonal band for knot complexity
    band3 = np.sin((xf + yf) * 0.7 + np.sin((xf - yf) * 1.5) * 0.8)
    # Sharp band edges (narrow lines, not broad blobs)
    knot1 = np.clip(1.0 - np.abs(band1) * 2.5, 0, 1)
    knot2 = np.clip(1.0 - np.abs(band2) * 2.5, 0, 1)
    knot3 = np.clip(1.0 - np.abs(band3) * 3.0, 0, 1) * 0.6
    # Over-under: band1 dominates where band2 is low (creates weave)
    weave = np.maximum(knot1 * (1.0 - knot2 * 0.4), knot2 * (1.0 - knot1 * 0.4))
    weave = np.maximum(weave, knot3)
    return {"pattern_val": np.clip(weave, 0, 1).astype(np.float32), "R_range": 65.0, "M_range": -25.0, "CC": None}

def paint_celtic_emboss(paint, shape, mask, seed, pm, bb):
    """Celtic knot - subtle emboss on band edges."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Skull mesh - array of skull-like shapes from concentric ovals + eye holes."""
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
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1950) * 0.14 + 0.08
    skull = np.clip(skull + bg, 0, 1)
    return {"pattern_val": skull, "R_range": 50.0, "M_range": -20.0, "CC": 0}

def paint_skull_darken(paint, shape, mask, seed, pm, bb):
    """Skull mesh - darkens eye holes and outline edges."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    cell_h, cell_w = 64, 48
    y, x = get_mgrid((h, w))
    ty = (y % cell_h).astype(np.float32) / cell_h - 0.5
    tx = (x % cell_w).astype(np.float32) / cell_w - 0.5
    eye_l = np.clip(1.0 - ((tx + 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    eye_r = np.clip(1.0 - ((tx - 0.12)**2 + (ty + 0.08)**2) / 0.005, 0, 1)
    darken = (eye_l + eye_r) * 0.25 * pm  # Stronger: 25% darkening in eye holes (was 6%)
    # Also darken skull outline edges
    skull_oval = np.clip(1.0 - (tx**2 / 0.12 + ty**2 / 0.18) * 1.5, 0, 1)
    outline = np.clip(skull_oval - 0.1, 0, 0.9) * 0.1 * pm  # Subtle outline brightening
    paint = np.clip(paint - darken[:,:,np.newaxis] * mask[:,:,np.newaxis] + outline[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_damascus(shape, mask, seed, sm):
    """Damascus steel - flowing layered wavy metal grain."""
    h, w = shape
    np.random.seed(seed + 1400)
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1401)
    # Flowing horizontal waves disturbed by noise
    wave = np.sin((y * 30 + n1 * 3) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 70.0, "M_range": 50.0, "CC": 0}

def paint_damascus_layer(paint, shape, mask, seed, pm, bb):
    """Damascus - alternating bright/dark metal layers."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1401)
    h = shape[0]
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    wave = np.sin((y * 30 + n1 * 3) * np.pi) * 0.5 + 0.5
    paint = np.clip(paint + (wave - 0.5)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_houndstooth_contrast(paint, shape, mask, seed, pm, bb):
    """Houndstooth - alternating brightness for classic pattern visibility."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    cell = max(32, min(h, w) // 28)
    y, x = get_mgrid((h, w))
    check = ((y // cell) % 2 ^ (x // cell) % 2).astype(np.float32)
    paint = np.clip(paint + (check - 0.5)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_plaid(shape, mask, seed, sm):
    """Plaid/Tartan v2 — dense multi-band tartan with weave texture, scaled to canvas."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    dim = min(h, w)
    # ~60 plaid cells across canvas (was fixed 48px)
    cell = max(8, dim / 60.0)
    # 3 band widths: wide, medium, thin (proportional to cell)
    ym = yf % cell
    xm = xf % cell
    # Horizontal bands
    h_wide = np.clip(1.0 - np.abs(ym - cell * 0.2) / (cell * 0.08), 0, 1)
    h_med  = np.clip(1.0 - np.abs(ym - cell * 0.5) / (cell * 0.04), 0, 1) * 0.6
    h_thin = np.clip(1.0 - np.abs(ym - cell * 0.75) / (cell * 0.02), 0, 1) * 0.35
    # Vertical bands (same structure)
    v_wide = np.clip(1.0 - np.abs(xm - cell * 0.2) / (cell * 0.08), 0, 1)
    v_med  = np.clip(1.0 - np.abs(xm - cell * 0.5) / (cell * 0.04), 0, 1) * 0.6
    v_thin = np.clip(1.0 - np.abs(xm - cell * 0.75) / (cell * 0.02), 0, 1) * 0.35
    horiz = h_wide + h_med + h_thin
    vert = v_wide + v_med + v_thin
    # Weave: intersections are brighter (additive blend)
    plaid = np.clip(horiz * 0.5 + vert * 0.5 + horiz * vert * 0.3, 0, 1)
    return {"pattern_val": plaid.astype(np.float32), "R_range": 75.0, "M_range": -45.0, "CC": None}


def paint_plaid_tint(paint, shape, mask, seed, pm, bb):
    """Plaid - alternating warm/cool shift on bands."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Oil slick - flowing rainbow pools with high metallic and variable roughness."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+200)
    pool = np.clip((n1 + n2) * 0.5 + 0.5, 0, 1)
    M_raw = np.clip(220 + pool * 35, 0, 255)
    R_raw = np.clip(5 + pool * 60, 0, 255)
    R_raw = np.where(M_raw < 240, np.maximum(R_raw, 15), R_raw)  # R≥15 for non-chrome
    spec[:,:,0] = np.clip(M_raw * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.where(mask > 0.01, R_raw, 100).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_galaxy(shape, mask, seed, sm):
    """Galaxy - deep space nebula with discrete star point reflections.
    FIXED WEAK-021: star density reduced from 2% to 0.5% for discrete points not noise field.
    Star pixels: M=230+ (high metallic peak), R=2 (mirror-like near-zero roughness).
    Nebula pixels: moderate M=80-150, R=30-60. Gaussian star metallic dot via blur."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    nebula = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    nebula_val = np.clip((nebula + 0.5) * 1.2, 0, 1)
    # LCG hash star field matching paint function star positions (~0.5% density for spec)
    flat_idx = np.arange(h * w, dtype=np.uint32)
    lcg = ((flat_idx * 1664525 + (seed & 0xFFFF)) * 22695477 + 1013904223) & 0xFFFFFFFF
    stars = (lcg % 1000 < 5).reshape(h, w).astype(np.float32)  # ~0.5% of pixels
    # Gaussian spread so each star metallic peak is a dot not a single pixel
    stars_spread = cv2.GaussianBlur(stars.astype(np.float32), (0, 0), 1.5)
    # Spec channels:
    # M (red): nebula=80-150, star peaks=220-255
    M_nebula = 80 + nebula_val * 70
    M_stars = np.clip(stars_spread * 255 * 1.2, 0, 255)
    M = np.clip(M_nebula + M_stars, 0, 255)
    # R (green): nebula=30-60, star pixels=2 (mirror-like reflection)
    R_nebula = 30 + nebula_val * 30
    R_stars = stars_spread * 255  # stars_spread blended DOWN: star pixels pull R low
    R = np.clip(R_nebula - R_stars * 0.8, 2, 255)
    # Chrome exception: only allow R<15 where M>=240 (actual star peaks)
    chrome_mask = M >= 240
    R = np.where(chrome_mask, R, np.clip(R, 15, 255))
    spec[:,:,0] = np.clip(M * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(R * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_rust(shape, mask, seed, sm):
    """Progressive rust - oxidation patches with variable roughness and no clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed+100)
    rust = np.clip((mn + 0.2) * 2, 0, 1)
    # Rusty areas: low metallic, high roughness, no clearcoat
    spec[:,:,0] = np.clip((180 - rust * 140) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((40 + rust * 180) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    cc = np.clip(16 + rust * 160, 16, 200).astype(np.uint8)  # rust degrades CC upward (more degraded)
    spec[:,:,2] = np.where(mask > 0.01, cc, 16).astype(np.uint8)  # CC≥16
    spec[:,:,3] = 255
    return spec

def spec_neon_glow(shape, mask, seed, sm):
    """Neon glow - edge-detected high metallic with variable roughness for glow effect."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    # Edge-like features from noise gradients
    edges = np.clip(np.abs(mn) * 3, 0, 1)
    spec[:,:,0] = np.clip((200 + edges * 55) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((10 + (1-edges) * 80) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    spec[:,:,1] = np.maximum(spec[:,:,1], 15)  # R≥15 roughness floor (non-chrome)
    return spec

def spec_weathered_paint(shape, mask, seed, sm):
    """Weathered paint - faded peeling layers showing underlayer patches."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    peel = np.clip((mn + 0.1) * 1.5, 0, 1)
    # Peeled areas: exposed primer (low metallic, high roughness, no CC)
    # Intact areas: normal paint (mid metallic, low roughness, full CC)
    spec[:,:,0] = np.clip((180 - peel * 130) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((20 + peel * 160) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    cc = np.clip(16 + peel * 150, 16, 200).astype(np.uint8)  # peel degrades CC upward
    spec[:,:,2] = np.where(mask > 0.01, cc, 16).astype(np.uint8)  # CC≥16
    spec[:,:,3] = 255
    return spec


# --- v5.5 "SHOKK THE SYSTEM" ADDITIONS (5 new patterns + 5 new bases for #55) ---

def texture_fracture(shape, mask, seed, sm):
    """Fracture - shattered impact glass with radial + Voronoi crack network."""
    h, w = shape
    np.random.seed(seed + 5500)
    n_impacts = int(3 + sm * 2)
    impact_y = np.random.randint(h // 6, 5 * h // 6, n_impacts).astype(np.float32)
    impact_x = np.random.randint(w // 6, 5 * w // 6, n_impacts).astype(np.float32)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Voronoi crack network via cKDTree (fast vectorized k=2 query)
    from scipy.spatial import cKDTree
    n_vor = max(30, int(h * w / 8000))
    np.random.seed(seed + 5501)
    vor_y = np.random.randint(0, h, n_vor).astype(np.float32)
    vor_x = np.random.randint(0, w, n_vor).astype(np.float32)
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    pts = np.column_stack([vor_y, vor_x])
    tree = cKDTree(pts)
    sy = np.arange(sh, dtype=np.float32) * ds
    sx = np.arange(sw, dtype=np.float32) * ds
    gy, gx = np.meshgrid(sy, sx, indexing='ij')
    coords = np.column_stack([gy.ravel(), gx.ravel()])
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(sh, sw).astype(np.float32)
    d2 = dists[:, 1].reshape(sh, sw).astype(np.float32)
    vor_crack = np.clip(1.0 - (d2 - d1) / 8.0, 0, 1)
    if ds > 1:
        vor_crack = cv2.resize(vor_crack.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
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
    """Fracture - darkens crack lines to simulate exposed substrate."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    darken = radial * 0.30 * pm  # 30% darkening in cracks (was 8%)
    # Also shift crack areas toward darker/desaturated (exposed substrate)
    crack_desat = radial * 0.15 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] - darken * mask - crack_desat * mask * 0.5, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - darken * mask - crack_desat * mask * 0.3, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - darken * mask, 0, 1)
    return paint

def texture_ember_mesh(shape, mask, seed, sm):
    """Ember Mesh - glowing hot wire grid with fading ember nodes at intersections."""
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
    # Anti-aliased grid lines + glow halo
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    glow_w = max(4, cell // 6)
    h_glow = np.clip(1.0 - np.abs((yf % cell)) / glow_w, 0, 1) * 0.12
    v_glow = np.clip(1.0 - np.abs((xf % cell)) / glow_w, 0, 1) * 0.12
    # Heat radiation between wires
    heat = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100)
    heat_bg = np.clip(heat * 0.18 + 0.10, 0, 0.25)
    ember = np.clip(grid * 0.8 + nodes * 0.4 + h_glow + v_glow + heat_bg, 0, 1)
    return {"pattern_val": ember.astype(np.float32), "R_range": -80.0, "M_range": 140.0, "CC": 0}

def paint_ember_mesh_glow(paint, shape, mask, seed, pm, bb):
    """Ember mesh - orange/red glow on wire lines."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Turbine - radial fan blade pattern spinning from center."""
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
    """Turbine - alternating light/dark blade sectors."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Static Noise - TV static random pixel noise pattern."""
    h, w = shape
    np.random.seed(seed + 5540)
    # Coarse static: blocky pixel groups scaled to resolution
    block = max(4, min(h, w) // 256)
    sh, sw = h // block, w // block
    coarse = np.random.random((sh, sw)).astype(np.float32)
    coarse_up = cv2.resize(coarse.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    # Fine static overlay
    fine = np.random.random((h, w)).astype(np.float32)
    static_val = np.clip(coarse_up * 0.6 + fine * 0.4, 0, 1)
    return {"pattern_val": static_val, "R_range": 80.0, "M_range": -30.0, "CC": 0}

def paint_static_noise_grain(paint, shape, mask, seed, pm, bb):
    """Static noise - random brightness jitter like analog TV snow."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    np.random.seed(seed + 5540)
    block = max(4, min(h, w) // 256)
    sh, sw = h // block, w // block
    coarse = np.random.random((sh, sw)).astype(np.float32)
    coarse_up = cv2.resize(coarse.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    grain = (coarse_up - 0.5) * 0.04 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def texture_razor_wire(shape, mask, seed, sm):
    """Razor Wire - coiled helical wire with barbed loops over gritty metal surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_f = y.astype(np.float32)
    x_f = x.astype(np.float32)
    dim = min(h, w)
    spacing = max(40, dim // 24)  # Tighter strand spacing
    coil_r = max(6, dim // 140)
    coil_freq = max(10, dim // 90)
    barb_sp = max(18, dim // 50)
    # Gritty metal surface background — full canvas coverage
    bg_noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 700)
    bg = np.clip(bg_noise * 0.2 + 0.12, 0.02, 0.3)
    # Horizontal coil strands
    strand_y = (y_f % spacing).astype(np.float32)
    center = spacing / 2.0
    coil = np.sin(x_f / coil_freq * np.pi * 2) * coil_r
    dist_from_coil = np.abs(strand_y - center - coil)
    wire = np.clip(1.0 - dist_from_coil / 3.5, 0, 1)
    # Secondary coil at different phase for depth
    coil2 = np.sin(x_f / coil_freq * np.pi * 2 + np.pi * 0.7) * coil_r * 0.6
    dist2 = np.abs(strand_y - center - coil2)
    wire2 = np.clip(1.0 - dist2 / 3.0, 0, 1) * 0.5
    # Barb spikes at regular intervals — more prominent
    barb_x = ((x % barb_sp) < max(4, dim // 300)).astype(np.float32)
    barb_mask = wire * barb_x
    # Wire shadow beneath strands
    shadow_dist = np.abs(strand_y - center - coil - 3.0)
    shadow = np.clip(1.0 - shadow_dist / 6.0, 0, 1) * 0.15
    result = np.clip(bg + wire + wire2 + barb_mask * 0.6 + shadow, 0, 1)
    return {"pattern_val": result.astype(np.float32), "R_range": 65.0, "M_range": 80.0, "CC": 0}

def paint_razor_wire_scratch(paint, shape, mask, seed, pm, bb):
    """Razor wire - dark scratch marks along wire paths."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    darken = wire * 0.22 * pm  # Visible scratches (was 6%)
    # Slight metallic shift in scratched areas (exposed metal)
    paint[:, :, 0] = np.clip(paint[:, :, 0] - darken * mask * 0.8, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - darken * mask * 0.6, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - darken * mask * 0.4, 0, 1)
    return paint


# --- v5.5 NEW BASE PAINT FUNCTIONS ---

def paint_plasma_shift(paint, shape, mask, seed, pm, bb):
    """Plasma metal - electric purple/blue micro-shift hue injection."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    np.random.seed(seed + 5550)
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5551)
    shift = np.clip(n * 0.5 + 0.5, 0, 1) * pm * 0.04
    paint[:,:,0] = np.clip(paint[:,:,0] + shift * 0.4 * mask, 0, 1)   # slight magenta
    paint[:,:,1] = np.clip(paint[:,:,1] - shift * 0.15 * mask, 0, 1)  # deepen green
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)   # blue push
    return paint

def paint_burnt_metal(paint, shape, mask, seed, pm, bb):
    """Burnt metal - exhaust header heat discoloration, golden/blue oxide."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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
    """Mercury - liquid metal pooling effect, heavy desaturation with bright caustics."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    np.random.seed(seed + 5570)
    caustic = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 5571)
    bright = np.clip(caustic, 0, 1) * 0.03 * pm
    paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_electric_blue_tint(paint, shape, mask, seed, pm, bb):
    """Electric blue tint - icy blue metallic color push."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    shift = 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] - shift * 0.3 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + shift * 0.2 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)
    return paint

def paint_volcanic_ash(paint, shape, mask, seed, pm, bb):
    """Volcanic ash - desaturates and darkens with gritty fine grain."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
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

# === SHOKK SERIES - UPGRADED EXISTING PATTERNS ===

def texture_shokk_bolt_v2(shape, mask, seed, sm):
    """SHOKK Bolt: Fractal branching lightning with independent R/M.
    R channel shows the main discharge path (chrome-mirror in the bolt),
    M channel shows the ionization field around it (metallic corona glow).
    Creates lightning that shifts between chrome and matte under different angles."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # PERF: recursive bolt = O(branches^depth). MUST cap low. 256 is the safe max.
    MAX_DIM = 256
    ds = max(1, min(h, w) // MAX_DIM)
    sh, sw = max(64, h // ds), max(64, w // ds)
    if sh > MAX_DIM or sw > MAX_DIM:
        scale_down = MAX_DIM / max(sh, sw)
        sh, sw = max(64, int(sh * scale_down)), max(64, int(sw * scale_down))
    bolt_map = np.zeros((sh, sw), dtype=np.float32)
    glow_map = np.zeros((sh, sw), dtype=np.float32)
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)

    def _draw_bolt(x0, y0, x1, y1, thickness, brightness, depth=0):
        if depth > 5 or brightness < 0.15:
            return
        n_segs = max(3, int(np.sqrt((x1-x0)**2 + (y1-y0)**2) / 15))
        pts_x = np.linspace(x0, x1, n_segs + 1)
        pts_y = np.linspace(y0, y1, n_segs + 1)
        for i in range(1, len(pts_x) - 1):
            pts_x[i] += rng.uniform(-20, 20) * (0.7 ** depth)
            pts_y[i] += rng.uniform(-10, 10) * (0.7 ** depth)
        for i in range(len(pts_x) - 1):
            sx, sy = pts_x[i], pts_y[i]
            ex, ey = pts_x[i+1], pts_y[i+1]
            seg_len = max(1, np.sqrt((ex-sx)**2 + (ey-sy)**2))
            dx, dy = ex - sx, ey - sy
            t = np.clip(((xx - sx) * dx + (yy - sy) * dy) / (seg_len**2 + 1e-8), 0, 1)
            proj_x = sx + t * dx
            proj_y = sy + t * dy
            dist = np.sqrt((xx - proj_x)**2 + (yy - proj_y)**2)
            core = np.clip(1.0 - dist / max(1, thickness), 0, 1) * brightness
            bolt_map[:] = np.maximum(bolt_map, core)
            corona = np.exp(-(dist**2) / (2 * (thickness * 4)**2)) * brightness * 0.6
            glow_map[:] = np.maximum(glow_map, corona)
            if rng.rand() < 0.3 and depth < 3:
                bx = sx + (ex - sx) * rng.uniform(0.3, 0.7)
                by = sy + (ey - sy) * rng.uniform(0.3, 0.7)
                branch_angle = rng.uniform(-1.2, 1.2)
                branch_len = seg_len * rng.uniform(0.4, 0.8)
                bex = bx + np.cos(np.arctan2(ey-sy, ex-sx) + branch_angle) * branch_len
                bey = by + np.sin(np.arctan2(ey-sy, ex-sx) + branch_angle) * branch_len
                _draw_bolt(bx, by, bex, bey, thickness * 0.6, brightness * 0.7, depth + 1)

    for _ in range(rng.randint(2, 5)):
        x0 = rng.randint(sw // 4, 3 * sw // 4)
        _draw_bolt(x0, 0, x0 + rng.randint(-sw//3, sw//3), sh, rng.uniform(2, 4), rng.uniform(0.7, 1.0))

    if bolt_map.shape[0] != h or bolt_map.shape[1] != w:
        bolt_map = cv2.resize(np.clip(bolt_map, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
        glow_map = cv2.resize(np.clip(glow_map, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
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
    # PERF: Compute at 512 max — N impacts × N cracks per impact = O(N² × pixels)
    ds = max(1, min(h, w) // 512)
    sh, sw = max(64, h // ds), max(64, w // ds)
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    crack_map = np.zeros((sh, sw), dtype=np.float32)
    shard_map = np.zeros((sh, sw), dtype=np.float32)

    n_impacts = rng.randint(3, 6)  # More impacts for denser coverage
    for _ in range(n_impacts):
        cx, cy = rng.randint(sw//6, 5*sw//6), rng.randint(sh//6, 5*sh//6)
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        angle = np.arctan2(yy - cy, xx - cx)
        max_r = min(sh, sw) * rng.uniform(0.12, 0.28)  # Tighter cracks for finer detail

        n_cracks = rng.randint(10, 18)  # More cracks for denser pattern
        for ci in range(n_cracks):
            crack_angle = ci * 2 * np.pi / n_cracks + rng.uniform(-0.2, 0.2)
            crack_width = rng.uniform(1.0, 2.5)
            ang_dist = np.abs(np.sin(angle - crack_angle))
            radial_crack = np.clip(1.0 - ang_dist * dist / crack_width, 0, 1)
            radial_crack *= np.clip(1.0 - dist / max_r, 0, 1)
            crack_map = np.maximum(crack_map, radial_crack * rng.uniform(0.5, 1.0))

        n_rings = rng.randint(3, 7)
        for ri in range(n_rings):
            ring_r = max_r * (ri + 1) / (n_rings + 1)
            ring = np.clip(1.0 - np.abs(dist - ring_r) / 2.0, 0, 1) * 0.9
            crack_map = np.maximum(crack_map, ring * np.clip(1.0 - dist / max_r, 0, 1))

        for ci in range(n_cracks):
            a1 = ci * 2 * np.pi / n_cracks
            a2 = (ci + 1) * 2 * np.pi / n_cracks
            in_wedge = (((angle - a1) % (2*np.pi)) < ((a2 - a1) % (2*np.pi))).astype(np.float32)
            tilt = rng.uniform(0.2, 1.0)
            shard_map += in_wedge * tilt * np.clip(1.0 - dist / max_r, 0, 1) * 0.5

        crater = np.clip(1.0 - dist / 15, 0, 1)
        crack_map = np.maximum(crack_map, crater)

    if ds > 1:
        crack_map = cv2.resize(crack_map, (w, h), interpolation=cv2.INTER_LINEAR)
        shard_map = cv2.resize(shard_map, (w, h), interpolation=cv2.INTER_LINEAR)
    crack_map = np.clip(crack_map, 0, 1)
    shard_map = np.clip(shard_map, 0, 1)
    R_pattern = crack_map  # High R in cracks = rough matte
    M_pattern = shard_map * (1.0 - crack_map * 0.8)  # Shards are metallic, cracks are not
    pv = np.clip(crack_map * 0.7 + shard_map * 0.5, 0, 1)  # Stronger (was 0.6/0.4)
    CC_pattern = np.clip(crater * 0.8, 0, 1) if n_impacts == 1 else None
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "CC_pattern": CC_pattern, "M_range": 50, "R_range": -65,
            "CC": None, "CC_range": 20 if CC_pattern is not None else 0}


def texture_shokk_pulse_wave_v2(shape, mask, seed, sm):
    """SHOKK Pulse Wave: Expanding concentric pulses with R/M phase offset.
    R and M channels show rings offset by half a wavelength - when R is at peak
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

    # Use R_pattern as primary visual (shows concentric ring structure)
    # Add high-freq noise for texture detail
    detail = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 3100) * 0.08
    pv = np.clip(R_pattern + detail, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 50, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_scream_v2(shape, mask, seed, sm):
    """SHOKK Scream: Acoustic shockwave visualization with R/M opposition.
    Simulates visible sound - pressure waves radiate from center with compression
    zones (high M = chrome) and rarefaction zones (high R = matte). The R and M
    channels are in direct opposition: where one peaks, the other troughs."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # PERF: compute at 1024 max — concentric waves upscale perfectly
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    cy, cx = sh / 2.0, sw / 2.0
    dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    angle = np.arctan2(yy - cy, xx - cx)
    max_r = np.sqrt(sh**2 + sw**2) / 2

    freq = 10 + rng.randint(0, 6)  # Higher frequency for finer pressure waves
    mouth_dir = rng.uniform(0, 2 * np.pi)
    directionality = 0.5 + 0.5 * np.cos(angle - mouth_dir)

    wave = np.sin(dist / max(max_r, 1) * 2 * np.pi * freq + angle * 0.8)
    M_pattern = np.clip((wave + 1) / 2 * directionality, 0, 1)
    R_pattern = np.clip((-wave + 1) / 2 * directionality, 0, 1)

    n_lines = 12 + rng.randint(0, 8)
    for i in range(n_lines):
        line_angle = mouth_dir + rng.uniform(-0.8, 0.8)
        ang_dist = np.abs(np.sin(angle - line_angle))
        line = np.clip(1.0 - ang_dist * 30, 0, 1) * np.clip(dist / max(max_r * 0.5, 1), 0, 1)
        M_pattern = np.clip(M_pattern + line * 0.2, 0, 1)

    center_void = np.clip(1.0 - dist / 10, 0, 1)  # Tighter void
    R_pattern = np.clip(R_pattern + center_void * 0.5, 0, 1)

    # Upscale to full resolution
    if ds > 1:
        M_pattern = cv2.resize(M_pattern.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        R_pattern = cv2.resize(R_pattern.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)

    pv = np.maximum(M_pattern, R_pattern)
    grain = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 300) * 0.03
    pv = np.clip(pv + grain, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


# === SHOKK SERIES - 7 NEW BOUNDARY-PUSHING PATTERNS ===

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
    # PERF: compute at 256×256 max — gas clouds and stars upscale perfectly
    ds = max(1, min(h, w) // 512)
    sh, sw = max(64, h // ds), max(64, w // ds)
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)

    dust = np.zeros((sh, sw), dtype=np.float32)
    stars = np.zeros((sh, sw), dtype=np.float32)
    for octave in range(5):
        freq = 2 ** (octave + 1)
        amp = 0.5 ** octave
        phase_x = rng.uniform(0, 100)
        phase_y = rng.uniform(0, 100)
        noise_x = np.sin(xx / max(sw, 1) * freq * np.pi + phase_x) * np.cos(yy / max(sh, 1) * freq * 0.7 * np.pi + phase_y)
        noise_y = np.cos(yy / max(sh, 1) * freq * np.pi + phase_y * 1.3) * np.sin(xx / max(sw, 1) * freq * 0.8 * np.pi + phase_x * 0.7)
        dust += (noise_x + noise_y) * amp

    dust = (dust - dust.min()) / (dust.max() - dust.min() + 1e-8)

    n_stars = rng.randint(15, 40)
    for _ in range(n_stars):
        sx, sy = rng.randint(0, sw), rng.randint(0, sh)
        sr = rng.uniform(5, 25) / ds
        brightness = rng.uniform(0.4, 1.0)
        star_dist = np.sqrt((xx - sx)**2 + (yy - sy)**2)
        star = np.exp(-(star_dist**2) / (2 * max(1, sr)**2)) * brightness
        stars = np.maximum(stars, star)

    filaments = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(rng.randint(5, 12)):
        fa = rng.uniform(0, np.pi)
        fp = rng.uniform(0, 100)
        fil = np.sin((xx * np.cos(fa) + yy * np.sin(fa)) / max(min(sh,sw), 1) * rng.uniform(3, 8) * np.pi + fp)
        fil = np.clip(fil, 0, 1) ** 3 * rng.uniform(0.3, 0.7)
        filaments = np.maximum(filaments, fil)

    # Upscale to full resolution
    if ds > 1:
        dust = cv2.resize(dust, (w, h), interpolation=cv2.INTER_LINEAR)
        stars = cv2.resize(stars, (w, h), interpolation=cv2.INTER_LINEAR)
        filaments = cv2.resize(filaments, (w, h), interpolation=cv2.INTER_LINEAR)

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
    pv = np.maximum(R_pattern, M_pattern)  # Max not avg
    grain = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 400) * 0.03
    pv = np.clip(pv + grain, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_tesseract(shape, mask, seed, sm):
    """SHOKK Tesseract: 4D hypercube projected into 2D - exotic geometry.
    R channel shows outer cube wireframe edges. M channel shows inner cube edges
    rotated 45 degrees. Creates an optical illusion of depth and dimensionality
    where the two cubes seem to phase through each other under lighting changes.
    OPTIMIZED: compute at 256x256 max, upscale."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Resolution cap for performance
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)

    # Tiling cell size
    cell = max(40, min(sh, sw) // 5)
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
    # Upscale to full resolution
    if ds > 1:
        pv = cv2.resize(pv.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        M_pattern = cv2.resize(M_pattern.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        R_pattern = cv2.resize(R_pattern.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return {"pattern_val": pv, "M_pattern": M_pattern, "R_pattern": R_pattern,
            "M_range": 55, "R_range": -65, "CC": None, "CC_pattern": None, "CC_range": 0}


def texture_shokk_plasma_storm(shape, mask, seed, sm):
    """SHOKK Plasma Storm: Violent branching plasma discharge from multiple epicenters.
    OPTIMIZED: compute at 256x256 max, upscale. Smooth fields upscale perfectly."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # PERF: N sources × N arms × sub-arms = O(N³ × pixels). Cap at 512.
    ds = max(1, min(h, w) // 512)
    sh, sw = max(64, h // ds), max(64, w // ds)
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    discharge = np.zeros((sh, sw), dtype=np.float32)
    field = np.zeros((sh, sw), dtype=np.float32)

    # Multiple epicenters (use scaled coordinates)
    n_sources = rng.randint(3, 7)
    for src in range(n_sources):
        cx = rng.randint(sw // 8, 7 * sw // 8)
        cy = rng.randint(sh // 8, 7 * sh // 8)
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        angle = np.arctan2(yy - cy, xx - cx)

        n_arms = rng.randint(4, 8)
        for arm in range(n_arms):
            arm_angle = arm * 2 * np.pi / n_arms + rng.uniform(-0.3, 0.3)
            ang_diff = np.abs(np.sin(angle - arm_angle))
            max_dist = min(sh, sw) * rng.uniform(0.15, 0.4)
            arm_width = 3.0 + dist * 0.02
            arm_line = np.exp(-(ang_diff * dist)**2 / (2 * arm_width**2))
            arm_line *= np.clip(1.0 - dist / max_dist, 0, 1)
            discharge = np.maximum(discharge, arm_line * rng.uniform(0.5, 1.0))

            for sub in range(rng.randint(2, 5)):
                sub_dist = max_dist * rng.uniform(0.2, 0.7)
                sub_angle = arm_angle + rng.uniform(-0.8, 0.8)
                sub_mask = (dist > sub_dist * 0.8) & (dist < sub_dist * 1.5)
                sub_ang_diff = np.abs(np.sin(angle - sub_angle))
                sub_line = np.exp(-(sub_ang_diff * dist)**2 / (2 * 2.0**2))
                sub_line *= sub_mask.astype(np.float32) * 0.5
                discharge = np.maximum(discharge, sub_line)

        core = np.exp(-(dist**2) / (2 * 8**2)) * 0.8  # Tighter core for finer detail
        discharge = np.maximum(discharge, core)
        ion_glow = np.exp(-(dist**2) / (2 * (max_dist * 0.4)**2)) * 0.5  # Tighter glow
        field = np.maximum(field, ion_glow)

    # Upscale to full resolution
    if ds > 1:
        discharge = cv2.resize(discharge, (w, h), interpolation=cv2.INTER_LINEAR)
        field = cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR)
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
    The Shokker signature sound made visible - a music visualizer in spec map.
    OPTIMIZED: compute at 256x256 max, upscale. Smooth fields upscale perfectly."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # PERF: Resolution cap at 384 — per-bar loop is O(bands × bars × pixels).
    MAX_DIM = 384
    ds = max(1, min(h, w) // MAX_DIM)
    sh, sw = max(64, h // ds), max(64, w // ds)
    if sh > MAX_DIM or sw > MAX_DIM:
        scale_down = MAX_DIM / max(sh, sw)
        sh, sw = max(64, int(sh * scale_down)), max(64, int(sw * scale_down))
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)

    n_bands = 16  # Frequency bands
    band_h = sh / n_bands
    amplitude = np.zeros((sh, sw), dtype=np.float32)
    energy = np.zeros((sh, sw), dtype=np.float32)

    for band in range(n_bands):
        y_center = (band + 0.5) * band_h
        band_mask = np.exp(-((yy - y_center)**2) / (2 * (band_h * 0.35)**2))

        # Generate "audio" waveform for this frequency band
        freq = 1 + band * 0.5  # Lower bands = lower visual frequency
        base_amp = rng.uniform(0.3, 1.0)
        phase = rng.uniform(0, 2 * np.pi)

        # Waveform envelope: random amplitude modulation
        env_freq = rng.uniform(0.5, 3.0)
        envelope = np.abs(np.sin(xx / max(sw, 1) * env_freq * np.pi + phase))
        # Bass bands get bigger amplitude bars
        bass_boost = max(0.5, 1.0 - band / n_bands * 0.7)

        # Amplitude bars (vertical bars whose height follows the waveform)
        bar_width = max(4, sw // 64)
        bar_x = (xx // bar_width).astype(int)
        bar_val = np.zeros_like(xx)
        unique_bars = np.unique(bar_x)
        for bx in unique_bars[:min(len(unique_bars), 200)]:
            bar_center_x = (bx + 0.5) * bar_width
            bar_amp = base_amp * (0.3 + 0.7 * np.abs(np.sin(bx * 0.3 + phase)))
            bar_mask = (bar_x == bx).astype(np.float32)
            bar_val += bar_mask * bar_amp

        amplitude += band_mask * bar_val * bass_boost * 0.35  # Was 0.15

        # Energy: smooth sine wave per band
        wave = (np.sin(xx / max(sw, 1) * freq * 2 * np.pi + phase) + 1.0) / 2.0
        energy += band_mask * wave * base_amp * 0.30  # Was 0.15

    # EKG signature pulse across center
    center_band = sh // 2
    pulse_y = np.exp(-((yy - center_band)**2) / (2 * (band_h * 0.8)**2))
    pulse_x = np.sin(xx / max(sw, 1) * 8 * np.pi)
    # Sharp EKG spike
    spike_pos = sw * rng.uniform(0.3, 0.7)
    spike = np.exp(-((xx - spike_pos)**2) / (2 * 10**2)) * 3.0
    ekg = pulse_y * np.clip(pulse_x * 0.4 + spike, -0.5, 1.0)

    amplitude = np.clip(amplitude + ekg * 0.5, 0, 1)  # Was 0.3
    energy = np.clip(energy + ekg * 0.4, 0, 1)  # Was 0.2

    # Fine grid overlay for monitor/screen look
    grid = np.sin(yy * np.pi * 0.5) ** 2 * 0.06 + np.sin(xx * np.pi * 0.25) ** 2 * 0.04

    # Upscale to full resolution
    if amplitude.shape[0] != h or amplitude.shape[1] != w:
        amplitude = cv2.resize(amplitude.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        energy = cv2.resize(energy.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        grid = cv2.resize(grid.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)

    R_pattern = amplitude
    M_pattern = energy
    pv = np.clip(np.maximum(amplitude, energy) + grid, 0, 1)  # max not avg
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
    """Subtle paint tint for SHOKK Phase patterns - slight contrast shift."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm <= 0:
        return paint
    rng = np.random.RandomState(seed + 999)
    boost = 0.04 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + boost * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - boost * 0.3 * mask, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════
# TEXTURE VARIANTS - 50 new procedural textures for pattern variety
# Research-based: flame styles, tribal/ornamental, wave/flow, geometric, etc.
# Each gives a distinct look so pattern IDs are no longer aliased to one texture.
# ══════════════════════════════════════════════════════════════════════════

def texture_flame_sweep(shape, mask, seed, sm):
    """Classic hot rod flame - horizontal sweep, thick at bottom thinning up."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1)
    n = multi_scale_noise(shape, [12, 24, 48], [0.25, 0.4, 0.35], seed + 301)
    sweep = np.clip(1.0 - yn * 1.2 + n * 0.4, 0, 1)
    sweep = np.power(sweep, 1.2)
    cc = np.clip(16 * (1 - sweep * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": sweep, "R_range": -130.0, "M_range": 110.0, "CC": cc}

def texture_flame_ribbon(shape, mask, seed, sm):
    """Thin ribbon-like flame bands - elegant flowing strips."""
    h, w = shape
    y, x = get_mgrid((h, w))
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 302)
    bands = np.sin(y.astype(np.float32) / max(h, 1) * np.pi * 8 + n * 2) * 0.5 + 0.5
    ribbon = np.clip(np.abs(bands - 0.5) * 2.5, 0, 1)
    cc = np.clip(16 * (1 - ribbon * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": ribbon, "R_range": -120.0, "M_range": 100.0, "CC": cc}

def texture_flame_tongues(shape, mask, seed, sm):
    """Vertical licking flame tongues - upward flicker."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = 1.0 - y.astype(np.float32) / max(h, 1)
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 303)
    tongues = np.clip(yn * 1.1 + n * 0.35, 0, 1)
    tongues = np.power(tongues, 0.9)
    cc = np.clip(16 * (1 - tongues * 0.6), 0, 16).astype(np.uint8)
    return {"pattern_val": tongues, "R_range": -140.0, "M_range": 115.0, "CC": cc}

def texture_flame_teardrop(shape, mask, seed, sm):
    """Teardrop flame shapes - organic droplet flow."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1)
    xn = (x.astype(np.float32) / max(w, 1) - 0.5) * 2
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 304)
    drop = np.clip(1.0 - yn - np.abs(xn) * 0.3 + n * 0.25, 0, 1)
    cc = np.clip(16 * (1 - drop * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": drop, "R_range": -125.0, "M_range": 105.0, "CC": cc}

def texture_flame_smoke_fade(shape, mask, seed, sm):
    """Flames fading into soft smoke - gradient with soft edges."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1)
    n = multi_scale_noise(shape, [8, 16, 32], [0.35, 0.4, 0.25], seed + 305)
    fade = np.clip((1.0 - yn) * 1.3 + n * 0.5, 0, 1)
    fade = np.power(fade, 1.5)
    cc = np.clip(16 * (1 - fade * 0.4), 0, 16).astype(np.uint8)
    return {"pattern_val": fade, "R_range": -100.0, "M_range": 90.0, "CC": cc}

def texture_flame_aggressive(shape, mask, seed, sm):
    """Sharp high-contrast flames - hellfire style."""
    h, w = shape
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.4, 0.2], seed + 306)
    n2 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 307)
    cracks = np.exp(-n1 ** 2 * 8)
    flow = np.clip((n2 + 0.2) * 1.8, 0, 1)
    agg = np.clip(cracks * 0.8 + flow * 0.2, 0, 1)
    cc = np.clip(16 * (1 - agg * 0.7), 0, 16).astype(np.uint8)
    return {"pattern_val": agg, "R_range": -150.0, "M_range": 130.0, "CC": cc}

def texture_flame_ghost_soft(shape, mask, seed, sm):
    """Ghost flames v2 — ethereal wisps with fine turbulence detail and sharp edges.
    Multi-scale noise for wisp structure + vertical gradient + edge turbulence."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    yn = 1.0 - yf / max(h, 1)
    # Fine turbulence for wisp edges (smaller scales = more detail)
    turb = multi_scale_noise(shape, [8, 16, 32, 64], [0.25, 0.3, 0.25, 0.2], seed + 308)
    fine = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 309)
    # Wisp tendrils: sine waves distorted by turbulence
    wisp1 = np.sin(xf * 0.06 + turb * 4.0 + yf * 0.02) * 0.5 + 0.5
    wisp2 = np.sin(xf * 0.04 - turb * 3.0 + yf * 0.03 + 1.5) * 0.5 + 0.5
    wisps = np.maximum(wisp1, wisp2)
    # Vertical fade: flames rise upward
    height = np.clip(yn * 1.2 + fine * 0.3, 0, 1)
    # Combine with gentle power curve (0.8, not 2.0)
    ghost = np.clip(wisps * height, 0, 1)
    ghost = np.power(np.clip(ghost, 0, 1), 0.8)
    return {"pattern_val": ghost.astype(np.float32), "R_range": -70.0, "M_range": 55.0, "CC": None}

def texture_flame_ball(shape, mask, seed, sm):
    """Radial burst / fireball - explosive center."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    yy, xx = y.astype(np.float32), x.astype(np.float32)
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    r = max(cy, cx) * 0.8
    n = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 309)
    n2 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 310)
    # Multiple smaller bursts instead of one big ball
    ball = np.clip(1.0 - dist / r + n * 0.35, 0, 1)
    ball = ball * (0.7 + n2 * 0.3)  # Break up the solid mass with fine turbulence
    ball = np.power(np.clip(ball, 0, 1), 0.8)
    cc = np.clip(16 * (1 - ball * 0.6), 0, 16).astype(np.uint8)
    return {"pattern_val": ball, "R_range": -140.0, "M_range": 120.0, "CC": cc}

def texture_flame_tribal_curves(shape, mask, seed, sm):
    """Tribal flame curves v2 — sharp knife-edge curves with fine turbulence.
    Multi-frequency sin composition + noise warp for intricate tribal tattoo look."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    yn = yf / max(h, 1) * np.pi * 6  # Higher freq (was 4)
    xn = xf / max(w, 1) * np.pi * 6
    # Multi-scale turbulence for organic warp
    n1 = multi_scale_noise(shape, [12, 24, 48], [0.25, 0.4, 0.35], seed + 310)
    n2 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 311)
    # Double-warped curves for intricacy
    curve1 = np.sin(yn + np.sin(xn * 1.2) * 0.8 + n1 * 2.0)
    curve2 = np.sin(xn * 0.8 + np.sin(yn * 1.5) * 0.6 + n2 * 1.5 + 1.0)
    # Sharp knife edges via abs-fold (tribal tattoo style)
    tribal = np.clip(1.0 - np.abs(curve1) * 1.8, 0, 1) + np.clip(1.0 - np.abs(curve2) * 2.0, 0, 1) * 0.6
    # Add fine grain detail
    tribal = np.clip(tribal + n2 * 0.08, 0, 1)
    return {"pattern_val": tribal.astype(np.float32), "R_range": -130.0, "M_range": 110.0, "CC": None}

def texture_flame_wild(shape, mask, seed, sm):
    """Chaotic multi-directional wildfire."""
    h, w = shape
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 311)
    n2 = multi_scale_noise(shape, [12, 28, 56], [0.3, 0.4, 0.3], seed + 312)
    wild = np.clip(np.abs(n1) * 0.85 + np.abs(n2) * 0.6 + 0.15, 0, 1)  # Stronger fire (was 0.7/0.5)
    cc = np.clip(16 * (1 - wild * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": wild, "R_range": -135.0, "M_range": 115.0, "CC": cc}

def texture_tribal_bands(shape, mask, seed, sm):
    """Thick horizontal tribal bands with sin modulation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1) * np.pi * 6
    xn = x.astype(np.float32) / max(w, 1) * np.pi * 4
    band = np.sin(yn + np.sin(xn * 2) * 0.6) * 0.5 + 0.5
    band = np.clip(np.abs(band - 0.5) * 2.2, 0, 1)
    return {"pattern_val": band, "R_range": 55.0, "M_range": -25.0, "CC": None}

def texture_tribal_scroll(shape, mask, seed, sm):
    """Scroll-like ornamental curves - gothic scroll."""
    h, w = shape
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 314)
    wave = np.sin((y * 25 + n * 4) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 65.0, "M_range": 45.0, "CC": 0}

def texture_tribal_knot_dense(shape, mask, seed, sm):
    """Denser celtic-style interwoven knot."""
    h, w = shape
    y, x = get_mgrid((h, w))
    y_n = y.astype(np.float32) / h * np.pi * 8
    x_n = x.astype(np.float32) / w * np.pi * 8
    b1 = np.sin(x_n + np.sin(y_n * 2.5) * 0.9)
    b2 = np.sin(y_n + np.sin(x_n * 2.5) * 0.9)
    weave = np.clip((np.abs(b1) + np.abs(b2) - 0.5) * 2, 0, 1)
    return {"pattern_val": weave.astype(np.float32), "R_range": 60.0, "M_range": -20.0, "CC": None}

def texture_tribal_meander(shape, mask, seed, sm):
    """Greek key v2 — dense continuous meander with proper right-angle labyrinth."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    # ~60 cells across canvas (was min 20px = ~100 max, but pattern was too big)
    cell = max(6, dim / 60.0)
    ly = (y % cell).astype(np.float32) / cell
    lx = (x % cell).astype(np.float32) / cell
    line_w = 0.08  # Line thickness as fraction of cell
    half = 0.5
    q = 0.25
    # Greek key structure: border + 3 internal arms
    border = ((ly < line_w) | (ly > 1-line_w) | (lx < line_w) | (lx > 1-line_w)).astype(np.float32)
    arm1 = ((np.abs(ly - q) < line_w) & (lx > q)).astype(np.float32)
    arm2 = ((np.abs(lx - (1-q)) < line_w) & (ly > q) & (ly < 1-q)).astype(np.float32)
    arm3 = ((np.abs(ly - (1-q)) < line_w) & (lx < 1-q)).astype(np.float32)
    arm4 = ((np.abs(lx - q) < line_w) & (ly > q) & (ly < half + line_w)).astype(np.float32)
    key = np.clip(border + arm1 + arm2 + arm3 + arm4, 0, 1)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2520) * 0.12 + 0.07
    key = np.clip(key + bg_fill, 0, 1)
    return {"pattern_val": key.astype(np.float32), "R_range": 75.0, "M_range": -40.0, "CC": None}

def texture_paisley_flow(shape, mask, seed, sm):
    """Paisley teardrop curved ornamental flow."""
    h, w = shape
    y = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w)
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 317)
    wave = np.sin((y * 20 + x * 15 + n * 3) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 68.0, "M_range": 48.0, "CC": 0}

def texture_wave_vertical(shape, mask, seed, sm):
    """Vertical wave bands - upright curtain."""
    h, w = shape
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w, 1) * np.pi * 10
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 318)
    wave = np.sin(xn + n * 2) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -80.0, "M_range": 70.0, "CC": None}

def texture_wave_diagonal(shape, mask, seed, sm):
    """Diagonal wave bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    diag = (y.astype(np.float32) + x.astype(np.float32)) / max(h + w, 1) * np.pi * 12
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 319)
    wave = np.sin(diag + n * 2) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -75.0, "M_range": 65.0, "CC": None}

def texture_wave_gentle(shape, mask, seed, sm):
    """Low-frequency soft waves."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1) * np.pi * 4
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 320)
    wave = np.sin(yn + n * 1.5) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -70.0, "M_range": 60.0, "CC": None}

def texture_wave_choppy(shape, mask, seed, sm):
    """High-frequency choppy waves."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yn = y.astype(np.float32) / max(h, 1) * np.pi * 20
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 321)
    wave = np.sin(yn + n * 3) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": -90.0, "M_range": 80.0, "CC": None}

def texture_chevron_bold(shape, mask, seed, sm):
    """Bold wide chevron stripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(40, min(h, w) // 12)
    v = (x.astype(np.float32) + (y.astype(np.float32) % period)) % period
    chev = (v < period // 2).astype(np.float32)
    return {"pattern_val": chev, "R_range": 75.0, "M_range": -45.0, "CC": None}

def texture_chevron_fine(shape, mask, seed, sm):
    """Finer chevron stripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(20, min(h, w) // 24)
    v = (x.astype(np.float32) + (y.astype(np.float32) % period)) % period
    chev = (v < period // 2).astype(np.float32)
    return {"pattern_val": chev, "R_range": 65.0, "M_range": -40.0, "CC": None}

def texture_aztec_steps(shape, mask, seed, sm):
    """Stepped Aztec-style geometric blocks."""
    h, w = shape
    y, x = get_mgrid((h, w))
    step = max(12, min(h, w) // 40)
    sy = (y // step).astype(np.int32) % 2
    sx = (x // step).astype(np.int32) % 2
    aztec = ((sy + sx) % 2).astype(np.float32)
    return {"pattern_val": aztec, "R_range": 68.0, "M_range": -38.0, "CC": None}

def texture_ripple_dense(shape, mask, seed, sm):
    """Denser concentric ripples."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    scale = max(h, w) / 8.0
    ripple = np.sin(dist / scale * np.pi * 2) * 0.5 + 0.5
    return {"pattern_val": ripple, "R_range": -70.0, "M_range": 55.0, "CC": None}

def texture_ripple_soft(shape, mask, seed, sm):
    """Softer broader ripples."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((y.astype(np.float32) - cy) ** 2 + (x.astype(np.float32) - cx) ** 2)
    scale = max(h, w) / 30.0  # ~30 ripple cycles (was /3 = only 3 cycles = huge rings)
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 328)
    ripple = np.sin(dist / scale * np.pi + n * 2.0) * 0.5 + 0.5
    return {"pattern_val": ripple, "R_range": -65.0, "M_range": 50.0, "CC": None}

def texture_pinstripe_vertical(shape, mask, seed, sm):
    """Vertical pinstripes v2 — anti-aliased with subtle background grain."""
    h, w = shape
    y, x = get_mgrid((h, w))
    xf = x.astype(np.float32)
    dim = min(h, w)
    period = max(10, dim // 40)
    line_w = max(1.5, period * 0.12)
    stripe = np.clip(1.0 - np.abs((xf % period) - period * 0.5) / line_w, 0, 1)
    # Background grain
    grain = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 50)
    # Boosted bg fill for coverage (racing_stripe, tropical_leaf)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 500) * 0.18 + 0.10
    pv = np.clip(stripe + grain * 0.04 + 0.02 + bg_fill, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -90.0, "M_range": 80.0, "CC": 0}

def texture_pinstripe_diagonal(shape, mask, seed, sm):
    """Diagonal pinstripes v2 — anti-aliased with background texture."""
    h, w = shape
    y, x = get_mgrid((h, w))
    d = (y.astype(np.float32) + x.astype(np.float32)) / 2
    dim = min(h, w)
    period = max(12, dim // 35)
    line_w = max(1.5, period * 0.1)
    stripe = np.clip(1.0 - np.abs((d % period) - period * 0.5) / line_w, 0, 1)
    grain = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 60)
    # Background surface grain for full coverage
    bg = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1860) * 0.12 + 0.08
    pv = np.clip(stripe + grain * 0.04 + bg, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -85.0, "M_range": 75.0, "CC": 0}

def texture_pinstripe_fine(shape, mask, seed, sm):
    """Very fine pinstripes v2 — dense with anti-aliased edges."""
    h, w = shape
    y, x = get_mgrid((h, w))
    xf = x.astype(np.float32)
    dim = min(h, w)
    period = max(6, dim // 80)
    line_w = max(1.0, period * 0.15)
    stripe = np.clip(1.0 - np.abs((xf % period) - period * 0.5) / line_w, 0, 1)
    grain = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 70)
    # Background surface grain for full coverage
    bg = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1870) * 0.12 + 0.07
    pv = np.clip(stripe + grain * 0.03 + bg, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -95.0, "M_range": 85.0, "CC": 0}

def texture_grating_heavy(shape, mask, seed, sm):
    """Heavy grating v2 — thick anti-aliased bars with rust texture between them."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    dim = min(h, w)
    period = max(12, dim // 40)
    bar_w = max(2, period * 0.25)
    # Anti-aliased bars
    bar = np.clip(1.0 - np.abs((yf % period) - period * 0.5) / bar_w, 0, 1)
    # Cross-bars (perpendicular, thinner)
    xf = x.astype(np.float32)
    xbar = np.clip(1.0 - np.abs((xf % (period * 3)) - period * 1.5) / (bar_w * 0.6), 0, 1) * 0.5
    # Surface texture between bars
    rust = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100)
    surface = np.clip(rust * 0.06 + 0.04, 0, 0.12)
    pv = np.clip(bar + xbar + surface, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -100.0, "M_range": 90.0, "CC": 0}

def texture_plasma_soft(shape, mask, seed, sm):
    """Softer plasma - subtle ghost energy."""
    h, w = shape
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.35, 0.4, 0.25], seed + 333)
    n2 = multi_scale_noise(shape, [8, 16, 32], [0.35, 0.4, 0.25], seed + 334)
    plasma = np.clip(np.abs(n1) * 0.6 + np.abs(n2) * 0.4, 0, 1)
    plasma = np.power(plasma, 1.3)
    return {"pattern_val": plasma, "R_range": -50.0, "M_range": 40.0, "CC": None}

def texture_plasma_fractal(shape, mask, seed, sm):
    """Deeply recursive high-frequency fractal noise."""
    h, w = shape
    # Much smaller tiles = higher frequency multi-scale noise
    n1 = multi_scale_noise(shape, [8, 16, 32, 64], [0.25, 0.35, 0.25, 0.15], seed + 335)
    n2 = multi_scale_noise(shape, [16, 32, 64, 128], [0.3, 0.3, 0.2, 0.2], seed + 336)
    
    # Recursive shatter effect
    frac = np.abs(np.sin(n1 * 10.0)) * 0.5 + np.abs(np.sin(n2 * 15.0)) * 0.5
    frac = np.power(frac, 1.5)
    return {"pattern_val": frac, "R_range": -80.0, "M_range": 70.0, "CC": None}

def texture_fractal_2(shape, mask, seed, sm):
    """High-frequency geometric crystal fracturing fractal (Variant 2)."""
    h, w = shape
    # Resolution-cap: compute at 2048 max (effectively full res)
    ds = max(1, min(h, w) // 2048)
    ch, cw = max(64, h // ds), max(64, w // ds)
    y, x = get_mgrid((ch, cw))
    sz = 16.0
    val = np.zeros((ch, cw), dtype=np.float32)
    for i in range(5):
        lx = (x % sz) / sz
        ly = (y % sz) / sz
        fold = np.abs(lx - 0.5) + np.abs(ly - 0.5)
        val += fold * (0.5 ** i)
        sz /= 2.0
    val = (np.sin(val * 20.0) * 0.5 + 0.5).astype(np.float32)
    if (ch, cw) != (h, w):
        val = cv2.resize(val, (w, h), interpolation=cv2.INTER_LINEAR)
    return {"pattern_val": val, "R_range": -75.0, "M_range": 65.0, "CC": None}

def texture_fractal_3(shape, mask, seed, sm):
    """Dense interwoven fractal network overlay (Variant 3)."""
    h, w = shape
    # extremely dense interwoven network using high frequency ridges
    n1 = multi_scale_noise(shape, [12, 24, 48, 96], [0.3, 0.3, 0.2, 0.2], seed + 400)
    n2 = multi_scale_noise(shape, [10, 20, 40, 80], [0.3, 0.3, 0.2, 0.2], seed + 401)
    
    # Ridged multi-fractal style
    ridge1 = 1.0 - np.abs(n1 * 2.0 - 1.0)
    ridge2 = 1.0 - np.abs(n2 * 2.0 - 1.0)
    
    network = np.clip(ridge1 * ridge2 * 2.5, 0, 1)
    return {"pattern_val": network, "R_range": -90.0, "M_range": 80.0, "CC": None}

def texture_stardust_2(shape, mask, seed, sm):
    """Supernova starburst — multiple scattered starbursts with fine rays and glitter."""
    h, w = shape
    rng = np.random.RandomState(seed + 200)
    # Resolution-cap: compute starbursts at 1024 max, upscale
    ds = max(1, min(h, w) // 1024)
    ch, cw = max(64, h // ds), max(64, w // ds)
    cy_g, cx_g = get_mgrid((ch, cw))
    burst = np.zeros((ch, cw), dtype=np.float32)

    # Multiple smaller starbursts scattered across canvas
    n_bursts = rng.randint(5, 9)
    for _ in range(n_bursts):
        cx = rng.randint(cw // 8, 7 * cw // 8)
        cy = rng.randint(ch // 8, 7 * ch // 8)
        radius = min(ch, cw) * rng.uniform(0.04, 0.10)
        dist = np.sqrt((cx_g - cx)**2 + (cy_g - cy)**2)
        core = np.clip(1.0 - dist / radius, 0, 1)
        angle = np.arctan2(cy_g - cy, cx_g - cx)
        n_rays = rng.randint(30, 60)
        rays = np.sin(angle * n_rays) * 0.5 + 0.5
        rays = rays * core * rng.uniform(0.4, 0.7)
        burst = np.maximum(burst, core * 0.5 + rays)

    # Upscale before adding pixel-level detail
    if (ch, cw) != (h, w):
        burst = cv2.resize(burst, (w, h), interpolation=cv2.INTER_LINEAR)

    # Dense fine glitter (at full resolution for crisp sparkle)
    glitter = rng.random((h, w)).astype(np.float32)
    stars = (glitter > 0.992).astype(np.float32)

    # Nebula background for full coverage
    nebula = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 201) * 0.15 + 0.08
    burst = np.clip(burst + stars + nebula, 0, 1)
    return {"pattern_val": burst.astype(np.float32), "R_range": -65.0, "M_range": 85.0, "CC": None}

def texture_biomechanical_2(shape, mask, seed, sm):
    """Procedural intricate organic-mechanical Giger style."""
    h, w = shape
    from scipy.spatial import cKDTree
    rng = np.random.RandomState(seed + 900)
    y, x = get_mgrid((h, w))
    
    # Density of cells
    cell_s = 25.0
    grid_y, grid_x = int(h / cell_s) + 2, int(w / cell_s) + 2
    cy, cx = np.mgrid[0:grid_y, 0:grid_x]
    pts_y = (cy * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    pts_x = (cx * cell_s + rng.rand(grid_y, grid_x) * cell_s).flatten()
    tree = cKDTree(np.column_stack((pts_y, pts_x)))
    
    coords = np.column_stack((y.flatten(), x.flatten()))
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(h, w).astype(np.float32)
    d2 = dists[:, 1].reshape(h, w).astype(np.float32)
    
    # Cell borders and centers
    edge = d2 - d1
    bones = np.clip(1.0 - d1 / (cell_s * 0.5), 0, 1)
    joints = np.where(edge < 1.5, 0.0, bones)
    
    # Mechanical tubes/wires winding through
    wires_n = multi_scale_noise(shape, [16, 32, 64], [0.4, 0.4, 0.2], seed + 901)
    tubes = np.abs(np.sin(wires_n * 20.0))
    tubes = np.power(tubes, 2.0) # sharp thin tubes
    
    mech = np.clip(joints * 0.6 + tubes * 0.8, 0, 1)
    return {"pattern_val": mech, "R_range": -85.0, "M_range": 75.0, "CC": None}

def texture_hologram_vertical(shape, mask, seed, sm):
    """Vertical scanline hologram style."""
    h, w = shape
    y, x = get_mgrid((h, w))
    period = max(4, h // 40)
    scan = np.sin(y.astype(np.float32) / period * np.pi * 2) * 0.5 + 0.5
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 338)
    scan = np.clip(scan + n * 0.2, 0, 1)
    return {"pattern_val": scan, "R_range": -60.0, "M_range": 50.0, "CC": None}

def texture_circuit_dense(shape, mask, seed, sm):
    """Denser circuit board traces."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(8, min(h, w) // 64)
    gx = (x.astype(np.int32) // cell) % 2
    gy = (y.astype(np.int32) // cell) % 2
    thin = ((x.astype(np.int32) % cell) < 2) | ((y.astype(np.int32) % cell) < 2)
    trace = ((gx | gy) & thin).astype(np.float32)
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 339)
    trace = np.clip(trace + n * 0.15, 0, 1)
    return {"pattern_val": trace, "R_range": -80.0, "M_range": 100.0, "CC": 0}

def texture_crosshatch_fine(shape, mask, seed, sm):
    """Crosshatch v2 — dense diagonal pen strokes with anti-aliased edges and pressure variation."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    dim = min(h, w)
    # ~80 crosshatch lines across (was fixed 12-41px period)
    period = max(6, dim / 80.0)
    line_w = max(1.5, period * 0.12)  # Scaled line width (was hardcoded 2px)
    # Diagonal lines in two directions
    d1 = (xf + yf) % period
    d2 = (xf - yf) % period
    # Anti-aliased: smooth falloff instead of binary
    hatch1 = np.clip(1.0 - np.abs(d1 - period * 0.5) / line_w, 0, 1)
    hatch2 = np.clip(1.0 - np.abs(d2 - period * 0.5) / line_w, 0, 1)
    # Pen pressure variation: lines get lighter/darker based on noise
    pressure = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 50)
    pressure_mod = np.clip(pressure * 0.3 + 0.7, 0.4, 1.0)
    hatch = np.clip(hatch1 * pressure_mod + hatch2 * pressure_mod * 0.8, 0, 1)
    return {"pattern_val": hatch.astype(np.float32), "R_range": 55.0, "M_range": -35.0, "CC": None}

def texture_houndstooth_bold(shape, mask, seed, sm):
    """Bolder houndstooth check."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(32, min(h, w) // 24)
    cy = (y // cell) % 2
    cx = (x // cell) % 2
    sy = (y % cell).astype(np.float32) / cell
    sx = (x % cell).astype(np.float32) / cell
    check = (cy ^ cx).astype(np.float32)
    tooth = ((sy < sx) & (sy < 0.6) & (sx < 0.6)) | ((sy > sx) & (sy > 0.4) & (sx > 0.4))
    pattern = np.clip(check + tooth.astype(np.float32), 0, 1)
    return {"pattern_val": pattern, "R_range": 72.0, "M_range": -42.0, "CC": None}

def texture_hex_honeycomb(shape, mask, seed, sm):
    """Honeycomb hex grid variant."""
    h, w = shape
    y, x = get_mgrid((h, w))
    size = max(14, min(h, w) // 80)
    row = (y // (size * 1.5)).astype(np.int32)
    cx = (x + (row % 2) * size) % (size * 2)
    cy = (y % (size * 1.5)).astype(np.float32)
    dx = np.abs(cx.astype(np.float32) - size)
    dy = cy - size * 0.75
    dist = np.sqrt(dx ** 2 + dy ** 2 * 1.2)
    edge = (np.abs(dist - size * 0.6) < 2).astype(np.float32)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2560) * 0.12 + 0.07
    edge = np.clip(edge + bg_fill, 0, 1)
    return {"pattern_val": edge, "R_range": -85.0, "M_range": 95.0, "CC": 0}

def texture_damascus_vertical(shape, mask, seed, sm):
    """Vertical damascus-style grain."""
    h, w = shape
    x = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w)
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 343)
    wave = np.sin((x * 30 + n * 3) * np.pi) * 0.5 + 0.5
    return {"pattern_val": wave, "R_range": 65.0, "M_range": 48.0, "CC": 0}

def texture_leopard_sparse(shape, mask, seed, sm):
    """Sparser leopard spots."""
    h, w = shape
    rng = np.random.RandomState(seed + 344)
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 345)
    spots = np.exp(-n ** 2 * 4)
    return {"pattern_val": spots, "R_range": 40.0, "M_range": -25.0, "CC": None}

def texture_lightning_soft(shape, mask, seed, sm):
    """Softer lightning branches."""
    h, w = shape
    n = multi_scale_noise(shape, [8, 16, 32], [0.35, 0.4, 0.25], seed + 346)
    y, x = get_mgrid((h, w))
    xn = x.astype(np.float32) / max(w, 1)
    branch = np.clip(np.abs(n) * 1.5 - 0.3 - xn * 0.2, 0, 1)
    # Background electric storm fill for coverage
    bg_storm = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 500)
    bg_storm = np.clip(bg_storm * 0.30 + 0.18, 0.05, 0.40)
    branch = np.clip(np.maximum(branch, bg_storm), 0, 1)
    return {"pattern_val": branch, "R_range": -110.0, "M_range": 120.0, "CC": 0}

def texture_turbine_swirl(shape, mask, seed, sm):
    """Turbine swirl variant - groovy spiral."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    yy, xx = y.astype(np.float32) - cy, x.astype(np.float32) - cx
    angle = np.arctan2(yy, xx)
    dist = np.sqrt(yy ** 2 + xx ** 2) / (max(cy, cx) + 1e-8)
    swirl = np.sin(angle * 5 + dist * 15) * 0.5 + 0.5
    return {"pattern_val": swirl, "R_range": -70.0, "M_range": 65.0, "CC": None}

def texture_stardust_fine(shape, mask, seed, sm):
    """Finer stardust scatter."""
    h, w = shape
    rng = np.random.RandomState(seed + 348)
    n = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 349)
    dust = np.clip(np.abs(n) - 0.5, 0, 1) * 2
    return {"pattern_val": dust, "R_range": -50.0, "M_range": 60.0, "CC": None}

def texture_cracked_ice_fine(shape, mask, seed, sm):
    """Finer cracked ice network."""
    h, w = shape
    n = multi_scale_noise(shape, [8, 16, 32, 64], [0.25, 0.3, 0.3, 0.15], seed + 350)
    cracks = np.exp(-n ** 2 * 10)
    return {"pattern_val": cracks, "R_range": -60.0, "M_range": 70.0, "CC": None}

def texture_snake_fine(shape, mask, seed, sm):
    """Finer snake skin scale pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 351)
    scale = max(6, min(h, w) // 60)
    row = (y // scale).astype(np.int32) % 2
    sx = (x + row * (scale // 2)) % scale
    sy = (y % scale).astype(np.float32)
    dist = np.sqrt((sx - scale / 2) ** 2 + (sy - scale / 2) ** 2)
    edge = (np.abs(dist - scale * 0.35) < 1.5).astype(np.float32) + n * 0.2
    return {"pattern_val": np.clip(edge, 0, 1), "R_range": -75.0, "M_range": 65.0, "CC": None}


# ══════════════════════════════════════════════════════════════════════════
# CLEARCOAT BLEND BASES - 10 extreme paint effects for the Blend Base dropdown
# These have DRAMATIC, unmissable color transforms designed for blending.
# ══════════════════════════════════════════════════════════════════════════

def paint_blend_arctic_freeze(paint, shape, mask, seed, pm, bb):
    """BLEND: Deep icy blue freeze - unmissable cold transformation."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    # Heavy desaturation + extreme blue push
    paint = paint * (1 - 0.65 * pm * mask[:,:,np.newaxis]) + gray * 0.65 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.20 * pm * mask[:,:,np.newaxis], 0, 1)  # darken base
    paint[:,:,0] = np.clip(paint[:,:,0] - 0.18 * pm * mask, 0, 1)  # kill red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.08 * pm * mask, 0, 1)  # slight green for ice
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.35 * pm * mask, 0, 1)  # massive blue tint
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_inferno(paint, shape, mask, seed, pm, bb):
    """BLEND: Hot ember red/orange - fiery transformation."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.50 * pm * mask[:,:,np.newaxis]) + gray * 0.50 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.15 * pm * mask[:,:,np.newaxis], 0, 1)  # darken
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.40 * pm * mask, 0, 1)  # massive red push
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.15 * pm * mask, 0, 1)  # orange component
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.25 * pm * mask, 0, 1)  # kill blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_toxic(paint, shape, mask, seed, pm, bb):
    """BLEND: Sickly neon green - toxic radioactive glow."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] - 0.15 * pm * mask, 0, 1)  # kill red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.40 * pm * mask, 0, 1)  # massive green
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.20 * pm * mask, 0, 1)  # kill blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_royal_purple(paint, shape, mask, seed, pm, bb):
    """BLEND: Deep royal purple - majestic violet transformation."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.50 * pm * mask[:,:,np.newaxis]) + gray * 0.50 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.18 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.22 * pm * mask, 0, 1)  # red for purple
    paint[:,:,1] = np.clip(paint[:,:,1] - 0.20 * pm * mask, 0, 1)  # kill green
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.35 * pm * mask, 0, 1)  # heavy blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_midnight(paint, shape, mask, seed, pm, bb):
    """BLEND: Near-black midnight - extreme darkening and desaturation."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.70 * pm * mask[:,:,np.newaxis]) + gray * 0.70 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.45 * pm * mask[:,:,np.newaxis], 0, 1)  # extreme darken
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05 * pm * mask, 0, 1)  # hint of blue
    paint = np.clip(paint + bb * 0.2 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_solar_gold(paint, shape, mask, seed, pm, bb):
    """BLEND: Rich warm gold - luxury golden transformation."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.45 * pm * mask[:,:,np.newaxis]) + gray * 0.45 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.30 * pm * mask, 0, 1)  # warm gold red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.18 * pm * mask, 0, 1)  # warm gold green
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.15 * pm * mask, 0, 1)  # kill cool blue
    paint = np.clip(paint + bb * 0.4 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_blood_wash(paint, shape, mask, seed, pm, bb):
    """BLEND: Deep blood red wash - dark dramatic crimson."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.55 * pm * mask[:,:,np.newaxis]) + gray * 0.55 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.25 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.45 * pm * mask, 0, 1)  # massive red
    paint[:,:,1] = np.clip(paint[:,:,1] - 0.20 * pm * mask, 0, 1)  # kill green
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.20 * pm * mask, 0, 1)  # kill blue
    paint = np.clip(paint + bb * 0.3 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_electric_cyan(paint, shape, mask, seed, pm, bb):
    """BLEND: Electric cyan shock - vivid teal-blue neon."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.50 * pm * mask[:,:,np.newaxis]) + gray * 0.50 * pm * mask[:,:,np.newaxis]
    paint[:,:,0] = np.clip(paint[:,:,0] - 0.20 * pm * mask, 0, 1)  # kill red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.35 * pm * mask, 0, 1)  # teal green
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.35 * pm * mask, 0, 1)  # teal blue
    paint = np.clip(paint + bb * 0.4 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_bronze_heat(paint, shape, mask, seed, pm, bb):
    """BLEND: Warm bronze patina - aged metallic warmth."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.40 * pm * mask[:,:,np.newaxis]) + gray * 0.40 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint - 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.25 * pm * mask, 0, 1)  # bronze red
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.12 * pm * mask, 0, 1)  # bronze warmth
    paint[:,:,2] = np.clip(paint[:,:,2] - 0.18 * pm * mask, 0, 1)  # kill cool
    paint = np.clip(paint + bb * 0.35 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_blend_ghost_silver(paint, shape, mask, seed, pm, bb):
    """BLEND: Ghostly silver bleach - pale ethereal washout."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    gray = paint.mean(axis=2, keepdims=True)
    # Near-total desaturation + brighten for ghostly silver
    paint = paint * (1 - 0.75 * pm * mask[:,:,np.newaxis]) + gray * 0.75 * pm * mask[:,:,np.newaxis]
    paint = np.clip(paint + 0.20 * pm * mask[:,:,np.newaxis], 0, 1)  # brighten (bleach)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.08 * pm * mask, 0, 1)  # cool tint
    paint = np.clip(paint + bb * 0.5 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

# Curated blend base entries - these go in BASE_REGISTRY alongside normal bases
BLEND_BASES = {
    "cc_arctic_freeze":  {"M": 200, "R": 20, "CC": 16, "paint_fn": paint_blend_arctic_freeze,  "desc": "BLEND: Deep icy blue freeze", "blend_only": True},
    "cc_inferno":        {"M": 150, "R": 40, "CC": 16, "paint_fn": paint_blend_inferno,         "desc": "BLEND: Hot ember red/orange fire", "blend_only": True},
    "cc_toxic":          {"M": 100, "R": 60, "CC": 16, "paint_fn": paint_blend_toxic,           "desc": "BLEND: Sickly neon green radioactive", "blend_only": True},
    "cc_royal_purple":   {"M": 120, "R": 30, "CC": 16, "paint_fn": paint_blend_royal_purple,    "desc": "BLEND: Deep royal purple majestic", "blend_only": True},
    "cc_midnight":       {"M": 5,   "R": 8,  "CC": 16, "paint_fn": paint_blend_midnight,        "desc": "BLEND: Near-black midnight void", "blend_only": True},
    "cc_solar_gold":     {"M": 230, "R": 25, "CC": 16, "paint_fn": paint_blend_solar_gold,      "desc": "BLEND: Rich warm luxury gold", "blend_only": True},
    "cc_blood_wash":     {"M": 80,  "R": 45, "CC": 16, "paint_fn": paint_blend_blood_wash,      "desc": "BLEND: Deep dramatic crimson wash", "blend_only": True},
    "cc_electric_cyan":  {"M": 180, "R": 15, "CC": 16, "paint_fn": paint_blend_electric_cyan,   "desc": "BLEND: Vivid teal-blue neon shock", "blend_only": True},
    "cc_bronze_heat":    {"M": 200, "R": 50, "CC": 16, "paint_fn": paint_blend_bronze_heat,     "desc": "BLEND: Warm bronze aged patina", "blend_only": True},
    "cc_ghost_silver":   {"M": 240, "R": 10, "CC": 16, "paint_fn": paint_blend_ghost_silver,    "desc": "BLEND: Ghostly pale silver bleach", "blend_only": True},
}


# --- BASE MATERIAL REGISTRY ---
# Organized by category, alphabetized within each section. 58 bases total.
BASE_REGISTRY = {
    # ── STANDARD FINISHES ──────────────────────────────────────────────
    "ceramic":          {"M": 10,  "R": 8,   "CC": 16, "paint_fn": paint_ceramic_gloss,   "desc": "Ultra-smooth ceramic coating deep wet shine — BASE-031 FIX: M=10 (dielectric nano-ceramic)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 30, "noise_R": 15},
    "gloss":            {"M": 0,   "R": 20,  "CC": 16, "paint_fn": paint_none,            "desc": "Standard glossy clearcoat"},
    "piano_black":      {"M": 5,   "R": 3,   "CC": 16, "paint_fn": paint_none,            "desc": "Deep piano black ultra-gloss mirror finish",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 10},
    "satin":            {"M": 0,   "R": 100, "CC": 50,  "paint_fn": paint_none,            "desc": "Soft satin semi-gloss clearcoat - CC=50 protective but not gloss — WEAK-014: noise variation",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_R": 20},
    "scuffed_satin":    {"M": 0,   "R": 160, "CC": 110, "paint_fn": paint_scuffed_satin_fn, "desc": "Scuffed satin — WEAK-015 FIX: rougher+duller than plain satin (R=160, CC=110 vs satin R=100, CC=50)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_R": 30, "noise_M": 12},
    "silk":             {"M": 30,  "R": 85,  "CC": 50,  "paint_fn": paint_silk_sheen,      "desc": "Silky smooth fabric-like sheen — BASE-028 FIX: CC=50 (silk sheen, not full gloss)"},
    "wet_look":         {"M": 10,  "R": 5,   "CC": 16, "paint_fn": paint_wet_gloss,       "desc": "Deep wet clearcoat show shine"},
    # ── METALLIC & FLAKE ──────────────────────────────────────────────
    "copper":           {"M": 190, "R": 55,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Warm oxidized copper metallic",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 35, "noise_R": 20},
    "diamond_coat":     {"M": 220, "R": 3,   "CC": 16, "paint_fn": paint_diamond_sparkle, "desc": "Diamond dust ultra-fine sparkle coat",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 25, "noise_R": 8},
    "electric_ice":     {"M": 240, "R": 10,  "CC": 16, "paint_fn": paint_electric_blue_tint, "desc": "Icy electric blue metallic - cold neon shimmer",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 8},
    "gunmetal":         {"M": 220, "R": 40,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Dark aggressive blue-gray metallic",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 30, "noise_R": 15},
    "metallic":         {"M": 200, "R": 50,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Standard metallic with visible flake",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 40, "noise_R": 18},
    "pearl":            {"M": 100, "R": 40,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Pearlescent iridescent sheen",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 12,
                         "base_spec_fn": spec_pearl_base},
    "pearlescent_white":{"M": 120, "R": 30,  "CC": 16, "paint_fn": paint_pearlescent_white_fn, "desc": "Tri-coat pearlescent white — HSV shimmer, tri-coat noise simulation",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 10,
                         "base_spec_fn": spec_pearlescent_white_base},
    "plasma_metal":     {"M": 230, "R": 18,  "CC": 16, "paint_fn": paint_plasma_shift,    "desc": "Electric plasma vein metallic — glowing blue/magenta FBM sin-vein structure",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.4, 0.35, 0.25], "noise_M": 55, "noise_R": 30},
    "rose_gold":        {"M": 240, "R": 12,  "CC": 16, "paint_fn": paint_rose_gold_tint,  "desc": "Pink-gold metallic warm shimmer",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.4, 0.4], "noise_M": 15, "noise_R": 10},
    "satin_gold":       {"M": 235, "R": 60,  "CC": 16, "paint_fn": paint_warm_metal,      "desc": "Satin gold metallic warm sheen — BASE-010 FIX: CC=16 (already fixed in canonical 2026-03-08)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 15, "noise_R": 18},
    # ── CHROME & MIRROR ───────────────────────────────────────────────
    "chrome":           {"M": 255, "R": 2,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Pure mirror chrome",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 20, "noise_R": 8},
    "dark_chrome":      {"M": 250, "R": 5,   "CC": 0,  "paint_fn": paint_smoked_darken,   "desc": "Smoked dark chrome black mirror",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.45, "perlin_lacunarity": 2.0, "noise_M": 35, "noise_R": 12},
    "mercury":          {"M": 255, "R": 3,   "CC": 0,  "paint_fn": paint_mercury_pool,    "desc": "Liquid mercury pooling mirror - desaturated chrome flow",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.5, "perlin_lacunarity": 1.8, "noise_M": 30, "noise_R": 10},
    # mirror_gold removed - M=255 G=2 identical to chrome; gold tint comes from paint color layer
    "satin_chrome":     {"M": 250, "R": 45,  "CC": 40, "paint_fn": paint_chrome_brighten, "desc": "BMW silky satin chrome — BASE-005 FIX: CC=40 (satin sheen)",
                         "noise_scales": [16, 32], "noise_weights": [0.4, 0.6], "noise_M": 20, "noise_R": 25},
    "surgical_steel":   {"M": 245, "R": 6,   "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Medical grade mirror surgical steel — BASE-006 FIX: CC=16 (sealed surgical steel)",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 15, "noise_R": 8},
    # ── CANDY & CLEARCOAT VARIANTS ────────────────────────────────────
    "candy":            {"M": 200, "R": 15,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Deep wet candy transparent glass",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 35, "noise_R": 15},
    "candy_chrome":     {"M": 250, "R": 15,  "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Candy-tinted chrome - deep color over mirror base",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 60, "noise_R": 15},
    # 2026-04-19 HEENAN HA10 — Animal engine identity audit. v2 inline entry
    # had R=160 (satin/scuffed range), but engine/base_registry_data.py L420
    # promised R=220 ("BMW Frozen / Porsche Chalk — true matte"). The v2
    # entry was the live one (audit shows R=160). Aligned to the curated
    # value: R=220 = true matte. CC bumped 80→210 to match the no-gloss
    # Frozen aesthetic. paint_fn kept as paint_none (the v2 default) — a
    # paint_fn upgrade to paint_f_clear_matte requires an import and is
    # deferred to next shift.
    "clear_matte":      {"M": 0,   "R": 220, "CC": 210, "paint_fn": paint_none,            "desc": "Precision matte clearcoat (BMW Frozen / Porsche Chalk style) — R=220 true matte roughness, CC=210 flat/no gloss (HA10: aligned to engine/base_registry_data.py)"},
    "smoked":           {"M": 15,  "R": 30,  "CC": 16, "paint_fn": paint_smoked_darken,   "desc": "Smoked tinted darkened clearcoat — BASE-043 FIX: R=30 (smoked haze roughness, not near-mirror)"},
    "spectraflame":     {"M": 245, "R": 15,  "CC": 16, "paint_fn": paint_spectraflame,    "desc": "Hot Wheels candy-over-chrome deep sparkle",
                         "noise_scales": [1, 2, 3], "noise_weights": [0.6, 0.25, 0.15], "noise_M": 80, "noise_R": 25},
    "tinted_clear":     {"M": 40,  "R": 8,   "CC": 16, "paint_fn": paint_tinted_clearcoat,"desc": "Deep tinted clearcoat over base color",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 12, "noise_R": 10},
    # ── GAP-FILL: COATED OVER METAL / DEEP GLASS ────────────────────────
    "hydrographic":     {"M": 240, "R": 5,   "CC": 16, "paint_fn": paint_chrome_brighten, "desc": "Mirror metal under maximum deep clearcoat - wet glass over chrome",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 20, "noise_R": 6},
    "jelly_pearl":      {"M": 120, "R": 15,  "CC": 16, "paint_fn": paint_fine_sparkle,    "desc": "Ultra-wet candy pearl - max depth, like looking through colored glass",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 18, "noise_R": 8},
    "orange_peel_gloss":{"M": 0,   "R": 160, "CC": 16, "paint_fn": paint_none,            "desc": "Orange-peel texture sealed under thick clearcoat",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.7, "perlin_lacunarity": 2.2, "noise_M": 0, "noise_R": 40},
    "tinted_lacquer":   {"M": 130, "R": 80,  "CC": 16, "paint_fn": paint_tinted_clearcoat,"desc": "Semi-metallic under thick lacquer pour - depth and warmth",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.4, "perlin_lacunarity": 1.8, "noise_M": 25, "noise_R": 20},
    # ── MATTE & FLAT ─────────────────────────────────────────────────
    "blackout":         {"M": 30,  "R": 220, "CC": 35,  "paint_fn": paint_none,            "desc": "Stealth murdered-out - thin protective matte coat (CC=35)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.3, "perlin_lacunarity": 2.0, "noise_M": 8, "noise_R": 15},
    "flat_black":       {"M": 0,   "R": 250, "CC": 220, "paint_fn": paint_none,            "desc": "Dead flat zero-sheen black — BASE-002 FIX: CC=220 (dead flat)"},
    "frozen":           {"M": 225, "R": 140, "CC": 100, "paint_fn": paint_subtle_flake,    "desc": "Frozen icy metallic — WEAK-017 FIX: distinct ice-crystal character vs frozen_matte — BASE-007 FIX: CC=100 (BMW Frozen protective matte clear)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.2, 0.45, 0.35], "noise_M": 40, "noise_R": 35},
    "frozen_matte":     {"M": 60,  "R": 210, "CC": 175, "paint_fn": paint_subtle_flake,    "desc": "BMW Individual frozen matte — WEAK-017 FIX: frosted uniform micro-roughness, no sparkle — BASE-008 FIX: CC=175 (frosted/flat)",
                         "noise_scales": [2, 3, 5], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 10, "noise_R": 20},
    "matte":            {"M": 0,   "R": 215, "CC": 215, "paint_fn": paint_matte_flat,      "desc": "Flat matte zero shine — WEAK-012: upgraded from paint_none + noise variation — BASE-001 FIX: CC=215 (flat matte clearcoat range)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.5, 0.3, 0.2], "noise_R": 25},
    "vantablack":       {"M": 0,   "R": 255, "CC": 240, "paint_fn": paint_none,            "desc": "Absolute void zero reflection — BASE-003 FIX: CC=240 (maximum degradation)",
                         "noise_scales": [1, 2, 4], "noise_weights": [0.5, 0.3, 0.2], "noise_M": 3, "noise_R": 5},
    "volcanic":         {"M": 80,  "R": 180, "CC": 70,  "paint_fn": paint_volcanic_ash,    "desc": "Volcanic ash coating - the ash layer IS the coat, heavily degraded (CC=70)"},
    # ── BRUSHED & DIRECTIONAL GRAIN ──────────────────────────────────
    "brushed_aluminum": {"M": 200, "R": 55,  "CC": 16, "paint_fn": paint_brushed_grain,   "desc": "Brushed natural aluminum directional grain — BASE-026 FIX: M=200 (real brushed aluminum); also CC=16 (sealed grain coat)",
                         "brush_grain": True, "noise_M": 15, "noise_R": 30},
    "brushed_titanium": {"M": 180, "R": 70,  "CC": 16, "paint_fn": paint_brushed_grain,   "desc": "Heavy directional titanium grain — CC fixed from 0 to 16",
                         "brush_grain": True, "noise_M": 25, "noise_R": 45},
    "satin_metal":      {"M": 235, "R": 65,  "CC": 55, "paint_fn": paint_subtle_flake,    "desc": "Subtle brushed satin metallic — BASE-027 FIX: CC=55 (satin character, not full gloss)",
                         "brush_grain": True, "noise_R": 20},
    # ── TACTICAL & INDUSTRIAL ────────────────────────────────────────
    "cerakote":         {"M": 40,  "R": 130, "CC": 160, "paint_fn": paint_tactical_flat,   "desc": "Mil-spec ceramic tactical coating - dead flat (CC=160) — BASE-018 FIX: CC=160 (mil-spec ceramic is dead flat, not near-gloss)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.4, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 20},
    "duracoat":         {"M": 25,  "R": 170, "CC": 150, "paint_fn": paint_tactical_flat,   "desc": "Tactical epoxy coat - air-dried flat finish (CC=150) — BASE-019 FIX: CC=150 (air-dry tactical epoxy is flat, not near-gloss)",
                         "perlin": True, "perlin_octaves": 2, "perlin_persistence": 0.45, "perlin_lacunarity": 2.0, "noise_M": 12, "noise_R": 25},
    "powder_coat":      {"M": 20,  "R": 155, "CC": 40,  "paint_fn": paint_none,            "desc": "Thick powder coat - cured protective surface, semi-matte (CC=40)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 15, "noise_R": 30},
    "rugged":           {"M": 50,  "R": 190, "CC": 175, "paint_fn": paint_tactical_flat,   "desc": "Rugged off-road coat - very rough protective layer (CC=175 dead flat) — BASE-020 FIX: CC=175 (rugged off-road coat is dead flat, not near-gloss)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 20, "noise_R": 35},
    # ── RAW METAL & WEATHERED ────────────────────────────────────────
    "anodized":         {"M": 170, "R": 80,  "CC": 140, "paint_fn": paint_subtle_flake,    "desc": "Gritty matte anodized aluminum — BASE-004 FIX: CC=140 (unsealed anodized)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 25},
    "burnt_headers":    {"M": 190, "R": 45,  "CC": 0,  "paint_fn": paint_burnt_metal,     "desc": "Exhaust header heat-treated gold-blue oxide",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 20},
    "galvanized":       {"M": 195, "R": 65,  "CC": 30,  "paint_fn": paint_galvanized_speckle, "desc": "Hot-dip galvanized zinc - the zinc IS the coat (CC=30 thin metallic coat)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 25, "noise_R": 30},
    "heat_treated":     {"M": 140, "R": 80,  "CC": 16, "paint_fn": paint_heat_tint,       "desc": "Heat-treated tool steel (gun barrel/blade) — muted straw/bronze/peacock oxide",
                         "noise_scales": [8, 16], "noise_weights": [0.4, 0.6], "noise_M": 18, "noise_R": 25},
    "patina_bronze":    {"M": 160, "R": 90,  "CC": 100, "paint_fn": paint_patina_green,    "desc": "Aged oxidized bronze with green patina — BASE-032 FIX: CC=100 (oxidized, no fresh clearcoat)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35},
    "patina_coat":      {"M": 100, "R": 150, "CC": 50, "paint_fn": paint_patina_green,    "desc": "Old weathered paint with fresh satin clearcoat sprayed over - protected patina",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 35},
    "battle_patina":    {"M": 140, "R": 150, "CC": 50, "paint_fn": paint_burnt_metal,     "desc": "Heavily worn metal base with thin protective satin coat - used racecar look — BASE-036 FIX: M=140 (worn+patina reduces metallic)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 40},
    "cerakote_gloss":   {"M": 100, "R": 70,  "CC": 16, "paint_fn": paint_tactical_flat,   "desc": "Cerakote gloss - polymer ceramic glossy sealed finish — BASE-023 FIX: M=100 (polymer ceramic, not near-chrome metallic)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 20},
    "raw_aluminum":     {"M": 200, "R": 30,  "CC": 100, "paint_fn": paint_raw_aluminum,    "desc": "Bare unfinished aluminum sheet metal — BASE-033 FIX: M=200 (real bare aluminum), CC=100 (no clearcoat on bare metal)",
                         "noise_scales": [16, 32], "noise_weights": [0.4, 0.6], "noise_M": 25, "noise_R": 25},
    "sandblasted":      {"M": 200, "R": 180, "CC": 155, "paint_fn": paint_none,            "desc": "Raw sandblasted metal rough texture — BASE-009 FIX: CC=155 (no clearcoat, stripped metal)",
                         "noise_scales": [2, 4, 8], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 20, "noise_R": 30},
    # titanium_raw removed - M=200 G=50 identical to metallic; differentiate via paint color
    # ── EXOTIC BASE FINISHES (RESEARCH-008) ──────────────────────────
    "chromaflair":      {"M": 210, "R": 12,  "CC": 18, "paint_fn": paint_chromaflair,      "desc": "ChromaFlair Light Shift — 3-angle color flip via multi-stop hue rotation",
                         "base_spec_fn": spec_chromaflair_base},
    "xirallic":         {"M": 170, "R": 20,  "CC": 18, "paint_fn": paint_xirallic,          "desc": "Xirallic Crystal Flake — large sparse alumina flakes with iron oxide blue-silver interference",
                         "base_spec_fn": spec_xirallic_base},
    "anodized_exotic":  {"M": 110, "R": 38,  "CC": 45, "paint_fn": paint_anodized_exotic,   "desc": "Anodized Exotic — dye-impregnated oxide layer, semi-gloss, subtle hex pore micro-texture",
                         "base_spec_fn": spec_anodized_exotic_base},
    # ── EXOTIC & COLOR-SHIFT ─────────────────────────────────────────
    "chameleon":        {"M": 160, "R": 25,  "CC": 16, "paint_fn": paint_cp_chameleon,  "desc": "Dual-tone chameleon color-shift driven by surface angle",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 1.8, "noise_M": 60, "noise_R": 35},
    "iridescent":       {"M": 200, "R": 20,  "CC": 16, "paint_fn": paint_iridescent_shift,"desc": "Rainbow angle-shift iridescent wrap — BASE-038 FIX: M=200 (iridescent wrap, not chrome-level)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "perlin_lacunarity": 2.0, "noise_M": 50, "noise_R": 25},
    # ── WRAP & COATING ───────────────────────────────────────────────
    "liquid_wrap":      {"M": 0,   "R": 80,  "CC": 50,  "paint_fn": paint_liquid_wrap_fn,  "desc": "Liquid rubber peel coat — WEAK-016 FIX: rubber/vinyl micro-texture character, distinct from satin_wrap",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_R": 18, "noise_M": 5},
    "primer":           {"M": 0,   "R": 200, "CC": 175, "paint_fn": paint_primer_flat,     "desc": "Raw primer - zero sheen, no clearcoat (CC=175) — BASE-021 FIX: CC=175 (raw primer has no clearcoat)"},
    "satin_wrap":       {"M": 0,   "R": 130, "CC": 60,  "paint_fn": paint_satin_wrap,      "desc": "Vinyl wrap satin surface - the film IS the coat layer (CC=60)"},
    # ── ORGANIC / PERLIN NOISE ───────────────────────────────────────
    "living_matte":     {"M": 0,   "R": 180, "CC": 160, "paint_fn": paint_none,            "desc": "Organic matte - natural organic matte surface (CC=160) — BASE-022 FIX: CC=160 (matte finish, not satin range)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "noise_M": 0, "noise_R": 30},
    "organic_metal":    {"M": 210, "R": 45,  "CC": 16, "paint_fn": paint_subtle_flake,    "desc": "Organic flowing metallic with Perlin noise terrain",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.5, "noise_M": 35, "noise_R": 20, "noise_CC": 8},
    "terrain_chrome":   {"M": 250, "R": 8,   "CC": 0,  "paint_fn": paint_chrome_brighten, "desc": "Chrome with Perlin terrain-like distortion in roughness",
                         "perlin": True, "perlin_octaves": 5, "perlin_persistence": 0.45, "noise_M": 0, "noise_R": 25},
    # ── WORN & DEGRADED CLEARCOAT (CC=81–255) ────────────────────────────────
    # The full 81-255 spectrum - progressive clearcoat breakdown.
    # Perfect second-layer candidates for the Dual Layer Base system.
    "track_worn":       {"M": 210, "R": 55,  "CC": 100, "paint_fn": paint_subtle_flake,   "desc": "Race-worn metallic - degraded clearcoat, battle-scarred (CC=100)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 25, "noise_R": 20, "noise_CC": 15},
    "sun_fade":         {"M": 60,  "R": 130, "CC": 120, "paint_fn": paint_none,            "desc": "UV sun-damaged paint - bleached, chalky, coat breaking down (CC=120)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.0, "noise_M": 0, "noise_R": 30, "noise_CC": 20},
    "acid_etch":        {"M": 100, "R": 110, "CC": 130, "paint_fn": paint_patina_green,    "desc": "Acid-rain etched surface - pitted with partial clearcoat failure (CC=130)",
                         "noise_scales": [16, 32, 64], "noise_weights": [0.4, 0.3, 0.3], "noise_M": 20, "noise_R": 25, "noise_CC": 25},
    "oxidized":         {"M": 180, "R": 70,  "CC": 160, "paint_fn": paint_burnt_metal,     "desc": "Oxidized metallic - rust bloom, clearcoat near-destroyed (CC=160)",
                         "noise_scales": [8, 16, 32], "noise_weights": [0.3, 0.4, 0.3], "noise_M": 30, "noise_R": 35, "noise_CC": 30},
    "chalky_base":      {"M": 10,  "R": 195, "CC": 180, "paint_fn": paint_primer_flat,     "desc": "Chalk-oxidized paint - heavy flat haze, nearly no coat left (CC=180)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.65, "perlin_lacunarity": 2.0, "noise_M": 5, "noise_R": 35, "noise_CC": 30},
    "barn_find":        {"M": 80,  "R": 160, "CC": 210, "paint_fn": paint_primer_flat,     "desc": "Barn-find condition - decades of clearcoat breakdown, deep chalky flat (CC=210)",
                         "perlin": True, "perlin_octaves": 4, "perlin_persistence": 0.7, "perlin_lacunarity": 1.8, "noise_M": 10, "noise_R": 40, "noise_CC": 35},
    "crumbling_clear":  {"M": 30,  "R": 180, "CC": 235, "paint_fn": paint_volcanic_ash,    "desc": "Peeling, crumbling clearcoat - paint underneath showing through (CC=235)",
                         "perlin": True, "perlin_octaves": 3, "perlin_persistence": 0.6, "perlin_lacunarity": 2.2, "noise_M": 8, "noise_R": 30, "noise_CC": 35},
    "destroyed_coat":   {"M": 0,   "R": 210, "CC": 255, "paint_fn": paint_none,            "desc": "Completely destroyed clearcoat - maximum degradation, pure chalk-rough (CC=255)"},
}
# Register clearcoat blend bases into main registry
BASE_REGISTRY.update(BLEND_BASES)

# ================================================================
# FACTORY base_spec_fn FUNCTIONS — generic texture generators
# Assigned in bulk to bases that lack dedicated base_spec_fn.
# Each returns (M_arr, R_arr) or (M_arr, R_arr, CC_arr).
# Rules: R >= 15 for non-chrome (M < 240). CC >= 16 always (chrome CC=0 OK).
# ================================================================

def _spec_chrome_mirror(shape, seed, sm, base_m, base_r):
    """Chrome/mirror bases: micro-grain metallic noise, near-zero roughness variation.
    Chrome has CC=0, so no CC array returned."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Very subtle metallic grain (M +/- 3)
    m_noise = multi_scale_noise(sh, [8, 16, 32], [0.5, 0.3, 0.2], seed + 8001)
    M_arr = np.clip(float(base_m) + (m_noise - 0.5) * 6.0 * sm, 0, 255).astype(np.float32)
    # Tiny roughness variation (R +/- 2)
    r_noise = multi_scale_noise(sh, [8, 16, 32], [0.5, 0.3, 0.2], seed + 8002)
    R_arr = np.clip(float(base_r) + (r_noise - 0.5) * 4.0 * sm, 0, 255).astype(np.float32)
    # Per-pixel GGX floor: R>=15 wherever M<240 (noise may push M below chrome threshold)
    R_arr = np.where(M_arr < 240, np.maximum(R_arr, 15), R_arr)
    return M_arr, R_arr


def _spec_metallic_flake(shape, seed, sm, base_m, base_r):
    """Metallic/flake/candy bases: sparkle noise in M, micro-variation in R.
    CC stays at base value (returned as flat array)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Metallic flake sparkle (M +/- 20, fine-grained)
    m_flake = multi_scale_noise(sh, [8, 16, 32, 64], [0.4, 0.3, 0.2, 0.1], seed + 8010)
    M_arr = np.clip(float(base_m) + (m_flake - 0.5) * 40.0 * sm, 0, 255).astype(np.float32)
    # Roughness micro-variation (R +/- 10)
    r_noise = multi_scale_noise(sh, [8, 16, 32], [0.3, 0.4, 0.3], seed + 8011)
    R_arr = np.clip(float(base_r) + (r_noise - 0.5) * 20.0 * sm, 15, 255).astype(np.float32)
    return M_arr, R_arr


def _spec_matte_rough(shape, seed, sm, base_m, base_r):
    """Matte/rough/flat bases: surface grain texture in R, CC unevenness.
    Returns (M, R, CC) with clearcoat variation."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Minimal M variation (+/- 5)
    m_noise = multi_scale_noise(sh, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8020)
    M_arr = np.clip(float(base_m) + (m_noise - 0.5) * 10.0 * sm, 0, 255).astype(np.float32)
    # Surface grain texture (R +/- 25)
    r_grain = multi_scale_noise(sh, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 8021)
    R_arr = np.clip(float(base_r) + (r_grain - 0.5) * 50.0 * sm, 15, 255).astype(np.float32)
    # CC unevenness (+/- 15) — matte bases typically have CC 80-200, center at 120
    cc_noise = multi_scale_noise(sh, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8022)
    CC_arr = np.clip(120.0 + (cc_noise - 0.5) * 30.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def _spec_weathered(shape, seed, sm, base_m, base_r):
    """Weathered/damaged bases: large-scale clearcoat breakdown, high R variation.
    Returns (M, R, CC) with significant damage patches."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Metallic showing through where clearcoat is gone (+/- 25)
    # Fine damage patches — scales 16-64 = 32-128px features at 2048
    m_damage = multi_scale_noise(sh, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8030)
    M_arr = np.clip(float(base_m) + (m_damage - 0.5) * 50.0 * sm, 0, 255).astype(np.float32)
    # Fine grain roughness damage
    r_damage = multi_scale_noise(sh, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 8031)
    R_arr = np.clip(float(base_r) + (r_damage - 0.5) * 80.0 * sm, 15, 255).astype(np.float32)
    # Medium clearcoat breakdown patches
    cc_breakdown = multi_scale_noise(sh, [16, 32, 64, 128], [0.15, 0.25, 0.35, 0.25], seed + 8032)
    CC_arr = np.clip(180.0 + (cc_breakdown - 0.5) * 60.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def _spec_standard_gloss(shape, seed, sm, base_m, base_r):
    """Standard gloss bases: subtle noise on all channels.
    Returns (M, R, CC) with gentle variation."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Subtle M variation (+/- 8)
    m_noise = multi_scale_noise(sh, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8040)
    M_arr = np.clip(float(base_m) + (m_noise - 0.5) * 16.0 * sm, 0, 255).astype(np.float32)
    # R variation (+/- 10)
    r_noise = multi_scale_noise(sh, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8041)
    R_arr = np.clip(float(base_r) + (r_noise - 0.5) * 20.0 * sm, 15, 255).astype(np.float32)
    # CC variation (+/- 5) — standard gloss bases typically CC=16-50, center at 20
    cc_noise = multi_scale_noise(sh, [8, 16, 32], [0.3, 0.4, 0.3], seed + 8042)
    CC_arr = np.clip(20.0 + (cc_noise - 0.5) * 10.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def _spec_foundation_flat(shape, seed, sm, base_m, base_r):
    """Foundation bases: TRULY flat spec. 2026-04-21 painter fix:
    previous form added `multi_scale_noise * 4.0` (±2 per channel).
    Painters saw that micro-modulation as texture/speckle on the spec
    map. A Foundation Base is meant to be absolutely plain — the
    painter's chosen colour is the only variable; the material look
    is the only thing the Foundation contributes, and it does so
    through the flat M/R constants, not through per-pixel noise."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # R floor: chrome (M >= 240) can have R < 15; every other foundation
    # enforces R >= 15 so it doesn't render as impossible-looking
    # super-smooth non-metallic.
    base_r_floored = float(base_r) if float(base_m) >= 240 else max(float(base_r), 15.0)
    M_arr = np.full((h, w), float(base_m), dtype=np.float32)
    R_arr = np.full((h, w), base_r_floored, dtype=np.float32)
    return M_arr, R_arr


def _mk_flat_foundation_decal_spec(fid):
    """Build a 4-arg (shape, mask, seed, sm) decal-spec callable that
    returns a flat 4-channel uint8 spec using the foundation's own
    M/R/CC values from BASE_REGISTRY. Honors the Foundation Base
    flat-spec contract (no per-pixel texture, no paint recoloring,
    no variance on mask/seed/sm).

    2026-04-22 HEENAN FAMILY overnight iter 3 landed this as a local
    closure inside build_multi_zone's decal branch. Iter 5 hoisted
    it to module level so behavioral tests can import and exercise
    it directly, and so any future edit that swaps out the shim is
    source-level visible.

    R-floor matches ``_spec_foundation_flat`` (non-chrome foundations
    get R >= 15 so they don't render as impossible-looking
    super-smooth non-metallic)."""
    _fb = BASE_REGISTRY.get(fid) or {}
    _m = int(_fb.get("M", 0))
    _r_raw = int(_fb.get("R", 50))
    _cc = int(_fb.get("CC", 16))
    _r = _r_raw if _m >= 240 else max(_r_raw, 15)

    def _fn(shape, mask, seed, sm):
        h, w = shape[:2] if len(shape) > 2 else shape
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        spec[:, :, 0] = _m
        spec[:, :, 1] = _r
        spec[:, :, 2] = _cc
        spec[:, :, 3] = 255
        return spec
    return _fn


def _mk_flat_legacy_decal_spec(M, R, CC):
    """Build a 4-arg ``(shape, mask, seed, sm)`` decal-spec callable that
    returns a flat 4-channel uint8 spec using the supplied M/R/CC values.

    2026-04-23 HEENAN FAMILY 6h Alpha-hardening Iter 3 landed this as a
    silent-no-op fix for the DECAL_SPEC_MAP dispatch site. Behavioral
    probe (tests/test_regression_decal_spec_map_4arg_dispatch_safety.py)
    confirmed that 16 of 19 non-``f_`` entries in DECAL_SPEC_MAP were
    silently TypeError'ing because ``engine.spec_paint`` re-exports the
    paint_v2 5-arg signatures over the original 4-arg ones for
    ``spec_gloss``, ``spec_matte``, ``spec_satin``, ``spec_satin_metal``,
    ``spec_brushed_titanium``, ``spec_anodized``, ``spec_frozen``. The
    engine's outer try/except at the dispatch site swallowed the
    TypeError and the painter's decal area simply got NO spec applied.

    Painter-impact note: any saved preset / season-shared / fleet
    payload with ``specFinish`` in {gloss, matte, satin, satin_metal,
    clear_matte, eggshell, flat_black, primer, semi_gloss, silk,
    wet_look, scuffed_satin, chalky_base, living_matte, ceramic,
    piano_black} previously rendered with NO decal-area spec. After
    this fix those decal areas render with a FLAT spec matching the
    finish's canonical M/R/CC. New picker assignments are filtered to
    ``f_*`` already, so this affects only legacy data — strict
    improvement, no painter is "losing" anything they had.
    """
    _m = int(M); _r = int(R); _cc = int(CC)
    def _fn(shape, mask, seed, sm):
        h, w = shape[:2] if len(shape) > 2 else shape
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        spec[:, :, 0] = _m
        spec[:, :, 1] = _r
        spec[:, :, 2] = _cc
        spec[:, :, 3] = 255
        return spec
    return _fn


# ================================================================
# MISSING FOUNDATION BASES — f_* entries that factory spec_fn targets need
# These are simple paint_none foundations with appropriate M/R/CC values.
# ================================================================

# 2026-04-21 painter fix: every f_* Foundation Base is FLAT. No noise_*,
# no perlin, no noise_scales/weights. A Foundation Base is a pure material
# property — constant M, R, CC everywhere. Painter-facing rule: the
# Foundation Base NEVER modifies the painter's chosen colour and NEVER
# adds texture to the spec map; the material LOOK is the flat M/R/CC
# numbers doing their job. Visible grain / weave / flake / wrinkle /
# patina belongs in a Pattern or Spec Pattern Overlay, NOT here.
_FACTORY_FOUNDATION_BASES = {
    # METALLIC_FLAKE foundations
    "f_candy":          {"M": 200, "R": 20,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation candy - transparent glass over metallic base, flat"},
    "f_electroplate":   {"M": 245, "R": 8,   "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation electroplate - electroplated metal coating, flat"},
    "f_pvd_coating":    {"M": 230, "R": 15,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation PVD coating - physical vapor deposition metallic, flat"},
    "f_vapor_deposit":  {"M": 240, "R": 10,  "CC": 16,  "paint_fn": paint_none,  "desc": "Foundation vapor deposit - thin-film vacuum deposition, flat"},
    # MATTE_ROUGH foundations
    "f_bead_blast":     {"M": 180, "R": 160, "CC": 140, "paint_fn": paint_none,  "desc": "Foundation bead blast - glass bead blasted metal surface, flat"},
    "f_matte":          {"M": 0,   "R": 210, "CC": 180, "paint_fn": paint_none,  "desc": "Foundation matte - dead flat matte finish, flat"},
    "f_sand_cast":      {"M": 150, "R": 140, "CC": 120, "paint_fn": paint_none,  "desc": "Foundation sand cast - rough sand casting material, flat (add a rough Spec Pattern for cast grain)"},
    "f_shot_peen":      {"M": 190, "R": 130, "CC": 110, "paint_fn": paint_none,  "desc": "Foundation shot peen - dimpled peened metal, flat (add a dimple Spec Pattern for visible peen)"},
    "f_wrinkle_coat":   {"M": 10,  "R": 170, "CC": 150, "paint_fn": paint_none,  "desc": "Foundation wrinkle coat - wrinkle-textured powder coating, flat"},
    # WEATHERED foundations
    "f_galvanized":     {"M": 195, "R": 65,  "CC": 30,  "paint_fn": paint_none,  "desc": "Foundation galvanized - hot-dip zinc coating, flat"},
    "f_hot_dip":        {"M": 190, "R": 70,  "CC": 35,  "paint_fn": paint_none,  "desc": "Foundation hot dip - hot-dip galvanized zinc material, flat"},
    "f_mill_scale":     {"M": 120, "R": 110, "CC": 130, "paint_fn": paint_none,  "desc": "Foundation mill scale - iron oxide scale material, flat"},
    "f_patina":         {"M": 80,  "R": 120, "CC": 140, "paint_fn": paint_none,  "desc": "Foundation patina - oxidation patina material, flat (add a weathering Spec Pattern for corrosion)"},
    "f_thermal_spray":  {"M": 160, "R": 100, "CC": 90,  "paint_fn": paint_none,  "desc": "Foundation thermal spray - plasma-sprayed metal material, flat"},
    "f_weathering_steel":{"M": 100, "R": 130, "CC": 160, "paint_fn": paint_none, "desc": "Foundation weathering steel - Cor-Ten material, flat"},
}

for _fk, _fv in _FACTORY_FOUNDATION_BASES.items():
    if _fk not in BASE_REGISTRY:
        BASE_REGISTRY[_fk] = _fv


# WEAK-018 FIX: Wire paint_jelly_pearl_v2 into BASE_REGISTRY pearl entry.
# Must run after BASE_REGISTRY is built. Uses same _adapt_bb wrapper pattern as FINISH_REGISTRY.
try:
    from engine.paint_v2.candy_special import paint_jelly_pearl_v2 as _pjpv2
    import numpy as _np_weak018
    def _adapt_bb_base(fn):
        """Wrap v2 paint fn to handle scalar bb for BASE_REGISTRY callers."""
        def _wrapped(paint, shape, mask, seed, pm, bb):
            bb_val = bb
            try:
                if _np_weak018.isscalar(bb):
                    h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                    bb_val = _np_weak018.full((int(h), int(w)), float(bb), dtype=_np_weak018.float32)
                elif hasattr(bb, "ndim") and bb.ndim == 0:
                    h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                    bb_val = _np_weak018.full((int(h), int(w)), float(bb), dtype=_np_weak018.float32)
            except Exception:
                bb_val = bb
            return fn(paint, shape, mask, seed, pm, bb_val)
        return _wrapped
    BASE_REGISTRY["pearl"]["paint_fn"] = _adapt_bb_base(_pjpv2)
    print("[WEAK-018 FIX] pearl paint_fn wired to paint_jelly_pearl_v2 (HSV shimmer, platelet particles)")
except Exception as _weak018_exc:
    print(f"[WEAK-018 FIX] pearl v2 wire-in skipped: {_weak018_exc}")

# ================================================================
# BATCH 1: Dedicated texture functions for broken pattern aliases
# ================================================================

def texture_matrix_rain(shape, mask, seed, sm):
    """Matrix rain v3 — dense columnar streams with head glow, character blocks, and CRT scanlines."""
    h, w = shape
    rng = np.random.RandomState(seed + 7001)
    dim = min(h, w)
    pattern = np.zeros((h, w), dtype=np.float32)
    # Dense columns: ~1 every 5-8px across canvas
    col_w = max(4, dim // 300)
    n_cols = w // col_w
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    for i in range(n_cols):
        cx = int(i * col_w + rng.randint(0, max(1, col_w)))
        if cx >= w: continue
        cw = max(2, col_w - 1)
        # Multiple streams per column for density
        n_streams = rng.randint(1, 4)
        for _ in range(n_streams):
            start = rng.randint(0, h)
            length = rng.randint(h // 4, h)
            brightness = rng.uniform(0.5, 1.0)
            dist_from_head = (yf - start) % h
            # Stream body (fading down from head)
            stream = np.clip(1.0 - dist_from_head / max(length, 1), 0, 1) * brightness
            # Head glow (bright leading character)
            head = np.exp(-(dist_from_head / max(length * 0.03, 1))**2) * 0.5
            # Character blocks (random on/off within stream)
            char_h = max(2, dim // 400)
            n_chars = h // char_h + 1
            chars = rng.randint(0, 3, n_chars)
            char_pattern = np.repeat(chars, char_h)[:h].reshape(-1, 1).astype(np.float32) / 2.0
            col_val = stream * (0.35 + char_pattern * 0.65) + head
            x0 = max(0, cx)
            x1 = min(w, cx + cw)
            if x1 > x0:
                pattern[:, x0:x1] = np.maximum(pattern[:, x0:x1],
                    np.broadcast_to(col_val, (h, x1 - x0)))
    # CRT scanline overlay
    scanlines = (np.sin(yf * np.pi * 0.25) ** 2 * 0.08 + 0.92)
    pattern = np.clip(pattern * scanlines, 0, 1)
    return {"pattern_val": pattern.astype(np.float32), "R_range": -100.0, "M_range": 140.0, "CC": 0}

def texture_giraffe(shape, mask, seed, sm):
    """Giraffe spots - large irregular Voronoi polygon patches with thin borders."""
    h, w = shape
    from scipy.spatial import cKDTree
    rng = np.random.RandomState(seed + 7002)
    cell_s = 50.0  # Large cells (40-60px range)
    grid_y = int(h / cell_s) + 2
    grid_x = int(w / cell_s) + 2
    cy_g, cx_g = np.mgrid[0:grid_y, 0:grid_x]
    pts_y = (cy_g * cell_s + rng.rand(grid_y, grid_x) * cell_s * 0.8).flatten()
    pts_x = (cx_g * cell_s + rng.rand(grid_y, grid_x) * cell_s * 0.8).flatten()
    points = np.column_stack((pts_y, pts_x))
    tree = cKDTree(points)
    y, x = get_mgrid((h, w))
    coords = np.column_stack((y.flatten().astype(np.float32),
                               x.flatten().astype(np.float32)))
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(h, w).astype(np.float32)
    d2 = dists[:, 1].reshape(h, w).astype(np.float32)
    edge = d2 - d1
    idx = dists[:, 0].reshape(h, w).astype(np.int32) % len(points)  # Cell ID approximation
    # Per-patch tonal variation (each giraffe spot slightly different brightness)
    cell_tone = rng.uniform(0.5, 0.95, len(points)).astype(np.float32)
    patch_shade = cell_tone[idx.ravel()].reshape(h, w)
    # Smooth border (anti-aliased)
    border = np.clip(edge / 4.0, 0, 1)
    # Spots with internal texture + dark borders
    spot_noise = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 7003) * 0.06
    pv = np.clip(patch_shade * border + spot_noise, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": 55.0, "M_range": -65.0, "CC": 0}

def texture_checkered_flag(shape, mask, seed, sm):
    """Checkered flag - clean alternating chess-board squares."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = 25  # ~25px squares
    row = (y // cell).astype(np.int32) % 2
    col = (x // cell).astype(np.int32) % 2
    pattern = (row ^ col).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -50.0, "CC": 0}

def texture_zebra_stripe(shape, mask, seed, sm):
    """Zebra stripe - organic wavy horizontal stripes with noise distortion."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Use noise to wobble stripe boundaries
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7004)
    stripe_freq = 0.08  # ~12px stripe width
    warped_y = y.astype(np.float32) + n * 25.0  # organic wobble
    wave = np.sin(warped_y * stripe_freq * np.pi * 2)
    # Sharp threshold for bold stripes, slight variation for broken edges
    n2 = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 7005)
    threshold = 0.0 + n2 * 0.15
    pattern = (wave > threshold).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 70.0, "M_range": -60.0, "CC": 0}

def texture_fingerprint(shape, mask, seed, sm):
    """Fingerprint - concentric swirling ridges from center."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cy, cx = h / 2.0, w / 2.0
    dy = (y.astype(np.float32) - cy)
    dx = (x.astype(np.float32) - cx)
    angle = np.arctan2(dy, dx)
    dist = np.sqrt(dy ** 2 + dx ** 2)
    # Angular perturbation via noise for swirl effect
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7006)
    # Spiral: ridges = sin(distance + angle_perturbation)
    ridge_freq = 0.35  # ~3px ridge spacing
    swirl_strength = 3.0
    spiral = np.sin((dist * ridge_freq + angle * swirl_strength + n * 4.0) * np.pi)
    ridges = (np.abs(spiral) < 0.3).astype(np.float32)
    # Skin texture background for full coverage
    skin_bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1750) * 0.13 + 0.08
    ridges = np.clip(ridges + skin_bg, 0, 1)
    return {"pattern_val": ridges, "R_range": 80.0, "M_range": -35.0, "CC": None}

def texture_data_stream(shape, mask, seed, sm):
    """Data stream - flowing horizontal data packet bands with digital blocks."""
    h, w = shape
    rng = np.random.RandomState(seed + 7007)
    pattern = np.zeros((h, w), dtype=np.float32)
    # Create horizontal bands of data at various y positions
    n_bands = max(10, h // 20)
    for _ in range(n_bands):
        band_y = rng.randint(0, h)
        band_h = rng.randint(3, 8)
        y_lo = max(0, band_y)
        y_hi = min(h, band_y + band_h)
        if y_hi <= y_lo:
            continue
        # Within each band, place blocks (packets) of varying width
        n_packets = rng.randint(5, w // 10)
        x_pos = 0
        for _ in range(n_packets):
            gap = rng.randint(2, 15)
            pkt_w = rng.randint(4, 30)
            x_pos += gap
            if x_pos >= w:
                break
            x_end = min(w, x_pos + pkt_w)
            brightness = rng.uniform(0.5, 1.0)
            pattern[y_lo:y_hi, x_pos:x_end] = brightness
            x_pos = x_end
    # Background digital noise (covers empty space)
    bg_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7008)
    bg = np.clip(bg_noise * 0.06 + 0.03, 0, 0.1)
    # Faint horizontal scan lines across entire canvas
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)
    scan = (np.sin(yf * np.pi * 0.3) ** 2 * 0.04)
    pattern = np.clip(pattern + bg + np.broadcast_to(scan, (h, w)), 0, 1)
    return {"pattern_val": pattern.astype(np.float32), "R_range": -90.0, "M_range": 120.0, "CC": 0}

def texture_chainlink(shape, mask, seed, sm):
    """Chainlink v2 — anti-aliased diamond mesh with shadow depth between wires."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    dim = min(h, w)
    cell = max(16, dim // 60.0)
    wire_w = max(1.5, cell * 0.08)
    # Anti-aliased diagonal wires
    d1 = (yf + xf) % cell
    d2 = (yf - xf + 10000) % cell
    wire1 = np.clip(1.0 - np.abs(d1 - cell * 0.5) / wire_w, 0, 1)
    wire2 = np.clip(1.0 - np.abs(d2 - cell * 0.5) / wire_w, 0, 1)
    wires = np.clip(wire1 + wire2, 0, 1)
    # Wire glow (wider, dimmer)
    glow_w = wire_w * 3
    g1 = np.clip(1.0 - np.abs(d1 - cell * 0.5) / glow_w, 0, 1) * 0.1
    g2 = np.clip(1.0 - np.abs(d2 - cell * 0.5) / glow_w, 0, 1) * 0.1
    # Shadow/depth between wires
    depth = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 50) * 0.05 + 0.03
    pv = np.clip(wires + g1 + g2 + depth, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": -80.0, "M_range": 100.0, "CC": 0}

def texture_pentagram_star(shape, mask, seed, sm):
    """Pentagram star - tiled five-pointed stars in a grid."""
    h, w = shape
    rng = np.random.RandomState(seed + 7009)
    y, x = get_mgrid((h, w))
    cell = max(24, min(h, w) // 55)  # ~55 stars across canvas (was fixed 60px)
    pattern = np.zeros((h, w), dtype=np.float32)
    # For each tile, draw a 5-pointed star using angular math
    ty = (y % cell).astype(np.float32) - cell / 2.0
    tx = (x % cell).astype(np.float32) - cell / 2.0
    angle = np.arctan2(ty, tx)
    dist = np.sqrt(ty ** 2 + tx ** 2)
    # Star shape: radius oscillates 5 times around the circle
    # r(theta) = outer where cos(5*theta/2) peaks, inner otherwise
    outer_r = cell * 0.42
    inner_r = cell * 0.18
    # 5-pointed star equation
    star_angle = np.abs(((angle / (2 * np.pi) * 5) % 1.0) - 0.5) * 2.0  # 0-1 sawtooth
    star_r = inner_r + (outer_r - inner_r) * (1.0 - star_angle)
    inside = (dist < star_r).astype(np.float32)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2540) * 0.12 + 0.07
    inside = np.clip(inside + bg_fill, 0, 1)
    return {"pattern_val": inside, "R_range": 70.0, "M_range": -50.0, "CC": 0}

def texture_biohazard_symbol(shape, mask, seed, sm):
    """Biohazard trefoil symbol - three overlapping crescents tiled in a grid."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(30, min(h, w) // 50)  # ~50 symbols across canvas (was fixed 80px)
    # Local coordinates within each tile
    ly = (y % cell).astype(np.float32) - cell / 2.0
    lx = (x % cell).astype(np.float32) - cell / 2.0
    pattern = np.zeros((h, w), dtype=np.float32)
    R = cell * 0.32  # outer radius of each crescent arc
    r = cell * 0.16  # inner radius (cutout)
    center_hole = cell * 0.08  # center hole radius
    # Three crescents at 120-degree intervals
    for k in range(3):
        a = k * 2.0 * np.pi / 3.0
        # Center of each crescent arc, offset from tile center
        offset = cell * 0.14
        cy_k = np.sin(a) * offset
        cx_k = np.cos(a) * offset
        dy = ly - cy_k
        dx = lx - cx_k
        dist = np.sqrt(dy ** 2 + dx ** 2)
        crescent = ((dist < R) & (dist > r)).astype(np.float32)
        pattern = np.maximum(pattern, crescent)
    # Cut out center hole
    center_dist = np.sqrt(ly ** 2 + lx ** 2)
    pattern = np.where(center_dist < center_hole, 0.0, pattern)
    return {"pattern_val": pattern, "R_range": 65.0, "M_range": -40.0, "CC": 0}

def texture_feather_barb(shape, mask, seed, sm):
    """Feather barb - central spine with diagonal parallel barbs branching off."""
    h, w = shape
    y, x = get_mgrid((h, w))
    tile_h = 60  # vertical tile for each feather unit
    tile_w = 80  # horizontal tile
    # Local coordinates
    ly = (y % tile_h).astype(np.float32)
    lx = (x % tile_w).astype(np.float32)
    pattern = np.zeros((h, w), dtype=np.float32)
    # Central rachis (spine) - horizontal center line of each tile
    spine_y = tile_h / 2.0
    spine_thick = 2.0
    spine = (np.abs(ly - spine_y) < spine_thick).astype(np.float32)
    pattern = np.maximum(pattern, spine)
    # Diagonal barbs branching off the spine
    barb_spacing = 4.0  # spacing between parallel barbs
    barb_thick = 1.2
    # Upper barbs: angled lines going up-right from spine
    # Line equation: y = spine_y - (x - x0) * slope => x + y*slope = const
    slope = 0.6
    upper_region = ly < spine_y
    diag_upper = ((lx * slope + ly) % barb_spacing)
    upper_barbs = ((diag_upper < barb_thick) & upper_region).astype(np.float32)
    # Lower barbs: angled lines going down-right from spine
    lower_region = ly > spine_y
    diag_lower = ((lx * slope - ly + tile_h) % barb_spacing)
    lower_barbs = ((diag_lower < barb_thick) & lower_region).astype(np.float32)
    pattern = np.maximum(pattern, upper_barbs)
    pattern = np.maximum(pattern, lower_barbs)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2610) * 0.12 + 0.07
    pattern = np.clip(pattern + bg_fill, 0, 1)
    return {"pattern_val": pattern, "R_range": 55.0, "M_range": -30.0, "CC": None}


# ══════════════════════════════════════════════════════════════════════════
# BATCH 2 — Unique texture functions for formerly-duplicated patterns
# Each returns {"pattern_val": float32[H,W] 0-1, "R_range", "M_range", "CC"}
# ══════════════════════════════════════════════════════════════════════════

def texture_binary_code_v2(shape, mask, seed, sm):
    """Binary code — columns of 1/0 rectangular cells like a binary readout."""
    h, w = shape
    rng = np.random.RandomState(seed)
    cell_w = max(8, min(h, w) // 64)
    cell_h = max(12, int(cell_w * 1.5))
    rows = (h + cell_h - 1) // cell_h
    cols = (w + cell_w - 1) // cell_w
    bits = rng.randint(0, 2, (rows, cols)).astype(np.float32)
    result = np.repeat(np.repeat(bits, cell_h, axis=0), cell_w, axis=1)[:h, :w]
    y, x = get_mgrid((h, w))
    # Column separator lines
    gap = max(1, cell_w // 6)
    col_gap = ((x % cell_w) < gap).astype(np.float32) * 0.3
    row_gap = ((y % cell_h) < max(1, cell_h // 8)).astype(np.float32) * 0.15
    pv = np.clip(result * 0.85 - col_gap - row_gap, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -100.0, "M_range": 150.0, "CC": 0}

def texture_palm_frond_v2(shape, mask, seed, sm):
    """Palm frond — radiating leaf veins with central spine, tiled."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Resolution-cap: compute fronds at 1024 max
    ds = max(1, min(h, w) // 1024)
    ch, cw = max(64, h // ds), max(64, w // ds)
    out = np.zeros((ch, cw), dtype=np.float32)
    y_arr, x_arr = get_mgrid((ch, cw))
    yf = y_arr.astype(np.float32)
    xf = x_arr.astype(np.float32)
    scale = min(ch, cw) / 256.0
    n_fronds = rng.randint(7, 12)  # More fronds for coverage (was 4-7)
    for _ in range(n_fronds):
        cx = rng.randint(0, cw)
        cy = rng.randint(0, ch)
        angle = rng.uniform(0, 2 * np.pi)
        length = rng.uniform(ch * 0.25, ch * 0.5)
        leaf_w_base = rng.uniform(20, 40) * scale
        end_x = cx + np.cos(angle) * length
        end_y = cy + np.sin(angle) * length
        margin = leaf_w_base * 1.5
        ry0 = max(0, int(min(cy, end_y) - margin))
        ry1 = min(ch, int(max(cy, end_y) + margin))
        rx0 = max(0, int(min(cx, end_x) - margin))
        rx1 = min(cw, int(max(cx, end_x) + margin))
        if ry1 <= ry0 or rx1 <= rx0:
            continue
        ry = yf[ry0:ry1, rx0:rx1]
        rx = xf[ry0:ry1, rx0:rx1]
        dx, dy = rx - cx, ry - cy
        along = dx * np.cos(angle) + dy * np.sin(angle)
        across = -dx * np.sin(angle) + dy * np.cos(angle)
        t = np.clip(along / max(1, length), 0, 1)
        in_frond = (along > 0) & (along < length)
        spine_w = 3.0 * scale * (1 - t * 0.5)
        spine = np.exp(-(across ** 2) / (2 * spine_w ** 2 + 1e-6)) * in_frond * 0.95  # Was 0.7
        leaf_taper = leaf_w_base * (1 - t)
        leaflet_pattern = np.abs(np.sin(t * 12.0 * np.pi))
        leaflet = np.exp(-(across ** 2) / (2 * (leaf_taper * 0.3 + 1) ** 2)) * leaflet_pattern
        leaflet *= in_frond * (np.abs(across) < leaf_taper) * 0.8  # Was 0.5
        out[ry0:ry1, rx0:rx1] += spine + leaflet
    # Upscale frond structure to full resolution
    if (ch, cw) != (h, w):
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    # Add fine leaf vein texture for detail (at full res for sharp veins)
    vein_noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 200)
    out = np.clip(out + np.where(out > 0.03, vein_noise * 0.08, 0), 0, 1)
    # Background foliage texture for full coverage
    bg_tex = multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 300)
    bg = np.clip(bg_tex * 0.18 + 0.10, 0, 0.25)
    pv = np.clip(np.maximum(out, bg), 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -40.0, "M_range": 30.0, "CC": None}

def texture_ekg_v2(shape, mask, seed, sm):
    """EKG heartbeat line — horizontal baseline with sharp QRS spikes, multiple scan lines.
    OPTIMIZED: compute waveform as 1D (x-only), broadcast to 2D only at distance step."""
    h, w = shape
    yf = np.arange(h, dtype=np.float32).reshape(-1, 1)  # (h,1) column
    out = np.zeros((h, w), dtype=np.float32)
    period = max(80, min(h, w) // 6)
    line_w = max(2.0, min(h, w) / 300.0)
    n_lines = max(3, h // 120)
    # Compute 1D waveform along x-axis ONCE (shared by all scan lines)
    x1d = np.arange(w, dtype=np.float32)
    phase_1d = (x1d % period) / period  # (w,) 1D array
    ekg_1d = np.zeros(w, dtype=np.float32)
    # P wave
    p_mask = (phase_1d > 0.10) & (phase_1d < 0.20)
    ekg_1d[p_mask] = np.sin((phase_1d[p_mask] - 0.10) / 0.10 * np.pi) * 0.3
    # QRS complex
    ekg_1d[(phase_1d > 0.30) & (phase_1d < 0.35)] = -0.2
    ekg_1d[(phase_1d > 0.35) & (phase_1d < 0.40)] = 1.0
    ekg_1d[(phase_1d > 0.40) & (phase_1d < 0.45)] = -0.4
    # T wave
    t_mask = (phase_1d > 0.55) & (phase_1d < 0.70)
    ekg_1d[t_mask] = np.sin((phase_1d[t_mask] - 0.55) / 0.15 * np.pi) * 0.4
    # Broadcast to 2D for each scan line
    trace_offset_1d = ekg_1d * h * 0.06  # (w,) — y-offset at each x
    for li in range(n_lines):
        center_y = np.float32(h * (li + 1) / (n_lines + 1))
        trace_y_1d = center_y + trace_offset_1d  # (w,) row
        # Distance from each pixel's y to the trace — broadcast (h,1) vs (1,w)
        dist = np.abs(yf - trace_y_1d.reshape(1, -1))
        line = np.clip(1.0 - dist / line_w, 0, 1)
        np.maximum(out, line, out=out)
    # CRT phosphor grain + scan lines for full coverage
    grain = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 300)
    scan = np.sin(yf * np.pi * 0.3) ** 2 * 0.08
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1750) * 0.13 + 0.08
    pv = np.clip(out + grain * 0.06 + scan + bg_fill, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -80.0, "M_range": 120.0, "CC": 0}

def texture_tire_smoke_v2(shape, mask, seed, sm):
    """Tire smoke — turbulent noise stretched horizontally, wispy smoke trails."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Resolution-cap: 30 plumes × full-res arrays. Cap at 1024.
    ds = max(1, min(h, w) // 1024)
    ch, cw = max(64, h // ds), max(64, w // ds)
    yf = np.arange(ch, dtype=np.float32).reshape(-1, 1)
    xf = np.arange(cw, dtype=np.float32).reshape(1, -1)
    # Layer 1: Ambient smoke haze (at compute res)
    haze = multi_scale_noise((ch, cw), [16, 32, 64], [0.3, 0.4, 0.3], seed + 4)
    haze = (haze - haze.min()) / (haze.max() - haze.min() + 1e-8)
    rise_factor = np.clip(1.0 - yf / ch, 0, 1)
    out = haze * (0.08 + rise_factor * 0.12)
    # Layer 2: Smoke plumes — wider, rising from bottom
    for _ in range(30):
        cx = rng.uniform(-cw * 0.05, cw * 1.05)
        base_width = cw * rng.uniform(0.04, 0.12)
        drift = rng.uniform(-0.3, 0.3)
        intensity = rng.uniform(0.25, 0.65)
        phase = rng.uniform(0, 2 * np.pi)
        rise = np.clip(1.0 - yf / ch, 0, 1)
        width = base_width * (1.0 + (1.0 - rise) * 2.5)
        path_x = cx + (1.0 - rise) * drift * cw * 0.3
        path_x += np.sin(yf * 0.03 + phase) * cw * 0.03 * (1.0 - rise)
        path_x += np.sin(yf * 0.07 + phase * 2.1) * cw * 0.015 * (1.0 - rise)
        dx = np.abs(xf - path_x)
        plume = np.clip(1.0 - dx / (width + 1), 0, 1) * rise ** 0.4
        out = np.maximum(out, plume * intensity)
    # Turbulent breakup
    nh, nw = max(1, ch // 12 + 1), max(1, cw // 12 + 1)
    turb = rng.rand(nh, nw).astype(np.float32)
    turb_map = np.repeat(np.repeat(turb, 12, 0), 12, 1)[:ch, :cw]
    out = out * (0.55 + turb_map * 0.6)
    # Upscale to full resolution
    if (ch, cw) != (h, w):
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -30.0, "M_range": 20.0, "CC": None}

def texture_ember_scatter_v2(shape, mask, seed, sm):
    """Ember scatter — dense bright dots with streaked trails over warm haze."""
    h, w = shape
    rng = np.random.RandomState(seed)
    sz = min(h, w)
    # Warm haze background — fills entire canvas
    haze = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 50)
    haze = np.clip(haze * 0.2 + 0.15, 0.05, 0.3)
    out = haze.copy()
    # Density map — embers cluster in hot zones
    density = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 100)
    density = (density - density.min()) / (density.max() - density.min() + 1e-8)
    n_embers = rng.randint(300, 500)  # 2.5x more embers
    for _ in range(n_embers):
        ex = rng.randint(0, w)
        ey = rng.randint(0, h)
        # Lower skip threshold for better coverage
        if density[ey % h, ex % w] < rng.uniform(0.1, 0.4):
            continue
        size = rng.uniform(0.003, 0.012) * sz  # Larger embers
        intensity = rng.uniform(0.6, 1.0)
        # Elongated trail (ember streak) — stretch in y direction
        trail_len = rng.uniform(2.0, 5.0)
        m = int(size * trail_len * 2) + 4
        y0, y1 = max(0, ey - m), min(h, ey + m)
        x0, x1 = max(0, ex - int(size * 2) - 3), min(w, ex + int(size * 2) + 3)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        ember = np.exp(-((lx - ex) ** 2 / (2 * size ** 2) +
                         (ly - ey) ** 2 / (2 * (size * trail_len) ** 2))) * intensity
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], ember)
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -50.0, "M_range": 100.0, "CC": None}

def texture_gothic_cross_v2(shape, mask, seed, sm):
    """Gothic cross — tiled ornate pointed cross/crucifix shapes in a grid."""
    h, w = shape
    y, x = get_mgrid((h, w))
    cell = max(40, min(h, w) // 12)
    ly = (y % cell).astype(np.float32)
    lx = (x % cell).astype(np.float32)
    cy, cx = cell / 2.0, cell / 2.0
    dy = ly - cy
    dx = lx - cx
    # Cross arms with flared (gothic pointed) ends
    arm_w = max(3.0, cell * 0.08)
    v_arm = (np.abs(dx) < arm_w + np.abs(dy) * 0.15).astype(np.float32) * \
            (np.abs(dy) < cell * 0.4).astype(np.float32)
    h_arm = (np.abs(dy) < arm_w + np.abs(dx) * 0.15).astype(np.float32) * \
            (np.abs(dx) < cell * 0.35).astype(np.float32)
    cross = np.maximum(v_arm, h_arm)
    # Pointed top
    denom = np.maximum(3.0 + (cy - ly) * 0.3, 1e-6)
    top_point = np.clip(1.0 - np.abs(dx) / denom, 0, 1) * \
                (ly < cy - cell * 0.3).astype(np.float32)
    pv = np.clip(cross + top_point * 0.5, 0, 1).astype(np.float32)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2570) * 0.12 + 0.07
    pv = np.clip(pv + bg_fill, 0, 1)
    return {"pattern_val": pv, "R_range": -60.0, "M_range": 50.0, "CC": None}

def texture_speed_lines_v2(shape, mask, seed, sm):
    """Speed lines — horizontal motion blur streaks, manga style."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    scale = min(h, w) / 256.0
    cy = h / 2.0
    for _ in range(100):
        sy = rng.randint(0, h)
        sx = rng.randint(0, w // 3)
        length = int(rng.randint(50, min(400, w)) * scale)
        thickness = max(1, int(rng.randint(1, 4) * scale))
        brightness = rng.uniform(0.3, 1.0)
        # Lines near center are longer/brighter (convergence)
        dist_from_center = abs(sy - cy) / (h / 2.0)
        brightness *= (1.0 - dist_from_center * 0.5)
        length = int(length * (1.0 - dist_from_center * 0.3))
        y0, y1 = max(0, sy), min(h, sy + thickness)
        x0, x1 = sx, min(w, sx + length)
        if y1 <= y0 or x1 <= x0:
            continue
        fade = np.linspace(1.0, 0.0, x1 - x0, dtype=np.float32).reshape(1, -1)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], brightness * fade)
    # Background motion blur noise
    blur_bg = multi_scale_noise(shape, [8, 32], [0.3, 0.7], seed + 200)
    blur_bg = np.clip(blur_bg * 0.16 + 0.09, 0, 0.25)
    pv = np.clip(out + blur_bg, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -55.0, "M_range": 45.0, "CC": None}

def texture_ocean_foam_v2(shape, mask, seed, sm):
    """Ocean foam — clusters of bubble circles with organic density variation."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    # Density field — foam clusters
    density = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 77)
    density = (density - density.min()) / (density.max() - density.min() + 1e-8)
    n_bubbles = rng.randint(300, 700)
    for _ in range(n_bubbles):
        bx = rng.randint(0, w)
        by = rng.randint(0, h)
        if density[by, bx] < 0.35:
            continue
        r = rng.uniform(2, 10) * density[by, bx]
        m = int(r + 3)
        y0, y1 = max(0, by - m), min(h, by + m)
        x0, x1 = max(0, bx - m), min(w, bx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((lx - bx) ** 2 + (ly - by) ** 2)
        # Ring shape for bubbles
        ring = np.exp(-((dist - r) ** 2) / (2 * 1.2 ** 2)) * rng.uniform(0.4, 1.0)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], ring)
    # Soft foam base layer
    foam_base = np.repeat(np.repeat(
        rng.rand(max(1, h // 4 + 1), max(1, w // 4 + 1)).astype(np.float32),
        4, 0), 4, 1)[:h, :w] * 0.15
    out += foam_base * (density > 0.3).astype(np.float32)
    pv = np.clip(out, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -20.0, "M_range": 15.0, "CC": None}

def texture_asphalt_v2(shape, mask, seed, sm):
    """Asphalt — rough road texture with multi-scale noise and aggregate stones."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Multi-scale noise base (coarser than static noise)
    base = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed) * 0.5 + 0.5
    # Aggregate stone particles
    stones = np.zeros((h, w), dtype=np.float32)
    n_stones = int(h * w * 0.003)
    for _ in range(n_stones):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        sr = rng.randint(1, 4)
        brightness = rng.uniform(0.5, 1.0)
        y0, y1 = max(0, sy - sr), min(h, sy + sr + 1)
        x0, x1 = max(0, sx - sr), min(w, sx + sr + 1)
        if y1 > y0 and x1 > x0:
            ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
            lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
            dist = np.sqrt((ly - sy) ** 2 + (lx - sx) ** 2)
            stone = np.clip(1.0 - dist / sr, 0, 1) * brightness
            stones[y0:y1, x0:x1] = np.maximum(stones[y0:y1, x0:x1], stone)
    # Fine grain overlay for extra texture detail
    grain = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 500)
    grain = np.clip(grain * 0.15, -0.1, 0.1)
    pv = np.clip(base * 0.55 + stones * 0.55 + grain + 0.08, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": 60.0, "M_range": -40.0, "CC": None}

def texture_dna_helix_v2(shape, mask, seed, sm):
    """DNA double helix — two intertwined sine waves with connecting rungs, tiled vertically."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Tile horizontally in columns
    col_w = max(60, min(h, w) // 6)
    lx = (xf % col_w).astype(np.float32)
    cx = col_w / 2.0
    period = max(40, min(h, w) // 10)
    amplitude = col_w * 0.3
    strand1_x = cx + np.sin(yf * np.pi * 2 / period) * amplitude
    strand2_x = cx - np.sin(yf * np.pi * 2 / period) * amplitude
    line_w = max(2.0, col_w / 25.0)
    s1 = np.clip(1.0 - np.abs(lx - strand1_x) / line_w, 0, 1)
    s2 = np.clip(1.0 - np.abs(lx - strand2_x) / line_w, 0, 1)
    # Connecting rungs at regular intervals
    rung_spacing = max(8, period // 5)
    rung_mask = (yf % rung_spacing < max(2, rung_spacing // 5)).astype(np.float32)
    rung_x_min = np.minimum(strand1_x, strand2_x)
    rung_x_max = np.maximum(strand1_x, strand2_x)
    rung = ((lx > rung_x_min) & (lx < rung_x_max)).astype(np.float32) * rung_mask * 0.7  # Was 0.5
    # Background molecular texture
    bg = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 400) * 0.16 + 0.09
    pv = np.clip(s1 + s2 + rung + bg, 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -70.0, "M_range": 90.0, "CC": None}

def texture_neuron_network_v2(shape, mask, seed, sm):
    """Neuron network — cell bodies (circles) with branching dendrite connections."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    n_neurons = max(35, int(60 * min(h, w) / 512))  # Denser network
    neurons_y = rng.randint(0, h, n_neurons)
    neurons_x = rng.randint(0, w, n_neurons)
    # Draw dendrite connections between nearby neurons
    for i in range(n_neurons):
        ay, ax = int(neurons_y[i]), int(neurons_x[i])
        dists = np.sqrt((neurons_y.astype(np.float64) - ay) ** 2 +
                        (neurons_x.astype(np.float64) - ax) ** 2)
        dists[i] = 1e9
        neighbors = np.argsort(dists)[:rng.randint(2, 4)]
        for ni in neighbors:
            by, bx = int(neurons_y[ni]), int(neurons_x[ni])
            n_pts = int(np.sqrt((ay - by) ** 2 + (ax - bx) ** 2)) + 1
            if n_pts < 2:
                continue
            for ti in range(n_pts):
                t = ti / max(1, n_pts - 1)
                py = int(ay + (by - ay) * t + np.sin(t * 6 + i) * 4)
                px = int(ax + (bx - ax) * t + np.cos(t * 6 + i) * 4)
                if 0 <= py < h and 0 <= px < w:
                    r = 1
                    y0, y1 = max(0, py - r), min(h, py + r + 1)
                    x0, x1 = max(0, px - r), min(w, px + r + 1)
                    out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], 0.4)
    # Draw cell bodies (soma) on top
    for i in range(n_neurons):
        cy_n, cx_n = int(neurons_y[i]), int(neurons_x[i])
        r = rng.uniform(4, 8) * min(h, w) / 512.0
        m = int(r) + 2
        y0, y1 = max(0, cy_n - m), min(h, cy_n + m)
        x0, x1 = max(0, cx_n - m), min(w, cx_n + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - cy_n) ** 2 + (lx - cx_n) ** 2)
        soma = np.clip(1.0 - dist / max(1, r), 0, 1) ** 0.5
        np.maximum(out[y0:y1, x0:x1], soma * 0.95, out=out[y0:y1, x0:x1])  # Brighter soma (was 0.8)
    # Synaptic noise on dendrites
    syn_noise = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 500)
    out = np.clip(out + np.where(out > 0.02, syn_noise * 0.08, 0), 0, 1)
    # Background neural fog (full coverage — brain tissue texture)
    bg_fog = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 600)
    bg = np.clip(bg_fog * 0.15 + 0.09, 0, 0.22)  # Stronger brain tissue bg
    pv = np.clip(np.maximum(out, bg), 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -80.0, "M_range": 110.0, "CC": 0}

def texture_molecular_v2(shape, mask, seed, sm):
    """Molecular — ball-and-stick model with atom circles and bond lines."""
    h, w = shape
    rng = np.random.RandomState(seed)
    out = np.zeros((h, w), dtype=np.float32)
    spacing = max(20, min(h, w) // 18)
    atoms = []
    for gy in range(0, h + spacing, spacing):
        for gx in range(0, w + spacing, spacing):
            ay = gy + rng.randint(-5, 6)
            ax = gx + rng.randint(-5, 6)
            ar = rng.uniform(3, 6) * min(h, w) / 512.0
            atoms.append((ay, ax, ar))
    # Draw bonds between nearby atoms
    for i, (ay1, ax1, _) in enumerate(atoms):
        for j in range(i + 1, min(i + 8, len(atoms))):
            ay2, ax2, _ = atoms[j]
            d = np.sqrt((ay1 - ay2) ** 2 + (ax1 - ax2) ** 2)
            if d > spacing * 1.6 or d < 5:
                continue
            bond_len = int(d) + 1
            for t_idx in range(bond_len):
                t = t_idx / max(1, bond_len - 1)
                by = int(ay1 + (ay2 - ay1) * t)
                bx = int(ax1 + (ax2 - ax1) * t)
                bw = 2  # Wider bonds (was 1)
                y0, y1 = max(0, by - bw), min(h, by + bw + 1)
                x0, x1 = max(0, bx - bw), min(w, bx + bw + 1)
                if y1 > y0 and x1 > x0:
                    out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], 0.55)  # Was 0.45
    # Draw atoms on top
    for ay, ax, ar in atoms:
        m = int(ar) + 2
        y0, y1 = max(0, ay - m), min(h, ay + m)
        x0, x1 = max(0, ax - m), min(w, ax + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        dist = np.sqrt((ly - ay) ** 2 + (lx - ax) ** 2)
        sphere = np.clip(1.0 - dist / max(1, ar), 0, 1) ** 0.6
        np.maximum(out[y0:y1, x0:x1], sphere, out=out[y0:y1, x0:x1])
    # Chemical substrate background
    bg = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 200) * 0.15 + 0.09
    pv = np.clip(np.maximum(out, bg), 0, 1).astype(np.float32)
    return {"pattern_val": pv, "R_range": -60.0, "M_range": 80.0, "CC": None}


# ---------------------------------------------------------------------------
# V5.3 DEDICATED TEXTURE FUNCTIONS (15 rewritten patterns)
# Each replaces a generic/shared texture_fn with a visually accurate version.
# ---------------------------------------------------------------------------

def texture_aero_flow_v2(shape, mask, seed, sm):
    """Aerodynamic flow lines with curl-noise distortion."""
    h, w = shape
    rng = np.random.default_rng(seed + 7000)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)
    # Base horizontal flow lines
    freq_y = 30.0
    flow = np.sin(yf * freq_y * np.pi) * 0.5 + 0.5
    # Curl-noise distortion: use multi-scale noise to displace y coordinate
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7001)
    n2 = multi_scale_noise(shape, [16, 32, 64], [0.25, 0.45, 0.3], seed + 7002)
    # Vertical wobble displacement
    displacement = n1 * 0.15 + n2 * 0.08
    yf_warped = yf + displacement
    flow_warped = np.sin(yf_warped * freq_y * np.pi) * 0.5 + 0.5
    # Add horizontal streaking via x-frequency modulation
    streak = np.sin(xf * 6.0 * np.pi + n1 * 4.0) * 0.3 + 0.7
    pattern = np.clip(flow_warped * streak, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -85.0, "M_range": 75.0, "CC": 0}


def texture_aztec_steps_v2(shape, mask, seed, sm):
    """Nested concentric rectangles creating stepped pyramid motif, tiled."""
    h, w = shape
    rng = np.random.default_rng(seed + 7010)
    y, x = get_mgrid((h, w))
    cell_size = max(40, min(h, w) // 10)
    # Local coordinates within each tile cell [0..1]
    lx = (x.astype(np.float32) % cell_size) / cell_size
    ly = (y.astype(np.float32) % cell_size) / cell_size
    # Concentric rectangular distance (Chebyshev from center)
    rect_dist = np.maximum(np.abs(lx - 0.5), np.abs(ly - 0.5))
    # Quantize into stepped bands
    n_steps = 6
    stepped = np.floor(rect_dist * n_steps * 2.0).astype(np.int32)
    pattern = (stepped % 2).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 68.0, "M_range": -38.0, "CC": None}


def texture_bamboo_stalk_v2(shape, mask, seed, sm):
    """Wide vertical bamboo stalks with horizontal node joints and grain noise."""
    h, w = shape
    rng = np.random.default_rng(seed + 7020)
    y, x = get_mgrid((h, w))
    xf = x.astype(np.float32)
    yf = y.astype(np.float32)
    # Wide vertical stalks (~20px)
    stalk_period = max(30, w // 16)
    stalk_width = stalk_period * 0.6
    x_in_cell = xf % stalk_period
    stalk_mask = np.clip(1.0 - np.abs(x_in_cell - stalk_period * 0.5) / (stalk_width * 0.5), 0, 1)
    stalk_mask = np.where(stalk_mask > 0, 1.0, 0.0).astype(np.float32)
    # Horizontal node joints every ~60px
    node_period = max(50, h // 8)
    node_band = np.abs(yf % node_period - node_period * 0.5)
    node_line = np.where(node_band < 2.5, 1.0, 0.0).astype(np.float32)
    # Subtle grain noise on stalk surface
    grain = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7021)
    grain = grain * 0.15 + 0.85  # subtle variation 0.7-1.0
    # Combine: stalk body with grain, plus joint lines
    pattern = stalk_mask * grain
    pattern = np.clip(pattern + node_line * stalk_mask * 0.4, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 55.0, "CC": 0}


def texture_hibiscus_v2(shape, mask, seed, sm):
    """5-petal hibiscus flower using rose curve r=cos(5*theta), tiled."""
    h, w = shape
    rng = np.random.default_rng(seed + 7030)
    y, x = get_mgrid((h, w))
    cell_size = max(30, min(h, w) // 20)  # Much denser flowers (was //6 = 6 flowers, now //20 = ~20)
    lx = (x.astype(np.float32) % cell_size) - cell_size * 0.5
    ly = (y.astype(np.float32) % cell_size) - cell_size * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) / (cell_size * 0.45)
    theta = np.arctan2(ly, lx)
    r_rose = np.abs(np.cos(2.5 * theta))  # 5-petal rose
    petal = np.clip(1.0 - (r / (r_rose + 0.05)) * 1.1, 0, 1)
    center = np.clip(1.0 - r * 4.0, 0, 1)
    # Background leaf texture between flowers
    bg = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100) * 0.18 + 0.10
    pattern = np.clip(petal + center * 0.7 + bg, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 55.0, "M_range": -35.0, "CC": None}


def texture_iron_cross_v2(shape, mask, seed, sm):
    """Flared 4-arm Iron Cross with arms narrowing toward tips, tiled in cells."""
    h, w = shape
    rng = np.random.default_rng(seed + 7040)
    y, x = get_mgrid((h, w))
    cell_size = max(50, min(h, w) // 8)
    # Local coordinates centered [-0.5, 0.5]
    lx = (x.astype(np.float32) % cell_size) / cell_size - 0.5
    ly = (y.astype(np.float32) % cell_size) / cell_size - 0.5
    ax, ay = np.abs(lx), np.abs(ly)
    # Central diamond: abs(x)+abs(y) < radius
    diamond = (ax + ay < 0.22).astype(np.float32)
    # Four rectangular arms that narrow: arm width tapers with distance
    arm_len = 0.45
    arm_base_w = 0.14
    arm_tip_w = 0.04
    # Horizontal arms
    h_arm_dist = ax
    h_arm_width = arm_base_w + (arm_tip_w - arm_base_w) * (h_arm_dist / arm_len)
    h_arm = ((ax < arm_len) & (ay < h_arm_width)).astype(np.float32)
    # Vertical arms
    v_arm_dist = ay
    v_arm_width = arm_base_w + (arm_tip_w - arm_base_w) * (v_arm_dist / arm_len)
    v_arm = ((ay < arm_len) & (ax < v_arm_width)).astype(np.float32)
    pattern = np.clip(diamond + h_arm + v_arm, 0, 1).astype(np.float32)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2500) * 0.12 + 0.07
    pattern = np.clip(pattern + bg_fill, 0, 1)
    return {"pattern_val": pattern, "R_range": 72.0, "M_range": -50.0, "CC": None}


def texture_gothic_scroll_v2(shape, mask, seed, sm):
    """Curling spiral scrollwork using parametric spirals arranged symmetrically."""
    h, w = shape
    rng = np.random.default_rng(seed + 7050)
    y, x = get_mgrid((h, w))
    cell_size = max(80, min(h, w) // 5)
    lx = (x.astype(np.float32) % cell_size) - cell_size * 0.5
    ly = (y.astype(np.float32) % cell_size) - cell_size * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) / (cell_size * 0.5) + 1e-8
    theta = np.arctan2(ly, lx)
    # Archimedean spiral: r = a + b*theta
    # Distance from spiral arm: measure sin(theta - r * k)
    k_spiral = 6.0
    scroll1 = np.sin(theta - r * k_spiral * np.pi) * 0.5 + 0.5
    scroll2 = np.sin(-theta - r * k_spiral * np.pi + np.pi * 0.5) * 0.5 + 0.5
    # Combine symmetric pair
    combined = np.minimum(scroll1, scroll2)
    # Sharpen scrollwork lines
    line = np.where(combined < 0.35, 1.0, 0.0).astype(np.float32)
    # Fade edges for filigree softness
    edge_fade = np.clip(1.0 - r * 0.3, 0.3, 1.0)
    pattern = (line * edge_fade).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -45.0, "CC": None}


def texture_drift_marks_v2(shape, mask, seed, sm):
    """Wide diagonal rubber drift streaks with soft edges, irregular spacing."""
    h, w = shape
    rng = np.random.default_rng(seed + 7060)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Diagonal projection at ~30 degrees
    diag = xf * 0.87 + yf * 0.5
    # Generate multiple wide streaks at irregular intervals
    n_streaks = rng.integers(6, 12)
    total_span = np.sqrt(float(h ** 2 + w ** 2))
    positions = np.sort(rng.uniform(0, total_span, n_streaks))
    widths = rng.uniform(25, 50, n_streaks)
    pattern = np.zeros((h, w), dtype=np.float32)
    for i in range(n_streaks):
        dist_from_center = np.abs(diag - positions[i])
        half_w = widths[i] * 0.5
        # Soft-edged streak using smoothstep
        t = np.clip(dist_from_center / half_w, 0, 1)
        streak = 1.0 - t * t * (3.0 - 2.0 * t)  # smoothstep falloff
        pattern = np.maximum(pattern, streak)
    # Add slight noise for rubber texture
    grain = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 7061)
    pattern = np.clip(pattern * (0.85 + grain * 0.15), 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -90.0, "M_range": 70.0, "CC": 0}


def texture_caustic_v2(shape, mask, seed, sm):
    """Multi-source interference pattern with 8-12 random point sources, bright peaks."""
    h, w = shape
    rng = np.random.default_rng(seed + 7070)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    n_sources = rng.integers(8, 13)
    src_y = rng.uniform(0, h, n_sources).astype(np.float32)
    src_x = rng.uniform(0, w, n_sources).astype(np.float32)
    freq = rng.uniform(0.08, 0.15, n_sources).astype(np.float32)
    # Sum of sine waves from each point source
    wave_sum = np.zeros((h, w), dtype=np.float32)
    for i in range(n_sources):
        dist = np.sqrt((yf - src_y[i]) ** 2 + (xf - src_x[i]) ** 2)
        wave_sum += np.sin(dist * freq[i] * 2.0 * np.pi) * 0.5 + 0.5
    # Normalize and enhance bright intersection peaks
    wave_sum = wave_sum / n_sources
    # Square to emphasize constructive interference peaks
    pattern = np.clip(wave_sum ** 2 * 2.5, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -70.0, "M_range": 55.0, "CC": 0}


def texture_frost_crystal_v2(shape, mask, seed, sm):
    """Hexagonal grid with dendritic branches growing from vertices at 60-deg angles."""
    h, w = shape
    rng = np.random.default_rng(seed + 7080)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Hexagonal grid parameters
    hex_size = max(25, min(h, w) // 20)  # Denser crystals (was //8 = 8 crystals, now //20 = ~20)
    # Hex grid: offset every other row
    row = np.floor(yf / (hex_size * 0.866)).astype(np.int32)
    x_offset = np.where(row % 2 == 0, 0.0, hex_size * 0.5)
    # Distance to nearest hex center
    hx = ((xf + x_offset) % hex_size) - hex_size * 0.5
    hy = (yf % (hex_size * 0.866)) - hex_size * 0.433
    dist_center = np.sqrt(hx ** 2 + hy ** 2)
    # Angle from hex center
    angle = np.arctan2(hy, hx)
    # Dendritic branches at 60-degree intervals (6-fold symmetry)
    branch_angle = np.abs(np.sin(angle * 3.0))  # peaks at 0, 60, 120, ... deg
    # Branch mask: thin lines radiating from center
    branch_width = hex_size * 0.04
    branch_mask = np.clip(1.0 - branch_angle / 0.18, 0, 1)  # Anti-aliased (was binary)
    # Sub-branches: secondary branching at smaller scale
    sub_branch = np.abs(np.sin(angle * 6.0 + dist_center * 0.3))
    sub_mask = np.clip(1.0 - sub_branch / 0.15, 0, 0.7) * (dist_center > hex_size * 0.15).astype(np.float32)  # Anti-aliased
    # Combine: hex edge + branches + sub-branches
    hex_edge = np.clip(1.0 - np.abs(dist_center - hex_size * 0.4) / (hex_size * 0.05), 0, 1)
    crystal = np.clip(branch_mask + sub_mask.astype(np.float32) + hex_edge * 0.6, 0, 1)
    # Fade with distance from center for crystal look
    fade = np.clip(1.0 - dist_center / (hex_size * 0.5), 0.1, 1.0)
    # Ice surface texture between crystals
    ice = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7081) * 0.06 + 0.04
    pattern = np.clip(crystal * fade + ice, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -80.0, "M_range": 60.0, "CC": None}


def texture_glitch_scan_v2(shape, mask, seed, sm):
    """Horizontal bands with random x-offset displacement, scanline flicker, binary noise."""
    h, w = shape
    rng = np.random.default_rng(seed + 7090)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Divide into horizontal bands of varying height
    band_height = max(4, h // 60)
    band_idx = (yf / band_height).astype(np.int32)
    n_bands = int(np.ceil(h / band_height)) + 1
    # Random x-displacement per band
    offsets = rng.integers(-w // 6, w // 6, n_bands)
    # Build offset map
    offset_map = np.zeros((h, w), dtype=np.float32)
    for i in range(n_bands):
        band_mask = (band_idx == i)
        offset_map = np.where(band_mask, float(offsets[i % n_bands]), offset_map)
    # Displaced x coordinate
    x_displaced = (xf + offset_map) % w
    # Scanline flicker: thin horizontal lines
    scanline = ((yf.astype(np.int32) % 3) == 0).astype(np.float32) * 0.3
    # Binary threshold noise from displaced coordinates
    noise_seed = seed + 7091
    # Create block noise using displaced coordinates
    block_w = max(6, w // 80)
    block_h = band_height
    bx = (x_displaced / block_w).astype(np.int32)
    by = (yf / block_h).astype(np.int32)
    # Hash-based pseudo-random binary values
    hash_val = ((bx * 73856093) ^ (by * 19349663) ^ noise_seed) % 1000
    binary = (hash_val > 500).astype(np.float32)
    # Combine: binary blocks + scanline flicker
    pattern = np.clip(binary * 0.8 + scanline, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -75.0, "M_range": 65.0, "CC": 0}


def texture_corrugated_v2(shape, mask, seed, sm):
    """Smooth sine-wave corrugation cross-section with smoothstep transitions."""
    h, w = shape
    rng = np.random.default_rng(seed + 7100)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    # Corrugation frequency
    freq = max(15, h // 20)
    phase = yf / freq * np.pi * 2.0
    # Raw sine wave
    raw = np.sin(phase) * 0.5 + 0.5
    # Smoothstep for rounded ridges: 3t^2 - 2t^3
    t = raw
    smooth = t * t * (3.0 - 2.0 * t)
    pattern = smooth.astype(np.float32)
    return {"pattern_val": pattern, "R_range": -100.0, "M_range": 90.0, "CC": 0}


def texture_herringbone_v2(shape, mask, seed, sm):
    """Proper V-stitch herringbone with short diagonal segments alternating in 2x2 cells."""
    h, w = shape
    rng = np.random.default_rng(seed + 7110)
    y, x = get_mgrid((h, w))
    # Cell dimensions: each cell contains one diagonal segment
    cell_w = max(12, w // 40)
    cell_h = max(20, h // 25)
    # Which cell
    cx = (x.astype(np.float32) / cell_w).astype(np.int32)
    cy = (y.astype(np.float32) / cell_h).astype(np.int32)
    # Local coordinates within cell [0, 1]
    lx = (x.astype(np.float32) % cell_w) / cell_w
    ly = (y.astype(np.float32) % cell_h) / cell_h
    # Alternating diagonal direction in checkerboard pattern
    direction = ((cx + cy) % 2).astype(np.float32)  # 0 or 1
    # Diagonal line: for direction 0: y = x, for direction 1: y = 1-x
    diag_0 = np.abs(ly - lx)
    diag_1 = np.abs(ly - (1.0 - lx))
    diag = np.where(direction < 0.5, diag_0, diag_1)
    # Line thickness
    thickness = 0.2
    line = np.clip(1.0 - diag / thickness, 0, 1).astype(np.float32)
    return {"pattern_val": line, "R_range": 72.0, "M_range": -42.0, "CC": None}


def texture_dazzle_v2(shape, mask, seed, sm):
    """Sharp geometric Voronoi patches with binary coloring overlaid with angled stripes."""
    h, w = shape
    rng = np.random.default_rng(seed + 7120)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Voronoi cells
    n_pts = max(25, int(h * w / 3000))
    n_pts = min(n_pts, 150)
    cell_id = _voronoi_cells_fast(shape, n_pts, 7120, seed)
    # Binary coloring per cell
    cell_color = (cell_id * 73856093 + seed) % 2
    voronoi_binary = cell_color.astype(np.float32)
    # Angled stripe field overlay
    angle1 = rng.uniform(0.3, 1.2)
    stripe1 = np.sin((xf * np.cos(angle1) + yf * np.sin(angle1)) * 0.08 * np.pi) > 0
    angle2 = rng.uniform(-1.2, -0.3)
    stripe2 = np.sin((xf * np.cos(angle2) + yf * np.sin(angle2)) * 0.12 * np.pi) > 0
    stripe_xor = (stripe1.astype(np.int32) ^ stripe2.astype(np.int32)).astype(np.float32)
    # Combine: XOR voronoi with stripe field for dazzle camo
    pattern = ((voronoi_binary.astype(np.int32) ^ stripe_xor.astype(np.int32)) % 2).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 60.0, "M_range": -80.0, "CC": 0}


def texture_leopard_rosette_v2(shape, mask, seed, sm):
    """Leopard rosette open rings using abs(dist - ring_radius) < thickness."""
    h, w = shape
    rng = np.random.default_rng(seed + 7130)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    # Work at 1/4 resolution for speed, then upscale
    ds = max(1, min(4, h // 256))
    sh, sw = h // ds, w // ds
    ys = np.arange(sh, dtype=np.float32) * ds
    xs = np.arange(sw, dtype=np.float32) * ds
    yg, xg = np.meshgrid(ys, xs, indexing='ij')
    # Scatter rosette centers in jittered grid
    cell_size = max(35, min(h, w) // 10)
    n_y = int(np.ceil(h / cell_size)) + 2
    n_x = int(np.ceil(w / cell_size)) + 2
    pat_small = np.zeros((sh, sw), dtype=np.float32)
    for iy in range(n_y):
        for ix in range(n_x):
            cy = iy * cell_size + rng.uniform(-cell_size * 0.25, cell_size * 0.25)
            cx_v = ix * cell_size + rng.uniform(-cell_size * 0.25, cell_size * 0.25)
            ring_r = rng.uniform(cell_size * 0.25, cell_size * 0.4)
            thickness = rng.uniform(2.5, 4.5)
            # Quick bounding-box skip
            margin = ring_r + thickness + 2
            if cy + margin < 0 or cy - margin > h or cx_v + margin < 0 or cx_v - margin > w:
                continue
            dist = np.sqrt((yg - cy) ** 2 + (xg - cx_v) ** 2)
            ring = np.clip(1.0 - np.abs(dist - ring_r) / thickness, 0, 1)
            center_dot = np.clip(1.0 - dist / (ring_r * 0.25 + 1e-6), 0, 1) * 0.6
            pat_small = np.maximum(pat_small, np.maximum(ring, center_dot))
    # Upscale to full resolution
    if ds > 1:
        from PIL import Image as _PILImg
        pat_img = _PILImg.fromarray((np.clip(pat_small, 0, 1) * 255).astype(np.uint8))
        pattern = np.array(pat_img.resize((w, h), _PILImg.BILINEAR), dtype=np.float32) / 255.0
    else:
        pattern = np.clip(pat_small, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": 40.0, "M_range": -25.0, "CC": None}


def texture_aurora_bands_v2(shape, mask, seed, sm):
    """Multi-frequency flowing curtain bands with vertical fade and horizontal shimmer."""
    h, w = shape
    rng = np.random.default_rng(seed + 7140)
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32) / max(h, 1)
    xf = x.astype(np.float32) / max(w, 1)
    # Vertical fade: bright at top, fading to dark at bottom
    v_fade = np.clip(1.0 - yf * 1.3, 0, 1) ** 0.7
    # Multi-frequency horizontal curtain waves
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7141)
    curtain = np.zeros((h, w), dtype=np.float32)
    freqs = [3.0, 5.0, 8.0, 13.0]
    amps = [0.35, 0.3, 0.2, 0.15]
    for freq, amp in zip(freqs, amps):
        phase = rng.uniform(0, 2 * np.pi)
        # Horizontally stretched noise displacement
        displacement = n1 * 0.3
        wave = np.sin((xf + displacement) * freq * np.pi * 2.0 + phase)
        curtain += wave * amp
    curtain = curtain * 0.5 + 0.5  # normalize to [0,1]
    # Horizontal shimmer via stretched noise
    shimmer = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7142)
    shimmer = shimmer * 0.25 + 0.80  # Wider shimmer range (was 0.15+0.85)
    pattern = np.clip(curtain * v_fade * shimmer, 0, 1).astype(np.float32)
    # Fine particle sparkle in aurora
    sparkle = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 7143) * 0.04
    pattern = np.clip(pattern + sparkle, 0, 1).astype(np.float32)
    return {"pattern_val": pattern, "R_range": -60.0, "M_range": 50.0, "CC": None}


# ── INTRICATE & ORNATE — Texture functions (Batch 1, 2026-03-28) ─────────────

def _ornate_norm(v):
    v = np.asarray(v, dtype=np.float32)
    lo = float(np.min(v))
    hi = float(np.max(v))
    if hi - lo < 1e-6:
        return np.zeros_like(v, dtype=np.float32)
    return np.clip((v - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _ornate_periodic_line(coord, period, width):
    phase = np.mod(coord / max(period, 1e-6) + 0.5, 1.0) - 0.5
    dist = np.abs(phase) * period
    return np.clip(1.0 - dist / max(width, 1e-6), 0.0, 1.0).astype(np.float32)


def _ornate_ring(radius, period, width):
    return _ornate_periodic_line(radius, period, width)


def _ornate_ellipse(lx, ly, rx, ry, width):
    d = np.sqrt((lx / max(rx, 1e-6)) ** 2 + (ly / max(ry, 1e-6)) ** 2)
    return np.clip(1.0 - np.abs(d - 1.0) / max(width, 1e-6), 0.0, 1.0).astype(np.float32)


def _ornate_wave_ink(value, width):
    return np.clip(1.0 - np.abs(np.sin(value)) / max(width, 1e-6), 0.0, 1.0).astype(np.float32)


def _ornate_micro_grit(shape, seed, strength=0.12):
    h, w = shape
    y, x = get_mgrid((h, w))
    xf = x.astype(np.float32)
    yf = y.astype(np.float32)
    noise = _ornate_norm(multi_scale_noise(shape, [3, 6, 12, 24], [0.34, 0.30, 0.22, 0.14], seed))
    hatch = np.sin(xf * 1.91 + yf * 0.73 + seed * 0.013) * np.sin(yf * 2.23 - xf * 0.41 + seed * 0.017)
    hatch = (hatch * 0.5 + 0.5).astype(np.float32)
    return np.clip(noise * 0.68 + hatch * 0.32, 0.0, 1.0).astype(np.float32) * float(strength)


def texture_sacred_geometry(shape, mask, seed, sm):
    """Sacred geometry - flower-of-life mandalas with hex arcs, spokes, and bead chains."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cx, cy = w * 0.5, h * 0.5
    dx, dy = xf - cx, yf - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    theta = np.arctan2(dy, dx)
    cell = max(18.0, sm * 46.0)
    line = max(0.48, sm * 0.68)
    radial = _ornate_ring(r, cell * 0.235, line)
    petals = _ornate_periodic_line(r * (1.0 + 0.18 * np.cos(theta * 6.0)), cell * 0.53, line * 0.92)
    lotus = _ornate_periodic_line(r * (1.0 + 0.11 * np.cos(theta * 12.0)), cell * 0.31, line * 0.62)
    spokes = _ornate_periodic_line(theta + np.sin(r / cell) * 0.10, (2.0 * np.pi) / 36.0, 0.0075)
    hex_field = np.zeros((h, w), dtype=np.float32)
    for angle in (0.0, np.pi / 3.0, -np.pi / 3.0):
        coord = xf * np.cos(angle) + yf * np.sin(angle)
        hex_field = np.maximum(hex_field, _ornate_periodic_line(coord, cell * 0.58, line * 0.60))
    flower = np.zeros((h, w), dtype=np.float32)
    for ox, oy in ((0.0, 0.0), (cell * 0.50, 0.0), (-cell * 0.50, 0.0),
                   (cell * 0.25, cell * 0.433), (-cell * 0.25, cell * 0.433),
                   (cell * 0.25, -cell * 0.433), (-cell * 0.25, -cell * 0.433)):
        rr = np.sqrt((dx - ox) ** 2 + (dy - oy) ** 2)
        flower = np.maximum(flower, _ornate_ellipse(dx - ox, dy - oy, cell * 0.50, cell * 0.50, 0.020))
        flower = np.maximum(flower, _ornate_ring(rr, cell * 0.50, line * 0.52))
    beads = _ornate_periodic_line(theta, (2.0 * np.pi) / 96.0, 0.0046) * _ornate_ring(r, cell * 0.46, line * 1.25)
    micro = _ornate_micro_grit(shape, seed + 5580, 0.10) * np.clip(radial + flower + hex_field, 0.0, 1.0)
    pv = np.clip(radial * 0.36 + petals * 0.46 + lotus * 0.44 + spokes * 0.30 + hex_field * 0.24 + flower * 0.42 + beads * 0.58 + micro, 0.0, 1.0)
    return {"pattern_val": pv.astype(np.float32), "R_range": 80.0, "M_range": 40.0, "CC": None}


def texture_lace_filigree(shape, mask, seed, sm):
    """Lace filigree - open thread mesh with scalloped rosettes, knots, and woven crossings."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(10.0, sm * 30.0)
    fine = max(0.34, sm * 0.48)
    warp = (multi_scale_noise(shape, [8, 16, 32, 64], [0.30, 0.32, 0.24, 0.14], seed + 5520) - 0.5) * sm * 3.8
    mesh = (
        _ornate_periodic_line(xf + warp, cell * 0.245, fine) * 0.30
        + _ornate_periodic_line(yf - warp, cell * 0.245, fine) * 0.30
        + _ornate_periodic_line((xf + yf) * 0.707 + warp, cell * 0.345, fine * 0.70) * 0.24
        + _ornate_periodic_line((xf - yf) * 0.707 - warp, cell * 0.345, fine * 0.70) * 0.24
    )
    lx = (xf % cell) - cell * 0.5
    ly = (yf % cell) - cell * 0.5
    scallop = np.maximum(
        _ornate_ellipse(lx, ly, cell * 0.38, cell * 0.22, 0.032),
        _ornate_ellipse(lx, ly, cell * 0.18, cell * 0.38, 0.034),
    )
    rosette = _ornate_wave_ink(np.arctan2(ly, lx) * 8.0 + np.sqrt(lx * lx + ly * ly) * 0.28, 0.15)
    rosette *= _ornate_ellipse(lx, ly, cell * 0.32, cell * 0.32, 0.060)
    pin = np.clip(1.0 - (lx * lx + ly * ly) / max((cell * 0.055) ** 2, 1e-6), 0.0, 1.0)
    open_hole = np.clip(1.0 - np.sqrt((lx / (cell * 0.28)) ** 2 + (ly / (cell * 0.28)) ** 2), 0.0, 1.0)
    thread_grain = _ornate_micro_grit(shape, seed + 5581, 0.13) * np.clip(mesh + scallop, 0.0, 1.0)
    pv = np.clip(mesh + scallop * 0.50 + rosette * 0.34 + pin * 0.46 + thread_grain - open_hole * 0.22, 0.0, 1.0)
    return {"pattern_val": pv.astype(np.float32), "R_range": 75.0, "M_range": -35.0, "CC": None}


def texture_stained_glass_voronoi(shape, mask, seed, sm):
    """Stained glass - Voronoi panes with random luminance and dark grout-line boundaries."""
    h, w = shape
    n_cells = min(max(25, int(min(h, w) / max(1.0, sm * 5.5))), 100)
    rng = np.random.default_rng(seed + 5501)
    cell_id = _voronoi_cells_fast(shape, n_cells, 5501, seed)
    cell_lum = rng.uniform(0.3, 1.0, size=int(cell_id.max()) + 1).astype(np.float32)
    crack = _voronoi_cracks_fast(shape, n_cells, 5501, seed, crack_width=6.0)
    return {"pattern_val": (cell_lum[cell_id] * (1.0 - crack * 0.92)).astype(np.float32),
            "R_range": 55.0, "M_range": -45.0, "CC": None}


def texture_brushed_metal_fine(shape, mask, seed, sm):
    """Brushed metal fine - three-frequency anisotropic directional micro-scratch grain."""
    h, w = shape
    y, x = get_mgrid((h, w))
    xf = x.astype(np.float32)
    f1 = np.abs(np.sin(xf * 2.0 * np.pi / max(1.0, sm * 12.0)))
    f2 = np.abs(np.sin(xf * 2.0 * np.pi / max(1.0, sm * 5.0)))
    f3 = np.abs(np.sin(xf * 2.0 * np.pi / max(1.0, sm * 2.5)))
    noise = multi_scale_noise(shape, [8, 16], [0.6, 0.4], seed + 5502)
    v = (f1 * 0.5 + f2 * 0.3 + f3 * 0.2) + (noise + 1.0) * 0.04
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 50.0, "M_range": -65.0, "CC": None}


def texture_carbon_3k_weave(shape, mask, seed, sm):
    """Carbon 3K weave - two interleaved ±45° diagonal satin-braid tow directions."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    tow = max(1.0, sm * 9.0)
    d_a = (xf + yf) / tow
    d_b = (xf - yf) / tow + 0.5
    tow_a = np.sin(d_a * np.pi * 2.0) * 0.5 + 0.5
    tow_b = np.sin(d_b * np.pi * 2.0) * 0.5 + 0.5
    bundle = np.abs(np.sin(d_a * np.pi * 6.0)) * 0.15
    return {"pattern_val": np.clip((tow_a * 0.55 + tow_b * 0.45) * (0.85 + bundle), 0.0, 1.0).astype(np.float32),
            "R_range": 55.0, "M_range": -60.0, "CC": None}


def texture_honeycomb_organic(shape, mask, seed, sm):
    """Honeycomb organic - waxy irregular hex cells with ragged wall rims and pollen pores."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(12.0, sm * 28.0)
    warp = sm * 9.0
    wx = xf + (multi_scale_noise(shape, [10, 20, 40, 80], [0.28, 0.30, 0.27, 0.15], seed + 5504) - 0.5) * warp
    wy = yf + (multi_scale_noise(shape, [10, 20, 40, 80], [0.28, 0.30, 0.27, 0.15], seed + 5505) - 0.5) * warp
    wall = np.zeros((h, w), dtype=np.float32)
    for angle in (0.0, np.pi / 3.0, -np.pi / 3.0):
        coord = wx * np.cos(angle) + wy * np.sin(angle)
        wall = np.maximum(wall, _ornate_periodic_line(coord, cell, max(0.62, sm * 0.92)))
    inner_wall = np.zeros((h, w), dtype=np.float32)
    for angle in (np.pi / 6.0, np.pi / 2.0, -np.pi / 6.0):
        coord = wx * np.cos(angle) + wy * np.sin(angle)
        inner_wall = np.maximum(inner_wall, _ornate_periodic_line(coord, cell * 0.50, max(0.30, sm * 0.42)))
    membrane = _ornate_norm(multi_scale_noise(shape, [4, 8, 16, 32], [0.34, 0.28, 0.22, 0.16], seed + 5506))
    pore_x = (wx % (cell * 0.42)) - cell * 0.21
    pore_y = (wy % (cell * 0.42)) - cell * 0.21
    pores = np.clip(1.0 - np.sqrt(pore_x * pore_x + pore_y * pore_y) / max(cell * 0.035, 1e-6), 0.0, 1.0)
    rim_grit = _ornate_micro_grit(shape, seed + 5582, 0.16) * np.clip(wall + inner_wall * 0.45, 0.0, 1.0)
    pv = np.clip(wall * (0.78 + membrane * 0.34) + inner_wall * 0.18 + pores * 0.22 + membrane * 0.08 + rim_grit, 0.0, 1.0)
    return {"pattern_val": pv.astype(np.float32), "R_range": 65.0, "M_range": -50.0, "CC": None}


def texture_baroque_scrollwork(shape, mask, seed, sm):
    """Baroque scrollwork - acanthus S-scrolls, leaf engraving, gilded knots, and hatch shadow."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell_sz = max(26.0, sm * 72.0)
    lx = (xf % cell_sz) - cell_sz * 0.5
    ly = (yf % cell_sz) - cell_sz * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    theta = np.arctan2(ly, lx)
    scroll_a = _ornate_periodic_line(r - theta * cell_sz * 0.135, cell_sz * 0.265, max(0.46, sm * 0.72))
    scroll_b = _ornate_periodic_line(r + theta * cell_sz * 0.150, cell_sz * 0.235, max(0.42, sm * 0.66))
    s_curve = _ornate_periodic_line(lx - np.sin(ly / cell_sz * np.pi * 2.0) * cell_sz * 0.25, cell_sz * 0.55, max(0.54, sm * 0.74))
    leaf_angle = theta + np.sin(r / max(cell_sz * 0.18, 1.0)) * 0.85
    leaf = _ornate_ellipse(lx * np.cos(leaf_angle) - ly * np.sin(leaf_angle),
                           lx * np.sin(leaf_angle) + ly * np.cos(leaf_angle),
                           cell_sz * 0.30, cell_sz * 0.080, 0.042)
    vein = _ornate_periodic_line(lx * np.cos(leaf_angle) - ly * np.sin(leaf_angle), cell_sz * 0.075, max(0.24, sm * 0.30)) * leaf
    hatch = _ornate_periodic_line(xf * 0.82 + yf * 0.57 + np.sin(theta * 3.0) * 4.0, max(3.0, sm * 4.2), max(0.24, sm * 0.32)) * 0.24
    knot = np.clip(1.0 - r / max(cell_sz * 0.055, 1e-6), 0.0, 1.0)
    fade = np.clip(1.0 - (r / (cell_sz * 0.53)) ** 2.2, 0.0, 1.0)
    engraving = _ornate_micro_grit(shape, seed + 5583, 0.12) * np.clip(scroll_a + scroll_b + leaf, 0.0, 1.0)
    pv = np.clip((scroll_a * 0.58 + scroll_b * 0.50 + s_curve * 0.28 + leaf * 0.50 + vein * 0.30 + knot * 0.44) * fade + hatch * fade + engraving, 0.0, 1.0)
    return {"pattern_val": pv.astype(np.float32),
            "R_range": 70.0, "M_range": -40.0, "CC": None}


def texture_art_nouveau_vine(shape, mask, seed, sm):
    """Art Nouveau vine - sinuous botanical stems, almond leaves, seed pods, and hairline tendrils."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    period = max(24.0, sm * 76.0)
    lane = np.floor(xf / period)
    center = (lane + 0.5) * period + np.sin(yf / max(sm * 32.0, 1.0) + lane * 1.7) * sm * 12.0
    stem_dist = np.abs(xf - center)
    stem = np.clip(1.0 - stem_dist / max(0.55, sm * 0.95), 0.0, 1.0)
    leaf_step = max(sm * 28.0, 13.0)
    leaf_phase = np.mod(yf / leaf_step + lane * 0.5, 1.0)
    side = np.where(leaf_phase < 0.5, -1.0, 1.0)
    leaf_cx = center + side * period * 0.22
    leaf_cy = (np.floor(yf / leaf_step) + 0.5) * leaf_step
    leaf = _ornate_ellipse((xf - leaf_cx) * 0.88 + (yf - leaf_cy) * side * 0.34,
                           (yf - leaf_cy) * 0.88 - (xf - leaf_cx) * side * 0.34,
                           period * 0.17, max(sm * 5.4, 4.0), 0.045)
    vein = _ornate_periodic_line((xf - leaf_cx) * 0.84 + (yf - leaf_cy) * side * 0.38, period * 0.055, max(0.20, sm * 0.26)) * leaf
    tendril_coord = xf - center + np.sin(yf / max(sm * 12.0, 1.0)) * sm * 6.0
    tendril_gate = _ornate_periodic_line(yf + lane * period, max(sm * 22.0, 10.0), max(0.48, sm * 0.62))
    tendril = _ornate_periodic_line(tendril_coord, max(sm * 8.5, 4.5), max(0.28, sm * 0.36)) * tendril_gate
    pod_x = (xf - center - side * period * 0.08)
    pod_y = (yf - leaf_cy)
    pods = _ornate_ellipse(pod_x, pod_y, max(sm * 3.0, 2.0), max(sm * 6.0, 4.0), 0.070) * (leaf_phase > 0.18) * (leaf_phase < 0.82)
    bg = _ornate_norm(multi_scale_noise(shape, [8, 16, 32, 64], [0.30, 0.30, 0.24, 0.16], seed + 5510)) * 0.08
    grain = _ornate_micro_grit(shape, seed + 5584, 0.11) * np.clip(stem + leaf + tendril, 0.0, 1.0)
    pv = np.clip(bg + stem * 0.78 + leaf * 0.58 + vein * 0.30 + tendril * 0.40 + pods * 0.28 + grain, 0.0, 1.0).astype(np.float32)
    return {"pattern_val": pv, "R_range": 65.0, "M_range": -35.0, "CC": None}


def texture_penrose_quasi(shape, mask, seed, sm):
    """Penrose quasicrystal - fivefold aperiodic ridge net with star nodes and facet dust."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cx, cy = w * 0.5, h * 0.5
    xf = xf - cx
    yf = yf - cy
    period = max(9.0, sm * 25.0)
    line = max(0.34, sm * 0.50)
    ridges = np.zeros((h, w), dtype=np.float32)
    facets = np.zeros((h, w), dtype=np.float32)
    node_product = np.ones((h, w), dtype=np.float32)
    for k in range(5):
        angle = k * np.pi * 2.0 / 5.0
        cx_k, cy_k = np.cos(angle), np.sin(angle)
        proj = xf * cx_k + yf * cy_k + np.sin(k * 12.989 + seed) * period * 0.20
        r0 = _ornate_periodic_line(proj, period, line)
        r1 = _ornate_periodic_line(proj, period * 0.6180339, line * 0.62)
        r2 = _ornate_periodic_line(proj, period * 1.6180339, line * 0.46)
        ridges = np.maximum(ridges, r0)
        facets += r1 * 0.16 + r2 * 0.10
        node_product *= np.clip(r0 + 0.18, 0.0, 1.0)
    nodes = np.clip((ridges + facets - 0.92) * 2.8 + node_product * 1.3, 0.0, 1.0)
    star = _ornate_wave_ink(np.arctan2(yf, xf) * 10.0 + np.sqrt(xf * xf + yf * yf) * 0.045, 0.12) * _ornate_ring(np.sqrt(xf * xf + yf * yf), period * 0.84, line * 1.2)
    shimmer = _ornate_micro_grit(shape, seed + 5585, 0.16)
    pv = np.clip(ridges * 0.62 + facets * 0.56 + nodes * 0.42 + star * 0.24 + shimmer * np.clip(ridges + facets, 0, 1), 0.0, 1.0)
    return {"pattern_val": pv.astype(np.float32),
            "R_range": 75.0, "M_range": 45.0, "CC": None}


def texture_topographic_dense(shape, mask, seed, sm):
    """Topographic dense - dense contour ink, index lines, ravine ticks, and paper grain."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    height = _ornate_norm(multi_scale_noise(shape, [8, 16, 32, 64, 128], [0.28, 0.26, 0.22, 0.16, 0.08], seed + 5509))
    ridge = 0.22 * np.sin((xf * 0.030 + yf * 0.019) / max(sm, 0.2)) + 0.11 * np.sin((xf * -0.017 + yf * 0.041) / max(sm, 0.2))
    height = _ornate_norm(height + ridge)
    contour_count = 68.0 / max(sm ** 0.10, 0.85)
    contour = np.abs(np.sin(height * contour_count * np.pi))
    lines = np.clip(1.0 - contour / 0.050, 0.0, 1.0)
    index_lines = np.clip(1.0 - np.abs(np.sin(height * (contour_count / 5.0) * np.pi)) / 0.052, 0.0, 1.0) * 0.48
    hatch = _ornate_periodic_line(xf * 0.79 + yf * 0.61 + height * 24.0, max(3.0, sm * 5.0), max(0.22, sm * 0.28))
    slope = np.hypot(np.gradient(height, axis=1), np.gradient(height, axis=0))
    tick = _ornate_periodic_line(xf * -0.34 + yf * 0.94 + height * 13.0, max(2.4, sm * 3.6), max(0.18, sm * 0.23))
    paper = _ornate_micro_grit(shape, seed + 5586, 0.10)
    pv = np.clip(lines * 0.78 + index_lines + hatch * np.clip(slope * 16.0, 0.0, 1.0) * 0.34 + tick * np.clip(slope * 22.0, 0.0, 1.0) * 0.18 + height * 0.11 + paper, 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": 60.0, "M_range": -55.0, "CC": None}


def texture_interference_rings(shape, mask, seed, sm):
    """Newton ring interference - multi-source optical fringes with moire beat shimmer."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cx, cy = w * 0.5, h * 0.5
    off = min(h, w) * 0.17
    period = max(8.0, sm * 20.0)
    width = max(0.28, sm * 0.40)
    rings = np.zeros((h, w), dtype=np.float32)
    phases = []
    for i, (ox, oy) in enumerate(((off, 0.0), (-off, 0.0), (0.0, off), (0.0, -off), (off * 0.55, off * 0.55), (-off * 0.55, off * 0.55))):
        rr = np.sqrt((xf - cx + ox) ** 2 + (yf - cy + oy) ** 2)
        rr = rr + np.sin((xf + yf) * 0.012 + i * 1.7) * sm * 1.8
        rings = np.maximum(rings, _ornate_ring(rr, period, width))
        phases.append(np.cos(rr * 2.0 * np.pi / period + i * 0.73))
    beat = _ornate_norm(np.abs(np.mean(phases, axis=0)))
    micro = _ornate_ring(np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2), period * 0.381966, width * 0.55)
    fringe = _ornate_wave_ink((xf - cx) * 0.055 + np.sin((yf - cy) * 0.021) * 3.0, 0.11) * 0.16
    shimmer = _ornate_micro_grit(shape, seed + 5587, 0.11) * beat
    pv = np.clip(rings * 0.72 + beat * 0.28 + micro * 0.32 + fringe + shimmer, 0.0, 1.0)
    return {"pattern_val": pv.astype(np.float32), "R_range": 70.0, "M_range": 50.0, "CC": None}


# ── TRIBAL & ANCIENT — Texture functions (Batch 2, 2026-03-28) ──────────────

def texture_maori_koru(shape, mask, seed, sm):
    """Maori koru — tiled logarithmic spiral fern frond uncoiling in each cell."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell_sz = max(4.0, sm * 52.0)
    lx = (xf % cell_sz) - cell_sz * 0.5
    ly = (yf % cell_sz) - cell_sz * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    theta = np.arctan2(ly, lx)
    b = 0.18
    spiral_phase = np.log(r / max(1.0, cell_sz * 0.06)) - b * theta
    v = np.abs(np.sin(spiral_phase * np.pi * 2.0)) * 0.5 + 0.5
    fade = np.clip(1.0 - (r / (cell_sz * 0.48)) ** 4, 0.0, 1.0)
    return {"pattern_val": (v * fade).astype(np.float32), "R_range": 65.0, "M_range": -40.0, "CC": None}


def texture_polynesian_tapa(shape, mask, seed, sm):
    """Polynesian tapa cloth — alternating horizontal bands of zigzag vs crosshatch."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    band_h = max(4.0, sm * 20.0)
    band_idx = (yf / band_h).astype(np.int32)
    freq = 2.0 * np.pi / max(1.0, sm * 10.0)
    zigzag = np.abs(np.sin(xf * freq + (yf % band_h) * 0.15))
    cross = np.minimum(np.abs(np.sin(xf * freq)), np.abs(np.sin(yf * freq)))
    v = np.where((band_idx % 2) == 0, zigzag, cross * 1.4)
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 55.0, "M_range": -45.0, "CC": None}


def texture_aztec_sun(shape, mask, seed, sm):
    """Aztec sun stone — radial calendar wheel with spokes and concentric ring bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell_sz = max(4.0, sm * 56.0)
    lx = (xf % cell_sz) - cell_sz * 0.5
    ly = (yf % cell_sz) - cell_sz * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    theta = np.arctan2(ly, lx)
    r_norm = r / (cell_sz * 0.48)
    spokes = np.abs(np.sin(theta * 10.0)) ** 6
    rings = np.abs(np.sin(r_norm * 8.0 * np.pi)) ** 3
    v = (spokes * 0.55 + rings * 0.45) * np.clip(1.0 - r_norm ** 3, 0.0, 1.0)
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 70.0, "M_range": -50.0, "CC": None}


def texture_celtic_trinity(shape, mask, seed, sm):
    """Celtic triquetra — three interlocked ring arcs at 120° offsets in tiled cells."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell_sz = max(4.0, sm * 50.0)
    lx = (xf % cell_sz) - cell_sz * 0.5
    ly = (yf % cell_sz) - cell_sz * 0.5
    ring_r = cell_sz * 0.24
    ring_t = max(1.0, sm * 1.8)
    v = np.zeros((h, w), dtype=np.float32)
    for ang in [0.0, 2.094395, 4.18879]:
        cx_k = np.cos(ang) * ring_r * 0.55
        cy_k = np.sin(ang) * ring_r * 0.55
        dist = np.sqrt((lx - cx_k) ** 2 + (ly - cy_k) ** 2)
        ring = np.clip(1.0 - np.abs(dist - ring_r) / ring_t, 0.0, 1.0)
        v = np.maximum(v, ring)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2510) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v, "R_range": 70.0, "M_range": -35.0, "CC": None}


def texture_viking_knotwork(shape, mask, seed, sm):
    """Viking interlace — diagonal over-under strand braid with parity switching."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 22.0)
    strand_w = max(1.0, sm * 2.5)
    d1 = (xf + yf) / cell
    d2 = (xf - yf) / cell
    s1 = np.abs((d1 % 1.0) - 0.5) * cell
    s2 = np.abs((d2 % 1.0) - 0.5) * cell
    strand1 = np.clip(1.0 - s1 / strand_w, 0.0, 1.0)
    strand2 = np.clip(1.0 - s2 / strand_w, 0.0, 1.0)
    parity = ((d1.astype(np.int32) + d2.astype(np.int32)) % 2).astype(np.float32)
    v = strand1 * (0.5 + parity * 0.5) + strand2 * (0.5 + (1.0 - parity) * 0.5)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2690) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 65.0, "M_range": -45.0, "CC": None}


def texture_native_geometric(shape, mask, seed, sm):
    """Native American diamond blanket — L1 diamond lattice with alternating border stripes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 28.0)
    lx = (xf % cell) / cell - 0.5
    ly = (yf % cell) / cell - 0.5
    l1 = np.abs(lx) + np.abs(ly)
    diamond = (l1 < 0.36).astype(np.float32)
    stripe = np.abs(np.sin((xf + yf) * np.pi / max(1.0, sm * 7.0))) ** 8
    v = diamond * 0.7 + stripe * 0.3
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 60.0, "M_range": -50.0, "CC": None}


def texture_inca_step(shape, mask, seed, sm):
    """Inca step fret — L-shape step motif with alternating rotation in tiled cells."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 24.0)
    cx_i = (xf / cell).astype(np.int32)
    cy_i = (yf / cell).astype(np.int32)
    lx = (xf % cell) / cell
    ly = (yf % cell) / cell
    parity = (cx_i + cy_i) % 2
    lx_r = np.where(parity == 0, lx, 1.0 - ly)
    ly_r = np.where(parity == 0, ly, lx)
    arm_w = 0.18
    h_arm = ((ly_r < arm_w) & (lx_r > 0.1)).astype(np.float32)
    v_arm = ((lx_r < arm_w) & (ly_r < 0.7)).astype(np.float32)
    pv = np.clip(h_arm + v_arm, 0.0, 1.0)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2550) * 0.12 + 0.07
    pv = np.clip(pv + bg_fill, 0, 1)
    return {"pattern_val": pv, "R_range": 60.0, "M_range": -55.0, "CC": None}


def texture_aboriginal_dots(shape, mask, seed, sm):
    """Aboriginal concentric ring dot art — periodic ring clusters on a regular grid."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    spacing = max(4.0, sm * 30.0)
    ring_sp = max(1.0, sm * 4.5)
    dot_r = max(0.5, sm * 1.8)
    gx = np.round(xf / spacing) * spacing
    gy = np.round(yf / spacing) * spacing
    r = np.sqrt((xf - gx) ** 2 + (yf - gy) ** 2) + 0.001
    ring_phase = (r % ring_sp) / ring_sp
    rings = np.clip(1.0 - np.abs(ring_phase - 0.5) / (dot_r / ring_sp), 0.0, 1.0)
    rings *= (r < ring_sp * 3.5).astype(np.float32)
    return {"pattern_val": rings, "R_range": 55.0, "M_range": -40.0, "CC": None}


def texture_turkish_arabesque(shape, mask, seed, sm):
    """Ottoman arabesque — crossed sinusoidal lattice producing interlaced medallion lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    freq = 2.0 * np.pi / max(1.0, sm * 28.0)
    a = np.sin(xf * freq) * np.cos(yf * freq * 0.5)
    b = np.cos(xf * freq * 0.5) * np.sin(yf * freq)
    prod = np.abs(a * b)
    v = np.exp(-prod * 12.0)
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": -45.0, "CC": None}


def texture_eight_point_star(shape, mask, seed, sm):
    """8-pointed geometric star — four directional arm distances forming star tiling."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 36.0)
    lx = (xf % cell) - cell * 0.5
    ly = (yf % cell) - cell * 0.5
    arm_t = max(1.0, sm * 3.0)
    d_h = np.abs(ly)
    d_v = np.abs(lx)
    d_d1 = np.abs(lx + ly) * 0.707
    d_d2 = np.abs(lx - ly) * 0.707
    min_dist = np.minimum(np.minimum(d_h, d_v), np.minimum(d_d1, d_d2))
    star = np.clip(1.0 - min_dist / arm_t, 0.0, 1.0)
    r = np.sqrt(lx ** 2 + ly ** 2)
    center = np.clip(1.0 - (r - cell * 0.08) / max(1.0, sm * 1.5), 0.0, 1.0)
    return {"pattern_val": np.clip(star + center * 0.5, 0.0, 1.0).astype(np.float32),
            "R_range": 70.0, "M_range": -50.0, "CC": None}


def texture_egyptian_lotus(shape, mask, seed, sm):
    """Egyptian lotus frieze — radial teardrop petal cluster with center stalk."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 44.0)
    lx = (xf % cell) - cell * 0.5
    ly = (yf % cell) - cell * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    theta = np.arctan2(lx, -ly)
    n_petals = 6
    petal_r = cell * 0.30
    petal_angle = (theta % (2.0 * np.pi / n_petals)) - np.pi / n_petals
    radial_hit = np.abs(r - petal_r * 0.7)
    angular_hit = np.abs(petal_angle) * r
    petal = np.clip(1.0 - (radial_hit * 0.06 + angular_hit * 0.08) / max(0.01, sm * 2.5), 0.0, 1.0)
    stalk = np.clip(1.0 - (np.abs(lx) * 4.0 + np.maximum(0.0, -ly) * 0.05) / max(1.0, sm * 3.0), 0.0, 1.0)
    return {"pattern_val": np.clip(petal * 0.8 + stalk * 0.3, 0.0, 1.0).astype(np.float32),
            "R_range": 60.0, "M_range": -40.0, "CC": None}


def texture_chinese_cloud(shape, mask, seed, sm):
    """Chinese ruyi cloud scroll — L-inf rectangular ring spirals with softened corners."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 40.0)
    lx = (xf % cell) - cell * 0.5
    ly = (yf % cell) - cell * 0.5
    l_inf = np.maximum(np.abs(lx), np.abs(ly))
    ring_sp = max(1.0, sm * 5.5)
    ring_phase = (l_inf % ring_sp) / ring_sp
    rings = (np.sin(ring_phase * np.pi * 2.0) * 0.5 + 0.5) ** 2
    l2 = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    corner_blend = np.clip((l_inf - l2 * 0.85) / max(0.01, cell * 0.08), 0.0, 1.0)
    v = rings * (1.0 - corner_blend * 0.5)
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 60.0, "M_range": -45.0, "CC": None}


# ── NATURAL TEXTURES — Texture functions (Batch 3, 2026-03-28) ──────────────

def texture_marble_veining(shape, mask, seed, sm):
    """Marble veining — turbulence-warped sine vein network with secondary frequency."""
    h, w = shape
    y, x = get_mgrid((h, w))
    xf = x.astype(np.float32)
    noise1 = multi_scale_noise(shape, [8, 16, 32, 64, 128], [0.40, 0.30, 0.15, 0.10, 0.05], seed + 6001)
    noise2 = multi_scale_noise(shape, [8, 16, 32, 64],     [0.50, 0.30, 0.15, 0.05],       seed + 6002)
    freq = 2.0 * np.pi / max(1.0, sm * 60.0)
    v1 = np.abs(np.sin(xf * freq + noise1 * 8.0 + noise2 * 3.0))
    v2 = np.abs(np.sin(xf * freq * 2.3 + noise1 * 5.0))
    return {"pattern_val": np.clip(v1 * 0.6 + v2 * 0.4, 0.0, 1.0).astype(np.float32),
            "R_range": 55.0, "M_range": -45.0, "CC": None}


def texture_wood_burl(shape, mask, seed, sm):
    """Wood burl — multiple swirling concentric ring centers warped by noise."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    rng = np.random.default_rng(seed + 6003)
    n_burls = 3
    cx_arr = rng.uniform(w * 0.15, w * 0.85, size=n_burls).astype(np.float32)
    cy_arr = rng.uniform(h * 0.15, h * 0.85, size=n_burls).astype(np.float32)
    warp = multi_scale_noise(shape, [16, 32, 64], [0.50, 0.35, 0.15], seed + 6004) * (sm * 25.0)
    ring_sp = max(1.0, sm * 8.0)
    v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_burls):
        wx = (xf + warp) - cx_arr[i]
        wy = (yf + warp * 0.7) - cy_arr[i]
        r = np.sqrt(wx ** 2 + wy ** 2)
        rings = np.abs(np.sin(r * np.pi / ring_sp))
        v = np.maximum(v, rings)
    return {"pattern_val": v, "R_range": 50.0, "M_range": -55.0, "CC": None}


def texture_seigaiha_scales(shape, mask, seed, sm):
    """Japanese seigaiha v2 — nested concentric arcs (3 rings per cell) with overlap.
    True seigaiha has multiple rings per scale, not just one. Added gradient fill."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    scale_w = max(8.0, sm * 36.0)
    row_h = scale_w * 0.30
    ring_t = max(0.8, sm * 2.0)
    row_i = (yf / row_h).astype(np.int32)
    offset = (row_i % 2) * (scale_w * 0.5)
    lx = ((xf + offset) % scale_w) - scale_w * 0.5
    ly = (yf % row_h)
    r = np.sqrt(lx ** 2 + (ly + scale_w * 0.05) ** 2)
    # 3 concentric arcs per cell (the actual seigaiha pattern)
    arc1 = np.clip(1.0 - np.abs(r - scale_w * 0.48) / ring_t, 0, 1)
    arc2 = np.clip(1.0 - np.abs(r - scale_w * 0.36) / ring_t, 0, 1) * 0.8
    arc3 = np.clip(1.0 - np.abs(r - scale_w * 0.24) / ring_t, 0, 1) * 0.6
    arcs = np.maximum(np.maximum(arc1, arc2), arc3)
    # Radial gradient fill between rings
    fill = np.clip(1.0 - r / (scale_w * 0.5), 0, 1) * 0.25
    # Upper hemisphere mask
    upper = np.clip(1.0 - ly / (row_h * 0.85), 0, 1)
    result = np.clip((arcs + fill) * upper, 0, 1)
    return {"pattern_val": result.astype(np.float32), "R_range": 65.0, "M_range": -40.0, "CC": None}


def texture_ammonite_chambers(shape, mask, seed, sm):
    """Ammonite chambers — log-spiral shell walls with radial suture divisions."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cx, cy = w * 0.5, h * 0.5
    lx, ly = xf - cx, yf - cy
    r = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    theta = np.arctan2(ly, lx)
    b = 0.22
    min_r = max(1.0, min(w, h) * 0.03)
    log_r = np.log(np.maximum(r, min_r))
    spiral_val = log_r / b - theta / (2.0 * np.pi)
    # Chamber walls
    walls = np.abs(np.sin(spiral_val * np.pi * 2.0))
    # Radial sutures
    n_chambers = 8
    suture = np.abs(np.sin(theta * n_chambers)) ** 10
    v = walls * 0.65 + suture * 0.35
    max_r = min(w, h) * 0.46
    fade = np.clip(1.0 - (r / max_r) ** 3, 0.0, 1.0)
    return {"pattern_val": np.clip(v * fade, 0.0, 1.0).astype(np.float32),
            "R_range": 65.0, "M_range": -50.0, "CC": None}


def texture_peacock_eye(shape, mask, seed, sm):
    """Peacock feather eye — elliptical concentric rings with 20-barb radial overlay."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 52.0)
    lx = (xf % cell) - cell * 0.5
    ly = (yf % cell) - cell * 0.5
    r = np.sqrt(lx ** 2 + (ly * 1.3) ** 2) + 0.001
    theta = np.arctan2(ly, lx)
    ring_sp = max(1.0, sm * 5.0)
    rings = np.abs(np.sin(r * np.pi / ring_sp))
    n_barbs = 20
    barbs = np.abs(np.sin(theta * n_barbs * 0.5)) ** 10
    center = np.clip(1.0 - r / max(1.0, cell * 0.08), 0.0, 1.0)
    v = rings * (0.55 + barbs * 0.45) + center * 0.75  # Slightly brighter center
    fade = np.clip(1.0 - (r / (cell * 0.46)) ** 3, 0.0, 1.0)
    pv = np.clip(v * fade, 0, 1)
    # Fine iridescence grain
    grain = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 100)
    pv = np.clip(pv + np.where(pv > 0.02, grain * 0.04, 0), 0, 1)
    return {"pattern_val": pv.astype(np.float32), "R_range": 70.0, "M_range": -45.0, "CC": None}


def texture_dragonfly_wing(shape, mask, seed, sm):
    """Dragonfly wing venation — dense Voronoi cell cracks for thin wing veins."""
    h, w = shape
    n_cells = min(max(60, int(min(h, w) / max(1.0, sm * 3.5))), 200)
    cracks = _voronoi_cracks_fast(shape, n_cells, 6006, seed, crack_width=3.0)
    bg = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1930) * 0.12 + 0.07
    cracks = np.clip(cracks + bg, 0, 1)
    return {"pattern_val": cracks.astype(np.float32), "R_range": 60.0, "M_range": -50.0, "CC": None}


def texture_insect_compound(shape, mask, seed, sm):
    """Insect compound eye — hex close-packed ommatidia with ring + center dot."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    hex_w = max(4.0, sm * 20.0)
    hex_h = hex_w * 0.866025
    row_i = (yf / hex_h).astype(np.int32)
    offset = (row_i % 2) * (hex_w * 0.5)
    lx = ((xf + offset) % hex_w) - hex_w * 0.5
    ly = (yf % hex_h) - hex_h * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2)
    omm_r = hex_w * 0.42
    ring_t = max(0.5, sm * 1.5)
    ring = np.clip(1.0 - np.abs(r - omm_r) / ring_t, 0.0, 1.0)
    center = np.clip(1.0 - r / (omm_r * 0.55), 0.0, 1.0) * 0.35
    return {"pattern_val": np.clip(ring + center, 0.0, 1.0).astype(np.float32),
            "R_range": 65.0, "M_range": -50.0, "CC": None}


def texture_diatom_radial(shape, mask, seed, sm):
    """Diatom microorganism — 16-fold radial symmetry with spokes, rings, and dots."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 50.0)
    lx = (xf % cell) - cell * 0.5
    ly = (yf % cell) - cell * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    theta = np.arctan2(ly, lx)
    n_spokes = 16
    spokes = np.abs(np.sin(theta * n_spokes * 0.5)) ** 8
    ring_sp = max(1.0, sm * 5.5)
    rings = (np.sin(r * np.pi / ring_sp) * 0.5 + 0.5) ** 4
    dot_phase = np.abs(np.sin(theta * n_spokes * 0.5 + r * 0.25)) ** 8
    fade = np.clip(1.0 - (r / (cell * 0.48)) ** 4, 0.0, 1.0)
    v = (spokes * 0.35 + rings * 0.40 + dot_phase * 0.25) * fade
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 70.0, "M_range": 50.0, "CC": None}


def texture_coral_polyp(shape, mask, seed, sm):
    """Coral polyp tiling — 8-tentacle radial star with concentric oral disk rings."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 30.0)
    lx = (xf % cell) - cell * 0.5
    ly = (yf % cell) - cell * 0.5
    r = np.sqrt(lx ** 2 + ly ** 2) + 0.001
    theta = np.arctan2(ly, lx)
    n_tentacles = 8
    tentacles = (np.cos(theta * n_tentacles) * 0.5 + 0.5) ** 4
    radial_fade = np.clip(1.0 - r / (cell * 0.46), 0.0, 1.0)
    ring_sp = max(1.0, sm * 6.0)
    disk = np.abs(np.sin(r * np.pi * 2.0 / ring_sp))
    v = disk * 0.4 + tentacles * radial_fade * 0.6
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 60.0, "M_range": -40.0, "CC": None}


def texture_birch_bark(shape, mask, seed, sm):
    """Birch bark — noise-warped horizontal lenticel bands with vertical cracks."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    noise_h = multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 6010) * (sm * 15.0)
    lenticel_freq = max(1.0, sm * 25.0)
    # Lenticels: dark horizontal bands
    lenticels = (np.abs(np.sin((yf + noise_h * 0.3) * np.pi / lenticel_freq)) < 0.10).astype(np.float32)
    noise_v = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed + 6011) * (sm * 20.0)
    crack_freq = max(1.0, sm * 40.0)
    # Vertical cracks: thin sinuous lines
    cracks = (np.abs(np.sin((xf + noise_v) * np.pi / crack_freq)) < 0.05).astype(np.float32)
    # Base is mostly bright (white birch)
    grain = (multi_scale_noise(shape, [8, 16], [0.6, 0.4], seed + 6012) * 0.12 + 0.88).astype(np.float32)
    v = grain * (1.0 - lenticels * 0.85) * (1.0 - cracks * 0.55)  # Stronger features (was 0.75/0.45)
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 45.0, "M_range": -65.0, "CC": None}


def texture_pine_cone_scale(shape, mask, seed, sm):
    """Pine cone scale — dual diagonal sine families forming interlocked diamond tiles."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell = max(4.0, sm * 28.0)
    # Two diagonal families at ±35°
    proj1 = xf * 0.81915 + yf * 0.57358   # cos35, sin35
    proj2 = xf * 0.81915 - yf * 0.57358   # cos-35, sin-35
    s1 = np.abs(np.sin(proj1 * np.pi / cell))
    s2 = np.abs(np.sin(proj2 * np.pi / cell))
    # Minimum gives raised ridges at diamond intersections
    v = np.minimum(s1, s2)
    return {"pattern_val": np.clip(1.0 - v * 2.2, 0.0, 1.0).astype(np.float32),
            "R_range": 60.0, "M_range": -50.0, "CC": None}


def texture_geode_crystal(shape, mask, seed, sm):
    """Geode crystal facets — Voronoi cells with per-facet directional sheen lines."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    n_crystals = min(max(8, int(min(h, w) / max(1.0, sm * 10.0))), 40)
    cell_id = _voronoi_cells_fast(shape, n_crystals, 6012, seed)
    cracks = _voronoi_cracks_fast(shape, n_crystals, 6012, seed, crack_width=4.0)
    rng = np.random.default_rng(seed + 6012)
    n_cells = int(cell_id.max()) + 1
    cell_angle = rng.uniform(0.0, np.pi, size=n_cells).astype(np.float32)
    angle = cell_angle[cell_id]
    dirx = np.cos(angle)
    diry = np.sin(angle)
    facet_sp = max(1.0, sm * 4.0)
    facet_lines = np.abs(np.sin((xf * dirx + yf * diry) * np.pi / facet_sp))
    v = facet_lines * (1.0 - cracks * 0.88)
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 80.0, "M_range": 55.0, "CC": None}


# ── TECH & CIRCUIT — Texture functions (Batch 4, 2026-03-28) ──────────────

def texture_circuit_traces(shape, mask, seed, sm):
    """PCB circuit board — orthogonal grid traces with via pad rings at intersections."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    pitch = np.float32(max(6.0, sm * 22.0))
    tw    = np.float32(max(1.5, sm * 2.5))
    xmod  = xf % pitch
    ymod  = yf % pitch
    h_tr  = np.clip((tw - np.abs(ymod - pitch * np.float32(0.5))) / tw, 0.0, 1.0)
    v_tr  = np.clip((tw - np.abs(xmod - pitch * np.float32(0.5))) / tw, 0.0, 1.0)
    traces = np.maximum(h_tr, v_tr)
    pad_r  = tw * np.float32(3.2)
    cx     = xmod - pitch * np.float32(0.5)
    cy     = ymod - pitch * np.float32(0.5)
    d_node = np.sqrt(cx ** 2 + cy ** 2)
    outer  = np.clip((pad_r - d_node) / tw, 0.0, 1.0)
    inner  = np.clip((d_node - pad_r * np.float32(0.45)) / tw, 0.0, 1.0)
    pad    = outer * inner
    return {"pattern_val": np.maximum(traces, pad * np.float32(0.9)).astype(np.float32),
            "R_range": 80.0, "M_range": 65.0, "CC": None}


def texture_hex_circuit(shape, mask, seed, sm):
    """Hexagonal circuit grid — three-direction parallel lines forming hex trace network."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    spacing = np.float32(max(8.0, sm * 20.0))
    tw      = np.float32(max(1.5, sm * 2.0))
    sqrt3   = np.float32(1.7320508)
    dirs = [(np.float32(0.0),           np.float32(1.0)),
            (sqrt3 * np.float32(0.5),   np.float32(0.5)),
            (sqrt3 * np.float32(0.5),   np.float32(-0.5))]
    v = np.zeros((h, w), dtype=np.float32)
    for bx, by in dirs:
        proj = xf * bx + yf * by
        mod  = proj % spacing
        dist = np.minimum(mod, spacing - mod)
        v    = np.maximum(v, np.clip((tw - dist) / tw, 0.0, 1.0))
    return {"pattern_val": v, "R_range": 75.0, "M_range": 55.0, "CC": None}


def texture_biomech_cables(shape, mask, seed, sm):
    """Biomechanical cable bundles — sinusoidal twisted cables with circumferential ribs."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cable_w    = np.float32(max(6.0, sm * 16.0))
    cable_r    = np.float32(max(1.5, sm * 2.5))
    twist_freq = np.float32(2.0 * np.pi / max(1.0, sm * 50.0))
    rib_freq   = np.float32(2.0 * np.pi / max(1.0, sm * 10.0))
    cable_idx  = np.floor(xf / cable_w).astype(np.float32)
    lx         = xf % cable_w
    parity     = (cable_idx % np.float32(2.0)) * np.float32(np.pi)
    twist      = np.sin(yf * twist_freq + cable_idx * np.float32(1.57) + parity) * (cable_w * np.float32(0.3))
    dist       = np.abs(lx - cable_w * np.float32(0.5) - twist)
    body       = np.clip((cable_r - dist) / cable_r, 0.0, 1.0)
    rib        = np.abs(np.cos(yf * rib_freq)).astype(np.float32) ** 6
    v          = body * (np.float32(0.55) + rib * np.float32(0.45))
    bg = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1970) * 0.13 + 0.08
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 40.0, "CC": None}


def texture_dendrite_web(shape, mask, seed, sm):
    """Dendrite web — multi-scale fractal branching vein network."""
    n_main = min(max(12, int(min(shape[0], shape[1]) / max(1.0, sm * 12.0))), 60)
    n_fine = min(max(40, int(min(shape[0], shape[1]) / max(1.0, sm * 5.0))), 180)
    c_main = _voronoi_cracks_fast(shape, n_main, 7004, seed, crack_width=4.0)
    c_fine = _voronoi_cracks_fast(shape, n_fine,  7005, seed, crack_width=2.0)
    v = np.maximum(c_main * np.float32(0.9), c_fine * np.float32(0.6))
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1910) * 0.14 + 0.08
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 55.0, "M_range": -30.0, "CC": None}


def texture_crystal_lattice(shape, mask, seed, sm):
    """Crystal lattice — 45°-rotated diamond rhombus grid with atom nodes at vertices."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    pitch   = np.float32(max(8.0, sm * 22.0))
    tw      = np.float32(max(1.5, sm * 2.5))
    inv_r2  = np.float32(0.7071068)
    u       = (xf + yf) * inv_r2
    vc      = (xf - yf) * inv_r2
    umod    = u  % pitch
    vcmod   = vc % pitch
    u_line  = np.clip((tw - np.minimum(umod, pitch - umod)) / tw, 0.0, 1.0)
    v_line  = np.clip((tw - np.minimum(vcmod, pitch - vcmod)) / tw, 0.0, 1.0)
    du      = np.minimum(umod, pitch - umod)
    dv      = np.minimum(vcmod, pitch - vcmod)
    d_node  = np.sqrt(du ** 2 + dv ** 2)
    node    = np.clip((tw * np.float32(3.5) - d_node) / tw, 0.0, 1.0)
    v       = np.maximum(np.maximum(u_line, v_line), node)
    return {"pattern_val": v.astype(np.float32), "R_range": 80.0, "M_range": 55.0, "CC": None}


def texture_chainmail_hex(shape, mask, seed, sm):
    """Hex chainmail — interlocking circular wire rings in hexagonal close-pack arrangement."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    ring_r  = np.float32(max(5.0, sm * 12.0))
    ring_tw = np.float32(max(1.5, sm * 2.0))
    sqrt3   = np.float32(1.7320508)
    col_p   = ring_r * np.float32(1.85)
    row_p   = col_p * sqrt3 * np.float32(0.5)
    ex  = xf % col_p - col_p * np.float32(0.5)
    ey  = yf % row_p - row_p * np.float32(0.5)
    er  = np.sqrt(ex ** 2 + ey ** 2)
    ox  = (xf + col_p * np.float32(0.5)) % col_p - col_p * np.float32(0.5)
    oy  = (yf + row_p * np.float32(0.5)) % row_p - row_p * np.float32(0.5)
    or_ = np.sqrt(ox ** 2 + oy ** 2)
    even = np.clip((ring_tw - np.abs(er  - ring_r)) / ring_tw, 0.0, 1.0)
    odd  = np.clip((ring_tw - np.abs(or_ - ring_r)) / ring_tw, 0.0, 1.0)
    return {"pattern_val": np.maximum(even, odd).astype(np.float32),
            "R_range": 70.0, "M_range": 50.0, "CC": None}


def texture_graphene_hex(shape, mask, seed, sm):
    """Graphene lattice — honeycomb bond network with atom nodes at unit cell positions."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    sqrt3   = np.float32(1.7320508)
    bond    = np.float32(max(4.0, sm * 10.0))
    spacing = bond * sqrt3
    tw      = np.float32(max(0.8, sm * 1.5))
    atom_r  = np.float32(max(1.5, sm * 2.2))
    v = np.zeros((h, w), dtype=np.float32)
    for angle_deg in (0.0, 60.0, 120.0):
        a    = float(angle_deg) * np.pi / 180.0
        bx   = np.float32(np.cos(a))
        by   = np.float32(np.sin(a))
        proj = xf * bx + yf * by
        mod  = proj % spacing
        dist = np.minimum(mod, spacing - mod)
        v    = np.maximum(v, np.clip((tw - dist) / tw, 0.0, 1.0))
    a_val = bond * sqrt3
    b_val = bond * np.float32(1.5)
    for sx, sy in ((np.float32(0.0), np.float32(0.0)),
                   (a_val * np.float32(0.5), b_val * np.float32(0.333))):
        dx   = ((xf - sx) + a_val * np.float32(0.5)) % a_val - a_val * np.float32(0.5)
        dy   = ((yf - sy) + b_val * np.float32(0.5)) % b_val - b_val * np.float32(0.5)
        dist = np.sqrt(dx ** 2 + dy ** 2)
        v    = np.maximum(v, np.clip((atom_r - dist) / atom_r, 0.0, 1.0))
    return {"pattern_val": v.astype(np.float32), "R_range": 75.0, "M_range": 55.0, "CC": None}


def texture_gear_mesh(shape, mask, seed, sm):
    """Interlocking gear mesh — toothed circular gear with spokes and hub, tiled."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    gear_r   = np.float32(max(8.0, sm * 18.0))
    cell_sz  = gear_r * np.float32(2.3)
    n_teeth  = max(8, int(float(gear_r) / 2.5))
    tooth_h  = np.float32(max(1.5, sm * 2.5))
    rim_tw   = np.float32(max(1.2, sm * 1.8))
    n_spokes = max(4, n_teeth // 2)
    lx    = xf % cell_sz - cell_sz * np.float32(0.5)
    ly    = yf % cell_sz - cell_sz * np.float32(0.5)
    r     = np.sqrt(lx ** 2 + ly ** 2) + np.float32(0.001)
    theta = np.arctan2(ly, lx).astype(np.float32)
    tooth_mod = np.sin(theta * np.float32(n_teeth)) * tooth_h
    rim       = np.clip((rim_tw - np.abs(r - gear_r - tooth_mod)) / rim_tw, 0.0, 1.0)
    hub_r     = gear_r * np.float32(0.22)
    hub       = np.clip((rim_tw - np.abs(r - hub_r)) / rim_tw, 0.0, 1.0)
    hub_fill  = np.clip((hub_r * np.float32(0.45) - r) / (hub_r * np.float32(0.45)), 0.0, 1.0)
    sp_period = np.float32(2.0 * np.pi / n_spokes)
    sp_phase  = theta % sp_period
    sp_dist   = np.minimum(sp_phase, sp_period - sp_phase)
    sp_tw_rad = np.clip(rim_tw / r, np.float32(0.0), np.float32(0.4))
    between   = (r > hub_r * np.float32(1.5)) & (r < gear_r - tooth_h * np.float32(1.5))
    spokes    = np.where(between,
                         np.clip((sp_tw_rad - sp_dist) / np.maximum(sp_tw_rad, np.float32(1e-4)), 0.0, 1.0),
                         np.float32(0.0))
    v = np.maximum(np.maximum(rim, hub), np.maximum(hub_fill * np.float32(0.7), spokes))
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2600) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 70.0, "M_range": 50.0, "CC": None}


def texture_vinyl_record(shape, mask, seed, sm):
    """Vinyl record — ultra-fine concentric groove rings with label ring and spindle hole."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell_sz    = np.float32(max(16.0, sm * 50.0))
    lx         = xf % cell_sz - cell_sz * np.float32(0.5)
    ly         = yf % cell_sz - cell_sz * np.float32(0.5)
    r          = np.sqrt(lx ** 2 + ly ** 2) + np.float32(0.001)
    groove_p   = np.float32(max(2.5, sm * 3.5))
    groove_tw  = np.float32(max(0.5, sm * 0.8))
    groove_mod = r % groove_p
    gr_dist    = np.minimum(groove_mod, groove_p - groove_mod)
    grooves    = np.clip((groove_tw - gr_dist) / groove_tw, 0.0, 1.0)
    label_r    = cell_sz * np.float32(0.25)
    grooves    = np.where(r < label_r, np.float32(0.3), grooves)
    lr_tw      = groove_tw * np.float32(2.0)
    label_ring = np.clip((lr_tw - np.abs(r - label_r)) / lr_tw, 0.0, 1.0)
    hole_r     = cell_sz * np.float32(0.04)
    v          = np.where(r < hole_r, np.float32(0.0), grooves)
    v          = np.maximum(v, label_ring * np.float32(0.8))
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32),
            "R_range": 55.0, "M_range": 35.0, "CC": None}


def texture_fiber_optic(shape, mask, seed, sm):
    """Fiber optic bundle — genuine hex-packed fiber cross-sections with per-fiber random
    brightness, cladding dark boundary ring, and TIR off-center bright spot per fiber.
    Visually distinct from chainmail_hex: varied luminance, dark cladding, TIR highlights."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    sqrt3   = np.float32(1.7320508)
    # Fiber geometry — ~8px diameter fiber at sm=1
    fiber_r  = np.float32(max(4.0, sm * 9.0))
    col_p    = fiber_r * np.float32(2.05)   # tight hex packing
    row_p    = col_p * sqrt3 * np.float32(0.5)
    core_r   = fiber_r * np.float32(0.68)   # glass core radius
    clad_w   = fiber_r * np.float32(0.18)   # cladding band width
    tir_r    = core_r * np.float32(0.28)    # TIR spot radius

    # --- Sublattice A: even rows ---
    col_a = np.floor(xf / col_p).astype(np.int32)
    row_a = np.floor(yf / row_p).astype(np.int32)
    lx_a  = xf - (col_a.astype(np.float32) + np.float32(0.5)) * col_p
    ly_a  = yf - (row_a.astype(np.float32) + np.float32(0.5)) * row_p
    dist_a = np.sqrt(lx_a ** 2 + ly_a ** 2)

    # --- Sublattice B: offset by (col_p/2, row_p/2) ---
    col_b = np.floor((xf - col_p * np.float32(0.5)) / col_p).astype(np.int32)
    row_b = np.floor((yf - row_p * np.float32(0.5)) / row_p).astype(np.int32)
    lx_b  = (xf - col_p * np.float32(0.5)) - (col_b.astype(np.float32) + np.float32(0.5)) * col_p
    ly_b  = (yf - row_p * np.float32(0.5)) - (row_b.astype(np.float32) + np.float32(0.5)) * row_p
    dist_b = np.sqrt(lx_b ** 2 + ly_b ** 2)

    # Pick nearest fiber center for each pixel
    use_b    = dist_b < dist_a
    nearest  = np.where(use_b, dist_b, dist_a)
    fiber_cx = np.where(use_b,
                        (col_b.astype(np.float32) + np.float32(0.5)) * col_p + col_p * np.float32(0.5),
                        (col_a.astype(np.float32) + np.float32(0.5)) * col_p)
    fiber_cy = np.where(use_b,
                        (row_b.astype(np.float32) + np.float32(0.5)) * row_p + row_p * np.float32(0.5),
                        (row_a.astype(np.float32) + np.float32(0.5)) * row_p)
    cell_col = np.where(use_b, col_b, col_a)
    cell_row = np.where(use_b, row_b + np.int32(1000), row_a)

    # Per-fiber brightness (fiber_id hash → pseudo-random 0.3–1.0)
    fid       = (cell_col.astype(np.int64) * np.int64(1619) +
                 cell_row.astype(np.int64) * np.int64(31337) +
                 np.int64(int(seed) & 0xFFFF)).astype(np.int64)
    fid_norm  = ((fid * np.int64(6364136223846793005) + np.int64(1442695040888963407)) >> np.int64(33)
                 & np.int64(0x7FFFFFFF)).astype(np.float32) / np.float32(0x7FFFFFFF)
    fiber_bright = np.float32(0.3) + fid_norm * np.float32(0.7)

    # Per-fiber TIR offset (small off-center bright spot — varies per fiber)
    tir_ox = (((fid * np.int64(2246822519)) >> np.int64(33) & np.int64(0x7FFFFFFF)).astype(np.float32)
              / np.float32(0x7FFFFFFF) - np.float32(0.5)) * core_r * np.float32(1.1)
    tir_oy = (((fid * np.int64(3266489917)) >> np.int64(33) & np.int64(0x7FFFFFFF)).astype(np.float32)
              / np.float32(0x7FFFFFFF) - np.float32(0.5)) * core_r * np.float32(1.1)
    tir_dist = np.sqrt((xf - fiber_cx - tir_ox) ** 2 + (yf - fiber_cy - tir_oy) ** 2)

    # Radial zones within each fiber
    in_fiber   = nearest < fiber_r                           # within total fiber area
    in_core    = nearest < core_r                            # glass core (light guides here)
    in_clad    = (nearest >= core_r) & (nearest < fiber_r)  # cladding (dark absorber)
    # Core: bright gradient, modulated by per-fiber brightness
    core_val   = np.clip((core_r - nearest) / np.maximum(core_r, np.float32(1e-4)), 0.0, 1.0)
    core_out   = core_val * fiber_bright
    # Cladding: dark ring — cladding absorbs evanescent light, boundary is the darkest zone
    clad_dist_inner = nearest - core_r          # 0 at core boundary, clad_w at outer
    clad_val   = np.clip(clad_dist_inner / np.maximum(clad_w, np.float32(1e-4)), 0.0, 1.0)
    # 0 at core edge → 1 at outer edge; invert: dark at edges of core, dark at outer rim
    clad_dark  = np.float32(1.0) - np.abs(clad_val * np.float32(2.0) - np.float32(1.0))
    clad_out   = np.float32(0.04) + clad_dark * np.float32(0.0)  # essentially black
    # TIR highlight: bright off-center spot within core only
    tir_spot   = np.clip((tir_r - tir_dist) / np.maximum(tir_r, np.float32(1e-4)), 0.0, 1.0)
    tir_out    = tir_spot * np.float32(0.55) * fiber_bright

    # Compose: outside fibers = near-black inter-fiber gap
    v = np.where(in_core,
                 np.clip(core_out + tir_out, 0.0, 1.0),
                 np.where(in_clad,
                          clad_out,
                          np.float32(0.02)))
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_sonar_ping(shape, mask, seed, sm):
    """Sonar/radar ping — expanding concentric rings from multiple offset source points."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    n_src   = min(max(2, int(min(h, w) / max(1.0, sm * 60.0))), 5)
    rng     = np.random.default_rng(seed + 7011)
    src_x   = rng.uniform(w * 0.15, w * 0.85, size=n_src).astype(np.float32)
    src_y   = rng.uniform(h * 0.15, h * 0.85, size=n_src).astype(np.float32)
    ring_p  = np.float32(max(8.0, sm * 22.0))
    ring_tw = np.float32(max(1.5, sm * 2.5))
    fade_sc = np.float32(1.0 / max(1.0, sm * 80.0))
    v = np.zeros((h, w), dtype=np.float32)
    for sx, sy in zip(src_x, src_y):
        dx   = xf - np.float32(sx)
        dy   = yf - np.float32(sy)
        r    = np.sqrt(dx ** 2 + dy ** 2)
        mod  = r % ring_p
        rd   = np.minimum(mod, ring_p - mod)
        fade = np.exp(-r * fade_sc).astype(np.float32)
        ring = np.clip((ring_tw - rd) / ring_tw, 0.0, 1.0) * (np.float32(0.5) + fade * np.float32(0.5))
        v    = np.maximum(v, ring)
    return {"pattern_val": v.astype(np.float32), "R_range": 60.0, "M_range": 40.0, "CC": None}


def texture_waveform_stack(shape, mask, seed, sm):
    """Waveform stack — multiple layered oscilloscope sine traces offset vertically."""
    h, w = shape
    # Resolution-cap: compute at 1024 max for performance, upscale
    MAX_DIM = 1024
    ds = max(1, min(h, w) // MAX_DIM)
    ch, cw = max(64, h // ds), max(64, w // ds)
    y, x = get_mgrid((ch, cw))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    wave_sp = np.float32(max(6.0, sm * 24.0))
    n_waves = min(max(4, int(ch / max(1.0, sm * 28.0))), 20)
    tw      = np.float32(max(1.0, sm * 1.5))
    v = np.zeros((ch, cw), dtype=np.float32)
    for i in range(n_waves + 1):
        cy        = np.float32((i + 0.5) * float(wave_sp))
        freq      = np.float32(2.0 * np.pi / max(1.0, sm * (25.0 + i * 7.0)))
        amplitude = np.float32(max(1.5, sm * 4.5) * (1.0 + (i % 3) * 0.25))
        wave_y    = cy + np.sin(xf * freq + np.float32(i * 0.8)) * amplitude
        dist      = np.abs(yf - wave_y)
        v         = np.maximum(v, np.clip((tw - dist) / tw, 0.0, 1.0))
    # Add oscilloscope grid background + noise floor
    grid_h = np.clip(1.0 - np.abs((yf % (wave_sp * 2)) - wave_sp) / wave_sp, 0, 1) * 0.04
    grid_v = np.clip(1.0 - np.abs((xf % (wave_sp * 4)) - wave_sp * 2) / (wave_sp * 2), 0, 1) * 0.03
    v = v + grid_h + grid_v
    # Upscale to full resolution
    if (ch, cw) != (h, w):
        v = cv2.resize(v, (w, h), interpolation=cv2.INTER_LINEAR)
    noise_floor = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 300) * 0.04 + 0.03
    v = np.clip(v + noise_floor, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 60.0, "M_range": 40.0, "CC": None}


# ── ART DECO & GEOMETRIC — Texture functions (Batch 5, 2026-03-28) ──────────────

def texture_art_deco_fan(shape, mask, seed, sm):
    """Art Deco fan v2 — dense tiled fans with more spokes, tighter arcs, border frame."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf   = y.astype(np.float32), x.astype(np.float32)
    dim = min(h, w)
    cell_w   = np.float32(max(16.0, dim / 50.0))  # ~50 fans across (was sm*28)
    cell_h   = cell_w * np.float32(0.85)
    n_spokes = max(8, int(float(cell_w) / 2.2))  # More spokes (was /3.5)
    spoke_tw = np.float32(max(1.2, cell_w * 0.04))  # Proportional width
    arc_p    = np.float32(max(2.5, sm * 4.0))
    lx       = xf % cell_w - cell_w * np.float32(0.5)
    ly       = yf % cell_h
    r        = np.sqrt(lx ** 2 + ly ** 2) + np.float32(0.001)
    theta    = np.arctan2(lx, ly)
    half_ang = np.float32(np.pi * 0.44)
    in_fan   = (np.abs(theta) < half_ang) & (r < cell_h * np.float32(0.95))
    sp_range  = half_ang * np.float32(2.0)
    sp_period = sp_range / np.float32(n_spokes)
    sp_phase  = (theta + half_ang) % sp_period
    sp_dist   = np.minimum(sp_phase, sp_period - sp_phase)
    sp_tw_rad = spoke_tw / np.maximum(r, np.float32(3.0))
    spokes    = np.where(in_fan, np.clip((sp_tw_rad - sp_dist) / np.maximum(sp_tw_rad, np.float32(1e-4)), 0.0, 1.0), np.float32(0.0))
    arc_mod  = r % arc_p
    arc_dist = np.minimum(arc_mod, arc_p - arc_mod)
    arcs     = np.where(in_fan, np.clip((spoke_tw - arc_dist) / spoke_tw, 0.0, 1.0), np.float32(0.0))
    v        = np.maximum(spokes, arcs * np.float32(0.6))
    return {"pattern_val": v.astype(np.float32), "R_range": 70.0, "M_range": 50.0, "CC": None}


def texture_chevron_stack(shape, mask, seed, sm):
    """Chevron stack — stacked V-chevrons via triangular-wave centerline."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf  = y.astype(np.float32), x.astype(np.float32)
    pitch   = np.float32(max(5.0, sm * 16.0))
    cell_w  = pitch * np.float32(2.0)
    tw      = np.float32(max(1.5, sm * 2.0))
    x_phase  = xf % cell_w
    y_center = np.abs(x_phase - pitch)
    raw  = (yf % pitch) - y_center
    dist = np.minimum(np.abs(raw), pitch - np.abs(raw))
    v    = np.clip((tw - dist) / tw, 0.0, 1.0)
    # Background surface for full coverage
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1880) * 0.14 + 0.09
    grain = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100) * 0.04
    v = np.clip(np.maximum(v, bg) + grain, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_quatrefoil(shape, mask, seed, sm):
    """Quatrefoil — four overlapping circle-arc leaves forming a Gothic foil lattice."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell  = np.float32(max(8.0, sm * 22.0))
    tw    = np.float32(max(1.5, sm * 2.0))
    lx    = xf % cell - cell * np.float32(0.5)
    ly    = yf % cell - cell * np.float32(0.5)
    half  = cell * np.float32(0.5)
    cr    = cell * np.float32(0.5)
    v     = np.zeros((h, w), dtype=np.float32)
    for cx, cy in ((np.float32(0.0), half), (np.float32(0.0), -half),
                   (half, np.float32(0.0)), (-half, np.float32(0.0))):
        dx  = lx - cx
        dy  = ly - cy
        r   = np.sqrt(dx ** 2 + dy ** 2)
        arc = np.abs(r - cr)
        v   = np.maximum(v, np.clip((tw - arc) / tw, 0.0, 1.0))
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_herringbone(shape, mask, seed, sm):
    """Herringbone — alternating-parity diagonal stripe directions in staggered cells."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    cell_w = np.float32(max(6.0, sm * 18.0))
    cell_h = cell_w * np.float32(0.5)
    tw     = np.float32(max(1.2, sm * 1.8))
    col_b  = np.floor(xf / cell_w).astype(np.float32)
    row_b  = np.floor(yf / cell_h).astype(np.float32)
    parity = (col_b + row_b) % np.float32(2.0) > np.float32(0.5)
    lx     = xf % cell_w
    ly     = yf % cell_h
    slope  = cell_h / cell_w
    diag1  = ly - lx * slope
    diag2  = ly + lx * slope - cell_h
    raw    = np.where(parity, diag2, diag1)
    dist   = np.abs(raw) * np.float32(0.7071)
    v      = np.clip((tw - dist) / tw, 0.0, 1.0)
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_basket_weave(shape, mask, seed, sm):
    """Basket weave — alternating horizontal/vertical strand blocks in 2×2 parity grid."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    block  = np.float32(max(5.0, sm * 14.0))
    tw     = np.float32(max(1.0, sm * 1.5))
    col_b  = np.floor(xf / block).astype(np.float32)
    row_b  = np.floor(yf / block).astype(np.float32)
    parity = (col_b + row_b) % np.float32(2.0) > np.float32(0.5)
    lx     = xf % block
    ly     = yf % block
    half_b = block * np.float32(0.5)
    h_dist = np.minimum(ly % half_b, half_b - ly % half_b)
    v_dist = np.minimum(lx % half_b, half_b - lx % half_b)
    dist   = np.where(parity, v_dist, h_dist)
    v      = np.clip((tw - dist) / tw, 0.0, 1.0)
    return {"pattern_val": v.astype(np.float32), "R_range": 60.0, "M_range": 40.0, "CC": None}


def texture_houndstooth(shape, mask, seed, sm):
    """Houndstooth — combined offset 45°-rotated checkerboards creating 4-pointed star tiles."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    pitch = np.float32(max(6.0, sm * 14.0))
    u     = (xf + yf) / pitch
    vc    = (xf - yf) / pitch
    sq1   = np.floor(u)               % np.float32(2.0)
    sq2   = np.floor(vc)              % np.float32(2.0)
    sq3   = np.floor(u  + np.float32(0.5)) % np.float32(2.0)
    sq4   = np.floor(vc + np.float32(0.5)) % np.float32(2.0)
    base  = ((sq1 + sq2) % np.float32(2.0) > np.float32(0.5)).astype(np.float32)
    notch = ((sq3 + sq4) % np.float32(2.0) > np.float32(0.5)).astype(np.float32)
    v     = np.maximum(base * np.float32(0.9), notch * np.float32(0.7))
    return {"pattern_val": v.astype(np.float32), "R_range": 60.0, "M_range": 40.0, "CC": None}


def texture_argyle(shape, mask, seed, sm):
    """Argyle — diamond outline grid with diagonal crosshatch lines in alternate diamonds."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    pitch = np.float32(max(8.0, sm * 20.0))
    tw    = np.float32(max(1.5, sm * 2.0))
    u     = (xf + yf) / pitch
    vc    = (xf - yf) / pitch
    u_mod  = u  % np.float32(2.0)
    vc_mod = vc % np.float32(2.0)
    du     = np.minimum(u_mod, np.float32(2.0) - u_mod) * pitch * np.float32(0.5)
    dv     = np.minimum(vc_mod, np.float32(2.0) - vc_mod) * pitch * np.float32(0.5)
    diamonds = np.clip((tw - np.minimum(du, dv)) / tw, 0.0, 1.0)
    check  = (np.floor(u) + np.floor(vc)) % np.float32(2.0) > np.float32(0.5)
    fu     = u  - np.floor(u)
    fv     = vc - np.floor(vc)
    d_c1   = np.minimum(fu, np.float32(1.0) - fu) * pitch * np.float32(1.414)
    d_c2   = np.minimum(fv, np.float32(1.0) - fv) * pitch * np.float32(1.414)
    ctw    = np.float32(max(0.8, sm * 1.2))
    cross  = np.where(check,
                      np.maximum(np.clip((ctw - d_c1) / ctw, 0.0, 1.0),
                                 np.clip((ctw - d_c2) / ctw, 0.0, 1.0)) * np.float32(0.5),
                      np.float32(0.0))
    v = np.maximum(diamonds, cross)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2620) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": np.clip(v, 0.0, 1.0).astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_tartan(shape, mask, seed, sm):
    """Tartan plaid — intersecting stripe families at varying widths forming a plaid grid."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf   = y.astype(np.float32), x.astype(np.float32)
    stripe_w = np.float32(max(4.0, sm * 10.0))
    tw       = np.float32(max(0.8, sm * 1.2))
    period   = np.float32(11.0) * stripe_w
    borders  = [0.0, 1.0, 3.0, 4.0, 7.0, 8.0, 10.0, 11.0]
    xmod     = xf % period
    ymod     = yf % period
    dx = np.full((h, w), np.float32(1e6))
    dy = np.full((h, w), np.float32(1e6))
    for bnd in borders:
        bv = np.float32(bnd) * stripe_w
        dx = np.minimum(dx, np.abs(xmod - bv))
        dy = np.minimum(dy, np.abs(ymod - bv))
    v = np.maximum(np.clip((tw - dx) / tw, 0.0, 1.0), np.clip((tw - dy) / tw, 0.0, 1.0))
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2630) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 60.0, "M_range": 40.0, "CC": None}


def texture_op_art_rings(shape, mask, seed, sm):
    """Op-art squares — concentric L-inf square rings creating optical pulsation illusion."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf  = y.astype(np.float32), x.astype(np.float32)
    cell_sz = np.float32(max(12.0, sm * 40.0))
    ring_p  = np.float32(max(3.0, sm * 5.0))
    tw      = np.float32(max(1.0, sm * 1.5))
    lx      = xf % cell_sz - cell_sz * np.float32(0.5)
    ly      = yf % cell_sz - cell_sz * np.float32(0.5)
    linf    = np.maximum(np.abs(lx), np.abs(ly))
    ring_mod  = linf % ring_p
    ring_dist = np.minimum(ring_mod, ring_p - ring_mod)
    v = np.clip((tw - ring_dist) / tw, 0.0, 1.0)
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_moire_grid(shape, mask, seed, sm):
    """Moiré grid — two slightly angled parallel line families creating interference fringes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf  = y.astype(np.float32), x.astype(np.float32)
    spacing = np.float32(max(6.0, sm * 14.0))
    tw      = np.float32(max(1.0, sm * 1.5))
    angle   = np.float32(0.12)
    cos_a   = np.float32(np.cos(float(angle)))
    sin_a   = np.float32(np.sin(float(angle)))
    m1  = yf % spacing
    d1  = np.minimum(m1, spacing - m1)
    m2  = (xf * sin_a + yf * cos_a) % spacing
    d2  = np.minimum(m2, spacing - m2)
    v   = np.maximum(np.clip((tw - d1) / tw, 0.0, 1.0), np.clip((tw - d2) / tw, 0.0, 1.0))
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2660) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 60.0, "M_range": 40.0, "CC": None}


def texture_lozenge_tile(shape, mask, seed, sm):
    """Lozenge tile — offset-row diamond shapes with clean L1-norm border outline."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    loz_w  = np.float32(max(8.0, sm * 20.0))
    loz_h  = loz_w * np.float32(0.6)
    tw     = np.float32(max(1.5, sm * 2.0))
    row    = np.floor(yf / loz_h).astype(np.float32)
    offset = (row % np.float32(2.0)) * loz_w * np.float32(0.5)
    lx     = (xf + offset) % loz_w - loz_w * np.float32(0.5)
    ly     = yf % loz_h - loz_h * np.float32(0.5)
    l1     = np.abs(lx) / (loz_w * np.float32(0.5)) + np.abs(ly) / (loz_h * np.float32(0.5))
    border = np.abs(l1 - np.float32(1.0)) * np.minimum(loz_w, loz_h) * np.float32(0.5)
    v      = np.clip((tw - border) / tw, 0.0, 1.0)
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_ogee_lattice(shape, mask, seed, sm):
    """Ogee lattice — sinusoidally-warped grid creating S-curve Gothic arch shapes."""
    h, w = shape
    y, x = get_mgrid((h, w))
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    pitch  = np.float32(max(8.0, sm * 24.0))
    tw     = np.float32(max(1.5, sm * 2.0))
    amp    = pitch * np.float32(0.35)
    freq   = np.float32(2.0 * np.pi) / pitch
    x_warp = (xf - amp * np.sin(yf * freq)) % pitch
    d_v    = np.minimum(x_warp, pitch - x_warp)
    y_warp = (yf - amp * np.sin(xf * freq + np.float32(np.pi))) % pitch
    d_h    = np.minimum(y_warp, pitch - y_warp)
    v      = np.maximum(np.clip((tw - d_v) / tw, 0.0, 1.0), np.clip((tw - d_h) / tw, 0.0, 1.0))
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2530) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 65.0, "M_range": 45.0, "CC": None}


# ── MATHEMATICAL & FRACTAL — Texture functions (Batch 6, 2026-03-28) ──────────────

def texture_reaction_diffusion(shape, mask, seed, sm):
    """Gray-Scott reaction-diffusion — REAL iterative Turing pattern.
    Simulates chemical U/V concentrations creating organic spots and stripes.
    Computed at 384 max — iterative Laplacian is O(iters×pixels)."""
    h, w = shape
    ds = max(1, min(h, w) // 384)
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed)
    # Initialize U=1 (uniform), V=0 with random seed patches
    U = np.ones((sh, sw), dtype=np.float64)
    V = np.zeros((sh, sw), dtype=np.float64)
    # Seed V with random spots
    n_seeds = max(10, sh * sw // 400)
    for _ in range(n_seeds):
        cy, cx = rng.randint(0, sh), rng.randint(0, sw)
        r = rng.randint(2, max(3, sh // 30))
        y0, y1 = max(0, cy - r), min(sh, cy + r)
        x0, x1 = max(0, cx - r), min(sw, cx + r)
        V[y0:y1, x0:x1] = 1.0
        U[y0:y1, x0:x1] = 0.5
    # Gray-Scott parameters for spots pattern
    Du, Dv = 0.16, 0.08
    F, k = 0.035, 0.065  # Spots regime
    dt = 1.0
    # Iterate — 200 steps at small resolution is fast
    for _ in range(200):
        Lu = cv2.Laplacian(U, cv2.CV_64F)
        Lv = cv2.Laplacian(V, cv2.CV_64F)
        uvv = U * V * V
        U += (Du * Lu - uvv + F * (1.0 - U)) * dt
        V += (Dv * Lv + uvv - (F + k) * V) * dt
        U = np.clip(U, 0, 1)
        V = np.clip(V, 0, 1)
    # V channel shows the spots — normalize
    result = (V - V.min()) / (V.max() - V.min() + 1e-8)
    result = result.astype(np.float32)
    if ds > 1:
        result = cv2.resize(result, (w, h), interpolation=cv2.INTER_LINEAR)
    bg = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 2670) * 0.08 + 0.05
    result = np.clip(result + bg, 0, 1)
    return {"pattern_val": result, "R_range": 70.0, "M_range": 55.0, "CC": None}


def texture_fractal_fern(shape, mask, seed, sm):
    """Barnsley fern v2 — dense IFS attractor with Gaussian smoothing for rich fill.
    Restored chain count (400) and wider kernel (5×5) for visible density."""
    h, w = shape
    rng = np.random.default_rng(int(seed) % (2 ** 31))
    n_chains, n_burnin, n_samples = 1200, 30, 150  # High density for visible fern coverage
    ifs = np.array([
        [ 0.0,   0.0,   0.0,  0.16,  0.0,  0.0 ],
        [ 0.85,  0.04, -0.04, 0.85,  0.0,  1.6 ],
        [ 0.20, -0.26,  0.23, 0.22,  0.0,  1.6 ],
        [-0.15,  0.28,  0.26, 0.24,  0.0,  0.44],
    ], dtype=np.float32)
    cum_p = np.array([0.01, 0.86, 0.93], dtype=np.float32)
    x = np.zeros(n_chains, dtype=np.float32)
    y = np.zeros(n_chains, dtype=np.float32)
    xs_list, ys_list = [], []
    for step in range(n_burnin + n_samples):
        r = rng.random(n_chains).astype(np.float32)
        t = (r[:, np.newaxis] > cum_p[np.newaxis, :]).sum(axis=1)
        p = ifs[t]
        x, y = p[:, 0] * x + p[:, 1] * y + p[:, 4], p[:, 2] * x + p[:, 3] * y + p[:, 5]
        if step >= n_burnin:
            xs_list.append(x.copy())
            ys_list.append(y.copy())
    xs = np.concatenate(xs_list)
    ys = np.concatenate(ys_list)
    xi = np.clip(((xs + np.float32(2.8)) / np.float32(5.6) * w).astype(np.int32), 0, w - 1)
    yi = np.clip(((np.float32(10.0) - ys) / np.float32(10.0) * h).astype(np.int32), 0, h - 1)
    density = np.zeros((h, w), dtype=np.float32)
    # 5×5 kernel spread for visible strokes (was 3×3)
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            np.add.at(density, (np.clip(yi + dr, 0, h - 1), np.clip(xi + dc, 0, w - 1)), np.float32(1.0))
    # Gaussian blur for smooth density fill — wider kernel for denser coverage
    density = cv2.GaussianBlur(density, (0, 0), 2.5)
    mx = float(density.max())
    if mx > 0:
        density /= np.float32(mx)
    # Power curve for contrast then normalize to full 0-1
    density = np.power(np.clip(density, 1e-6, 1.0), 0.5).astype(np.float32)
    d_min, d_max = float(density.min()), float(density.max())
    if d_max > d_min:
        density = (density - d_min) / (d_max - d_min)
    # Background organic texture in empty areas — rich enough to see spec effect
    bg = multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 500) * 0.22 + 0.12
    density = np.clip(np.maximum(density, bg), 0, 1)
    return {"pattern_val": density, "R_range": 70.0, "M_range": 50.0, "CC": None}


def paint_fractal_fern_tint(paint, shape, mask, seed, pm, bb):
    """Fractal fern paint — green-tinted where fern density is high, darkened in stems."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
    h, w = shape
    # Get the fern density to use as a guide
    fern = texture_fractal_fern(shape, mask, seed, 1.0)['pattern_val']
    # Green tint in fern areas — subtle but visible
    green_boost = fern * 0.15 * pm
    paint[:, :, 1] = np.clip(paint[:, :, 1] + green_boost * mask, 0, 1)  # Add green
    paint[:, :, 0] = np.clip(paint[:, :, 0] - fern * 0.05 * pm * mask, 0, 1)  # Reduce red slightly
    # Darken stem areas (highest density = darkest)
    stem_darken = np.clip(fern - 0.6, 0, 0.4) * 0.3 * pm
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - stem_darken * mask, 0, 1)
    # Brightness boost
    paint = np.clip(paint + bb * 0.3 * mask[:, :, np.newaxis] * pm, 0, 1)
    return paint


def texture_hilbert_curve(shape, mask, seed, sm):
    """Hilbert space-filling curve maze — closed walls between non-adjacent cells."""
    h, w = shape
    # Resolution-cap: compute at max 1024×1024, upscale for speed
    MAX_DIM = 1024
    ds = max(1, min(h, w) // MAX_DIM)
    ch, cw = max(64, h // ds), max(64, w // ds)
    y_g, x_g = get_mgrid((ch, cw))
    yf = y_g.astype(np.float32)
    xf = x_g.astype(np.float32)
    grid_n  = 16
    cell_hf = np.float32(ch) / np.float32(grid_n)
    cell_wf = np.float32(cw) / np.float32(grid_n)
    wall_tw = np.float32(max(1.5, min(float(cell_hf), float(cell_wf)) * 0.07))

    def _d2xy(n, d):
        x = y = 0
        s = 1
        t = d
        while s < n:
            rx = 1 if (t & 2) else 0
            ry = 1 if (t & 1) ^ rx else 0
            if ry == 0:
                if rx == 1:
                    x = s - 1 - x
                    y = s - 1 - y
                x, y = y, x
            x += s * rx
            y += s * ry
            t >>= 2
            s <<= 1
        return x, y

    hidx = np.zeros((grid_n, grid_n), dtype=np.int32)
    for d in range(grid_n * grid_n):
        cx_h, cy_h = _d2xy(grid_n, d)
        hidx[cy_h, cx_h] = d
    h_closed = np.abs(np.diff(hidx, axis=1)) != 1
    v_closed = np.abs(np.diff(hidx, axis=0)) != 1
    cy_px = np.clip((yf / cell_hf).astype(np.int32), 0, grid_n - 1)
    cx_px = np.clip((xf / cell_wf).astype(np.int32), 0, grid_n - 1)
    vv = np.zeros((ch, cw), dtype=np.float32)
    for k in range(grid_n - 1):
        wall_x   = np.float32(k + 1) * cell_wf
        dist     = np.abs(xf - wall_x)
        near     = dist < wall_tw
        if not near.any():
            continue
        closed   = h_closed[cy_px, k]
        strength = np.clip((wall_tw - dist) / wall_tw, 0.0, 1.0)
        vv = np.where(near & closed, np.maximum(vv, strength), vv)
    for k in range(grid_n - 1):
        wall_y   = np.float32(k + 1) * cell_hf
        dist     = np.abs(yf - wall_y)
        near     = dist < wall_tw
        if not near.any():
            continue
        closed   = v_closed[k, cx_px]
        strength = np.clip((wall_tw - dist) / wall_tw, 0.0, 1.0)
        vv = np.where(near & closed, np.maximum(vv, strength), vv)
    # Upscale if computed at lower resolution
    if (ch, cw) != (h, w):
        vv = cv2.resize(vv, (w, h), interpolation=cv2.INTER_LINEAR)
    # Background math-paper texture for full coverage
    bg = multi_scale_noise(shape, [16, 32, 64, 128], [0.2, 0.3, 0.3, 0.2], seed + 1890) * 0.13 + 0.08
    vv = np.clip(vv + bg, 0, 1)
    return {"pattern_val": vv, "R_range": 70.0, "M_range": 50.0, "CC": None}


def texture_lorenz_slice(shape, mask, seed, sm):
    """Lorenz butterfly attractor — dense chaotic ODE trajectory map.
    Many chains with long traces for rich butterfly wing coverage."""
    h, w = shape
    rng = np.random.default_rng(int(seed) % (2 ** 31))
    # Compute at capped resolution for speed
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    # Dense sampling: more chains + longer traces = fuller butterfly
    n_chains = 500
    n_burnin = 50
    n_samples = 300
    dt = np.float32(0.012)
    sigma, rho, beta = np.float32(10.0), np.float32(28.0), np.float32(8.0 / 3.0)
    x = rng.uniform(-15.0, 15.0, n_chains).astype(np.float32)
    y = rng.uniform(-15.0, 15.0, n_chains).astype(np.float32)
    z = rng.uniform(10.0, 35.0, n_chains).astype(np.float32)
    xs_list, zs_list = [], []
    for step in range(n_burnin + n_samples):
        dx = sigma * (y - x) * dt
        dy = (x * (rho - z) - y) * dt
        dz = (x * y - beta * z) * dt
        x += dx; y += dy; z += dz
        if step >= n_burnin:
            xs_list.append(x.copy())
            zs_list.append(z.copy())
    xs = np.concatenate(xs_list)
    zs = np.concatenate(zs_list)
    xi = np.clip(((xs + 27.0) / 54.0 * sw).astype(np.int32), 0, sw - 1)
    zi = np.clip(((52.0 - zs) / 54.0 * sh).astype(np.int32), 0, sh - 1)
    density = np.zeros((sh, sw), dtype=np.float32)
    # Wider kernel for visible strokes
    kern = max(2, min(sh, sw) // 100)
    for dr in range(-kern, kern + 1):
        for dc in range(-kern, kern + 1):
            w_k = 1.0 / (1.0 + abs(dr) + abs(dc))  # Distance falloff
            np.add.at(density, (np.clip(zi + dr, 0, sh - 1), np.clip(xi + dc, 0, sw - 1)), np.float32(w_k))
    density = cv2.GaussianBlur(density, (0, 0), max(1.5, sh / 200.0))
    mx = float(density.max())
    if mx > 0:
        density /= np.float32(mx)
    # Upscale
    if ds > 1:
        density = cv2.resize(density, (w, h), interpolation=cv2.INTER_LINEAR)
    # Power curve for contrast boost
    density = np.power(np.clip(density, 1e-6, 1.0), 0.5).astype(np.float32)
    # Stretch to full range
    d_min, d_max = float(density.min()), float(density.max())
    if d_max > d_min:
        density = (density - d_min) / (d_max - d_min)
    # Add turbulent background so empty regions still have visible texture
    bg = multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 700) * 0.18 + 0.08
    density = np.clip(np.maximum(density, bg), 0, 1)
    return {"pattern_val": density.astype(np.float32), "R_range": 75.0, "M_range": 55.0, "CC": None}


def texture_julia_boundary(shape, mask, seed, sm):
    """Julia set fractal — sharp boundary detail, zoomed into interesting region.
    Computes at 1024 max for speed, uses deep zoom + high iterations for crisp edges."""
    h, w = shape
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    y_g, x_g = get_mgrid((sh, sw))
    # Several interesting c values that produce rich boundary detail
    c_opts = [(-0.7269, 0.1889), (-0.40, 0.600), (0.285, 0.010), (-0.835, -0.2321),
              (-0.75, 0.11), (0.355, 0.355), (-0.1, 0.651)]
    cr, ci = c_opts[int(seed) % len(c_opts)]
    # ZOOM IN to the boundary region — scale smaller = more detail visible
    zoom = 1.2  # Tighter zoom for finer detail (was 3.2 = way too zoomed out)
    cx, cy = 0.0, 0.0  # Center on origin
    zr = (x_g.astype(np.float32) - sw * 0.5) / sw * zoom + cx
    zi = (y_g.astype(np.float32) - sh * 0.5) / sh * zoom + cy
    # More iterations = sharper boundaries
    max_iter = 40
    smooth_result = np.zeros((sh, sw), dtype=np.float32)
    for i in range(max_iter):
        mag_sq = zr * zr + zi * zi
        active = mag_sq < 4.0
        zr_n = np.where(active, zr * zr - zi * zi + cr, zr)
        zi_n = np.where(active, 2.0 * zr * zi + ci, zi)
        # Smooth coloring via normalized iteration count
        smooth_result += active.astype(np.float32)
        zr, zi = zr_n, zi_n
    smooth_result /= max_iter
    # Sharp power curve — emphasize the fractal boundary edges
    result = np.clip(1.0 - np.abs(smooth_result - 0.5) * 4.0, 0, 1).astype(np.float32)
    # Add the interior/exterior as subtle depth
    interior = (smooth_result > 0.95).astype(np.float32) * 0.3
    result = np.clip(result + interior, 0, 1)
    if ds > 1:
        result = cv2.resize(result, (w, h), interpolation=cv2.INTER_LINEAR)
    bg = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 200) * 0.08 + 0.05
    result = np.clip(result + bg, 0, 1)
    return {"pattern_val": result, "R_range": 80.0, "M_range": 60.0, "CC": None}


def texture_wave_standing(shape, mask, seed, sm):
    """Chladni plate standing wave — multiple vibration modes superimposed.
    Creates the complex nodal line patterns seen on vibrating metal plates."""
    h, w = shape
    dim = min(h, w)
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32) / dim * np.pi * 2
    xf = x_g.astype(np.float32) / dim * np.pi * 2
    rng = np.random.RandomState(seed)
    # Superimpose 4-6 vibration modes at different frequencies
    n_modes = rng.randint(4, 7)
    result = np.zeros((h, w), dtype=np.float32)
    for i in range(n_modes):
        mx = rng.randint(2, 12)  # Mode numbers — higher = finer detail
        my = rng.randint(2, 12)
        amp = rng.uniform(0.3, 1.0)
        phase = rng.uniform(0, np.pi * 2)
        # Chladni mode: sin(mx*x)*sin(my*y) - sin(my*x)*sin(mx*y)
        mode = np.sin(mx * xf + phase) * np.sin(my * yf) - np.sin(my * xf) * np.sin(mx * yf + phase)
        result += mode * amp
    # Nodal lines are where result ≈ 0 — extract them as bright lines
    result = (result - result.min()) / (result.max() - result.min() + 1e-8)
    # Create sharp nodal lines (zero-crossings become bright)
    nodal = np.clip(1.0 - np.abs(result - 0.5) * 6.0, 0, 1).astype(np.float32)
    # Add subtle fill from the mode pattern itself
    fill = result * 0.2
    v = np.clip(nodal + fill, 0, 1)
    bg = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 300) * 0.06 + 0.04
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_lissajous_web(shape, mask, seed, sm):
    """Lissajous web — implicit sin(3x) minus sin(4y+pi/2) zero-contour family tiled."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf     = y_g.astype(np.float32)
    xf     = x_g.astype(np.float32)
    period = np.float32(max(10.0, sm * 28.0))
    a_f    = np.float32(3.0)
    b_f    = np.float32(4.0)
    delta  = np.float32(np.pi * 0.5)
    tw     = np.float32(max(1.5, sm * 2.5))
    ux     = xf % period / period * np.float32(2.0 * np.pi)
    uy     = yf % period / period * np.float32(2.0 * np.pi)
    diff   = np.abs(np.sin(a_f * ux) - np.sin(b_f * uy + delta))
    line_w = tw * np.float32(3.0) / np.maximum(period, np.float32(1.0))
    v      = np.clip(np.float32(1.0) - diff / np.maximum(line_w, np.float32(1e-4)), 0.0, 1.0)
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1900) * 0.13 + 0.08
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 70.0, "M_range": 50.0, "CC": None}


def texture_dragon_curve(shape, mask, seed, sm):
    """Real dragon curve fractal — fold-sequence bit-pattern algorithm.
    Computes at capped resolution then upscales for speed.
    Produces the genuine space-filling right-angle fractal, not a crosshatch."""
    h, w = shape
    # PERF: Cap compute resolution at 192 max — distance field is O(n_steps × pixels).
    # Even at 256×256 input we downsample; the fractal upscales cleanly.
    MAX_DIM = 192
    ds = max(1, min(h, w) // MAX_DIM)
    rh, rw = max(64, h // ds), max(64, w // ds)
    # Clamp in case shape is already small but above MAX_DIM
    if rh > MAX_DIM or rw > MAX_DIM:
        scale_down = MAX_DIM / max(rh, rw)
        rh, rw = max(64, int(rh * scale_down)), max(64, int(rw * scale_down))
    yf = get_mgrid((rh, rw))[0].astype(np.float32)
    xf = get_mgrid((rh, rw))[1].astype(np.float32)
    n_iter  = 9  # 512 steps — half the segs vs 10, 2× faster, still detailed
    n_steps = 1 << n_iter

    # --- Build dragon curve path via fold-sequence bit-trick ---
    # For each step t, turn direction = +1 (left) or -1 (right)
    # turn(t) = +1 if floor(t / lsb(t) / 2) is even, else -1
    # Equivalent: bit above the lowest set bit of t
    # Heading: 0=right, 1=up, 2=left, 3=down
    dx_dir = [1, 0, -1, 0]
    dy_dir = [0, -1, 0, 1]   # y increases downward in image coords
    px = np.empty(n_steps + 1, dtype=np.float64)
    py = np.empty(n_steps + 1, dtype=np.float64)
    px[0] = 0.0
    py[0] = 0.0
    heading = 0
    for t in range(1, n_steps + 1):
        # Walk one unit in current heading
        px[t] = px[t - 1] + dx_dir[heading]
        py[t] = py[t - 1] + dy_dir[heading]
        if t < n_steps:
            # Compute turn for NEXT step using bit-trick on t
            lsb = t & (-t)                    # lowest set bit of t
            bit_above = (t // lsb) >> 1       # bit above lsb position
            turn = 1 if (bit_above % 2 == 0) else -1
            heading = (heading + turn) % 4

    # Normalize path to DOWNSAMPLED canvas with margin
    margin = 0.08
    px_min, px_max = px.min(), px.max()
    py_min, py_max = py.min(), py.max()
    span_x = max(px_max - px_min, 1.0)
    span_y = max(py_max - py_min, 1.0)
    scale_fit = min((rw * (1.0 - 2 * margin)) / span_x,
                    (rh * (1.0 - 2 * margin)) / span_y)
    off_x = rw * margin + (rw * (1.0 - 2 * margin) - span_x * scale_fit) * 0.5
    off_y = rh * margin + (rh * (1.0 - 2 * margin) - span_y * scale_fit) * 0.5
    px_s = ((px - px_min) * scale_fit + off_x).astype(np.float32)
    py_s = ((py - py_min) * scale_fit + off_y).astype(np.float32)

    # Line width scaled with sm (and canvas size)
    line_w = np.float32(max(1.5, sm * 2.5))
    glow_w = line_w * np.float32(3.5)

    # --- Distance field: min dist to any segment (at reduced resolution) ---
    min_dist = np.full((rh, rw), np.float32(1e9))
    chunk = 256
    for start in range(0, n_steps, chunk):
        end   = min(start + chunk, n_steps)
        ax    = px_s[start:end][:, np.newaxis, np.newaxis]
        ay    = py_s[start:end][:, np.newaxis, np.newaxis]
        bx    = px_s[start + 1:end + 1][:, np.newaxis, np.newaxis]
        by_   = py_s[start + 1:end + 1][:, np.newaxis, np.newaxis]
        abx   = bx - ax
        aby   = by_ - ay
        ab2   = abx * abx + aby * aby + np.float32(1e-8)
        apx   = xf[np.newaxis] - ax
        apy   = yf[np.newaxis] - ay
        t_    = np.clip((apx * abx + apy * aby) / ab2, 0.0, 1.0)
        closx = ax + t_ * abx
        closy = ay + t_ * aby
        d2    = (xf[np.newaxis] - closx) ** 2 + (yf[np.newaxis] - closy) ** 2
        min_d2_batch = d2.min(axis=0)
        min_dist = np.minimum(min_dist, min_d2_batch)
    min_dist = np.sqrt(np.maximum(min_dist, np.float32(0.0)))

    on_path = np.clip((line_w - min_dist) / np.maximum(line_w, np.float32(1e-4)), 0.0, 1.0)
    glow    = np.clip((glow_w - min_dist) / np.maximum(glow_w, np.float32(1e-4)),
                      0.0, 1.0) * np.float32(0.3)
    v       = np.clip(on_path + glow * (np.float32(1.0) - on_path), 0.0, 1.0)

    # Upscale from compute resolution to target shape
    if rh != h or rw != w:
        v = cv2.resize(v.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    bg_fill = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 2680) * 0.08 + 0.05
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 70.0, "M_range": 50.0, "CC": None}


def texture_diffraction_grating(shape, mask, seed, sm):
    """Holographic diffraction grating — 6 sinusoidal gratings at 30-degree intervals."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf    = y_g.astype(np.float32)
    xf    = x_g.astype(np.float32)
    freq  = np.float32(2.0 * np.pi / max(4.0, sm * 8.0))
    n_ang = 6
    v     = np.zeros((h, w), dtype=np.float32)
    for i in range(n_ang):
        angle = np.float32(np.pi * i / n_ang)
        ca    = np.float32(np.cos(float(angle)))
        sa    = np.float32(np.sin(float(angle)))
        v    += np.cos(freq * (xf * ca + yf * sa))
    v = (v / np.float32(n_ang) + np.float32(1.0)) * np.float32(0.5)
    v = np.clip(v * v, 0.0, 1.0)
    return {"pattern_val": v, "R_range": 80.0, "M_range": 65.0, "CC": None}


def texture_perlin_terrain(shape, mask, seed, sm):
    """Topographic terrain — multi-octave noise with ridged erosion + contour lines.
    Fine detail at car scale: features 20-80px at 2048."""
    h, w = shape
    # Higher scales = finer detail. Scale 16 = 128px cells, scale 64 = 32px cells
    terrain = multi_scale_noise(shape, [16, 32, 64, 128], [0.45, 0.28, 0.17, 0.10], seed).astype(np.float32)
    # Ridged: absolute value creates sharp ridge lines (erosion scarring)
    ridged = 1.0 - np.abs(terrain)
    ridged = np.clip(ridged, 0, 1) ** 1.5  # Sharpen ridges
    # Add contour lines for topographic map effect
    elevation = (terrain + 1.0) * 0.5  # Normalize to 0-1
    n_contours = 20
    contour = np.abs(np.sin(elevation * n_contours * np.pi))
    contour_lines = np.clip(1.0 - contour / 0.15, 0, 1)  # Sharp lines where sin crosses zero
    # Combine: ridged terrain + contour lines + subtle elevation shading
    v = np.clip(ridged * 0.5 + contour_lines * 0.35 + elevation * 0.15, 0, 1)
    v = np.power(np.clip(v, 1e-6, 1.0), 0.8).astype(np.float32)
    bg = multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 400) * 0.05 + 0.03
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 55.0, "M_range": 35.0, "CC": None}


def texture_phyllotaxis(shape, mask, seed, sm):
    """Phyllotaxis spiral — Fibonacci golden-angle seed packing distance field.
    OPTIMIZED: compute at 1024 max, upscale."""
    h, w = shape
    # Resolution cap for performance
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    y_g, x_g = get_mgrid((sh, sw))
    cy, cx   = sh // 2, sw // 2
    yf       = (y_g - cy).astype(np.float32)
    xf       = (x_g - cx).astype(np.float32)
    golden_a = np.float32(2.399911)
    seed_r   = np.float32(max(2.5, sm * 5.0)) / ds
    dot_r    = np.float32(max(2.0, sm * 3.5)) / ds
    r_max    = np.float32(min(sh, sw) // 2)
    n_seeds  = min(800, max(60, int(float(r_max) ** 2 / max(float(seed_r ** 2), 1.0) * 0.80)))
    n_approx = (np.sqrt(xf * xf + yf * yf) + np.float32(1e-3)) / seed_r
    n_approx = n_approx * n_approx
    delta    = 18
    min_d_sq = np.full((sh, sw), np.float32(1e9))
    for dn in range(-delta, delta + 1):
        n_c  = np.clip(n_approx + np.float32(dn), 0.0, np.float32(n_seeds - 1))
        nf   = n_c.astype(np.int32).astype(np.float32)
        sx   = np.sqrt(nf) * seed_r * np.cos(nf * golden_a)
        sy   = np.sqrt(nf) * seed_r * np.sin(nf * golden_a)
        d_sq = (xf - sx) ** 2 + (yf - sy) ** 2
        min_d_sq = np.minimum(min_d_sq, d_sq)
    v = np.clip(np.float32(1.0) - np.sqrt(np.maximum(min_d_sq, np.float32(0.0))) / dot_r, 0.0, 1.0)
    # Upscale to full resolution
    if ds > 1:
        v = cv2.resize(v.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1920) * 0.12 + 0.07
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 65.0, "M_range": 45.0, "CC": None}


def texture_truchet_flow(shape, mask, seed, sm):
    """Truchet flow tiles — random quarter-circle arcs creating organic flowing curves.
    Wider arcs with visible fill for car-scale detail."""
    h, w = shape
    dim = min(h, w)
    y_g, x_g = get_mgrid((h, w))
    yf      = y_g.astype(np.float32)
    xf      = x_g.astype(np.float32)
    tile_sz = np.float32(max(12, dim // 60))  # ~34px tiles at 2048 — good density
    tw      = np.float32(max(2.5, tile_sz * 0.15))  # Wider arcs — 15% of tile
    half    = tile_sz * np.float32(0.5)
    t_col   = np.floor(xf / tile_sz).astype(np.int64)
    t_row   = np.floor(yf / tile_sz).astype(np.int64)
    lx      = xf % tile_sz
    ly      = yf % tile_sz
    hash_v  = (t_col * np.int64(1619) + t_row * np.int64(31337) + np.int64(int(seed))) % np.int64(2)
    orient  = hash_v.astype(np.bool_)
    d0a = np.abs(np.sqrt(lx * lx + ly * ly) - half)
    d0b = np.abs(np.sqrt((lx - tile_sz) ** 2 + (ly - tile_sz) ** 2) - half)
    d0  = np.minimum(d0a, d0b)
    d1a = np.abs(np.sqrt((lx - tile_sz) ** 2 + ly * ly) - half)
    d1b = np.abs(np.sqrt(lx * lx + (ly - tile_sz) ** 2) - half)
    d1  = np.minimum(d1a, d1b)
    dist = np.where(orient, d1, d0)
    v    = np.clip((tw - dist) / tw, 0.0, 1.0)
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1940) * 0.13 + 0.08
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 65.0, "M_range": 45.0, "CC": None}


# ── OP-ART & VISUAL ILLUSIONS — Texture functions (Batch 7, 2026-03-28) ────────────

def texture_concentric_op(shape, mask, seed, sm):
    """Bridget Riley-style concentric band illusion — two frequencies produce optical vibration beat."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    cy, cx   = h // 2, w // 2
    yf = (y_g - cy).astype(np.float32); xf = (x_g - cx).astype(np.float32)
    r  = np.sqrt(xf * xf + yf * yf)
    p  = np.float32(max(6.0, sm * 16.0))
    v1 = np.sin(r * np.float32(2.0 * np.pi) / p)
    v2 = np.sin(r * np.float32(2.0 * np.pi) / (p * np.float32(1.618)))
    v  = (v1 + v2) * np.float32(0.5)
    v  = (v + np.float32(1.0)) * np.float32(0.5)
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 80.0, "M_range": 60.0, "CC": None}

def texture_checker_warp(shape, mask, seed, sm):
    """Sine-warped checkerboard — sinusoidal displacement creates bulging grid illusion."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    p   = np.float32(max(8.0, sm * 20.0))
    wa  = np.float32(max(3.0, sm * 8.0))
    wf  = np.float32(2.0 * np.pi / (p * 4.0))
    xw  = xf + wa * np.sin(yf * wf)
    yw  = yf + wa * np.sin(xf * wf)
    cx_i = np.floor(xw / p).astype(np.int32) % 2
    cy_i = np.floor(yw / p).astype(np.int32) % 2
    v   = ((cx_i + cy_i) % 2).astype(np.float32)
    return {"pattern_val": v, "R_range": 75.0, "M_range": 55.0, "CC": None}

def texture_barrel_distort(shape, mask, seed, sm):
    """Barrel-lens distorted checkerboard — straight lines bow outward from image center."""
    h, w  = shape
    y_g, x_g = get_mgrid((h, w))
    cy, cx    = h // 2, w // 2
    half_r    = np.float32(min(h, w) * 0.5)
    yf = (y_g - cy).astype(np.float32) / half_r
    xf = (x_g - cx).astype(np.float32) / half_r
    r2 = xf * xf + yf * yf
    k  = np.float32(0.35)
    xu = (xf * (np.float32(1.0) + k * r2)) * half_r + np.float32(cx)
    yu = (yf * (np.float32(1.0) + k * r2)) * half_r + np.float32(cy)
    p  = np.float32(max(8.0, sm * 20.0))
    gx = np.floor(xu / p).astype(np.int32) % 2
    gy = np.floor(yu / p).astype(np.int32) % 2
    v  = ((gx + gy) % 2).astype(np.float32)
    return {"pattern_val": v, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_moire_interference(shape, mask, seed, sm):
    """Two grids at slightly different scale and 15-degree rotation — classic moiré beat fringes."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    f1  = np.float32(2.0 * np.pi / max(8.0, sm * 16.0))
    f2  = f1 * np.float32(1.07)
    ang = np.float32(np.pi / 12.0)
    ca  = np.float32(np.cos(float(ang))); sa = np.float32(np.sin(float(ang)))
    g1  = np.sin(xf * f1) * np.sin(yf * f1)
    xr  = xf * ca - yf * sa; yr = xf * sa + yf * ca
    g2  = np.sin(xr * f2) * np.sin(yr * f2)
    v   = (g1 + g2) * np.float32(0.5)
    v   = (v + np.float32(1.0)) * np.float32(0.5)
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 80.0, "M_range": 65.0, "CC": None}

def texture_twisted_rings(shape, mask, seed, sm):
    """Concentric rings twisted by radius via Archimedean phase — spring/vortex optical illusion."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    cy, cx    = h // 2, w // 2
    yf = (y_g - cy).astype(np.float32); xf = (x_g - cx).astype(np.float32)
    r     = np.sqrt(xf * xf + yf * yf)
    theta = np.arctan2(yf, xf)
    p     = np.float32(max(6.0, sm * 14.0))
    twist = np.float32(0.022)
    twisted_r = r - twist * r * r + theta * np.float32(float(p) / (2.0 * np.pi))
    v     = np.sin(twisted_r * np.float32(2.0 * np.pi) / p)
    v     = (v + np.float32(1.0)) * np.float32(0.5)
    return {"pattern_val": v, "R_range": 75.0, "M_range": 55.0, "CC": None}

def texture_spiral_hypnotic(shape, mask, seed, sm):
    """Archimedean spiral banded by phase — rotating depth vortex optical illusion."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    cy, cx    = h // 2, w // 2
    yf = (y_g - cy).astype(np.float32); xf = (x_g - cx).astype(np.float32)
    r     = np.sqrt(xf * xf + yf * yf)
    theta = np.arctan2(yf, xf)
    a     = np.float32(max(4.0, sm * 10.0))
    phase = (r / a - theta / np.float32(2.0 * np.pi)) % np.float32(1.0)
    v     = np.sin(phase * np.float32(2.0 * np.pi))
    v     = (v + np.float32(1.0)) * np.float32(0.5)
    return {"pattern_val": v, "R_range": 80.0, "M_range": 60.0, "CC": None}

def texture_necker_grid(shape, mask, seed, sm):
    """Isometric cube tiling — three-brightness face shading creates Necker cube 3D/2D illusion."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    cell = np.float32(max(12.0, sm * 28.0))
    sq3  = np.float32(np.sqrt(3.0))
    u    = xf / (cell * sq3) + yf / cell
    v_c  = -xf / (cell * sq3) + yf / cell
    uf   = u - np.floor(u); vf = v_c - np.floor(v_c)
    top  = (uf < np.float32(0.5)) & (vf < np.float32(0.5))
    right = (uf >= np.float32(0.5)) & (vf < np.float32(0.5))
    bot  = (uf >= np.float32(0.5)) & (vf >= np.float32(0.5))
    v_out = np.where(top | bot, np.float32(0.85),
            np.where(right,     np.float32(0.20), np.float32(0.48)))
    du   = np.minimum(uf, np.float32(1.0) - uf)
    dv   = np.minimum(vf, np.float32(1.0) - vf)
    tw   = np.float32(2.0) / cell
    v_out = np.where((du < tw) | (dv < tw), np.float32(0.03), v_out)
    return {"pattern_val": v_out, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_radial_pulse(shape, mask, seed, sm):
    """24 radial spokes with radius-modulated width — apparent inward pulse motion illusion."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    cy, cx    = h // 2, w // 2
    yf = (y_g - cy).astype(np.float32); xf = (x_g - cx).astype(np.float32)
    r     = np.sqrt(xf * xf + yf * yf)
    theta = np.arctan2(yf, xf)
    n_sp  = 24
    sp    = np.float32(2.0 * np.pi / n_sp)
    tn    = theta % sp
    dc    = np.abs(tn - sp * np.float32(0.5))
    rp    = np.float32(max(8.0, sm * 20.0))
    hw    = sp * (np.float32(0.28) + np.float32(0.22) * np.sin(r * np.float32(2.0 * np.pi) / rp))
    v     = np.clip((hw - dc) / np.maximum(hw, np.float32(1e-6)), 0.0, 1.0)
    return {"pattern_val": v, "R_range": 75.0, "M_range": 55.0, "CC": None}

def texture_hex_op(shape, mask, seed, sm):
    """Nested hexagonal shells via hex Chebyshev distance — 3D optical tunnel illusion."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    cy, cx    = h // 2, w // 2
    yf = (y_g - cy).astype(np.float32); xf = (x_g - cx).astype(np.float32)
    sq3  = np.float32(np.sqrt(3.0))
    q    = xf * np.float32(2.0 / 3.0)
    rr   = -xf * np.float32(1.0 / 3.0) + yf * sq3 * np.float32(1.0 / 3.0)
    hex_d = np.maximum(np.abs(q), np.maximum(np.abs(rr), np.abs(q + rr)))
    p    = np.float32(max(8.0, sm * 18.0))
    v    = np.sin(hex_d / p * np.float32(2.0 * np.pi))
    v    = (v + np.float32(1.0)) * np.float32(0.5)
    v    = np.clip(v * np.float32(1.6) - np.float32(0.20), 0.0, 1.0)
    return {"pattern_val": v, "R_range": 75.0, "M_range": 55.0, "CC": None}

def texture_pinwheel_tiling(shape, mask, seed, sm):
    """7 golden-angle overlapping grids approximate aperiodic pinwheel — no repeating tile direction.
    OPTIMIZED: compute at 1024 max, upscale."""
    h, w = shape
    # Resolution cap for performance
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    y_g, x_g = get_mgrid((sh, sw))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    p      = np.float32(max(10.0, sm * 24.0))
    golden = np.float32(2.399911)
    v      = np.zeros((sh, sw), dtype=np.float32)
    for i in range(7):
        ang = golden * np.float32(i)
        ca  = np.float32(np.cos(float(ang))); sa = np.float32(np.sin(float(ang)))
        xu  = xf * ca + yf * sa; yu = -xf * sa + yf * ca
        tx  = (xu % p) / p; ty = (yu % p) / p
        d   = np.abs(tx - np.float32(0.5)) + np.abs(ty - np.float32(0.5))
        w_i = np.float32(1.0 / (i + 1))
        v   = np.maximum(v, w_i * np.clip(np.float32(1.0) - d * np.float32(2.8), 0.0, 1.0))
    mn, mx = float(v.min()), float(v.max())
    v = (v - np.float32(mn)) / np.float32(max(mx - mn, 1e-6))
    # Upscale to full resolution
    if ds > 1:
        v = cv2.resize(v.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return {"pattern_val": v, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_impossible_grid(shape, mask, seed, sm):
    """Phase-inverted alternating square cells — interior/exterior swap creates impossible connectivity."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    cell  = np.float32(max(12.0, sm * 28.0))
    gf_x  = (xf % cell) / cell; gf_y = (yf % cell) / cell
    cx_i  = np.floor(xf / cell).astype(np.int32) % 2
    cy_i  = np.floor(yf / cell).astype(np.int32) % 2
    par   = ((cx_i + cy_i) % 2).astype(np.bool_)
    d     = np.maximum(np.abs(gf_x - np.float32(0.5)), np.abs(gf_y - np.float32(0.5))) * np.float32(2.0)
    d_inv = np.float32(1.0) - d
    d_out = np.where(par, d_inv, d)
    v     = np.sin(d_out * np.float32(4.0 * np.pi))
    v     = (v + np.float32(1.0)) * np.float32(0.5)
    return {"pattern_val": v, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_rose_curve(shape, mask, seed, sm):
    """Rhodonea k=5 polar rose — petal outline with radial fill, tiled as repeating field."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf   = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    p    = np.float32(max(20.0, sm * 48.0))
    half = p * np.float32(0.5)
    lx   = xf % p - half; ly = yf % p - half
    lr   = np.sqrt(lx * lx + ly * ly)
    lt   = np.arctan2(ly, lx)
    rose_r = half * np.float32(0.84) * np.abs(np.cos(np.float32(5.0) * lt))
    d    = np.abs(lr - rose_r)
    tw   = np.float32(max(2.0, sm * 3.0))
    edge = np.clip((tw - d) / tw, 0.0, 1.0)
    fill = np.where(lr < rose_r,
                    np.clip((rose_r - lr) / np.maximum(rose_r, np.float32(1.0)) * np.float32(1.5),
                            0.0, np.float32(0.65)),
                    np.float32(0.0))
    v    = np.maximum(edge, fill)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2650) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 70.0, "M_range": 50.0, "CC": None}


# ── ART DECO DEPTH + TEXTILE — Texture functions (Batch 8, 2026-03-28) ─────────────

def texture_art_deco_sunburst(shape, mask, seed, sm):
    """Chrysler Building Art Deco sunburst — 36 radial spokes with 5 concentric ring bands."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    cy, cx   = h // 2, w // 2
    yf = (y_g - cy).astype(np.float32); xf = (x_g - cx).astype(np.float32)
    r     = np.sqrt(xf * xf + yf * yf)
    theta = np.arctan2(yf, xf)
    n_sp  = 36
    sp    = np.float32(2.0 * np.pi / n_sp)
    tn    = theta % sp
    dc    = np.minimum(tn, sp - tn)
    arc_d = dc * np.maximum(r, np.float32(1.0))
    sw    = np.float32(max(3.0, sm * 5.0))
    spokes = np.clip((sw - arc_d) / sw, 0.0, 1.0)
    r_max = np.float32(min(h, w) * 0.5)
    rads  = [0.25, 0.42, 0.56, 0.70, 0.84]
    bw    = np.float32(max(3.0, sm * 5.0))
    rings = np.zeros((h, w), dtype=np.float32)
    for rp in rads:
        d = np.abs(r - r_max * np.float32(rp))
        rings = np.maximum(rings, np.clip((bw - d) / bw, 0.0, 1.0))
    v = np.maximum(spokes, rings)
    return {"pattern_val": v, "R_range": 80.0, "M_range": 60.0, "CC": None}

def texture_art_deco_chevron(shape, mask, seed, sm):
    """Bold Art Deco double-stripe chevrons — nested V-shapes with wide gaps, classic 1920s style."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    period = np.float32(max(10.0, sm * 24.0))
    cx_f   = np.float32(w * 0.5)
    v_dist = np.abs(xf - cx_f) + yf
    vmod   = (v_dist % period) / period
    b1 = np.float32(0.12); b2 = np.float32(0.28)
    b3 = np.float32(0.52); b4 = np.float32(0.68)
    v  = np.where(((vmod >= b1) & (vmod < b2)) | ((vmod >= b3) & (vmod < b4)),
                  np.float32(1.0), np.float32(0.0))
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2590) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v, "R_range": 75.0, "M_range": 55.0, "CC": None}

def texture_greek_meander(shape, mask, seed, sm):
    """Greek key meander — right-angle hook spiral motif tiled in alternating-parity rows."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    cell  = np.float32(max(8.0, sm * 20.0))
    tw    = np.float32(max(1.2, sm * 1.8))
    xmod  = xf % cell; ymod = yf % cell
    col_i = np.floor(xf / cell).astype(np.int32)
    row_i = np.floor(yf / cell).astype(np.int32)
    flip  = ((col_i + row_i) % 2).astype(np.bool_)
    xm    = np.where(flip, cell - xmod - np.float32(1.0), xmod)
    y1 = cell * np.float32(0.15); y2 = cell * np.float32(0.50); y3 = cell * np.float32(0.85)
    x1 = cell * np.float32(0.15); x2 = cell * np.float32(0.85)
    tw1 = tw + np.float32(1.0)
    d_h1 = np.abs(ymod - y1)
    d_h2 = np.where(xm > cell * np.float32(0.45), np.abs(ymod - y2), tw1)
    d_h3 = np.abs(ymod - y3)
    d_v1 = np.where(ymod < cell * np.float32(0.55), np.abs(xm - x1), tw1)
    d_v2 = np.abs(xm - x2)
    d_min = np.minimum(d_h1, np.minimum(d_h2, np.minimum(d_h3, np.minimum(d_v1, d_v2))))
    v = np.clip((tw - d_min) / tw, 0.0, 1.0)
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2000) * 0.12 + 0.07
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_moroccan_zellige(shape, mask, seed, sm):
    """Moroccan zellige 8-pointed star — two overlapping L-inf norms create Islamic star tile."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    cell  = np.float32(max(12.0, sm * 28.0))
    tw    = np.float32(max(1.5, sm * 2.5))
    lx    = xf % cell - cell * np.float32(0.5)
    ly    = yf % cell - cell * np.float32(0.5)
    sq_n  = np.maximum(np.abs(lx), np.abs(ly))
    diag_n = (np.abs(lx) + np.abs(ly)) * np.float32(0.7071)
    star_r = cell * np.float32(0.42)
    d1    = np.abs(sq_n - star_r)
    d2    = np.abs(diag_n - star_r)
    d_out = np.minimum(d1, d2)
    outline = np.clip((tw - d_out) / tw, 0.0, 1.0)
    in_star = (sq_n < star_r) & (diag_n < star_r)
    fill    = np.where(in_star, np.float32(0.55), np.float32(0.0))
    v       = np.maximum(outline, fill)
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 75.0, "M_range": 55.0, "CC": None}

def texture_escher_reptile(shape, mask, seed, sm):
    """Escher-style hex reptile tessellation — alternating shaded cells with organic boundary."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    cell  = np.float32(max(14.0, sm * 32.0))
    sq3   = np.float32(np.sqrt(3.0))
    u     = xf / (cell * sq3) + yf / cell
    vc_   = -xf / (cell * sq3) + yf / cell
    uf    = u - np.floor(u); vf = vc_ - np.floor(vc_)
    du    = np.minimum(uf, np.float32(1.0) - uf)
    dv    = np.minimum(vf, np.float32(1.0) - vf)
    deform = np.sin(uf * np.float32(6.0 * np.pi)) * np.sin(vf * np.float32(4.0 * np.pi)) * np.float32(0.07)
    d_bnd  = np.minimum(du + deform, dv + deform)
    tw     = np.float32(2.5) / cell
    uid    = np.floor(u).astype(np.int32)
    vid    = np.floor(vc_).astype(np.int32)
    alt    = ((uid + vid) % 2).astype(np.bool_)
    fill   = np.where(alt, np.float32(0.65), np.float32(0.15))
    v      = np.where(d_bnd < tw, np.float32(1.0), fill)
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_constructivist(shape, mask, seed, sm):
    """Soviet Constructivist — orthogonal grid + 45-degree diagonals + bold horizontal band."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    p    = np.float32(max(10.0, sm * 24.0))
    tw   = np.float32(max(1.5, sm * 2.5))
    h_d  = np.abs((yf % p) - p * np.float32(0.5))
    v_d  = np.abs((xf % p) - p * np.float32(0.5))
    vv   = np.clip((tw - np.minimum(h_d, v_d)) / tw, 0.0, 1.0)
    dp   = p * np.float32(1.4142)
    d45  = (xf + yf) % dp
    d45_d = np.minimum(d45, dp - d45)
    vv   = np.maximum(vv, np.clip((tw - d45_d) / tw, 0.0, 1.0) * np.float32(0.7))
    band_p = p * np.float32(3.0)
    band_d = np.abs((yf % band_p) - band_p * np.float32(0.5))
    band_w = tw * np.float32(3.0)
    vv     = np.maximum(vv, np.clip((band_w - band_d) / band_w, 0.0, 1.0) * np.float32(0.85))
    mn, mx = float(vv.min()), float(vv.max())
    vv = (vv - np.float32(mn)) / np.float32(max(mx - mn, 1e-6))
    return {"pattern_val": vv, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_bauhaus_system(shape, mask, seed, sm):
    """Bauhaus primary form grid — circle, square, and diamond outline shapes alternating in cells."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    cell  = np.float32(max(12.0, sm * 28.0))
    r_sh  = cell * np.float32(0.38)
    tw    = np.float32(max(1.5, sm * 2.0))
    col_i = np.floor(xf / cell).astype(np.int32)
    row_i = np.floor(yf / cell).astype(np.int32)
    lx    = xf % cell - cell * np.float32(0.5)
    ly    = yf % cell - cell * np.float32(0.5)
    shid  = (col_i + row_i * 3) % 3
    circ_d    = np.abs(np.sqrt(lx * lx + ly * ly) - r_sh)
    sq_d      = np.abs(np.maximum(np.abs(lx), np.abs(ly)) - r_sh)
    diamond_d = np.abs((np.abs(lx) + np.abs(ly)) * np.float32(0.7071) - r_sh)
    d_out = np.where(shid == 0, circ_d,
            np.where(shid == 1, sq_d, diamond_d))
    v = np.clip((tw - d_out) / tw, 0.0, 1.0)
    bg_fill = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2640) * 0.12 + 0.07
    v = np.clip(v + bg_fill, 0, 1)
    return {"pattern_val": v, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_celtic_plait(shape, mask, seed, sm):
    """Celtic plait braid — two diagonal strand families with alternating over-under weave."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    p    = np.float32(max(8.0, sm * 18.0))
    sw   = np.float32(max(2.5, sm * 4.0))
    sq2  = np.float32(np.sqrt(2.0))
    d1   = (xf + yf) / sq2; d2 = (xf - yf) / sq2
    d1c  = np.abs(d1 % p - p * np.float32(0.5))
    d2c  = np.abs(d2 % p - p * np.float32(0.5))
    s1   = d1c < sw; s2 = d2c < sw
    cell2 = np.floor(d2 / p).astype(np.int32) % 2
    top1  = s1 & (~s2 | (cell2 == 0))
    top2  = s2 & (~s1 | (cell2 != 0))
    v     = np.where(top1, np.float32(0.90),
            np.where(top2, np.float32(0.40), np.float32(0.05)))
    # Strand fiber texture — noise along strands for detail
    fiber = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 3200) * 0.1
    v = np.clip(v + fiber, 0.0, 1.0)
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 75.0, "M_range": 55.0, "CC": None}

def texture_cane_weave(shape, mask, seed, sm):
    """Cane/rattan weave — orthogonal H+V grid with alternating over-under crossings.
    LAZY-008 FIX: replaced diagonal ±45 projections (was ≈celtic_plait) with true
    basket-weave structure: H canes run left-right, V canes run top-bottom,
    crossings alternate which cane is on top via checkerboard cell parity."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    p  = np.float32(max(7.0, sm * 15.0))   # cell period in pixels
    sw = np.float32(max(2.0, sm * 3.5))    # strand half-width
    # Orthogonal bands: H strand centred on each row period, V strand on each col period
    h_pos    = np.abs((yf % p) - p * np.float32(0.5))
    v_pos    = np.abs((xf % p) - p * np.float32(0.5))
    h_strand = h_pos < sw
    v_strand = v_pos < sw
    # Over-under: checkerboard by integer cell index (not diagonal)
    cell = (np.floor(xf / p).astype(np.int32) + np.floor(yf / p).astype(np.int32)) % 2
    h_top  = h_strand & v_strand & (cell == 0)   # H cane on top at even crossing
    v_top  = h_strand & v_strand & (cell != 0)   # V cane on top at odd crossing
    h_only = h_strand & ~v_strand
    v_only = v_strand & ~h_strand
    v      = np.where(h_top,  np.float32(0.88),
             np.where(v_top,  np.float32(0.44),
             np.where(h_only, np.float32(0.82),
             np.where(v_only, np.float32(0.78),
                              np.float32(0.06)))))
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 55.0, "M_range": 35.0, "CC": None}

def texture_cable_knit(shape, mask, seed, sm):
    """Cable knit — two rope-twist strands crossing per column period with subtle rib background."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    col_w = np.float32(max(6.0, sm * 14.0))
    row_p = np.float32(max(8.0, sm * 18.0))
    tw    = np.float32(max(1.5, sm * 2.0))
    xmod  = xf % col_w; ymod = yf % row_p
    phase = ymod / row_p
    s1_x  = col_w * (np.float32(0.25) + np.float32(0.5) * phase)
    s1_xb = col_w * (np.float32(0.75) - np.float32(0.5) * (phase - np.float32(0.5)))
    s1_pos = np.where(phase < np.float32(0.5), s1_x, s1_xb)
    s2_pos = col_w - s1_pos
    d1    = np.abs(xmod - s1_pos); d2 = np.abs(xmod - s2_pos)
    v     = np.clip((tw - np.minimum(d1, d2)) / tw, 0.0, 1.0)
    rib   = np.abs(xmod / col_w - np.float32(0.5)) * np.float32(2.0)
    v     = np.maximum(v, np.float32(0.12) * (np.float32(1.0) - rib))
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 65.0, "M_range": 45.0, "CC": None}

def texture_damask_brocade(shape, mask, seed, sm):
    """Damask brocade — four-petal rose with outer ring and diamond accent, figure-vs-ground."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    p    = np.float32(max(16.0, sm * 40.0))
    half = p * np.float32(0.5)
    lx   = xf % p - half; ly = yf % p - half
    r    = np.sqrt(lx * lx + ly * ly)
    lt   = np.arctan2(ly, lx)
    rose_r = half * np.float32(0.62) * np.abs(np.cos(np.float32(2.0) * lt))
    ring_r = half * np.float32(0.80)
    diag   = (np.abs(lx) + np.abs(ly)) * np.float32(0.7071)
    diag_r = half * np.float32(0.28)
    in_rose = r < rose_r
    in_ring = (r > ring_r * np.float32(0.88)) & (r < ring_r)
    in_diag = diag < diag_r
    # Gradient edges instead of binary (smoother transitions)
    rose_edge = np.clip(1.0 - np.abs(r - rose_r) / max(float(half * 0.06), 0.5), 0, 1)
    ring_edge = np.clip(1.0 - np.abs(r - ring_r * 0.94) / max(float(half * 0.08), 0.5), 0, 1)
    v = np.where(in_rose | in_ring | in_diag, np.float32(0.85), np.float32(0.15))
    v = np.clip(v + rose_edge * 0.15 + ring_edge * 0.1, 0, 1)
    # Subtle fabric weave texture
    weave = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 100) * 0.04
    v = np.clip(v + weave, 0, 1)
    return {"pattern_val": v.astype(np.float32), "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_tatami_grid(shape, mask, seed, sm):
    """Tatami grid — Japanese 2:1 mat rectangles staggered in alternating rows with border lines."""
    h, w = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32); xf = x_g.astype(np.float32)
    mat_w = np.float32(max(12.0, sm * 28.0))
    mat_h = mat_w * np.float32(0.5)
    tw    = np.float32(max(1.5, sm * 2.0))
    row_i = np.floor(yf / mat_h).astype(np.int32)
    ymod  = yf % mat_h
    row_even = (row_i % 2) == 0
    col_x    = np.where(row_even, xf, xf + mat_w * np.float32(0.5))
    xmod     = col_x % mat_w
    dx       = np.minimum(xmod, mat_w - xmod)
    dy       = np.minimum(ymod, mat_h - ymod)
    d        = np.minimum(dx, dy)
    v        = np.clip((tw - d) / tw, 0.0, 1.0)
    grain    = np.float32(1.0) - np.abs(xmod / mat_w * np.float32(2.0) - np.float32(1.0))
    v        = np.maximum(v, grain * np.float32(0.10))
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 55.0, "M_range": 35.0, "CC": None}


# ── FINAL 4 — To 100 Patterns (🏁 Batch 9, 2026-03-28) ───────────────────────────────

def texture_hypocycloid(shape, mask, seed, sm):
    """Tiled 5-cusped Spirograph hypocycloid — parametric star outline sampled from k=5 hypotrochoid curve."""
    h, w  = shape
    ci    = min(max(20, int(sm * 48)), 24)
    R     = np.float32(ci * 0.44)
    r     = R * np.float32(0.2)          # k=5: r = R/5
    Rr    = R - r                         # 4r
    n_t   = 360
    t_arr = np.linspace(0.0, 2.0 * np.pi, n_t, dtype=np.float32)
    cx_t  = Rr * np.cos(t_arr) + r * np.cos((Rr / r) * t_arr)
    cy_t  = Rr * np.sin(t_arr) - r * np.sin((Rr / r) * t_arr)
    yi    = np.arange(ci, dtype=np.float32) - np.float32(ci // 2)
    xi    = np.arange(ci, dtype=np.float32) - np.float32(ci // 2)
    yc, xc = np.meshgrid(yi, xi, indexing='ij')
    min_d = np.full((ci, ci), np.float32(1e9))
    for ti in range(0, n_t, 90):
        te    = min(ti + 90, n_t)
        dx    = xc[:, :, None] - cx_t[None, None, ti:te]
        dy    = yc[:, :, None] - cy_t[None, None, ti:te]
        min_d = np.minimum(min_d, np.sqrt(dx * dx + dy * dy).min(axis=2))
    sw     = np.float32(max(1.5, sm * 2.5))
    cell_v = np.clip((sw - min_d) / sw, np.float32(0.0), np.float32(1.0))
    ny = int(np.ceil(h / ci)) + 1; nx = int(np.ceil(w / ci)) + 1
    tiled  = np.tile(cell_v, (ny, nx))[:h, :w]
    return {"pattern_val": tiled.astype(np.float32), "R_range": 80.0, "M_range": 60.0, "CC": None}

def texture_voronoi_relaxed(shape, mask, seed, sm):
    """Centroidal Voronoi relaxed cells — jitter-grid seeds give uniform organic cell borders."""
    h, w     = shape
    rng      = np.random.RandomState(seed + 940)
    cell_d   = max(12.0, sm * 30.0)
    ds       = max(1, min(4, h // 256))
    sh, sw_d = h // ds, w // ds
    cd       = max(4, int(cell_d / ds))
    ny_s     = sh // cd + 2;  nx_s = sw_d // cd + 2
    gy = (np.arange(ny_s) * cd).astype(np.float32)
    gx = (np.arange(nx_s) * cd).astype(np.float32)
    gxg, gyg = np.meshgrid(gx, gy)
    jit    = float(cd) * 0.35
    pts_y  = np.clip(gyg + rng.uniform(-jit, jit, gyg.shape), 0, sh - 1).astype(np.float32).flatten()
    pts_x  = np.clip(gxg + rng.uniform(-jit, jit, gxg.shape), 0, sw_d - 1).astype(np.float32).flatten()
    n_pts  = min(len(pts_y), 150)
    pts_y  = pts_y[:n_pts];  pts_x = pts_x[:n_pts]
    y_g, x_g = np.mgrid[0:sh, 0:sw_d]
    yf = y_g.astype(np.float32);  xf = x_g.astype(np.float32)
    dist1  = np.full((sh, sw_d), np.float32(1e9))
    dist2  = np.full((sh, sw_d), np.float32(1e9))
    for i in range(n_pts):
        d      = np.sqrt((yf - pts_y[i]) ** 2 + (xf - pts_x[i]) ** 2)
        new_d2 = np.where(d < dist1, dist1, np.where(d < dist2, d, dist2))
        dist1  = np.minimum(dist1, d)
        dist2  = new_d2
    cw = np.float32(max(2.0, sm * 4.0))
    v  = np.clip(np.float32(1.0) - (dist2 - dist1) / cw, np.float32(0.0), np.float32(1.0))
    if ds > 1:
        v = cv2.resize(v.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1990) * 0.12 + 0.07
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 70.0, "M_range": 50.0, "CC": None}

def texture_wave_ripple_2d(shape, mask, seed, sm):
    """2D wave ripple interference — 4 circular wave sources creating constructive/destructive ring patterns."""
    h, w    = shape
    y_g, x_g = get_mgrid((h, w))
    yf = y_g.astype(np.float32);  xf = x_g.astype(np.float32)
    src  = [(h * 0.25, w * 0.25), (h * 0.75, w * 0.75),
            (h * 0.20, w * 0.80), (h * 0.80, w * 0.20)]
    freq = np.float32(2.0 * np.pi / max(8.0, sm * 20.0))
    v    = np.zeros((h, w), dtype=np.float32)
    for sy, sx in src:
        r_s = np.sqrt((yf - np.float32(sy)) ** 2 + (xf - np.float32(sx)) ** 2)
        v   = v + np.sin(r_s * freq)
    v = v * np.float32(0.25) * np.float32(0.5) + np.float32(0.5)
    return {"pattern_val": np.clip(v, 0.0, 1.0), "R_range": 80.0, "M_range": 60.0, "CC": None}

def texture_sierpinski_tri(shape, mask, seed, sm):
    """Sierpinski gasket — Pascal triangle mod-2 via bitwise (xi & yi)==0 on scaled integer grid."""
    h, w    = shape
    y_g, x_g = get_mgrid((h, w))
    scale   = max(2, int(sm * 6))
    xi      = (x_g // scale).astype(np.int32) & 0x3FF
    yi      = (y_g // scale).astype(np.int32) & 0x3FF
    v       = ((xi & yi) == 0).astype(np.float32)
    bg = multi_scale_noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 1960) * 0.12 + 0.07
    v = np.clip(v + bg, 0, 1)
    return {"pattern_val": v, "R_range": 75.0, "M_range": 55.0, "CC": None}


# --- PATTERN TEXTURE REGISTRY ---
# !! ARCHITECTURE GUARD - READ BEFORE MODIFYING !!
# See ARCHITECTURE.md for full documentation.
# - Each entry maps a pattern ID to {texture_fn, paint_fn, variable_cc, desc}
# - texture_fn generates the spatial pattern array (0-1)
# - paint_fn modifies the RGB paint layer in pattern grooves
# - Adding entries is SAFE. Removing or renaming entries WILL break the UI.
# - If a UI pattern ID is missing here, it silently renders as "none" (invisible).
# - The v7.0 alias block (~line 5170+) maps 162 UI patterns to closest texture_fn.
#   If you need different visuals for an alias, create a NEW texture_fn and re-point it.
#   DO NOT modify the shared texture_fn - it breaks every other pattern using it.
PATTERN_REGISTRY = {
    "acid_wash":         {"texture_fn": texture_acid_wash,        "paint_fn": paint_acid_etch,        "variable_cc": True,  "desc": "Corroded acid-etched surface"},
    "aero_flow": {"texture_fn": texture_aero_flow_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Aerodynamic flow visualization streaks"},
    "art_deco": {"texture_fn": texture_art_deco_fan, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "1920s geometric fan/sunburst motif"},
    "asphalt_texture": {"texture_fn": texture_asphalt_v2, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Road surface aggregate texture"},
    "atomic_orbital": {"texture_fn": texture_ripple_dense, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Electron cloud probability orbital rings"},
    "aurora_bands": {"texture_fn": texture_aurora_bands_v2, "paint_fn": paint_aurora, "variable_cc": False, "desc": "Northern lights wavy curtain bands"},
    "aztec": {"texture_fn": texture_aztec_steps_v2, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Angular stepped Aztec geometric blocks"},
    "bamboo_stalk": {"texture_fn": texture_bamboo_stalk_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Vertical bamboo stalks with joints"},
    "barbed_wire":       {"texture_fn": texture_barbed_wire,     "paint_fn": paint_barbed_scratch,   "variable_cc": False, "desc": "Twisted wire with barb spikes"},
    "battle_worn":       {"texture_fn": texture_battle_worn,      "paint_fn": paint_scratch_marks,    "variable_cc": True,  "desc": "Scratched weathered damage"},
    "binary_code": {"texture_fn": texture_binary_code_v2, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Streaming 0s and 1s binary data"},
    "biohazard": {"texture_fn": texture_biohazard_symbol, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Repeating biohazard trefoil symbol"},
    # "biomechanical" LIVES IN engine/registry.py
    "biomechanical_2": {"texture_fn": texture_biomechanical_2, "paint_fn": paint_damascus_layer, "variable_cc": False, "desc": "Procedural Giger-style organic mechanical"},
    "blue_flame": {"texture_fn": texture_flame_aggressive, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Blue flame - superseded by flame_blue_propane"},
    "board_wax": {"texture_fn": texture_ripple_soft, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Circular surfboard wax rub pattern"},
    "brake_dust": {"texture_fn": texture_metal_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Hot brake dust particle scatter"},
    # "brick" REMOVED - Artistic & Cultural category replaced by image-based patterns (see engine/registry.py)
    "bullet_holes": {"texture_fn": texture_fracture, "paint_fn": paint_fracture_damage, "variable_cc": True, "desc": "Scattered impact penetration holes"},
    "camo":              {"texture_fn": texture_camo,            "paint_fn": paint_camo_pattern,     "variable_cc": False, "desc": "Digital splinter camouflage blocks"},
    "carbon_fiber":      {"texture_fn": texture_carbon_fiber,     "paint_fn": paint_carbon_darken,    "variable_cc": False, "desc": "Woven 2x2 twill weave"},
    "caustic": {"texture_fn": texture_caustic_v2, "paint_fn": paint_ripple_reflect, "variable_cc": False, "desc": "Underwater dancing light caustic pools"},
    "celtic_knot":       {"texture_fn": texture_celtic_knot,    "paint_fn": paint_celtic_emboss,    "variable_cc": False, "desc": "Interwoven flowing band knot pattern"},
    "chainlink": {"texture_fn": texture_chainlink, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Chain-link fence diagonal wire grid"},
    "chainmail":         {"texture_fn": texture_chainmail,       "paint_fn": paint_chainmail_emboss, "variable_cc": False, "desc": "Interlocking metal ring mesh"},
    "checkered_flag": {"texture_fn": texture_checkered_flag, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Classic racing checkered flag grid"},
    "chevron":           {"texture_fn": texture_chevron,        "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Repeating V/arrow stripe pattern"},
    "circuit_board":     {"texture_fn": texture_circuit_board,   "paint_fn": paint_circuit_glow,     "variable_cc": False, "desc": "PCB trace lines with pads and vias"},
    "circuitboard": {"texture_fn": texture_circuit_board, "paint_fn": paint_circuit_glow, "variable_cc": False, "desc": "PCB trace pattern metallic traces"},
    "classic_hotrod": {"texture_fn": texture_flame_sweep, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Classic hot rod - superseded by flame_hotrod_classic"},
    "corrugated": {"texture_fn": texture_corrugated_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Corrugated sheet metal parallel ridges"},
    "cracked_ice":       {"texture_fn": texture_cracked_ice,      "paint_fn": paint_ice_cracks,       "variable_cc": False, "desc": "Frozen crack network"},
    "crocodile": {"texture_fn": texture_dragon_scale, "paint_fn": paint_scale_pattern, "variable_cc": False, "desc": "Deep embossed crocodile hide scales"},
    "crosshatch":        {"texture_fn": texture_crosshatch_fine, "paint_fn": paint_crosshatch_ink,   "variable_cc": False, "desc": "Overlapping diagonal pen stroke lines"},
    # "damascus" REMOVED - Artistic & Cultural replaced by image-based (engine/registry.py)
    "data_stream": {"texture_fn": texture_data_stream, "paint_fn": paint_hologram_lines, "variable_cc": False, "desc": "Flowing horizontal data packet streams"},
    "dazzle":            {"texture_fn": texture_dazzle_v2,          "paint_fn": paint_dazzle_contrast,  "variable_cc": False, "desc": "Bold Voronoi B/W dazzle camo patches"},
    # "denim" REMOVED - Artistic & Cultural replaced by image-based (engine/registry.py)
    "diamond_plate":     {"texture_fn": texture_diamond_plate,    "paint_fn": paint_diamond_emboss,   "variable_cc": False, "desc": "Industrial raised diamond tread"},
    "dimensional": {"texture_fn": texture_interference, "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Newtons rings thin-film interference"},
    "dna_helix": {"texture_fn": texture_dna_helix_v2, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Double-helix DNA strand spiral"},
    # "dragon_scale" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "drift_marks": {"texture_fn": texture_drift_marks_v2, "paint_fn": paint_tread_darken, "variable_cc": False, "desc": "Sideways drift tire trail marks"},
    "ekg": {"texture_fn": texture_ekg_v2, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Heartbeat EKG monitor line pulse"},
    "ember_mesh":        {"texture_fn": texture_ember_mesh,    "paint_fn": paint_ember_mesh_glow,  "variable_cc": False, "desc": "Glowing hot wire grid with ember nodes"},
    "ember_scatter": {"texture_fn": texture_ember_scatter_v2, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Floating glowing embers scattered"},
    "expanded_metal": {"texture_fn": texture_grating_heavy, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Stretched diamond expanded mesh"},
    "feather": {"texture_fn": texture_feather_barb, "paint_fn": paint_snake_emboss, "variable_cc": False, "desc": "Layered overlapping bird feather barbs"},
    "fingerprint": {"texture_fn": texture_fingerprint, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Swirling concentric fingerprint ridges"},
    "finish_line": {"texture_fn": texture_houndstooth_bold, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Bold start/finish line checkered band"},
    "fire_lick": {"texture_fn": texture_flame_tongues, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Flickering flame tongues licking upward"},
    "fireball": {"texture_fn": texture_flame_ball, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Explosive spherical fireball burst"},
    "flame_fade": {"texture_fn": texture_flame_smoke_fade, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Flames gradually fading into smoke"},
    # "fleur_de_lis" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "fractal": {"texture_fn": texture_plasma_fractal, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Self-similar Mandelbrot fractal branching"},
    "fractal_2": {"texture_fn": texture_fractal_2, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "High-frequency geometric fracturing"},
    "fractal_3": {"texture_fn": texture_fractal_3, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Dense interwoven fractal network"},
    "fracture":          {"texture_fn": texture_fracture,      "paint_fn": paint_fracture_damage,  "variable_cc": True,  "desc": "Shattered impact glass with radial crack network"},
    "fresnel_ghost": {"texture_fn": texture_hex_honeycomb, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Hidden hex pattern Fresnel amplification"},
    "frost_crystal":     {"texture_fn": texture_frost_crystal_v2,  "paint_fn": paint_frost_crystal,    "variable_cc": False, "desc": "Ice crystal branching fractals"},
    "g_force": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Acceleration force vector compression"},
    "ghost_flames": {"texture_fn": texture_plasma_soft, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "[Legacy] Ghost flames - superseded by flame_ghost"},
    "giraffe": {"texture_fn": texture_giraffe, "paint_fn": paint_leopard_spots, "variable_cc": False, "desc": "Irregular polygon giraffe spot patches"},
    "glacier_crack": {"texture_fn": texture_cracked_ice, "paint_fn": paint_ice_cracks, "variable_cc": False, "desc": "Deep blue-white glacial ice fissures"},
    "glitch_scan": {"texture_fn": texture_glitch_scan_v2, "paint_fn": paint_hologram_lines, "variable_cc": False, "desc": "Horizontal glitch scanline displacement"},
    "gothic_arch": {"texture_fn": texture_gothic_cross_v2, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Ornate gothic cathedral cross grid"},
    "gothic_scroll": {"texture_fn": texture_gothic_scroll_v2, "paint_fn": paint_damascus_layer, "variable_cc": False, "desc": "Flowing dark ornamental scroll filigree"},
    "grating": {"texture_fn": texture_grating_heavy, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Industrial floor grating parallel bars"},
    "greek_key": {"texture_fn": texture_tribal_meander, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Continuous right-angle meander border"},
    "grip_tape": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Coarse skateboard grip tape texture"},
    "hailstorm": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "Dense scattered impact crater dimples"},
    "halfpipe": {"texture_fn": texture_wave_gentle, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Curved halfpipe ramp cross-section"},
    "hammered":          {"texture_fn": texture_hammered,         "paint_fn": paint_hammered_dimples, "variable_cc": False, "desc": "Hand-hammered dimple pattern"},
    "hellfire": {"texture_fn": texture_flame_aggressive, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Hellfire - superseded by flame_hellfire_column"},
    "hex_mesh":          {"texture_fn": texture_hex_mesh,         "paint_fn": paint_hex_emboss,       "variable_cc": False, "desc": "Honeycomb wire grid"},
    "hibiscus": {"texture_fn": texture_hibiscus_v2, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Hawaiian hibiscus flower pattern"},
    "hologram":          {"texture_fn": texture_hologram,         "paint_fn": paint_hologram_lines,   "variable_cc": False, "desc": "Horizontal scanline projection"},
    "holographic": {"texture_fn": texture_holographic_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Hologram diffraction grating rainbow"},
    "holographic_flake": {"texture_fn": texture_holographic_flake,"paint_fn": paint_coarse_flake,     "variable_cc": False, "desc": "Rainbow prismatic micro-grid flake"},
    "inferno": {"texture_fn": texture_flame_wild, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Inferno - superseded by flame_inferno_wall"},
    "interference":      {"texture_fn": texture_interference,     "paint_fn": paint_interference_shift,"variable_cc": False, "desc": "Flowing rainbow wave bands"},
    "iron_emblem": {"texture_fn": texture_iron_cross_v2, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Bold Iron Cross motif array"},
    # "japanese_wave" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "kevlar_weave": {"texture_fn": texture_kevlar_weave, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Tight aramid fiber golden weave"},
    "knurled": {"texture_fn": texture_crosshatch, "paint_fn": paint_crosshatch_ink, "variable_cc": False, "desc": "Machine knurling diagonal cross-hatch"},
    "lap_counter": {"texture_fn": texture_pinstripe_fine, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Repeating tally mark lap counter"},
    "lava_flow":         {"texture_fn": texture_lava_flow,       "paint_fn": paint_lava_glow,        "variable_cc": True,  "desc": "Flowing molten rock with hot cracks"},
    "leather_grain": {"texture_fn": texture_hammered, "paint_fn": paint_hammered_dimples, "variable_cc": False, "desc": "Natural grain leather pebble texture"},
    "leopard":           {"texture_fn": texture_leopard_rosette_v2,  "paint_fn": paint_leopard_spots,    "variable_cc": False, "desc": "Organic leopard rosette spots"},
    "lightning":         {"texture_fn": texture_lightning_soft,    "paint_fn": paint_lightning_glow,   "variable_cc": False, "desc": "Forked lightning bolt paths"},
    "magma_crack":       {"texture_fn": texture_magma_crack,     "paint_fn": paint_magma_glow,       "variable_cc": False, "desc": "Voronoi boundary cracks with orange lava glow"},
    # "mandala" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "marble":            {"texture_fn": texture_marble,          "paint_fn": paint_marble_vein,      "variable_cc": False, "desc": "Soft noise veins like polished marble"},
    "matrix_rain": {"texture_fn": texture_matrix_rain, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Falling green character rain columns"},
    "mega_flake":        {"texture_fn": texture_mega_flake,      "paint_fn": paint_mega_sparkle,     "variable_cc": False, "desc": "Large hex glitter flake facets"},
    "metal_flake":       {"texture_fn": texture_metal_flake,      "paint_fn": paint_coarse_flake,     "variable_cc": False, "desc": "Coarse visible metallic flake"},
    "molecular": {"texture_fn": texture_molecular_v2, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Ball-and-stick molecular bond diagram"},
    # "mosaic" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "multicam":          {"texture_fn": texture_multicam,        "paint_fn": paint_multicam_colors,  "variable_cc": False, "desc": "5-layer organic Perlin camo pattern"},
    "nanoweave": {"texture_fn": texture_carbon_fiber, "paint_fn": paint_carbon_darken, "variable_cc": False, "desc": "Microscopic tight-knit nano fiber"},
    "neural": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Living neural network Voronoi cells"},
    "neuron_network": {"texture_fn": texture_neuron_network_v2, "paint_fn": paint_circuit_glow, "variable_cc": False, "desc": "Branching neural dendrite connection web"},
    "nitro_burst": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Nitrous oxide flame burst spray"},
    "none":              {"texture_fn": None,                     "paint_fn": paint_none,             "variable_cc": False, "desc": "No pattern overlay"},
    # "norse_rune" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "ocean_foam": {"texture_fn": texture_ocean_foam_v2, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "White sea foam bubbles on water"},
    "optical_illusion": {"texture_fn": texture_interference, "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Moire interference exotic geometry"},
    "p_plasma": {"texture_fn": texture_plasma, "paint_fn": paint_plasma_veins, "variable_cc": False, "desc": "Plasma ball discharge electric tendrils"},
    "p_tessellation": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Geometric Penrose-style tiling"},
    "p_topographic": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Contour map elevation isolines"},
    # "paisley" REMOVED - Artistic & Cultural replaced by image-based (engine/registry.py)
    "palm_frond": {"texture_fn": texture_palm_frond_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Tropical palm leaf frond silhouettes"},
    "peeling_paint": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Curling paint peel flake patches"},
    "five_point_star": {"texture_fn": texture_pentagram_star, "paint_fn": paint_spiderweb_crack, "variable_cc": False, "desc": "Five-pointed star geometric array"},
    "perforated": {"texture_fn": texture_metal_flake, "paint_fn": paint_coarse_flake, "variable_cc": False, "desc": "Evenly punched round hole grid"},
    "pinstripe":         {"texture_fn": texture_pinstripe,       "paint_fn": paint_pinstripe,        "variable_cc": False, "desc": "Thin parallel racing stripes"},
    "pinstripe_flames": {"texture_fn": texture_pinstripe_diagonal, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "[Legacy] Pinstripe flames - superseded by flame_pinstripe_outline"},
    "pit_lane_marks": {"texture_fn": texture_pinstripe_fine, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Pit lane boundary lines and markings"},
    "pixel_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Retro 8-bit pixel block mosaic"},
    "plaid":             {"texture_fn": texture_plaid,          "paint_fn": paint_plaid_tint,       "variable_cc": False, "desc": "Overlapping tartan plaid bands"},
    "plasma":            {"texture_fn": texture_plasma,           "paint_fn": paint_plasma_veins,     "variable_cc": False, "desc": "Branching electric plasma veins"},
    "podium_stripe": {"texture_fn": texture_chevron_bold, "paint_fn": paint_chevron_contrast, "variable_cc": False, "desc": "Victory podium step stripe bands"},
    "pulse_monitor": {"texture_fn": texture_wave_choppy, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Multi-line vital signs monitor waveforms"},
    "qr_code": {"texture_fn": texture_houndstooth, "paint_fn": paint_houndstooth_contrast, "variable_cc": False, "desc": "Dense QR code square block grid"},
    "racing_stripe": {"texture_fn": texture_pinstripe_vertical, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Bold dual center racing stripes"},
    "rain_drop":         {"texture_fn": texture_rain_drop,       "paint_fn": paint_rain_droplets,    "variable_cc": False, "desc": "Water droplet beading on surface"},
    "razor":             {"texture_fn": texture_razor,           "paint_fn": paint_razor_slash,      "variable_cc": False, "desc": "Diagonal aggressive slash marks"},
    "razor_wire":        {"texture_fn": texture_razor_wire,    "paint_fn": paint_razor_wire_scratch, "variable_cc": False, "desc": "Coiled helical wire with barbed loops"},
    "rev_counter": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Tachometer LED bar segment array"},
    "rip_tide": {"texture_fn": texture_wave_choppy, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Dangerous swirling rip current flow"},
    "ripple":            {"texture_fn": texture_ripple,           "paint_fn": paint_ripple_reflect,   "variable_cc": False, "desc": "Concentric water drop rings"},
    "rivet_grid": {"texture_fn": texture_rivet_plate, "paint_fn": paint_rivet_plate_emboss, "variable_cc": False, "desc": "Evenly spaced industrial rivet dots"},
    "rivet_plate":       {"texture_fn": texture_rivet_plate,    "paint_fn": paint_rivet_plate_emboss, "variable_cc": False, "desc": "Industrial riveted panel seams with chrome heads"},
    "road_rash": {"texture_fn": texture_battle_worn, "paint_fn": paint_scratch_marks, "variable_cc": True, "desc": "Sliding contact abrasion scrape marks"},
    "roll_cage": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Tubular roll cage structure grid"},
    "rooster_tail": {"texture_fn": texture_rain_drop, "paint_fn": paint_rain_droplets, "variable_cc": False, "desc": "Dirt spray rooster tail splash"},
    "rpm_gauge": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Tachometer arc needle sweep"},
    "rust_bloom": {"texture_fn": texture_acid_wash, "paint_fn": paint_acid_etch, "variable_cc": True, "desc": "Expanding rust spot corrosion blooms"},
    "sandstorm": {"texture_fn": texture_static_noise, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Dense blowing sand particle streaks"},
    "shokk_bioform":      {"texture_fn": texture_shokk_bioform,      "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Alien reaction-diffusion organic living surface"},
    "shokk_bolt": {"texture_fn": texture_shokk_bolt_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Fractal branching lightning with chrome/matte split"},
    "shokk_fracture": {"texture_fn": texture_shokk_fracture_v2, "paint_fn": paint_shokk_phase, "variable_cc": True, "desc": "SHOKK: Shattered glass with chrome shard facets"},
    "shokk_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Perspective-warped digital grid tunnel"},
    "shokk_hex": {"texture_fn": texture_hex_mesh, "paint_fn": paint_hex_emboss, "variable_cc": False, "desc": "Hexagonal cells with electric edge glow"},
    "shokk_nebula":       {"texture_fn": texture_shokk_nebula,       "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Cosmic gas cloud with star-forming knots"},
    "shokk_phase_interference": {"texture_fn": texture_shokk_phase_interference, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK Phase: Dual-wave moiré interference pattern"},
    "shokk_phase_split":        {"texture_fn": texture_shokk_phase_split,        "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK Phase: Independent M/R sine waves - shimmer split"},
    "shokk_phase_vortex":       {"texture_fn": texture_shokk_phase_vortex,       "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK Phase: Radial/angular vortex with CC modulation"},
    "shokk_plasma_storm": {"texture_fn": texture_shokk_plasma_storm, "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Multi-epicenter branching plasma discharge"},
    "shokk_predator":     {"texture_fn": texture_shokk_predator,     "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Active camo distortion field hexagonal shimmer"},
    "shokk_pulse_wave": {"texture_fn": texture_shokk_pulse_wave_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Breathing concentric chrome/matte rings"},
    "shokk_scream": {"texture_fn": texture_shokk_scream_v2, "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Acoustic shockwave pressure visualization"},
    "shokk_singularity":  {"texture_fn": texture_shokk_singularity,  "paint_fn": paint_shokk_phase, "variable_cc": True,  "desc": "SHOKK: Black hole gravity well with accretion disk"},
    "shokk_tesseract":    {"texture_fn": texture_shokk_tesseract,    "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: 4D hypercube exotic geometry wireframe"},
    "shokk_waveform":     {"texture_fn": texture_shokk_waveform,     "paint_fn": paint_shokk_phase, "variable_cc": False, "desc": "SHOKK: Audio frequency decomposition visualizer"},
    "shrapnel": {"texture_fn": texture_fracture, "paint_fn": paint_fracture_damage, "variable_cc": True, "desc": "Irregular shrapnel damage fragments"},
    "skid_marks": {"texture_fn": texture_tire_tread, "paint_fn": paint_tread_darken, "variable_cc": False, "desc": "Black rubber tire skid marks"},
    "skull":             {"texture_fn": texture_skull,          "paint_fn": paint_skull_darken,     "variable_cc": False, "desc": "Repeating skull mesh array"},
    "skull_wings": {"texture_fn": texture_skull, "paint_fn": paint_skull_darken, "variable_cc": False, "desc": "Affliction-style winged skull spread"},
    "snake_skin":        {"texture_fn": texture_snake_skin,      "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Elongated overlapping reptile scales"},
    "snake_skin_2":      {"texture_fn": texture_snake_skin_2,    "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Diamond-shaped python scales with color variation"},
    "snake_skin_3":      {"texture_fn": texture_snake_skin_3,    "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Hourglass saddle pattern viper scales"},
    "snake_skin_4":      {"texture_fn": texture_snake_skin_4,    "paint_fn": paint_snake_emboss,     "variable_cc": False, "desc": "Cobblestone pebble boa constrictor scales"},
    "solar_flare": {"texture_fn": texture_lightning, "paint_fn": paint_lightning_glow, "variable_cc": False, "desc": "Erupting coronal mass ejection"},
    "sound_wave": {"texture_fn": texture_wave_gentle, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Audio waveform amplitude oscillation"},
    "soundwave": {"texture_fn": texture_wave_vertical, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Audio waveform visualization"},
    "spark_scatter": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Grinding metal spark shower trails"},
    "speed_lines": {"texture_fn": texture_speed_lines_v2, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Motion speed streak action lines"},
    "spiderweb":         {"texture_fn": texture_spiderweb,      "paint_fn": paint_spiderweb_crack,  "variable_cc": False, "desc": "Radial + concentric web crack lines"},
    "sponsor_fade": {"texture_fn": texture_pinstripe_fine, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Gradient fade zones for sponsor areas"},
    "stardust":          {"texture_fn": texture_stardust,         "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Sparse bright star pinpoints"},
    "stardust_2":        {"texture_fn": texture_stardust_2,       "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Supernova explosion starburst"},
    "starting_grid": {"texture_fn": texture_tron, "paint_fn": paint_tron_glow, "variable_cc": False, "desc": "Grid slot positions track layout"},
    "static_noise":      {"texture_fn": texture_static_noise,  "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "TV static blocky pixel noise grain"},
    # "steampunk_gears" REMOVED - Artistic & Cultural image-based (engine/registry.py)
    "surf_stripe": {"texture_fn": texture_pinstripe_diagonal, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Retro surfboard racing stripes"},
    "tessellation": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Interlocking M.C. Escher-style tiles"},
    "thorn_vine": {"texture_fn": texture_barbed_wire, "paint_fn": paint_barbed_scratch, "variable_cc": False, "desc": "Twisted thorny vine dark botanical"},
    "tiger_stripe": {"texture_fn": texture_camo, "paint_fn": paint_camo_pattern, "variable_cc": False, "desc": "Organic tiger stripe broken bands"},
    "tiki_totem": {"texture_fn": texture_tribal_bands, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Carved tiki pole face pattern"},
    "tire_smoke": {"texture_fn": texture_tire_smoke_v2, "paint_fn": paint_static_noise_grain, "variable_cc": False, "desc": "Burnout tire smoke wisps and haze"},
    "tire_tread":        {"texture_fn": texture_tire_tread,      "paint_fn": paint_tread_darken,     "variable_cc": False, "desc": "Directional V-groove rubber tread"},
    "topographic":       {"texture_fn": texture_topographic,    "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Elevation contour map lines"},
    "torch_burn": {"texture_fn": texture_flame_teardrop, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "Focused torch flame burn marks"},
    "tornado": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Spiraling funnel vortex rotation"},
    "track_map": {"texture_fn": texture_topographic, "paint_fn": paint_topographic_line, "variable_cc": False, "desc": "Race circuit layout line pattern"},
    "tribal_flame": {"texture_fn": texture_flame_tribal_curves, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Tribal flame - superseded by flame_tribal_knife"},
    "tron":              {"texture_fn": texture_tron,            "paint_fn": paint_tron_glow,        "variable_cc": False, "desc": "Neon 48px grid with 2px light lines"},
    "trophy_laurel": {"texture_fn": texture_tribal_knot_dense, "paint_fn": paint_celtic_emboss, "variable_cc": False, "desc": "Victory laurel wreath motif"},
    "tropical_leaf": {"texture_fn": texture_pinstripe_vertical, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Large monstera tropical leaf outlines"},
    "turbine":           {"texture_fn": texture_turbine,       "paint_fn": paint_turbine_spin,     "variable_cc": False, "desc": "Radial fan blade spiral from center"},
    "turbo_swirl": {"texture_fn": texture_turbine, "paint_fn": paint_turbine_spin, "variable_cc": False, "desc": "Turbocharger compressor spiral vortex"},
    "victory_confetti": {"texture_fn": texture_stardust, "paint_fn": paint_stardust_sparkle, "variable_cc": False, "desc": "Scattered celebration confetti"},
    "voronoi_shatter": {"texture_fn": texture_mosaic, "paint_fn": paint_mosaic_tint, "variable_cc": False, "desc": "Clean voronoi cell shatter sharp edges"},
    "wave":              {"texture_fn": texture_wave,           "paint_fn": paint_wave_shimmer,     "variable_cc": False, "desc": "Smooth flowing sine wave ripples"},
    "wave_curl": {"texture_fn": texture_wave_choppy, "paint_fn": paint_wave_shimmer, "variable_cc": False, "desc": "Curling ocean wave barrel shape"},
    "wildfire": {"texture_fn": texture_flame_wild, "paint_fn": paint_lava_glow, "variable_cc": True, "desc": "[Legacy] Wildfire - superseded by flame_inferno_wall"},
    "wind_tunnel": {"texture_fn": texture_pinstripe_diagonal, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Flow visualization smoke streaks"},
    "wood_grain":        {"texture_fn": texture_wood_grain,      "paint_fn": paint_wood_grain,       "variable_cc": False, "desc": "Natural flowing wood grain texture"},
    "zebra": {"texture_fn": texture_zebra_stripe, "paint_fn": paint_pinstripe, "variable_cc": False, "desc": "Bold black-white zebra stripe pattern"},
    # ── Intricate & Ornate (★) — Batch 1 (2026-03-28) ───────────────────────────
    "art_nouveau_vine":   {"texture_fn": texture_art_nouveau_vine,    "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Art Nouveau noise-warped sinuous vine stems and branch lattice"},
    "baroque_scrollwork": {"texture_fn": texture_baroque_scrollwork,  "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Tiled Archimedean spiral scrollwork with 3-lobe flourish modulation"},
    "brushed_metal_fine": {"texture_fn": texture_brushed_metal_fine,  "paint_fn": paint_pinstripe,          "variable_cc": False, "desc": "Three-frequency anisotropic directional micro-scratch grain"},
    "carbon_3k_weave":    {"texture_fn": texture_carbon_3k_weave,     "paint_fn": paint_carbon_darken,      "variable_cc": False, "desc": "Satin-braid diagonal ±45° carbon 3K tow weave"},
    "damascus_steel":     {"texture_fn": texture_damascus,            "paint_fn": paint_damascus_layer,     "variable_cc": False, "desc": "Folded-metal sinuous Damascus steel layered bands"},
    "honeycomb_organic":  {"texture_fn": texture_honeycomb_organic,   "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Noise-warped hex grid for irregular organic honeycomb cells"},
    "interference_rings": {"texture_fn": texture_interference_rings,  "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Newton ring four-source radial interference beating"},
    "lace_filigree":      {"texture_fn": texture_lace_filigree,       "paint_fn": paint_crosshatch_ink,     "variable_cc": False, "desc": "Orthogonal and diagonal sinusoidal cross-grid openwork"},
    "penrose_quasi":      {"texture_fn": texture_penrose_quasi,       "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Five 72°-spaced cosine projections Penrose quasicrystal tiling"},
    "hex_mandala":        {"texture_fn": texture_sacred_geometry,     "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Three 120°-offset plane waves Flower of Life hexagonal mandalas"},
    "stained_glass":      {"texture_fn": texture_stained_glass_voronoi,"paint_fn": paint_mosaic_tint,       "variable_cc": False, "desc": "Voronoi panes with random luminance and dark grout lines"},
    "topographic_dense":  {"texture_fn": texture_topographic_dense,   "paint_fn": paint_topographic_line,  "variable_cc": False, "desc": "35 tightly-spaced contour lines over multi-scale noise height field"},
    # ── Tribal & Ancient (✨) — Batch 2 (2026-03-28) ─────────────────────────
    "spiral_fern":        {"texture_fn": texture_maori_koru,          "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Maori koru logarithmic spiral fern frond uncoiling in tiled cells"},
    "zigzag_bands":       {"texture_fn": texture_polynesian_tapa,     "paint_fn": paint_crosshatch_ink,     "variable_cc": False, "desc": "Polynesian tapa cloth alternating zigzag and crosshatch band rows"},
    "radial_calendar":    {"texture_fn": texture_aztec_sun,           "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Aztec sun stone radial spoke and concentric ring calendar wheel"},
    "triple_knot":        {"texture_fn": texture_celtic_trinity,      "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Celtic triquetra three interlocked rings at 120° in tiled cells"},
    "diagonal_interlace": {"texture_fn": texture_viking_knotwork,     "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Viking diagonal over-under interlace braid with parity switching"},
    "diamond_blanket":    {"texture_fn": texture_native_geometric,    "paint_fn": paint_crosshatch_ink,     "variable_cc": False, "desc": "Native American L1 diamond blanket lattice with border stripes"},
    "step_fret":          {"texture_fn": texture_inca_step,           "paint_fn": paint_crosshatch_ink,     "variable_cc": False, "desc": "Inca step fret L-shape motif with alternating rotation tiling"},
    "concentric_dot_rings": {"texture_fn": texture_aboriginal_dots,   "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Aboriginal periodic concentric ring dot clusters on a regular grid"},
    "medallion_lattice":  {"texture_fn": texture_turkish_arabesque,   "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Ottoman crossed sinusoidal lattice producing interlaced medallion lines"},
    "eight_point_star":   {"texture_fn": texture_eight_point_star,    "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "8-pointed geometric star four-direction arm distance tiling"},
    "petal_frieze":       {"texture_fn": texture_egyptian_lotus,      "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Egyptian lotus frieze radial teardrop petal cluster with center stalk"},
    "cloud_scroll":       {"texture_fn": texture_chinese_cloud,       "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Chinese ruyi cloud L-inf rectangular ring scroll with corner softening"},
    # ── Natural Textures (🌿) — Batch 3 (2026-03-28) ─────────────────────────
    "marble_veining":     {"texture_fn": texture_marble_veining,      "paint_fn": paint_damascus_layer,     "variable_cc": False, "desc": "Turbulence-warped sinusoidal marble vein network with secondary veins"},
    "wood_burl":          {"texture_fn": texture_wood_burl,           "paint_fn": paint_pinstripe,          "variable_cc": False, "desc": "Multi-center swirling concentric ellipse burl figure with noise warp"},
    "seigaiha_scales":    {"texture_fn": texture_seigaiha_scales,     "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Japanese seigaiha overlapping arched half-circle scale tiles"},
    "ammonite_chambers":  {"texture_fn": texture_ammonite_chambers,   "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Ammonite log-spiral shell walls with radial suture divisions"},
    "peacock_eye":        {"texture_fn": texture_peacock_eye,         "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Peacock feather eye elliptical rings with 20-barb radial overlay"},
    "dragonfly_wing":     {"texture_fn": texture_dragonfly_wing,      "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Dragonfly wing dense Voronoi venation network with thin cell walls"},
    "insect_compound":    {"texture_fn": texture_insect_compound,     "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Insect compound eye hex close-packed ommatidium ring array"},
    "diatom_radial":      {"texture_fn": texture_diatom_radial,       "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Radial diatom microorganism 16-spoke rings and inter-spoke dots"},
    "coral_polyp":        {"texture_fn": texture_coral_polyp,         "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Coral polyp tiling 8-tentacle radial star with oral disk rings"},
    "birch_bark":         {"texture_fn": texture_birch_bark,          "paint_fn": paint_pinstripe,          "variable_cc": False, "desc": "Birch bark noise-warped horizontal lenticel bands with cracks"},
    "pine_cone_scale":    {"texture_fn": texture_pine_cone_scale,     "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Phyllotaxis dual diagonal sine families forming diamond scale tiles"},
    "geode_crystal":      {"texture_fn": texture_geode_crystal,       "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Geode Voronoi crystal facets with per-facet directional sheen lines"},
    # ── Tech & Circuit (⚙️) — Batch 4 (2026-03-28) ─────────────────────────
    "circuit_traces":  {"texture_fn": texture_circuit_traces,  "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "PCB orthogonal grid traces with via pad rings at intersections"},
    "hex_circuit":     {"texture_fn": texture_hex_circuit,     "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Hexagonal circuit grid three-direction parallel lines forming hex trace network"},
    "biomech_cables":  {"texture_fn": texture_biomech_cables,  "paint_fn": paint_pinstripe,          "variable_cc": False, "desc": "Sinusoidal twisted cable bundles with circumferential rib details"},
    "dendrite_web":    {"texture_fn": texture_dendrite_web,    "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Multi-scale fractal branching vein network via layered Voronoi cracks"},
    "crystal_lattice": {"texture_fn": texture_crystal_lattice, "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "45°-rotated diamond rhombus grid with atom nodes at lattice vertices"},
    "chainmail_hex":   {"texture_fn": texture_chainmail_hex,   "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Interlocking circular wire rings in hexagonal close-pack arrangement"},
    "graphene_hex":    {"texture_fn": texture_graphene_hex,    "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Honeycomb bond network with atom nodes at graphene unit cell positions"},
    "gear_mesh":       {"texture_fn": texture_gear_mesh,       "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Toothed circular gear with spokes and hub — tiled mechanical mesh"},
    "vinyl_record":    {"texture_fn": texture_vinyl_record,    "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Ultra-fine concentric groove rings with label area and spindle hole"},
    "fiber_optic":     {"texture_fn": texture_fiber_optic,     "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Hexagonally close-packed fiber core cross-sections with cladding ring"},
    "sonar_ping":      {"texture_fn": texture_sonar_ping,      "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Expanding concentric rings from multiple offset radar/sonar source points"},
    "waveform_stack":  {"texture_fn": texture_waveform_stack,  "paint_fn": paint_pinstripe,          "variable_cc": False, "desc": "Multiple layered oscilloscope sine traces offset vertically across surface"},
    # ── Art Deco & Geometric (🎨) — Batch 5 (2026-03-28) ─────────────────────────
    "art_deco_fan":   {"texture_fn": texture_art_deco_fan,   "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Tiled semicircular fans with radiating spokes and concentric arc bands"},
    "chevron_stack":  {"texture_fn": texture_chevron_stack,  "paint_fn": paint_pinstripe,          "variable_cc": False, "desc": "Stacked V-chevrons via triangular-wave centerline periodic in y"},
    "quatrefoil":     {"texture_fn": texture_quatrefoil,     "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Four overlapping circle-arc leaves forming a Gothic quatrefoil foil lattice"},
    "herringbone":    {"texture_fn": texture_herringbone,    "paint_fn": paint_crosshatch_ink,     "variable_cc": False, "desc": "Alternating-parity diagonal stripe directions in staggered rectangular cells"},
    "basket_weave":   {"texture_fn": texture_basket_weave,   "paint_fn": paint_crosshatch_ink,     "variable_cc": False, "desc": "Alternating horizontal and vertical strand blocks in 2x2 parity grid"},
    "houndstooth":    {"texture_fn": texture_houndstooth,    "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Combined offset 45-degree rotated checkerboards creating 4-pointed star tile pattern"},
    "argyle":         {"texture_fn": texture_argyle,         "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "L1-norm diamond outline grid with diagonal crosshatch in alternate diamonds"},
    "tartan":         {"texture_fn": texture_tartan,         "paint_fn": paint_pinstripe,          "variable_cc": False, "desc": "Intersecting stripe families with sett widths forming plaid grid"},
    "op_art_rings":   {"texture_fn": texture_op_art_rings,   "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Concentric L-inf square rings creating optical pulsation illusion"},
    "moire_grid":     {"texture_fn": texture_moire_grid,     "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Two slightly angled parallel line families creating interference fringe patterns"},
    "lozenge_tile":   {"texture_fn": texture_lozenge_tile,   "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Offset-row diamond lozenge shapes with L1-norm border outline"},
    "ogee_lattice":   {"texture_fn": texture_ogee_lattice,   "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Sinusoidally-warped grid creating S-curve Gothic ogee arch lattice shapes"},
    # ── Mathematical & Fractal (🌀) — Batch 6 (2026-03-28) ─────────────────────────
    "reaction_diffusion":  {"texture_fn": texture_reaction_diffusion,  "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Gray-Scott Turing activator-inhibitor spot/stripe morphogenesis approximation"},
    "fractal_fern":        {"texture_fn": texture_fractal_fern,        "paint_fn": paint_fractal_fern_tint,  "variable_cc": False, "desc": "Barnsley fern IFS attractor — green-tinted fractal leaf pattern with visible stem structure"},
    "hilbert_curve":       {"texture_fn": texture_hilbert_curve,       "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Hilbert space-filling curve maze — walls rendered between non-adjacent cells"},
    "lorenz_slice":        {"texture_fn": texture_lorenz_slice,        "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Lorenz butterfly attractor density projected onto x/z plane via ODE iteration"},
    "julia_boundary":      {"texture_fn": texture_julia_boundary,      "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Julia set z-squared-plus-c fractal boundary smooth escape-time coloring"},
    "wave_standing":       {"texture_fn": texture_wave_standing,       "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "2D Chladni standing wave nodal lines from orthogonal and diagonal cosine products"},
    "lissajous_web":       {"texture_fn": texture_lissajous_web,       "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Lissajous web sin(3x)-sin(4y+pi/2) implicit zero-contour family tiled periodically"},
    "dragon_curve":        {"texture_fn": texture_dragon_curve,        "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Dragon curve fractal approximation via 5 levels of 45-degree-rotated right-angle grids"},
    "diffraction_grating": {"texture_fn": texture_diffraction_grating, "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Holographic diffraction grating — 6 sinusoidal gratings at 30-degree intervals squared"},
    "perlin_terrain":      {"texture_fn": texture_perlin_terrain,      "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Multi-octave terrain noise with ridged sharpening for erosion scar morphology"},
    "phyllotaxis":         {"texture_fn": texture_phyllotaxis,         "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Fibonacci phyllotaxis golden-angle seed spiral packing distance field"},
    "truchet_flow":        {"texture_fn": texture_truchet_flow,        "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Truchet quarter-circle arc tiles — random orientation creates organic flowing paths"},
    # ── Op-Art & Visual Illusions (🔮) — Batch 7 (2026-03-28) ─────────────────────────
    "concentric_op":       {"texture_fn": texture_concentric_op,       "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Bridget Riley dual-frequency concentric bands producing optical vibration beat"},
    "checker_warp":        {"texture_fn": texture_checker_warp,        "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Sine-warped checkerboard — sinusoidal displacement creates bulging impossible grid illusion"},
    "barrel_distort":      {"texture_fn": texture_barrel_distort,      "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Barrel lens distortion applied to checkerboard — straight lines bow outward from center"},
    "moire_interference":  {"texture_fn": texture_moire_interference,  "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Two grids at 7% different scale and 15-degree rotation producing moiré beat fringes"},
    "twisted_rings":       {"texture_fn": texture_twisted_rings,       "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Concentric rings twisted by radius via Archimedean phase — spring vortex illusion"},
    "spiral_hypnotic":     {"texture_fn": texture_spiral_hypnotic,     "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Archimedean spiral banded by phase offset — rotating depth vortex optical illusion"},
    "necker_grid":         {"texture_fn": texture_necker_grid,         "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Isometric cube tiling with three-brightness face shading — Necker cube 3D/2D illusion"},
    "radial_pulse":        {"texture_fn": texture_radial_pulse,        "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "24 radial spokes with radius-modulated width — apparent inward pulse motion illusion"},
    "hex_op":              {"texture_fn": texture_hex_op,              "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Nested hexagonal shells via hex Chebyshev distance — 3D optical tunnel illusion"},
    "pinwheel_tiling":     {"texture_fn": texture_pinwheel_tiling,     "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "7 golden-angle overlapping grids approximate aperiodic pinwheel — no repeating tile direction"},
    "impossible_grid":     {"texture_fn": texture_impossible_grid,     "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Phase-inverted alternating square cells with banded L-inf metric — impossible connectivity illusion"},
    "rose_curve":          {"texture_fn": texture_rose_curve,          "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Rhodonea k=5 polar rose tiled field — five-petal outline with radial gradient fill"},
    # ── Art Deco Depth + Textile (🏛️🧵) — Batch 8 (2026-03-28) ────────────────────────
    "art_deco_sunburst":   {"texture_fn": texture_art_deco_sunburst,   "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Chrysler Building Art Deco sunburst — 36 radial spokes with 5 concentric decorative ring bands"},
    "art_deco_chevron":    {"texture_fn": texture_art_deco_chevron,    "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Bold Art Deco double-stripe nested V chevrons with wide gaps — classic 1920s style"},
    "greek_meander":       {"texture_fn": texture_greek_meander,       "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Greek key meander right-angle hook spiral motif tiled in alternating-parity rows"},
    "star_tile_mosaic":    {"texture_fn": texture_moroccan_zellige,    "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Moroccan zellige 8-pointed star — two overlapping L-inf norms create Islamic star tile"},
    "escher_reptile":      {"texture_fn": texture_escher_reptile,      "paint_fn": paint_hex_emboss,         "variable_cc": False, "desc": "Escher-style hex reptile tessellation — alternating shaded cells with organic boundary deformation"},
    "constructivist":      {"texture_fn": texture_constructivist,      "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Soviet Constructivist — orthogonal grid plus 45-degree diagonals and bold horizontal band"},
    "bauhaus_system":      {"texture_fn": texture_bauhaus_system,      "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Bauhaus primary form grid — circle, square, and diamond outline shapes alternating in cells"},
    "celtic_plait":        {"texture_fn": texture_celtic_plait,        "paint_fn": paint_celtic_emboss,      "variable_cc": False, "desc": "Celtic plait braid — two diagonal strand families with alternating over-under weave"},
    "cane_weave":          {"texture_fn": texture_cane_weave,          "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Cane/rattan weave — orthogonal H+V basket grid with alternating over-under crossings at each cell"},
    "cable_knit":          {"texture_fn": texture_cable_knit,          "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Cable knit — vertical rope-twist columns with two strands crossing per period"},
    "damask_brocade":      {"texture_fn": texture_damask_brocade,      "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "Damask brocade — four-petal rose with outer ring and diamond accent, figure-vs-ground contrast"},
    "tatami_grid":         {"texture_fn": texture_tatami_grid,         "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Tatami grid — Japanese 2:1 mat rectangles staggered alternating rows with border lines"},
    # ── Final 4 — To 100 Patterns (🏁 Batch 9, 2026-03-28) ──────────────────────────
    "hypocycloid":         {"texture_fn": texture_hypocycloid,         "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Tiled 5-cusped Spirograph hypocycloid — parametric star outline from k=5 hypotrochoid curve"},
    "voronoi_relaxed":     {"texture_fn": texture_voronoi_relaxed,     "paint_fn": paint_interference_shift, "variable_cc": False, "desc": "Centroidal Voronoi relaxed cells — jitter-grid seeds give uniform organic cell borders"},
    "wave_ripple_2d":      {"texture_fn": texture_wave_ripple_2d,      "paint_fn": paint_ripple_reflect,     "variable_cc": False, "desc": "2D circular wave interference from 4 sources — constructive/destructive ring patterns"},
    "sierpinski_tri":      {"texture_fn": texture_sierpinski_tri,      "paint_fn": paint_mosaic_tint,        "variable_cc": False, "desc": "Sierpinski gasket via Pascal triangle mod 2 — bitwise integer test produces deep fractal"},
}

# Stubs for engine/chameleon.py functions - real implementations injected at startup.
# These exist only so MONOLITHIC_REGISTRY dict literal can evaluate without NameError.
# All are overridden by globals().update(_ch_fns) + MONOLITHIC_REGISTRY patch below.
def _chameleon_stub_paint(paint, shape, mask, seed, pm, bb): return paint
def _chameleon_stub_spec(shape, mask, seed, sm):
    # np is module-level — no local import needed.
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 219; spec[:,:,1] = 12; spec[:,:,2] = 16
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec
spec_chameleon_pro       = _chameleon_stub_spec
paint_chameleon_arctic   = _chameleon_stub_paint
paint_chameleon_amethyst = _chameleon_stub_paint
paint_chameleon_copper   = _chameleon_stub_paint
paint_chameleon_emerald  = _chameleon_stub_paint
paint_chameleon_midnight = _chameleon_stub_paint
paint_chameleon_obsidian = _chameleon_stub_paint
paint_chameleon_ocean    = _chameleon_stub_paint
paint_chameleon_phoenix  = _chameleon_stub_paint
paint_chameleon_venom    = _chameleon_stub_paint
paint_mystichrome        = _chameleon_stub_paint

# Stubs for engine/prizm.py functions - real implementations injected at startup.
def _prizm_stub_paint(paint, shape, mask, seed, pm, bb): return paint
def _prizm_stub_spec(shape, mask, seed, sm):
    # np is module-level — no local import needed.
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 225; spec[:,:,1] = 14; spec[:,:,2] = 30
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec
spec_prizm_adaptive      = _prizm_stub_spec
spec_prizm_arctic        = _prizm_stub_spec
spec_prizm_black_rainbow = _prizm_stub_spec
spec_prizm_duochrome     = _prizm_stub_spec
spec_prizm_ember         = _prizm_stub_spec
spec_prizm_holographic   = _prizm_stub_spec
spec_prizm_iridescent    = _prizm_stub_spec
spec_prizm_midnight      = _prizm_stub_spec
spec_prizm_mystichrome   = _prizm_stub_spec
spec_prizm_oceanic       = _prizm_stub_spec
spec_prizm_phoenix       = _prizm_stub_spec
spec_prizm_solar         = _prizm_stub_spec
spec_prizm_venom         = _prizm_stub_spec
# Wave 2 prizm stubs (replaced by prizm.py at load time)
spec_prizm_galaxy_dust   = _prizm_stub_spec
spec_prizm_sunset_strip  = _prizm_stub_spec
spec_prizm_toxic_waste   = _prizm_stub_spec
spec_prizm_chrome_rose   = _prizm_stub_spec
spec_prizm_deep_space    = _prizm_stub_spec
spec_prizm_copper_flame  = _prizm_stub_spec
spec_prizm_alien_skin    = _prizm_stub_spec
spec_prizm_titanium      = _prizm_stub_spec
spec_prizm_aurora_shift  = _prizm_stub_spec
spec_prizm_candy_paint   = _prizm_stub_spec
paint_prizm_adaptive     = _prizm_stub_paint
paint_prizm_arctic       = _prizm_stub_paint
paint_prizm_black_rainbow= _prizm_stub_paint
paint_prizm_duochrome    = _prizm_stub_paint
paint_prizm_ember        = _prizm_stub_paint
paint_prizm_holographic  = _prizm_stub_paint
paint_prizm_iridescent   = _prizm_stub_paint
paint_prizm_midnight     = _prizm_stub_paint
paint_prizm_mystichrome  = _prizm_stub_paint
paint_prizm_oceanic      = _prizm_stub_paint
paint_prizm_phoenix      = _prizm_stub_paint
paint_prizm_solar        = _prizm_stub_paint
paint_prizm_venom        = _prizm_stub_paint
paint_prizm_galaxy_dust  = _prizm_stub_paint
paint_prizm_sunset_strip = _prizm_stub_paint
paint_prizm_toxic_waste  = _prizm_stub_paint
paint_prizm_chrome_rose  = _prizm_stub_paint
paint_prizm_deep_space   = _prizm_stub_paint
paint_prizm_copper_flame = _prizm_stub_paint
paint_prizm_alien_skin   = _prizm_stub_paint
paint_prizm_titanium     = _prizm_stub_paint
paint_prizm_aurora_shift = _prizm_stub_paint
paint_prizm_candy_paint  = _prizm_stub_paint

# --- MONOLITHIC FINISHES (can't decompose) ---
MONOLITHIC_REGISTRY = {
    "aurora":             (spec_aurora_borealis_mono,  paint_aurora_borealis_mono),  # WEAK-040: upgraded from legacy 2-sine wave to domain-warped curtain aurora
    "cel_shade":          (spec_cel_shade,     paint_cel_shade),
    "chameleon_arctic":   (spec_chameleon_pro, paint_chameleon_arctic),
    "chameleon_amethyst": (spec_chameleon_pro, paint_chameleon_amethyst),
    "chameleon_copper":   (spec_chameleon_pro, paint_chameleon_copper),
    "chameleon_emerald":  (spec_chameleon_pro, paint_chameleon_emerald),
    "chameleon_midnight": (spec_chameleon_pro, paint_chameleon_midnight),
    "chameleon_obsidian": (spec_chameleon_pro, paint_chameleon_obsidian),
    "chameleon_ocean":    (spec_chameleon_pro, paint_chameleon_ocean),
    "chameleon_phoenix":  (spec_chameleon_pro, paint_chameleon_phoenix),
    "chameleon_venom":    (spec_chameleon_pro, paint_chameleon_venom),
    "cs_chrome_shift":(spec_cs_chrome_shift, paint_cs_chrome_shift),
    "cs_complementary":(spec_cs_complementary, paint_cs_complementary),
    "cs_cool":       (spec_cs_cool,      paint_cs_cool),
    "cs_deepocean":  (spec_cs_deepocean,  paint_cs_deepocean),
    "cs_earth":      (spec_cs_earth,     paint_cs_earth),
    "cs_emerald":    (spec_cs_emerald,    paint_cs_emerald),
    "cs_extreme":    (spec_cs_extreme,   paint_cs_extreme),
    "cs_inferno":    (spec_cs_inferno,    paint_cs_inferno),
    "cs_monochrome": (spec_cs_monochrome, paint_cs_monochrome),
    "cs_mystichrome":(spec_cs_mystichrome,paint_cs_mystichrome),
    "cs_nebula":     (spec_cs_nebula,     paint_cs_nebula),
    "cs_neon_shift": (spec_cs_neon_shift, paint_cs_neon_shift),
    "cs_ocean_shift":(spec_cs_ocean_shift,paint_cs_ocean_shift),
    "cs_prism_shift":(spec_cs_prism_shift,paint_cs_prism_shift),
    "cs_rainbow":    (spec_cs_rainbow,   paint_cs_rainbow),
    "cs_solarflare": (spec_cs_solarflare, paint_cs_solarflare),
    "cs_split":      (spec_cs_split,     paint_cs_split),
    "cs_subtle":     (spec_cs_subtle,    paint_cs_subtle),
    "cs_supernova":  (spec_cs_supernova,  paint_cs_supernova),
    "cs_triadic":    (spec_cs_triadic,   paint_cs_triadic),
    "cs_vivid":      (spec_cs_vivid,     paint_cs_vivid),
    "cs_warm":       (spec_cs_warm,      paint_cs_warm),
    "ember_glow":   (spec_ember_glow,   paint_ember_glow),
    "frost_bite":   (spec_frost_bite,    paint_subtle_flake),
    "galaxy":       (spec_galaxy,        paint_galaxy_nebula),
    "glitch":             (spec_glitch,        paint_glitch),
    "holographic_wrap":   (spec_holographic,   paint_holographic_full),
    "liquid_metal": (spec_liquid_metal,  paint_liquid_reflect),
    "mystichrome":        (spec_chameleon_pro, paint_mystichrome),
    "neon_glow":    (spec_neon_glow,     paint_neon_edge),
    "oil_slick":    (spec_oil_slick,     paint_oil_slick_full),  # WEAK-039 FIX: was paint_oil_slick (10% sine, near-invisible); full = FBM thin-film 360° hue at 70% blend
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
    "prizm_galaxy_dust":  (spec_prizm_galaxy_dust,  paint_prizm_galaxy_dust),
    "prizm_sunset_strip": (spec_prizm_sunset_strip, paint_prizm_sunset_strip),
    "prizm_toxic_waste":  (spec_prizm_toxic_waste,  paint_prizm_toxic_waste),
    "prizm_chrome_rose":  (spec_prizm_chrome_rose,  paint_prizm_chrome_rose),
    "prizm_deep_space":   (spec_prizm_deep_space,   paint_prizm_deep_space),
    "prizm_copper_flame": (spec_prizm_copper_flame, paint_prizm_copper_flame),
    "prizm_alien_skin":   (spec_prizm_alien_skin,   paint_prizm_alien_skin),
    "prizm_titanium":     (spec_prizm_titanium,     paint_prizm_titanium),
    "prizm_aurora_shift": (spec_prizm_aurora_shift, paint_prizm_aurora_shift),
    "prizm_candy_paint":  (spec_prizm_candy_paint,  paint_prizm_candy_paint),
    "radioactive":        (spec_radioactive,   paint_radioactive),
    "rust":         (spec_rust,          paint_rust_corrosion),
    "scorched":           (spec_scorched,      paint_scorched),
    "static":             (spec_static,        paint_static),
    "thermochromic":      (spec_thermochromic, paint_thermochromic),
    "weathered_paint": (spec_weathered_paint, paint_weathered_peel),
    "worn_chrome":  (spec_worn_chrome,   paint_patina),
    # ── RESEARCH-008: New Exotic Monolithic Bases ──────────────
    "oil_slick_base":      (spec_oil_slick_base,      paint_oil_slick_full),
    "thermal_titanium":    (spec_thermal_titanium,     paint_thermal_titanium),
    "galaxy_nebula_base":  (spec_galaxy_nebula_base,   paint_galaxy_nebula_full),
    # ── RESEARCH SESSION 6: 6 New Monolithic Finishes (2026-03-29) ──────────
    "aurora_borealis_mono":  (spec_aurora_borealis_mono,  paint_aurora_borealis_mono),
    "deep_space_void":       (spec_deep_space_void,        paint_deep_space_void),
    "polished_obsidian_mono":(spec_polished_obsidian_mono, paint_polished_obsidian_mono),
    "patinated_bronze":      (spec_patinated_bronze,       paint_patinated_bronze),
    "reactive_plasma":       (spec_reactive_plasma,        paint_reactive_plasma),
    "molten_metal":          (spec_molten_metal,           paint_molten_metal),
}



# --- CHAMELEON + PRIZM MODULE OVERRIDES (V5 Extracted Modules) ---
# Uses importlib.util to load modules BY FILE PATH - bypasses engine/__init__.py
# and avoids the circular import (engine/__init__ re-imports shokker_engine_v2).
# Edit engine/chameleon.py and engine/prizm.py directly for these finishes.
try:
    import sys as _sys, os as _os, importlib.util as _ilu
    _engine_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "engine")

    # Load chameleon module directly (unique name avoids package cache conflict)
    _ch_path = _os.path.join(_engine_dir, "chameleon.py")
    if _os.path.exists(_ch_path):
        _ch_spec = _ilu.spec_from_file_location("__shokker_chameleon__", _ch_path)
        _chameleon_mod = _ilu.module_from_spec(_ch_spec)
        _ch_spec.loader.exec_module(_chameleon_mod)
        _chameleon_mod.integrate_chameleon(_sys.modules[__name__])
        # Inject all paint_* and spec_* functions into this module's namespace
        _ch_fns = {k: v for k, v in vars(_chameleon_mod).items()
                   if k.startswith('paint_') or k.startswith('spec_')}
        globals().update(_ch_fns)
        # Also patch MONOLITHIC_REGISTRY which captured the stub at construction time.
        # The dict stores function objects directly - replace BOTH spec and paint with real ones.
        _real_spec_ch_pro = _ch_fns.get('spec_chameleon_pro')
        if _real_spec_ch_pro:
            _chameleon_keys = [k for k, v in MONOLITHIC_REGISTRY.items()
                               if k.startswith('chameleon_') or k == 'mystichrome']
            for _ck in _chameleon_keys:
                _old_spec, _old_paint = MONOLITHIC_REGISTRY[_ck]
                # Use real paint from chameleon module (e.g. paint_chameleon_arctic); fallback to existing
                _real_paint = _ch_fns.get('paint_' + _ck, _old_paint)
                MONOLITHIC_REGISTRY[_ck] = (_real_spec_ch_pro, _real_paint)
        print(f"[V5] Chameleon module loaded ({len(_ch_fns)} functions)")
    else:
        print("[V5] engine/chameleon.py not found - using legacy chameleon stubs")
except Exception as _ch_err:
    print(f"[V5] Chameleon load error: {_ch_err}")

try:
    # Load prizm module directly
    _pz_path = _os.path.join(_engine_dir, "prizm.py")
    if _os.path.exists(_pz_path):
        _pz_spec = _ilu.spec_from_file_location("__shokker_prizm__", _pz_path)
        _prizm_mod = _ilu.module_from_spec(_pz_spec)
        _pz_spec.loader.exec_module(_prizm_mod)
        _prizm_mod.integrate_prizm(_sys.modules[__name__])
        _pz_fns = {k: v for k, v in vars(_prizm_mod).items()
                   if k.startswith('paint_') or k.startswith('spec_')}
        globals().update(_pz_fns)
        # Patch MONOLITHIC_REGISTRY prizm entries - same reason as chameleon above.
        for _pzk in [k for k in MONOLITHIC_REGISTRY if k.startswith('prizm_')]:
            _old_spec, _old_paint = MONOLITHIC_REGISTRY[_pzk]
            _new_spec  = _pz_fns.get(f'spec_{_pzk}',  _old_spec)
            _new_paint = _pz_fns.get(f'paint_{_pzk}', _old_paint)
            MONOLITHIC_REGISTRY[_pzk] = (_new_spec, _new_paint)
        print(f"[V5] Prizm module loaded ({len(_pz_fns)} functions)")
    else:
        print("[V5] engine/prizm.py not found - using legacy prizm stubs")
except Exception as _pz_err:
    print(f"[V5] Prizm load error: {_pz_err}")

# --- LAZY-LOAD EXPANSION MODULES ---
# Expansion modules (24K, Pattern Expansion, Color Monolithics, Paradigm, Fusions,
# Atelier) are deferred until the first render request to speed up server startup.
# _ensure_expansions_loaded() is called once at the top of build_multi_zone.
import sys as _sys

_expansions_loaded = False

def _ensure_expansions_loaded():
    """Lazy-load all expansion modules on first render. INTERNAL.

    Idempotent — subsequent calls return immediately. Imports are wrapped
    in try/except so a missing/broken expansion never blocks the engine
    from booting; the offending pack is logged and skipped.

    Side effects:
        Mutates BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY by
        adding the expansion entries.
    """
    global _expansions_loaded
    if _expansions_loaded:
        return
    _expansions_loaded = True
    _t0 = time.time()
    _this_module = _sys.modules[__name__]

    # --- 24K ARSENAL EXPANSION ---
    try:
        import shokker_24k_expansion as _exp24k
        _exp24k.integrate_expansion(_this_module)
    except ImportError:
        print("[24K Arsenal] Expansion module not found - running with base 55/55/50 finishes")
    except Exception as e:
        print(f"[24K Arsenal] Expansion load error: {e}")

    # --- PATTERN EXPANSION (Decades, Flames, Music, Astro v2, Hero, Reactive) ---
    try:
        from engine.pattern_expansion import NEW_PATTERNS
        PATTERN_REGISTRY.update(NEW_PATTERNS)
    except Exception as _e:
        pass

    # --- COLOR MONOLITHICS EXPANSION (260+ color-changing finishes) ---
    try:
        import shokker_color_monolithics as _clr_mono
        _clr_mono.integrate_color_monolithics(_this_module)
    except ImportError:
        print("[Color Monolithics] Module not found - running without color finishes")
    except Exception as e:
        print(f"[Color Monolithics] Load error: {e}")

    # --- PARADIGM EXPANSION (Exotic Materials - PBR physics exploits) ---
    try:
        import shokker_paradigm_expansion as _paradigm
        _paradigm.integrate_paradigm(_this_module)
    except ImportError:
        print("[PARADIGM] Module not found - running without paradigm materials")
    except Exception as e:
        print(f"[PARADIGM] Load error: {e}")

    # --- FUSIONS EXPANSION (150 Paradigm Shift Hybrid Materials) ---
    try:
        import shokker_fusions_expansion as _fusions
        _fusions.integrate_fusions(_this_module)
    except ImportError:
        print("[FUSIONS] Module not found - running without paradigm shift fusions")
    except Exception as e:
        print(f"[FUSIONS] Load error: {e}")

    # --- ATELIER EXPANSION (Ultra-Detail / Pro Grade finishes) ---
    try:
        import shokker_atelier_expansion as _atelier
        _atelier.integrate_atelier(_this_module)
    except ImportError:
        print("[Atelier] Module not found - running without ultra-detail finishes")
    except Exception as e:
        print(f"[Atelier] Load error: {e}")

    if "_spb_wrap_pattern_registry_detail" in globals():
        _spb_wrap_pattern_registry_detail()
    if "_spb_apply_regular_pattern_rebuilds" in globals():
        _spb_apply_regular_pattern_rebuilds()
    if "_spb_apply_pattern_quality_floor" in globals():
        _spb_apply_pattern_quality_floor()
    if "_spb_apply_standalone_monolithic_detail_profiles" in globals():
        _spb_apply_standalone_monolithic_detail_profiles()
    if "_spb_wire_regular_base_v2_overrides" in globals():
        _spb_wire_regular_base_v2_overrides()
    if "_normalize_classic_foundation_contract" in globals():
        _normalize_classic_foundation_contract()
    if "_spb_apply_regular_base_quality_wrappers" in globals():
        _spb_apply_regular_base_quality_wrappers()
    if "_spb_apply_monolithic_contract_guards" in globals():
        _spb_apply_monolithic_contract_guards()

    print(f"  [Lazy-Load] All expansion modules loaded in {time.time()-_t0:.2f}s")


# ================================================================
# REGISTRY MERGE — Bring in ALL entries from engine.registry that didn't
# survive the circular import chain. This includes:
#   - Foundation bases (f_*) from base_registry_data.py
#   - Image-based patterns from assets/patterns/ directory
#   - Staging decade patterns from _staging/pattern_upgrades/
#   - User pattern examples from basespatterns_examples/
#   - Any other entries added by engine/registry.py's _build_registries()
# ================================================================
try:
    from engine.registry import _build_registries as _br
    _full_base, _full_pat, _full_mono, _full_fin, _full_fus = _br()
    _added_b = _added_p = _added_m = 0
    for k, v in _full_base.items():
        if k not in BASE_REGISTRY:
            BASE_REGISTRY[k] = v
            _added_b += 1
    for k, v in _full_pat.items():
        if k not in PATTERN_REGISTRY:
            PATTERN_REGISTRY[k] = v
            _added_p += 1
    for k, v in _full_mono.items():
        if k not in MONOLITHIC_REGISTRY:
            MONOLITHIC_REGISTRY[k] = v
            _added_m += 1
    if _added_b or _added_p or _added_m:
        print(f"  Engine loaded: {len(BASE_REGISTRY)} bases, {len(PATTERN_REGISTRY)} patterns, {len(MONOLITHIC_REGISTRY)} monolithics")
        if _added_b: print(f"  [Registry merge] +{_added_b} bases (Foundation, expansions)")
        if _added_p: print(f"  [Registry merge] +{_added_p} patterns (image-based, decades, examples)")
        if _added_m: print(f"  [Registry merge] +{_added_m} monolithics")
except Exception as _merge_err:
    print(f"  [Registry merge] Warning: {_merge_err}")

# Register Dual Color Shift monolithics
try:
    from engine.dual_color_shift import DUAL_SHIFT_MONOLITHICS
    _ds_added = 0
    for k, v in DUAL_SHIFT_MONOLITHICS.items():
        if k not in MONOLITHIC_REGISTRY:
            MONOLITHIC_REGISTRY[k] = v
            _ds_added += 1
    if _ds_added:
        print(f"  [Dual Shift] Registered {_ds_added} color shift monolithics")
except Exception as _ds_err:
    print(f"  [Dual Shift] Warning: {_ds_err}")

# Register CS Duo to Micro-Flake upgrades (replaces old flat-gradient duos)
try:
    from engine.micro_flake_shift import CS_DUO_MICRO_MONOLITHICS
    _csd_added = 0
    for k, v in CS_DUO_MICRO_MONOLITHICS.items():
        MONOLITHIC_REGISTRY[k] = v  # Overwrite old entries
        _csd_added += 1
    if _csd_added:
        print(f"  [CS Duo-Micro] Upgraded {_csd_added} color shift duos to micro-flake")
except Exception as _csd_err:
    print(f"  [CS Duo-Micro] Warning: {_csd_err}")

# Register Micro-Flake Shift monolithics
try:
    from engine.micro_flake_shift import MICRO_SHIFT_MONOLITHICS
    _ms_added = 0
    for k, v in MICRO_SHIFT_MONOLITHICS.items():
        if k not in MONOLITHIC_REGISTRY:
            MONOLITHIC_REGISTRY[k] = v
            _ms_added += 1
    if _ms_added:
        print(f"  [Micro Shift] Registered {_ms_added} micro-flake shift monolithics")
except Exception as _ms_err:
    print(f"  [Micro Shift] Warning: {_ms_err}")

# Register HyperFlip perceptual color-shift monolithics
try:
    from engine.perceptual_color_shift import HYPERFLIP_MONOLITHICS
    _hf_added = 0
    for k, v in HYPERFLIP_MONOLITHICS.items():
        MONOLITHIC_REGISTRY[k] = v
        _hf_added += 1
    if _hf_added:
        print(f"  [HyperFlip] Registered {_hf_added} perceptual color-shift monolithics")
except Exception as _hf_err:
    print(f"  [HyperFlip] Warning: {_hf_err}")

# Wire missing UI patterns to closest existing patterns.
# 2026-04-21 HEENAN OVERNIGHT iter 3: repaired 3 broken targets whose
# originals (`chrome_edge`, `shimmer_pearl_ripple`, `glow_pulse`) did
# not exist in PATTERN_REGISTRY — the fallback loop silently skipped
# them, leaving the picker entries unrenderable. Replaced with the
# closest existing semantic equivalent so the painter gets SOMETHING
# rather than silent no-render.
_PATTERN_FALLBACKS = {
    'rune_symbols': 'norse_rune',
    'iridescent_fog': 'shimmer_spectral_mesh',
    'chrome_delete_edge':   'shimmer_chrome_flux',      # was 'chrome_edge' (missing)
    'carbon_clearcoat_lock': 'carbon_fiber',
    'racing_scratch': 'racing_stripe',
    'pearlescent_flip':     'shimmer_prism_frost',     # was 'shimmer_pearl_ripple' (missing)
    'satin_wax': 'board_wax',
    'uv_night_accent':      'shimmer_neon_weft',       # was 'glow_pulse' (missing)
}
_pat_wired = 0
for _pk, _pv_target in _PATTERN_FALLBACKS.items():
    if _pk not in PATTERN_REGISTRY and _pv_target in PATTERN_REGISTRY:
        PATTERN_REGISTRY[_pk] = PATTERN_REGISTRY[_pv_target]
        _pat_wired += 1
if _pat_wired:
    print(f"  [Pattern Fallback] Wired {_pat_wired} missing patterns to closest equivalents")

# 2026-04-21 HEENAN OVERNIGHT iter 3: UI-visible pattern id aliases.
# Two categories covered here:
#
#  a) Cross-registry rename aliases (HB2, H4HR-1, H4HR-2): the JS side
#     (paint-booth-0-finish-data.js + state-zones _SPB_LEGACY_ID_MIGRATIONS)
#     renamed these ids to disambiguate from colliding MONOLITHIC/BASE
#     ids, but Python PATTERN_REGISTRY still uses the legacy un-suffixed
#     keys. These aliases point the new canonical id at the exact same
#     render tuple — identical output, no saved-config risk.
#
#  b) Family-prefix semantic aliases (geo_*, nature_*, tribal_*):
#     previously unrenderable family-prefixed ids now render by aliasing
#     to the closest semantic equivalent in PATTERN_REGISTRY. Painter-
#     facing change: selecting the family id now produces visible output
#     (previously silent no-render). The 12 remaining family patterns
#     with no adequate semantic match are de-exposed from PATTERN_GROUPS
#     in paint-booth-0-finish-data.js (so the picker no longer shows
#     dead entries).
_UI_PATTERN_ALIASES = {
    # --- (a) Cross-registry renames ---
    'shokk_cipher_pattern':     'shokk_cipher',         # HB2
    'dragonfly_wing_pattern':   'dragonfly_wing',       # H4HR-1
    'carbon_weave_pattern':     'carbon_weave',         # H4HR-2
    # --- (b) Family-prefix semantic aliases ---
    'geo_fractal_triangle':     'fractal',              # fractal-triangle → generic fractal
    'geo_hilbert_curve':        'hilbert_curve',        # exact core match
    'nature_bark_rough':        'birch_bark',           # rough tree-bark texture
    'nature_water_ripple_pat':  'ripple',               # water ripple
    'tribal_celtic_spiral':     'celtic_knot',          # celtic knotwork family
    'tribal_norse_runes':       'norse_rune',           # norse rune glyphs
}
_alias_wired = 0
for _ak, _av_target in _UI_PATTERN_ALIASES.items():
    if _ak not in PATTERN_REGISTRY and _av_target in PATTERN_REGISTRY:
        PATTERN_REGISTRY[_ak] = PATTERN_REGISTRY[_av_target]
        _alias_wired += 1
if _alias_wired:
    print(f"  [UI Alias] Wired {_alias_wired} UI-exposed pattern ids to canonical Python render functions")


def _spb_normalize01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _spb_hash_seed(text):
    h = 2166136261
    for ch in str(text):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _spb_micro_detail(shape, seed, family=0):
    h, w = shape
    yy, xx = get_mgrid((h, w))
    s = int(seed) + int(family) * 7919
    a = np.sin((xx + s * 0.17) * (0.73 + (family % 5) * 0.07) + (yy - s * 0.11) * 0.19)
    b = np.sin((yy + s * 0.13) * (0.81 + (family % 7) * 0.05) - (xx + s * 0.07) * 0.23)
    c = np.sin((xx * 1.91 + yy * 1.37) + s * 0.031)
    fine = _spb_normalize01(a * 0.46 + b * 0.34 + c * 0.20)
    sparkle = (fine > (0.91 - min(0.05, (family % 6) * 0.006))).astype(np.float32)
    return fine, sparkle


def _spb_frac(arr):
    return arr - np.floor(arr)


def _spb_gridline(coord, freq, width=0.035, phase=0.0):
    pos = _spb_frac(coord * float(freq) + float(phase))
    dist = np.minimum(pos, 1.0 - pos)
    return np.exp(-((dist / max(float(width), 1e-4)) ** 2)).astype(np.float32)


def _spb_hash_field(shape, seed):
    h, w = shape
    yy, xx = get_mgrid((h, w))
    v = np.sin((xx + 19.17) * 12.9898 + (yy + 73.31) * 78.233 + seed * 0.037719) * 43758.5453
    return _spb_frac(v).astype(np.float32)


def _spb_hex_lines(xf, yf, freq, width=0.028, phase=0.0):
    return np.clip(
        _spb_gridline(xf, freq, width, phase)
        + _spb_gridline(xf * 0.5 + yf * 0.8660254, freq, width, phase * 0.73)
        + _spb_gridline(xf * 0.5 - yf * 0.8660254, freq, width, phase * 1.31),
        0,
        1,
    ).astype(np.float32)


def _spb_edge_energy(arr):
    return np.clip(
        np.abs(arr - np.roll(arr, 1, axis=0)) + np.abs(arr - np.roll(arr, 1, axis=1)),
        0,
        1,
    ).astype(np.float32)


def _spb_pattern_xy(shape):
    h, w = shape
    yy, xx = get_mgrid((h, w))
    xf = xx.astype(np.float32) / max(w - 1, 1)
    yf = yy.astype(np.float32) / max(h - 1, 1)
    cx = xf - 0.5
    cy = yf - 0.5
    r = np.sqrt(cx * cx + cy * cy)
    a = np.arctan2(cy, cx)
    return xf, yf, cx, cy, r, a


def _spb_fast_line_px(coord, period, width=1.5, phase=0.0):
    pos = np.mod(coord + float(phase), float(period))
    dist = np.minimum(pos, float(period) - pos)
    return np.clip(1.0 - dist / max(float(width), 1e-4), 0, 1).astype(np.float32)


def _spb_fast_dots_px(x, y, period_x, period_y, radius, phase_x=0.0, phase_y=0.0):
    px = np.mod(x + float(phase_x), float(period_x)) - float(period_x) * 0.5
    py = np.mod(y + float(phase_y), float(period_y)) - float(period_y) * 0.5
    rr = float(radius) * float(radius)
    return np.clip(1.0 - (px * px + py * py) / max(rr, 1e-4), 0, 1).astype(np.float32)


def _spb_fast_grain_px(x, y, seed):
    # Deterministic integer-ish grain without trig; good enough for tiny 2048 texture breakup.
    return (np.mod(x * 13.0 + y * 17.0 + float(seed % 997), 101.0) / 100.0).astype(np.float32)


def _spb_rebuilt_tech_pattern_value(pattern_id, shape, seed, sm):
    h, w = shape
    x = np.arange(w, dtype=np.float32)[np.newaxis, :]
    y = np.arange(h, dtype=np.float32)[:, np.newaxis]
    family = _spb_hash_seed(pattern_id) ^ (int(seed) * 2654435761)
    phase = float(family % 257)
    grain = _spb_fast_grain_px(x, y, family)
    diag_a = x + y * 0.50
    diag_b = x - y * 0.62

    if pattern_id == "circuit_traces":
        traces = np.maximum(_spb_fast_line_px(x, 64, 2.0, phase), _spb_fast_line_px(y, 48, 1.7, phase * 0.37))
        traces = np.maximum(traces, _spb_fast_line_px(diag_a, 96, 1.25, phase * 0.19))
        pads = _spb_fast_dots_px(x, y, 96, 80, 7.0, phase, phase * 0.41)
        micro = np.maximum(_spb_fast_line_px(x, 16, 0.55, phase), _spb_fast_line_px(y, 18, 0.55, phase * 0.73)) * 0.28
        field = traces * 0.72 + pads * 0.58 + micro + (grain > 0.97).astype(np.float32) * 0.22

    elif pattern_id == "hex_circuit":
        lattice = np.maximum(
            np.maximum(_spb_fast_line_px(x, 34, 1.15, phase), _spb_fast_line_px(diag_a, 34, 1.15, phase * 0.31)),
            _spb_fast_line_px(diag_b, 34, 1.15, phase * 0.67),
        )
        nodes = _spb_fast_dots_px(x + y * 0.25, y, 68, 58, 4.8, phase, phase * 0.23)
        jumpers = np.maximum(_spb_fast_line_px(y, 116, 1.4, phase), _spb_fast_line_px(x + y * 0.08, 142, 1.1, phase))
        field = lattice * 0.70 + nodes * 0.55 + jumpers * 0.28 + (grain > 0.985).astype(np.float32) * 0.18

    elif pattern_id == "biomech_cables":
        cable1 = _spb_fast_line_px(y + np.sin(x * 0.021 + phase * 0.013) * 18.0, 58, 3.8, phase)
        cable2 = _spb_fast_line_px(y + np.sin(x * 0.014 - phase * 0.017) * 27.0, 91, 2.4, phase * 0.4)
        ribs = _spb_fast_line_px(x + np.sin(y * 0.026) * 7.0, 44, 1.0, phase)
        pores = _spb_fast_dots_px(x, y, 42, 36, 2.6, phase, phase * 0.9)
        field = cable1 * 0.62 + cable2 * 0.48 + ribs * 0.30 + pores * 0.22 + grain * 0.08

    elif pattern_id == "dendrite_web":
        web = np.maximum(
            np.maximum(_spb_fast_line_px(x + y * 0.18, 76, 1.2, phase), _spb_fast_line_px(x - y * 0.72, 112, 1.1, phase * 0.7)),
            _spb_fast_line_px(y + np.mod(x, 96) * 0.42, 88, 1.0, phase * 0.3),
        )
        branch = _spb_fast_line_px(y + np.sin(x * 0.035 + phase) * 10.0, 42, 0.8, phase)
        tips = (_spb_fast_dots_px(x, y, 74, 61, 3.2, phase, phase * 0.51) * (grain > 0.58)).astype(np.float32)
        field = web * 0.58 + branch * 0.42 + tips * 0.42 + grain * 0.09

    elif pattern_id == "crystal_lattice":
        facets = np.maximum(
            np.maximum(_spb_fast_line_px(diag_a, 72, 1.3, phase), _spb_fast_line_px(diag_b, 68, 1.3, phase * 0.41)),
            _spb_fast_line_px(y, 96, 1.0, phase * 0.19),
        )
        facets = np.maximum(facets, (_spb_fast_grain_px(np.floor(x / 44), np.floor(y / 44), family) > 0.63).astype(np.float32) * 0.18)
        glints = _spb_fast_dots_px(x, y, 118, 86, 3.4, phase, phase * 0.27)
        field = facets * 0.74 + glints * 0.38 + grain * 0.07

    elif pattern_id == "chainmail_hex":
        cell = 30.0
        row_offset = np.mod(np.floor(y / cell), 2.0) * cell * 0.5
        dx = np.mod(x + row_offset + phase, cell) - cell * 0.5
        dy = np.mod(y + phase * 0.21, cell * 0.82) - cell * 0.41
        dist2 = dx * dx + dy * dy
        rings = np.clip(1.0 - np.abs(dist2 - 82.0) / 48.0, 0, 1)
        links = np.maximum(_spb_fast_line_px(diag_a, 42, 0.8, phase), _spb_fast_line_px(diag_b, 42, 0.8, phase * 0.3))
        field = rings * 0.78 + links * 0.28 + grain * 0.06

    elif pattern_id == "graphene_hex":
        lattice = np.maximum(
            np.maximum(_spb_fast_line_px(x, 24, 0.85, phase), _spb_fast_line_px(diag_a, 24, 0.85, phase * 0.5)),
            _spb_fast_line_px(diag_b, 24, 0.85, phase * 0.75),
        )
        atoms = _spb_fast_dots_px(x + y * 0.18, y, 48, 42, 2.4, phase, phase * 0.2)
        defects = (grain > 0.992).astype(np.float32)
        field = lattice * 0.78 + atoms * 0.34 + defects * 0.20

    elif pattern_id == "gear_mesh":
        cell = 96.0
        dx = np.mod(x + phase, cell) - cell * 0.5
        dy = np.mod(y + phase * 0.39, cell) - cell * 0.5
        r2 = dx * dx + dy * dy
        angle = np.arctan2(dy, dx)
        teeth = 1.0 + 0.16 * np.sin(angle * 16.0)
        ring = np.clip(1.0 - np.abs(np.sqrt(r2) - 23.0 * teeth) / 2.8, 0, 1)
        hubs = np.clip(1.0 - r2 / (7.5 * 7.5), 0, 1)
        mesh = np.maximum(_spb_fast_line_px(x, 24, 0.75, phase), _spb_fast_line_px(y, 24, 0.75, phase))
        field = ring * 0.74 + hubs * 0.42 + mesh * 0.22 + grain * 0.05

    elif pattern_id == "vinyl_record":
        cx = x - w * (0.52 + ((family % 7) - 3) * 0.012)
        cy = y - h * (0.50 + ((family % 5) - 2) * 0.014)
        radius = np.sqrt(cx * cx + cy * cy)
        grooves = _spb_fast_line_px(radius, 8.0, 0.95, phase)
        sweep = _spb_fast_line_px((np.arctan2(cy, cx) + np.pi) * 70.0 + radius * 0.08, 46, 0.65, phase)
        dust = (grain > 0.985).astype(np.float32)
        field = grooves * 0.72 + sweep * 0.28 + dust * 0.22

    elif pattern_id == "fiber_optic":
        fibers = np.maximum(_spb_fast_line_px(x + np.sin(y * 0.030) * 3.5, 10, 0.55, phase),
                            _spb_fast_line_px(x + y * 0.07, 17, 0.45, phase * 0.47))
        pulses = _spb_fast_dots_px(x + np.sin(y * 0.011) * 11.0, y, 54, 42, 2.6, phase, phase * 0.29)
        glints = (grain > 0.982).astype(np.float32)
        field = fibers * 0.62 + pulses * 0.48 + glints * 0.28

    elif pattern_id == "sonar_ping":
        centers = ((0.31, 0.36), (0.68, 0.42), (0.50, 0.70))
        field = np.zeros((h, w), dtype=np.float32)
        for idx, (cxn, cyn) in enumerate(centers):
            rr = np.sqrt((x - w * cxn) ** 2 + (y - h * cyn) ** 2)
            field = np.maximum(field, _spb_fast_line_px(rr, 34 + idx * 9, 1.5, phase + idx * 13))
        sweeps = _spb_fast_line_px(x * 0.42 + y, 118, 1.0, phase)
        blips = _spb_fast_dots_px(x, y, 102, 89, 3.8, phase, phase * 0.33)
        field = field * 0.68 + sweeps * 0.20 + blips * 0.42 + (grain > 0.992).astype(np.float32) * 0.18

    elif pattern_id == "waveform_stack":
        field = np.zeros((h, w), dtype=np.float32)
        for idx in range(9):
            base = (idx + 1) * h / 10.0
            wave = base + np.sin(x * (0.020 + idx * 0.002) + phase * 0.02 + idx) * (8.0 + idx * 1.8)
            field = np.maximum(field, np.clip(1.0 - np.abs(y - wave) / 2.0, 0, 1))
        ticks = np.maximum(_spb_fast_line_px(x, 64, 0.65, phase), _spb_fast_line_px(y, h / 10.0, 0.55, phase))
        field = field * 0.74 + ticks * 0.20 + (grain > 0.988).astype(np.float32) * 0.20

    else:
        field = np.maximum(_spb_fast_line_px(x, 32, 1.0, phase), _spb_fast_line_px(y, 32, 1.0, phase))
        field = field + grain * 0.12

    field = np.clip(field + grain * 0.035, 0, 1)
    return field.astype(np.float32, copy=False)


def _spb_rebuilt_specific_pattern_value(pattern_id, shape, seed, sm):
    h, w = shape
    x = np.arange(w, dtype=np.float32)[np.newaxis, :]
    y = np.arange(h, dtype=np.float32)[:, np.newaxis]
    family = _spb_hash_seed(pattern_id) ^ (int(seed) * 1103515245)
    phase = float(family % 997)
    grain = _spb_fast_grain_px(x, y, family)
    field = np.zeros((h, w), dtype=np.float32)

    if pattern_id == "reaction_diffusion":
        a = np.sin(x * 0.052 + np.sin(y * 0.019 + phase) * 2.1)
        b = np.sin(y * 0.061 + np.cos(x * 0.017 - phase) * 2.4)
        c = np.sin((x - y) * 0.043 + (a + b) * 1.3)
        field = np.clip((a * b + c) * 0.30 + 0.50, 0, 1)
        field = np.maximum(field, _spb_fast_line_px(field * 255.0, 31.0, 2.0, phase) * 0.85)

    elif pattern_id == "phyllotaxis":
        if cv2 is not None:
            rng = np.random.default_rng(family & 0xFFFFFFFF)
            cx, cy = w * 0.5, h * 0.5
            golden = np.pi * (3.0 - np.sqrt(5.0))
            n = max(900, int(min(h, w) * 1.25))
            for i in range(n):
                r = np.sqrt(i / n) * min(h, w) * 0.50
                a = i * golden + phase * 0.003
                px = int(np.clip(cx + np.cos(a) * r, 0, w - 1))
                py = int(np.clip(cy + np.sin(a) * r, 0, h - 1))
                cv2.circle(field, (px, py), int(rng.integers(1, 3)), float(0.45 + 0.55 * i / n), -1, lineType=cv2.LINE_AA)
        field += _spb_fast_line_px(np.sqrt((x - w * 0.5) ** 2 + (y - h * 0.5) ** 2), 17.0, 0.8, phase) * 0.20

    elif pattern_id == "lorenz_slice":
        if cv2 is not None:
            px, py, pz = 0.1, 0.0, 0.0
            pts = []
            dt = 0.006
            for _ in range(5200):
                dx = 10.0 * (py - px)
                dy = px * (28.0 - pz) - py
                dz = px * py - 8.0 * pz / 3.0
                px += dx * dt
                py += dy * dt
                pz += dz * dt
                sx = int(np.clip((px + 22.0) / 44.0 * w, 0, w - 1))
                sy = int(np.clip((pz - 2.0) / 52.0 * h, 0, h - 1))
                pts.append([sx, sy])
            cv2.polylines(field, [np.asarray(pts, dtype=np.int32)], False, 1.0, 1, lineType=cv2.LINE_AA)
        field = np.maximum(field, _spb_fast_line_px(x - y * 0.18, 83.0, 0.8, phase) * 0.14)

    elif pattern_id == "julia_boundary":
        zx = (x / max(w - 1, 1) - 0.5) * 2.9
        zy = (y / max(h - 1, 1) - 0.5) * 2.5
        c_re = -0.72 + ((family % 37) - 18) * 0.0017
        c_im = 0.27 + ((family >> 8) % 41 - 20) * 0.0015
        acc = np.zeros((h, w), dtype=np.float32)
        for i in range(7):
            zx, zy = zx * zx - zy * zy + c_re, 2.0 * zx * zy + c_im
            mag = zx * zx + zy * zy
            acc += (mag < 4.0).astype(np.float32) * (1.0 - i * 0.08)
            zx = np.clip(zx, -4.0, 4.0)
            zy = np.clip(zy, -4.0, 4.0)
        field = _spb_fast_line_px(acc, 1.0, 0.12, phase)

    elif pattern_id == "holographic":
        grating = _spb_fast_line_px(x + np.sin(y * 0.018 + phase) * 18.0, 19.0, 1.0, phase)
        prism = np.sin((x * 0.027 + y * 0.011) + np.sin((x - y) * 0.009) * 3.0 + phase) * 0.5 + 0.5
        field = np.clip(grating * 0.54 + prism * 0.34 + (grain > 0.982).astype(np.float32) * 0.20, 0, 1)

    elif pattern_id == "nature_water_ripple_pat":
        centers = ((0.28, 0.34), (0.70, 0.42), (0.48, 0.76))
        for idx, (cx, cy) in enumerate(centers):
            rr = np.sqrt((x - w * cx) ** 2 + (y - h * cy) ** 2)
            field = np.maximum(field, _spb_fast_line_px(rr, 24.0 + idx * 7.0, 1.2, phase + idx * 19.0))
        field += grain * 0.07

    elif pattern_id == "decade_90s_dot_matrix":
        dots = _spb_fast_dots_px(x, y, 14.0, 14.0, 2.3, phase, phase * 0.37)
        scan = _spb_fast_line_px(y, 7.0, 0.55, phase)
        dropout = (grain > 0.88).astype(np.float32)
        field = np.clip(dots * (0.45 + dropout * 0.48) + scan * 0.24, 0, 1)

    elif pattern_id == "giraffe":
        cell = 74.0
        qx = np.floor((x + y * 0.22) / cell)
        qy = np.floor((y - x * 0.12) / (cell * 0.78))
        cell_hash = np.mod(qx * 17.0 + qy * 29.0 + phase, 23.0) / 22.0
        seams = np.maximum(_spb_fast_line_px(x + y * 0.22, cell, 3.0, phase), _spb_fast_line_px(y - x * 0.12, cell * 0.78, 3.0, phase * 0.27))
        spots = (cell_hash > 0.38).astype(np.float32) * (1.0 - seams)
        field = np.clip(spots * 0.68 + seams * 0.40 + grain * 0.08, 0, 1)

    elif pattern_id in {"hilbert_curve", "geo_hilbert_curve"}:
        block = 32.0 if pattern_id == "hilbert_curve" else 24.0
        maze = np.maximum(_spb_fast_line_px(x, block, 1.15, phase), _spb_fast_line_px(y, block, 1.15, phase * 0.5))
        gates = ((_spb_fast_grain_px(np.floor(x / block), np.floor(y / block), family) > 0.44).astype(np.float32))
        turns = np.maximum(_spb_fast_line_px(x + y, block * 2.0, 1.0, phase), _spb_fast_line_px(x - y, block * 2.0, 1.0, phase * 0.77))
        field = np.clip(maze * gates * 0.72 + turns * 0.36 + grain * 0.05, 0, 1)

    elif pattern_id == "soundwave":
        for idx in range(11):
            base_y = (idx + 1) * h / 12.0
            wave = base_y + np.sin(x * (0.018 + idx * 0.0018) + phase * 0.01 + idx) * (7.0 + idx)
            field = np.maximum(field, np.clip(1.0 - np.abs(y - wave) / 1.8, 0, 1))
        field += _spb_fast_line_px(x, 52.0, 0.65, phase) * 0.12

    elif pattern_id == "pinwheel_tiling":
        cx = x - w * 0.5
        cy = y - h * 0.5
        theta = np.arctan2(cy, cx)
        rr = np.sqrt(cx * cx + cy * cy)
        blades = np.sin(theta * 9.0 + rr * 0.025 + phase * 0.02) * 0.5 + 0.5
        seams = _spb_fast_line_px(theta + rr * 0.002, 0.38, 0.018, phase * 0.001)
        field = np.clip(blades * 0.42 + seams * 0.62 + grain * 0.05, 0, 1)

    elif pattern_id == "shokk_signal_noise":
        scan = _spb_fast_line_px(y + np.sin(x * 0.025 + phase) * 5.0, 9.0, 0.85, phase)
        packets = _spb_fast_dots_px(x, y, 37.0, 19.0, 2.1, phase, phase * 0.31)
        dropout = (grain > 0.78).astype(np.float32)
        field = np.clip(scan * 0.48 + packets * 0.42 + dropout * 0.20, 0, 1)

    elif pattern_id == "decade_90s_chrome_bubble":
        if cv2 is not None:
            rng = np.random.default_rng(family & 0xFFFFFFFF)
            for _ in range(80):
                cx = int(rng.integers(0, w))
                cy = int(rng.integers(0, h))
                r = int(rng.integers(max(4, min(h, w) // 90), max(8, min(h, w) // 26)))
                cv2.circle(field, (cx, cy), r, float(rng.uniform(0.45, 1.0)), 1, lineType=cv2.LINE_AA)
                cv2.circle(field, (cx, cy), max(1, r // 3), float(rng.uniform(0.12, 0.34)), -1, lineType=cv2.LINE_AA)
        field += (grain > 0.985).astype(np.float32) * 0.22

    elif pattern_id == "ripple":
        rr = np.sqrt((x - w * 0.46) ** 2 + (y - h * 0.54) ** 2)
        field = _spb_fast_line_px(rr + np.sin(x * 0.014 + phase) * 7.0, 21.0, 1.1, phase)
        field = np.maximum(field, _spb_fast_line_px(y + np.sin(x * 0.028) * 12.0, 43.0, 1.0, phase * 0.4) * 0.42)

    elif pattern_id == "decade_70s_funk_zigzag":
        zig = np.abs(np.mod(x / 34.0 + phase * 0.01, 2.0) - 1.0) * 42.0
        bands = _spb_fast_line_px(y + zig, 72.0, 4.0, phase)
        fine_zig = _spb_fast_line_px(y - zig * 0.55, 28.0, 1.0, phase * 0.33)
        field = np.clip(bands * 0.72 + fine_zig * 0.38 + grain * 0.08, 0, 1)

    elif pattern_id == "skull_wings":
        if cv2 is not None:
            rng = np.random.default_rng(family & 0xFFFFFFFF)
            cx, cy = int(w * 0.50), int(h * 0.50)
            cv2.ellipse(field, (cx, cy), (max(8, w // 18), max(10, h // 13)), 0, 0, 360, 0.92, 2, lineType=cv2.LINE_AA)
            cv2.circle(field, (int(cx - w * 0.020), int(cy - h * 0.018)), max(2, min(h, w) // 90), 0.12, -1, lineType=cv2.LINE_AA)
            cv2.circle(field, (int(cx + w * 0.020), int(cy - h * 0.018)), max(2, min(h, w) // 90), 0.12, -1, lineType=cv2.LINE_AA)
            cv2.line(field, (cx, int(cy + h * 0.010)), (cx, int(cy + h * 0.045)), 0.88, 1, lineType=cv2.LINE_AA)
            for side in (-1, 1):
                root = (int(cx + side * w * 0.045), int(cy + h * 0.006))
                for idx in range(30):
                    spread = idx / 29.0
                    length = w * (0.13 + 0.23 * (1.0 - spread * 0.45))
                    lift = h * (-0.19 + spread * 0.38)
                    x2 = int(np.clip(root[0] + side * length, 0, w - 1))
                    y2 = int(np.clip(root[1] + lift + rng.uniform(-h * 0.010, h * 0.010), 0, h - 1))
                    cv2.line(field, root, (x2, y2), float(0.42 + 0.44 * (1.0 - spread)), 1, lineType=cv2.LINE_AA)
                    barb = int(np.clip(x2 - side * w * 0.030, 0, w - 1))
                    cv2.line(field, (barb, y2), (x2, y2), 0.34, 1, lineType=cv2.LINE_AA)
        field = np.maximum(field, _spb_fast_line_px(x + y * 0.36, 23.0, 0.7, phase) * 0.16)
        field += (grain > 0.988).astype(np.float32) * 0.14

    elif pattern_id == "decade_90s_geo_minimal":
        base_grid = np.maximum(_spb_fast_line_px(x, 86.0, 0.9, phase), _spb_fast_line_px(y, 74.0, 0.9, phase * 0.41)) * 0.18
        if cv2 is not None:
            rng = np.random.default_rng(family & 0xFFFFFFFF)
            field += base_grid
            for _ in range(72):
                px = int(rng.integers(0, w))
                py = int(rng.integers(0, h))
                size = int(rng.integers(max(5, min(h, w) // 80), max(10, min(h, w) // 28)))
                val = float(rng.uniform(0.42, 0.96))
                choice = int(rng.integers(0, 4))
                if choice == 0:
                    cv2.rectangle(field, (px, py), (min(w - 1, px + size), min(h - 1, py + size)), val, 1, lineType=cv2.LINE_AA)
                elif choice == 1:
                    cv2.circle(field, (px, py), size // 2, val, 1, lineType=cv2.LINE_AA)
                elif choice == 2:
                    pts = np.asarray([[px, py], [min(w - 1, px + size), py], [px, min(h - 1, py + size)]], dtype=np.int32)
                    cv2.polylines(field, [pts], True, val, 1, lineType=cv2.LINE_AA)
                else:
                    cv2.line(field, (px, py), (min(w - 1, px + size * 2), min(h - 1, py + size)), val, 1, lineType=cv2.LINE_AA)
        else:
            field = base_grid
        field += _spb_fast_dots_px(x, y, 53.0, 47.0, 1.6, phase, phase * 0.7) * 0.22

    elif pattern_id == "stardust_2":
        stars = (grain > 0.972).astype(np.float32)
        bright = (grain > 0.994).astype(np.float32)
        nebula = np.sin(x * 0.013 + y * 0.017 + np.sin(y * 0.006 + phase) * 2.4) * 0.5 + 0.5
        trails = _spb_fast_line_px(x - y * 0.34, 141.0, 0.75, phase) * (grain > 0.86).astype(np.float32)
        field = np.clip(stars * 0.58 + bright * 0.42 + trails * 0.30 + nebula * 0.13, 0, 1)

    elif pattern_id == "decade_60s_gogo_check":
        warp_x = x + np.sin(y * 0.025 + phase) * 18.0
        warp_y = y + np.sin(x * 0.023 - phase * 0.4) * 18.0
        check = ((np.floor(warp_x / 34.0) + np.floor(warp_y / 34.0)) % 2.0).astype(np.float32)
        seams = np.maximum(_spb_fast_line_px(warp_x, 34.0, 1.4, phase), _spb_fast_line_px(warp_y, 34.0, 1.4, phase * 0.33))
        dots = _spb_fast_dots_px(warp_x, warp_y, 68.0, 68.0, 4.0, phase, phase * 0.51)
        field = np.clip(check * 0.58 + seams * 0.36 + dots * 0.24 + grain * 0.04, 0, 1)

    elif pattern_id == "wave_standing":
        a = np.sin(x * 0.041 + phase * 0.017)
        b = np.sin(y * 0.047 - phase * 0.013)
        c = np.sin((x + y) * 0.028 + np.sin((x - y) * 0.006) * 2.0)
        nodes = np.abs(a + b + c) / 3.0
        field = np.clip(_spb_fast_line_px(nodes * 255.0, 23.0, 2.0, phase) * 0.78 + _spb_fast_line_px(x - y, 97.0, 0.8, phase) * 0.20, 0, 1)

    elif pattern_id == "decade_90s_floppy_disk":
        field += _spb_fast_line_px(x, 128.0, 0.8, phase) * 0.10 + _spb_fast_line_px(y, 128.0, 0.8, phase) * 0.10
        if cv2 is not None:
            cell_w = max(42, w // 8)
            cell_h = max(42, h // 6)
            for yy0 in range(0, h, cell_h):
                for xx0 in range(0, w, cell_w):
                    jitter = int(((xx0 * 17 + yy0 * 29 + family) % 15) - 7)
                    x0, y0 = xx0 + max(2, cell_w // 8), yy0 + max(2, cell_h // 8)
                    x1, y1 = min(w - 1, xx0 + cell_w - max(3, cell_w // 8)), min(h - 1, yy0 + cell_h - max(3, cell_h // 8))
                    cv2.rectangle(field, (x0, y0), (x1, y1), 0.70, 1, lineType=cv2.LINE_AA)
                    cv2.rectangle(field, (x0 + cell_w // 8, y0), (x1 - cell_w // 5, y0 + cell_h // 4), 0.44, 1, lineType=cv2.LINE_AA)
                    cv2.line(field, (x0 + cell_w // 5, y1 - cell_h // 5 + jitter), (x1 - cell_w // 5, y1 - cell_h // 5 + jitter), 0.88, 1, lineType=cv2.LINE_AA)

    elif pattern_id == "crocodile":
        cell = 62.0
        row = np.floor(y / (cell * 0.62))
        offset = np.mod(row, 2.0) * cell * 0.42
        dx = np.mod(x + offset + phase, cell) - cell * 0.5
        dy = np.mod(y + phase * 0.37, cell * 0.62) - cell * 0.31
        scale = 1.0 + (np.mod(row, 5.0) - 2.0) * 0.06
        plate = (dx / (cell * 0.43 * scale)) ** 2 + (dy / (cell * 0.25)) ** 2
        seams = np.clip(np.abs(plate - 1.0) * -3.0 + 1.0, 0, 1)
        pores = _spb_fast_dots_px(x + y * 0.18, y, 24.0, 19.0, 1.4, phase, phase * 0.23)
        field = np.clip(seams * 0.70 + pores * 0.22 + grain * 0.08, 0, 1)

    elif pattern_id == "cloud_scroll":
        flow = y + np.sin(x * 0.019 + phase * 0.021) * 34.0 + np.sin(x * 0.007 - phase * 0.031) * 72.0
        curls = _spb_fast_line_px(flow, 86.0, 3.0, phase)
        inner = _spb_fast_line_px(flow + np.sin(y * 0.018) * 18.0, 29.0, 1.1, phase * 0.3)
        wisps = _spb_fast_line_px(x + y * 0.17 + np.sin(y * 0.011) * 26.0, 113.0, 0.9, phase)
        field = np.clip(curls * 0.62 + inner * 0.30 + wisps * 0.22 + grain * 0.05, 0, 1)

    elif pattern_id == "snake_skin_4":
        cell = 42.0
        diamond = np.abs(np.mod((x + phase) / cell, 1.0) - 0.5) + np.abs(np.mod((y + phase * 0.31) / (cell * 0.72), 1.0) - 0.5)
        seams = np.clip(1.0 - np.abs(diamond - 0.52) / 0.035, 0, 1)
        ridges = _spb_fast_line_px(x + y * 0.24, 21.0, 0.55, phase) * 0.18
        speckles = (grain > 0.965).astype(np.float32) * 0.18
        field = np.clip(seams * 0.76 + ridges + speckles, 0, 1)

    elif pattern_id == "fresnel_ghost":
        cx = x - w * 0.5
        cy = y - h * 0.5
        rr = np.sqrt(cx * cx + cy * cy)
        rings = _spb_fast_line_px(rr + np.sin(np.arctan2(cy, cx) * 5.0 + phase * 0.01) * 9.0, 28.0, 1.25, phase)
        ghost = _spb_fast_line_px(x * 0.72 + y * 0.21, 67.0, 0.9, phase) * 0.34
        caustic = _spb_fast_line_px(rr * 0.62 + x * 0.08, 49.0, 0.8, phase * 0.53)
        field = np.clip(rings * 0.62 + ghost + caustic * 0.24 + (grain > 0.988).astype(np.float32) * 0.16, 0, 1)

    elif pattern_id == "dragon_curve":
        field = np.maximum(_spb_fast_line_px(x + y, 51.0, 1.1, phase), _spb_fast_line_px(x - y, 73.0, 1.0, phase * 0.4)) * 0.25
        if cv2 is not None:
            pts = []
            px, py = int(w * 0.15), int(h * 0.55)
            step = max(5, min(h, w) // 42)
            angle = 0
            turns = "1101100111001001110110001100100"
            for idx in range(min(620, max(96, (h + w) // 5))):
                turn = 1 if turns[idx % len(turns)] == "1" else -1
                angle = (angle + turn) % 4
                px = int(np.clip(px + (1 if angle == 0 else -1 if angle == 2 else 0) * step, 0, w - 1))
                py = int(np.clip(py + (1 if angle == 1 else -1 if angle == 3 else 0) * step, 0, h - 1))
                pts.append([px, py])
            if len(pts) > 1:
                cv2.polylines(field, [np.asarray(pts, dtype=np.int32)], False, 0.95, 1, lineType=cv2.LINE_AA)
        field += (grain > 0.989).astype(np.float32) * 0.16

    elif pattern_id == "hex_mandala":
        cx = x - w * 0.5
        cy = y - h * 0.5
        rr = np.sqrt(cx * cx + cy * cy)
        theta = np.arctan2(cy, cx)
        rings = _spb_fast_line_px(rr, 31.0, 1.15, phase)
        petals = _spb_fast_line_px(theta * 96.0 + np.sin(rr * 0.018 + phase * 0.01) * 8.0, 13.0, 0.85, phase)
        hexes = np.maximum(
            np.maximum(_spb_fast_line_px(x, 38.0, 0.7, phase), _spb_fast_line_px(x * 0.5 + y * 0.866, 38.0, 0.7, phase * 0.29)),
            _spb_fast_line_px(x * 0.5 - y * 0.866, 38.0, 0.7, phase * 0.61),
        )
        rosette = _spb_fast_line_px(rr + np.sin(theta * 12.0) * 12.0, 67.0, 1.4, phase)
        field = np.clip(rings * 0.42 + petals * 0.34 + hexes * 0.26 + rosette * 0.34 + (grain > 0.99).astype(np.float32) * 0.12, 0, 1)

    elif pattern_id == "shokk_fracture":
        shards = np.maximum(
            np.maximum(_spb_fast_line_px(x + y * 0.37, 73.0, 0.95, phase), _spb_fast_line_px(x - y * 0.71, 97.0, 0.9, phase * 0.33)),
            _spb_fast_line_px(x * 0.19 + y, 61.0, 0.75, phase * 0.57),
        )
        splinters = _spb_fast_line_px(x + np.floor(y / 31.0) * 17.0, 43.0, 0.55, phase) * (grain > 0.62).astype(np.float32)
        impact = _spb_fast_dots_px(x, y, 137.0, 111.0, 3.8, phase, phase * 0.19)
        field = np.clip(shards * 0.66 + splinters * 0.32 + impact * 0.22 + (grain > 0.991).astype(np.float32) * 0.15, 0, 1)

    elif pattern_id == "shokk_waveform":
        field = np.zeros((h, w), dtype=np.float32)
        for idx in range(10):
            base_y = (idx + 0.75) * h / 11.0
            wave = base_y + np.sin(x * (0.019 + idx * 0.0025) + phase * 0.018 + idx * 0.7) * (8.0 + idx * 1.4)
            wave += np.sin(x * 0.006 - phase * 0.011) * (16.0 - idx * 0.6)
            field = np.maximum(field, np.clip(1.0 - np.abs(y - wave) / 1.6, 0, 1))
        carrier = np.maximum(_spb_fast_line_px(x, 48.0, 0.55, phase), _spb_fast_line_px(y, 96.0, 0.55, phase * 0.4))
        pulses = _spb_fast_dots_px(x, y, 83.0, 47.0, 2.4, phase, phase * 0.31)
        field = np.clip(field * 0.70 + carrier * 0.18 + pulses * 0.26, 0, 1)

    elif pattern_id == "shokk_plasma_storm":
        ion = np.sin(x * 0.034 + np.sin(y * 0.017 + phase) * 2.8)
        shear = np.sin((x - y * 0.52) * 0.046 + phase * 0.02)
        charge = _spb_fast_line_px((ion + shear) * 128.0, 37.0, 2.2, phase)
        bolts = np.maximum(
            _spb_fast_line_px(x + np.sin(y * 0.025 + phase * 0.01) * 26.0, 83.0, 0.85, phase),
            _spb_fast_line_px(y + np.sin(x * 0.031 - phase * 0.01) * 20.0, 71.0, 0.75, phase * 0.37),
        )
        sparks = (grain > 0.982).astype(np.float32)
        field = np.clip(charge * 0.52 + bolts * 0.42 + sparks * 0.22, 0, 1)

    elif pattern_id == "shokk_tesseract":
        cube_a = np.maximum(_spb_fast_line_px(x, 92.0, 1.1, phase), _spb_fast_line_px(y, 92.0, 1.1, phase * 0.33))
        cube_b = np.maximum(_spb_fast_line_px(x + y * 0.42, 92.0, 0.9, phase * 0.61), _spb_fast_line_px(x - y * 0.42, 92.0, 0.9, phase * 0.21))
        inner = np.maximum(_spb_fast_line_px(x + 24.0, 46.0, 0.65, phase), _spb_fast_line_px(y + 24.0, 46.0, 0.65, phase * 0.5))
        nodes = _spb_fast_dots_px(x + y * 0.19, y, 92.0, 92.0, 4.2, phase, phase * 0.19)
        phase_gates = (_spb_fast_grain_px(np.floor(x / 92.0), np.floor(y / 92.0), family) > 0.38).astype(np.float32)
        field = np.clip((cube_a * 0.46 + cube_b * 0.42 + inner * 0.20) * phase_gates + nodes * 0.36 + (grain > 0.99).astype(np.float32) * 0.14, 0, 1)

    elif pattern_id == "shokk_scream":
        throat = np.abs(y - h * 0.52) / max(h, 1)
        carrier = _spb_fast_line_px(y + np.sin(x * 0.032 + phase * 0.01) * 24.0, 34.0, 1.1, phase)
        harmonics = _spb_fast_line_px(y - np.sin(x * 0.071 - phase * 0.02) * 9.0, 13.0, 0.55, phase * 0.43)
        shock = _spb_fast_line_px(x - y * 0.22, 77.0, 0.75, phase)
        field = np.clip((carrier * 0.54 + harmonics * 0.36 + shock * 0.18) * np.clip(1.25 - throat * 2.2, 0.2, 1.0) + (grain > 0.989).astype(np.float32) * 0.14, 0, 1)

    elif pattern_id == "flame_inferno_wall":
        height = 1.0 - y / max(h - 1, 1)
        tongues = np.sin(x * 0.027 + np.sin(y * 0.012 + phase) * 3.4) * 0.5 + 0.5
        lick = _spb_fast_line_px(x + np.sin(y * 0.026 + phase * 0.01) * 31.0, 61.0, 2.3, phase)
        sparks = (grain > (0.965 - height * 0.035)).astype(np.float32)
        ribs = _spb_fast_line_px(y + tongues * 44.0, 43.0, 1.1, phase * 0.27)
        field = np.clip(tongues * height * 0.38 + lick * 0.44 + ribs * 0.26 + sparks * 0.20, 0, 1)

    elif pattern_id == "flame_blue_propane":
        height = 1.0 - y / max(h - 1, 1)
        jets = _spb_fast_line_px(x + np.sin(y * 0.018 + phase * 0.01) * 12.0, 42.0, 1.35, phase)
        inner = _spb_fast_line_px(x + np.sin(y * 0.041 - phase * 0.01) * 5.0, 21.0, 0.55, phase * 0.3)
        heat = _spb_fast_line_px(y + np.sin(x * 0.022) * 18.0, 57.0, 0.9, phase)
        field = np.clip((jets * 0.58 + inner * 0.36 + heat * 0.18) * (0.42 + height * 0.72) + (grain > 0.991).astype(np.float32) * 0.12, 0, 1)

    elif pattern_id == "flame_ember_field":
        drift = _spb_fast_line_px(y - x * 0.10 + np.sin(x * 0.011 + phase) * 24.0, 83.0, 1.0, phase)
        embers = (grain > 0.956).astype(np.float32)
        hot = (grain > 0.990).astype(np.float32)
        shimmer = np.sin(x * 0.019 + y * 0.031 + phase * 0.01) * 0.5 + 0.5
        field = np.clip(drift * 0.28 + embers * 0.48 + hot * 0.32 + shimmer * 0.10, 0, 1)

    else:
        field = grain

    field = np.clip(field, 0, 1)
    return field.astype(np.float32, copy=False)


_SPB_PATTERN_REBUILD_MODES = {}


def _spb_register_pattern_rebuild(mode, ids):
    for _pid in ids:
        _SPB_PATTERN_REBUILD_MODES[_pid] = mode


_spb_register_pattern_rebuild("tech", (
    "circuit_traces", "hex_circuit", "biomech_cables", "dendrite_web",
    "crystal_lattice", "chainmail_hex", "graphene_hex", "gear_mesh",
    "vinyl_record", "fiber_optic", "sonar_ping", "waveform_stack",
))
_spb_register_pattern_rebuild("world", (
    "spiral_fern", "zigzag_bands", "radial_calendar", "triple_knot",
    "diagonal_interlace", "diamond_blanket", "step_fret",
    "concentric_dot_rings", "medallion_lattice", "eight_point_star",
    "petal_frieze", "cloud_scroll", "tribal_celtic_spiral",
))
_spb_register_pattern_rebuild("natural", (
    "marble_veining", "wood_burl", "seigaiha_scales", "ammonite_chambers",
    "peacock_eye", "dragonfly_wing_pattern", "insect_compound",
    "diatom_radial", "coral_polyp", "birch_bark", "pine_cone_scale",
    "geode_crystal", "nature_bark_rough", "nature_water_ripple_pat",
))
_spb_register_pattern_rebuild("surface", (
    "iridescent_fog", "chrome_delete_edge", "carbon_clearcoat_lock",
    "racing_scratch", "pearlescent_flip", "frost_crystal", "satin_wax",
    "uv_night_accent",
))
_spb_register_pattern_rebuild("surface", (
    "shimmer_quantum_shard", "shimmer_prism_frost", "shimmer_velvet_static",
    "shimmer_chrome_flux", "shimmer_matte_halo", "shimmer_oil_tension",
    "shimmer_neon_weft", "shimmer_void_dust", "shimmer_turbine_sheen",
    "shimmer_spectral_mesh",
))
_spb_register_pattern_rebuild("deco", (
    "art_deco_fan", "chevron_stack", "quatrefoil", "herringbone",
    "basket_weave", "houndstooth", "argyle", "tartan", "op_art_rings",
    "moire_grid", "lozenge_tile", "ogee_lattice", "art_deco_sunburst",
    "art_deco_chevron", "greek_meander", "star_tile_mosaic",
    "escher_reptile", "constructivist", "bauhaus_system", "celtic_plait",
    "cane_weave", "cable_knit", "damask_brocade", "tatami_grid",
    "celtic_knot",
))
_spb_register_pattern_rebuild("op", (
    "concentric_op", "checker_warp", "barrel_distort", "moire_interference",
    "twisted_rings", "spiral_hypnotic", "necker_grid", "radial_pulse",
    "hex_op", "pinwheel_tiling", "impossible_grid", "rose_curve",
))
_spb_register_pattern_rebuild("math", (
    "reaction_diffusion", "fractal_fern", "hilbert_curve", "lorenz_slice",
    "julia_boundary", "wave_standing", "lissajous_web", "dragon_curve",
    "diffraction_grating", "perlin_terrain", "phyllotaxis", "truchet_flow",
    "hypocycloid", "voronoi_relaxed", "wave_ripple_2d", "sierpinski_tri",
    "geo_fractal_triangle", "geo_hilbert_curve",
))
_spb_register_pattern_rebuild("weather", (
    "aurora_bands", "hailstorm", "lightning", "plasma", "ripple",
    "sandstorm", "solar_flare", "tornado", "wave",
))
_spb_register_pattern_rebuild("abstract", (
    "biomechanical_2", "fractal", "fractal_2", "fractal_3", "interference",
    "optical_illusion", "optical_illusion_2", "sound_wave", "stardust",
    "stardust_2", "voronoi_shatter",
))
_spb_register_pattern_rebuild("paradigm", (
    "circuitboard", "holographic", "p_tessellation", "p_topographic",
    "soundwave", "caustic", "dimensional", "fresnel_ghost", "neural",
    "p_plasma",
))
_spb_register_pattern_rebuild("animal", ("camo", "multicam"))
_spb_register_pattern_rebuild("gothic", ("thorn_vine", "skull", "skull_wings"))
_spb_register_pattern_rebuild("metal", ("metal_flake", "carbon_fiber", "kevlar_weave", "nanoweave"))
_spb_register_pattern_rebuild("shokk", ("pixel_grid",))
_spb_register_pattern_rebuild("decade", (
    "decade_50s_diner_checkerboard", "decade_50s_jukebox_arc",
    "decade_50s_sputnik_orbit", "decade_50s_drivein_marquee",
    "decade_50s_fallout_shelter", "decade_50s_boomerang_formica",
    "decade_50s_atomic_reactor", "decade_50s_diner_chrome",
    "decade_50s_crt_phosphor", "decade_50s_casino_felt",
    "decade_60s_peace_sign", "decade_60s_tie_dye_spiral",
    "decade_60s_lava_lamp_blob", "decade_60s_opart_illusion",
    "decade_60s_pop_art_halftone", "decade_60s_gogo_check",
    "decade_60s_caged_square", "decade_60s_peter_max_gradient",
    "decade_60s_peter_max_alt", "decade_70s_earth_tone_geo",
    "decade_70s_funk_zigzag", "decade_70s_studio54_glitter",
    "decade_70s_pong_pixel", "decade_80s_pacman_maze",
    "decade_80s_neon_grid", "decade_80s_rubiks_cube",
    "decade_80s_rubiks_cube_2", "decade_80s_rubiks_cube_3",
    "decade_80s_boombox_speaker", "decade_80s_nintendo_dpad",
    "decade_80s_breakdance_spin", "decade_80s_laser_tag",
    "decade_80s_leg_warmer", "decade_90s_grunge_splatter",
    "decade_90s_nirvana_smiley", "decade_90s_cross_colors",
    "decade_90s_tamagotchi_egg", "decade_90s_sega_blast",
    "decade_90s_fresh_prince", "decade_90s_floppy_disk",
    "decade_90s_rave_zigzag", "decade_90s_y2k_bug",
    "decade_90s_tribal_tattoo", "decade_90s_dialup_static",
    "decade_90s_slap_bracelet", "decade_90s_windows95",
    "decade_90s_chrome_bubble", "decade_90s_rugrats_squiggle",
    "decade_90s_rollerblade_streak", "decade_90s_beanie_tag",
    "decade_90s_dot_matrix", "decade_90s_geo_minimal",
    "decade_90s_sbtb_wall",
))


# Damage-control rule: the audit-generated family rebuild map above is kept
# only as historical candidate data. Shipping pattern rewrites must be
# deliberate per-ID implementations, not generic family cousins.
_SPB_BESPOKE_PATTERN_REBUILD_IDS = {
    "circuit_traces", "hex_circuit", "biomech_cables", "dendrite_web",
    "crystal_lattice", "chainmail_hex", "graphene_hex", "gear_mesh",
    "vinyl_record", "fiber_optic", "sonar_ping", "waveform_stack",
    "reaction_diffusion", "phyllotaxis", "lorenz_slice", "julia_boundary",
    "holographic", "nature_water_ripple_pat", "decade_90s_dot_matrix",
    "giraffe", "hilbert_curve", "geo_hilbert_curve", "soundwave",
    "pinwheel_tiling",
    "shokk_signal_noise", "decade_90s_chrome_bubble", "ripple",
    "decade_70s_funk_zigzag", "skull_wings", "decade_90s_geo_minimal",
    "stardust_2", "decade_60s_gogo_check", "wave_standing",
    "decade_90s_floppy_disk", "crocodile", "cloud_scroll",
    "snake_skin_4", "fresnel_ghost", "dragon_curve",
    "hex_mandala", "shokk_fracture", "shokk_waveform",
    "shokk_plasma_storm", "shokk_tesseract",
    "shokk_scream", "flame_inferno_wall", "flame_blue_propane",
    "flame_ember_field",
}

_SPB_SPECIFIC_PATTERN_REBUILD_IDS = _SPB_BESPOKE_PATTERN_REBUILD_IDS - {
    "circuit_traces", "hex_circuit", "biomech_cables", "dendrite_web",
    "crystal_lattice", "chainmail_hex", "graphene_hex", "gear_mesh",
    "vinyl_record", "fiber_optic", "sonar_ping", "waveform_stack",
}

_SPB_PATTERN_REBUILD_MODES.update({
    "giraffe": "animal",
    "crocodile": "animal",
    "snake_skin_4": "animal",
    "nature_water_ripple_pat": "natural",
    "shokk_signal_noise": "shokk",
    "hex_mandala": "deco",
    "shokk_fracture": "shokk",
    "shokk_waveform": "shokk",
    "shokk_plasma_storm": "shokk",
    "shokk_tesseract": "shokk",
    "shokk_scream": "shokk",
    "flame_inferno_wall": "weather",
    "flame_blue_propane": "weather",
    "flame_ember_field": "weather",
})


_SPB_PATTERN_AUDIT_BOOST_IDS = {
    "perlin_terrain", "tornado", "lightning", "phyllotaxis", "skull_wings",
    "lorenz_slice", "sandstorm", "caustic", "shimmer_spectral_mesh",
    "wave_standing", "solar_flare", "truchet_flow", "julia_boundary",
    "reaction_diffusion", "fractal_fern", "shimmer_void_dust",
    "decade_80s_breakdance_spin", "decade_80s_rubiks_cube_2",
    "geo_fractal_triangle", "geo_hilbert_curve", "voronoi_relaxed", "hypocycloid",
}


_SPB_PATTERN_PALETTES = {
    "tech": ((0.02, 0.09, 0.12), (0.00, 0.92, 1.00), (0.95, 1.00, 0.58)),
    "world": ((0.10, 0.05, 0.02), (0.95, 0.68, 0.22), (0.28, 0.78, 0.88)),
    "natural": ((0.05, 0.10, 0.06), (0.48, 0.82, 0.40), (0.92, 0.70, 0.40)),
    "surface": ((0.08, 0.08, 0.09), (0.86, 0.92, 0.98), (0.34, 0.80, 1.00)),
    "deco": ((0.08, 0.05, 0.08), (0.96, 0.76, 0.24), (0.18, 0.80, 0.92)),
    "op": ((0.02, 0.02, 0.04), (0.95, 0.95, 0.95), (0.15, 0.55, 1.00)),
    "math": ((0.03, 0.04, 0.12), (0.45, 0.95, 1.00), (1.00, 0.32, 0.72)),
    "weather": ((0.04, 0.05, 0.08), (0.25, 0.70, 1.00), (1.00, 0.48, 0.18)),
    "abstract": ((0.05, 0.02, 0.09), (0.92, 0.20, 1.00), (0.10, 0.92, 0.82)),
    "paradigm": ((0.02, 0.02, 0.08), (0.20, 1.00, 0.78), (1.00, 0.24, 0.68)),
    "animal": ((0.10, 0.08, 0.04), (0.70, 0.58, 0.34), (0.16, 0.13, 0.08)),
    "gothic": ((0.03, 0.02, 0.025), (0.48, 0.06, 0.08), (0.82, 0.74, 0.62)),
    "metal": ((0.08, 0.08, 0.08), (0.72, 0.76, 0.78), (0.98, 0.82, 0.44)),
    "shokk": ((0.02, 0.02, 0.03), (0.00, 0.92, 1.00), (1.00, 0.34, 0.06)),
    "decade": ((0.10, 0.04, 0.06), (1.00, 0.58, 0.14), (0.12, 0.90, 1.00)),
}


def _spb_rebuilt_pattern_value(pattern_id, mode, shape, seed, sm):
    if pattern_id in _SPB_SPECIFIC_PATTERN_REBUILD_IDS:
        return _spb_rebuilt_specific_pattern_value(pattern_id, shape, seed, sm)
    if mode == "tech":
        return _spb_rebuilt_tech_pattern_value(pattern_id, shape, seed, sm)
    h, w = shape
    xf, yf, cx, cy, r, a = _spb_pattern_xy((h, w))
    family = _spb_hash_seed(pattern_id) ^ (int(seed) * 1103515245)
    phase = ((family & 1023) / 1023.0)
    variant = family % 17
    fine, sparkle = _spb_micro_detail((h, w), seed + 7607, family)
    noise = _spb_hash_field((h, w), seed + family)
    field = np.zeros((h, w), dtype=np.float32)

    if mode == "tech":
        field = np.clip(
            _spb_gridline(xf, 18 + variant, 0.018, phase)
            + _spb_gridline(yf, 15 + (variant % 8), 0.016, phase * 0.61)
            + _spb_gridline(xf + yf * 0.42, 10 + (variant % 6), 0.010, phase * 1.7)
            + _spb_gridline(xf - yf * 0.73, 12 + (variant % 5), 0.009, phase * 2.1),
            0,
            1,
        )
        if "hex" in pattern_id or "graphene" in pattern_id or "chainmail" in pattern_id:
            field = np.maximum(field, _spb_hex_lines(xf, yf, 22 + variant, 0.020, phase))
        if "vinyl" in pattern_id or "sonar" in pattern_id:
            field = np.maximum(field, _spb_gridline(r + np.sin(a * 5.0) * 0.018, 28 + variant, 0.018, phase))
        if "waveform" in pattern_id:
            wave = np.abs(yf - (0.14 + 0.72 * _spb_frac(xf * 7.0 + np.sin(xf * 38.0 + phase * 6.28) * 0.07)))
            field = np.maximum(field, np.exp(-((wave / 0.015) ** 2)))
        if "cables" in pattern_id or "dendrite" in pattern_id:
            cables = _spb_gridline(yf + np.sin(xf * (18 + variant) + phase * 6.28) * 0.050, 9 + variant % 5, 0.018, phase)
            field = np.maximum(field, cables)
        pads = ((_spb_gridline(xf, 9 + variant, 0.020, phase) > 0.70) & (_spb_gridline(yf, 7 + variant % 6, 0.020, phase) > 0.70)).astype(np.float32)
        field = np.clip(field * 0.82 + pads * 0.55 + fine * 0.18 + sparkle * 0.30, 0, 1)

    elif mode == "world":
        radial = _spb_gridline(r + np.sin(a * (3 + variant % 7)) * 0.018, 12 + variant, 0.018, phase)
        spokes = _spb_gridline((a / (2 * np.pi)) + 0.5, 10 + variant, 0.025, phase)
        tile = np.maximum(_spb_hex_lines(xf, yf, 10 + variant % 7, 0.025, phase), _spb_gridline(xf + yf, 9 + variant, 0.018, phase))
        if "cloud" in pattern_id or "fern" in pattern_id:
            tile = np.maximum(tile, _spb_gridline(yf + np.sin(xf * 18.0) * 0.050, 11 + variant, 0.020, phase))
        if "dot" in pattern_id:
            tile = np.maximum(tile, (((np.sin(xf * 80.0) * np.sin(yf * 80.0)) > 0.78).astype(np.float32)))
        field = np.clip(radial * 0.42 + spokes * 0.32 + tile * 0.48 + fine * 0.14 + sparkle * 0.18, 0, 1)

    elif mode == "natural":
        ridge = np.sin((xf * (12 + variant) + np.sin(yf * 18.0 + phase * 6.28) * 0.20) * np.pi * 2)
        vein = _spb_gridline(r + np.sin(a * (5 + variant % 6)) * 0.030, 18 + variant, 0.017, phase)
        cellular = _spb_hex_lines(xf + np.sin(yf * 12.0) * 0.025, yf + np.sin(xf * 9.0) * 0.025, 14 + variant, 0.022, phase)
        if "water" in pattern_id or "seigaiha" in pattern_id or "ammonite" in pattern_id:
            cellular = np.maximum(cellular, _spb_gridline(r + np.sin(a * 6.0) * 0.025, 24 + variant, 0.015, phase))
        if "bark" in pattern_id or "wood" in pattern_id or "marble" in pattern_id:
            vein = np.maximum(vein, _spb_gridline(xf + np.sin(yf * 25.0 + phase) * 0.080 + fine * 0.040, 16 + variant, 0.014, phase))
        if "coral" in pattern_id or "diatom" in pattern_id:
            cellular = np.maximum(cellular, _spb_gridline(a / (2 * np.pi) + r * 0.45, 18 + variant, 0.016, phase))
        field = np.clip(_spb_normalize01(ridge) * 0.18 + vein * 0.36 + cellular * 0.42 + fine * 0.18 + sparkle * 0.16, 0, 1)

    elif mode == "surface":
        scratch = _spb_gridline(yf + np.sin(xf * 31.0 + phase * 9.0) * 0.025, 30 + variant, 0.010, phase)
        mist = _spb_normalize01(np.sin(xf * 23.0 + phase) + np.sin(yf * 29.0 - phase * 2.0) + np.sin((xf + yf) * 41.0))
        frost = _spb_hex_lines(xf + fine * 0.035, yf - fine * 0.035, 24 + variant, 0.014, phase)
        if "scratch" in pattern_id:
            field = np.clip(scratch * 0.72 + fine * 0.34 + sparkle * 0.30, 0, 1)
        elif "frost" in pattern_id:
            field = frost
        else:
            field = np.clip(mist * 0.34 + scratch * 0.28 + frost * 0.24 + fine * 0.14 + sparkle * 0.26, 0, 1)

    elif mode == "deco":
        chevron = _spb_gridline(np.abs(_spb_frac(xf * (6 + variant % 5)) - 0.5) + yf * 0.42, 10 + variant, 0.018, phase)
        weave = np.maximum(_spb_gridline(xf, 18 + variant, 0.020, phase), _spb_gridline(yf, 16 + variant % 7, 0.020, phase * 1.2))
        sun = np.maximum(_spb_gridline(r, 18 + variant, 0.014, phase), _spb_gridline(a / (2 * np.pi), 14 + variant, 0.021, phase))
        if "weave" in pattern_id or "tartan" in pattern_id or "knit" in pattern_id or "tatami" in pattern_id:
            field = weave
        elif "sun" in pattern_id or "fan" in pattern_id:
            field = sun
        else:
            field = np.clip(chevron * 0.44 + weave * 0.28 + sun * 0.30, 0, 1)
        field = np.clip(field + fine * 0.13 + sparkle * 0.13, 0, 1)

    elif mode == "op":
        rings = _spb_gridline(r + np.sin(a * (4 + variant % 8)) * 0.018, 28 + variant, 0.016, phase)
        warp_x = xf + np.sin(yf * 23.0 + phase * 6.28) * 0.035
        warp_y = yf + np.sin(xf * 21.0 - phase * 6.28) * 0.035
        checker = ((_spb_frac(warp_x * (12 + variant)) > 0.5) ^ (_spb_frac(warp_y * (11 + variant % 8)) > 0.5)).astype(np.float32)
        moire = _spb_gridline(warp_x + warp_y * 0.63, 25 + variant, 0.014, phase)
        field = np.clip(rings * 0.38 + checker * 0.28 + moire * 0.42 + fine * 0.12, 0, 1)

    elif mode == "math":
        z_x = cx * (2.7 + (variant % 4) * 0.2)
        z_y = cy * (2.7 + (variant % 5) * 0.16)
        acc = np.zeros((h, w), dtype=np.float32)
        zx, zy = z_x.copy(), z_y.copy()
        c1 = np.sin(phase * 6.28) * 0.42
        c2 = np.cos(phase * 6.28) * 0.32
        for _ in range(4):
            zx, zy = zx * zx - zy * zy + c1, 2.0 * zx * zy + c2
            acc += np.exp(-np.clip(zx * zx + zy * zy, 0, 9))
        curves = _spb_gridline(acc, 9 + variant, 0.020, phase)
        field = np.clip(curves * 0.64 + _spb_hex_lines(xf, yf, 13 + variant, 0.018, phase) * 0.22 + fine * 0.18 + sparkle * 0.18, 0, 1)

    elif mode == "weather":
        flow = _spb_gridline(yf + np.sin(xf * (11 + variant) + phase * 6.28) * 0.090, 13 + variant, 0.022, phase)
        fork = _spb_gridline(xf + np.sin(yf * 27.0 + phase) * 0.055, 18 + variant, 0.011, phase)
        rings = _spb_gridline(r + np.sin(a * 7.0) * 0.024, 22 + variant, 0.018, phase)
        if "lightning" in pattern_id:
            field = np.maximum(fork, fork * (noise > 0.68))
        elif "ripple" in pattern_id or "wave" in pattern_id:
            field = rings
        elif "tornado" in pattern_id:
            field = _spb_gridline(a / (2 * np.pi) + r * (2.5 + variant * 0.05), 24 + variant, 0.018, phase)
        else:
            field = np.clip(flow * 0.42 + fork * 0.30 + rings * 0.24, 0, 1)
        field = np.clip(field + fine * 0.16 + sparkle * 0.20, 0, 1)

    elif mode == "abstract":
        flow = _spb_normalize01(np.sin((xf * (18 + variant) + np.sin(yf * 17.0) * 0.18) * 6.28)
                                + np.sin((yf * (21 + variant % 7) + np.cos(xf * 19.0) * 0.16) * 6.28))
        crack = _spb_hex_lines(xf + fine * 0.06, yf - fine * 0.05, 18 + variant, 0.016, phase)
        star = (noise > (0.88 - (variant % 4) * 0.015)).astype(np.float32)
        if "stardust" in pattern_id:
            field = np.clip(star * 0.78 + fine * 0.30 + sparkle * 0.44, 0, 1)
        elif "sound" in pattern_id:
            carrier = _spb_gridline(yf + np.sin(xf * 36.0 + phase) * 0.08, 18 + variant, 0.016, phase)
            harmonics = _spb_gridline(yf - np.sin(xf * 54.0 - phase * 3.0) * 0.05, 27 + variant, 0.011, phase)
            field = np.clip(carrier * 0.58 + harmonics * 0.36 + fine * 0.22 + sparkle * 0.18, 0, 1)
        else:
            field = np.clip(flow * 0.36 + crack * 0.40 + star * 0.20 + fine * 0.16, 0, 1)

    elif mode == "paradigm":
        grid = _spb_hex_lines(xf, yf, 20 + variant, 0.016, phase)
        ghost = _spb_gridline(r + np.sin(a * (6 + variant % 7)) * 0.03, 26 + variant, 0.014, phase)
        neural = np.maximum(
            _spb_gridline(xf + np.sin(yf * 19.0) * 0.04, 17 + variant, 0.013, phase),
            _spb_gridline(yf + np.sin(xf * 23.0) * 0.04, 15 + variant, 0.013, phase),
        )
        field = np.clip(grid * 0.34 + ghost * 0.34 + neural * 0.36 + fine * 0.16 + sparkle * 0.18, 0, 1)

    elif mode == "animal":
        cellular = _spb_hex_lines(xf + fine * 0.05, yf + noise * 0.04, 10 + variant, 0.040, phase)
        shards = ((_spb_frac(xf * (9 + variant) + noise * 0.25) > 0.48) ^ (_spb_frac(yf * (8 + variant) + fine * 0.20) > 0.53)).astype(np.float32)
        field = np.clip(cellular * 0.52 + shards * 0.26 + fine * 0.18 + sparkle * 0.16, 0, 1)

    elif mode == "gothic":
        vine = _spb_gridline(yf + np.sin(xf * 16.0 + phase * 6.28) * 0.075, 10 + variant, 0.018, phase)
        thorn = _spb_gridline(xf - yf * 0.8, 20 + variant, 0.012, phase)
        rose = _spb_gridline(r + np.sin(a * 8.0) * 0.035, 18 + variant, 0.016, phase)
        field = np.clip(vine * 0.44 + thorn * 0.28 + rose * 0.30 + fine * 0.13 + sparkle * 0.13, 0, 1)

    elif mode == "metal":
        weave = np.maximum(_spb_gridline(xf + yf * 0.18, 32 + variant, 0.014, phase),
                           _spb_gridline(yf - xf * 0.18, 30 + variant, 0.014, phase * 1.4))
        flake = (noise > 0.82).astype(np.float32)
        field = np.clip(weave * 0.50 + flake * 0.36 + fine * 0.24 + sparkle * 0.24, 0, 1)

    elif mode == "shokk":
        px = ((_spb_frac(xf * (30 + variant)) > 0.45) & (_spb_frac(yf * (28 + variant)) > 0.45)).astype(np.float32)
        scan = _spb_gridline(yf + np.sin(xf * 20.0) * 0.02, 34 + variant, 0.010, phase)
        field = np.clip(px * 0.50 + scan * 0.32 + fine * 0.16 + sparkle * 0.26, 0, 1)

    elif mode == "decade":
        if "_50s_" in pattern_id:
            atom = np.maximum(_spb_gridline(r, 14 + variant, 0.020, phase), _spb_gridline(a / (2 * np.pi), 8 + variant, 0.028, phase))
            chrome = np.maximum(_spb_gridline(xf, 16 + variant, 0.016, phase), _spb_gridline(yf, 12 + variant, 0.016, phase))
            field = np.clip(atom * 0.48 + chrome * 0.30 + fine * 0.20 + sparkle * 0.16, 0, 1)
        elif "_60s_" in pattern_id:
            swirl = _spb_gridline(a / (2 * np.pi) + r * (2.0 + variant * 0.08), 18 + variant, 0.024, phase)
            dots = ((np.sin(xf * 75.0) * np.sin(yf * 75.0)) > 0.50).astype(np.float32)
            field = np.clip(swirl * 0.44 + dots * 0.24 + fine * 0.22 + sparkle * 0.16, 0, 1)
        elif "_70s_" in pattern_id:
            disco = _spb_hex_lines(xf, yf, 12 + variant, 0.025, phase)
            zig = _spb_gridline(yf + np.abs(_spb_frac(xf * 6.0) - 0.5) * 0.45, 13 + variant, 0.021, phase)
            field = np.clip(disco * 0.42 + zig * 0.34 + fine * 0.18 + sparkle * 0.24, 0, 1)
        elif "_80s_" in pattern_id:
            grid = np.maximum(_spb_gridline(xf, 18 + variant, 0.016, phase), _spb_gridline(yf, 18 + variant, 0.016, phase))
            laser = _spb_gridline(xf - yf * 0.72, 14 + variant, 0.012, phase)
            field = np.clip(grid * 0.42 + laser * 0.34 + fine * 0.18 + sparkle * 0.24, 0, 1)
        else:
            grunge = (_spb_hash_field((h, w), seed + family * 3) > 0.62).astype(np.float32)
            y2k = _spb_gridline(r + np.sin(a * 5.0) * 0.024, 20 + variant, 0.016, phase)
            static = _spb_gridline(yf + noise * 0.05, 24 + variant, 0.012, phase)
            field = np.clip(grunge * 0.26 + y2k * 0.38 + static * 0.26 + fine * 0.18 + sparkle * 0.18, 0, 1)

    else:
        field = np.clip(fine * 0.85 + sparkle * 0.25, 0, 1)

    if pattern_id in _SPB_PATTERN_AUDIT_BOOST_IDS:
        contour = _spb_gridline(fine + r * (0.45 + (variant % 5) * 0.04) + np.sin(a * (4 + variant % 6)) * 0.035,
                                12 + variant, 0.026, phase)
        mesh = _spb_hex_lines(xf + fine * 0.025, yf - fine * 0.025, 13 + variant, 0.024, phase)
        streak = _spb_gridline(yf + np.sin(xf * (24 + variant) + phase * 6.28) * 0.055,
                               18 + variant, 0.018, phase)
        if mode == "weather":
            boost = np.maximum(contour, streak)
        elif mode == "math":
            boost = np.maximum(contour, mesh)
        else:
            boost = np.clip(contour * 0.54 + mesh * 0.36 + streak * 0.28, 0, 1)
        field = np.clip(field * 0.56 + boost * 0.62 + fine * 0.10 + sparkle * 0.20, 0, 1)

    field = _spb_normalize01(field)
    field = np.clip(field * (0.86 + min(max(float(sm), 0.0), 2.0) * 0.08) + fine * 0.10 + sparkle * 0.12, 0, 1)
    return _spb_normalize01(field).astype(np.float32)


def _spb_make_rebuilt_pattern_texture(pattern_id, mode, original_texture=None):
    def _texture(shape, mask, seed, sm):
        h, w = shape[:2] if len(shape) > 2 else shape
        mask_arr = np.asarray(mask, dtype=np.float32) if mask is not None else np.ones((h, w), dtype=np.float32)
        pv = _spb_rebuilt_pattern_value(pattern_id, mode, (h, w), seed, sm)
        pv = np.clip(pv * mask_arr, 0, 1).astype(np.float32)
        edge = pv if mode == "tech" else _spb_edge_energy(pv)
        return {
            "pattern_val": pv,
            "M_range": float(84 + (_spb_hash_seed(pattern_id) % 72)),
            "R_range": float(58 + ((_spb_hash_seed(pattern_id) >> 5) % 72)),
            "edge_val": edge,
        }
    _texture._spb_detail_wrapped = True
    _texture._spb_rebuilt_pattern = True
    return _texture


def _spb_make_rebuilt_pattern_paint(pattern_id, mode):
    def _paint(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        h, w = shape[:2] if len(shape) > 2 else shape
        mask_arr = np.asarray(mask, dtype=np.float32)
        if hasattr(bb, "ndim") and bb.ndim == 2:
            bb3 = bb[:, :, np.newaxis]
        else:
            bb3 = bb
        pv = _spb_rebuilt_pattern_value(pattern_id, mode, (h, w), seed + 4109, 1.0)
        edge = pv if mode == "tech" else _spb_edge_energy(pv)
        base_c, line_c, accent_c = _SPB_PATTERN_PALETTES.get(mode, _SPB_PATTERN_PALETTES["abstract"])
        phase = (_spb_hash_seed(pattern_id) % 360) * np.pi / 180.0
        hue_shift = np.array([
            0.08 * np.sin(phase),
            0.08 * np.sin(phase + 2.094),
            0.08 * np.sin(phase + 4.188),
        ], dtype=np.float32)
        base = np.clip(np.asarray(base_c, dtype=np.float32) + hue_shift * 0.45, 0, 1)
        line = np.clip(np.asarray(line_c, dtype=np.float32) + hue_shift, 0, 1)
        accent = np.clip(np.asarray(accent_c, dtype=np.float32) - hue_shift * 0.70, 0, 1)
        carrier = np.clip(pv * 0.78 + edge * 0.20, 0, 1)
        overlay = (
            base[np.newaxis, np.newaxis, :] * (1.0 - carrier[:, :, np.newaxis])
            + line[np.newaxis, np.newaxis, :] * carrier[:, :, np.newaxis]
            + accent[np.newaxis, np.newaxis, :] * np.clip(edge[:, :, np.newaxis] * 0.65, 0, 1)
        )
        if pattern_id in _SPB_PATTERN_AUDIT_BOOST_IDS:
            overlay = np.clip(overlay + pv[:, :, np.newaxis] * 0.12 + edge[:, :, np.newaxis] * 0.18, 0, 1)
        if bb3 is not None:
            overlay = np.clip(overlay + np.asarray(bb3, dtype=np.float32) * 0.18, 0, 1)
        blend = np.clip(float(pm) * 0.92, 0, 1) * mask_arr[:, :, np.newaxis]
        return np.ascontiguousarray(np.clip(paint[:, :, :3] * (1.0 - blend) + overlay * blend, 0, 1).astype(np.float32))
    _paint._spb_pattern_direct_paint = True
    return _paint


def _spb_apply_regular_pattern_rebuilds():
    rebuilt = 0
    _targets = [PATTERN_REGISTRY]
    _reg_mod = _sys.modules.get("engine.registry") if "_sys" in globals() else None
    _reg_patterns = getattr(_reg_mod, "PATTERN_REGISTRY", None)
    if isinstance(_reg_patterns, dict) and _reg_patterns is not PATTERN_REGISTRY:
        _targets.append(_reg_patterns)
    for _pid, _mode in _SPB_PATTERN_REBUILD_MODES.items():
        if _pid not in _SPB_BESPOKE_PATTERN_REBUILD_IDS:
            continue
        for _target in _targets:
            _entry = _target.get(_pid)
            if not isinstance(_entry, dict) or _entry.get("image_path"):
                continue
            _tex = _entry.get("texture_fn")
            if getattr(_tex, "_spb_rebuilt_pattern", False):
                continue
            _new_entry = dict(_entry)
            _new_entry["texture_fn"] = _spb_make_rebuilt_pattern_texture(_pid, _mode, _tex)
            if _mode == "tech":
                # Tech patterns should read as material circuitry in the spec map,
                # not repaint the whole car with a heavy RGB overlay.
                _new_entry["paint_fn"] = paint_none
            else:
                _new_entry["paint_fn"] = _spb_make_rebuilt_pattern_paint(_pid, _mode)
            _new_entry["desc"] = (_new_entry.get("desc") or "") + " | SPB Alpha high-detail rebuilt pattern."
            _target[_pid] = _new_entry
            if _target is PATTERN_REGISTRY:
                rebuilt += 1
    if rebuilt:
        print(f"  [Pattern Rebuild] Applied {rebuilt} high-detail regular pattern renderers")


def _spb_mono_profile(pv_weight, fine_weight, sparkle_weight, m_base, m_detail, m_edge,
                      r_base, r_detail, r_edge, cc_base, cc_detail, cc_fine, blend,
                      tint_a, tint_b):
    return {
        "pv_weight": float(pv_weight),
        "fine_weight": float(fine_weight),
        "sparkle_weight": float(sparkle_weight),
        "m_base": float(m_base),
        "m_detail": float(m_detail),
        "m_edge": float(m_edge),
        "r_base": float(r_base),
        "r_detail": float(r_detail),
        "r_edge": float(r_edge),
        "cc_base": float(cc_base),
        "cc_detail": float(cc_detail),
        "cc_fine": float(cc_fine),
        "blend": float(blend),
        "tint_a": tuple(float(v) for v in tint_a),
        "tint_b": tuple(float(v) for v in tint_b),
    }


_PATTERN_MONO_PROFILES = {
    "hex_mandala": _spb_mono_profile(0.88, 0.08, 0.04, 48, 166, 56, 90, -86, 30, 28, 108, 18, 0.62, (0.08, 0.32, 0.80), (0.96, 0.74, 0.18)),
    "lace_filigree": _spb_mono_profile(0.90, 0.07, 0.03, 28, 118, 44, 118, -62, 38, 36, 92, 24, 0.54, (0.84, 0.76, 0.66), (0.98, 0.94, 0.82)),
    "honeycomb_organic": _spb_mono_profile(0.86, 0.10, 0.04, 36, 142, 64, 104, -72, 42, 24, 104, 20, 0.58, (0.20, 0.12, 0.04), (0.96, 0.66, 0.12)),
    "baroque_scrollwork": _spb_mono_profile(0.91, 0.06, 0.03, 58, 174, 62, 86, -84, 34, 30, 116, 22, 0.66, (0.30, 0.16, 0.05), (1.00, 0.70, 0.18)),
    "art_nouveau_vine": _spb_mono_profile(0.87, 0.10, 0.03, 24, 128, 42, 112, -68, 28, 26, 96, 18, 0.60, (0.06, 0.28, 0.10), (0.68, 0.92, 0.34)),
    "penrose_quasi": _spb_mono_profile(0.84, 0.10, 0.06, 8, 188, 66, 76, -92, 32, 34, 112, 26, 0.64, (0.10, 0.26, 0.62), (0.98, 0.32, 0.80)),
    "topographic_dense": _spb_mono_profile(0.92, 0.06, 0.02, 22, 132, 78, 130, -70, 46, 22, 88, 16, 0.50, (0.10, 0.22, 0.12), (0.76, 0.64, 0.36)),
    "interference_rings": _spb_mono_profile(0.83, 0.10, 0.07, 10, 190, 58, 70, -94, 26, 40, 118, 30, 0.68, (0.02, 0.46, 0.92), (1.00, 0.18, 0.70)),
    "brushed_metal_fine": _spb_mono_profile(0.89, 0.08, 0.03, 70, 138, 58, 72, -74, 42, 24, 82, 18, 0.45, (0.30, 0.34, 0.38), (0.82, 0.78, 0.68)),
}


_ORNAMENTAL_PAINT_STYLES = {
    "hex_mandala": {
        "base": (0.05, 0.10, 0.22), "line": (0.96, 0.70, 0.18), "shadow": (0.02, 0.04, 0.12),
        "detail": 1.05, "edge": 1.35, "blend": 0.88,
    },
    "lace_filigree": {
        "base": (0.18, 0.16, 0.14), "line": (0.98, 0.92, 0.78), "shadow": (0.06, 0.05, 0.05),
        "detail": 1.16, "edge": 1.10, "blend": 0.80,
    },
    "honeycomb_organic": {
        "base": (0.25, 0.14, 0.03), "line": (0.98, 0.58, 0.08), "shadow": (0.09, 0.04, 0.00),
        "detail": 1.05, "edge": 1.45, "blend": 0.84,
    },
    "baroque_scrollwork": {
        "base": (0.18, 0.09, 0.02), "line": (1.00, 0.66, 0.12), "shadow": (0.06, 0.025, 0.00),
        "detail": 1.12, "edge": 1.32, "blend": 0.88,
    },
    "art_nouveau_vine": {
        "base": (0.03, 0.16, 0.08), "line": (0.58, 0.95, 0.34), "shadow": (0.01, 0.06, 0.025),
        "detail": 1.10, "edge": 1.20, "blend": 0.84,
    },
    "penrose_quasi": {
        "base": (0.08, 0.05, 0.22), "line": (0.92, 0.26, 0.98), "shadow": (0.02, 0.02, 0.10),
        "detail": 1.02, "edge": 1.55, "blend": 0.90,
    },
    "topographic_dense": {
        "base": (0.16, 0.17, 0.09), "line": (0.78, 0.66, 0.34), "shadow": (0.04, 0.06, 0.025),
        "detail": 1.18, "edge": 1.05, "blend": 0.78,
    },
    "interference_rings": {
        "base": (0.03, 0.07, 0.16), "line": (0.08, 0.78, 1.00), "shadow": (0.12, 0.02, 0.17),
        "detail": 1.04, "edge": 1.42, "blend": 0.90,
    },
}


def _spb_pattern_mono_profile(pattern_id):
    return _PATTERN_MONO_PROFILES.get(pattern_id) or _spb_mono_profile(
        0.82, 0.13, 0.05,
        38, 138, 42,
        80, -86, 32,
        24, 84, 20,
        0.58,
        (0.26, 0.36, 0.52),
        (0.88, 0.62, 0.32),
    )


def _spb_pattern_detail_value(pattern_id, texture_fn, shape, mask, seed, sm):
    tex = texture_fn(shape, mask, seed, sm)
    if not isinstance(tex, dict) or "pattern_val" not in tex:
        return None, tex
    pv = _spb_normalize01(tex["pattern_val"])
    family = _spb_hash_seed(pattern_id) & 0xFFFF
    fine, sparkle = _spb_micro_detail(shape, seed + 3307, family)
    profile = _spb_pattern_mono_profile(pattern_id)
    # Keep the named pattern dominant, then fill empty visual space with
    # pixel-scale detail so 2048 renders do not collapse into flat blobs.
    detail = np.clip(
        pv * profile["pv_weight"] + fine * profile["fine_weight"] + sparkle * profile["sparkle_weight"],
        0,
        1,
    ).astype(np.float32)
    tex = dict(tex)
    tex["pattern_val"] = detail
    if "M_range" in tex:
        tex["M_range"] = float(tex.get("M_range") or 0.0) * 1.08
    if "R_range" in tex:
        tex["R_range"] = float(tex.get("R_range") or 0.0) * 1.08
    return detail, tex


def _spb_wrap_pattern_registry_detail():
    """Late registry ratchet for explicitly profiled pattern-driven monolithics."""
    for _pid, _entry in list(PATTERN_REGISTRY.items()):
        if _pid not in _PATTERN_MONO_PROFILES:
            continue
        if not isinstance(_entry, dict):
            continue
        _tex_fn = _entry.get("texture_fn")
        if _tex_fn is None or getattr(_tex_fn, "_spb_detail_wrapped", False):
            continue

        def _make_wrapped(pid, tex_fn):
            def _wrapped(shape, mask, seed, sm):
                detail, tex = _spb_pattern_detail_value(pid, tex_fn, shape, mask, seed, sm)
                if tex is None:
                    return tex_fn(shape, mask, seed, sm)
                return tex
            _wrapped._spb_detail_wrapped = True
            return _wrapped

        _entry = dict(_entry)
        _entry["texture_fn"] = _make_wrapped(_pid, _tex_fn)
        PATTERN_REGISTRY[_pid] = _entry


_SPB_PATTERN_QUALITY_FLOOR_IDS = {
    "decade_50s_jukebox_arc",
    "decade_50s_atomic_reactor",
    "decade_50s_diner_chrome",
    "decade_60s_peace_sign",
    "decade_60s_lava_lamp_blob",
    "decade_60s_caged_square",
    "decade_60s_peter_max_gradient",
    "decade_60s_peter_max_alt",
    "decade_80s_breakdance_spin",
    "decade_80s_laser_tag",
    "decade_90s_grunge_splatter",
    "decade_90s_tamagotchi_egg",
    "decade_90s_fresh_prince",
    "decade_90s_sbtb_wall",
    "fractal_fern",
    "wave_ripple_2d",
}


def _spb_wrap_texture_quality_floor(pattern_id, texture_fn):
    if getattr(texture_fn, "_spb_quality_floor_wrapped", False):
        return texture_fn

    def _wrapped(shape, mask, seed, sm):
        tex = texture_fn(shape, mask, seed, sm)
        if not isinstance(tex, dict) or "pattern_val" not in tex:
            return tex
        h, w = shape[:2] if len(shape) > 2 else shape
        pv = _spb_normalize01(np.asarray(tex["pattern_val"], dtype=np.float32))
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        family = _spb_hash_seed(pattern_id) ^ (int(seed) * 2654435761)
        phase = (family % 360) * np.pi / 180.0
        print_dot = (
            np.sin(xx * (1.11 + (family % 5) * 0.029) + yy * 0.19 + phase)
            * np.sin(yy * (1.23 + (family % 7) * 0.025) - xx * 0.15 - phase)
        ) * 0.5 + 0.5
        screen = (
            (np.mod(xx + yy * 0.41 + (family % 31), 7.0) < 1.05)
            | (np.mod(xx - yy * 0.33 + (family % 37), 11.0) < 0.90)
        ).astype(np.float32)
        stamp = _spb_normalize01(np.sin((xx + yy * 0.21) * 0.47 + phase) + np.sin((yy - xx * 0.17) * 0.59 - phase))
        carrier = np.clip(print_dot * 0.46 + screen * 0.34 + stamp * 0.20, 0, 1)
        if pattern_id.startswith("decade_90s_"):
            weight = 0.34
        elif pattern_id.startswith("decade_"):
            weight = 0.26
        else:
            weight = 0.22
        detail = _spb_normalize01(np.clip(pv * (1.0 - weight) + carrier * weight, 0, 1)).astype(np.float32)
        out = dict(tex)
        out["pattern_val"] = detail
        if "M_range" in out:
            out["M_range"] = max(float(out.get("M_range") or 0.0), 0.24)
        if "R_range" in out:
            out["R_range"] = max(float(out.get("R_range") or 0.0), 0.24)
        return out

    _wrapped._spb_quality_floor_wrapped = True
    return _wrapped


def _spb_apply_pattern_quality_floor():
    wrapped = 0
    for _pid in _SPB_PATTERN_QUALITY_FLOOR_IDS:
        _entry = PATTERN_REGISTRY.get(_pid)
        if not isinstance(_entry, dict) or _entry.get("image_path"):
            continue
        _tex_fn = _entry.get("texture_fn")
        if not callable(_tex_fn) or getattr(_tex_fn, "_spb_quality_floor_wrapped", False):
            continue
        _new_entry = dict(_entry)
        _new_entry["texture_fn"] = _spb_wrap_texture_quality_floor(_pid, _tex_fn)
        PATTERN_REGISTRY[_pid] = _new_entry
        wrapped += 1
    if wrapped:
        print(f"  [Pattern Quality Floor] Added 2048 detail carrier to {wrapped} weak renderer(s)")


_spb_wrap_pattern_registry_detail()
_spb_apply_regular_pattern_rebuilds()
_spb_apply_pattern_quality_floor()


# ================================================================
# CATCH-ALL: Wire unregistered UI monolithics to family-based fallbacks
# These are catalog entries that were added for UI but never got specific engine functions.
# Rather than silently rendering nothing, map them to the closest generic behavior.
# ================================================================
try:
    import json as _json_reg
    import os as _os_reg

    # Load the UI finish data to find monolithic IDs that are in the catalog
    _finish_data_path = _os_reg.path.join(_os_reg.path.dirname(_os_reg.path.abspath(__file__)), 'paint-booth-0-finish-data.js')
    if _os_reg.path.exists(_finish_data_path):
        import re as _re_reg
        with open(_finish_data_path, 'r', encoding='utf-8') as _fdf:
            _fd_content = _fdf.read()

        # Find all IDs in the monolithics/specials section
        _mono_section_start = _fd_content.find('const MONOLITHICS')
        if _mono_section_start < 0:
            _mono_section_start = _fd_content.find('const SPECIALS')
        if _mono_section_start >= 0:
            _mono_section_end = _fd_content.find('\n];', _mono_section_start)
            _mono_section = (
                _fd_content[_mono_section_start:_mono_section_end]
                if _mono_section_end > _mono_section_start
                else _fd_content[_mono_section_start:]
            )
            _ui_mono_ids = [
                _mid for _mid in _re_reg.findall(r'id:\s*"([^"]+)"', _mono_section)
                if not str(_mid).isdigit()
            ]
            _missing_monos = [m for m in _ui_mono_ids if m not in MONOLITHIC_REGISTRY]

            # Diverse fallback pools — each family resolves to a SET of registered
            # functions, and we pick deterministically via hash so that the 8
            # Ornamental finishes (for example) look DIFFERENT from each other
            # instead of all collapsing to sparkle_diamond_dust. The per-family
            # pool is curated so visually appropriate functions are chosen
            # (weave-like for carbon, damask-like for ornamental, etc.).
            def _filter_pool(pool):
                return [p for p in pool if p in MONOLITHIC_REGISTRY]

            _EFFECTS_POOL = _filter_pool([
                'thermochromic', 'wormhole', 'void', 'static', 'scorched',
                'radioactive', 'aurora', 'galaxy', 'spectral_prismatic_flip',
                'spectral_neon_reactive', 'spectral_rainbow_metal',
                'reactive_plasma', 'reactive_pulse_metal', 'reactive_ghost_metal',
                'sparkle_galaxy', 'sparkle_constellation', 'sparkle_meteor',
                'sparkle_starfield', 'sparkle_firefly', 'sparkle_lightning_bug',
                'wave_candy_flow', 'wave_chrome_tide', 'wave_turbulent_flow',
                'trizone_frozen_ember_chrome', 'trizone_vanta_chrome_pearl',
                'weather_volcanic_ash', 'weather_acid_rain', 'thermal_titanium',
            ])
            _CARBON_POOL = _filter_pool([
                'weathered_metal', 'thin_film', 'wave_moire_metal',
                'spectral_mono_chrome', 'trizone_pearl_carbon_gold',
                'trizone_titanium_copper_chrome', 'velvet', 'worn_chrome',
            ])
            _ORNAMENTAL_POOL = _filter_pool([
                'quilt_pearl_patchwork', 'quilt_random_chaos',
                'spectral_earth_sky', 'spectral_complementary',
                'trizone_chrome_candy_matte', 'trizone_glass_metal_matte',
                'trizone_mercury_obsidian_candy', 'trizone_anodized_candy_silk',
                'wave_pearl_current', 'wave_standing_chrome',
            ])
            _FUSION_POOL = _filter_pool([
                'spectral_prismatic_flip', 'spectral_rainbow_metal',
                'spectral_warm_cool', 'spectral_dark_light',
                'trizone_ceramic_flake_satin', 'trizone_stealth_spectra_frozen',
                'wave_dual_frequency', 'wave_metallic_pulse',
                'wave_circular_radar', 'wave_diagonal_sweep',
                'reactive_warm_cold', 'reactive_chrome_fade',
                'reactive_dual_tone', 'reactive_mirror_shadow',
                'sparkle_galaxy', 'sparkle_confetti', 'sparkle_starfield',
                'aurora', 'galaxy', 'wormhole',
            ])
            _SPARKLE_POOL = _filter_pool([
                'sparkle_diamond_dust', 'sparkle_champagne', 'sparkle_confetti',
                'sparkle_constellation', 'sparkle_firefly', 'sparkle_galaxy',
                'sparkle_lightning_bug', 'sparkle_meteor', 'sparkle_snowfall',
                'sparkle_starfield',
            ])
            _WAVE_POOL = _filter_pool([
                'wave_candy_flow', 'wave_chrome_tide', 'wave_circular_radar',
                'wave_diagonal_sweep', 'wave_dual_frequency',
                'wave_metallic_pulse', 'wave_moire_metal', 'wave_pearl_current',
                'wave_standing_chrome', 'wave_turbulent_flow',
            ])
            _WEATHER_POOL = _filter_pool([
                'weather_acid_rain', 'weather_barn_dust', 'weather_desert_blast',
                'weather_hood_bake', 'weather_ice_storm', 'weather_ocean_mist',
                'weather_road_spray', 'weather_salt_spray', 'weather_sun_fade',
                'weather_volcanic_ash', 'weathered_metal', 'weathered_paint',
            ])

            def _pick_from_pool(pool, key):
                if not pool:
                    return None
                # Deterministic pick by FNV-ish hash of the id so repeated loads
                # produce the same assignment
                h = 2166136261
                for ch in key:
                    h ^= ord(ch)
                    h = (h * 16777619) & 0xFFFFFFFF
                return pool[h % len(pool)]

            # Map of family prefixes -> pool name; used to route unknown IDs.
            # Order matters: first match wins, so list specific prefixes first.
            _PREFIX_ROUTES = [
                ('carbon_',     _CARBON_POOL),
                ('weave_',      _CARBON_POOL),
                ('cf_',         _FUSION_POOL),
                ('fusion_',     _FUSION_POOL),
                ('atelier_',    _ORNAMENTAL_POOL),
                ('ornate_',     _ORNAMENTAL_POOL),
                ('damask_',     _ORNAMENTAL_POOL),
                ('filigree_',   _ORNAMENTAL_POOL),
                ('cc_',         _EFFECTS_POOL),
                ('prizm_',      _EFFECTS_POOL),
                ('chameleon_',  _EFFECTS_POOL),
                ('guilloche_',  _ORNAMENTAL_POOL),
                ('cs_',         _EFFECTS_POOL),
                ('neon_',       _EFFECTS_POOL),
                ('depth_',      _FUSION_POOL),
                ('fractal_',    _EFFECTS_POOL),
                ('wave_',       _WAVE_POOL),
                ('heat_',       _WEATHER_POOL),
                ('crystal_',    _EFFECTS_POOL),
                ('dark_',       _EFFECTS_POOL),
                ('acid_',       _WEATHER_POOL),
                ('laser_',      _EFFECTS_POOL),
                ('meteor_',     _EFFECTS_POOL),
                ('plasma_',     _EFFECTS_POOL),
                ('volcanic_',   _WEATHER_POOL),
                ('electric_',   _EFFECTS_POOL),
                ('diamond_',    _SPARKLE_POOL),
                ('patina_',     _WEATHER_POOL),
                ('micro_',      _SPARKLE_POOL),
                ('sparkle_',    _SPARKLE_POOL),
                ('reactive_',   _FUSION_POOL),
                ('spectral_',   _FUSION_POOL),
                ('trizone_',    _FUSION_POOL),
                ('aurora_',     _EFFECTS_POOL),
                ('brushed_',    _CARBON_POOL),
                ('black_',      _EFFECTS_POOL),
            ]

            # Explicit one-to-one mapping for a handful of high-profile
            # Effects & Vision IDs so the picker shows a visually-distinct
            # representative for each name (no more "everything is aurora").
            _EV_EXPLICIT = {
                'acid_trip':           'wormhole',
                'antimatter':          'void',
                'astral':              'galaxy',
                'banshee':             'static',
                'black_diamond':       'sparkle_diamond_dust',
                'blood_oath':          'weather_acid_rain',
                'bone':                'weathered_paint',
                'catacombs':           'void',
                'cel_shade':           'trizone_glass_metal_matte',
                'chromatic_aberration':'spectral_prismatic_flip',
                'crt_scanline':        'static',
                'crystal_cave':        'sparkle_constellation',
                'cursed':              'weather_salt_spray',
                'daguerreotype':       'weathered_metal',
                'dark_fairy':          'sparkle_firefly',
                'dark_ritual':         'void',
                'datamosh':            'static',
                'death_metal':         'worn_chrome',
                'demon_forge':         'weather_volcanic_ash',
                'double_exposure':     'spectral_complementary',
                'dragon_breath':       'weather_volcanic_ash',
                'dreamscape':          'aurora',
                'eclipse':             'void',
                'embossed':            'quilt_random_chaos',
                'enchanted':           'sparkle_firefly',
                'ethereal':            'aurora',
                'film_burn':           'weather_hood_bake',
                'fish_eye':            'wave_circular_radar',
                'fourth_dimension':    'wormhole',
                'galaxy':              'galaxy',
                'gargoyle':            'weathered_metal',
                'glitch':              'static',
                'glitch_reality':      'spectral_prismatic_flip',
                'graveyard':           'weather_barn_dust',
                'grid_walk':           'wave_diagonal_sweep',
                'halftone':            'trizone_chrome_candy_matte',
                'hallucination':       'aurora',
                'haunted':             'sparkle_lightning_bug',
                'heat_haze':           'weather_hood_bake',
                'hellhound':           'weather_volcanic_ash',
                'holographic_wrap':    'spectral_rainbow_metal',
                'infrared':            'thermal_titanium',
                'iron_maiden':         'worn_chrome',
                'kaleidoscope':        'spectral_prismatic_flip',
                'levitation':          'aurora',
                'lich_king':           'weather_ice_storm',
                'long_exposure':       'sparkle_starfield',
                'mirage':              'wave_standing_chrome',
                'multiverse':          'spectral_rainbow_metal',
                'nebula_core':         'galaxy',
                'necrotic':            'weather_salt_spray',
                'negative':            'spectral_inverse_logic' if 'spectral_inverse_logic' in MONOLITHIC_REGISTRY else 'spectral_complementary',
                'nightmare':           'void',
                'parallax':            'wave_diagonal_sweep',
                'phantom':             'sparkle_firefly',
                'phantom_zone':        'wormhole',
                'polarized':           'spectral_prismatic_flip',
                'portal':              'wormhole',
                'possessed':           'static',
                'psychedelic':         'wave_turbulent_flow',
                'reaper':              'void',
                'refraction':          'spectral_rainbow_metal',
                'rust':                'weather_acid_rain',
                'sepia':               'weather_sun_fade',
                'shadow_realm':        'void',
                'silk_road':           'weather_desert_blast',
                'solarization':        'sparkle_starfield',
                'spectral':            'spectral_prismatic_flip',
                'tesseract':           'wormhole',
                'thermochromic':       'thermochromic',
                'tin_type':            'weathered_metal',
                'uv_blacklight':       'sparkle_firefly',
                'vinyl_record':        'wave_circular_radar',
                'void_walker':         'void',
                'voodoo':              'static',
                'wraith':              'sparkle_firefly',
                'x_ray':               'spectral_inverse_logic' if 'spectral_inverse_logic' in MONOLITHIC_REGISTRY else 'spectral_mono_chrome',
            }

            def _resolve_fallback(mid):
                # 1. Explicit E&V mapping
                if mid in _EV_EXPLICIT:
                    t = _EV_EXPLICIT[mid]
                    if t in MONOLITHIC_REGISTRY:
                        return t
                # 2. Prefix-routed pool (diverse pick via hash)
                for prefix, pool in _PREFIX_ROUTES:
                    if mid.startswith(prefix):
                        picked = _pick_from_pool(pool, mid)
                        if picked and picked in MONOLITHIC_REGISTRY:
                            return picked
                # 3. Last resort: round-robin across all known pools rather than
                # always returning aurora
                for pool in (_EFFECTS_POOL, _FUSION_POOL, _SPARKLE_POOL,
                             _WAVE_POOL, _WEATHER_POOL, _ORNAMENTAL_POOL,
                             _CARBON_POOL):
                    picked = _pick_from_pool(pool, mid)
                    if picked and picked in MONOLITHIC_REGISTRY:
                        return picked
                # 4. Hard fallback
                for name in ('aurora', 'sparkle_diamond_dust'):
                    if name in MONOLITHIC_REGISTRY:
                        return name
                return None

            _fallback_wired = 0
            _fallback_diversity = set()
            CATALOG_FALLBACK_WIRED_IDS = globals().setdefault("CATALOG_FALLBACK_WIRED_IDS", set())
            CATALOG_FALLBACK_WIRED_TO = globals().setdefault("CATALOG_FALLBACK_WIRED_TO", {})
            for _mid in _missing_monos:
                _fallback_id = _resolve_fallback(_mid)
                if _fallback_id and _fallback_id in MONOLITHIC_REGISTRY:
                    MONOLITHIC_REGISTRY[_mid] = MONOLITHIC_REGISTRY[_fallback_id]
                    CATALOG_FALLBACK_WIRED_IDS.add(_mid)
                    CATALOG_FALLBACK_WIRED_TO[_mid] = _fallback_id
                    _fallback_diversity.add(_fallback_id)
                    _fallback_wired += 1

            if _fallback_wired:
                print(f"  [Catalog Fallback] Wired {_fallback_wired} unregistered monolithics to family fallbacks")
                print(f"  [Catalog Fallback] Distinct fallback behaviors used: {len(_fallback_diversity)}")
                print(f"  [Catalog Fallback] Total monolithics now: {len(MONOLITHIC_REGISTRY)}")
except Exception as _fb_err:
    print(f"  [Catalog Fallback] Warning: {_fb_err}")


def _spb_make_pattern_monolithic(pattern_id):
    entry = PATTERN_REGISTRY.get(pattern_id)
    if not isinstance(entry, dict) or entry.get("texture_fn") is None:
        return None
    texture_fn = entry["texture_fn"]

    def _spec(shape, *args, **kwargs):
        h, w = shape[:2] if len(shape) > 2 else shape
        if args and isinstance(args[0], np.ndarray):
            seed = args[1] if len(args) > 1 else kwargs.get("seed", 0)
            sm = args[2] if len(args) > 2 else kwargs.get("sm", 1.0)
            base_m = kwargs.get("base_m", 80)
            base_r = kwargs.get("base_r", 80)
        else:
            seed = args[0] if len(args) > 0 else kwargs.get("seed", 0)
            sm = args[1] if len(args) > 1 else kwargs.get("sm", 1.0)
            base_m = args[2] if len(args) > 2 else kwargs.get("base_m", 80)
            base_r = args[3] if len(args) > 3 else kwargs.get("base_r", 80)
        mask = np.ones((h, w), dtype=np.float32)
        detail, _tex = _spb_pattern_detail_value(pattern_id, texture_fn, (h, w), mask, seed, sm)
        if detail is None:
            detail = np.zeros((h, w), dtype=np.float32)
        family = _spb_hash_seed(pattern_id)
        fine, sparkle = _spb_micro_detail((h, w), seed + 4703, family)
        profile = _spb_pattern_mono_profile(pattern_id)
        edge = np.clip(np.abs(detail - np.roll(detail, 1, axis=0)) + np.abs(detail - np.roll(detail, 1, axis=1)), 0, 1)
        M = float(base_m) + (
            profile["m_base"]
            + detail * profile["m_detail"]
            + edge * profile["m_edge"]
            + sparkle * 30.0
        ) * sm
        R = float(base_r) + (
            profile["r_base"]
            + detail * profile["r_detail"]
            + edge * profile["r_edge"]
            - sparkle * 18.0
        ) * sm
        CC = profile["cc_base"] + detail * profile["cc_detail"] + fine * profile["cc_fine"] + sparkle * 24.0
        return (
            np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32),
        )

    def _paint(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        h, w = shape[:2] if len(shape) > 2 else shape
        detail, _tex = _spb_pattern_detail_value(pattern_id, texture_fn, (h, w), mask, seed, 1.0)
        if detail is None:
            return np.ascontiguousarray(paint[:, :, :3].astype(np.float32))
        family = _spb_hash_seed(pattern_id)
        fine, sparkle = _spb_micro_detail((h, w), seed + 5903, family)
        profile = _spb_pattern_mono_profile(pattern_id)
        phase = (family % 360) * np.pi / 180.0
        tint_a = np.asarray(profile["tint_a"], dtype=np.float32)
        tint_b = np.asarray(profile["tint_b"], dtype=np.float32)
        glint = np.array([
            0.50 + 0.22 * np.sin(phase + 0.0),
            0.50 + 0.22 * np.sin(phase + 2.09),
            0.50 + 0.22 * np.sin(phase + 4.18),
        ], dtype=np.float32)
        carrier = np.clip(detail * 0.78 + fine * 0.16 + sparkle * 0.06, 0, 1)
        overlay = tint_a[np.newaxis, np.newaxis, :] * carrier[:, :, np.newaxis] + tint_b[np.newaxis, np.newaxis, :] * (1.0 - carrier[:, :, np.newaxis])
        overlay = np.clip(overlay + glint[np.newaxis, np.newaxis, :] * sparkle[:, :, np.newaxis] * 0.18, 0, 1)
        shade = (0.70 + detail * 0.24 + sparkle * 0.20)[:, :, np.newaxis]
        blend = np.clip(pm * profile["blend"], 0, 1) * mask[:, :, np.newaxis]
        style = _ORNAMENTAL_PAINT_STYLES.get(pattern_id)
        if style is not None:
            edge = np.clip(np.abs(detail - np.roll(detail, 1, axis=0)) + np.abs(detail - np.roll(detail, 1, axis=1)), 0, 1)
            ink = np.clip(detail * style["detail"] + edge * style["edge"] + sparkle * 0.22, 0, 1)
            base = np.asarray(style["base"], dtype=np.float32)
            line = np.asarray(style["line"], dtype=np.float32)
            shadow = np.asarray(style["shadow"], dtype=np.float32)
            enamel = base[np.newaxis, np.newaxis, :] * (1.0 - ink[:, :, np.newaxis]) + line[np.newaxis, np.newaxis, :] * ink[:, :, np.newaxis]
            groove = np.clip(edge * 1.8 - detail * 0.25, 0, 1)[:, :, np.newaxis]
            enamel = enamel * (1.0 - groove * 0.35) + shadow[np.newaxis, np.newaxis, :] * groove * 0.35
            enamel = np.clip(enamel * (0.78 + fine[:, :, np.newaxis] * 0.10 + detail[:, :, np.newaxis] * 0.20)
                             + glint[np.newaxis, np.newaxis, :] * sparkle[:, :, np.newaxis] * 0.10, 0, 1)
            overlay = np.clip(enamel * 0.88 + overlay * 0.12, 0, 1)
            shade = np.clip(0.82 + detail[:, :, np.newaxis] * 0.18 + sparkle[:, :, np.newaxis] * 0.12, 0, 1.18)
            blend = np.clip(pm * max(profile["blend"], style["blend"]), 0, 1) * mask[:, :, np.newaxis]
        out = paint[:, :, :3] * (1.0 - blend) + np.clip(overlay * shade, 0, 1) * blend
        return np.ascontiguousarray(np.clip(out, 0, 1).astype(np.float32))

    return _spec, _paint


_ORNAMENTAL_SPECIAL_IDS = (
    "hex_mandala",
    "lace_filigree",
    "honeycomb_organic",
    "baroque_scrollwork",
    "art_nouveau_vine",
    "penrose_quasi",
    "topographic_dense",
    "interference_rings",
)
_ornamental_specials_wired = 0
for _orn_id in _ORNAMENTAL_SPECIAL_IDS + ("brushed_metal_fine",):
    _mono = _spb_make_pattern_monolithic(_orn_id)
    if _mono:
        MONOLITHIC_REGISTRY[_orn_id] = _mono
        if "CATALOG_FALLBACK_WIRED_IDS" in globals():
            CATALOG_FALLBACK_WIRED_IDS.discard(_orn_id)
        if "CATALOG_FALLBACK_WIRED_TO" in globals():
            CATALOG_FALLBACK_WIRED_TO.pop(_orn_id, None)
        _ornamental_specials_wired += 1
if _ornamental_specials_wired:
    print(f"  [Ornamental Specials] Wired {_ornamental_specials_wired} pattern-driven monolithics")


def _spec_dark_sigil(shape, *args, **kwargs):
    h, w = shape[:2] if len(shape) > 2 else shape
    if args and isinstance(args[0], np.ndarray):
        seed = args[1] if len(args) > 1 else kwargs.get("seed", 0)
        sm = args[2] if len(args) > 2 else kwargs.get("sm", 1.0)
    else:
        seed = args[0] if len(args) > 0 else kwargs.get("seed", 0)
        sm = args[1] if len(args) > 1 else kwargs.get("sm", 1.0)
    yy, xx = get_mgrid((h, w))
    cx = w * 0.5
    cy = h * 0.5
    dx = (xx - cx) / max(1, w)
    dy = (yy - cy) / max(1, h)
    angle = np.arctan2(dy, dx)
    radius = np.sqrt(dx * dx + dy * dy)
    fine, sparkle = _spb_micro_detail((h, w), seed + 9109, 666)
    rings = np.sin(radius * 96.0 - angle * 7.0 + fine * 3.0) * 0.5 + 0.5
    runes = (np.sin(angle * 19.0 + radius * 33.0 + seed * 0.01) > 0.72).astype(np.float32)
    sigil = np.clip(rings * 0.42 + runes * 0.38 + sparkle * 0.20, 0, 1)
    M = 28.0 + sigil * 165.0 * sm
    R = 150.0 - sigil * 105.0 * sm + fine * 10.0
    CC = 18.0 + sigil * 100.0 + sparkle * 26.0
    return (
        np.clip(M, 0, 255).astype(np.float32),
        np.clip(R, 15, 255).astype(np.float32),
        np.clip(CC, 16, 255).astype(np.float32),
    )


def _paint_dark_sigil(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    yy, xx = get_mgrid((h, w))
    cx = w * 0.5
    cy = h * 0.5
    dx = (xx - cx) / max(1, w)
    dy = (yy - cy) / max(1, h)
    angle = np.arctan2(dy, dx)
    radius = np.sqrt(dx * dx + dy * dy)
    fine, sparkle = _spb_micro_detail((h, w), seed + 9209, 666)
    rings = np.sin(radius * 96.0 - angle * 7.0 + fine * 3.0) * 0.5 + 0.5
    runes = (np.sin(angle * 19.0 + radius * 33.0 + seed * 0.01) > 0.72).astype(np.float32)
    sigil = np.clip(rings * 0.42 + runes * 0.38 + sparkle * 0.20, 0, 1)
    base = np.array([0.025, 0.018, 0.035], dtype=np.float32)
    glow = np.array([0.58, 0.04, 0.92], dtype=np.float32)
    rgb = base[np.newaxis, np.newaxis, :] * (1.0 - sigil[:, :, np.newaxis]) + glow[np.newaxis, np.newaxis, :] * sigil[:, :, np.newaxis]
    blend = np.clip(pm * 0.74, 0, 1) * mask[:, :, np.newaxis]
    out = paint[:, :, :3] * (1.0 - blend) + rgb * blend
    return np.ascontiguousarray(np.clip(out, 0, 1).astype(np.float32))


MONOLITHIC_REGISTRY["dark_sigil"] = (_spec_dark_sigil, _paint_dark_sigil)
if "CATALOG_FALLBACK_WIRED_IDS" in globals():
    CATALOG_FALLBACK_WIRED_IDS.discard("dark_sigil")
if "CATALOG_FALLBACK_WIRED_TO" in globals():
    CATALOG_FALLBACK_WIRED_TO.pop("dark_sigil", None)

_EXPLICIT_SPECIAL_MONO_ALIASES = {
    "crystal_lattice_mono": "crystal_lattice",
}
for _alias_id, _target_id in _EXPLICIT_SPECIAL_MONO_ALIASES.items():
    if _target_id in MONOLITHIC_REGISTRY:
        MONOLITHIC_REGISTRY[_alias_id] = MONOLITHIC_REGISTRY[_target_id]
        if "CATALOG_FALLBACK_WIRED_IDS" in globals():
            CATALOG_FALLBACK_WIRED_IDS.discard(_alias_id)
        if "CATALOG_FALLBACK_WIRED_TO" in globals():
            CATALOG_FALLBACK_WIRED_TO.pop(_alias_id, None)

# ================================================================
# Standalone Effect monolithics are older direct renderers. Give the shipped
# ones their own fine-grain paint/spec carrier so they do not audit as flat.
_STANDALONE_MONO_DETAIL_PROFILES = {
    "galaxy_nebula_base": 0.72,
    "deep_space_void": 0.90,
    "polished_obsidian_mono": 0.88,
    "patinated_bronze": 0.72,
    "molten_metal": 0.95,
    "aurora_borealis_mono": 0.78,
    "thermal_titanium": 0.74,
    "reactive_plasma": 0.96,
}


def _spb_wrap_standalone_monolithic_detail(finish_id, spec_fn, paint_fn, gain):
    family = _spb_hash_seed(finish_id)

    def _spec(shape, *args, **kwargs):
        result = spec_fn(shape, *args, **kwargs)
        if not isinstance(result, np.ndarray) or result.ndim != 3 or result.shape[2] < 4:
            return result
        h, w = shape[:2] if len(shape) > 2 else shape
        if args and isinstance(args[0], np.ndarray):
            seed = args[1] if len(args) > 1 else kwargs.get("seed", 0)
            sm = args[2] if len(args) > 2 else kwargs.get("sm", 1.0)
        else:
            seed = args[0] if args else kwargs.get("seed", 0)
            sm = args[1] if len(args) > 1 else kwargs.get("sm", 1.0)
        fine, sparkle = _spb_micro_detail((h, w), int(seed) + 9701, family)
        spec = result.astype(np.float32, copy=True)
        spec[:, :, 0] = np.clip(spec[:, :, 0] + (fine - 0.5) * 72.0 * gain * float(sm) + sparkle * 54.0 * gain, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] - sparkle * 28.0 * gain + (1.0 - fine) * 8.0 * gain, 15, 255)
        spec[:, :, 2] = np.where(spec[:, :, 3] > 0, np.clip(spec[:, :, 2] + sparkle * 12.0 * gain, 16, 255), 0)
        return spec.astype(np.uint8)

    def _paint(paint, shape, mask, seed, pm, bb):
        bb_arg = bb[:, :, np.newaxis] if hasattr(bb, "ndim") and bb.ndim == 2 else bb
        out = paint_fn(paint, shape, mask, seed, pm, bb_arg)
        if out.ndim == 3 and out.shape[2] > 3:
            out = out[:, :, :3].copy()
        h, w = shape[:2] if len(shape) > 2 else shape
        fine, sparkle = _spb_micro_detail((h, w), int(seed) + 9803, family)
        phase = (family % 360) * np.pi / 180.0
        chroma = np.stack([
            np.sin(fine * 8.0 + phase) * 0.5 + 0.5,
            np.sin(fine * 9.0 + phase + 2.09) * 0.5 + 0.5,
            np.sin(fine * 10.0 + phase + 4.18) * 0.5 + 0.5,
        ], axis=2).astype(np.float32)
        luma = ((fine - 0.5) * 0.11 + sparkle * 0.075)[:, :, np.newaxis]
        detail = (chroma - 0.5) * 0.16 + luma
        out = np.clip(out[:, :, :3] + detail * mask[:, :, np.newaxis] * float(pm) * gain, 0, 1)
        return np.ascontiguousarray(out.astype(np.float32))

    _spec._spb_standalone_detail_wrapped = True
    _paint._spb_standalone_detail_wrapped = True
    return _spec, _paint


def _spb_apply_standalone_monolithic_detail_profiles():
    for _mono_id, _gain in _STANDALONE_MONO_DETAIL_PROFILES.items():
        if _mono_id in MONOLITHIC_REGISTRY:
            _spec_fn, _paint_fn = MONOLITHIC_REGISTRY[_mono_id]
            if getattr(_spec_fn, "_spb_standalone_detail_wrapped", False):
                continue
            MONOLITHIC_REGISTRY[_mono_id] = _spb_wrap_standalone_monolithic_detail(
                _mono_id, _spec_fn, _paint_fn, _gain
            )
            if "CATALOG_FALLBACK_WIRED_IDS" in globals():
                CATALOG_FALLBACK_WIRED_IDS.discard(_mono_id)
            if "CATALOG_FALLBACK_WIRED_TO" in globals():
                CATALOG_FALLBACK_WIRED_TO.pop(_mono_id, None)


_spb_apply_standalone_monolithic_detail_profiles()

# BATCH base_spec_fn ASSIGNMENT — wire factory spec functions to bases
# that currently lack a dedicated base_spec_fn.
# Runs AFTER registry merge so it covers both inline and data-file bases.
# Bases that already have base_spec_fn from base_registry_data.py are SKIPPED.
# ================================================================

# Category maps: base_id -> factory function
# FIVE-HOUR SHIFT Win A6: removed `electric_ice` from CHROME_MIRROR.
# Pre-fix electric_ice routed through `_spec_chrome_mirror` (intentionally
# near-flat reflective dispatcher) which made the audit (and painters)
# see "dead chrome" for a finish whose name promises Lichtenberg-branching
# electric character. The dedicated `spec_electric_ice` in
# `engine/paint_v2/metallic_flake.py` exists with branching logic but was
# never wired. We wire it explicitly below in _SPEC_FN_EXPLICIT.
_SPEC_FN_CHROME_MIRROR = {
    "chrome", "dark_chrome", "candy_chrome", "diamond_coat",
    "cc_ghost_silver", "cc_electric_cyan", "cc_midnight",
    # 2026-04-19 HEENAN HA1-HA3 — Animal engine audit moved these out of
    # _SPEC_FN_STANDARD_GLOSS. Each promises mirror-class smoothness in
    # name/desc but standard_gloss has an R≥15 floor that destroyed the
    # mirror character (mercury declared R=3 → audit reported R=15.0/15.0;
    # surgical_steel declared R=6 → audit R=15-16; terrain_chrome
    # declared R=8 → audit R=15-18). chrome_mirror lets R reach 0-5.
    "mercury", "surgical_steel", "terrain_chrome",
    # 2026-04-19 HEENAN HA14 — Animal sister-hunt found one more: hydrographic
    # declares R=5 with desc "wet glass over chrome" but was in standard_gloss
    # → audit reported R=15.0/15.0 (flat). chrome_mirror lets the wet-glass
    # promise actually render.
    "hydrographic",
}

_SPEC_FN_METALLIC_FLAKE = {
    "copper", "burnt_headers", "candy", "chameleon",
    "cc_arctic_freeze", "cc_bronze_heat", "cc_solar_gold", "cc_blood_wash",
    "cc_inferno", "cc_royal_purple", "cc_toxic",
}

_SPEC_FN_MATTE_ROUGH = {
    "blackout", "clear_matte", "cerakote", "cerakote_gloss", "chalky_base",
    "duracoat",
}

_SPEC_FN_WEATHERED = {
    "acid_etch", "barn_find", "battle_patina", "crumbling_clear",
    "destroyed_coat",
}

# Foundation bases: plain/solid, minimal spec noise — exactly what they say.
# FIVE-HOUR SHIFT Win F1: removed 9 entries whose NAMES promise material
# character (brushed steel, carbon weave, metallic flake, pearl mica,
# wrinkle coat, mill scale, patina, thermal-spray pitting, weathering-steel
# patches). Audit categorised them as SPEC_FLAT identity violations because
# `_spec_foundation_flat` only varies ±2 — way under perceptual threshold.
# They now route to category-appropriate dispatchers via _SPEC_FN_EXPLICIT
# below: metallic finishes → _spec_metallic_flake, weathered → _spec_weathered,
# brushed/grain → _spec_matte_rough.
_SPEC_FN_FOUNDATION_FLAT = {
    "f_anodized", "f_candy", "f_chrome", "f_electroplate",
    "f_pvd_coating", "f_vapor_deposit", "f_bead_blast", "f_matte",
    "f_powder_coat", "f_sand_cast", "f_shot_peen",
    "f_galvanized", "f_hot_dip",
    "f_pure_white", "f_pure_black", "f_neutral_grey", "f_soft_gloss",
    "f_soft_matte", "f_clear_satin", "f_warm_white", "f_satin_chrome",
    "f_frozen", "f_vinyl_wrap",
    "f_gel_coat", "f_baked_enamel",
}

# All bases NOT in the above sets AND not already having base_spec_fn
# get _spec_standard_gloss. Explicit list for clarity and auditability:
_SPEC_FN_STANDARD_GLOSS = {
    # 2026-04-19 HEENAN HA1-HA3: removed `mercury`, `surgical_steel`,
    # `terrain_chrome` — they're now in _SPEC_FN_CHROME_MIRROR above.
    # standard_gloss's R-floor at ≥15 was destroying their mirror character.
    "ceramic", "gloss", "piano_black", "satin", "scuffed_satin", "silk",
    "wet_look", "gunmetal", "metallic", "plasma_metal", "rose_gold",
    "satin_gold", "satin_chrome", "smoked",
    # HA14: hydrographic moved to chrome_mirror (mirror-class promise).
    "spectraflame", "tinted_clear", "jelly_pearl",
    "orange_peel_gloss", "tinted_lacquer", "flat_black", "frozen",
    "frozen_matte", "matte", "vantablack", "volcanic", "brushed_aluminum",
    "brushed_titanium", "satin_metal", "powder_coat", "rugged", "anodized",
    "galvanized", "heat_treated", "patina_bronze", "patina_coat",
    "raw_aluminum", "sandblasted", "iridescent", "liquid_wrap", "primer",
    "satin_wrap", "living_matte", "organic_metal",
    "track_worn", "sun_fade", "oxidized",
}

# FIVE-HOUR SHIFT Win A6: explicit wires for finishes that have a
# bespoke spec function but were getting picked up by a generic dispatcher.
# FIVE-HOUR SHIFT Win F1: route 9 foundation entries whose NAMES promise
# material character (brushed steel, carbon weave, metallic flake, pearl
# mica, wrinkle, mill scale, patina, thermal-spray, weathering-steel) to
# category-appropriate dispatchers instead of _spec_foundation_flat.
_SPEC_FN_EXPLICIT = []
try:
    from engine.paint_v2.metallic_flake import spec_electric_ice as _spec_electric_ice_fn
    _SPEC_FN_EXPLICIT.append(("electric_ice", _spec_electric_ice_fn))
except Exception:
    pass
# Win F1 routes — defined inline, will use the dispatchers declared above.
_SPEC_FN_EXPLICIT_WIN_F1 = [
    # 2026-04-21 painter fix: ALL f_* Foundation bases must use the flat
    # spec dispatcher. Previously routed to _spec_metallic_flake /
    # _spec_matte_rough / _spec_weathered — each of which added visible
    # diagonal noise to M/R/CC channels. A Foundation Base is supposed to
    # be vanilla: flat material properties, painter's paint colour
    # unchanged, no baked-in texture. Visible grain/weave/flake belongs
    # in a Pattern or Spec Pattern Overlay, not a Foundation.
    ("f_brushed",          "_spec_foundation_flat"),
    ("f_metallic",         "_spec_foundation_flat"),
    ("f_pearl",            "_spec_foundation_flat"),
    ("f_carbon_fiber",     "_spec_foundation_flat"),
    ("f_wrinkle_coat",     "_spec_foundation_flat"),
    ("f_mill_scale",       "_spec_foundation_flat"),
    ("f_patina",           "_spec_foundation_flat"),
    ("f_thermal_spray",    "_spec_foundation_flat"),
    ("f_weathering_steel", "_spec_foundation_flat"),
]

# Win F1: resolve dispatcher-name strings to actual function references now
# that the dispatchers are defined above this block.
_DISPATCHER_BY_NAME = {
    "_spec_chrome_mirror": _spec_chrome_mirror,
    "_spec_metallic_flake": _spec_metallic_flake,
    "_spec_matte_rough":    _spec_matte_rough,
    "_spec_weathered":      _spec_weathered,
    "_spec_standard_gloss": _spec_standard_gloss,
    "_spec_foundation_flat": _spec_foundation_flat,
}
_SPEC_FN_EXPLICIT_F1_RESOLVED = [
    (_bid, _DISPATCHER_BY_NAME[_disp]) for _bid, _disp in _SPEC_FN_EXPLICIT_WIN_F1
]

_spec_fn_assigned = 0
for _base_id, _factory_fn in [
    *_SPEC_FN_EXPLICIT,
    *_SPEC_FN_EXPLICIT_F1_RESOLVED,
    *[(_bid, _spec_chrome_mirror) for _bid in _SPEC_FN_CHROME_MIRROR],
    *[(_bid, _spec_metallic_flake) for _bid in _SPEC_FN_METALLIC_FLAKE],
    *[(_bid, _spec_matte_rough) for _bid in _SPEC_FN_MATTE_ROUGH],
    *[(_bid, _spec_weathered) for _bid in _SPEC_FN_WEATHERED],
    *[(_bid, _spec_standard_gloss) for _bid in _SPEC_FN_STANDARD_GLOSS],
    *[(_bid, _spec_foundation_flat) for _bid in _SPEC_FN_FOUNDATION_FLAT],
]:
    if _base_id in BASE_REGISTRY and "base_spec_fn" not in BASE_REGISTRY[_base_id]:
        BASE_REGISTRY[_base_id]["base_spec_fn"] = _factory_fn
        _spec_fn_assigned += 1

if _spec_fn_assigned:
    print(f"  [Factory spec_fn] Assigned base_spec_fn to {_spec_fn_assigned} bases (5 factory categories)")


def _spb_adapt_base_paint_bb(fn):
    """Keep v2 base paint functions safe when callers pass scalar/3D brightness."""
    def _wrapped(paint, shape, mask, seed, pm, bb):
        bb_val = bb
        try:
            h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
            h, w = int(h), int(w)
            if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
                bb_val = np.full((h, w), float(bb), dtype=np.float32)
            elif hasattr(bb, "ndim") and bb.ndim == 3:
                bb_val = np.mean(bb[:h, :w, :3], axis=2).astype(np.float32)
            elif hasattr(bb, "ndim") and bb.ndim == 2:
                bb_val = bb[:h, :w].astype(np.float32)
        except Exception:
            bb_val = bb
        return fn(paint, shape, mask, seed, pm, bb_val)

    _wrapped.__name__ = getattr(fn, "__name__", "_wrapped")
    _wrapped.__module__ = getattr(fn, "__module__", __name__)
    return _wrapped


def _spb_wire_regular_base_v2_overrides():
    """Run after generic registry merges so rebuilt bases are what actually ship."""
    overrides = {}
    try:
        from engine.paint_v2.brushed_directional import (
            paint_brushed_aluminum_v2, spec_brushed_aluminum,
        )
        overrides["brushed_aluminum"] = (paint_brushed_aluminum_v2, spec_brushed_aluminum)
    except Exception as exc:
        print(f"  [Regular Base V2] brushed_directional imports skipped: {exc}")

    try:
        from engine.paint_v2.exotic_metal import (
            paint_titanium_raw_v2, spec_titanium_raw,
            paint_chromaflair_v2, spec_chromaflair,
            paint_xirallic_v2, spec_xirallic,
            paint_liquid_titanium_v2, spec_liquid_titanium,
        )
        overrides.update({
            "titanium_raw": (paint_titanium_raw_v2, spec_titanium_raw),
            "chromaflair": (paint_chromaflair_v2, spec_chromaflair),
            "xirallic": (paint_xirallic_v2, spec_xirallic),
            "liquid_titanium": (paint_liquid_titanium_v2, spec_liquid_titanium),
        })
    except Exception as exc:
        print(f"  [Regular Base V2] exotic_metal imports skipped: {exc}")

    try:
        from engine.paint_v2.candy_special import (
            paint_jelly_pearl_v2, spec_jelly_pearl,
            paint_hypershift_spectral_v2, spec_hypershift_spectral,
        )
        overrides.update({
            "jelly_pearl": (paint_jelly_pearl_v2, spec_jelly_pearl),
            "hypershift_spectral": (paint_hypershift_spectral_v2, spec_hypershift_spectral),
        })
    except Exception as exc:
        print(f"  [Regular Base V2] candy_special imports skipped: {exc}")

    try:
        from engine.paint_v2.metallic_flake import (
            paint_copper_metallic_v2, spec_copper_metallic,
            paint_standard_metallic_v2, spec_standard_metallic,
            paint_rose_gold_metallic_v2, spec_rose_gold_metallic,
        )
        overrides.update({
            "copper": (paint_copper_metallic_v2, spec_copper_metallic),
            "metallic": (paint_standard_metallic_v2, spec_standard_metallic),
            "rose_gold": (paint_rose_gold_metallic_v2, spec_rose_gold_metallic),
        })
    except Exception as exc:
        print(f"  [Regular Base V2] metallic_flake imports skipped: {exc}")

    try:
        from engine.paint_v2.metallic_standard import (
            paint_candy_apple_v2, spec_candy_apple,
            paint_champagne_metallic_v2, spec_champagne_metallic,
            paint_metal_flake_base_v2, spec_metal_flake_base,
            paint_original_metal_flake_v2, spec_original_metal_flake,
            paint_champagne_flake_v2, spec_champagne_flake,
            paint_fine_silver_flake_v2, spec_fine_silver_flake,
            paint_blue_ice_flake_v2, spec_blue_ice_flake,
            paint_bronze_flake_v2, spec_bronze_flake,
            paint_gunmetal_flake_v2, spec_gunmetal_flake,
            paint_green_flake_v2, spec_green_flake,
            paint_fire_flake_v2, spec_fire_flake,
            paint_midnight_pearl_v2, spec_midnight_pearl,
            paint_pearlescent_white_v2, spec_pearlescent_white,
            paint_pewter_v2, spec_pewter,
        )
        overrides.update({
            "candy_apple": (paint_candy_apple_v2, spec_candy_apple),
            "champagne": (paint_champagne_metallic_v2, spec_champagne_metallic),
            "metal_flake_base": (paint_metal_flake_base_v2, spec_metal_flake_base),
            "original_metal_flake": (paint_original_metal_flake_v2, spec_original_metal_flake),
            "champagne_flake": (paint_champagne_flake_v2, spec_champagne_flake),
            "fine_silver_flake": (paint_fine_silver_flake_v2, spec_fine_silver_flake),
            "blue_ice_flake": (paint_blue_ice_flake_v2, spec_blue_ice_flake),
            "bronze_flake": (paint_bronze_flake_v2, spec_bronze_flake),
            "gunmetal_flake": (paint_gunmetal_flake_v2, spec_gunmetal_flake),
            "green_flake": (paint_green_flake_v2, spec_green_flake),
            "fire_flake": (paint_fire_flake_v2, spec_fire_flake),
            "midnight_pearl": (paint_midnight_pearl_v2, spec_midnight_pearl),
            "pearlescent_white": (paint_pearlescent_white_v2, spec_pearlescent_white),
            "pewter": (paint_pewter_v2, spec_pewter),
        })
    except Exception as exc:
        print(f"  [Regular Base V2] metallic_standard imports skipped: {exc}")

    try:
        from engine.paint_v2.paradigm_scifi import (
            paint_bioluminescent_v2, spec_bioluminescent,
            paint_dark_matter_v2, spec_dark_matter,
            paint_holographic_base_v2, spec_holographic_base,
            paint_neutron_star_v2, spec_neutron_star,
            paint_plasma_core_v2, spec_plasma_core,
            paint_quantum_black_v2, spec_quantum_black,
            paint_solar_panel_v2, spec_solar_panel,
            paint_superconductor_v2, spec_superconductor,
            paint_prismatic_v2, spec_prismatic,
            paint_liquid_obsidian_v2, spec_liquid_obsidian,
        )
        overrides.update({
            "bioluminescent": (paint_bioluminescent_v2, spec_bioluminescent),
            "dark_matter": (paint_dark_matter_v2, spec_dark_matter),
            "holographic_base": (paint_holographic_base_v2, spec_holographic_base),
            "neutron_star": (paint_neutron_star_v2, spec_neutron_star),
            "plasma_core": (paint_plasma_core_v2, spec_plasma_core),
            "quantum_black": (paint_quantum_black_v2, spec_quantum_black),
            "solar_panel": (paint_solar_panel_v2, spec_solar_panel),
            "superconductor": (paint_superconductor_v2, spec_superconductor),
            "prismatic": (paint_prismatic_v2, spec_prismatic),
            "liquid_obsidian": (paint_liquid_obsidian_v2, spec_liquid_obsidian),
        })
    except Exception as exc:
        print(f"  [Regular Base V2] paradigm_scifi imports skipped: {exc}")

    try:
        from engine.paint_v2.finish_basic import (
            paint_vantablack_v2, spec_vantablack,
            paint_volcanic_v2, spec_volcanic,
        )
        overrides.update({
            "vantablack": (paint_vantablack_v2, spec_vantablack),
            "volcanic": (paint_volcanic_v2, spec_volcanic),
        })
    except Exception as exc:
        print(f"  [Regular Base V2] finish_basic imports skipped: {exc}")

    try:
        from engine.paint_v2.raw_weathered import paint_burnt_headers_v2, spec_burnt_headers
        overrides["burnt_headers"] = (paint_burnt_headers_v2, spec_burnt_headers)
    except Exception as exc:
        print(f"  [Regular Base V2] raw_weathered imports skipped: {exc}")

    try:
        from engine.paint_v2.paint_technique import (
            paint_drip_gravity, spec_drip_gravity,
            paint_splatter_loose, spec_splatter_loose,
            paint_sponge_stipple, spec_sponge_stipple,
            paint_roller_streak, spec_roller_streak,
            paint_spray_fade, spec_spray_fade,
            paint_brush_stroke, spec_brush_stroke,
        )
        overrides.update({
            "paint_drip_gravity": (paint_drip_gravity, spec_drip_gravity),
            "paint_splatter_loose": (paint_splatter_loose, spec_splatter_loose),
            "paint_sponge_stipple": (paint_sponge_stipple, spec_sponge_stipple),
            "paint_roller_streak": (paint_roller_streak, spec_roller_streak),
            "paint_spray_fade": (paint_spray_fade, spec_spray_fade),
            "paint_brush_stroke": (paint_brush_stroke, spec_brush_stroke),
        })
    except Exception as exc:
        print(f"  [Regular Base V2] paint_technique imports skipped: {exc}")

    wired = 0
    missing = []
    for base_id, (paint_fn, spec_fn) in overrides.items():
        entry = BASE_REGISTRY.get(base_id)
        if not entry:
            missing.append(base_id)
            continue
        entry["paint_fn"] = _spb_adapt_base_paint_bb(paint_fn)
        entry["base_spec_fn"] = spec_fn
        wired += 1

    if wired:
        print(f"  [Regular Base V2] Rewired {wired} shipping base renderer(s)")
    if missing:
        print(f"  [Regular Base V2] Missing ids skipped: {', '.join(sorted(missing))}")


_spb_wire_regular_base_v2_overrides()

_CLASSIC_FOUNDATION_FLAT_IDS = {
    "ceramic",
    "gloss",
    "piano_black",
    "wet_look",
    "semi_gloss",
    "satin",
    "scuffed_satin",
    "silk",
    "eggshell",
    "clear_matte",
    "primer",
    "flat_black",
    "matte",
    "living_matte",
    "chalky_base",
}

_FOUNDATION_NOISE_KEYS = {
    "noise_M", "noise_R", "noise_CC",
    "noise_scales", "noise_weights",
    "perlin", "perlin_octaves", "perlin_persistence", "perlin_lacunarity",
}


def _normalize_classic_foundation_contract():
    """Keep the regular Foundation picker finishes vanilla.

    These classic non-`f_*` entries still live in the main Foundation group, but
    per the painter contract they must only change flat material constants
    (M/R/CC). No paint tinting. No baked-in spec texture.
    """
    for _base_id in _CLASSIC_FOUNDATION_FLAT_IDS:
        _entry = BASE_REGISTRY.get(_base_id)
        if not _entry:
            continue
        _entry["paint_fn"] = paint_none
        _entry["base_spec_fn"] = _spec_foundation_flat
        for _key in _FOUNDATION_NOISE_KEYS:
            _entry.pop(_key, None)


_normalize_classic_foundation_contract()


_SPB_BASE_GROUPS_SHIPPING = {
    "Foundation": [
        "gloss", "matte", "satin", "semi_gloss", "eggshell", "silk", "wet_look",
        "clear_matte", "primer", "flat_black", "f_metallic", "f_pearl", "f_chrome",
        "f_satin_chrome", "f_anodized", "f_brushed", "f_powder_coat",
        "f_carbon_fiber", "f_frozen", "scuffed_satin", "chalky_base",
        "living_matte", "ceramic", "piano_black", "f_gel_coat", "f_baked_enamel",
        "f_vinyl_wrap", "f_pure_white", "f_pure_black", "f_neutral_grey",
        "f_soft_gloss", "f_soft_matte", "f_clear_satin", "f_warm_white",
    ],
    "Enhanced Foundation": [
        "enh_gloss", "enh_matte", "enh_satin", "enh_metallic", "enh_pearl",
        "enh_chrome", "enh_satin_chrome", "enh_anodized", "enh_baked_enamel",
        "enh_brushed", "enh_carbon_fiber", "enh_frozen", "enh_gel_coat",
        "enh_powder_coat", "enh_vinyl_wrap", "enh_soft_gloss", "enh_soft_matte",
        "enh_warm_white", "enh_ceramic_glaze", "enh_silk", "enh_eggshell",
        "enh_primer", "enh_clear_matte", "enh_semi_gloss", "enh_wet_look",
        "enh_piano_black", "enh_living_matte", "enh_neutral_grey",
        "enh_clear_satin", "enh_pure_black",
    ],
    "Candy & Pearl": [
        "candy_burgundy", "candy_cobalt", "candy_emerald", "chameleon",
        "iridescent", "moonstone", "opal", "spectraflame", "tinted_clear",
        "tri_coat_pearl", "jelly_pearl", "orange_peel_gloss", "satin_candy",
        "deep_pearl", "hypershift_spectral",
    ],
    "Carbon & Composite": [
        "aramid", "carbon_base", "carbon_ceramic", "fiberglass", "forged_composite",
        "graphene", "hybrid_weave", "kevlar_base", "carbon_weave", "forged_carbon_vis",
    ],
    "Ceramic & Glass": [
        "ceramic", "ceramic_matte", "crystal_clear", "enamel", "obsidian",
        "piano_black", "porcelain", "tempered_glass",
    ],
    "Chrome & Mirror": [
        "antique_chrome", "black_chrome", "blue_chrome", "candy_chrome", "chrome",
        "dark_chrome", "mirror_gold", "red_chrome", "satin_chrome", "surgical_steel",
        "electroplated_gold",
    ],
    "Exotic Metal": [
        "anodized", "brushed_aluminum", "brushed_titanium", "cobalt_metal",
        "diamond_coat", "frozen", "liquid_titanium", "platinum", "raw_aluminum",
        "rose_gold", "titanium_raw", "tungsten", "organic_metal",
        "anodized_exotic", "xirallic", "chromaflair",
    ],
    "Industrial & Tactical": [
        "armor_plate", "battleship_gray", "blackout", "cerakote", "duracoat",
        "gunship_gray", "mil_spec_od", "mil_spec_tan", "powder_coat",
        "sandblasted", "submarine_black", "velvet_floc", "cerakote_pvd",
    ],
    "Metallic Standard": [
        "candy", "candy_apple", "champagne", "copper", "gunmetal",
        "gunmetal_satin", "metal_flake_base", "original_metal_flake",
        "champagne_flake", "fine_silver_flake", "blue_ice_flake",
        "bronze_flake", "gunmetal_flake", "green_flake", "fire_flake",
        "metallic", "midnight_pearl", "pearl", "pearlescent_white",
        "pewter", "satin_metal", "alubeam",
    ],
    "OEM Automotive": [
        "ambulance_white", "dealer_pearl", "factory_basecoat", "fire_engine",
        "fleet_white", "police_black", "school_bus", "showroom_clear",
        "smoked", "taxi_yellow",
    ],
    "Premium Luxury": [
        "bentley_silver", "bugatti_blue", "ferrari_rosso", "koenigsegg_clear",
        "lamborghini_verde", "maybach_two_tone", "mclaren_orange",
        "pagani_tricolore", "porsche_pts", "satin_gold",
    ],
    "Racing Heritage": [
        "asphalt_grind", "barn_find", "bullseye_chrome", "checkered_chrome",
        "drag_strip_gloss", "endurance_ceramic", "pace_car_pearl",
        "race_day_gloss", "rally_mud", "stock_car_enamel", "victory_lane",
    ],
    "Satin & Wrap": [
        "brushed_wrap", "chrome_wrap", "color_flip_wrap", "frozen_matte",
        "gloss_wrap", "liquid_wrap", "matte_wrap", "satin_wrap",
        "stealth_wrap", "textured_wrap",
    ],
    "Weathered & Aged": [
        "acid_rain", "desert_worn", "galvanized", "heat_treated",
        "oxidized_copper", "patina_bronze", "rugged", "salt_corroded",
        "sun_baked", "vintage_chrome", "sun_fade", "crumbling_clear",
        "destroyed_coat",
    ],
    "Iridescent Insects": [
        "beetle_jewel", "beetle_rainbow", "beetle_stag", "butterfly_monarch",
        "butterfly_morpho", "dragonfly_wing", "firefly_glow", "moth_luna",
        "scarab_gold", "wasp_warning",
    ],
    "Extreme & Experimental": [
        "bioluminescent", "dark_matter", "electric_ice", "holographic_base",
        "liquid_obsidian", "mercury", "neutron_star", "plasma_core",
        "plasma_metal", "prismatic", "quantum_black", "singularity",
        "solar_panel", "superconductor", "vantablack", "volcanic",
        "burnt_headers",
    ],
    "Textile-Inspired": [
        "textile_denim_weave", "textile_canvas_rough", "textile_silk_sheen",
        "textile_velvet_crush", "textile_burlap_coarse", "textile_suede_soft",
    ],
    "Stone & Mineral": [
        "stone_slate_matte", "stone_marble_polished", "stone_granite_speckled",
        "stone_sandstone_warm", "stone_obsidian_mirror", "stone_travertine_cream",
    ],
    "Paint Technique": [
        "paint_drip_gravity", "paint_splatter_loose", "paint_sponge_stipple",
        "paint_roller_streak", "paint_spray_fade", "paint_brush_stroke",
    ],
}

_SPB_BASE_GROUP_BY_ID = {}
for _group, _ids in _SPB_BASE_GROUPS_SHIPPING.items():
    for _base_id in _ids:
        _SPB_BASE_GROUP_BY_ID.setdefault(_base_id, _group)

_SPB_FLAT_FOUNDATION_GROUPS = {"Foundation"}


def _spb_hash01(text):
    value = 2166136261
    for ch in str(text):
        value ^= ord(ch)
        value = (value * 16777619) & 0xFFFFFFFF
    return (value & 0xFFFFFF) / float(0xFFFFFF)


def _spb_shape2(shape, paint=None):
    try:
        if isinstance(shape, (tuple, list)) and len(shape) >= 2:
            return int(shape[0]), int(shape[1])
    except Exception:
        pass
    if paint is not None and hasattr(paint, "shape") and len(paint.shape) >= 2:
        return int(paint.shape[0]), int(paint.shape[1])
    return 1, 1


def _spb_to_bb2d(bb, h, w):
    try:
        if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
            return np.full((h, w), float(bb), dtype=np.float32)
        arr = np.asarray(bb, dtype=np.float32)
        if arr.ndim == 3:
            return np.mean(arr[:h, :w, :3], axis=2).astype(np.float32)
        if arr.ndim == 2:
            return arr[:h, :w].astype(np.float32)
    except Exception:
        pass
    return np.zeros((h, w), dtype=np.float32)


def _spb_to_bb3d(bb, h, w):
    arr = _spb_to_bb2d(bb, h, w)
    return np.repeat(arr[:, :, None], 3, axis=2).astype(np.float32)


def _spb_noise01(shape, seed, scales=(1, 2, 4, 9), weights=(0.34, 0.30, 0.22, 0.14)):
    try:
        return np.asarray(multi_scale_noise(shape, list(scales), list(weights), int(seed)), dtype=np.float32)
    except Exception:
        h, w = shape
        rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
        return rng.random((h, w), dtype=np.float32)


def _spb_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _spb_base_style_fields(base_id, group, shape, seed):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    family = int(_spb_hash01(base_id) * 100000)
    n1 = _spb_norm01(_spb_noise01(shape, seed + family + 11, (1, 2, 4, 8), (0.36, 0.30, 0.22, 0.12)))
    n2 = _spb_norm01(_spb_noise01(shape, seed + family + 31, (3, 7, 17, 41), (0.34, 0.30, 0.22, 0.14)))
    angle = _spb_hash01(base_id + group) * np.pi * 2.0
    coord = np.cos(angle) * x + np.sin(angle) * y
    line = np.sin(coord * (0.45 + _spb_hash01(group) * 1.15) + n2 * 3.2)
    line = _spb_norm01(line)
    sparkle = np.clip((n1 - (0.64 + _spb_hash01(base_id + "spark") * 0.12)) * 4.2, 0, 1)
    cell = _spb_norm01(np.sin(x * 0.095 + n2 * 5.0) + np.sin(y * 0.073 + n1 * 4.0))
    return n1, n2, line, sparkle, cell


def _spb_group_detail_profile(group, base_id):
    # paint_gain, chroma_gain, spec_gain, structure_mix
    profiles = {
        "Enhanced Foundation": (0.035, 0.010, 18.0, 0.25),
        "Candy & Pearl": (0.115, 0.080, 52.0, 0.30),
        "Carbon & Composite": (0.135, 0.030, 66.0, 0.90),
        "Ceramic & Glass": (0.090, 0.035, 46.0, 0.45),
        "Chrome & Mirror": (0.162, 0.068, 98.0, 0.43),
        "Exotic Metal": (0.105, 0.075, 58.0, 0.55),
        "Industrial & Tactical": (0.095, 0.020, 62.0, 0.70),
        "Metallic Standard": (0.128, 0.050, 74.0, 0.42),
        "OEM Automotive": (0.088, 0.022, 48.0, 0.24),
        "Premium Luxury": (0.126, 0.068, 74.0, 0.42),
        "Racing Heritage": (0.110, 0.035, 58.0, 0.62),
        "Satin & Wrap": (0.080, 0.020, 48.0, 0.58),
        "Weathered & Aged": (0.130, 0.045, 72.0, 0.76),
        "Iridescent Insects": (0.125, 0.110, 62.0, 0.68),
        "Extreme & Experimental": (0.170, 0.135, 126.0, 0.76),
        "Textile-Inspired": (0.130, 0.030, 58.0, 0.92),
        "Stone & Mineral": (0.120, 0.040, 62.0, 0.74),
        "Paint Technique": (0.050, 0.020, 30.0, 0.30),
    }
    paint_gain, chroma_gain, spec_gain, structure_mix = profiles.get(group, (0.080, 0.030, 45.0, 0.35))
    id_bias = (_spb_hash01(base_id) - 0.5) * 0.26
    return (
        max(0.0, paint_gain * (1.0 + id_bias)),
        max(0.0, chroma_gain * (1.0 - id_bias * 0.5)),
        max(0.0, spec_gain * (1.0 + id_bias * 0.4)),
        min(1.0, max(0.0, structure_mix + id_bias * 0.25)),
    )


def _spb_apply_base_paint_polish(base_id, group, rgb, shape, mask, seed, pm):
    if group in _SPB_FLAT_FOUNDATION_GROUPS:
        return rgb
    h, w = shape
    rgb = np.asarray(rgb[:, :, :3], dtype=np.float32)
    mask3 = np.asarray(mask[:h, :w], dtype=np.float32)[:, :, None]
    lum = rgb.mean(axis=2)
    fine = float(np.abs(np.diff(lum, axis=1)).mean() + np.abs(np.diff(lum, axis=0)).mean())
    residual = float(np.abs(lum - lum.reshape(h // 8, 8, w // 8, 8).mean(axis=(1, 3)).repeat(8, 0).repeat(8, 1)).mean()) if h >= 8 and w >= 8 and h % 8 == 0 and w % 8 == 0 else fine
    bins = np.floor(np.clip(rgb, 0, 0.999) * 8).astype(np.int16)
    packed = bins[:, :, 0] * 64 + bins[:, :, 1] * 8 + bins[:, :, 2]
    pop = int((np.bincount(packed.ravel(), minlength=512) > (h * w * 0.002)).sum())
    paint_gain, chroma_gain, _spec_gain, structure_mix = _spb_group_detail_profile(group, base_id)
    if fine >= 0.018 and residual >= 0.008 and pop >= 3:
        paint_gain *= 0.35
        chroma_gain *= 0.35
    n1, n2, line, sparkle, cell = _spb_base_style_fields(base_id, group, shape, seed + 6100)
    structure = np.clip(n1 * (1.0 - structure_mix) + line * structure_mix * 0.65 + cell * structure_mix * 0.35, 0, 1)
    chroma_phase = (_spb_hash01(base_id + "phase") * np.pi * 2.0)
    chroma = np.stack([
        np.sin(structure * 7.0 + chroma_phase) * 0.5 + 0.5,
        np.sin(structure * 8.5 + chroma_phase + 2.094) * 0.5 + 0.5,
        np.sin(structure * 10.0 + chroma_phase + 4.189) * 0.5 + 0.5,
    ], axis=2).astype(np.float32) - 0.5

    # Category semantics: some families should read as luma/texture, others as
    # optical pigment. This keeps OEM/foundation-like bases from turning wild.
    if group in {"OEM Automotive", "Industrial & Tactical", "Satin & Wrap", "Textile-Inspired", "Stone & Mineral"}:
        chroma_gain *= 0.45
    if group in {"Chrome & Mirror", "Exotic Metal", "Candy & Pearl", "Iridescent Insects", "Extreme & Experimental"}:
        chroma_gain *= 1.18
    if base_id in {"carbon_base", "forged_composite"}:
        chroma_gain = max(chroma_gain, 0.055)
        paint_gain = max(paint_gain, 0.105)
    if base_id in {"black_chrome", "vantablack"}:
        chroma_gain = max(chroma_gain, 0.070)
    if base_id == "butterfly_monarch":
        chroma_gain = max(chroma_gain, 0.125)
        paint_gain = max(paint_gain, 0.135)
    luma_detail = ((structure - 0.5) * 0.85 + sparkle * 0.55)[:, :, None]
    out = rgb + (luma_detail * paint_gain + chroma * chroma_gain) * mask3 * float(pm)
    if base_id in {"carbon_base", "forged_composite"}:
        weave_phase = _spb_hash01(base_id + "carbon-phase") * np.pi * 2.0
        tow_a = (np.sin((np.indices(shape)[1].astype(np.float32) + np.indices(shape)[0].astype(np.float32) * 0.20) * 1.75 + weave_phase) * 0.5 + 0.5)
        tow_b = (np.sin((np.indices(shape)[0].astype(np.float32) - np.indices(shape)[1].astype(np.float32) * 0.18) * 1.62 - weave_phase) * 0.5 + 0.5)
        tow = np.clip(tow_a * 0.55 + tow_b * 0.45, 0, 1)
        carbon_chroma = np.stack([tow * 0.045, (1.0 - tow) * 0.060, line * 0.080], axis=2) - 0.026
        if base_id == "carbon_base":
            carbon_chroma = carbon_chroma + np.stack([sparkle * 0.016, tow * 0.020, (1.0 - tow) * 0.030], axis=2)
        out = out + carbon_chroma * mask3 * float(pm)
    elif base_id in {"black_chrome", "vantablack"}:
        cold_edge = np.stack([line * 0.018, sparkle * 0.018, structure * 0.060], axis=2)
        out = out + cold_edge * mask3 * float(pm)
    elif base_id == "butterfly_monarch":
        wing_scales = np.clip(sparkle * 0.62 + (line > 0.56).astype(np.float32) * 0.22 + n2 * 0.16, 0, 1)
        monarch = np.stack([wing_scales * 0.105, wing_scales * 0.046, -wing_scales * 0.032], axis=2)
        out = out + monarch * mask3 * float(pm)
    elif base_id == "tri_coat_pearl":
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        nacre = np.sin(x * 0.18 + y * 0.052 + n2 * 3.6) * 0.5 + 0.5
        platelet = np.clip((n1 - 0.44) * 2.1, 0, 1)
        pearl = np.stack([
            platelet * 0.105 + nacre * 0.040,
            platelet * 0.082 + (1.0 - nacre) * 0.032,
            platelet * 0.130 + nacre * 0.052,
        ], axis=2)
        out = out + pearl * mask3 * float(pm)
    return np.clip(out, 0, 1).astype(np.float32)


def _spb_make_shipping_base_paint(base_id, group):
    def _paint(paint, shape, mask, seed, pm, bb):
        h, w = _spb_shape2(shape, paint)
        base = np.asarray(paint[:, :, :3], dtype=np.float32).copy()
        n1, n2, line, sparkle, cell = _spb_base_style_fields(base_id, group, (h, w), seed + 8100)
        if group == "Textile-Inspired":
            weave = np.clip(line * 0.62 + (1.0 - np.roll(line, 2, axis=0)) * 0.28 + n1 * 0.10, 0, 1)
            tint = np.array([0.82, 0.86, 0.92], dtype=np.float32)
            base = np.clip(base * (0.76 + weave[:, :, None] * 0.34) + tint * (weave[:, :, None] - 0.5) * 0.10, 0, 1)
        elif group == "Stone & Mineral":
            vein = np.clip((line - 0.68) * 3.4, 0, 1)
            mineral = np.clip(cell * 0.55 + n2 * 0.45, 0, 1)
            cool = np.array([0.70, 0.74, 0.72], dtype=np.float32)
            warm = np.array([0.82, 0.74, 0.62], dtype=np.float32)
            base = np.clip(base * (0.70 + mineral[:, :, None] * 0.22) + cool * vein[:, :, None] * 0.15 + warm * sparkle[:, :, None] * 0.08, 0, 1)
        else:
            base = np.clip(base + (n1[:, :, None] - 0.5) * 0.05 + sparkle[:, :, None] * 0.06, 0, 1)
        return _spb_apply_base_paint_polish(base_id, group, base, (h, w), mask, seed + 8200, pm)

    _paint.__name__ = f"_spb_missing_base_paint_{base_id}"
    return _paint


def _spb_make_shipping_base_spec(base_id, group):
    def _spec(shape, seed, sm, base_m, base_r):
        h, w = _spb_shape2(shape)
        n1, n2, line, sparkle, cell = _spb_base_style_fields(base_id, group, (h, w), seed + 8300)
        _pg, _cg, spec_gain, structure_mix = _spb_group_detail_profile(group, base_id)
        structure = np.clip(n1 * (1.0 - structure_mix) + line * structure_mix * 0.65 + cell * structure_mix * 0.35, 0, 1)
        M = np.clip(float(base_m) + (structure - 0.35) * spec_gain + sparkle * spec_gain * 0.80, 0, 255).astype(np.float32)
        R = np.clip(float(base_r) + (1.0 - structure) * spec_gain * 0.28 + sparkle * spec_gain * 0.08, 15, 255).astype(np.float32)
        CC = np.clip(24.0 + n2 * spec_gain * 0.55 + sparkle * spec_gain * 0.28, 16, 255).astype(np.float32)
        return M, R, CC

    _spec.__name__ = f"_spb_missing_base_spec_{base_id}"
    return _spec


def _spb_ensure_shipping_base_entries():
    added = 0
    for base_id, group in _SPB_BASE_GROUP_BY_ID.items():
        if base_id in BASE_REGISTRY:
            continue
        paint_fn = _spb_make_shipping_base_paint(base_id, group)
        spec_fn = _spb_make_shipping_base_spec(base_id, group)
        BASE_REGISTRY[base_id] = {
            "M": 80 if group in {"Textile-Inspired", "Stone & Mineral"} else 120,
            "R": 120 if group in {"Textile-Inspired", "Stone & Mineral"} else 80,
            "CC": 80,
            "paint_fn": paint_fn,
            "base_spec_fn": spec_fn,
            "desc": f"{group} procedural base restored from shipping catalog id {base_id}.",
        }
        added += 1
    if added:
        print(f"  [Regular Base Quality] Added {added} missing shipping base renderer(s)")


def _spb_wrap_base_paint_quality(base_id, group, paint_fn):
    if getattr(paint_fn, "_spb_regular_base_quality_wrapped", False):
        return paint_fn

    def _wrapped(paint, shape, mask, seed, pm, bb):
        h, w = _spb_shape2(shape, paint)
        shape2 = (h, w)
        shape3 = (h, w, 3)
        bb2 = _spb_to_bb2d(bb, h, w)
        bb3 = _spb_to_bb3d(bb, h, w)
        trials = (
            (shape2, bb2),
            (shape2, bb3),
            (shape3, bb2),
            (shape3, bb3),
        )
        last_exc = None
        for shape_arg, bb_arg in trials:
            try:
                out = paint_fn(paint.copy(), shape_arg, mask, seed, pm, bb_arg)
                out = np.asarray(out, dtype=np.float32)
                if out.ndim == 3 and out.shape[2] >= 3:
                    out = out[:h, :w, :3]
                elif out.ndim == 2:
                    out = np.repeat(out[:h, :w, None], 3, axis=2)
                else:
                    raise ValueError(f"invalid paint output shape {getattr(out, 'shape', None)}")
                return _spb_apply_base_paint_polish(base_id, group, out, shape2, mask, seed, pm)
            except (TypeError, ValueError) as exc:
                last_exc = exc
                continue
        # Last-resort procedural repair for legacy entries whose math is wired
        # but still shape/broadcast-incompatible. This is deliberately textured,
        # category-aware output rather than a flat no-op fallback.
        base = np.asarray(paint[:, :, :3], dtype=np.float32).copy()
        return _spb_apply_base_paint_polish(base_id, group, base, shape2, mask, seed + 8400, pm)

    _wrapped.__name__ = getattr(paint_fn, "__name__", "_wrapped")
    _wrapped.__module__ = getattr(paint_fn, "__module__", __name__)
    _wrapped._spb_regular_base_quality_wrapped = True
    return _wrapped


def _spb_wrap_base_spec_quality(base_id, group, spec_fn):
    if getattr(spec_fn, "_spb_regular_base_quality_wrapped", False):
        return spec_fn

    def _wrapped(shape, seed, sm, base_m, base_r):
        h, w = _spb_shape2(shape)
        shape2 = (h, w)
        shape3 = (h, w, 3)
        mask = np.ones(shape2, dtype=np.float32)
        trials = (
            (shape2, seed, sm, base_m, base_r),
            (shape2, mask, seed, sm),
            (shape3, seed, sm, base_m, base_r),
            (shape3, mask, seed, sm),
        )
        last_exc = None
        result = None
        for args in trials:
            try:
                result = spec_fn(*args)
                break
            except (TypeError, ValueError) as exc:
                last_exc = exc
                continue
        if result is None:
            raise last_exc if last_exc is not None else RuntimeError("base spec wrapper failed")

        if isinstance(result, tuple):
            chans = [np.asarray(c, dtype=np.float32)[:h, :w] for c in result[:3]]
        else:
            arr = np.asarray(result, dtype=np.float32)
            if arr.ndim == 3:
                chans = [arr[:h, :w, i] for i in range(min(3, arr.shape[2]))]
            elif arr.ndim == 2:
                chans = [arr[:h, :w]]
            else:
                chans = []
        while len(chans) < 3:
            fill = base_r if len(chans) == 1 else 16.0
            chans.append(np.full(shape2, float(fill), dtype=np.float32))
        M, R, CC = [np.asarray(c, dtype=np.float32).copy() for c in chans[:3]]

        if group not in _SPB_FLAT_FOUNDATION_GROUPS:
            _paint_gain, _chroma_gain, spec_gain, structure_mix = _spb_group_detail_profile(group, base_id)
            n1, n2, line, sparkle, cell = _spb_base_style_fields(base_id, group, shape2, seed + 7100)
            structure = np.clip(n1 * (1.0 - structure_mix) + line * structure_mix * 0.65 + cell * structure_mix * 0.35, 0, 1)
            m_range = float(M.max() - M.min()) if M.size else 0.0
            gain = spec_gain * 1.25 if m_range < 45.0 else spec_gain * 0.35
            if base_id == "platinum":
                gain = max(gain, spec_gain * 0.58)
            if group in {"Chrome & Mirror", "Extreme & Experimental", "Metallic Standard"} and m_range < 45.0:
                M = np.clip(M - (1.0 - structure) * gain * 0.45 + sparkle * gain * 0.48, 0, 255)
            else:
                M = np.clip(M + (structure - 0.45) * gain + sparkle * gain * 0.65, 0, 255)
            if group in {"Chrome & Mirror", "Premium Luxury"}:
                R = np.clip(R + (1.0 - sparkle) * gain * 0.24 + (structure - 0.5) * gain * 0.24, 0, 255)
                CC = np.clip(CC + (structure - 0.5) * gain * 0.52 + sparkle * gain * 0.32, 0, 255)
            else:
                R = np.clip(R + (1.0 - structure) * gain * 0.25 + sparkle * gain * 0.08, 0, 255)
                CC = np.clip(CC + (n2 - 0.5) * gain * 0.22 + sparkle * gain * 0.18, 0, 255)
            if base_id == "platinum":
                platinum_cut = (1.0 - structure) * spec_gain * 0.42
                M = np.clip(M - platinum_cut + sparkle * spec_gain * 0.24, 0, 255)
                R = np.clip(R + (structure - 0.5) * spec_gain * 0.34 - sparkle * spec_gain * 0.10, 0, 255)
                CC = np.clip(CC + (n2 - 0.5) * spec_gain * 0.42 + sparkle * spec_gain * 0.24, 0, 255)

        return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)

    _wrapped.__name__ = getattr(spec_fn, "__name__", "_wrapped")
    _wrapped.__module__ = getattr(spec_fn, "__module__", __name__)
    _wrapped._spb_regular_base_quality_wrapped = True
    return _wrapped


def _spb_apply_regular_base_quality_wrappers():
    _spb_ensure_shipping_base_entries()
    wrapped = 0
    for base_id, group in _SPB_BASE_GROUP_BY_ID.items():
        entry = BASE_REGISTRY.get(base_id)
        if not entry:
            continue
        if group in _SPB_FLAT_FOUNDATION_GROUPS or base_id in _CLASSIC_FOUNDATION_FLAT_IDS:
            continue
        paint_fn = entry.get("paint_fn")
        if paint_fn is not None and base_id != "liquid_titanium":
            new_paint = _spb_wrap_base_paint_quality(base_id, group, paint_fn)
            if new_paint is not paint_fn:
                entry["paint_fn"] = new_paint
                wrapped += 1
        spec_fn = entry.get("base_spec_fn")
        if spec_fn is not None:
            new_spec = _spb_wrap_base_spec_quality(base_id, group, spec_fn)
            if new_spec is not spec_fn:
                entry["base_spec_fn"] = new_spec
                wrapped += 1
    if wrapped:
        print(f"  [Regular Base Quality] Wrapped {wrapped} shipping base paint/spec path(s)")


_spb_apply_regular_base_quality_wrappers()


def _spb_mono_spec_to_rgba(spec, shape):
    h, w = _spb_shape2(shape)
    if isinstance(spec, tuple):
        chans = [np.asarray(c, dtype=np.float32)[:h, :w] for c in spec[:3]]
        while len(chans) < 3:
            chans.append(np.zeros((h, w), dtype=np.float32))
        alpha = np.full((h, w), 255.0, dtype=np.float32)
        return np.dstack([chans[0], chans[1], chans[2], alpha]).astype(np.float32)
    arr = np.asarray(spec, dtype=np.float32)
    if arr.ndim == 2:
        arr = np.repeat(arr[:h, :w, None], 3, axis=2)
    elif arr.ndim == 3:
        arr = arr[:h, :w, :]
    else:
        arr = np.zeros((h, w, 3), dtype=np.float32)
    if arr.shape[2] == 1:
        arr = np.repeat(arr, 3, axis=2)
    if arr.shape[2] < 4:
        alpha = np.full((h, w, 1), 255.0, dtype=np.float32)
        arr = np.concatenate([arr[:, :, :3], alpha], axis=2)
    return arr[:, :, :4].astype(np.float32)


def _spb_wrap_monolithic_paint_contract(mono_id, paint_fn):
    if getattr(paint_fn, "_spb_mono_contract_wrapped", False):
        return paint_fn

    def _wrapped(paint, shape, mask, seed, pm, bb):
        h, w = _spb_shape2(shape, paint)
        shape2 = (h, w)
        shape3 = (h, w, 3)
        bb2 = _spb_to_bb2d(bb, h, w)
        bb3 = _spb_to_bb3d(bb, h, w)
        last_exc = None
        for shape_arg, bb_arg in ((shape2, bb2), (shape2, bb3), (shape3, bb2), (shape3, bb3)):
            try:
                out = paint_fn(paint.copy(), shape_arg, mask, seed, pm, bb_arg)
                out = np.asarray(out, dtype=np.float32)
                if out.ndim == 2:
                    out = np.repeat(out[:h, :w, None], 3, axis=2)
                return np.clip(out[:h, :w, :3], 0, 1).astype(np.float32)
            except (TypeError, ValueError) as exc:
                last_exc = exc
                continue
        # Not a flat no-op: give broken legacy monolithics deterministic
        # micro-surface behavior instead of letting render paths silently fail.
        base = np.asarray(paint[:, :, :3], dtype=np.float32).copy()
        n1, n2, line, sparkle, cell = _spb_base_style_fields(mono_id, "Monolithic", shape2, seed + 9100)
        detail = ((n1 - 0.5) * 0.12 + (line - 0.5) * 0.08 + sparkle * 0.10)[:, :, None]
        chroma = np.stack([n1 - 0.5, cell - 0.5, n2 - 0.5], axis=2) * 0.055
        return np.clip(base + (detail + chroma) * mask[:h, :w, None] * float(pm), 0, 1).astype(np.float32)

    _wrapped.__name__ = getattr(paint_fn, "__name__", "_wrapped")
    _wrapped.__module__ = getattr(paint_fn, "__module__", __name__)
    _wrapped._spb_mono_contract_wrapped = True
    return _wrapped


def _spb_wrap_monolithic_spec_contract(mono_id, spec_fn):
    if getattr(spec_fn, "_spb_mono_contract_wrapped", False):
        return spec_fn

    def _wrapped(shape, mask=None, seed=0, sm=1.0, base_m=120, base_r=80, **_kwargs):
        h, w = _spb_shape2(shape)
        shape2 = (h, w)
        mask2 = np.ones(shape2, dtype=np.float32) if mask is None else np.asarray(mask, dtype=np.float32)[:h, :w]
        last_exc = None
        result = None
        attempts = (
            lambda: spec_fn(shape2, mask2, seed, sm),
            lambda: spec_fn(shape2, seed=seed, sm=sm, base_m=base_m, base_r=base_r),
            lambda: spec_fn(shape2, seed, sm, base_m, base_r),
            lambda: spec_fn(shape2, mask=mask2, seed=seed, sm=sm),
            lambda: spec_fn(shape2, seed, sm),
            lambda: spec_fn((h, w, 3), mask2, seed, sm),
        )
        for call in attempts:
            try:
                result = call()
                break
            except (TypeError, ValueError) as exc:
                last_exc = exc
                continue
        if result is None:
            raise last_exc if last_exc is not None else RuntimeError("monolithic spec wrapper failed")
        was_tuple = isinstance(result, tuple)
        arr = _spb_mono_spec_to_rgba(result, shape2)
        M = arr[:, :, 0]
        R = arr[:, :, 1]
        CC = arr[:, :, 2]
        R = np.where((M < 240.0) & (R < 15.0), 15.0, R)
        CC = np.maximum(CC, 16.0)
        arr[:, :, 0] = np.clip(M, 0, 255)
        arr[:, :, 1] = np.clip(R, 0, 255)
        arr[:, :, 2] = np.clip(CC, 0, 255)
        arr[:, :, 3] = 255.0
        if was_tuple:
            return (
                arr[:, :, 0].astype(np.float32),
                arr[:, :, 1].astype(np.float32),
                arr[:, :, 2].astype(np.float32),
            )
        return arr.astype(np.float32)

    _wrapped.__name__ = getattr(spec_fn, "__name__", "_wrapped")
    _wrapped.__module__ = getattr(spec_fn, "__module__", __name__)
    _wrapped._spb_mono_contract_wrapped = True
    return _wrapped


def _spb_apply_monolithic_contract_guards():
    wrapped = 0
    for mono_id, entry in list(MONOLITHIC_REGISTRY.items()):
        if not isinstance(entry, tuple) or len(entry) < 2:
            continue
        spec_fn, paint_fn = entry[0], entry[1]
        new_spec = _spb_wrap_monolithic_spec_contract(mono_id, spec_fn) if callable(spec_fn) else spec_fn
        new_paint = _spb_wrap_monolithic_paint_contract(mono_id, paint_fn) if callable(paint_fn) else paint_fn
        if new_spec is not spec_fn or new_paint is not paint_fn:
            MONOLITHIC_REGISTRY[mono_id] = (new_spec, new_paint, *entry[2:])
            wrapped += int(new_spec is not spec_fn) + int(new_paint is not paint_fn)
    if wrapped:
        print(f"  [Monolithic Contract] Wrapped {wrapped} paint/spec path(s)")


_spb_apply_monolithic_contract_guards()

# ================================================================
# GENERIC FALLBACK RENDERER - moved to engine.render
# ================================================================
from engine.render import render_generic_finish



# --- COMPOSE FUNCTIONS (array helpers from engine.core) ---

# ================================================================
# DUAL LAYER BASE SYSTEM - implementation in engine/overlay.py
# ================================================================
def _normalize_second_base_blend_mode(mode):
    """Delegate to engine.overlay (kept here for callers that use it by name)."""
    from engine.overlay import _normalize_second_base_blend_mode as _norm
    return _norm(mode)


def blend_dual_base_spec(spec_primary, spec_secondary, strength,
                          blend_mode="noise", noise_scale=24, seed=42,
                          pattern_mask=None, zone_mask=None, overlay_scale=1.0):
    """Delegate to engine.overlay with noise_fn=multi_scale_noise. overlay_scale from engine.overlay_context when not passed."""
    from engine.overlay import blend_dual_base_spec as _blend_spec
    try:
        from engine import overlay_context
        _scale = getattr(overlay_context, "overlay_scale", 1.0)
    except Exception:
        _scale = 1.0
    return _blend_spec(
        spec_primary, spec_secondary, strength,
        blend_mode=blend_mode, noise_scale=noise_scale, seed=seed,
        pattern_mask=pattern_mask, zone_mask=zone_mask,
        noise_fn=multi_scale_noise, overlay_scale=_scale
    )


def blend_dual_base_paint(paint_primary, paint_secondary, alpha_map):
    """Delegate to engine.overlay."""
    from engine.overlay import blend_dual_base_paint as _blend_paint
    return _blend_paint(paint_primary, paint_secondary, alpha_map)


def overlay_pattern_on_spec(spec, pattern_id, shape, mask, seed, sm, scale=1.0, opacity=1.0, spec_mult=1.0, rotation=0):
    """Overlay a pattern texture ON TOP of an existing spec map.

    Used to add patterns over monolithic finishes. The monolithic generates
    its own complete spec, then this function modulates M/R/CC with the
    pattern texture - same math as compose_finish, but starting from an
    arbitrary spec map instead of a flat base.

    opacity: 0-1, how much the pattern affects the monolithic's values.
             1.0 = full pattern modulation, 0.5 = half-strength.
    """
    if not pattern_id or pattern_id == "none" or pattern_id not in PATTERN_REGISTRY:
        return spec  # Nothing to overlay

    pattern = PATTERN_REGISTRY[pattern_id]
    # Image-based patterns (V5 engine registry): no texture_fn, use image_path
    image_path = pattern.get("image_path")
    if image_path:
        try:
            from engine.render import _load_image_pattern
            pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if pv is None:
                return spec
            pv = np.asarray(pv, dtype=np.float32)
            pv_min, pv_max = float(pv.min()), float(pv.max())
            if pv_max - pv_min > 1e-8:
                pv = (pv - pv_min) / (pv_max - pv_min)
            else:
                pv = np.zeros_like(pv)
            R_range, M_range = 60.0, 50.0
            M_arr = spec[:, :, 0].astype(np.float32)
            R_arr = spec[:, :, 1].astype(np.float32)
            M_arr = M_arr + pv * M_range * sm * opacity * spec_mult
            R_arr = R_arr + pv * R_range * sm * opacity * spec_mult
            spec[:, :, 0] = np.clip(M_arr * mask + spec[:, :, 0].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            spec[:, :, 1] = np.clip(R_arr * mask + spec[:, :, 1].astype(np.float32) * (1 - mask), 0, 255).astype(np.uint8)
            return spec
        except Exception:
            return spec

    tex_fn = pattern.get("texture_fn")
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


def overlay_pattern_paint(paint, pattern_id, shape, mask, seed, pm, bb, scale=1.0, opacity=1.0, rotation=0, spec_mult=1.0):
    """Overlay a pattern's paint modifier ON TOP of a monolithic's paint output.

    Applies the pattern's paint_fn (if any) with attenuated strength.
    Uses spatial blending via pattern_val so paint follows actual texture shape.
    """
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if not pattern_id or pattern_id == "none" or pattern_id not in PATTERN_REGISTRY:
        return paint
    pattern = PATTERN_REGISTRY[pattern_id]
    pat_paint_fn = pattern.get("paint_fn", paint_none)
    hard_mask = np.where(mask > 0.5, mask, 0.0).astype(np.float32)
    # Save paint before pattern modification for spatial blending
    paint_before = paint.copy()
    if pat_paint_fn is not paint_none:
        # Run pattern paint - boosted for visibility (pattern paint_fns have tiny multipliers)
        # !! ARCHITECTURE GUARD - Same _PAT_PAINT_BOOST as compose_paint_mod. Keep in sync.
        _PAT_PAINT_BOOST = 3.5
        paint = pat_paint_fn(paint, shape, hard_mask, seed, pm * 0.5 * opacity * spec_mult * _PAT_PAINT_BOOST, bb * 0.5 * opacity * spec_mult * _PAT_PAINT_BOOST)
        if getattr(pat_paint_fn, "_spb_pattern_direct_paint", False) and abs(float(scale or 1.0) - 1.0) < 1e-6 and abs(float(rotation or 0.0) % 360.0) < 1e-6:
            return np.ascontiguousarray(np.clip(paint[:, :, :3], 0, 1).astype(np.float32))
    # --- SPATIAL BLEND: use pattern_val to make paint follow texture shape ---
    image_path = pattern.get("image_path")
    if image_path:
        try:
            from engine.render import _load_image_pattern, _load_color_image_pattern
            # Load the FULL COLOR version for paint overlay
            rgba = _load_color_image_pattern(image_path, shape, scale=scale, rotation=rotation)
            if rgba is not None and rgba.shape[2] >= 4:
                alpha = rgba[:, :, 3]
                rgb = rgba[:, :, :3]
                # Check if image has REAL transparency or is fully opaque
                has_real_transparency = float(alpha.min()) < 0.95
                if has_real_transparency:
                    # Image has transparent areas — use alpha as blend mask
                    alpha_3d = (alpha[:, :, np.newaxis] * opacity * hard_mask[:, :, np.newaxis]).astype(np.float32)
                    paint[:, :, :3] = np.clip(
                        paint_before[:, :, :3] * (1.0 - alpha_3d) + rgb * alpha_3d,
                        0, 1
                    ).astype(np.float32)
                else:
                    # Fully opaque image (like Art Deco) — use SCREEN blend so bright
                    # pattern areas show on top of existing paint, dark areas are transparent
                    # Screen blend: result = 1 - (1-a)(1-b) = a + b - a*b
                    screen = paint_before[:, :, :3] + rgb - paint_before[:, :, :3] * rgb
                    blend_3d = np.full_like(screen[:, :, :1], opacity, dtype=np.float32) * hard_mask[:, :, np.newaxis]
                    paint[:, :, :3] = np.clip(
                        paint_before[:, :, :3] * (1.0 - blend_3d) + screen * blend_3d,
                        0, 1
                    ).astype(np.float32)
                    print(f"    [OVERLAY PAINT] Screen-blended opaque image pattern at {opacity*100:.0f}%")
            elif rgba is not None:
                # Fewer than 4 channels — use Screen blend
                screen = paint_before[:, :, :3] + rgba[:, :, :3] - paint_before[:, :, :3] * rgba[:, :, :3]
                blend_3d = np.full_like(screen[:, :, :1], opacity, dtype=np.float32) * hard_mask[:, :, np.newaxis]
                paint[:, :, :3] = np.clip(
                    paint_before[:, :, :3] * (1.0 - blend_3d) + screen * blend_3d,
                    0, 1
                ).astype(np.float32)
            else:
                # Fallback to grayscale if color load fails
                pv = _load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
                if pv is not None:
                    pv = np.asarray(pv, dtype=np.float32)
                    pv_min, pv_max = float(pv.min()), float(pv.max())
                    if pv_max - pv_min > 1e-8:
                        pv = (pv - pv_min) / (pv_max - pv_min)
                    pv_3d = pv[:, :, np.newaxis] * opacity * hard_mask[:, :, np.newaxis]
                    paint = np.clip(paint_before * (1.0 - pv_3d) + paint * pv_3d, 0, 1).astype(np.float32)
        except Exception as _img_err:
            print(f"    [OVERLAY PAINT] Image pattern paint failed: {_img_err}")
        return paint
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


def _suggest_similar_ids(requested_id, registry, max_suggestions=5):
    """Return a list of registry keys that are similar to the requested ID.
    Uses simple substring and prefix matching for fast, dependency-free suggestions."""
    if not requested_id or not registry:
        return []
    req = str(requested_id).lower().strip()
    scored = []
    for key in registry:
        k = str(key).lower()
        # Exact substring match scores highest
        if req in k or k in req:
            scored.append((0, key))
        # Shared prefix
        elif k[:3] == req[:3]:
            scored.append((1, key))
        # Any word overlap
        else:
            req_parts = set(req.replace("_", " ").replace("-", " ").split())
            key_parts = set(k.replace("_", " ").replace("-", " ").split())
            overlap = req_parts & key_parts
            if overlap:
                scored.append((2, key))
    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:max_suggestions]]


def _sanitize_spec_result_legacy_unused(zone_spec, shape):
    """Ensure zone_spec is a numpy array, not a dict. Some spec functions return dicts."""
    if isinstance(zone_spec, dict):
        for key in ('spec', 'pattern_val', 'result'):
            if key in zone_spec and isinstance(zone_spec[key], np.ndarray):
                return zone_spec[key]
        # Dict with no recognized array key — create default
        default = np.zeros((shape[0], shape[1], 4), dtype=np.float32)
        default[:,:,0] = 5; default[:,:,1] = 100; default[:,:,2] = 16; default[:,:,3] = 255
        return default
    return zone_spec


def _sanitize_spec_result(zone_spec, shape):
    """Normalize spec outputs from all engine contracts to HxWx4 float32."""
    h, w = shape[:2]

    def _default():
        default = np.zeros((h, w, 4), dtype=np.float32)
        default[:, :, 0] = 5
        default[:, :, 1] = 100
        default[:, :, 2] = 16
        default[:, :, 3] = 255
        return default

    def _plane(value, fallback):
        if value is None:
            return np.full((h, w), float(fallback), dtype=np.float32)
        arr = np.asarray(value, dtype=np.float32)
        if arr.ndim == 0:
            return np.full((h, w), float(arr), dtype=np.float32)
        if arr.shape != (h, w):
            try:
                arr = np.resize(arr, (h, w)).astype(np.float32)
            except Exception:
                return np.full((h, w), float(fallback), dtype=np.float32)
        return arr

    if isinstance(zone_spec, dict):
        for key in ("spec", "rgba", "result"):
            if key in zone_spec:
                return _sanitize_spec_result(zone_spec[key], shape)
        if any(k in zone_spec for k in ("M", "R", "CC")):
            zone_spec = (zone_spec.get("M"), zone_spec.get("R"), zone_spec.get("CC"))
        else:
            return _default()

    if isinstance(zone_spec, (tuple, list)) and len(zone_spec) >= 2:
        out = np.empty((h, w, 4), dtype=np.float32)
        out[:, :, 0] = np.clip(_plane(zone_spec[0], 5), 0, 255)
        out[:, :, 1] = np.clip(_plane(zone_spec[1], 100), 0, 255)
        out[:, :, 2] = np.clip(_plane(zone_spec[2] if len(zone_spec) > 2 else None, 16), 0, 255)
        out[:, :, 3] = 255
        return out

    if isinstance(zone_spec, np.ndarray):
        arr = zone_spec.astype(np.float32, copy=False)
        if arr.ndim == 3 and arr.shape[0] in (3, 4) and arr.shape[1:3] == (h, w):
            arr = np.moveaxis(arr, 0, -1)
        if arr.ndim == 2:
            out = np.empty((h, w, 4), dtype=np.float32)
            out[:, :, 0] = np.clip(_plane(arr, 5), 0, 255)
            out[:, :, 1] = 100
            out[:, :, 2] = 16
            out[:, :, 3] = 255
            return out
        if arr.ndim == 3 and arr.shape[:2] == (h, w):
            if arr.shape[2] == 4:
                return arr
            out = np.empty((h, w, 4), dtype=np.float32)
            out[:, :, 0] = np.clip(arr[:, :, 0], 0, 255)
            out[:, :, 1] = np.clip(arr[:, :, 1] if arr.shape[2] > 1 else 100, 0, 255)
            out[:, :, 2] = np.clip(arr[:, :, 2] if arr.shape[2] > 2 else 16, 0, 255)
            out[:, :, 3] = 255
            return out
    return zone_spec

def _sanitize_paint_result(paint, shape, backup=None):
    """Ensure paint is a numpy array, not a dict."""
    if isinstance(paint, dict):
        for key in ('paint', 'result'):
            if key in paint and isinstance(paint[key], np.ndarray):
                return paint[key]
        return backup.copy() if backup is not None else np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    return paint


def build_multi_zone(paint_file, output_dir, zones, iracing_id="23371", seed=51, save_debug_images=False, import_spec_map=None, car_prefix="car_num", stamp_image=None, stamp_spec_finish="gloss", preview_mode=False, decal_spec_finishes=None, decal_paint_path=None, decal_mask_base64=None, abort_event=None, progress_callback=None, generate_normal_map=False, export_layers=False):
    """Apply different finishes to color-detected zones — the core renderer.

    PUBLIC, stable. This is THE main entrypoint for the engine. It handles
    paint loading, zone-mask building, finish/pattern composition, decal
    overlays, optional stamps, optional normal maps, and TGA writing.

    ZONE PRIORITY: zones are processed in array order, FIRST WINS. Each
    zone's mask is clipped against everything previously claimed (with a
    soft 0.8 multiplier so anti-aliased edges blend gently). The special
    ``color: 'remaining'`` zone fills whatever has not been claimed yet
    and should always be the LAST entry.

    MASK BLENDING: zone masks default to soft (gaussian-blurred 3px) edges
    so finishes blend at color boundaries instead of producing aliased
    seams. Pre-drawn ``region_mask`` arrays are treated as hard masks.

    REMAINDER LOGIC: any pixel not claimed by an earlier zone (i.e.,
    ``claimed < 1.0``) is available to a remainder zone. Remainder uses
    ``1.0 - claimed`` so soft-edge blends carry through coherently.

    Zone format supports THREE modes:

    1. LEGACY (backward compat): ``"finish"`` key maps to FINISH_REGISTRY::

         {"name": "Body", "color": "blue", "finish": "chrome", "intensity": "100"}

    2. COMPOSITING (v3.0+): ``"base"`` + optional ``"pattern"`` keys::

         {"name": "Body", "color": "blue", "base": "chrome",
          "pattern": "carbon_fiber", "intensity": "100"}

       375 bases x 569 patterns = 213k+ combinations.

    3. MONOLITHIC: ``"finish"`` key maps to MONOLITHIC_REGISTRY
       (e.g. ``"phantom"``, ``"ember_glow"``)::

         {"name": "Body", "color": "blue", "finish": "phantom", "intensity": "100"}

    Args:
        paint_file: Path to source paint .tga/.png (must exist unless
            ``preview_mode=True``).
        output_dir: Directory to write outputs into. Created if missing.
            Ignored when ``preview_mode=True``.
        zones: List of zone dicts; see above for accepted shapes.
        iracing_id: iRacing customer ID baked into output filenames.
        seed: Deterministic seed (int or str — non-numeric strings are
            hashed).
        save_debug_images: When True, write per-zone mask PNGs.
        import_spec_map: Optional path to a base spec map to overlay on top
            of, instead of starting from a blank canvas.
        car_prefix: Output filename prefix; default ``"car_num"``.
        stamp_image: Optional decal/sticker image to stamp on top.
        stamp_spec_finish: Spec finish applied to the stamp pixels.
        preview_mode: When True, returns arrays without writing TGAs.
        decal_spec_finishes: Optional per-decal spec overrides.
        decal_paint_path: Optional decal RGBA composite path.
        decal_mask_base64: Optional base64 decal mask.
        abort_event: Optional ``threading.Event`` for early cancellation.
        progress_callback: Optional ``callable(percent, message)``.
        generate_normal_map: When True, also write a normal map TGA.
        export_layers: When True, return per-zone layer arrays for export.

    Returns:
        Tuple ``(paint_rgb_uint8, combined_spec_uint8, zone_masks)`` —
        or ``(paint, spec, zone_masks, layers)`` when ``export_layers=True``,
        or ``(paint, spec)`` when ``preview_mode=True``.

    Raises:
        ValueError: zones is empty or paint_file is missing.

    Side effects:
        Writes car_num_<id>.tga, car_spec_<id>.tga, PREVIEW_*.png and
        (optionally) zone debug images into ``output_dir`` unless
        ``preview_mode=True``.
    """
    # Validate inputs early so we surface actionable errors instead of
    # cryptic IndexErrors/KeyErrors deep inside the pipeline.
    _validate_zones(zones)
    if not preview_mode:
        _validate_paint_file(paint_file)
    seed = _coerce_seed(seed)

    # Ensure expansion modules are loaded on first render (lazy-load for fast startup)
    _ensure_expansions_loaded()

    logger.info("=" * 60)
    logger.info(f"  {ENGINE_DISPLAY_NAME} - Base + Pattern Compositing")
    logger.info(f"  Zones: {len(zones)}  |  Seed: {seed}  |  Engine: {ENGINE_VERSION}")
    logger.info(f"  Combinations: {len(BASE_REGISTRY)} bases x {len(PATTERN_REGISTRY)} patterns = {len(BASE_REGISTRY) * len(PATTERN_REGISTRY)}+")
    logger.info("=" * 60)

    # ---- Zone result cache (preview_mode only) ----
    # Persists across calls as a function attribute so unchanged zones are skipped.
    # Each entry: { 'zone_spec': np.array, 'paint_delta': np.array, 'mask': np.array }
    # 'paint_delta' is the paint array AFTER this zone was applied minus the paint BEFORE,
    # masked to the zone — so we can replay it without re-running the full pipeline.
    # Cache is invalidated externally (by server.py) when paint file or scale changes.
    import hashlib as _hashlib
    if not hasattr(build_multi_zone, '_zone_cache'):
        build_multi_zone._zone_cache = {}

    start_time = time.time()
    if not preview_mode:
        os.makedirs(output_dir, exist_ok=True)

    # Load paint -- PROTECT THE ORIGINAL SOURCE FILE
    # ALWAYS back up the source in its own directory on first render.
    # On subsequent renders, ALWAYS load from the backup to prevent
    # cumulative degradation (re-processing a previously rendered file).
    import shutil
    if not preview_mode:
        logger.info(f"\n  Loading: {paint_file}")
        paint_basename = os.path.basename(paint_file)
        source_normalized = os.path.normpath(os.path.abspath(paint_file))
        source_dir = os.path.dirname(source_normalized)

        if paint_basename.startswith("ORIGINAL_"):
            # Source is already the backup file - use it directly
            logger.info(f"  Source is already the backup file - using directly")
        else:
            # Check for backup in the SOURCE directory (where the paint lives)
            backup_path = os.path.join(source_dir, f"ORIGINAL_{paint_basename}")
            if not os.path.exists(backup_path):
                # First render ever for this file - back it up so subsequent
                # renders never re-process previously rendered output. This
                # is a SIDE EFFECT — we write to the source's directory.
                shutil.copy2(paint_file, backup_path)
                logger.info(f"  Backed up original to: {source_dir}/ORIGINAL_{paint_basename}")
            else:
                # Backup exists - ALWAYS load from it to avoid stacking effects
                paint_file = backup_path
                logger.info(f"  Loading from backup: ORIGINAL_{paint_basename} (prevents re-processing)")

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
    zone_masks_preclaim = []
    claimed = np.zeros((h, w), dtype=np.float32)  # Track what's been claimed

    # Per-zone layer collection for export_layers mode (#21)
    _export_zone_layers = [] if export_layers else None

    # First pass: build masks for non-remainder zones
    for i, zone in enumerate(zones):
        color_desc = zone.get("color", "everything")

        # SPATIAL REGION MASK: if the zone has a pre-drawn region mask, use it directly
        # This bypasses color detection entirely - great for numbers, sponsors, artwork
        if "region_mask" in zone and zone["region_mask"] is not None:
            region = zone["region_mask"]
            # Ensure it's the right size
            if region.shape[0] != h or region.shape[1] != w:
                from PIL import Image as PILImage
                rm_img = PILImage.fromarray((region * 255).astype(np.uint8))
                rm_img = rm_img.resize((w, h), PILImage.NEAREST)
                region = np.array(rm_img).astype(np.float32) / 255.0
            mask = region.astype(np.float32)
            mask_preclaim = mask.astype(np.float32).copy()
            # Subtract already-claimed areas
            mask = mask_preclaim
            mask = np.clip(mask - claimed * 0.8, 0, 1)
            claimed = np.clip(claimed + mask, 0, 1)
            pixel_count = np.sum(mask > 0.1)
            pct = pixel_count / (h * w) * 100
            print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (SPATIAL REGION MASK)")
            zone_masks.append(mask)
            zone_masks_preclaim.append(mask_preclaim)
            continue

        # Parse selector(s) - can be a single selector or a LIST of selectors (multi-color zone)
        hard_edge = zone.get("hard_edge", False)
        _blur = 0 if hard_edge else 3

        # PHOTOSHOP-CORRECT LAYER-LOCAL COLOR MATCH:
        # If the zone is restricted to a PSD layer AND the client sent us the
        # layer's own RGB, build a layer-local scheme and stats so the color
        # selector matches against the layer's unblended pixels rather than the
        # composite. This fixes the semi-transparent/blended-layer case where
        # the composite color differs from the layer's own color.
        _match_scheme = scheme
        _match_stats = stats
        _layer_rgb = zone.get("source_layer_rgb")
        if _layer_rgb is not None:
            try:
                _lrgb = np.asarray(_layer_rgb)
                if _lrgb.dtype != np.uint8:
                    _lrgb = _lrgb.astype(np.uint8)
                # Resize layer RGB to match scheme if needed
                if _lrgb.shape[0] != h or _lrgb.shape[1] != w:
                    _lrgb = cv2.resize(_lrgb, (w, h), interpolation=cv2.INTER_AREA)
                # Extract RGB + alpha-gate: pixels with alpha < 8 become unmatched
                # (set to a neutral magenta so color match rejects them).
                if _lrgb.ndim == 3 and _lrgb.shape[2] >= 4:
                    _alpha_gate = _lrgb[:, :, 3] >= 8
                    _rgb_u8 = _lrgb[:, :, :3].copy()
                    # Pixels where layer has no contribution → unreachable magenta
                    _rgb_u8[~_alpha_gate] = (255, 0, 255)
                else:
                    _rgb_u8 = _lrgb[:, :, :3]
                _match_scheme = _rgb_u8.astype(np.float32) / 255.0
                _match_stats = analyze_paint_colors(_match_scheme)
                print(f"    Zone {i+1} [{zone['name']}]: color-match using layer-local RGB (Photoshop-correct)")
            except Exception as _llm_err:
                print(f"    Zone {i+1} [{zone['name']}]: layer-local match failed ({_llm_err}), using composite")
                _match_scheme = scheme
                _match_stats = stats

        if isinstance(color_desc, list):
            # Multi-color zone: union of multiple color selectors
            # Each element is a dict like {"color_rgb": [R,G,B], "tolerance": 40}
            union_mask = np.zeros((h, w), dtype=np.float32)
            for sub_desc in color_desc:
                if isinstance(sub_desc, dict):
                    sub_selector = sub_desc
                else:
                    sub_selector = parse_color_description(str(sub_desc))
                sub_mask = build_zone_mask(_match_scheme, _match_stats, sub_selector, blur_radius=_blur)
                union_mask = np.maximum(union_mask, sub_mask)  # OR/union
            mask = union_mask
            print(f"    Zone {i+1} [{zone['name']}]: multi-color ({len(color_desc)} selectors)")
        elif isinstance(color_desc, dict):
            selector = color_desc
            if selector.get("remainder"):
                zone_masks.append(None)  # Placeholder
                zone_masks_preclaim.append(None)
                continue
            mask = build_zone_mask(_match_scheme, _match_stats, selector, blur_radius=_blur)
        else:
            selector = parse_color_description(str(color_desc))
            if selector.get("remainder"):
                zone_masks.append(None)  # Placeholder
                zone_masks_preclaim.append(None)
                continue
            mask = build_zone_mask(_match_scheme, _match_stats, selector, blur_radius=_blur)

        # ---- SPATIAL MASK: intersect color mask with drawn include/exclude regions ----
        # spatial_mask is a 2D numpy array: 0=unset, 1=include, 2=exclude
        # Unlike region_mask which REPLACES color detection, spatial_mask REFINES it.
        spatial = zone.get("spatial_mask")
        if spatial is not None and isinstance(spatial, np.ndarray):
            # Resize if needed
            if spatial.shape[0] != h or spatial.shape[1] != w:
                sm_img = Image.fromarray(spatial.astype(np.uint8))
                sm_img = sm_img.resize((w, h), Image.NEAREST)
                spatial = np.array(sm_img).astype(np.uint8)
            # Exclude: zero out pixels marked as 2
            mask = np.where(spatial == 2, 0.0, mask)
            # Include: if ANY pixels are marked as 1, restrict to only those
            has_include = np.any(spatial == 1)
            if has_include:
                mask = np.where(spatial == 1, mask, 0.0)

        # Layer-restricted zones must resolve ownership INSIDE the chosen
        # source layer before higher-priority zones subtract claimed pixels.
        # If we wait until render-time, earlier zones can steal matching colors
        # from unrelated layers and leave only a partial mask here.
        _source_layer_mask = _normalize_source_layer_mask(
            zone.get("source_layer_mask"), (h, w), i, zone
        )
        if _source_layer_mask is not None:
            mask = (mask * _source_layer_mask).astype(np.float32)

        mask_preclaim = mask.astype(np.float32).copy()

        # Subtract already-claimed areas (higher priority zones come first)
        mask = mask_preclaim
        mask = np.clip(mask - claimed * 0.8, 0, 1)

        # Add to claimed
        claimed = np.clip(claimed + mask, 0, 1)

        pixel_count = np.sum(mask > 0.1)
        pct = pixel_count / (h * w) * 100
        print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (color: {color_desc})")

        zone_masks.append(mask)
        zone_masks_preclaim.append(mask_preclaim)

    # Harden zone masks: threshold soft masks so zones get clean ownership.
    # Without this, later zones (especially "remaining") bleed into earlier zones
    # because soft masks (0.0-1.0) leave gaps that remainder fills, then the blend
    # formula (zone_spec * mask + existing * (1-mask)) pulls values toward the later zone.
    HARD_THRESHOLD = 0.15  # Pixels above this get full ownership (mask=1.0)
    def _harden_zone_ownership_mask(soft_mask, hard_edge):
        if soft_mask is None:
            return None
        if np.max(soft_mask) < 0.01:
            return np.zeros_like(soft_mask)
        if hard_edge:
            return np.where(soft_mask > 0.01, 1.0, 0.0).astype(np.float32)
        return np.where(
            soft_mask > HARD_THRESHOLD,
            1.0,
            soft_mask / HARD_THRESHOLD * soft_mask
        ).astype(np.float32)

    for i in range(len(zone_masks)):
        hard_edge = zones[i].get("hard_edge", False) if i < len(zones) else False
        zone_masks[i] = _harden_zone_ownership_mask(zone_masks[i], hard_edge)
        zone_masks_preclaim[i] = _harden_zone_ownership_mask(zone_masks_preclaim[i], hard_edge)

    priority_override_masks = [None] * len(zone_masks)
    for i, zone in enumerate(zones):
        if zone_masks_preclaim[i] is None or not zone.get("priority_override"):
            continue
        spatial = zone.get("spatial_mask")
        try:
            has_include = bool(np.any(np.asarray(spatial) == 1))
        except Exception:
            has_include = False
        if not has_include:
            continue
        priority_override_masks[i] = zone_masks_preclaim[i]
        pixel_count = int(np.sum(priority_override_masks[i] > 0.1))
        if pixel_count > 0:
            pct = pixel_count / (h * w) * 100
            print(f"    Zone {i+1} [{zone['name']}]: priority override armed on {pct:.1f}% of pixels")

    claim_masks_for_remainder = [
        priority_override_masks[i] if priority_override_masks[i] is not None else zone_masks[i]
        for i in range(len(zone_masks))
    ]

    # Rebuild claimed from hardened masks (so remainder doesn't bleed into them)
    claimed_hard = np.zeros((h, w), dtype=np.float32)
    for i in range(len(claim_masks_for_remainder)):
        if claim_masks_for_remainder[i] is not None:
            claimed_hard = np.clip(claimed_hard + claim_masks_for_remainder[i], 0, 1)

    # Second pass: fill in "remainder" zones
    for i, zone in enumerate(zones):
        if zone_masks[i] is not None:
            continue
        remainder_mask = _build_remainder_zone_mask(
            zone, i, zones, claim_masks_for_remainder, claimed_hard, sigma=2.0
        )

        pixel_count = np.sum(remainder_mask > 0.1)
        pct = pixel_count / (h * w) * 100
        print(f"    Zone {i+1} [{zone['name']}]: {pct:.1f}% of pixels (remainder)")
        zone_masks[i] = remainder_mask
        claim_masks_for_remainder[i] = remainder_mask

    print(f"  Zone masks built: {time.time()-t_masks:.2f}s")

    # Per-zone "prior claimed": sum of earlier zone masks (clip to 1).
    # Stacks for ALL zones: Zone 1 wins, then Zone 2 gets remainder, then Zone 3, etc.
    # effective_mask[i] = zone_masks[i] * (1 - prior_claimed[i]) so later zones never overwrite earlier.
    prior_claimed = []
    _cum = np.zeros((h, w), dtype=np.float32)
    for _idx in range(len(claim_masks_for_remainder)):
        prior_claimed.append(_cum.copy())
        if claim_masks_for_remainder[_idx] is not None:
            _cum = np.clip(_cum + claim_masks_for_remainder[_idx], 0, 1)

    future_priority_override = [None] * len(zone_masks)
    _future = np.zeros((h, w), dtype=np.float32)
    for _idx in range(len(zone_masks) - 1, -1, -1):
        future_priority_override[_idx] = _future.copy()
        if priority_override_masks[_idx] is not None:
            _future = np.clip(_future + priority_override_masks[_idx], 0, 1)

    # Initialize outputs
    # Start with default spec OR imported spec map (for merge mode)
    if import_spec_map and os.path.exists(import_spec_map):
        print(f"\n  IMPORT SPEC MAP: Loading {os.path.basename(import_spec_map)}")
        try:
            imp_img = Image.open(import_spec_map)
            # Handle both RGBA (32-bit) and RGB (24-bit) spec maps
            if imp_img.mode == 'RGBA':
                combined_spec = np.array(imp_img).astype(np.float32)
            elif imp_img.mode == 'RGB':
                rgb = np.array(imp_img).astype(np.float32)
                alpha = np.full((rgb.shape[0], rgb.shape[1], 1), 255, dtype=np.float32)
                combined_spec = np.concatenate([rgb, alpha], axis=2)
            else:
                imp_img = imp_img.convert('RGBA')
                combined_spec = np.array(imp_img).astype(np.float32)
            # Resize to match paint if needed
            if combined_spec.shape[0] != h or combined_spec.shape[1] != w:
                imp_resized = Image.fromarray(combined_spec.astype(np.uint8)).resize((w, h), Image.LANCZOS)
                combined_spec = np.array(imp_resized).astype(np.float32)
            print(f"    Imported spec: {combined_spec.shape[1]}x{combined_spec.shape[0]} RGBA")
            print(f"    Zones will MERGE on top of imported spec map")
        except Exception as e:
            logger.warning(f"    WARNING: Failed to load import spec map '{import_spec_map}': {e}")
            logger.warning(f"    Falling back to default spec")
            combined_spec = np.zeros((h, w, 4), dtype=np.float32)
            combined_spec[:,:,0] = 5       # Low metallic
            combined_spec[:,:,1] = 100     # Medium-rough
            combined_spec[:,:,2] = 16      # Max clearcoat
            combined_spec[:,:,3] = 255     # Full spec mask
    else:
        combined_spec = np.zeros((h, w, 4), dtype=np.float32)
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
    # Shared thread pool for spec generation — reused across all zones instead of
    # creating/destroying a new ThreadPoolExecutor per zone (saves pool overhead).
    # max_workers=2: one for current zone's spec, one for next zone's spec (pipelining).
    _shared_spec_pool = ThreadPoolExecutor(max_workers=min(2, _os.cpu_count() or 1))
    for i, zone in enumerate(zones):
        # Preview abort: if a newer request arrived, return partial render immediately
        if preview_mode and abort_event is not None and abort_event.is_set():
            print(f"  [ABORT] Preview aborted after {i}/{len(zones)} zones ({time.time()-start_time:.2f}s)")
            paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
            if paint_rgb.shape[2] == 4:
                paint_rgb = paint_rgb[:, :, :3]
            combined_spec[:,:,1] = np.where(combined_spec[:,:,0] < 240, np.maximum(combined_spec[:,:,1], 15), combined_spec[:,:,1])
            combined_spec[:,:,2] = np.maximum(combined_spec[:,:,2], 16)
            combined_spec_u8 = np.clip(combined_spec, 0, 255).astype(np.uint8)
            return (paint_rgb, combined_spec_u8)

        t_zone = time.time()
        name = zone["name"]
        # Report progress via callback (if provided)
        if progress_callback:
            try:
                progress_callback(i + 1, len(zones), name)
            except Exception:
                pass
        intensity = zone.get("intensity", "100")
        # Use effective mask so this zone does not overwrite earlier zones (same-color overlap)
        zone_mask_raw = priority_override_masks[i] if priority_override_masks[i] is not None else zone_masks[i]
        if priority_override_masks[i] is not None and zone_mask_raw is not None:
            zone_mask = zone_mask_raw.astype(np.float32)
        elif zone_mask_raw is not None and i > 0 and prior_claimed[i] is not None:
            zone_mask = (zone_mask_raw * (1.0 - prior_claimed[i])).astype(np.float32)
        else:
            zone_mask = zone_mask_raw
        _future_override = future_priority_override[i] if i < len(future_priority_override) else None
        if zone_mask is not None and _future_override is not None and np.max(_future_override) > 0.01:
            zone_mask = (zone_mask * (1.0 - _future_override)).astype(np.float32)

        # PSD layer restriction: intersect zone mask with source layer alpha
        _source_layer_mask = _normalize_source_layer_mask(
            zone.get("source_layer_mask"), zone_mask.shape if zone_mask is not None else (h, w), i, zone
        )
        if _source_layer_mask is not None and zone_mask is not None:
            zone_mask = (zone_mask * _source_layer_mask).astype(np.float32)
            print(f"    [{name}] Layer mask applied: {float(zone_mask.sum()):.0f} active pixels")

        try:
            from engine import overlay_context
            overlay_context.overlay_scale = max(0.01, min(5.0, float(zone.get("second_base_scale", 1.0))))
        except Exception:
            pass

        if zone_mask is None or np.max(zone_mask) < 0.01:
            print(f"    [{name}] => SKIPPED (no matching pixels)")
            continue
        # Skip zones covering <0.1% of pixels — invisible and wastes render time
        _zone_coverage = float(np.mean(zone_mask > 0.1))
        if _zone_coverage < 0.001:
            print(f"    [{name}] => SKIPPED (coverage {_zone_coverage*100:.2f}% < 0.1% threshold)")
            continue

        # ---- Zone-level cache (preview_mode only) ----
        # Compute a hash of all zone settings + mask fingerprint.
        # If matched, replay the cached zone_spec and paint_delta instead of re-rendering.
        _zone_cache_key = None
        if preview_mode:
            try:
                # Build a stable cache key from zone settings + mask fingerprint.
                # We exclude the zone mask data itself (too large) and instead fingerprint
                # it via shape + sum + max so minor floating-point drift doesn't cause
                # spurious cache misses.
                _zone_key_data = {
                    k: v for k, v in zone.items()
                    if k not in ("region_mask", "spatial_mask", "name")
                }
                _zm_sig = f"{zone_mask.shape}:{zone_mask.sum():.4f}:{zone_mask.max():.4f}:{h}x{w}"
                _zone_raw = str(sorted(_zone_key_data.items())) + _zm_sig
                _zone_cache_key = _hashlib.md5(_zone_raw.encode()).hexdigest()
                if _zone_cache_key in build_multi_zone._zone_cache:
                    cached = build_multi_zone._zone_cache[_zone_cache_key]
                    zone_spec = cached['zone_spec']
                    # Replay paint delta: add the cached paint modification back onto current paint
                    _pdelta = cached['paint_delta']
                    _pmask = cached['mask']
                    paint = np.where(_pmask[:, :, np.newaxis] > 0.01,
                                     np.clip(paint + _pdelta, 0, 1), paint).astype(np.float32)
                    print(f"    [{name}] => CACHE HIT (skipped re-render)")
                    # Jump directly to the combined_spec blending step below
                    # (reuse cached zone_spec, paint already updated)
                    # GPU-accelerated when CuPy is available
                    hard_edge = zone.get("hard_edge", False)
                    if is_gpu():
                        _zs_g = to_gpu(zone_spec.astype(np.float32))
                        _m3d_g = to_gpu(zone_mask[:, :, np.newaxis])
                        _cs_g = to_gpu(combined_spec)
                        if hard_edge:
                            combined_spec = to_cpu(xp.where(_m3d_g > 0.01, _zs_g, _cs_g))
                        else:
                            strong = _m3d_g > 0.5
                            soft = (_m3d_g > 0.05) & ~strong
                            blended = xp.clip(_zs_g * _m3d_g + _cs_g * (1 - _m3d_g), 0, 255)
                            combined_spec = to_cpu(xp.where(strong, _zs_g, xp.where(soft, blended, _cs_g)))
                    else:
                        mask3d = zone_mask[:, :, np.newaxis]
                        if hard_edge:
                            combined_spec = np.where(mask3d > 0.01, zone_spec, combined_spec)
                        else:
                            strong = mask3d > 0.5
                            soft = (mask3d > 0.05) & ~strong
                            blended = np.clip(
                                zone_spec.astype(np.float32) * mask3d +
                                combined_spec * (1 - mask3d),
                                0, 255
                            )
                            combined_spec = np.where(strong, zone_spec.astype(np.float32), np.where(soft, blended, combined_spec))
                    print(f"    [Zone {i+1}] \"{name}\" rendered in {time.time()-t_zone:.2f}s (cached)")
                    continue
            except Exception as _ce:
                _zone_cache_key = None  # Cache lookup failed — fall through to normal render
                print(f"    [{name}] zone cache lookup error (falling through): {_ce}")

        # Snapshot paint before this zone renders so we can store the delta
        _paint_before = paint.copy() if (preview_mode and _zone_cache_key) else None

        # Custom intensity overrides per-zone slider values
        # Custom sliders now use 0-1 normalized range (same as presets),
        # so they also need _INTENSITY_SCALE applied.
        # BOIL THE OCEAN audit fix: defend against malformed payloads where
        # one of {spec, paint, bright} is None instead of a float (older
        # saved configs, hand-edited JSON, etc.). Previously crashed with
        # TypeError: float() argument must be... NoneType.
        custom = zone.get("custom_intensity")
        def _safe_float_default(val, default):
            try:
                return float(val) if val is not None else float(default)
            except (TypeError, ValueError):
                return float(default)
        if custom:
            # Fall back to the preset for the zone's intensity if a slot is None.
            _preset_sm, _preset_pm, _preset_bb = _parse_intensity(intensity)
            # Note: _preset_* are post-scale; we want the pre-scale value to
            # mirror "this slot has no override". Easiest: divide back out.
            _ps = _INTENSITY_SCALE["spec"];   _pp = _INTENSITY_SCALE["paint"];   _pb = _INTENSITY_SCALE["bright"]
            _bare_sm = _preset_sm / _ps if _ps else _preset_sm
            _bare_pm = _preset_pm / _pp if _pp else _preset_pm
            _bare_bb = _preset_bb / _pb if _pb else _preset_bb
            sm = _safe_float_default(custom.get("spec"),   _bare_sm) * _INTENSITY_SCALE["spec"]
            pm = _safe_float_default(custom.get("paint"),  _bare_pm) * _INTENSITY_SCALE["paint"]
            bb = _safe_float_default(custom.get("bright"), _bare_bb) * _INTENSITY_SCALE["bright"]
        else:
            sm, pm, bb = _parse_intensity(intensity)
        # Base vs Pattern Intensity: when pattern_intensity is set, pattern uses it so lowering base doesn't kill pattern
        pat_int = zone.get("pattern_intensity")
        if pat_int is not None:
            sm_pattern, _, _ = _parse_intensity(pat_int)
            try:
                pattern_intensity_01 = max(0.0, min(1.0, float(pat_int) / 100.0))
            except (TypeError, ValueError):
                pattern_intensity_01 = 1.0
        else:
            sm_pattern = sm
            pattern_intensity_01 = 1.0

        # --- Dispatch: determine which rendering path to use ---
        spec_mult = float(zone.get("pattern_spec_mult", 1.0))
        base_id = zone.get("base")
        pattern_id = zone.get("pattern", "none")
        finish_name = zone.get("finish")

        # REVERSE FALLBACK: finish from Specials picker that's actually a BASE_REGISTRY entry
        # (COLORSHOXX, MORTAL SHOKK, PARADIGM, Shokk Series, Angle SHOKK, Extreme & Experimental)
        if finish_name and finish_name not in MONOLITHIC_REGISTRY and finish_name in BASE_REGISTRY:
            print(f"    [{name}] specials→base fallback: '{finish_name}' is a base, not a monolithic")
            base_id = finish_name
            finish_name = None

        _engine_rot_debug(f"BUILD_MULTI_ZONE [{name}]: base_id={base_id}, finish_name={finish_name}, "
                          f"rotation={zone.get('rotation')}, finish_colors={zone.get('finish_colors') is not None}, "
                          f"in_MONO_REG={finish_name in MONOLITHIC_REGISTRY if finish_name else 'N/A'}, "
                          f"in_FINISH_REG={finish_name in FINISH_REGISTRY if finish_name else 'N/A'}")

        # PATH 0: CUSTOM MIX FINISH - base_id starts with "custom_"
        if base_id and base_id.startswith("custom_"):
            try:
                # Search multiple locations for custom_finishes.json
                _custom_json_path = None
                for _try_dir in [
                    os.path.dirname(os.path.abspath(__file__)),                           # Same dir as engine
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),           # One level up
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),  # Two levels up (E:\Koda)
                ]:
                    _try_path = os.path.join(_try_dir, 'custom_finishes.json')
                    if os.path.exists(_try_path):
                        _custom_json_path = _try_path
                        break
                if _custom_json_path is None:
                    _custom_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_finishes.json')
                _custom_recipe = None
                if os.path.exists(_custom_json_path):
                    import json as _json_mod
                    with open(_custom_json_path, 'r', encoding='utf-8') as _cf:
                        _custom_list = _json_mod.load(_cf)
                    for _ce in _custom_list:
                        if _ce.get('id') == base_id:
                            _custom_recipe = _ce
                            break
                if _custom_recipe:
                    from engine.compose import mix_finishes, mix_finish_paint
                    _mix_ids = _custom_recipe['finish_ids']
                    _mix_wts = _custom_recipe['weights']
                    _mix_mode = _custom_recipe.get('mix_mode', 'both')  # 'both', 'color', 'spec'
                    print(f"    [{name}] -> PATH 0 (custom mix): {base_id} = {_mix_ids} @ {_mix_wts} mode={_mix_mode}")
                    # Apply spec blend (unless color-only mode)
                    if _mix_mode in ('both', 'spec'):
                        zone_spec = mix_finishes(shape, zone_mask, seed + i * 13, sm, _mix_ids, _mix_wts, monolithic_registry=MONOLITHIC_REGISTRY)
                    else:
                        # Color-only: use neutral spec (the zone's base spec will be used later, or default)
                        zone_spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
                        zone_spec[:,:,0] = 128  # neutral M
                        zone_spec[:,:,1] = 50   # neutral R
                        zone_spec[:,:,2] = 16   # min CC
                        zone_spec[:,:,3] = 255
                    # Apply paint blend (unless spec-only mode)
                    if _mix_mode in ('both', 'color'):
                        paint = mix_finish_paint(paint, shape, zone_mask, seed + i * 13, pm, bb, _mix_ids, _mix_wts, monolithic_registry=MONOLITHIC_REGISTRY)
                    # else: spec-only mode, don't touch paint
                    hard_edge = zone.get("hard_edge", False)
                    mask3d = zone_mask[:, :, np.newaxis]
                    if hard_edge:
                        combined_spec = np.where(mask3d > 0.01, zone_spec.astype(np.float32), combined_spec)
                    else:
                        strong = mask3d > 0.5
                        soft = (mask3d > 0.05) & ~strong
                        blended = np.clip(
                            zone_spec.astype(np.float32) * mask3d +
                            combined_spec * (1 - mask3d),
                            0, 255
                        )
                        combined_spec = np.where(strong, zone_spec.astype(np.float32), np.where(soft, blended, combined_spec))
                    if preview_mode and _zone_cache_key and _paint_before is not None:
                        _pdelta = paint - _paint_before
                        build_multi_zone._zone_cache[_zone_cache_key] = {
                            'zone_spec': zone_spec, 'paint_delta': _pdelta, 'mask': zone_mask
                        }
                    logger.debug(f"    [Zone {i+1}] \"{name}\" rendered in {time.time()-t_zone:.2f}s (custom mix)")
                    continue
                else:
                    logger.warning(f"    {_format_zone_id(i, zone)} WARNING: custom finish '{base_id}' not in custom_finishes.json — falling through")
            except Exception as _cmix_err:
                logger.warning(f"    {_format_zone_id(i, zone)} custom mix error: {_cmix_err} — falling through to normal render")
                import traceback as _tb
                logger.debug(_tb.format_exc())

        if base_id:
            # CHECK: Is this actually a monolithic masquerading as a base?
            # This lets the UI send monolithics via "base" key seamlessly.
            if base_id not in BASE_REGISTRY and base_id in MONOLITHIC_REGISTRY:
                finish_name = base_id
                base_id = None  # Fall through to monolithic path below
            elif base_id not in BASE_REGISTRY:
                _similar_bases = _suggest_similar_ids(base_id, BASE_REGISTRY)
                _hint = f"  Did you mean: {', '.join(_similar_bases)}" if _similar_bases else f"  Available bases: {', '.join(list(BASE_REGISTRY.keys())[:10])}..."
                logger.warning(f"    WARNING: Unknown base '{base_id}' in {_format_zone_id(i, zone)}, skipping zone.\n      {_hint}")
                continue

        if base_id:
            _engine_rot_debug(f"  [{name}] -> PATH 1 (compositing): base={base_id}")
            # PATH 1: v3.0 COMPOSITING - base + pattern (or pattern stack)
            if pattern_id != "none" and pattern_id not in PATTERN_REGISTRY:
                _similar_pats = _suggest_similar_ids(pattern_id, PATTERN_REGISTRY)
                _hint_p = f"  Did you mean: {', '.join(_similar_pats)}" if _similar_pats else ""
                logger.warning(f"    WARNING: Unknown pattern '{pattern_id}' in {_format_zone_id(i, zone)}, falling back to 'none'.{_hint_p}")
                pattern_id = "none"
            zone_scale = float(zone.get("scale", 1.0))
            zone_rotation = float(zone.get("rotation", 0))
            zone_base_scale = float(zone.get("base_scale", 1.0))
            pattern_stack = zone.get("pattern_stack", [])
            primary_pat_opacity = float(zone.get("pattern_opacity", 1.0))

            # SMART AUTO-SCALE: adapt pattern density to zone coverage area
            # Small zones (car numbers, sponsors) get denser patterns automatically
            auto_scale = _compute_zone_auto_scale(zone_mask, shape)
            if auto_scale < 1.0 and pattern_id != "none":
                print(f"      [{name}] Auto-scale: {auto_scale:.3f} (zone covers {(auto_scale**2)*100:.1f}% of canvas)")
            if not zone.get("pattern_fit_zone", False) and zone.get("pattern_placement") != "fit": zone_scale *= auto_scale  # User slider multiplies on top of auto-scale

            # ZONE TARGETING: Fit to Zone bounding box
            # Concentrates the entire pattern into the zone's bounding box.
            # Without this, small zones (car numbers, logos) only see a tiny crop
            # of a full-canvas pattern. With it, the whole pattern squeezes into the zone.
            if (zone.get("pattern_fit_zone", False) or zone.get("pattern_placement") == "fit") and zone_mask is not None:
                rows = np.any(zone_mask > 0.1, axis=1)
                cols = np.any(zone_mask > 0.1, axis=0)
                if rows.any() and cols.any():
                    r_min, r_max = np.where(rows)[0][[0, -1]]
                    c_min, c_max = np.where(cols)[0][[0, -1]]
                    bbox_h = r_max - r_min + 1
                    bbox_w = c_max - c_min + 1
                    bbox_center_y = (r_min + r_max) / 2.0 / h
                    bbox_center_x = (c_min + c_max) / 2.0 / w
                    # Override offset to center pattern on zone bbox
                    zone['pattern_offset_x'] = bbox_center_x
                    zone['pattern_offset_y'] = bbox_center_y
                    # ZOOM IN so the pattern fills just the bbox area
                    # fit_ratio < 1.0 for small zones; dividing by it zooms in
                    fit_ratio = max(bbox_h / h, bbox_w / w)
                    if fit_ratio > 0.01:
                        zone_scale = zone_scale / fit_ratio  # zoom in to concentrate
                        zone_scale = min(zone_scale, 8.0)  # Prevent over-zoom
                    print(f"      [{name}] Fit-to-Zone: bbox=({r_min},{c_min})-({r_max},{c_max}), fit_ratio={fit_ratio:.3f}, effective_scale={zone_scale:.3f}, center=({bbox_center_x:.3f},{bbox_center_y:.3f})")

            # v6.0 advanced finish params
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) / 100.0 if _z_cc is not None and float(_z_cc) > 1.0 else (float(_z_cc) if _z_cc is not None else None)
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {"pattern_sm": sm_pattern, "pattern_intensity": pattern_intensity_01}
            # Pattern strength map (per-pixel modulation)
            if zone.get("pattern_strength_map") is not None:
                _v6kw["pattern_strength_map"] = zone["pattern_strength_map"]
            _v6kw["base_strength"] = float(zone.get("base_strength", 1.0))
            _v6kw["base_spec_strength"] = float(zone.get("base_spec_strength", 1.0))
            _v6kw["base_spec_blend_mode"] = zone.get("base_spec_blend_mode", "normal")
            _v6kw["base_color_mode"] = zone.get("base_color_mode", "source")
            # BOIL THE OCEAN drift fix: when mode='gradient', the engine's
            # _apply_base_color_override expects the stops/direction packaged
            # into base_color as a dict. JS sends them as separate top-level
            # gradient_stops/gradient_direction keys -- pre-fix the engine
            # silently ignored them and the painter saw the gradient picker
            # do nothing. Pack them here so the existing engine path fires.
            if (zone.get("base_color_mode") == "gradient"
                    and zone.get("gradient_stops")):
                _v6kw["base_color"] = {
                    "stops": zone.get("gradient_stops"),
                    "direction": zone.get("gradient_direction", "horizontal"),
                }
            else:
                _v6kw["base_color"] = zone.get("base_color", [1.0, 1.0, 1.0])
            _v6kw["base_color_source"] = zone.get("base_color_source")
            _v6kw["base_color_strength"] = float(zone.get("base_color_strength", 1.0))
            _v6kw["base_color_fit_zone"] = bool(zone.get("base_color_fit_zone", False))
            _v6kw["base_hue_offset"] = float(zone.get("base_hue_offset", 0))
            _v6kw["base_saturation_adjust"] = float(zone.get("base_saturation_adjust", 0))
            _v6kw["base_brightness_adjust"] = float(zone.get("base_brightness_adjust", 0))
            _v6kw["pattern_opacity"] = float(zone.get("pattern_opacity", 1.0))
            _v6kw["pattern_offset_x"] = max(0.0, min(1.0, float(zone.get("pattern_offset_x", 0.5))))
            _v6kw["pattern_offset_y"] = max(0.0, min(1.0, float(zone.get("pattern_offset_y", 0.5))))
            _v6kw["pattern_flip_h"] = bool(zone.get("pattern_flip_h", False))
            _v6kw["pattern_flip_v"] = bool(zone.get("pattern_flip_v", False))
            _v6kw["base_offset_x"] = max(0.0, min(1.0, float(zone.get("base_offset_x", 0.5))))
            _v6kw["base_offset_y"] = max(0.0, min(1.0, float(zone.get("base_offset_y", 0.5))))
            _v6kw["base_rotation"] = float(zone.get("base_rotation", 0))
            _v6kw["base_flip_h"] = bool(zone.get("base_flip_h", False))
            _v6kw["base_flip_v"] = bool(zone.get("base_flip_v", False))
            if zone.get("spec_pattern_stack"): _v6kw["spec_pattern_stack"] = zone["spec_pattern_stack"]
            if zone.get("overlay_spec_pattern_stack"): _v6kw["overlay_spec_pattern_stack"] = zone["overlay_spec_pattern_stack"]
            if zone.get("third_overlay_spec_pattern_stack"): _v6kw["third_overlay_spec_pattern_stack"] = zone["third_overlay_spec_pattern_stack"]
            if zone.get("fourth_overlay_spec_pattern_stack"): _v6kw["fourth_overlay_spec_pattern_stack"] = zone["fourth_overlay_spec_pattern_stack"]
            if zone.get("fifth_overlay_spec_pattern_stack"): _v6kw["fifth_overlay_spec_pattern_stack"] = zone["fifth_overlay_spec_pattern_stack"]
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba; print(f"    [{name}] v6.1 BLEND: base={_z_bb}, dir={_z_bd}, amount={_z_ba:.2f}")
            if _z_pc: _v6kw["paint_color"] = _z_pc
            # Dual Layer Base Overlay — trigger on EITHER base ID or color source
            _z_sb = zone.get("second_base")
            _z_sb_cs = zone.get("second_base_color_source")
            if _z_sb or _z_sb_cs:
                _v6kw["second_base"] = _z_sb or ''
                _v6kw["second_base_color_source"] = _z_sb_cs
                _v6kw["second_base_color"] = zone.get("second_base_color", [1.0, 1.0, 1.0])
                _v6kw["second_base_strength"] = float(zone.get("second_base_strength", 0.0))
                _v6kw["second_base_spec_strength"] = float(zone.get("second_base_spec_strength", 1.0))
                _v6kw["second_base_blend_mode"] = zone.get("second_base_blend_mode", "noise")
                _v6kw["second_base_noise_scale"] = int(zone.get("second_base_noise_scale", 24))
                _v6kw["second_base_scale"] = float(zone.get("second_base_scale", 1.0))
                _v6kw["second_base_pattern"] = zone.get("second_base_pattern")
                # Keep react-to-pattern overlays spatially aligned with the primary pattern scale.
                _v6kw["second_base_pattern_scale"] = float(zone.get("second_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["second_base_pattern_rotation"] = float(zone.get("second_base_pattern_rotation", 0.0))
                _v6kw["second_base_pattern_opacity"] = float(zone.get("second_base_pattern_opacity", 1.0))
                _v6kw["second_base_pattern_strength"] = float(zone.get("second_base_pattern_strength", 1.0))
                _v6kw["second_base_pattern_invert"] = bool(zone.get("second_base_pattern_invert", False))
                _v6kw["second_base_pattern_harden"] = bool(zone.get("second_base_pattern_harden", False))
                _sb_ox = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                _sb_oy = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                _sb_pscale = _v6kw["second_base_pattern_scale"]
                # Fit-to-Zone for 2nd base overlay
                if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _sb_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _sb_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _sb_pscale = _sb_pscale / _ft_ratio
                _v6kw["second_base_pattern_offset_x"] = _sb_ox
                _v6kw["second_base_pattern_offset_y"] = _sb_oy
                _v6kw["second_base_pattern_scale"] = _sb_pscale
            _v6kw["second_base_hue_shift"] = float(zone.get("second_base_hue_shift", 0))
            _v6kw["second_base_saturation"] = float(zone.get("second_base_saturation", 0))
            _v6kw["second_base_brightness"] = float(zone.get("second_base_brightness", 0))
            _v6kw["second_base_pattern_hue_shift"] = float(zone.get("second_base_pattern_hue_shift", 0))
            _v6kw["second_base_pattern_saturation"] = float(zone.get("second_base_pattern_saturation", 0))
            _v6kw["second_base_pattern_brightness"] = float(zone.get("second_base_pattern_brightness", 0))
            _v6kw["second_base_color_source"] = zone.get("second_base_color_source")
            _z_tb = zone.get("third_base")
            if _z_tb:
                _v6kw["third_base"] = _z_tb
                _v6kw["third_base_color"] = zone.get("third_base_color", [1.0, 1.0, 1.0])
                _v6kw["third_base_strength"] = float(zone.get("third_base_strength", 0.0))
                _v6kw["third_base_spec_strength"] = float(zone.get("third_base_spec_strength", 1.0))
                _v6kw["third_base_blend_mode"] = zone.get("third_base_blend_mode", "noise")
                _v6kw["third_base_noise_scale"] = int(zone.get("third_base_noise_scale", 24))
                _v6kw["third_base_scale"] = float(zone.get("third_base_scale", 1.0))
                _v6kw["third_base_pattern"] = zone.get("third_base_pattern")
                _v6kw["third_base_pattern_scale"] = float(zone.get("third_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["third_base_pattern_rotation"] = float(zone.get("third_base_pattern_rotation", 0.0))
                _v6kw["third_base_pattern_opacity"] = float(zone.get("third_base_pattern_opacity", 1.0))
                _v6kw["third_base_pattern_strength"] = float(zone.get("third_base_pattern_strength", 1.0))
                _v6kw["third_base_pattern_invert"] = bool(zone.get("third_base_pattern_invert", False))
                _v6kw["third_base_pattern_harden"] = bool(zone.get("third_base_pattern_harden", False))
                _tb_ox = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_x", 0.5))))
                _tb_oy = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_y", 0.5))))
                _tb_pscale = _v6kw["third_base_pattern_scale"]
                # Fit-to-Zone for 3rd base overlay
                if zone.get("third_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _tb_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _tb_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _tb_pscale = _tb_pscale / _ft_ratio
                _v6kw["third_base_pattern_offset_x"] = _tb_ox
                _v6kw["third_base_pattern_offset_y"] = _tb_oy
                _v6kw["third_base_pattern_scale"] = _tb_pscale
            _v6kw["third_base_hue_shift"] = float(zone.get("third_base_hue_shift", 0))
            _v6kw["third_base_saturation"] = float(zone.get("third_base_saturation", 0))
            _v6kw["third_base_brightness"] = float(zone.get("third_base_brightness", 0))
            _v6kw["third_base_color_source"] = zone.get("third_base_color_source")
            _z_fb = zone.get("fourth_base")
            if _z_fb:
                _v6kw["fourth_base"] = _z_fb
                _v6kw["fourth_base_color"] = zone.get("fourth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fourth_base_strength"] = float(zone.get("fourth_base_strength", 0.0))
                _v6kw["fourth_base_spec_strength"] = float(zone.get("fourth_base_spec_strength", 1.0))
                _v6kw["fourth_base_blend_mode"] = zone.get("fourth_base_blend_mode", "noise")
                _v6kw["fourth_base_noise_scale"] = int(zone.get("fourth_base_noise_scale", 24))
                _v6kw["fourth_base_scale"] = float(zone.get("fourth_base_scale", 1.0))
                _v6kw["fourth_base_pattern"] = zone.get("fourth_base_pattern")
                _v6kw["fourth_base_pattern_scale"] = float(zone.get("fourth_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["fourth_base_pattern_rotation"] = float(zone.get("fourth_base_pattern_rotation", 0.0))
                _v6kw["fourth_base_pattern_opacity"] = float(zone.get("fourth_base_pattern_opacity", 1.0))
                _v6kw["fourth_base_pattern_strength"] = float(zone.get("fourth_base_pattern_strength", 1.0))
                _v6kw["fourth_base_pattern_invert"] = bool(zone.get("fourth_base_pattern_invert", False))
                _v6kw["fourth_base_pattern_harden"] = bool(zone.get("fourth_base_pattern_harden", False))
                _fb_ox = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_x", 0.5))))
                _fb_oy = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_y", 0.5))))
                _fb_pscale = _v6kw["fourth_base_pattern_scale"]
                # Fit-to-Zone for 4th base overlay
                if zone.get("fourth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fb_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _fb_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _fb_pscale = _fb_pscale / _ft_ratio
                _v6kw["fourth_base_pattern_offset_x"] = _fb_ox
                _v6kw["fourth_base_pattern_offset_y"] = _fb_oy
                _v6kw["fourth_base_pattern_scale"] = _fb_pscale
            _v6kw["fourth_base_hue_shift"] = float(zone.get("fourth_base_hue_shift", 0))
            _v6kw["fourth_base_saturation"] = float(zone.get("fourth_base_saturation", 0))
            _v6kw["fourth_base_brightness"] = float(zone.get("fourth_base_brightness", 0))
            _v6kw["fourth_base_color_source"] = zone.get("fourth_base_color_source")
            _z_fif = zone.get("fifth_base")
            if _z_fif:
                _v6kw["fifth_base"] = _z_fif
                _v6kw["fifth_base_color"] = zone.get("fifth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fifth_base_strength"] = float(zone.get("fifth_base_strength", 0.0))
                _v6kw["fifth_base_spec_strength"] = float(zone.get("fifth_base_spec_strength", 1.0))
                _v6kw["fifth_base_blend_mode"] = zone.get("fifth_base_blend_mode", "noise")
                _v6kw["fifth_base_noise_scale"] = int(zone.get("fifth_base_noise_scale", 24))
                _v6kw["fifth_base_scale"] = float(zone.get("fifth_base_scale", 1.0))
                _v6kw["fifth_base_pattern"] = zone.get("fifth_base_pattern")
                _v6kw["fifth_base_pattern_scale"] = float(zone.get("fifth_base_pattern_scale", 1.0)) * auto_scale
                _v6kw["fifth_base_pattern_rotation"] = float(zone.get("fifth_base_pattern_rotation", 0.0))
                _v6kw["fifth_base_pattern_opacity"] = float(zone.get("fifth_base_pattern_opacity", 1.0))
                _v6kw["fifth_base_pattern_strength"] = float(zone.get("fifth_base_pattern_strength", 1.0))
                _v6kw["fifth_base_pattern_invert"] = bool(zone.get("fifth_base_pattern_invert", False))
                _v6kw["fifth_base_pattern_harden"] = bool(zone.get("fifth_base_pattern_harden", False))
                _fif_ox = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_x", 0.5))))
                _fif_oy = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_y", 0.5))))
                _fif_pscale = _v6kw["fifth_base_pattern_scale"]
                # Fit-to-Zone for 5th base overlay
                if zone.get("fifth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fif_ox = (_ftc_min + _ftc_max) / 2.0 / w
                            _fif_oy = (_ftr_min + _ftr_max) / 2.0 / h
                            _fif_pscale = _fif_pscale / _ft_ratio
                _v6kw["fifth_base_pattern_offset_x"] = _fif_ox
                _v6kw["fifth_base_pattern_offset_y"] = _fif_oy
                _v6kw["fifth_base_pattern_scale"] = _fif_pscale
            _v6kw["fifth_base_hue_shift"] = float(zone.get("fifth_base_hue_shift", 0))
            _v6kw["fifth_base_saturation"] = float(zone.get("fifth_base_saturation", 0))
            _v6kw["fifth_base_brightness"] = float(zone.get("fifth_base_brightness", 0))
            _v6kw["fifth_base_color_source"] = zone.get("fifth_base_color_source")
            _v6kw["monolithic_registry"] = MONOLITHIC_REGISTRY

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                # (prevents double-rendering at zone_scale=1.0 which overwhelms the stack's scale)
                stack_ids = {ps.get("id") for ps in pattern_stack[:4] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation,
                                         "offset_x": float(zone.get("pattern_offset_x", 0.5)),
                                         "offset_y": float(zone.get("pattern_offset_y", 0.5))})
                for ps in pattern_stack[:4]:  # Max 4 additional (matches JS MAX_PATTERN_STACK_LAYERS)
                    pid = ps.get("id", "none")
                    _pid_in_reg = pid in PATTERN_REGISTRY
                    print(f"    [STACK] Pattern layer: id='{pid}' in_registry={_pid_in_reg}")
                    if not _pid_in_reg and pid != "none":
                        # Try common ID transformations
                        _alt_id = pid.replace(" ", "_").replace("-", "_")
                        if _alt_id in PATTERN_REGISTRY:
                            print(f"    [STACK] Found as '{_alt_id}' — using that instead")
                            pid = _alt_id
                            _pid_in_reg = True
                    if pid != "none" and _pid_in_reg:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)) * auto_scale,  # Auto-scale stack layers too
                            "rotation": float(ps.get("rotation", 0)),
                            "blend_mode": ps.get("blend_mode", "normal"),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%{"["+p.get("blend_mode","normal")+"]" if p.get("blend_mode","normal") != "normal" else ""}' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                bs_label = f" base@{zone_base_scale:.2f}x" if zone_base_scale != 1.0 else ""
                print(f"    [{name}] => {label} ({intensity}){bs_label} [stacked compositing]")
                # v6.1: build blend paint kwargs
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_color_fit_zone": _v6kw.get("base_color_fit_zone", False), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0), "pattern_intensity": pattern_intensity_01}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5); _v6paint["second_base_hue_shift"] = _v6kw.get("second_base_hue_shift", 0); _v6paint["second_base_saturation"] = _v6kw.get("second_base_saturation", 0); _v6paint["second_base_brightness"] = _v6kw.get("second_base_brightness", 0); _v6paint["second_base_pattern_hue_shift"] = _v6kw.get("second_base_pattern_hue_shift", 0); _v6paint["second_base_pattern_saturation"] = _v6kw.get("second_base_pattern_saturation", 0); _v6paint["second_base_pattern_brightness"] = _v6kw.get("second_base_pattern_brightness", 0)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5); _v6paint["third_base_hue_shift"] = _v6kw.get("third_base_hue_shift", 0); _v6paint["third_base_saturation"] = _v6kw.get("third_base_saturation", 0); _v6paint["third_base_brightness"] = _v6kw.get("third_base_brightness", 0)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5); _v6paint["fourth_base_hue_shift"] = _v6kw.get("fourth_base_hue_shift", 0); _v6paint["fourth_base_saturation"] = _v6kw.get("fourth_base_saturation", 0); _v6paint["fourth_base_brightness"] = _v6kw.get("fourth_base_brightness", 0)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5); _v6paint["fifth_base_hue_shift"] = _v6kw.get("fifth_base_hue_shift", 0); _v6paint["fifth_base_saturation"] = _v6kw.get("fifth_base_saturation", 0); _v6paint["fifth_base_brightness"] = _v6kw.get("fifth_base_brightness", 0)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                _v6paint["base_offset_x"] = _v6kw.get("base_offset_x", 0.5)
                _v6paint["base_offset_y"] = _v6kw.get("base_offset_y", 0.5)
                _v6paint["base_rotation"] = _v6kw.get("base_rotation", 0)
                _v6paint["base_flip_h"] = _v6kw.get("base_flip_h", False)
                _v6paint["base_flip_v"] = _v6kw.get("base_flip_v", False)
                _v6paint["pattern_offset_x"] = _v6kw.get("pattern_offset_x", 0.5)
                _v6paint["pattern_offset_y"] = _v6kw.get("pattern_offset_y", 0.5)
                if all_patterns:
                    # Parallel: spec in background thread while paint mod runs in foreground
                    if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                        _spec_ex = _shared_spec_pool
                        _spec_fut = _spec_ex.submit(compose_finish_stacked, base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                        _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                        if _paint_was_gpu: paint = to_cpu(paint)
                        paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                        if _paint_was_gpu: paint = to_gpu(paint)
                        zone_spec = _spec_fut.result()
                else:
                    # Parallel: spec in background thread while paint mod runs in foreground
                    if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                        _spec_ex = _shared_spec_pool
                        _spec_fut = _spec_ex.submit(compose_finish, base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                        _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                        if _paint_was_gpu: paint = to_cpu(paint)
                        paint = compose_paint_mod(base_id, "none", paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                        if _paint_was_gpu: paint = to_gpu(paint)
                        zone_spec = _spec_fut.result()
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.2f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                bs_label = f" base@{zone_base_scale:.2f}x" if zone_base_scale != 1.0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}{bs_label} [compositing]")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_color_fit_zone": _v6kw.get("base_color_fit_zone", False), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0), "pattern_intensity": pattern_intensity_01}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5); _v6paint["second_base_hue_shift"] = _v6kw.get("second_base_hue_shift", 0); _v6paint["second_base_saturation"] = _v6kw.get("second_base_saturation", 0); _v6paint["second_base_brightness"] = _v6kw.get("second_base_brightness", 0); _v6paint["second_base_pattern_hue_shift"] = _v6kw.get("second_base_pattern_hue_shift", 0); _v6paint["second_base_pattern_saturation"] = _v6kw.get("second_base_pattern_saturation", 0); _v6paint["second_base_pattern_brightness"] = _v6kw.get("second_base_pattern_brightness", 0)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5); _v6paint["third_base_hue_shift"] = _v6kw.get("third_base_hue_shift", 0); _v6paint["third_base_saturation"] = _v6kw.get("third_base_saturation", 0); _v6paint["third_base_brightness"] = _v6kw.get("third_base_brightness", 0)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5); _v6paint["fourth_base_hue_shift"] = _v6kw.get("fourth_base_hue_shift", 0); _v6paint["fourth_base_saturation"] = _v6kw.get("fourth_base_saturation", 0); _v6paint["fourth_base_brightness"] = _v6kw.get("fourth_base_brightness", 0)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5); _v6paint["fifth_base_hue_shift"] = _v6kw.get("fifth_base_hue_shift", 0); _v6paint["fifth_base_saturation"] = _v6kw.get("fifth_base_saturation", 0); _v6paint["fifth_base_brightness"] = _v6kw.get("fifth_base_brightness", 0)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                _v6paint["base_offset_x"] = _v6kw.get("base_offset_x", 0.5)
                _v6paint["base_offset_y"] = _v6kw.get("base_offset_y", 0.5)
                _v6paint["base_rotation"] = _v6kw.get("base_rotation", 0)
                _v6paint["base_flip_h"] = _v6kw.get("base_flip_h", False)
                _v6paint["base_flip_v"] = _v6kw.get("base_flip_v", False)
                # Parallel: spec in background thread while paint mod runs in foreground
                if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                    _spec_ex = _shared_spec_pool
                    _spec_fut = _spec_ex.submit(compose_finish, base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                    _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                    if _paint_was_gpu: paint = to_cpu(paint)
                    paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation, **_v6paint)
                    if _paint_was_gpu: paint = to_gpu(paint)
                    zone_spec = _spec_fut.result()

        elif finish_name and zone.get("finish_colors") and (
            finish_name.startswith("grad_") or finish_name.startswith("gradm_")
            or finish_name.startswith("grad3_") or finish_name.startswith("ghostg_")
            or finish_name.startswith("mc_")
        ):
            # PATH 4 first for client-defined gradient types - client colors always win over registry
            zone_rotation = float(zone.get("rotation", 0))
            _engine_rot_debug(f"  [{name}] -> PATH 4 (generic, client gradient): finish={finish_name}, rotation={zone_rotation}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is not None: zone_spec = _sanitize_spec_result(zone_spec, shape)
            if paint is not None: paint = _sanitize_paint_result(paint, shape)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult if 'spec_mult' in dir() else 1.0, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)

        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            _engine_rot_debug(f"  [{name}] -> PATH 2 (monolithic): finish={finish_name}")
            # PATH 2: MONOLITHIC - special finishes (now with optional pattern overlay!)
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_pat_scale = float(zone.get("scale", 1.0))
            mono_pat_opacity = float(zone.get("pattern_opacity", 1.0))
            # SMART AUTO-SCALE for monolithic pattern overlay
            mono_auto_scale = _compute_zone_auto_scale(zone_mask, shape)
            mono_pat_scale *= mono_auto_scale
            mono_pat_rotation = float(zone.get("rotation", 0))
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            bs_label = f" base@{mono_base_scale:.2f}x" if mono_base_scale != 1.0 else ""
            logger.debug(f"    [{name}] => {finish_name}{pat_label} ({intensity}){bs_label} [monolithic]")

            _mono_base_strength = max(0.0, min(2.0, float(zone.get("base_strength", 1.0))))
            _mono_spec_strength = max(0.0, min(2.0, float(zone.get("base_spec_strength", 1.0))))
            # Combined: base_strength affects paint, spec_strength affects spec map
            _sm_effective = sm * _mono_base_strength * _mono_spec_strength
            _pm_effective = pm * _mono_base_strength
            _bb_effective = bb * _mono_base_strength
            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            try:
                if mono_base_scale != 1.0 and mono_base_scale > 0:
                    MAX_MONO_DIM = 4096
                    tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                    tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                    tile_shape = (tile_h, tile_w)
                    tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                    tile_spec = _sanitize_spec_result(spec_fn(tile_shape, tile_mask, seed + i * 13, _sm_effective), tile_shape)
                    reps_h = int(np.ceil(shape[0] / tile_h))
                    reps_w = int(np.ceil(shape[1] / tile_w))
                    zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                    paint = paint_fn(paint, shape, zone_mask, seed + i * 13, _pm_effective, _bb_effective)
                else:
                    zone_spec = spec_fn(shape, zone_mask, seed + i * 13, _sm_effective)
                    paint = paint_fn(paint, shape, zone_mask, seed + i * 13, _pm_effective, _bb_effective)
            except Exception as _mono_err:
                logger.warning(f"    WARNING: Monolithic finish '{finish_name}' failed in {_format_zone_id(i, zone)}: {_mono_err}")
                import traceback
                logger.debug(traceback.format_exc())
                # Fall back to default spec (flat, non-crashing) — keep render alive.
                zone_spec = np.zeros((shape[0], shape[1], 4), dtype=np.float32)
                zone_spec[:,:,0] = 5; zone_spec[:,:,1] = 100; zone_spec[:,:,2] = CC_FLOOR; zone_spec[:,:,3] = 255

            # Safety: normalize dict/tuple/RGB specs before overlays touch channels.
            zone_spec = _sanitize_spec_result(zone_spec, shape)
            if isinstance(paint, dict):
                _p_arr = paint.get('paint', None)
                if isinstance(_p_arr, np.ndarray):
                    paint = _p_arr
                else:
                    logger.warning(f"    WARNING: paint for '{finish_name}' returned dict in {_format_zone_id(i, zone)}, restoring from backup")
                    paint = _paint_backup.copy() if '_paint_backup' in dir() else np.zeros((shape[0], shape[1], 3), dtype=np.float32)

            # Apply HSB adjustments to monolithic paint (same as base+pattern path)
            _mono_hue = float(zone.get("base_hue_offset", 0))
            _mono_sat = float(zone.get("base_saturation_adjust", 0))
            _mono_bri = float(zone.get("base_brightness_adjust", 0))
            if abs(_mono_hue) >= 0.5 or abs(_mono_sat) >= 0.5 or abs(_mono_bri) >= 0.5:
                paint = _apply_hsb_adjustments(paint, zone_mask, _mono_hue, _mono_sat, _mono_bri)

            # Optional pattern overlay on top of monolithic
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_pat_scale, mono_pat_opacity, spec_mult=spec_mult, rotation=mono_pat_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_pat_scale, mono_pat_opacity, rotation=mono_pat_rotation)

            # Pattern stack on monolithic: apply additional stacked patterns on top
            _mono_pattern_stack = zone.get("pattern_stack", [])
            if _mono_pattern_stack:
                for _mps_idx, _mps in enumerate(_mono_pattern_stack[:4]):  # Max 4 (JS MAX_PATTERN_STACK_LAYERS)
                    _mps_id = _mps.get("id", "none")
                    if _mps_id == "none" or _mps_id not in PATTERN_REGISTRY:
                        # Try underscore transformation for image-based patterns
                        _mps_alt = _mps_id.replace(" ", "_").replace("-", "_")
                        if _mps_alt in PATTERN_REGISTRY:
                            _mps_id = _mps_alt
                        else:
                            print(f"    [MONO STACK] Pattern '{_mps.get('id')}' not in registry, skipping")
                            continue
                    _mps_opacity = float(_mps.get("opacity", 1.0))
                    _mps_scale = float(_mps.get("scale", 1.0)) * mono_auto_scale
                    _mps_rotation = float(_mps.get("rotation", 0))
                    print(f"    [MONO STACK] Applying stacked pattern {_mps_idx+2}: '{_mps_id}' opacity={_mps_opacity} scale={_mps_scale}")
                    zone_spec = overlay_pattern_on_spec(zone_spec, _mps_id, shape, zone_mask, seed + i * 13 + 200 + _mps_idx * 31, sm, _mps_scale, _mps_opacity, spec_mult=spec_mult, rotation=_mps_rotation)
                    paint = overlay_pattern_paint(paint, _mps_id, shape, zone_mask, seed + i * 13 + 200 + _mps_idx * 31, pm, bb, _mps_scale, _mps_opacity, rotation=_mps_rotation)

            # Spec pattern stack on monolithic: apply spec patterns to zone_spec
            _mono_spec_patterns = zone.get("spec_pattern_stack", [])
            if _mono_spec_patterns:
                from engine.spec_patterns import PATTERN_CATALOG
                for _msp in _mono_spec_patterns:
                    _msp_name = _msp.get("pattern", "")
                    _msp_fn = PATTERN_CATALOG.get(_msp_name)
                    if _msp_fn is None:
                        continue
                    _msp_opacity = float(_msp.get("opacity", 0.5))
                    _msp_blend = _msp.get("blend_mode", "normal")
                    _msp_channels = _msp.get("channels", "MR")
                    _msp_scale = float(_msp.get("scale", 1.0))
                    _msp_rotation = float(_msp.get("rotation", 0))
                    _msp_range = float(_msp.get("range", 40.0))
                    _msp_params = _msp.get("params", {})
                    _msp_seed = seed + 5000 + hash(_msp_name) % 10000
                    if abs(_msp_scale - 1.0) > 0.01 and _msp_scale < 1.0:
                        # Generate at larger resolution for smooth downscale (no tile seams)
                        _inv = min(1.0 / _msp_scale, 8.0)
                        _gen_h = min(16384, max(shape[0], int(np.ceil(shape[0] * _inv))))
                        _gen_w = min(16384, max(shape[1], int(np.ceil(shape[1] * _inv))))
                        _msp_arr_big = _msp_fn((_gen_h, _gen_w), _msp_seed, sm, **_msp_params)
                        from PIL import Image as _PILImg
                        _msp_arr = np.array(_PILImg.fromarray(
                            (np.clip(_msp_arr_big, 0, 1) * 255).astype(np.uint8)
                        ).resize((shape[1], shape[0]), _PILImg.LANCZOS)).astype(np.float32) / 255.0
                    elif abs(_msp_scale - 1.0) > 0.01 and _msp_scale > 1.0:
                        _msp_arr = _msp_fn(shape, _msp_seed, sm, **_msp_params)
                        _msp_arr = _crop_center_array(_msp_arr, _msp_scale, shape[0], shape[1])
                    else:
                        _msp_arr = _msp_fn(shape, _msp_seed, sm, **_msp_params)
                    if abs(_msp_rotation) > 0.5:
                        _msp_arr = _rotate_single_array(_msp_arr, _msp_rotation, shape)
                    _msp_delta = (_msp_arr - 0.5) * 2.0
                    _msp_contrib = _msp_delta * _msp_range
                    _msp_M = zone_spec[:,:,0].astype(np.float32)
                    _msp_R = zone_spec[:,:,1].astype(np.float32)
                    _msp_CC = zone_spec[:,:,2].astype(np.float32)
                    if "M" in _msp_channels:
                        _msp_M = _apply_spec_blend_mode(_msp_M, _msp_contrib, _msp_opacity, _msp_blend)
                    if "R" in _msp_channels:
                        _msp_R = _apply_spec_blend_mode(_msp_R, _msp_contrib, _msp_opacity, _msp_blend)
                    if "C" in _msp_channels:
                        _msp_CC = _apply_spec_blend_mode(_msp_CC, _msp_contrib, _msp_opacity, _msp_blend)
                    zone_spec[:,:,0] = np.clip(_msp_M, 0, 255).astype(np.uint8)
                    zone_spec[:,:,1] = np.clip(_msp_R, 0, 255).astype(np.uint8)
                    zone_spec[:,:,2] = np.clip(_msp_CC, 16, 255).astype(np.uint8)
                    print(f"    [MONO SPEC] Applied spec pattern '{_msp_name}' opacity={_msp_opacity}")

            # Dual Layer Base Overlay on monolithic (same as base+pattern path)
            _z_sb = zone.get("second_base")
            _z_sb_color_src = zone.get("second_base_color_source")
            _z_sb_is_mono = _z_sb and str(_z_sb).startswith("mono:")
            _z_sb_in_base = _z_sb and _z_sb in BASE_REGISTRY
            _z_sb_in_mono = _z_sb_is_mono and _z_sb[5:] in MONOLITHIC_REGISTRY
            _z_sb_src_is_mono = _z_sb_color_src and str(_z_sb_color_src).startswith("mono:") and _z_sb_color_src[5:] in MONOLITHIC_REGISTRY
            _z_sb_str = float(zone.get("second_base_strength", 0))
            print(f"    [{name}] OVERLAY CHECK: sb='{_z_sb}', src='{_z_sb_color_src}', is_mono={_z_sb_is_mono}, in_base={_z_sb_in_base}, in_mono={_z_sb_in_mono}, src_in_mono={_z_sb_src_is_mono}, strength={_z_sb_str}")
            if (_z_sb_in_base or _z_sb_in_mono or _z_sb_src_is_mono) and _z_sb_str > 0.001:
                try:
                    _sb_strength = float(zone.get("second_base_strength", 0))
                    _has_sb_spec = bool(_z_sb_in_base or _z_sb_in_mono)
                    spec_secondary = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
                    if _z_sb_in_mono:
                        # Special finish as overlay - use its spec_fn
                        _mono_id = _z_sb[5:]
                        _sb_spec_fn = MONOLITHIC_REGISTRY[_mono_id][0]
                        _sb_seed_off = abs(hash(_z_sb)) % 10000
                        spec_secondary = _sanitize_spec_result(_sb_spec_fn(shape, zone_mask, seed + i * 13 + _sb_seed_off, sm), shape)
                        print(f"    [{name}] 2nd base overlay: MONO spec '{_mono_id}'")
                    else:
                        # Regular base as overlay - existing logic
                        _sb_def = BASE_REGISTRY[_z_sb]
                        _sb_M = float(_sb_def["M"])
                        _sb_R = float(_sb_def["R"])
                        _sb_CC = int(_sb_def.get("CC", 16))
                        _sb_seed_off = abs(hash(_z_sb)) % 10000
                        if _sb_def.get("base_spec_fn"):
                            _sb_result = _sb_def["base_spec_fn"](shape, seed + i * 13 + _sb_seed_off, sm, _sb_M, _sb_R)
                            _sb_M_arr = _sb_result[0]
                            _sb_R_arr = _sb_result[1]
                            _sb_CC_arr = _sb_result[2] if len(_sb_result) > 2 else np.full(shape, float(_sb_CC))
                        elif _sb_def.get("perlin"):
                            _sb_noise = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed + i * 13 + _sb_seed_off)
                            _sb_M_arr = _sb_M + _sb_noise * _sb_def.get("noise_M", 0) * sm
                            _sb_R_arr = _sb_R + _sb_noise * _sb_def.get("noise_R", 0) * sm
                            _sb_CC_arr = np.full(shape, float(_sb_CC))
                        else:
                            _sb_M_arr = np.full(shape, _sb_M)
                            _sb_R_arr = np.full(shape, _sb_R)
                            _sb_CC_arr = np.full(shape, float(_sb_CC))
                        _sb_M_final = _sb_M_arr * zone_mask + 5.0 * (1 - zone_mask)
                        _sb_R_final = _sb_R_arr * zone_mask + 100.0 * (1 - zone_mask)
                        spec_secondary[:,:,0] = np.clip(_sb_M_final, 0, 255).astype(np.uint8)
                        spec_secondary[:,:,1] = np.clip(_sb_R_final, 0, 255).astype(np.uint8)
                        spec_secondary[:,:,2] = np.clip(_sb_CC_arr * zone_mask, 0, 255).astype(np.uint8)
                        spec_secondary[:,:,3] = 255
                    _sb_bm = zone.get("second_base_blend_mode", "noise")
                    # Use "React to zone pattern" (second_base_pattern) first; fallback to zone L1 pattern
                    _pat_id = zone.get("second_base_pattern") or zone.get("pattern") or zone.get("mono_pattern")
                    _sb_bm_norm = _normalize_second_base_blend_mode(_sb_bm)
                    # Build pattern mask for pattern, pattern_vivid, AND tint (so tint is pattern-driven, not uniform)
                    _sb_needs_mask = _sb_bm_norm in ("pattern", "pattern_vivid", "tint")
                    # Monolithic path: use same effective scale space as zone pattern overlay.
                    _sb_pat_scale = max(0.1, min(10.0, float(zone.get("second_base_pattern_scale", 1.0)) * mono_auto_scale))
                    _sb_pat_rot = float(zone.get("second_base_pattern_rotation", 0))
                    _sb_pat_op = zone.get("second_base_pattern_opacity", 1.0)
                    _sb_pat_op = min(1.0, float(_sb_pat_op)) if float(_sb_pat_op) > 1 else float(_sb_pat_op)
                    _sb_pat_str = max(0.0, min(2.0, float(zone.get("second_base_pattern_strength", 1.0))))
                    _sb_pat_ox = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                    _sb_pat_oy = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                    # Fit-to-Zone for 2nd base overlay (monolithic path)
                    if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                        _ftrows = np.any(zone_mask > 0.1, axis=1)
                        _ftcols = np.any(zone_mask > 0.1, axis=0)
                        if _ftrows.any() and _ftcols.any():
                            _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                            _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                            _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                            if _ft_ratio > 0.01:
                                _sb_pat_ox = (_ftc_min + _ftc_max) / 2.0 / w
                                _sb_pat_oy = (_ftr_min + _ftr_max) / 2.0 / h
                                _sb_pat_scale = _sb_pat_scale / _ft_ratio
                    _pat_mask = _get_pattern_mask(_pat_id, shape, zone_mask, seed + i * 13, sm, scale=_sb_pat_scale, rotation=_sb_pat_rot, opacity=_sb_pat_op, strength=_sb_pat_str, offset_x=_sb_pat_ox, offset_y=_sb_pat_oy) if _sb_needs_mask and _pat_id else None
                    if _pat_mask is not None:
                        if zone.get("second_base_pattern_invert"):
                            _pat_mask = 1.0 - _pat_mask
                        if zone.get("second_base_pattern_harden"):
                            _pat_mask = np.clip((_pat_mask.astype(np.float32) - 0.45) / 0.15, 0, 1)
                    if _has_sb_spec:
                        zone_spec, _ = blend_dual_base_spec(
                            zone_spec, spec_secondary,
                            strength=_sb_strength,
                            blend_mode=_sb_bm,
                            noise_scale=int(zone.get("second_base_noise_scale", 24)),
                            seed=seed + i * 13,
                            pattern_mask=_pat_mask,
                            zone_mask=zone_mask
                        )
                    # Paint side: tint overlay with second_base_color and blend
                    hard_mask = np.where(zone_mask > 0.5, zone_mask, 0.0).astype(np.float32)
                    paint_overlay = paint.copy()
                    _sb_mask3d = hard_mask[:, :, np.newaxis]
                    _sb_src_mono_id = None
                    if _z_sb_src_is_mono:
                        _sb_src_mono_id = _z_sb_color_src[5:]
                    elif _z_sb_in_mono and MONOLITHIC_REGISTRY.get(_z_sb[5:]):
                        _sb_src_mono_id = _z_sb[5:]
                    if _sb_src_mono_id and MONOLITHIC_REGISTRY.get(_sb_src_mono_id):
                        # Use the mono's paint_fn - it generates its own colors
                        # from a neutral seed so strong underlying bases (e.g. prizm_duochrome)
                        # don't swallow overlay identity.
                        _mono_paint_fn = MONOLITHIC_REGISTRY[_sb_src_mono_id][1]
                        _seed_paint = np.full_like(paint[:, :, :3], 0.533, dtype=np.float32)
                        _color_paint = _mono_paint_fn(_seed_paint, shape, hard_mask, seed + i * 13 + 7777, 1.0, 0.0)
                        if _color_paint is not None:
                            paint_overlay[:, :, :3] = _color_paint[:, :, :3]
                        print(f"    [{name}] 2nd base overlay: MONO color source '{_sb_src_mono_id}'")
                    else:
                        _sb_color = zone.get("second_base_color", [1.0, 1.0, 1.0])
                        if _sb_color is not None and len(_sb_color) >= 3:
                            _sb_r = float(_sb_color[0])
                            _sb_g = float(_sb_color[1])
                            _sb_b = float(_sb_color[2])
                            _sb_rgb = np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                            paint_overlay[:, :, :3] = paint_overlay[:, :, :3] * (1.0 - _sb_mask3d) + _sb_rgb * _sb_mask3d
                            if _z_sb_in_base:
                                _sb_def = BASE_REGISTRY[_z_sb]
                                _sb_pfn = _sb_def.get("paint_fn", paint_none)
                                if _sb_pfn is not paint_none:
                                    paint_overlay = _sb_pfn(paint_overlay, shape, hard_mask, seed + i * 13 + 7777, 1.0, 1.0)
                                # Apply user's overlay color after paint_fn so the chosen tint is always visible (Fix 2)
                                paint_overlay[:, :, :3] *= np.array([_sb_r, _sb_g, _sb_b], dtype=np.float32)
                    _sb_ns = int(zone.get("second_base_noise_scale", 24))
                    _sb_bm = zone.get("second_base_blend_mode", "noise")
                    _sb_bm_norm = _normalize_second_base_blend_mode(_sb_bm)
                    if _sb_bm_norm in ("pattern", "pattern_vivid", "tint"):
                        _blend_w = _get_pattern_mask(_pat_id, shape, hard_mask, seed + i * 13, 1.0, scale=_sb_pat_scale, rotation=_sb_pat_rot, opacity=_sb_pat_op, strength=_sb_pat_str, offset_x=_sb_pat_ox, offset_y=_sb_pat_oy) if _pat_id else None
                        if _blend_w is None:
                            _blend_w = np.full(shape, _sb_strength, dtype=np.float32)
                        else:
                            if zone.get("second_base_pattern_invert"):
                                _blend_w = 1.0 - _blend_w
                            if zone.get("second_base_pattern_harden"):
                                _blend_w = np.clip((_blend_w.astype(np.float32) - 0.45) / 0.15, 0, 1)
                            if _sb_bm_norm == "pattern_vivid":
                                _thr = np.clip(1.0 - float(_sb_strength), 0.0, 1.0)
                                _blend_w = np.clip((_blend_w - _thr) / max(0.08, 1e-4), 0.0, 1.0).astype(np.float32)
                            elif _sb_bm_norm == "tint":
                                _blend_w = np.clip(_blend_w * _sb_strength * 0.35, 0, 1).astype(np.float32)
                            else:
                                _blend_w = _blend_w * _sb_strength
                    elif _sb_bm_norm == "noise":
                        _nz = multi_scale_noise(shape, [_sb_ns, _sb_ns * 2, _sb_ns * 4], [0.5, 0.3, 0.2], seed + 1234)
                        _blend_w = np.clip(_nz, 0, 1).astype(np.float32)
                    else:
                        _blend_w = np.ones(shape, dtype=np.float32)
                    _blend_w = _blend_w * hard_mask
                    # Pattern-Pop / Tint: alpha already scaled in _blend_w; use 1.0 for pattern/tint/pop
                    _mul = 1.0 if _sb_bm_norm in ("pattern", "pattern_vivid", "tint") else _sb_strength
                    _blend_w3d = (_blend_w * _mul)[:, :, np.newaxis]
                    # Use overlay RGB only so 3-channel paint never shape-mismatches (overlay may be 4-ch from paint_fn)
                    paint[:, :, :3] = paint[:, :, :3] * (1.0 - _blend_w3d) + paint_overlay[:, :, :3] * _blend_w3d
                except Exception as _e:
                    import traceback
                    print(f"    [{name}] 2nd base overlay ERROR: {_e}")
                    traceback.print_exc()

        elif finish_name and finish_name in FINISH_REGISTRY:
            _engine_rot_debug(f"  [{name}] -> PATH 3 (legacy): finish={finish_name}")
            # PATH 3: LEGACY - backward compat with original FINISH_REGISTRY
            spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
            print(f"    [{name}] => {finish_name} ({intensity}) [legacy]")
            try:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, sm)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, pm, bb)
                zone_spec = _sanitize_spec_result(zone_spec, shape)
                paint = _sanitize_paint_result(paint, shape)
            except Exception as _legacy_err:
                logger.warning(f"    WARNING: Legacy finish '{finish_name}' failed in {_format_zone_id(i, zone)}: {_legacy_err}")
                zone_spec = np.zeros((shape[0], shape[1], 4), dtype=np.float32)
                zone_spec[:,:,0] = 5; zone_spec[:,:,1] = 100; zone_spec[:,:,2] = CC_FLOOR; zone_spec[:,:,3] = 255

        elif finish_name and zone.get("finish_colors"):
            # PATH 4: GENERIC FALLBACK - client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            _engine_rot_debug(f"  [{name}] -> PATH 4 (generic fallback): finish={finish_name}, rotation={zone_rotation}, fc_keys={list(zone.get('finish_colors',{}).keys())}")
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is not None: zone_spec = _sanitize_spec_result(zone_spec, shape)
            if paint is not None: paint = _sanitize_paint_result(paint, shape)
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
            _similar_finish = _suggest_similar_ids(label, FINISH_REGISTRY) + _suggest_similar_ids(label, MONOLITHIC_REGISTRY) + _suggest_similar_ids(label, BASE_REGISTRY)
            _hint_f = f"\n      Did you mean: {', '.join(dict.fromkeys(_similar_finish).keys())}" if _similar_finish else ""
            logger.warning(f"    WARNING: Unknown finish/base '{label}' in {_format_zone_id(i, zone)}, skipping.{_hint_f}")
            continue

        # ---- Store zone result in cache (preview_mode only) ----
        if preview_mode and _zone_cache_key and _paint_before is not None:
            try:
                _paint_delta = (paint - _paint_before).astype(np.float32)
                build_multi_zone._zone_cache[_zone_cache_key] = {
                    'zone_spec': zone_spec.copy(),
                    'paint_delta': _paint_delta,
                    'mask': zone_mask.copy(),
                }
                # Limit cache size: keep at most 64 zone entries (avoids unbounded RAM growth)
                if len(build_multi_zone._zone_cache) > 64:
                    _oldest = next(iter(build_multi_zone._zone_cache))
                    del build_multi_zone._zone_cache[_oldest]
            except Exception as _cse:
                pass  # Cache store failure is non-fatal

        # ---- Export layers: capture per-zone spec + paint before compositing (#21) ----
        if _export_zone_layers is not None:
            try:
                # Capture zone spec (masked to zone area only)
                _ez_mask3d = zone_mask[:, :, np.newaxis]
                _ez_spec = (zone_spec.astype(np.float32) * (_ez_mask3d > 0.05).astype(np.float32)).astype(np.uint8)
                # Capture zone paint (current paint state, masked)
                _ez_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
                if _ez_paint.shape[2] == 4:
                    _ez_paint = _ez_paint[:, :, :3]
                _ez_paint_masked = (_ez_paint.astype(np.float32) * (_ez_mask3d[:, :, :3] > 0.05 if _ez_mask3d.shape[2] == 1 else _ez_mask3d > 0.05).astype(np.float32)).astype(np.uint8)
                _export_zone_layers.append({
                    "zone_index": i,
                    "zone_name": name,
                    "spec": _ez_spec.copy(),
                    "paint": _ez_paint_masked.copy(),
                    "mask": zone_mask.copy(),
                })
            except Exception as _exl_err:
                logger.warning(f"    [export_layers] WARNING: capture failed for {_format_zone_id(i, zone)}: {_exl_err}")

        # Apply zone spec with hard ownership: where mask is strong, fully replace
        # Vectorized across all 4 channels at once for speed
        # GPU-accelerated when CuPy is available
        if is_gpu():
            _zs_g = to_gpu(zone_spec.astype(np.float32))
            _m3d_g = to_gpu(zone_mask[:,:,np.newaxis])
            _cs_g = to_gpu(combined_spec)
            hard_edge = zone.get("hard_edge", False)
            if hard_edge:
                combined_spec = to_cpu(xp.where(_m3d_g > 0.01, _zs_g, _cs_g))
            else:
                strong = _m3d_g > 0.5
                soft = (_m3d_g > 0.05) & ~strong
                blended = xp.clip(_zs_g * _m3d_g + _cs_g * (1 - _m3d_g), 0, 255)
                combined_spec = to_cpu(xp.where(strong, _zs_g, xp.where(soft, blended, _cs_g)))
        else:
            mask3d = zone_mask[:,:,np.newaxis]  # (h, w, 1)
            hard_edge = zone.get("hard_edge", False)
            if hard_edge:
                combined_spec = np.where(mask3d > 0.01, zone_spec.astype(np.float32), combined_spec)
            else:
                strong = mask3d > 0.5
                soft = (mask3d > 0.05) & ~strong
                blended = np.clip(
                    zone_spec.astype(np.float32) * mask3d +
                    combined_spec * (1 - mask3d),
                    0, 255
                )
                combined_spec = np.where(strong, zone_spec.astype(np.float32), np.where(soft, blended, combined_spec))

        _zone_elapsed = time.time() - t_zone
        _zone_pct = _zone_coverage * 100 if '_zone_coverage' in dir() else float(np.mean(zone_mask > 0.1)) * 100
        print(f"    [Zone {i+1}] \"{name}\" rendered in {_zone_elapsed:.2f}s ({_zone_pct:.1f}% of pixels)")

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
            combined_spec.astype(np.uint8), (np.clip(paint, 0, 1) * 255).astype(np.uint8),
            max_wear, seed + 777
        )
        worn_spec_f = worn_spec.astype(np.float32)
        # Blend worn results per zone, scaled by each zone's wear fraction
        for zi, zone, zm, wl in wear_zones:
            wear_frac = wl / max_wear  # 0.0-1.0 how much of the max wear this zone gets
            mask_bool = zm > 0.5
            mask3d = mask_bool[:,:,np.newaxis]
            # Interpolate between unworn and worn based on wear fraction
            if wear_frac >= 0.99:
                # Full strength - just swap
                combined_spec = np.where(mask3d, worn_spec_f, combined_spec)
                paint = np.where(mask3d, worn_paint.astype(np.float32) / 255.0, paint)
            else:
                # Partial strength - lerp between original and worn (all float32)
                spec_lerp = np.clip(
                    combined_spec * (1 - wear_frac) +
                    worn_spec_f * wear_frac, 0, 255
                )
                paint_lerp = np.clip(
                    paint * (1 - wear_frac) +
                    worn_paint.astype(np.float32) / 255.0 * wear_frac, 0, 1
                )
                combined_spec = np.where(mask3d, spec_lerp, combined_spec)
                paint = np.where(mask3d, paint_lerp, paint)
            print(f"    Zone {zi+1} [{zone['name']}]: wear {wl}% (frac={wear_frac:.2f})")
        print(f"  Batched wear applied in {time.time()-t_wear:.2f}s")

    print(f"  All finishes applied: {time.time()-t_finishes:.2f}s")

    # ---- DECAL SPEC FINISHES: Apply spec to decal regions ----
    if decal_spec_finishes and decal_paint_path and os.path.exists(decal_paint_path):
        print(f"\n  Applying decal spec finishes ({len(decal_spec_finishes)} entries)...")
        t_decal_spec = time.time()
        try:
            from engine.spec_paint import (spec_gloss, spec_matte, spec_satin,
                spec_metallic, spec_pearl, spec_chrome, spec_satin_metal,
                spec_carbon_fiber, spec_brushed_titanium, spec_anodized, spec_frozen)
            # 2026-04-22 HEENAN FAMILY overnight — Foundation trust fix.
            #
            # Foundation f_* ids selected as a decal specFinish (via the UI
            # dropdown in paint-booth-6-ui-boot.js) used to dispatch through
            # engine.spec_paint.spec_metallic / spec_pearl / spec_chrome /
            # spec_carbon_fiber / spec_satin_metal / spec_brushed_titanium /
            # spec_anodized / spec_frozen. Those were WRONG for two reasons:
            #
            #   1. Several produced visible per-pixel texture on the decal
            #      region's spec map (spec_metallic M-spread=80, spec_pearl
            #      M-spread=168, spec_carbon_fiber R-spread=50). That
            #      contradicted the Foundation Base flat-spec contract:
            #      "a foundation never adds its own texture; it's a pure
            #      material property — flat M/R/CC everywhere."
            #   2. The 5-arg signature functions (spec_satin_metal,
            #      spec_brushed_titanium, spec_anodized, spec_frozen) raised
            #      TypeError when invoked with the 4-arg `(shape, mask, seed,
            #      sm)` call at the dispatch site below. The outer try/except
            #      silently swallowed the error and the painter got no spec
            #      on their decal.
            #
            # Fix: every f_* id routes through the module-level
            # ``_mk_flat_foundation_decal_spec(fid)`` factory (defined near
            # the ``_spec_foundation_flat`` dispatcher above). The factory
            # returns a closure ignoring mask/seed/sm and emitting a
            # 4-channel uint8 spec using the foundation's own M/R/CC from
            # BASE_REGISTRY. Iter 5 hoisted this to module level so
            # behavioral tests can exercise it directly.
            #
            # The 7 "original hardcoded" entries + 12 classic non-f_
            # foundation ids below (gloss/matte/satin/semi_gloss/...) still
            # point at the broken 5-arg functions. Those are pre-existing
            # out-of-scope silent-TypeError cases documented for a separate
            # follow-up, not today's Foundation trust iter.
            # 2026-04-23 HEENAN FAMILY 6h Alpha-hardening Iter 3:
            # The behavioral probe at tests/_probe_decal_spec_map_dispatch.py
            # confirmed that 16 of 19 non-`f_` entries previously crashed
            # at this dispatch site with TypeError because engine.spec_paint
            # re-exports the paint_v2 5-arg signatures over the original
            # 4-arg ones for spec_gloss/matte/satin/satin_metal (the outer
            # try/except below silently swallowed the error → no decal spec).
            # The 4-arg-safe survivors are spec_metallic, spec_pearl,
            # spec_chrome, spec_carbon_fiber — those still render their
            # original textured spec. Every other legacy id now routes
            # through the new _mk_flat_legacy_decal_spec(M,R,CC) factory
            # for a flat 4-channel uint8 spec matching the original 4-arg
            # function's canonical M/R/CC. Painter-impact: legacy presets
            # with these specFinish values previously got NO decal spec;
            # they now get the intended flat spec. Strict improvement.
            DECAL_SPEC_MAP = {
                # Originally 4-arg, now 5-arg via paint_v2 re-export → flat shim.
                # M/R/CC values match the original engine/spec_paint.py 4-arg defs.
                "gloss":         _mk_flat_legacy_decal_spec(M=0,   R=20,  CC=16),
                "matte":         _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                "satin":         _mk_flat_legacy_decal_spec(M=0,   R=100, CC=50),
                "satin_metal":   _mk_flat_legacy_decal_spec(M=235, R=65,  CC=16),
                # Survivors — still 4-arg-safe in engine.spec_paint, render
                # with their original textured spec.
                "metallic": spec_metallic,
                "pearl":    spec_pearl,
                "chrome":   spec_chrome,
                # Foundation base IDs — classic finishes. Each pointed at the
                # corresponding (now-broken) gloss/matte/satin function before;
                # now point at the matching flat shim so their painter-intent
                # is honored.
                "clear_matte":   _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                "eggshell":      _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                "flat_black":    _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                "primer":        _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                "semi_gloss":    _mk_flat_legacy_decal_spec(M=0,   R=20,  CC=16),
                "silk":          _mk_flat_legacy_decal_spec(M=0,   R=100, CC=50),
                "wet_look":      _mk_flat_legacy_decal_spec(M=0,   R=20,  CC=16),
                "scuffed_satin": _mk_flat_legacy_decal_spec(M=0,   R=100, CC=50),
                "chalky_base":   _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                "living_matte":  _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                "ceramic":       _mk_flat_legacy_decal_spec(M=0,   R=100, CC=50),
                "piano_black":   _mk_flat_legacy_decal_spec(M=0,   R=20,  CC=16),
                # Foundation f_ prefixed bases — FLAT-SPEC SHIM (the actual
                # Iter 3 fix). Each entry returns a flat 4-channel uint8
                # spec using the foundation's own M/R/CC. Honors the
                # Foundation Base flat-spec contract.
                "f_pure_white":    _mk_flat_foundation_decal_spec("f_pure_white"),
                "f_pure_black":    _mk_flat_foundation_decal_spec("f_pure_black"),
                "f_neutral_grey":  _mk_flat_foundation_decal_spec("f_neutral_grey"),
                "f_soft_gloss":    _mk_flat_foundation_decal_spec("f_soft_gloss"),
                "f_soft_matte":    _mk_flat_foundation_decal_spec("f_soft_matte"),
                "f_clear_satin":   _mk_flat_foundation_decal_spec("f_clear_satin"),
                "f_warm_white":    _mk_flat_foundation_decal_spec("f_warm_white"),
                "f_chrome":        _mk_flat_foundation_decal_spec("f_chrome"),
                "f_satin_chrome":  _mk_flat_foundation_decal_spec("f_satin_chrome"),
                "f_metallic":      _mk_flat_foundation_decal_spec("f_metallic"),
                "f_pearl":         _mk_flat_foundation_decal_spec("f_pearl"),
                "f_carbon_fiber":  _mk_flat_foundation_decal_spec("f_carbon_fiber"),
                "f_brushed":       _mk_flat_foundation_decal_spec("f_brushed"),
                "f_frozen":        _mk_flat_foundation_decal_spec("f_frozen"),
                "f_powder_coat":   _mk_flat_foundation_decal_spec("f_powder_coat"),
                "f_anodized":      _mk_flat_foundation_decal_spec("f_anodized"),
                "f_vinyl_wrap":    _mk_flat_foundation_decal_spec("f_vinyl_wrap"),
                "f_gel_coat":      _mk_flat_foundation_decal_spec("f_gel_coat"),
                "f_baked_enamel":  _mk_flat_foundation_decal_spec("f_baked_enamel"),
            }
            # Load the composited paint (paint + decals baked in)
            decal_comp = Image.open(decal_paint_path).convert('RGBA')
            if decal_comp.size != (w, h):
                decal_comp = decal_comp.resize((w, h), Image.LANCZOS)
            decal_arr = np.array(decal_comp)

            # Prefer the separate decal-only alpha mask sent from the client.
            # The composite image has a fully-opaque paint background so its alpha
            # channel is 255 everywhere — useless as a mask. The dedicated mask
            # encodes only the decal pixels as grey values, which is what we need.
            if decal_mask_base64:
                try:
                    import base64 as _b64, io as _io
                    _raw = decal_mask_base64
                    if ',' in _raw:
                        _raw = _raw.split(',', 1)[1]
                    mask_img = Image.open(_io.BytesIO(_b64.b64decode(_raw))).convert('L')
                    if mask_img.size != (w, h):
                        mask_img = mask_img.resize((w, h), Image.LANCZOS)
                    decal_alpha = np.array(mask_img, dtype=np.float32) / 255.0
                    print(f"  Decal spec: using dedicated alpha mask ({decal_alpha.max():.3f} max)")
                except Exception as _me:
                    print(f"  Decal spec: mask decode failed ({_me}), falling back to composite alpha")
                    decal_alpha = decal_arr[:, :, 3].astype(np.float32) / 255.0
            else:
                # Fallback: extract alpha from composite (may be all-255 if paint has opaque bg)
                decal_alpha = decal_arr[:, :, 3].astype(np.float32) / 255.0

            if decal_alpha.max() > 0.01:
                # Use the first entry's spec finish for all decal areas
                # (all decals currently share one spec finish setting)
                spec_name = decal_spec_finishes[0].get("specFinish", "gloss")
                spec_fn = DECAL_SPEC_MAP.get(spec_name, spec_gloss)
                decal_spec = spec_fn((h, w), decal_alpha, seed + 7777, 1.0)

                # Blend decal spec onto combined_spec using decal alpha
                alpha4 = decal_alpha[:, :, np.newaxis]
                combined_spec = np.clip(
                    combined_spec * (1.0 - alpha4) +
                    decal_spec.astype(np.float32) * alpha4,
                    0, 255
                )

                decal_px = int(np.sum(decal_alpha > 0.01))
                print(f"  Decal spec applied: {decal_px:,} pixels, finish={spec_name}")
            else:
                print(f"  Decal spec skipped: no visible decal pixels in alpha channel")
        except Exception as e:
            print(f"  Decal Spec ERROR: {e}")
        print(f"  Decal spec time: {time.time()-t_decal_spec:.2f}s")

    # ---- SPEC STAMPS: Apply stamp overlays on top of ALL zones ----
    if stamp_image and os.path.exists(stamp_image):
        logger.info(f"\n  Applying spec stamp: {os.path.basename(stamp_image)} (finish={stamp_spec_finish})")
        t_stamp = time.time()
        try:
            stamp_img = Image.open(stamp_image).convert('RGBA')
            # Validate dimensions match canvas; resize if not. Log a one-line
            # heads-up so users know we resampled (LANCZOS = high quality).
            if stamp_img.size != (w, h):
                logger.info(
                    f"  Stamp resampled: {stamp_img.size[0]}x{stamp_img.size[1]} -> {w}x{h} (LANCZOS)"
                )
                stamp_img = stamp_img.resize((w, h), Image.LANCZOS)
            stamp_arr = np.array(stamp_img)
            stamp_alpha = stamp_arr[:, :, 3].astype(np.float32) / 255.0  # 0-1 mask
            stamp_rgb = stamp_arr[:, :, :3].astype(np.float32) / 255.0

            # Only process if stamp has any non-transparent pixels
            if np.max(stamp_alpha) > 0.01:
                # Generate spec for stamped area using chosen finish.
                # 2026-04-23 HEENAN FAMILY 6h Alpha-hardening Iter 4:
                # parallel fix to the Iter 3 DECAL_SPEC_MAP silent-no-op.
                # spec_gloss / spec_matte / spec_satin / spec_satin_metal
                # are re-exported from engine.paint_v2 with 5-arg signatures
                # — calling them with the 4-arg dispatch below raises
                # TypeError that the outer except silently swallows. Pre-fix,
                # painters using the stamp feature with the DEFAULT finish
                # ("gloss") got NO spec on their stamped pixels because the
                # `, spec_gloss)` fallback ALSO crashed. Fix routes the 4
                # broken keys through the same _mk_flat_legacy_decal_spec
                # factory that DECAL_SPEC_MAP now uses.
                from engine.spec_paint import (spec_metallic, spec_pearl, spec_chrome)
                STAMP_SPEC_MAP = {
                    # Originally 4-arg, now 5-arg via paint_v2 re-export → flat shim.
                    # M/R/CC values match the original engine/spec_paint.py 4-arg defs.
                    "gloss":       _mk_flat_legacy_decal_spec(M=0,   R=20,  CC=16),
                    "matte":       _mk_flat_legacy_decal_spec(M=0,   R=220, CC=200),
                    "satin":       _mk_flat_legacy_decal_spec(M=0,   R=100, CC=50),
                    "satin_metal": _mk_flat_legacy_decal_spec(M=235, R=65,  CC=16),
                    # 4-arg-safe survivors.
                    "metallic": spec_metallic,
                    "pearl":    spec_pearl,
                    "chrome":   spec_chrome,
                }
                # Safe-default fallback (was spec_gloss, which also crashed).
                _safe_default_stamp_spec = _mk_flat_legacy_decal_spec(M=0, R=20, CC=16)
                spec_fn = STAMP_SPEC_MAP.get(stamp_spec_finish, _safe_default_stamp_spec)
                stamp_spec = spec_fn((h, w), stamp_alpha, seed + 9999, 1.0)

                # Blend stamp onto paint (RGB channels only)
                alpha3 = stamp_alpha[:, :, np.newaxis]
                paint[:, :, :3] = paint[:, :, :3] * (1.0 - alpha3) + stamp_rgb * alpha3
                if paint.shape[2] > 3:
                    paint[:, :, 3] = np.maximum(paint[:, :, 3], stamp_alpha)

                # Blend stamp spec onto combined_spec (all 4 channels)
                alpha4 = stamp_alpha[:, :, np.newaxis]
                combined_spec = np.clip(
                    combined_spec * (1.0 - alpha4) +
                    stamp_spec.astype(np.float32) * alpha4,
                    0, 255
                )

                stamp_px = np.sum(stamp_alpha > 0.01)
                logger.info(f"  Stamp applied: {stamp_px:,} pixels affected, finish={stamp_spec_finish}")
            else:
                logger.info(f"  Stamp skipped: no visible pixels")
        except Exception as e:
            logger.error(f"  Stamp ERROR processing '{stamp_image}': {e}")
        logger.debug(f"  Stamp time: {time.time()-t_stamp:.2f}s")

    # Convert paint and spec to uint8 (single conversion point)
    t_save = time.time()
    paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    if paint_rgb.shape[2] == 4:
        paint_rgb = paint_rgb[:, :, :3]
    # Enforce PBR floors before final output (the build_multi_zone path
    # always wants CC>=CC_FLOOR everywhere — true matte zones already have
    # CC near the floor, so unconditionally clamping is intentional).
    # See module docstring "IRON RULES" and constants CC_FLOOR /
    # ROUGHNESS_FLOOR_NONMIRROR / CHROME_M_THRESHOLD.
    combined_spec[:,:,1] = np.where(combined_spec[:,:,0] < CHROME_M_THRESHOLD,
                                     np.maximum(combined_spec[:,:,1], ROUGHNESS_FLOOR_NONMIRROR),
                                     combined_spec[:,:,1])
    combined_spec[:,:,2] = np.maximum(combined_spec[:,:,2], CC_FLOOR)
    # Numerical safety in case any earlier step left NaN/Inf.
    combined_spec = np.nan_to_num(combined_spec, nan=0.0, posinf=255.0, neginf=0.0)
    combined_spec_u8 = np.clip(combined_spec, 0, 255).astype(np.uint8)

    # ---- PREVIEW MODE: return arrays directly, skip all file I/O ----
    if preview_mode:
        if export_layers and _export_zone_layers:
            return (paint_rgb, combined_spec_u8, _export_zone_layers)
        return (paint_rgb, combined_spec_u8)

    # Save outputs - car_prefix is "car_num" (custom numbers) or "car" (no custom numbers)
    # Spec map is ALWAYS car_spec regardless of custom number setting
    paint_path = os.path.join(output_dir, f"{car_prefix}_{iracing_id}.tga")
    spec_path = os.path.join(output_dir, f"car_spec_{iracing_id}.tga")

    write_tga_24bit(paint_path, paint_rgb)
    write_tga_32bit(spec_path, combined_spec_u8)

    # ---- OPTIONAL: Normal map generation from metallic channel ----
    if generate_normal_map:
        try:
            import cv2 as _cv2
            t_normal = time.time()
            # Use M channel (R = index 0 = Metallic) as height map
            height_map = combined_spec_u8[:, :, 0].astype(np.float32) / 255.0
            # Compute Sobel gradients in X and Y directions
            dx = _cv2.Sobel(height_map, _cv2.CV_32F, 1, 0, ksize=3)
            dy = _cv2.Sobel(height_map, _cv2.CV_32F, 0, 1, ksize=3)
            # Convert to tangent-space normal map: R = 0.5 + dx*0.5, G = 0.5 + dy*0.5, B = 1.0
            normal_r = np.clip(0.5 + dx * 0.5, 0.0, 1.0)
            normal_g = np.clip(0.5 + dy * 0.5, 0.0, 1.0)
            normal_b = np.ones_like(height_map)
            normal_map = np.stack([normal_r, normal_g, normal_b], axis=-1)
            normal_map_u8 = (normal_map * 255).astype(np.uint8)
            normal_path = os.path.join(output_dir, f"{car_prefix}_{iracing_id}_normal.tga")
            write_tga_24bit(normal_path, normal_map_u8)
            logger.info(f"  Normal map saved: {normal_path} ({time.time()-t_normal:.2f}s)")
        except Exception as e:
            logger.warning(f"  Normal map generation failed: {e}")

    # Save previews
    Image.fromarray(paint_rgb).save(os.path.join(output_dir, "PREVIEW_paint.png"))
    Image.fromarray(combined_spec_u8).save(os.path.join(output_dir, "PREVIEW_spec.png"))

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

    logger.debug(f"  File I/O + previews: {time.time()-t_save:.2f}s")

    elapsed = time.time() - start_time
    # Concise final summary, easy to grep in long server logs.
    logger.info(f"\n{'=' * 60}")
    logger.info(f"  DONE in {elapsed:.1f}s  (engine {ENGINE_VERSION}, seed {seed})")
    logger.info(f"  Paint: {paint_path}")
    logger.info(f"  Spec:  {spec_path}")
    if save_debug_images:
        logger.info(f"  Zone previews saved for debugging")
    logger.info(f"{'=' * 60}")

    if export_layers and _export_zone_layers:
        return paint_rgb, combined_spec_u8, zone_masks, _export_zone_layers
    return paint_rgb, combined_spec_u8, zone_masks


# ================================================================
# LIVE PREVIEW - Low-res fast render (no file I/O)
# ================================================================

def preview_render(paint_file, zones, seed=51, preview_scale=0.25, import_spec_map=None,
                   decal_spec_finishes=None, decal_paint_path=None, decal_mask_base64=None,
                   abort_event=None):
    """Live preview: runs the full render pipeline at reduced resolution.

    PUBLIC, stable. Used by the Paint Booth UI to drive the live preview
    panel. Internally calls :func:`build_multi_zone` with
    ``preview_mode=True`` so the preview matches the final render exactly
    (HSB, overlays, patterns, blend modes, color sources, decal spec
    finishes, etc.).

    Args:
        paint_file: Path to source paint image. Validated up front.
        zones: List of zone dicts (see :func:`build_multi_zone`).
        seed: Deterministic seed (int or str).
        preview_scale: 0..1 fraction of original resolution to render.
            Defaults to 0.25 (1/4 res). Smaller = faster, blurrier.
        import_spec_map: Optional pre-rendered spec map to overlay.
        decal_spec_finishes: Optional list of per-zone decal finish overrides.
        decal_paint_path: Optional decal RGBA composite path.
        decal_mask_base64: Optional base64-encoded decal mask.
        abort_event: Optional ``threading.Event`` to early-cancel the render.

    Returns:
        Tuple ``(paint_rgb_uint8, combined_spec_uint8, elapsed_ms)``. On
        error, returns blank arrays + the elapsed time so the UI can keep
        rolling — the failure is logged via ``logger.warning``.
    """
    _validate_zones(zones)
    _validate_paint_file(paint_file)
    seed = _coerce_seed(seed)
    # Clamp preview_scale into a sane range to avoid degenerate tiny renders
    # or accidental full-res passes.
    try:
        preview_scale = float(preview_scale)
    except (TypeError, ValueError):
        preview_scale = 0.25
    preview_scale = max(0.05, min(1.0, preview_scale))
    import time as _time
    import tempfile
    t0 = _time.time()

    # Downscale paint for speed
    scheme_img = Image.open(paint_file).convert('RGB')
    orig_w, orig_h = scheme_img.size
    preview_w = max(16, int(orig_w * preview_scale))
    preview_h = max(16, int(orig_h * preview_scale))
    scheme_img = scheme_img.resize((preview_w, preview_h), Image.LANCZOS)

    # Save to temp file (build_multi_zone expects a file path)
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    tmp_path = tmp.name
    tmp.close()
    scheme_img.save(tmp_path)

    # Downscale import spec map if provided
    preview_spec = None
    if import_spec_map and os.path.exists(import_spec_map):
        try:
            spec_img = Image.open(import_spec_map).convert('RGBA')
            spec_img = spec_img.resize((preview_w, preview_h), Image.LANCZOS)
            tmp_spec = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            preview_spec = tmp_spec.name
            tmp_spec.close()
            spec_img.save(preview_spec)
        except Exception:
            preview_spec = import_spec_map

    # Downscale decal_paint_path to preview resolution if provided
    # The decal composite is RGBA (alpha = decal mask), so preserve full RGBA.
    preview_decal_path = None
    if decal_paint_path and os.path.exists(decal_paint_path):
        try:
            decal_img = Image.open(decal_paint_path).convert('RGBA')
            decal_img = decal_img.resize((preview_w, preview_h), Image.LANCZOS)
            tmp_decal = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            preview_decal_path = tmp_decal.name
            tmp_decal.close()
            decal_img.save(preview_decal_path)
        except Exception:
            preview_decal_path = decal_paint_path  # Fall back to original size

    # Resize any region_mask / spatial_mask in zones to preview res
    for z in zones:
        if "region_mask" in z and z["region_mask"] is not None:
            rm = z["region_mask"]
            if isinstance(rm, np.ndarray) and (rm.shape[0] != preview_h or rm.shape[1] != preview_w):
                rm_img = Image.fromarray((rm * 255).astype(np.uint8) if rm.max() <= 1.0 else rm.astype(np.uint8))
                rm_img = rm_img.resize((preview_w, preview_h), Image.NEAREST)
                z["region_mask"] = np.array(rm_img).astype(np.float32) / 255.0
        if "spatial_mask" in z and z["spatial_mask"] is not None:
            sm = z["spatial_mask"]
            if isinstance(sm, np.ndarray) and (sm.shape[0] != preview_h or sm.shape[1] != preview_w):
                sm_img = Image.fromarray(sm.astype(np.uint8))
                sm_img = sm_img.resize((preview_w, preview_h), Image.NEAREST)
                z["spatial_mask"] = np.array(sm_img).astype(np.uint8)

    try:
        result = build_multi_zone(
            paint_file=tmp_path,
            output_dir=None,
            zones=zones,
            iracing_id="preview",
            seed=seed,
            import_spec_map=preview_spec or import_spec_map,
            preview_mode=True,
            decal_spec_finishes=decal_spec_finishes,
            decal_paint_path=preview_decal_path,
            decal_mask_base64=decal_mask_base64,
            abort_event=abort_event,
        )
        paint_rgb, combined_spec = result
    except Exception as e:
        # Do NOT crash the preview loop — return a neutral grey so the UI
        # can keep polling. Log details so we can root-cause later.
        import traceback
        logger.warning(
            f"  [preview_render] render failed at {preview_w}x{preview_h} "
            f"({len(zones)} zones, seed={seed}): {e}"
        )
        logger.warning(traceback.format_exc())
        paint_rgb = np.full((preview_h, preview_w, 3), 128, dtype=np.uint8)
        combined_spec = np.zeros((preview_h, preview_w, 4), dtype=np.uint8)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        if preview_spec and preview_spec != import_spec_map:
            try:
                os.unlink(preview_spec)
            except Exception:
                pass
        if preview_decal_path and preview_decal_path != decal_paint_path:
            try:
                os.unlink(preview_decal_path)
            except Exception:
                pass

    elapsed_ms = int((_time.time() - t0) * 1000)
    logger.info(f"  [preview_render] {preview_w}x{preview_h} ({len(zones)} zones) in {elapsed_ms}ms")

    return paint_rgb, combined_spec, elapsed_ms


# ================================================================
# CONVENIENCE: Apply single finish to whole car (backward compat)
# ================================================================

def apply_single_finish(paint_file, finish_name, output_dir, iracing_id="23371",
                        seed=51, intensity="100"):
    """Apply a single legacy/monolithic finish to the entire car.

    PUBLIC, stable. Convenience wrapper that builds a one-zone config and
    delegates to :func:`build_multi_zone`. Preserves backward compatibility
    with v1-era integrations that referenced finishes by name only.

    Args:
        paint_file: Path to the source .tga/.png paint.
        finish_name: Key into FINISH_REGISTRY or MONOLITHIC_REGISTRY
            (e.g. ``"chrome"``, ``"phantom"``, ``"prismatic"``).
        output_dir: Directory to write car_num_*.tga and car_spec_*.tga.
        iracing_id: iRacing customer ID used in output filenames.
        seed: Deterministic seed; accepts int or str (see :func:`_coerce_seed`).
        intensity: ``"0"`` to ``"100"`` (or any numeric string), forwarded
            verbatim into the zone spec.

    Returns:
        Same return value as :func:`build_multi_zone`.

    Side effects:
        Writes TGA + PNG preview files into ``output_dir``.
    """
    if not finish_name:
        raise ValueError("finish_name is required (e.g. 'chrome', 'phantom').")
    zones = [{
        "name": "Whole Car",
        "color": "everything",
        "finish": finish_name,
        "intensity": intensity,
    }]
    return build_multi_zone(paint_file, output_dir, zones, iracing_id, _coerce_seed(seed))


def apply_composed_finish(paint_file, base, pattern, output_dir, iracing_id="23371",
                          seed=51, intensity="100"):
    """Apply a composed base+pattern finish to the entire car (v3.0+ path).

    PUBLIC, stable. Convenience wrapper around :func:`build_multi_zone` for
    the modern compositing model where a finish is the cross product of a
    BASE_REGISTRY entry and a PATTERN_REGISTRY entry (375 x 569 ~= 213k+
    combinations as of v6.2).

    Args:
        paint_file: Path to source paint image.
        base: Key into BASE_REGISTRY (e.g. ``"chrome"``, ``"matte"``).
        pattern: Key into PATTERN_REGISTRY, or None/empty for ``"none"``.
        output_dir: Output directory.
        iracing_id: iRacing customer ID for filenames.
        seed: Deterministic seed (int or str).
        intensity: ``"0"`` to ``"100"`` numeric string.

    Returns:
        Same as :func:`build_multi_zone`.

    Side effects:
        Writes TGA + PNG preview files.
    """
    if not base:
        raise ValueError("base is required (key into BASE_REGISTRY).")
    zones = [{
        "name": "Whole Car",
        "color": "everything",
        "base": base,
        "pattern": pattern or "none",
        "intensity": intensity,
    }]
    return build_multi_zone(paint_file, output_dir, zones, iracing_id, _coerce_seed(seed))


# ================================================================
# SHARED HELPERS (extracted for reuse in helmet/suit/wear)
# ================================================================

def _parse_intensity(intensity):
    """Parse a UI intensity value to ``(spec_mult, paint_mult, bright_boost)``.

    INTERNAL helper. Accepts any integer 0-100 (not just multiples of 10)
    via linear interpolation. Applies the per-channel scaling table from
    ``engine.core._INTENSITY_SCALE`` so ``100% == 1.0`` maps to the
    correct internal multiplier for each rendering stage.

    Args:
        intensity: int, str, or any value castable to float. Unknown values
            fall back to full intensity (1.0) rather than raising — the UI
            sometimes posts blanks during fast slider drags and we don't
            want to crash a render over that.

    Returns:
        Tuple of three floats: ``(spec_mult, paint_mult, bright_boost)``.
    """
    # Fast path: exact match in table (multiples of 10)
    if intensity in INTENSITY:
        preset = INTENSITY[intensity]
    else:
        # Parse as numeric - support any 0-100 value the slider sends
        try:
            pct = max(0.0, min(100.0, float(intensity))) / 100.0
        except (TypeError, ValueError):
            pct = 1.0  # unknown string → full intensity
        preset = {"paint": pct, "spec": pct, "bright": pct}
    return (preset["spec"]  * _INTENSITY_SCALE["spec"],
            preset["paint"] * _INTENSITY_SCALE["paint"],
            preset["bright"] * _INTENSITY_SCALE["bright"])


def _build_color_mask(paint_rgb, zone, shape):
    """Build a zone mask from a color description. INTERNAL.

    Simplified compared to :func:`build_multi_zone`'s inline version —
    intended for helmet/suit pipelines that don't need full
    claimed/remainder tracking. The caller is responsible for clipping
    against ``claimed`` and applying any priority/order rules.

    Args:
        paint_rgb: HxWx3 paint array (uint8 or 0..1 float).
        zone: zone dict with at least a ``color`` key.
        shape: ``(h, w)`` tuple.

    Returns:
        HxW float32 mask in 0..1.
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
            # Remainder zone - return full mask (caller clips with claimed)
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

    PUBLIC, stable. Helmet paints are typically 512x512 or 1024x1024 24-bit
    TGA. Uses the same zone/finish system as cars — color-match zones on the
    helmet paint and apply finishes to generate ``helmet_spec_<id>.tga``.

    The helmet UV layout has the crown on top, visor in the middle, chin
    bar at bottom. Colors match just like car paints.

    Args:
        helmet_paint_file: Path to the helmet paint .tga/.png.
        output_dir: Output directory; created if missing.
        zones: List of zone dicts (same shape as build_multi_zone).
        iracing_id: iRacing customer ID for the output filename.
        seed: Deterministic seed (int or str).

    Returns:
        Tuple ``(helmet_spec_uint8, helmet_paint_uint8)`` if helmet paint
        is generated, otherwise the spec array.

    Side effects:
        Writes ``helmet_spec_<id>.tga`` and ``PREVIEW_helmet_spec.png``
        into ``output_dir``.
    """
    _validate_zones(zones)
    _validate_paint_file(helmet_paint_file)
    seed = _coerce_seed(seed)
    logger.info(f"\n{'='*60}")
    logger.info(f"  {ENGINE_DISPLAY_NAME} - Helmet Spec Generator")
    logger.info(f"  ID: {iracing_id}")
    logger.info(f"{'='*60}")
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
    combined_spec = np.zeros((h, w, 4), dtype=np.float32)
    combined_spec[:,:,1] = 100  # default R
    combined_spec[:,:,2] = 16   # default CC (CC≥16 always)
    combined_spec[:,:,3] = 255  # full spec mask

    claimed = np.zeros(shape, dtype=np.float32)
    _shared_spec_pool = ThreadPoolExecutor(max_workers=min(2, _os.cpu_count() or 1))

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
        # REVERSE FALLBACK: specials→base for migrated finishes
        if finish_name and finish_name not in MONOLITHIC_REGISTRY and finish_name in BASE_REGISTRY:
            base_id = finish_name
            finish_name = None

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
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) / 100.0 if _z_cc is not None and float(_z_cc) > 1.0 else (float(_z_cc) if _z_cc is not None else None)
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            # Pattern strength map (per-pixel modulation)
            if zone.get("pattern_strength_map") is not None:
                _v6kw["pattern_strength_map"] = zone["pattern_strength_map"]
            _v6kw["base_strength"] = float(zone.get("base_strength", 1.0))
            _v6kw["base_spec_strength"] = float(zone.get("base_spec_strength", 1.0))
            _v6kw["base_spec_blend_mode"] = zone.get("base_spec_blend_mode", "normal")
            _v6kw["base_color_mode"] = zone.get("base_color_mode", "source")
            # BOIL THE OCEAN drift fix: when mode='gradient', the engine's
            # _apply_base_color_override expects the stops/direction packaged
            # into base_color as a dict. JS sends them as separate top-level
            # gradient_stops/gradient_direction keys -- pre-fix the engine
            # silently ignored them and the painter saw the gradient picker
            # do nothing. Pack them here so the existing engine path fires.
            if (zone.get("base_color_mode") == "gradient"
                    and zone.get("gradient_stops")):
                _v6kw["base_color"] = {
                    "stops": zone.get("gradient_stops"),
                    "direction": zone.get("gradient_direction", "horizontal"),
                }
            else:
                _v6kw["base_color"] = zone.get("base_color", [1.0, 1.0, 1.0])
            _v6kw["base_color_source"] = zone.get("base_color_source")
            _v6kw["base_color_strength"] = float(zone.get("base_color_strength", 1.0))
            _v6kw["base_color_fit_zone"] = bool(zone.get("base_color_fit_zone", False))
            _v6kw["base_hue_offset"] = float(zone.get("base_hue_offset", 0))
            _v6kw["base_saturation_adjust"] = float(zone.get("base_saturation_adjust", 0))
            _v6kw["base_brightness_adjust"] = float(zone.get("base_brightness_adjust", 0))
            _v6kw["pattern_opacity"] = float(zone.get("pattern_opacity", 1.0))
            _v6kw["pattern_offset_x"] = max(0.0, min(1.0, float(zone.get("pattern_offset_x", 0.5))))
            _v6kw["pattern_offset_y"] = max(0.0, min(1.0, float(zone.get("pattern_offset_y", 0.5))))
            _v6kw["pattern_flip_h"] = bool(zone.get("pattern_flip_h", False))
            _v6kw["pattern_flip_v"] = bool(zone.get("pattern_flip_v", False))
            _v6kw["base_offset_x"] = max(0.0, min(1.0, float(zone.get("base_offset_x", 0.5))))
            _v6kw["base_offset_y"] = max(0.0, min(1.0, float(zone.get("base_offset_y", 0.5))))
            _v6kw["base_rotation"] = float(zone.get("base_rotation", 0))
            _v6kw["base_flip_h"] = bool(zone.get("base_flip_h", False))
            _v6kw["base_flip_v"] = bool(zone.get("base_flip_v", False))
            if zone.get("spec_pattern_stack"): _v6kw["spec_pattern_stack"] = zone["spec_pattern_stack"]
            if zone.get("overlay_spec_pattern_stack"): _v6kw["overlay_spec_pattern_stack"] = zone["overlay_spec_pattern_stack"]
            if zone.get("third_overlay_spec_pattern_stack"): _v6kw["third_overlay_spec_pattern_stack"] = zone["third_overlay_spec_pattern_stack"]
            if zone.get("fourth_overlay_spec_pattern_stack"): _v6kw["fourth_overlay_spec_pattern_stack"] = zone["fourth_overlay_spec_pattern_stack"]
            if zone.get("fifth_overlay_spec_pattern_stack"): _v6kw["fifth_overlay_spec_pattern_stack"] = zone["fifth_overlay_spec_pattern_stack"]
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc
            # Dual Layer Base Overlay — trigger on EITHER base ID or color source
            _z_sb = zone.get("second_base")
            _z_sb_cs = zone.get("second_base_color_source")
            if _z_sb or _z_sb_cs:
                _v6kw["second_base"] = _z_sb or ''
                _v6kw["second_base_color_source"] = _z_sb_cs
                _v6kw["second_base_color"] = zone.get("second_base_color", [1.0, 1.0, 1.0])
                _v6kw["second_base_strength"] = float(zone.get("second_base_strength", 0.0))
                _v6kw["second_base_spec_strength"] = float(zone.get("second_base_spec_strength", 1.0))
                _v6kw["second_base_blend_mode"] = zone.get("second_base_blend_mode", "noise")
                _v6kw["second_base_noise_scale"] = int(zone.get("second_base_noise_scale", 24))
                _v6kw["second_base_scale"] = float(zone.get("second_base_scale", 1.0))
                _v6kw["second_base_pattern"] = zone.get("second_base_pattern")
                _v6kw["second_base_pattern_scale"] = float(zone.get("second_base_pattern_scale", 1.0))
                _v6kw["second_base_pattern_rotation"] = float(zone.get("second_base_pattern_rotation", 0.0))
                _v6kw["second_base_pattern_opacity"] = float(zone.get("second_base_pattern_opacity", 1.0))
                _v6kw["second_base_pattern_strength"] = float(zone.get("second_base_pattern_strength", 1.0))
                _v6kw["second_base_pattern_invert"] = bool(zone.get("second_base_pattern_invert", False))
                _v6kw["second_base_pattern_harden"] = bool(zone.get("second_base_pattern_harden", False))
                _sb_oxN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                _sb_oyN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                _sb_pscaleN = _v6kw["second_base_pattern_scale"]
                # Fit-to-Zone for 2nd base overlay
                if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _sb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _sb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _sb_pscaleN = _sb_pscaleN / _ft_ratio
                _v6kw["second_base_pattern_offset_x"] = _sb_oxN
                _v6kw["second_base_pattern_offset_y"] = _sb_oyN
                _v6kw["second_base_pattern_scale"] = _sb_pscaleN
            _v6kw["second_base_hue_shift"] = float(zone.get("second_base_hue_shift", 0))
            _v6kw["second_base_saturation"] = float(zone.get("second_base_saturation", 0))
            _v6kw["second_base_brightness"] = float(zone.get("second_base_brightness", 0))
            _v6kw["second_base_pattern_hue_shift"] = float(zone.get("second_base_pattern_hue_shift", 0))
            _v6kw["second_base_pattern_saturation"] = float(zone.get("second_base_pattern_saturation", 0))
            _v6kw["second_base_pattern_brightness"] = float(zone.get("second_base_pattern_brightness", 0))
            _v6kw["second_base_color_source"] = zone.get("second_base_color_source")
            _z_tb = zone.get("third_base")
            if _z_tb:
                _v6kw["third_base"] = _z_tb
                _v6kw["third_base_color"] = zone.get("third_base_color", [1.0, 1.0, 1.0])
                _v6kw["third_base_strength"] = float(zone.get("third_base_strength", 0.0))
                _v6kw["third_base_spec_strength"] = float(zone.get("third_base_spec_strength", 1.0))
                _v6kw["third_base_blend_mode"] = zone.get("third_base_blend_mode", "noise")
                _v6kw["third_base_noise_scale"] = int(zone.get("third_base_noise_scale", 24))
                _v6kw["third_base_scale"] = float(zone.get("third_base_scale", 1.0))
                _v6kw["third_base_pattern"] = zone.get("third_base_pattern")
                _v6kw["third_base_pattern_scale"] = float(zone.get("third_base_pattern_scale", 1.0))
                _v6kw["third_base_pattern_rotation"] = float(zone.get("third_base_pattern_rotation", 0.0))
                _v6kw["third_base_pattern_opacity"] = float(zone.get("third_base_pattern_opacity", 1.0))
                _v6kw["third_base_pattern_strength"] = float(zone.get("third_base_pattern_strength", 1.0))
                _v6kw["third_base_pattern_invert"] = bool(zone.get("third_base_pattern_invert", False))
                _v6kw["third_base_pattern_harden"] = bool(zone.get("third_base_pattern_harden", False))
                _tb_oxN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_x", 0.5))))
                _tb_oyN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_y", 0.5))))
                _tb_pscaleN = _v6kw["third_base_pattern_scale"]
                # Fit-to-Zone for 3rd base overlay
                if zone.get("third_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _tb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _tb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _tb_pscaleN = _tb_pscaleN / _ft_ratio
                _v6kw["third_base_pattern_offset_x"] = _tb_oxN
                _v6kw["third_base_pattern_offset_y"] = _tb_oyN
                _v6kw["third_base_pattern_scale"] = _tb_pscaleN
            _v6kw["third_base_hue_shift"] = float(zone.get("third_base_hue_shift", 0))
            _v6kw["third_base_saturation"] = float(zone.get("third_base_saturation", 0))
            _v6kw["third_base_brightness"] = float(zone.get("third_base_brightness", 0))
            _v6kw["third_base_color_source"] = zone.get("third_base_color_source")
            _z_fb = zone.get("fourth_base")
            if _z_fb:
                _v6kw["fourth_base"] = _z_fb
                _v6kw["fourth_base_color"] = zone.get("fourth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fourth_base_strength"] = float(zone.get("fourth_base_strength", 0.0))
                _v6kw["fourth_base_spec_strength"] = float(zone.get("fourth_base_spec_strength", 1.0))
                _v6kw["fourth_base_blend_mode"] = zone.get("fourth_base_blend_mode", "noise")
                _v6kw["fourth_base_noise_scale"] = int(zone.get("fourth_base_noise_scale", 24))
                _v6kw["fourth_base_scale"] = float(zone.get("fourth_base_scale", 1.0))
                _v6kw["fourth_base_pattern"] = zone.get("fourth_base_pattern")
                _v6kw["fourth_base_pattern_scale"] = float(zone.get("fourth_base_pattern_scale", 1.0))
                _v6kw["fourth_base_pattern_rotation"] = float(zone.get("fourth_base_pattern_rotation", 0.0))
                _v6kw["fourth_base_pattern_opacity"] = float(zone.get("fourth_base_pattern_opacity", 1.0))
                _v6kw["fourth_base_pattern_strength"] = float(zone.get("fourth_base_pattern_strength", 1.0))
                _v6kw["fourth_base_pattern_invert"] = bool(zone.get("fourth_base_pattern_invert", False))
                _v6kw["fourth_base_pattern_harden"] = bool(zone.get("fourth_base_pattern_harden", False))
                _fb_oxN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_x", 0.5))))
                _fb_oyN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_y", 0.5))))
                _fb_pscaleN = _v6kw["fourth_base_pattern_scale"]
                # Fit-to-Zone for 4th base overlay
                if zone.get("fourth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fb_pscaleN = _fb_pscaleN / _ft_ratio
                _v6kw["fourth_base_pattern_offset_x"] = _fb_oxN
                _v6kw["fourth_base_pattern_offset_y"] = _fb_oyN
                _v6kw["fourth_base_pattern_scale"] = _fb_pscaleN
            _v6kw["fourth_base_hue_shift"] = float(zone.get("fourth_base_hue_shift", 0))
            _v6kw["fourth_base_saturation"] = float(zone.get("fourth_base_saturation", 0))
            _v6kw["fourth_base_brightness"] = float(zone.get("fourth_base_brightness", 0))
            _v6kw["fourth_base_color_source"] = zone.get("fourth_base_color_source")
            _z_fif = zone.get("fifth_base")
            if _z_fif:
                _v6kw["fifth_base"] = _z_fif
                _v6kw["fifth_base_color"] = zone.get("fifth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fifth_base_strength"] = float(zone.get("fifth_base_strength", 0.0))
                _v6kw["fifth_base_spec_strength"] = float(zone.get("fifth_base_spec_strength", 1.0))
                _v6kw["fifth_base_blend_mode"] = zone.get("fifth_base_blend_mode", "noise")
                _v6kw["fifth_base_noise_scale"] = int(zone.get("fifth_base_noise_scale", 24))
                _v6kw["fifth_base_scale"] = float(zone.get("fifth_base_scale", 1.0))
                _v6kw["fifth_base_pattern"] = zone.get("fifth_base_pattern")
                _v6kw["fifth_base_pattern_scale"] = float(zone.get("fifth_base_pattern_scale", 1.0))
                _v6kw["fifth_base_pattern_rotation"] = float(zone.get("fifth_base_pattern_rotation", 0.0))
                _v6kw["fifth_base_pattern_opacity"] = float(zone.get("fifth_base_pattern_opacity", 1.0))
                _v6kw["fifth_base_pattern_strength"] = float(zone.get("fifth_base_pattern_strength", 1.0))
                _v6kw["fifth_base_pattern_invert"] = bool(zone.get("fifth_base_pattern_invert", False))
                _v6kw["fifth_base_pattern_harden"] = bool(zone.get("fifth_base_pattern_harden", False))
                _fif_oxN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_x", 0.5))))
                _fif_oyN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_y", 0.5))))
                _fif_pscaleN = _v6kw["fifth_base_pattern_scale"]
                # Fit-to-Zone for 5th base overlay
                if zone.get("fifth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fif_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fif_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fif_pscaleN = _fif_pscaleN / _ft_ratio
                _v6kw["fifth_base_pattern_offset_x"] = _fif_oxN
                _v6kw["fifth_base_pattern_offset_y"] = _fif_oyN
                _v6kw["fifth_base_pattern_scale"] = _fif_pscaleN
            _v6kw["fifth_base_hue_shift"] = float(zone.get("fifth_base_hue_shift", 0))
            _v6kw["fifth_base_saturation"] = float(zone.get("fifth_base_saturation", 0))
            _v6kw["fifth_base_brightness"] = float(zone.get("fifth_base_brightness", 0))
            _v6kw["fifth_base_color_source"] = zone.get("fifth_base_color_source")
            _v6kw["monolithic_registry"] = MONOLITHIC_REGISTRY

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                stack_ids = {ps.get("id") for ps in pattern_stack[:4] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation,
                                         "offset_x": float(zone.get("pattern_offset_x", 0.5)),
                                         "offset_y": float(zone.get("pattern_offset_y", 0.5))})
                for ps in pattern_stack[:4]:  # Max 4 additional (matches JS MAX_PATTERN_STACK_LAYERS)
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                            "blend_mode": ps.get("blend_mode", "normal"),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%{"["+p.get("blend_mode","normal")+"]" if p.get("blend_mode","normal") != "normal" else ""}' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                print(f"    [{name}] => {label} ({intensity}) [stacked compositing]")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_color_fit_zone": _v6kw.get("base_color_fit_zone", False), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5); _v6paint["second_base_hue_shift"] = _v6kw.get("second_base_hue_shift", 0); _v6paint["second_base_saturation"] = _v6kw.get("second_base_saturation", 0); _v6paint["second_base_brightness"] = _v6kw.get("second_base_brightness", 0); _v6paint["second_base_pattern_hue_shift"] = _v6kw.get("second_base_pattern_hue_shift", 0); _v6paint["second_base_pattern_saturation"] = _v6kw.get("second_base_pattern_saturation", 0); _v6paint["second_base_pattern_brightness"] = _v6kw.get("second_base_pattern_brightness", 0)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5); _v6paint["third_base_hue_shift"] = _v6kw.get("third_base_hue_shift", 0); _v6paint["third_base_saturation"] = _v6kw.get("third_base_saturation", 0); _v6paint["third_base_brightness"] = _v6kw.get("third_base_brightness", 0)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5); _v6paint["fourth_base_hue_shift"] = _v6kw.get("fourth_base_hue_shift", 0); _v6paint["fourth_base_saturation"] = _v6kw.get("fourth_base_saturation", 0); _v6paint["fourth_base_brightness"] = _v6kw.get("fourth_base_brightness", 0)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5); _v6paint["fifth_base_hue_shift"] = _v6kw.get("fifth_base_hue_shift", 0); _v6paint["fifth_base_saturation"] = _v6kw.get("fifth_base_saturation", 0); _v6paint["fifth_base_brightness"] = _v6kw.get("fifth_base_brightness", 0)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                _v6paint["base_offset_x"] = _v6kw.get("base_offset_x", 0.5)
                _v6paint["base_offset_y"] = _v6kw.get("base_offset_y", 0.5)
                _v6paint["base_rotation"] = _v6kw.get("base_rotation", 0)
                _v6paint["base_flip_h"] = _v6kw.get("base_flip_h", False)
                _v6paint["base_flip_v"] = _v6kw.get("base_flip_v", False)
                _v6paint["pattern_offset_x"] = _v6kw.get("pattern_offset_x", 0.5)
                _v6paint["pattern_offset_y"] = _v6kw.get("pattern_offset_y", 0.5)
                if all_patterns:
                    # Parallel: spec in background thread while paint mod runs in foreground
                    if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                        _spec_ex = _shared_spec_pool
                        _spec_fut = _spec_ex.submit(compose_finish_stacked, base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                        _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                        if _paint_was_gpu: paint = to_cpu(paint)
                        paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                        if _paint_was_gpu: paint = to_gpu(paint)
                        zone_spec = _spec_fut.result()
                else:
                    # Parallel: spec in background thread while paint mod runs in foreground
                    if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                        _spec_ex = _shared_spec_pool
                        _spec_fut = _spec_ex.submit(compose_finish, base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                        _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                        if _paint_was_gpu: paint = to_cpu(paint)
                        paint = compose_paint_mod(base_id, "none", paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                        if _paint_was_gpu: paint = to_gpu(paint)
                        zone_spec = _spec_fut.result()
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.1f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_color_fit_zone": _v6kw.get("base_color_fit_zone", False), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5); _v6paint["second_base_hue_shift"] = _v6kw.get("second_base_hue_shift", 0); _v6paint["second_base_saturation"] = _v6kw.get("second_base_saturation", 0); _v6paint["second_base_brightness"] = _v6kw.get("second_base_brightness", 0); _v6paint["second_base_pattern_hue_shift"] = _v6kw.get("second_base_pattern_hue_shift", 0); _v6paint["second_base_pattern_saturation"] = _v6kw.get("second_base_pattern_saturation", 0); _v6paint["second_base_pattern_brightness"] = _v6kw.get("second_base_pattern_brightness", 0)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5); _v6paint["third_base_hue_shift"] = _v6kw.get("third_base_hue_shift", 0); _v6paint["third_base_saturation"] = _v6kw.get("third_base_saturation", 0); _v6paint["third_base_brightness"] = _v6kw.get("third_base_brightness", 0)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5); _v6paint["fourth_base_hue_shift"] = _v6kw.get("fourth_base_hue_shift", 0); _v6paint["fourth_base_saturation"] = _v6kw.get("fourth_base_saturation", 0); _v6paint["fourth_base_brightness"] = _v6kw.get("fourth_base_brightness", 0)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5); _v6paint["fifth_base_hue_shift"] = _v6kw.get("fifth_base_hue_shift", 0); _v6paint["fifth_base_saturation"] = _v6kw.get("fifth_base_saturation", 0); _v6paint["fifth_base_brightness"] = _v6kw.get("fifth_base_brightness", 0)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                _v6paint["base_offset_x"] = _v6kw.get("base_offset_x", 0.5)
                _v6paint["base_offset_y"] = _v6kw.get("base_offset_y", 0.5)
                _v6paint["base_rotation"] = _v6kw.get("base_rotation", 0)
                _v6paint["base_flip_h"] = _v6kw.get("base_flip_h", False)
                _v6paint["base_flip_v"] = _v6kw.get("base_flip_v", False)
                # Parallel: spec in background thread while paint mod runs in foreground
                if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                    _spec_ex = _shared_spec_pool
                    _spec_fut = _spec_ex.submit(compose_finish, base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                    _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                    if _paint_was_gpu: paint = to_cpu(paint)
                    paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation, **_v6paint)
                    if _paint_was_gpu: paint = to_gpu(paint)
                    zone_spec = _spec_fut.result()
        elif finish_name and zone.get("finish_colors") and (
            finish_name.startswith("grad_") or finish_name.startswith("gradm_")
            or finish_name.startswith("grad3_") or finish_name.startswith("ghostg_")
            or finish_name.startswith("mc_")
        ):
            zone_rotation = float(zone.get("rotation", 0))
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is not None: zone_spec = _sanitize_spec_result(zone_spec, shape)
            if paint is not None: paint = _sanitize_paint_result(paint, shape)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}) [monolithic]")

            _mono_base_strength = max(0.0, min(2.0, float(zone.get("base_strength", 1.0))))
            _mono_spec_strength = max(0.0, min(2.0, float(zone.get("base_spec_strength", 1.0))))
            _sm_eff = sm * _mono_base_strength * _mono_spec_strength
            _pm_eff = pm * _mono_base_strength
            _bb_eff = bb * _mono_base_strength
            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                tile_spec = _sanitize_spec_result(spec_fn(tile_shape, tile_mask, seed + i * 13, _sm_eff), tile_shape)
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, _pm_eff, _bb_eff)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, _sm_eff)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, _pm_eff, _bb_eff)

            # Apply HSB adjustments to monolithic paint (same as base+pattern path)
            _mono_hue = float(zone.get("base_hue_offset", 0))
            _mono_sat = float(zone.get("base_saturation_adjust", 0))
            _mono_bri = float(zone.get("base_brightness_adjust", 0))
            if abs(_mono_hue) >= 0.5 or abs(_mono_sat) >= 0.5 or abs(_mono_bri) >= 0.5:
                paint = _apply_hsb_adjustments(paint, zone_mask, _mono_hue, _mono_sat, _mono_bri)

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
            # PATH 4: GENERIC FALLBACK - client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is not None: zone_spec = _sanitize_spec_result(zone_spec, shape)
            if paint is not None: paint = _sanitize_paint_result(paint, shape)
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
        if is_gpu():
            _zs_g = to_gpu(zone_spec.astype(np.float32))
            _m3d_g = to_gpu(zone_mask[:,:,np.newaxis])
            _cs_g = to_gpu(combined_spec)
            soft = _m3d_g > 0.05
            blended = xp.clip(_zs_g * _m3d_g + _cs_g * (1 - _m3d_g), 0, 255)
            combined_spec = to_cpu(xp.where(soft, blended, _cs_g))
        else:
            mask3d = zone_mask[:,:,np.newaxis]
            soft = mask3d > 0.05
            blended = np.clip(
                zone_spec.astype(np.float32) * mask3d +
                combined_spec * (1 - mask3d),
                0, 255
            )
            combined_spec = np.where(soft, blended, combined_spec)

    # Enforce PBR floors + convert to uint8 for helmet spec output
    combined_spec[:,:,1] = np.where(combined_spec[:,:,0] < 240, np.maximum(combined_spec[:,:,1], 15), combined_spec[:,:,1])
    combined_spec[:,:,2] = np.maximum(combined_spec[:,:,2], 16)
    combined_spec_u8 = np.clip(combined_spec, 0, 255).astype(np.uint8)
    os.makedirs(output_dir, exist_ok=True)
    spec_path = os.path.join(output_dir, f"helmet_spec_{iracing_id}.tga")
    write_tga_32bit(spec_path, combined_spec_u8)
    Image.fromarray(combined_spec_u8).save(os.path.join(output_dir, "PREVIEW_helmet_spec.png"))

    # Also save modified paint if it changed
    helmet_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    paint_path = os.path.join(output_dir, f"helmet_{iracing_id}.tga")
    write_tga_24bit(paint_path, helmet_paint)
    Image.fromarray(helmet_paint).save(os.path.join(output_dir, "PREVIEW_helmet_paint.png"))

    elapsed = time.time() - start_time
    print(f"\n  Helmet done in {elapsed:.1f}s!")
    print(f"  Spec:  {spec_path}")
    print(f"  Paint: {paint_path}")
    return helmet_paint, combined_spec_u8


def build_suit_spec(suit_paint_file, output_dir, zones, iracing_id="23371", seed=51):
    """Generate a spec map for an iRacing suit (firesuit) paint file.

    PUBLIC, stable. Suit paints are typically 1024x1024 24-bit TGA.

    UV layout: shirt (upper left/center), pants (lower center), gloves
    (lower left), shoes (lower left corner). Uses the exact same zone/finish
    system as cars and helmets.

    Args:
        suit_paint_file: Path to the suit paint .tga/.png.
        output_dir: Output directory; created if missing.
        zones: List of zone dicts (same shape as build_multi_zone).
        iracing_id: iRacing customer ID for the output filename.
        seed: Deterministic seed (int or str).

    Returns:
        Tuple ``(suit_paint_uint8, suit_spec_uint8)``.

    Side effects:
        Writes ``suit_spec_<id>.tga`` and ``PREVIEW_suit_spec.png``.
    """
    _validate_zones(zones)
    _validate_paint_file(suit_paint_file)
    seed = _coerce_seed(seed)
    logger.info(f"\n{'='*60}")
    logger.info(f"  {ENGINE_DISPLAY_NAME} - Suit Spec Generator")
    logger.info(f"  ID: {iracing_id}")
    logger.info(f"{'='*60}")
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

    combined_spec = np.zeros((h, w, 4), dtype=np.float32)
    combined_spec[:,:,1] = 100  # default R
    combined_spec[:,:,2] = 16   # default CC (CC≥16 always)
    combined_spec[:,:,3] = 255  # full spec mask
    claimed = np.zeros(shape, dtype=np.float32)
    _shared_spec_pool = ThreadPoolExecutor(max_workers=min(2, _os.cpu_count() or 1))

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
        # REVERSE FALLBACK: specials→base for migrated finishes
        if finish_name and finish_name not in MONOLITHIC_REGISTRY and finish_name in BASE_REGISTRY:
            base_id = finish_name
            finish_name = None

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
            _z_cc = zone.get("cc_quality"); _z_cc = float(_z_cc) / 100.0 if _z_cc is not None and float(_z_cc) > 1.0 else (float(_z_cc) if _z_cc is not None else None)
            _z_bb = zone.get("blend_base") or None; _z_bd = zone.get("blend_dir", "horizontal"); _z_ba = float(zone.get("blend_amount", 0.5))
            _z_pc = zone.get("paint_color")
            _v6kw = {}
            # Pattern strength map (per-pixel modulation)
            if zone.get("pattern_strength_map") is not None:
                _v6kw["pattern_strength_map"] = zone["pattern_strength_map"]
            _v6kw["base_strength"] = float(zone.get("base_strength", 1.0))
            _v6kw["base_spec_strength"] = float(zone.get("base_spec_strength", 1.0))
            _v6kw["base_spec_blend_mode"] = zone.get("base_spec_blend_mode", "normal")
            _v6kw["base_color_mode"] = zone.get("base_color_mode", "source")
            # BOIL THE OCEAN drift fix: when mode='gradient', the engine's
            # _apply_base_color_override expects the stops/direction packaged
            # into base_color as a dict. JS sends them as separate top-level
            # gradient_stops/gradient_direction keys -- pre-fix the engine
            # silently ignored them and the painter saw the gradient picker
            # do nothing. Pack them here so the existing engine path fires.
            if (zone.get("base_color_mode") == "gradient"
                    and zone.get("gradient_stops")):
                _v6kw["base_color"] = {
                    "stops": zone.get("gradient_stops"),
                    "direction": zone.get("gradient_direction", "horizontal"),
                }
            else:
                _v6kw["base_color"] = zone.get("base_color", [1.0, 1.0, 1.0])
            _v6kw["base_color_source"] = zone.get("base_color_source")
            _v6kw["base_color_strength"] = float(zone.get("base_color_strength", 1.0))
            _v6kw["base_color_fit_zone"] = bool(zone.get("base_color_fit_zone", False))
            _v6kw["base_hue_offset"] = float(zone.get("base_hue_offset", 0))
            _v6kw["base_saturation_adjust"] = float(zone.get("base_saturation_adjust", 0))
            _v6kw["base_brightness_adjust"] = float(zone.get("base_brightness_adjust", 0))
            _v6kw["pattern_opacity"] = float(zone.get("pattern_opacity", 1.0))
            _v6kw["pattern_offset_x"] = max(0.0, min(1.0, float(zone.get("pattern_offset_x", 0.5))))
            _v6kw["pattern_offset_y"] = max(0.0, min(1.0, float(zone.get("pattern_offset_y", 0.5))))
            _v6kw["pattern_flip_h"] = bool(zone.get("pattern_flip_h", False))
            _v6kw["pattern_flip_v"] = bool(zone.get("pattern_flip_v", False))
            _v6kw["base_offset_x"] = max(0.0, min(1.0, float(zone.get("base_offset_x", 0.5))))
            _v6kw["base_offset_y"] = max(0.0, min(1.0, float(zone.get("base_offset_y", 0.5))))
            _v6kw["base_rotation"] = float(zone.get("base_rotation", 0))
            _v6kw["base_flip_h"] = bool(zone.get("base_flip_h", False))
            _v6kw["base_flip_v"] = bool(zone.get("base_flip_v", False))
            if zone.get("spec_pattern_stack"): _v6kw["spec_pattern_stack"] = zone["spec_pattern_stack"]
            if zone.get("overlay_spec_pattern_stack"): _v6kw["overlay_spec_pattern_stack"] = zone["overlay_spec_pattern_stack"]
            if zone.get("third_overlay_spec_pattern_stack"): _v6kw["third_overlay_spec_pattern_stack"] = zone["third_overlay_spec_pattern_stack"]
            if zone.get("fourth_overlay_spec_pattern_stack"): _v6kw["fourth_overlay_spec_pattern_stack"] = zone["fourth_overlay_spec_pattern_stack"]
            if zone.get("fifth_overlay_spec_pattern_stack"): _v6kw["fifth_overlay_spec_pattern_stack"] = zone["fifth_overlay_spec_pattern_stack"]
            if _z_cc is not None: _v6kw["cc_quality"] = _z_cc
            if _z_bb: _v6kw["blend_base"] = _z_bb; _v6kw["blend_dir"] = _z_bd; _v6kw["blend_amount"] = _z_ba
            if _z_pc: _v6kw["paint_color"] = _z_pc
            # Dual Layer Base Overlay — trigger on EITHER base ID or color source
            _z_sb = zone.get("second_base")
            _z_sb_cs = zone.get("second_base_color_source")
            if _z_sb or _z_sb_cs:
                _v6kw["second_base"] = _z_sb or ''
                _v6kw["second_base_color_source"] = _z_sb_cs
                _v6kw["second_base_color"] = zone.get("second_base_color", [1.0, 1.0, 1.0])
                _v6kw["second_base_strength"] = float(zone.get("second_base_strength", 0.0))
                _v6kw["second_base_spec_strength"] = float(zone.get("second_base_spec_strength", 1.0))
                _v6kw["second_base_blend_mode"] = zone.get("second_base_blend_mode", "noise")
                _v6kw["second_base_noise_scale"] = int(zone.get("second_base_noise_scale", 24))
                _v6kw["second_base_scale"] = float(zone.get("second_base_scale", 1.0))
                _v6kw["second_base_pattern"] = zone.get("second_base_pattern")
                _v6kw["second_base_pattern_scale"] = float(zone.get("second_base_pattern_scale", 1.0))
                _v6kw["second_base_pattern_rotation"] = float(zone.get("second_base_pattern_rotation", 0.0))
                _v6kw["second_base_pattern_opacity"] = float(zone.get("second_base_pattern_opacity", 1.0))
                _v6kw["second_base_pattern_strength"] = float(zone.get("second_base_pattern_strength", 1.0))
                _v6kw["second_base_pattern_invert"] = bool(zone.get("second_base_pattern_invert", False))
                _v6kw["second_base_pattern_harden"] = bool(zone.get("second_base_pattern_harden", False))
                _sb_oxN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_x", 0.5))))
                _sb_oyN = max(0.0, min(1.0, float(zone.get("second_base_pattern_offset_y", 0.5))))
                _sb_pscaleN = _v6kw["second_base_pattern_scale"]
                # Fit-to-Zone for 2nd base overlay
                if zone.get("second_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _sb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _sb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _sb_pscaleN = _sb_pscaleN / _ft_ratio
                _v6kw["second_base_pattern_offset_x"] = _sb_oxN
                _v6kw["second_base_pattern_offset_y"] = _sb_oyN
                _v6kw["second_base_pattern_scale"] = _sb_pscaleN
            _v6kw["second_base_hue_shift"] = float(zone.get("second_base_hue_shift", 0))
            _v6kw["second_base_saturation"] = float(zone.get("second_base_saturation", 0))
            _v6kw["second_base_brightness"] = float(zone.get("second_base_brightness", 0))
            _v6kw["second_base_pattern_hue_shift"] = float(zone.get("second_base_pattern_hue_shift", 0))
            _v6kw["second_base_pattern_saturation"] = float(zone.get("second_base_pattern_saturation", 0))
            _v6kw["second_base_pattern_brightness"] = float(zone.get("second_base_pattern_brightness", 0))
            _v6kw["second_base_color_source"] = zone.get("second_base_color_source")
            _z_tb = zone.get("third_base")
            if _z_tb:
                _v6kw["third_base"] = _z_tb
                _v6kw["third_base_color"] = zone.get("third_base_color", [1.0, 1.0, 1.0])
                _v6kw["third_base_strength"] = float(zone.get("third_base_strength", 0.0))
                _v6kw["third_base_spec_strength"] = float(zone.get("third_base_spec_strength", 1.0))
                _v6kw["third_base_blend_mode"] = zone.get("third_base_blend_mode", "noise")
                _v6kw["third_base_noise_scale"] = int(zone.get("third_base_noise_scale", 24))
                _v6kw["third_base_scale"] = float(zone.get("third_base_scale", 1.0))
                _v6kw["third_base_pattern"] = zone.get("third_base_pattern")
                _v6kw["third_base_pattern_scale"] = float(zone.get("third_base_pattern_scale", 1.0))
                _v6kw["third_base_pattern_rotation"] = float(zone.get("third_base_pattern_rotation", 0.0))
                _v6kw["third_base_pattern_opacity"] = float(zone.get("third_base_pattern_opacity", 1.0))
                _v6kw["third_base_pattern_strength"] = float(zone.get("third_base_pattern_strength", 1.0))
                _v6kw["third_base_pattern_invert"] = bool(zone.get("third_base_pattern_invert", False))
                _v6kw["third_base_pattern_harden"] = bool(zone.get("third_base_pattern_harden", False))
                _tb_oxN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_x", 0.5))))
                _tb_oyN = max(0.0, min(1.0, float(zone.get("third_base_pattern_offset_y", 0.5))))
                _tb_pscaleN = _v6kw["third_base_pattern_scale"]
                # Fit-to-Zone for 3rd base overlay
                if zone.get("third_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _tb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _tb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _tb_pscaleN = _tb_pscaleN / _ft_ratio
                _v6kw["third_base_pattern_offset_x"] = _tb_oxN
                _v6kw["third_base_pattern_offset_y"] = _tb_oyN
                _v6kw["third_base_pattern_scale"] = _tb_pscaleN
            _v6kw["third_base_hue_shift"] = float(zone.get("third_base_hue_shift", 0))
            _v6kw["third_base_saturation"] = float(zone.get("third_base_saturation", 0))
            _v6kw["third_base_brightness"] = float(zone.get("third_base_brightness", 0))
            _v6kw["third_base_color_source"] = zone.get("third_base_color_source")
            _z_fb = zone.get("fourth_base")
            if _z_fb:
                _v6kw["fourth_base"] = _z_fb
                _v6kw["fourth_base_color"] = zone.get("fourth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fourth_base_strength"] = float(zone.get("fourth_base_strength", 0.0))
                _v6kw["fourth_base_spec_strength"] = float(zone.get("fourth_base_spec_strength", 1.0))
                _v6kw["fourth_base_blend_mode"] = zone.get("fourth_base_blend_mode", "noise")
                _v6kw["fourth_base_noise_scale"] = int(zone.get("fourth_base_noise_scale", 24))
                _v6kw["fourth_base_scale"] = float(zone.get("fourth_base_scale", 1.0))
                _v6kw["fourth_base_pattern"] = zone.get("fourth_base_pattern")
                _v6kw["fourth_base_pattern_scale"] = float(zone.get("fourth_base_pattern_scale", 1.0))
                _v6kw["fourth_base_pattern_rotation"] = float(zone.get("fourth_base_pattern_rotation", 0.0))
                _v6kw["fourth_base_pattern_opacity"] = float(zone.get("fourth_base_pattern_opacity", 1.0))
                _v6kw["fourth_base_pattern_strength"] = float(zone.get("fourth_base_pattern_strength", 1.0))
                _v6kw["fourth_base_pattern_invert"] = bool(zone.get("fourth_base_pattern_invert", False))
                _v6kw["fourth_base_pattern_harden"] = bool(zone.get("fourth_base_pattern_harden", False))
                _fb_oxN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_x", 0.5))))
                _fb_oyN = max(0.0, min(1.0, float(zone.get("fourth_base_pattern_offset_y", 0.5))))
                _fb_pscaleN = _v6kw["fourth_base_pattern_scale"]
                # Fit-to-Zone for 4th base overlay
                if zone.get("fourth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fb_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fb_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fb_pscaleN = _fb_pscaleN / _ft_ratio
                _v6kw["fourth_base_pattern_offset_x"] = _fb_oxN
                _v6kw["fourth_base_pattern_offset_y"] = _fb_oyN
                _v6kw["fourth_base_pattern_scale"] = _fb_pscaleN
            _v6kw["fourth_base_hue_shift"] = float(zone.get("fourth_base_hue_shift", 0))
            _v6kw["fourth_base_saturation"] = float(zone.get("fourth_base_saturation", 0))
            _v6kw["fourth_base_brightness"] = float(zone.get("fourth_base_brightness", 0))
            _v6kw["fourth_base_color_source"] = zone.get("fourth_base_color_source")
            _z_fif = zone.get("fifth_base")
            if _z_fif:
                _v6kw["fifth_base"] = _z_fif
                _v6kw["fifth_base_color"] = zone.get("fifth_base_color", [1.0, 1.0, 1.0])
                _v6kw["fifth_base_strength"] = float(zone.get("fifth_base_strength", 0.0))
                _v6kw["fifth_base_spec_strength"] = float(zone.get("fifth_base_spec_strength", 1.0))
                _v6kw["fifth_base_blend_mode"] = zone.get("fifth_base_blend_mode", "noise")
                _v6kw["fifth_base_noise_scale"] = int(zone.get("fifth_base_noise_scale", 24))
                _v6kw["fifth_base_scale"] = float(zone.get("fifth_base_scale", 1.0))
                _v6kw["fifth_base_pattern"] = zone.get("fifth_base_pattern")
                _v6kw["fifth_base_pattern_scale"] = float(zone.get("fifth_base_pattern_scale", 1.0))
                _v6kw["fifth_base_pattern_rotation"] = float(zone.get("fifth_base_pattern_rotation", 0.0))
                _v6kw["fifth_base_pattern_opacity"] = float(zone.get("fifth_base_pattern_opacity", 1.0))
                _v6kw["fifth_base_pattern_strength"] = float(zone.get("fifth_base_pattern_strength", 1.0))
                _v6kw["fifth_base_pattern_invert"] = bool(zone.get("fifth_base_pattern_invert", False))
                _v6kw["fifth_base_pattern_harden"] = bool(zone.get("fifth_base_pattern_harden", False))
                _fif_oxN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_x", 0.5))))
                _fif_oyN = max(0.0, min(1.0, float(zone.get("fifth_base_pattern_offset_y", 0.5))))
                _fif_pscaleN = _v6kw["fifth_base_pattern_scale"]
                # Fit-to-Zone for 5th base overlay
                if zone.get("fifth_base_fit_zone", False) and zone_mask is not None:
                    _ftrows = np.any(zone_mask > 0.1, axis=1)
                    _ftcols = np.any(zone_mask > 0.1, axis=0)
                    if _ftrows.any() and _ftcols.any():
                        _ftr_min, _ftr_max = np.where(_ftrows)[0][[0, -1]]
                        _ftc_min, _ftc_max = np.where(_ftcols)[0][[0, -1]]
                        _ft_ratio = max((_ftr_max - _ftr_min + 1) / h, (_ftc_max - _ftc_min + 1) / w)
                        if _ft_ratio > 0.01:
                            _fif_oxN = (_ftc_min + _ftc_max) / 2.0 / w
                            _fif_oyN = (_ftr_min + _ftr_max) / 2.0 / h
                            _fif_pscaleN = _fif_pscaleN / _ft_ratio
                _v6kw["fifth_base_pattern_offset_x"] = _fif_oxN
                _v6kw["fifth_base_pattern_offset_y"] = _fif_oyN
                _v6kw["fifth_base_pattern_scale"] = _fif_pscaleN
            _v6kw["fifth_base_hue_shift"] = float(zone.get("fifth_base_hue_shift", 0))
            _v6kw["fifth_base_saturation"] = float(zone.get("fifth_base_saturation", 0))
            _v6kw["fifth_base_brightness"] = float(zone.get("fifth_base_brightness", 0))
            _v6kw["fifth_base_color_source"] = zone.get("fifth_base_color_source")
            _v6kw["monolithic_registry"] = MONOLITHIC_REGISTRY

            if pattern_stack or primary_pat_opacity < 1.0:
                # STACKED PATTERNS: build combined list (primary + stack layers)
                # DEDUP: skip primary pattern if it already appears in the stack
                stack_ids = {ps.get("id") for ps in pattern_stack[:4] if ps.get("id") and ps.get("id") != "none"}
                all_patterns = []
                if pattern_id and pattern_id != "none" and pattern_id not in stack_ids:
                    all_patterns.append({"id": pattern_id, "opacity": primary_pat_opacity, "scale": zone_scale, "rotation": zone_rotation,
                                         "offset_x": float(zone.get("pattern_offset_x", 0.5)),
                                         "offset_y": float(zone.get("pattern_offset_y", 0.5))})
                for ps in pattern_stack[:4]:  # Max 4 additional (matches JS MAX_PATTERN_STACK_LAYERS)
                    pid = ps.get("id", "none")
                    if pid != "none" and pid in PATTERN_REGISTRY:
                        all_patterns.append({
                            "id": pid,
                            "opacity": float(ps.get("opacity", 1.0)),
                            "scale": float(ps.get("scale", 1.0)),
                            "rotation": float(ps.get("rotation", 0)),
                            "blend_mode": ps.get("blend_mode", "normal"),
                        })
                pat_names = " + ".join(f'{p["id"]}@{int(p["opacity"]*100)}%{"["+p.get("blend_mode","normal")+"]" if p.get("blend_mode","normal") != "normal" else ""}' for p in all_patterns)
                label = f"{base_id} + [{pat_names}]"
                print(f"    [{name}] => {label} ({intensity}) [stacked compositing]")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_color_fit_zone": _v6kw.get("base_color_fit_zone", False), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5); _v6paint["second_base_hue_shift"] = _v6kw.get("second_base_hue_shift", 0); _v6paint["second_base_saturation"] = _v6kw.get("second_base_saturation", 0); _v6paint["second_base_brightness"] = _v6kw.get("second_base_brightness", 0); _v6paint["second_base_pattern_hue_shift"] = _v6kw.get("second_base_pattern_hue_shift", 0); _v6paint["second_base_pattern_saturation"] = _v6kw.get("second_base_pattern_saturation", 0); _v6paint["second_base_pattern_brightness"] = _v6kw.get("second_base_pattern_brightness", 0)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5); _v6paint["third_base_hue_shift"] = _v6kw.get("third_base_hue_shift", 0); _v6paint["third_base_saturation"] = _v6kw.get("third_base_saturation", 0); _v6paint["third_base_brightness"] = _v6kw.get("third_base_brightness", 0)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5); _v6paint["fourth_base_hue_shift"] = _v6kw.get("fourth_base_hue_shift", 0); _v6paint["fourth_base_saturation"] = _v6kw.get("fourth_base_saturation", 0); _v6paint["fourth_base_brightness"] = _v6kw.get("fourth_base_brightness", 0)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5); _v6paint["fifth_base_hue_shift"] = _v6kw.get("fifth_base_hue_shift", 0); _v6paint["fifth_base_saturation"] = _v6kw.get("fifth_base_saturation", 0); _v6paint["fifth_base_brightness"] = _v6kw.get("fifth_base_brightness", 0)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                _v6paint["base_offset_x"] = _v6kw.get("base_offset_x", 0.5)
                _v6paint["base_offset_y"] = _v6kw.get("base_offset_y", 0.5)
                _v6paint["base_rotation"] = _v6kw.get("base_rotation", 0)
                _v6paint["base_flip_h"] = _v6kw.get("base_flip_h", False)
                _v6paint["base_flip_v"] = _v6kw.get("base_flip_v", False)
                _v6paint["pattern_offset_x"] = _v6kw.get("pattern_offset_x", 0.5)
                _v6paint["pattern_offset_y"] = _v6kw.get("pattern_offset_y", 0.5)
                if all_patterns:
                    # Parallel: spec in background thread while paint mod runs in foreground
                    if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                        _spec_ex = _shared_spec_pool
                        _spec_fut = _spec_ex.submit(compose_finish_stacked, base_id, all_patterns, shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                        _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                        if _paint_was_gpu: paint = to_cpu(paint)
                        paint = compose_paint_mod_stacked(base_id, all_patterns, paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                        if _paint_was_gpu: paint = to_gpu(paint)
                        zone_spec = _spec_fut.result()
                else:
                    # Parallel: spec in background thread while paint mod runs in foreground
                    if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                        _spec_ex = _shared_spec_pool
                        _spec_fut = _spec_ex.submit(compose_finish, base_id, "none", shape, zone_mask, seed + i * 13, sm, spec_mult=spec_mult, base_scale=zone_base_scale, **_v6kw)
                        _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                        if _paint_was_gpu: paint = to_cpu(paint)
                        paint = compose_paint_mod(base_id, "none", paint, shape, zone_mask, seed + i * 13, pm, bb, **_v6paint)
                        if _paint_was_gpu: paint = to_gpu(paint)
                        zone_spec = _spec_fut.result()
            else:
                # SINGLE PATTERN: original path
                label = f"{base_id}" + (f" + {pattern_id}" if pattern_id != "none" else "")
                scale_label = f" @{zone_scale:.1f}x" if zone_scale != 1.0 else ""
                rot_label = f" rot{zone_rotation:.0f}°" if zone_rotation != 0 else ""
                print(f"    [{name}] => {label} ({intensity}){scale_label}{rot_label}")
                _v6paint = {"base_strength": _v6kw.get("base_strength", 1.0), "base_spec_strength": _v6kw.get("base_spec_strength", 1.0), "base_color_mode": _v6kw.get("base_color_mode", "source"), "base_color": _v6kw.get("base_color", [1.0, 1.0, 1.0]), "base_color_source": _v6kw.get("base_color_source"), "base_color_strength": _v6kw.get("base_color_strength", 1.0), "base_color_fit_zone": _v6kw.get("base_color_fit_zone", False), "base_hue_offset": _v6kw.get("base_hue_offset", 0), "base_saturation_adjust": _v6kw.get("base_saturation_adjust", 0), "base_brightness_adjust": _v6kw.get("base_brightness_adjust", 0)}
                if _z_bb: _v6paint["blend_base"] = _z_bb; _v6paint["blend_dir"] = _z_bd; _v6paint["blend_amount"] = _z_ba
                if _z_sb or _v6kw.get("second_base_color_source"): _v6paint["second_base"] = _z_sb; _v6paint["second_base_color_source"] = _v6kw.get("second_base_color_source"); _v6paint["second_base_color"] = _v6kw.get("second_base_color", [1.0, 1.0, 1.0]); _v6paint["second_base_strength"] = _v6kw.get("second_base_strength", 0.0); _v6paint["second_base_spec_strength"] = _v6kw.get("second_base_spec_strength", 1.0); _v6paint["second_base_blend_mode"] = _v6kw.get("second_base_blend_mode", "noise"); _v6paint["second_base_noise_scale"] = _v6kw.get("second_base_noise_scale", 24); _v6paint["second_base_scale"] = _v6kw.get("second_base_scale", 1.0); _v6paint["second_base_pattern"] = _v6kw.get("second_base_pattern"); _v6paint["second_base_pattern_scale"] = _v6kw.get("second_base_pattern_scale", 1.0); _v6paint["second_base_pattern_rotation"] = _v6kw.get("second_base_pattern_rotation", 0.0); _v6paint["second_base_pattern_opacity"] = _v6kw.get("second_base_pattern_opacity", 1.0); _v6paint["second_base_pattern_strength"] = _v6kw.get("second_base_pattern_strength", 1.0); _v6paint["second_base_pattern_invert"] = _v6kw.get("second_base_pattern_invert", False); _v6paint["second_base_pattern_harden"] = _v6kw.get("second_base_pattern_harden", False); _v6paint["second_base_pattern_offset_x"] = _v6kw.get("second_base_pattern_offset_x", 0.5); _v6paint["second_base_pattern_offset_y"] = _v6kw.get("second_base_pattern_offset_y", 0.5); _v6paint["second_base_hue_shift"] = _v6kw.get("second_base_hue_shift", 0); _v6paint["second_base_saturation"] = _v6kw.get("second_base_saturation", 0); _v6paint["second_base_brightness"] = _v6kw.get("second_base_brightness", 0); _v6paint["second_base_pattern_hue_shift"] = _v6kw.get("second_base_pattern_hue_shift", 0); _v6paint["second_base_pattern_saturation"] = _v6kw.get("second_base_pattern_saturation", 0); _v6paint["second_base_pattern_brightness"] = _v6kw.get("second_base_pattern_brightness", 0)
                if _z_tb or _v6kw.get("third_base_color_source"): _v6paint["third_base"] = _z_tb; _v6paint["third_base_color_source"] = _v6kw.get("third_base_color_source"); _v6paint["third_base_color"] = _v6kw.get("third_base_color", [1.0, 1.0, 1.0]); _v6paint["third_base_strength"] = _v6kw.get("third_base_strength", 0.0); _v6paint["third_base_spec_strength"] = _v6kw.get("third_base_spec_strength", 1.0); _v6paint["third_base_blend_mode"] = _v6kw.get("third_base_blend_mode", "noise"); _v6paint["third_base_noise_scale"] = _v6kw.get("third_base_noise_scale", 24); _v6paint["third_base_scale"] = _v6kw.get("third_base_scale", 1.0); _v6paint["third_base_pattern"] = _v6kw.get("third_base_pattern"); _v6paint["third_base_pattern_scale"] = _v6kw.get("third_base_pattern_scale", 1.0); _v6paint["third_base_pattern_rotation"] = _v6kw.get("third_base_pattern_rotation", 0.0); _v6paint["third_base_pattern_opacity"] = _v6kw.get("third_base_pattern_opacity", 1.0); _v6paint["third_base_pattern_strength"] = _v6kw.get("third_base_pattern_strength", 1.0); _v6paint["third_base_pattern_invert"] = _v6kw.get("third_base_pattern_invert", False); _v6paint["third_base_pattern_harden"] = _v6kw.get("third_base_pattern_harden", False); _v6paint["third_base_pattern_offset_x"] = _v6kw.get("third_base_pattern_offset_x", 0.5); _v6paint["third_base_pattern_offset_y"] = _v6kw.get("third_base_pattern_offset_y", 0.5); _v6paint["third_base_hue_shift"] = _v6kw.get("third_base_hue_shift", 0); _v6paint["third_base_saturation"] = _v6kw.get("third_base_saturation", 0); _v6paint["third_base_brightness"] = _v6kw.get("third_base_brightness", 0)
                if _z_fb or _v6kw.get("fourth_base_color_source"): _v6paint["fourth_base"] = _z_fb; _v6paint["fourth_base_color_source"] = _v6kw.get("fourth_base_color_source"); _v6paint["fourth_base_color"] = _v6kw.get("fourth_base_color", [1.0, 1.0, 1.0]); _v6paint["fourth_base_strength"] = _v6kw.get("fourth_base_strength", 0.0); _v6paint["fourth_base_spec_strength"] = _v6kw.get("fourth_base_spec_strength", 1.0); _v6paint["fourth_base_blend_mode"] = _v6kw.get("fourth_base_blend_mode", "noise"); _v6paint["fourth_base_noise_scale"] = _v6kw.get("fourth_base_noise_scale", 24); _v6paint["fourth_base_scale"] = _v6kw.get("fourth_base_scale", 1.0); _v6paint["fourth_base_pattern"] = _v6kw.get("fourth_base_pattern"); _v6paint["fourth_base_pattern_scale"] = _v6kw.get("fourth_base_pattern_scale", 1.0); _v6paint["fourth_base_pattern_rotation"] = _v6kw.get("fourth_base_pattern_rotation", 0.0); _v6paint["fourth_base_pattern_opacity"] = _v6kw.get("fourth_base_pattern_opacity", 1.0); _v6paint["fourth_base_pattern_strength"] = _v6kw.get("fourth_base_pattern_strength", 1.0); _v6paint["fourth_base_pattern_invert"] = _v6kw.get("fourth_base_pattern_invert", False); _v6paint["fourth_base_pattern_harden"] = _v6kw.get("fourth_base_pattern_harden", False); _v6paint["fourth_base_pattern_offset_x"] = _v6kw.get("fourth_base_pattern_offset_x", 0.5); _v6paint["fourth_base_pattern_offset_y"] = _v6kw.get("fourth_base_pattern_offset_y", 0.5); _v6paint["fourth_base_hue_shift"] = _v6kw.get("fourth_base_hue_shift", 0); _v6paint["fourth_base_saturation"] = _v6kw.get("fourth_base_saturation", 0); _v6paint["fourth_base_brightness"] = _v6kw.get("fourth_base_brightness", 0)
                if _z_fif or _v6kw.get("fifth_base_color_source"): _v6paint["fifth_base"] = _z_fif; _v6paint["fifth_base_color_source"] = _v6kw.get("fifth_base_color_source"); _v6paint["fifth_base_color"] = _v6kw.get("fifth_base_color", [1.0, 1.0, 1.0]); _v6paint["fifth_base_strength"] = _v6kw.get("fifth_base_strength", 0.0); _v6paint["fifth_base_spec_strength"] = _v6kw.get("fifth_base_spec_strength", 1.0); _v6paint["fifth_base_blend_mode"] = _v6kw.get("fifth_base_blend_mode", "noise"); _v6paint["fifth_base_noise_scale"] = _v6kw.get("fifth_base_noise_scale", 24); _v6paint["fifth_base_scale"] = _v6kw.get("fifth_base_scale", 1.0); _v6paint["fifth_base_pattern"] = _v6kw.get("fifth_base_pattern"); _v6paint["fifth_base_pattern_scale"] = _v6kw.get("fifth_base_pattern_scale", 1.0); _v6paint["fifth_base_pattern_rotation"] = _v6kw.get("fifth_base_pattern_rotation", 0.0); _v6paint["fifth_base_pattern_opacity"] = _v6kw.get("fifth_base_pattern_opacity", 1.0); _v6paint["fifth_base_pattern_strength"] = _v6kw.get("fifth_base_pattern_strength", 1.0); _v6paint["fifth_base_pattern_invert"] = _v6kw.get("fifth_base_pattern_invert", False); _v6paint["fifth_base_pattern_harden"] = _v6kw.get("fifth_base_pattern_harden", False); _v6paint["fifth_base_pattern_offset_x"] = _v6kw.get("fifth_base_pattern_offset_x", 0.5); _v6paint["fifth_base_pattern_offset_y"] = _v6kw.get("fifth_base_pattern_offset_y", 0.5); _v6paint["fifth_base_hue_shift"] = _v6kw.get("fifth_base_hue_shift", 0); _v6paint["fifth_base_saturation"] = _v6kw.get("fifth_base_saturation", 0); _v6paint["fifth_base_brightness"] = _v6kw.get("fifth_base_brightness", 0)
                _v6paint["monolithic_registry"] = _v6kw.get("monolithic_registry")
                _v6paint["base_offset_x"] = _v6kw.get("base_offset_x", 0.5)
                _v6paint["base_offset_y"] = _v6kw.get("base_offset_y", 0.5)
                _v6paint["base_rotation"] = _v6kw.get("base_rotation", 0)
                _v6paint["base_flip_h"] = _v6kw.get("base_flip_h", False)
                _v6paint["base_flip_v"] = _v6kw.get("base_flip_v", False)
                # Parallel: spec in background thread while paint mod runs in foreground
                if True:  # was: ThreadPoolExecutor per-zone. Now uses _shared_spec_pool
                    _spec_ex = _shared_spec_pool
                    _spec_fut = _spec_ex.submit(compose_finish, base_id, pattern_id, shape, zone_mask, seed + i * 13, sm, scale=zone_scale, spec_mult=spec_mult, rotation=zone_rotation, base_scale=zone_base_scale, **_v6kw)
                    _paint_was_gpu = is_gpu() and hasattr(paint, '__cuda_array_interface__')
                    if _paint_was_gpu: paint = to_cpu(paint)
                    paint = compose_paint_mod(base_id, pattern_id, paint, shape, zone_mask, seed + i * 13, pm, bb, scale=zone_scale, rotation=zone_rotation, **_v6paint)
                    if _paint_was_gpu: paint = to_gpu(paint)
                    zone_spec = _spec_fut.result()
        elif finish_name and zone.get("finish_colors") and (
            finish_name.startswith("grad_") or finish_name.startswith("gradm_")
            or finish_name.startswith("grad3_") or finish_name.startswith("ghostg_")
            or finish_name.startswith("mc_")
        ):
            zone_rotation = float(zone.get("rotation", 0))
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is not None: zone_spec = _sanitize_spec_result(zone_spec, shape)
            if paint is not None: paint = _sanitize_paint_result(paint, shape)
            if zone_spec is None:
                continue
            mono_pat = zone.get("pattern", "none")
            if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
                mono_scale = float(zone.get("scale", 1.0))
                mono_opacity = float(zone.get("pattern_opacity", 1.0))
                mono_rotation = float(zone.get("rotation", 0))
                zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, shape, zone_mask, seed + i * 13 + 99, sm, mono_scale, mono_opacity, spec_mult=spec_mult, rotation=mono_rotation)
                paint = overlay_pattern_paint(paint, mono_pat, shape, zone_mask, seed + i * 13 + 99, pm, bb, mono_scale, mono_opacity, rotation=mono_rotation)
        elif finish_name and finish_name in MONOLITHIC_REGISTRY:
            spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
            mono_pat = zone.get("pattern", "none")
            mono_base_scale = float(zone.get("base_scale", 1.0))
            pat_label = f" + {mono_pat}" if mono_pat and mono_pat != "none" else ""
            print(f"    [{name}] => {finish_name}{pat_label} ({intensity}) [monolithic]")

            _mono_base_strength = max(0.0, min(2.0, float(zone.get("base_strength", 1.0))))
            _mono_spec_strength = max(0.0, min(2.0, float(zone.get("base_spec_strength", 1.0))))
            _sm_eff = sm * _mono_base_strength * _mono_spec_strength
            _pm_eff = pm * _mono_base_strength
            _bb_eff = bb * _mono_base_strength
            # --- BASE SCALE for monolithics: generate at smaller dims, tile to fill ---
            if mono_base_scale != 1.0 and mono_base_scale > 0:
                MAX_MONO_DIM = 4096
                tile_h = min(MAX_MONO_DIM, max(4, int(shape[0] / mono_base_scale)))
                tile_w = min(MAX_MONO_DIM, max(4, int(shape[1] / mono_base_scale)))
                tile_shape = (tile_h, tile_w)
                tile_mask = np.ones((tile_h, tile_w), dtype=np.float32)
                tile_spec = _sanitize_spec_result(spec_fn(tile_shape, tile_mask, seed + i * 13, _sm_eff), tile_shape)
                reps_h = int(np.ceil(shape[0] / tile_h))
                reps_w = int(np.ceil(shape[1] / tile_w))
                zone_spec = np.tile(tile_spec, (reps_h, reps_w, 1))[:shape[0], :shape[1], :]
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, _pm_eff, _bb_eff)
            else:
                zone_spec = spec_fn(shape, zone_mask, seed + i * 13, _sm_eff)
                paint = paint_fn(paint, shape, zone_mask, seed + i * 13, _pm_eff, _bb_eff)

            # Apply HSB adjustments to monolithic paint (same as base+pattern path)
            _mono_hue = float(zone.get("base_hue_offset", 0))
            _mono_sat = float(zone.get("base_saturation_adjust", 0))
            _mono_bri = float(zone.get("base_brightness_adjust", 0))
            if abs(_mono_hue) >= 0.5 or abs(_mono_sat) >= 0.5 or abs(_mono_bri) >= 0.5:
                paint = _apply_hsb_adjustments(paint, zone_mask, _mono_hue, _mono_sat, _mono_bri)

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
            # PATH 4: GENERIC FALLBACK - client-defined finish with color data
            zone_rotation = float(zone.get("rotation", 0))
            zone_spec, paint = render_generic_finish(finish_name, zone, paint, shape, zone_mask, seed + i * 13, sm, pm, bb, rotation=zone_rotation)
            if zone_spec is not None: zone_spec = _sanitize_spec_result(zone_spec, shape)
            if paint is not None: paint = _sanitize_paint_result(paint, shape)
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
        if is_gpu():
            _zs_g = to_gpu(zone_spec.astype(np.float32))
            _m3d_g = to_gpu(zone_mask[:,:,np.newaxis])
            _cs_g = to_gpu(combined_spec)
            soft = _m3d_g > 0.05
            blended = xp.clip(_zs_g * _m3d_g + _cs_g * (1 - _m3d_g), 0, 255)
            combined_spec = to_cpu(xp.where(soft, blended, _cs_g))
        else:
            mask3d = zone_mask[:,:,np.newaxis]
            soft = mask3d > 0.05
            blended = np.clip(
                zone_spec.astype(np.float32) * mask3d +
                combined_spec * (1 - mask3d),
                0, 255
            )
            combined_spec = np.where(soft, blended, combined_spec)

    # Enforce PBR floors + convert to uint8 for suit spec output
    combined_spec[:,:,1] = np.where(combined_spec[:,:,0] < 240, np.maximum(combined_spec[:,:,1], 15), combined_spec[:,:,1])
    combined_spec[:,:,2] = np.maximum(combined_spec[:,:,2], 16)
    combined_spec_u8 = np.clip(combined_spec, 0, 255).astype(np.uint8)
    os.makedirs(output_dir, exist_ok=True)
    spec_path = os.path.join(output_dir, f"suit_spec_{iracing_id}.tga")
    write_tga_32bit(spec_path, combined_spec_u8)
    Image.fromarray(combined_spec_u8).save(os.path.join(output_dir, "PREVIEW_suit_spec.png"))

    suit_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    paint_path = os.path.join(output_dir, f"suit_{iracing_id}.tga")
    write_tga_24bit(paint_path, suit_paint)
    Image.fromarray(suit_paint).save(os.path.join(output_dir, "PREVIEW_suit_paint.png"))

    elapsed = time.time() - start_time
    print(f"\n  Suit done in {elapsed:.1f}s!")
    print(f"  Spec:  {spec_path}")
    print(f"  Paint: {paint_path}")
    return suit_paint, combined_spec_u8


def build_matching_set(car_paint_file, output_dir, zones, iracing_id="23371", seed=51,
                       helmet_paint_file=None, suit_paint_file=None, import_spec_map=None, car_prefix="car_num",
                       stamp_image=None, stamp_spec_finish="gloss",
                       decal_spec_finishes=None, decal_paint_path=None, decal_mask_base64=None,
                       progress_callback=None):
    """Build car + matching helmet + matching suit in one call.

    PUBLIC, stable. Applies the SAME ``zones`` config to all three meshes
    that are provided. Helmet/suit are skipped if their paint files are
    missing (we do NOT auto-generate placeholder helmet/suit spec maps —
    that would surprise users with files they did not request).

    Args:
        car_paint_file: Path to car paint .tga/.png. Required.
        output_dir: Output directory.
        zones: Zone list applied to all meshes.
        iracing_id: iRacing customer ID for filenames.
        seed: Deterministic seed (int or str).
        helmet_paint_file: Optional helmet paint path. Skipped if missing.
        suit_paint_file: Optional suit paint path. Skipped if missing.
        import_spec_map: Optional pre-existing spec map for the car.
        car_prefix: Output prefix (default ``"car_num"``).
        stamp_image: Optional decal stamp image.
        stamp_spec_finish: Spec finish for the stamp.
        decal_spec_finishes: Optional per-zone decal finish overrides.
        decal_paint_path: Optional decal RGBA composite path.
        decal_mask_base64: Optional base64-encoded decal mask.
        progress_callback: Optional ``callable(percent, message)``.

    Returns:
        dict with keys ``car_paint``, ``car_spec`` always present, plus
        ``helmet_paint``/``helmet_spec`` and ``suit_paint``/``suit_spec``
        when their input files were provided.

    Side effects:
        Writes car/helmet/suit TGAs and PREVIEW_*.png files into output_dir.
    """
    _validate_zones(zones)
    _validate_paint_file(car_paint_file)
    seed = _coerce_seed(seed)
    logger.info(f"\n{'='*60}")
    logger.info(f"  {ENGINE_DISPLAY_NAME} - MATCHING SET BUILDER")
    logger.info(f"  Car + Helmet + Suit - One Click")
    logger.info(f"{'='*60}")
    total_start = time.time()

    results = {}

    # 1. Build car (always)
    car_paint, car_spec, zone_masks = build_multi_zone(
        car_paint_file, output_dir, zones, iracing_id, seed, import_spec_map=import_spec_map, car_prefix=car_prefix,
        stamp_image=stamp_image, stamp_spec_finish=stamp_spec_finish,
        decal_spec_finishes=decal_spec_finishes, decal_paint_path=decal_paint_path,
        decal_mask_base64=decal_mask_base64, progress_callback=progress_callback)
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
    """Apply wear/age post-processing to a rendered spec map + paint.

    PUBLIC, stable. Operates on already-rendered outputs — does NOT
    re-invoke the finish pipeline. Inputs are *not* mutated; defensive
    copies are made internally.

    Args:
        spec_map: HxWx4 uint8 RGBA (R=Metallic, G=Roughness, B=Clearcoat,
            A=SpecMask). Must already conform to iron rules.
        paint_rgb: HxWx3 uint8 RGB paint.
        wear_level: 0..100 — clamped if out of range.

            * 0   — showroom fresh (no change)
            * 25  — light track wear (micro-scratches, slight CC fade)
            * 50  — mid-season (visible scratches, roughness up, chips)
            * 75  — heavy use (deep scratches, CC loss, paint fade)
            * 100 — track-beaten veteran (severe damage, extensive CC loss)
        seed: Deterministic seed (int or str). Hashed if non-numeric.

    Returns:
        Tuple ``(modified_spec, modified_paint)`` — both fresh uint8 arrays.

    Notes:
        Iron rules (CC>=16, R>=15 for non-mirror) are re-enforced on the
        output via :func:`_enforce_iron_rules`.
    """
    if spec_map is None or paint_rgb is None:
        raise ValueError("apply_wear requires non-None spec_map and paint_rgb.")
    seed = _coerce_seed(seed)
    # Clamp wear into the valid 0..100 range so callers can't sneak negative
    # or absurd values past us.
    try:
        wear_level = max(0, min(100, int(wear_level)))
    except (TypeError, ValueError):
        wear_level = 0
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
    cc_noise = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 888)
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

    # 4. Edge wear - stronger damage at color boundaries
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
        spec[:,:,2] = np.clip(spec[:,:,2].astype(np.float32) - edge_wear * 10, 16, 255)  # CC≥16

    # Enforce iron rules centrally (CC>=CC_FLOOR, R>=ROUGHNESS_FLOOR_NONMIRROR
    # for non-mirror pixels). Single source of truth for PBR safety.
    result_spec = _enforce_iron_rules(spec)
    result_paint = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    # Release intermediate large arrays for GC (helps on tight memory boxes).
    del spec, paint
    return result_spec, result_paint


# ================================================================
# EXPORT PACKAGE BUILDER
# ================================================================

def build_export_package(output_dir, iracing_id="23371", car_folder_name=None,
                         include_helmet=True, include_suit=True,
                         wear_level=0, zones_config=None):
    """Bundle all render outputs in ``output_dir`` into a single export ZIP.

    PUBLIC, stable.

    Creates and writes (alongside whatever already lives in ``output_dir``):

    * ``shokker_config.json`` — replayable zone config.
    * ``README.txt`` — install instructions.
    * ``shokker_<id>_<folder>_<timestamp>.zip`` containing all
      ``.tga``/``.png``/``.json``/``.txt`` siblings.

    Args:
        output_dir: Directory holding car_num_*.tga + car_spec_*.tga (etc.).
        iracing_id: iRacing customer ID.
        car_folder_name: Display name for README; defaults to ``"unknown"``.
        include_helmet: Reserved (currently unused; helmet is included if its
            TGA is present in ``output_dir``).
        include_suit: Reserved (same).
        wear_level: 0..100 — recorded into config.json for replay.
        zones_config: List of JSON-serializable zone dicts. None to skip.

    Returns:
        Absolute path to the created ZIP file.

    Side effects:
        Writes README.txt, shokker_config.json, and the .zip into
        ``output_dir``.
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
            "engine_version": ENGINE_VERSION,
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

    # Create README
    readme_path = os.path.join(output_dir, "README.txt")
    readme = f"""{ENGINE_DISPLAY_NAME} - Export Package
========================================
iRacing ID: {iracing_id}
Car: {car_folder_name or 'N/A'}
Wear Level: {wear_level}/100
Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
Engine version: {ENGINE_VERSION}

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

Powered by Shokker Engine {ENGINE_VERSION}
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
    logger.info(f"\n  Export package: {zip_path}")
    logger.info(f"  Size: {zip_size / 1024 / 1024:.1f} MB")
    return zip_path


# ================================================================
# GRADIENT MASK GENERATOR
# ================================================================

_GRADIENT_CACHE = {}


def generate_gradient_mask(height, width, direction="horizontal", center=None,
                           start_pct=0.0, end_pct=1.0):
    """Generate a float32 gradient mask (0..1) for zone fade transitions.

    PUBLIC, stable. Memoized — repeated calls with identical args return a
    *copy* of the cached array (so callers can mutate freely without
    poisoning the cache).

    Args:
        height: Output rows.
        width: Output columns.
        direction: One of ``'horizontal'``, ``'vertical'``, ``'radial'``,
            ``'diagonal'``. Unknown values produce a constant 0.5 mask.
        center: ``(cx, cy)`` normalized 0..1 anchor for radial gradients.
            Defaults to the canvas center.
        start_pct: Where the gradient begins (0.0 = edge / center-for-radial).
        end_pct: Where the gradient ends (1.0 = opposite edge).

    Returns:
        ``float32`` HxW array clipped to 0..1.

    Performance:
        ``O(H*W)`` per cache miss; ``O(H*W)`` for the defensive copy on hit.
    """
    if height <= 0 or width <= 0:
        raise ValueError(f"generate_gradient_mask: positive dims required, got {height}x{width}")
    cache_key = (
        int(height), int(width), str(direction),
        tuple(center) if center else None,
        round(float(start_pct), 6), round(float(end_pct), 6),
    )
    if cache_key in _GRADIENT_CACHE:
        return _GRADIENT_CACHE[cache_key].copy()
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

    # Cap cache size so a wild caller can't blow out memory.
    if len(_GRADIENT_CACHE) < 64:
        _GRADIENT_CACHE[cache_key] = mask.copy()
    return mask


# ================================================================
# DAY/NIGHT DUAL SPEC MAP GENERATOR
# ================================================================

def generate_night_variant(day_spec, night_boost=0.7):
    """Generate a night-optimized spec map from a day spec map.

    PUBLIC, stable. The day spec is not mutated; we always operate on a copy.

    Night variant has enhanced reflectivity for track lighting:

    * Metallic boost: more reflection under spotlights.
    * Roughness reduction: sharper, more dramatic reflections.
    * Clearcoat: pushed toward CC_FLOOR (max gloss) where any CC exists.

    Args:
        day_spec: RGBA uint8 array. R=Metallic, G=Roughness, B=Clearcoat,
            A=SpecMask.
        night_boost: 0.0..1.0 strength of night enhancement. Clipped if
            out of range.

    Returns:
        ``night_spec``: RGBA uint8 array with night-optimized values, iron
        rules re-enforced.
    """
    if day_spec is None:
        raise ValueError("generate_night_variant: day_spec is None.")
    if day_spec.ndim != 3 or day_spec.shape[2] < 3:
        raise ValueError(
            f"generate_night_variant: expected HxWx{{3,4}} array, got shape {day_spec.shape}."
        )
    night = day_spec.astype(np.float32, copy=True)
    boost = float(np.clip(night_boost, 0.0, 1.0))

    # R channel = Metallic: boost reflectivity
    night[:, :, 0] = np.clip(night[:, :, 0] * (1.0 + 0.3 * boost) + 15 * boost, 0, 255)
    # G channel = Roughness: reduce for sharper reflections
    night[:, :, 1] = np.clip(night[:, :, 1] * (1.0 - 0.25 * boost) - 8 * boost, 0, 255)
    # B channel = Clearcoat: push toward CC_FLOOR (max gloss) where any CC exists
    cc = night[:, :, 2]
    cc_mask = cc > 0
    cc[cc_mask] = np.clip(cc[cc_mask] + 4 * boost, 0, CC_FLOOR)
    night[:, :, 2] = cc
    # A channel = SpecMask: untouched on purpose.
    return _enforce_iron_rules(night)


# ================================================================
# FULL RENDER PIPELINE (Car + Helmet + Suit + Wear + Export)
# ================================================================

def full_render_pipeline(car_paint_file, output_dir, zones, iracing_id="23371",
                         seed=51, helmet_paint_file=None, suit_paint_file=None,
                         wear_level=0, car_folder_name=None, export_zip=True,
                         dual_spec=False, night_boost=0.7, import_spec_map=None,
                         car_prefix="car_num", stamp_image=None, stamp_spec_finish="gloss",
                         decal_spec_finishes=None, decal_paint_path=None, decal_mask_base64=None,
                         progress_callback=None):
    """The one-call render pipeline: car + helmet + suit + wear + export.

    PUBLIC, stable. Orchestrates the four big stages and writes all files
    to ``output_dir``.

    Stages:

    1. Build matching set (car + helmet + suit) via :func:`build_matching_set`.
    2. Apply post-processing wear via :func:`apply_wear` (helmet/suit get
       progressively less wear than the car body).
    3. (Optional) Generate night spec variants via :func:`generate_night_variant`.
    4. (Optional) Build a ZIP export package via :func:`build_export_package`.

    Args:
        car_paint_file: Path to source car paint .tga/.png.
        output_dir: Directory to write all artefacts. Created if missing.
        zones: List of zone dicts (see :func:`build_multi_zone`).
        iracing_id: iRacing customer ID for filenames.
        seed: Deterministic seed (int or str).
        helmet_paint_file: Optional helmet paint source.
        suit_paint_file: Optional suit paint source.
        wear_level: 0..100 wear amount (helmet -20, suit -40).
        car_folder_name: Name used inside the export ZIP / README.
        export_zip: When True, package everything into a .zip.
        dual_spec: When True, also generate night spec variants.
        night_boost: 0..1 strength of night enhancement.
        import_spec_map: Optional path to a user-supplied spec map base.
        car_prefix: Output prefix (default ``"car_num"``).
        stamp_image: Optional decal/sticker stamp image.
        stamp_spec_finish: Spec finish to apply to the stamp (default ``"gloss"``).
        decal_spec_finishes: Per-zone decal finish overrides.
        decal_paint_path: Optional decal RGBA composite path.
        decal_mask_base64: Optional base64-encoded decal mask.
        progress_callback: Optional ``callable(percent: int, message: str)``.

    Returns:
        dict with keys:
            ``car_paint``, ``car_spec`` (np.ndarray)
            ``helmet_spec``, ``suit_spec`` (optional)
            ``car_spec_night``, ``helmet_spec_night``, ``suit_spec_night`` (optional)
            ``export_zip`` (str path, optional)

    Side effects:
        Writes TGAs, PNG previews, optional shokker_config.json + README.txt,
        and optional ZIP into ``output_dir``.
    """
    _validate_zones(zones)
    seed = _coerce_seed(seed)
    logger.info(f"\n{'*'*60}")
    logger.info(f"  {ENGINE_DISPLAY_NAME} - FULL RENDER PIPELINE")
    logger.info(f"  Car + Helmet + Suit + Wear({wear_level}) + Export")
    logger.info(f"{'*'*60}")
    pipeline_start = time.time()

    if progress_callback:
        try:
            progress_callback(0, "starting full pipeline")
        except Exception as _e:
            logger.debug(f"  [progress_callback] ignored exception: {_e}")

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Build matching set (car + helmet + suit)
    t_step1 = time.time()
    results = build_matching_set(
        car_paint_file, output_dir, zones, iracing_id, seed,
        helmet_paint_file, suit_paint_file, import_spec_map=import_spec_map,
        car_prefix=car_prefix, stamp_image=stamp_image, stamp_spec_finish=stamp_spec_finish,
        decal_spec_finishes=decal_spec_finishes, decal_paint_path=decal_paint_path,
        decal_mask_base64=decal_mask_base64,
        progress_callback=progress_callback
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

        # Wear on helmet (lighter - helmets don't get as beat up)
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

        # Wear on suit (much lighter - suits are fabric)
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
    # Concise final summary — easy to spot in long server logs.
    artefacts = sorted(k for k in results.keys() if k != "export_zip")
    logger.info(f"\n{'*'*60}")
    logger.info(f"  FULL PIPELINE COMPLETE in {pipeline_elapsed:.1f}s")
    logger.info(f"  Outputs: {len(artefacts)} arrays  ({', '.join(artefacts)})")
    if "export_zip" in results:
        try:
            zip_size_mb = os.path.getsize(results["export_zip"]) / 1024 / 1024
            logger.info(f"  Export ZIP: {os.path.basename(results['export_zip'])} ({zip_size_mb:.1f} MB)")
        except OSError:
            pass
    logger.info(f"  Engine version: {ENGINE_VERSION}")
    logger.info(f"{'*'*60}")

    if progress_callback:
        try:
            progress_callback(100, "pipeline complete")
        except Exception as _e:
            logger.debug(f"  [progress_callback] ignored exception: {_e}")

    return results


# ================================================================
# MAIN — basic smoke test (run: python shokker_engine_v2.py)
# Verifies: imports, registries populated, helpers return sane shapes.
# Does NOT touch the filesystem or run a full render.
# ================================================================
if __name__ == '__main__':
    import sys

    failures = []

    def _check(name, cond, detail=""):
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {name}{(' — ' + detail) if detail else ''}")
        if not cond:
            failures.append(name)

    print(f"\n{ENGINE_DISPLAY_NAME} smoke test (engine version {ENGINE_VERSION})")
    print("=" * 60)

    _check("ENGINE_VERSION is a non-empty string",
           isinstance(ENGINE_VERSION, str) and bool(ENGINE_VERSION),
           ENGINE_VERSION)
    _check("BASE_REGISTRY populated",
           isinstance(BASE_REGISTRY, dict) and len(BASE_REGISTRY) > 50,
           f"{len(BASE_REGISTRY)} bases")
    _check("PATTERN_REGISTRY populated",
           isinstance(PATTERN_REGISTRY, dict) and len(PATTERN_REGISTRY) > 50,
           f"{len(PATTERN_REGISTRY)} patterns")
    _check("FINISH_REGISTRY populated",
           isinstance(FINISH_REGISTRY, dict) and len(FINISH_REGISTRY) > 0,
           f"{len(FINISH_REGISTRY)} finishes")
    _check("MONOLITHIC_REGISTRY populated",
           isinstance(MONOLITHIC_REGISTRY, dict) and len(MONOLITHIC_REGISTRY) > 50,
           f"{len(MONOLITHIC_REGISTRY)} monolithics")

    # Helper functions
    _check("_coerce_seed('hello') is deterministic",
           _coerce_seed("hello") == _coerce_seed("hello"))
    _check("_coerce_seed(None) -> default",
           _coerce_seed(None) == 51 & 0xFFFFFFFF)
    _check("_coerce_seed(123) -> 123", _coerce_seed(123) == 123)

    # Iron-rule enforcement
    _spec_test = np.zeros((4, 4, 4), dtype=np.uint8)
    _spec_test[:, :, 2] = 5  # bad CC value (1-15)
    _spec_test[:, :, 1] = 0  # bad R for non-mirror
    _safe = _enforce_iron_rules(_spec_test)
    _check("_enforce_iron_rules raises CC>=16",
           int(_safe[:, :, 2].min()) == CC_FLOOR,
           f"min CC = {int(_safe[:, :, 2].min())}")
    _check("_enforce_iron_rules raises R>=15 for non-mirror",
           int(_safe[:, :, 1].min()) == ROUGHNESS_FLOOR_NONMIRROR,
           f"min R = {int(_safe[:, :, 1].min())}")

    # Gradient mask
    _g = generate_gradient_mask(32, 64, "horizontal")
    _check("generate_gradient_mask shape",
           _g.shape == (32, 64) and _g.dtype == np.float32,
           f"{_g.shape} {_g.dtype}")
    _check("gradient bounds",
           0.0 <= float(_g.min()) and float(_g.max()) <= 1.0)

    # Zone validation surfaces friendly errors
    try:
        _validate_zones(None)
        _check("_validate_zones(None) raises", False, "no exception")
    except ValueError:
        _check("_validate_zones(None) raises", True)

    # Cache stats
    _stats = get_cache_stats()
    _check("get_cache_stats returns dict with engine_version",
           isinstance(_stats, dict) and _stats.get("engine_version") == ENGINE_VERSION)

    print("=" * 60)
    if failures:
        print(f"  RESULT: {len(failures)} failure(s) — {failures}")
        sys.exit(1)
    else:
        print("  RESULT: all checks passed")
        sys.exit(0)



# ================================================================
# END OF ENGINE - Dead duplicate block (2,673 lines) removed
# 2026-03-11. Backup: _archive/shokker_engine_v2_pre_dedup.py
# ================================================================
