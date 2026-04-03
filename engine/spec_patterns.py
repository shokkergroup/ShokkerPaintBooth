"""
engine/spec_patterns.py
Reusable spec pattern library for Shokker Paint Booth V5.
Composable spatial modulation patterns for M, R, CC spec channels.
Every function returns a (h,w) float32 array in [0, 1].

All functions take (shape, seed, sm, **kwargs) where sm controls variation amplitude.
When sm=0, output is flat 0.5 (no variation).

50 PATTERN TYPES — each creates a fundamentally different visual effect:
 1. banded_rows        — horizontal bands with feathered transitions
 2. flake_scatter       — sparse metallic flake particles
 3. depth_gradient      — coating thickness from gravity pooling
 4. orange_peel_texture — spray coating cellular micro-bumps
 5. wear_scuff          — localized wear patches and streaks
 6. aniso_grain         — directional brushing/grinding marks
 7. interference_bands  — thin-film sinusoidal iridescence
 8. concentric_ripple   — expanding rings from random centers
 9. hex_cells           — honeycomb pattern with per-cell variation
10. marble_vein         — organic veining like natural stone
11. cloud_wisps         — fractal cloud formations for pearlescent
12. micro_sparkle       — ultra-fine dense metallic pigment grain
13. panel_zones         — large irregular zones with different values
14. spiral_sweep        — logarithmic spirals from center
15. carbon_weave        — woven fiber crosshatch pattern
16. crackle_network     — dried clay / crackle glaze fractures
17. flow_lines          — fluid paint flow simulation
18. micro_facets        — tiny angled facets like crushed crystal
19. moire_overlay       — overlapping grids creating moiré interference
20. pebble_grain        — large rounded bumps like leather grain
21. radial_sunburst     — rays emanating from center point
22. topographic_steps   — contour-line stepped levels
23. wave_ripple         — directional water surface interference
24. patina_bloom        — circular bloom spots from chemical reaction
25. electric_branches   — branching tree/lightning Lichtenberg figures

CONVENIENCE:
26. multi_band_spec     — combo of bands + flakes + depth, outputs 0-255
"""
import numpy as np
try:
    import cv2 as _cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False
from scipy.ndimage import gaussian_filter as _scipy_gaussian
from scipy.spatial import cKDTree


