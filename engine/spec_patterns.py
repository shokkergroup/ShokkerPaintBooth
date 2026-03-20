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

    result = np.zeros(shape, dtype=np.float32)
    wsum = np.zeros(shape, dtype=np.float32)
    for b in range(num_bands):
        wb = np.exp(-((eff_y - band_centers[b]) ** 2) / (2.0 * feather_px ** 2))
        result += wb * band_values[b]
        wsum += wb
    result /= np.maximum(wsum, 1e-6)

    return _sm_scale(result, sm).astype(np.float32)


# ============================================================================
# 2. FLAKE SCATTER — sparse metallic flake particles
# ============================================================================

def flake_scatter(shape, seed, sm, density=0.02, flake_radius=2,
                  intensity_range=(0.3, 1.0)):
    """
    Sparse bright spots simulating metallic flake particles.
    Uses vectorized stamp placement for performance.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    eff_density = density * sm
    num_flakes = min(int(h * w * eff_density), 50000)
    if num_flakes < 1:
        return _flat(shape)

    fy = rng.randint(0, h, size=num_flakes)
    fx = rng.randint(0, w, size=num_flakes)
    lo, hi = intensity_range
    intensities = rng.uniform(lo, hi, size=num_flakes).astype(np.float32)

    result = _flat(shape)
    r = max(1, int(flake_radius))
    for i in range(num_flakes):
        y, x = int(fy[i]), int(fx[i])
        y0, y1 = max(0, y - r), min(h, y + r + 1)
        x0, x1 = max(0, x - r), min(w, x + r + 1)
        yy = np.arange(y0, y1, dtype=np.float32) - y
        xl = np.arange(x0, x1, dtype=np.float32) - x
        dsq = yy[:, np.newaxis]**2 + xl[np.newaxis, :]**2
        falloff = np.clip(1.0 - dsq / (r*r + 0.1), 0, 1)
        stamp = 0.5 + (intensities[i] - 0.5) * falloff * sm
        result[y0:y1, x0:x1] = np.maximum(result[y0:y1, x0:x1], stamp)

    return result.astype(np.float32)


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
    Edges between cells are visible as transitions.
    Good for: carbon fiber hex, metallic hex flake, scale patterns.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    cs = max(4, cell_size)
    # Hex grid dimensions
    ny = max(2, int(h / (cs * 0.866)) + 2)
    nx = max(2, int(w / cs) + 2)

    # Cell center values
    cell_vals = rng.uniform(0.2, 0.8, size=(ny, nx)).astype(np.float32)

    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)

    # Hex grid: offset every other row
    row_h = cs * 0.866  # sqrt(3)/2
    result = np.zeros(shape, dtype=np.float32)
    min_dist = np.full(shape, 1e6, dtype=np.float32)
    nearest_val = np.full(shape, 0.5, dtype=np.float32)

    # Check nearest hex center for each pixel (vectorized per center)
    for iy in range(ny):
        for ix in range(nx):
            cy = iy * row_h
            cx = ix * cs + (cs * 0.5 if iy % 2 else 0)
            dy = (yy[:, np.newaxis] - cy) / row_h
            dx = (xx[np.newaxis, :] - cx) / cs
            d = dy**2 + dx**2
            closer = d < min_dist
            nearest_val = np.where(closer, cell_vals[iy % ny, ix % nx], nearest_val)
            min_dist = np.minimum(min_dist, d)

    # Edge detection: where distance to center is high = edge zone
    edge_factor = np.clip(min_dist / (edge_width + 0.01), 0, 1)
    # Blend between cell value and edge value (edges trend toward 0.3)
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
        # 2D value noise approximation via sin products
        n = (np.sin(yy[:, np.newaxis] * freq * np.pi * 2 + a1) *
             np.sin(xx[np.newaxis, :] * freq * np.pi * 2 + a2) * 0.5 +
             np.sin(yy[:, np.newaxis] * freq * np.pi * 1.7 + a3) *
             np.cos(xx[np.newaxis, :] * freq * np.pi * 2.3 + a4) * 0.5)
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
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    # Zone centers and values
    zone_vals = rng.uniform(0.15, 0.85, size=num_zones).astype(np.float32)
    zone_cy = rng.uniform(0.1, 0.9, size=num_zones)
    zone_cx = rng.uniform(0.1, 0.9, size=num_zones)

    # For each pixel, find nearest zone (Voronoi)
    min_dist = np.full(shape, 1e6, dtype=np.float32)
    second_dist = np.full(shape, 1e6, dtype=np.float32)
    nearest = np.zeros(shape, dtype=np.float32)

    for z in range(num_zones):
        d = np.sqrt(((yy[:, np.newaxis] - zone_cy[z]) * 2)**2 +
                     ((xx[np.newaxis, :] - zone_cx[z]) * 2)**2)
        closer = d < min_dist
        # Update second-nearest before nearest
        second_dist = np.where(closer, min_dist, np.minimum(second_dist, d))
        nearest = np.where(closer, zone_vals[z], nearest)
        min_dist = np.where(closer, d, min_dist)

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

    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    d1 = np.full(shape, 1e6, dtype=np.float32)
    d2 = np.full(shape, 1e6, dtype=np.float32)
    nearest = np.zeros(shape, dtype=np.float32)

    for i in range(n):
        d = np.sqrt(((yy[:, np.newaxis] - cy[i]))**2 +
                     ((xx[np.newaxis, :] - cx[i]))**2)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        nearest = np.where(closer, cell_vals[i], nearest)
        d1 = np.where(closer, d, d1)

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
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    # Base flow direction (slightly diagonal)
    base_angle = rng.uniform(-0.3, 0.3)  # Near horizontal

    result = np.full(shape, 0.5, dtype=np.float32)
    for _ in range(num_streams):
        # Stream center line: y = start_y + curvature_fn(x)
        start_y = rng.uniform(0, 1)
        intensity = rng.uniform(0.3, 0.8)
        freq = rng.uniform(0.5, curvature)
        phase = rng.uniform(0, 2 * np.pi)
        amplitude = rng.uniform(0.02, 0.12)
        lw = line_width * rng.uniform(0.5, 2.0)

        # Stream path
        stream_y = start_y + np.sin(xx * freq * np.pi + phase) * amplitude + xx * np.tan(base_angle)
        # Distance from each pixel to stream path
        dist = np.abs(yy[:, np.newaxis] - stream_y[np.newaxis, :])
        # Stream profile: Gaussian cross-section
        stream = np.exp(-(dist ** 2) / (2 * lw ** 2))
        result = result + stream * (intensity - 0.5) * 0.5

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
    Large rounded bumps like leather grain, pebbled rubber, or
    hammered metal. Bigger and softer than orange_peel_texture.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    ps = max(4, pebble_size)
    # Use Voronoi-like approach: random centers, each pixel gets value
    # based on distance to nearest center
    n = max(8, (h * w) // (ps * ps))
    n = min(n, 2000)
    cy = rng.uniform(0, h, size=n).astype(np.float32)
    cx = rng.uniform(0, w, size=n).astype(np.float32)
    pebble_height = rng.uniform(0.3, 0.8, size=n).astype(np.float32)

    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)

    # Find nearest center and distance
    min_dist = np.full(shape, 1e6, dtype=np.float32)
    nearest_h = np.full(shape, 0.5, dtype=np.float32)

    for i in range(n):
        d = np.sqrt((yy[:, np.newaxis] - cy[i])**2 +
                     (xx[np.newaxis, :] - cx[i])**2)
        closer = d < min_dist
        nearest_h = np.where(closer, pebble_height[i], nearest_h)
        min_dist = np.where(closer, d, min_dist)

    # Pebble profile: rounded dome shape based on distance to center
    pebble_radius = ps * 0.6
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

    result = np.full(shape, 0.5, dtype=np.float32)
    for _ in range(num_blooms):
        cy, cx = rng.uniform(0, 1), rng.uniform(0, 1)
        radius = rng.uniform(min_radius, max_radius)
        intensity = rng.uniform(0.3, 0.9)
        # Ring vs solid: some blooms have bright edge, some are solid
        ring = rng.uniform(0, 1) > 0.5

        dist = np.sqrt(((yy[:, np.newaxis] - cy))**2 +
                        ((xx[np.newaxis, :] - cx))**2)

        if ring:
            # Ring bloom: bright at edge, fade inside and outside
            ring_dist = np.abs(dist - radius * 0.7) / (radius * 0.3 + 1e-6)
            bloom = np.exp(-ring_dist**2 * 2) * intensity
        else:
            # Solid bloom: bright at center, fade outward
            bloom = np.exp(-(dist / radius)**2) * intensity

        result = result + (bloom - 0.5) * 0.3

    return _sm_scale(_normalize(result), sm).astype(np.float32)


# ============================================================================
# 25. ELECTRIC BRANCHES — branching tree / Lichtenberg figures
# ============================================================================

def electric_branches(shape, seed, sm, num_trees=3, branch_depth=6,
                      thickness=0.008):
    """
    Branching tree/lightning patterns (Lichtenberg figures).
    Recursive branching from random root points.
    Simulates electrical discharge, frost crystals, or vein networks.
    """
    h, w = shape
    if sm < 0.001:
        return _flat(shape)

    rng = np.random.RandomState(seed)
    yy = np.arange(h, dtype=np.float32) / h
    xx = np.arange(w, dtype=np.float32) / w

    result = np.full(shape, 0.3, dtype=np.float32)

    def _draw_branch(y0, x0, angle, length, depth, intensity):
        """Draw a branch as a line with falloff and spawn sub-branches."""
        if depth <= 0 or length < 0.005:
            return
        # End point
        y1 = y0 + np.sin(angle) * length
        x1 = x0 + np.cos(angle) * length

        # Distance from each pixel to the line segment
        # Parameterize: P = (y0,x0) + t*(dy,dx), t clamped to [0,1]
        dy, dx = y1 - y0, x1 - x0
        seg_len = max(np.sqrt(dy**2 + dx**2), 1e-6)

        t = ((yy[:, np.newaxis] - y0) * dy + (xx[np.newaxis, :] - x0) * dx) / (seg_len**2)
        t = np.clip(t, 0, 1)
        closest_y = y0 + t * dy
        closest_x = x0 + t * dx
        dist = np.sqrt((yy[:, np.newaxis] - closest_y)**2 +
                        (xx[np.newaxis, :] - closest_x)**2)

        # Glow around branch
        thick = thickness * (depth / branch_depth)  # Thinner for deeper branches
        glow = np.exp(-(dist / max(thick, 0.001))**2) * intensity
        result[:] = np.maximum(result, 0.3 + glow * 0.7)

        # Spawn sub-branches
        num_children = rng.randint(1, 4)
        for _ in range(num_children):
            child_angle = angle + rng.uniform(-0.8, 0.8)
            child_length = length * rng.uniform(0.4, 0.7)
            child_intensity = intensity * rng.uniform(0.5, 0.85)
            # Branch from a random point along parent
            branch_t = rng.uniform(0.3, 0.9)
            by = y0 + dy * branch_t
            bx = x0 + dx * branch_t
            _draw_branch(by, bx, child_angle, child_length, depth - 1, child_intensity)

    # Create trees from random root points
    for _ in range(num_trees):
        root_y = rng.uniform(0.2, 0.8)
        root_x = rng.uniform(0.2, 0.8)
        root_angle = rng.uniform(0, 2 * np.pi)
        root_length = rng.uniform(0.15, 0.35)
        _draw_branch(root_y, root_x, root_angle, root_length,
                     branch_depth, rng.uniform(0.6, 1.0))

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

    return np.clip(result, 0, 255).astype(np.float32)


# ============================================================================
# 26. VORONOI_FRACTURE — shattered glass cell boundaries
# ============================================================================

def voronoi_fracture(shape, seed, sm, num_cells=40, edge_width=2.0, **kwargs):
    """Voronoi tessellation with bright cell interiors and dark fracture edges."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    cx = rng.rand(num_cells) * w
    cy = rng.rand(num_cells) * h
    cell_vals = rng.rand(num_cells).astype(np.float32) * 0.6 + 0.2

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dists = np.full((2, h, w), 1e9, dtype=np.float32)
    closest = np.zeros((h, w), dtype=np.int32)

    for i in range(num_cells):
        d = np.sqrt((xx - cx[i])**2 + (yy - cy[i])**2)
        mask = d < dists[0]
        dists[1] = np.where(mask, dists[0], np.minimum(dists[1], d))
        closest = np.where(mask, i, closest)
        dists[0] = np.minimum(dists[0], d)

    edge = np.clip((dists[1] - dists[0]) / edge_width, 0, 1).astype(np.float32)
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
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    result = np.ones(shape, dtype=np.float32)

    for _ in range(blob_count):
        cx, cy = rng.rand() * w, rng.rand() * h
        rx, ry = rng.uniform(10, 60), rng.uniform(10, 60)
        angle = rng.uniform(0, np.pi)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        dx = (xx - cx) * cos_a + (yy - cy) * sin_a
        dy = -(xx - cx) * sin_a + (yy - cy) * cos_a
        d = (dx/rx)**2 + (dy/ry)**2
        depth = rng.uniform(0.3, 1.0)
        etch = np.exp(-d * 2.0) * depth * intensity
        # Noise at edges
        edge_noise = np.sin(dx * 0.3 + rng.uniform(0, 6.28)) * np.cos(dy * 0.4) * 0.15
        result -= etch + np.clip(edge_noise * np.exp(-d * 3.0), 0, 0.3)

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
    # Sprinkle star clusters
    stars = (rng.rand(h, w) > 0.997).astype(np.float32)
    star_glow = np.zeros_like(stars)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            star_glow += np.roll(np.roll(stars, dy, 0), dx, 1) * np.exp(-(dy**2 + dx**2) * 0.5)
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

    result = scale_bright * tilt
    return _sm_scale(_normalize(result), sm)


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

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Assign each pixel to nearest shard (Voronoi)
    closest = np.zeros((h, w), dtype=np.int32)
    min_dist = np.full((h, w), 1e9, dtype=np.float32)
    second_dist = np.full((h, w), 1e9, dtype=np.float32)
    for i in range(num_shards):
        d = (xx - cx[i])**2 + (yy - cy[i])**2
        mask = d < min_dist
        second_dist = np.where(mask, min_dist, np.minimum(second_dist, d))
        closest = np.where(mask, i, closest)
        min_dist = np.minimum(min_dist, d)

    # Angular gradient within each shard
    shard_angle = angles[closest]
    grad = np.sin((xx * np.cos(shard_angle) + yy * np.sin(shard_angle)) * 0.1) * 0.5 + 0.5

    # Edge darkening (fracture lines)
    edge = np.clip((np.sqrt(second_dist) - np.sqrt(min_dist)) / 3.0, 0, 1)

    result = shard_spec[closest] * (0.6 + 0.4 * grad) * edge
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 34. NEURAL_DENDRITE — branching neural network dendrites
# ============================================================================

