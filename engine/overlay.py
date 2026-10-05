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
    "pattern_glow":      {"pattern_glow", "pattern-glow", "glow", "halo", "bloom"},
    "pattern_fresnel":   {"pattern_fresnel", "pattern-fresnel", "fresnel", "rim", "grazing"},
    "pattern_flow":      {"pattern_flow", "pattern-flow", "flow", "brushed", "anisotropic"},
    "pattern_shatter":   {"pattern_shatter", "pattern-shatter", "shatter", "crack", "forged", "flake"},
}
# Inverted lookup: alias -> canonical id (built once at import).
_ALIAS_TO_CANONICAL = {alias: canonical
                       for canonical, aliases in _BLEND_MODE_ALIASES.items()
                       for alias in aliases}
_PATTERN_REQUIRED_BLEND_MODES = {
    "pattern",
    "pattern_vivid",
    "pattern_edges",
    "pattern_peaks",
    "pattern_glow",
    "pattern_fresnel",
    "pattern_flow",
    "pattern_shatter",
}

# 2026-06-02 BASE-OVERLAY blend grid rethink: 3 redundant pattern modes were cut
# from the UI (pattern_screen, pattern_threshold, pattern_contour). Saved looks
# may still reference them, so the normalizer remaps the dead ids to a kept mode
# instead of falling through to "dust". screen->pattern (both follow brightness),
# threshold->pattern_vivid (both isolate highlights), contour->pattern_peaks (both
# react to pattern transitions/detail).
_REMOVED_MODE_REMAP = {
    "pattern_screen":    "pattern",
    "pattern_threshold": "pattern_vivid",
    "pattern_contour":   "pattern_peaks",
    # accept dashed / bare aliases of the removed ids too
    "pattern-screen":    "pattern",
    "pattern-threshold": "pattern_vivid",
    "pattern-contour":   "pattern_peaks",
    "screen":            "pattern",
    "threshold":         "pattern_vivid",
    "contour":           "pattern_peaks",
}


