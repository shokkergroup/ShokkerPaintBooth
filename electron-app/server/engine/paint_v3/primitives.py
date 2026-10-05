"""
paint_v3.primitives — structural-motif library + spec/paint composers.

SPB-107 (Paradigm retool, owner mandate 2026-05-18 "make finishes MATCH
what they say they do/look like. UNIQUE, no duplicate patterns/functions").

Distilled from the 5 M7 keepers (p_coronal 86.1, p_non_euclidean 85.2,
p_seismic 79.4, p_time_reversed 79.0, p_geomagnetic 78.4) in
engine/paint_v2/paradigm_scifi.py. Common DNA across all 5:

  • Each defines a STRUCTURAL MOTIF — arcs, faultlines, hyperbolic tiles,
    crystal growth fronts, aurora curtains — not raw multi-octave noise.
  • M/R/CC fields composed by binary-or-near-binary thresholding on the
    motif, with multi_scale_noise modulation for fine detail.
  • Sharp high-state vs low-state separation in M (typically 200+ vs <50)
    and inverse R (15 vs 150+) and CC (16 vs 80+).
  • Every spec_fn applies `sm` amplitude scale and floors CC at 16
    (iRacing PBR clearcoat minimum, see SPEC_MAP_REFERENCE.md).

This module's contract:

  MOTIFS (each returns a (h,w) float32 field in [0, 1], structural pattern):
    motif_thermal_hotspots — radial heat blobs (blackbody, ember)
    motif_fissure_network  — cracked vein network (ember, seismic siblings)
    motif_liquid_pool      — caustic ripples + concentric pool (mercury_pool)
    motif_flow_curl        — curl-noise flow lines (living_chrome)
    motif_spiral_lens      — spacetime spiral lensing (wormhole)

  MODULATORS:
    fine_grain(shape, seed)            — pixel-level texture (16-px noise)
    dithered_threshold(field, t, jit)  — sharp binary mask with jittered edge
    radial_gauss(shape, cx, cy, sigma) — single gaussian falloff

  COMPOSERS:
    compose_spec(motif, **mr_cc_params, sm, mask) -> (h,w,4) uint8 spec map
    compose_paint(paint_in, motif, palette_lut, **params) -> (h,w,3) float32

  PALETTE:
    palette_lut(hsv_stops, n=256) -> (n,3) float32 RGB lookup table

Cache discipline: motif fields are seed-keyed and cached at 1024² then
upsampled. Matches the _ps_noise pattern in paint_v2/paradigm_scifi.py.
"""
from __future__ import annotations

import colorsys
import numpy as np

from engine.core import multi_scale_noise, get_mgrid, _resize_array


# ---------------------------------------------------------------------------
# Field cache — match the paint_v2 _ps_noise cache discipline
# ---------------------------------------------------------------------------

_V3_FIELD_CACHE: dict = {}


def _cache_get(key):
    return _V3_FIELD_CACHE.get(key)


def _cache_put(key, value):
    if len(_V3_FIELD_CACHE) > 128:
        _V3_FIELD_CACHE.clear()
    _V3_FIELD_CACHE[key] = value
    return value


def _shape_hw(shape):
    return shape[:2] if len(shape) > 2 else shape


# ---------------------------------------------------------------------------
# Modulators
# ---------------------------------------------------------------------------

def fine_grain(shape, seed: int, freqs=(16, 32), weights=(0.6, 0.4)) -> np.ndarray:
    """Pixel-scale grain noise in [0, 1]. Wraps multi_scale_noise with
    sensible defaults for fine surface detail (16-32 px features)."""
    h, w = _shape_hw(shape)
    return multi_scale_noise((h, w), list(freqs), list(weights), int(seed))


def dithered_threshold(field: np.ndarray, threshold: float, jitter: float,
                       seed: int) -> np.ndarray:
    """Sharp binary mask with dithered (noisy) boundary.

    Keeper-style transition: `mirror_mask = (field > threshold + dither_noise * jitter)`.
    Returns float32 in {0, 1}-ish (continuous near boundary).
    """
    h, w = field.shape[:2]
    jitter_field = (fine_grain((h, w), seed, freqs=(4, 8, 16),
                               weights=(0.4, 0.35, 0.25)) - 0.5) * jitter
    return (field > (threshold + jitter_field)).astype(np.float32)


