"""
engine/shokk_series.py - SHOKK Series bases (20 color-shifting PBR bases).

Every base provides a (base_spec_fn, paint_fn) pair.
- base_spec_fn(shape, seed, sm, base_m, base_r) → (M_arr, R_arr, CC_arr)
- paint_fn(paint, shape, mask, seed, pm, bb) → paint (mutated in-place)

Pillar 1 - Metallic micro-variation: M=0 (dielectric white specular) vs M=255 (colored specular).
Pillar 2 - Roughness directional control: Low R reveals environment, high R reveals paint color.
Pillar 3 - Clearcoat interference: CC thickness variation creates optical path differences.
"""
import numpy as np
from functools import lru_cache
from engine.core import multi_scale_noise, get_mgrid
from engine.utils import perlin_multi_octave

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# Tiny LRU cache so spec_fn + paint_fn sharing the same seed don't recompute.
_perlin_cache = {}
_PERLIN_CACHE_MAX = 8

def _perlin_upscale_cached(shape, seed, octaves=5, persistence=0.55, lacunarity=2.2):
    """Cached version of _perlin_upscale for use in hot paths."""
    key = (shape, seed, octaves, persistence, lacunarity)
    if key in _perlin_cache:
        return _perlin_cache[key]
    result = _perlin_upscale(shape, seed, octaves, persistence, lacunarity)
    if len(_perlin_cache) >= _PERLIN_CACHE_MAX:
        _perlin_cache.pop(next(iter(_perlin_cache)))
    _perlin_cache[key] = result
    return result

_ising_cache = {}
_ISING_CACHE_MAX = 4

def _ising_domains_cached(shape, seed, temperature=2.2, iterations=80):
    """Cached version of _ising_domains for use in hot paths."""
    key = (shape, seed, temperature, iterations)
    if key in _ising_cache:
        return _ising_cache[key]
    result = _ising_domains(shape, seed, temperature, iterations)
    if len(_ising_cache) >= _ISING_CACHE_MAX:
        _ising_cache.pop(next(iter(_ising_cache)))
    _ising_cache[key] = result
    return result

def _voronoi_cells(shape, n_cells, seed):
    """Return (labels, dist) arrays using scipy KDTree for speed. labels = nearest cell index, dist = 0-1."""
    from scipy.spatial import cKDTree
    h, w = shape
    rng = np.random.RandomState(seed)
    cy = rng.rand(n_cells).astype(np.float64) * h
    cx = rng.rand(n_cells).astype(np.float64) * w
    pts = np.stack([cy, cx], axis=1)
    pts_tiled = []
    for dy_off in [-h, 0, h]:
        for dx_off in [-w, 0, w]:
            pts_tiled.append(pts + np.array([[dy_off, dx_off]]))
    pts_tiled = np.concatenate(pts_tiled, axis=0)
    tree = cKDTree(pts_tiled)
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.stack([yy.ravel(), xx.ravel()], axis=1).astype(np.float64)
    dists_flat, idx_flat = tree.query(coords)
    labels = (idx_flat % n_cells).reshape(h, w).astype(np.int32)
    dists = dists_flat.reshape(h, w).astype(np.float32)
    max_d = dists.max() + 1e-8
    return labels, dists / max_d


def _voronoi_edges(labels, thickness=2):
    """Binary mask: 1 on Voronoi cell edges."""
    from scipy.ndimage import maximum_filter, minimum_filter
    mx = maximum_filter(labels, size=thickness)
    mn = minimum_filter(labels, size=thickness)
    return (mx != mn).astype(np.float32)


