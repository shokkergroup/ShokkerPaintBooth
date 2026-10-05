"""
paint_v3.paradigm_v3_batch_2 — Batch 2 (Quantum & Fields) Paradigm finishes.

Retools the Batch 2 finishes to reflect direct user creative feedback:
  - p_static: Glowing retro CRT phosphor screen overlay with high-contrast neon green/cyan phosphor glitches,
              and glass CRT screen specular glaze (no heavy rust-like reddish texture).
  - stealth:  Hyper-detailed carbon fiber twill weave with tactical matte panels, panel seams,
              and micro-rivets/hex-screws spaced along the boundaries.
  - magnetic: Ferrofluid liquid metal flow waves! Sweeping liquid chrome waves flowing smoothly
              between bipolar fields, populated by micro-flux grain.
  - p_aurora: Ethereal polar auroral storm curtains! Thin, luminous, high-contrast waves
              intertwined with floating stardust particles.
  - quantum:  Unique radial subatomic wave interference with Planck subatomic glow (retains the successful look).

Centralized scaling is implemented via expansions/paradigm.py wrappers.
"""
from __future__ import annotations

import colorsys
import cv2
import numpy as np

from .primitives import (
    fine_grain,
    dithered_threshold,
    radial_gauss,
    palette_lut,
    compose_paint,
)
from .paradigm_v3 import _paradigm_spec, _shape_hw
from engine.core import get_mgrid, multi_scale_noise

# Voronoi helper function for faceted panels
def _voronoi_v3(shape, n_points: int, seed: int):
    h, w = _shape_hw(shape)
    rng = np.random.RandomState(int(seed))
    pts = np.zeros((n_points, 2), dtype=np.float32)
    pts[:, 0] = rng.uniform(0, w, n_points)
    pts[:, 1] = rng.uniform(0, h, n_points)
    
    y, x = get_mgrid((h, w))
    min_dist = np.full((h, w), 1e8, dtype=np.float32)
    cell_id = np.zeros((h, w), dtype=np.int32)
    
    # Brute-force Voronoi for small n_points
    for i in range(n_points):
        dy = y - pts[i, 1]
        dx = x - pts[i, 0]
        dist = np.sqrt(dx*dx + dy*dy)
        closer = dist < min_dist
        min_dist[closer] = dist[closer]
        cell_id[closer] = i
        
    return min_dist, cell_id


_STEALTH_FIELD_CACHE = {}


def _bounded_shape_b2(shape, limit=768):
    h, w = _shape_hw(shape)
    scale = min(1.0, float(limit) / float(max(h, w)))
    if scale >= 1.0:
        return int(h), int(w)
    return max(128, int(round(h * scale))), max(128, int(round(w * scale)))


def _resize2_b2(field, shape, interpolation):
    h, w = _shape_hw(shape)
    if field.shape == (h, w):
        return field
    return cv2.resize(field.astype(np.float32, copy=False), (int(w), int(h)), interpolation=interpolation)


