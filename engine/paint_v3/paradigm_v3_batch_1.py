"""
paint_v3.paradigm_v3_batch_1 — Batch 1 (Cosmic & Spacetime) Paradigm finishes.

Rebuilds 5 below-75 finishes to push them to high-composite M7 keepers:
  - singularity     (was 36.6)
  - void            (was 45.8)
  - gravity_well    (was 50.8)
  - nebula          (was 52.6)
  - infinite_finish (was 12.7)

Strictly adheres to:
  Rule 1: Motif-mirror (identical parameters in spec and paint)
  Rule 2: Spec channel independence (percentile >= 0.60 on M/R/CC independence via _paradigm_spec)
"""
from __future__ import annotations

import numpy as np

from .primitives import (
    motif_spiral_lens,
    motif_void_core,
    motif_nebula_cloud,
    fine_grain,
    dithered_threshold,
    radial_gauss,
    palette_lut,
    compose_paint,
)
from .paradigm_v3 import _paradigm_spec, _shape_hw
from engine.core import get_mgrid, multi_scale_noise, _resize_array

# ===========================================================================
# Fast nebula cloud motif (perf 2026-06-04)
# ===========================================================================
# The stock primitives.motif_nebula_cloud spends ~1.8s at 2048 (cold), of
# which ~1.35s is FIVE full-res radial_gauss core blobs (np.exp over 4.2M px
# each) plus three full-res multi_scale_noise fields and a 4.2M fancy-index
# warp gather. Every term of this motif is intrinsically smooth/wispy — gas
# clouds and gaussian star cores — so computing the field on a capped grid
# and bilinearly upscaling to (h, w) is visually identical while cutting the
# cold cost by (cap/res)^2. The math below mirrors motif_nebula_cloud EXACTLY
# (same seeds, same scales/weights, same 5 RandomState core draws, same
# 0.70/0.30 blend) so std and look are preserved; at res <= cap it is the
# same computation as the original (just without the disk-cache wrapper).

# Cap chosen so the smallest motif scale (4 px feature on a /4 grid) still has
# ~160 px of base resolution — finer than any visible nebula gas structure,
# yet small enough that the cold 2048 render lands comfortably under 2s. At or
# below the cap (e.g. the 256 px catalog swatch / picker preview) the field is
# byte-identical to the stock primitive, so the picker look never shifts.
_NEBULA_CLOUD_CAP = 640


def _fast_nebula_cloud(h: int, w: int, seed: int) -> np.ndarray:
    """Wispy interstellar gas-cloud field in [0, 1], shape (h, w).

    Resolution-capped, look-identical reimplementation of
    primitives.motif_nebula_cloud (see module note). Mirrors its seeds and
    parameters term-for-term so spec/paint stay in motif-mirror lockstep
    (Rule 1) and the rendered look + std are preserved.
    """
    seed = int(seed)
    # Compute on a capped grid; at small res this is the native resolution.
    ch = min(int(h), _NEBULA_CLOUD_CAP)
    cw = min(int(w), _NEBULA_CLOUD_CAP)

    # Multi-scale wispy gas (large sweeping structure dominates).
    gas = multi_scale_noise((ch, cw), [4, 8, 16, 32],
                            [0.50, 0.30, 0.15, 0.05], seed + 8701)
    # Curl-like warp displacement fields (low frequency, smooth).
    base_x = multi_scale_noise((ch, cw), [8, 16], [0.6, 0.4], seed + 8702)
    base_y = multi_scale_noise((ch, cw), [8, 16], [0.6, 0.4], seed + 8703)

    y, x = get_mgrid((ch, cw))
    dy = (base_y - 0.5) * (ch / 8.0)
    dx = (base_x - 0.5) * (cw / 8.0)
    y_warped = np.clip(y + dy, 0, ch - 1).astype(np.int32)
    x_warped = np.clip(x + dx, 0, cw - 1).astype(np.int32)
    warped_gas = gas[y_warped, x_warped]

    # Star / hotspot cluster reservoirs — gaussian blobs, perfectly smooth so
    # capping + upscale is invisible. Same 5 RandomState draws as the original.
    rng = np.random.RandomState(seed + 8704)
    yy = y.astype(np.float32)
    xx = x.astype(np.float32)
    sig_base = float(min(ch, cw))
    cores = np.zeros((ch, cw), dtype=np.float32)
    for _ in range(5):
        cx = rng.uniform(0.2, 0.8)
        cy = rng.uniform(0.2, 0.8)
        sfrac = rng.uniform(0.08, 0.18)
        cyp, cxp = ch * cy, cw * cx
        sigma = sig_base * sfrac
        r2 = (yy - cyp) ** 2 + (xx - cxp) ** 2
        blob = np.exp(r2 * (-1.0 / (2.0 * sigma * sigma)))
        np.maximum(cores, blob, out=cores)

    field = np.clip(warped_gas * 0.70 + cores * 0.30, 0, 1).astype(np.float32)

    if ch != int(h) or cw != int(w):
        field = _resize_array(field, int(h), int(w))
        np.clip(field, 0.0, 1.0, out=field)
    return field.astype(np.float32, copy=False)