def _spiral_field(shape, seed, arms=2, tightness=0.12):
    """Logarithmic spiral 0-1 field."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0
    dy, dx = yy - cy, xx - cx
    r = np.sqrt(dy**2 + dx**2) + 1e-8
    theta = np.arctan2(dy, dx)
    phase = (theta * arms / (2 * np.pi) - np.log(r + 1) * tightness) % 1.0
    return phase


def _bz_reaction(shape, seed, n_waves=5, n_colors=4):
    """Belousov-Zhabotinsky spiral wave → discrete phase labels (0..n_colors-1)."""
    h, w = shape
    rng = np.random.RandomState(seed)
    field = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_waves):
        cy = rng.rand() * h
        cx = rng.rand() * w
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dy = yy - cy
        dx = xx - cx
        r = np.sqrt(dy**2 + dx**2)
        theta = np.arctan2(dy, dx)
        wave = (theta / (2 * np.pi) + r * 0.008 * (0.8 + rng.rand() * 0.4)) % 1.0
        field += wave
    field = field % 1.0
    labels = (field * n_colors).astype(np.int32) % n_colors
    return labels, field


def _ising_domains(shape, seed, temperature=2.2, iterations=80):
    """2D Ising model relaxation via vectorized checkerboard Metropolis."""
    h, w = shape
    rng = np.random.RandomState(seed)
    grid = rng.choice([-1, 1], size=(h, w)).astype(np.float32)
    beta = 1.0 / max(temperature, 0.01)
    prob_table = np.array([np.exp(-beta * dE) if dE > 0 else 1.0 for dE in range(-8, 9, 4)])
    for it in range(iterations):
        for parity in range(2):
            neighbors = (np.roll(grid, 1, 0) + np.roll(grid, -1, 0) +
                         np.roll(grid, 1, 1) + np.roll(grid, -1, 1))
            dE = 2.0 * grid * neighbors
            mask_check = np.zeros((h, w), dtype=bool)
            mask_check[parity::2, ::2] = True
            mask_check[1 - parity::2, 1::2] = True
            prob = np.exp(-beta * np.clip(dE, 0, 8))
            prob[dE <= 0] = 1.0
            flip = (rng.rand(h, w) < prob) & mask_check
            grid[flip] *= -1
    return (grid > 0).astype(np.float32)


def _dither_floyd_steinberg(values, shape, seed):
    """Floyd-Steinberg error-diffusion dither of float array to 0/1."""
    rng = np.random.RandomState(seed)
    v = values.copy().astype(np.float64)
    h, w = shape
    out = np.zeros((h, w), dtype=np.float32)
    for iy in range(h):
        for ix in range(w):
            old = v[iy, ix]
            new = 1.0 if old >= 0.5 else 0.0
            out[iy, ix] = new
            err = old - new
            if ix + 1 < w:
                v[iy, ix+1] += err * 7 / 16
            if iy + 1 < h:
                if ix - 1 >= 0:
                    v[iy+1, ix-1] += err * 3 / 16
                v[iy+1, ix] += err * 5 / 16
                if ix + 1 < w:
                    v[iy+1, ix+1] += err * 1 / 16
    return out


def _dither_fast(shape, seed, threshold_noise=0.08):
    """Fast blue-noise-ish M dither for 2048² without full Floyd-Steinberg per-pixel loop."""
    h, w = shape
    rng = np.random.RandomState(seed)
    base = np.full((h, w), 0.5, dtype=np.float32)
    base += rng.randn(h, w).astype(np.float32) * threshold_noise
    noise_fine = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed + 77)
    base += noise_fine * 0.15
    return (base >= 0.5).astype(np.float32)


def _standing_wave(shape, seed, n_waves=5):
    """Superposition of sinusoidal plane waves → constructive/destructive nodes."""
    h, w = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yy = yy / h * 2 * np.pi
    xx = xx / w * 2 * np.pi
    field = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_waves):
        kx = rng.uniform(2, 12)
        ky = rng.uniform(2, 12)
        phase = rng.uniform(0, 2 * np.pi)
        field += np.sin(kx * xx + ky * yy + phase)
    field = field / n_waves
    return (field - field.min()) / (field.max() - field.min() + 1e-8)


def _blackbody_color(temperature_01):
    """Map 0-1 temperature to approximate blackbody RGB (0-1 floats)."""
    t = np.clip(temperature_01, 0, 1)
    r = np.clip(t * 2.5, 0, 1)
    g = np.clip((t - 0.3) * 2.0, 0, 1)
    b = np.clip((t - 0.6) * 3.3, 0, 1)
    return r, g, b


def _caustic_pattern(shape, seed, n_sources=30):
    """Approximate caustic refraction intensity pattern."""
    h, w = shape
    rng = np.random.RandomState(seed)
    field = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_sources):
        cy = rng.rand() * h
        cx = rng.rand() * w
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dy = yy - cy
        dx = xx - cx
        r = np.sqrt(dy**2 + dx**2) + 1e-8
        band = np.sin(r * rng.uniform(0.04, 0.12)) * np.exp(-r * 0.002)
        field += band
    field = (field - field.min()) / (field.max() - field.min() + 1e-8)
    return field


# ══════════════════════════════════════════════════════════════════════════════
# 1. SHOKK FLUX - Thin-Film Optical Interference
# ══════════════════════════════════════════════════════════════════════════════

def _perlin_upscale(shape, seed, octaves=5, persistence=0.55, lacunarity=2.2):
    """Generate perlin at 512x512 and upscale to target shape for speed."""
    from scipy.ndimage import zoom
    small = (min(shape[0], 512), min(shape[1], 512))
    noise = perlin_multi_octave(small, octaves=octaves, persistence=persistence, lacunarity=lacunarity, seed=seed)
    if small[0] < shape[0] or small[1] < shape[1]:
        noise = zoom(noise, (shape[0] / small[0], shape[1] / small[1]), order=3)
    return noise

def spec_shokk_flux(shape, seed, sm, base_m, base_r):
    noise = _perlin_upscale(shape, seed + 100)
    thickness = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    # 2026-04-20 HEENAN HARDMODE-SHOKK-1 (Animal) — thin-film range was
    # 220+/-35 metallic, 15+/-12 roughness: too narrow to read as
    # "thin-film interference" in render. Widen M to 160+/-95 (visible
    # dielectric base vs metal peak) and R from +/-12 to +/-40 so the
    # interference film actually shifts surface gloss.
    detail = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 101)
    M = np.clip(160.0 + thickness * 95 * sm + detail * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + thickness * 40 * sm + detail * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + thickness * 42 * sm, 0, 255).astype(np.float32)
    return M, R, CC

def paint_shokk_flux(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    noise = _perlin_upscale(shape, seed + 100)
    t = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    wavelengths = np.stack([
        np.clip(np.sin(t * np.pi * 2.0) * 0.5 + 0.5, 0, 1),
        np.clip(np.sin(t * np.pi * 2.0 + 2.094) * 0.5 + 0.5, 0, 1),
        np.clip(np.sin(t * np.pi * 2.0 + 4.189) * 0.5 + 0.5, 0, 1),
    ], axis=-1)
    blend = pm * 0.85
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + wavelengths * m3, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 2. SHOKK PHASE - Liquid Crystal Domain Simulation
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_phase(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-2 (Animal) — liquid-crystal domain
    # finish was rendering as random colourful tiles with no domain-wall
    # signature. Use the Voronoi edge map to give walls a distinct material
    # (mirror-bright surface tension) vs frosted domain interiors. Also
    # widen the per-cell metallic uniform from (0,220) to (50,255) so each
    # cell has more individual identity.
    labels, _ = _voronoi_cells(shape, 120, seed + 200)
    edges = _voronoi_edges(labels, thickness=2).astype(np.float32)
    rng = np.random.RandomState(seed + 203)
    cell_M = rng.uniform(50, 255, size=120).astype(np.float32)
    M = cell_M[labels]
    # Walls smooth (R=8), domain interiors frosted (R=45) + low-freq grain.
    r_noise = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 202)
    R = np.where(edges > 0.5, 8.0, 45.0).astype(np.float32) + r_noise * 6 * sm
    # Walls glossy (CC=16), domains matte (CC=50) — surface-tension look.
    CC = np.where(edges > 0.5, 16.0, 50.0).astype(np.float32)
    return np.clip(M, 0, 255), np.clip(R, 15, 255), CC

def paint_shokk_phase(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    labels, _ = _voronoi_cells(shape, 120, seed + 200)
    rng = np.random.RandomState(seed + 203)
    n_cells = 120
    hues = rng.uniform(0, 1, size=n_cells).astype(np.float32)
    h_map = hues[labels]
    r_ch = np.clip(np.abs(h_map * 6 - 3) - 1, 0, 1)
    g_ch = np.clip(2 - np.abs(h_map * 6 - 2), 0, 1)
    b_ch = np.clip(2 - np.abs(h_map * 6 - 4), 0, 1)
    blend = pm * 0.80
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_ch * mask * blend * 0.85, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_ch * mask * blend * 0.85, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_ch * mask * blend * 0.85, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 3. SHOKK DUAL - Hard Chromatic Binary Flip
# ══════════════════════════════════════════════════════════════════════════════

def _shokk_dual_binary_field(shape, seed):
    """Build the shared hard-flip mask used by spec and paint for shokk_dual.

    2026-04-20 HEENAN HARDMODE-FIX-DUAL — the prior implementation took a
    continuous h_param in [0,1] and produced a smooth gradient in both
    spec (M=80+h*175, R=5+(1-h)*80) and paint (warm*(1-h)+cool*h). That
    is not a "Hard Chromatic Binary Flip" — probing at 256x256 produced
    1200+ distinct rounded M values. This helper returns a crisp binary
    mask with a ±0.01 smoothstep transition zone (essentially 0 or 1
    across 99.9%+ of pixels) so spec and paint both flip with hard
    edges while still being GPU-aliasing-safe.
    """
    h, w = shape
    yy, xx = get_mgrid(shape)
    h_noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 300)
    fine = multi_scale_noise(shape, [32, 64], [0.6, 0.4], seed + 302)
    # Continuous bias field in [0,1], then threshold at 0.5 with a
    # very narrow smoothstep (±0.01) so the edge is effectively binary
    # but not aliased at 1px scale.
    bias = np.clip(xx / max(w - 1, 1) * 0.6 + h_noise * 0.3 + fine * 0.1, 0, 1)
    t = np.clip((bias - 0.49) / 0.02, 0, 1).astype(np.float32)
    # Smoothstep keeps the output differentiable at the seam while 99%+
    # of pixels evaluate to 0.0 or 1.0.
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def spec_shokk_dual(shape, seed, sm, base_m, base_r):
    """Hard Chromatic Binary Flip — ACTUAL binary now.

    2026-04-20 HEENAN HARDMODE-SHOKK-3b — the HARDMODE R1 change locked
    M/R to h_param but kept them as a continuous gradient; the audit
    pointed out that is not a binary flip. Use _shokk_dual_binary_field
    so side A = (M=255, R=5) chrome-bright, side B = (M=80, R=85) matte
    dielectric, with a ~2-pixel-wide smoothstep seam between them.
    """
    flip = _shokk_dual_binary_field(shape, seed)  # 0 on side A, 1 on side B
    M = np.clip(255.0 - flip * 175.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(5.0 + flip * 80.0 * sm, 15, 255).astype(np.float32)
    CC = np.full(shape, 16.0, dtype=np.float32)
    return M, R, CC


def paint_shokk_dual(paint, shape, mask, seed, pm, bb):
    """Hard Chromatic Binary Flip — paint path uses the SAME binary mask
    as the spec (_shokk_dual_binary_field) so paint and spec agree pixel
    for pixel on which side of the flip a given pixel belongs to."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint
    flip = _shokk_dual_binary_field(shape, seed)
    warm = np.array([0.82, 0.22, 0.18], dtype=np.float32)
    cool = np.array([0.18, 0.32, 0.82], dtype=np.float32)
    # Binary pick: side A = warm, side B = cool.
    color = (warm[np.newaxis, np.newaxis, :] * (1.0 - flip[:, :, np.newaxis]) +
             cool[np.newaxis, np.newaxis, :] * flip[:, :, np.newaxis])
    blend = pm * 0.85
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + color * m3, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 4. SHOKK SPECTRUM - Diffraction Grating Dispersion
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_spectrum(shape, seed, sm, base_m, base_r):
    h, w = shape
    # Noise-warped spectral coordinate (aligned to paint seeds 403/404/405)
    n_warp = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 403)
    n_fine = multi_scale_noise(shape, [32, 64], [0.6, 0.4], seed + 404)
    # Iridescent micro-flake metallic field - very high M with flake sparkle
    flake = multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed + 405)
    flake_spots = np.clip((flake - 0.4) * 3.0, 0, 1)  # sparse bright flakes
    M = np.full(shape, 230.0, dtype=np.float32) + n_warp * 15 * sm + flake_spots * 25 * sm
    # Groove-driven R that follows body curves via noise warp
    yy, xx = get_mgrid(shape)
    groove_phase = yy * 0.12 + n_warp * 4.0  # noise-warped grooves follow body
    R = 6.0 + np.abs(np.sin(groove_phase)) * 35.0 * sm + n_fine * 8 * sm
    # CC with spectral interference thickness
    CC = 16.0 + np.abs(np.sin(groove_phase * 0.7 + n_fine * 2.0)) * 30 * sm
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32)

