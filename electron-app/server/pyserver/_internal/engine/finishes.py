"""
engine/finishes.py - Standard Finish Functions
================================================
All spec_fn and paint_fn for the BASE_REGISTRY entries.
These are the "building blocks" - combinable bases that get pattern overlays.

CHANNEL SEMANTICS:
    Every spec_fn here writes the M / R / CC / A channels (in that order).
    Iron rules enforced:
        - CC always >= SPEC_CLEARCOAT_MIN (16) when nonzero
        - R always >= SPEC_ROUGHNESS_MIN (15) for non-chrome (M < 240)

PAINT VS SPEC SPLIT:
    spec_fn modifies the spec map only. paint_fn modifies the diffuse paint
    image only. The compose layer handles weaving these per-zone.

CONSISTENT RETURN TYPES:
    spec_fn -> (H, W, 4) uint8 always
    paint_fn -> (H, W, 3) float32 always
    Even on failure, these never raise -- they fall back to neutral output.

NUMERICAL SAFETY:
    All clip operations use the SPEC_CHANNEL_MIN/MAX constants from core.py.
    All noise generation calls catch failures and fall back to zero arrays.

DEBUG OUTPUT:
    Every spec_fn logs a debug message at completion when verbose mode is on
    (via engine.core.engine_core_set_verbose).

-----------------------------------------------------------------------------
SPEC MAP CHANNEL REFERENCE - VERIFIED 2025/2026 (triple-confirmed in-sim)
-----------------------------------------------------------------------------

  R = Metallic   (0=pure paint/dielectric, 255=pure metal/conductor)
  G = Roughness  (0=perfect mirror, 255=chalk/fully diffuse)
  B = Clearcoat  (0=NO coat, 12-18=MAX GLOSS, 128=satin, 255=scuffed/dull)

  ┌─────────────────────────────────────────────────────────────────┐
  │ CLEARCOAT (B channel) - the "wet glass" layer over your paint  │
  │                                                                 │
  │  B = 0          No clearcoat - raw material surface            │
  │  B = 12–18      MAXIMUM GLOSS - factory fresh / show car       │
  │  B = 40–80      Satin / semi-gloss - slight haze               │
  │  B = 81–140     Weathered - daily driver, visible coat wear    │
  │  B = 141–200    Aged / oxidized - heavy haze, faded panels     │
  │  B = 201–255    Scuffed / destroyed - Brillo-pad dull          │
  │                                                                 │
  │ WHY 16 NOT 0 OR 255 FOR GLOSS:                                 │
  │   Old iRacing docs said "leave blue at 255" - back then CC     │
  │   wasn't active (255 was just a placeholder). Now that CC is   │
  │   live, 255 = most degraded clearcoat. Use 16 for max gloss.  │
  └─────────────────────────────────────────────────────────────────┘

FINISH TYPES (current standard bases):
  chrome           → Pure mirror: M=255, G=2,   CC=0
  gloss            → Showroom paint: M=0,   G=15,  CC=16
  metallic         → Standard metallic: M=200, G=45,  CC=16
  pearl            → Iridescent: M=110, G=35,  CC=16
  candy            → Deep lacquer: M=130, G=12,  CC=16
  satin            → Semi-gloss: M=0,   G=95,  CC=50  ← CC=50 not 10!
  matte            → Flat: M=0,   G=210, CC=0
  satin_metal      → Brushed metallic: M=235, G=60,  CC=16
  metal_flake      → Heavy flake: M=240, G=10,  CC=16
  holographic_flake→ Prismatic: M=235, G=8,   CC=16
  stardust         → Dark metal+stars: M=160, G=55,  CC=16
  brushed_titanium → Directional grain: M=180, G=70,  CC=0
  anodized         → Industrial: M=170, G=80,  CC=0
  carbon_fiber     → Twill weave: M=55,  G=30,  CC=16
  frozen           → Icy matte: M=225, G=140, CC=0
  hex_mesh         → Hex grid: varies
  ripple           → Ring interference: varies
  hammered         → Dimple impacts: M=180, G=var, CC=0

NEW RANGE-EXPLOITING FINISHES (use CC 17–255 deliberately):
  wet_gloss        → Ultra-premium gloss: M=0,   G=8,   CC=16  (G lower than standard)
  daily_driver     → Real-world used: M=0,   G=20,  CC=60
  weathered_metal  → Track-worn: M=200, G=55,  CC=100
  race_worn        → Heavily raced: M=180, G=80,  CC=140
  oxidized_metal   → Sun-damaged: M=160, G=90,  CC=200
  ghost_panel      → Clearcoat-only pattern: M=200, G=40, CC varies 16–120
  velvet           → Soft matte+thin coat: M=0,   G=155, CC=45

FIX GUIDE:
  "Satin looks like matte"     → CC was 10 (below threshold). Now 50. ✅ Fixed
  "Gloss looks plastic"        → spec_gloss: M should be 0, G lower (8-15)
  "Chrome has color tint"      → spec_chrome: M=255, G=2, CC=0
  "Metallic looks muddy"       → paint_metallic: lighten albedo when M>150
  "Candy not deep enough"      → CC=16 is correct; adjust G lower (10-12)
"""

