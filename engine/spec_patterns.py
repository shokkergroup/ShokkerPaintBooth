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
    """Compress pattern toward 0.5 based on sm, clipped to [0, 1].

    2026-04-21 painter-report fix: a spec-overlay callsite was passing
    `sm > 1` (via `_sm_base = sm * base_spec_strength` with
    base_spec_strength up to 2.0). For that sm, this formula produces
    values below 0 and above 1, which then trips the
    `_validate_spec_output` [0, 1] assertion at the end of every spec
    pattern that uses `_sm_scale`. The assertion raised up through the
    compose pipeline into `preview_render`, which caught the exception
    and substituted a solid mid-gray fallback buffer — causing the
    "entire canvas turns gray" painter report when combining certain
    Foundation bases with Spec Pattern Overlays from the Mechanical /
    Race Heritage / Weather & Track / Artistic / Abstract Art
    categories.

    The clip makes the helper robust to out-of-contract sm values
    regardless of the caller. sm ∈ [0, 1] is still the intended input
    (compression factor: 0 = flatten, 1 = preserve); the clip keeps
    the output bounded when a caller exceeds that contract.
    """
    return np.clip(0.5 + (arr - 0.5) * sm, 0.0, 1.0)

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
        scales: list of sigma values (e.g. [16, 32, 64]) — higher = coarser noise
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


def _smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _shard_voronoi_spec(shape, seed, sm, target_px=16.0, min_cells=160,
                        max_cells=14000, edge_px=1.35, glint_density=0.003,
                        scratch_count=0, name="shard_voronoi"):
    """Dense broken-glass/facet topology for 2048-aware spec overlays.

    Unlike soft noise thresholds, this builds real Voronoi shards with dark
    fracture seams, per-facet reflection planes, bevel glints, hairline cracks,
    and sub-pixel chips. ``target_px`` is in final texture pixels so a 2048 car
    gets thousands of tiny pieces instead of billboard-sized blobs.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.default_rng(seed)
    area = max(1, h * w)
    n_cells = int(np.clip(area / max(float(target_px) ** 2, 4.0), min_cells, max_cells))

    margin = max(float(target_px), 4.0)
    pts_y = rng.uniform(-margin, h + margin, n_cells).astype(np.float32)
    pts_x = rng.uniform(-margin, w + margin, n_cells).astype(np.float32)
    pts = np.column_stack([pts_y.astype(np.float64), pts_x.astype(np.float64)])
    tree = cKDTree(pts)

    yy_i, xx_i = np.mgrid[0:h, 0:w]
    coords = np.column_stack([yy_i.ravel().astype(np.float64), xx_i.ravel().astype(np.float64)])
    dists, idxs = tree.query(coords, k=2, workers=-1)
    d1 = dists[:, 0].reshape(shape).astype(np.float32)
    d2 = dists[:, 1].reshape(shape).astype(np.float32)
    labels = idxs[:, 0].reshape(shape)

    yy = yy_i.astype(np.float32)
    xx = xx_i.astype(np.float32)
    angles = rng.uniform(0.0, np.pi, n_cells).astype(np.float32)
    brightness = rng.uniform(0.18, 0.92, n_cells).astype(np.float32)
    sizes = rng.uniform(max(3.0, target_px * 0.55), max(4.0, target_px * 1.45), n_cells).astype(np.float32)
    glint_offsets = rng.uniform(-0.28, 0.28, n_cells).astype(np.float32)

    lab_flat = labels.ravel()
    angle = angles[lab_flat].reshape(shape)
    c_y = pts_y[lab_flat].reshape(shape)
    c_x = pts_x[lab_flat].reshape(shape)
    size = sizes[lab_flat].reshape(shape)
    base = brightness[lab_flat].reshape(shape)
    offset = glint_offsets[lab_flat].reshape(shape) * size

    dx = xx - c_x
    dy = yy - c_y
    proj = dx * np.cos(angle) + dy * np.sin(angle)
    perp = -dx * np.sin(angle) + dy * np.cos(angle)

    plane = np.clip(0.5 + proj / np.maximum(size * 0.82, 1.0), 0.0, 1.0)
    cross_plane = np.clip(0.5 + perp / np.maximum(size * 1.20, 1.0), 0.0, 1.0)
    glint = np.exp(-((proj - offset) ** 2) / (2.0 * np.maximum(size * 0.105, 0.85) ** 2)).astype(np.float32)

    gap = d2 - d1
    crack = 1.0 - _smoothstep(edge_px, edge_px * 3.4, gap)
    bevel = np.exp(-((gap - edge_px * 3.0) ** 2) / (2.0 * max(edge_px * 1.2, 0.65) ** 2)).astype(np.float32)

    result = (
        0.42
        + (base - 0.5) * 0.52
        + (plane - 0.5) * 0.28
        + (cross_plane - 0.5) * 0.12
        + glint * 0.24
        + bevel * 0.18
        - crack * 0.56
    ).astype(np.float32)

    if scratch_count > 0:
        scratches = np.zeros(shape, dtype=np.float32)
        count = int(np.clip(scratch_count, 1, 900))
        for _ in range(count):
            length = rng.uniform(target_px * 1.4, target_px * 5.8)
            ang = rng.uniform(0.0, 2.0 * np.pi)
            cx = rng.uniform(0.0, w)
            cy = rng.uniform(0.0, h)
            x0 = int(np.clip(cx - np.cos(ang) * length * 0.5, 0, w - 1))
            y0 = int(np.clip(cy - np.sin(ang) * length * 0.5, 0, h - 1))
            x1 = int(np.clip(cx + np.cos(ang) * length * 0.5, 0, w - 1))
            y1 = int(np.clip(cy + np.sin(ang) * length * 0.5, 0, h - 1))
            val = float(rng.uniform(0.45, 1.0))
            if _CV2_OK:
                _cv2.line(scratches, (x0, y0), (x1, y1), val, thickness=1, lineType=_cv2.LINE_AA)
            else:
                steps = max(abs(x1 - x0), abs(y1 - y0), 1)
                xs = np.clip(np.linspace(x0, x1, steps + 1).astype(np.int32), 0, w - 1)
                ys = np.clip(np.linspace(y0, y1, steps + 1).astype(np.int32), 0, h - 1)
                np.maximum.at(scratches, (ys, xs), val)
        scratches = np.maximum(scratches, _gauss(scratches, sigma=0.45) * 0.55)
        result += scratches * 0.20

    if glint_density > 0:
        n_chips = int(np.clip(area * float(glint_density), 80, 90000))
        chip_y = rng.integers(0, h, n_chips)
        chip_x = rng.integers(0, w, n_chips)
        chip_v = rng.uniform(0.35, 1.0, n_chips).astype(np.float32)
        chips = np.zeros(shape, dtype=np.float32)
        np.maximum.at(chips, (chip_y, chip_x), chip_v)
        chips = np.maximum(chips, _gauss(chips, sigma=0.42) * 0.75)
        result += chips * 0.17

    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return out


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
    if sm < 0.001:
        return _flat(shape)
    return _shard_voronoi_spec(
        shape, seed + 1801, sm,
        target_px=max(5.0, float(facet_size)),
        min_cells=260,
        max_cells=22000,
        edge_px=0.75,
        glint_density=0.0022,
        scratch_count=0,
        name="micro_facets",
    )
micro_facets._spb_concept_complete = True
micro_facets.__doc__ = "Tiny random crystal facets with fracture seams and micro glints. Targets R=Metallic, G=Roughness, B=Clearcoat."


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
    if sm < 0.001:
        return _flat(shape)
    target_px = max(16.0, np.sqrt(max(shape[0] * shape[1], 1) / max(num_cells * 10.0, 1.0)))
    return _shard_voronoi_spec(
        shape, seed + 2601, sm,
        target_px=target_px,
        min_cells=max(180, int(num_cells * 4)),
        max_cells=13000,
        edge_px=max(0.8, float(edge_width)),
        glint_density=0.0012,
        scratch_count=max(12, int(num_cells * 0.9)),
        name="voronoi_fracture",
    )
voronoi_fracture._spb_concept_complete = True
voronoi_fracture.__doc__ = "Voronoi fracture: dense broken-surface cell boundaries and hairline cracks. Targets R=Metallic, G=Roughness, B=Clearcoat."


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
    if sm < 0.001:
        return _flat(shape)
    area = max(shape[0] * shape[1], 1)
    dynamic_px = np.sqrt(area / max(num_shards * 5.0, 1.0))
    return _shard_voronoi_spec(
        shape, seed + 3301, sm,
        target_px=max(12.0, min(30.0, dynamic_px)),
        min_cells=max(180, int(num_shards * 4)),
        max_cells=12000,
        edge_px=1.15,
        glint_density=0.0028,
        scratch_count=max(20, int(num_shards * 1.2)),
        name="prismatic_shatter",
    )
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
prismatic_shatter._spb_concept_complete = True
prismatic_shatter.__doc__ = "Shattered glass/prism facets. Targets R=Metallic, G=Roughness, B=Clearcoat."


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
    if sm < 0.001:
        return _flat(shape)
    return _shard_voronoi_spec(
        shape, seed + 5901, sm,
        target_px=12.0,
        min_cells=420,
        max_cells=18000,
        edge_px=0.95,
        glint_density=0.0065,
        scratch_count=max(60, int((shape[0] * shape[1]) / (96 * 96))),
        name="crushed_glass",
    )
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
crushed_glass._spb_concept_complete = True
crushed_glass.__doc__ = "Crushed glass: dense jagged shards, fracture seams, and micro-chip glints. Targets R=Metallic, G=Roughness, B=Clearcoat."


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

def split_bands(shape, seed, sm, num_pairs=12, ratio=3.0,
                thick_bright=0.85, thin_bright=0.25, warp_strength=0.04):
    """
    Racing-stripe split bands: alternating wide glossy and narrow matte bands
    with organic warp, per-band jitter, and crossfade feathering.
    ratio controls thick:thin width (3.0 = thick is 3x wider than thin).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)

    # Build band edge positions with thick/thin alternation
    total_units = num_pairs * (ratio + 1.0)
    unit_h = h / total_units
    edges = []
    y_cursor = 0.0
    for i in range(num_pairs):
        edges.append((y_cursor, y_cursor + unit_h * ratio, thick_bright + rng.uniform(-0.05, 0.05)))
        y_cursor += unit_h * ratio
        edges.append((y_cursor, y_cursor + unit_h, thin_bright + rng.uniform(-0.03, 0.03)))
        y_cursor += unit_h

    # Warp field for organic feel
    xx = np.arange(w, dtype=np.float32) / max(w, 1)
    warp = (np.sin(xx * rng.uniform(3, 10) * np.pi + rng.uniform(0, 2 * np.pi)) +
            np.sin(xx * rng.uniform(6, 14) * np.pi + rng.uniform(0, 2 * np.pi)) * 0.4
            ) * warp_strength * h
    yy = np.arange(h, dtype=np.float32)
    eff_y = yy[:, np.newaxis] + warp[np.newaxis, :]  # (h, w)

    # Per-band soft assignment with Gaussian feathering
    feather_px = max(unit_h * 0.15, 1.0)
    result = np.zeros(shape, dtype=np.float32)
    weight_sum = np.zeros(shape, dtype=np.float32)
    for y_start, y_end, val in edges:
        center = (y_start + y_end) * 0.5
        half_w = (y_end - y_start) * 0.5
        dist = np.abs(eff_y - center) - half_w
        # Inside band: dist <= 0; outside: positive
        band_w = np.exp(-np.clip(dist, 0, None) ** 2 / (2.0 * feather_px ** 2))
        band_w[dist <= 0] = 1.0
        result += band_w * val
        weight_sum += band_w
    result /= np.maximum(weight_sum, 1e-6)

    # Add subtle noise texture within bands
    noise = rng.uniform(-0.03, 0.03, size=shape).astype(np.float32)
    result = np.clip(result + noise, 0, 1)
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
    noise = multi_scale_noise(shape, [16, 32, 64], [0.5, 0.3, 0.2], seed)
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
    # Base: 4-octave noise texture (was 2-octave; too smooth/fake at full res)
    result = multi_scale_noise(shape, [4, 8, 16, 32],
                               [0.45, 0.30, 0.15, 0.10], seed) * 0.30 + 0.5
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
    fbm = multi_scale_noise(shape, [16, 32, 64, 128], [0.5, 0.25, 0.15, 0.1], seed)
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
    if sm < 0.001:
        return _flat(shape)
    area = max(shape[0] * shape[1], 1)
    dynamic_px = np.sqrt(area / max(num_cells * 4.0, 1.0))
    return _shard_voronoi_spec(
        shape, seed + 12401, sm,
        target_px=max(10.0, min(24.0, dynamic_px)),
        min_cells=max(240, int(num_cells * 3)),
        max_cells=16000,
        edge_px=0.95,
        glint_density=0.0035,
        scratch_count=0,
        name="spec_faceted_diamond",
    )
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
spec_faceted_diamond._spb_concept_complete = True
spec_faceted_diamond.__doc__ = "Faceted diamond/gem cut surface. Targets R=Metallic, G=Roughness, B=Clearcoat."


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
    if sm < 0.001:
        return _flat(shape)
    area = max(shape[0] * shape[1], 1)
    dynamic_px = np.sqrt(area / max(num_crystals * 5.0, 1.0))
    shards = _shard_voronoi_spec(
        shape, seed + 13401, sm,
        target_px=max(9.0, min(20.0, dynamic_px)),
        min_cells=max(300, int(num_crystals * 4)),
        max_cells=18000,
        edge_px=0.85,
        glint_density=0.0040,
        scratch_count=max(30, int(num_crystals * 0.7)),
        name="spec_crystal_growth",
    )
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.5
    radial = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / max(min(h, w) * 0.5, 1.0)
    angular = np.sin(np.arctan2(yy - cy, xx - cx) * 18.0 + radial * 26.0) * 0.5 + 0.5
    result = shards * 0.82 + angular * np.clip(1.0 - radial, 0, 1) * 0.18
    return _sm_scale(_normalize(result), sm).astype(np.float32)
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
spec_crystal_growth._spb_concept_complete = True
spec_crystal_growth.__doc__ = "Crystal growth/geode facets with radial crystalline glints. Targets R=Metallic, G=Roughness, B=Clearcoat."


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
# SPARKLE SYSTEM EXPANSION — 9 new sparkle spec patterns
# ============================================================================

def sparkle_rain(shape, seed, sm, density=0.008, streak_len=12):
    """Falling sparkle streaks — vertical metallic rain drops with bright heads.
    Vectorized: scatter drop heads via numpy indexing, vertical blur for streaks."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 8800)
    n_drops = min(max(50, int(h * w * density)), 40000)

    # Scatter bright drop heads onto canvas
    ys = rng.integers(0, h, n_drops)
    xs = rng.integers(0, w, n_drops)
    brights = rng.uniform(0.6, 1.0, n_drops).astype(np.float32)

    canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(canvas, (ys, xs), brights)

    # Asymmetric vertical blur for streak tails (more blur downward)
    # Apply a tall narrow kernel to simulate falling rain streaks
    if _CV2_OK:
        ksize = max(int(streak_len * 1.5) | 1, 3)
        # Create asymmetric vertical kernel (bright head, fading tail)
        kernel = np.zeros((ksize, 1), dtype=np.float32)
        half = ksize // 2
        for i in range(ksize):
            if i <= half:
                kernel[i, 0] = 1.0  # head region
            else:
                kernel[i, 0] = max(0, 1.0 - (i - half) / (ksize - half)) ** 1.5  # fading tail
        kernel /= kernel.sum()
        streaked = _cv2.filter2D(canvas, -1, kernel)
    else:
        streaked = _scipy_gaussian(canvas, sigma=(streak_len * 0.4, 0.3))

    smax = streaked.max()
    if smax > 1e-7:
        streaked /= smax

    result = 0.5 + streaked * 0.5 * sm
    return result.clip(0.0, 1.0).astype(np.float32)

def sparkle_constellation(shape, seed, sm, n_clusters=12, stars_per=60):
    """Clustered star groups with magnitude classes, connecting filaments, and
    Gaussian glow halos. Fully vectorized: all stars scattered via numpy indexing,
    single cv2.GaussianBlur pass for glow."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 8810)

    # Generate all cluster centers
    cluster_cy = rng.uniform(0.08, 0.92, n_clusters) * h
    cluster_cx = rng.uniform(0.08, 0.92, n_clusters) * w
    cluster_spread = rng.uniform(0.025, 0.07, n_clusters) * min(h, w)

    # Generate all stars for all clusters at once
    total_stars = n_clusters * stars_per
    cluster_ids = np.repeat(np.arange(n_clusters), stars_per)
    cy_all = np.repeat(cluster_cy, stars_per)
    cx_all = np.repeat(cluster_cx, stars_per)
    spread_all = np.repeat(cluster_spread, stars_per)

    sy = np.clip(rng.normal(cy_all, spread_all), 0, h - 1).astype(np.int32)
    sx = np.clip(rng.normal(cx_all, spread_all), 0, w - 1).astype(np.int32)

    # Magnitude classes: bright cores (20%), medium (50%), dim (30%)
    mag_roll = rng.uniform(0, 1, total_stars)
    intensities = np.where(mag_roll < 0.2, rng.uniform(0.85, 1.0, total_stars),
                  np.where(mag_roll < 0.7, rng.uniform(0.5, 0.8, total_stars),
                           rng.uniform(0.25, 0.5, total_stars))).astype(np.float32)

    # Scatter all stars onto canvas
    canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(canvas, (sy, sx), intensities)

    # Gaussian blur for glow halos (single pass)
    glow = _gauss(canvas, sigma=2.5)
    glow_max = glow.max()
    if glow_max > 1e-7:
        glow /= glow_max

    # Add faint connecting filaments between nearby cluster members
    filament = _gauss(canvas, sigma=max(min(h, w) * 0.012, 2.0))
    fil_max = filament.max()
    if fil_max > 1e-7:
        filament = (filament / fil_max) * 0.3

    # Composite: sharp points + glow + filaments
    combined = np.maximum(canvas * 0.8, glow * 0.6) + filament
    combined = np.clip(combined, 0, 1)
    result = 0.5 + combined * 0.5
    return _sm_scale(result, sm).astype(np.float32)

def sparkle_nebula(shape, seed, sm, density=0.006):
    """Sparkle with FBM density clouds — dense sparkle regions fade into sparse voids."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.RandomState(seed + 8820)
    cloud = multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 8821)
    cloud_norm = (cloud - cloud.min()) / (cloud.max() - cloud.min() + 1e-8)
    raw = rng.uniform(0, 1, shape).astype(np.float32)
    threshold = 1.0 - density * (0.5 + cloud_norm * 2.0)
    sparkle = np.clip((raw - threshold) / 0.02, 0, 1)
    result = 0.5 + sparkle * 0.5
    return _sm_scale(result, sm).astype(np.float32)

def sparkle_firefly(shape, seed, sm, n_flies=200, glow_radius=8):
    """Soft glowing sparkle points — like fireflies with warm Gaussian halos.
    Vectorized: scatter point intensities, single Gaussian blur for glow."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 8830)

    ys = rng.integers(0, h, n_flies)
    xs = rng.integers(0, w, n_flies)
    brights = rng.uniform(0.4, 1.0, n_flies).astype(np.float32)

    # Scatter firefly points onto canvas
    canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(canvas, (ys, xs), brights)

    # Single Gaussian blur produces soft glow halos around every point
    sigma = max(1.5, glow_radius * 0.45)
    glow = _gauss(canvas, sigma=sigma)
    gmax = glow.max()
    if gmax > 1e-7:
        glow /= gmax

    # Keep sharp cores visible through the glow
    combined = np.maximum(canvas * 0.7, glow)
    result = 0.5 + combined * 0.5
    return _sm_scale(result, sm).astype(np.float32)

def sparkle_shattered(shape, seed, sm, n_shards=600):
    if sm < 0.001:
        return _flat(shape)
    area = max(shape[0] * shape[1], 1)
    target_px = max(7.0, min(13.0, np.sqrt(area / max(n_shards * 8.0, 1.0))))
    return _shard_voronoi_spec(
        shape, seed + 8840, sm,
        target_px=target_px,
        min_cells=max(600, int(n_shards)),
        max_cells=26000,
        edge_px=0.75,
        glint_density=0.010,
        scratch_count=max(80, int(n_shards * 0.25)),
        name="sparkle_shattered",
    )
    """Shattered glass shard sparkle with Voronoi-crack boundaries and per-facet
    angle-dependent brightness. Fully vectorized: uses cKDTree for facet assignment,
    angular brightness via dot-product simulation, crack edges via gradient detection."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 8840)

    # Generate shard center points
    n_pts = min(n_shards, 2000)
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    pts = np.column_stack([pts_y, pts_x])

    # cKDTree for nearest-shard assignment
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.column_stack([yy.ravel(), xx.ravel()])
    _, labels = tree.query(coords)
    labels = labels.reshape(shape)

    # Per-shard brightness based on simulated viewing angle
    shard_angles = rng.uniform(0, np.pi, n_pts).astype(np.float32)
    shard_brightness = (np.cos(shard_angles) ** 2 * 0.6 + 0.2 +
                       rng.uniform(0, 0.2, n_pts)).astype(np.float32)
    shard_brightness = np.clip(shard_brightness, 0.15, 1.0)

    # Map per-shard brightness to image
    facet_map = shard_brightness[labels]

    # Detect crack edges via label gradient
    dy_label = np.diff(labels.astype(np.float32), axis=0, prepend=labels[:1, :].astype(np.float32))
    dx_label = np.diff(labels.astype(np.float32), axis=1, prepend=labels[:, :1].astype(np.float32))
    edge_mask = ((np.abs(dy_label) > 0.5) | (np.abs(dx_label) > 0.5)).astype(np.float32)

    # Widen crack lines slightly
    if _CV2_OK:
        edge_mask = _cv2.dilate(edge_mask, np.ones((2, 2), np.uint8), iterations=1)

    # Cracks are dark (low values), facets are bright
    result = facet_map * (1.0 - edge_mask * 0.7)

    # Add subtle noise within facets for realism
    noise = rng.uniform(-0.05, 0.05, shape).astype(np.float32)
    result = np.clip(result + noise, 0, 1)

    result = 0.5 + (result - 0.5) * 0.9
    return _sm_scale(_normalize(result), sm).astype(np.float32)
sparkle_shattered._spb_concept_complete = True
sparkle_shattered.__doc__ = "Shattered sparkle: tiny glass shard sparkle with dense fractured facets. Targets R=Metallic, G=Roughness, B=Clearcoat."

def sparkle_champagne(shape, seed, sm, density=0.02, bubble_max=4):
    """Rising champagne bubbles — round sparkle dots clustered vertically.
    Vectorized: scatter bubble centers, multi-sigma Gaussian blur for size classes."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 8850)
    n_bubbles = min(max(100, int(h * w * density)), 50000)

    # Bubble positions biased toward bottom-up rising columns
    xs = rng.integers(0, w, n_bubbles)
    # Bubbles rise: denser at bottom, sparser at top
    ys = (rng.beta(2.0, 1.2, n_bubbles) * h).astype(np.int32)
    ys = np.clip(ys, 0, h - 1)
    brights = rng.uniform(0.4, 1.0, n_bubbles).astype(np.float32)

    # Scatter bubble centers
    canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(canvas, (ys, xs), brights)

    # Multi-pass blur for different bubble sizes (small, medium, large)
    small = _gauss(canvas, sigma=max(0.8, bubble_max * 0.25))
    medium = _gauss(canvas, sigma=max(1.2, bubble_max * 0.5))
    large = _gauss(canvas, sigma=max(2.0, bubble_max * 0.8))

    # Blend size classes
    combined = small * 0.4 + medium * 0.35 + large * 0.25
    cmax = combined.max()
    if cmax > 1e-7:
        combined /= cmax

    result = 0.5 + combined * 0.5
    return _sm_scale(result, sm).astype(np.float32)

def sparkle_comet(shape, seed, sm, n_comets=80, tail_len=30):
    """Comet tail sparkle — bright head with fading directional tail streak.
    Vectorized: generate all tail pixel coordinates as arrays, scatter in one pass."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 8860)

    # Generate comet parameters
    cy = rng.integers(0, h, n_comets)
    cx = rng.integers(0, w, n_comets)
    angles = rng.uniform(0, 2 * np.pi, n_comets)
    lengths = np.maximum(5, (tail_len * rng.uniform(0.5, 1.5, n_comets)).astype(np.int32))
    brights = rng.uniform(0.6, 1.0, n_comets).astype(np.float32)
    max_len = int(lengths.max())

    # Build all tail points at once: (n_comets, max_len)
    t_steps = np.arange(max_len, dtype=np.float32)[np.newaxis, :]  # (1, max_len)
    dy = np.cos(angles)[:, np.newaxis]  # (n_comets, 1)
    dx = np.sin(angles)[:, np.newaxis]

    all_py = (cy[:, np.newaxis] + dy * t_steps).astype(np.int32)
    all_px = (cx[:, np.newaxis] + dx * t_steps).astype(np.int32)

    # Fade mask: (n_comets, max_len)
    tail_frac = t_steps / lengths[:, np.newaxis].astype(np.float32)
    fade = brights[:, np.newaxis] * np.clip(1.0 - tail_frac, 0, 1) ** 1.5

    # Valid mask: within bounds and within each comet's tail length
    valid = ((all_py >= 0) & (all_py < h) & (all_px >= 0) & (all_px < w) &
             (t_steps < lengths[:, np.newaxis]))

    # Flatten and scatter
    py_flat = all_py[valid]
    px_flat = all_px[valid]
    fade_flat = fade[valid].astype(np.float32)

    canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(canvas, (py_flat, px_flat), fade_flat)

    # Soft glow blur
    result = _gauss(canvas, sigma=0.8)
    rmax = result.max()
    if rmax > 1e-7:
        result /= rmax

    result = 0.5 + result * 0.5
    return _sm_scale(result, sm).astype(np.float32)

def sparkle_galaxy_swirl(shape, seed, sm, n_arms=3, density=0.008):
    """Spiral galaxy sparkle — logarithmic spiral arms dense with star points."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.RandomState(seed + 8870)
    y, x = np.mgrid[0:h, 0:w]
    cy, cx = h * 0.5, w * 0.5
    dy, dx = (y - cy).astype(np.float32), (x - cx).astype(np.float32)
    r = np.sqrt(dy ** 2 + dx ** 2) + 1e-8
    theta = np.arctan2(dy, dx)
    arm_val = np.zeros(shape, dtype=np.float32)
    for i in range(n_arms):
        offset = i * 2 * np.pi / n_arms
        spiral = theta - 0.4 * np.log(r / (min(h, w) * 0.1) + 1e-8) + offset
        arm_val += np.exp(-((np.sin(spiral) * r / (min(h, w) * 0.3)) ** 2) * 8)
    arm_norm = np.clip(arm_val / max(float(arm_val.max()), 1e-8), 0, 1)
    raw = rng.uniform(0, 1, shape).astype(np.float32)
    threshold = 1.0 - density * (0.3 + arm_norm * 3.0)
    sparkle = np.clip((raw - threshold) / 0.02, 0, 1)
    result = 0.5 + sparkle * 0.5
    return _sm_scale(result, sm).astype(np.float32)