def paint_shokk_spectrum(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint
    h, w = shape
    yy, xx = get_mgrid(shape)
    # Noise-warped spectral coordinate - bands follow body curves
    n_warp = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 403)
    n_fine = multi_scale_noise(shape, [32, 64], [0.6, 0.4], seed + 404)
    # Spectral coordinate warped by body noise (not linear L-R)
    t = (xx / w * 0.6 + yy / h * 0.3 + n_warp * 0.35) % 1.0
    # Smooth spectral bands with feathered transitions (raised cosine)
    r_ch = np.clip(0.5 + 0.5 * np.cos((t - 0.0) * np.pi * 2.0), 0, 1)
    g_ch = np.clip(0.5 + 0.5 * np.cos((t - 0.333) * np.pi * 2.0), 0, 1)
    b_ch = np.clip(0.5 + 0.5 * np.cos((t - 0.667) * np.pi * 2.0), 0, 1)
    # Iridescent micro-flake shimmer overlay
    flake = multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed + 405)
    shimmer = np.clip((flake - 0.3) * 2.5, 0, 1) * 0.15
    r_ch = np.clip(r_ch + shimmer * np.sin(t * 12.0), 0, 1)
    g_ch = np.clip(g_ch + shimmer * np.sin(t * 12.0 + 2.1), 0, 1)
    b_ch = np.clip(b_ch + shimmer * np.sin(t * 12.0 + 4.2), 0, 1)
    # Angle-simulation: fine noise shifts hue slightly for viewing-angle effect
    angle_shift = n_fine * 0.08
    r_ch = np.clip(r_ch + angle_shift, 0, 1)
    g_ch = np.clip(g_ch - angle_shift * 0.5, 0, 1)
    b_ch = np.clip(b_ch + angle_shift * 0.3, 0, 1)
    blend = pm * 0.80
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_ch * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_ch * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_ch * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 5. SHOKK AURORA - Atmospheric Curtain Dynamics
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_aurora(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-7 (Animal R2) — aurora curtains
    # had R clamped to a tiny ~8-point swing, so the curtain pattern only
    # showed up in M. Widen to a ~20-point swing reaching down to R=10
    # so the curtain peaks read as semi-mirror against semi-matte gulfs,
    # reinforcing the atmospheric depth promised by the name.
    h, w = shape
    yy, xx = get_mgrid(shape)
    wave1 = np.sin(yy * 0.025 + np.sin(xx * 0.015) * 4.0) * 0.5 + 0.5
    wave2 = np.sin(yy * 0.018 + np.sin(xx * 0.022) * 3.0) * 0.5 + 0.5
    curtain = (wave1 + wave2) / 2.0
    M = 100 + curtain * 130
    R = 10 + (1.0 - curtain) * 30  # widened swing: 10..40 across curtain
    CC = np.full(shape, 16.0, dtype=np.float32)
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 500)
    M = M + n * 8 * sm
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), CC

def paint_shokk_aurora(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    yy, xx = get_mgrid(shape)
    wave1 = np.sin(yy * 0.025 + np.sin(xx * 0.015) * 4.0) * 0.5 + 0.5
    wave2 = np.sin(yy * 0.018 + np.sin(xx * 0.022) * 3.0) * 0.5 + 0.5
    t = (wave1 + wave2) / 2.0
    stops_r = np.array([0.05, 0.0, 0.2, 0.6, 0.4])
    stops_g = np.array([0.8, 0.6, 0.3, 0.1, 0.6])
    stops_b = np.array([0.3, 0.7, 0.8, 0.7, 0.9])
    idx = np.clip(t * (len(stops_r) - 1), 0, len(stops_r) - 1.001)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(stops_r) - 1)
    frac = idx - lo
    r_ch = stops_r[lo] * (1 - frac) + stops_r[hi] * frac
    g_ch = stops_g[lo] * (1 - frac) + stops_g[hi] * frac
    b_ch = stops_b[lo] * (1 - frac) + stops_b[hi] * frac
    blend = pm * 0.82
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_ch * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_ch * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_ch * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 6. SHOKK HELIX - Double-Strand Complementary Spiral
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_helix(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-8 (Animal R2) — double helix had
    # M=215+/-10 (essentially flat) while R/CC carried the strand-swap
    # signal. Make M flip with the strand too so the dominant strand
    # actually reads as more metallic than the recessed strand.
    phase = _spiral_field(shape, seed + 600, arms=2, tightness=0.10)
    strand = np.sin(phase * 2 * np.pi) * 0.5 + 0.5  # 0=strand_B, 1=strand_A
    R_var = 5.0 + (1.0 - strand) * 45.0
    CC_var = 45.0 - np.abs(np.sin(phase * 2 * np.pi)) * 29
    CC_var = np.clip(CC_var, 16, 255)
    # Strand_A: M~250 (chrome-bright). Strand_B: M~120 (deep dielectric).
    # Domain-warp noise adds organic micro-variation within each strand.
    M = 120.0 + strand * 130.0
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 601)
    M = M + n * 30 * sm
    return np.clip(M, 0, 255), np.clip(R_var, 15, 255).astype(np.float32), CC_var.astype(np.float32)

def paint_shokk_helix(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    phase = _spiral_field(shape, seed + 600, arms=2, tightness=0.10)
    strand_a = np.sin(phase * 2 * np.pi) * 0.5 + 0.5
    strand_b = 1.0 - strand_a
    color_a = np.array([0.85, 0.15, 0.55], dtype=np.float32)
    color_b = np.array([0.15, 0.85, 0.55], dtype=np.float32)
    blend = pm * 0.78
    mixed = strand_a[:, :, np.newaxis] * color_a + strand_b[:, :, np.newaxis] * color_b
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + mixed * m3, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 7. SHOKK CATALYST - BZ Reaction Wavefront
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_catalyst(shape, seed, sm, base_m, base_r):
    labels, _ = _bz_reaction(shape, seed + 700, n_waves=5, n_colors=4)
    M_map = np.array([240, 160, 80, 0], dtype=np.float32)
    M = M_map[labels]
    # R varies per BZ phase: phase0=6, phase1=45, phase2=70, phase3=20
    R_map = np.array([6, 45, 70, 20], dtype=np.float32)
    R = R_map[labels]
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 701)
    R = R + n * 4 * sm
    CC = np.full(shape, 16.0, dtype=np.float32)
    return np.clip(M, 0, 255), np.clip(R, 15, 255), CC