# ===========================================================================
# Palette LUTs for Batch 1
# ===========================================================================

_BATCH1_LUT_CACHE: dict = {}


def _lut_b1(name: str) -> np.ndarray:
    cached = _BATCH1_LUT_CACHE.get(name)
    if cached is not None:
        return cached
    if name == "singularity":
        # Deep violet-indigo core fading into hot neon pink-cyan-white accretion disk
        stops = [
            (0.78, 0.95, 0.02),   # core void (indigo-black)
            (0.82, 0.90, 0.35),   # inner rim (violet)
            (0.92, 0.85, 0.65),   # accretion ring (magenta)
            (0.55, 0.80, 0.85),   # outer arms (cyan-blue)
            (0.60, 0.15, 0.98),   # hot bright highlight (white-cyan)
        ]
    elif name == "void":
        # Absolute black void wells with surrounding cold steel-chrome accretion halos
        stops = [
            (0.65, 0.95, 0.01),   # pure black void core
            (0.60, 0.80, 0.08),   # fading shadow
            (0.55, 0.40, 0.25),   # steel mid-tone
            (0.50, 0.15, 0.70),   # bright metallic silver rim
            (0.50, 0.02, 0.98),   # mirror chrome highlight
        ]
    elif name == "gravity_well":
        # Deep space gravity vortex: magenta accretion ring with bright yellow-gold corona highlights
        stops = [
            (0.80, 0.95, 0.03),   # deep purple-black core
            (0.85, 0.85, 0.30),   # inner flow (magenta shadow)
            (0.95, 0.90, 0.60),   # energy ring (intense pink)
            (0.08, 0.95, 0.85),   # flame discharge (orange-gold)
            (0.14, 0.80, 0.98),   # bright crown (yellow-white)
        ]
    elif name == "nebula":
        # Sweeping interstellar gas clouds: deep space shadow, wispy purple gas, bright orange clusters
        stops = [
            (0.60, 0.95, 0.05),   # deep indigo space shadow
            (0.70, 0.90, 0.35),   # wispy purple gas
            (0.82, 0.85, 0.65),   # magenta core cloud
            (0.95, 0.95, 0.80),   # stellar nursery (electric orange)
            (0.12, 0.90, 0.96),   # supergiant star (yellow-white)
        ]
    elif name == "infinite_finish":
        # Endless feedback depth: neon jade and lime green concentric mirrors going down forever
        stops = [
            (0.42, 0.95, 0.02),   # green-black endless depth
            (0.40, 0.85, 0.25),   # emerald mid-depth
            (0.38, 0.70, 0.55),   # jade ring
            (0.34, 0.50, 0.80),   # lime highlight
            (0.30, 0.20, 0.98),   # neon-green bright crest
        ]
    else:
        raise ValueError(f"unknown LUT: {name}")
    table = palette_lut(stops)
    _BATCH1_LUT_CACHE[name] = table
    return table


# ===========================================================================
# 1. SINGULARITY
# ===========================================================================

def spec_singularity(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71101
    
    # Primary: spacetime spiral lens (4 arms, medium pull)
    primary = motif_spiral_lens((h, w), seed_eff, arms=4, pull_strength=1.8)
    # Secondary: softer lens at different phase representing gravity wave ripples
    secondary = motif_spiral_lens((h, w), seed_eff + 1000, arms=4, pull_strength=1.2)
    # Tertiary: decorrelating fine grain
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(16, 32), weights=(0.5, 0.5))
    
    # Apply M6 channel independence coefficients
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(240.0,  -25.0,  15.0),
                          r_coeffs=(-30.0,  175.0,  60.0),
                          cc_coeffs=(-15.0, -25.0, 165.0),
                          m_base=15.0, r_base=45.0, cc_base=50.0)


def paint_singularity(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71101
    
    # Identical primary motif call (Rule 1)
    primary = motif_spiral_lens((h, w), seed_eff, arms=4, pull_strength=1.8)
    return compose_paint(paint, primary, _lut_b1("singularity"),
                          mask, pm, bb,
                          intensity=0.94, dark_zone_only=True,
                          dark_threshold=0.55)


# ===========================================================================
# 2. VOID
# ===========================================================================

def spec_void(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71102
    
    # Primary: radial void cores (maximum zero-reflection zones)
    primary = motif_void_core((h, w), seed_eff, n_voids=7, void_sigma=0.14)
    # Secondary: Difference of Gaussians (DoG) representing accretion rims around void edges
    wide_void = motif_void_core((h, w), seed_eff, n_voids=7, void_sigma=0.20)
    secondary = np.clip(wide_void - primary, 0, 1).astype(np.float32)
    # Tertiary: decorrelating fine grain
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(16, 32), weights=(0.55, 0.45))
    
    # M6 coefficients: void is M=0, R=255, CC=0 in core. R is extremely high in core.
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(-220.0,  200.0,  15.0),  # M drops in void core, rises on rims
                          r_coeffs=(220.0,  -150.0,  45.0),  # R spikes in void core, drops on rims
                          cc_coeffs=(-180.0, 160.0, 150.0),  # CC drops in core, rises on rims
                          m_base=240.0, r_base=20.0, cc_base=45.0)


