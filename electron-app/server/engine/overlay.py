"""
engine/overlay.py - Base Overlay (Dual Layer) blend logic
=========================================================
Blend two spec or paint layers with noise / pattern-driven alpha.

EDIT HERE for: overlay blend behavior, zone masking, overlay scale (0.10–5.0),
and any second-base logic that does not need PATTERN_REGISTRY.

This module does NOT import shokker_engine_v2 or registries. Callers pass
noise_fn (e.g. multi_scale_noise) and pattern_mask (from _get_pattern_mask in engine).
"""

import numpy as np


def _normalize_second_base_blend_mode(mode):
    """Normalize UI blend mode to engine internal id. Supports 10 modes including pattern_edges, pattern_peaks, pattern_contour, pattern_screen, pattern_threshold."""
    if mode is None:
        return "dust"
    m = str(mode).strip().lower()
    if m in ("pattern-reactive", "pattern_reactive", "pattern"):
        return "pattern"
    if m in ("pattern-vivid", "pattern_vivid", "pattern-pop", "pattern_pop", "pop"):
        return "pattern_vivid"
    if m in ("tint", "tint-subtle", "tint_subtle", "subtle", "color-shift"):
        return "tint"
    if m in ("organic", "noise", "dust", "fractal"):
        return "dust"
    if m in ("marble", "swirl", "liquid"):
        return "marble"
    if m in ("uniform", "pattern-edges", "pattern_edges", "edges"):
        return "pattern_edges"
    if m in ("pattern-peaks", "pattern_peaks", "peaks"):
        return "pattern_peaks"
    if m in ("pattern-contour", "pattern_contour", "contour"):
        return "pattern_contour"
    if m in ("pattern-screen", "pattern_screen", "screen"):
        return "pattern_screen"
    if m in ("pattern-threshold", "pattern_threshold", "threshold"):
        return "pattern_threshold"
    return "dust"


def _blur_2d(arr, sigma=2.0):
    """Simple 2D blur for pattern-derived alpha. Uses scipy if available, else separable box blur with numpy."""
    try:
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(arr.astype(np.float64), sigma=sigma, mode="nearest").astype(np.float32)
    except Exception:
        pass
    # Numpy fallback: separable 1D box blur (approx)
    out = np.asarray(arr, dtype=np.float32)
    k = max(2, int(round(sigma * 2)))
    for axis in (1, 0):
        for _ in range(2):
            out = (out + np.roll(out, 1, axis=axis) + np.roll(out, -1, axis=axis)) / 3.0
    return out


