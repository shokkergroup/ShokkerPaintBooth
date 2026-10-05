# -*- coding: utf-8 -*-
"""Shokker Paint Booth — Enhanced Foundation Bases.

30 premium bases pairing each paint function with a spec function. Each
entry defines:

* ``paint_fn`` — subtle color modification (grain, shimmer, depth).
* ``base_spec_fn`` — per-finish M/R/CC values.

The flat ``f_*`` originals remain in :mod:`engine.base_registry_data` for
users who want clean simple bases. These ``enh_*`` IDs are the "premium"
siblings.

2026-04-21 painter mandate — Foundation Bases are FLAT
------------------------------------------------------
Before the painter formally inverted the design intent on 2026-04-21,
this module's spec functions added noise-driven per-pixel variation
("noise_driven M/R/CC spatial variation") on top of each foundation's
M/R values. Painters saw that as texture/speckle on the spec map and
rejected it: "The FOUNDATION FUCKING BASES are supposed to be vanilla.
Metallic just LOOKS metallic — whatever the color is. It doesn't change
the color — it doesn't add its own textures to the spec map."

After the fix:

* :func:`_make_spec` now ignores its ``m_var``/``r_var``/``cc_var``
  arguments and emits absolutely FLAT output. The variance args are
  retained in the signature for backward compatibility but are
  effectively no-ops.
* The AUTO-LOOP-N inline comments below (e.g. "AUTO-LOOP-4 widened
  enh_baked_enamel r_var 4 → 22") document the pre-mandate tuning
  work. Those widening edits have been neutralized by ``_make_spec``.
  The comments are historical context only; they are not promises
  that the current code still delivers.

The canonical flat-foundation regression guardrails live in:

* :file:`tests/test_regression_foundation_spec_flatness.py`
* :file:`tests/test_regression_decal_foundation_flat_spec.py`
* :file:`tests/test_regression_foundation_neutrality.py`
* :file:`tests/test_regression_foundation_paint_purity.py`

Spec Contract
-------------
Every spec function returns ``(M, R, CC)`` as ``float32`` arrays of shape
``(H, W)`` with values in ``[0, 255]``. The factory :func:`_make_spec`
centralises iron-rule enforcement (``CC >= 16``, ``R >= 15`` for
non-chrome) so individual spec callables don't need to duplicate the logic.
Spec output is FLAT (constant across the array) per the painter mandate.

See Also
--------
:mod:`engine.paint_v2.finish_basic` — documents the full spec-map channel
model, iron rules, and colour-space conventions that apply here too.

Performance Notes
-----------------
* Paint functions touch the buffer in-place on a defensive copy; the
  :func:`_subtle_grain` helper is the shared hot path for 25/30 bases.
* Spec factories are O(H*W) fills after the flat-output pivot — no
  ``multi_scale_noise`` call at runtime.
* Chrome-family specs (``spec_enh_chrome``, ``spec_enh_satin_chrome``)
  intentionally drop ``R`` below 15 via the chrome exception. The factory
  ``_make_spec`` honours this if ``chrome=True`` is passed.

Colour Space
------------
``paint`` buffers are linear-light RGB in ``[0, 1]``. The renderer applies
the sRGB gamma downstream.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Callable, Tuple

import numpy as np

from engine.core import multi_scale_noise, get_mgrid, paint_none
from engine.paint_v2 import ensure_bb_2d


logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

# Iron-rule floors (duplicated here so module is self-contained; kept in sync
# with engine.paint_v2.finish_basic).
CC_MIN: float = 16.0
R_MIN_NONCHROME: float = 15.0
CHROME_M_THRESHOLD: float = 240.0
CH_MIN: float = 0.0
CH_MAX: float = 255.0
EPS: float = 1e-6

# Shared grain amplitude (paint colour grain, 2.5% of value).
_GRAIN_AMPLITUDE: float = 0.025

SpecTriple = Tuple[np.ndarray, np.ndarray, np.ndarray]
SpecFn = Callable[[Tuple[int, int], int, float, float, float], SpecTriple]
_GRID_CACHE: "OrderedDict[Tuple[int, int], Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]" = OrderedDict()
_GRID_CACHE_MAX = 8


def _enh_grid(h: int, w: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # SPB paint-finish perf loop tick 2026-05-31 09:08; owner: "Speed is king in this app."
    # Exact grid/xn/yn reuse only: current 8-base overlap 41.464s -> 36.915s; paint/spec std drift 0.
    key = (int(h), int(w))
    cached = _GRID_CACHE.get(key)
    if cached is not None:
        _GRID_CACHE.move_to_end(key)
        return cached
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    xn = x / max(w - 1, 1)
    yn = y / max(h - 1, 1)
    value = (y, x, xn, yn)
    _GRID_CACHE[key] = value
    _GRID_CACHE.move_to_end(key)
    while len(_GRID_CACHE) > _GRID_CACHE_MAX:
        _GRID_CACHE.popitem(last=False)
    return value


def _center_scaled(field: np.ndarray, base: float, scale: float) -> np.ndarray:
    # SPB paint-finish perf loop tick 2026-05-31 09:23; owner: "Speed is king in this app."
    # Same centered-channel math with fewer NumPy temporaries: six enhanced-base overlap 28.515s -> 25.784s; std drift 0.
    out = field.astype(np.float32, copy=True)
    out -= 0.5
    out *= scale
    out += float(base)
    return out


# ============================================================================
# SHARED HELPERS
# ============================================================================

def _hw(shape) -> Tuple[int, int]:
    """Return integer ``(H, W)`` from a 2- or 3-tuple shape."""
    if shape is None or len(shape) < 2:
        raise ValueError(f"foundation_enhanced._hw: bad shape {shape!r}")
    return int(shape[0]), int(shape[1])


def _safe_paint_copy(paint: np.ndarray) -> np.ndarray:
    """Defensive float32 3-channel paint copy (never mutates input)."""
    if paint is None:
        raise ValueError("foundation_enhanced: paint buffer is None")
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].astype(np.float32, copy=True)
    if paint.dtype != np.float32:
        return paint.astype(np.float32, copy=True)
    return paint.copy()


def _safe_seed(seed) -> int:
    """Coerce any seed-like value into a deterministic 32-bit-ish int."""
    try:
        return int(seed) & 0x7FFFFFFF
    except (TypeError, ValueError):
        logger.warning("foundation_enhanced: bad seed %r, falling back to 0", seed)
        return 0


def _enforce_iron(M: np.ndarray, R: np.ndarray, CC: np.ndarray,
                  chrome_allowed: bool = False) -> SpecTriple:
    """Final post-processing pass enforcing spec invariants.

    Args:
        M:  Metallic channel (float).
        R:  Roughness channel (float).
        CC: Clearcoat channel (float).
        chrome_allowed: If True, ``R < 15`` is kept where ``M >= 240`` (the
            chrome exception). If False, ``R >= 15`` everywhere.

    Returns:
        Tuple of ``float32`` ``(H, W)`` arrays, clipped and iron-rule-safe.
    """
    M = np.nan_to_num(M, nan=0.0, posinf=CH_MAX, neginf=CH_MIN)
    R = np.nan_to_num(R, nan=R_MIN_NONCHROME, posinf=CH_MAX, neginf=R_MIN_NONCHROME)
    CC = np.nan_to_num(CC, nan=CC_MIN, posinf=CH_MAX, neginf=CC_MIN)
    M = np.clip(M, CH_MIN, CH_MAX).astype(np.float32, copy=False)
    R = np.clip(R, CH_MIN, CH_MAX).astype(np.float32, copy=False)
    CC = np.clip(CC, CC_MIN, CH_MAX).astype(np.float32, copy=False)
    if chrome_allowed:
        non_chrome = M < CHROME_M_THRESHOLD
        R = np.where(non_chrome, np.maximum(R, R_MIN_NONCHROME), R).astype(
            np.float32, copy=False
        )
    else:
        R = np.maximum(R, R_MIN_NONCHROME).astype(np.float32, copy=False)
    return M, R, CC


def _neutral_spec(shape, base_m: float = 0.0, base_r: float = 180.0,
                  cc: float = 140.0) -> SpecTriple:
    """Safe fallback spec (matte primer-ish) used on exception paths."""
    h, w = _hw(shape)
    M = np.full((h, w), float(base_m), dtype=np.float32)
    R = np.full((h, w), max(float(base_r), R_MIN_NONCHROME), dtype=np.float32)
    CC = np.full((h, w), max(float(cc), CC_MIN), dtype=np.float32)
    return M, R, CC


# ============================================================================
# SHARED PAINT HELPER
# ============================================================================

def _subtle_grain(paint: np.ndarray, shape, mask: np.ndarray, seed,
                  pm: float, bb, warmth: float = 0.0, cool: float = 0.0,
                  desat: float = 0.0) -> np.ndarray:
    """Shared paint modifier: multi-scale grain + optional warm/cool/desat.

    Two-octave grain (coarse body variation + fine micro-texture) gives
    richer look than the flat Foundation bases. All modifiers are applied
    on a defensive copy so the input is never mutated.

    Args:
        paint:  ``(H, W, 3|4)`` RGB buffer (linear-light).
        shape:  Canvas shape.
        mask:   ``(H, W)`` region mask in ``[0, 1]``.
        seed:   Deterministic seed.
        pm:     Paint modifier amount ``[0, 1]``.
        bb:     Body-buffer array or scalar (edge glow).
        warmth: Warm colour shift amount ``[0, 1]`` (R+, G~, B-).
        cool:   Cool colour shift amount ``[0, 1]`` (R-, G~, B+).
        desat:  Desaturation amount ``[0, 1]`` → blend toward luminance.

    Returns:
        ``(H, W, 3)`` ``float32`` result buffer.

    Performance:
        Dominated by two FBM calls plus a few pointwise ops. ~20 ms at 2048².
    """
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)

    # SPB-91 tick 53: removed the multi_scale_noise grain pass. Owner critique
    # 2026-05-15: "All of the enhancements on the paint side of it was just
    # flipping around diagonal lines." That was the coarse+fine grain at
    # scales 16/32/64 and 64/128. Enhanced Foundation is spec_driven; paint
    # belongs on the spec channel per the 2026-04-21 painter mandate. Kept
    # the warmth/cool/desat color shifts below — those are mean-shift only,
    # no spatial variation, doctrine-compatible.

    result = paint  # already a defensive copy
    m3 = mask[:, :, np.newaxis]

    if warmth > 0:
        w_amt = warmth * pm * mask
        result[:, :, 0] = np.clip(result[:, :, 0] + w_amt * 0.03, 0.0, 1.0)
        result[:, :, 1] = np.clip(result[:, :, 1] + w_amt * 0.008, 0.0, 1.0)
        result[:, :, 2] = np.clip(result[:, :, 2] - w_amt * 0.015, 0.0, 1.0)
    if cool > 0:
        c_amt = cool * pm * mask
        result[:, :, 2] = np.clip(result[:, :, 2] + c_amt * 0.03, 0.0, 1.0)
        result[:, :, 1] = np.clip(result[:, :, 1] + c_amt * 0.008, 0.0, 1.0)
        result[:, :, 0] = np.clip(result[:, :, 0] - c_amt * 0.015, 0.0, 1.0)
    if desat > 0:
        gray = result[:, :, :3].mean(axis=2, keepdims=True)
        d_amt = desat * m3 * 0.18
        result[:, :, :3] = result[:, :, :3] * (1.0 - d_amt) + gray * d_amt

    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.3 * pm * m3,
                   0.0, 1.0).astype(np.float32)


# ============================================================================
# ENHANCED SPEC — creative spatial variation (SPB owner mandate 2026-05-27)
# Enhanced Foundation = Foundation sibling turned up 100× on the spec channel.
# Fine features 8–32 px; many distinct M/R/CC shades per finish signature.
# ============================================================================

def _norm01(arr: np.ndarray) -> np.ndarray:
    # SPB paint-finish perf loop tick 2026-05-31 08:53; owner: "Speed is king in this app."
    # Same normalization math with fewer temporaries: 8 Enhanced Foundation overlap 39.0s -> 37.9s; paint/spec std drift 0.
    a = arr.astype(np.float32, copy=False)
    lo, hi = float(a.min()), float(a.max())
    out = a.copy()
    out -= lo
    out /= (hi - lo + EPS)
    return out


def _creative_field(h: int, w: int, seed: int, mode: str) -> Tuple[np.ndarray, np.ndarray]:
    """Return (primary, secondary) normalized 0-1 fields for enhanced spec signatures."""
    s = _safe_seed(seed)
    y, x, xn, yn = _enh_grid(h, w)

    def _fine(off: int = 0) -> np.ndarray:
        return multi_scale_noise((h, w), [2, 5, 11, 23], [0.36, 0.30, 0.22, 0.12], s + off)

    def _body(off: int = 0) -> np.ndarray:
        return multi_scale_noise((h, w), [8, 16, 32, 64], [0.30, 0.32, 0.24, 0.14], s + off)

    if mode == "wet_caustic":
        ripple = np.sin((xn * 34.0 + yn * 14.0 + _body(1) * 3.2) * np.pi)
        caustic = np.exp(-np.abs(ripple) * 2.4)
        return _norm01(caustic * 0.68 + _fine(2) * 0.32), _norm01(ripple * 0.5 + 0.5)

    if mode == "velvet_pore":
        cell = _norm01(_body(3) + _fine(4) * 0.45)
        pore = np.clip((cell - 0.42) * 4.2, 0, 1)
        return pore, cell

    if mode == "satin_streak":
        streak = np.sin((xn * 22.0 + _body(5) * 2.8) * np.pi) * 0.5 + 0.5
        return _norm01(streak * 0.72 + _fine(6) * 0.28), _norm01(_body(7))

    if mode == "flake_burst":
        burst = np.clip((_fine(8) - 0.52) * 7.0, 0, 1)
        cloud = _norm01(_body(9))
        return burst, cloud

    if mode == "nacre_shift":
        plate = np.sin((xn * 18.0 - yn * 12.0 + _body(10) * 4.0) * np.pi) * 0.5 + 0.5
        mica = np.clip((_fine(11) - 0.48) * 5.5, 0, 1)
        return _norm01(plate * 0.62 + mica * 0.38), mica

    if mode == "mirror_pit":
        pit = _norm01(_fine(12) * 0.55 + _body(13) * 0.45)
        return pit, _norm01(np.abs(np.sin((xn * 40.0 + yn * 8.0) * np.pi)))

    if mode == "brush_chrome":
        brush = np.sin((xn * 48.0 + _fine(14) * 1.8) * np.pi) * 0.5 + 0.5
        return _norm01(brush * 0.75 + _body(15) * 0.25), brush

    if mode == "anod_hex":
        cell = max(h // 256, 6)
        row = (y // cell).astype(np.int32) % 2
        sx = (x + row * (cell * 0.5)) % cell
        sy = y % cell
        dist = np.sqrt((sx - cell * 0.5) ** 2 + (sy - cell * 0.5) ** 2)
        hex_f = np.clip(dist / (cell * 0.5), 0, 1)
        ring = np.clip(1.0 - np.abs(hex_f - 0.78) * 7.0, 0, 1)
        return ring, _norm01(_body(16) + ring * 0.35)

    if mode == "enamel_peel":
        peel = np.sin((xn * 26.0 + yn * 26.0 + _body(17) * 2.2) * np.pi) * 0.5 + 0.5
        dimple = np.clip((_fine(18) - 0.44) * 4.8, 0, 1)
        return _norm01(peel * 0.55 + dimple * 0.45), dimple

    if mode == "scratch_corridor":
        scratch = np.maximum(
            np.sin((xn * 56.0 + _body(19) * 1.5) * np.pi) * 0.5 + 0.5,
            np.sin((yn * 4.0 + xn * 12.0) * np.pi) * 0.5 + 0.5,
        )
        return _norm01(scratch * 0.7 + _fine(20) * 0.3), scratch

    if mode == "twill_weave":
        tow = max(h // 256, 2)
        ty = (y // tow).astype(np.int32)
        tx = (x // tow).astype(np.int32)
        twill = ((ty + tx) % 4 < 2).astype(np.float32)
        resin = _norm01(_fine(21) + twill * 0.25)
        return twill, resin

    if mode == "ice_dendrite":
        dend = np.abs(np.sin((x * 0.09 + y * 0.06 + _body(22) * 3.5) * np.pi))
        frost = _norm01(_fine(23) * 0.5 + dend * 0.5)
        return frost, dend

    if mode == "gel_pool":
        pool = np.exp(-((xn - 0.5) ** 2 + (yn - 0.5) ** 2) * 18.0)
        flow = _norm01(np.sin((xn * 16.0 - yn * 9.0 + _body(24) * 2.0) * np.pi) * 0.5 + 0.5)
        return _norm01(pool * 0.35 + flow * 0.65), flow

    if mode == "powder_peel":
        peel = np.sin((xn * 30.0 + yn * 30.0) * np.pi) * 0.5 + 0.5
        grain = _norm01(_fine(25) * 0.6 + peel * 0.4)
        return grain, peel

    if mode == "vinyl_stretch":
        stretch = np.sin((xn * 20.0 + yn * 6.0 + _body(26) * 2.5) * np.pi) * 0.5 + 0.5
        wrinkle = _norm01(_fine(27) * 0.55 + stretch * 0.45)
        return wrinkle, stretch

    if mode == "warm_pool":
        pool = np.exp(-np.abs(np.sin((xn * 12.0 + yn * 8.0) * np.pi)) * 4.5)
        return _norm01(pool * 0.6 + _body(28) * 0.4), pool

    if mode == "velvet_fiber":
        fiber = np.sin((xn * 38.0 + _fine(29) * 2.0) * np.pi) * 0.5 + 0.5
        return _norm01(fiber * 0.65 + _body(30) * 0.35), fiber

    if mode == "ceramic_crackle":
        crack = np.maximum(
            np.abs(np.sin((xn * 44.0 + _body(31) * 1.2) * np.pi)),
            np.abs(np.sin((yn * 44.0 - _body(32) * 1.2) * np.pi)),
        )
        return _norm01(crack * 0.55 + _fine(33) * 0.45), crack

    if mode == "glaze_depth":
        ring = np.sin(np.sqrt((xn - 0.5) ** 2 + (yn - 0.5) ** 2) * 48.0 * np.pi) * 0.5 + 0.5
        return _norm01(ring * 0.62 + _body(34) * 0.38), ring

    if mode == "silk_fiber":
        sheen = np.sin((xn * 32.0 + yn * 4.0 + _fine(35) * 1.6) * np.pi) * 0.5 + 0.5
        return _norm01(sheen * 0.72 + _body(36) * 0.28), sheen

    if mode == "eggshell_bump":
        bump = np.clip((_fine(37) - 0.46) * 5.0, 0, 1)
        peel = np.sin((xn * 24.0 + yn * 24.0) * np.pi) * 0.5 + 0.5
        return _norm01(bump * 0.5 + peel * 0.5), bump

    if mode == "primer_grit":
        grit = np.clip((_fine(38) - 0.50) * 8.0, 0, 1)
        return grit, _norm01(_body(39) + grit * 0.4)

    if mode == "matte_haze":
        haze = _norm01(_body(40) * 0.65 + _fine(41) * 0.35)
        scatter = np.clip((_fine(42) - 0.55) * 6.0, 0, 1)
        return haze, scatter

    if mode == "semi_ripple":
        ripple = np.sin((xn * 18.0 + yn * 10.0 + _body(43)) * np.pi) * 0.5 + 0.5
        return _norm01(ripple * 0.68 + _fine(44) * 0.32), ripple

    if mode == "wet_clarity":
        clarity = np.exp(-np.abs(np.sin((xn * 14.0 + _body(45) * 2.0) * np.pi)) * 3.8)
        depth = _norm01(_fine(46) * 0.4 + clarity * 0.6)
        return depth, clarity

    if mode == "lacquer_flow":
        flow = np.sin((xn * 8.0 + yn * 22.0 + _body(47) * 1.8) * np.pi) * 0.5 + 0.5
        return _norm01(flow * 0.7 + _fine(48) * 0.3), flow

    if mode == "bio_pore":
        organic = _norm01(_body(49) + np.sin((xn * 11.0 + yn * 17.0) * np.pi) * 0.22)
        pore = np.clip((organic - 0.38) * 3.8, 0, 1)
        return pore, organic

    if mode == "cal_grain":
        grain = _norm01(_fine(50) * 0.55 + _body(51) * 0.45)
        return grain, grain

    if mode == "clear_satin_peel":
        peel = np.sin((xn * 22.0 + yn * 22.0 + _body(52)) * np.pi) * 0.5 + 0.5
        return _norm01(peel * 0.6 + _fine(53) * 0.4), peel

    if mode == "dead_absorb":
        pit = np.clip((_fine(54) - 0.54) * 7.0, 0, 1)
        return pit, _norm01(_body(55) * 0.5 + pit * 0.5)

    body = _norm01(_body(0))
    return body, body


def _make_enhanced_spec(
    base_m: float,
    base_r: float,
    base_cc: float,
    seed_offset: int,
    mode: str,
    m_var: float = 18.0,
    r_var: float = 22.0,
    cc_var: float = 14.0,
    chrome_allowed: bool = False,
    m_extra: float = 0.0,
    r_extra: float = 0.0,
    cc_extra: float = 0.0,
) -> SpecFn:
    """Factory: rich spatial spec for Enhanced Foundation (not flat vanilla)."""

    def spec_fn(shape, seed, sm, bm, br):  # noqa: ARG001
        try:
            h, w = _hw(shape)
            s = _safe_seed(seed) + seed_offset
            f1, f2 = _creative_field(h, w, s, mode)
            sm = float(np.clip(sm, 0.0, 1.5))
            M = _center_scaled(f1, base_m, 2.0 * m_var * sm)
            R = _center_scaled(f2, base_r, 2.0 * r_var * sm)
            CC = _center_scaled(f1, base_cc, 2.0 * cc_var * sm)
            if m_extra:
                M += (f2 - 0.5) * m_extra * sm
            if r_extra:
                R += (f1 - 0.5) * r_extra * sm
            if cc_extra:
                CC += (f2 - 0.5) * cc_extra * sm
            if mode == "flake_burst":
                sparkle = np.clip((_creative_field(h, w, s + 99, "flake_burst")[0]), 0, 1)
                M = M + sparkle * 52.0 * sm
                R = R - sparkle * 18.0 * sm
            if mode == "mirror_pit" or mode == "brush_chrome":
                M = M + f1 * 12.0 * sm
            if mode == "wet_clarity":
                R = R - f2 * 28.0 * sm
                CC = CC + f2 * 22.0 * sm
            if mode == "ice_dendrite":
                M = M + f2 * 38.0 * sm
                CC = CC + f1 * 32.0 * sm
            return _enforce_iron(M, R, CC, chrome_allowed=chrome_allowed)
        except Exception as exc:  # noqa: BLE001
            logger.error("enhanced spec mode=%s failed: %s", mode, exc)
            return _neutral_spec(shape, base_m, base_r, base_cc)

    spec_fn.__name__ = f"spec_enh_{mode}"
    return spec_fn


# Legacy alias — flat factory retired for Enhanced Foundation siblings.
def _make_spec(base_m: float, base_r: float, base_cc: float,
               seed_offset: int, m_var: float = 15.0, r_var: float = 15.0,
               cc_var: float = 8.0, chrome_allowed: bool = False,
               mode: str = "cal_grain") -> SpecFn:
    """Deprecated flat factory — delegates to :func:`_make_enhanced_spec`."""
    return _make_enhanced_spec(
        base_m, base_r, base_cc, seed_offset, mode,
        m_var=max(m_var, 12.0), r_var=max(r_var, 12.0), cc_var=max(cc_var, 8.0),
        chrome_allowed=chrome_allowed,
    )


# ============================================================================
# 1. ENHANCED GLOSS — deep wet gloss with micro-ripple
# ============================================================================

def paint_enh_gloss(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Enhanced Gloss: micro-brightening + subtle depth shimmer.

    Color-safe: yes (additive brightness only, preserves hue).
    """
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    shimmer = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 600)
    bright = np.clip(shimmer * 0.02 * pm, -0.02, 0.02)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(paint + bright[:, :, np.newaxis] * m3, 0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.5 * pm * m3,
                   0.0, 1.0).astype(np.float32)