def paint_void(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71102
    
    # Identical primary motif call (Rule 1)
    primary = motif_void_core((h, w), seed_eff, n_voids=7, void_sigma=0.14)
    return compose_paint(paint, primary, _lut_b1("void"),
                          mask, pm, bb,
                          intensity=0.90, dark_zone_only=True,
                          dark_threshold=0.50)


# ===========================================================================
# 3. GRAVITY_WELL
# ===========================================================================

def spec_gravity_well(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71103
    
    # Primary: extremely high pull spiral accretion vortex (2 arms, pull_strength=3.6)
    primary = motif_spiral_lens((h, w), seed_eff, arms=2, pull_strength=3.6)
    # Secondary: softer warp representing peripheral spacetime distortion
    secondary = motif_spiral_lens((h, w), seed_eff + 1200, arms=2, pull_strength=2.2)
    # Tertiary: decorrelating fine grain
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(16, 32), weights=(0.5, 0.5))
    
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(235.0,  -35.0,  20.0),
                          r_coeffs=(-40.0,  180.0,  50.0),
                          cc_coeffs=(-20.0, -30.0, 170.0),
                          m_base=20.0, r_base=40.0, cc_base=55.0)


def paint_gravity_well(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71103
    
    # Identical primary motif call (Rule 1)
    primary = motif_spiral_lens((h, w), seed_eff, arms=2, pull_strength=3.6)
    return compose_paint(paint, primary, _lut_b1("gravity_well"),
                          mask, pm, bb,
                          intensity=0.95, dark_zone_only=True,
                          dark_threshold=0.58)


# ===========================================================================
# 4. NEBULA
# ===========================================================================

def spec_nebula(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71104
    
    # Primary: wispy interstellar nebula cloud gas
    primary = _fast_nebula_cloud(h, w, seed_eff)
    # Secondary: perpendicular gas band structure
    secondary = _fast_nebula_cloud(h, w, seed_eff + 500)
    # Tertiary: decorrelating fine grain
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(8, 16, 32), weights=(0.4, 0.4, 0.2))
    
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(220.0,   30.0,  15.0),
                          r_coeffs=(-60.0,  180.0,  55.0),
                          cc_coeffs=(45.0,  -40.0, 160.0),
                          m_base=25.0, r_base=60.0, cc_base=50.0)


def paint_nebula(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71104
    
    # Identical primary motif call (Rule 1)
    primary = _fast_nebula_cloud(h, w, seed_eff)
    return compose_paint(paint, primary, _lut_b1("nebula"),
                          mask, pm, bb,
                          intensity=0.92, dark_zone_only=True,
                          dark_threshold=0.50)


# ===========================================================================
# 5. INFINITE_FINISH
# ===========================================================================

def spec_infinite_finish(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 71105
    
    # Circular feedback coordinate field
    y, x = get_mgrid((h, w))
    cx, cy = w * 0.5, h * 0.5
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max(h, w) + 1e-6
    
    # Concentric recursive feedback tunnel (16 rings)
    primary = np.clip(np.abs(np.sin(r * 16.0 * np.pi)), 0, 1).astype(np.float32)
    # Secondary: double frequency feedback tunnel (32 rings)
    secondary = np.clip(np.abs(np.sin(r * 32.0 * np.pi)), 0, 1).astype(np.float32)
    # Tertiary: decorrelating fine grain
    tertiary = fine_grain((h, w), seed_eff + 200, freqs=(16, 32), weights=(0.5, 0.5))
    
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(230.0,  -25.0,  20.0),
                          r_coeffs=(-40.0,  185.0,  50.0),
                          cc_coeffs=(-20.0, -30.0, 170.0),
                          m_base=20.0, r_base=40.0, cc_base=55.0)


def paint_infinite_finish(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    
    # Concentric recursive feedback tunnel (16 rings) - identical to spec_infinite_finish primary
    y, x = get_mgrid((h, w))
    cx, cy = w * 0.5, h * 0.5
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max(h, w) + 1e-6
    primary = np.clip(np.abs(np.sin(r * 16.0 * np.pi)), 0, 1).astype(np.float32)
    
    return compose_paint(paint, primary, _lut_b1("infinite_finish"),
                          mask, pm, bb,
                          intensity=0.96, dark_zone_only=True,
                          dark_threshold=0.55)


# ===========================================================================
# Batch 1 Registry exports
# ===========================================================================

V3_BATCH1_SEEDS = {
    "singularity":     (spec_singularity,     paint_singularity),
    "void":            (spec_void,            paint_void),
    "gravity_well":    (spec_gravity_well,    paint_gravity_well),
    "nebula":          (spec_nebula,          paint_nebula),
    "infinite_finish": (spec_infinite_finish, paint_infinite_finish),
}