def radial_gauss(shape, cx_frac: float, cy_frac: float,
                 sigma_frac: float) -> np.ndarray:
    """Single gaussian falloff field, peak at (cx_frac, cy_frac) of image.
    sigma_frac is sigma as fraction of min(h, w). Output in (0, 1]."""
    h, w = _shape_hw(shape)
    y, x = get_mgrid((h, w))
    cy, cx = h * cy_frac, w * cx_frac
    sigma = min(h, w) * sigma_frac
    r2 = (y - cy) ** 2 + (x - cx) ** 2
    return np.exp(-r2 / (2.0 * sigma * sigma)).astype(np.float32)


# ---------------------------------------------------------------------------
# Motifs
# ---------------------------------------------------------------------------

def motif_thermal_hotspots(shape, seed: int, n_hotspots: int = 9,
                           hotspot_sigma: float = 0.10) -> np.ndarray:
    """Radial heat-glow blobs scattered across the surface — the structural
    motif for any "glowing core/hotspot" finish (blackbody stars,
    ember coals, etc.).

    Each hotspot is a gaussian peak at a pseudo-random location, with
    inter-hotspot positions determined by the seed. Output is the
    pointwise maximum across blobs, modulated by a low-freq turbulence
    field so the hot regions have organic interior texture.

    Returns field in [0, 1] where 1 = peak hotspot center, 0 = cold.
    """
    h, w = _shape_hw(shape)
    key = ("thermal_hotspots", int(h), int(w), int(seed), int(n_hotspots),
           round(hotspot_sigma, 4))
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rng = np.random.RandomState(int(seed) + 8101)
    field = np.zeros((h, w), dtype=np.float32)
    for i in range(n_hotspots):
        cx = rng.uniform(0.08, 0.92)
        cy = rng.uniform(0.08, 0.92)
        sigma_jitter = rng.uniform(0.7, 1.3)
        blob = radial_gauss((h, w), cx, cy, hotspot_sigma * sigma_jitter)
        field = np.maximum(field, blob)
    # Internal turbulence within the hot blobs — gives the cores a
    # "boiling plasma" texture instead of flat discs.
    turb = multi_scale_noise((h, w), [16, 32, 64], [0.35, 0.40, 0.25],
                             int(seed) + 8102)
    field = np.clip(field * (0.65 + turb * 0.35), 0, 1).astype(np.float32)
    return _cache_put(key, field)


def motif_fissure_network(shape, seed: int, density: float = 1.0) -> np.ndarray:
    """Branching crack/vein network — structural motif for finishes that
    fake "molten material visible through a cracked crust" (ember,
    cooling lava, weathered enamel).

    Construction: take an absolute-value low-frequency noise (creates
    ridge lines along the 0.5-isolevel), threshold sharply, then add
    secondary ridges from a different seed for branching detail.

    Returns field in [0, 1] where 1 = on a fissure, 0 = solid crust.
    """
    h, w = _shape_hw(shape)
    key = ("fissure_network", int(h), int(w), int(seed), round(density, 3))
    cached = _cache_get(key)
    if cached is not None:
        return cached
    # Primary fault — long sweeping cracks at low freq
    primary = multi_scale_noise((h, w), [8, 16, 32], [0.4, 0.35, 0.25],
                                int(seed) + 8201)
    primary_ridge = np.clip(1.0 - np.abs(primary - 0.5) * 6.0, 0, 1)
    # Secondary fracture — branching detail at mid freq
    secondary = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25],
                                  int(seed) + 8205)
    secondary_ridge = np.clip(1.0 - np.abs(secondary - 0.5) * 9.0, 0, 1)
    # Density modulator — reduces overall fissure coverage if density < 1
    network = np.clip(primary_ridge * 0.65 + secondary_ridge * 0.45, 0, 1)
    network = np.clip(network * density, 0, 1).astype(np.float32)
    return _cache_put(key, network)