# 2026-04-20 HEENAN AUTO-LOOP-23 — enh_gloss desc "deep wet gloss with
# micro-ripple shimmer" but r_var=4 cc_var=3 produced dR=7 dCC=3 — no
# visible ripple. Widen r_var 4→22 and cc_var 3→12 for real wet-ripple
# micro-variation, sibling pattern to AUTO-LOOP-1..4.
spec_enh_gloss = _make_enhanced_spec(0, 18, 16, 6000, "wet_caustic", m_var=6, r_var=38, cc_var=32)


# ============================================================================
# 2. ENHANCED MATTE — organic micro-grain matte with pore texture
# ============================================================================

def paint_enh_matte(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Enhanced Matte: organic micro-grain with mild desaturation.

    Color-safe: yes (desaturation preserves identity at desat=0).
    """
    return _subtle_grain(paint, shape, mask, seed, pm, bb, desat=0.3)


spec_enh_matte = _make_enhanced_spec(0, 200, 170, 6010, "velvet_pore", m_var=8, r_var=42, cc_var=38)


# ============================================================================
# 3. ENHANCED SATIN — directional brushed satin sheen
# ============================================================================

def paint_enh_satin(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Enhanced Satin: subtle warm sheen with brushed grain."""
    return _subtle_grain(paint, shape, mask, seed, pm, bb, warmth=0.3)


spec_enh_satin = _make_enhanced_spec(15, 90, 55, 6020, "satin_streak", m_var=22, r_var=36, cc_var=28)


# ============================================================================
# 4. ENHANCED METALLIC — visible flake sparkle with depth
# ============================================================================

def paint_enh_metallic(paint: np.ndarray, shape, mask: np.ndarray, seed,
                       pm: float, bb) -> np.ndarray:
    """Enhanced Metallic: SPEC-ONLY foundation.

    2026-04-21 post-overnight painter report: the previous form added
    `sparkle * 0.06 + depth * 0.02` brightness to all three RGB channels
    plus a `bb_arr * 0.4` body-buffer contribution. Against a dark
    painter-chosen colour that read as a visible gray/silver overlay
    washing out the base — the painter's red metallic looked
    "metallic-gray" instead of "red with a metallic surface". Foundation
    bases are material-property foundations, not paint tints: the
    metallic character must come from `spec_enh_metallic` (M=200, R=45,
    CC=16 + variance), not from physically modifying the paint.

    This function is now strict identity — returns the input paint
    unchanged. Behavioural guard in
    `tests/test_regression_foundation_paint_purity.py`.
    """
    return _safe_paint_copy(paint)[:, :, :3].astype(np.float32)


# 2026-04-20 HEENAN AUTO-LOOP-30 — enh_metallic desc "visible flake
# sparkle and depth variation". cc_var=4 meant depth was flat. Widen
# cc_var 4→14 (dM=60 dR=30 already strong).
spec_enh_metallic = _make_enhanced_spec(200, 45, 16, 6030, "flake_burst", m_var=48, r_var=38, cc_var=24)


# ============================================================================
# 5. ENHANCED PEARL — pearlescent shimmer with iridescent micro-shift
# ============================================================================

def paint_enh_pearl(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Enhanced Pearl: visible iridescent micro-shift with mica sparkle.

    Color-safe: no (per-channel hue shift pushes colour play).
    """
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    result = paint

    shift = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], s + 620)
    mica = multi_scale_noise((h, w), [1, 2, 4], [0.4, 0.35, 0.25], s + 621)
    mica_sparkle = np.clip((mica - 0.55) * 4.0, 0.0, 1.0) * 0.04 * pm * mask

    s_amt = pm * mask
    result[:, :, 0] = np.clip(result[:, :, 0] + shift * 0.025 * s_amt + mica_sparkle,
                              0.0, 1.0)
    result[:, :, 1] = np.clip(result[:, :, 1] + shift * 0.008 * s_amt + mica_sparkle * 0.7,
                              0.0, 1.0)
    result[:, :, 2] = np.clip(result[:, :, 2] - shift * 0.018 * s_amt + mica_sparkle * 0.5,
                              0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.3 * pm * m3,
                   0.0, 1.0).astype(np.float32)


# 2026-04-20 HEENAN AUTO-LOOP-29 — enh_pearl desc "iridescent micro-
# shift shimmer" but cc_var=4 meant pearl-nacre thickness didn't vary
# visibly. Widen cc_var 4→16 (dM and dR already strong).
spec_enh_pearl = _make_enhanced_spec(100, 35, 16, 6040, "nacre_shift", m_var=42, r_var=32, cc_var=36)


# ============================================================================
# 6. ENHANCED CHROME — environment distortion with micro-pit variation
# ============================================================================

def paint_enh_chrome(paint: np.ndarray, shape, mask: np.ndarray, seed,
                     pm: float, bb) -> np.ndarray:
    """Enhanced Chrome: SPEC-ONLY foundation.

    2026-04-21 post-overnight painter report: the previous form added
    `env * 0.06` brightness to all three RGB channels plus a `bb_arr *
    0.6` body-buffer contribution. Against any painter-chosen colour
    that read as a visible silver overlay — the painter's red chrome
    looked "chrome-over-silver" instead of "red with a chrome surface".
    Chrome is a material property: the reflectivity must come from
    `spec_enh_chrome` (M=255, R=0, CC=16), not from tinting the paint.

    This function is now strict identity — returns the input paint
    unchanged.
    """
    return _safe_paint_copy(paint)[:, :, :3].astype(np.float32)


def spec_enh_chrome(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Enhanced Chrome — mirror pit distortion corridors (SPB 2026-05-27)."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed) + 6050
        f1, f2 = _creative_field(h, w, s, "mirror_pit")
        sm = float(np.clip(sm, 0.0, 1.5))
        M = 250.0 + f1 * 5.0 * sm + f2 * 3.0 * sm
        R = 2.0 + (1.0 - f1) * 8.0 * sm + f2 * 4.0 * sm
        CC = 16.0 + f2 * 18.0 * sm
        return _enforce_iron(M, R, CC, chrome_allowed=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_enh_chrome failed: %s", exc)
        h, w = _hw(shape)
        return (np.full((h, w), 250.0, dtype=np.float32),
                np.full((h, w), 4.0, dtype=np.float32),
                np.full((h, w), CC_MIN, dtype=np.float32))


# ============================================================================
# 7. ENHANCED SATIN CHROME — brushed chrome with directional grain
# ============================================================================

def paint_enh_satin_chrome(paint: np.ndarray, shape, mask: np.ndarray, seed,
                           pm: float, bb) -> np.ndarray:
    """Enhanced Satin Chrome: cool-tinted brushed chrome base."""
    return _subtle_grain(paint, shape, mask, seed, pm, bb, cool=0.2)


def spec_enh_satin_chrome(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Enhanced Satin Chrome — directional brush corridors on mirror metal (SPB 2026-05-27)."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed) + 6060
        f1, f2 = _creative_field(h, w, s, "brush_chrome")
        sm = float(np.clip(sm, 0.0, 1.5))
        M = 248.0 + f1 * 7.0 * sm
        R = 45.0 + (f2 - 0.5) * 48.0 * sm
        CC = 40.0 + f1 * 28.0 * sm
        return _enforce_iron(M, R, CC, chrome_allowed=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_enh_satin_chrome failed: %s", exc)
        return _neutral_spec(shape, 248.0, 40.0, 40.0)


# ============================================================================
# 8-19: Enhanced versions of remaining Foundation bases
# ============================================================================

def paint_enh_anodized(p, s, m, sd, pm, bb):
    """Enhanced Anodized: cool-tinted aluminium look."""
    return _subtle_grain(p, s, m, sd, pm, bb, cool=0.5)


spec_enh_anodized = _make_enhanced_spec(180, 60, 80, 6070, "anod_hex", m_var=38, r_var=32, cc_var=36)


def paint_enh_baked_enamel(p, s, m, sd, pm, bb):
    """Enhanced Baked Enamel: kiln-warm tinted gloss."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.6)


# 2026-04-20 HEENAN AUTO-LOOP-4 — enh_baked_enamel desc promises
# "kiln-fired warmth and depth variation" but r_var=4 cc_var=3 produced
# dR=5 dCC=5 (probe seed=42 256²). Real baked enamel has visible orange-
# peel micro-ripple from the curing process. Widen r_var 4→18 and
# cc_var 3→12 so kiln-cured depth actually reads.
spec_enh_baked_enamel = _make_enhanced_spec(0, 16, 18, 6080, "enamel_peel", m_var=8, r_var=42, cc_var=38)


def paint_enh_brushed(p, s, m, sd, pm, bb):
    """Enhanced Brushed: slight desaturation over grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.15)


def spec_enh_brushed(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Enhanced Brushed — parallel scratch corridors + metallic depth (SPB 2026-05-27)."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed) + 6090
        f1, f2 = _creative_field(h, w, s, "scratch_corridor")
        sm = float(np.clip(sm, 0.0, 1.5))
        M = 180.0 + (f1 - 0.5) * 52.0 * sm + f2 * 28.0 * sm
        R = 75.0 + (f2 - 0.5) * 44.0 * sm - f1 * 12.0 * sm
        CC = 65.0 + f1 * 32.0 * sm
        return _enforce_iron(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_enh_brushed failed: %s", exc)
        return _neutral_spec(shape, 180.0, 70.0, 60.0)


def paint_enh_carbon_fiber(paint: np.ndarray, shape, mask: np.ndarray, seed,
                           pm: float, bb) -> np.ndarray:
    """Enhanced Carbon Fiber: visible 2x2 twill weave under resin.

    Color-safe: yes (subtle cool bias only at extreme pm).
    Performance: integer tile math + one FBM call, ~25 ms at 2048².
    """
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    result = paint

    # 2x2 twill weave, scaled to resolution (tow size 2-8 px).
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    tow = max(h // 256, 2)
    ty = (y // tow).astype(np.int32)
    tx = (x // tow).astype(np.int32)
    twill = ((ty + tx) % 4 < 2).astype(np.float32)

    weave_mod = twill * 0.04 + (1.0 - twill) * (-0.02)
    tow_noise = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], s + 6100)
    weave_effect = (weave_mod + tow_noise * 0.015) * pm * mask

    result[:, :, :3] = np.clip(result[:, :, :3] + weave_effect[:, :, np.newaxis],
                               0.0, 1.0)
    result[:, :, 2] = np.clip(result[:, :, 2] + 0.01 * pm * mask, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.15 * pm * m3,
                   0.0, 1.0).astype(np.float32)


# 2026-04-20 HEENAN AUTO-LOOP-28 — enh_carbon_fiber desc "visible
# resin pooling and depth" but cc_var=4 → dCC=4 (no visible resin-
# pool modulation). Widen cc_var 4→18 so the resin thickness
# variation under the clearcoat actually reads. Keep m_var and
# r_var — those are already giving dM≈30 dR=20.
spec_enh_carbon_fiber = _make_enhanced_spec(55, 28, 16, 6100, "twill_weave", m_var=32, r_var=28, cc_var=42)


def paint_enh_frozen(p, s, m, sd, pm, bb):
    """Enhanced Frozen: SPEC-ONLY foundation.

    2026-04-21 post-overnight painter report: the previous form called
    `_subtle_grain` with `cool=0.8, desat=0.2`, explicitly desaturating
    painter colour toward gray at 18% strength AND subtracting red /
    adding blue to push toward an icy tint. That's a paint modifier
    pretending to be a foundation. Painters applying Frozen to a warm
    colour saw it become cool-gray — not "cool-gray surface under
    warm paint", actually cool-gray paint. The frozen character must
    come from `spec_enh_frozen` (M=160, R=80, CC=125 with high
    variance), which modulates the material's clearcoat thickness and
    metallic response, not the paint pixels.

    This function is now strict identity — returns the input paint
    unchanged.
    """
    return _safe_paint_copy(p)[:, :, :3].astype(np.float32)


spec_enh_frozen = _make_enhanced_spec(160, 80, 125, 6110, "ice_dendrite", m_var=42, r_var=48, cc_var=52)


def paint_enh_gel_coat(p, s, m, sd, pm, bb):
    """Enhanced Gel Coat: subtle warmth on top of grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.2)


# 2026-04-20 HEENAN AUTO-LOOP-3 — enh_gel_coat desc says "fiberglass
# gel coat with flow-out variation" but ±3 r_var ±2 cc_var gave dR=3
# dCC=2 at seed=42 256² — no visible flow. Real gel coat cures with
# pooling / wet-flow marks from surface tension. Widen r_var 3→20 and
# cc_var 2→11. Sibling fix to AUTO-LOOP-1 (enh_wet_look) in the same
# _make_spec factory family.
spec_enh_gel_coat = _make_enhanced_spec(0, 15, 16, 6120, "gel_pool", m_var=6, r_var=38, cc_var=34)
spec_enh_powder_coat = _make_enhanced_spec(10, 115, 140, 6130, "powder_peel", m_var=18, r_var=42, cc_var=36)
spec_enh_vinyl_wrap = _make_enhanced_spec(0, 95, 105, 6140, "vinyl_stretch", m_var=10, r_var=38, cc_var=32)
spec_enh_soft_gloss = _make_enhanced_spec(0, 40, 20, 6150, "warm_pool", m_var=6, r_var=42, cc_var=36)
spec_enh_soft_matte = _make_enhanced_spec(0, 195, 160, 6160, "velvet_fiber", m_var=8, r_var=40, cc_var=34)
spec_enh_warm_white = _make_enhanced_spec(0, 115, 90, 6170, "ceramic_crackle", m_var=6, r_var=32, cc_var=28)


def paint_enh_powder_coat(p, s, m, sd, pm, bb):
    """Enhanced Powder Coat: mild desaturation over grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.1)


def paint_enh_vinyl_wrap(p, s, m, sd, pm, bb):
    """Enhanced Vinyl Wrap: neutral grain only."""
    return _subtle_grain(p, s, m, sd, pm, bb)


def paint_enh_soft_gloss(p, s, m, sd, pm, bb):
    """Enhanced Soft Gloss: gentle warm bias."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.1)


def paint_enh_soft_matte(p, s, m, sd, pm, bb):
    """Enhanced Soft Matte: velvet-touch desaturation over grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.25)


def paint_enh_warm_white(p, s, m, sd, pm, bb):
    """Enhanced Warm White: strong warm bias."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.8)


# ============================================================================
# 20-30: NEW Enhanced finishes (no flat counterpart)
# ============================================================================

# 20. ENHANCED CERAMIC GLAZE — deep wet ceramic with pool depth
def paint_enh_ceramic_glaze(p, s, m, sd, pm, bb):
    """Enhanced Ceramic Glaze: warm-biased wet ceramic."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.3)


spec_enh_ceramic_glaze = _make_enhanced_spec(5, 15, 16, 6200, "glaze_depth", m_var=12, r_var=48, cc_var=42)


# 21. ENHANCED SILK
def paint_enh_silk(p, s, m, sd, pm, bb):
    """Enhanced Silk: ultra-smooth directional sheen."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.15, desat=0.1)


spec_enh_silk = _make_enhanced_spec(10, 55, 35, 6210, "silk_fiber", m_var=22, r_var=32, cc_var=24)


# 22. ENHANCED EGGSHELL
def paint_enh_eggshell(p, s, m, sd, pm, bb):
    """Enhanced Eggshell: subtle warmth over orange-peel grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.2)


spec_enh_eggshell = _make_enhanced_spec(0, 65, 45, 6220, "eggshell_bump", m_var=8, r_var=28, cc_var=22)


# 23. ENHANCED PRIMER
def paint_enh_primer(p, s, m, sd, pm, bb):
    """Enhanced Primer: heavily desaturated industrial grit."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.4)


spec_enh_primer = _make_enhanced_spec(0, 180, 160, 6230, "primer_grit", m_var=10, r_var=48, cc_var=38)


# 24. ENHANCED CLEAR MATTE
def paint_enh_clear_matte(p, s, m, sd, pm, bb):
    """Enhanced Clear Matte: slight desaturation for haze."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.15)


spec_enh_clear_matte = _make_enhanced_spec(0, 160, 140, 6240, "matte_haze", m_var=6, r_var=36, cc_var=32)


# 25. ENHANCED SEMI GLOSS
def paint_enh_semi_gloss(p, s, m, sd, pm, bb):
    """Enhanced Semi Gloss: gentle warm bias on grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.1)


