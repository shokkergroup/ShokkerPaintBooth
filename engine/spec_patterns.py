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

def metallic_sand(shape, seed, sm, block_size=2):
    """
    Sand-like metallic particles: 2px block-quantized grid, each block gets
    an independent random brightness — slightly larger than diamond_dust.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    bs = max(1, block_size)
    ny, nx = max(1, (h + bs - 1) // bs), max(1, (w + bs - 1) // bs)
    blocks = rng.random((ny, nx)).astype(np.float32)
    # Expand blocks to full image
    yi = np.clip(np.arange(h) // bs, 0, ny - 1)
    xi = np.clip(np.arange(w) // bs, 0, nx - 1)
    result = blocks[yi[:, np.newaxis], xi[np.newaxis, :]]
    # Add per-pixel micro-variation
    result += rng.uniform(-0.08, 0.08, size=(h, w)).astype(np.float32)
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
    Smaller and denser than diamond_dust — like looking at a star-filled night sky.
    Per-pixel random with very low threshold, sub-pixel blur for soft glow.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed)
    raw = rng.random((h, w)).astype(np.float32)
    threshold = 1.0 - density
    # Variable intensity per star
    intensity = rng.uniform(0.3, 1.0, (h, w)).astype(np.float32)
    sparkle = np.where(raw > threshold, intensity, 0.04).astype(np.float32)
    sparkle = _gauss(sparkle, sigma=0.3)
    return _sm_scale(_normalize(sparkle), sm).astype(np.float32)


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