def motif_liquid_pool(shape, seed: int, ripple_freq: float = 4.5) -> np.ndarray:
    """Caustic ripple + concentric pool — structural motif for "liquid
    metallic surface with depth pooling and surface ripples"
    (mercury_pool, liquid_obsidian siblings).

    Construction: concentric circular ripples from a central focus
    (the pool center) interfere with a secondary off-center focus,
    producing caustic-like depth modulation. A fine ripple shimmer
    is overlaid for high-frequency surface motion.

    Returns field in [0, 1] where 1 = ripple crest, 0 = pool depth.
    """
    h, w = _shape_hw(shape)
    key = ("liquid_pool", int(h), int(w), int(seed), round(ripple_freq, 3))
    cached = _cache_get(key)
    if cached is not None:
        return cached
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(int(seed) + 8301)
    # Two foci so the interference pattern isn't perfectly centered
    cx1 = rng.uniform(0.30, 0.55) * w
    cy1 = rng.uniform(0.30, 0.55) * h
    cx2 = rng.uniform(0.50, 0.75) * w
    cy2 = rng.uniform(0.50, 0.75) * h
    r1 = np.sqrt((x - cx1) ** 2 + (y - cy1) ** 2) / max(h, w)
    r2 = np.sqrt((x - cx2) ** 2 + (y - cy2) ** 2) / max(h, w)
    ripple1 = np.sin(r1 * ripple_freq * 2.0 * np.pi) * 0.5 + 0.5
    ripple2 = np.sin(r2 * ripple_freq * 2.6 * np.pi + 1.2) * 0.5 + 0.5
    interference = ripple1 * 0.55 + ripple2 * 0.45
    # Fine shimmer overlay
    shimmer = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], int(seed) + 8305)
    pool = np.clip(interference * 0.75 + shimmer * 0.25, 0, 1).astype(np.float32)
    return _cache_put(key, pool)


def motif_flow_curl(shape, seed: int, viscosity: float = 1.0) -> np.ndarray:
    """Curl-noise flow lines — structural motif for "chrome that appears
    to flow" (living_chrome, liquid_titanium siblings).

    Construction: compute a vector field from two perpendicular
    multi_scale_noise fields, then derive the "flow density" by
    integrating along the curl direction. The result is bands of
    flow that bend around invisible obstacles. Higher viscosity =
    longer smoother flow lines.

    Returns field in [0, 1] where 1 = flow line crest, 0 = between flows.
    """
    h, w = _shape_hw(shape)
    key = ("flow_curl", int(h), int(w), int(seed), round(viscosity, 3))
    cached = _cache_get(key)
    if cached is not None:
        return cached
    base = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25],
                             int(seed) + 8401)
    cross = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25],
                              int(seed) + 8407)
    # Flow direction phase from two perpendicular fields
    phase = (base * 2.0 - 1.0) * 3.0 * viscosity + (cross * 2.0 - 1.0) * 1.8
    # Sinusoidal banding along the flow direction
    flow = np.sin(phase * np.pi * 1.4) * 0.5 + 0.5
    # Sharpen the bands so they read as ridges, not smooth waves
    flow = np.clip((flow - 0.4) * 2.5, 0, 1).astype(np.float32)
    return _cache_put(key, flow)