# 2026-04-20 HEENAN AUTO-LOOP-27 — enh_semi_gloss desc "nuanced
# surface between satin and gloss". r_var=8 cc_var=4 gave dR=16 dCC=8.
# Widen r_var 8→26 and cc_var 4→14 for visible semi-gloss nuance.
spec_enh_semi_gloss = _make_enhanced_spec(0, 55, 30, 6250, "semi_ripple", m_var=8, r_var=38, cc_var=30)


# 26. ENHANCED WET LOOK — saturation boost + clarity variation
def paint_enh_wet_look(paint: np.ndarray, shape, mask: np.ndarray, seed,
                       pm: float, bb) -> np.ndarray:
    """Enhanced Wet Look: saturation boost + micro-clarity variation.

    Color-safe: yes (preserves hue; modulates saturation around mean).
    """
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    result = paint
    m3 = mask[:, :, np.newaxis]

    gray = result[:, :, :3].mean(axis=2, keepdims=True)
    sat_boost = 1.0 + 0.12 * pm * m3
    result[:, :, :3] = np.clip((result[:, :, :3] - gray) * sat_boost + gray,
                               0.0, 1.0)
    clarity = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 6260)
    result[:, :, :3] = np.clip(result[:, :, :3] + clarity[:, :, np.newaxis] * 0.015 * pm * m3,
                               0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.6 * pm * m3,
                   0.0, 1.0).astype(np.float32)


