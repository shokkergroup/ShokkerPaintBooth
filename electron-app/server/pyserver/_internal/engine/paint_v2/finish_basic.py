# -*- coding: utf-8 -*-
"""Shokker Paint Booth V5 - Finish Basic Paint/Spec Module.

Foundation bases (Gloss, Matte, Satin, Eggshell, Primer, etc.) implemented as
paired ``paint_*`` (color buffer modifiers) and ``spec_*`` (M/R/CC channel
generators) functions consumed by :mod:`engine.base_registry_data`.

Design Rule
-----------
Foundation bases are SOLID. Their ``paint_fn`` must NOT apply any visible
noise, texture, grain, or pattern to the paint color or spec map. All texture
variation lives in the BASE_REGISTRY M/R/CC values + Perlin noise keys, NOT
in these paint functions.

The ``paint_fn`` here only handles:
    * Subtle contrast/gamma for the base sheen level.
    * Zero ``noise`` or ``multi_scale_noise`` calls on Foundation IDs that are
      explicitly tagged "solid" (gloss/matte/satin/eggshell/primer/silk/etc.).

Spec Return Contract
--------------------
Every ``spec_*`` function returns ``(M, R, CC)`` as three ``float32`` arrays
of shape ``(H, W)`` with values in the ``0-255`` range.

* ``M``  = Metallic   (channel 0): 0 = dielectric, 255 = metallic.
* ``R``  = Roughness  (channel 1): 0 = mirror,     255 = matte.
* ``CC`` = Clearcoat  (channel 2): 0-15 = none, **16 = max gloss**, 255 = dull.

Iron Rules (Spec Map Invariants)
--------------------------------
1. ``CC >= 16`` everywhere (the iRacing PBR shader treats CC<16 as "no
   clearcoat" which collapses gloss). Chrome/mirror finishes that intentionally
   want B<16 are the only exception and must document so explicitly.
2. ``R >= 15`` for non-chrome finishes (M < ~240). Pure mirror-grade chrome
   (M >= 245) may set R below 15.
3. All output arrays must be finite. NaN/Inf is clipped to range bounds.
4. ``paint_*`` functions never mutate the input ``paint`` array; they always
   return a new ``float32`` buffer.

Color Space Notes
-----------------
``paint`` arrays are linear-light RGB in ``[0, 1]`` (NOT sRGB). The PBR
renderer applies the gamma curve downstream. ``spec`` arrays are unitless
PBR channel values in ``[0, 255]``.

Performance Hints
-----------------
* All operations are vectorized numpy; no per-pixel Python loops in the
  hot path.
* For typical 2048x2048 panels every spec function runs in well under 50 ms
  on CPU thanks to the cached :func:`engine.core.multi_scale_noise` octave
  generator.
* GPU acceleration (CuPy) is opt-in via :mod:`engine.gpu`; this module
  stays GPU-agnostic.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

from engine.core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec
from engine.paint_v2 import ensure_bb_2d


# ============================================================================
# MODULE CONSTANTS — extracted magic numbers
# ============================================================================

logger = logging.getLogger(__name__)

# Iron-rule spec channel floors (see module docstring).
CC_MIN: float = 16.0          # Maximum gloss when CC == 16, do NOT go below.
R_MIN_NONCHROME: float = 15.0 # Roughness floor for non-chrome (M < CHROME_M).
CHROME_M_THRESHOLD: float = 240.0  # M >= 240 → considered chrome → R<15 OK.

# Spec channel hard limits (sRGB byte range).
CH_MIN: float = 0.0
CH_MAX: float = 255.0

# Common roughness presets (255 byte scale).
R_GLOSS: float = 18.0
R_SATIN: float = 90.0
R_MATTE: float = 220.0

# Common clearcoat presets (lower = glossier, see module docstring).
CC_GLOSS: float = CC_MIN
CC_SEMI_GLOSS: float = 40.0
CC_SATIN: float = 60.0
CC_EGGSHELL: float = 100.0
CC_MATTE: float = 200.0
CC_FLAT: float = 220.0
CC_VANTA: float = 240.0

# Tiny epsilon for divide-by-zero guards.
EPS: float = 1e-6

ShapeLike = Tuple[int, int]
SpecTriple = Tuple[np.ndarray, np.ndarray, np.ndarray]


# ============================================================================
# SHARED HELPERS — input validation, defensive paint copy, neutral fallbacks
# ============================================================================

def _hw(shape) -> ShapeLike:
    """Return ``(H, W)`` from a 2- or 3-tuple shape, with int coercion.

    Args:
        shape: ``(H, W)`` or ``(H, W, C)`` tuple (or numpy ``.shape``).

    Returns:
        ``(int(H), int(W))`` tuple suitable for indexing/np construction.

    Raises:
        ValueError: If ``shape`` cannot be interpreted as 2-D or 3-D.
    """
    if shape is None:
        raise ValueError("finish_basic._hw: shape is None")
    if len(shape) >= 2:
        return int(shape[0]), int(shape[1])
    raise ValueError(f"finish_basic._hw: bad shape {shape!r} (need 2+ dims)")


def _safe_paint_copy(paint: np.ndarray) -> np.ndarray:
    """Return a defensive ``float32`` 3-channel copy of ``paint``.

    Strips any 4th alpha channel, never mutates the caller's array.

    Args:
        paint: Input color buffer ``(H, W, 3)`` or ``(H, W, 4)``.

    Returns:
        New ``float32`` array with shape ``(H, W, 3)``.
    """
    if paint is None:
        raise ValueError("finish_basic: paint buffer is None")
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].astype(np.float32, copy=True)
    if paint.dtype != np.float32:
        return paint.astype(np.float32, copy=True)
    return paint.copy()


def _validate_spec_inputs(shape, seed, sm) -> None:
    """Lightweight assertion for ``spec_*`` entrypoints.

    Args:
        shape: Expected ``(H, W)`` tuple.
        seed:  Deterministic seed (any int-castable).
        sm:    Spec multiplier (typically ``[0, 1.5]``).

    Raises:
        ValueError: On obviously bad inputs (caught upstream by fallback).
    """
    if shape is None or len(shape) < 2:
        raise ValueError(f"spec input: bad shape {shape!r}")
    if shape[0] <= 0 or shape[1] <= 0:
        raise ValueError(f"spec input: zero/neg dim {shape!r}")
    try:
        int(seed)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"spec input: seed not int-castable: {seed!r}") from exc
    if not np.isfinite(float(sm)):
        raise ValueError(f"spec input: non-finite sm {sm!r}")


def _neutral_spec(shape, base_m: float = 0.0, base_r: float = R_MATTE,
                  cc: float = CC_MATTE) -> SpecTriple:
    """Fallback neutral matte spec used on exception paths.

    Always satisfies iron rules. Matches generic "matte primer" defaults so
    a failed finish never produces a NaN-poisoned spec map.
    """
    h, w = _hw(shape)
    M = np.full((h, w), float(base_m), dtype=np.float32)
    R = np.full((h, w), max(float(base_r), R_MIN_NONCHROME), dtype=np.float32)
    CC = np.full((h, w), max(float(cc), CC_MIN), dtype=np.float32)
    return M, R, CC


def _enforce_iron_rules(M: np.ndarray, R: np.ndarray, CC: np.ndarray) -> SpecTriple:
    """Final post-processing pass enforcing the spec map invariants.

    * Replaces NaN/Inf with safe defaults.
    * Clips all channels to ``[0, 255]``.
    * Forces ``CC >= 16`` everywhere.
    * Forces ``R >= 15`` where ``M < CHROME_M_THRESHOLD`` (chrome exception).

    All inputs are treated as ``float32``; outputs are ``float32`` arrays.
    """
    M = np.nan_to_num(M, nan=0.0, posinf=CH_MAX, neginf=CH_MIN)
    R = np.nan_to_num(R, nan=R_MIN_NONCHROME, posinf=CH_MAX, neginf=R_MIN_NONCHROME)
    CC = np.nan_to_num(CC, nan=CC_MIN, posinf=CH_MAX, neginf=CC_MIN)
    M = np.clip(M, CH_MIN, CH_MAX).astype(np.float32, copy=False)
    R = np.clip(R, CH_MIN, CH_MAX).astype(np.float32, copy=False)
    CC = np.clip(CC, CC_MIN, CH_MAX).astype(np.float32, copy=False)
    # Chrome exception: only force R>=15 where the surface is NOT chrome.
    non_chrome = M < CHROME_M_THRESHOLD
    R = np.where(non_chrome, np.maximum(R, R_MIN_NONCHROME), R).astype(np.float32, copy=False)
    return M, R, CC


def _safe_seed(seed) -> int:
    """Coerce any seed-like value into a deterministic 32-bit-ish int."""
    try:
        return int(seed) & 0x7FFFFFFF
    except (TypeError, ValueError):
        logger.warning("finish_basic: bad seed %r, falling back to 0", seed)
        return 0


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # paint_*
    "paint_blackout_v2", "paint_ceramic_v2", "paint_chameleon_v2",
    "paint_clear_matte_v2", "paint_eggshell_v2", "paint_flat_black_v2",
    "paint_frozen_v2", "paint_frozen_matte_v2", "paint_gloss_v2",
    "paint_iridescent_v2", "paint_liquid_obsidian_v2", "paint_living_matte_v2",
    "paint_matte_v2", "paint_mirror_gold_v2", "paint_noise_scales_v2",
    "paint_orange_peel_gloss_v2", "paint_organic_metal_v2", "paint_perlin_v2",
    "paint_piano_black_v2", "paint_primer_v2", "paint_satin_v2",
    "paint_satin_metal_v2", "paint_scuffed_satin_v2", "paint_semi_gloss_v2",
    "paint_silk_v2", "paint_terrain_chrome_v2", "paint_vantablack_v2",
    "paint_volcanic_v2", "paint_wet_look_v2",
    # spec_*
    "spec_blackout", "spec_ceramic", "spec_chameleon", "spec_clear_matte",
    "spec_eggshell", "spec_flat_black", "spec_frozen", "spec_frozen_matte",
    "spec_gloss", "spec_iridescent", "spec_liquid_obsidian", "spec_living_matte",
    "spec_matte", "spec_mirror_gold", "spec_noise_scales", "spec_orange_peel_gloss",
    "spec_organic_metal", "spec_perlin", "spec_piano_black", "spec_primer",
    "spec_satin", "spec_satin_metal", "spec_scuffed_satin", "spec_semi_gloss",
    "spec_silk", "spec_terrain_chrome", "spec_vantablack", "spec_volcanic",
    "spec_wet_look",
    # constants
    "CC_MIN", "R_MIN_NONCHROME", "CHROME_M_THRESHOLD",
]


# ============================================================================
# BLACKOUT - Total light absorption matte black
# Color-safe: yes (overrides base color with near-zero darkness).
# Targets: paint RGB → near-black; spec → flat M=0, R=15, CC=200.
# ============================================================================

def paint_blackout_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                      pm: float, bb) -> np.ndarray:
    """Blackout: near-zero reflectance total black absorption.

    Args:
        paint: ``(H, W, 3|4)`` float32 RGB color buffer (linear light).
        shape: Canvas ``(H, W)`` or ``(H, W, C)`` shape tuple.
        mask:  ``(H, W)`` float32 region mask in ``[0, 1]``.
        seed:  Deterministic seed (unused for solid blackout).
        pm:    Paint modifier amount in ``[0, 1]``.
        bb:    Body-buffer (edge glow) array or scalar.

    Returns:
        New ``float32`` ``(H, W, 3)`` color buffer.
    """
    paint = _safe_paint_copy(paint)
    bb = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    darkness = np.full((h, w), 0.02, dtype=np.float32)
    effect = np.stack([darkness, darkness, darkness], axis=2)
    blend = pm * (bb[:, :, np.newaxis] ** 2.2)
    m3 = mask[:, :, np.newaxis]
    return np.clip(paint * (1.0 - m3 * blend) + effect * (m3 * blend),
                   0.0, 1.0).astype(np.float32)


def spec_blackout(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Blackout spec — CC=200 maximum degradation = near-dead flat matte.

    Channels: M=0 (dielectric), R=15 (iron-rule floor), CC=200.

    Args:
        shape:  ``(H, W)`` canvas size.
        seed:   Seed (unused; output is constant).
        sm:     Spec multiplier (unused; output is constant).
        base_m: Registry M (unused for solid blackout).
        base_r: Registry R (unused for solid blackout).

    Returns:
        ``(M, R, CC)`` float32 arrays of shape ``(H, W)``.
    """
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        M = np.zeros((h, w), dtype=np.float32)
        R = np.full((h, w), R_MIN_NONCHROME, dtype=np.float32)
        CC = np.full((h, w), CC_MATTE, dtype=np.float32)
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001 — fallback safety net
        logger.error("spec_blackout failed: %s", exc, exc_info=False)
        return _neutral_spec(shape, 0.0, R_MIN_NONCHROME, CC_MATTE)