def sparkle_electric_field(shape, seed, sm, density=0.01):
    """Electric field sparkle — sparkle density follows electric field lines between charges."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.RandomState(seed + 8880)
    y, x = np.mgrid[0:h, 0:w]
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    field = np.zeros(shape, dtype=np.float32)
    n_charges = rng.randint(4, 8)
    for _ in range(n_charges):
        cy, cx = rng.uniform(0.1, 0.9) * h, rng.uniform(0.1, 0.9) * w
        sign = rng.choice([-1.0, 1.0])
        r2 = (yf - cy) ** 2 + (xf - cx) ** 2 + 100
        field += sign / np.sqrt(r2)
    field_norm = (field - field.min()) / (field.max() - field.min() + 1e-8)
    grad_y = np.abs(np.diff(field_norm, axis=0, prepend=field_norm[:1, :]))
    grad_x = np.abs(np.diff(field_norm, axis=1, prepend=field_norm[:, :1]))
    intensity = np.clip((grad_y + grad_x) * 8, 0, 1)
    raw = rng.uniform(0, 1, shape).astype(np.float32)
    threshold = 1.0 - density * (0.2 + intensity * 4.0)
    sparkle = np.clip((raw - threshold) / 0.02, 0, 1)
    result = 0.5 + sparkle * 0.5
    return _sm_scale(result, sm).astype(np.float32)


# ============================================================================
# RACING & AUTOMOTIVE SPEC PATTERNS — 8 new effects (v6.2)
# ============================================================================

def tire_rubber_transfer(shape, seed, sm, streak_count=40, arc_strength=0.3):
    """Dark rubber marks from tire contact — parallel arc streaks with particulate
    roughness embedded in the rubber deposit. Realistic tire-scuff spec overlay."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9100)

    result = np.full(shape, 0.5, dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    yf = yy.astype(np.float32) / max(h, 1)
    xf = xx.astype(np.float32) / max(w, 1)

    # Rubber transfer arcs (curved streaks like tire contact patches)
    for _ in range(streak_count):
        cx = rng.uniform(0.1, 0.9)
        cy = rng.uniform(0.2, 0.8)
        angle = rng.uniform(-0.3, 0.3)
        width = rng.uniform(0.008, 0.025)
        curve = rng.uniform(-arc_strength, arc_strength)
        dx = xf - cx
        dy = yf - cy
        rotx = dx * np.cos(angle) + dy * np.sin(angle)
        roty = -dx * np.sin(angle) + dy * np.cos(angle)
        arc_y = roty - curve * rotx ** 2
        streak = np.exp(-arc_y ** 2 / (2 * width ** 2)) * np.exp(-rotx ** 2 / 0.08)
        intensity = rng.uniform(0.3, 0.8)
        result -= streak * intensity * 0.3  # rubber is dark (lowers values)

    # Particulate roughness in deposit areas
    noise = rng.uniform(-0.04, 0.04, shape).astype(np.float32)
    deposit_mask = np.clip((0.5 - result) * 5, 0, 1)
    result += noise * deposit_mask

    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def vinyl_wrap_texture(shape, seed, sm, channel_spacing=80, bubble_density=0.001):
    """Subtle vinyl wrap film texture with air-channel micro-grooves and tiny
    trapped air bubble imperfections. Cast vinyl surface character."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9110)

    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)

    # Air-release channel micro-grooves (barely visible parallel lines)
    phase = rng.uniform(0, 2 * np.pi)
    groove_y = np.sin(yy * 2 * np.pi / channel_spacing + phase) * 0.5 + 0.5
    groove_x = np.sin(xx * 2 * np.pi / (channel_spacing * 0.7) + phase * 1.3) * 0.5 + 0.5
    channels = groove_y[:, np.newaxis] * 0.6 + groove_x[np.newaxis, :] * 0.4
    channels = channels * 0.15  # very subtle

    # Vinyl surface texture (slightly different orange-peel from paint)
    # Added 4th & 5th octaves so the surface doesn't read as fake/over-smooth
    # at higher canvas resolutions where 12-px octave is barely perceptible.
    vinyl_tex = multi_scale_noise(shape, [3, 6, 12, 24, 48],
                                  [0.42, 0.26, 0.16, 0.10, 0.06], seed + 9111)
    vinyl_tex = _normalize(vinyl_tex) * 0.12

    # Trapped air bubbles (tiny bright dots)
    n_bubbles = min(max(20, int(h * w * bubble_density)), 5000)
    by = rng.integers(0, h, n_bubbles)
    bx = rng.integers(0, w, n_bubbles)
    bubble_canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(bubble_canvas, (by, bx), rng.uniform(0.5, 1.0, n_bubbles).astype(np.float32))
    bubble_canvas = _gauss(bubble_canvas, sigma=1.5)
    bmax = bubble_canvas.max()
    if bmax > 1e-7:
        bubble_canvas = (bubble_canvas / bmax) * 0.2

    result = 0.5 + channels - vinyl_tex * 0.5 + bubble_canvas
    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def paint_drip_edge(shape, seed, sm, edge_fraction=0.25, drip_count=30):
    """Thick paint/clearcoat accumulation at panel bottom edges — sag curtain
    with horizontal drip ridges. High clearcoat buildup zone."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9120)

    yy = np.arange(h, dtype=np.float32) / max(h, 1)
    xx = np.arange(w, dtype=np.float32) / max(w, 1)

    # Gravity sag gradient — thicker at bottom
    edge_start = 1.0 - edge_fraction
    sag = np.clip((yy - edge_start) / edge_fraction, 0, 1) ** 1.5
    sag_2d = sag[:, np.newaxis] * np.ones(w, dtype=np.float32)[np.newaxis, :]

    # Horizontal drip ridges (curtain lines)
    ridge_sum = np.zeros(shape, dtype=np.float32)
    for _ in range(drip_count):
        freq = rng.uniform(40, 120)
        phase = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.1, 0.4)
        ridge = np.sin(yy * 2 * np.pi * freq / h + phase) * 0.5 + 0.5
        ridge_2d = ridge[:, np.newaxis] * np.ones(w, dtype=np.float32)[np.newaxis, :]
        ridge_sum += ridge_2d * amp

    ridge_sum = _normalize(ridge_sum) * sag_2d

    # Column-wise waviness (paint doesn't sag perfectly evenly)
    col_warp = np.sin(xx * rng.uniform(4, 12) * np.pi + rng.uniform(0, 2 * np.pi))
    col_mod = 0.8 + col_warp * 0.2
    ridge_sum *= col_mod[np.newaxis, :]

    # High values = thick clearcoat buildup
    result = 0.5 + ridge_sum * 0.4
    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def racing_tape_residue(shape, seed, sm, num_strips=6, strip_width_frac=0.04):
    """Adhesive residue pattern from removed sponsor tape / racing tape.
    Rectangular boundaries with sticky rough film inside, clean paint outside."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9130)

    yy, xx = np.mgrid[0:h, 0:w]
    yf = yy.astype(np.float32) / max(h, 1)
    xf = xx.astype(np.float32) / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_strips):
        # Random rectangular tape region
        x0 = rng.uniform(0.05, 0.7)
        y0 = rng.uniform(0.05, 0.7)
        tw = rng.uniform(0.08, 0.35)
        th = rng.uniform(strip_width_frac * 0.5, strip_width_frac * 2.0)

        # Soft rectangular mask
        mx = np.clip((xf - x0) / 0.005, 0, 1) * np.clip((x0 + tw - xf) / 0.005, 0, 1)
        my = np.clip((yf - y0) / 0.005, 0, 1) * np.clip((y0 + th - yf) / 0.005, 0, 1)
        mask = mx * my

        # Residue: slightly rough, slightly less glossy (lower clearcoat)
        residue_noise = rng.uniform(-0.08, 0.08, shape).astype(np.float32)
        residue_base = rng.uniform(-0.15, -0.05)  # slightly darker/rougher
        result += mask * (residue_base + residue_noise * 0.5)

        # Raised edge where tape was (slightly brighter ridge)
        edge_y = np.exp(-((yf - y0) ** 2) / (0.002 ** 2)) + np.exp(-((yf - y0 - th) ** 2) / (0.002 ** 2))
        edge_x = np.exp(-((xf - x0) ** 2) / (0.002 ** 2)) + np.exp(-((xf - x0 - tw) ** 2) / (0.002 ** 2))
        edge = (edge_y * mx + edge_x * my) * 0.15
        result += edge

    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def sponsor_deboss(shape, seed, sm, num_logos=4, depth=0.3):
    """Pressed-in logo effect — subtle roughness change from embossed/debossed
    impressions in the clearcoat surface. Catches light at pressed edges."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9140)

    yy, xx = np.mgrid[0:h, 0:w]
    yf = yy.astype(np.float32) / max(h, 1)
    xf = xx.astype(np.float32) / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_logos):
        # Random elliptical stamp region
        cx = rng.uniform(0.15, 0.85)
        cy = rng.uniform(0.15, 0.85)
        rx = rng.uniform(0.04, 0.12)
        ry = rng.uniform(0.02, 0.06)
        angle = rng.uniform(0, np.pi)

        dx = xf - cx
        dy = yf - cy
        rotx = dx * np.cos(angle) + dy * np.sin(angle)
        roty = -dx * np.sin(angle) + dy * np.cos(angle)
        dist = (rotx / rx) ** 2 + (roty / ry) ** 2

        # Stamp interior: depressed (slightly different roughness)
        interior = np.clip(1.0 - dist, 0, 1)
        interior = interior ** 0.5  # soften edges

        # Edge highlight (catches light at pressed boundary)
        edge_ring = np.exp(-((np.sqrt(dist) - 1.0) ** 2) / 0.02)

        # Internal texture (simulated text/logo detail)
        # Bumped to 4 octaves so logo interiors have visible micro-detail
        # rather than reading as a featureless oval at high resolution.
        internal_noise = multi_scale_noise(shape, [3, 6, 12, 24],
                                           [0.45, 0.28, 0.17, 0.10],
                                           seed + 9141 + _)
        internal_detail = _normalize(internal_noise) * interior * 0.3

        result += interior * (-depth * 0.3) + edge_ring * 0.2 + internal_detail * 0.15

    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def heat_discoloration(shape, seed, sm, num_zones=5, max_radius=0.2):
    """Heat-treated metal color zones — like exhaust manifold bluing or
    weld heat-affected zones. Concentric temperature gradient bands."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9150)

    yy, xx = np.mgrid[0:h, 0:w]
    yf = yy.astype(np.float32) / max(h, 1)
    xf = xx.astype(np.float32) / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_zones):
        cx = rng.uniform(0.1, 0.9)
        cy = rng.uniform(0.1, 0.9)
        radius = rng.uniform(0.05, max_radius)

        dist = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
        norm_dist = dist / max(radius, 0.01)

        # Temperature-dependent zones (like heat coloring on steel)
        # Center = hottest (high metallic), rings outward = cooling zones
        zone1 = np.exp(-norm_dist ** 2 * 2.0)  # white-hot center
        zone2 = np.exp(-((norm_dist - 0.5) ** 2) * 8.0)  # straw yellow ring
        zone3 = np.exp(-((norm_dist - 0.8) ** 2) * 12.0)  # blue ring
        zone4 = np.exp(-((norm_dist - 1.1) ** 2) * 15.0)  # purple ring

        # Each zone affects roughness differently
        heat_val = zone1 * 0.9 + zone2 * 0.6 + zone3 * 0.35 + zone4 * 0.2
        result += heat_val * 0.25

    # Add micro-scale oxide texture
    oxide_noise = multi_scale_noise(shape, [2, 5, 10], [0.4, 0.35, 0.25], seed + 9151)
    oxide = (_normalize(oxide_noise) - 0.5) * 0.08
    result += oxide

    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def salt_spray_corrosion(shape, seed, sm, pit_density=0.015, cluster_count=15):
    """Fine salt-air corrosion pitting — coastal/marine environment surface
    degradation with clustered micro-pits and halo staining."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9160)

    # Base: slightly roughened from salt exposure
    base_noise = multi_scale_noise(shape, [8, 20, 40], [0.3, 0.4, 0.3], seed + 9161)
    base = _normalize(base_noise) * 0.15

    # Corrosion cluster zones (salt collects in certain areas)
    yf = np.arange(h, dtype=np.float32) / max(h, 1)
    xf = np.arange(w, dtype=np.float32) / max(w, 1)
    yy, xx = np.meshgrid(yf, xf, indexing='ij')
    cluster_map = np.zeros(shape, dtype=np.float32)
    for _ in range(cluster_count):
        cx = rng.uniform(0.05, 0.95)
        cy = rng.uniform(0.05, 0.95)
        sr = rng.uniform(0.03, 0.1)
        cluster_map += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sr ** 2))
    cluster_map = _normalize(cluster_map)

    # Scatter corrosion pits (denser in cluster zones)
    n_pits = min(max(200, int(h * w * pit_density)), 60000)
    py = rng.integers(0, h, n_pits)
    px = rng.integers(0, w, n_pits)
    pit_intensity = rng.uniform(0.3, 1.0, n_pits).astype(np.float32)

    # Pits are more likely to survive in cluster zones
    keep_prob = 0.2 + cluster_map[py, px] * 0.8
    keep = rng.uniform(0, 1, n_pits) < keep_prob
    py, px, pit_intensity = py[keep], px[keep], pit_intensity[keep]

    pit_canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(pit_canvas, (py, px), pit_intensity)

    # Pit halos (staining around pits)
    halo = _gauss(pit_canvas, sigma=2.5)
    hmax = halo.max()
    if hmax > 1e-7:
        halo /= hmax

    # Pits are rough (high roughness = low spec value in some channels)
    result = 0.5 - base - pit_canvas * 0.3 - halo * 0.15
    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


def track_grime(shape, seed, sm, splatter_density=0.005, buildup_zones=8):
    """Real racing dirt/rubber/oil buildup pattern — concentrated at leading
    edges and wheel wells, with splatter spray and embedded rubber particulate."""
    h, w = shape
    if sm < 0.001: return _flat(shape)
    rng = np.random.default_rng(seed + 9170)

    yf = np.arange(h, dtype=np.float32) / max(h, 1)
    xf = np.arange(w, dtype=np.float32) / max(w, 1)
    yy, xx = np.meshgrid(yf, xf, indexing='ij')

    # Grime buildup zones (heavier at front/bottom of panels)
    buildup = np.zeros(shape, dtype=np.float32)
    for _ in range(buildup_zones):
        cx = rng.uniform(0.1, 0.9)
        cy = rng.uniform(0.3, 0.95)  # bias toward bottom
        sx = rng.uniform(0.08, 0.25)
        sy = rng.uniform(0.05, 0.15)
        buildup += np.exp(-((xx - cx) ** 2 / (2 * sx ** 2) + (yy - cy) ** 2 / (2 * sy ** 2)))
    buildup = _normalize(buildup)

    # Vertical gradient: more grime lower on the panel
    gravity_bias = np.clip(yf * 1.2 - 0.1, 0, 1) ** 0.8
    buildup *= gravity_bias[:, np.newaxis] * 0.7 + 0.3

    # Splatter spray pattern (rubber/oil droplets flung by tires)
    n_splats = min(max(100, int(h * w * splatter_density)), 40000)
    sy = rng.integers(0, h, n_splats)
    sx = rng.integers(0, w, n_splats)
    splat_int = rng.uniform(0.2, 0.8, n_splats).astype(np.float32)

    splat_canvas = np.zeros(shape, dtype=np.float32)
    np.maximum.at(splat_canvas, (sy, sx), splat_int)
    splat_blur = _gauss(splat_canvas, sigma=1.8)
    smax = splat_blur.max()
    if smax > 1e-7:
        splat_blur /= smax

    # Embedded particulate texture
    grit = multi_scale_noise(shape, [2, 4, 8], [0.5, 0.3, 0.2], seed + 9171)
    grit = _normalize(grit) * buildup * 0.2

    # Grime darkens and roughens the surface
    result = 0.5 - buildup * 0.25 - splat_blur * 0.15 - grit
    result = np.clip(result, 0, 1)
    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# v6.2.x — VALIDATION HELPER + NEW SPONSOR/VINYL/RACE-WEAR/PREMIUM PATTERNS
# ============================================================================
#
# Pattern function signature (all spec patterns in this module):
#   def pattern_name(shape, seed, sm, **params) -> np.ndarray
#     - shape : (h, w) tuple   — output dimensions in pixels
#     - seed  : int            — RNG seed for reproducibility
#     - sm    : float [0..1]   — strength multiplier; sm=0 returns flat 0.5
#     - **params               — pattern-specific tuning args (see each fn)
#
# Returns: float32 (h, w) array in [0, 1]. Values are MODULATION values; the
# composer maps them onto a target spec channel (R/G/B) honoring iron rules:
#   CC (B) >= 16 always       → composer enforces post-mix
#   R >= 15 for non-chrome    → composer enforces post-mix
# Patterns themselves output normalized [0,1] modulation; the composer applies
# them to the spec channel via _sm_scale-aware blending.
# ============================================================================


def _validate_spec_output(arr, name="pattern"):
    """
    Lightweight runtime sanity check for spec pattern outputs.

    Asserts:
      - arr is a numpy ndarray
      - dtype is float32 (canonical for the spec composer)
      - shape is 2-D (h, w) — single-channel modulation map
      - finite (no NaN / inf) — would corrupt the composer's blend math
      - value range is within [0, 1] (with tiny floating-point slack)

    Use as the final line of any new pattern function:
        return _validate_spec_output(result, "my_pattern_name")

    Raises:
        AssertionError if any invariant is violated. The message includes the
        pattern name to make debugging in the spec_patterns library trivial.
    """
    assert isinstance(arr, np.ndarray), f"{name}: not an ndarray ({type(arr)})"
    assert arr.dtype == np.float32, f"{name}: expected float32, got {arr.dtype}"
    assert arr.ndim == 2, f"{name}: expected 2-D (h,w), got shape {arr.shape}"
    # Cheap finite check — uses .min/.max instead of full isfinite for speed
    amin, amax = float(arr.min()), float(arr.max())
    assert amin == amin and amax == amax, f"{name}: contains NaN"  # NaN != NaN
    assert -1e-4 <= amin <= 1.0 + 1e-4, f"{name}: min out of range ({amin})"
    assert -1e-4 <= amax <= 1.0 + 1e-4, f"{name}: max out of range ({amax})"
    return arr


# ----------------------------------------------------------------------------
# SPONSOR & VINYL (5 patterns) — vinyl_seam, decal_lift_edge,
# sponsor_emboss_v2, sticker_bubble_film, vinyl_stretched
# ----------------------------------------------------------------------------

def vinyl_seam(shape, seed, sm, num_seams=5, seam_width_frac=0.0025,
               angle_jitter=0.15, **kwargs):
    """
    Vinyl panel seam lines — long thin bright ridges where two vinyl sheets
    meet. Targets G=Roughness (the seam catches light at a sharp edge).
    A few high-contrast lines at slight angle variations, with a faint
    "halo" of slightly raised vinyl on each side from heat-gun finish.

    Params:
      num_seams          — count of seam lines across the panel.
      seam_width_frac    — seam thickness as fraction of min(h,w).
      angle_jitter       — radians; how non-horizontal each seam may be.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9300)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    seam_w = max(seam_width_frac, 1.0 / max(min(h, w), 1))

    result = np.full(shape, 0.5, dtype=np.float32)
    for _ in range(num_seams):
        y0 = rng.uniform(0.05, 0.95)
        ang = rng.uniform(-angle_jitter, angle_jitter)
        # signed distance from a (mostly horizontal) line
        d = (yf - y0) - ang * (xf - 0.5)
        # Sharp bright crest
        crest = np.exp(-(d * d) / (2.0 * seam_w * seam_w))
        # Wider faint halo (heat-gun softens edges of the vinyl on either side)
        halo = np.exp(-(d * d) / (2.0 * (seam_w * 6.0) ** 2)) * 0.18
        result += (crest * 0.45 + halo) * rng.uniform(0.85, 1.0)

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "vinyl_seam")


def decal_lift_edge(shape, seed, sm, num_decals=4, edge_softness=0.004,
                    lift_strength=0.55, **kwargs):
    """
    Sponsor/decal edges that have started lifting — bright rim around a
    rectangular sticker boundary, with a subtle interior shading that's
    slightly different from surrounding paint. Targets G=Roughness primarily
    (the lifted edge has both micro-air and adhesive halo).

    Params:
      num_decals     — number of decal regions.
      edge_softness  — fractional softness of the rectangle border feathering.
      lift_strength  — how aggressively the rim brightens vs interior.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9301)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    eps = max(edge_softness, 1.0 / max(min(h, w), 1))
    for _ in range(num_decals):
        x0 = rng.uniform(0.05, 0.55)
        y0 = rng.uniform(0.05, 0.55)
        rw = rng.uniform(0.15, 0.40)
        rh = rng.uniform(0.10, 0.30)
        # Distance to the nearest edge of the rectangle (inside positive)
        dx_in = np.minimum(xf - x0, x0 + rw - xf)
        dy_in = np.minimum(yf - y0, y0 + rh - yf)
        inside = (dx_in > 0) & (dy_in > 0)
        d_edge = np.minimum(np.abs(dx_in), np.abs(dy_in))
        rim = np.exp(-(d_edge * d_edge) / (2.0 * eps * eps))
        # Brighten only along the rectangle border (lifted adhesive ridge)
        result += rim * lift_strength * 0.25 * inside.astype(np.float32)
        # Slightly de-gloss the interior by a small amount
        result -= inside.astype(np.float32) * rng.uniform(0.02, 0.06)

    # Random micro-noise inside lifted halos (adhesive grit)
    grit = rng.uniform(-0.025, 0.025, shape).astype(np.float32)
    result += grit
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "decal_lift_edge")


def sponsor_emboss_v2(shape, seed, sm, num_logos=6, base_size=0.10,
                      relief=0.35, **kwargs):
    """
    V2 of the sponsor stamp / emboss pattern — random circular and rectangular
    logo footprints with a clear inner/outer relief edge using a signed
    distance falloff. Targets G=Roughness + B=Clearcoat (embossed boundary).

    Improves on sponsor_deboss by:
      - mixing two logo footprint shapes (circle + rounded rect)
      - using SDF-based relief for cleaner anti-aliased edges
      - subtle radial sheen across the logo face (shallow stamp impression)

    Params:
      num_logos  — total stamp count.
      base_size  — fractional radius/half-extent for logos.
      relief     — depth of the embossed boundary highlight.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9302)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    edge_w = 0.005
    for _ in range(num_logos):
        cx = rng.uniform(0.10, 0.90)
        cy = rng.uniform(0.10, 0.90)
        r = base_size * rng.uniform(0.5, 1.4)
        if rng.random() < 0.5:
            # Circular logo SDF
            d = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2) - r
        else:
            # Rounded-rectangle SDF
            rh_ = r * rng.uniform(0.55, 1.15)
            rw_ = r * rng.uniform(0.85, 1.45)
            ax = np.maximum(np.abs(xf - cx) - rw_, 0.0)
            ay = np.maximum(np.abs(yf - cy) - rh_, 0.0)
            d = np.sqrt(ax * ax + ay * ay)
            inside = ((np.abs(xf - cx) <= rw_) & (np.abs(yf - cy) <= rh_))
            d = np.where(inside, -np.minimum(rw_ - np.abs(xf - cx),
                                             rh_ - np.abs(yf - cy)), d)
        # Bright rim where |d| ~ 0; slight darkening inside
        rim = np.exp(-(d * d) / (2.0 * edge_w * edge_w)) * relief
        face = np.where(d < 0,
                        -0.06 * (1.0 - np.clip(-d / max(r, 1e-3), 0, 1)),
                        0.0)
        result += rim + face.astype(np.float32)

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "sponsor_emboss_v2")


def sticker_bubble_film(shape, seed, sm, bubble_density=0.0009,
                        max_radius=10, **kwargs):
    """
    Trapped air bubbles under sticker / vinyl film — soft circular dimples
    each with a small bright glint and a Gaussian dim halo (the trapped air
    interface). Targets G=Roughness (bubble surface is smoother than
    surrounding film, so it reads BRIGHTER in roughness inversion).

    Params:
      bubble_density — bubbles per pixel (clamped to a max).
      max_radius     — largest bubble radius in pixels.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9303)
    n = int(np.clip(h * w * bubble_density, 12, 12000))
    by = rng.integers(0, h, n)
    bx = rng.integers(0, w, n)
    radii = rng.integers(2, max(max_radius, 3) + 1, n)
    intensities = rng.uniform(0.4, 1.0, n).astype(np.float32)

    canvas = np.zeros(shape, dtype=np.float32)
    np.add.at(canvas, (by, bx), intensities)
    # Two-scale glow: tiny bright glint + larger soft halo
    glint = _gauss(canvas, sigma=1.2)
    halo = _gauss(canvas, sigma=max(2.0, max_radius * 0.5))
    g_max = max(glint.max(), 1e-7)
    h_max = max(halo.max(), 1e-7)
    bubbles = (glint / g_max) * 0.45 + (halo / h_max) * 0.30

    # Subtle non-bubble film texture so the surrounding isn't dead-flat
    film = multi_scale_noise(shape, [4, 8, 16], [0.5, 0.3, 0.2], seed + 9304)
    film = (_normalize(film) - 0.5) * 0.10

    result = 0.5 + film + bubbles
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "sticker_bubble_film")