def motif_spiral_lens(shape, seed: int, arms: int = 3,
                      pull_strength: float = 1.4) -> np.ndarray:
    """Spacetime spiral lensing — structural motif for finishes that fake
    gravitational distortion / vortex (wormhole, singularity siblings).

    Construction: convert image coords to polar (r, theta), generate
    angular ripples that spiral inward as r decreases (logarithmic
    spiral). The pull_strength controls how tightly the spiral winds
    near the center. Output is dark at the singularity, bright at the
    accretion-ring radius, fading at outer halo.

    Returns field in [0, 1] where 1 = bright spiral arm, 0 = void.
    """
    h, w = _shape_hw(shape)
    key = ("spiral_lens", int(h), int(w), int(seed), int(arms),
           round(pull_strength, 3))
    cached = _cache_get(key)
    if cached is not None:
        return cached
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(int(seed) + 8501)
    cx = rng.uniform(0.42, 0.58) * w
    cy = rng.uniform(0.42, 0.58) * h
    dy = y - cy
    dx = x - cx
    r = np.sqrt(dy ** 2 + dx ** 2) / max(h, w) + 1e-6
    theta = np.arctan2(dy, dx)
    # Logarithmic spiral: angle that tightens as r → 0
    spiral_phase = theta * arms + np.log(r + 0.05) * pull_strength * 4.0
    arm = np.sin(spiral_phase) * 0.5 + 0.5
    # Accretion ring: bright torus around the singularity
    ring = np.exp(-((r - 0.18) ** 2) / 0.008)
    # Inner void: dark singularity core
    void_core = 1.0 - np.exp(-(r ** 2) / 0.005)
    # Outer halo turbulence
    halo_turb = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], int(seed) + 8510)
    field = np.clip((arm * 0.65 + ring * 0.55) * void_core
                    + halo_turb * (1.0 - void_core) * 0.18, 0, 1).astype(np.float32)
    return _cache_put(key, field)


def motif_void_core(shape, seed: int, n_voids: int = 6, void_sigma: float = 0.15) -> np.ndarray:
    """Radial dark void zones with subtle accretion ring edges — the structural
    motif for finishes that fake empty spacetime / deep zero-reflection holes
    (void, gravity_well siblings).

    Returns field in [0, 1] where 1 = center of void (maximum darkness),
    0 = normal space / accretion rim highlight.
    """
    h, w = _shape_hw(shape)
    key = ("void_core", int(h), int(w), int(seed), int(n_voids), round(void_sigma, 4))
    cached = _cache_get(key)
    if cached is not None:
        return cached

    rng = np.random.RandomState(int(seed) + 8601)
    void_field = np.zeros((h, w), dtype=np.float32)
    
    y, x = get_mgrid((h, w))
    for _ in range(n_voids):
        cx = rng.uniform(0.15, 0.85)
        cy = rng.uniform(0.15, 0.85)
        sigma = void_sigma * rng.uniform(0.75, 1.25)
        
        # Calculate distance to this void center
        r = np.sqrt((x - cx * w) ** 2 + (y - cy * h) ** 2) / max(h, w)
        
        # Core: gaussian falloff representing the void tunnel
        core = np.exp(-(r ** 2) / (2.0 * sigma * sigma))
        void_field = np.maximum(void_field, core)
        
    # Modulate with some multi-scale noise for organic distortion
    turb = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], int(seed) + 8602)
    # Organic warping of the void shape
    warped_void = np.clip(void_field * (0.8 + turb * 0.2), 0, 1)
    
    field = warped_void.astype(np.float32)
    return _cache_put(key, field)


def motif_nebula_cloud(shape, seed: int) -> np.ndarray:
    """Wispy, multi-band interstellar gas clouds — structural motif for
    cosmic nebulas and active galactic nuclei (nebula sibling).

    Returns field in [0, 1] representing gas density.
    """
    h, w = _shape_hw(shape)
    key = ("nebula_cloud", int(h), int(w), int(seed))
    cached = _cache_get(key)
    if cached is not None:
        return cached

    # Nebula clouds are wispy and organic: construct via multi-scale noise
    # with high weight on large, sweeping structures but with fine turbulent edges.
    gas = multi_scale_noise((h, w), [4, 8, 16, 32], [0.50, 0.30, 0.15, 0.05], int(seed) + 8701)
    
    # Warped phase flow: use curl-like displacement for wispy details
    base_x = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], int(seed) + 8702)
    base_y = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], int(seed) + 8703)
    
    # Warping distance
    y, x = get_mgrid((h, w))
    dy = (base_y - 0.5) * (h / 8.0)
    dx = (base_x - 0.5) * (w / 8.0)
    
    # Interpolate/warp the gas density organically
    y_warped = np.clip(y + dy, 0, h - 1).astype(np.int32)
    x_warped = np.clip(x + dx, 0, w - 1).astype(np.int32)
    warped_gas = gas[y_warped, x_warped]
    
    # Add star/hotspot cluster reservoirs
    rng = np.random.RandomState(int(seed) + 8704)
    cores = np.zeros((h, w), dtype=np.float32)
    for _ in range(5):
        cx = rng.uniform(0.2, 0.8)
        cy = rng.uniform(0.2, 0.8)
        blob = radial_gauss((h, w), cx, cy, rng.uniform(0.08, 0.18))
        cores = np.maximum(cores, blob)
        
    field = np.clip(warped_gas * 0.70 + cores * 0.30, 0, 1).astype(np.float32)
    return _cache_put(key, field)