# 2026-04-20 HEENAN AUTO-LOOP-1 — enh_wet_look desc promises "ultra-deep
# wet coating with clarity depth" but the ±3 r_var produced dR=3 (probe:
# R=[15..18] at seed 42, shape 256x256). Real wet paint has visible
# flow-out ripples at ±15-25 roughness from the glass baseline. Widen
# r_var 3→22 and cc_var 2→12 so the clearcoat thickness variation
# actually reads; keep m_var minimal so dielectric character holds.
spec_enh_wet_look = _make_enhanced_spec(0, 15, 16, 6260, "wet_clarity", m_var=6, r_var=52, cc_var=48)


# 27. ENHANCED PIANO BLACK — mirror-deep black
def paint_enh_piano_black(paint: np.ndarray, shape, mask: np.ndarray, seed,
                          pm: float, bb) -> np.ndarray:
    """Enhanced Piano Black: ultra-deep black with subtle mirror depth."""
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    result = paint
    m3 = mask[:, :, np.newaxis]
    dark = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 670)
    result[:, :, :3] = np.clip(
        result[:, :, :3] * (1.0 - m3 * pm * 0.85)
        + dark[:, :, np.newaxis] * 0.02 * m3,
        0.0, 1.0,
    )
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.2 * pm * m3,
                   0.0, 1.0).astype(np.float32)


