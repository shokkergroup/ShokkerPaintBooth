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

    # Two-octave grain: coarse body + fine micro-texture.
    coarse = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 500)
    fine = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], s + 501)
    grain = (coarse * 0.6 + fine * 0.4) * _GRAIN_AMPLITUDE * pm

    result = paint  # already a defensive copy
    m3 = mask[:, :, np.newaxis]
    result[:, :, :3] = np.clip(result[:, :, :3] + grain[:, :, np.newaxis] * m3,
                               0.0, 1.0)

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
# SPEC FACTORY
# ============================================================================

def _make_spec(base_m: float, base_r: float, base_cc: float,
               seed_offset: int, m_var: float = 15.0, r_var: float = 15.0,
               cc_var: float = 8.0, chrome_allowed: bool = False) -> SpecFn:
    """Factory: produces a FLAT spec function for a Foundation Base.

    2026-04-21 painter report: Foundation Bases were adding visible noise
    texture to the spec map via `multi_scale_noise * (m_var/r_var/cc_var)`.
    The painter's report: "NONE of the foundation bases are supposed to
    do ANYTHING other than change the texture/look of the color it's
    affecting. [...] The FOUNDATION FUCKING BASES are supposed to be
    vanilla." So Metallic foundation should output FLAT M=200, R=45,
    CC=16 — not noisy values sweeping through m_var=30.

    The m_var / r_var / cc_var arguments are kept in the signature for
    backward-compat with existing call sites (e.g. `_make_spec(200, 45,
    16, 6030, m_var=30, r_var=15, cc_var=14)`), but are now IGNORED. The
    HARDMODE loop that tuned those variances for "visible dM/dR/dCC"
    was working to the wrong design intent.

    Args:
        base_m:         Base metallic channel value (0-255) — FLAT.
        base_r:         Base roughness channel value (0-255) — FLAT.
        base_cc:        Base clearcoat channel value (16-255) — FLAT.
        seed_offset:    Unused (kept for signature compat).
        m_var:          IGNORED (kept for signature compat).
        r_var:          IGNORED.
        cc_var:         IGNORED.
        chrome_allowed: If True, ``R < 15`` is kept where ``M >= 240``.

    Returns:
        Callable ``spec_fn(shape, seed, sm, base_m, base_r)`` that returns
        flat M/R/CC arrays of constant value.
    """
    def spec_fn(shape, seed, sm, bm, br):  # bm/br unused — baked into closure
        try:
            h, w = _hw(shape)
            # FLAT output: every pixel gets the same M/R/CC. No noise,
            # no variance, no per-pixel modulation. `sm` also ignored —
            # Foundation intensity is the painter's base_strength slider,
            # not a pattern-variation scalar.
            M = np.full((h, w), float(base_m), dtype=np.float32)
            R = np.full((h, w), float(base_r), dtype=np.float32)
            CC = np.full((h, w), float(base_cc), dtype=np.float32)
            return _enforce_iron(M, R, CC, chrome_allowed=chrome_allowed)
        except Exception as exc:  # noqa: BLE001
            logger.error("spec factory (offset=%d) failed: %s", seed_offset, exc)
            return _neutral_spec(shape, base_m, base_r, base_cc)

    spec_fn.__name__ = f"spec_enh_factory_{seed_offset}"
    spec_fn.__doc__ = (
        f"Foundation Base spec function (flat M={base_m}, R={base_r}, "
        f"CC={base_cc}, chrome={chrome_allowed}). NO noise — Foundation "
        f"Bases must output flat material properties."
    )
    return spec_fn


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
spec_enh_gloss = _make_spec(0, 18, 16, 6000, m_var=5, r_var=22, cc_var=12)


# ============================================================================
# 2. ENHANCED MATTE — organic micro-grain matte with pore texture
# ============================================================================