def neural_dendrite(shape, seed, sm, num_neurons=5, branch_depth=7, **kwargs):
    """Branching neural dendrite trees — synaptic network visualization."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    result = np.zeros(shape, dtype=np.float32)

    def _draw_branch(x, y, angle, length, thickness, depth):
        if depth <= 0 or length < 2:
            return
        steps = int(length)
        for s in range(steps):
            px = int(x + s * np.cos(angle))
            py = int(y + s * np.sin(angle))
            r = max(1, int(thickness))
            for dy in range(-r, r+1):
                for dx in range(-r, r+1):
                    if dx*dx + dy*dy <= r*r:
                        yy, xx2 = py + dy, px + dx
                        if 0 <= yy < h and 0 <= xx2 < w:
                            val = 1.0 - (dx*dx + dy*dy) / (r*r + 1)
                            result[yy, xx2] = max(result[yy, xx2], val * 0.8)
        ex = x + length * np.cos(angle)
        ey = y + length * np.sin(angle)
        # Branch into 2-3 children
        n_children = rng.randint(2, 4)
        for _ in range(n_children):
            child_angle = angle + rng.uniform(-0.7, 0.7)
            child_len = length * rng.uniform(0.5, 0.75)
            child_thick = thickness * 0.65
            _draw_branch(ex, ey, child_angle, child_len, child_thick, depth - 1)

    for _ in range(num_neurons):
        sx, sy = rng.rand() * w, rng.rand() * h
        for arm in range(rng.randint(3, 7)):
            angle = rng.uniform(0, 2 * np.pi)
            _draw_branch(sx, sy, angle, rng.uniform(30, 80), 3.0, branch_depth)
        # Cell body glow
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                yy, xx2 = int(sy) + dy, int(sx) + dx
                if 0 <= yy < h and 0 <= xx2 < w:
                    d = np.sqrt(dx*dx + dy*dy)
                    result[yy, xx2] = max(result[yy, xx2], np.exp(-d*d / 18.0))

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
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    result = np.ones(shape, dtype=np.float32) * 0.85

    for _ in range(num_spots):
        cx, cy = rng.rand() * w, rng.rand() * h
        radius = rng.uniform(8, max_radius)
        d = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        # Ring pattern with rough edges
        ring = np.sin(d / radius * np.pi * 3.0) * 0.3
        rust_depth = np.exp(-(d / radius)**2 * 2.0) * rng.uniform(0.4, 0.9)
        # Jagged edge noise
        angle = np.arctan2(yy - cy, xx - cx)
        edge_noise = np.sin(angle * rng.uniform(5, 15)) * radius * 0.15
        adjusted_d = d - edge_noise
        mask = np.clip(1.0 - adjusted_d / radius, 0, 1)
        result -= (rust_depth + ring * 0.5) * mask

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

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    min_d = np.full((h, w), 1e9, dtype=np.float32)
    second_d = np.full((h, w), 1e9, dtype=np.float32)
    closest = np.zeros((h, w), dtype=np.int32)

    for i in range(num_plates):
        d = np.sqrt((xx - cx[i])**2 + (yy - cy[i])**2)
        mask = d < min_d
        second_d = np.where(mask, min_d, np.minimum(second_d, d))
        closest = np.where(mask, i, closest)
        min_d = np.minimum(min_d, d)

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
    # Asymmetric: gradual rise then sharp drop
    primary = np.where(profile < 0.7, profile / 0.7, (1.0 - profile) / 0.3)

    # Secondary ripples (smaller scale)
    v = -X * np.sin(wind_angle) + Y * np.cos(wind_angle)
    secondary = np.sin(u * dune_freq * 5.0 + v * 3.0 + rng.uniform(0, 6.28)) * 0.15

    # Large-scale undulation
    large = np.sin(u * 2.5 + rng.uniform(0, 6.28)) * np.sin(v * 1.8 + rng.uniform(0, 6.28)) * 0.2

    result = primary + secondary + large
    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 42. CIRCUIT_TRACE — PCB routing traces
# ============================================================================

def circuit_trace(shape, seed, sm, trace_count=40, **kwargs):
    """PCB circuit traces — Manhattan-routed conductive paths with pads."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    result = np.full(shape, 0.15, dtype=np.float32)  # Dark substrate

    for _ in range(trace_count):
        x, y = rng.randint(0, w), rng.randint(0, h)
        thickness = rng.randint(1, 4)
        brightness = rng.uniform(0.6, 1.0)
        segments = rng.randint(3, 10)

        for _ in range(segments):
            direction = rng.choice(['h', 'v'])
            length = rng.randint(10, 80)

            if direction == 'h':
                x2 = np.clip(x + rng.choice([-1, 1]) * length, 0, w-1)
                y1, y2_t = max(0, y-thickness), min(h, y+thickness+1)
                x_lo, x_hi = int(min(x, x2)), int(max(x, x2))
                result[y1:y2_t, x_lo:x_hi] = brightness
                x = int(x2)
            else:
                y2 = np.clip(y + rng.choice([-1, 1]) * length, 0, h-1)
                x1, x2_t = max(0, x-thickness), min(w, x+thickness+1)
                y_lo, y_hi = int(min(y, y2)), int(max(y, y2))
                result[y_lo:y_hi, x1:x2_t] = brightness
                y = int(y2)

        # Solder pad at endpoints
        pad_r = thickness + 2
        for dy in range(-pad_r, pad_r+1):
            for dx in range(-pad_r, pad_r+1):
                py2, px2 = y + dy, x + dx
                if 0 <= py2 < h and 0 <= px2 < w and dx*dx + dy*dy <= pad_r*pad_r:
                    result[py2, px2] = min(1.0, brightness + 0.15)

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

    # Create smooth flowing thickness field
    thickness = np.zeros(shape, dtype=np.float32)
    for _ in range(num_pools):
        cx, cy = rng.rand(), rng.rand()
        sx, sy = rng.uniform(0.1, 0.4), rng.uniform(0.1, 0.4)
        angle = rng.uniform(0, np.pi)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        dx = (X - cx) * cos_a + (Y - cy) * sin_a
        dy = -(X - cx) * sin_a + (Y - cy) * cos_a
        pool = np.exp(-(dx**2 / sx**2 + dy**2 / sy**2))
        thickness += pool * rng.uniform(0.5, 2.0)

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

        # Ejecta rays
        num_rays = rng.randint(8, 20)
        rays = np.zeros(shape, dtype=np.float32)
        for ray in range(num_rays):
            ray_angle = rng.uniform(0, 2 * np.pi)
            ray_width = rng.uniform(0.05, 0.15)
            ang_dist = np.abs(np.mod(theta - ray_angle + np.pi, 2*np.pi) - np.pi)
            ray_mask = np.exp(-(ang_dist / ray_width)**2)
            ray_falloff = np.exp(-(r - crater_r) / (crater_r * rng.uniform(1.0, 3.0)))
            ray_falloff = np.where(r > crater_r, ray_falloff, 0)
            rays += ray_mask * ray_falloff * 0.3

        # Shock rings
        shock = np.sin((r - crater_r) / (crater_r * 0.3) * np.pi * 4) * 0.1
        shock = np.where(r > crater_r, shock * np.exp(-(r - crater_r) / crater_r), 0)

        result += rim + rays + shock - bowl

    return _sm_scale(_normalize(np.clip(result, 0, 1.5)), sm)