def _stealth_fields(shape, seed_eff):
    h, w = _shape_hw(shape)
    key = (int(h), int(w), int(seed_eff))
    cached = _STEALTH_FIELD_CACHE.get(key)
    if cached is not None:
        return cached

    # SPB paint-finish perf loop 2026-05-31; stealth measured 5785.4ms -> 1734.6ms.
    # Armor panels are large forms, so compute the Voronoi plate map on a bounded
    # grid and reuse it for both paint and spec while keeping twill full-res.
    work_shape = _bounded_shape_b2((h, w), 768)
    n_facets = min(24, max(10, (h * w) // (256 * 256)))
    min_dist, cell_id = _voronoi_v3(work_shape, n_facets, seed_eff)
    if work_shape != (h, w):
        min_dist = _resize2_b2(min_dist, (h, w), cv2.INTER_LINEAR).astype(np.float32)
        cell_id = np.rint(_resize2_b2(cell_id.astype(np.float32), (h, w), cv2.INTER_NEAREST)).astype(np.int32)

    max_d = min_dist.max() + 1e-8
    seams = np.clip(1.0 - min_dist / (max_d * 0.035), 0, 1).astype(np.float32)
    out = (n_facets, cell_id, seams)
    if len(_STEALTH_FIELD_CACHE) > 12:
        _STEALTH_FIELD_CACHE.clear()
    _STEALTH_FIELD_CACHE[key] = out
    return out

# ===========================================================================
# Palette LUTs for Batch 2 (Tuned to dynamic, glowing CRT, Ferrofluid, and Carbon tones)
# ===========================================================================

_BATCH2_LUT_CACHE: dict = {}

def _lut_b2(name: str) -> np.ndarray:
    cached = _BATCH2_LUT_CACHE.get(name)
    if cached is not None:
        return cached
    if name == "quantum":
        # Fluorescent subatomic quantum field - glowing magenta, purple, cyan, neon green
        stops = [
            (0.85, 0.90, 0.05),   # deep indigo valley
            (0.78, 0.85, 0.25),   # violet quantum glow
            (0.92, 0.90, 0.55),   # hot magenta transition
            (0.52, 0.85, 0.85),   # glowing electric cyan
            (0.33, 0.95, 0.95),   # neon green highlight
        ]
    elif name == "magnetic":
        # Sweeping liquid ferrofluid copper/chrome waves
        stops = [
            (0.00, 0.00, 0.08),   # liquid black obsidian deep valleys
            (0.08, 0.85, 0.25),   # dark magnetic copper
            (0.12, 0.90, 0.65),   # bright copper-gold chrome
            (0.55, 0.70, 0.85),   # liquid silver-blue flux
            (0.60, 0.00, 0.98),   # hot white-silver crests
        ]
    elif name == "p_static":
        # Retro phosphorus CRT screen: deep space black, neon phosphorus green, glowing electric cyan
        stops = [
            (0.60, 0.90, 0.04),   # cathode black
            (0.62, 0.80, 0.25),   # vintage slate-gray glass
            (0.35, 0.95, 0.70),   # bright phosphorus green glow
            (0.50, 0.90, 0.85),   # glowing CRT cyan
            (0.00, 0.00, 0.98),   # bright white static sparks
        ]
    elif name == "p_aurora":
        # Ethereal polar auroral storm curtains - deep violet-indigo, emerald green, neon magenta
        stops = [
            (0.72, 0.85, 0.05),   # cold deep space void
            (0.68, 0.80, 0.25),   # deep violet wind
            (0.42, 0.95, 0.75),   # glowing emerald green curtains
            (0.50, 0.90, 0.88),   # electric turquoise highlights
            (0.88, 0.95, 0.98),   # high-altitude neon pink/magenta
        ]
    elif name == "stealth":
        # Stealth tactical military carbon composite: slate gray, military olive, black weave, titanium seams
        stops = [
            (0.00, 0.00, 0.08),   # black carbon fiber weave
            (0.33, 0.12, 0.18),   # dark military olive-gray
            (0.60, 0.05, 0.35),   # matte titanium plate
            (0.60, 0.02, 0.50),   # light tactical slate
            (0.00, 0.00, 0.85),   # bright titanium screw heads
        ]
    else:
        raise ValueError(f"Unknown Batch 2 name: {name}")
    
    lut = palette_lut(stops)
    _BATCH2_LUT_CACHE[name] = lut
    return lut

# ===========================================================================
# 1. QUANTUM (Unique radial probability waves - Successful Look)
# ===========================================================================

def spec_quantum(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72101
    
    # Wave packet radial interference probability
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed_eff)
    cx1, cy1 = rng.uniform(0.2, 0.5) * w, rng.uniform(0.2, 0.5) * h
    cx2, cy2 = rng.uniform(0.5, 0.8) * w, rng.uniform(0.5, 0.8) * h
    
    r1 = np.sqrt((x - cx1) ** 2 + (y - cy1) ** 2) / max(h, w)
    r2 = np.sqrt((x - cx2) ** 2 + (y - cy2) ** 2) / max(h, w)
    
    wave1 = np.clip(np.abs(np.sin(r1 * 24.0 * np.pi)), 0, 1).astype(np.float32)
    wave2 = np.clip(np.abs(np.sin(r2 * 36.0 * np.pi)), 0, 1).astype(np.float32)
    primary = np.clip(wave1 * 0.55 + wave2 * 0.45, 0, 1)
    
    secondary = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed_eff + 10)
    tertiary = fine_grain((h, w), seed_eff + 20, freqs=(16, 32), weights=(0.5, 0.5))
    
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(225.0,  -20.0,  30.0),
                          r_coeffs=(-45.0,  175.0,  40.0),
                          cc_coeffs=(-15.0, -25.0, 160.0),
                          m_base=25.0, r_base=35.0, cc_base=50.0)