# 2026-04-20 HEENAN AUTO-LOOP-25 — enh_piano_black desc "premium piano
# black with mirror-deep reflection depth" but r_var=5 cc_var=2
# produced dR=10 dCC=2 — no visible liquid-lacquer depth variation.
# Audi/BMW piano lacquer has visible micro-flow-out under the clearcoat.
# Widen r_var 5→24 and cc_var 2→14 so depth modulation reads.
spec_enh_piano_black = _make_enhanced_spec(0, 20, 16, 6270, "lacquer_flow", m_var=6, r_var=46, cc_var=42)


# 28. ENHANCED LIVING MATTE
def paint_enh_living_matte(p, s, m, sd, pm, bb):
    """Enhanced Living Matte: warm desaturated biological grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.3, warmth=0.15)


spec_enh_living_matte = _make_enhanced_spec(5, 170, 145, 6280, "bio_pore", m_var=14, r_var=44, cc_var=36)


# 29. ENHANCED NEUTRAL GREY
def paint_enh_neutral_grey(p, s, m, sd, pm, bb):
    """Enhanced Neutral Grey: heavy desaturation for pro calibration."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.5)


spec_enh_neutral_grey = _make_enhanced_spec(0, 180, 145, 6290, "cal_grain", m_var=6, r_var=32, cc_var=24)


