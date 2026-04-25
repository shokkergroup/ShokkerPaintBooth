# -*- coding: utf-8 -*-
"""Shokker Paint Booth — Ceramic & Glass Finish Family.

Six dielectric (non-metallic) bases, each with a unique physically-motivated
paint + spec pair. These materials have very different optical properties
from metals: glass transmits, ceramic scatters, enamel has depth, obsidian
absorbs.

Techniques (all distinct)
-------------------------
* ``ceramic_matte``  — Micro-facet scattering (Oren-Nayar inspired).
* ``crystal_clear``  — Snell's law refraction distortion + caustics.
* ``enamel``         — Clean baked gloss (kept simple).
* ``obsidian``       — Volcanic glass: Fresnel (Schlick) + absorption gradient.
* ``porcelain``      — Subsurface scattering via Gaussian blur chain.
* ``tempered_glass`` — Stress birefringence (photoelastic effect, HSV).

Spec Contract
-------------
Every spec function returns ``(M, R, CC)`` as ``float32`` arrays of shape
``(H, W)`` in ``[0, 255]`` satisfying the iron rules:

* ``CC >= 16`` everywhere (clearcoat presence).
* ``R >= 15`` for non-chrome (all six here are non-chrome dielectrics).
* Finite values only — NaN/Inf is clipped.

See :mod:`engine.paint_v2.finish_basic` for full spec-map channel semantics.

Performance Notes
-----------------
* ``paint_crystal_clear_v2`` and ``paint_porcelain_depth_v2`` use OpenCV
  (``cv2``) GaussianBlur on CPU — ~60-80 ms at 2048² combined.
* ``paint_tempered_glass_v2`` is the heaviest (~110 ms) due to the HSV sector
  computations and multiple ``np.where`` chains; this is accepted for the
  rare occasion tempered-glass is selected.
* All other functions are dominated by a single multi-scale FBM call (~15 ms).

Color Space
-----------
``paint`` buffers are linear-light RGB in ``[0, 1]``. Gamma is applied
downstream by the PBR renderer.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d


logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS — physical/optical parameters and iron-rule floors
# ============================================================================

# Iron-rule floors (keep in sync with engine.paint_v2.finish_basic).
CC_MIN: float = 16.0
R_MIN_NONCHROME: float = 15.0
CH_MIN: float = 0.0
CH_MAX: float = 255.0
EPS: float = 1e-6

# Physical optics constants.
GLASS_IOR: float = 1.52        # Refractive index of crown/soda-lime glass.
AIR_IOR: float = 1.0           # Refractive index of air.
FRESNEL_R0_GLASS: float = 0.04 # Schlick R0 = ((n1-n2)/(n1+n2))² for air/glass.

# Crystal-clear refraction displacement (fraction of canvas max dim).
REFRACTION_DISP_FRAC: float = 0.02

# SSS blur weights (surface → deep scatter) and radii scaling.
_SSS_WEIGHTS: Tuple[float, ...] = (0.4, 0.25, 0.2, 0.15)

# Tempered glass quench-jet count (base 8, ±5 per seed).
_TEMPERED_N_JETS_MIN: int = 8
_TEMPERED_N_JETS_RANGE: int = 6

SpecTriple = Tuple[np.ndarray, np.ndarray, np.ndarray]


# ============================================================================
# SHARED HELPERS
# ============================================================================

def _hw(shape) -> Tuple[int, int]:
    """Return integer ``(H, W)`` from a 2- or 3-tuple shape."""
    if shape is None or len(shape) < 2:
        raise ValueError(f"ceramic_glass._hw: bad shape {shape!r}")
    return int(shape[0]), int(shape[1])


def _safe_paint_copy(paint: np.ndarray) -> np.ndarray:
    """Defensive float32 3-channel paint copy (never mutates input)."""
    if paint is None:
        raise ValueError("ceramic_glass: paint buffer is None")
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
        logger.warning("ceramic_glass: bad seed %r, falling back to 0", seed)
        return 0


def _enforce_iron(M: np.ndarray, R: np.ndarray, CC: np.ndarray) -> SpecTriple:
    """Clip + apply iron rules (CC>=16, R>=15 non-chrome). All dielectrics here."""
    M = np.nan_to_num(M, nan=0.0, posinf=CH_MAX, neginf=CH_MIN)
    R = np.nan_to_num(R, nan=R_MIN_NONCHROME, posinf=CH_MAX, neginf=R_MIN_NONCHROME)
    CC = np.nan_to_num(CC, nan=CC_MIN, posinf=CH_MAX, neginf=CC_MIN)
    M = np.clip(M, CH_MIN, CH_MAX).astype(np.float32, copy=False)
    R = np.clip(R, R_MIN_NONCHROME, CH_MAX).astype(np.float32, copy=False)
    CC = np.clip(CC, CC_MIN, CH_MAX).astype(np.float32, copy=False)
    return M, R, CC


def _neutral_spec(shape, base_m: float = 0.0, base_r: float = 40.0,
                  cc: float = CC_MIN) -> SpecTriple:
    """Safe fallback spec (glossy dielectric) used on exception paths."""
    h, w = _hw(shape)
    M = np.full((h, w), float(base_m), dtype=np.float32)
    R = np.full((h, w), max(float(base_r), R_MIN_NONCHROME), dtype=np.float32)
    CC = np.full((h, w), max(float(cc), CC_MIN), dtype=np.float32)
    return M, R, CC


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # paint
    "paint_ceramic_matte_v2", "paint_crystal_clear_v2", "paint_enamel_coating_v2",
    "paint_obsidian_glass_v2", "paint_porcelain_depth_v2", "paint_tempered_glass_v2",
    # spec
    "spec_ceramic_matte", "spec_crystal_clear", "spec_enamel_coating",
    "spec_obsidian_glass", "spec_porcelain_depth", "spec_tempered_glass",
    # constants
    "GLASS_IOR", "FRESNEL_R0_GLASS", "CC_MIN", "R_MIN_NONCHROME",
]


# ============================================================================
# CERAMIC MATTE — Flat matte ceramic (no micro-facet noise in base)
# Color-safe: yes (22% desaturation blend).
# ============================================================================

def paint_ceramic_matte_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                           pm: float, bb) -> np.ndarray:
    """Ceramic matte: solid flat look, no facet or Oren-Nayar noise in base.

    Args:
        paint: RGB buffer ``(H, W, 3|4)`` in linear-light ``[0, 1]``.
        shape: Canvas shape.
        mask:  ``(H, W)`` region mask in ``[0, 1]``.
        seed:  Deterministic seed (unused for solid base).
        pm:    Paint modifier amount.
        bb:    Body-buffer scalar or array.

    Returns:
        ``float32`` ``(H, W, 3)`` buffer.
    """
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    base = paint
    gray = base.mean(axis=2, keepdims=True)
    ceramic = np.clip(base * 0.78 + gray * 0.22, 0.0, 1.0).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + ceramic * (m3 * blend),
                     0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.1 * pm * m3,
                   0.0, 1.0).astype(np.float32)


def spec_ceramic_matte(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Ceramic matte spec — dielectric, high roughness with fired-clay variation."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed)
        clay = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 60)
        M = 0.0 + clay * 4.0 * sm
        R = 120.0 + clay * 15.0 * sm
        CC = 160.0 + clay * 10.0 * sm
        return _enforce_iron(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_ceramic_matte failed: %s", exc)
        return _neutral_spec(shape, 0.0, 120.0, 160.0)


# ============================================================================
# CRYSTAL CLEAR — Snell's law refraction + caustic highlights
# Clear glass refracts what's behind it. We simulate by displacing the paint
# buffer using Snell's law angles derived from a surface curvature map.
# Caustic bright spots form where rays converge (positive Laplacian).
# Color-safe: no (adds a cool blue tint).
# ============================================================================

def paint_crystal_clear_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                           pm: float, bb) -> np.ndarray:
    """Crystal clear glass with Snell refraction distortion and caustics.

    Physics:
        Snell's law: ``n1·sin(θ1) = n2·sin(θ2)``; the refraction offset is
        proportional to the surface-curvature gradient times ``n_air/n_glass``.
        Caustics form at high positive Laplacian of the curvature field where
        rays converge.

    Performance:
        Single FBM call + vectorized numpy gradient/Laplacian + one fancy
        indexing pass for the displaced sample. ~25 ms at 2048².
    """
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    base = paint

    # Surface curvature field (glass is never perfectly flat).
    curve = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 210)

    grad_y = np.gradient(curve, axis=0)
    grad_x = np.gradient(curve, axis=1)
    n_ratio = AIR_IOR / GLASS_IOR
    disp_scale = float(max(h, w)) * REFRACTION_DISP_FRAC
    dx = (grad_x * n_ratio * disp_scale).astype(np.int32)
    dy = (grad_y * n_ratio * disp_scale).astype(np.int32)

    yy, xx = np.mgrid[0:h, 0:w]
    sy = np.clip(yy + dy, 0, h - 1)
    sx = np.clip(xx + dx, 0, w - 1)
    refracted = base[sy, sx, :]

    # Caustics: positive-Laplacian regions focus light.
    laplacian = (np.roll(curve, 1, 0) + np.roll(curve, -1, 0)
                 + np.roll(curve, 1, 1) + np.roll(curve, -1, 1) - 4.0 * curve)
    caustics = np.clip(laplacian * 15.0, 0.0, 1.0)

    # Glass tints slightly cool.
    effect = np.clip(refracted * 0.92, 0.0, 1.0)
    effect[:, :, 2] = np.clip(effect[:, :, 2] + 0.03, 0.0, 1.0)
    effect = np.clip(effect + caustics[:, :, np.newaxis] * 0.2,
                     0.0, 1.0).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + effect * (m3 * blend),
                     0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.30 * pm * m3,
                   0.0, 1.0).astype(np.float32)


def spec_crystal_clear(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Crystal-clear glass spec — zero metallic, very low roughness, moderate CC."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed)
        curve = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 210)
        M = base_m * 0.05 + curve * 3.0 * sm
        R = 5.0 + curve * 10.0 * sm
        CC = 20.0 + curve * 10.0
        return _enforce_iron(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_crystal_clear failed: %s", exc)
        return _neutral_spec(shape, 0.0, 15.0, 20.0)


# ============================================================================
# ENAMEL — Clean baked gloss (no heavy glaze simulation)
# Color-safe: yes (very subtle saturation boost).
# ============================================================================

def paint_enamel_coating_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                            pm: float, bb) -> np.ndarray:
    """Enamel: solid deep gloss, no texture or glaze variation in base."""
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    base = paint
    gray = base.mean(axis=2, keepdims=True)
    # Slight saturation boost and very subtle depth (no noise).
    deep = np.clip(base * 1.05 + gray * 0.02, 0.0, 1.0)
    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + deep * (m3 * blend),
                     0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.2 * pm * m3,
                   0.0, 1.0).astype(np.float32)


def spec_enamel_coating(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Enamel spec — dielectric, low roughness (glassy) with kiln-fired variation."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed)
        kiln = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], s + 110)
        M = base_m * 0.1 + kiln * 3.0 * sm
        R = 18.0 + kiln * 4.0 * sm
        CC = CC_MIN + kiln * 2.0 * sm
        return _enforce_iron(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_enamel_coating failed: %s", exc)
        return _neutral_spec(shape, 0.0, 18.0, CC_MIN)


# ============================================================================
# OBSIDIAN — Volcanic glass: Fresnel (Schlick) + absorption + conchoidal fracture
# Natural obsidian absorbs almost all light (like void) but has strong Fresnel
# reflections at edges thanks to its smooth glass surface. Differs from void:
# obsidian has glass specularity, not micro-texture light trapping.
# Color-safe: no (pushes toward near-black with cool Fresnel highlights).
# ============================================================================

def paint_obsidian_glass_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                            pm: float, bb) -> np.ndarray:
    """Obsidian volcanic glass with Schlick Fresnel edge reflections.

    Physics:
        Schlick approximation: ``R = R0 + (1 - R0)·(1 - cos θ)^5``. For glass
        (``n = 1.5``), ``R0 ≈ 0.04``. Absorption is modeled as
        ``exp(-(4 + noise))`` — very deep.

    Performance:
        One FBM + one edge-blur (cv2.GaussianBlur) + one FBM → ~50 ms @ 2048².
    """
    # Lazy import cv2 — optional dep on some minimal deployments.
    try:
        import cv2 as _cv2
    except ImportError as exc:
        logger.error("paint_obsidian_glass_v2 needs OpenCV: %s", exc)
        return _safe_paint_copy(paint)

    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    base = paint

    # Deep absorption — volcanic glass is nearly opaque.
    micro = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], s + 230)
    absorbed = np.exp(-(4.0 + micro * 1.0))

    gray = base.mean(axis=2, keepdims=True)
    obsidian_base = np.clip(gray * absorbed[:, :, np.newaxis] + 0.005,
                            0.0, 0.04)

    # Schlick Fresnel at edges (proxied via mask edge = mask - blurred mask).
    mask_blur = _cv2.GaussianBlur(mask.astype(np.float32), (0, 0),
                                  max(h // 32, 3))
    edge = np.clip((mask - mask_blur) * 6.0, 0.0, 1.0)
    fresnel = FRESNEL_R0_GLASS + (1.0 - FRESNEL_R0_GLASS) * np.power(edge, 2.0)

    effect = obsidian_base.copy()
    fresnel_color = np.array([0.35, 0.38, 0.42], dtype=np.float32)  # cool cast
    effect = np.clip(effect + fresnel[:, :, np.newaxis] * fresnel_color * 0.4,
                     0.0, 1.0)

    # Conchoidal fracture highlights — shell-like fracture of obsidian.
    fracture = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], s + 231)
    fracture_edge = np.clip((fracture - 0.7) * 5.0, 0.0, 1.0)
    effect = np.clip(effect + fracture_edge[:, :, np.newaxis] * 0.04,
                     0.0, 1.0).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + effect * (m3 * blend),
                     0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.15 * pm * m3,
                   0.0, 1.0).astype(np.float32)


def spec_obsidian_glass(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Obsidian spec — volcanic glass with conchoidal fracture topology.

    FIVE-HOUR SHIFT Win A3 (Animal's deferred fix from TWENTY WINS shift):
    pre-fix this returned M≈20, R≈8 + tiny micro-noise → spec_std under
    the 4.0 audit threshold → flagged SPEC_FLAT (B). Headline "ultra-deep
    glass black" base reading as flat-black paint, completely losing the
    obsidian identity.
    Now drives M and R off a high-frequency conchoidal-fracture mask with
    sharp ridge highlights along fracture edges (real obsidian breaks
    along curved planes, leaving sharp specular ridges).
    """
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed)
        # Conchoidal fracture topology (mid-frequency, 3 octaves)
        fracture = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.4, 0.2], s + 270)
        # Sharp ridge highlights along fracture edges via gradient magnitude.
        # np.gradient returns (dy, dx) along the two axes; sum the absolute
        # values to get a smooth ridge field, then sharpen.
        gy = np.abs(np.gradient(fracture, axis=0))
        gx = np.abs(np.gradient(fracture, axis=1))
        ridge = np.clip((gy + gx) * 6.0, 0, 1)
        # M lifts along ridges (higher reflectance at fracture edges).
        M = base_m + ridge * 25.0 * sm  # base_m≈20 → 20-45 along fractures
        # R inversely follows ridges (smoother in pools, rougher at edges).
        # Keep micro fracture variation so the field is never literally flat.
        R = 15.0 + (1.0 - ridge) * 18.0 * sm + fracture * 6.0 * sm  # R 15-39
        CC = CC_MIN + ridge * 4.0 * sm  # 16-20
        return _enforce_iron(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_obsidian_glass failed: %s", exc)
        return _neutral_spec(shape, 0.0, 18.0, CC_MIN)


# ============================================================================
# PORCELAIN — Subsurface scattering via blur-chain diffusion
# Porcelain's signature look is the soft glow from light scattering INSIDE
# the translucent material. We simulate SSS by progressively blurring the
# paint at increasing radii and blending. Warm tones scatter more (red
# channel boosted) because long wavelengths penetrate deeper.
# Color-safe: no (pushes toward warm cream/ivory).
# ============================================================================

def paint_porcelain_depth_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                             pm: float, bb) -> np.ndarray:
    """Porcelain with subsurface scattering via Gaussian blur-chain diffusion.

    Performance:
        Four ``cv2.GaussianBlur`` passes × 3 channels → ~80 ms at 2048².
        This is the second-slowest paint function in the module; kept this
        way because physically-correct SSS requires multiple length scales.
    """
    try:
        import cv2 as _cv2
    except ImportError as exc:
        logger.error("paint_porcelain_depth_v2 needs OpenCV: %s", exc)
        return _safe_paint_copy(paint)

    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    base = paint

    # Warm porcelain base (slight cream/ivory shift).
    gray = base.mean(axis=2, keepdims=True)
    porcelain = np.clip(base * 0.4 + gray * 0.5 + 0.08, 0.0, 1.0)
    porcelain[:, :, 0] = np.clip(porcelain[:, :, 0] + 0.03, 0.0, 1.0)  # warm
    porcelain[:, :, 2] = np.clip(porcelain[:, :, 2] - 0.02, 0.0, 1.0)  # less blue

    # Multi-scale SSS: each blur represents deeper penetration.
    sss_accum = np.zeros_like(porcelain)
    radii = [max(h // 256, 1), max(h // 128, 2), max(h // 64, 3), max(h // 32, 4)]
    for weight, radius in zip(_SSS_WEIGHTS, radii):
        blurred = np.zeros_like(porcelain)
        for c in range(3):
            blurred[:, :, c] = _cv2.GaussianBlur(
                porcelain[:, :, c].astype(np.float32), (0, 0), float(radius)
            )
        sss_accum += blurred * weight

    # Red scatters more in porcelain (long-wavelength penetration).
    sss_accum[:, :, 0] = np.clip(sss_accum[:, :, 0] * 1.08, 0.0, 1.0)

    # Surface gloss composite on top of SSS.
    surface_gloss = np.clip(porcelain * 0.3 + sss_accum * 0.7, 0.0, 1.0)

    # Fine craze pattern (very subtle on quality porcelain).
    craze = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], s + 241)
    craze_lines = np.clip((craze - 0.85) * 10.0, 0.0, 0.05)
    surface_gloss = np.clip(surface_gloss - craze_lines[:, :, np.newaxis],
                            0.0, 1.0)

    effect = surface_gloss.astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + effect * (m3 * blend),
                     0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.25 * pm * m3,
                   0.0, 1.0).astype(np.float32)