def vinyl_stretched(shape, seed, sm, stretch_freq=18.0, stretch_amp=0.30,
                    streak_density=0.6, **kwargs):
    """
    Vinyl wrap that's been stretched over a complex curve — directional
    micro-streaks running along the stretch axis with periodic thickness
    variation as the film thinned and thickened across the contour.
    Targets G=Roughness (stretched film reads as fine grain along axis).

    Params:
      stretch_freq    — wave count of thickness ridges along the stretch axis.
      stretch_amp     — peak modulation amplitude for the ridges.
      streak_density  — strength of the high-freq grain on top of the ridges.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9305)
    angle = rng.uniform(-0.6, 0.6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Project coordinates along the (rotated) stretch axis
    u = (xx / max(w, 1)) * np.cos(angle) + (yy / max(h, 1)) * np.sin(angle)
    v = -(xx / max(w, 1)) * np.sin(angle) + (yy / max(h, 1)) * np.cos(angle)

    # Periodic ridges (thinning/thickening as film stretched)
    ridges = (np.sin(u * stretch_freq * np.pi * 2.0) * 0.5 + 0.5) * stretch_amp

    # Fine grain along the stretch axis (perpendicular = v)
    grain_seed = rng.uniform(-1, 1, size=h).astype(np.float32)
    # Reproject: grain modulated along the perpendicular axis
    grain_idx = np.clip(((v - v.min()) / max(v.max() - v.min(), 1e-6) *
                         (h - 1)).astype(np.int32), 0, h - 1)
    grain = grain_seed[grain_idx] * streak_density * 0.18

    # Thickness halo (smooth low-freq variation)
    bg = multi_scale_noise(shape, [10, 22], [0.6, 0.4], seed + 9306)
    bg = (_normalize(bg) - 0.5) * 0.10

    result = 0.5 + ridges - 0.15 + grain + bg
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "vinyl_stretched")


# ----------------------------------------------------------------------------
# RACE WEAR (5 patterns) — tire_smoke_residue, brake_dust_buildup,
# oil_streak_panel, gravel_chip_field, wax_streak_polish
# ----------------------------------------------------------------------------

def tire_smoke_residue(shape, seed, sm, num_passes=5, smoke_strength=0.45,
                       **kwargs):
    """
    Hazy tire smoke residue — soft directional smudges left after burnouts
    or hard brake events. Multiple low-frequency Gaussian-blurred ribbons
    overlaid at slight angles, generally BIASED to bottom of panel.
    Targets G=Roughness (haze raises roughness, dulls reflection).

    Params:
      num_passes      — number of overlapping smoke ribbons.
      smoke_strength  — how much the residue darkens / dulls.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9310)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.zeros(shape, dtype=np.float32)
    for _ in range(num_passes):
        cy = rng.uniform(0.45, 0.95)
        cx = rng.uniform(0.0, 1.0)
        ang = rng.uniform(-0.25, 0.25)
        wide = rng.uniform(0.10, 0.35)
        rotx = (xf - cx) * np.cos(ang) - (yf - cy) * np.sin(ang)
        roty = (xf - cx) * np.sin(ang) + (yf - cy) * np.cos(ang)
        ribbon = np.exp(-(roty * roty) / (2.0 * wide * wide))
        ribbon *= np.exp(-(rotx * rotx) / 0.18)  # finite extent along axis
        result += ribbon * rng.uniform(0.6, 1.0)

    haze = _gauss(result, sigma=4.0)
    h_max = max(haze.max(), 1e-7)
    haze /= h_max

    # Embedded micro-particulate (carbon flecks)
    grit = multi_scale_noise(shape, [1.5, 3, 6], [0.5, 0.3, 0.2], seed + 9311)
    grit = (_normalize(grit) - 0.5) * 0.08

    out = 0.5 - haze * smoke_strength + grit * haze
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(out), sm).astype(np.float32)
    return _validate_spec_output(out, "tire_smoke_residue")


def brake_dust_buildup(shape, seed, sm, vertical_bias=0.85,
                       cluster_count=20, **kwargs):
    """
    Brake-dust accumulation — fine particulate concentrated in lower regions
    and around wheel arches. Multi-scale FBM weighted by a lower-bias gradient,
    with sparse darker clusters where dust pools heaviest.
    Targets G=Roughness + B=Clearcoat (pollution dulls clearcoat).

    Params:
      vertical_bias  — how strongly dust prefers lower panel (0..1).
      cluster_count  — number of heavier dust pools.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9320)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)

    # Gravity bias — dust heavier near bottom of panel
    grav = np.clip((yf - 0.25) / 0.75, 0, 1) ** 1.6
    grav = grav * vertical_bias + (1.0 - vertical_bias) * 0.5

    fbm = multi_scale_noise(shape, [2, 5, 11, 22], [0.4, 0.3, 0.2, 0.1],
                            seed + 9321)
    fbm = _normalize(fbm)

    pools = np.zeros(shape, dtype=np.float32)
    for _ in range(cluster_count):
        cx = rng.uniform(0.05, 0.95)
        cy = rng.uniform(0.55, 0.98)  # bias to bottom
        sx = rng.uniform(0.05, 0.18)
        sy = rng.uniform(0.04, 0.12)
        pools += np.exp(-((xf - cx) ** 2 / (2 * sx ** 2) +
                          (yf - cy) ** 2 / (2 * sy ** 2)))
    pools = _normalize(pools)

    dust = fbm * grav * 0.7 + pools * grav * 0.5
    out = 0.5 - dust * 0.32
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(out), sm).astype(np.float32)
    return _validate_spec_output(out, "brake_dust_buildup")


def oil_streak_panel(shape, seed, sm, num_streaks=14, streak_len=0.45,
                     drip_chance=0.45, **kwargs):
    """
    Oil/fluid streaks running down a panel — dark vertical wet streaks with
    occasional horizontal drip pooling and a faint sheen along the streak
    axis (oil surface tension). Targets B=Clearcoat (oil glosses) +
    G=Roughness (drip edges are rougher).

    Params:
      num_streaks   — count of streaks.
      streak_len    — fractional length of an average streak.
      drip_chance   — probability per streak that a horizontal drip forms.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9330)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_streaks):
        cx = rng.uniform(0.05, 0.95)
        y0 = rng.uniform(0.0, 0.4)
        length = streak_len * rng.uniform(0.6, 1.4)
        wpx = rng.uniform(0.0035, 0.012)
        wobble = rng.uniform(0.005, 0.018)
        # Vertical streak: x ≈ cx + small wobble(y)
        wob = wobble * np.sin(yf * np.pi * rng.uniform(2.0, 6.0))
        d = (xf - cx - wob)
        # Falloff along axis (streak fades out)
        ax = np.clip((yf - y0) / max(length, 1e-3), 0, 1)
        env = np.where(ax > 1.0, 0.0,
                       np.where(ax < 0.0, 0.0,
                                1.0 - (2.0 * ax - 1.0) ** 2))
        streak = np.exp(-(d * d) / (2.0 * wpx * wpx))
        result -= streak * env * rng.uniform(0.18, 0.30)
        # Bright sheen down the centre of the streak (oil reflects)
        result += np.exp(-(d * d) / (2.0 * (wpx * 0.35) ** 2)) * env * 0.10

        # Optional horizontal drip pool at random y
        if rng.random() < drip_chance:
            yd = y0 + length * rng.uniform(0.6, 1.0)
            pw = rng.uniform(0.012, 0.030)
            ph = rng.uniform(0.004, 0.010)
            pool = np.exp(-((xf - cx) ** 2 / (2 * pw * pw) +
                            (yf - yd) ** 2 / (2 * ph * ph)))
            result -= pool * 0.18
            result += np.exp(-((xf - cx) ** 2 / (2 * (pw * 0.5) ** 2) +
                              (yf - yd) ** 2 / (2 * (ph * 0.5) ** 2))) * 0.08

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "oil_streak_panel")


def gravel_chip_field(shape, seed, sm, chip_density=0.0008,
                      bias_dir='leading', **kwargs):
    """
    Stone-chip damage field — many small irregular bright dots (exposed
    primer / metal) clustered toward a leading edge, each chip with a
    surrounding dark "halo" of disturbed clearcoat.
    Targets R=Metallic (exposed metal) + G=Roughness (rough chip + halo).

    Params:
      chip_density  — chips per pixel; clamped to a sane range.
      bias_dir      — 'leading' (top), 'lower' (bottom), or 'uniform'.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9340)
    # Density floor raised so chips are visible even at small canvas sizes
    n = int(np.clip(h * w * chip_density, 80, 8000))
    # Bias spawn distribution along Y axis
    if bias_dir == 'leading':
        ys = np.clip(rng.beta(1.4, 4.0, n), 0, 1)
    elif bias_dir == 'lower':
        ys = np.clip(rng.beta(4.0, 1.4, n), 0, 1)
    else:
        ys = rng.uniform(0, 1, n)
    xs = rng.uniform(0, 1, n)
    by = (ys * (h - 1)).astype(np.int32)
    bx = (xs * (w - 1)).astype(np.int32)

    # Chips themselves (sharp bright cores)
    chips = np.zeros(shape, dtype=np.float32)
    np.maximum.at(chips, (by, bx), rng.uniform(0.55, 1.0, n).astype(np.float32))
    chips = _gauss(chips, sigma=0.7)
    cmax = max(chips.max(), 1e-7)
    chips /= cmax

    # Surrounding darker halo (clearcoat disturbed)
    halo_seed = np.zeros(shape, dtype=np.float32)
    np.maximum.at(halo_seed, (by, bx), rng.uniform(0.6, 1.0, n).astype(np.float32))
    halo = _gauss(halo_seed, sigma=2.4)
    hmax = max(halo.max(), 1e-7)
    halo /= hmax

    result = 0.5 + chips * 0.42 - halo * 0.18
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "gravel_chip_field")


def wax_streak_polish(shape, seed, sm, n_strokes=18, stroke_width=0.012,
                      **kwargs):
    """
    Hand-polished wax streaks — irregular curved wipe arcs left by a buffing
    cloth, each arc slightly increasing local gloss (lower roughness).
    Targets B=Clearcoat (gloss) + G=Roughness (smooth zones).

    Params:
      n_strokes     — number of polish swipes.
      stroke_width  — arc thickness as a fraction of the panel.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9350)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(n_strokes):
        cx = rng.uniform(-0.2, 1.2)
        cy = rng.uniform(-0.2, 1.2)
        r = rng.uniform(0.15, 0.45)
        ang0 = rng.uniform(0, 2 * np.pi)
        ang_span = rng.uniform(0.7, 2.4)
        sw = stroke_width * rng.uniform(0.7, 1.5)

        dx = xf - cx
        dy = yf - cy
        rad = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)
        # Arc weight: only within an angular band
        ang_diff = (theta - ang0 + np.pi) % (2 * np.pi) - np.pi
        in_band = np.abs(ang_diff) < ang_span * 0.5
        radial = np.exp(-((rad - r) ** 2) / (2.0 * sw * sw))
        arc = radial * in_band.astype(np.float32)
        # Polish brightens the arc (gloss lift)
        result += arc * 0.18

    # Light pre-polish dust/swirl for realism
    dust = multi_scale_noise(shape, [3, 7], [0.6, 0.4], seed + 9351)
    result -= (1.0 - _normalize(dust)) * 0.05

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "wax_streak_polish")


# ----------------------------------------------------------------------------
# PREMIUM FINISHES (5 patterns) — mother_of_pearl_inlay, anodized_rainbow,
# frosted_glass_etch, gold_leaf_torn, copper_patina_drip
# ----------------------------------------------------------------------------

def mother_of_pearl_inlay(shape, seed, sm, num_shards=140, shimmer_freq=14.0,
                          **kwargs):
    """
    Mother-of-pearl / nacre inlay — many irregular polygon shards (Voronoi
    cells), each tinted with a per-cell phase offset of a sinusoidal
    iridescence so adjacent shards shimmer at slightly different "angles".
    Targets R=Metallic (nacre is highly reflective).

    Params:
      num_shards    — count of nacre shards (Voronoi seeds).
      shimmer_freq  — cycles of the per-cell iridescence band.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9400)
    pts = rng.random((num_shards, 2)) * np.array([h, w], dtype=np.float32)
    grid_y = np.arange(h, dtype=np.float32)
    grid_x = np.arange(w, dtype=np.float32)
    yy, xx = np.meshgrid(grid_y, grid_x, indexing='ij')
    coords = np.column_stack([yy.ravel(), xx.ravel()])
    tree = cKDTree(pts)
    _, idx = tree.query(coords, k=1)
    cell_idx = idx.reshape(shape)
    # Per-cell phase
    phases = rng.uniform(0, 2 * np.pi, num_shards).astype(np.float32)
    # Per-cell direction for the band axis
    dirs = rng.uniform(0, np.pi, num_shards).astype(np.float32)
    cdir = np.cos(dirs)[cell_idx]
    sdir = np.sin(dirs)[cell_idx]
    yn = yy / max(h, 1)
    xn = xx / max(w, 1)
    proj = yn * sdir + xn * cdir
    iridescence = 0.5 + 0.5 * np.sin(proj * shimmer_freq * np.pi * 2.0 +
                                     phases[cell_idx])

    # Slight cell-edge darkening (interface between nacre layers)
    # Approximated by distance to second-nearest neighbour
    _, idx2 = tree.query(coords, k=2)
    d_diff = np.abs(idx2[:, 0] - idx2[:, 1]).reshape(shape)  # ignored; use dist
    # Recompute distances quickly via float
    d12 = (pts[idx2[:, 0]] - pts[idx2[:, 1]])
    # NOTE: we use the squared distance from the pixel to the 2nd-nearest seed
    # minus the same to the 1st-nearest as a cheap edge proxy.
    d_a, _ = tree.query(coords, k=1)
    d_b, _ = tree.query(coords, k=2)
    edge = np.clip(1.0 - np.abs(d_b[:, 1] - d_b[:, 0]).reshape(shape) / 2.5,
                   0.0, 1.0) * 0.08

    result = iridescence * 0.85 + 0.075 - edge
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "mother_of_pearl_inlay")


def anodized_rainbow(shape, seed, sm, band_freq=10.0, axis_jitter=0.10,
                     **kwargs):
    """
    Anodized titanium / niobium rainbow bands — very smooth, low-roughness
    surface with interference banding from the oxide thickness gradient.
    Targets R=Metallic (high) and modulates the band positions via a slow
    FBM warp (oxide thickness varies organically).

    Params:
      band_freq    — number of color bands across the panel.
      axis_jitter  — strength of the FBM warp distortion.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9410)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yn = yy / max(h, 1)
    xn = xx / max(w, 1)
    angle = rng.uniform(0, 2 * np.pi)
    proj = yn * np.cos(angle) + xn * np.sin(angle)
    warp = multi_scale_noise(shape, [12, 26, 60], [0.5, 0.3, 0.2], seed + 9411)
    warp = (_normalize(warp) - 0.5) * axis_jitter
    band = 0.5 + 0.5 * np.sin((proj + warp) * band_freq * np.pi * 2.0)
    # Subtle film perturbation so adjacent bands aren't perfectly periodic
    detail = multi_scale_noise(shape, [4, 9], [0.6, 0.4], seed + 9412)
    detail = (_normalize(detail) - 0.5) * 0.07
    result = np.clip(band + detail, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(result, sm).astype(np.float32)
    return _validate_spec_output(out, "anodized_rainbow")


def frosted_glass_etch(shape, seed, sm, etch_density=2200, etch_radius=2.2,
                       base_smooth=0.18, **kwargs):
    """
    Frosted / sandblasted glass etch — dense fine random pits forming a
    diffuse haze, with gentle low-frequency variation between heavier and
    lighter etched zones. Targets G=Roughness (etched glass is rough).

    Params:
      etch_density  — number of etch points (high count for glass texture).
      etch_radius   — Gaussian sigma for each etch's spread.
      base_smooth   — strength of the low-frequency smooth field underneath.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9420)
    canvas = np.zeros(shape, dtype=np.float32)
    n = int(np.clip(etch_density, 200, 30000))
    py = rng.integers(0, h, n)
    px = rng.integers(0, w, n)
    inten = rng.uniform(0.5, 1.0, n).astype(np.float32)
    np.add.at(canvas, (py, px), inten)
    etch = _gauss(canvas, sigma=max(0.7, etch_radius * 0.5))
    em = max(etch.max(), 1e-7)
    etch /= em

    bg = multi_scale_noise(shape, [10, 24], [0.6, 0.4], seed + 9421)
    bg = _normalize(bg) * base_smooth

    result = 0.45 + etch * 0.45 + bg
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "frosted_glass_etch")


def gold_leaf_torn(shape, seed, sm, n_sheets=10, tear_jitter=0.08, **kwargs):
    """
    Torn gold-leaf application — discrete leaf sheets each with rough torn
    edges and small interior wrinkle veins, gold sections highly metallic
    while exposed substrate (gaps) stays dull. Targets R=Metallic.

    Params:
      n_sheets     — number of leaf sheets to lay down.
      tear_jitter  — irregularity of leaf borders (0.0 = clean rect).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9430)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    coverage = np.full(shape, 0.0, dtype=np.float32)

    # Per-sheet noise field used to perturb the rectangular boundary
    warp_a = multi_scale_noise(shape, [4, 8, 16], [0.5, 0.3, 0.2], seed + 9431)
    warp_a = (_normalize(warp_a) - 0.5) * tear_jitter
    warp_b = multi_scale_noise(shape, [4, 8, 16], [0.5, 0.3, 0.2], seed + 9432)
    warp_b = (_normalize(warp_b) - 0.5) * tear_jitter

    for _ in range(n_sheets):
        x0 = rng.uniform(-0.05, 0.7)
        y0 = rng.uniform(-0.05, 0.7)
        sx = rng.uniform(0.18, 0.40)
        sy = rng.uniform(0.18, 0.40)
        # Warped sheet membership: distance to sheet center, irregular border
        dx = (xf - (x0 + sx * 0.5)) + warp_a
        dy = (yf - (y0 + sy * 0.5)) + warp_b
        inside = (np.abs(dx) < sx * 0.5) & (np.abs(dy) < sy * 0.5)
        # Soft membership at the very edge
        edge_d = np.minimum(sx * 0.5 - np.abs(dx), sy * 0.5 - np.abs(dy))
        soft = np.clip(edge_d / 0.005, 0.0, 1.0) * inside
        coverage = np.maximum(coverage, soft.astype(np.float32))

    # Wrinkle veins — fine FBM seen only on covered area
    wrinkle = multi_scale_noise(shape, [2, 5, 11], [0.5, 0.3, 0.2], seed + 9433)
    wrinkle = (_normalize(wrinkle) - 0.5) * 0.18
    leaf_face = 0.85 + wrinkle  # gold is bright in metallic channel

    # Substrate (uncovered): dull, roughish
    sub = 0.30 + (rng.uniform(-0.05, 0.05, shape).astype(np.float32))

    result = coverage * leaf_face + (1.0 - coverage) * sub
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "gold_leaf_torn")


def copper_patina_drip(shape, seed, sm, num_drips=10, drip_len=0.55,
                       patina_freq=0.03, **kwargs):
    """
    Copper patina with verdigris drips — base is low-roughness metallic
    copper modulated by FBM patina blooms; on top, vertical green-runoff
    streaks where moisture pulled patina downward. Targets R=Metallic and
    G=Roughness (patina = rough; drip channels = smooth wet runs).

    Params:
      num_drips     — count of vertical patina drips.
      drip_len      — fractional length of each drip.
      patina_freq   — base patina cell frequency (lower = larger blooms).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9440)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)

    # Patina blooms — low frequency FBM, normalized
    bloom = multi_scale_noise(shape,
                              [int(1.0 / max(patina_freq, 0.005)),
                               int(2.0 / max(patina_freq, 0.005)),
                               int(4.0 / max(patina_freq, 0.005))],
                              [0.5, 0.3, 0.2], seed + 9441)
    bloom = _normalize(bloom)
    # Threshold so we get distinct patches
    patina_mask = np.clip((bloom - 0.45) * 2.4, 0.0, 1.0)

    # Drip streaks
    drips = np.zeros(shape, dtype=np.float32)
    for _ in range(num_drips):
        cx = rng.uniform(0.05, 0.95)
        y0 = rng.uniform(0.0, 0.45)
        wpx = rng.uniform(0.004, 0.011)
        length = drip_len * rng.uniform(0.6, 1.4)
        wob = 0.012 * np.sin(yf * np.pi * rng.uniform(2.0, 5.0))
        d = (xf - cx - wob)
        ax = np.clip((yf - y0) / max(length, 1e-3), 0, 1)
        env = np.where(ax > 1.0, 0.0,
                       np.where(ax < 0.0, 0.0,
                                1.0 - (2.0 * ax - 1.0) ** 2))
        drips += np.exp(-(d * d) / (2.0 * wpx * wpx)) * env

    drips = np.clip(drips, 0.0, 1.0)

    # Composite: copper bright (~0.78) - patina darken - but drips stay smooth/bright
    base = 0.78 * np.ones(shape, dtype=np.float32)
    result = base - patina_mask * 0.30 + drips * 0.20
    # Tiny granular detail
    grit = multi_scale_noise(shape, [1.5, 4], [0.6, 0.4], seed + 9442)
    grit = (_normalize(grit) - 0.5) * 0.06
    result += grit

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "copper_patina_drip")


# ----------------------------------------------------------------------------
# COLOR-SHIFT VARIANTS (5+) — palette tweaks on existing successful patterns
# ----------------------------------------------------------------------------
# These are compact wrappers that re-use the underlying base pattern with
# parameter tweaks suited to a "warm", "cool", "deep", "bright", or
# "monochrome" tonal mood. The composer then maps the [0,1] modulation to
# whatever spec channel the user chose — but the inner distribution shifts
# differently because the parameter set produces a different histogram.

def brushed_linear_warm(shape, seed, sm, frequency=72.0, **kwargs):
    """
    Warm-toned variant of brushed_linear — slightly lower frequency and
    boosted contrast give a softer, denser brushed grain that pairs well
    with warm copper / brass / gold finishes. G=Roughness target.
    """
    arr = brushed_linear(shape, seed, sm, frequency=frequency,
                         phase_noise=0.030, **kwargs)
    # Slight bias toward the darker (smoother) side — warm metals polish
    # cleaner, so the high-roughness peaks are pulled back a touch.
    out = (arr - 0.5) * 0.92 + 0.48
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return _validate_spec_output(out, "brushed_linear_warm")


def brushed_linear_cool(shape, seed, sm, frequency=92.0, **kwargs):
    """
    Cool-toned variant of brushed_linear — higher frequency and tighter phase
    noise yield a crisper, more aggressive brushed grain better suited to
    cool steel / titanium / chrome finishes. G=Roughness target.
    """
    arr = brushed_linear(shape, seed, sm, frequency=frequency,
                         phase_noise=0.012, **kwargs)
    # Slight bias toward the brighter side — cool metals show grain crisper.
    out = (arr - 0.5) * 1.06 + 0.51
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return _validate_spec_output(out, "brushed_linear_cool")


def micro_sparkle_warm(shape, seed, sm, density=0.13, **kwargs):
    """
    Warm-tinted variant of micro_sparkle — slightly fewer, softer sparkles
    that read like champagne / gold pearl rather than diamond ice. R or
    metallic-channel target depending on use.
    """
    arr = micro_sparkle(shape, seed, sm, density=density, **kwargs)
    # Lift the dark floor so sparkle sits over a warmer metallic base
    out = arr * 0.82 + 0.16
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return _validate_spec_output(out, "micro_sparkle_warm")


def micro_sparkle_cool(shape, seed, sm, density=0.18, **kwargs):
    """
    Cool-tinted variant of micro_sparkle — denser, sharper points reading
    like diamond ice / silver flake on a deep field. R or metallic-channel.
    """
    arr = micro_sparkle(shape, seed, sm, density=density, **kwargs)
    # Crush the floor (cooler metallics are darker between sparkles)
    out = (arr - 0.5) * 1.15 + 0.50
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return _validate_spec_output(out, "micro_sparkle_cool")


def cloud_wisps_warm(shape, seed, sm, num_octaves=5, **kwargs):
    """
    Warm-toned cloud_wisps variant — boosted persistence + bias toward
    higher mid-tones gives a softer, hazier pearl roll suitable for sunset
    pearls and bronze pearls. R or G channel target.
    """
    arr = cloud_wisps(shape, seed, sm, num_octaves=num_octaves,
                      persistence=0.62, **kwargs)
    out = arr * 0.80 + 0.18
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return _validate_spec_output(out, "cloud_wisps_warm")


def cloud_wisps_cool(shape, seed, sm, num_octaves=6, **kwargs):
    """
    Cool-toned cloud_wisps variant — extra octave + lower persistence gives
    a colder, sharper cloud structure that suits silver/blue/teal pearls.
    """
    arr = cloud_wisps(shape, seed, sm, num_octaves=num_octaves,
                      persistence=0.42, **kwargs)
    out = (arr - 0.5) * 1.10 + 0.50
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return _validate_spec_output(out, "cloud_wisps_cool")


def aniso_grain_deep(shape, seed, sm, **kwargs):
    """
    Deep / high-contrast variant of aniso_grain — increases grain_depth and
    pushes the histogram outward. Good for dramatic anodized or deep brushed
    looks where a subtle aniso_grain would otherwise vanish. G=Roughness.
    """
    arr = aniso_grain(shape, seed, sm, grain_depth=0.85, **kwargs)
    out = (arr - 0.5) * 1.20 + 0.50
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    return _validate_spec_output(out, "aniso_grain_deep")


# ============================================================================
# v6.2.y — RACE HERITAGE, MECHANICAL, WEATHER & TRACK, ARTISTIC (24 patterns)
# ============================================================================
#
# All functions follow the canonical signature:
#   def pattern_name(shape, seed, sm, **params) -> np.ndarray
# Return float32 (h, w) in [0, 1]. Composer maps to the appropriate channel.
# ============================================================================


# ----------------------------------------------------------------------------
# RACE HERITAGE (6 patterns)
# ----------------------------------------------------------------------------

def checker_flag_subtle(shape, seed, sm, squares=18, warp=0.006, **kwargs):
    """
    Faint large checkered-flag specular modulation — alternating light/dark
    square cells with a soft edge and a gentle low-frequency warp so the
    rows never line up perfectly. Targets R=Metallic (distinctive victory-
    lane ghost pattern without a hard graphic stamp).

    Params:
      squares  — number of squares along the shorter axis.
      warp     — low-frequency warp amplitude as a fraction of the canvas.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    # Low-frequency warp so the grid slightly wobbles
    warp_noise = multi_scale_noise(shape, [30, 60], [0.6, 0.4], seed + 9401)
    warp_noise = (_normalize(warp_noise) - 0.5) * 2.0 * warp
    u = xf + warp_noise
    v = yf + warp_noise[::-1, :]
    cx = np.floor(u * squares)
    cy = np.floor(v * squares)
    check = np.mod(cx + cy, 2).astype(np.float32)
    # Softened by blurring the hard check, then blending back toward 0.5
    soft = _gauss(check, sigma=1.2)
    out = 0.5 + (soft - 0.5) * 0.55
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(out), sm).astype(np.float32)
    return _validate_spec_output(out, "checker_flag_subtle")


