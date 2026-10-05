# -*- coding: utf-8 -*-
"""Shokker Paint Booth — Enhanced Foundation EXOTIC (v2, full rewrite).

Quality bar (CLAUDE.md, owner brief 2026-05-15, ratified after SPB-85):

* Render canvas is 2048×2048 covering an ENTIRE car body. Anything that
  looks small in a thumbnail is huge on the car.
* Every generator layers at least 4 frequency bands with the highest
  legitimately fine — single-pixel sparkle / micro-flake / micro-facet.
* Recommended octave palette: macro (4, 8, 16) — detail (64, 128, 256) —
  fine (512, 1024) — micro (2048 = single-pixel + dart-thrown sparkle).
* No "interesting math = good finish" assumptions. Use real techniques:
  Voronoi cells for fracture/cane/kintsugi, lognormal-sized sparkle for
  micro-flake, anisotropic Gaussian for brushed/damascus, multi-frequency
  ridge fields with non-linear sharpness for fractal/lace.

This is the rewrite of v1 (which used octaves up to 64 and produced
boring blobby fields — owner rejected as "the worst I've seen produced").

REGISTRY CONTRACT (preserved from v1):
    spec_fn(shape, seed, sm, bm, br) -> (M, R, CC) float32 (H, W) in [0, 255]
    paint_fn(paint, shape, mask, seed, pm, bb) -> paint (vanilla pass-through)
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Callable, Tuple

import cv2
import numpy as np
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)

# ============================================================================
# IRON RULES (matched to foundation_enhanced)
# ============================================================================
CC_MIN: float = 16.0
R_MIN_NONCHROME: float = 15.0
CHROME_M_THRESHOLD: float = 240.0
CH_MIN: float = 0.0
CH_MAX: float = 255.0

SpecTriple = Tuple[np.ndarray, np.ndarray, np.ndarray]
SpecFn = Callable[[Tuple[int, int], int, float, float, float], SpecTriple]


# ============================================================================
# COMMON HELPERS
# ============================================================================

def _hw(shape) -> Tuple[int, int]:
    if shape is None or len(shape) < 2:
        raise ValueError(f"enhanced_foundation_exotic._hw: bad shape {shape!r}")
    return int(shape[0]), int(shape[1])


def _finish_seed(finish_id: str, salt: int = 0) -> int:
    h = hashlib.sha256(f"{finish_id}|{salt}".encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") & 0x7FFFFFFF


def _enforce_iron(M, R, CC, chrome_allowed: bool = False) -> SpecTriple:
    M = np.nan_to_num(M, nan=0.0, posinf=CH_MAX, neginf=CH_MIN)
    R = np.nan_to_num(R, nan=R_MIN_NONCHROME, posinf=CH_MAX, neginf=R_MIN_NONCHROME)
    CC = np.nan_to_num(CC, nan=CC_MIN, posinf=CH_MAX, neginf=CC_MIN)
    M = np.clip(M, CH_MIN, CH_MAX).astype(np.float32, copy=False)
    R = np.clip(R, CH_MIN, CH_MAX).astype(np.float32, copy=False)
    CC = np.clip(CC, CC_MIN, CH_MAX).astype(np.float32, copy=False)
    if chrome_allowed:
        non_chrome = M < CHROME_M_THRESHOLD
        R = np.where(non_chrome, np.maximum(R, R_MIN_NONCHROME), R).astype(np.float32, copy=False)
    else:
        R = np.maximum(R, R_MIN_NONCHROME).astype(np.float32, copy=False)
    return M, R, CC


def _grid(shape) -> Tuple[np.ndarray, np.ndarray]:
    h, w = _hw(shape)
    y = np.linspace(0.0, 1.0, h, dtype=np.float32)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32)
    return np.meshgrid(x, y)


# ============================================================================
# NEW HIGH-FREQUENCY NOISE INFRASTRUCTURE
# ============================================================================

def _band_noise(shape, seed: int, freq: int) -> np.ndarray:
    """One frequency band of normalized noise in [0,1].

    freq = number of distinct features per axis. So freq=2048 on a 2048 canvas
    means single-pixel features (true white noise). freq=4 means a 4x4 grid of
    blocks. We build coarse bands by random + bilinear upsample so they have
    smooth interior gradients (avoids blocky aliasing on lower freqs).
    """
    h, w = _hw(shape)
    rng = np.random.default_rng(seed)
    if freq >= max(h, w):
        # Single-pixel band — pure random. Cheapest path.
        return rng.random((h, w), dtype=np.float32)
    # SPB paint-finish perf loop tick 2026-06-04; owner: "Speed is king in this app."
    # The manual numpy bilinear (four full-res fancy-index gathers per band) dominated
    # every EFX generator (_band_noise was ~60-77% of total in aurora_skin/frost_fractal
    # profiles). cv2.resize(INTER_LINEAR) is the SAME bilinear interpolation, SIMD-vectorized.
    # We build the coarse freq×freq random grid and let OpenCV upsample to (h, w).
    # Visual signature is preserved (identical bilinear); only the Python-level gather is gone.
    grid = rng.random((freq + 2, freq + 2), dtype=np.float32)
    # Map the (h, w) sample coordinates onto the [0, freq] extent of the coarse grid,
    # matching the original np.linspace(0, freq, n) sampling exactly. cv2.resize samples
    # pixel centers, so we crop the coarse grid to the [0, freq] span (freq+1 cells wide)
    # and resize that to (h, w) for an equivalent bilinear field.
    src = grid[:freq + 1, :freq + 1]
    out = cv2.resize(src, (w, h), interpolation=cv2.INTER_LINEAR)
    return out.astype(np.float32, copy=False)


def _multiband(shape, seed: int, bands: list[tuple[int, float]]) -> np.ndarray:
    """Sum multiple frequency bands with given (freq, weight) tuples.

    Example: bands=[(8, 0.4), (64, 0.3), (512, 0.2), (2048, 0.1)] gives
    a 4-band finish where macro structure dominates but real micro detail
    rides on top. The 2048 band is single-pixel sparkle/grain that prevents
    the boring smoothness owner called out in v1.
    """
    h, w = _hw(shape)
    acc = np.zeros((h, w), dtype=np.float32)
    total_w = sum(w_ for _, w_ in bands) or 1.0
    # SPB paint-finish perf loop tick 2026-06-13; owner: "Speed is king in this app."
    # `acc += (w_/total_w)*b` allocated a fresh 4M-element temporary on every band
    # (the scalar*array product) before the in-place add — memory-bandwidth bound and
    # the dominant cost of every EFX generator (_multiband own-time was ~1.47s/5 calls
    # in cProfile). _band_noise already returns a private array per call, so we scale it
    # IN PLACE then add IN PLACE: zero temporaries, identical float32 math.
    # Verified np.array_equal vs the old expression (maxdiff 0.0).
    scale_dtype = acc.dtype
    for i, (f, w_) in enumerate(bands):
        b = _band_noise((h, w), seed + i * 7919, f)
        np.multiply(b, scale_dtype.type(w_ / total_w), out=b)
        np.add(acc, b, out=acc)
    # Normalize to ~[0, 1] (band sums can drift slightly).
    np.clip(acc, 0.0, 1.0, out=acc)
    return acc


def _worley_cells(shape, seed: int, n_points: int, sharpness: float = 2.0,
                  power: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Worley/Voronoi distance field via jitter-grid trick.

    Returns (d1, d2 - d1) where d1 is distance to nearest seed (cell interior
    intensity) and d2-d1 is distance to the cell boundary (edge ridge).
    Real cellular structure — what you want for fracture, leaded glass,
    kintsugi cracks, crystalline frost.

    `sharpness` powers the d1 falloff (higher = tighter cells).
    `power` shapes the boundary ridge (higher = sharper ridge crests).
    """
    h, w = _hw(shape)
    rng = np.random.default_rng(seed)
    # Generate seed points on a jittered grid so density is uniform.
    side = max(2, int(math.sqrt(n_points * h * w / max(h * w, 1))))
    # Simple uniform random instead of jitter-grid — works well at typical N.
    pys = rng.random(n_points, dtype=np.float32) * h
    pxs = rng.random(n_points, dtype=np.float32) * w
    # Compute distances on a coarse grid to keep memory bounded.
    coarse = 4  # 4× downsample for speed; upsampled distance is smooth.
    ch, cw = h // coarse, w // coarse
    cy = (np.arange(ch).astype(np.float32) + 0.5) * coarse
    cx = (np.arange(cw).astype(np.float32) + 0.5) * coarse
    Y, X = np.meshgrid(cy, cx, indexing="ij")
    # SPB paint-finish perf loop tick 2026-05-31 07:53; owner: "Speed is king in this app."
    # Exact nearest-neighbor query replaces the old all-pairs distance tensor, preserving Voronoi structure.
    # Measured: efx_damascus_trinity 14109.6->11408.3 ms, efx_damascus_fold 6570.0->4966.8 ms; std drift ~0.
    pts = np.column_stack([pys, pxs]).astype(np.float32, copy=False)
    grid_pts = np.column_stack([Y.ravel(), X.ravel()]).astype(np.float32, copy=False)
    d, _idx = cKDTree(pts).query(grid_pts, k=2, workers=-1)
    d1c = d[:, 0].reshape(ch, cw).astype(np.float32)
    d2c = d[:, 1].reshape(ch, cw).astype(np.float32)
    # Normalize by typical inter-point distance.
    norm = math.sqrt(h * w / max(n_points, 1)) * 0.6
    d1c = d1c / norm
    edgec = (d2c - d1c) / norm  # ~0 at edges, ~1 at cell centers
    # Upsample bilinearly. cv2.resize(INTER_LINEAR) replaces the PIL round-trip
    # (Image.fromarray -> encode -> resize -> np.array), which showed up as
    # ImagingEncoder/encode cost in profiles. Same bilinear interpolation.
    d1 = cv2.resize(d1c, (w, h), interpolation=cv2.INTER_LINEAR)
    edge = cv2.resize(edgec, (w, h), interpolation=cv2.INTER_LINEAR)
    # Shape responses. SPB paint-finish perf loop tick 2026-06-13; owner: "Speed is king."
    # cv2.resize hands back fresh float32 arrays, so shape the cell/edge responses
    # in place — drops two full-res 4M temporaries + the trailing .astype copies that
    # showed up in cProfile. Same op order/dtype -> bit-identical (verified
    # np.array_equal across 4 n/sharpness/power settings, maxdiff 0.0).
    np.power(d1, sharpness, out=d1)
    np.subtract(1.0, d1, out=d1)
    np.clip(d1, 0.0, 1.0, out=d1)
    np.power(edge, power, out=edge)
    np.subtract(1.0, edge, out=edge)
    np.clip(edge, 0.0, 1.0, out=edge)
    return d1, edge