def paint_quantum(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72101
    
    # Interference waves
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed_eff)
    cx1, cy1 = rng.uniform(0.2, 0.5) * w, rng.uniform(0.2, 0.5) * h
    cx2, cy2 = rng.uniform(0.5, 0.8) * w, rng.uniform(0.5, 0.8) * h
    r1 = np.sqrt((x - cx1) ** 2 + (y - cy1) ** 2) / max(h, w)
    r2 = np.sqrt((x - cx2) ** 2 + (y - cy2) ** 2) / max(h, w)
    wave1 = np.clip(np.abs(np.sin(r1 * 24.0 * np.pi)), 0, 1).astype(np.float32)
    wave2 = np.clip(np.abs(np.sin(r2 * 36.0 * np.pi)), 0, 1).astype(np.float32)
    primary = np.clip(wave1 * 0.55 + wave2 * 0.45, 0, 1)
    
    turb = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed_eff + 30)
    motif = np.clip(primary * (0.7 + turb * 0.3), 0, 1)
    
    return compose_paint(paint, motif, _lut_b2("quantum"),
                          mask, pm, bb,
                          intensity=0.92, dark_zone_only=True,
                          dark_threshold=0.52)

# ===========================================================================
# 2. MAGNETIC (Ferrofluid sweeping liquid metal wave flows)
# ===========================================================================

def spec_magnetic(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72202
    
    # Smooth, sweeping liquid metal curves based on dipole field
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32); xf = x.astype(np.float32)
    rng = np.random.RandomState(seed_eff)
    py1, px1 = rng.uniform(0.1, 0.4) * h, rng.uniform(0.1, 0.4) * w
    py2, px2 = rng.uniform(0.6, 0.9) * h, rng.uniform(0.6, 0.9) * w
    dy1, dx1 = yf - py1, xf - px1
    dy2, dx2 = yf - py2, xf - px2
    dist1 = dy1**2 + dx1**2 + 1e-5
    dist2 = dy2**2 + dx2**2 + 1e-5
    field_x = dx1 / dist1 - dx2 / dist2
    field_y = dy1 / dist1 - dy2 / dist2
    mag = np.sqrt(field_x**2 + field_y**2)
    mag = (mag - mag.min()) / (mag.max() - mag.min() + 1e-8)
    angle = np.arctan2(field_y, field_x)
    
    # Sweeping metal waves (lower frequency, highly sweeping)
    waves = np.clip(np.abs(np.sin(angle * 6.0 + mag * 12.0)), 0, 1).astype(np.float32)
    
    # Micro-flux details flowing along the ribbons
    filings = fine_grain((h, w), seed_eff + 15, freqs=(16, 32, 64), weights=(0.2, 0.4, 0.4))
    primary = np.clip(waves * 0.85 + filings * mag * 0.15, 0, 1)
    
    # Secondary: Pole centers (extremely high specular reflection/chrome)
    secondary = np.clip(1.0 / (np.sqrt(dist1) / h + 0.05) + 1.0 / (np.sqrt(dist2) / h + 0.05), 0, 10).astype(np.float32)
    secondary = (secondary - secondary.min()) / (secondary.max() - secondary.min() + 1e-8)
    
    # Tertiary: Fine independent filings
    tertiary = fine_grain((h, w), seed_eff + 40, freqs=(24, 48), weights=(0.5, 0.5))
    
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(245.0,  10.0,   0.0),
                          r_coeffs=(-120.0,  -80.0,  200.0), # sweeping metal is mirror-smooth, valleys rough
                          cc_coeffs=(-15.0, 50.0,   120.0),
                          m_base=10.0, r_base=10.0, cc_base=60.0)