def _normalize_second_base_blend_mode(mode: Optional[str]) -> str:
    """Normalize UI blend mode string to canonical engine id.

    Args:
        mode: Free-form mode string from the UI; case/dashes/underscores ignored.
            None defaults to "dust".

    Returns:
        Canonical mode id, one of: dust, marble, pattern, pattern_vivid, tint,
        pattern_edges, pattern_peaks, pattern_glow, pattern_fresnel,
        pattern_flow, pattern_shatter. Unknown inputs fall back to "dust".

        BACKWARD-COMPAT: the 3 removed ids (pattern_screen, pattern_threshold,
        pattern_contour) are remapped to a kept mode so older saved looks render
        instead of erroring or washing out as "dust".
    """
    if mode is None:
        return "dust"
    key = str(mode).strip().lower()
    # Remap removed ids first so they survive even if their aliases were dropped.
    if key in _REMOVED_MODE_REMAP:
        return _REMOVED_MODE_REMAP[key]
    return _ALIAS_TO_CANONICAL.get(key, "dust")


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
    (a straight linear over-blend for every kept mode).

    Args:
        shape: (H, W) target shape.
        strength: Slider value in [0, 1]. This is a literal final mix amount:
            0 means primary only, 0.5 means half overlay contribution, and 1
            means full overlay contribution wherever the mode mask is active.
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

    v6.2 post-alpha: keep mode masks expressive, but make strength a linear
    contract. Older perceptual boosts made 10-20% overlays show too strongly
    and could leak overlay spec even near 0%.
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
    logger.debug("get_base_overlay_alpha: mode='%s' strength=%.3f overlay_scale=%.2f", blend_mode, _s, overlay_scale)
    if _s <= _EPSILON:
        return np.zeros((H, W), dtype=np.float32)
    # 2026-05-30 (owner bug: "solid red 2nd base overlay + hue shift does NOTHING"): pattern-reactive
    # blend modes — pattern / pattern_vivid (Pattern-Pop, the DEFAULT for a new 2nd base) / pattern_edges
    # / pattern_peaks / pattern_glow / pattern_fresnel / pattern_flow / pattern_shatter — used to RETURN
    # ZERO ALPHA here when no pattern was present, so the overlay was silently INVISIBLE and its HSB got
    # masked to nothing (the visible-result HSB mask is hard_mask * overlay_alpha → 0). Now fall THROUGH to
    # the uniform `else: alpha = np.ones` branch below (then × strength), so a pattern-mode overlay with NO
    # pattern shows as a uniform color wash (like Tint) and IS recolorable. With a pattern present each mode
    # still reacts exactly as before (those branches require pattern_mask is not None).

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
        # Normalize to a full-strength feature mask. Strength is applied once
        # at the end so Spec Strength remains an honest linear mix.
        fmax = float(flakes.max())
        if fmax > 1e-8:
            flakes /= fmax
        alpha = np.clip(flakes, 0, 1).astype(np.float32)
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
        alpha = np.clip(marble, 0, 1).astype(np.float32)
        if pattern_mask is not None:
            alpha = np.clip(alpha * pattern_mask, 0, 1).astype(np.float32)

    elif blend_mode == "pattern" and pattern_mask is not None:
        alpha = np.clip(pattern_mask, 0, 1).astype(np.float32)

    elif blend_mode == "tint" and pattern_mask is not None:
        # TINT with pattern: color influence shaped by the pattern. Strength
        # is applied once at the end as a linear mix scalar.
        alpha = np.clip(pattern_mask, 0, 1).astype(np.float32)

    elif blend_mode == "tint" and pattern_mask is None:
        # TINT v2 without pattern: uniform color wash over entire zone
        # Perceptual curve: 10% feels like 10%, not invisible
        # Uses cubic ease for natural color influence feel
        # Uniform tint should honor 100% as full replacement.
        alpha = np.ones((H, W), dtype=np.float32)

    elif blend_mode == "pattern_vivid" and pattern_mask is not None:
        # Pattern-Pop: percentile-stretch then bias alpha toward mask *highlights*.
        # Older builds used gamma 0.65 (<1), which *lifts* mid-gray toward full
        # alpha — woven / plait masks (e.g. Celtic Plait) then read as a flat
        # second-base wash instead of "ink on the bright threads / dots".
        pm = pattern_mask.astype(np.float32)
        p5 = np.percentile(pm, 5)
        p95 = np.percentile(pm, 95)
        if p95 - p5 > 0.05:
            pm = np.clip((pm - p5) / (p95 - p5), 0, 1)
        # Gamma > 1 keeps plateaus dim and concentrates tint on upper percentiles.
        alpha = np.clip(np.power(pm, 1.45), 0, 1).astype(np.float32)

    elif blend_mode == "pattern_edges" and pattern_mask is not None:
        # PATTERN EDGES v2 — Crisp edge detection with controllable width
        pm = pattern_mask.astype(np.float64)
        # Sobel in both directions for true edge magnitude
        gy, gx = np.gradient(pm)
        mag = np.sqrt(gx * gx + gy * gy).astype(np.float32)
        m_min, m_max = float(mag.min()), float(mag.max())
        if m_max - m_min > 1e-8:
            mag = (mag - m_min) / (m_max - m_min)
        # Fixed edge mask; strength only controls final blend amount.
        threshold = 0.12
        sharpness = 9.0
        edges = np.clip((mag - threshold) * sharpness, 0, 1)
        # Subtle inner glow (1-2px, not blurry 3px) for anti-aliasing only
        edges_aa = _blur_2d(edges, sigma=1.0)
        edges = np.clip(edges * 0.8 + edges_aa * 0.2, 0, 1)
        alpha = np.clip(edges, 0, 1).astype(np.float32)

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
        alpha = np.clip(features, 0, 1).astype(np.float32)

    elif blend_mode == "pattern_glow" and pattern_mask is not None:
        # PATTERN GLOW — material BLEEDS past the pattern edges via an outward
        # gaussian halo. Distinct from Pattern-Reactive (which stops at the mask)
        # and from Pattern Edges (which only inks the boundary): here the overlay
        # spec/colour spills OUTWARD into a soft bloom so the pattern looks lit /
        # backlit ("the material glows past the threads"). The pattern core stays
        # full alpha; a multi-scale blur extends a falling halo beyond the rim.
        pm = pattern_mask.astype(np.float32)
        # Stretch so the bloom keys off the real pattern highlights, not noise.
        p5 = np.percentile(pm, 5)
        p95 = np.percentile(pm, 95)
        if p95 - p5 > 0.05:
            pm = np.clip((pm - p5) / (p95 - p5), 0, 1)
        # Halo radius scales with canvas so the bleed reads at any resolution.
        _core_sigma = max(1.5, min(H, W) / 256.0)    # tight inner feather
        _halo_sigma = max(6.0, min(H, W) / 48.0)     # broad outward bloom
        halo_near = _blur_2d(pm, sigma=_core_sigma)
        halo_far = _blur_2d(pm, sigma=_halo_sigma)
        # Combine: keep the hard pattern core, then add the spreading glow that
        # reaches well past the original edge. max() guarantees the halo only
        # ADDS coverage (material bleeds out), never erodes the pattern.
        glow = np.maximum(pm, halo_near * 0.85)
        glow = np.maximum(glow, halo_far * 0.55)
        # Gentle lift so faint bloom tails remain visible without going flat.
        alpha = np.clip(np.power(glow, 0.8), 0, 1).astype(np.float32)

    elif blend_mode == "pattern_fresnel" and pattern_mask is not None:
        # PATTERN FRESNEL — grazing-rim concentration. Alpha is driven by the
        # pattern-gradient magnitude (where the surface "turns away" — i.e. the
        # pattern's slopes/rims) combined with a radial falloff from the zone
        # centre, so the overlay material concentrates at grazing angles / the
        # outer edges of the zone and thins through the flat centre. Reads like
        # a fresnel sheen riding the pattern's relief, very different from the
        # flat fills of Pattern / Pattern-Pop.
        pm = pattern_mask.astype(np.float32)
        # Pattern-relief term: gradient magnitude = the pattern's grazing slopes.
        gy, gx = np.gradient(pm.astype(np.float64))
        relief = np.sqrt(gx * gx + gy * gy).astype(np.float32)
        r_max = float(relief.max())
        if r_max > 1e-8:
            relief = relief / r_max
        relief = _blur_2d(relief, sigma=max(1.0, min(H, W) / 384.0))
        # Radial falloff: 0 at centre -> 1 at the rim (grazing angle proxy).
        yy, xx = np.mgrid[0:H, 0:W]
        cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
        rr = np.sqrt(((yy - cy) / max(cy, 1.0)) ** 2 +
                     ((xx - cx) / max(cx, 1.0)) ** 2).astype(np.float32)
        rim = np.clip(rr, 0, 1)
        rim = np.power(rim, 1.8)   # fresnel-like sharpening toward the edge
        # Material rides where pattern relief AND grazing rim coincide, but the
        # rim alone still gives a clean edge sheen on flat/no-relief patterns.
        fres = np.clip(relief * 0.65 + rim * 0.55, 0, 1)
        # Keep it pattern-aware so it never tints fully blank areas: gate softly
        # by the (stretched) pattern itself with a floor so rims survive.
        gate = np.clip(pm * 0.6 + 0.4, 0, 1)
        alpha = np.clip(fres * gate, 0, 1).astype(np.float32)

    elif blend_mode == "pattern_flow" and pattern_mask is not None:
        # PATTERN FLOW — anisotropic brushed-metal smear. Computes the pattern
        # gradient, then SMEARS the alpha ALONG the iso-lines (perpendicular to
        # the gradient) by sampling the pattern at offsets that follow the local
        # flow direction. Produces directional streaks like brushed aluminium /
        # combed flake, with the grain bending around the pattern's features.
        pm = pattern_mask.astype(np.float32)
        gy, gx = np.gradient(pm.astype(np.float64))
        gmag = np.sqrt(gx * gx + gy * gy) + 1e-6
        # Iso-line (flow) direction = gradient rotated 90deg, unit length.
        fx = (-gy / gmag).astype(np.float32)
        fy = (gx / gmag).astype(np.float32)
        yy, xx = np.mgrid[0:H, 0:W]
        # Streak length scales with canvas; longer = silkier brushed grain.
        n_taps = 9
        step = max(1.0, min(H, W) / 220.0)
        acc = np.zeros((H, W), dtype=np.float32)
        wsum = 0.0
        for t in range(-(n_taps // 2), n_taps // 2 + 1):
            w = float(np.cos((t / (n_taps / 2.0)) * (np.pi / 2.0)))  # taper ends
            sx = np.clip((xx + fx * (t * step)).round().astype(np.int64), 0, W - 1)
            sy = np.clip((yy + fy * (t * step)).round().astype(np.int64), 0, H - 1)
            acc += pm[sy, sx] * w
            wsum += w
        if wsum > 1e-6:
            acc /= wsum
        # Stretch the smeared field so the streaks read with contrast.
        mn, mx = float(acc.min()), float(acc.max())
        if mx - mn > 1e-8:
            acc = (acc - mn) / (mx - mn)
        alpha = np.clip(acc, 0, 1).astype(np.float32)

    elif blend_mode == "pattern_shatter" and pattern_mask is not None:
        # PATTERN SHATTER — cracked-glass / forged-carbon cells. Threshold the
        # pattern into discrete cells, label them, then use the distance
        # transform of the cell interiors so each cell fills toward its centre
        # while hard, dark CRACKS sit on the cell boundaries (forged-flake /
        # shattered look). cv2 is already imported at module scope.
        pm = pattern_mask.astype(np.float32)
        thr = float(np.percentile(pm, 55))
        cells = (pm > thr).astype(np.uint8)
        # Distance transform: bright toward cell interiors, ~0 at every edge.
        try:
            dist = cv2.distanceTransform(cells, cv2.DIST_L2, 3).astype(np.float32)
        except cv2.error as e:
            logger.warning("pattern_shatter distanceTransform failed: %s; using cells", e)
            dist = cells.astype(np.float32)
        d_max = float(dist.max())
        if d_max > 1e-8:
            dist /= d_max
        # Hard crack mask: pattern gradient picks the fracture lines between
        # cells; subtract so boundaries read as dark seams.
        gy, gx = np.gradient(pm.astype(np.float64))
        cracks = np.sqrt(gx * gx + gy * gy).astype(np.float32)
        c_max = float(cracks.max())
        if c_max > 1e-8:
            cracks = np.clip(cracks / c_max, 0, 1)
        # Sharpen cracks into thin hard seams.
        cracks = np.clip((cracks - 0.18) * 6.0, 0, 1)
        # Faceted fill (power curve gives a hard flake plateau) minus the seams.
        facets = np.power(np.clip(dist, 0, 1), 0.6)
        shatter = np.clip(facets - cracks * 0.85, 0, 1)
        alpha = np.clip(shatter, 0, 1).astype(np.float32)

    else:
        alpha = np.ones((H, W), dtype=np.float32)

    alpha = _validate_alpha(alpha, name=f"{blend_mode}-feature")
    alpha = np.clip(alpha * _s, 0, 1).astype(np.float32)
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
            pattern_peaks, pattern_glow, pattern_fresnel, pattern_flow,
            pattern_shatter.
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
        # Normalized id kept for logging / future per-mode branches; the blend
        # math below is uniform (linear over) for every kept mode.
        bm = _normalize_second_base_blend_mode(blend_mode)
        logger.debug("blend_dual_base_spec: mode=%s -> canonical=%s", blend_mode, bm)
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
        # All kept modes use a straight linear over-blend; the alpha shape carries
        # the mode character. (The former pattern_screen special-case was removed
        # along with that mode in the 2026-06-02 blend-grid rethink.)
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
