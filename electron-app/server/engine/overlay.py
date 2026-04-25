"""
engine/overlay.py - Base Overlay (Dual Layer) blend logic
=========================================================
Blend two spec or paint layers with noise / pattern-driven alpha.

EDIT HERE for: overlay blend behavior, zone masking, overlay scale (0.10-5.0),
and any second-base logic that does not need PATTERN_REGISTRY.

This module does NOT import shokker_engine_v2 or registries. Callers pass
noise_fn (e.g. multi_scale_noise) and pattern_mask (from _get_pattern_mask
in engine.compose).

CHANNEL SEMANTICS (spec maps):
    Channel 0 (R) = Metallic, channel 1 (G) = Roughness,
    channel 2 (B) = Clearcoat, channel 3 (A) = Specular Mask.
    Iron rules enforced after every blend: CC>=16, R>=15 (non-chrome).

COMPOSITION ORDER:
    primary spec  ->  blend_dual_base_spec(primary, secondary, alpha) -> blended
    Iron-rule clamp is applied to the blended result before uint8 conversion.

PERFORMANCE NOTES:
    - alpha shape (H, W) is broadcast through (H, W, 1) for fused blend math.
    - Spec inputs are uint8; we work in float32 only for the blend itself
      to avoid wrap-around at clip boundaries.
    - Pattern-driven modes accept float32 pattern_mask in [0, 1]; values
      outside this range are clipped silently.
"""

import logging
import numpy as np
import cv2  # hoisted from per-call local imports -- cv2 is always available when this file is loaded
from typing import Optional, Tuple

logger = logging.getLogger("engine.overlay")

# ================================================================
# OVERLAY CONSTANTS
# Magic numbers documented inline so future maintainers know the why.
# ================================================================
OVERLAY_SCALE_MIN = 0.01     # Minimum overlay scale factor (avoid div by zero in noise scale calc)
OVERLAY_SCALE_MAX = 5.0      # Maximum overlay scale factor (beyond this the overlay covers everything)
OVERLAY_STRENGTH_MIN = 0.0   # Minimum overlay strength (zero -> primary only)
OVERLAY_STRENGTH_MAX = 1.0   # Maximum overlay strength (one -> secondary only at 100%)
OVERLAY_NOISE_SCALE_MIN = 8  # Minimum noise feature size in pixels (prevents 0-division and aliasing)
FLAKE_THRESHOLD_BASE = 0.85  # Base threshold for flake probability (matches v6.1 dust scatter)
FLAKE_BLUR_KERNEL = (3, 3)   # Gaussian blur kernel for flake smoothing (3x3 = ~1px feather)
FLAKE_BLUR_SIGMA = 0.6       # Gaussian blur sigma for flake smoothing (subtle anti-alias only)

# Iron rule constants (kept local to avoid circular import with engine.core).
# Mirror of engine.core.SPEC_ROUGHNESS_MIN / SPEC_CLEARCOAT_MIN /
# SPEC_METALLIC_CHROME_THRESHOLD -- if those change, update both places.
_ROUGHNESS_FLOOR = 15.0
_CHROME_THRESH = 240.0
_CC_FLOOR = 16.0
_CHANNEL_MIN = 0.0
_CHANNEL_MAX = 255.0

# Numerical safety
_EPSILON = 1e-8

try:
    from scipy.ndimage import gaussian_filter as _scipy_gaussian_filter
    _HAS_SCIPY_GAUSSIAN = True
except ImportError:
    _HAS_SCIPY_GAUSSIAN = False