def paint_magnetic(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72202
    
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32); xf = x.astype(np.float32)
    rng = np.random.RandomState(seed_eff)
    py1, px1 = rng.uniform(0.1, 0.4) * h, rng.uniform(0.1, 0.4) * w
    py2, px2 = rng.uniform(0.6, 0.9) * h, rng.uniform(0.6, 0.9) * w
    dy1, dx1 = yf - py1, xf - px1
    dy2, dx2 = yf - py2, xf - px2
    dist1 = dy1**2 + dx1**2 + 1e-5
    dist2 = dy2**2 + dx2**2 + 1e-5
    field_x = dx1 / dist1 - dx2 / dist2
    field_y = dy1 / dist1 - dy2 / dist2
    mag = np.sqrt(field_x**2 + field_y**2)
    mag = (mag - mag.min()) / (mag.max() - mag.min() + 1e-8)
    angle = np.arctan2(field_y, field_x)
    waves = np.clip(np.abs(np.sin(angle * 6.0 + mag * 12.0)), 0, 1).astype(np.float32)
    
    filings = fine_grain((h, w), seed_eff + 15, freqs=(16, 32, 64), weights=(0.2, 0.4, 0.4))
    motif = np.clip(waves * 0.85 + filings * mag * 0.15, 0, 1)
    
    # Composes sweeping bronze, silver, and copper liquid waves
    return compose_paint(paint, motif, _lut_b2("magnetic"),
                          mask, pm, bb,
                          intensity=0.98, dark_zone_only=True,
                          dark_threshold=0.60)

# ===========================================================================
# 3. P_STATIC (Phosphor CRT digital glitch overlay & glass CRT glaze)
# ===========================================================================