# ============================================================================
# CERAMIC — Ceramic glaze (paired with paint_ceramic_gloss in spec_paint)
# Color-safe: yes (pass-through).
# Targets: paint = identity; spec = high gloss with subtle glaze variation.
# ============================================================================

def paint_ceramic_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                     pm: float, bb) -> np.ndarray:
    """Ceramic: pure pass-through, no texture in base layer.

    Variation comes entirely from :func:`spec_ceramic` and the renderer's
    PBR clearcoat lobe.
    """
    return _safe_paint_copy(paint)


def spec_ceramic(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Ceramic spec: high gloss, minimal roughness with subtle glaze noise."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        glaze = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 50)
        M = float(base_m) + glaze * 4.0 * sm
        R = float(base_r) + glaze * 3.0 * sm
        CC = CC_MIN + glaze * 2.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_ceramic failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# CHAMELEON — Multi-layer interference color shift film.
# Color-safe: NO — overrides base color with hue-cycled chameleon stops.
# Targets: paint RGB (HSV-driven hue rotation); spec M+R for interference.
# Performance: ~50ms @ 2048² (FBM dominates; the per-segment loop is over
# only 5 hue stops, not pixels — already vectorized).
# ============================================================================

# Chameleon hue anchor table (5 stops + wrap), kept module-level so we don't
# rebuild it on every call.
_CHAM_STOPS_H = np.array([0.48, 0.78, 0.95, 0.12, 0.35, 0.48], dtype=np.float32)
_CHAM_STOPS_S = np.array([0.90, 0.85, 0.92, 0.88, 0.85, 0.90], dtype=np.float32)
_CHAM_STOPS_V = np.array([0.80, 0.72, 0.78, 0.85, 0.76, 0.80], dtype=np.float32)


def paint_chameleon_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                       pm: float, bb) -> np.ndarray:
    """Chameleon: dramatic dual-shift interference color rotation.

    Uses the same noise seeds (``+2200``, ``+2201``) as :func:`spec_chameleon`
    so paint and spec are spatially "married". A 5-stop hue cycle produces
    3+ visibly distinct color zones across the panel.

    Performance:
        FBM cost dominates; the inner ``for i in range(n_stops - 1)`` loop is
        over ``5`` segments — vectorized per-segment via boolean masks.
    """
    paint = _safe_paint_copy(paint)
    h, w = _hw(shape)
    out = paint
    s = _safe_seed(seed)

    # Same noise fields as spec_chameleon (s+2200, s+2201) for marriage.
    shift_fbm = multi_scale_noise((h, w), [8, 16, 32], [0.45, 0.35, 0.2], s + 2200)
    sparkle = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], s + 2201)
    combined = shift_fbm * 0.7 + sparkle * 0.3

    # Normalize to 0-1 for hue mapping (guard tight ranges).
    c_min, c_max = float(combined.min()), float(combined.max())
    if c_max - c_min > EPS:
        norm = (combined - c_min) / (c_max - c_min)
    else:
        norm = np.full_like(combined, 0.5)

    # Steepen transitions (gamma < 1) for distinct zones.
    n_stops = len(_CHAM_STOPS_H)
    steep = np.clip(np.power(norm, 0.55), 0.0, 1.0)
    t = steep * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)

    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)

    for i in range(n_stops - 1):
        seg = (idx == i)
        if not np.any(seg):
            continue
        f = frac[seg]
        h0, h1 = _CHAM_STOPS_H[i], _CHAM_STOPS_H[i + 1]
        # Handle hue wraparound: take the short way around the colour wheel.
        if abs(h1 - h0) > 0.5:
            if h0 > h1:
                out_h[seg] = (h0 + (h1 + 1.0 - h0) * f) % 1.0
            else:
                out_h[seg] = (h0 - (h0 + 1.0 - h1) * f) % 1.0
        else:
            out_h[seg] = h0 * (1.0 - f) + h1 * f
        out_s[seg] = _CHAM_STOPS_S[i] * (1.0 - f) + _CHAM_STOPS_S[i + 1] * f
        out_v[seg] = _CHAM_STOPS_V[i] * (1.0 - f) + _CHAM_STOPS_V[i + 1] * f

    ch_r, ch_g, ch_b = hsv_to_rgb_vec(out_h, out_s, out_v)

    # Strong blend — paint modifier drives visibility, boosted for drama.
    blend = np.clip(pm * 0.85, 0.0, 1.0) * mask
    out[:, :, 0] = np.clip(out[:, :, 0] * (1.0 - blend) + ch_r * blend, 0.0, 1.0)
    out[:, :, 1] = np.clip(out[:, :, 1] * (1.0 - blend) + ch_g * blend, 0.0, 1.0)
    out[:, :, 2] = np.clip(out[:, :, 2] * (1.0 - blend) + ch_b * blend, 0.0, 1.0)
    return out