def paint_enh_matte(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Enhanced Matte: organic micro-grain with mild desaturation.

    Color-safe: yes (desaturation preserves identity at desat=0).
    """
    return _subtle_grain(paint, shape, mask, seed, pm, bb, desat=0.3)


spec_enh_matte = _make_spec(0, 200, 170, 6010, m_var=5, r_var=20, cc_var=15)


# ============================================================================
# 3. ENHANCED SATIN — directional brushed satin sheen
# ============================================================================

def paint_enh_satin(paint: np.ndarray, shape, mask: np.ndarray, seed,
                    pm: float, bb) -> np.ndarray:
    """Enhanced Satin: subtle warm sheen with brushed grain."""
    return _subtle_grain(paint, shape, mask, seed, pm, bb, warmth=0.3)


spec_enh_satin = _make_spec(15, 90, 55, 6020, m_var=10, r_var=18, cc_var=10)


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
spec_enh_metallic = _make_spec(200, 45, 16, 6030, m_var=30, r_var=15, cc_var=14)


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
spec_enh_pearl = _make_spec(100, 35, 16, 6040, m_var=25, r_var=12, cc_var=16)


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
    """Enhanced Chrome spec — FLAT mirror chrome. 2026-04-21 painter fix:
    previously added `disp`/`micro` noise on top of M/R/CC. Foundation
    Bases must be flat; chrome LOOK comes from the spec values, not
    from surface texture noise."""
    try:
        h, w = _hw(shape)
        M = np.full((h, w), 250.0, dtype=np.float32)
        R = np.full((h, w), 2.0, dtype=np.float32)
        CC = np.full((h, w), float(CC_MIN), dtype=np.float32)
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
    """Enhanced Satin Chrome spec — FLAT. 2026-04-21 painter fix:
    previously applied a `brush` multi_scale_noise pattern to create
    directional grain. A Foundation Base must be flat; painters who
    want a brushed grain look should add a brushed Spec Pattern
    Overlay on top, not bake it into the Foundation."""
    try:
        h, w = _hw(shape)
        M = np.full((h, w), 248.0, dtype=np.float32)
        R = np.full((h, w), 45.0, dtype=np.float32)
        CC = np.full((h, w), 40.0, dtype=np.float32)
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


spec_enh_anodized = _make_spec(180, 60, 80, 6070, m_var=20, r_var=15, cc_var=12)


def paint_enh_baked_enamel(p, s, m, sd, pm, bb):
    """Enhanced Baked Enamel: kiln-warm tinted gloss."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.6)


# 2026-04-20 HEENAN AUTO-LOOP-4 — enh_baked_enamel desc promises
# "kiln-fired warmth and depth variation" but r_var=4 cc_var=3 produced
# dR=5 dCC=5 (probe seed=42 256²). Real baked enamel has visible orange-
# peel micro-ripple from the curing process. Widen r_var 4→18 and
# cc_var 3→12 so kiln-cured depth actually reads.
spec_enh_baked_enamel = _make_spec(0, 16, 18, 6080, m_var=3, r_var=18, cc_var=12)


def paint_enh_brushed(p, s, m, sd, pm, bb):
    """Enhanced Brushed: slight desaturation over grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.15)


def spec_enh_brushed(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Enhanced Brushed spec — FLAT. 2026-04-21 painter fix: previously
    applied a directional brush grain via multi_scale_noise. A
    Foundation Base must be flat; painters who want a brushed grain
    look should add a brushed Spec Pattern Overlay, not bake it into
    the Foundation."""
    try:
        h, w = _hw(shape)
        M = np.full((h, w), 180.0, dtype=np.float32)
        R = np.full((h, w), 75.0, dtype=np.float32)
        CC = np.full((h, w), 65.0, dtype=np.float32)
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
spec_enh_carbon_fiber = _make_spec(55, 28, 16, 6100, m_var=15, r_var=10, cc_var=18)


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


spec_enh_frozen = _make_spec(160, 80, 125, 6110, m_var=20, r_var=25, cc_var=20)


def paint_enh_gel_coat(p, s, m, sd, pm, bb):
    """Enhanced Gel Coat: subtle warmth on top of grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.2)


# 2026-04-20 HEENAN AUTO-LOOP-3 — enh_gel_coat desc says "fiberglass
# gel coat with flow-out variation" but ±3 r_var ±2 cc_var gave dR=3
# dCC=2 at seed=42 256² — no visible flow. Real gel coat cures with
# pooling / wet-flow marks from surface tension. Widen r_var 3→20 and
# cc_var 2→11. Sibling fix to AUTO-LOOP-1 (enh_wet_look) in the same
# _make_spec factory family.
spec_enh_gel_coat = _make_spec(0, 15, 16, 6120, m_var=3, r_var=20, cc_var=11)


def paint_enh_powder_coat(p, s, m, sd, pm, bb):
    """Enhanced Powder Coat: mild desaturation over grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.1)


spec_enh_powder_coat = _make_spec(10, 115, 140, 6130, m_var=8, r_var=20, cc_var=15)


def paint_enh_vinyl_wrap(p, s, m, sd, pm, bb):
    """Enhanced Vinyl Wrap: neutral grain only."""
    return _subtle_grain(p, s, m, sd, pm, bb)


spec_enh_vinyl_wrap = _make_spec(0, 95, 105, 6140, m_var=5, r_var=15, cc_var=12)


def paint_enh_soft_gloss(p, s, m, sd, pm, bb):
    """Enhanced Soft Gloss: gentle warm bias."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.1)


# 2026-04-20 HEENAN AUTO-LOOP-26 — enh_soft_gloss desc "warm micro-
# shimmer and subtle depth". r_var=6 cc_var=3 produced dR=12 dCC=6
# — shimmer-and-depth promise invisible. Widen r_var 6→25 and
# cc_var 3→13 so warm shimmer reads.
spec_enh_soft_gloss = _make_spec(0, 40, 20, 6150, m_var=3, r_var=25, cc_var=13)


def paint_enh_soft_matte(p, s, m, sd, pm, bb):
    """Enhanced Soft Matte: velvet-touch desaturation over grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.25)