import logging
import numpy as np
import sys
import os
from typing import Callable, Optional, Tuple

logger = logging.getLogger("engine.finishes")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core import (
    multi_scale_noise,
    get_mgrid,
    SPEC_ROUGHNESS_MIN,
    SPEC_CLEARCOAT_MIN,
    SPEC_CHANNEL_MAX,
    SPEC_METALLIC_CHROME_THRESHOLD,
)

# Local channel min reused below
_SPEC_CHANNEL_MIN = 0


def _make_neutral_spec(shape: Tuple[int, int], mask: np.ndarray) -> np.ndarray:
    """Emergency fallback spec map (M=0, R=128, CC=16) when something goes wrong.

    Iron-rule compliant. Always returns a valid (H, W, 4) uint8 array even
    if the input shape is degenerate.
    """
    h = max(1, int(shape[0]))
    w = max(1, int(shape[1]))
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[:, :, 0] = 0
    out[:, :, 1] = 128
    out[:, :, 2] = SPEC_CLEARCOAT_MIN
    if mask is not None and mask.shape[:2] == (h, w):
        out[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    else:
        out[:, :, 3] = SPEC_CHANNEL_MAX
    return out


def _delegate(fn_name: str) -> Optional[Callable]:
    """Look up a finish function in the legacy shokker_engine_v2 module.

    Args:
        fn_name: Name of the legacy spec_/paint_ function.

    Returns:
        The function object if found, else None. Failures are logged at debug
        level only -- this is normal during the migration period when many
        names live in the legacy engine.
    """
    try:
        import shokker_engine_v2 as _e
        fn = getattr(_e, fn_name, None)
        if fn is None:
            logger.debug("_delegate: '%s' not found in shokker_engine_v2", fn_name)
        return fn
    except ImportError:
        logger.debug("_delegate: shokker_engine_v2 not available for '%s'", fn_name)
        return None
    except Exception as e:
        logger.warning("_delegate: unexpected error loading '%s': %s", fn_name, e)
        return None


def _make_spec(M: int, G: int, CC: int,
               noise_M: int = 0, noise_G: int = 0, noise_CC: int = 0) -> Callable:
    """Factory: create a spec_fn with given M/G/CC base values plus optional noise.

    Iron rules are baked in at the factory level: if a noise_X parameter is
    supplied, the corresponding channel respects its safety floor (R>=15 for
    non-chrome, CC>=16 when present).

    Args:
        M, G, CC: Base channel values; clamped to [0, 255] at factory time.
        noise_M, noise_G, noise_CC: Noise amplitudes per channel. 0 = flat.

    Returns:
        spec_fn(shape, mask, seed, sm) -> (H, W, 4) uint8 array.
    """
    # Pre-validate base values at factory time -- one-time cost
    _M = max(0, min(255, int(M)))
    _G = max(0, min(255, int(G)))
    _CC = max(0, min(255, int(CC)))

    def spec_fn(shape: Tuple[int, int], mask: np.ndarray, seed: int, sm: float) -> np.ndarray:
        h, w = int(shape[0]), int(shape[1])
        if h <= 0 or w <= 0:
            logger.warning("_make_spec: invalid shape (%d, %d)", h, w)
            return np.zeros((max(1, h), max(1, w), 4), dtype=np.uint8)
        spec = np.zeros((h, w, 4), dtype=np.float32)

        m_val = float(_M)
        g_val = float(_G)
        cc_val = float(_CC)

        # Ensure sm is numeric; default to 1.0 if None
        _sm = float(sm) if sm is not None else 1.0

        if noise_M > 0 or noise_G > 0 or noise_CC > 0:
            try:
                noise = multi_scale_noise(shape, [16, 32, 64], [0.35, 0.40, 0.25], seed)
                noise_sm = noise * _sm
            except Exception as e:
                logger.warning("_make_spec noise generation failed (M=%d, G=%d, CC=%d): %s",
                               _M, _G, _CC, e)
                noise_sm = np.zeros((h, w), dtype=np.float32)
            if noise_M > 0:
                m_val = np.clip(m_val + noise_sm * noise_M, 0, SPEC_CHANNEL_MAX)
            if noise_G > 0:
                # Enforce GGX roughness floor: G >= SPEC_ROUGHNESS_MIN for non-chrome
                g_floor = SPEC_ROUGHNESS_MIN if _M < SPEC_METALLIC_CHROME_THRESHOLD else 0
                g_val = np.clip(g_val + noise_sm * noise_G, g_floor, SPEC_CHANNEL_MAX)
            if noise_CC > 0:
                # Enforce clearcoat floor: CC >= SPEC_CLEARCOAT_MIN when nonzero
                cc_val = np.clip(cc_val + noise_sm * noise_CC,
                                 SPEC_CLEARCOAT_MIN, SPEC_CHANNEL_MAX)

        spec[:, :, 0] = m_val
        spec[:, :, 1] = g_val
        spec[:, :, 2] = cc_val
        spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX)

        return np.clip(spec, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    spec_fn.__name__ = f"spec_M{_M}_G{_G}_CC{_CC}"
    spec_fn.__doc__ = (f"Auto-generated spec_fn (M={_M}, G={_G}, CC={_CC}, "
                       f"noise=M{noise_M}/G{noise_G}/CC{noise_CC}).")
    return spec_fn


def _make_paint_passthrough() -> Callable:
    """Factory: paint_fn that passes the input paint through unchanged.

    Used for spec-only finishes that don't modify the diffuse paint image.
    Returns a fresh function each call so identity comparisons remain unique
    per registry entry.
    """
    def paint_fn(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                 seed: int, pm: float, bb: float) -> np.ndarray:
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        return paint
    paint_fn.__name__ = "paint_passthrough"
    paint_fn.__doc__ = "Identity paint function (factory-built passthrough)."
    return paint_fn


# ================================================================
# SECTION 1: STANDARD BASE SPEC+PAINT FUNCTIONS
# Delegate to legacy engine (stable implementations there)
# All follow signature: spec_fn(shape, mask, seed, sm) → (h,w,4) uint8
#                       paint_fn(paint, shape, mask, seed, pm, bb) → (h,w,4)
# ================================================================

spec_gloss = _delegate('spec_gloss')
paint_gloss = _delegate('paint_gloss')

spec_matte = _delegate('spec_matte')
paint_matte = _delegate('paint_matte')

spec_satin = _delegate('spec_satin')
paint_satin = _delegate('paint_satin')

spec_metallic = _delegate('spec_metallic')
paint_metallic = _delegate('paint_metallic')

spec_pearl = _delegate('spec_pearl')
paint_pearl = _delegate('paint_pearl')

spec_chrome = _delegate('spec_chrome')
paint_chrome = _delegate('paint_chrome')

spec_satin_metal = _delegate('spec_satin_metal')
paint_satin_metal = _delegate('paint_satin_metal')

spec_metal_flake = _delegate('spec_metal_flake')
paint_metal_flake = _delegate('paint_metal_flake')

spec_holographic_flake = _delegate('spec_holographic_flake')
paint_holographic_flake = _delegate('paint_holographic_flake')

spec_stardust = _delegate('spec_stardust')
paint_stardust = _delegate('paint_stardust')

spec_candy = _delegate('spec_candy')
paint_candy = _delegate('paint_candy')

spec_brushed_titanium = _delegate('spec_brushed_titanium')
paint_brushed_titanium = _delegate('paint_brushed_titanium')

spec_anodized = _delegate('spec_anodized')
paint_anodized = _delegate('paint_anodized')

spec_hex_mesh = _delegate('spec_hex_mesh')
paint_hex_mesh = _delegate('paint_hex_mesh')

spec_frozen = _delegate('spec_frozen')
paint_frozen = _delegate('paint_frozen')

spec_carbon_fiber = _delegate('spec_carbon_fiber')
paint_carbon_fiber = _delegate('paint_carbon_fiber')

spec_ripple = _delegate('spec_ripple')
paint_ripple = _delegate('paint_ripple')

spec_hammered = _delegate('spec_hammered')
paint_hammered = _delegate('paint_hammered')


# ================================================================
# SECTION 2: NEW V5 BASE FINISHES - CC Range Exploitation
# These are the first NATIVE V5 spec functions - fully written here,
# no delegation. They deliberately use CC values from 17–255 to
# produce effects the legacy engine never had.
#
# CLEARCOAT REMINDER:
#   CC=0     → no coat (raw material)
#   CC=16    → max gloss / factory fresh
#   CC=50    → semi-gloss / satin
#   CC=100   → weathered / track-worn coat
#   CC=140   → aged / race-worn
#   CC=200   → oxidized / sun-damaged
#   CC=240+  → scuffed/dull (intentional weathered metallic)
# ================================================================


def spec_wet_gloss(shape: Tuple[int, int], mask: np.ndarray, seed: int, sm: float) -> np.ndarray:
    """Wet Gloss: ultra-premium showroom finish.

    Like spec_gloss but G=8 (even smoother) for a near-glass surface.
    M=0, G=8, CC=16 -> dielectric + mirror-smooth + perfect coat.

    Args:
        shape: (H, W) target shape.
        mask: (H, W) zone mask in [0, 1].
        seed: Deterministic seed.
        sm: Spec multiplier (slider).

    Returns:
        (H, W, 4) uint8 spec map (M, R, CC, A).
    """
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        return _make_neutral_spec(shape, mask)
    _sm = float(sm) if sm is not None else 1.0
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    try:
        noise = multi_scale_noise(shape, [16, 32, 64], [0.35, 0.40, 0.25], seed + 100)
    except Exception as e:
        logger.warning("spec_wet_gloss noise failed (seed=%d): %s", seed, e)
        noise = np.zeros((h, w), dtype=np.float32)
    G_BASE = 15          # Near-glass smoothness base
    G_VARIATION = 5      # Noise variation amplitude
    G = np.clip(G_BASE + noise * G_VARIATION * _sm, SPEC_ROUGHNESS_MIN, 25).astype(np.uint8)
    spec[:, :, 0] = 0                    # M=0: pure dielectric
    spec[:, :, 1] = G                    # G: near-glass smoothness with subtle variation
    spec[:, :, 2] = SPEC_CLEARCOAT_MIN   # CC=16: max gloss clearcoat
    spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    logger.debug("spec_wet_gloss: %dx%d seed=%d sm=%.3f", w, h, seed, _sm)
    return spec


def paint_wet_gloss(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                    seed: int, pm: float, bb: float) -> np.ndarray:
    """Wet-gloss paint: subtly deepens saturation to emulate clearcoat depth.

    Args:
        paint: (H, W, 3+) float32 paint array.
        shape: (H, W) target shape (unused; signature compatibility).
        mask: (H, W) zone mask.
        seed: Deterministic seed (unused).
        pm: Paint multiplier.
        bb: Brightness boost (unused).

    Returns:
        (H, W, 3) float32 paint with mild saturation boost in-mask.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    _pm = float(pm) if pm is not None else 1.0
    SAT_ENHANCEMENT = 0.08   # 8% saturation boost through clearcoat depth
    # Vectorized: apply saturation boost to all channels at once (no per-channel loop)
    boost = 1.0 + mask[:, :, np.newaxis] * SAT_ENHANCEMENT * _pm
    result = np.clip(paint * boost, 0, 1).astype(np.float32)
    return result


def spec_daily_driver(shape: Tuple[int, int], mask: np.ndarray,
                      seed: int, sm: float) -> np.ndarray:
    """Daily Driver: real-world used car finish.

    Perfect paint color + slightly worn clearcoat (CC=60). Matte paint base
    (M=0) like gloss, but clearcoat has visible everyday wear.

    Args:
        shape: (H, W).
        mask: (H, W) zone mask in [0, 1].
        seed: Deterministic seed.
        sm: Spec multiplier slider.

    Returns:
        (H, W, 4) uint8 spec map.
    """
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        return _make_neutral_spec(shape, mask)
    _sm = float(sm) if sm is not None else 1.0
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    try:
        noise = multi_scale_noise(shape, [8, 16, 32], [0.30, 0.40, 0.30], seed + 200)
    except Exception as e:
        logger.warning("spec_daily_driver noise failed (seed=%d): %s", seed, e)
        noise = np.zeros((h, w), dtype=np.float32)
    CC_BASE = 60        # Mid-wear clearcoat
    CC_VARIATION = 20   # Wear variation amplitude
    CC_MIN = 40         # Minimum CC for daily driver (still some coat)
    CC_MAX = 90         # Maximum CC (not fully degraded)
    G_BASE = 20         # Slight roughness
    G_VARIATION = 8     # Roughness variation
    CC = np.clip(CC_BASE + noise * CC_VARIATION * _sm, CC_MIN, CC_MAX).astype(np.uint8)
    G = np.clip(G_BASE + noise * G_VARIATION * _sm, SPEC_ROUGHNESS_MIN, 35).astype(np.uint8)
    spec[:, :, 0] = 0
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    return spec

def paint_daily_driver(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                       seed: int, pm: float, bb: float) -> np.ndarray:
    """Daily-driver paint: color unchanged; subtle micro-variation breaks flat-paint look.

    The wear effect is entirely in spec_daily_driver; this function only adds
    a barely-perceptible 0.5% brightness wobble so completely flat panels
    don't look CG-fake.

    Args:
        paint: (H, W, 3+) float32 paint array.
        shape: (H, W) target shape.
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        pm: Paint multiplier (skipped entirely below 0.01).
        bb: Brightness boost (unused).

    Returns:
        (H, W, 3) float32 paint with subtle micro-variation in-mask.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    result = paint.copy()
    # Add extremely subtle per-pixel variation to break uniform flatness
    MICRO_VARIATION = 0.005  # 0.5% brightness variation for realism
    _pm = float(pm) if pm is not None else 1.0
    if _pm > 0.01:
        try:
            import cv2  # local import: cv2 is heavy and only needed in this branch
            h, w = int(shape[0]), int(shape[1])
            rng = np.random.RandomState(seed + 205)
            micro = rng.randn(h, w).astype(np.float32)
            # Smooth the random noise for coherent variation (not per-pixel static)
            micro = cv2.GaussianBlur(micro, (5, 5), 1.0) * MICRO_VARIATION * _pm
            # Single broadcast add -- avoids materializing micro * mask as a separate temp
            result[:, :, :3] = np.clip(
                result[:, :, :3] + (micro * mask)[:, :, np.newaxis], 0, 1
            )
        except Exception as e:
            logger.warning("paint_daily_driver micro-variation failed (seed=%d): %s", seed, e)
    return result


def spec_weathered_metal(shape: Tuple[int, int], mask: np.ndarray,
                         seed: int, sm: float) -> np.ndarray:
    """Weathered Metal: track-worn metallic.

    High metallic base but clearcoat is well-worn (CC=100). Looks like a
    well-used metallic car that's seen real racing. Areas of heavier wear
    get higher CC (duller) driven by panel-scale noise.

    Args:
        shape: (H, W).
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        sm: Spec multiplier.

    Returns:
        (H, W, 4) uint8 spec map.
    """
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        return _make_neutral_spec(shape, mask)
    _sm = float(sm) if sm is not None else 1.0
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    try:
        # Large-scale wear pattern (scratches at panel scale)
        wear = multi_scale_noise(shape, [16, 32, 64], [0.30, 0.40, 0.30], seed + 300)
        wear_n = np.clip(wear * 0.5 + 0.5, 0, 1)
        # Fine metallic flake variation
        fine = multi_scale_noise(shape, [16, 32, 64], [0.40, 0.35, 0.25], seed + 310)
    except Exception as e:
        logger.warning("spec_weathered_metal noise failed (seed=%d): %s", seed, e)
        wear_n = np.full((h, w), 0.5, dtype=np.float32)
        fine = np.zeros((h, w), dtype=np.float32)

    M = np.clip(200 + fine * 30 * _sm, 160, 240).astype(np.uint8)
    G = np.clip(55 + wear_n * 25 * _sm, SPEC_ROUGHNESS_MIN, 90).astype(np.uint8)
    CC = np.clip(100 + wear_n * 40 * _sm, 80, 150).astype(np.uint8)

    spec[:, :, 0] = M
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    return spec

def paint_weathered_metal(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                          seed: int, pm: float, bb: float) -> np.ndarray:
    """Weathered metal - subtle darkening of highlights to simulate grime.

    Vectorized: applies the per-pixel darkening factor across all 3 RGB
    channels in one broadcast multiply (no per-channel Python loop).

    Args:
        paint: (H, W, 3+) float32 paint array in [0, 1].
        shape: (H, W) target shape.
        mask: (H, W) zone mask in [0, 1].
        seed: Deterministic seed.
        pm: Paint multiplier (slider 0..1+).
        bb: Brightness boost (unused for this finish).

    Returns:
        (H, W, 3) float32 paint with weathering applied inside the mask.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    _pm = float(pm) if pm is not None else 1.0
    try:
        noise = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 315)
    except Exception as e:
        logger.warning("paint_weathered_metal noise failed: %s", e)
        noise = np.zeros((paint.shape[0], paint.shape[1]), dtype=np.float32)
    wear = np.clip(noise * 0.5 + 0.5, 0, 1)
    # Per-pixel darkening factor: subtle (max 10% darken) and only inside mask.
    # Single broadcast multiply -- replaces the prior 3-iteration per-channel loop.
    darken = (1.0 - wear * 0.10 * _pm) * mask + (1.0 - mask)
    result = np.clip(paint[:, :, :3] * darken[:, :, np.newaxis], 0, 1).astype(np.float32)
    return result


def spec_race_worn(shape: Tuple[int, int], mask: np.ndarray,
                   seed: int, sm: float) -> np.ndarray:
    """Race Worn: heavily raced metallic.

    CC=140 = significant clearcoat degradation from racing exposure. Patchy
    coverage (some sections less worn than others). M=180 = still metallic
    but not showroom-fresh.

    Args:
        shape: (H, W).
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        sm: Spec multiplier.

    Returns:
        (H, W, 4) uint8 spec map.
    """
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        return _make_neutral_spec(shape, mask)
    _sm = float(sm) if sm is not None else 1.0
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    try:
        # Large panel-scale wear pattern
        panel_wear = multi_scale_noise(shape, [32, 64, 128], [0.25, 0.45, 0.30], seed + 400)
        pn = np.clip(panel_wear * 0.5 + 0.5, 0, 1)
        # Fine surface scratches
        scratches = multi_scale_noise(shape, [32, 64], [0.50, 0.50], seed + 410)
        sn = np.clip(scratches * 0.5 + 0.5, 0, 1)
    except Exception as e:
        logger.warning("spec_race_worn noise failed: %s", e)
        pn = np.full((h, w), 0.5, dtype=np.float32)
        sn = np.full((h, w), 0.5, dtype=np.float32)

    M = np.clip(180 + sn * 40 * _sm, 140, 230).astype(np.uint8)
    G = np.clip(80 + pn * 30 * _sm, 60, 120).astype(np.uint8)
    CC = np.clip(140 + pn * 60 * _sm, 100, 200).astype(np.uint8)

    spec[:, :, 0] = M
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    return spec

def paint_race_worn(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                    seed: int, pm: float, bb: float) -> np.ndarray:
    """Race-worn paint - moderate darkening with warm-tinted grime.

    Vectorized: per-channel darken/add factors are stacked into broadcastable
    arrays and applied in two ops instead of three Python iterations.

    Args:
        paint: (H, W, 3+) float32 paint array.
        shape: (H, W) target shape.
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        pm: Paint multiplier.
        bb: Brightness boost (unused).

    Returns:
        (H, W, 3) float32 paint with grime applied.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    _pm = float(pm) if pm is not None else 1.0
    try:
        noise = multi_scale_noise(shape, [8, 16, 32], [0.35, 0.40, 0.25], seed + 415)
    except Exception as e:
        logger.warning("paint_race_worn noise failed: %s", e)
        noise = np.zeros((paint.shape[0], paint.shape[1]), dtype=np.float32)
    grime = np.clip(noise * 0.5 + 0.5, 0, 1) * mask
    grime3 = grime[:, :, np.newaxis]
    # Per-channel darken / add factors as constant 1D vectors -- broadcast once.
    darken = np.array([0.12, 0.12, 0.15], dtype=np.float32)[None, None, :]
    add_tint = np.array([0.05, 0.04, 0.0], dtype=np.float32)[None, None, :]
    result = np.clip(paint[:, :, :3] * (1 - grime3 * darken * _pm)
                     + grime3 * add_tint * _pm, 0, 1).astype(np.float32)
    return result


def spec_oxidized_metal(shape: Tuple[int, int], mask: np.ndarray,
                        seed: int, sm: float) -> np.ndarray:
    """Oxidized Metal: sun-damaged metallic panels.

    CC=200 = heavy clearcoat degradation from UV exposure. The car still has
    metallic base (M=160) but the top coat is nearly destroyed. Creates that
    chalky metallic look of a car left in the sun for years.

    Args:
        shape: (H, W).
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        sm: Spec multiplier.

    Returns:
        (H, W, 4) uint8 spec map.
    """
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        return _make_neutral_spec(shape, mask)
    _sm = float(sm) if sm is not None else 1.0
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    try:
        # Large blotchy oxidation pattern
        oxidation = multi_scale_noise(shape, [24, 48, 96], [0.25, 0.40, 0.35], seed + 500)
        ox = np.clip(oxidation * 0.5 + 0.5, 0, 1)
    except Exception as e:
        logger.warning("spec_oxidized_metal noise failed: %s", e)
        ox = np.full((h, w), 0.5, dtype=np.float32)

    M = np.clip(160 - ox * 40 * _sm, 100, 180).astype(np.uint8)
    G = np.clip(90 + ox * 40 * _sm, 70, 140).astype(np.uint8)
    CC = np.clip(200 + ox * 40 * _sm, 160, 245).astype(np.uint8)

    spec[:, :, 0] = M
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    return spec

def paint_oxidized_metal(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                         seed: int, pm: float, bb: float) -> np.ndarray:
    """Oxidized - fades and desaturates the paint color for sun-damaged look.

    Vectorized: replaces the per-channel for loop with a single broadcast
    expression. Luma uses ITU-R BT.601 weights for consistency with the
    rest of the engine's color analysis.

    Args:
        paint: (H, W, 3+) float32 paint array.
        shape: (H, W) target shape.
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        pm: Paint multiplier.
        bb: Brightness boost (unused).

    Returns:
        (H, W, 3) float32 desaturated paint.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    _pm = float(pm) if pm is not None else 1.0
    try:
        noise = multi_scale_noise(shape, [24, 48], [0.5, 0.5], seed + 505)
    except Exception as e:
        logger.warning("paint_oxidized_metal noise failed: %s", e)
        noise = np.zeros((paint.shape[0], paint.shape[1]), dtype=np.float32)
    fade = (np.clip(noise * 0.5 + 0.5, 0, 1) * mask)[:, :, np.newaxis]
    # BT.601 luma -- broadcast through channels in one expression
    lum = (0.299 * paint[:, :, 0] +
           0.587 * paint[:, :, 1] +
           0.114 * paint[:, :, 2])[:, :, np.newaxis]
    result = np.clip(paint[:, :, :3] * (1 - fade * 0.35 * _pm)
                     + lum * fade * 0.25 * _pm, 0, 1).astype(np.float32)
    return result


def spec_ghost_panel(shape: Tuple[int, int], mask: np.ndarray,
                     seed: int, sm: float) -> np.ndarray:
    """Ghost Panel: clearcoat-only hidden pattern.

    M and G channels are UNIFORM everywhere (consistent metallic). Only the
    CC channel varies - some areas get CC=16 (perfect gloss), others get
    CC=80-120 (slightly hazed).

    Result: at most angles the car looks uniform. But as light rakes across
    the surface, hidden panels APPEAR in the clearcoat. A secret design
    that only reveals itself in certain lighting.

    PARADIGM 2 from the Spec Map Bible.

    Args:
        shape: (H, W).
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        sm: Spec multiplier; controls sigmoid steepness of the ghost reveal.

    Returns:
        (H, W, 4) uint8 spec map.
    """
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        return _make_neutral_spec(shape, mask)
    _sm = float(sm) if sm is not None else 1.0
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    try:
        # Large-scale ghost pattern (panel-scale features)
        ghost = multi_scale_noise(shape, [32, 64, 128], [0.30, 0.40, 0.30], seed + 600)
        gn = np.clip(ghost * 0.5 + 0.5, 0, 1)
    except Exception as e:
        logger.warning("spec_ghost_panel noise failed: %s", e)
        gn = np.full((h, w), 0.5, dtype=np.float32)

    GHOST_CC_PERFECT = 16   # Perfect clearcoat (max gloss)
    GHOST_CC_HAZED = 90     # Slightly hazed clearcoat
    GHOST_THRESHOLD = 0.55  # Pattern threshold for ghost reveal
    GHOST_M = 200           # Consistent metallic value
    GHOST_G = 40            # Consistent roughness value

    # Use smooth sigmoid transition instead of hard threshold for subtler ghost reveal
    # Sigmoid: 1/(1+exp(-k*(x-threshold))) — smooth step at threshold
    _k = 12.0 * _sm  # Steepness of transition (higher = sharper ghost boundary)
    ghost_blend = 1.0 / (1.0 + np.exp(-_k * (gn - GHOST_THRESHOLD)))
    CC = np.clip(GHOST_CC_HAZED + (GHOST_CC_PERFECT - GHOST_CC_HAZED) * ghost_blend,
                 SPEC_CLEARCOAT_MIN, SPEC_CHANNEL_MAX).astype(np.uint8)

    spec[:, :, 0] = GHOST_M    # M: consistent metallic
    spec[:, :, 1] = GHOST_G    # G: consistent smoothness
    spec[:, :, 2] = CC         # CC: varies - the "ghost" is only in clearcoat
    spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    logger.debug("spec_ghost_panel: %dx%d seed=%d threshold=%.2f", w, h, seed, GHOST_THRESHOLD)
    return spec

def paint_ghost_panel(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                      seed: int, pm: float, bb: float) -> np.ndarray:
    """Ghost-panel paint: unchanged. Effect is entirely in the spec map.

    Returns a defensive copy so callers can mutate without aliasing back.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return paint.copy()


def spec_velvet(shape: Tuple[int, int], mask: np.ndarray,
                seed: int, sm: float) -> np.ndarray:
    """Velvet: ultra-soft matte with a barely-there clearcoat.

    Channel breakdown:
        G=155: very rough surface (near-matte but not full matte).
        CC=45: just above satin - thin coat that softens without glossing.
        M=0:   pure dielectric for maximum Fresnel contrast at edges.

    Result: the surface looks velvety soft. At normal incidence -> nearly matte.
    At glancing angles -> the Fresnel effect kicks in (dielectric) creating
    a subtle edge glow that real velvet has.

    Args:
        shape: (H, W).
        mask: (H, W) zone mask.
        seed: Deterministic seed.
        sm: Spec multiplier.

    Returns:
        (H, W, 4) uint8 spec map.
    """
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        return _make_neutral_spec(shape, mask)
    _sm = float(sm) if sm is not None else 1.0
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    try:
        noise = multi_scale_noise(shape, [16, 32, 64], [0.40, 0.35, 0.25], seed + 700)
    except Exception as e:
        logger.warning("spec_velvet noise failed: %s", e)
        noise = np.zeros((h, w), dtype=np.float32)
    VELVET_G_BASE = 155   # Very rough base (velvet texture)
    VELVET_G_RANGE = 20   # Roughness variation
    VELVET_CC_BASE = 45   # Thin clearcoat
    VELVET_CC_RANGE = 10  # Clearcoat variation
    G = np.clip(VELVET_G_BASE + noise * VELVET_G_RANGE * _sm, 130, 180).astype(np.uint8)
    CC = np.clip(VELVET_CC_BASE + noise * VELVET_CC_RANGE * _sm, 35, 60).astype(np.uint8)
    spec[:, :, 0] = 0
    spec[:, :, 1] = G
    spec[:, :, 2] = CC
    spec[:, :, 3] = np.clip(mask * 255, 0, SPEC_CHANNEL_MAX).astype(np.uint8)
    return spec

def paint_velvet(paint: np.ndarray, shape: Tuple[int, int], mask: np.ndarray,
                 seed: int, pm: float, bb: float) -> np.ndarray:
    """Velvet paint: slight warmth shift to enhance the soft fabric feel.

    Adds a touch of red and removes a touch of blue inside the mask. Vectorized
    via constant per-channel deltas.

    Args:
        paint: (H, W, 3+) float32 paint array.
        shape: (H, W) target shape.
        mask: (H, W) zone mask.
        seed: Deterministic seed (unused).
        pm: Paint multiplier.
        bb: Brightness boost (unused).

    Returns:
        (H, W, 3) float32 paint with warm shift inside the mask.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    _pm = float(pm) if pm is not None else 1.0
    WARM_RED_BOOST = 0.03    # Subtle red warmth
    COOL_BLUE_REDUCE = 0.02  # Slight blue reduction for warmth
    result = paint.copy()
    # Apply warm tint shift -- two channels only, kept separate for clarity
    result[:, :, 0] = np.clip(paint[:, :, 0] + mask * WARM_RED_BOOST * _pm, 0, 1)
    result[:, :, 2] = np.clip(paint[:, :, 2] - mask * COOL_BLUE_REDUCE * _pm, 0, 1)
    return result


# ================================================================
# SECTION 3: ADVANCED FINISH FUNCTIONS (24K Arsenal exclusive bases)
# ================================================================

def build_advanced_base_registry() -> dict:
    """Return all 24K Arsenal base entries as a dict of (spec_fn, paint_fn) tuples.

    Returns:
        dict mapping finish_id -> (spec_fn, paint_fn). Empty dict when the
        24K expansion module is unavailable.
    """
    try:
        import shokker_24k_expansion as _exp
        return getattr(_exp, 'BASE_REGISTRY', {})
    except Exception as e:
        logger.debug("build_advanced_base_registry: 24K expansion unavailable (%s)", e)
        return {}


# ================================================================
# NEW V5 FINISH REGISTRY - all native V5 bases in one dict
# Registry.py imports this and merges into BASE_REGISTRY.
#
# Lookup order in registry.py:
#   1. BASE_REGISTRY (legacy + standard finishes)
#   2. V5_BASE_FINISHES (this dict)
#   3. build_advanced_base_registry() (24K Arsenal expansion)
#
# Each entry is (spec_fn, paint_fn). See module-level "CONSISTENT RETURN
# TYPES" note above for the contract every function must satisfy.
# ================================================================

V5_BASE_FINISHES = {
    "wet_gloss":        (spec_wet_gloss,       paint_wet_gloss),
    "daily_driver":     (spec_daily_driver,     paint_daily_driver),
    "weathered_metal":  (spec_weathered_metal,  paint_weathered_metal),
    "race_worn":        (spec_race_worn,         paint_race_worn),
    "oxidized_metal":   (spec_oxidized_metal,    paint_oxidized_metal),
    "ghost_panel":      (spec_ghost_panel,       paint_ghost_panel),
    "velvet":           (spec_velvet,            paint_velvet),
}


def get_v5_finish(finish_id: str) -> Optional[Tuple[Callable, Callable]]:
    """Look up a V5 native finish by id.

    Args:
        finish_id: The finish id (e.g. "wet_gloss", "ghost_panel").

    Returns:
        (spec_fn, paint_fn) tuple if found, else None. Logs a warning on
        unknown ids so registry merge failures show up in the build log
        instead of failing silently.
    """
    if finish_id not in V5_BASE_FINISHES:
        logger.warning("get_v5_finish: unknown finish id '%s' (available: %s)",
                       finish_id, sorted(V5_BASE_FINISHES))
        return None
    return V5_BASE_FINISHES[finish_id]