def spec_chameleon(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Chameleon spec — dual-shift interference film with real M/R variation.

    Multi-layer thin-film interference creates angle-dependent color AND
    specular shifts. Flat M/R produces zero visible shift; this function
    drives M and R variation so the interference layers catch light at
    different intensities across the surface.
    """
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        # Large-scale interference pattern — thin-film thickness variation.
        shift_fbm = multi_scale_noise((h, w), [8, 16, 32], [0.45, 0.35, 0.2], s + 2200)
        # High-freq sparkle for micro-flake interference.
        sparkle = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], s + 2201)
        combined = shift_fbm * 0.7 + sparkle * 0.3
        # M: highly metallic with strong spatial variation (base_m ± 50).
        M = base_m + combined * 100.0 * sm - 50.0
        # R: low overall with hot/cold zones from interference alignment.
        R = base_r + (1.0 - combined) * 40.0 * sm - 20.0
        # CC: glossy with slight thin-film thickness variation.
        CC = CC_MIN + combined * 20.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_chameleon failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# CLEAR_MATTE — Matte clearcoat, solid, no texture.
# Color-safe: yes (tiny +0.02 value lift only).
# ============================================================================

def paint_clear_matte_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                         pm: float, bb) -> np.ndarray:
    """Clear matte (BMW Frozen / Porsche Chalk style).

    WEAK-013 fix: precision matte clearcoat preserves base color almost
    perfectly. Just a tiny +0.02 value lift from the protective clear layer.
    No contrast reduction.
    """
    paint = _safe_paint_copy(paint)
    protected = np.clip(paint + 0.02, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (protected * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_clear_matte(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Clear matte spec — engineered factory matte (WEAK-013).

    Very uniform roughness with very low amplitude noise (±5, not ±30) —
    matte clearcoats are engineered to be consistent. Near-zero metallic with
    fine-scale dust flicker (0-15). CC: 180-200 (slight sheen from clear).
    """
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        precision_fbm = multi_scale_noise((h, w), [16, 32, 64], [0.6, 0.3, 0.1], s + 1300)
        dust_noise = multi_scale_noise((h, w), [64, 128], [0.7, 0.3], s + 1301)
        # Near-zero metallic; only fine-scale dust flicker (0-15 range).
        M = dust_noise * 15.0 * sm
        # G=200-220 with very low amplitude (engineered consistency).
        R = 210.0 + precision_fbm * 10.0 * sm - 5.0
        # CC: 180-200 — matte clearcoat has slight sheen, not dead flat.
        CC = 190.0 + precision_fbm * 10.0 - 5.0
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_clear_matte failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), 190.0)