# ---------------------------------------------------------------------------
# Palette LUT
# ---------------------------------------------------------------------------

def palette_lut(hsv_stops: list, n: int = 256) -> np.ndarray:
    """Build an (n, 3) float32 RGB LUT by linear HSV interpolation across
    a list of HSV anchor stops. Hue interpolates along shorter arc.
    """
    n_anchors = len(hsv_stops)
    table = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        t = i / float(n - 1)
        seg = t * (n_anchors - 1)
        idx = int(seg)
        frac = seg - idx
        if idx >= n_anchors - 1:
            h, s, v = hsv_stops[-1]
        else:
            h0, s0, v0 = hsv_stops[idx]
            h1, s1, v1 = hsv_stops[idx + 1]
            dh = h1 - h0
            if dh > 0.5:
                dh -= 1.0
            elif dh < -0.5:
                dh += 1.0
            h = (h0 + dh * frac) % 1.0
            s = s0 + (s1 - s0) * frac
            v = v0 + (v1 - v0) * frac
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        table[i] = (r, g, b)
    return table


# ---------------------------------------------------------------------------
# Composers — standardized spec/paint assembly
# ---------------------------------------------------------------------------

def _apply_placement_to_field(field: np.ndarray) -> np.ndarray:
    if field is None or field.size == 0:
        return field
    from engine.paint_v2.placement_context import get_zone_placement
    pl = get_zone_placement()
    if pl is None:
        return field

    scale = float(pl.get("scale", 1.0))
    offset_x = float(pl.get("offset_x", 0.5))
    offset_y = float(pl.get("offset_y", 0.5))
    rotation = float(pl.get("rotation", 0.0))
    flip_h = bool(pl.get("flip_h", False))
    flip_v = bool(pl.get("flip_v", False))

    if (abs(scale - 1.0) < 0.01 and
        abs(offset_x - 0.5) < 0.001 and
        abs(offset_y - 0.5) < 0.001 and
        abs(rotation % 360.0) < 0.5 and
        not flip_h and not flip_v):
        return field

    from engine.compose import _transform_base_color_source
    h, w = field.shape[:2]
    # Re-normalize/clip input field to [0, 1] to prevent _transform_base_color_source issues
    f_norm = np.clip(field, 0.0, 1.0)
    temp = np.repeat(f_norm[:, :, np.newaxis], 3, axis=2)
    transformed = _transform_base_color_source(
        temp, (h, w),
        scale=scale, offset_x=offset_x, offset_y=offset_y,
        rotation=rotation, flip_h=flip_h, flip_v=flip_v
    )
    # Ensure shape matches exactly
    res = transformed[:, :, 0]
    if res.shape[:2] != (h, w):
        from engine.core import _resize_array
        res = _resize_array(res, h, w)
    return res