def get_base_overlay_alpha(shape, strength, blend_mode, noise_scale=24, seed=42,
                            pattern_mask=None, zone_mask=None, noise_fn=None,
                            overlay_scale=1.0):
    """Compute (H,W) float32 alpha 0-1 for base overlay. Used by both spec and paint blend.
    Callers apply: result = primary * (1 - alpha) + secondary * alpha (or screen blend for pattern_screen).

    v6.0.1: Improved slider curves so low values (5-30%) still show visible effect.
    Uses perceptual power curves instead of linear multiplication for smoother falloff.
    """
    H, W = shape[0], shape[1]
    blend_mode = _normalize_second_base_blend_mode(blend_mode)
    # Perceptual strength: sqrt curve so low slider values still produce visible alpha
    # strength=0.05 → 0.22, 0.10 → 0.32, 0.25 → 0.50, 0.50 → 0.71, 1.0 → 1.0
    _s = float(strength)
    _ps = np.sqrt(max(0.0, _s))  # perceptual strength for modes that need it

    if blend_mode == "dust" and noise_fn is not None:
        scale_factor = max(0.01, float(overlay_scale))
        effective_noise_scale = max(2, int((noise_scale / scale_factor) / 3.0))
        noise = noise_fn(
            (H, W),
            [effective_noise_scale, max(1, effective_noise_scale // 2)],
            [0.7, 0.3],
            seed + 555
        )
        n_min, n_max = float(noise.min()), float(noise.max())
        noise = (noise - n_min) / (n_max - n_min + 1e-8)
        # Gentler power curve: at low strength still keep some noise visible
        power_val = 3.0 - (_s * 2.0)
        noise = np.power(noise, max(1.0, power_val))
        alpha = np.clip(noise * _ps * 1.8, 0, 1).astype(np.float32)
        if pattern_mask is not None:
            alpha = np.clip(alpha * pattern_mask, 0, 1).astype(np.float32)

    elif blend_mode == "marble" and noise_fn is not None:
        scale_factor = max(0.01, float(overlay_scale))
        effective_noise_scale = max(4, int((noise_scale / scale_factor) * 1.5))
        noise = noise_fn(
            (H, W),
            [effective_noise_scale, effective_noise_scale * 2, max(2, effective_noise_scale // 2)],
            [0.6, 0.3, 0.1],
            seed + 888
        )
        n_min, n_max = float(noise.min()), float(noise.max())
        noise = (noise - n_min) / (n_max - n_min + 1e-8)
        y, x = np.mgrid[0:H, 0:W]
        base_coord = (y + x) / max(1, effective_noise_scale)
        warped_coord = base_coord + noise * 6.0
        marble = np.power(np.abs(np.sin(warped_coord * np.pi)), 1.5)
        alpha = np.clip(marble * _ps * 1.5, 0, 1).astype(np.float32)
        if pattern_mask is not None:
            alpha = np.clip(alpha * pattern_mask, 0, 1).astype(np.float32)

    elif blend_mode == "pattern" and pattern_mask is not None:
        # Perceptual: at 5% strength you still see a hint
        alpha = np.clip(pattern_mask * _ps, 0, 1).astype(np.float32)

    elif blend_mode == "tint" and pattern_mask is not None:
        # Tint is intentionally subtle — but use sqrt curve for low-end visibility
        alpha = np.clip(pattern_mask * _ps * 0.45, 0, 1).astype(np.float32)

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
        if pattern_mask is not None:
            gy, gx = np.gradient(pattern_mask.astype(np.float64))
            mag = np.sqrt(gx * gx + gy * gy).astype(np.float32)
            m_min, m_max = float(mag.min()), float(mag.max())
            if m_max - m_min > 1e-8:
                mag = (mag - m_min) / (m_max - m_min)
            alpha = np.clip(mag * _ps * 1.5, 0, 1).astype(np.float32)
        else:
            alpha = np.full((H, W), _ps, dtype=np.float32)

    elif blend_mode == "pattern_peaks" and pattern_mask is not None:
        blurred = _blur_2d(pattern_mask, sigma=2.5)
        peaks = np.clip(pattern_mask.astype(np.float32) - blurred, 0, 1)
        p_min, p_max = float(peaks.min()), float(peaks.max())
        if p_max - p_min > 1e-8:
            peaks = (peaks - p_min) / (p_max - p_min)
        alpha = np.clip(peaks * _ps * 2.0, 0, 1).astype(np.float32)

    elif blend_mode == "pattern_contour" and pattern_mask is not None:
        # Iso-band: width scales with strength so low values show wider band
        center = np.clip(_s, 0.0, 1.0)
        width = 0.08 + (1.0 - _s) * 0.15  # wider band at low strength
        dist = np.abs(pattern_mask.astype(np.float32) - center)
        alpha = np.clip(1.0 - np.clip((dist - width * 0.5) / max(width * 0.5, 1e-4), 0, 1), 0, 1).astype(np.float32)
        alpha = np.clip(alpha * _ps * 1.8, 0, 1).astype(np.float32)

    elif blend_mode == "pattern_screen" and pattern_mask is not None:
        alpha = np.clip(pattern_mask * _ps, 0, 1).astype(np.float32)

    elif blend_mode == "pattern_threshold" and pattern_mask is not None:
        # Overlay in darks and lights; base in midtones. strength widens the midtone band.
        mid = 0.5
        band = np.clip(_s, 0.0, 1.0) * 0.5
        low, high = mid - band, mid + band
        in_low = np.clip((low - pattern_mask.astype(np.float32)) / max(0.08, 1e-4), 0, 1)
        in_high = np.clip((pattern_mask.astype(np.float32) - high) / max(0.08, 1e-4), 0, 1)
        alpha = np.clip(np.maximum(in_low, in_high) * _ps, 0, 1).astype(np.float32)

    else:
        alpha = np.full((H, W), _ps, dtype=np.float32)

    if zone_mask is not None and zone_mask.shape[:2] == (H, W):
        alpha = alpha * np.clip(zone_mask.astype(np.float32), 0, 1)
    return alpha


def _screen_uint8(primary, secondary):
    """Screen blend for uint8 spec maps: 1 - (1-a/255)(1-b/255) -> a + b - a*b/255."""
    p = primary.astype(np.float32)
    s = secondary.astype(np.float32)
    return np.clip(p + s - p * s / 255.0, 0, 255).astype(np.uint8)


def blend_dual_base_spec(spec_primary, spec_secondary, strength,
                         blend_mode="dust", noise_scale=24, seed=42,
                         pattern_mask=None, zone_mask=None, noise_fn=None,
                         overlay_scale=1.0):
    """Blend two spec maps to create a dual-material surface.

    spec_primary:   (H, W, 4) uint8 - the primary base spec
    spec_secondary: (H, W, 4) uint8 - the overlay base spec
    strength:       0.0–1.0 - global blend amount
    blend_mode:     normalized from UI (dust, marble, pattern, pattern_vivid, tint, pattern_edges, pattern_peaks, pattern_contour, pattern_screen, pattern_threshold)
    pattern_mask:   (H, W) float32 - used by all pattern-driven modes
    zone_mask:      (H, W) float32 optional - confine overlay to zone
    noise_fn:       used for dust and marble
    overlay_scale:  0.10–5.0

    Returns:        (blended_spec (H, W, 4) uint8, alpha (H, W) float32)
    """
    H, W = spec_primary.shape[:2]
    sp = spec_primary.astype(np.float32)
    ss = spec_secondary.astype(np.float32)
    bm = _normalize_second_base_blend_mode(blend_mode)

    alpha = get_base_overlay_alpha(
        (H, W), strength, blend_mode,
        noise_scale=noise_scale, seed=seed,
        pattern_mask=pattern_mask, zone_mask=zone_mask,
        noise_fn=noise_fn, overlay_scale=overlay_scale
    )

    alpha4 = alpha[:, :, np.newaxis]
    if bm == "pattern_screen":
        screened = _screen_uint8(spec_primary, spec_secondary)
        blended = sp * (1.0 - alpha4) + screened.astype(np.float32) * alpha4
    else:
        blended = sp * (1.0 - alpha4) + ss * alpha4
    return np.clip(blended, 0, 255).astype(np.uint8), alpha


def blend_dual_base_paint(paint_primary, paint_secondary, alpha_map):
    """Blend two paint layers with a shared alpha field.

    paint_primary:   (H, W, 4) float32
    paint_secondary: (H, W, 4) float32
    alpha_map:       (H, W) float32

    Returns: (H, W, 4) float32
    """
    alpha4 = np.clip(alpha_map[:, :, np.newaxis], 0, 1)
    return paint_primary * (1.0 - alpha4) + paint_secondary * alpha4