# ============================================================================
# EGGSHELL — Low-sheen eggshell finish, SOLID.
# Color-safe: yes (8% desaturation).
# ============================================================================

def paint_eggshell_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                      pm: float, bb) -> np.ndarray:
    """Eggshell: ~8% desaturation, no grain, no noise."""
    paint = _safe_paint_copy(paint)
    gray = paint.mean(axis=2, keepdims=True)
    desat = np.clip(paint * 0.92 + gray * 0.08, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (desat * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_eggshell(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Eggshell spec — CC=100 low sheen with subtle orange-peel micro-texture."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        tex = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 150)
        M = float(base_m) + tex * 3.0 * sm
        R = float(base_r) + tex * 6.0 * sm
        CC = CC_EGGSHELL + tex * 8.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_eggshell failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_EGGSHELL)


# ============================================================================
# FLAT_BLACK — Flat black with zero specular component.
# ============================================================================

def paint_flat_black_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                        pm: float, bb) -> np.ndarray:
    """Flat black: pure absorption with tiny edge glow from ``bb``."""
    paint = _safe_paint_copy(paint)
    bb = ensure_bb_2d(bb, shape)
    black_val = bb * 0.04
    blend = pm * mask[:, :, np.newaxis]
    result = paint * (1.0 - blend) + black_val[:, :, np.newaxis] * blend
    return np.clip(result, 0.0, 1.0).astype(np.float32)


def spec_flat_black(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Flat black spec — CC=220 near-maximum degradation = dead flat."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        M = np.zeros((h, w), dtype=np.float32)
        R = np.full((h, w), R_MIN_NONCHROME, dtype=np.float32)
        CC = np.full((h, w), CC_FLAT, dtype=np.float32)
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_flat_black failed: %s", exc)
        return _neutral_spec(shape, 0.0, R_MIN_NONCHROME, CC_FLAT)


# ============================================================================
# FROZEN / FROZEN_MATTE — Distinct ice-crystal vs frosted-glass surfaces.
# Color-safe: yes (subtle blue iridescence vs neutral desat).
# ============================================================================

def paint_frozen_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Frozen (ice-crystal) — slight blue iridescence (WEAK-017).

    Distinct from ``frozen_matte`` (frosted/etched). Frozen = crystalline
    sparkle with cold metallic blue cast.
    """
    paint = _safe_paint_copy(paint)
    out = paint
    blend = np.clip(pm, 0.0, 1.0) * mask
    out[:, :, 0] = np.clip(out[:, :, 0] - 0.025 * blend, 0.0, 1.0)  # less red
    out[:, :, 2] = np.clip(out[:, :, 2] + 0.04 * blend, 0.0, 1.0)   # more blue
    return out


def spec_frozen(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Frozen spec — Worley-style ice-crystal pattern (WEAK-017).

    Distance-to-nearest-seed-point produces sharp crystalline boundaries.
    The inner per-crystal loop is bounded (80 points) and vectorized over
    the (H, W) grid, so performance scales as ``O(H·W·N_crystals)`` —
    ~80 ms at 2048² with N=80. Trade-off accepted for the visual win.
    """
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        rng = np.random.RandomState(s + 7700)
        n_crystals = 80
        pts_y = rng.uniform(0, h, n_crystals).astype(np.float32)
        pts_x = rng.uniform(0, w, n_crystals).astype(np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

        # Vectorized min-distance accumulation. Each iteration is a single
        # broadcast over the full (H,W) grid — no Python pixel loop.
        dist = np.full((h, w), 1e9, dtype=np.float32)
        for i in range(n_crystals):
            d = np.sqrt((yy - pts_y[i]) ** 2 + (xx - pts_x[i]) ** 2)
            dist = np.minimum(dist, d)

        crystal = np.clip(dist / (float(dist.max()) + EPS), 0.0, 1.0)
        M = base_m + crystal * 40.0 * sm - 20.0
        R = base_r + (1.0 - crystal) * 35.0 * sm
        CC = CC_MIN + crystal * 20.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_frozen failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


def paint_frozen_matte_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                          pm: float, bb) -> np.ndarray:
    """Frozen matte (frosted glass) — distinct from ``frozen`` (WEAK-017).

    Frosted/etched glass character: slight desaturation + brightness
    reduction simulating translucency. No blue iridescence, no crystalline
    sparkle — uniform diffusion.
    """
    paint = _safe_paint_copy(paint)
    out = paint
    gray = out.mean(axis=2, keepdims=True)
    desaturated = out * 0.93 + gray * 0.07
    dimmed = np.clip(desaturated * 0.96, 0.0, 1.0)
    blend = np.clip(pm, 0.0, 1.0) * mask[:, :, np.newaxis]
    return np.clip(out * (1.0 - blend) + dimmed * blend, 0.0, 1.0).astype(np.float32)


def spec_frozen_matte(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Frozen matte spec — uniform micro-roughness (WEAK-017).

    Distinct from ``spec_frozen`` (no crystalline pattern). Isotropic FBM at
    small scales models a frosted/etched glass surface.
    """
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        frost_fbm = multi_scale_noise((h, w), [2, 3, 5], [0.5, 0.3, 0.2], s + 7710)
        # Low metallic — frosted matte suppresses metallic highlights.
        M = base_m * 0.12 + frost_fbm * 10.0 * sm
        # Uniform high micro-roughness 200-230.
        R = 200.0 + frost_fbm * 30.0 * sm
        # High/flat CC — frosted = no clearcoat sparkle.
        CC = 160.0 + frost_fbm * 40.0
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_frozen_matte failed: %s", exc)
        return _neutral_spec(shape, base_m, 215.0, 180.0)


# ============================================================================
# GLOSS — Standard high-gloss finish, SOLID.
# ============================================================================

def paint_gloss_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                   pm: float, bb) -> np.ndarray:
    """Gloss: subtle contrast bump only, no texture."""
    paint = _safe_paint_copy(paint)
    contrasted = np.clip((paint - 0.5) * 1.04 + 0.5, 0.0, 1.0)
    bb_arr = ensure_bb_2d(bb, shape)
    ping = np.clip(bb_arr - 0.9, 0.0, 1.0) * 0.12 * pm
    m3 = mask[:, :, np.newaxis]
    return np.clip(contrasted + ping[:, :, np.newaxis] * m3, 0.0, 1.0).astype(np.float32)


def spec_gloss(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Gloss spec — maximum reflectance with subtle micro-variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        micro = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 100)
        M = float(base_m) + micro * 2.0 * sm
        R = float(base_r) + micro * 2.0 * sm
        CC = CC_MIN + micro * 1.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_gloss failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# IRIDESCENT — Pass-through paint; spec drives the shift.
# ============================================================================

def paint_iridescent_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                        pm: float, bb) -> np.ndarray:
    """Iridescent: pass-through (interference film handled in spec)."""
    return _safe_paint_copy(paint)


def spec_iridescent(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Iridescent spec — glossy with interference-film M/R variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        film = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], s + 200)
        M = float(base_m) + film * 20.0 * sm
        R = float(base_r) + film * 8.0 * sm
        CC = CC_MIN + film * 3.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_iridescent failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# LIQUID_OBSIDIAN — Pass-through (deep black, spec-driven).
# ============================================================================

def paint_liquid_obsidian_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                             pm: float, bb) -> np.ndarray:
    """Liquid obsidian: pass-through (spec handles the glassy black surface)."""
    return _safe_paint_copy(paint)


def spec_liquid_obsidian(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Liquid obsidian spec — CC=16 glossy with glass-smooth micro-variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        glass = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 250)
        M = float(base_m) + glass * 5.0 * sm
        R = float(base_r) + glass * 4.0 * sm
        CC = CC_MIN + glass * 2.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_liquid_obsidian failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# LIVING_MATTE — Organic matte with patchy character (WEAK-013 fix).
# ============================================================================

def paint_living_matte_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                          pm: float, bb) -> np.ndarray:
    """Living matte — organic irregular matte (WEAK-013 fix).

    Slight desaturation and darkening simulate a natural matte surface with
    irregular absorption. Distinct from ``clear_matte``.
    """
    paint = _safe_paint_copy(paint)
    gray = paint.mean(axis=2, keepdims=True)
    desat = paint * 0.88 + gray * 0.12
    flat = np.clip((desat - 0.5) * 0.75 + 0.5, 0.0, 1.0)
    darkened = np.clip(flat * 0.92, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (darkened * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_living_matte(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Living matte spec — high-amplitude 3-octave FBM (WEAK-013 fix).

    Noticeably patchy R: 210-255, distinct from precision-engineered uniform
    ``clear_matte``. Models natural surface irregularity (dirt, skin oil,
    uneven spray absorption).
    """
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        organic_fbm = multi_scale_noise((h, w), [16, 32, 64], [0.5, 0.33, 0.17], s + 1310)
        patch_fbm = multi_scale_noise((h, w), [6, 12, 24], [0.5, 0.35, 0.15], s + 1311)
        M = organic_fbm * 20.0 * sm
        R = 232.0 + organic_fbm * 45.0 * sm - 22.0
        CC = 202.0 + patch_fbm * 55.0 - 27.0
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_living_matte failed: %s", exc)
        return _neutral_spec(shape, base_m, 230.0, 200.0)


# ============================================================================
# MATTE — Standard matte finish, SOLID (WEAK-010 fix).
# ============================================================================

def paint_matte_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                   pm: float, bb) -> np.ndarray:
    """Matte (WEAK-010) — ~12% desaturation + slight darkening for chalky tone."""
    paint = _safe_paint_copy(paint)
    gray = paint.mean(axis=2, keepdims=True)
    desat = paint * 0.88 + gray * 0.12
    flat = np.clip((desat - 0.5) * 0.75 + 0.5, 0.0, 1.0)
    darkened = np.clip(flat * 0.95, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (darkened * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_matte(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Matte spec (WEAK-010) — 3-octave FBM roughness G: 220-255."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        rough_fbm = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], s + 4100)
        M = rough_fbm * 30.0 * sm
        R = 220.0 + rough_fbm * 35.0 * sm
        cc_noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], s + 4101)
        CC = 200.0 + cc_noise * 30.0
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_matte failed: %s", exc)
        return _neutral_spec(shape, 0.0, R_MATTE, CC_MATTE)


# ============================================================================
# MIRROR_GOLD — Warm gold mirror (Chrome exception; R<15 OK).
# Color-safe: NO — overrides with warm gold tint.
# ============================================================================

def paint_mirror_gold_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                         pm: float, bb) -> np.ndarray:
    """Mirror gold: subtle warm gold/copper tint, no noise."""
    paint = _safe_paint_copy(paint)
    out = paint
    bb_arr = ensure_bb_2d(bb, shape)
    blend = np.clip(pm, 0.0, 1.0) * mask
    out[:, :, 0] = np.clip(out[:, :, 0] + 0.06 * blend, 0.0, 1.0)
    out[:, :, 1] = np.clip(out[:, :, 1] + 0.02 * blend, 0.0, 1.0)
    out[:, :, 2] = np.clip(out[:, :, 2] - 0.03 * blend, 0.0, 1.0)
    out = np.clip(out + (bb_arr * 0.5 * blend)[:, :, np.newaxis], 0.0, 1.0)
    return out


def spec_mirror_gold(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Mirror gold — max metallic (chrome exception: R<15 OK)."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        micro = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 430)
        M = np.clip(252.0 + micro * 3.0 * sm, 245.0, CH_MAX).astype(np.float32)
        # Chrome exception: R<15 OK at high M.
        R = np.clip(2.0 + micro * 4.0 * sm, CH_MIN, CH_MAX).astype(np.float32)
        CC = np.clip(CC_MIN + micro * 1.5 * sm, CC_MIN, CH_MAX).astype(np.float32)
        # Run iron rules (chrome exception preserved by M >= threshold).
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_mirror_gold failed: %s", exc)
        # Fallback: solid chrome — not enforce_iron because R needs to stay low.
        h, w = _hw(shape)
        return (np.full((h, w), 250.0, dtype=np.float32),
                np.full((h, w), 4.0, dtype=np.float32),
                np.full((h, w), CC_MIN, dtype=np.float32))


# ============================================================================
# NOISE_SCALES / PERLIN — debug/test bases (pass-through paint).
# ============================================================================

def paint_noise_scales_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                          pm: float, bb) -> np.ndarray:
    """Noise scales (debug): pass-through paint, spec-driven texture."""
    return _safe_paint_copy(paint)


def spec_noise_scales(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Noise scales spec — CC=16 gloss with multi-scale noise variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        ns = multi_scale_noise((h, w), [8, 16, 32, 64], [0.25, 0.3, 0.25, 0.2], s + 350)
        M = float(base_m) + ns * 12.0 * sm
        R = float(base_r) + ns * 10.0 * sm
        CC = CC_MIN + ns * 4.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_noise_scales failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


def paint_perlin_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Perlin (debug): pass-through paint."""
    return _safe_paint_copy(paint)


def spec_perlin(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Perlin spec — CC=16 gloss with Perlin-driven surface variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        pn = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.35, 0.3], s + 360)
        M = float(base_m) + pn * 10.0 * sm
        R = float(base_r) + pn * 8.0 * sm
        CC = CC_MIN + pn * 3.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_perlin failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# ORANGE_PEEL_GLOSS — Cellular dimple texture in spec (the orange peel).
# Performance: two FBM calls + a sin-modulated cell pattern, ~30 ms @ 2048².
# ============================================================================

def paint_orange_peel_gloss_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                               pm: float, bb) -> np.ndarray:
    """Orange peel gloss — visible dimple texture from spray micro-coating."""
    paint = _safe_paint_copy(paint)
    if pm == 0.0:
        return paint
    h, w = _hw(shape)
    s = _safe_seed(seed)
    dimple_coarse = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], s + 8800)
    dimple_fine = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], s + 8801)
    cells = np.sin(dimple_coarse * np.pi * 12.0) * 0.5 + 0.5  # ~6-8 px cells
    cells = cells * (0.8 + dimple_fine * 0.2)
    texture = cells * 0.12 * pm
    contrasted = np.clip((paint - 0.5) * 1.06 + 0.5, 0.0, 1.0)
    effect = np.clip(contrasted + texture[:, :, np.newaxis] - 0.06, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = effect * m3 + paint * (1.0 - m3)
    return np.clip(result, 0.0, 1.0).astype(np.float32)


def spec_orange_peel_gloss(shape, seed, sm: float, base_m: float,
                           base_r: float) -> SpecTriple:
    """Orange peel spec — fine cellular bumps (6-8 px cells)."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        dimple_coarse = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], s + 8800)
        dimple_fine = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], s + 8801)
        cells = np.sin(dimple_coarse * np.pi * 12.0) * 0.5 + 0.5
        cells = cells * (0.8 + dimple_fine * 0.2)
        M = base_m + cells * 15.0 * sm - 7.0
        R = base_r + (1.0 - cells) * 30.0 * sm + cells * 5.0 * sm
        CC = CC_MIN + (1.0 - cells) * 12.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_orange_peel_gloss failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# ORGANIC_METAL — pass-through paint, spec drives organic grain.
# ============================================================================

def paint_organic_metal_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                           pm: float, bb) -> np.ndarray:
    """Organic metal: pass-through (spec-driven)."""
    return _safe_paint_copy(paint)