def compose_spec(motif: np.ndarray, mask, sm: float,
                 m_hi: float, m_lo: float,
                 r_hi: float, r_lo: float,
                 cc_hi: float, cc_lo: float,
                 grain: np.ndarray | None = None,
                 grain_amp: float = 18.0) -> np.ndarray:
    """Standard spec-map assembly from a single motif field in [0, 1].

    motif near 1 → uses (m_hi, r_hi, cc_hi)
    motif near 0 → uses (m_lo, r_lo, cc_lo)

    Note: by keeper convention, "hi" for M typically means metallic-mirror
    (M=220+, R=15), and "lo" means matte-void (M=20, R=200+). So r_hi is
    usually LOWER than r_lo. Caller picks the polarity.

    grain is an optional fine-grain field added with grain_amp magnitude
    to all three channels for surface micro-texture. None to skip.

    Returns (h, w, 4) uint8: [M, R, CC, alpha] per iRacing PBR contract.
    """
    motif = _apply_placement_to_field(motif)
    if grain is not None:
        grain = _apply_placement_to_field(grain)

    h, w = motif.shape[:2]
    s = max(float(sm), 0.05)
    g = (grain - 0.5) * grain_amp if grain is not None else 0.0
    M = motif * m_hi * s + (1.0 - motif) * m_lo * s + g
    R = motif * r_hi * s + (1.0 - motif) * r_lo * s + g
    CC = motif * cc_hi + (1.0 - motif) * cc_lo  # CC unaffected by sm by convention
    if mask is not None:
        if mask.ndim == 3:
            mask2 = mask[:, :, 0]
        else:
            mask2 = mask
        active = (mask2 > 0.01).astype(np.float32)
    else:
        active = np.ones((h, w), dtype=np.float32)
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[:, :, 0] = (np.clip(M, 0, 255).astype(np.uint8)) * (active > 0)
    out[:, :, 1] = (np.clip(R, 15, 255).astype(np.uint8)) * (active > 0)
    out[:, :, 2] = (np.clip(CC, 16, 255).astype(np.uint8)) * (active > 0)
    out[:, :, 3] = (active * 255).astype(np.uint8)
    return out


def compose_paint(paint_in: np.ndarray, motif: np.ndarray, lut: np.ndarray,
                  mask, pm: float, bb,
                  intensity: float = 0.85,
                  dark_zone_only: bool = True,
                  dark_threshold: float = 0.45) -> np.ndarray:
    """Standard paint-map blend from a motif field + palette LUT.

    motif (0..1) indexes into the (256, 3) LUT to choose a chromatic
    substrate color per pixel. By default the substrate replaces only
    DARK regions of the incoming paint (luma < dark_threshold), so
    sponsor decals / numbers / light body sections pass through.

    pm = paint multiplier (0..1) caller-supplied, intensity is the
    finish's own blend strength.

    bb = brightness booster (scalar or 2D).
    """
    motif = _apply_placement_to_field(motif)

    if paint_in.ndim == 3 and paint_in.shape[2] > 3:
        paint_in = paint_in[:, :, :3].copy()
    src = np.asarray(paint_in, dtype=np.float32)
    if src.max() > 1.5:
        src = src / 255.0
    h, w = src.shape[:2]
    # Substrate from motif → palette LUT
    idx = (np.clip(motif, 0, 1) * 255).astype(np.int32).clip(0, 255)
    substrate = lut[idx]  # (h, w, 3)
    # Base-aware: only blend into dark zones if requested
    if dark_zone_only:
        luma = src[:, :, 0] * 0.299 + src[:, :, 1] * 0.587 + src[:, :, 2] * 0.114
        treat = 1.0 / (1.0 + np.exp((luma - dark_threshold) * 8.0))
    else:
        treat = np.ones((h, w), dtype=np.float32)
    if mask is not None:
        if mask.ndim == 3:
            mask2 = mask[:, :, 0]
        else:
            mask2 = mask
    else:
        mask2 = np.ones((h, w), dtype=np.float32)
    active = (treat * mask2 * intensity * float(pm)).astype(np.float32)
    active3 = active[:, :, np.newaxis]
    result = src * (1.0 - active3) + substrate * active3
    # Brightness booster
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb_arr = bb[:, :, np.newaxis]
    elif hasattr(bb, "ndim") and bb.ndim == 3:
        bb_arr = bb
    else:
        bb_arr = np.float32(bb)
    mask3 = (mask2[:, :, np.newaxis] if mask is not None else np.ones((h, w, 1), dtype=np.float32))
    result = np.clip(result + bb_arr * 0.18 * mask3, 0.0, 1.0)
    return result.astype(np.float32)