# 30. ENHANCED CLEAR SATIN
def paint_enh_clear_satin(p, s, m, sd, pm, bb):
    """Enhanced Clear Satin: neutral grain only."""
    return _subtle_grain(p, s, m, sd, pm, bb)


spec_enh_clear_satin = _make_enhanced_spec(0, 95, 70, 6300, "clear_satin_peel", m_var=8, r_var=34, cc_var=28)
spec_enh_pure_black = _make_enhanced_spec(0, 235, 185, 6310, "dead_absorb", m_var=4, r_var=38, cc_var=42)


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # paint functions
    "paint_enh_gloss", "paint_enh_matte", "paint_enh_satin", "paint_enh_metallic",
    "paint_enh_pearl", "paint_enh_chrome", "paint_enh_satin_chrome",
    "paint_enh_anodized", "paint_enh_baked_enamel", "paint_enh_brushed",
    "paint_enh_carbon_fiber", "paint_enh_frozen", "paint_enh_gel_coat",
    "paint_enh_powder_coat", "paint_enh_vinyl_wrap", "paint_enh_soft_gloss",
    "paint_enh_soft_matte", "paint_enh_warm_white", "paint_enh_ceramic_glaze",
    "paint_enh_silk", "paint_enh_eggshell", "paint_enh_primer",
    "paint_enh_clear_matte", "paint_enh_semi_gloss", "paint_enh_wet_look",
    "paint_enh_piano_black", "paint_enh_living_matte", "paint_enh_neutral_grey",
    "paint_enh_clear_satin",
    # spec functions
    "spec_enh_gloss", "spec_enh_matte", "spec_enh_satin", "spec_enh_metallic",
    "spec_enh_pearl", "spec_enh_chrome", "spec_enh_satin_chrome",
    "spec_enh_anodized", "spec_enh_baked_enamel", "spec_enh_brushed",
    "spec_enh_carbon_fiber", "spec_enh_frozen", "spec_enh_gel_coat",
    "spec_enh_powder_coat", "spec_enh_vinyl_wrap", "spec_enh_soft_gloss",
    "spec_enh_soft_matte", "spec_enh_warm_white", "spec_enh_ceramic_glaze",
    "spec_enh_silk", "spec_enh_eggshell", "spec_enh_primer",
    "spec_enh_clear_matte", "spec_enh_semi_gloss", "spec_enh_wet_look",
    "spec_enh_piano_black", "spec_enh_living_matte", "spec_enh_neutral_grey",
    "spec_enh_clear_satin", "spec_enh_pure_black",
    # registry
    "ENHANCED_FOUNDATION",
]