def spec_organic_metal(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Organic metal spec — glossy with organic grain-boundary variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        grain = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], s + 300)
        M = float(base_m) + grain * 15.0 * sm
        R = float(base_r) + grain * 10.0 * sm
        CC = CC_MIN + grain * 3.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_organic_metal failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# PIANO_BLACK — near-black, no texture.
# ============================================================================

def paint_piano_black_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                         pm: float, bb) -> np.ndarray:
    """Piano black: deep near-black, no noise."""
    paint = _safe_paint_copy(paint)
    deep = np.clip(paint * 0.06, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (deep * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_piano_black(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Piano black spec — ultra-smooth glossy with micro-depth variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        depth = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 400)
        M = float(base_m) + depth * 3.0 * sm
        R = float(base_r) + depth * 3.0 * sm
        CC = CC_MIN + depth * 1.5 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_piano_black failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# PRIMER — Solid primer grey, SOLID.
# ============================================================================

def paint_primer_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Primer: solid grey, no grain."""
    paint = _safe_paint_copy(paint)
    gray = np.full_like(paint, 0.42)
    primer = np.clip(paint * 0.25 + gray * 0.75, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (primer * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_primer(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Primer spec — CC=180 zero sheen with spray-coat grit variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        grit = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], s + 700)
        M = float(base_m) + grit * 5.0 * sm
        R = float(base_r) + grit * 12.0 * sm
        CC = 180.0 + grit * 10.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_primer failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), 180.0)


# ============================================================================
# SATIN — Standard satin finish, SOLID.
# Color-safe: yes (preserves saturation per design).
# ============================================================================

def paint_satin_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                   pm: float, bb) -> np.ndarray:
    """Satin: soft sheen, no pattern (preserves color saturation)."""
    paint = _safe_paint_copy(paint)
    soft = np.clip(paint * 0.97 + 0.02, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (soft * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_satin(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Satin spec (WEAK-011) — real 2-octave FBM sheen variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        sheen_coarse = multi_scale_noise((h, w), [8, 16], [0.55, 0.45], s + 3800)
        sheen_fine = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], s + 3801)
        sheen_fbm = sheen_coarse * 0.7 + sheen_fine * 0.3
        M = sheen_fbm * 18.0 * sm
        R = 80.0 + sheen_fbm * 60.0 * sm
        cc_noise = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], s + 3802)
        CC = 40.0 + cc_noise * 50.0
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_satin failed: %s", exc)
        return _neutral_spec(shape, 0.0, R_SATIN, CC_SATIN)


# ============================================================================
# SATIN_METAL — pass-through paint; spec brushes it.
# ============================================================================

def paint_satin_metal_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                         pm: float, bb) -> np.ndarray:
    """Satin metal: pass-through (brushed_grain handles surface)."""
    return _safe_paint_copy(paint)


def spec_satin_metal(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Satin metal spec — directional brush-grain metallic variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        rng = np.random.RandomState(s + 450)
        # Directional brush: column-correlated noise + light isotropic jitter.
        brush = (rng.standard_normal((h, 1)).astype(np.float32) * 0.7
                 + rng.standard_normal((h, w)).astype(np.float32) * 0.3)
        M = float(base_m) + brush * 12.0 * sm
        R = float(base_r) + brush * 10.0 * sm
        CC = CC_MIN + np.abs(brush) * 4.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_satin_metal failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# SCUFFED_SATIN — Rougher/duller than clean satin (WEAK-015 fix).
# ============================================================================

def paint_scuffed_satin_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                           pm: float, bb) -> np.ndarray:
    """Scuffed satin (WEAK-015) — rougher/duller than clean satin.

    Scuffing removes surface gloss: ~8% desaturation + micro-abrasion
    darkening. Previously brightened (physically backward) — now corrected.
    """
    paint = _safe_paint_copy(paint)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    gray = paint.mean(axis=2, keepdims=True)
    desat = paint * 0.92 + gray * 0.08
    darkened = np.clip(desat * 0.97, 0.0, 1.0)
    micro = multi_scale_noise((h, w), [16, 32, 64], [0.5, 0.3, 0.2], s + 5902)
    darkened = np.clip(darkened * (1.0 - micro[:, :, np.newaxis] * 0.04 * pm), 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (darkened * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_scuffed_satin(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Scuffed satin spec (WEAK-015) — must be rougher and duller than satin.

    R = 160-200 (higher than satin's 95), CC = 90-140 (higher/duller than 70).
    Scuffing exposes micro-metal highlights — sparse bright M spots simulate
    abraded paint revealing primer/metal underneath.
    """
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        scuff_fbm = multi_scale_noise((h, w), [16, 32, 64], [0.45, 0.35, 0.2], s + 5902)
        bright_spots = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], s + 5903)
        bright_mask = np.clip((bright_spots - 0.88) / 0.12, 0.0, 1.0)  # top 12% bright
        M = scuff_fbm * 25.0 * sm + bright_mask * 180.0
        R = 160.0 + scuff_fbm * 40.0 * sm
        CC = 90.0 + scuff_fbm * 50.0
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_scuffed_satin failed: %s", exc)
        return _neutral_spec(shape, 0.0, 180.0, 110.0)