def drag_strip_burnout(shape, seed, sm, num_strips=2, strip_width=0.18,
                       smoke_spread=0.25, **kwargs):
    """
    Two wide dark parallel rubber streaks down the panel as if the car just
    did a long burnout on a prepped drag strip. Hot-black rubber deposit
    with soft heat-smoke haze fading outward from each lane.
    Targets G=Roughness (rubber kills gloss) + R=Metallic (darken).

    Params:
      num_strips    — usually 2 (dual rear tires).
      strip_width   — fractional width of each rubber lane.
      smoke_spread  — how far smoke haloes spread beyond the lane.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9410)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)

    result = np.full(shape, 0.5, dtype=np.float32)
    # Space strips symmetrically around centre
    centres = np.linspace(0.32, 0.68, max(num_strips, 1))
    for cx in centres:
        cx_j = float(cx) + rng.uniform(-0.03, 0.03)
        d = np.abs(xf - cx_j)
        rubber = np.exp(-(d * d) / (2.0 * (strip_width * 0.45) ** 2))
        smoke = np.exp(-(d * d) / (2.0 * smoke_spread ** 2)) * 0.35
        # Speckle rubber unevenness along length
        length_mod = 0.75 + 0.25 * np.sin(yf * np.pi * rng.uniform(3.5, 7.5) +
                                           rng.uniform(0, 6.28))
        result -= rubber * 0.32 * length_mod
        result -= smoke * 0.12

    # Carbon grit embedded in the rubber
    grit = multi_scale_noise(shape, [1.5, 3, 6], [0.5, 0.3, 0.2], seed + 9411)
    grit = (_normalize(grit) - 0.5) * 0.10
    # Mask grit to live only where rubber lives
    rubber_mask = np.clip(0.5 - result, 0.0, 0.5) * 2.0
    result += grit * rubber_mask

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "drag_strip_burnout")


def pit_lane_stripes(shape, seed, sm, num_stripes=6, stripe_width=0.012,
                     gap=0.06, angle=0.0, **kwargs):
    """
    Clean parallel speed stripes running the length of the panel — like
    pit-lane painted stripes or speed livery tape bands. Sharp bright
    ridges with a thin dark feather to sell the tape edge.
    Targets R=Metallic (paint lane livery pop).

    Params:
      num_stripes    — count of parallel bands.
      stripe_width   — fractional width of each band.
      gap            — fractional centre-to-centre gap.
      angle          — radians of tilt (small values for near-horizontal).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    # Projected coordinate along the stripe-normal direction
    v = yf * np.cos(angle) + xf * np.sin(angle)
    # Total band height
    total = num_stripes * gap
    v0 = 0.5 - total * 0.5
    result = np.full(shape, 0.5, dtype=np.float32)
    for i in range(num_stripes):
        centre = v0 + gap * (i + 0.5)
        d = v - centre
        crest = np.exp(-(d * d) / (2.0 * stripe_width * stripe_width))
        # Thin feathered dark rim from the tape edge shadow
        feather = np.exp(-(d * d) / (2.0 * (stripe_width * 3.0) ** 2)) - crest
        result += crest * 0.38 - feather * 0.10
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "pit_lane_stripes")


def victory_lap_confetti(shape, seed, sm, density=0.0009, min_r=1.5,
                          max_r=4.5, **kwargs):
    """
    Confetti-scale scattered bright specks of all sizes, lightly clustered
    to feel like paper confetti caught on the clearcoat during a victory
    lap. Each speck is a tiny Gaussian highlight with a cooler dark rim.
    Targets R=Metallic (tiny paper highlights).

    Params:
      density   — fraction of pixels that spawn a confetti piece.
      min_r/max_r — radius range in pixels for individual pieces.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9420)
    n = int(np.clip(h * w * density, 120, 9000))
    ys = rng.integers(0, h, n)
    xs = rng.integers(0, w, n)
    intensity = rng.uniform(0.5, 1.0, n).astype(np.float32)

    bright = np.zeros(shape, dtype=np.float32)
    np.maximum.at(bright, (ys, xs), intensity)
    # Two blur passes approximate mixed-size confetti
    small = _gauss(bright, sigma=float(min_r))
    large = _gauss(bright, sigma=float(max_r))
    both = small * 0.65 + large * 0.45
    bmax = max(both.max(), 1e-7)
    both /= bmax

    # Slight cool darker rim from motion shadow
    shadow = _gauss(bright, sigma=float(max_r * 1.8)) * 0.25
    shadow /= max(shadow.max(), 1e-7)

    result = 0.5 + both * 0.38 - shadow * 0.12
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "victory_lap_confetti")


def sponsor_tape_vinyl(shape, seed, sm, num_tapes=3, tape_length=0.55,
                       tape_width=0.06, **kwargs):
    """
    Faux vinyl sponsor-tape seam strips — rectangular regions with a raised
    bright rim (hardcut tape edge) and a subtly different interior matte
    sheen. Each strip sits at a random angle across the panel.
    Targets G=Roughness (seam boundary) + B=Clearcoat (interior sheen).

    Params:
      num_tapes    — number of tape strips.
      tape_length  — fractional length along its own axis.
      tape_width   — fractional width of each strip.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9430)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_tapes):
        cx = rng.uniform(0.15, 0.85)
        cy = rng.uniform(0.15, 0.85)
        ang = rng.uniform(-0.6, 0.6)
        # Rotated local coordinates centred on (cx, cy)
        rx = (xf - cx) * np.cos(ang) - (yf - cy) * np.sin(ang)
        ry = (xf - cx) * np.sin(ang) + (yf - cy) * np.cos(ang)
        half_len = tape_length * 0.5
        half_w = tape_width * 0.5
        # Inside-the-rect mask (soft)
        inside = np.clip(1.0 - np.abs(rx) / half_len, 0, 1) * \
                 np.clip(1.0 - np.abs(ry) / half_w, 0, 1)
        inside_soft = _gauss(inside, sigma=0.8)
        # Edge rim = |grad(inside)| proxy via diff of blurs
        inside_wider = _gauss(inside, sigma=2.2)
        rim = np.clip(inside_soft - inside_wider, 0, 1)
        rmax = max(rim.max(), 1e-7)
        rim /= rmax
        # Matte interior dimming
        interior = inside_soft - rim * 0.6
        result += rim * 0.32 - interior * 0.10

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "sponsor_tape_vinyl")


def race_number_ghost(shape, seed, sm, **kwargs):
    """
    Subtle large "race number" ghost — a big circular badge with a faint
    numeral shape implied via crossed tape-like strokes and a bright rim.
    Looks like the residue of a removed competition number roundel.
    Targets B=Clearcoat (residue gloss) + G=Roughness (edge).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9440)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    cx = rng.uniform(0.35, 0.65)
    cy = rng.uniform(0.35, 0.65)
    r = rng.uniform(0.22, 0.30)
    # Radial distance
    rad = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
    disk = np.clip(1.0 - rad / r, 0, 1)
    disk_soft = _gauss(disk, sigma=2.0)
    disk_wide = _gauss(disk, sigma=8.0)
    rim = np.clip(disk_soft - disk_wide, 0, 1)
    rmax = max(rim.max(), 1e-7)
    rim /= rmax

    # Random numeral strokes — two thick lines inside the disk at angles
    strokes = np.zeros(shape, dtype=np.float32)
    for _ in range(rng.integers(2, 5)):
        ang = rng.uniform(0, np.pi)
        rx = (xf - cx) * np.cos(ang) - (yf - cy) * np.sin(ang)
        ry = (xf - cx) * np.sin(ang) + (yf - cy) * np.cos(ang)
        thick = rng.uniform(0.01, 0.02)
        stroke = np.exp(-(ry * ry) / (2.0 * thick * thick))
        # Bounded along rx
        stroke *= np.clip(1.0 - (rx * rx) / (r * r), 0, 1)
        strokes += stroke
    strokes = _normalize(strokes) * (disk > 0.05)

    result = 0.5 + rim * 0.22 + strokes * 0.12 - disk_wide * 0.04
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "race_number_ghost")


# ----------------------------------------------------------------------------
# MECHANICAL (6 patterns)
# ----------------------------------------------------------------------------

def exhaust_pipe_scorch(shape, seed, sm, num_vents=2, heat_radius=0.18,
                         **kwargs):
    """
    Heat-scorched coloration radiating from faux exhaust-tip locations —
    concentric metallic/roughness bands blend through soft soot halos.
    Vents are positioned near the bottom edge of the panel.
    Targets R=Metallic (oxide bluing) + G=Roughness (soot).

    Params:
      num_vents    — number of exhaust tips.
      heat_radius  — fractional radius of heat influence.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9510)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_vents):
        cx = rng.uniform(0.2, 0.8)
        cy = rng.uniform(0.78, 0.96)
        r = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
        # Oscillating temperature bands (straw → blue → purple)
        bands = 0.5 + 0.5 * np.cos(r / max(heat_radius, 1e-3) * np.pi * 4.0)
        bands *= np.exp(-r / max(heat_radius, 1e-3))
        # Soot halo
        soot = np.exp(-(r * r) / (2.0 * (heat_radius * 1.6) ** 2)) * 0.25
        result += bands * 0.28 - soot * 0.18

    # Micro oxide micro-texture bound to hot zones only
    noise = multi_scale_noise(shape, [2, 4], [0.6, 0.4], seed + 9511)
    noise = (_normalize(noise) - 0.5) * 0.10
    result += noise * np.clip(result - 0.5, 0, 1) * 2.0
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "exhaust_pipe_scorch")


def radiator_grille_mesh(shape, seed, sm, cell=8, hole_frac=0.55, **kwargs):
    """
    Fine perforated grille mesh overlay — dense regular circular holes
    with a polished metallic rim around each hole and a slightly recessed
    dark interior. Distinct from mesh_perforated via finer cells and a
    cross-brace shadow halo.
    Targets R=Metallic + G=Roughness.

    Params:
      cell       — grid cell size in pixels.
      hole_frac  — fraction of each cell occupied by a hole.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Local cell coordinates
    cy = np.mod(yy, cell) - cell * 0.5
    cx = np.mod(xx, cell) - cell * 0.5
    r = np.sqrt(cx * cx + cy * cy)
    hole_r = cell * 0.5 * hole_frac
    # Hole interior = dark; rim = bright; matrix = mid
    hole_mask = np.clip(1.0 - r / max(hole_r, 1e-3), 0, 1)
    rim = np.exp(-((r - hole_r) ** 2) / (2.0 * (cell * 0.08) ** 2))
    # Cross-brace shadow band every few cells
    brace = np.where((np.mod(yy, cell * 3) < 1.0) |
                     (np.mod(xx, cell * 3) < 1.0), 1.0, 0.0).astype(np.float32)
    brace = _gauss(brace, sigma=0.9) * 0.14

    result = 0.5 + rim * 0.32 - hole_mask * 0.24 - brace
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "radiator_grille_mesh")


def engine_bay_grime(shape, seed, sm, buildup=0.55, **kwargs):
    """
    Concentrated lower-panel engine-bay grime — oily dust, fingerprints,
    and residual splatter pooled in the bottom 40%. Darker, rougher,
    with embedded speckle.
    Targets G=Roughness + B=Clearcoat.

    Params:
      buildup  — overall darken/dull intensity (0..1).
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    # Strong gravity bias
    grav = np.clip((yf - 0.45) / 0.55, 0, 1) ** 1.8
    fbm = multi_scale_noise(shape, [3, 7, 14], [0.45, 0.35, 0.2], seed + 9521)
    fbm = _normalize(fbm)
    pools = multi_scale_noise(shape, [14, 28], [0.6, 0.4], seed + 9522)
    pools = _normalize(pools) ** 2.2
    # Speckle of small oily dots
    rng = np.random.default_rng(seed + 9523)
    dots = (rng.random(shape) < 0.003).astype(np.float32)
    dots = _gauss(dots, sigma=1.1)
    dmax = max(dots.max(), 1e-7)
    dots /= dmax

    grime = (fbm * 0.5 + pools * 0.5) * grav + dots * 0.25 * grav
    out = 0.5 - grime * buildup * 0.42
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(out), sm).astype(np.float32)
    return _validate_spec_output(out, "engine_bay_grime")


def tire_smoke_streaks(shape, seed, sm, num_streaks=14, taper=0.35, **kwargs):
    """
    Whispy horizontal tire-smoke streaks — long thin sinuous bright/dark
    ribbons that thin out at each end. Different from tire_smoke_residue
    (hazy smudges) — these are elongated motion-trails like a moving car.
    Targets G=Roughness.

    Params:
      num_streaks  — number of streaks.
      taper        — fraction of streak length that fades at each tip.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9530)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)
    for _ in range(num_streaks):
        cy = rng.uniform(0.1, 0.9)
        wob_freq = rng.uniform(1.5, 4.5)
        wob_amp = rng.uniform(0.005, 0.025)
        y_line = cy + wob_amp * np.sin(xf * np.pi * wob_freq + rng.uniform(0, 6.28))
        thickness = rng.uniform(0.003, 0.011)
        d = yf - y_line
        streak = np.exp(-(d * d) / (2.0 * thickness * thickness))
        # Length envelope (fade tips)
        env = np.clip(1.0 - ((xf - 0.5) ** 2) / (0.5 - taper * 0.3) ** 2, 0, 1)
        tint = rng.choice([-1.0, 1.0]) * rng.uniform(0.12, 0.22)
        result += streak * env * tint
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "tire_smoke_streaks")


def undercarriage_spray(shape, seed, sm, spray_density=0.0025,
                         fan_height=0.55, **kwargs):
    """
    Bottom-up road-spray pattern — a fan of fine specks shot upward from
    the bottom edge, thinning with height. Organic, unmasked peppering of
    small bright/dark motes. Targets G=Roughness.

    Params:
      spray_density  — specks per pixel.
      fan_height     — fractional height the spray reaches.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9540)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    n = int(np.clip(h * w * spray_density, 200, 20000))
    # Density falls off quadratically with height from bottom
    ys = 1.0 - rng.beta(1.2, 3.5, n) * fan_height
    xs = rng.uniform(0, 1, n)
    by = np.clip((ys * (h - 1)).astype(np.int32), 0, h - 1)
    bx = np.clip((xs * (w - 1)).astype(np.int32), 0, w - 1)
    sign = rng.choice([-1.0, 1.0], n).astype(np.float32)
    amp = rng.uniform(0.25, 0.9, n).astype(np.float32) * sign
    dots = np.zeros(shape, dtype=np.float32)
    # Use add.at so overlapping specks stack to denser pools
    np.add.at(dots, (by, bx), amp)
    dots = _gauss(dots, sigma=1.2)
    # Normalize symmetric signed output around 0
    adots = dots / max(np.abs(dots).max(), 1e-7)
    # Reinforce bottom-up gravity weight for visibility
    grav = np.clip((yf - 0.35) / 0.65, 0, 1) ** 1.4
    result = 0.5 + adots * 0.35 * grav
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "undercarriage_spray")


def suspension_rust_ring(shape, seed, sm, num_rings=5, ring_spread=0.18,
                          **kwargs):
    """
    Concentric rust rings around suspension fixtures — bolt heads, bushing
    caps — with radial corrosion falling off with distance. Each fixture
    sits at a random panel location with 3-5 stepped rust bands.
    Targets G=Roughness + R=Metallic.

    Params:
      num_rings    — fixture count.
      ring_spread  — fractional radius of rust ring influence.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9550)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(num_rings):
        cx = rng.uniform(0.1, 0.9)
        cy = rng.uniform(0.1, 0.9)
        r = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
        # Bolt head metallic disk at centre
        head = np.exp(-(r * r) / (2.0 * 0.012 ** 2))
        # Concentric stepped rust bands
        stepped = np.cos(r / max(ring_spread, 1e-3) * np.pi * 3.5) * 0.5 + 0.5
        envelope = np.exp(-(r * r) / (2.0 * ring_spread ** 2))
        result += head * 0.35 - (stepped * envelope) * 0.22
    # FBM micro-corrosion flavour
    fbm = multi_scale_noise(shape, [2, 5, 10], [0.5, 0.3, 0.2], seed + 9551)
    fbm = (_normalize(fbm) - 0.5) * 0.08
    result += fbm
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "suspension_rust_ring")


# ----------------------------------------------------------------------------
# WEATHER & TRACK (6 patterns)
# ----------------------------------------------------------------------------

def rain_droplet_beads(shape, seed, sm, density=0.0015, min_r=2.5,
                        max_r=6.5, **kwargs):
    """
    Individual rain droplet beads — round wet highlights with a dark
    bottom crescent (gravity-sagged water) and a tiny bright glint.
    Completely different from wet-track haze: these are discrete drops.
    Targets B=Clearcoat (beads are glossy) + G=Roughness (edge).

    Params:
      density     — beads per pixel.
      min_r/max_r — bead radius range in pixels.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9610)
    n = int(np.clip(h * w * density, 120, 7000))
    ys = rng.integers(0, h, n)
    xs = rng.integers(0, w, n)
    amp = rng.uniform(0.6, 1.0, n).astype(np.float32)
    seeds = np.zeros(shape, dtype=np.float32)
    np.maximum.at(seeds, (ys, xs), amp)
    small = _gauss(seeds, sigma=float(min_r))
    large = _gauss(seeds, sigma=float(max_r))
    bead_body = large * 0.8 + small * 0.4
    bmax = max(bead_body.max(), 1e-7)
    bead_body /= bmax

    # Gravity sag: shift seeds down a few pixels for a darker crescent
    sag_seeds = np.zeros(shape, dtype=np.float32)
    sag_y = np.clip(ys + int(max_r * 0.8), 0, h - 1)
    np.maximum.at(sag_seeds, (sag_y, xs), amp)
    sag = _gauss(sag_seeds, sigma=float(max_r * 0.8))
    smax = max(sag.max(), 1e-7)
    sag /= smax

    # Glint (tiny sharp bright peak) — unshifted seeds blurred small
    glint = _gauss(seeds, sigma=float(min_r * 0.35))
    gmax = max(glint.max(), 1e-7)
    glint /= gmax

    result = 0.5 + bead_body * 0.28 + glint * 0.35 - sag * 0.18
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "rain_droplet_beads")


def mud_splatter_random(shape, seed, sm, num_splats=60, splat_size=0.04,
                         **kwargs):
    """
    Organic mud splatter — irregular dark blobs with radiating thin spokes
    (impact drip trails). Sizes vary widely so clusters look randomly
    flung. Targets G=Roughness + B=Clearcoat.

    Params:
      num_splats  — number of individual splat impacts.
      splat_size  — average fractional radius of each splat.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9620)
    result = np.full(shape, 0.5, dtype=np.float32)
    mn = float(min(h, w))

    # Cap splat tile reach in pixels so a single large splat doesn't blow up
    max_tile_px = int(0.18 * mn)
    for _ in range(num_splats):
        cx = rng.uniform(0.02, 0.98)
        cy = rng.uniform(0.02, 0.98)
        s_f = splat_size * rng.uniform(0.35, 2.4)
        # Work inside a local window sized to the splat + its spokes
        tile_r_f = s_f * 5.2  # enough to contain ~4.5x spokes
        cx_px, cy_px = int(cx * w), int(cy * h)
        tile_r = min(int(tile_r_f * mn) + 2, max_tile_px)
        x0 = max(0, cx_px - tile_r); x1 = min(w, cx_px + tile_r + 1)
        y0 = max(0, cy_px - tile_r); y1 = min(h, cy_px + tile_r + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1)
        txf = txx / max(w, 1)
        dx = txf - cx; dy = tyf - cy
        # Core blob with FBM-warped boundary
        ang = np.arctan2(dy, dx)
        r = np.sqrt(dx * dx + dy * dy)
        edge_wob = 1.0 + 0.25 * np.sin(ang * rng.uniform(3, 9) +
                                        rng.uniform(0, 6.28))
        blob = np.clip(1.0 - r / (s_f * edge_wob + 1e-4), 0, 1) ** 1.5
        result[y0:y1, x0:x1] -= blob * 0.30
        # Radiating spokes (drip trails)
        if rng.random() < 0.45:
            n_spokes = int(rng.integers(3, 7))
            spoke_angles = rng.uniform(0, 6.28, n_spokes)
            for sa in spoke_angles:
                rx = dx * np.cos(sa) + dy * np.sin(sa)
                ry = -dx * np.sin(sa) + dy * np.cos(sa)
                length = s_f * rng.uniform(2.0, 4.5)
                width = s_f * 0.15
                spoke = np.exp(-(ry * ry) / (2.0 * width * width))
                spoke *= np.clip(rx / length, 0, 1)
                spoke *= np.clip(1.0 - rx / length, 0, 1)
                result[y0:y1, x0:x1] -= spoke * 0.10

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "mud_splatter_random")


def wet_track_gloss(shape, seed, sm, pool_scale=0.38, num_pools=8, **kwargs):
    """
    Wet clearcoat pooling — broad glossy pools with a bright film-shine
    and FBM-shaped boundaries, like rain collected on polished paint.
    Different from cc_panel_pool (those are micro-pools) — these are large
    macro-film areas. Targets B=Clearcoat.

    Params:
      pool_scale  — gives pool softness / blur.
      num_pools   — count of wet regions.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9630)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    pools = np.zeros(shape, dtype=np.float32)
    for _ in range(num_pools):
        cx = rng.uniform(0.1, 0.9)
        cy = rng.uniform(0.1, 0.9)
        sx = rng.uniform(0.10, 0.25)
        sy = rng.uniform(0.06, 0.18)
        pools += np.exp(-((xf - cx) ** 2 / (2 * sx * sx) +
                           (yf - cy) ** 2 / (2 * sy * sy)))
    # FBM boundary perturbation
    warp = multi_scale_noise(shape, [20, 40], [0.6, 0.4], seed + 9631)
    warp = _normalize(warp)
    pools = pools * (0.6 + 0.6 * warp)
    pools = _normalize(pools)
    # Glossy film reflection streaks
    film = 0.5 + 0.5 * np.cos(yf * np.pi * 4.5 + warp * 2.0)
    out = 0.5 + pools * 0.30 + film * pools * 0.12
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(out), sm).astype(np.float32)
    return _validate_spec_output(out, "wet_track_gloss")


def dry_dust_film(shape, seed, sm, film_strength=0.22, grain_scale=2.0,
                   **kwargs):
    """
    Whole-panel fine dry-dust film — a soft low-frequency haze with a
    very fine grain on top. Uniformly covers the surface without any
    specific clustering. Targets G=Roughness + B=Clearcoat (dulled gloss).

    Params:
      film_strength  — overall haze intensity.
      grain_scale    — pixel scale of dust grains.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    # Soft low-frequency variance
    macro = multi_scale_noise(shape, [40, 80], [0.6, 0.4], seed + 9640)
    macro = _normalize(macro)
    # Very fine grain
    rng = np.random.default_rng(seed + 9641)
    micro = rng.random(shape).astype(np.float32)
    micro = _gauss(micro, sigma=float(grain_scale))
    micro = _normalize(micro)
    # Combine — subtract below 0.5 to dull the surface
    dust = macro * 0.7 + micro * 0.3
    out = 0.5 - (dust - 0.5) * film_strength
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(out), sm).astype(np.float32)
    return _validate_spec_output(out, "dry_dust_film")


def morning_dew_fog(shape, seed, sm, fog_density=0.55, **kwargs):
    """
    Cold-morning dew fog — very soft misted surface with a subtle vertical
    wash and gentle low-frequency variation. Gentler and more uniform than
    dry_dust_film. Targets B=Clearcoat (damp, glossy haze).

    Params:
      fog_density  — overall fogging strength.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    # Soft low-freq fog field
    fog = multi_scale_noise(shape, [60, 120], [0.55, 0.45], seed + 9650)
    fog = _normalize(fog)
    # Top-of-panel bias (fog settles high then dissipates)
    bias = np.exp(-((yf - 0.30) ** 2) / (2.0 * 0.25 ** 2))
    # Add very faint tiny dewlet bumps
    rng = np.random.default_rng(seed + 9651)
    dewlets_seed = (rng.random(shape) < 0.0006).astype(np.float32)
    dewlets = _gauss(dewlets_seed, sigma=1.8)
    dewlets_max = max(dewlets.max(), 1e-7)
    dewlets /= dewlets_max

    result = 0.5 + (fog - 0.5) * 0.25 * bias * fog_density + dewlets * 0.12
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "morning_dew_fog")