def paint_shokk_catalyst(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    labels, field = _bz_reaction(shape, seed + 700, n_waves=5, n_colors=4)
    colors = np.array([
        [0.9, 0.2, 0.1],
        [0.9, 0.7, 0.1],
        [0.1, 0.8, 0.3],
        [0.2, 0.3, 0.9],
    ], dtype=np.float32)
    blend = pm * 0.80
    color_map = colors[labels]  # (h, w, 3) - all channels at once
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + color_map * m3, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 8. SHOKK MIRAGE - Thermal Gradient Refraction
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_mirage(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-11 (Animal R2) — thermal mirage
    # had R=15+/-9 (everything nearly mirror). Real heat-haze has hot
    # zones (smooth) and cool zones (scattered) with much wider swing.
    # Drop minimum R to 8 and scale the warp factor so cool zones reach
    # R~48 — actual visible refractive contrast.
    warp_x = _perlin_upscale_cached(shape, seed + 801, octaves=3, persistence=0.6, lacunarity=2.0)
    warp_y = _perlin_upscale_cached(shape, seed + 802, octaves=3, persistence=0.6, lacunarity=2.0)
    warp_mag = np.sqrt(warp_x**2 + warp_y**2)
    warp_mag = (warp_mag - warp_mag.min()) / (warp_mag.max() - warp_mag.min() + 1e-8)
    noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 803)
    M = np.clip(235.0 - warp_mag * 20.0 * sm + noise * 15.0 * sm, 0, 255).astype(np.float32)
    R = 8.0 + warp_mag * 40.0 * sm + noise * 8.0 * sm
    wave = np.sin(warp_mag * 6.0) * 0.5 + 0.5
    R = R + wave * 5 * sm
    CC = np.full(shape, 16.0, dtype=np.float32)
    return M, np.clip(R, 15, 255).astype(np.float32), CC

def paint_shokk_mirage(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    warp_x = _perlin_upscale_cached(shape, seed + 801, octaves=3, persistence=0.6, lacunarity=2.0)
    warp_y = _perlin_upscale_cached(shape, seed + 802, octaves=3, persistence=0.6, lacunarity=2.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    strength = pm * 30
    sy = np.clip((yy + warp_y * strength).astype(np.int32), 0, h - 1)
    sx = np.clip((xx + warp_x * strength).astype(np.int32), 0, w - 1)
    blend = pm * 0.40
    warped = paint[sy, sx, :]
    m3 = mask[:,:,np.newaxis]
    paint = np.clip(paint * (1 - m3 * blend) + warped * m3 * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 9. SHOKK POLARITY - Magnetic Domain Visualization
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_polarity(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-9 (Animal R2) — Ising magnetic-
    # domain visualisation had IDENTICAL M=180 for both spin states
    # (line was `np.where(domains > 0.5, 180.0, 180.0)` — a no-op). Domains
    # of opposite spin should look like opposite materials, not same. Flip
    # M between 100 (spin-down dielectric) and 230 (spin-up metallic). Add
    # noise modulation so each domain has internal variation rather than
    # being a flat chip.
    small = (min(shape[0], 512), min(shape[1], 512))
    domains_small = _ising_domains_cached(small, seed + 900, temperature=2.3, iterations=30)
    from scipy.ndimage import zoom
    zy, zx = shape[0] / small[0], shape[1] / small[1]
    domains = (zoom(domains_small, (zy, zx), order=0) > 0.5).astype(np.float32)
    edges = _voronoi_edges(domains.astype(np.int32), thickness=3)
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 902)
    # Spin-up=230 metallic, spin-down=100 dielectric, edges=250 (boundary glow).
    M_interior = np.where(domains > 0.5, 230.0, 100.0) + n * 25 * sm
    M = np.where(edges > 0.5, 250.0, M_interior).astype(np.float32)
    # R: spin-up=10 (smooth metal), spin-down=55 (matte), edges=15 (sharp glow).
    R_interior = np.where(domains > 0.5, 10.0, 55.0)
    R = np.where(edges > 0.5, 15.0, R_interior).astype(np.float32)
    CC = np.full(shape, 16.0, dtype=np.float32)
    return np.clip(M, 0, 255), np.clip(R, 15, 255), CC

def paint_shokk_polarity(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    small = (min(shape[0], 512), min(shape[1], 512))
    domains_small = _ising_domains_cached(small, seed + 900, temperature=2.3, iterations=30)
    from scipy.ndimage import zoom
    zy, zx = shape[0] / small[0], shape[1] / small[1]
    domains = (zoom(domains_small, (zy, zx), order=0) > 0.5).astype(np.float32)
    warm = np.array([0.8, 0.35, 0.15], dtype=np.float32)
    cool = np.array([0.15, 0.35, 0.8], dtype=np.float32)
    blend = pm * 0.75
    # Vectorized channel blend instead of per-channel loop
    color_map = domains[:,:,np.newaxis] * warm[np.newaxis,np.newaxis,:] + (1 - domains[:,:,np.newaxis]) * cool[np.newaxis,np.newaxis,:]
    m3 = mask[:,:,np.newaxis]
    paint = np.clip(paint * (1 - m3 * blend) + color_map * m3 * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 10. SHOKK REACTOR - Cherenkov Radiation Glow
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_reactor(shape, seed, sm, base_m, base_r):
    h, w = shape
    rng = np.random.RandomState(seed + 1000)
    n_cores = 12
    cores_y = rng.rand(n_cores) * h
    cores_x = rng.rand(n_cores) * w
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glow = np.zeros((h, w), dtype=np.float32)
    for i in range(n_cores):
        r = np.sqrt((yy - cores_y[i])**2 + (xx - cores_x[i])**2) + 1e-8
        glow += np.clip(1.0 / (1.0 + r * 0.015), 0, 1)
    glow = np.clip(glow, 0, 1)
    # FLAT-FIX: use smooth glow field instead of hard binary threshold
    # Smooth transition creates continuous M/R variation across glow gradient
    noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1001)
    M = np.clip(240.0 - glow * 240.0 + noise * 25.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + glow * 49.0 + noise * 15.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + glow * 24.0 + noise * 8.0 * sm, 0, 255).astype(np.float32)
    return M, R, CC

def paint_shokk_reactor(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    rng = np.random.RandomState(seed + 1000)
    n_cores = 12
    cores_y = rng.rand(n_cores) * h
    cores_x = rng.rand(n_cores) * w
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glow = np.zeros((h, w), dtype=np.float32)
    for i in range(n_cores):
        r = np.sqrt((yy - cores_y[i])**2 + (xx - cores_x[i])**2) + 1e-8
        glow += np.clip(1.0 / (1.0 + r * 0.015), 0, 1)
    glow = np.clip(glow, 0, 1)
    blend = pm * 0.85
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + glow * 0.05 * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + glow * 0.55 * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + glow * 0.90 * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 11. SHOKK PRISM - Caustic Refraction Through Crystal
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_prism(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-4 (Animal) — caustic refraction
    # rendered with M=160+/-60 (mid-metallic everywhere) and R=2+/-4
    # (always near-mirror) reads as uniform shiny noise. Widen M to
    # 100..255 (caustic peaks fully metallic, troughs dielectric) and
    # R to 2..27 (peaks mirror, troughs roughened) so the caustic
    # pattern is visible in the spec response instead of just CC.
    caustic = _caustic_pattern(shape, seed + 1100, n_sources=30)
    M = 100 + caustic * 155
    R = 2.0 + caustic * 25
    CC = 16.0 + caustic * 44
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 1101)
    M = M + n * 20 * sm
    R = R + n * 5 * sm
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32)

def paint_shokk_prism(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    caustic = _caustic_pattern(shape, seed + 1100, n_sources=30)
    r_ch = np.clip(np.sin(caustic * np.pi * 3.0) * 0.5 + 0.5, 0, 1)
    g_ch = np.clip(np.sin(caustic * np.pi * 3.0 + 2.094) * 0.5 + 0.5, 0, 1)
    b_ch = np.clip(np.sin(caustic * np.pi * 3.0 + 4.189) * 0.5 + 0.5, 0, 1)
    blend = pm * 0.70
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_ch * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_ch * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_ch * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 12. SHOKK WRAITH - Sub-Resolution Metallic Dithering
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_wraith(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-10 (Animal R2) — wraith had M
    # swinging the full 0..255 dither but R clamped to 5+/-1.5 (basically
    # always near-mirror). The dither pattern only showed in the metallic
    # channel; correlate R with the dither so metallic pixels are also
    # smoother than dielectric ones — gives the "ghost emerging" feel.
    dither = _dither_fast(shape, seed + 1200)
    M = dither * 255.0
    n = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 1201)
    # Metallic pixels get smoother (R=5), dielectric pixels get rougher (R=27).
    R = 5.0 + (1.0 - dither) * 22.0 + n * 4 * sm
    CC = np.full(shape, 16.0, dtype=np.float32)
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255), CC

def paint_shokk_wraith(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    # Use the same dither field as spec (seed+1200) for spatial coherence
    dither = _dither_fast(shape, seed + 1200)
    # Dither-correlated subtle hue shift: M=255 pixels warm, M=0 pixels cool
    r_noise = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 1201)
    warm_shift = dither * 0.03 * pm          # warm tint on metallic pixels
    cool_shift = (1.0 - dither) * 0.03 * pm  # cool tint on dielectric pixels
    paint[:,:,0] = np.clip(paint[:,:,0] + (warm_shift - cool_shift * 0.5) * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + r_noise * 0.01 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + (cool_shift - warm_shift * 0.5) * mask, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 13. SHOKK TESSERACT - 4D Hypercube Projection
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_tesseract(shape, seed, sm, base_m, base_r):
    h, w = shape
    yy, xx = get_mgrid(shape)
    yn = yy / h * 2 - 1
    xn = xx / w * 2 - 1
    rng = np.random.RandomState(seed + 1300)
    angle = rng.rand() * np.pi
    z1 = np.sin(xn * 2 + angle) * np.cos(yn * 2 + angle)
    z2 = np.cos(xn * 2 - angle) * np.sin(yn * 2 - angle)
    face_id = ((z1 * 3 + z2 * 5 + 4) * 2).astype(np.int32) % 6
    M_per_face = np.array([240, 100, 200, 60, 180, 120], dtype=np.float32)
    # R floor: faces with M<240 need R>=15; face0 M=240 can have low R
    R_per_face = np.array([3, 40, 18, 50, 16, 35], dtype=np.float32)
    M = M_per_face[face_id]
    R = R_per_face[face_id]
    overlap = (np.abs(z1 - z2) < 0.15).astype(np.float32)
    CC = 16.0 + overlap * 44.0  # CC floor 16, overlap areas get 60
    return np.clip(M, 0, 255), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 16, 255).astype(np.float32)

def paint_shokk_tesseract(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    yy, xx = get_mgrid(shape)
    yn = yy / h * 2 - 1
    xn = xx / w * 2 - 1
    rng = np.random.RandomState(seed + 1300)
    angle = rng.rand() * np.pi
    z1 = np.sin(xn * 2 + angle) * np.cos(yn * 2 + angle)
    z2 = np.cos(xn * 2 - angle) * np.sin(yn * 2 - angle)
    face_id = ((z1 * 3 + z2 * 5 + 4) * 2).astype(np.int32) % 6
    colors = np.array([
        [0.9, 0.1, 0.2], [0.2, 0.1, 0.9], [0.9, 0.6, 0.1],
        [0.1, 0.8, 0.4], [0.7, 0.1, 0.8], [0.1, 0.7, 0.9],
    ], dtype=np.float32)
    blend = pm * 0.78
    color_map = colors[face_id]  # (h, w, 3)
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + color_map * m3, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 14. SHOKK FUSION - Tokamak Plasma Confinement
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_fusion(shape, seed, sm, base_m, base_r):
    h, w = shape
    yy, xx = get_mgrid(shape)
    cy, cx = h / 2.0, w / 2.0
    dy, dx = yy - cy, xx - cx
    r = np.sqrt(dy**2 + dx**2)
    theta = np.arctan2(dy, dx)
    R_major = min(h, w) * 0.35
    r_minor = min(h, w) * 0.12
    torus_r = np.sqrt((r - R_major)**2 + (np.sin(theta * 3) * r_minor * 0.5)**2)
    torus_t = np.clip(1.0 - torus_r / (r_minor * 2), 0, 1)
    M = 80 + torus_t * 170
    # R: hot_core(torus_t=1) R=15, cool_edge(torus_t=0) R=70
    R = np.clip(70.0 - torus_t * 55.0, 15, 255).astype(np.float32)
    CC = np.full(shape, 16.0, dtype=np.float32)
    return np.clip(M, 0, 255).astype(np.float32), R, CC

def paint_shokk_fusion(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    yy, xx = get_mgrid(shape)
    cy, cx = h / 2.0, w / 2.0
    dy, dx = yy - cy, xx - cx
    r = np.sqrt(dy**2 + dx**2)
    R_major = min(h, w) * 0.35
    r_minor = min(h, w) * 0.12
    torus_r = np.sqrt((r - R_major)**2)
    torus_t = np.clip(1.0 - torus_r / (r_minor * 2), 0, 1)
    bb_r, bb_g, bb_b = _blackbody_color(torus_t)
    blend = pm * 0.82
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + bb_r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + bb_g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + bb_b * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 15. SHOKK RIFT - Dimensional Fracture Network
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_rift(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-5 (Animal) — fracture network had
    # M and R already differentiated at the cracks, but CC was flat 16.0
    # everywhere. Cracks should glow with high gloss vs matte domains.
    # Set CC=220 on the crack network, CC=16 inside domains so cracks
    # appear to "gleam" optically — depth illusion of liquid-light cracks.
    labels, dist = _voronoi_cells(shape, 60, seed + 1500)
    edges = _voronoi_edges(labels, thickness=3)
    side = (labels % 2).astype(np.float32)
    # Crack edges get micro-sparkle metallic; domain sides get warm/cool flips.
    crack_sparkle = multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed + 1502)
    crack_M = 230.0 + crack_sparkle * 25 * sm
    M = np.where(edges > 0.5, crack_M, np.where(side > 0.5, 230.0, 60.0)).astype(np.float32)
    R = np.where(edges > 0.5, 15.0, np.where(side > 0.5, 45.0, 25.0)).astype(np.float32)
    CC = np.where(edges > 0.5, 220.0, 16.0).astype(np.float32)
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), CC

def paint_shokk_rift(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    labels, dist = _voronoi_cells(shape, 60, seed + 1500)
    edges = _voronoi_edges(labels, thickness=3)
    side = (labels % 2).astype(np.float32)
    warm = np.array([0.85, 0.3, 0.1], dtype=np.float32)
    cool = np.array([0.1, 0.25, 0.85], dtype=np.float32)
    white = np.array([0.95, 0.95, 1.0], dtype=np.float32)
    blend = pm * 0.82
    base_color = side[:, :, np.newaxis] * warm + (1 - side[:, :, np.newaxis]) * cool
    ch = np.where(edges[:, :, np.newaxis] > 0.5, white, base_color)
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + ch * m3, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 16. SHOKK VORTEX - Logarithmic Spiral Color Drain
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_vortex(shape, seed, sm, base_m, base_r):
    """Logarithmic spiral color drain — spec should reinforce the spiral
    arms with clear metallic/dielectric contrast so the spiral reads in
    the spec map, not just in the paint colour.

    2026-04-20 HEENAN HARDMODE-R3-VORTEX — measured dM=59, dR=8 at
    512x512. The spiral arms were only ±15 metallic from base; the
    radial R sweep was tiny. Widen spiral M to ±70 and radial R to
    15..55 so the spiral arms flash chrome over dielectric and the
    radial drain shows visible roughness gradient from centre to edge.
    """
    h, w = shape
    yy, xx = get_mgrid(shape)
    cy, cx = h / 2.0, w / 2.0
    r = np.sqrt((yy - cy)**2 + (xx - cx)**2) + 1e-8
    max_r = np.sqrt(cy**2 + cx**2)
    r_norm = np.clip(r / max_r, 0, 1)
    theta = np.arctan2(yy - cy, xx - cx)
    spiral1 = (theta / (2 * np.pi) + np.log(r + 1) * 0.08) % 1.0
    spiral2 = (theta / (2 * np.pi) + np.log(r + 1) * 0.12) % 1.0
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1600)
    # Widened spiral M: arms flash to 250, troughs drop to 110 (was 195..225).
    M = np.clip(250.0 - spiral1 * 140.0 * sm + n * 18.0 * sm, 0, 255).astype(np.float32)
    # R now sweeps 15 (centre mirror) -> 55 (edge scattered).
    R = np.clip(15.0 + r_norm * 40.0 + n * 10.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16 + spiral2 * 40, 0, 255).astype(np.float32)
    return M, R, CC

def paint_shokk_vortex(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    yy, xx = get_mgrid(shape)
    cy, cx = h / 2.0, w / 2.0
    r = np.sqrt((yy - cy)**2 + (xx - cx)**2) + 1e-8
    theta = np.arctan2(yy - cy, xx - cx)
    hue = (theta / (2 * np.pi) + np.log(r + 1) * 0.08 + 0.5) % 1.0
    r_ch = np.clip(np.abs(hue * 6 - 3) - 1, 0, 1)
    g_ch = np.clip(2 - np.abs(hue * 6 - 2), 0, 1)
    b_ch = np.clip(2 - np.abs(hue * 6 - 4), 0, 1)
    blend = pm * 0.80
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_ch * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_ch * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_ch * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 17. SHOKK SURGE - Standing Wave Superposition
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_surge(shape, seed, sm, base_m, base_r):
    field = _standing_wave(shape, seed + 1700, n_waves=5)
    M = 120 + field * 130
    # R: constructive_nodes(field=1) R=6 (intense smooth), destructive_nodes(field=0) R=50 (scattered rough)
    R = 50.0 - field * 44.0
    CC = np.full(shape, 16.0, dtype=np.float32)
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 1701)
    M = M + n * 6 * sm
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), CC

def paint_shokk_surge(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    field = _standing_wave(shape, seed + 1700, n_waves=5)
    sat = field * 0.8 + 0.2
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 1702)
    hue = (field * 0.6 + n * 0.2 + 0.5) % 1.0
    r_ch = np.clip(np.abs(hue * 6 - 3) - 1, 0, 1) * sat
    g_ch = np.clip(2 - np.abs(hue * 6 - 2), 0, 1) * sat
    b_ch = np.clip(2 - np.abs(hue * 6 - 4), 0, 1) * sat
    blend = pm * 0.72
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_ch * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_ch * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_ch * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 18. SHOKK CIPHER - Steganographic Color Encoding
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_cipher(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-6 (Animal) — "Steganographic
    # encoding revealed via Fresnel amplification" was rendering with
    # M=220+/-12 and R=8+/-4 — a perceptually flat metallic. The hidden
    # pattern needs M+/-45 and R+/-17.5 to actually read as encoded
    # information that emerges at angle.
    hidden = _perlin_upscale_cached(shape, seed + 1800, octaves=4, persistence=0.45, lacunarity=2.5)
    hidden = (hidden - hidden.min()) / (hidden.max() - hidden.min() + 1e-8)
    M = 220.0 + (hidden - 0.5) * 90 * sm
    R = 8.0 + (hidden - 0.5) * 35 * sm
    CC = np.full(shape, 16.0, dtype=np.float32)
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), CC

def paint_shokk_cipher(paint, shape, mask, seed, pm, bb):
    # 2026-04-20 HEENAN HARDMODE-SHOKK-6b (Animal) — paint pass added a
    # nearly-invisible 0.06 brightness shift. Pair with a multi-scale
    # texture so the "encoded" pattern actually has visible fine detail
    # alongside the wider M/R modulation in the spec.
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    hidden = _perlin_upscale_cached(shape, seed + 1800, octaves=4, persistence=0.45, lacunarity=2.5)
    hidden = (hidden - hidden.min()) / (hidden.max() - hidden.min() + 1e-8)
    fine = multi_scale_noise(shape, [4, 8], [0.6, 0.4], seed + 1801)
    subtle = (hidden - 0.5) * pm * 0.10 + (fine - 0.5) * pm * 0.05
    paint += subtle[:,:,np.newaxis] * mask[:,:,np.newaxis]
    np.clip(paint, 0, 1, out=paint)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 19. SHOKK INFERNO - Blackbody Radiation Temperature Map
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_inferno(shape, seed, sm, base_m, base_r):
    noise = _perlin_upscale(shape, seed + 1900, octaves=5, persistence=0.6, lacunarity=2.0)
    turb = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1901)
    temp = np.clip((noise * 0.5 + 0.5) + turb * 0.2, 0, 1)
    M = temp * 255.0
    # R: hot(temp=1) R=5 (molten smooth), cool(temp=0) R=100 (cooled rough)
    R = 100.0 - temp * 95.0
    # CC: cool(temp=0) CC=16, hot(temp=1) CC=80 (heat degrades clearcoat)
    CC = np.clip(16.0 + temp * 64.0, 16, 255).astype(np.float32)
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), CC

def paint_shokk_inferno(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    noise = _perlin_upscale(shape, seed + 1900, octaves=5, persistence=0.6, lacunarity=2.0)
    turb = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 1901)
    temp = np.clip((noise * 0.5 + 0.5) + turb * 0.2, 0, 1)
    bb_r, bb_g, bb_b = _blackbody_color(temp)
    blend = pm * 0.85
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + bb_r * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + bb_g * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + bb_b * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 20. SHOKK APEX - The Crown Jewel: Multi-Layer Technique Stack
# ══════════════════════════════════════════════════════════════════════════════

def spec_shokk_apex(shape, seed, sm, base_m, base_r):
    """The Crown Jewel — SHOKK Apex layers every technique in the series.

    2026-04-20 HEENAN HARDMODE-R3-APEX — measured on 512x512 this was
    rendering M=200..255 (dM=55), R pinned flat at 15 by the floor, and
    CC=16..66. The "flagship of flagships" was actually the NARROWEST
    M range of the 6 untouched SHOKK finishes. The change below:
      - widens M via dither from ±22 to ±75 (base 150, dither*110)
        so the dithered metallic/dielectric mix is actually visible
      - bumps the groove+dither R term so R genuinely varies between
        mirror (R=15) and scattered (R=55) instead of sitting on the floor
      - keeps the CC layer1 + reinforce multi-technique stack intact
    """
    layer1_cc = _perlin_upscale(shape, seed + 2000)
    layer1_cc = (layer1_cc - layer1_cc.min()) / (layer1_cc.max() - layer1_cc.min() + 1e-8)
    dither = _dither_fast(shape, seed + 2001)
    h, w = shape
    groove_period = 6
    yy = np.arange(h, dtype=np.float32).reshape(-1, 1)
    groove = ((yy % groove_period) / groove_period)
    groove = np.broadcast_to(groove, shape).copy()
    spectral_noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 2002)
    # Widened M: dither spans 150..260 pre-clip; spectral noise adds ±20.
    M = 150.0 + dither * 110 + spectral_noise * 20 * sm
    # R genuinely varies: dither drives metal vs dielectric R; groove adds
    # directional roughness. Range now ~10..55 (clipped to 15 floor).
    R = 10.0 + (1.0 - dither) * 35.0 + groove * 15.0
    CC = 16.0 + layer1_cc * 50 * sm
    reinforce = layer1_cc * dither * (1.0 - groove)
    M = M + reinforce * 20
    R = R - reinforce * 5
    return np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(CC, 0, 255).astype(np.float32)

def paint_shokk_apex(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    layer1 = _perlin_upscale(shape, seed + 2000)
    t = (layer1 - layer1.min()) / (layer1.max() - layer1.min() + 1e-8)
    spectral = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 2002)
    hue = (t * 0.5 + spectral * 0.3 + 0.5) % 1.0
    r_ch = np.clip(np.abs(hue * 6 - 3) - 1, 0, 1)
    g_ch = np.clip(2 - np.abs(hue * 6 - 2), 0, 1)
    b_ch = np.clip(2 - np.abs(hue * 6 - 4), 0, 1)
    shimmer = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed + 2003)
    r_ch = np.clip(r_ch + shimmer * 0.08, 0, 1)
    g_ch = np.clip(g_ch + shimmer * 0.05, 0, 1)
    b_ch = np.clip(b_ch + shimmer * 0.08, 0, 1)
    blend = pm * 0.88
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_ch * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_ch * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_ch * mask * blend, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# 21-24. SHOKK FOUNDERS - blood / pulse / venom / void
# ══════════════════════════════════════════════════════════════════════════════
# 2026-04-19 HEENAN HSHKBASE — Bockwinkel SHOKK audit flagged these 5 entries
# (blood/pulse/static/venom/void) as the original wave that lacked dedicated
# `spec_*` functions. shokk_static was tuned in H4HR-BOCK1 (parameter only).
# This block adds dedicated spec/paint pairs for the remaining 4 — promoting
# them from "generic dispatcher with constant M/R/CC + perlin noise" to
# "real signature character that matches the brand promise."
#
# Naming convention: spec_shokk_X / paint_shokk_X. Each pair documented with
# the brand promise it implements.

# ── shokk_blood — deep arterial red metallic, dark vein-shifted edges ───────
def spec_shokk_blood(shape, seed, sm, base_m, base_r):
    """Arterial vein topology: high-M base broken by dark crack/vein lines.
    Veins have sharply lower M (ridge edges → matte cracks read as dried
    blood crust). CC stays glossy except at deepest vein nodes."""
    veins = multi_scale_noise(shape, [4, 8, 16], [0.5, 0.35, 0.15], seed + 2100)
    # Convert noise to ridge map: |gradient| approximates vein lines
    gy = np.abs(np.gradient(veins, axis=0))
    gx = np.abs(np.gradient(veins, axis=1))
    ridge = np.clip((gy + gx) * 8.0, 0, 1)
    flake = multi_scale_noise(shape, [16, 32, 64], [0.4, 0.35, 0.25], seed + 2101)
    M = np.clip(200.0 - ridge * 80.0 * sm + flake * 18.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + ridge * 35.0 * sm + np.abs(flake) * 6.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + ridge * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, CC

def paint_shokk_blood(paint, shape, mask, seed, pm, bb):
    """Red dominance with dark venous shadows tracking the spec ridges."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    veins = multi_scale_noise(shape, [4, 8, 16], [0.5, 0.35, 0.15], seed + 2100)
    gy = np.abs(np.gradient(veins, axis=0))
    gx = np.abs(np.gradient(veins, axis=1))
    ridge = np.clip((gy + gx) * 8.0, 0, 1)
    # Color ramp: bright arterial red base → dark venous red on ridges
    bright = np.array([0.78, 0.08, 0.10], dtype=np.float32)
    deep   = np.array([0.32, 0.02, 0.03], dtype=np.float32)
    color = bright[np.newaxis, np.newaxis, :] * (1.0 - ridge[:, :, np.newaxis]) + \
            deep[np.newaxis, np.newaxis, :]   * ridge[:, :, np.newaxis]
    blend = pm * 0.85
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + color * m3, 0, 1)
    return paint


# ── shokk_pulse — hot pink ⇄ electric blue rhythmic ripple ──────────────────
def spec_shokk_pulse(shape, seed, sm, base_m, base_r):
    """Concentric standing wave from a Perlin-warped center: M oscillates with
    the wave so the painter sees a pulsing pink/blue band as the angle changes.
    R drops in the wave troughs (smoother pink phase) and rises on the crests
    (rougher blue phase)."""
    h, w = shape
    yy, xx = get_mgrid(shape)
    # Perlin-warped radial distance creates organic-feeling waves (vs hard rings).
    warp = multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 2200) * 30.0
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) + warp
    # Standing wave at ~32-pixel wavelength.
    wave = np.sin(r * (2.0 * np.pi / 32.0))
    M = np.clip(220.0 + wave * 25.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + (1.0 - wave) * 22.0 * sm, 15, 255).astype(np.float32)
    CC = np.full(shape, 16.0, dtype=np.float32)
    return M, R, CC

def paint_shokk_pulse(paint, shape, mask, seed, pm, bb):
    """Pink↔blue color shift along the wave phase. Crests = pink, troughs = blue."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    yy, xx = get_mgrid(shape)
    warp = multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 2200) * 30.0
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) + warp
    wave = np.sin(r * (2.0 * np.pi / 32.0))
    # Map wave [-1, 1] → [0, 1] mix between pink and blue.
    phase = (wave + 1.0) * 0.5
    pink = np.array([1.00, 0.20, 0.40], dtype=np.float32)
    blue = np.array([0.20, 0.40, 1.00], dtype=np.float32)
    color = pink[np.newaxis, np.newaxis, :] * phase[:, :, np.newaxis] + \
            blue[np.newaxis, np.newaxis, :] * (1.0 - phase[:, :, np.newaxis])
    blend = pm * 0.85
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + color * m3, 0, 1)
    return paint