# ============================================================================
# 45. FUNGAL_NETWORK — mycelium interconnected threads
# ============================================================================

def fungal_network(shape, seed, sm, num_hyphae=60, **kwargs):
    """Mycelium fungal network — delicate interconnected branching threads."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    result = np.full(shape, 0.1, dtype=np.float32)

    for _ in range(num_hyphae):
        x, y = rng.rand() * w, rng.rand() * h
        angle = rng.uniform(0, 2 * np.pi)
        speed = rng.uniform(1.5, 4.0)
        brightness = rng.uniform(0.5, 1.0)
        length = rng.randint(40, 150)

        for step in range(length):
            px, py = int(x) % w, int(y) % h
            # Glow around hypha
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    yy2, xx2 = (py + dy) % h, (px + dx) % w
                    d = np.sqrt(dx*dx + dy*dy)
                    glow = brightness * np.exp(-d * 0.8)
                    result[yy2, xx2] = max(result[yy2, xx2], glow)

            # Random walk with momentum
            angle += rng.uniform(-0.4, 0.4)
            x += np.cos(angle) * speed
            y += np.sin(angle) * speed

            # Occasional branching
            if rng.rand() < 0.03:
                angle += rng.choice([-1.0, 1.0]) * rng.uniform(0.5, 1.2)

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

    # Warp field from gravity wells
    warp_x = np.zeros(shape, dtype=np.float32)
    warp_y = np.zeros(shape, dtype=np.float32)
    for _ in range(num_wells):
        wx, wy = rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)
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

    # Accretion ring brightness near event horizon
    accretion = np.zeros(shape, dtype=np.float32)
    for _ in range(num_wells):
        wx, wy = rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)
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
        # Expanding rings behind
        r = np.sqrt(dx**2 + dy**2)
        rings = np.sin(r * 30.0 - along * 15.0) * 0.3 * cone_mask * np.exp(-cone_dist * 5.0)

        result += shock + np.clip(rings, 0, 1) * 0.5

    return _sm_scale(_normalize(result), sm)


# ============================================================================
# 48. CRYSTAL_GROWTH — dendritic crystal frost formation
# ============================================================================

def crystal_growth(shape, seed, sm, num_seeds_pts=4, growth_steps=200, **kwargs):
    """Dendritic crystal growth — frost/snowflake branching solidification."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    result = np.zeros(shape, dtype=np.float32)

    # Use 6-fold symmetry growth simulation
    for s in range(num_seeds_pts):
        cx, cy = rng.randint(20, w-20), rng.randint(20, h-20)
        angle = rng.uniform(0, np.pi / 3)
        num_arms = 6

        for arm in range(num_arms):
            arm_angle = angle + arm * np.pi / 3
            x, y = float(cx), float(cy)
            branch_prob = 0.08

            for step in range(growth_steps):
                px, py = int(x) % w, int(y) % h
                val = 1.0 - step / growth_steps * 0.5
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        yy2 = (py + dy) % h
                        xx2 = (px + dx) % w
                        result[yy2, xx2] = max(result[yy2, xx2], val * np.exp(-(dx*dx+dy*dy)*0.5))

                # Advance with slight randomness
                x += np.cos(arm_angle) * 1.5 + rng.uniform(-0.3, 0.3)
                y += np.sin(arm_angle) * 1.5 + rng.uniform(-0.3, 0.3)

                # Side branches
                if rng.rand() < branch_prob:
                    side = rng.choice([-1, 1])
                    bx, by = x, y
                    b_angle = arm_angle + side * np.pi / 3
                    b_len = rng.randint(10, 40)
                    for bs in range(b_len):
                        bpx, bpy = int(bx) % w, int(by) % h
                        bval = val * (1.0 - bs / b_len) * 0.7
                        result[bpy, bpx] = max(result[bpy, bpx], bval)
                        bx += np.cos(b_angle) * 1.2
                        by += np.sin(b_angle) * 1.2

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

        # Width expands as smoke rises
        plume_width = width_base + (1.0 - yy) * 0.08
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
    """Recursive fractal electrical discharge — dense branching energy patterns."""
    h, w = shape
    if sm < 0.001:
        return _flat(shape)
    rng = np.random.RandomState(seed)
    result = np.zeros(shape, dtype=np.float32)

    def _bolt(x1, y1, x2, y2, brightness, depth_left):
        if depth_left <= 0:
            return
        # Midpoint displacement
        mx = (x1 + x2) / 2 + rng.uniform(-1, 1) * abs(x2 - x1) * 0.4
        my = (y1 + y2) / 2 + rng.uniform(-1, 1) * abs(y2 - y1) * 0.4
        mx = np.clip(mx, 0, w-1)
        my = np.clip(my, 0, h-1)

        # Draw line segment
        steps = max(int(np.sqrt((mx-x1)**2 + (my-y1)**2)), 1)
        for s in range(steps):
            t = s / steps
            px = int(x1 + (mx - x1) * t) % w
            py = int(y1 + (my - y1) * t) % h
            r = max(1, int(brightness * 2.5))
            for dy in range(-r, r+1):
                for dx in range(-r, r+1):
                    yy2 = (py + dy) % h
                    xx2 = (px + dx) % w
                    d = np.sqrt(dx*dx + dy*dy)
                    glow = brightness * np.exp(-d * 0.7)
                    result[yy2, xx2] = max(result[yy2, xx2], glow)

        _bolt(x1, y1, mx, my, brightness * 0.85, depth_left - 1)
        _bolt(mx, my, x2, y2, brightness * 0.85, depth_left - 1)

        # Side branch
        if rng.rand() < 0.35:
            bx = mx + rng.uniform(-40, 40)
            by = my + rng.uniform(-40, 40)
            _bolt(mx, my, np.clip(bx, 0, w-1), np.clip(by, 0, h-1),
                  brightness * 0.5, depth_left - 2)

    for _ in range(num_bolts):
        x1 = rng.uniform(0, w)
        y1 = rng.choice([0, h-1]) if rng.rand() > 0.5 else rng.uniform(0, h)
        x2 = rng.uniform(0, w)
        y2 = rng.uniform(0, h)
        _bolt(x1, y1, x2, y2, 1.0, depth)

    return _sm_scale(_normalize(result), sm)


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