def tarmac_grit_embed(shape, seed, sm, grit_density=0.005, **kwargs):
    """
    Embedded tarmac grit — tiny sharp asphalt grains pressed into the
    clearcoat, visible as dark-cored bright-rim specks at various sizes.
    Targets R=Metallic + G=Roughness.

    Params:
      grit_density  — grit grains per pixel.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9660)
    n = int(np.clip(h * w * grit_density, 250, 18000))
    ys = rng.integers(0, h, n)
    xs = rng.integers(0, w, n)
    amp = rng.uniform(0.45, 1.0, n).astype(np.float32)

    # Dark cores
    cores = np.zeros(shape, dtype=np.float32)
    np.maximum.at(cores, (ys, xs), amp)
    cores_b = _gauss(cores, sigma=0.6)
    cores_b /= max(cores_b.max(), 1e-7)

    # Bright rims (slightly larger blur minus core)
    rims = _gauss(cores, sigma=1.8)
    rims /= max(rims.max(), 1e-7)
    rim_only = np.clip(rims - cores_b, 0, 1)

    # Very low-frequency dark wash so it reads as embedded rather than floating
    wash = multi_scale_noise(shape, [12, 24], [0.5, 0.5], seed + 9661)
    wash = _normalize(wash) - 0.5

    result = 0.5 - cores_b * 0.30 + rim_only * 0.35 + wash * 0.05
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "tarmac_grit_embed")


# ----------------------------------------------------------------------------
# ARTISTIC (6 patterns)
# ----------------------------------------------------------------------------

def brushstroke_bold(shape, seed, sm, n_strokes=14, stroke_width=0.022,
                      **kwargs):
    """
    Painterly bold brush strokes — elongated curved streaks with a clear
    directional grain inside each stroke, as if painted by hand.
    Targets R=Metallic (brush catches light).

    Params:
      n_strokes     — count of brush strokes.
      stroke_width  — fractional stroke width.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9710)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(n_strokes):
        x0 = rng.uniform(-0.1, 0.8)
        y0 = rng.uniform(0.05, 0.95)
        length = rng.uniform(0.25, 0.55)
        ang = rng.uniform(-0.5, 0.5)
        bow = rng.uniform(-0.12, 0.12)
        # Parameterised along stroke length
        t = np.clip((xf - x0) / length, 0, 1)
        # Stroke centreline y(t) with gentle bow
        yline = y0 + ang * (xf - x0) + bow * np.sin(t * np.pi)
        d = yf - yline
        env = np.clip(np.where(t > 0, t, 0) * np.where(t < 1, 1 - t, 0) * 4.0,
                       0, 1)
        crest = np.exp(-(d * d) / (2.0 * stroke_width * stroke_width))
        # Bristle grain inside stroke
        bristles = 0.5 + 0.5 * np.cos((d / stroke_width) *
                                        rng.uniform(6, 14))
        result += crest * env * 0.30 * (0.6 + 0.4 * bristles)
        # Slight dark trailing edge
        trail = np.exp(-(d * d) / (2.0 * (stroke_width * 2.2) ** 2)) - crest
        result -= np.clip(trail, 0, 1) * env * 0.08

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "brushstroke_bold")


def crayon_wax_resist(shape, seed, sm, rub_density=0.35, streak_len=0.12,
                       **kwargs):
    """
    Wax-crayon rubbing texture — short parallel streaks of soft matte
    wax wash, with low-frequency large zones of heavier/lighter buildup.
    Targets G=Roughness.

    Params:
      rub_density  — density of short rub strokes.
      streak_len   — fractional length of a single rub stroke.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9720)
    n_strokes = int(max(20, rub_density * h * w * 4e-5))
    # Cap stroke count so 4k canvases don't explode
    n_strokes = min(n_strokes, 6000)
    strokes = np.zeros(shape, dtype=np.float32)
    mn = float(min(h, w))
    for _ in range(n_strokes):
        cx = rng.uniform(0.0, 1.0)
        cy = rng.uniform(0.0, 1.0)
        ang = rng.normal(0.25, 0.25)  # mostly near-horizontal
        half_L = streak_len * 0.5 * rng.uniform(0.5, 1.5)
        thick = rng.uniform(0.0015, 0.004)
        # Local tile to contain the stroke (axis-aligned bounding box)
        cs, sn = np.cos(ang), np.sin(ang)
        rx_reach = abs(half_L * cs) + abs(thick * 3.5 * sn)
        ry_reach = abs(half_L * sn) + abs(thick * 3.5 * cs)
        tile_rx = int(rx_reach * w) + 2
        tile_ry = int(ry_reach * h) + 2
        cx_px, cy_px = int(cx * w), int(cy * h)
        x0 = max(0, cx_px - tile_rx); x1 = min(w, cx_px + tile_rx + 1)
        y0 = max(0, cy_px - tile_ry); y1 = min(h, cy_px + tile_ry + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1); txf = txx / max(w, 1)
        dx = txf - cx; dy = tyf - cy
        rx = dx * cs + dy * sn
        ry = -dx * sn + dy * cs
        stroke = np.exp(-(ry * ry) / (2.0 * thick * thick))
        stroke *= np.clip(1.0 - (rx * rx) / (half_L * half_L), 0, 1)
        strokes[y0:y1, x0:x1] += stroke * float(rng.uniform(0.6, 1.0))
    smax = max(strokes.max(), 1e-7)
    strokes /= smax

    # Macro zones of heavier/lighter buildup
    zones = multi_scale_noise(shape, [40, 80], [0.6, 0.4], seed + 9721)
    zones = _normalize(zones)

    result = 0.5 + strokes * 0.28 * (0.5 + zones * 0.8) - \
             (1.0 - zones) * 0.08
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "crayon_wax_resist")


def airbrush_gradient_bloom(shape, seed, sm, num_blooms=5, bloom_radius=0.30,
                              **kwargs):
    """
    Soft airbrush-style gradient blooms — several smooth radial gradients
    overlaid so highlights blend feather-soft without any hard edges.
    Targets R=Metallic.

    Params:
      num_blooms    — number of bloom centres.
      bloom_radius  — fractional bloom radius.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9730)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)
    for _ in range(num_blooms):
        cx = rng.uniform(0.15, 0.85)
        cy = rng.uniform(0.15, 0.85)
        rad = bloom_radius * rng.uniform(0.55, 1.4)
        r = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
        sign = rng.choice([1.0, -1.0])
        bloom = np.exp(-(r * r) / (2.0 * (rad * 0.5) ** 2))
        result += sign * bloom * 0.18
    # Very soft global blur to seal any edges
    result = _gauss(result, sigma=2.4)
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "airbrush_gradient_bloom")


def spray_paint_drip(shape, seed, sm, num_drips=9, drip_len=0.40, **kwargs):
    """
    Spray-tagger paint drips — individual vertical drip tears with a
    bright speckled top (spray hit) and a thinning drool running down.
    More aggressive/graphic than oil_streak_panel. Targets B=Clearcoat
    + G=Roughness.

    Params:
      num_drips  — number of drip tears.
      drip_len   — fractional length of each drip.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9740)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1)
    xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)
    for _ in range(num_drips):
        cx = rng.uniform(0.05, 0.95)
        y0 = rng.uniform(0.0, 0.35)
        L = drip_len * rng.uniform(0.6, 1.4)
        w_top = rng.uniform(0.010, 0.022)
        t = np.clip((yf - y0) / max(L, 1e-3), 0, 1)
        # Taper width down the drip
        w_t = w_top * (1.0 - 0.7 * t) + 0.001
        d = xf - cx
        drip = np.exp(-(d * d) / (2.0 * w_t * w_t))
        env = np.where(t > 1.0, 0.0, np.where(t < 0.0, 0.0, 1.0))
        # Bright spray hit near top (gaussian head)
        head = np.exp(-((yf - y0) ** 2) / (2.0 * 0.012 ** 2))
        spray_fan = np.exp(-(d * d) / (2.0 * 0.02 ** 2)) * head
        result += spray_fan * 0.22
        result += drip * env * 0.24
        # Thin bright centerline of wet drip
        result += np.exp(-(d * d) / (2.0 * (w_t * 0.3) ** 2)) * env * 0.10
    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "spray_paint_drip")


def stippled_dots_fine(shape, seed, sm, dot_density=0.04, dot_radius=1.2,
                         **kwargs):
    """
    Dense fine stippled dot pointillism — very many small uniform bright
    dots filling the panel. Targets R=Metallic.

    Params:
      dot_density  — dots per pixel.
      dot_radius   — blur sigma for each dot.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 9750)
    seeds = (rng.random(shape) < dot_density).astype(np.float32)
    # Each dot amplitude jitters slightly
    jitter = rng.uniform(0.6, 1.0, shape).astype(np.float32)
    seeds *= jitter
    dots = _gauss(seeds, sigma=float(dot_radius))
    dots /= max(dots.max(), 1e-7)
    # Very subtle dark background for contrast balance
    dark_wash = multi_scale_noise(shape, [20, 40], [0.5, 0.5], seed + 9751)
    dark_wash = (_normalize(dark_wash) - 0.5) * 0.06
    result = 0.5 + dots * 0.35 + dark_wash
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "stippled_dots_fine")


def halftone_print(shape, seed, sm, cell=12, dot_max=0.45, **kwargs):
    """
    Halftone print dot pattern — regular grid of circular dots whose
    radius is modulated by a low-frequency FBM (tonal map). Classic
    pop-art / comic-book halftone look. Targets R=Metallic.

    Params:
      cell     — halftone grid cell size in pixels.
      dot_max  — maximum dot radius as fraction of cell size.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Build tonal modulation field
    tone = multi_scale_noise(shape, [30, 60], [0.6, 0.4], seed + 9760)
    tone = _normalize(tone)
    # Cell coordinates (centre-of-cell distance)
    cy = np.mod(yy, cell) - cell * 0.5
    cx = np.mod(xx, cell) - cell * 0.5
    r = np.sqrt(cx * cx + cy * cy)
    # Per-cell target radius = dot_max * cell * tone(cell)
    target_r = (dot_max * cell) * tone
    # Soft inside-dot mask
    dot = np.clip(1.0 - (r - target_r) / 1.2, 0, 1)
    # Slight blur to anti-alias
    dot = _gauss(dot, sigma=0.6)
    dot = _normalize(dot)
    result = 0.5 + (dot - 0.5) * 0.55
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "halftone_print")


# ----------------------------------------------------------------------------
# ABSTRACT ART (17 patterns) — art-history-inspired spec overlays.
#   expressionist_splatter, cubist_facets, rothko_field, kandinsky_shapes,
#   mondrian_grid, op_art_circles, op_art_waves, suprematism, futurist_motion,
#   minimalist_stripe, hard_edge_field, color_field_bleed, fluid_acrylic_pour,
#   ink_wash_gradient, neon_glitch, retro_wave, bauhaus_forms
# All signatures: (shape, seed, sm, **kwargs) -> float32 (h,w) in [0,1].
# ----------------------------------------------------------------------------

def abstract_expressionist_splatter(shape, seed, sm, n_splats=28,
                                     drip_chance=0.6, **kwargs):
    """
    Pollock-style paint splatter spec map. Dense irregular droplets
    of varying radius with occasional downward drip trails.
    Targets R=Metallic (reflective paint splats). Tile-bounded per
    splat for 2k-canvas performance.

    Params:
      n_splats      — number of splatter clusters.
      drip_chance   — probability each splat produces a drip tail.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10100)
    result = np.full(shape, 0.5, dtype=np.float32)

    def _put_blob(cx_f, cy_f, rad_f, amp):
        # Tile bounding box (4-sigma reach in fractional coords)
        reach_x = int(rad_f * 4.0 * w) + 2
        reach_y = int(rad_f * 4.0 * h) + 2
        cx_px = int(cx_f * w); cy_px = int(cy_f * h)
        x0 = max(0, cx_px - reach_x); x1 = min(w, cx_px + reach_x + 1)
        y0 = max(0, cy_px - reach_y); y1 = min(h, cy_px + reach_y + 1)
        if x1 <= x0 or y1 <= y0:
            return
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1); txf = txx / max(w, 1)
        d2 = (txf - cx_f) ** 2 + (tyf - cy_f) ** 2
        blob = np.exp(-d2 / (2.0 * rad_f * rad_f))
        result[y0:y1, x0:x1] += blob * amp

    for _ in range(n_splats):
        cx = float(rng.uniform(0.02, 0.98))
        cy = float(rng.uniform(0.02, 0.98))
        amp = float(rng.uniform(-0.35, 0.45))
        rad = float(rng.uniform(0.004, 0.055))
        _put_blob(cx, cy, rad, amp)
        # Satellite specks
        n_sat = int(rng.integers(4, 16))
        for _s in range(n_sat):
            sx = float(cx + rng.normal(0, rad * 2.8))
            sy = float(cy + rng.normal(0, rad * 2.8))
            sr = float(rng.uniform(0.001, 0.006))
            _put_blob(sx, sy, sr, amp * 0.6)
        # Drip trail
        if rng.random() < drip_chance:
            drip_len = float(rng.uniform(0.05, 0.22))
            drip_w = float(rng.uniform(0.0015, 0.0035))
            # Tile covering the drip (below cy by drip_len)
            reach_x = int(drip_w * 4.0 * w) + 2
            cx_px = int(cx * w); cy_px = int(cy * h)
            x0 = max(0, cx_px - reach_x); x1 = min(w, cx_px + reach_x + 1)
            y0 = cy_px; y1 = min(h, int((cy + drip_len) * h) + 1)
            if x1 > x0 and y1 > y0:
                tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                tyf = tyy / max(h, 1); txf = txx / max(w, 1)
                t = np.clip((tyf - cy) / max(drip_len, 1e-3), 0, 1)
                env = np.where((t > 0) & (t < 1), 1.0, 0.0).astype(np.float32)
                wt = drip_w * (1.0 - 0.7 * t) + 5e-4
                d = txf - cx
                drip = np.exp(-(d * d) / (2.0 * wt * wt))
                result[y0:y1, x0:x1] += drip * env * amp * 0.35

    result = np.clip(result, 0.0, 1.0)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_expressionist_splatter")


def abstract_cubist_facets(shape, seed, sm, num_facets=28, **kwargs):
    """
    Cubist faceted plane spec map — Voronoi-cell partition where each
    cell receives a constant value (flat angular facets). Per-cell
    values drawn from a bimodal distribution for characteristic
    cubist tonal contrast. Targets R=Metallic.

    Params:
      num_facets — total number of facet cells.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10110)
    pts = rng.random((num_facets, 2)).astype(np.float32)
    pts[:, 0] *= w; pts[:, 1] *= h
    # Bimodal cell values — cubist favours contrast
    vals = np.where(rng.random(num_facets) < 0.5,
                     rng.uniform(0.15, 0.35, num_facets),
                     rng.uniform(0.65, 0.9, num_facets)).astype(np.float32)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.stack([xx.ravel(), yy.ravel()], axis=1).astype(np.float32)
    _, idx = tree.query(coords, k=1)
    result = vals[idx].reshape(h, w)
    # Very light smoothing so facet edges anti-alias one pixel
    result = _gauss(result, sigma=0.6)
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_cubist_facets")


def abstract_rothko_field(shape, seed, sm, num_fields=3, feather=0.08,
                           **kwargs):
    """
    Rothko-style soft color-field rectangles — a few very large
    horizontal rectangles stacked with gently feathered edges.
    Targets B=Clearcoat (soft depth variation per field).

    Params:
      num_fields — number of horizontal colour-field bands.
      feather    — vertical feather softness between bands.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10120)
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    result = np.full(shape, 0.5, dtype=np.float32)
    # Band boundaries
    bounds = np.sort(rng.uniform(0.15, 0.85, num_fields - 1))
    bounds = np.concatenate([[0.0], bounds, [1.0]]).astype(np.float32)
    vals = rng.uniform(0.2, 0.85, num_fields).astype(np.float32)
    # Single shared brush-texture noise for the whole canvas — cheap
    fld_noise = multi_scale_noise(shape, [40, 80], [0.6, 0.4],
                                   seed + 10121)
    fld_noise = _normalize(fld_noise) - 0.5
    for i in range(num_fields):
        top, bot = bounds[i], bounds[i + 1]
        # Smooth envelope inside band (column vector broadcasts over width)
        env_top = 1.0 / (1.0 + np.exp(-(yy - top) / max(feather, 1e-4)))
        env_bot = 1.0 / (1.0 + np.exp((yy - bot) / max(feather, 1e-4)))
        env = (env_top * env_bot).astype(np.float32)
        # Phase-shift the shared noise per field so each field looks distinct
        phase = int(rng.integers(0, h))
        band_noise = np.roll(fld_noise, phase, axis=0)
        result = result * (1.0 - env) + (vals[i] + band_noise * 0.08) * env
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_rothko_field")