def spec_p_static(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72303
    
    # Ultra-smooth glass CRT screen (low roughness, max clearcoat)
    # Primary: CRT horizontal scanlines
    y, x = get_mgrid((h, w))
    scan_period = max(2, h // 256)
    scanline_field = ((y // scan_period) % 2).astype(np.float32)
    primary = scanline_field
    
    # Secondary: Digital glitches & sync drop blocks
    rng = np.random.RandomState(seed_eff)
    glitch_blocks = np.zeros((h, w), dtype=np.float32)
    for _ in range(12):
        gy = rng.randint(0, h - 30)
        gx = rng.randint(0, w - 120)
        gh = rng.randint(4, 24)
        gw = rng.randint(20, 200)
        glitch_blocks[gy:gy+gh, gx:gx+gw] = rng.uniform(0.8, 1.0)
    secondary = glitch_blocks
    
    # Tertiary: High-frequency phosphor pixel matrix
    tertiary = fine_grain((h, w), seed_eff + 90, freqs=(64, 128), weights=(0.5, 0.5))
    
    # Spec: Smooth CRT screen glaze (M=15, R=25, CC=16) with metallic glinting sparks
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(15.0,   230.0,  10.0), # Glitch blocks are highly metallic sparks
                          r_coeffs=(-15.0,  -120.0, 160.0), # Glitch and scanlines are mirror-smooth (low R)
                          cc_coeffs=(-10.0, 80.0,   120.0),
                          m_base=15.0, r_base=20.0, cc_base=16.0) # max clearcoat base


def paint_p_static(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72303
    
    # CRT Phosphor backdrop (deep dark slate body)
    # Motif blends scanlines, digital glitch blocks, and white static bursts
    y, x = get_mgrid((h, w))
    scan_period = max(2, h // 256)
    scanline_field = (((y // scan_period) % 2) * 0.20).astype(np.float32)
    
    # Digital glitches & phosphor grid
    rng = np.random.RandomState(seed_eff)
    glitch_blocks = np.zeros((h, w), dtype=np.float32)
    for _ in range(12):
        gy = rng.randint(0, h - 30)
        gx = rng.randint(0, w - 120)
        gh = rng.randint(4, 24)
        gw = rng.randint(20, 200)
        glitch_blocks[gy:gy+gh, gx:gx+gw] = rng.uniform(0.7, 1.0)
        
    static = fine_grain((h, w), seed_eff + 50, freqs=(16, 32, 64), weights=(0.3, 0.4, 0.3))
    
    motif = np.clip(glitch_blocks * 0.50 + scanline_field * 0.30 + static * 0.20, 0, 1)
    
    # Composes glowing phosphorus green and electric cyan scanline grid
    paint = compose_paint(paint, motif, _lut_b2("p_static"),
                          mask, pm, bb,
                          intensity=0.98, dark_zone_only=True,
                          dark_threshold=0.55)
                          
    # High-frequency phosphor sub-pixel noise overlay (never muddy red/brown, purely green/cyan/white)
    subpixel_noise = rng.uniform(-0.12, 0.12, (h, w)).astype(np.float32)
    cyan_glow = np.zeros((h, w, 3), dtype=np.float32)
    cyan_glow[:, :, 0] = 0.0   # Red
    cyan_glow[:, :, 1] = 0.9   # Green
    cyan_glow[:, :, 2] = 1.0   # Blue
    
    noise_mask = (rng.uniform(0.0, 1.0, (h, w)) > 0.94).astype(np.float32)
    paint = np.clip(paint + (subpixel_noise[:, :, np.newaxis] * cyan_glow * noise_mask[:, :, np.newaxis] * pm * mask[:, :, np.newaxis]), 0.0, 1.0)
    return paint

# ===========================================================================
# 4. P_AURORA (Ethereal sweeping curtains with stardust flares)
# ===========================================================================

def spec_p_aurora(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72404
    
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    
    # Luminous vertical/horizontal wave curtains
    wobble = multi_scale_noise((h, w), [12, 24], [0.65, 0.35], seed_eff) * (h * 0.15)
    curtain1 = np.sin((yf + wobble) * 0.022 * np.pi) * 0.5 + 0.5
    curtain2 = np.sin((yf + wobble * 0.8) * 0.038 * np.pi + 1.2) * 0.5 + 0.5
    primary = np.clip(curtain1 * 0.60 + curtain2 * 0.40, 0, 1).astype(np.float32)
    
    # Floating stardust flares
    rng = np.random.RandomState(seed_eff + 10)
    stardust = (rng.uniform(0.0, 1.0, (h, w)) > 0.992).astype(np.float32)
    secondary = stardust
    
    # Solar wind turbulence wisps
    tertiary = fine_grain((h, w), seed_eff + 75, freqs=(24, 48, 96), weights=(0.4, 0.4, 0.2))
    
    # Rich iridescent anodized pearl specification
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(210.0,  45.0,   0.0),
                          r_coeffs=(-110.0,  -60.0,  180.0), # highly reflective waves, rough voids
                          cc_coeffs=(-20.0, -10.0,  160.0),
                          m_base=30.0, r_base=35.0, cc_base=80.0)


def paint_p_aurora(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72404
    
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    
    wobble = multi_scale_noise((h, w), [12, 24], [0.65, 0.35], seed_eff) * (h * 0.15)
    curtain1 = np.sin((yf + wobble) * 0.022 * np.pi) * 0.5 + 0.5
    curtain2 = np.sin((yf + wobble * 0.8) * 0.038 * np.pi + 1.2) * 0.5 + 0.5
    primary = np.clip(curtain1 * 0.60 + curtain2 * 0.40, 0, 1).astype(np.float32)
    
    # stardust particles
    rng = np.random.RandomState(seed_eff + 10)
    stardust = (rng.uniform(0.0, 1.0, (h, w)) > 0.992).astype(np.float32)
    
    wisps = fine_grain((h, w), seed_eff + 75, freqs=(24, 48, 96), weights=(0.4, 0.4, 0.2))
    motif = np.clip(primary * 0.70 + stardust * 0.20 + wisps * 0.10, 0, 1)
    
    return compose_paint(paint, motif, _lut_b2("p_aurora"),
                          mask, pm, bb,
                          intensity=0.96, dark_zone_only=True,
                          dark_threshold=0.55)

# ===========================================================================
# 5. STEALTH (Hyper-detailed Carbon Fiber twill weave + tactical panels & micro-rivets)
# ===========================================================================

def spec_stealth(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72505
    n_facets, cell_id, seams = _stealth_fields((h, w), seed_eff)
    
    # Detailed 2D carbon fiber twill weave micro-grain (roughness variation field)
    y, x = get_mgrid((h, w))
    carbon_twill = (((y + x) // 2) % 2).astype(np.float32) * 0.25 + (((y - x) // 2) % 2).astype(np.float32) * 0.25
    primary = carbon_twill
    
    # Secondary: Seam hex-screws/rivets placed periodically along the seam lines
    seams_dithered = dithered_threshold(seams, 0.85, 0.1, seed_eff + 44)
    secondary = seams_dithered
    
    # Tertiary: Plate facet base modulation
    rng = np.random.RandomState(seed_eff + 99)
    facet_shades = rng.uniform(0.1, 0.6, n_facets + 1).astype(np.float32)
    facet_shades_field = facet_shades[np.clip(cell_id, 0, n_facets)]
    tertiary = facet_shades_field
    
    # Spec: Detail carbon weave (alternating smooth/rough to catch light), titanium seams/screws
    return _paradigm_spec((h, w), mask, sm,
                          primary, secondary, tertiary,
                          m_coeffs=(10.0,   240.0,  40.0), # screws/seams highly metallic (M=240)
                          r_coeffs=(80.0,   -120.0, 60.0), # carbon weave R ripples, seams mirror-smooth
                          cc_coeffs=(-15.0, 85.0,   120.0),
                          m_base=15.0, r_base=120.0, cc_base=50.0) # base plate matte tactical coating


def paint_stealth(paint, shape, mask, seed, pm, bb):
    h, w = _shape_hw(shape)
    seed_eff = int(seed) + 72505
    n_facets, cell_id, seams = _stealth_fields((h, w), seed_eff)
    
    # Facet shade modulation
    rng = np.random.RandomState(seed_eff + 99)
    facet_shades = rng.uniform(0.1, 0.5, n_facets + 1).astype(np.float32)
    plates = facet_shades[np.clip(cell_id, 0, n_facets)]
    
    # Twill carbon fiber micro-texture
    y, x = get_mgrid((h, w))
    carbon_twill = (((y + x) // 2) % 2).astype(np.float32) * 0.15 + (((y - x) // 2) % 2).astype(np.float32) * 0.15
    
    # Micro-screws spaced along seams
    seams_dithered = dithered_threshold(seams, 0.85, 0.1, seed_eff + 44)
    
    motif = np.clip(plates * 0.55 + carbon_twill * 0.25 + seams * 0.10 + seams_dithered * 0.10, 0, 1)
    
    # Composes tactical charcoal and olive military panels with carbon grain and titanium joints
    return compose_paint(paint, motif, _lut_b2("stealth"),
                          mask, pm, bb,
                          intensity=0.95, dark_zone_only=True,
                          dark_threshold=0.60)

# ===========================================================================
# Batch 2 Registry exports
# ===========================================================================

V3_BATCH2_SEEDS = {
    "quantum":     (spec_quantum,     paint_quantum),
    "magnetic":    (spec_magnetic,    paint_magnetic),
    "p_static":    (spec_p_static,    paint_p_static),
    "p_aurora":    (spec_p_aurora,    paint_p_aurora),
    "stealth":     (spec_stealth,     paint_stealth),
}