def _validate_alpha(alpha: np.ndarray, name: str = "alpha") -> np.ndarray:
    """Coerce alpha to float32 [0, 1] and scrub NaN/Inf.

    Defensive: pattern math occasionally produces non-finite values that
    propagate through compositing. Catch them at the alpha boundary.
    """
    alpha = np.asarray(alpha, dtype=np.float32)
    if not np.isfinite(alpha).all():
        logger.debug("_validate_alpha: %s contained non-finite values; sanitizing", name)
        np.nan_to_num(alpha, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(alpha, 0.0, 1.0)


# Lookup table for blend-mode normalization. O(1) lookup vs the prior chain of
# elif comparisons. Aliases map to the same canonical id.
_BLEND_MODE_ALIASES = {
    # canonical -> {aliases}
    "pattern":           {"pattern", "pattern-reactive", "pattern_reactive"},
    "pattern_vivid":     {"pattern_vivid", "pattern-vivid", "pattern-pop", "pattern_pop", "pop"},
    "tint":              {"tint", "tint-subtle", "tint_subtle", "subtle", "color-shift"},
    "dust":              {"dust", "organic", "noise", "fractal"},
    "marble":            {"marble", "swirl", "liquid"},
    "pattern_edges":     {"pattern_edges", "uniform", "pattern-edges", "edges"},
    "pattern_peaks":     {"pattern_peaks", "pattern-peaks", "peaks"},
    "pattern_contour":   {"pattern_contour", "pattern-contour", "contour"},
    "pattern_screen":    {"pattern_screen", "pattern-screen", "screen"},
    "pattern_threshold": {"pattern_threshold", "pattern-threshold", "threshold"},
}
# Inverted lookup: alias -> canonical id (built once at import).
_ALIAS_TO_CANONICAL = {alias: canonical
                       for canonical, aliases in _BLEND_MODE_ALIASES.items()
                       for alias in aliases}


def _normalize_second_base_blend_mode(mode: Optional[str]) -> str:
    """Normalize UI blend mode string to canonical engine id.

    Args:
        mode: Free-form mode string from the UI; case/dashes/underscores ignored.
            None defaults to "dust".

    Returns:
        Canonical mode id, one of: dust, marble, pattern, pattern_vivid, tint,
        pattern_edges, pattern_peaks, pattern_contour, pattern_screen,
        pattern_threshold. Unknown inputs fall back to "dust".
    """
    if mode is None:
        return "dust"
    return _ALIAS_TO_CANONICAL.get(str(mode).strip().lower(), "dust")


def _blur_2d(arr: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """2D Gaussian blur for pattern-derived alpha.

    Uses scipy.ndimage when available (better quality, separable convolution);
    falls back to a numpy-only iterative box blur otherwise.

    Args:
        arr: 2D source array.
        sigma: Gaussian standard deviation in pixels (for scipy path);
            half-width for the box blur fallback.

    Returns:
        Float32 blurred array of the same shape.
    """
    if arr is None or arr.size == 0:
        return arr
    if _HAS_SCIPY_GAUSSIAN:
        try:
            return _scipy_gaussian_filter(arr.astype(np.float64), sigma=sigma,
                                           mode="nearest").astype(np.float32)
        except Exception as e:
            logger.debug("_blur_2d: scipy gaussian failed (%s), using box-blur fallback", e)
    # Numpy fallback: separable 1D box blur (approx)
    out = np.asarray(arr, dtype=np.float32)
    k = max(2, int(round(sigma * 2)))
    for axis in (1, 0):
        for _ in range(2):
            out = (out + np.roll(out, 1, axis=axis) + np.roll(out, -1, axis=axis)) / 3.0
    return out


def get_base_overlay_alpha(shape: Tuple[int, int],
                           strength: float,
                           blend_mode: Optional[str],
                           noise_scale: int = 24,
                           seed: int = 42,
                           pattern_mask: Optional[np.ndarray] = None,
                           zone_mask: Optional[np.ndarray] = None,
                           noise_fn=None,
                           overlay_scale: float = 1.0) -> np.ndarray:
    """Compute (H, W) float32 alpha in [0, 1] for a base overlay.

    Used by both spec and paint blend pipelines. Callers apply the alpha as:
        result = primary * (1 - alpha) + secondary * alpha
    (or a screen blend for pattern_screen).

    Args:
        shape: (H, W) target shape.
        strength: Slider value in [0, 1]. Internally re-mapped per blend mode
            using a perceptual curve so low slider values remain visible.
        blend_mode: One of the canonical blend mode ids (see
            _normalize_second_base_blend_mode). Aliases accepted.
        noise_scale: Feature size in pixels for noise-driven modes (dust, marble).
        seed: Deterministic seed; same inputs -> identical alpha.
        pattern_mask: (H, W) float32 in [0, 1] for pattern-driven modes.
        zone_mask: Optional (H, W) float32 to confine the overlay to a zone.
        noise_fn: Callable (shape, scales, weights, seed) -> 2D float; required
            for dust/marble modes.
        overlay_scale: 0.01-5.0 — overall feature scaling for noise modes.

    Returns:
        Float32 (H, W) alpha array, clipped to [0, 1].

    v6.0.1: Improved slider curves so low values (5-30%) still show visible
    effect. Uses perceptual power curves instead of linear multiplication.
    """
    H, W = int(shape[0]), int(shape[1])
    if H <= 0 or W <= 0:
        logger.warning("get_base_overlay_alpha: invalid shape (%d, %d), returning zero alpha", H, W)
        return np.zeros((max(1, H), max(1, W)), dtype=np.float32)
    blend_mode = _normalize_second_base_blend_mode(blend_mode)
    # Validate strength and overlay_scale
    try:
        _s = max(OVERLAY_STRENGTH_MIN, min(OVERLAY_STRENGTH_MAX, float(strength)))
    except (TypeError, ValueError):
        logger.warning("get_base_overlay_alpha: invalid strength %r, defaulting to 0.5", strength)
        _s = 0.5
    overlay_scale = max(OVERLAY_SCALE_MIN, min(OVERLAY_SCALE_MAX, float(overlay_scale)))
    noise_scale = max(OVERLAY_NOISE_SCALE_MIN, int(noise_scale if noise_scale else 24))
    # Perceptual strength: sqrt curve so low slider values still produce visible alpha
    # strength=0.05 -> 0.22, 0.10 -> 0.32, 0.25 -> 0.50, 0.50 -> 0.71, 1.0 -> 1.0
    _ps = np.sqrt(max(0.0, _s))  # perceptual strength for modes that need it
    logger.debug("get_base_overlay_alpha: mode='%s' strength=%.3f overlay_scale=%.2f", blend_mode, _s, overlay_scale)

    if blend_mode == "dust" and noise_fn is not None:
        # FRACTAL DUST v2 — per-pixel metallic flake scatter with density variation
        # Uses 3 octaves: large density clouds + medium clusters + fine per-pixel sparkle
        scale_factor = max(OVERLAY_SCALE_MIN, float(overlay_scale))
        ens = max(OVERLAY_NOISE_SCALE_MIN, int((noise_scale / scale_factor) / 2.0))
        # Density field — where flakes cluster (medium-scale variation)
        try:
            n_density = noise_fn((H, W), [ens, ens * 2, ens * 4], [0.3, 0.4, 0.3], seed + 555)
            n_density = (n_density - n_density.min()) / (n_density.max() - n_density.min() + 1e-8)
        except Exception as e:
            logger.warning("dust blend noise_fn failed: %s, using uniform density", e)
            n_density = np.full((H, W), 0.5, dtype=np.float32)
        # Fine per-pixel sparkle — actual individual flakes
        rng = np.random.RandomState(seed + 557)
        sparkle = rng.random((H, W)).astype(np.float32)
        # Flake probability modulated by density (more flakes in dense areas)
        flake_density_range = 0.35   # How much density modulates flake threshold
        flake_threshold = FLAKE_THRESHOLD_BASE - n_density * flake_density_range  # 0.50 in dense, 0.85 in sparse
        flakes = np.where(sparkle > flake_threshold,
                          (sparkle - flake_threshold) / (1.0 - flake_threshold + _EPSILON),
                          0).astype(np.float32)
        # Tiny blur to make flakes 2px instead of single pixels (avoids single-pixel aliasing)
        try:
            flakes = cv2.GaussianBlur(flakes, FLAKE_BLUR_KERNEL, FLAKE_BLUR_SIGMA)
        except cv2.error as e:
            # Previously tried to except cv2.error with cv2 not yet imported -- latent bug fixed
            logger.warning("dust flake blur failed: %s", e)
        # Normalize and apply strength
        fmax = float(flakes.max())
        if fmax > 1e-8:
            flakes /= fmax
        dust_strength_multiplier = 2.0    # How much strength amplifies dust
        dust_strength_offset = 0.15       # Minimum visible dust even at 0% strength
        alpha = np.clip(flakes * (_s * dust_strength_multiplier + dust_strength_offset), 0, 1).astype(np.float32)
        if pattern_mask is not None:
            alpha = np.clip(alpha * pattern_mask, 0, 1).astype(np.float32)

    elif blend_mode == "marble" and noise_fn is not None:
        # LIQUID MARBLE v2 — multi-octave domain-warped veining with organic flow
        # 3 warp fields + 3 vein frequencies for realistic marble/liquid metal
        scale_factor = max(0.01, float(overlay_scale))
        ens = max(8, int((noise_scale / scale_factor) * 1.2))
        warp1 = noise_fn((H, W), [ens, ens * 2, ens * 4], [0.3, 0.4, 0.3], seed + 888)
        warp2 = noise_fn((H, W), [ens, ens * 2, ens * 4], [0.3, 0.4, 0.3], seed + 889)
        warp3 = noise_fn((H, W), [ens * 2, ens * 4], [0.5, 0.5], seed + 890)
        y, x = np.mgrid[0:H, 0:W]
        yf = y.astype(np.float32) / max(1, ens)
        xf = x.astype(np.float32) / max(1, ens)
        # 3 vein frequencies with cross-warp for organic look
        coord1 = yf + warp1 * 8.0 + warp3 * 3.0
        coord2 = xf * 0.7 + yf * 0.3 + warp2 * 8.0
        coord3 = (xf + yf) * 0.5 + warp1 * 4.0 + warp2 * 4.0
        vein1 = 1.0 - np.abs(np.sin(coord1 * np.pi))  # Bright veins on dark
        vein2 = 1.0 - np.abs(np.sin(coord2 * np.pi * 1.3))
        vein3 = 1.0 - np.abs(np.sin(coord3 * np.pi * 0.7))
        # Layer veins: thin primary + medium secondary + broad tertiary
        marble = np.clip(vein1 ** 2.0 * 0.5 + vein2 ** 1.5 * 0.3 + vein3 * 0.2, 0, 1)
        # Stretch contrast
        mn, mx = float(marble.min()), float(marble.max())
        if mx > mn: marble = (marble - mn) / (mx - mn)
        alpha = np.clip(marble * (_s * 2.2 + 0.12), 0, 1).astype(np.float32)
        if pattern_mask is not None:
            alpha = np.clip(alpha * pattern_mask, 0, 1).astype(np.float32)

    elif blend_mode == "pattern" and pattern_mask is not None:
        # Perceptual: at 5% strength you still see a hint
        alpha = np.clip(pattern_mask * _ps, 0, 1).astype(np.float32)

    elif blend_mode == "tint" and pattern_mask is not None:
        # TINT v2 with pattern: color influence shaped by pattern, with perceptual curve
        # At low strength (5-20%), gives subtle color wash following pattern contours
        # At high strength (60-100%), strong color override following pattern density
        # Uses sqrt for low end, linear for high end — smooth ramp
        tint_strength = _ps * 0.6 if _s < 0.4 else _s * 0.7
        alpha = np.clip(pattern_mask * tint_strength, 0, 1).astype(np.float32)

    elif blend_mode == "tint" and pattern_mask is None:
        # TINT v2 without pattern: uniform color wash over entire zone
        # Perceptual curve: 10% feels like 10%, not invisible
        # Uses cubic ease for natural color influence feel
        tint_val = _s * _s * (3.0 - 2.0 * _s)  # smoothstep: 0→0, 0.5→0.5, 1→1
        alpha = np.full((H, W), tint_val * 0.75, dtype=np.float32)  # cap at 75% max to never fully replace

    elif blend_mode == "pattern_vivid" and pattern_mask is not None:
        # Pattern-Pop: at low strength, use soft blend instead of hard threshold
        # Smooth transition: low strength = gentle overlay, high strength = hard cutoff
        if _s < 0.5:
            # Soft mode: multiply pattern by boosted strength (visible even at 5%)
            alpha = np.clip(pattern_mask * _ps * 1.5, 0, 1).astype(np.float32)
        else:
            # Hard mode: threshold-based cutoff with softer edge width at mid-range
            threshold = np.clip(1.0 - _s, 0.0, 1.0)
            edge_width = 0.15 + (1.0 - _s) * 0.2  # wider edge at lower strength
            alpha = np.clip((pattern_mask - threshold) / max(edge_width, 1e-4), 0.0, 1.0).astype(np.float32)

    elif blend_mode == "pattern_edges":
        # PATTERN EDGES v2 — Crisp edge detection with controllable width
        if pattern_mask is not None:
            pm = pattern_mask.astype(np.float64)
            # Sobel in both directions for true edge magnitude
            gy, gx = np.gradient(pm)
            mag = np.sqrt(gx * gx + gy * gy).astype(np.float32)
            m_min, m_max = float(mag.min()), float(mag.max())
            if m_max - m_min > 1e-8:
                mag = (mag - m_min) / (m_max - m_min)
            # Adaptive threshold: at low strength, only strongest edges show
            # At high strength, more subtle edges appear
            threshold = 0.30 - _s * 0.25  # 0.30 at 0% → 0.05 at 100%
            sharpness = 6.0 + _s * 4.0  # steeper cutoff at high strength
            edges = np.clip((mag - threshold) * sharpness, 0, 1)
            # Subtle inner glow (1-2px, not blurry 3px) for anti-aliasing only
            if _s > 0.3:
                edges_aa = _blur_2d(edges, sigma=1.0)
                edges = np.clip(edges * 0.8 + edges_aa * 0.2, 0, 1)
            alpha = np.clip(edges * (_s * 2.0 + 0.2), 0, 1).astype(np.float32)
        else:
            alpha = np.full((H, W), _ps, dtype=np.float32)

    elif blend_mode == "pattern_peaks" and pattern_mask is not None:
        # PATTERN PEAKS v2 — unsharp mask peak isolation
        # Subtracts blurred from original to isolate high-frequency detail (peaks + ridges)
        pm = pattern_mask.astype(np.float32)
        # Two-scale peak detection: fine detail + medium structure
        _fine_sigma = max(1.5, min(H, W) / 512.0)   # ~4px at 2048
        _med_sigma = max(4.0, min(H, W) / 128.0)     # ~16px at 2048
        blur_fine = _blur_2d(pm, sigma=_fine_sigma)
        blur_med = _blur_2d(pm, sigma=_med_sigma)
        # Fine peaks (sharp detail) + medium peaks (broader ridges)
        peaks_fine = np.abs(pm - blur_fine)
        peaks_med = np.abs(pm - blur_med)
        features = peaks_fine * 0.6 + peaks_med * 0.4
        # Normalize to full range
        f_max = float(features.max())
        if f_max > 1e-8:
            features /= f_max
        # Power curve for contrast: makes peaks POP
        features = np.power(features, 0.7)
        alpha = np.clip(features * (_s * 2.5 + 0.2), 0, 1).astype(np.float32)

    elif blend_mode == "pattern_contour" and pattern_mask is not None:
        # PATTERN CONTOUR v2 — crisp topographic iso-lines with consistent pixel-width
        pm_f = pattern_mask.astype(np.float32)
        n_contours = max(4, int(6 + _s * 14))  # 6-20 contour lines
        # Scale pattern to n_contours levels, detect transitions between levels
        scaled = pm_f * n_contours
        # Distance to nearest integer = distance to nearest contour line
        frac = scaled - np.floor(scaled)
        dist_to_line = np.minimum(frac, 1.0 - frac)
        # Line width in pattern-space: ~1-2 pixels worth at current resolution
        line_width = 0.04 + (1.0 - _s) * 0.04  # 0.04 at high strength, 0.08 at low
        contours = np.clip(1.0 - dist_to_line / line_width, 0, 1)
        # Anti-alias: slight blur for smooth line edges
        contours = _blur_2d(contours, sigma=0.5) if min(H, W) >= 512 else contours
        alpha = np.clip(contours * (_s * 1.8 + 0.25), 0, 1).astype(np.float32)

    elif blend_mode == "pattern_screen" and pattern_mask is not None:
        # PATTERN SCREEN v2 — Photoshop-style screen blend via pattern
        # Screen = 1-(1-A)(1-B). At low strength, lightens where pattern is bright.
        # At high strength, dramatic lightening effect that preserves dark pattern areas.
        pm_f = pattern_mask.astype(np.float32)
        # Adaptive contrast: stretch pattern to use more of the 0-1 range
        p5 = np.percentile(pm_f, 5)
        p95 = np.percentile(pm_f, 95)
        if p95 - p5 > 0.05:
            pm_f = np.clip((pm_f - p5) / (p95 - p5), 0, 1)
        # Screen alpha: pattern brightness × strength with perceptual curve
        alpha = np.clip(pm_f * (_s * 1.6 + 0.15), 0, 1).astype(np.float32)

    elif blend_mode == "pattern_threshold" and pattern_mask is not None:
        # PATTERN THRESHOLD v2 — crisp binary mask from pattern with adjustable cutoff
        # Low strength = only brightest pattern areas (highlights). High = most of pattern.
        pm_f = pattern_mask.astype(np.float32)
        # Threshold slides from 0.95 (strength=0, almost nothing passes) to 0.05 (strength=1, almost everything)
        threshold = 0.95 - _s * 0.90
        # Edge width: very sharp at high strength (poster effect), softer at low (feathered highlights)
        edge = 0.02 + (1.0 - _s) * 0.08
        alpha = np.clip((pm_f - threshold) / max(edge, 1e-4), 0, 1).astype(np.float32)

    else:
        # Default fallback: linear strength (15% = 15% blend, not sqrt-boosted)
        alpha = np.full((H, W), _s, dtype=np.float32)

    if zone_mask is not None and zone_mask.shape[:2] == (H, W):
        # In-place multiply where possible to avoid an extra full-canvas alloc
        zm = np.clip(zone_mask.astype(np.float32, copy=False), 0, 1)
        alpha = alpha * zm
    # Final NaN/Inf scrub: pattern modes occasionally emit non-finite alpha
    return _validate_alpha(alpha, name=blend_mode)


def _screen_uint8(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    """Photoshop-style screen blend for uint8 spec maps.

    Formula: ``out = 1 - (1 - a/255)(1 - b/255)`` simplified to
    ``a + b - a*b/255``. Faster than the explicit (1-x)(1-y) form and
    gives identical 8-bit output.

    Args:
        primary: (H, W, ...) uint8 array.
        secondary: (H, W, ...) uint8 array of matching shape.

    Returns:
        uint8 array of the same shape as the inputs.
    """
    p = primary.astype(np.float32)
    s = secondary.astype(np.float32)
    return np.clip(p + s - p * s / 255.0, 0, 255).astype(np.uint8)


def blend_dual_base_spec(spec_primary: np.ndarray,
                         spec_secondary: np.ndarray,
                         strength: float,
                         blend_mode: str = "dust",
                         noise_scale: int = 24,
                         seed: int = 42,
                         pattern_mask: Optional[np.ndarray] = None,
                         zone_mask: Optional[np.ndarray] = None,
                         noise_fn=None,
                         overlay_scale: float = 1.0
                         ) -> Tuple[np.ndarray, np.ndarray]:
    """Blend two spec maps to create a dual-material surface.

    Args:
        spec_primary:   (H, W, 4) uint8 - the primary base spec (M, R, CC, A).
        spec_secondary: (H, W, 4) uint8 - the overlay base spec.
        strength:       0.0-1.0 - global blend amount.
        blend_mode:     UI mode string (normalized internally). One of
            dust, marble, pattern, pattern_vivid, tint, pattern_edges,
            pattern_peaks, pattern_contour, pattern_screen, pattern_threshold.
        noise_scale:    Feature size in pixels for noise modes.
        seed:           Deterministic seed.
        pattern_mask:   (H, W) float32 in [0, 1] for pattern-driven modes.
        zone_mask:      (H, W) float32 optional zone confinement mask.
        noise_fn:       Required for dust/marble; ignored otherwise.
        overlay_scale:  0.01-5.0 overall feature scaling.

    Returns:
        (blended_spec, alpha) where blended_spec is (H, W, 4) uint8 with iron
        rules enforced (CC>=16, R>=15 non-chrome) and alpha is the (H, W)
        float32 mix mask actually used.

    On error returns (primary copy, zero alpha) so the parent render does not
    abort.
    """
    try:
        if spec_primary is None or spec_primary.size == 0:
            raise ValueError("blend_dual_base_spec: spec_primary is empty/None")
        if spec_secondary is None or spec_secondary.size == 0:
            raise ValueError("blend_dual_base_spec: spec_secondary is empty/None")
        H, W = spec_primary.shape[:2]
        # Validate inputs -- ensure both specs have matching dimensions
        if spec_secondary.shape[:2] != (H, W):
            logger.warning("blend_dual_base_spec: shape mismatch primary=%s secondary=%s, resizing",
                           spec_primary.shape, spec_secondary.shape)
            # cv2 hoisted to module scope -- no per-call import overhead
            spec_secondary = cv2.resize(spec_secondary, (W, H), interpolation=cv2.INTER_NEAREST)
        bm = _normalize_second_base_blend_mode(blend_mode)
        strength = max(OVERLAY_STRENGTH_MIN, min(OVERLAY_STRENGTH_MAX, float(strength)))

        alpha = get_base_overlay_alpha(
            (H, W), strength, blend_mode,
            noise_scale=noise_scale, seed=seed,
            pattern_mask=pattern_mask, zone_mask=zone_mask,
            noise_fn=noise_fn, overlay_scale=overlay_scale
        )

        alpha4 = alpha[:, :, np.newaxis]
        # Pre-allocate result as float32 and blend in-place to avoid extra allocations
        result = spec_primary.astype(np.float32)
        inv_alpha4 = 1.0 - alpha4
        if bm == "pattern_screen":
            # Screen blend: a + b - a*b/255 (integer math avoids float conversion of secondary)
            p = result
            s = spec_secondary.astype(np.float32)
            screened = np.clip(p + s - p * s / 255.0, 0, _CHANNEL_MAX)
            result *= inv_alpha4
            result += screened * alpha4
        else:
            ss = spec_secondary.astype(np.float32)
            result *= inv_alpha4
            result += ss * alpha4
        # Enforce PBR floors on blended spec in-place using local constants.
        # CC floor: every CC>0 pixel must be at least the clearcoat minimum.
        np.maximum(result[:, :, 2], _CC_FLOOR, out=result[:, :, 2])
        non_chrome = result[:, :, 0] < _CHROME_THRESH
        r_chan = result[:, :, 1]
        # Use boolean indexing -- O(N) on the masked subset, no full-array temp
        r_chan[non_chrome] = np.maximum(r_chan[non_chrome], _ROUGHNESS_FLOOR)
        return np.clip(result, _CHANNEL_MIN, _CHANNEL_MAX).astype(np.uint8), alpha
    except Exception as e:
        logger.error("blend_dual_base_spec failed (mode=%s, shape=%s): %s",
                     blend_mode, getattr(spec_primary, "shape", "?"), e)
        return (spec_primary.copy() if spec_primary is not None else np.zeros((1, 1, 4), dtype=np.uint8),
                np.zeros((spec_primary.shape[0], spec_primary.shape[1]), dtype=np.float32)
                if spec_primary is not None else np.zeros((1, 1), dtype=np.float32))


def blend_dual_base_paint(paint_primary: np.ndarray,
                          paint_secondary: np.ndarray,
                          alpha_map: np.ndarray) -> np.ndarray:
    """Blend two paint layers with a shared alpha field (linear over operator).

    Args:
        paint_primary:   (H, W, 3-4) float32 in [0, 1].
        paint_secondary: (H, W, 3-4) float32 in [0, 1].
        alpha_map:       (H, W) float32 in [0, 1].

    Returns:
        (H, W, 3-4) float32 blended paint. If primary has more channels than
        secondary (e.g. an alpha channel), the extras are preserved unchanged.

    Notes:
        Paint is treated as straight (NOT premultiplied) alpha. The standard
        over operator is applied to the matched RGB channels only.
    """
    try:
        if paint_primary is None or paint_primary.size == 0:
            raise ValueError("blend_dual_base_paint: paint_primary is empty/None")
        if paint_secondary is None or paint_secondary.size == 0:
            raise ValueError("blend_dual_base_paint: paint_secondary is empty/None")
        # Validate alpha_map range -- use in-place clip
        alpha = _validate_alpha(alpha_map, name="paint-alpha")
        alpha4 = alpha[:, :, np.newaxis]
        # Ensure matching channel count
        p_ch = paint_primary.shape[2] if paint_primary.ndim == 3 else 3
        s_ch = paint_secondary.shape[2] if paint_secondary.ndim == 3 else 3
        min_ch = min(p_ch, s_ch)
        if min_ch < 3:
            raise ValueError(f"blend_dual_base_paint: at least 3 channels required (got primary={p_ch}, secondary={s_ch})")
        # In-place blend: result = primary * (1-alpha) + secondary * alpha
        inv_alpha4 = 1.0 - alpha4
        result = paint_primary[:, :, :min_ch] * inv_alpha4
        result += paint_secondary[:, :, :min_ch] * alpha4
        np.clip(result, 0.0, 1.0, out=result)
        # Preserve any extra channels from primary (e.g., alpha)
        if p_ch > min_ch:
            # Pre-allocate full array instead of concatenate
            full = np.empty((paint_primary.shape[0], paint_primary.shape[1], p_ch),
                            dtype=np.float32)
            full[:, :, :min_ch] = result
            full[:, :, min_ch:] = paint_primary[:, :, min_ch:]
            return full
        return result.astype(np.float32, copy=False)
    except Exception as e:
        logger.error("blend_dual_base_paint failed (primary shape=%s, secondary shape=%s): %s",
                     getattr(paint_primary, "shape", "?"),
                     getattr(paint_secondary, "shape", "?"), e)
        return paint_primary.copy() if paint_primary is not None else np.zeros((1, 1, 3), dtype=np.float32)