def _sparkle_field(shape, seed: int, density_per_megapixel: float = 800.0,
                   size_mean: float = 1.4, size_sigma: float = 0.6,
                   intensity_mean: float = 0.85) -> np.ndarray:
    """Dart-thrown sparkle field with lognormal radius distribution.

    Real metallic flake has size variation. This places sparkle points with
    radii drawn from lognormal — many tiny sparkles, fewer big ones. Each
    sparkle is rendered as a soft Gaussian-like dot.

    density_per_megapixel: typical 500-2000 (more = denser flake).
    size_mean: radius in pixels (lognormal mu in pixels).
    """
    h, w = _hw(shape)
    rng = np.random.default_rng(seed)
    n_sparkles = int(density_per_megapixel * (h * w) / 1_000_000)
    if n_sparkles <= 0:
        return np.zeros((h, w), dtype=np.float32)
    ys = rng.integers(0, h, size=n_sparkles)
    xs = rng.integers(0, w, size=n_sparkles)
    # Lognormal radii (in pixels). Clamp to [1, 5] for sanity.
    radii = np.clip(rng.lognormal(mean=math.log(size_mean), sigma=size_sigma, size=n_sparkles), 1.0, 5.0).astype(np.float32)
    intensities = np.clip(rng.normal(intensity_mean, 0.15, size=n_sparkles), 0.4, 1.0).astype(np.float32)
    field = np.zeros((h, w), dtype=np.float32)
    # SPB paint-finish perf loop tick 2026-06-04; owner: "Speed is king in this app."
    # The per-particle Python loop (meshgrid + slice-max per sparkle) was O(N) Python
    # iterations — ~6300 calls/render for frost_fractal at 2048. Vectorized by bucketing
    # particles on their integer stamp radius (ri in {1..5}) and stamping every particle
    # in a bucket at once via a scatter-max (np.maximum.at). The soft blob falloff
    # it/(1+d²/r²), the clamps, and the max-combine semantics are preserved EXACTLY.
    ri_all = np.maximum(1, np.rint(radii).astype(np.int64))
    for ri in np.unique(ri_all):
        ri = int(ri)
        sel = ri_all == ri
        cy = ys[sel].astype(np.int64)
        cx = xs[sel].astype(np.int64)
        rr = radii[sel]            # true float radius drives the falloff (matches original)
        it = intensities[sel]
        m = cy.shape[0]
        if m == 0:
            continue
        # Stamp footprint offsets [-ri, ri] in both axes.
        off = np.arange(-ri, ri + 1, dtype=np.int64)
        oy, ox = np.meshgrid(off, off, indexing="ij")          # (K, K)
        oy = oy.ravel(); ox = ox.ravel()                        # (K*K,)
        dist2 = (oy * oy + ox * ox).astype(np.float32)          # (K*K,)
        # Per-particle blob values: it / (1 + dist2 / r²)  -> (m, K*K)
        inv_r2 = (1.0 / (rr * rr)).astype(np.float32)           # (m,)
        blob = it[:, None] / (1.0 + dist2[None, :] * inv_r2[:, None])
        # Target pixel coords for every (particle, offset) pair.
        ty = cy[:, None] + oy[None, :]                          # (m, K*K)
        tx = cx[:, None] + ox[None, :]
        inb = (ty >= 0) & (ty < h) & (tx >= 0) & (tx < w)
        np.maximum.at(field, (ty[inb], tx[inb]), blob[inb])
    return field