def _gauss(arr, sigma):
    """Gaussian blur: use cv2 (3-5x faster) with scipy fallback."""
    if not _CV2_OK or sigma < 0.3:
        return _scipy_gaussian(arr, sigma=sigma)
    # cv2.GaussianBlur requires odd kernel size
    ksize = int(sigma * 6) | 1  # nearest odd integer >= 6*sigma
    ksize = max(ksize, 3)
    return _cv2.GaussianBlur(arr, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sm_scale(arr, sm):
    """Compress pattern toward 0.5 based on sm."""
    return 0.5 + (arr - 0.5) * sm

def _normalize(arr):
    """Normalize array to 0-1 range."""
    lo, hi = arr.min(), arr.max()
    if hi - lo > 1e-7:
        return (arr - lo) / (hi - lo)
    return np.full_like(arr, 0.5)

def _flat(shape):
    """Return flat 0.5 array."""
    return np.full(shape, 0.5, dtype=np.float32)

def multi_scale_noise(shape, scales, weights, seed):
    """Blend Gaussian-smoothed random noise at multiple spatial scales.

    Args:
        shape: (h, w) output shape
        scales: list of sigma values (e.g. [4, 8, 16]) — higher = coarser noise
        weights: list of blend weights matching scales (will be normalised)
        seed: int random seed for reproducibility

    Returns:
        float32 (h, w) array, un-normalised weighted sum of noise octaves
    """
    rng = np.random.RandomState(seed)
    result = np.zeros(shape, dtype=np.float32)
    total_w = sum(weights)
    for sigma, w in zip(scales, weights):
        noise = rng.rand(*shape).astype(np.float32)
        if sigma > 0:
            noise = _gauss(noise, sigma=float(sigma))
        result += noise * (w / total_w)
    return result


# ============================================================================
# 1. BANDED ROWS — horizontal bands with feathered transitions
# ============================================================================

def banded_rows(shape, seed, sm, num_bands=30, palette_size=10,
                feather_frac=0.2, warp_strength=0.03):
    """
    N horizontal bands cycling through palette_size distinct values with
    Gaussian feathered transitions. Band boundaries are warped by low-freq
    noise for organic feel.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    base_palette = np.linspace(0.15, 0.85, palette_size).astype(np.float32)
    rng.shuffle(base_palette)
    band_values = np.array([base_palette[i % palette_size]
                            for i in range(num_bands)], dtype=np.float32)

    band_height = h / num_bands
    band_centers = (np.arange(num_bands, dtype=np.float32) + 0.5) * band_height
    row_coords = np.arange(h, dtype=np.float32)

    xx = np.arange(w, dtype=np.float32) / max(w, 1)
    warp = (np.sin(xx * rng.uniform(2, 8) * np.pi + rng.uniform(0, 2*np.pi)) +
            np.sin(xx * rng.uniform(4, 12) * np.pi + rng.uniform(0, 2*np.pi)) * 0.5
            ) * warp_strength * h

    eff_y = row_coords[:, np.newaxis] + warp[np.newaxis, :]
    feather_px = max(band_height * feather_frac, 1.0)

    # Vectorized over all bands at once: (num_bands, h, w) → reduce along axis 0
    # eff_y is (h, w); band_centers is (B,)
    # diff: (B, h, w) via broadcasting
    diff = eff_y[np.newaxis, :, :] - band_centers[:, np.newaxis, np.newaxis]  # (B, h, w)
    wb = np.exp(-(diff ** 2) / (2.0 * feather_px ** 2))                      # (B, h, w)
    wsum = wb.sum(axis=0)                                                      # (h, w)
    result = (wb * band_values[:, np.newaxis, np.newaxis]).sum(axis=0)        # (h, w)
    result /= np.maximum(wsum, 1e-6)

    return _sm_scale(result, sm).astype(np.float32)


# ============================================================================
# 2. FLAKE SCATTER — sparse metallic flake particles
# ============================================================================

def flake_scatter(shape, seed, sm, density=0.02, flake_radius=2,
                  intensity_range=(0.3, 1.0)):
    """
    Sparse bright spots simulating metallic flake particles.
    Vectorized: scatter all flakes onto sparse canvas, Gaussian-blur for glow.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.default_rng(seed)
    eff_density = density * sm
    num_flakes = min(int(h * w * eff_density), 50000)
    if num_flakes < 1:
        return _flat(shape)

    fy = rng.integers(0, h, size=num_flakes)
    fx = rng.integers(0, w, size=num_flakes)
    lo, hi = intensity_range
    intensities = rng.uniform(lo, hi, size=num_flakes).astype(np.float32)

    # Scatter all flake intensities onto canvas in one pass
    canvas = np.zeros(shape, dtype=np.float32)
    np.add.at(canvas, (fy, fx), intensities)
    canvas = np.clip(canvas, 0.0, 1.0)

    # One Gaussian blur pass produces radial glow around every flake
    sigma = max(0.5, flake_radius * 0.6)
    blurred = _gauss(canvas, sigma=sigma)
    bmax = blurred.max()
    if bmax > 1e-7:
        blurred = blurred / bmax

    result = 0.5 + blurred * 0.5 * sm
    return result.clip(0.0, 1.0).astype(np.float32)


# ============================================================================
# 3. DEPTH GRADIENT — coating thickness from gravity
# ============================================================================

def depth_gradient(shape, seed, sm, direction='vertical', noise_strength=0.15):
    """
    Top-to-bottom or radial gradient with curtain/drip noise modulation.
    Simulates clearcoat pooling at lower body panels.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    if direction == 'radial':
        cy, cx = h / 2.0, w / 2.0
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        grad = np.sqrt(((yy - cy) / h)**2 + ((xx - cx) / w)**2)
        grad = np.clip(grad / max(grad.max(), 1e-6), 0, 1)
    else:
        grad = np.broadcast_to(
            np.linspace(0.0, 1.0, h, dtype=np.float32)[:, np.newaxis], shape
        ).copy()

    # Curtain drip noise
    cn = rng.uniform(-1, 1, size=w).astype(np.float32)
    ks = max(3, w // 50)
    cn = np.convolve(cn, np.ones(ks)/ks, mode='same')
    grad += cn[np.newaxis, :] * noise_strength
    return _sm_scale(_normalize(grad), sm).astype(np.float32)


# ============================================================================
# 4. ORANGE PEEL TEXTURE — spray coating cellular micro-bumps
# ============================================================================

def orange_peel_texture(shape, seed, sm, cell_size=6):
    """
    Fine cellular bumps via bilinear-interpolated cell grid.
    Simulates the classic spray-applied coating texture.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    ny, nx = max(2, h // cell_size), max(2, w // cell_size)
    cv = rng.uniform(0.3, 0.7, size=(ny + 2, nx + 2)).astype(np.float32)

    yy = np.arange(h, dtype=np.float32) / h * ny
    xx = np.arange(w, dtype=np.float32) / w * nx
    yi = np.clip(yy.astype(int), 0, ny)
    xi = np.clip(xx.astype(int), 0, nx)
    yf, xf = yy - yi.astype(np.float32), xx - xi.astype(np.float32)
    yi2, xi2 = yi[:, np.newaxis], xi[np.newaxis, :]
    yf2, xf2 = yf[:, np.newaxis], xf[np.newaxis, :]

    result = (cv[yi2, xi2] * (1-yf2) * (1-xf2) +
              cv[yi2, xi2+1] * (1-yf2) * xf2 +
              cv[yi2+1, xi2] * yf2 * (1-xf2) +
              cv[yi2+1, xi2+1] * yf2 * xf2)
    result += rng.uniform(-0.05, 0.05, size=shape).astype(np.float32)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 5. WEAR SCUFF — localized wear patches and streaks
# ============================================================================

def wear_scuff(shape, seed, sm, wear_density=0.3, streak_angle=0):
    """
    Multi-frequency sin-product patches thresholded to create wear zones
    with directional streak overlays.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    result = np.zeros(shape, dtype=np.float32)
    for _ in range(5):
        fy, fx = rng.uniform(3, 20), rng.uniform(3, 20)
        py, px = rng.uniform(0, 2*np.pi), rng.uniform(0, 2*np.pi)
        yv = np.sin(np.arange(h, dtype=np.float32) / h * fy * np.pi + py)
        xv = np.sin(np.arange(w, dtype=np.float32) / w * fx * np.pi + px)
        result += yv[:, np.newaxis] * xv[np.newaxis, :] * rng.uniform(0.1, 0.3)

    wear = np.clip((np.clip(result, -1, 1) - (1 - wear_density)) / max(wear_density, 0.01), 0, 1)
    if streak_angle == 0:
        streak = np.clip(rng.uniform(0, 1, size=h).astype(np.float32) - 0.7, 0, 1) * 3.0
        wear = np.maximum(wear, streak[:, np.newaxis] * 0.5)
    wm = wear.max()
    if wm > 0:
        wear /= wm
    return _sm_scale(wear, sm).astype(np.float32)


# ============================================================================
# 6. ANISO GRAIN — directional brushing/grinding marks
# ============================================================================

def aniso_grain(shape, seed, sm, direction='horizontal', grain_depth=0.4):
    """
    Row- or column-correlated noise creating visible grain lines.
    Like brushed aluminum or sanded wood.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    if direction == 'horizontal':
        base = rng.uniform(0.2, 0.8, size=h).astype(np.float32)
        for _ in range(2):
            s = base.copy(); s[1:] = base[1:]*0.7 + base[:-1]*0.3; base = s
        result = base[:, np.newaxis] + rng.uniform(-0.05, 0.05, size=shape).astype(np.float32)
    else:
        base = rng.uniform(0.2, 0.8, size=w).astype(np.float32)
        for _ in range(2):
            s = base.copy(); s[1:] = base[1:]*0.7 + base[:-1]*0.3; base = s
        result = base[np.newaxis, :] + rng.uniform(-0.05, 0.05, size=shape).astype(np.float32)

    return (0.5 + (_normalize(result) - 0.5) * sm * grain_depth).astype(np.float32)


# ============================================================================
# 7. INTERFERENCE BANDS — thin-film sinusoidal iridescence
# ============================================================================

def interference_bands(shape, seed, sm, frequency=8.0, noise_warp=0.3):
    """
    Multi-angle sine waves warped by noise then passed through sin()
    to create thin-film-like color banding.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    field = np.zeros(shape, dtype=np.float32)
    for _ in range(3):
        a = rng.uniform(0, np.pi)
        f = frequency * rng.uniform(0.7, 1.3)
        p = rng.uniform(0, 2*np.pi)
        proj = yy[:, np.newaxis] * np.cos(a) + xx[np.newaxis, :] * np.sin(a)
        field += np.sin(proj * f * 2 * np.pi + p) * rng.uniform(0.2, 0.5)

    for _ in range(2):
        fy, fx = rng.uniform(2, 6), rng.uniform(2, 6)
        field += (np.sin(yy[:, np.newaxis]*fy*np.pi + rng.uniform(0, 2*np.pi)) *
                  np.sin(xx[np.newaxis, :]*fx*np.pi + rng.uniform(0, 2*np.pi)) * noise_warp)

    result = 0.5 + 0.5 * np.sin(field * 2 * np.pi)
    return _sm_scale(result, sm).astype(np.float32)


# ============================================================================
# 8. CONCENTRIC RIPPLE — expanding rings from random centers
# ============================================================================

def concentric_ripple(shape, seed, sm, num_centers=3, ring_freq=15.0,
                      decay=0.5):
    """
    Expanding concentric rings from N random center points.
    Like water ripples, machining marks, or radial brushing.
    Ring spacing and phase vary per center for complexity.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    result = np.zeros(shape, dtype=np.float32)
    for _ in range(num_centers):
        cy, cx = rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)
        freq = ring_freq * rng.uniform(0.7, 1.3)
        phase = rng.uniform(0, 2 * np.pi)
        dist = np.sqrt(((yy[:, np.newaxis] - cy) * 2)**2 +
                        ((xx[np.newaxis, :] - cx) * 2)**2)
        # Rings with distance decay
        rings = np.sin(dist * freq * np.pi + phase) * np.exp(-dist * decay * 3)
        result += rings * rng.uniform(0.3, 0.6)

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 9. HEX CELLS — honeycomb pattern with per-cell variation
# ============================================================================

def hex_cells(shape, seed, sm, cell_size=20, edge_width=0.15):
    """
    Hexagonal honeycomb grid. Each cell gets a random value.
    Vectorized Voronoi via cKDTree: all hex centers built as arrays,
    nearest-2 query in one call. No Python loops over cells or pixels.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.default_rng(seed)
    cs = max(4, cell_size)
    row_h = cs * 0.866  # sqrt(3)/2

    ny = max(2, int(h / row_h) + 3)
    nx = max(2, int(w / cs) + 3)
    iy_arr = np.arange(ny)
    ix_arr = np.arange(nx)
    IY, IX = np.meshgrid(iy_arr, ix_arr, indexing='ij')
    center_y = IY.astype(np.float64) * row_h
    center_x = IX.astype(np.float64) * cs + (cs * 0.5) * (IY % 2).astype(np.float64)
    cell_vals = rng.uniform(0.2, 0.8, size=(ny, nx)).astype(np.float32).ravel()

    centers = np.column_stack([center_y.ravel(), center_x.ravel()])  # (N, 2)
    tree = cKDTree(centers)

    # Pixel query grid
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    pts = np.column_stack([yy.ravel(), xx.ravel()])  # (h*w, 2)

    # Query 2 nearest neighbors for edge detection
    dists, idxs = tree.query(pts, k=2, workers=-1)   # (h*w, 2)
    d1 = dists[:, 0].reshape(shape).astype(np.float32)
    d2 = dists[:, 1].reshape(shape).astype(np.float32)
    nearest_val = cell_vals[idxs[:, 0]].reshape(shape)

    # Normalize distances by cell radius for edge_width parameter
    d1_n = d1 / cs
    edge_factor = np.clip(d1_n / (edge_width + 0.01), 0, 1)
    result = nearest_val * (1 - edge_factor * 0.4) + 0.3 * edge_factor * 0.4
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 10. MARBLE VEIN — organic veining like natural stone
# ============================================================================

def marble_vein(shape, seed, sm, vein_freq=6.0, turbulence=3, vein_sharpness=3.0):
    """
    Organic veining pattern. Multiple sin waves distorted by turbulent
    noise create marble/stone-like veins running through the surface.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    # Base directional field
    angle = rng.uniform(0, np.pi)
    proj = yy[:, np.newaxis] * np.cos(angle) + xx[np.newaxis, :] * np.sin(angle)

    # Add turbulent distortion at multiple scales
    turb = np.zeros(shape, dtype=np.float32)
    for i in range(turbulence):
        scale = 2.0 ** (i + 1)
        a1, a2 = rng.uniform(0, 2*np.pi, 2)
        turb += (np.sin(yy[:, np.newaxis]*scale*np.pi + a1) *
                 np.sin(xx[np.newaxis, :]*scale*np.pi + a2)) / scale

    # Vein pattern: sharp sine ridges
    vein_field = np.sin((proj * vein_freq + turb * 0.8) * np.pi)
    # Sharpen veins
    veins = np.abs(vein_field) ** (1.0 / max(vein_sharpness, 0.5))

    # Add secondary perpendicular veins (thinner)
    angle2 = angle + np.pi * 0.4 + rng.uniform(-0.2, 0.2)
    proj2 = yy[:, np.newaxis] * np.cos(angle2) + xx[np.newaxis, :] * np.sin(angle2)
    veins2 = np.abs(np.sin((proj2 * vein_freq * 1.5 + turb * 0.5) * np.pi)) ** (1.0 / max(vein_sharpness * 1.5, 0.5))
    result = veins * 0.7 + veins2 * 0.3

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 11. CLOUD WISPS — fractal cloud formations
# ============================================================================

def cloud_wisps(shape, seed, sm, num_octaves=5, lacunarity=2.0, persistence=0.5):
    """
    Multi-octave fractal noise creating cloud-like wisps.
    Good for pearlescent shimmer, fog effects, soft organic variation.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    result = np.zeros(shape, dtype=np.float32)
    amplitude = 1.0
    freq = 1.0
    for i in range(num_octaves):
        a1 = rng.uniform(0, 2*np.pi)
        a2 = rng.uniform(0, 2*np.pi)
        a3 = rng.uniform(0, 2*np.pi)
        a4 = rng.uniform(0, 2*np.pi)
        # Per-octave random rotation angles to break axis-aligned diagonal stripe bias
        rot1 = rng.uniform(0, 2*np.pi)
        rot2 = rng.uniform(0, 2*np.pi)
        c1, s1 = np.cos(rot1), np.sin(rot1)
        c2, s2 = np.cos(rot2), np.sin(rot2)
        # Rotate coordinates for each sub-noise component
        yy_g = yy[:, np.newaxis]
        xx_g = xx[np.newaxis, :]
        u1 = yy_g * c1 + xx_g * s1
        v1 = -yy_g * s1 + xx_g * c1
        u2 = yy_g * c2 + xx_g * s2
        v2 = -yy_g * s2 + xx_g * c2
        # 2D value noise approximation via sin products on rotated coords
        n = (np.sin(u1 * freq * np.pi * 2 + a1) *
             np.sin(v1 * freq * np.pi * 2 + a2) * 0.5 +
             np.sin(u2 * freq * np.pi * 1.7 + a3) *
             np.cos(v2 * freq * np.pi * 2.3 + a4) * 0.5)
        result += n * amplitude
        freq *= lacunarity
        amplitude *= persistence

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 12. MICRO SPARKLE — ultra-fine dense metallic pigment grain
# ============================================================================

def micro_sparkle(shape, seed, sm, grain_size=1, density=0.15):
    """
    Very fine, dense random sparkle — smaller and denser than flake_scatter.
    Simulates fine metallic pigment like pearl dust or metallic base coat.
    Uses block-based approach for speed instead of per-particle stamps.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    gs = max(1, grain_size)

    if gs == 1:
        # Per-pixel sparkle (fastest)
        raw = rng.uniform(0, 1, size=shape).astype(np.float32)
        # Only top density% of pixels are bright sparkles
        threshold = 1.0 - density
        sparkle = np.clip((raw - threshold) / max(density, 0.01), 0, 1)
        result = 0.5 + sparkle * 0.5
    else:
        # Block sparkle (for larger grains)
        bh, bw = max(1, h // gs), max(1, w // gs)
        raw = rng.uniform(0, 1, size=(bh, bw)).astype(np.float32)
        threshold = 1.0 - density
        sparkle = np.clip((raw - threshold) / max(density, 0.01), 0, 1)
        # Nearest-neighbor upscale
        yi = (np.arange(h) * bh // h).clip(0, bh-1)
        xi = (np.arange(w) * bw // w).clip(0, bw-1)
        result = 0.5 + sparkle[yi[:, np.newaxis], xi[np.newaxis, :]] * 0.5

    return _sm_scale(result, sm).astype(np.float32)


# ============================================================================
# 13. PANEL ZONES — large irregular zones with different values
# ============================================================================

def panel_zones(shape, seed, sm, num_zones=6, feather=0.08):
    """
    Large irregular zones each with a distinct spec value.
    Simulates multi-panel paint variation, patchy coatings,
    or geographic region-based effects.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)

    # Zone centers and values
    zone_vals = rng.uniform(0.15, 0.85, size=num_zones).astype(np.float32)
    zone_cy = rng.uniform(0.1, 0.9, size=num_zones)
    zone_cx = rng.uniform(0.1, 0.9, size=num_zones)

    # For each pixel, find nearest zone via cKDTree (no per-zone loop)
    # Coordinates scaled by 2 to match original distance metric
    centers = np.column_stack([(zone_cy * 2).astype(np.float64), (zone_cx * 2).astype(np.float64)])
    tree = cKDTree(centers)
    yy_g = (np.arange(h, dtype=np.float64) / h) * 2
    xx_g = (np.arange(w, dtype=np.float64) / w) * 2
    YY, XX = np.meshgrid(yy_g, xx_g, indexing='ij')
    pts = np.column_stack([YY.ravel(), XX.ravel()])
    dists, idxs = tree.query(pts, k=2, workers=-1)
    min_dist    = dists[:, 0].reshape(shape).astype(np.float32)
    second_dist = dists[:, 1].reshape(shape).astype(np.float32)
    nearest     = zone_vals[idxs[:, 0]].reshape(shape)

    # Feather at zone boundaries
    edge_blend = np.clip((second_dist - min_dist) / max(feather, 0.001), 0, 1)
    # At boundaries (edge_blend near 0), blend toward mid-value
    result = nearest * edge_blend + 0.5 * (1 - edge_blend)

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 14. SPIRAL SWEEP — logarithmic spirals from center
# ============================================================================

def spiral_sweep(shape, seed, sm, num_arms=4, tightness=3.0, fade=0.3):
    """
    Logarithmic spiral arms radiating from center.
    Creates rotational visual interest — like swirl marks, turbine blades,
    or spiral galaxy patterns in the spec map.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    cy, cx = 0.5 + rng.uniform(-0.1, 0.1), 0.5 + rng.uniform(-0.1, 0.1)
    yy = (np.arange(h, dtype=np.float32) / h - cy)[:, np.newaxis]
    xx = (np.arange(w, dtype=np.float32) / w - cx)[np.newaxis, :]

    theta = np.arctan2(yy, xx)
    r = np.sqrt(yy**2 + xx**2) + 1e-6

    # Spiral: value depends on theta - tightness*log(r)
    spiral_phase = theta * num_arms - np.log(r + 0.01) * tightness * num_arms
    result = 0.5 + 0.5 * np.sin(spiral_phase + rng.uniform(0, 2*np.pi))

    # Fade toward edges
    if fade > 0:
        edge_fade = np.clip(1.0 - r / 0.7, 0, 1) ** fade
        result = result * edge_fade + 0.5 * (1 - edge_fade)

    return _sm_scale(result, sm).astype(np.float32)


# ============================================================================
# 15. CARBON WEAVE — woven fiber crosshatch pattern
# ============================================================================

def carbon_weave(shape, seed, sm, weave_size=12, contrast=0.6):
    """
    Woven fiber crosshatch pattern — alternating over/under threads.
    Simulates carbon fiber, kevlar, or woven textile in spec channel.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    ws = max(4, weave_size)

    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)

    # Thread phase for warp (horizontal) and weft (vertical)
    warp_phase = (yy % (ws * 2)) / (ws * 2)  # 0-1 repeating
    weft_phase = (xx % (ws * 2)) / (ws * 2)

    # Which thread is on top? Checkerboard at weave scale
    warp_cell = (yy // ws).astype(int) % 2  # (h,)
    weft_cell = (xx // ws).astype(int) % 2  # (w,)
    # Over/under: XOR pattern
    on_top = (warp_cell[:, np.newaxis] ^ weft_cell[np.newaxis, :]).astype(np.float32)

    # Thread profile: raised where on top, indented where under
    warp_profile = 0.5 + 0.5 * np.sin(warp_phase * np.pi)  # (h,)
    weft_profile = 0.5 + 0.5 * np.sin(weft_phase * np.pi)  # (w,)

    result = (on_top * warp_profile[:, np.newaxis] +
              (1 - on_top) * weft_profile[np.newaxis, :])

    # Add micro-variation within threads
    result += rng.uniform(-0.03, 0.03, size=shape).astype(np.float32)

    return _sm_scale(_normalize(result) * contrast + 0.5 * (1 - contrast), sm).astype(np.float32)


# ============================================================================
# 16. CRACKLE NETWORK — dried clay / crackle glaze fractures
# ============================================================================

def crackle_network(shape, seed, sm, cell_count=25, crack_width=0.12):
    """
    Organic crack/craze pattern using Voronoi edge detection.
    Each cell is intact surface; boundaries are cracks/fractures.
    Simulates crackle glaze, dried mud, or aged clearcoat.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    # Voronoi cell centers
    n = max(4, cell_count)
    cy = rng.uniform(0, 1, size=n).astype(np.float32)
    cx = rng.uniform(0, 1, size=n).astype(np.float32)
    cell_vals = rng.uniform(0.4, 0.7, size=n).astype(np.float32)

    # Use cKDTree for vectorized 2-NN query — no Python loop over cells
    # Centers are in normalized [0,1] coordinates (match yy/xx)
    centers = np.column_stack([cy.astype(np.float64), cx.astype(np.float64)])
    tree = cKDTree(centers)
    yy_g = np.arange(h, dtype=np.float64) / h
    xx_g = np.arange(w, dtype=np.float64) / w
    YY, XX = np.meshgrid(yy_g, xx_g, indexing='ij')
    pts = np.column_stack([YY.ravel(), XX.ravel()])
    dists, idxs = tree.query(pts, k=2, workers=-1)
    d1      = dists[:, 0].reshape(shape).astype(np.float32)
    d2      = dists[:, 1].reshape(shape).astype(np.float32)
    nearest = cell_vals[idxs[:, 0]].reshape(shape)

    # Crack detection: thin zone where d2 ≈ d1
    crack_factor = np.clip(1.0 - (d2 - d1) / max(crack_width * 0.1, 0.001), 0, 1)

    # Cracks are dark/rough (low value), intact surface is cell value
    result = nearest * (1 - crack_factor) + 0.15 * crack_factor

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 17. FLOW LINES — fluid paint flow simulation
# ============================================================================

def flow_lines(shape, seed, sm, num_streams=40, line_width=0.02, curvature=3.0):
    """
    Fluid flow lines showing how paint/coating flows across surface.
    Simulates spray patterns, drip paths, or wind streaks.
    Creates organic elongated streaks that curve across the surface.
    Optimized: processes streams in batches to reduce per-stream overhead.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    # Base flow direction (slightly diagonal)
    base_angle = rng.uniform(-0.3, 0.3)
    tan_angle = np.tan(base_angle)

    # Pre-generate all stream parameters at once
    n = num_streams
    start_ys = rng.uniform(0, 1, n).astype(np.float32)
    intensities = rng.uniform(0.3, 0.8, n).astype(np.float32)
    freqs = rng.uniform(0.5, curvature, n).astype(np.float32)
    phases = rng.uniform(0, 2 * np.pi, n).astype(np.float32)
    amplitudes = rng.uniform(0.02, 0.12, n).astype(np.float32)
    lws = (line_width * rng.uniform(0.5, 2.0, n)).astype(np.float32)

    # Process in batches of 8 to limit peak memory while still vectorizing
    batch_size = 8
    result = np.zeros(shape, dtype=np.float32)
    for b_start in range(0, n, batch_size):
        b_end = min(b_start + batch_size, n)
        b = b_end - b_start
        # Compute all stream centerlines for this batch: (b, w)
        stream_ys = (start_ys[b_start:b_end, None] +
                     np.sin(xx[None, :] * freqs[b_start:b_end, None] * np.pi + phases[b_start:b_end, None]) *
                     amplitudes[b_start:b_end, None] +
                     xx[None, :] * tan_angle)
        # Distance from every pixel row to every stream: (b, h, w) via broadcasting
        # yy is (h,), stream_ys is (b, w) → dist is (b, h, w)
        dist = np.abs(yy[None, :, None] - stream_ys[:, None, :])
        # Gaussian profile: (b, h, w)
        inv_2lw2 = 1.0 / (2.0 * lws[b_start:b_end, None, None] ** 2)
        streams = np.exp(-(dist ** 2) * inv_2lw2)
        # Accumulate weighted streams
        weights = (intensities[b_start:b_end] - 0.5)[:, None, None] * 0.5
        result += (streams * weights).sum(axis=0)

    result += 0.5  # Re-center around 0.5
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 18. MICRO FACETS — tiny angled facets like crushed crystal
# ============================================================================

def micro_facets(shape, seed, sm, facet_size=8, angle_range=0.5):
    """
    Tiny flat facets at random angles simulating crushed crystal,
    faceted gemstone, or micro-machined surface. Each facet has a
    uniform value representing its angle to the viewer.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    fs = max(2, facet_size)
    # Grid of facets
    ny, nx = max(2, h // fs), max(2, w // fs)
    facet_vals = rng.uniform(0.1, 0.9, size=(ny, nx)).astype(np.float32)

    # Map pixels to facets (nearest-neighbor = flat facets)
    yi = (np.arange(h) * ny // h).clip(0, ny - 1)
    xi = (np.arange(w) * nx // w).clip(0, nx - 1)
    result = facet_vals[yi[:, np.newaxis], xi[np.newaxis, :]]

    # Add very slight gradient within each facet to show tilt
    y_in_facet = (np.arange(h, dtype=np.float32) % fs) / fs - 0.5
    x_in_facet = (np.arange(w, dtype=np.float32) % fs) / fs - 0.5
    # Random tilt directions per facet
    tilt_y = rng.uniform(-angle_range, angle_range, size=(ny, nx)).astype(np.float32)
    tilt_x = rng.uniform(-angle_range, angle_range, size=(ny, nx)).astype(np.float32)
    ty = tilt_y[yi[:, np.newaxis], xi[np.newaxis, :]]
    tx = tilt_x[yi[:, np.newaxis], xi[np.newaxis, :]]
    result += y_in_facet[:, np.newaxis] * ty + x_in_facet[np.newaxis, :] * tx

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 19. MOIRE OVERLAY — overlapping grids creating moiré interference
# ============================================================================

def moire_overlay(shape, seed, sm, grid1_freq=20, grid2_freq=21, grid2_angle=0.05):
    """
    Two slightly offset grids create moiré interference patterns.
    The beat frequency between grids creates large-scale wavy patterns
    from high-frequency components. Mesmerizing visual effect.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    # Grid 1: axis-aligned
    g1 = ((0.5 + 0.5 * np.sin(yy[:, np.newaxis] * grid1_freq * 2 * np.pi)) *
          (0.5 + 0.5 * np.sin(xx[np.newaxis, :] * grid1_freq * 2 * np.pi)))

    # Grid 2: slightly rotated and different frequency
    angle = grid2_angle + rng.uniform(-0.02, 0.02)
    proj_y = yy[:, np.newaxis] * np.cos(angle) + xx[np.newaxis, :] * np.sin(angle)
    proj_x = -yy[:, np.newaxis] * np.sin(angle) + xx[np.newaxis, :] * np.cos(angle)
    g2 = ((0.5 + 0.5 * np.sin(proj_y * grid2_freq * 2 * np.pi)) *
          (0.5 + 0.5 * np.sin(proj_x * grid2_freq * 2 * np.pi)))

    # Moiré = product of two grids reveals beat frequency
    result = g1 * g2

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 20. PEBBLE GRAIN — large rounded bumps like leather grain
# ============================================================================

def pebble_grain(shape, seed, sm, pebble_size=15, roundness=0.7):
    """
    Large rounded bumps like leather grain, pebbled rubber, or hammered metal.
    Vectorized grid-jitter Voronoi via cKDTree: one center per grid cell,
    nearest-neighbor query in one call — no per-center Python loops.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.default_rng(seed)
    ps = max(4, pebble_size)
    pebble_radius = ps * 0.6

    ny = max(2, h // ps + 2)
    nx = max(2, w // ps + 2)

    jitter_y = rng.uniform(0.1, 0.9, size=(ny, nx))
    jitter_x = rng.uniform(0.1, 0.9, size=(ny, nx))
    pebble_height = rng.uniform(0.3, 0.8, size=(ny, nx)).astype(np.float32).ravel()

    iy_arr = np.arange(ny, dtype=np.float64)
    ix_arr = np.arange(nx, dtype=np.float64)
    IY, IX = np.meshgrid(iy_arr, ix_arr, indexing='ij')
    center_y = (IY + jitter_y) * ps
    center_x = (IX + jitter_x) * ps

    centers = np.column_stack([center_y.ravel(), center_x.ravel()])
    tree = cKDTree(centers)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    pts = np.column_stack([yy.ravel(), xx.ravel()])

    dists, idxs = tree.query(pts, k=1, workers=-1)
    min_dist = dists.reshape(shape).astype(np.float32)
    nearest_h = pebble_height[idxs].reshape(shape)

    dome = np.clip(1.0 - (min_dist / pebble_radius) ** roundness, 0, 1)
    result = nearest_h * dome + 0.2 * (1 - dome)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 21. RADIAL SUNBURST — rays emanating from center
# ============================================================================

def radial_sunburst(shape, seed, sm, num_rays=12, sharpness=2.0,
                    center_glow=0.3):
    """
    Rays emanating from a central point like a sunburst, crown,
    or radial polish marks. Each ray has slightly different intensity.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    cy = 0.5 + rng.uniform(-0.15, 0.15)
    cx = 0.5 + rng.uniform(-0.15, 0.15)
    yy = (np.arange(h, dtype=np.float32) / h - cy)[:, np.newaxis]
    xx = (np.arange(w, dtype=np.float32) / w - cx)[np.newaxis, :]

    theta = np.arctan2(yy, xx)
    r = np.sqrt(yy**2 + xx**2) + 1e-6

    # Ray pattern
    ray_base = np.sin(theta * num_rays + rng.uniform(0, 2*np.pi))
    rays = (0.5 + 0.5 * ray_base) ** sharpness

    # Per-ray intensity variation
    ray_idx = ((theta + np.pi) / (2 * np.pi) * num_rays).astype(int) % num_rays
    ray_intensities = rng.uniform(0.4, 1.0, size=num_rays).astype(np.float32)
    intensity_map = ray_intensities[ray_idx]

    result = rays * intensity_map

    # Center glow
    if center_glow > 0:
        glow = np.exp(-(r / 0.15)**2) * center_glow
        result = result + glow

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 22. TOPOGRAPHIC STEPS — contour-line stepped levels
# ============================================================================

def topographic_steps(shape, seed, sm, num_levels=8, noise_octaves=3):
    """
    Quantized noise field creating terraced/stepped contour regions.
    Like topographic map lines, anodizing layers, or stepped clearcoat.
    Each level is a flat plateau with sharp-ish transitions between levels.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    # Multi-octave noise field
    field = np.zeros(shape, dtype=np.float32)
    amp = 1.0
    for i in range(noise_octaves):
        f = 2.0 ** (i + 1)
        a1, a2 = rng.uniform(0, 2*np.pi, 2)
        field += (np.sin(yy[:, np.newaxis]*f*np.pi + a1) *
                  np.sin(xx[np.newaxis, :]*f*np.pi + a2)) * amp
        amp *= 0.5

    # Normalize to 0-1
    field = _normalize(field)

    # Quantize into levels with slight softening at edges
    levels = max(2, num_levels)
    stepped = np.round(field * (levels - 1)) / (levels - 1)

    # Slight smoothing between steps (not perfectly hard)
    alpha = 0.85
    result = stepped * alpha + field * (1 - alpha)

    return _sm_scale(result, sm).astype(np.float32)


# ============================================================================
# 23. WAVE RIPPLE — directional water surface interference
# ============================================================================

def wave_ripple(shape, seed, sm, num_waves=5, base_freq=6.0, choppy=0.3):
    """
    Overlapping directional waves creating water-surface-like interference.
    Multiple wave trains at different angles and frequencies combine.
    Simulates liquid metal, water reflection, or rippled glass.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    result = np.zeros(shape, dtype=np.float32)
    for _ in range(num_waves):
        angle = rng.uniform(0, np.pi)
        freq = base_freq * rng.uniform(0.5, 2.0)
        phase = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.15, 0.4)

        proj = yy[:, np.newaxis] * np.cos(angle) + xx[np.newaxis, :] * np.sin(angle)
        wave = np.sin(proj * freq * 2 * np.pi + phase)

        # Add choppiness (sharpen wave peaks)
        if choppy > 0:
            wave = np.sign(wave) * np.abs(wave) ** (1 - choppy * 0.5)

        result += wave * amp

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 24. PATINA BLOOM — circular bloom spots from chemical reaction
# ============================================================================

def patina_bloom(shape, seed, sm, num_blooms=20, min_radius=0.02,
                 max_radius=0.12):
    """
    Circular bloom/stain spots from chemical patina, water spots,
    or oxidation reactions. Each bloom is a soft circular gradient.
    Overlapping blooms create organic depth variation.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    # Pre-generate all bloom parameters at once
    n = num_blooms
    cys       = rng.uniform(0, 1, n).astype(np.float32)
    cxs       = rng.uniform(0, 1, n).astype(np.float32)
    radii     = rng.uniform(min_radius, max_radius, n).astype(np.float32)
    intensities = rng.uniform(0.3, 0.9, n).astype(np.float32)
    is_ring   = rng.uniform(0, 1, n) > 0.5   # (n,) bool

    result = np.full(shape, 0.5, dtype=np.float32)

    # Separate ring and solid blooms to batch each type
    ring_idx  = np.where(is_ring)[0]
    solid_idx = np.where(~is_ring)[0]

    # --- Solid blooms: (n_solid, h, w) ---
    if len(solid_idx) > 0:
        # dist^2 = (yy - cy)^2 + (xx - cx)^2 for each bloom
        dy = yy[:, np.newaxis, np.newaxis] - cys[solid_idx][np.newaxis, np.newaxis, :]  # (h,1,n)
        dx = xx[np.newaxis, :, np.newaxis] - cxs[solid_idx][np.newaxis, np.newaxis, :]  # (1,w,n)
        # dist: (h, w, n_solid)
        dist_sq = dy**2 + dx**2
        r2 = (radii[solid_idx]**2)[np.newaxis, np.newaxis, :]
        bloom = np.exp(-dist_sq / np.maximum(r2, 1e-12)) * intensities[solid_idx][np.newaxis, np.newaxis, :]
        result += (bloom.sum(axis=2) - 0.5 * len(solid_idx)) * 0.3

    # --- Ring blooms ---
    if len(ring_idx) > 0:
        dy = yy[:, np.newaxis, np.newaxis] - cys[ring_idx][np.newaxis, np.newaxis, :]
        dx = xx[np.newaxis, :, np.newaxis] - cxs[ring_idx][np.newaxis, np.newaxis, :]
        dist = np.sqrt(dy**2 + dx**2)
        r_inner = (radii[ring_idx] * 0.7)[np.newaxis, np.newaxis, :]
        r_width = (radii[ring_idx] * 0.3 + 1e-6)[np.newaxis, np.newaxis, :]
        ring_dist = np.abs(dist - r_inner) / r_width
        bloom = np.exp(-ring_dist**2 * 2) * intensities[ring_idx][np.newaxis, np.newaxis, :]
        result += (bloom.sum(axis=2) - 0.5 * len(ring_idx)) * 0.3

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 25. ELECTRIC BRANCHES — branching tree / Lichtenberg figures
# ============================================================================

def electric_branches(shape, seed, sm, num_trees=3, branch_depth=6,
                      thickness=0.008):
    """
    Branching tree/lightning patterns (Lichtenberg figures).
    Vectorized: collect all segments iteratively (capped), then draw each segment
    onto a sparse canvas via rasterized line sampling, apply Gaussian blur for glow.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.default_rng(seed)
    MAX_SEGS = 2000   # cap to prevent exponential blowup

    # --- Phase 1: collect segments iteratively (stack-based) ---
    segments = []  # (y0, x0, y1, x1, thickness_norm, intensity)

    stack = []
    for _ in range(num_trees):
        root_y = rng.uniform(0.2, 0.8)
        root_x = rng.uniform(0.2, 0.8)
        root_angle = rng.uniform(0, 2 * np.pi)
        root_length = rng.uniform(0.15, 0.35)
        stack.append((root_y, root_x, root_angle, root_length, branch_depth, rng.uniform(0.6, 1.0)))

    while stack and len(segments) < MAX_SEGS:
        y0, x0, angle, length, depth, intensity = stack.pop()
        if depth <= 0 or length < 0.005:
            continue
        y1 = y0 + np.sin(angle) * length
        x1 = x0 + np.cos(angle) * length
        thick = max(thickness * (depth / max(branch_depth, 1)), 0.001)
        dy_seg = y1 - y0; dx_seg = x1 - x0
        segments.append((y0, x0, y1, x1, thick, intensity))

        num_children = int(rng.integers(1, 4))
        for _ in range(num_children):
            child_angle = angle + rng.uniform(-0.8, 0.8)
            child_length = length * rng.uniform(0.4, 0.7)
            child_intensity = intensity * rng.uniform(0.5, 0.85)
            branch_t = rng.uniform(0.3, 0.9)
            by = y0 + dy_seg * branch_t
            bx = x0 + dx_seg * branch_t
            stack.append((by, bx, child_angle, child_length, depth - 1, child_intensity))

    if not segments:
        return _flat(shape)

    # --- Phase 2: rasterize segments onto a sparse canvas, then Gaussian blur ---
    canvas = np.zeros(shape, dtype=np.float32)
    inten_canvas = np.zeros(shape, dtype=np.float32)

    for (y0, x0, y1, x1, thick, inten) in segments:
        # Rasterize this line segment using Bresenham-style sampling
        py0 = int(np.clip(y0 * h, 0, h - 1))
        px0 = int(np.clip(x0 * w, 0, w - 1))
        py1 = int(np.clip(y1 * h, 0, h - 1))
        px1 = int(np.clip(x1 * w, 0, w - 1))
        n_steps = max(abs(py1 - py0), abs(px1 - px0), 1)
        ts = np.linspace(0, 1, n_steps + 1)
        ys = np.clip((py0 + (py1 - py0) * ts).astype(np.int32), 0, h - 1)
        xs = np.clip((px0 + (px1 - px0) * ts).astype(np.int32), 0, w - 1)
        np.maximum.at(canvas, (ys, xs), inten)

    # Gaussian blur for glow — sigma proportional to mean thickness
    mean_thick = float(np.mean([s[4] for s in segments]))
    sigma = max(mean_thick * min(h, w) * 0.5, 1.5)
    blurred = _gauss(canvas, sigma=sigma)
    result = np.maximum(canvas * 0.4, blurred)
    result = 0.3 + result * 0.7

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 26. MULTI_BAND_SPEC — convenience combo (outputs 0-255)
# ============================================================================

def multi_band_spec(shape, seed, sm, base_val, variation, num_bands=30,
                    palette_size=10, flake_density=0.01, depth_weight=0.3):
    """
    Convenience: combines banded_rows + flake_scatter + depth_gradient
    into a ready-to-use spec channel value array in 0-255 range.
    """
    bands = banded_rows(shape, seed, sm, num_bands=num_bands,
                        palette_size=palette_size)
    flakes = flake_scatter(shape, seed + 7777, sm, density=flake_density)
    depth = depth_gradient(shape, seed + 8888, sm)

    combined = bands * 0.5 + flakes * 0.3 + depth * depth_weight
    combined = _normalize(combined)
    result = base_val + (combined - 0.5) * 2.0 * variation * sm

    # Normalize to [0,1] to match all other pattern functions
    result_01 = np.clip(result / 255.0, 0.0, 1.0)
    return _sm_scale(result_01, sm).astype(np.float32)


# ============================================================================
# 26. VORONOI_FRACTURE — shattered glass cell boundaries
# ============================================================================

def voronoi_fracture(shape, seed, sm, num_cells=40, edge_width=2.0, **kwargs):
    """Voronoi tessellation with bright cell interiors and dark fracture edges."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cx = rng.rand(num_cells).astype(np.float32) * w
    cy = rng.rand(num_cells).astype(np.float32) * h
    cell_vals = (rng.rand(num_cells).astype(np.float32) * 0.6 + 0.2)

    # Use cKDTree for vectorized 2-NN query instead of per-cell loop
    centers = np.column_stack([cy, cx]).astype(np.float64)
    tree = cKDTree(centers)
    yy, xx = np.mgrid[0:h, 0:w]
    pts = np.column_stack([yy.ravel().astype(np.float64), xx.ravel().astype(np.float64)])
    dists, idxs = tree.query(pts, k=2, workers=-1)
    d1 = dists[:, 0].reshape(shape).astype(np.float32)
    d2 = dists[:, 1].reshape(shape).astype(np.float32)
    closest = idxs[:, 0].reshape(shape)

    edge = np.clip((d2 - d1) / max(edge_width, 1e-6), 0, 1).astype(np.float32)
    cell_fill = cell_vals[closest]
    result = cell_fill * edge
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 27. PLASMA_TURBULENCE — hot plasma energy field
# ============================================================================

def plasma_turbulence(shape, seed, sm, octaves=6, freq_base=3.0, **kwargs):
    """Multi-octave sinusoidal plasma field — chaotic swirling energy."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    result = np.zeros(shape, dtype=np.float32)
    amp = 1.0
    for o in range(octaves):
        freq = freq_base * (2.0 ** o)
        ph1, ph2, ph3 = rng.uniform(0, 2*np.pi, 3)
        a1, a2 = rng.uniform(0.5, 1.5, 2)
        result += amp * np.sin(X * freq * a1 + np.sin(Y * freq * 0.7 + ph1) * 2.0 + ph2)
        result += amp * 0.7 * np.cos(Y * freq * a2 + np.cos(X * freq * 0.6 + ph3) * 1.8)
        amp *= 0.55
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 28. DIAMOND_LATTICE — geometric diamond/rhombus grid with depth
# ============================================================================

def diamond_lattice(shape, seed, sm, cell_size=24, depth_variation=0.4, **kwargs):
    """Repeating diamond lattice — each cell has unique depth modulation."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Diamond coordinates: rotate 45 degrees
    u = (xx + yy) / cell_size
    v = (xx - yy) / cell_size
    cu, cv = np.floor(u).astype(np.int32), np.floor(v).astype(np.int32)
    fu, fv = u - np.floor(u), v - np.floor(v)

    # Distance to cell center
    dist = np.abs(fu - 0.5) + np.abs(fv - 0.5)
    dist = 1.0 - np.clip(dist * 2.0, 0, 1)

    # Per-cell variation
    cell_hash = ((cu * 73856093) ^ (cv * 19349663)) & 0xFFFF
    cell_val = (cell_hash.astype(np.float32) / 65535.0) * depth_variation + (1.0 - depth_variation * 0.5)
    result = dist * cell_val
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 29. ACID_ETCH — chemical dissolution eating through coating
# ============================================================================

def acid_etch(shape, seed, sm, intensity=0.6, blob_count=30, **kwargs):
    """Chemical etching — irregular dissolution patches exposing underlayer."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)

    # Pre-generate all blob parameters
    n = blob_count
    cxs    = rng.rand(n).astype(np.float32) * w
    cys    = rng.rand(n).astype(np.float32) * h
    rxs    = rng.uniform(10, 60, n).astype(np.float32)
    rys    = rng.uniform(10, 60, n).astype(np.float32)
    angles = rng.uniform(0, np.pi, n).astype(np.float32)
    depths = rng.uniform(0.3, 1.0, n).astype(np.float32)
    noise_phases = rng.uniform(0, 6.28, n).astype(np.float32)

    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    # Build 2D grids once
    XX, YY = np.meshgrid(xx, yy)  # (h, w)

    result = np.ones(shape, dtype=np.float32)

    # Process in small batches to limit (n, h, w) peak memory
    batch = max(1, min(5, blob_count))
    for b_start in range(0, n, batch):
        b_end = min(b_start + batch, n)
        B = b_end - b_start

        cos_a = np.cos(angles[b_start:b_end]).astype(np.float32)  # (B,)
        sin_a = np.sin(angles[b_start:b_end]).astype(np.float32)

        # (B, h, w) local rotated coords
        dX = XX[np.newaxis, :, :] - cxs[b_start:b_end, np.newaxis, np.newaxis]
        dY = YY[np.newaxis, :, :] - cys[b_start:b_end, np.newaxis, np.newaxis]
        dx = dX * cos_a[:, np.newaxis, np.newaxis] + dY * sin_a[:, np.newaxis, np.newaxis]
        dy = -dX * sin_a[:, np.newaxis, np.newaxis] + dY * cos_a[:, np.newaxis, np.newaxis]

        rx = rxs[b_start:b_end, np.newaxis, np.newaxis]
        ry = rys[b_start:b_end, np.newaxis, np.newaxis]
        d = (dx / rx) ** 2 + (dy / ry) ** 2

        dep = depths[b_start:b_end, np.newaxis, np.newaxis]
        etch = np.exp(-d * 2.0) * dep * intensity

        ph = noise_phases[b_start:b_end, np.newaxis, np.newaxis]
        edge_noise = np.sin(dx * 0.3 + ph) * np.cos(dy * 0.4) * 0.15
        etch_total = etch + np.clip(edge_noise * np.exp(-d * 3.0), 0, 0.3)

        result -= etch_total.sum(axis=0)

    return _sm_scale(_normalize(np.clip(result, 0, 1)), sm)


# ============================================================================
# 30. GALAXY_SWIRL — spiral galaxy arms with star clusters
# ============================================================================

def galaxy_swirl(shape, seed, sm, num_arms=4, twist=3.0, **kwargs):
    """Spiral galaxy arms with concentrated star clusters along arms."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(-1, 1, h, dtype=np.float32)
    xx = np.linspace(-1, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    r = np.sqrt(X**2 + Y**2) + 1e-7
    theta = np.arctan2(Y, X)

    # Spiral arms
    arms = np.zeros(shape, dtype=np.float32)
    for a in range(num_arms):
        arm_angle = theta - twist * np.log(r + 0.1) + a * 2.0 * np.pi / num_arms
        arm_brightness = np.exp(-((np.sin(arm_angle) * r)**2) * 8.0)
        arms += arm_brightness

    # Central bulge
    bulge = np.exp(-r**2 * 6.0)
    # Outer halo falloff
    halo = np.exp(-r * 2.0)

    result = arms * halo + bulge * 0.5
    # Sprinkle star clusters — Gaussian blur replaces slow nested-roll loop
    stars = (rng.rand(h, w) > 0.997).astype(np.float32)
    star_glow = _gauss(stars, sigma=1.0)
    result += star_glow * 0.3

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 31. REPTILE_SCALE — overlapping biological scales
# ============================================================================

def reptile_scale(shape, seed, sm, scale_size=18, overlap=0.3, **kwargs):
    """Overlapping reptilian scales with orientation-based specularity."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Offset rows for scale pattern
    row = yy / scale_size
    col = xx / scale_size
    # Every other row offset by half
    offset = (np.floor(row).astype(np.int32) % 2) * 0.5
    col_off = col + offset

    fr = row - np.floor(row)
    fc = col_off - np.floor(col_off)

    # Scale shape: rounded top (bright), dark edge at bottom
    scale_y = np.clip(1.0 - fr * (1.0 + overlap), 0, 1)
    scale_x = 1.0 - np.abs(fc - 0.5) * 2.0
    scale_bright = scale_y * scale_x

    # Per-scale random tilt affecting spec
    cell_r = np.floor(row).astype(np.int32)
    cell_c = np.floor(col_off).astype(np.int32)
    cell_hash = ((cell_r * 48271) ^ (cell_c * 16807)) & 0xFFFF
    tilt = (cell_hash.astype(np.float32) / 65535.0) * 0.4 + 0.8

    result = (scale_bright * tilt).astype(np.float32)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 32. MAGNETIC_FIELD — iron filing lines along magnetic poles
# ============================================================================

def magnetic_field(shape, seed, sm, num_poles=3, line_density=20.0, **kwargs):
    """Magnetic field lines between poles — iron filing visualization."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(-1, 1, h, dtype=np.float32)
    xx = np.linspace(-1, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    poles = []
    for _ in range(num_poles):
        px, py = rng.uniform(-0.7, 0.7), rng.uniform(-0.7, 0.7)
        polarity = rng.choice([-1.0, 1.0])
        poles.append((px, py, polarity))

    # Compute field angle at each point
    Bx = np.zeros(shape, dtype=np.float32)
    By = np.zeros(shape, dtype=np.float32)
    for px, py, pol in poles:
        dx = X - px
        dy = Y - py
        r2 = dx**2 + dy**2 + 0.01
        r3 = r2 * np.sqrt(r2)
        Bx += pol * dx / r3
        By += pol * dy / r3

    theta = np.arctan2(By, Bx)
    strength = np.sqrt(Bx**2 + By**2)
    strength = np.clip(strength / (strength.max() + 1e-7), 0, 1)

    # Field lines via sin of angle * density
    lines = (np.sin(theta * line_density) * 0.5 + 0.5) * strength
    return _sm_scale(_normalize(lines), sm)


# ============================================================================
# 33. PRISMATIC_SHATTER — shattered prism fragments with angular reflections
# ============================================================================

def prismatic_shatter(shape, seed, sm, num_shards=60, **kwargs):
    """Shattered glass/prism — each shard reflects at a different angle."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cx = rng.rand(num_shards) * w
    cy = rng.rand(num_shards) * h
    angles = rng.uniform(0, np.pi, num_shards)
    shard_spec = rng.uniform(0.15, 0.95, num_shards).astype(np.float32)

    # Assign each pixel to nearest shard via cKDTree (vectorized, no loop)
    centers = np.column_stack([cy.astype(np.float64), cx.astype(np.float64)])
    tree = cKDTree(centers)
    yy_g, xx_g = np.mgrid[0:h, 0:w]
    pts = np.column_stack([yy_g.ravel().astype(np.float64), xx_g.ravel().astype(np.float64)])
    dists, idxs = tree.query(pts, k=2, workers=-1)
    min_dist_v   = dists[:, 0].reshape(shape).astype(np.float32)
    second_dist_v= dists[:, 1].reshape(shape).astype(np.float32)
    closest = idxs[:, 0].reshape(shape)

    yy = yy_g.astype(np.float32)
    xx = xx_g.astype(np.float32)

    # Angular gradient within each shard — normalize to [0,1] to avoid wild oscillation
    shard_angle = angles[closest]
    xx_n = xx / w
    yy_n = yy / h
    grad = np.sin((xx_n * np.cos(shard_angle) + yy_n * np.sin(shard_angle)) * np.pi) * 0.5 + 0.5

    # Edge darkening (fracture lines)
    edge = np.clip((second_dist_v - min_dist_v) / 3.0, 0, 1)

    result = (shard_spec[closest] * (0.6 + 0.4 * grad) * edge).astype(np.float32)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 34. NEURAL_DENDRITE — branching neural network dendrites
# ============================================================================

def neural_dendrite(shape, seed, sm, num_neurons=5, branch_depth=7, **kwargs):
    """
    Branching neural dendrite trees — synaptic network visualization.
    Vectorized: collect segments iteratively (capped), rasterize to sparse canvas,
    apply Gaussian blur for soft dendritic glow. Fast on any resolution.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    MAX_SEGS = 3000  # cap against exponential blowup

    # --- Phase 1: collect segments and body centers via iterative stack ---
    segments = []  # (ax, ay, bx, by, thickness_px, brightness)
    bodies   = []

    for _ in range(num_neurons):
        sx, sy = rng.uniform(0, w), rng.uniform(0, h)
        bodies.append((sx, sy))
        n_arms = int(rng.integers(3, 7))
        arm_stack = []
        for _ in range(n_arms):
            angle = rng.uniform(0, 2 * np.pi)
            arm_stack.append((sx, sy, angle, rng.uniform(30, 80), 3.0, branch_depth))

        while arm_stack and len(segments) < MAX_SEGS:
            x, y, angle, length, thickness, depth = arm_stack.pop()
            if depth <= 0 or length < 2:
                continue
            ex = x + length * np.cos(angle)
            ey = y + length * np.sin(angle)
            bright = 0.8 * (depth / max(branch_depth, 1))
            segments.append((x, y, ex, ey, max(thickness, 1.0), bright))
            n_children = int(rng.integers(2, 4))
            for _ in range(n_children):
                child_angle = angle + rng.uniform(-0.7, 0.7)
                child_len   = length * rng.uniform(0.5, 0.75)
                arm_stack.append((ex, ey, child_angle, child_len, thickness * 0.65, depth - 1))

    # --- Phase 2: rasterize all segments onto a sparse canvas ---
    canvas = np.zeros(shape, dtype=np.float32)

    for (ax, ay, bx, by, thick, bright) in segments:
        py0 = int(np.clip(ay, 0, h - 1))
        px0 = int(np.clip(ax, 0, w - 1))
        py1 = int(np.clip(by, 0, h - 1))
        px1 = int(np.clip(bx, 0, w - 1))
        n_steps = max(abs(py1 - py0), abs(px1 - px0), 1)
        ts = np.linspace(0, 1, n_steps + 1)
        ys = np.clip((py0 + (py1 - py0) * ts).astype(np.int32), 0, h - 1)
        xs = np.clip((px0 + (px1 - px0) * ts).astype(np.int32), 0, w - 1)
        np.maximum.at(canvas, (ys, xs), bright)

    # Cell body markers
    for sx, sy in bodies:
        iy = int(np.clip(sy, 0, h - 1))
        ix = int(np.clip(sx, 0, w - 1))
        canvas[iy, ix] = max(canvas[iy, ix], 1.0)

    # Gaussian blur adds soft dendritic glow halo
    blurred = _gauss(canvas, sigma=3.0)
    result = np.maximum(canvas, blurred)
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 35. HEAT_DISTORTION — convection shimmer waves
# ============================================================================

def heat_distortion(shape, seed, sm, wave_count=12, turbulence=4.0, **kwargs):
    """Heat mirage convection — rising shimmering waves of distorted air."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    result = np.zeros(shape, dtype=np.float32)
    for i in range(wave_count):
        freq_x = rng.uniform(4, 20)
        freq_y = rng.uniform(2, 8)
        phase = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.3, 1.0)
        # Waves that intensify toward top (rising heat)
        wave = np.sin(X * freq_x + Y * freq_y * turbulence + phase)
        intensity = (1.0 - Y) ** 1.5  # Stronger at top
        result += wave * amp * intensity

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 36. RUST_BLOOM — expanding oxidation fronts
# ============================================================================

def rust_bloom(shape, seed, sm, num_spots=25, max_radius=50, **kwargs):
    """Rust oxidation blooms — circular corrosion expanding from seed points."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)

    # Pre-generate all spot parameters
    n = num_spots
    cxs    = rng.rand(n).astype(np.float32) * w
    cys    = rng.rand(n).astype(np.float32) * h
    radii  = rng.uniform(8, max_radius, n).astype(np.float32)
    depths = rng.uniform(0.4, 0.9, n).astype(np.float32)
    edge_freqs = rng.uniform(5, 15, n).astype(np.float32)

    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    XX, YY = np.meshgrid(xx, yy)  # (h, w)

    result = np.ones(shape, dtype=np.float32) * 0.85

    # Process in batches to limit peak (B, h, w) memory
    batch = max(1, min(5, num_spots))
    for b_start in range(0, n, batch):
        b_end = min(b_start + batch, n)

        # (B, h, w)
        dX = XX[np.newaxis, :, :] - cxs[b_start:b_end, np.newaxis, np.newaxis]
        dY = YY[np.newaxis, :, :] - cys[b_start:b_end, np.newaxis, np.newaxis]
        r  = radii[b_start:b_end, np.newaxis, np.newaxis]
        d  = np.sqrt(dX**2 + dY**2)

        ring       = np.sin(d / r * np.pi * 3.0) * 0.3
        rust_depth = np.exp(-(d / r)**2 * 2.0) * depths[b_start:b_end, np.newaxis, np.newaxis]
        angle      = np.arctan2(dY, dX)
        ef         = edge_freqs[b_start:b_end, np.newaxis, np.newaxis]
        edge_noise = np.sin(angle * ef) * r * 0.15
        adjusted_d = d - edge_noise
        mask       = np.clip(1.0 - adjusted_d / r, 0, 1)
        result    -= ((rust_depth + ring * 0.5) * mask).sum(axis=0)

    return _sm_scale(_normalize(np.clip(result, 0, 1)), sm)


# ============================================================================
# 37. QUANTUM_NOISE — multi-frequency probability density field
# ============================================================================

def quantum_noise(shape, seed, sm, num_waves=30, **kwargs):
    """Quantum probability density — standing wave interference of many frequencies."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, np.pi * 4, h, dtype=np.float32)
    xx = np.linspace(0, np.pi * 4, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    psi_real = np.zeros(shape, dtype=np.float32)
    psi_imag = np.zeros(shape, dtype=np.float32)
    for _ in range(num_waves):
        kx = rng.uniform(-3, 3)
        ky = rng.uniform(-3, 3)
        phase = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.5, 1.5)
        psi_real += amp * np.cos(kx * X + ky * Y + phase)
        psi_imag += amp * np.sin(kx * X + ky * Y + phase)

    # Probability density |psi|^2
    prob = psi_real**2 + psi_imag**2
    return _sm_scale(_normalize(prob), sm)


# ============================================================================
# 38. WOVEN_MESH — fine interlocking thread mesh
# ============================================================================

def woven_mesh(shape, seed, sm, thread_spacing=10, thread_width=3, **kwargs):
    """Interlocking woven mesh — threads crossing over/under with spec variation."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Horizontal threads
    h_phase = (yy % thread_spacing) / thread_spacing
    h_thread = np.exp(-((h_phase - 0.5) * thread_spacing / thread_width)**2)

    # Vertical threads
    v_phase = (xx % thread_spacing) / thread_spacing
    v_thread = np.exp(-((v_phase - 0.5) * thread_spacing / thread_width)**2)

    # Over-under pattern: alternate which is on top
    cell_x = (xx / thread_spacing).astype(np.int32)
    cell_y = (yy / thread_spacing).astype(np.int32)
    over_under = ((cell_x + cell_y) % 2).astype(np.float32)

    # Where both threads exist, the "on top" one gets brighter spec
    both = h_thread * v_thread
    h_final = h_thread * (1.0 - both * over_under) * 0.8 + 0.1
    v_final = v_thread * (1.0 - both * (1.0 - over_under)) * 0.9 + 0.1

    result = np.maximum(h_final, v_final)
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 39. LAVA_CRACK — cooling lava with glowing fissures
# ============================================================================

def lava_crack(shape, seed, sm, num_plates=35, glow_width=4.0, **kwargs):
    """Cooling lava — dark solid plates with bright glowing cracks between them."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cx = rng.rand(num_plates) * w
    cy = rng.rand(num_plates) * h
    plate_dark = rng.uniform(0.05, 0.25, num_plates).astype(np.float32)

    centers = np.column_stack([cy.astype(np.float64), cx.astype(np.float64)])
    tree = cKDTree(centers)
    yy, xx = np.mgrid[0:h, 0:w]
    pts = np.column_stack([yy.ravel().astype(np.float64), xx.ravel().astype(np.float64)])
    dists, idxs = tree.query(pts, k=2, workers=-1)
    min_d    = dists[:, 0].reshape(shape).astype(np.float32)
    second_d = dists[:, 1].reshape(shape).astype(np.float32)
    closest  = idxs[:, 0].reshape(shape)

    # Crack brightness = inverse of edge distance
    edge_dist = second_d - min_d
    crack_glow = np.exp(-edge_dist / glow_width) * 0.95

    # Plate surface is dark with slight variation
    plate_surface = plate_dark[closest]

    result = np.maximum(plate_surface, crack_glow)
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 40. DIFFRACTION_GRATING — fine parallel lines creating spectrum spread
# ============================================================================

def diffraction_grating(shape, seed, sm, line_freq=80.0, num_orders=5, **kwargs):
    """Fine parallel ruling lines — diffractive spec modulation like a CD surface."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    angle = rng.uniform(0, np.pi)
    u = X * np.cos(angle) + Y * np.sin(angle)

    result = np.zeros(shape, dtype=np.float32)
    for order in range(1, num_orders + 1):
        freq = line_freq * order
        phase = rng.uniform(0, 2 * np.pi)
        intensity = 1.0 / order
        result += np.sin(u * freq * 2 * np.pi + phase) * intensity

    # Add subtle curvature (like CD tracks)
    r = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    curve = np.sin(r * line_freq * 1.5) * 0.3
    result += curve

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 41. SAND_DUNE — wind-blown sand ripple formations
# ============================================================================

def sand_dune(shape, seed, sm, dune_freq=15.0, wind_angle=0.3, **kwargs):
    """Wind-sculpted sand dunes — asymmetric ripples with slip faces."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    # Wind direction
    u = X * np.cos(wind_angle) + Y * np.sin(wind_angle)

    # Primary dunes with asymmetric profile (gentle windward, steep lee)
    dune = u * dune_freq
    profile = np.mod(dune, 1.0)
    # Asymmetric: gradual rise then sharp drop — both sides normalized to [0,1]
    gentle = np.clip(profile / 0.7, 0, 1)
    steep = np.clip((1.0 - profile) / (1.0 - 0.7), 0, 1)
    primary = np.where(profile < 0.7, gentle, steep)

    # Secondary ripples (smaller scale)
    v = -X * np.sin(wind_angle) + Y * np.cos(wind_angle)
    secondary = np.sin(u * dune_freq * 5.0 + v * 3.0 + rng.uniform(0, 6.28)) * 0.15

    # Large-scale undulation
    large = np.sin(u * 2.5 + rng.uniform(0, 6.28)) * np.sin(v * 1.8 + rng.uniform(0, 6.28)) * 0.2

    result = (primary + secondary + large).astype(np.float32)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 42. CIRCUIT_TRACE — PCB routing traces
# ============================================================================

def circuit_trace(shape, seed, sm, trace_count=40, **kwargs):
    """
    PCB circuit traces — Manhattan-routed conductive paths with pads.
    Vectorized: traces filled via numpy slice assignment; pads via vectorized
    circular mask per pad; glow halo via Gaussian blur of bright regions.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    result = np.full(shape, 0.15, dtype=np.float32)

    pad_centers = []  # (y, x, pad_r, brightness)

    for _ in range(trace_count):
        x = int(rng.integers(0, w))
        y = int(rng.integers(0, h))
        thickness = int(rng.integers(1, 4))
        brightness = float(rng.uniform(0.6, 1.0))
        num_segs = int(rng.integers(3, 10))

        for _ in range(num_segs):
            go_horiz = rng.random() < 0.5
            length = int(rng.integers(10, 80))
            sign = 1 if rng.random() < 0.5 else -1

            if go_horiz:
                x2 = int(np.clip(x + sign * length, 0, w - 1))
                y0c = max(0, y - thickness)
                y1c = min(h, y + thickness + 1)
                x_lo = min(x, x2); x_hi = max(x, x2)
                result[y0c:y1c, x_lo:x_hi] = brightness
                x = x2
            else:
                y2 = int(np.clip(y + sign * length, 0, h - 1))
                x0c = max(0, x - thickness)
                x1c = min(w, x + thickness + 1)
                y_lo = min(y, y2); y_hi = max(y, y2)
                result[y_lo:y_hi, x0c:x1c] = brightness
                y = y2

        pad_centers.append((y, x, thickness + 2, brightness))

    # Vectorized circular pad rendering
    for (py, px, pad_r, brightness) in pad_centers:
        y0p = max(0, py - pad_r); y1p = min(h, py + pad_r + 1)
        x0p = max(0, px - pad_r); x1p = min(w, px + pad_r + 1)
        dy_arr = np.arange(y0p, y1p, dtype=np.float32) - py
        dx_arr = np.arange(x0p, x1p, dtype=np.float32) - px
        dsq = dy_arr[:, np.newaxis]**2 + dx_arr[np.newaxis, :]**2
        mask = dsq <= pad_r * pad_r
        sub = result[y0p:y1p, x0p:x1p]
        sub[mask] = np.maximum(sub[mask], min(1.0, brightness + 0.15))
        result[y0p:y1p, x0p:x1p] = sub

    # Subtle glow halo via Gaussian blur of bright trace regions
    bright_mask = (result > 0.5).astype(np.float32)
    glow = _gauss(bright_mask, sigma=2.0) * 0.25
    result = np.clip(result + glow, 0.0, 1.0)

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 43. OIL_SLICK — thin-film oil interference with flowing shapes
# ============================================================================

def oil_slick(shape, seed, sm, num_pools=8, freq=6.0, **kwargs):
    """Oil film interference — organic flowing pools with rainbow-like banding."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    # Create smooth flowing thickness field — vectorize over all pools at once
    n = num_pools
    cxs   = rng.rand(n).astype(np.float32)
    cys   = rng.rand(n).astype(np.float32)
    sxs   = rng.uniform(0.1, 0.4, n).astype(np.float32)
    sys_  = rng.uniform(0.1, 0.4, n).astype(np.float32)
    angles= rng.uniform(0, np.pi, n).astype(np.float32)
    amps  = rng.uniform(0.5, 2.0, n).astype(np.float32)
    cos_a = np.cos(angles); sin_a = np.sin(angles)

    # (n, h, w) rotated coords
    dX = X[np.newaxis, :, :] - cxs[:, np.newaxis, np.newaxis]
    dY = Y[np.newaxis, :, :] - cys[:, np.newaxis, np.newaxis]
    dx = dX * cos_a[:, np.newaxis, np.newaxis] + dY * sin_a[:, np.newaxis, np.newaxis]
    dy = -dX * sin_a[:, np.newaxis, np.newaxis] + dY * cos_a[:, np.newaxis, np.newaxis]
    pools = np.exp(-(dx**2 / sxs[:, np.newaxis, np.newaxis]**2 +
                     dy**2 / sys_[:, np.newaxis, np.newaxis]**2))
    thickness = (pools * amps[:, np.newaxis, np.newaxis]).sum(axis=0).astype(np.float32)

    # Interference: sin of thickness gives rainbow banding
    interference = np.sin(thickness * freq * 2 * np.pi) * 0.5 + 0.5
    # Modulate by thickness (thicker = more visible)
    visibility = np.clip(thickness / thickness.max(), 0, 1) if thickness.max() > 0 else thickness
    result = interference * visibility * 0.8 + (1.0 - visibility) * 0.3

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 44. METEOR_IMPACT — radial crater with ejecta rays
# ============================================================================

def meteor_impact(shape, seed, sm, num_craters=3, **kwargs):
    """Meteor impact craters — radial ejecta rays with concentric shock rings."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(-1, 1, h, dtype=np.float32)
    xx = np.linspace(-1, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_craters):
        cx, cy = rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6)
        crater_r = rng.uniform(0.1, 0.35)
        dx, dy = X - cx, Y - cy
        r = np.sqrt(dx**2 + dy**2) + 1e-7
        theta = np.arctan2(dy, dx)

        # Crater bowl
        bowl = np.clip(1.0 - (r / crater_r)**2, 0, 1) * 0.4
        # Raised rim
        rim = np.exp(-((r - crater_r) / (crater_r * 0.15))**2) * 0.6

        # Ejecta rays — vectorized over all rays at once
        num_rays = rng.randint(8, 20)
        ray_angles = rng.uniform(0, 2 * np.pi, num_rays).astype(np.float32)
        ray_widths = rng.uniform(0.05, 0.15, num_rays).astype(np.float32)
        ray_decays = rng.uniform(1.0, 3.0, num_rays).astype(np.float32)
        # ang_dist: (h, w, num_rays)
        ang_dist = np.abs(np.mod(theta[:, :, np.newaxis] - ray_angles[np.newaxis, np.newaxis, :] + np.pi, 2*np.pi) - np.pi)
        ray_mask = np.exp(-(ang_dist / ray_widths[np.newaxis, np.newaxis, :])**2)
        ray_falloff_all = np.exp(-(r[:, :, np.newaxis] - crater_r) / (crater_r * ray_decays[np.newaxis, np.newaxis, :]))
        ray_falloff_all = np.where(r[:, :, np.newaxis] > crater_r, ray_falloff_all, 0.0)
        rays = (ray_mask * ray_falloff_all * 0.3).sum(axis=2).astype(np.float32)

        # Shock rings
        shock = np.sin((r - crater_r) / (crater_r * 0.3) * np.pi * 4) * 0.1
        shock = np.where(r > crater_r, shock * np.exp(-(r - crater_r) / crater_r), 0)

        result += rim + rays + shock - bowl

    return _sm_scale(_normalize(np.clip(result, 0, 1.5)), sm)


# ============================================================================
# 45. FUNGAL_NETWORK — mycelium interconnected threads
# ============================================================================

def fungal_network(shape, seed, sm, num_hyphae=60, **kwargs):
    """
    Mycelium fungal network — delicate interconnected branching threads.
    Vectorized: accumulate all random-walk path pixel coords into arrays,
    scatter brightness values to canvas, apply one Gaussian blur for glow.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)

    all_y = []
    all_x = []
    all_v = []

    for _ in range(num_hyphae):
        x0 = rng.uniform(0, w)
        y0 = rng.uniform(0, h)
        angle = rng.uniform(0, 2 * np.pi)
        speed = rng.uniform(1.5, 4.0)
        brightness = rng.uniform(0.5, 1.0)
        length = int(rng.integers(40, 150))

        delta_angles = rng.uniform(-0.4, 0.4, size=length)
        branch_mask  = rng.random(size=length) < 0.03
        branch_signs = rng.choice([-1.0, 1.0], size=length)
        branch_mags  = rng.uniform(0.5, 1.2, size=length)

        # Vectorized cumulative angle integration
        # Branches add extra delta at flagged steps
        effective_da = delta_angles + branch_mask * branch_signs * branch_mags
        # Cumulative angle at each step
        angles_arr = angle + np.cumsum(np.concatenate([[0.0], effective_da[:-1]]))
        # Cumulative positions
        dx_arr = np.cos(angles_arr) * speed
        dy_arr = np.sin(angles_arr) * speed
        xs_arr = (x0 + np.concatenate([[0.0], np.cumsum(dx_arr[:-1])])).astype(np.int32) % w
        ys_arr = (y0 + np.concatenate([[0.0], np.cumsum(dy_arr[:-1])])).astype(np.int32) % h

        all_y.extend(ys_arr.tolist())
        all_x.extend(xs_arr.tolist())
        all_v.extend([brightness] * length)

    if not all_y:
        return _flat(shape)

    canvas = np.zeros(shape, dtype=np.float32)
    ys = np.array(all_y, dtype=np.int32)
    xs = np.array(all_x, dtype=np.int32)
    vs = np.array(all_v, dtype=np.float32)
    np.add.at(canvas, (ys, xs), vs)
    canvas = np.clip(canvas, 0.0, 1.0)

    # Gaussian blur for soft glow around hyphae
    blurred = _gauss(canvas, sigma=2.0)
    result = np.maximum(canvas * 0.6, blurred)
    bmax = result.max()
    if bmax > 1e-7:
        result = result / bmax
    result = result * 0.9 + 0.1   # floor at 0.1

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 46. GRAVITY_WELL — spacetime distortion around singularity
# ============================================================================

def gravity_well(shape, seed, sm, num_wells=2, **kwargs):
    """Gravitational lensing — spacetime warped around singularity points."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(-1, 1, h, dtype=np.float32)
    xx = np.linspace(-1, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    # Background grid (gets distorted)
    grid_freq = 20.0
    bg_x = np.sin(X * grid_freq) * 0.5 + 0.5
    bg_y = np.sin(Y * grid_freq) * 0.5 + 0.5
    bg = (bg_x + bg_y) * 0.5

    # Warp field from gravity wells — store coordinates for reuse
    warp_x = np.zeros(shape, dtype=np.float32)
    warp_y = np.zeros(shape, dtype=np.float32)
    well_coords = []
    for _ in range(num_wells):
        wx, wy = rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)
        well_coords.append((wx, wy))
        mass = rng.uniform(0.05, 0.2)
        dx, dy = X - wx, Y - wy
        r = np.sqrt(dx**2 + dy**2) + 0.01
        force = mass / r**2
        warp_x += force * dx / r
        warp_y += force * dy / r

    # Apply warp to background
    warped_X = X + warp_x * 0.3
    warped_Y = Y + warp_y * 0.3
    warped_bg_x = np.sin(warped_X * grid_freq) * 0.5 + 0.5
    warped_bg_y = np.sin(warped_Y * grid_freq) * 0.5 + 0.5
    warped_bg = (warped_bg_x + warped_bg_y) * 0.5

    # Accretion ring brightness near event horizon — reuse stored well coordinates
    accretion = np.zeros(shape, dtype=np.float32)
    for wx, wy in well_coords:
        r = np.sqrt((X - wx)**2 + (Y - wy)**2) + 1e-7
        ring = np.exp(-((r - 0.08) / 0.03)**2) * 0.6
        accretion += ring

    result = warped_bg + accretion
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 47. SONIC_BOOM — Mach cone shockwave propagation
# ============================================================================

def sonic_boom(shape, seed, sm, num_sources=3, **kwargs):
    """Sonic boom shockwaves — Mach cone interference patterns."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(-1, 1, h, dtype=np.float32)
    xx = np.linspace(-1, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    result = np.zeros(shape, dtype=np.float32)

    for _ in range(num_sources):
        sx, sy = rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)
        mach_angle = rng.uniform(0.3, 0.8)  # Mach cone half-angle
        direction = rng.uniform(0, 2 * np.pi)

        dx = X - sx
        dy = Y - sy
        # Rotate to direction frame
        cos_d, sin_d = np.cos(direction), np.sin(direction)
        along = dx * cos_d + dy * sin_d
        perp = -dx * sin_d + dy * cos_d

        # Mach cone: |perp| / along = tan(mach_angle)
        cone_dist = np.abs(np.abs(perp) - along * np.tan(mach_angle))
        cone_mask = (along > 0).astype(np.float32)

        # Shockwave rings along cone
        shock = np.exp(-cone_dist**2 * 200.0) * cone_mask
        # Expanding rings behind — reduced frequency to reduce aliasing
        r = np.sqrt(dx**2 + dy**2)
        rings = np.sin(r * 15.0 - along * 15.0) * 0.3 * cone_mask * np.exp(-cone_dist * 5.0)

        result += shock + rings * 0.5

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 48. CRYSTAL_GROWTH — dendritic crystal frost formation
# ============================================================================

def crystal_growth(shape, seed, sm, num_seeds_pts=4, growth_steps=200, **kwargs):
    """
    Dendritic crystal growth — frost/snowflake branching solidification.
    Vectorized: pre-compute arm + branch paths as numpy arrays, scatter to canvas,
    Gaussian blur for soft crystalline glow. Coordinate swap bug (y,x) is fixed.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)

    canvas = np.zeros(shape, dtype=np.float32)
    all_y = []
    all_x = []
    all_v = []

    for _ in range(num_seeds_pts):
        cx = int(rng.integers(20, max(21, w - 20)))
        cy = int(rng.integers(20, max(21, h - 20)))
        base_angle = rng.uniform(0, np.pi / 3)

        for arm in range(6):
            arm_angle = base_angle + arm * np.pi / 3
            rand_dx = rng.uniform(-0.3, 0.3, size=growth_steps).astype(np.float32)
            rand_dy = rng.uniform(-0.3, 0.3, size=growth_steps).astype(np.float32)
            branch_mask  = rng.random(size=growth_steps) < 0.08
            branch_sides = rng.choice([-1, 1], size=growth_steps)
            branch_lens  = rng.integers(10, 40, size=growth_steps)

            # Vectorized main arm path
            steps_main = np.arange(growth_steps, dtype=np.float32)
            vals_main  = 1.0 - steps_main / growth_steps * 0.5

            step_dx = np.cos(arm_angle) * 1.5 + rand_dx
            step_dy = np.sin(arm_angle) * 1.5 + rand_dy

            arm_xs = cx + np.concatenate([[0.0], np.cumsum(step_dx[:-1])]).astype(np.float32)
            arm_ys = cy + np.concatenate([[0.0], np.cumsum(step_dy[:-1])]).astype(np.float32)

            py_arr = arm_ys.astype(np.int32) % h
            px_arr = arm_xs.astype(np.int32) % w
            all_y.extend(py_arr.tolist())
            all_x.extend(px_arr.tolist())
            all_v.extend(vals_main.tolist())

            # Side branches (already fast per-branch vectorization)
            branch_steps_idx = np.where(branch_mask)[0]
            for step in branch_steps_idx:
                val = float(vals_main[step])
                x_b = float(arm_xs[step])
                y_b = float(arm_ys[step])
                b_angle = arm_angle + branch_sides[step] * np.pi / 3
                b_len = int(branch_lens[step])
                if b_len > 0:
                    s = np.arange(b_len, dtype=np.float32)
                    bx_arr = x_b + np.cos(b_angle) * 1.2 * s
                    by_arr = y_b + np.sin(b_angle) * 1.2 * s
                    bval_arr = val * (1.0 - s / b_len) * 0.7
                    all_y.extend((by_arr.astype(np.int32) % h).tolist())
                    all_x.extend((bx_arr.astype(np.int32) % w).tolist())
                    all_v.extend(bval_arr.tolist())

    if all_y:
        ys = np.array(all_y, dtype=np.int32)
        xs = np.array(all_x, dtype=np.int32)
        vs = np.array(all_v, dtype=np.float32)
        np.maximum.at(canvas, (ys, xs), vs)

    blurred = _gauss(canvas, sigma=1.5)
    result = np.maximum(canvas, blurred * 0.7)
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 49. SMOKE_TENDRIL — rising smoke tendrils with turbulent mixing
# ============================================================================

def smoke_tendril(shape, seed, sm, num_plumes=6, **kwargs):
    """Rising smoke plumes — turbulent tendrils with billowing expansion."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    result = np.zeros(shape, dtype=np.float32)

    for _ in range(num_plumes):
        base_x = rng.uniform(0.1, 0.9)
        width_base = rng.uniform(0.02, 0.05)

        # Plume centerline with turbulent wandering
        n_freq = rng.randint(3, 8)
        centerline = np.zeros(h, dtype=np.float32) + base_x
        for f in range(n_freq):
            freq = rng.uniform(2, 10)
            amp = rng.uniform(0.02, 0.08) * (1.0 - yy * 0.3)  # More turbulent at top
            phase = rng.uniform(0, 2 * np.pi)
            centerline += np.sin(yy * freq * 2 * np.pi + phase) * amp

        # Width expands as smoke rises — narrow at source (bottom), wide at dispersal (top)
        plume_width = width_base + yy * 0.08
        dist_from_center = np.abs(X - centerline[:, np.newaxis])
        plume = np.exp(-(dist_from_center / plume_width[:, np.newaxis])**2)

        # Fade at bottom (source) and top (dissipation)
        vertical_fade = np.sin(np.clip(yy * np.pi, 0, np.pi))
        result += plume * vertical_fade[:, np.newaxis] * rng.uniform(0.4, 0.8)

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 50. FRACTAL_DISCHARGE — recursive branching electrical discharge
# ============================================================================

def fractal_discharge(shape, seed, sm, num_bolts=4, depth=8, **kwargs):
    """
    Recursive fractal electrical discharge — dense branching energy patterns.
    Vectorized: build segments iteratively via midpoint displacement (capped),
    rasterize onto a sparse canvas, Gaussian blur for electric glow.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    MAX_SEGS = 4000  # cap against exponential growth

    # --- Phase 1: collect segments via iterative stack ---
    segments = []  # (x1, y1, x2, y2, brightness)

    for _ in range(num_bolts):
        x1 = rng.uniform(0, w)
        y1 = float(rng.choice([0.0, float(h - 1)])) if rng.random() > 0.5 else rng.uniform(0, h)
        x2 = rng.uniform(0, w)
        y2 = rng.uniform(0, h)

        stack = [(x1, y1, x2, y2, 1.0, depth)]
        while stack and len(segments) < MAX_SEGS:
            sx1, sy1, sx2, sy2, br, dl = stack.pop()
            if dl <= 0:
                continue
            mx = (sx1 + sx2) / 2 + rng.uniform(-1, 1) * abs(sx2 - sx1) * 0.4
            my = (sy1 + sy2) / 2 + rng.uniform(-1, 1) * abs(sy2 - sy1) * 0.4
            mx = float(np.clip(mx, 0, w - 1))
            my = float(np.clip(my, 0, h - 1))

            segments.append((sx1, sy1, mx, my, br))
            segments.append((mx, my, sx2, sy2, br))

            stack.append((sx1, sy1, mx, my, br * 0.85, dl - 1))
            stack.append((mx, my, sx2, sy2, br * 0.85, dl - 1))

            if rng.random() < 0.35:
                bx = float(np.clip(mx + rng.uniform(-40, 40), 0, w - 1))
                by_s = float(np.clip(my + rng.uniform(-40, 40), 0, h - 1))
                stack.append((mx, my, bx, by_s, br * 0.5, dl - 2))

    if not segments:
        return _flat(shape)

    # --- Phase 2: rasterize all segments to a sparse canvas ---
    canvas = np.zeros(shape, dtype=np.float32)

    for (sx1, sy1, sx2, sy2, br) in segments:
        py0 = int(np.clip(sy1, 0, h - 1))
        px0 = int(np.clip(sx1, 0, w - 1))
        py1 = int(np.clip(sy2, 0, h - 1))
        px1 = int(np.clip(sx2, 0, w - 1))
        n_steps = max(abs(py1 - py0), abs(px1 - px0), 1)
        ts = np.linspace(0, 1, n_steps + 1)
        ys = np.clip((py0 + (py1 - py0) * ts).astype(np.int32), 0, h - 1)
        xs = np.clip((px0 + (px1 - px0) * ts).astype(np.int32), 0, w - 1)
        np.maximum.at(canvas, (ys, xs), br)

    # Gaussian blur for electric glow/corona effect
    blurred = _gauss(canvas, sigma=3.0)
    result = np.maximum(canvas * 0.5, blurred)

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 51. DIAMOND DUST — very fine dense sparkle on dark field
# ============================================================================

def diamond_dust(shape, seed, sm, density=0.003):
    """
    Thousands of tiny bright points on a near-black field.
    Like crushed diamonds: high-contrast ultra-fine sparkle.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    raw = rng.random((h, w)).astype(np.float32)
    threshold = 1.0 - density
    sparkle = np.where(raw > threshold, raw, 0.05).astype(np.float32)
    # Tiny blur for pixel-wide glow
    sparkle = _gauss(sparkle, sigma=0.4)
    return _sm_scale(_normalize(sparkle), sm).astype(np.float32)


# ============================================================================
# 52. METALLIC SAND — fine 2px block-quantized metallic particles
# ============================================================================

def metallic_sand(shape, seed, sm, block_size=2, flow_angle=0.18):
    """
    Metallic sand particles with directional flow alignment. Each particle is an
    elongated rectangle (2:1 aspect) rotated along a flow direction field, creating
    anisotropic sheen like metallic sand oriented by coating spray. The flow direction
    has gentle spatial variation from a low-freq noise field. Distinct from micro_sparkle
    (isotropic square blocks) and diamond_dust (per-pixel scatter).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    rng2 = np.random.RandomState(seed + 55)
    bs = max(2, block_size)
    # Flow direction field: gentle spatial variation
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    base_angle = rng2.uniform(0, np.pi)
    flow_field = base_angle + (np.sin(yy[:, np.newaxis] * 3.5 * np.pi + rng2.uniform(0, np.pi * 2)) *
                               np.cos(xx[np.newaxis, :] * 2.8 * np.pi + rng2.uniform(0, np.pi * 2))) * flow_angle
    # Anisotropic particle grid: elongated 2:1 in flow direction
    # Use rotated coordinate sampling for each particle cell
    ny, nx = max(2, (h + bs - 1) // bs), max(2, (w + bs - 1) // bs)
    particle_vals = rng.random((ny, nx)).astype(np.float32)
    # Assign each pixel to its particle cell
    yi = np.clip(np.arange(h) // bs, 0, ny - 1)
    xi = np.clip(np.arange(w) // bs, 0, nx - 1)
    base = particle_vals[yi[:, np.newaxis], xi[np.newaxis, :]]
    # Elongation: within each cell, brightness varies along flow direction
    # (bright at particle center-line, darker at particle edges perpendicular to flow)
    y_in_cell = (np.arange(h, dtype=np.float32) % bs) / bs - 0.5
    x_in_cell = (np.arange(w, dtype=np.float32) % bs) / bs - 0.5
    # Project cell-local position onto perpendicular-to-flow direction
    cos_f = np.cos(flow_field)
    sin_f = np.sin(flow_field)
    perp_dist = np.abs(y_in_cell[:, np.newaxis] * cos_f - x_in_cell[np.newaxis, :] * sin_f)
    # Particle profile: Gaussian falloff perpendicular to flow (elongated highlight)
    particle_profile = np.exp(-(perp_dist ** 2) / 0.08).astype(np.float32)
    result = base * (0.5 + 0.5 * particle_profile)
    # Per-pixel micro-variation (sand grain noise)
    result += rng.uniform(-0.05, 0.05, size=(h, w)).astype(np.float32)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 53. HOLOGRAPHIC FLAKE — iridescent scatter with sinusoidal position modulation
# ============================================================================

def holographic_flake(shape, seed, sm, density=0.004, freq_x=12.0, freq_y=9.0):
    """
    Iridescent flakes: random scatter modulated by sin(x)*sin(y) so brightness
    varies smoothly across the image — rainbow-like prismatic variation.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    # Base scatter
    raw = rng.random((h, w)).astype(np.float32)
    threshold = 1.0 - density
    sparkle = np.where(raw > threshold, 1.0, 0.0).astype(np.float32)
    # Position-dependent brightness modulation
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    ph1, ph2 = rng.uniform(0, 2 * np.pi, 2)
    mod = (np.sin(xx[np.newaxis, :] * freq_x * np.pi + ph1) *
           np.sin(yy[:, np.newaxis] * freq_y * np.pi + ph2)) * 0.5 + 0.5
    result = sparkle * (0.4 + 0.6 * mod) + 0.06
    blurred = _gauss(result, sigma=0.6)
    return _sm_scale(_normalize(blurred), sm).astype(np.float32)


# ============================================================================
# 54. CRYSTAL SHIMMER — small Voronoi cells with edge darkening
# ============================================================================

def crystal_shimmer(shape, seed, sm, cell_size=10, edge_width=0.25):
    """
    Faceted crystal-like sparkle: small Voronoi cells (8-12px) each get a random
    brightness; cell edges are darkened to simulate angular facet boundaries.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    cs = max(4, cell_size)
    ny = max(2, h // cs + 2)
    nx = max(2, w // cs + 2)
    iy_arr = np.arange(ny)
    ix_arr = np.arange(nx)
    IY, IX = np.meshgrid(iy_arr, ix_arr, indexing='ij')
    center_y = (IY.astype(np.float64) + rng.uniform(0.1, 0.9, (ny, nx))) * cs
    center_x = (IX.astype(np.float64) + rng.uniform(0.1, 0.9, (ny, nx))) * cs
    cell_vals = rng.uniform(0.15, 0.95, (ny, nx)).astype(np.float32).ravel()
    centers = np.column_stack([center_y.ravel(), center_x.ravel()])
    tree = cKDTree(centers)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    pts = np.column_stack([yy.ravel(), xx.ravel()])
    dists, idxs = tree.query(pts, k=2, workers=-1)
    d1 = dists[:, 0].reshape(shape).astype(np.float32)
    d2 = dists[:, 1].reshape(shape).astype(np.float32)
    nearest_val = cell_vals[idxs[:, 0]].reshape(shape)
    edge_factor = np.clip((d2 - d1) / (edge_width * cs + 0.01), 0, 1)
    result = nearest_val * (0.5 + 0.5 * edge_factor)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 55. STARDUST FINE — extremely fine high-density night-sky sparkle
# ============================================================================

def stardust_fine(shape, seed, sm, density=0.012):
    """
    Dense star-field sparkle with FBM density clustering and variable star magnitude.
    Stars cluster in nebula-like regions (FBM density map), each star has a random
    brightness class (dim/medium/bright), and bright stars get a larger cross-shaped
    diffraction spike. Distinct from diamond_dust (uniform sparse scatter + blur).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    rng2 = np.random.RandomState(seed + 77)
    # FBM density map: stars cluster in nebula-like regions
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    density_field = np.zeros(shape, dtype=np.float32)
    amp = 1.0
    for freq_s in [2.0, 4.5, 9.0]:
        ph = rng2.uniform(0, 2 * np.pi, 2)
        density_field += amp * (np.sin(yy[:, np.newaxis] * freq_s * np.pi * 2 + ph[0]) *
                                np.cos(xx[np.newaxis, :] * freq_s * np.pi * 2 + ph[1]) * 0.5 + 0.5)
        amp *= 0.5
    density_field = _normalize(density_field)
    # Per-pixel star placement weighted by density field
    raw = rng.random((h, w)).astype(np.float32)
    eff_threshold = 1.0 - density * (0.3 + density_field * 1.4)
    is_star = raw > eff_threshold
    # Magnitude classes: dim (0.2-0.4), medium (0.5-0.7), bright (0.8-1.0)
    magnitude = rng.uniform(0.0, 1.0, (h, w)).astype(np.float32)
    star_bright = np.where(magnitude > 0.7, rng.uniform(0.8, 1.0, (h, w)),
                  np.where(magnitude > 0.3, rng.uniform(0.45, 0.7, (h, w)),
                           rng.uniform(0.15, 0.4, (h, w)))).astype(np.float32)
    canvas = np.where(is_star, star_bright, 0.03).astype(np.float32)
    # Bright stars get a small cross-shaped diffraction spike (4-pixel arms)
    bright_mask = (is_star & (magnitude > 0.7)).astype(np.float32)
    spike = np.zeros(shape, dtype=np.float32)
    for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        spike += np.roll(bright_mask, dy, axis=0) * np.roll(np.ones_like(bright_mask), dx, axis=1) * 0.35
    canvas = np.maximum(canvas, spike * 0.4)
    # Soft nebula background glow from density field
    canvas += density_field * 0.06
    return _sm_scale(_normalize(canvas), sm).astype(np.float32)


# ============================================================================
# 56. PEARL MICRO — soft pearlescent micro-texture with sine harmonics
# ============================================================================

def pearl_micro(shape, seed, sm, octaves=4):
    """
    Soft undulating pearlescent brightness like mother-of-pearl.
    Multiple low-frequency sine harmonics combine for smooth iridescent variation.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    result = np.zeros(shape, dtype=np.float32)
    amp = 1.0
    for i in range(octaves):
        freq = 2.0 ** i * rng.uniform(1.5, 3.5)
        ph_y, ph_x = rng.uniform(0, 2 * np.pi), rng.uniform(0, 2 * np.pi)
        a = rng.uniform(0, np.pi)
        proj = yy[:, np.newaxis] * np.cos(a) + xx[np.newaxis, :] * np.sin(a)
        result += amp * np.sin(proj * freq * np.pi + ph_y)
        amp *= 0.55
    result = result * 0.5 + 0.5
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 57. GOLD FLAKE — large sparse gold-leaf style irregular flakes
# ============================================================================

def gold_flake(shape, seed, sm, density1=0.35, density2=0.3):
    """
    Sparse large flakes using two-noise thresholding for irregular blob shapes.
    Bright flakes on a medium-dark field — gold-leaf style.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    # Two independent noise fields: intersect them to get irregular blob shapes
    def _smooth_noise(freq, phase_seed):
        yy = np.arange(h, dtype=np.float32) / h
        xx = np.arange(w, dtype=np.float32) / w
        ps = np.random.RandomState(phase_seed)
        n = np.zeros(shape, dtype=np.float32)
        for _ in range(3):
            fy, fx = ps.uniform(freq * 0.5, freq * 1.5), ps.uniform(freq * 0.5, freq * 1.5)
            n += np.sin(yy[:, np.newaxis] * fy * np.pi + ps.uniform(0, 6.28)) * \
                 np.sin(xx[np.newaxis, :] * fx * np.pi + ps.uniform(0, 6.28))
        return _normalize(n)

    n1 = _smooth_noise(8.0, seed)
    n2 = _smooth_noise(10.0, seed + 1337)
    flakes = ((n1 > (1.0 - density1)) & (n2 > (1.0 - density2))).astype(np.float32)
    base = np.full(shape, 0.22, dtype=np.float32)
    result = base + flakes * 0.78
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 58. BRUSHED SPARKLE — directional anisotropic noise + embedded sparkle points
# ============================================================================

def brushed_sparkle(shape, seed, sm, sparkle_density=0.002):
    """
    Brushed metal texture with embedded sparkle: horizontally stretched noise
    creates the grain, random bright points add the sparkle on top.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    rng2 = np.random.default_rng(seed + 42)
    # Horizontal brushed grain: row-correlated noise
    base = rng.uniform(0.3, 0.7, size=h).astype(np.float32)
    # Smooth the rows
    kernel = np.ones(max(3, h // 80), dtype=np.float32)
    kernel /= kernel.sum()
    base = np.convolve(base, kernel, mode='same')
    grain = base[:, np.newaxis] + rng.uniform(-0.04, 0.04, size=(h, w)).astype(np.float32)
    grain = _normalize(grain)
    # Embedded sparkle
    raw = rng2.random((h, w)).astype(np.float32)
    threshold = 1.0 - sparkle_density
    sparkle = np.where(raw > threshold, 1.0, 0.0).astype(np.float32)
    sparkle = _gauss(sparkle, sigma=0.5)
    result = grain * 0.75 + sparkle * 0.25
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 59. CRUSHED GLASS — jagged angular bright fragments via sharp thresholding
# ============================================================================

def crushed_glass(shape, seed, sm, threshold_hi=0.72):
    """
    Jagged irregular bright fragments — high-frequency noise with sharp threshold
    creates angular bright shapes. Not smooth: harsh glass-shard edges.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    field = np.zeros(shape, dtype=np.float32)
    for _ in range(6):
        fy, fx = rng.uniform(20, 60), rng.uniform(20, 60)
        py, px = rng.uniform(0, 2 * np.pi), rng.uniform(0, 2 * np.pi)
        field += np.sin(yy[:, np.newaxis] * fy * np.pi + py) * \
                 np.sin(xx[np.newaxis, :] * fx * np.pi + px)
    field = _normalize(field)
    # Hard threshold for angular bright fragments
    bright = np.where(field > threshold_hi, field, 0.08).astype(np.float32)
    return _sm_scale(_normalize(bright), sm).astype(np.float32)


# ============================================================================
# 60. PRISMATIC DUST — multi-frequency sparkle + sin(dist) ring interference
# ============================================================================

def prismatic_dust(shape, seed, sm, scatter_density=0.005, ring_freq=18.0):
    """
    Fine scatter combined with sin(dist) rings from a center point — creates
    a prismatic interference halo overlaid on random sparkle dust.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    rng2 = np.random.RandomState(seed)
    # Scatter layer
    raw = rng.random((h, w)).astype(np.float32)
    threshold = 1.0 - scatter_density
    scatter = np.where(raw > threshold, 1.0, 0.05).astype(np.float32)
    scatter = _gauss(scatter, sigma=0.4)
    # Prismatic ring layer from a random center
    cy, cx = rng2.uniform(0.3, 0.7), rng2.uniform(0.3, 0.7)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    dist = np.sqrt(((yy[:, np.newaxis] - cy) * 2)**2 +
                   ((xx[np.newaxis, :] - cx) * 2)**2)
    rings = (np.sin(dist * ring_freq * np.pi) * 0.5 + 0.5).astype(np.float32)
    result = scatter * 0.55 + rings * 0.45
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 61. CHEVRON BANDS — V-shaped horizontal bands
# ============================================================================

def chevron_bands(shape, seed, sm, num_bands=20, v_angle=0.6, palette_size=8):
    """
    V-shaped bands: y + abs(x - w/2) * angle defines the band coordinate.
    Produces a chevron / arrowhead striping effect across the surface.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    palette = np.linspace(0.15, 0.85, palette_size, dtype=np.float32)
    rng.shuffle(palette)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    # Chevron coordinate
    coord = yy[:, np.newaxis] + np.abs(xx[np.newaxis, :] - w / 2.0) * v_angle
    # Normalize to [0, num_bands] and pick palette
    band_width = h / num_bands
    band_idx = (coord / band_width).astype(np.int32) % palette_size
    result = palette[band_idx]
    # Feather within band
    frac = (coord / band_width) - np.floor(coord / band_width)
    feather = np.where(frac < 0.15, frac / 0.15,
              np.where(frac > 0.85, (1.0 - frac) / 0.15, 1.0)).astype(np.float32)
    result = result * feather + result.mean() * (1.0 - feather)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 62. WAVE BANDS — sinusoidal wavy horizontal bands
# ============================================================================

def wave_bands(shape, seed, sm, num_bands=18, wave_freq=3.0, wave_amp=0.12,
               palette_size=8):
    """
    Sinusoidal wavy bands: y + sin(x * freq) * amplitude as band coordinate.
    Bands undulate left-right for an organic flowing stripe pattern.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    palette = np.linspace(0.15, 0.85, palette_size, dtype=np.float32)
    rng.shuffle(palette)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32) / w  # normalize x to 0-1
    ph = rng.uniform(0, 2 * np.pi)
    wave = np.sin(xx[np.newaxis, :] * wave_freq * np.pi * 2 + ph) * (wave_amp * h)
    coord = yy[:, np.newaxis] + wave
    band_width = h / num_bands
    band_idx = (np.abs(coord) / band_width).astype(np.int32) % palette_size
    result = palette[band_idx]
    frac = (np.abs(coord) / band_width) - np.floor(np.abs(coord) / band_width)
    feather = np.where(frac < 0.1, frac / 0.1,
              np.where(frac > 0.9, (1.0 - frac) / 0.1, 1.0)).astype(np.float32)
    result = result * feather + result.mean() * (1.0 - feather)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 63. GRADIENT BANDS — bands with internal bright-to-dark gradient
# ============================================================================

def gradient_bands(shape, seed, sm, num_bands=16, palette_size=6):
    """
    Each band fades from bright to dark across its width using fmod for banding
    and the fractional position within the band for the internal gradient.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    palette = np.linspace(0.2, 0.85, palette_size, dtype=np.float32)
    rng.shuffle(palette)
    band_width = h / num_bands
    yy = np.arange(h, dtype=np.float32)
    # Fractional position within each band [0, 1)
    frac = (yy / band_width) - np.floor(yy / band_width)
    # Band index
    band_idx = (np.floor(yy / band_width).astype(np.int32)) % palette_size
    base_val = palette[band_idx]
    # Gradient: bright at start of band (frac=0), dark at end (frac=1)
    gradient = base_val * (1.0 - frac * 0.65)
    result = gradient[:, np.newaxis] * np.ones(w, dtype=np.float32)[np.newaxis, :]
    # Add slight warp noise
    noise = rng.uniform(-0.03, 0.03, size=w).astype(np.float32)
    result += noise[np.newaxis, :]
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 64. SPLIT BANDS — alternating thick/thin bands with different intensities
# ============================================================================

def split_bands(shape, seed, sm, thick_count=10, thin_count=10,
                thick_bright=0.82, thin_bright=0.35):
    """
    Alternating thick bright bands and thin dark bands.
    Every pair: one wide high-value band followed by one narrow low-value band.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    # Build a 1D band map
    total_pairs = (thick_count + thin_count) // 2
    pair_height = h / max(1, total_pairs)
    thick_frac = thick_count / max(1, thick_count + thin_count)
    yy = np.arange(h, dtype=np.float32)
    pair_pos = (yy / pair_height) - np.floor(yy / pair_height)
    is_thick = pair_pos < thick_frac
    bright_jitter = rng.uniform(-0.06, 0.06, size=h).astype(np.float32)
    row_val = np.where(is_thick,
                       thick_bright + bright_jitter,
                       thin_bright + bright_jitter * 0.5).astype(np.float32)
    result = row_val[:, np.newaxis] * np.ones(w, dtype=np.float32)[np.newaxis, :]
    # Add slight column noise
    result += rng.uniform(-0.02, 0.02, size=(h, w)).astype(np.float32)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 65. DIAGONAL BANDS — 45-degree angled bands
# ============================================================================

def diagonal_bands(shape, seed, sm, num_bands=20, palette_size=8, angle_deg=45.0):
    """
    Bands running at an angle (default 45°). Band coordinate is
    (x*cos(a) + y*sin(a)) / sqrt(2) for true diagonal width independence.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    palette = np.linspace(0.15, 0.85, palette_size, dtype=np.float32)
    rng.shuffle(palette)
    angle = np.deg2rad(angle_deg + rng.uniform(-5, 5))
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    # Projected diagonal coordinate
    coord = yy[:, np.newaxis] * np.sin(angle) + xx[np.newaxis, :] * np.cos(angle)
    # Normalize so num_bands fits across the diagonal span
    span = h * np.sin(angle) + w * np.cos(angle)
    band_width = span / num_bands
    band_idx = (np.abs(coord) / band_width).astype(np.int32) % palette_size
    result = palette[band_idx]
    frac = (np.abs(coord) / band_width) - np.floor(np.abs(coord) / band_width)
    feather = np.where(frac < 0.12, frac / 0.12,
              np.where(frac > 0.88, (1.0 - frac) / 0.12, 1.0)).astype(np.float32)
    result = result * feather + result.mean() * (1.0 - feather)
    return _sm_scale(_normalize(result), sm).astype(np.float32)



# ============================================================================
# PRIORITY 2 BATCH A — 🪛 DIRECTIONAL BRUSHED (66–77)
# Roughness channel (Green) optimized — simulates physical surface texture direction
# ============================================================================

def brushed_linear(shape, seed, sm, frequency=80.0, phase_noise=0.02, **kwargs):
    """
    Pure horizontal parallel lines — sin(y * freq) with zero x-modulation.
    The definitive G=Roughness brushed aluminum spec overlay pattern.
    Bright = rough/matte, dark = smooth/reflective in roughness channel.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    noise = rng.uniform(-phase_noise, phase_noise, size=h).astype(np.float32)
    result = np.sin((yy + noise) * frequency * np.pi * 2.0)
    out = result[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
    return _sm_scale(_normalize(out), sm).astype(np.float32)


def brushed_diagonal(shape, seed, sm, frequency=70.0, angle_deg=45.0, phase_noise=0.015, **kwargs):
    """
    Diagonal brushed lines via rotated coordinate projection.
    Angle defaults 45° — great for chevron-style panel polish. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    angle = np.deg2rad(angle_deg + rng.uniform(-3.0, 3.0))
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    proj = yy[:, np.newaxis] * np.sin(angle) + xx[np.newaxis, :] * np.cos(angle)
    noise = rng.normal(0, phase_noise * 0.5, size=shape).astype(np.float32)
    result = np.sin((proj + noise) * frequency * np.pi * 2.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def brushed_cross(shape, seed, sm, frequency=60.0, x_weight=0.5, y_weight=0.5, **kwargs):
    """
    Bidirectional cross-brushed — orthogonal H+V strokes additive blend.
    Simulates cross-brushed stainless / scotch-brite finishing. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    h_lines = np.sin(yy * frequency * np.pi * 2.0)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
    v_lines = np.sin(xx * frequency * np.pi * 2.0)[np.newaxis, :] * np.ones((h, 1), dtype=np.float32)
    result = h_lines * y_weight + v_lines * x_weight
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def brushed_radial(shape, seed, sm, num_lines=120, phase_noise=0.03, **kwargs):
    """
    Radial lines from center — machined disc or spinner radial polish.
    sin(theta * num_lines) produces spoke-like radial scratches. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    theta = np.arctan2(yy - cy, xx - cx)
    noise = rng.normal(0, phase_noise, size=shape).astype(np.float32)
    result = np.sin((theta + noise) * num_lines)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def brushed_arc(shape, seed, sm, frequency=50.0, center_y_frac=1.5, **kwargs):
    """
    Concentric arc sweeps from off-canvas center — belt-sanded panel with slight bow.
    Center below image creates bowed horizontal lines realistic for large panel polishing. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    center_y = h * center_y_frac + rng.uniform(-h * 0.1, h * 0.1)
    center_x = w * (0.5 + rng.uniform(-0.1, 0.1))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((yy - center_y) ** 2 + (xx - center_x) ** 2)
    result = np.sin(dist / max(h, w) * frequency * np.pi * 2.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def hairline_polish(shape, seed, sm, frequency=200.0, micro_wobble=0.004, **kwargs):
    """
    Precision hairline polish — ultra-fine primary horizontal grooves (200Hz) with subordinate
    perpendicular micro-scratches (400Hz, 12% weight) from abrasive particle contacts.
    Physically distinct from brushed_linear: bidirectional micro-texture catches cross-angle light.
    Classic premium stainless / watch-case / appliance-grade satin character. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    # Primary: ultra-fine horizontal parallels with near-zero waviness
    micro_noise = rng.uniform(-micro_wobble, micro_wobble, size=h).astype(np.float32)
    primary = np.sin((yy + micro_noise) * frequency * np.pi * 2.0)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
    # Secondary: perpendicular micro-scratches at 2× frequency, 12% weight
    # Abrasive particle contacts leave finer cross-grain marks absent from brushed_linear
    secondary = np.sin(xx * frequency * 2.0 * np.pi * 2.0)[np.newaxis, :] * np.ones((h, 1), dtype=np.float32)
    result = primary + secondary * 0.12
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def lathe_concentric(shape, seed, sm, frequency=60.0, spiral_drift=0.5, **kwargs):
    """
    Lathe-turned concentric rings with optional spiral drift — machined billet part face.
    sin(dist + theta*drift) produces near-perfect rings with realistic tool-path spiral. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy = h / 2.0 + rng.uniform(-h * 0.05, h * 0.05)
    cx = w / 2.0 + rng.uniform(-w * 0.05, w * 0.05)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    theta = np.arctan2(yy - cy, xx - cx)
    coord = dist / max(h, w) + theta / (2.0 * np.pi) * spiral_drift * (dist / max(h, w))
    result = np.sin(coord * frequency * np.pi * 2.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def bead_blast_uniform(shape, seed, sm, grain_size=3.0, isotropy=0.95, **kwargs):
    """
    Bead-blasted metal — uniform isotropic fine pit texture, no directionality.
    Two-scale noise: coarse cell grid blurred for bead pits + fine noise for grain. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    gs = max(2, int(grain_size))
    gh, gw = max(2, h // gs), max(2, w // gs)
    coarse = rng.uniform(0, 1, size=(gh, gw)).astype(np.float32)
    rep_y = int(np.ceil(h / gh))
    rep_x = int(np.ceil(w / gw))
    upsampled = np.repeat(np.repeat(coarse, rep_y, axis=0), rep_x, axis=1)[:h, :w]
    blurred = _gauss(upsampled, sigma=grain_size * 0.8)
    fine = rng.uniform(0, 1, size=shape).astype(np.float32)
    result = blurred * isotropy + fine * (1.0 - isotropy)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def orbital_swirl(shape, seed, sm, num_passes=8, orbit_radius_frac=0.3, frequency=40.0, **kwargs):
    """
    DA orbital polisher marks — overlapping circular arc brushed regions.
    Multiple passes each create a ring of tangential lines at their orbit radius. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    result = np.zeros(shape, dtype=np.float32)
    orbit_r = min(h, w) * orbit_radius_frac
    for _ in range(num_passes):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        reach = orbit_r * rng.uniform(0.7, 1.3)
        mask = np.exp(-((dist - reach) / max(reach * 0.2, 2.0)) ** 2)
        theta = np.arctan2(yy - cy, xx - cx)
        arc_lines = np.sin(theta * frequency) * mask
        result += arc_lines
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def buffer_swirl(shape, seed, sm, num_centers=20, swirl_radius_frac=0.15, **kwargs):
    """
    Random circular buffer swirl marks — multiple independent arc rings.
    Simulates car-wash buffer or aggressive compound polishing swirl artifacts. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    result = np.zeros(shape, dtype=np.float32)
    base_r = min(h, w) * swirl_radius_frac
    for _ in range(num_centers):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        r = base_r * rng.uniform(0.5, 2.0)
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        ring = np.exp(-((dist - r) / max(r * 0.08, 2.0)) ** 2)
        result += ring * rng.uniform(0.5, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def wire_brushed_coarse(shape, seed, sm, frequency=25.0, waviness=0.06, **kwargs):
    """
    Coarse wire-brushed texture — low-frequency, high-amplitude directional grain.
    Wide visible parallel scratches with wandering path warp. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    # Cumulative random warp: creates wandering brush path
    warp = np.cumsum(rng.uniform(-waviness / w, waviness / w, size=w)).astype(np.float32)
    warp -= warp.mean()
    eff_y = yy[:, np.newaxis] + warp[np.newaxis, :]
    result = np.sin(eff_y * frequency * np.pi * 2.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def hand_polished(shape, seed, sm, num_regions=12, strokes_per_region=8, **kwargs):
    """
    Hand polishing marks — short directional strokes with random angle per region.
    Simulates wax-on/wax-off hand polishing — each zone has its own preferred direction. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    result = np.zeros(shape, dtype=np.float32)
    weight = np.zeros(shape, dtype=np.float32)
    for _ in range(num_regions):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        region_r = min(h, w) * rng.uniform(0.15, 0.35)
        angle = rng.uniform(0, np.pi)
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        w_region = np.exp(-(dist / max(region_r, 1.0)) ** 2)
        proj = (yy - cy) * np.sin(angle) + (xx - cx) * np.cos(angle)
        freq = rng.uniform(20, 60)
        lines = np.sin(proj / max(region_r, 1.0) * freq)
        result += lines * w_region
        weight += w_region
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(weight > 0.001, result / weight, 0.5)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH B — ⌚ GUILLOCHÉ & MACHINED (78–89)
# R=Metallic and G=Roughness — watch-dial engine turning, knurling, precision machining
# ============================================================================

def guilloche_barleycorn(shape, seed, sm, frequency=40.0, n_lobes=8, amplitude=0.3, **kwargs):
    """
    Classic guilloche barleycorn — lobed concentric rings via polar amplitude modulation.
    r*(1+A*cos(n*theta)) distorts radial frequency into interlocking oval corn cells. R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy = h / 2.0 + rng.uniform(-h * 0.03, h * 0.03)
    cx = w / 2.0 + rng.uniform(-w * 0.03, w * 0.03)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / max(h, w)
    theta = np.arctan2(yy - cy, xx - cx)
    r_mod = r * (1.0 + amplitude * np.cos(n_lobes * theta))
    result = np.sin(r_mod * frequency * np.pi * 2.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def guilloche_hobnail(shape, seed, sm, spacing=16, dome_radius_frac=0.45, **kwargs):
    """
    Guilloche hobnail — square-grid array of hemispherical dome protrusions.
    Modular cx/cy to nearest cell center, smooth dome profile. R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = (xx % spacing) - spacing * 0.5
    cy = (yy % spacing) - spacing * 0.5
    r = np.sqrt(cx ** 2 + cy ** 2)
    result = np.clip(1.0 - r / (spacing * dome_radius_frac), 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def guilloche_waves(shape, seed, sm, x_freq=60.0, y_mod_freq=8.0, amplitude=0.15, **kwargs):
    """
    Classic guilloche engine-turned wave — phase-modulated sweep lines.
    sin(x*freq + A*sin(y*mod)) creates flowing undulating wave sheets. R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    phase = amplitude * np.sin(yy * y_mod_freq * np.pi * 2.0 + rng.uniform(0, np.pi))
    carrier = np.sin((xx[np.newaxis, :] + phase[:, np.newaxis]) * x_freq * np.pi * 2.0)
    return _sm_scale(_normalize(carrier), sm).astype(np.float32)


def guilloche_sunray(shape, seed, sm, n_rays=72, ring_freq=20.0, ray_fade=0.6, **kwargs):
    """
    Engine-turned sunray — radial lines + concentric rings polar cross-hatch.
    sin(theta*n)*(1-r*fade) + cos(r*freq) creates the pocket-watch dial character. R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy = h / 2.0 + rng.uniform(-h * 0.02, h * 0.02)
    cx = w / 2.0 + rng.uniform(-w * 0.02, w * 0.02)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / max(h, w)
    theta = np.arctan2(yy - cy, xx - cx)
    rays = np.sin(theta * n_rays) * np.clip(1.0 - r * ray_fade, 0.0, 1.0)
    rings = np.cos(r * ring_freq * np.pi * 2.0) * 0.3
    result = rays + rings
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def guilloche_moire_eng(shape, seed, sm, freq=30.0, offset_frac=0.15, **kwargs):
    """
    Engine-turned moire — interference between two offset concentric ring systems.
    Two sources at cx+-offset beat into flowing moire ellipses. R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy = h / 2.0
    offset = w * offset_frac + rng.uniform(-w * 0.02, w * 0.02)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r1 = np.sqrt((yy - cy) ** 2 + (xx - (w / 2 - offset / 2)) ** 2) / max(h, w)
    r2 = np.sqrt((yy - cy) ** 2 + (xx - (w / 2 + offset / 2)) ** 2) / max(h, w)
    result = (np.sin(r1 * freq * np.pi * 2.0) + np.sin(r2 * freq * np.pi * 2.0)) * 0.5
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def jeweling_circles(shape, seed, sm, spacing=14, circle_radius_frac=0.55, **kwargs):
    """
    Jeweling (spotfacing) — hex-close-packed overlapping circles, scalloped at intersections.
    Vectorized nearest-center per row (O(h*w)), max across 2 rows for overlap. R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row_h = np.float32(spacing * 0.8660254)
    r = spacing * circle_radius_frac
    row_base = np.floor(yy / row_h).astype(np.int32)
    result = np.zeros(shape, dtype=np.float32)
    for drow in [0, 1]:
        row_i = row_base + drow
        row_offset_x = (row_i % 2) * spacing * 0.5
        col_i = np.round((xx - row_offset_x) / spacing).astype(np.int32)
        cx_c = col_i * spacing + row_offset_x
        cy_c = row_i * row_h
        dist = np.sqrt((yy - cy_c) ** 2 + (xx - cx_c) ** 2)
        result = np.maximum(result, np.clip(1.0 - dist / r, 0.0, 1.0))
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def knurl_diamond(shape, seed, sm, frequency=30.0, angle_deg=45.0, **kwargs):
    """
    Diamond knurl — product of two crossed diagonal sin lines, raised diamond peaks.
    abs(sin(proj1)) * abs(sin(proj2)) — peaks only at both-high intersections. G=Roughness + R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    angle = np.deg2rad(angle_deg + rng.uniform(-2, 2))
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    proj1 = yy[:, np.newaxis] * np.sin(angle) + xx[np.newaxis, :] * np.cos(angle)
    proj2 = yy[:, np.newaxis] * np.sin(-angle) + xx[np.newaxis, :] * np.cos(-angle)
    result = np.abs(np.sin(proj1 * frequency * np.pi * 2.0)) * np.abs(np.sin(proj2 * frequency * np.pi * 2.0))
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def knurl_straight(shape, seed, sm, frequency=40.0, sharpness=3.0, **kwargs):
    """
    Straight knurl — horizontal ridges sharpened from sine to discrete stepped form.
    sign(sin)*|sin|^(1/sharp) compresses peaks up, flattens valleys into ridges. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h
    wave = np.sin(yy * frequency * np.pi * 2.0)
    ridge = np.sign(wave) * np.abs(wave) ** (1.0 / max(sharpness, 0.1))
    out = ridge[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
    return _sm_scale(_normalize(out), sm).astype(np.float32)


def face_mill_bands(shape, seed, sm, pass_width=60, freq=20.0, **kwargs):
    """
    Face milling — parallel circular arc scallops from sequential cutter passes.
    Each pass: ring from (cy=h/2, cx=i*pass_width); accumulated arcs create scallops. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy = h / 2.0
    n_passes = w // max(pass_width, 1) + 2
    result = np.zeros(shape, dtype=np.float32)
    for i in range(-1, n_passes):
        cx_pass = i * pass_width + rng.uniform(-pass_width * 0.05, pass_width * 0.05)
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx_pass) ** 2)
        result += np.sin(dist / max(h, w) * freq * np.pi * 2.0)
    result /= max(n_passes, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def fly_cut_arcs(shape, seed, sm, cutter_radius_frac=1.2, pass_pitch=40, **kwargs):
    """
    Fly cutting — overlapping large-radius scalloped arcs from single-point cutter passes.
    Gaussian ring at r_cutter from far-below center; adjacent pitches create scallops. G=Roughness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r_cutter = max(h, w) * cutter_radius_frac
    arc_width = max(h, w) * 0.02
    cy_pass = h * 2.0
    n_passes = w // max(pass_pitch, 1) + 2
    result = np.zeros(shape, dtype=np.float32)
    for i in range(-1, n_passes):
        cx_pass = i * pass_pitch + rng.uniform(-pass_pitch * 0.05, pass_pitch * 0.05)
        dist = np.sqrt((yy - cy_pass) ** 2 + (xx - cx_pass) ** 2)
        result += np.exp(-((dist - r_cutter) / arc_width) ** 2)
    result /= max(n_passes, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def engraved_crosshatch(shape, seed, sm, frequency=50.0, angle_deg=30.0, **kwargs):
    """
    Precision engraved crosshatch — additive fine parallel lines at +-angle.
    Additive (vs knurl_diamond product) gives uniform weight at all grid points. G=Roughness.
    Variable-depth FBM modulation along groove direction simulates hand-engraving pressure variation:
    some zones emphasise one line family, others the second — classic tonal vignetting of intaglio prints.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    angle = np.deg2rad(angle_deg + rng.uniform(-2, 2))
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    proj1 = yy[:, np.newaxis] * np.sin(angle) + xx[np.newaxis, :] * np.cos(angle)
    proj2 = yy[:, np.newaxis] * np.sin(-angle) + xx[np.newaxis, :] * np.cos(-angle)
    lines1 = np.sin(proj1 * frequency * np.pi * 2.0)
    lines2 = np.sin(proj2 * frequency * np.pi * 2.0)
    # Variable-depth modulation: slow multi-scale envelope varies groove depth across the image.
    # Physical basis: engraver pressure varies across a plate — deeper grooves hold more ink,
    # producing tonal variation. Two independent fields so each line family can independently fade.
    depth1 = multi_scale_noise(shape, [max(h // 6, 8), max(h // 12, 4)], [0.6, 0.4], seed + 200)
    depth1 = (depth1 - depth1.min()) / max(depth1.max() - depth1.min(), 1e-7)
    depth2 = multi_scale_noise(shape, [max(h // 5, 8), max(h // 10, 4)], [0.55, 0.45], seed + 201)
    depth2 = (depth2 - depth2.min()) / max(depth2.max() - depth2.min(), 1e-7)
    # Weight each family: 0.55-1.0 range so neither family ever disappears fully
    amp1 = 0.55 + depth1 * 0.45
    amp2 = 0.55 + depth2 * 0.45
    result = (lines1 * amp1 + lines2 * amp2) * 0.5
    return _sm_scale(_normalize(result.astype(np.float32)), sm).astype(np.float32)


def edm_dimple(shape, seed, sm, spacing=12, dimple_radius_frac=0.4, **kwargs):
    """
    EDM dimple texture — hex-close-packed spherical craters, bright rim, dark pit.
    Vectorized hex-grid; inverted dome (1-spherical profile) = circular pit. G=Roughness + R=Metallic.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row_h = np.float32(spacing * 0.8660254)
    r = spacing * dimple_radius_frac
    row_base = np.floor(yy / row_h).astype(np.int32)
    result = np.zeros(shape, dtype=np.float32)
    for drow in [0, 1]:
        row_i = row_base + drow
        row_offset_x = (row_i % 2) * spacing * 0.5
        col_i = np.round((xx - row_offset_x) / spacing).astype(np.int32)
        cx_c = col_i * spacing + row_offset_x
        cy_c = row_i * row_h
        dist = np.sqrt((yy - cy_c) ** 2 + (xx - cx_c) ** 2)
        pit = np.clip(1.0 - (dist / r) ** 2, 0.0, 1.0)
        result = np.maximum(result, pit)
    result = 1.0 - result  # Invert: bright rim, dark pit
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH B — ⌚ GUILLOCHÉ & ENGINE TURNING (78–89) — SPEC OVERLAY SET
# Watch-dial precision: rose engine, engine turning, sunburst, cloisonné, damascene, moiré
# ============================================================================

def guilloche_straight(shape, seed, sm, frequency=50.0, pitch=0.02, phase_vary=0.008, **kwargs):
    """Straight-line guilloché — tight-pitch sinusoidal parallels with x-amplitude modulation, groove/land metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    # Amplitude envelope across x: sin(x*freq) creates bright/dark column zones
    A = np.sin(xx * frequency * np.pi * 2.0)[np.newaxis, :]
    # Phase shifts subtly with x — creates sinusoidal wandering lines
    phase_shift = np.sin(xx * 6.0 * np.pi) * phase_vary
    rows = np.sin(yy[:, np.newaxis] / pitch * np.pi * 2.0 + phase_shift[np.newaxis, :])
    result = rows * (0.5 + 0.5 * A)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def guilloche_wavy(shape, seed, sm, freq=45.0, angle_diff_deg=7.0, **kwargs):
    """Wavy guilloché — two sinusoid families at slight angle difference, beating creates shimmering wave metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    eps = np.deg2rad(angle_diff_deg)
    # Family 1: horizontal lines
    f1 = np.sin(Y * freq * np.pi * 2.0)
    # Family 2: rotated by eps creates beating interference
    f2 = np.sin((Y * np.cos(eps) + X * np.sin(eps)) * freq * np.pi * 2.0)
    result = f1 * f2  # Amplitude modulation: envelope is the interference pattern
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def guilloche_basket(shape, seed, sm, frequency=40.0, **kwargs):
    """Basket-weave guilloché — two 90° sinusoid families phase-shifted half-period per band for over/under 3D depth."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Band index per axis
    v_band = np.floor(X * frequency).astype(np.int32)
    h_phase = ((v_band % 2) * np.pi).astype(np.float32)
    h_lines = np.sin(Y * frequency * np.pi * 2.0)
    v_lines = np.sin(X * frequency * np.pi * 2.0 + h_phase)
    # Interleave: horizontal strands over even v-bands, vertical over odd
    weave_select = ((v_band % 2) == 0).astype(np.float32)
    result = h_lines * weave_select + v_lines * (1.0 - weave_select)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def sunburst_rays(shape, seed, sm, n_rays=128, **kwargs):
    """Precision radial ray engraving — 128+ even/odd groove-land alternating rays with feathered edges."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    theta = np.arctan2(yy - cy, xx - cx)
    # Fractional position within ray cycle
    ray_frac = ((theta + np.pi) / (np.pi * 2.0) * n_rays) % 1.0
    # Even/odd alternation with cosine feather at ray edges
    ray_idx = np.floor((theta + np.pi) / (np.pi * 2.0) * n_rays).astype(np.int32)
    base = (ray_idx % 2).astype(np.float32)
    edge_feather = np.cos((ray_frac - 0.5) * np.pi * 2.0)
    result = base * 0.6 + edge_feather * 0.4
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def sunburst_wavy_rays(shape, seed, sm, n_rays=96, waver_freq=6.0, waver_amp=0.015, **kwargs):
    """Wavy-width radial rays — ray boundaries waver sinusoidally in r, creating spinning optical illusion."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy, dx = yy - cy, xx - cx
    theta = np.arctan2(dy, dx)
    r = np.sqrt(dy * dy + dx * dx) / (min(h, w) * 0.5 + 1e-6)
    # Width modulation: waver_amp * sin(r * waver_freq * 2π) varies ray width with radius
    width_mod = waver_amp * np.sin(r * waver_freq * np.pi * 2.0)
    eff_theta = theta + width_mod
    ray_frac = ((eff_theta + np.pi) / (np.pi * 2.0) * n_rays) % 1.0
    result = np.cos(ray_frac * np.pi * 2.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cloisonne_grid(shape, seed, sm, scale=16.0, wire_width=0.12, **kwargs):
    """Cloisonné raised wire grid — high-metallic wire lines, smooth-center cell interior roughness gradient."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h * scale
    xx = np.arange(w, dtype=np.float32) / w * scale
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    fy = Y % 1.0
    fx = X % 1.0
    dist_y = np.minimum(fy, 1.0 - fy)
    dist_x = np.minimum(fx, 1.0 - fx)
    wire_dist = np.minimum(dist_y, dist_x)
    # Wire proximity mask: near wire = full metallic, interior = smooth gradient
    wire_mask = np.clip(1.0 - wire_dist / wire_width, 0.0, 1.0)
    center_dist = wire_dist / 0.5
    result = wire_mask * 1.0 + (1.0 - wire_mask) * (1.0 - center_dist * 0.8)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def damascene_inlay(shape, seed, sm, freq=14.0, node_sharpness=4.0, **kwargs):
    """Damascene inlay — abs(sin)·abs(sin) nodes with metallic peaks at intersections, gold-inlay geometry."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Node: both axes high simultaneously
    node = (np.abs(np.sin(X * freq * np.pi)) * np.abs(np.sin(Y * freq * np.pi))) ** node_sharpness
    # Cross arms: partial high in one axis — lower metallic weave between nodes
    h_cross = np.abs(np.sin(Y * freq * np.pi)) ** (node_sharpness * 0.4)
    v_cross = np.abs(np.sin(X * freq * np.pi)) ** (node_sharpness * 0.4)
    result = node * 1.0 + (h_cross + v_cross) * 0.25 - (1.0 - node) * 0.15
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def moire_engine(shape, seed, sm, freq=40.0, rotation_deg=5.0, **kwargs):
    """Moiré interference guilloché — two slightly-rotated vertical line families beat into emergent interference bands."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    eps = np.deg2rad(rotation_deg)
    # Family 1: pure vertical lines
    f1 = np.sin(X * freq * np.pi * 2.0)
    # Family 2: rotated by eps — the slight mis-alignment creates beating envelope
    f2 = np.sin((X * np.cos(eps) + Y * np.sin(eps)) * freq * np.pi * 2.0)
    result = f1 + f2
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH C -- WORN, PATINA & WEATHERING (90-101)
# R=Metallic (0=none,255=full), G=Roughness (0=mirror,255=matte),
# B=Clearcoat INVERTED (16=max gloss, 255=dull)
# ============================================================================

def spec_rust_bloom(shape, seed, sm, num_seeds=30, bloom_radius_frac=0.12, **kwargs):
    """Multi-scale Worley-noise rust blooms: metallic drops to zero at bloom centers, roughness peaks."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sy = rng.uniform(0, h, size=num_seeds).astype(np.float32)
    sx = rng.uniform(0, w, size=num_seeds).astype(np.float32)
    pts = np.stack([sy, sx], axis=1)
    tree = cKDTree(pts)
    coords = np.column_stack([yy.ravel(), xx.ravel()])
    dists, _ = tree.query(coords, k=1)
    dists = dists.reshape(shape).astype(np.float32)
    max_r = min(h, w) * bloom_radius_frac
    bloom = np.clip(1.0 - dists / max(max_r, 1.0), 0.0, 1.0)
    sy2 = rng.uniform(0, h, size=num_seeds * 4).astype(np.float32)
    sx2 = rng.uniform(0, w, size=num_seeds * 4).astype(np.float32)
    pts2 = np.stack([sy2, sx2], axis=1)
    tree2 = cKDTree(pts2)
    dists2, _ = tree2.query(coords, k=1)
    dists2 = dists2.reshape(shape).astype(np.float32)
    bloom2 = np.clip(1.0 - dists2 / max(max_r * 0.4, 1.0), 0.0, 1.0)
    rust = np.clip(bloom * 0.7 + bloom2 * 0.3, 0.0, 1.0)
    result = 1.0 - rust
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_patina_verdigris(shape, seed, sm, octaves=5, persistence=0.55, **kwargs):
    """FBM-inverted patina: verdigris accumulates in low-elevation recesses of fractal noise field."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    fbm = np.zeros(shape, dtype=np.float32)
    amp, freq = 1.0, 1.0
    for _ in range(octaves):
        px, py = rng.uniform(0, 2 * np.pi), rng.uniform(0, 2 * np.pi)
        fx, fy = rng.uniform(2, 6) * freq, rng.uniform(2, 6) * freq
        fbm += amp * (np.sin(X * fx * np.pi * 2 + px) * np.cos(Y * fy * np.pi * 2 + py))
        amp *= persistence
        freq *= 2.0
    fbm = _normalize(fbm)
    patina_mask = np.clip(0.45 - fbm, 0.0, 0.45) / 0.45
    patina_mask = _gauss(patina_mask, sigma=2.0)
    result = patina_mask
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_oxidized_pitting(shape, seed, sm, num_pits=400, pit_radius=4.0, **kwargs):
    """Oxidation pits via cKDTree nearest-neighbor (fast). Was brute-force loop over 400 pits."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    density_n = np.zeros(shape, dtype=np.float32)
    for freq_d in [3.0, 6.0]:
        px, py = rng.uniform(0, np.pi * 2), rng.uniform(0, np.pi * 2)
        density_n += np.sin(yy / h * freq_d * np.pi * 2 + py) * np.cos(xx / w * freq_d * np.pi * 2 + px)
    density_n = _normalize(density_n)
    flat_prob = density_n.ravel()
    flat_prob = np.clip(flat_prob, 0.0, 1.0)
    flat_prob /= flat_prob.sum()
    pit_indices = rng.choice(h * w, size=num_pits, replace=False, p=flat_prob)
    pit_y = (pit_indices // w).astype(np.float32)
    pit_x = (pit_indices % w).astype(np.float32)
    # cKDTree: find nearest K pits per pixel
    pts = np.column_stack([pit_y, pit_x])
    tree = cKDTree(pts)
    grid = np.column_stack([yy.ravel(), xx.ravel()])
    k = min(4, len(pts))
    dists, _ = tree.query(grid, k=k, workers=-1)
    dists = dists.reshape(h, w, k) if k > 1 else dists.reshape(h, w, 1)
    # Pit depth (dark center) + ring (bright edge) from nearest K pits
    pit_depth = np.exp(-(dists / max(pit_radius * 0.4, 1.0)) ** 2)
    pit_ring = np.exp(-((dists - pit_radius) / max(pit_radius * 0.3, 1.0)) ** 2) * 0.6
    result = np.sum(pit_ring - pit_depth * 0.8, axis=2)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_heat_scale(shape, seed, sm, band_count=14, noise_warp=0.08, **kwargs):
    """Sinusoidal heat-gradient bands like titanium exhaust: oxide thickness creates spectral zones."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    base_grad = X
    warp_x = np.cos(Y * 4.7 * np.pi + rng.uniform(0, np.pi)) * noise_warp * 0.5
    warped = base_grad + warp_x + np.sin(X * 3.1 * np.pi + rng.uniform(0, np.pi)) * noise_warp * 0.3
    band_wave = np.sin(warped * band_count * np.pi * 2.0) * 0.5 + 0.5
    heat_zone = np.clip(1.0 - warped * 1.5, 0.0, 1.0)
    result = band_wave * 0.65 + heat_zone * 0.35
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_galvanic_corrosion(shape, seed, sm, num_sites=120, corrosion_band=6.0, **kwargs):
    """Voronoi two-metal partition: roughness spikes and metallic drops at galvanic attack cell boundaries."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    sy = rng.uniform(0, h, size=num_sites).astype(np.float32)
    sx = rng.uniform(0, w, size=num_sites).astype(np.float32)
    pts = np.stack([sy, sx], axis=1)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    coords = np.column_stack([yy.ravel(), xx.ravel()])
    dists, _ = tree.query(coords, k=2)
    d1 = dists[:, 0].reshape(shape)
    d2 = dists[:, 1].reshape(shape)
    boundary_dist = (d2 - d1).reshape(shape).astype(np.float32)
    seam_corr = np.exp(-boundary_dist / max(corrosion_band, 1.0))
    result = 1.0 - seam_corr
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_stress_fractures(shape, seed, sm, num_seeds=8, crack_steps=120, **kwargs):
    """Crack tree grown along FBM gradient directions: crack pixels carry near-zero metallic and max roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    noise = np.zeros(shape, dtype=np.float32)
    amp, freq = 1.0, 4.0
    for _ in range(4):
        px, py = rng.uniform(0, np.pi * 2), rng.uniform(0, np.pi * 2)
        noise += amp * np.sin(X * freq * np.pi * 2 + px) * np.cos(Y * freq * np.pi * 2 + py)
        amp *= 0.5
        freq *= 2.1
    noise = _normalize(noise)
    gx = np.gradient(noise, axis=1)
    gy = np.gradient(noise, axis=0)
    crack_canvas = np.zeros(shape, dtype=np.float32)
    for _ in range(num_seeds):
        cy_i = int(rng.uniform(h * 0.1, h * 0.9))
        cx_i = int(rng.uniform(w * 0.1, w * 0.9))
        py_f, px_f = float(cy_i), float(cx_i)
        for _step in range(crack_steps):
            iy = int(np.clip(py_f, 0, h - 1))
            ix = int(np.clip(px_f, 0, w - 1))
            crack_canvas[iy, ix] = 1.0
            for dy2 in [-1, 0, 1]:
                for dx2 in [-1, 0, 1]:
                    ny2 = int(np.clip(iy + dy2, 0, h - 1))
                    nx2 = int(np.clip(ix + dx2, 0, w - 1))
                    crack_canvas[ny2, nx2] = max(crack_canvas[ny2, nx2], 0.7)
            vx = -gy[iy, ix]
            vy = gx[iy, ix]
            mag = np.sqrt(vx * vx + vy * vy) + 1e-6
            vx = vx / mag + rng.uniform(-0.3, 0.3)
            vy = vy / mag + rng.uniform(-0.3, 0.3)
            step_size = rng.uniform(0.8, 2.0)
            px_f += vx * step_size
            py_f += vy * step_size
            if px_f < 0 or px_f >= w or py_f < 0 or py_f >= h:
                break
    result = 1.0 - crack_canvas
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_battle_scars(shape, seed, sm, num_scratches=18, scratch_length_frac=0.35, **kwargs):
    """Long linear scratch gouges at random angles: bright metallic streak flanked by rough paint pile-up edges."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    result = np.zeros(shape, dtype=np.float32)
    scratch_len = min(h, w) * scratch_length_frac
    for _ in range(num_scratches):
        sy_s = rng.uniform(0, h)
        sx_s = rng.uniform(0, w)
        angle = rng.uniform(0, np.pi)
        dx_s = np.cos(angle)
        dy_s = np.sin(angle)
        core_w = rng.uniform(0.5, 1.5)
        halo_w = core_w + rng.uniform(1.5, 3.5)
        rx = xx - sx_s
        ry = yy - sy_s
        along = rx * dx_s + ry * dy_s
        perp = np.abs(-rx * dy_s + ry * dx_s)
        length_mask = ((along >= 0) & (along <= scratch_len)).astype(np.float32)
        core = np.exp(-(perp / max(core_w, 0.5)) ** 2) * length_mask
        halo = (np.exp(-(perp / max(halo_w, 1.0)) ** 2) -
                np.exp(-(perp / max(core_w * 0.8, 0.3)) ** 2)) * length_mask
        result += core * 0.9 - halo * 0.3
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_worn_edges(shape, seed, sm, num_contours=25, contour_noise=0.04, **kwargs):
    """Edge-wear via proximity to curved contour lines: high metallic at simulated panel edges, normal at center."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    border_dist = np.minimum(np.minimum(Y, 1.0 - Y), np.minimum(X, 1.0 - X))
    warp = np.zeros(shape, dtype=np.float32)
    for _ in range(3):
        fx, fy = rng.uniform(2, 5), rng.uniform(2, 5)
        px, py = rng.uniform(0, np.pi * 2), rng.uniform(0, np.pi * 2)
        warp += np.sin(X * fx * np.pi * 2 + px) * np.sin(Y * fy * np.pi * 2 + py) * contour_noise
    warped_dist = np.clip(border_dist + warp, 0.0, 0.5)
    contour = np.abs(np.sin(warped_dist * num_contours * np.pi * 2.0))
    edge_weight = np.exp(-warped_dist * 6.0)
    result = contour * 0.5 + edge_weight * 0.5
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_peeling_clear(shape, seed, sm, **kwargs):
    """Clearcoat peel: edge-biased delamination front shapes lifted vs bonded zones.
    LAZY-007 FIX: replaced random 35%-Voronoi cell mask (was 85%+ overlap with
    spec_galvanic_corrosion) with proximity-weighted FBM peel wavefront.
    Physics: clearcoat delaminates from panel edges inward; organic 4-octave FBM
    warps the front boundary; lifted zones low-signal, bonded zones high-signal,
    peel-front edge gets a roughness spike. Zero Voronoi — completely distinct pipeline."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Edge proximity: 1 at canvas edge, 0 at canvas centre (delamination starts at edges)
    edge_dist = np.minimum(np.minimum(Y, np.float32(1.0) - Y),
                           np.minimum(X, np.float32(1.0) - X))
    edge_bias = np.float32(1.0) - np.clip(edge_dist / np.float32(0.35), 0.0, 1.0)
    # 4-octave FBM shapes the organic peel-front wavefront (not grid-based)
    fbm = np.zeros(shape, dtype=np.float32)
    amp, freq = 1.0, 3.0
    for _ in range(4):
        px = rng.uniform(0, np.pi * 2)
        py = rng.uniform(0, np.pi * 2)
        fbm += np.float32(amp) * (
            np.sin(X * np.float32(freq * np.pi * 2) + np.float32(px)) *
            np.cos(Y * np.float32(freq * np.pi * 2) + np.float32(py)))
        amp *= 0.5; freq *= 2.0
    fbm = _normalize(fbm) * np.float32(0.5)
    # Combined peel potential — high at edges, FBM-modulated interior
    peel_potential = edge_bias * np.float32(0.6) + fbm * np.float32(0.4)
    # Threshold: sm scales extent of peeling (sm=1.0 → heavy; sm=0.3 → light fringe)
    threshold = np.float32(0.55) - np.float32(sm) * np.float32(0.30)
    peeled = (peel_potential > threshold).astype(np.float32)
    # Soft roughness spike at peel-front boundary (±front_width around threshold)
    front_width = np.float32(0.06)
    front_spike = np.clip((front_width - np.abs(peel_potential - threshold)) / front_width,
                          0.0, 1.0)
    front_spike = _gauss(front_spike, sigma=1.5)
    # Output: bonded(high) + front-spike; lifted(peeled) regions are the dark/rough signal
    result = (np.float32(1.0) - peeled) * np.float32(0.3) + front_spike * np.float32(0.7)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_sandblast_strip(shape, seed, sm, blob_octaves=4, blob_freq=2.5, **kwargs):
    """FBM domain-warp blob shapes partition sandblasted bare-metal zones from unblasted paint zones."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    warp_x = np.zeros(shape, dtype=np.float32)
    warp_y = np.zeros(shape, dtype=np.float32)
    amp, freq = 1.0, blob_freq
    for _ in range(blob_octaves):
        px1, py1 = rng.uniform(0, np.pi * 2), rng.uniform(0, np.pi * 2)
        px2, py2 = rng.uniform(0, np.pi * 2), rng.uniform(0, np.pi * 2)
        warp_x += amp * np.sin(X * freq * np.pi * 2 + px1) * np.cos(Y * freq * np.pi * 2 + py1)
        warp_y += amp * np.cos(X * freq * np.pi * 2 + px2) * np.sin(Y * freq * np.pi * 2 + py2)
        amp *= 0.5
        freq *= 2.0
    field = np.sin((X + warp_x * 0.15) * blob_freq * np.pi * 2) * \
            np.cos((Y + warp_y * 0.15) * blob_freq * np.pi * 2)
    field = _normalize(field)
    blast_mask = np.clip((field - 0.48) * 8.0, 0.0, 1.0)
    blast_mask = _gauss(blast_mask, sigma=1.5)
    return _sm_scale(_normalize(blast_mask), sm).astype(np.float32)


def spec_micro_chips(shape, seed, sm, chip_radius=3.5, base_density=0.0015, **kwargs):
    """Paint chips via cKDTree nearest-neighbor (fast). Was brute-force loop over 6K+ chips."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy_n = np.arange(h, dtype=np.float32) / h
    xx_n = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy_n, xx_n, indexing='ij')
    density_field = np.zeros(shape, dtype=np.float32)
    amp, freq = 1.0, 2.0
    for _ in range(3):
        px, py = rng.uniform(0, np.pi * 2), rng.uniform(0, np.pi * 2)
        density_field += amp * (np.sin(X * freq * np.pi * 2 + px) *
                                np.sin(Y * freq * np.pi * 2 + py) * 0.5 + 0.5)
        amp *= 0.55
        freq *= 2.3
    density_field = _normalize(density_field)
    flat_prob = density_field.ravel()
    flat_prob = np.clip(flat_prob, 0.01, 1.0)
    flat_prob /= flat_prob.sum()
    num_chips = int(h * w * base_density)
    chip_indices = rng.choice(h * w, size=max(num_chips, 1), replace=False, p=flat_prob)
    chip_y = (chip_indices // w).astype(np.float32)
    chip_x = (chip_indices % w).astype(np.float32)
    # cKDTree: find nearest K chips per pixel in one vectorized query
    pts = np.column_stack([chip_y, chip_x])
    tree = cKDTree(pts)
    yg, xg = np.mgrid[0:h, 0:w]
    grid = np.column_stack([yg.ravel().astype(np.float32), xg.ravel().astype(np.float32)])
    k = min(6, len(pts))  # each pixel only affected by nearest few chips
    dists, _ = tree.query(grid, k=k, workers=-1)
    if k == 1:
        dists = dists.reshape(h, w, 1)
    else:
        dists = dists.reshape(h, w, k)
    # Sum Gaussian contributions from nearest K chips only
    result = np.sum(np.exp(-(dists / max(chip_radius, 0.5)) ** 2), axis=2)
    result = np.clip(result, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_aged_matte(shape, seed, sm, octaves=6, persistence=0.48, **kwargs):
    """Tangent-warped FBM oxidation: high-fbm zones gain roughness and ghost metallic, creating dead-matte look."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    fbm1 = np.zeros(shape, dtype=np.float32)
    amp, freq = 1.0, 1.5
    for i in range(octaves):
        px, py = rng.uniform(0, np.pi * 2), rng.uniform(0, np.pi * 2)
        Xw = X + (np.tan(np.clip(Y * freq * 0.5, -1.4, 1.4)) * 0.05 if i % 2 == 1 else 0.0)
        fbm1 += amp * np.cos(Xw * freq * np.pi * 2 + px) * np.sin(Y * freq * np.pi * 2 + py)
        amp *= persistence
        freq *= 2.05
    fbm1 = _normalize(fbm1)
    result = fbm1 * 0.8 + _gauss(fbm1, sigma=3.0) * 0.2
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH D: Carbon Fiber & Industrial Weave (102–113)
# ============================================================================

def spec_carbon_2x2_twill(shape, seed, sm, tow_width=8.0, **kwargs):
    """Standard 2×2 twill carbon fiber. Two fiber families at ±45°. Each tow goes over 2 then under 2.
    High metallic at tow crown, low at sides, roughness spikes at interlace crossover points."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Two fiber families at ±45°
    u = (X + Y) / tow_width          # +45° direction
    v = (X - Y) / tow_width          # -45° direction
    # 2×2 twill: over-2/under-2 phase = 0.5-period phase offset between tows
    # Tow crown profile: cos² gives smooth metallic peak per tow
    phase_shift = np.floor(u) * 0.5  # shifts every other tow by half period
    tow_a = np.cos((u + phase_shift) * np.pi) ** 2   # family A tow crowns
    phase_shift_b = np.floor(v) * 0.5
    tow_b = np.cos((v + phase_shift_b) * np.pi) ** 2  # family B tow crowns
    # Metallic: high at either tow crown, combined by max (the top tow dominates)
    metallic = np.maximum(tow_a, tow_b)
    # Crossover points: where both families are at their edges — max roughness
    crossover = (1.0 - tow_a) * (1.0 - tow_b)
    result = metallic * 0.75 - crossover * 0.25
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_carbon_plain_weave(shape, seed, sm, tow_width=6.0, **kwargs):
    """Plain weave (1×1) carbon fiber. Checkerboard-like interlace: alternating over/under every fiber.
    More symmetric, grid-like metallic variation vs the diagonal flow of twill."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Orthogonal fiber families (0° and 90°) — plain weave is aligned grids
    u = X / tow_width   # horizontal tows
    v = Y / tow_width   # vertical tows
    # 1×1 plain: every tow alternates — parity of tow index flips which is on top
    u_parity = np.floor(u).astype(np.int32) % 2
    v_parity = np.floor(v).astype(np.int32) % 2
    # Where parities match: one family on top; mismatch: other family on top
    on_top = (u_parity == v_parity).astype(np.float32)
    # Crown profile per tow
    tow_u = np.cos((u % 1.0) * np.pi * 2.0 - np.pi) * 0.5 + 0.5
    tow_v = np.cos((v % 1.0) * np.pi * 2.0 - np.pi) * 0.5 + 0.5
    # Top tow gives metallic highlight; bottom tow is subdued
    metallic = on_top * tow_u + (1.0 - on_top) * tow_v * 0.4
    # Checkerboard roughness at interlace crossings (tow edges)
    edge_u = np.sin((u % 1.0) * np.pi * 2.0) ** 2
    edge_v = np.sin((v % 1.0) * np.pi * 2.0) ** 2
    crossover = edge_u * edge_v
    result = metallic * 0.8 - crossover * 0.2
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_carbon_3k_fine(shape, seed, sm, tow_width=4.5, **kwargs):
    """True 3K fiber tow carbon — sub-tow microstructure with 3 fiber bundles per tow.
    LAZY-003 FIX: replaced Gaussian-crown twill (was ≈spec_carbon_2x2_twill) with
    dual-frequency construction: main ±45° tow grid (tow_width) PLUS 3-bundle
    sub-grid (tow_width/3). Bundle ridges visible inside each tow crown as fine
    ribbing — a second spatial scale impossible to produce from single-scale twill."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    tw = np.float32(tow_width)
    # --- MAIN TOW LEVEL: 2×2 twill ±45° (cos² crowns, same as 2x2_twill) ---
    u = (X + Y) / tw
    v = (X - Y) / tw
    phase_a = np.floor(u) * np.float32(0.5)
    tow_a = np.cos((u + phase_a) * np.pi) ** 2
    phase_b = np.floor(v) * np.float32(0.5)
    tow_b = np.cos((v + phase_b) * np.pi) ** 2
    metallic_main = np.maximum(tow_a, tow_b)
    # --- SUB-TOW LEVEL: 3 fiber bundles per tow (3× higher frequency) ---
    bw = tw / np.float32(3.0)   # bundle width
    u_s = (X + Y) / bw          # sub-grid +45°
    v_s = (X - Y) / bw          # sub-grid -45°
    sigma = np.float32(0.22)
    u_cen = (u_s % np.float32(1.0)) - np.float32(0.5)
    v_cen = (v_s % np.float32(1.0)) - np.float32(0.5)
    bundle_a = np.exp(-(u_cen ** 2) / (np.float32(2.0) * sigma ** 2))
    bundle_b = np.exp(-(v_cen ** 2) / (np.float32(2.0) * sigma ** 2))
    # Bundle detail modulated by main tow envelope (sub-structure only visible on tow crowns)
    sub_detail = np.maximum(bundle_a, bundle_b) * metallic_main * np.float32(0.38)
    metallic = metallic_main * np.float32(0.70) + sub_detail
    # Sub-bundle gap micro-roughness (between bundles, inside tow)
    micro_gap = (np.float32(1.0) - bundle_a) * (np.float32(1.0) - bundle_b) * metallic_main
    result = metallic - micro_gap * np.float32(0.18)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_carbon_forged(shape, seed, sm, num_strands=800, strand_len_frac=0.25, **kwargs):
    """Forged carbon fiber via local bounding-box rasterization (fast).
    Was brute-force loop computing distance on full 4M grid per strand."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    result = np.zeros(shape, dtype=np.float32)
    strand_len = min(h, w) * strand_len_frac
    sy = rng.uniform(0, h, size=num_strands).astype(np.float32)
    sx = rng.uniform(0, w, size=num_strands).astype(np.float32)
    angles = rng.uniform(0, np.pi, size=num_strands).astype(np.float32)
    lengths = rng.uniform(strand_len * 0.3, strand_len, size=num_strands).astype(np.float32)
    widths = rng.uniform(0.8, 2.5, size=num_strands).astype(np.float32)
    for i in range(num_strands):
        dx_s, dy_s = np.cos(angles[i]), np.sin(angles[i])
        # Bounding box of strand + falloff margin
        ey, ex = sy[i] + dy_s * lengths[i], sx[i] + dx_s * lengths[i]
        margin = widths[i] * 4
        y0 = max(0, int(min(sy[i], ey) - margin))
        y1 = min(h, int(max(sy[i], ey) + margin) + 1)
        x0 = max(0, int(min(sx[i], ex) - margin))
        x1 = min(w, int(max(sx[i], ex) + margin) + 1)
        if y1 <= y0 or x1 <= x0:
            continue
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        rx, ry = lx - sx[i], ly - sy[i]
        t = np.clip(rx * dx_s + ry * dy_s, 0.0, lengths[i])
        dist = np.sqrt((rx - t * dx_s) ** 2 + (ry - t * dy_s) ** 2)
        contrib = np.exp(-(dist / max(widths[i], 0.5)) ** 2)
        result[y0:y1, x0:x1] = np.maximum(result[y0:y1, x0:x1], contrib)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_carbon_wet_layup(shape, seed, sm, tow_width=9.0, **kwargs):
    """Wet layup carbon: hand-applied resin-rich surface. Structurally distinct from
    prepreg/2x2_twill (sharp fiber peaks). Key physical differences:
    - Large smooth resin-pool zones (macro roughness variation from uneven hand layup)
    - Barely-visible fiber ghost buried under thick resin (20% amplitude vs prepreg 100%)
    - Meniscus surface-tension ridges at tow crossovers (narrow raised rings)
    - Air-bubble rings: circular depressions from trapped layup gas inclusions
    Result: spatially large gloss variation + subtle weave ghost — completely different
    spatial character from any other carbon spec pattern."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')

    # 1. Fiber ghost — same 2x2 twill geometry, very low amplitude (buried under resin)
    u = (X + Y) / tow_width
    v = (X - Y) / tow_width
    tow_a = np.cos((u + np.floor(u) * 0.5) * np.pi) ** 2
    tow_b = np.cos((v + np.floor(v) * 0.5) * np.pi) ** 2
    fiber_ghost = np.maximum(tow_a, tow_b) * 0.20

    # 2. Resin pooling: large-scale macro variation from uneven hand-layup thickness
    pool_sigma = max(8.0, tow_width * 3.5)
    resin_pool = multi_scale_noise(shape, [pool_sigma * 2.0, pool_sigma], [0.60, 0.40], seed + 200)
    resin_pool = (resin_pool - resin_pool.min()) / max(resin_pool.max() - resin_pool.min(), 1e-7)
    # Micro surface-tension ripple at tow scale
    micro_ripple = multi_scale_noise(shape, [tow_width * 0.8, tow_width * 0.4], [0.55, 0.45], seed + 201)
    micro_ripple = micro_ripple / max(float(np.abs(micro_ripple).max()), 1e-7) * 0.08

    # 3. Meniscus ridges at tow crossovers — resin surface tension forms narrow ridges
    u_frac = u % 1.0
    v_frac = v % 1.0
    meniscus = (np.sin(u_frac * np.pi) * np.sin(v_frac * np.pi)) ** 4 * 0.35

    # 4. Air-bubble rings — thin annular ridges from displaced resin around trapped gas
    n_bub = max(3, int(7 * sm))
    rng2 = np.random.RandomState(seed + 400)
    b_y = rng2.uniform(h * 0.1, h * 0.9, n_bub).astype(np.float32)
    b_x = rng2.uniform(w * 0.1, w * 0.9, n_bub).astype(np.float32)
    b_r = rng2.uniform(6.0, 18.0, n_bub).astype(np.float32)
    bubble_rings = np.zeros((h, w), dtype=np.float32)
    for by, bx, br in zip(b_y, b_x, b_r):
        dist = np.sqrt((Y - by) ** 2 + (X - bx) ** 2)
        ring = np.exp(-((dist - br) ** 2) / (2.0 * 3.5 ** 2))
        bubble_rings = np.maximum(bubble_rings, ring)
    bubble_rings *= 0.28

    result = resin_pool * 0.50 + fiber_ghost + meniscus + micro_ripple + bubble_rings
    return _sm_scale(_normalize(result.astype(np.float32)), sm).astype(np.float32)


def spec_kevlar_weave(shape, seed, sm, tow_width=7.0, **kwargs):
    """Kevlar (aramid fiber) weave. Plain-weave geometry with distinct Kevlar optical properties:
    matte satin sheen (lower metallic, higher roughness than carbon), silky micro-texture,
    moderate roughness bumps at interlace crossovers."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Kevlar: orthogonal plain-weave grid (0°/90°), slightly diagonal offset
    angle_offset = 0.15   # slight skew differentiates from plain carbon
    u = (X * np.cos(angle_offset) + Y * np.sin(angle_offset)) / tow_width
    v = (-X * np.sin(angle_offset) + Y * np.cos(angle_offset)) / tow_width
    u_parity = np.floor(u).astype(np.int32) % 2
    v_parity = np.floor(v).astype(np.int32) % 2
    on_top = (u_parity == v_parity).astype(np.float32)
    # Kevlar tow: raised cosine but with silky micro-texture added
    u_frac = u % 1.0
    v_frac = v % 1.0
    tow_u = np.cos((u_frac - 0.5) * np.pi) ** 2
    tow_v = np.cos((v_frac - 0.5) * np.pi) ** 2
    # Silky micro-texture: high-freq sinusoidal along tow axis
    micro_u = np.sin(u * np.pi * 8.0) ** 2 * 0.12
    micro_v = np.sin(v * np.pi * 8.0) ** 2 * 0.12
    # Kevlar: lower peak metallic (0.55 range) with satin micro-texture
    metallic = on_top * tow_u * 0.55 + (1.0 - on_top) * tow_v * 0.25
    # Interlace crossover roughness: moderate (kevlar is rougher than carbon)
    cross_u = np.abs(np.sin(u_frac * np.pi))
    cross_v = np.abs(np.sin(v_frac * np.pi))
    crossover_roughness = (1.0 - cross_u) * (1.0 - cross_v) * 0.35
    result = metallic + micro_u + micro_v - crossover_roughness * 0.5
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_fiberglass_chopped(shape, seed, sm, num_strands=600, **kwargs):
    """Chopped fiberglass via local bounding-box rasterization (fast).
    Was brute-force loop computing distance on full 4M grid per strand."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    result = np.zeros(shape, dtype=np.float32)
    num_clusters = max(num_strands // 8, 8)
    cluster_y = rng.uniform(0, h, size=num_clusters).astype(np.float32)
    cluster_x = rng.uniform(0, w, size=num_clusters).astype(np.float32)
    cluster_radius = min(h, w) * 0.18
    for i in range(num_strands):
        c = rng.randint(0, num_clusters)
        sy_s = float(np.clip(cluster_y[c] + rng.normal(0, cluster_radius * 0.4), 0, h - 1))
        sx_s = float(np.clip(cluster_x[c] + rng.normal(0, cluster_radius * 0.4), 0, w - 1))
        angle = rng.uniform(0, np.pi)
        strand_len = rng.uniform(min(h, w) * 0.04, min(h, w) * 0.18)
        orientation_spec = np.sin(angle) ** 2
        spec_peak = 0.25 + orientation_spec * 0.75
        dx_s, dy_s = np.cos(angle), np.sin(angle)
        strand_width = rng.uniform(0.6, 1.8)
        # Local bounding box only
        ey, ex = sy_s + dy_s * strand_len, sx_s + dx_s * strand_len
        margin = strand_width * 4
        y0 = max(0, int(min(sy_s, ey) - margin))
        y1 = min(h, int(max(sy_s, ey) + margin) + 1)
        x0 = max(0, int(min(sx_s, ex) - margin))
        x1 = min(w, int(max(sx_s, ex) + margin) + 1)
        if y1 <= y0 or x1 <= x0:
            continue
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        rx, ry = lx - sx_s, ly - sy_s
        t = np.clip(rx * dx_s + ry * dy_s, 0.0, strand_len)
        dist = np.sqrt((rx - t * dx_s) ** 2 + (ry - t * dy_s) ** 2)
        contrib = spec_peak * np.exp(-(dist / max(strand_width, 0.4)) ** 2)
        result[y0:y1, x0:x1] = np.maximum(result[y0:y1, x0:x1], contrib)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_woven_dyneema(shape, seed, sm, grid_spacing=5.0, **kwargs):
    """Woven Dyneema/UHMWPE. Very tight, almost invisible weave. Extremely subtle spec:
    slight grid-like R variation (160–200 range), nearly smooth surface.
    The 'almost metallic' appearance of Dyneema sheets — neither matte nor glossy."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Very tight near-invisible plain weave at 0°/90°
    u = X / grid_spacing
    v = Y / grid_spacing
    # Dyneema: extremely subtle cosine modulation — very low amplitude
    tow_u = np.cos(u * np.pi * 2.0) * 0.08 + 0.5
    tow_v = np.cos(v * np.pi * 2.0) * 0.08 + 0.5
    # Combined: multiply gives cross-grid with very low contrast
    grid_pattern = tow_u * tow_v
    # Add subtle diagonal micro-texture (Dyneema has slight sheen directionality)
    diag = np.sin((X + Y) / (grid_spacing * 1.5) * np.pi) * 0.04
    result = grid_pattern + diag
    # Very compressed output — tight R range around 0.5 (maps to 160–200 after scaling)
    result = np.clip(result, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_mesh_perforated(shape, seed, sm, hole_spacing=18.0, hole_radius_frac=0.38, **kwargs):
    """Perforated metal mesh. Regular grid of circular holes.
    At hole centers: R=0 (no material). Between holes: high metallic polished metal.
    Smooth radial distance function for hole-to-metal transition."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Grid coordinates normalized within each cell
    u = (X % hole_spacing) / hole_spacing  # [0, 1) within cell
    v = (Y % hole_spacing) / hole_spacing
    # Distance from cell center [0.5, 0.5]
    du = u - 0.5
    dv = v - 0.5
    dist_from_center = np.sqrt(du * du + dv * dv)  # 0 = hole center, ~0.7 = corner
    hole_radius = hole_radius_frac   # in normalized cell units
    # Smooth radial mask: 0 inside hole, 1 at metal
    hole_mask = np.clip((dist_from_center - hole_radius) / (hole_radius * 0.25), 0.0, 1.0)
    # Metal between holes: polished, so high metallic at solid areas
    # Near hole edge: slight chamfer/burr effect (slight dip then rise)
    chamfer = np.exp(-((dist_from_center - hole_radius) / (hole_radius * 0.15)) ** 2) * 0.15
    result = hole_mask + chamfer
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_expanded_metal(shape, seed, sm, diamond_size=20.0, angle_deg=30.0, **kwargs):
    """Expanded metal mesh (diamond-pattern). Rotated diamond grid — slitted and stretched sheet.
    Wire frame has high metallic edges; open diamond interior = no material.
    NOT circular holes — uses rotated diamond coordinate geometry."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    angle = np.deg2rad(angle_deg)
    # Rotate coordinates to align diamond grid
    Xr = X * np.cos(angle) + Y * np.sin(angle)
    Yr = -X * np.sin(angle) + Y * np.cos(angle)
    # Diamond cell via abs transform: each diamond cell is a rotated square
    # Normalize into cell space — diamond half-period
    cell_h = diamond_size
    cell_w = diamond_size * 0.55   # diamonds are narrower than tall (stretched sheet ratio)
    u = (Xr % cell_w) / cell_w    # [0,1) horizontal in diamond cell
    v = (Yr % cell_h) / cell_h    # [0,1) vertical in diamond cell
    # Diamond wire frame: distance to diamond edge in abs coords
    # |u - 0.5| + |v - 0.5| gives diamond shape; wire is where this is near 0.5
    diamond_d = np.abs(u - 0.5) + np.abs(v - 0.5)
    wire_width = 0.12   # normalized
    wire_inner = 0.50 - wire_width
    # Wire region: diamond_d near 0.5
    on_wire = np.clip(1.0 - np.abs(diamond_d - 0.50) / wire_width, 0.0, 1.0)
    # Open diamond interior (diamond_d < wire_inner) = no metal
    interior_mask = (diamond_d < wire_inner).astype(np.float32)
    result = on_wire * (1.0 - interior_mask * 0.95)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_chainlink_fence(shape, seed, sm, wire_spacing=16.0, wire_width_px=1.8, **kwargs):
    """Chain-link fence wire pattern. Diagonal interlocking diamond wire weave.
    Wire intersections have highest metallic (double thickness = more metal).
    Differs from expanded_metal: wires physically cross and interlock rather than stamped openings.
    Uses two sets of diagonal sinusoidal wires that cross each other."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Two families of diagonal wires: +45° and -45°
    wire_sigma = wire_width_px
    # Family A: wires running at +45°, spaced wire_spacing apart in perpendicular direction
    diag_a = (X - Y) / np.sqrt(2.0)   # perpendicular distance coordinate for +45° wires
    # Distance to nearest wire in family A
    wire_phase_a = (diag_a % wire_spacing) / wire_spacing  # [0,1)
    wire_center_a = np.abs(wire_phase_a - 0.5)  # 0 = wire center, 0.5 = midway between wires
    wire_a = np.exp(-(wire_center_a * wire_spacing / wire_sigma) ** 2)
    # Family B: wires running at -45°
    diag_b = (X + Y) / np.sqrt(2.0)
    wire_phase_b = (diag_b % wire_spacing) / wire_spacing
    wire_center_b = np.abs(wire_phase_b - 0.5)
    wire_b = np.exp(-(wire_center_b * wire_spacing / wire_sigma) ** 2)
    # Intersection: both wires present — additive for double-thickness metallic peak
    # This is the key geometric difference from expanded_metal
    result = wire_a + wire_b   # intersections naturally peak at 2.0 (double metal)
    result = np.clip(result, 0.0, 2.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_ballistic_weave(shape, seed, sm, tow_width=4.0, **kwargs):
    """Dense military-spec ballistic nylon/Cordura weave. Very tight plain weave, near-invisible.
    Moderate R (synthetic fiber — not metallic), G varies with weave peaks (80–160),
    B moderate clearcoat. Utilitarian 'tactical' texture with slight nylon sheen."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Dense orthogonal plain weave — tight pitch
    u = X / tow_width
    v = Y / tow_width
    u_frac = u % 1.0
    v_frac = v % 1.0
    u_parity = np.floor(u).astype(np.int32) % 2
    v_parity = np.floor(v).astype(np.int32) % 2
    on_top = (u_parity == v_parity).astype(np.float32)
    # Ballistic nylon: low-amplitude tow crown (synthetic fiber, minimal specular)
    tow_u = np.cos((u_frac - 0.5) * np.pi) ** 2 * 0.35 + 0.32
    tow_v = np.cos((v_frac - 0.5) * np.pi) ** 2 * 0.35 + 0.32
    # Slight surface nylon sheen — smooth low-amplitude
    nylon_sheen = (np.sin(u * np.pi * 2.0) + np.sin(v * np.pi * 2.0)) * 0.05
    metallic = on_top * tow_u + (1.0 - on_top) * tow_v * 0.6 + nylon_sheen
    # Roughness variation at interlace — moderate, not sharp
    interlace_rough = (1.0 - np.cos((u_frac + v_frac) * np.pi)) * 0.15
    result = metallic - interlace_rough * 0.3
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH E: 🔵 CLEARCOAT BEHAVIOR (114–123)
# B=Clearcoat channel — INVERTED: low value = gloss, high = matte/rough
# These patterns make clearcoat variation visible: pooling, drips, fish-eyes,
# overspray halos, edge thinning. Dark output = extra-glossy zones.
# ============================================================================

def cc_panel_pool(shape, seed, sm, num_pools=12, pool_spread=0.18, **kwargs):
    """Clearcoat pooling — gravity-settled extra-clear collects in panel low spots.
    Scattered Gaussian clear pools (dark = thick clear = extra gloss). B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Pools prefer lower half of panel (gravity bias)
    result = np.zeros(shape, dtype=np.float32)
    for _ in range(num_pools):
        cy = rng.uniform(0.4, 0.9)  # gravity bias to bottom
        cx = rng.uniform(0.05, 0.95)
        r = rng.uniform(pool_spread * 0.5, pool_spread * 1.5)
        pool = np.exp(-((Y - cy) ** 2 + (X - cx) ** 2) / (2 * r ** 2))
        result = np.maximum(result, pool * rng.uniform(0.6, 1.0))
    # Dark = extra clear (thicker pool = glossier)
    result = 1.0 - result  # invert: pool = darker = lower B = more gloss
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_drip_runs(shape, seed, sm, num_drips=8, drip_length=0.25, **kwargs):
    """Clearcoat drip runs — vertical streaks of excess clear running down panel.
    Thin elongated Gaussian streaks darker at head, fading down run. B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    result = np.zeros(shape, dtype=np.float32)
    for _ in range(num_drips):
        x0 = rng.uniform(0.05, 0.95)
        y0 = rng.uniform(0.1, 0.5)
        length = drip_length * rng.uniform(0.5, 1.5)
        width = rng.uniform(0.005, 0.018)
        # Drip: narrow x-Gaussian, elongated y profile (run downward)
        x_gauss = np.exp(-((X - x0) ** 2) / (2 * width ** 2))
        y_run = np.where(
            (Y >= y0) & (Y <= y0 + length),
            np.exp(-((Y - y0) / (length * 0.4)) ** 2),
            0.0
        )
        result = np.maximum(result, x_gauss * y_run * rng.uniform(0.7, 1.0))
    result = 1.0 - result  # dark drip = extra gloss
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_fish_eye(shape, seed, sm, num_craters=20, crater_radius=0.04, **kwargs):
    """Fish-eye defects — silicone contamination repels clearcoat, making circular bare patches.
    Bright ring (thin clear/dull edge) + dark center (no clear) = inverse dome. B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    result = np.full(shape, 0.5, dtype=np.float32)  # neutral base
    for _ in range(num_craters):
        cy = rng.uniform(0.05, 0.95)
        cx = rng.uniform(0.05, 0.95)
        r = crater_radius * rng.uniform(0.5, 2.0)
        dist = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2)
        norm_d = dist / max(r, 1e-6)
        # Ring profile: bright at ~0.7r (matte edge), dark at center (bare), normal outside
        ring = np.exp(-((norm_d - 0.65) ** 2) / 0.05) * 0.8
        bare = np.clip(1.0 - norm_d * 3.0, 0.0, 1.0) * 0.5
        crater = ring - bare
        result = result + crater * (dist < r * 1.5).astype(np.float32)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_overspray_halo(shape, seed, sm, num_halos=6, halo_radius=0.22, **kwargs):
    """Overspray halo — misty edge from spray gun overspray, ring of thin/rough clearcoat.
    Bright ring at spray edge (thin/rough), dark center (full gloss), fades outside. B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    result = np.zeros(shape, dtype=np.float32)
    for _ in range(num_halos):
        cy = rng.uniform(0.1, 0.9)
        cx = rng.uniform(0.1, 0.9)
        r = halo_radius * rng.uniform(0.4, 1.6)
        dist = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2) / max(r, 1e-6)
        # Soft ring: peak at r=1 (halo boundary), dark inside, fade outside
        halo = np.exp(-((dist - 1.0) ** 2) / 0.04)
        result = np.maximum(result, halo)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_edge_thin(shape, seed, sm, edge_width=0.12, noise_scale=0.04, **kwargs):
    """Panel edge thinning — clearcoat thins at panel corners/edges as it sags inward.
    Edges bright (thin clear = rough), center dark (thick clear = gloss). B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Distance to nearest edge (0 at edge, 0.5 at center)
    edge_dist = np.minimum(np.minimum(Y, 1.0 - Y), np.minimum(X, 1.0 - X))
    # Thin at edges: ramp from 1 at edge to 0 beyond edge_width
    thin_mask = 1.0 - np.clip(edge_dist / edge_width, 0.0, 1.0)
    # Add slight noise warp for organic look
    noise = multi_scale_noise(shape, [4, 8, 16], [0.5, 0.3, 0.2], seed)
    result = thin_mask + noise * noise_scale
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_masking_edge(shape, seed, sm, num_edges=4, edge_softness=0.03, **kwargs):
    """Masking tape edge — sharp boundary where tape lifted, leaving abrupt clear-coat step.
    Hard bright-to-dark transitions at random angles. B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    result = np.zeros(shape, dtype=np.float32)
    for _ in range(num_edges):
        angle = rng.uniform(0, np.pi)
        offset = rng.uniform(0.2, 0.8)
        proj = X * np.cos(angle) + Y * np.sin(angle)
        # Hard step softened by edge_softness
        step = np.clip((proj - offset) / edge_softness, 0.0, 1.0)
        result = np.maximum(result, step * rng.uniform(0.5, 1.0))
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_spot_polish(shape, seed, sm, num_spots=15, spot_radius=0.08, **kwargs):
    """Spot polish — localized re-polished areas where clearcoat was buffed extra smooth.
    Dark smooth spots (extra gloss) vs normal surrounding surface. B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Base: slight noise texture
    result = multi_scale_noise(shape, [8, 16], [0.7, 0.3], seed) * 0.3 + 0.5
    for _ in range(num_spots):
        cy = rng.uniform(0.05, 0.95)
        cx = rng.uniform(0.05, 0.95)
        r = spot_radius * rng.uniform(0.4, 1.8)
        spot = np.exp(-((Y - cy) ** 2 + (X - cx) ** 2) / (2 * (r * 0.5) ** 2))
        result = result - spot * rng.uniform(0.3, 0.6)  # darken = more gloss
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_gloss_stripe(shape, seed, sm, num_stripes=6, stripe_width=0.06, angle_deg=0.0, **kwargs):
    """Gloss stripes — parallel extra-glossy bands from single pass of spray gun.
    Dark stripes (thicker clear) alternating with normal surface. B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    angle = np.deg2rad(angle_deg + rng.uniform(-5, 5))
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Projection along spray direction
    proj = X * np.cos(angle) + Y * np.sin(angle)
    # Spacing: canvas-relative
    spacing = 1.0 / max(num_stripes, 1)
    phase = (proj % spacing) / spacing  # [0,1] repeat
    # Soft stripe: peak at 0.5 (center of dark stripe)
    stripe = np.cos((phase - 0.5) * np.pi * 2.0) * 0.5 + 0.5
    stripe = stripe ** (1.0 / stripe_width)
    return _sm_scale(_normalize(1.0 - stripe * 0.6), sm).astype(np.float32)


def cc_wet_zone(shape, seed, sm, num_zones=5, **kwargs):
    """Wet zones — areas of clearcoat not yet fully flowed/leveled, patches of higher gloss.
    Organic blob shapes via FBM-shaped thresholding. Dark = extra wet/gloss. B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    fbm = multi_scale_noise(shape, [2, 4, 8, 16], [0.5, 0.25, 0.15, 0.1], seed)
    fbm_norm = _normalize(fbm)
    # Threshold creates blob zones
    threshold = 0.55
    wet = np.clip((fbm_norm - threshold) / (1.0 - threshold), 0.0, 1.0)
    result = 1.0 - wet * 0.7  # wet zones are darker (glossier)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def cc_panel_fade(shape, seed, sm, fade_direction=0.0, noise_warp=0.06, **kwargs):
    """Panel fade — clearcoat thickness gradient across panel from spray angle.
    One side thick/glossy (dark), opposite thin/dull (bright). B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    angle = np.deg2rad(fade_direction + rng.uniform(-15, 15))
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Linear gradient along angle
    grad = X * np.cos(angle) + Y * np.sin(angle)
    # Warp with low-frequency noise for organic look
    warp = multi_scale_noise(shape, [3, 6], [0.6, 0.4], seed + 1)
    result = _normalize(grad) + _normalize(warp) * noise_warp
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH E: 🏗️ GEOMETRIC & ARCHITECTURAL (124–135)
# Precise geometric structures from architecture, industrial design, faceted surfaces.
# Each uses mathematically distinct geometry targeting R=Metallic channel primarily.
# ============================================================================

def spec_faceted_diamond(shape, seed, sm, num_cells=120, **kwargs):
    """Faceted diamond/gem cut surface. Each Voronoi cell = one facet. Within each cell,
    metallic varies linearly from cell centroid (high metallic = specular highlight) to
    cell edge (lower metallic). Gradient direction rotates randomly per cell — simulates
    each facet's different orientation. Multi-directional glitter of cut gem surfaces."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Scatter Voronoi seed points
    pts_y = rng.uniform(0, h, num_cells).astype(np.float32)
    pts_x = rng.uniform(0, w, num_cells).astype(np.float32)
    # Per-cell gradient direction (facet orientation)
    facet_angles = rng.uniform(0, 2 * np.pi, num_cells).astype(np.float32)
    # Per-cell brightness offset (random facet reflectivity)
    facet_brightness = rng.uniform(0.3, 1.0, num_cells).astype(np.float32)
    # Build KD-tree for fast nearest-cell lookup
    pts = np.stack([pts_y, pts_x], axis=1)
    tree = cKDTree(pts)
    coords = np.stack([Y.ravel(), X.ravel()], axis=1)
    dists, indices = tree.query(coords, k=1)
    dists = dists.reshape(h, w).astype(np.float32)
    indices = indices.reshape(h, w)
    # Normalize distance within each cell by approximate cell radius
    cell_radius = np.sqrt(h * w / num_cells) * 0.6
    norm_dist = np.clip(dists / cell_radius, 0.0, 1.0)
    # Per-pixel: get cell index, look up facet angle and brightness
    idx_flat = indices.ravel()
    angle_map = facet_angles[idx_flat].reshape(h, w)
    bright_map = facet_brightness[idx_flat].reshape(h, w)
    # Directional gradient: project pixel offset from cell center along facet angle
    cell_cy = pts_y[idx_flat].reshape(h, w)
    cell_cx = pts_x[idx_flat].reshape(h, w)
    dy = Y - cell_cy
    dx = X - cell_cx
    proj = dx * np.cos(angle_map) + dy * np.sin(angle_map)
    # Normalize projection to [-1, 1] within cell
    proj_norm = np.clip(proj / (cell_radius + 1e-6), -1.0, 1.0)
    # Metallic: high at facet highlight direction, falls off to edges
    facet_gradient = (proj_norm * 0.5 + 0.5) * bright_map
    # Edge darkening: lower metallic at Voronoi cell boundaries
    edge_fade = 1.0 - norm_dist ** 1.5
    result = facet_gradient * edge_fade
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_hammered_dimple(shape, seed, sm, dimple_spacing=18.0, **kwargs):
    """Hammered metal dimples. Hex-grid hemispherical impressions.
    Each dimple: metallic = cos(r / radius * pi/2) — high metallic at dimple rim
    (angled surface reflects more), low at center (surface points away from viewer).
    Distinct cos-radial profile from a hex-packed grid. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Hex grid: two interleaved square grids offset by half spacing
    spacing_x = dimple_spacing
    spacing_y = dimple_spacing * np.sqrt(3.0) / 2.0
    # Row index
    row = np.floor(Y / spacing_y).astype(np.int32)
    row_f = (Y / spacing_y) - np.floor(Y / spacing_y)
    # Hex offset: alternate rows shift by half spacing
    x_offset = (row % 2) * (spacing_x * 0.5)
    col_f = ((X - x_offset) / spacing_x) - np.floor((X - x_offset) / spacing_x)
    # Distance to nearest hex center
    dx_cell = (col_f - 0.5) * spacing_x
    dy_cell = (row_f - 0.5) * spacing_y
    r_dimple = np.sqrt(dx_cell ** 2 + dy_cell ** 2)
    # Dimple radius = ~0.45 * spacing
    dimple_radius = dimple_spacing * 0.45
    # cos(r/radius * pi/2): 1 at rim edge, 0 at center, 0 outside
    inside = (r_dimple < dimple_radius).astype(np.float32)
    cos_profile = np.cos(np.clip(r_dimple / dimple_radius, 0.0, 1.0) * (np.pi / 2.0))
    # Rim highlight: metallic peaks at ~0.8 * radius
    rim_mask = np.exp(-((r_dimple / dimple_radius - 0.80) ** 2) / 0.04)
    # Combine: inside gets rim-weighted cos profile, outside gets flat plate spec
    metallic = inside * (rim_mask * 0.8 + cos_profile * 0.3) + (1.0 - inside) * 0.55
    # Add slight random per-dimple depth variation via low-freq noise
    noise_amp = 0.08
    noise = np.sin(X / dimple_spacing * 1.7 + rng.uniform(0, np.pi)) * \
            np.cos(Y / dimple_spacing * 1.3 + rng.uniform(0, np.pi)) * noise_amp
    result = metallic + noise
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_knurled_diamond(shape, seed, sm, frequency=28.0, angle_deg=60.0, **kwargs):
    """Precision diamond knurl (machine tool handle grip). Two families of diagonal ridges
    crossing at ~60°, creating raised diamond peaks. Ridge crossings = metallic peaks
    (double ridge height), valley between = metallic trough. CUT INTO solid surface —
    distinct from chainlink (wire crossings) or stamped expanded metal. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    angle_rad = np.deg2rad(angle_deg)
    # Family A ridges: at +angle
    proj_a = X * np.cos(angle_rad) + Y * np.sin(angle_rad)
    ridge_a = (np.cos(proj_a / (h / frequency) * 2.0 * np.pi) + 1.0) * 0.5
    # Family B ridges: at -angle (symmetric to create diamond peaks)
    proj_b = X * np.cos(-angle_rad) + Y * np.sin(-angle_rad)
    ridge_b = (np.cos(proj_b / (h / frequency) * 2.0 * np.pi) + 1.0) * 0.5
    # Diamond peaks: both ridge families at max = crossing point = metallic peak
    # Multiply gives diamond intersection peaks; average gives valley fill
    crossing = ridge_a * ridge_b   # high only at both-peak intersections
    combined = crossing * 0.8 + (ridge_a + ridge_b) * 0.1
    # Roughness spike at ridge tips (knurling is cut, not smooth)
    roughness_spike = (ridge_a ** 4 + ridge_b ** 4) * 0.2
    result = combined + roughness_spike
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_knurled_straight(shape, seed, sm, frequency=36.0, sharpness=4.0, **kwargs):
    """Straight knurl (axial knurling). Single family of parallel ridges at 0° — axial.
    Creates metallic bands: bright ridge / dark valley. Roughness peaks at ridge tips.
    Single-family, not crossing — fundamentally simpler than diamond knurl.
    Stepped/sharpened sine profile for machined-ridge crispness. G=Roughness primary."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Axial ridges: modulate on Y only (horizontal ridges = axial knurl on a cylinder)
    phase = (Y / h) * frequency * 2.0 * np.pi
    # Sharpened cosine → discrete stepped ridges (like a machine-cut tooth profile)
    raw = np.cos(phase)
    # Raise to power → sharpen peaks, flatten valleys
    ridge = np.sign(raw) * (np.abs(raw) ** (1.0 / sharpness))
    ridge = (ridge + 1.0) * 0.5  # remap to [0,1]
    # Slight tool-mark waviness from machine runout
    runout = np.sin(X / w * np.pi * rng.uniform(3, 7)) * 0.04
    result = ridge + runout
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_architectural_grid(shape, seed, sm, cell_size=40.0, frame_frac=0.10, **kwargs):
    """Architectural curtain wall grid (building facade). Large rectangular glass panels
    with polished aluminum frame. Frame: high metallic, low roughness (polished aluminum).
    Panel interior: very low metallic, moderate roughness (glass). Frame width = ~10% of cell.
    Uses min(fmod(x*scale), fmod(y*scale)) frame-proximity approach. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Panel aspect ratio: slightly wider than tall (curtain wall typical)
    cell_h = cell_size
    cell_w = cell_size * 1.35
    # Normalized position within each cell
    fx = (X % cell_w) / cell_w  # [0,1] across each cell column
    fy = (Y % cell_h) / cell_h  # [0,1] across each cell row
    # Distance to nearest frame edge (0 = edge, 0.5 = center of glass)
    dist_x = np.minimum(fx, 1.0 - fx)       # 0 at vertical frame, 0.5 at cell mid
    dist_y = np.minimum(fy, 1.0 - fy)       # 0 at horizontal frame, 0.5 at cell mid
    # Frame proximity: min of both distances (closer to frame wins)
    frame_dist = np.minimum(dist_x, dist_y)
    # Frame mask: within frame_frac of edge = frame zone
    on_frame = np.clip(1.0 - frame_dist / frame_frac, 0.0, 1.0)
    # Softened step for frame/glass boundary
    frame_soft = on_frame ** 0.5
    # Frame = high metallic (polished aluminum), glass = low metallic
    metallic = frame_soft * 0.85 + (1.0 - frame_soft) * 0.05
    # Slight variation per panel (manufacturing tolerance)
    panel_var = np.sin(np.floor(X / cell_w) * 3.7 + np.floor(Y / cell_h) * 5.3) * 0.06
    result = metallic + panel_var * (1.0 - frame_soft)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_hexagonal_tiles(shape, seed, sm, tile_size=22.0, grout_frac=0.12, **kwargs):
    """Hexagonal tile mosaic. Hex grid, each tile: smooth interior (low roughness, low metallic
    = ceramic/stone) with raised grout lines (higher metallic from mineral content, higher
    roughness from texture). Uses hex distance function for tile vs. grout classification.
    R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Hex grid geometry: flat-topped hexagons
    spacing_x = tile_size
    spacing_y = tile_size * np.sqrt(3.0) / 2.0
    # Axial coordinates
    col = np.floor(X / spacing_x)
    row = np.floor(Y / spacing_y)
    # Fractional position within cell
    fx = (X / spacing_x) - np.floor(X / spacing_x) - 0.5  # [-0.5, 0.5]
    fy = (Y / spacing_y) - np.floor(Y / spacing_y) - 0.5
    # Hex offset for alternating rows
    offset = (np.floor(Y / spacing_y).astype(np.int32) % 2) * 0.5
    fx_off = ((X / spacing_x - offset) % 1.0) - 0.5
    # Hex distance approximation: max of |fx|, (|fx| + |fy|*2/sqrt(3))/2... use simpler form
    hex_dist = np.maximum(np.abs(fx_off), (np.abs(fx_off) + np.abs(fy) * 1.1547) * 0.5773)
    # Normalize so hex boundary = 1.0
    hex_norm = hex_dist / 0.5
    # Grout = near hex boundary; tile interior = below threshold
    grout_threshold = 1.0 - grout_frac
    on_grout = np.clip((hex_norm - grout_threshold) / grout_frac, 0.0, 1.0)
    # Per-tile subtle variation (different tile colors/reflectivity)
    tile_id_x = np.floor(X / spacing_x + 0.5).astype(np.int32)
    tile_id_y = np.floor(Y / spacing_y + 0.5).astype(np.int32)
    tile_var = (np.sin(tile_id_x * 2.7 + tile_id_y * 4.1) * 0.5 + 0.5) * 0.12
    # Tile interior: low metallic ceramic, slight per-tile variation
    tile_metallic = 0.10 + tile_var
    # Grout: moderate metallic (mineral/cement), higher roughness
    grout_metallic = 0.40
    result = tile_metallic * (1.0 - on_grout) + grout_metallic * on_grout
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_brick_mortar(shape, seed, sm, brick_h=16.0, brick_w=36.0, mortar_frac=0.08, **kwargs):
    """Brick and mortar pattern. Staggered running-bond brick layout.
    Brick face: moderate roughness (clay texture), near-zero metallic.
    Mortar joint: higher roughness, slightly higher metallic (mineral aggregate).
    Row stagger offset of 0.5 per row = running bond. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Course (row) index and fractional position within row
    course = np.floor(Y / brick_h).astype(np.int32)
    fy = (Y % brick_h) / brick_h  # [0,1] within course height
    # Running bond: alternate courses offset by half brick width
    x_offset = (course % 2) * (brick_w * 0.5)
    fx = ((X + x_offset) % brick_w) / brick_w  # [0,1] within brick width
    # Distance to nearest mortar joint (horizontal or vertical)
    mortar_h_dist = np.minimum(fy, 1.0 - fy)                # distance to top/bottom joint
    mortar_v_dist = np.minimum(fx, 1.0 - fx)                # distance to left/right joint
    mortar_h_norm = mortar_h_dist / (mortar_frac * 0.5)     # 0 at joint, 1 inside brick
    mortar_v_norm = mortar_v_dist / (mortar_frac * 0.5)
    on_mortar_h = np.clip(1.0 - mortar_h_norm, 0.0, 1.0)
    on_mortar_v = np.clip(1.0 - mortar_v_norm, 0.0, 1.0)
    on_mortar = np.maximum(on_mortar_h, on_mortar_v)
    # Per-brick clay texture variation (subtle roughness difference)
    brick_id = np.floor((X + x_offset) / brick_w).astype(np.int32)
    brick_var = (np.sin(brick_id * 3.3 + course * 7.1) * 0.5 + 0.5) * 0.08
    # Brick face: near-zero metallic, moderate roughness
    brick_metallic = 0.04 + brick_var
    # Mortar joint: slightly higher metallic (aggregate), higher roughness
    mortar_metallic = 0.28
    result = brick_metallic * (1.0 - on_mortar) + mortar_metallic * on_mortar
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_corrugated_panel(shape, seed, sm, frequency=12.0, amplitude=0.4, **kwargs):
    """Corrugated metal panel (industrial siding/roofing). Sinusoidal cross-section profile.
    Metallic value depends on surface normal angle: wave tops (normal-facing) = high metallic
    (direct reflection), wave sides = medium, valley = low metallic. Strong directional
    sheen of corrugated metal. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Corrugation runs vertically (ridges left-to-right); x determines height
    phase = (X / w) * frequency * 2.0 * np.pi
    # Surface z-profile: sine wave
    z = np.sin(phase) * amplitude
    # Surface normal (in x-z plane): dz/dx = amplitude * freq * cos(phase)
    dzdx = amplitude * frequency / w * 2.0 * np.pi * np.cos(phase)
    # Normal angle from vertical: arctan(dzdx). Normal-facing = low dzdx = high metallic
    # cos(slope_angle) approximates the specular component
    cos_angle = 1.0 / np.sqrt(1.0 + dzdx ** 2)
    # Metallic = cos^2 of surface tilt (Phong-like normal weighting)
    metallic = cos_angle ** 2
    # Add slight panel-to-panel overlap shading (corrugated sheets overlap at ridge)
    overlap_shade = np.where(
        (X % (w / frequency)) < (w / frequency * 0.08),
        0.7,
        1.0
    )
    result = metallic * overlap_shade
    # Slight lengthwise variation (panel length sections)
    long_var = np.cos(Y / h * np.pi * rng.uniform(2, 5)) * 0.05
    result = result + long_var
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_riveted_plate(shape, seed, sm, rivet_spacing=24.0, rivet_radius_frac=0.28, **kwargs):
    """Riveted metal plate (aircraft/ship construction). Flat polished plate with circular
    rivet heads on regular grid. Each rivet: dome adds metallic peak, rivet edge has
    roughness spike. Plate between rivets: flat polished metal. Slight roughness smear
    around each rivet from installation. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Regular grid of rivets
    fx = (X % rivet_spacing) / rivet_spacing  # [0,1] within grid cell
    fy = (Y % rivet_spacing) / rivet_spacing
    # Distance from rivet center (center of each grid cell)
    dx = (fx - 0.5) * rivet_spacing
    dy = (fy - 0.5) * rivet_spacing
    r_rivet = np.sqrt(dx ** 2 + dy ** 2)
    rivet_radius = rivet_spacing * rivet_radius_frac
    # Rivet dome: Gaussian metallic peak (dome specularity)
    rivet_dome = np.exp(-(r_rivet / (rivet_radius * 0.6)) ** 2)
    # Rivet edge: roughness spike at r ≈ rivet_radius
    edge_spike = np.exp(-((r_rivet - rivet_radius) / (rivet_radius * 0.15)) ** 2)
    # Installation smear: slightly elevated roughness in 1-2px halo around rivet
    smear_halo = np.exp(-(r_rivet / (rivet_radius * 1.4)) ** 2) * 0.25
    # Base plate: high metallic flat surface
    plate_metallic = 0.75
    # Rivet contribution: peak at dome center, slight reduction at valley between rivets
    rivet_metallic = rivet_dome * 0.9 + edge_spike * 0.3
    # On-rivet vs off-rivet blend
    on_rivet = np.clip(rivet_dome + edge_spike * 0.5, 0.0, 1.0)
    result = plate_metallic * (1.0 - on_rivet * 0.4) + rivet_metallic * on_rivet + smear_halo * 0.15
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_weld_seam(shape, seed, sm, num_passes=3, pass_spacing=8.0, **kwargs):
    """Weld seam pattern. Linear weld bead running horizontally across surface.
    Weld crown: rough, oxidized (high G, moderate R). Heat-affected zone (HAZ):
    elevated roughness, reduced metallic (scale formation). Base metal: clean spec.
    Multiple parallel passes create weld ripple pattern. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Primary weld center: horizontal band through middle
    weld_center = 0.5 + rng.uniform(-0.15, 0.15)
    weld_width = 0.04 + rng.uniform(0, 0.02)
    # HAZ extends further on either side
    haz_width = weld_width * 3.5
    dist_from_weld = np.abs(Y - weld_center)
    # Weld crown mask
    weld_mask = np.exp(-(dist_from_weld / weld_width) ** 2)
    # HAZ mask (falls off beyond weld, before base metal)
    haz_mask = np.exp(-(dist_from_weld / haz_width) ** 2) * (1.0 - weld_mask * 0.8)
    # Weld ripple: sinusoidal variation along weld length (multi-pass ripple pattern)
    ripple_freq = w / (pass_spacing * 4.0)
    weld_ripple = (np.cos(X * ripple_freq * 2.0 * np.pi) * 0.5 + 0.5)
    # Bead height variation from weld puddle solidification
    puddle_variation = np.sin(X * ripple_freq * 3.7 * np.pi + rng.uniform(0, np.pi)) * 0.3 + 0.7
    # Metallic profile: base = high, HAZ = reduced (scale), weld crown = moderate oxidized
    base_metallic = 0.75
    haz_metallic = 0.35    # scale reduces metallic
    weld_metallic = 0.45 * puddle_variation   # oxidized but still some metal
    result = (base_metallic * (1.0 - haz_mask - weld_mask * 0.5)
              + haz_metallic * haz_mask
              + weld_metallic * weld_mask * weld_ripple)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_stamped_emboss(shape, seed, sm, cell_size=28.0, **kwargs):
    """Stamped/embossed sheet metal (decorative panel). Repeating circle-in-square motif.
    Emboss creates directional light reflection: raised areas catch light (high metallic),
    recessed areas shadowed (low metallic). Uses abs(combined sine waves) for sharp emboss
    peaks. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    scale = 1.0 / cell_size
    # Square grid emboss: orthogonal sine wave ridges
    sx = np.cos(X * scale * 2.0 * np.pi)
    sy = np.cos(Y * scale * 2.0 * np.pi)
    # Circle-in-square emboss: radial distance from cell center
    cx = (X % cell_size) - cell_size * 0.5
    cy = (Y % cell_size) - cell_size * 0.5
    r_cell = np.sqrt(cx ** 2 + cy ** 2)
    circle_radius = cell_size * 0.38
    # Embossed circle ring: peak at circle edge
    circle_edge = np.exp(-((r_cell - circle_radius) / (cell_size * 0.06)) ** 2)
    # Embossed grid: cross intersection peaks
    grid_cross = np.abs(sx * sy)
    # Combined emboss: raised ridges at grid intersections + circle edge
    emboss = np.maximum(grid_cross ** 0.5, circle_edge)
    # Sharp emboss profile using abs of sine combo (distinct from smooth Gaussian)
    sharp_grid = (np.abs(sx) ** 0.6 + np.abs(sy) ** 0.6) * 0.3
    result = emboss * 0.7 + sharp_grid * 0.3
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_cast_surface(shape, seed, sm, bump_scale=0.15, grain_scale=0.05, **kwargs):
    """Sand-cast metal surface texture. Random bumpy texture characteristic of sand casting:
    Gaussian roughness distribution overlaid with low-frequency large bumps (from sand grain
    clusters). R varies 140-200 (cast iron/aluminum base), G varies 120-200 (rough but not
    sandpaper-rough). Matte-metallic look of raw cast parts before machining. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Multi-scale FBM for sand grain surface:
    # Low freq: large sand cluster bumps
    # High freq: individual grain roughness
    def noise_layer(freq, shape, seed_off):
        ny = np.sin(Y * freq * 0.0314 + rng.uniform(0, np.pi)) * \
             np.cos(X * freq * 0.0271 + rng.uniform(0, np.pi))
        return ny
    # Sand grain cluster bumps (low frequency, large scale)
    low_freq = noise_layer(2.5, shape, 0) * 0.5 + \
               noise_layer(4.1, shape, 1) * 0.3 + \
               noise_layer(7.3, shape, 2) * 0.15
    # Fine grain roughness (high frequency, small scale)
    high_freq = noise_layer(18.0, shape, 3) * 0.4 + \
                noise_layer(35.0, shape, 4) * 0.3 + \
                noise_layer(67.0, shape, 5) * 0.2
    # Gaussian blur for large bump diffusion (sand grain clusters spread out)
    low_blur = _gauss(low_freq.astype(np.float32), sigma=3.5)
    # Cast surface: combination of cluster bumps + fine grain noise
    raw = low_blur * bump_scale + high_freq * grain_scale
    # Moderate metallic: 140-200 range → normalized output 0.55-0.78 (cast iron base)
    result = raw * 0.5 + 0.62  # bias toward moderate metallic
    # Random casting porosity via cKDTree (was brute-force loop over ~819 pores)
    num_pores = int(h * w * 0.0002)
    p_y = rng.randint(0, h, num_pores).astype(np.float32)
    p_x = rng.randint(0, w, num_pores).astype(np.float32)
    pts = np.column_stack([p_y, p_x])
    tree = cKDTree(pts)
    grid = np.column_stack([Y.ravel(), X.ravel()])
    k = min(3, len(pts))
    dists, _ = tree.query(grid, k=k, workers=-1)
    dists = dists.reshape(h, w, k) if k > 1 else dists.reshape(h, w, 1)
    avg_pr = 3.0  # average pore radius
    pore_map = np.sum(np.exp(-(dists ** 2) / (2 * avg_pr ** 2)) * 0.3, axis=2)
    result = result - np.clip(pore_map, 0.0, 0.3)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH F: NATURAL & ORGANIC (12 patterns)
# ============================================================================

def spec_wood_grain_fine(shape, seed, sm, ring_freq=0.55, ring_warp=6.0, **kwargs):
    """Fine wood grain — maple/birch parallel growth rings with FBM warp perturbation.
    ring_value = sin(y * ring_freq + fbm(x,y) * ring_warp). Earlywood (ring peak):
    high metallic, low roughness. Latewood (ring valley): low metallic, high roughness.
    Ring spacing ~8-12px at ring_freq=0.55. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, float(h), h, dtype=np.float32)
    xx = np.linspace(0.0, float(w), w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # FBM perturbation — 4 octaves of sinusoidal noise
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for oct_i, freq_scale in enumerate([1.0, 2.1, 4.3, 8.7]):
        ph_y = rng.uniform(0, 2 * np.pi)
        ph_x = rng.uniform(0, 2 * np.pi)
        fbm += amp * np.sin(Y * freq_scale * 0.04 + ph_y) * np.cos(X * freq_scale * 0.037 + ph_x)
        amp *= 0.5
    # Ring function: earlywood (sin→1) vs latewood (sin→-1)
    ring_val = np.sin(Y * ring_freq + fbm * ring_warp)
    # Metallic: high at earlywood (ring_val near +1), low at latewood
    metallic = ring_val * 0.5 + 0.5          # 0..1
    metallic = metallic * 0.55 + 0.25        # range 0.25..0.80
    # Roughness: inverse of metallic (latewood is rougher)
    roughness = 1.0 - metallic
    # Slight grain-direction noise on roughness
    grain_noise = np.sin(X * 0.3 + rng.uniform(0, np.pi)) * 0.04
    roughness = np.clip(roughness + grain_noise, 0.0, 1.0)
    result = metallic
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_wood_burl(shape, seed, sm, num_eyes=8, eye_influence=0.55, **kwargs):
    """Wood burl — swirling grain from multiple burl 'eye' seed points. Each eye
    has its own rotation direction. Ring function uses distance_to_nearest_eye
    instead of linear y-coordinate, creating complex swirling high-value burl veneer.
    R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Scatter burl eye positions
    eye_y = rng.uniform(h * 0.1, h * 0.9, num_eyes).astype(np.float32)
    eye_x = rng.uniform(w * 0.1, w * 0.9, num_eyes).astype(np.float32)
    eye_rot = rng.choice([-1.0, 1.0], num_eyes).astype(np.float32)  # rotation direction
    eye_freq = rng.uniform(0.25, 0.55, num_eyes).astype(np.float32)  # ring frequency per eye
    # Build Voronoi: nearest eye
    pts = np.stack([eye_y, eye_x], axis=1)
    tree = cKDTree(pts)
    coords = np.stack([Y.ravel(), X.ravel()], axis=1)
    dists, idx = tree.query(coords, k=1)
    dists = dists.reshape(h, w).astype(np.float32)
    idx = idx.reshape(h, w)
    # Per-pixel ring value using distance to nearest eye + angular swirl
    idx_flat = idx.ravel()
    cy = eye_y[idx_flat].reshape(h, w)
    cx = eye_x[idx_flat].reshape(h, w)
    rot = eye_rot[idx_flat].reshape(h, w)
    freq = eye_freq[idx_flat].reshape(h, w)
    # Angle from eye center — swirl offset
    angle = np.arctan2(Y - cy, X - cx) * rot
    ring_val = np.sin(dists * freq + angle * eye_influence)
    metallic = ring_val * 0.5 + 0.5          # 0..1
    metallic = metallic * 0.5 + 0.25         # range 0.25..0.75
    # Blend: near eye centers = more complex, away = simpler rings
    eye_radius = np.sqrt(h * w / num_eyes) * 0.7
    center_blend = np.exp(-dists / (eye_radius + 1e-6))
    metallic = metallic * (0.7 + 0.3 * center_blend)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_stone_granite(shape, seed, sm, num_crystals=600, **kwargs):
    """Granite crystalline texture. Multi-scale Voronoi mimics the crystalline grain
    structure: quartz crystals (high metallic/reflective), feldspar (medium metallic),
    mica (very high metallic, sharp flash). Crystal boundaries have roughness spike.
    R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Scatter crystal seed points
    pts_y = rng.uniform(0, h, num_crystals).astype(np.float32)
    pts_x = rng.uniform(0, w, num_crystals).astype(np.float32)
    # Assign mineral type: 0=feldspar(medium), 1=quartz(high), 2=mica(very high flash)
    mineral = rng.choice([0, 1, 2], num_crystals, p=[0.55, 0.30, 0.15])
    metallic_by_mineral = np.array([0.35, 0.72, 0.95], dtype=np.float32)
    roughness_by_mineral = np.array([0.65, 0.35, 0.10], dtype=np.float32)
    pts = np.stack([pts_y, pts_x], axis=1)
    tree = cKDTree(pts)
    coords = np.stack([Y.ravel(), X.ravel()], axis=1)
    dists, idx = tree.query(coords, k=2)  # nearest + second nearest for boundary
    dist1 = dists[:, 0].reshape(h, w).astype(np.float32)
    dist2 = dists[:, 1].reshape(h, w).astype(np.float32)
    idx1 = idx[:, 0].reshape(h, w)
    # Crystal boundary: where dist1 ≈ dist2
    boundary = np.exp(-((dist2 - dist1) ** 2) / (2.0 * 2.0 ** 2))
    # Per-crystal metallic and roughness lookup
    m_map = metallic_by_mineral[mineral[idx1.ravel()]].reshape(h, w)
    r_map = roughness_by_mineral[mineral[idx1.ravel()]].reshape(h, w)
    # Mica flash: large random sparkle within mica crystals
    mica_mask = (mineral[idx1.ravel()] == 2).reshape(h, w).astype(np.float32)
    flash_noise = np.abs(np.sin(Y * 0.47 + X * 0.31 + rng.uniform(0, np.pi)))
    m_map += mica_mask * flash_noise * 0.3
    # Roughness spike at boundaries
    r_map = np.clip(r_map + boundary * 0.25, 0.0, 1.0)
    result = np.clip(m_map, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_stone_marble(shape, seed, sm, vein_freq=0.08, vein_warp=7.0, **kwargs):
    """Marble vein pattern. Swirling veins: vein = sin(x*freq + fbm(x,y)*vein_warp).
    Vein areas (near zero of sine): high roughness (micro-fracture), moderate metallic
    (mineral-filled vein). Marble body: low roughness, low metallic (polished stone).
    Strong FBM warp creates organic feel. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, float(h), h, dtype=np.float32)
    xx = np.linspace(0.0, float(w), w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # FBM warp — 5 octaves for strong organic warping
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [1.0, 2.0, 4.0, 8.0, 16.0]:
        ph_y = rng.uniform(0, 2 * np.pi)
        ph_x = rng.uniform(0, 2 * np.pi)
        fbm += amp * (np.sin(Y * freq_s * 0.02 + ph_y) * 0.6 +
                      np.cos(X * freq_s * 0.023 + ph_x) * 0.4)
        amp *= 0.55
    # Second FBM for Y-direction warp (gives bidirectional curl)
    fbm2 = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [1.0, 2.0, 4.0, 8.0]:
        ph_y = rng.uniform(0, 2 * np.pi)
        ph_x = rng.uniform(0, 2 * np.pi)
        fbm2 += amp * np.sin(X * freq_s * 0.019 + Y * freq_s * 0.021 + ph_x)
        amp *= 0.5
    # Vein function: distance to vein = |sin()|
    vein_raw = np.sin(X * vein_freq + fbm * vein_warp + fbm2 * vein_warp * 0.4)
    vein_dist = np.abs(vein_raw)        # 0 = at vein center, 1 = between veins
    vein_mask = np.exp(-vein_dist * 4.0)  # soft vein indicator
    # Metallic: low in marble body, moderate in vein (mineral deposits)
    metallic = 0.15 + vein_mask * 0.50   # 0.15 body → 0.65 vein
    # Roughness: low in polished marble body, higher at micro-fracture veins
    roughness = 0.20 + vein_mask * 0.55
    result = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_water_ripple_spec(shape, seed, sm, num_drops=6, **kwargs):
    """Water ripple surface spec. Concentric circular waves from multiple random
    drop points. Near wave crest: higher metallic (water facet at crest angle
    reflects more). Trough: lower metallic. Multiple overlapping ripple systems
    create interference. Clearcoat: max gloss throughout (water surface). R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Random drop centers
    drop_y = rng.uniform(h * 0.1, h * 0.9, num_drops).astype(np.float32)
    drop_x = rng.uniform(w * 0.1, w * 0.9, num_drops).astype(np.float32)
    drop_freq = rng.uniform(0.08, 0.18, num_drops).astype(np.float32)
    drop_phase = rng.uniform(0, 2 * np.pi, num_drops).astype(np.float32)
    drop_amp = rng.uniform(0.5, 1.0, num_drops).astype(np.float32)
    # Accumulate overlapping ripple systems
    ripple_sum = np.zeros((h, w), dtype=np.float32)
    for i in range(num_drops):
        dist = np.sqrt((Y - drop_y[i]) ** 2 + (X - drop_x[i]) ** 2)
        # Decay amplitude with distance from drop center
        decay = np.exp(-dist / (max(h, w) * 0.35))
        wave = np.sin(dist * drop_freq[i] + drop_phase[i]) * decay * drop_amp[i]
        ripple_sum += wave
    # Metallic: higher at wave crest (sin→+1) — surface normal facet angle effect
    metallic = ripple_sum * 0.5 + 0.5    # 0..1
    metallic = metallic * 0.55 + 0.28   # range 0.28..0.83
    result = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_coral_reef(shape, seed, sm, branch_octaves=6, **kwargs):
    """Coral reef texture. Branching coral structure via multi-scale FBM creates
    irregular cellular/branching coral. Coral branch surfaces: moderate metallic
    (calcium carbonate shimmer), branching tips: slightly higher metallic. Inter-coral
    void areas: zero metallic, high roughness. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, float(h), h, dtype=np.float32)
    xx = np.linspace(0.0, float(w), w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Multi-scale FBM building coral branching structure
    fbm_a = np.zeros((h, w), dtype=np.float32)
    fbm_b = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for i in range(branch_octaves):
        freq_s = 2.0 ** i * 0.013
        ph = rng.uniform(0, 2 * np.pi, 4)
        fbm_a += amp * np.sin(X * freq_s + ph[0]) * np.cos(Y * freq_s * 1.1 + ph[1])
        fbm_b += amp * np.cos(X * freq_s * 1.17 + ph[2]) * np.sin(Y * freq_s * 0.93 + ph[3])
        amp *= 0.52
    # Domain-warp second pass for branching topology
    fbm_warped = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for i in range(4):
        freq_s = 2.0 ** i * 0.018
        ph = rng.uniform(0, 2 * np.pi, 2)
        fbm_warped += amp * np.sin((X + fbm_a * 18.0) * freq_s + ph[0]) * \
                            np.cos((Y + fbm_b * 18.0) * freq_s + ph[1])
        amp *= 0.5
    # Branching coral = threshold of domain-warped FBM
    coral_field = fbm_warped
    coral_norm = _normalize(coral_field)
    # Coral branch areas: above threshold
    branch_thresh = 0.55
    branch_mask = np.clip((coral_norm - branch_thresh) / (1.0 - branch_thresh), 0.0, 1.0)
    # Tips: top 10% of field = highest metallic
    tip_mask = np.clip((coral_norm - 0.85) / 0.15, 0.0, 1.0)
    metallic = branch_mask * 0.50 + tip_mask * 0.25   # branch: 0.50, tip: 0.75
    result = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_snake_scales(shape, seed, sm, scale_w=20.0, scale_h=14.0, **kwargs):
    """Reptile scale array. Elongated oval scales in offset rows. Each scale:
    specular peak near scale center-top (convex surface catches light), lower
    metallic at scale edges. Scale overlap regions: roughness spike where scales
    layer. Uses elliptical distance function per scale. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Scale grid: offset rows (like fish scales but elongated + different profile)
    row_idx = np.floor(Y / scale_h).astype(np.int32)
    row_frac = (Y / scale_h) - np.floor(Y / scale_h)  # 0..1 within row
    # Offset alternate rows by half scale width
    x_offset = (row_idx % 2) * (scale_w * 0.5)
    col_frac = ((X + x_offset) / scale_w) - np.floor((X + x_offset) / scale_w)
    # Distance to scale center (upper half of row = scale body)
    dx = (col_frac - 0.5) * scale_w     # px distance from scale center x
    dy = (row_frac - 0.35) * scale_h    # bias toward top of row (scale peak)
    # Elliptical distance (scales are elongated horizontally)
    ellipse_r = np.sqrt((dx / (scale_w * 0.46)) ** 2 + (dy / (scale_h * 0.52)) ** 2)
    # Scale interior: ellipse_r < 1.0
    inside = (ellipse_r < 1.0).astype(np.float32)
    # Specular peak at scale center-top (convex surface): metallic peaks at r≈0.3
    r_clamp = np.clip(ellipse_r, 0.0, 1.0)
    # Convex profile: peak near center-top, falls to edges
    scale_metallic = np.cos(r_clamp * np.pi * 0.5) ** 2 * inside
    # Overlap/underlap zone: where row_frac > 0.75 (scale overlap region)
    overlap = np.clip((row_frac - 0.70) / 0.30, 0.0, 1.0)
    # Overlap roughness spike (scales layering) reduces effective metallic
    scale_metallic *= (1.0 - overlap * 0.6)
    scale_metallic = scale_metallic * 0.65 + 0.15  # bias: 0.15 body → 0.80 peak
    result = np.clip(scale_metallic, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_fish_scales(shape, seed, sm, scale_r=16.0, **kwargs):
    """Fish scale array. Circular overlapping scales in offset rows. KEY DIFFERENCE
    from snake_scales: radial metallic gradient is INVERTED — higher at scale rim,
    lower at center (iridescent armored look). Creates the characteristic reflective
    edge shimmer of fish scales vs the convex peak of reptile scales. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    scale_d = scale_r * 2.0
    scale_h = scale_r * 1.3   # vertical spacing (overlap factor)
    row_idx = np.floor(Y / scale_h).astype(np.int32)
    row_frac = (Y / scale_h) - np.floor(Y / scale_h)
    # Offset alternate rows
    x_offset = (row_idx % 2) * (scale_d * 0.5)
    col_frac = ((X + x_offset) / scale_d) - np.floor((X + x_offset) / scale_d)
    # Distance to scale center (circular)
    dx = (col_frac - 0.5) * scale_d
    dy = (row_frac - 0.5) * scale_h
    r = np.sqrt(dx ** 2 + dy ** 2)
    norm_r = np.clip(r / scale_r, 0.0, 1.0)
    inside = (norm_r < 1.0).astype(np.float32)
    # INVERTED radial: high metallic at rim, low at center — fish scale iridescence
    # sin(r/radius * pi): 0 at center, peaks at r≈0.5, 0 at edge — but we INVERT:
    # actual fish: highest reflection at rim angle (scale edge catches light differently)
    rim_metallic = np.sin(np.clip(norm_r, 0.0, 1.0) * np.pi) * inside
    # Add subtle radial secondary shimmer rings (iridescent interference)
    shimmer = np.cos(norm_r * np.pi * 3.0) * 0.15 * inside
    metallic = rim_metallic * 0.60 + shimmer + 0.18
    metallic = np.clip(metallic * inside + (1.0 - inside) * 0.05, 0.0, 1.0)
    result = metallic
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_leaf_venation(shape, seed, sm, num_secondary=8, **kwargs):
    """Leaf vein network. Hierarchical vein structure approximated with oriented
    noise gradients: main mid-rib (center line, thickest), secondary veins at
    angles from mid-rib, tertiary veins filling gaps. Vein channels: high metallic
    (hydrated tissue), inter-vein leaf tissue: lower metallic, slight roughness.
    R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Main mid-rib: vertical center line — distance to X=0
    midrib_dist = np.abs(X)
    midrib_mask = np.exp(-midrib_dist * w * 0.4)
    # Secondary veins: fan out from mid-rib at regular angles
    secondary_total = np.zeros((h, w), dtype=np.float32)
    for i in range(num_secondary):
        # Secondary vein position along mid-rib (Y coordinate of branch point)
        branch_y = -0.85 + (1.7 * i / (num_secondary - 1))
        # Angle of secondary vein from mid-rib
        angle_side = rng.uniform(25, 55) * np.pi / 180.0
        if rng.rand() > 0.5:
            angle_side = -angle_side
        # Both left and right secondary veins at each level
        for side in [-1.0, 1.0]:
            vein_angle = angle_side * side
            # Vein direction vector
            vy = np.sin(np.abs(vein_angle))
            vx = np.cos(vein_angle) * side
            # Distance from each pixel to this secondary vein line
            # Line passes through (branch_y, 0), direction (vy, vx)
            dy = Y - branch_y
            dx_p = X - 0.0
            # Perpendicular distance to vein line
            perp = np.abs(dy * vx - dx_p * vy)
            # Only render on appropriate side
            along = dy * vy + dx_p * vx
            mask_side = (along > -0.05).astype(np.float32)
            secondary_total += np.exp(-perp * w * 0.6) * mask_side * 0.5
    secondary_total = np.clip(secondary_total, 0.0, 1.0)
    # Tertiary veins: fine FBM network filling the leaf tissue
    tertiary = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [12.0, 24.0, 48.0]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        layer = np.abs(np.sin(X * freq_s + ph[0]) * np.cos(Y * freq_s * 1.1 + ph[1]))
        layer = np.exp(-layer * 4.0)
        tertiary += amp * layer
        amp *= 0.5
    tertiary = _normalize(tertiary) * 0.30
    # Combine: mid-rib highest, secondary next, tertiary fine
    metallic = np.clip(midrib_mask * 0.85 + secondary_total * 0.55 + tertiary, 0.0, 1.0)
    # Background leaf tissue: low metallic
    metallic = metallic * 0.75 + 0.10
    result = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_terrain_erosion(shape, seed, sm, octaves=7, lacunarity=2.1, **kwargs):
    """Eroded terrain topology. Multi-octave domain-warped FBM creates ridge/valley
    topology. Ridgetops: lower roughness (wind-polished exposed rock), valley floors:
    higher roughness (sediment accumulation), cliff faces: high metallic (fresh exposed
    rock face). Gradient magnitude of FBM used as roughness proxy. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, 4.0, h, dtype=np.float32)
    xx = np.linspace(0.0, 4.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Domain warp FBM pass 1 (warp coordinates)
    warp_x = np.zeros((h, w), dtype=np.float32)
    warp_y = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for i in range(4):
        freq_s = lacunarity ** i
        ph = rng.uniform(0, 2 * np.pi, 4)
        warp_x += amp * np.sin(X * freq_s + ph[0]) * np.cos(Y * freq_s + ph[1])
        warp_y += amp * np.cos(X * freq_s + ph[2]) * np.sin(Y * freq_s + ph[3])
        amp *= 0.5
    # Warped FBM (terrain elevation)
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for i in range(octaves):
        freq_s = lacunarity ** i
        ph = rng.uniform(0, 2 * np.pi, 2)
        fbm += amp * np.sin((X + warp_x * 1.2) * freq_s + ph[0]) * \
                     np.cos((Y + warp_y * 1.2) * freq_s + ph[1])
        amp *= 0.48
    elevation = _normalize(fbm)
    # Gradient magnitude = slope = cliff face indicator
    gy = np.gradient(elevation, axis=0)
    gx = np.gradient(elevation, axis=1)
    slope = np.sqrt(gy ** 2 + gx ** 2).astype(np.float32)
    slope = _normalize(slope)
    # Ridgetops: local maxima of elevation (high elevation, low slope)
    ridge_mask = np.clip(elevation - slope * 0.5, 0.0, 1.0)
    # Valley floors: low elevation areas
    valley_mask = 1.0 - elevation
    # Cliff faces: high slope regions = high metallic (fresh exposed rock)
    metallic = slope * 0.65 + ridge_mask * 0.20 + 0.10
    metallic = np.clip(metallic, 0.0, 1.0)
    result = metallic
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def spec_crystal_growth(shape, seed, sm, num_crystals=80, **kwargs):
    """Crystal growth / geode interior. Radial crystal growth from center outward.
    Each crystal face is flat (low roughness) but at different angles — metallic
    varies with crystal face angle (FBM angular variation per Voronoi cell). Dense
    crystal packing creates Voronoi-like facets with angular metallic peaks. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy, cx = h / 2.0, w / 2.0
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Crystal tips radiate from center — place seeds on expanding rings
    crystal_tips_y = []
    crystal_tips_x = []
    for ring_r in np.linspace(max(h, w) * 0.05, max(h, w) * 0.70, num_crystals // 5):
        n_in_ring = max(3, int(2 * np.pi * ring_r / (max(h, w) * 0.12)))
        angles = rng.uniform(0, 2 * np.pi, n_in_ring)
        for a in angles:
            crystal_tips_y.append(cy + ring_r * np.sin(a))
            crystal_tips_x.append(cx + ring_r * np.cos(a))
    pts_y = np.array(crystal_tips_y[:num_crystals], dtype=np.float32)
    pts_x = np.array(crystal_tips_x[:num_crystals], dtype=np.float32)
    # Crystal face angle (random orientation per crystal)
    face_angles = rng.uniform(0, np.pi, len(pts_y)).astype(np.float32)
    # Voronoi
    pts = np.stack([pts_y, pts_x], axis=1)
    tree = cKDTree(pts)
    coords = np.stack([Y.ravel(), X.ravel()], axis=1)
    dists, idx = tree.query(coords, k=2)
    dist1 = dists[:, 0].reshape(h, w).astype(np.float32)
    dist2 = dists[:, 1].reshape(h, w).astype(np.float32)
    idx1 = idx[:, 0].reshape(h, w)
    # Radial distance from geode center (crystals brighter near center = more dense)
    r_center = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2)
    r_norm = np.clip(r_center / (max(h, w) * 0.5), 0.0, 1.0)
    # Per-crystal directional metallic: light catching flat face angle
    fa = face_angles[idx1.ravel()].reshape(h, w)
    cy_cell = pts_y[idx1.ravel()].reshape(h, w)
    cx_cell = pts_x[idx1.ravel()].reshape(h, w)
    dy = Y - cy_cell
    dx = X - cx_cell
    proj = np.cos(np.arctan2(dy, dx) - fa)   # face-angle dot product
    face_metallic = proj * 0.5 + 0.5         # 0..1
    # Crystal boundary glint: sharp metallic spike at cell edges
    boundary = np.exp(-((dist2 - dist1) ** 2) / (2.0 * 1.5 ** 2))
    metallic = face_metallic * (1.0 - r_norm * 0.4) + boundary * 0.35
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_lava_flow(shape, seed, sm, flow_freq=0.035, aa_roughness=0.72, **kwargs):
    """Solidified lava flow texture. Pahoehoe lava: smooth ropy flow lines (sinusoidal,
    low roughness, moderate metallic) separated by rough aa lava zones (FBM high-roughness).
    Flow line direction follows a perturbed gradient field. Contrast between glassy
    ropy lava and rough broken aa lava. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, float(h), h, dtype=np.float32)
    xx = np.linspace(0.0, float(w), w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Flow direction field: gentle perturbed gradient (lava flows downhill)
    # Base flow direction: mostly in X direction with FBM perturbation
    fbm_flow = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [1.0, 2.0, 4.0, 8.0]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        fbm_flow += amp * np.sin(X * freq_s * 0.012 + ph[0]) * \
                         np.cos(Y * freq_s * 0.015 + ph[1])
        amp *= 0.52
    # Flow coordinate: X + warp (perpendicular to flow direction)
    flow_coord = X + fbm_flow * 35.0
    # Pahoehoe ropy lines: sin along flow direction
    ropy = np.sin(flow_coord * flow_freq * 2.0 * np.pi)
    # Ropy rope distance (0 = on rope surface)
    rope_mask = (ropy * 0.5 + 0.5)  # 0..1 continuous, peaks at rope crests
    # AA lava zones: high-freq FBM in the valleys between ropes
    aa_fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [8.0, 16.0, 32.0, 64.0]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        aa_fbm += amp * np.abs(np.sin(X * freq_s * 0.011 + ph[0]) *
                               np.cos(Y * freq_s * 0.013 + ph[1]))
        amp *= 0.5
    aa_field = _normalize(aa_fbm)
    # AA zone indicator: where rope_mask is low = between ropes = aa lava
    aa_zone = 1.0 - rope_mask
    # Metallic: pahoehoe rope surface = moderate metallic (glassy), aa zone = lower
    metallic = rope_mask * 0.60 + aa_zone * 0.18
    # Roughness: pahoehoe ropes = low roughness (glassy), aa = very rough
    roughness = rope_mask * 0.20 + aa_zone * aa_roughness + aa_field * aa_zone * 0.25
    result = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH G: LIGHTING & OPTICAL EFFECTS (12 patterns)
# ============================================================================

def spec_fresnel_gradient(shape, seed, sm, edge_metallic=0.92, center_metallic=0.38,
                          fbm_strength=0.18, **kwargs):
    """Fresnel reflectivity gradient. Real Fresnel physics: surfaces appear more
    reflective at glancing angles (edges) than at normal incidence (center).
    Radial proxy from image center with FBM perturbation. Near edges = high
    metallic, low roughness (glancing angle). Near center = moderate metallic,
    moderate roughness (normal incidence). R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Radial distance from center (0=center, 1=corner)
    radius = np.sqrt(X * X + Y * Y) / np.sqrt(2.0)
    radius = np.clip(radius, 0.0, 1.0)
    # FBM perturbation on the radial field — organic edge variation
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [2.0, 4.0, 8.0, 16.0]:
        ph = rng.uniform(0, 2 * np.pi, 4)
        fbm += amp * (np.sin(X * freq_s + ph[0]) * np.cos(Y * freq_s + ph[1]) +
                      np.sin(X * freq_s * 1.3 + ph[2]) * np.cos(Y * freq_s * 0.9 + ph[3]) * 0.5)
        amp *= 0.5
    fbm = fbm / (fbm.std() + 1e-6) * fbm_strength
    # Fresnel proxy: angle = radius + fbm perturbation
    fresnel_angle = np.clip(radius + fbm, 0.0, 1.0)
    # Schlick Fresnel approximation: F = F0 + (1-F0)*(1-cos(theta))^5
    # cos(theta) ≈ 1 - fresnel_angle; (1-cos)^5 = fresnel_angle^5
    F0 = 0.04  # base reflectivity
    schlick = F0 + (1.0 - F0) * np.power(fresnel_angle, 5.0)
    # Map Schlick to metallic range
    metallic = center_metallic + (edge_metallic - center_metallic) * schlick
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_caustic_light(shape, seed, sm, caustic_sharpness=8.0, num_octaves=4, **kwargs):
    """Caustic light patterns (light focused through curved surface). Bright
    branching caustic lines via folded-wavefront simulation: compute gradient
    of FBM noise, fold points along gradient direction. Caustic lines = where
    many folded points converge (high gradient magnitude of folded FBM).
    High metallic at caustic lines, near-zero elsewhere. Very low roughness
    throughout. Creates shimmering bright-line patterns like light through water.
    R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, float(h), h, dtype=np.float32)
    xx = np.linspace(0.0, float(w), w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    scale = 1.0 / max(h, w)
    Ys = Y * scale
    Xs = X * scale
    # Multi-octave FBM for base potential field
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    freq = 4.0
    for _ in range(num_octaves):
        ph = rng.uniform(0, 2 * np.pi, 4)
        fbm += amp * np.sin(Xs * freq * 2 * np.pi + ph[0]) * np.cos(Ys * freq * 2 * np.pi + ph[1])
        fbm += amp * 0.5 * np.cos(Xs * freq * 1.7 * 2 * np.pi + ph[2]) * \
                           np.sin(Ys * freq * 2.1 * 2 * np.pi + ph[3])
        amp *= 0.5
        freq *= 2.1
    # Gradient of FBM (approximate via finite differences)
    grad_y = np.gradient(fbm, axis=0)
    grad_x = np.gradient(fbm, axis=1)
    # Fold: map each point to (x + grad_x * fold_strength, y + grad_y * fold_strength)
    fold_strength = 0.035 * max(h, w)
    fold_x = np.clip(X + grad_x * fold_strength, 0, w - 1.001)
    fold_y = np.clip(Y + grad_y * fold_strength, 0, h - 1.001)
    # Density of folded points: create histogram of landing positions
    fold_xf = fold_x.ravel().astype(np.float32)
    fold_yf = fold_y.ravel().astype(np.float32)
    density, _, _ = np.histogram2d(fold_yf, fold_xf,
                                    bins=[h, w],
                                    range=[[0, h], [0, w]])
    density = density.astype(np.float32)
    # Smooth slightly to get soft caustic lines
    density = _gauss(density, sigma=1.2)
    density = _normalize(density)
    # Sharp caustic threshold: raise to power to concentrate the bright lines
    caustic = np.power(density, caustic_sharpness)
    caustic = _normalize(caustic)
    metallic = caustic * 0.90 + 0.05
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_diffraction_grating(shape, seed, sm, fine_freq=120.0, secondary_strength=0.25, **kwargs):
    """Diffraction grating (like a CD/DVD surface). Very fine parallel ruling
    lines create diffraction: grating = sin(x * fine_freq)^2. Metallic varies
    with constructive interference zones (position-dependent phase). Secondary
    perpendicular grating adds cross-diffraction shimmer. Different from the
    earlier diffraction_grating pattern (which uses multi-order rainbow logic);
    this one uses the squared-sine grating rule directly. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, float(h), h, dtype=np.float32)
    xx = np.linspace(0.0, float(w), w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    scale = 2.0 * np.pi / max(h, w)
    # Primary grating: fine parallel lines in X direction
    primary = np.sin(X * scale * fine_freq) ** 2
    # Constructive interference: position-dependent phase modulation
    # Interference position depends on both x and y (like viewing angle shift)
    phase_mod = np.sin(Y * scale * fine_freq * 0.08 + rng.uniform(0, 2 * np.pi)) * 0.5
    primary_intf = np.sin(X * scale * fine_freq + phase_mod * np.pi) ** 2
    # Secondary perpendicular grating (cross-diffraction)
    secondary = np.sin(Y * scale * fine_freq * 0.94) ** 2 * secondary_strength
    # Modulate secondary with spatial FBM for organic disc imperfections
    fbm = np.zeros((h, w), dtype=np.float32)
    for freq_s, a in [(2.0, 0.5), (5.0, 0.3), (11.0, 0.2)]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        fbm += a * np.sin(X * scale * freq_s + ph[0]) * np.cos(Y * scale * freq_s + ph[1])
    fbm = (fbm * 0.5 + 0.5)
    # Combine: primary interference peaks dominate, secondary adds cross pattern
    metallic = primary_intf * 0.65 + secondary * fbm * 0.35
    metallic = np.clip(_normalize(metallic), 0.0, 1.0)
    return _sm_scale(metallic, sm).astype(np.float32)


def spec_retroreflective(shape, seed, sm, grid_spacing=22.0, microsphere_fill=0.55, **kwargs):
    """Retroreflective surface (road signs / safety vest). Glass microspheres or
    corner-cube arrays create retro-reflection: very high metallic at near-normal
    incidence (retroreflector center), drops at angles. Simulate with Gaussian-peak
    metallic at grid of corner-cube centers (arranged in staggered grid), high
    fill between peaks from microsphere coverage. Creates the characteristic
    sparkly grid of retroreflective materials. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    spacing = grid_spacing
    # Staggered grid: even rows offset by half-spacing
    row_idx = np.floor(Y / spacing).astype(np.int32)
    col_frac = (X / spacing) + (row_idx % 2) * 0.5
    local_x = (col_frac % 1.0) - 0.5   # -0.5 to 0.5
    local_y = (Y / spacing % 1.0) - 0.5
    # Gaussian peak at corner-cube center (normal incidence)
    sigma_cube = 0.18  # fraction of cell
    cube_peak = np.exp(-(local_x ** 2 + local_y ** 2) / (2 * sigma_cube ** 2))
    # Microsphere fill: moderate high metallic between cube peaks
    micro_fill = microsphere_fill * (1.0 - cube_peak * 0.3)
    # FBM variation for non-uniform bead coating
    fbm = np.zeros((h, w), dtype=np.float32)
    for freq_s, a in [(3.0, 0.4), (7.0, 0.25), (15.0, 0.15)]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        fbm += a * np.sin(X * freq_s * 0.015 + ph[0]) * np.cos(Y * freq_s * 0.015 + ph[1])
    fbm = (fbm * 0.5 + 0.5)
    metallic = cube_peak * 0.90 + micro_fill * fbm * 0.65
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_velvet_sheen(shape, seed, sm, edge_width=0.22, fiber_scatter=0.12, **kwargs):
    """Velvet sheen effect (light scattering from fiber tips). Velvet has highest
    reflectivity at grazing angles (fiber tips catch light). Simulate: directional
    gradient field with FBM noise approximates 'edges' of curved surfaces.
    Edge-adjacent areas: high metallic, near-zero roughness (fiber tip specular).
    Center areas: low metallic, high roughness (fiber base absorption). The
    directional gradient field gives different orientations per zone. R=Metallic
    + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # FBM curvature field — simulates curved fabric surface orientations
    curvature = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [1.5, 3.2, 6.5, 13.0]:
        ph = rng.uniform(0, 2 * np.pi, 4)
        curvature += amp * (np.sin(X * freq_s * 2 * np.pi + ph[0]) *
                            np.cos(Y * freq_s * 2 * np.pi + ph[1]))
        amp *= 0.52
    curvature = _normalize(curvature)
    # Gradient magnitude of curvature field = edge proxy (where direction changes)
    grad_y = np.gradient(curvature, axis=0)
    grad_x = np.gradient(curvature, axis=1)
    grad_mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
    grad_mag = _normalize(grad_mag)
    # Edge zones (high gradient) = fiber tips = high metallic, low roughness
    # Center zones (low gradient) = fiber base = low metallic, high roughness
    edge_mask = grad_mag
    # Add small-scale fiber scatter noise
    scatter = np.zeros((h, w), dtype=np.float32)
    for freq_s, a in [(20.0, 0.5), (45.0, 0.3), (90.0, 0.2)]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        scatter += a * np.abs(np.sin(X * freq_s * 2 * np.pi + ph[0]) *
                              np.cos(Y * freq_s * 2 * np.pi + ph[1]))
    scatter = _normalize(scatter) * fiber_scatter
    metallic = edge_mask * 0.85 + scatter * 0.15
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_sparkle_flake(shape, seed, sm, density_base=0.018, size_tiers=(3, 6, 10), **kwargs):
    """Metal flake sparkle field. Random oriented flakes create point-source
    specular highlights. Three flake size tiers. Each flake: circular high-metallic
    center (mirror face), dark ring around flake (edge shadow), very low metallic
    between flakes. FBM density clustering makes flakes group organically.
    Distinct from flake_scatter (2D scatter), micro_sparkle (ultra-fine grain),
    and gold_flake (large irregular leaf shapes). R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    canvas = np.zeros((h, w), dtype=np.float32)
    # FBM density map — flakes cluster in high-density regions
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    density_fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [2.0, 4.0, 8.0]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        density_fbm += amp * (np.sin(X * freq_s * 2 * np.pi + ph[0]) *
                              np.cos(Y * freq_s * 2 * np.pi + ph[1]) * 0.5 + 0.5)
        amp *= 0.5
    density_fbm = _normalize(density_fbm)
    for tier_idx, flake_r in enumerate(size_tiers):
        tier_density = density_base * (0.7 ** tier_idx)
        num_flakes = int(tier_density * h * w / (np.pi * flake_r ** 2))
        # Sample positions weighted by FBM density
        flat_prob = density_fbm.ravel()
        flat_prob = flat_prob / (flat_prob.sum() + 1e-9)
        chosen = rng.choice(h * w, size=min(num_flakes, h * w), replace=False, p=flat_prob)
        fy = (chosen // w).astype(np.float32)
        fx = (chosen % w).astype(np.float32)
        for i in range(len(fy)):
            cy_i, cx_i = int(fy[i]), int(fx[i])
            y0 = max(0, cy_i - flake_r - 2)
            y1 = min(h, cy_i + flake_r + 3)
            x0 = max(0, cx_i - flake_r - 2)
            x1 = min(w, cx_i + flake_r + 3)
            Yl = np.arange(y0, y1, dtype=np.float32)
            Xl = np.arange(x0, x1, dtype=np.float32)
            Ygr, Xgr = np.meshgrid(Yl, Xl, indexing='ij')
            dist = np.sqrt((Ygr - fy[i]) ** 2 + (Xgr - fx[i]) ** 2)
            # Mirror face peak at center
            face = np.exp(-(dist / (flake_r * 0.55)) ** 2)
            # Edge shadow ring
            ring_dist = np.abs(dist - flake_r * 0.85)
            ring = np.exp(-(ring_dist / (flake_r * 0.18)) ** 2) * 0.4
            flake_val = np.clip(face - ring, 0.0, 1.0)
            canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1], flake_val)
    metallic = np.clip(canvas, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_iridescent_film(shape, seed, sm, film_octaves=5, band_freq=12.0, **kwargs):
    """Thin-film iridescence. FBM-driven film thickness creates spatially-varying
    metallic modulation: thick zones = high metallic, thin zones = low metallic.
    The thickness variation is banded (sin of thickness * band_freq) to simulate
    the interference color bands of thin-film optics. Roughness near zero throughout
    (smooth film surface). Creates the oily iridescent shimmer pattern distinct
    from interference_bands (which is purely sinusoidal x/y). R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Film thickness via FBM (organic flowing pools)
    thickness = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    freq = 1.8
    for _ in range(film_octaves):
        ph = rng.uniform(0, 2 * np.pi, 4)
        thickness += amp * (np.sin(X * freq * 2 * np.pi + ph[0]) *
                            np.cos(Y * freq * 2 * np.pi + ph[1]) +
                            np.cos(X * freq * 1.6 * 2 * np.pi + ph[2]) *
                            np.sin(Y * freq * 2.2 * 2 * np.pi + ph[3]) * 0.6)
        amp *= 0.52
        freq *= 2.07
    thickness = _normalize(thickness)
    # Interference banding: metallic = sin^2(thickness * band_freq * π)
    metallic = np.sin(thickness * band_freq * np.pi) ** 2
    # Modulate by thickness envelope: very thin or very thick film less metallic
    envelope = np.sin(thickness * np.pi)  # peaks at mid-thickness
    metallic = metallic * (0.7 + 0.3 * envelope)
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_anisotropic_radial(shape, seed, sm, num_segments=24, star_power=2.0, **kwargs):
    """Radial anisotropic reflection (machined aluminum disc). Metallic varies
    with angular position using atan2 star formula: metallic = sin(angle *
    num_segments/2)^star_power. Creates sharp star-like radiating metallic bands
    distinct from brushed_radial (which has smooth gradient lines) and
    radial_sunburst (which uses abs(sin) + smoothstep). FBM radial noise adds
    slight organic imperfection to the machined-disc look. R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy, cx = h * 0.5, w * 0.5
    yy = np.arange(h, dtype=np.float32) - cy
    xx = np.arange(w, dtype=np.float32) - cx
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Angle from center
    angle = np.arctan2(Y, X)   # -pi to pi
    # Radial distance (normalized)
    radius = np.sqrt(Y ** 2 + X ** 2) / (max(h, w) * 0.5)
    radius = np.clip(radius, 0.0, 1.0)
    # Angular star pattern: sin(angle * N/2)^p
    star = np.sin(angle * (num_segments / 2.0)) ** star_power
    star = star * 0.5 + 0.5   # remap -1..1 → 0..1
    # Slight FBM radial perturbation (like tooling run-out)
    runout = np.zeros((h, w), dtype=np.float32)
    for freq_s, a in [(3.0, 0.4), (7.0, 0.3), (15.0, 0.2)]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        runout += a * np.sin(X * freq_s * 0.01 + ph[0]) * np.cos(Y * freq_s * 0.01 + ph[1])
    runout = (runout * 0.5 + 0.5) * 0.06
    # Radial fade: strongest near mid-radius (disc face), fades at center+edge
    radial_fade = np.sin(radius * np.pi)
    metallic = star * radial_fade * (1.0 - runout) * 0.85 + runout * 0.15
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_bokeh_scatter(shape, seed, sm, num_circles=60, hex_jitter=0.15, **kwargs):
    """Bokeh scatter pattern (out-of-focus aperture circles). Hexagonally-packed
    overlapping circles with Gaussian soft edges. Each circle ±20% size variation.
    Circle interiors: max gloss, moderate metallic. Circle edges: metallic spike
    (lens aperture blade ring). Hexagonal arrangement from aperture blade geometry.
    Distinct from concentric_ripple (single center), patina_bloom (chemistry),
    and EDM_dimple (machined craters). R=Metallic + B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    canvas = np.zeros((h, w), dtype=np.float32)
    # Hexagonal grid layout
    hex_cols = int(np.sqrt(num_circles * w / h) + 2)
    hex_rows = int(num_circles / hex_cols) + 2
    base_r = min(h, w) / (2.0 * max(hex_rows, hex_cols) * 0.85)
    for row in range(hex_rows):
        for col in range(hex_cols):
            # Hex grid center
            cx_base = (col + (row % 2) * 0.5) * base_r * 1.8
            cy_base = row * base_r * 1.56
            # Add jitter
            jx = rng.uniform(-hex_jitter, hex_jitter) * base_r
            jy = rng.uniform(-hex_jitter, hex_jitter) * base_r
            cx_i = cx_base + jx - base_r * 0.5
            cy_i = cy_base + jy - base_r * 0.5
            # Size variation ±20%
            circle_r = base_r * rng.uniform(0.80, 1.20)
            # Build local patch
            y0 = max(0, int(cy_i - circle_r - 3))
            y1 = min(h, int(cy_i + circle_r + 4))
            x0 = max(0, int(cx_i - circle_r - 3))
            x1 = min(w, int(cx_i + circle_r + 4))
            if y1 <= y0 or x1 <= x0:
                continue
            Yl = np.arange(y0, y1, dtype=np.float32)
            Xl = np.arange(x0, x1, dtype=np.float32)
            Ygr, Xgr = np.meshgrid(Yl, Xl, indexing='ij')
            dist = np.sqrt((Ygr - cy_i) ** 2 + (Xgr - cx_i) ** 2)
            # Soft interior: Gaussian fill
            interior = np.exp(-(dist / (circle_r * 0.6)) ** 2) * 0.65
            # Edge ring: metallic spike at aperture blade ring
            ring_dist = np.abs(dist - circle_r * 0.88)
            ring = np.exp(-(ring_dist / (circle_r * 0.12)) ** 2) * 0.90
            bokeh_val = np.clip(interior + ring, 0.0, 1.0)
            canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1], bokeh_val)
    metallic = np.clip(canvas, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_light_leak(shape, seed, sm, streak_width=0.035, num_ghosts=5, **kwargs):
    """Light leak / lens flare artifacts. Photographic lens flare: main bright
    streak along one axis (high metallic band), circular halo at specific radius
    from center, ghost aperture circles at intervals along streak axis. Creates
    a stylized photographic artifact look. Main streak = anamorphic flare bar.
    Halo ring = primary lens reflection. Ghosts = secondary internal reflections.
    R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy, cx = h * 0.5, w * 0.5
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    canvas = np.zeros((h, w), dtype=np.float32)
    # Main anamorphic streak: horizontal bright bar through center
    dy = np.abs(Y - cy) / h
    streak_sigma = streak_width
    streak = np.exp(-(dy ** 2) / (2 * streak_sigma ** 2)) * 0.85
    canvas += streak
    # Primary halo: circular ring at ~35% of min dimension from center
    halo_r = min(h, w) * rng.uniform(0.28, 0.42)
    dist_center = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2)
    halo_width = min(h, w) * 0.025
    halo = np.exp(-((dist_center - halo_r) ** 2) / (2 * halo_width ** 2)) * 0.60
    canvas += halo
    # Ghost aperture circles along the streak axis at intervals
    ghost_positions = np.linspace(cx * 0.3, cx * 1.7, num_ghosts)
    for i, gx in enumerate(ghost_positions):
        ghost_r = min(h, w) * rng.uniform(0.04, 0.14)
        ghost_strength = rng.uniform(0.15, 0.45) * (0.7 ** i)
        ghost_dist = np.sqrt((Y - cy) ** 2 + (X - gx) ** 2)
        ghost_ring_w = ghost_r * 0.18
        ghost = np.exp(-((ghost_dist - ghost_r * 0.8) ** 2) / (2 * ghost_ring_w ** 2))
        ghost_fill = np.exp(-(ghost_dist / (ghost_r * 0.75)) ** 2) * 0.3
        canvas += (ghost + ghost_fill) * ghost_strength
    metallic = np.clip(canvas, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_subsurface_depth(shape, seed, sm, sss_depth=0.65, scatter_radius=8.0, **kwargs):
    """Subsurface scattering depth map. Simulates light penetration depth in
    translucent materials (skin, marble, wax). High curvature areas (high FBM
    gradient magnitude) = lower metallic (light scatters into material, diffuse
    glow). Low curvature (smooth surfaces) = higher metallic (surface reflection
    dominates). Roughness gradient creates the characteristic 'depth glow' look
    of SSS materials. Distinct from cloud_wisps (pearlescent) and marble_vein
    (linear veins). R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    # Multi-scale FBM for subsurface structure
    structure = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    freq = 1.2
    for _ in range(6):
        ph = rng.uniform(0, 2 * np.pi, 4)
        structure += amp * (np.sin(X * freq * 2 * np.pi + ph[0]) *
                            np.cos(Y * freq * 2 * np.pi + ph[1]) +
                            np.cos(X * freq * 1.7 * 2 * np.pi + ph[2]) *
                            np.sin(Y * freq * 2.3 * 2 * np.pi + ph[3]) * 0.5)
        amp *= 0.5
        freq *= 2.0
    structure = _normalize(structure)
    # Curvature proxy: gradient magnitude (high = high curvature = SSS dominant)
    grad_y = np.gradient(structure, axis=0)
    grad_x = np.gradient(structure, axis=1)
    curvature = np.sqrt(grad_x ** 2 + grad_y ** 2)
    curvature = _normalize(curvature)
    # Blur curvature to simulate scatter radius (light travels sideways in material)
    sss_blur = _gauss(curvature, sigma=scatter_radius)
    sss_blur = _normalize(sss_blur)
    # Metallic: high where smooth (surface reflection), low where high SSS
    metallic = (1.0 - sss_blur) * 0.72 + structure * 0.18
    metallic = np.clip(metallic * sss_depth + (1.0 - sss_depth) * 0.5, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_chromatic_aberration(shape, seed, sm, inner_radius=0.30, fringe_period=0.04,
                               fringe_octaves=3, **kwargs):
    """Chromatic aberration pattern. Lens CA separates channels at image edges.
    Inner zone (center): uniform spec (no aberration). Outer zone: alternating
    metallic peaks at fine spatial frequency (R/G/B channel separation proxy).
    The fringe period scales with distance from center (aberration grows outward).
    FBM perturbation on the boundary adds organic lens distortion. Distinct from
    diffraction_grating (uniform grating) and moire_overlay (two grids).
    R=Metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cy, cx = h * 0.5, w * 0.5
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    radius = np.sqrt(X * X + Y * Y) / np.sqrt(2.0)
    radius = np.clip(radius, 0.0, 1.0)
    # FBM perturbation on the radius to simulate lens field curvature
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [2.0, 5.0, 11.0]:
        ph = rng.uniform(0, 2 * np.pi, 2)
        fbm += amp * np.sin(X * freq_s * 2 * np.pi + ph[0]) * \
                     np.cos(Y * freq_s * 2 * np.pi + ph[1])
        amp *= 0.45
    fbm = fbm / (fbm.std() + 1e-6) * 0.06
    radius_perturbed = np.clip(radius + fbm, 0.0, 1.0)
    # Outer zone mask (beyond inner_radius = aberration zone)
    outer_mask = np.clip((radius_perturbed - inner_radius) / (1.0 - inner_radius + 1e-6),
                         0.0, 1.0)
    outer_mask = outer_mask ** 1.4  # smooth falloff
    # Chromatic fringe pattern: alternating metallic bands at fine period
    # Period shrinks with radius (aberration magnitude grows outward)
    # Multi-frequency fringe sum simulates R + G + B channel separation
    fringe = np.zeros((h, w), dtype=np.float32)
    for oct_i in range(fringe_octaves):
        period = fringe_period * (0.65 ** oct_i)
        ph = rng.uniform(0, 2 * np.pi)
        fringe += np.sin(radius_perturbed / period * 2 * np.pi + ph) ** 2
    fringe = _normalize(fringe)
    # Inner zone: flat moderate metallic (no aberration)
    inner_metallic = np.full((h, w), 0.50, dtype=np.float32)
    metallic = inner_metallic * (1.0 - outer_mask) + fringe * outer_mask * 0.85 + \
               outer_mask * 0.10
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH H: Surface Treatments (patterns 85–92)
# ============================================================================

def spec_electroplated_chrome(shape, seed, sm, cell_density=55.0, metallic_base=230,
                               metallic_range=15, **kwargs):
    """Electroplated chrome surface. Chrome plating has a micro-crystalline surface
    structure from the electroplating process. Unlike brushed chrome (directional),
    electroplated chrome has isotropic micro-nodule texture from crystal nucleation.
    Fine-scale Voronoi noise (~50+ cells per unit): each cell slightly different
    metallic value. Clearcoat at absolute minimum variation (16-18 out of 255).
    R=Metallic (high, ~230 base ± 15), G=Roughness (very low, near-mirror),
    B=Clearcoat (near 16, max gloss)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    # Generate dense Voronoi for micro-crystalline structure
    n_pts = int(cell_density * cell_density * 0.8)
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    # Per-cell metallic offset: each crystal facet reflects slightly differently
    cell_offsets = rng.uniform(-metallic_range, metallic_range, n_pts).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tree = cKDTree(np.column_stack([pts_y, pts_x]))
    dist, idx = tree.query(np.column_stack([yy.ravel(), xx.ravel()]), k=2)
    dist = dist.reshape(h, w, 2)
    idx = idx.reshape(h, w, 2)
    # Base metallic from cell assignment
    cell_metallic = cell_offsets[idx[:, :, 0]]  # per-pixel cell offset
    # Cell boundary darkening (very slight dip at crystal grain boundaries)
    dist_diff = dist[:, :, 1] - dist[:, :, 0]
    boundary = np.exp(-dist_diff * 12.0)  # narrow at grain boundary
    metallic_raw = (metallic_base + cell_metallic) / 255.0
    metallic_raw -= boundary * 0.04  # tiny dip at boundaries
    metallic = np.clip(metallic_raw, 0.0, 1.0)
    # Roughness: very low (mirror-like), slight per-cell variation
    roughness = np.clip(boundary * 0.08 + rng.uniform(0.02, 0.05, (h, w)).astype(np.float32), 0.0, 0.15)
    # Clearcoat: minimum variation (16-18 → 0.063–0.071 normalized)
    cc_base = 16.0 / 255.0
    cc = np.full((h, w), cc_base, dtype=np.float32) + boundary * (2.0 / 255.0)
    # Return metallic channel (primary)
    combined = metallic * 0.7 + (1.0 - roughness) * 0.2 + (1.0 - cc) * 0.1
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_anodized_texture(shape, seed, sm, pore_density=105.0, metallic_base=170,
                           **kwargs):
    """Anodized aluminum surface texture. Anodizing creates a nanoporous aluminum
    oxide layer with a very regular hexagonal pore array. Simulates the hexagonal
    pore grid: tiny circles of lower metallic (the pores, filled with air/dye)
    surrounded by high-metallic oxide inter-pore material. Pore array is hexagonal,
    fine pitch (100+ pores per unit). Overall: moderate metallic (150-190),
    slightly higher roughness than bare aluminum, glossy clearcoat.
    R=Metallic, G=Roughness, B=Clearcoat (glossy)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    pitch = w / pore_density
    pore_radius = pitch * 0.22  # pores are ~22% of pitch radius
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    # Hexagonal grid: offset every other row by pitch/2
    row_idx = np.floor(Y / (pitch * 0.866)).astype(np.int32)
    col_offset = (row_idx % 2) * pitch * 0.5
    # Distance to nearest hex grid point
    hex_y = (Y % (pitch * 0.866)) / (pitch * 0.866)
    # Approximate hex grid pore field using two overlapping sine grids
    # Hex = product of 3 cosine waves at 0°, 60°, 120°
    freq = 2.0 * np.pi / pitch
    a0 = np.cos(X * freq)
    a1 = np.cos(X * freq * 0.5 + Y * freq * 0.866)
    a2 = np.cos(-X * freq * 0.5 + Y * freq * 0.866)
    hex_field = (a0 + a1 + a2) / 3.0  # range roughly [-1, 1], +1 at hex centers
    # Pores are at hex_field maxima (field > threshold)
    pore_mask = np.clip((hex_field - 0.75) / 0.25, 0.0, 1.0)  # 1.0 at pore center
    # Inter-pore oxide: high metallic (anodized oxide is bright aluminum oxide)
    inter_pore_metallic = metallic_base / 255.0
    pore_metallic = (metallic_base - 60) / 255.0  # pores are hollow — lower metallic
    metallic = inter_pore_metallic * (1.0 - pore_mask) + pore_metallic * pore_mask
    # Roughness: slightly higher than bare aluminum (oxide layer is not perfectly smooth)
    roughness = 0.18 + pore_mask * 0.12
    metallic = np.clip(metallic + rng.uniform(-0.01, 0.01, (h, w)).astype(np.float32), 0.0, 1.0)
    roughness = np.clip(roughness, 0.0, 1.0)
    combined = metallic * 0.65 + (1.0 - roughness) * 0.35
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_powder_coat_texture(shape, seed, sm, cell_size=22.0, roughness_base=0.50,
                              **kwargs):
    """Powder coat texture spec pattern. Powder coating has a distinctive 'orange peel'
    surface texture from electrostatic particle application and oven curing. The texture
    is non-metallic (particles are paint powder, not metal), semi-glossy, with broad
    smooth bumps (wavelength 20-30px) and very slight peaks — like orange peel but
    softer than spray orange peel. G=Roughness (100-160), R=Metallic (0-20, non-metallic),
    B=Clearcoat (semi-glossy). Key difference from orange_peel_texture: lower frequency,
    no metal, softer peak character."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    # FBM for broad orange peel bumps (wavelength ~20-30px)
    noise = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for octave in range(4):
        freq = 1.0 / cell_size * (2 ** octave)
        ph = rng.uniform(0, 2 * np.pi, 4)
        yy = np.linspace(0, 1, h, dtype=np.float32)
        xx = np.linspace(0, 1, w, dtype=np.float32)
        X, Y = np.meshgrid(xx, yy)
        noise += amp * np.sin(X * w * freq * 2 * np.pi + ph[0]) * \
                        np.cos(Y * h * freq * 2 * np.pi + ph[1])
        noise += amp * 0.5 * np.sin(X * w * freq * 1.7 * 2 * np.pi + ph[2] +
                                     Y * h * freq * 0.6 * 2 * np.pi + ph[3])
        amp *= 0.55
    noise = _normalize(noise)
    # Powder coat: roughness is the dominant signal
    # Bump peaks = slightly smoother (particles fused there), valleys = slightly rougher
    roughness = roughness_base - (noise - 0.5) * 0.25  # peaks smoother, valleys rougher
    # Very low metallic (powder is pigment + resin, not metal)
    metallic = 0.04 + noise * 0.06  # 0-20/255 range
    roughness = np.clip(roughness, 0.39, 0.63)
    metallic = np.clip(metallic, 0.0, 0.08)
    combined = roughness * 0.75 + metallic * 0.10 + noise * 0.15
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_thermal_spray(shape, seed, sm, splat_density=0.018, **kwargs):
    """Thermal spray coating (plasma spray / HVOF). Creates a 'splat' texture:
    individual droplets of molten metal solidified on impact. Each splat has
    a slightly raised metallic peak (solidified droplet center), rough edge
    (impact crater rim / solidification boundary), and lower metallic in
    center of large splats (oxidized top surface). Dense field of overlapping
    circular splats. Characteristic 'orange peel with metallic sheen'.
    R=Metallic, G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    n_splats = int(splat_density * h * w)
    sy = rng.uniform(0, h, n_splats).astype(np.float32)
    sx = rng.uniform(0, w, n_splats).astype(np.float32)
    # Splat radii: 3 size tiers (small, medium, large)
    size_tier = rng.randint(0, 3, n_splats)
    radii = np.array([4.0, 8.0, 14.0], dtype=np.float32)[size_tier]
    metallic_map = np.zeros((h, w), dtype=np.float32)
    roughness_map = np.zeros((h, w), dtype=np.float32)
    count_map = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tree = cKDTree(np.column_stack([sy, sx]))
    # Query k nearest splats per pixel
    k = min(8, n_splats)
    dists, indices = tree.query(np.column_stack([yy.ravel(), xx.ravel()]), k=k)
    dists = dists.reshape(h, w, k)
    indices = indices.reshape(h, w, k)
    for ki in range(k):
        r_ki = radii[indices[:, :, ki]]
        d_ki = dists[:, :, ki]
        in_splat = (d_ki < r_ki).astype(np.float32)
        # Normalized radius within splat
        r_norm = np.clip(d_ki / (r_ki + 1e-6), 0.0, 1.0)
        # Metallic: peak at center-ish, dip at very center (oxidized top), rim flash
        splat_metallic = np.where(r_norm < 0.3,
                                  0.55 + r_norm * 0.6,  # rising from center
                                  np.where(r_norm < 0.75,
                                           0.73 - (r_norm - 0.3) * 0.3,
                                           0.60 + (r_norm - 0.75) * 0.8))  # rim flash
        # Roughness: spike at rim (solidification front), smooth at center
        splat_roughness = 0.2 + r_norm * r_norm * 0.55 + np.exp(-((r_norm - 0.85) ** 2) / 0.01) * 0.35
        metallic_map += in_splat * splat_metallic
        roughness_map += in_splat * splat_roughness
        count_map += in_splat
    valid = count_map > 0
    metallic_map[valid] /= count_map[valid]
    roughness_map[valid] /= count_map[valid]
    # Background (unsplated substrate): rough, low metallic
    metallic_map[~valid] = 0.25
    roughness_map[~valid] = 0.80
    metallic_map = np.clip(metallic_map, 0.0, 1.0)
    roughness_map = np.clip(roughness_map, 0.0, 1.0)
    combined = metallic_map * 0.65 + (1.0 - roughness_map) * 0.35
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_electroformed_texture(shape, seed, sm, num_columns=None, col_aspect=2.8,
                                **kwargs):
    """Electroformed metal surface (grown metal). Electroforming grows metal layer by
    layer — resulting in columnar grain structure oriented perpendicular to the mandrel
    surface. Simulate columnar grain growth: elongated Voronoi cells taller than wide
    (aspect ratio ~2.5-3:1), oriented vertically. Each column: metallic varies from
    column base (lower, buried layers) to column tip (higher, freshest surface).
    Creates the directional columnar structure of electroformed copper/nickel.
    R=Metallic (directional gradient), G=Roughness (column boundaries)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    if num_columns is None:
        num_columns = int((w / 8.0) * (h / 8.0))
    # Generate column seed points — stretched vertically (columnar growth)
    n = num_columns
    pts_x = rng.uniform(0, w, n).astype(np.float32)
    pts_y = rng.uniform(0, h, n).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Anisotropic distance: stretch y axis to create tall columns
    pts_aniso = np.column_stack([pts_y / col_aspect, pts_x])
    query_pts = np.column_stack([yy.ravel() / col_aspect, xx.ravel()])
    tree = cKDTree(pts_aniso)
    dist, idx = tree.query(query_pts, k=2)
    dist = dist.reshape(h, w, 2)
    idx = idx.reshape(h, w, 2)
    # Column boundary roughness
    dist_diff = (dist[:, :, 1] - dist[:, :, 0]) / (dist[:, :, 0] + 0.5)
    boundary = np.exp(-dist_diff * 6.0)
    # Columnar metallic gradient: tip (top, y=0) is brightest
    # Each column has slightly different base metallic (compositional variation)
    col_base = rng.uniform(0.45, 0.65, n).astype(np.float32)[idx[:, :, 0]]
    y_norm = yy / h  # 0=top (tip), 1=bottom (base)
    # Column tips (near y=0) = higher metallic; base = lower
    tip_boost = (1.0 - y_norm) * 0.3
    metallic = col_base + tip_boost - boundary * 0.12
    metallic = np.clip(metallic, 0.0, 1.0)
    roughness = boundary * 0.60 + 0.08
    roughness = np.clip(roughness, 0.0, 1.0)
    combined = metallic * 0.7 + (1.0 - roughness) * 0.3
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_pvd_coating(shape, seed, sm, cell_density=80.0, **kwargs):
    """PVD (Physical Vapor Deposition) coating texture. PVD coatings (TiN, TiAlN on
    cutting tools) form via droplet nucleation — atom clusters land and grow into
    very fine uniform nodules. Ultra-fine Voronoi with extremely small cells.
    Very high metallic throughout (180-240, PVD is very smooth/reflective), very
    low roughness (G: 10-30). Note: TiN has characteristic golden color but this
    spec map only encodes surface topology, not color. The extreme uniformity and
    micro-nodule texture distinguish PVD from electroplated chrome (different cell
    distribution) and brushed surfaces (no directionality).
    R=Metallic (180-240), G=Roughness (very low)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    n_pts = int(cell_density * cell_density * 0.9)
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    # Very slight per-nucleation-site metallic variation
    site_metallic = rng.uniform(0.70, 0.95, n_pts).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tree = cKDTree(np.column_stack([pts_y, pts_x]))
    dist, idx = tree.query(np.column_stack([yy.ravel(), xx.ravel()]), k=2)
    dist = dist.reshape(h, w, 2)
    idx = idx.reshape(h, w, 2)
    cell_m = site_metallic[idx[:, :, 0]]
    dist_diff = dist[:, :, 1] - dist[:, :, 0]
    # Very narrow grain boundaries (PVD grains nearly flush)
    boundary = np.exp(-dist_diff * 20.0)
    metallic = cell_m - boundary * 0.03  # almost no boundary dip
    # Overall very high metallic (180-240)
    metallic = 0.70 + metallic * 0.24  # maps to ~178-240/255
    # Very low roughness with tiny per-site variation
    roughness = 0.05 + boundary * 0.06 + rng.uniform(0, 0.02, (h, w)).astype(np.float32)
    metallic = np.clip(metallic, 0.0, 1.0)
    roughness = np.clip(roughness, 0.0, 0.12)
    combined = metallic * 0.80 + (1.0 - roughness) * 0.20
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_shot_peened(shape, seed, sm, dimple_density=0.022, dimple_radius=6.0,
                     **kwargs):
    """Shot peened surface. Shot peening fires hardened shot at a metal surface,
    creating overlapping circular impact dimples covering nearly the entire surface.
    Dense field of overlapping Gaussian depressions: dimple center = local roughness
    peak (impact compressed material), dimple rim = slight metallic flash (compressive
    stress raises material slightly, catching light). Coverage so high dimples overlap
    completely. G=Roughness (140-200), R=Metallic (80-140), B=Clearcoat (120-180,
    peened surfaces lose their gloss). Work-hardened surface has moderate metallic."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    n_dimples = int(dimple_density * h * w)
    dy = rng.uniform(0, h, n_dimples).astype(np.float32)
    dx = rng.uniform(0, w, n_dimples).astype(np.float32)
    # Vary dimple radii slightly
    radii = dimple_radius * rng.uniform(0.7, 1.3, n_dimples).astype(np.float32)
    roughness_map = np.zeros((h, w), dtype=np.float32)
    metallic_map = np.zeros((h, w), dtype=np.float32)
    weight_map = np.zeros((h, w), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tree = cKDTree(np.column_stack([dy, dx]))
    k = min(6, n_dimples)
    dists, indices = tree.query(np.column_stack([yy.ravel(), xx.ravel()]), k=k)
    dists = dists.reshape(h, w, k)
    indices = indices.reshape(h, w, k)
    for ki in range(k):
        r_ki = radii[indices[:, :, ki]]
        d_ki = dists[:, :, ki]
        in_d = (d_ki < r_ki * 1.4).astype(np.float32)
        r_norm = np.clip(d_ki / (r_ki + 1e-6), 0.0, 1.5)
        # Roughness: Gaussian peak at dimple center (compressive deformation)
        rough_d = 0.65 * np.exp(-r_norm * r_norm * 1.2) + 0.25
        # Metallic: rim flash from work hardening (raised rim catches light)
        metal_d = 0.35 + 0.25 * np.exp(-((r_norm - 0.7) ** 2) / 0.12)
        roughness_map += in_d * rough_d
        metallic_map += in_d * metal_d
        weight_map += in_d
    valid = weight_map > 0
    roughness_map[valid] /= weight_map[valid]
    metallic_map[valid] /= weight_map[valid]
    roughness_map[~valid] = 0.55
    metallic_map[~valid] = 0.30
    roughness_map = np.clip(roughness_map, 0.0, 1.0)
    metallic_map = np.clip(metallic_map, 0.0, 1.0)
    combined = roughness_map * 0.55 + metallic_map * 0.45
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_laser_etched(shape, seed, sm, tile_size=32.0, border_frac=0.18, **kwargs):
    """Laser-etched surface pattern. Laser etching creates sharp-edged matte areas
    on a polished substrate. The etched/polished boundary is a step function (not
    gradual) — the laser ablates material with very sharp edge definition.
    Pattern: tiled grid with etched border strips surrounding polished centers.
    Etched areas: G=Roughness 200+ (rough ablated surface), R=Metallic ~40 (oxidized).
    Polished areas: G=Roughness ~10 (mirror finish), R=Metallic ~200 (bare polished metal).
    The sharp binary boundary is the key characteristic distinguishing this from
    gradual weathering patterns."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    # Tile-local coordinates
    tx = (X % tile_size) / tile_size
    ty = (Y % tile_size) / tile_size
    # Border strip: within border_frac of any edge = etched
    in_border = ((tx < border_frac) | (tx > 1.0 - border_frac) |
                 (ty < border_frac) | (ty > 1.0 - border_frac)).astype(np.float32)
    # Sharp step function (no gradual transition)
    # Add slight FBM wobble to the border edge for realistic laser imperfection
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [4.0, 8.0, 16.0]:
        ph = rng.uniform(0, 2 * np.pi, 4)
        fbm += amp * np.sin(X * freq_s / w * 2 * np.pi + ph[0]) * \
                     np.cos(Y * freq_s / h * 2 * np.pi + ph[1])
        amp *= 0.5
    fbm = fbm / (fbm.std() + 1e-6) * (border_frac * 0.25)
    # Perturbed border: shift tx, ty slightly before thresholding
    tx_p = np.clip(tx + fbm * 0.5, 0.0, 1.0)
    ty_p = np.clip(ty + fbm * 0.5, 0.0, 1.0)
    in_border = ((tx_p < border_frac) | (tx_p > 1.0 - border_frac) |
                 (ty_p < border_frac) | (ty_p > 1.0 - border_frac)).astype(np.float32)
    # Etched (border): rough + low metallic; polished (center): smooth + high metallic
    roughness_etched = 0.82
    roughness_polished = 0.04
    metallic_etched = 0.16
    metallic_polished = 0.80
    roughness = roughness_polished * (1.0 - in_border) + roughness_etched * in_border
    metallic = metallic_polished * (1.0 - in_border) + metallic_etched * in_border
    # Combined: metallic dominates in polished areas, roughness in etched
    combined = metallic * 0.6 + (1.0 - roughness) * 0.4
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


# ============================================================================
# PRIORITY 2 BATCH I: Specialty & Exotic (patterns 93–100)
# ============================================================================

def spec_liquid_metal(shape, seed, sm, wave1_freq=0.8, wave2_freq=1.3, amplitude=0.04,
                      **kwargs):
    """Liquid metal / mercury surface spec. Mercury at rest has near-perfect
    reflectivity (G: 2-8, R: 240-255) interrupted only by standing gravity waves.
    Two-frequency sinusoidal interference pattern (like mercury in a dish, lit from
    above) creates subtle metallic variation. The standing wave pattern from two
    slightly different frequencies creates beating interference — distinguishes this
    from flat chrome (which has no surface normal variation). The amplitude is very
    low (0.02-0.06) — mercury is almost perfectly flat.
    R=Metallic (240-255), G=Roughness (2-8), B=Clearcoat (16-18)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    # Standing wave 1: primary
    ph1 = rng.uniform(0, 2 * np.pi, 2)
    wave1 = np.sin(X * wave1_freq * 2 * np.pi * w / 100.0 + ph1[0]) * \
            np.cos(Y * wave1_freq * 2 * np.pi * h / 100.0 + ph1[1])
    # Standing wave 2: slightly different frequency → beat pattern
    ph2 = rng.uniform(0, 2 * np.pi, 2)
    wave2 = np.sin(X * wave2_freq * 2 * np.pi * w / 100.0 + ph2[0]) * \
            np.cos(Y * wave2_freq * 2 * np.pi * h / 100.0 + ph2[1])
    # Interference: beat envelope
    interference = (wave1 + wave2) * 0.5
    # Surface normal variation → metallic modulation
    metallic = 0.95 + interference * amplitude  # 0.95 base = ~242/255
    # Extremely low roughness (G: 2-8), slight variation at wave peaks
    roughness = 0.015 + np.abs(interference) * 0.010
    metallic = np.clip(metallic, 0.0, 1.0)
    roughness = np.clip(roughness, 0.0, 0.04)
    combined = metallic * 0.85 + (1.0 - roughness) * 0.15
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_chameleon_flake(shape, seed, sm, cell_density=28.0, metallic_base=190,
                          **kwargs):
    """ChromaFlair / chameleon flake surface spec. Multi-layer thin-film flakes
    (ChromaFlair pigment) create angle-dependent color shift. Each flake is an
    individual thin-film platelet with its own reflectivity angle. In spec terms:
    Voronoi cells at medium scale (20-40 per unit) each get a random metallic value
    assigned by hash (random-metallic mosaic). Inter-flake boundaries: slight
    roughness spike (flake edge scatter). Base metallic: 160-220. The random
    per-flake metallic mosaic is the spec signature of genuine ChromaFlair.
    R=Metallic, G=Roughness (boundary spikes only)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    n_pts = int(cell_density * cell_density)
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    # Per-flake metallic: random mosaic (160-220 range = 0.627-0.863)
    flake_metallic = rng.uniform(0.627, 0.863, n_pts).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tree = cKDTree(np.column_stack([pts_y, pts_x]))
    dist, idx = tree.query(np.column_stack([yy.ravel(), xx.ravel()]), k=2)
    dist = dist.reshape(h, w, 2)
    idx = idx.reshape(h, w, 2)
    metallic = flake_metallic[idx[:, :, 0]]
    # Flake boundary: roughness spike at cell edge
    dist_diff = dist[:, :, 1] - dist[:, :, 0]
    boundary_sharpness = np.exp(-dist_diff * 8.0)
    roughness = boundary_sharpness * 0.35 + 0.04
    metallic = np.clip(metallic - boundary_sharpness * 0.04, 0.0, 1.0)
    roughness = np.clip(roughness, 0.0, 1.0)
    combined = metallic * 0.70 + (1.0 - roughness) * 0.30
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_xirallic_crystal(shape, seed, sm, cell_density=14.0, **kwargs):
    """Xirallic crystal flake (alumina flakes with iron oxide coating). Xirallic
    creates 'deep sparkle': flakes are larger and more widely spaced than standard
    metallic flake, with higher individual reflectivity but lower density. Alumina
    (aluminum oxide) platelet faces are highly specular at center (bright crystal face),
    dropping to low metallic at flake edge. Inter-flake areas: moderate R and G.
    Larger Voronoi cells (10-20 per unit) with steep radial metallic gradient from
    flake center to edge. Creates 'depth-sparkle' character distinct from regular
    metallic flake (which has smaller, denser, more uniform cells).
    R=Metallic (200-255 at flake center), G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    n_pts = int(cell_density * cell_density)
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tree = cKDTree(np.column_stack([pts_y, pts_x]))
    dist, idx = tree.query(np.column_stack([yy.ravel(), xx.ravel()]), k=2)
    dist = dist.reshape(h, w, 2)
    idx = idx.reshape(h, w, 2)
    # Cell size varies per flake (simulate size distribution)
    cell_sizes = rng.uniform(w / (cell_density * 1.5), w / (cell_density * 0.7), n_pts).astype(np.float32)
    local_radius = cell_sizes[idx[:, :, 0]]
    r_norm = np.clip(dist[:, :, 0] / (local_radius * 0.5 + 1e-6), 0.0, 1.0)
    # Metallic: very high at crystal center, drops steeply at edges
    # High center = 200-255/255, edge = 60-80/255
    metallic_center = 0.90  # 229/255 ≈ crystal face specular
    metallic_edge = 0.27   # 68/255 ≈ flake edge scatter
    metallic = metallic_center * (1.0 - r_norm) ** 2.5 + metallic_edge * (1.0 - (1.0 - r_norm) ** 2.5)
    # Inter-flake: lower metallic (R=80), moderate roughness (G=80)
    dist_diff = dist[:, :, 1] - dist[:, :, 0]
    inter_flake = np.clip(1.0 - dist_diff * 3.0, 0.0, 1.0)  # 1.0 in deep inter-flake space
    metallic = metallic * (1.0 - inter_flake * 0.5) + inter_flake * 0.31  # inter = R~80
    roughness = 0.08 + inter_flake * 0.23  # G~80 in inter-flake
    metallic = np.clip(metallic, 0.0, 1.0)
    roughness = np.clip(roughness, 0.0, 1.0)
    combined = metallic * 0.72 + (1.0 - roughness) * 0.28
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_holographic_foil(shape, seed, sm, grating1_freq=55.0, grating2_freq=48.0,
                           **kwargs):
    """Holographic foil / rainbow chrome. A holographic foil has two families of
    diffraction gratings at 90° to each other at slightly different line frequencies.
    The beat pattern of the two gratings creates moiré interference — metallic peaks
    where both gratings constructively interfere. Fundamentally different from
    spec_diffraction_grating (single grating family) and moire_overlay (two grids at
    small angle offset). This uses perpendicular gratings at different frequencies —
    creating a 2D checkerboard beat pattern with both horizontal and vertical periodicity.
    R=Metallic (varies with interference)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    ph1 = rng.uniform(0, 2 * np.pi, 2)
    ph2 = rng.uniform(0, 2 * np.pi, 2)
    # Grating 1: horizontal lines at freq1
    g1 = np.sin(X * grating1_freq * 2 * np.pi + ph1[0]) ** 2
    # Grating 2: vertical lines at freq2 (90° rotation, different freq)
    g2 = np.sin(Y * grating2_freq * 2 * np.pi + ph2[0]) ** 2
    # Beat pattern: product = constructive interference where both are bright
    beat = g1 * g2
    # Add cross-term: diagonal beat from sum frequency
    g_cross1 = np.sin((X * grating1_freq + Y * grating2_freq) * 2 * np.pi + ph1[1]) ** 2
    g_cross2 = np.sin((X * grating1_freq - Y * grating2_freq) * 2 * np.pi + ph2[1]) ** 2
    # Holographic foil: strong beat + cross modulation
    metallic = beat * 0.55 + g_cross1 * 0.20 + g_cross2 * 0.20 + 0.05
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_oil_film_thick(shape, seed, sm, num_pools=6, **kwargs):
    """Thick oil film / spilled oil spec. A thick oil film smoothes over the rough
    substrate beneath. FBM defines oil pooling regions: thick pools have very smooth
    surface (oil fills and levels), thin film edges let substrate texture bleed through.
    Pool centers: very smooth (G=5-15/255), high gloss (B=16-20). Pool edges/thin areas:
    substrate roughness bleeds through (G=80-120), moderate gloss (B=60-100). The
    spatial gradient from pool center to edge is the key effect — oil 'fills' surface
    roughness proportionally to thickness. Different from oil_slick (thin-film colors)
    and depth_gradient (coating thickness). R=Metallic (low, oil is non-metallic),
    G=Roughness (inverse of oil thickness), B=Clearcoat."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    # FBM to define oil thickness distribution
    thickness = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [1.5, 3.0, 6.0, 12.0]:
        ph = rng.uniform(0, 2 * np.pi, 4)
        thickness += amp * np.sin(X * freq_s * 2 * np.pi + ph[0]) * \
                          np.cos(Y * freq_s * 2 * np.pi + ph[1])
        amp *= 0.5
    thickness = _normalize(thickness)
    # Pool centers: Gaussian peaks at random locations
    for _ in range(num_pools):
        py = rng.uniform(0.1, 0.9)
        px = rng.uniform(0.1, 0.9)
        pr = rng.uniform(0.08, 0.20)
        pool_r = np.sqrt((X - px) ** 2 + (Y - py) ** 2)
        pool_bump = np.exp(-pool_r ** 2 / (2 * pr ** 2))
        thickness += pool_bump * 0.6
    thickness = _normalize(thickness)
    # Thick oil → very smooth (G low), thin edges → substrate roughness bleeds through
    roughness_thick = 0.025   # G≈6/255 at pool center
    roughness_thin = 0.43     # G≈110/255 at thin edge
    roughness = roughness_thin * (1.0 - thickness) + roughness_thick * thickness
    # Oil itself is non-metallic but its smooth surface reflects well
    metallic = 0.15 + thickness * 0.12  # slight specular increase with thickness
    roughness = np.clip(roughness, 0.0, 1.0)
    metallic = np.clip(metallic, 0.0, 1.0)
    # Combined: thickness is the key driver
    combined = thickness * 0.40 + (1.0 - roughness) * 0.40 + metallic * 0.20
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_magnetic_ferrofluid(shape, seed, sm, hex_spacing=30.0, spike_sigma=0.35,
                              **kwargs):
    """Ferrofluid spike pattern (Rosensweig instability). Ferrofluid in a magnetic
    field self-organizes into a regular hexagonal array of spikes via the Rosensweig
    instability. Each spike is a tall sharp cone — Gaussian profile exp(-r²/σ²).
    Spike tips: very high metallic (240+, apex reflects directly), spike sides:
    decreasing metallic, valleys between spikes: low metallic (50-80/255).
    Hexagonal grid distribution. Creates sci-fi textured surface with dramatic
    bright spikes on dark valleys. Fundamentally different from ferrofluid-inspired
    patterns — this specifically models the 3D spike geometry.
    R=Metallic (240+ at tips, 50-80 in valleys)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    # Hex grid spike positions
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    # Hex grid: two basis vectors
    b1x, b1y = hex_spacing, 0.0
    b2x, b2y = hex_spacing * 0.5, hex_spacing * 0.866
    # For each pixel, find distance to nearest hex spike
    # Use the three-cosine hex field approach for efficiency
    freq = 2.0 * np.pi / hex_spacing
    h1 = np.cos(X * freq)
    h2 = np.cos(X * freq * 0.5 + Y * freq * 0.866)
    h3 = np.cos(-X * freq * 0.5 + Y * freq * 0.866)
    # Combined hex field: peaks at hex lattice points
    hex_field = (h1 + h2 + h3) / 3.0  # range [-1, 1], +1 at hex lattice
    # Add slight random phase jitter (ferrofluid spikes are not perfect hex)
    ph_jitter = rng.uniform(-0.15, 0.15, (h, w)).astype(np.float32) * 0.08
    hex_field_j = np.clip(hex_field + ph_jitter, -1.0, 1.0)
    # Spike height: Gaussian in (1 - hex_field) space
    # hex_field = 1 at spike tip, -1 at valley
    spike_height = np.exp(-((1.0 - hex_field_j) / (spike_sigma * 2.0)) ** 2)
    # Metallic: very high at spike tip (0.94+), low in valley (0.20-0.31)
    valley_metallic = 0.22
    tip_metallic = 0.96  # 244/255
    metallic = valley_metallic + (tip_metallic - valley_metallic) * spike_height
    metallic = np.clip(metallic, 0.0, 1.0)
    return _sm_scale(_normalize(metallic), sm).astype(np.float32)


def spec_aerogel_surface(shape, seed, sm, octaves=4, threshold=0.52, **kwargs):
    """Aerogel surface texture. Aerogel is the lowest-density solid — nanofoam
    structure of interconnected SiO2 struts with 95%+ air. The surface is a fractal
    pore network: interconnected voids separated by smooth glass-like struts. Simulate
    with multi-scale FBM with threshold masking to create interconnected nanofoam
    topology. R=Metallic very low (20-60/255, aerogel is mostly air), G=Roughness
    variable (pore walls vs. struts), B=Clearcoat moderate (struts are smooth glass).
    Very unusual spec signature: low metallic everywhere, but struts have near-zero
    roughness (glass) while pore walls have high roughness (rough air-glass interface)."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    # Multi-scale FBM for fractal pore network
    fbm_fine = np.zeros((h, w), dtype=np.float32)
    fbm_coarse = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for octave in range(octaves + 2):
        freq_s = 2.0 ** (octave + 1)
        ph = rng.uniform(0, 2 * np.pi, 4)
        layer = np.sin(X * freq_s * 2 * np.pi * w / 64 + ph[0]) * \
                np.cos(Y * freq_s * 2 * np.pi * h / 64 + ph[1]) + \
                0.5 * np.sin(X * freq_s * 1.7 * 2 * np.pi * w / 64 + ph[2]) * \
                np.sin(Y * freq_s * 0.9 * 2 * np.pi * h / 64 + ph[3])
        if octave < 3:
            fbm_coarse += amp * layer
        fbm_fine += amp * layer
        amp *= 0.5
    fbm_fine = _normalize(fbm_fine)
    fbm_coarse = _normalize(fbm_coarse)
    # Threshold to create connected pore network
    # Strut mask: where fbm > threshold (solid aerogel strut)
    strut_mask = (fbm_fine > threshold).astype(np.float32)
    # Smooth boundary between strut and pore
    strut_smooth = np.clip((fbm_fine - (threshold - 0.08)) / 0.08, 0.0, 1.0)
    # Aerogel metallic: very low everywhere (air-dominated structure)
    metallic_strut = 0.16   # 40/255 on strut (glass silica)
    metallic_pore = 0.08    # 20/255 in pore (air)
    metallic = metallic_pore + (metallic_strut - metallic_pore) * strut_smooth
    # Roughness: strut surface is smooth glass; pore walls are rough
    roughness_strut = 0.06   # G≈15/255 smooth glass strut
    roughness_pore = 0.72    # G≈183/255 rough pore walls
    roughness = roughness_pore + (roughness_strut - roughness_pore) * strut_smooth
    # Fine fractal detail on roughness
    roughness += fbm_fine * 0.08 - 0.04
    metallic = np.clip(metallic, 0.0, 1.0)
    roughness = np.clip(roughness, 0.0, 1.0)
    # Clearcoat moderate (glass struts smooth, overall moderate)
    combined = (1.0 - roughness) * 0.55 + metallic * 0.25 + strut_smooth * 0.20
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


def spec_damascus_steel_spec(shape, seed, sm, num_layers=18, warp_strength=4.5,
                              **kwargs):
    """Damascus steel surface spec overlay. Damascus (wootz) steel has a watered-silk
    pattern from folded high-carbon and low-carbon steel bands. Unlike the paint Damascus
    pattern (color), this spec overlay encodes the surface micro-topography:
    High-carbon bands (harder, polishes brighter, etches brighter): R=190/255, G=20/255.
    Low-carbon bands (softer, slightly rougher, chemical etching reveals): R=120/255, G=60/255.
    Uses flow-field distorted stripes (same approach as damascus_steel paint but targeting
    spec channels). Different from any other pattern: binary spec alternation following
    the characteristic folded-layer sinuous pattern. R=Metallic + G=Roughness."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)
    xx = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)
    # Flow-field distortion (characteristic Damascus watered-silk warp)
    # Multi-scale FBM warp field
    warp_x = np.zeros((h, w), dtype=np.float32)
    warp_y = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for freq_s in [1.5, 3.0, 6.0, 12.0]:
        ph = rng.uniform(0, 2 * np.pi, 8)
        warp_x += amp * np.sin(X * freq_s * 2 * np.pi + ph[0]) * \
                       np.cos(Y * freq_s * 2 * np.pi + ph[1])
        warp_y += amp * np.sin(X * freq_s * 2 * np.pi + ph[2]) * \
                       np.cos(Y * freq_s * 2 * np.pi + ph[3])
        amp *= 0.5
    warp_x = warp_x / (warp_x.std() + 1e-6) * warp_strength / w
    warp_y = warp_y / (warp_y.std() + 1e-6) * warp_strength * 0.3 / h
    # Distorted band coordinate
    band_coord = Y + warp_y + np.sin((X + warp_x) * 2 * np.pi * 3.0) * 0.04
    # Layer bands: sine wave along band_coord
    band_phase = band_coord * num_layers * np.pi
    # Add second harmonic for more realistic folded-steel character
    band_wave = np.sin(band_phase) + 0.3 * np.sin(band_phase * 2.0 + np.pi / 4)
    band_normalized = _normalize(band_wave)
    # High-carbon band (bright, hard): metallic=190/255, roughness=20/255
    # Low-carbon band (softer): metallic=120/255, roughness=60/255
    metallic_hi = 190.0 / 255.0
    metallic_lo = 120.0 / 255.0
    roughness_hi = 20.0 / 255.0
    roughness_lo = 60.0 / 255.0
    # Smooth sinusoidal transition between bands (not sharp step)
    t = band_normalized  # 0=low-carbon, 1=high-carbon
    metallic = metallic_lo + (metallic_hi - metallic_lo) * t
    roughness = roughness_lo + (roughness_hi - roughness_lo) * (1.0 - t)
    metallic = np.clip(metallic, 0.0, 1.0)
    roughness = np.clip(roughness, 0.0, 1.0)
    combined = metallic * 0.65 + (1.0 - roughness) * 0.35
    return _sm_scale(_normalize(combined), sm).astype(np.float32)


# ============================================================================
# PATTERN CATALOG — for programmatic access
# ============================================================================

PATTERN_CATALOG = {
    "banded_rows": banded_rows,
    "flake_scatter": flake_scatter,
    "depth_gradient": depth_gradient,
    "orange_peel_texture": orange_peel_texture,
    "wear_scuff": wear_scuff,
    "aniso_grain": aniso_grain,
    "interference_bands": interference_bands,
    "concentric_ripple": concentric_ripple,
    "hex_cells": hex_cells,
    "marble_vein": marble_vein,
    "cloud_wisps": cloud_wisps,
    "micro_sparkle": micro_sparkle,
    "panel_zones": panel_zones,
    "spiral_sweep": spiral_sweep,
    "carbon_weave": carbon_weave,
    "crackle_network": crackle_network,
    "flow_lines": flow_lines,
    "micro_facets": micro_facets,
    "moire_overlay": moire_overlay,
    "pebble_grain": pebble_grain,
    "radial_sunburst": radial_sunburst,
    "topographic_steps": topographic_steps,
    "wave_ripple": wave_ripple,
    "patina_bloom": patina_bloom,
    "electric_branches": electric_branches,
    # --- NEW PATTERNS (26-50) ---
    "voronoi_fracture": voronoi_fracture,
    "plasma_turbulence": plasma_turbulence,
    "diamond_lattice": diamond_lattice,
    "acid_etch": acid_etch,
    "galaxy_swirl": galaxy_swirl,
    "reptile_scale": reptile_scale,
    "magnetic_field": magnetic_field,
    "prismatic_shatter": prismatic_shatter,
    "neural_dendrite": neural_dendrite,
    "heat_distortion": heat_distortion,
    "rust_bloom": rust_bloom,
    "quantum_noise": quantum_noise,
    "woven_mesh": woven_mesh,
    "lava_crack": lava_crack,
    "diffraction_grating": diffraction_grating,
    "sand_dune": sand_dune,
    "circuit_trace": circuit_trace,
    "oil_slick": oil_slick,
    "meteor_impact": meteor_impact,
    "fungal_network": fungal_network,
    "gravity_well": gravity_well,
    "sonic_boom": sonic_boom,
    "crystal_growth": crystal_growth,
    "smoke_tendril": smoke_tendril,
    "fractal_discharge": fractal_discharge,
    # --- NEW PATTERNS (51-65) ---
    "diamond_dust": diamond_dust,
    "metallic_sand": metallic_sand,
    "holographic_flake": holographic_flake,
    "crystal_shimmer": crystal_shimmer,
    "stardust_fine": stardust_fine,
    "pearl_micro": pearl_micro,
    "gold_flake": gold_flake,
    "brushed_sparkle": brushed_sparkle,
    "crushed_glass": crushed_glass,
    "prismatic_dust": prismatic_dust,
    "chevron_bands": chevron_bands,
    "wave_bands": wave_bands,
    "gradient_bands": gradient_bands,
    "split_bands": split_bands,
    "diagonal_bands": diagonal_bands,
    # --- PRIORITY 2 BATCH A: Directional Brushed (66–77) ---
    "brushed_linear": brushed_linear,
    "brushed_diagonal": brushed_diagonal,
    "brushed_cross": brushed_cross,
    "brushed_radial": brushed_radial,
    "brushed_arc": brushed_arc,
    "hairline_polish": hairline_polish,
    "lathe_concentric": lathe_concentric,
    "bead_blast_uniform": bead_blast_uniform,
    "orbital_swirl": orbital_swirl,
    "buffer_swirl": buffer_swirl,
    "wire_brushed_coarse": wire_brushed_coarse,
    "hand_polished": hand_polished,
    # --- PRIORITY 2 BATCH B: Guilloché & Machined (78–89) ---
    "guilloche_barleycorn": guilloche_barleycorn,
    "guilloche_hobnail": guilloche_hobnail,
    "guilloche_waves": guilloche_waves,
    "guilloche_sunray": guilloche_sunray,
    "guilloche_moire_eng": guilloche_moire_eng,
    "jeweling_circles": jeweling_circles,
    "knurl_diamond": knurl_diamond,
    "knurl_straight": knurl_straight,
    "face_mill_bands": face_mill_bands,
    "fly_cut_arcs": fly_cut_arcs,
    "engraved_crosshatch": engraved_crosshatch,
    "edm_dimple": edm_dimple,
    # --- PRIORITY 2 BATCH D: Carbon Fiber & Industrial Weave (102-113) ---
    "spec_carbon_2x2_twill": spec_carbon_2x2_twill,
    "spec_carbon_plain_weave": spec_carbon_plain_weave,
    "spec_carbon_3k_fine": spec_carbon_3k_fine,
    "spec_carbon_forged": spec_carbon_forged,
    "spec_carbon_wet_layup": spec_carbon_wet_layup,
    "spec_kevlar_weave": spec_kevlar_weave,
    "spec_fiberglass_chopped": spec_fiberglass_chopped,
    "spec_woven_dyneema": spec_woven_dyneema,
    "spec_mesh_perforated": spec_mesh_perforated,
    "spec_expanded_metal": spec_expanded_metal,
    "spec_chainlink_fence": spec_chainlink_fence,
    "spec_ballistic_weave": spec_ballistic_weave,
    # --- PRIORITY 2 BATCH E: Clearcoat Behavior (114–123) ---
    "cc_panel_pool": cc_panel_pool,
    "cc_drip_runs": cc_drip_runs,
    "cc_fish_eye": cc_fish_eye,
    "cc_overspray_halo": cc_overspray_halo,
    "cc_edge_thin": cc_edge_thin,
    "cc_masking_edge": cc_masking_edge,
    "cc_spot_polish": cc_spot_polish,
    "cc_gloss_stripe": cc_gloss_stripe,
    "cc_wet_zone": cc_wet_zone,
    "cc_panel_fade": cc_panel_fade,
    # --- PRIORITY 2 BATCH C: Worn, Patina & Weathering (90-101) ---
    "spec_rust_bloom": spec_rust_bloom,
    "spec_patina_verdigris": spec_patina_verdigris,
    "spec_oxidized_pitting": spec_oxidized_pitting,
    "spec_heat_scale": spec_heat_scale,
    "spec_galvanic_corrosion": spec_galvanic_corrosion,
    "spec_stress_fractures": spec_stress_fractures,
    "spec_battle_scars": spec_battle_scars,
    "spec_worn_edges": spec_worn_edges,
    "spec_peeling_clear": spec_peeling_clear,
    "spec_sandblast_strip": spec_sandblast_strip,
    "spec_micro_chips": spec_micro_chips,
    "spec_aged_matte": spec_aged_matte,
    # --- PRIORITY 2 BATCH E: Geometric & Architectural (124–135) ---
    "spec_faceted_diamond": spec_faceted_diamond,
    "spec_hammered_dimple": spec_hammered_dimple,
    "spec_knurled_diamond": spec_knurled_diamond,
    "spec_knurled_straight": spec_knurled_straight,
    "spec_architectural_grid": spec_architectural_grid,
    "spec_hexagonal_tiles": spec_hexagonal_tiles,
    "spec_brick_mortar": spec_brick_mortar,
    "spec_corrugated_panel": spec_corrugated_panel,
    "spec_riveted_plate": spec_riveted_plate,
    "spec_weld_seam": spec_weld_seam,
    "spec_stamped_emboss": spec_stamped_emboss,
    "spec_cast_surface": spec_cast_surface,
    # --- PRIORITY 2 BATCH F: Natural & Organic (124-135) ---
    "spec_wood_grain_fine": spec_wood_grain_fine,
    "spec_wood_burl": spec_wood_burl,
    "spec_stone_granite": spec_stone_granite,
    "spec_stone_marble": spec_stone_marble,
    "spec_water_ripple_spec": spec_water_ripple_spec,
    "spec_coral_reef": spec_coral_reef,
    "spec_snake_scales": spec_snake_scales,
    "spec_fish_scales": spec_fish_scales,
    "spec_leaf_venation": spec_leaf_venation,
    "spec_terrain_erosion": spec_terrain_erosion,
    "spec_crystal_growth": spec_crystal_growth,
    "spec_lava_flow": spec_lava_flow,
    # --- PRIORITY 2 BATCH G: Lighting & Optical Effects (136-147) ---
    "spec_fresnel_gradient": spec_fresnel_gradient,
    "spec_caustic_light": spec_caustic_light,
    "spec_diffraction_grating": spec_diffraction_grating,
    "spec_retroreflective": spec_retroreflective,
    "spec_velvet_sheen": spec_velvet_sheen,
    "spec_sparkle_flake": spec_sparkle_flake,
    "spec_iridescent_film": spec_iridescent_film,
    "spec_anisotropic_radial": spec_anisotropic_radial,
    "spec_bokeh_scatter": spec_bokeh_scatter,
    "spec_light_leak": spec_light_leak,
    "spec_subsurface_depth": spec_subsurface_depth,
    "spec_chromatic_aberration": spec_chromatic_aberration,
    # --- PRIORITY 2 BATCH H: Surface Treatments (148-155) ---
    "spec_electroplated_chrome": spec_electroplated_chrome,
    "spec_anodized_texture": spec_anodized_texture,
    "spec_powder_coat_texture": spec_powder_coat_texture,
    "spec_thermal_spray": spec_thermal_spray,
    "spec_electroformed_texture": spec_electroformed_texture,
    "spec_pvd_coating": spec_pvd_coating,
    "spec_shot_peened": spec_shot_peened,
    "spec_laser_etched": spec_laser_etched,
    # --- PRIORITY 2 BATCH I: Specialty & Exotic (156-163) ---
    "spec_liquid_metal": spec_liquid_metal,
    "spec_chameleon_flake": spec_chameleon_flake,
    "spec_xirallic_crystal": spec_xirallic_crystal,
    "spec_holographic_foil": spec_holographic_foil,
    "spec_oil_film_thick": spec_oil_film_thick,
    "spec_magnetic_ferrofluid": spec_magnetic_ferrofluid,
    "spec_aerogel_surface": spec_aerogel_surface,
    "spec_damascus_steel_spec": spec_damascus_steel_spec,
}

# Category suggestions for which patterns work best with which finish types
PATTERN_SUGGESTIONS = {
    "metallic":     ["banded_rows", "flake_scatter", "micro_sparkle", "depth_gradient", "aniso_grain"],
    "pearl":        ["cloud_wisps", "interference_bands", "flow_lines", "banded_rows", "micro_sparkle"],
    "chrome":       ["wave_ripple", "concentric_ripple", "aniso_grain", "flow_lines", "depth_gradient"],
    "matte":        ["orange_peel_texture", "pebble_grain", "micro_facets", "cloud_wisps"],
    "satin":        ["flow_lines", "aniso_grain", "depth_gradient", "cloud_wisps"],
    "carbon":       ["carbon_weave", "hex_cells", "micro_facets"],
    "exotic":       ["interference_bands", "spiral_sweep", "moire_overlay", "electric_branches", "marble_vein"],
    "weathered":    ["wear_scuff", "crackle_network", "patina_bloom", "pebble_grain", "topographic_steps"],
    "luxury":       ["banded_rows", "depth_gradient", "cloud_wisps", "flow_lines", "micro_sparkle"],
    "sci_fi":       ["electric_branches", "hex_cells", "moire_overlay", "spiral_sweep", "concentric_ripple"],
    "racing":       ["aniso_grain", "flow_lines", "depth_gradient", "banded_rows", "micro_sparkle"],
    "gloss":        ["orange_peel_texture", "depth_gradient", "flow_lines", "micro_sparkle"],
    "candy":        ["cloud_wisps", "banded_rows", "flow_lines", "patina_bloom", "interference_bands"],
    "wrap_vinyl":   ["micro_facets", "pebble_grain", "orange_peel_texture", "carbon_weave"],
    "iridescent":   ["interference_bands", "moire_overlay", "spiral_sweep", "wave_ripple", "banded_rows"],
}