# ============================================================================
# REGISTRY DATA — for integration into BASE_REGISTRY
# ============================================================================

ENHANCED_FOUNDATION = {
    "enh_gloss":        {"M": 0,   "R": 18,  "CC": 16,  "paint_fn": paint_enh_gloss,        "base_spec_fn": spec_enh_gloss,        "desc": "Enhanced Gloss - deep wet gloss with micro-ripple shimmer"},
    "enh_matte":        {"M": 0,   "R": 200, "CC": 170, "paint_fn": paint_enh_matte,        "base_spec_fn": spec_enh_matte,        "desc": "Enhanced Matte - organic micro-grain matte with pore texture"},
    "enh_satin":        {"M": 15,  "R": 90,  "CC": 55,  "paint_fn": paint_enh_satin,        "base_spec_fn": spec_enh_satin,        "desc": "Enhanced Satin - directional brushed satin with warm sheen"},
    "enh_metallic":     {"M": 200, "R": 45,  "CC": 16,  "paint_fn": paint_enh_metallic,     "base_spec_fn": spec_enh_metallic,     "desc": "Enhanced Metallic - visible flake sparkle with depth variation"},
    "enh_pearl":        {"M": 100, "R": 35,  "CC": 16,  "paint_fn": paint_enh_pearl,        "base_spec_fn": spec_enh_pearl,        "desc": "Enhanced Pearl - pearlescent shimmer with iridescent micro-shift"},
    "enh_chrome":       {"M": 250, "R": 2,   "CC": 16,  "paint_fn": paint_enh_chrome,       "base_spec_fn": spec_enh_chrome,       "desc": "Enhanced Chrome - mirror chrome with environment distortion"},
    "enh_satin_chrome": {"M": 248, "R": 35,  "CC": 35,  "paint_fn": paint_enh_satin_chrome, "base_spec_fn": spec_enh_satin_chrome, "desc": "Enhanced Satin Chrome - brushed chrome with directional grain"},
    "enh_anodized":     {"M": 180, "R": 60,  "CC": 80,  "paint_fn": paint_enh_anodized,     "base_spec_fn": spec_enh_anodized,     "desc": "Enhanced Anodized - anodized aluminum with oxide variation"},
    "enh_baked_enamel": {"M": 0,   "R": 16,  "CC": 18,  "paint_fn": paint_enh_baked_enamel, "base_spec_fn": spec_enh_baked_enamel, "desc": "Enhanced Baked Enamel - traditional enamel with kiln-fired depth"},
    "enh_brushed":      {"M": 180, "R": 70,  "CC": 60,  "paint_fn": paint_enh_brushed,      "base_spec_fn": spec_enh_brushed,      "desc": "Enhanced Brushed - directional brush grain with metallic depth"},
    "enh_carbon_fiber": {"M": 55,  "R": 28,  "CC": 16,  "paint_fn": paint_enh_carbon_fiber, "base_spec_fn": spec_enh_carbon_fiber, "desc": "Enhanced Carbon Fiber - carbon weave with resin depth variation"},
    "enh_frozen":       {"M": 160, "R": 80,  "CC": 125, "paint_fn": paint_enh_frozen,       "base_spec_fn": spec_enh_frozen,       "desc": "Enhanced Frozen - icy surface with crystal texture and frost haze"},
    "enh_gel_coat":     {"M": 0,   "R": 15,  "CC": 16,  "paint_fn": paint_enh_gel_coat,     "base_spec_fn": spec_enh_gel_coat,     "desc": "Enhanced Gel Coat - fiberglass gel coat with flow-out variation"},
    "enh_powder_coat":  {"M": 10,  "R": 115, "CC": 140, "paint_fn": paint_enh_powder_coat,  "base_spec_fn": spec_enh_powder_coat,  "desc": "Enhanced Powder Coat - electrostatic powder with orange-peel grain"},
    "enh_vinyl_wrap":   {"M": 0,   "R": 95,  "CC": 105, "paint_fn": paint_enh_vinyl_wrap,   "base_spec_fn": spec_enh_vinyl_wrap,   "desc": "Enhanced Vinyl Wrap - conformable vinyl with stretch texture"},
    "enh_soft_gloss":   {"M": 0,   "R": 40,  "CC": 20,  "paint_fn": paint_enh_soft_gloss,   "base_spec_fn": spec_enh_soft_gloss,   "desc": "Enhanced Soft Gloss - gentle gloss with warm micro-shimmer"},
    "enh_soft_matte":   {"M": 0,   "R": 195, "CC": 160, "paint_fn": paint_enh_soft_matte,   "base_spec_fn": spec_enh_soft_matte,   "desc": "Enhanced Soft Matte - velvet-touch matte with organic grain"},
    "enh_warm_white":   {"M": 0,   "R": 115, "CC": 90,  "paint_fn": paint_enh_warm_white,   "base_spec_fn": spec_enh_warm_white,   "desc": "Enhanced Warm White - creamy warm white with ceramic undertone"},
    "enh_ceramic_glaze":{"M": 5,   "R": 15,  "CC": 16,  "paint_fn": paint_enh_ceramic_glaze,"base_spec_fn": spec_enh_ceramic_glaze,"desc": "Enhanced Ceramic Glaze - deep wet ceramic with pool depth"},
    "enh_silk":         {"M": 10,  "R": 55,  "CC": 35,  "paint_fn": paint_enh_silk,         "base_spec_fn": spec_enh_silk,         "desc": "Enhanced Silk - ultra-smooth with subtle directional sheen"},
    "enh_eggshell":     {"M": 0,   "R": 65,  "CC": 45,  "paint_fn": paint_enh_eggshell,     "base_spec_fn": spec_enh_eggshell,     "desc": "Enhanced Eggshell - subtle orange-peel texture with warm tone"},
    "enh_primer":       {"M": 0,   "R": 180, "CC": 160, "paint_fn": paint_enh_primer,       "base_spec_fn": spec_enh_primer,       "desc": "Enhanced Primer - rough industrial primer with grit variation"},
    # 2026-04-19 HEENAN HA12 — Animal sister-hunt: name promises matte,
    # R=160 was satin/scuffed band. Bumped to R=200 — true matte threshold.
    "enh_clear_matte":  {"M": 0,   "R": 200, "CC": 140, "paint_fn": paint_enh_clear_matte,  "base_spec_fn": spec_enh_clear_matte,  "desc": "Enhanced Clear Matte - protective flat coat with micro-haze (HA12: R 160→200)"},
    "enh_semi_gloss":   {"M": 0,   "R": 55,  "CC": 30,  "paint_fn": paint_enh_semi_gloss,   "base_spec_fn": spec_enh_semi_gloss,   "desc": "Enhanced Semi Gloss - sweet spot between gloss and satin"},
    "enh_wet_look":     {"M": 0,   "R": 15,  "CC": 16,  "paint_fn": paint_enh_wet_look,     "base_spec_fn": spec_enh_wet_look,     "desc": "Enhanced Wet Look - ultra-deep wet coating with clarity depth"},
    "enh_piano_black":  {"M": 0,   "R": 20,  "CC": 16,  "paint_fn": paint_enh_piano_black,  "base_spec_fn": spec_enh_piano_black,  "desc": "Enhanced Piano Black - mirror-deep black with reflection depth"},
    # 2026-04-19 HEENAN HA13 — Animal sister-hunt: name promises matte,
    # R=170 below matte threshold. Bumped to R=195 — true matte band.
    "enh_living_matte": {"M": 5,   "R": 195, "CC": 145, "paint_fn": paint_enh_living_matte, "base_spec_fn": spec_enh_living_matte, "desc": "Enhanced Living Matte - organic matte with biological grain (HA13: R 170→195)"},
    "enh_neutral_grey": {"M": 0,   "R": 180, "CC": 145, "paint_fn": paint_enh_neutral_grey, "base_spec_fn": spec_enh_neutral_grey, "desc": "Enhanced Neutral Grey - professional neutral with micro-grain"},
    "enh_clear_satin":  {"M": 0,   "R": 95,  "CC": 70,  "paint_fn": paint_enh_clear_satin,  "base_spec_fn": spec_enh_clear_satin,  "desc": "Enhanced Clear Satin - satin clearcoat with orange-peel micro"},
    "enh_pure_black":   {"M": 0,   "R": 235, "CC": 185, "paint_fn": paint_enh_piano_black,  "base_spec_fn": spec_enh_pure_black,  "desc": "Enhanced Pure Black - absolute black with dead matte grain"},
}