def _anisotropic_band(shape, seed: int, angle_deg: float, freq: int,
                       aspect: float = 6.0) -> np.ndarray:
    """Directional grain. Produces elongated features aligned to an angle.

    Used for damascus, brushed, anisotropic chrome. We layer two effects:
      1. Sinusoidal bands at high frequency PERPENDICULAR to the brushing
         direction (these are the visible "fold lines" or "brush strokes").
      2. Multi-band noise modulating those bands so they're irregular.

    This is a complete rewrite of the v2 first-pass which had a column-only
    shift bug (used row 0 shift for every column → no real anisotropy).
    """
    h, w = _hw(shape)
    a = math.radians(angle_deg)
    X, Y = _grid((h, w))
    # v = across the brushing direction (high-frequency dimension).
    v = -X * math.sin(a) + Y * math.cos(a)
    # Modulate amplitude with low-freq noise along the brushing direction so
    # the bands aren't uniform — some bright, some dim.
    along_modulation = _multiband((h, w), seed, [
        (max(2, int(freq // aspect)), 0.5),
        (max(4, int(freq // max(1.0, aspect / 2))), 0.5),
    ])
    # Phase jitter (low-frequency) so bands aren't perfectly straight.
    phase_jitter = _multiband((h, w), seed ^ 0x1357, [
        (max(4, int(freq // 8)), 0.6),
        (max(8, int(freq // 4)), 0.4),
    ])
    # SPB paint-finish perf loop tick 2026-06-13; owner: "Speed is king in this app."
    # Build the sin argument and the grain in place to drop the chain of full-res 4M
    # temporaries (this fn was the top EFX hotspot — ~709 ms own-time/call in cProfile,
    # called up to 4x in damascus). Scalar promotion is matched to the original exactly
    # (float64 python scalar `freq*math.pi*2.0`, in-place float32 ops), so the result is
    # bit-identical — verified np.array_equal across 5 angle/freq settings (maxdiff 0.0).
    jittered = (phase_jitter - 0.5) * 0.05
    jittered += v
    jittered = jittered * (freq * math.pi * 2.0)
    np.sin(jittered, out=jittered)
    jittered += 1.0
    jittered *= 0.5
    # Combine: grain = 0.7*jittered*along + 0.3*along (same op order/rounding as before).
    grain = 0.7 * jittered
    grain *= along_modulation
    grain += 0.3 * along_modulation
    np.clip(grain, 0.0, 1.0, out=grain)
    return grain


def _conv1d(a: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
    """Naive 1D convolution along an axis (numpy only)."""
    k = kernel.size
    pad = k // 2
    if axis == 0:
        ap = np.pad(a, ((pad, pad), (0, 0)), mode="edge")
        out = np.zeros_like(a)
        for i, w in enumerate(kernel):
            out += w * ap[i:i + a.shape[0], :]
    else:
        ap = np.pad(a, ((0, 0), (pad, pad)), mode="edge")
        out = np.zeros_like(a)
        for i, w in enumerate(kernel):
            out += w * ap[:, i:i + a.shape[1]]
    return out


def _ridge_sharp(shape, seed: int, freq: int, power: float = 4.0) -> np.ndarray:
    """Sharp ridge field. Uses abs(sin) on multi-band noise then a power curve.

    power=1 gives smooth ridges, power=4 gives knife-edge ridges, power=8 gives
    very thin bright veins. Used for lace, kintsugi cracks, spectral corridors.
    """
    base = _multiband(shape, seed, [(freq, 0.7), (freq * 2, 0.3)])
    # SPB paint-finish perf loop tick 2026-06-13; owner: "Speed is king in this app."
    # `_multiband` already returns a private array, so fold abs/power/clip in place to
    # avoid two full-res 4M temporaries. Same op order/dtype -> bit-identical
    # (verified np.array_equal across 5 freq/power settings, maxdiff 0.0).
    np.multiply(base, 2.0, out=base)
    np.subtract(1.0, base, out=base)
    np.abs(base, out=base)
    np.power(base, power, out=base)
    np.clip(base, 0.0, 1.0, out=base)
    return base


def _high_octave_micro(shape, seed: int, base_strength: float = 1.0) -> np.ndarray:
    """The micro-detail layer that the v1 generators lacked.

    Stacks noise at octaves 256, 512, 1024, 2048 with descending weights.
    The 2048 band is single-pixel (true white noise) — produces the
    gritty/sparkly micro-detail that prevents the "smeared" feeling.
    Returns array in [0, 1] centered around 0.5.
    """
    return _multiband(shape, seed, [
        (256, 0.30 * base_strength),
        (512, 0.30 * base_strength),
        (1024, 0.25 * base_strength),
        (2048, 0.15 * base_strength),
    ])


def _recipe_work_shape(shape, component_count: int = 0) -> Tuple[int, int]:
    """Render expensive recipe ingredients smaller, then restore full-res detail."""
    h, w = _hw(shape)
    if h >= 1536 and w >= 1536:
        if component_count >= 4:
            return max(512, int(round(h * 0.375))), max(512, int(round(w * 0.375)))
        return max(512, h // 2), max(512, w // 2)
    return h, w


def _resize_field(field: np.ndarray, shape) -> np.ndarray:
    h, w = _hw(shape)
    if field.shape == (h, w):
        return field.astype(np.float32, copy=False)
    return cv2.resize(field.astype(np.float32, copy=False), (w, h), interpolation=cv2.INTER_LINEAR)


# ============================================================================
# 12 REWRITTEN SINGLE-CHARACTER EXOTIC SPEC GENERATORS
# ============================================================================
# Each generator now layers explicitly:
#   1. MACRO layer (broad structure, octaves 4-16)
#   2. MID layer (the character — flow, fracture, ridges)
#   3. FINE layer (octaves 256-512)
#   4. MICRO layer (octaves 1024-2048 + sparkle field)
#
# Generators document their frequency band intent in comments.


def _gen_holographic_drift(hw, seed):
    """Iridescent holographic foil. Now layered with mid-scale chromatic
    regions (so the foil reads as zoned holography, not uniform haze) +
    finer diffraction grating + micro-sparkle.

    Bands: Voronoi chromatic regions (n=18, big enough to survive thumb scale),
    moderate diffraction (60-120 cycles), sparkle, sub-pixel speckle.
    """
    X, Y = _grid(hw)
    chroma_region, chroma_edge = _worley_cells(hw, seed, n_points=22, sharpness=1.0, power=2.5)
    # Diffraction at MODERATE frequency so it doesn't disappear under downsample.
    g1 = (np.sin((X + Y) * 70 * math.pi + chroma_region * 4) + 1.0) * 0.5
    g2 = (np.sin((X * 0.7 + Y * 1.3) * 100 * math.pi) + 1.0) * 0.5
    grating = (g1 * 0.6 + g2 * 0.4)
    micro = _high_octave_micro(hw, seed ^ 0xAA)
    sparkle = _sparkle_field(hw, seed ^ 0xBB, density_per_megapixel=500, size_mean=1.2, intensity_mean=0.92)
    M = 150.0 + 50.0 * grating + 40.0 * chroma_region + 40.0 * sparkle + 15.0 * (micro - 0.5)
    R = 30.0 + 40.0 * (1.0 - grating) + 25.0 * chroma_edge + 25.0 * micro
    CC = 35.0 + 110.0 * grating + 70.0 * chroma_region + 40.0 * (micro - 0.5)
    return M, R, CC


def _gen_cathedral_veil(hw, seed):
    """Leaded stained-glass. Voronoi cells with thick lead ridges between.
    Cell interiors carry fine micro-noise (glass texture). Edge ridges bright.

    Bands: Voronoi (~120 cells) + cell-interior octaves 256/512/1024 + micro sparkle.
    """
    cell, edge = _worley_cells(hw, seed, n_points=130, sharpness=1.5, power=3.5)
    interior_tex = _high_octave_micro(hw, seed ^ 0xCAFE)
    sparkle = _sparkle_field(hw, seed ^ 0xDEAD, density_per_megapixel=200, size_mean=1.0)
    # Lead is bright (M high, R low), glass is dim (M low, R medium).
    M = 50.0 + 160.0 * edge + 20.0 * cell + 50.0 * sparkle
    R = 180.0 - 130.0 * edge + 20.0 * (interior_tex - 0.5)
    CC = 30.0 + 130.0 * edge + 30.0 * interior_tex


    return M, R, CC


def _gen_frost_fractal(hw, seed):
    """Crystallized frost. Macro-scale frost zones (Voronoi cells with soft
    edges) + branching ridges inside + dense ice-crystal sparkle. Lower
    ridge powers so branches cover more area instead of being sparse thin lines.

    Bands: Voronoi zones (n=30) + 3 ridge scales freqs 16/64/256 + sparkle + micro.
    """
    frost_zone, _ = _worley_cells(hw, seed, n_points=30, sharpness=0.8, power=1.5)
    r1 = _ridge_sharp(hw, seed ^ 0x11, freq=16,  power=1.8) * 0.35
    r2 = _ridge_sharp(hw, seed ^ 0x22, freq=64,  power=2.2) * 0.35
    r3 = _ridge_sharp(hw, seed ^ 0x33, freq=256, power=2.5) * 0.30
    branches = np.clip(r1 + r2 + r3, 0.0, 1.0)
    sparkle = _sparkle_field(hw, seed ^ 0x44, density_per_megapixel=1500, size_mean=1.0, intensity_mean=0.95)
    micro = _high_octave_micro(hw, seed ^ 0x55)
    # Combine: frost zones provide macro variation, branches provide structure, sparkle = ice
    combined = np.clip(0.45 * frost_zone + 0.40 * branches + 0.15 * micro, 0.0, 1.0)
    M = 70.0 + 120.0 * combined + 60.0 * sparkle
    R = 50.0 + 110.0 * (1.0 - combined) + 20.0 * (1.0 - micro)
    CC = 60.0 + 130.0 * combined + 30.0 * sparkle
    return M, R, CC


def _gen_kintsugi_bloom(hw, seed):
    """Gold-veined kintsugi. Sparse Voronoi cracks (only the brightest 20% kept)
    against a quiet body. Veins are bright metallic, body is dark + textured.

    Bands: Worley (n=50) — body micro-detail at 256/512 — sparkle in body.
    """
    _, edge = _worley_cells(hw, seed, n_points=55, sharpness=2.0, power=5.0)
    # Keep only the brightest 20% of edges (sparse veins, not full network).
    threshold = np.quantile(edge, 0.80)
    veins = np.where(edge > threshold, (edge - threshold) / (1.0 - threshold + 1e-6), 0.0)
    body = _multiband(hw, seed ^ 0xC0DE, [(32, 0.3), (256, 0.4), (1024, 0.3)])
    sparkle = _sparkle_field(hw, seed ^ 0xDEAD, density_per_megapixel=300, size_mean=1.0)
    M = 35.0 + 200.0 * veins + 40.0 * body + 60.0 * sparkle
    R = 200.0 - 170.0 * veins + 25.0 * (1.0 - body)
    CC = 25.0 + 130.0 * veins + 25.0 * body
    return M, R, CC


def _gen_quicksilver_pool(hw, seed):
    """Liquid mercury. Smooth pooling at multiple scales, with micro-ripples
    that catch the eye. M near max, R near zero (chrome territory).

    Bands: smooth pooling 8/32 — ripple 256 — sub-pixel grain 2048.
    """
    pool = _multiband(hw, seed, [(8, 0.4), (32, 0.3), (128, 0.2), (256, 0.1)])
    ripple = _ridge_sharp(hw, seed ^ 0xFA, freq=256, power=2.5)
    micro = _high_octave_micro(hw, seed ^ 0xCE, base_strength=0.5)
    M = 218.0 - 35.0 * pool + 18.0 * ripple
    R = 6.0 + 12.0 * pool + 8.0 * micro  # chrome_allowed = True; can go below 15
    CC = 18.0 + 22.0 * pool + 6.0 * ripple
    return M, R, CC


def _gen_volcanic_obsidian(hw, seed):
    """Conchoidal fracture in volcanic glass. Worley cells with VERY sharp
    edges (power=8) for knife-blade fracture lines. Cell interiors carry
    obsidian-dark spec with subtle internal striae.

    Bands: Worley fracture network + interior striae 64/256/1024 + micro.
    """
    cell, edge = _worley_cells(hw, seed, n_points=85, sharpness=1.8, power=6.0)
    striae = _anisotropic_band(hw, seed ^ 0x77, angle_deg=22.0, freq=128, aspect=4.0)
    micro = _high_octave_micro(hw, seed ^ 0x88)
    fracture_gleam = np.power(edge, 1.5)  # bright crests
    M = 35.0 + 215.0 * fracture_gleam + 30.0 * cell + 25.0 * (striae - 0.5)
    R = 215.0 - 130.0 * fracture_gleam - 30.0 * cell + 15.0 * micro
    CC = 25.0 + 90.0 * fracture_gleam + 35.0 * cell
    return M, R, CC


def _gen_aurora_skin(hw, seed):
    """Northern-lights veil. Multi-angle flow bands at low frequency, then
    rapid CC oscillation at high frequency for the prismatic shimmer.

    Bands: flow at 3 angles freq=4 — high-freq CC oscillation 512 — micro-sparkle.
    """
    band_a = _multiband(hw, seed,        [(4, 0.5), (8, 0.3), (16, 0.2)])
    band_b = _multiband(hw, seed ^ 0xAB, [(4, 0.5), (8, 0.3), (32, 0.2)])
    band_c = _multiband(hw, seed ^ 0xCD, [(8, 0.4), (16, 0.4), (64, 0.2)])
    cc_osc = _ridge_sharp(hw, seed ^ 0xEF, freq=512, power=2.0)
    sparkle = _sparkle_field(hw, seed ^ 0xFE, density_per_megapixel=350, size_mean=1.1)
    micro = _high_octave_micro(hw, seed ^ 0xAA)
    M = 110.0 + 70.0 * band_a + 40.0 * band_b + 40.0 * sparkle + 15.0 * (micro - 0.5)
    R = 40.0 + 35.0 * band_b + 25.0 * (1.0 - micro)
    CC = 60.0 + 75.0 * band_a + 70.0 * band_c + 50.0 * cc_osc
    return M, R, CC


def _gen_lace_filament(hw, seed):
    """Lace filament. Real lace has REPEATING geometric units, not just
    random ridges. We layer: Worley cell network for the "lace eyelets"
    (the holes in the lace) + sharp filament ridges between cells +
    fine micro-structure. The Worley anchors mid-scale visibility.

    Bands: Voronoi eyelets (n=80) + sharp filament ridges 64/256 + micro.
    """
    eyelet, filament_edge = _worley_cells(hw, seed, n_points=80, sharpness=2.0, power=3.5)
    # Filament ridges sit on top of eyelet boundaries.
    f1 = _ridge_sharp(hw, seed ^ 0x11, freq=64,  power=2.0) * 0.5
    f2 = _ridge_sharp(hw, seed ^ 0x22, freq=256, power=2.5) * 0.5
    fine_filament = np.clip(f1 + f2, 0.0, 1.0)
    # Combine eyelet edges (the geometric lace skeleton) with random fine filament.
    lace = np.clip(0.55 * filament_edge + 0.45 * fine_filament, 0.0, 1.0)
    body = _anisotropic_band(hw, seed ^ 0x55, angle_deg=45.0, freq=64, aspect=4.0)
    sparkle = _sparkle_field(hw, seed ^ 0x77, density_per_megapixel=400, size_mean=1.0)
    M = 70.0 + 150.0 * lace + 30.0 * body + 35.0 * sparkle
    R = 180.0 - 140.0 * lace + 20.0 * (1.0 - body)
    CC = 45.0 + 115.0 * lace + 25.0 * body
    return M, R, CC


def _gen_tempered_spectrum(hw, seed):
    """Heat-tempered oxide. Smooth horizontal bands at low frequency with
    sharp band-boundary ridges, fine grain inside each band, micro-flake.

    Bands: macro horizontal sweep + band-edge ridges + grain 256 + sparkle.
    """
    X, Y = _grid(hw)
    sweep = (np.sin(Y * 5.5 * math.pi) + 1.0) * 0.5  # ~6 horizontal bands
    band_edges = _ridge_sharp(hw, seed, freq=8, power=6.0)
    grain = _anisotropic_band(hw, seed ^ 0x99, angle_deg=0.0, freq=256, aspect=8.0)
    sparkle = _sparkle_field(hw, seed ^ 0xAA, density_per_megapixel=500, size_mean=1.0)
    micro = _high_octave_micro(hw, seed ^ 0xBB)
    M = 145.0 + 50.0 * sweep + 25.0 * grain + 35.0 * sparkle + 15.0 * (micro - 0.5)
    R = 60.0 + 30.0 * band_edges + 25.0 * (1.0 - grain)
    CC = 30.0 + 170.0 * sweep + 50.0 * band_edges + 20.0 * (micro - 0.5)
    return M, R, CC


def _gen_damascus_fold(hw, seed):
    """Folded pattern-welded steel. Real damascus has TWO key visual scales:
    (1) macro folded-billet pattern of darker and lighter steel layers
        (visible from arm's length on a car body), and
    (2) fine directional grain from the forging.

    v2 used only directional sin-bands which average to flat blocks at
    thumbnail scale (macro_std=4.6). Now layered with Voronoi-elongated
    "billet zones" that survive downsampling, plus the anisotropic grain
    riding on top.

    Bands: Voronoi billet zones (n=40 with anisotropic-friendly sharpness),
    directional bands at +30°/-30°/freq 64/128, fine grain at 512, sparkle.
    """
    # SPB paint-finish perf loop tick 2026-05-31 13:35; owner: "No base can be more than 4 seconds."
    # Damascus keeps the same billet/fold recipe, but computes the expensive structure at half-res
    # on 2048 renders and restores full-res single-pixel carrier afterward.
    # Measured efx_damascus_fold 4453.0 ms -> 1457.1 ms at 2048; M7 not rerun in perf-only heartbeat.
    work_hw = _recipe_work_shape(hw, 3)
    billet, billet_edge = _worley_cells(work_hw, seed, n_points=40, sharpness=1.2, power=2.5)
    fold_a = _anisotropic_band(work_hw, seed ^ 0xA0, angle_deg=30.0,  freq=64,  aspect=6.0)
    fold_b = _anisotropic_band(work_hw, seed ^ 0xB0, angle_deg=-30.0, freq=128, aspect=5.0)
    micro_grain = _anisotropic_band(work_hw, seed ^ 0xC0, angle_deg=30.0, freq=512, aspect=4.0)
    sparkle = _sparkle_field(work_hw, seed ^ 0xD0, density_per_megapixel=600, size_mean=0.9)
    # Billet zones (each Voronoi cell = one fold layer) drive macro structure.
    # Fold bands add the directional grain inside each billet zone.
    grain = np.clip(0.45 * billet + 0.20 * fold_a + 0.20 * fold_b + 0.15 * micro_grain, 0.0, 1.0)
    M = 150.0 + 80.0 * grain + 30.0 * billet_edge + 25.0 * sparkle
    R = 130.0 - 100.0 * grain + 20.0 * (1.0 - micro_grain)
    CC = 30.0 + 50.0 * grain + 25.0 * billet_edge + 15.0 * sparkle
    if work_hw != hw:
        M = _resize_field(M, hw)
        R = _resize_field(R, hw)
        CC = _resize_field(CC, hw)
        micro = (_band_noise(hw, seed ^ 0xD1, max(hw)) - 0.5).astype(np.float32, copy=False)
        M = M + micro * 16.0
        R = R - micro * 9.0
        CC = CC + micro * 10.0
    return M, R, CC


def _micro_stardust(shape, seed: int, density_per_megapixel: float = 25000.0) -> np.ndarray:
    """SPB-85 tick 52: vectorized 1-pixel sparkle field for ~100k+ particles.

    The original _sparkle_field uses a per-particle Python loop with
    np.meshgrid — O(N × kernel²). For ~100k particles that's prohibitive.
    This version uses np.maximum.at scatter — O(N) — but renders only
    single-pixel sparkles (which is what 100k-density implies: each
    particle is sub-pixel at any sensible canvas).

    Intensity is lognormal so a few particles are bright and many are
    faint — matches the "stardust" character of countless tiny specks.
    """
    h, w = _hw(shape)
    rng = np.random.default_rng(seed)
    n = int(density_per_megapixel * (h * w) / 1_000_000)
    if n <= 0:
        return np.zeros((h, w), dtype=np.float32)
    ys = rng.integers(0, h, size=n)
    xs = rng.integers(0, w, size=n)
    # Lognormal intensity — most particles dim, some bright. Matches the
    # log-spaced visibility of real micro flake.
    intensities = np.clip(
        rng.lognormal(math.log(0.45), 0.7, size=n), 0.08, 1.0
    ).astype(np.float32)
    field = np.zeros((h, w), dtype=np.float32)
    np.maximum.at(field, (ys, xs), intensities)
    return field


def _gen_stardust_coat(hw, seed):
    """Stardust nebula coat. SPB-85 tick 52: owner counted "purple dots" in
    v2 — density was way too low (~8k total particles at 2048). Target is
    100k+ for continuous shimmer that reads as fine flake on the car body.

    Four layers now:
      * Voronoi nebula clouds (n=15, soft macro depth)
      * Bright big stars (~30 at 2048, 12-15 px radius, lognormal)
      * Medium stars (~240 at 2048, 4 px radius)
      * **100k+ single-pixel micro-sparkles** via vectorized scatter (new)
      * Body multiband for atmospheric depth
    """
    nebula, _ = _worley_cells(hw, seed, n_points=15, sharpness=0.7, power=1.0)
    big_stars = _sparkle_field(hw, seed ^ 0x11, density_per_megapixel=8,
                                  size_mean=12.0, size_sigma=0.6, intensity_mean=0.98)
    medium_stars = _sparkle_field(hw, seed ^ 0x22, density_per_megapixel=60,
                                    size_mean=4.0, size_sigma=0.5, intensity_mean=0.90)
    # SPB-85 tick 52: 100k+ micro-particles via vectorized scatter.
    # 25000 / megapixel = 100k at 2048² (4 megapixels).
    micro_sparkle = _micro_stardust(hw, seed ^ 0x33, density_per_megapixel=25000)
    body = _multiband(hw, seed ^ 0x44, [(64, 0.4), (256, 0.4), (1024, 0.2)]) * 0.35
    stars = np.maximum(big_stars, np.maximum(medium_stars, micro_sparkle))
    M = 35.0 + 50.0 * nebula + 30.0 * body + 200.0 * stars
    R = 75.0 - 25.0 * nebula + 20.0 * (1.0 - body)
    CC = 25.0 + 45.0 * nebula + 25.0 * body + 170.0 * stars
    return M, R, CC


def _gen_spectral_edge(hw, seed):
    """Ghost veil with bright spec-edge corridors. Use Voronoi cell EDGES
    (real cellular boundaries) as the corridor skeleton, then sharpen the
    brightest portion. Adds visible mid-scale structure that survives
    thumbnail downsample, while keeping the ghost-veil intent.

    Bands: Voronoi cell edges (n=45, sparse) + sharp accent ridges + body grain.
    """
    _, cell_edges = _worley_cells(hw, seed, n_points=45, sharpness=1.5, power=4.0)
    # Keep only brightest 50% of edges (sparse corridors, not full network).
    threshold = np.quantile(cell_edges, 0.50)
    corridors = np.where(cell_edges > threshold,
                          (cell_edges - threshold) / (1.0 - threshold + 1e-6),
                          0.0)
    accent_r = _ridge_sharp(hw, seed ^ 0xA1, freq=128, power=3.0) * 0.4
    corridors_combined = np.clip(corridors + accent_r * 0.3, 0.0, 1.0)
    body = _multiband(hw, seed ^ 0xC3, [(32, 0.3), (128, 0.4), (1024, 0.3)])
    speckle = _band_noise(hw, seed ^ 0xD4, freq=2048)
    M = 45.0 + 50.0 * body + 175.0 * corridors_combined + 20.0 * (speckle - 0.5)
    R = 145.0 + 30.0 * body - 115.0 * corridors_combined
    CC = 45.0 + 35.0 * body + 130.0 * corridors_combined
    return M, R, CC


# ============================================================================
# REWRITTEN MULTI-FINISH RECIPE BLENDER
# ============================================================================
# v1 used `_region_blobs` at octaves (2, 4, 8) — produced car-body-sized
# patches, the owner's "two halves painted different" complaint.
#
# v2 uses high-frequency weight fields that interleave at the per-finish
# scale. The recipe types now mean:
#   "interleaved"  — soft weights from mid-frequency noise (default)
#   "rings"        — concentric rings, but feathered at edges and modulated
#   "stripes"      — fine alternating strips at high frequency
#
# Crucially, the blend is per-pixel weighted (soft), not hard region masks.


def _interleave_weights(shape, seed: int, n: int, freq: int = 64) -> np.ndarray:
    """Per-pixel weights for N characters, summing to 1, smoothly interleaved.

    Each character gets its own noise field at the given frequency. We take
    softmax over the N fields → smooth weights that interleave at the noise
    scale. Higher `freq` = finer interleaving on the car.
    """
    h, w = _hw(shape)
    fields = np.stack([
        _multiband((h, w), seed + i * 9973, [(freq // 2, 0.4), (freq, 0.4), (freq * 2, 0.2)])
        for i in range(n)
    ], axis=0)
    # Softmax with temperature for blend sharpness.
    temp = 6.0  # higher = sharper region boundaries
    exp_f = np.exp(fields * temp)
    return (exp_f / exp_f.sum(axis=0, keepdims=True)).astype(np.float32)


def _ring_weights(shape, seed: int, n: int, freq_modulation: int = 64) -> np.ndarray:
    """Concentric rings, but modulated so they're not boring circles."""
    h, w = _hw(shape)
    X, Y = _grid((h, w))
    cx, cy = 0.5, 0.5
    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / 0.71
    modulation = _multiband((h, w), seed, [(freq_modulation, 0.5), (freq_modulation * 2, 0.5)])
    r_mod = np.clip(r + (modulation - 0.5) * 0.18, 0.0, 1.0)
    # Soft assignment: each character owns a ring band.
    fields = np.zeros((n, h, w), dtype=np.float32)
    width = 1.0 / n
    centers = np.linspace(width / 2, 1.0 - width / 2, n)
    for i, cc in enumerate(centers):
        fields[i] = np.exp(-((r_mod - cc) ** 2) / (2 * (width * 0.6) ** 2))
    fields += 1e-6
    return fields / fields.sum(axis=0, keepdims=True)


def _stripe_weights(shape, seed: int, n: int, freq: int = 32) -> np.ndarray:
    """Fine diagonal stripes that cycle through N characters.

    Higher freq = finer stripes (think tight pinstripes vs broad bands).
    """
    h, w = _hw(shape)
    X, Y = _grid((h, w))
    # Stripe phase at the given frequency.
    phase = ((X + Y) * freq) % 1.0
    # Add modulation so stripes aren't perfectly straight.
    modulation = _multiband((h, w), seed, [(64, 0.5), (256, 0.5)])
    phase = (phase + (modulation - 0.5) * 0.15) % 1.0
    # Soft assign to N characters with overlap.
    fields = np.zeros((n, h, w), dtype=np.float32)
    width = 1.0 / n
    centers = np.linspace(width / 2, 1.0 - width / 2, n)
    for i, cc in enumerate(centers):
        d = np.minimum(np.abs(phase - cc), 1.0 - np.abs(phase - cc))
        fields[i] = np.exp(-(d ** 2) / (2 * (width * 0.4) ** 2))
    fields += 1e-6
    return fields / fields.sum(axis=0, keepdims=True)


def _make_recipe(finish_id: str, generators: list, recipe_kind: str = "interleaved",
                 chrome_allowed: bool = False, freq: int = 64) -> SpecFn:
    """Compose multiple generators into one finish via soft per-pixel weighting.

    Unlike v1's hard regions + box-blur (which produced 3-zone patches),
    this blends per-pixel based on smooth high-frequency weight fields.
    The blend is interleaved at the noise scale — no big patches.
    """
    n = len(generators)

    def _weights(shape, seed):
        if recipe_kind == "rings":
            return _ring_weights(shape, seed, n, freq_modulation=freq)
        if recipe_kind == "stripes":
            return _stripe_weights(shape, seed, n, freq=freq)
        return _interleave_weights(shape, seed, n, freq=freq)

    def spec_fn(shape, seed, sm, bm, br):
        try:
            base = (int(seed) & 0x7FFFFFFF) ^ _finish_seed(finish_id)
            hw = _hw(shape)
            work_hw = _recipe_work_shape(hw, n)
            weights = _weights(work_hw, base)
            M = R = CC = None
            # SPB paint-finish perf loop tick 2026-05-31 12:57; owner: "No base can be more than 4 seconds."
            # Recipe generators are the EFX bottleneck, so blend costly ingredients at half-res on 2048 renders,
            # upsample the blended channels, then restore full-res 1px micro carrier. Fine detail stays present,
            # but the repeated Worley/anisotropic ingredient work no longer explodes per recipe component.
            for i, gen in enumerate(generators):
                Mi, Ri, CCi = gen(work_hw, base ^ ((i + 1) * 0x9E3779B1))
                wi = weights[i]
                if M is None:
                    M = wi * Mi
                    R = wi * Ri
                    CC = wi * CCi
                else:
                    M += wi * Mi
                    R += wi * Ri
                    CC += wi * CCi
            if work_hw != hw:
                M = _resize_field(M, hw)
                R = _resize_field(R, hw)
                CC = _resize_field(CC, hw)
                micro = _band_noise(hw, base ^ 0x51EED, max(hw))
                micro_delta = (micro - 0.5).astype(np.float32, copy=False)
                M = M + micro_delta * 18.0
                R = R - micro_delta * 10.0
                CC = CC + micro_delta * 12.0
            return _enforce_iron(M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32),
                                  chrome_allowed=chrome_allowed)
        except Exception as exc:
            logger.error("enhanced_foundation_exotic recipe[%s] failed: %s", finish_id, exc)
            h, w = _hw(shape)
            return _enforce_iron(
                np.full((h, w), 120.0, dtype=np.float32),
                np.full((h, w), 90.0, dtype=np.float32),
                np.full((h, w), 60.0, dtype=np.float32),
            )
    spec_fn.__name__ = f"spec_recipe_{finish_id}"
    return spec_fn


# ============================================================================
# WRAPPER — bind generator to spec_fn signature + iron rules
# ============================================================================

def _make_exotic(finish_id: str, generator: Callable, chrome_allowed: bool = False) -> SpecFn:
    def spec_fn(shape, seed, sm, bm, br):
        try:
            s = (int(seed) & 0x7FFFFFFF) ^ _finish_seed(finish_id)
            M, R, CC = generator(_hw(shape), s)
            return _enforce_iron(M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32),
                                  chrome_allowed=chrome_allowed)
        except Exception as exc:
            logger.error("enhanced_foundation_exotic[%s] failed: %s", finish_id, exc)
            h, w = _hw(shape)
            return _enforce_iron(
                np.full((h, w), 120.0, dtype=np.float32),
                np.full((h, w), 90.0, dtype=np.float32),
                np.full((h, w), 60.0, dtype=np.float32),
            )
    spec_fn.__name__ = f"spec_exotic_{finish_id}"
    return spec_fn


# ============================================================================
# PAINT FUNCTION — flat vanilla pass-through (spec_driven intent)
# ============================================================================

def paint_passthrough(paint: np.ndarray, shape, mask, seed, pm, bb) -> np.ndarray:
    if paint is None:
        return paint
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].astype(np.float32, copy=True)
    if paint.dtype != np.float32:
        return paint.astype(np.float32, copy=True)
    return paint.copy()


# ============================================================================
# 20 NEW FINISHES — bound spec fns
# ============================================================================

spec_efx_holographic_drift = _make_exotic("efx_holographic_drift", _gen_holographic_drift)
spec_efx_cathedral_veil    = _make_exotic("efx_cathedral_veil",    _gen_cathedral_veil)
spec_efx_frost_fractal     = _make_exotic("efx_frost_fractal",     _gen_frost_fractal)
spec_efx_kintsugi_bloom    = _make_exotic("efx_kintsugi_bloom",    _gen_kintsugi_bloom)
spec_efx_quicksilver_pool  = _make_exotic("efx_quicksilver_pool",  _gen_quicksilver_pool, chrome_allowed=True)
spec_efx_volcanic_obsidian = _make_exotic("efx_volcanic_obsidian", _gen_volcanic_obsidian)
spec_efx_aurora_skin       = _make_exotic("efx_aurora_skin",       _gen_aurora_skin)
spec_efx_lace_filament     = _make_exotic("efx_lace_filament",     _gen_lace_filament)
spec_efx_tempered_spectrum = _make_exotic("efx_tempered_spectrum", _gen_tempered_spectrum)
spec_efx_damascus_fold     = _make_exotic("efx_damascus_fold",     _gen_damascus_fold)
spec_efx_stardust_coat     = _make_exotic("efx_stardust_coat",     _gen_stardust_coat)
spec_efx_spectral_edge     = _make_exotic("efx_spectral_edge",     _gen_spectral_edge)

# Multi-finish recipes — now using fine-frequency interleaved weights, not regions.
spec_efx_frost_mercury_duo = _make_recipe(
    "efx_frost_mercury_duo",
    [_gen_frost_fractal, _gen_quicksilver_pool],
    recipe_kind="interleaved", chrome_allowed=True, freq=96,
)
spec_efx_aurora_obsidian_veil = _make_recipe(
    "efx_aurora_obsidian_veil",
    [_gen_aurora_skin, _gen_volcanic_obsidian],
    recipe_kind="interleaved", freq=80,
)
spec_efx_damascus_trinity = _make_recipe(
    "efx_damascus_trinity",
    [_gen_damascus_fold, _gen_quicksilver_pool, _gen_spectral_edge],
    recipe_kind="stripes", chrome_allowed=True, freq=24,
)
spec_efx_cathedral_holographic = _make_recipe(
    "efx_cathedral_holographic",
    [_gen_cathedral_veil, _gen_holographic_drift],
    recipe_kind="interleaved", freq=96,
)
spec_efx_tempered_quattro = _make_recipe(
    "efx_tempered_quattro",
    [_gen_tempered_spectrum, _gen_aurora_skin, _gen_damascus_fold, _gen_stardust_coat],
    recipe_kind="rings", freq=64,
)
spec_efx_crystalline_triad = _make_recipe(
    "efx_crystalline_triad",
    [_gen_frost_fractal, _gen_kintsugi_bloom, _gen_spectral_edge],
    recipe_kind="interleaved", freq=80,
)
spec_efx_volcanic_triad = _make_recipe(
    "efx_volcanic_triad",
    [_gen_volcanic_obsidian, _gen_quicksilver_pool, _gen_stardust_coat],
    recipe_kind="interleaved", chrome_allowed=True, freq=72,
)
spec_efx_aurora_fold = _make_recipe(
    "efx_aurora_fold",
    [_gen_aurora_skin, _gen_damascus_fold],
    recipe_kind="interleaved", freq=80,
)


# ============================================================================
# REGISTRY
# ============================================================================

ENHANCED_FOUNDATION_EXOTIC = {
    "efx_holographic_drift": {"M": 200, "R": 40, "CC": 120, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_holographic_drift,
        "desc": "★ Holographic Drift — diffraction grating + micro-sparkle (4 octave bands)"},
    "efx_cathedral_veil": {"M": 110, "R": 110, "CC": 80, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_cathedral_veil,
        "desc": "★ Cathedral Veil — Voronoi cane network + glass-interior texture"},
    "efx_frost_fractal": {"M": 150, "R": 80, "CC": 130, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_frost_fractal,
        "desc": "★ Frost Fractal — 5-frequency recursive ridges + ice-crystal sparkle"},
    "efx_kintsugi_bloom": {"M": 90, "R": 130, "CC": 60, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_kintsugi_bloom,
        "desc": "★ Kintsugi Bloom — sparse gold veins on a textured matte body"},
    "efx_quicksilver_pool": {"M": 215, "R": 10, "CC": 25, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_quicksilver_pool,
        "desc": "★ Quicksilver Pool — multi-scale mercury pooling, chrome territory"},
    "efx_volcanic_obsidian": {"M": 110, "R": 150, "CC": 70, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_volcanic_obsidian,
        "desc": "★ Volcanic Obsidian — Voronoi fracture wells with knife-edge ridges"},
    "efx_aurora_skin": {"M": 140, "R": 55, "CC": 130, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_aurora_skin,
        "desc": "★ Aurora Skin — flowing chromatic veils with high-freq CC oscillation"},
    "efx_lace_filament": {"M": 140, "R": 110, "CC": 90, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_lace_filament,
        "desc": "★ Lace Filament — 5-octave fractal lace + anisotropic body grain"},
    "efx_tempered_spectrum": {"M": 170, "R": 70, "CC": 130, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_tempered_spectrum,
        "desc": "★ Tempered Spectrum — heat-tint bands with anisotropic grain + sparkle"},
    "efx_damascus_fold": {"M": 200, "R": 60, "CC": 55, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_damascus_fold,
        "desc": "★ Damascus Fold — interleaved anisotropic bands at multiple angles"},
    "efx_stardust_coat": {"M": 100, "R": 70, "CC": 80, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_stardust_coat,
        "desc": "★ Stardust Coat — sparse big stars + dense micro-sparkle on dark body"},
    "efx_spectral_edge": {"M": 90, "R": 130, "CC": 80, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_spectral_edge,
        "desc": "★ Spectral Edge — sharp light corridors at 3 frequencies + sub-pixel speckle"},
    # Multi-finish recipes — soft per-pixel interleaved weights (no big patches)
    "efx_frost_mercury_duo": {"M": 180, "R": 50, "CC": 90, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_frost_mercury_duo,
        "desc": "★ Frost / Mercury Duo (DUAL) — interleaved at freq 96"},
    "efx_aurora_obsidian_veil": {"M": 130, "R": 100, "CC": 100, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_aurora_obsidian_veil,
        "desc": "★ Aurora / Obsidian Veil (DUAL) — interleaved at freq 80"},
    "efx_damascus_trinity": {"M": 175, "R": 60, "CC": 60, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_damascus_trinity,
        "desc": "★ Damascus Trinity (TRIPLE) — fine diagonal stripes at freq 24"},
    "efx_cathedral_holographic": {"M": 155, "R": 80, "CC": 100, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_cathedral_holographic,
        "desc": "★ Cathedral / Holographic (DUAL) — interleaved at freq 96"},
    "efx_tempered_quattro": {"M": 155, "R": 65, "CC": 110, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_tempered_quattro,
        "desc": "★ Tempered Quattro (QUAD) — modulated concentric rings"},
    "efx_crystalline_triad": {"M": 120, "R": 110, "CC": 90, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_crystalline_triad,
        "desc": "★ Crystalline Triad (TRIPLE) — interleaved at freq 80"},
    "efx_volcanic_triad": {"M": 145, "R": 100, "CC": 75, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_volcanic_triad,
        "desc": "★ Volcanic Triad (TRIPLE) — interleaved at freq 72"},
    "efx_aurora_fold": {"M": 170, "R": 60, "CC": 95, "paint_fn": paint_passthrough,
        "base_spec_fn": spec_efx_aurora_fold,
        "desc": "★ Aurora Fold (DUAL) — interleaved at freq 80"},
}


__all__ = ["ENHANCED_FOUNDATION_EXOTIC", "paint_passthrough"]