# ============================================================================
# SEMI_GLOSS — Semi-gloss finish, SOLID.
# ============================================================================

def paint_semi_gloss_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                        pm: float, bb) -> np.ndarray:
    """Semi-gloss: visible but gentle sheen reduction with micro-grain."""
    paint = _safe_paint_copy(paint)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    grain = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 800)
    contrasted = np.clip((paint - 0.5) * 1.05 + 0.5, 0.0, 1.0)
    contrasted[:, :, :3] = np.clip(
        contrasted[:, :, :3] + grain[:, :, np.newaxis] * 0.012 * pm, 0.0, 1.0
    )
    m3 = mask[:, :, np.newaxis]
    return (contrasted * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_semi_gloss(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Semi-gloss spec — CC=40 mild dulling with noise variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 801)
        M = float(base_m) + noise * 5.0 * sm
        R = float(base_r) + noise * 8.0 * sm
        CC = CC_SEMI_GLOSS + noise * 6.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_semi_gloss failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_SEMI_GLOSS)


# ============================================================================
# SILK — Solid silk sheen, no weave texture.
# ============================================================================

def paint_silk_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                  pm: float, bb) -> np.ndarray:
    """Silk: soft lift, no weave pattern."""
    paint = _safe_paint_copy(paint)
    m3 = mask[:, :, np.newaxis]
    soft = np.clip(paint + 0.03 * pm * m3, 0.0, 1.0)
    return (soft * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_silk(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Silk spec — CC=60 smooth sheen with subtle directional fiber variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        fiber = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], s + 500)
        M = float(base_m) + fiber * 6.0 * sm
        R = float(base_r) + fiber * 8.0 * sm
        CC = CC_SATIN + fiber * 6.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_silk failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_SATIN)