def spec_porcelain_depth(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Porcelain spec — dielectric, low-moderate roughness with glaze clearcoat."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed)
        craze = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], s + 241)
        M = base_m * 0.05 + craze * 3.0 * sm
        R = 25.0 + craze * 20.0 * sm
        CC = CC_MIN + craze * 8.0
        return _enforce_iron(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_porcelain_depth failed: %s", exc)
        return _neutral_spec(shape, 0.0, 30.0, CC_MIN)


# ============================================================================
# TEMPERED GLASS — Stress birefringence (photoelastic effect)
# Tempered glass has internal stress patterns from rapid cooling (quenching).
# Under polarization, these stresses create rainbow interference fringes —
# the "butterfly wing" pattern visible in windshields with polarized
# sunglasses. Model: N cooling-jet stress centers, each producing a damped
# sinusoidal ring pattern; the combined stress field drives an HSV hue for
# Michel-Levy-chart interference colors.
# Color-safe: no (overrides base with glass palette + rainbow fringes).
# Performance: vectorized HSV sector math + N-jet accumulator (~110 ms @ 2048²).
# ============================================================================

def paint_tempered_glass_v2(paint: np.ndarray, shape, mask: np.ndarray, seed,
                            pm: float, bb) -> np.ndarray:
    """Tempered glass with stress birefringence fringes from quenching jets."""
    paint = _safe_paint_copy(paint)
    bb_arr = ensure_bb_2d(bb, shape)
    h, w = _hw(shape)
    s = _safe_seed(seed)
    base = paint
    y, x = get_mgrid((h, w))
    yn = y / max(h - 1, 1)
    xn = x / max(w - 1, 1)

    # Multi-jet quench stress field.
    rng = np.random.RandomState(s + 250)
    stress = np.zeros((h, w), dtype=np.float32)
    n_jets = _TEMPERED_N_JETS_MIN + (s % _TEMPERED_N_JETS_RANGE)
    for _ in range(n_jets):
        cy, cx = rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)
        dist = np.sqrt((yn - cy) ** 2 + (xn - cx) ** 2)
        freq = rng.uniform(15.0, 30.0)
        stress += np.sin(dist * freq) * np.exp(-dist * 3.0)

    # Normalize to 0-1 with EPS guard for degenerate fields.
    stress = (stress - stress.min()) / (stress.max() - stress.min() + EPS)

    # Michel-Levy mapping: stress → hue.
    hue = stress * 2.0 * np.pi
    sat = np.clip(stress * 0.5, 0.0, 0.35)

    # HSV → RGB via sector decomposition (vectorized).
    sixth = np.pi / 3.0
    h_idx = (hue / sixth).astype(np.int32) % 6
    f_val = (hue / sixth) - np.floor(hue / sixth)
    v_val = np.full_like(stress, 0.9)  # bright glass
    p_val = v_val * (1.0 - sat)
    q_val = v_val * (1.0 - sat * f_val)
    t_val = v_val * (1.0 - sat * (1.0 - f_val))

    bire_r = np.where(h_idx == 0, v_val,
              np.where(h_idx == 1, q_val,
              np.where(h_idx == 2, p_val,
              np.where(h_idx == 3, p_val,
              np.where(h_idx == 4, t_val, v_val)))))
    bire_g = np.where(h_idx == 0, t_val,
              np.where(h_idx == 1, v_val,
              np.where(h_idx == 2, v_val,
              np.where(h_idx == 3, q_val,
              np.where(h_idx == 4, p_val, p_val)))))
    bire_b = np.where(h_idx == 0, p_val,
              np.where(h_idx == 1, p_val,
              np.where(h_idx == 2, t_val,
              np.where(h_idx == 3, v_val,
              np.where(h_idx == 4, v_val, q_val)))))

    gray = base.mean(axis=2, keepdims=True)
    glass_base = np.clip(gray * 0.85 + 0.08, 0.0, 1.0)
    bire = np.stack([bire_r, bire_g, bire_b], axis=-1).astype(np.float32)
    effect = np.clip(glass_base * 0.7 + bire * 0.3, 0.0, 1.0).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    m3 = mask[:, :, np.newaxis]
    result = np.clip(base * (1.0 - m3 * blend) + effect * (m3 * blend),
                     0.0, 1.0)
    return np.clip(result + bb_arr[:, :, np.newaxis] * 0.25 * pm * m3,
                   0.0, 1.0).astype(np.float32)


def spec_tempered_glass(shape, seed, sm: float, base_m: float, base_r: float) -> SpecTriple:
    """Tempered glass spec — dielectric, very low roughness, glass surface CC."""
    try:
        h, w = _hw(shape)
        s = _safe_seed(seed)
        stress = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], s + 250)
        M = base_m * 0.05 + stress * 3.0 * sm
        R = 4.0 + stress * 8.0 * sm
        CC = 20.0 + stress * 10.0
        return _enforce_iron(M, R, CC)
    except Exception as exc:  # noqa: BLE001
        logger.error("spec_tempered_glass failed: %s", exc)
        return _neutral_spec(shape, 0.0, 15.0, 20.0)