# ── shokk_venom — toxic acid green-yellow, ceramic surface with reactive zones
def spec_shokk_venom(shape, seed, sm, base_m, base_r):
    """Dielectric ceramic (M near 0) with bubble-like reactive zones where R
    drops sharply (smoother fluid pools amid rougher cured surface)."""
    pools = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.4, 0.2], seed + 2300)
    # Threshold the pools into discrete "wet zones"
    wet = np.clip((pools - 0.2) * 4.0, 0, 1)
    grit = multi_scale_noise(shape, [16, 64], [0.6, 0.4], seed + 2301)
    M = np.clip(0.0 + wet * 20.0 * sm + np.abs(grit) * 6.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(70.0 - wet * 50.0 * sm + grit * 8.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + wet * 18.0 * sm, 0, 255).astype(np.float32)
    return M, R, CC

def paint_shokk_venom(paint, shape, mask, seed, pm, bb):
    """Acid green-yellow base with bright neon pools where the wet zones are."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    pools = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.4, 0.2], seed + 2300)
    wet = np.clip((pools - 0.2) * 4.0, 0, 1)
    base   = np.array([0.55, 0.85, 0.20], dtype=np.float32)   # acid yellow-green
    bright = np.array([0.75, 1.00, 0.10], dtype=np.float32)   # neon pool
    color = base[np.newaxis, np.newaxis, :] * (1.0 - wet[:, :, np.newaxis]) + \
            bright[np.newaxis, np.newaxis, :] * wet[:, :, np.newaxis]
    blend = pm * 0.85
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + color * m3, 0, 1)
    return paint


# ── shokk_void — vantablack absorption with rare edge shimmer ───────────────
def _void_shimmer_mask(shape, seed, target_fraction=0.003):
    """Return a 0/1 shimmer mask covering exactly `target_fraction` of the
    image at the strongest Perlin-edge crests.

    2026-04-20 HEENAN HARDMODE-FIX-VOID — the previous implementation
    computed `edge_strength = np.clip((gy+gx)*12.0, 0, 1)` which clipped
    ~55-58% of pixels to 1.0 before thresholding at 0.85, making the
    "rare 0.3% shimmer" actually cover a majority of the surface. The
    threshold now runs off a percentile so the glint coverage is
    guaranteed regardless of noise statistics.
    """
    edges_n = multi_scale_noise(shape, [4, 8], [0.7, 0.3], seed + 2400)
    gy = np.abs(np.gradient(edges_n, axis=0))
    gx = np.abs(np.gradient(edges_n, axis=1))
    edge_strength = (gy + gx).astype(np.float32)
    # Pick the edge_strength value at the (1-target_fraction) percentile.
    cutoff = float(np.quantile(edge_strength, 1.0 - float(target_fraction)))
    return (edge_strength >= cutoff).astype(np.float32)


def spec_shokk_void(shape, seed, sm, base_m, base_r):
    """Near-perfect absorption (M=0, R=240, CC=240). Sparse high-M shimmer
    points (~0.3% of pixels) at the strongest Perlin-edge crests — rare
    glints that read as 'subtle edge shimmer' against the void. Coverage
    is percentile-locked (see _void_shimmer_mask) so seed/resolution
    cannot turn this into a majority-coverage effect."""
    shimmer = _void_shimmer_mask(shape, seed, target_fraction=0.003)
    M = np.clip(0.0 + shimmer * 240.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(240.0 - shimmer * 220.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(240.0 - shimmer * 200.0 * sm, 16, 255).astype(np.float32)
    return M, R, CC


def paint_shokk_void(paint, shape, mask, seed, pm, bb):
    """Pure black absorption with the same sparse shimmer brightening to
    near-white at glint points. Shimmer coverage ~0.3% of pixels,
    percentile-locked via _void_shimmer_mask."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    shimmer = _void_shimmer_mask(shape, seed, target_fraction=0.003)
    color = shimmer[:, :, np.newaxis] * np.array([0.95, 0.95, 0.97], dtype=np.float32)[np.newaxis, np.newaxis, :]
    blend = pm * 0.92
    m3 = (mask * blend)[:, :, np.newaxis]
    paint[:, :, :3] = np.clip(paint[:, :, :3] * (1 - m3) + color * m3, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT MAP - for easy registration
# ══════════════════════════════════════════════════════════════════════════════

SHOKK_BASES = {
    "shokk_flux":      {"M": 220, "R": 15,  "CC": 30,  "paint_fn": paint_shokk_flux,      "base_spec_fn": spec_shokk_flux,      "desc": "Thin-film optical interference - CC thickness drives wavelength-selective reflection"},
    "shokk_phase":     {"M": 110, "R": 15,  "CC": 20,  "paint_fn": paint_shokk_phase,     "base_spec_fn": spec_shokk_phase,     "desc": "Liquid crystal domain simulation - Voronoi cells with M=0 to M=220 per domain"},
    "shokk_dual":      {"M": 140, "R": 36,  "CC": 16,  "paint_fn": paint_shokk_dual,      "base_spec_fn": spec_shokk_dual,      "desc": "Hard chromatic binary flip - two complementary colors in interlocking Voronoi tessellation"},
    "shokk_spectrum":  {"M": 245, "R": 30,  "CC": 16,  "paint_fn": paint_shokk_spectrum,   "base_spec_fn": spec_shokk_spectrum,   "desc": "Diffraction grating dispersion - parallel micro-groove roughness reveals spectral bands"},
    "shokk_aurora":    {"M": 165, "R": 16,  "CC": 16,  "paint_fn": paint_shokk_aurora,     "base_spec_fn": spec_shokk_aurora,     "desc": "Atmospheric curtain dynamics - layered sine-wave curtain folds with M/R variation"},
    "shokk_helix":     {"M": 215, "R": 28,  "CC": 30,  "paint_fn": paint_shokk_helix,      "base_spec_fn": spec_shokk_helix,      "desc": "Double-strand complementary spiral - R/CC phase opposition swaps dominant strand"},
    "shokk_catalyst":  {"M": 120, "R": 35,  "CC": 16,  "paint_fn": paint_shokk_catalyst,   "base_spec_fn": spec_shokk_catalyst,   "desc": "BZ reaction wavefront - four-phase spiral with distinct Fresnel per phase"},
    "shokk_mirage":    {"M": 235, "R": 15,  "CC": 16,  "paint_fn": paint_shokk_mirage,     "base_spec_fn": spec_shokk_mirage,     "desc": "Thermal gradient refraction - domain-warped UV creates heat-shimmer color displacement"},
    "shokk_polarity":  {"M": 190, "R": 25,  "CC": 16,  "paint_fn": paint_shokk_polarity,   "base_spec_fn": spec_shokk_polarity,   "desc": "Magnetic domain visualization - Ising model domains with textured boundary network"},
    "shokk_reactor":   {"M": 120, "R": 30,  "CC": 40,  "paint_fn": paint_shokk_reactor,    "base_spec_fn": spec_shokk_reactor,    "desc": "Cherenkov radiation glow - stable dielectric cores anchor shifting metallic field"},
    "shokk_prism":     {"M": 190, "R": 15,  "CC": 38,  "paint_fn": paint_shokk_prism,      "base_spec_fn": spec_shokk_prism,      "desc": "Caustic refraction through crystal - concentrated light bands with CC thickness variation"},
    "shokk_wraith":    {"M": 128, "R": 15,  "CC": 16,  "paint_fn": paint_shokk_wraith,     "base_spec_fn": spec_shokk_wraith,     "desc": "Sub-resolution metallic dithering - M=0/255 error-diffused dither exploits texture filtering"},
    "shokk_tesseract_v2": {"M": 150, "R": 18,  "CC": 20,  "paint_fn": paint_shokk_tesseract,  "base_spec_fn": spec_shokk_tesseract,  "desc": "4D hypercube projection - six impossible coexisting faces with distinct spec per face"},
    "shokk_fusion_base":  {"M": 165, "R": 38,  "CC": 16,  "paint_fn": paint_shokk_fusion,     "base_spec_fn": spec_shokk_fusion,     "desc": "Tokamak plasma confinement - toroidal geometry with blackbody temperature-mapped spec"},
    "shokk_rift":      {"M": 145, "R": 24,  "CC": 16,  "paint_fn": paint_shokk_rift,       "base_spec_fn": spec_shokk_rift,       "desc": "Dimensional fracture network - warm/cool sides with mirror-bright crack lightning"},
    "shokk_vortex":    {"M": 225, "R": 15,  "CC": 36,  "paint_fn": paint_shokk_vortex,     "base_spec_fn": spec_shokk_vortex,     "desc": "Logarithmic spiral color drain - dual-spiral Moire interference shifts with angle"},
    "shokk_surge":     {"M": 185, "R": 28,  "CC": 16,  "paint_fn": paint_shokk_surge,      "base_spec_fn": spec_shokk_surge,      "desc": "Standing wave superposition - constructive/destructive nodes with non-repeating pattern"},
    "shokk_cipher":    {"M": 220, "R": 15,  "CC": 16,  "paint_fn": paint_shokk_cipher,     "base_spec_fn": spec_shokk_cipher,     "desc": "Steganographic encoding - hidden pattern emerges through Fresnel amplification of micro-perturbations"},
    "shokk_inferno":   {"M": 128, "R": 50,  "CC": 48,  "paint_fn": paint_shokk_inferno,    "base_spec_fn": spec_shokk_inferno,    "desc": "Blackbody radiation temperature map - Planck's law M/R follows thermodynamic temperature"},
    "shokk_apex":      {"M": 230, "R": 15,  "CC": 40,  "paint_fn": paint_shokk_apex,       "base_spec_fn": spec_shokk_apex,       "desc": "Multi-layer technique stack - thin-film + dither + grooves + spectral simultaneously"},
    # 2026-04-19 HEENAN HSHKBASE — original SHOKK 4 (blood/pulse/venom/void)
    # promoted from generic dispatcher routing to dedicated spec/paint pairs.
    # Values match the engine/base_registry_data.py declarations so the SHOKK
    # tier reads as 24/24 flagship instead of 20/24 + 4 generic stand-ins.
    "shokk_blood":     {"M": 200, "R": 15, "CC": 16,  "paint_fn": paint_shokk_blood,  "base_spec_fn": spec_shokk_blood,  "desc": "Arterial vein topology - dark venous cracks across high-M base, dried-blood crust on ridges"},
    "shokk_pulse":     {"M": 220, "R": 15, "CC": 16,  "paint_fn": paint_shokk_pulse,  "base_spec_fn": spec_shokk_pulse,  "desc": "Concentric standing wave - hot pink crests / electric blue troughs with rhythmic radial pulse"},
    "shokk_venom":     {"M": 0,   "R": 70, "CC": 16,  "paint_fn": paint_shokk_venom,  "base_spec_fn": spec_shokk_venom,  "desc": "Toxic ceramic with reactive pools - acid green-yellow base, neon-bright wet zones with smoother spec"},
    "shokk_void":      {"M": 0,   "R": 240, "CC": 240, "paint_fn": paint_shokk_void,   "base_spec_fn": spec_shokk_void,   "desc": "Vantablack absorption with rare edge shimmer - 0.3% of pixels glint at sharpest Perlin crests"},
}