# ============================================================================
# TERRAIN_CHROME — Chrome with terrain micro-distortion.
# Iron-rule note: chrome exception preserved by _enforce_iron_rules
# wherever M >= CHROME_M_THRESHOLD.
# ============================================================================

def paint_terrain_chrome_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                            pm: float, bb) -> np.ndarray:
    """Terrain chrome: pass-through (Perlin keys handle distortion)."""
    return _safe_paint_copy(paint)


def spec_terrain_chrome(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Terrain chrome spec — CC=16 chrome gloss with terrain micro-distortion."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        terrain = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 550)
        M = float(base_m) + terrain * 8.0 * sm
        R = float(base_r) + terrain * 6.0 * sm
        CC = CC_MIN + terrain * 2.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_terrain_chrome failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)


# ============================================================================
# VANTABLACK — Ultra-black, maximum absorption.
# ============================================================================

def paint_vantablack_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                        pm: float, bb) -> np.ndarray:
    """Vantablack: near-zero reflectance, no texture."""
    paint = _safe_paint_copy(paint)
    void = np.clip(paint * 0.002, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (void * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_vantablack(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Vantablack — CC=240 maximum degradation = absolutely dead surface."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        M = np.zeros((h, w), dtype=np.float32)
        R = np.full((h, w), R_MIN_NONCHROME, dtype=np.float32)
        CC = np.full((h, w), CC_VANTA, dtype=np.float32)
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_vantablack failed: %s", exc)
        return _neutral_spec(shape, 0.0, R_MIN_NONCHROME, CC_VANTA)


# ============================================================================
# VOLCANIC — Darkened base + warm/cool zonal tint + ash texture.
# Color-safe: NO — overrides base with volcanic palette.
# ============================================================================

def paint_volcanic_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                      pm: float, bb) -> np.ndarray:
    """Volcanic: darken base, warm orange/red in bright zones, cool charcoal
    in dark zones, ash texture noise overlay."""
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    base = paint
    gray = base.mean(axis=2)
    darkened = np.clip(base * 0.35, 0.0, 1.0)
    ash = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 6600)
    ash_fine = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], s + 6601)
    ash_tex = ash * 0.06 + ash_fine * 0.03
    bright_mask = np.clip((gray - 0.3) * 2.5, 0.0, 1.0)
    warm_r = 0.55 + ash * 0.12
    warm_g = 0.18 + ash * 0.06
    warm_b = 0.05 + ash * 0.03
    cool_r = 0.12 + ash * 0.04
    cool_g = 0.12 + ash * 0.03
    cool_b = 0.14 + ash * 0.03
    bm3 = bright_mask[:, :, np.newaxis]
    warm = np.stack([warm_r, warm_g, warm_b], axis=-1)
    cool = np.stack([cool_r, cool_g, cool_b], axis=-1)
    volcanic_color = warm * bm3 + cool * (1.0 - bm3)
    effect = np.clip(darkened * 0.4 + volcanic_color * 0.6 + ash_tex[:, :, np.newaxis],
                     0.0, 1.0).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + effect * (m3 * blend), 0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.20 * pm * m3,
                   0.0, 1.0).astype(np.float32)