def abstract_kandinsky_shapes(shape, seed, sm, n_circles=12, n_lines=10,
                                n_triangles=6, **kwargs):
    """
    Kandinsky abstract composition — scattered circles, straight
    lines, and triangles of varying size. Tile-bounded for 2k speed.
    Targets R=Metallic.

    Params:
      n_circles    — count of circular shapes.
      n_lines      — count of straight line segments.
      n_triangles — count of triangles.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10130)
    result = np.full(shape, 0.5, dtype=np.float32)

    def _tile_bbox(cx_f, cy_f, reach_xf, reach_yf):
        rx = int(reach_xf * w) + 2; ry = int(reach_yf * h) + 2
        cxp = int(cx_f * w); cyp = int(cy_f * h)
        x0 = max(0, cxp - rx); x1 = min(w, cxp + rx + 1)
        y0 = max(0, cyp - ry); y1 = min(h, cyp + ry + 1)
        return x0, x1, y0, y1

    # Circles (filled or ring)
    for _ in range(n_circles):
        cx = float(rng.uniform(0.05, 0.95))
        cy = float(rng.uniform(0.05, 0.95))
        rad = float(rng.uniform(0.015, 0.10))
        amp = float(rng.uniform(-0.35, 0.35))
        x0, x1, y0, y1 = _tile_bbox(cx, cy, rad * 1.6, rad * 1.6)
        if x1 <= x0 or y1 <= y0:
            continue
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1); txf = txx / max(w, 1)
        r = np.sqrt((txf - cx) ** 2 + (tyf - cy) ** 2)
        if rng.random() < 0.5:
            contribution = amp * np.clip(1.0 - (r - rad) / 0.006, 0, 1)
        else:
            ring_w = rad * float(rng.uniform(0.08, 0.18))
            contribution = amp * np.exp(-((r - rad) ** 2) /
                                          (2.0 * ring_w ** 2))
        result[y0:y1, x0:x1] += contribution

    # Lines
    for _ in range(n_lines):
        x_f = float(rng.uniform(0.05, 0.95))
        y_f = float(rng.uniform(0.05, 0.95))
        ang = float(rng.uniform(0, np.pi))
        length = float(rng.uniform(0.15, 0.45))
        thick = float(rng.uniform(0.0015, 0.004))
        cs, sn = np.cos(ang), np.sin(ang)
        # bounding box around full line segment length
        reach_x = length * 0.5 * abs(cs) + thick * 4.0 * abs(sn) + 0.01
        reach_y = length * 0.5 * abs(sn) + thick * 4.0 * abs(cs) + 0.01
        # center of line = start + length/2 * direction
        cx = x_f + length * 0.5 * cs
        cy = y_f + length * 0.5 * sn
        x0, x1, y0, y1 = _tile_bbox(cx, cy, reach_x, reach_y)
        if x1 <= x0 or y1 <= y0:
            continue
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1); txf = txx / max(w, 1)
        dx = txf - x_f; dy = tyf - y_f
        along = dx * cs + dy * sn
        perp = -dx * sn + dy * cs
        env = np.clip(along / length, 0, 1) * np.clip(1 - along / length, 0, 1) * 4.0
        env = np.clip(env, 0, 1)
        line = np.exp(-(perp * perp) / (2.0 * thick * thick))
        result[y0:y1, x0:x1] += line * env * float(rng.uniform(-0.35, 0.4))

    # Triangles (pyramid distance)
    for _ in range(n_triangles):
        cx = float(rng.uniform(0.10, 0.90))
        cy = float(rng.uniform(0.10, 0.90))
        sz = float(rng.uniform(0.04, 0.12))
        amp = float(rng.uniform(-0.35, 0.4))
        rot = float(rng.uniform(0, 2 * np.pi))
        x0, x1, y0, y1 = _tile_bbox(cx, cy, sz * 1.3, sz * 1.3)
        if x1 <= x0 or y1 <= y0:
            continue
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1); txf = txx / max(w, 1)
        dx = txf - cx; dy = tyf - cy
        rx = dx * np.cos(rot) + dy * np.sin(rot)
        ry = -dx * np.sin(rot) + dy * np.cos(rot)
        tri_mask = (ry + np.abs(rx) * 0.577) < sz
        tri_mask &= (ry > -sz * 0.5)
        result[y0:y1, x0:x1] += tri_mask.astype(np.float32) * amp * 0.7

    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_kandinsky_shapes")


def abstract_mondrian_grid(shape, seed, sm, min_splits=3, max_splits=6,
                             **kwargs):
    """
    Mondrian-style rectangular grid — the plane is recursively split
    along axis-aligned lines with thick black grid lines separating
    rectangles, each filled with a constant spec value (primary-like
    contrast). Targets R=Metallic.

    Params:
      min_splits — minimum recursion depth.
      max_splits — maximum recursion depth.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10140)
    result = np.full(shape, 0.5, dtype=np.float32)
    grid_line_w = max(3, int(min(h, w) * 0.006))

    # Build rectangle list by recursive splitting
    # Each rect: (y0,y1,x0,x1,depth)
    rects = [(0, h, 0, w, 0)]
    final = []
    while rects:
        y0, y1, x0, x1, d = rects.pop()
        rh = y1 - y0; rw = x1 - x0
        if (d >= max_splits) or (rh < 40 or rw < 40) or \
           (d >= min_splits and rng.random() < 0.35):
            final.append((y0, y1, x0, x1))
            continue
        # Choose split axis along longer side
        if rw > rh:
            split = rng.integers(int(x0 + rw * 0.25), int(x0 + rw * 0.75) + 1)
            rects.append((y0, y1, x0, int(split), d + 1))
            rects.append((y0, y1, int(split), x1, d + 1))
        else:
            split = rng.integers(int(y0 + rh * 0.25), int(y0 + rh * 0.75) + 1)
            rects.append((y0, int(split), x0, x1, d + 1))
            rects.append((int(split), y1, x0, x1, d + 1))

    # Fill each final rect with a value; weight toward extremes (primaries)
    for (y0, y1, x0, x1) in final:
        r = rng.random()
        if r < 0.25:
            v = rng.uniform(0.05, 0.20)  # dark (blue/black)
        elif r < 0.55:
            v = rng.uniform(0.80, 0.95)  # bright (white/yellow)
        else:
            v = rng.uniform(0.35, 0.65)  # mid (red/grey)
        result[y0:y1, x0:x1] = v

    # Draw grid lines (dark)
    # Horizontal lines at rect tops
    for (y0, y1, x0, x1) in final:
        if y0 > 0:
            y_s = max(0, y0 - grid_line_w // 2)
            y_e = min(h, y0 + grid_line_w // 2 + 1)
            result[y_s:y_e, x0:x1] = 0.06
        if x0 > 0:
            x_s = max(0, x0 - grid_line_w // 2)
            x_e = min(w, x0 + grid_line_w // 2 + 1)
            result[y0:y1, x_s:x_e] = 0.06
    out = _sm_scale(_normalize(result.astype(np.float32)), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_mondrian_grid")


def abstract_op_art_circles(shape, seed, sm, ring_freq=40.0, **kwargs):
    """
    Op-art concentric circles — very high-frequency alternating light
    and dark rings from an off-centre origin, producing the classic
    Bridget Riley illusory-motion ring field. Targets R=Metallic.

    Params:
      ring_freq — rings per unit radius.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10150)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1); xf = xx / max(w, 1)
    cx = float(rng.uniform(0.4, 0.6))
    cy = float(rng.uniform(0.4, 0.6))
    r = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
    # Sharp square-wave rings, slight radial thickness modulation
    rings = np.sign(np.sin(r * ring_freq * 2 * np.pi))
    rings = rings * 0.5 + 0.5
    # Soft vignette to anchor composition
    vign = np.clip(1.0 - r * 1.4, 0, 1)
    result = rings * (0.3 + 0.7 * vign) + 0.5 * (1 - vign) * 0.0
    result = np.clip(_normalize(result).astype(np.float32), 0.0, 1.0)
    out = _sm_scale(result, sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_op_art_circles")


def abstract_op_art_waves(shape, seed, sm, freq=30.0, wave_amp=0.08,
                           wave_freq=3.0, **kwargs):
    """
    Op-art wavy parallel lines — tight parallel stripes whose
    x-coordinate is perturbed by a slow sinusoid, producing Bridget
    Riley's 'Current' and 'Movement in Squares' illusory-motion look.
    Targets G=Roughness.

    Params:
      freq        — stripe frequency.
      wave_amp    — amplitude of the sinusoidal warp.
      wave_freq   — number of wave cycles vertically.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1); xf = xx / max(w, 1)
    warp = np.sin(yf * wave_freq * 2 * np.pi) * wave_amp
    stripes = np.sin((xf + warp) * freq * 2 * np.pi)
    # Sharpen
    stripes = np.clip(stripes * 3.0, -1.0, 1.0)
    result = stripes * 0.5 + 0.5
    result = result.astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_op_art_waves")


def abstract_suprematism(shape, seed, sm, n_forms=7, **kwargs):
    """
    Malevich-style suprematism — a handful of clean, hard-edged
    rectangles of varying rotation and size arranged asymmetrically
    on a flat ground. Targets R=Metallic.

    Params:
      n_forms — total number of primary forms.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10160)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(n_forms):
        cx = float(rng.uniform(0.15, 0.85))
        cy = float(rng.uniform(0.15, 0.85))
        rw = float(rng.uniform(0.05, 0.35))
        rh = float(rng.uniform(0.02, 0.18))
        rot = float(rng.uniform(-0.6, 0.6))
        v = float(rng.choice([0.10, 0.12, 0.88, 0.92, 0.4, 0.7]))
        # Rotated bbox — use max diagonal as reach
        diag = max(rw, rh) + 0.02
        reach_x = int(diag * w) + 2
        reach_y = int(diag * h) + 2
        cxp = int(cx * w); cyp = int(cy * h)
        x0 = max(0, cxp - reach_x); x1 = min(w, cxp + reach_x + 1)
        y0 = max(0, cyp - reach_y); y1 = min(h, cyp + reach_y + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1); txf = txx / max(w, 1)
        dx = txf - cx; dy = tyf - cy
        rx = dx * np.cos(rot) + dy * np.sin(rot)
        ry = -dx * np.sin(rot) + dy * np.cos(rot)
        mask = (np.abs(rx) < rw * 0.5) & (np.abs(ry) < rh * 0.5)
        edge = np.maximum(np.abs(rx) - rw * 0.5,
                           np.abs(ry) - rh * 0.5)
        feather = np.clip(1.0 - edge * 200.0, 0, 1)
        blend = feather * mask.astype(np.float32)
        result[y0:y1, x0:x1] = result[y0:y1, x0:x1] * (1.0 - blend) + v * blend
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_suprematism")


def abstract_futurist_motion(shape, seed, sm, n_lines=90, blur_sigma=1.5,
                               **kwargs):
    """
    Futurist speed-blur motion — fanned parallel streaks with
    directional Gaussian blur, evoking Balla / Boccioni dynamism.
    Targets G=Roughness.

    Params:
      n_lines     — number of motion streaks.
      blur_sigma  — additional Gaussian blur sigma.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10170)
    result = np.zeros(shape, dtype=np.float32)
    # Draw streaks by impulse + directional blur
    ang = float(rng.uniform(-0.25, 0.25))  # near-horizontal
    cs, sn = np.cos(ang), np.sin(ang)
    for _ in range(n_lines):
        y0 = int(rng.uniform(0, h))
        x0 = int(rng.uniform(0, w * 0.3))
        length = int(rng.uniform(w * 0.35, w * 0.85))
        amp = float(rng.uniform(0.4, 1.0))
        # Plot along parametric line
        ts = np.arange(length)
        xs = np.clip(x0 + (ts * cs).astype(np.int32), 0, w - 1)
        ys = np.clip(y0 + (ts * sn).astype(np.int32), 0, h - 1)
        # Trailing amplitude
        env = np.linspace(amp, 0.0, length, dtype=np.float32)
        result[ys, xs] = np.maximum(result[ys, xs], env)
    # Directional blur via anisotropic Gaussian approx (horizontal strong)
    result = _gauss(result, sigma=blur_sigma)
    result = _normalize(result)
    # Lift base + combine to modulation around 0.5
    result = 0.5 + (result - 0.5) * 0.9
    result = np.clip(result, 0.0, 1.0).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_futurist_motion")


def abstract_minimalist_stripe(shape, seed, sm, n_bands=6, **kwargs):
    """
    Minimalist horizontal bands — a very small number of large flat
    horizontal bands (Agnes Martin / Donald Judd minimalism).
    Targets B=Clearcoat.

    Params:
      n_bands — number of horizontal bands.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10180)
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    bounds = np.linspace(0, 1, n_bands + 1)
    vals = rng.uniform(0.25, 0.85, n_bands).astype(np.float32)
    result = np.zeros(shape, dtype=np.float32)
    for i in range(n_bands):
        mask = ((yy >= bounds[i]) & (yy < bounds[i + 1])).astype(np.float32)
        result = result + mask * vals[i]
    # Very light horizontal wash for hand-painted minimalism
    wash = multi_scale_noise(shape, [80], [1.0], seed + 10181)
    wash = (_normalize(wash) - 0.5) * 0.05
    result = np.clip(result + wash, 0, 1).astype(np.float32)
    # Broadcast to full width
    if result.shape[1] != w:
        result = np.broadcast_to(result, shape).copy()
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_minimalist_stripe")


def abstract_hard_edge_field(shape, seed, sm, n_blocks=14, **kwargs):
    """
    Hard-edge abstraction — Ellsworth Kelly / Frank Stella flat
    colour blocks with razor-sharp boundaries. Blocks are axis or
    diagonal-aligned trapezoids. Targets R=Metallic.

    Params:
      n_blocks — number of colour blocks.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10190)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1); xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(n_blocks):
        # Random half-plane chosen by linear inequality
        a = rng.uniform(-1.2, 1.2)
        b = rng.uniform(-1.2, 1.2)
        c = rng.uniform(-0.6, 0.6)
        side = (a * (xf - 0.5) + b * (yf - 0.5) + c) > 0
        v = float(rng.uniform(0.1, 0.9))
        # Only paint inside a randomly placed box
        bx = rng.uniform(0.05, 0.55); by = rng.uniform(0.05, 0.55)
        bw = rng.uniform(0.2, 0.55); bh = rng.uniform(0.2, 0.55)
        in_box = (xf >= bx) & (xf <= bx + bw) & \
                  (yf >= by) & (yf <= by + bh)
        mask = side & in_box
        result = np.where(mask, v, result)
    result = np.clip(result, 0, 1).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_hard_edge_field")


def abstract_color_field_bleed(shape, seed, sm, num_fields=4, bleed=0.06,
                                 **kwargs):
    """
    Helen Frankenthaler soak-stain / bleed — large blurred colour
    regions with irregular edges that bleed into each other.
    Targets B=Clearcoat.

    Params:
      num_fields — number of soft colour fields.
      bleed      — fractional bleed softness.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10200)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1); xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)
    # One shared bleed noise map — cheap, re-phased per field
    rim_noise_base = multi_scale_noise(shape, [30, 60], [0.6, 0.4],
                                        seed + 10201)
    rim_noise_base = (_normalize(rim_noise_base) - 0.5) * bleed
    for i in range(num_fields):
        cx = rng.uniform(0.05, 0.95); cy = rng.uniform(0.05, 0.95)
        rx = rng.uniform(0.15, 0.5); ry = rng.uniform(0.15, 0.5)
        v = float(rng.uniform(0.2, 0.85))
        # Elliptical distance, then extremely soft falloff
        d = np.sqrt(((xf - cx) / rx) ** 2 + ((yf - cy) / ry) ** 2)
        falloff = np.exp(-(d ** 2) / (2.0 * 0.9 ** 2))
        # Phase-shift shared rim-noise so each field's edge looks distinct
        phase_y = int(rng.integers(0, h))
        phase_x = int(rng.integers(0, w))
        rim_noise = np.roll(np.roll(rim_noise_base, phase_y, axis=0),
                             phase_x, axis=1)
        falloff = np.clip(falloff + rim_noise * (1.0 - falloff), 0, 1)
        result = result * (1.0 - falloff) + v * falloff
    # Large gaussian to emulate soak (sigma bounded to avoid cv2 overhead)
    soak_sigma = float(min(min(h, w) * 0.005 + 1.0, 10.0))
    result = _gauss(result, sigma=soak_sigma)
    result = np.clip(result, 0, 1).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_color_field_bleed")


def abstract_fluid_acrylic_pour(shape, seed, sm, swirl_freq=6.0,
                                  turb_scale=40.0, **kwargs):
    """
    Fluid-acrylic pour — swirling marbled cells produced by combining
    a large-scale domain-warped noise with per-cell 'ring' banding,
    evoking 'cells' in a gravity pour painting. Targets R=Metallic.

    Params:
      swirl_freq  — frequency of the swirl warp.
      turb_scale  — base turbulence scale.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    # Base low-frequency field
    base = multi_scale_noise(shape, [turb_scale, turb_scale * 0.5],
                              [0.6, 0.4], seed + 10210)
    base = _normalize(base)
    # Warp coordinates using the noise
    warp_x = multi_scale_noise(shape, [turb_scale * 0.6], [1.0],
                                seed + 10211)
    warp_y = multi_scale_noise(shape, [turb_scale * 0.6], [1.0],
                                seed + 10212)
    warp_x = (_normalize(warp_x) - 0.5) * 0.15
    warp_y = (_normalize(warp_y) - 0.5) * 0.15
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1) + warp_y
    xf = xx / max(w, 1) + warp_x
    # Cell rings from distance from noise-defined centres
    swirl = np.sin((base + yf * 0.5 + xf * 0.5) * swirl_freq * 2 * np.pi)
    swirl = swirl * 0.5 + 0.5
    # Overlay a second twist
    swirl2 = np.sin((base * 1.7 - yf * 0.3 + xf * 0.7) *
                     swirl_freq * 1.3 * 2 * np.pi)
    swirl2 = swirl2 * 0.5 + 0.5
    result = 0.55 * swirl + 0.45 * swirl2
    result = _gauss(result.astype(np.float32), sigma=0.8)
    result = np.clip(_normalize(result), 0, 1).astype(np.float32)
    out = _sm_scale(result, sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_fluid_acrylic_pour")


def abstract_ink_wash_gradient(shape, seed, sm, edge_bleeds=12, **kwargs):
    """
    Sumi-e ink wash — a large graded wash from bright to dark with
    irregular bleed edges and small dark dropped ink blots near the
    dark end. Targets G=Roughness.

    Params:
      edge_bleeds — number of bleed fingers along the gradient edge.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10220)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1); xf = xx / max(w, 1)
    # Angled base gradient
    ang = float(rng.uniform(-0.4, 0.4))
    grad = yf * np.cos(ang) + xf * np.sin(ang)
    grad = _normalize(grad.astype(np.float32))
    # Irregular wash boundary: shift the gradient by a multi-scale noise
    noise = multi_scale_noise(shape, [20, 40, 80], [0.4, 0.4, 0.2],
                               seed + 10221)
    noise = (_normalize(noise) - 0.5) * 0.25
    wash = np.clip(grad + noise, 0, 1)
    # Dark mid/low = rough; gamma-curve to emulate ink soaking
    wash = np.power(wash, 1.8)
    # Drop ink blots (small dark blobs) in the darker half
    blots = np.zeros(shape, dtype=np.float32)
    for _ in range(edge_bleeds):
        # choose a point weighted toward the darker region
        cx = rng.uniform(0.0, 1.0)
        cy = rng.uniform(0.0, 1.0)
        # only allow if dark
        idx_y = int(np.clip(cy * h, 0, h - 1))
        idx_x = int(np.clip(cx * w, 0, w - 1))
        if wash[idx_y, idx_x] > 0.55:
            continue
        rad = rng.uniform(0.01, 0.04)
        d2 = (xf - cx) ** 2 + (yf - cy) ** 2
        blots += np.exp(-d2 / (2.0 * rad * rad)) * rng.uniform(0.3, 0.7)
    blots = np.clip(blots, 0, 1)
    result = np.clip(1.0 - wash + blots * 0.5, 0, 1).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_ink_wash_gradient")


def abstract_neon_glitch(shape, seed, sm, n_slices=30, bar_density=0.08,
                          **kwargs):
    """
    Digital glitch artefact — horizontal data-corruption slices,
    scanline banding, and small rectangular RGB-shift blocks.
    Targets R=Metallic with high contrast.

    Params:
      n_slices    — number of glitch slice bands.
      bar_density — density of horizontal scanline bars.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10230)
    result = np.full(shape, 0.5, dtype=np.float32)
    # Scanline grid
    yy = np.arange(h).reshape(-1, 1).astype(np.float32)
    scan = 0.5 + 0.15 * np.sin(yy * (2 * np.pi / 2.0))
    result = result * 0.5 + np.broadcast_to(scan, shape) * 0.5

    # Slice offsets — horizontal bands shifted +/- some pixels
    for _ in range(n_slices):
        y0 = int(rng.uniform(0, h - 1))
        y1 = int(min(h, y0 + rng.integers(1, max(2, int(h * 0.03)))))
        shift = int(rng.integers(-int(w * 0.08), int(w * 0.08) + 1))
        brightness = float(rng.uniform(-0.3, 0.35))
        if shift == 0:
            result[y0:y1, :] = np.clip(result[y0:y1, :] + brightness, 0, 1)
        else:
            result[y0:y1, :] = np.roll(result[y0:y1, :], shift, axis=1)
            result[y0:y1, :] = np.clip(result[y0:y1, :] + brightness, 0, 1)

    # Small rectangular glitch blocks (datamosh)
    n_blocks = int(bar_density * 200)
    for _ in range(n_blocks):
        by = int(rng.uniform(0, h))
        bx = int(rng.uniform(0, w))
        bh = int(rng.integers(2, max(3, int(h * 0.02))))
        bw = int(rng.integers(int(w * 0.02), int(w * 0.15)))
        y0 = max(0, by); y1 = min(h, by + bh)
        x0 = max(0, bx); x1 = min(w, bx + bw)
        v = float(rng.choice([0.08, 0.92]))
        result[y0:y1, x0:x1] = v
    out = _sm_scale(_normalize(result.astype(np.float32)), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_neon_glitch")


def abstract_retro_wave(shape, seed, sm, horizon_frac=0.55,
                          grid_freq_x=28.0, grid_freq_y=18.0, **kwargs):
    """
    Synthwave retro grid — perspective floor grid receding to a
    horizon, with a soft sun gradient above. Iconic 80s
    vapourwave aesthetic. Targets R=Metallic.

    Params:
      horizon_frac — fraction of height where horizon sits.
      grid_freq_x  — horizontal line frequency.
      grid_freq_y  — receding line frequency.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yf = yy / max(h, 1); xf = xx / max(w, 1)
    result = np.full(shape, 0.5, dtype=np.float32)

    # Sun semi-circle above horizon
    cx = 0.5; cy = horizon_frac
    r_sun = 0.18
    d = np.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
    sun = np.clip(1.0 - d / r_sun, 0, 1)
    sun = sun * (yf <= horizon_frac).astype(np.float32)
    # Horizontal dark sun bands
    sun *= 0.5 + 0.5 * np.sign(np.sin((yf - cy) * 80.0))
    result += sun * 0.35

    # Floor grid below horizon
    below = (yf > horizon_frac).astype(np.float32)
    # Perspective projection: v = (yf - horizon) / (1 - horizon)
    v = np.clip((yf - horizon_frac) / max(1 - horizon_frac, 1e-3), 0, 1)
    # Receding horizontal lines: density increases toward horizon
    lines_y = np.abs(np.sin(np.power(v + 1e-3, 0.5) * grid_freq_y * np.pi))
    # Converging vertical lines: u = (xf - 0.5) / v
    u = (xf - 0.5) / np.clip(v, 0.05, 1.0)
    lines_x = np.abs(np.sin(u * grid_freq_x * np.pi))
    grid = np.maximum(1.0 - lines_y * 4.0, 1.0 - lines_x * 4.0)
    grid = np.clip(grid, 0, 1)
    result += grid * below * 0.35
    # Darken sky above horizon
    result -= (1.0 - below) * 0.10
    result = np.clip(result, 0, 1).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_retro_wave")


def abstract_bauhaus_forms(shape, seed, sm, n_primitives=9, **kwargs):
    """
    Bauhaus primary forms — circle, square, and triangle primitives
    sized and placed according to Bauhaus design-school principles:
    clear hierarchy, primary-colour tonality, balanced asymmetry.
    Targets R=Metallic.

    Params:
      n_primitives — number of primary forms.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.default_rng(seed + 10250)
    result = np.full(shape, 0.5, dtype=np.float32)

    for _ in range(n_primitives):
        cx = float(rng.uniform(0.12, 0.88))
        cy = float(rng.uniform(0.12, 0.88))
        sz = float(rng.uniform(0.05, 0.22))
        kind = int(rng.integers(0, 3))
        v = float(rng.choice([0.08, 0.92, 0.35, 0.70]))
        reach = sz + 0.01
        reach_x = int(reach * w) + 2
        reach_y = int(reach * h) + 2
        cxp = int(cx * w); cyp = int(cy * h)
        x0 = max(0, cxp - reach_x); x1 = min(w, cxp + reach_x + 1)
        y0 = max(0, cyp - reach_y); y1 = min(h, cyp + reach_y + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        tyy, txx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        tyf = tyy / max(h, 1); txf = txx / max(w, 1)
        if kind == 0:
            d = np.sqrt((txf - cx) ** 2 + (tyf - cy) ** 2)
            mask = np.clip(1.0 - (d - sz * 0.5) * 400.0, 0, 1)
        elif kind == 1:
            dx = np.abs(txf - cx); dy = np.abs(tyf - cy)
            edge = np.maximum(dx - sz * 0.5, dy - sz * 0.5)
            mask = np.clip(-edge * 400.0, 0, 1)
        else:
            dx = txf - cx; dy = tyf - cy
            rot = float(rng.uniform(0, 2 * np.pi))
            rx = dx * np.cos(rot) + dy * np.sin(rot)
            ry = -dx * np.sin(rot) + dy * np.cos(rot)
            tri_edge = np.maximum(ry + np.abs(rx) * 0.577 - sz * 0.45,
                                    -ry - sz * 0.25)
            mask = np.clip(-tri_edge * 400.0, 0, 1)
        result[y0:y1, x0:x1] = result[y0:y1, x0:x1] * (1.0 - mask) + v * mask
    result = np.clip(result, 0, 1).astype(np.float32)
    out = _sm_scale(_normalize(result), sm).astype(np.float32)
    return _validate_spec_output(out, "abstract_bauhaus_forms")


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
    # --- SPARKLE SYSTEM EXPANSION (9 new) ---
    "sparkle_rain": sparkle_rain,
    "sparkle_constellation": sparkle_constellation,
    "sparkle_nebula": sparkle_nebula,
    "sparkle_firefly": sparkle_firefly,
    "sparkle_shattered": sparkle_shattered,
    "sparkle_champagne": sparkle_champagne,
    "sparkle_comet": sparkle_comet,
    "sparkle_galaxy_swirl": sparkle_galaxy_swirl,
    "sparkle_electric_field": sparkle_electric_field,
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
    # --- RACING & AUTOMOTIVE (v6.2) ---
    "tire_rubber_transfer": tire_rubber_transfer,
    "vinyl_wrap_texture": vinyl_wrap_texture,
    "paint_drip_edge": paint_drip_edge,
    "racing_tape_residue": racing_tape_residue,
    "sponsor_deboss": sponsor_deboss,
    "heat_discoloration": heat_discoloration,
    "salt_spray_corrosion": salt_spray_corrosion,
    "track_grime": track_grime,
    # --- v6.2.x SPONSOR & VINYL ---
    "vinyl_seam": vinyl_seam,
    "decal_lift_edge": decal_lift_edge,
    "sponsor_emboss_v2": sponsor_emboss_v2,
    "sticker_bubble_film": sticker_bubble_film,
    "vinyl_stretched": vinyl_stretched,
    # --- v6.2.x RACE WEAR ---
    "tire_smoke_residue": tire_smoke_residue,
    "brake_dust_buildup": brake_dust_buildup,
    "oil_streak_panel": oil_streak_panel,
    "gravel_chip_field": gravel_chip_field,
    "wax_streak_polish": wax_streak_polish,
    # --- v6.2.x PREMIUM FINISHES ---
    "mother_of_pearl_inlay": mother_of_pearl_inlay,
    "anodized_rainbow": anodized_rainbow,
    "frosted_glass_etch": frosted_glass_etch,
    "gold_leaf_torn": gold_leaf_torn,
    "copper_patina_drip": copper_patina_drip,
    # --- v6.2.x COLOR-SHIFT VARIANTS ---
    "brushed_linear_warm": brushed_linear_warm,
    "brushed_linear_cool": brushed_linear_cool,
    "micro_sparkle_warm": micro_sparkle_warm,
    "micro_sparkle_cool": micro_sparkle_cool,
    "cloud_wisps_warm": cloud_wisps_warm,
    "cloud_wisps_cool": cloud_wisps_cool,
    "aniso_grain_deep": aniso_grain_deep,
    # --- v6.2.y RACE HERITAGE ---
    "checker_flag_subtle": checker_flag_subtle,
    "drag_strip_burnout": drag_strip_burnout,
    "pit_lane_stripes": pit_lane_stripes,
    "victory_lap_confetti": victory_lap_confetti,
    "sponsor_tape_vinyl": sponsor_tape_vinyl,
    "race_number_ghost": race_number_ghost,
    # --- v6.2.y MECHANICAL ---
    "exhaust_pipe_scorch": exhaust_pipe_scorch,
    "radiator_grille_mesh": radiator_grille_mesh,
    "engine_bay_grime": engine_bay_grime,
    "tire_smoke_streaks": tire_smoke_streaks,
    "undercarriage_spray": undercarriage_spray,
    "suspension_rust_ring": suspension_rust_ring,
    # --- v6.2.y WEATHER & TRACK ---
    "rain_droplet_beads": rain_droplet_beads,
    "mud_splatter_random": mud_splatter_random,
    "wet_track_gloss": wet_track_gloss,
    "dry_dust_film": dry_dust_film,
    "morning_dew_fog": morning_dew_fog,
    "tarmac_grit_embed": tarmac_grit_embed,
    # --- v6.2.y ARTISTIC ---
    "brushstroke_bold": brushstroke_bold,
    "crayon_wax_resist": crayon_wax_resist,
    "airbrush_gradient_bloom": airbrush_gradient_bloom,
    "spray_paint_drip": spray_paint_drip,
    "stippled_dots_fine": stippled_dots_fine,
    "halftone_print": halftone_print,
    # --- ABSTRACT ART (17 patterns) ---
    "abstract_expressionist_splatter": abstract_expressionist_splatter,
    "abstract_cubist_facets": abstract_cubist_facets,
    "abstract_rothko_field": abstract_rothko_field,
    "abstract_kandinsky_shapes": abstract_kandinsky_shapes,
    "abstract_mondrian_grid": abstract_mondrian_grid,
    "abstract_op_art_circles": abstract_op_art_circles,
    "abstract_op_art_waves": abstract_op_art_waves,
    "abstract_suprematism": abstract_suprematism,
    "abstract_futurist_motion": abstract_futurist_motion,
    "abstract_minimalist_stripe": abstract_minimalist_stripe,
    "abstract_hard_edge_field": abstract_hard_edge_field,
    "abstract_color_field_bleed": abstract_color_field_bleed,
    "abstract_fluid_acrylic_pour": abstract_fluid_acrylic_pour,
    "abstract_ink_wash_gradient": abstract_ink_wash_gradient,
    "abstract_neon_glitch": abstract_neon_glitch,
    "abstract_retro_wave": abstract_retro_wave,
    "abstract_bauhaus_forms": abstract_bauhaus_forms,
}

# 2026-04-21 HEENAN OVERNIGHT iter 3: HP2 / HP3 / H4HR-4..H4HR-8
# cross-registry rename aliases. The JS side renamed these spec-pattern
# IDs to disambiguate from colliding MONOLITHIC ids (HP2: carbon_weave,
# HP3: diffraction_grating, H4HR-4..8: oil_slick/gravity_well/sparkle_*),
# but PATTERN_CATALOG still uses the un-prefixed legacy keys. Without
# this block, selecting the JS-canonical id results in
# PATTERN_CATALOG.get(sp_name) → None → `continue` (silent no-render).
#
# Each alias points the JS-canonical id at the same function the old
# key points at, so the painter gets identical render output.
_HP_H4HR_SPEC_ALIASES = {
    # HP2 — cross-registry rename to disambiguate from BASES/PATTERNS carbon_weave
    "spec_carbon_weave":              "carbon_weave",
    # HP3 — renamed to spec_diffraction_grating_cd (CC target via docstring)
    "spec_diffraction_grating_cd":    "diffraction_grating",
    # H4HR-4..H4HR-8 — 5 collisions vs MONOLITHICS
    "spec_oil_slick":                 "oil_slick",
    "spec_gravity_well":              "gravity_well",
    "spec_sparkle_constellation":     "sparkle_constellation",
    "spec_sparkle_firefly":           "sparkle_firefly",
    "spec_sparkle_champagne":         "sparkle_champagne",
}
for _new_id, _old_id in _HP_H4HR_SPEC_ALIASES.items():
    if _new_id not in PATTERN_CATALOG and _old_id in PATTERN_CATALOG:
        PATTERN_CATALOG[_new_id] = PATTERN_CATALOG[_old_id]


def _spb_catalog_seed(name):
    h = 2166136261
    for ch in str(name):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _spb_micro_overlay(shape, seed, family):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng_seed = (int(seed) * 1664525 + int(family) * 1013904223) & 0xFFFFFFFF
    rng = np.random.default_rng(rng_seed)
    raw = rng.random((h, w), dtype=np.float32)
    fine = raw * 0.58 + _gauss(raw, sigma=0.85) * 0.27 + _gauss(raw, sigma=2.1) * 0.15
    fine = _normalize(fine).astype(np.float32)
    sparkle = (raw > (0.986 - min(0.018, (family % 10) * 0.0018))).astype(np.float32)
    if sparkle.any():
        sparkle = np.maximum(sparkle, _gauss(sparkle, sigma=0.38) * 0.55).astype(np.float32)
    return fine, sparkle


_SPB_SPEC_REBUILD_MODES = {
    "depth_gradient": "depth_pool",
    "abstract_ink_wash_gradient": "ink_wash",
    "cc_fish_eye": "bubbles",
    "cc_drip_runs": "drips",
    "sponsor_tape_vinyl": "tape",
    "race_number_ghost": "race_ghost",
    "crayon_wax_resist": "wax",
    "exhaust_pipe_scorch": "scorch",
    "spec_battle_scars": "scratches",
    "electric_branches": "branches",
    "undercarriage_spray": "spray_grit",
    "tire_smoke_streaks": "smoke_streaks",
    "abstract_suprematism": "hard_edge",
    "cloud_wisps": "wisps",
    "tarmac_grit_embed": "grit",
    "spec_cast_surface": "cast_pits",
    "abstract_expressionist_splatter": "splatter",
    "spec_chromatic_aberration": "chromatic_fringe",
    "sponsor_deboss": "deboss",
    "abstract_minimalist_stripe": "pinstripe",
    "rain_droplet_beads": "beads",
    "tire_smoke_residue": "smoke_residue",
    "victory_lap_confetti": "confetti",
    "sticker_bubble_film": "bubbles",
    "spec_caustic_light": "caustic",
    "cloud_wisps_cool": "wisps",
    "gravel_chip_field": "chips",
    "racing_tape_residue": "tape",
    "spec_thermal_spray": "thermal_spray",
    "spec_leaf_venation": "leaf_veins",
    "sponsor_emboss_v2": "emboss",
    "moire_overlay": "moire_rebuild",
    "engine_bay_grime": "oil_grime",
    "brushstroke_bold": "bristles",
    "abstract_kandinsky_shapes": "kandinsky",
}


def _spb_draw_line(canvas, x0, y0, x1, y1, value=1.0, thickness=1):
    h, w = canvas.shape
    if _CV2_OK:
        _cv2.line(
            canvas,
            (int(np.clip(x0, 0, w - 1)), int(np.clip(y0, 0, h - 1))),
            (int(np.clip(x1, 0, w - 1)), int(np.clip(y1, 0, h - 1))),
            float(value),
            thickness=max(1, int(thickness)),
            lineType=_cv2.LINE_AA,
        )
        return
    steps = max(abs(int(x1 - x0)), abs(int(y1 - y0)), 1)
    xs = np.clip(np.linspace(x0, x1, steps + 1).astype(np.int32), 0, w - 1)
    ys = np.clip(np.linspace(y0, y1, steps + 1).astype(np.int32), 0, h - 1)
    np.maximum.at(canvas, (ys, xs), float(value))


def _spb_spec_rebuild_feature(shape, seed, name, mode):
    """Targeted concept layer for underperforming spec overlays.

    This is intentionally ID-gated. The global wrapper adds pixel coverage;
    these modes add the visual idea the weak thumbnail promised.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng((_spb_catalog_seed(name) + int(seed) * 2654435761) & 0xFFFFFFFF)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn = xx / max(w - 1, 1)
    yn = yy / max(h - 1, 1)
    base = np.zeros((h, w), dtype=np.float32)
    fine, sparkle = _spb_micro_overlay((h, w), seed + 991, _spb_catalog_seed(name) ^ 0xA5A5A5A5)

    if mode == "depth_pool":
        gravity = yn ** 1.35
        meniscus = np.sin((yn + fine * 0.075) * np.pi * 34.0 + np.sin(xn * 13.0) * 1.7)
        base = gravity * 0.58 + (meniscus * 0.5 + 0.5) * 0.22 + fine * 0.20
        for _ in range(18):
            x = rng.uniform(0, w)
            _spb_draw_line(base, x, rng.uniform(0, h * 0.15), x + rng.uniform(-18, 18), h, rng.uniform(0.35, 0.95), 1)
        base = np.maximum(base, _gauss(base, 0.55) * 0.72)
    elif mode in {"drips", "spray_grit"}:
        for _ in range(90 if mode == "drips" else 150):
            x = rng.uniform(0, w)
            y0 = rng.uniform(0, h * 0.92)
            length = rng.uniform(h * 0.035, h * (0.28 if mode == "drips" else 0.13))
            lean = rng.uniform(-0.08, 0.08) * length
            _spb_draw_line(base, x, y0, x + lean, y0 + length, rng.uniform(0.35, 1.0), rng.integers(1, 3))
        base += sparkle * (0.40 if mode == "spray_grit" else 0.20)
        base = np.maximum(base, _gauss(base, 0.75) * 0.62)
    elif mode in {"bubbles", "beads"}:
        count = 180 if mode == "bubbles" else 260
        max_r = 13.0 if mode == "bubbles" else 8.0
        for _ in range(count):
            cx = int(rng.integers(0, w))
            cy = int(rng.integers(0, h))
            r = int(max(2, rng.uniform(2.0, max_r)))
            value = float(rng.uniform(0.48, 1.0))
            if _CV2_OK:
                _cv2.circle(base, (cx, cy), r, value, 1, lineType=_cv2.LINE_AA)
                if r > 3:
                    _cv2.circle(base, (cx, cy), max(1, r // 3), value * 0.22, -1, lineType=_cv2.LINE_AA)
            else:
                _spb_draw_line(base, cx - r, cy, cx + r, cy, value, 1)
                _spb_draw_line(base, cx, cy - r, cx, cy + r, value * 0.72, 1)
        base += fine * 0.20
    elif mode == "race_ghost":
        # Two faded seven-segment-style numerals, with residue halos and worn edges.
        for digit in range(2):
            ox = w * (0.24 + digit * 0.27 + rng.uniform(-0.025, 0.025))
            oy = h * rng.uniform(0.24, 0.36)
            dw = w * rng.uniform(0.16, 0.22)
            dh = h * rng.uniform(0.30, 0.42)
            segs = [
                (0.08, 0.00, 0.92, 0.00),
                (0.00, 0.06, 0.00, 0.48),
                (1.00, 0.06, 1.00, 0.48),
                (0.10, 0.50, 0.90, 0.50),
                (0.00, 0.54, 0.00, 0.94),
                (1.00, 0.54, 1.00, 0.94),
                (0.08, 1.00, 0.92, 1.00),
            ]
            keep = rng.choice(len(segs), size=int(rng.integers(4, 7)), replace=False)
            for idx in keep:
                x0, y0, x1, y1 = segs[int(idx)]
                _spb_draw_line(
                    base,
                    ox + x0 * dw,
                    oy + y0 * dh,
                    ox + x1 * dw,
                    oy + y1 * dh,
                    rng.uniform(0.55, 1.0),
                    max(2, int(min(h, w) * rng.uniform(0.006, 0.012))),
                )
        halo = _gauss(base, 2.0)
        worn = (fine > 0.58).astype(np.float32)
        base = np.maximum(base * (0.62 + worn * 0.38), halo * 0.42)
        base += fine * 0.22 + sparkle * 0.18
    elif mode in {"tape", "ghost", "deboss", "emboss"}:
        for _ in range(16):
            y = rng.uniform(0.05, 0.95)
            ang = rng.uniform(-0.18, 0.18)
            dist = np.abs((yn - y) - ang * (xn - 0.5))
            base += np.exp(-(dist ** 2) / (2.0 * rng.uniform(0.0015, 0.0045) ** 2)) * rng.uniform(0.30, 0.75)
        for _ in range(18 if mode in {"deboss", "emboss"} else 9):
            x0 = rng.uniform(0.02, 0.80)
            y0 = rng.uniform(0.02, 0.85)
            bw = rng.uniform(0.035, 0.17)
            bh = rng.uniform(0.018, 0.10)
            edge = (
                (np.abs(xn - (x0 + bw * 0.5)) < bw * 0.5).astype(np.float32)
                * (np.abs(yn - (y0 + bh * 0.5)) < bh * 0.5).astype(np.float32)
            )
            if _CV2_OK:
                rim = _cv2.Canny((edge * 255).astype(np.uint8), 1, 2).astype(np.float32) / 255.0
            else:
                rim = np.clip(
                    np.abs(edge - np.roll(edge, 1, axis=0)) +
                    np.abs(edge - np.roll(edge, 1, axis=1)),
                    0,
                    1,
                )
            base += rim * rng.uniform(0.35, 0.95) + edge * (0.09 if mode == "ghost" else 0.18)
        base += fine * (0.12 if mode == "ghost" else 0.22)
    elif mode in {"scratches", "chips"}:
        for _ in range(260):
            x = rng.uniform(0, w)
            y = rng.uniform(0, h)
            length = rng.uniform(4, 38)
            ang = rng.uniform(0, 2 * np.pi)
            _spb_draw_line(base, x, y, x + np.cos(ang) * length, y + np.sin(ang) * length, rng.uniform(0.35, 1.0), 1)
        if mode == "chips":
            base += sparkle * 0.65
        base = np.maximum(base, _gauss(base, 0.45) * 0.55)
    elif mode == "scorch":
        cx = rng.uniform(0.35, 0.65) * w
        cy = rng.uniform(0.38, 0.68) * h
        d = np.hypot((xx - cx) / max(w, 1), (yy - cy) / max(h, 1))
        rings = np.sin(d * 220.0 + fine * 3.0) * 0.5 + 0.5
        plume = np.exp(-(d ** 2) / 0.085)
        soot = _normalize(_gauss(fine, 3.0) + yn * 0.35)
        base = plume * (0.42 + rings * 0.38) + soot * 0.24 + sparkle * 0.10
    elif mode in {"branches", "leaf_veins"}:
        root_count = 18 if mode == "branches" else 42
        for _ in range(root_count):
            x = rng.uniform(0, w)
            y = rng.uniform(0, h)
            ang = rng.uniform(-np.pi, np.pi)
            length = rng.uniform(18, 70)
            for depth in range(5):
                x2 = x + np.cos(ang) * length
                y2 = y + np.sin(ang) * length
                _spb_draw_line(base, x, y, x2, y2, rng.uniform(0.45, 1.0), 1)
                if rng.random() < 0.65:
                    ang += rng.uniform(-0.78, 0.78)
                x, y = x2, y2
                length *= rng.uniform(0.52, 0.76)
        base = np.maximum(base, _gauss(base, 0.58) * 0.60)
        base += fine * 0.12
    elif mode in {"wisps", "smoke_streaks", "smoke_residue", "oil_grime"}:
        flow = (
            np.sin(xx * 0.052 + yy * 0.018 + fine * 4.0)
            + np.sin(xx * -0.026 + yy * 0.044 + fine * 5.5)
        ) * 0.5 + 0.5
        smear = _normalize(_gauss(fine, 5.0) + flow * 0.85 + yn * (0.22 if mode != "wisps" else 0.0))
        streaks = np.sin(xx * 0.24 + yy * 0.035 + smear * 2.8) * 0.5 + 0.5
        base = smear * 0.54 + streaks * 0.24 + sparkle * (0.10 if mode == "wisps" else 0.22)
    elif mode in {"grit", "cast_pits", "thermal_spray"}:
        density = 0.075 if mode == "grit" else 0.115
        pits = (rng.random((h, w), dtype=np.float32) < density).astype(np.float32)
        pits = np.maximum(pits, _gauss(pits, 0.65) * 0.62)
        orange = _normalize(_gauss(rng.random((h, w), dtype=np.float32), 1.8))
        base = pits * 0.58 + orange * 0.34 + fine * 0.20
    elif mode in {"splatter", "confetti", "hard_edge", "kandinsky"}:
        for _ in range(140 if mode == "splatter" else 70):
            cx = int(rng.integers(0, w))
            cy = int(rng.integers(0, h))
            if mode in {"confetti", "hard_edge", "kandinsky"}:
                rw = int(rng.integers(3, max(5, int(w * 0.035))))
                rh = int(rng.integers(2, max(4, int(h * 0.028))))
                x0, x1 = max(0, cx - rw), min(w, cx + rw)
                y0, y1 = max(0, cy - rh), min(h, cy + rh)
                base[y0:y1, x0:x1] = np.maximum(base[y0:y1, x0:x1], rng.uniform(0.38, 1.0))
            else:
                r = int(max(1, rng.uniform(1.5, 8.0)))
                value = float(rng.uniform(0.45, 1.0))
                if _CV2_OK:
                    _cv2.circle(base, (cx, cy), r, value, -1, lineType=_cv2.LINE_AA)
                    if r > 2:
                        _cv2.circle(base, (cx, cy), r + 1, value * 0.42, 1, lineType=_cv2.LINE_AA)
                else:
                    x0, x1 = max(0, cx - r), min(w, cx + r + 1)
                    y0, y1 = max(0, cy - r), min(h, cy + r + 1)
                    base[y0:y1, x0:x1] = np.maximum(base[y0:y1, x0:x1], value)
        base += fine * 0.14
    elif mode in {"pinstripe", "moire_rebuild", "chromatic_fringe"}:
        angle = rng.uniform(-0.5, 0.5)
        coord = (xx * np.cos(angle) + yy * np.sin(angle))
        freq1 = rng.uniform(0.42, 0.64)
        freq2 = freq1 * rng.uniform(1.055, 1.11)
        lines = (np.sin(coord * freq1) * 0.5 + 0.5) ** 9
        lines2 = (np.sin((coord + yy * 0.12) * freq2 + 1.7) * 0.5 + 0.5) ** 9
        base = np.maximum(lines, lines2) * 0.75 + fine * 0.18
        if mode == "chromatic_fringe":
            base += np.abs(np.sin(coord * 0.035 + fine * 3.0)) * 0.22
    elif mode == "caustic":
        web = (
            np.sin(xx * 0.085 + fine * 6.0)
            + np.sin(yy * 0.073 + fine * 5.0)
            + np.sin((xx + yy) * 0.052)
        )
        base = np.clip((web - 1.0) * 0.50, 0, 1) + fine * 0.18
        base = np.maximum(base, _gauss(base, 0.50) * 0.64)
    elif mode == "wax":
        for _ in range(120):
            y = rng.uniform(0, h)
            x0 = rng.uniform(0, w * 0.25)
            x1 = rng.uniform(w * 0.55, w)
            wobble = rng.uniform(-26, 26)
            _spb_draw_line(base, x0, y, x1, y + wobble, rng.uniform(0.25, 0.90), rng.integers(1, 3))
        base += (1.0 - fine) * 0.18 + sparkle * 0.16
    elif mode == "bristles":
        for _ in range(180):
            y = rng.uniform(0, h)
            x = rng.uniform(0, w)
            length = rng.uniform(18, 96)
            _spb_draw_line(base, x, y, x + length, y + rng.uniform(-12, 12), rng.uniform(0.32, 1.0), rng.integers(1, 4))
        base = np.maximum(base, _gauss(base, 0.60) * 0.58)
    else:
        base = fine

    base = _normalize(np.clip(base, 0, None).astype(np.float32))
    # Restore a subtle all-over carrier so dense panel coverage survives at 2048.
    return np.clip(base * 0.86 + fine * 0.10 + sparkle * 0.04, 0, 1).astype(np.float32)


def _spb_spec_detail_profile(name, index):
    family = _spb_catalog_seed(name)
    is_sparkle = any(tok in name for tok in ("sparkle", "flake", "dust", "glass", "shimmer", "crystal", "sand"))
    is_directional = any(tok in name for tok in ("brushed", "grain", "grating", "weave", "carbon", "machined"))
    is_weather = any(tok in name for tok in ("mud", "dust", "grime", "rust", "scorch", "patina", "wear", "rain"))
    is_ring = any(tok in name for tok in ("ring", "ripple", "concentric", "halo", "spiral", "wave"))
    is_crack = any(tok in name for tok in ("crack", "branch", "lightning", "electric", "shatter", "fracture"))
    is_grid = any(tok in name for tok in ("grid", "hex", "cell", "matrix", "dot", "weave", "carbon"))
    return {
        "detail_gain": 0.21 + (family % 7) * 0.014 + (0.22 if is_sparkle else 0.0) + (0.10 if is_directional else 0.0),
        "edge_gain": 0.048 + (index % 5) * 0.009 + (0.034 if is_directional else 0.0) + (0.020 if is_weather else 0.0),
        "sparkle_gain": 0.110 + (family % 9) * 0.010 + (0.130 if is_sparkle else 0.0),
        "threshold_shift": min(0.085, (family % 11) * 0.007),
        "directional_gain": 0.140 if is_directional else 0.0,
        "ring_gain": 0.170 if is_ring else 0.0,
        "crack_gain": 0.190 if is_crack else 0.0,
        "grid_gain": 0.155 if is_grid else 0.0,
    }


_SPEC_PATTERN_DETAIL_PROFILES = {
    _spb_name: _spb_spec_detail_profile(_spb_name, _spb_i)
    for _spb_i, _spb_name in enumerate(PATTERN_CATALOG)
}


def _spb_wrap_spec_pattern(name, fn):
    if getattr(fn, "_spb_detail_wrapped", False):
        return fn
    if getattr(fn, "_spb_concept_complete", False):
        fn._spb_detail_wrapped = True
        return fn
    rebuild_mode = _SPB_SPEC_REBUILD_MODES.get(name)
    if not rebuild_mode:
        return fn

    def _wrapped(shape, seed=0, sm=1.0, **kwargs):
        strength = float(np.clip(abs(sm), 0.0, 2.0))
        if strength <= 1e-6:
            return _validate_spec_output(fn(shape, seed, sm, **kwargs), name)
        concept = _spb_spec_rebuild_feature(shape, seed + 1217, name, rebuild_mode)
        concept_edge = np.clip(
            np.abs(concept - np.roll(concept, 1, axis=0)) +
            np.abs(concept - np.roll(concept, 1, axis=1)),
            0,
            1,
        )
        enhanced = _normalize(np.clip(concept + concept_edge * 0.20 * min(strength, 1.0), 0, 1))
        enhanced = np.clip(0.5 + (enhanced - 0.5) * (1.12 + 0.18 * min(strength, 1.0)), 0, 1)
        return _validate_spec_output(np.clip(enhanced, 0, 1).astype(np.float32), name)

    _wrapped._spb_detail_wrapped = True
    _wrapped.__name__ = getattr(fn, "__name__", name)
    _wrapped.__doc__ = getattr(fn, "__doc__", None)
    _wrapped.__module__ = getattr(fn, "__module__", __name__)
    return _wrapped


PATTERN_CATALOG = {
    _spb_name: _spb_wrap_spec_pattern(_spb_name, _spb_fn)
    for _spb_name, _spb_fn in PATTERN_CATALOG.items()
}


def _spb_fast_line_distance(coord, period, width, phase=0.0):
    pos = np.mod(coord + float(phase), float(period))
    dist = np.minimum(pos, float(period) - pos)
    return np.clip(1.0 - dist / max(float(width), 1e-6), 0, 1).astype(np.float32)


def _spb_fast_hash_grid(shape, seed):
    h, w = shape[:2] if len(shape) > 2 else shape
    y = np.arange(h, dtype=np.float32)[:, np.newaxis]
    x = np.arange(w, dtype=np.float32)[np.newaxis, :]
    return (np.mod(x * 12.9898 + y * 78.233 + float(seed % 997) * 37.719, 101.0) / 100.0).astype(np.float32)


def _spb_fast_dots_px(x, y, period_x, period_y, radius, phase_x=0.0, phase_y=0.0):
    px = np.mod(x + float(phase_x), float(period_x)) - float(period_x) * 0.5
    py = np.mod(y + float(phase_y), float(period_y)) - float(period_y) * 0.5
    rr = float(radius) * float(radius)
    return np.clip(1.0 - (px * px + py * py) / max(rr, 1e-6), 0, 1).astype(np.float32)


def _spb_fast_spec_pattern(name, style):
    def _fast(shape, seed=0, sm=1.0, **kwargs):
        h, w = shape[:2] if len(shape) > 2 else shape
        if sm < 0.001:
            return _flat((h, w))
        rng = np.random.default_rng((_spb_catalog_seed(name) ^ int(seed) * 2654435761) & 0xFFFFFFFF)
        y = np.arange(h, dtype=np.float32)[:, np.newaxis]
        x = np.arange(w, dtype=np.float32)[np.newaxis, :]
        base = np.zeros((h, w), dtype=np.float32)
        grain = _spb_fast_hash_grid((h, w), seed + _spb_catalog_seed(name))

        if style == "tire_rubber_transfer":
            base.fill(0.50)
            for _ in range(46):
                pts = []
                cx = rng.uniform(w * 0.10, w * 0.90)
                cy = rng.uniform(h * 0.18, h * 0.86)
                length = rng.uniform(w * 0.18, w * 0.52)
                bow = rng.uniform(-h * 0.08, h * 0.08)
                angle = rng.uniform(-0.22, 0.22)
                for t in np.linspace(-0.5, 0.5, 18):
                    px = cx + t * length
                    py = cy + bow * (t * t - 0.25)
                    rx = (px - cx) * np.cos(angle) - (py - cy) * np.sin(angle) + cx
                    ry = (px - cx) * np.sin(angle) + (py - cy) * np.cos(angle) + cy
                    pts.append([int(np.clip(rx, 0, w - 1)), int(np.clip(ry, 0, h - 1))])
                if _CV2_OK:
                    _cv2.polylines(base, [np.asarray(pts, dtype=np.int32)], False, float(rng.uniform(0.05, 0.32)), int(rng.integers(1, 4)), lineType=_cv2.LINE_AA)
            base -= (grain > 0.985).astype(np.float32) * 0.10

        elif style == "mother_of_pearl_inlay":
            cell = 38.0
            qx = np.floor((x + y * 0.28) / cell)
            qy = np.floor((y - x * 0.16) / (cell * 0.78))
            cell_hash = np.mod(qx * 17.0 + qy * 31.0 + float(seed % 251), 19.0) / 18.0
            seams = np.maximum(_spb_fast_line_distance(x + y * 0.28, cell, 1.3, seed), _spb_fast_line_distance(y - x * 0.16, cell * 0.78, 1.3, seed * 0.37))
            nacre = np.sin((x * 0.032 + y * 0.021) + cell_hash * 4.8) * 0.5 + 0.5
            base = seams * 0.60 + nacre * 0.28 + cell_hash * 0.22 + (grain > 0.982).astype(np.float32) * 0.18

        elif style == "meteor_impact":
            base.fill(0.42)
            for _ in range(7):
                cx = int(rng.integers(0, w))
                cy = int(rng.integers(0, h))
                radius = int(rng.integers(max(8, min(h, w) // 38), max(16, min(h, w) // 10)))
                if _CV2_OK:
                    _cv2.circle(base, (cx, cy), radius, float(rng.uniform(0.72, 1.0)), 1, lineType=_cv2.LINE_AA)
                    _cv2.circle(base, (cx, cy), max(2, radius // 4), float(rng.uniform(0.08, 0.24)), -1, lineType=_cv2.LINE_AA)
                    for _ray in range(9):
                        ang = rng.uniform(0, np.pi * 2)
                        x2 = cx + np.cos(ang) * radius * rng.uniform(1.2, 2.8)
                        y2 = cy + np.sin(ang) * radius * rng.uniform(1.2, 2.8)
                        _cv2.line(base, (cx, cy), (int(np.clip(x2, 0, w - 1)), int(np.clip(y2, 0, h - 1))), float(rng.uniform(0.35, 0.88)), 1, lineType=_cv2.LINE_AA)
            base += (grain > 0.992).astype(np.float32) * 0.25

        elif style == "acid_etch":
            directional = _spb_fast_line_distance(x + y * 0.22, 27.0, 2.2, seed)
            pitted = (grain > 0.78).astype(np.float32)
            if _CV2_OK:
                pitted = _cv2.GaussianBlur(pitted, (0, 0), 1.2)
            base = directional * 0.34 + pitted * 0.46 + _spb_fast_line_distance(x - y * 0.51, 73.0, 1.1, seed * 0.7) * 0.22

        elif style == "rust_bloom":
            bloom = (grain > 0.935).astype(np.float32)
            if _CV2_OK:
                bloom = _cv2.GaussianBlur(bloom, (0, 0), 3.0)
            veins = np.maximum(_spb_fast_line_distance(x + y * 0.33, 61.0, 1.4, seed), _spb_fast_line_distance(x - y * 0.41, 79.0, 1.0, seed * 0.31))
            base = bloom * 0.62 + veins * 0.30 + (grain > 0.985).astype(np.float32) * 0.20

        elif style == "spec_shot_peened":
            pits = (grain > 0.915).astype(np.float32)
            if _CV2_OK:
                pits = np.maximum(pits, _cv2.GaussianBlur(pits, (0, 0), 0.75) * 0.65)
            base = pits * 0.72 + (grain > 0.985).astype(np.float32) * 0.22

        elif style == "engraved_crosshatch":
            a = _spb_fast_line_distance(x + y * 0.58, 16.0, 0.85, seed)
            b = _spb_fast_line_distance(x - y * 0.62, 18.0, 0.85, seed * 0.29)
            c = _spb_fast_line_distance(x, 96.0, 1.2, seed)
            base = np.maximum(a, b) * 0.78 + c * 0.18 + grain * 0.08

        elif style == "wax_streak_polish":
            base.fill(0.48)
            for _ in range(34):
                y0 = int(rng.integers(0, h))
                x0 = int(rng.integers(0, max(1, w // 4)))
                x1 = int(rng.integers(max(2, w // 2), w))
                wob = int(rng.integers(-max(2, h // 80), max(3, h // 80)))
                if _CV2_OK:
                    _cv2.line(base, (x0, y0), (x1, int(np.clip(y0 + wob, 0, h - 1))), float(rng.uniform(0.58, 0.92)), int(rng.integers(1, 3)), lineType=_cv2.LINE_AA)
            base += _spb_fast_line_distance(y, 13.0, 0.45, seed) * 0.12 + grain * 0.05

        elif style == "flow_lines":
            wave = y + np.sin(x * 0.021 + seed * 0.013) * 13.0 + np.sin(x * 0.007 - seed * 0.017) * 31.0
            base = _spb_fast_line_distance(wave, 34.0, 1.15, seed) * 0.76
            base += _spb_fast_line_distance(wave + x * 0.035, 89.0, 0.9, seed * 0.21) * 0.28 + grain * 0.06

        elif style == "oil_streak_panel":
            base.fill(0.48)
            for _ in range(22):
                x0 = int(rng.integers(0, w))
                y0 = int(rng.integers(0, max(1, h // 3)))
                length = int(rng.integers(max(8, h // 10), max(12, h // 2)))
                lean = int(rng.integers(-max(2, w // 24), max(3, w // 24)))
                if _CV2_OK:
                    _cv2.line(base, (x0, y0), (int(np.clip(x0 + lean, 0, w - 1)), int(np.clip(y0 + length, 0, h - 1))), float(rng.uniform(0.18, 0.42)), int(rng.integers(1, 4)), lineType=_cv2.LINE_AA)
            smear = _spb_fast_line_distance(x + y * 0.11, 67.0, 2.0, seed) * 0.16
            base += smear - (grain > 0.985).astype(np.float32) * 0.08

        elif style == "copper_patina_drip":
            base.fill(0.46)
            for _ in range(32):
                x0 = int(rng.integers(0, w))
                y0 = int(rng.integers(0, h))
                length = int(rng.integers(max(6, h // 30), max(12, h // 5)))
                if _CV2_OK:
                    _cv2.line(base, (x0, y0), (int(np.clip(x0 + rng.integers(-4, 5), 0, w - 1)), int(np.clip(y0 + length, 0, h - 1))), float(rng.uniform(0.62, 0.95)), int(rng.integers(1, 3)), lineType=_cv2.LINE_AA)
                    _cv2.circle(base, (x0, y0), int(rng.integers(2, 7)), float(rng.uniform(0.54, 0.88)), -1, lineType=_cv2.LINE_AA)
            base += (grain > 0.955).astype(np.float32) * 0.22 + _spb_fast_line_distance(y, 43.0, 1.1, seed) * 0.14

        elif style in {"sponsor_deboss", "sponsor_emboss"}:
            base.fill(0.50)
            sign = -1.0 if style == "sponsor_deboss" else 1.0
            for _ in range(16):
                x0 = int(rng.integers(0, max(1, int(w * 0.82))))
                y0 = int(rng.integers(0, max(1, int(h * 0.86))))
                rw = int(rng.integers(max(8, w // 32), max(12, w // 8)))
                rh = int(rng.integers(max(5, h // 44), max(9, h // 10)))
                x1 = min(w - 1, x0 + rw)
                y1 = min(h - 1, y0 + rh)
                val = 0.5 + sign * float(rng.uniform(0.18, 0.38))
                if _CV2_OK:
                    _cv2.rectangle(base, (x0, y0), (x1, y1), val, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(base, (x0, (y0 + y1) // 2), (x1, (y0 + y1) // 2), 0.5 + sign * 0.12, 1, lineType=_cv2.LINE_AA)
                    _cv2.line(base, ((x0 + x1) // 2, y0), ((x0 + x1) // 2, y1), 0.5 - sign * 0.10, 1, lineType=_cv2.LINE_AA)
            base += (grain - 0.5) * 0.10

        elif style == "banded_rows":
            row = _spb_fast_line_distance(y, 28.0, 5.5, seed)
            fine_rows = _spb_fast_line_distance(y, 7.0, 0.65, seed * 0.19)
            base = row * 0.64 + fine_rows * 0.24 + _spb_fast_line_distance(x + y * 0.05, 93.0, 1.0, seed) * 0.12

        elif style == "mud_splatter_random":
            base.fill(0.46)
            splats = (grain > 0.965).astype(np.float32)
            if _CV2_OK:
                splats = np.maximum(splats, _cv2.GaussianBlur(splats, (0, 0), 1.6) * 0.78)
            gravity = (y / max(h - 1, 1)) ** 1.35
            base += splats * (0.30 + gravity * 0.34) + (grain > 0.992).astype(np.float32) * 0.18

        elif style == "spray_paint_drip":
            base.fill(0.48)
            mist = (grain > 0.90).astype(np.float32)
            if _CV2_OK:
                mist = _cv2.GaussianBlur(mist, (0, 0), 0.9)
            for _ in range(28):
                x0 = int(rng.integers(0, w))
                y0 = int(rng.integers(0, h))
                if _CV2_OK:
                    _cv2.line(base, (x0, y0), (int(np.clip(x0 + rng.integers(-3, 4), 0, w - 1)), int(np.clip(y0 + rng.integers(h // 40, max(h // 7, h // 40 + 1)), 0, h - 1))), float(rng.uniform(0.62, 0.94)), 1, lineType=_cv2.LINE_AA)
            base += mist * 0.26

        elif style == "electroformed":
            cells = np.maximum(_spb_fast_line_distance(x + y * 0.37, 31.0, 1.1, seed), _spb_fast_line_distance(x - y * 0.52, 43.0, 1.1, seed * 0.43))
            nodules = (grain > 0.965).astype(np.float32)
            if _CV2_OK:
                nodules = np.maximum(nodules, _cv2.GaussianBlur(nodules, (0, 0), 0.85) * 0.62)
            base = cells * 0.46 + nodules * 0.40 + grain * 0.10

        elif style == "hand_polished":
            arcs = _spb_fast_line_distance(x + np.sin(y * 0.018 + seed) * 18.0, 52.0, 1.0, seed)
            swirls = _spb_fast_line_distance(np.sqrt((x - w * 0.5) ** 2 + (y - h * 0.5) ** 2), 19.0, 0.8, seed)
            base = arcs * 0.48 + swirls * 0.32 + grain * 0.08

        elif style == "electroplated_chrome":
            bath = _spb_fast_line_distance(x + np.sin(y * 0.014 + seed) * 22.0, 47.0, 0.9, seed)
            current = _spb_fast_line_distance(y - x * 0.18, 89.0, 0.75, seed * 0.31)
            pinholes = (grain > 0.986).astype(np.float32)
            base = bath * 0.42 + current * 0.26 + pinholes * 0.22 + 0.46

        elif style == "xirallic_crystal":
            facets = np.maximum(
                np.maximum(_spb_fast_line_distance(x + y * 0.41, 29.0, 0.95, seed), _spb_fast_line_distance(x - y * 0.63, 37.0, 0.9, seed * 0.23)),
                _spb_fast_line_distance(x * 0.18 + y, 43.0, 0.8, seed * 0.57),
            )
            flashes = (grain > 0.976).astype(np.float32)
            base = facets * 0.48 + flashes * 0.34 + grain * 0.08 + 0.38

        elif style == "pvd_coating":
            vapor = _spb_fast_line_distance(y + np.sin(x * 0.015 + seed) * 18.0, 53.0, 1.0, seed)
            ion = _spb_fast_line_distance(x - y * 0.28, 71.0, 0.85, seed * 0.47)
            base = vapor * 0.40 + ion * 0.28 + (grain > 0.982).astype(np.float32) * 0.18 + 0.44

        elif style == "quantum_noise":
            packets = (grain > 0.91).astype(np.float32)
            fringes = _spb_fast_line_distance(x + np.sin(y * 0.023 + seed) * 9.0, 17.0, 0.55, seed)
            anti = _spb_fast_line_distance(y - np.sin(x * 0.019 - seed) * 11.0, 23.0, 0.5, seed * 0.37)
            base = packets * 0.28 + fringes * 0.34 + anti * 0.24 + 0.40

        elif style in {"tape_residue", "sponsor_tape_vinyl"}:
            base.fill(0.48)
            for _ in range(22):
                y0 = int(rng.integers(0, h))
                x0 = int(rng.integers(0, max(1, w // 3)))
                x1 = int(rng.integers(max(2, w // 2), w))
                wob = int(rng.integers(-max(2, h // 60), max(3, h // 60)))
                val = float(rng.uniform(0.18, 0.40) if style == "tape_residue" else rng.uniform(0.58, 0.86))
                if _CV2_OK:
                    _cv2.line(base, (x0, y0), (x1, int(np.clip(y0 + wob, 0, h - 1))), val, int(rng.integers(1, 4)), lineType=_cv2.LINE_AA)
            base += _spb_fast_line_distance(x + y * 0.09, 83.0, 0.8, seed) * 0.12 + (grain - 0.5) * 0.08

        elif style == "aerogel_surface":
            pores = (grain > 0.945).astype(np.float32)
            web = np.maximum(_spb_fast_line_distance(x + y * 0.27, 31.0, 0.65, seed), _spb_fast_line_distance(x - y * 0.39, 43.0, 0.55, seed * 0.29))
            if _CV2_OK:
                pores = _cv2.GaussianBlur(pores, (0, 0), 0.75)
            base = pores * 0.42 + web * 0.30 + 0.42

        elif style == "coral_reef":
            pores = _spb_fast_dots_px(x + y * 0.13, y, 23.0, 19.0, 2.2, seed, seed * 0.41)
            ridges = np.maximum(_spb_fast_line_distance(x + y * 0.36, 47.0, 0.9, seed), _spb_fast_line_distance(y, 61.0, 0.8, seed * 0.33))
            base = pores * 0.46 + ridges * 0.28 + (grain > 0.982).astype(np.float32) * 0.18 + 0.36

        elif style == "oxidized_pitting":
            pits = (grain > 0.935).astype(np.float32)
            stains = _spb_fast_line_distance(y + np.sin(x * 0.012 + seed) * 20.0, 67.0, 1.6, seed)
            if _CV2_OK:
                pits = np.maximum(pits, _cv2.GaussianBlur(pits, (0, 0), 1.0) * 0.60)
            base = 0.44 - pits * 0.26 + stains * 0.22 + (grain > 0.99).astype(np.float32) * 0.12

        elif style == "terrain_erosion":
            terrain = np.sin(x * 0.018 + np.sin(y * 0.009 + seed) * 2.2) + np.sin(y * 0.016 - seed * 0.01)
            contour = _spb_fast_line_distance(terrain * 64.0, 9.0, 0.7, seed)
            gullies = _spb_fast_line_distance(x + y * 0.22, 97.0, 0.8, seed * 0.21)
            base = contour * 0.50 + gullies * 0.22 + grain * 0.08 + 0.38

        elif style == "carbon_wet_layup":
            weave_a = _spb_fast_line_distance(x + y * 0.19, 14.0, 0.65, seed)
            weave_b = _spb_fast_line_distance(y - x * 0.19, 14.0, 0.65, seed * 0.31)
            resin = _spb_fast_line_distance(x + np.sin(y * 0.017 + seed) * 12.0, 89.0, 1.2, seed)
            base = np.maximum(weave_a, weave_b) * 0.46 + resin * 0.22 + (grain > 0.987).astype(np.float32) * 0.15 + 0.40

        elif style == "chameleon_flake":
            flakes = (grain > 0.955).astype(np.float32)
            prism = _spb_fast_line_distance(x + y * 0.31 + np.sin(y * 0.015 + seed) * 16.0, 31.0, 0.8, seed)
            base = flakes * 0.44 + prism * 0.32 + _spb_fast_line_distance(y, 79.0, 0.7, seed * 0.17) * 0.14 + 0.38

        elif style == "stone_granite":
            chips = (grain > 0.82).astype(np.float32) * 0.20 + (grain > 0.965).astype(np.float32) * 0.28
            veins = np.maximum(_spb_fast_line_distance(x + y * 0.43, 89.0, 0.9, seed), _spb_fast_line_distance(x - y * 0.26, 131.0, 0.8, seed * 0.51))
            base = chips + veins * 0.24 + 0.36

        elif style == "wet_zone":
            puddles = (np.sin(x * 0.014 + seed) + np.sin(y * 0.018 - seed * 0.2) + np.sin((x + y) * 0.009)) / 3.0
            edges = _spb_fast_line_distance(puddles * 120.0, 17.0, 1.2, seed)
            gloss = _spb_fast_line_distance(x + np.sin(y * 0.011) * 21.0, 113.0, 1.0, seed)
            base = edges * 0.44 + gloss * 0.22 + (grain > 0.992).astype(np.float32) * 0.12 + 0.42

        elif style == "brake_dust_buildup":
            gravity = (y / max(h - 1, 1)) ** 1.4
            dust = (grain > (0.82 - gravity * 0.10)).astype(np.float32)
            streaks = _spb_fast_line_distance(y - x * 0.05, 47.0, 1.2, seed)
            base = 0.50 - dust * (0.20 + gravity * 0.18) + streaks * 0.12

        elif style == "subsurface_depth":
            depth = np.sin(x * 0.017 + np.sin(y * 0.010 + seed) * 2.6) + np.sin(y * 0.021 - seed * 0.01)
            membranes = _spb_fast_line_distance(depth * 72.0, 13.0, 0.9, seed)
            pores = (grain > 0.968).astype(np.float32)
            base = 0.42 + membranes * 0.36 + pores * 0.16

        elif style == "gold_leaf_torn":
            seams = np.maximum(_spb_fast_line_distance(x + y * 0.41, 57.0, 1.0, seed), _spb_fast_line_distance(x - y * 0.27, 83.0, 0.9, seed * 0.33))
            flakes = (grain > 0.90).astype(np.float32)
            torn = (_spb_fast_hash_grid((max(1, h // 8), max(1, w // 8)), seed) > 0.55).astype(np.float32)
            if _CV2_OK:
                torn = _cv2.resize(torn, (w, h), interpolation=_cv2.INTER_NEAREST)
            base = 0.40 + torn * 0.28 + seams * 0.30 + flakes * 0.12

        elif style == "iridescent_film":
            bands = _spb_fast_line_distance(x + np.sin(y * 0.012 + seed) * 30.0, 39.0, 1.0, seed)
            oil = _spb_fast_line_distance(y - np.sin(x * 0.015 - seed) * 22.0, 53.0, 0.8, seed * 0.41)
            pin = (grain > 0.988).astype(np.float32)
            base = 0.44 + bands * 0.30 + oil * 0.24 + pin * 0.12

        elif style == "cloud_wisps":
            wisps = _spb_fast_line_distance(y + np.sin(x * 0.012 + seed) * 42.0 + np.sin(x * 0.004) * 80.0, 93.0, 1.8, seed)
            inner = _spb_fast_line_distance(x + y * 0.16, 121.0, 0.8, seed * 0.22)
            base = 0.43 + wisps * 0.36 + inner * 0.14 + grain * 0.04

        elif style == "light_leak":
            rays = _spb_fast_line_distance(x - y * 0.28, 111.0, 1.1, seed)
            bloom = np.clip(1.0 - np.sqrt((x - w * 0.12) ** 2 + (y - h * 0.18) ** 2) / max(h, w) * 2.4, 0, 1)
            scan = _spb_fast_line_distance(y, 31.0, 0.6, seed)
            base = 0.42 + rays * 0.26 + bloom * 0.24 + scan * 0.10

        elif style == "heat_discoloration":
            temper = _spb_fast_line_distance(y + np.sin(x * 0.011 + seed) * 26.0, 61.0, 1.1, seed)
            oxide = _spb_fast_line_distance(x + y * 0.12, 97.0, 0.8, seed * 0.31)
            base = 0.43 + temper * 0.34 + oxide * 0.18 + (grain > 0.986).astype(np.float32) * 0.12

        elif style == "salt_spray":
            crystals = (grain > 0.942).astype(np.float32)
            wind = _spb_fast_line_distance(x + y * 0.08, 43.0, 0.8, seed)
            crust = _spb_fast_line_distance(y + np.sin(x * 0.018) * 12.0, 67.0, 1.1, seed * 0.19)
            base = 0.42 + crystals * 0.30 + wind * 0.18 + crust * 0.18

        elif style == "sparkle_nebula":
            stars = (grain > 0.972).astype(np.float32)
            hot = (grain > 0.994).astype(np.float32)
            gas = np.sin(x * 0.013 + y * 0.017 + np.sin(y * 0.006 + seed) * 2.4) * 0.5 + 0.5
            lanes = _spb_fast_line_distance(x - y * 0.33, 139.0, 0.75, seed)
            base = 0.38 + stars * 0.36 + hot * 0.24 + gas * 0.16 + lanes * 0.14

        else:
            base = grain

        return _validate_spec_output(_sm_scale(_normalize(np.clip(base, 0, 1)), sm).astype(np.float32), name)

    _fast._spb_fast_spec_override = True
    _fast.__name__ = f"fast_{name}"
    return _fast


for _spb_fast_name, _spb_fast_style in {
    "tire_rubber_transfer": "tire_rubber_transfer",
    "mother_of_pearl_inlay": "mother_of_pearl_inlay",
    "meteor_impact": "meteor_impact",
    "acid_etch": "acid_etch",
    "rust_bloom": "rust_bloom",
    "spec_shot_peened": "spec_shot_peened",
    "engraved_crosshatch": "engraved_crosshatch",
    "wax_streak_polish": "wax_streak_polish",
    "flow_lines": "flow_lines",
    "oil_streak_panel": "oil_streak_panel",
    "copper_patina_drip": "copper_patina_drip",
    "sponsor_deboss": "sponsor_deboss",
    "sponsor_emboss_v2": "sponsor_emboss",
    "banded_rows": "banded_rows",
    "spec_rust_bloom": "rust_bloom",
    "mud_splatter_random": "mud_splatter_random",
    "spray_paint_drip": "spray_paint_drip",
    "spec_electroformed_texture": "electroformed",
    "hand_polished": "hand_polished",
    "spec_electroplated_chrome": "electroplated_chrome",
    "spec_xirallic_crystal": "xirallic_crystal",
    "spec_pvd_coating": "pvd_coating",
    "quantum_noise": "quantum_noise",
    "sponsor_tape_vinyl": "sponsor_tape_vinyl",
    "racing_tape_residue": "tape_residue",
    "spec_aerogel_surface": "aerogel_surface",
    "spec_coral_reef": "coral_reef",
    "spec_oxidized_pitting": "oxidized_pitting",
    "spec_terrain_erosion": "terrain_erosion",
    "spec_carbon_wet_layup": "carbon_wet_layup",
    "spec_chameleon_flake": "chameleon_flake",
    "spec_stone_granite": "stone_granite",
    "cc_wet_zone": "wet_zone",
    "brake_dust_buildup": "brake_dust_buildup",
    "spec_subsurface_depth": "subsurface_depth",
    "gold_leaf_torn": "gold_leaf_torn",
    "spec_iridescent_film": "iridescent_film",
    "cloud_wisps_warm": "cloud_wisps",
    "spec_light_leak": "light_leak",
    "heat_discoloration": "heat_discoloration",
    "salt_spray_corrosion": "salt_spray",
    "sparkle_nebula": "sparkle_nebula",
}.items():
    if _spb_fast_name in PATTERN_CATALOG:
        _spb_old_fn = PATTERN_CATALOG[_spb_fast_name]
        _spb_new_fn = _spb_fast_spec_pattern(_spb_fast_name, _spb_fast_style)
        _spb_new_fn.__doc__ = getattr(_spb_old_fn, "__doc__", None)
        _spb_new_fn.__module__ = getattr(_spb_old_fn, "__module__", __name__)
        PATTERN_CATALOG[_spb_fast_name] = _spb_new_fn


def _spb_wrap_bespoke_spec_overlay(name, style, old_fn):
    def _wrapped(shape, seed=0, sm=1.0, **kwargs):
        h, w = shape[:2] if len(shape) > 2 else shape
        if sm < 0.001:
            return _flat((h, w))
        try:
            raw = old_fn((h, w), seed=seed, sm=1.0, **kwargs)
        except TypeError:
            raw = old_fn((h, w), seed, 1.0)
        if isinstance(raw, tuple):
            raw = raw[0]
        base = np.asarray(raw, dtype=np.float32)
        if base.ndim == 3:
            base = base[:, :, 0]
        base = _normalize(base)

        catalog_seed = _spb_catalog_seed(name)
        grain = _spb_fast_hash_grid((h, w), seed + catalog_seed)
        y = np.arange(h, dtype=np.float32)[:, np.newaxis]
        x = np.arange(w, dtype=np.float32)[np.newaxis, :]
        xf = x / max(w - 1, 1)
        yf = y / max(h - 1, 1)
        micro_cross = np.maximum(
            _spb_fast_line_distance(x + y * 0.31, 9.0 + (catalog_seed % 5), 0.48, seed),
            _spb_fast_line_distance(x - y * 0.43, 13.0 + (catalog_seed % 7), 0.42, seed * 0.37),
        )

        if style == "rain":
            columns = _spb_fast_line_distance(x + np.sin(y * 0.115 + seed) * 2.2, 11.0, 0.46, seed)
            heads = (grain > 0.935).astype(np.float32)
            tails = _spb_fast_line_distance(y + grain * 10.0, 17.0, 1.0, seed * 0.29) * columns
            out = base * 0.50 + columns * 0.22 + tails * 0.22 + heads * 0.30 + micro_cross * 0.16
        elif style == "flake":
            tiny = (grain > 0.905).astype(np.float32) * 0.30
            hot = (grain > 0.976).astype(np.float32) * 0.50
            facets = np.maximum(
                _spb_fast_line_distance(x + y * 0.19, 7.0, 0.38, seed),
                _spb_fast_line_distance(x - y * 0.27, 11.0, 0.34, seed * 0.23),
            )
            out = base * 0.34 + tiny + hot + facets * 0.28 + micro_cross * 0.14
        elif style == "galaxy":
            cx = w * (0.47 + ((catalog_seed % 17) - 8) * 0.002)
            cy = h * (0.51 + ((catalog_seed % 13) - 6) * 0.002)
            dx = (x - cx) / max(w, 1)
            dy = (y - cy) / max(h, 1)
            radius = np.sqrt(dx * dx + dy * dy)
            angle = np.arctan2(dy, dx)
            arms = _spb_fast_line_distance((angle + radius * 21.0) * 34.0, 19.0, 0.72, seed)
            stars = (grain > 0.958).astype(np.float32) * (0.35 + np.clip(1.0 - radius * 1.8, 0, 1) * 0.35)
            dust = _spb_fast_line_distance(x - y * 0.14, 23.0, 0.55, seed * 0.41)
            out = base * 0.42 + arms * 0.34 + stars + dust * 0.18 + micro_cross * 0.12
        elif style == "electric":
            field_a = _spb_fast_line_distance(x + np.sin(y * 0.048 + seed) * 8.0, 15.0, 0.55, seed)
            field_b = _spb_fast_line_distance(y - np.sin(x * 0.052 - seed) * 8.0, 19.0, 0.50, seed * 0.33)
            sparks = (grain > 0.963).astype(np.float32) * 0.38
            corona = np.maximum(field_a, field_b)
            out = base * 0.42 + corona * 0.42 + sparks + micro_cross * 0.18
        elif style == "masking_edge":
            tape_fibers = _spb_fast_line_distance(x + y * 0.06, 8.0, 0.40, seed)
            overspray = (grain > 0.86).astype(np.float32) * 0.14 + (grain > 0.976).astype(np.float32) * 0.28
            edge = np.clip(np.abs(base - np.roll(base, 1, axis=0)) + np.abs(base - np.roll(base, 1, axis=1)), 0, 1)
            out = base * 0.64 + tape_fibers * 0.22 + overspray + edge * 0.26 + micro_cross * 0.12
        elif style == "panel_fade":
            spray = (grain > 0.80).astype(np.float32) * 0.12 + (grain > 0.965).astype(np.float32) * 0.28
            peel = np.sin(x * 1.71 + np.sin(y * 0.39 + seed) * 1.4) * np.sin(y * 1.37 - x * 0.11)
            peel = (peel * 0.5 + 0.5).astype(np.float32)
            fan = _spb_fast_line_distance(x * np.cos(seed * 0.01) + y * np.sin(seed * 0.01), 37.0, 0.78, seed)
            out = base * 0.60 + spray + peel * 0.16 + fan * 0.18 + micro_cross * 0.12
        elif style == "drip_edge":
            sag = np.clip((yf - 0.58) / 0.42, 0, 1)
            curtains = _spb_fast_line_distance(x + np.sin(y * 0.079 + seed) * 5.0, 12.0, 0.55, seed)
            beads = (grain > (0.94 - sag * 0.08)).astype(np.float32) * (0.22 + sag * 0.30)
            horizontal_ridges = _spb_fast_line_distance(y + np.sin(x * 0.033) * 6.0, 9.0, 0.45, seed * 0.31)
            out = base * 0.50 + curtains * sag * 0.34 + horizontal_ridges * sag * 0.28 + beads + micro_cross * 0.12
        elif style == "hex":
            micro_cells = np.maximum(
                _spb_fast_line_distance(x + y * 0.50, 8.0, 0.38, seed),
                _spb_fast_line_distance(x - y * 0.50, 8.0, 0.38, seed * 0.29),
            )
            stipple = (grain > 0.88).astype(np.float32) * 0.16 + (grain > 0.975).astype(np.float32) * 0.34
            edge = np.clip(np.abs(base - np.roll(base, 1, axis=0)) + np.abs(base - np.roll(base, 1, axis=1)), 0, 1)
            out = base * 0.58 + micro_cells * 0.24 + stipple + edge * 0.22 + micro_cross * 0.13
        else:
            out = base * 0.70 + micro_cross * 0.30 + (grain > 0.965).astype(np.float32) * 0.18

        return _validate_spec_output(_sm_scale(_normalize(np.clip(out, 0, 1)), sm).astype(np.float32), name)

    _wrapped.__name__ = getattr(old_fn, "__name__", f"spec_{name}")
    _wrapped.__doc__ = getattr(old_fn, "__doc__", None)
    _wrapped.__module__ = getattr(old_fn, "__module__", __name__)
    _wrapped._spb_bespoke_spec_overlay = True
    return _wrapped


for _spb_detail_name, _spb_detail_style in {
    "sparkle_rain": "rain",
    "spec_sparkle_flake": "flake",
    "sparkle_galaxy_swirl": "galaxy",
    "sparkle_electric_field": "electric",
    "cc_masking_edge": "masking_edge",
    "cc_panel_fade": "panel_fade",
    "paint_drip_edge": "drip_edge",
    "hex_cells": "hex",
}.items():
    if _spb_detail_name in PATTERN_CATALOG:
        PATTERN_CATALOG[_spb_detail_name] = _spb_wrap_bespoke_spec_overlay(
            _spb_detail_name,
            _spb_detail_style,
            PATTERN_CATALOG[_spb_detail_name],
        )

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