spec_enh_soft_matte = _make_spec(0, 195, 160, 6160, m_var=5, r_var=18, cc_var=12)


def paint_enh_warm_white(p, s, m, sd, pm, bb):
    """Enhanced Warm White: strong warm bias."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.8)


spec_enh_warm_white = _make_spec(0, 115, 90, 6170, m_var=3, r_var=12, cc_var=8)


# ============================================================================
# 20-30: NEW Enhanced finishes (no flat counterpart)
# ============================================================================

# 20. ENHANCED CERAMIC GLAZE — deep wet ceramic with pool depth
def paint_enh_ceramic_glaze(p, s, m, sd, pm, bb):
    """Enhanced Ceramic Glaze: warm-biased wet ceramic."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.3)


# 2026-04-20 HEENAN AUTO-LOOP-2 — enh_ceramic_glaze desc promises
# "hand-fired ceramic glaze with pooled color depth and delicate surface
# crazing" but the factory ±5 r_var ±3 cc_var produced dR=5 dCC=3 at
# seed=42 256² — no visible pooling. Real hand-fired glaze has strong
# flow-out pooling (wider R variation) and thicker-thinner clearcoat
# (wider CC). Widen r_var 5→25 and cc_var 3→14.
spec_enh_ceramic_glaze = _make_spec(5, 15, 16, 6200, m_var=8, r_var=25, cc_var=14)


# 21. ENHANCED SILK
def paint_enh_silk(p, s, m, sd, pm, bb):
    """Enhanced Silk: ultra-smooth directional sheen."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.15, desat=0.1)


spec_enh_silk = _make_spec(10, 55, 35, 6210, m_var=8, r_var=12, cc_var=6)


# 22. ENHANCED EGGSHELL
def paint_enh_eggshell(p, s, m, sd, pm, bb):
    """Enhanced Eggshell: subtle warmth over orange-peel grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.2)


spec_enh_eggshell = _make_spec(0, 65, 45, 6220, m_var=3, r_var=10, cc_var=6)


# 23. ENHANCED PRIMER
def paint_enh_primer(p, s, m, sd, pm, bb):
    """Enhanced Primer: heavily desaturated industrial grit."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.4)


spec_enh_primer = _make_spec(0, 180, 160, 6230, m_var=5, r_var=25, cc_var=18)


# 24. ENHANCED CLEAR MATTE
def paint_enh_clear_matte(p, s, m, sd, pm, bb):
    """Enhanced Clear Matte: slight desaturation for haze."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.15)


spec_enh_clear_matte = _make_spec(0, 160, 140, 6240, m_var=3, r_var=15, cc_var=10)


# 25. ENHANCED SEMI GLOSS
def paint_enh_semi_gloss(p, s, m, sd, pm, bb):
    """Enhanced Semi Gloss: gentle warm bias on grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, warmth=0.1)


# 2026-04-20 HEENAN AUTO-LOOP-27 — enh_semi_gloss desc "nuanced
# surface between satin and gloss". r_var=8 cc_var=4 gave dR=16 dCC=8.
# Widen r_var 8→26 and cc_var 4→14 for visible semi-gloss nuance.
spec_enh_semi_gloss = _make_spec(0, 55, 30, 6250, m_var=4, r_var=26, cc_var=14)


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
spec_enh_wet_look = _make_spec(0, 15, 16, 6260, m_var=3, r_var=22, cc_var=12)


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
spec_enh_piano_black = _make_spec(0, 20, 16, 6270, m_var=3, r_var=24, cc_var=14)


# 28. ENHANCED LIVING MATTE
def paint_enh_living_matte(p, s, m, sd, pm, bb):
    """Enhanced Living Matte: warm desaturated biological grain."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.3, warmth=0.15)


spec_enh_living_matte = _make_spec(5, 170, 145, 6280, m_var=8, r_var=22, cc_var=15)


# 29. ENHANCED NEUTRAL GREY
def paint_enh_neutral_grey(p, s, m, sd, pm, bb):
    """Enhanced Neutral Grey: heavy desaturation for pro calibration."""
    return _subtle_grain(p, s, m, sd, pm, bb, desat=0.5)


spec_enh_neutral_grey = _make_spec(0, 180, 145, 6290, m_var=3, r_var=15, cc_var=10)


# 30. ENHANCED CLEAR SATIN
def paint_enh_clear_satin(p, s, m, sd, pm, bb):
    """Enhanced Clear Satin: neutral grain only."""
    return _subtle_grain(p, s, m, sd, pm, bb)


spec_enh_clear_satin = _make_spec(0, 95, 70, 6300, m_var=4, r_var=12, cc_var=8)


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
    "spec_enh_clear_satin",
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
    "enh_pure_black":   {"M": 0,   "R": 235, "CC": 185, "paint_fn": paint_enh_piano_black,  "base_spec_fn": spec_enh_primer,       "desc": "Enhanced Pure Black - absolute black with dead matte grain"},
}