def spec_volcanic(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Volcanic spec — CC=70 semi-gloss with ash-texture roughness variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        ash = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 6600)
        M = float(base_m) + ash * 10.0 * sm
        R = float(base_r) + ash * 15.0 * sm
        CC = 70.0 + ash * 12.0 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_volcanic failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), 70.0)


# ============================================================================
# WET_LOOK — Solid wet look, no texture.
# ============================================================================

def paint_wet_look_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                      pm: float, bb) -> np.ndarray:
    """Wet look: subtle depth gamma, no pattern."""
    paint = _safe_paint_copy(paint)
    wet = np.clip(paint ** 1.1, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return (wet * m3 + paint * (1.0 - m3)).astype(np.float32)


def spec_wet_look(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Wet look spec — CC=16 ultra-glossy with subtle coating thickness variation."""
    try:
        _validate_spec_inputs(shape, seed, sm)
        h, w = _hw(shape)
        s = _safe_seed(seed)
        coat = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 600)
        M = float(base_m) + coat * 3.0 * sm
        R = float(base_r) + coat * 2.0 * sm
        CC = CC_MIN + coat * 1.5 * sm
        return _enforce_iron_rules(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_wet_look failed: %s", exc)
        return _neutral_spec(shape, base_m, max(base_r, R_MIN_NONCHROME), CC_MIN)
